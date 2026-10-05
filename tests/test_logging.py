"""Unit tests for Sage logging observability and safety."""

import logging
from datetime import datetime
from unittest.mock import MagicMock, patch
import httpx
import pytest

from analyzer import LLMParseError, LLMValidationError, analyze
from cli import _parse_args, main, setup_logging
from models import IncidentAnalysis, LogEntry
from parser import parse_file


class TestSetupLogging:
    """Test setup_logging behavior and log level configuration."""

    def test_setup_logging_configures_level(self):
        setup_logging("DEBUG")
        assert logging.getLogger().level == logging.DEBUG

        setup_logging("WARNING")
        assert logging.getLogger().level == logging.WARNING

        setup_logging("INFO")
        assert logging.getLogger().level == logging.INFO


class TestParserLogging:
    """Test parser module logging behavior."""

    def test_parse_file_emits_info_log(self, tmp_path, caplog):
        log_file = tmp_path / "test.log"
        log_file.write_text(
            "2026-08-31 09:00:01 INFO auth-service User login\n"
            "2026-08-31 09:00:02 INFO order-service Order created\n",
            encoding="utf-8",
        )

        with caplog.at_level(logging.INFO, logger="parser"):
            entries = parse_file(str(log_file))

        assert len(entries) == 2
        assert any("Parsed 2 log entries from" in record.message for record in caplog.records)

    def test_parse_file_emits_debug_for_skipped_lines(self, tmp_path, caplog):
        log_file = tmp_path / "test.log"
        log_file.write_text(
            "2026-08-31 09:00:01 INFO auth-service User login\n"
            "This is a bad line\n",
            encoding="utf-8",
        )

        with caplog.at_level(logging.DEBUG, logger="parser"):
            entries = parse_file(str(log_file))

        assert len(entries) == 1
        assert any("Skipping unparseable log line" in record.message for record in caplog.records)


