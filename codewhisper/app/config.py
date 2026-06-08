"""
CodeWhisper — Application Configuration
Production-hardened: PostgreSQL preferred, SQLite fallback to /tmp.
"""

import os
from dotenv import load_dotenv

load_dotenv()


def _db_url():
    """Return DATABASE_URL. Fixes postgres:// → postgresql://. Falls back to /tmp SQLite."""
    url = os.getenv("DATABASE_URL", "").strip()
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    if url:
        return url
    # Use /tmp which is always writable (works on Render, Heroku, Railway)
    return "sqlite:////tmp/codewhisper.db"


class Config:
    SECRET_KEY  = os.getenv("SECRET_KEY", "dev-fallback-secret-please-change-in-production")
    FLASK_ENV   = os.getenv("FLASK_ENV", "production")

    SQLALCHEMY_DATABASE_URI    = _db_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO            = False

    REDIS_URL = os.getenv("REDIS_URL", "")

    JWT_SECRET_KEY           = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret-please-change-in-production")
    JWT_ACCESS_TOKEN_EXPIRES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES", 3600))
    JWT_TOKEN_LOCATION       = ["headers"]
    JWT_HEADER_NAME          = "Authorization"
    JWT_HEADER_TYPE          = "Bearer"

    LLM_PROVIDER      = os.getenv("LLM_PROVIDER", "groq")
    GROQ_API_KEY      = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL        = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    OPENAI_API_KEY    = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL      = os.getenv("OPENAI_MODEL", "gpt-4o")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    CLAUDE_MODEL      = os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")

    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")


class DevelopmentConfig(Config):
    DEBUG = True
    FLASK_ENV = "development"


class ProductionConfig(Config):
    DEBUG = False
    FLASK_ENV = "production"


class StandaloneConfig(Config):
    DEBUG = True
    FLASK_ENV = "development"

    @staticmethod
    def _sqlite_path():
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        return f"sqlite:///{base}/codewhisper_dev.db"

    SQLALCHEMY_DATABASE_URI = None
    RATELIMIT_STORAGE_URI   = "memory://"


StandaloneConfig.SQLALCHEMY_DATABASE_URI = StandaloneConfig._sqlite_path()


class TestingConfig(Config):
    TESTING                  = True
    DEBUG                    = True
    SQLALCHEMY_DATABASE_URI  = "sqlite:///:memory:"
    JWT_SECRET_KEY           = "test-jwt-secret-key-long-enough-for-hs256-32bytes!"
    JWT_ACCESS_TOKEN_EXPIRES = 300
    WTF_CSRF_ENABLED         = False
    REDIS_MOCK               = True


config_map = {
    "development": DevelopmentConfig,
    "standalone":  StandaloneConfig,
    "production":  ProductionConfig,
    "testing":     TestingConfig,
}


def get_config():
    env = os.getenv("FLASK_ENV", "production").lower()
    return config_map.get(env, ProductionConfig)
