"""
CodeWhisper — Application Configuration
Loads settings from environment variables via python-dotenv.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY  = os.getenv("SECRET_KEY", "dev-fallback-secret-change-in-prod")
    FLASK_ENV   = os.getenv("FLASK_ENV", "development")

    SQLALCHEMY_DATABASE_URI    = os.getenv(
        "DATABASE_URL",
        "sqlite:///codewhisper_dev.db"
        )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO            = False

    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    JWT_SECRET_KEY           = os.getenv("JWT_SECRET_KEY", "jwt-fallback-secret-change-in-prod")
    JWT_ACCESS_TOKEN_EXPIRES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES", 3600))
    JWT_TOKEN_LOCATION       = ["headers"]
    JWT_HEADER_NAME          = "Authorization"
    JWT_HEADER_TYPE          = "Bearer"

    LLM_PROVIDER    = os.getenv("LLM_PROVIDER", "groq")
    GROQ_API_KEY    = os.getenv("GROQ_API_KEY")
    GROQ_MODEL      = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL    = os.getenv("OPENAI_MODEL", "gpt-4o")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    CLAUDE_MODEL      = os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")

    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")


class DevelopmentConfig(Config):
    DEBUG = True


class StandaloneConfig(Config):
    """
    No-dependency dev mode: SQLite file + in-memory rate limiter.
    Used when PostgreSQL/Redis are not available (local quick-start).
    """
    import os as _os
    _BASE = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), ".."))
    DEBUG = True
    SQLALCHEMY_DATABASE_URI  = f"sqlite:///{_BASE}/codewhisper_dev.db"
    RATELIMIT_STORAGE_URI    = "memory://"


class ProductionConfig(Config):
    DEBUG = False


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
    env = os.getenv("FLASK_ENV", "development").lower()
    return config_map.get(env, DevelopmentConfig)
