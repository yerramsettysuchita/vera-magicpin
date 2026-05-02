# Trigger Taxonomy
## Phase 1 Intelligence — magicpin AI Challenge (Vera)

All 26 trigger kinds found across the full dataset of 100 triggers, grouped by family.

---

## Family A: Knowledge & Compliance (External, Merchant-Facing)

### research_digest
- **Count**: 6 (trg_001 + trg_026–030)
- **Urgency range**: 1–2
- **Scope**: merchant
- **Key payload fields**: `category`, `top_item_id` (links to digest item with title/source/trial_n/patient_segment)
- **Best specificity anchor**: trial_n + percentage reduction + journal citation (e.g., "2,100-patient trial, 38% reduction, JIDA Oct 2026 p.14")
- **High-quality opening**: "Dr. Meera, JIDA's Oct issue landed — one item directly relevant to your high-risk adult patients."
- **Generic opening (avoid)**: "There's new research in dentistry you should know about."

### regulation_change
- **Count**: 1 (trg_002)
- **Urgency range**: 4
- **Scope**: merchant
- **Key payload fields**: `top_item_id`, `deadline_iso` (hard compliance deadline)
- **Best specificity anchor**: deadline date + exact limit change + equipment impact (1.5→1.0 mSv, Dec 15)
- **High-quality opening**: "Bharat, DCI just revised radiograph dose limits effective 2026-12-15 — E-speed film passes the new 1.0 mSv cap, D-speed does not."
- **Generic opening (avoid)**: "There's a new compliance update you should be aware of."

### cde_opportunity
- **Count**: 1 (trg_022)
- **Urgency range**: 1
- **Scope**: merchant
- **Key payload fields**: `digest_item_id`, `credits`, `fee`
- **Best specificity anchor**: date + credits + fee ("2026-05-02, 2 CDE credits, free for IDA members")
- **High-quality opening**: "IDA Delhi chapter: digital impressions webinar this Friday 2 May, 7pm — 2 CDE credits, free for members."
- **Generic opening (avoid)**: "There's a continuing education opportunity this week."

### supply_alert
- **Count**: 1 (trg_018)
- **Urgency range**: 5
- **Scope**: merchant
- **Key payload fields**: `molecule`, `affected_batches`, `manufacturer`
- **Best specificity anchor**: exact batch numbers + manufacturer + affected customer count derived from merchant's repeat-Rx list
- **High-quality opening**: "Ramesh, urgent: voluntary recall on atorvastatin batches AT2024-1102 + AT2024-1108 by MfrZ — 22 of your chronic-Rx customers may be affected."
- **Generic opening (avoid)**: "There's an important product recall you should address."

---

## Family B: Performance Monitoring (Internal, Merchant-Facing)

### perf_dip
- **Count**: 6 (trg_004 + trg_031–035)
- **Urgency range**: 3–4
- **Scope**: merchant
- **Key payload fields**: `metric`, `delta_pct`, `window`, `vs_baseline`
- **Best specificity anchor**: exact delta_pct + metric + window (e.g., "calls down 50% week-over-week vs baseline of 12")
- **High-quality opening**: "Bharat, quick check — calls dropped 50% this week (4 vs baseline 12). Three things that typically cause this in Andheri West."
- **Generic opening (avoid)**: "Your performance has been declining recently."

### seasonal_perf_dip
- **Count**: 1 (trg_014)
- **Urgency range**: 1
- **Scope**: merchant
- **Key payload fields**: `delta_pct`, `is_expected_seasonal`, `season_note`
- **Best specificity anchor**: dip percentage + peer range + season context + recommended action timing
- **High-quality opening**: "Karthik, views down 30% — but this is the normal April-June lull (every metro gym sees -25 to -35%). Skip ad spend now; save it for Sept-Oct when conversion is 2x."
- **Generic opening (avoid)**: "Your views are down this week."

