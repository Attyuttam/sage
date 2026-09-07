import json
from datetime import datetime
from unittest.mock import MagicMock, patch
import pytest
import httpx
from pydantic import ValidationError

from analyzer import (
    LLMParseError,
    LLMValidationError,
    analyze,
    _build_prompt,
    _generate_analysis,
)
from models import IncidentAnalysis, LogEntry


@pytest.fixture
def sample_entries() -> list[LogEntry]:
    return [
        LogEntry(
            timestamp=datetime(2026, 8, 31, 9, 5, 15),
            level="WARN",
            service="payment-service",
            message="Database response slow",
            metadata={"request_id": "REQ003", "latency_ms": "2800"},
        ),
        LogEntry(
            timestamp=datetime(2026, 8, 31, 9, 5, 18),
            level="ERROR",
            service="payment-service",
            message="Database connection timeout",
            metadata={"request_id": "REQ003"},
        ),
    ]


class TestPromptBuilder:
    """Test prompt template generation from log entries."""

    def test_build_prompt_contains_sre_persona_and_json_schema(self, sample_entries: list[LogEntry]):
        prompt = _build_prompt(sample_entries)

        assert "senior Site Reliability Engineer" in prompt
        assert "ONLY with a single valid JSON object" in prompt
        assert '"severity": "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"' in prompt
        assert '"affected_services"' in prompt
        assert '"primary_issue"' in prompt
        assert '"probable_cause"' in prompt
        assert '"evidence"' in prompt
        assert '"confidence"' in prompt

    def test_build_prompt_contains_serialized_log_lines(self, sample_entries: list[LogEntry]):
        prompt = _build_prompt(sample_entries)

        assert "2026-08-31 09:05:15 WARN payment-service Database response slow request_id=REQ003 latency_ms=2800" in prompt
        assert "2026-08-31 09:05:18 ERROR payment-service Database connection timeout request_id=REQ003" in prompt


class TestAnalyzerGeneration:
    """Test HTTP client and Ollama generation logic with mocked network calls."""

    @patch("analyzer.httpx.Client")
    def test_generate_analysis_success(self, mock_client_cls):
        # Mock non-streaming response returning valid IncidentAnalysis JSON
        valid_json = (
            '{"severity": "HIGH", "affected_services": ["payment-service"], '
            '"primary_issue": "DB Timeout", "probable_cause": "Pool exhausted", '
            '"evidence": ["09:05:18 DB_TIMEOUT"], "confidence": 0.95}'
        )

        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"response": valid_json}

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response

        mock_client_context = MagicMock()
        mock_client_context.__enter__.return_value = mock_client
        mock_client_context.__exit__.return_value = None
        mock_client_cls.return_value = mock_client_context

        result = _generate_analysis("test prompt", model="llama3.2", ollama_url="http://localhost:11434")

        # Verify validated IncidentAnalysis return object
        assert isinstance(result, IncidentAnalysis)
        assert result.severity == "HIGH"
        assert result.affected_services == ["payment-service"]
        assert result.primary_issue == "DB Timeout"
        assert result.confidence == 0.95

        # Verify POST payload
        mock_client.post.assert_called_once_with(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3.2",
                "prompt": "test prompt",
                "stream": False,
                "format": "json",
            },
        )

    @patch("analyzer.httpx.Client")
    def test_generate_analysis_invalid_json(self, mock_client_cls):
        # Mock response returning non-JSON plain text
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"response": "This is plain text, not JSON"}

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response

        mock_client_context = MagicMock()
        mock_client_context.__enter__.return_value = mock_client
        mock_client_context.__exit__.return_value = None
        mock_client_cls.return_value = mock_client_context

        with pytest.raises(LLMParseError) as exc_info:
            _generate_analysis("test prompt", model="llama3.2", ollama_url="http://localhost:11434")

        assert "LLM returned invalid JSON" in str(exc_info.value)
        assert isinstance(exc_info.value.__cause__, json.JSONDecodeError)

    @patch("analyzer.httpx.Client")
    def test_generate_analysis_schema_validation_error(self, mock_client_cls):
        # Mock response returning valid JSON but invalid schema
        invalid_schema_json = '{"severity": "UNKNOWN", "affected_services": [], "primary_issue": "none", "probable_cause": "none", "evidence": [], "confidence": 5.0}'
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"response": invalid_schema_json}

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response

        mock_client_context = MagicMock()
        mock_client_context.__enter__.return_value = mock_client
        mock_client_context.__exit__.return_value = None
        mock_client_cls.return_value = mock_client_context

        with pytest.raises(LLMValidationError) as exc_info:
            _generate_analysis("test prompt", model="llama3.2", ollama_url="http://localhost:11434")

        assert "LLM output failed schema validation" in str(exc_info.value)
        assert isinstance(exc_info.value.__cause__, ValidationError)

    @patch("analyzer.httpx.Client")
    def test_generate_analysis_connection_error(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client.post.side_effect = httpx.ConnectError("Connection refused")

        mock_client_context = MagicMock()
        mock_client_context.__enter__.return_value = mock_client
        mock_client_context.__exit__.return_value = None
        mock_client_cls.return_value = mock_client_context

        with pytest.raises(ConnectionError) as exc_info:
            _generate_analysis("test prompt", model="llama3.2", ollama_url="http://localhost:11434")

        assert "Could not connect to Ollama" in str(exc_info.value)
        assert isinstance(exc_info.value.__cause__, httpx.ConnectError)

    @patch("analyzer.httpx.Client")
    def test_generate_analysis_http_status_error(self, mock_client_cls):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_error = httpx.HTTPStatusError(
            "404 Not Found",
            request=MagicMock(),
            response=mock_response,
        )

        mock_client = MagicMock()
        mock_client.post.side_effect = mock_error

        mock_client_context = MagicMock()
        mock_client_context.__enter__.return_value = mock_client
        mock_client_context.__exit__.return_value = None
        mock_client_cls.return_value = mock_client_context

        with pytest.raises(RuntimeError) as exc_info:
            _generate_analysis("test prompt", model="non-existent-model", ollama_url="http://localhost:11434")

        assert "Ollama returned status 404" in str(exc_info.value)
        assert isinstance(exc_info.value.__cause__, httpx.HTTPStatusError)

    @patch("analyzer._generate_analysis")
    def test_analyze_orchestration(self, mock_generate, sample_entries: list[LogEntry]):
        expected = IncidentAnalysis(
            severity="CRITICAL",
            affected_services=["payment-service"],
            primary_issue="DB Outage",
            probable_cause="Timeout",
            evidence=["09:05:18 DB_TIMEOUT"],
            confidence=0.9,
        )
        mock_generate.return_value = expected

        result = analyze(sample_entries, model="mistral", ollama_url="http://custom:11434")

        assert result == expected
        mock_generate.assert_called_once()
        call_args, call_kwargs = mock_generate.call_args
        prompt_arg = call_args[0]
        assert "senior Site Reliability Engineer" in prompt_arg
        assert call_kwargs["model"] == "mistral"
        assert call_kwargs["ollama_url"] == "http://custom:11434"
