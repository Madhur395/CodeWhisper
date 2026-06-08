"""
CodeWhisper — UI Routes
Phase 8: Serves all HTML page templates.

These routes render Jinja2 templates. All actual data loading happens
via JavaScript fetch() calls to the API endpoints — no server-side
data injection needed (pure SPA-style with JWT in localStorage).

Pages:
    GET /           — Login page
    GET /register   — Registration page
    GET /dashboard  — User dashboard (stats + history)
    GET /solve      — Hint workspace
    GET /recommend  — Problem recommendations
"""

from flask import Blueprint, render_template

ui_bp = Blueprint("ui", __name__)


@ui_bp.route("/")
def index():
    """Landing / Login page."""
    return render_template("login.html")


@ui_bp.route("/register")
def register_page():
    """User registration page."""
    return render_template("register.html")


@ui_bp.route("/dashboard")
def dashboard():
    """User dashboard — stats and session history."""
    return render_template("dashboard.html")


@ui_bp.route("/solve")
def solve():
    """Hint workspace — paste a problem, get progressive hints."""
    return render_template("solve.html")


@ui_bp.route("/recommend")
def recommend_page():
    """Problem recommendations page."""
    return render_template("recommend.html")
