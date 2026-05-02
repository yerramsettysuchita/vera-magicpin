"""
bot.py -- Vera FastAPI server, wired to the judge_simulator.py API contract.

Endpoints (all must respond within 30s):
  POST /v1/context   -- store category / merchant / trigger / customer context
  POST /v1/tick      -- compose messages for a batch of trigger IDs
  POST /v1/reply     -- handle inbound merchant message; return action
  GET  /v1/healthz   -- liveness check
  GET  /v1/metadata  -- pipeline info (team_name, model, profiles)

Run:
    uvicorn bot:app --host 0.0.0.0 --port 8080
    (judge_simulator.py defaults to localhost:8080)

Env vars:
    ANTHROPIC_API_KEY  -- required for compose()
    VERA_LOG_LEVEL     -- DEBUG | INFO  (default: INFO)
    PORT               -- server port   (default: 8080)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

# -- Logging ------------------------------------------------------------------

_LOG_LEVEL = os.environ.get("VERA_LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=_LOG_LEVEL,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s',
    datefmt="%H:%M:%S",
)
_log = logging.getLogger("vera.bot")

# -- In-process context store -------------------------------------------------
# Keyed by scope -> context_id -> payload
# Scopes: "category", "merchant", "trigger", "customer"
_store: dict[str, dict[str, Any]] = {
    "category": {},
    "merchant": {},
    "trigger": {},
    "customer": {},
}

# Version tracking (parallel to _store): scope -> context_id -> version
# Preloaded data has version 0; judge pushes version >= 1, always wins.
_store_meta: dict[str, dict[str, int]] = {
    "category": {},
    "merchant": {},
    "trigger": {},
    "customer": {},
}

# Conversation turn history keyed by conversation_id
_conv_history: dict[str, list[dict]] = {}

# -- Constants ----------------------------------------------------------------
_START_TIME = datetime.now(timezone.utc)
_VERSION = "1.0.0"
_TEAM_NAME = "Vera"
_MODEL_COMPOSER = "claude-sonnet-4-6"
_MODEL_SIMULATOR = "claude-haiku-4-5-20251001"
_TICK_TIMEOUT_S = 25
_MAX_ACTIONS_PER_TICK = int(os.environ.get("VERA_MAX_ACTIONS_PER_TICK", "20"))


# -- Lifespan: warm caches on startup -----------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    _log.info("Vera bot starting -- warming prompt cache")
    try:
        from composer import warm_prompt_cache
        loaded = warm_prompt_cache()
        _log.info(f"Prompts warmed: {loaded}")
    except Exception as exc:
        _log.warning(f"Prompt warm failed: {exc}")

    # Pre-load expanded dataset into store so cold ticks work without prior context push
    _preload_expanded_dataset()
    yield
    _log.info("Vera bot shutting down")


def _preload_expanded_dataset():
    """Load expanded dataset files into the context store at startup."""
    from pathlib import Path
    expanded = Path(PROJECT_ROOT) / "expanded"
    if not expanded.exists():
        return

    loaded = {"merchant": 0, "trigger": 0, "customer": 0, "category": 0}

    for scope in ("merchants", "triggers", "customers"):
        scope_singular = scope.rstrip("s")
        d = expanded / scope
        if d.exists():
            for f in d.glob("*.json"):
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                    id_field = {
                        "merchants": "merchant_id",
                        "triggers": "id",
                        "customers": "customer_id",
                    }[scope]
                    cid = data.get(id_field, f.stem)
                    _store[scope_singular][cid] = data
                    _store_meta[scope_singular][cid] = 0  # preloaded = version 0
                    loaded[scope_singular] += 1
                except Exception:
                    pass

    cat_dir = expanded / "categories"
    if cat_dir.exists():
        for f in cat_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                slug = data.get("slug", f.stem)
                _store["category"][slug] = data
                _store_meta["category"][slug] = 0  # preloaded = version 0
                loaded["category"] += 1
            except Exception:
                pass

    _log.info(f"Preloaded: {loaded}")


app = FastAPI(
    title="Vera -- magicpin AI Engagement Bot",
    version=_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
)


# -- Request / Response models ------------------------------------------------

class ContextRequest(BaseModel):
    scope: str = Field(..., description="'category'|'merchant'|'trigger'|'customer'")
    context_id: str
    version: int = 1
    payload: dict[str, Any]
    delivered_at: str | None = None


class TickRequest(BaseModel):
    now: str | None = None
    available_triggers: list[str] = Field(..., description="List of trigger IDs to process")


class ReplyRequest(BaseModel):
    conversation_id: str
    merchant_id: str
    customer_id: str | None = None
    from_role: str = "merchant"
    message: str
    received_at: str | None = None
    turn_number: int = 1


# -- GET / (landing) -----------------------------------------------------------

@app.get("/")
async def root():
    return {
        "name": "Vera",
        "description": "magicpin AI Engagement Bot — merchant message composer",
        "version": _VERSION,
        "status": "live",
        "endpoints": {
            "healthz":  "GET  /v1/healthz",
            "metadata": "GET  /v1/metadata",
            "context":  "POST /v1/context",
            "tick":     "POST /v1/tick",
            "reply":    "POST /v1/reply",
        },
        "docs": "/docs",
    }


# -- Middleware: request timing ------------------------------------------------

@app.middleware("http")
async def log_requests(request: Request, call_next):
    t0 = time.monotonic()
    response = await call_next(request)
    elapsed_ms = int((time.monotonic() - t0) * 1000)
    _log.info(f"{request.method} {request.url.path} -> {response.status_code} ({elapsed_ms}ms)")
    return response


# -- POST /v1/context ----------------------------------------------------------

_VALID_SCOPES = {"category", "merchant", "trigger", "customer"}


@app.post("/v1/context")
async def push_context(req: ContextRequest) -> dict:
    """
    Store a context blob. Idempotent by (context_id, version).
    - invalid scope   → 400 invalid_scope
    - same version    → no-op, accepted=true
    - incoming < stored → 409 stale_version (spec §2.1)
    - incoming > stored → replace atomically, accepted=true
    """
    scope = req.scope.lower()

    # 400 for unknown scope
    if scope not in _VALID_SCOPES:
        return JSONResponse(
            status_code=400,
            content={
                "accepted": False,
                "reason": "invalid_scope",
                "details": f"scope must be one of {sorted(_VALID_SCOPES)}, got '{scope}'",
            },
        )

    if scope not in _store:
        _store[scope] = {}
        _store_meta[scope] = {}

    stored_version = _store_meta.get(scope, {}).get(req.context_id, -1)
    incoming_version = req.version
    now_iso = datetime.now(timezone.utc).isoformat()
    ack_id = f"ack_{req.context_id}_v{incoming_version}"

    if incoming_version < stored_version:
        # 409 — judge already pushed a newer version; this is stale
        return JSONResponse(
            status_code=409,
            content={
                "accepted": False,
                "reason": "stale_version",
                "current_version": stored_version,
            },
        )

    if incoming_version == stored_version and req.context_id in _store.get(scope, {}):
        # Idempotent no-op — re-posting same version is a no-op per spec §2.1
        _log.debug(f"Context no-op: {scope}/{req.context_id} v{incoming_version}")
        return {"accepted": True, "ack_id": ack_id, "stored_at": now_iso}

    # Higher version or first write — replace atomically
    _store[scope][req.context_id] = req.payload
    _store_meta[scope][req.context_id] = incoming_version
    _log.debug(f"Context stored: {scope}/{req.context_id} v{incoming_version}")
    return {"accepted": True, "ack_id": ack_id, "stored_at": now_iso}


@app.get("/v1/context/{scope}/{context_id}")
async def get_context(scope: str, context_id: str) -> dict:
    entry = _store.get(scope, {}).get(context_id)
    if not entry:
        return JSONResponse(status_code=404, content={"error": f"Not found: {scope}/{context_id}"})
    version = _store_meta.get(scope, {}).get(context_id, 0)
    return {"scope": scope, "context_id": context_id, "version": version, "payload": entry}


# -- POST /v1/tick ------------------------------------------------------------

@app.post("/v1/tick")
async def tick(req: TickRequest) -> dict:
    """
    Main composition endpoint.

    Receives a list of trigger IDs. For each trigger:
      1. Look up trigger payload from store
      2. Look up merchant from trigger.merchant_id
      3. Look up customer from trigger.customer_id (if any)
      4. Look up category from merchant.category_slug
      5. Call compose() and collect the action

    Returns {"actions": [...]} up to MAX_ACTIONS_PER_TICK.
    """
    from composer import compose, ComposerError

    trigger_ids = req.available_triggers[:_MAX_ACTIONS_PER_TICK]
    actions = []
    loop = asyncio.get_event_loop()

    for trigger_id in trigger_ids:
        trigger = _store["trigger"].get(trigger_id)
        if not trigger:
            _log.warning(f"Trigger not found: {trigger_id}")
            continue

        merchant_id = trigger.get("merchant_id")
        customer_id = trigger.get("customer_id")

        merchant = _store["merchant"].get(merchant_id)
        if not merchant:
            _log.warning(f"Merchant not found: {merchant_id} for trigger {trigger_id}")
            continue

        customer = _store["customer"].get(customer_id) if customer_id else None
        category_slug = merchant.get("category_slug", "")
        category_ctx = _store["category"].get(category_slug, {})

        try:
            composed = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda t=trigger, m=merchant, c=customer, cat=category_ctx: compose(
                        trigger=t,
                        merchant=m,
                        customer=c,
                        category_ctx=cat,
                    ),
                ),
                timeout=_TICK_TIMEOUT_S,
            )
            merchant_name = (merchant.get("identity") or {}).get("name", merchant_id)
            conv_id = f"conv_{merchant_id}_{trigger_id}"
            actions.append({
                "conversation_id": conv_id,
                "merchant_id":    merchant_id,
                "customer_id":    customer_id,
                "send_as":        composed.send_as,
                "trigger_id":     trigger_id,
                "template_name":  f"vera_{composed.profile_id}_v1",
                "template_params": [merchant_name, trigger_id, composed.body[:60]],
                "body":           composed.body,
                "cta":            composed.cta,
                "suppression_key": composed.suppression_key,
                "rationale":      composed.rationale,
            })
            _log.info(f"Composed [{composed.profile_id}] for {merchant_id} ({composed.latency_ms}ms)")

        except asyncio.TimeoutError:
            _log.error(f"Timeout composing {trigger_id}")
        except ComposerError as exc:
            _log.error(f"ComposerError for {trigger_id}: {exc}")
        except Exception as exc:
            _log.error(f"Unexpected error for {trigger_id}: {exc}")

    return {"actions": actions}


# -- POST /v1/reply -----------------------------------------------------------

@app.post("/v1/reply")
async def handle_reply(req: ReplyRequest) -> dict:
    """
    Handle an inbound merchant message.

    Returns one of:
      {"action": "end"}                        -- bot stops (hostile / auto-reply / decline)
      {"action": "wait", "wait_seconds": N}    -- bot waits before retrying
      {"action": "continue", "body": "..."}    -- bot sends a follow-up message
    """
    from conversation_handlers import handle_merchant_reply

    # Build / extend conversation history
    history = _conv_history.setdefault(req.conversation_id, [])
    history.append({
        "from": "merchant",
        "msg": req.message,
        "turn": req.turn_number,
        "ts": req.received_at or datetime.now(timezone.utc).isoformat(),
    })

    merchant = _store["merchant"].get(req.merchant_id, {})
    result = handle_merchant_reply(
        turns=history,
        merchant=merchant,
        conversation_id=req.conversation_id,
    )

    # Translate internal "continue" action to judge-facing "send"
    if result.get("action") == "continue":
        result = dict(result)
        result["action"] = "send"

    # Append bot response to history if sending
    if result.get("action") == "send" and result.get("body"):
        history.append({
            "from": "vera",
            "msg": result["body"],
            "turn": req.turn_number + 1,
        })

    _log.info(
        f"Reply [{req.conversation_id}] turn={req.turn_number} "
        f"state={result.get('_state','?')} -> action={result.get('action')}"
    )

    # Strip internal fields before returning
    return {k: v for k, v in result.items() if not k.startswith("_")}


# -- GET /v1/healthz ----------------------------------------------------------

@app.get("/v1/healthz")
async def healthz() -> dict:
    """Liveness + readiness check."""
    checks: dict[str, str] = {}
    ok = True

    if os.environ.get("ANTHROPIC_API_KEY"):
        checks["llm_api_key"] = "ok (anthropic)"
    elif os.environ.get("OPENROUTER_API_KEY"):
        checks["llm_api_key"] = "ok (openrouter)"
    else:
        checks["llm_api_key"] = "missing (set ANTHROPIC_API_KEY or OPENROUTER_API_KEY)"
        ok = False

    from signal_classifier import get_all_profiles
    from composer import _PROMPTS_DIR, _PROMPT_CACHE
    missing = [p for p in get_all_profiles()
               if p not in _PROMPT_CACHE and not (_PROMPTS_DIR / f"{p}.txt").exists()]
    checks["prompt_files"] = "ok (8/8)" if not missing else f"missing: {missing}"
    if missing:
        ok = False

    store_counts = {scope: len(items) for scope, items in _store.items()}
    checks["context_store"] = str(store_counts)

    uptime_s = (datetime.now(timezone.utc) - _START_TIME).total_seconds()
    contexts_loaded = {scope: len(items) for scope, items in _store.items()}
    return JSONResponse(
        status_code=200 if ok else 503,
        content={
            "status": "ok" if ok else "degraded",
            "uptime_seconds": round(uptime_s, 1),
            "contexts_loaded": contexts_loaded,
            "version": _VERSION,
            "checks": checks,
            "ts": datetime.now(timezone.utc).isoformat(),
        },
    )


# -- GET /v1/metadata ---------------------------------------------------------

@app.get("/v1/metadata")
async def metadata() -> dict:
    """Pipeline metadata required by judge_simulator.py."""
    from signal_classifier import get_all_profiles
    from composer import get_retry_rate_stats

    return {
        "team_name":    _TEAM_NAME,
        "team_members": ["Vera"],
        "model":        _MODEL_COMPOSER,
        "approach":     (
            "5-layer deterministic pipeline: signal_classifier (pure Python, <5ms) → "
            "context_distiller (4-context → 200-token facts) → profile prompt (8 cached) → "
            "Claude claude-sonnet-4-6 (temperature=0) → validator (anti-hallucination). "
            "Routing is decided before any LLM call. IPL contrarian rule baked into event_seasonal prompt."
        ),
        "contact_email":  "manjunathroyalgimail@gmail.com",
        "version":        _VERSION,
        "submitted_at":   "2026-05-02T00:00:00Z",
        "simulator_model": _MODEL_SIMULATOR,
        "profiles":       get_all_profiles(),
        "max_actions_per_tick": _MAX_ACTIONS_PER_TICK,
        "levers": {
            "L1": "Specificity", "L2": "Loss aversion", "L3": "Social proof",
            "L4": "Effort externalization", "L5": "Curiosity", "L6": "Reciprocity",
            "L7": "Asking the merchant", "L8": "Binary commitment",
        },
        "retry_stats":  get_retry_rate_stats(),
        "store_counts": {scope: len(items) for scope, items in _store.items()},
    }


# -- POST /v1/teardown (optional) --------------------------------------------

@app.post("/v1/teardown")
async def teardown() -> dict:
    """Wipe all in-memory state at end of test window (§11 privacy rule)."""
    for scope in _store:
        _store[scope].clear()
    for scope in _store_meta:
        _store_meta[scope].clear()
    _conv_history.clear()
    _log.info("Teardown complete — all context and conversation state wiped")
    return {"wiped": True, "ts": datetime.now(timezone.utc).isoformat()}


# -- Dev server entrypoint ----------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(
        "bot:app",
        host="0.0.0.0",
        port=port,
        reload=os.environ.get("VERA_ENV") == "development",
        log_level=_LOG_LEVEL.lower(),
    )
