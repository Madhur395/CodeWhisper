"""
CodeWhisper — UserProblemSession Model
Tracks a single user's attempt at solving a specific problem.

Table: user_problem_sessions
Relationships:
    - Many sessions → one User (backref: 'user')
    - Many sessions → one Problem (optional, backref: 'problem')
    - One session → many HintLogs (backref: 'session')
"""

import uuid
from datetime import datetime, timezone
from app.extensions import db


class UserProblemSession(db.Model):
    __tablename__ = "user_problem_sessions"

    # ── Primary Key ───────────────────────────────────────────────────────────
    id = db.Column(
        db.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )

    # ── Foreign Keys ──────────────────────────────────────────────────────────
    user_id = db.Column(
        db.UUID(as_uuid=True),
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    # Nullable: custom pasted problems won't have a DB problem_id
    problem_id = db.Column(
        db.UUID(as_uuid=True),
        db.ForeignKey("problems.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # ── Fields ────────────────────────────────────────────────────────────────
    # Raw problem text pasted by the user
    problem_text = db.Column(db.Text, nullable=True)

    # Number of hints the user has been shown
    hints_requested = db.Column(db.Integer, default=0, nullable=False)

    # Current depth level (1–5); 0 = session started but no hint shown yet
    current_hint_level = db.Column(db.Integer, default=0, nullable=False)

    # True once the user clicks "Mark as Solved"
    is_solved = db.Column(db.Boolean, default=False, nullable=False)

    started_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    solved_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    hint_logs = db.relationship(
        "HintLog",
        backref="session",
        lazy="dynamic",
        cascade="all, delete-orphan",
        order_by="HintLog.hint_level"
    )

    # ── Repr ──────────────────────────────────────────────────────────────────
    def __repr__(self):
        return (
            f"<UserProblemSession id={self.id} user_id={self.user_id} "
            f"hints={self.hints_requested} solved={self.is_solved}>"
        )

    # ── Serialization ─────────────────────────────────────────────────────────
    def to_dict(self):
        """Full representation for API responses."""
        return {
            "session_id": str(self.id),
            "user_id": str(self.user_id),
            "problem_id": str(self.problem_id) if self.problem_id else None,
            "problem_preview": (
                (self.problem_text[:120] + "...") if self.problem_text else None
            ),
            "hints_requested": self.hints_requested,
            "current_hint_level": self.current_hint_level,
            "is_solved": self.is_solved,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "solved_at": self.solved_at.isoformat() if self.solved_at else None,
        }
