"""Unit tests for LogEntry and IncidentAnalysis data models."""

from datetime import datetime
import pytest
from pydantic import ValidationError

from models import LogEntry, IncidentAnalysis


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


class TestIncidentAnalysis:
    """Test IncidentAnalysis Pydantic validation boundaries."""

    @pytest.fixture
    def valid_data(self) -> dict:
        return {
            "severity": "HIGH",
            "affected_services": ["payment-service", "order-service"],
            "primary_issue": "Database connection timeout and pool exhaustion",
            "probable_cause": "Latency spike led to exhausted connection pool",
            "evidence": [
                "09:05:15 Database response slow latency_ms=2800",
                "09:08:15 Database connection pool exhausted active=100 max=100",
            ],
            "confidence": 0.95,
        }

    def test_completely_valid_data(self, valid_data):
        """Test 1: Completely valid data constructs properly."""
        analysis = IncidentAnalysis.model_validate(valid_data)
        assert analysis.severity == "HIGH"
        assert analysis.affected_services == ["payment-service", "order-service"]
        assert analysis.primary_issue == "Database connection timeout and pool exhaustion"
        assert analysis.probable_cause == "Latency spike led to exhausted connection pool"
        assert len(analysis.evidence) == 2
        assert analysis.confidence == 0.95

    @pytest.mark.parametrize("severity", ["LOW", "MEDIUM", "HIGH", "CRITICAL"])
    def test_all_valid_severities(self, valid_data, severity):
        valid_data["severity"] = severity
        analysis = IncidentAnalysis.model_validate(valid_data)
        assert analysis.severity == severity

    def test_invalid_severity(self, valid_data):
        """Test 2: Invalid severity string is rejected."""
        valid_data["severity"] = "MODERATE"
        with pytest.raises(ValidationError) as exc_info:
            IncidentAnalysis.model_validate(valid_data)

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("severity",)
        assert "literal_error" in errors[0]["type"]

    def test_confidence_below_zero(self, valid_data):
        """Test 3: Confidence below 0.0 is rejected."""
        valid_data["confidence"] = -0.1
        with pytest.raises(ValidationError) as exc_info:
            IncidentAnalysis.model_validate(valid_data)

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("confidence",)
        assert "greater_than_equal" in errors[0]["type"]

    def test_confidence_above_one(self, valid_data):
        """Test 4: Confidence above 1.0 is rejected."""
        valid_data["confidence"] = 1.05
        with pytest.raises(ValidationError) as exc_info:
            IncidentAnalysis.model_validate(valid_data)

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("confidence",)
        assert "less_than_equal" in errors[0]["type"]

    @pytest.mark.parametrize(
        "missing_field",
        ["severity", "affected_services", "primary_issue", "probable_cause", "evidence", "confidence"],
    )
    def test_missing_required_field(self, valid_data, missing_field):
        """Test 5: Missing any required field raises ValidationError."""
        del valid_data[missing_field]
        with pytest.raises(ValidationError) as exc_info:
            IncidentAnalysis.model_validate(valid_data)

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == (missing_field,)
        assert errors[0]["type"] == "missing"
