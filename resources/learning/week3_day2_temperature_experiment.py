"""Week 3 Day 2 experiment: temperature and sampling in LLM incident analysis.

This is a standalone learning script. It does not change Sage application behavior.
"""

import json
import sys
import time
from pathlib import Path

import httpx
from pydantic import ValidationError

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from analyzer import LLMParseError, LLMValidationError, MAX_ATTEMPTS, _build_prompt
from config import DEFAULT_MODEL, OLLAMA_URL, TIMEOUT
from models import IncidentAnalysis
from parser import parse_file

TEMPERATURES = (0.0, 0.5, 1.0)
RUNS_PER_TEMPERATURE = 3
LOG_PATH = PROJECT_ROOT / "resources" / "application.log"


def _generate_analysis_with_temperature(
    prompt: str,
    temperature: float,
    *,
    model: str = DEFAULT_MODEL,
    ollama_url: str = OLLAMA_URL,
) -> IncidentAnalysis:
    """Send prompt to Ollama with an explicit temperature option, parse, and validate."""
    url = f"{ollama_url}/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": temperature,
        },
    }

    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
    except httpx.ConnectError as exc:
        raise ConnectionError(
            f"Could not connect to Ollama at {ollama_url}. Is it running?"
        ) from exc
    except httpx.TimeoutException as exc:
        raise TimeoutError(
            f"Request to Ollama timed out after {TIMEOUT}s. Is the machine overloaded?"
        ) from exc
    except httpx.HTTPStatusError as exc:
        raise RuntimeError(
            f"Ollama returned status {exc.response.status_code}. Is the model '{model}' pulled?"
        ) from exc

    raw_json_str = data.get("response", "").strip()

    try:
        parsed_dict = json.loads(raw_json_str)
    except json.JSONDecodeError as exc:
        raise LLMParseError(
            f"LLM returned invalid JSON: {exc}\nRaw output:\n{raw_json_str}"
        ) from exc

    try:
        analysis = IncidentAnalysis.model_validate(parsed_dict)
    except ValidationError as exc:
        raise LLMValidationError(
            f"LLM output failed schema validation:\n{exc}"
        ) from exc

    return analysis


def analyze_with_temperature(
    prompt: str,
    temperature: float,
    *,
    model: str = DEFAULT_MODEL,
    ollama_url: str = OLLAMA_URL,
) -> IncidentAnalysis:
    """Analyze using prompt and temperature, retrying on parse/validation failures."""
    last_exc: Exception | None = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return _generate_analysis_with_temperature(
                prompt,
                temperature=temperature,
                model=model,
                ollama_url=ollama_url,
            )
        except (LLMParseError, LLMValidationError) as exc:
            last_exc = exc

    if last_exc is None:
        raise RuntimeError("Retry loop completed without an exception")
    raise last_exc


def main() -> None:
    """Run Sage analysis across varying temperatures with identical prompt/input."""
    entries = parse_file(str(LOG_PATH))
    prompt = _build_prompt(entries)

    print("=" * 70)
    print("Week 3 Day 2: Temperature & Sampling Experiment")
    print(f"Log file:        {LOG_PATH}")
    print(f"Parsed entries:  {len(entries)}")
    print(f"Prompt length:   {len(prompt)} characters")
    print(f"Model:           {DEFAULT_MODEL}")
    print(f"Temperatures:    {TEMPERATURES}")
    print(f"Runs per temp:   {RUNS_PER_TEMPERATURE}")
    print("=" * 70)

    results: list[dict] = []

    for temp in TEMPERATURES:
        for run_idx in range(1, RUNS_PER_TEMPERATURE + 1):
            print(f"\n[Running] Temperature: {temp} | Run: {run_idx}/{RUNS_PER_TEMPERATURE} ...")
            start = time.perf_counter()
            analysis = analyze_with_temperature(prompt, temperature=temp)
            latency = time.perf_counter() - start

            record = {
                "temperature": temp,
                "run": run_idx,
                "severity": analysis.severity,
                "primary_issue": analysis.primary_issue,
                "probable_cause": analysis.probable_cause,
                "confidence": analysis.confidence,
                "latency_seconds": round(latency, 3),
                "full_output": analysis.model_dump(),
            }
            results.append(record)

            print(f"  • Latency:        {record['latency_seconds']}s")
            print(f"  • Severity:       {record['severity']}")
            print(f"  • Primary Issue:  {record['primary_issue']}")
            print(f"  • Probable Cause: {record['probable_cause']}")
            print(f"  • Confidence:     {record['confidence']}")
            print("  • Full IncidentAnalysis output:")
            print(json.dumps(record["full_output"], indent=4))

    print("\n" + "=" * 70)
    print("EXPERIMENT SUMMARY")
    print("=" * 70)
    print(f"{'Temp':<6} {'Run':<5} {'Latency':<9} {'Severity':<10} {'Confidence':<12} {'Primary Issue'}")
    print("-" * 70)
    for r in results:
        print(
            f"{r['temperature']:<6.1f} {r['run']:<5} {r['latency_seconds']:<9.3f} "
            f"{r['severity']:<10} {r['confidence']:<12.2f} {r['primary_issue'][:35]}"
        )


if __name__ == "__main__":
    main()
