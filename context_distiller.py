"""
context_distiller.py — Distills raw 4-context data into 3-5 key facts.

Instead of dumping thousands of tokens of raw JSON into the LLM,
this module extracts only what matters for the specific trigger:
  1. Best specificity anchor (numbers, dates, names from trigger payload)
  2. Merchant performance delta vs category peer stats
  3. Memory trace (last topic + engagement state)
  4. Customer facts (name, language, state, history) — if applicable
  5. Category seasonal / digest relevance — if applicable

Output is a flat dict ("DistilledContext") passed as the user message to the composer.
"""

from __future__ import annotations
from datetime import datetime, timezone


# Category peer stats (fallback when category context not loaded)
_PEER_STATS: dict[str, dict] = {
    "dentists":    {"avg_ctr": 0.030, "avg_rating": 4.4, "avg_reviews": 62,  "avg_views_30d": 1820},
    "salons":      {"avg_ctr": 0.040, "avg_rating": 4.5, "avg_reviews": 88,  "avg_views_30d": 2400},
    "restaurants": {"avg_ctr": 0.025, "avg_rating": 4.2, "avg_reviews": 142, "avg_views_30d": 4800},
    "gyms":        {"avg_ctr": 0.045, "avg_rating": 4.5, "avg_reviews": 56,  "avg_views_30d": 1100},
    "pharmacies":  {"avg_ctr": 0.038, "avg_rating": 4.6, "avg_reviews": 42,  "avg_views_30d": 1400},
}

# Category voice fingerprints (taboos + key vocab)
_CATEGORY_VOICE: dict[str, dict] = {
    "dentists": {
        "register": "clinical/authority — peer dentist",
        "salutation": "Dr.",
        "taboos": ["AMAZING DEAL", "guaranteed results", "best dental clinic", "cure", "guaranteed"],
        "vocab": ["fluoride varnish", "caries", "periodontal", "mSv", "DCI circular", "JIDA"],
        "emoji": "",
    },
    "salons": {
        "register": "warm-practical — craft knowledgeable",
        "salutation": "",
        "taboos": ["miracle transformation", "guaranteed glow", "instant results"],
        "vocab": ["keratin", "balayage", "threading", "bridal", "Olaplex", "slot"],
        "emoji": "✂️",
    },
    "restaurants": {
        "register": "peer/operator — data-driven",
        "salutation": "",
        "taboos": ["amazing food deals", "guaranteed packed house", "viral restaurant"],
        "vocab": ["covers", "AOV", "table turnover", "match-night", "thali", "delivery"],
        "emoji": "",
    },
    "gyms": {
        "register": "coach-to-owner — energetic",
        "salutation": "",
        "taboos": ["guaranteed weight loss", "shred in 7 days", "fastest results"],
        "vocab": ["churn", "PT sessions", "trial-to-paid", "HIIT", "membership", "active members"],
        "emoji": "",
    },
    "pharmacies": {
        "register": "trustworthy-precise — compliance-first",
        "salutation": "Namaste",
        "taboos": ["miracle cure", "best pharmacy", "doctor recommended"],
        "vocab": ["Schedule H1", "CDSCO", "molecule", "batch", "chronic-Rx", "delivery"],
        "emoji": "",
    },
}

# Category offer catalog defaults (when merchant has no active offers)
_OFFER_DEFAULTS: dict[str, list[str]] = {
    "dentists":    ["Dental Cleaning @ ₹299", "Teeth Whitening @ ₹1,499", "Free Consultation"],
    "salons":      ["Hair Spa @ ₹499", "Keratin Treatment @ ₹2,499", "Haircut @ ₹99"],
    "restaurants": ["Weekday Lunch Thali @ ₹149", "Family Sunday Brunch @ ₹699/pax"],
    "gyms":        ["First Month @ ₹499", "3 FREE Trial Classes", "Personal Training Demo @ ₹199"],
    "pharmacies":  ["Free Home Delivery > ₹499", "Senior Citizen 15% OFF"],
}

