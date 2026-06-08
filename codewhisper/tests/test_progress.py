"""
CodeWhisper — Phase 6: Progress Tracker & Recommender Tests
Covers ProgressTrackerService, RecommenderService, all routes, and seed script.
"""

import uuid
import pytest
from datetime import datetime, timezone
from unittest.mock import patch

# ── Shared helpers ────────────────────────────────────────────────────────────

def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def register_and_login(client, username=None, email=None, password="Pass1234"):
    uid = uuid.uuid4().hex[:8]
    username = username or f"user_{uid}"
    email    = email    or f"{uid}@cw.dev"
    client.post("/auth/register", json={"username": username, "email": email, "password": password})
    resp = client.post("/auth/login", json={"email": email, "password": password})
    data = resp.get_json()
    assert "access_token" in data, f"Login failed: {data}"
    return data["access_token"]


def make_session(db, user, problem=None, hints_requested=2,
                 current_hint_level=2, is_solved=False, solved_at=None):
    """Helper to create a UserProblemSession directly in DB."""
    from app.models.session import UserProblemSession
    s = UserProblemSession(
        user_id=user.id,
        problem_id=problem.id if problem else None,
        problem_text=(problem.statement if problem else "Custom pasted problem text for testing."),
        hints_requested=hints_requested,
        current_hint_level=current_hint_level,
        is_solved=is_solved,
        solved_at=solved_at,
    )
    db.session.add(s)
    db.session.commit()
    return s


def make_problem(db, title="Test Problem", tags=None, difficulty="Medium", source="LeetCode"):
    """Helper to create a Problem directly in DB."""
    from app.models.problem import Problem
    p = Problem(
        title=title,
        statement=f"Statement for {title}. " * 5,
        tags=tags or ["Array", "HashMap"],
        difficulty=difficulty,
        source=source,
    )
    db.session.add(p)
    db.session.commit()
    return p


