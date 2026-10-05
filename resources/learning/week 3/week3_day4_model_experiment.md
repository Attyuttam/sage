# Week 3 Day 4: Model Comparison Experiment (llama3.2 vs llama3.1:8b)

## 1. Hypothesis

Prior to running the experiment, the following three-part hypothesis was formulated:
1. **Diagnostic Quality**: `llama3.2` (~3B) and `llama3.1:8b` (~8B) will produce similar-quality answers because the Sage logs are relatively simple and explicit.
2. **Execution Latency**: `llama3.2` will be faster because it has fewer parameters to compute during prompt prefill and token generation.
3. **Engineering Trade-off**: For the current Sage workload, the smaller model (`llama3.2`) is likely the superior engineering choice to avoid unnecessary resource consumption and latency overhead.

---

## 2. Experimental Setup

The experiment was conducted locally using Ollama under controlled conditions where the model was the sole independent variable.

* **Execution Script**: `resources/learning/week3_day4_model_experiment.py`
* **Log Input**: `resources/application.log` (all 65 parsed log entries)
* **Prompt Strategy**: Production-style explicit instructions (SRE persona, strict JSON requirement, `<log_data>` boundaries, explicit enum literals and semantic definitions, no few-shot examples).
* **Repetition**: 3 runs per model (6 runs total).
* **Environment**: Local Windows CPU host, 16 GB RAM, no dedicated GPU acceleration.

---

## 3. Fixed Variables

To isolate model capacity and parameter scale, all other runtime parameters were held constant:

| Variable | Fixed Value | Rationale |
| :--- | :--- | :--- |
| **Input Logs** | `resources/application.log` | Identical 65 log lines across all 6 runs |
| **Prompt Text** | Explicit SRE instructions (7,163 chars) | Identical prompt string across all runs |
| **Temperature** | `0.0` | Eliminates random sampling variance |
| **Streaming** | `stream = False` | Standard blocking HTTP POST |
| **Response Format** | `format = "json"` | Ollama JSON grammar constraint mode |
| **Schema Validation** | `models.IncidentAnalysis` | Strict Pydantic model validation |
| **Retry Limit** | Up to 3 attempts | Matches Sage's production retry behavior |
| **Timeout Headroom** | 360 seconds | Accommodates 8B parameter CPU prefill |

---

## 4. Model Characteristics

### Model A: `llama3.2:latest`
* **Architecture**: Meta Llama 3.2
* **Parameter Scale**: ~3 Billion parameters
* **On-Disk Size**: 2.0 GB
* **Active RAM Footprint**: ~2.6 GB
* **Target Environment**: Edge, mobile, and lightweight CPU inference

### Model B: `llama3.1:8b`
* **Architecture**: Meta Llama 3.1
* **Parameter Scale**: ~8 Billion parameters
* **On-Disk Size**: 4.9 GB
* **Active RAM Footprint**: ~5.6 GB
* **Target Environment**: General enterprise / workstation LLM workloads

---

## 5. Results from All 6 Runs

Both models achieved a **100% validation success rate** on Attempt 1 across all runs.

### Summary Table

| Model | Run | Status | Attempts | Latency (s) | Severity | Affected Services | Confidence | Primary Issue |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- | :---: | :--- |
| **llama3.2** | 1 | `VALIDATED` | 1 | 50.369 | `CRITICAL` | payment-service | 0.90 | Payment Service Unavailability |
| **llama3.2** | 2 | `VALIDATED` | 1 | 32.100 | `CRITICAL` | payment-service | 0.90 | Payment Service Unavailability |
| **llama3.2** | 3 | `VALIDATED` | 1 | 31.690 | `CRITICAL` | payment-service | 0.90 | Payment Service Unavailability |
| **llama3.1:8b** | 1 | `VALIDATED` | 1 | 151.532 | `CRITICAL` | payment-service, order-service | 0.90 | Payment Service Unavailability and Database Connection Issues |
| **llama3.1:8b** | 2 | `VALIDATED` | 1 | 84.276 | `CRITICAL` | payment-service, order-service | 0.90 | Payment Service Unavailability and Database Connection Issues |
| **llama3.1:8b** | 3 | `VALIDATED` | 1 | 87.007 | `CRITICAL` | payment-service, order-service | 0.90 | Payment Service Unavailability and Database Connection Issues |

---

## 6. Detailed Outputs

### `llama3.2` Output (Representative Warm Run — Runs 2 & 3 Identical)

```json
{
  "severity": "CRITICAL",
  "affected_services": [
    "payment-service"
  ],
  "primary_issue": "Payment Service Unavailability",
  "probable_cause": "Repeated database connection timeouts and failures due to high database connection pool usage and slow database responses, leading to a circuit breaker opening and payment service degradation.",
  "evidence": [
    "2026-08-31 09:08:15 ERROR payment-service Database connection pool exhausted active=100 max=100",
    "2026-08-31 09:13:44 WARN payment-service Database response slow request_id=REQ007 latency_ms=2900",
    "2026-08-31 09:14:02 ERROR payment-service Database connection pool exhausted active=100 max=100"
  ],
  "confidence": 0.9
}
```

---

### `llama3.1:8b` Output (Representative Warm Run — Runs 2 & 3 Identical)

