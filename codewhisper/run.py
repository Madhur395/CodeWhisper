"""
CodeWhisper — Production Entry Point
run.py: used by gunicorn as  gunicorn run:app
- auto-creates DB tables on startup
- auto-seeds problem bank if empty
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


def _init_db():
    """Create tables and seed problems. Called once on first request."""
    with app.app_context():
        try:
            from app.extensions import db
            db.create_all()
            logger.info("✅ DB tables ready")
        except Exception as e:
            logger.error("❌ DB init error: %s", e)

        try:
            from app.models.problem import Problem
            if Problem.query.count() == 0:
                sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
                from scripts.seed_problems import seed
                n = seed(verbose=False, app=app)
                logger.info("✅ Seeded %d problems", n)
        except Exception as e:
            logger.warning("⚠️  Seed skipped: %s", e)


# Run on startup (gunicorn imports this module once per worker)
_init_db()


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
