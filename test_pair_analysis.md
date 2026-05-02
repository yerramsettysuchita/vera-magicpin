# Test Pair Analysis — All 30 Canonical Pairs
## Phase 1 Intelligence — magicpin AI Challenge (Vera)

**Total pairs**: 30 | **HIGH confidence**: 17 | **MEDIUM confidence**: 2 | **LOW confidence**: 11  
**Customer-facing (send_as=merchant_on_behalf)**: T03, T04, T07, T08, T13, T14, T15, T28, T29 (9 pairs)  
**Merchant-facing (send_as=vera)**: T01, T02, T05, T06, T09, T10, T11, T12, T16, T17, T18, T19, T20, T21, T22, T23, T24, T25, T26, T27, T30 (21 pairs)

⚠️ **Highest-risk pairs** (special Phase 2 attention required): **T03, T04, T08, T14, T15**

---

## Full Pair Table

| ID | merchant_id + category | trigger_id + kind | Strongest specificity anchor | Best lever | Voice register | CTA type | send_as | Data confidence | Notes |
|----|------------------------|-------------------|------------------------------|-----------|----------------|----------|---------|-----------------|-------|
| **T01** | m_006 Mylari South Indian Cafe — restaurant Bangalore | trg_013 `active_planning_intent` | Merchant's 88 calls/12,400 views + Weekday Lunch Thali @ ₹149 + merchant asked "what would it look like" | L4 — Effort externalization | Peer / operator-to-operator | open_ended | vera | HIGH | Deliver the corporate thali package artifact immediately — merchant explicitly asked for it |
| **T02** | m_008 Zen Yoga Studio — gym Chennai | trg_016 `active_planning_intent` | School holiday window Apr-Jun, +50% pediatric opportunity; 95 active members, 55% trial-to-paid | L4 — Effort externalization | Warm-practical / coach | open_ended | vera | HIGH | Merchant asked "what should it look like?" — respond with full kids yoga camp structure |
| **T03** ⚠️ | m_019 Karim's Salon — salon Lucknow | trg_076 `appointment_tomorrow` | None from trigger (placeholder); customer Aditya has 1 prior visit; salon category defaults only | L4 — Effort externalization | Warm-practical | multi_choice_slot | merchant_on_behalf | LOW | **HIGHEST RISK**: Placeholder trigger, no appointment time/service/slot; customer state=lapsed_hard (anomaly for appointment trigger); must fabricate from category salon patterns; en-only customer |
| **T04** ⚠️ | m_020 Beauty Lounge by Renu — salon Lucknow | trg_077 `appointment_tomorrow` | None from trigger (placeholder); customer Riya: 2 visits, hi-only language | L8 — Binary commitment | Warm-practical + Hindi | binary_yes_no | merchant_on_behalf | LOW | **HIGH RISK**: Placeholder trigger + expired merchant subscription + Hindi-preferred customer (must reply in Hindi) |
| **T05** | m_009 Apollo Health Plus — pharmacy Jaipur | trg_020 `category_seasonal` | ORS +40%, sunscreen +38%, antifungal +45%, cold/cough −60% (4 specific data points) + 240 chronic-Rx patients | L1 — Specificity / verifiability | Trustworthy-precise | binary | vera | HIGH | Best-anchored seasonal trigger in dataset; all 4 trend numbers from category fingerprints; merchant has 68% repeat rate |
| **T06** | m_001 Dr. Meera's Dental Clinic — dentist Delhi | trg_022 `cde_opportunity` | IDA Delhi webinar 2026-05-02, 2 CDE credits, free for members — **EXPIRES TOMORROW** | L6 — Reciprocity | Clinical/authority — peer dentist | open_ended | vera | HIGH | Urgency: trigger expires 2026-05-02 (1 day away). Frame as "spotted this for you specifically" not generic blast |
| **T07** | m_009 Apollo Health Plus — pharmacy Jaipur | trg_019 `chronic_refill_due` | Molecules: metformin, atorvastatin, telmisartan; stock ran out 2026-04-28 (3 days ago!); delivery address saved | L8 — Binary commitment | Trustworthy-precise + Hindi + namaste (senior 65-75) | binary_yes_no | merchant_on_behalf | HIGH | Stock expiry was 2026-04-28 — already overdue! Message urgency = "your medicines ran out 3 days ago, dispatching now if you say YES"; delivery via son's WhatsApp |
| **T08** ⚠️ | m_011 Bright Smile Dental — **dentist** Bangalore | trg_081 `chronic_refill_due` | None from trigger (placeholder); customer Vivaan: 5 visits, LTV ₹4,900, state=new (anomaly) | L4 — Effort externalization | Warm-clinical (dental, not pharmacy) | multi_choice_slot | merchant_on_behalf | LOW | **HIGHEST RISK**: Category mismatch — `chronic_refill_due` on a dentist. Reframe as 6-month recall/cleaning due. Placeholder + expired subscription + customer state=new despite 5 visits (data inconsistency). |
| **T09** | m_001 Dr. Meera's Dental Clinic — dentist Delhi | trg_023 `competitor_opened` | Smile Studio 1.3 km, Dental Cleaning @ ₹199 vs Dr. Meera's ₹299 (₹100 gap); Dr. Meera has 124 high-risk adults | L2 — Loss aversion | Peer — data-first, no panic | binary | vera | HIGH | Must avoid panic tone; counter with Dr. Meera's clinical differentiation (high-risk adult cohort, JIDA-sourced advice) not price-matching |
| **T10** | m_006 Mylari South Indian Cafe — restaurant Bangalore | trg_056 `competitor_opened` | Merchant's own strengths: 12,400 views, CTR +0.007 vs peer, 4,200 customers, 42% repeat, thali quality reviews | L5 — Curiosity | Peer / operator | open_ended | vera | MEDIUM | Placeholder trigger — no competitor details. Pivot to merchant's defensive strengths. Mylari (T01/T10/T12/T22 all use m_006) — keep topics distinct |
| **T11** | m_003 Studio11 Family Salon — salon Hyderabad | trg_008 `curious_ask_due` | First-ever curious ask (last_ask_at=null); bridal-trial searches Kapra +28% noted in last msg (no reply received) | L7 — Asking the merchant | Warm-practical + Telugu/English | open_ended | vera | HIGH | Last topic was bridal-trial — don't repeat. Ask about something different (e.g., which weekday slot is most in demand). Single question only. |
| **T12** | m_006 Mylari South Indian Cafe — restaurant Bangalore | trg_096 `curious_ask_due` | Merchant's recent active engagement ("Yes good idea, what would it look like"); 22 thali_quality reviews; 45% delivery share | L7 — Asking the merchant | Peer / operator | open_ended | vera | MEDIUM | Placeholder trigger. 4th test pair for m_006 — must differ from T01 (corp thali plan), T10 (competitor), T22 (milestone). Ask about delivery vs dine-in mix or weekend management. |
| **T13** | m_007 PowerHouse Fitness — gym Bangalore | trg_015 `customer_lapsed_hard` | 57 days since last visit, 5 months membership, weight_loss focus, LTV ₹4,490 | L2 — Loss aversion | Warm — no-shame, no guilt-trip | binary_yes_no | merchant_on_behalf | HIGH | Must include "no commitment / no auto-charge" language explicitly. May = lowest acquisition window but retention focus is right. |
| **T14** ⚠️ | m_014 Asha Dental Care — dentist Chandigarh | trg_071 `customer_lapsed_soft` | Customer Reyansh: 5 visits, LTV ₹4,390; use dental recall defaults (6-month cleaning) | L5 — Curiosity | Warm-clinical (no guilt-trip dental) | binary_yes_no | merchant_on_behalf | LOW | **HIGH RISK**: Customer state=CHURNED but trigger says lapsed_soft — possible opt-out, handle carefully. Placeholder trigger + LOW merchant data. Treat as soft lapse; do not push aggressively. |
| **T15** ⚠️ | m_049 Daily Care Medicos — pharmacy Lucknow | trg_072 `customer_lapsed_soft` | Customer Reyansh: 12 visits, LTV ₹3,012, hi-en mix language; summer seasonal: ORS/antifungal surge | L5 — Curiosity | Warm + hi-en mix | binary_yes_no | merchant_on_behalf | LOW | **HIGH RISK**: Placeholder trigger + no service history (services_received=[]) + customer state=active contradicts lapsed_soft trigger. Must use hi-en mix language. |
| **T16** | m_004 Glamour Lounge Spa — salon Pune | trg_025 `dormant_with_vera` | 38 days dormant; 180 lapsed customers (47% of 380 YTD); expired subscription; last topic=subscription_expiry | L7 — Asking the merchant | Peer — warm, not pushy | open_ended | vera | HIGH | Anti-repetition: last topic was subscription. Must re-open conversation with a new angle — ask about the merchant's current situation. |
| **T17** | m_029 Chai Point Cafe — restaurant Chandigarh | trg_046 `dormant_with_vera` | Merchant CTR = 0.025 (exactly at peer median); calls −21% in 7d from delta_7d; no prior conversation | L7 — Asking the merchant | Peer / operator | open_ended | vera | LOW | No prior conversation history — fresh cold re-engagement. Use peer comparison (exactly at median CTR) as low-pressure hook. |
| **T18** | m_003 Studio11 Family Salon — salon Hyderabad | trg_006 `festival_upcoming` | Diwali 2026-10-31, 188 days away; salon seasonal: Oct-Dec = 4x baseline bridal; Kapra bridal searches +28% | L3 — Social proof | Warm-practical | binary | vera | HIGH | Contrarian planning insight: "Diwali bridal is 188 days away but your Oct calendar fills 8-10 weeks ahead — peers are booking now" |
| **T19** | m_037 Bend & Burn — gym Bangalore | trg_061 `festival_upcoming` | Bangalore gym seasonal: Aug-Oct = wedding-prep + festival return wave; 5,934 views (above avg for gyms) | L3 — Social proof | Warm-practical / coach | binary | vera | LOW | Placeholder trigger — no festival name/date. Anchor on seasonal gym data: Aug-Oct wedding-prep wave. Risky if festival doesn't match gym context. |
| **T20** | m_010 Sunrise Medicos — pharmacy Lucknow | trg_021 `gbp_unverified` | +30% call uplift after GBP verification; 5-day approval path; no prior conversation, Basic plan | L1 — Specificity / verifiability | Trustworthy-precise | binary | vera | HIGH | Cold first outbound (no session window open). The 30% uplift is the hook. WhatsApp pre-approved template format required for first message. |
| **T21** | m_005 SK Pizza Junction — restaurant Delhi | trg_010 `ipl_match_today` | DC vs MI, 2026-04-26 7:30pm, **is_weeknight=FALSE** — Saturday match → −12% covers | L2 — Loss aversion (contrarian) | Peer / operator — insider data | binary | vera | HIGH | ⚠️ ANTI-PATTERN TRAP: Weekend IPL = −12% covers. Correct answer is advise AGAINST the promo; suggest Tue/Wed/Thu weeknight match instead. Judge rewards the contrarian insight. |
| **T22** | m_006 Mylari South Indian Cafe — restaurant Bangalore | trg_012 `milestone_reached` | 145/150 reviews (5 from milestone), 22 thali_quality reviews this month, is_imminent=true | L3 — Social proof | Peer — celebrating together, momentum | open_ended | vera | HIGH | is_imminent=true: not yet reached. Frame as momentum-building to the milestone. 4th pair for m_006 — distinct topic. |
| **T23** | m_032 Pizza Spot — restaurant Pune | trg_041 `milestone_reached` | Merchant CTR 0.053 (+0.028 vs peer avg 0.025) — standout performance metric | L5 — Curiosity | Peer / operator | open_ended | vera | LOW | Placeholder trigger — no milestone metric known. Anchor on CTR outperformance as proxy. Don't fabricate a specific milestone number. |
| **T24** | m_002 Bharat Dental Care — dentist Mumbai | trg_004 `perf_dip` | Calls −50% in 7d vs baseline 12; CTR 0.018 (−0.012 vs peer); renewal in 12 days; 5 risk signals | L1 — Specificity / verifiability | Peer — data-first, not alarming | open_ended | vera | HIGH | Do NOT mention subscription renewal in the dip message. Diagnose the −50% calls first. No seasonal explanation available — this is a genuine dip. |
| **T25** | m_023 The Beauty Bar — salon Pune | trg_031 `perf_dip` | Merchant CTR 0.058 (+0.018 vs peer) is strong, but calls/views trend needs diagnosis; expired subscription | L3 — Social proof | Peer / warm | open_ended | vera | LOW | Placeholder trigger — unknown which metric dipped. Expired subscription limits ability to fix. Use peer comparison rather than fabricating a dip metric. |
| **T26** | m_008 Zen Yoga Studio — gym Chennai | trg_024 `perf_spike` | Calls +15% in 7d vs baseline 18; likely_driver=kids_yoga_post (causal insight available!) | L5 — Curiosity | Warm-practical / coach | open_ended | vera | HIGH | likely_driver is known — anchor on it. 3rd test pair for m_008 (T02, T26, T29) — keep distinct. T02 was planning kids yoga; T26 is the payoff spike. |
| **T27** | m_010 Sunrise Medicos — pharmacy Lucknow | trg_036 `perf_spike` | Merchant calls +5% delta_7d; CTR 0.041 (+0.003 vs peer); no active offers; unverified GBP | L6 — Reciprocity | Trustworthy-precise | open_ended | vera | LOW | Placeholder trigger — no spike metric. Anchor on modest delta_7d improvement. T20 is also Sunrise (gbp trigger) — ensure distinct angles. |
| **T28** | m_001 Dr. Meera's Dental Clinic — dentist Delhi | trg_003 `recall_due` | 6-month cleaning due 2026-11-12; two specific slots (Wed 5 Nov 6pm / Thu 6 Nov 5pm) — best slot data in dataset | L8 — Binary commitment | Warm-clinical + hi-en mix | multi_choice_slot | merchant_on_behalf | HIGH | Best-anchored customer recall in dataset. Two specific slots matching preferred_slots=weekday_evening. Must use hi-en mix. Pre-approved template format. |
| **T29** | m_008 Zen Yoga Studio — gym Chennai | trg_066 `recall_due` | Customer Diya: 9 visits, LTV ₹6,183 (high for yoga studio), lapsed_soft; en-only | L4 — Effort externalization | Warm-practical (gym/yoga) | multi_choice_slot | merchant_on_behalf | LOW | Placeholder trigger — no slot data. 3rd pair for m_008. Use category-default slots. Diya's high LTV (₹6,183) = retention priority. |
| **T30** | m_001 Dr. Meera's Dental Clinic — dentist Delhi | trg_002 `regulation_change` | DCI circular: radiograph dose 1.5→1.0 mSv, effective 2026-12-15; E-speed passes, D-speed does not | L2 — Loss aversion | Clinical/authority — peer dentist | open_ended | vera | HIGH | 4th pair for m_001 — distinct from T06 (CDE), T09 (competitor), T28 (patient recall). D-speed plate failure = specific compliance risk anchor. |

