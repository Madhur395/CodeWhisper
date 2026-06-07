"""
CodeWhisper — Recommend Routes
Phase 6: RecommenderService wired in.
Phase 7: Rate limiting applied, limit query-param validated.

Endpoints:
    GET /recommend/problems   — Tag-scored problem recommendations
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.extensions import limiter
from app.services.recommender import RecommenderService

recommend_bp = Blueprint("recommend", __name__)


# ── GET /recommend/problems ───────────────────────────────────────────────────

@recommend_bp.route("/problems", methods=["GET"])
@jwt_required()
@limiter.limit("30 per hour", error_message="Recommend limit reached (30/hour).")
def recommend():
    """
    Return tag-scored DSA problem recommendations for the authenticated user.

    Query params:
        limit (int, default 5, range 1–20)

    Responses:
        200 — { recommendations: [{ problem_id, title, difficulty,
                                     tags, source, statement_preview }] }
        400 — Invalid limit parameter
        401 — Unauthenticated
        429 — Rate limit exceeded
    """
    user_id = get_jwt_identity()

    # Validate & clamp the limit parameter
    limit = request.args.get("limit", 5, type=int)
    if limit is None or not isinstance(limit, int):
        return jsonify({"error": "limit must be an integer between 1 and 20."}), 400
    limit = max(1, min(limit, 20))

    problems = RecommenderService().recommend(user_id, limit=limit)
    return jsonify({"recommendations": problems}), 200
