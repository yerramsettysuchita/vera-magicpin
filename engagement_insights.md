# Engagement Insights
## Phase 1 Intelligence — magicpin AI Challenge (Vera)

Compiled from `engagement-design.md` + `engagement-research.md`. These insights shape how Phase 2 must build the `compose()` function and every prompt.

---

## 1. The 4-Context Composition Architecture

The canonical composition function is `compose(category, merchant, trigger, customer?) → ComposedMessage`.

Each context answers a different question:

| Context | Question | Refresh cadence |
|---------|----------|----------------|
| **Category** | How do we talk to *this type* of business? | Weekly (digest), monthly (voice/catalog) |
| **Merchant** | Who is this specific business, what's their state? | Daily (perf), real-time (conversation) |
| **Trigger** | Why are we messaging *right now*? | Per-event |
| **Customer** | Who is the merchant's customer, what's their state? | Per visit/interaction |

**Phase 2 implication**: The composer must consume all 4 contexts. Omitting any one of them degrades specificity. The trigger alone is never enough — without merchant context, all messages become generic.

---

## 2. Voice Architecture

### Category is what drives voice, not the trigger

The trigger kind creates the occasion; the category creates the voice. Same `perf_dip` trigger → different registers for dentist vs. restaurant vs. gym:
- Dentist: "Dr. Bharat, calls down 50% this week vs baseline 12"
- Restaurant: "Suresh, covers off this week — here's what weeknight data says"  
- Gym: "Karthik, new member calls dipping — here's the Apr-Jun seasonal context"

### The 5 category voices (from `category_voice_fingerprints.md`)

| Category | Register | Taboo words | Key vocabulary |
|----------|----------|-------------|----------------|
| Dentists | Peer-clinical, source-cited | "AMAZING DEAL", "guaranteed results", "best dental clinic" | JIDA, DCI circular, caries, fluoride varnish, mSv, E-speed |
| Salons | Warm-practical, craft-knowledgeable | "miracle transformation", "guaranteed glow", "instant results" | Olaplex, balayage, keratin, bridal, slot times |
| Restaurants | Peer/operator, data-driven | "amazing food deals", "guaranteed packed house", "viral restaurant" | AOV, covers, table turnover, match-night, thali pull |
| Gyms | Coach-to-owner, energetic | "guaranteed weight loss", "shred in 7 days", "fastest results" | Churn, PT sessions, trial-to-paid, HIIT, membership |
| Pharmacies | Trustworthy-precise, compliance-first | "miracle cure", "best pharmacy", "doctor recommended" | Schedule H1, CDSCO alert, molecule names, batch numbers |

---

## 3. WhatsApp Session Window Rules

**Critical for CTA and send logic:**

1. The **24-hour session window** opens when a merchant or customer sends a message. Within that window, any free-form message can be sent.
2. **First outbound** (when no session is open) must use a **Kaleyra pre-approved template** — template_params must be filled correctly. Only certain words/formats are allowed.
3. **Template format**: Fill the `template_params` fields precisely; the body is pre-defined. Only the variable slots change.
4. **After first outbound**: Within 24h, all follow-up messages are free-form. This is why the `last_engagement` and `last_msg_topic` fields matter — they tell you if a session is still warm.

**Phase 2 implications**:
- Test pairs where `last_engagement=null` (T17, T20, T27) require template-format first messages
- Messages with a recent engagement tag (T01, T06) can use free-form
- For customer-facing pairs, check if a session is open before deciding free-form vs template

---

## 4. Merchant Context — What Already Exists

From `engagement-research.md`, the existing production system already provides most of `MerchantContext`:

| Field | Source | Location |
|-------|--------|----------|
| Identity (name, city, locality, verified) | `aryan_client.get_merchant_v2()` via `_load_merchant_data` | `vera-mcp/src/tools/merchant_info.py:188` |
| Subscription (status, days remaining) | `vera_get_subscription_status` | `vera-mcp` tool |
| Performance (views, calls, CTR) | `vera_get_performance_summary` in `_prefetch_product_context` | `merchant_agent.py:899` |
| Active offers | `vera_get_merchant_offer` + `_get_active_offers` | `vera-mcp` |
| Conversation history | `_behavioral_profile` + `_session_scenario` | `merchant_agent.py:740` |
| Review stats | `gbp_get_review_stats` via `build_merchant_snapshot()` | `vera-mcp/src/services/merchant_snapshot.py:51` |

