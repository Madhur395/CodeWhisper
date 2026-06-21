"""
CodeWhisper — Production Entry Point
Gunicorn: gunicorn run:app
Auto-initialises DB tables and seeds problem bank on startup.
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
    """Create all DB tables and seed problems. Safe to call multiple times."""
    with app.app_context():
        from app.extensions import db

        # Log which DB we're using
        db_url = str(app.config.get("SQLALCHEMY_DATABASE_URI", ""))
        if "postgresql" in db_url or "postgres" in db_url:
            logger.info("📦 Using PostgreSQL (persistent)")
        elif "sqlite" in db_url:
            logger.warning("⚠️  Using SQLite — data will be lost on restart! Set DATABASE_URL.")
        else:
            logger.info("📦 DB: %s", db_url[:30])

        # Try flask db upgrade first (uses Alembic migrations)
        try:
            from flask_migrate import upgrade
            upgrade()
            logger.info("✅ Migrations applied (flask db upgrade)")
        except Exception as e:
            logger.warning("Migration failed (%s) — falling back to create_all()", e)
            try:
                db.create_all()
                logger.info("✅ DB tables created via create_all()")
            except Exception as e2:
                logger.error("❌ DB init failed: %s", e2)
                return

        # Seed problem bank if empty
        try:
            from app.models.problem import Problem
            count = Problem.query.count()
            if count == 0:
                sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
                from scripts.seed_problems import seed
                n = seed(verbose=False, app=app)
                logger.info("✅ Seeded %d problems into problem bank", n)
            else:
                logger.info("ℹ️  Problem bank: %d problems already exist", count)
        except Exception as e:
            logger.warning("⚠️  Could not seed problems: %s", e)


# Run on startup (once per gunicorn worker process)
_init_db()


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
