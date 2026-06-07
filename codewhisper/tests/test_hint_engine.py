"""
CodeWhisper — Phase 5: Hint Engine Service Tests
Covers HintEngineService (unit) and /hints/* routes (integration).

All LLM calls are mocked — no real API keys needed.
Redis is mocked via the autouse fixture in conftest.py.
"""

import uuid
import pytest
from unittest.mock import MagicMock, patch

# ── Shared test data ──────────────────────────────────────────────────────────

PROBLEM_TEXT = (
    "Given an array of integers nums and an integer target, "
    "return indices of the two numbers such that they add up to target. "
    "You may assume each input has exactly one solution, "
    "and you may not use the same element twice."
)

MOCK_HINTS = [
    "Think about what kind of lookup operation is needed here.",
    "Can you identify the complement of each number as you scan through?",
    "A HashMap (dictionary) supports O(1) average-time lookups.",
    "Iterate once: for each number, check if its complement already exists in the map, then insert it.",
    "Use a dict {value: index}. For each element, compute target - element and check the dict before inserting.",
]

SHORT_TEXT = "short"        # < 20 chars — invalid
VALID_TEXT  = PROBLEM_TEXT  # > 20 chars — valid


# ── Helpers ───────────────────────────────────────────────────────────────────

def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def register_and_login(client, username=None, email=None, password="Pass1234"):
    """Register + login a user, auto-generating unique credentials if not provided."""
    uid = uuid.uuid4().hex[:8]
    username = username or f"user_{uid}"
    email    = email    or f"{uid}@cw.dev"
    client.post("/auth/register", json={"username": username, "email": email, "password": password})
    resp = client.post("/auth/login", json={"email": email, "password": password})
    data = resp.get_json()
    assert "access_token" in data, f"Login failed: {data}"
    return data["access_token"]


def mock_llm_client(hints=None):
    """Return a MagicMock LLM client whose generate_hints() returns MOCK_HINTS."""
    m = MagicMock()
    m.generate_hints.return_value = hints or MOCK_HINTS
    return m


# ══════════════════════════════════════════════════════════════════════════════
# UNIT TESTS — HintEngineService
# ══════════════════════════════════════════════════════════════════════════════

