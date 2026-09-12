"""Week 3 Day 1 experiment: compare Sage analyses across input sizes.

This is a standalone learning script. It does not change Sage application behavior.
"""

import json
import sys
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from analyzer import _build_prompt, analyze
from parser import parse_file


ENTRY_COUNTS = (5, 15, 30, 65)
LOG_PATH = PROJECT_ROOT / "resources" / "application.log"
TOKEN_COUNT_MESSAGE = "not exposed by current Sage implementation"


def main() -> None:
    """Run the same Sage analysis against increasingly large log suffixes."""
    all_entries = parse_file(str(LOG_PATH))

    print("Week 3 Day 1: Tokens and Context Windows")
    print(f"Log file: {LOG_PATH}")
    print(f"Total parsed entries available: {len(all_entries)}")

    for requested_count in ENTRY_COUNTS:
        entries = all_entries[-requested_count:]
        prompt = _build_prompt(entries)

        start = time.perf_counter()
        analysis = analyze(entries)
        latency_seconds = time.perf_counter() - start

        print("\n" + "=" * 60)
        print(f"Requested entry count: {requested_count}")
        print(f"Parsed entry count: {len(entries)}")
        print(f"Prompt character count: {len(prompt)}")
        print(f"Token count: {TOKEN_COUNT_MESSAGE}")
        print(f"Complete-call latency: {latency_seconds:.3f} seconds")
        print("Resulting IncidentAnalysis:")
        print(json.dumps(analysis.model_dump(), indent=2))


if __name__ == "__main__":
    main()