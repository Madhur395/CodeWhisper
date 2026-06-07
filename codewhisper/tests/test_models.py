"""
CodeWhisper — Phase 2: Database Model Tests
Tests all four models: User, Problem, UserProblemSession, HintLog.
Covers creation, relationships, constraints, and serialization.
"""

import uuid
import pytest
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError

from app.models.user import User
from app.models.problem import Problem
from app.models.session import UserProblemSession
from app.models.hint_log import HintLog


# ══════════════════════════════════════════════════════════════════════════════
# USER MODEL TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestUserModel:
    """Tests for the User model."""

    def test_user_creation(self, db):
        """User can be created with required fields."""
        user = User(
            username="alice",
            email="alice@example.com",
            password_hash="hashed_password_123"
        )
        db.session.add(user)
        db.session.commit()

        fetched = db.session.get(User, user.id)
        assert fetched is not None
        assert fetched.username == "alice"
        assert fetched.email == "alice@example.com"
        assert fetched.password_hash == "hashed_password_123"

    def test_user_id_is_uuid(self, db):
        """User primary key is a valid UUID."""
        user = User(username="bob", email="bob@example.com", password_hash="pw")
        db.session.add(user)
        db.session.commit()
        assert isinstance(user.id, uuid.UUID)

    def test_user_created_at_auto_set(self, db):
        """created_at is automatically set on insert."""
        user = User(username="carol", email="carol@example.com", password_hash="pw")
        db.session.add(user)
        db.session.commit()
        assert user.created_at is not None
        assert isinstance(user.created_at, datetime)

    def test_user_unique_email_constraint(self, db):
        """Two users with the same email should raise IntegrityError."""
        u1 = User(username="user1", email="dupe@example.com", password_hash="pw")
        u2 = User(username="user2", email="dupe@example.com", password_hash="pw")
        db.session.add(u1)
        db.session.commit()
        db.session.add(u2)
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

    def test_user_unique_username_constraint(self, db):
        """Two users with the same username should raise IntegrityError."""
        u1 = User(username="samename", email="e1@example.com", password_hash="pw")
        u2 = User(username="samename", email="e2@example.com", password_hash="pw")
        db.session.add(u1)
        db.session.commit()
        db.session.add(u2)
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

    def test_user_email_required(self, db):
        """User creation without email should fail."""
        user = User(username="nomail", password_hash="pw")
        db.session.add(user)
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

    def test_user_to_dict(self, sample_user):
        """to_dict() returns correct fields and excludes password_hash."""
        d = sample_user.to_dict()
        assert d["username"] == "testuser"
        assert d["email"] == "test@codewhisper.dev"
        assert "id" in d
        assert "created_at" in d
        assert "password_hash" not in d

    def test_user_repr(self, sample_user):
        """__repr__ includes username and email."""
        r = repr(sample_user)
        assert "testuser" in r
        assert "test@codewhisper.dev" in r

    def test_user_sessions_relationship_empty(self, db, sample_user):
        """A new user starts with zero sessions."""
        assert sample_user.sessions.count() == 0

    def test_user_sessions_relationship_populated(self, db, sample_user, sample_session):
        """User.sessions reflects created sessions."""
        assert sample_user.sessions.count() == 1
        s = sample_user.sessions.first()
        assert s.id == sample_session.id


