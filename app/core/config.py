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
    # "development" enables CORS for localhost:5173 and drops the Secure flag on auth cookies (so cookies work over plain HTTP in local dev)
    ENVIRONMENT: str = "production"
    SENTRY_DSN: str = ""  # Empty string = Sentry disabled (dev default)
    SENTRY_TRACES_SAMPLE_RATE: float = 0.0  # 0.0 = no traces (dev default)

    # Pydantic-AI model string for endgame insights (Phase 65). Empty string
    # is treated as "unconfigured" — app/main.py lifespan calls
    # get_insights_agent() which raises UserError on the empty string, aborting
    # startup (D-22/D-23). Accepts any pydantic-ai model string, e.g.
    # "anthropic:claude-haiku-4-5-20251001", "google-gla:gemini-2.5-flash".
    # Tests use the built-in "test" provider (see tests/conftest.py).
    PYDANTIC_AI_MODEL_INSIGHTS: str = ""
    # When true, insights service strips `report.overview = ""` before
    # returning to client. Full overview still persists in llm_logs.response_json
    # for offline analysis — log is source of truth, response is policy-gated
    # view (D-18, BETA-02).
    INSIGHTS_HIDE_OVERVIEW: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
