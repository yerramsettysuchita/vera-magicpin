"""
conversation_handlers.py -- Multi-turn conversation state machine for Vera.

Called by bot.py's /v1/reply endpoint. Given the full turn history + latest
merchant message, returns the correct action dict for the judge.

Return contract (must match judge_simulator.py expectations):
  {"action": "end"}                        -- stop all outreach (hostile/decline/auto-reply)
  {"action": "wait", "wait_seconds": N}    -- pause and retry later
  {"action": "continue", "body": "..."}    -- send a follow-up reply

Internal "_state" key is stripped by bot.py before returning to the judge.
"""

from __future__ import annotations

import re
from memory_trace import detect_auto_reply, detect_intent_transition, get_conversation_state


# -- Signal word sets ---------------------------------------------------------

_DECLINE_SIGNALS = {
    "no", "nahi", "nope", "not interested", "stop", "stop messaging",
    "band karo", "mat bhejo", "unsubscribe", "remove", "opt out",
    "spam", "useless spam", "don't contact", "do not contact",
    "please stop", "leave me alone",
}

_HOSTILE_SIGNALS = {
    "spam", "useless", "annoying", "waste of time", "terrible", "worst",
    "stop messaging me", "stop contacting me", "never contact me again",
    "report", "complaint", "harassing",
}

_INTENT_ACCEPTED_SIGNALS = {
    "ok", "okay", "yes", "let's do it", "do it", "go ahead", "sure",
    "haan", "haan ji", "bilkul", "please proceed", "send it", "send",
    "sounds good", "great", "perfect", "done", "proceed",
    "chalo karte hain", "kar do", "bhejna", "ready",
}

_QUESTION_SIGNALS = {
    "how", "what", "when", "where", "which", "can you", "could you",
    "tell me", "explain", "kaise", "kab", "kahan", "batao", "kya hai",
}

_OOO_PATTERNS = [
    "out of office", "out of the office", "auto", "automatic reply",
    "ooo", "unavailable", "on leave", "on vacation", "holiday",
    "dhanyawad", "dhanyavaad", "office par nahi", "travel mein",
    "will respond", "will reply", "when i return", "back on",
]


def _is_ooo_message(msg: str) -> bool:
    msg_lower = msg.lower()
    return any(p in msg_lower for p in _OOO_PATTERNS)


def _count_ooo_in_turns(turns: list[dict]) -> int:
    return sum(
        1 for t in turns
        if t.get("from") in ("merchant", "customer") and _is_ooo_message(t.get("msg", ""))
    )

# -- Intent-accepted follow-up templates per profile -------------------------

_INTENT_FOLLOW_UPS: dict[str, str] = {
    "knowledge_digest":   "On it -- I'll pull the abstract and draft your WhatsApp message. Give me 2 minutes.",
    "perf_dip_recovery":  "Good -- pulling the diagnosis now. I'll share one specific fix in a moment.",
    "perf_win":           "Great -- drafting the follow-up campaign now. Ready in 2 minutes.",
    "event_seasonal":     "Perfect -- building the campaign + WhatsApp message now. Done shortly.",
    "activation_urgency": "Got it -- working on it now. I'll send you the draft shortly.",
    "planning_curiosity": "Excellent -- mapping it out now. I'll have the plan ready shortly.",
    "customer_recall":    "Confirmed -- sending the reminder now.",
    "customer_winback":   "Booking it in -- I'll confirm the slot shortly.",
}

_DEFAULT_INTENT_FOLLOW_UP = (
    "Got it -- working on it now. I'll have the draft ready in 2 minutes."
)


def _last_merchant_msg(turns: list[dict]) -> str:
    merchant_msgs = [t.get("msg", "") for t in turns if t.get("from") == "merchant"]
    return merchant_msgs[-1].strip() if merchant_msgs else ""


def _is_hostile(msg: str) -> bool:
    msg_lower = msg.lower()
    return any(sig in msg_lower for sig in _HOSTILE_SIGNALS)


def _is_decline(msg: str) -> bool:
    msg_lower = msg.lower().strip(".,!? ")
    # Exact match on short declines
    if msg_lower in _DECLINE_SIGNALS:
        return True
    # Phrase match
    return any(sig in msg_lower for sig in _DECLINE_SIGNALS if len(sig) > 4)


def _is_question(msg: str) -> bool:
    if "?" in msg:
        return True
    msg_lower = msg.lower()
    return any(sig in msg_lower for sig in _QUESTION_SIGNALS)


