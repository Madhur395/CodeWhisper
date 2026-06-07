"""
CodeWhisper — Groq LLM Client
Primary LLM backend powered by Groq's ultra-fast LPU inference.

Groq exposes an OpenAI-compatible Chat Completions API, so the standard
`openai` Python SDK is used — just pointed at Groq's base URL.

API docs : https://console.groq.com/docs
Models   : https://console.groq.com/docs/models
Key prefix: gsk_...

Reads:
    GROQ_API_KEY   — Required. Get one free at console.groq.com/keys
    GROQ_MODEL     — Optional. Default: llama-3.3-70b-versatile
"""

import json
import logging
import os
import time

from openai import (
    OpenAI,
    APIError,
    APITimeoutError,
    RateLimitError,
    APIConnectionError,
    AuthenticationError,
)

from app.llm.base import BaseLLMClient, LLMError
from app.utils.prompt_builder import SYSTEM_PROMPT, build_hint_prompt

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

GROQ_BASE_URL   = "https://api.groq.com/openai/v1"

# Best general-purpose model on Groq as of mid-2025 (128K context, very fast)
DEFAULT_MODEL   = "llama-3.3-70b-versatile"

MAX_TOKENS      = 1500
TEMPERATURE     = 0.7
MAX_RETRIES     = 3
INITIAL_BACKOFF = 1.0   # seconds — doubles on each retry
MAX_BACKOFF     = 16.0  # seconds — cap

# Generic fallback hints returned when all API attempts fail
FALLBACK_HINTS = [
    "Think carefully about the problem constraints and what they imply "
    "about the expected time complexity.",
    "Consider what information you need to track as you iterate through "
    "the input. What data structure lets you query that information efficiently?",
    "Break the problem into smaller sub-problems. "
    "Can you solve a simpler version first and build up?",
    "Think about the relationship between elements. "
    "Is there a sorted order or a two-pointer / sliding-window pattern that might help?",
    "Try working through a small example by hand. "
    "Map each step to an algorithm — what pattern emerges?",
]


class GroqClient(BaseLLMClient):
    """
    LLM client that calls Groq's OpenAI-compatible Chat Completions API
    to generate 5 progressive Socratic-style DSA hints at lightning speed.

    Groq's LPU (Language Processing Unit) hardware delivers 200–315 tokens/s,
    making it ideal for real-time hint generation without perceptible lag.

    Features
    --------
    - Uses the standard `openai` SDK (no extra package required)
    - Exponential backoff retry — up to MAX_RETRIES attempts
    - Retryable: RateLimitError, APITimeoutError, APIConnectionError
    - Non-retryable: AuthenticationError, APIError, JSONDecodeError, ValueError
    - JSON response validation: ensures exactly 5 non-empty hint strings
    - Returns FALLBACK_HINTS if all retries are exhausted (never raises)
    """

    def __init__(self) -> None:
        api_key = os.getenv("GROQ_API_KEY", "")
        if not api_key or api_key.startswith("gsk_REPLACE"):
            logger.warning(
                "GROQ_API_KEY is not set or is a placeholder. "
                "Set it in .env to enable Groq hint generation."
            )

        self._api_key = api_key or "gsk_placeholder"
        self._client = None  # lazy — avoids crashing callers when SDK/env misconfigured
        self.model = os.getenv("GROQ_MODEL", DEFAULT_MODEL)
        logger.debug("GroqClient initialised — model=%s", self.model)

    def _get_client(self) -> OpenAI:
        if self._client is None:
            self._client = OpenAI(
                api_key=self._api_key,
                base_url=GROQ_BASE_URL,
            )
        return self._client

    # ── Public interface ──────────────────────────────────────────────────────

    def generate_hints(self, problem: str) -> list[str]:
        """
        Call Groq with a Socratic system prompt and return 5 progressive hints.

        Retries up to MAX_RETRIES times with exponential backoff on transient
        errors (rate limits, timeouts, connection issues).
        Returns FALLBACK_HINTS if all attempts fail — never raises to the caller.

        Args:
            problem (str): Raw DSA / coding problem statement.

        Returns:
            list[str]: Exactly 5 Socratic hint strings.
        """
        last_error: Exception | None = None
        backoff = INITIAL_BACKOFF

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logger.debug(
                    "Groq attempt %d/%d  model=%s", attempt, MAX_RETRIES, self.model
                )
                hints = self._call_api(problem)
                hints = self._validate_hints(hints)
                logger.info("Groq generated hints successfully on attempt %d", attempt)
                return hints

            except TypeError as exc:
                # e.g. openai/httpx version mismatch during client init
                last_error = exc
                logger.warning("Groq client init error: %s", exc)
                break

            except (RateLimitError, APITimeoutError, APIConnectionError) as exc:
                # Transient — worth retrying with backoff
                last_error = exc
                wait = min(backoff, MAX_BACKOFF)
                logger.warning(
                    "Groq transient error (attempt %d/%d): %s — retrying in %.1fs",
                    attempt, MAX_RETRIES, exc, wait,
                )
                if attempt < MAX_RETRIES:
                    time.sleep(wait)
                    backoff *= 2

            except (AuthenticationError, APIError, json.JSONDecodeError, ValueError) as exc:
                # Non-retryable (bad key, malformed JSON, wrong schema)
                last_error = exc
                logger.warning(
                    "Groq non-retryable error (attempt %d/%d): %s",
                    attempt, MAX_RETRIES, exc,
                )
                break

        logger.error(
            "Groq failed after %d attempt(s): %s — returning fallback hints",
            MAX_RETRIES, last_error,
        )
        return FALLBACK_HINTS

    # ── Private helpers ───────────────────────────────────────────────────────

    def _call_api(self, problem: str) -> list[str]:
        """
        Make one Chat Completions call to Groq and return the parsed JSON list.

        Raises:
            json.JSONDecodeError: If the response is not valid JSON.
            openai.*: Any SDK exception propagates to generate_hints() for handling.
        """
        response = self._get_client().chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": build_hint_prompt(problem)},
            ],
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
        )
        raw = response.choices[0].message.content.strip()
        return json.loads(raw)

    def _validate_hints(self, parsed: object) -> list[str]:
        """
        Ensure the LLM response is a list of exactly 5 non-empty strings.

        Args:
            parsed: The Python object decoded from the JSON response.

        Returns:
            list[str]: Cleaned (stripped) list of 5 hint strings.

        Raises:
            ValueError: If the structure does not match expectations.
        """
        if not isinstance(parsed, list):
            raise ValueError(
                f"Expected a JSON array, got {type(parsed).__name__!r}"
            )
        if len(parsed) < 3:
            raise ValueError(
                f"Expected at least 3 hints, got {len(parsed)}"
            )
        cleaned = [h.strip() for h in parsed if isinstance(h, str) and h.strip()]
        if len(cleaned) < 3:
            raise ValueError("Too few valid hint strings in LLM response")
        while len(cleaned) < 5:
            cleaned.append(FALLBACK_HINTS[len(cleaned) % len(FALLBACK_HINTS)])
        return cleaned[:5]
