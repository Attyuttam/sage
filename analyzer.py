"""Build prompts from parsed logs and stream analysis from Ollama."""

import json
import sys
from textwrap import dedent

import httpx

from config import DEFAULT_MODEL, OLLAMA_URL, TIMEOUT
from models import LogEntry


def analyze(
    entries: list[LogEntry],
    *,
    model: str = DEFAULT_MODEL,
    ollama_url: str = OLLAMA_URL,
) -> None:
    """Send log entries to Ollama for analysis and stream the response to stdout.

    Raises:
        ConnectionError: If Ollama is not reachable.
    """
    prompt = _build_prompt(entries)
    _stream_response(prompt, model=model, ollama_url=ollama_url)


def _build_prompt(entries: list[LogEntry]) -> str:
    """Construct an analysis prompt from structured log entries."""
    log_block = "\n".join(str(e) for e in entries)

    prompt = dedent("""\
        You are a senior Site Reliability Engineer. Analyze the following application logs.

        Provide:
        1. A brief summary of what happened
        2. Root cause analysis of any errors or warnings
        3. The timeline of the incident (if any)
        4. Recommended actions

        Be concise and specific. Reference timestamps and request IDs where relevant.

        --- LOGS ---
        {logs}
        --- END LOGS ---
    """).format(logs=log_block)

    return prompt


def _stream_response(
    prompt: str,
    *,
    model: str,
    ollama_url: str,
) -> None:
    """POST to Ollama's /api/generate and stream tokens to stdout."""
    url = f"{ollama_url}/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": True,
    }

    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            with client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                for raw_line in response.iter_lines():
                    if not raw_line:
                        continue
                    chunk = json.loads(raw_line)
                    token = chunk.get("response", "")
                    sys.stdout.write(token)
                    sys.stdout.flush()

                    if chunk.get("done", False):
                        break

    except httpx.ConnectError:
        print(
            "\nError: Could not connect to Ollama. "
            f"Is it running at {ollama_url}?",
            file=sys.stderr,
        )
        sys.exit(1)
    except httpx.HTTPStatusError as exc:
        print(
            f"\nError: Ollama returned status {exc.response.status_code}. "
            f"Is the model '{model}' pulled?",
            file=sys.stderr,
        )
        sys.exit(1)

    # Ensure a newline after streamed output
    print()
