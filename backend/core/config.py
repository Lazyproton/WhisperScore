"""
WhisperScore — Application Configuration
Loads settings from environment variables / .env file.
"""
from pydantic_settings import BaseSettings
from pathlib import Path
from typing import List


class Settings(BaseSettings):
    # ─── App ──────────────────────────────────────────────
    APP_NAME: str = "WhisperScore API"
    VERSION: str = "1.0.0"
    DEBUG: bool = True

    # ─── Database ─────────────────────────────────────────
    DATABASE_URL: str = "sqlite:///./whisperscore.db"

    # ─── Storage ──────────────────────────────────────────
    UPLOAD_DIR: Path = Path("uploads")
    MAX_FILE_SIZE_MB: int = 500

    # ─── Groq LLM ─────────────────────────────────────────
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.1-8b-instant"

    # ─── Whisper ──────────────────────────────────────────
    WHISPER_MODEL_SIZE: str = "base"
    # Compute type: "int8" (CPU), "float16" (GPU)
    WHISPER_COMPUTE_TYPE: str = "int8"
    WHISPER_DEVICE: str = "cpu"

    # ─── CORS ─────────────────────────────────────────────
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
    ]

    # ─── Analysis ─────────────────────────────────────────
    MAX_RECORDING_DURATION_SECONDS: int = 600  # 10 min
    ENABLE_VIDEO_ANALYSIS: bool = True

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

# Ensure upload directory exists
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