# ══════════════════════════════════════════════════════════════════════════════
# PROGRESS TRACKER SERVICE — UNIT TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestProgressTrackerServiceUnit:

    # ── get_history ────────────────────────────────────────────────────────────

    def test_get_history_returns_empty_for_new_user(self, app, db, sample_user):
        from app.services.progress_tracker import ProgressTrackerService
        with app.app_context():
            result = ProgressTrackerService().get_history(str(sample_user.id))
        assert result["sessions"] == []
        assert result["total"] == 0

    def test_get_history_returns_sessions(self, app, db, sample_user, sample_problem):
        from app.services.progress_tracker import ProgressTrackerService
        with app.app_context():
            make_session(db, sample_user, sample_problem)
            make_session(db, sample_user, sample_problem)
            result = ProgressTrackerService().get_history(str(sample_user.id))
        assert result["total"] == 2
        assert len(result["sessions"]) == 2

    def test_get_history_ordered_newest_first(self, app, db, sample_user, sample_problem):
        from app.services.progress_tracker import ProgressTrackerService
        with app.app_context():
            s1 = make_session(db, sample_user, sample_problem)
            s2 = make_session(db, sample_user, sample_problem)
            result = ProgressTrackerService().get_history(str(sample_user.id))
        # Newest session should be first
        session_ids = [s["session_id"] for s in result["sessions"]]
        assert session_ids[0] == str(s2.id)

    def test_get_history_session_dict_structure(self, app, db, sample_user, sample_problem):
        from app.services.progress_tracker import ProgressTrackerService
        with app.app_context():
            make_session(db, sample_user, sample_problem, hints_requested=3, is_solved=True,
                         solved_at=datetime.now(timezone.utc))
            result = ProgressTrackerService().get_history(str(sample_user.id))
        s = result["sessions"][0]
        assert "session_id"      in s
        assert "problem_preview" in s
        assert "hints_used"      in s
        assert "is_solved"       in s
        assert "started_at"      in s
        assert "solved_at"       in s
        assert s["hints_used"]   == 3
        assert s["is_solved"]    is True
        assert s["solved_at"]    is not None

    def test_get_history_pagination_page_1(self, app, db, sample_user, sample_problem):
        from app.services.progress_tracker import ProgressTrackerService
        with app.app_context():
            for _ in range(5):
                make_session(db, sample_user, sample_problem)
            result = ProgressTrackerService().get_history(
                str(sample_user.id), page=1, per_page=3
            )
        assert len(result["sessions"]) == 3
        assert result["total"]   == 5
        assert result["pages"]   == 2
        assert result["page"]    == 1

    def test_get_history_pagination_page_2(self, app, db, sample_user, sample_problem):
        from app.services.progress_tracker import ProgressTrackerService
        with app.app_context():
            for _ in range(5):
                make_session(db, sample_user, sample_problem)
            result = ProgressTrackerService().get_history(
                str(sample_user.id), page=2, per_page=3
            )
        assert len(result["sessions"]) == 2

    def test_get_history_per_page_clamped_to_100(self, app, db, sample_user, sample_problem):
        from app.services.progress_tracker import ProgressTrackerService
        with app.app_context():
            result = ProgressTrackerService().get_history(
                str(sample_user.id), per_page=9999
            )
        assert result["per_page"] == 100

    def test_get_history_only_returns_own_sessions(self, app, db, sample_user, sample_problem):
        """Sessions of other users must not appear."""
        from app.services.progress_tracker import ProgressTrackerService
        from app.models.user import User
        from app.utils.validators import hash_password
        with app.app_context():
            other = User(username="other_u", email="other@cw.dev",
                         password_hash=hash_password("pass1234"))
            db.session.add(other)
            db.session.commit()
            make_session(db, sample_user, sample_problem)
            make_session(db, other, sample_problem)
            result = ProgressTrackerService().get_history(str(sample_user.id))
        assert result["total"] == 1

    # ── get_stats ──────────────────────────────────────────────────────────────

    def test_get_stats_zero_for_new_user(self, app, db, sample_user):
        from app.services.progress_tracker import ProgressTrackerService
        with app.app_context():
            stats = ProgressTrackerService().get_stats(str(sample_user.id))
        assert stats["total_attempted"]           == 0
        assert stats["total_solved"]              == 0
        assert stats["solve_rate"]                == "0%"
        assert stats["average_hints_per_problem"] == 0.0

    def test_get_stats_calculates_totals(self, app, db, sample_user, sample_problem):
        from app.services.progress_tracker import ProgressTrackerService
        with app.app_context():
            make_session(db, sample_user, sample_problem, hints_requested=3, is_solved=True,
                         solved_at=datetime.now(timezone.utc))
            make_session(db, sample_user, sample_problem, hints_requested=5, is_solved=True,
                         solved_at=datetime.now(timezone.utc))
            make_session(db, sample_user, sample_problem, hints_requested=1, is_solved=False)
            stats = ProgressTrackerService().get_stats(str(sample_user.id))
        assert stats["total_attempted"] == 3
        assert stats["total_solved"]    == 2

    def test_get_stats_solve_rate_correct(self, app, db, sample_user, sample_problem):
        from app.services.progress_tracker import ProgressTrackerService
        with app.app_context():
            make_session(db, sample_user, sample_problem, is_solved=True,
                         solved_at=datetime.now(timezone.utc))
            make_session(db, sample_user, sample_problem, is_solved=True,
                         solved_at=datetime.now(timezone.utc))
            make_session(db, sample_user, sample_problem, is_solved=False)
            make_session(db, sample_user, sample_problem, is_solved=False)
            stats = ProgressTrackerService().get_stats(str(sample_user.id))
        assert stats["solve_rate"] == "50.0%"

    def test_get_stats_average_hints(self, app, db, sample_user, sample_problem):
        from app.services.progress_tracker import ProgressTrackerService
        with app.app_context():
            make_session(db, sample_user, sample_problem, hints_requested=2)
            make_session(db, sample_user, sample_problem, hints_requested=4)
            stats = ProgressTrackerService().get_stats(str(sample_user.id))
        assert stats["average_hints_per_problem"] == 3.0

    def test_get_stats_top_tags_from_linked_problems(self, app, db, sample_user):
        from app.services.progress_tracker import ProgressTrackerService
        with app.app_context():
            p1 = make_problem(db, "P1", tags=["DP", "Array"])
            p2 = make_problem(db, "P2", tags=["DP", "Tree"])
            p3 = make_problem(db, "P3", tags=["Array"])
            make_session(db, sample_user, p1)
            make_session(db, sample_user, p2)
            make_session(db, sample_user, p3)
            stats = ProgressTrackerService().get_stats(str(sample_user.id))
        # DP appears 2x, Array 2x, Tree 1x
        assert "DP" in stats["top_tags"]
        assert "Array" in stats["top_tags"]

    def test_get_stats_has_all_expected_keys(self, app, db, sample_user):
        from app.services.progress_tracker import ProgressTrackerService
        with app.app_context():
            stats = ProgressTrackerService().get_stats(str(sample_user.id))
        for key in ["total_attempted", "total_solved", "solve_rate",
                    "average_hints_per_problem", "top_tags"]:
            assert key in stats

    # ── mark_solved ────────────────────────────────────────────────────────────

    def test_mark_solved_sets_is_solved_true(self, app, db, sample_user, sample_problem):
        from app.services.progress_tracker import ProgressTrackerService
        from app.models.session import UserProblemSession
        with app.app_context():
            session = make_session(db, sample_user, sample_problem, is_solved=False)
            ProgressTrackerService().mark_solved(str(session.id), str(sample_user.id))
            refreshed = UserProblemSession.query.get(session.id)
        assert refreshed.is_solved is True

    def test_mark_solved_sets_solved_at_timestamp(self, app, db, sample_user, sample_problem):
        from app.services.progress_tracker import ProgressTrackerService
        from app.models.session import UserProblemSession
        with app.app_context():
            session = make_session(db, sample_user, sample_problem, is_solved=False)
            ProgressTrackerService().mark_solved(str(session.id), str(sample_user.id))
            refreshed = UserProblemSession.query.get(session.id)
        assert refreshed.solved_at is not None

    def test_mark_solved_returns_confirmation(self, app, db, sample_user, sample_problem):
        from app.services.progress_tracker import ProgressTrackerService
        with app.app_context():
            session = make_session(db, sample_user, sample_problem)
            result = ProgressTrackerService().mark_solved(str(session.id), str(sample_user.id))
        assert "message"    in result
        assert "session_id" in result
        assert "solved_at"  in result

    def test_mark_solved_idempotent(self, app, db, sample_user, sample_problem):
        from app.services.progress_tracker import ProgressTrackerService
        with app.app_context():
            session = make_session(db, sample_user, sample_problem, is_solved=True,
                                   solved_at=datetime.now(timezone.utc))
            result = ProgressTrackerService().mark_solved(str(session.id), str(sample_user.id))
        assert "already" in result["message"].lower()

    def test_mark_solved_404_wrong_user(self, app, db, sample_user, sample_problem):
        from app.services.progress_tracker import ProgressTrackerService
        from werkzeug.exceptions import NotFound
        with app.app_context():
            session = make_session(db, sample_user, sample_problem)
            with pytest.raises((NotFound, Exception)):
                ProgressTrackerService().mark_solved(str(session.id), str(uuid.uuid4()))

    def test_mark_solved_404_unknown_session(self, app, db, sample_user):
        from app.services.progress_tracker import ProgressTrackerService
        from werkzeug.exceptions import NotFound
        with app.app_context():
            with pytest.raises((NotFound, Exception)):
                ProgressTrackerService().mark_solved(str(uuid.uuid4()), str(sample_user.id))

    # ── get_concept_breakdown ──────────────────────────────────────────────────

    def test_concept_breakdown_empty_for_new_user(self, app, db, sample_user):
        from app.services.progress_tracker import ProgressTrackerService
        with app.app_context():
            result = ProgressTrackerService().get_concept_breakdown(str(sample_user.id))
        assert result == []

    def test_concept_breakdown_counts_tags(self, app, db, sample_user):
        from app.services.progress_tracker import ProgressTrackerService
        with app.app_context():
            p1 = make_problem(db, "C1", tags=["DP", "Array"])
            p2 = make_problem(db, "C2", tags=["DP"])
            make_session(db, sample_user, p1)
            make_session(db, sample_user, p2)
            result = ProgressTrackerService().get_concept_breakdown(str(sample_user.id))
        tag_map = {r["tag"]: r["count"] for r in result}
        assert tag_map.get("DP")    == 2
        assert tag_map.get("Array") == 1

    def test_concept_breakdown_sorted_by_count_desc(self, app, db, sample_user):
        from app.services.progress_tracker import ProgressTrackerService
        with app.app_context():
            p1 = make_problem(db, "D1", tags=["DP", "Array", "Graph"])
            p2 = make_problem(db, "D2", tags=["DP"])
            make_session(db, sample_user, p1)
            make_session(db, sample_user, p2)
            result = ProgressTrackerService().get_concept_breakdown(str(sample_user.id))
        counts = [r["count"] for r in result]
        assert counts == sorted(counts, reverse=True)


