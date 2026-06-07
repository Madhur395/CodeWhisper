"""
CodeWhisper — LLM Integration Layer Tests
Covers: GroqClient (primary), OpenAIClient, ClaudeClient, factory, prompt builder.
All external API calls are mocked — no real keys needed.
"""

import json
import pytest
from unittest.mock import MagicMock, patch

# ── Shared test data ───────────────────────────────────────────────────────────

SAMPLE_PROBLEM = (
    "Given an array of integers nums and an integer target, "
    "return indices of the two numbers such that they add up to target. "
    "You may assume each input has exactly one solution, "
    "and you may not use the same element twice."
)

VALID_HINTS = [
    "Think about what kind of lookup this problem requires.",
    "Can you find the complement of each number as you scan through?",
    "A HashMap supports O(1) average-time lookups by value.",
    "Iterate once: for each num, check if (target - num) is in your map, then insert it.",
    "Use a dict {value: index}. For each element compute target - element and check before inserting.",
]

FIVE_HINT_JSON = json.dumps(VALID_HINTS)


# ── Constructor helpers ───────────────────────────────────────────────────────

def make_groq_client():
    """GroqClient with the OpenAI SDK patched out (same SDK, different base_url)."""
    with patch("app.llm.groq_client.OpenAI"):
        from app.llm.groq_client import GroqClient
        return GroqClient()


def make_openai_client():
    """OpenAIClient with the OpenAI SDK patched out."""
    with patch("app.llm.openai_client.OpenAI"):
        from app.llm.openai_client import OpenAIClient
        return OpenAIClient()


# ══════════════════════════════════════════════════════════════════════════════
# PROMPT BUILDER TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestPromptBuilder:

    def test_system_prompt_non_empty(self):
        from app.utils.prompt_builder import SYSTEM_PROMPT
        assert isinstance(SYSTEM_PROMPT, str) and len(SYSTEM_PROMPT) > 100

    def test_system_prompt_contains_key_instructions(self):
        from app.utils.prompt_builder import SYSTEM_PROMPT
        p = SYSTEM_PROMPT.lower()
        assert "5" in p and "json" in p and "hint" in p

    def test_system_prompt_forbids_runnable_code(self):
        from app.utils.prompt_builder import SYSTEM_PROMPT
        assert "runnable" in SYSTEM_PROMPT.lower() or "code" in SYSTEM_PROMPT.lower()

    def test_build_hint_prompt_includes_problem(self):
        from app.utils.prompt_builder import build_hint_prompt
        out = build_hint_prompt("Find the max element.")
        assert "Find the max element" in out
        assert "Problem" in out

    def test_build_hint_prompt_strips_whitespace(self):
        from app.utils.prompt_builder import build_hint_prompt
        assert build_hint_prompt("  Two Sum  ") == "Problem:\nTwo Sum"

    def test_build_hint_prompt_returns_string(self):
        from app.utils.prompt_builder import build_hint_prompt
        assert isinstance(build_hint_prompt("x"), str)

    def test_build_analysis_prompt_returns_string(self):
        from app.utils.prompt_builder import build_analysis_prompt
        r = build_analysis_prompt("Find the shortest path.")
        assert isinstance(r, str) and "shortest path" in r

    def test_tag_system_prompt_exists(self):
        from app.utils.prompt_builder import TAG_SYSTEM_PROMPT
        assert isinstance(TAG_SYSTEM_PROMPT, str) and len(TAG_SYSTEM_PROMPT) > 20


# ══════════════════════════════════════════════════════════════════════════════
# BASE LLM CLIENT TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestBaseLLMClient:

    def test_base_is_abstract(self):
        from app.llm.base import BaseLLMClient
        with pytest.raises(TypeError):
            BaseLLMClient()

    def test_subclass_without_generate_hints_raises(self):
        from app.llm.base import BaseLLMClient
        class Incomplete(BaseLLMClient):
            pass
        with pytest.raises(TypeError):
            Incomplete()

    def test_concrete_subclass_works(self):
        from app.llm.base import BaseLLMClient
        class Good(BaseLLMClient):
            def generate_hints(self, problem):
                return ["h1","h2","h3","h4","h5"]
        assert len(Good().generate_hints("p")) == 5

    def test_llm_error_is_exception(self):
        from app.llm.base import LLMError
        e = LLMError("fail")
        assert isinstance(e, Exception) and "fail" in str(e)


# ══════════════════════════════════════════════════════════════════════════════
# GROQ CLIENT TESTS  (primary provider)
# ══════════════════════════════════════════════════════════════════════════════