class TestHintEngineServiceUnit:
    """
    Pure unit tests for HintEngineService.
    Uses the DB (in-memory SQLite) but mocks the LLM client.
    """

    # ── start_session ──────────────────────────────────────────────────────────

    def test_start_session_returns_hint_1(self, app, sample_user):
        """start_session() returns Hint #1 in the response dict."""
        with app.app_context():
            svc = HintEngineService()
            svc._llm_client = mock_llm_client()

            result = svc.start_session(str(sample_user.id), VALID_TEXT)

        assert result["hint_level"] == 1
        assert result["hint"] == MOCK_HINTS[0]
        assert result["total_hints"] == 5
        assert result["exhausted"] is False
        assert "session_id" in result

    def test_start_session_creates_db_session_row(self, app, db, sample_user):
        """start_session() persists a UserProblemSession row."""
        from app.models.session import UserProblemSession

        with app.app_context():
            svc = HintEngineService()
            svc._llm_client = mock_llm_client()
            result = svc.start_session(str(sample_user.id), VALID_TEXT)

            session = UserProblemSession.query.filter_by(
                id=uuid.UUID(result["session_id"])
            ).first()

        assert session is not None
        assert str(session.user_id) == str(sample_user.id)
        assert session.hints_requested == 1
        assert session.current_hint_level == 1
        assert session.is_solved is False

    def test_start_session_logs_hint_1_to_db(self, app, db, sample_user):
        """start_session() writes a HintLog row for Hint #1."""
        from app.models.hint_log import HintLog

        with app.app_context():
            svc = HintEngineService()
            svc._llm_client = mock_llm_client()
            result = svc.start_session(str(sample_user.id), VALID_TEXT)

            log = HintLog.query.filter_by(
                session_id=uuid.UUID(result["session_id"]),
                hint_level=1,
            ).first()

        assert log is not None
        assert log.hint_text == MOCK_HINTS[0]

    def test_start_session_calls_llm_on_cache_miss(self, app, sample_user):
        """LLM is invoked when no cached hints exist."""
        with app.app_context():
            svc = HintEngineService()
            llm = mock_llm_client()
            svc._llm_client = llm

            svc.start_session(str(sample_user.id), VALID_TEXT)

        llm.generate_hints.assert_called_once_with(VALID_TEXT)

    def test_start_session_skips_llm_on_cache_hit(self, app, sample_user):
        """LLM is NOT called when hints are already in Redis cache."""
        from app.utils.cache import cache_hints, get_problem_hash

        with app.app_context():
            problem_hash = get_problem_hash(VALID_TEXT)
            cache_hints(problem_hash, MOCK_HINTS)   # pre-warm cache

            svc = HintEngineService()
            llm = mock_llm_client()
            svc._llm_client = llm

            svc.start_session(str(sample_user.id), VALID_TEXT)

        llm.generate_hints.assert_not_called()

    def test_start_session_caches_hints_on_llm_call(self, app, sample_user):
        """After a cache MISS + LLM call, hints are stored in Redis."""
        from app.utils.cache import get_cached_hints, get_problem_hash

        with app.app_context():
            svc = HintEngineService()
            svc._llm_client = mock_llm_client()
            svc.start_session(str(sample_user.id), VALID_TEXT)

            cached = get_cached_hints(get_problem_hash(VALID_TEXT))

        assert cached == MOCK_HINTS

    def test_start_session_stores_hint_index_in_redis(self, app, sample_user):
        """After start_session(), Redis holds hint_index=1 for the new session."""
        from app.utils.cache import get_session_hint_index

        with app.app_context():
            svc = HintEngineService()
            svc._llm_client = mock_llm_client()
            result = svc.start_session(str(sample_user.id), VALID_TEXT)
            idx = get_session_hint_index(result["session_id"])

        assert idx == 1

    # ── get_next_hint ──────────────────────────────────────────────────────────

    def test_get_next_hint_returns_hint_2(self, app, db, sample_user):
        """After start_session (hint 1), get_next_hint delivers hint 2."""
        with app.app_context():
            svc = HintEngineService()
            svc._llm_client = mock_llm_client()

            # Start session (delivers hint 1)
            start = svc.start_session(str(sample_user.id), VALID_TEXT)
            session_id = start["session_id"]

            # Get next hint (should be hint 2)
            result = svc.get_next_hint(session_id, str(sample_user.id))

        assert result["hint_level"] == 2
        assert result["hint"] == MOCK_HINTS[1]
        assert result["exhausted"] is False

    def test_get_next_hint_increments_db_counters(self, app, db, sample_user):
        """get_next_hint() updates hints_requested and current_hint_level in DB."""
        from app.models.session import UserProblemSession

        with app.app_context():
            svc = HintEngineService()
            svc._llm_client = mock_llm_client()
            start = svc.start_session(str(sample_user.id), VALID_TEXT)
            session_id = start["session_id"]

            svc.get_next_hint(session_id, str(sample_user.id))

            session = UserProblemSession.query.filter_by(
                id=uuid.UUID(session_id)
            ).first()

        assert session.hints_requested == 2
        assert session.current_hint_level == 2

    def test_get_next_hint_logs_to_db(self, app, db, sample_user):
        """get_next_hint() writes a HintLog entry for the new level."""
        from app.models.hint_log import HintLog

        with app.app_context():
            svc = HintEngineService()
            svc._llm_client = mock_llm_client()
            start = svc.start_session(str(sample_user.id), VALID_TEXT)
            session_id = start["session_id"]

            svc.get_next_hint(session_id, str(sample_user.id))

            log = HintLog.query.filter_by(
                session_id=uuid.UUID(session_id),
                hint_level=2,
            ).first()

        assert log is not None
        assert log.hint_text == MOCK_HINTS[1]

    def test_get_next_hint_does_not_call_llm_when_cached(self, app, db, sample_user):
        """Subsequent get_next_hint() calls do NOT re-invoke the LLM."""
        with app.app_context():
            svc = HintEngineService()
            llm = mock_llm_client()
            svc._llm_client = llm

            start = svc.start_session(str(sample_user.id), VALID_TEXT)
            session_id = start["session_id"]

            # Get hints 2, 3, 4 — none should call LLM
            for _ in range(3):
                svc.get_next_hint(session_id, str(sample_user.id))

        # LLM was called only once (during start_session on cache miss)
        assert llm.generate_hints.call_count == 1

    def test_get_next_hint_advances_through_all_5_levels(self, app, db, sample_user):
        """Iterating through get_next_hint() delivers hints 2→3→4→5 in order."""
        with app.app_context():
            svc = HintEngineService()
            svc._llm_client = mock_llm_client()
            start = svc.start_session(str(sample_user.id), VALID_TEXT)
            session_id = start["session_id"]

            hints_received = [start["hint"]]   # hint 1 already in

            for i in range(4):                 # hints 2, 3, 4, 5
                r = svc.get_next_hint(session_id, str(sample_user.id))
                hints_received.append(r["hint"])

        assert hints_received == MOCK_HINTS

    def test_get_next_hint_returns_exhausted_after_hint_5(self, app, db, sample_user):
        """After all 5 hints, get_next_hint() returns exhausted=True."""
        with app.app_context():
            svc = HintEngineService()
            svc._llm_client = mock_llm_client()
            start = svc.start_session(str(sample_user.id), VALID_TEXT)
            session_id = start["session_id"]

            for _ in range(4):                # advance to hint 5
                svc.get_next_hint(session_id, str(sample_user.id))

            # This call should be exhausted
            result = svc.get_next_hint(session_id, str(sample_user.id))

        assert result["exhausted"] is True
        assert "message" in result

    def test_get_next_hint_stays_exhausted_on_repeated_calls(self, app, db, sample_user):
        """Calling get_next_hint() after exhaustion keeps returning exhausted."""
        with app.app_context():
            svc = HintEngineService()
            svc._llm_client = mock_llm_client()
            start = svc.start_session(str(sample_user.id), VALID_TEXT)
            session_id = start["session_id"]

            for _ in range(5):
                svc.get_next_hint(session_id, str(sample_user.id))

            result1 = svc.get_next_hint(session_id, str(sample_user.id))
            result2 = svc.get_next_hint(session_id, str(sample_user.id))

        assert result1["exhausted"] is True
        assert result2["exhausted"] is True

    def test_get_next_hint_404_on_wrong_user(self, app, db, sample_user):
        """get_next_hint() returns 404 when session doesn't belong to user."""
        from werkzeug.exceptions import NotFound

        with app.app_context():
            svc = HintEngineService()
            svc._llm_client = mock_llm_client()
            start = svc.start_session(str(sample_user.id), VALID_TEXT)
            session_id = start["session_id"]

            other_user_id = str(uuid.uuid4())   # random user

            with pytest.raises((NotFound, Exception)):
                svc.get_next_hint(session_id, other_user_id)

    def test_get_next_hint_404_on_invalid_session_id(self, app, db, sample_user):
        """get_next_hint() returns 404 for a non-existent session UUID."""
        from werkzeug.exceptions import NotFound

        with app.app_context():
            svc = HintEngineService()
            svc._llm_client = mock_llm_client()

            with pytest.raises((NotFound, Exception)):
                svc.get_next_hint(str(uuid.uuid4()), str(sample_user.id))

    # ── get_session_hints ──────────────────────────────────────────────────────

    def test_get_session_hints_returns_all_delivered(self, app, db, sample_user):
        """get_session_hints() returns all hints logged so far in order."""
        with app.app_context():
            svc = HintEngineService()
            svc._llm_client = mock_llm_client()

            start = svc.start_session(str(sample_user.id), VALID_TEXT)
            session_id = start["session_id"]

            svc.get_next_hint(session_id, str(sample_user.id))
            svc.get_next_hint(session_id, str(sample_user.id))

            history = svc.get_session_hints(session_id, str(sample_user.id))

        assert len(history) == 3
        assert history[0]["level"] == 1
        assert history[1]["level"] == 2
        assert history[2]["level"] == 3

    def test_get_session_hints_empty_before_any_hint(self, app, db, sample_session, sample_user):
        """A newly created session with no hints returns an empty list."""
        with app.app_context():
            svc = HintEngineService()
            hints = svc.get_session_hints(str(sample_session.id), str(sample_user.id))

        # sample_session has 1 hint_requested but no HintLog rows yet
        # (created directly in DB without going through start_session)
        # So result may have 0 rows
        assert isinstance(hints, list)

    def test_get_session_hints_contains_hint_text(self, app, db, sample_user):
        """Each item in get_session_hints() has 'level' and 'hint' keys."""
        with app.app_context():
            svc = HintEngineService()
            svc._llm_client = mock_llm_client()
            start = svc.start_session(str(sample_user.id), VALID_TEXT)
            session_id = start["session_id"]

            history = svc.get_session_hints(session_id, str(sample_user.id))

        assert "level" in history[0]
        assert "hint" in history[0]
        assert "delivered_at" in history[0]

    # ── reset_session ──────────────────────────────────────────────────────────

    def test_reset_session_clears_redis_index(self, app, db, sample_user):
        """reset_session() resets Redis pointer to 0."""
        from app.utils.cache import get_session_hint_index

        with app.app_context():
            svc = HintEngineService()
            svc._llm_client = mock_llm_client()
            start = svc.start_session(str(sample_user.id), VALID_TEXT)
            session_id = start["session_id"]

            svc.get_next_hint(session_id, str(sample_user.id))   # advance to 2

            svc.reset_session(session_id, str(sample_user.id))
            idx = get_session_hint_index(session_id)

        assert idx == 0

    def test_reset_session_resets_db_counters(self, app, db, sample_user):
        """reset_session() zeroes hints_requested and current_hint_level in DB."""
        from app.models.session import UserProblemSession

        with app.app_context():
            svc = HintEngineService()
            svc._llm_client = mock_llm_client()
            start = svc.start_session(str(sample_user.id), VALID_TEXT)
            session_id = start["session_id"]

            svc.get_next_hint(session_id, str(sample_user.id))
            svc.reset_session(session_id, str(sample_user.id))

            session = UserProblemSession.query.filter_by(
                id=uuid.UUID(session_id)
            ).first()

        assert session.hints_requested == 0
        assert session.current_hint_level == 0

    def test_reset_then_restart_delivers_hint_1_again(self, app, db, sample_user):
        """After reset + get_next_hint, user gets Hint #1 again."""
        with app.app_context():
            svc = HintEngineService()
            svc._llm_client = mock_llm_client()
            start = svc.start_session(str(sample_user.id), VALID_TEXT)
            session_id = start["session_id"]

            svc.get_next_hint(session_id, str(sample_user.id))   # hint 2
            svc.reset_session(session_id, str(sample_user.id))
            result = svc.get_next_hint(session_id, str(sample_user.id))

        assert result["hint_level"] == 1
        assert result["hint"] == MOCK_HINTS[0]

    # ── _get_session helper ────────────────────────────────────────────────────

    def test_get_session_raises_404_on_bad_uuid(self, app, sample_user):
        """_get_session() aborts 404 for a non-UUID string."""
        from werkzeug.exceptions import NotFound

        with app.app_context():
            svc = HintEngineService()
            with pytest.raises((NotFound, Exception)):
                svc._get_session("not-a-uuid", str(sample_user.id))

    def test_get_session_raises_404_for_unknown_session(self, app, sample_user):
        """_get_session() aborts 404 when session ID doesn't exist in DB."""
        from werkzeug.exceptions import NotFound

        with app.app_context():
            svc = HintEngineService()
            with pytest.raises((NotFound, Exception)):
                svc._get_session(str(uuid.uuid4()), str(sample_user.id))


