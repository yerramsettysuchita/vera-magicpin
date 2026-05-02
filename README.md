# Vera — magicpin AI Challenge Submission

**Vera** is a deterministic AI engagement assistant for Indian merchants on magicpin. Given a trigger event, a merchant profile, and optional customer context, it composes a WhatsApp message that is hyper-specific, correctly voiced for the business category, and structured to compel a reply.

---

## Decision Quality Framework

The single most important design choice: **the routing decision is made before any LLM is called.**

Every incoming trigger is classified in pure Python in under 5ms. The classifier outputs a `profile_id`, a primary lever, and a `send_as` identity. Only then is an LLM call made — using a specialized system prompt written for that exact profile. This means the "what to say and why" is decided deterministically; the LLM's only job is to express it well.

This is what the judge scores as Decision Quality: not whether the message is fluent, but whether the bot picked the right signal from all available context before composing anything.

**Signal selection priority:**
1. Trigger payload anchor (the single most specific fact: a date, a metric delta, a competitor name)
2. Merchant performance delta vs category peer median (peer comparison)
3. Conversation memory trace (last topic, session state)
4. Category voice fingerprint (what this business type can and cannot say)

Thin-data triggers get curiosity/asking levers. Rich-data triggers get specificity anchors and peer deltas. The classifier decides which path applies before the prompt is even loaded.

---

## 5-Layer Architecture

```
Trigger + Merchant + Customer + Category
         |
         v
  signal_classifier.py        <5ms, pure Python, zero LLM
  (26 trigger kinds -> 8 profile IDs)
  Output: profile_id, primary_lever, send_as, cta_type
         |
         v
  memory_trace.py              <1ms
  (last_topic, session_open, turn_count from conversation_history)
         |
         v
  context_distiller.py         <5ms
  (3-5 key facts: trigger anchor, peer delta, category voice,
   language fingerprint, memory trace)
         |
         v
  prompts/<profile_id>.txt     (8 files, cached in memory at startup)
  (lever rules, category voice, anti-patterns, CTA constraint,
   rationale template — all baked in per profile)
         |
         v
  Claude claude-sonnet-4-6     temperature=0, prompt cache on system prompt
  (compose body + cta + send_as + rationale as strict JSON)
         |
         v
  validator.py                 <2ms
  (anti-hallucination: number pool check | URL scan | jargon scan |
   CTA shape | language match | suppression key)
         |
  [if fail] re-prompt once with error list
  [if still fail] surface as warnings, never crash
         |
         v
  ComposedMessage {body, cta, send_as, suppression_key, rationale}
```

**Layer 4 — Reply Simulator (optional):** `reply_simulator.py` makes a second LLM call using `claude-haiku-4-5-20251001` at temperature=0.7. It simulates 3 likely merchant replies and scores YES-path ease (1–10). Messages averaging below 6 are flagged for revision. This directly optimises the Engagement Compulsion scoring dimension that most bots leave on the table.

---

## The 8 Trigger Profiles

| Profile | Trigger kinds | Primary lever | send_as |
|---|---|---|---|
| `knowledge_digest` | research_digest, regulation_change, cde_opportunity, supply_alert | L1 Specificity | vera |
| `perf_dip_recovery` | perf_dip, seasonal_perf_dip | L1 Specificity + L2 Loss aversion | vera |
| `perf_win` | perf_spike, milestone_reached | L5 Curiosity | vera |
| `event_seasonal` | festival_upcoming, category_seasonal, ipl_match_today | L2 Loss aversion | vera |
| `activation_urgency` | dormant_with_vera, winback_eligible, renewal_due, gbp_unverified, competitor_opened | L2 Loss aversion | vera |
| `planning_curiosity` | curious_ask_due, active_planning_intent | L7 Asking / L4 Effort extension | vera |
| `customer_recall` | recall_due, appointment_tomorrow, trial_followup, chronic_refill_due | L8 Binary commitment | merchant_on_behalf |
| `customer_winback` | customer_lapsed_soft, customer_lapsed_hard, chronic_refill_due | L5 / L2+L8 by sub-kind | merchant_on_behalf |

---

## Key Design Decisions

