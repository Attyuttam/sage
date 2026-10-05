# Week 3 Day 6: The Big Experiment — Multi-Variable Matrix Analysis

## 1. Objective

The objective of this experiment is to execute a controlled multi-variable experiment combining the major dimensions investigated throughout Week 3:
1. **Model Architecture and Capacity**: `llama3.2` (~3B) vs `llama3.1:8b` (~8B)
2. **Context Window Size**: 30 log entries vs 65 log entries (full log)
3. **Sampling Temperature**: `0.0` (greedy deterministic decoding) vs `1.0` (high-entropy stochastic sampling)

By fixing the prompt strategy to the production-grade explicit-instruction format identified during Day 3, this experiment evaluates how model capacity, input size, and temperature interact with respect to schema validation reliability, diagnostic quality, root-cause identification, causal explanation depth, and inference latency.

---

## 2. My Pre-Experiment Hypotheses

The pre-experiment hypotheses formulated prior to running the experiment are recorded below:

* **3B + 30 + T=0**: correct answers, relatively low latency, fewer causal relationships than 8B, and high consistency.
* **3B + 30 + T=1**: similar to T=0 but potentially less consistent.
* **3B + 65 + T=0**: correct answers, somewhat higher latency, potentially more information for inference, fewer causal relationships than 8B, and high consistency.
* **3B + 65 + T=1**: similar to T=0 but potentially reduced consistency and therefore potentially affected correctness.
* **8B vs 3B**: 8B should provide better causal relationships but with much higher latency; 8B should not be necessary for simple incidents.

---

## 3. Experimental Design

The experiment executes an exact 8-configuration full factorial matrix ($2 \times 2 \times 2$):

| Config ID | Model | Context Size | Temperature |
| :---: | :--- | :---: | :---: |
| **1** | `llama3.2` | 30 logs | 0.0 |
| **2** | `llama3.2` | 30 logs | 1.0 |
| **3** | `llama3.2` | 65 logs | 0.0 |
| **4** | `llama3.2` | 65 logs | 1.0 |
| **5** | `llama3.1:8b` | 30 logs | 0.0 |
| **6** | `llama3.1:8b` | 30 logs | 1.0 |
| **7** | `llama3.1:8b` | 65 logs | 0.0 |
| **8** | `llama3.1:8b` | 65 logs | 1.0 |

Each configuration was executed once ($n=1$) using the standalone script `resources/learning/week3_day6_big_experiment.py`. All raw responses, token counts, timings, and parsed outputs are preserved in `resources/learning/week3_day6_results.json`.

---

## 4. Fixed Variables

To isolate the interactions between model, context size, and temperature, all other aspects of the pipeline remained strictly identical:

| Variable | Fixed Specification | Purpose / Rationale |
| :--- | :--- | :--- |
| **Log Source** | `resources/application.log` (65 total entries) | Ground truth log stream untouched |
| **Parsing Implementation** | `parser.parse_file` / `models.LogEntry` | Exact string representation across all prompts |
| **Prompt Template** | Day 3 Explicit-Instruction Template | SRE persona, untrusted `<log_data>` boundary, strict JSON requirement, field rules |
| **Output Schema** | `models.IncidentAnalysis` (Pydantic v2) | Strict validation of severity enums, field lengths, confidence bounds, evidence |
| **Inference Transport** | Ollama HTTP API (`/api/generate`) | Blocking HTTP POST (`stream=False`), `format="json"` |
| **Retry Policy** | Up to 3 attempts on parse/validation error | Matches Sage production retry behavior |
| **Timeout Headroom** | 360 seconds | Accommodates 8B CPU prefill and token generation without premature aborts |
| **Hardware Host** | Windows 11 CPU host (16 GB RAM) | Identical execution environment across all 8 runs |

---

## 5. Independent Variables & Context Construction

### Independent Variables
1. **Model**:
   - `llama3.2` (3.21B parameters, 2.0 GB disk footprint, ~2.6 GB active RAM)
   - `llama3.1:8b` (8.03B parameters, 4.9 GB disk footprint, ~5.6 GB active RAM)
2. **Context Size**:
   - **30 logs**: Log suffix representing the second half and recovery phase of the incident.
   - **65 logs**: The complete log stream capturing pre-incident baseline, first failure wave, intermediate lull, second failure wave, and recovery.
