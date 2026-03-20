# Phase 2: Import Pipeline - Research

**Researched:** 2026-03-11
**Domain:** Async background job management, chess platform API clients, bulk DB insertion
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

None — user delegated all Phase 2 technical decisions to Claude.

### Claude's Discretion

User delegated all Phase 2 decisions to Claude. The following areas should be resolved during research and planning based on project requirements, CLAUDE.md constraints, and best practices:

**Import job tracking:**
- Background job management approach (in-memory vs DB-backed)
- Progress reporting mechanism (polling endpoint with job ID)
- Job state model (pending, in_progress, completed, failed)
- Concurrency handling (what if user triggers import while one is running)

**Error handling & resilience:**
- Platform API downtime and rate limiting strategy
- Retry policy for transient failures
- Partial success behavior (some games imported, then failure)
- User-facing error messages for invalid usernames, API errors, etc.
- PGN parsing failures for individual games (skip and continue)

**API endpoint design:**
- Endpoint structure (unified vs per-platform)
- Re-sync trigger mechanism (same endpoint, detects last import)
- Response shape for import initiation and status polling
- Progress granularity (games fetched count, total estimate if available)

**Platform normalization:**
- chess.com monthly archives API: sequential fetching with rate-limit delays, User-Agent header required
- lichess NDJSON streaming: line-by-line parsing
- Unified schema mapping from both platform formats to Game model
- Edge cases: missing fields, non-Standard variants (filter out), anonymous opponents
- Time control bucketing: <=180s bullet, <=600s blitz, <=1800s rapid, else classical
- lichess timestamps in milliseconds (not seconds)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.

</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| IMP-01 | User can import games from chess.com by entering their username | chess.com archive API endpoints, JSON normalization patterns |
| IMP-02 | User can import games from lichess by entering their username | lichess `/api/games/user` NDJSON streaming, normalization |
| IMP-03 | User can re-sync to fetch only new games since last import (incremental) | `since` parameter on lichess; latest archive month detection on chess.com; `last_synced_at` in import_jobs table |
| IMP-04 | User sees import progress and status while games are being fetched | In-memory job store with UUID job ID; polling endpoint; progress counter |
| INFRA-02 | Game import runs as a background task (does not block the API server) | `asyncio.create_task` pattern, immediate job ID response |

</phase_requirements>

---

## Summary

Phase 2 builds the import pipeline that fetches games from chess.com and lichess, processes them in the background, and stores them with Zobrist hashes via the existing Phase 1 models. The core challenge is managing long-running async jobs (a full chess.com import can be hundreds of API calls across monthly archives) while keeping the API responsive and giving users live progress feedback.

The recommended approach uses `asyncio.create_task` (not FastAPI `BackgroundTasks`) to launch import jobs, with an in-memory job registry (Python dict keyed by UUID) for progress tracking. This avoids the complexity of Celery/Redis while fully meeting the phase requirements — a single Uvicorn worker is the deployment model for v1 and in-memory state is sufficient. The DB stores a lightweight `import_jobs` table for persistence of terminal states and to support incremental re-sync (tracking `last_synced_at` per user+platform).

chess.com is fetched synchronously month-by-month via the JSON archive API with 100–300ms delays. lichess is streamed as NDJSON line-by-line via `httpx.AsyncClient.stream()`. Both normalize into the existing `Game`/`GamePosition` models. Duplicates are handled by the existing `ON CONFLICT DO NOTHING` on the `(platform, platform_game_id)` unique constraint.

