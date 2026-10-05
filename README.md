# Sage

Analyze application logs using a locally running LLM through [Ollama](https://ollama.com).

## Prerequisites

- Python 3.10+
- [Ollama](https://ollama.com) installed and running
- A model pulled (e.g. `ollama pull llama3.2`)

## Install

```bash
pip install -e .
```

## Usage

```bash
# Analyze a log file
sage resources/application.log

# Use a specific model
sage resources/application.log --model mistral

# Only analyze the last 20 entries
sage resources/application.log --last 20

# Override temperature, timeout, or max attempts
sage resources/application.log --temperature 0.0 --timeout 60 --max-attempts 3

# Run directly with Python
python cli.py resources/application.log
```

## Configuration

Sage uses a tiered configuration system:
1. **CLI arguments** have the highest precedence.
2. **Environment variables** (`SAGE_*`) provide system-wide defaults.
3. **Hard-coded defaults** provide safe fallbacks.

| Setting | Environment Variable | CLI Argument | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| **Ollama Server** | `SAGE_OLLAMA_URL` | `--ollama-url` | `http://localhost:11434` | Ollama API server endpoint |
| **Model** | `SAGE_MODEL` | `--model` | `llama3.2` | Model identifier to use |
| **Temperature** | `SAGE_TEMPERATURE` | `--temperature` | `0.0` | Sampling temperature (`0.0` for deterministic extraction) |
| **Timeout** | `SAGE_TIMEOUT` | `--timeout` | `120.0` | HTTP request timeout in seconds |
| **Max Attempts** | `SAGE_MAX_ATTEMPTS` | `--max-attempts` | `3` | Total analysis attempts (initial attempt + retries) |
| **Log Level** | `SAGE_LOG_LEVEL` | `--log-level` | `INFO` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`) |

Invalid numeric or enum values in environment variables produce a clear configuration error on startup.

## Logging

Sage logs diagnostic and operational events to `stderr`, keeping standard output clean for the incident analysis report.

Available logging levels:
* `DEBUG` — Detailed internal execution steps (prompt character lengths, skipped log lines, attempt dispatch).
* `INFO` — Normal operational milestones (log parsing counts, analysis start, successful schema validation).
* `WARNING` — Recoverable issues (malformed LLM output or schema validation failures triggering a retry).
* `ERROR` — Unrecoverable failures (exhausted retries, network connection errors, timeouts, HTTP errors).

Sensitive information such as full prompt bodies, raw untrusted log blocks, full raw responses, and credentials are never emitted into log records.

## How it works

1. **Parse** — Reads the log file and extracts structured entries (timestamp, level, service, message, metadata).
2. **Prompt** — Builds one structured incident-analysis prompt from the parsed entries.
3. **Analyze** — Sends a non-streaming request to Ollama (`stream=False`, `format="json"`, with configured `temperature`) and receives structured JSON output.
4. **Validate** — Parses the model response with `json.loads()` and validates it with Pydantic's `IncidentAnalysis` model.
5. **Retry and report** — Retries malformed or schema-invalid model output up to `max_attempts` total attempts. Connection, timeout, and HTTP failures are reported by the CLI as clear error messages with a non-zero exit code; validated results are printed as an incident report.
