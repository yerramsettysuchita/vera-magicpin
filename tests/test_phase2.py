"""
tests/test_phase2.py — Phase 2 unit tests for Vera's compose pipeline.

5 test pairs covering:
  1. CDE webinar → knowledge_digest (dentist, Delhi)
  2. IPL weekend match → event_seasonal contrarian (restaurant, Delhi, is_weeknight=False)
  3. Perf dip calls −50% → perf_dip_recovery (dentist, Mumbai)
  4. Chronic refill → customer_winback (pharmacy, Jaipur, Hindi)
  5. Validator failure → URL in body caught as hard error

Run: pytest tests/test_phase2.py -v
Requires: ANTHROPIC_API_KEY env var
"""

from __future__ import annotations
import json
import sys
import time
import os
import pytest

# Allow imports from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from signal_classifier import classify
from validator import validate
from context_distiller import distill, format_for_prompt


# ── Test Fixtures ──────────────────────────────────────────────────────────────

MERCHANT_M001_DENTIST_DELHI = {
    "merchant_id": "m_001_drmeera_dentist_delhi",
    "category_slug": "dentists",
    "identity": {
        "name": "Dr. Meera's Dental Clinic",
        "city": "Delhi",
        "locality": "Lajpat Nagar",
        "verified": True,
        "languages": ["en", "hi"],
        "owner_first_name": "Meera",
    },
    "subscription": {"status": "active", "plan": "Pro", "days_remaining": 82},
    "performance": {
        "window_days": 30,
        "views": 2410, "calls": 18, "directions": 45, "ctr": 0.021, "leads": 9,
        "delta_7d": {"views_pct": 0.18, "calls_pct": -0.05, "ctr_pct": 0.02},
    },
    "conversation_history": [
        {"ts": "2026-04-24T10:12:00Z", "from": "vera",
         "body": "Profile audit done — your photos are 8/10, description complete, but Google posts are stale (last post 22 days ago). Want me to draft 3 posts you can review?",
         "engagement": "merchant_replied"},
        {"ts": "2026-04-24T10:18:00Z", "from": "merchant",
         "body": "Yes please, focus on whitening and aligners", "engagement": "intent_action"},
    ],
    "customer_aggregate": {"total_unique_ytd": 540, "lapsed_180d_plus": 78,
                           "retention_6mo_pct": 0.38, "high_risk_adult_count": 124},
}

MERCHANT_M002_DENTIST_MUMBAI = {
    "merchant_id": "m_002_bharat_dentist_mumbai",
    "category_slug": "dentists",
    "identity": {
        "name": "Bharat Dental Care",
        "city": "Mumbai",
        "locality": "Andheri West",
        "verified": False,
        "languages": ["en", "hi", "mr"],
        "owner_first_name": "Bharat",
    },
    "subscription": {"status": "active", "plan": "Pro", "days_remaining": 12},
    "performance": {
        "window_days": 30,
        "views": 980, "calls": 4, "directions": 18, "ctr": 0.018, "leads": 2,
        "delta_7d": {"views_pct": -0.22, "calls_pct": -0.50, "ctr_pct": -0.10},
    },
    "conversation_history": [
        {"ts": "2026-04-10T11:00:00Z", "from": "vera",
         "body": "Subscription expires in 16 days — Bharat Dental Care...",
         "engagement": "merchant_no_reply"},
    ],
    "customer_aggregate": {"total_unique_ytd": 220, "lapsed_180d_plus": 95,
                           "retention_6mo_pct": 0.18},
}

MERCHANT_M005_RESTAURANT_DELHI = {
    "merchant_id": "m_005_pizzajunction_restaurant_delhi",
    "category_slug": "restaurants",
    "identity": {
        "name": "SK Pizza Junction",
        "city": "Delhi",
        "locality": "Sant Nagar",
        "verified": False,
        "languages": ["en", "hi"],
        "owner_first_name": "Suresh",
    },
    "subscription": {"status": "trial", "plan": "Trial", "days_remaining": 7},
    "performance": {
        "window_days": 30,
        "views": 2200, "calls": 12, "directions": 38, "ctr": 0.020, "leads": 4,
        "delta_7d": {"views_pct": 0.08, "calls_pct": 0.10},
    },
    "conversation_history": [
        {"ts": "2026-04-25T18:00:00Z", "from": "vera",
         "body": "Quick check — IPL match nights driving any extra footfall?",
         "engagement": "merchant_no_reply"},
    ],
    "customer_aggregate": {"delivery_orders_30d": 180, "dine_in_orders_30d": 95},
}