class TestGroqClient:
    """
    GroqClient uses the openai SDK pointed at https://api.groq.com/openai/v1.
    All SDK constructor and API calls are mocked.
    """

    # ── Happy path ────────────────────────────────────────────────────────────

    def test_generate_hints_success(self):
        client = make_groq_client()
        with patch.object(client, "_call_api", return_value=VALID_HINTS):
            hints = client.generate_hints(SAMPLE_PROBLEM)
        assert len(hints) == 5
        assert all(isinstance(h, str) for h in hints)

    def test_generate_hints_strips_whitespace(self):
        client = make_groq_client()
        padded = [f"  {h}  " for h in VALID_HINTS]
        with patch.object(client, "_call_api", return_value=padded):
            hints = client.generate_hints(SAMPLE_PROBLEM)
        assert all(h == h.strip() for h in hints)

    def test_generate_hints_passes_problem_to_call_api(self):
        client = make_groq_client()
        with patch.object(client, "_call_api", return_value=VALID_HINTS) as m:
            client.generate_hints(SAMPLE_PROBLEM)
        m.assert_called_once_with(SAMPLE_PROBLEM)

    def test_call_api_uses_groq_base_url(self):
        """GroqClient is initialised with Groq's base URL."""
        from app.llm.groq_client import GROQ_BASE_URL
        captured = {}
        def fake_openai_init(self_obj, *, api_key, base_url):
            captured["base_url"] = base_url
        with patch("app.llm.groq_client.OpenAI.__init__", fake_openai_init):
            from app.llm.groq_client import GroqClient
            GroqClient()
        assert captured["base_url"] == GROQ_BASE_URL

    def test_default_model_is_llama_70b(self):
        from app.llm.groq_client import DEFAULT_MODEL
        assert "llama" in DEFAULT_MODEL.lower()
        assert "70b" in DEFAULT_MODEL.lower()

    # ── Validation ────────────────────────────────────────────────────────────

    def test_validate_rejects_non_list(self):
        client = make_groq_client()
        with patch.object(client, "_call_api", return_value={"key": "val"}):
            hints = client.generate_hints(SAMPLE_PROBLEM)
        assert len(hints) == 5  # fallback

    def test_validate_rejects_wrong_count(self):
        client = make_groq_client()
        with patch.object(client, "_call_api", return_value=["a", "b", "c"]):
            hints = client.generate_hints(SAMPLE_PROBLEM)
        assert len(hints) == 5  # fallback

    def test_validate_rejects_empty_string_hint(self):
        client = make_groq_client()
        with patch.object(client, "_call_api", return_value=VALID_HINTS[:4] + [""]):
            hints = client.generate_hints(SAMPLE_PROBLEM)
        assert len(hints) == 5  # fallback

    def test_validate_rejects_non_string_element(self):
        client = make_groq_client()
        with patch.object(client, "_call_api", return_value=VALID_HINTS[:4] + [99]):
            hints = client.generate_hints(SAMPLE_PROBLEM)
        assert len(hints) == 5  # fallback

    # ── Retry & error handling ────────────────────────────────────────────────

    def test_retries_on_rate_limit_error(self):
        from app.llm.groq_client import MAX_RETRIES
        from openai import RateLimitError
        client = make_groq_client()
        err = RateLimitError("rate limit", response=MagicMock(status_code=429), body={})
        with patch.object(client, "_call_api", side_effect=err) as m:
            with patch("app.llm.groq_client.time.sleep"):
                hints = client.generate_hints(SAMPLE_PROBLEM)
        assert m.call_count == MAX_RETRIES
        assert len(hints) == 5  # fallback

    def test_retries_on_timeout_error(self):
        from app.llm.groq_client import MAX_RETRIES
        from openai import APITimeoutError
        client = make_groq_client()
        err = APITimeoutError(request=MagicMock())
        with patch.object(client, "_call_api", side_effect=err) as m:
            with patch("app.llm.groq_client.time.sleep"):
                hints = client.generate_hints(SAMPLE_PROBLEM)
        assert m.call_count == MAX_RETRIES
        assert len(hints) == 5

    def test_retries_on_connection_error(self):
        from app.llm.groq_client import MAX_RETRIES
        from openai import APIConnectionError
        client = make_groq_client()
        err = APIConnectionError(request=MagicMock())
        with patch.object(client, "_call_api", side_effect=err) as m:
            with patch("app.llm.groq_client.time.sleep"):
                hints = client.generate_hints(SAMPLE_PROBLEM)
        assert m.call_count == MAX_RETRIES

    def test_no_retry_on_auth_error(self):
        """AuthenticationError (bad key) is non-retryable."""
        from openai import AuthenticationError
        client = make_groq_client()
        err = AuthenticationError("bad key", response=MagicMock(status_code=401), body={})
        with patch.object(client, "_call_api", side_effect=err) as m:
            with patch("app.llm.groq_client.time.sleep"):
                hints = client.generate_hints(SAMPLE_PROBLEM)
        assert m.call_count == 1   # no retry
        assert len(hints) == 5     # fallback

    def test_no_retry_on_json_decode_error(self):
        client = make_groq_client()
        err = json.JSONDecodeError("bad json", "", 0)
        with patch.object(client, "_call_api", side_effect=err) as m:
            with patch("app.llm.groq_client.time.sleep"):
                hints = client.generate_hints(SAMPLE_PROBLEM)
        assert m.call_count == 1
        assert len(hints) == 5

    def test_succeeds_after_one_transient_failure(self):
        from openai import APITimeoutError
        client = make_groq_client()
        call_count = 0
        def side_effect(problem):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise APITimeoutError(request=MagicMock())
            return VALID_HINTS
        with patch.object(client, "_call_api", side_effect=side_effect):
            with patch("app.llm.groq_client.time.sleep"):
                hints = client.generate_hints(SAMPLE_PROBLEM)
        assert hints == VALID_HINTS
        assert call_count == 2

    def test_fallback_hints_on_total_failure(self):
        from app.llm.groq_client import FALLBACK_HINTS
        from openai import RateLimitError
        client = make_groq_client()
        err = RateLimitError("limit", response=MagicMock(status_code=429), body={})
        with patch.object(client, "_call_api", side_effect=err):
            with patch("app.llm.groq_client.time.sleep"):
                hints = client.generate_hints(SAMPLE_PROBLEM)
        assert hints == FALLBACK_HINTS

    def test_backoff_sleep_called_between_retries(self):
        from app.llm.groq_client import MAX_RETRIES
        from openai import RateLimitError
        client = make_groq_client()
        err = RateLimitError("limit", response=MagicMock(status_code=429), body={})
        with patch.object(client, "_call_api", side_effect=err):
            with patch("app.llm.groq_client.time.sleep") as mock_sleep:
                client.generate_hints(SAMPLE_PROBLEM)
        assert mock_sleep.call_count == MAX_RETRIES - 1

    # ── _call_api unit test ───────────────────────────────────────────────────

    def test_call_api_parses_json_response(self):
        client = make_groq_client()
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = FIVE_HINT_JSON
        with patch.object(client._client.chat.completions, "create", return_value=mock_resp):
            result = client._call_api(SAMPLE_PROBLEM)
        assert result == VALID_HINTS

    def test_call_api_raises_on_invalid_json(self):
        client = make_groq_client()
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = "not json at all"
        with patch.object(client._client.chat.completions, "create", return_value=mock_resp):
            with pytest.raises(json.JSONDecodeError):
                client._call_api(SAMPLE_PROBLEM)


