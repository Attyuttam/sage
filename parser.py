"""Parse application log files into structured LogEntry objects."""

import re
from datetime import datetime
from pathlib import Path

from models import LogEntry

# Matches lines like:
#   2026-08-31 09:00:01 INFO payment-service Payment request received request_id=REQ001 user_id=U101
#
# Groups: timestamp, level, service, remainder (message + optional key=value pairs)
_LINE_PATTERN = re.compile(
    r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})"  # timestamp
    r"\s+(INFO|WARN|ERROR|DEBUG|FATAL)"            # level
    r"\s+([\w-]+)"                                 # service name
    r"\s+(.+)$"                                    # remainder
)

# Matches key=value pairs at the end of a log message
_KV_PATTERN = re.compile(r"(\w+)=([\w.%-]+)")

_TIMESTAMP_FMT = "%Y-%m-%d %H:%M:%S"


def parse_file(path: str) -> list[LogEntry]:
    """Read a log file and return a list of parsed entries.

    Lines that don't match the expected format are silently skipped.
    """
    log_path = Path(path)
    if not log_path.exists():
        raise FileNotFoundError(f"Log file not found: {path}")

    entries: list[LogEntry] = []

    with open(log_path, encoding="utf-8") as f:
        for line_number, raw_line in enumerate(f, start=1):
            line = raw_line.strip()
            if not line:
                continue

            entry = _parse_line(line, line_number)
            if entry is not None:
                entries.append(entry)

    return entries


def _parse_line(line: str, line_number: int) -> LogEntry | None:
    """Parse a single log line into a LogEntry, or None if it doesn't match."""
    match = _LINE_PATTERN.match(line)
    if not match:
        return None

    timestamp_str, level, service, remainder = match.groups()

    try:
        timestamp = datetime.strptime(timestamp_str, _TIMESTAMP_FMT)
    except ValueError:
        return None

    # Separate the human-readable message from trailing key=value pairs
    metadata: dict[str, str] = {}
    kv_pairs = _KV_PATTERN.findall(remainder)
    if kv_pairs:
        metadata = dict(kv_pairs)
        # Strip key=value tokens to isolate the message text
        message = _KV_PATTERN.sub("", remainder).strip()
    else:
        message = remainder.strip()

    return LogEntry(
        timestamp=timestamp,
        level=level,
        service=service,
        message=message,
        metadata=metadata,
    )
