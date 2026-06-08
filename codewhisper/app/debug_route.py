"""Status and init endpoints."""
import os, sys
from flask import Blueprint, jsonify, request

debug_bp = Blueprint("debug", __name__)

CODE_VERSION = "final-v1"

@debug_bp.route("/api/status")
def status():
    info = {
        "code_version": CODE_VERSION,
        "cwd": os.getcwd(),
        "FLASK_ENV": os.getenv("FLASK_ENV", "not set"),
        "DATABASE_URL_set": bool(os.getenv("DATABASE_URL")),
        "GROQ_KEY_set": os.getenv("GROQ_API_KEY", "").startswith("gsk_") and
                        not os.getenv("GROQ_API_KEY", "").startswith("gsk_REPLACE"),
    }
    try:
        from app.models.user import User
        info["users_table"] = f"ok ({User.query.count()} users)"
    except Exception as e:
        info["users_table"] = f"ERROR: {str(e)[:80]}"
    try:
        from app.models.problem import Problem
        info["problems_table"] = f"ok ({Problem.query.count()} problems)"
    except Exception as e:
        info["problems_table"] = f"ERROR: {str(e)[:80]}"
    return jsonify(info)


@debug_bp.route("/api/init", methods=["GET", "POST"])
def init_db():
    """One-time DB setup — call this after first deploy."""
    results = {}
    try:
        from app.extensions import db
        db.create_all()
        results["tables"] = "created"
    except Exception as e:
        results["tables"] = f"ERROR: {e}"
    try:
        from app.models.problem import Problem
        count = Problem.query.count()
        if count == 0:
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from scripts.seed_problems import seed
            from app import create_app
            n = seed(verbose=False, app=create_app())
            results["seed"] = f"seeded {n} problems"
        else:
            results["seed"] = f"already has {count} problems"
    except Exception as e:
        results["seed"] = f"ERROR: {e}"
    return jsonify(results)


@debug_bp.route("/api/test-hints", methods=["POST"])
def test_hints():
    """Test hint generation directly."""
    try:
        from app.llm import get_llm_client
        client = get_llm_client()
        hints = client.generate_hints(
            "Given an array of integers and a target, find two indices that sum to target."
        )
        return jsonify({
            "ok": True,
            "hints_count": len(hints),
            "first_hint": hints[0] if hints else None,
            "is_fallback": hints[0].startswith("Think carefully") if hints else False,
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