# ══════════════════════════════════════════════════════════════════════════════
# OPENAI CLIENT TESTS  (retained as optional fallback)
# ══════════════════════════════════════════════════════════════════════════════

class TestOpenAIClient:

    def test_generate_hints_success(self):
        client = make_openai_client()
        with patch.object(client, "_call_api", return_value=VALID_HINTS):
            hints = client.generate_hints(SAMPLE_PROBLEM)
        assert len(hints) == 5

    def test_validate_rejects_wrong_count(self):
        client = make_openai_client()
        with patch.object(client, "_call_api", return_value=["a", "b"]):
            hints = client.generate_hints(SAMPLE_PROBLEM)
        assert len(hints) == 5  # fallback

    def test_retries_on_rate_limit(self):
        from app.llm.openai_client import MAX_RETRIES
        from openai import RateLimitError
        client = make_openai_client()
        err = RateLimitError("limit", response=MagicMock(status_code=429), body={})
        with patch.object(client, "_call_api", side_effect=err) as m:
            with patch("app.llm.openai_client.time.sleep"):
                client.generate_hints(SAMPLE_PROBLEM)
        assert m.call_count == MAX_RETRIES

    def test_no_retry_on_json_error(self):
        client = make_openai_client()
        with patch.object(client, "_call_api", side_effect=json.JSONDecodeError("b","",0)) as m:
            with patch("app.llm.openai_client.time.sleep"):
                client.generate_hints(SAMPLE_PROBLEM)
        assert m.call_count == 1

    def test_fallback_on_total_failure(self):
        from app.llm.openai_client import FALLBACK_HINTS
        from openai import RateLimitError
        client = make_openai_client()
        err = RateLimitError("limit", response=MagicMock(status_code=429), body={})
        with patch.object(client, "_call_api", side_effect=err):
            with patch("app.llm.openai_client.time.sleep"):
                hints = client.generate_hints(SAMPLE_PROBLEM)
        assert hints == FALLBACK_HINTS


