# Phase 69: Benchmark DB Infrastructure & Ingestion Pipeline - Pattern Map

**Mapped:** 2026-04-25
**Files analyzed:** 14
**Analogs found:** 13 / 14

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `docker-compose.benchmark.yml` | infrastructure | config | `docker-compose.dev.yml` | exact |
| `deploy/init-benchmark-db.sql` | infrastructure | config | `deploy/init-dev-db.sql` | role-match (adds RO user) |
| `bin/benchmark_db.sh` | infrastructure | batch | `bin/reset_db.sh` + `bin/prod_db_tunnel.sh` | role-match |
| `alembic/versions/<hash>_add_eval_depth_...py` | migration | batch | `alembic/versions/20260424_121249_2af113f4790f_drop_llm_logs_flags.py` | exact |
| `app/models/game.py` (modify) | model | CRUD | existing `game.py` itself | self-reference |
| `app/schemas/normalization.py` (modify) | schema | request-response | existing `normalization.py` itself | self-reference |
| `app/services/normalization.py` (modify) | service | transform | existing `normalization.py` itself | self-reference |
| `app/models/benchmark_selected_user.py` | model | CRUD | `app/models/game.py` | role-match |
| `app/models/benchmark_ingest_checkpoint.py` | model | CRUD | `app/models/game.py` | role-match |
| `scripts/select_benchmark_users.py` | script | streaming/batch | `scripts/reclassify_positions.py` | partial-match |
| `scripts/import_benchmark_users.py` | script | batch | `scripts/reimport_games.py` | role-match |
| `tests/test_benchmark_ingest.py` | test | unit | `tests/test_import_service.py` + `tests/test_chesscom_client.py` | role-match |
| `CLAUDE.md` (modify §Database Access) | docs | config | existing `CLAUDE.md` §Database Access (MCP) | self-reference |
| `~/.claude.json` (manual edit) | config | config | existing `mcpServers` entries in `~/.claude.json` | exact |

---

## Pattern Assignments

### `docker-compose.benchmark.yml` (infrastructure, config)

**Analog:** `docker-compose.dev.yml` (lines 1-29)

**Full analog to copy:**
```yaml
# Local development database only
# Usage: docker compose -f docker-compose.dev.yml up -d
services:
  db:
    image: postgres:18-alpine
    command:
      - "postgres"
      - "-c"
      - "shared_preload_libraries=pg_stat_statements"
      - "-c"
      - "pg_stat_statements.track=all"
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    volumes:
      - devpgdata:/var/lib/postgresql/data
      - ./deploy/init-dev-db.sql:/docker-entrypoint-initdb.d/init-dev-db.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s

volumes:
  devpgdata:
```

**Specific deviations from analog:**
- Comment: `# Benchmark database — isolated from dev/prod`
- Comment usage line: `# Usage: docker compose -f docker-compose.benchmark.yml -p flawchess-benchmark up -d`
- Port: `"5433:5432"` (not `"5432:5432"`)
- Volume name: `benchmarkpgdata` (not `devpgdata`)
- Init SQL mount: `./deploy/init-benchmark-db.sql:/docker-entrypoint-initdb.d/init-benchmark-db.sql`
- `volumes:` block: `benchmarkpgdata:` (not `devpgdata:`)

**Convention reminder:** The `-p flawchess-benchmark` project flag is NOT in the compose file itself — it is always specified on the CLI. The compose file carries no project name.

---

### `deploy/init-benchmark-db.sql` (infrastructure, config)

**Analog:** `deploy/init-dev-db.sql` (lines 1-16)

**Full analog:**
```sql
-- Creates the dev and test databases on first container init
CREATE DATABASE flawchess;
CREATE DATABASE flawchess_test;

-- Create app user matching .env defaults
CREATE USER flawchess WITH PASSWORD 'flawchess';
GRANT ALL PRIVILEGES ON DATABASE flawchess TO flawchess;
GRANT ALL PRIVILEGES ON DATABASE flawchess_test TO flawchess;

-- Allow flawchess user to create objects in public schema
\c flawchess
GRANT ALL ON SCHEMA public TO flawchess;

\c flawchess_test
GRANT ALL ON SCHEMA public TO flawchess;
```

**Specific deviations — what to add beyond the analog:**

The benchmark init SQL creates one database (not two) PLUS a second read-only role for MCP access. The dev analog has no read-only role. Add this block after the app user grants:

