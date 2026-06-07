"""
CodeWhisper — Progress Tracker Service
Phase 6: Full implementation.

Tracks user learning history, computes aggregate stats,
marks sessions as solved, and builds a learning profile
from tag data on attempted problems.
"""

import logging
import uuid as _uuid
from datetime import datetime, timezone
from collections import Counter

from flask import abort

from app.extensions import db
from app.models.session import UserProblemSession
from app.utils.problem_tags import tags_for_session

logger = logging.getLogger(__name__)


class ProgressTrackerService:
    """
    Service layer for all user progress operations.

    Methods
    -------
    get_history(user_id, page, per_page)
        Paginated list of all problem sessions for a user.

    get_stats(user_id)
        Aggregate learning stats: total attempted, solved,
        solve rate, avg hints used, top concept tags.

    mark_solved(session_id, user_id)
        Mark a session as solved with a timestamp.

    get_concept_breakdown(user_id)
        Tag frequency across all sessions with a linked problem.
    """

    # ── get_history ────────────────────────────────────────────────────────────

    def get_history(
        self,
        user_id: str,
        page: int = 1,
        per_page: int = 20,
    ) -> dict:
        """
        Return a paginated list of problem sessions for the given user,
        ordered newest-first.

        Args:
            user_id  (str): UUID of the authenticated user.
            page     (int): Page number (1-based). Default 1.
            per_page (int): Items per page. Default 20, max 100.

        Returns:
            dict: {
                sessions: [...],
                total: int,
                page: int,
                per_page: int,
                pages: int
            }
        """
        uid = self._parse_uuid(user_id)
        per_page = min(per_page, 100)

        pagination = (
            UserProblemSession.query
            .filter_by(user_id=uid)
            .order_by(UserProblemSession.started_at.desc())
            .paginate(page=page, per_page=per_page, error_out=False)
        )

        sessions = [
            {
                "session_id":      str(s.id),
                "problem_preview": (s.problem_text[:120] + "...") if s.problem_text else None,
                "hints_used":      s.hints_requested,
                "current_level":   s.current_hint_level,
                "is_solved":       s.is_solved,
                "started_at":      s.started_at.isoformat() if s.started_at else None,
                "solved_at":       s.solved_at.isoformat() if s.solved_at else None,
            }
            for s in pagination.items
        ]

        return {
            "sessions":  sessions,
            "total":     pagination.total,
            "page":      page,
            "per_page":  per_page,
            "pages":     pagination.pages,
        }

    # ── get_stats ──────────────────────────────────────────────────────────────

    def get_stats(self, user_id: str) -> dict:
        """
        Return aggregate learning statistics for the user.

        Stats included:
            - total_attempted  : total sessions started
            - total_solved     : sessions marked as solved
            - solve_rate       : "X.X%" string
            - average_hints_per_problem : float rounded to 2dp
            - top_tags         : top-5 concept tags across all sessions
              (derived from linked Problem.tags; excludes custom-only sessions)

        Args:
            user_id (str): UUID of the authenticated user.

        Returns:
            dict: statistics payload.
        """
        uid = self._parse_uuid(user_id)

        sessions = (
            UserProblemSession.query
            .filter_by(user_id=uid)
            .all()
        )

        total  = len(sessions)
        solved = sum(1 for s in sessions if s.is_solved)
        avg_hints = (
            round(sum(s.hints_requested for s in sessions) / total, 2)
            if total else 0.0
        )
        solve_rate = (
            f"{round((solved / total) * 100, 1)}%" if total else "0%"
        )

        # Build top-tags from linked problems
        top_tags = self._compute_top_tags(sessions, top_n=5)

        return {
            "total_attempted":           total,
            "total_solved":              solved,
            "solve_rate":                solve_rate,
            "average_hints_per_problem": avg_hints,
            "top_tags":                  top_tags,
        }

    # ── mark_solved ────────────────────────────────────────────────────────────

    def mark_solved(self, session_id: str, user_id: str) -> dict:
        """
        Mark a session as solved and record the solve timestamp.

        Args:
            session_id (str): UUID of the session to mark.
            user_id    (str): UUID of the owning user (authorisation check).

        Returns:
            dict: {session_id, message, solved_at}

        Raises:
            404: Session not found or not owned by this user.
        """
        session = self._get_session(session_id, user_id)

        if session.is_solved:
            # Idempotent — already solved
            return {
                "session_id": str(session.id),
                "message":    "Problem was already marked as solved.",
                "solved_at":  session.solved_at.isoformat() if session.solved_at else None,
            }

        session.is_solved = True
        session.solved_at = datetime.now(timezone.utc)
        db.session.commit()

        logger.info("Session %s marked as solved by user %s", session_id, user_id)

        return {
            "session_id": str(session.id),
            "message":    "🎉 Problem marked as solved! Great work.",
            "solved_at":  session.solved_at.isoformat(),
        }

    # ── get_concept_breakdown ──────────────────────────────────────────────────

    def get_concept_breakdown(self, user_id: str) -> list[dict]:
        """
        Return tag frequency counts across all of the user's sessions
        that are linked to a Problem with tags.

        Args:
            user_id (str): UUID of the authenticated user.

        Returns:
            list[dict]: [{tag, count}, ...] sorted by count desc.
        """
        uid = self._parse_uuid(user_id)
        sessions = (
            UserProblemSession.query
            .filter_by(user_id=uid)
            .all()
        )
        tag_counter = Counter()
        for s in sessions:
            session_tags = tags_for_session(s)
            if session_tags:
                tag_counter.update(session_tags)

        return [
            {"tag": tag, "count": count}
            for tag, count in tag_counter.most_common()
        ]

    # ── Private helpers ────────────────────────────────────────────────────────

    def _get_session(
        self, session_id: str, user_id: str
    ) -> UserProblemSession:
        """Load a session owned by user_id; abort 404 otherwise."""
        sid = self._parse_uuid(session_id)
        uid = self._parse_uuid(user_id)
        session = UserProblemSession.query.filter_by(id=sid, user_id=uid).first()
        if not session:
            abort(404, description="Session not found.")
        return session

    @staticmethod
    def _parse_uuid(value: str) -> _uuid.UUID:
        """Parse a UUID string; abort 404 on invalid format."""
        try:
            return _uuid.UUID(str(value))
        except (ValueError, AttributeError):
            abort(404, description="Invalid ID format.")

    @staticmethod
    def _compute_top_tags(
        sessions: list[UserProblemSession], top_n: int = 5
    ) -> list[str]:
        """Collect tags from linked problems and return the top N."""
        tag_counter: Counter = Counter()
        for s in sessions:
            session_tags = tags_for_session(s)
            if session_tags:
                tag_counter.update(session_tags)
        return [tag for tag, _ in tag_counter.most_common(top_n)]