MERCHANT_M009_PHARMACY_JAIPUR = {
    "merchant_id": "m_009_apollo_pharmacy_jaipur",
    "category_slug": "pharmacies",
    "identity": {
        "name": "Apollo Health Plus Pharmacy",
        "city": "Jaipur",
        "locality": "Malviya Nagar",
        "verified": True,
        "languages": ["en", "hi"],
        "owner_first_name": "Ramesh",
    },
    "subscription": {"status": "active", "plan": "Pro", "days_remaining": 60},
    "performance": {
        "window_days": 30,
        "views": 1850, "calls": 38, "directions": 95, "ctr": 0.045, "leads": 24,
        "delta_7d": {"views_pct": 0.06, "calls_pct": 0.08},
    },
    "conversation_history": [
        {"ts": "2026-04-24T08:00:00Z", "from": "vera",
         "body": "Heads up: voluntary recall on atorvastatin batches AT2024-1102/1108 by MfrZ. Want the customer list filtered for that molecule?",
         "engagement": "merchant_replied"},
        {"ts": "2026-04-24T08:30:00Z", "from": "merchant",
         "body": "Yes send me the list please", "engagement": "intent_action"},
    ],
    "customer_aggregate": {"total_unique_ytd": 1820, "repeat_customer_pct": 0.68,
                           "chronic_rx_count": 240},
}

CUSTOMER_C013_GRANDFATHER = {
    "customer_id": "c_013_grandfather_for_m009",
    "merchant_id": "m_009_apollo_pharmacy_jaipur",
    "identity": {"name": "Mr. Sharma", "language_pref": "hi",
                 "age_band": "65-75", "senior_citizen": True},
    "relationship": {
        "first_visit": "2024-08-10", "last_visit": "2026-04-22",
        "visits_total": 24,
        "chronic_conditions": ["diabetes_t2", "hypertension", "dyslipidemia"],
        "lifetime_value": 24600,
    },
    "state": "active",
    "preferences": {"preferred_slots": "morning_delivery", "channel": "whatsapp_via_son",
                    "delivery_address": "saved"},
}

TRIGGER_CDE_WEBINAR = {
    "id": "trg_022_cde_webinar_dentists",
    "scope": "merchant",
    "kind": "cde_opportunity",
    "source": "external",
    "merchant_id": "m_001_drmeera_dentist_delhi",
    "customer_id": None,
    "payload": {"digest_item_id": "d_2026W17_ida_webinar", "credits": 2,
                "fee": "free_for_members"},
    "urgency": 1,
    "suppression_key": "cde:dentists:2026-05-02",
    "expires_at": "2026-05-02T19:00:00+05:30",
}

TRIGGER_IPL_WEEKEND = {
    "id": "trg_010_ipl_match_delhi",
    "scope": "merchant",
    "kind": "ipl_match_today",
    "source": "external",
    "merchant_id": "m_005_pizzajunction_restaurant_delhi",
    "customer_id": None,
    "payload": {
        "match": "DC vs MI",
        "venue": "Arun Jaitley Stadium",
        "city": "Delhi",
        "match_time_iso": "2026-04-26T19:30:00+05:30",
        "is_weeknight": False,  # Sunday — critical: should NOT push a promo
    },
    "urgency": 3,
    "suppression_key": "ipl:m_005:2026-04-26",
}

TRIGGER_PERF_DIP_CALLS = {
    "id": "trg_004_perf_dip_bharat",
    "scope": "merchant",
    "kind": "perf_dip",
    "source": "internal",
    "merchant_id": "m_002_bharat_dentist_mumbai",
    "customer_id": None,
    "payload": {
        "metric": "calls",
        "delta_pct": -0.50,
        "window": "7d",
        "vs_baseline": 12,
    },
    "urgency": 4,
    "suppression_key": "perf_dip:m_002_bharat_dentist_mumbai:calls:2026-W17",
}

