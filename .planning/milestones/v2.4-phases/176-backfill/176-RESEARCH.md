# Phase 176: Backfill - Research

**Researched:** 2026-07-17
**Domain:** Backend eval-queue lottery + drain-tick completion-marker correctness (PostgreSQL/SQLAlchemy async)
**Confidence:** HIGH — every claim below is `[VERIFIED: codebase read]` against the actual file on disk today (2026-07-17), not training-data recall. No external library research was needed; this phase adds zero new dependencies.

## Summary

Phase 176 is a small, surgical addition to an already-mature ES-lottery eval-queue system. All five CONTEXT.md decisions (D-01..D-05) are locked and this research confirms every cited code shape still matches, with one naming drift (CONTEXT.md's `run_one_full_eval_tick` is actually the private `_full_drain_tick()`). The two things a planner must get exactly right are (1) the new `_claim_tier4_bestmove` predicate — it MUST explicitly exclude `lichess_evals_at IS NOT NULL` games even though `full_pv_completed_at` is stamped for those games too (174-06 unified the pass), and (2) the Maia-absent stamping guardrail — `_build_best_move_candidates` returns `[]` both when Maia legitimately found zero qualifying plies AND when Maia is entirely absent (no onnxruntime), so the stamp decision cannot be inferred from row count and needs an independent `is_maia_available()` check threaded into the completion decision.

**Primary recommendation:** Add the guardrail and the stamp in exactly one place — `eval_apply.py`'s `apply_completion_decision` (the single choke-point both `_full_drain_tick` and the remote-worker's `_apply_atomic_submit` already funnel through) — rather than threading a new parameter through both call sites' business logic. This mirrors the existing `_mark_full_pv_completed`/`_mark_full_evals_completed` pattern exactly and requires zero changes to either caller beyond one new `maia_available` bool.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Tier-4b ES lottery pick (`_claim_tier4_bestmove`) | API/Backend (service layer) | Database (partial index) | Pure SQL-lottery service function, mirrors `_claim_tier4_blob` exactly |
| Completion-marker stamp (`best_moves_completed_at`) | API/Backend (`eval_apply.py`) | Database (new column) | Single write choke-point shared by both drain lanes |
| Maia-absent guardrail | API/Backend (`maia_engine.py` + `eval_apply.py`) | — | In-process singleton state check, no DB/network involved |
| Config gate (`BEST_MOVE_BACKFILL_ENABLED`) | API/Backend (`config.py`) | — | Pydantic Settings, mirrors `EVAL_AUTO_DRAIN_ENABLED` |
| Migration (column + index + one-time stamp) | Database | — | Alembic-owned schema change |

No frontend, CDN, or client-tier capability is touched by this phase — it is 100% backend batch-job plumbing (BACK-01 has no UI surface).

## Standard Stack

No new libraries. This phase reuses:
- SQLAlchemy 2.x async (`sa.text` CTEs, bound params) — already the project standard.
- The existing `onnxruntime` isolated `maia-inference` uv group (Phase 174, GEMS-06) — no new dependency, only a new *public accessor* into the existing module.

## Package Legitimacy Audit

Not applicable — zero new external packages are introduced by this phase.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| BACK-01 | The existing analyzed corpus gains best-move rows opportunistically via the tier-4 lottery pattern (global + random, no deterministic sweep, no ETA); backfill lottery keying decided at phase planning | §"Verified: tier-4b lottery copy target" + §"Verified: completion-marker + partial-index pattern" below give the exact predicate, recency column, and index shape for the new `_claim_tier4_bestmove` rung (D-02), keyed off the new `best_moves_completed_at IS NULL` self-termination signal (D-01) |

</phase_requirements>

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Add a new **nullable `best_moves_completed_at` timestamp** column on `games`. Stamped by the drain tick whenever a game goes through the best-move pass — on **both** the backfill path AND the existing go-forward path. Self-termination predicate: `full_pv_completed_at IS NOT NULL AND best_moves_completed_at IS NULL`. Rejected: `NOT EXISTS(game_best_moves)` (ambiguous — legitimate zero-candidate games would never self-terminate); a temporal cutoff on `full_pv_completed_at` (fragile).
- **D-02:** Add a **new parallel tier-4b rung** `_claim_tier4_bestmove` — a copy of `_claim_tier4_blob`'s two-stage ES weighted (user → game) lottery, same plain-SELECT/no-lock shape, with the D-01 predicate — ordered **after** `_claim_tier4_blob` in the bundled `scope=None` path of `claim_eval_job`. Blob backfill drains first; best-move backfill uses leftover backend capacity. Rejected: OR-broadening the existing tier-4-blob rung (would risk handing workers games whose only gap is best-moves, which workers cannot fill).
- **D-02-fact (decisive, verified):** Best-move rows require Maia inference; `onnxruntime`/`numpy` are excluded from `Dockerfile.worker`. Remote workers physically cannot produce `maia_prob`. Best-move backfill **must** run on the backend in-process drain and **requires zero worker changes**.
- **D-03:** **Engine-only** predicate `lichess_evals_at IS NULL`. `lichess_evals_at IS NULL` = "games *we* analyzed with our own Stockfish" = ALL chess.com games + engine-analyzed lichess/bot games (the dominant ~94% of the 176 population). Only lichess games that arrived WITH imported evals (`lichess_evals_at IS NOT NULL`) are out — those are 174-07's job.
- **D-03-locked:** Whole-corpus draining via ES floors + recency weighting is locked by BACK-01 and the tier-4 precedent — not re-litigated. Guest exclusion (QUEUE-08) is inherited from the shared ES building blocks.
- **D-04:** In the **same migration** that adds `best_moves_completed_at`, run a one-time stamp: set it (to `full_pv_completed_at` or `now()`) `WHERE EXISTS` a `game_best_moves` row for the game.
- **D-05:** Add a **dedicated `BEST_MOVE_BACKFILL_ENABLED`** settings bool (default `False`). The tier-4b rung checks **both** it AND `EVAL_AUTO_DRAIN_ENABLED`.