def _get_profile_from_history(turns: list[dict]) -> str:
    """Best-effort: extract profile from Vera's last message topic."""
    vera_msgs = [t.get("msg", "") for t in turns if t.get("from") == "vera"]
    if not vera_msgs:
        return ""
    last = vera_msgs[-1].lower()
    if any(w in last for w in ["review", "rating", "theme"]):
        return "activation_urgency"
    if any(w in last for w in ["calls", "views", "ctr", "down"]):
        return "perf_dip_recovery"
    if any(w in last for w in ["up", "spike", "milestone", "crossed"]):
        return "perf_win"
    if any(w in last for w in ["festival", "diwali", "ipl", "season"]):
        return "event_seasonal"
    if any(w in last for w in ["research", "digest", "cde", "circular", "webinar"]):
        return "knowledge_digest"
    if any(w in last for w in ["appointment", "recall", "refill", "slot"]):
        return "customer_recall"
    return ""


def handle_merchant_reply(
    turns: list[dict],
    merchant: dict,
    conversation_id: str = "",
) -> dict:
    """
    Main entry point called by /v1/reply.

    Args:
        turns:           Full conversation history (list of {"from", "msg", "turn"})
        merchant:        Merchant context dict (may be empty for unknown merchants)
        conversation_id: For logging

    Returns:
        dict with "action" key + optional "body", "wait_seconds", "_state" (internal)
    """
    last_msg = _last_merchant_msg(turns)
    state = get_conversation_state(turns)

    # Priority 1: Hostile -> end immediately, no follow-up message
    if _is_hostile(last_msg):
        return {
            "action": "end",
            "rationale": "Merchant sent hostile message — ending conversation to respect their preference.",
            "_state": "hostile",
        }

    # Priority 2: Explicit decline / opt-out -> end
    if _is_decline(last_msg) or state == "declined":
        return {
            "action": "end",
            "rationale": "Merchant declined or opted out — gracefully exiting per their request.",
            "_state": "declined",
        }

    # Priority 3: Auto-reply / OOO detection
    ooo_count = _count_ooo_in_turns(turns)
    if ooo_count >= 1 or state == "auto_reply" or detect_auto_reply(turns, threshold=2):
        if ooo_count >= 2:
            return {
                "action": "end",
                "rationale": "Auto-reply on 2+ turns — merchant is OOO; ending conversation gracefully.",
                "_state": "auto_reply_end",
            }
        return {
            "action": "wait",
            "wait_seconds": 3600,
            "rationale": "Auto-reply detected — merchant is OOO; waiting 1 hour before next check-in.",
            "_state": "auto_reply_wait",
        }

    # Priority 4: Intent transition -> deliver the thing immediately
    if state == "accepted" or detect_intent_transition(turns):
        profile = _get_profile_from_history(turns)
        follow_up = _INTENT_FOLLOW_UPS.get(profile, _DEFAULT_INTENT_FOLLOW_UP)
        owner = (merchant.get("identity") or {}).get("owner_first_name", "")
        if owner:
            follow_up = f"{owner}, {follow_up[0].lower()}{follow_up[1:]}"
        return {
            "action": "continue",
            "body": follow_up,
            "cta": "Let me know if you'd like any changes.",
            "rationale": f"Merchant accepted (intent_transition detected) — delivering follow-up for profile '{profile}'. Switching from qualifying to action mode.",
            "_state": "accepted",
        }

    # Priority 5: Off-topic (GST, unrelated questions) -> gentle redirect
    if state == "off_topic":
        return {
            "action": "continue",
            "body": (
                "Happy to help with that later! For now, let me focus on "
                "your business growth — shall we pick up where we left off?"
            ),
            "cta": "Pick up where we left off?",
            "rationale": "Off-topic question detected (GST/unrelated) — redirecting to core mission without dismissing the merchant.",
            "_state": "off_topic",
        }

    # Priority 6: Question -> wait for compose() to handle next tick
    if _is_question(last_msg):
        return {
            "action": "wait",
            "wait_seconds": 60,
            "rationale": "Merchant asked a qualifying question — waiting 60s for next compose() tick to answer with full context.",
            "_state": "qualifying_question",
        }

    # Priority 7: Short positive / neutral ("ok", "thanks", "hmm") -> wait for next tick
    if len(last_msg.split()) <= 3:
        return {
            "action": "wait",
            "wait_seconds": 120,
            "rationale": "Short neutral reply — giving merchant space; checking back in 2 minutes.",
            "_state": "short_reply_wait",
        }

    # Default: qualifying conversation in progress -> wait for next trigger
    return {
        "action": "wait",
        "wait_seconds": 300,
        "rationale": "Conversation in qualifying state — waiting 5 minutes before next follow-up.",
        "_state": "qualifying",
    }
