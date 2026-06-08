"""Temporary debug route — remove after confirming deployment works."""
import os
from flask import Blueprint, jsonify

debug_bp = Blueprint("debug", __name__)

@debug_bp.route("/api/debug/config")
def debug_config():
    db_url = os.getenv("DATABASE_URL", "NOT SET")
    if db_url and len(db_url) > 30:
        db_url = db_url[:15] + "..." + db_url[-10:]
    return jsonify({
        "FLASK_ENV": os.getenv("FLASK_ENV", "not set"),
        "DATABASE_URL": db_url,
        "GROQ_API_KEY": "set" if os.getenv("GROQ_API_KEY","").startswith("gsk_") else "NOT SET",
        "python_path": os.getcwd(),
    })
