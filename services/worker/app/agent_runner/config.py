"""Agent runner config — env defaults + runtime override from local JSON file.

Module-level constants snapshot env at import time (kept for backwards compat).
For live runtime values that reflect the Provider Settings UI, call
``load_effective_provider_config()`` — it re-reads env + the override file
on every call, so no worker restart is needed after a Save.
"""
import json
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ── Env-snapshot constants (kept for backwards compat) ─────────────────────
AGENT_RUNNER_ENABLED: bool = os.getenv("AGENT_RUNNER_ENABLED", "false").lower() == "true"
AGENT_RUNNER_MODE: str = os.getenv("AGENT_RUNNER_MODE", "prompt_only")
HERMES_API_URL: str = os.getenv("HERMES_API_URL", "")
HERMES_API_KEY: str = os.getenv("HERMES_API_KEY", "")
HERMES_TIMEOUT_MS: int = int(os.getenv("HERMES_TIMEOUT_MS", "120000"))
HERMES_TIMEOUT_SECONDS: float = float(os.getenv("HERMES_TIMEOUT_SECONDS", str(int(os.getenv("HERMES_TIMEOUT_MS", "120000")) / 1000)))
HERMES_FALLBACK_MODE: str = os.getenv("HERMES_FALLBACK_MODE", "hermes_manual")
HERMES_RETRY_ATTEMPTS: int = int(os.getenv("HERMES_RETRY_ATTEMPTS", "1"))
HERMES_RETRY_BACKOFF_SECONDS: float = float(os.getenv("HERMES_RETRY_BACKOFF_SECONDS", "2"))
HERMES_PROVIDER: str = os.getenv("HERMES_PROVIDER", "openai_compatible")
HERMES_REQUEST_FORMAT: str = os.getenv("HERMES_REQUEST_FORMAT", "native")
HERMES_MODEL: str = os.getenv("HERMES_MODEL", "")

# Optional temperature override. Leave blank → omit from payload (provider default).
_HERMES_TEMP_STR: str = (os.getenv("HERMES_TEMPERATURE", "") or "").strip()
try:
    HERMES_TEMPERATURE: Optional[float] = float(_HERMES_TEMP_STR) if _HERMES_TEMP_STR else None
except ValueError:
    HERMES_TEMPERATURE = None

AGENT_RUNNER_ARTIFACT_DIR: str = os.getenv("AGENT_RUNNER_ARTIFACT_DIR", "/app/data/agent-runs")
AGENT_RUNS_FILE: str = os.getenv("AGENT_RUNS_FILE", "/app/data/agent-runs.json")


# ── Runtime effective config ───────────────────────────────────────────────
PROVIDER_SETTINGS_PATH: Path = Path("/app/data/provider-settings.local.json")


def _safe_load_overrides() -> dict:
    """Read JSON override file. Returns {} on any error (file missing, malformed, etc)."""
    try:
        if not PROVIDER_SETTINGS_PATH.exists():
            return {}
        raw = PROVIDER_SETTINGS_PATH.read_text(encoding="utf-8")
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except Exception as exc:
        logger.warning("provider-settings: cannot read %s: %s", PROVIDER_SETTINGS_PATH, exc)
        return {}


def _coerce_float(v, default: float) -> float:
    try:
        if v is None or v == "":
            return default
        return float(v)
    except (ValueError, TypeError):
        return default


def _coerce_int(v, default: int) -> int:
    try:
        if v is None or v == "":
            return default
        return int(v)
    except (ValueError, TypeError):
        return default


def _coerce_opt_float(v) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def load_effective_provider_config() -> dict:
    """Return the live effective provider config.

    Precedence: local-override-file > env > built-in default.

    Call this every time an agent run starts — it is cheap (single small
    file read) and reflects the latest Save from the Provider Settings UI
    without needing a worker restart.
    """
    ov = _safe_load_overrides()

    def s(key: str, env_key: str, default: str) -> str:
        if key in ov and ov.get(key) not in (None, ""):
            return str(ov[key])
        return os.getenv(env_key, default) or default

    def b(key: str, env_key: str, default: bool) -> bool:
        if key in ov and ov.get(key) is not None:
            return bool(ov[key])
        return os.getenv(env_key, "true" if default else "false").lower() == "true"

    # Temperature is special: None means "omit from payload"
    if "hermes_temperature" in ov:
        temperature = _coerce_opt_float(ov.get("hermes_temperature"))
    else:
        temperature = _coerce_opt_float(os.getenv("HERMES_TEMPERATURE", ""))

    return {
        "agent_runner_enabled":       b("agent_runner_enabled",       "AGENT_RUNNER_ENABLED",       False),
        "agent_runner_mode":          s("agent_runner_mode",          "AGENT_RUNNER_MODE",          "prompt_only"),
        "hermes_provider":            s("hermes_provider",            "HERMES_PROVIDER",            "openai_compatible"),
        "hermes_request_format":      s("hermes_request_format",      "HERMES_REQUEST_FORMAT",      "native"),
        "hermes_api_url":             s("hermes_api_url",             "HERMES_API_URL",             ""),
        "hermes_api_key":             s("hermes_api_key",             "HERMES_API_KEY",             ""),
        "hermes_model":               s("hermes_model",               "HERMES_MODEL",               ""),
        "hermes_fallback_mode":       s("hermes_fallback_mode",       "HERMES_FALLBACK_MODE",       "hermes_manual"),
        "hermes_timeout_seconds":     _coerce_float(ov.get("hermes_timeout_seconds") if "hermes_timeout_seconds" in ov else os.getenv("HERMES_TIMEOUT_SECONDS"), 120.0),
        "hermes_retry_attempts":      _coerce_int(ov.get("hermes_retry_attempts") if "hermes_retry_attempts" in ov else os.getenv("HERMES_RETRY_ATTEMPTS"), 1),
        "hermes_retry_backoff_seconds": _coerce_float(ov.get("hermes_retry_backoff_seconds") if "hermes_retry_backoff_seconds" in ov else os.getenv("HERMES_RETRY_BACKOFF_SECONDS"), 2.0),
        "hermes_temperature":         temperature,
        "override_file_present":      PROVIDER_SETTINGS_PATH.exists(),
        "runtime_config_source":      "local_override" if PROVIDER_SETTINGS_PATH.exists() else "env",
    }