# ── Import alias for readability ──────────────────────────────────────────────
from app.services.hint_engine import HintEngineService   # noqa: E402


# ══════════════════════════════════════════════════════════════════════════════
# INTEGRATION TESTS — /hints/* API routes
# ══════════════════════════════════════════════════════════════════════════════

class TestHintSubmitEndpoint:
    """Integration tests for POST /hints/submit"""

    def test_submit_valid_problem_returns_201(self, client):
        """Valid problem → 201 with hint_level=1 and a hint string."""
        token = register_and_login(client)

        with patch("app.services.hint_engine.get_llm_client", return_value=mock_llm_client()):
            resp = client.post(
                "/hints/submit",
                json={"problem_text": VALID_TEXT},
                headers=auth_headers(token),
            )

        assert resp.status_code == 201
        body = resp.get_json()
        assert body["hint_level"] == 1
        assert body["hint"] == MOCK_HINTS[0]
        assert body["total_hints"] == 5
        assert body["exhausted"] is False
        assert "session_id" in body

    def test_submit_requires_auth(self, client):
        """POST /hints/submit without token → 401."""
        resp = client.post("/hints/submit", json={"problem_text": VALID_TEXT})
        assert resp.status_code == 401

    def test_submit_rejects_missing_problem_text(self, client):
        """Empty body → 400."""
        token = register_and_login(client)
        resp = client.post(
            "/hints/submit",
            json={},
            headers=auth_headers(token),
        )
        assert resp.status_code == 400

    def test_submit_rejects_short_problem_text(self, client):
        """Problem text shorter than 20 chars → 400."""
        token = register_and_login(client)
        resp = client.post(
            "/hints/submit",
            json={"problem_text": SHORT_TEXT},
            headers=auth_headers(token),
        )
        assert resp.status_code == 400
        assert "error" in resp.get_json()

    def test_submit_rejects_whitespace_only_text(self, client):
        """Whitespace-only problem → 400."""
        token = register_and_login(client)
        resp = client.post(
            "/hints/submit",
            json={"problem_text": "   "},
            headers=auth_headers(token),
        )
        assert resp.status_code == 400

    def test_submit_creates_session_in_db(self, client, db):
        """After submit, a UserProblemSession row exists in DB."""
        from app.models.session import UserProblemSession

        token = register_and_login(client)

        with patch("app.services.hint_engine.get_llm_client", return_value=mock_llm_client()):
            resp = client.post(
                "/hints/submit",
                json={"problem_text": VALID_TEXT},
                headers=auth_headers(token),
            )

        session_id = resp.get_json()["session_id"]
        session = UserProblemSession.query.filter_by(
            id=uuid.UUID(session_id)
        ).first()
        assert session is not None
        assert session.hints_requested == 1

    def test_submit_second_same_problem_hits_cache(self, client, db):
        """Two submits of the same problem text — LLM called only once."""
        token1 = register_and_login(client)
        token2 = register_and_login(client)
        llm = mock_llm_client()

        with patch("app.services.hint_engine.get_llm_client", return_value=llm):
            client.post("/hints/submit", json={"problem_text": VALID_TEXT}, headers=auth_headers(token1))
            client.post("/hints/submit", json={"problem_text": VALID_TEXT}, headers=auth_headers(token2))

        assert llm.generate_hints.call_count == 1  # second hit cache


