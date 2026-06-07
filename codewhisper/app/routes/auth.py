"""
CodeWhisper — Authentication Routes
Phase 3: Full implementation of register, login, logout, and /me.
Phase 7: Rate limiting applied on register and login to prevent brute-force.

Endpoints:
    POST  /auth/register  — Create a new user account
    POST  /auth/login     — Authenticate and receive a JWT token
    POST  /auth/logout    — Invalidate the current JWT (Redis blocklist)
    GET   /auth/me        — Return the authenticated user's profile

Rate limits:
    POST /auth/register — 10 per hour  (prevent account spam)
    POST /auth/login    — 20 per hour  (prevent password brute-force)
"""

import uuid as _uuid

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import (
    create_access_token,
    jwt_required,
    get_jwt_identity,
    get_jwt,
)

from app.extensions import db, limiter
from app.models.user import User
from app.utils.validators import (
    hash_password,
    verify_password,
    validate_register_payload,
    validate_login_payload,
)
from app.utils.cache import blacklist_token

auth_bp = Blueprint("auth", __name__)


# ── POST /auth/register ───────────────────────────────────────────────────────

@auth_bp.route("/register", methods=["POST"])
@limiter.limit("10 per hour", error_message="Too many registration attempts. Please wait before trying again.")
def register():
    """
    Register a new CodeWhisper user.

    Request body (JSON):
        {
            "username": "alice",
            "email":    "alice@example.com",
            "password": "securepass123"
        }

    Responses:
        201 — User created; returns access_token + user profile
        400 — Validation error (missing / invalid fields)
        409 — Email or username already taken
        429 — Rate limit exceeded
    """
    data = request.get_json(silent=True)

    is_valid, error_msg = validate_register_payload(data)
    if not is_valid:
        return jsonify({"error": error_msg}), 400

    username = data["username"].strip()
    email    = data["email"].strip().lower()
    password = data["password"]

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "An account with this email already exists."}), 409

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "This username is already taken."}), 409

    user = User(
        username=username,
        email=email,
        password_hash=hash_password(password),
    )
    db.session.add(user)
    db.session.commit()

    access_token = create_access_token(identity=str(user.id))

    return jsonify({
        "message":      "Account created successfully.",
        "access_token": access_token,
        "user":         user.to_dict(),
    }), 201


# ── POST /auth/login ──────────────────────────────────────────────────────────

@auth_bp.route("/login", methods=["POST"])
@limiter.limit("20 per hour", error_message="Too many login attempts. Please wait before trying again.")
def login():
    """
    Authenticate a user and return a JWT access token.

    Request body (JSON):
        {
            "email":    "alice@example.com",
            "password": "securepass123"
        }

    Responses:
        200 — Login successful; returns access_token + user profile
        400 — Validation error
        401 — Invalid credentials
        429 — Rate limit exceeded
    """
    data = request.get_json(silent=True)

    is_valid, error_msg = validate_login_payload(data)
    if not is_valid:
        return jsonify({"error": error_msg}), 400

    email    = data["email"].strip().lower()
    password = data["password"]

    user = User.query.filter_by(email=email).first()

    # Uniform error message — prevents user enumeration
    if not user or not verify_password(password, user.password_hash):
        return jsonify({"error": "Invalid email or password."}), 401

    access_token = create_access_token(identity=str(user.id))

    return jsonify({
        "message":      "Login successful.",
        "access_token": access_token,
        "user":         user.to_dict(),
    }), 200


# ── POST /auth/logout ─────────────────────────────────────────────────────────

@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    """
    Invalidate the current JWT by adding its jti to the Redis blocklist.

    Requires:
        Authorization: Bearer <token>

    Responses:
        200 — Logged out successfully
        401 — Missing or invalid token
    """
    jwt_payload = get_jwt()
    jti         = jwt_payload["jti"]
    expires_in  = current_app.config.get("JWT_ACCESS_TOKEN_EXPIRES", 3600)

    blacklist_token(jti, expires_in)

    return jsonify({"message": "Logged out successfully."}), 200


# ── GET /auth/me ──────────────────────────────────────────────────────────────

@auth_bp.route("/me", methods=["GET"])
@jwt_required()
@limiter.limit("60 per hour", error_message="Profile fetch limit reached (60/hour).")
def me():
    """
    Return the profile of the currently authenticated user.

    Requires:
        Authorization: Bearer <token>

    Responses:
        200 — { user: { id, username, email, created_at } }
        401 — Missing or invalid token
        404 — User not found (deleted account edge case)
        422 — Malformed token identity
    """
    user_id = get_jwt_identity()

    try:
        uid = _uuid.UUID(user_id)
    except (ValueError, AttributeError):
        return jsonify({"error": "Invalid token identity."}), 422

    user = User.query.filter_by(id=uid).first()
    if not user:
        return jsonify({"error": "User not found."}), 404

    return jsonify({"user": user.to_dict()}), 200
