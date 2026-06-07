"""
CodeWhisper — Input Validators & Password Utilities
Phase 3: Full implementation with bcrypt password hashing.
"""

import re
import bcrypt


# ── Password Hashing ──────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    """
    Hash a plaintext password using bcrypt with a random salt.

    Args:
        password (str): Plaintext password.

    Returns:
        str: Bcrypt-hashed password string.
    """
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """
    Verify a plaintext password against a stored bcrypt hash.

    Args:
        password (str): Plaintext password to check.
        hashed (str): Stored bcrypt hash.

    Returns:
        bool: True if the password matches, False otherwise.
    """
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


# ── Email Validation ──────────────────────────────────────────────────────────

_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

def is_valid_email(email: str) -> bool:
    """Return True if the email address looks syntactically valid."""
    return bool(_EMAIL_RE.match(email.strip()))


# ── Registration Payload Validation ──────────────────────────────────────────

def validate_register_payload(data: dict) -> tuple[bool, str]:
    """
    Validate the POST /auth/register request body.

    Rules:
        - username: required, 3–100 chars, alphanumeric + underscores only
        - email: required, valid format
        - password: required, minimum 8 characters

    Args:
        data (dict): Parsed JSON request body.

    Returns:
        tuple[bool, str]: (is_valid, error_message). error_message is "" on success.
    """
    if not data:
        return False, "Request body is missing or not valid JSON."

    username = data.get("username", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "")

    if not username:
        return False, "Username is required."
    if len(username) < 3:
        return False, "Username must be at least 3 characters."
    if len(username) > 100:
        return False, "Username must be at most 100 characters."
    if not re.match(r"^[a-zA-Z0-9_]+$", username):
        return False, "Username may only contain letters, numbers, and underscores."

    if not email:
        return False, "Email is required."
    if not is_valid_email(email):
        return False, "Email address is not valid."

    if not password:
        return False, "Password is required."
    if len(password) < 8:
        return False, "Password must be at least 8 characters."
    if len(password) > 128:
        return False, "Password must be at most 128 characters."

    return True, ""


def validate_login_payload(data: dict) -> tuple[bool, str]:
    """
    Validate the POST /auth/login request body.

    Args:
        data (dict): Parsed JSON request body.

    Returns:
        tuple[bool, str]: (is_valid, error_message).
    """
    if not data:
        return False, "Request body is missing or not valid JSON."
    if not data.get("email", "").strip():
        return False, "Email is required."
    if not data.get("password", ""):
        return False, "Password is required."
    return True, ""


# ── Problem Input Validation ──────────────────────────────────────────────────

def validate_problem_input(problem_text: str) -> tuple[bool, str]:
    """
    Validate a pasted DSA/coding problem text.

    Args:
        problem_text (str): Raw problem text from the user.

    Returns:
        tuple[bool, str]: (is_valid, error_message).
    """
    if not problem_text or not problem_text.strip():
        return False, "Problem text cannot be empty."
    if len(problem_text.strip()) < 20:
        return False, "Problem text is too short (minimum 20 characters)."
    if len(problem_text) > 10_000:
        return False, "Problem text is too long (maximum 10,000 characters)."
    return True, ""
