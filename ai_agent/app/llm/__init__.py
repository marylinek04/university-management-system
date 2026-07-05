"""LLM reasoning core (Layer 3) - provider-agnostic chat model factory."""

from .client import get_chat_model

__all__ = ["get_chat_model"]
