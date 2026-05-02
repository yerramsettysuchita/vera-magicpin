"""
signal_classifier.py — Deterministic trigger → profile router.

Pure Python. No LLM. Guaranteed <5ms. 100% deterministic.
Called first in every compose() pipeline to route to the correct
8 specialized prompt and lever strategy.
"""

from __future__ import annotations

# Maps trigger.kind → profile_id
_KIND_TO_PROFILE: dict[str, str] = {
    # Family A — Knowledge & Compliance
    "research_digest":      "knowledge_digest",
    "regulation_change":    "knowledge_digest",
    "cde_opportunity":      "knowledge_digest",
    "supply_alert":         "knowledge_digest",
    # Family B — Performance
    "perf_dip":             "perf_dip_recovery",
    "seasonal_perf_dip":    "perf_dip_recovery",
    "perf_spike":           "perf_win",
    "milestone_reached":    "perf_win",
    # Family C — Event & Seasonal
    "festival_upcoming":    "event_seasonal",
    "category_seasonal":    "event_seasonal",
    "ipl_match_today":      "event_seasonal",
    # Family D — Activation & Account Health
    "dormant_with_vera":    "activation_urgency",
    "winback_eligible":     "activation_urgency",
    "renewal_due":          "activation_urgency",
    "gbp_unverified":       "activation_urgency",
    "competitor_opened":    "activation_urgency",
    "review_theme_emerged": "activation_urgency",
    # Family E — Conversation & Planning
    "curious_ask_due":      "planning_curiosity",
    "active_planning_intent": "planning_curiosity",
    # Family F — Customer Recall & Booking
    "recall_due":                "customer_recall",
    "appointment_tomorrow":      "customer_recall",
    "trial_followup":            "customer_recall",
    "wedding_package_followup":  "customer_recall",
    # Family G — Customer Retention & Care
    "customer_lapsed_soft": "customer_winback",
    "customer_lapsed_hard": "customer_winback",
    "chronic_refill_due":   "customer_winback",
}

# send_as value per profile
_PROFILE_SEND_AS: dict[str, str] = {
    "knowledge_digest":   "vera",
    "perf_dip_recovery":  "vera",
    "perf_win":           "vera",
    "event_seasonal":     "vera",
    "activation_urgency": "vera",
    "planning_curiosity": "vera",
    "customer_recall":    "merchant_on_behalf",
    "customer_winback":   "merchant_on_behalf",
}

# CTA type per profile (used to validate composer output)
_PROFILE_CTA_TYPE: dict[str, str] = {
    "knowledge_digest":   "open_ended",
    "perf_dip_recovery":  "open_ended",
    "perf_win":           "open_ended",
    "event_seasonal":     "binary",
    "activation_urgency": "mixed",       # binary for renewal/competitor; open for dormant/review
    "planning_curiosity": "open_ended",
    "customer_recall":    "multi_choice_or_binary",
    "customer_winback":   "binary",
}

# Primary lever per profile (numeric)
_PROFILE_PRIMARY_LEVER: dict[str, int] = {
    "knowledge_digest":   1,
    "perf_dip_recovery":  1,
    "perf_win":           5,
    "event_seasonal":     2,
    "activation_urgency": 2,
    "planning_curiosity": 7,   # or 4 for active_planning
    "customer_recall":    8,
    "customer_winback":   5,   # or 2 for hard lapse, 8 for refill
}


class ClassificationResult:
    __slots__ = ("profile_id", "send_as", "cta_type", "primary_lever",
                 "is_seasonal_dip", "is_category_mismatch", "kind")

    def __init__(
        self,
        profile_id: str,
        send_as: str,
        cta_type: str,
        primary_lever: int,
        kind: str,
        is_seasonal_dip: bool = False,
        is_category_mismatch: bool = False,
    ) -> None:
        self.profile_id = profile_id
        self.send_as = send_as
        self.cta_type = cta_type
        self.primary_lever = primary_lever
        self.kind = kind
        self.is_seasonal_dip = is_seasonal_dip
        self.is_category_mismatch = is_category_mismatch

    def __repr__(self) -> str:
        flags = []
        if self.is_seasonal_dip:
            flags.append("seasonal_dip")
        if self.is_category_mismatch:
            flags.append("category_mismatch")
        flag_str = f" [{','.join(flags)}]" if flags else ""
        return (
            f"ClassificationResult(profile={self.profile_id!r}, "
            f"send_as={self.send_as!r}, lever=L{self.primary_lever}{flag_str})"
        )


def classify(trigger: dict, merchant: dict) -> ClassificationResult:
    """
    Map trigger.kind + merchant context to a ClassificationResult.

    Handles two edge cases deterministically:
    1. chronic_refill_due on a non-pharmacy → reframe as customer_recall
    2. perf_dip with seasonal context → flag is_seasonal_dip=True
    """
    kind: str = trigger.get("kind", "")
    payload: dict = trigger.get("payload", {}) or {}
    category_slug: str = merchant.get("category_slug", merchant.get("category", ""))

    is_seasonal_dip = False
    is_category_mismatch = False

    # Edge case 1: chronic_refill_due assigned to non-pharmacy (T08 pattern)
    if kind == "chronic_refill_due" and category_slug not in ("pharmacies", "pharmacy"):
        is_category_mismatch = True
        profile_id = "customer_recall"

    # Edge case 2: perf_dip with seasonal context flag
    elif kind == "perf_dip" and (
        payload.get("is_expected_seasonal") or "seasonal" in kind
    ):
        is_seasonal_dip = True
        profile_id = "perf_dip_recovery"

    # Normal lookup
    else:
        profile_id = _KIND_TO_PROFILE.get(kind)
        if profile_id is None:
            # Unknown kind — fall back by trigger scope
            profile_id = (
                "customer_recall"
                if trigger.get("scope") == "customer"
                else "activation_urgency"
            )

    # Lever override for sub-kinds
    lever = _PROFILE_PRIMARY_LEVER[profile_id]
    if kind == "active_planning_intent":
        lever = 4  # Effort externalization
    elif kind == "chronic_refill_due" and not is_category_mismatch:
        lever = 8  # Binary commitment
    elif kind == "customer_lapsed_hard":
        lever = 2  # Loss aversion
    elif kind == "regulation_change":
        lever = 1  # Specificity (hardest anchor)

    return ClassificationResult(
        profile_id=profile_id,
        send_as=_PROFILE_SEND_AS[profile_id],
        cta_type=_PROFILE_CTA_TYPE[profile_id],
        primary_lever=lever,
        kind=kind,
        is_seasonal_dip=is_seasonal_dip,
        is_category_mismatch=is_category_mismatch,
    )


def get_all_profiles() -> list[str]:
    return list(_PROFILE_SEND_AS.keys())


def kind_to_profile(kind: str) -> str | None:
    return _KIND_TO_PROFILE.get(kind)