# ══════════════════════════════════════════════════════════════════════════════
# PROBLEM MODEL TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestProblemModel:
    """Tests for the Problem model."""

    def test_problem_creation(self, db):
        """Problem can be created with all fields."""
        p = Problem(
            title="Binary Search",
            statement="Given a sorted array and a target, return its index.",
            tags=["Binary Search", "Array"],
            difficulty="Easy",
            source="LeetCode"
        )
        db.session.add(p)
        db.session.commit()

        fetched = db.session.get(Problem, p.id)
        assert fetched is not None
        assert fetched.title == "Binary Search"
        assert fetched.difficulty == "Easy"
        assert fetched.source == "LeetCode"

    def test_problem_id_is_uuid(self, db, sample_problem):
        """Problem primary key is a valid UUID."""
        assert isinstance(sample_problem.id, uuid.UUID)

    def test_problem_tags_stored_as_list(self, db, sample_problem):
        """Tags are stored and retrieved as a list."""
        assert isinstance(sample_problem.tags, list)
        assert "Array" in sample_problem.tags
        assert "HashMap" in sample_problem.tags

    def test_problem_tags_nullable(self, db):
        """Tags can be null for problems without tags."""
        p = Problem(title="Untitled", statement="Some problem.", tags=None)
        db.session.add(p)
        db.session.commit()
        assert p.tags is None

    def test_problem_created_at_auto_set(self, db, sample_problem):
        """created_at is automatically populated."""
        assert sample_problem.created_at is not None
        assert isinstance(sample_problem.created_at, datetime)

    def test_problem_to_dict(self, sample_problem):
        """to_dict() returns all expected fields."""
        d = sample_problem.to_dict()
        assert d["title"] == "Two Sum"
        assert d["difficulty"] == "Easy"
        assert d["source"] == "LeetCode"
        assert isinstance(d["tags"], list)
        assert "id" in d
        assert "statement" in d

    def test_problem_to_card_dict(self, sample_problem):
        """to_card_dict() excludes statement (compact form)."""
        d = sample_problem.to_card_dict()
        assert "statement" not in d
        assert d["title"] == "Two Sum"
        assert d["difficulty"] == "Easy"

    def test_problem_repr(self, sample_problem):
        """__repr__ includes title and difficulty."""
        r = repr(sample_problem)
        assert "Two Sum" in r
        assert "Easy" in r

    def test_problem_difficulty_options(self, db):
        """Various difficulty values are accepted."""
        for diff in ["Easy", "Medium", "Hard"]:
            p = Problem(
                title=f"Problem {diff}",
                statement="...",
                tags=[],
                difficulty=diff
            )
            db.session.add(p)
        db.session.commit()


# ══════════════════════════════════════════════════════════════════════════════
# USER PROBLEM SESSION MODEL TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestUserProblemSessionModel:
    """Tests for the UserProblemSession model."""

    def test_session_creation(self, db, sample_user, sample_problem):
        """Session can be created with user and problem FK."""
        s = UserProblemSession(
            user_id=sample_user.id,
            problem_id=sample_problem.id,
            problem_text="Given an array...",
            hints_requested=0,
            current_hint_level=0,
            is_solved=False
        )
        db.session.add(s)
        db.session.commit()

        fetched = db.session.get(UserProblemSession, s.id)
        assert fetched is not None
        assert fetched.user_id == sample_user.id
        assert fetched.problem_id == sample_problem.id
        assert fetched.is_solved is False

    def test_session_id_is_uuid(self, sample_session):
        """Session primary key is a valid UUID."""
        assert isinstance(sample_session.id, uuid.UUID)

    def test_session_defaults(self, db, sample_user):
        """Default values are applied on creation."""
        s = UserProblemSession(
            user_id=sample_user.id,
            problem_text="What is the time complexity of quicksort?"
        )
        db.session.add(s)
        db.session.commit()

        assert s.hints_requested == 0
        assert s.current_hint_level == 0
        assert s.is_solved is False
        assert s.started_at is not None
        assert s.solved_at is None

    def test_session_problem_id_nullable(self, db, sample_user):
        """Session can exist without a problem_id (custom pasted problem)."""
        s = UserProblemSession(
            user_id=sample_user.id,
            problem_text="Custom pasted problem...",
        )
        db.session.add(s)
        db.session.commit()
        assert s.problem_id is None

    def test_session_requires_user_id(self, db):
        """Session without user_id should fail (FK constraint)."""
        s = UserProblemSession(problem_text="some problem")
        db.session.add(s)
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

    def test_session_mark_solved(self, db, sample_session):
        """Session can be marked as solved with a timestamp."""
        sample_session.is_solved = True
        sample_session.solved_at = datetime.now(timezone.utc)
        db.session.commit()

        fetched = db.session.get(UserProblemSession, sample_session.id)
        assert fetched.is_solved is True
        assert fetched.solved_at is not None

    def test_session_hint_counter_increment(self, db, sample_session):
        """hints_requested and current_hint_level can be incremented."""
        sample_session.hints_requested += 1
        sample_session.current_hint_level = 2
        db.session.commit()

        fetched = db.session.get(UserProblemSession, sample_session.id)
        assert fetched.hints_requested == 2
        assert fetched.current_hint_level == 2

    def test_session_to_dict(self, sample_session):
        """to_dict() returns all expected fields."""
        d = sample_session.to_dict()
        assert "session_id" in d
        assert "user_id" in d
        assert "problem_preview" in d
        assert "hints_requested" in d
        assert "is_solved" in d
        assert "started_at" in d

    def test_session_repr(self, sample_session):
        """__repr__ includes user_id and is_solved."""
        r = repr(sample_session)
        assert "False" in r   # is_solved default

    def test_session_backref_user(self, sample_session, sample_user):
        """backref 'user' resolves to the correct User instance."""
        assert sample_session.user.id == sample_user.id
        assert sample_session.user.username == "testuser"

    def test_session_backref_problem(self, sample_session, sample_problem):
        """backref 'problem' resolves to the correct Problem instance."""
        assert sample_session.problem.id == sample_problem.id
        assert sample_session.problem.title == "Two Sum"

    def test_session_hint_logs_relationship_empty(self, db, sample_session):
        """A new session starts with zero hint logs."""
        assert sample_session.hint_logs.count() == 0

    def test_session_hint_logs_relationship_populated(self, db, sample_session, sample_hint_log):
        """hint_logs relationship reflects created hints."""
        assert sample_session.hint_logs.count() == 1
        h = sample_session.hint_logs.first()
        assert h.id == sample_hint_log.id


