"""One-time init endpoint + status check."""
import os, sys
from flask import Blueprint, jsonify, request

debug_bp = Blueprint("debug", __name__)


@debug_bp.route("/api/init", methods=["POST"])
def init_db():
    """One-time DB init — POST to this to create tables and seed problems."""
    secret = request.args.get("secret", "")
    if secret != os.getenv("SECRET_KEY", "")[:16] and secret != "codewhisper2025":
        return jsonify({"error": "unauthorized"}), 403

    results = {}

    # Create tables
    try:
        from app.extensions import db
        from flask import current_app
        with current_app.app_context():
            db.create_all()
        results["tables"] = "✅ created"
    except Exception as e:
        results["tables"] = f"❌ {e}"

    # Seed problems
    try:
        from app.models.problem import Problem
        from flask import current_app
        with current_app.app_context():
            count = Problem.query.count()
            if count == 0:
                sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                from scripts.seed_problems import seed
                from app import create_app
                app = create_app()
                n = seed(verbose=False, app=app)
                results["seed"] = f"✅ seeded {n} problems"
            else:
                results["seed"] = f"✅ already has {count} problems"
    except Exception as e:
        results["seed"] = f"❌ {e}"

    return jsonify(results)


@debug_bp.route("/api/status")
def status():
    """Check deployment status."""
    info = {
        "code_version": "aa3a021",
        "cwd": os.getcwd(),
        "FLASK_ENV": os.getenv("FLASK_ENV", "not set"),
        "DATABASE_URL_set": bool(os.getenv("DATABASE_URL")),
        "GROQ_KEY_set": os.getenv("GROQ_API_KEY", "").startswith("gsk_"),
    }
    try:
        from app.models.user import User
        info["users_table"] = f"✅ ok ({User.query.count()} users)"
    except Exception as e:
        info["users_table"] = f"❌ {str(e)[:100]}"

    try:
        from app.models.problem import Problem
        info["problems_table"] = f"✅ ok ({Problem.query.count()} problems)"
    except Exception as e:
        info["problems_table"] = f"❌ {str(e)[:100]}"

    return jsonify(info)
