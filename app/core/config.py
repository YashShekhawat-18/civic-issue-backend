from pydantic import SecretStr
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
    overdue_days: int = 3

    # Photo uploads
    upload_dir: str = "uploads"
    max_upload_mb: int = 5

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