# ══════════════════════════════════════════════════════════════════════════════
# HINT LOG MODEL TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestHintLogModel:
    """Tests for the HintLog model."""

    def test_hint_log_creation(self, db, sample_session):
        """HintLog can be created with all required fields."""
        h = HintLog(
            session_id=sample_session.id,
            hint_level=1,
            hint_text="Think about what data structure gives O(1) lookup."
        )
        db.session.add(h)
        db.session.commit()

        fetched = db.session.get(HintLog, h.id)
        assert fetched is not None
        assert fetched.hint_level == 1
        assert "O(1)" in fetched.hint_text

    def test_hint_log_id_is_uuid(self, sample_hint_log):
        """HintLog primary key is a valid UUID."""
        assert isinstance(sample_hint_log.id, uuid.UUID)

    def test_hint_log_delivered_at_auto_set(self, sample_hint_log):
        """delivered_at is automatically set on insert."""
        assert sample_hint_log.delivered_at is not None
        assert isinstance(sample_hint_log.delivered_at, datetime)

    def test_hint_log_requires_session_id(self, db):
        """HintLog without session_id should fail (FK constraint)."""
        h = HintLog(hint_level=1, hint_text="some hint")
        db.session.add(h)
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

    def test_hint_log_requires_hint_text(self, db, sample_session):
        """HintLog without hint_text should fail (NOT NULL constraint)."""
        h = HintLog(session_id=sample_session.id, hint_level=2, hint_text=None)
        db.session.add(h)
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

    def test_hint_log_unique_level_per_session(self, db, sample_session):
        """Two hint logs with the same session_id + hint_level should fail."""
        h1 = HintLog(session_id=sample_session.id, hint_level=2, hint_text="First hint at level 2")
        h2 = HintLog(session_id=sample_session.id, hint_level=2, hint_text="Duplicate at level 2")
        db.session.add(h1)
        db.session.commit()
        db.session.add(h2)
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

    def test_hint_log_multiple_levels(self, db, sample_session):
        """Multiple hints at different levels are all accepted."""
        for level in range(1, 6):
            h = HintLog(
                session_id=sample_session.id,
                hint_level=level,
                hint_text=f"Hint at level {level}"
            )
            db.session.add(h)
        db.session.commit()

        all_hints = sample_session.hint_logs.all()
        assert len(all_hints) == 5
        levels = [h.hint_level for h in all_hints]
        assert sorted(levels) == [1, 2, 3, 4, 5]

    def test_hint_log_to_dict(self, sample_hint_log):
        """to_dict() returns all expected fields."""
        d = sample_hint_log.to_dict()
        assert "id" in d
        assert "session_id" in d
        assert d["hint_level"] == 1
        assert "hint_text" in d
        assert "delivered_at" in d

    def test_hint_log_repr(self, sample_hint_log):
        """__repr__ includes session_id and hint_level."""
        r = repr(sample_hint_log)
        assert "hint_level=1" in r

    def test_hint_log_backref_session(self, sample_hint_log, sample_session):
        """backref 'session' resolves to the correct session."""
        assert sample_hint_log.session.id == sample_session.id