### Claude's Discretion

- **Backfill re-runs the full pass, not Maia-on-stored-data** — route the tier-4b claim through the same drain tick (`_full_drain_tick`/`apply_full_eval`), exactly what it already does for go-forward games and lichess backfill (174-07).
- **Maia-absent stamping guardrail (correctness — verify in research):** the drain tick must only stamp `best_moves_completed_at` when Maia actually ran. Confirm this applies to BOTH the backfill and go-forward stamping.
- Exact column type (`TIMESTAMPTZ`), index name, and whether to reuse the `TIER4_*` half-life/floor constants or introduce `BEST_MOVE_*` ones — planner decides (reusing tier-4's is the likely default).
- **SC3 verification approach:** coverage growth is measurable via a snapshot diff of `count(DISTINCT game_id)` in `game_best_moves` (or count of stamped games) over time — no 100%/ETA promise.

### Deferred Ideas (OUT OF SCOPE)

- Gem/great threshold calibration against real per-game frequency (GEMS-07, future requirement, not 176).
- Any Maia-on-workers escape hatch (174 D-02, explicitly rejected).

</user_constraints>

## Architecture Patterns

### System Architecture Diagram

```
                     ┌─────────────────────────────────────────────┐
                     │        run_full_eval_drain() loop            │
                     │        (app/services/eval_drain.py)          │
                     └───────────────────┬───────────────────────────┘
                                          │ each tick
                                          ▼
                     ┌─────────────────────────────────────────────┐
                     │           _full_drain_tick()                  │
                     │  Step 0: yield gate (import/entry-ply active)│
                     │  Step 1: claim_eval_job(scope=None)  ◄────────┼─── ClaimedJob(tier, game_id, ...)
                     └───────────────────┬───────────────────────────┘
                                          │
                                          ▼
        ┌─────────────────────────────────────────────────────────────────┐
        │            claim_eval_job() bundled ladder (eval_queue_service.py)│
        │                                                                   │
        │  tier-1 (_claim_queued_job, SKIP LOCKED)                         │
        │    │ empty                                                       │
        │    ▼                                                             │
        │  tier-3 (_claim_tier3_derived — needs-engine ES lottery          │
        │           + residual lichess-PV-backfill fallback, 174-07)      │
        │    │ empty, gated by EVAL_AUTO_DRAIN_ENABLED                     │
        │    ▼                                                             │
        │  tier-4  (_claim_tier4_blob — NULL-blob ES lottery)              │
        │    │ empty                                                       │
        │    ▼                                                             │
        │  tier-4b (_claim_tier4_bestmove — NEW, D-02) ◄── gated by         │
        │           BEST_MOVE_BACKFILL_ENABLED AND EVAL_AUTO_DRAIN_ENABLED │
        └─────────────────────────────────────────────────────────────────┘
                                          │ ClaimedJob(tier=TIER_BESTMOVE_BACKFILL)
                                          ▼
                     ┌─────────────────────────────────────────────┐
                     │  _full_drain_tick Steps 2-3: load PGN,        │
                     │  gather asyncio Stockfish multipv=2 (NO       │
                     │  session open), build best_move_rows via      │
                     │  _build_best_move_candidates (Maia inference) │
                     └───────────────────┬───────────────────────────┘
                                          ▼
                     ┌─────────────────────────────────────────────┐
                     │  apply_full_eval() → apply_completion_decision│
                     │  (eval_apply.py) — SHARED by _full_drain_tick │
                     │  AND eval_remote.py's _apply_atomic_submit     │
                     │                                                │
                     │  maia_available = maia_engine.is_maia_available()│
                     │  Path A/C: stamp full_evals/full_pv_completed_at│
                     │            + best_moves_completed_at IFF        │
                     │            maia_available (NEW guardrail)       │
                     └─────────────────────────────────────────────┘
```

### Recommended Project Structure

No new files. All changes land in existing modules:
```
app/
├── core/config.py              # + BEST_MOVE_BACKFILL_ENABLED
├── models/
│   ├── eval_jobs.py             # + TIER_BESTMOVE_BACKFILL constant
│   └── game.py                  # + best_moves_completed_at column + partial index
├── services/
│   ├── eval_queue_service.py    # + _claim_tier4_bestmove, + tier-4b rung in claim_eval_job
│   ├── eval_apply.py            # + _mark_best_moves_completed, + maia_available param
│   └── maia_engine.py           # + is_maia_available() public accessor
alembic/versions/
└── <new>_phase_176_best_moves_completed_at.py   # column + index + D-04 one-time stamp
```

### Pattern 1: Two-stage ES weighted lottery rung (copy of `_claim_tier4_blob`)

**What:** A near-verbatim copy of `_claim_tier4_blob` (`app/services/eval_queue_service.py:555-654`), swapping only the predicate and (optionally) the recency-anchor column.

**Verified signature/shape** `[VERIFIED: eval_queue_service.py]`:
```python
async def _claim_tier4_bestmove(
    session: AsyncSession,
) -> tuple[int, int] | None:
    """Tier-4b spare-capacity lottery: pick one PV-complete non-guest engine game
    still missing its best-move pass (D-01/D-02/D-03)."""
    tau_u_seconds = TIER4_USER_RECENCY_HALF_LIFE_DAYS / math.log(2) * 86400.0
    floor_u = TIER4_USER_WEIGHT_FLOOR
    tau_g_seconds = TIER4_GAME_RECENCY_HALF_LIFE_DAYS / math.log(2) * 86400.0
    floor_g = TIER4_GAME_WEIGHT_FLOOR

    picked_user_id = await _es_weighted_user_pick(
        session,
        candidate_exists_sql="""
                SELECT 1 FROM games g
                WHERE g.user_id = u.id
                  AND g.full_pv_completed_at IS NOT NULL
                  AND g.best_moves_completed_at IS NULL
                  AND g.lichess_evals_at IS NULL
        """,
        recency_col_sql="u.last_activity",
        tau_seconds=tau_u_seconds,
        floor=floor_u,
    )
    if picked_user_id is None:
        return None

    game_id = await _es_weighted_game_pick(
        session,
        game_where_sql=(
            "g.user_id = :picked_user"
            " AND g.full_pv_completed_at IS NOT NULL"
            " AND g.best_moves_completed_at IS NULL"
            " AND g.lichess_evals_at IS NULL"
        ),
        recency_col_sql="g.full_pv_completed_at",
        tau_seconds=tau_g_seconds,
        game_floor=floor_g,
        tc_weights=GAME_TC_WEIGHTS,
        extra_params={"picked_user": picked_user_id},
    )
    if game_id is None:
        return None
    return game_id, picked_user_id
```

**Critical, non-obvious correctness detail (verified against 174-06/174-07):** `full_pv_completed_at` is stamped for BOTH engine games AND lichess-eval games (174-06 unified the full pass so every game type gets a best-move attempt). This means `full_pv_completed_at IS NOT NULL` alone is **not** an engine-games-only filter — it is a superset covering both populations. The explicit `AND g.lichess_evals_at IS NULL` clause in the predicate above is load-bearing (D-03): without it, tier-4b would contend with 174-07's residual fallback for the SAME lichess-eval games, and — worse — pointlessly re-drain games whose `best_moves_completed_at` situation isn't actually 176's problem (D-03 explicitly assigns lichess-eval-game backfill to 174-07).

**Recency-column choice:** `_claim_tier4_blob`'s Stage 2 anchors on `g.full_evals_completed_at` (the timestamp of the event that made the game eligible). The direct analog for tier-4b is `g.full_pv_completed_at` (the timestamp of the event — 176's own predicate's gating column — that made THIS game eligible for best-move backfill). This mirrors the existing pattern exactly (recency anchor = the column the WHERE clause gates on).

**Tier constant:** `app/models/eval_jobs.py` declares `TIER_EXPLICIT=1`, `TIER_IDLE_BACKLOG=3`, `TIER_BLOB_BACKFILL=4` `[VERIFIED: eval_jobs.py]`. Add `TIER_BESTMOVE_BACKFILL: int = 5`, updating the module docstring's tier-list comment to match (same style as the existing 3 constants). `ClaimedJob.tier` is currently an inert field downstream (`_ = tier  # tier is available for Phase 118 tier-aware cache logic` in `_full_drain_tick`) — safe to extend with no ripple effects.

**Where the new rung slots into `claim_eval_job`** `[VERIFIED: eval_queue_service.py:757-776]`:
```python
async with async_session_maker() as session:
    blob_pick = await _claim_tier4_blob(session)

if blob_pick is None:
    # Tier-4 blob empty → try tier-4b best-move backfill (D-02, D-05 gate).
    # EVAL_AUTO_DRAIN_ENABLED is already True at this point (checked above);
    # only the dedicated gate needs checking here.
    if not settings.BEST_MOVE_BACKFILL_ENABLED:
        return None
    async with async_session_maker() as session:
        bestmove_pick = await _claim_tier4_bestmove(session)
    if bestmove_pick is None:
        return None
    game_id4b, user_id4b = bestmove_pick
    return ClaimedJob(
        game_id=game_id4b,
        user_id=user_id4b,
        tier=TIER_BESTMOVE_BACKFILL,
        is_lichess_eval_game=False,  # D-03 predicate structurally excludes lichess-eval games
        job_id=None,
    )

game_id4, user_id4 = blob_pick
return ClaimedJob(..., tier=TIER_BLOB_BACKFILL, ...)
```
`is_lichess_eval_game=False` is always correct here by construction (the tier-4b predicate excludes `lichess_evals_at IS NOT NULL` games), unlike `_claim_tier4_blob`'s comment that resolution happens "later in the Plan-03 lease handler" — that deferral was specific to the remote-worker blob-lease flow, which tier-4b never reaches (D-02-fact: backend-only, `_full_drain_tick` is the sole consumer of the bundled `scope=None` path).

**No changes needed to `_full_drain_tick`'s own claim/dispatch logic** — it already calls `claim_eval_job(worker_id=WORKER_ID_SERVER_POOL)` (scope=None, the bundled path) and routes ANY claimed game — tier-1/3/4/4b alike — through the identical Steps 2-5 (load → gather multipv=2 → `_build_best_move_candidates` → `apply_full_eval`). This is what "requires zero worker changes" and "no new eval code" (CONTEXT.md Reusable Assets) means concretely.

### Pattern 2: Completion-marker + guardrail (the crux of D-01's correctness requirement)

**Verified: `_build_best_move_candidates` cannot distinguish "Maia ran, zero candidates" from "Maia absent"** `[VERIFIED: eval_apply.py:1785-1929]`. The function:
- Returns `[]` when there are no out-of-book played==best plies (legitimate zero).
- Returns `[]` when `score_move(...)` returns `None` for every candidate — which happens when `maia_engine._session is None` (no onnxruntime) (`app/services/maia_engine.py:137-138`, `score_move` returns `None` immediately when `_session is None`).
- Wraps the ENTIRE body in a bare `except Exception: return []` (line 1923), so even an unexpected internal error looks identical to "no candidates" from the caller's perspective.

**Therefore row-count-based inference is structurally unsound.** The guardrail needs an independent signal.

**Recommended fix — add a tiny public accessor to `maia_engine.py`:**
```python
def is_maia_available() -> bool:
    """True when the process-wide Maia session was successfully loaded at
    lifespan startup (start_maia). Cheap in-memory check — no I/O."""
    return _session is not None
```
This mirrors the exact pattern the existing test suite already uses directly (`tests/services/test_maia_engine.py` monkeypatches `maia_engine._session = None`/sets it to simulate presence/absence) `[VERIFIED: test_maia_engine.py:33-39]` — a public accessor formalizes what tests already do informally.

**Where to check it and where to stamp — single choke point, `eval_apply.py`:**

`apply_full_eval` (eval_apply.py:1955) is called by BOTH `_full_drain_tick` (eval_drain.py:868) AND `_apply_atomic_submit` (eval_remote.py:1196) `[VERIFIED: both call sites read]`. Both already call `_build_best_move_candidates` themselves and pass `best_move_rows` into `apply_full_eval`:
- `_full_drain_tick`: `best_move_rows = await _build_best_move_candidates(game_id, targets, engine_result_map, second_best_map)` (eval_drain.py:850).
- `_apply_atomic_submit`: `best_move_rows = await _build_best_move_candidates(game_id, targets, engine_result_map, None)` (eval_remote.py:1170) — this is the remote-worker submit path; it runs server-side (Maia still runs on the backend even though Stockfish evals came from a remote worker), so it is ALSO a "go-forward" stamping site per D-01, not just `_full_drain_tick`.

Recommended: inside `apply_full_eval` itself (single call site, zero changes needed in either caller), right where `best_move_rows` is consumed:
```python
# eval_apply.py, inside apply_full_eval, near the existing:
#   if best_move_rows:
#       await _upsert_best_move_rows(write_session, best_move_rows)
from app.services import maia_engine
maia_available = maia_engine.is_maia_available()
if best_move_rows:
    await _upsert_best_move_rows(write_session, best_move_rows)
...
stamp_complete = await apply_completion_decision(
    write_session,
    ...,
    maia_available=maia_available,   # NEW param
)
```
Then in `apply_completion_decision` (eval_apply.py:686-776), add a new `_mark_best_moves_completed` helper mirroring `_mark_full_pv_completed` exactly, called alongside it on Path A and Path C ONLY when `maia_available` is True:
```python
async def _mark_best_moves_completed(session: AsyncSession, game_id: int) -> None:
    """Mark one game's best-move pass as attempted (D-176-01), mirrors _mark_full_pv_completed."""
    now_ts = datetime.now(timezone.utc)
    games_table = Game.__table__
    stmt = (
        update(games_table)
        .where(games_table.c.id == game_id)
        .values(best_moves_completed_at=now_ts)
    )
    await session.execute(stmt)

# Path A:
if failed_ply_count == 0:
    await _mark_full_evals_completed(write_session, game_id)
    await _mark_full_pv_completed(write_session, game_id)
    if maia_available:
        await _mark_best_moves_completed(write_session, game_id)
    stamp_complete = True
# Path C: same addition, alongside the existing two _mark_* calls.
```

**Why this is correct and covers both D-01 requirements ("both the backfill path AND the existing go-forward path"):**
1. **Backfill path** (tier-4b claims): routes through `_full_drain_tick` → `apply_full_eval` → `apply_completion_decision`. Covered.
2. **Go-forward, local drain** (fresh games processed by `_full_drain_tick`): same call chain. Covered.
3. **Go-forward, remote-worker-submitted** (`_apply_atomic_submit`, eval_remote.py): also calls `apply_full_eval` → `apply_completion_decision` with its own `best_move_rows`. Covered — this path is NOT reachable by tier-4b (workers never see `scope=None`), but it IS a go-forward stamping site D-01 requires, and this design covers it "for free" since the check lives in the single shared function rather than being duplicated per-caller.

**One nuance to flag for the planner:** the stamp should be applied **regardless of `is_lichess_eval_game`** — `full_pv_completed_at`/`_build_best_move_candidates` already run for lichess-eval games too (174-06), so a lichess-eval game processed by the go-forward or 174-07-residual-fallback path should ALSO get `best_moves_completed_at` stamped when Maia ran. The `lichess_evals_at IS NULL` exclusion belongs ONLY in the 176 tier-4b **lottery predicate** (to avoid contending with 174-07's population), not in the stamp-writing logic itself, which is source-agnostic (mirrors `full_pv_completed_at`'s own unconditional stamping).

**Zero-candidate legitimacy confirmed** `[VERIFIED: eval_apply.py:1826-1839]`: `_build_best_move_candidates` returns `[]` (not an error) for a game whose out-of-book plies never have played==best, or where none pass `passes_inaccuracy_gate`. This is D-01's explicitly rejected-alternative case (`NOT EXISTS(game_best_moves)` was rejected precisely because it can't distinguish this from Maia-absent) — the guardrail design above correctly stamps `best_moves_completed_at` in this case too (Maia DID run; it just found nothing to score), matching D-01's intent exactly.

