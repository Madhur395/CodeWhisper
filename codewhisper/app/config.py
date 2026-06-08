"""
CodeWhisper — Application Configuration
Production-hardened with PostgreSQL + SQLite fallback.
"""

import os
from dotenv import load_dotenv

load_dotenv()


def _db_url():
    """Return DATABASE_URL, fixing postgres:// → postgresql:// for Render."""
    url = os.getenv("DATABASE_URL", "").strip()
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    if url:
        return url
    # Fallback to SQLite when no DATABASE_URL is set (works on Render free tier too)
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    sqlite_path = os.path.join(base, "codewhisper_prod.db")
    return f"sqlite:///{sqlite_path}"


class Config:
    # Flask
    SECRET_KEY  = os.getenv("SECRET_KEY", "dev-fallback-CHANGE-IN-PROD-" + "x"*20)
    FLASK_ENV   = os.getenv("FLASK_ENV", "production")

    # Database — PostgreSQL if set, SQLite fallback
    SQLALCHEMY_DATABASE_URI    = _db_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO            = False

    # Redis (optional)
    REDIS_URL = os.getenv("REDIS_URL", "")

    # JWT
    JWT_SECRET_KEY           = os.getenv("JWT_SECRET_KEY", "jwt-fallback-CHANGE-IN-PROD-" + "y"*20)
    JWT_ACCESS_TOKEN_EXPIRES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES", 3600))
    JWT_TOKEN_LOCATION       = ["headers"]
    JWT_HEADER_NAME          = "Authorization"
    JWT_HEADER_TYPE          = "Bearer"

    # LLM
    LLM_PROVIDER      = os.getenv("LLM_PROVIDER", "groq")
    GROQ_API_KEY      = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL        = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    OPENAI_API_KEY    = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL      = os.getenv("OPENAI_MODEL", "gpt-4o")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    CLAUDE_MODEL      = os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")

    # CORS
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")


class DevelopmentConfig(Config):
    DEBUG = True
    FLASK_ENV = "development"


class ProductionConfig(Config):
    DEBUG = False
    FLASK_ENV = "production"


class StandaloneConfig(Config):
    """SQLite + in-memory for local dev without Docker."""
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
    """Return the correct config class based on FLASK_ENV."""
    env = os.getenv("FLASK_ENV", "production").lower()
    return config_map.get(env, ProductionConfig)