```sql
-- Create read-only user for MCP server (flawchess-benchmark-db)
-- Password MUST be replaced before first use: openssl rand -hex 16
-- Do NOT commit the real password — use <PASSWORD> as placeholder in git
CREATE USER flawchess_benchmark_ro WITH PASSWORD '<PASSWORD>';
GRANT CONNECT ON DATABASE flawchess_benchmark TO flawchess_benchmark_ro;
GRANT USAGE ON SCHEMA public TO flawchess_benchmark_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO flawchess_benchmark_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO flawchess_benchmark_ro;
```

**Convention reminder:** The `<PASSWORD>` placeholder is intentional — never commit the real password. Same pattern as the prod read-only user documented in CLAUDE.md.

---

### `bin/benchmark_db.sh` (infrastructure, batch)

**Analog:** `bin/reset_db.sh` (lines 1-25) for structure; `bin/prod_db_tunnel.sh` (lines 13-33) for start/stop subcommand pattern.

**reset_db.sh core structure to copy:**
```bash
#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

PROJECT="flawchess-dev"
COMPOSE_FILE="docker-compose.dev.yml"

echo "Stopping and removing dev database (including data)..."
docker compose -f "$COMPOSE_FILE" -p "$PROJECT" down -v

echo "Starting fresh dev database..."
docker compose -f "$COMPOSE_FILE" -p "$PROJECT" up -d

echo "Waiting for database to be healthy..."
until docker compose -f "$COMPOSE_FILE" -p "$PROJECT" exec db pg_isready -U postgres -q 2>/dev/null; do
  sleep 1
done

echo "Running Alembic migrations..."
uv run alembic upgrade head
```

**prod_db_tunnel.sh subcommand pattern to copy:**
```bash
if [ "${1:-}" = "stop" ]; then
  ...
  exit 0
fi
```

**Specific deviations:**
- `PROJECT="flawchess-benchmark"`, `COMPOSE_FILE="docker-compose.benchmark.yml"`
- Add `BENCHMARK_DB_URL="postgresql+asyncpg://flawchess_benchmark:flawchess_benchmark@localhost:5433/flawchess_benchmark"` constant
- Expose three subcommands via `case "${1:-start}" in start) ... stop) ... reset) ... esac`
- `start`: bring up container, wait for health, run `DATABASE_URL="$BENCHMARK_DB_URL" uv run alembic upgrade head`
- `stop`: `docker compose ... down` (no `-v`)
- `reset`: `docker compose ... down -v`, then same as `start`
- Do NOT seed openings in reset (benchmark DB does not need them)
- Alembic override: `DATABASE_URL="$BENCHMARK_DB_URL" uv run alembic upgrade head` (not bare `uv run alembic upgrade head` — the env var routes to benchmark DB on port 5433)

---

### `alembic/versions/<hash>_add_eval_depth_eval_source_version_to_games.py` (migration, batch)

**Analog:** `alembic/versions/20260424_121249_2af113f4790f_drop_llm_logs_flags.py` (lines 1-34)

**Full analog to copy format from:**
```python
"""drop llm_logs flags

Revision ID: 2af113f4790f
Revises: c72eeee6a61a
Create Date: 2026-04-24 12:12:49.157775+00:00

Drops `flags` column from `llm_logs`. ...
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision: str = "2af113f4790f"
down_revision: str | None = "c72eeee6a61a"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.drop_column("llm_logs", "flags")


def downgrade() -> None:
    op.add_column(
        "llm_logs",
        sa.Column("flags", JSONB(), nullable=False, server_default="[]"),
    )
    op.alter_column("llm_logs", "flags", server_default=None)
```

**Specific deviations:**
- Docstring describes adding `eval_depth` and `eval_source_version`. Include explanation that `eval_depth` will be NULL for all current Lichess API imports (API does not expose depth in the NDJSON game object — `evals=true` only adds PGN annotations). This is the INGEST-06 documentation requirement.
- `down_revision: str | None = "2af113f4790f"` (current head as of research date)
- `upgrade()`: two `op.add_column("games", ...)` calls:
  - `sa.Column("eval_depth", sa.SmallInteger(), nullable=True)`
  - `sa.Column("eval_source_version", sa.String(length=50), nullable=True)`
- `downgrade()`: two `op.drop_column("games", ...)` calls in reverse order

