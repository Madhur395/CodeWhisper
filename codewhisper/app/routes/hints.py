"""
CodeWhisper — Hints Routes
Phase 5: HintEngineService wired in.
Phase 7: Rate limiting applied (20 submits/hour, 60 next-hints/hour per user).

Endpoints:
    POST  /hints/submit                — Submit a problem → receive Hint #1
    GET   /hints/next/<session_id>     — Advance to the next progressive hint
    GET   /hints/session/<session_id>  — Retrieve all hints delivered so far
    POST  /hints/reset/<session_id>    — Reset hint pointer to the beginning

Rate limits (per authenticated user, backed by Redis):
    POST /hints/submit    — 20 per hour   (LLM cost control)
    GET  /hints/next/...  — 60 per hour   (generous — no LLM call after first)
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.extensions import limiter
from app.services.hint_engine import HintEngineService
from app.utils.validators import validate_problem_input

hints_bp = Blueprint("hints", __name__)


# ── POST /hints/submit ────────────────────────────────────────────────────────

@hints_bp.route("/submit", methods=["POST"])
@jwt_required()
@limiter.limit("20 per hour", error_message="Hint submission limit reached (20/hour). Try again later.")
def submit_problem():
    """
    Submit a DSA/coding problem and receive the first Socratic hint.

    Request body (JSON):
        { "problem_text": "<full problem statement, 20–10 000 chars>" }

    Responses:
        201 — { session_id, hint_level, hint, total_hints, exhausted }
        400 — Validation error (text too short / too long / missing)
        401 — Unauthenticated
        429 — Rate limit exceeded (20 submits per hour per user)
        500 — LLM / internal error
    """
    user_id      = get_jwt_identity()
    data         = request.get_json(silent=True) or {}
    problem_text = data.get("problem_text", "").strip()

    is_valid, error_msg = validate_problem_input(problem_text)
    if not is_valid:
        return jsonify({"error": error_msg}), 400

    result = HintEngineService().start_session(user_id, problem_text)
    return jsonify(result), 201


# ── GET /hints/next/<session_id> ──────────────────────────────────────────────

@hints_bp.route("/next/<session_id>", methods=["GET"])
@jwt_required()
@limiter.limit("60 per hour", error_message="Next-hint limit reached (60/hour). Try again later.")
def next_hint(session_id):
    """
    Advance to the next progressive hint for an existing session.

    Responses:
        200 — { session_id, hint_level, hint, total_hints, exhausted }
              or { session_id, message, exhausted: true } when all hints shown
        401 — Unauthenticated
        404 — Session not found or not owned by this user
        429 — Rate limit exceeded
    """
    user_id = get_jwt_identity()
    result  = HintEngineService().get_next_hint(session_id, user_id)
    return jsonify(result), 200


# ── GET /hints/session/<session_id> ──────────────────────────────────────────

@hints_bp.route("/session/<session_id>", methods=["GET"])
@jwt_required()
@limiter.limit("120 per hour", error_message="Session fetch limit reached (120/hour).")
def get_session(session_id):
    """
    Retrieve all hints delivered so far for a session, ordered by level.

    Responses:
        200 — { session_id, hints: [{ level, hint, delivered_at }, ...] }
        401 — Unauthenticated
        404 — Session not found
        429 — Rate limit exceeded
    """
    user_id = get_jwt_identity()
    hints   = HintEngineService().get_session_hints(session_id, user_id)
    return jsonify({"session_id": session_id, "hints": hints}), 200


# ── POST /hints/reset/<session_id> ───────────────────────────────────────────

@hints_bp.route("/reset/<session_id>", methods=["POST"])
@jwt_required()
@limiter.limit("10 per hour", error_message="Session reset limit reached (10/hour).")
def reset_session(session_id):
    """
    Reset a session's hint pointer so the user starts from Hint #1 again.
    Also clears all existing hint logs for the session.

    Responses:
        200 — { session_id, message }
        401 — Unauthenticated
        404 — Session not found
        429 — Rate limit exceeded
    """
    user_id = get_jwt_identity()
    result  = HintEngineService().reset_session(session_id, user_id)
    return jsonify(result), 200