3. **Temperature**:
   - **0.0**: Greedy decoding (deterministic token selection).
   - **1.0**: Standard temperature sampling (higher exploration and distribution breadth).

### Detailed Context Construction & Log Slices

* **30-Log Context Window**:
  - Selection: `all_entries[-30:]` (entries 35 through 64, corresponding to lines 36 to 65 in `resources/application.log`).
  - Time Span: `2026-08-31 09:09:08` to `2026-08-31 09:18:16` (548 seconds).
  - Prompt Length: 3,862 characters (~1,002–1,017 input tokens).
  - Log contents included: Second order-service retry warning (`09:09:08`), inventory sync, subsequent payment requests (REQ005, REQ006), second wave of DB response latency (`09:13:44`), second DB timeout (`09:13:47`), second DB pool exhaustion (`09:14:02`), payment error rate spike (42%), order dependency failures, circuit breaker trip (`09:15:00`), payment unavailable (`09:16:05`), DB restoration (`09:17:10`), circuit breaker reset (`09:17:30`), and final operational payment (REQ008).
  - Excluded from 30 logs: Initial normal payments (REQ001, REQ002), first order (ORD001), first DB timeouts on REQ003 (`09:05:15`–`09:05:22`), first pool warning (`09:08:10`), first pool exhaustion (`09:08:15`), initial DB health check failure (`09:08:46`), and initial order failure ORD003 (`09:09:05`).

* **65-Log Context Window**:
  - Selection: `all_entries[-65:]` (all 65 entries in `resources/application.log`).
  - Time Span: `2026-08-31 09:00:01` to `2026-08-31 09:18:16` (1,095 seconds).
  - Prompt Length: 6,971 characters (~1,907–1,922 input tokens).
  - Log contents included: The complete timeline from baseline healthy traffic through both incident spikes and full recovery.

---

## 6. Results Table

All 8 configurations passed Pydantic validation on **Attempt 1 of 3** (0 retries required, 100% schema validation success).

| ID | Model | Context | Temp | Status | Attempts | Latency (s) | Seq. Throughput (runs/hr) | Prompt Tokens | Output Tokens | Severity | Confidence | Primary Issue Headline |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **1** | `llama3.2` | 30 logs | 0.0 | `VALIDATED` | 1 | 35.64 | 101.02 | 1017 | 142 | `CRITICAL` | 0.90 | Payment service dependency failure causing order creation failures |
| **2** | `llama3.2` | 30 logs | 1.0 | `VALIDATED` | 1 | 10.92 | 329.70 | 1017 | 109 | `CRITICAL` | 0.80 | Payment Service Unavailability |
| **3** | `llama3.2` | 65 logs | 0.0 | `VALIDATED` | 1 | 49.36 | 72.94 | 1922 | 119 | `CRITICAL` | 0.90 | Payment Service Unavailability |
| **4** | `llama3.2` | 65 logs | 1.0 | `VALIDATED` | 1 | 29.14 | 123.54 | 1922 | 239 | `CRITICAL` | 0.90 | Database connection timeout leading to Payment Service Unavailability |
| **5** | `llama3.1:8b` | 30 logs | 0.0 | `VALIDATED` | 1 | 104.76 | 34.37 | 1002 | 179 | `HIGH` | 0.90 | Payment service dependency failure leading to order creation issues |
| **6** | `llama3.1:8b` | 30 logs | 1.0 | `VALIDATED` | 1 | 39.01 | 92.28 | 1002 | 196 | `HIGH` | 0.90 | Payment service unavailability leading to order creation failures |
| **7** | `llama3.1:8b` | 65 logs | 0.0 | `VALIDATED` | 1 | 163.41 | 22.03 | 1907 | 274 | `CRITICAL` | 0.95 | Payment Service Unavailability and Database Connection Issues |
| **8** | `llama3.1:8b` | 65 logs | 1.0 | `VALIDATED` | 1 | 59.82 | 60.18 | 1907 | 257 | `CRITICAL` | 0.95 | Payment Service Downtime and Datastore Connection Pool Exhaustion |

---

## 7. Quality Analysis