**Deterministic routing before LLM.** `signal_classifier.py` maps every trigger kind to a profile ID in pure Python. Same input always produces the same routing decision. Failures are debuggable without touching the LLM. The correct system prompt — with the right lever, voice, and constraints — reaches the model every time.

**Context distillation over context dumping.** Raw 4-context input is ~4,000 tokens. `context_distiller.py` extracts 3–5 critical facts (~200 tokens): the trigger's single best anchor, the peer delta (merchant CTR vs category median), the category voice fingerprint, and the language fingerprint from conversation history. Leaner input means fewer hallucinations and sharper specificity scores.

**Prompt caching on system prompts.** All 8 prompts are loaded into memory at startup and passed to Claude with `cache_control: ephemeral`. Repeat calls to the same profile hit the Anthropic prompt cache, reducing input token cost by ~90% and latency from ~4s to ~1.5s on warm paths.

**Hard validator before delivery.** Every number in the composed body is cross-referenced against a pool of numbers from the input (trigger payload, merchant performance, customer relationship data). If a number cannot be traced to input, it is flagged as HALLUCINATION_RISK. URLs trigger a hard block. Technical jargon (internal field names) triggers a re-prompt. After one retry, remaining errors surface as warnings — a partial message is always better than no message.

**IPL contrarian rule — the highest-scoring single insight.** The `event_seasonal` prompt contains an explicit rule: if `is_weeknight = False` (Saturday/Sunday match), do not push a match-night promo. Weekend IPL = −12% restaurant covers. Instead advise the merchant to save their promotion for the next weeknight match (Tuesday/Wednesday/Thursday = +18% covers). This contrarian insight is verified present in T21 of the submission.

**`send_as` discipline.** Customer-facing messages (`customer_recall`, `customer_winback`) use `send_as: merchant_on_behalf` and never mention Vera or magicpin. The validator enforces this. Merchant-facing messages use `send_as: vera`.

**Language routing.** Language is determined by city (for merchant-facing) and `customer.language_pref` (for customer-facing). Rules: Lucknow/Jaipur/Kanpur/Patna = full Hindi; Delhi/Mumbai/Pune/Ahmedabad = hi-en; Chennai/Bengaluru/Hyderabad = English only. The distiller injects the language fingerprint into every user message; prompts enforce the register.

---

## Multi-Turn Conversation Handling

`conversation_handlers.py` implements a priority-ordered state machine that routes every merchant reply to the correct response type in under 2ms:

| Priority | Signal | Action |
|---|---|---|
| 1 | Hostile (`"stop"`, `"spam"`) | `{"action": "end"}` |
| 2 | Decline (`"no"`, `"not interested"`) | `{"action": "end"}` |
| 3 | Auto-reply (same message ≥3 times) | Acknowledge once → `{"action": "end"}` |
| 4 | Intent transition (`"haan ji"`, `"sure"`, `"let's do it"`) | `{"action": "continue", "body": "<next step>"}` |
| 5 | Off-topic (GST, loans) | Gentle redirect → `{"action": "continue"}` |
| 6 | Question | `{"action": "wait", "wait_seconds": 60}` |
| 7 | Short neutral (≤3 words) | `{"action": "wait", "wait_seconds": 120}` |
| 8 | Default | `{"action": "wait", "wait_seconds": 300}` |

---

## Performance Metrics

| Metric | Value |
|---|---|
| Test pairs routed correctly | 30 / 30 (100%) |
| Routing errors | 0 |
| Validation warnings on dry-run | 0 |
| Profiles used | 8 (all active) |
| Trigger kinds covered | 26+ |
| signal_classifier latency | <5ms (pure Python, zero LLM) |
| context_distiller latency | <5ms |
| validator latency | <2ms |
| LLM compose latency (warm cache) | ~1.5s per call |
| LLM compose latency (cold) | ~6–8s per call |
| submission.jsonl body length | avg 233 chars, min 160, max 334 |
| send_as=vera | 21 pairs |
| send_as=merchant_on_behalf | 9 pairs |
| Unit tests passing (no API key) | 6 / 6 |
| Anti-hallucination: numbers traceable to input | 100% |
| IPL contrarian rule verified | T21 confirmed |

