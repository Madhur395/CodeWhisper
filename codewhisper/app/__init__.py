"""
CodeWhisper — Flask Application Factory
Production-hardened: absolute paths, DATABASE_URL fix, graceful startup.
"""

import os
import logging
from flask import Flask, jsonify
from app.config import get_config
from app.extensions import db, migrate, jwt, cors, limiter

# Base directory of the project (one level above this package)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

logger = logging.getLogger(__name__)


def create_app(config=None):
    app = Flask(
        __name__,
        template_folder=os.path.join(BASE_DIR, "templates"),  # absolute path
        static_folder=os.path.join(BASE_DIR, "static"),       # absolute path
    )

    # ── Load Configuration ────────────────────────────────────────────────────
    cfg = config if config is not None else get_config()
    app.config.from_object(cfg)

    # ── Fix Render's postgres:// → postgresql:// ──────────────────────────────
    db_url = app.config.get("SQLALCHEMY_DATABASE_URI") or ""
    if db_url.startswith("postgres://"):
        app.config["SQLALCHEMY_DATABASE_URI"] = db_url.replace(
            "postgres://", "postgresql://", 1
        )

    # ── Rate limiter storage (memory:// is safe on all platforms) ─────────────
    app.config.setdefault("RATELIMIT_STORAGE_URI", "memory://")
    app.config["RATELIMIT_ENABLED"] = True

    # ── Initialize Extensions ─────────────────────────────────────────────────
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    cors.init_app(app, resources={r"/*": {"origins": app.config.get("CORS_ORIGINS", "*")}})
    limiter.init_app(app)

    # ── Import models so Flask-Migrate / SQLAlchemy can discover them ─────────
    from app.models import User, Problem, UserProblemSession, HintLog  # noqa: F401

    # ── Register Blueprints ───────────────────────────────────────────────────
    from app.routes.auth      import auth_bp
    from app.routes.hints     import hints_bp
    from app.routes.progress  import progress_bp
    from app.routes.recommend import recommend_bp
    from app.routes.ui        import ui_bp

    app.register_blueprint(auth_bp,      url_prefix="/auth")
    app.register_blueprint(hints_bp,     url_prefix="/hints")
    app.register_blueprint(progress_bp,  url_prefix="/progress")
    app.register_blueprint(recommend_bp, url_prefix="/recommend")
    app.register_blueprint(ui_bp)

    # Debug route (temporary)
    try:
        from app.debug_route import debug_bp
        app.register_blueprint(debug_bp)
    except Exception:
        pass

    # ── Global Error Handlers ─────────────────────────────────────────────────

    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({"error": "Bad request.", "detail": str(e)}), 400

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Resource not found."}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({"error": "Method not allowed."}), 405

    @app.errorhandler(429)
    def rate_limited(e):
        return jsonify({
            "error": "Rate limit exceeded. Please try again later.",
            "retry_after": getattr(e, "retry_after", None),
        }), 429

    @app.errorhandler(500)
    def server_error(e):
        logger.error("Internal server error: %s", e, exc_info=True)
        return jsonify({"error": "Internal server error."}), 500

    # ── Health Check ──────────────────────────────────────────────────────────

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok", "app": "CodeWhisper", "version": "1.0.0"}), 200

    return app