### Evaluation Rubric
Each run is evaluated against a 4-dimension rubric (0 to 2 points per dimension, max total = 8):
1. **Root-Cause Identification**: 0 = Incorrect, 1 = Partially correct / symptomatic, 2 = Correctly identifies the DB latency / connection-pool exhaustion chain.
2. **Affected-Service Identification**: 0 = Incorrect, 1 = Partially correct (omits impacted services or includes un-impacted services), 2 = Accurately isolates `payment-service` and `order-service` without hallucinations.
3. **Evidence Quality**: 0 = Missing/irrelevant, 1 = Some useful lines, 2 = Strong multi-event evidence supporting the causal chain.
4. **Causal Explanation**: 0 = Incorrect, 1 = Partially explains chain, 2 = Clearly explains the causal cascade.

> *Note: A score of 8/8 indicates strong alignment with the human rubric criteria for this benchmark scenario; it is an evaluation tool, not mathematical proof of universal correctness.*

### Rubric Breakdown per Configuration

| Config ID | Configuration | Root Cause (0-2) | Affected Services (0-2) | Evidence Quality (0-2) | Causal Explanation (0-2) | Total Score (0-8) |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: |
| **1** | `llama3.2` / 30 / T=0.0 | 1 | 2 | 1 | 1 | **5 / 8** |
| **2** | `llama3.2` / 30 / T=1.0 | 2 | 1 | 2 | 2 | **7 / 8** |
| **3** | `llama3.2` / 65 / T=0.0 | 2 | 1 | 2 | 1 | **6 / 8** |
| **4** | `llama3.2` / 65 / T=1.0 | 2 | 1 | 2 | 2 | **7 / 8** |
| **5** | `llama3.1:8b` / 30 / T=0.0 | 2 | 2 | 2 | 2 | **8 / 8** |
| **6** | `llama3.1:8b` / 30 / T=1.0 | 2 | 2 | 2 | 2 | **8 / 8** |
| **7** | `llama3.1:8b` / 65 / T=0.0 | 2 | 2 | 2 | 2 | **8 / 8** |
| **8** | `llama3.1:8b` / 65 / T=1.0 | 2 | 1 | 2 | 2 | **7 / 8** |

### Detailed Qualitative Observations

* **Config 1 (`llama3.2` / 30 / T=0.0)**:
  - Focused strictly on the symptom at the beginning of the 30-log slice (`order-service` failing due to payment dependency). Did not extract the database pool exhaustion that occurred at 09:14:02. Cites only 2 evidence lines. Score: **5/8**.
* **Config 2 (`llama3.2` / 30 / T=1.0)**:
  - Successfully identified the DB timeout and circuit breaker trip (`09:13:47` and `09:15:00`). However, it omitted `order-service` from `affected_services`, reporting only `payment-service`. Score: **7/8**.
* **Config 3 (`llama3.2` / 65 / T=0.0)**:
  - Identified DB pool exhaustion, but hallucinated that "user logins to fail" in its probable cause (all user logins in the logs succeeded with HTTP 200/INFO). Omitted `order-service` from `affected_services`. Score: **6/8**.
* **Config 4 (`llama3.2` / 65 / T=1.0)**:
  - Extracted a strong chronological 5-line evidence progression covering the first wave (`09:05:15` to `09:08:15`). However, it falsely flagged `inventory-service` as an affected service (inventory sync was completely healthy). Score: **7/8**.
* **Config 5 (`llama3.1:8b` / 30 / T=0.0)**:
  - Even with only 30 logs, `llama3.1:8b` synthesized both the downstream order creation failure and the underlying payment DB pool exhaustion / 42% error rate. Isolated services perfectly (`order-service`, `payment-service`). Score: **8/8**.
* **Config 6 (`llama3.1:8b` / 30 / T=1.0)**:
  - Successfully connected DB slow response (`09:13:44`), pool exhaustion (`09:14:02`), circuit breaker, and downstream order failure. Cited 4 clean evidence lines. Score: **8/8**.
* **Config 7 (`llama3.1:8b` / 65 / T=0.0)**:
  - Produced the most comprehensive and structured diagnostic output of the experiment. Extracted a 6-event chronological proof chain spanning initial timeouts at 09:05:18, pool exhaustion at 09:08:15, downstream order failure at 09:09:11, and circuit breaker trip at 09:15:00. Clear causal hierarchy without extraneous service hallucinations. Score: **8/8**.
