"""
CodeWhisper — Groq LLM Client
Falls back to generic hints if API key is missing or calls fail.
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

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
DEFAULT_MODEL  = "llama-3.3-70b-versatile"
MAX_TOKENS     = 1500
TEMPERATURE    = 0.7
MAX_RETRIES    = 3
INITIAL_BACKOFF = 1.0
MAX_BACKOFF    = 16.0

FALLBACK_HINTS = [
    "Think carefully about the problem constraints and what they imply about the expected time complexity.",
    "Consider what information you need to track as you iterate through the input. What data structure lets you query that information efficiently?",
    "Break the problem into smaller sub-problems. Can you solve a simpler version first and build up?",
    "Think about the relationship between elements. Is there a sorted order or a two-pointer / sliding-window pattern that might help?",
    "Try working through a small example by hand. Map each step to an algorithm — what pattern emerges?",
]


class GroqClient(BaseLLMClient):

    def __init__(self) -> None:
        self._api_key = os.getenv("GROQ_API_KEY", "").strip()
        self._key_valid = bool(self._api_key and not self._api_key.startswith("gsk_REPLACE"))
        
        if not self._key_valid:
            logger.warning("GROQ_API_KEY not set — will use fallback hints. "
                           "Get a free key at https://console.groq.com/keys")
            # Still create client so code doesn't crash at import time
            self._client = OpenAI(
                api_key="gsk_placeholder",
                base_url=GROQ_BASE_URL,
            )
        else:
            self._client = OpenAI(
                api_key=self._api_key,
                base_url=GROQ_BASE_URL,
            )
        
        self.model = os.getenv("GROQ_MODEL", DEFAULT_MODEL)
        logger.debug("GroqClient ready — key_valid=%s model=%s", self._key_valid, self.model)

    def generate_hints(self, problem: str) -> list[str]:
        # If no valid key, return fallback immediately — no API call
        if not self._key_valid:
            logger.info("No Groq key — returning fallback hints")
            return FALLBACK_HINTS

        last_error = None
        backoff = INITIAL_BACKOFF

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logger.debug("Groq attempt %d/%d", attempt, MAX_RETRIES)
                hints = self._call_api(problem)
                hints = self._validate_hints(hints)
                logger.info("Groq hints generated OK on attempt %d", attempt)
                return hints

            except (RateLimitError, APITimeoutError, APIConnectionError) as exc:
                last_error = exc
                wait = min(backoff, MAX_BACKOFF)
                logger.warning("Groq transient error attempt %d: %s — retry in %.1fs", attempt, exc, wait)
                if attempt < MAX_RETRIES:
                    time.sleep(wait)
                    backoff *= 2

            except (AuthenticationError, APIError, json.JSONDecodeError, ValueError) as exc:
                last_error = exc
                logger.warning("Groq non-retryable error: %s", exc)
                break

        logger.error("Groq failed after %d attempts: %s — using fallback hints", MAX_RETRIES, last_error)
        return FALLBACK_HINTS

    def _call_api(self, problem: str) -> list[str]:
        response = self._client.chat.completions.create(
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
        if not isinstance(parsed, list):
            raise ValueError(f"Expected JSON list, got {type(parsed).__name__}")
        if len(parsed) != 5:
            raise ValueError(f"Expected 5 hints, got {len(parsed)}")
        for i, h in enumerate(parsed, 1):
            if not isinstance(h, str) or not h.strip():
                raise ValueError(f"Hint {i} is not a non-empty string")
        return [h.strip() for h in parsed]