**Primary recommendation:** Use `asyncio.create_task` + in-memory job dict + DB `import_jobs` table. No Celery, no Redis. Keep it simple and async-native.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| httpx | already installed | Async HTTP client for both platform APIs | Project constraint (CLAUDE.md); `requests` would block the event loop |
| asyncio | stdlib | `create_task` for non-blocking job execution | Native to FastAPI's event loop; no extra dependencies |
| uuid | stdlib | Job ID generation | Universally available; UUID4 for unpredictable IDs |
| python-chess | >=1.10.0 | PGN parsing via `hashes_for_game()` | Already in use from Phase 1 |
| SQLAlchemy 2.x async | already installed | Bulk insert of Game + GamePosition rows | Already in use from Phase 1 |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| asyncio.sleep | stdlib | Rate-limit delays between chess.com requests | 100–300ms between archive month fetches |
| json | stdlib | NDJSON line parsing for lichess | Built-in; no extra dependency needed |
| datetime | stdlib | `last_synced_at` timestamps, `since` ms conversion | Built-in |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| asyncio.create_task + in-memory dict | Celery + Redis | Celery adds Redis infra, worker processes, separate config — overkill for v1 single-worker deployment |
| asyncio.create_task + in-memory dict | ARQ + Redis | ARQ is elegant and async-native but still requires Redis; unnecessary for v1 |
| asyncio.create_task + in-memory dict | FastAPI BackgroundTasks | BackgroundTasks are tied to a single request lifecycle and provide no status tracking — insufficient for IMP-04 |
| In-memory job dict | Full DB job table | Full DB job table adds write overhead on every progress tick; in-memory is faster and acceptable for single-worker v1 |

**Installation:** No new dependencies needed — httpx, asyncio, and SQLAlchemy are already installed.

---

## Architecture Patterns

### Recommended Project Structure

```
app/
├── routers/
│   └── imports.py          # POST /imports, GET /imports/{job_id}
├── services/
│   ├── import_service.py   # orchestrates job launch, calls platform clients
│   ├── chesscom_client.py  # chess.com API client
│   └── lichess_client.py   # lichess API client
├── repositories/
│   ├── game_repository.py  # bulk insert Game + GamePosition rows
│   └── import_job_repository.py  # CRUD for import_jobs table
├── models/
│   └── import_job.py       # ImportJob SQLAlchemy model
└── schemas/
    └── imports.py          # Pydantic request/response schemas
```

### Pattern 1: Job Registry (In-Memory + DB hybrid)

**What:** An in-memory Python dict holds live progress for running jobs. The `import_jobs` DB table records final state (completed/failed) and `last_synced_at` for incremental sync.

**When to use:** Single-worker v1. If the process restarts, in-flight job state is lost (acceptable — users can re-trigger). Completed/failed state survives via DB.

```python
# Source: asyncio stdlib + project patterns
import asyncio
import uuid
from dataclasses import dataclass, field
from enum import Enum

class JobStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class JobState:
    job_id: str
    user_id: int
    platform: str
    username: str
    status: JobStatus = JobStatus.PENDING
    games_fetched: int = 0
    games_imported: int = 0
    error: str | None = None

# Module-level registry in import_service.py
_jobs: dict[str, JobState] = {}

def create_job(user_id: int, platform: str, username: str) -> str:
    job_id = str(uuid.uuid4())
    _jobs[job_id] = JobState(job_id=job_id, user_id=user_id,
                              platform=platform, username=username)
    return job_id

def get_job(job_id: str) -> JobState | None:
    return _jobs.get(job_id)
```

### Pattern 2: asyncio.create_task for Non-Blocking Import

**What:** The POST endpoint creates a job ID, fires `asyncio.create_task(run_import(...))`, and immediately returns the job ID. The import runs in the background on the event loop.

**When to use:** Any long-running I/O-bound operation that must not block the API response.

```python
# Source: FastAPI + asyncio stdlib
@router.post("/imports", response_model=ImportStartedResponse)
async def start_import(
    request: ImportRequest,
    current_user_id: int = Depends(get_current_user_id),
):
    # Check for existing in-progress job for this user+platform
    existing = import_service.find_active_job(current_user_id, request.platform)
    if existing:
        return ImportStartedResponse(job_id=existing.job_id, status=existing.status)

    job_id = import_service.create_job(
        user_id=current_user_id,
        platform=request.platform,
        username=request.username,
    )
    asyncio.create_task(
        import_service.run_import(job_id)
    )
    return ImportStartedResponse(job_id=job_id, status=JobStatus.PENDING)
```

### Pattern 3: chess.com Sequential Archive Fetch

**What:** Fetch the list of monthly archive URLs, then iterate through each month with `asyncio.sleep` delays. Parse the JSON response for individual game objects.

**When to use:** Always for chess.com — their API requires sequential access.