# Seasonal beats per category (month number → beat note)
_SEASONAL_BEATS: dict[str, dict[tuple[int, ...], str]] = {
    "dentists": {
        (11, 12, 1, 2): "exam-stress bruxism spike +30% ortho (18-24 cohort)",
        (10, 11, 12):   "wedding whitening peak (2x baseline)",
        (1,):           "new-year resolution +40% check-ups",
        (4, 5, 6):      "school holiday +50% pediatric window",
    },
    "salons": {
        (10, 11, 12):  "4x baseline bridal season (Oct-Dec)",
        (4, 5):        "secondary bridal + summer haircare",
        (7, 8):        "monsoon anti-frizz + scalp treatments",
        (3,):          "post-Holi colour-recovery surge",
    },
    "restaurants": {
        (3, 4, 5):   "IPL Tue/Wed/Thu weeknight match surge +18% covers",
        (10, 11):    "Diwali corporate gifting + family feasts",
        (12,):       "Christmas/New Year set menus (3x baseline)",
        (7, 8):      "monsoon delivery surge",
    },
    "gyms": {
        (1,):       "resolution surge — trial walk-ins 4x",
        (4, 5, 6):  "LOWEST acquisition window — focus retention only",
        (8, 9, 10): "wedding-prep + festival return surge",
        (11, 12):   "holiday slowdown — pilot new programs",
    },
    "pharmacies": {
        (4, 5, 6):  "ORS +40%, sunscreen +38%, antifungal +45%, cold/cough -60%",
        (7, 8):     "monsoon antibacterial/antifungal/immunity peak",
        (10, 11):   "festival sweets → diabetic monitoring surge",
        (12, 1):    "respiratory peak 2x cough/cold/anti-allergic",
    },
}


def _get_seasonal_note(category: str, month: int | None = None) -> str:
    if month is None:
        month = datetime.now().month
    beats = _SEASONAL_BEATS.get(category, {})
    for months, note in beats.items():
        if month in months:
            return note
    return ""


def _peer_delta(merchant: dict, category: str) -> dict:
    """Calculate CTR delta vs category peer."""
    perf = merchant.get("performance", {}) or {}
    merchant_ctr = perf.get("ctr", 0.0)
    peer = _PEER_STATS.get(category, {})
    peer_ctr = peer.get("avg_ctr", 0.03)
    delta = merchant_ctr - peer_ctr
    pct = round(delta / peer_ctr * 100) if peer_ctr else 0
    return {
        "merchant_ctr": merchant_ctr,
        "peer_ctr": peer_ctr,
        "ctr_delta": round(delta, 4),
        "ctr_delta_pct": pct,
        "ctr_status": "above" if delta > 0 else ("at" if delta == 0 else "below"),
    }