# ══════════════════════════════════════════════════════════════════════════════
# RECOMMENDER SERVICE — UNIT TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestRecommenderServiceUnit:

    def test_recommend_returns_empty_when_no_problems(self, app, db, sample_user):
        from app.services.recommender import RecommenderService
        with app.app_context():
            result = RecommenderService().recommend(str(sample_user.id))
        assert result == []

    def test_recommend_returns_problems(self, app, db, sample_user):
        from app.services.recommender import RecommenderService
        with app.app_context():
            for i in range(6):
                make_problem(db, f"Problem {i}")
            result = RecommenderService().recommend(str(sample_user.id))
        assert len(result) > 0

    def test_recommend_respects_limit(self, app, db, sample_user):
        from app.services.recommender import RecommenderService
        with app.app_context():
            for i in range(10):
                make_problem(db, f"Lim Problem {i}")
            result = RecommenderService().recommend(str(sample_user.id), limit=3)
        assert len(result) <= 3

    def test_recommend_excludes_attempted_problems(self, app, db, sample_user):
        from app.services.recommender import RecommenderService
        with app.app_context():
            p_attempted = make_problem(db, "Attempted")
            p_unseen    = make_problem(db, "Unseen")
            make_session(db, sample_user, p_attempted)
            result = RecommenderService().recommend(str(sample_user.id))
        result_ids = [r["problem_id"] for r in result]
        assert str(p_attempted.id) not in result_ids
        assert str(p_unseen.id)    in result_ids

    def test_recommend_card_has_required_fields(self, app, db, sample_user):
        from app.services.recommender import RecommenderService
        with app.app_context():
            make_problem(db, "Fields Problem")
            result = RecommenderService().recommend(str(sample_user.id))
        card = result[0]
        for field in ["problem_id", "title", "difficulty", "tags", "source", "statement_preview"]:
            assert field in card

    def test_recommend_prefers_tag_overlap(self, app, db, sample_user):
        """
        User solved a DP problem → recommender should surface other DP problems
        over unrelated ones.
        """
        from app.services.recommender import RecommenderService
        with app.app_context():
            solved_p = make_problem(db, "Solved DP",   tags=["DP"])
            dp_p     = make_problem(db, "Unseen DP",   tags=["DP"])
            trie_p   = make_problem(db, "Unseen Trie", tags=["Trie"])

            # User solved the DP problem
            make_session(db, sample_user, solved_p,
                         is_solved=True, solved_at=datetime.now(timezone.utc))

            result = RecommenderService().recommend(str(sample_user.id), limit=2)

        result_titles = [r["title"] for r in result]
        # DP unseen should score higher and appear
        assert "Unseen DP" in result_titles

    def test_recommend_default_limit_is_5(self, app, db, sample_user):
        from app.services.recommender import RecommenderService
        with app.app_context():
            for i in range(10):
                make_problem(db, f"Default Lim {i}")
            result = RecommenderService().recommend(str(sample_user.id))
        assert len(result) <= 5

    def test_recommend_max_limit_clamped_to_20(self, app, db, sample_user):
        from app.services.recommender import RecommenderService
        with app.app_context():
            for i in range(30):
                make_problem(db, f"Max Lim {i}")
            result = RecommenderService().recommend(str(sample_user.id), limit=999)
        assert len(result) <= 20

    def test_recommend_all_results_are_unseen(self, app, db, sample_user):
        from app.services.recommender import RecommenderService
        with app.app_context():
            attempted = [make_problem(db, f"Att {i}") for i in range(3)]
            unseen    = [make_problem(db, f"Uns {i}") for i in range(4)]
            for p in attempted:
                make_session(db, sample_user, p)
            result = RecommenderService().recommend(str(sample_user.id))
        attempted_ids = {str(p.id) for p in attempted}
        for card in result:
            assert card["problem_id"] not in attempted_ids


