"""Tests for problem tag resolution from pasted text."""

from app.utils.problem_tags import find_problem_for_text, infer_tags_from_text, tags_for_session


TWO_SUM = (
    "Given an array of integers nums and an integer target, "
    "return indices of the two numbers such that they add up to target. "
    "You may assume each input has exactly one solution."
)


def test_find_problem_for_two_sum_paste(app, db, sample_problem):
    with app.app_context():
        from app.models.problem import Problem

        p = Problem.query.filter_by(title="Two Sum").first()
        assert p is not None
        matched = find_problem_for_text(TWO_SUM)
        assert matched is not None
        assert matched.id == p.id


def test_infer_tags_from_custom_text():
    tags = infer_tags_from_text(TWO_SUM)
    assert "Array" in tags


def test_stats_top_tags_from_pasted_sessions(app, db, sample_user):
    from app.models.session import UserProblemSession
    from app.services.progress_tracker import ProgressTrackerService

    with app.app_context():
        db.session.add(
            UserProblemSession(
                user_id=sample_user.id,
                problem_text=TWO_SUM,
                hints_requested=3,
                is_solved=True,
            )
        )
        db.session.commit()
        stats = ProgressTrackerService().get_stats(str(sample_user.id))
    assert stats["top_tags"]
    assert "Array" in stats["top_tags"]
