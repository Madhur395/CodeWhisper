"""
CodeWhisper — Production Entry Point
Gunicorn uses this file: gunicorn run:app

On first startup, automatically:
  - runs DB migrations (flask db upgrade)
  - seeds the problem bank if empty
"""

import os
import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

from app import create_app

app = create_app()


def _bootstrap():
    """Run DB migrations and seed the problem bank on startup."""
    with app.app_context():
        # ── 1. Run migrations ─────────────────────────────────────────────
        try:
            from flask_migrate import upgrade
            upgrade()
            logger.info("✅ Database migrations applied")
        except Exception as e:
            logger.error("❌ Migration failed: %s", e)
            # Try create_all as fallback (works for fresh SQLite)
            try:
                from app.extensions import db
                db.create_all()
                logger.info("✅ DB tables created via create_all() fallback")
            except Exception as e2:
                logger.error("❌ create_all failed: %s", e2)

        # ── 2. Seed problem bank if empty ─────────────────────────────────
        try:
            from app.models.problem import Problem
            if Problem.query.count() == 0:
                sys.path.insert(0, os.path.dirname(__file__))
                from scripts.seed_problems import seed
                inserted = seed(verbose=False, app=app)
                logger.info("✅ Problem bank seeded (%d problems)", inserted)
            else:
                logger.info("ℹ️  Problem bank already populated (%d problems)",
                            Problem.query.count())
        except Exception as e:
            logger.warning("⚠️  Could not seed problems: %s", e)


# Run bootstrap when gunicorn imports this module
_bootstrap()


if __name__ == "__main__":
    # Local dev fallback
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
