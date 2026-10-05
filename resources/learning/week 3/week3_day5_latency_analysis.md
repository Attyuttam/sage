# Week 3 Day 5: Latency, Throughput, and Production Readiness

---

## 1. Latency vs Throughput

**Latency** measures how long a single analysis request takes from submission to validated result.

**Throughput** measures how many analyses a system can process over a time period.

They are inversely related in a sequential (non-concurrent) system:

```
throughput = 1 / latency
throughput_per_hour = 3600 / latency_seconds
```

This relationship is exactly linear in a sequential system — double the latency halves the throughput. In a concurrent system, throughput can be improved by processing multiple requests in parallel, independent of latency per request.

**Why both matter for Sage**:
- A user waiting at a CLI feels *latency* directly.
- An automated pipeline processing many log files per hour experiences *throughput* as its binding constraint.

---

## 2. Average vs Median vs P95/P99

| Statistic | What it Measures | When it Can Mislead |
| :--- | :--- | :--- |
| **Mean (average)** | Total time / number of requests | A single cold-start spike (e.g. 151s) can inflate the mean significantly, making the "typical" experience look worse than it is |
| **Median (P50)** | The middle observation: 50% are faster, 50% are slower | Ignores the tail entirely — a system with a great P50 can still have devastating P99 |
| **P95** | 95% of requests are faster than this | Requires at least ~20 samples to be meaningful; with n=3 it is a fiction |
| **P99** | 99% of requests are faster than this | Requires at least ~100 samples; describes worst-case production behavior |

The gap between median and P95/P99 is called **tail latency**. For user-facing systems, tail latency often matters more than the median because:
- Retries or timeouts hit the tail.
- Users who happen to get the slow request experience the worst outcome.
- The cold-start case described in Section 5 below is a real-world tail latency event.

