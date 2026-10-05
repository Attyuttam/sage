"""Unit tests for the CLI module."""

import json
from datetime import datetime
from unittest.mock import MagicMock, patch
import pytest

from analyzer import LLMParseError, LLMValidationError
from cli import _parse_args, main
from config import (
    DEFAULT_MODEL,
    LOG_LEVEL,
    MAX_ATTEMPTS,
    OLLAMA_URL,
    TEMPERATURE,
    TIMEOUT,
)
from models import IncidentAnalysis, LogEntry


class TestCliArgs:
    """Test argument parsing rules and defaults."""

    def test_default_arguments(self, monkeypatch):
        monkeypatch.setattr("sys.argv", ["sage", "app.log"])
        args = _parse_args()

        assert args.logfile == "app.log"
        assert args.model == DEFAULT_MODEL
        assert args.last is None
        assert args.ollama_url == OLLAMA_URL
        assert args.temperature == TEMPERATURE
        assert args.timeout == TIMEOUT
        assert args.max_attempts == MAX_ATTEMPTS
        assert args.log_level == LOG_LEVEL

    def test_custom_flags(self, monkeypatch):
        monkeypatch.setattr(
            "sys.argv",
            [
                "sage",
                "custom.log",
                "--model",
                "mistral",
                "--last",
                "50",
                "--ollama-url",
                "http://192.168.1.100:11434",
                "--temperature",
                "0.7",
                "--timeout",
                "45.5",
                "--max-attempts",
                "5",
                "--log-level",
                "DEBUG",
            ],
        )
        args = _parse_args()

        assert args.logfile == "custom.log"
        assert args.model == "mistral"
        assert args.last == 50
        assert args.ollama_url == "http://192.168.1.100:11434"
        assert args.temperature == 0.7
        assert args.timeout == 45.5
        assert args.max_attempts == 5
        assert args.log_level == "DEBUG"

    def test_invalid_log_level_choice_fails(self, monkeypatch):
        monkeypatch.setattr("sys.argv", ["sage", "app.log", "--log-level", "INVALID"])
        with pytest.raises(SystemExit) as exc_info:
            _parse_args()

        assert exc_info.value.code == 2

    def test_missing_required_logfile_fails(self, monkeypatch, capsys):
        monkeypatch.setattr("sys.argv", ["sage"])
        with pytest.raises(SystemExit) as exc_info:
            _parse_args()

        assert exc_info.value.code == 2

    def test_version_flag_exits_successfully(self, monkeypatch, capsys):
        monkeypatch.setattr("sys.argv", ["sage", "--version"])
        with pytest.raises(SystemExit) as exc_info:
            _parse_args()

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        output = captured.out or captured.err
        assert "0.1.0" in output