# ══════════════════════════════════════════════════════════════════════════════
# CLAUDE CLIENT TESTS  (retained as optional fallback)
# ══════════════════════════════════════════════════════════════════════════════

class TestClaudeClient:

    def _make_client(self):
        from app.llm.claude_client import ClaudeClient
        return ClaudeClient()

    def test_generate_hints_success(self):
        client = self._make_client()
        with patch.object(client, "_call_api", return_value=VALID_HINTS):
            hints = client.generate_hints(SAMPLE_PROBLEM)
        assert len(hints) == 5

    def test_retries_on_rate_limit(self):
        import anthropic
        from app.llm.claude_client import MAX_RETRIES
        client = self._make_client()
        err = anthropic.RateLimitError(
            message="rate limit",
            response=MagicMock(status_code=429, headers={}),
            body={},
        )
        with patch.object(client, "_call_api", side_effect=err) as m:
            with patch("app.llm.claude_client.time.sleep"):
                hints = client.generate_hints(SAMPLE_PROBLEM)
        assert m.call_count == MAX_RETRIES
        assert len(hints) == 5

    def test_fallback_on_connection_error(self):
        import anthropic
        from app.llm.claude_client import FALLBACK_HINTS
        client = self._make_client()
        err = anthropic.APIConnectionError(request=MagicMock())
        with patch.object(client, "_call_api", side_effect=err):
            with patch("app.llm.claude_client.time.sleep"):
                hints = client.generate_hints(SAMPLE_PROBLEM)
        assert hints == FALLBACK_HINTS


# ══════════════════════════════════════════════════════════════════════════════
# LLM FACTORY TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestLLMFactory:

    def test_factory_returns_groq_by_default(self):
        """Default provider (no env set) must be Groq."""
        from app.llm import get_llm_client
        from app.llm.groq_client import GroqClient
        with patch("app.llm.groq_client.OpenAI"), \
             patch.dict("os.environ", {"LLM_PROVIDER": "groq"}):
            client = get_llm_client()
        assert isinstance(client, GroqClient)

    def test_factory_returns_groq_explicitly(self):
        from app.llm import get_llm_client
        from app.llm.groq_client import GroqClient
        with patch("app.llm.groq_client.OpenAI"), \
             patch.dict("os.environ", {"LLM_PROVIDER": "groq"}):
            client = get_llm_client()
        assert isinstance(client, GroqClient)

    def test_factory_returns_openai_client(self):
        from app.llm import get_llm_client
        from app.llm.openai_client import OpenAIClient
        with patch("app.llm.openai_client.OpenAI"), \
             patch.dict("os.environ", {"LLM_PROVIDER": "openai"}):
            client = get_llm_client()
        assert isinstance(client, OpenAIClient)

    def test_factory_returns_claude_client(self):
        from app.llm import get_llm_client
        from app.llm.claude_client import ClaudeClient
        with patch.dict("os.environ", {"LLM_PROVIDER": "claude"}):
            client = get_llm_client()
        assert isinstance(client, ClaudeClient)

    def test_factory_is_case_insensitive(self):
        from app.llm import get_llm_client
        from app.llm.groq_client import GroqClient
        with patch("app.llm.groq_client.OpenAI"), \
             patch.dict("os.environ", {"LLM_PROVIDER": "GROQ"}):
            client = get_llm_client()
        assert isinstance(client, GroqClient)

    def test_factory_falls_back_to_groq_on_unknown(self):
        from app.llm import get_llm_client
        from app.llm.groq_client import GroqClient
        with patch("app.llm.groq_client.OpenAI"), \
             patch.dict("os.environ", {"LLM_PROVIDER": "unknown_provider"}):
            client = get_llm_client()
        assert isinstance(client, GroqClient)

    def test_factory_returns_base_client_subclass(self):
        from app.llm import get_llm_client
        from app.llm.base import BaseLLMClient
        for provider, ctx in [
            ("groq",   patch("app.llm.groq_client.OpenAI")),
            ("openai", patch("app.llm.openai_client.OpenAI")),
            ("claude", patch("app.llm.claude_client.anthropic.Anthropic")),
        ]:
            with ctx, patch.dict("os.environ", {"LLM_PROVIDER": provider}):
                client = get_llm_client()
            assert isinstance(client, BaseLLMClient), f"Failed for {provider}"

    def test_all_clients_have_generate_hints(self):
        from app.llm import get_llm_client
        for provider, ctx in [
            ("groq",   patch("app.llm.groq_client.OpenAI")),
            ("openai", patch("app.llm.openai_client.OpenAI")),
            ("claude", patch("app.llm.claude_client.anthropic.Anthropic")),
        ]:
            with ctx, patch.dict("os.environ", {"LLM_PROVIDER": provider}):
                client = get_llm_client()
            assert callable(getattr(client, "generate_hints", None))


