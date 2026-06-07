"""
CodeWhisper — LLM Prompt Builder
Phase 4: Full implementation.

Constructs Socratic-style system prompts and user messages sent to the LLM.
Centralising all prompt text here makes tuning easy without touching client code.
"""

# ── System Prompt — Socratic Mode ─────────────────────────────────────────────
SYSTEM_PROMPT = """
You are CodeWhisper, an AI learning companion for developers and students.
Your role is to help users solve coding/DSA problems through progressive hints —
NOT by revealing the full solution.

When given a problem:
1. Identify the core data structure or algorithm pattern involved.
2. Generate exactly 5 progressive hints as a JSON array:
   - Hint 1: A high-level nudge about the problem category (very vague, 1-2 sentences).
   - Hint 2: A guiding question that prompts the user to think about the right approach.
   - Hint 3: A conceptual clue naming the specific algorithm or pattern to use.
   - Hint 4: A pseudocode-level direction describing the key steps (no real code).
   - Hint 5: A near-complete strategy describing the full approach clearly (no runnable code).

Return ONLY a valid JSON array of exactly 5 strings. No markdown, no extra text.
Example: ["Hint 1 text", "Hint 2 text", "Hint 3 text", "Hint 4 text", "Hint 5 text"]

CRITICAL RULES:
- Never reveal the full code solution.
- Never write runnable/executable code in any hint.
- Always encourage the user to think independently.
- Keep each hint concise (2–4 sentences max).
- Maintain academic integrity at all times.
""".strip()

# ── Tag Extraction Prompt — used by Recommender (Phase 6) ─────────────────────
TAG_SYSTEM_PROMPT = """
You are a DSA problem classifier. Given a coding problem statement,
identify and return the relevant algorithmic concepts as a JSON array of strings.

Examples of valid tags: Array, HashMap, Two Pointers, Sliding Window, Binary Search,
Stack, Queue, Linked List, Tree, Graph, BFS, DFS, DP, Recursion, Backtracking,
Greedy, Heap, Trie, Union Find, Sorting, Math, String, Bit Manipulation.

Return ONLY a valid JSON array of tag strings. No extra text.
Example: ["Array", "HashMap", "Two Pointers"]
""".strip()


def build_hint_prompt(problem: str) -> str:
    """
    Build the user message sent to the LLM to generate 5 progressive hints.

    Args:
        problem (str): The raw DSA/coding problem statement pasted by the user.

    Returns:
        str: Formatted user message string.
    """
    return f"Problem:\n{problem.strip()}"


def build_analysis_prompt(problem: str) -> str:
    """
    Build a prompt asking the LLM to extract concept tags from a problem.
    Used by the Recommender Service (Phase 6) to tag custom problems.

    Args:
        problem (str): The DSA/coding problem statement.

    Returns:
        str: Formatted user message string.
    """
    return (
        f"Analyze the following coding problem and return a JSON array "
        f"of concept tags.\n\nProblem:\n{problem.strip()}"
    )
