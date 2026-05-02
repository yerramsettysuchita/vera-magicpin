"""
intent_classifier.py -- Classifies merchant reply intent into discrete categories.

Layer 5 component. Returns structured intent signals used by state_machine.py
and conversation_handlers.py to select the next conversation action.
"""

from __future__ import annotations

from memory_trace import detect_intent_transition

__all__ = ["classify_intent", "classify_turns", "IntentCategory"]

IntentCategory = str  # "accept" | "decline" | "hostile" | "question" | "off_topic" | "neutral"

_ACCEPT_SIGNALS = {
    "ok", "okay", "yes", "let's do it", "do it", "go ahead", "sure",
    "haan", "haan ji", "bilkul", "please proceed", "send it", "send",
    "sounds good", "great", "perfect", "done", "proceed",
    "chalo karte hain", "kar do", "bhejna", "ready",
}

_DECLINE_SIGNALS = {
    "no", "nahi", "nope", "not interested", "stop", "stop messaging",
    "band karo", "mat bhejo", "unsubscribe", "remove", "opt out",
    "don't contact", "do not contact", "please stop", "leave me alone",
}

_HOSTILE_SIGNALS = {
    "spam", "useless", "annoying", "waste of time", "terrible", "worst",
    "stop messaging me", "stop contacting me", "never contact me again",
    "report", "complaint", "harassing",
}

_QUESTION_SIGNALS = {
    "how", "what", "when", "where", "which", "can you", "could you",
    "tell me", "explain", "kaise", "kab", "kahan", "batao", "kya hai",
}

_OFF_TOPIC_SIGNALS = {"gst", "income tax", "loan", "help me", "can you also"}


def classify_intent(message: str) -> IntentCategory:
    """
    Classify a single merchant message.
    Priority order: hostile > decline > off_topic > accept > question > neutral.
    """
    msg = message.lower().strip(".,!? ")

    if any(s in msg for s in _HOSTILE_SIGNALS):
        return "hostile"

    if msg in _DECLINE_SIGNALS or any(s in msg for s in _DECLINE_SIGNALS if len(s) > 4):
        return "decline"

    if any(s in msg for s in _OFF_TOPIC_SIGNALS):
        return "off_topic"

    if msg in _ACCEPT_SIGNALS or any(s in msg for s in _ACCEPT_SIGNALS if len(s) > 3):
        return "accept"

    if "?" in message or any(s in msg for s in _QUESTION_SIGNALS):
        return "question"

    return "neutral"


def classify_turns(turns: list[dict]) -> IntentCategory:
    """
    Classify overall conversation intent from all merchant turns.
    Uses detect_intent_transition for sequence-aware accept detection
    (handles "ok", "let's go", etc. even in the middle of a conversation).
    """
    if detect_intent_transition(turns):
        return "accept"
    merchant_msgs = [t.get("msg", "") for t in turns if t.get("from") == "merchant"]
    if not merchant_msgs:
        return "neutral"
    return classify_intent(merchant_msgs[-1])