### perf_spike
- **Count**: 6 (trg_024 + trg_036–040)
- **Urgency range**: 1
- **Scope**: merchant
- **Key payload fields**: `metric`, `delta_pct`, `window`, `likely_driver`
- **Best specificity anchor**: spike percentage + likely driver + immediate action to capitalize
- **High-quality opening**: "Padma, calls up 15% this week — likely the kids yoga post. Want me to turn this into a summer-camp series post while the momentum is live?"
- **Generic opening (avoid)**: "Your business is growing, great job!"

### milestone_reached
- **Count**: 6 (trg_012 + trg_041–045)
- **Urgency range**: 1
- **Scope**: merchant
- **Key payload fields**: `metric`, `value_now`, `milestone_value`, `is_imminent`
- **Best specificity anchor**: current count + milestone target + specific action to capitalise (e.g., "5 reviews away from 150 — post now while window is open")
- **High-quality opening**: "Suresh, you're at 145 reviews — 5 away from the 150 milestone that unlocks a GBP badge. Want me to draft a 'thank you' post to push the last 5?"
- **Generic opening (avoid)**: "Congratulations on your growing reviews!"

---

## Family C: Event & Seasonal (External, Merchant-Facing)

### festival_upcoming
- **Count**: 6 (trg_006 + trg_061–065)
- **Urgency range**: 1–2
- **Scope**: merchant
- **Key payload fields**: `festival`, `date`, `days_until`, `category_relevance`
- **Best specificity anchor**: days_until + category-specific opportunity (bridal prep for salons, family feast bookings for restaurants)
- **High-quality opening**: "Lakshmi, Diwali is 188 days away — but bridal bookings for Oct-Nov festivals start now. 3 salons in Kapra launched their Bridal Trial package last week."
- **Generic opening (avoid)**: "Diwali is coming up soon, a great time to run promotions."

### category_seasonal
- **Count**: 1 (trg_020)
- **Urgency range**: 2
- **Scope**: merchant
- **Key payload fields**: `season`, `trends` (list of demand shifts with percentages)
- **Best specificity anchor**: exact demand shift percentages (ORS +40%, anti-fungal +45%)
- **High-quality opening**: "Ramesh, summer demand shift is here: ORS demand +40%, sunscreen +38%, anti-fungal +45% — and cold/cough down 60%. Time to rearrange the shelf."
- **Generic opening (avoid)**: "Summer is here and demand patterns are changing."

### ipl_match_today
- **Count**: 1 (trg_010)
- **Urgency range**: 3
- **Scope**: merchant
- **Key payload fields**: `match`, `venue`, `city`, `match_time_iso`, `is_weeknight`
- **Best specificity anchor**: specific match + data insight about weekend vs weeknight (Saturday IPL = -12% covers)
- **High-quality opening**: "Quick heads-up Suresh — DC vs MI at Arun Jaitley tonight, 7:30pm. Saturday IPL = -12% covers (people watch at home). Skip the match-night promo; push your BOGO as delivery-only instead."
- **Generic opening (avoid)**: "There's an IPL match tonight — great time to run a promotion!"

---

## Family D: Activation & Account Health (Internal, Merchant-Facing)

### dormant_with_vera
- **Count**: 6 (trg_025 + trg_046–050)
- **Urgency range**: 2
- **Scope**: merchant
- **Key payload fields**: `days_since_last_merchant_message`, `last_topic`
- **Best specificity anchor**: days since last contact + something new in the merchant's data since last touch
- **High-quality opening**: "Anand, it's been 38 days — since then, your CTR climbed to 2.5% (above the 2.5% restaurant peer median). Quick check: what's been moving for you in Sector 8?"
- **Generic opening (avoid)**: "Hi! We haven't spoken in a while."

### winback_eligible
- **Count**: 1 (trg_009)
- **Urgency range**: 2
- **Scope**: merchant
- **Key payload fields**: `days_since_expiry`, `perf_dip_pct`, `lapsed_customers_added_since_expiry`
- **Best specificity anchor**: lapsed customers accrued + perf dip percentage (loss aversion)
- **High-quality opening**: "Anjali, since your subscription expired 38 days ago: 24 new customer lapse events, and your CTR has dropped 30%. The gap is growing — want to see what a quick restart looks like?"
- **Generic opening (avoid)**: "It's been a while since your subscription ended."

