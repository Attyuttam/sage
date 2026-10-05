"""Command-line interface for Sage."""

import argparse
import logging
import sys

from analyzer import LLMParseError, LLMValidationError, analyze
from config import (
    DEFAULT_MODEL,
    LOG_LEVEL,
    MAX_ATTEMPTS,
    OLLAMA_URL,
    TEMPERATURE,
    TIMEOUT,
    VALID_LOG_LEVELS,
)
from parser import parse_file

__version__ = "0.1.0"
logger = logging.getLogger(__name__)


def setup_logging(level: str = LOG_LEVEL) -> None:
    """Configure root logging for the Sage application to stderr."""
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
        force=True,
    )


def main() -> None:
    """Entry point for the sage CLI."""
    args = _parse_args()
    setup_logging(args.log_level)
    logger.debug(
        "Starting Sage CLI (logfile='%s', model='%s', log_level='%s')",
        args.logfile,
        args.model,
        args.log_level,
    )

    # Parse
    try:
        entries = parse_file(args.logfile)
    except FileNotFoundError as exc:
        logger.error("Log file not found: %s", args.logfile)
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    if not entries:
        logger.warning("No log entries found in file: %s", args.logfile)
        print("No log entries found in the file.", file=sys.stderr)
        sys.exit(1)

    # Optionally limit to the last N entries
    if args.last is not None:
        logger.debug("Limiting analysis to last %d entries", args.last)
        entries = entries[-args.last :]

    print(f"Parsed {len(entries)} log entries. Sending to {args.model}...\n")

    # Analyze
    try:
        result = analyze(
            entries,
            model=args.model,
            ollama_url=args.ollama_url,
            temperature=args.temperature,
            timeout=args.timeout,
            max_attempts=args.max_attempts,
        )
    except (LLMParseError, LLMValidationError, ConnectionError, TimeoutError, RuntimeError) as exc:
        logger.error("Analysis failed: %s", exc)
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    # Display validated structured report
    print("\n" + "=" * 60)
    print("           VALIDATED INCIDENT ANALYSIS REPORT")
    print("=" * 60)
    print(f"Severity:          {result.severity}")
    print(f"Affected Services: {', '.join(result.affected_services)}")
    print(f"Primary Issue:     {result.primary_issue}")
    print(f"Probable Cause:    {result.probable_cause}")
    print(f"Confidence:        {result.confidence * 100:.1f}%")
    print("Evidence:")
    for item in result.evidence:
        print(f"  • {item}")
    print("=" * 60)


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
        "--temperature",
        type=float,
        default=TEMPERATURE,
        help=f"Sampling temperature (default: {TEMPERATURE})",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=TIMEOUT,
        help=f"Request timeout in seconds (default: {TIMEOUT})",
    )
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=MAX_ATTEMPTS,
        help=f"Maximum total analysis attempts (default: {MAX_ATTEMPTS})",
    )
    parser.add_argument(
        "--log-level",
        default=LOG_LEVEL,
        choices=sorted(VALID_LOG_LEVELS),
        type=str.upper,
        help=f"Logging level (default: {LOG_LEVEL})",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()