TRIGGER_CHRONIC_REFILL_PHARMACY = {
    "id": "trg_019_chronic_refill_grandfather",
    "scope": "customer",
    "kind": "chronic_refill_due",
    "source": "internal",
    "merchant_id": "m_009_apollo_pharmacy_jaipur",
    "customer_id": "c_013_grandfather_for_m009",
    "payload": {
        "molecule_list": ["metformin", "atorvastatin", "telmisartan"],
        "last_refill": "2026-03-26",
        "stock_runs_out_iso": "2026-04-28T00:00:00+05:30",
        "delivery_address_saved": True,
    },
    "urgency": 3,
    "suppression_key": "refill:c_013_grandfather_for_m009:2026-04",
}


# ── Helper ─────────────────────────────────────────────────────────────────────

def _compose_timed(trigger, merchant, customer=None):
    """Import compose lazily so tests without ANTHROPIC_API_KEY skip cleanly."""
    from composer import compose
    t0 = time.monotonic()
    result = compose(trigger=trigger, merchant=merchant, customer=customer)
    elapsed = time.monotonic() - t0
    return result, elapsed


# ── Test 1: CDE Webinar → knowledge_digest ────────────────────────────────────

@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set",
)
def test_cde_webinar_knowledge_digest():
    """CDE opportunity → knowledge_digest profile, dentist, Dr. salutation."""
    result, elapsed = _compose_timed(TRIGGER_CDE_WEBINAR, MERCHANT_M001_DENTIST_DELHI)

    assert elapsed < 10, f"compose() took {elapsed:.1f}s — must be <10s"
    assert result.profile_id == "knowledge_digest"
    assert result.send_as == "vera"

    body_lower = result.body.lower()
    # Must reference dentist-appropriate content (credits, CDE, IDA, or webinar)
    assert any(kw in body_lower for kw in ["cde", "credit", "webinar", "ida", "workshop"]), \
        f"Body missing CDE anchor: {result.body}"

    # No URL in body
    assert "http" not in body_lower and "www." not in body_lower, \
        f"URL found in body: {result.body}"

    # Should address Dr. Meera
    assert "meera" in body_lower or "dr." in body_lower, \
        f"Doctor salutation missing: {result.body}"

    print(f"\n[T22 CDE] body: {result.body}")
    print(f"[T22 CDE] cta: {result.cta}")
    print(f"[T22 CDE] latency: {result.latency_ms}ms")


# ── Test 2: IPL Weekend → event_seasonal contrarian ──────────────────────────

@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set",
)
def test_ipl_weekend_contrarian():
    """
    IPL match on Sunday (is_weeknight=False) — Vera must NOT push a promo.
    Instead she should advise against it and mention the weeknight uplift.
    This is the critical contrarian insight the judge scores highest.
    """
    result, elapsed = _compose_timed(TRIGGER_IPL_WEEKEND, MERCHANT_M005_RESTAURANT_DELHI)

    assert elapsed < 10, f"compose() took {elapsed:.1f}s"
    assert result.profile_id == "event_seasonal"

    body_lower = result.body.lower()

    # MUST NOT push a promo for Sunday IPL
    promo_push_words = ["run a promo", "launch a promo", "ipl offer", "special offer tonight",
                        "combo tonight", "push a deal"]
    for phrase in promo_push_words:
        assert phrase not in body_lower, \
            f"ANTI-PATTERN: IPL promo pushed on Sunday — '{phrase}' found in: {result.body}"

    # MUST reference weekend covers dip or advise against / save for weeknight
    contrarian_signals = ["-12", "12%", "weeknight", "tue", "wed", "thu", "next match",
                          "skip", "avoid", "save", "weekend"]
    assert any(sig in body_lower for sig in contrarian_signals), \
        f"Missing contrarian insight (weekend = -12% covers): {result.body}"

    print(f"\n[T10 IPL] body: {result.body}")
    print(f"[T10 IPL] cta: {result.cta}")
    print(f"[T10 IPL] latency: {result.latency_ms}ms")


