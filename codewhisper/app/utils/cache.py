"""
CodeWhisper — Redis Cache Utilities
Falls back to an in-memory dict when Redis is unavailable (standalone dev mode).
"""

import os
import hashlib
import json
import logging

logger = logging.getLogger(__name__)

# ── In-memory fallback store ──────────────────────────────────────────────────
_mem_store: dict = {}

# ── Redis client (lazy singleton) ─────────────────────────────────────────────
_redis_client = None
_redis_available = None          # None = untested, True/False after first ping


def get_redis_client():
    global _redis_client, _redis_available
    if _redis_client is None:
        try:
            import redis
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            _redis_client = redis.from_url(redis_url, decode_responses=True,
                                           socket_connect_timeout=1)
            _redis_client.ping()
            _redis_available = True
            logger.debug("Redis connected at %s", redis_url)
        except Exception as exc:
            logger.warning("Redis unavailable (%s) — using in-memory fallback", exc)
            _redis_available = False
            _redis_client = None
    return _redis_client if _redis_available else None


def _r():
    return get_redis_client()


# ── Generic get/set/delete with memory fallback ────────────────────────────────

def _setex(key: str, ttl: int, value: str):
    rc = _r()
    if rc:
        try:
            rc.setex(key, int(ttl), value)
            return
        except Exception:
            pass
    _mem_store[key] = value


def _get(key: str):
    rc = _r()
    if rc:
        try:
            return rc.get(key)
        except Exception:
            pass
    return _mem_store.get(key)


def _exists(key: str) -> int:
    rc = _r()
    if rc:
        try:
            return rc.exists(key)
        except Exception:
            pass
    return 1 if key in _mem_store else 0


def _delete(key: str):
    rc = _r()
    if rc:
        try:
            rc.delete(key)
        except Exception:
            pass
    _mem_store.pop(key, None)


# ── Token Blacklisting ────────────────────────────────────────────────────────

def blacklist_token(jti: str, expires_in: int) -> None:
    _setex(f"blocklist:{jti}", int(expires_in), "true")


def is_token_blacklisted(jti: str) -> bool:
    return _exists(f"blocklist:{jti}") == 1


# ── Hint Caching ──────────────────────────────────────────────────────────────

HINT_CACHE_TTL = 60 * 60 * 24   # 24 hours


def get_problem_hash(problem_text: str) -> str:
    normalised = problem_text.strip().lower()
    return hashlib.sha256(normalised.encode("utf-8")).hexdigest()


def cache_hints(problem_hash: str, hints: list) -> None:
    _setex(f"hints:{problem_hash}", HINT_CACHE_TTL, json.dumps(hints))


def get_cached_hints(problem_hash: str):
    raw = _get(f"hints:{problem_hash}")
    return json.loads(raw) if raw else None


# ── Session Hint Index ────────────────────────────────────────────────────────

SESSION_HINT_TTL = 60 * 60   # 1 hour


def store_session_hint_index(session_id: str, index: int) -> None:
    _setex(f"session:{session_id}:hint_index", SESSION_HINT_TTL, index)


def get_session_hint_index(session_id: str) -> int:
    val = _get(f"session:{session_id}:hint_index")
    return int(val) if val is not None else 0


def clear_session_hint_index(session_id: str) -> None:
    _delete(f"session:{session_id}:hint_index")