---

## Trigger Kind Coverage

| Trigger Kind | Test Pairs | Profile | Seed/Placeholder |
|---|---|---|---|
| `active_planning_intent` | T01, T02 | planning_curiosity | Seed (both) |
| `appointment_tomorrow` | T03 ⚠️, T04 ⚠️ | customer_recall | Placeholder (both) |
| `category_seasonal` | T05 | event_seasonal | Seed |
| `cde_opportunity` | T06 | knowledge_digest | Seed |
| `chronic_refill_due` | T07, T08 ⚠️ | customer_winback | Seed / Placeholder |
| `competitor_opened` | T09, T10 | activation_urgency | Seed / Placeholder |
| `curious_ask_due` | T11, T12 | planning_curiosity | Seed / Placeholder |
| `customer_lapsed_hard` | T13 | customer_winback | Seed |
| `customer_lapsed_soft` | T14 ⚠️, T15 ⚠️ | customer_winback | Placeholder (both) |
| `dormant_with_vera` | T16, T17 | activation_urgency | Seed / Placeholder |
| `festival_upcoming` | T18, T19 | event_seasonal | Seed / Placeholder |
| `gbp_unverified` | T20 | activation_urgency | Seed |
| `ipl_match_today` | T21 | event_seasonal | Seed |
| `milestone_reached` | T22, T23 | perf_win | Seed / Placeholder |
| `perf_dip` | T24, T25 | perf_dip_recovery | Seed / Placeholder |
| `perf_spike` | T26, T27 | perf_win | Seed / Placeholder |
| `recall_due` | T28, T29 | customer_recall | Seed / Placeholder |
| `regulation_change` | T30 | knowledge_digest | Seed |

