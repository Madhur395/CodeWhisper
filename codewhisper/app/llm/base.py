"""
CodeWhisper — Abstract LLM Client Base Class
Phase 4: Full implementation.

Defines the interface all LLM provider adapters must implement.
Uses the Adapter / Strategy pattern so the provider can be swapped
via a single environment variable (LLM_PROVIDER=openai|claude).
"""

from abc import ABC, abstractmethod


class BaseLLMClient(ABC):
    """
    Abstract base class for LLM provider clients.

    Any new LLM provider (OpenAI, Claude, Gemini, Mistral, …)
    must subclass this and implement generate_hints().

    The contract:
        - Input:  a raw DSA/coding problem string
        - Output: a Python list of exactly 5 progressive hint strings
        - Errors: raise LLMError on unrecoverable failure (after retries)
    """

    @abstractmethod
    def generate_hints(self, problem: str) -> list[str]:
        """
        Send the problem to the LLM and return 5 Socratic hints.

        Args:
            problem (str): Full coding/DSA problem statement.

        Returns:
            list[str]: Exactly 5 hint strings in ascending depth order.
                       Hint 1 is the vaguest nudge;
                       Hint 5 is a near-complete approach (no runnable code).

        Raises:
            LLMError: On API failure after all retry attempts are exhausted,
                      or when the response cannot be parsed as a 5-element list.
        """
        pass


class LLMError(Exception):
    """
    Raised when an LLM client cannot produce a valid hint list
    after all retry attempts have been exhausted.
    """
    pass
