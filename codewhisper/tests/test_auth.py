"""
CodeWhisper — Phase 3: Authentication System Tests
Covers register, login, logout, /me, validators, and password utilities.
Uses fakeredis so no real Redis server is needed.
"""

import pytest
from unittest.mock import patch, MagicMock


# ══════════════════════════════════════════════════════════════════════════════
# HELPER — get a valid JWT token for a given user via the login endpoint
# ══════════════════════════════════════════════════════════════════════════════

def register_and_login(client, username="alice", email="alice@cw.dev", password="Secret123"):
    """Register a user and return the JWT access token."""
    client.post("/auth/register", json={
        "username": username,
        "email": email,
        "password": password,
    })
    resp = client.post("/auth/login", json={"email": email, "password": password})
    return resp.get_json()["access_token"]


def auth_headers(token: str) -> dict:
    """Build the Authorization header dict."""
    return {"Authorization": f"Bearer {token}"}


# ══════════════════════════════════════════════════════════════════════════════
# VALIDATOR UNIT TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestValidators:
    """Unit tests for app/utils/validators.py"""

    # ── hash_password / verify_password ──────────────────────────────────

    def test_hash_password_returns_string(self):
        from app.utils.validators import hash_password
        h = hash_password("mypassword")
        assert isinstance(h, str)
        assert len(h) > 20

    def test_hash_password_not_plaintext(self):
        from app.utils.validators import hash_password
        h = hash_password("mypassword")
        assert h != "mypassword"

    def test_verify_password_correct(self):
        from app.utils.validators import hash_password, verify_password
        h = hash_password("correct_horse")
        assert verify_password("correct_horse", h) is True

    def test_verify_password_wrong(self):
        from app.utils.validators import hash_password, verify_password
        h = hash_password("correct_horse")
        assert verify_password("wrong_password", h) is False

    def test_hash_is_unique_per_call(self):
        """bcrypt uses random salts — same input → different hashes each time."""
        from app.utils.validators import hash_password
        h1 = hash_password("same_password")
        h2 = hash_password("same_password")
        assert h1 != h2

    def test_both_hashes_verify_correctly(self):
        """Despite different hashes, both verify correctly."""
        from app.utils.validators import hash_password, verify_password
        h1 = hash_password("same_password")
        h2 = hash_password("same_password")
        assert verify_password("same_password", h1) is True
        assert verify_password("same_password", h2) is True

    # ── validate_register_payload ─────────────────────────────────────────

    def test_register_valid_payload(self):
        from app.utils.validators import validate_register_payload
        ok, err = validate_register_payload({
            "username": "alice",
            "email": "alice@example.com",
            "password": "securepass"
        })
        assert ok is True
        assert err == ""

    def test_register_missing_body(self):
        from app.utils.validators import validate_register_payload
        ok, err = validate_register_payload(None)
        assert ok is False
        assert err != ""

    def test_register_missing_username(self):
        from app.utils.validators import validate_register_payload
        ok, err = validate_register_payload({"email": "a@b.com", "password": "pass1234"})
        assert ok is False
        assert "username" in err.lower()

    def test_register_username_too_short(self):
        from app.utils.validators import validate_register_payload
        ok, err = validate_register_payload({"username": "ab", "email": "a@b.com", "password": "pass1234"})
        assert ok is False
        assert "3" in err

    def test_register_username_invalid_chars(self):
        from app.utils.validators import validate_register_payload
        ok, err = validate_register_payload({"username": "alice!", "email": "a@b.com", "password": "pass1234"})
        assert ok is False
        assert "username" in err.lower()

    def test_register_missing_email(self):
        from app.utils.validators import validate_register_payload
        ok, err = validate_register_payload({"username": "alice", "password": "pass1234"})
        assert ok is False
        assert "email" in err.lower()

    def test_register_invalid_email(self):
        from app.utils.validators import validate_register_payload
        ok, err = validate_register_payload({"username": "alice", "email": "not-an-email", "password": "pass1234"})
        assert ok is False
        assert "email" in err.lower()

    def test_register_missing_password(self):
        from app.utils.validators import validate_register_payload
        ok, err = validate_register_payload({"username": "alice", "email": "a@b.com"})
        assert ok is False
        assert "password" in err.lower()

    def test_register_password_too_short(self):
        from app.utils.validators import validate_register_payload
        ok, err = validate_register_payload({"username": "alice", "email": "a@b.com", "password": "short"})
        assert ok is False
        assert "8" in err

    # ── validate_login_payload ────────────────────────────────────────────

    def test_login_valid_payload(self):
        from app.utils.validators import validate_login_payload
        ok, err = validate_login_payload({"email": "a@b.com", "password": "pass1234"})
        assert ok is True

    def test_login_missing_email(self):
        from app.utils.validators import validate_login_payload
        ok, err = validate_login_payload({"password": "pass1234"})
        assert ok is False

    def test_login_missing_password(self):
        from app.utils.validators import validate_login_payload
        ok, err = validate_login_payload({"email": "a@b.com"})
        assert ok is False

    def test_login_missing_body(self):
        from app.utils.validators import validate_login_payload
        ok, err = validate_login_payload(None)
        assert ok is False


