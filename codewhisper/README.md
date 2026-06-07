# 🤫 CodeWhisper
> AI-Powered Hint Engine for DSA & Coding Problem Learning

---

## Overview

**CodeWhisper** is an AI-powered learning companion that helps developers and students solve Data Structures & Algorithms (DSA) problems through **progressive, Socratic-style hints** — rather than giving away direct answers.

Instead of copy-pasting solutions, users paste their problem and receive intelligent, step-by-step hints that guide them toward the answer while encouraging genuine understanding.

---

## Features

- 🔍 **Problem Analysis** — Identifies underlying DSA concepts and patterns
- 💡 **Progressive Hints** — 5-level hint sequence from vague nudge → near-complete approach
- 🧠 **Socratic Guidance** — Never reveals the full solution; promotes critical thinking
- 📊 **Progress Tracking** — History of solved problems and learning stats
- 🎯 **Recommendations** — Similar problems suggested based on concepts practiced
- 🔐 **Secure Auth** — JWT-based authentication with token blacklisting
- ⚡ **Redis Caching** — Hints cached to minimize LLM API calls
- 🤖 **Multi-LLM Support** — OpenAI GPT-4 or Anthropic Claude (switchable)

---

## Tech Stack

| Layer        | Technology                        |
|--------------|-----------------------------------|
| Language     | Python 3.11+                      |
| Framework    | Flask                             |
| LLM APIs     | OpenAI GPT-4 / Anthropic Claude   |
| Database     | PostgreSQL                        |
| Cache        | Redis                             |
| ORM          | SQLAlchemy + Flask-Migrate        |
| Auth         | Flask-JWT-Extended                |
| Testing      | pytest + pytest-flask             |
| Deployment   | Docker + Docker Compose           |

---

## Project Structure

```
codewhisper/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── config.py            # Configuration classes
│   ├── extensions.py        # Extension instances (db, jwt, etc.)
│   ├── routes/              # API blueprints
│   ├── services/            # Business logic
│   ├── llm/                 # LLM adapter clients
│   ├── models/              # SQLAlchemy models
│   └── utils/               # Helpers (cache, validators, prompts)
├── tests/                   # Test suite
├── migrations/              # Alembic migrations
├── scripts/                 # Utility scripts (seed, etc.)
├── templates/               # HTML templates (UI)
├── static/                  # Static assets (CSS, JS)
├── .env.example             # Environment variable template
├── requirements.txt         # Python dependencies
├── Dockerfile               # Container definition
├── docker-compose.yml       # Local dev stack
└── run.py                   # App entry point
```

---

## Quick Start

### 1. Clone & Setup Environment
```bash
git clone <repo-url>
cd codewhisper
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your API keys and DB credentials
```

### 3. Run with Docker (Recommended)
```bash
docker-compose up --build
docker-compose exec web flask db upgrade
```

### 4. Run Locally
```bash
flask db upgrade
flask run
```

### 5. Run Tests
```bash
pytest tests/ -v --cov=app
```

---

## API Endpoints

| Method | Endpoint                        | Description                  |
|--------|---------------------------------|------------------------------|
| POST   | `/auth/register`                | Register new user            |
| POST   | `/auth/login`                   | Login, receive JWT           |
| POST   | `/auth/logout`                  | Logout, blacklist token      |
| POST   | `/hints/submit`                 | Submit problem, get Hint #1  |
| GET    | `/hints/next/<session_id>`      | Get next progressive hint    |
| GET    | `/hints/session/<session_id>`   | Get all hints for session    |
| GET    | `/progress/history`             | User problem history         |
| GET    | `/progress/stats`               | Learning statistics          |
| PATCH  | `/progress/solve/<session_id>`  | Mark problem as solved       |
| GET    | `/recommend/problems`           | Get recommended problems     |

---

## Environment Variables

```env
FLASK_ENV=development
SECRET_KEY=your-secret-key
DATABASE_URL=postgresql://user:password@localhost:5432/codewhisper
REDIS_URL=redis://localhost:6379/0
LLM_PROVIDER=openai
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-claude-key
JWT_SECRET_KEY=your-jwt-secret
JWT_ACCESS_TOKEN_EXPIRES=3600
```

---

## License

MIT License — built for learning, not for copying. 🚀

---

> *"The best way to learn is to be guided, not given."* — CodeWhisper
