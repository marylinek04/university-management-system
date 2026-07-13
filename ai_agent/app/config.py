"""
Central configuration for the University Operations AI Agent.

All values are read from environment variables (with sensible defaults) so
that the LLM provider/model, database path, and safety limits can be changed
without touching code - this is what the project proposal calls a
"configurable through environment variables" Layer 3.

See .env.example for the full list of supported variables.
"""

from __future__ import annotations

import os
from pathlib import Path

try:  # optional convenience for local (non-Docker) runs
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover - python-dotenv is in requirements.txt
    pass


def _env_bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    val = os.getenv(name)
    if val is None or val.strip() == "":
        return default
    try:
        return int(val)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    val = os.getenv(name)
    if val is None or val.strip() == "":
        return default
    try:
        return float(val)
    except ValueError:
        return default


def _env_str(name: str, default: str) -> str:
    """Like os.getenv, but treats a BLANK value as unset.

    .env.example ships several intentionally-blank lines (e.g. ``LLM_MODEL=``
    meaning "use the per-provider default"). ``os.getenv(name, default)``
    would return that empty string instead of the default, which previously
    caused ChatOllama to be constructed with ``model=""`` and fail with
    "model must be specified".
    """
    val = os.getenv(name)
    if val is None or val.strip() == "":
        return default
    return val.strip()


# ---------------------------------------------------------------------------
# LLM provider configuration (Layer 3)
# ---------------------------------------------------------------------------
# One of: "ollama" (default, required - offline/local, no API key),
# "openai" (optional fallback), "anthropic" (optional fallback).
# Ollama is the standard execution path for development, testing, and
# evaluation. OpenAI/Anthropic are only used if explicitly selected here
# AND the matching *_API_KEY is set - they are never required.
LLM_PROVIDER = _env_str("LLM_PROVIDER", "ollama").lower()

# Default models per provider; overridable via LLM_MODEL
_DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-3-5-haiku-20241022",
    "ollama": "llama3.1",
}
# Blank/unset LLM_MODEL means "use the per-provider default" (see .env.example).
LLM_MODEL = _env_str("LLM_MODEL", _DEFAULT_MODELS.get(LLM_PROVIDER, "llama3.1"))

LLM_TEMPERATURE = _env_float("LLM_TEMPERATURE", 0.1)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OLLAMA_BASE_URL = _env_str("OLLAMA_BASE_URL", "http://localhost:11434")

# ---------------------------------------------------------------------------
# Database (Layer 6 - data layer)
# ---------------------------------------------------------------------------
APP_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = APP_DIR / "db" / "university.db"
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", str(DEFAULT_DB_PATH)))

# ---------------------------------------------------------------------------
# Workflow / safety controls (Layer 2 - orchestration)
# ---------------------------------------------------------------------------
# Maximum number of agent loop iterations (LLM calls / tool calls) per turn
# before the workflow forces a fallback response. Prevents infinite loops.
MAX_ITERATIONS = _env_int("MAX_ITERATIONS", 6)

# Tools that mutate data and therefore require explicit user confirmation
CONFIRMATION_REQUIRED_TOOLS = {"create_enrollment_request"}

# Minimum confidence (0-1) the intent router must have before acting on a
# classified intent. Below this, the workflow falls back to a clarification
# or "unsupported request" response.
INTENT_CONFIDENCE_THRESHOLD = _env_float("INTENT_CONFIDENCE_THRESHOLD", 0.4)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_LEVEL = _env_str("LOG_LEVEL", "INFO").upper()

# ---------------------------------------------------------------------------
# Long-term memory (bonus)
# ---------------------------------------------------------------------------
ENABLE_LONG_TERM_MEMORY = _env_bool("ENABLE_LONG_TERM_MEMORY", True)