---

## Multi-Pair Merchant Flags

Merchants appearing in multiple test pairs require distinct message topics across all pairs:

| Merchant | Test Pairs | Topics — must all differ |
|---|---|---|
| **m_001** Dr. Meera Delhi | T06, T09, T28, T30 | CDE webinar / competitor opened / patient recall / regulation change ✓ |
| **m_006** Mylari Bangalore | T01, T10, T12, T22 | Corp thali planning / competitor response / curious ask / milestone ✓ |
| **m_008** Zen Yoga Chennai | T02, T26, T29 | Kids yoga planning / perf spike / customer recall ✓ |
| **m_009** Apollo Pharmacy Jaipur | T05, T07 | Seasonal demand shift (merchant) / chronic refill (customer) ✓ |
| **m_010** Sunrise Medicos Lucknow | T20, T27 | GBP verification / perf spike ✓ |

---

## 5 Highest-Risk Pairs — Phase 2 Alert

### ⚠️ T03 — appointment_tomorrow / Karim's Salon Lucknow / customer Aditya
**Risk factors**: Placeholder trigger (no appointment time, no service, no slot options). Customer state=lapsed_hard contradicts appointment trigger. 1 visit total, no service history.  
**Strategy**: Assume appointment was booked via walk-in or call. Use salon category default "haircut / styling" service. Generate 2 plausible slot times (tomorrow 10am / 11am). Keep message brief and warm. Customer is en-only.

