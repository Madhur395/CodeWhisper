"""
CodeWhisper — Problem Bank Seed Script
Phase 6: Full implementation — 55 curated DSA problems.

Usage (from project root, with venv active):
    python scripts/seed_problems.py

Or inside Docker:
    docker-compose exec web python scripts/seed_problems.py

The script is idempotent: it skips any problem whose title already exists
in the database, so it is safe to run multiple times.
"""

import sys
import os

# ── Make sure the app package is importable ───────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── Problem Bank (55 curated problems) ───────────────────────────────────────
PROBLEMS = [
    # ── Arrays & Hashing ──────────────────────────────────────────────────────
    {
        "title": "Two Sum",
        "statement": (
            "Given an array of integers nums and an integer target, "
            "return indices of the two numbers such that they add up to target. "
            "You may assume each input has exactly one solution, "
            "and you may not use the same element twice."
        ),
        "tags": ["Array", "HashMap"],
        "difficulty": "Easy",
        "source": "LeetCode",
    },
    {
        "title": "Contains Duplicate",
        "statement": (
            "Given an integer array nums, return true if any value appears "
            "at least twice in the array, and return false if every element is distinct."
        ),
        "tags": ["Array", "HashSet"],
        "difficulty": "Easy",
        "source": "LeetCode",
    },
    {
        "title": "Product of Array Except Self",
        "statement": (
            "Given an integer array nums, return an array answer such that "
            "answer[i] is equal to the product of all the elements of nums "
            "except nums[i]. You must solve it without using the division operation."
        ),
        "tags": ["Array", "Prefix Sum"],
        "difficulty": "Medium",
        "source": "LeetCode",
    },
    {
        "title": "Top K Frequent Elements",
        "statement": (
            "Given an integer array nums and an integer k, return the k most "
            "frequent elements. You may return the answer in any order."
        ),
        "tags": ["Array", "HashMap", "Heap"],
        "difficulty": "Medium",
        "source": "LeetCode",
    },
    {
        "title": "Group Anagrams",
        "statement": (
            "Given an array of strings strs, group the anagrams together. "
            "You can return the answer in any order."
        ),
        "tags": ["Array", "HashMap", "String", "Sorting"],
        "difficulty": "Medium",
        "source": "LeetCode",
    },

    # ── Sliding Window ────────────────────────────────────────────────────────
    {
        "title": "Longest Substring Without Repeating Characters",
        "statement": (
            "Given a string s, find the length of the longest substring "
            "without repeating characters."
        ),
        "tags": ["Sliding Window", "String", "HashMap"],
        "difficulty": "Medium",
        "source": "LeetCode",
    },
    {
        "title": "Minimum Window Substring",
        "statement": (
            "Given two strings s and t of lengths m and n respectively, return "
            "the minimum window substring of s such that every character in t "
            "(including duplicates) is included in the window."
        ),
        "tags": ["Sliding Window", "String"],
        "difficulty": "Hard",
        "source": "LeetCode",
    },
    {
        "title": "Permutation in String",
        "statement": (
            "Given two strings s1 and s2, return true if s2 contains a permutation of s1, "
            "or false otherwise. In other words, return true if one of s1's permutations "
            "is the substring of s2."
        ),
        "tags": ["Sliding Window", "String", "HashMap"],
        "difficulty": "Medium",
        "source": "LeetCode",
    },
    {
        "title": "Best Time to Buy and Sell Stock",
        "statement": (
            "You are given an array prices where prices[i] is the price of a given stock "
            "on the ith day. Return the maximum profit you can achieve from this transaction."
        ),
        "tags": ["Sliding Window", "Array", "DP"],
        "difficulty": "Easy",
        "source": "LeetCode",
    },

    # ── Two Pointers ──────────────────────────────────────────────────────────
    {
        "title": "Valid Palindrome",
        "statement": (
            "A phrase is a palindrome if, after converting all uppercase letters "
            "into lowercase letters and removing all non-alphanumeric characters, "
            "it reads the same forward and backward."
        ),
        "tags": ["Two Pointers", "String"],
        "difficulty": "Easy",
        "source": "LeetCode",
    },
    {
        "title": "3Sum",
        "statement": (
            "Given an integer array nums, return all the triplets [nums[i], nums[j], nums[k]] "
            "such that i != j, i != k, and j != k, and nums[i] + nums[j] + nums[k] == 0."
        ),
        "tags": ["Two Pointers", "Array", "Sorting"],
        "difficulty": "Medium",
        "source": "LeetCode",
    },
    {
        "title": "Container With Most Water",
        "statement": (
            "You are given an integer array height of length n. Find two lines that together "
            "with the x-axis form a container, such that the container contains the most water."
        ),
        "tags": ["Two Pointers", "Array", "Greedy"],
        "difficulty": "Medium",
        "source": "LeetCode",
    },
    {
        "title": "Trapping Rain Water",
        "statement": (
            "Given n non-negative integers representing an elevation map where the width "
            "of each bar is 1, compute how much water it can trap after raining."
        ),
        "tags": ["Two Pointers", "Array", "DP", "Stack"],
        "difficulty": "Hard",
        "source": "LeetCode",
    },

    # ── Binary Search ─────────────────────────────────────────────────────────
    {
        "title": "Binary Search",
        "statement": (
            "Given an array of integers nums which is sorted in ascending order, "
            "and an integer target, write a function to search target in nums. "
            "If target exists, return its index. Otherwise, return -1."
        ),
        "tags": ["Binary Search", "Array"],
        "difficulty": "Easy",
        "source": "LeetCode",
    },
    {
        "title": "Search in Rotated Sorted Array",
        "statement": (
            "Given the array nums after the possible rotation and an integer target, "
            "return the index of target if it is in nums, or -1 if it is not in nums."
        ),
        "tags": ["Binary Search", "Array"],
        "difficulty": "Medium",
        "source": "LeetCode",
    },
    {
        "title": "Find Minimum in Rotated Sorted Array",
        "statement": (
            "Given the sorted rotated array nums of unique elements, return the minimum "
            "element of this array."
        ),
        "tags": ["Binary Search", "Array"],
        "difficulty": "Medium",
        "source": "LeetCode",
    },
    {
        "title": "Koko Eating Bananas",
        "statement": (
            "Koko loves to eat bananas. There are n piles of bananas, the ith pile has "
            "piles[i] bananas. Return the minimum integer k such that she can eat all "
            "the bananas within h hours."
        ),
        "tags": ["Binary Search", "Array"],
        "difficulty": "Medium",
        "source": "LeetCode",
    },

    # ── Stack ─────────────────────────────────────────────────────────────────
    {
        "title": "Valid Parentheses",
        "statement": (
            "Given a string s containing just the characters '(', ')', '{', '}', '[' "
            "and ']', determine if the input string is valid."
        ),
        "tags": ["Stack", "String"],
        "difficulty": "Easy",
        "source": "LeetCode",
    },
    {
        "title": "Min Stack",
        "statement": (
            "Design a stack that supports push, pop, top, and retrieving "
            "the minimum element in constant time."
        ),
        "tags": ["Stack", "Design"],
        "difficulty": "Medium",
        "source": "LeetCode",
    },
    {
        "title": "Daily Temperatures",
        "statement": (
            "Given an array of integers temperatures representing daily temperatures, "
            "return an array answer such that answer[i] is the number of days you have "
            "to wait after the ith day to get a warmer temperature."
        ),
        "tags": ["Stack", "Monotonic Stack", "Array"],
        "difficulty": "Medium",
        "source": "LeetCode",
    },
    {
        "title": "Largest Rectangle in Histogram",
        "statement": (
            "Given an array of integers heights representing the histogram's bar height "
            "where the width of each bar is 1, return the area of the largest rectangle "
            "in the histogram."
        ),
        "tags": ["Stack", "Monotonic Stack", "Array"],
        "difficulty": "Hard",
        "source": "LeetCode",
    },

    # ── Linked List ───────────────────────────────────────────────────────────
    {
        "title": "Reverse Linked List",
        "statement": (
            "Given the head of a singly linked list, reverse the list, "
            "and return the reversed list."
        ),
        "tags": ["Linked List", "Recursion"],
        "difficulty": "Easy",
        "source": "LeetCode",
    },
    {
        "title": "Merge Two Sorted Lists",
        "statement": (
            "You are given the heads of two sorted linked lists list1 and list2. "
            "Merge the two lists into one sorted list and return the head."
        ),
        "tags": ["Linked List", "Recursion"],
        "difficulty": "Easy",
        "source": "LeetCode",
    },
    {
        "title": "Linked List Cycle",
        "statement": (
            "Given head, the head of a linked list, determine if the linked list has a cycle in it."
        ),
        "tags": ["Linked List", "Two Pointers"],
        "difficulty": "Easy",
        "source": "LeetCode",
    },
    {
        "title": "LRU Cache",
        "statement": (
            "Design a data structure that follows the constraints of a Least Recently Used (LRU) "
            "cache. Implement the LRUCache class with get and put operations both in O(1) time."
        ),
        "tags": ["Linked List", "HashMap", "Design"],
        "difficulty": "Medium",
        "source": "LeetCode",
    },

    # ── Trees ─────────────────────────────────────────────────────────────────
    {
        "title": "Invert Binary Tree",
        "statement": (
            "Given the root of a binary tree, invert the tree, and return its root."
        ),
        "tags": ["Tree", "BFS", "DFS", "Recursion"],
        "difficulty": "Easy",
        "source": "LeetCode",
    },
    {
        "title": "Maximum Depth of Binary Tree",
        "statement": (
            "Given the root of a binary tree, return its maximum depth."
        ),
        "tags": ["Tree", "DFS", "BFS"],
        "difficulty": "Easy",
        "source": "LeetCode",
    },
    {
        "title": "Balanced Binary Tree",
        "statement": (
            "Given a binary tree, determine if it is height-balanced (depth of the two "
            "subtrees of every node never differs by more than one)."
        ),
        "tags": ["Tree", "DFS"],
        "difficulty": "Easy",
        "source": "LeetCode",
    },
    {
        "title": "Binary Tree Level Order Traversal",
        "statement": (
            "Given the root of a binary tree, return the level order traversal "
            "of its nodes' values (i.e., from left to right, level by level)."
        ),
        "tags": ["Tree", "BFS"],
        "difficulty": "Medium",
        "source": "LeetCode",
    },
    {
        "title": "Lowest Common Ancestor of a Binary Search Tree",
        "statement": (
            "Given a binary search tree (BST), find the lowest common ancestor (LCA) "
            "node of two given nodes in the BST."
        ),
        "tags": ["Tree", "BST", "DFS"],
        "difficulty": "Medium",
        "source": "LeetCode",
    },
    {
        "title": "Serialize and Deserialize Binary Tree",
        "statement": (
            "Serialization is the process of converting a data structure or object "
            "into a sequence of bits so that it can be stored. Design an algorithm to "
            "serialize and deserialize a binary tree."
        ),
        "tags": ["Tree", "BFS", "DFS", "Design"],
        "difficulty": "Hard",
        "source": "LeetCode",
    },

    # ── Graphs ────────────────────────────────────────────────────────────────
    {
        "title": "Number of Islands",
        "statement": (
            "Given an m x n 2D binary grid grid which represents a map of '1's (land) "
            "and '0's (water), return the number of islands."
        ),
        "tags": ["Graph", "DFS", "BFS", "Union Find"],
        "difficulty": "Medium",
        "source": "LeetCode",
    },
    {
        "title": "Clone Graph",
        "statement": (
            "Given a reference of a node in a connected undirected graph, "
            "return a deep copy (clone) of the graph."
        ),
        "tags": ["Graph", "BFS", "DFS", "HashMap"],
        "difficulty": "Medium",
        "source": "LeetCode",
    },
    {
        "title": "Course Schedule",
        "statement": (
            "There are a total of numCourses courses you have to take, labeled from 0 "
            "to numCourses - 1. Return true if you can finish all courses."
        ),
        "tags": ["Graph", "Topological Sort", "DFS"],
        "difficulty": "Medium",
        "source": "LeetCode",
    },
    {
        "title": "Pacific Atlantic Water Flow",
        "statement": (
            "Given an m x n rectangular island, return a list of grid coordinates where "
            "rain water can flow to both the Pacific and Atlantic oceans."
        ),
        "tags": ["Graph", "DFS", "BFS"],
        "difficulty": "Medium",
        "source": "LeetCode",
    },
    {
        "title": "Word Ladder",
        "statement": (
            "A transformation sequence from word beginWord to word endWord using a dictionary "
            "wordList is valid if every adjacent pair of words differs by a single letter. "
            "Return the number of words in the shortest transformation sequence."
        ),
        "tags": ["Graph", "BFS", "String"],
        "difficulty": "Hard",
        "source": "LeetCode",
    },

    # ── Dynamic Programming ───────────────────────────────────────────────────
    {
        "title": "Climbing Stairs",
        "statement": (
            "You are climbing a staircase. It takes n steps to reach the top. "
            "Each time you can either climb 1 or 2 steps. "
            "In how many distinct ways can you climb to the top?"
        ),
        "tags": ["DP", "Math", "Memoization"],
        "difficulty": "Easy",
        "source": "LeetCode",
    },
    {
        "title": "House Robber",
        "statement": (
            "You are a professional robber. Given an integer array nums representing "
            "the amount of money of each house, return the maximum amount of money "
            "you can rob tonight without alerting the police."
        ),
        "tags": ["DP", "Array"],
        "difficulty": "Medium",
        "source": "LeetCode",
    },
    {
        "title": "Coin Change",
        "statement": (
            "You are given an integer array coins representing coins of different denominations "
            "and an integer amount representing a total amount of money. Return the fewest number "
            "of coins that you need to make up that amount."
        ),
        "tags": ["DP", "BFS"],
        "difficulty": "Medium",
        "source": "LeetCode",
    },
    {
        "title": "Longest Increasing Subsequence",
        "statement": (
            "Given an integer array nums, return the length of the longest strictly "
            "increasing subsequence."
        ),
        "tags": ["DP", "Binary Search"],
        "difficulty": "Medium",
        "source": "LeetCode",
    },
    {
        "title": "Word Break",
        "statement": (
            "Given a string s and a dictionary of strings wordDict, return true if s can be "
            "segmented into a space-separated sequence of one or more dictionary words."
        ),
        "tags": ["DP", "String", "Trie"],
        "difficulty": "Medium",
        "source": "LeetCode",
    },
    {
        "title": "0/1 Knapsack",
        "statement": (
            "Given N items where each item has some weight and profit associated with it "
            "and given a bag with capacity W, find the maximum profit possible such that "
            "the items in the bag fit within the capacity."
        ),
        "tags": ["DP", "Array"],
        "difficulty": "Medium",
        "source": "Classic",
    },
    {
        "title": "Edit Distance",
        "statement": (
            "Given two strings word1 and word2, return the minimum number of operations "
            "required to convert word1 to word2. Operations: Insert, Delete, or Replace a character."
        ),
        "tags": ["DP", "String"],
        "difficulty": "Hard",
        "source": "LeetCode",
    },
    {
        "title": "Unique Paths",
        "statement": (
            "There is a robot on an m x n grid. The robot is initially located at the top-left "
            "corner. The robot tries to move to the bottom-right corner. Return the number of "
            "possible unique paths."
        ),
        "tags": ["DP", "Math", "Combinatorics"],
        "difficulty": "Medium",
        "source": "LeetCode",
    },

    # ── Heap / Priority Queue ─────────────────────────────────────────────────
    {
        "title": "Kth Largest Element in an Array",
        "statement": (
            "Given an integer array nums and an integer k, return the kth largest element "
            "in the array."
        ),
        "tags": ["Heap", "Array", "Quickselect"],
        "difficulty": "Medium",
        "source": "LeetCode",
    },
    {
        "title": "Merge K Sorted Lists",
        "statement": (
            "You are given an array of k linked-lists lists, each linked-list is sorted "
            "in ascending order. Merge all the linked-lists into one sorted linked-list "
            "and return it."
        ),
        "tags": ["Heap", "Linked List", "Divide & Conquer"],
        "difficulty": "Hard",
        "source": "LeetCode",
    },
    {
        "title": "Find Median from Data Stream",
        "statement": (
            "The MedianFinder class finds the median from a data stream. "
            "Implement addNum(int num) and findMedian() in O(log n) and O(1) respectively."
        ),
        "tags": ["Heap", "Design", "Two Heaps"],
        "difficulty": "Hard",
        "source": "LeetCode",
    },

    # ── Backtracking ──────────────────────────────────────────────────────────
    {
        "title": "Permutations",
        "statement": (
            "Given an array nums of distinct integers, return all the possible permutations. "
            "You can return the answer in any order."
        ),
        "tags": ["Backtracking", "Array"],
        "difficulty": "Medium",
        "source": "LeetCode",
    },
    {
        "title": "Subsets",
        "statement": (
            "Given an integer array nums of unique elements, return all possible subsets "
            "(the power set). The solution set must not contain duplicate subsets."
        ),
        "tags": ["Backtracking", "Array", "Bit Manipulation"],
        "difficulty": "Medium",
        "source": "LeetCode",
    },
    {
        "title": "Combination Sum",
        "statement": (
            "Given an array of distinct integers candidates and a target integer target, "
            "return a list of all unique combinations of candidates where the chosen "
            "numbers sum to target."
        ),
        "tags": ["Backtracking", "Array"],
        "difficulty": "Medium",
        "source": "LeetCode",
    },
    {
        "title": "N-Queens",
        "statement": (
            "The n-queens puzzle is the problem of placing n queens on an n x n chessboard "
            "such that no two queens attack each other. Return all distinct solutions."
        ),
        "tags": ["Backtracking", "Array"],
        "difficulty": "Hard",
        "source": "LeetCode",
    },

    # ── Greedy ────────────────────────────────────────────────────────────────
    {
        "title": "Jump Game",
        "statement": (
            "You are given an integer array nums. You are initially positioned at the first "
            "index of the array. Each element represents your maximum jump length. "
            "Return true if you can reach the last index, or false otherwise."
        ),
        "tags": ["Greedy", "Array", "DP"],
        "difficulty": "Medium",
        "source": "LeetCode",
    },
    {
        "title": "Gas Station",
        "statement": (
            "There are n gas stations along a circular route. You have a car with an "
            "unlimited gas tank. Return the starting gas station's index if you can travel "
            "around the circuit once, otherwise return -1."
        ),
        "tags": ["Greedy", "Array"],
        "difficulty": "Medium",
        "source": "LeetCode",
    },

    # ── Trie ──────────────────────────────────────────────────────────────────
    {
        "title": "Implement Trie (Prefix Tree)",
        "statement": (
            "A trie (pronounced as 'try') or prefix tree is a tree data structure used to "
            "efficiently store and retrieve keys in a dataset of strings. "
            "Implement the Trie class with insert, search, and startsWith methods."
        ),
        "tags": ["Trie", "Design", "String"],
        "difficulty": "Medium",
        "source": "LeetCode",
    },
    {
        "title": "Word Search II",
        "statement": (
            "Given an m x n board of characters and a list of strings words, "
            "return all words on the board. Each word must be constructed from letters of "
            "sequentially adjacent cells."
        ),
        "tags": ["Trie", "Backtracking", "Matrix"],
        "difficulty": "Hard",
        "source": "LeetCode",
    },

    # ── Intervals ─────────────────────────────────────────────────────────────
    {
        "title": "Merge Intervals",
        "statement": (
            "Given an array of intervals where intervals[i] = [starti, endi], merge all "
            "overlapping intervals and return an array of the non-overlapping intervals."
        ),
        "tags": ["Intervals", "Array", "Sorting"],
        "difficulty": "Medium",
        "source": "LeetCode",
    },
    {
        "title": "Non-Overlapping Intervals",
        "statement": (
            "Given an array of intervals intervals where intervals[i] = [starti, endi], "
            "return the minimum number of intervals you need to remove to make the rest "
            "of the intervals non-overlapping."
        ),
        "tags": ["Intervals", "Greedy", "Sorting"],
        "difficulty": "Medium",
        "source": "LeetCode",
    },
]