**Convention reminders:**
- Use `sa.SmallInteger()` (not `sa.Integer()`) per CLAUDE.md "use appropriate column types"
- `String(length=50)` is appropriate for a short version tag like `"lichess-pgn"`
- Generate via `uv run alembic revision --autogenerate -m "add eval_depth eval_source_version to games"` — verify autogenerate output matches expectations before adding the docstring

---

### `app/models/game.py` (modify — add two columns)

**Self-reference:** Add after the `black_blunders` column (line 118), following the exact pattern of adjacent nullable SmallInteger columns.

**Pattern to mirror (lines 111-118):**
```python
    white_acpl: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    black_acpl: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    white_inaccuracies: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    black_inaccuracies: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    white_mistakes: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    black_mistakes: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    white_blunders: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    black_blunders: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
```

**New columns to add (after line 118):**
```python
    # Eval metadata — populated for Lichess imports; NULL for chess.com
    # eval_depth is NULL for all current Lichess API imports: the /api/games/user
    # endpoint does not expose depth in the NDJSON JSON object (evals=true only
    # adds [%eval] PGN annotations). If the API adds depth in future, the column
    # is ready to receive it.
    eval_depth: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    eval_source_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
```

**Convention reminders:**
- `SmallInteger` is already imported at line 6 — no new import needed
- `String` is already imported at line 8 — no new import needed
- `Mapped` and `mapped_column` already imported — no new imports needed

---

### `app/schemas/normalization.py` (modify — add two optional fields to NormalizedGame)

**Self-reference:** Add to the `NormalizedGame` model after the existing optional lichess-only fields (after line 60).

**Pattern to mirror (lines 52-60):**
```python
    # lichess-only analysis fields (optional, default None)
    white_acpl: int | None = None
    black_acpl: int | None = None
    white_inaccuracies: int | None = None
    black_inaccuracies: int | None = None
    white_mistakes: int | None = None
    black_mistakes: int | None = None
    white_blunders: int | None = None
    black_blunders: int | None = None
```

**New fields to add:**
```python
    # Eval metadata — populated for Lichess imports; NULL for chess.com
    eval_depth: int | None = None
    eval_source_version: str | None = None
```

**Convention reminder:** Per CLAUDE.md, use `Literal["lichess-pgn"]` rather than bare `str` if the field has a fixed set of values. Since chess.com leaves it NULL and future sources could add new values, `str | None` is acceptable for now. The planner should decide whether to use `Literal["lichess-pgn"] | None` upfront or keep it `str | None`.

---

### `app/services/normalization.py` (modify — set eval_source_version in normalize_lichess_game)

**Self-reference:** `normalize_lichess_game` is at line 288. The modification adds `eval_source_version="lichess-pgn"` unconditionally on the `NormalizedGame(...)` constructor call at the end of the function.

**Pattern to understand — how optional fields are set (nearby existing pattern):**
The function already sets optional lichess-only analysis fields from the `analysis` dict. The new field follows the same "constant for all Lichess games" pattern — no conditional, always set to `"lichess-pgn"` regardless of whether the game has eval annotations.

**Specific deviation:** `eval_depth=None` always (API does not surface depth), `eval_source_version="lichess-pgn"` always for Lichess games. Neither field is parsed from the game dict.

---

### `app/models/benchmark_selected_user.py` (new model, CRUD)

**Analog:** `app/models/game.py` — same Base class, same Mapped column conventions, same UniqueConstraint pattern.

**Imports pattern to copy (game.py lines 1-16):**
```python
from sqlalchemy import (
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
```

**UniqueConstraint pattern to copy (game.py lines 43-47):**
```python
class Game(Base):
    __tablename__ = "games"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "platform", "platform_game_id", name="uq_games_user_platform_game_id"
        ),
    )
```

**id column pattern (game.py line 49):**
```python
    id: Mapped[int] = mapped_column(primary_key=True)
```

**Specific deviations:**
- `__tablename__ = "benchmark_selected_users"`
- `UniqueConstraint("lichess_username", name="uq_benchmark_selected_users_username")`
- Columns: `lichess_username: Mapped[str]`, `rating_bucket: Mapped[int]` (SmallInteger), `tc_bucket: Mapped[str]`, `median_elo: Mapped[int]` (SmallInteger), `eval_game_count: Mapped[int]` (SmallInteger), `selected_at: Mapped[datetime]` (server_default=func.now()), `dump_month: Mapped[str]` (String(7), e.g. "2026-02")
- NO foreign key to `users.id` — these rows are created by the selection script before User stub rows exist
- This table is created via `Base.metadata.create_all(bind=engine)` in the script, NOT via Alembic migration (INFRA-02 compliance: benchmark-only tables must not pollute the canonical migration chain)

