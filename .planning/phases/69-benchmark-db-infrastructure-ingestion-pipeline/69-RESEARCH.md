# Phase 69: Benchmark DB Infrastructure & Ingestion Pipeline - Research

**Researched:** 2026-04-25
**Domain:** PostgreSQL infrastructure, Lichess PGN dumps, ingestion pipeline, Alembic migrations
**Confidence:** HIGH (infrastructure patterns from codebase), MEDIUM (Lichess API eval_depth surface)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** No cheat-filtering in Phase 69. Document residual upward bias in 2000+ buckets in the script header and Phase 70/73 reports. Phase 70 gate (Pawn/Rook/Minor cells) is the safety net.
- **D-02:** Ingest selection scan uses one recent Lichess monthly dump. Expand to two months if cells are under-quota. Do not pre-emptively scan multiple dumps.
- **D-03:** Delete the selection-scan dump after ingest completes successfully (row counts verified).
- **D-04 (supersedes random-game framing):** Sample unit is distinct players. Per (rating x TC) cell, target ~500 distinct players (tunable via D-15). Selection bucket = player's median Elo + modal TC across snapshot-month games.
- **D-05:** Per-game player-side bucketing for analytics preserved. White's stats bucket by WhiteElo, Black's by BlackElo. Selection is at user level; bucketing for analytics is per-game-side.
- **D-06:** Existing prod `games` rows leave `eval_depth` + `eval_source_version` as NULL forever. No backfill.
- **D-07:** For Lichess imports, populate `eval_depth` from API per-game where surfaced; fallback NULL. `eval_source_version` = constant string per source (e.g., `"lichess-pgn"`). Verify actual API surface during Phase 69 implementation.
- **D-08:** No `is_benchmark` flag on User table. Benchmark DB instance isolation handles separation.
- **D-09:** No per-user game cap as primary constraint. Use time window (D-13) and outlier hard-skip (D-14).
- **D-10:** Selection assigns user to one cell at selection time; full imported history stored regardless of within-history bucket drift. Cohort drift accepted.
- **D-11:** Per selected user, ingest full game history (eval-bearing AND non-eval) within time window. Eval columns NULL for non-eval games.
- **D-12:** Selection threshold: pick users with >= K eval-bearing games in snapshot month (start K=5, planning-time tunable).
- **D-13:** Per-user history bounded via Lichess API `since=` set to 36 months back from selection-month dump end.
- **D-14:** Hard skip (not warning) on any single user whose window-bounded ingest would exceed 20k games. Log username + count.
- **D-15 (revised 2026-04-25):** Staged via `--per-cell N` flag. Smoke=3, Interim milestone=100 (Phase 69 completion target), Decision gate after 100/cell run.
- **D-15a:** Selection-scan output persisted as username list per cell. Orchestrator counts already-imported users per cell on startup, draws `N - current` additional usernames. Per-game unique constraint makes already-imported games no-op. Per-user outer-loop checkpoint records "user X completed."
- **U1 approach locked:** Reuse existing `app/services/import_service.run_import(platform=lichess, username=...)` per selected user.

### Claude's Discretion

- Exact pre-filter tool for dump selection scan (zgrep, ripgrep, pure Python with zstd)
- Centipawn convention verification format (script self-test vs one-off validation note)
- MCP server local port, Postgres user/password setup, exact `docker-compose.benchmark.yml` structure
- Stub User row schema in benchmark DB (sentinel email, password hash placeholder, is_active value)
- Ingestion outer-loop checkpoint structure (selected usernames + per-user state)
- Selection-scan player-bucketing algorithm details (modal TC handling)

### Deferred Ideas (OUT OF SCOPE)

- Bans-list cross-reference for cheat filtering (v1.13+)
- Hybrid two-tier sampling
- CPL-based outlier rejection
- Phase 69 split (preserve as `/gsd-insert-phase` option if needed)
- Refresh cadence policy (Phase 73)
- Multi-month dump scan ingestion (U2)
- Backfill of `eval_depth`/`eval_source_version` for prod games
- chess.com population baselines (v1.13+)
- `is_benchmark` User flag
- Per-user game cap
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INFRA-01 | Separate `flawchess-benchmark` PostgreSQL 18 instance via `docker-compose.benchmark.yml`, isolated from dev/prod | Section 5: docker-compose.benchmark.yml template provided |
| INFRA-02 | Benchmark DB uses same canonical schema + Alembic migrations as dev/prod/test; `[%eval` populates existing `eval_cp`/`eval_mate` columns | Section 6: migration approach confirmed; Section 3: eval pipeline already handles this |
| INFRA-03 | Read-only MCP server `flawchess-benchmark-db` configured and documented in CLAUDE.md | Section 4: exact JSON shape and port documented |
| INGEST-01 | Bulk ingestion with eval-presence pre-filter (zgrep or equivalent) before python-chess parsing | Section 2: streaming pre-filter strategy with code skeleton |
| INGEST-02 | Stratified subsampling on (rating_bucket x TC); 5 buckets x 4 TCs = 20 cells | Section 9: bucketing algorithm with concrete grid |
| INGEST-03 | Player-side bucketing: WhiteElo and BlackElo determine each side's bucket independently | Section 9: confirmed from benchmarks skill SQL pattern |
| INGEST-04 | Resumable ingest: checkpoint table, idempotent inserts, SIGINT-safe flush | Section 7: checkpoint schema designed; Section 11: verification strategy |
| INGEST-05 | Storage target 50-100 GB for v1.12 MVP | Section 10: verified 54 GB at 2000 users x 1000 avg games |
| INGEST-06 | Add `eval_depth` (SmallInteger nullable) + `eval_source_version` (String nullable) to `games`; centipawn convention verified | Section 3: API surface research; Section 6: migration sketch |
</phase_requirements>

---

## 1. Executive Summary

- **Infrastructure is a straight copy of docker-compose.dev.yml** with three changes: project name `flawchess-benchmark`, port 5433, volume `benchmarkpgdata`. The init SQL needs one new file for the benchmark database + read-only user. MCP registration follows the exact same `@modelcontextprotocol/server-postgres` pattern already used for `flawchess-db` and `flawchess-prod-db` — stored in `~/.claude.json` under the project key.

- **The ingestion pipeline already exists.** `app/services/import_service.run_import` + `lichess_client.fetch_lichess_games` handles everything: streaming NDJSON, `since_ms` parameter, `evals=true`, retry logic, Sentry at outer boundary. The orchestrator script (`scripts/import_benchmark_users.py`) only needs to: (a) create stub User rows, (b) call `run_import` per username, (c) track outer-loop checkpoint state in the benchmark DB.

- **eval_depth is NOT surfaced per-game in the Lichess `/api/games/user` NDJSON response.** The `evals=true` parameter adds `[%eval ...]` annotations to the PGN text (which `zobrist.py` already parses via `node.eval()`), but depth is not included in the game JSON. `eval_depth` will be NULL for all Lichess API-imported games under current infrastructure. `eval_source_version = "lichess-pgn"` is appropriate as a constant. Document explicitly per D-07.

