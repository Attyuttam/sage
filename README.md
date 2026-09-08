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

# Run directly with Python
python cli.py resources/application.log
```

## How it works

1. **Parse** — Reads the log file and extracts structured entries (timestamp, level, service, message, metadata).
2. **Prompt** — Builds one structured incident-analysis prompt from the parsed entries.
3. **Analyze** — Sends a non-streaming request to Ollama (`stream=False`, `format="json"`) and receives structured JSON output.
4. **Validate** — Parses the model response with `json.loads()` and validates it with Pydantic's `IncidentAnalysis` model.
5. **Retry and report** — Retries malformed or schema-invalid model output up to three total attempts. Connection, timeout, and HTTP failures are reported by the CLI as clear error messages with a non-zero exit code; validated results are printed as an incident report.
