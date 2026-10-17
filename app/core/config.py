from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # env_ignore_empty=True: a line like "SMTP_PORT=" in .env is treated as "not set"
    # (the default below is used) instead of crashing the app.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", env_ignore_empty=True)

    app_env: str = "development"
    mongo_uri: str = "mongodb://127.0.0.1:27017"
    mongo_db_name: str = "civic_issue_db"
    client_url: str = "http://localhost:3000"

    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60

    duplicate_radius_meters: int = 100

    # Overdue job (Phase 8)
    overdue_days: int = Field(default=3, ge=1)           # unresolved for this many days = overdue
    overdue_check_minutes: int = Field(default=60, ge=1)  # how often the job runs
    scheduler_enabled: bool = True                        # SCHEDULER_ENABLED=false switches the job off

    # Points (Phase 9). Set a value to 0 to switch that reward off.
    points_complaint_created: int = Field(default=10, ge=0)    # citizen reports a NEW complaint
    points_complaint_upvoted: int = Field(default=2, ge=0)     # citizen upvotes someone's complaint (once per complaint)
    points_complaint_resolved: int = Field(default=20, ge=0)   # reporter's complaint gets RESOLVED

    # Security (Phase 11)
    rate_limit_enabled: bool = True
    rate_limit_login_max: int = Field(default=10, ge=1)      # login attempts per IP per window
    rate_limit_register_max: int = Field(default=5, ge=1)    # sign-ups per IP per window
    rate_limit_window_seconds: int = Field(default=900, ge=1)
    trust_proxy_headers: bool = False                        # True only behind your own reverse proxy
    max_json_body_kb: int = Field(default=256, ge=1)         # biggest allowed non-upload request body

    # Photo uploads
    upload_dir: str = "uploads"
    max_upload_mb: int = 5

    # Geotagged photos: a photo must carry the GPS position of where it was taken (JPEG).
    # REQUIRE_PHOTO_GPS=false switches the rule off (for example for a quick demo with any photo).
    require_photo_gps: bool = True
    geotag_max_distance_meters: int = Field(default=300, ge=10)  # photo position vs. complaint position

    # Email (Phase 7). Leave SMTP_HOST empty and the app simply skips sending emails.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: SecretStr = SecretStr("")
    smtp_from: str = ""
    smtp_use_tls: bool = True  # STARTTLS on port 587. Port 465 uses SSL automatically.

    # Only used by the seed script
    seed_admin_name: str = "System Admin"
    seed_admin_email: str = ""
    seed_admin_password: str = ""
    seed_worker_password: str = ""


settings = Settings()


def validate_settings() -> None:
    """Called at startup. Stops the app early if the JWT secret is unsafe."""
    secret = settings.jwt_secret
    if not secret or secret.startswith("CHANGE_THIS") or len(secret) < 32:
        raise RuntimeError(
            "JWT_SECRET is missing or too weak. Generate one with: "
            'python -c "import secrets; print(secrets.token_urlsafe(48))"'
        )
