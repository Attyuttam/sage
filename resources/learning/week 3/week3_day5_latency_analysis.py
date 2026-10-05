"""Week 3 Day 5 — Latency and Throughput Analysis.

This is a standalone learning script. It does not run new LLM inference.
It analyzes latency measurements already recorded in existing experiment result files.

Available data sources:
  - week3_day4_results.json:  6 runs across llama3.2 (3 runs) and llama3.1:8b (3 runs),
                               all 65 log entries, explicit prompt, temperature 0.0
  - week3_day3_results.json:  9 runs across 3 prompt variants (A/B/C),
                               all llama3.2, all 65 log entries, temperature 0.0

Absent data:
  - Week 3 Day 1 context experiment (5 / 15 / 30 / 65 entries): results were printed
    to stdout only — no JSON result file was saved. No latency-by-context-size data
    is available for re-analysis without running new LLM inference.

For samples of N < 20, P95 and P99 cannot be meaningfully estimated. Where the
sample is too small this script explicitly says so rather than reporting a number.
"""

import json
import statistics
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = PROJECT_ROOT / "resources" / "learning"

DAY4_RESULTS = RESULTS_DIR / "week3_day4_results.json"
DAY3_RESULTS = RESULTS_DIR / "week3_day3_results.json"

MIN_SAMPLE_FOR_P95 = 20   # Conventional minimum for reliable P95 estimation
MIN_SAMPLE_FOR_P99 = 100  # Conventional minimum for reliable P99 estimation


def load_json(path: Path) -> list[dict[str, Any]]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def latency_stats(values: list[float], label: str) -> dict[str, Any]:
    """Compute latency statistics for a list of observations.

    Omits percentiles that are not meaningful given the sample size.
    """
    n = len(values)
    sorted_vals = sorted(values)

    stats: dict[str, Any] = {
        "label": label,
        "n": n,
        "min_s": round(min(values), 3),
        "max_s": round(max(values), 3),
        "mean_s": round(statistics.mean(values), 3),
        "median_p50_s": round(statistics.median(values), 3),
    }

    if n >= MIN_SAMPLE_FOR_P95:
        p95_idx = int(0.95 * n) - 1
        stats["p95_s"] = round(sorted_vals[p95_idx], 3)
    else:
        stats["p95_s"] = f"NOT_RELIABLE (n={n}, need >={MIN_SAMPLE_FOR_P95})"

    if n >= MIN_SAMPLE_FOR_P99:
        p99_idx = int(0.99 * n) - 1
        stats["p99_s"] = round(sorted_vals[p99_idx], 3)
    else:
        stats["p99_s"] = f"NOT_RELIABLE (n={n}, need >={MIN_SAMPLE_FOR_P99})"

    # Approximate sequential throughput: one job at a time, no parallelism
    stats["throughput_per_hour_mean"] = round(3600 / stats["mean_s"], 2)
    stats["throughput_per_hour_median"] = round(3600 / stats["median_p50_s"], 2)

    return stats


def print_stats(stats: dict[str, Any]) -> None:
    print(f"\n  {'Label':<45} {stats['label']}")
    print(f"  {'Sample size (n)':<45} {stats['n']}")
    print(f"  {'Min':<45} {stats['min_s']}s")
    print(f"  {'Max':<45} {stats['max_s']}s")
    print(f"  {'Mean (average)':<45} {stats['mean_s']}s")
    print(f"  {'Median (P50)':<45} {stats['median_p50_s']}s")
    print(f"  {'P95':<45} {stats['p95_s']}")
    print(f"  {'P99':<45} {stats['p99_s']}")
    print(f"  {'Sequential throughput (mean-based)':<45} {stats['throughput_per_hour_mean']} analyses/hour")
    print(f"  {'Sequential throughput (median-based)':<45} {stats['throughput_per_hour_median']} analyses/hour")


def latency_ratio(a_mean: float, b_mean: float, a_label: str, b_label: str) -> None:
    ratio = round(b_mean / a_mean, 2)
    print(f"\n  {a_label} mean:  {a_mean}s")
    print(f"  {b_label} mean:  {b_mean}s")
    print(f"  Ratio ({b_label} / {a_label}):  {ratio}x slower")


