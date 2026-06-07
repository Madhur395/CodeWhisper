"""
CodeWhisper — Standalone Dev Launcher
Runs the app with SQLite (no PostgreSQL needed) and in-memory cache (no Redis needed).

Usage:
    python run_dev.py

The server starts at http://localhost:5000
"""

import os
import sys

# ── Force standalone mode ─────────────────────────────────────────────────────
os.environ.setdefault("FLASK_ENV",               "standalone")
os.environ.setdefault("SECRET_KEY",              "dev-codewhisper-secret-key-2025")
os.environ.setdefault("JWT_SECRET_KEY",          "dev-codewhisper-jwt-key-2025-secure")
os.environ.setdefault("JWT_ACCESS_TOKEN_EXPIRES","3600")
os.environ.setdefault("LLM_PROVIDER",            "groq")
os.environ.setdefault("GROQ_MODEL",              "llama-3.3-70b-versatile")
os.environ.setdefault("CORS_ORIGINS",            "*")
# SQLite — no PostgreSQL required
os.environ.setdefault("DATABASE_URL",            "sqlite:///codewhisper_dev.db")

# ── Import app ────────────────────────────────────────────────────────────────
from app import create_app
from app.config import StandaloneConfig

app = create_app(config=StandaloneConfig)

# ── Bootstrap DB + seed problems ──────────────────────────────────────────────
with app.app_context():
    from app.extensions import db
    db.create_all()
    print("✅  Database tables created (SQLite)")

    # Seed problem bank if empty
    from app.models.problem import Problem
    if Problem.query.count() == 0:
        try:
            sys.path.insert(0, os.path.dirname(__file__))
            from scripts.seed_problems import seed
            inserted = seed(verbose=False, app=app)
            print(f"✅  Problem bank seeded ({inserted} problems)")
        except Exception as e:
            print(f"⚠️  Could not seed problems: {e}")
    else:
        print(f"ℹ️   Problem bank already has {Problem.query.count()} problems")

    # Check API key
    groq_key = os.environ.get("GROQ_API_KEY", "")
    if not groq_key or groq_key.startswith("gsk_REPLACE"):
        print()
        print("⚠️  ─────────────────────────────────────────────────────────────")
        print("   GROQ_API_KEY is not set — hint generation will use fallbacks.")
        print("   Get a free key at https://console.groq.com/keys")
        print("   Then set it:  export GROQ_API_KEY=gsk_...")
        print("   Or edit .env and restart.")
        print("⚠️  ─────────────────────────────────────────────────────────────")
    else:
        print(f"✅  Groq API key detected ({groq_key[:12]}...)")

print()
print("🚀  CodeWhisper is starting...")
print("    ┌───────────────────────────────────────────┐")
print("    │  Open in browser:  http://127.0.0.1:5000   │")
print("    │  Press Ctrl+C to stop                     │")
print("    └───────────────────────────────────────────┘")
print()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
