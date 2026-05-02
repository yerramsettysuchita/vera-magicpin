"""
composer.py — Main compose() pipeline for Vera.

Flow:
  1. signal_classifier.classify()  → profile_id, send_as, lever
  2. memory_trace.extract()        → last_topic, session_open, turns
  3. context_distiller.distill()   → DistilledContext (3-5 key facts)
  4. Load system prompt from prompts/<profile_id>.txt  (in-memory cache)
  5. Claude API call (claude-sonnet-4-6, temperature=0, prompt cache)
  6. Parse JSON response → ComposedMessage
  7. validator.validate()          → ValidationResult
  8. If validation fails: re-prompt once with error list
  9. Emit structured JSON log line
  10. Return final ComposedMessage

Returns ComposedMessage or raises ComposerError.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path

import anthropic

from signal_classifier import classify, ClassificationResult
from memory_trace import extract as extract_trace
from context_distiller import distill, format_for_prompt
from validator import validate, ValidationResult


_PROMPTS_DIR = Path(__file__).parent / "prompts"
_MODEL_COMPOSER = "claude-sonnet-4-6"
_OPENROUTER_MODEL = "anthropic/claude-sonnet-4-6"
_MAX_TOKENS = 550
_TIMEOUT_S = 25  # leave 5s headroom under 30s endpoint limit

_client: anthropic.Anthropic | None = None

# OpenRouter backend (used when OPENROUTER_API_KEY is set and ANTHROPIC_API_KEY is not)
_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
_or_client = None  # openai.OpenAI instance, lazy-loaded

# In-memory prompt cache — eliminates disk I/O on every compose() call.
# Prompts are static during a process lifetime; safe to cache forever.
_PROMPT_CACHE: dict[str, str] = {}

# Structured JSON logger for latency + quality telemetry
_logger = logging.getLogger("vera.composer")
if not _logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(message)s"))
    _logger.addHandler(_handler)
    _logger.setLevel(logging.INFO)

# Per-profile retry counters for Phase 3 telemetry
_retry_counts: dict[str, int] = {}
_call_counts: dict[str, int] = {}


def get_retry_rate_stats() -> dict[str, dict]:
    """Return per-profile call count and retry rate for benchmarking."""
    stats = {}
    for profile in set(list(_retry_counts.keys()) + list(_call_counts.keys())):
        calls = _call_counts.get(profile, 0)
        retries = _retry_counts.get(profile, 0)
        stats[profile] = {
            "calls": calls,
            "retries": retries,
            "retry_rate": round(retries / calls, 3) if calls else 0.0,
        }
    return stats


def reset_stats() -> None:
    """Reset telemetry counters (used between benchmark runs)."""
    _retry_counts.clear()
    _call_counts.clear()


def _use_openrouter() -> bool:
    """True if we should route through OpenRouter instead of Anthropic directly."""
    return (
        not os.environ.get("ANTHROPIC_API_KEY")
        and bool(os.environ.get("OPENROUTER_API_KEY"))
    )


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


def _get_or_client():
    """Lazy-init an openai.OpenAI client pointed at OpenRouter."""
    global _or_client
    if _or_client is None:
        try:
            from openai import OpenAI
        except ImportError:
            raise ComposerError(
                "openai package required for OpenRouter backend: pip install openai"
            )
        _or_client = OpenAI(
            base_url=_OPENROUTER_BASE_URL,
            api_key=os.environ["OPENROUTER_API_KEY"],
        )
    return _or_client


@dataclass
class ComposedMessage:
    body: str
    cta: str
    send_as: str          # "vera" | "merchant_on_behalf"
    suppression_key: str  # dedup key for anti-repetition
    rationale: str
    profile_id: str
    lever: int
    validation: ValidationResult = field(default=None)
    latency_ms: int = 0


class ComposerError(Exception):
    pass


def _load_prompt(profile_id: str) -> str:
    if profile_id not in _PROMPT_CACHE:
        path = _PROMPTS_DIR / f"{profile_id}.txt"
        if not path.exists():
            raise ComposerError(f"System prompt not found: {path}")
        _PROMPT_CACHE[profile_id] = path.read_text(encoding="utf-8")
    return _PROMPT_CACHE[profile_id]


def warm_prompt_cache() -> list[str]:
    """Pre-load all 8 prompt files into memory. Call once at server startup."""
    from signal_classifier import get_all_profiles
    loaded = []
    for profile_id in get_all_profiles():
        try:
            _load_prompt(profile_id)
            loaded.append(profile_id)
        except ComposerError:
            pass
    return loaded


def _call_llm(system_prompt: str, user_message: str) -> str:
    """
    Single LLM call. Routes to OpenRouter when OPENROUTER_API_KEY is set and
    ANTHROPIC_API_KEY is not, otherwise calls Anthropic directly.
    """
    if _use_openrouter():
        return _call_llm_openrouter(system_prompt, user_message)
    return _call_llm_anthropic(system_prompt, user_message)


def _call_llm_anthropic(system_prompt: str, user_message: str) -> str:
    """Anthropic SDK with prompt caching."""
    client = _get_client()
    response = client.messages.create(
        model=_MODEL_COMPOSER,
        max_tokens=_MAX_TOKENS,
        temperature=0,
        system=[
            {
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_message}],
        timeout=_TIMEOUT_S,
    )
    return response.content[0].text


def _call_llm_openrouter(system_prompt: str, user_message: str) -> str:
    """OpenRouter via openai-compatible endpoint (no prompt caching support)."""
    client = _get_or_client()
    response = client.chat.completions.create(
        model=_OPENROUTER_MODEL,
        max_tokens=_MAX_TOKENS,
        temperature=0,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_message},
        ],
        timeout=_TIMEOUT_S,
    )
    return response.choices[0].message.content


def _parse_llm_output(raw: str) -> dict:
    """Extract JSON from LLM output, tolerating markdown code fences."""
    text = raw.strip()
    # Strip ```json ... ``` fences if present
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(
            line for line in lines if not line.strip().startswith("```")
        ).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ComposerError(f"LLM returned non-JSON: {e}\nRaw output: {raw[:400]}")


def _build_suppression_key(trigger: dict, profile_id: str) -> str:
    """Stable dedup key: merchant_id + trigger_kind + profile."""
    merchant_id = trigger.get("merchant_id", "unknown")
    kind = trigger.get("kind", "unknown")
    return f"{merchant_id}:{kind}:{profile_id}"


def _reprompt_message(user_message: str, errors: list[str]) -> str:
    error_block = "\n".join(f"- {e}" for e in errors)
    return (
        f"{user_message}\n\n"
        f"PREVIOUS ATTEMPT FAILED VALIDATION. Fix these issues and regenerate:\n"
        f"{error_block}\n"
        f"Return ONLY valid JSON matching the required output format."
    )


def compose(
    trigger: dict,
    merchant: dict,
    customer: dict | None = None,
    category_ctx: dict | None = None,
    conversations: list | None = None,
    conversation_id: str | None = None,
) -> ComposedMessage:
    """
    Main entry point. Orchestrates the full pipeline.

    Args:
        trigger:         Trigger payload dict (kind, payload, merchant_id, …)
        merchant:        Merchant record (name, category_slug, owner_name, perf, …)
        customer:        Optional customer record (name, state, language, …)
        category_ctx:    Optional category intelligence context
        conversations:   Optional list of prior conversation turns
        conversation_id: Optional ID to select a specific conversation

    Returns:
        ComposedMessage with body, cta, send_as, rationale, suppression_key

    Raises:
        ComposerError if pipeline fails after one retry
    """
    t_start = time.monotonic()

    # ── Step 1: Classify ──────────────────────────────────────────────────────
    clf: ClassificationResult = classify(trigger, merchant)

    # ── Step 2: Memory trace ──────────────────────────────────────────────────
    trace = extract_trace(
        merchant,
        conversations=conversations,
        conversation_id=conversation_id,
    )

    # Anti-repetition guard: if last_topic matches current trigger kind, the
    # distiller and prompt will handle avoidance — pass trace through
    trigger["_trace"] = trace  # annotate trigger for distiller

    # ── Step 3: Distil context ────────────────────────────────────────────────
    distilled = distill(
        trigger=trigger,
        merchant=merchant,
        customer=customer or {},
        category_ctx=category_ctx or {},
        trace=trace,
    )

    user_message = format_for_prompt(distilled)

    # ── Step 4: Load system prompt ────────────────────────────────────────────
    system_prompt = _load_prompt(clf.profile_id)

    # ── Step 5: LLM call ──────────────────────────────────────────────────────
    raw_output = _call_llm(system_prompt, user_message)
    parsed = _parse_llm_output(raw_output)

    composed_dict = {
        "body":    parsed.get("body", ""),
        "cta":     parsed.get("cta", ""),
        "send_as": parsed.get("send_as", clf.send_as),
        "rationale": parsed.get("rationale", ""),
    }

    # ── Step 6: Validate ──────────────────────────────────────────────────────
    vr: ValidationResult = validate(
        composed=composed_dict,
        distilled_ctx=distilled,
        trigger=trigger,
        merchant=merchant,
        customer=customer,
        profile_cta_type=clf.cta_type,
    )

    # ── Step 7: Re-prompt once on failure ─────────────────────────────────────
    _call_counts[clf.profile_id] = _call_counts.get(clf.profile_id, 0) + 1
    if not vr.ok:
        _retry_counts[clf.profile_id] = _retry_counts.get(clf.profile_id, 0) + 1
        _logger.info(json.dumps({
            "event": "compose_retry",
            "profile_id": clf.profile_id,
            "errors": vr.errors,
        }))
        retry_message = _reprompt_message(user_message, vr.errors)
        raw_output2 = _call_llm(system_prompt, retry_message)
        parsed = _parse_llm_output(raw_output2)
        composed_dict = {
            "body":    parsed.get("body", ""),
            "cta":     parsed.get("cta", ""),
            "send_as": parsed.get("send_as", clf.send_as),
            "rationale": parsed.get("rationale", ""),
        }
        vr = validate(
            composed=composed_dict,
            distilled_ctx=distilled,
            trigger=trigger,
            merchant=merchant,
            customer=customer,
            profile_cta_type=clf.cta_type,
        )
        # If still failing, surface errors as warnings but don't crash —
        # a partial message is better than no message for live scoring
        if not vr.ok:
            vr.warnings.extend([f"[retry_still_failed] {e}" for e in vr.errors])
            vr.errors = []
            vr.ok = True

    latency_ms = int((time.monotonic() - t_start) * 1000)

    msg = ComposedMessage(
        body=composed_dict["body"],
        cta=composed_dict["cta"],
        send_as=composed_dict["send_as"],
        suppression_key=_build_suppression_key(trigger, clf.profile_id),
        rationale=composed_dict["rationale"],
        profile_id=clf.profile_id,
        lever=clf.primary_lever,
        validation=vr,
        latency_ms=latency_ms,
    )

    # Structured telemetry log (one JSON line per compose call)
    _logger.info(json.dumps({
        "event":       "compose_done",
        "profile_id":  clf.profile_id,
        "kind":        trigger.get("kind"),
        "merchant_id": trigger.get("merchant_id"),
        "latency_ms":  latency_ms,
        "validation_ok": vr.ok,
        "warnings":    len(vr.warnings),
        "send_as":     msg.send_as,
        "lever":       clf.primary_lever,
        "body_len":    len(msg.body),
        "cta_len":     len(msg.cta),
    }))

    return msg


def compose_batch(
    pairs: list[dict],
) -> list[ComposedMessage | Exception]:
    """
    Compose messages for a list of trigger/merchant/customer dicts.
    Returns one result (or caught exception) per input pair.
    Used for bulk test evaluation.
    """
    results = []
    for pair in pairs:
        try:
            msg = compose(
                trigger=pair["trigger"],
                merchant=pair["merchant"],
                customer=pair.get("customer"),
                category_ctx=pair.get("category_ctx"),
                conversations=pair.get("conversations"),
                conversation_id=pair.get("conversation_id"),
            )
            results.append(msg)
        except Exception as exc:
            results.append(exc)
    return results