```python
# Source: chess.com Published-Data API docs + CLAUDE.md constraints
USER_AGENT = "Chessalytics/1.0 (contact@example.com)"

async def fetch_chesscom_games(
    client: httpx.AsyncClient,
    username: str,
    since_timestamp: int | None = None,
) -> AsyncIterator[dict]:
    # 1. Fetch archive list
    archives_url = f"https://api.chess.com/pub/player/{username}/games/archives"
    resp = await client.get(archives_url, headers={"User-Agent": USER_AGENT})
    if resp.status_code == 404:
        raise ValueError(f"chess.com user '{username}' not found")
    resp.raise_for_status()
    archives = resp.json()["archives"]  # list of monthly URLs

    for archive_url in archives:
        # Filter out months before since_timestamp if incremental
        # archive_url looks like: .../games/2024/03
        if since_timestamp and _archive_before_timestamp(archive_url, since_timestamp):
            continue

        await asyncio.sleep(0.15)  # 150ms between requests
        month_resp = await client.get(archive_url, headers={"User-Agent": USER_AGENT})
        if month_resp.status_code == 429:
            await asyncio.sleep(60)
            month_resp = await client.get(archive_url, headers={"User-Agent": USER_AGENT})
        month_resp.raise_for_status()

        for game in month_resp.json().get("games", []):
            if game.get("rules", "chess") != "chess":  # filter non-Standard
                continue
            yield game
```

### Pattern 4: lichess NDJSON Streaming

**What:** Use `httpx.AsyncClient.stream()` with `aiter_lines()` to consume the NDJSON response line by line without buffering the full body.

**When to use:** Always for lichess — they stream the response; buffering would exhaust memory for users with many games.

```python
# Source: httpx docs (python-httpx.org/async) + lichess API docs
async def fetch_lichess_games(
    client: httpx.AsyncClient,
    username: str,
    since_ms: int | None = None,
) -> AsyncIterator[dict]:
    params = {
        "perfType": "ultraBullet,bullet,blitz,rapid,classical",
        "moves": "true",
        "tags": "true",
        "clocks": "false",
        "evals": "false",
        "opening": "true",
    }
    if since_ms:
        params["since"] = str(since_ms)

    url = f"https://lichess.org/api/games/user/{username}"
    headers = {"Accept": "application/x-ndjson"}

    async with client.stream("GET", url, params=params, headers=headers,
                              timeout=300.0) as response:
        if response.status_code == 404:
            raise ValueError(f"lichess user '{username}' not found")
        response.raise_for_status()
        async for line in response.aiter_lines():
            if not line.strip():
                continue
            try:
                game = json.loads(line)
            except json.JSONDecodeError:
                continue
            if game.get("variant", {}).get("key", "standard") != "standard":
                continue
            yield game
```

### Pattern 5: Bulk Insert with ON CONFLICT DO NOTHING

**What:** Use PostgreSQL's `INSERT ... ON CONFLICT DO NOTHING` for idempotent game inserts. `game_positions` rows are inserted after getting the game's DB primary key.

**When to use:** Every import — deduplication is handled at DB level via the `(platform, platform_game_id)` unique constraint.

```python
# Source: SQLAlchemy 2.0 docs + PostgreSQL dialect
from sqlalchemy.dialects.postgresql import insert as pg_insert

async def bulk_insert_games(
    session: AsyncSession,
    game_rows: list[dict],
) -> list[int]:
    """Insert games, skipping duplicates. Returns list of new game IDs."""
    stmt = pg_insert(Game).values(game_rows)
    stmt = stmt.on_conflict_do_nothing(
        constraint="uq_games_platform_game_id"
    ).returning(Game.id)
    result = await session.execute(stmt)
    await session.flush()
    return [row[0] for row in result.fetchall()]
```

### Anti-Patterns to Avoid