### renewal_due
- **Count**: 6 (trg_005 + trg_091–095)
- **Urgency range**: 4
- **Scope**: merchant
- **Key payload fields**: `days_remaining`, `plan`, `renewal_amount`
- **Best specificity anchor**: exact days remaining + what pauses when it lapses (profile maintenance, campaigns)
- **High-quality opening**: "Bharat, Pro plan expires in 12 days (₹4,999 to renew). Your CTR is already 40% below the Mumbai peer median — without the plan, GBP posts pause too. Want me to draft the renewal note?"
- **Generic opening (avoid)**: "Your subscription is expiring soon."

### gbp_unverified
- **Count**: 1 (trg_021)
- **Urgency range**: 3
- **Scope**: merchant
- **Key payload fields**: `verified`, `verification_path`, `estimated_uplift_pct`
- **Best specificity anchor**: 30% estimated uplift + specific verification path + time estimate
- **High-quality opening**: "Vikas, Sunrise Medicos is unverified on GBP — verified pharmacies in Lucknow see ~30% higher click-through. Verification via postcard takes 5-7 days. Want me to start the process?"
- **Generic opening (avoid)**: "Your Google Business Profile needs to be verified."

### competitor_opened
- **Count**: 6 (trg_023 + trg_056–060)
- **Urgency range**: 2
- **Scope**: merchant
- **Key payload fields**: `competitor_name`, `distance_km`, `their_offer`, `opened_date`
- **Best specificity anchor**: competitor name + distance + their specific offer vs your offer
- **High-quality opening**: "Dr. Meera, Smile Studio opened 1.3km from you on April 8 — they're running Dental Cleaning @ ₹199 (vs your ₹299). Want to talk positioning strategy?"
- **Generic opening (avoid)**: "A new competitor has opened near you."

### review_theme_emerged
- **Count**: 6 (trg_011 + trg_051–055)
- **Urgency range**: 3
- **Scope**: merchant
- **Key payload fields**: `theme`, `occurrences_30d`, `trend`, `common_quote`
- **Best specificity anchor**: exact count + direct quote from reviews + concrete fix action
- **High-quality opening**: "Suresh, 4 reviews this month mention delivery latency — top quote: 'took 50 mins for a 15 min ride.' Quick fix: add a delivery-time-estimate to your order confirmation. Want me to draft the Swiggy message?"
- **Generic opening (avoid)**: "Some customers have mentioned delivery times in their reviews."

---

## Family E: Conversation & Planning (Internal, Merchant-Facing)

### curious_ask_due
- **Count**: 6 (trg_008 + trg_096–100)
- **Urgency range**: 1
- **Scope**: merchant
- **Key payload fields**: `ask_template`, `last_ask_at`
- **Best specificity anchor**: the ask itself + a specific deliverable the bot will produce from the answer
- **High-quality opening**: "Hi Lakshmi — quick one: what service has been most asked-for at Studio11 this week? I'll turn the answer into a Google post + pricing reply template. 5 min."
- **Generic opening (avoid)**: "Hi! Just checking in to see how things are going."

### active_planning_intent
- **Count**: 2 (trg_013, trg_016)
- **Urgency range**: 4
- **Scope**: merchant
- **Key payload fields**: `intent_topic`, `merchant_last_message`
- **Best specificity anchor**: complete drafted artifact delivered — the merchant said "yes, what would it look like?" → answer that question specifically
- **High-quality opening**: "Suresh, here's a starter version for the corporate thali package — [full pricing tiers + radius + target offices]. Edit and send, or say go and I'll draft the outreach."
- **Generic opening (avoid)**: "Great idea! Here are some things to consider about corporate catering."

---

## Family F: Customer Recall & Booking (Internal, Customer-Facing)

