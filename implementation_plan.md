# Implementation Plan: CodeWhisper
> AI-Powered Hint Engine for DSA & Coding Problem Learning

---

## Table of Contents
1. [Project Overview](#1-project-overview)
2. [Implementation Philosophy](#2-implementation-philosophy)
3. [Phases at a Glance](#3-phases-at-a-glance)
4. [Phase 1 — Project Setup & Environment](#4-phase-1--project-setup--environment)
5. [Phase 2 — Database Models & Migrations](#5-phase-2--database-models--migrations)
6. [Phase 3 — Authentication System](#6-phase-3--authentication-system)
7. [Phase 4 — LLM Integration Layer](#7-phase-4--llm-integration-layer)
8. [Phase 5 — Hint Engine Service (Core)](#8-phase-5--hint-engine-service-core)
9. [Phase 6 — Progress Tracker & Recommender](#9-phase-6--progress-tracker--recommender)
10. [Phase 7 — REST API Routes](#10-phase-7--rest-api-routes)
11. [Phase 8 — Frontend UI](#11-phase-8--frontend-ui)
12. [Phase 9 — Testing](#12-phase-9--testing)
13. [Phase 10 — Dockerization & Deployment](#13-phase-10--dockerization--deployment)
14. [Milestone Summary & Timeline](#14-milestone-summary--timeline)
15. [Dependencies & Risk Register](#15-dependencies--risk-register)
16. [Definition of Done](#16-definition-of-done)

---

## 1. Project Overview

| Field            | Detail                                         |
|------------------|------------------------------------------------|
| **Project**      | CodeWhisper                                    |
| **Domain**       | AI-Powered Developer Tools & Productivity      |
| **Stack**        | Python 3.11+, Flask, PostgreSQL, Redis, LLM APIs |
| **Goal**         | Progressive, Socratic hint engine for DSA problems |
| **Auth**         | JWT-based via Flask-JWT-Extended               |
| **LLM Providers**| OpenAI GPT-4 / Anthropic Claude (adapter pattern) |
| **Deployment**   | Docker + Docker Compose → Render / Railway / AWS |

---

## 2. Implementation Philosophy

- **Iterative & Incremental** — Build and verify one layer at a time, bottom-up (DB → Services → APIs → UI).
- **Test-as-you-go** — Write tests alongside each service/route, not at the end.
- **Abstract Early** — Use adapter pattern for LLM clients from Day 1 to avoid vendor lock-in.
- **Cache Aggressively** — Redis caching on hint sequences reduces LLM API cost and latency.
- **Security First** — Apply input validation, JWT guards, and rate limiting from the first route.

---

## 3. Phases at a Glance

```
Phase 1  ──►  Project Setup & Dev Environment         (Days 1–2)
Phase 2  ──►  Database Models & Migrations            (Days 3–4)
Phase 3  ──►  Authentication System                   (Days 5–6)
Phase 4  ──►  LLM Integration Layer                   (Days 7–8)
Phase 5  ──►  Hint Engine Service (Core Logic)        (Days 9–12)
Phase 6  ──►  Progress Tracker & Recommender          (Days 13–15)
Phase 7  ──►  REST API Routes (All Endpoints)         (Days 16–18)
Phase 8  ──►  Frontend UI                             (Days 19–22)
Phase 9  ──►  Testing (Unit + Integration)            (Days 23–25)
Phase 10 ──►  Dockerization & Deployment              (Days 26–28)
```

---

## 4. Phase 1 — Project Setup & Environment

**Duration:** Days 1–2  
**Goal:** Bootstrap a clean, runnable project skeleton with all tools configured.

### 4.1 Tasks

#### Step 1.1 — Initialize Repository
- [ ] Create project directory: `codewhisper/`
- [ ] Initialize Git repository: `git init`
- [ ] Create `.gitignore` (Python, `.env`, `__pycache__`, `*.pyc`, `.venv/`)
- [ ] Create `README.md` with project title and brief description

#### Step 1.2 — Python Virtual Environment
```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

#### Step 1.3 — Install Core Dependencies
```bash
pip install flask flask-jwt-extended flask-sqlalchemy flask-migrate \
            flask-cors psycopg2-binary redis python-dotenv \
            openai anthropic pytest pytest-flask
pip freeze > requirements.txt
```

#### Step 1.4 — Environment Configuration
Create `.env.example`:
```env
# Flask
FLASK_ENV=development
SECRET_KEY=your-secret-key

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/codewhisper

# Redis
REDIS_URL=redis://localhost:6379/0

# LLM
LLM_PROVIDER=openai          # or 'claude'
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-claude-key

# JWT
JWT_SECRET_KEY=your-jwt-secret
JWT_ACCESS_TOKEN_EXPIRES=3600
```
Copy to `.env` and fill in values.

#### Step 1.5 — Project Skeleton
Create the full folder structure as defined in architecture:
```
codewhisper/
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── extensions.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── hints.py
│   │   ├── progress.py
│   │   └── recommend.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── hint_engine.py
│   │   ├── progress_tracker.py
│   │   └── recommender.py
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── openai_client.py
│   │   └── claude_client.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── problem.py
│   │   ├── session.py
│   │   └── hint_log.py
│   └── utils/
│       ├── __init__.py
│       ├── cache.py
│       ├── validators.py
│       └── prompt_builder.py
├── tests/
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_hint_engine.py
│   └── test_progress.py
├── migrations/
├── .env.example
├── .gitignore
├── requirements.txt
└── run.py
```

#### Step 1.6 — Flask App Factory
**`app/__init__.py`**
```python
from flask import Flask
from app.config import Config
from app.extensions import db, migrate, jwt, cors

def create_app(config=Config):
    app = Flask(__name__)
    app.config.from_object(config)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    cors.init_app(app)

    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.hints import hints_bp
    from app.routes.progress import progress_bp
    from app.routes.recommend import recommend_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(hints_bp, url_prefix='/hints')
    app.register_blueprint(progress_bp, url_prefix='/progress')
    app.register_blueprint(recommend_bp, url_prefix='/recommend')

    return app
```

**`app/config.py`**
```python
import os
from dotenv import load_dotenv
load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'openai')
```

**`app/extensions.py`**
```python
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
cors = CORS()
```

**`run.py`**
```python
from app import create_app
app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
```

### ✅ Phase 1 Deliverables
- [ ] Git repo initialized with `.gitignore`
- [ ] Virtual environment active with all packages installed
- [ ] `.env` configured
- [ ] Flask app factory runs without errors (`flask run`)
- [ ] All folders and `__init__.py` files created

---

## 5. Phase 2 — Database Models & Migrations

**Duration:** Days 3–4  
**Goal:** Define all SQLAlchemy models and run initial migrations.

### 5.1 Tasks

#### Step 2.1 — User Model
**`app/models/user.py`**
```python
import uuid
from app.extensions import db
from datetime import datetime

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sessions = db.relationship('UserProblemSession', backref='user', lazy=True)
```

#### Step 2.2 — Problem Model
**`app/models/problem.py`**
```python
import uuid
from app.extensions import db
from datetime import datetime

class Problem(db.Model):
    __tablename__ = 'problems'

    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = db.Column(db.String(255))
    statement = db.Column(db.Text, nullable=False)
    tags = db.Column(db.ARRAY(db.String))       # ['DP', 'Array', 'BFS']
    difficulty = db.Column(db.String(20))        # Easy / Medium / Hard
    source = db.Column(db.String(100))           # LeetCode, Custom, etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

#### Step 2.3 — UserProblemSession Model
**`app/models/session.py`**
```python
import uuid
from app.extensions import db
from datetime import datetime

class UserProblemSession(db.Model):
    __tablename__ = 'user_problem_sessions'

    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=False)
    problem_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey('problems.id'), nullable=True)
    problem_text = db.Column(db.Text)            # Raw pasted problem
    hints_requested = db.Column(db.Integer, default=0)
    current_hint_level = db.Column(db.Integer, default=0)
    is_solved = db.Column(db.Boolean, default=False)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    solved_at = db.Column(db.DateTime, nullable=True)

    hint_logs = db.relationship('HintLog', backref='session', lazy=True)
```

#### Step 2.4 — HintLog Model
**`app/models/hint_log.py`**
```python
import uuid
from app.extensions import db
from datetime import datetime

class HintLog(db.Model):
    __tablename__ = 'hint_logs'

    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey('user_problem_sessions.id'), nullable=False)
    hint_level = db.Column(db.Integer, nullable=False)   # 1–5
    hint_text = db.Column(db.Text, nullable=False)
    delivered_at = db.Column(db.DateTime, default=datetime.utcnow)
```

#### Step 2.5 — Import All Models
**`app/models/__init__.py`**
```python
from app.models.user import User
from app.models.problem import Problem
from app.models.session import UserProblemSession
from app.models.hint_log import HintLog
```

#### Step 2.6 — Run Migrations
```bash
flask db init
flask db migrate -m "Initial models: users, problems, sessions, hint_logs"
flask db upgrade
```

### ✅ Phase 2 Deliverables
- [ ] All 4 models defined with correct relationships
- [ ] `flask db upgrade` runs cleanly
- [ ] Tables verified in PostgreSQL via `\dt`

---

## 6. Phase 3 — Authentication System

**Duration:** Days 5–6  
**Goal:** Implement register, login, and logout with JWT tokens.

### 6.1 Tasks

#### Step 3.1 — Password Hashing Utility
```bash
pip install bcrypt
```
```python
# app/utils/validators.py
import bcrypt

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())
```

#### Step 3.2 — Auth Routes
**`app/routes/auth.py`**

| Endpoint | Method | Auth Required | Description |
|---|---|---|---|
| `/auth/register` | POST | No | Create new user account |
| `/auth/login` | POST | No | Authenticate and return JWT |
| `/auth/logout` | POST | Yes | Blacklist token (Redis) |

```python
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from app.models.user import User
from app.extensions import db
from app.utils.validators import hash_password, verify_password

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    # Validate: username, email, password present
    # Check duplicate email/username
    # Hash password
    # Save user to DB
    # Return 201 with success message

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    # Find user by email
    # Verify password
    # Create JWT access token
    # Return token + user info

@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    # Add JWT jti to Redis blocklist
    # Return 200
```

#### Step 3.3 — JWT Blocklist (Redis)
```python
# app/utils/cache.py
import redis
import os

r = redis.from_url(os.getenv('REDIS_URL'))

def blacklist_token(jti: str, expires_in: int):
    r.setex(f"blocklist:{jti}", expires_in, "true")

def is_token_blacklisted(jti: str) -> bool:
    return r.exists(f"blocklist:{jti}") == 1
```

Wire into JWT loader in `extensions.py`:
```python
@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):
    return is_token_blacklisted(jwt_payload['jti'])
```

### ✅ Phase 3 Deliverables
- [ ] `POST /auth/register` creates user with hashed password
- [ ] `POST /auth/login` returns valid JWT
- [ ] `POST /auth/logout` blacklists token via Redis
- [ ] Protected routes return 401 without valid token

---

## 7. Phase 4 — LLM Integration Layer

**Duration:** Days 7–8  
**Goal:** Build an abstract, swappable LLM client using the adapter pattern.

### 7.1 Tasks

#### Step 4.1 — Abstract Base Client
**`app/llm/base.py`**
```python
from abc import ABC, abstractmethod

class BaseLLMClient(ABC):
    @abstractmethod
    def generate_hints(self, problem: str) -> list[str]:
        """
        Accepts a DSA problem string.
        Returns a list of 5 progressive hints.
        """
        pass
```

#### Step 4.2 — Prompt Builder
**`app/utils/prompt_builder.py`**
```python
SYSTEM_PROMPT = """
You are CodeWhisper, an AI learning companion for developers.
Your role is to help users solve coding/DSA problems through hints —
NOT by revealing the full solution.

When given a problem:
1. Identify the core data structure or algorithm pattern involved.
2. Generate exactly 5 progressive hints as a JSON array:
   - Hint 1: High-level nudge about problem category.
   - Hint 2: A guiding question about the approach.
   - Hint 3: A conceptual clue about the algorithm/pattern.
   - Hint 4: A pseudocode-level direction.
   - Hint 5: A near-complete approach (no full runnable code).

Return ONLY a valid JSON array of 5 strings. No extra text.
Never reveal the full solution. Encourage the user to think.
"""

def build_hint_prompt(problem: str) -> str:
    return f"Problem:\n{problem}"
```

#### Step 4.3 — OpenAI Client
**`app/llm/openai_client.py`**
```python
import json
import openai
import os
from app.llm.base import BaseLLMClient
from app.utils.prompt_builder import SYSTEM_PROMPT, build_hint_prompt

class OpenAIClient(BaseLLMClient):
    def __init__(self):
        openai.api_key = os.getenv('OPENAI_API_KEY')
        self.model = "gpt-4o"

    def generate_hints(self, problem: str) -> list[str]:
        response = openai.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_hint_prompt(problem)}
            ],
            max_tokens=1500,
            temperature=0.7
        )
        content = response.choices[0].message.content
        return json.loads(content)   # Parse JSON array of 5 hints
```

#### Step 4.4 — Claude Client
**`app/llm/claude_client.py`**
```python
import json
import anthropic
import os
from app.llm.base import BaseLLMClient
from app.utils.prompt_builder import SYSTEM_PROMPT, build_hint_prompt

class ClaudeClient(BaseLLMClient):
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

    def generate_hints(self, problem: str) -> list[str]:
        response = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": build_hint_prompt(problem)}]
        )
        content = response.content[0].text
        return json.loads(content)
```

#### Step 4.5 — LLM Factory
**`app/llm/__init__.py`**
```python
import os
from app.llm.openai_client import OpenAIClient
from app.llm.claude_client import ClaudeClient

def get_llm_client():
    provider = os.getenv('LLM_PROVIDER', 'openai').lower()
    if provider == 'claude':
        return ClaudeClient()
    return OpenAIClient()
```

#### Step 4.6 — Error Handling & Retries
Wrap LLM calls with:
- `try/except` for API errors, timeouts, and JSON parse failures.
- Retry logic (up to 3 attempts with exponential backoff).
- Fallback: if both providers fail, return a generic "Think about the problem constraints" hint.

### ✅ Phase 4 Deliverables
- [ ] `BaseLLMClient` ABC defined
- [ ] `OpenAIClient.generate_hints()` returns 5-hint list from GPT-4
- [ ] `ClaudeClient.generate_hints()` returns 5-hint list from Claude
- [ ] `get_llm_client()` factory switches provider via `.env`
- [ ] Retry & error handling implemented

---

## 8. Phase 5 — Hint Engine Service (Core)

**Duration:** Days 9–12  
**Goal:** Build the core hint engine that orchestrates LLM calls, Redis caching, and session management.

### 8.1 Tasks

#### Step 5.1 — Redis Cache Helpers
**`app/utils/cache.py`** (extend existing file)
```python
import hashlib
import json

HINT_CACHE_TTL = 60 * 60 * 24   # 24 hours

def get_problem_hash(problem_text: str) -> str:
    return hashlib.sha256(problem_text.strip().lower().encode()).hexdigest()

def cache_hints(problem_hash: str, hints: list[str]):
    key = f"hints:{problem_hash}"
    r.setex(key, HINT_CACHE_TTL, json.dumps(hints))

def get_cached_hints(problem_hash: str) -> list[str] | None:
    key = f"hints:{problem_hash}"
    data = r.get(key)
    return json.loads(data) if data else None

def store_session_hint_index(session_id: str, index: int):
    r.setex(f"session:{session_id}:hint_index", 3600, index)

def get_session_hint_index(session_id: str) -> int:
    val = r.get(f"session:{session_id}:hint_index")
    return int(val) if val else 0
```

#### Step 5.2 — Hint Engine Service
**`app/services/hint_engine.py`**
```python
from app.llm import get_llm_client
from app.utils.cache import (
    get_problem_hash, cache_hints, get_cached_hints,
    store_session_hint_index, get_session_hint_index
)
from app.models.session import UserProblemSession
from app.models.hint_log import HintLog
from app.models.problem import Problem
from app.extensions import db

class HintEngineService:

    def __init__(self):
        self.llm_client = get_llm_client()

    def start_session(self, user_id: str, problem_text: str) -> dict:
        """
        Called on POST /hints/submit.
        1. Hash problem text → check Redis cache
        2. Cache MISS → call LLM → cache results
        3. Create DB session record
        4. Return session_id + first hint
        """
        problem_hash = get_problem_hash(problem_text)

        # Check cache
        hints = get_cached_hints(problem_hash)
        if not hints:
            hints = self.llm_client.generate_hints(problem_text)
            cache_hints(problem_hash, hints)

        # Create session in DB
        session = UserProblemSession(
            user_id=user_id,
            problem_text=problem_text,
            hints_requested=1,
            current_hint_level=1
        )
        db.session.add(session)
        db.session.commit()

        # Store hint index in Redis
        store_session_hint_index(str(session.id), 1)

        # Log first hint to DB
        hint_log = HintLog(
            session_id=session.id,
            hint_level=1,
            hint_text=hints[0]
        )
        db.session.add(hint_log)
        db.session.commit()

        return {
            "session_id": str(session.id),
            "hint_level": 1,
            "hint": hints[0],
            "total_hints": len(hints)
        }

    def get_next_hint(self, session_id: str, user_id: str) -> dict:
        """
        Called on GET /hints/next/{session_id}.
        Fetches next hint from Redis-cached sequence.
        """
        session = UserProblemSession.query.filter_by(
            id=session_id, user_id=user_id
        ).first_or_404()

        current_index = get_session_hint_index(session_id)
        problem_hash = get_problem_hash(session.problem_text)
        hints = get_cached_hints(problem_hash)

        if current_index >= len(hints):
            return {"message": "No more hints available. Try solving it now!", "exhausted": True}

        next_hint = hints[current_index]
        next_index = current_index + 1

        # Update Redis
        store_session_hint_index(session_id, next_index)

        # Update DB session
        session.hints_requested += 1
        session.current_hint_level = next_index
        db.session.commit()

        # Log hint
        hint_log = HintLog(
            session_id=session.id,
            hint_level=next_index,
            hint_text=next_hint
        )
        db.session.add(hint_log)
        db.session.commit()

        return {
            "session_id": session_id,
            "hint_level": next_index,
            "hint": next_hint,
            "total_hints": len(hints),
            "exhausted": next_index >= len(hints)
        }

    def get_session_hints(self, session_id: str, user_id: str) -> list[dict]:
        """
        Called on GET /hints/session/{session_id}.
        Returns all hints delivered so far for a session.
        """
        session = UserProblemSession.query.filter_by(
            id=session_id, user_id=user_id
        ).first_or_404()

        logs = HintLog.query.filter_by(session_id=session.id)\
                            .order_by(HintLog.hint_level).all()
        return [{"level": h.hint_level, "hint": h.hint_text} for h in logs]
```

### ✅ Phase 5 Deliverables
- [ ] Problem hashing and Redis caching working
- [ ] `start_session()` creates DB record and returns Hint #1
- [ ] `get_next_hint()` returns subsequent hints from cache (no extra LLM call)
- [ ] All hints logged to `hint_logs` table
- [ ] Graceful "hints exhausted" response at Hint #5

---

## 9. Phase 6 — Progress Tracker & Recommender

**Duration:** Days 13–15  
**Goal:** Implement learning progress tracking and tag-based problem recommendations.

### 9.1 Tasks

#### Step 6.1 — Progress Tracker Service
**`app/services/progress_tracker.py`**
```python
from app.models.session import UserProblemSession
from app.models.hint_log import HintLog
from app.extensions import db
from datetime import datetime

class ProgressTrackerService:

    def get_history(self, user_id: str) -> list[dict]:
        """Return all problem sessions for the user."""
        sessions = UserProblemSession.query.filter_by(user_id=user_id)\
                                           .order_by(UserProblemSession.started_at.desc()).all()
        return [
            {
                "session_id": str(s.id),
                "problem_preview": s.problem_text[:100] + "...",
                "hints_used": s.hints_requested,
                "is_solved": s.is_solved,
                "started_at": s.started_at.isoformat(),
                "solved_at": s.solved_at.isoformat() if s.solved_at else None
            }
            for s in sessions
        ]

    def get_stats(self, user_id: str) -> dict:
        """Aggregate stats: total solved, avg hints per problem, concepts seen."""
        sessions = UserProblemSession.query.filter_by(user_id=user_id).all()
        total = len(sessions)
        solved = sum(1 for s in sessions if s.is_solved)
        avg_hints = sum(s.hints_requested for s in sessions) / total if total else 0

        return {
            "total_attempted": total,
            "total_solved": solved,
            "average_hints_per_problem": round(avg_hints, 2),
            "solve_rate": f"{round((solved/total)*100, 1)}%" if total else "0%"
        }

    def mark_solved(self, session_id: str, user_id: str) -> dict:
        """Mark a session as solved."""
        session = UserProblemSession.query.filter_by(
            id=session_id, user_id=user_id
        ).first_or_404()
        session.is_solved = True
        session.solved_at = datetime.utcnow()
        db.session.commit()
        return {"message": "Problem marked as solved!", "session_id": session_id}
```

#### Step 6.2 — Recommender Service
**`app/services/recommender.py`**
```python
from app.models.problem import Problem
from app.models.session import UserProblemSession
from sqlalchemy import func

class RecommenderService:

    def recommend(self, user_id: str, limit: int = 5) -> list[dict]:
        """
        Tag-based recommendation:
        1. Get tags from user's solved sessions (via related problems).
        2. Find problems with overlapping tags not yet attempted.
        3. Return top N.
        """
        # Get attempted problem IDs
        attempted_ids = [
            s.problem_id for s in
            UserProblemSession.query.filter_by(user_id=user_id).all()
            if s.problem_id
        ]

        # Get all problems not yet attempted
        candidates = Problem.query.filter(
            Problem.id.notin_(attempted_ids)
        ).limit(limit * 3).all()

        # Simple shuffle for now; future: tag overlap scoring
        import random
        random.shuffle(candidates)

        return [
            {
                "problem_id": str(p.id),
                "title": p.title,
                "difficulty": p.difficulty,
                "tags": p.tags,
                "source": p.source
            }
            for p in candidates[:limit]
        ]
```

#### Step 6.3 — Seed Problem Bank
Create a migration/script to populate the `problems` table with 50+ curated DSA problems (from LeetCode/Codeforces) tagged with difficulty and concept tags.

```python
# scripts/seed_problems.py
PROBLEMS = [
    {"title": "Two Sum", "tags": ["Array", "HashMap"], "difficulty": "Easy", "source": "LeetCode"},
    {"title": "Longest Substring Without Repeating Characters", "tags": ["Sliding Window", "String"], "difficulty": "Medium", "source": "LeetCode"},
    {"title": "Coin Change", "tags": ["DP", "BFS"], "difficulty": "Medium", "source": "LeetCode"},
    # ... add 50+ problems
]
```

### ✅ Phase 6 Deliverables
- [ ] `get_history()` returns paginated session history
- [ ] `get_stats()` returns solve rate and avg hints used
- [ ] `mark_solved()` updates session correctly
- [ ] `recommend()` returns 5 unseen problems
- [ ] Problem bank seeded with 50+ DSA problems

---

## 10. Phase 7 — REST API Routes

**Duration:** Days 16–18  
**Goal:** Wire all services to Flask route blueprints and add input validation + rate limiting.

### 10.1 Tasks

#### Step 7.1 — Rate Limiting Setup
```bash
pip install flask-limiter
```
```python
# app/extensions.py
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
limiter = Limiter(key_func=get_remote_address, storage_uri=os.getenv('REDIS_URL'))
```

#### Step 7.2 — Hints Routes
**`app/routes/hints.py`**
```python
@hints_bp.route('/submit', methods=['POST'])
@jwt_required()
@limiter.limit("20 per hour")
def submit_problem():
    user_id = get_jwt_identity()
    data = request.get_json()
    problem_text = data.get('problem_text', '').strip()

    if not problem_text or len(problem_text) < 20:
        return jsonify({"error": "Problem text too short."}), 400

    result = HintEngineService().start_session(user_id, problem_text)
    return jsonify(result), 201


@hints_bp.route('/next/<session_id>', methods=['GET'])
@jwt_required()
def next_hint(session_id):
    user_id = get_jwt_identity()
    result = HintEngineService().get_next_hint(session_id, user_id)
    return jsonify(result), 200


@hints_bp.route('/session/<session_id>', methods=['GET'])
@jwt_required()
def get_session(session_id):
    user_id = get_jwt_identity()
    hints = HintEngineService().get_session_hints(session_id, user_id)
    return jsonify({"hints": hints}), 200
```

#### Step 7.3 — Progress Routes
**`app/routes/progress.py`**
```python
@progress_bp.route('/history', methods=['GET'])
@jwt_required()
def history():
    user_id = get_jwt_identity()
    data = ProgressTrackerService().get_history(user_id)
    return jsonify({"history": data}), 200

@progress_bp.route('/stats', methods=['GET'])
@jwt_required()
def stats():
    user_id = get_jwt_identity()
    data = ProgressTrackerService().get_stats(user_id)
    return jsonify(data), 200

@progress_bp.route('/solve/<session_id>', methods=['PATCH'])
@jwt_required()
def mark_solved(session_id):
    user_id = get_jwt_identity()
    result = ProgressTrackerService().mark_solved(session_id, user_id)
    return jsonify(result), 200
```

#### Step 7.4 — Recommend Routes
**`app/routes/recommend.py`**
```python
@recommend_bp.route('/problems', methods=['GET'])
@jwt_required()
def recommend():
    user_id = get_jwt_identity()
    problems = RecommenderService().recommend(user_id)
    return jsonify({"recommendations": problems}), 200
```

#### Step 7.5 — Global Error Handlers
```python
# app/__init__.py
@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Resource not found"}), 404

@app.errorhandler(429)
def rate_limited(e):
    return jsonify({"error": "Rate limit exceeded. Try again later."}), 429

@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Internal server error"}), 500
```

### ✅ Phase 7 Deliverables
- [ ] All 9 endpoints implemented and reachable
- [ ] JWT protection on all non-auth routes
- [ ] Rate limiting: 20 hint submissions/hour per user
- [ ] Input validation on `/hints/submit`
- [ ] Global error handlers returning clean JSON

---

## 11. Phase 8 — Frontend UI

**Duration:** Days 19–22  
**Goal:** Build a clean, responsive single-page UI served by Flask.

### 11.1 Pages & Components

| Page | Route | Description |
|---|---|---|
| **Landing / Login** | `/` | Login form + Register link |
| **Register** | `/register` | New user signup |
| **Dashboard** | `/dashboard` | Problem history + stats |
| **Hint Workspace** | `/solve` | Problem input + hint display |
| **Recommendations** | `/recommend` | Suggested problems |

### 11.2 Tasks

#### Step 8.1 — Base Template
Create `templates/base.html` with:
- Navbar (logo, username, logout)
- Flash message container
- Block for page content
- Inline CSS (no external CDN required)

#### Step 8.2 — Hint Workspace (Core UI)
`templates/solve.html`:
```
┌─────────────────────────────────────────────────┐
│  PASTE YOUR PROBLEM                             │
│  ┌───────────────────────────────────────────┐  │
│  │  <textarea id="problem-input">           │  │
│  └───────────────────────────────────────────┘  │
│  [  Get First Hint  ]                           │
├─────────────────────────────────────────────────┤
│  HINTS                                          │
│  ┌──────────────────────────────────────────┐   │
│  │  💡 Hint 1: Think about the constraints  │   │
│  └──────────────────────────────────────────┘   │
│  [  Next Hint  ]   [  Mark as Solved  ]         │
└─────────────────────────────────────────────────┘
```
- JavaScript `fetch()` calls to API.
- Hints appear as animated cards (CSS).
- "Next Hint" disabled when hints exhausted.
- Progress bar showing `hint_level / 5`.

#### Step 8.3 — Dashboard Page
`templates/dashboard.html`:
- Stats cards: Total Attempted, Total Solved, Solve Rate, Avg Hints Used.
- Table of recent sessions with date, problem preview, hints used, solved status.
- "Continue" button on unsolved sessions.

#### Step 8.4 — Recommendations Panel
- Grid of recommended problem cards.
- Each card shows: Title, Difficulty badge (color-coded), Tags, Source.
- "Start Solving" button navigates to hint workspace pre-filled.

#### Step 8.5 — Auth Pages
- Clean login/register forms with client-side validation.
- JWT token stored in `localStorage`.
- All fetch calls include `Authorization: Bearer <token>` header.

### ✅ Phase 8 Deliverables
- [ ] Login / Register working end-to-end
- [ ] Hint workspace: problem input → first hint → next hints
- [ ] Progress bar showing current hint level
- [ ] Dashboard shows stats + session history
- [ ] Recommendation page displays 5 problems
- [ ] Responsive on mobile and desktop

---

## 12. Phase 9 — Testing

**Duration:** Days 23–25  
**Goal:** Achieve >80% test coverage on services and routes.

### 12.1 Test Setup
**`tests/conftest.py`**
```python
import pytest
from app import create_app
from app.extensions import db

@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()
```

### 12.2 Test Cases

#### Auth Tests — `tests/test_auth.py`
| Test | Expected |
|---|---|
| `test_register_success` | 201, user created |
| `test_register_duplicate_email` | 409, error message |
| `test_login_valid_credentials` | 200, JWT token returned |
| `test_login_wrong_password` | 401 |
| `test_logout_blacklists_token` | 200, subsequent request returns 401 |

#### Hint Engine Tests — `tests/test_hint_engine.py`
| Test | Expected |
|---|---|
| `test_start_session_creates_db_record` | Session row created |
| `test_first_hint_returned` | Hint #1 in response |
| `test_cache_hit_avoids_llm_call` | LLM not called on 2nd same problem |
| `test_next_hint_increments_level` | hint_level goes 1→2→3 |
| `test_hints_exhausted_message` | Returns exhausted flag at level 5 |

#### Progress Tests — `tests/test_progress.py`
| Test | Expected |
|---|---|
| `test_get_history_returns_sessions` | List of sessions |
| `test_get_stats_calculates_correctly` | Correct solve rate |
| `test_mark_solved_updates_db` | `is_solved=True`, `solved_at` set |
| `test_recommend_excludes_attempted` | No already-attempted problems |

### 12.3 Run Tests
```bash
pytest tests/ -v --cov=app --cov-report=term-missing
```

### ✅ Phase 9 Deliverables
- [ ] All test cases written and passing
- [ ] Coverage ≥ 80% on `app/services/` and `app/routes/`
- [ ] No broken imports or setup errors in test suite

---

## 13. Phase 10 — Dockerization & Deployment

**Duration:** Days 26–28  
**Goal:** Containerize the full stack and deploy to cloud.

### 13.1 Tasks

#### Step 10.1 — Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000
CMD ["flask", "run", "--host=0.0.0.0"]
```

#### Step 10.2 — Docker Compose (Local Dev)
**`docker-compose.yml`**
```yaml
version: '3.9'
services:
  web:
    build: .
    ports:
      - "5000:5000"
    env_file: .env
    depends_on:
      - db
      - redis
    volumes:
      - .:/app

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: codewhisper
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
    volumes:
      - pg_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  pg_data:
```

#### Step 10.3 — Run Locally with Docker
```bash
docker-compose up --build
docker-compose exec web flask db upgrade
docker-compose exec web python scripts/seed_problems.py
```

#### Step 10.4 — Cloud Deployment (Render / Railway)
- Push code to GitHub.
- Connect repo to Render or Railway.
- Set environment variables in platform dashboard.
- Add managed PostgreSQL and Redis add-ons.
- Set start command: `gunicorn run:app`.
- Add `gunicorn` to `requirements.txt`.

#### Step 10.5 — Production Hardening
- [ ] Set `FLASK_ENV=production`
- [ ] Use `gunicorn` (not Flask dev server)
- [ ] Enable HTTPS (auto via Render/Railway)
- [ ] Set strict CORS origins
- [ ] Rotate all secrets post-deployment

### ✅ Phase 10 Deliverables
- [ ] `docker-compose up` starts all 3 services cleanly
- [ ] App accessible at `http://localhost:5000`
- [ ] Deployed and live on Render/Railway
- [ ] All environment variables set in cloud dashboard
- [ ] DB migrations run in production

---

## 14. Milestone Summary & Timeline

| Phase | Description | Duration | Milestone |
|---|---|---|---|
| **Phase 1** | Project Setup & Environment | Days 1–2 | ✅ Flask app runs |
| **Phase 2** | Database Models & Migrations | Days 3–4 | ✅ All tables in PostgreSQL |
| **Phase 3** | Authentication System | Days 5–6 | ✅ JWT login/register working |
| **Phase 4** | LLM Integration Layer | Days 7–8 | ✅ Hints generated from OpenAI/Claude |
| **Phase 5** | Hint Engine Service | Days 9–12 | ✅ Progressive hints with Redis caching |
| **Phase 6** | Progress Tracker & Recommender | Days 13–15 | ✅ Stats, history, recommendations working |
| **Phase 7** | REST API Routes | Days 16–18 | ✅ All 9 endpoints live & validated |
| **Phase 8** | Frontend UI | Days 19–22 | ✅ Full UI end-to-end functional |
| **Phase 9** | Testing | Days 23–25 | ✅ >80% coverage, all tests green |
| **Phase 10** | Dockerization & Deployment | Days 26–28 | ✅ Live on cloud |

**Total Estimated Duration: 28 Days (4 Weeks)**

---

## 15. Dependencies & Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| LLM API rate limits | Medium | High | Redis caching; exponential backoff retries |
| LLM cost overrun | Medium | Medium | Max token limits; aggressive caching; free tier usage |
| LLM returns invalid JSON | Low | High | Strict prompt + try/except + fallback response |
| PostgreSQL connection issues | Low | High | Docker health checks; retry on startup |
| JWT token leakage | Low | High | Short expiry (1hr); Redis blocklist on logout |
| Prompt injection by user | Medium | Medium | System prompt enforcement; input length limits |
| Redis cache miss on restart | Low | Low | LLM re-generates; no data loss |

---

## 16. Definition of Done

A feature/phase is considered **Done** when:

- [ ] Code is written and follows project structure
- [ ] All related unit/integration tests pass
- [ ] No linting errors (`flake8` / `black` formatted)
- [ ] Endpoint tested manually via Postman or curl
- [ ] Code committed to Git with a descriptive message
- [ ] Relevant documentation/comments added
- [ ] Edge cases handled (empty inputs, auth failures, API errors)

---

> 🚀 **CodeWhisper** — Built to teach, not to tell. One hint at a time.