class TestCliMain:
    """Test CLI main orchestration flow."""

    @patch("cli.analyze")
    @patch("cli.parse_file")
    def test_main_success_flow(self, mock_parse, mock_analyze, monkeypatch, capsys):
        entries = [
            LogEntry(
                timestamp=datetime(2026, 8, 31, 9, 0, 1),
                level="INFO",
                service="auth",
                message="ok",
                metadata={},
            )
            for _ in range(5)
        ]
        mock_parse.return_value = entries
        mock_analyze.return_value = IncidentAnalysis(
            severity="HIGH",
            affected_services=["auth"],
            primary_issue="Auth degradation",
            probable_cause="Auth timeouts",
            evidence=["09:00:01 INFO"],
            confidence=0.9,
        )
        monkeypatch.setattr(
            "sys.argv",
            [
                "sage",
                "dummy.log",
                "--last",
                "2",
                "--model",
                "llama3.1:8b",
                "--temperature",
                "0.2",
                "--timeout",
                "90",
                "--max-attempts",
                "4",
            ],
        )

        main()

        # Should slice last 2 entries and forward all parameters
        mock_analyze.assert_called_once()
        sent_entries = mock_analyze.call_args[0][0]
        assert len(sent_entries) == 2
        kwargs = mock_analyze.call_args[1]
        assert kwargs["model"] == "llama3.1:8b"
        assert kwargs["temperature"] == 0.2
        assert kwargs["timeout"] == 90.0
        assert kwargs["max_attempts"] == 4

        captured = capsys.readouterr()
        assert "Parsed 2 log entries" in captured.out
        assert "VALIDATED INCIDENT ANALYSIS REPORT" in captured.out
        assert "Severity:          HIGH" in captured.out

    @patch("cli.analyze")
    @patch("cli.parse_file")
    def test_main_last_zero_analyzes_all_entries(self, mock_parse, mock_analyze, monkeypatch, capsys):
        entries = [LogEntry(datetime(2026, 8, 31, 9, 0, 1), "INFO", "auth", "ok", {}) for _ in range(3)]
        mock_parse.return_value = entries
        mock_analyze.return_value = IncidentAnalysis(
            severity="LOW",
            affected_services=[],
            primary_issue="Normal operation - no issues detected",
            probable_cause="N/A",
            evidence=[],
            confidence=0.9,
        )
        monkeypatch.setattr("sys.argv", ["sage", "dummy.log", "--last", "0"])

        main()

        assert mock_analyze.call_args[0][0] == entries
        assert "Parsed 3 log entries" in capsys.readouterr().out

    @patch("cli.analyze")
    @patch("cli.parse_file")
    def test_main_last_larger_than_entries_analyzes_all_entries(self, mock_parse, mock_analyze, monkeypatch, capsys):
        entries = [LogEntry(datetime(2026, 8, 31, 9, 0, 1), "INFO", "auth", "ok", {}) for _ in range(3)]
        mock_parse.return_value = entries
        mock_analyze.return_value = IncidentAnalysis(
            severity="LOW",
            affected_services=[],
            primary_issue="Normal operation - no issues detected",
            probable_cause="N/A",
            evidence=[],
            confidence=0.9,
        )
        monkeypatch.setattr("sys.argv", ["sage", "dummy.log", "--last", "10"])

        main()

        assert mock_analyze.call_args[0][0] == entries
        assert "Parsed 3 log entries" in capsys.readouterr().out

    @patch("cli.parse_file", side_effect=FileNotFoundError("Log file not found: test.log"))
    def test_main_file_not_found(self, mock_parse, monkeypatch, capsys):
        monkeypatch.setattr("sys.argv", ["sage", "test.log"])
        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Error: Log file not found: test.log" in captured.err

    @patch("cli.parse_file", return_value=[])
    def test_main_empty_file(self, mock_parse, monkeypatch, capsys):
        monkeypatch.setattr("sys.argv", ["sage", "empty.log"])
        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "No log entries found in the file." in captured.err

    @patch("cli.analyze", side_effect=LLMParseError("Malformed JSON string"))
    @patch("cli.parse_file", return_value=[LogEntry(datetime(2026, 8, 31, 9, 0, 0), "INFO", "svc", "msg")])
    def test_main_llm_parse_error(self, mock_parse, mock_analyze, monkeypatch, capsys):
        monkeypatch.setattr("sys.argv", ["sage", "app.log"])
        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Error: Malformed JSON string" in captured.err

    @patch("cli.analyze", side_effect=LLMValidationError("Invalid severity value"))
    @patch("cli.parse_file", return_value=[LogEntry(datetime(2026, 8, 31, 9, 0, 0), "INFO", "svc", "msg")])
    def test_main_llm_validation_error(self, mock_parse, mock_analyze, monkeypatch, capsys):
        monkeypatch.setattr("sys.argv", ["sage", "app.log"])
        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Error: Invalid severity value" in captured.err

    @patch("cli.analyze", side_effect=ConnectionError("Could not connect to Ollama at http://localhost:11434. Is it running?"))
    @patch("cli.parse_file", return_value=[LogEntry(datetime(2026, 8, 31, 9, 0, 0), "INFO", "svc", "msg")])
    def test_main_connection_error(self, mock_parse, mock_analyze, monkeypatch, capsys):
        monkeypatch.setattr("sys.argv", ["sage", "app.log"])
        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Error: Could not connect to Ollama" in captured.err
        assert "VALIDATED INCIDENT ANALYSIS REPORT" not in captured.out

    @patch("cli.analyze", side_effect=TimeoutError("Request to Ollama timed out after 120.0s. Is the machine overloaded?"))
    @patch("cli.parse_file", return_value=[LogEntry(datetime(2026, 8, 31, 9, 0, 0), "INFO", "svc", "msg")])
    def test_main_timeout_error(self, mock_parse, mock_analyze, monkeypatch, capsys):
        monkeypatch.setattr("sys.argv", ["sage", "app.log"])
        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Error: Request to Ollama timed out" in captured.err
        assert "VALIDATED INCIDENT ANALYSIS REPORT" not in captured.out

    @patch("cli.analyze", side_effect=RuntimeError("Ollama returned status 500. Is the model 'llama3.2' pulled?"))
    @patch("cli.parse_file", return_value=[LogEntry(datetime(2026, 8, 31, 9, 0, 0), "INFO", "svc", "msg")])
    def test_main_runtime_error(self, mock_parse, mock_analyze, monkeypatch, capsys):
        monkeypatch.setattr("sys.argv", ["sage", "app.log"])
        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Error: Ollama returned status 500" in captured.err
        assert "VALIDATED INCIDENT ANALYSIS REPORT" not in captured.out


class TestCliIntegration:
    """Full CLI integration pipeline test with real file parsing and mocked HTTP boundary."""

    @patch("analyzer.httpx.Client")
    def test_cli_end_to_end_mocked_http_pipeline(self, mock_client_cls, tmp_path, monkeypatch, capsys):
        log_file = tmp_path / "production.log"
        log_file.write_text(
            "2026-08-31 09:05:15 WARN payment-service DB slow latency_ms=2800\n"
            "2026-08-31 09:05:18 ERROR payment-service DB timeout request_id=REQ001\n",
            encoding="utf-8",
        )

        mock_client = MagicMock()
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_client
        mock_context.__exit__.return_value = None
        mock_client_cls.return_value = mock_context

        valid_response_json = json.dumps({
            "severity": "HIGH",
            "affected_services": ["payment-service"],
            "primary_issue": "Database connection timeout",
            "probable_cause": "High query latency caused connection pool exhaustion",
            "evidence": [
                "2026-08-31 09:05:15 WARN payment-service DB slow latency_ms=2800",
                "2026-08-31 09:05:18 ERROR payment-service DB timeout request_id=REQ001",
            ],
            "confidence": 0.95,
        })

        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {"response": valid_response_json}
        mock_client.post.return_value = mock_resp

        monkeypatch.setattr("sys.argv", ["sage", str(log_file), "--model", "llama3.2"])

        main()

        captured = capsys.readouterr()
        assert "Parsed 2 log entries. Sending to llama3.2..." in captured.out
        assert "VALIDATED INCIDENT ANALYSIS REPORT" in captured.out
        assert "Severity:          HIGH" in captured.out
        assert "Affected Services: payment-service" in captured.out
        assert "Primary Issue:     Database connection timeout" in captured.out
        assert "Probable Cause:    High query latency caused connection pool exhaustion" in captured.out
        assert "Confidence:        95.0%" in captured.out
        assert "2026-08-31 09:05:15 WARN payment-service DB slow" in captured.out