- **Inserting game_positions for duplicate games:** Only insert positions for games that were actually inserted (new). Check `RETURNING id` and only process those.
- **Buffering entire lichess response:** Never `resp.json()` on a lichess games stream — `aiter_lines()` is mandatory.
- **Awaiting each game insert individually:** Use bulk insert; per-game commits kill performance for users with thousands of games.
- **Blocking the event loop with `time.sleep()`:** Use `asyncio.sleep()` for delays.
- **Using `board.fen()` for position matching:** Use `board.board_fen()` per CLAUDE.md — `fen()` includes castling/en passant state.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Duplicate detection | Custom dedupe query before insert | `ON CONFLICT DO NOTHING` with unique constraint | Already enforced at DB layer; race-condition safe |
| Zobrist hash computation | Custom hash function | `hashes_for_game()` from `app/services/zobrist.py` | Already built and tested in Phase 1 |
| PGN parsing | Custom PGN tokenizer | `chess.pgn.read_game()` from python-chess | Handles all PGN edge cases including headers, comments, variations |
| Time control parsing | Custom string parser | `_parse_time_control()` utility function | Straightforward but error-prone; implement once in a shared utility |
| NDJSON streaming | Custom line buffering | `httpx aiter_lines()` | httpx handles chunked encoding, keep-alive, and partial lines correctly |

**Key insight:** The hardest parts (Zobrist hashing, PGN parsing, deduplication) are already solved. Phase 2 is primarily glue code connecting platform APIs to the existing data layer.

---

## Common Pitfalls

### Pitfall 1: chess.com User-Agent Requirement
**What goes wrong:** Requests without a recognizable `User-Agent` header may be blocked or throttled with no documentation error.
**Why it happens:** chess.com uses User-Agent to identify and contact developers if their app misbehaves.
**How to avoid:** Always set `User-Agent: Chessalytics/1.0 (contact@example.com)` on every chess.com request.
**Warning signs:** 403 or 429 responses where you'd expect 200.

### Pitfall 2: lichess `since`/`until` Parameters Are Milliseconds
**What goes wrong:** Passing Unix seconds (e.g., `1700000000`) instead of milliseconds (e.g., `1700000000000`) silently fetches all games from 1970.
**Why it happens:** Documented in CLAUDE.md; lichess deviates from the Unix seconds convention.
**How to avoid:** Always multiply Python `datetime.timestamp()` by 1000 before passing to lichess. Unit test this conversion.
**Warning signs:** Incremental sync fetches way more games than expected.

### Pitfall 3: chess.com `rules` Field for Variant Filtering
**What goes wrong:** Importing Chess960, bughouse, etc. games that confuse position analysis.
**Why it happens:** chess.com archives include all variants by default.
**How to avoid:** Filter `game["rules"] != "chess"` — skip anything that isn't standard chess. The field values are: `"chess"`, `"chess960"`, `"bughouse"`, `"kingofthehill"`, `"threecheck"`, `"crazyhouse"`.
**Warning signs:** Position hashes for Chess960 will have wrong starting positions.

### Pitfall 4: lichess Variant Filtering Requires Nested Access
**What goes wrong:** lichess game objects have `"variant": {"key": "standard", "name": "Standard"}` — not a flat string.
**Why it happens:** lichess uses a richer object structure than chess.com.
**How to avoid:** Check `game["variant"]["key"] == "standard"` (not `game["variant"] == "standard"`).
**Warning signs:** `KeyError` or wrong variant filtering.

### Pitfall 5: Inserting game_positions for Already-Existing Games
**What goes wrong:** `ON CONFLICT DO NOTHING` silently skips duplicate games, but if you then insert game_positions using the original `game_id` from the dict (not the DB ID), you'll create orphaned position rows referencing non-existent games or double the positions for existing games.
**Why it happens:** The `RETURNING id` clause only returns IDs for actually-inserted rows. Re-imported duplicates return no rows.
**How to avoid:** Only call `hashes_for_game()` and insert `game_positions` for game IDs returned by `RETURNING id`. Skip duplicates entirely.
**Warning signs:** game_positions count grows on re-sync even though game count is unchanged.

### Pitfall 6: chess.com `end_time` vs lichess `createdAt` Timestamps
**What goes wrong:** chess.com `end_time` is Unix seconds. lichess `createdAt` and `lastMoveAt` are Unix milliseconds. Mixing them produces wildly wrong `played_at` values.
**Why it happens:** Each platform uses different timestamp conventions.
**How to avoid:** For chess.com: `datetime.fromtimestamp(game["end_time"], tz=timezone.utc)`. For lichess: `datetime.fromtimestamp(game["createdAt"] / 1000, tz=timezone.utc)`.
**Warning signs:** `played_at` values in 1970 or far future.

