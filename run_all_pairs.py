"""
run_all_pairs.py -- Generate submission.jsonl for all 30 canonical test pairs.

Reads:
  expanded/test_pairs.json          -- 30 (test_id, trigger_id, merchant_id, customer_id) rows
  expanded/triggers/<id>.json       -- full trigger payloads
  expanded/merchants/<id>.json      -- full merchant records
  expanded/customers/<id>.json      -- full customer records (if applicable)
  expanded/categories/<slug>.json   -- category context

Writes:
  submission.jsonl                  -- 30 lines, one JSON object per pair

Usage:
  python run_all_pairs.py                    # run all 30 pairs
  python run_all_pairs.py --test-ids T01 T06 T21   # specific pairs only
  python run_all_pairs.py --dry-run          # classify+distil only, no LLM
  python run_all_pairs.py --resume           # skip already-written test IDs

Requires: ANTHROPIC_API_KEY (unless --dry-run)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
EXPANDED_DIR = PROJECT_ROOT / "expanded"
SUBMISSION_FILE = PROJECT_ROOT / "submission.jsonl"
SUBMISSION_DRYRUN_FILE = PROJECT_ROOT / "submission_dryrun.jsonl"

sys.path.insert(0, str(PROJECT_ROOT))


# -- Data loading -------------------------------------------------------------

def _load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _load_pairs() -> list[dict]:
    return _load_json(EXPANDED_DIR / "test_pairs.json")["pairs"]


def _resolve_pair(pair: dict) -> dict | None:
    """Load all context for a single test pair. Returns None if data missing."""
    trigger_path = EXPANDED_DIR / "triggers" / f"{pair['trigger_id']}.json"
    merchant_path = EXPANDED_DIR / "merchants" / f"{pair['merchant_id']}.json"

    if not trigger_path.exists():
        print(f"  [MISSING] trigger: {pair['trigger_id']}")
        return None
    if not merchant_path.exists():
        print(f"  [MISSING] merchant: {pair['merchant_id']}")
        return None

    trigger = _load_json(trigger_path)
    merchant = _load_json(merchant_path)

    customer = None
    if pair.get("customer_id"):
        cust_path = EXPANDED_DIR / "customers" / f"{pair['customer_id']}.json"
        if cust_path.exists():
            customer = _load_json(cust_path)
        else:
            print(f"  [WARN] customer not found: {pair['customer_id']} -- proceeding without")

    category_slug = merchant.get("category_slug", "")
    category_path = EXPANDED_DIR / "categories" / f"{category_slug}.json"
    category_ctx = _load_json(category_path) if category_path.exists() else {}

    return {
        "trigger": trigger,
        "merchant": merchant,
        "customer": customer,
        "category_ctx": category_ctx,
    }


# -- Dry-run (no LLM) ---------------------------------------------------------

def _dry_run_pair(test_id: str, ctx: dict) -> dict:
    from signal_classifier import classify
    from context_distiller import distill, format_for_prompt
    from memory_trace import extract as extract_trace

    trigger = ctx["trigger"]
    merchant = ctx["merchant"]
    customer = ctx.get("customer")

    clf = classify(trigger, merchant)
    trace = extract_trace(merchant)
    trigger["_trace"] = trace
    distilled = distill(
        trigger=trigger, merchant=merchant,
        customer=customer or {}, category_ctx=ctx.get("category_ctx", {}), trace=trace,
    )
    prompt_preview = format_for_prompt(distilled)[:120]

    owner = (merchant.get("identity") or {}).get("owner_first_name", "merchant")
    return {
        "test_id":        test_id,
        "body":           f"[DRY-RUN] {owner} -- {clf.profile_id} profile, L{clf.primary_lever}",
        "cta":            "[dry-run CTA]",
        "send_as":        clf.send_as,
        "suppression_key": trigger.get("suppression_key", f"{test_id}:dry-run"),
        "rationale":      f"dry-run: {clf.profile_id} | lever L{clf.primary_lever} | {prompt_preview}...",
        "_latency_ms":    0,
        "_profile_id":    clf.profile_id,
        "_validation_ok": True,
    }


# -- Full LLM compose ---------------------------------------------------------

def _compose_pair(test_id: str, ctx: dict) -> dict:
    from composer import compose

    t0 = time.monotonic()
    composed = compose(
        trigger=ctx["trigger"],
        merchant=ctx["merchant"],
        customer=ctx.get("customer"),
        category_ctx=ctx.get("category_ctx"),
    )
    latency_ms = int((time.monotonic() - t0) * 1000)

    return {
        "test_id":        test_id,
        "body":           composed.body,
        "cta":            composed.cta,
        "send_as":        composed.send_as,
        "suppression_key": composed.suppression_key,
        "rationale":      composed.rationale,
        "_latency_ms":    latency_ms,
        "_profile_id":    composed.profile_id,
        "_validation_ok": composed.validation.ok if composed.validation else True,
        "_warnings":      composed.validation.warnings if composed.validation else [],
    }


# -- Submission writer --------------------------------------------------------

def _write_result(result: dict, f) -> None:
    """Write one line to the submission JSONL, stripping internal fields."""
    submission_row = {k: v for k, v in result.items() if not k.startswith("_")}
    f.write(json.dumps(submission_row, ensure_ascii=False) + "\n")
    f.flush()


# -- Main ---------------------------------------------------------------------

def run(
    test_ids: list[str] | None = None,
    dry_run: bool = False,
    resume: bool = False,
) -> None:
    pairs = _load_pairs()
    if test_ids:
        pairs = [p for p in pairs if p["test_id"] in test_ids]

    # Resume mode: skip already-written test IDs
    already_written: set[str] = set()
    if resume and SUBMISSION_FILE.exists():
        with open(SUBMISSION_FILE, encoding="utf-8") as f:
            for line in f:
                try:
                    already_written.add(json.loads(line)["test_id"])
                except Exception:
                    pass
        print(f"Resume mode: {len(already_written)} pairs already written, skipping.")

    mode = "DRY-RUN" if dry_run else "LLM COMPOSE"
    # Dry-run writes to a separate file to protect the real submission.jsonl
    output_file = SUBMISSION_DRYRUN_FILE if dry_run else SUBMISSION_FILE
    print(f"\nVera -- run_all_pairs.py [{mode}]")
    print(f"Output: {output_file}")
    print("-" * 60)

    write_mode = "a" if resume else "w"
    results_summary = []

    with open(output_file, write_mode, encoding="utf-8") as out:
        for pair in pairs:
            test_id = pair["test_id"]
            if test_id in already_written:
                print(f"  [{test_id}] SKIP (already written)")
                continue

            print(f"  [{test_id}] {pair['trigger_id'][:50]}...", end=" ", flush=True)

            ctx = _resolve_pair(pair)
            if ctx is None:
                print("DATA MISSING")
                continue

            try:
                if dry_run:
                    result = _dry_run_pair(test_id, ctx)
                else:
                    result = _compose_pair(test_id, ctx)

                _write_result(result, out)

                status = "OK" if result.get("_validation_ok", True) else "WARN"
                latency = result.get("_latency_ms", 0)
                profile = result.get("_profile_id", "?")
                print(f"[{status}] {latency}ms [{profile}]")

                results_summary.append({
                    "test_id":    test_id,
                    "profile_id": profile,
                    "latency_ms": latency,
                    "ok":         result.get("_validation_ok", True),
                    "warnings":   result.get("_warnings", []),
                })

            except Exception as exc:
                print(f"ERROR: {exc}")
                results_summary.append({
                    "test_id": test_id,
                    "error": str(exc),
                    "ok": False,
                })

    # Final summary
    print("\n" + "=" * 60)
    print(f"  SUBMISSION SUMMARY  ({len(results_summary)} pairs)")
    print("=" * 60)
    ok_count = sum(1 for r in results_summary if r.get("ok"))
    warn_count = sum(1 for r in results_summary if not r.get("ok") and "error" not in r)
    err_count = sum(1 for r in results_summary if "error" in r)
    total_ms = sum(r.get("latency_ms", 0) for r in results_summary)

    print(f"  OK:    {ok_count}")
    print(f"  WARN:  {warn_count}")
    print(f"  ERROR: {err_count}")
    if results_summary:
        print(f"  Avg latency: {total_ms // len(results_summary)}ms")
    print(f"  Output: {output_file}")

    # Per-profile breakdown
    from collections import Counter
    profile_counts = Counter(r.get("profile_id", "?") for r in results_summary)
    print("\n  By profile:")
    for profile, count in sorted(profile_counts.items()):
        print(f"    {profile:<26} {count} pairs")
    print("=" * 60)

    # Flag any warnings
    warnings_found = [(r["test_id"], r["warnings"]) for r in results_summary if r.get("warnings")]
    if warnings_found:
        print("\n  VALIDATION WARNINGS:")
        for tid, warns in warnings_found:
            for w in warns:
                print(f"  [{tid}] {w}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate submission.jsonl for all 30 test pairs")
    parser.add_argument("--test-ids", nargs="+", help="Specific test IDs to run (e.g. T01 T06)")
    parser.add_argument("--dry-run", action="store_true", help="Skip LLM -- classifier+distiller only")
    parser.add_argument("--resume", action="store_true", help="Skip already-written test IDs")
    args = parser.parse_args()

    has_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENROUTER_API_KEY")
    if not args.dry_run and not has_key:
        print("ERROR: Set ANTHROPIC_API_KEY or OPENROUTER_API_KEY. Use --dry-run to test without LLM.")
        sys.exit(1)

    run(
        test_ids=args.test_ids,
        dry_run=args.dry_run,
        resume=args.resume,
    )


if __name__ == "__main__":
    main()