**Convention reminders:**
- Use `SmallInteger` for `rating_bucket` (values 800/1200/1600/2000/2400) and `median_elo` (fits in 16-bit signed)
- Use `SmallInteger` for `eval_game_count` (snapshot-month count, rarely exceeds a few hundred)
- `dump_month` is String(7) to hold "YYYY-MM"

---

### `app/models/benchmark_ingest_checkpoint.py` (new model, CRUD)

**Analog:** `app/models/game.py` — same pattern as above.

**Specific deviations from game.py pattern:**
- `__tablename__ = "benchmark_ingest_checkpoints"`
- `UniqueConstraint("lichess_username", name="uq_benchmark_ingest_checkpoints_username")`
- Columns: `lichess_username: Mapped[str]` (String(100)), `status: Mapped[str]` (String(20) — "pending"|"completed"|"skipped"|"failed"), `games_imported: Mapped[int]` (default=0), `skip_reason: Mapped[str | None]` (String(100), nullable), `started_at: Mapped[datetime | None]`, `completed_at: Mapped[datetime | None]`, `benchmark_user_id: Mapped[int | None]` (FK to users.id in benchmark DB)
- `benchmark_user_id` FK pattern to copy from game.py line 51: `mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)` — use `SET NULL` not `CASCADE` since user deletion should not cascade checkpoint deletion
- This table is also created via `Base.metadata.create_all()`, NOT Alembic

**Convention reminder:** Per CLAUDE.md, FK constraints are mandatory even for benchmark-only tables. The `benchmark_user_id` column referencing `users.id` MUST use `ForeignKey("users.id", ondelete="SET NULL")`.

---

### `scripts/select_benchmark_users.py` (script, streaming/batch)

**Analog:** `scripts/reclassify_positions.py` — closest for: module docstring format, `sys.path.insert` pattern, `_log()` timestamped logger, `parse_args()` argparse structure, `main()` with Sentry init, `asyncio.run(main())` at bottom.

**sys.path + Sentry init pattern to copy (reclassify_positions.py lines 29-33, 195-196):**
```python
# Ensure project root is on sys.path so `app.*` imports work when running as a script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sentry_sdk
...
    if settings.SENTRY_DSN:
        sentry_sdk.init(dsn=settings.SENTRY_DSN, environment=settings.ENVIRONMENT)
```

**`_log()` timestamped logger pattern (reclassify_positions.py lines 57-60):**
```python
def _log(msg: str = "") -> None:
    """Print a message prefixed with a UTC timestamp (second precision)."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")
```

**argparse pattern (reclassify_positions.py lines 63-87):**
```python
def parse_args() -> argparse.Namespace:
    """Parse and validate CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Backfill position classification for existing game_positions rows."
    )
    ...
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Skip confirmation prompt and proceed immediately.",
    )
    return parser.parse_args()
```

**asyncio.run entry point (reclassify_positions.py lines 295-296):**
```python
if __name__ == "__main__":
    asyncio.run(main())
```

**Specific deviations:**
- `parse_args()` needs `--dump-path` (path to `.pgn.zst` file), `--per-cell` (int, default 500), `--eval-threshold` (int, default 5 per D-12), `--output-db-url` (benchmark DB URL)
- The script does NOT use `async_session_maker` from `app.core.database` — it creates its own engine pointing at the benchmark DB via `--output-db-url` arg (or `BENCHMARK_DATABASE_URL` env var)
- Core logic: streaming zstd decompress + header-only PGN parse (no python-chess game tree) + bucketing algorithm + `Base.metadata.create_all()` + persist to `benchmark_selected_users`
- No confirmation prompt (non-destructive operation — only inserts to benchmark DB)
- Progress logging every 1M games processed
- Note: `zstandard` package must be added to `pyproject.toml` as a dev dependency (or use `subprocess` + `zstdcat` fallback)

---

### `scripts/import_benchmark_users.py` (script, batch)