# ══════════════════════════════════════════════════════════════════════════════
# PROGRESS ROUTES — INTEGRATION TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestProgressHistoryEndpoint:

    def test_history_returns_200(self, client):
        token = register_and_login(client)
        resp = client.get("/progress/history", headers=auth_headers(token))
        assert resp.status_code == 200

    def test_history_requires_auth(self, client):
        resp = client.get("/progress/history")
        assert resp.status_code == 401

    def test_history_empty_for_new_user(self, client):
        token = register_and_login(client)
        resp  = client.get("/progress/history", headers=auth_headers(token))
        body  = resp.get_json()
        assert body["total"]    == 0
        assert body["sessions"] == []

    def test_history_pagination_params(self, client):
        token = register_and_login(client)
        resp  = client.get("/progress/history?page=1&per_page=5",
                           headers=auth_headers(token))
        body = resp.get_json()
        assert "page"     in body
        assert "per_page" in body
        assert "pages"    in body
        assert "total"    in body

    def test_history_sessions_created_via_hint_submit(self, client, db):
        """Sessions submitted via /hints/submit appear in history."""
        from app.services.hint_engine import HintEngineService
        from unittest.mock import MagicMock
        token = register_and_login(client)

        mock_llm = MagicMock()
        mock_llm.generate_hints.return_value = [
            "H1", "H2", "H3", "H4", "H5"
        ]
        with patch("app.services.hint_engine.get_llm_client", return_value=mock_llm):
            client.post(
                "/hints/submit",
                json={"problem_text": "A" * 50},
                headers=auth_headers(token),
            )

        resp = client.get("/progress/history", headers=auth_headers(token))
        assert resp.get_json()["total"] == 1


