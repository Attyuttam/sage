"""Unit tests for the log parser."""

from datetime import datetime
from pathlib import Path
import pytest

from parser import parse_file, _parse_line


class TestLogLineParser:
    """Test single line parsing logic."""

    def test_parse_valid_line_with_metadata(self):
        raw = "2026-08-31 09:05:15 WARN payment-service Database response slow request_id=REQ003 latency_ms=2800"
        entry = _parse_line(raw)

        assert entry is not None
        assert entry.timestamp == datetime(2026, 8, 31, 9, 5, 15)
        assert entry.level == "WARN"
        assert entry.service == "payment-service"
        assert entry.message == "Database response slow"
        assert entry.metadata == {"request_id": "REQ003", "latency_ms": "2800"}

    def test_parse_valid_line_without_metadata(self):
        raw = "2026-08-31 09:17:20 INFO payment-service Health check successful"
        entry = _parse_line(raw)

        assert entry is not None
        assert entry.timestamp == datetime(2026, 8, 31, 9, 17, 20)
        assert entry.level == "INFO"
        assert entry.service == "payment-service"
        assert entry.message == "Health check successful"
        assert entry.metadata == {}

    def test_parse_all_supported_levels(self):
        for level in ["INFO", "WARN", "ERROR", "DEBUG", "FATAL"]:
            raw = f"2026-08-31 09:00:00 {level} test-service Test message"
            entry = _parse_line(raw)
            assert entry is not None
            assert entry.level == level

    def test_parse_invalid_line_returns_none(self):
        assert _parse_line("This is not a log line") is None
        assert _parse_line("2026-99-99 99:99:99 INFO test-service Invalid date") is None
        assert _parse_line("   ") is None


class TestLogFileParser:
    """Test file reading and batch processing."""

    def test_parse_missing_file_raises_filenotfound(self):
        with pytest.raises(FileNotFoundError, match="Log file not found"):
            parse_file("non_existent_file.log")

    def test_parse_empty_file(self, tmp_path: Path):
        empty_file = tmp_path / "empty.log"
        empty_file.write_text("", encoding="utf-8")

        entries = parse_file(str(empty_file))
        assert entries == []

    def test_parse_file_with_blank_and_invalid_lines(self, tmp_path: Path):
        test_file = tmp_path / "test.log"
        content = (
            "\n"
            "2026-08-31 09:00:01 INFO auth-service User logged in user_id=U100\n"
            "   \n"
            "INVALID TRACE ERROR stack dump at line 40\n"
            "2026-08-31 09:00:02 ERROR auth-service Auth failed user_id=U101\n"
            "\n"
        )
        test_file.write_text(content, encoding="utf-8")

        entries = parse_file(str(test_file))
        assert len(entries) == 2
        assert entries[0].service == "auth-service"
        assert entries[0].level == "INFO"
        assert entries[1].level == "ERROR"

    def test_parse_sample_application_log(self):
        sample_path = Path("resources/application.log")
        assert sample_path.exists(), "Sample application.log should exist in resources/"

        entries = parse_file(str(sample_path))
        assert len(entries) == 65

        info_count = sum(1 for e in entries if e.level == "INFO")
        warn_count = sum(1 for e in entries if e.level == "WARN")
        error_count = sum(1 for e in entries if e.level == "ERROR")

        assert info_count == 39
        assert warn_count == 7
        assert error_count == 19
