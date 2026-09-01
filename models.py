"""Data models for structured log representation."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class LogEntry:
    """A single parsed log line.

    Attributes:
        timestamp: When the event occurred.
        level:     Severity — INFO, WARN, ERROR, etc.
        service:   The originating microservice name.
        message:   Human-readable event description.
        metadata:  Key-value pairs extracted from the line (e.g. request_id, user_id).
    """

    timestamp: datetime
    level: str
    service: str
    message: str
    metadata: dict[str, str] = field(default_factory=dict)

    def __str__(self) -> str:
        ts = self.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        meta = " ".join(f"{k}={v}" for k, v in self.metadata.items())
        parts = [ts, self.level, self.service, self.message]
        if meta:
            parts.append(meta)
        return " ".join(parts)
