"""
CodeWhisper — Hint Engine Service
Uses DB (session.current_hint_level) as source of truth for hint pointer.
This works correctly with multiple gunicorn workers and no Redis.
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
)

logger = logging.getLogger(__name__)

MAX_HINTS = 5


class HintEngineService:

    def __init__(self):
        self._llm_client = get_llm_client()

    # ── start_session ──────────────────────────────────────────────────────────

    def start_session(self, user_id: str, problem_text: str) -> dict:
        problem_hash = get_problem_hash(problem_text)

        # Get hints (from cache or LLM)
        hints = get_cached_hints(problem_hash)
        if not hints:
            logger.info("Cache MISS — calling LLM for hints")
            hints = self._llm_client.generate_hints(problem_text)
            if not hints:
                from app.llm.groq_client import FALLBACK_HINTS
                hints = list(FALLBACK_HINTS)
            cache_hints(problem_hash, hints)
        else:
            logger.info("Cache HIT — skipping LLM call")

        # Create session with hint_level=1 in DB
        uid = _uuid.UUID(str(user_id)) if isinstance(user_id, str) else user_id
        session = UserProblemSession(
            user_id=uid,
            problem_text=problem_text,
            hints_requested=1,
            current_hint_level=1,   # DB is source of truth
        )
        db.session.add(session)
        db.session.commit()

        # Log Hint #1
        try:
            hint_log = HintLog(session_id=session.id, hint_level=1, hint_text=hints[0])
            db.session.add(hint_log)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.warning("HintLog #1 skipped (duplicate?): %s", e)

        logger.info("Session %s created, hint 1 delivered", session.id)

        return {
            "session_id":  str(session.id),
            "hint_level":  1,
            "hint":        hints[0],
            "total_hints": len(hints),
            "exhausted":   False,
        }

    # ── get_next_hint ──────────────────────────────────────────────────────────

    def get_next_hint(self, session_id: str, user_id: str) -> dict:
        session = self._get_session(session_id, user_id)

        # current_hint_level stored in DB = last hint delivered
        # next hint to deliver = current_hint_level + 1 (but after start it's already 1)
        # So the NEXT index into the hints list = current_hint_level (0-based array)
        current_level = session.current_hint_level  # e.g. 1 after start_session

        # Exhaustion check
        if current_level >= MAX_HINTS:
            return {
                "session_id":  session_id,
                "hint_level":  current_level,
                "total_hints": MAX_HINTS,
                "exhausted":   True,
                "message":     "You've seen all hints! Try solving it now. 💪",
            }

        # Get hints from cache
        problem_hash = get_problem_hash(session.problem_text)
        hints = get_cached_hints(problem_hash)
        if hints is None:
            logger.warning("Cache expired for session %s — regenerating", session_id[:8])
            hints = self._llm_client.generate_hints(session.problem_text)
            if not hints:
                from app.llm.groq_client import FALLBACK_HINTS
                hints = list(FALLBACK_HINTS)
            cache_hints(problem_hash, hints)

        # Safety: clamp to available hints
        if current_level >= len(hints):
            return {
                "session_id":  session_id,
                "hint_level":  current_level,
                "total_hints": len(hints),
                "exhausted":   True,
                "message":     "You've seen all hints! Try solving it now. 💪",
            }

        # Deliver next hint (current_level is 0-based index into hints list)
        next_hint_text = hints[current_level]
        next_level     = current_level + 1   # 1-based level number

        # Update DB atomically (DB = source of truth, works across all workers)
        session.hints_requested  = (session.hints_requested or 0) + 1
        session.current_hint_level = next_level
        db.session.commit()

        # Log hint (ignore duplicate)
        try:
            hint_log = HintLog(
                session_id=session.id,
                hint_level=next_level,
                hint_text=next_hint_text,
            )
            db.session.add(hint_log)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.warning("HintLog insert skipped (duplicate?): %s", e)

        exhausted = next_level >= MAX_HINTS

        logger.info("Session %s: delivered hint level %d, exhausted=%s",
                    session_id[:8], next_level, exhausted)

        return {
            "session_id":  session_id,
            "hint_level":  next_level,
            "hint":        next_hint_text,
            "total_hints": len(hints),
            "exhausted":   exhausted,
        }

    # ── get_session_hints ──────────────────────────────────────────────────────

    def get_session_hints(self, session_id: str, user_id: str) -> list[dict]:
        session = self._get_session(session_id, user_id)
        logs = (
            HintLog.query
            .filter_by(session_id=session.id)
            .order_by(HintLog.hint_level)
            .all()
        )
        return [
            {
                "level":        h.hint_level,
                "hint":         h.hint_text,
                "delivered_at": h.delivered_at.isoformat() if h.delivered_at else None,
            }
            for h in logs
        ]

    # ── reset_session ──────────────────────────────────────────────────────────

    def reset_session(self, session_id: str, user_id: str) -> dict:
        session = self._get_session(session_id, user_id)

        clear_session_hint_index(session_id)   # clear Redis too if present

        # Delete existing hint logs so unique constraint won't block re-delivery
        HintLog.query.filter_by(session_id=session.id).delete()

        session.hints_requested    = 0
        session.current_hint_level = 0
        db.session.commit()

        return {"session_id": session_id, "message": "Session reset. Starting from Hint #1."}

    # ── private ────────────────────────────────────────────────────────────────

    def _get_session(self, session_id: str, user_id: str) -> UserProblemSession:
        try:
            sid = _uuid.UUID(str(session_id))
            uid = _uuid.UUID(str(user_id))
        except (ValueError, AttributeError):
            abort(404, description="Invalid session or user ID.")
        session = UserProblemSession.query.filter_by(id=sid, user_id=uid).first()
        if session is None:
            abort(404, description="Session not found.")
        return session