# ══════════════════════════════════════════════════════════════════════════════
# REGISTER ENDPOINT TESTS  — POST /auth/register
# ══════════════════════════════════════════════════════════════════════════════

class TestRegister:

    def test_register_success(self, client):
        """Valid registration returns 201 with token and user profile."""
        resp = client.post("/auth/register", json={
            "username": "alice",
            "email": "alice@cw.dev",
            "password": "Secret123",
        })
        assert resp.status_code == 201
        body = resp.get_json()
        assert "access_token" in body
        assert body["user"]["username"] == "alice"
        assert body["user"]["email"] == "alice@cw.dev"
        assert "password_hash" not in body["user"]

    def test_register_creates_user_in_db(self, client, db):
        """User row exists in DB after registration."""
        from app.models.user import User
        client.post("/auth/register", json={
            "username": "bob",
            "email": "bob@cw.dev",
            "password": "Secret123",
        })
        user = User.query.filter_by(email="bob@cw.dev").first()
        assert user is not None
        assert user.username == "bob"

    def test_register_password_is_hashed_in_db(self, client, db):
        """Stored password is bcrypt hash, not plaintext."""
        from app.models.user import User
        client.post("/auth/register", json={
            "username": "carol",
            "email": "carol@cw.dev",
            "password": "Secret123",
        })
        user = User.query.filter_by(email="carol@cw.dev").first()
        assert user.password_hash != "Secret123"
        assert user.password_hash.startswith("$2b$")

    def test_register_duplicate_email(self, client):
        """Second registration with same email returns 409."""
        payload = {"username": "dave", "email": "dave@cw.dev", "password": "Secret123"}
        client.post("/auth/register", json=payload)
        resp = client.post("/auth/register", json={
            "username": "dave2",
            "email": "dave@cw.dev",
            "password": "Secret123",
        })
        assert resp.status_code == 409
        assert "email" in resp.get_json()["error"].lower()

    def test_register_duplicate_username(self, client):
        """Second registration with same username returns 409."""
        client.post("/auth/register", json={"username": "eve", "email": "eve@cw.dev", "password": "Secret123"})
        resp = client.post("/auth/register", json={"username": "eve", "email": "eve2@cw.dev", "password": "Secret123"})
        assert resp.status_code == 409
        assert "username" in resp.get_json()["error"].lower()

    def test_register_missing_username(self, client):
        resp = client.post("/auth/register", json={"email": "x@cw.dev", "password": "Secret123"})
        assert resp.status_code == 400

    def test_register_missing_email(self, client):
        resp = client.post("/auth/register", json={"username": "frank", "password": "Secret123"})
        assert resp.status_code == 400

    def test_register_missing_password(self, client):
        resp = client.post("/auth/register", json={"username": "frank", "email": "frank@cw.dev"})
        assert resp.status_code == 400

    def test_register_password_too_short(self, client):
        resp = client.post("/auth/register", json={
            "username": "grace", "email": "grace@cw.dev", "password": "short"
        })
        assert resp.status_code == 400
        assert "8" in resp.get_json()["error"]

    def test_register_invalid_email_format(self, client):
        resp = client.post("/auth/register", json={
            "username": "henry", "email": "not-an-email", "password": "Secret123"
        })
        assert resp.status_code == 400

    def test_register_username_special_chars(self, client):
        resp = client.post("/auth/register", json={
            "username": "bad name!", "email": "bad@cw.dev", "password": "Secret123"
        })
        assert resp.status_code == 400

    def test_register_empty_body(self, client):
        resp = client.post("/auth/register", json={})
        assert resp.status_code == 400

    def test_register_no_body(self, client):
        resp = client.post("/auth/register", content_type="application/json", data="")
        assert resp.status_code == 400

    def test_register_token_is_valid_jwt(self, client):
        """The returned token can immediately authenticate a request."""
        resp = client.post("/auth/register", json={
            "username": "ivy", "email": "ivy@cw.dev", "password": "Secret123"
        })
        token = resp.get_json()["access_token"]
        me_resp = client.get("/auth/me", headers=auth_headers(token))
        assert me_resp.status_code == 200

    def test_register_email_normalised_to_lowercase(self, client, db):
        """Email is stored in lowercase regardless of input casing."""
        from app.models.user import User
        client.post("/auth/register", json={
            "username": "jake",
            "email": "Jake@CW.DEV",
            "password": "Secret123",
        })
        user = User.query.filter_by(username="jake").first()
        assert user.email == "jake@cw.dev"


