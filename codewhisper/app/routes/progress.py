"""
CodeWhisper — Progress Routes
Phase 6: ProgressTrackerService wired in.
Phase 7: Rate limiting applied, input validation on mark_solved.

Endpoints:
    GET   /progress/history              — Paginated session history
    GET   /progress/stats                — Aggregate learning statistics
    PATCH /progress/solve/<session_id>   — Mark session as solved
    GET   /progress/concepts             — Tag-frequency breakdown
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.extensions import limiter
from app.services.progress_tracker import ProgressTrackerService

progress_bp = Blueprint("progress", __name__)


# ── GET /progress/history ─────────────────────────────────────────────────────

@progress_bp.route("/history", methods=["GET"])
@jwt_required()
@limiter.limit("60 per hour", error_message="History fetch limit reached (60/hour).")
def history():
    """
    Return the authenticated user's paginated session history, newest-first.

    Query params:
        page     (int, default 1)
        per_page (int, default 20, max 100)

    Responses:
        200 — { sessions, total, page, per_page, pages }
        401 — Unauthenticated
        429 — Rate limit exceeded
    """
    user_id  = get_jwt_identity()
    page     = request.args.get("page",     1,   type=int)
    per_page = request.args.get("per_page", 20,  type=int)

    # Clamp page to sensible bounds
    page     = max(1, page)
    per_page = max(1, min(per_page, 100))

    data = ProgressTrackerService().get_history(user_id, page=page, per_page=per_page)
    return jsonify(data), 200


# ── GET /progress/stats ───────────────────────────────────────────────────────

@progress_bp.route("/stats", methods=["GET"])
@jwt_required()
@limiter.limit("30 per hour", error_message="Stats fetch limit reached (30/hour).")
def stats():
    """
    Return aggregate learning statistics for the authenticated user.

    Responses:
        200 — { total_attempted, total_solved, solve_rate,
                average_hints_per_problem, top_tags }
        401 — Unauthenticated
        429 — Rate limit exceeded
    """
    user_id = get_jwt_identity()
    data    = ProgressTrackerService().get_stats(user_id)
    return jsonify(data), 200


# ── PATCH /progress/solve/<session_id> ───────────────────────────────────────

@progress_bp.route("/solve/<session_id>", methods=["PATCH"])
@jwt_required()
@limiter.limit("30 per hour", error_message="Mark-solved limit reached (30/hour).")
def mark_solved(session_id):
    """
    Mark the given problem session as solved.

    Path param:
        session_id — UUID of the UserProblemSession to mark.

    Responses:
        200 — { session_id, message, solved_at }
        401 — Unauthenticated
        404 — Session not found or not owned by this user
        429 — Rate limit exceeded
    """
    user_id = get_jwt_identity()
    result  = ProgressTrackerService().mark_solved(session_id, user_id)
    return jsonify(result), 200


# ── GET /progress/concepts ────────────────────────────────────────────────────

@progress_bp.route("/concepts", methods=["GET"])
@jwt_required()
@limiter.limit("30 per hour", error_message="Concepts fetch limit reached (30/hour).")
def concepts():
    """
    Return a tag-frequency breakdown across all of the user's sessions.

    Responses:
        200 — { concepts: [{ tag, count }, ...] } sorted by count desc
        401 — Unauthenticated
        429 — Rate limit exceeded
    """
    user_id = get_jwt_identity()
    data    = ProgressTrackerService().get_concept_breakdown(user_id)
    return jsonify({"concepts": data}), 200
