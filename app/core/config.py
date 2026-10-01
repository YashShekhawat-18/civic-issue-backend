from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    mongo_uri: str = "mongodb://127.0.0.1:27017"
    mongo_db_name: str = "civic_issue_db"
    client_url: str = "http://localhost:3000"

    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60

    duplicate_radius_meters: int = 100
    overdue_days: int = 3


settings = Settings()


def validate_settings() -> None:
    """Called at startup. Stops the app early if the JWT secret is unsafe."""
    secret = settings.jwt_secret
    if not secret or secret.startswith("CHANGE_THIS") or len(secret) < 32:
        raise RuntimeError(
            "JWT_SECRET is missing or too weak. Generate one with: "
            'python -c "import secrets; print(secrets.token_urlsafe(48))"'
        )