def _extract_trigger_anchor(trigger: dict, category_ctx: dict | None) -> str:
    """
    Pull the single strongest specificity anchor from the trigger payload.
    Returns a descriptive string, NOT a data structure.
    """
    kind = trigger.get("kind", "")
    payload = trigger.get("payload", {}) or {}
    is_placeholder = payload.get("placeholder", False)

    if is_placeholder:
        return f"[placeholder trigger — kind={kind}; derive anchor from merchant performance + category data]"

    # Kind-specific extraction
    if kind in ("research_digest", "regulation_change", "cde_opportunity", "supply_alert"):
        item_id = payload.get("top_item_id") or payload.get("digest_item_id", "")
        deadline = payload.get("deadline_iso", "")
        credits = payload.get("credits", "")
        fee = payload.get("fee", "")
        molecule = payload.get("molecule", "")
        batches = payload.get("affected_batches", "")

        # Look up digest item in category context
        anchor_parts = []
        if category_ctx:
            for item in category_ctx.get("digest", []):
                if item.get("id") == item_id:
                    src = item.get("source", "")
                    n = item.get("trial_n", "")
                    title = item.get("title", "")
                    seg = item.get("patient_segment", "")
                    anchor_parts.append(f"{src}: {title}" + (f" (n={n}, {seg})" if n else ""))
                    break
        if deadline:
            anchor_parts.append(f"deadline {deadline}")
        if credits:
            anchor_parts.append(f"{credits} CDE credits, {fee}")
        if molecule:
            anchor_parts.append(f"molecule: {molecule}, batches: {batches}")
        return " | ".join(anchor_parts) if anchor_parts else f"trigger kind={kind}, item={item_id}"

    elif kind in ("perf_dip", "seasonal_perf_dip", "perf_spike"):
        metric = payload.get("metric", "")
        delta = payload.get("delta_pct", "")
        window = payload.get("window", "7d")
        baseline = payload.get("vs_baseline", "")
        driver = payload.get("likely_driver", "")
        seasonal = payload.get("is_expected_seasonal", False)
        s_note = payload.get("season_note", "")

        parts = []
        if metric and delta != "":
            sign = "+" if isinstance(delta, (int, float)) and delta > 0 else ""
            parts.append(f"{metric} {sign}{delta:.0%} vs baseline {baseline} over {window}")
        if driver:
            parts.append(f"likely driver: {driver}")
        if seasonal and s_note:
            parts.append(f"seasonal context: {s_note}")
        return " | ".join(parts) if parts else f"{kind}: {metric}"

    elif kind == "milestone_reached":
        metric = payload.get("metric", "")
        value_now = payload.get("value_now", "")
        milestone = payload.get("milestone_value", "")
        imminent = payload.get("is_imminent", False)
        if metric and value_now:
            gap = ""
            if imminent and isinstance(value_now, (int, float)) and isinstance(milestone, (int, float)):
                gap = f" ({int(milestone - value_now)} away from {milestone})"
            return f"{metric}: {value_now}{gap}"
        return f"milestone trigger (no specifics)"

    elif kind == "competitor_opened":
        name = payload.get("competitor_name", "")
        dist = payload.get("distance_km", "")
        offer = payload.get("their_offer", "")
        date = payload.get("opened_date", "")
        if name:
            return f"{name} opened {dist}km away on {date} — their offer: {offer}"
        return "[placeholder competitor — use merchant's own strengths as anchor]"

    elif kind in ("festival_upcoming", "category_seasonal"):
        festival = payload.get("festival", payload.get("season", ""))
        date = payload.get("date", "")
        days_until = payload.get("days_until", "")
        trends = payload.get("trends", [])
        if festival:
            return f"{festival} on {date} ({days_until} days); category_relevance={payload.get('category_relevance', [])}"
        if trends:
            return "Seasonal trends: " + ", ".join(trends)
        return "[placeholder seasonal trigger]"

    elif kind == "ipl_match_today":
        match = payload.get("match", "")
        time_iso = payload.get("match_time_iso", "")
        is_weeknight = payload.get("is_weeknight", True)
        venue = payload.get("venue", "")
        day_type = "WEEKNIGHT (+18% covers)" if is_weeknight else "WEEKEND (-12% covers — ADVISE AGAINST promo)"
        return f"IPL: {match} at {venue} on {time_iso} — {day_type}"

    elif kind == "gbp_unverified":
        uplift = payload.get("estimated_uplift_pct", 0.3)
        path = payload.get("verification_path", "postcard_or_phone_call")
        return f"GBP unverified; +{uplift*100:.0f}% call uplift after verification via {path} (5-day process)"

    elif kind == "dormant_with_vera":
        days = payload.get("days_since_last_merchant_message", payload.get("days_dormant", ""))
        last = payload.get("last_topic", "")
        return f"{days} days dormant; last topic: {last or 'unknown'}"

    elif kind in ("recall_due", "appointment_tomorrow"):
        service = payload.get("service_due", "")
        due = payload.get("due_date", "")
        slots = payload.get("available_slots", [])
        slot_str = ""
        if slots:
            slot_labels = [s.get("label", "") for s in slots[:2]]
            slot_str = " | Slots: " + ", ".join(slot_labels)
        return f"Service due: {service}, due {due}{slot_str}"

    elif kind in ("chronic_refill_due",):
        molecules = payload.get("molecule_list", [])
        runs_out = payload.get("stock_runs_out_iso", "")
        delivery = payload.get("delivery_address_saved", False)
        return (
            f"Molecules: {', '.join(molecules) if molecules else 'not specified'}; "
            f"stock runs out: {runs_out or 'unknown'}; "
            f"delivery address saved: {delivery}"
        )

    elif kind in ("customer_lapsed_soft", "customer_lapsed_hard"):
        days = payload.get("days_since_last_visit", "")
        focus = payload.get("previous_focus", "")
        months = payload.get("previous_membership_months", "")
        parts = []
        if days:
            parts.append(f"{days} days since last visit")
        if focus:
            parts.append(f"previous focus: {focus}")
        if months:
            parts.append(f"{months} months membership")
        return " | ".join(parts) if parts else f"{kind} trigger"

    elif kind in ("curious_ask_due",):
        template = payload.get("ask_template", "")
        last_ask = payload.get("last_ask_at")
        return f"Curious ask template: {template}; last asked: {last_ask or 'never'}"

    elif kind == "active_planning_intent":
        topic = payload.get("intent_topic", "")
        last_msg = payload.get("merchant_last_message", "")
        return f"Planning intent: {topic}; merchant said: \"{last_msg}\""

    elif kind in ("renewal_due",):
        days = payload.get("days_remaining", payload.get("days_since_expiry", ""))
        uplift = payload.get("estimated_uplift_pct", "")
        return f"Renewal: {days} days remaining/since expiry; estimated uplift: {uplift}"

    elif kind == "review_theme_emerged":
        theme = payload.get("theme", "")
        count = payload.get("occurrences_30d", "")
        quote = payload.get("common_quote", "")
        sentiment = payload.get("sentiment", "")
        return f"Review theme: '{theme}' ({sentiment}, {count} times in 30d); example: \"{quote}\""

    elif kind == "winback_eligible":
        lapsed = payload.get("lapsed_count", "")
        uplift = payload.get("estimated_uplift_pct", "")
        return f"{lapsed} lapsed customers eligible for winback; estimated uplift: {uplift}%"

    elif kind in ("trial_followup", "wedding_package_followup"):
        trial_date = payload.get("trial_date", "")
        next_opts = payload.get("next_session_options", [])
        wedding_date = payload.get("wedding_date", "")
        days_to_wedding = payload.get("days_to_wedding", "")
        if wedding_date:
            return f"Wedding: {wedding_date} ({days_to_wedding} days away)"
        return f"Trial on {trial_date}; next options: {next_opts}"

    # Fallback
    return f"trigger kind={kind}; payload keys: {list(payload.keys())}"