```json
{
  "severity": "CRITICAL",
  "affected_services": [
    "payment-service",
    "order-service"
  ],
  "primary_issue": "Payment Service Unavailability and Database Connection Issues",
  "probable_cause": "The payment service experienced a series of database connection timeouts, leading to payment failures and subsequent order creation failures. The issue was exacerbated by a high database connection pool usage and eventual exhaustion, triggering a circuit breaker and degrading the payment service.",
  "evidence": [
    "2026-08-31 09:05:18 ERROR payment-service Database connection timeout request_id=REQ003",
    "2026-08-31 09:05:22 ERROR payment-service Database connection timeout request_id=REQ003",
    "2026-08-31 09:08:15 ERROR payment-service Database connection pool exhausted active=100 max=100",
    "2026-08-31 09:09:05 ERROR order-service Failed to create order order_id=ORD003 error_code=PAYMENT_SERVICE_UNAVAILABLE",
    "2026-08-31 09:15:00 WARN payment-service Circuit breaker opened failure_count=15 threshold=10"
  ],
  "confidence": 0.9
}
```

---

## 7. Comparative Analysis Across Dimensions

### 1. Structured-Output Reliability
* **Both models achieved 100% reliability (3/3 on Attempt 1)**.
* Neither model required a retry. Both adhered strictly to valid JSON, the Pydantic schema, enum bounds (`CRITICAL`), and required non-empty evidence arrays.

### 2. Diagnosis Correctness
* Both correctly diagnosed the incident severity as **`CRITICAL`**.
* Both identified the fundamental root cause: payment service database connection timeouts leading to connection pool exhaustion and circuit breaker trip.

### 3. Primary Issue Formulation
* `llama3.2`: Focused cleanly on the high-level symptom (`"Payment Service Unavailability"`).
* `llama3.1:8b`: Combined both the symptom and root cause into the headline (`"Payment Service Unavailability and Database Connection Issues"`).

### 4. Probable Cause & Cascading Impact
* `llama3.2`: Accurately identified the failure progression within `payment-service`. However, it did not explicitly mention how downstream callers were impacted.
* `llama3.1:8b`: Tracked the **cascading blast radius**. It recognized that the payment failures propagated to `order-service`, causing order creation failures. Consequently, it listed both `["payment-service", "order-service"]` under `affected_services`.

### 5. Evidence Quality
* `llama3.2`: Extracted 3 log lines concentrated around the pool exhaustion events (09:08:15, 09:13:44, 09:14:02).
* `llama3.1:8b`: Extracted a superior **5-line chronological narrative arc**:
  1. *09:05:18*: Initial root cause database connection timeout.
  2. *09:05:22*: Repeated database timeout retry.
  3. *09:08:15*: Pool exhaustion.
  4. *09:09:05*: Downstream cascading order creation failure.
  5. *09:15:00*: Circuit breaker trip (`failure_count=15 threshold=10`).

### 6. Confidence
* Both models scored **`0.90`** certainty.

### 7. Consistency Across Runs
* Both models were deterministic at `temperature = 0.0`:
  * `llama3.2`: 100% identical outputs across Runs 1, 2, and 3.
  * `llama3.1:8b`: Slight phrasing variation on Run 1, with Runs 2 and 3 settling into 100% identical outputs.

### 8. Latency Comparison
* **Cold Start**:
  * `llama3.2`: 50.4s
  * `llama3.1:8b`: 151.5s (**3.0x slower**)
* **Warm State Average**:
  * `llama3.2`: **31.9s**
  * `llama3.1:8b`: **85.6s** (**2.7x slower**)

---

## 8. Resource and Model-Size Considerations

| Dimension | `llama3.2` (3B) | `llama3.1:8b` (8B) | Delta / Impact |
| :--- | :---: | :---: | :---: |
| **Disk Storage** | 2.0 GB | 4.9 GB | 2.45x larger |
| **RAM Footprint** | ~2.6 GB | ~5.6 GB | 2.15x larger |
| **Execution Latency (Warm)** | ~32s | ~86s | +54s per run (+169%) |
| **Installation Friction** | Low | High | 8B nearly triggered host disk exhaustion |

On consumer CPU architectures without dedicated VRAM, running `llama3.1:8b` consumes over a third of available system RAM (5.6 GB out of 16 GB), creating noticeable memory pressure and requiring substantial wait times (~1.5 minutes per log analysis).

---

## 9. Evaluation of Hypothesis

1. **Hypothesis 1: Similar diagnostic quality because logs are explicit**
   * **Verdict: Partially Supported (Nuanced)**.
   * Both models correctly identified the primary incident and root cause. However, `llama3.1:8b` demonstrated superior causal reasoning by tracing downstream service impacts (`order-service`) and assembling a chronological 5-stage evidence chain.
2. **Hypothesis 2: `llama3.2` will be faster due to fewer parameters**
   * **Verdict: Strongly Supported**.
   * `llama3.2` was 2.7x faster in warm inference (31.9s vs 85.6s) and 3.0x faster on cold start (50.4s vs 151.5s).
3. **Hypothesis 3: `llama3.2` is the better engineering choice for Sage**
   * **Verdict: Strongly Supported**.
   * For Sage’s workload, the 3B model achieves 100% schema adherence and accurate incident diagnosis while saving 54 seconds per call, 3 GB of disk space, and 3 GB of working memory. The marginal depth gained by the 8B model does not justify the 2.7x latency penalty and host resource overhead on CPU.

---

## 10. Limitations of the Experiment

* **CPU-Bound Inference**: The benchmark was conducted entirely on CPU. On dedicated GPU hardware with high memory bandwidth (e.g. NVIDIA RTX or Apple Silicon), 8B latency would decrease substantially, potentially altering the trade-off calculus.
* **Single Log Incident**: The experiment evaluated a single 65-line database pool exhaustion scenario. More complex, ambiguous multi-service incidents might exhibit wider quality gaps between 3B and 8B models.