**Analog:** `scripts/reimport_games.py` — closest for: full script structure, Sentry pattern, `_log()`, argparse, per-user loop with outer error boundary.

**Full script structure to mirror (reimport_games.py):**

Header docstring format (lines 1-22):
```python
"""Re-import games for user(s) to populate engine analysis data.
...
Usage (local dev):
    uv run python scripts/reimport_games.py --user-id 42
    uv run python scripts/reimport_games.py --all --platform lichess --yes
"""
```

Imports block (lines 24-46):
```python
import argparse
import asyncio
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sentry_sdk
from sqlalchemy import select

from app.core.config import settings
from app.core.database import async_session_maker
from app.models.user import User
from app.services.import_service import create_job, get_job, run_import
```

Sentry capture at outer-per-user boundary (lines 273-276):
```python
        except Exception as e:
            sentry_sdk.capture_exception(e)
            _log(f"  ERROR: User {user_id} failed: {e}")
            total_failed += 1
```

`create_job` + `run_import` invocation (lines 200-208):
```python
            job_id = create_job(user_id=user_id, platform=platform, username=username)
            await run_import(job_id)

            job_state = get_job(job_id)
            if job_state is not None:
                if job_state.status == "completed":
                    total_imported += job_state.games_imported
```

**Specific deviations:**
- `parse_args()` needs `--per-cell N` (int), `--db-url` for benchmark DB, `--dry-run` flag
- No `--all` / `--user-id` mutually exclusive group — operates on the benchmark DB's `benchmark_selected_users` table
- On startup: connect to benchmark DB, count completed users per cell, compute deficit per cell
- `create_stub_user()` helper (async, checks for existing `lichess_username` row before inserting)
- Per-user: insert `benchmark_ingest_checkpoints` row with `status="pending"`, call `run_import`, update checkpoint to `"completed"` or `"skipped"` or `"failed"`
- Hard-skip for users with > 20k window-bounded games (D-14): update checkpoint to `"skipped"`, `skip_reason="over_20k_games"`, log username + count
- `since_ms` = `(selection_month_end - 36_months).timestamp() * 1000` (D-13) — pass as kwarg to `run_import` or `create_job`
- Sentry tagging: `sentry_sdk.set_context("benchmark_ingest", {"username": username, "cell": f"{rating_bucket}/{tc_bucket}"})` before each capture (per CLAUDE.md §Error Handling)
- Centipawn convention docblock in script header (INGEST-06 documentation requirement)
- Do NOT use `asyncio.gather` for parallel imports — sequential per-user per CLAUDE.md Critical Constraints

**`_BATCH_SIZE` note:** `import_service._BATCH_SIZE` is currently **28** in the codebase (not 10 as stated in older STATE.md). The benchmark scripts should NOT hardcode a batch size — they call `run_import()` which uses `import_service._BATCH_SIZE` internally.

---

### `tests/test_benchmark_ingest.py` (test, unit)

**Analog:** `tests/test_import_service.py` (lines 1-20) — docstring format, import style, class-based test grouping. Also `tests/test_chesscom_client.py` — helper factory functions (`_make_game()`, `_make_response()`).

**Module docstring + imports pattern to copy (test_import_service.py lines 1-18):**
```python
"""Tests for the import service.

Focuses on orchestration logic: job lifecycle, incremental sync, hash computation,
and error handling. All external dependencies are mocked.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import app.services.import_service as import_service
from app.services.import_service import (
    create_job,
    run_import,
)
```

**Helper factory pattern (test_chesscom_client.py lines 22-52):**
```python
def _make_game(
    uuid: str = "game-uuid-1",
    ...
) -> dict:
    """Build a minimal chess.com game dict."""
    return {
        "uuid": uuid,
        ...
    }
```

**test_import_service.py autouse fixture pattern (lines 57-62):**
```python
@pytest.fixture(autouse=True)
def clear_jobs():
    """Clear the in-memory job registry before each test to prevent cross-test pollution."""
    import_service._jobs.clear()
    yield
    import_service._jobs.clear()
```

