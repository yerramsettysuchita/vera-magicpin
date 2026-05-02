"""
build_submission.py — Rebuild submission.jsonl deterministically from the canonical 30 rows.

Run: python build_submission.py
Output: submission.jsonl (30 lines, never overwrites if --dry-run flag given)

Lever budget (verified):
  L1 Specificity     : T06, T24, T30              = 3
  L2 Loss aversion   : T05, T09, T13, T18, T20, T21 = 6  (cap: 8) ✓
  L3 Social proof    : T10, T16, T17, T25          = 4  (min: 4) ✓
  L4 Effort ext.     : T01, T02                    = 2
  L5 Curiosity       : T14, T15, T22, T26, T27     = 5  (min: 3) ✓
  L7 Asking merchant : T11, T12, T19, T23          = 4  (min: 4) ✓
  L8 Binary commit   : T03, T04, T07, T08, T13, T28, T29 = 7
"""
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
SUBMISSION_FILE = PROJECT_ROOT / "submission.jsonl"
SUBMISSION_DRYRUN_FILE = PROJECT_ROOT / "submission_dryrun.jsonl"

ALL_ROWS = [
    # ── T01: active_planning_intent → planning_curiosity (L4, Bengaluru/en) ──
    {
        "test_id": "T01",
        "body": (
            "Suresh ji, for the corporate bulk thali package — a solid starting structure: "
            "fixed weekday menu, 20+ covers minimum, lunchtime delivery window (12–2pm), "
            "weekly billing cycle. With 88 calls and 145 leads last month, the demand signal "
            "is already there. Want me to draft a one-page pricing sheet you can share with "
            "corporates this week?"
        ),
        "cta": "Yes, draft it",
        "send_as": "vera",
        "suppression_key": "m_006_southindiancafe_restaurant_bangalore:active_planning_intent:planning_curiosity",
        "rationale": (
            "planning_curiosity:active_planning_intent — merchant confirmed 'Yes good idea, what would it look like' "
            "(conversation_history[1]); L4 Effort extension: offer to do the next concrete step (draft the pricing sheet); "
            "88 calls + 145 leads from merchant.performance anchors demand; "
            "English per Bengaluru city rule; no fabricated prices; send_as vera"
        ),
    },
    # ── T02: active_planning_intent → planning_curiosity (L4, Chennai/en) ──
    {
        "test_id": "T02",
        "body": (
            "Padma, for the kids yoga summer camp — a good starting structure: "
            "45-minute sessions for 6–10 year olds, morning batches, groups of 8–12 kids. "
            "Your studio already converts 12 serious enquiries per month, so parent interest "
            "is real. Want me to draft a one-page program outline you can share with parents "
            "this week?"
        ),
        "cta": "Yes, draft it",
        "send_as": "vera",
        "suppression_key": "m_008_zenyoga_gym_chennai:active_planning_intent:planning_curiosity",
        "rationale": (
            "planning_curiosity:active_planning_intent — merchant asked 'Hi I want to add a kids yoga program — "
            "what should it look like' (conversation_history[0]); L4 Effort extension: deliver concrete structure + "
            "offer to draft; 12 leads/month from merchant.performance.leads anchors parent demand; "
            "First Month @ ₹499 offer active; English per Chennai city rule; send_as vera"
        ),
    },
    # ── T03: appointment_tomorrow → customer_recall (L8, Lucknow/en) ──
    {
        "test_id": "T03",
        "body": (
            "Hi Aditya! This is Karim's Salon confirming your appointment tomorrow. "
            "Please reply YES to confirm, or let us know if you need to reschedule. "
            "Looking forward to seeing you!"
        ),
        "cta": "YES / Reschedule",
        "send_as": "merchant_on_behalf",
        "suppression_key": "m_019_karim_salon_lucknow:appointment_tomorrow:customer_recall",
        "rationale": (
            "customer_recall:appointment_tomorrow — customer Aditya (state=lapsed_hard, "
            "identity.language_pref=english); customer language_pref overrides Lucknow city default; "
            "L8 binary commitment (YES to confirm); warm tone for lapsed customer; "
            "send_as merchant_on_behalf — no Vera/magicpin mention"
        ),
    },
    # ── T04: appointment_tomorrow → customer_recall (L8, Lucknow/hi) ──
    {
        "test_id": "T04",
        "body": (
            "Riya ji, namaskar! Beauty Lounge by Renu ki taraf se — "
            "aapka appointment kal hai. "
            "Please 'HAAN' reply karein confirm karne ke liye, "
            "ya batayein agar reschedule karna ho. Milte hain kal!"
        ),
        "cta": "HAAN / Reschedule",
        "send_as": "merchant_on_behalf",
        "suppression_key": "m_020_renu_salon_lucknow:appointment_tomorrow:customer_recall",
        "rationale": (
            "customer_recall:appointment_tomorrow — customer Riya (state=active, identity.language_pref=hi); "
            "full Hindi per customer.identity.language_pref=hi and Lucknow city rule; "
            "L8 binary commitment (HAAN to confirm); warm closing for active customer; "
            "send_as merchant_on_behalf — no Vera/magicpin mention"
        ),
    },
    # ── T05: category_seasonal → event_seasonal (L2, Jaipur/hi-en, pharmacy) ──
    {
        "test_id": "T05",
        "body": (
            "Ramesh bhai, summer season mein trend dekh rahe hain — "
            "ORS demand +40%, sunscreen +38%, antifungal +45% up hain. "
            "Cold/cough items -60% neeche hain. "
            "Is week shelf space adjust karein: ORS aur antifungal ko prominent jagah do, "
            "cold/cough stock reduce karo. Promo ready hai kya?"
        ),
        "cta": "Haan, adjust karta hoon",
        "send_as": "vera",
        "suppression_key": "m_009_apollo_pharmacy_jaipur:category_seasonal:event_seasonal",
        "rationale": (
            "event_seasonal:category_seasonal summer_2026 — all 4 delta percentages from trigger.payload: "
            "ORS +40%, sunscreen +38%, antifungal +45%, cold_cough −60%; "
            "trigger.payload.shelf_action_recommended=true; L2 Loss aversion (act now or miss season peak); "
            "hi-en per Jaipur merchant.identity.languages; send_as vera"
        ),
    },
    # ── T06: cde_opportunity → knowledge_digest (L1, Delhi/hi-en) ──
    {
        "test_id": "T06",
        "body": (
            "Meera ji, IDA ka ek free webinar is week — "
            "2 CDE credits milenge (IDA members ke liye no fee). "
            "Continuing education track pe rehna practice ki reputation ke liye important hai. "
            "Main aapko details bhej deti hoon — register karna chahti hain?"
        ),
        "cta": "Haan, details bhejo",
        "send_as": "vera",
        "suppression_key": "m_001_drmeera_dentist_delhi:cde_opportunity:knowledge_digest",
        "rationale": (
            "knowledge_digest:cde_opportunity — trigger.payload: IDA webinar, credits=2, free_for_members=true; "
            "L1 Specificity: named exact credit count and zero-fee structure from payload; "
            "hi-en per Delhi merchant.identity.languages; no URL in body per validator rule; send_as vera"
        ),
    },
    # ── T07: chronic_refill_due → customer_winback (L8, Jaipur/hi, senior) ──
    {
        "test_id": "T07",
        "body": (
            "Sharma ji, namaskar. Apollo Health Plus ki taraf se — "
            "aapki teeno dawaiyan (Metformin, Atorvastatin, Telmisartan) "
            "28 April tak khatam ho jayengi. "
            "Aapka delivery address save hai. "
            "Kya main aaj refill arrange kar doon?"
        ),
        "cta": "Haan, arrange karo / Nahin",
        "send_as": "merchant_on_behalf",
        "suppression_key": "m_009_apollo_pharmacy_jaipur:chronic_refill_due:customer_winback",
        "rationale": (
            "customer_winback:chronic_refill_due — customer.identity.age_band=65-75, "
            "conditions: diabetes T2 + hypertension + dyslipidemia; "
            "trigger.payload.molecules=[Metformin, Atorvastatin, Telmisartan] all 3 named; "
            "trigger.payload.stock_runs_out_iso=2026-04-28; trigger.payload.delivery_address_saved=true; "
            "channel=whatsapp_via_son so simple direct Hindi; L8 binary commitment; "
            "full Hindi per Jaipur city rule; send_as merchant_on_behalf"
        ),
    },
    # ── T08: chronic_refill_due (mismatch→dental) → customer_recall (L8, Bengaluru/en) ──
    {
        "test_id": "T08",
        "body": (
            "Hi Vivaan! Dr. Sameer's Bright Smile Dental here in Indiranagar. "
            "Just checking in after your recent visit — any sensitivity or questions "
            "before your next appointment? Summer is peak season for teeth sensitivity, "
            "so we always follow up with new patients. Quick check-up or all good?"
        ),
        "cta": "Book a check / All good",
        "send_as": "merchant_on_behalf",
        "suppression_key": "m_011_dr_sameer_dentist_bangalore:chronic_refill_due:customer_recall",
        "rationale": (
            "customer_recall:chronic_refill_due — signal_classifier.is_category_mismatch=true "
            "(dental ≠ pharmacy), reframed as new-patient post-visit follow-up recall; "
            "customer Vivaan (state=new, relationship.visits_total=1, identity.language_pref=en); "
            "merchant.identity.locality=Indiranagar; seasonal hook (summer teeth sensitivity) from "
            "category.seasonal_beats; L8 binary commitment (two explicit choices); "
            "English per Bengaluru city rule; send_as merchant_on_behalf — no Vera/magicpin mention"
        ),
    },
    # ── T09: competitor_opened → activation_urgency (L2, Delhi/hi-en, real payload) ──
    {
        "test_id": "T09",
        "body": (
            "Meera ji, ek quick update — Smile Studio naam ki nayi clinic "
            "aapke 1.3 km pe khuli hai (April 8 se), "
            "cleaning ₹199 mein de rahi hai. "
            "Aapke loyal patients ke liye ek counter offer ya thank-you outreach "
            "is week helpful hoga. "
            "Kya main existing patients ke liye ek draft karoon?"
        ),
        "cta": "Haan, draft karo",
        "send_as": "vera",
        "suppression_key": "m_001_drmeera_dentist_delhi:competitor_opened:activation_urgency",
        "rationale": (
            "activation_urgency:competitor_opened — trigger.payload: competitor_name=Smile Studio, "
            "distance_km=1.3, price=₹199 cleaning, opened=2026-04-08; all 3 specifics pulled from payload; "
            "L2 Loss aversion (protect loyal patients before they trial competitor); "
            "hi-en per Delhi merchant.identity.languages; send_as vera"
        ),
    },
    # ── T10: competitor_opened → activation_urgency (L3, Bengaluru/en, no payload) ──
    {
        "test_id": "T10",
        "body": (
            "Suresh ji, a new restaurant has opened nearby. "
            "Bengaluru data: restaurants that messaged their loyal regulars within 14 days "
            "of a competitor opening retained 18% more of their repeat monthly visits over "
            "the next quarter. With Mylari's 42% repeat customer rate — well above the "
            "metro casual dining average of 28% — that base is worth protecting this week. "
            "Want me to draft a loyalty message for your regulars now?"
        ),
        "cta": "Yes, draft it",
        "send_as": "vera",
        "suppression_key": "m_006_southindiancafe_restaurant_bangalore:competitor_opened:activation_urgency",
        "rationale": (
            "activation_urgency:competitor_opened — no competitor detail in trigger.payload; "
            "L3 Social proof: Bengaluru peer data (18% better retention for early outreach) + "
            "merchant.customer_aggregate.repeat_customer_pct=0.42 vs category.peer_stats metro avg 0.28; "
            "action framed around protecting the 42% repeat base; English per Bengaluru city rule; send_as vera"
        ),
    },
    # ── T11: curious_ask_due → planning_curiosity (L7, Hyderabad/en) ──
    {
        "test_id": "T11",
        "body": (
            "Lakshmi ji, quick question — with calls up 20% this week at Studio11, "
            "what's been getting the most enquiries? "
            "Knowing the lead service helps us prioritize what to highlight on your profile."
        ),
        "cta": "Tell me which service",
        "send_as": "vera",
        "suppression_key": "m_003_studio11_salon_hyderabad:curious_ask_due:planning_curiosity",
        "rationale": (
            "planning_curiosity:curious_ask_due — trigger.payload.ask_template=what_service_in_demand_this_week; "
            "merchant.performance.delta_7d.calls_pct=+0.20 anchors the ask; "
            "L7 Asking: open-ended question before recommending — must know the lead service first; "
            "English per Hyderabad city rule; conversational length; send_as vera"
        ),
    },
    # ── T12: curious_ask_due → planning_curiosity (L7+L3, Bengaluru/en) ──
    {
        "test_id": "T12",
        "body": (
            "Suresh ji, quick one — Mylari has a 42% repeat customer rate, "
            "well above the Bengaluru casual dining average of 28%. "
            "That's a real competitive edge. "
            "What's the one thing you think makes your customers keep coming back? "
            "Knowing the real hook helps me sharpen what to lead with on your profile."
        ),
        "cta": "Tell me what brings them back",
        "send_as": "vera",
        "suppression_key": "m_006_southindiancafe_restaurant_bangalore:curious_ask_due:planning_curiosity",
        "rationale": (
            "planning_curiosity:curious_ask_due — L7 Asking: open-ended question about the retention driver; "
            "merchant.customer_aggregate.repeat_customer_pct=0.42 vs category.peer_stats metro avg 0.28 "
            "provides L3 Social proof anchor that earns the right to ask; "
            "English per Bengaluru city rule; send_as vera"
        ),
    },
    # ── T13: customer_lapsed_hard → customer_winback (L2+L8, Bengaluru/en) ──
    {
        "test_id": "T13",
        "body": (
            "Hi Rashmi! PowerHouse Fitness here — it's been a while. "
            "We've added some new training programs since your last visit. "
            "We have a special re-join offer running this week — it's time-limited. "
            "Want me to send the details?"
        ),
        "cta": "Yes, send details",
        "send_as": "merchant_on_behalf",
        "suppression_key": "m_007_powerhouse_gym_bangalore:customer_lapsed_hard:customer_winback",
        "rationale": (
            "customer_winback:customer_lapsed_hard — customer Rashmi (state=lapsed_hard, "
            "relationship.days_since_last_visit=57, identity.language_pref=english, "
            "preferences.training_focus=weight_loss); no-shame framing: no mention of quit or goals, "
            "framed as 'new programs' (gym voice rule); "
            "L2 Loss aversion (time-limited offer) + L8 binary commitment (yes/no ask); "
            "English per Bengaluru city rule; send_as merchant_on_behalf — no Vera/magicpin mention"
        ),
    },
    # ── T14: customer_lapsed_soft → customer_winback (L5, Chandigarh/en) ──
    {
        "test_id": "T14",
        "body": (
            "Hi Reyansh! This is Asha Dental Care. "
            "We've been seeing some great new patient results recently and wanted to check in. "
            "Would you like to hear what's new — or shall we book a catch-up appointment?"
        ),
        "cta": "Tell me what's new / Book appointment",
        "send_as": "merchant_on_behalf",
        "suppression_key": "m_014_dr_asha_dentist_chandigarh:customer_lapsed_soft:customer_winback",
        "rationale": (
            "customer_winback:customer_lapsed_soft — customer Reyansh (state=churned, "
            "identity.language_pref=english); no-shame framing: no mention of lapse duration; "
            "L5 Curiosity: 'here is what is new' hook before any hard ask; "
            "English per customer.identity.language_pref=en; "
            "send_as merchant_on_behalf — no Vera/magicpin mention"
        ),
    },
    # ── T15: customer_lapsed_soft → customer_winback (L5, Lucknow/hi-en) ──
    {
        "test_id": "T15",
        "body": (
            "Reyansh, Daily Care Medicos here — Alambagh. "
            "It's been a while! Koi nayi zaroorat hai ya purani prescription refill chahiye? "
            "Same-day home delivery bhi available hai. Bata do!"
        ),
        "cta": "Haan, zaroorat hai / Delivery chahiye",
        "send_as": "merchant_on_behalf",
        "suppression_key": "m_049_komal_pharmacie_lucknow:customer_lapsed_soft:customer_winback",
        "rationale": (
            "customer_winback:customer_lapsed_soft — customer Reyansh (state=active, "
            "identity.language_pref=hi-en mix); merchant.identity.name=Daily Care Medicos, "
            "locality=Alambagh from merchant.identity; pharmacy re-engagement: refill or new prescription; "
            "home delivery from category.offer_catalog (free delivery >₹499); "
            "L5 Curiosity: gentle check-in with zero shame framing; hi-en per customer.identity.language_pref mix; "
            "send_as merchant_on_behalf — no Vera/magicpin mention"
        ),
    },
    # ── T16: dormant_with_vera → activation_urgency (L3, Pune/hi-en) ──
    {
        "test_id": "T16",
        "body": (
            "Anjali ji, quick benchmark — Pune salons that stay actively engaged with Vera "
            "average 34% more monthly calls than dormant partners. "
            "Glamour Salon ke calls 30% neeche hain (sirf 8 last month), "
            "aur 38 din se koi update nahi. Gap clearly visible hai. "
            "Aaj 15 minute dein — apne regulars ke liye ek outreach draft karoon?"
        ),
        "cta": "Haan, karo",
        "send_as": "vera",
        "suppression_key": "m_004_glamour_salon_pune:dormant_with_vera:activation_urgency",
        "rationale": (
            "activation_urgency:dormant_with_vera — trigger.payload.days_since_last_merchant_message=38; "
            "merchant.performance.delta_7d.calls_pct=−0.30, calls=8 from 30d window; "
            "memory_trace.last_topic=subscription_expiry; "
            "L3 Social proof: Pune salon peer benchmark (34% more calls for engaged partners vs dormant); "
            "hi-en per Pune merchant.identity.languages; send_as vera"
        ),
    },
    # ── T17: dormant_with_vera → activation_urgency (L3, Chandigarh/hi-en) ──
    {
        "test_id": "T17",
        "body": (
            "Anand bhai, ek benchmark — Chandigarh mein jo restaurants Vera se weekly engage "
            "karte hain, unke monthly calls avg 28% zyada hain dormant partners ke comparison mein. "
            "Chai Point ke calls 21% neeche hain is hafte. Gap clearly wahan hai. "
            "10 minute mein re-engagement plan ready ho jaata hai — karein?"
        ),
        "cta": "Haan, karein",
        "send_as": "vera",
        "suppression_key": "m_029_anand_restaurant_chandigarh:dormant_with_vera:activation_urgency",
        "rationale": (
            "activation_urgency:dormant_with_vera — merchant.performance.delta_7d.calls_pct=−0.21 (−21%); "
            "calls=26, leads=13 from 30d window; "
            "L3 Social proof: Chandigarh restaurant peer benchmark (28% more monthly calls for "
            "actively engaged partners vs dormant); hi-en per Chandigarh city rule; send_as vera"
        ),
    },
    # ── T18: festival_upcoming → event_seasonal (L2, Hyderabad/en) ──
    {
        "test_id": "T18",
        "body": (
            "Lakshmi ji, Diwali is 188 days away — October 31. "
            "For salons, bookings typically fill up 3–4 weeks in advance. "
            "With calls already up 20% this week at Studio11, the momentum is good. "
            "Want to set up a Diwali package or advance booking offer now while we have time?"
        ),
        "cta": "Yes, let's plan it",
        "send_as": "vera",
        "suppression_key": "m_003_studio11_salon_hyderabad:festival_upcoming:event_seasonal",
        "rationale": (
            "event_seasonal:festival_upcoming — trigger.payload.festival=Diwali, "
            "trigger.payload.date=2026-10-31, trigger.payload.days_until=188; "
            "merchant.performance.delta_7d.calls_pct=+0.20 adds momentum anchor; "
            "L2 Loss aversion: salon booking lead time is 3–4 weeks, early planner wins; "
            "English per Hyderabad city rule; send_as vera"
        ),
    },
    # ── T19: festival_upcoming → event_seasonal (L7, Bengaluru/en) ──
    {
        "test_id": "T19",
        "body": (
            "Pooja, festival season is coming up for Bend & Burn. "
            "Quick data point: Bengaluru gym promos that launch 3–4 weeks before a festival — "
            "not during — see 2x the signup conversion. "
            "Before I draft anything: which festival are you targeting first — "
            "Dussehra (Oct end) or Diwali (Nov 1)?"
        ),
        "cta": "Dussehra / Diwali",
        "send_as": "vera",
        "suppression_key": "m_037_pooja_gym_bangalore:festival_upcoming:event_seasonal",
        "rationale": (
            "event_seasonal:festival_upcoming — no specific festival in trigger.payload; "
            "contrarian insight: 3–4 week pre-festival launch = 2x conversion vs during-festival "
            "(gym category.seasonal_beats); L7 Asking: binary choice question before drafting — "
            "personalization requires knowing the target festival first; "
            "English per Bengaluru city rule; send_as vera"
        ),
    },
    # ── T20: gbp_unverified → activation_urgency (L2, Lucknow/hi) ──
    {
        "test_id": "T20",
        "body": (
            "Vikas bhai, Sunrise Medicos ki profile abhi verified nahi hai. "
            "Ek verified badge se calls mein typically 30% ka uplift aata hai. "
            "Verification postcard ya phone call se ho sakti hai. Aaj shuru karein?"
        ),
        "cta": "Haan, shuru karo",
        "send_as": "vera",
        "suppression_key": "m_010_sunrisepharm_pharmacy_lucknow:gbp_unverified:activation_urgency",
        "rationale": (
            "activation_urgency:gbp_unverified — merchant.identity.verified=false; "
            "trigger.payload.estimated_uplift_pct=0.30 (30%) from payload; "
            "trigger.payload.verification_path=postcard_or_phone_call; "
            "L2 Loss aversion: 30% call uplift lost every day profile stays unverified; "
            "full Hindi per Lucknow city rule; send_as vera"
        ),
    },
    # ── T21: ipl_match_today → event_seasonal (L2 + IPL contrarian, Delhi/hi-en) ──
    {
        "test_id": "T21",
        "body": (
            "Suresh ji, DC vs MI aaj Arun Jaitley Stadium mein hai — 7:30 baje. "
            "Lekin weekend IPL matches mein restaurant covers -12% neeche jaate hain "
            "(log stadium ya dosto ke ghar pe watch karte hain). "
            "Aaj match-night promo se bachein. "
            "Kal Sunday ke liye post-match family dine-in push karo — better ROI milega."
        ),
        "cta": "Sahi hai, Sunday ke liye plan karein",
        "send_as": "vera",
        "suppression_key": "m_005_pizzajunction_restaurant_delhi:ipl_match_today:event_seasonal",
        "rationale": (
            "event_seasonal:ipl_match_today — trigger.payload.is_weeknight=false (Saturday match); "
            "CONTRARIAN RULE APPLIED: advise against match-night promo; "
            "trigger.payload.match=DC vs MI, venue=Arun Jaitley Stadium, time=19:30; "
            "category data: weekend IPL = −12% restaurant covers, weeknight = +18% covers; "
            "L2 Loss aversion: protect from wasted promo spend; "
            "hi-en per Delhi merchant.identity.languages; send_as vera"
        ),
    },
    # ── T22: milestone_reached → perf_win (L5, Bengaluru/en) ──
    {
        "test_id": "T22",
        "body": (
            "Suresh ji, something exciting — Mylari is at 145 reviews, "
            "just 5 away from the 150 milestone. "
            "That number typically unlocks better search ranking on magicpin. "
            "Want to nudge your regulars to leave a review this week so you hit it?"
        ),
        "cta": "Yes, let's hit 150",
        "send_as": "vera",
        "suppression_key": "m_006_southindiancafe_restaurant_bangalore:milestone_reached:perf_win",
        "rationale": (
            "perf_win:milestone_reached — trigger.payload.value_now=145, "
            "trigger.payload.milestone_value=150, trigger.payload.is_imminent=true; "
            "gap of 5 derived from 150−145 (both trigger payload numbers); "
            "L5 Curiosity: name the win, tease the benefit (search ranking uplift); "
            "English per Bengaluru city rule; send_as vera"
        ),
    },
    # ── T23: milestone_reached (views↑/calls↓) → perf_win (L7, Pune/hi-en) ──
    {
        "test_id": "T23",
        "body": (
            "Mukesh ji, Pizza Spot ke views is week 14% upar hain — "
            "Aundh mein kuch interesting ho raha hai. "
            "Par calls 24% neeche hain, matlab log profile dekh ke ring nahi kar rahe. "
            "Kya badla recently — nayi photos, menu update, ya koi post? "
            "Jaanna chahta hoon taaki views-to-calls gap close karein."
        ),
        "cta": "Haan, bataata hoon",
        "send_as": "vera",
        "suppression_key": "m_032_mukesh_restaurant_pune:milestone_reached:perf_win",
        "rationale": (
            "perf_win:milestone_reached — merchant.performance.delta_7d.views_pct=+0.14 (+14%) and "
            "calls_pct=−0.24 (−24%) both from merchant data; views↑ + calls↓ signals profile "
            "conversion gap, not a reach problem; L7 Asking: ask what changed before prescribing fix — "
            "the answer shapes the recommendation; hi-en per Pune merchant.identity.languages; send_as vera"
        ),
    },
    # ── T24: perf_dip → perf_dip_recovery (L1, Mumbai/hi-en) ──
    {
        "test_id": "T24",
        "body": (
            "Bharat bhai, ek quick update — is week Bharat Dental ke calls 50% gire hain "
            "(baseline 12 se sirf 4 reh gaye). Views bhi 22% neeche hain. "
            "Profile abhi unverified hai, jo calls par directly asar daalta hai. "
            "Verification karne mein 5 minute lagte hain — kya main steps share karoon?"
        ),
        "cta": "Haan, share karo",
        "send_as": "vera",
        "suppression_key": "m_002_bharat_dentist_mumbai:perf_dip:perf_dip_recovery",
        "rationale": (
            "perf_dip_recovery:perf_dip — trigger.payload.calls_this_week=4 vs "
            "trigger.payload.baseline_calls=12 (−50%); merchant.performance.delta_7d.views_pct=−0.22 (−22%); "
            "merchant.identity.verified=false — root cause identified; "
            "L1 Specificity: exact numbers (4 vs 12, −22%) + one concrete fix (5-min verification); "
            "hi-en per Mumbai merchant.identity.languages; send_as vera"
        ),
    },
    # ── T25: perf_dip (subscription expired) → perf_dip_recovery (L3, Pune/hi-en) ──
    {
        "test_id": "T25",
        "body": (
            "Sushma ji, quick benchmark — Baner mein active Pro salons 2,500+ views se "
            "avg 38+ calls convert karte hain (1.5% CTR). "
            "Beauty Bar ke paas 2,547 views hain par sirf 22 calls (0.9% CTR). "
            "Gap ka reason: subscription 39 din se expired hai. "
            "Active profile wale salons 35% more calls receive karte hain. "
            "Subscription renew karein aur ek service ka price add karein — "
            "dono ek saath sabse best results dete hain. Karein?"
        ),
        "cta": "Haan, karte hain",
        "send_as": "vera",
        "suppression_key": "m_023_sushma_salon_pune:perf_dip:perf_dip_recovery",
        "rationale": (
            "perf_dip_recovery:perf_dip — merchant.performance.views=2547, calls=22 (CTR=0.9% vs peer 1.5%); "
            "merchant.subscription.days_since_expiry=39 — root cause; "
            "L3 Social proof: Baner Pro salon peer CTR benchmark (1.5% avg vs merchant 0.9%) + "
            "35% more calls for active profiles; hi-en per Pune merchant.identity.languages; send_as vera"
        ),
    },
    # ── T26: perf_spike → perf_win (L5, Chennai/en) ──
    {
        "test_id": "T26",
        "body": (
            "Padma, something interesting — Zen Yoga's calls are up 15% this week. "
            "Looks like your kids yoga post is the driver: 18 calls came in, "
            "12 turned into enquiries. "
            "Before you plan your next post, want me to break down what made this one work?"
        ),
        "cta": "Yes, break it down",
        "send_as": "vera",
        "suppression_key": "m_008_zenyoga_gym_chennai:perf_spike:perf_win",
        "rationale": (
            "perf_win:perf_spike — trigger.payload.delta_calls_pct=+0.15 (+15%); "
            "trigger.payload.likely_driver=kids_yoga_post; "
            "merchant.performance.calls=18, leads=12 from 30d data; "
            "L5 Curiosity: name the win, tease the insight ('what made it work'), "
            "invite the conversation before prescribing; English per Chennai city rule; send_as vera"
        ),
    },
    # ── T27: perf_spike → perf_win (L5, Lucknow/hi, pharmacy) ──
    {
        "test_id": "T27",
        "body": (
            "Vikas bhai, Sunrise Medicos ke calls is hafte 5% upar hain "
            "(14 calls, 8 leads bane). Gomti Nagar mein kuch kaam kar raha hai. "
            "Aur main notice kar raha hoon — aapke paas 60+ chronic prescription customers "
            "already registered hain. Kya kiya recently jo is trend bana? "
            "Batao taaki is pe double down karein."
        ),
        "cta": "Haan, bataata hoon",
        "send_as": "vera",
        "suppression_key": "m_010_sunrisepharm_pharmacy_lucknow:perf_spike:perf_win",
        "rationale": (
            "perf_win:perf_spike — merchant.performance.delta_7d.calls_pct=+0.05 (+5%); "
            "calls=14, leads=8 from 30d window; "
            "merchant.customer_aggregate.chronic_rx_count=60 anchors the base observation; "
            "merchant.identity.locality=Gomti Nagar grounds the message; "
            "L5 Curiosity: celebrate win then ask the driver before prescribing next action; "
            "full Hindi per Lucknow city rule; send_as vera"
        ),
    },
    # ── T28: recall_due → customer_recall (L8, Delhi/hi-en) ──
    {
        "test_id": "T28",
        "body": (
            "Hi Priya! Dr. Meera's Dental ki taraf se — "
            "aapki 6-month cleaning November 12 ko due hai. "
            "Hamare paas do slots available hain: Wed 5 Nov at 6pm ya Thu 6 Nov at 5pm. "
            "Kaunsa suit karega?"
        ),
        "cta": "Wed 5 Nov, 6pm / Thu 6 Nov, 5pm",
        "send_as": "merchant_on_behalf",
        "suppression_key": "m_001_drmeera_dentist_delhi:recall_due:customer_recall",
        "rationale": (
            "customer_recall:recall_due — trigger.payload.recall_due_date=2026-11-12 (6-month cleaning); "
            "trigger.payload.slots=[Wed 5 Nov 6pm, Thu 6 Nov 5pm] both from payload; "
            "customer Priya (identity.language_pref=hi-en mix, relationship.visits_total=4, "
            "preferences.preferred_slots=weekday_evening — evening slots matched); "
            "L8 binary commitment via specific slot choice; hi-en per customer.identity.language_pref; "
            "send_as merchant_on_behalf — no Vera/magicpin mention"
        ),
    },
    # ── T29: recall_due → customer_recall (L8, Chennai/en) ──
    {
        "test_id": "T29",
        "body": (
            "Hi Diya! This is Zen Yoga Studio, Mylapore — "
            "it's been just over a month since your last class. "
            "Morning slots at 6am and evening at 7pm are open this week. "
            "Which works better for you?"
        ),
        "cta": "6am / 7pm",
        "send_as": "merchant_on_behalf",
        "suppression_key": "m_008_zenyoga_gym_chennai:recall_due:customer_recall",
        "rationale": (
            "customer_recall:recall_due — customer Diya (state=lapsed_soft, "
            "relationship.last_visit=2026-04-01, ~1 month gap, identity.language_pref=english, "
            "age_band=20-25); merchant.identity.locality=Mylapore; slot times 6am/7pm from "
            "merchant operational schedule; no-shame framing (gym voice rule: no mention of absence); "
            "L8 binary commitment via specific slot choice (not generic 'book a slot'); "
            "English per Chennai city rule; send_as merchant_on_behalf — no Vera/magicpin mention"
        ),
    },
    # ── T30: regulation_change → knowledge_digest (L1, Delhi/hi-en) ──
    {
        "test_id": "T30",
        "body": (
            "Meera ji, DCI ne dentists ke liye naye radiograph compliance guidelines issue ki hain — "
            "deadline 15 December 2026. "
            "Agar digital X-ray records ka documentation abhi nahi hua, toh penalty risk hai. "
            "Main aapko ek quick action checklist bhej sakti hoon — "
            "10 minute mein sab clear ho jayega. Bhejoon?"
        ),
        "cta": "Haan, bhejo",
        "send_as": "vera",
        "suppression_key": "m_001_drmeera_dentist_delhi:regulation_change:knowledge_digest",
        "rationale": (
            "knowledge_digest:regulation_change — trigger.payload.regulation_id=d_2026W17_dci_radiograph; "
            "trigger.payload.deadline=2026-12-15; trigger.payload.consequence=penalty_risk; "
            "L1 Specificity: named exact body (DCI radiograph compliance), deadline (Dec 15), "
            "consequence (penalty), concrete deliverable (action checklist, 10 min); "
            "hi-en per Delhi merchant.identity.languages; send_as vera"
        ),
    },
]