def distill(
    trigger: dict,
    merchant: dict,
    customer: dict | None,
    category_ctx: dict | None,
    trace: dict | None = None,
) -> dict:
    """
    Distill 4 raw contexts into 3-5 key facts for the composer prompt.

    Returns a DistilledContext dict with keys:
      - trigger_anchor   : best specificity anchor
      - peer_delta       : merchant CTR vs peer (dict)
      - merchant_summary : name, owner, city, subscription, key signals
      - category_voice   : voice register, taboos, key vocab
      - memory_trace     : last topic, engagement, session state
      - customer_summary : customer facts (if applicable)
      - seasonal_note    : current seasonal context
      - active_offer     : best active offer or category default
      - is_placeholder   : bool — LOW confidence flag
    """
    kind = trigger.get("kind", "")
    payload = trigger.get("payload", {}) or {}
    is_placeholder = payload.get("placeholder", False)

    # Resolve category
    category = merchant.get("category_slug") or merchant.get("category", "")
    if category_ctx:
        category = category_ctx.get("slug", category)
    category = category.lower().replace(" ", "")
    # Normalize
    if "dentist" in category:
        category = "dentists"
    elif "salon" in category or "beauty" in category:
        category = "salons"
    elif "restaurant" in category or "cafe" in category or "food" in category:
        category = "restaurants"
    elif "gym" in category or "fitness" in category or "yoga" in category:
        category = "gyms"
    elif "pharma" in category or "medico" in category or "medical" in category:
        category = "pharmacies"

    voice = _CATEGORY_VOICE.get(category, _CATEGORY_VOICE["dentists"])
    peer = _peer_delta(merchant, category)
    trigger_anchor = _extract_trigger_anchor(trigger, category_ctx)
    seasonal_note = _get_seasonal_note(category)

    # Merchant summary
    identity = merchant.get("identity", {}) or {}
    subscription = merchant.get("subscription", {}) or {}
    performance = merchant.get("performance", {}) or {}
    signals = merchant.get("signals", []) or []
    customer_agg = merchant.get("customer_aggregate", {}) or {}
    review_themes = merchant.get("review_themes", []) or []

    owner_name = (
        identity.get("name") or merchant.get("owner") or
        merchant.get("identity", {}).get("name", "")
    )
    merchant_name = merchant.get("name") or identity.get("name", "")
    city = identity.get("city") or merchant.get("city", "")
    locality = identity.get("locality") or merchant.get("locality", "")
    languages = identity.get("languages") or merchant.get("languages", ["en"])
    sub_status = subscription.get("status", "unknown")
    sub_days = subscription.get("days_remaining", 0)

    # Active offers: prefer merchant data, fall back to category defaults
    offers_raw = merchant.get("offers") or merchant.get("active_offers") or []
    active_offers: list[str] = []
    if offers_raw:
        for o in offers_raw:
            if isinstance(o, dict) and o.get("status", "active") == "active":
                active_offers.append(o.get("title", ""))
            elif isinstance(o, str):
                active_offers.append(o)
    if not active_offers:
        active_offers = _OFFER_DEFAULTS.get(category, [])[:2]
        active_offers = [f"[default] {o}" for o in active_offers]

    # Key signals summary
    signal_str = ", ".join(signals[:4]) if signals else "no signals"

    # Review themes summary
    positive_themes = [t.get("theme") for t in review_themes if t.get("sentiment") == "pos"]
    negative_themes = [t.get("theme") for t in review_themes if t.get("sentiment") == "neg"]

    merchant_summary = {
        "merchant_id": merchant.get("merchant_id", ""),
        "name": merchant_name,
        "owner": owner_name,
        "city": city,
        "locality": locality,
        "languages": languages,
        "subscription_status": sub_status,
        "subscription_days_remaining": sub_days,
        "views_30d": performance.get("views", 0),
        "calls_30d": performance.get("calls", 0),
        "ctr": performance.get("ctr", 0),
        "delta_7d_calls_pct": performance.get("delta_7d", {}).get("calls_pct"),
        "delta_7d_views_pct": performance.get("delta_7d", {}).get("views_pct"),
        "signals": signal_str,
        "lapsed_customers": customer_agg.get("lapsed_180d_plus") or customer_agg.get("lapsed_90d_plus", 0),
        "total_ytd_customers": customer_agg.get("total_unique_ytd", 0),
        "chronic_rx_count": customer_agg.get("chronic_rx_count", 0),
        "high_risk_adult_count": customer_agg.get("high_risk_adult_count", 0),
        "active_members": customer_agg.get("total_active_members", 0),
        "positive_review_themes": positive_themes,
        "negative_review_themes": negative_themes,
        "active_offers": active_offers[:3],
    }

    # Customer summary (if applicable)
    customer_summary: dict | None = None
    if customer:
        c_identity = customer.get("identity", {}) or {}
        c_rel = customer.get("relationship", {}) or {}
        c_prefs = customer.get("preferences", {}) or {}
        customer_summary = {
            "customer_name": c_identity.get("name", ""),
            "language_pref": c_identity.get("language_pref", "en"),
            "age_band": c_identity.get("age_band", ""),
            "senior_citizen": c_identity.get("senior_citizen", False),
            "state": customer.get("state", ""),
            "visits_total": c_rel.get("visits_total", 0),
            "last_visit": c_rel.get("last_visit", ""),
            "services_received": c_rel.get("services_received", [])[:5],
            "lifetime_value": c_rel.get("lifetime_value", 0),
            "preferred_slots": c_prefs.get("preferred_slots", ""),
            "consent_scope": customer.get("consent", {}).get("scope", []),
        }

    # Memory trace
    trace_summary: dict = trace or {
        "last_topic": merchant.get("last_msg_topic"),
        "last_engagement": merchant.get("last_engagement", "cold"),
        "session_open": False,
    }

    return {
        "trigger_anchor": trigger_anchor,
        "trigger_kind": kind,
        "trigger_scope": trigger.get("scope", "merchant"),
        "trigger_urgency": trigger.get("urgency", 2),
        "suppression_key": trigger.get("suppression_key", ""),
        "expires_at": trigger.get("expires_at", ""),
        "is_placeholder": is_placeholder,
        "peer_delta": peer,
        "merchant_summary": merchant_summary,
        "category": category,
        "category_voice": voice,
        "seasonal_note": seasonal_note,
        "memory_trace": trace_summary,
        "customer_summary": customer_summary,
        "active_offers": active_offers,
    }


