"""Data models for structured log representation and incident analysis."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


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


class IncidentAnalysis(BaseModel):
    """Structured incident analysis output from LLM log examination.

    Attributes:
        severity:          Severity level strictly bounded to LOW, MEDIUM, HIGH, CRITICAL.
        affected_services: List of microservice names impacted by the incident.
        primary_issue:     Concise summary headline of the primary failure.
        probable_cause:    Detailed root cause explanation deduced from logs.
        evidence:          Specific log lines, timestamps, or errors supporting findings.
        confidence:        Confidence score between 0.0 and 1.0.
    """

    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    affected_services: list[str]
    primary_issue: str
    probable_cause: str
    evidence: list[str]
    confidence: float = Field(..., ge=0.0, le=1.0)