class TestAnalyzerLogging:
    """Test analyzer module logging levels and privacy safety."""

    @pytest.fixture
    def sample_entries(self) -> list[LogEntry]:
        return [
            LogEntry(
                timestamp=datetime(2026, 8, 31, 9, 5, 15),
                level="WARN",
                service="payment-service",
                message="Database response slow",
                metadata={"secret_token": "SENSITIVE_12345"},
            )
        ]

    @pytest.fixture
    def valid_analysis(self) -> IncidentAnalysis:
        return IncidentAnalysis(
            severity="HIGH",
            affected_services=["payment-service"],
            primary_issue="DB Issue",
            probable_cause="Pool exhaustion",
            evidence=["09:05:15 WARN slow"],
            confidence=0.9,
        )

    @patch("analyzer._generate_analysis")
    def test_analyze_success_logs_info_and_debug(self, mock_gen, sample_entries, valid_analysis, caplog):
        mock_gen.return_value = valid_analysis

        with caplog.at_level(logging.DEBUG, logger="analyzer"):
            result = analyze(sample_entries, model="llama3.2")

        assert result == valid_analysis

        # Check INFO logs for start and success
        assert any("Starting incident analysis on 1 log entries" in r.message and r.levelno == logging.INFO for r in caplog.records)
        assert any("Analysis validated successfully on attempt 1/3" in r.message and r.levelno == logging.INFO for r in caplog.records)

        # Check DEBUG logs for attempt
        assert any("Executing analysis attempt 1/3" in r.message and r.levelno == logging.DEBUG for r in caplog.records)

    @patch("analyzer._generate_analysis")
    def test_analyze_retry_logs_warning(self, mock_gen, sample_entries, valid_analysis, caplog):
        mock_gen.side_effect = [
            LLMParseError("bad json response"),
            valid_analysis,
        ]

        with caplog.at_level(logging.INFO, logger="analyzer"):
            result = analyze(sample_entries)

        assert result == valid_analysis

        # Check WARNING log on failed attempt 1
        warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warning_records) == 1
        assert "Attempt 1/3 failed with LLMParseError" in warning_records[0].message
        assert "Retrying..." in warning_records[0].message

    @patch("analyzer._generate_analysis")
    def test_analyze_exhausted_retries_logs_error(self, mock_gen, sample_entries, caplog):
        exc = LLMValidationError("schema validation failed")
        mock_gen.side_effect = [exc, exc, exc]

        with caplog.at_level(logging.INFO, logger="analyzer"):
            with pytest.raises(LLMValidationError):
                analyze(sample_entries, max_attempts=3)

        # Check ERROR log on exhausted attempts
        error_records = [r for r in caplog.records if r.levelno == logging.ERROR]
        assert len(error_records) == 1
        assert "Analysis failed after 3 attempts" in error_records[0].message

    @patch("analyzer.httpx.Client")
    def test_analyzer_logs_error_on_connection_failure(self, mock_client_cls, sample_entries, caplog):
        """Analyzer emits ERROR log on connection failure."""
        mock_client = MagicMock()
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_client
        mock_context.__exit__.return_value = None
        mock_client_cls.return_value = mock_context
        mock_client.post.side_effect = httpx.ConnectError("Connection refused")

        with caplog.at_level(logging.ERROR, logger="analyzer"):
            with pytest.raises(ConnectionError):
                analyze(sample_entries)

        assert any("Could not connect to Ollama" in r.message and r.levelno == logging.ERROR for r in caplog.records)

    @patch("analyzer.httpx.Client")
    def test_analyzer_logs_error_on_http_status_failure(self, mock_client_cls, sample_entries, caplog):
        """Analyzer emits ERROR log on HTTP status failure."""
        mock_client = MagicMock()
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_client
        mock_context.__exit__.return_value = None
        mock_client_cls.return_value = mock_context

        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_client.post.side_effect = httpx.HTTPStatusError("500 Error", request=MagicMock(), response=mock_resp)

        with caplog.at_level(logging.ERROR, logger="analyzer"):
            with pytest.raises(RuntimeError):
                analyze(sample_entries)

        assert any("Ollama returned HTTP 500" in r.message and r.levelno == logging.ERROR for r in caplog.records)

    @patch("analyzer.httpx.Client")
    def test_analyzer_does_not_log_full_prompt_or_secrets(self, mock_client_cls, sample_entries, caplog):
        """Ensure full prompts or secret metadata are NOT emitted in log messages."""
        mock_client = MagicMock()
        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_client
        mock_context.__exit__.return_value = None
        mock_client_cls.return_value = mock_context

        valid_json = (
            '{"severity": "HIGH", "affected_services": ["payment-service"], '
            '"primary_issue": "DB Issue", "probable_cause": "Timeout", '
            '"evidence": ["09:05:15 WARN slow"], "confidence": 0.9}'
        )
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {"response": valid_json}
        mock_client.post.return_value = mock_resp

        with caplog.at_level(logging.DEBUG):
            analyze(sample_entries)

        # Verify no log message contains the raw prompt template tags or secrets
        for record in caplog.records:
            assert "<log_data>" not in record.message
            assert "</log_data>" not in record.message
            assert "senior Site Reliability Engineer" not in record.message
            assert "SENSITIVE_12345" not in record.message


class TestCliLogging:
    """Test CLI module fatal and error logging behavior."""

    def test_cli_logs_error_on_file_not_found(self, monkeypatch, capsys):
        monkeypatch.setattr("sys.argv", ["sage", "non_existent_file.log"])
        with pytest.raises(SystemExit):
            main()

        captured = capsys.readouterr()
        assert "[ERROR] cli: Log file not found: non_existent_file.log" in captured.err

    @patch("cli.analyze", side_effect=ConnectionError("Could not connect to Ollama"))
    @patch("cli.parse_file", return_value=[LogEntry(datetime(2026, 8, 31, 9, 0, 0), "INFO", "svc", "msg")])
    def test_cli_logs_error_on_analysis_failure(self, mock_parse, mock_analyze, monkeypatch, capsys):
        monkeypatch.setattr("sys.argv", ["sage", "dummy.log"])
        with pytest.raises(SystemExit):
            main()

        captured = capsys.readouterr()
        assert "[ERROR] cli: Analysis failed: Could not connect to Ollama" in captured.err