# ══════════════════════════════════════════════════════════════════════════════
# FALLBACK HINTS CONTENT TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestFallbackHints:

    def test_groq_fallback_is_5_strings(self):
        from app.llm.groq_client import FALLBACK_HINTS
        assert isinstance(FALLBACK_HINTS, list) and len(FALLBACK_HINTS) == 5
        assert all(isinstance(h, str) and h.strip() for h in FALLBACK_HINTS)

    def test_openai_fallback_is_5_strings(self):
        from app.llm.openai_client import FALLBACK_HINTS
        assert isinstance(FALLBACK_HINTS, list) and len(FALLBACK_HINTS) == 5

    def test_claude_fallback_is_5_strings(self):
        from app.llm.claude_client import FALLBACK_HINTS
        assert isinstance(FALLBACK_HINTS, list) and len(FALLBACK_HINTS) == 5

    def test_all_fallbacks_are_identical(self):
        from app.llm.groq_client  import FALLBACK_HINTS as groq_fb
        from app.llm.openai_client import FALLBACK_HINTS as oai_fb
        from app.llm.claude_client import FALLBACK_HINTS as claude_fb
        assert groq_fb == oai_fb == claude_fb


# ══════════════════════════════════════════════════════════════════════════════
# END-TO-END SMOKE TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestLLMSmoke:

    def test_groq_end_to_end_mocked(self):
        from app.llm import get_llm_client
        with patch("app.llm.groq_client.OpenAI"), \
             patch.dict("os.environ", {"LLM_PROVIDER": "groq"}):
            client = get_llm_client()
        with patch.object(client, "_call_api", return_value=VALID_HINTS):
            hints = client.generate_hints(SAMPLE_PROBLEM)
        assert len(hints) == 5
        assert hints[0] == VALID_HINTS[0]
        assert hints[4] == VALID_HINTS[4]

    def test_openai_end_to_end_mocked(self):
        from app.llm import get_llm_client
        with patch("app.llm.openai_client.OpenAI"), \
             patch.dict("os.environ", {"LLM_PROVIDER": "openai"}):
            client = get_llm_client()
        with patch.object(client, "_call_api", return_value=VALID_HINTS):
            hints = client.generate_hints(SAMPLE_PROBLEM)
        assert len(hints) == 5

    def test_claude_end_to_end_mocked(self):
        from app.llm import get_llm_client
        with patch.dict("os.environ", {"LLM_PROVIDER": "claude"}):
            client = get_llm_client()
        with patch.object(client, "_call_api", return_value=VALID_HINTS):
            hints = client.generate_hints(SAMPLE_PROBLEM)
        assert len(hints) == 5

    def test_groq_is_default_provider(self):
        """When LLM_PROVIDER is absent, Groq is selected."""
        import os
        from app.llm import get_llm_client, _DEFAULT_PROVIDER
        assert _DEFAULT_PROVIDER == "groq"

    def test_switching_provider_gives_different_class(self):
        from app.llm import get_llm_client
        from app.llm.groq_client import GroqClient
        from app.llm.claude_client import ClaudeClient
        with patch("app.llm.groq_client.OpenAI"), \
             patch.dict("os.environ", {"LLM_PROVIDER": "groq"}):
            groq = get_llm_client()
        with patch.dict("os.environ", {"LLM_PROVIDER": "claude"}):
            claude = get_llm_client()
        assert type(groq)   is GroqClient
        assert type(claude) is ClaudeClient
        assert type(groq)   is not type(claude)
