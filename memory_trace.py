"""
memory_trace.py — Conversation history parser.

Extracts the last Vera topic and merchant reply signal from
conversation_history, ensuring Vera never repeats herself and
knows whether a WhatsApp session window is currently open.
"""

from __future__ import annotations
from datetime import datetime, timezone, timedelta


def extract(merchant: dict, conversations: dict | None = None,
            conversation_id: str | None = None) -> dict:
    """
    Extract memory trace from merchant context + live conversation state.

    Returns:
        last_topic       : str | None   — last message Vera sent
        last_engagement  : str          — "merchant_replied" | "merchant_no_reply" | "intent_action" | "cold"
        session_open     : bool         — True if WhatsApp 24h session window is open
        turns_in_flight  : list[dict]   — current conversation turns (if conversation_id given)
        turn_count       : int          — number of turns in current conversation
        last_merchant_msg: str | None   — last thing the merchant said
    """
    history: list[dict] = merchant.get("conversation_history", []) or []

    last_topic: str | None = None
    last_engagement: str = "cold"
    session_open: bool = False
    last_ts: datetime | None = None
    last_merchant_msg: str | None = None

    if history:
        # Find most recent vera message and merchant reply
        vera_msgs = [m for m in history if m.get("from") == "vera"]
        merchant_msgs = [m for m in history if m.get("from") == "merchant"]

        if vera_msgs:
            last_vera = vera_msgs[-1]
            last_topic = last_vera.get("body", "")[:120]
            last_engagement = last_vera.get("engagement", "merchant_no_reply")
            ts_str = last_vera.get("ts", "")
            if ts_str:
                try:
                    last_ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                except ValueError:
                    pass

        if merchant_msgs:
            last_merchant_msg = merchant_msgs[-1].get("body", "")[:200]

        # Fallback: use merchant map signals
        if not last_topic:
            last_topic = merchant.get("last_msg_topic")
            last_engagement = merchant.get("last_engagement", "cold") or "cold"

    # Determine if WhatsApp 24h session is open
    if last_ts:
        now = datetime.now(timezone.utc)
        session_open = (now - last_ts) < timedelta(hours=24)
    elif merchant.get("last_engagement") in ("merchant_replied", "intent_action", "intent_question"):
        # No timestamp but engagement signals session may be warm
        session_open = True

    # Live conversation state
    turns_in_flight: list[dict] = []
    turn_count = 0
    if conversations and conversation_id:
        turns_in_flight = conversations.get(conversation_id, [])
        turn_count = len(turns_in_flight)
        # If there are live turns, the session is definitely open
        if turns_in_flight:
            session_open = True
            # Override last_merchant_msg with most recent from live turns
            merchant_turns = [t for t in turns_in_flight if t.get("from") == "merchant"]
            if merchant_turns:
                last_merchant_msg = merchant_turns[-1].get("msg", "")

    return {
        "last_topic": last_topic,
        "last_engagement": last_engagement,
        "session_open": session_open,
        "turns_in_flight": turns_in_flight,
        "turn_count": turn_count,
        "last_merchant_msg": last_merchant_msg,
    }


def is_repeat_topic(candidate_topic: str, trace: dict, threshold: float = 0.6) -> bool:
    """
    Detect if the candidate message is repeating the last sent topic.
    Simple word-overlap heuristic — no LLM needed.
    """
    last = trace.get("last_topic")
    if not last or not candidate_topic:
        return False

    def words(s: str) -> set[str]:
        return {w.lower().strip(".,!?") for w in s.split() if len(w) > 3}

    last_words = words(last)
    cand_words = words(candidate_topic)
    if not last_words:
        return False

    overlap = len(last_words & cand_words) / len(last_words)
    return overlap >= threshold


def detect_auto_reply(turns: list[dict], threshold: int = 3) -> bool:
    """
    Detect if the merchant is sending the same auto-reply canned response.
    Returns True if the same merchant message appears >= threshold times.
    """
    merchant_msgs = [t.get("msg", "").strip() for t in turns if t.get("from") == "merchant"]
    if len(merchant_msgs) < threshold:
        return False
    # Check if the last N messages are identical
    recent = merchant_msgs[-threshold:]
    return len(set(recent)) == 1


def detect_intent_transition(turns: list[dict]) -> bool:
    """
    Detect if merchant has said "ok let's do it" or similar — signals
    intent transition from qualifying to action mode.
    """
    positive_signals = {
        "ok", "okay", "yes", "let's do it", "do it", "go ahead", "sure",
        "haan", "haan ji", "bilkul", "please proceed", "send it", "send"
    }
    merchant_msgs = [t.get("msg", "").strip().lower() for t in turns if t.get("from") == "merchant"]
    for msg in reversed(merchant_msgs[-3:]):
        if any(sig in msg for sig in positive_signals):
            return True
    return False


def get_conversation_state(turns: list[dict]) -> str:
    """
    Classify conversation state for reply composer.
    Returns: "qualifying" | "accepted" | "declined" | "auto_reply" | "off_topic" | "new"
    """
    if not turns:
        return "new"

    if detect_auto_reply(turns):
        return "auto_reply"

    if detect_intent_transition(turns):
        return "accepted"

    merchant_msgs = [t.get("msg", "").strip().lower() for t in turns if t.get("from") == "merchant"]
    if not merchant_msgs:
        return "qualifying"

    last_msg = merchant_msgs[-1] if merchant_msgs else ""
    decline_signals = {"no", "nahi", "not interested", "stop", "band karo", "unsubscribe", "remove"}
    if any(sig in last_msg for sig in decline_signals):
        return "declined"

    # Check for off-topic (GST, unrelated questions)
    off_topic_signals = {"gst", "income tax", "loan", "help me", "can you also"}
    if any(sig in last_msg for sig in off_topic_signals):
        return "off_topic"

    return "qualifying"
