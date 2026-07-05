"""
Provider-agnostic LLM factory (Layer 3 - LLM reasoning core).

The orchestration layer (LangGraph) only ever calls ``get_chat_model()``.
Which concrete provider/model is used is controlled entirely by environment
variables (see app/config.py and .env.example):

    LLM_PROVIDER = ollama | openai | anthropic
    LLM_MODEL     = <provider-specific model name>
    LLM_TEMPERATURE = 0.0 - 1.0

PRIMARY / REQUIRED: "ollama" is the default provider and is what standard
execution, Docker, and the evaluation suite run against. It is fully
offline/local (``OLLAMA_BASE_URL``, no API key) and requires no external
service.

OPTIONAL FALLBACK: "openai" and "anthropic" are only used if the project is
explicitly configured to do so (``LLM_PROVIDER=openai`` /
``LLM_PROVIDER=anthropic`` *and* the matching ``*_API_KEY`` set). There is
NO automatic/silent fallback between providers - exactly one provider is
selected by ``LLM_PROVIDER`` and used for the whole process; if that
provider is misconfigured, ``get_chat_model()`` raises
``LLMConfigurationError`` rather than silently switching to another
provider.

This keeps the agent reasoning core swappable without touching the
workflow, tools, or UI - satisfying the "make the model configurable
through environment variables" requirement.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from .. import config


class LLMConfigurationError(RuntimeError):
    """Raised when the configured LLM provider is missing required setup."""


@lru_cache(maxsize=1)
def get_chat_model(**overrides: Any):
    """
    Return a LangChain-compatible chat model instance for the configured
    provider. Cached so the same model/client is reused across a process.

    Supported providers: "ollama" (default/required), "openai" (optional
    fallback), "anthropic" (optional fallback). Exactly one provider is used
    per process - there is no silent fallback chain between providers.
    """
    provider = overrides.get("provider", config.LLM_PROVIDER)
    model = overrides.get("model", config.LLM_MODEL)
    temperature = overrides.get("temperature", config.LLM_TEMPERATURE)

    # --- PRIMARY (default, required): local/offline Ollama -----------------
    if provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=model,
            temperature=temperature,
            base_url=config.OLLAMA_BASE_URL,
        )

    # --- OPTIONAL FALLBACK: OpenAI (only if explicitly selected) ------------
    if provider == "openai":
        if not config.OPENAI_API_KEY:
            raise LLMConfigurationError(
                "LLM_PROVIDER=openai but OPENAI_API_KEY is not set. "
                "OpenAI is an optional fallback provider - either set "
                "OPENAI_API_KEY in your .env file, or switch LLM_PROVIDER "
                "back to 'ollama' (the default, no API key required)."
            )
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=model,
            temperature=temperature,
            api_key=config.OPENAI_API_KEY,
        )

    # --- OPTIONAL FALLBACK: Anthropic (only if explicitly selected) ---------
    if provider == "anthropic":
        if not config.ANTHROPIC_API_KEY:
            raise LLMConfigurationError(
                "LLM_PROVIDER=anthropic but ANTHROPIC_API_KEY is not set. "
                "Anthropic is an optional fallback provider - either set "
                "ANTHROPIC_API_KEY in your .env file, or switch LLM_PROVIDER "
                "back to 'ollama' (the default, no API key required)."
            )
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=model,
            temperature=temperature,
            api_key=config.ANTHROPIC_API_KEY,
        )

    raise LLMConfigurationError(
        f"Unknown LLM_PROVIDER '{provider}'. Expected one of: ollama (default), openai, anthropic."
    )