## Verified: completion-marker + partial-index pattern

**Column declaration** `[VERIFIED: app/models/game.py:190-196]` — `full_pv_completed_at` is the exact template to copy:
```python
best_moves_completed_at: Mapped[datetime.datetime | None] = mapped_column(
    sa.DateTime(timezone=True), nullable=True
)
```
`sa.DateTime(timezone=True)` is the project's TIMESTAMPTZ convention (matches `full_evals_completed_at`, `full_pv_completed_at`, `lichess_evals_at`, `entry_eval_lease_expiry` — all four use the identical type). No new type needed.

**Index declaration + 174-07's drift lesson (MUST heed this):** `[VERIFIED: app/models/game.py:84-90, 174-07-SUMMARY.md Deviations §1]` — the model's `__table_args__` currently declares `ix_games_lichess_pv_backfill_pending` verbatim matching the migration. 174-07 hit an `alembic check` drift failure because an OLDER index comment claimed partial indexes were "migration-only" when in fact this one (and its predecessor) WAS declared in `__table_args__`. **The rule going forward: every partial index used by a lottery predicate must be declared in BOTH `app/models/game.py`'s `__table_args__` AND the migration, with byte-identical `postgresql_where` text.** Recommended new index (mirrors `ix_games_lichess_pv_backfill_pending`'s shape exactly — single `user_id` column, partial WHERE):
```python
Index(
    "ix_games_bestmove_backfill_pending",
    "user_id",
    postgresql_where=sa.text(
        "full_pv_completed_at IS NOT NULL AND best_moves_completed_at IS NULL"
        " AND lichess_evals_at IS NULL"
    ),
),
```
Run `uv run alembic check` after writing the migration + model change — it must report "No new upgrade operations detected" before the plan is considered done (174-07 precedent).

