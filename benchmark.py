"""
benchmark.py -- Latency profiler for Vera's compose() pipeline.

Runs compose() against all 8 trigger profiles using seed data from
dataset/triggers_seed.json and dataset/merchants_seed.json.

Reports:
  - p50 / p95 / p99 latency per profile
  - Per-profile retry rate (validation failures)
  - Bottleneck identification

Usage:
    python benchmark.py                        # run all 8 profiles once
    python benchmark.py --runs 3               # 3 runs per profile
    python benchmark.py --profile event_seasonal  # single profile
    python benchmark.py --dry-run              # classifier + distiller only, no LLM

Requires: ANTHROPIC_API_KEY env var (unless --dry-run)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

DATASET_DIR = PROJECT_ROOT / "dataset"


# -- Seed data: one representative (trigger, merchant, customer?) per profile --

def _load_seeds() -> dict:
    with open(DATASET_DIR / "triggers_seed.json") as f:
        triggers = json.load(f)["triggers"]
    with open(DATASET_DIR / "merchants_seed.json") as f:
        merchants = {m["merchant_id"]: m for m in json.load(f)["merchants"]}
    with open(DATASET_DIR / "customers_seed.json") as f:
        customers_list = json.load(f)["customers"]
        customers = {c["customer_id"]: c for c in customers_list}
    return {"triggers": triggers, "merchants": merchants, "customers": customers}


# Map profile_id -> preferred trigger id from seed
_PROFILE_TO_TRIGGER = {
    "knowledge_digest":   "trg_022_cde_webinar_dentists",
    "perf_dip_recovery":  "trg_004_perf_dip_bharat",
    "perf_win":           "trg_012_milestone_mylari",
    "event_seasonal":     "trg_010_ipl_match_delhi",
    "activation_urgency": "trg_021_unverified_gbp_sunrise",
    "planning_curiosity": "trg_008_curious_ask_studio11",
    "customer_recall":    "trg_003_recall_due_priya",
    "customer_winback":   "trg_015_winback_rashmi",
}


def _build_pair(profile_id: str, seeds: dict) -> dict | None:
    tid = _PROFILE_TO_TRIGGER.get(profile_id)
    if not tid:
        return None
    trigger = next((t for t in seeds["triggers"] if t["id"] == tid), None)
    if not trigger:
        return None
    merchant = seeds["merchants"].get(trigger["merchant_id"])
    if not merchant:
        return None
    customer = None
    cid = trigger.get("customer_id")
    if cid:
        customer = seeds["customers"].get(cid)
    return {"trigger": trigger, "merchant": merchant, "customer": customer}


# -- Dry-run mode: skip LLM, only profile classifier + distiller --------------

def _dry_run_pair(pair: dict) -> dict:
    from signal_classifier import classify
    from memory_trace import extract as extract_trace
    from context_distiller import distill, format_for_prompt

    t0 = time.monotonic()
    clf = classify(pair["trigger"], pair["merchant"])
    trace = extract_trace(pair["merchant"])
    pair["trigger"]["_trace"] = trace
    distilled = distill(
        trigger=pair["trigger"],
        merchant=pair["merchant"],
        customer=pair.get("customer") or {},
        category_ctx={},
        trace=trace,
    )
    _ = format_for_prompt(distilled)
    elapsed_ms = int((time.monotonic() - t0) * 1000)
    return {
        "profile_id": clf.profile_id,
        "latency_ms": elapsed_ms,
        "validation_ok": True,
        "dry_run": True,
    }


# -- Full compose run ----------------------------------------------------------

def _compose_pair(pair: dict) -> dict:
    from composer import compose
    t0 = time.monotonic()
    result = compose(
        trigger=pair["trigger"],
        merchant=pair["merchant"],
        customer=pair.get("customer"),
    )
    elapsed_ms = int((time.monotonic() - t0) * 1000)
    return {
        "profile_id": result.profile_id,
        "latency_ms": elapsed_ms,
        "validation_ok": result.validation.ok if result.validation else True,
        "body_len": len(result.body),
        "cta_len": len(result.cta),
        "dry_run": False,
    }


# -- Stats calculation ---------------------------------------------------------

def _percentile(data: list[float], pct: int) -> float:
    if not data:
        return 0.0
    sorted_data = sorted(data)
    idx = int(len(sorted_data) * pct / 100)
    return sorted_data[min(idx, len(sorted_data) - 1)]


def _print_report(results_by_profile: dict[str, list[dict]]) -> None:
    SEP = "=" * 72
    DASH = "-" * 68
    print("\n" + SEP)
    print("  VERA COMPOSE() BENCHMARK REPORT")
    print(SEP)
    print(f"  {'Profile':<26}  {'Runs':>4}  {'p50':>6}  {'p95':>6}  {'p99':>6}  {'Retry%':>7}  {'Status'}")
    print("  " + DASH)

    all_latencies = []
    for profile_id, results in sorted(results_by_profile.items()):
        latencies = [r["latency_ms"] for r in results]
        all_latencies.extend(latencies)
        fails = sum(1 for r in results if not r.get("validation_ok", True))
        retry_pct = round(fails / len(results) * 100) if results else 0

        p50 = _percentile(latencies, 50)
        p95 = _percentile(latencies, 95)
        p99 = _percentile(latencies, 99)

        dry = "[dry-run]" if results and results[0].get("dry_run") else ""
        status = "SLOW" if p95 > 8000 else ("OK" if p95 < 5000 else "WARN")
        print(
            f"  {profile_id:<26}  {len(results):>4}  "
            f"{p50:>5.0f}ms  {p95:>5.0f}ms  {p99:>5.0f}ms  "
            f"{retry_pct:>6}%  {status} {dry}"
        )

    print("  " + DASH)
    overall_p50 = _percentile(all_latencies, 50)
    overall_p95 = _percentile(all_latencies, 95)
    print(f"  {'OVERALL':<26}  {len(all_latencies):>4}  {overall_p50:>5.0f}ms  {overall_p95:>5.0f}ms")
    print(SEP)

    # Bottleneck identification
    print("\n  BOTTLENECK ANALYSIS:")
    sorted_profiles = sorted(
        results_by_profile.items(),
        key=lambda kv: _percentile([r["latency_ms"] for r in kv[1]], 95),
        reverse=True,
    )
    for profile_id, results in sorted_profiles[:3]:
        p95 = _percentile([r["latency_ms"] for r in results], 95)
        fails = sum(1 for r in results if not r.get("validation_ok", True))
        retry_pct = round(fails / len(results) * 100) if results else 0
        reasons = []
        if p95 > 8000:
            reasons.append("LLM latency high -- consider max_tokens reduction")
        if retry_pct > 20:
            reasons.append(f"High retry rate ({retry_pct}%) -- prompt needs refinement")
        if not reasons:
            reasons.append("Within acceptable range")
        print(f"  [{profile_id}] p95={p95:.0f}ms: {'; '.join(reasons)}")

    print()


# -- Main ---------------------------------------------------------------------

def run_benchmark(
    profiles: list[str] | None = None,
    runs: int = 1,
    dry_run: bool = False,
) -> dict[str, list[dict]]:
    seeds = _load_seeds()

    from signal_classifier import get_all_profiles
    target_profiles = profiles or get_all_profiles()

    results_by_profile: dict[str, list[dict]] = {}

    for profile_id in target_profiles:
        pair = _build_pair(profile_id, seeds)
        if not pair:
            print(f"  [{profile_id}] No seed trigger found -- skipping")
            continue

        profile_results = []
        for run_i in range(runs):
            print(f"  [{profile_id}] run {run_i + 1}/{runs}...", end=" ", flush=True)
            try:
                if dry_run:
                    result = _dry_run_pair(pair)
                else:
                    result = _compose_pair(pair)
                profile_results.append(result)
                ok_str = "OK" if result.get("validation_ok", True) else "WARN"
                print(f"{result['latency_ms']}ms [{ok_str}]")
            except Exception as exc:
                print(f"ERROR: {exc}")
                profile_results.append({
                    "profile_id": profile_id,
                    "latency_ms": 0,
                    "validation_ok": False,
                    "error": str(exc),
                })

        results_by_profile[profile_id] = profile_results

    # Print retry rate stats from composer module
    if not dry_run:
        try:
            from composer import get_retry_rate_stats
            retry_stats = get_retry_rate_stats()
            if any(v["retries"] > 0 for v in retry_stats.values()):
                print("\n  VALIDATION RETRY RATES (from telemetry):")
                for profile, stat in sorted(retry_stats.items()):
                    if stat["calls"] > 0:
                        print(f"  [{profile}] {stat['retries']}/{stat['calls']} retries "
                              f"({stat['retry_rate']*100:.0f}%)")
        except ImportError:
            pass

    return results_by_profile


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark Vera compose() latency")
    parser.add_argument("--runs", type=int, default=1, help="Runs per profile (default: 1)")
    parser.add_argument("--profile", type=str, default=None, help="Single profile to benchmark")
    parser.add_argument("--dry-run", action="store_true", help="Skip LLM -- profile classifier+distiller only")
    parser.add_argument("--json-out", type=str, default=None, help="Write raw results to JSON file")
    args = parser.parse_args()

    if not args.dry_run and not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not set. Use --dry-run to profile without LLM.")
        sys.exit(1)

    profiles = [args.profile] if args.profile else None

    print(f"\nRunning Vera benchmark: profiles={profiles or 'all'}, runs={args.runs}, dry_run={args.dry_run}")
    print("-" * 72)

    results = run_benchmark(profiles=profiles, runs=args.runs, dry_run=args.dry_run)
    _print_report(results)

    if args.json_out:
        with open(args.json_out, "w") as f:
            json.dump(results, f, indent=2)
        print(f"Raw results written to {args.json_out}")


if __name__ == "__main__":
    main()