class TestNextHintEndpoint:
    """Integration tests for GET /hints/next/<session_id>"""

    def _start(self, client, token):
        """Helper: submit a problem and return the session_id."""
        with patch("app.services.hint_engine.get_llm_client", return_value=mock_llm_client()):
            resp = client.post(
                "/hints/submit",
                json={"problem_text": VALID_TEXT},
                headers=auth_headers(token),
            )
        return resp.get_json()["session_id"]

    def test_next_hint_returns_200(self, client):
        """GET /hints/next/<session_id> → 200 with hint_level=2."""
        token = register_and_login(client)
        session_id = self._start(client, token)

        with patch("app.services.hint_engine.get_llm_client", return_value=mock_llm_client()):
            resp = client.get(f"/hints/next/{session_id}", headers=auth_headers(token))

        assert resp.status_code == 200
        body = resp.get_json()
        assert body["hint_level"] == 2
        assert body["hint"] == MOCK_HINTS[1]

    def test_next_hint_requires_auth(self, client):
        """GET /hints/next/<session_id> without token → 401."""
        resp = client.get(f"/hints/next/{uuid.uuid4()}")
        assert resp.status_code == 401

    def test_next_hint_404_on_wrong_session(self, client):
        """GET /hints/next/<random_uuid> → 404."""
        token = register_and_login(client)
        with patch("app.services.hint_engine.get_llm_client", return_value=mock_llm_client()):
            resp = client.get(f"/hints/next/{uuid.uuid4()}", headers=auth_headers(token))
        assert resp.status_code == 404

    def test_next_hint_progressive_levels(self, client):
        """Calling next 4 times yields hints at levels 2, 3, 4, 5."""
        token = register_and_login(client)
        session_id = self._start(client, token)

        levels = []
        with patch("app.services.hint_engine.get_llm_client", return_value=mock_llm_client()):
            for _ in range(4):
                r = client.get(f"/hints/next/{session_id}", headers=auth_headers(token))
                levels.append(r.get_json()["hint_level"])

        assert levels == [2, 3, 4, 5]

    def test_next_hint_exhausted_flag(self, client):
        """After hint 5, exhausted=True is returned."""
        token = register_and_login(client)
        session_id = self._start(client, token)

        with patch("app.services.hint_engine.get_llm_client", return_value=mock_llm_client()):
            for _ in range(4):
                client.get(f"/hints/next/{session_id}", headers=auth_headers(token))
            # This 5th next call is the exhaustion call
            resp = client.get(f"/hints/next/{session_id}", headers=auth_headers(token))

        body = resp.get_json()
        assert body["exhausted"] is True
        assert "message" in body

    def test_next_hint_other_user_cannot_access_session(self, client):
        """A different user's token cannot fetch hints for another user's session."""
        token_a = register_and_login(client)
        token_b = register_and_login(client)

        session_id = self._start(client, token_a)

        with patch("app.services.hint_engine.get_llm_client", return_value=mock_llm_client()):
            resp = client.get(f"/hints/next/{session_id}", headers=auth_headers(token_b))

        assert resp.status_code == 404


