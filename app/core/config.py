from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://flawchess:flawchess@localhost:5432/flawchess"
    TEST_DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/flawchess_test"
    DB_ECHO: bool = False
    SECRET_KEY: str = "change-me-in-production"
    GOOGLE_OAUTH_CLIENT_ID: str = ""
    GOOGLE_OAUTH_CLIENT_SECRET: str = ""
    BACKEND_URL: str = "http://localhost:8000"
    # Frontend base URL — used to build OAuth redirect back to SPA
    FRONTEND_URL: str = "http://localhost:5173"
    # Environment: "development" bypasses JWT auth on all endpoints
    ENVIRONMENT: str = "production"
    SENTRY_DSN: str = ""  # Empty string = Sentry disabled (dev default)
    SENTRY_TRACES_SAMPLE_RATE: float = 0.0  # 0.0 = no traces (dev default)

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