**Migration chain:** `[VERIFIED: alembic/versions/ directory listing]` current head is `1eda5daba951` (`20260716_171823_..._phase_174_07_lichess_best_move_backfill_.py`). The new migration's `down_revision` must be `"1eda5daba951"`.

**Self-termination predicate confirmed exactly as D-01 states:** `full_pv_completed_at IS NOT NULL AND best_moves_completed_at IS NULL`. Additionally the tier-4b LOTTERY predicate needs `AND lichess_evals_at IS NULL` on top (see Pattern 1 above) — these are two different things: the column's self-termination semantics (D-01, universal) vs. the lottery rung's population scope (D-03, 176-specific). Don't conflate the index predicate with a "the column always implies engine-only" assumption.

## Verified: D-04 one-time backfill stamp

**`game_best_moves` table shape** `[VERIFIED: app/models/game_best_move.py, migration 903b54b77161]`:
```python
class GameBestMove(Base):
    __tablename__ = "game_best_moves"
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"), nullable=False, primary_key=True)
    ply: Mapped[int] = mapped_column(SmallInteger, nullable=False, primary_key=True)
    maia_prob: Mapped[float] = mapped_column(REAL, nullable=False)
    best_cp / best_mate / second_cp / second_mate: SmallInteger, nullable
```
Composite PK `(game_id, ply)`, no `user_id` (position-scoped, not user-scoped — deliberate per the model's own docstring).

**D-04 one-time stamp — raw SQL in the same migration** (mirrors the existing project convention of `op.execute` for data-only migration steps):
```python
def upgrade() -> None:
    op.add_column("games", sa.Column("best_moves_completed_at", sa.DateTime(timezone=True), nullable=True))
    op.execute(
        sa.text("""
            UPDATE games g
            SET best_moves_completed_at = COALESCE(g.full_pv_completed_at, now())
            WHERE EXISTS (
                SELECT 1 FROM game_best_moves gbm WHERE gbm.game_id = g.id
            )
        """)
    )
    op.create_index(
        "ix_games_bestmove_backfill_pending",
        "games",
        ["user_id"],
        unique=False,
        postgresql_where=sa.text(
            "full_pv_completed_at IS NOT NULL AND best_moves_completed_at IS NULL"
            " AND lichess_evals_at IS NULL"
        ),
    )
```
Ordering matters: `add_column` → data backfill `UPDATE` → `create_index` (so the index is built on final, already-stamped data, avoiding a spurious index-then-rewrite). This mirrors `903b54b77161`'s and `1eda5daba951`'s general shape (though neither of those two needed a data-only step — the closest project precedent for a migration-embedded data backfill is worth a quick search by the planner if a cleaner analog exists, but none was found among the last ~10 migrations at research time).

**Downgrade:** drop the index, then drop the column (standard reversible pair; the one-time `UPDATE` has no meaningful downgrade — accept data loss on the stamped values as the existing project convention does for other completion markers, since games remain re-drainable).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Weighted random pick over users/games | A bespoke `ORDER BY RANDOM()` or top-N window | `_es_weighted_user_pick` / `_es_weighted_game_pick` (existing shared building blocks) | Already solves anti-starvation (floor terms) and recency-weighting (ES key); reinventing it risks reintroducing the Phase 146 D-01 top-N-cutoff starvation bug that these functions were built to fix |
| "Is Maia loaded" detection | Reaching into `maia_engine._session` from `eval_apply.py` directly (as tests do) | A new `maia_engine.is_maia_available()` public function | Keeps the module boundary clean; `_session` is a private implementation detail, `eval_apply.py` should not import it directly |

**Key insight:** Everything genuinely new in this phase is ~40 lines of SQL-shape-copying and one guardrail boolean — the temptation to over-build (e.g., a dedicated "Maia backfill status" tracking table, or a custom retry/backoff scheme) should be resisted; the existing self-terminating-lottery + completion-marker pattern already handles all of it.

## Common Pitfalls

### Pitfall 1: Row-count-based Maia-availability inference
**What goes wrong:** Stamping `best_moves_completed_at` whenever `best_move_rows` is non-empty (or, worse, unconditionally on Path A/C) silently corrupts the self-termination signal on a Maia-absent backend.
**Why it happens:** `_build_best_move_candidates` returns `[]` for both "Maia ran, found nothing" and "Maia absent" — indistinguishable from the caller's perspective without an independent check.
**How to avoid:** Use `maia_engine.is_maia_available()` (module-global session presence), never infer from `best_move_rows`.
**Warning signs:** A quick/incomplete implementation would look correct in dev (where `.env` typically doesn't install the `maia-inference` group unless explicitly synced) but would silently and permanently starve the backfill lottery of a whole cohort of games if a backend ever boots without onnxruntime in prod.

### Pitfall 2: Predicate confusion — `full_pv_completed_at` is not engine-games-only
**What goes wrong:** Writing the tier-4b predicate as just `full_pv_completed_at IS NOT NULL AND best_moves_completed_at IS NULL` (omitting `lichess_evals_at IS NULL`) would make tier-4b compete with 174-07's residual fallback for the same lichess-eval-game population, double-processing games and violating D-03's explicit scope boundary.
**Why it happens:** Prior to 174-06, `full_pv_completed_at` really was closer to an engine-only signal in practice; 174-06 unified the pass so it now applies to both.
**How to avoid:** Always include the explicit `lichess_evals_at IS NULL` clause in the tier-4b predicate (both Stage 1 EXISTS-subquery and Stage 2 WHERE), exactly as `_claim_tier3_derived`'s Step 1 does for its own "needs-engine" predicate.
**Warning signs:** A test asserting the tier-4b rung's predicate is missing an explicit "lichess-eval games with full_pv_completed_at set are excluded" case (see Testing section below).

### Pitfall 3: `alembic check` drift from a mismatched `Index()` declaration
**What goes wrong:** Adding the migration's `create_index` call without updating `app/models/game.py`'s `__table_args__` (or vice versa) causes `alembic check` to propose reverting the change on the next autogenerate.
**Why it happens:** Documented precedent — this exact mistake happened in 174-07 (see 174-07-SUMMARY.md Deviations §1).
**How to avoid:** Run `uv run alembic check` as an explicit verification step after writing both files; the plan's verification loop should not consider the migration task done without it.

### Pitfall 4: Forgetting the tier-4b gate check when `EVAL_AUTO_DRAIN_ENABLED=True` but `BEST_MOVE_BACKFILL_ENABLED=False`
**What goes wrong:** If the new gate is only checked inside `_claim_tier4_bestmove` itself (not in `claim_eval_job`), the function still executes its two SQL queries every tick even when disabled — wasted DB round-trips at the idle-poll cadence.
**Why it happens:** Easy to put the gate in the "wrong" place if copying `_claim_tier4_blob`'s shape too literally (that function has no gate of its own — `EVAL_AUTO_DRAIN_ENABLED` is checked once, earlier, in `claim_eval_job`).
**How to avoid:** Check `settings.BEST_MOVE_BACKFILL_ENABLED` in `claim_eval_job`, immediately before calling `_claim_tier4_bestmove` (see Pattern 1's code block above) — mirrors where `EVAL_AUTO_DRAIN_ENABLED` is already checked for the bundled path.

## Code Examples

### `maia_engine.is_maia_available()` — new public accessor
```python
# app/services/maia_engine.py — add near score_move, after the module-global _session

def is_maia_available() -> bool:
    """True when the process-wide Maia session was successfully loaded at
    lifespan startup (start_maia). Cheap in-memory check — no I/O, no session.

    Used by eval_apply.py's completion-marker guardrail (Phase 176 D-01): a
    Maia-absent backend must never stamp best_moves_completed_at, or the
    affected games would be permanently excluded from the tier-4b backfill
    lottery with zero best-move rows.
    """
    return _session is not None
```

### New tier constant
```python
# app/models/eval_jobs.py — extend the existing TIER_* block
#   TIER_EXPLICIT = 1           — explicit user request (highest priority)
#   TIER_IDLE_BACKLOG = 3       — idle-backlog drain
#   TIER_BLOB_BACKFILL = 4      — spare-capacity flaw-blob backfill
#   TIER_BESTMOVE_BACKFILL = 5  — spare-capacity best-move backfill (Phase 176, lowest priority)
TIER_EXPLICIT: int = 1
TIER_IDLE_BACKLOG: int = 3
TIER_BLOB_BACKFILL: int = 4
TIER_BESTMOVE_BACKFILL: int = 5
```

### Config gate
```python
# app/core/config.py — add immediately after EVAL_AUTO_DRAIN_ENABLED (line 83)

# Best-move backfill toggle (Phase 176 BACK-01, D-05). When False (default), the
# tier-4b spare-capacity lottery is suppressed even when EVAL_AUTO_DRAIN_ENABLED
# is True (both gates are checked — see claim_eval_job's bundled scope=None path).
# Independent from EVAL_AUTO_DRAIN_ENABLED because best-move backfill load is
# backend-only and cannot be shed to the remote worker fleet (unlike blob
# backfill, ~85% of which the workers carry) — this lets prod pause best-move
# backfill under backend CPU/latency pressure without disabling all idle drain.
# Default False; enable in prod deliberately after observing backend RSS/CPU
# (mirrors 174 D-03b's posture).
BEST_MOVE_BACKFILL_ENABLED: bool = False
```

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Tier-4b's game-level recency anchor should be `g.full_pv_completed_at` (mirroring `_claim_tier4_blob`'s `g.full_evals_completed_at` anchor pattern) rather than `g.played_at` | Pattern 1 | Low — this is an ES-lottery tuning choice, not a correctness issue; either column produces a valid non-degenerate weighted pick. Flagged as a reasonable default consistent with the existing precedent, not independently verified against a design doc. |
| A2 | No existing project migration embeds a data-only `UPDATE` alongside a `add_column`/`create_index` in one file (a clean analog for D-04's one-time stamp) | "Verified: D-04 one-time backfill stamp" | Low — the plain `op.execute(sa.text(...))` pattern is standard Alembic and matches the project's SQL style elsewhere (e.g. `OPENING_CACHE_BACKFILL_SQL` in eval_drain.py uses the identical `sa.text(...)` INSERT-SELECT idiom), so this is a safe extrapolation even without a migration-file precedent. |

**If this table is empty:** N/A — two low-risk tuning/precedent assumptions are listed above; neither affects correctness of the locked D-01..D-05 decisions.

## Open Questions

1. **Should `_claim_tier4_bestmove`'s Stage-2 game pick also apply a TC-priority multiplier via `GAME_TC_WEIGHTS`?**
   - What we know: `_claim_tier4_blob` uses `GAME_TC_WEIGHTS` (classical=8 > ... > other=0.5) exactly as `_claim_tier3_derived` does.
   - What's unclear: Nothing, really — CONTEXT.md's "Claude's discretion" note says reusing tier-4's constants (which includes `GAME_TC_WEIGHTS`) is "the likely default." Treat this as settled: reuse `GAME_TC_WEIGHTS` unchanged, consistent with every other rung.
   - Recommendation: Reuse as-is; no new constant needed.

2. **Exact migration filename/revision-id** — not knowable until `alembic revision` is actually run at plan-execution time (auto-generates a random hex revision id). Planner/executor should run `uv run alembic revision -m "phase 176 best_moves_completed_at"` (not `--autogenerate`, since the column type + index + data backfill need hand-authoring per the D-04 pattern above) and let Alembic assign the id, chaining `down_revision = "1eda5daba951"`.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| onnxruntime (maia-inference uv group) | Maia inference during backfill drain | Conditional — present on backend only if `uv sync --group maia-inference` (or equivalent) was run; the guardrail (this phase's core deliverable) makes its ABSENCE safe rather than requiring it | Whatever Phase 174 pinned | The Maia-absent guardrail (Pattern 2 above) IS the fallback — games simply never get `best_moves_completed_at` stamped until a Maia-capable backend processes them |
| PostgreSQL (dev DB) | All lottery/migration testing | ✓ (per CLAUDE.md, `docker compose -f docker-compose.dev.yml -p flawchess-dev up -d`) | 18 | — |

**Missing dependencies with no fallback:** None — this phase's entire design goal is to make Maia-absence a non-blocking, self-healing condition.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (async, `pytest-asyncio`), backend |
| Config file | `pyproject.toml` (pytest section) / `tests/conftest.py` (per-run DB template) |
| Quick run command | `uv run pytest tests/services/test_eval_queue.py tests/services/test_full_eval_drain.py tests/services/test_maia_engine.py -x` |
| Full suite command | `uv run pytest -n auto` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BACK-01 | `_claim_tier4_bestmove` picks a PV-complete, best-move-incomplete, non-lichess-eval, non-guest game | unit | `pytest tests/services/test_eval_queue.py::TestTier4bBestMoveBackfill -x` | ❌ Wave 0 (new test class, mirrors existing `TestTier4BlobBackfill`) |
| BACK-01 | tier-4b excludes lichess-eval games even when `full_pv_completed_at IS NOT NULL` (D-03) | unit | same file, new test | ❌ Wave 0 |
| BACK-01 | tier-4b is gated by BOTH `BEST_MOVE_BACKFILL_ENABLED` and `EVAL_AUTO_DRAIN_ENABLED` independently (D-05) | unit | same file, 2 new tests (one flag off each) | ❌ Wave 0 |
| BACK-01 | tier-4b claim routes through `_full_drain_tick` end-to-end, self-terminates | integration | `pytest tests/services/test_full_eval_drain.py::TestBestMoveBackfill -x` | ❌ Wave 0 (mirrors 174-07's `TestLichessBestMoveBackfill`) |
| BACK-01 (guardrail) | Maia-absent backend does NOT stamp `best_moves_completed_at` (monkeypatch `maia_engine._session = None`) | unit/integration | same file, dedicated guardrail test | ❌ Wave 0 |
| BACK-01 (D-04) | Migration's one-time UPDATE stamps only games with an existing `game_best_moves` row | other | `uv run alembic upgrade head` / `downgrade -1` round trip + `uv run alembic check` | N/A (migration-level verification, not pytest) |

### Sampling Rate
- **Per task commit:** the quick run command above.
- **Per wave merge:** `uv run pytest -n auto` (full backend suite).
- **Phase gate:** Full suite green before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] New `TestTier4bBestMoveBackfill` class in `tests/services/test_eval_queue.py` — mirror `TestTier4BlobBackfill`'s 7-test shape (null-pick, empty-queue, excludes-guests, excludes-pv-incomplete, **excludes-lichess-eval** [new, D-03-specific], excludes-already-stamped, dispatch-via-claim [after BOTH tier-3 and tier-4-blob return None], dispatch-disabled-by-BEST_MOVE_BACKFILL_ENABLED [separate from EVAL_AUTO_DRAIN_ENABLED], claimed-job-fields).
- [ ] `_insert_game` test helper (`tests/services/test_eval_queue.py:109-142`) needs a new optional `best_moves_completed_at: datetime | None = None` kwarg (mirrors its existing `full_pv_completed_at`/`lichess_evals_at` kwargs) — currently the helper does not accept it `[VERIFIED: read the helper]`.
- [ ] New `TestBestMoveBackfill` class in `tests/services/test_full_eval_drain.py` — mirror 174-07's `TestLichessBestMoveBackfill` end-to-end + double-claim-idempotency shape, but for the engine-side (non-lichess) population.
- [ ] Dedicated Maia-absent guardrail test — the single most important new test in this phase (mutation-test-style: prove the guardrail by showing the stamp does NOT fire when `maia_engine._session = None`, using the exact monkeypatch pattern `tests/services/test_maia_engine.py:33-39` already establishes, then showing it DOES fire with a session present). Per this project's own MEMORY.md lesson ("Mutation-test gap closures" — prove a fix by reverting it and confirming behavior changes, not by grep), this test should assert the NEGATIVE case explicitly (stamp stays NULL) rather than only the positive case.
- [ ] Migration round-trip test is manual (`alembic upgrade head` / `downgrade -1` / `upgrade head` + `alembic check`), per 174-07 precedent — not a pytest test.

**Test-isolation gotcha (from project MEMORY.md, applies directly here):** tier-3/tier-4/tier-4b lottery draws are GLOBAL + random across the whole test DB. Every non-guest `Game` row inserted by a new test MUST be cleaned up in a `finally: await _delete_games(...)` block (exactly as every existing `TestTier4BlobBackfill` test already does) — a leaked non-guest game with a matching predicate will make an unrelated test elsewhere in the suite flake ("got unexpected game id").

## Security Domain

This phase has no user-facing input surface (no new router, no new request schema) — it is a backend batch-job addition. ASVS categories mostly don't apply; the one relevant control is already established project convention:

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | Marginal (no external input) | All new SQL fragments in `_claim_tier4_bestmove` must follow the existing `_es_weighted_user_pick`/`_es_weighted_game_pick` convention: WHERE-clause SHAPE is a trusted hardcoded string (never derived from request input), all numeric VALUES (tau, floor, tc weights) are bound via the `sa.text(...)` params dict — never f-string-interpolated. This is already how the module is structured; the new rung must not deviate. |
| V6 Cryptography | No | Not applicable — no secrets, no crypto in this phase. |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SQL injection via lottery predicate values | Tampering | Already mitigated by the project's existing `:param` binding convention (QUEUE-08 security note in `eval_queue_service.py`'s module docstring) — the new rung must not introduce any f-string-interpolated VALUE into the `sa.text(...)` query. |
| Resource exhaustion (backend CPU/RAM) from an uncapped backfill drain | Denial of Service (self-inflicted) | This is exactly what D-05's dedicated `BEST_MOVE_BACKFILL_ENABLED` kill-switch and D-02's tier ordering (live tier-1/2/3 always preempts tier-4/4b) exist to mitigate — no additional new control needed beyond faithfully implementing D-02/D-05 as specified. |

## Sources

### Primary (HIGH confidence — direct codebase reads, this session)
- `app/services/eval_queue_service.py` (full file, 888 lines) — `_claim_tier4_blob`, `_es_weighted_user_pick`, `_es_weighted_game_pick`, `claim_eval_job` bundled ladder, all TIER4_* constants.
- `app/services/eval_drain.py` (full file, 1092 lines) — `_full_drain_tick`, confirms `run_one_full_eval_tick` does not exist as a symbol (naming drift, see below).
- `app/services/eval_apply.py` (lines 1700-2113) — `_build_best_move_candidates`, `_upsert_best_move_rows`, `apply_full_eval`, `apply_completion_decision`, `_mark_full_pv_completed`, `_mark_full_evals_completed`.
- `app/services/maia_engine.py` (full file, 153 lines) — `_session` global, `start_maia`, `score_move`.
- `app/models/game.py` (lines 1-263) — `full_pv_completed_at` column + `ix_games_lichess_pv_backfill_pending` index declaration.
- `app/models/game_best_move.py` (full file) — `GameBestMove` ORM model.
- `app/models/eval_jobs.py` (relevant excerpt) — `TIER_*` constants.
- `app/core/config.py` (full file) — `EVAL_AUTO_DRAIN_ENABLED` at line 83, `Settings` class shape.
- `app/routers/eval_remote.py` (lines 1100-1230) — `_apply_atomic_submit`'s `_build_best_move_candidates` call, confirming the remote-submit lane is ALSO a go-forward stamping site.
- `.planning/phases/174-backend-maia-inference-best-move-storage-spike-gated/174-07-SUMMARY.md` — the `alembic check` drift lesson, the residual-fallback broadening precedent.
- `alembic/versions/20260716_171823_1eda5daba951_...py` and `alembic/versions/20260716_125231_903b54b77161_...py` — migration shape precedents, current head revision id.
- `tests/services/test_eval_queue.py` (lines 1-210, 1629-1930) — `TestTier4BlobBackfill` test shape, `_insert_game`/`_delete_games` helpers.
- `tests/services/test_maia_engine.py` (full file) — existing `_session` monkeypatch pattern for Maia-absent simulation.

### Secondary (MEDIUM confidence)
- None — no external documentation was consulted; this is a pure internal-codebase research task with zero new dependencies.

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Tier-4b lottery copy target: HIGH — verbatim function signatures and line numbers confirmed against the live file.
- Completion-marker + guardrail design: HIGH — the correctness gap (row-count can't signal Maia-absence) is directly demonstrated by reading `_build_best_move_candidates`'s actual control flow, not inferred.
- Migration/index pattern: HIGH — directly copies the verified, already-shipped 174-07 precedent, including its documented drift lesson.
- D-04 one-time stamp SQL: MEDIUM — the exact `UPDATE ... WHERE EXISTS` shape is straightforward and low-risk, but no identical precedent migration was found in the last ~10 files to copy verbatim (see Assumption A2).

**Research date:** 2026-07-17
**Valid until:** Stable — this is internal, already-shipped-adjacent code (Phase 174/175 just merged); no external API/library churn risk. Re-verify line numbers if Phase 176 planning is deferred more than ~2-3 phases (the eval-queue module has historically been touched by nearly every eval-related phase).