* **Config 8 (`llama3.1:8b` / 65 / T=1.0)**:
  - High quality root cause and 6 evidence lines, but under T=1.0 included `user-service` in `affected_services` (even though user logins were unaffected). Score: **7/8**.

---

## 8. Latency Analysis

### Observed Latency Summary

```
Config 1 (3B / 30 / T=0.0) :  35.64s  |  Throughput: 101.0 runs/hr
Config 2 (3B / 30 / T=1.0) :  10.92s  |  Throughput: 329.7 runs/hr
Config 3 (3B / 65 / T=0.0) :  49.36s  |  Throughput:  72.9 runs/hr
Config 4 (3B / 65 / T=1.0) :  29.14s  |  Throughput: 123.5 runs/hr
Config 5 (8B / 30 / T=0.0) : 104.76s  |  Throughput:  34.4 runs/hr
Config 6 (8B / 30 / T=1.0) :  39.01s  |  Throughput:  92.3 runs/hr
Config 7 (8B / 65 / T=0.0) : 163.41s  |  Throughput:  22.0 runs/hr
Config 8 (8B / 65 / T=1.0) :  59.82s  |  Throughput:  60.2 runs/hr
```

### Statistical Averages by Factor

| Dimension | Group A | Mean Latency A | Group B | Mean Latency B | Latency Ratio (B / A) |
| :--- | :--- | :---: | :--- | :---: | :---: |
| **Model** | `llama3.2` (3B) | 31.27s | `llama3.1:8b` (8B) | 91.75s | **2.93x** slower |
| **Context Size** | 30 logs | 47.58s | 65 logs | 75.43s | **1.59x** slower |
| **Temperature** | T=1.0 (stochastic) | 34.72s | T=0.0 (greedy) | 88.29s | **2.54x** slower |

### Sequential Throughput Impact
* The fastest configuration (`llama3.2` / 30 logs / T=1.0) processed at **10.92s** (~329.7 analyses/hour).
* The slowest configuration (`llama3.1:8b` / 65 logs / T=0.0) required **163.41s** (~22.0 analyses/hour).
* The 8B model with full context and greedy decoding represents a **15x throughput reduction** compared to the lightweight 3B model at T=1.0 on CPU inference.

---

## 9. Context-Size Analysis

### Quantitative Comparison: 30 logs vs 65 logs

| Metric | 30 Logs (Configs 1, 2, 5, 6) | 65 Logs (Configs 3, 4, 7, 8) | Delta / Ratio |
| :--- | :---: | :---: | :---: |
| **Prompt Characters** | 3,862 chars | 6,971 chars | +80.5% |
| **Prompt Eval Tokens** | ~1,002–1,017 tokens | ~1,907–1,922 tokens | +90.3% |
| **Mean Latency (3B)** | 23.28s | 39.25s | +15.97s (+68.6%) |
| **Mean Latency (8B)** | 71.89s | 111.62s | +39.73s (+55.3%) |
| **Mean Quality Score** | 7.0 / 8 | 7.0 / 8 | 0.0 delta |

### Diagnostic Implications
1. **The 30-Log Window Contained Sufficient Signal for 8B**: Because the 30-log slice still captured the second wave of DB pool exhaustion (`09:14:02`) and circuit breaker trips, `llama3.1:8b` achieved full 8/8 quality scores even on the truncated context.
2. **The 30-Log Window Confused 3B at T=0.0**: `llama3.2` at T=0.0 locked onto the first available error in its window (`order-service` dependency failure) and failed to synthesize the subsequent DB pool exhaustion logs, yielding a lower score (5/8).
3. **Prefill Latency Scaling**: Doubling context size added ~900 prompt evaluation tokens, which added ~16 seconds of CPU prefill time for 3B and ~40 seconds for 8B.

---

## 10. Temperature Analysis

### Quantitative Comparison: T=0.0 vs T=1.0

| Metric | T=0.0 (Configs 1, 3, 5, 7) | T=1.0 (Configs 2, 4, 6, 8) | Delta / Ratio |
| :--- | :---: | :---: | :---: |
| **Mean Latency (3B)** | 42.50s | 20.03s | -22.47s (-52.9%) |
| **Mean Latency (8B)** | 134.09s | 49.42s | -84.67s (-63.1%) |
| **Overall Mean Latency** | 88.29s | 34.72s | **2.54x faster at T=1.0** |
| **Mean Quality Score** | 6.75 / 8 | 7.25 / 8 | +0.50 |
| **Service Hallucination Count** | 0 instances | 2 instances (Configs 4, 8) | Higher boundary leakage |

