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
    JWT_SECRET: str = ""
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
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:3000"]
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
    WORKER_ENABLED: bool = True

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
    PORTAL_SECRET_KEY: str = ""
    PORTAL_TOKEN_EXPIRE_HOURS: int = 72

    # --- Twilio (SMS) ---------------------------------------------------
    TWILIO_ACCOUNT_SID: str | None = None
    TWILIO_AUTH_TOKEN: str | None = None
    TWILIO_FROM_NUMBER: str | None = None

    # --- Webhook dispatch -----------------------------------------------
    WEBHOOK_MAX_RETRIES: int = 3

    def model_post_init(self, __context) -> None:
        if not self.JWT_SECRET:
            raise ValueError("JWT_SECRET must be set")
        if len(self.JWT_SECRET) < 32:
            raise ValueError("JWT_SECRET must be at least 32 characters")
        if not self.PORTAL_SECRET_KEY:
            raise ValueError("PORTAL_SECRET_KEY must be set")

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def split_origins(cls, v):
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

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