# ══════════════════════════════════════════════════════════════════════════════
# LOGIN ENDPOINT TESTS  — POST /auth/login
# ══════════════════════════════════════════════════════════════════════════════

class TestLogin:

    def test_login_success(self, client):
        """Valid credentials return 200 with access_token and user profile."""
        client.post("/auth/register", json={
            "username": "kim", "email": "kim@cw.dev", "password": "Secret123"
        })
        resp = client.post("/auth/login", json={"email": "kim@cw.dev", "password": "Secret123"})
        assert resp.status_code == 200
        body = resp.get_json()
        assert "access_token" in body
        assert body["user"]["email"] == "kim@cw.dev"

    def test_login_wrong_password(self, client):
        """Wrong password returns 401."""
        client.post("/auth/register", json={
            "username": "leo", "email": "leo@cw.dev", "password": "Secret123"
        })
        resp = client.post("/auth/login", json={"email": "leo@cw.dev", "password": "WrongPass99"})
        assert resp.status_code == 401
        assert "Invalid" in resp.get_json()["error"]

    def test_login_nonexistent_email(self, client):
        """Login with unregistered email returns 401 (not 404, to prevent enumeration)."""
        resp = client.post("/auth/login", json={"email": "ghost@cw.dev", "password": "Secret123"})
        assert resp.status_code == 401

    def test_login_missing_email(self, client):
        resp = client.post("/auth/login", json={"password": "Secret123"})
        assert resp.status_code == 400

    def test_login_missing_password(self, client):
        resp = client.post("/auth/login", json={"email": "a@cw.dev"})
        assert resp.status_code == 400

    def test_login_empty_body(self, client):
        resp = client.post("/auth/login", json={})
        assert resp.status_code == 400

    def test_login_token_authenticates_protected_route(self, client):
        """Token from login works on a @jwt_required() route."""
        token = register_and_login(client, "mia", "mia@cw.dev", "Secret123")
        resp = client.get("/auth/me", headers=auth_headers(token))
        assert resp.status_code == 200

    def test_login_email_case_insensitive(self, client):
        """Login works with different casing of registered email."""
        client.post("/auth/register", json={
            "username": "noah", "email": "noah@cw.dev", "password": "Secret123"
        })
        resp = client.post("/auth/login", json={"email": "NOAH@CW.DEV", "password": "Secret123"})
        assert resp.status_code == 200

    def test_login_response_has_no_password_hash(self, client):
        """Response body never exposes the password hash."""
        client.post("/auth/register", json={
            "username": "olivia", "email": "olivia@cw.dev", "password": "Secret123"
        })
        resp = client.post("/auth/login", json={"email": "olivia@cw.dev", "password": "Secret123"})
        body = resp.get_json()
        assert "password_hash" not in body
        assert "password_hash" not in body.get("user", {})