**Specific test functions to implement per VALIDATION.md:**
- `test_scan_dump_parser` — feed synthetic PGN header text to `scan_dump_for_players` logic, verify field extraction and `has_eval` flag detection. No real `.zst` file needed — mock the decompressed text stream.
- `test_player_bucketing` — feed a list of synthetic player stats dicts, verify median Elo + modal TC bucketing assigns correct (rating_bucket, tc_bucket) cell. Pure Python, no DB or network.
- `test_eval_columns` — verify that `normalize_lichess_game()` sets `eval_source_version="lichess-pgn"` on output. Mock lichess game dict, call the function, assert field value.
- `test_centipawn_convention` — pure doctest/assertion verifying that a hardcoded `[%eval 2.35]` annotation parses to `eval_cp=235` via python-chess `node.eval()`. No mocking needed.
- `test_stub_user_invariants` — mock an `AsyncSession`, call `create_stub_user()`, assert `is_active=False`, `hashed_password="!BENCHMARK_NO_AUTH"`, email format.
- `test_outlier_skip` — mock `run_import` to simulate a user with >20k games, assert checkpoint is written with `status="skipped"`, `skip_reason="over_20k_games"`.

**Convention reminder:** All async tests use `asyncio_mode = "auto"` (set in `pyproject.toml`). These tests are pure unit tests — they do NOT require a running database or network. Use `unittest.mock.AsyncMock` / `MagicMock` for all external dependencies. The test file does NOT need a `conftest.py` session fixture (`test_engine`, etc.) since no DB writes are tested here.

---

### `CLAUDE.md` (modify §Database Access (MCP))

**Self-reference:** The existing §Database Access (MCP) section has two entries as the pattern.

**Existing entries to copy format from:**
```markdown
- **`flawchess-db`** — local dev database (Docker on `localhost:5432`). Requires dev DB running: `docker compose -f docker-compose.dev.yml -p flawchess-dev up -d`
- **`flawchess-prod-db`** — production database via read-only user. Requires SSH tunnel: `bin/prod_db_tunnel.sh` (forwards `localhost:15432` → prod DB on port 5432). Stop with `bin/prod_db_tunnel.sh stop`.
```

**New entry to append:**
```markdown
- **`flawchess-benchmark-db`** — benchmark database (Docker on `localhost:5433`). Requires benchmark DB running: `docker compose -f docker-compose.benchmark.yml -p flawchess-benchmark up -d` (or `bin/benchmark_db.sh start`). Read-only password stored locally only (not committed to git).
```

---

### `~/.claude.json` (manual user-level edit)

**Analog:** Existing `flawchess-db` and `flawchess-prod-db` entries (verified in RESEARCH.md §4).

**Existing entries to copy format from:**
```json
"flawchess-db": {
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-postgres", "postgresql://flawchess:flawchess@localhost:5432/flawchess"],
  "env": {}
},
"flawchess-prod-db": {
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-postgres", "postgresql://flawchess_ro:***@localhost:15432/flawchess"],
  "env": {}
}
```

**New entry:**
```json
"flawchess-benchmark-db": {
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-postgres", "postgresql://flawchess_benchmark_ro:<PASSWORD>@localhost:5433/flawchess_benchmark"],
  "env": {}
}
```

**Convention reminder:** Replace `<PASSWORD>` with the value set in `deploy/init-benchmark-db.sql`. This edit is manual (the executor cannot write `~/.claude.json` directly — it requires a user-level edit outside the project). Document in the plan as a manual step with exact JSON path: `projects["/home/aimfeld/Projects/Python/flawchess"]["mcpServers"]`.

---

## Shared Patterns

### Timestamped Logger (`_log`)
**Source:** `scripts/reimport_games.py` lines 50-53, `scripts/reclassify_positions.py` lines 57-60
**Apply to:** `scripts/select_benchmark_users.py`, `scripts/import_benchmark_users.py`
```python
def _log(msg: str = "") -> None:
    """Print a message prefixed with a UTC timestamp (second precision)."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")
```

### Sentry Init in Scripts
**Source:** `scripts/reimport_games.py` lines 225-226, `scripts/reclassify_positions.py` lines 195-196
**Apply to:** `scripts/select_benchmark_users.py`, `scripts/import_benchmark_users.py`
```python
    if settings.SENTRY_DSN:
        sentry_sdk.init(dsn=settings.SENTRY_DSN, environment=settings.ENVIRONMENT)
```

