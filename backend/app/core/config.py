import logging
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger("orcai.config")

_INSECURE_DEFAULTS = {"change-me-to-a-long-random-secret", "portal-dev-secret"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- Environment -----------------------------------------------------
    ENV: str = "development"  # development | staging | production
    DEBUG: bool = False

    # --- Database --------------------------------------------------------
    # sqlite:///./orcai.db (dev) or postgresql+psycopg://user:pass@host/db
    DATABASE_URL: str = "sqlite:///./orcai.db"

    # --- Auth ------------------------------------------------------------
    JWT_SECRET: str = "change-me-to-a-long-random-secret"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # --- AI providers ----------------------------------------------------
    # Provider priority: gemini -> openai -> deterministic (fallback).
    AI_PROVIDER: str = "auto"  # auto | gemini | openai | none
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-2.5-flash"
    OPENAI_API_KEY: str | None = None
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    LLM_MODEL: str = "gpt-4o-mini"
    AI_TIMEOUT_SECONDS: float = 60.0

    # --- Inbound channels ------------------------------------------------
    WHATSAPP_VERIFY_TOKEN: str | None = None
    WHATSAPP_PHONE_NUMBER_ID: str | None = None
    WHATSAPP_APP_SECRET: str | None = None  # for X-Hub-Signature-256 verification
    TELEGRAM_BOT_TOKEN: str | None = None
    TELEGRAM_SECRET_TOKEN: str | None = None  # X-Telegram-Bot-Api-Secret-Token

    # --- CORS / security -------------------------------------------------
    BACKEND_CORS_ORIGINS: str = "http://localhost:3000"
    SECURITY_HEADERS: bool = True
    MAX_UPLOAD_BYTES: int = 5 * 1024 * 1024  # 5 MB

    # --- Rate limiting ---------------------------------------------------
    RL_ENABLED: bool = True
    RL_REQUESTS_PER_MINUTE: int = 180  # per IP + authenticated user
    RL_BURST: int = 40

    # --- Background jobs -------------------------------------------------
    JOBS_ENABLED: bool = True
    JOBS_POLL_SECONDS: float = 2.0
    JOBS_MAX_ATTEMPTS: int = 3
    JOBS_LEASE_SECONDS: int = 300

    # --- Billing / uploads ----------------------------------------------
    DEFAULT_AGENCY_TIER: str = "starter"
    UPLOAD_DIR: str = "uploads"

    # --- Email (SMTP) ---------------------------------------------------
    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM: str = "noreply@orcai.ai"
    SMTP_TLS: bool = True

    # --- Scrapers -------------------------------------------------------
    SCRAPE_USER_AGENT: str = "ORCAI-RecruiterBot/1.0"
    SCRAPE_DELAY_SECONDS: float = 2.0
    SCRAPE_MAX_RESULTS: int = 100
    GOOGLE_API_KEY: str | None = None
    GOOGLE_CX_ID: str | None = None  # Custom Search Engine ID

    # --- Enrichment (Tier 3) -------------------------------------------
    APOLLO_API_KEY: str | None = None
    PDL_API_KEY: str | None = None
    HUNTER_API_KEY: str | None = None

    # --- Billing (Stripe / Razorpay) -----------------------------------
    STRIPE_SECRET_KEY: str | None = None
    STRIPE_PUBLISHABLE_KEY: str | None = None
    STRIPE_WEBHOOK_SECRET: str | None = None
    RAZORPAY_KEY_ID: str | None = None
    RAZORPAY_KEY_SECRET: str | None = None
    RAZORPAY_WEBHOOK_SECRET: str | None = None

    # --- Candidate self-service portal ---------------------------------
    PORTAL_SECRET_KEY: str = "portal-dev-secret"
    PORTAL_TOKEN_EXPIRE_HOURS: int = 72

    def model_post_init(self, __context) -> None:
        if self.ENV == "production":
            if self.JWT_SECRET in _INSECURE_DEFAULTS:
                raise ValueError("JWT_SECRET must be changed from its default value in production")
            if self.PORTAL_SECRET_KEY in _INSECURE_DEFAULTS:
                raise ValueError("PORTAL_SECRET_KEY must be changed from its default value in production")

    @field_validator("BACKEND_CORS_ORIGINS")
    @classmethod
    def split_origins(cls, v: str) -> list[str]:
        return [o.strip() for o in v.split(",") if o.strip()]

    @property
    def cors_origins(self) -> list[str]:
        return self.BACKEND_CORS_ORIGINS

    @property
    def is_production(self) -> bool:
        return self.ENV == "production"

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()