def main() -> None:
    print("=" * 70)
    print("Week 3 Day 5: Latency and Throughput Analysis")
    print("=" * 70)

    # ─────────────────────────────────────────────────────────────────────────
    # SECTION 1 — Data Availability
    # ─────────────────────────────────────────────────────────────────────────
    print("\n" + "-" * 70)
    print("SECTION 1: Data Availability")
    print("-" * 70)

    if DAY4_RESULTS.exists():
        print(f"  [PRESENT]  {DAY4_RESULTS.name}")
    else:
        print(f"  [MISSING]  {DAY4_RESULTS.name}")

    if DAY3_RESULTS.exists():
        print(f"  [PRESENT]  {DAY3_RESULTS.name}")
    else:
        print(f"  [MISSING]  {DAY3_RESULTS.name}")

    print()
    print("  [ABSENT]   week3_day1_results.json")
    print("             -> Day 1 context experiment printed to stdout only.")
    print("             -> No latency-by-context-size data is available for")
    print("                re-analysis without running new LLM inference.")
    print("             -> Day 1 latency figures are therefore omitted rather")
    print("                than invented.")

    # ─────────────────────────────────────────────────────────────────────────
    # SECTION 2 — Model Comparison (Day 4: llama3.2 vs llama3.1:8b)
    # ─────────────────────────────────────────────────────────────────────────
    print("\n" + "-" * 70)
    print("SECTION 2: Model Comparison (Day 4 data — llama3.2 vs llama3.1:8b)")
    print("  Conditions: 65 log entries, explicit prompt, temperature 0.0")
    print("-" * 70)

    day4 = load_json(DAY4_RESULTS)
    ll32_latencies = [r["latency_seconds"] for r in day4 if r["model"] == "llama3.2"]
    ll31_latencies = [r["latency_seconds"] for r in day4 if r["model"] == "llama3.1:8b"]

    ll32_stats = latency_stats(ll32_latencies, "llama3.2 (3B) — Day 4, n=3")
    ll31_stats = latency_stats(ll31_latencies, "llama3.1:8b (8B) — Day 4, n=3")

    print_stats(ll32_stats)
    print()
    print_stats(ll31_stats)

    print("\n  --- Model Latency Ratio ---")
    latency_ratio(ll32_stats["mean_s"], ll31_stats["mean_s"], "llama3.2", "llama3.1:8b")

    print("\n  --- Sequential Throughput Comparison ---")
    print(f"  llama3.2 (mean-based):    {ll32_stats['throughput_per_hour_mean']} analyses/hour")
    print(f"  llama3.1:8b (mean-based): {ll31_stats['throughput_per_hour_mean']} analyses/hour")
    tp_ratio = round(ll32_stats["throughput_per_hour_mean"] / ll31_stats["throughput_per_hour_mean"], 2)
    print(f"  Throughput ratio:         llama3.2 is {tp_ratio}x more throughput-efficient")

    # ─────────────────────────────────────────────────────────────────────────
    # SECTION 3 — Prompt Variant Latency (Day 3 data)
    # ─────────────────────────────────────────────────────────────────────────
    print("\n" + "-" * 70)
    print("SECTION 3: Prompt Variant Latency (Day 3 data — llama3.2, 65 entries)")
    print("  Note: Variant A latency includes 3 retry attempts per run.")
    print("-" * 70)

    day3 = load_json(DAY3_RESULTS)
    for variant_id in ["Variant A", "Variant B", "Variant C"]:
        variant_records = [r for r in day3 if r["variant_id"] == variant_id]
        latencies = [r["latency_seconds"] for r in variant_records]
        variant_name = variant_records[0]["variant_name"] if variant_records else variant_id
        stats = latency_stats(latencies, f"{variant_id} ({variant_name}) — n=3")
        print_stats(stats)
        print()

    # ─────────────────────────────────────────────────────────────────────────
    # SECTION 4 — Combined llama3.2 View (Day 3 + Day 4 combined)
    # ─────────────────────────────────────────────────────────────────────────
    print("-" * 70)
    print("SECTION 4: Combined llama3.2 Latency View")
    print("  Sources: Day 3 Variants B+C (validated runs) + Day 4 llama3.2 runs")
    print("  Excluded: Day 3 Variant A (all validation failed; 9 retried attempts)")
    print("-" * 70)

    validated_day3_ll32 = [
        r["latency_seconds"]
        for r in day3
        if r["variant_id"] in ("Variant B", "Variant C") and r["success"]
    ]
    combined_ll32 = validated_day3_ll32 + ll32_latencies
    combined_stats = latency_stats(combined_ll32, f"llama3.2 combined validated runs (n={len(combined_ll32)})")
    print_stats(combined_stats)

    print("\n  NOTE: Even with n=9 combined observations, P95 and P99 remain")
    print("  NOT RELIABLE. A minimum of 20 observations is required for P95")
    print("  and 100 for P99 to carry statistical meaning.")

    # ─────────────────────────────────────────────────────────────────────────
    # SECTION 5 — Cold Start vs Warm State Analysis
    # ─────────────────────────────────────────────────────────────────────────
    print("\n" + "-" * 70)
    print("SECTION 5: Cold Start vs Warm State (Day 4)")
    print("-" * 70)

    for model_name, latencies in [("llama3.2", ll32_latencies), ("llama3.1:8b", ll31_latencies)]:
        cold = latencies[0]
        warm = latencies[1:]
        warm_mean = round(statistics.mean(warm), 3) if len(warm) > 1 else warm[0]
        overhead = round(cold - warm_mean, 3)
        pct = round((overhead / warm_mean) * 100, 1)
        print(f"\n  {model_name}")
        print(f"    Run 1 (cold start):   {cold}s")
        print(f"    Runs 2-3 mean (warm): {warm_mean}s")
        print(f"    Cold start overhead:  +{overhead}s ({pct}% above warm mean)")

    # ─────────────────────────────────────────────────────────────────────────
    # SECTION 6 — What we do NOT know
    # ─────────────────────────────────────────────────────────────────────────
    print("\n" + "-" * 70)
    print("SECTION 6: What the Existing Data Cannot Tell Us")
    print("-" * 70)
    gaps = [
        "Day 1 context-size effect on latency (no JSON saved; not re-run)",
        "Latency under concurrent load (all experiments were sequential)",
        "Latency variance across different log incidents (one log file only)",
        "GPU-accelerated inference times for either model",
        "Tail latency (P95/P99) — all samples are n=3, far below n=20 minimum",
        "Latency distribution shape (normal vs skewed vs bimodal unknown)",
        "Week-to-week or day-to-day system load variability",
    ]
    for i, gap in enumerate(gaps, 1):
        print(f"  {i}. {gap}")

    print("\n" + "=" * 70)
    print("Analysis complete. No new LLM inference was performed.")
    print("=" * 70)


if __name__ == "__main__":
    main()
