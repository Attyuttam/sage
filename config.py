"""Default configuration for Sage.

Settings are loaded from environment variables (with a SAGE_ prefix)
and fall back to safe local defaults.
"""

import os


def _get_env_float(name: str, default: float) -> float:
    """Read a float from an environment variable, raising ValueError if invalid."""
    val = os.getenv(name)
    if val is None:
        return default
    try:
        return float(val)
    except ValueError as exc:
        raise ValueError(
            f"Invalid numeric value for environment variable {name}: '{val}'"
        ) from exc


def _get_env_int(name: str, default: int) -> int:
    """Read an integer from an environment variable, raising ValueError if invalid."""
    val = os.getenv(name)
    if val is None:
        return default
    try:
        return int(val)
    except ValueError as exc:
        raise ValueError(
            f"Invalid integer value for environment variable {name}: '{val}'"
        ) from exc


# Ollama server URL
OLLAMA_URL = os.getenv("SAGE_OLLAMA_URL", "http://localhost:11434")

# Model to use for analysis
DEFAULT_MODEL = os.getenv("SAGE_MODEL", "llama3.2")
MODEL = DEFAULT_MODEL

# Sampling temperature (0.0 for deterministic structured JSON extraction)
TEMPERATURE = _get_env_float("SAGE_TEMPERATURE", 0.0)

# Request timeout in seconds
TIMEOUT = _get_env_float("SAGE_TIMEOUT", 120.0)

# Maximum total analysis attempts (initial attempt + retries on parse/schema failures)
MAX_ATTEMPTS = _get_env_int("SAGE_MAX_ATTEMPTS", 3)

# Valid logging levels
VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


def _get_env_log_level(name: str, default: str) -> str:
    """Read and validate log level string from environment variable."""
    val = os.getenv(name)
    if val is None:
        return default
    val_upper = val.strip().upper()
    if val_upper not in VALID_LOG_LEVELS:
        raise ValueError(
            f"Invalid log level for environment variable {name}: '{val}'. Must be one of {sorted(VALID_LOG_LEVELS)}"
        )
    return val_upper


# Logging level (defaults to INFO)
LOG_LEVEL = _get_env_log_level("SAGE_LOG_LEVEL", "INFO")


