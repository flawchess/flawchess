from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/chessalytics"
    DB_ECHO: bool = False
    SECRET_KEY: str = "change-me-in-production"
    GOOGLE_OAUTH_CLIENT_ID: str = ""
    GOOGLE_OAUTH_CLIENT_SECRET: str = ""
    BACKEND_URL: str = "http://localhost:8000"
    # Frontend base URL — used to build OAuth redirect back to SPA
    FRONTEND_URL: str = "http://localhost:5173"
    # Environment: "development" bypasses JWT auth on all endpoints
    ENVIRONMENT: str = "production"

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
