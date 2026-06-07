"""
CodeWhisper — Anthropic Claude Client
Phase 4: Full implementation with retry logic, exponential backoff, and fallback.

Uses the anthropic Python SDK (v0.x / v1.x).
Reads ANTHROPIC_API_KEY and optional CLAUDE_MODEL from environment.
"""

import json
import logging
import os
import time

import anthropic
from anthropic import (
    APIError,
    APITimeoutError,
    RateLimitError,
    APIConnectionError,
    APIStatusError,
)

from app.llm.base import BaseLLMClient, LLMError
from app.utils.prompt_builder import SYSTEM_PROMPT, build_hint_prompt

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────
DEFAULT_MODEL   = "claude-3-5-sonnet-20241022"
MAX_TOKENS      = 1500
MAX_RETRIES     = 3
INITIAL_BACKOFF = 1.0    # seconds
MAX_BACKOFF     = 16.0   # seconds

FALLBACK_HINTS = [
    "Think carefully about the problem constraints and what they imply about the expected time complexity.",
    "Consider what information you need to track as you iterate through the input. What data structure lets you query that information efficiently?",
    "Break the problem into smaller sub-problems. Can you solve a simpler version first and build up?",
    "Think about the relationship between elements. Is there a sorted order or a two-pointer / sliding-window pattern that might help?",
    "Try working through a small example by hand. Map each step to an algorithm — what pattern emerges?",
]


class ClaudeClient(BaseLLMClient):
    """
    LLM client that calls the Anthropic Claude Messages API to generate
    5 progressive Socratic-style DSA hints.

    Features:
        - Exponential backoff retry (up to MAX_RETRIES attempts)
        - Handles: APIError, RateLimitError, APITimeoutError, APIConnectionError
        - JSON parse validation: ensures exactly 5 string hints
        - Falls back to generic hints if all retries are exhausted
    """

    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            logger.warning("ANTHROPIC_API_KEY is not set. Claude calls will fail.")
        self._client = anthropic.Anthropic(api_key=api_key)
        self.model = os.getenv("CLAUDE_MODEL", DEFAULT_MODEL)

    # ── Public interface ──────────────────────────────────────────────────────

    def generate_hints(self, problem: str) -> list[str]:
        """
        Call Anthropic Claude with a Socratic system prompt and return 5 hints.

        Retries up to MAX_RETRIES times with exponential backoff on transient errors.
        Returns FALLBACK_HINTS if all attempts fail.

        Args:
            problem (str): Raw DSA problem statement.

        Returns:
            list[str]: 5 hint strings.
        """
        last_error: Exception | None = None
        backoff = INITIAL_BACKOFF

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logger.debug("Claude attempt %d/%d for model=%s", attempt, MAX_RETRIES, self.model)
                hints = self._call_api(problem)
                hints = self._validate_hints(hints)
                logger.info("Claude generated hints successfully on attempt %d", attempt)
                return hints

            except (RateLimitError, APITimeoutError, APIConnectionError) as e:
                last_error = e
                wait = min(backoff, MAX_BACKOFF)
                logger.warning(
                    "Claude transient error (attempt %d/%d): %s — retrying in %.1fs",
                    attempt, MAX_RETRIES, e, wait,
                )
                if attempt < MAX_RETRIES:
                    time.sleep(wait)
                    backoff *= 2

            except (APIStatusError, APIError, json.JSONDecodeError, ValueError) as e:
                last_error = e
                logger.warning(
                    "Claude non-retryable error (attempt %d/%d): %s",
                    attempt, MAX_RETRIES, e,
                )
                break

        logger.error("Claude failed after %d attempts: %s — using fallback hints", MAX_RETRIES, last_error)
        return FALLBACK_HINTS

    # ── Private helpers ───────────────────────────────────────────────────────

    def _call_api(self, problem: str) -> list[str]:
        """Make the actual API call and return parsed JSON."""
        response = self._client.messages.create(
            model=self.model,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": build_hint_prompt(problem)},
            ],
        )
        raw_content = response.content[0].text.strip()
        return json.loads(raw_content)

    def _validate_hints(self, parsed: object) -> list[str]:
        """
        Ensure the LLM response is a list of exactly 5 non-empty strings.

        Raises:
            ValueError: If the structure is wrong.
        """
        if not isinstance(parsed, list):
            raise ValueError(f"Expected a JSON list, got {type(parsed).__name__}")
        if len(parsed) != 5:
            raise ValueError(f"Expected exactly 5 hints, got {len(parsed)}")
        for i, hint in enumerate(parsed):
            if not isinstance(hint, str) or not hint.strip():
                raise ValueError(f"Hint {i+1} is not a non-empty string: {hint!r}")
        return [h.strip() for h in parsed]
