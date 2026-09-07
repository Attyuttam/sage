"""Build prompts from parsed logs and analyze them using Ollama."""

import json
from textwrap import dedent

import httpx
from pydantic import ValidationError

from config import DEFAULT_MODEL, OLLAMA_URL, TIMEOUT
from models import IncidentAnalysis, LogEntry


class LLMParseError(Exception):
    """Raised when the LLM response is not valid JSON."""
    pass


class LLMValidationError(Exception):
    """Raised when the LLM JSON response does not conform to the IncidentAnalysis schema."""
    pass


def analyze(
    entries: list[LogEntry],
    *,
    model: str = DEFAULT_MODEL,
    ollama_url: str = OLLAMA_URL,
) -> IncidentAnalysis:
    """Send log entries to Ollama for analysis, validate against IncidentAnalysis, and return it.

    Raises:
        ConnectionError: If Ollama is not reachable.
        RuntimeError: If Ollama returns an HTTP error.
        LLMParseError: If the LLM response is not valid JSON.
        LLMValidationError: If the LLM response fails schema validation.
    """
    prompt = _build_prompt(entries)
    return _generate_analysis(prompt, model=model, ollama_url=ollama_url)


def _build_prompt(entries: list[LogEntry]) -> str:
    """Construct an analysis prompt asking for structured IncidentAnalysis JSON."""
    log_block = "\n".join(str(e) for e in entries)

    prompt = dedent("""\
        You are a senior Site Reliability Engineer. Analyze the following application logs.

        You must respond ONLY with a single valid JSON object. Do not include markdown backticks or commentary.
        The JSON object must match this exact schema:
        {{
            "severity": "LOW" | "MEDIUM" | "HIGH" | "CRITICAL",
            "affected_services": ["<service_name>", ...],
            "primary_issue": "<concise summary headline>",
            "probable_cause": "<detailed root cause explanation>",
            "evidence": ["<specific log line or timestamp/error details>", ...],
            "confidence": <float between 0.0 and 1.0>
        }}

        --- LOGS ---
        {logs}
        --- END LOGS ---
    """).format(logs=log_block)

    return prompt


def _generate_analysis(
    prompt: str,
    *,
    model: str,
    ollama_url: str,
) -> IncidentAnalysis:
    """POST to Ollama's /api/generate without streaming, parse JSON, and validate with Pydantic."""
    url = f"{ollama_url}/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
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
    except httpx.HTTPStatusError as exc:
        raise RuntimeError(
            f"Ollama returned status {exc.response.status_code}. Is the model '{model}' pulled?"
        ) from exc

    raw_json_str = data.get("response", "").strip()

    # Step 1: JSON Parsing
    try:
        parsed_dict = json.loads(raw_json_str)
    except json.JSONDecodeError as exc:
        raise LLMParseError(
            f"LLM returned invalid JSON: {exc}\nRaw output:\n{raw_json_str}"
        ) from exc

    # Step 2: Pydantic Validation
    try:
        analysis = IncidentAnalysis.model_validate(parsed_dict)
    except ValidationError as exc:
        raise LLMValidationError(
            f"LLM output failed schema validation:\n{exc}"
        ) from exc

    return analysis