# ══════════════════════════════════════════════════════════════════════════════
# LOGOUT ENDPOINT TESTS  — POST /auth/logout
# ══════════════════════════════════════════════════════════════════════════════

class TestLogout:

    def test_logout_success(self, client):
        """Logout with a valid token returns 200."""
        token = register_and_login(client, "pat", "pat@cw.dev", "Secret123")
        with patch("app.utils.cache.get_redis_client") as mock_redis:
            mock_client = MagicMock()
            mock_redis.return_value = mock_client
            mock_client.exists.return_value = 0

            resp = client.post("/auth/logout", headers=auth_headers(token))
            assert resp.status_code == 200
            assert "Logged out" in resp.get_json()["message"]

    def test_logout_requires_token(self, client):
        """Logout without a token returns 401."""
        resp = client.post("/auth/logout")
        assert resp.status_code == 401

    def test_logout_blacklists_token(self, client):
        """After logout, the same token is rejected on protected routes."""
        token = register_and_login(client, "quinn", "quinn@cw.dev", "Secret123")

        # Patch Redis to simulate blacklisting
        blacklisted = set()

        def fake_setex(key, ttl, value):
            blacklisted.add(key)

        def fake_exists(key):
            return 1 if key in blacklisted else 0

        with patch("app.utils.cache.get_redis_client") as mock_redis:
            mock_client = MagicMock()
            mock_client.setex.side_effect = fake_setex
            mock_client.exists.side_effect = fake_exists
            mock_redis.return_value = mock_client

            # Logout
            logout_resp = client.post("/auth/logout", headers=auth_headers(token))
            assert logout_resp.status_code == 200

            # Same token now rejected
            me_resp = client.get("/auth/me", headers=auth_headers(token))
            assert me_resp.status_code == 401

    def test_logout_invalid_token(self, client):
        """Logout with garbage token returns 401/422."""
        resp = client.post("/auth/logout", headers={"Authorization": "Bearer garbage.token.here"})
        assert resp.status_code in [401, 422]


# ══════════════════════════════════════════════════════════════════════════════
# PROFILE ENDPOINT TESTS  — GET /auth/me
# ══════════════════════════════════════════════════════════════════════════════

class TestMe:

    def test_me_returns_user_profile(self, client):
        """GET /auth/me returns the authenticated user's profile."""
        token = register_and_login(client, "ray", "ray@cw.dev", "Secret123")
        resp = client.get("/auth/me", headers=auth_headers(token))
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["user"]["username"] == "ray"
        assert body["user"]["email"] == "ray@cw.dev"

    def test_me_requires_token(self, client):
        """GET /auth/me without token returns 401."""
        resp = client.get("/auth/me")
        assert resp.status_code == 401

    def test_me_with_invalid_token(self, client):
        """GET /auth/me with a bad token returns 401/422."""
        resp = client.get("/auth/me", headers={"Authorization": "Bearer bad.token"})
        assert resp.status_code in [401, 422]

    def test_me_response_excludes_password_hash(self, client):
        """Profile response never includes the password hash."""
        token = register_and_login(client, "sam", "sam@cw.dev", "Secret123")
        resp = client.get("/auth/me", headers=auth_headers(token))
        user = resp.get_json()["user"]
        assert "password_hash" not in user

    def test_me_includes_expected_fields(self, client):
        """Profile includes id, username, email, created_at."""
        token = register_and_login(client, "tara", "tara@cw.dev", "Secret123")
        resp = client.get("/auth/me", headers=auth_headers(token))
        user = resp.get_json()["user"]
        assert "id" in user
        assert "username" in user
        assert "email" in user
        assert "created_at" in user


# ══════════════════════════════════════════════════════════════════════════════
# JWT PROTECTION TESTS  — General token enforcement
# ══════════════════════════════════════════════════════════════════════════════