class TestProgressStatsEndpoint:

    def test_stats_returns_200(self, client):
        token = register_and_login(client)
        resp  = client.get("/progress/stats", headers=auth_headers(token))
        assert resp.status_code == 200

    def test_stats_requires_auth(self, client):
        resp = client.get("/progress/stats")
        assert resp.status_code == 401

    def test_stats_zero_for_new_user(self, client):
        token = register_and_login(client)
        body  = client.get("/progress/stats", headers=auth_headers(token)).get_json()
        assert body["total_attempted"]           == 0
        assert body["total_solved"]              == 0
        assert body["solve_rate"]                == "0%"
        assert body["average_hints_per_problem"] == 0.0

    def test_stats_has_top_tags_key(self, client):
        token = register_and_login(client)
        body  = client.get("/progress/stats", headers=auth_headers(token)).get_json()
        assert "top_tags" in body


class TestMarkSolvedEndpoint:

    def test_mark_solved_returns_200(self, client, db, sample_user, sample_user_token,
                                     sample_problem):
        session = make_session(db, sample_user, sample_problem)
        resp = client.patch(
            f"/progress/solve/{session.id}",
            headers=auth_headers(sample_user_token),
        )
        assert resp.status_code == 200

    def test_mark_solved_requires_auth(self, client):
        resp = client.patch(f"/progress/solve/{uuid.uuid4()}")
        assert resp.status_code == 401

    def test_mark_solved_404_on_unknown_session(self, client):
        token = register_and_login(client)
        resp  = client.patch(
            f"/progress/solve/{uuid.uuid4()}",
            headers=auth_headers(token),
        )
        assert resp.status_code == 404

    def test_mark_solved_response_body(self, client, db, sample_user,
                                       sample_user_token, sample_problem):
        session = make_session(db, sample_user, sample_problem)
        resp = client.patch(
            f"/progress/solve/{session.id}",
            headers=auth_headers(sample_user_token),
        )
        body = resp.get_json()
        assert "session_id" in body
        assert "message"    in body
        assert "solved_at"  in body

    def test_mark_solved_updates_db_is_solved(self, client, db, sample_user,
                                              sample_user_token, sample_problem):
        from app.models.session import UserProblemSession
        session = make_session(db, sample_user, sample_problem, is_solved=False)
        client.patch(
            f"/progress/solve/{session.id}",
            headers=auth_headers(sample_user_token),
        )
        refreshed = UserProblemSession.query.get(session.id)
        assert refreshed.is_solved is True
        assert refreshed.solved_at is not None

    def test_mark_solved_wrong_user_returns_404(self, client, db,
                                               sample_user, sample_problem):
        session   = make_session(db, sample_user, sample_problem)
        other_tok = register_and_login(client)
        resp = client.patch(
            f"/progress/solve/{session.id}",
            headers=auth_headers(other_tok),
        )
        assert resp.status_code == 404

    def test_mark_solved_is_idempotent(self, client, db, sample_user,
                                       sample_user_token, sample_problem):
        session = make_session(db, sample_user, sample_problem, is_solved=True,
                               solved_at=datetime.now(timezone.utc))
        resp = client.patch(
            f"/progress/solve/{session.id}",
            headers=auth_headers(sample_user_token),
        )
        assert resp.status_code == 200
        assert "already" in resp.get_json()["message"].lower()


