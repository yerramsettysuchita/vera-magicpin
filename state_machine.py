"""
state_machine.py -- Explicit FSM for Vera's conversation lifecycle.

Layer 5 component. Tracks conversation state across turns and computes
the correct next action for conversation_handlers.py.

States:
  new         -- no merchant messages received yet
  qualifying  -- merchant engaged, intent unclear
  accepted    -- merchant said yes / let's do it
  declined    -- merchant opted out
  hostile     -- merchant is aggressively negative
  auto_reply  -- merchant is sending OOO / canned responses
  off_topic   -- merchant asking about unrelated topics (GST, loans, etc.)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from intent_classifier import classify_turns
from auto_reply_detector import auto_reply_score

__all__ = ["ConversationFSM", "ConvState"]

ConvState = Literal[
    "new", "qualifying", "accepted", "declined",
    "hostile", "auto_reply", "off_topic",
]

# Suggested wait in seconds before Vera can follow up
_WAIT_SECONDS: dict[str, int] = {
    "new":        0,
    "qualifying": 300,
    "accepted":   0,
    "declined":   0,
    "hostile":    0,
    "auto_reply": 0,
    "off_topic":  120,
}

_INTENT_TO_STATE: dict[str, ConvState] = {
    "hostile":   "hostile",
    "decline":   "declined",
    "accept":    "accepted",
    "off_topic": "off_topic",
    "question":  "qualifying",
    "neutral":   "qualifying",
}


@dataclass
class ConversationFSM:
    """
    Explicit finite-state machine for a single conversation thread.
    Instantiate one per conversation_id and call transition() on each new turn.
    """
    state: ConvState = "new"
    turns_in_state: int = 0
    _history: list[ConvState] = field(default_factory=list, repr=False)

    def transition(self, turns: list[dict]) -> ConvState:
        """
        Compute and apply next state given the full conversation turns.
        Auto-reply detection takes priority over intent classification.
        """
        if self.is_terminal:
            return self.state

        if auto_reply_score(turns) >= 0.7:
            self._set("auto_reply")
            return self.state

        intent = classify_turns(turns)
        next_state: ConvState = _INTENT_TO_STATE.get(intent, "qualifying")
        self._set(next_state)
        return self.state

    def _set(self, new_state: ConvState) -> None:
        if new_state != self.state:
            self._history.append(self.state)
            self.state = new_state
            self.turns_in_state = 0
        else:
            self.turns_in_state += 1

    @property
    def is_terminal(self) -> bool:
        """Terminal states cannot transition further."""
        return self.state in ("hostile", "declined")

    @property
    def suggested_wait_seconds(self) -> int:
        """How long Vera should wait before following up in this state."""
        return _WAIT_SECONDS.get(self.state, 300)

    @property
    def state_history(self) -> list[ConvState]:
        return list(self._history)