**What does NOT exist in production** (but exists in challenge dataset):
- `CategoryContext` — completely absent; just a string in metadata
- `customer_aggregate` — no pipeline aggregates per-merchant cohort stats
- `TriggerContext` — no normalized abstraction; each cron has ad-hoc payloads
- Visit history per (merchant, customer_phone) — raw data in BOTOPS but no derived view
- Shared `EngagementComposer` — each agent has its own embedded prompt builder

**Phase 2 implication**: The challenge bot must simulate what production doesn't have. The dataset provides all 4 contexts fully populated — trust them.

---

## 5. Redis Cache TTL — 30 Min

The merchant context is cached for **30 minutes** at `vera:merchant_ctx:{merchant_id}`. 

- **Good for**: In-conversation reuse (most agents fire within 30 min of each other)
- **Problem for**: Daily/weekly engagement crons that fire once and miss cache 100% of the time → full snapshot rebuild cost per send

For the challenge bot: no caching layer to worry about. But in rationale fields, referencing that merchant data was "from today's snapshot" or "from the 30-min cached context" is a marker of production-awareness.

---

## 6. Aryan as the Synchronous Bottleneck

`aryan_client.get_merchant_v2()` is the **only path** to `category` and `locality`. It's a synchronous remote HTTP call:

- Slow aryan = slow every customer-info-pack call
- The recommended fix: cache aryan responses per merchant for ~24h before scaling send frequency

**Challenge bot implication**: The dataset provides `category_slug` and `locality` directly in the merchant data. The bot must use these directly — no need for aryan. But the rationale should note that in production, these come via aryan.

---

## 7. Customer Context Architecture

From `engagement-design.md`, `CustomerContext.state` follows this progression:

```
new → active → lapsed_soft (3-6 months) → lapsed_hard (6 months+) → churned (12 months+)
```

**Key behavioral rules**:
- `churned` = likely opted out or permanently disengaged — handle with extreme caution (T14 risk)
- `lapsed_soft` + `lapsed_hard` = recoverable — warm message, no guilt-trip
- `new` = first meaningful interaction — discovery-focused, no assumptions about history

**Consent model** (from design doc):
- Customer opted in **via merchant**, not via Vera
- Consent scope determines what messages are allowed (e.g., `recall_reminders` ≠ `promotional_offers`)
- T07 (grandfather) has `refill_reminders` scope — appropriate for chronic refill message
- T03 (Aditya at Karim) has only `promotional_offers` scope — appointment reminder is borderline; keep to confirmatory/non-promotional framing

---

## 8. Message Length + Structure

From both design doc examples and the case studies:

| Element | Rule |
|---------|------|
| **Opening line** | Single-line hook with the data anchor. No preamble ("I hope you're well, I'm reaching out because...") |
| **Body** | 2-3 lines maximum for merchant-facing; 1-2 lines for customer-facing |
| **CTA** | Last line only. Binary (Reply 1/2/YES) or single open question. Never two CTAs. |
| **Total length** | 3-5 lines for merchant. 2-3 lines for customer. Max 300 characters for binary CTAs. |
| **Emojis** | Category-appropriate. Dentists: none or 🦷. Salons: ✂️ 💆. Restaurants: none. Gyms: none or 💪. Pharmacies: none. |
| **Language mix** | Honor `language_pref` strictly. hi-en mix = natural code-switching. Pure hi = full Hindi. en = English only. |

**Anti-patterns penalized by judge**:
- Long preamble before the data point (−2 Engagement Compulsion)
- Multiple CTAs in one message (−2 Trigger Relevance)
- URL in the body (−3 hard penalty)
- Generic offers without price/service specificity (−2 Specificity)
- Re-introducing Vera to a customer in a merchant-on-behalf message (−1 Category Fit)
- Repeating exact same message topic from previous session (−2 anti-repetition penalty)

---

## 9. Hindi-English Code-Mix Rules

From category fingerprints and design examples:

| City | Pattern | Example |
|------|---------|---------|
| Lucknow, Jaipur (hi) | Full Hindi or hi-en mix | "Namaste Sharma ji, aapki medicines..." |
| Hyderabad, Chennai (te/ta) | English primary, occasional Telugu/Tamil marker | "Hi Padma, this week's yoga inquiries..." |
| Bangalore (kn) | English primary, occasional Kannada | "Suresh, namma Indiranagar thali pull is strong" |
| Delhi, Mumbai | Natural hi-en code-switch | "Meera, ye research aapke high-risk adult patients ke liye relevant hai" |
| Pune, Chandigarh | Mostly English | Standard English |

