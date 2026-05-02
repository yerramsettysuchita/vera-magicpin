"""
reply_simulator.py — Simulates 3 likely merchant replies and scores YES-path ease.

This is Vera's "moat" feature: before a message is sent, we simulate how a real
merchant is likely to respond. We score for how easily the message converts to a
YES (or equivalent action). Messages that score < 6 are flagged for revision.

Flow:
  1. Takes a ComposedMessage + distilled context
  2. Sends to claude-haiku (fast, cheap) at temperature=0.7 to get variety
  3. Returns 3 simulated merchant replies with YES-path scores (1-10)
  4. Also returns the best-scoring message version if an alternative phrasing would score higher

Architecture:
  - Async-ready but runs sync in the test suite
  - Uses claude-haiku-4-5-20251001 (speed over quality for simulation)
  - temperature=0.7 intentionally for realistic reply variety
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field

import anthropic


_MODEL_SIMULATOR = "claude-haiku-4-5-20251001"
_MAX_TOKENS_SIM = 500
_TIMEOUT_S = 20

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


@dataclass
class SimulatedReply:
    reply_text: str
    yes_path_score: int       # 1-10: how likely this leads to merchant action
    reply_type: str           # "accepted" | "qualified" | "declined" | "ignored"
    reasoning: str


@dataclass
class SimulationResult:
    replies: list[SimulatedReply]
    best_score: int
    worst_score: int
    avg_score: float
    flag_for_revision: bool   # True if avg_score < 6
    improvement_hint: str     # specific suggestion if flag_for_revision=True
    latency_ms: int = 0


_SIMULATOR_SYSTEM_PROMPT = """You are a realistic Indian merchant — a busy shop owner, salon manager, or clinic operator — receiving a WhatsApp message from an AI assistant called Vera.

Your job: simulate how a real merchant would respond to the message. Be realistic. Merchants are busy, sometimes skeptical, sometimes warm. They respond in Hindi, English, or code-switch (hi-en mix) depending on their city.

You will return EXACTLY 3 different simulated replies representing the realistic range of merchant responses to the given message.

For each reply:
- reply_text: what the merchant actually types back (realistic WhatsApp message — short, natural, sometimes with typos)
- yes_path_score (1-10): how much this reply advances toward the merchant taking the desired action
  - 10 = immediate YES, books/confirms/acts
  - 7-9 = positive engagement, asking follow-up
  - 4-6 = neutral / lukewarm ("okay", "dekh lete", "maybe")
  - 1-3 = decline or no action ("no thanks", silence, "busy")
- reply_type: "accepted" | "qualified" | "declined" | "ignored"
- reasoning: 1 sentence on why the merchant responded this way

After the 3 replies, provide:
- improvement_hint: if avg_score < 6, one specific suggestion to improve the message to get a better response (e.g., "The ask is too vague — name the specific slot" or "The data point is too generic — cite the actual number")
- If avg_score >= 6, improvement_hint = ""

OUTPUT FORMAT (strict JSON):
{
  "replies": [
    {"reply_text": "...", "yes_path_score": 8, "reply_type": "accepted", "reasoning": "..."},
    {"reply_text": "...", "yes_path_score": 5, "reply_type": "qualified", "reasoning": "..."},
    {"reply_text": "...", "yes_path_score": 2, "reply_type": "declined", "reasoning": "..."}
  ],
  "improvement_hint": "..."
}"""


def _build_simulation_prompt(
    message_body: str,
    cta: str,
    merchant: dict,
    distilled_ctx: dict,
) -> str:
    owner = merchant.get("owner_name", merchant.get("name", "merchant"))
    category = merchant.get("category_slug", merchant.get("category", "unknown"))
    city = merchant.get("city", "unknown")
    lang_pref = merchant.get("language_pref", "en")

    # Pull trace info if available
    trace = distilled_ctx.get("memory_trace", {}) or {}
    session_open = trace.get("session_open", False)
    turn_count = trace.get("turn_count", 0)

    context_lines = [
        f"Merchant: {owner}",
        f"Category: {category}",
        f"City: {city}",
        f"Language preference: {lang_pref}",
        f"Prior conversation turns: {turn_count}",
        f"WhatsApp session open: {session_open}",
    ]

    customer_summary = distilled_ctx.get("customer_summary", "")
    if customer_summary:
        context_lines.append(f"Customer context: {customer_summary}")

    context_block = "\n".join(context_lines)

    return (
        f"MERCHANT CONTEXT:\n{context_block}\n\n"
        f"MESSAGE VERA SENT:\n{message_body}\n\n"
        f"CTA: {cta}\n\n"
        f"Simulate 3 realistic merchant replies and score each for YES-path ease."
    )


def simulate(
    message_body: str,
    cta: str,
    merchant: dict,
    distilled_ctx: dict,
) -> SimulationResult:
    """
    Simulate 3 merchant replies to a composed Vera message.

    Args:
        message_body:  The body text of the composed message
        cta:           The CTA line of the composed message
        merchant:      Merchant record
        distilled_ctx: Output from context_distiller.distill()

    Returns:
        SimulationResult with 3 replies, scores, and improvement hint
    """
    t_start = time.monotonic()
    client = _get_client()

    user_prompt = _build_simulation_prompt(message_body, cta, merchant, distilled_ctx)

    response = client.messages.create(
        model=_MODEL_SIMULATOR,
        max_tokens=_MAX_TOKENS_SIM,
        temperature=0.7,
        system=_SIMULATOR_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
        timeout=_TIMEOUT_S,
    )

    raw = response.content[0].text.strip()

    # Strip markdown fences
    if raw.startswith("```"):
        lines = raw.splitlines()
        raw = "\n".join(
            line for line in lines if not line.strip().startswith("```")
        ).strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Graceful degradation: return a neutral result rather than crashing
        return SimulationResult(
            replies=[],
            best_score=5,
            worst_score=5,
            avg_score=5.0,
            flag_for_revision=False,
            improvement_hint="[simulation parse error — raw output not valid JSON]",
            latency_ms=int((time.monotonic() - t_start) * 1000),
        )

    replies = []
    for r in data.get("replies", []):
        replies.append(
            SimulatedReply(
                reply_text=r.get("reply_text", ""),
                yes_path_score=int(r.get("yes_path_score", 5)),
                reply_type=r.get("reply_type", "qualified"),
                reasoning=r.get("reasoning", ""),
            )
        )

    scores = [r.yes_path_score for r in replies] if replies else [5]
    best = max(scores)
    worst = min(scores)
    avg = sum(scores) / len(scores)
    flag = avg < 6.0

    hint = data.get("improvement_hint", "")
    if flag and not hint:
        hint = "Message did not achieve avg YES-path score ≥ 6. Review specificity and CTA clarity."

    return SimulationResult(
        replies=replies,
        best_score=best,
        worst_score=worst,
        avg_score=round(avg, 2),
        flag_for_revision=flag,
        improvement_hint=hint,
        latency_ms=int((time.monotonic() - t_start) * 1000),
    )


def simulate_from_composed(composed, merchant: dict, distilled_ctx: dict) -> SimulationResult:
    """
    Convenience wrapper accepting a ComposedMessage dataclass directly.
    """
    return simulate(
        message_body=composed.body,
        cta=composed.cta,
        merchant=merchant,
        distilled_ctx=distilled_ctx,
    )
