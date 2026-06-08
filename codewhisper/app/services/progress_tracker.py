"""
CodeWhisper — Progress Tracker Service
Phase 6 + fix: Top concepts work even for custom-pasted problems (no problem_id).
"""

import logging
import re
import uuid as _uuid
from collections import Counter
from datetime import datetime, timezone

from flask import abort

from app.extensions import db
from app.models.session import UserProblemSession

logger = logging.getLogger(__name__)

# ── Keyword → Tag mapping for custom problems ──────────────────────────────────
# When a session has no problem_id, we extract tags from the problem text itself
KEYWORD_TAGS = {
    "array":           "Array",
    "subarray":        "Array",
    "hashmap":         "HashMap",
    "hash map":        "HashMap",
    "dictionary":      "HashMap",
    "two pointer":     "Two Pointers",
    "two sum":         "HashMap",
    "sliding window":  "Sliding Window",
    "binary search":   "Binary Search",
    "sorted":          "Binary Search",
    "stack":           "Stack",
    "queue":           "Queue",
    "linked list":     "Linked List",
    "tree":            "Tree",
    "binary tree":     "Tree",
    "bst":             "BST",
    "graph":           "Graph",
    "bfs":             "BFS",
    "breadth":         "BFS",
    "dfs":             "DFS",
    "depth":           "DFS",
    "dynamic programming": "DP",
    "dp":              "DP",
    "memoization":     "DP",
    "recursion":       "Recursion",
    "backtracking":    "Backtracking",
    "greedy":          "Greedy",
    "heap":            "Heap",
    "priority queue":  "Heap",
    "trie":            "Trie",
    "string":          "String",
    "palindrome":      "String",
    "subsequence":     "DP",
    "subset":          "Backtracking",
    "permutation":     "Backtracking",
    "interval":        "Intervals",
    "merge":           "Sorting",
    "sort":            "Sorting",
    "matrix":          "Matrix",
    "grid":            "Matrix",
    "island":          "Graph",
    "path":            "Graph",
    "cycle":           "Graph",
    "topological":     "Graph",
    "bit":             "Bit Manipulation",
    "xor":             "Bit Manipulation",
    "math":            "Math",
    "number":          "Math",
    "prime":           "Math",
}


def _extract_tags_from_text(text: str) -> list[str]:
    """Extract concept tags from problem text using keyword matching."""
    if not text:
        return []
    text_lower = text.lower()
    found = set()
    for keyword, tag in KEYWORD_TAGS.items():
        if keyword in text_lower:
            found.add(tag)
    return list(found)


def _try_match_problem_bank(problem_text: str) -> list[str]:
    """Try to find a matching problem in the DB by title similarity."""
    if not problem_text:
        return []
    try:
        from app.models.problem import Problem
        # Check if any seeded problem's title appears in the pasted text
        problems = Problem.query.filter(Problem.tags.isnot(None)).all()
        text_lower = problem_text.lower()
        for p in problems:
            if p.title and p.title.lower() in text_lower:
                return p.tags or []
        return []
    except Exception:
        return []


class ProgressTrackerService:

    def get_history(self, user_id: str, page: int = 1, per_page: int = 20) -> dict:
        uid      = self._parse_uuid(user_id)
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

    def get_stats(self, user_id: str) -> dict:
        uid      = self._parse_uuid(user_id)
        sessions = UserProblemSession.query.filter_by(user_id=uid).all()
        total    = len(sessions)
        solved   = sum(1 for s in sessions if s.is_solved)
        avg_hints = round(sum(s.hints_requested for s in sessions) / total, 2) if total else 0.0
        solve_rate = f"{round((solved / total) * 100, 1)}%" if total else "0%"
        top_tags   = self._compute_top_tags(sessions, top_n=5)
        return {
            "total_attempted":           total,
            "total_solved":              solved,
            "solve_rate":                solve_rate,
            "average_hints_per_problem": avg_hints,
            "top_tags":                  top_tags,
        }

    def mark_solved(self, session_id: str, user_id: str) -> dict:
        session = self._get_session(session_id, user_id)
        if session.is_solved:
            return {
                "session_id": str(session.id),
                "message":    "Problem was already marked as solved.",
                "solved_at":  session.solved_at.isoformat() if session.solved_at else None,
            }
        session.is_solved  = True
        session.solved_at  = datetime.now(timezone.utc)
        db.session.commit()
        return {
            "session_id": str(session.id),
            "message":    "🎉 Problem marked as solved! Great work.",
            "solved_at":  session.solved_at.isoformat(),
        }

    def get_concept_breakdown(self, user_id: str) -> list[dict]:
        uid      = self._parse_uuid(user_id)
        sessions = UserProblemSession.query.filter_by(user_id=uid).all()
        tag_counter: Counter = Counter()

        for s in sessions:
            tags = []

            # Priority 1: tags from linked Problem in DB
            if s.problem and s.problem.tags:
                tags = s.problem.tags

            # Priority 2: match problem_text against the problem bank
            elif s.problem_text:
                tags = _try_match_problem_bank(s.problem_text)

            # Priority 3: extract tags from problem_text using keywords
            if not tags and s.problem_text:
                tags = _extract_tags_from_text(s.problem_text)

            tag_counter.update(tags)

        return [{"tag": tag, "count": count} for tag, count in tag_counter.most_common()]

    # ── Private helpers ────────────────────────────────────────────────────────

    def _get_session(self, session_id: str, user_id: str) -> UserProblemSession:
        sid = self._parse_uuid(session_id)
        uid = self._parse_uuid(user_id)
        s   = UserProblemSession.query.filter_by(id=sid, user_id=uid).first()
        if not s:
            abort(404, description="Session not found.")
        return s

    @staticmethod
    def _parse_uuid(value: str) -> _uuid.UUID:
        try:
            return _uuid.UUID(str(value))
        except (ValueError, AttributeError):
            abort(404, description="Invalid ID format.")

    @staticmethod
    def _compute_top_tags(sessions: list, top_n: int = 5) -> list[str]:
        tag_counter: Counter = Counter()
        for s in sessions:
            tags = []
            # From linked problem
            if s.problem and s.problem.tags:
                tags = s.problem.tags
            # From problem bank match
            elif s.problem_text:
                tags = _try_match_problem_bank(s.problem_text)
            # From keyword extraction
            if not tags and s.problem_text:
                tags = _extract_tags_from_text(s.problem_text)
            tag_counter.update(tags)
        return [tag for tag, _ in tag_counter.most_common(top_n)]