class TestConceptsEndpoint:

    def test_concepts_returns_200(self, client):
        token = register_and_login(client)
        resp  = client.get("/progress/concepts", headers=auth_headers(token))
        assert resp.status_code == 200

    def test_concepts_requires_auth(self, client):
        resp = client.get("/progress/concepts")
        assert resp.status_code == 401

    def test_concepts_empty_for_new_user(self, client):
        token = register_and_login(client)
        body  = client.get("/progress/concepts", headers=auth_headers(token)).get_json()
        assert body["concepts"] == []


# ══════════════════════════════════════════════════════════════════════════════
# RECOMMENDER ROUTES — INTEGRATION TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestRecommendEndpoint:

    def test_recommend_returns_200(self, client):
        token = register_and_login(client)
        resp  = client.get("/recommend/problems", headers=auth_headers(token))
        assert resp.status_code == 200

    def test_recommend_requires_auth(self, client):
        resp = client.get("/recommend/problems")
        assert resp.status_code == 401

    def test_recommend_empty_when_no_problems(self, client):
        token = register_and_login(client)
        body  = client.get("/recommend/problems", headers=auth_headers(token)).get_json()
        assert body["recommendations"] == []

    def test_recommend_returns_list(self, client, db):
        token = register_and_login(client)
        for i in range(5):
            make_problem(db, f"Route Rec {i}")
        body = client.get("/recommend/problems", headers=auth_headers(token)).get_json()
        assert isinstance(body["recommendations"], list)

    def test_recommend_limit_query_param(self, client, db):
        token = register_and_login(client)
        for i in range(10):
            make_problem(db, f"QLim {i}")
        body = client.get("/recommend/problems?limit=3", headers=auth_headers(token)).get_json()
        assert len(body["recommendations"]) <= 3

    def test_recommend_card_structure(self, client, db):
        token = register_and_login(client)
        make_problem(db, "Struct Problem")
        body = client.get("/recommend/problems", headers=auth_headers(token)).get_json()
        card = body["recommendations"][0]
        for field in ["problem_id", "title", "difficulty", "tags", "source"]:
            assert field in card

    def test_recommend_excludes_user_attempted(self, client, db):
        """Problems linked to a user session (via problem_id) don't appear in recs."""
        from app.models.user import User
        from app.utils.validators import hash_password

        token = register_and_login(client)

        # Create problems in DB
        p_attempted = make_problem(db, "Rec Excl Attempted")
        _p_unseen   = make_problem(db, "Rec Excl Unseen")

        # Find the user just registered
        resp = client.get("/auth/me", headers=auth_headers(token))
        user_id = resp.get_json()["user"]["id"]
        user = User.query.filter_by(id=uuid.UUID(user_id)).first()

        # Create a session explicitly linked to the problem
        make_session(db, user, p_attempted)

        body = client.get("/recommend/problems", headers=auth_headers(token)).get_json()
        rec_ids = [r["problem_id"] for r in body["recommendations"]]
        assert str(p_attempted.id) not in rec_ids


