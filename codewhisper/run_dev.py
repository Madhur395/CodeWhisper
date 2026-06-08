"""
CodeWhisper — Standalone Dev Launcher (no PostgreSQL or Redis needed)
Usage: python run_dev.py
Opens at: http://localhost:5000
"""

import os, sys, logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

os.environ.setdefault("FLASK_ENV",               "standalone")
os.environ.setdefault("SECRET_KEY",              "dev-codewhisper-secret-key-2025")
os.environ.setdefault("JWT_SECRET_KEY",          "dev-codewhisper-jwt-key-2025-secure")
os.environ.setdefault("JWT_ACCESS_TOKEN_EXPIRES","3600")
os.environ.setdefault("LLM_PROVIDER",            "groq")
os.environ.setdefault("GROQ_MODEL",              "llama-3.3-70b-versatile")
os.environ.setdefault("CORS_ORIGINS",            "*")

from app import create_app
from app.config import StandaloneConfig

app = create_app(config=StandaloneConfig)

with app.app_context():
    from app.extensions import db
    db.create_all()
    print("✅  Database tables created (SQLite)")

    from app.models.problem import Problem
    if Problem.query.count() == 0:
        sys.path.insert(0, os.path.dirname(__file__))
        from scripts.seed_problems import seed
        n = seed(verbose=False, app=app)
        print(f"✅  Problem bank seeded ({n} problems)")
    else:
        print(f"ℹ️   Problem bank: {Problem.query.count()} problems")

    key = os.environ.get("GROQ_API_KEY", "")
    if not key or "REPLACE" in key:
        print()
        print("⚠️  GROQ_API_KEY not set — using fallback hints")
        print("   Get a free key: https://console.groq.com/keys")
        print("   Then: export GROQ_API_KEY=gsk_...")
    else:
        print(f"✅  Groq API key: {key[:12]}...")

print()
print("🚀  http://localhost:5000")
print("    Ctrl+C to stop")
print()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
