# Lever Budget Table — All 30 Pairs
## Phase 1 Intelligence — magicpin AI Challenge (Vera)

**Purpose**: Assign primary/secondary levers to all 30 pairs and verify the diversity constraints from the challenge brief.

---

## Constraints to satisfy
- No single lever used more than **8 times** as primary
- **Lever 3 (Social Proof)** used at least **4 times**
- **Lever 7 (Asking the merchant)** used at least **4 times**
- **Lever 5 (Curiosity)** used at least **3 times**
- LOW confidence pairs should use levers that don't require hard numbers (prefer L4, L5, L7)

---

## Full Assignment Table

| Pair | Merchant | Trigger Kind | Profile | Primary Lever | Secondary Lever | Data Conf | Notes |
|------|----------|-------------|---------|--------------|----------------|-----------|-------|
| T01 | m_006 Mylari Cafe — restaurant | `active_planning_intent` | planning_curiosity | **L4** — Effort externalization | L6 — Reciprocity | HIGH | Deliver corp thali package draft immediately |
| T02 | m_008 Zen Yoga — gym | `active_planning_intent` | planning_curiosity | **L4** — Effort externalization | L6 — Reciprocity | HIGH | Deliver full kids yoga camp structure |
| T03 ⚠️ | m_019 Karim's Salon — salon | `appointment_tomorrow` | customer_recall | **L4** — Effort externalization | L8 — Binary commitment | LOW | Placeholder: fabricate from salon defaults; no-effort slot confirm |
| T04 ⚠️ | m_020 Beauty Lounge — salon | `appointment_tomorrow` | customer_recall | **L8** — Binary commitment | L4 — Effort externalization | LOW | Hindi message; simple 1-tap confirm; expired subscription merchant |
| T05 | m_009 Apollo Pharmacy — pharmacy | `category_seasonal` | event_seasonal | **L1** — Specificity/verifiability | L2 — Loss aversion | HIGH | ORS +40%, sunscreen +38%, antifungal +45%, cold/cough −60% |
| T06 | m_001 Dr. Meera Dental — dentist | `cde_opportunity` | knowledge_digest | **L6** — Reciprocity | L1 — Specificity | HIGH | Expires tomorrow 2026-05-02 — "spotted this for you specifically" |
| T07 | m_009 Apollo Pharmacy — pharmacy | `chronic_refill_due` | customer_winback | **L8** — Binary commitment | L4 — Effort externalization | HIGH | Senior citizen; molecules named; stock overdue; Hindi namaste |
| T08 ⚠️ | m_011 Bright Smile Dental — dentist | `chronic_refill_due` | customer_winback | **L4** — Effort externalization | L8 — Binary commitment | LOW | Category mismatch: reframe as dental recall; slot held; no pharmacy language |
| T09 | m_001 Dr. Meera Dental — dentist | `competitor_opened` | activation_urgency | **L2** — Loss aversion | L1 — Specificity | HIGH | Smile Studio 1.3 km, ₹199 cleaning vs ₹299; peer tone, not panic |
| T10 | m_006 Mylari Cafe — restaurant | `competitor_opened` | activation_urgency | **L5** — Curiosity | L2 — Loss aversion | MEDIUM | Placeholder: anchor on merchant's own CTR strength; ask about competitor |
| T11 | m_003 Studio11 Salon — salon | `curious_ask_due` | planning_curiosity | **L7** — Asking the merchant | L6 — Reciprocity | HIGH | First-ever ask; single question about in-demand service this week |
| T12 | m_006 Mylari Cafe — restaurant | `curious_ask_due` | planning_curiosity | **L7** — Asking the merchant | L4 — Effort externalization | MEDIUM | 4th Mylari pair; ask about delivery vs dine-in or weekend peak |
| T13 | m_007 PowerHouse Gym — gym | `customer_lapsed_hard` | customer_winback | **L2** — Loss aversion | L4 — Effort externalization | HIGH | 57d away, weight_loss focus, "no commitment / no auto-charge" required |
| T14 ⚠️ | m_014 Asha Dental — dentist | `customer_lapsed_soft` | customer_winback | **L5** — Curiosity | L4 — Effort externalization | LOW | Churned customer state mismatch; brief non-pushy; dental recall framing |
| T15 ⚠️ | m_049 Daily Care Medicos — pharmacy | `customer_lapsed_soft` | customer_winback | **L5** — Curiosity | L4 — Effort externalization | LOW | No service history; hi-en mix; summer seasonal hook (ORS/antifungal) |
| T16 | m_004 Glamour Salon — salon | `dormant_with_vera` | activation_urgency | **L7** — Asking the merchant | L2 — Loss aversion | HIGH | 38d dormant; expired sub; last topic was subscription — must ask new angle |
| T17 | m_029 Chai Point Cafe — restaurant | `dormant_with_vera` | activation_urgency | **L7** — Asking the merchant | L5 — Curiosity | LOW | No prior conversation; CTR at peer median; cold re-engagement question |
| T18 | m_003 Studio11 Salon — salon | `festival_upcoming` | event_seasonal | **L3** — Social proof | L2 — Loss aversion | HIGH | Diwali 188d away; "peers are booking bridal Oct slots now" |
| T19 | m_037 Bend & Burn Gym — gym | `festival_upcoming` | event_seasonal | **L3** — Social proof | L2 — Loss aversion | LOW | Placeholder; anchor on Aug-Oct wedding-prep wave in Bangalore gyms |
| T20 | m_010 Sunrise Medicos — pharmacy | `gbp_unverified` | activation_urgency | **L1** — Specificity/verifiability | L2 — Loss aversion | HIGH | "+30% calls after verification in 5 days" — cold first outbound |
| T21 | m_005 Pizza Junction — restaurant | `ipl_match_today` | event_seasonal | **L2** — Loss aversion (contrarian) | L3 — Social proof | HIGH | Weekend match → −12% covers; ADVISE AGAINST promo; suggest weeknight |
| T22 | m_006 Mylari Cafe — restaurant | `milestone_reached` | perf_win | **L3** — Social proof | L5 — Curiosity | HIGH | 145/150 reviews; is_imminent=true; momentum + peer comparison |
| T23 | m_032 Pizza Spot — restaurant | `milestone_reached` | perf_win | **L5** — Curiosity | L3 — Social proof | LOW | Placeholder; anchor on CTR +0.028 vs peer as proxy for milestone |
| T24 | m_002 Bharat Dental — dentist | `perf_dip` | perf_dip_recovery | **L1** — Specificity/verifiability | L2 — Loss aversion | HIGH | Calls −50% in 7d vs baseline 12; do NOT pivot to renewal/paid upgrade |
| T25 | m_023 The Beauty Bar — salon | `perf_dip` | perf_dip_recovery | **L3** — Social proof | L1 — Specificity | LOW | Placeholder; peer comparison approach; expired subscription merchant |
| T26 | m_008 Zen Yoga — gym | `perf_spike` | perf_win | **L5** — Curiosity | L4 — Effort externalization | HIGH | Calls +15%, likely_driver=kids_yoga_post; capitalize while signal hot |
| T27 | m_010 Sunrise Medicos — pharmacy | `perf_spike` | perf_win | **L6** — Reciprocity | L5 — Curiosity | LOW | Placeholder; modest delta_7d (+5% calls); distinct from T20 (GBP) |
| T28 | m_001 Dr. Meera Dental — dentist | `recall_due` | customer_recall | **L8** — Binary commitment | L4 — Effort externalization | HIGH | Two specific slots (Wed 5 Nov 6pm / Thu 6 Nov 5pm); hi-en mix |
| T29 | m_008 Zen Yoga — gym | `recall_due` | customer_recall | **L4** — Effort externalization | L8 — Binary commitment | LOW | Placeholder; Diya LTV ₹6,183 = retention priority; default slots |
| T30 | m_001 Dr. Meera Dental — dentist | `regulation_change` | knowledge_digest | **L2** — Loss aversion | L1 — Specificity | HIGH | D-speed fails 1.0 mSv standard; effective 2026-12-15; compliance risk |