### recall_due
- **Count**: 6 (trg_003 + trg_066–070)
- **Urgency range**: 3
- **Scope**: customer
- **Key payload fields**: `service_due`, `last_service_date`, `due_date`, `available_slots`
- **Best specificity anchor**: specific due date + actual available slots + price + any add-on
- **High-quality opening**: "Hi Priya, Dr. Meera's clinic here 🦷 It's been 5 months — your 6-month cleaning recall is due. 2 slots: Wed 5 Nov 6pm or Thu 6 Nov 5pm. ₹299 + complimentary fluoride."
- **Generic opening (avoid)**: "Hi! It's been a while since your last dental visit."

### appointment_tomorrow
- **Count**: 5 (trg_076–080; all generated/placeholder)
- **Urgency range**: 2
- **Scope**: customer
- **Key payload fields**: placeholder — only `metric_or_topic: "appointment_tomorrow"` (LOW DATA CONFIDENCE)
- **Best specificity anchor**: appointment time + service + merchant name (must be derived from merchant context, not trigger payload)
- **High-quality opening**: "Hi Aditya, reminder from Karim's Salon Alambagh — your appointment is tomorrow. Reply 1 to confirm, 2 to reschedule."
- **Generic opening (avoid)**: "Don't forget your appointment tomorrow!"

### trial_followup
- **Count**: 6 (trg_017 + trg_086–090)
- **Urgency range**: 2
- **Scope**: customer
- **Key payload fields**: `trial_date`, `next_session_options` (trg_017 only; generated ones have placeholder)
- **Best specificity anchor**: named trial class + specific next session date + no-commitment framing
- **High-quality opening**: "Hi Karthik's parent, Padma from Zen Yoga here — Karthik attended the kids yoga trial Tue 22 Apr. His next session: Sat 3 May, 8am. Reply YES to hold the spot — no commitment yet."
- **Generic opening (avoid)**: "We hope Karthik enjoyed his trial class!"

### wedding_package_followup
- **Count**: 1 (trg_007)
- **Urgency range**: 2
- **Scope**: customer
- **Key payload fields**: `wedding_date`, `trial_completed`, `days_to_wedding`, `next_step_window_open`
- **Best specificity anchor**: days-to-wedding countdown + specific package with price + preferred day blocked
- **High-quality opening**: "Hi Kavya 💍 Lakshmi from Studio11 Kapra — 196 days to your wedding, perfect window for the 30-day skin-prep program. ₹2,499 covers 4 sessions + take-home kit. Want me to block your Saturday 4pm slot?"
- **Generic opening (avoid)**: "Congratulations on your upcoming wedding! We'd love to help you prepare."

---

## Family G: Customer Retention & Care (Internal, Customer-Facing)

### customer_lapsed_soft
- **Count**: 5 (trg_071–075; all generated/placeholder)
- **Urgency range**: 3
- **Scope**: customer
- **Key payload fields**: placeholder — only `metric_or_topic: "customer_lapsed_soft"` (LOW DATA)
- **Best specificity anchor**: last visit date (from customer.relationship) + specific re-engagement offer from merchant catalog
- **High-quality opening**: "Hi Reyansh, Dr. Asha's clinic here — it's been about 3 months since your last visit. We have a Dental Cleaning slot open this week at ₹299. Want to book?"
- **Generic opening (avoid)**: "Hi! We miss seeing you at our clinic."

### customer_lapsed_hard
- **Count**: 1 (trg_015)
- **Urgency range**: 3
- **Scope**: customer
- **Key payload fields**: `days_since_last_visit`, `previous_focus`, `previous_membership_months`
- **Best specificity anchor**: specific days since last visit + customer's previous goal/focus + new specific offering matching that goal
- **High-quality opening**: "Hi Rashmi 👋 Karthik from PowerHouse — it's been about 8 weeks. We added a Tue/Thu evening HIIT class that fits weight-loss goals well (45 min, 6:30pm). Free trial spot for Tue 30 Apr? Reply YES — no commitment, no auto-charge."
- **Generic opening (avoid)**: "Hi Rashmi! We haven't seen you in a while and we miss you!"

