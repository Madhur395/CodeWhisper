"""
CodeWhisper — Hint Engine Service
Phase 5: Full implementation.

Orchestrates the full hint lifecycle:
  1. Problem hashing → Redis cache lookup
  2. Cache MISS → LLM call → cache result
  3. DB session creation
  4. Progressive hint delivery via Redis index pointer
  5. HintLog persistence for every delivered hint
  6. Graceful exhaustion & error handling

The service is stateless (all state lives in Redis + PostgreSQL),
so it can be safely instantiated per-request.
"""

import logging
import uuid as _uuid

from flask import abort

from app.extensions import db
from app.llm import get_llm_client
from app.models.hint_log import HintLog
from app.models.session import UserProblemSession
from app.utils.cache import (
    cache_hints,
    clear_session_hint_index,
    get_cached_hints,
    get_problem_hash,
    get_session_hint_index,
    store_session_hint_index,
)
from app.utils.problem_tags import find_problem_for_text

logger = logging.getLogger(__name__)

# Maximum number of progressive hints per problem session
MAX_HINTS = 5


def _normalize_hints(hints: list | None) -> list[str]:
    """
    Ensure exactly MAX_HINTS non-empty hint strings.
    Pads with generic fallbacks when the LLM or cache returns fewer than 5.
    """
    from app.llm.groq_client import FALLBACK_HINTS

    valid: list[str] = []
    if hints:
        valid = [h.strip() for h in hints if isinstance(h, str) and h.strip()]
    while len(valid) < MAX_HINTS:
        valid.append(FALLBACK_HINTS[len(valid) % len(FALLBACK_HINTS)])
    return valid[:MAX_HINTS]


