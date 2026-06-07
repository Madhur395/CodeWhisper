"""
CodeWhisper — Recommender Service
Phase 6: Full implementation.

Tag-based problem recommendation engine:
  1. Collects tags from the user's attempted/solved sessions.
  2. Scores unseen problems by tag overlap with the user's profile.
  3. Falls back to any unseen problem when no tag data is available.
  4. Returns a ranked, de-duplicated list of problem cards.
"""

import logging
import random
import uuid as _uuid
from collections import Counter

from app.models.problem import Problem
from app.models.session import UserProblemSession
from app.utils.problem_tags import tags_for_session

logger = logging.getLogger(__name__)


class RecommenderService:
    """
    Recommends unseen DSA problems to the user based on the concept tags
    from their previously attempted and solved problem sessions.

    The algorithm (Phase 6: tag-based filtering + overlap scoring):
        1. Collect all problem_ids the user has attempted.
        2. Build a "user tag profile" from those problems' tags.
        3. Fetch all problems NOT yet attempted.
        4. Score each candidate by counting overlapping tags.
        5. Sort by score (desc) → return top `limit`.
        6. Shuffle same-score items for variety.
        7. Fall back to random unseen problems if no tag profile exists.

    Future enhancement (Phase 9+): collaborative filtering using
    embedding similarity (e.g. sentence-transformers).
    """

    # ── recommend ──────────────────────────────────────────────────────────────

    def recommend(self, user_id: str, limit: int = 5) -> list[dict]:
        """
        Return up to `limit` recommended problems for the user.

        Args:
            user_id (str): UUID of the authenticated user.
            limit   (int): Max number of recommendations. Default 5.

        Returns:
            list[dict]: Problem card dicts, best match first.
        """
        uid = self._parse_uuid(user_id)
        limit = max(1, min(limit, 20))  # clamp to [1, 20]

        # ── Step 1: Collect solved problem IDs (exclude from Discover) ───────
        # Only hide problems the user marked solved — not every hint session,
        # otherwise the bank drains to 0–2 items after casual testing.
        sessions = UserProblemSession.query.filter_by(user_id=uid).all()

        excluded_ids = {
            s.problem_id
            for s in sessions
            if s.problem_id is not None and s.is_solved
        }

        # ── Step 2: Build user tag profile ───────────────────────────────────
        tag_profile: Counter = Counter()
        for s in sessions:
            session_tags = tags_for_session(s)
            if session_tags:
                tag_profile.update(session_tags)

        logger.debug(
            "User %s solved_excluded=%d tag_profile=%s",
            user_id, len(excluded_ids), dict(tag_profile.most_common(5))
        )

        # ── Step 3: Fetch problems not yet solved ───────────────────────────
        candidates_query = Problem.query
        if excluded_ids:
            candidates_query = candidates_query.filter(
                Problem.id.notin_(list(excluded_ids))
            )
        candidates = candidates_query.all()

        if not candidates:
            logger.info("No unseen problems available for user %s", user_id)
            return []

        # ── Step 4 & 5: Score, shuffle a wider pool, then pick `limit` ───────
        if tag_profile:
            ranked = self._score_problems(candidates, tag_profile)
        else:
            ranked = list(candidates)
            random.shuffle(ranked)

        pool_size = min(len(ranked), max(limit * 4, limit + 8))
        pool = list(ranked[:pool_size])
        random.shuffle(pool)

        # ── Step 6: Serialise ─────────────────────────────────────────────────
        return [self._to_card(p) for p in pool[:limit]]

    # ── Private helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _score_problems(
        candidates: list[Problem],
        tag_profile: Counter,
    ) -> list[Problem]:
        """
        Score each candidate problem by tag overlap with the user's profile.
        Problems with the same score are shuffled for variety.

        Returns:
            list[Problem]: Sorted best-first (descending score).
        """
        def _overlap(problem: Problem) -> int:
            if not problem.tags:
                return 0
            return sum(tag_profile.get(tag, 0) for tag in problem.tags)

        # Group by score, shuffle within each group, then flatten
        from itertools import groupby

        scored_pairs = sorted(
            [(p, _overlap(p)) for p in candidates],
            key=lambda x: x[1],
            reverse=True,
        )

        result: list[Problem] = []
        for _score, group in groupby(scored_pairs, key=lambda x: x[1]):
            group_list = [p for p, _ in group]
            random.shuffle(group_list)
            result.extend(group_list)

        return result

    @staticmethod
    def _to_card(problem: Problem) -> dict:
        """Serialise a Problem to a recommendation card dict."""
        return {
            "problem_id": str(problem.id),
            "title":      problem.title,
            "difficulty": problem.difficulty,
            "tags":       problem.tags or [],
            "source":     problem.source,
            "statement_preview": (
                (problem.statement[:200] + "...") if problem.statement else None
            ),
        }

    @staticmethod
    def _parse_uuid(value: str) -> _uuid.UUID:
        """Parse UUID string; returns a default UUID on failure (no 404 here)."""
        try:
            return _uuid.UUID(str(value))
        except (ValueError, AttributeError):
            # Return a random UUID that will match nothing in the DB
            return _uuid.uuid4()
