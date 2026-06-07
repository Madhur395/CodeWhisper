"""
CodeWhisper — Flask Extension Instances
All extensions are initialized here and bound to the app in create_app().

Phase 3: JWT blocklist loader wired in.
Phase 7: Flask-Limiter wired in (Redis-backed, keyed by JWT identity).
"""

import os

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# ── Extension instances (unbound until init_app() is called) ─────────────────

db      = SQLAlchemy()
migrate = Migrate()
jwt     = JWTManager()
cors    = CORS()


# ── Rate Limiter ──────────────────────────────────────────────────────────────
# Key function: prefer the authenticated user's JWT identity so limits are
# per-user rather than per-IP (important behind reverse proxies / shared IPs).
# Falls back to remote address for unauthenticated requests.

def _rate_limit_key() -> str:
    """
    Return a stable string key for the rate-limiter.

    Priority:
        1. JWT identity (user UUID)  — for authenticated routes
        2. Remote IP address         — fallback for public endpoints
    """
    try:
        from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
        verify_jwt_in_request(optional=True)
        identity = get_jwt_identity()
        if identity:
            return f"user:{identity}"
    except Exception:
        pass
    return get_remote_address()


limiter = Limiter(
    key_func=_rate_limit_key,
    # Storage is set in create_app() via app.config["RATELIMIT_STORAGE_URI"]
    # so we don't hard-code the Redis URL here.
    default_limits=["200 per day", "60 per hour"],
    default_limits_exempt_when=lambda: False,
)


# ── JWT Token Blocklist Loader ────────────────────────────────────────────────

@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header: dict, jwt_payload: dict) -> bool:
    """
    Called by Flask-JWT-Extended on every @jwt_required() request.
    Returns True (→ 401) if the token's jti is in the Redis blocklist.
    Enables stateful logout with stateless JWTs.
    """
    from app.utils.cache import is_token_blacklisted
    jti = jwt_payload.get("jti")
    if not jti:
        return False
    try:
        return is_token_blacklisted(jti)
    except Exception:
        # Redis unreachable — fail open rather than locking everyone out
        return False


# ── Custom JWT Error Responses ────────────────────────────────────────────────

@jwt.revoked_token_loader
def revoked_token_response(jwt_header: dict, jwt_payload: dict):
    from flask import jsonify
    return jsonify({"error": "Token has been revoked. Please log in again."}), 401


@jwt.expired_token_loader
def expired_token_response(jwt_header: dict, jwt_payload: dict):
    from flask import jsonify
    return jsonify({"error": "Token has expired. Please log in again."}), 401


@jwt.invalid_token_loader
def invalid_token_response(reason: str):
    from flask import jsonify
    return jsonify({"error": f"Invalid token: {reason}"}), 422


@jwt.unauthorized_loader
def missing_token_response(reason: str):
    from flask import jsonify
    return jsonify({"error": "Authentication required. Please provide a valid Bearer token."}), 401
