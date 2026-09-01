"""Unit tests for the LLM analyzer and prompt construction."""

from datetime import datetime
from unittest.mock import MagicMock, patch
import pytest
import httpx

from analyzer import analyze, _build_prompt, _stream_response
from models import LogEntry


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

    def test_build_prompt_contains_sre_persona_and_instructions(self, sample_entries: list[LogEntry]):
        prompt = _build_prompt(sample_entries)

        assert "senior Site Reliability Engineer" in prompt
        assert "A brief summary of what happened" in prompt
        assert "Root cause analysis" in prompt
        assert "timeline of the incident" in prompt
        assert "Recommended actions" in prompt

    def test_build_prompt_contains_serialized_log_lines(self, sample_entries: list[LogEntry]):
        prompt = _build_prompt(sample_entries)

        assert "2026-08-31 09:05:15 WARN payment-service Database response slow request_id=REQ003 latency_ms=2800" in prompt
        assert "2026-08-31 09:05:18 ERROR payment-service Database connection timeout request_id=REQ003" in prompt


class TestAnalyzerStreaming:
    """Test HTTP client and Ollama streaming logic with mocked network calls."""

    @patch("analyzer.httpx.Client")
    def test_stream_response_success(self, mock_client_cls, capsys):
        # Mock streaming response
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.iter_lines.return_value = [
            '{"response": "Root ", "done": false}',
            '{"response": "cause: ", "done": false}',
            '{"response": "DB timeout", "done": true}',
        ]

        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_response
        mock_context.__exit__.return_value = None

        mock_client = MagicMock()
        mock_client.stream.return_value = mock_context

        mock_client_context = MagicMock()
        mock_client_context.__enter__.return_value = mock_client
        mock_client_context.__exit__.return_value = None
        mock_client_cls.return_value = mock_client_context

        _stream_response("test prompt", model="llama3.2", ollama_url="http://localhost:11434")

        captured = capsys.readouterr()
        assert "Root cause: DB timeout" in captured.out

    @patch("analyzer.httpx.Client")
    def test_stream_response_connection_error(self, mock_client_cls, capsys):
        mock_client = MagicMock()
        mock_client.stream.side_effect = httpx.ConnectError("Connection refused")

        mock_client_context = MagicMock()
        mock_client_context.__enter__.return_value = mock_client
        mock_client_context.__exit__.return_value = None
        mock_client_cls.return_value = mock_client_context

        with pytest.raises(SystemExit) as exc_info:
            _stream_response("test prompt", model="llama3.2", ollama_url="http://localhost:11434")

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Could not connect to Ollama" in captured.err

    @patch("analyzer.httpx.Client")
    def test_stream_response_http_status_error(self, mock_client_cls, capsys):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_error = httpx.HTTPStatusError(
            "404 Not Found",
            request=MagicMock(),
            response=mock_response,
        )

        mock_client = MagicMock()
        mock_client.stream.side_effect = mock_error

        mock_client_context = MagicMock()
        mock_client_context.__enter__.return_value = mock_client
        mock_client_context.__exit__.return_value = None
        mock_client_cls.return_value = mock_client_context

        with pytest.raises(SystemExit) as exc_info:
            _stream_response("test prompt", model="non-existent-model", ollama_url="http://localhost:11434")

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Ollama returned status 404" in captured.err

    @patch("analyzer._stream_response")
    def test_analyze_orchestration(self, mock_stream, sample_entries: list[LogEntry]):
        analyze(sample_entries, model="mistral", ollama_url="http://custom:11434")

        mock_stream.assert_called_once()
        call_args, call_kwargs = mock_stream.call_args
        prompt_arg = call_args[0]
        assert "senior Site Reliability Engineer" in prompt_arg
        assert call_kwargs["model"] == "mistral"
        assert call_kwargs["ollama_url"] == "http://custom:11434"