def seed(verbose: bool = True, app=None) -> int:
    """
    Insert all PROBLEMS into the database, skipping existing titles.

    Can be called with an existing Flask app (e.g. in tests) or will
    create its own app instance when run as a standalone script.

    Args:
        verbose (bool): Print progress to stdout.
        app: Optional Flask app instance. If None, creates a new one.

    Returns:
        int: Number of problems actually inserted.
    """
    from app.extensions import db
    from app.models.problem import Problem

    if app is None:
        from app import create_app
        app = create_app()
        ctx = app.app_context()
        ctx.push()
        owns_ctx = True
    else:
        owns_ctx = False

    inserted = 0
    try:
        existing_titles = {p.title for p in Problem.query.all()}

        for data in PROBLEMS:
            if data["title"] in existing_titles:
                if verbose:
                    print(f"  ⏭  Skipping (exists): {data['title']}")
                continue

            problem = Problem(
                title=data["title"],
                statement=data["statement"],
                tags=data["tags"],
                difficulty=data["difficulty"],
                source=data["source"],
            )
            db.session.add(problem)
            inserted += 1

            if verbose:
                print(f"  ✅ Added: {data['title']} [{data['difficulty']}]")

        db.session.commit()

    finally:
        if owns_ctx:
            ctx.pop()

    if verbose:
        print(f"\n🎉 Seed complete — {inserted} problems inserted, "
              f"{len(PROBLEMS) - inserted} already existed.")
    return inserted


if __name__ == "__main__":
    print(f"📚 CodeWhisper Problem Bank — {len(PROBLEMS)} problems defined\n")
    seed(verbose=True)
