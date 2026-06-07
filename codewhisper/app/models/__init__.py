"""
CodeWhisper — Models Package
Imports all models so SQLAlchemy / Alembic can discover them for migrations.

Import order matters:
    User → UserProblemSession (FK: users.id)
    Problem → UserProblemSession (FK: problems.id)
    UserProblemSession → HintLog (FK: user_problem_sessions.id)
"""

from app.models.user import User                        # noqa: F401
from app.models.problem import Problem                  # noqa: F401
from app.models.session import UserProblemSession       # noqa: F401
from app.models.hint_log import HintLog                 # noqa: F401

__all__ = ["User", "Problem", "UserProblemSession", "HintLog"]