def format_for_prompt(ctx: dict) -> str:
    """
    Render the distilled context as a human-readable string for the LLM user message.
    Kept terse — no raw JSON dumps, only what matters.
    """
    lines: list[str] = []
    m = ctx["merchant_summary"]
    v = ctx["category_voice"]
    p = ctx["peer_delta"]
    trace = ctx["memory_trace"]

    # ── Trigger anchor ──
    lines.append(f"TRIGGER KIND: {ctx['trigger_kind']}")
    lines.append(f"TRIGGER ANCHOR: {ctx['trigger_anchor']}")
    if ctx["is_placeholder"]:
        lines.append("⚠ PLACEHOLDER TRIGGER — no specific numbers in payload; derive from merchant + category data")

    # ── Merchant ──
    lines.append(f"\nMERCHANT: {m['name']} | {m['owner']} | {m['city']}/{m['locality']}")
    lines.append(f"SUBSCRIPTION: {m['subscription_status']} ({m['subscription_days_remaining']}d remaining)")
    lines.append(
        f"PERFORMANCE: {m['views_30d']} views | {m['calls_30d']} calls | CTR {m['ctr']:.3f} "
        f"({p['ctr_status']} peer by {abs(p['ctr_delta_pct'])}%)"
    )
    if m["delta_7d_calls_pct"] is not None or m["delta_7d_views_pct"] is not None:
        calls_str = f"{m['delta_7d_calls_pct']:+.0%}" if m["delta_7d_calls_pct"] is not None else "n/a"
        views_str = f"{m['delta_7d_views_pct']:+.0%}" if m["delta_7d_views_pct"] is not None else "n/a"
        lines.append(f"7D DELTA: calls {calls_str} | views {views_str}")
    if m["signals"] != "no signals":
        lines.append(f"SIGNALS: {m['signals']}")
    if m["lapsed_customers"]:
        lines.append(f"LAPSED CUSTOMERS: {m['lapsed_customers']}")
    if m["chronic_rx_count"]:
        lines.append(f"CHRONIC-RX COUNT: {m['chronic_rx_count']}")
    if m["high_risk_adult_count"]:
        lines.append(f"HIGH-RISK ADULTS: {m['high_risk_adult_count']}")
    if m["active_members"]:
        lines.append(f"ACTIVE MEMBERS: {m['active_members']}")
    if m["active_offers"]:
        lines.append(f"ACTIVE OFFERS: {' | '.join(m['active_offers'])}")
    if m["positive_review_themes"]:
        lines.append(f"REVIEW THEMES (+): {', '.join(m['positive_review_themes'])}")
    if m["negative_review_themes"]:
        lines.append(f"REVIEW THEMES (-): {', '.join(m['negative_review_themes'])}")
    lines.append(f"LANGUAGES: {', '.join(m['languages'])}")

    # ── Category voice ──
    lines.append(f"\nCATEGORY: {ctx['category']} | VOICE: {v['register']}")
    lines.append(f"TABOO WORDS: {', '.join(v['taboos'])}")
    lines.append(f"KEY VOCAB: {', '.join(v['vocab'])}")
    if ctx["seasonal_note"]:
        lines.append(f"SEASONAL (current): {ctx['seasonal_note']}")

    # ── Memory trace ──
    lines.append(f"\nLAST TOPIC SENT: {trace.get('last_topic') or 'none (first message)'}")
    lines.append(f"LAST ENGAGEMENT: {trace.get('last_engagement', 'cold')}")
    lines.append(f"SESSION OPEN: {trace.get('session_open', False)}")

    # ── Customer (if applicable) ──
    if ctx.get("customer_summary"):
        c = ctx["customer_summary"]
        lines.append(f"\nCUSTOMER: {c['customer_name']} | {c['language_pref']} | age {c['age_band']}")
        lines.append(f"CUSTOMER STATE: {c['state']} | visits: {c['visits_total']} | LTV ₹{c['lifetime_value']}")
        if c["services_received"]:
            lines.append(f"SERVICES HISTORY: {', '.join(str(s) for s in c['services_received'])}")
        if c["preferred_slots"]:
            lines.append(f"PREFERRED SLOTS: {c['preferred_slots']}")
        if c["senior_citizen"]:
            lines.append("⚠ SENIOR CITIZEN — use namaste greeting, full molecule names, clear delivery details")
        lines.append(f"CONSENT SCOPE: {', '.join(c['consent_scope'])}")

    lines.append(f"\nSUPPRESSION KEY: {ctx['suppression_key']}")

    return "\n".join(lines)