---

## Lever Count Verification

| Lever | Description | Pairs (Primary) | Count | Constraint | Status |
|-------|-------------|-----------------|-------|-----------|--------|
| L1 | Specificity / verifiability | T05, T20, T24 | **3** | ≤ 8 | ✅ |
| L2 | Loss aversion | T09, T13, T21, T30 | **4** | ≤ 8 | ✅ |
| L3 | Social proof | T18, T19, T22, T25 | **4** | ≥ 4 required | ✅ **MET** |
| L4 | Effort externalization | T01, T02, T03, T08, T29 | **5** | ≤ 8 | ✅ |
| L5 | Curiosity | T10, T14, T15, T23, T26 | **5** | ≥ 3 required | ✅ **MET** |
| L6 | Reciprocity | T06, T27 | **2** | ≤ 8 | ✅ |
| L7 | Asking the merchant | T11, T12, T16, T17 | **4** | ≥ 4 required | ✅ **MET** |
| L8 | Binary commitment | T04, T07, T28 | **3** | ≤ 8 | ✅ |
| **TOTAL** | | | **30** | Σ = 30 | ✅ |

All 3 minimum constraints satisfied. No lever exceeds 8. Total sums to exactly 30.

---

## Lever Usage by Profile

| Profile | Typical Primary | Pairs | Actual Assignment |
|---------|----------------|-------|-------------------|
| knowledge_digest | L1 | T06, T30 | L6 (T06), L2 (T30) — appropriate: T06 is CDE (reciprocity), T30 is compliance (loss aversion) |
| perf_dip_recovery | L1 | T24, T25 | L1 (T24), L3 (T25) — T25 placeholder so social proof is safer anchor |
| perf_win | L5 | T22, T23, T26 | L3 (T22), L5 (T23), L5 (T26) — milestone=social proof; spike=curiosity |
| event_seasonal | L2 | T05, T18, T19, T21 | L1 (T05), L3 (T18), L3 (T19), L2 (T21) — seasonal variety |
| activation_urgency | L2 | T09, T10, T16, T17, T20 | L2 (T09), L5 (T10), L7 (T16), L7 (T17), L1 (T20) — appropriate by sub-kind |
| planning_curiosity | L7 | T01, T02, T11, T12 | L4 (T01), L4 (T02), L7 (T11), L7 (T12) — active_planning→L4; curious_ask→L7 |
| customer_recall | L8 | T03, T04, T28, T29 | L4 (T03), L8 (T04), L8 (T28), L4 (T29) — slot-data pairs use L8; placeholder pairs use L4 |
| customer_winback | L5/L2/L8 | T07, T08, T13, T14, T15 | L8 (T07), L4 (T08), L2 (T13), L5 (T14), L5 (T15) — varies by sub-kind |