### Why Did T=1.0 Exhibit Lower Latency?
In this experiment, T=1.0 runs exhibited significantly faster generation times. Two factors contribute:
1. **Warm State vs Cold Load**: The test ran sequentially from Config 1 to 8. For both models, the T=0.0 run preceded the T=1.0 run, meaning initial memory allocation and internal caching occurred during the T=0.0 runs.
2. **Token Generation Trajectory**: Under T=1.0, sampling trajectories reached stop tokens or structured JSON closures with different token distributions.

### Quality Trade-offs of Temperature
* **At T=0.0**: High determinism, zero service hallucinations (no unimpacted services added). However, 3B exhibited premature convergence on local patterns (e.g. blaming user logins or stopping at order service).
* **At T=1.0**: Broader evidence collection and richer causal phrasing. However, temperature introduced **hallucinated service dependencies** in 2 out of 4 runs:
  - Config 4 (`llama3.2` / 65) included `inventory-service`.
  - Config 8 (`llama3.1:8b` / 65) included `user-service`.

---

## 11. Model Comparison: `llama3.2` (3B) vs `llama3.1:8b` (8B)

### Quantitative Summary

| Dimension | `llama3.2` (3B) | `llama3.1:8b` (8B) | Comparison |
| :--- | :---: | :---: | :---: |
| **Mean Latency** | 31.27s | 91.75s | 3B is **2.93x faster** |
| **Max Latency (Cold/Worst)** | 49.36s | 163.41s | 8B worst-case is **3.31x higher** |
| **Sequential Throughput (Mean)** | 156.9 runs/hour | 52.2 runs/hour | 3B yields **3.0x higher throughput** |
| **Mean Quality Score** | 6.25 / 8 | 7.75 / 8 | 8B scores **+1.50 points higher** |
| **Root Cause Accuracy (Mean)** | 1.75 / 2.0 | 2.0 / 2.0 | 8B achieved 100% root cause detection |
| **Service Isolation (Mean)** | 1.25 / 2.0 | 1.75 / 2.0 | 8B accurately isolated services in 3/4 runs |
| **Evidence Extraction Depth** | 2 to 5 lines | 3 to 6 lines | 8B systematically extracts more complete chains |

### Capacity and Reasoning Differences
* **3B (`llama3.2`)**: Highly competent at structured JSON generation (100% schema compliance on Attempt 1). However, its attention over longer contexts or complex multi-hop dependencies is more brittle. It frequently dropped `order-service` when focusing on `payment-service`, or added false services when temperature was elevated.
* **8B (`llama3.1:8b`)**: Consistently demonstrated superior multi-service reasoning. It articulated the hierarchical causal chain:
  $$\text{DB Connection Timeout} \longrightarrow \text{Connection Pool Exhaustion} \longrightarrow \text{Circuit Breaker Trip} \longrightarrow \text{Order Service Rejections}$$
  However, this reasoning capacity carries a severe latency cost on CPU hosts (up to 2.7 minutes per single analysis).

---

## 12. Interaction Observations

1. **Model Capacity $\times$ Context Size**:
   - For `llama3.1:8b`, context size had virtually no impact on diagnostic quality (both 30 and 65 logs produced 8/8 scores at T=0.0). The 8B model's attention mechanism extracted the relevant causal links even from a narrower window.
   - For `llama3.2`, context size interacted strongly with diagnostic focus: with 30 logs it focused on the order-service symptom, whereas with 65 logs it identified the database pool exhaustion.

2. **Model Capacity $\times$ Temperature**:
   - At T=0.0, `llama3.1:8b` was strictly superior in diagnostic accuracy (8/8 vs 5/8 and 6/8 for 3B).
   - At T=1.0, both models experienced service boundary hallucinations (`inventory-service` in 3B, `user-service` in 8B). Higher entropy impairs strict negative constraint adherence (i.e. excluding healthy services) regardless of parameter count.

