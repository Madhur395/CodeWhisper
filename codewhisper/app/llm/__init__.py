"""
CodeWhisper — LLM Client Factory
Returns the correct LLM client based on the LLM_PROVIDER environment variable.

Supported providers
-------------------
  groq   — Groq LPU inference (default) — ultra-fast, free tier available
  openai — OpenAI GPT-4o
  claude — Anthropic Claude 3.5 Sonnet

Usage
-----
    from app.llm import get_llm_client
    client = get_llm_client()
    hints  = client.generate_hints(problem_text)
"""

import importlib
import logging
import os

from app.llm.base import BaseLLMClient

logger = logging.getLogger(__name__)

# Registry: provider name → dotted class path (lazy-imported)
_PROVIDER_MAP: dict[str, str] = {
    "groq":   "app.llm.groq_client.GroqClient",
    "openai": "app.llm.openai_client.OpenAIClient",
    "claude": "app.llm.claude_client.ClaudeClient",
}

# Default provider when LLM_PROVIDER is unset
_DEFAULT_PROVIDER = "groq"


def get_llm_client() -> BaseLLMClient:
    """
    Instantiate and return the LLM client for the configured provider.

    Reads LLM_PROVIDER from the environment (default: "groq").
    Performs a case-insensitive lookup; falls back to Groq on unknown values.

    Returns:
        BaseLLMClient: A ready-to-use client instance.
    """
    provider = os.getenv("LLM_PROVIDER", _DEFAULT_PROVIDER).strip().lower()

    if provider not in _PROVIDER_MAP:
        logger.warning(
            "Unknown LLM_PROVIDER=%r — falling back to %r. "
            "Supported providers: %s",
            provider, _DEFAULT_PROVIDER, list(_PROVIDER_MAP),
        )
        provider = _DEFAULT_PROVIDER

    # Lazy import — avoids loading unused SDKs at startup
    module_path, class_name = _PROVIDER_MAP[provider].rsplit(".", 1)
    module = importlib.import_module(module_path)
    client_class: type[BaseLLMClient] = getattr(module, class_name)

    logger.debug("LLM client: provider=%s  class=%s", provider, class_name)
    return client_class()