---

## LOW Confidence Lever Choices

For the 11 LOW confidence pairs, levers were chosen to avoid requiring specific numbers from the (missing) trigger payload:

| Pair | Assigned Lever | Why It's Safe for LOW Confidence |
|------|---------------|----------------------------------|
| T03 | L4 | Effort ext doesn't require trigger numbers — just confirm the slot |
| T04 | L8 | Binary "reply YES" requires no specific data, just a time |
| T08 | L4 | Deliver dental recall booking — category defaults fill the gap |
| T14 | L5 | Curiosity framing avoids quantified loss claims |
| T15 | L5 | Curiosity hook from seasonal data (not the missing trigger payload) |
| T17 | L7 | Single question — no specifics required |
| T19 | L3 | Peer/seasonal data is from category fingerprints, not trigger payload |
| T23 | L5 | Curiosity about CTR performance — uses merchant map, not trigger |
| T25 | L3 | Category peer comparison — uses peer_stats, not trigger payload |
| T27 | L6 | Reciprocity framing ("I noticed") — avoids fabricating a spike metric |
| T29 | L4 | Slot hold requires no specific trigger data; uses customer's LTV anchor |

---

## Secondary Lever Reference

Secondary levers reinforce or contrast the primary. Key pairings:

- **L4 + L8**: Deliver artifact AND ask for confirmation (planning/recall pairs)
- **L2 + L1**: Loss aversion grounded in specific numbers (risk pairs)
- **L5 + L3**: Curiosity sparked by what peers are doing (milestone/spike pairs)
- **L7 + L4**: Ask one question, offer to build from the answer (curious_ask pairs)
- **L1 + L2**: Specific metric anchor drives the loss framing (perf/compliance pairs)