- **Storage at 100/cell (2000 users) is well within INGEST-05 target.** Prod row sizes: 3,106 bytes/game row (with indexes), 350 bytes/game_position row (with indexes), avg 68.3 positions/game. At 2000 users x 1000 avg games: ~54 GB. Even at 2000 users x 2000 avg games: ~108 GB. INGEST-05's 50-100 GB target holds comfortably for the Phase 69 completion milestone.

- **The Alembic migration is straightforward.** Two nullable columns added to `games`. Runs uniformly against dev/prod/test/benchmark because all four environments share the same migration chain. `NormalizedGame` schema and `game_repository.bulk_insert_games` both need updating to accept the new fields.

---

## 2. Lichess Dump Format and Pre-Filter Strategy

### Format

Lichess monthly standard rated dumps are at:
```
https://database.lichess.org/standard/lichess_db_standard_rated_YYYY-MM.pgn.zst
```

- **Compression:** Zstandard (`.pgn.zst`). Compressed size: ~20 GB/month. Uncompressed: ~140 GB (7x expansion). [VERIFIED: database.lichess.org]
- **Game volume:** ~20-30 million rated standard games per recent month. [ASSUMED - exact 2025/2026 monthly count not verified; order of magnitude from public discussions]
- **Eval coverage:** ~6% of games in standard dumps have `[%eval` annotations (2026-04-07 validation report measured 14.7% for the FlawChess user base, but that's a self-selected population of Lichess users who have requested analysis — the full dump has lower coverage). [CITED: reports/endgame-conversion-recovery-analysis.md]
- **Eval format:** `[%eval 2.35]` = 235 centipawns advantage to White; `[%eval -0.40]` = 40 centipawns advantage to Black; `[%eval #4]` = White mates in 4; `[%eval #-2]` = Black mates in 2. Always signed from White's POV, in pawn units (1.0 = 100 centipawns). [VERIFIED: WebSearch, lichess forum + database documentation]

### Pre-Filter Strategy

The dump scan for **player selection** (not the per-user import) needs to extract per-game: `White`, `Black`, `WhiteElo`, `BlackElo`, `TimeControl`, `Variant`, and `has_[%eval]` — without python-chess game-tree parsing.

**Recommended approach: pure Python streaming with `zstandard` library.**

Rationale:
- `zgrep` cannot read `.zst` (only `.gz`). Using `zstdcat | grep` works but loses line context for multi-line PGN headers.
- `ripgrep` (`rg`) with `--search-zip` does not support zstandard natively.
- Pure Python with `zstandard` (third-party, `pip install zstandard`) gives a streaming decompressor at C-extension speed (well over 1 GB/s decompression throughput), with full control over line accumulation. [VERIFIED: python-zstandard docs, zstd-benchmark GitHub]
- A PGN game in the dump is a block of header lines followed by a moves line, separated by blank lines. Header fields are accessible as text without chess parsing.

**Performance:** On dev hardware with NVMe, expect 30-50 MB/s net throughput (IO-bound, decompression faster than disk read). A 20 GB compressed file scans in ~7-11 minutes. [ASSUMED - based on zstd decompression speed and typical NVMe read speeds]

**Code skeleton for `scripts/select_benchmark_users.py`:**

```python
# Source: design based on python-chess PGN iteration + zstandard streaming
import zstandard as zstd
import io

def scan_dump_for_players(dump_path: str) -> Iterator[dict]:
    """Stream the dump and yield per-game player records without python-chess parsing."""
    dctx = zstd.ZstdDecompressor()
    with open(dump_path, "rb") as fh:
        stream = dctx.stream_reader(fh)
        text_stream = io.TextIOWrapper(stream, encoding="utf-8", errors="replace")
        
        game_headers: dict[str, str] = {}
        has_eval = False
        
        for line in text_stream:
            line = line.rstrip("\n")
            
            if line.startswith("["):
                # PGN header line: [Key "Value"]
                # Extract key-value without regex for speed
                bracket_end = line.index('"')
                key = line[1:bracket_end].strip()
                value = line[bracket_end+1:line.rindex('"')]
                game_headers[key] = value
                
            elif line.startswith("1.") or (line and not line.startswith("[")):
                # Moves line — check for eval presence
                if "%eval" in line:
                    has_eval = True
                    
            elif line == "" and game_headers:
                # Blank line = game boundary; emit if we have headers
                if game_headers.get("Variant", "Standard") == "Standard":
                    yield {
                        "white": game_headers.get("White", ""),
                        "black": game_headers.get("Black", ""),
                        "white_elo": _parse_elo(game_headers.get("WhiteElo", "?")),
                        "black_elo": _parse_elo(game_headers.get("BlackElo", "?")),
                        "time_control": game_headers.get("TimeControl", ""),
                        "has_eval": has_eval,
                    }
                game_headers = {}
                has_eval = False

def _parse_elo(s: str) -> int | None:
    try:
        return int(s)
    except (ValueError, TypeError):
        return None
```

**Required new dependency:** `zstandard` (add to `pyproject.toml` under a `[benchmark]` optional group or directly in dependencies if the project accepts it).

**Alternative if zstandard is not added as a project dep:** Use `subprocess` to pipe `zstdcat dump.pgn.zst` and read stdout — same result, no new Python dep, but less portable.

---

## 3. Lichess API for Eval Metadata

### (a) Is `since_ms` already wired through?

**Yes, verified.** `app/services/lichess_client.py` lines 97-98:
```python
if since_ms is not None:
    params["since"] = str(since_ms)
```
And `import_service._make_game_iterator` (lines 347-349) computes `since_ms` from `previous_job.last_synced_at`. For the benchmark orchestrator, `since_ms` is computed as `(selection_month_end - 36_months).timestamp() * 1000`. [VERIFIED: app/services/lichess_client.py, app/services/import_service.py]

### (b) Does the Lichess API surface eval depth per-game?

**Not in the NDJSON game object.** The `evals=true` parameter adds `[%eval ...]` PGN annotations to the `pgn` string field inside the NDJSON game object. The eval depth is **not exposed** as a separate JSON field in the game response. The game JSON includes a `players.{color}.analysis` object with `acpl`, `inaccuracy`, `mistake`, `blunder`, `accuracy` — but no `eval_depth`. [VERIFIED: app/services/normalization.py lines 401-437, which exhaustively maps the `analysis` object; depth is not there]

Consequence for D-07: `eval_depth` will be NULL for all Lichess API-imported games. `eval_source_version` should be set to `"lichess-pgn"` as a constant string whenever a Lichess game is imported (regardless of whether that specific game has evals). This is the correct implementation of D-07's "fallback NULL" path.

**Implementation note:** The Lichess API documentation lists `analysed` as a filter parameter — this filters to only return games that Lichess has analyzed. The `evals=true` parameter is separate and adds the annotations to games that already have them. Neither surfaces depth. [CITED: github.com/lichess-org/api — api-games-user-username.yaml]

### (c) Does `evals=true` require other flags?

No. The existing `lichess_client.py` already passes `evals=True` (line 93). No additional flags needed for benchmark ingestion. [VERIFIED: app/services/lichess_client.py]

### (d) Is there NDJSON streaming support?

Yes, already used. `lichess_client.fetch_lichess_games` streams NDJSON line-by-line via `httpx.AsyncClient.stream`. [VERIFIED: app/services/lichess_client.py]

### Centipawn Convention Verification

The Lichess `[%eval]` format uses **pawn units** (not centipawns) in the PGN text, always **signed from White's POV**:
- `[%eval 2.35]` = White is up 2.35 pawns = +235 centipawns
- `[%eval -0.50]` = Black is up 0.5 pawns = -50 centipawns from White's POV
- `[%eval #4]` = White mates in 4
- `[%eval #-2]` = Black mates in 2 (shown as mate_in = -2)
[VERIFIED: lichess forum + WebSearch confirmation of pawn-unit format signed from White POV]

The existing `zobrist.py` lines 170-174:
```python
pov = node.eval()  # python-chess returns PovScore
if pov is not None:
    w = pov.white()              # convert to White's POV
    eval_cp = w.score(mate_score=None)   # centipawns (already multiplied by 100 by python-chess)
    eval_mate = w.mate()
```
`python-chess` `node.eval()` parses `[%eval 2.35]` → `PovScore` with `score=235` centipawns from White's POV. `w.score(mate_score=None)` returns `235`. This is correct: `game_positions.eval_cp` stores **signed centipawns from White's POV** (positive = White advantage). [VERIFIED: app/services/zobrist.py; python-chess score() API multiplies pawn units by 100]

**Verification recommendation:** A one-shot doctest in `scripts/import_benchmark_users.py` header:

```python
# Centipawn convention verification (INGEST-06 requirement):
# Lichess [%eval 2.35] → python-chess PovScore → white().score() = 235 (centipawns, White POV)
# Stored in game_positions.eval_cp as signed integer (positive = White advantage)
# Verified against: https://lichess.org/{known_game_id} with known eval annotation
# Example: game with [%eval 1.20] at move 15 → eval_cp = 120 in game_positions
```

---

## 4. MCP Server Registration

### Current Configuration

MCP servers are registered in `~/.claude.json` under `projects["/home/aimfeld/Projects/Python/flawchess"]["mcpServers"]`. [VERIFIED: ~/.claude.json contents confirmed]

The existing two servers use `@modelcontextprotocol/server-postgres` via `npx`:

```json
{
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
}
```

### Third Entry for `flawchess-benchmark-db`

The benchmark DB will use port **5433** (dev is 5432, prod tunnel is 15432). Read-only user pattern mirrors `flawchess-prod-db`.

**JSON to add** to `~/.claude.json` under `projects[".../flawchess"]["mcpServers"]`:

```json
"flawchess-benchmark-db": {
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-postgres", "postgresql://flawchess_benchmark_ro:<PASSWORD>@localhost:5433/flawchess_benchmark"],
  "env": {}
}
```

The read-only password is chosen at setup time (suggest generating a random hex string). It must appear in:
1. `deploy/init-benchmark-db.sql` (as the `CREATE USER ... WITH PASSWORD` value)
2. `~/.claude.json` above (the MCP connection string)
3. Not committed to git (document in `CLAUDE.md` that the password is local-only, just like prod)

### CLAUDE.md Update

Per INFRA-03, after setup add to `CLAUDE.md` §Database Access (MCP):
```
- **`flawchess-benchmark-db`** — benchmark database (Docker on `localhost:5433`). Requires benchmark DB running: `docker compose -f docker-compose.benchmark.yml -p flawchess-benchmark up -d`
```

---

## 5. docker-compose.benchmark.yml + bin Script

### Proposed `docker-compose.benchmark.yml`

```yaml
# Benchmark database — isolated from dev/prod
# Usage: docker compose -f docker-compose.benchmark.yml -p flawchess-benchmark up -d
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
      - "5433:5432"
    volumes:
      - benchmarkpgdata:/var/lib/postgresql/data
      - ./deploy/init-benchmark-db.sql:/docker-entrypoint-initdb.d/init-benchmark-db.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s

volumes:
  benchmarkpgdata:
```

Key differences from `docker-compose.dev.yml`: project name `flawchess-benchmark`, port `5433:5432`, volume `benchmarkpgdata`, init SQL `init-benchmark-db.sql`.

### Proposed `deploy/init-benchmark-db.sql`

```sql
-- Creates the benchmark database on first container init
CREATE DATABASE flawchess_benchmark;

-- Create app user for Alembic migrations and ingestion scripts
CREATE USER flawchess_benchmark WITH PASSWORD 'flawchess_benchmark';
GRANT ALL PRIVILEGES ON DATABASE flawchess_benchmark TO flawchess_benchmark;

\c flawchess_benchmark
GRANT ALL ON SCHEMA public TO flawchess_benchmark;

-- Create read-only user for MCP server access
-- Password is set separately (not committed to git)
-- Replace <PASSWORD> with: openssl rand -hex 16
CREATE USER flawchess_benchmark_ro WITH PASSWORD '<PASSWORD>';
GRANT CONNECT ON DATABASE flawchess_benchmark TO flawchess_benchmark_ro;
GRANT USAGE ON SCHEMA public TO flawchess_benchmark_ro;
-- Grant SELECT on all current and future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO flawchess_benchmark_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO flawchess_benchmark_ro;
```

Note: The `<PASSWORD>` placeholder must be replaced before first use. The password is not committed. This mirrors the prod read-only user pattern.

### Proposed `bin/benchmark_db.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

PROJECT="flawchess-benchmark"
COMPOSE_FILE="docker-compose.benchmark.yml"
BENCHMARK_DB_URL="postgresql+asyncpg://flawchess_benchmark:flawchess_benchmark@localhost:5433/flawchess_benchmark"

case "${1:-start}" in
  start)
    echo "Starting benchmark database..."
    docker compose -f "$COMPOSE_FILE" -p "$PROJECT" up -d
    echo "Waiting for database to be healthy..."
    until docker compose -f "$COMPOSE_FILE" -p "$PROJECT" exec db pg_isready -U postgres -q 2>/dev/null; do
      sleep 1
    done
    echo "Running Alembic migrations..."
    DATABASE_URL="$BENCHMARK_DB_URL" uv run alembic upgrade head
    echo "Done. Benchmark database is ready on port 5433."
    ;;
  stop)
    echo "Stopping benchmark database..."
    docker compose -f "$COMPOSE_FILE" -p "$PROJECT" down
    ;;
  reset)
    echo "Resetting benchmark database (ALL DATA WILL BE LOST)..."
    docker compose -f "$COMPOSE_FILE" -p "$PROJECT" down -v
    docker compose -f "$COMPOSE_FILE" -p "$PROJECT" up -d
    until docker compose -f "$COMPOSE_FILE" -p "$PROJECT" exec db pg_isready -U postgres -q 2>/dev/null; do
      sleep 1
    done
    DATABASE_URL="$BENCHMARK_DB_URL" uv run alembic upgrade head
    echo "Done. Benchmark database reset."
    ;;
  *)
    echo "Usage: $0 [start|stop|reset]"
    exit 1
    ;;