### chronic_refill_due
- **Count**: 6 (trg_019 + trg_081–085)
- **Urgency range**: 2–3
- **Scope**: customer
- **Key payload fields**: `molecule_list`, `last_refill`, `stock_runs_out_iso`, `delivery_address_saved`
- **Best specificity anchor**: exact molecule names + run-out date + total with savings + free delivery
- **High-quality opening**: "Namaste — Apollo Health Plus Malviya Nagar. Sharma ji ki 3 medicines (metformin, atorvastatin, telmisartan) 28 April ko khatam hongi. Total ₹1,420 (₹240 saved). Free delivery by 5pm tomorrow. Reply CONFIRM."
- **Generic opening (avoid)**: "Your medicines are running out soon!"

---

## Trigger Kind Summary Table

| Kind | Count | Urgency | Scope | Data Quality | Profile |
|---|---|---|---|---|---|
| research_digest | 6 | 1-2 | merchant | HIGH (seed) / MED (gen) | knowledge_digest |
| regulation_change | 1 | 4 | merchant | HIGH | knowledge_digest |
| cde_opportunity | 1 | 1 | merchant | HIGH | knowledge_digest |
| supply_alert | 1 | 5 | merchant | HIGH | knowledge_digest |
| perf_dip | 6 | 3-4 | merchant | HIGH (seed) / LOW (gen) | perf_dip_recovery |
| seasonal_perf_dip | 1 | 1 | merchant | HIGH | perf_dip_recovery |
| perf_spike | 6 | 1 | merchant | HIGH (seed) / LOW (gen) | perf_win |
| milestone_reached | 6 | 1 | merchant | HIGH (seed) / LOW (gen) | perf_win |
| festival_upcoming | 6 | 1-2 | merchant | HIGH (seed) / LOW (gen) | event_seasonal |
| category_seasonal | 1 | 2 | merchant | HIGH | event_seasonal |
| ipl_match_today | 1 | 3 | merchant | HIGH | event_seasonal |
| dormant_with_vera | 6 | 2 | merchant | HIGH (seed) / LOW (gen) | activation_urgency |
| winback_eligible | 1 | 2 | merchant | HIGH | activation_urgency |
| renewal_due | 6 | 4 | merchant | HIGH (seed) / LOW (gen) | activation_urgency |
| gbp_unverified | 1 | 3 | merchant | HIGH | activation_urgency |
| competitor_opened | 6 | 2 | merchant | HIGH (seed) / LOW (gen) | activation_urgency |
| review_theme_emerged | 6 | 3 | merchant | HIGH (seed) / LOW (gen) | activation_urgency |
| curious_ask_due | 6 | 1 | merchant | HIGH (seed) / LOW (gen) | planning_curiosity |
| active_planning_intent | 2 | 4 | merchant | HIGH | planning_curiosity |
| recall_due | 6 | 3 | customer | HIGH (seed) / LOW (gen) | customer_recall |
| appointment_tomorrow | 5 | 2 | customer | LOW (all gen) | customer_recall |
| trial_followup | 6 | 2 | customer | HIGH (seed) / LOW (gen) | customer_recall |
| wedding_package_followup | 1 | 2 | customer | HIGH | customer_recall |
| customer_lapsed_soft | 5 | 3 | customer | LOW (all gen) | customer_winback |
| customer_lapsed_hard | 1 | 3 | customer | HIGH | customer_winback |
| chronic_refill_due | 6 | 2-3 | customer | HIGH (seed) / LOW (gen) | customer_winback |

**Total**: 100 triggers across 26 kinds
- Merchant-facing: 74 triggers (19 kinds)
- Customer-facing: 26 triggers (7 kinds)
- External source: 27 triggers
- Internal source: 73 triggers
- HIGH data confidence (seed): 25 triggers
- PLACEHOLDER data (generated): 75 triggers