### Sentry Outer Capture (Per-User Boundary)
**Source:** `scripts/reimport_games.py` lines 273-276
**Apply to:** `scripts/import_benchmark_users.py` outer per-user loop
```python
        except Exception as e:
            sentry_sdk.capture_exception(e)
            _log(f"  ERROR: User {user_id} failed: {e}")
            total_failed += 1
```
With benchmark-specific context tagging (CLAUDE.md §Error Handling):
```python
        except Exception as exc:
            sentry_sdk.set_context("benchmark_ingest", {
                "username": username,
                "cell": f"{rating_bucket}/{tc_bucket}",
            })
            sentry_sdk.capture_exception(exc)
```

### sys.path Bootstrap for Scripts
**Source:** `scripts/reimport_games.py` lines 31-32, `scripts/reclassify_positions.py` lines 29-30
**Apply to:** All new scripts in `scripts/`
```python
# Ensure project root is on sys.path so `app.*` imports work when running as a script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
```

### Confirmation Prompt with `--yes` Flag
**Source:** `scripts/reimport_games.py` lines 249-256, `scripts/reclassify_positions.py` lines 214-220
**Apply to:** `scripts/import_benchmark_users.py` (for destructive operations; not needed for `select_benchmark_users.py` which is non-destructive)
```python
    if not args.yes:
        response = input(
            f"This will ... Proceed? [y/N] "
        )
        if response.strip().lower() not in ("y", "yes"):
            _log("Aborted.")
            return
```

### SQLAlchemy Async Model Base
**Source:** `app/models/base.py` lines 1-11, imported by all models
**Apply to:** `app/models/benchmark_selected_user.py`, `app/models/benchmark_ingest_checkpoint.py`
```python
from app.models.base import Base
```
Both new benchmark model files inherit from `Base` exactly as all other models do.

### FK with ondelete Policy
**Source:** `app/models/game.py` line 51
**Apply to:** `benchmark_ingest_checkpoint.py` `benchmark_user_id` column
```python
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
```
For the checkpoint model, use `ondelete="SET NULL"` since a deleted stub user should not cascade-delete the checkpoint record.

---

## Discrepancy Flags for Planner

### `_BATCH_SIZE` discrepancy (PLANNING INPUT REQUIRED)
RESEARCH.md §15 Q6 and the codebase (`app/services/import_service.py` line 37) confirm `_BATCH_SIZE = 28`. CLAUDE.md §Production Server says "10 games" (outdated). STATE.md says "10 games" (outdated). The planner must document that **28 is the current value** and benchmark ingest does not override it — `run_import()` uses the service-internal constant.

### Rating bucket width reconciliation (PLANNING INPUT REQUIRED)
RESEARCH.md §15 Q1 flags a conflict: REQUIREMENTS.md uses 400-wide buckets (800-1200-1600-2000-2400+); the existing benchmarks skill uses 500-wide buckets (`floor(elo/500)*500`). Phase 69 selection uses REQUIREMENTS.md 400-wide. The planner should resolve before writing the plan. Recommendation in RESEARCH.md: use 400-wide for INGEST-02 selection, accept that Phase 73 analytics will bucket at query time using whatever width the benchmarks skill uses.

### `zstandard` dependency (PLANNING INPUT REQUIRED)
The streaming dump scanner needs `zstandard` (Python bindings for Zstd). RESEARCH.md §15 Q2 proposes three options: (a) add to `[dependency-groups] dev` in `pyproject.toml`, (b) conditional import with graceful error, (c) `subprocess` + `zstdcat` CLI fallback. The planner must decide and record in the plan.

### Benchmark-only tables via `create_all` vs Alembic (PLANNING INPUT REQUIRED)
RESEARCH.md §15 Q3 recommends creating `benchmark_selected_users` and `benchmark_ingest_checkpoints` via `Base.metadata.create_all()` in the scripts, not via Alembic (to avoid polluting prod/dev/test schemas per INFRA-02). The planner must confirm this approach.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `scripts/select_benchmark_users.py` (streaming dump core) | script | streaming | No existing script scans a compressed dump file. The zstd decompression + PGN header-only streaming loop is novel. The script structure mirrors `reclassify_positions.py` but the core scan logic has no analog. Use RESEARCH.md §2 code skeleton as the reference. |

---

## Metadata

**Analog search scope:** `app/models/`, `app/schemas/`, `app/services/`, `scripts/`, `tests/`, `alembic/versions/`, `bin/`, `deploy/`, `docker-compose.dev.yml`
**Files read:** 18 source files
**Pattern extraction date:** 2026-04-25

---

## PATTERN MAPPING COMPLETE
