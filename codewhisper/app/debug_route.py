"""Diagnostic route to check deployment status."""
import os
import sys
from flask import Blueprint, jsonify

debug_bp = Blueprint("debug", __name__)

@debug_bp.route("/api/status")
def status():
    info = {
        "python": sys.version,
        "cwd": os.getcwd(),
        "FLASK_ENV": os.getenv("FLASK_ENV", "not set"),
        "DATABASE_URL_set": bool(os.getenv("DATABASE_URL")),
        "GROQ_API_KEY_set": os.getenv("GROQ_API_KEY","").startswith("gsk_"),
    }
    # Test DB connection
    try:
        from app.extensions import db
        from flask import current_app
        with current_app.app_context():
            db.session.execute(db.text("SELECT 1"))
            info["db_connection"] = "ok"
    except Exception as e:
        info["db_connection"] = f"ERROR: {str(e)[:200]}"
    
    # Check tables
    try:
        from app.models.user import User
        count = User.query.count()
        info["users_table"] = f"ok ({count} users)"
    except Exception as e:
        info["users_table"] = f"ERROR: {str(e)[:200]}"

    return jsonify(info)
