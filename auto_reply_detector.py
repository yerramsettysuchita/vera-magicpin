"""
auto_reply_detector.py -- Identifies OOO / canned auto-replies in merchant messages.

Layer 5 component. Used by state_machine.py and conversation_handlers.py to decide
whether to pause or end outreach when the merchant is not genuinely engaged.
"""

from __future__ import annotations

import re

from memory_trace import detect_auto_reply

__all__ = ["is_auto_reply", "detect_repeat_auto_reply", "auto_reply_score"]

_OOO_PATTERNS = [
    r"i\s+(am|m)\s+out\s+of\s+(office|town)",
    r"auto.?reply",
    r"currently\s+unavailable",
    r"back\s+on\s+\w+",
    r"on\s+(leave|vacation|holiday)",
    r"not\s+available\s+right\s+now",
    r"will\s+respond\s+(later|shortly|soon)",
    r"bahar\s+(hu|hoon|gaya|hai)",
    r"abhi\s+available\s+nahi",
    r"thoda\s+busy\s+hu",
]

_OOO_RE = [re.compile(p, re.IGNORECASE) for p in _OOO_PATTERNS]


def is_auto_reply(message: str) -> bool:
    """Return True if message matches known OOO/auto-reply patterns."""
    for pat in _OOO_RE:
        if pat.search(message):
            return True
    return False


def detect_repeat_auto_reply(turns: list[dict], threshold: int = 3) -> bool:
    """Return True if merchant sent the same canned message >= threshold times."""
    return detect_auto_reply(turns, threshold=threshold)


def auto_reply_score(turns: list[dict]) -> float:
    """
    Continuous score [0, 1] for auto-reply likelihood.
    Combines OOO pattern match on latest message with repeat-message detection.
    """
    if not turns:
        return 0.0
    merchant_msgs = [t for t in turns if t.get("from") == "merchant"]
    if not merchant_msgs:
        return 0.0
    last_msg = merchant_msgs[-1].get("msg", "")
    pattern_score = 1.0 if is_auto_reply(last_msg) else 0.0
    repeat_score = 0.7 if detect_repeat_auto_reply(turns, threshold=2) else 0.0
    return min(1.0, pattern_score + repeat_score * 0.3)