# ── Test 3: Perf dip calls −50% → perf_dip_recovery ─────────────────────────

@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set",
)
def test_perf_dip_calls_50pct():
    """Perf dip − 50% calls → body must cite the exact number, single diagnosis."""
    result, elapsed = _compose_timed(TRIGGER_PERF_DIP_CALLS, MERCHANT_M002_DENTIST_MUMBAI)

    assert elapsed < 10, f"compose() took {elapsed:.1f}s"
    assert result.profile_id == "perf_dip_recovery"
    assert result.send_as == "vera"

    body_lower = result.body.lower()

    # Must cite specific metric delta (50% or 50)
    assert "50" in result.body, \
        f"Specific −50% delta not cited in body: {result.body}"

    # Must mention calls
    assert "call" in body_lower, f"Metric 'calls' not mentioned: {result.body}"

    # Must NOT be alarming ("you're losing!" panic framing)
    alarm_words = ["you're losing customers", "disaster", "critical failure", "urgent action"]
    for word in alarm_words:
        assert word not in body_lower, f"Alarm framing detected: '{word}' in {result.body}"

    # CTA must be a single open-ended question (not a list)
    assert "?" in result.cta, f"CTA is not a question: {result.cta}"

    print(f"\n[T04 DIP] body: {result.body}")
    print(f"[T04 DIP] cta: {result.cta}")
    print(f"[T04 DIP] latency: {result.latency_ms}ms")


# ── Test 4: Chronic refill pharmacy → customer_winback ───────────────────────

@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set",
)
def test_chronic_refill_pharmacy():
    """
    Chronic refill for pharmacy customer (Hindi language pref, Jaipur city).
    signal_classifier must route to customer_winback (not customer_recall —
    chronic_refill_due on PHARMACY stays as customer_winback).
    Message must honor Hindi language preference.
    """
    result, elapsed = _compose_timed(
        TRIGGER_CHRONIC_REFILL_PHARMACY,
        MERCHANT_M009_PHARMACY_JAIPUR,
        customer=CUSTOMER_C013_GRANDFATHER,
    )

    assert elapsed < 10, f"compose() took {elapsed:.1f}s"

    # Pharmacy chronic_refill → customer_winback (NOT customer_recall)
    assert result.profile_id == "customer_winback", \
        f"Expected customer_winback, got {result.profile_id}"

    # Customer name must appear
    body_lower = result.body.lower()
    assert "sharma" in body_lower or "mr." in body_lower, \
        f"Customer name missing from body: {result.body}"

    # No URL
    assert "http" not in body_lower and "www." not in body_lower

    # Binary CTA expected for hard winback / refill
    cta_lower = result.cta.lower()
    binary_signals = ["yes", "no", "confirm", "call", "deliver", "book", "reply"]
    assert any(sig in cta_lower for sig in binary_signals), \
        f"Binary CTA missing for refill trigger: {result.cta}"

    print(f"\n[T19 REFILL] body: {result.body}")
    print(f"[T19 REFILL] cta: {result.cta}")
    print(f"[T19 REFILL] send_as: {result.send_as}")
    print(f"[T19 REFILL] latency: {result.latency_ms}ms")


# ── Test 5: Validator must catch URL in body ──────────────────────────────────