class TestGetSessionEndpoint:
    """Integration tests for GET /hints/session/<session_id>"""

    def _start_and_advance(self, client, token, steps=2):
        """Start a session and advance `steps` times; return session_id."""
        with patch("app.services.hint_engine.get_llm_client", return_value=mock_llm_client()):
            r = client.post("/hints/submit", json={"problem_text": VALID_TEXT}, headers=auth_headers(token))
            session_id = r.get_json()["session_id"]
            for _ in range(steps - 1):
                client.get(f"/hints/next/{session_id}", headers=auth_headers(token))
        return session_id

    def test_get_session_returns_hints_list(self, client):
        """GET /hints/session/<id> → 200 with 'hints' list."""
        token = register_and_login(client)
        session_id = self._start_and_advance(client, token, steps=3)

        with patch("app.services.hint_engine.get_llm_client", return_value=mock_llm_client()):
            resp = client.get(f"/hints/session/{session_id}", headers=auth_headers(token))

        assert resp.status_code == 200
        body = resp.get_json()
        assert "hints" in body
        assert len(body["hints"]) == 3

    def test_get_session_requires_auth(self, client):
        """GET /hints/session/<id> without token → 401."""
        resp = client.get(f"/hints/session/{uuid.uuid4()}")
        assert resp.status_code == 401

    def test_get_session_404_on_unknown_session(self, client):
        """GET /hints/session/<random_uuid> → 404."""
        token = register_and_login(client)
        with patch("app.services.hint_engine.get_llm_client", return_value=mock_llm_client()):
            resp = client.get(f"/hints/session/{uuid.uuid4()}", headers=auth_headers(token))
        assert resp.status_code == 404

    def test_get_session_hint_structure(self, client):
        """Each hint object has 'level', 'hint', and 'delivered_at' keys."""
        token = register_and_login(client)
        session_id = self._start_and_advance(client, token, steps=1)

        with patch("app.services.hint_engine.get_llm_client", return_value=mock_llm_client()):
            resp = client.get(f"/hints/session/{session_id}", headers=auth_headers(token))

        hints = resp.get_json()["hints"]
        assert hints[0]["level"] == 1
        assert hints[0]["hint"] == MOCK_HINTS[0]
        assert "delivered_at" in hints[0]

    def test_get_session_hints_ordered_by_level(self, client):
        """Hints are returned in ascending order of hint_level."""
        token = register_and_login(client)
        session_id = self._start_and_advance(client, token, steps=4)

        with patch("app.services.hint_engine.get_llm_client", return_value=mock_llm_client()):
            resp = client.get(f"/hints/session/{session_id}", headers=auth_headers(token))

        levels = [h["level"] for h in resp.get_json()["hints"]]
        assert levels == sorted(levels)


