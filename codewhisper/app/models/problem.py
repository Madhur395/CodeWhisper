"""
CodeWhisper — Problem Model
Represents a curated DSA / coding problem in the platform's problem bank.

Table: problems
Relationships:
    - One problem → many UserProblemSessions (optional FK; sessions may have no problem_id
      when the user pastes a custom problem not in the bank)
"""

import uuid
from datetime import datetime, timezone
from app.extensions import db


class Problem(db.Model):
    __tablename__ = "problems"

    # ── Primary Key ───────────────────────────────────────────────────────────
    id = db.Column(
        db.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )

    # ── Fields ────────────────────────────────────────────────────────────────
    title = db.Column(db.String(255), nullable=False, index=True)
    statement = db.Column(db.Text, nullable=False)

    # Stored as a JSON array of strings e.g. ["Array", "HashMap", "DP"]
    # Using JSON type for SQLite compatibility in tests; ARRAY for PostgreSQL
    tags = db.Column(db.JSON, nullable=True)

    # "Easy" | "Medium" | "Hard"
    difficulty = db.Column(db.String(20), nullable=True, index=True)

    # "LeetCode" | "Codeforces" | "HackerRank" | "Classic" | "Custom"
    source = db.Column(db.String(100), nullable=True)

    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    sessions = db.relationship(
        "UserProblemSession",
        backref="problem",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )

    # ── Repr ──────────────────────────────────────────────────────────────────
    def __repr__(self):
        return (
            f"<Problem id={self.id} title={self.title!r} "
            f"difficulty={self.difficulty!r} tags={self.tags}>"
        )

    # ── Serialization ─────────────────────────────────────────────────────────
    def to_dict(self):
        """Return a dict representation suitable for JSON responses."""
        return {
            "id": str(self.id),
            "title": self.title,
            "statement": self.statement,
            "tags": self.tags or [],
            "difficulty": self.difficulty,
            "source": self.source,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def to_card_dict(self):
        """Compact representation for recommendation cards (no full statement)."""
        return {
            "id": str(self.id),
            "title": self.title,
            "tags": self.tags or [],
            "difficulty": self.difficulty,
            "source": self.source,
        }
