from typing import Literal

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Populate os.environ from .env so third-party libraries that read provider
# API keys directly (e.g. pydantic-ai's GoogleProvider reading GOOGLE_API_KEY)
# can see them. pydantic-settings only loads .env into the Settings object,
# not into the process environment.
load_dotenv()


class Settings(BaseSettings):
    # DATABASE_URL is what the running app (and Alembic) connect to. The four
    # DATABASE_URL_* variants are the single source of truth for the per-target
    # URLs used by maintenance scripts that take a `--db dev|benchmark|prod`
    # flag; resolve them via db_url_for_target() rather than port-swapping
    # DATABASE_URL. All are reached over localhost (dev/benchmark via Docker,
    # prod via the SSH tunnel from bin/prod_db_tunnel.sh). Override in .env.
    DATABASE_URL: str = "postgresql+asyncpg://flawchess:flawchess@localhost:5432/flawchess"
    DATABASE_URL_DEV: str = "postgresql+asyncpg://flawchess:flawchess@localhost:5432/flawchess"
    DATABASE_URL_TEST: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/flawchess_test"
    DATABASE_URL_PROD: str = "postgresql+asyncpg://flawchess:flawchess@localhost:15432/flawchess"
    DATABASE_URL_BENCHMARK: str = "postgresql+asyncpg://flawchess_benchmark:flawchess_benchmark@localhost:5433/flawchess_benchmark"
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
    # "anthropic:claude-haiku-4-5-20251001", "google:gemini-3.5-flash".
    # Tests use the built-in "test" provider (see tests/conftest.py).
    PYDANTIC_AI_MODEL_INSIGHTS: str = ""
    # When true, insights service strips `report.overview = ""` before
    # returning to client. Full overview still persists in llm_logs.response_json
    # for offline analysis — log is source of truth, response is policy-gated
    # view (D-18, BETA-02).
    INSIGHTS_HIDE_OVERVIEW: bool = False

    # Google Gemini thinking controls. Only applied when PYDANTIC_AI_MODEL_INSIGHTS
    # starts with "google:" or "google-cloud:". Silently ignored for other
    # providers (Anthropic, OpenAI, test).
    #
    # GEMINI_THINKING_LEVEL:  Gemini 3+ knob — "minimal", "low", "medium", or
    #   "high", in increasing reasoning depth / token cost / latency. "minimal"
    #   is the cheapest/fastest (Google's equivalent of the old 2.5
    #   thinking_budget=0). Gemini 3.5's own default is "medium"; we default to
    #   "low" to keep insights cheap and fast.
    # GEMINI_THINKING_BUDGET: Gemini 2.5 knob — explicit token cap. 0 disables
    #   thinking entirely. Ignored on Gemini 3 (which uses thinking_level).
    # GEMINI_INCLUDE_THOUGHTS: when True, Google returns thoughts_token_count in
    #   usage metadata so the insights service can persist them to
    #   llm_logs.thinking_tokens for cost attribution.
    GEMINI_THINKING_LEVEL: Literal["minimal", "low", "medium", "high"] = "low"
    GEMINI_THINKING_BUDGET: int = 0
    GEMINI_INCLUDE_THOUGHTS: bool = True

    # Automatic background full-eval toggle (Phase 117). When False, the tier-3
    # idle-backlog derived pick is suppressed — the only automatic eval source as of
    # Phase 118, which removed the tier-2 auto-window enqueue. Tier-1 (explicit,
    # on-demand single-game request) is UNAFFECTED — on-demand analysis still works.
    # Default False (safe for dev/CI so a local backend doesn't pin every core on the
    # hundreds-of-thousands-game backlog). Prod opts in explicitly via its .env.
    EVAL_AUTO_DRAIN_ENABLED: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()


# Maintenance scripts (backfill_eval, reindex_table, gen_benchmarks, …) accept a
# `--db` flag and resolve the connection URL through here, so the DATABASE_URL_*
# settings above are the one place credentials/hosts/ports are configured.
DbTarget = Literal["dev", "test", "prod", "benchmark"]


def db_url_for_target(target: str) -> str:
    """Resolve a script ``--db`` target to its configured async DB URL.

    ``target`` is one of ``DbTarget`` (typed loosely as ``str`` because callers
    pass argparse values). Reads the matching ``DATABASE_URL_*`` setting (sourced
    from ``.env``). Raises ``ValueError`` for an unknown target.
    """
    urls: dict[str, str] = {
        "dev": settings.DATABASE_URL_DEV,
        "test": settings.DATABASE_URL_TEST,
        "prod": settings.DATABASE_URL_PROD,
        "benchmark": settings.DATABASE_URL_BENCHMARK,
    }
    try:
        return urls[target]
    except KeyError:
        raise ValueError(f"Unknown DB target: {target!r}. Must be one of: {sorted(urls)}") from None