---

## Repository Structure

```
vera_submission/
├── bot.py                      FastAPI server — all 5 judge endpoints
├── composer.py                 Main compose() pipeline (10-step orchestrator)
├── signal_classifier.py        Layer 1: deterministic trigger → profile router
├── context_distiller.py        Layer 2: 4-context → 3-5 facts extractor + peer delta
├── memory_trace.py             Layer 2b: conversation history → last topic + session state
├── validator.py                Layer 5: anti-hallucination, URL, jargon, CTA guardrails
├── reply_simulator.py          Layer 4: YES-path scoring via Haiku simulation
├── conversation_handlers.py    Multi-turn state machine (8-priority reply router)
├── run_all_pairs.py            Batch runner for all 30 canonical test pairs
├── build_submission.py         Deterministic submission.jsonl builder
├── judge_simulator.py          Local evaluation harness
├── benchmark.py                p50/p95/p99 latency profiler per profile
├── requirements.txt            Python dependencies
├── submission.jsonl            Final output: 30 lines, one JSON per test pair
│
├── prompts/                    8 system prompts, one per trigger profile
│   ├── knowledge_digest.txt
│   ├── perf_dip_recovery.txt
│   ├── perf_win.txt
│   ├── event_seasonal.txt      Contains IPL contrarian rule (weeknight vs weekend)
│   ├── activation_urgency.txt
│   ├── planning_curiosity.txt
│   ├── customer_recall.txt     Language rules, L8 binary commitment, no-Vera policy
│   └── customer_winback.txt    No-shame framing rule, sub-kind lever routing
│
├── expanded/                   Dataset: 50 merchants, 100 triggers, 200 customers
├── tests/
│   └── test_phase2.py          Unit tests (6 non-LLM, 4 LLM-gated)
└── dataset/                    Source seed files
```

---

## Running

```bash
# Install dependencies
pip install -r requirements.txt

# Start the bot server (port 8080 matches judge_simulator.py default)
ANTHROPIC_API_KEY=<key> uvicorn bot:app --host 0.0.0.0 --port 8080

# Generate submission.jsonl via LLM (requires API key)
ANTHROPIC_API_KEY=<key> python run_all_pairs.py

# Dry-run — classifier + distiller only, no LLM, safe to run anytime
python run_all_pairs.py --dry-run
# Note: dry-run writes to submission_dryrun.jsonl, never overwrites submission.jsonl

# Resume an interrupted LLM run
ANTHROPIC_API_KEY=<key> python run_all_pairs.py --resume

# Run specific pairs only
ANTHROPIC_API_KEY=<key> python run_all_pairs.py --test-ids T01 T09 T21

# Run judge simulator against live bot
python judge_simulator.py

# Run unit tests
python -m pytest tests/ -v
```

---

## Anti-Patterns Avoided

| Anti-pattern | How Vera avoids it |
|---|---|
| Hallucinated citations | Number pool validation in `validator.py` — every figure in body cross-referenced against input |
| Generic discount copy | Validator blocks percentage-off language when specific offer+price is available |
| Multiple CTAs | Validator enforces exactly one CTA per message, re-prompts if violated |
| Promotional tone for dentists | Category voice rules baked into each profile prompt; dentists never see "discount" language |
| URL injection | Hard regex block on all URL patterns — automatic -3 judge penalty avoided |
| Pattern-matching the 30 test pairs | Architecture is context-grounded via distiller; works on any trigger/merchant combination |
| Repeated topics | `suppression_key` deduplication + `memory_trace` last-topic guard prevent same-message repeats |

---

## What Additional Context Would Improve Scores

1. **Live offer catalog with pricing** — sharper specificity anchors on `activation_urgency` and `perf_dip_recovery` messages.
2. **Verified competitor pricing** — `competitor_opened` trigger has their offer; knowing the merchant's exact counter-price improves head-to-head framing.
3. **Customer visit timestamps** — lapsed thresholds are inferred from state labels; exact last-visit dates make the "it's been X weeks" anchor verifiable.
4. **Real-time peer benchmarks** — category peer medians are static; live CTR comparisons would sharpen every peer-delta anchor.
