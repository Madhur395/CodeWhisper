"""
CodeWhisper — User Model
Represents a registered user of the platform.

Table: users
Relationships:
    - One user → many UserProblemSessions (backref: 'user')
"""

import uuid
from datetime import datetime, timezone
from app.extensions import db


class User(db.Model):
    __tablename__ = "users"

    # ── Primary Key ───────────────────────────────────────────────────────────
    id = db.Column(
        db.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )

    # ── Fields ────────────────────────────────────────────────────────────────
    username = db.Column(db.String(100), unique=True, nullable=False, index=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.Text, nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    sessions = db.relationship(
        "UserProblemSession",
        backref="user",
        lazy="dynamic",       # Use .all() or .filter() on the query
        cascade="all, delete-orphan"
    )

    # ── Repr ──────────────────────────────────────────────────────────────────
    def __repr__(self):
        return f"<User id={self.id} username={self.username!r} email={self.email!r}>"

    # ── Serialization ─────────────────────────────────────────────────────────
    def to_dict(self):
        """Return a safe public representation (no password hash)."""
        return {
            "id": str(self.id),
            "username": self.username,
            "email": self.email,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