class TestJWTProtection:

    def test_protected_route_without_token_returns_401(self, client):
        """All @jwt_required() routes block unauthenticated requests."""
        routes = [
            ("GET",   "/auth/me"),
            ("POST",  "/auth/logout"),
            ("POST",  "/hints/submit"),
            ("GET",   "/hints/next/some-session"),
            ("GET",   "/hints/session/some-session"),
            ("GET",   "/progress/history"),
            ("GET",   "/progress/stats"),
            ("PATCH", "/progress/solve/some-session"),
            ("GET",   "/recommend/problems"),
        ]
        for method, path in routes:
            if method == "GET":
                resp = client.get(path)
            elif method == "POST":
                resp = client.post(path, json={})
            elif method == "PATCH":
                resp = client.patch(path, json={})
            else:
                resp = client.open(path, method=method)
            assert resp.status_code == 401, (
                f"{method} {path} should return 401, got {resp.status_code}"
            )

    def test_expired_token_returns_401(self, client, app):
        """An expired token is rejected with a clear error message."""
        from flask_jwt_extended import create_access_token
        from datetime import timedelta

        with app.app_context():
            expired_token = create_access_token(
                identity="some-user-id",
                expires_delta=timedelta(seconds=-1)   # already expired
            )

        resp = client.get("/auth/me", headers=auth_headers(expired_token))
        assert resp.status_code == 401
        assert "expired" in resp.get_json()["error"].lower()

    def test_malformed_token_returns_422(self, client):
        """A syntactically invalid token returns 422."""
        resp = client.get("/auth/me", headers={"Authorization": "Bearer not.a.jwt"})
        assert resp.status_code == 422

    def test_auth_routes_do_not_require_token(self, client):
        """/auth/register and /auth/login are publicly accessible."""
        r1 = client.post("/auth/register", json={})   # 400, not 401
        r2 = client.post("/auth/login",    json={})   # 400, not 401
        assert r1.status_code != 401
        assert r2.status_code != 401


# ══════════════════════════════════════════════════════════════════════════════
# CACHE UTILITY UNIT TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestCacheUtils:
    """Unit tests for blacklist_token / is_token_blacklisted."""

    def test_blacklist_token_calls_setex(self):
        from app.utils.cache import blacklist_token
        with patch("app.utils.cache.get_redis_client") as mock_r:
            mock_client = MagicMock()
            mock_r.return_value = mock_client
            blacklist_token("test-jti-123", 3600)
            mock_client.setex.assert_called_once_with("blocklist:test-jti-123", 3600, "true")

    def test_is_token_blacklisted_true(self):
        from app.utils.cache import is_token_blacklisted
        with patch("app.utils.cache.get_redis_client") as mock_r:
            mock_client = MagicMock()
            mock_client.exists.return_value = 1
            mock_r.return_value = mock_client
            assert is_token_blacklisted("test-jti-456") is True

    def test_is_token_blacklisted_false(self):
        from app.utils.cache import is_token_blacklisted
        with patch("app.utils.cache.get_redis_client") as mock_r:
            mock_client = MagicMock()
            mock_client.exists.return_value = 0
            mock_r.return_value = mock_client
            assert is_token_blacklisted("test-jti-789") is False

    def test_get_problem_hash_deterministic(self):
        from app.utils.cache import get_problem_hash
        h1 = get_problem_hash("Given an array of integers...")
        h2 = get_problem_hash("Given an array of integers...")
        assert h1 == h2

    def test_get_problem_hash_normalises_whitespace(self):
        from app.utils.cache import get_problem_hash
        h1 = get_problem_hash("  Given an array  ")
        h2 = get_problem_hash("given an array")
        assert h1 == h2

    def test_get_problem_hash_different_problems(self):
        from app.utils.cache import get_problem_hash
        h1 = get_problem_hash("Problem A")
        h2 = get_problem_hash("Problem B")
        assert h1 != h2

    def test_get_problem_hash_length(self):
        from app.utils.cache import get_problem_hash
        h = get_problem_hash("Any problem text")
        assert len(h) == 64  # SHA-256 hex digest