### Pitfall 7: Time Control Bucketing Edge Cases
**What goes wrong:** Incorrect bucket for games with increment (e.g., `180+2` gives estimated 180 + 40*2 = 260s, correctly "blitz" — but naive parsing of `180` alone would say "bullet").
**Why it happens:** Increment adds time per move; the effective duration is longer than the base time.
**How to avoid:** Estimated game duration = `base_seconds + increment_seconds * 40` (standard 40-move estimate). Apply the thresholds to the estimated duration, not base time alone.
**Warning signs:** Bullet games where users played increment time controls.

### Pitfall 8: Concurrency — Duplicate Import Jobs
**What goes wrong:** User clicks "import" twice, creating two concurrent jobs that both write the same games, causing race conditions.
**Why it happens:** No guard on job creation.
**How to avoid:** Before creating a new job, check `_jobs` for any in-progress job for `(user_id, platform)`. Return the existing job ID if found.
**Warning signs:** Doubled game counts, unique constraint errors in logs.

---

## Code Examples

Verified patterns from official sources and project context:

### chess.com Archive List Endpoint
```python
# Source: chess.com Published-Data API documentation
# GET https://api.chess.com/pub/player/{username}/games/archives
# Returns: {"archives": ["https://api.chess.com/pub/player/USER/games/2024/01", ...]}

# GET https://api.chess.com/pub/player/{username}/games/{YYYY}/{MM}
# Returns: {"games": [{game_obj}, ...]}
# game fields: url, pgn, fen, start_time, end_time, rated, time_control,
#              time_class, rules, white{username, rating, result}, black{...},
#              eco (opening URL), uuid
```

### lichess Game Export Endpoint
```python
# Source: lichess API docs (lichess.org/api)
# GET https://lichess.org/api/games/user/{username}
# Headers: Accept: application/x-ndjson
# Params: since (ms), until (ms), perfType, moves, tags, opening, max
# Returns: NDJSON stream, one game per line
#
# Each line is a JSON object with fields:
# id, rated, variant{key, name}, speed, perf, createdAt (ms), lastMoveAt (ms),
# status, players{white{user{name, id}, rating}, black{...}},
# winner ("white"|"black"), moves (space-separated UCI), opening{eco, name, ply},
# clock{initial (seconds), increment (seconds), totalTime}
```

### Time Control Bucketing
```python
# Source: CLAUDE.md constraints
def parse_time_control(tc_str: str) -> tuple[str | None, int | None]:
    """Parse '600+5' -> ('blitz', 800). Returns (bucket, estimated_seconds)."""
    if not tc_str or tc_str == "-":
        return None, None
    try:
        if "+" in tc_str:
            base, increment = map(int, tc_str.split("+"))
        elif "/" in tc_str:
            # Daily format like "1/259200" — skip or mark as "classical"
            return "classical", None
        else:
            base, increment = int(tc_str), 0
    except ValueError:
        return None, None

    estimated = base + increment * 40
    if estimated <= 180:
        return "bullet", estimated
    elif estimated <= 600:
        return "blitz", estimated
    elif estimated <= 1800:
        return "rapid", estimated
    else:
        return "classical", estimated
```

### SQLAlchemy Bulk Insert Pattern
```python
# Source: SQLAlchemy 2.0 docs (docs.sqlalchemy.org) + PostgreSQL dialect
from sqlalchemy.dialects.postgresql import insert as pg_insert

async def insert_games_skip_duplicates(
    session: AsyncSession, rows: list[dict]
) -> list[int]:
    if not rows:
        return []
    stmt = (
        pg_insert(Game)
        .values(rows)
        .on_conflict_do_nothing(constraint="uq_games_platform_game_id")
        .returning(Game.id)
    )
    result = await session.execute(stmt)
    return [r[0] for r in result.fetchall()]
```

