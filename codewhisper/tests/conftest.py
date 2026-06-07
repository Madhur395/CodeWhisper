"""
CodeWhisper — Pytest Configuration & Shared Fixtures
Phase 3 update:
  - db.create_all() / db.drop_all() active (Phase 2)
  - mock_redis autouse fixture patches Redis so no real server needed (Phase 3)
"""

import pytest
from unittest.mock import MagicMock, patch

from app import create_app
from app.extensions import db as _db
from app.config import TestingConfig


# ══════════════════════════════════════════════════════════════════════════════
# CORE APP / DB FIXTURES
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="function")
def app():
    """
    Create a test Flask application with in-memory SQLite.
    Each test function gets a clean database.
    """
    app = create_app(config=TestingConfig)
    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture(scope="function")
def db(app):
    """Expose the db instance bound to the test app context."""
    return _db


@pytest.fixture(scope="function")
def client(app):
    """Return a Flask test HTTP client."""
    return app.test_client()


@pytest.fixture(scope="function")
def runner(app):
    """Return a Flask CLI test runner."""
    return app.test_cli_runner()


# ══════════════════════════════════════════════════════════════════════════════
# REDIS MOCK — autouse so ALL tests skip real Redis by default
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(autouse=True)
def mock_redis():
    """
    Patch the Redis client in app.utils.cache so no real Redis server
    is required during testing.

    Behaviour:
      - blacklist_token / is_token_blacklisted use an in-memory dict
      - hint cache helpers work via the same dict
      - session hint index helpers work via the same dict

    Tests that need to assert specific Redis interactions can override
    this fixture or patch get_redis_client() directly with MagicMock.
    """
    store = {}

    mock_client = MagicMock()

    def fake_setex(key, ttl, value):
        store[key] = str(value)

    def fake_get(key):
        return store.get(key)

    def fake_exists(key):
        return 1 if key in store else 0

    def fake_delete(key):
        store.pop(key, None)

    mock_client.setex.side_effect = fake_setex
    mock_client.get.side_effect = fake_get
    mock_client.exists.side_effect = fake_exists
    mock_client.delete.side_effect = fake_delete

    with patch("app.utils.cache.get_redis_client", return_value=mock_client):
        # Also patch the module-level _redis_client so the singleton
        # doesn't hold a stale reference across tests
        with patch("app.utils.cache._redis_client", mock_client):
            yield mock_client


# ══════════════════════════════════════════════════════════════════════════════
# REUSABLE DATA FACTORIES
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def sample_user(db):
    """Create and persist a test user with a real bcrypt hash."""
    from app.models.user import User
    from app.utils.validators import hash_password
    user = User(
        username="testuser",
        email="test@codewhisper.dev",
        password_hash=hash_password("TestPass123"),
    )
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def sample_user_token(client, sample_user):
    """Return a valid JWT for sample_user via the login endpoint."""
    resp = client.post("/auth/login", json={
        "email": "test@codewhisper.dev",
        "password": "TestPass123",
    })
    return resp.get_json()["access_token"]


@pytest.fixture
def sample_problem(db):
    """Create and persist a test problem."""
    from app.models.problem import Problem
    problem = Problem(
        title="Two Sum",
        statement=(
            "Given an array of integers nums and an integer target, "
            "return indices of the two numbers such that they add up to target."
        ),
        tags=["Array", "HashMap"],
        difficulty="Easy",
        source="LeetCode",
    )
    db.session.add(problem)
    db.session.commit()
    return problem


@pytest.fixture
def sample_session(db, sample_user, sample_problem):
    """Create and persist a test UserProblemSession."""
    from app.models.session import UserProblemSession
    session = UserProblemSession(
        user_id=sample_user.id,
        problem_id=sample_problem.id,
        problem_text=sample_problem.statement,
        hints_requested=1,
        current_hint_level=1,
        is_solved=False,
    )
    db.session.add(session)
    db.session.commit()
    return session


@pytest.fixture
def sample_hint_log(db, sample_session):
    """Create and persist a test HintLog entry."""
    from app.models.hint_log import HintLog
    hint = HintLog(
        session_id=sample_session.id,
        hint_level=1,
        hint_text="Think about what data structure gives O(1) lookup time.",
    )
    db.session.add(hint)
    db.session.commit()
    return hint
