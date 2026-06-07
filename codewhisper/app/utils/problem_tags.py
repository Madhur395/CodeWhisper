"""
CodeWhisper — Problem matching & concept tag resolution
Links pasted problem text to the curated bank and infers tags for custom problems.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.problem import Problem
    from app.models.session import UserProblemSession


def normalize_problem_text(text: str) -> str:
    """Lowercase, collapse whitespace, strip punctuation edges for matching."""
    if not text:
        return ""
    cleaned = re.sub(r"\s+", " ", text.strip().lower())
    return cleaned


def find_problem_for_text(problem_text: str) -> Problem | None:
    """
    Match pasted problem text to a curated Problem row (if close enough).
    """
    from app.models.problem import Problem

    user_norm = normalize_problem_text(problem_text)
    if len(user_norm) < 20:
        return None

    best: Problem | None = None
    best_score = 0

    for problem in Problem.query.all():
        stmt_norm = normalize_problem_text(problem.statement)
        if not stmt_norm:
            continue

        if user_norm == stmt_norm:
            return problem

        score = 0
        if stmt_norm in user_norm or user_norm in stmt_norm:
            score = min(len(stmt_norm), len(user_norm))
        else:
            # Strong signal: opening of the official statement appears in paste
            for length in (80, 60, 40):
                prefix = stmt_norm[:length]
                if len(prefix) >= 40 and prefix in user_norm:
                    score = max(score, length)
                    break

        if score > best_score:
            best_score = score
            best = problem

    return best if best_score >= 40 else None


# Keyword → concept tag (used when no bank match exists)
_TAG_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("Array", ("array", "nums", "subarray", "elements", "indices")),
    ("HashMap", ("hash map", "hashmap", "dictionary", "frequency map")),
    ("HashSet", ("hash set", "hashset", "duplicate", "distinct")),
    ("Two Pointers", ("two pointer", "two pointers", "left and right")),
    ("Sliding Window", ("sliding window", "subarray of size", "contiguous")),
    ("Binary Search", ("binary search", "sorted array", "search space")),
    ("Stack", ("stack", "lifo", "parentheses", "valid parentheses")),
    ("Queue", ("queue", "bfs", "breadth-first")),
    ("Linked List", ("linked list", "listnode", "next pointer")),
    ("Tree", ("binary tree", "root node", "subtree", "leaf")),
    ("Graph", ("graph", "adjacency", "dfs", "depth-first", "topological")),
    ("Heap", ("heap", "priority queue", "kth largest", "k most frequent")),
    ("DP", ("dynamic programming", "dp", "memoization", "optimal substructure")),
    ("Recursion", ("recursion", "recursive", "backtrack")),
    ("Greedy", ("greedy", "locally optimal")),
    ("String", ("string", "substring", "palindrome", "anagram")),
    ("Math", ("prime", "modulo", "gcd", "divisible")),
    ("Bit Manipulation", ("bitwise", "xor", "binary representation")),
    ("Sorting", ("sort", "sorted", "merge sort", "quick sort")),
    ("Union Find", ("union find", "disjoint set", "connected components")),
]


def infer_tags_from_text(problem_text: str, max_tags: int = 5) -> list[str]:
    """Heuristic concept tags from problem wording (custom / unmatched pastes)."""
    if not problem_text:
        return []
    lower = problem_text.lower()
    tags: list[str] = []
    for tag, keywords in _TAG_KEYWORDS:
        if any(kw in lower for kw in keywords):
            tags.append(tag)
        if len(tags) >= max_tags:
            break
    return tags


def tags_for_session(session: UserProblemSession) -> list[str]:
    """
    Concept tags for a session: linked problem → bank match → keyword inference.
    """
    if session.problem and session.problem.tags:
        return list(session.problem.tags)

    if session.problem_text:
        matched = find_problem_for_text(session.problem_text)
        if matched and matched.tags:
            return list(matched.tags)
        inferred = infer_tags_from_text(session.problem_text)
        if inferred:
            return inferred

    return []