class HintEngineService:
    """
    Core service that drives CodeWhisper's progressive hint system.

    Methods
    -------
    start_session(user_id, problem_text) → dict
        Begin a new hint session: cache-or-generate hints, create DB record,
        store hint index in Redis, log + return Hint #1.

    get_next_hint(session_id, user_id) → dict
        Advance the hint pointer and return the next hint from cache.
        Returns an exhausted payload when all hints have been delivered.

    get_session_hints(session_id, user_id) → list[dict]
        Return all hints delivered so far for the given session.

    reset_session(session_id, user_id) → dict
        Clear Redis hint index so the user can restart from Hint #1.
    """

    def __init__(self):
        self._llm_client = get_llm_client()

    # ── start_session ──────────────────────────────────────────────────────────

    def start_session(self, user_id: str, problem_text: str) -> dict:
        """
        Start a new hint session for a DSA problem.

        Flow:
          1. Normalise & hash the problem text.
          2. Check Redis for a cached hint sequence.
          3. On cache MISS → call LLM → store in Redis.
          4. Create a UserProblemSession row in PostgreSQL.
          5. Store hint pointer (index=1) in Redis.
          6. Persist HintLog(level=1) in PostgreSQL.
          7. Return session_id + Hint #1.

        Args:
            user_id  (str): UUID string of the authenticated user.
            problem_text (str): Raw DSA problem pasted by the user.

        Returns:
            dict: {session_id, hint_level, hint, total_hints}
        """
        problem_hash = get_problem_hash(problem_text)

        # ── Step 1: Cache lookup ──────────────────────────────────────────────
        hints = get_cached_hints(problem_hash)
        cache_hit = hints is not None

        # ── Step 2: Cache MISS → call LLM ────────────────────────────────────
        if not cache_hit:
            logger.info("Cache MISS for hash=%s — calling LLM", problem_hash[:12])
            hints = self._llm_client.generate_hints(problem_text)
        else:
            logger.info("Cache HIT for hash=%s — skipping LLM call", problem_hash[:12])

        hints = _normalize_hints(hints)
        cache_hints(problem_hash, hints)

        # Defensive: ensure we have something to return
        if not hints:
            logger.error("Hint list is empty after LLM call — aborting")
            abort(500, description="Failed to generate hints. Please try again.")

        # ── Step 3: Persist session ───────────────────────────────────────────
        matched_problem = find_problem_for_text(problem_text)
        session = UserProblemSession(
            user_id=_uuid.UUID(user_id) if isinstance(user_id, str) else user_id,
            problem_id=matched_problem.id if matched_problem else None,
            problem_text=problem_text,
            hints_requested=1,
            current_hint_level=1,
        )
        db.session.add(session)
        db.session.commit()
        logger.debug("Created session id=%s for user=%s", session.id, user_id)

        # ── Step 4: Persist hint index in Redis ───────────────────────────────
        # Index represents "next hint to deliver" (1-based already consumed)
        store_session_hint_index(str(session.id), 1)

        # ── Step 5: Log Hint #1 to DB ─────────────────────────────────────────
        hint_log = HintLog(
            session_id=session.id,
            hint_level=1,
            hint_text=hints[0],
        )
        db.session.add(hint_log)
        db.session.commit()

        return {
            "session_id": str(session.id),
            "hint_level": 1,
            "hint": hints[0],
            "total_hints": len(hints),
            "exhausted": False,
        }

    # ── get_next_hint ──────────────────────────────────────────────────────────

    def get_next_hint(self, session_id: str, user_id: str) -> dict:
        """
        Deliver the next progressive hint for an existing session.

        Flow:
          1. Load session from DB (404 if not found or not owned by user).
          2. Retrieve current hint index from Redis.
          3. If index >= MAX_HINTS → return exhausted payload (no DB changes).
          4. Fetch hint from Redis cache (regenerate if cache expired).
          5. Advance the Redis index pointer.
          6. Update session counters in DB.
          7. Persist HintLog for the new hint level.
          8. Return the hint payload.

        Args:
            session_id (str): UUID string of the session.
            user_id    (str): UUID string of the authenticated user.

        Returns:
            dict: {session_id, hint_level, hint, total_hints, exhausted}
                  or {message, exhausted: True} when all hints delivered.
        """
        # ── Step 1: Load + authorise session ─────────────────────────────────
        session = self._get_session(session_id, user_id)

        # ── Step 2: Current pointer from Redis ───────────────────────────────
        current_index = get_session_hint_index(session_id)
        logger.debug(
            "get_next_hint: session=%s current_index=%d", session_id[:8], current_index
        )

        # ── Step 3: Exhaustion check ──────────────────────────────────────────
        if current_index >= MAX_HINTS:
            return {
                "session_id": session_id,
                "message": "You've seen all available hints! Try solving it now. 💪",
                "exhausted": True,
                "hint_level": current_index,
                "total_hints": MAX_HINTS,
            }

        # ── Step 4: Fetch hints from cache (re-generate if stale) ────────────
        problem_hash = get_problem_hash(session.problem_text)
        hints = get_cached_hints(problem_hash)

        if hints is None:
            # Cache evicted (TTL expired) — regenerate without extra LLM cost
            logger.warning(
                "Hint cache expired for session=%s — regenerating", session_id[:8]
            )
            hints = self._llm_client.generate_hints(session.problem_text)
            cache_hints(problem_hash, hints)

        hints = _normalize_hints(hints)
        cache_hints(problem_hash, hints)

        # Safety guard (should not trigger after normalization)
        if current_index >= len(hints):
            return {
                "session_id": session_id,
                "message": "You've seen all available hints! Try solving it now. 💪",
                "exhausted": True,
                "hint_level": current_index,
                "total_hints": len(hints),
            }

        next_hint_text = hints[current_index]
        next_index = current_index + 1

        # ── Step 5: Advance Redis pointer ────────────────────────────────────
        store_session_hint_index(session_id, next_index)

        # ── Step 6: Update session counters in DB ─────────────────────────────
        session.hints_requested = (session.hints_requested or 0) + 1
        session.current_hint_level = next_index
        db.session.commit()

        # ── Step 7: Persist HintLog ───────────────────────────────────────────
        hint_log = HintLog(
            session_id=session.id,
            hint_level=next_index,
            hint_text=next_hint_text,
        )
        db.session.add(hint_log)
        db.session.commit()

        exhausted = next_index >= MAX_HINTS
        logger.debug(
            "Delivered hint level=%d exhausted=%s session=%s",
            next_index, exhausted, session_id[:8],
        )

        return {
            "session_id": session_id,
            "hint_level": next_index,
            "hint": next_hint_text,
            "total_hints": len(hints),
            "exhausted": exhausted,
        }

    # ── get_session_hints ──────────────────────────────────────────────────────

    def get_session_hints(self, session_id: str, user_id: str) -> list[dict]:
        """
        Return all hints delivered so far for a session, ordered by hint_level.

        Args:
            session_id (str): UUID string of the session.
            user_id    (str): UUID string of the authenticated user.

        Returns:
            list[dict]: [{level, hint, delivered_at}, ...]
        """
        session = self._get_session(session_id, user_id)

        logs = (
            HintLog.query
            .filter_by(session_id=session.id)
            .order_by(HintLog.hint_level)
            .all()
        )
        return [
            {
                "level": h.hint_level,
                "hint": h.hint_text,
                "delivered_at": h.delivered_at.isoformat() if h.delivered_at else None,
            }
            for h in logs
        ]

    # ── reset_session ──────────────────────────────────────────────────────────

    def reset_session(self, session_id: str, user_id: str) -> dict:
        """
        Reset a session's hint pointer back to the beginning.

        Clears the Redis index so the user will receive Hint #1 again
        on the next get_next_hint() call.  Does NOT delete hint logs.

        Args:
            session_id (str): UUID string of the session.
            user_id    (str): UUID string of the authenticated user.

        Returns:
            dict: {session_id, message}
        """
        session = self._get_session(session_id, user_id)
        clear_session_hint_index(session_id)

        # Delete existing hint logs so levels can be re-delivered without
        # hitting the (session_id, hint_level) unique constraint
        HintLog.query.filter_by(session_id=session.id).delete()

        # Reset DB counters
        session.hints_requested = 0
        session.current_hint_level = 0
        db.session.commit()

        return {
            "session_id": session_id,
            "message": "Session reset. You'll start from Hint #1 again.",
        }

    # ── Private helpers ────────────────────────────────────────────────────────

    def _get_session(self, session_id: str, user_id: str) -> UserProblemSession:
        """
        Load a UserProblemSession owned by `user_id`.

        Accepts both string UUIDs and UUID objects for both arguments.
        Returns 404 if the session doesn't exist or belongs to another user.

        Args:
            session_id (str | UUID): Session primary key.
            user_id    (str | UUID): Requesting user's primary key.

        Returns:
            UserProblemSession
        """
        try:
            sid = _uuid.UUID(str(session_id))
            uid = _uuid.UUID(str(user_id))
        except ValueError:
            abort(404, description="Invalid session or user ID.")

        session = UserProblemSession.query.filter_by(id=sid, user_id=uid).first()
        if session is None:
            abort(404, description="Session not found.")
        return session
