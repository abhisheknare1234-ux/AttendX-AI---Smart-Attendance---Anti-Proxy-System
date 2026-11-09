"""Application configuration.

Configuration is environment-driven. A `.env` file may be used for local development; in
production all values must be supplied by the deployment environment (or a secret manager).
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_SECRET = "dev-only-insecure-secret-key-change-before-deploying-attendx"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Application -----------------------------------------------------
    app_name: str = "AttendX AI"
    app_env: Literal["development", "test", "staging", "production"] = "development"
    debug: bool = False
    log_level: str = "INFO"
    api_v1_prefix: str = "/api/v1"

    # --- Database --------------------------------------------------------
    # PostgreSQL is the production database. SQLite is supported for local
    # development and the automated test suite only.
    database_url: str = "sqlite:///./attendx_dev.db"

    # --- Secrets ---------------------------------------------------------
    secret_key: str = ""
    qr_signing_key: str = ""

    # --- Auth sessions ---------------------------------------------------
    session_ttl_minutes: int = Field(default=480, ge=5, le=60 * 24 * 30)
    session_cookie_name: str = "attendx_session"
    csrf_cookie_name: str = "attendx_csrf"
    cookie_secure: bool | None = None
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"

    # --- Web / origins ---------------------------------------------------
    web_origin: str = "http://localhost:3000"
    allowed_origins: str = ""  # comma-separated extra CORS origins

    # --- Login protection ------------------------------------------------
    login_max_attempts: int = 5
    login_window_seconds: int = 300
    login_lockout_minutes: int = 15
    ip_rate_limit_per_minute: int = 60

    # --- Attendance defaults --------------------------------------------
    default_attendance_window_seconds: int = 180
    default_qr_refresh_seconds: int = 30
    qr_grace_seconds: int = 15
    pin_length: int = 6
    pin_max_attempts: int = 5
    pin_expiry_grace_seconds: int = 60

    # --- Geofence --------------------------------------------------------
    default_geofence_radius_m: float = 60.0
    default_max_gps_accuracy_m: float = 100.0
    gps_stale_after_seconds: int = 120

    # --- Verification providers -----------------------------------------
    # "none" means the factor is genuinely unavailable and is reported as
    # such. It never fabricates a successful verification. "local_opencv"
    # uses local YuNet + SFace models and encrypted templates.
    face_provider: Literal["none", "http", "local_opencv"] = "none"
    face_http_url: str = ""
    face_http_token: str = ""
    face_provider_model: str = "external-face-v1"
    face_model_dir: str = "models"
    face_match_threshold: float = Field(default=0.363, ge=0.0, le=1.0)
    face_detection_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    face_template_key: str = ""

    liveness_provider: Literal["none", "http", "local_minifas"] = "none"
    liveness_http_url: str = ""
    liveness_http_token: str = ""
    liveness_provider_model: str = "external-liveness-v1"
    liveness_model_dir: str = "models"
    liveness_threshold: float = Field(default=0.0, ge=-20.0, le=20.0)

    # --- Bootstrap / development ----------------------------------------
    bootstrap_admin_email: str = ""
    bootstrap_admin_password: str = ""
    bootstrap_admin_name: str = "Institutional Administrator"
    seed_dev_data: bool = False

    # --- Data retention --------------------------------------------------
    evidence_retention_days: int = 180
    session_retention_days: int = 30

    @field_validator("secret_key", "qr_signing_key", mode="before")
    @classmethod
    def _strip(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def _validate_secrets(self) -> "Settings":
        if not self.secret_key:
            if self.app_env == "production":
                raise ValueError("SECRET_KEY must be set in production")
            self.secret_key = DEV_SECRET
        if not self.qr_signing_key:
            self.qr_signing_key = self.secret_key
        if self.app_env == "production" and self.secret_key == DEV_SECRET:
            raise ValueError("Refusing to run in production with the development SECRET_KEY")
        if self.cookie_secure is None:
            object.__setattr__(self, "cookie_secure", self.app_env in {"staging", "production"})
        if self.pin_length < 4 or self.pin_length > 10:
            raise ValueError("PIN_LENGTH must be between 4 and 10")
        return self

    @property
    def effective_cookie_secure(self) -> bool:
        return bool(self.cookie_secure)

    @property
    def cors_origins(self) -> list[str]:
        origins = {self.web_origin.strip().rstrip("/")}
        for item in self.allowed_origins.split(","):
            item = item.strip().rstrip("/")
            if item:
                origins.add(item)
        return sorted(origins)

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
