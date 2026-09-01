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

1. **Parse** — Reads the log file and extracts structured entries (timestamp, level, service, message, metadata)
2. **Prompt** — Builds an analysis prompt from the parsed entries
3. **Analyze** — Streams the prompt to Ollama and prints the LLM's response in real time
