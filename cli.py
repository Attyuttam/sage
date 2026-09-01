"""Command-line interface for Sage."""

import argparse
import sys

from analyzer import analyze
from config import DEFAULT_MODEL, OLLAMA_URL
from parser import parse_file

__version__ = "0.1.0"


def main() -> None:
    """Entry point for the sage CLI."""
    args = _parse_args()

    # Parse
    try:
        entries = parse_file(args.logfile)
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    if not entries:
        print("No log entries found in the file.", file=sys.stderr)
        sys.exit(1)

    # Optionally limit to the last N entries
    if args.last is not None:
        entries = entries[-args.last :]

    print(f"Parsed {len(entries)} log entries. Sending to {args.model}...\n")

    # Analyze
    analyze(entries, model=args.model, ollama_url=args.ollama_url)


def _parse_args() -> argparse.Namespace:
    """Define and parse CLI arguments."""
    parser = argparse.ArgumentParser(
        prog="sage",
        description="Analyze application logs using a local LLM via Ollama.",
    )
    parser.add_argument(
        "logfile",
        help="Path to the log file to analyze",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Ollama model to use (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--last",
        type=int,
        metavar="N",
        default=None,
        help="Only analyze the last N log entries",
    )
    parser.add_argument(
        "--ollama-url",
        default=OLLAMA_URL,
        help=f"Ollama server URL (default: {OLLAMA_URL})",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()