> **Key insight**: A system that shows `Median = 21s` but `Max = 64s` (as in Variant B's 3 observations) should not be declared "21 second system". The max in 3 observations was 3x the median. In 1000 observations, the tail could be even worse.

---

## 3. What the Existing Experiments Tell Us

### Available data sources

| File | Experiment | Runs | Model | Context |
| :--- | :--- | :---: | :--- | :--- |
| `week3_day4_results.json` | Model comparison | 6 | llama3.2 (3) + llama3.1:8b (3) | 65 entries |
| `week3_day3_results.json` | Prompt strategy | 9 | llama3.2 | 65 entries |

> **Week 3 Day 1 latency data is not available for re-analysis.** That experiment printed results to stdout only and saved no JSON file. Its latency-by-context-size observations cannot be reproduced without running new LLM inference, which was not performed for this Day 5 analysis.

---

### Model Comparison Latency (Day 4 — n=3 per model)

| Statistic | `llama3.2` (3B) | `llama3.1:8b` (8B) |
| :--- | :--- | :--- |
| **Min** | 31.690s | 84.276s |
| **Max** | 50.369s | 151.532s |
| **Mean** | 38.053s | 107.605s |
| **Median (P50)** | 32.100s | 87.007s |
| **P95** | NOT RELIABLE (n=3) | NOT RELIABLE (n=3) |
| **P99** | NOT RELIABLE (n=3) | NOT RELIABLE (n=3) |
| **Sequential Throughput (mean)** | 94.6 analyses/hour | 33.5 analyses/hour |

**Latency ratio**: `llama3.1:8b` is **2.83x slower** than `llama3.2` (mean-based).  
**Throughput ratio**: `llama3.2` processes **2.83x more log batches per hour** under sequential operation.

---

### Prompt Variant Latency (Day 3 — n=3 per variant, all llama3.2)

| Prompt Variant | Min | Max | Mean | Median | Note |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **A — Zero-shot** | 53.29s | 53.92s | 53.61s | 53.62s | Includes 3 retry attempts per run; all failed validation |
| **B — Explicit** | 21.13s | 64.18s | 35.53s | 21.29s | High cold-start run 1 skews mean |
| **C — Few-shot** | 23.68s | 78.35s | 41.91s | 23.69s | Longer prompt adds prefill cost |

**Key observation**: The mean for Variant B (35.5s) is very different from its median (21.3s) because Run 1 was a cold start (64.2s). This is a concrete demonstration of why the mean can mislead when cold starts are present in a small sample.

---

### Cold Start vs Warm State (Day 4)

| Model | Cold Start (Run 1) | Warm Mean (Runs 2-3) | Cold Start Overhead |
| :--- | :--- | :--- | :--- |
| `llama3.2` | 50.369s | 31.895s | +18.5s (+57.9%) |
| `llama3.1:8b` | 151.532s | 85.642s | +65.9s (+76.9%) |

Cold start overhead occurs because Ollama must load the model weights from disk into memory on the first request after the model is not yet loaded. **This is a real tail latency event in production** — after a period of inactivity or a server restart, the first user request to Sage will experience a dramatically longer wait.

---

### Combined llama3.2 View (n=9 validated runs across Day 3 + Day 4)

By pooling all validated `llama3.2` runs from Variant B, Variant C, and Day 4:

| Statistic | Value |
| :--- | :--- |
| n | 9 |
| Min | 21.13s |
| Max | 78.35s |
| Mean | 38.50s |
| Median (P50) | 31.69s |
| P95 | **NOT RELIABLE** — need n ≥ 20 |
| P99 | **NOT RELIABLE** — need n ≥ 100 |
| Sequential Throughput (mean) | 93.5 analyses/hour |

Even at n=9, the spread from 21s to 78s in a small sample should discourage any production SLA claim. This range represents a 3.7x difference between best and worst observed, which is very high variability for a sample of 9.

---

## 4. What the Experiments Do NOT Tell Us

1. **Context-size effect on latency**: Day 1 ran the experiment across 5, 15, 30, and 65 log entries, which would have been the most direct measurement of how prompt token count affects inference time. That data was not saved to a file and is not available for analysis.

2. **Tail latency under realistic production conditions**: With n=3 per group, P95 and P99 are statistically meaningless. A production system would need ≥20 runs to estimate P95 and ≥100 runs to estimate P99 with any confidence.

3. **Concurrent request behavior**: All experiments ran one analysis at a time (sequential). In a system handling multiple simultaneous requests, throughput could be improved (parallelism) or degraded (resource contention), but this experiment says nothing about that.

4. **Latency variance across different incident types**: All 6 Day 4 runs analyzed the same log file with the same incident. A more complex log may produce longer outputs and therefore longer generation time.

5. **GPU-accelerated inference**: All measurements were on CPU. With a GPU, latency for both models would decrease substantially and the ratio between them would likely change.

6. **Long-run stability**: One session of 3 runs each cannot reveal if latency degrades over time due to memory pressure or thermal throttling.

---

## 5. Why a Single Slow Request Matters

In interactive SRE tooling:
- An on-call engineer triggering Sage at 3 AM during an incident cannot afford to wait 151 seconds for a diagnosis.
- If Sage is triggered automatically on log ingestion, a blocked request holds a connection or a queue slot.
- The cold-start case (+65.9s overhead for llama3.1:8b) is likely to occur in exactly the scenario where it matters most: the first Sage invocation after a quiet period.

```
Cold-start llama3.1:8b: 151.5s
vs
Warm llama3.2:          31.9s

That is a 4.75x difference in the worst vs typical case,
comparing the worst model in the worst state to the
best model in its warm state.
```

For a production SRE system, the **P99 tail is what causes SLA breaches**, not the P50. Our experiments are far too small to characterize that tail.

---

## 6. How Model Latency Affects Capacity

At sequential throughput (one analysis at a time):

| Model | Mean Latency | Analyses/Hour | Analyses/Day |
| :--- | :--- | :--- | :--- |
| `llama3.2` | 38.1s | 94.6 | 2,270 |
| `llama3.1:8b` | 107.6s | 33.5 | 804 |

If Sage were deployed to analyze logs from an environment generating 500 log batches per day:
- `llama3.2` would handle this with capacity to spare (2,270/day limit).
- `llama3.1:8b` would also handle it (804/day limit), but with much less headroom.
- At 1,000 log batches/day, `llama3.1:8b` would become the bottleneck and would need parallelism to keep up.

> **Important caveat**: This calculation assumes 24-hour continuous operation at the observed lab latency. Real production systems have burst periods, cold starts, retry overhead, and resource contention that make the actual capacity significantly lower.

---

## 7. How Context Size Affects Latency

The Ollama inference pipeline has two latency components:

1. **Prompt prefill (time-to-first-token)**: Grows with prompt length (number of input tokens). Longer context = more time before any output is generated.
2. **Token generation**: Grows with output length. Longer, more detailed analyses take longer to produce.

**What Day 1 would have shown**: The context experiment varied input from 5 to 65 log entries, which changes the prompt token count significantly. The expected pattern would have been:

```
5 entries   → shortest prompt → fastest prefill → likely fastest overall
15 entries  → medium prompt   → some prefill overhead
30 entries  → longer prompt   → more overhead
65 entries  → longest prompt  → most prefill overhead
```

However, this is a theoretical expectation. The actual data was not saved, and the relationship may not be strictly linear — generation length also varies based on what the model finds in the logs.

**What we can observe from Day 3**: Variant C (few-shot) had a prompt length of 8,624 characters versus Variant B's 7,163 characters. The mean latency of Variant C (41.9s) was higher than Variant B (35.5s), which is consistent with the longer prompt incurring additional prefill cost. But n=3 is too small to treat this as a reliable causal relationship.

---

## 8. What Sage Would Need in Production

For a production SRE incident analysis tool, the following latency requirements would need to be established before deployment:

| Requirement | Target | Current Status |
| :--- | :--- | :--- |
| **P50 latency** | ≤ 30s for interactive use | `llama3.2` warm P50 ≈ 32s (close, but measured n=3) |
| **P95 latency** | ≤ 60s | Unknown — insufficient data |
| **P99 latency** | ≤ 120s | Unknown — insufficient data |
| **Cold start overhead** | Documented and acceptable | 50.4s for `llama3.2`, 151.5s for `llama3.1:8b` |
| **Validation success rate** | ≥ 99% | `llama3.2` = 100% (n=6), insufficient data for production claim |
| **Concurrent request capacity** | Defined | Untested |

---

## 9. Why Our Current Experiments Cannot Establish Production SLAs

A production SLA (Service Level Agreement/Objective) for latency requires:

1. **Large samples**: P95 requires ≥ 20 observations; P99 requires ≥ 100. Our maximum per group is n=9 (combined Day 3+4 validated runs).
2. **Representative conditions**: All experiments ran on a single machine, in a lab setting, with no concurrent load, at a single time of day.
3. **Multiple log scenarios**: All experiments used one 65-line log file with one incident type. Real production logs are more varied.
4. **Warm and cold state characterization**: We have one cold start observation per model — not enough to know the distribution of cold start overhead.
5. **Sustained operation**: A 3-run experiment cannot reveal latency degradation over hours of continuous use.

> **The honest conclusion from this experiment**: We have directional evidence that `llama3.2` warm latency is roughly 30–50 seconds on CPU, and that `llama3.1:8b` is roughly 85–150 seconds. Both exhibit meaningful cold-start penalties. These numbers are useful for planning experiments but cannot be treated as production guarantees.

---

## Data Source Files

| File | Description |
| :--- | :--- |
| [`week3_day4_results.json`](file:///d:/projects/sage/resources/learning/week3_day4_results.json) | 6 model comparison runs |
| [`week3_day3_results.json`](file:///d:/projects/sage/resources/learning/week3_day3_results.json) | 9 prompt strategy runs |
| [`week3_day5_latency_analysis.py`](file:///d:/projects/sage/resources/learning/week3_day5_latency_analysis.py) | Analysis script (no LLM inference) |
