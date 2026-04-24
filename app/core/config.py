from typing import Literal

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Populate os.environ from .env so third-party libraries that read provider
# API keys directly (e.g. pydantic-ai's GoogleProvider reading GOOGLE_API_KEY)
# can see them. pydantic-settings only loads .env into the Settings object,
# not into the process environment.
load_dotenv()


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

    # Google Gemini thinking controls. Only applied when PYDANTIC_AI_MODEL_INSIGHTS
    # starts with "google-gla:" or "google-vertex:". Silently ignored for other
    # providers (Anthropic, OpenAI, test).
    #
    # GEMINI_THINKING_LEVEL:  Gemini 3+ knob (e.g. gemini-3-flash-preview) —
    #   "low" (cheaper, faster) or "high" (more reasoning).
    # GEMINI_THINKING_BUDGET: Gemini 2.5 knob — explicit token cap. 0 disables
    #   thinking entirely. Ignored on Gemini 3 (which uses thinking_level).
    # GEMINI_INCLUDE_THOUGHTS: when True, Google returns thoughts_token_count in
    #   usage metadata so the insights service can persist them to
    #   llm_logs.thinking_tokens for cost attribution.
    GEMINI_THINKING_LEVEL: Literal["low", "high"] = "low"
    GEMINI_THINKING_BUDGET: int = 0
    GEMINI_INCLUDE_THOUGHTS: bool = True

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