### ⚠️ T04 — appointment_tomorrow / Beauty Lounge by Renu / customer Riya
**Risk factors**: Placeholder trigger. Merchant subscription EXPIRED. Customer prefers Hindi exclusively.  
**Strategy**: Message must be in Hindi. Even with expired subscription, the appointment reminder is for the customer — send from merchant. Generate default slot. Subscription expiry doesn't affect this customer-facing message.

### ⚠️ T08 — chronic_refill_due / Bright Smile Dental (DENTIST!) / customer Vivaan
**Risk factors**: `chronic_refill_due` is a pharmacy-scoped trigger assigned to a dental clinic — category mismatch. Placeholder trigger. Expired merchant subscription. Customer state=new despite 5 visits.  
**Strategy**: Reframe as dental recall/cleaning due message. Use "dental cleaning" as the "service due" equivalent. Generate a slot or CTA to book. Anchor on the 5-visit history. Do NOT mention refills, molecules, or pharmacy-related language.

### ⚠️ T14 — customer_lapsed_soft / Asha Dental Chandigarh / customer Reyansh
**Risk factors**: Customer state=CHURNED — this may indicate opt-out. Placeholder trigger. LOW merchant data (no offers, no signals).  
**Strategy**: Treat as soft lapse message, not hard winback. Keep extremely brief and non-pushy. Dental category recall framing ("your cleaning is due") is lower pressure than promo. If churned = opted out, the bot should note suppression concern in rationale.

