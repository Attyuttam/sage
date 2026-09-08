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
    """Test IncidentAnalysis Pydantic validation rules and boundaries."""

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

    def test_valid_incident_data_succeeds(self, valid_data):
        """Validation Rule 1: Valid data satisfying all type and constraint rules succeeds."""
        analysis = IncidentAnalysis.model_validate(valid_data)
        assert analysis.severity == "HIGH"
        assert analysis.affected_services == ["payment-service", "order-service"]
        assert analysis.primary_issue == "Database connection timeout and pool exhaustion"
        assert analysis.probable_cause == "Latency spike led to exhausted connection pool"
        assert len(analysis.evidence) == 2
        assert analysis.confidence == 0.95

    @pytest.mark.parametrize("severity", ["LOW", "MEDIUM", "HIGH", "CRITICAL"])
    def test_all_valid_severities(self, valid_data, severity):
        """Validation Rule: Literal enum accepts exactly LOW, MEDIUM, HIGH, and CRITICAL."""
        valid_data["severity"] = severity
        analysis = IncidentAnalysis.model_validate(valid_data)
        assert analysis.severity == severity

    def test_missing_required_field_raises_validation_error(self, valid_data):
        """Validation Rule 2: Missing required field raises pydantic.ValidationError."""
        del valid_data["primary_issue"]
        with pytest.raises(ValidationError) as exc_info:
            IncidentAnalysis.model_validate(valid_data)

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("primary_issue",)
        assert errors[0]["type"] == "missing"

    @pytest.mark.parametrize(
        "missing_field",
        ["severity", "affected_services", "primary_issue", "probable_cause", "evidence", "confidence"],
    )
    def test_all_missing_required_fields(self, valid_data, missing_field):
        """Validation Rule 2 (comprehensive): Every required field without default raises ValidationError when missing."""
        del valid_data[missing_field]
        with pytest.raises(ValidationError) as exc_info:
            IncidentAnalysis.model_validate(valid_data)

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == (missing_field,)
        assert errors[0]["type"] == "missing"

    def test_invalid_severity_super_critical_raises_validation_error(self, valid_data):
        """Validation Rule 3: Invalid severity 'SUPER_CRITICAL' violates Literal constraint."""
        valid_data["severity"] = "SUPER_CRITICAL"
        with pytest.raises(ValidationError) as exc_info:
            IncidentAnalysis.model_validate(valid_data)

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("severity",)
        assert "literal_error" in errors[0]["type"]

    def test_confidence_below_zero_raises_validation_error(self, valid_data):
        """Validation Rule 4: Confidence below 0 (-0.2) violates Field(ge=0.0) constraint."""
        valid_data["confidence"] = -0.2
        with pytest.raises(ValidationError) as exc_info:
            IncidentAnalysis.model_validate(valid_data)

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("confidence",)
        assert "greater_than_equal" in errors[0]["type"]

    def test_confidence_above_one_raises_validation_error(self, valid_data):
        """Validation Rule 5: Confidence above 1 (1.5) violates Field(le=1.0) constraint."""
        valid_data["confidence"] = 1.5
        with pytest.raises(ValidationError) as exc_info:
            IncidentAnalysis.model_validate(valid_data)

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("confidence",)
        assert "less_than_equal" in errors[0]["type"]


class TestIncidentAnalysisDomainValidation:
    """Test domain-level constraints that go beyond JSON schema rules."""

    @pytest.fixture
    def valid_data(self) -> dict:
        return {
            "severity": "HIGH",
            "affected_services": ["payment-service"],
            "primary_issue": "Database connection pool exhausted",
            "probable_cause": "Latency spike led to exhausted connection pool",
            "evidence": ["09:08:15 DB pool exhausted active=100 max=100"],
            "confidence": 0.85,
        }

    def test_empty_primary_issue_raises_validation_error(self, valid_data):
        """Domain Rule: primary_issue must not be an empty string."""
        valid_data["primary_issue"] = ""
        with pytest.raises(ValidationError) as exc_info:
            IncidentAnalysis.model_validate(valid_data)

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("primary_issue",) for e in errors)

    def test_empty_probable_cause_raises_validation_error(self, valid_data):
        """Domain Rule: probable_cause must not be an empty string."""
        valid_data["probable_cause"] = ""
        with pytest.raises(ValidationError) as exc_info:
            IncidentAnalysis.model_validate(valid_data)

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("probable_cause",) for e in errors)

    @pytest.mark.parametrize("severity", ["HIGH", "CRITICAL"])
    def test_high_critical_with_empty_evidence_raises_validation_error(self, valid_data, severity):
        """Domain Rule: HIGH and CRITICAL incidents must include at least one evidence entry."""
        valid_data["severity"] = severity
        valid_data["evidence"] = []
        with pytest.raises(ValidationError) as exc_info:
            IncidentAnalysis.model_validate(valid_data)

        error_messages = str(exc_info.value)
        assert "evidence" in error_messages.lower() or severity.lower() in error_messages.lower()

    @pytest.mark.parametrize("severity", ["LOW", "MEDIUM"])
    def test_low_medium_with_empty_evidence_is_valid(self, valid_data, severity):
        """Domain Rule: LOW and MEDIUM incidents may have empty evidence."""
        valid_data["severity"] = severity
        valid_data["evidence"] = []
        analysis = IncidentAnalysis.model_validate(valid_data)
        assert analysis.evidence == []

    def test_low_confidence_is_valid(self, valid_data):
        """Domain Rule: Low confidence is valid — uncertainty is not the same as invalid data."""
        valid_data["severity"] = "LOW"
        valid_data["evidence"] = []
        valid_data["confidence"] = 0.05
        analysis = IncidentAnalysis.model_validate(valid_data)
        assert analysis.confidence == 0.05