# ══════════════════════════════════════════════════════════════════════════════
# CROSS-MODEL / RELATIONSHIP TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestModelRelationships:
    """Tests for cross-model relationships and cascades."""

    def test_full_chain_user_session_hint(self, db, sample_user, sample_problem):
        """Full chain: User → Session → HintLog works end-to-end."""
        # Create session
        session = UserProblemSession(
            user_id=sample_user.id,
            problem_id=sample_problem.id,
            problem_text="Chain test problem.",
            hints_requested=3,
            current_hint_level=3
        )
        db.session.add(session)
        db.session.commit()

        # Add 3 hints
        for i in range(1, 4):
            hint = HintLog(
                session_id=session.id,
                hint_level=i,
                hint_text=f"Hint number {i}"
            )
            db.session.add(hint)
        db.session.commit()

        # Traverse the chain
        fetched_user = db.session.get(User, sample_user.id)
        fetched_session = fetched_user.sessions.first()
        fetched_hints = fetched_session.hint_logs.all()

        assert fetched_session is not None
        assert len(fetched_hints) == 3
        assert fetched_hints[0].hint_level == 1

    def test_cascade_delete_user_removes_sessions(self, db, sample_user, sample_session):
        """Deleting a user cascades to their sessions."""
        session_id = sample_session.id
        db.session.delete(sample_user)
        db.session.commit()

        assert db.session.get(UserProblemSession, session_id) is None

    def test_cascade_delete_session_removes_hints(self, db, sample_session, sample_hint_log):
        """Deleting a session cascades to its hint logs."""
        hint_id = sample_hint_log.id
        db.session.delete(sample_session)
        db.session.commit()

        assert db.session.get(HintLog, hint_id) is None

    def test_multiple_sessions_per_user(self, db, sample_user):
        """A user can have multiple sessions."""
        for i in range(3):
            s = UserProblemSession(
                user_id=sample_user.id,
                problem_text=f"Problem {i}"
            )
            db.session.add(s)
        db.session.commit()

        assert sample_user.sessions.count() == 3

    def test_query_sessions_by_user_id(self, db, sample_user, sample_session):
        """Sessions can be queried by user_id."""
        results = UserProblemSession.query.filter_by(user_id=sample_user.id).all()
        assert len(results) >= 1
        assert all(s.user_id == sample_user.id for s in results)

    def test_query_hint_logs_by_session_ordered(self, db, sample_session):
        """HintLogs are returned ordered by hint_level."""
        for level in [3, 1, 2]:
            db.session.add(HintLog(
                session_id=sample_session.id,
                hint_level=level,
                hint_text=f"Hint {level}"
            ))
        db.session.commit()

        hints = sample_session.hint_logs.all()
        levels = [h.hint_level for h in hints]
        assert levels == sorted(levels)

    def test_db_tables_created(self, db):
        """All expected tables exist in the test database."""
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        assert "users" in tables
        assert "problems" in tables
        assert "user_problem_sessions" in tables
        assert "hint_logs" in tables