esac
```

**Alembic note:** The benchmark DB uses the SAME Alembic migration chain as dev/prod. The `DATABASE_URL` env var override routes Alembic to the benchmark DB. `alembic/env.py` already reads from `settings.DATABASE_URL`, so overriding the env var is sufficient. [VERIFIED: alembic/env.py line 23]

---

## 6. Alembic Migration for eval_depth + eval_source_version

### Latest Migration (baseline)

Latest migration: `20260424_121249_2af113f4790f_drop_llm_logs_flags.py` [VERIFIED: alembic/versions/ directory listing]

### Migration Format (from existing files)

The project uses date-prefixed migration files with a slug. Format: `YYYYMMDD_HHMMSS_{revid}_{slug}.py`. The `--autogenerate` workflow is used. [VERIFIED: alembic/versions/ file names]

### Autogenerate Command

```bash
uv run alembic revision --autogenerate -m "add eval_depth eval_source_version to games"
```

### Expected Migration Content

```python
"""add eval_depth eval_source_version to games

Revision ID: <auto>
Revises: 2af113f4790f
Create Date: <auto>

Adds eval_depth (SmallInteger, nullable) and eval_source_version (String, nullable)
to the canonical games table per INGEST-06. Applied uniformly to dev/prod/test/benchmark.
- eval_depth: populated from Lichess API when depth metadata is surfaced; NULL otherwise.
  As of research date, the Lichess /api/games/user endpoint does NOT surface depth per-game
  in JSON — eval_depth will be NULL for all Lichess API imports. If the API adds this in
  future, the column is ready.
- eval_source_version: constant string per source ("lichess-pgn" for all Lichess imports,
  NULL for chess.com). Enables downstream queries to filter or annotate by eval origin.
"""