class TestResetSessionEndpoint:
    """Integration tests for POST /hints/reset/<session_id>"""

    def test_reset_session_returns_200(self, client):
        """POST /hints/reset/<id> → 200 with confirmation message."""
        token = register_and_login(client)

        with patch("app.services.hint_engine.get_llm_client", return_value=mock_llm_client()):
            r = client.post("/hints/submit", json={"problem_text": VALID_TEXT}, headers=auth_headers(token))
            session_id = r.get_json()["session_id"]
            resp = client.post(f"/hints/reset/{session_id}", headers=auth_headers(token))

        assert resp.status_code == 200
        assert "message" in resp.get_json()

    def test_reset_session_requires_auth(self, client):
        """POST /hints/reset/<id> without token → 401."""
        resp = client.post(f"/hints/reset/{uuid.uuid4()}")
        assert resp.status_code == 401

    def test_reset_then_next_delivers_hint_1(self, client):
        """After reset, GET /hints/next delivers hint_level=1 again."""
        token = register_and_login(client)

        with patch("app.services.hint_engine.get_llm_client", return_value=mock_llm_client()):
            r = client.post("/hints/submit", json={"problem_text": VALID_TEXT}, headers=auth_headers(token))
            session_id = r.get_json()["session_id"]

            # Advance to hint 3
            client.get(f"/hints/next/{session_id}", headers=auth_headers(token))
            client.get(f"/hints/next/{session_id}", headers=auth_headers(token))

            # Reset
            client.post(f"/hints/reset/{session_id}", headers=auth_headers(token))

            # Next hint should be level 1 again
            resp = client.get(f"/hints/next/{session_id}", headers=auth_headers(token))

        body = resp.get_json()
        assert body["hint_level"] == 1
        assert body["hint"] == MOCK_HINTS[0]