**Hard rules**:
- Customer `language_pref: "hi"` → full Hindi message body (T04: Riya)
- Customer `language_pref: "hi-en mix"` → code-switch naturally (T07: grandfather via son, T28: Priya)
- Customer `language_pref: "en"` → English only
- Senior citizen (65+, especially pharmacy) → "Namaste" as greeting, full molecule names, slower pacing

---

## 10. The send_as Distinction

| Value | Who "speaks" | Persona | When used |
|-------|-------------|---------|-----------|
| `"vera"` | Vera — the AI assistant | Signs off as Vera, speaks to merchant | All merchant-facing triggers |
| `"merchant_on_behalf"` | The merchant (via Vera's drafting) | "Hi Priya, Dr. Meera's clinic here" | All customer-facing triggers |

**Critical for customer-facing messages**:
- NEVER introduce "Vera" to a customer — the merchant is the sender
- Attribution pattern: `"{merchant_name} here"` or `"{merchant_name} clinic here"` or just `"{merchant_name}"`
- Vera signs off only in merchant-facing messages: `"— Vera"` or `"~ Vera"` where appropriate

---

## 11. Trigger Expiry Handling

| Trigger state | Action |
|--------------|--------|
| `expires_at` in future | Send normally |
| `expires_at` recently passed (< 24h) | Include urgency marker; send if still actionable |
| `expires_at` past by days | Check suppression_key; if already sent, suppress; if not sent, still compose but note staleness in rationale |

**Alert pairs**:
- T06 (CDE webinar): expires 2026-05-02 — tomorrow (current date 2026-05-01)
- T07 (chronic refill): stock ran out 2026-04-28 — 3 days ago; treat as overdue refill
- T21 (IPL match): expires 2026-04-26 — already expired by 5 days; compose the message for the trigger kind anyway (judge evaluates the composition, not timing)

---

## 12. Engagement Frequency Design Intent

From `engagement-design.md`:

The framework is designed for **3-5 messages per week per merchant**, up from the current "few times a month." This requires:

1. **Knowledge-driven messages** (research_digest, regulation_change, CDE) — external rhythm
2. **Performance-driven messages** (perf_dip/spike, milestone) — internal data-driven
3. **Event-driven messages** (festival, IPL, seasonal) — calendar-driven
4. **Curiosity-driven messages** (curious_ask, active_planning) — conversation-sustaining
5. **Customer-driven messages** (recall, winback, chronic_refill) — roster-driven

**Each category has a natural send rate**: Pharmacies have the highest frequency potential (chronic refills, compliance, seasonal demand shifts). Dentists are lower frequency but higher stakes per message (clinical precision required). Restaurants are highest event sensitivity (IPL, festivals).

---

## 13. Suppression Key Design

Every trigger has a `suppression_key` that the bot must echo back in the response:

```json
{"suppression_key": "recall:c_001_priya_for_m001:6mo"}
```

The suppression key prevents duplicate sends. The bot must:
1. Return the suppression_key from the trigger in the ComposedMessage
2. NOT generate its own suppression key (use the one from the trigger payload)
3. For placeholder triggers, the key is in format `{kind}:{merchant_id}:gen_{n}` — still return it as-is

---

## 14. Composer Architecture — Key Design Principles

From `engagement-design.md`:

1. **Single composer, kind-dispatched** — one `EngagementComposer.compose()` handles all 26 trigger kinds by dispatching to kind-specific prompt variants. The trigger `kind` field determines which prompt template is loaded.

2. **Versioned + auditable** — every send records the composer version + context hash. The challenge rationale field is the equivalent of this audit trail.

3. **No hardcoded values in the composer** — all specificity comes from the 4 input contexts. The composer is a transformer, not a template. If the input is thin (LOW confidence pair), the composer must still produce output — it uses category defaults rather than refusing.

4. **The `rationale` field is first-class** — the challenge requires a rationale on every composed message. This maps directly to the design principle of auditability. The rationale must explain: which context drove which element of the message, which lever was used, and any notable risks or choices.

---

## 15. Open Question — Offer Source of Truth

From `engagement-design.md` (open question 5):

> The canonical merchant offer catalog likely lives outside vera-mcp (aryan `catalogoffer`, merchant-portal-api, or magicpin_jobs output). MerchantContext needs to read from that source — pending identification.

**Challenge implication**: For seed merchants (HIGH confidence), active offers are in the dataset. For generated merchants (LOW confidence), `active_offers = []` — no offers available. In these cases:
- Use **category offer catalog defaults** (from `category_voice_fingerprints.md`)
- Frame the offer reference as "based on your typical services" rather than citing a specific active offer
- Never fabricate a price that isn't in the data or category defaults
