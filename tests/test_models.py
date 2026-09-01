"""Unit tests for LogEntry data model."""

from datetime import datetime
from models import LogEntry


class TestLogEntry:
    """Test LogEntry instantiation and string representation."""

    def test_log_entry_fields(self):
        ts = datetime(2026, 8, 31, 9, 0, 1)
        entry = LogEntry(
            timestamp=ts,
            level="INFO",
            service="payment-service",
            message="Payment request received",
            metadata={"request_id": "REQ001", "amount": "2500"},
        )
        assert entry.timestamp == ts
        assert entry.level == "INFO"
        assert entry.service == "payment-service"
        assert entry.message == "Payment request received"
        assert entry.metadata == {"request_id": "REQ001", "amount": "2500"}

    def test_log_entry_str_with_metadata(self):
        entry = LogEntry(
            timestamp=datetime(2026, 8, 31, 9, 0, 1),
            level="INFO",
            service="payment-service",
            message="Payment request received",
            metadata={"request_id": "REQ001", "user_id": "U101"},
        )
        assert str(entry) == "2026-08-31 09:00:01 INFO payment-service Payment request received request_id=REQ001 user_id=U101"

    def test_log_entry_str_without_metadata(self):
        entry = LogEntry(
            timestamp=datetime(2026, 8, 31, 9, 8, 45),
            level="INFO",
            service="payment-service",
            message="Health check started",
        )
        assert str(entry) == "2026-08-31 09:08:45 INFO payment-service Health check started"
