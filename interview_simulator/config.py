import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    BASE_DIR = BASE_DIR
    DATA_DIR = BASE_DIR / "data"
    UPLOAD_DIR = BASE_DIR / "uploads"
    DATABASE = DATA_DIR / "interview_simulator.db"

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-secret-change-me")
    PORT = int(os.getenv("PORT", "5000"))
    DEBUG = os.getenv("FLASK_DEBUG", "0").lower() in {"1", "true", "yes"}

    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH_MB", "8")) * 1024 * 1024
    QUESTION_TIME_LIMIT = int(os.getenv("QUESTION_TIME_LIMIT_SECONDS", "120"))
    MAX_QUESTIONS_PER_SESSION = int(os.getenv("MAX_QUESTIONS_PER_SESSION", "5"))
    PERMANENT_SESSION_LIFETIME_DAYS = int(os.getenv("SESSION_LIFETIME_DAYS", "7"))

    AI_PROVIDER = os.getenv("AI_PROVIDER", "hybrid").strip().lower()
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_FOLLOWUP_MODEL = os.getenv("OPENAI_FOLLOWUP_MODEL", "gpt-5-mini")
    OPENAI_TIMEOUT_SECONDS = int(os.getenv("OPENAI_TIMEOUT_SECONDS", "8"))

    SESSION_COOKIE_NAME = "interview_simulator_session"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
