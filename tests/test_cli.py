"""Unit tests for the CLI module."""

from datetime import datetime
from unittest.mock import patch
import pytest

from analyzer import LLMParseError, LLMValidationError
from cli import _parse_args, main
from config import DEFAULT_MODEL, OLLAMA_URL
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
            ],
        )
        args = _parse_args()

        assert args.logfile == "custom.log"
        assert args.model == "mistral"
        assert args.last == 50
        assert args.ollama_url == "http://192.168.1.100:11434"

    def test_missing_required_logfile_fails(self, monkeypatch, capsys):
        monkeypatch.setattr("sys.argv", ["sage"])
        with pytest.raises(SystemExit) as exc_info:
            _parse_args()

        assert exc_info.value.code == 2


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
        monkeypatch.setattr("sys.argv", ["sage", "dummy.log", "--last", "2"])

        main()

        # Should slice last 2 entries
        mock_analyze.assert_called_once()
        sent_entries = mock_analyze.call_args[0][0]
        assert len(sent_entries) == 2

        captured = capsys.readouterr()
        assert "Parsed 2 log entries" in captured.out
        assert "VALIDATED INCIDENT ANALYSIS REPORT" in captured.out
        assert "Severity:          HIGH" in captured.out

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