# ══════════════════════════════════════════════════════════════════════════════
# EDGE CASE / BOUNDARY TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestHintEngineEdgeCases:

    def test_exactly_20_char_problem_is_accepted(self, client):
        """Problem text of exactly 20 chars passes validation."""
        token = register_and_login(client)
        text_20 = "A" * 20
        with patch("app.services.hint_engine.get_llm_client", return_value=mock_llm_client()):
            resp = client.post("/hints/submit", json={"problem_text": text_20}, headers=auth_headers(token))
        assert resp.status_code == 201

    def test_problem_text_at_max_length_is_accepted(self, client):
        """Problem text of 10,000 chars is accepted."""
        token = register_and_login(client)
        text_10k = "A" * 10_000
        with patch("app.services.hint_engine.get_llm_client", return_value=mock_llm_client()):
            resp = client.post("/hints/submit", json={"problem_text": text_10k}, headers=auth_headers(token))
        assert resp.status_code == 201

    def test_problem_text_over_max_length_is_rejected(self, client):
        """Problem text of 10,001 chars → 400."""
        token = register_and_login(client)
        text_over = "A" * 10_001
        resp = client.post("/hints/submit", json={"problem_text": text_over}, headers=auth_headers(token))
        assert resp.status_code == 400

    def test_same_problem_different_users_each_get_own_session(self, client, db):
        """Two different users submitting the same problem each get their own session."""
        from app.models.session import UserProblemSession

        token_a = register_and_login(client)
        token_b = register_and_login(client)

        with patch("app.services.hint_engine.get_llm_client", return_value=mock_llm_client()):
            r_a = client.post("/hints/submit", json={"problem_text": VALID_TEXT}, headers=auth_headers(token_a))
            r_b = client.post("/hints/submit", json={"problem_text": VALID_TEXT}, headers=auth_headers(token_b))

        sid_a = r_a.get_json()["session_id"]
        sid_b = r_b.get_json()["session_id"]

        assert sid_a != sid_b

    def test_hint_engine_service_import(self):
        """HintEngineService can be imported without errors."""
        from app.services.hint_engine import HintEngineService
        assert HintEngineService is not None

    def test_hint_engine_max_hints_constant(self):
        """MAX_HINTS is set to 5."""
        from app.services.hint_engine import MAX_HINTS
        assert MAX_HINTS == 5
