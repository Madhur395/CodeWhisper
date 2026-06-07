# Architecture Document: CodeWhisper
> AI-Powered Hint Engine for DSA & Coding Problem Learning

---

## Table of Contents
1. [System Overview](#1-system-overview)
2. [Architecture Style](#2-architecture-style)
3. [High-Level Architecture Diagram](#3-high-level-architecture-diagram)
4. [Component Breakdown](#4-component-breakdown)
5. [Technology Stack](#5-technology-stack)
6. [Data Flow](#6-data-flow)
7. [Database Design](#7-database-design)
8. [API Design](#8-api-design)
9. [LLM Integration Strategy](#9-llm-integration-strategy)
10. [Security Considerations](#10-security-considerations)
11. [Scalability & Performance](#11-scalability--performance)
12. [Folder Structure](#12-folder-structure)

---

## 1. System Overview

**CodeWhisper** is an AI-powered learning companion that helps developers and students solve DSA and coding problems through progressive, Socratic-style hints — rather than handing out direct answers.

### Core Goals
- Accept any coding/DSA problem as input.
- Analyze the problem and detect underlying concepts and patterns.
- Deliver a sequence of adaptive, progressive hints using LLM APIs (OpenAI / Claude).
- Track user progress, history of solved problems, and recommend similar practice problems.
- Maintain academic integrity by never revealing full solutions upfront.

---

## 2. Architecture Style

CodeWhisper follows a **Layered Monolith with Service-Oriented Internals** approach, well-suited for a Python/Flask application that can evolve into microservices later.

| Layer | Responsibility |
|---|---|
| **Presentation Layer** | Web UI (HTML/CSS/JS or React) served by Flask |
| **API Layer** | RESTful Flask routes exposing endpoints |
| **Service Layer** | Business logic — hint engine, progress tracker, recommender |
| **LLM Integration Layer** | Abstracted client for OpenAI / Claude APIs |
| **Data Layer** | PostgreSQL (persistent) + Redis (caching/sessions) |

---

## 3. High-Level Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                          CLIENT LAYER                            │
│           Browser / Web App (HTML + JS / React)                  │
└────────────────────────────┬─────────────────────────────────────┘
                             │ HTTPS Requests
┌────────────────────────────▼─────────────────────────────────────┐
│                        FLASK API SERVER                          │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐  │
│  │  Auth Routes │  │ Hint Routes  │  │  Progress/Rec Routes   │  │
│  └─────────────┘  └──────┬───────┘  └────────────┬───────────┘  │
│                           │                       │              │
│  ┌────────────────────────▼───────────────────────▼───────────┐  │
│  │                     SERVICE LAYER                          │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  │  │
│  │  │  HintEngine  │  │ProgressTrack │  │   Recommender   │  │  │
│  │  │   Service    │  │   Service    │  │    Service      │  │  │
│  │  └──────┬───────┘  └──────┬───────┘  └────────┬────────┘  │  │
│  └─────────┼─────────────────┼───────────────────┼───────────┘  │
│            │                 │                   │              │
│  ┌─────────▼─────────┐  ┌────▼───────────────────▼───────────┐  │
│  │  LLM CLIENT LAYER │  │         DATA ACCESS LAYER          │  │
│  │  (OpenAI/Claude)  │  │   (SQLAlchemy ORM + Redis Cache)   │  │
│  └─────────┬─────────┘  └────────────────┬────────────────────┘  │
└────────────┼────────────────────────────┼──────────────────────┘
             │                            │
   ┌─────────▼──────────┐     ┌───────────▼────────────┐
   │  OpenAI / Claude   │     │  PostgreSQL + Redis     │
   │     External API   │     │  (Persistent + Cache)   │
   └────────────────────┘     └────────────────────────┘
```

---

## 4. Component Breakdown

### 4.1 Frontend (Presentation Layer)
- Simple, responsive web interface built with **HTML/CSS/JS** (or optionally React).
- Features:
  - Problem input box (paste coding problem).
  - Hint display panel (progressive hint cards).
  - "Next Hint" button to request deeper hints.
  - Dashboard showing problem history and progress.
  - Recommended problems panel.

### 4.2 Flask API Server
- Serves as the application entry point.
- Handles routing, middleware (auth, rate limiting), and request/response formatting.
- Key Route Groups:
  - `/auth` — register, login, logout (JWT-based)
  - `/hints` — submit problem, get next hint
  - `/progress` — fetch user history & stats
  - `/recommend` — get similar problems

### 4.3 Hint Engine Service
The **core brain** of CodeWhisper.
- Accepts a problem statement from the user.
- Uses the LLM to:
  1. **Analyze** the problem — detect data structures, algorithms, patterns (e.g., sliding window, BFS, DP).
  2. **Generate** a bank of 3–5 progressive hints (from high-level nudge → concept hint → approach hint).
  3. **Adapt** hint depth based on user's previous interactions and responses.
- Maintains hint state per user session (stored in Redis).

### 4.4 LLM Client Layer
- An abstracted wrapper supporting **OpenAI GPT** and **Anthropic Claude**.
- Responsibilities:
  - Prompt engineering (Socratic-style system prompts).
  - API call management (retries, timeouts, fallbacks).
  - Response parsing and formatting.
- Easily swappable via a strategy/adapter pattern.

### 4.5 Progress Tracker Service
- Logs every problem a user has worked on.
- Tracks:
  - Number of hints requested per problem.
  - Whether the user marked a problem as "solved".
  - Concepts/tags encountered (e.g., DP, Graph, Tree).
- Generates a user learning profile over time.

### 4.6 Recommender Service
- Uses tags/concepts from solved and attempted problems to recommend similar problems.
- Initial implementation: **tag-based filtering** from a curated problem bank.
- Future: collaborative filtering or embedding-based similarity.

### 4.7 Data Access Layer
- **SQLAlchemy ORM** for all PostgreSQL interactions.
- **Redis** for:
  - Session management.
  - Caching hint sequences (avoid redundant LLM calls for the same problem).
  - Rate-limiting counters.

---

## 5. Technology Stack

| Category | Technology | Purpose |
|---|---|---|
| **Language** | Python 3.11+ | Core backend language |
| **Web Framework** | Flask | API server & routing |
| **LLM APIs** | OpenAI GPT-4 / Anthropic Claude | Hint generation & problem analysis |
| **Database** | PostgreSQL | Persistent user data, problems, history |
| **Cache / Sessions** | Redis | Hint state, session tokens, rate limiting |
| **ORM** | SQLAlchemy | Database abstraction |
| **Auth** | Flask-JWT-Extended | JWT-based authentication |
| **Frontend** | HTML/CSS/JS (or React) | User interface |
| **Environment Config** | python-dotenv | Secrets & env variable management |
| **Testing** | pytest | Unit and integration tests |
| **Containerization** | Docker + Docker Compose | Local dev & deployment |
| **Deployment** | Render / Railway / AWS EC2 | Cloud hosting |

---

## 6. Data Flow

### Hint Request Flow
```
User pastes problem
        │
        ▼
POST /hints/submit
        │
        ▼
HintEngineService.analyze(problem)
        │
        ├── Check Redis cache (same problem hash?)
        │        └── Cache HIT → return cached hint sequence
        │
        └── Cache MISS → call LLM Client
                  │
                  ▼
         LLM API (OpenAI/Claude)
         [System Prompt: Socratic mode]
         [Generate 3-5 progressive hints]
                  │
                  ▼
         Parse & store hints in Redis (keyed by user+problem hash)
                  │
                  ▼
         Return Hint #1 to user
                  │
        ┌─────────▼──────────┐
        │  User requests     │
        │  "Next Hint"       │
        └─────────┬──────────┘
                  │
                  ▼
         Fetch Hint #2 from Redis
         (No new LLM call needed)
                  │
                  ▼
         Log interaction to PostgreSQL
                  │
                  ▼
         Return Hint #2 to user
```

---

## 7. Database Design

### Users Table
```sql
CREATE TABLE users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username    VARCHAR(100) UNIQUE NOT NULL,
    email       VARCHAR(255) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at  TIMESTAMP DEFAULT NOW()
);
```

### Problems Table
```sql
CREATE TABLE problems (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title       VARCHAR(255),
    statement   TEXT NOT NULL,
    tags        TEXT[],              -- e.g. ['DP', 'Array', 'BFS']
    difficulty  VARCHAR(20),         -- Easy / Medium / Hard
    source      VARCHAR(100),        -- LeetCode, Codeforces, Custom
    created_at  TIMESTAMP DEFAULT NOW()
);
```

### User Problem Sessions Table
```sql
CREATE TABLE user_problem_sessions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id),
    problem_id      UUID REFERENCES problems(id),
    hints_requested INT DEFAULT 0,
    is_solved       BOOLEAN DEFAULT FALSE,
    started_at      TIMESTAMP DEFAULT NOW(),
    solved_at       TIMESTAMP
);
```

### Hint Logs Table
```sql
CREATE TABLE hint_logs (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id  UUID REFERENCES user_problem_sessions(id),
    hint_level  INT NOT NULL,        -- 1 = vague, 5 = near-solution
    hint_text   TEXT NOT NULL,
    delivered_at TIMESTAMP DEFAULT NOW()
);
```

---

## 8. API Design

### Authentication
| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/register` | Register a new user |
| POST | `/auth/login` | Login and receive JWT token |
| POST | `/auth/logout` | Invalidate session |

### Hints
| Method | Endpoint | Description |
|---|---|---|
| POST | `/hints/submit` | Submit a problem, receive first hint |
| GET | `/hints/next/{session_id}` | Get next progressive hint |
| GET | `/hints/session/{session_id}` | Get all hints for a session |

### Progress
| Method | Endpoint | Description |
|---|---|---|
| GET | `/progress/history` | Get all problems attempted by user |
| GET | `/progress/stats` | Get learning stats (concepts mastered, etc.) |
| PATCH | `/progress/solve/{session_id}` | Mark problem as solved |

### Recommendations
| Method | Endpoint | Description |
|---|---|---|
| GET | `/recommend/problems` | Get recommended problems based on user profile |

---

## 9. LLM Integration Strategy

### System Prompt Design (Socratic Mode)
```
You are CodeWhisper, an AI learning companion for developers.
Your role is to help users solve coding/DSA problems through hints — 
NOT by revealing the full solution.

When given a problem:
1. Identify the core data structure or algorithm pattern involved.
2. Generate exactly 5 progressive hints:
   - Hint 1: A high-level nudge about problem category.
   - Hint 2: A guiding question about the approach.
   - Hint 3: A conceptual clue about the algorithm.
   - Hint 4: A pseudocode-level direction.
   - Hint 5: A near-complete approach (no full code).

Never reveal the full solution. Encourage the user to think.
```

### Adapter Pattern for LLM Providers
```python
# llm/base.py
class BaseLLMClient(ABC):
    @abstractmethod
    def generate_hints(self, problem: str) -> list[str]:
        pass

# llm/openai_client.py
class OpenAIClient(BaseLLMClient):
    def generate_hints(self, problem: str) -> list[str]:
        # Call OpenAI GPT API
        ...

# llm/claude_client.py
class ClaudeClient(BaseLLMClient):
    def generate_hints(self, problem: str) -> list[str]:
        # Call Anthropic Claude API
        ...
```

---

## 10. Security Considerations

| Concern | Mitigation |
|---|---|
| **API Key Exposure** | Store keys in `.env`, never commit to version control |
| **Authentication** | JWT tokens with expiry; refresh token mechanism |
| **Rate Limiting** | Redis-backed rate limiting per user (e.g., 20 hint requests/hour) |
| **Input Sanitization** | Validate and sanitize problem input before passing to LLM |
| **Prompt Injection** | Enforce strict system prompts; strip suspicious characters from user input |
| **SQL Injection** | Use SQLAlchemy ORM parameterized queries exclusively |
| **CORS** | Restrict allowed origins in Flask-CORS configuration |

---

## 11. Scalability & Performance

| Strategy | Details |
|---|---|
| **Redis Hint Caching** | Cache hint sequences by `hash(problem_text)` to avoid duplicate LLM calls |
| **Async LLM Calls** | Use `asyncio` or Celery task queue for non-blocking LLM API calls |
| **Database Indexing** | Index `user_id`, `problem_id`, and `tags` columns for fast queries |
| **Horizontal Scaling** | Stateless Flask app allows multiple instances behind a load balancer |
| **CDN** | Serve static frontend assets via CDN (e.g., Cloudflare) |
| **LLM Cost Control** | Cache aggressively; set max token limits on LLM responses |

---

## 12. Folder Structure

```
codewhisper/
├── app/
│   ├── __init__.py               # Flask app factory
│   ├── config.py                 # Configuration (dev/prod)
│   ├── extensions.py             # DB, Redis, JWT init
│   │
│   ├── routes/
│   │   ├── auth.py               # /auth endpoints
│   │   ├── hints.py              # /hints endpoints
│   │   ├── progress.py           # /progress endpoints
│   │   └── recommend.py          # /recommend endpoints
│   │
│   ├── services/
│   │   ├── hint_engine.py        # Core hint generation logic
│   │   ├── progress_tracker.py   # User progress tracking
│   │   └── recommender.py        # Problem recommendation
│   │
│   ├── llm/
│   │   ├── base.py               # Abstract LLM client
│   │   ├── openai_client.py      # OpenAI GPT integration
│   │   └── claude_client.py      # Anthropic Claude integration
│   │
│   ├── models/
│   │   ├── user.py               # User model
│   │   ├── problem.py            # Problem model
│   │   ├── session.py            # UserProblemSession model
│   │   └── hint_log.py           # HintLog model
│   │
│   └── utils/
│       ├── cache.py              # Redis helpers
│       ├── validators.py         # Input validation
│       └── prompt_builder.py     # LLM prompt construction
│
├── tests/
│   ├── test_hint_engine.py
│   ├── test_auth.py
│   └── test_progress.py
│
├── migrations/                   # Alembic DB migrations
├── .env.example                  # Environment variable template
├── requirements.txt              # Python dependencies
├── Dockerfile                    # Container definition
├── docker-compose.yml            # Local dev stack (Flask + Postgres + Redis)
└── README.md                     # Project overview
```

---

## Summary

| Aspect | Decision |
|---|---|
| **Architecture** | Layered Monolith (Flask) with service-oriented internals |
| **LLM Strategy** | Adapter pattern supporting OpenAI & Claude; Socratic prompt design |
| **Hint Delivery** | Progressive, session-based, Redis-cached |
| **Data Storage** | PostgreSQL for persistence, Redis for sessions & cache |
| **Auth** | JWT-based with Flask-JWT-Extended |
| **Scalability Path** | Stateless Flask → Celery workers → Microservices (future) |

> **CodeWhisper** is designed to be a robust, extensible, and educationally responsible platform that truly transforms how developers learn DSA — one hint at a time. 🚀
