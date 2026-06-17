"""
X Automation — Konfiqurasiya İdarəetməsi
Bütün .env parametrlərini oxuyur və doğrulayır.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ENV_FILE mühit dəyişəni vasitəsilə fərqli .env faylı yükləmək mümkündür (məsələn: .env.production)
env_file = os.getenv("ENV_FILE", ".env")
load_dotenv(dotenv_path=env_file)


class Settings:
    """Bütün konfiqurasiya parametrlərini bir yerdə toplayır."""

    # ── X (Twitter) API ──────────────────────────────────────────────────────
    X_API_KEY: str = os.getenv("X_API_KEY", "")
    X_API_SECRET: str = os.getenv("X_API_SECRET", "")
    X_ACCESS_TOKEN: str = os.getenv("X_ACCESS_TOKEN", "")
    X_ACCESS_TOKEN_SECRET: str = os.getenv("X_ACCESS_TOKEN_SECRET", "")
    X_BEARER_TOKEN: str = os.getenv("X_BEARER_TOKEN", "")

    # ── Grok API (xAI) ───────────────────────────────────────────────────────
    GROK_API_KEY: str = os.getenv("GROK_API_KEY", "")
    GROK_BASE_URL: str = "https://api.x.ai/v1"

    # ── DeepSeek API ─────────────────────────────────────────────────────────
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"

    # ── Post Parametrləri ────────────────────────────────────────────────────
    POST_TIME: str = os.getenv("POST_TIME", "09:00")
    TIMEZONE: str = os.getenv("TIMEZONE", "Asia/Baku")
    POST_LANGUAGE: str = os.getenv("POST_LANGUAGE", "English")
    BUSINESS_NICHE: str = os.getenv("BUSINESS_NICHE", "Business, Startups, Finance")
    
    # ── Video Repost Parametrləri ──────────────────────────────────────────
    VIDEO_REPOST_TIME: str = os.getenv("VIDEO_REPOST_TIME", "18:00")
    VIDEO_REPOST_ENABLED: bool = os.getenv("VIDEO_REPOST_ENABLED", "true").lower() == "true"
    VIDEO_REPOST_MIN_FOLLOWERS: int = int(os.getenv("VIDEO_REPOST_MIN_FOLLOWERS", "50000"))
    VIDEO_REPOST_WINDOW_HOURS: int = int(os.getenv("VIDEO_REPOST_WINDOW_HOURS", "24"))

    # ── Media ─────────────────────────────────────────────────────────────────
    MEDIA_FOLDER: str = os.getenv("MEDIA_FOLDER", "data/media")

    # ── Sistem ───────────────────────────────────────────────────────────────
    DRY_RUN: bool = os.getenv("DRY_RUN", "false").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # ── Yollar ───────────────────────────────────────────────────────────────
    BASE_DIR: Path = Path(__file__).parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    LOGS_DIR: Path = BASE_DIR / "logs"
    HISTORY_FILE: Path = DATA_DIR / "history.json"

    @property
    def MEDIA_DIR(self) -> Path:
        return self.BASE_DIR / self.MEDIA_FOLDER

    def validate(self) -> None:
        """Tələb olunan parametrlərin mövcudluğunu yoxlayır."""
        required = {
            "X_API_KEY": self.X_API_KEY,
            "X_API_SECRET": self.X_API_SECRET,
            "X_ACCESS_TOKEN": self.X_ACCESS_TOKEN,
            "X_ACCESS_TOKEN_SECRET": self.X_ACCESS_TOKEN_SECRET,
            "GROK_API_KEY": self.GROK_API_KEY,
            "DEEPSEEK_API_KEY": self.DEEPSEEK_API_KEY,
        }
        missing = [k for k, v in required.items() if not v or v.endswith("_here")]
        if missing:
            raise ValueError(
                f"❌ .env faylında bu parametrlər boşdur: {', '.join(missing)}\n"
                "   .env.example faylına baxın və .env faylınızı doldurun."
            )

    def ensure_dirs(self) -> None:
        """Lazımi qovluqları yaradır."""
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.LOGS_DIR.mkdir(parents=True, exist_ok=True)
        self.MEDIA_DIR.mkdir(parents=True, exist_ok=True)


settings = Settings()