def test_validator_catches_url_in_body():
    """
    Validator hard check: URL in body is a −3 penalty.
    This test does NOT call the LLM — it runs the validator directly
    with a deliberately malformed composed dict.
    Must fail with ok=False and an error mentioning URL.
    """
    bad_composed = {
        "body": "Bharat, calls down 50% this week — check magicpin.in/dashboard for recovery tips.",
        "cta": "Want me to diagnose what's driving it?",
        "send_as": "vera",
        "rationale": "Test rationale",
    }

    trigger = {
        "kind": "perf_dip",
        "payload": {"metric": "calls", "delta_pct": -0.50, "window": "7d", "vs_baseline": 12},
        "merchant_id": "m_002_bharat_dentist_mumbai",
    }

    merchant = {
        "merchant_id": "m_002_bharat_dentist_mumbai",
        "category_slug": "dentists",
        "identity": {"owner_first_name": "Bharat", "languages": ["en", "hi"], "city": "Mumbai"},
        "performance": {"views": 980, "calls": 4, "ctr": 0.018,
                        "delta_7d": {"calls_pct": -0.50}},
    }

    vr = validate(
        composed=bad_composed,
        distilled_ctx={},
        trigger=trigger,
        merchant=merchant,
        customer=None,
        profile_cta_type="open_ended",
    )

    assert not vr.ok, "Validator should have flagged URL in body as error"
    error_text = " ".join(vr.errors).lower()
    assert "url" in error_text or "link" in error_text or "http" in error_text, \
        f"URL error not reported. Errors: {vr.errors}"

    print(f"\n[VALIDATOR] errors: {vr.errors}")
    print(f"[VALIDATOR] reprompt: {vr.reprompt_instruction}")


# ── Test 5b: Validator catches jargon (suppression_key in body) ───────────────

def test_validator_catches_jargon():
    """
    Validator catches internal jargon (suppression_key, trigger_id) in body.
    Another no-LLM validator-only test.
    """
    bad_composed = {
        "body": "Bharat, calls down 50% — suppression_key: perf_dip:m_002:calls:2026-W17. One fix?",
        "cta": "Want me to diagnose?",
        "send_as": "vera",
        "rationale": "Test",
    }

    trigger = {
        "kind": "perf_dip",
        "payload": {"metric": "calls", "delta_pct": -0.50, "window": "7d", "vs_baseline": 12},
        "merchant_id": "m_002_bharat_dentist_mumbai",
    }

    merchant = {
        "merchant_id": "m_002_bharat_dentist_mumbai",
        "category_slug": "dentists",
        "identity": {"owner_first_name": "Bharat", "languages": ["en"], "city": "Mumbai"},
        "performance": {"calls": 4, "delta_7d": {"calls_pct": -0.50}},
    }

    vr = validate(
        composed=bad_composed,
        distilled_ctx={},
        trigger=trigger,
        merchant=merchant,
        profile_cta_type="open_ended",
    )

    assert not vr.ok, "Validator should have flagged jargon in body"
    error_text = " ".join(vr.errors).lower()
    assert "jargon" in error_text or "suppression" in error_text or "internal" in error_text, \
        f"Jargon error not reported. Errors: {vr.errors}"

    print(f"\n[VALIDATOR JARGON] errors: {vr.errors}")


# ── Test: signal_classifier edge cases (no LLM) ───────────────────────────────

def test_classifier_chronic_refill_pharmacy():
    """chronic_refill_due on pharmacy → customer_winback (normal path)."""
    trigger = {"kind": "chronic_refill_due", "payload": {}}
    merchant = {"category_slug": "pharmacies"}
    clf = classify(trigger, merchant)
    assert clf.profile_id == "customer_winback"
    assert not clf.is_category_mismatch


def test_classifier_chronic_refill_non_pharmacy():
    """chronic_refill_due on dentist → customer_recall (edge case reframe)."""
    trigger = {"kind": "chronic_refill_due", "payload": {}}
    merchant = {"category_slug": "dentists"}
    clf = classify(trigger, merchant)
    assert clf.profile_id == "customer_recall"
    assert clf.is_category_mismatch


def test_classifier_seasonal_dip_flagged():
    """perf_dip with is_expected_seasonal=True → is_seasonal_dip=True."""
    trigger = {"kind": "perf_dip", "payload": {"is_expected_seasonal": True}}
    merchant = {"category_slug": "gyms"}
    clf = classify(trigger, merchant)
    assert clf.profile_id == "perf_dip_recovery"
    assert clf.is_seasonal_dip


def test_classifier_ipl_routes_event_seasonal():
    """ipl_match_today → event_seasonal."""
    trigger = {"kind": "ipl_match_today", "payload": {"is_weeknight": False}}
    merchant = {"category_slug": "restaurants"}
    clf = classify(trigger, merchant)
    assert clf.profile_id == "event_seasonal"