from alembic import op
import sqlalchemy as sa


revision: str = "<auto>"
down_revision: str | None = "2af113f4790f"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column("games", sa.Column("eval_depth", sa.SmallInteger(), nullable=True))
    op.add_column("games", sa.Column("eval_source_version", sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column("games", "eval_source_version")
    op.drop_column("games", "eval_depth")
```

### Manual Review Checklist

After `--autogenerate`:
- [ ] Confirm autogenerate adds `eval_depth` (SmallInteger) + `eval_source_version` (String) — no other changes
- [ ] Confirm `down_revision` points to `2af113f4790f` (latest current)
- [ ] Add comment block explaining eval_depth NULL behavior for all current importers
- [ ] Run against dev DB: `uv run alembic upgrade head`
- [ ] Run against benchmark DB: `DATABASE_URL=...benchmark... uv run alembic upgrade head`
- [ ] Run against test DB: `uv run pytest tests/test_llm_logs_migration.py` as sanity pattern (if a migration test exists)

### Schema Model Update

In `app/models/game.py`, add after `black_blunders`:
```python
# Eval metadata: populated for Lichess imports when API surfaces it; NULL for chess.com
# eval_depth is NULL for all current Lichess API imports (API does not expose depth in JSON)
eval_depth: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
eval_source_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
```

### NormalizedGame Schema Update

`app/schemas/normalization.py` `NormalizedGame` needs two new optional fields:
```python
eval_depth: int | None = None
eval_source_version: str | None = None
```

And `normalize_lichess_game` must set `eval_source_version="lichess-pgn"` unconditionally for all Lichess games.

---

## 7. Sample Ingestion Architecture

### Overview: Three Scripts

Per CONTEXT.md code_context section, three scripts in `scripts/`:

1. **`scripts/select_benchmark_users.py`** — One-shot: scans monthly dump, accumulates per-player stats, assigns cells, persists username lists.
2. **`scripts/import_benchmark_users.py`** — Orchestrator: reads persisted user lists, counts already-imported users per cell, imports `N - current` additional users via existing pipeline, writes outer-loop checkpoints.
3. (Optional) **`scripts/seed_benchmark_db.py`** is NOT needed as a separate script — stub User row creation happens inline in `import_benchmark_users.py` before calling `run_import`.

### Checkpoint / Persistence Schema

Per D-15a, checkpoints live in the benchmark DB itself. Two tables:

**Table 1: `benchmark_selected_users`** (persisted by `select_benchmark_users.py`, read by `import_benchmark_users.py`)

```python
class BenchmarkSelectedUser(Base):
    __tablename__ = "benchmark_selected_users"
    __table_args__ = (
        UniqueConstraint("lichess_username", name="uq_benchmark_selected_users_username"),
    )
    
    id: Mapped[int] = mapped_column(primary_key=True)
    lichess_username: Mapped[str] = mapped_column(String(100), nullable=False)
    rating_bucket: Mapped[int] = mapped_column(SmallInteger, nullable=False)  # e.g., 800, 1200, 1600...
    tc_bucket: Mapped[str] = mapped_column(String(20), nullable=False)  # bullet/blitz/rapid/classical
    median_elo: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    eval_game_count: Mapped[int] = mapped_column(SmallInteger, nullable=False)  # eval-bearing games in snapshot month
    selected_at: Mapped[datetime] = mapped_column(server_default=func.now())
    dump_month: Mapped[str] = mapped_column(String(7), nullable=False)  # "2026-02"
```

**Table 2: `benchmark_ingest_checkpoints`** (written/read by `import_benchmark_users.py`)

```python
class BenchmarkIngestCheckpoint(Base):
    __tablename__ = "benchmark_ingest_checkpoints"
    __table_args__ = (
        UniqueConstraint("lichess_username", name="uq_benchmark_ingest_checkpoints_username"),
    )
    
    id: Mapped[int] = mapped_column(primary_key=True)
    lichess_username: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # "pending" | "completed" | "skipped" | "failed"
    games_imported: Mapped[int] = mapped_column(nullable=False, default=0)
    skip_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)  # "over_20k_games" etc.
    started_at: Mapped[datetime | None]
    completed_at: Mapped[datetime | None]
    benchmark_user_id: Mapped[int | None]  # FK to users.id in benchmark DB (the stub User row)
```

**INFRA-02 compliance note:** These tables are NOT in the canonical Alembic migration chain (they would contaminate prod/dev/test schemas). Two options:
- Add them via a **separate migration env** scoped to the benchmark DB only (complex)
- Create them via `CREATE TABLE IF NOT EXISTS` at the start of `select_benchmark_users.py` (simpler, matches the "ingestion script" pattern)

**Recommended:** Create them inline in the scripts using `metadata.create_all()` against the benchmark DB connection. This avoids polluting the canonical migration chain while keeping schema creation reproducible. The tables only ever exist in the benchmark DB; INFRA-02 says no benchmark-only schema additions to the canonical Alembic chain.

### Orchestrator Flow: `--per-cell N`

```
startup:
  1. Open connection to benchmark DB
  2. For each (rating_bucket, tc_bucket) cell in 5x4 grid:
     a. Count users in benchmark_selected_users for this cell
     b. Count completed users in benchmark_ingest_checkpoints for this cell
     c. Deficit = N - completed_count (if deficit <= 0: skip cell)
  3. For each cell with deficit > 0:
     a. Pull next `deficit` usernames from benchmark_selected_users
        (order by id, skip already-completed/skipped/failed users)
     b. For each username in drawn batch:
        i.   Pre-check: query Lichess API for game count (or attempt import + check 20k trigger)
        ii.  Create stub User row (if not exists) in benchmark DB
        iii. Insert checkpoint row with status="pending"
        iv.  Call run_import (creates import job, calls lichess_client)
        v.   On completion: update checkpoint to "completed"
        vi.  On 20k games: update checkpoint to "skipped", skip_reason="over_20k_games"
        vii. On error: update checkpoint to "failed" (outer Sentry capture)
  4. On SIGINT: flush current batch, commit checkpoint, exit cleanly
```

**Resumability:** Re-running with `--per-cell 100` when `current=3`:
- Counts 3 completed users per cell
- Draws 97 more from the pool (skipping already-completed/failed/skipped)
- Imports only new users
- Already-imported games are no-op via `(user_id, platform, platform_game_id)` unique constraint

---

## 8. Stub User Row Strategy

### FastAPI-Users Required Fields

`SQLAlchemyBaseUserTable` (verified from venv source) requires: [VERIFIED: app/models/user.py + fastapi_users_db_sqlalchemy]
- `email`: unique String(320)
- `hashed_password`: String(1024)
- `is_active`: Boolean (default True)
- `is_superuser`: Boolean (default False)
- `is_verified`: Boolean (default False)

Plus project-specific extensions in `app/models/user.py`:
- `chess_com_username`: nullable
- `lichess_username`: String(100), nullable
- `created_at`, `last_login`, `last_activity`: timestamp fields
- `is_guest`: Boolean (default False)
- `beta_enabled`: Boolean (default False)

### Recommended Stub Strategy

```python
from app.models.user import User
from sqlalchemy.ext.asyncio import AsyncSession

async def create_stub_user(session: AsyncSession, lichess_username: str) -> int:
    """Create a benchmark stub User row satisfying FastAPI-Users invariants.
    
    These users never serve auth — the benchmark DB has no auth surface.
    Sentinel email prevents collision with real users (different domain).
    """
    stub = User(
        email=f"lichess-{lichess_username.lower()}@benchmark.flawchess.local",
        hashed_password="!BENCHMARK_NO_AUTH",   # bcrypt hash prefix "!" = disabled in many systems
        is_active=False,                          # never can log in even if prod DB were accessed
        is_superuser=False,
        is_verified=False,
        lichess_username=lichess_username,
        is_guest=False,
        beta_enabled=False,
    )
    session.add(stub)
    await session.flush()  # get the id before commit
    return stub.id
```

**`is_active=False`:** Prevents any auth attempt from succeeding even if the benchmark DB were accidentally exposed. No functional downside since benchmark users never log in.

**Email uniqueness:** `lichess-{username.lower()}@benchmark.flawchess.local` — the `.local` TLD is not a real domain, and the `benchmark.flawchess.local` subdomain is clearly synthetic. This passes FastAPI-Users email validation. [ASSUMED - standard email validation accepts `.local` TLDs; verify if email validation is strict]

**Password:** `"!BENCHMARK_NO_AUTH"` is not a valid bcrypt hash (bcrypt hashes start with `$2b$`). FastAPI-Users `verify_password` compares against the hashed value via bcrypt — a non-bcrypt string will always fail comparison. No security risk. [ASSUMED - FastAPI-Users uses bcrypt comparison which will fail for non-bcrypt strings]

**Idempotency:** Before `create_stub_user`, check if a User row with `lichess_username=username` already exists. If so, return existing `id` without creating a duplicate. The `uq_games_user_platform_game_id` unique constraint handles game-level idempotency; user-level idempotency needs an explicit check.

---

## 9. Selection-Scan Player Bucketing Algorithm

### Rating Bucket Grid

Per INGEST-02, the 5 rating buckets are: 800-1199, 1200-1599, 1600-1999, 2000-2399, 2400+.

Wait — REQUIREMENTS.md says: `800–1200, 1200–1600, 1600–2000, 2000–2400, 2400+` while SEED-002 says the same but with different bracket names. The benchmarks skill uses `floor(user_rating / 500) * 500` (500-wide buckets starting at 0: 0, 500, 1000, 1500, 2000...).

**Conflict:** REQUIREMENTS.md has 400-wide buckets; benchmarks skill has 500-wide buckets. The planner needs to resolve this. For Phase 69 selection, the 400-wide REQUIREMENTS.md buckets match the stated grid (5 buckets covering 800+). The benchmarks skill's 500-wide bucketing applies to analytics queries in Phase 73. **For INGEST-02 and INGEST-03, use the REQUIREMENTS.md 400-wide grid for selection.** [ASSUMED - pending planner reconciliation; see Open Questions Q1]

**Recommended bucket boundaries (from REQUIREMENTS.md INGEST-02):**

| Bucket # | Label | Elo Range |
|----------|-------|-----------|
| 1 | 800 | 800-1199 |
| 2 | 1200 | 1200-1599 |
| 3 | 1600 | 1600-1999 |
| 4 | 2000 | 2000-2399 |
| 5 | 2400 | 2400+ |

Games with ratings < 800 or NULL are excluded from selection.

### Time Control Grid

The 4 TC buckets follow the FlawChess canonical bucketing rule from `app/services/normalization.py` `parse_time_control`:
- **bullet:** estimated_seconds < 180
- **blitz:** 180 <= estimated_seconds < 600
- **rapid:** 600 <= estimated_seconds <= 1800
- **classical:** estimated_seconds > 1800 or daily
[VERIFIED: app/services/normalization.py]

### Bucketing Algorithm (Pseudocode)

```python
from collections import defaultdict, Counter

# player_stats: dict[username -> {"elos": [int], "tcs": ["bullet"|...], "eval_count": int}]
player_stats: dict[str, dict] = defaultdict(lambda: {"elos": [], "tcs": [], "eval_count": 0})

for game in scan_dump_for_players(dump_path):
    for side in ["white", "black"]:
        username = game[side]
        elo = game[f"{side}_elo"]
        tc = compute_tc_bucket(game["time_control"])
        
        if username and elo and tc:
            player_stats[username]["elos"].append(elo)
            player_stats[username]["tcs"].append(tc)
            if game["has_eval"]:
                player_stats[username]["eval_count"] += 1

# After scan: assign each player to one cell
selected_users: dict[tuple[int, str], list[str]] = defaultdict(list)  # (rating_bucket, tc) -> usernames

for username, stats in player_stats.items():
    if stats["eval_count"] < K_EVAL_THRESHOLD:  # D-12: K=5
        continue
    
    elos = stats["elos"]
    tcs = stats["tcs"]
    
    # Median Elo
    median_elo = sorted(elos)[len(elos) // 2]
    
    # Modal TC (most frequent)
    modal_tc = Counter(tcs).most_common(1)[0][0]
    
    # Assign to rating bucket
    if median_elo < 800:
        continue  # below minimum
    elif median_elo < 1200:
        rating_bucket = 800
    elif median_elo < 1600:
        rating_bucket = 1200
    elif median_elo < 2000:
        rating_bucket = 1600
    elif median_elo < 2400:
        rating_bucket = 2000
    else:
        rating_bucket = 2400
    
    selected_users[(rating_bucket, modal_tc)].append(username)

# Sample N per cell (shuffle for randomness, then take first N)
import random
random.shuffle(selected_users_list)
cell_quota = per_cell_N  # e.g., 500 for full run
final_selection = {cell: users[:cell_quota] for cell, users in selected_users.items()}
```

**Multi-TC players:** Players whose games span multiple TCs are assigned to the modal TC (most games played). This is unambiguous if one TC dominates. For ties (e.g., 50/50 blitz/rapid), `Counter.most_common(1)` returns one deterministically (first in Counter's order). This is acceptable — the player's historical games will still appear in multiple analytics cells when queried (D-10).

**D-05 compliance:** Player-side bucketing for analytics happens at query time on `white_rating`/`black_rating` per game, not at selection time. Selection bucket only determines which cell the user is drawn from.

---

## 10. Storage Budget Verification

### Prod Row Sizes (Verified from Production DB)

| Table | Row Count | Total Size (w/ indexes) | Bytes/Row |
|-------|-----------|--------------------------|-----------|
| `games` | 299,926 | 932 MB | **3,106 bytes** |
| `game_positions` | 20,498,142 | 7,178 MB | **350 bytes** |
| **avg positions/game** | — | — | **68.3** |

[VERIFIED: live query against production DB via `asyncpg` on port 15432]

### Storage Projections (Phase 69 Completion Target: 2000 users)

| Users | Avg Games/User | Total Games | Total Positions | Estimated Storage |
|-------|---------------|-------------|-----------------|-------------------|
| 2,000 | 500 | 1.0M | 68.3M | **27 GB** |
| 2,000 | 1,000 | 2.0M | 136.7M | **54 GB** |
| 2,000 | 2,000 | 4.0M | 273.4M | **108 GB** |
| 2,000 | 3,000 | 6.0M | 410.1M | **162 GB** |

**INGEST-05 verdict:** The 50-100 GB target is met at 2000 users with 1000-2000 avg games/user. At 36 months, an active player averages ~100-500 games/month depending on TC. A blitz player averaging 200 games/month over 36 months = 7200 games — this user would be under the 20k hard-skip threshold but would put storage pressure. Monitoring per-user game counts during ingest is important.

### Queen Endgame Coverage (Success Criterion 3)

At 54 GB (2000 users x 1000 games x 68.3 positions):
- Total positions: 136.7M
- Per cell (20 cells): 6.8M positions
- Queen endgame positions (~2%): 136k per cell
- Success criterion requires >= 1k queen endgame samples per cell: **136x overqualified at 2000 users**

Even at the smoke test level (3 users/cell = 60 users x 1000 games):
- Total positions: 4.1M
- Per cell: 205k positions  
- Queen endgame positions (~2%): 4,100 — **still above 1k minimum**

### Index Strategy

The existing indexes on `game_positions` are sufficient for benchmark DB queries. No benchmark-specific indexes are needed for Phase 69. Phase 73 may add analytics-oriented covering indexes when the `/benchmarks` skill is upgraded, but that is out of Phase 69 scope. [ASSUMED - Phase 73 queries are not yet designed; Phase 69 planner should add an open question]

---

## 11. Resumability Test Strategy

### Verification Requirement (Success Criterion 4)

"Interrupting with SIGINT mid-dump and resuming produces the same row counts as an uninterrupted run on a small dump."

### Recommended Test: Manual Verification Script

Not CI-eligible (requires a real Lichess API call + benchmark DB running). Lives as a manual verification step in the phase's verification report.

**Procedure:**

```bash
# Step 1: Run import for 3 users in one cell (smoke test)
uv run python scripts/import_benchmark_users.py --per-cell 3

# Step 2: Record row counts
psql postgresql://...benchmark... -c "SELECT count(*) FROM games; SELECT count(*) FROM game_positions;"
# Save as baseline: games_before=X, positions_before=Y

# Step 3: Start import for 10 more users, interrupt mid-run
uv run python scripts/import_benchmark_users.py --per-cell 13 &
IMPORT_PID=$!
sleep 30  # let it partially complete
kill -INT $IMPORT_PID

# Step 4: Record partial counts
psql ... -c "SELECT count(*) FROM games; SELECT count(*) FROM game_positions;"

# Step 5: Resume
uv run python scripts/import_benchmark_users.py --per-cell 13

# Step 6: Record final counts; compare with uninterrupted run
# Uninterrupted: start from fresh DB, run --per-cell 13 without interruption
# Row counts must match (within import-order nondeterminism)
```

**Key invariant:** `benchmark_ingest_checkpoints` records which users are "completed" — on resume, the orchestrator skips them and continues from the first "pending" user. Per-game idempotency via `(user_id, platform, platform_game_id)` unique constraint means partial users don't double-import on resume. [VERIFIED: import_service.py uses bulk_insert_games which handles duplicate via unique constraint]

**CI-eligible component:** A unit test for the outer-loop skip logic (given a list of usernames and a set of "completed" usernames, verify the orchestrator draws the right batch) can live in `tests/test_benchmark_ingest.py` without network access.

---

## 12. Validation Architecture (Dimension 8 — Nyquist Validation)

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio |
| Config | `pyproject.toml` `[tool.pytest.ini_options]` (asyncio_mode = "auto") |
| Quick run command | `uv run pytest tests/test_benchmark_ingest.py -x` |
| Full suite command | `uv run pytest` |

### Phase 69 Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INFRA-01 | docker-compose.benchmark.yml starts a healthy PG18 instance | manual smoke | `docker compose -f docker-compose.benchmark.yml -p flawchess-benchmark ps` | Wave 0 |
| INFRA-02 | Alembic migrations run against benchmark DB produce correct schema | integration | `DATABASE_URL=...benchmark... uv run alembic upgrade head` (verify no errors) | Wave 0 |
| INFRA-03 | flawchess-benchmark-db MCP server returns row counts | manual smoke | `mcp__flawchess-benchmark-db__query` with `SELECT count(*) FROM games` | Wave 0 (manual) |
| INGEST-01 | Pre-filter scan extracts headers + eval flag correctly | unit | `uv run pytest tests/test_benchmark_ingest.py::test_scan_dump_parser -x` | Wave 0 |
| INGEST-02 | Selection bucketing assigns players to correct (rating x TC) cell | unit | `uv run pytest tests/test_benchmark_ingest.py::test_player_bucketing -x` | Wave 0 |
| INGEST-03 | Player-side bucketing: analytics queries bucket by white_rating/black_rating independently | query | Manual SQL against benchmark DB: `SELECT white_rating, black_rating FROM games LIMIT 5` | manual |
| INGEST-04 | SIGINT mid-import + resume produces same row counts | integration/manual | See Section 11 procedure | manual |
| INGEST-05 | Storage <= 100 GB after 2000-user import | manual check | `SELECT pg_size_pretty(pg_database_size('flawchess_benchmark'))` via MCP | post-ingest |
| INGEST-06 | Alembic migration adds eval_depth/eval_source_version to games; eval_source_version='lichess-pgn' on imported games | unit + integration | `uv run pytest tests/test_benchmark_ingest.py::test_eval_columns -x` | Wave 0 |

### Dimension 8: Evidence for Phase 70

Phase 70 (classifier validation) needs the following evidence from Phase 69:

1. **Per-cell game counts:** `SELECT count(*) FROM games g JOIN users u ON u.id = g.user_id GROUP BY floor(CASE WHEN g.user_color='white' THEN g.white_rating ELSE g.black_rating END / 400) * 400, g.time_control_bucket` — must confirm all 20 cells populated above minimum.
2. **Eval coverage per cell:** `SELECT count(*) FILTER (WHERE eval_cp IS NOT NULL), count(*) FROM game_positions WHERE endgame_class IS NOT NULL` — Phase 70 queries `eval_cp IS NOT NULL` for validation.
3. **eval_source_version distribution:** `SELECT eval_source_version, count(*) FROM games GROUP BY eval_source_version` — should show `"lichess-pgn"` for all Lichess games, NULL for any non-Lichess.
4. **Resumability proof:** Row-count comparison from Section 11 procedure documented in verification report.

### Sampling Rate

- **Per user import (development):** `uv run pytest tests/test_benchmark_ingest.py -x`
- **Post-ingest verification:** MCP queries confirming row counts and eval coverage
- **Phase gate:** All 9 requirements verified (mix of automated + manual) before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_benchmark_ingest.py` — unit tests for scan_dump_parser, player_bucketing, eval_columns
- [ ] `deploy/init-benchmark-db.sql` — benchmark init SQL file
- [ ] `docker-compose.benchmark.yml` — benchmark compose file
- [ ] `bin/benchmark_db.sh` — start/stop/reset script
- [ ] `zstandard` package added to `pyproject.toml` (or CLI fallback documented)

---

## 13. Security Threat Model

| Threat | STRIDE | Severity | Mitigation | Status |
|--------|--------|----------|------------|--------|
| Cross-contamination: benchmark DB writes accidentally reach prod | Tampering | **HIGH** | Separate Docker project name (`flawchess-benchmark`), separate named volume (`benchmarkpgdata`), separate port (5433), separate database name (`flawchess_benchmark`), separate user (`flawchess_benchmark`). `DATABASE_URL` in benchmark scripts must reference `localhost:5433/flawchess_benchmark` explicitly. | Design |
| MCP read-only role grants more than SELECT | Elevation of Privilege | **MEDIUM** | `init-benchmark-db.sql` uses `ALTER DEFAULT PRIVILEGES ... GRANT SELECT ON TABLES` + `GRANT SELECT ON ALL TABLES` pattern. No WRITE grants to `flawchess_benchmark_ro`. Verify with: `SELECT has_table_privilege('flawchess_benchmark_ro', 'games', 'INSERT')` (must be false). | Design |
| Ingestion script credentials in shell history or logs | Information Disclosure | **LOW** | Benchmark DB password stored in `~/.claude.json` (MCP only) and `init-benchmark-db.sql` (local file, not committed to git). Benchmark scripts connect via `DATABASE_URL` env var. Scripts must not echo passwords. | Design |
| Lichess API rate limit triggering account/IP ban | Denial of Service | **MEDIUM** | Existing `lichess_client.py` handles 429 with 60-second backoff (`_RATE_LIMIT_BACKOFF_SECONDS = 60`) and a `sentry_sdk.capture_message` warning. Max 3 retries. Per-user sequentiality (never `asyncio.gather` on same session) also limits concurrent requests. The orchestrator runs one user at a time, which is within Lichess's acceptable usage. [VERIFIED: lichess_client.py] | Existing |
| Buggy script triggers ON DELETE CASCADE, destroys benchmark data | Tampering | **LOW** | Impact contained to benchmark DB only (never touches prod). A `--dry-run` flag on the orchestrator and a confirmation prompt (like `reimport_games.py` pattern) reduces accidental invocation risk. | Design |
| Benchmark DB read-only user password committed to git | Information Disclosure | **MEDIUM** | `init-benchmark-db.sql` uses `<PASSWORD>` placeholder with explicit note NOT to commit the real password. Same pattern as prod. CLAUDE.md §Database Access documents that the password is local-only. | Design |
| Lichess dump download path traversal or corrupt download | Tampering | **LOW** | Download via HTTPS to a known path. Verify file size before scan begins. `zstandard` decompressor will raise on corrupt data. | Design |

---

## 14. Sentry Capture Boundary

### Existing Pattern (Verified)

`import_service.run_import` already has the correct Sentry capture at the outer boundary:
- `TimeoutError` → `sentry_sdk.set_context("import", {...}); sentry_sdk.capture_exception()` (lines 275-276)
- Generic `Exception` → `sentry_sdk.set_context("import", {...}); sentry_sdk.capture_exception(exc)` (lines 298-299)
[VERIFIED: app/services/import_service.py]

`lichess_client.fetch_lichess_games` does NOT capture per-attempt stream errors (correct) — it only captures a 429 warning message, and lets the final `last_attempt_error` propagate to `run_import`'s outer handler. [VERIFIED: lichess_client.py lines 184-193]

### Orchestrator Script Sentry Pattern

The benchmark orchestrator script (`scripts/import_benchmark_users.py`) must follow `reimport_games.py`'s pattern:

1. Initialize Sentry at script startup (if `settings.SENTRY_DSN` is set)
2. Outer `try/except` per user captures terminal failures:
   ```python
   try:
       await import_one_user(username, ...)
   except Exception as exc:
       sentry_sdk.capture_exception(exc)
       log_error(username, exc)
       update_checkpoint(username, "failed")
   ```
3. `run_import` is called inside `import_one_user` — it already handles its own Sentry capture. The orchestrator's outer boundary captures failures that happen OUTSIDE `run_import` (e.g., stub user creation failure, checkpoint DB error).
4. Do NOT add `capture_exception` in the per-user retry loop (if any). Only at the outer boundary.
[VERIFIED: reimport_games.py Sentry pattern; import_service.py capture boundary]

**Tagging:** Use `sentry_sdk.set_context("benchmark_ingest", {"username": username, "cell": f"{rating_bucket}/{tc_bucket}"})` before capture to preserve Sentry issue grouping (per CLAUDE.md §Error Handling).

---

## 15. Open Questions for the Planner

1. **Rating bucket width reconciliation (PLANNING BLOCKER):** REQUIREMENTS.md INGEST-02 uses 400-wide buckets (800-1200, 1200-1600, ..., 2400+). The benchmarks skill uses 500-wide (`floor(elo/500)*500`). Phase 69 selection uses 400-wide per REQUIREMENTS.md. Phase 73 analytics will use 500-wide per the existing benchmarks skill. Either (a) accept that selection and analytics use different bucket widths (not ideal but functional), or (b) update INGEST-02 to use 500-wide buckets matching the benchmarks skill. Recommend resolving before writing the plan.

2. **`zstandard` as project dependency:** The streaming pre-filter requires `zstandard` (Python bindings for Zstd). This is a dev/scripts dependency, not needed for the production backend. Plan options: (a) add to `[dependency-groups] dev` in `pyproject.toml`, (b) add as a conditional import with a graceful error if not installed, (c) use `subprocess` + `zstdcat` CLI fallback. Decision affects Wave 0 setup.

3. **Benchmark-only checkpoint tables vs. canonical schema:** Section 7 recommends creating `benchmark_selected_users` and `benchmark_ingest_checkpoints` via `metadata.create_all()` rather than Alembic migrations (to avoid polluting prod schema). Confirm this approach is acceptable before planning the migration wave.

4. **eval_depth NULL documentation scope:** Per D-07, `eval_depth` will be NULL for all current Lichess API imports (API does not surface depth in JSON). The plan must include: (a) a comment in the migration file, (b) a note in the `import_benchmark_users.py` script header, (c) a verification note in the ingestion script. Confirm whether a test is also required (INGEST-06 says "documented" not "tested").

5. **Stub User email validation strictness:** `lichess-{username}@benchmark.flawchess.local` — does FastAPI-Users' email validator accept `.local` TLD? If it uses a strict RFC-5321 validator, `*.local` may fail. Alternative: `lichess-{username}@benchmark.internal` or a real-looking but synthetic domain like `benchmark-noreply@flawchess.com` with a username prefix. Verify during Wave 0 implementation.

6. **`_BATCH_SIZE` in `import_service.py`:** The comment in `import_service.py` says `_BATCH_SIZE = 28` (lines 37-40), NOT 10 as stated in STATE.md and CLAUDE.md. The code comment says it was increased from 10 to 28. The STATE.md constraint says "10 games per commit — OOM-safe". This is a discrepancy. The benchmark scripts reference says batch_size=10. Planner should verify which value is current in the codebase and which applies to benchmark ingest. [VERIFIED: import_service.py shows _BATCH_SIZE = 28 with comment "Increased from 10 to 28 for fewer DB commits"]

---

## 16. References

### Primary (HIGH confidence)

- `app/services/lichess_client.py` — since_ms parameter, evals=true, retry pattern, Sentry boundary
- `app/services/import_service.py` — run_import orchestration, _BATCH_SIZE, Sentry pattern
- `app/services/normalization.py` — normalize_lichess_game, analysis field mapping
- `app/services/zobrist.py` — eval_cp parsing via node.eval(), pov.white().score()
- `app/models/game.py` — canonical games table, existing columns
- `app/models/game_position.py` — eval_cp/eval_mate columns, existing indexes
- `app/models/user.py` — User model, FastAPI-Users extended fields
- `docker-compose.dev.yml` — template for benchmark compose file
- `deploy/init-dev-db.sql` — template for benchmark init SQL
- `bin/reset_db.sh` — template for benchmark_db.sh
- `scripts/reimport_games.py` — Sentry pattern, script structure reference
- `alembic/versions/20260424_121249_2af113f4790f_drop_llm_logs_flags.py` — current migration format
- `alembic/env.py` — DATABASE_URL override mechanism
- `.claude.json` (project section) — exact MCP server registration format verified
- `.planning/phases/69-benchmark-db-infrastructure-ingestion-pipeline/69-CONTEXT.md` — all locked decisions
- `.planning/REQUIREMENTS.md` — INFRA-01..03, INGEST-01..06
- Production DB (live query via asyncpg port 15432) — row sizes: games=3106 bytes, game_positions=350 bytes, avg 68.3 positions/game

### Secondary (MEDIUM confidence)

- WebSearch: Lichess monthly dump format confirmed (`.pgn.zst`, ~20 GB compressed, ~140 GB uncompressed)
- WebSearch + lichess forum: `[%eval]` format confirmed as pawn units signed from White's POV
- WebSearch: python-zstandard confirmed as viable streaming decompressor at C-extension speeds
- `github.com/lichess-org/api` — api-games-user-username.yaml confirms `evals` parameter description

### Tertiary (LOW confidence)

- [ASSUMED] Lichess `evals=true` parameter adds PGN annotations only, not JSON depth fields — inferred from thorough codebase inspection (normalization.py has no depth extraction) + failed API schema fetch. Needs runtime verification during Wave 0 implementation via `print(game_dict.keys())` on a sample analyzed game.
- [ASSUMED] FastAPI-Users email validator accepts `.local` TLD for stub user emails — needs Wave 0 verification.
- [ASSUMED] Typical Lichess user average 500-2000 games over 36 months — storage budget depends on this; actual distribution unknown without sampling.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Lichess API does not surface `eval_depth` in game JSON (`evals=true` only adds PGN annotations) | Sections 3, 6 | eval_depth could be populated; implementation would add field extraction instead of leaving NULL |
| A2 | `.local` TLD accepted by FastAPI-Users email validator for stub user email | Section 8 | Stub user creation fails; need alternative email pattern |
| A3 | Typical Lichess user averages 500-2000 games over 36 months | Section 10 | Storage could exceed projections if users average 3000+ games |
| A4 | Monthly Lichess standard dump ~20M games (order of magnitude) | Section 2 | Pre-filter scan throughput estimate may be off; not a blocker |
| A5 | `_BATCH_SIZE = 28` (not 10) is the current value in import_service.py | Section 15 Q6 | Benchmark ingest plan must use the verified constant, not the outdated STATE.md reference |

---

## Metadata

**Confidence breakdown:**
- Infrastructure (docker-compose, MCP, alembic): HIGH — direct code verification
- Import pipeline reuse: HIGH — full code read
- eval_depth API surface: MEDIUM — codebase confirms NULL path; API YAML confirms `evals` adds annotations; no runtime test
- Storage projections: HIGH — verified from live production DB row sizes
- Dump format + centipawn convention: MEDIUM — confirmed via WebSearch + codebase cross-reference

**Research date:** 2026-04-25
**Valid until:** 2026-05-25 (stable infrastructure; 7 days for Lichess API surface if they update)

---

## RESEARCH COMPLETE