### Job Status Polling Endpoint
```python
# Source: FastAPI + project patterns
@router.get("/imports/{job_id}", response_model=ImportStatusResponse)
async def get_import_status(job_id: str):
    state = import_service.get_job(job_id)
    if state is None:
        # Check DB for completed/failed jobs (survived process restart)
        db_job = await import_job_repo.get(job_id)
        if db_job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        return ImportStatusResponse.from_db(db_job)
    return ImportStatusResponse.from_state(state)
```

---

## API Endpoint Design

### Recommended Endpoint Structure

```
POST /imports
Body: { "platform": "chess.com" | "lichess", "username": "...", "user_id": ... }
Response: { "job_id": "uuid", "status": "pending" }

GET /imports/{job_id}
Response: {
    "job_id": "uuid",
    "platform": "chess.com",
    "username": "...",
    "status": "pending" | "in_progress" | "completed" | "failed",
    "games_fetched": 142,
    "games_imported": 138,  # new games (skipped duplicates)
    "error": null | "Invalid username"
}
```

**Re-sync:** Use the same `POST /imports` endpoint. The service checks for a `last_synced_at` in `import_jobs` for this `(user_id, platform, username)` and sets `since` accordingly. The client doesn't need to know — it just POSTs again.

**Concurrency guard:** If an in-progress job exists for `(user_id, platform)`, return it immediately with its current status rather than starting a duplicate.

---

## Database: import_jobs Table

A lightweight table to track terminal state and enable incremental sync:

```python
# New model: app/models/import_job.py
class ImportJob(Base):
    __tablename__ = "import_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # UUID
    user_id: Mapped[int] = mapped_column(nullable=False, index=True)
    platform: Mapped[str] = mapped_column(String(20), nullable=False)
    username: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # terminal only
    games_fetched: Mapped[int] = mapped_column(nullable=False, default=0)
    games_imported: Mapped[int] = mapped_column(nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
    last_synced_at: Mapped[datetime.datetime | None]  # for incremental sync
    started_at: Mapped[datetime.datetime] = mapped_column(server_default=func.now())
    completed_at: Mapped[datetime.datetime | None]
```

**Alembic migration required** for this new table.

---

## chess.com Platform Normalization

chess.com JSON game object → Game model mapping:

| chess.com field | Game model field | Notes |
|----------------|------------------|-------|
| `uuid` | `platform_game_id` | Unique game identifier |
| `url` | `platform_url` | Direct link to game |
| `pgn` | `pgn` | Full PGN string |
| `rules` | filter: skip if `!= "chess"` | Standard variant only |
| `white.result` / `black.result` | `result` | Normalize to `"1-0"` / `"0-1"` / `"1/2-1/2"` |
| `white.username` vs user's username | `user_color` | Compare to determine `"white"` or `"black"` |
| `white.rating` or `black.rating` | `user_rating` | Depends on user_color |
| `time_control` | `time_control_str`, `time_control_bucket`, `time_control_seconds` | Parse with `parse_time_control()` |
| `rated` | `rated` | Boolean |
| `end_time` (Unix seconds) | `played_at` | `datetime.fromtimestamp(end_time, tz=timezone.utc)` |
| `eco` (URL) | `opening_eco`, `opening_name` | Extract ECO code from URL; name requires extra parsing |
| `"chess.com"` | `platform` | Literal string |

chess.com `result` field uses their own strings: `"win"`, `"checkmated"`, `"resigned"`, `"timeout"`, `"agreed"`, `"stalemate"`, `"insufficient"`, `"repetition"`, `"timevsinsufficient"`, `"50move"`. Map to `"1-0"` / `"0-1"` / `"1/2-1/2"` based on `user_color`.

---

## lichess Platform Normalization

lichess NDJSON game object → Game model mapping:

| lichess field | Game model field | Notes |
|--------------|------------------|-------|
| `id` | `platform_game_id` | e.g., `"q7ZvsdUF"` |
| `"https://lichess.org/{id}"` | `platform_url` | Constructed from ID |
| `moves` (space-separated) + header tags | `pgn` | Must reconstruct PGN from moves + metadata for hashing |
| `variant.key` | filter: skip if `!= "standard"` | Standard variant only |
| `winner` | `result` | `"white"` → `"1-0"`, `"black"` → `"0-1"`, absent → `"1/2-1/2"` |
| players.white/black username vs import username | `user_color` | Compare to determine color |
| player rating | `user_rating` / `opponent_rating` | From `players.{color}.rating` |
| `clock.initial` + `clock.increment` | `time_control_str`, bucket, seconds | Format as `"{initial}+{increment}"` for `time_control_str` |
| `rated` | `rated` | Boolean |
| `createdAt` (ms) | `played_at` | `datetime.fromtimestamp(createdAt / 1000, tz=timezone.utc)` |
| `opening.eco` / `opening.name` | `opening_eco`, `opening_name` | Present if `opening=true` parameter used |
| `"lichess"` | `platform` | Literal string |

**Critical:** lichess NDJSON does not include a ready-made PGN string by default. To call `hashes_for_game(pgn_text)`, you need a valid PGN. Options:
1. Request with `pgnInJson=true` — adds a `"pgn"` field to each NDJSON object (recommended).
2. Reconstruct PGN manually from `moves` field + metadata headers.

**Recommendation:** Use `pgnInJson=true` parameter on the lichess request. This is the cleanest approach and avoids manual PGN reconstruction.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Celery for all background jobs | asyncio.create_task for I/O-bound single-worker jobs | Widespread in FastAPI ecosystem ~2022+ | No Redis/RabbitMQ dependency for simple cases |
| FastAPI BackgroundTasks for everything | BackgroundTasks for fire-and-forget; asyncio.create_task for trackable jobs | FastAPI best practices ~2023+ | Proper status tracking without external deps |
| SQLAlchemy `bulk_save_objects` | `session.execute(insert(...).values([...]))` | SQLAlchemy 2.0 (2023) | Faster, async-compatible, supports RETURNING |

**Deprecated/outdated:**
- `session.bulk_save_objects()`: Not available in async sessions; replaced by `session.execute(insert(...))`.
- `requests` library: Blocked for this project (CLAUDE.md). Use `httpx.AsyncClient`.
- `berserk` lichess client: Blocked for this project (CLAUDE.md). Use direct `httpx` calls.

---

## Open Questions

1. **lichess `pgnInJson` response size**
   - What we know: The parameter adds full PGN text to each NDJSON line, which increases payload size.
   - What's unclear: Whether this significantly impacts streaming performance for users with 10,000+ games.
   - Recommendation: Use `pgnInJson=true` for simplicity. If performance is an issue, switch to manual PGN reconstruction from the `moves` field in a follow-up.

2. **chess.com rate limit specifics**
   - What we know: Sequential access is unlimited; parallel requests may trigger 429s.
   - What's unclear: The exact threshold for sequential requests before rate limiting kicks in.
   - Recommendation: Use 150ms delay between month requests. On 429, back off 60 seconds. This is conservative and safe.

3. **Import job persistence on restart**
   - What we know: In-memory jobs are lost on process restart; DB records terminal states only.
   - What's unclear: How to handle jobs that were `in_progress` when the server restarted.
   - Recommendation: On startup, check DB for any jobs with no `completed_at` and mark them `failed` with `error_message="Server restarted"`. This is honest and lets users re-trigger.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.23.x |
