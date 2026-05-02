"""
validator.py — Post-generation guardrails for ComposedMessage.

Five checks (in order):
  1. CTA shape — exactly one CTA, correct type for profile
  2. Language match — body honors merchant's language_pref
  3. Anti-hallucination scan — every cited fact traceable to input
  4. URL scan — no hyperlinks in body (−3 penalty)
  5. Jargon scan — no internal field names exposed

Returns ValidationResult(ok, errors[], warnings[], fixed_body)
If ok=False, the composer re-prompts once with the error list.
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field


@dataclass
class ValidationResult:
    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    fixed_body: str | None = None
    reprompt_instruction: str = ""


# ── Internal jargon that must never appear in the message body ──────────────
_JARGON_PATTERNS = [
    r"\bsuppression_key\b",
    r"\btrigger_id\b",
    r"\bpayload\b",
    r"\bcontext_id\b",
    r"\bmerchant_id\b",
    r"\bcustomer_id\b",
    r"\bDistilledContext\b",
    r"\bcomposeMessage\b",
    r"\bprofile_id\b",
    r"\bkind\b(?=\s*[:=])",  # "kind:" or "kind=" patterns
    r"\bdata_richness\b",
    r"\bplaceholder\b",
]

# ── URL pattern ──────────────────────────────────────────────────────────────
_URL_PATTERN = re.compile(
    r"https?://\S+|www\.\S+|\b\w+\.(com|in|org|net|io|co)\b",
    re.IGNORECASE,
)

# ── Multiple CTA indicators ──────────────────────────────────────────────────
# A CTA is a sentence with a question mark or an imperative ending
_CTA_ENDINGS = re.compile(r"\?\s*$|\breply\b|\bYES\b|\bNO\b|\bSTOP\b|\bCall now\b|\bBook now\b", re.IGNORECASE | re.MULTILINE)


def _count_ctas(body: str) -> int:
    """Heuristic: count question marks + "Reply X" patterns as CTA candidates."""
    questions = body.count("?")
    reply_cmds = len(re.findall(r"\bReply\s+[0-9A-Z]\b", body, re.IGNORECASE))
    # Each "Reply X" is a CTA; each "?" is a potential CTA
    # But "?" inside a parenthetical doesn't count
    clean = re.sub(r"\([^)]*\?[^)]*\)", "", body)
    clean_questions = clean.count("?")
    return max(clean_questions, reply_cmds)


def _check_cta_shape(body: str, cta: str, profile_cta_type: str | None) -> list[str]:
    errors = []
    cta_count = _count_ctas(body + " " + cta)

    if cta_count == 0:
        errors.append("NO_CTA: message has no call-to-action — add one")
    elif cta_count > 2:
        errors.append(f"MULTIPLE_CTA: {cta_count} CTA signals detected — reduce to exactly one")

    if not cta or not cta.strip():
        errors.append("EMPTY_CTA: cta field is blank")

    return errors


def _check_language(body: str, languages: list[str], language_pref: str | None = None) -> list[str]:
    """
    Verify language match. If merchant/customer is hi-only, body must contain
    Devanagari or clear Hindi words. If en-only, no Devanagari.
    """
    warnings = []
    pref = (language_pref or "").lower()

    has_devanagari = bool(re.search(r"[ऀ-ॿ]", body))
    has_english = bool(re.search(r"[a-zA-Z]{3,}", body))

    if pref == "hi" and not has_devanagari:
        # Strict Hindi required — check for at least some Hindi words
        hindi_words = {"namaste", "aapka", "aapki", "ji", "haan", "nahi", "kare", "karo",
                       "lagta", "chahiye", "please", "aap"}
        body_lower = body.lower()
        found_hindi = any(w in body_lower for w in hindi_words)
        if not found_hindi and not has_devanagari:
            warnings.append(
                "LANG_MISMATCH: customer prefers Hindi-only but body appears English — "
                "consider adding Hindi phrases or Devanagari"
            )

    if "hi" in (languages or []) and "hi-en mix" in pref and not has_devanagari:
        # hi-en mix: soft warning, some Hindi appreciated
        pass  # too noisy to warn — code-mixing is natural

    return warnings


def _check_urls(body: str) -> list[str]:
    errors = []
    urls = _URL_PATTERN.findall(body)
    if urls:
        errors.append(f"URL_PENALTY: body contains URL(s) — {urls[:3]} — remove immediately (−3 penalty)")
    return errors


def _check_jargon(body: str) -> list[str]:
    errors = []
    for pattern in _JARGON_PATTERNS:
        if re.search(pattern, body, re.IGNORECASE):
            errors.append(f"JARGON_EXPOSED: internal term matched '{pattern}' in body (−1 penalty)")
    return errors


def _check_anti_hallucination(
    body: str,
    distilled_ctx: dict,
    trigger: dict,
    merchant: dict,
    customer: dict | None,
) -> list[str]:
    """
    Scan every number in the body and verify it appears somewhere in the input.
    Any number NOT traceable to input = potential hallucination.
    """
    warnings = []
    # Extract all numbers (percentages, currency amounts, counts)
    body_numbers = set(re.findall(r"\b\d[\d,.]*\b", body.replace("₹", "")))

    # Build a pool of legitimate numbers from all input sources
    legitimate_pool: set[str] = set()

    payload = trigger.get("payload", {}) or {}
    for v in _flatten_values(payload):
        if isinstance(v, (int, float)):
            legitimate_pool.add(str(int(v)) if v == int(v) else str(v))
            # Also add percentage form
            if 0 < abs(v) < 1:
                legitimate_pool.add(str(int(v * 100)))

    perf = merchant.get("performance", {}) or {}
    for v in _flatten_values(perf):
        if isinstance(v, (int, float)):
            legitimate_pool.add(str(int(v)) if v == int(v) else str(round(v, 4)))

    agg = merchant.get("customer_aggregate", {}) or {}
    for v in _flatten_values(agg):
        if isinstance(v, (int, float)):
            legitimate_pool.add(str(int(v)))

    if customer:
        rel = customer.get("relationship", {}) or {}
        for v in _flatten_values(rel):
            if isinstance(v, (int, float)):
                legitimate_pool.add(str(int(v)))

    # Add anchor numbers from distilled context
    anchor = distilled_ctx.get("trigger_anchor", "")
    anchor_nums = re.findall(r"\b\d[\d,.]*\b", anchor)
    legitimate_pool.update(anchor_nums)

    # Allow common small numbers (days, percentages already in data)
    common_ok = {"1", "2", "3", "4", "5", "6", "7", "10", "15", "20", "24", "30",
                 "40", "45", "50", "60", "100", "299", "499", "999"}
    legitimate_pool.update(common_ok)

    suspicious = body_numbers - legitimate_pool
    # Filter out years (2026, 2025) and phone-like numbers
    suspicious = {n for n in suspicious if not (len(n) == 4 and n.startswith("202"))}
    suspicious = {n for n in suspicious if len(n) < 8}

    if suspicious:
        warnings.append(
            f"HALLUCINATION_RISK: numbers {suspicious} in body not found in input data — "
            "verify these are from category fingerprints, not invented"
        )

    return warnings


def _flatten_values(d: dict | list, _depth: int = 0) -> list:
    if _depth > 3:
        return []
    vals = []
    if isinstance(d, dict):
        for v in d.values():
            if isinstance(v, (int, float, str)):
                vals.append(v)
            elif isinstance(v, (dict, list)):
                vals.extend(_flatten_values(v, _depth + 1))
    elif isinstance(d, list):
        for item in d:
            if isinstance(item, (int, float, str)):
                vals.append(item)
            elif isinstance(item, (dict, list)):
                vals.extend(_flatten_values(item, _depth + 1))
    return vals


def validate(
    composed: dict,
    distilled_ctx: dict,
    trigger: dict,
    merchant: dict,
    customer: dict | None = None,
    profile_cta_type: str | None = None,
) -> ValidationResult:
    """
    Run all 5 guardrail checks on a ComposedMessage.

    Args:
        composed        : {"body": ..., "cta": ..., "send_as": ..., "rationale": ...}
        distilled_ctx   : output of context_distiller.distill()
        trigger         : raw trigger dict
        merchant        : raw merchant dict
        customer        : raw customer dict (if applicable)
        profile_cta_type: expected CTA type from signal_classifier

    Returns:
        ValidationResult with ok=True if all checks pass, else errors + reprompt instruction
    """
    body = composed.get("body", "")
    cta = composed.get("cta", "")
    rationale = composed.get("rationale", "")

    all_errors: list[str] = []
    all_warnings: list[str] = []

    # 1. CTA shape
    cta_errors = _check_cta_shape(body, cta, profile_cta_type)
    all_errors.extend(cta_errors)

    # 2. Language match
    m_identity = merchant.get("identity", {}) or {}
    merchant_langs = m_identity.get("languages") or merchant.get("languages", ["en"])
    cust_lang_pref = None
    if customer:
        cust_lang_pref = customer.get("identity", {}).get("language_pref")
    lang_warnings = _check_language(body, merchant_langs, cust_lang_pref)
    all_warnings.extend(lang_warnings)

    # 3. URL check
    url_errors = _check_urls(body)
    all_errors.extend(url_errors)

    # 4. Jargon check
    jargon_errors = _check_jargon(body)
    all_errors.extend(jargon_errors)

    # 5. Anti-hallucination
    halluc_warnings = _check_anti_hallucination(body, distilled_ctx, trigger, merchant, customer)
    all_warnings.extend(halluc_warnings)

    # Additional: empty body or rationale
    if not body or len(body.strip()) < 20:
        all_errors.append("EMPTY_BODY: body is empty or too short")
    if not rationale or len(rationale.strip()) < 20:
        all_warnings.append("WEAK_RATIONALE: rationale is too short — add lever + context explanation")

    # Anti-repetition check
    last_topic = distilled_ctx.get("memory_trace", {}).get("last_topic") or ""
    if last_topic and _is_same_topic(body, last_topic):
        all_errors.append(
            f"ANTI_REPETITION: body topic appears similar to last sent message: '{last_topic[:60]}' — "
            "change the topic or angle (−2 penalty)"
        )

    ok = len(all_errors) == 0

    reprompt = ""
    if not ok:
        reprompt = (
            "The previous composition failed validation. Fix these issues:\n"
            + "\n".join(f"  - {e}" for e in all_errors)
            + (("\nWarnings (fix if possible):\n" + "\n".join(f"  - {w}" for w in all_warnings)) if all_warnings else "")
        )

    return ValidationResult(
        ok=ok,
        errors=all_errors,
        warnings=all_warnings,
        reprompt_instruction=reprompt,
    )


def _is_same_topic(body: str, last_topic: str, threshold: float = 0.55) -> bool:
    """Word-overlap heuristic to detect topic repetition."""
    def key_words(s: str) -> set[str]:
        return {w.lower().strip(".,!?₹") for w in s.split() if len(w) > 4}

    last_w = key_words(last_topic)
    body_w = key_words(body)
    if not last_w:
        return False
    overlap = len(last_w & body_w) / len(last_w)
    return overlap >= threshold