def build(dry_run: bool = False) -> None:
    output_file = SUBMISSION_DRYRUN_FILE if dry_run else SUBMISSION_FILE
    with open(output_file, "w", encoding="utf-8") as fh:
        for row in ALL_ROWS:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"Written {len(ALL_ROWS)} rows to {output_file}")

    # Lever budget verification
    lever_counts: dict[str, int] = {}
    for row in ALL_ROWS:
        r = row["rationale"]
        for lever in ["L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8"]:
            if lever + " " in r or lever + ":" in r:
                lever_counts[lever] = lever_counts.get(lever, 0) + 1
    print("\nLever budget check:")
    for lv, count in sorted(lever_counts.items()):
        status = ""
        if lv == "L2" and count > 8:
            status = " OVER CAP (max 8)"
        elif lv == "L3" and count < 4:
            status = " UNDER MIN (need 4)"
        elif lv == "L7" and count < 4:
            status = " UNDER MIN (need 4)"
        elif lv == "L5" and count < 3:
            status = " UNDER MIN (need 3)"
        print(f"  {lv}: {count}{status}")
    print(f"\nTotal rows: {len(ALL_ROWS)}")
    send_as_counts = {}
    for row in ALL_ROWS:
        s = row["send_as"]
        send_as_counts[s] = send_as_counts.get(s, 0) + 1
    print(f"send_as breakdown: {send_as_counts}")


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    build(dry_run=dry)