### ⚠️ T15 — customer_lapsed_soft / Daily Care Medicos Lucknow / customer Reyansh
**Risk factors**: Placeholder trigger. No service history (services_received=[]). Customer state=active contradicts lapsed_soft. Hi-en mix required.  
**Strategy**: Customer has 12 visits with ₹3,012 LTV — use summer seasonal hook (ORS/antifungal demand +40-45%) as a new reason to visit. Hi-en mix in message. Don't refer to "lapse" since state=active.

---

## Data Confidence Summary

| Confidence | Count | Pairs | Hallucination Risk |
|---|---|---|---|
| **HIGH** | 17 | T01, T02, T05, T06, T07, T09, T11, T13, T16, T18, T20, T21, T22, T24, T26, T28, T30 | Low — rich payload available |
| **MEDIUM** | 2 | T10, T12 | Medium — placeholder trigger but HIGH-data merchant |
| **LOW** | 11 | T03, T04, T08, T14, T15, T17, T19, T23, T25, T27, T29 | High — must derive from merchant perf + category defaults |

**LOW confidence pairs strategy**: Do not fabricate specific numbers (e.g., "your calls dropped 23%") — instead use merchant performance delta, category peer stats, or seasonal data as anchors. For customer-facing LOW pairs, use the customer's visit count and LTV as proxies for specificity.