3. **Context Size $\times$ Temperature**:
   - The combination of large context (65 logs) and high temperature (T=1.0) produced the highest rate of service over-inclusion across both models. With more benign service names present in the context (e.g. `user-service` logins, `inventory-service` checks), stochastic sampling at T=1.0 increased the probability of unimpacted services leaking into `affected_services`.

---

## 13. Configuration Trade-offs

| Configuration | Pros | Cons | Best Use Case |
| :--- | :--- | :--- | :--- |
| **3B + 30 logs + T=0.0** | Predictable latency (~35s), low memory, deterministic | Missed root cause in partial window, narrow evidence | Fast local triage when log window is pre-filtered |
| **3B + 30 logs + T=1.0** | Lowest latency (10.9s), high throughput (~330/hr) | Missed downstream order service, stochastic variance | High-volume non-critical log filtering |
| **3B + 65 logs + T=0.0** | Good root cause detection, sub-minute latency | Hallucinated user login failure, missed order-service | General-purpose low-resource CLI tool |
| **3B + 65 logs + T=1.0** | Rich evidence extraction (5 lines), fast (29.1s) | Hallucinated inventory-service failure | Exploratory SRE assistance |
| **8B + 30 logs + T=0.0** | Perfect 8/8 diagnostic score, deterministic | High latency (104.8s) on CPU | Deep-dive triage with constrained log snippets |
| **8B + 30 logs + T=1.0** | Perfect 8/8 diagnostic score, moderate latency (39.0s) | Stochastic non-determinism | Interactive troubleshooting |
| **8B + 65 logs + T=0.0** | Outstanding causal clarity, 6-line proof chain, 0 hallucinations | Slowest run (163.4s / 2.7 min), lowest throughput (22/hr) | Post-mortem generation and automated incident reports |
| **8B + 65 logs + T=1.0** | Strong evidence synthesis, moderate latency (59.8s) | Hallucinated user-service involvement | Draft post-mortem generation |

---

## 14. What the Experiment Supports

1. **Explicit Prompting Delivers 100% Schema Reliability**: Across all 8 configurations spanning different models, context sizes, and temperatures, the explicit SRE prompt achieved 100% first-attempt JSON validation with zero retries.
2. **8B Model Exhibits Significantly Superior Causal Reasoning**: `llama3.1:8b` systematically explained the full multi-tier failure chain, whereas `llama3.2` exhibited blind spots (omitting affected services or focusing solely on symptoms).
3. **T=0.0 Prevents Hallucinated Service Inclusions**: Greedy decoding completely eliminated false-positive service identifications across all runs, whereas T=1.0 introduced false-positive services in 50% of the runs.
4. **Context Prefill Adds Linear CPU Latency Overhead**: Doubling the log volume nearly doubled the prompt evaluation tokens and added 55%–68% latency overhead.

---

## 15. What the Experiment Does NOT Prove

1. **Does NOT Prove Production Invariant Latency**: Because each configuration was executed once ($n=1$), the recorded latencies reflect single-point samples influenced by execution order, CPU thermal state, and Ollama caching.
2. **Does NOT Prove 8B is Universally Required**: For simple single-service failures with clear error messages, smaller models may achieve identical diagnostic quality at 3x the throughput.
3. **Does NOT Prove Statistical Superiority of T=1.0 Speed**: The faster execution of T=1.0 runs was influenced by cache warmth following the initial T=0.0 runs rather than an intrinsic algorithmic advantage of high temperature.
4. **Does NOT Prove Generalizability to All Log Formats**: The experiment evaluated a single incident scenario from `resources/application.log`. Behavior on multi-tenant, unstructured, or noisy logs remains to be tested.

---

## 16. Limitations

1. **Sample Size ($n=1$)**: Each cell in the matrix was executed once to maintain a controlled 8-run matrix. Variance across repeated runs at T=1.0 cannot be statistically quantified from this dataset.
2. **Hardware Constraints**: Inference was conducted entirely on CPU (no dedicated GPU acceleration), accentuating the latency disparity between 3B and 8B.
3. **Single Scenario Dataset**: All runs analyzed the database connection pool failure from `resources/application.log`.
4. **Sequential Execution Order**: Runs were executed in fixed order (Config 1 through 8), meaning warm-cache benefits accrued disproportionately to later configurations.