| Config file | `pyproject.toml` (`asyncio_mode = "auto"`) |
| Quick run command | `uv run pytest tests/test_import*.py -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| IMP-01 | chess.com games fetched and normalized correctly | unit | `uv run pytest tests/test_chesscom_client.py -x` | Wave 0 |
| IMP-01 | Invalid chess.com username returns 404/error | unit | `uv run pytest tests/test_chesscom_client.py::test_invalid_username -x` | Wave 0 |
| IMP-02 | lichess games fetched via NDJSON and normalized | unit | `uv run pytest tests/test_lichess_client.py -x` | Wave 0 |
| IMP-02 | Invalid lichess username returns error | unit | `uv run pytest tests/test_lichess_client.py::test_invalid_username -x` | Wave 0 |
| IMP-03 | Re-sync uses `since` timestamp, no duplicates imported | unit | `uv run pytest tests/test_import_service.py::test_incremental_sync -x` | Wave 0 |
| IMP-03 | `last_synced_at` stored after successful import | unit | `uv run pytest tests/test_import_service.py::test_last_synced_at -x` | Wave 0 |
| IMP-04 | Job status transitions from pending → in_progress → completed | unit | `uv run pytest tests/test_import_service.py::test_job_lifecycle -x` | Wave 0 |
| IMP-04 | Status endpoint returns 404 for unknown job ID | unit | `uv run pytest tests/test_imports_router.py::test_unknown_job -x` | Wave 0 |
| INFRA-02 | POST /imports returns immediately (does not block) | integration | `uv run pytest tests/test_imports_router.py::test_nonblocking -x` | Wave 0 |
| IMP-01+02 | Variant filtering skips Chess960 / non-standard games | unit | `uv run pytest tests/test_normalization.py::test_variant_filter -x` | Wave 0 |
| IMP-01+02 | Time control bucketing correct for all categories | unit | `uv run pytest tests/test_normalization.py::test_time_control_bucket -x` | Wave 0 |
| IMP-01+02 | Duplicate games not inserted (ON CONFLICT DO NOTHING) | unit | `uv run pytest tests/test_game_repository.py::test_duplicate_skip -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/ -x -q`
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
All test files need to be created. Key fixtures needed:

- [ ] `tests/test_chesscom_client.py` — covers IMP-01 normalization and error handling
- [ ] `tests/test_lichess_client.py` — covers IMP-02 normalization and NDJSON parsing
- [ ] `tests/test_import_service.py` — covers IMP-03, IMP-04 job lifecycle
- [ ] `tests/test_imports_router.py` — covers INFRA-02 non-blocking, IMP-04 polling
- [ ] `tests/test_normalization.py` — covers variant filtering, time control bucketing, result mapping
- [ ] `tests/test_game_repository.py` — covers bulk insert + ON CONFLICT DO NOTHING
- [ ] `tests/conftest.py` — add `AsyncSession` mock fixture (extend existing conftest)
- [ ] No new framework install needed — pytest + pytest-asyncio already in dev-dependencies

---

## Sources

### Primary (HIGH confidence)
- chess.com Published-Data API (chessnerd.net/chesscom-api.html) — archive endpoints, game fields, rate limit notes
- lichess API tips (lichess.org/page/api-tips) — rate limiting behavior, 429 handling
- lichess API YAML spec (github.com/lichess-org/api) — `/api/games/user` parameters including `since` (ms), `perfType`, `pgnInJson`
- httpx async docs (python-httpx.org/async/) — `stream()`, `aiter_lines()` patterns
- FastAPI background tasks docs (fastapi.tiangolo.com/tutorial/background-tasks/) — BackgroundTasks limitations
- SQLAlchemy 2.0 DML docs (docs.sqlalchemy.org/en/20/orm/queryguide/dml.html) — bulk insert with `RETURNING`
- Project source: `app/services/zobrist.py`, `app/models/game.py`, `app/models/game_position.py`, `app/core/database.py`

### Secondary (MEDIUM confidence)
- lichess NDJSON game structure (WebSearch cross-referenced with API YAML) — `variant.key`, `clock`, `createdAt` ms timestamps, `players` structure
- chess.com `rules` field values (WebSearch + chessnerd.net) — "chess", "chess960", "bughouse", etc.
- asyncio.create_task for job tracking pattern (multiple 2024-2025 FastAPI articles) — UUID job dict approach

### Tertiary (LOW confidence)
- chess.com `end_time` being Unix seconds (inferred from standard practice + WebSearch) — flag for validation during implementation
- Exact chess.com rate limit thresholds (only "sequential is unlimited" confirmed) — use conservative 150ms delay

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; all libraries already in project
- Architecture: HIGH — asyncio.create_task + in-memory dict is a well-established pattern for this scale
- chess.com API: MEDIUM-HIGH — endpoint structure confirmed; some field details inferred from secondary sources
- lichess API: MEDIUM-HIGH — parameters confirmed via YAML spec; NDJSON structure confirmed via multiple sources
- Pitfalls: HIGH — most from CLAUDE.md constraints + verified API behavior

**Research date:** 2026-03-11
**Valid until:** 2026-04-11 (APIs are stable; chess.com and lichess rarely change their game export APIs)