# ══════════════════════════════════════════════════════════════════════════════
# SEED SCRIPT TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestSeedProblems:

    def test_problems_list_has_at_least_50_entries(self):
        from scripts.seed_problems import PROBLEMS
        assert len(PROBLEMS) >= 50

    def test_every_problem_has_required_fields(self):
        from scripts.seed_problems import PROBLEMS
        for p in PROBLEMS:
            assert "title"      in p, f"Missing title in {p}"
            assert "statement"  in p, f"Missing statement in {p}"
            assert "tags"       in p, f"Missing tags in {p}"
            assert "difficulty" in p, f"Missing difficulty in {p}"
            assert "source"     in p, f"Missing source in {p}"

    def test_every_problem_title_is_non_empty_string(self):
        from scripts.seed_problems import PROBLEMS
        for p in PROBLEMS:
            assert isinstance(p["title"], str) and p["title"].strip()

    def test_every_problem_tags_is_non_empty_list(self):
        from scripts.seed_problems import PROBLEMS
        for p in PROBLEMS:
            assert isinstance(p["tags"], list) and len(p["tags"]) > 0

    def test_every_problem_difficulty_is_valid(self):
        from scripts.seed_problems import PROBLEMS
        valid = {"Easy", "Medium", "Hard"}
        for p in PROBLEMS:
            assert p["difficulty"] in valid, f"Invalid difficulty in {p['title']}"

    def test_no_duplicate_titles(self):
        from scripts.seed_problems import PROBLEMS
        titles = [p["title"] for p in PROBLEMS]
        assert len(titles) == len(set(titles)), "Duplicate titles found in PROBLEMS"

    def test_seed_function_inserts_problems(self, app, db):
        from scripts.seed_problems import seed
        from app.models.problem import Problem
        count_before = Problem.query.count()
        inserted = seed(verbose=False, app=app)
        count_after = Problem.query.count()
        assert inserted > 0
        assert count_after == count_before + inserted

    def test_seed_function_is_idempotent(self, app, db):
        from scripts.seed_problems import seed
        from app.models.problem import Problem
        seed(verbose=False, app=app)
        total_after_first = Problem.query.count()
        inserted_second = seed(verbose=False, app=app)
        total_after_second = Problem.query.count()
        assert inserted_second == 0
        assert total_after_second == total_after_first

    def test_seeded_problems_queryable(self, app, db):
        from scripts.seed_problems import seed
        from app.models.problem import Problem
        seed(verbose=False, app=app)
        two_sum = Problem.query.filter_by(title="Two Sum").first()
        assert two_sum is not None
        assert two_sum.difficulty == "Easy"
        assert "HashMap" in two_sum.tags


# ══════════════════════════════════════════════════════════════════════════════
# END-TO-END FLOW TEST
# ══════════════════════════════════════════════════════════════════════════════

class TestProgressEndToEnd:
    """
    Simulate a realistic user journey:
      1. Register + login
      2. Submit a problem → get hints
      3. Mark session as solved
      4. Check stats reflect the solve
      5. Get recommendations (solved session excluded)
    """

    def test_full_user_journey(self, client, db):
        from unittest.mock import MagicMock
        from scripts.seed_problems import seed

        # Seed problem bank using the test app's context
        seed(verbose=False, app=client.application)

        token = register_and_login(client)

        # Submit a problem
        mock_llm = MagicMock()
        mock_llm.generate_hints.return_value = ["H1","H2","H3","H4","H5"]

        with patch("app.services.hint_engine.get_llm_client", return_value=mock_llm):
            r = client.post(
                "/hints/submit",
                json={"problem_text": "Given an array and a target, find two indices that sum to target."},
                headers=auth_headers(token),
            )
        assert r.status_code == 201
        session_id = r.get_json()["session_id"]

        # Mark as solved
        r2 = client.patch(
            f"/progress/solve/{session_id}",
            headers=auth_headers(token),
        )
        assert r2.status_code == 200

        # Check stats
        stats = client.get("/progress/stats", headers=auth_headers(token)).get_json()
        assert stats["total_attempted"] == 1
        assert stats["total_solved"]    == 1
        assert stats["solve_rate"]      == "100.0%"

        # Check history
        hist = client.get("/progress/history", headers=auth_headers(token)).get_json()
        assert hist["total"] == 1
        assert hist["sessions"][0]["is_solved"] is True

        # Recommendations still work
        recs = client.get("/recommend/problems", headers=auth_headers(token)).get_json()
        assert isinstance(recs["recommendations"], list)
