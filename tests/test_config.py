"""Unit tests for Sage configuration module."""

import importlib
import pytest

import config


class TestConfigDefaults:
    """Test default configuration values when no SAGE_* environment variables are set."""

    def test_default_values(self, monkeypatch):
        for var in [
            "SAGE_OLLAMA_URL",
            "SAGE_MODEL",
            "SAGE_TEMPERATURE",
            "SAGE_TIMEOUT",
            "SAGE_MAX_ATTEMPTS",
            "SAGE_LOG_LEVEL",
        ]:
            monkeypatch.delenv(var, raising=False)

        importlib.reload(config)

        assert config.OLLAMA_URL == "http://localhost:11434"
        assert config.DEFAULT_MODEL == "llama3.2"
        assert config.MODEL == "llama3.2"
        assert config.TEMPERATURE == 0.0
        assert config.TIMEOUT == 120.0
        assert config.MAX_ATTEMPTS == 3
        assert config.LOG_LEVEL == "INFO"


class TestConfigEnvOverrides:
    """Test environment variable overrides for configuration values."""

    def test_env_var_overrides(self, monkeypatch):
        monkeypatch.setenv("SAGE_OLLAMA_URL", "http://remote-gpu:11434")
        monkeypatch.setenv("SAGE_MODEL", "llama3.1:8b")
        monkeypatch.setenv("SAGE_TEMPERATURE", "0.7")
        monkeypatch.setenv("SAGE_TIMEOUT", "300.5")
        monkeypatch.setenv("SAGE_MAX_ATTEMPTS", "5")
        monkeypatch.setenv("SAGE_LOG_LEVEL", "DEBUG")

        importlib.reload(config)

        assert config.OLLAMA_URL == "http://remote-gpu:11434"
        assert config.DEFAULT_MODEL == "llama3.1:8b"
        assert config.MODEL == "llama3.1:8b"
        assert config.TEMPERATURE == 0.7
        assert config.TIMEOUT == 300.5
        assert config.MAX_ATTEMPTS == 5
        assert config.LOG_LEVEL == "DEBUG"


class TestConfigValidation:
    """Test that invalid numeric or enum configuration values raise clear configuration errors."""

    def test_invalid_temperature_raises_value_error(self, monkeypatch):
        monkeypatch.setenv("SAGE_TEMPERATURE", "not-a-number")
        with pytest.raises(ValueError) as exc_info:
            importlib.reload(config)

        assert "Invalid numeric value for environment variable SAGE_TEMPERATURE" in str(exc_info.value)

    def test_invalid_timeout_raises_value_error(self, monkeypatch):
        monkeypatch.setenv("SAGE_TIMEOUT", "invalid_timeout")
        with pytest.raises(ValueError) as exc_info:
            importlib.reload(config)

        assert "Invalid numeric value for environment variable SAGE_TIMEOUT" in str(exc_info.value)

    def test_invalid_max_attempts_raises_value_error(self, monkeypatch):
        monkeypatch.setenv("SAGE_MAX_ATTEMPTS", "three")
        with pytest.raises(ValueError) as exc_info:
            importlib.reload(config)

        assert "Invalid integer value for environment variable SAGE_MAX_ATTEMPTS" in str(exc_info.value)

    def test_invalid_float_max_attempts_raises_value_error(self, monkeypatch):
        monkeypatch.setenv("SAGE_MAX_ATTEMPTS", "3.5")
        with pytest.raises(ValueError) as exc_info:
            importlib.reload(config)

        assert "Invalid integer value for environment variable SAGE_MAX_ATTEMPTS" in str(exc_info.value)

    def test_invalid_log_level_raises_value_error(self, monkeypatch):
        monkeypatch.setenv("SAGE_LOG_LEVEL", "VERBOSE")
        with pytest.raises(ValueError) as exc_info:
            importlib.reload(config)

        assert "Invalid log level for environment variable SAGE_LOG_LEVEL" in str(exc_info.value)

    @pytest.mark.parametrize(
        "raw_level, expected_level",
        [
            ("  debug  ", "DEBUG"),
            ("warning", "WARNING"),
            (" error\t", "ERROR"),
            ("critical", "CRITICAL"),
            ("INFO", "INFO"),
        ],
    )
    def test_log_level_case_and_whitespace_normalization(self, monkeypatch, raw_level, expected_level):
        monkeypatch.setenv("SAGE_LOG_LEVEL", raw_level)
        importlib.reload(config)

        assert config.LOG_LEVEL == expected_level


