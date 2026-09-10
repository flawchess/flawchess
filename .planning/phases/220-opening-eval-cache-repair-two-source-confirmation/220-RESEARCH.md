# Phase 220: Opening Eval Cache Repair & Two-Source Confirmation - Research

**Researched:** 2026-09-09
**Domain:** PostgreSQL data repair pipeline + async SQLAlchemy write-path hardening (in-repo, brownfield)
**Confidence:** HIGH (every claim below is grounded in a file opened this session; no external package introduced)

## Summary

This is a **zero-new-dependency, all-in-repo phase**. There is no "standard stack" to research: every
primitive the seed asks for already exists (`EnginePool`, `compute_hashes`, `eval_cp_to_expected_score`,
`_collect_full_ply_targets`, `_classify_and_fill_oracle`, `db_url_for_target`, the Alembic conventions,
the script/test templates). What the planner actually needs is **file:line ground truth**, because the
seed and CONTEXT.md carry several line numbers and assumptions that are stale or wrong against the
current tree.

Six findings materially change the plan:

1. **The per-game write lock D-04 asks for already exists** — `apply_full_eval` takes
   `pg_advisory_xact_lock(_game_write_lock_key(game_id))` as its first statement
   (`app/services/eval_apply.py:2876-2881`). Rederive should take **that same lock**, not
   `SELECT … FROM games FOR UPDATE`: a games-row lock would protect nothing, because no existing
   writer takes one. The blob-submit lane does **not** take it, and the no-resurrect property is
   provable from its statement shapes — but it has a pre-existing `StaleDataError` window.
2. **`refresh_game_oracle_counts` is already extracted** — the seed's "extract `eval_apply.py`
   ~1335-1375" was done by Phase 214: the block is `_write_oracle_counts(session, game, positions)`
   at `app/services/eval_apply.py:1311`. CACHEFIX-06 reduces to renaming/promoting it (or just
   calling `_classify_and_fill_oracle`, which already calls it).
3. **`scripts/backfill_flaws.py` is the WRONG rederive host as literally written.** Its write path is
   `delete_flaws_for_game` + `bulk_insert_game_flaws` (delete-then-insert), which destroys
   `allowed_pv_lines` / `missed_pv_lines` and all 8 tactic-tag columns for every repaired game.
   Rederive must go through `_classify_and_fill_oracle`'s 4-way diff/upsert.
4. **CACHEFIX-12 has a self-confirmation trap.** `_merge_dedup_pv_into_engine_map`
   (`app/routers/eval_remote.py:1302`) injects **cached** values into `engine_result_map` before the
   write session. Passing that map plus a naive target list to `_upsert_opening_cache` would write
   cache values back into the cache — harmless under first-write-wins, **self-promoting** under
   CACHEFIX-08.
5. **The seed's `orphan` rule over-deletes.** Measured on the dev DB: walking only completed engine
   games leaves **39,207 / 106,615 (36.8%)** cache rows carrier-less, but only **24,029 (22.5%)** have
   no `game_positions` carrier at all. The 15,178-row difference would be wrongly deleted.
6. **`blobs_completed_at` re-arming is free.** `_classify_and_fill_oracle` ends with
   `_refresh_blobs_completed` (`app/services/eval_apply.py:1816`), which clears the stamp
   bidirectionally when a new NULL-blob flaw appears. Seed step 5.4 needs no new code.

**Primary recommendation:** build the repair script around three existing functions —
`_collect_full_ply_targets` (board + DB hash per ply, free of PGN/`initial_fen` handling),
`_classify_and_fill_oracle` (rederive, blob-preserving, oracle counts, blob re-arm), and
`pg_advisory_xact_lock(_game_write_lock_key(gid))` (D-04) — and copy `scripts/gen_red_herring_pool.py`'s
shape (injectable `session_maker` **and** injectable `EnginePool`) rather than
`scripts/backfill_flaws.py`'s.

## User Constraints (from CONTEXT.md)

### Locked Decisions

Copied verbatim from `220-CONTEXT.md` `## Implementation Decisions`:

- **D-01:** **Repair first, two-source hardening second.** Release 1 = audit-table migration
  (CACHEFIX-01) + `scripts/opening_cache_repair.py` (CACHEFIX-02..07) + CACHEFIX-12 as a plain upsert
  through the existing `_upsert_opening_cache` (one shared function, two call sites) + the
  `OPENING_CACHE_BACKFILL_SQL` fix. Then the prod repair runs as the operator stage. Release 2 =
  CACHEFIX-08 (provenance columns, candidate -> promote write path, confirmed-only read paths) whose
  migration marks rows by audit status exactly as CACHEFIX-08 already states. — **Reversibility:**
  costly. Consequence: the repair script does NOT need to know about `confirmed`/`n_sources`; the
  CACHEFIX-08 migration derives them from `opening_cache_audit.status` (`screened_clean` /
  `confirmed_clean` / `repaired` -> `confirmed=true, n_sources=2`; everything else, including rows
  inserted after the seed, -> candidate). A future re-audit after hardening must set the columns
  itself; note that in the script's docstring, do not build it now. CACHEFIX-12 ships in release 1.
- **D-02:** Screen/confirm do not set any provenance column progressively (no such columns exist in
  release 1). Nothing in the repair depends on hardening.
- **D-03:** **Nothing is paused.** The server full-drain tick, the remote workers and the PV/blob
  lotteries keep running through every stage.
- **D-04:** **Rederive concurrency invariant (must be in the plan and tested):** rederive takes
  `SELECT ... FROM games WHERE id = :id FOR UPDATE` at the start of its per-game transaction, and a
  concurrent blob/PV submit for a flaw row that rederive removed must not resurrect that flaw (the
  submit's write must be a no-op for a missing `game_flaws` row, never an insert). The drain/submit
  paths currently take no game-row lock … so the planner must read the blob-submit write path and
  either add the same single-row lock there or prove the no-resurrect property from its upsert shape.
  Test: rederive removes a flaw, then a blob submit for that ply lands, and `game_flaws` stays empty
  at that ply. Pausing the lotteries via the existing env gates is the fallback only if the lock
  cannot be added safely; record which was chosen.
- **D-05:** **Stage gating stays strict** as CACHEFIX-02 states (each stage refuses to run before the
  previous stage's `finished_at`). No pipelining of confirm behind a still-walking screen. The screen
  walks engine games by `id` ascending (cursor = `last_game_id_walked`), not popular-first.
- **D-06:** **Hash-mismatch handling in screen:** try up to `MAX_CARRIERS_PER_HASH = 3` distinct
  carrier games (named constant) before marking `hash_mismatch`. `hash_mismatch` rows are never
  evaluated and are left in the cache untouched.
- **D-07:** **CACHEFIX-10 legacy sample runs after `report`, as its own subcommand (`legacy-sample`)**,
  gated on `calibrate` having finished. 200 games fully evaluated before 2026-06-18 across ALL plies at
  depth 15, plus a like-for-like control of 50 games fully evaluated after 2026-08-20 on the same walk.
  Per-row disagreement = expected-score delta beyond `screen_floor` or mate/non-mate mismatch. Decision
  rule: build and run `screen --legacy-cohort` only if the legacy disagreement rate at ply > 20 exceeds
  twice the control rate AND the absolute excess is at least 1 percentage point; otherwise record the
  numbers and build nothing. — **Reversibility:** reversible.
- **D-08:** **`herring_pool` rows at repaired `(game_id, ply)` are KEPT, never deleted or regenerated.**
  `herrings_touched` is a report counter only.
- **D-09:** `drill_items` whose `(user_id, game_id, ply)` no longer has a `game_flaws` row are pruned;
  `drill_solves` are kept. No `drill_items` are created for flaws ADDED by the repair. No change to
  drill scheduling or streak state beyond the prune.
- **D-10:** **No in-app nightly tick.** CACHEFIX-09 is implemented as written: the lichess cross-check
  query and the opening bounce rate join the `db-report` skill's Sanity Checks section
  (`.claude/skills/db-report/SKILL.md` §3), with `n_bad > 5` flagged in the report. The `db-report`
  sanity section additionally reports `count(*) FILTER (WHERE disagreements >= 1)` on the cache once
  the column exists.
- **D-11:** **Two-source agreement is measured in expected-score units, not 50cp.** Promote when
  `abs(expected_score(new) - expected_score(old)) <= OPENING_CACHE_AGREE_MAX_SCORE_DELTA` and
  mate/non-mate match. The constant is a named module constant in `eval_drain.py`, set from the prod
  `calibrate` result: the measured `confirm_floor`, rounded up, with a docstring citing the calibration
  date and value.
- **D-12:** **Disagreement reporting is throttled per row, not per event.** `sentry_sdk.capture_message`
  fires only when `disagreements` reaches 2 on the same row. The message string is fixed (grouping),
  hash and all values go in `set_context`, `set_tag("source", "opening-cache")`.
- **D-13:** **Self-promotion is impossible by construction.** The cache gains `source_game_id BIGINT
  NULL` (no FK). A result whose `game_id` equals the candidate's `source_game_id` neither promotes nor
  counts as a disagreement. Column set for CACHEFIX-08 is therefore: `confirmed`, `n_sources`,
  `disagreements`, `engine_version`, `written_at`, `confirmed_at`, `source_game_id`. —
  **Reversibility:** one-way.

### Claude's Discretion

- Everything the seed and ROADMAP already lock is not re-decided here; where CONTEXT.md and the seed
  differ, CONTEXT.md wins (D-07 rule, D-10 no tick, D-11 units, D-12 throttle, D-13 column). Anything
  else (batch sizes within the 500-row convention, subcommand flag names, report table layout, test
  fixture shapes) is the planner's.
- The optional 1-in-N canary from the seed is NOT built unless it is a trivial add-on; D-12 is the
  safety signal.

### Deferred Ideas (OUT OF SCOPE)

- Optional 1-in-N confirmed-hit canary (seed hardening item 3): not built unless trivial.
- Multi-thread Stockfish build for the pool (Phase 219 D-09): unrelated, stays a seed.
- A post-hardening re-audit mode that sets `confirmed`/`n_sources` from the script itself: documented
  in the script docstring, not built.
- Reviewed todos not folded: bitboard storage, WR-01 pt-33 Tailwind axis label, 172 deferred review
  findings, variation-tree nested button.

## Phase Requirements

| ID | Description (abridged from ROADMAP) | Research Support |
|----|-------------------------------------|------------------|
| CACHEFIX-01 | Alembic migration adds 4 audit tables | §Schema & Migrations — head rev, naming, CHECK/create_table precedent, `alembic/env.py` import requirement |
| CACHEFIX-02 | `scripts/opening_cache_repair.py`, 7 subcommands, `--db`, resumable | §Script Shape to Copy, §Pattern 1 (subparsers), §Pattern 5 (cooperative SIGTERM) |
| CACHEFIX-03 | `calibrate` + `screen` (board rebuild, hash assert, depth-15) | §Board Replay & Hash Assertion, §Engine API, §Pitfall 6 (orphan rule) |
| CACHEFIX-04 | `confirm` re-evaluates flagged rows at 1M nodes | §Engine API (`evaluate_nodes_with_pv`), §Expected-Score Utilities |
| CACHEFIX-05 | `propagate` old-value predicate on `game_positions` | §Post-Move Shift, §Pitfall 1 (asyncpg CAST), §Write-Path Anatomy (`best_move` is un-shifted) |
| CACHEFIX-06 | `rederive` through the drain's own classifier + shared oracle refresh | §Rederive Path — **do NOT use `backfill_flaws.py`'s write path**; `_write_oracle_counts` already extracted |
| CACHEFIX-07 | `report` writes `reports/opening-cache-repair/…` | §Report & Verification Queries |
| CACHEFIX-08 | Two-source confirmation + provenance columns | §Read Paths for CACHEFIX-08, §Schema (metadata-only DEFAULT), §Pitfall 3 (backfill SQL tests) |
| CACHEFIX-09 | db-report sanity section gains the two checks | §db-report Skill Integration |
| CACHEFIX-10 | legacy-cohort sample + decision | §Engine API, D-07 |
| CACHEFIX-11 | Prod acceptance assertions | §Validation Architecture — Prod Acceptance |
| CACHEFIX-12 | Submit path writes the cache | §Write-Path Anatomy (submit lane), §Pitfall 2 (self-confirmation trap) |

## Project Constraints (from CLAUDE.md)

Directives that bind this phase (planner must verify compliance):

- **Never use `asyncio.gather` on the same `AsyncSession`.** One session per worker coroutine.
  [VERIFIED: CLAUDE.md §Critical Constraints]
- **`bin/reset_db.sh` must not be run without explicit user permission.** Plans must not gate on it.
- **No magic numbers** — every threshold/batch size a named constant (`MAX_CARRIERS_PER_HASH`,
  `OPENING_CACHE_AGREE_MAX_SCORE_DELTA`, batch sizes).
- **No bare `str` for a fixed set of values** — the stage names and audit statuses must be
  `Literal[...]` in signatures. `--db` choices are already `Literal`-shaped via `db_url_for_target`.
- **`uv run ty check app/ tests/ scripts/` must pass with zero errors.** Explicit return annotations
  on every function; `Sequence[str]` not `list[str]` for covariant params; `# ty: ignore[rule-name]`
  only with a reason.
- **Database design rules:** FK with explicit `ondelete` for any column referencing a PK; unique
  constraints for natural keys; no native `ENUM` — status columns use `TEXT` + `CHECK` for low-volume
  tables, `SMALLINT` + `IntEnum` + `CHECK` for high-cardinality ones. `opening_cache_audit` is 2.57M
  rows: **`status` is the borderline case.** The seed and CACHEFIX-01 both say `status TEXT CHECK`;
  at 2.57M rows a `TEXT` status costs ~1 byte + string per row versus 2 bytes for SMALLINT. Recommend
  keeping `TEXT` + `CHECK` (the seed/ROADMAP lock it, statuses are operator-facing, and the table is
  transient-ish audit data) and stating the deviation-from-cardinality-rule rationale in the model
  docstring. `opening_cache_repair_rows` / `_games` are small.
- **Sentry:** `capture_exception` in every non-trivial `except` in `app/services/` and `app/routers/`;
  **never embed variables in the message string**; `set_context` / `set_tag("source", …)`.
- **Functions:** nesting depth hard 4, logic LOC hard 200, cognitive ≤15. The repair script will
  breach this if written as one function per stage — split each stage into
  `_stage_x_batch` / `_stage_x_run`. Gate:
  `uv run python scripts/check_function_size.py app/ --fail-over-depth 4 --fail-over-loc 200`
  (**scoped to `app/` only** — `scripts/` is not gated, but `ruff` C901/PLR0912/PLR0915 is project-wide).
- **Router convention:** `APIRouter(prefix=…)` with relative paths — no router change needed here.
- **Changelog:** append a user-facing bullet under `## [Unreleased]` in `CHANGELOG.md` when the repair
  merges to `main`. `CHANGELOG.md:9` is the `## [Unreleased]` heading; `### Fixed` at line 11.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Audit/repair tables | Database (Alembic) | — | Schema-level; must survive the run as the trail (CACHEFIX-01) |
| Stage orchestration + resume | Operator script (`scripts/`) | Database (status columns) | All progress state lives in DB columns; the script is stateless between invocations |
| Engine evaluation (screen/confirm/calibrate) | Local process (`EnginePool`) | — | Runs on the 4-worker box; only hashes/evals cross the tunnel |
| Board rebuild + hash assertion | Service (`eval_apply._collect_full_ply_targets` + `zobrist.compute_hashes`) | — | Existing single implementation; do not re-derive |
| Cache write (tick + submit) | Service (`eval_drain._upsert_opening_cache`) | Router (`eval_remote._apply_atomic_submit` call site) | CACHEFIX-12: one function, two call sites |
| Cache read (transplant + lease omit) | Service (`eval_apply._fetch_dedup_evals`) | Router (`eval_remote._fetch_cached_opening_hashes` wraps it) | The router helper already delegates — the `confirmed` filter goes in ONE place |
| Flaw reclassification | Service (`eval_apply._classify_and_fill_oracle`) | Script (calls it) | Single classifier writer rule; blob/tactic preservation is a native property of the diff/upsert |
| Concurrency isolation | Database (advisory lock) | — | `pg_advisory_xact_lock` already used by both live write lanes |
| Integrity check | Skill (`db-report` SKILL.md §3) | — | D-10: no cron, no in-app tick |

## Standard Stack

### Core

No new external packages. Everything is already in `pyproject.toml`.

| Component | Version | Purpose | Why Standard |
|-----------|---------|---------|--------------|
| SQLAlchemy 2.x async | in-repo | `select()` API + `text()` batched writes | CLAUDE.md mandates 2.x async |
| asyncpg | in-repo | Postgres driver | CLAUDE.md: no SQLite, asyncpg only |
| Alembic | in-repo | Migrations | head = `e55d2651a373` |
| python-chess 1.11.x | in-repo | PGN replay, `chess.Board`, `polyglot.zobrist_hash` | CLAUDE.md |
| Stockfish via `app.services.engine.EnginePool` | in-repo | depth-15 `evaluate`, 1M-node `evaluate_nodes_with_pv` | CLAUDE.md |
| `sentry-sdk` | in-repo | script + service error capture | CLAUDE.md |
| pytest / pytest-asyncio | in-repo | tests | `asyncio_mode = "auto"`, session-scoped loop |

**Package Legitimacy Audit:** *Not applicable — this phase installs no external packages.* If the
planner ever adds one, run `gsd_run query package-legitimacy check --ecosystem pypi <pkg>` first.

### Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| PostgreSQL (dev, `localhost:5432`) | dev smoke, all stages | ✓ | container `flawchess-dev-db-1` running [VERIFIED: `docker ps`, 2026-09-09] | — |
| PostgreSQL (benchmark, `localhost:5433`) | CACHEFIX-12 benchmark acceptance | ✓ | container `flawchess-benchmark-db-1` running [VERIFIED: `docker ps`] | — |
| PostgreSQL (prod, `localhost:15432`) | prod run | requires `bin/prod_db_tunnel.sh` | — | none — operator must start the tunnel |
| Stockfish binary | screen/confirm/calibrate/legacy-sample | assumed present (dev box runs the drain) [ASSUMED] | — | `EnginePool` injection in tests (no binary needed) |
| `flawchess-db` MCP | ad-hoc verification queries | ✓ | — | `uv run python` + `db_url_for_target` |

Dev DB state measured 2026-09-09 [VERIFIED: queried via `db_url_for_target('dev')`]:

| Metric | Dev value |
|---|---|
| `opening_position_eval` rows | 106,615 |
| …with `pv IS NOT NULL` | 32,856 |
| `games` | 163,810 |
| engine games (`full_evals_completed_at IS NOT NULL AND lichess_evals_at IS NULL`) | 5,941 |
| `game_positions` | 12,561,680 |
| `game_flaws` | 70,933 |
| `herring_pool` | 30 |
| `drill_items` | 31 |
| lichess cross-check (`n_checked` / `n_bad`) | 2,137 / **0** |

**Consequence for the dev smoke:** dev has **zero** lichess-detectable poison, so the smoke test
cannot rely on real poisoned rows to exercise `confirmed_bad → propagate → rederive`. The plan must
**inject** a synthetic poisoned cache row (overwrite one dev cache row's `eval_cp` to a piece value
whose carriers exist) so the whole chain is exercised end to end, then assert it is repaired.

## Architecture Patterns

### System Architecture Diagram

```
                    ┌──────────────────────── RELEASE 1 (repair) ───────────────────────┐

  opening_position_eval (2.57M)                    engine games (walk by id ASC)
            │                                                  │
   [seed] INSERT…SELECT ──► opening_cache_audit(status=pending)│
            │                                                  │
   [calibrate] ~500 post-2026-08-20 rows ──► EnginePool ──► p99 deltas
            │                          (depth-15 + 1M-node)     │
            └──► opening_cache_repair_progress{screen_floor, confirm_floor}
                                                               │
   [screen]  for each game (cursor last_game_id_walked):       ▼
             load Game.pgn + game_positions rows
               └─► _collect_full_ply_targets(...)  →  [(ply, full_hash_from_DB, board)]
                     └─► compute_hashes(board)[2] == full_hash ?
                            no  ──► try next carrier (≤ MAX_CARRIERS_PER_HASH=3) ──► hash_mismatch
                            yes ──► engine.evaluate(board)  (depth 15)
                                     └─► |Δexpected_score| ≤ screen_floor ? screened_clean : flagged
             walk end ──► rows still `pending` ──► orphan  (see Pitfall 6 before deleting)

   [confirm] flagged ──► evaluate_nodes_with_pv(board)  (1M nodes)
                          └─► |Δ| > confirm_floor or mate mismatch
                                 ├─ yes: confirmed_bad + OVERWRITE opening_position_eval row
                                 └─ no : confirmed_clean (cache untouched)

   [propagate] confirmed_bad ──► UPDATE game_positions p
                                 FROM game_positions n
                                 WHERE n.full_hash = :h AND n.ply BETWEEN 1 AND 20
                                   AND p.(game_id,user_id) = n.(game_id,user_id)
                                   AND p.ply = n.ply - 1              ◄── post-move shift
                                   AND p.eval_cp IS NOT DISTINCT FROM CAST(:old_cp AS smallint)
                                   AND p.eval_mate IS NOT DISTINCT FROM CAST(:old_mate AS smallint)
                                 RETURNING …
                               ──► opening_cache_repair_rows (PK game_id,ply)
                               ──► opening_cache_repair_games (status=pending)
                               ──► audit.repaired_at        (all in ONE txn)

   [rederive] per pending game, ONE txn:
                 pg_advisory_xact_lock(_game_write_lock_key(gid))   ◄── D-04, the EXISTING lock
                 snapshot flaws_before_* + accuracy/ACPL
                 _classify_and_fill_oracle(session, gid, {}, None, blobs_pending=True)
                     ├─ classify_game_flaws (reads positions[n+1].pv — no engine)
                     ├─ 4-way diff/upsert (blob + tactic preserved by omission)
                     ├─ _write_oracle_counts  (counts + accuracy + ACPL)
                     └─ _refresh_blobs_completed  ◄── clears blobs_completed_at ⇒ tier-4 re-arm (free)
                 prune drill_items with no game_flaws row  (D-09)
                 count herring_pool rows at repaired plies (D-08 — count only)
                 write flaws_after_*, status=reclassified

   [report] read-only ──► reports/opening-cache-repair/opening-cache-repair-YYYY-MM-DD.md
   [legacy-sample] (D-07, after report) ──► 200 pre-06-18 games + 50 post-08-20 control

                    └───────────────────────────────────────────────────────────────────┘

                    ┌──────────────────────── RELEASE 2 (hardening) ─────────────────────┐
   tick   ─┐
           ├─► _upsert_opening_cache(session, engine_targets, engine_result_map)
   submit ─┘        candidate(n_sources=1) → promote(n_sources=2,confirmed) → replace+disagreements++
                                                            └─► Sentry at disagreements == 2 (D-12)
   _fetch_dedup_evals  ──► WHERE confirmed              (transplant)
   _fetch_cached_opening_hashes ──► delegates to it     (lease omit)
                    └───────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| File | Responsibility in this phase |
|------|------------------------------|
| `alembic/versions/<new>_phase_220_opening_cache_audit.py` | 4 audit tables (release 1) |
| `alembic/versions/<new>_phase_220_cache_provenance.py` | 7 cache columns + status-derived marking (release 2) |
| `app/models/opening_cache_audit.py` (new, + 3 more or one module) | ORM models; MUST be imported in `alembic/env.py` and `app/models/__init__.py` |
| `scripts/opening_cache_repair.py` (new) | 8 subcommands (7 stages + `legacy-sample`) |
| `app/services/eval_drain.py` | `_upsert_opening_cache` gains the candidate/promote logic (R2); `OPENING_CACHE_BACKFILL_SQL` `ORDER BY` fix (R1); `OPENING_CACHE_AGREE_MAX_SCORE_DELTA` constant (R2) |
| `app/routers/eval_remote.py` | `_apply_atomic_submit` passes `update_opening_cache=True` + a correctly-filtered `engine_targets_for_cache` (R1, CACHEFIX-12) |
| `app/services/eval_apply.py` | `_write_oracle_counts` → public `refresh_game_oracle_counts` (R1); `_fetch_dedup_evals` gains `WHERE confirmed` (R2) |
| `scripts/backfill_flaws.py` | `--from-repair-table` **routed through `_classify_and_fill_oracle`**, plus the single-writer docstring note |
| `.claude/skills/db-report/SKILL.md` | §3 gains Check C (lichess cross-check) + Check D (opening bounce rate) |

### Pattern 1: argparse subcommands (the only in-repo precedent)

```python
# Source: scripts/benchmark_lane.py:925-938 (read 2026-09-09)
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase 212 benchmark full-game-analysis lane operator surface."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    _add_select_subparser(subparsers)
    _add_snapshot_subparser(subparsers)
    ...
    args = parser.parse_args()
    if args.command == "status" and not args.all_tranches and args.tranche is None:
        parser.error("status requires --tranche unless --all-tranches is given")
    return args
```

`benchmark_lane.py` also shows the per-subparser `--db` helper (`choices=["dev","test","prod","benchmark"]`).
For CACHEFIX-02 make `--db` **required** (no default), matching `resweep_holed_games.py` and
`backfill_flaws.py` — `benchmark_lane.py`'s `default="benchmark"` is the exception, not the rule.

### Pattern 2: script skeleton with injectable session_maker AND EnginePool

`scripts/gen_red_herring_pool.py` is the right template (it is the only script that does both DB and
engine work and is unit-tested without Stockfish):

```python
# Source: scripts/gen_red_herring_pool.py:818-831 (read 2026-09-09)
    if settings.SENTRY_DSN:
        sentry_sdk.init(dsn=settings.SENTRY_DSN, environment=settings.ENVIRONMENT)

    if session_maker is None:
        url = db_url_for_target(db)
        engine = create_async_engine(url, pool_pre_ping=True)
        session_maker = async_sessionmaker(engine, expire_on_commit=False)

    owns_pool = pool is None
    if pool is None:
        pool = EnginePool(HERRING_GENERATOR_WORKERS)
        await pool.start()
```

`tests/scripts/test_gen_red_herring_pool.py:1-37` documents the matching test shape: a `_FakePool`
recording every board it was asked to evaluate, injected via the `pool=` parameter — **no Stockfish
binary required in CI**. Copy this exactly.

`db_url_for_target` lives at `app/core/config.py:222` and maps
`{"dev","test","prod","benchmark"}` → `settings.DATABASE_URL_{DEV,TEST,PROD,BENCHMARK}`
[VERIFIED: app/core/config.py:222-238].

### Pattern 3: batched write with asyncpg-safe casts

```python
# Source: app/services/eval_apply.py:517-527 (read 2026-09-09)
        values_parts.append(
            f"(CAST(:ply_{i} AS smallint),"
            f" CAST(:ecp_{i} AS smallint),"
            f" CAST(:emt_{i} AS smallint),"
            f" CAST(:bm_{i} AS varchar))"
        )
```

`_upsert_opening_cache`'s own docstring states the rule: *"Uses CAST() instead of :: cast syntax for
asyncpg compatibility (same reason as `_batch_update_eval_rows`)."*
[VERIFIED: app/services/eval_drain.py:464-465]

### Pattern 4: per-game advisory lock (the D-04 answer)

```python
# Source: app/services/eval_apply.py:2876-2881 (read 2026-09-09)
    # 260825-v8g (FLAWCHESS-9F / FLAWCHESS-8G): serialize same-game writers for the
    # whole write session before any row work runs — see the docstring paragraph
    # above for the deadlock/correctness rationale.
    await write_session.execute(
        sa.text("SELECT pg_advisory_xact_lock(:lock_key)"),
        {"lock_key": _game_write_lock_key(game_id)},
    )
```

Key derivation [VERIFIED: app/services/eval_apply.py:121-148]:

```python
_GAME_WRITE_LOCK_NAMESPACE: int = 0x464C4157
_GAME_WRITE_LOCK_MASK: int = 0xFFFFFFFF

def _game_write_lock_key(game_id: int) -> int:
    return (_GAME_WRITE_LOCK_NAMESPACE << 32) | (game_id & _GAME_WRITE_LOCK_MASK)
```

The key space is provably disjoint from `tests/conftest.py`'s `_TEMPLATE_ADVISORY_LOCK_KEY =
7_777_777_777` (docstring states this explicitly) [VERIFIED: app/services/eval_apply.py:117-121;
tests/conftest.py:75].

### Pattern 5: cooperative SIGTERM in a long-running script

```python
# Source: scripts/import_stress_monitor.py:385-395 (read 2026-09-09)
    # Cooperative termination on SIGINT/SIGTERM — finish the current tick,
    # flush the file, then exit. Avoids a half-written block at the tail.
    stop_requested = False

    def _request_stop(signum: int, _frame: object) -> None:
        nonlocal stop_requested
        logger.info("signal %s received, stopping after this tick", signum)
        stop_requested = True

    signal.signal(signal.SIGINT, _request_stop)
    signal.signal(signal.SIGTERM, _request_stop)
```

This is the only signal-handling precedent in `scripts/` outside the remote worker's supervisor.
Success criterion 1 requires a **real** SIGTERM mid-batch. Cooperative shutdown makes the resume test
weaker (it always commits the current batch cleanly), so the plan should test **both**: a cooperative
SIGTERM (graceful, no lost batch) **and** a hard `SIGKILL`/uncaught-`CancelledError` mid-batch
(uncommitted batch rolls back, statuses unchanged, re-run redoes exactly that batch). See
§Validation Architecture for how.

### Anti-Patterns to Avoid

- **Do NOT route rederive through `scripts/backfill_flaws.py`'s existing write path.** It is
  delete-then-insert (see §Rederive Path) and destroys blobs + tactic tags.
- **Do NOT add `SELECT … FROM games FOR UPDATE`** for D-04. No existing writer takes a games-row lock,
  so it would serialize rederive against nothing. Use the advisory lock.
- **Do NOT pass `engine_result_map` straight into `_upsert_opening_cache` from the submit path**
  without filtering out dedup-sourced entries (Pitfall 2).
- **Do NOT `TRUNCATE` the cache** (seed §Operational, explicit).
- **Do NOT write an eval for a board whose replayed hash was not asserted** (ROADMAP cross-cutting
  constraint).
- **Do NOT re-evaluate lichess-analysed games** (`lichess_evals_at IS NOT NULL`). They may still be
  *carriers* whose boards seed the screen, and CACHEFIX-05's value predicate may touch their
  `game_positions` rows — that is the only permitted contact.
- **Do NOT use `asyncio.gather` on one session.** The engine gather must run with **no session open**,
  exactly as `_full_drain_tick` Step 3 does (`app/services/eval_drain.py:988-1006`).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Rebuild the board for ply N of a game | PGN re-parse loop + `initial_fen` handling | `eval_apply._collect_full_ply_targets(game_id, pgn, gp_rows)` (`app/services/eval_apply.py:210`) | Returns `(ply, full_hash **from the DB row**, pre-push `board.copy()`, move_uci/move_san)` in one mainline walk; `chess.pgn.read_game(...).board()` already honours the `[FEN]`/`[SetUp]` header, so `games.initial_fen` needs no special handling |
| Zobrist hash of a board | `chess.polyglot.zobrist_hash` directly | `zobrist.compute_hashes(board) -> (white, black, full)` (`app/services/zobrist.py:119`) | Applies the `ctypes.c_int64` signed-BIGINT conversion; the raw polyglot value is unsigned and will **never** compare equal to a stored `full_hash` |
| cp → expected score | your own sigmoid | `eval_cp_to_expected_score(cp, user_color)` / `eval_mate_to_expected_score` (`app/services/eval_utils.py:65,90`) | `LICHESS_K = 0.00368208`; mate is deliberately NOT routed through the sigmoid |
| Reclassify a game's flaws | `classify_game_flaws` + `delete` + `bulk_insert` | `eval_apply._classify_and_fill_oracle(...)` (`app/services/eval_apply.py:992`) | 4-way diff/upsert preserves blobs + tactic tags by omission, writes oracle counts + accuracy/ACPL, and refreshes `blobs_completed_at` |
| Recompute oracle counts / accuracy / ACPL | new helper | `eval_apply._write_oracle_counts(session, game, positions)` (`app/services/eval_apply.py:1311`) | Already the extracted shared block CACHEFIX-06 asks for |
| Re-arm a game for the PV/blob lottery | `UPDATE games SET blobs_completed_at = NULL` | nothing — `_refresh_blobs_completed` (`app/services/eval_apply.py:1816`) does it inside `_classify_and_fill_oracle` | Bidirectional by design; the tier-4 lottery selects `full_evals_completed_at IS NOT NULL AND blobs_completed_at IS NULL` (`app/services/eval_queue_service.py:817`) |
| Batched `UPDATE … FROM (VALUES …)` with NULLable smallints | `::` casts | `CAST(:p AS smallint)` | asyncpg rejects `::`-style casts through SQLAlchemy `text()` here (documented in-repo) |
| Serialize same-game writers | new lock table / `FOR UPDATE` | `pg_advisory_xact_lock(_game_write_lock_key(gid))` | Already the FIRST statement on both live write lanes |
| Resolve a `--db` target | `os.environ[...]` | `app.core.config.db_url_for_target` (`app/core/config.py:222`) | Raises on unknown targets |
| Get the Stockfish version string for `engine_version` | UCI handshake by hand | `engine.get_stockfish_version()` (`app/services/engine.py:386`) — returns e.g. `'Stockfish 18'` | Opens and quits one UCI connection; does not touch `EnginePool` |

**Key insight:** the repair pipeline is 90% orchestration over functions that already exist and are
already tested. Every place the seed says "write X" the correct instruction is usually "call the
existing X and pass the right arguments." The genuinely new code is: the 4 tables, the stage state
machine, the propagate SQL, and the report.

## Write-Path Anatomy

### `_upsert_opening_cache` — the shared write function

`app/services/eval_drain.py:437-517`. Signature [VERIFIED: app/services/eval_drain.py:437-441]:

```python
async def _upsert_opening_cache(
    session: AsyncSession,
    engine_targets: list[_FullPlyEvalTarget],
    engine_result_map: dict[int, tuple[int | None, int | None, str | None, str | None]],
) -> None:
```

Body facts the planner needs:

- **Filter** [VERIFIED: app/services/eval_drain.py:474-479]:
  ```python
    cache_rows = [
        (t.full_hash, cp, mate, bm, pv)
        for t in engine_targets
        if t.ply <= _DEDUP_MAX_PLY and not t.is_terminal
        for cp, mate, bm, pv in (engine_result_map.get(t.ply, (None, None, None, None)),)
        if cp is not None or mate is not None
    ]
  ```
  So the caller's `engine_targets` list is what defines "freshly computed" — the function itself does
  **not** exclude dedup-transplanted plies. This is the CACHEFIX-12 trap (Pitfall 2).
- **Dedup-by-hash collapse** [VERIFIED: app/services/eval_drain.py:487-493]: a `dict[int, tuple]`
  keyed by `full_hash`, preferring a pv-bearing row, because "Postgres rejects INSERT ... ON CONFLICT
  when two proposed rows share the conflict key". **Do not duplicate this** (ROADMAP CACHEFIX-12).
- **First-write-wins + pv self-heal** [VERIFIED: app/services/eval_drain.py:508-513]:
  ```sql
  INSERT INTO opening_position_eval (full_hash, eval_cp, eval_mate, best_move, pv)
   VALUES ... ON CONFLICT (full_hash) DO UPDATE SET pv = EXCLUDED.pv
   WHERE opening_position_eval.pv IS NULL AND EXCLUDED.pv IS NOT NULL
  ```
- **Transaction:** runs inside the caller's write transaction; the docstring says "If it fails the
  whole txn rolls back and the game is re-picked next tick — acceptable … No outer try/except is
  added (we do not swallow cache errors)."

`_DEDUP_MAX_PLY: int = DEDUP_MAX_PLY` (`app/services/eval_drain.py:157`), aliased from
`DEDUP_MAX_PLY: int = 20` (`app/models/game_position.py:44`), which is also the
`ix_gp_full_hash_opening` partial-index predicate (`app/models/game_position.py:106-110`). The
coupling invariant is documented at `app/models/game_position.py:33-43`.

### `OPENING_CACHE_BACKFILL_SQL`

`app/services/eval_drain.py:181-202`. The defect is exactly as the seed states — `SELECT DISTINCT ON
(nxt.full_hash)` with **no `ORDER BY`** [VERIFIED: app/services/eval_drain.py:183-186]:

```sql
    INSERT INTO opening_position_eval (full_hash, eval_cp, eval_mate, best_move)
    SELECT DISTINCT ON (nxt.full_hash)
           nxt.full_hash,
           cur.eval_cp,
```

Gate predicates (must be preserved) [VERIFIED: app/services/eval_drain.py:194-200]:
`nxt.ply <= :dedup_max_ply`, `g.full_evals_completed_at IS NOT NULL`, `g.lichess_evals_at IS NULL`,
`(cur.eval_cp IS NOT NULL OR cur.eval_mate IS NOT NULL)`, `ON CONFLICT (full_hash) DO NOTHING`.

Note the constant is `TextClause` and takes a `:dedup_max_ply` bind param. Six tests execute it as the
"gate" (see §Pitfall 3).

### `_full_drain_tick` — the tick call site

`app/services/eval_drain.py:875`. The cache-write arguments [VERIFIED: app/services/eval_drain.py:1115-1121]:

```python
            update_opening_cache=True,
            upsert_opening_cache_fn=_upsert_opening_cache,
            engine_targets_for_cache=engine_targets,
```

`engine_targets` is built at `app/services/eval_drain.py:990-994`:
```python
    engine_targets = [
        t
        for t in targets
        if t.is_terminal or t.ply > _DEDUP_MAX_PLY or t.full_hash not in dedup_map
    ]
```
i.e. **targets the engine actually evaluated**, dedup hits excluded. That is the semantic the submit
path must reproduce.

`apply_full_eval` asserts both companions are supplied when `update_opening_cache=True`
[VERIFIED: app/services/eval_apply.py:2900-2906].

### `_apply_atomic_submit` — the CACHEFIX-12 site

`app/routers/eval_remote.py:1167`. What it already has in hand before the write session:

| Value | Line | Note |
|---|---|---|
| `targets` (with `board`, DB `full_hash`, `ply`) | 1272-1278 | via `_collect_full_ply_targets` |
| `engine_result_map` from `body.evals` | 1282-1284 | `{e.ply: (e.eval_cp, e.eval_mate, e.best_move, e.pv)}` |
| `dedup_map` | 1291-1301 | fetched in its own short session; empty for lichess-eval games |
| `_merge_dedup_pv_into_engine_map(...)` | **1302** | **mutates `engine_result_map` in place, inserting CACHED tuples** |
| `is_lichess_eval_game` | 1237 | via `derive_is_lichess_eval_game` |
| write session + `apply_full_eval(...)` | 1385-1425 | `update_opening_cache` not passed ⇒ defaults `False` |
| the exact comment CACHEFIX-12 reverses | **1369-1371** | `# correctly). update_opening_cache stays False here (Pitfall 4 / D-05 — the` |

**Is the shared function directly callable there?** Yes — `apply_full_eval` already takes
`upsert_opening_cache_fn` / `engine_targets_for_cache` as parameters, so CACHEFIX-12 is three added
kwargs plus **one new local list**. No adapter, no signature change. The new list is the whole risk
surface:

```python
# Recommended — build BEFORE the merge at line 1302 mutates engine_result_map.
_worker_plies: frozenset[int] = frozenset(engine_result_map)   # right after line 1284
...
_engine_targets_for_cache = [
    t for t in targets
    if not t.is_terminal
    and t.ply <= DEDUP_MAX_PLY
    and t.ply in _worker_plies          # the worker actually evaluated it
    and t.full_hash not in dedup_map    # it was not a cache hit
]
```

`is_lichess_eval_game` needs no extra guard: `dedup_map` is `{}` for those games, but they also never
donate to the cache today. The tick's own filter excludes them by producing no engine targets for a
lichess game's opening plies (`dedup_hashes` is `[]`, so every ply is an engine target) — **that is a
divergence**: for a lichess-eval game the tick DOES pass opening plies in `engine_targets`, yet the
seed (diagnosis 7) and `_fetch_dedup_evals`' provenance rule say lichess games must never seed the
cache. Verify this against `tests/services/test_full_eval_drain.py::test_dedup_excludes_analyzed_source`
(line 450) before mirroring it; the safe choice for the **submit** path is to skip the cache write
entirely when `is_lichess_eval_game` is True.

**Trusted-operator gating is unchanged:** `require_operator_token` (`app/routers/eval_remote.py:173`)
is a `Depends(...)` on the endpoint, fail-closed (403 if unconfigured, 401 on mismatch, constant-time
`hmac.compare_digest` on UTF-8 bytes). `_apply_atomic_submit` is called only from the gated endpoint
at `app/routers/eval_remote.py:1436`. Adding the cache write adds no new trust surface, exactly as
CACHEFIX-12 states.

### `_fetch_cached_opening_hashes` — lease omission

`app/routers/eval_remote.py:211-232`. It **delegates** to `_fetch_dedup_evals`
[VERIFIED: app/routers/eval_remote.py:226-232]:

```python
    opening_hashes = [fh for (ply, fh, _cp, _mate) in gp_rows if ply <= DEDUP_MAX_PLY]
    if not opening_hashes:
        return frozenset()
    cached = await _fetch_dedup_evals(session, opening_hashes)
    return frozenset(fh for fh, (_cp, _mate, _bm, pv) in cached.items() if pv is not None)
```

**Consequence for CACHEFIX-08:** the `confirmed` filter goes into `_fetch_dedup_evals` **only** — both
read paths inherit it. Do not add a second filter in the router.

The consumer is `_lease_position_redundant` (`app/routers/eval_remote.py:234-266`), which also encodes
the incremental-lease rule (`prev.eval_cp is not None or prev.eval_mate is not None or prev.ends_game`)
and the "terminal donor is NEVER redundant" invariant.

## D-04 Concurrency: the answer

### The lock already exists — take THAT one

`apply_full_eval` (`app/services/eval_apply.py:2759`) executes
`SELECT pg_advisory_xact_lock(:lock_key)` as its **first** statement (line 2876-2881). Its docstring
states the rationale verbatim [VERIFIED: app/services/eval_apply.py:2810-2843]:

> *"The lock is taken here, at the very top of `apply_full_eval`, and not in the router
> (`_apply_atomic_submit`), because Phase 150 R7 already funnels BOTH live write lanes — the router
> and `_full_drain_tick` (eval_drain.py) — through this one shared function; a router-only lock would
> leave the drain lane racing."*
> … *"no new deadlock cycle is introduced because the lock is always the FIRST statement on every path
> into this function, with the identical key derivation (`_game_write_lock_key`) every time."*

**Recommendation (record this as the D-04 choice):** rederive executes
`SELECT pg_advisory_xact_lock(:lock_key)` with `_game_write_lock_key(game_id)` as the first statement
of its per-game transaction. This satisfies D-04's intent strictly better than
`SELECT … FROM games FOR UPDATE`, which would serialize rederive against **no existing writer**
(grep confirms zero `with_for_update` / `FOR UPDATE` against `games` in `eval_apply.py`,
`eval_drain.py`, `routers/eval_remote.py` — the only `FOR UPDATE` hits are on `eval_jobs`
(`app/services/eval_queue_service.py:267`) and the entry-lease (`app/services/eval_entry.py:434,451`))
[VERIFIED: repo-wide grep 2026-09-09].

### Concurrent `game_flaws` writers — full inventory

| Writer | File:line | Statement shape | Can it resurrect a deleted flaw? | Takes the advisory lock? |
|---|---|---|---|---|
| `_diff_upsert_flaw_rows` (drain + atomic-submit, via `_classify_and_fill_oracle`) | `app/services/eval_apply.py:1239` | `delete_flaw_plies` + `bulk_insert_game_flaws` + 2× `bulk_update_game_flaw_rows` | Yes — it is the authoritative classifier and will re-INSERT a ply it re-classifies as a flaw | **Yes** (via `apply_full_eval`) |
| `_apply_flaw_blob_submit` → `_batch_update_flaw_pv_lines` | `app/services/eval_apply.py:1782` | `UPDATE game_flaws SET … FROM (VALUES …) WHERE game_flaws.game_id = :game_id AND game_flaws.ply = v.ply` | **No** — pure UPDATE, silent 0-row no-op | **No** |
| `_apply_flaw_blob_submit` → `bulk_update_tactic_tags` | `app/repositories/game_flaws_repository.py:174-193` | `await session.execute(update(GameFlaw), updates)` (ORM bulk-update-by-PK) | **No** — but raises `StaleDataError` on a 0-row match | **No** |
| `eval_entry._classify_and_insert_flaws` | `app/services/eval_entry.py:549-610` | `bulk_insert_game_flaws` = `pg_insert(...).on_conflict_do_nothing()` | **Yes, in principle** | **No** |
| `scripts/backfill_flaws.py` | `scripts/backfill_flaws.py:~232-245` | `delete_flaws_for_game` + `bulk_insert_game_flaws` | Yes (and destroys blobs) | **No** |
| `scripts/retag_flaws.py` | — | `bulk_update_tactic_tags` | No (same StaleDataError shape) | **No** |

**No-resurrect proof for the blob lane:** both of its `game_flaws` statements are UPDATEs; neither is
an INSERT or an upsert. [VERIFIED: app/services/eval_apply.py:1805-1813 — the SQL string is
`"UPDATE game_flaws" … " WHERE game_flaws.game_id = :game_id" " AND game_flaws.ply = v.ply"`;
app/repositories/game_flaws_repository.py:193 — `await session.execute(update(GameFlaw), updates)`.]
So D-04's stated invariant **holds today by construction** — a blob submit for a ply rederive deleted
cannot recreate the row.

**But there is a real pre-existing defect the plan should fix while it is here.** `bulk_update_tactic_tags`
is ORM bulk-update-by-PK, and `delete_flaw_plies`' docstring records the incident
[VERIFIED: app/repositories/game_flaws_repository.py:220-232]:

> *"A clean per-ply `DELETE ... WHERE ply IN (...)`, never a bulk-update-by-PK, which asserts exactly
> one row matched per parameter set and raises `StaleDataError` when a ply no longer exists
> (FLAWCHESS-8D)."*

`_apply_flaw_blob_submit` computes `null_flaw_plies` in a **read session that is closed before** the
write session opens (`app/routers/eval_remote.py:986-993` read, `1064` write). If rederive deletes one
of those plies in the window, `bulk_update_tactic_tags` raises `StaleDataError` → 500 → the whole
submit rolls back (blobs lost, worker retries). Frequency today is low; rederive will raise it.

**Recommended fix (small, in the spirit of D-04's "add the same lock there"):** in
`_apply_flaw_blob_submit`'s write session, take `pg_advisory_xact_lock(_game_write_lock_key(game_id))`
as the first statement **and** re-read the surviving flaw plies inside that transaction, filtering
`updates` and `blob_map` to them. The lock alone does not close the window (the stale read happened
earlier); the in-lock re-read is the load-bearing half. Record in the plan which of the two D-04
options was chosen: **advisory lock in rederive + advisory lock and in-lock re-read filter in the blob
submit** (not `FOR UPDATE`, not pausing the lotteries).

**`_classify_and_fill_oracle` as a concurrent classifier:** yes, it is the one writer that could
re-insert a flaw rederive deleted — but it only runs under `apply_full_eval`, which holds the same
advisory lock, so with the rederive lock in place the two serialize. After rederive commits, a later
drain tick re-classifying the same game reads the **repaired** `game_positions` evals and reaches the
same conclusion rederive did. No divergence.

**`eval_entry._classify_and_insert_flaws`** is unlocked and inserts. Its population is disjoint in
practice (entry-ply cold lane processes games with `evals_completed_at IS NULL` — fresh imports, not
long-completed legacy carriers) [ASSUMED — inferred from the lane's queue predicate, not measured].
Note it in the plan; do not change it.

## Rederive Path

### `_classify_and_fill_oracle` is the correct entry point

`app/services/eval_apply.py:992`. Signature:

```python
async def _classify_and_fill_oracle(
    session: AsyncSession,
    game_id: int,
    engine_result_map: dict[int, tuple[int | None, int | None, str | None, str | None]],
    flaw_pv_blobs: dict[int, tuple[list[PvNode], list[PvNode]]] | None = None,
    blobs_pending: bool = False,
) -> None:
```

**It is a diff/upsert, NOT delete-then-insert** — confirmed [VERIFIED: app/services/eval_apply.py:1249-1300].
The four buckets are DELETE (`existing_plies - desired_plies`), INSERT (`desired_plies -
existing_plies`), UPDATE-fresh, UPDATE-preserve-by-omission. `preserve_plies = already_blobbed_plies -
freshly_blobbed`; preserved rows have `FLAW_BLOB_COLUMNS` keys stripped from the row dict so the SET
clause never mentions them (`app/repositories/game_flaws_repository.py:171`:
`FLAW_BLOB_COLUMNS: tuple[str, ...] = ("allowed_pv_lines", "missed_pv_lines") + TACTIC_TAG_COLUMNS`).

**Recommended rederive call:**

```python
await _classify_and_fill_oracle(
    session, game_id,
    engine_result_map={},      # no fresh engine work in rederive
    flaw_pv_blobs=None,        # ⇒ freshly_blobbed = set() ⇒ every blobbed ply is preserved
    blobs_pending=True,        # a NEW flaw with no blob gets a NULL tactic tag, not a raw ungated one
)
```

Why each argument is safe:

- `engine_result_map={}` — `_classify_flaw_rows` builds `pv_by_ply` from it (empty), and
  `classify_game_flaws`' docstring says *"The backfill path omits it and reads PVs from
  positions[n+1].pv"* [VERIFIED: app/services/flaws_service.py:960-964]. `_write_flaw_pvs`
  (`app/services/eval_apply.py:1382`) skips every ply whose `engine_result_map.get(cand_ply)` is None,
  so it writes nothing and **cannot clobber** existing `game_positions.pv`.
- `flaw_pv_blobs=None` — `freshly_blobbed` is `set()`
  [VERIFIED: app/services/eval_apply.py:1229-1234], so `preserve_plies == already_blobbed_plies` and
  every existing real blob + its 8 tactic columns survive.
- `blobs_pending=True` — this is a **judgement call the plan must record**. With `False`, a newly
  created flaw gets the pre-Phase-143 gate-free raw tactic tag (the Phase 147 strict-zero violation the
  drain avoids by passing `True`). With `True`, it gets NULL and is left for tier-4. `True` matches
  both live lanes (`app/services/eval_drain.py:1108` and `app/routers/eval_remote.py:1409`).

`_classify_and_fill_oracle` also runs `_write_oracle_counts` (counts + accuracy + ACPL) and
`_refresh_blobs_completed` — so seed steps 5.2, 5.3 and 5.4 are all covered by this one call.

### `refresh_game_oracle_counts` (CACHEFIX-06) is already extracted

The seed says "Extract the block at `eval_apply.py` ~1335-1375 into a shared
`refresh_game_oracle_counts(session, game, positions)`". **Phase 214 already did this.** It is
`_write_oracle_counts(session: AsyncSession, game: Game, positions: list[GamePosition]) -> bool` at
`app/services/eval_apply.py:1311` [VERIFIED: app/services/eval_apply.py:1311-1313]. Its docstring even
states the WR-01 reason it takes `game` and not `game_id`.

**Recommended plan action:** rename it to the public `refresh_game_oracle_counts` (keeping
`_write_oracle_counts` as an alias is unnecessary — it has exactly one caller) and update
`_classify_and_fill_oracle:1355`. That satisfies CACHEFIX-06's "shared … extracted from
`eval_apply.py` (drain and script use the same function)" with a one-line change instead of a
refactor. **Do not resurrect `scripts/archive/backfill_accuracy_acpl.py`** (seed, explicit).

### `scripts/backfill_flaws.py` — the hazard

Current CLI [VERIFIED: scripts/backfill_flaws.py:72-105]: `--db {dev,benchmark,prod}` (required),
`--user-id`, `--dry-run`, `--limit`, `--full-evald-only`. `BACKFILL_GAMES_PER_BATCH = 100`
(`scripts/backfill_flaws.py:62`). `run_backfill(...)` takes an injectable `session_maker`.

Its write path [VERIFIED: scripts/backfill_flaws.py:~231-245]:

```python
                    # Delete-then-insert = idempotent recompute (threshold-change safe).
                    # T-108-13 mitigation: delete scoped to (game_id, user_id).
                    await delete_flaws_for_game(session, game_id=game_id_val, user_id=game_user_id)
                    rows = [ flaw_record_to_row(...) for flaw in flaw_list ]
                    await bulk_insert_game_flaws(session, rows)
```

`delete_flaws_for_game` is `DELETE FROM game_flaws WHERE game_id = … AND user_id = …`
[VERIFIED: app/repositories/game_flaws_repository.py:196-217]. Running this over repaired games would
wipe `allowed_pv_lines`, `missed_pv_lines` and all 8 tactic-tag columns for every one of them —
undoing tier-4 blob work the fleet spent months producing.

Its module docstring's claim *"All three write paths (import hook in eval_drain.py,
reclassify_positions.py, and this script) call the SAME classify_game_flaws + flaw_record_to_row
functions so the materialized table never drifts (D-10)"* is about the **classifier**, not the write
shape — and `reclassify_positions.py` no longer exists in `scripts/` [VERIFIED: `ls scripts/`
2026-09-09].

**Recommended:** implement `--from-repair-table` as a distinct code path in `backfill_flaws.py` that
(a) selects `game_id` from `opening_cache_repair_games WHERE status = 'pending'`, and (b) calls
`_classify_and_fill_oracle` under the advisory lock — **never** the existing delete-then-insert
branch. Add the single-writer note the seed asks for, and add a docstring warning that the legacy
branch is blob-destructive. If mixing two write shapes in one script feels wrong, the cleaner
alternative (also compliant with CACHEFIX-06's "no second classifier call site") is to put the
rederive loop in `opening_cache_repair.py` and have `backfill_flaws.py --from-repair-table` be a thin
delegating wrapper — flag the choice for the user.

### `flaws_service` API

```python
# app/services/flaws_service.py:946-952
def classify_game_flaws(
    game: Game,
    positions: list[GamePosition],
    pv_by_ply: Mapping[int, str] | None = None,
    flaw_pv_blobs: dict[int, tuple[list[PvNode], list[PvNode]]] | None = None,
    blobs_pending: bool = False,
) -> GameFlawsResult:
```

`flaw_record_to_row(user_id: int, game_id: int, flaw: FlawRecord) -> dict[str, Any]`
(`app/repositories/game_flaws_repository.py`, imported at `scripts/backfill_flaws.py:56`).

Constants [VERIFIED: app/services/flaws_service.py:46-48, 81]:
```python
INACCURACY_DROP: float = 0.05
MISTAKE_DROP: float = 0.10
BLUNDER_DROP: float = 0.15
EVAL_COVERAGE_MIN: float = 0.90
```

`GameNotAnalyzed` is returned when coverage `< EVAL_COVERAGE_MIN`; discriminate with
`if "reason" in result` (TypedDict, `isinstance` raises).

### `_missing_flaw_pv_targets`

`app/services/eval_drain.py:520`. Despite the seed's step-5.4 reference, this is **not** the re-arm
mechanism: it is an in-tick helper that finds engine-game flaw plies which took a pv-less opening
dedup transplant so the tick can re-evaluate them for a PV
[VERIFIED: app/services/eval_drain.py:526-540, docstring]. The re-arm for the PV/blob lottery is
`_refresh_blobs_completed` clearing `games.blobs_completed_at`, consumed by the tier-4 predicate
`full_evals_completed_at IS NOT NULL AND blobs_completed_at IS NULL`
(`app/services/eval_queue_service.py:817`). **Nothing to build for seed step 5.4.**

## Read Paths for CACHEFIX-08

`_fetch_dedup_evals` (`app/services/eval_apply.py:334-366`) — the single read
[VERIFIED: app/services/eval_apply.py:356-366]:

```python
    result = await session.execute(
        select(
            OpeningPositionEval.full_hash,
            OpeningPositionEval.eval_cp,
            OpeningPositionEval.eval_mate,
            OpeningPositionEval.best_move,
            OpeningPositionEval.pv,
        ).where(OpeningPositionEval.full_hash.in_(full_hashes))
    )
    return {row[0]: (row[1], row[2], row[3], row[4]) for row in result.all()}
```

The `confirmed` filter is a one-line `.where(OpeningPositionEval.confirmed.is_(True))` addition here.
`_fetch_cached_opening_hashes` inherits it for free (it calls this function).

`_resolve_full_eval` (`app/services/eval_apply.py:369-394`) is pure and needs no change; note its
documented behaviour: *"pv_string is always None for dedup'd positions here — the dedup map's cached
pv (element [3]) is intentionally NOT surfaced through this function"*.

Existing tests around these read paths (all will need review under CACHEFIX-08):
`tests/services/test_full_eval_drain.py` lines 319, 395, 450, 513, 995, 1070, 1201, 1744;
`tests/test_eval_worker_endpoints.py` lines 5350, 5470.

## Schema & Migrations

### Current cache schema

`app/models/opening_position_eval.py` (56 lines, read in full). Columns
[VERIFIED: app/models/opening_position_eval.py:39-56]:

| Column | Type | Notes |
|---|---|---|
| `full_hash` | `BigInteger`, `primary_key=True` | the only key; no FK by design |
| `eval_cp` | `SmallInteger`, nullable | |
| `eval_mate` | `SmallInteger`, nullable | |
| `best_move` | `String(5)`, nullable | 4-char + 5-char promotion |
| `pv` | `Text`, nullable | full UCI PV FROM the position |

No indexes beyond the PK. The model docstring's "Immutable" claim
(`app/models/opening_position_eval.py:8-11`) becomes false with CACHEFIX-08 — update it.

`game_positions` relevant index [VERIFIED: app/models/game_position.py:106-110]:
```python
        Index(
            "ix_gp_full_hash_opening",
            "full_hash",
            postgresql_where=text(f"ply <= {DEDUP_MAX_PLY}"),
        ),
```
Partial on `ply <= 20`. The propagate SQL's `n.ply BETWEEN 1 AND 20` is what keeps it usable.
PK is `(user_id, game_id, ply)` (`app/models/game_position.py:48-52`); composite FK
`(game_id, user_id) → games(id, user_id) ON DELETE CASCADE`.

`game_flaws` PK is `(user_id, game_id, ply)` with FKs to `users.id` and `games.id`, both
`ondelete="CASCADE"` [VERIFIED: app/models/game_flaw.py:32-43]. Index
`ix_game_flaws_user_severity` on `(user_id, severity)`; the migration-only partial index
`ix_game_flaws_blob_backfill` (WHERE `allowed_pv_lines IS NULL`) is in
`_AUTOGEN_INDEX_IGNORELIST` (`alembic/env.py:105`).

`drill_items` PK `(user_id, game_id, ply)`; **FK to `games(id) ON DELETE CASCADE` only, deliberately
NOT to `game_flaws`** [VERIFIED: app/models/drill_item.py:15-27 module docstring + 77-85]. The
docstring is explicit that the prune is done by explicit deletion, never a cascade — which is exactly
D-09. Columns to be aware of when pruning: `status` (`DrillStatus` IntEnum 0/1/2), `streak`,
`due_date`, `fail_count`, `ever_correct`, `created_at`.

`herring_pool` — self-sufficient rows (`fen`, `arriving_move_uci`, `mover_color`, 5-entry `ladder`
JSONB with a `CheckConstraint("jsonb_typeof(ladder) = 'array' AND jsonb_array_length(ladder) = 5")`),
`UniqueConstraint('user_id','game_id','ply')`, FK `(game_id,user_id) → games ON DELETE SET NULL`
[VERIFIED: alembic/versions/20260727_214735_03df30e3c008…py:24-42]. `app/repositories/train_repository.py`
only ever **reads** `HerringPool` (no INSERT/UPDATE/DELETE — grep 2026-09-09), confirming D-08's
"count only, never delete".

### Alembic

- **Head revision:** `e55d2651a373`
  (`alembic/versions/20260823_184840_e55d2651a373_add_users_promoted_at.py`), verified as the unique
  head by walking all 122 revision files' `revision`/`down_revision` pairs [VERIFIED: script run
  2026-09-09].
- **File naming:** `YYYYMMDD_HHMMSS_<rev12>_<snake_slug>.py`.
- **Header shape** [VERIFIED: alembic/versions/…e55d2651a373…py:53-58]:
  ```python
  revision: str = 'e55d2651a373'
  down_revision: Union[str, Sequence[str], None] = '0ac0176294fd'
  branch_labels: Union[str, Sequence[str], None] = None
  depends_on: Union[str, Sequence[str], None] = None
  ```
- **Convention:** a rich module docstring explaining *why*, not just *what*; backfill SQL as a module
  constant so a test can execute the exact statement (see
  `alembic/versions/…0ac0176294fd…py:56-70`, `BACKFILL_SQL` exported for
  `tests/test_normalization.py::test_migration_sql_matches_extract_initial_fen`). **Copy this** for
  the CACHEFIX-08 status-derived marking UPDATE.
- **`create_table` precedent with CHECK constraints:**
  `alembic/versions/20260727_214735_03df30e3c008_phase_192_herring_pool_and_drill_solve_link.py:24-43`.
- **New models MUST be imported in two places or autogenerate will emit `drop_table`:**
  `alembic/env.py:12-29` (the `# noqa: F401` import block feeding `target_metadata = Base.metadata`)
  and `app/models/__init__.py`. `_AUTOGEN_TABLE_IGNORELIST` (`alembic/env.py:128-133`) is for
  benchmark-only tables — **do not** add the audit tables there; they are canonical.
  `tests/test_alembic_autogen_filter.py` pins the filter behaviour.

### Adding `confirmed BOOL NOT NULL DEFAULT false` to 2.57M rows

**Metadata-only, no table rewrite.** PostgreSQL 18 docs, §5.7.1 "Adding a Column":

> "Adding a column with a constant default value does not require each row of the table to be updated
> when the `ALTER TABLE` statement is executed. Instead, the default value will be returned the next
> time the row is accessed, and applied when the table is rewritten, making the `ALTER TABLE` very
> fast even on large tables."
> "If the default value is volatile (e.g., `clock_timestamp()`) each row will need to be updated with
> the value calculated at the time `ALTER TABLE` is executed."

[CITED: https://www.postgresql.org/docs/18/ddl-alter.html]

**Lock implication.** The `ALTER TABLE` reference states:

> "Note that the lock level required may differ for each subform. An `ACCESS EXCLUSIVE` lock is
> acquired unless explicitly noted. When multiple subcommands are given, the lock acquired will be the
> strictest one required by any subcommand."

[CITED: https://www.postgresql.org/docs/18/sql-altertable.html]

So `ADD COLUMN … DEFAULT false` takes `ACCESS EXCLUSIVE` on `opening_position_eval` — brief (a catalog
update), but it blocks every reader. Two consequences for the release-2 migration:

1. Add **all seven** CACHEFIX-08 columns in **one** `ALTER TABLE` (Alembic emits one `op.add_column`
   per call, each its own `ALTER TABLE`; either accept seven brief locks or use a single
   `op.execute("ALTER TABLE opening_position_eval ADD COLUMN … , ADD COLUMN … ")`). Prefer the single
   statement.
2. The **status-derived `UPDATE`** that marks screened rows `confirmed=true, n_sources=2` is a real
   row rewrite over ~2.5M rows and must be **batched** in the migration (`WHERE full_hash IN (SELECT
   … LIMIT n)` loop or a keyset walk), not one statement — Alembic runs on backend container startup
   (`deploy/entrypoint.sh`, per `alembic/versions/…0ac0176294fd…py:14-18`), and a multi-minute
   single-statement UPDATE would stall the deploy. Flag this to the user: the alternative is to move
   the marking into `opening_cache_repair.py` as a `mark-confirmed` subcommand run by the operator
   after the migration.

Existing large-table precedent in-repo is `alembic/versions/…0ac0176294fd…py` (`games.initial_fen`,
nullable add + one `op.execute(BACKFILL_SQL)` over ~176 affected rows) — its comment
*"Nullable add — metadata-only in PostgreSQL, so no rewrite of a large table"* is the project's stated
position [VERIFIED: alembic/versions/20260815_084711_0ac0176294fd_phase_210_games_initial_fen.py:74].
No batched-migration precedent exists in this repo [VERIFIED: grep for `LIMIT`/loop in
`alembic/versions/` found none].

## Board Replay + Hash Assertion

`compute_hashes(board: chess.Board) -> tuple[int, int, int]` returning `(white_hash, black_hash,
full_hash)` (`app/services/zobrist.py:119`). The load-bearing line
[VERIFIED: app/services/zobrist.py:133]:

```python
    full_hash = ctypes.c_int64(chess.polyglot.zobrist_hash(board)).value
```

The `ctypes.c_int64` conversion is why you must call `compute_hashes`, not `zobrist_hash` directly.

`games.initial_fen` (`app/models/game.py:141`, `Text`, NULL = standard start) needs **no explicit
handling** in the replay: `chess.pgn.read_game(...).board()` returns the position from the `[FEN]`
header when `[SetUp "1"]` is present, and `initial_fen` is *derived from* that header at import
(`normalization.extract_initial_fen`). All three in-repo replay implementations rely on this:

- `_collect_full_ply_targets` (`app/services/eval_apply.py:244,262`) — `game = chess.pgn.read_game(...)`,
  `board = game.board()`
- `flaws_service._recompute_fen_map` (`app/services/flaws_service.py:321`)
- `train_pool.fen_and_last_move_at_ply` (`app/services/train_pool.py:1218`)

**Use `_collect_full_ply_targets`.** It returns exactly what the screen needs per ply
[VERIFIED: app/services/eval_apply.py:283-295]: `_FullPlyEvalTarget(game_id, ply, full_hash=<from the
DB row>, board=board.copy(), eval_cp, eval_mate, move_uci, move_san)`. The assertion is then
`compute_hashes(t.board)[2] == t.full_hash` — comparing the replayed board against the **stored** hash.

`game_positions.move_san` is `String(10)`, nullable, "SAN of the move played FROM this position
(leading to ply+1); None on final position" (`app/models/game_position.py:~135`). You do not need it
for the replay if you use the PGN path.

**Pass `include_terminal=False`** for the screen — the terminal donor has `full_hash = 0` and is never
cached.

## Expected-Score Utilities

```python
# app/services/eval_utils.py:62
LICHESS_K: float = 0.00368208

# app/services/eval_utils.py:65-67
def eval_cp_to_expected_score(
    eval_cp: int,
    user_color: Literal["white", "black"],
) -> float:
# body: sign = 1 if user_color == "white" else -1
#       return 1.0 / (1.0 + math.exp(-LICHESS_K * sign * eval_cp))

# app/services/eval_utils.py:90-93
def eval_mate_to_expected_score(
    eval_mate: int,
    user_color: Literal["white", "black"],
) -> float:
# returns exactly 1.0 or 0.0 — mate is NOT routed through the sigmoid (D-02)
```

For a **position-keyed** delta (the audit table's `delta_score`) the natural convention is
`user_color="white"` for both sides of the comparison — the cache is white-perspective and the delta is
symmetric under a consistent choice. State this explicitly in the script; a mixed convention silently
halves or doubles the floor.

The seed's severity boundaries near equality follow from these constants: `INACCURACY_DROP = 0.05` at
ES 0.5 is `ln((0.5+0.05)/(0.5-0.05)) / LICHESS_K ≈ 54cp`; `MISTAKE_DROP = 0.10` ≈ 110cp;
`BLUNDER_DROP = 0.15` ≈ 168cp [VERIFIED by arithmetic on the quoted constants].

## Engine API

| Symbol | Line | Signature / return |
|---|---|---|
| `evaluate(board)` | `app/services/engine.py:258` | `-> tuple[int|None, int|None]`, **depth 15**, white perspective, `(None, None)` on failure/pool-not-started |
| `evaluate_nodes_with_pv(board)` | `app/services/engine.py:287` | `-> tuple[int|None, int|None, str|None, str|None]` = `(eval_cp, eval_mate, best_move_uci, pv_uci_string)`, **1M nodes** — the drain's call |
| `evaluate_nodes_multipv2(board)` | `app/services/engine.py:308` | 7-tuple; the tick's call — **not** needed by the repair |
| `EnginePool(size).start()/.stop()` | `app/services/engine.py:399,437,455` | same methods exist on the instance: `pool.evaluate`, `pool.evaluate_nodes_with_pv` |
| `get_stockfish_version()` | `app/services/engine.py:386` | `-> str`, e.g. `'Stockfish 18'`; opens+quits one UCI connection, does not use the pool → **this is `engine_version`** |
| `_NODES_BUDGET: int = 1_000_000` | `app/services/engine.py:104` | |
| `_NODES_TIMEOUT_S: float = 5.0` | `app/services/engine.py:105` | 1M-node mean ~0.98s, prod p90 1.277s |
| `_POOL_SIZE_ENV: str = "STOCKFISH_POOL_SIZE"`, `_DEFAULT_POOL_SIZE: int = 1` | `app/services/engine.py:152-153` | module-level `start_engine()` reads the env var |

The module-level `evaluate` / `evaluate_nodes_with_pv` return `(None, …)` when `_pool is None`, so the
repair script must **either** call `start_engine()` (env-driven size) **or** construct its own
`EnginePool(4)` and call the instance methods. The `gen_red_herring_pool.py` pattern (own pool,
injectable) is preferable for testability.

Depth-15 mean cost is documented as ~0.09s [VERIFIED: app/services/engine.py:101-103 comment
*"depth-15 mean ~0.09s; 1M-node mean ~0.98s"*], matching the seed's 65 CPU-hour screen budget.

## Common Pitfalls

### Pitfall 1: NULL bind parameters in the `IS NOT DISTINCT FROM` predicate

**What goes wrong:** `p.eval_mate IS NOT DISTINCT FROM :old_mate` with `old_mate=None` fails or
mis-types under asyncpg (Postgres cannot infer the parameter type; asyncpg is strict about it).
**How to avoid:** `CAST(:old_mate AS smallint)`, matching `_batch_update_eval_rows`
(`app/services/eval_apply.py:517-527`) and `_upsert_opening_cache`
(`app/services/eval_drain.py:496-502`). Never `::smallint` through SQLAlchemy `text()` — the
`_upsert_opening_cache` docstring states this is an asyncpg-compatibility rule.
**Warning sign:** `asyncpg.exceptions.IndeterminateDatatypeError` or `could not determine data type of
parameter $N` in the dev smoke.
**Related memory:** `project_asyncpg_jsonb_null_vs_sql_null` — a bound Python `None` to a JSONB column
serializes as json `null`, not SQL NULL. The audit tables have no JSONB columns; keep it that way.

### Pitfall 2: CACHEFIX-12 self-confirmation via `_merge_dedup_pv_into_engine_map`

**What goes wrong:** at `app/routers/eval_remote.py:1302`, `_merge_dedup_pv_into_engine_map(targets,
dedup_map, engine_result_map)` inserts the **cached** 4-tuple into `engine_result_map` for every
opening ply the worker did not evaluate [VERIFIED: app/routers/eval_remote.py:288-297 — *"for each
non-terminal target in the opening region whose full_hash is in dedup_map AND whose ply the worker did
NOT evaluate fresh, insert the cached 4-tuple … into engine_result_map"*]. Feed that map plus an
unfiltered target list to `_upsert_opening_cache` and you write the cache's own values back into the
cache.
**Why it matters:** under release-1 first-write-wins this is a harmless no-op on eval (the pv self-heal
would write the row's own pv onto itself). Under **CACHEFIX-08** it is a **self-promotion**: a
candidate would be "confirmed" by its own value on the very next submit that touches the position.
D-13's `source_game_id` guard does **not** save you — the second game is a genuinely different game.
**How to avoid:** snapshot `frozenset(engine_result_map)` immediately after building it from
`body.evals` (line 1284) and **before** line 1302; filter `engine_targets_for_cache` on that set AND
on `t.full_hash not in dedup_map`.
**Warning sign:** a CACHEFIX-08 test where one submit alone flips `confirmed` to true.

### Pitfall 3: `OPENING_CACHE_BACKFILL_SQL` is a test fixture, not dead code

**What goes wrong:** deleting it (CACHEFIX-08 offers "delete it or give it a deterministic ORDER BY")
breaks six tests that execute it as the canonical gate before calling `_fetch_dedup_evals`
[VERIFIED: `tests/services/test_full_eval_drain.py` lines 375, 434, 496, 1041, 1097, 1299].
Under CACHEFIX-08 those tests also break in a second way: rows the SQL inserts have `confirmed=false`
by DEFAULT, so `_fetch_dedup_evals` with the `confirmed` filter returns nothing and every gate test
fails on a false negative.
**How to avoid:** keep the constant, add the deterministic `ORDER BY nxt.full_hash,
g.full_evals_completed_at DESC, cur.pv IS NULL`, and in release 2 add `confirmed` to the INSERT column
list with an explicit value (the seed's own rule: *"Under item 3 any backfilled row is a candidate,
never confirmed"* → `false`). Then update those six tests to seed a confirmed row.
**Warning sign:** `test_dedup_hits_parity_source` failing with an empty dedup map.

### Pitfall 4: `bulk_update_tactic_tags` raises `StaleDataError` on a vanished row

Covered in §D-04. `app/repositories/game_flaws_repository.py:193` is
`await session.execute(update(GameFlaw), updates)`; the `delete_flaw_plies` docstring records
FLAWCHESS-8D verbatim. Rederive deleting a flaw between the blob submit's read and write session
turns a 200 into a 500.

### Pitfall 5: post-move shift, three separate conventions in one join

- `game_positions` row P stores the eval of the position **after** move P, i.e. of the position whose
  `full_hash` is on row P+1 [VERIFIED: `_post_move_eval`, app/services/eval_apply.py:397-412 — *"the
  eval stored at row `ply` is the eval of the position AFTER the move at `ply`, i.e. the eval of the
  NEXT position (`ply + 1`)"*].
- `game_positions.best_move` at row P is the best move **FROM** row P's own position — **not** shifted
  [VERIFIED: app/services/eval_apply.py:684-686 — *"best_move stays decision-ply-keyed (best move FROM
  row k's position), so it is NOT shifted"*].
- `game_positions.pv` is written **only at flaw-adjacent plies** (flaw_ply and flaw_ply+1), never for
  ordinary plies [VERIFIED: app/services/eval_apply.py:712-713 — *"_pv_string intentionally discarded
  here: pv is written ONLY at flaw-adjacent plies (ply = flaw_ply + 1) in _classify_and_fill_oracle"*;
  and `_write_flaw_pvs`, app/services/eval_apply.py:1391-1394].

So CACHEFIX-05's shape is right: **eval** goes to row `n.ply - 1`; **best_move/pv** go to row `n` (the
position's own row) and only when they equal the old cached values. Because `pv` is only ever written
at flaw plies, the pv-replacement branch will fire rarely — the report should count it separately so
a zero there is not read as a bug.

### Pitfall 6: the `orphan` rule over-deletes (measured)

**What goes wrong:** CACHEFIX-03 says "Rows still `pending` after the walk become `orphan` and are
deleted from the cache", and D-05 fixes the walk to *engine games*. A cache row whose only carriers
are (a) lichess games, (b) engine games not yet `full_evals_completed_at`-stamped (Path B games —
`_upsert_opening_cache` commits in the same transaction as the eval writes but **before**
`apply_completion_decision`, so a game that stays pending still leaves cache rows), or (c) games
deleted since, is marked `orphan` and deleted.

Measured on the dev DB, 2026-09-09 [VERIFIED: queried via `db_url_for_target('dev')`]:

| carrier definition (ply 1..20) | cache rows with no carrier | share of 106,615 |
|---|---|---|
| completed engine games only (`full_evals_completed_at IS NOT NULL AND lichess_evals_at IS NULL`) | **39,207** | 36.8% |
| any non-lichess game (`lichess_evals_at IS NULL`) | 31,111 | 29.2% |
| **any `game_positions` row at all** | **24,029** | 22.5% |

So the seed's rule would delete **15,178 dev rows (14.2% of the cache)** that have a perfectly good
carrier board. Extrapolated to prod's 2.57M rows this is on the order of 10⁵ rows of avoidable
re-evaluation, and it also silently *hides* poison: an unscreened row that gets deleted is never
audited, so the report's `screened_clean + confirmed_* + orphan` accounting looks complete when it is
not.

**How to avoid:** (1) define the carrier walk over **all** games with a `game_positions` row at ply
1..20 (the board is the board — a lichess game is a legitimate board source; you never read its eval),
or at minimum over `lichess_evals_at IS NULL` regardless of completion; (2) make orphan **deletion** a
separate, explicit, `--dry-run`-able action rather than an implicit tail of the screen — a `pending`
row after the walk can also mean the screen skipped its carrier (PGN parse failure, `--limit`, a kill
before the cursor advanced); (3) report the orphan count and a sample before deleting anything.
**Warning sign:** the dev smoke reporting an orphan count in the tens of thousands.

### Pitfall 7: dev has zero detectable poison

The lichess cross-check on dev returns `n_checked = 2,137, n_bad = 0`. The dev smoke therefore cannot
naturally exercise `flagged → confirmed_bad → propagate → rederive`. The plan must inject a synthetic
poisoned row (pick a dev cache hash with ≥5 carriers, record its true value, overwrite `eval_cp` with
a piece value, run the pipeline, assert the true value is restored and the row is `repaired`) and
restore/clean up. This also gives success criterion 1 a real diff to resume across.

### Pitfall 8: `asyncio.gather` must run with no session open

The tick's Step 3 comment is the rule [VERIFIED: app/services/eval_drain.py:1000-1001 — *"CLAUDE.md
hard rule: gather must never run inside an AsyncSession scope"*]. In the repair script: load a batch of
boards in a session, **close it**, gather the engine calls, then open a write session for the status
transitions. Batches of 500 rows per commit (ROADMAP cross-cutting constraint).

### Pitfall 9: tests must clean up every non-guest `Game` insert

Memory `project_eval_lottery_test_isolation`: the tier-3 lottery is global + random, so a leaked
non-guest game with `needs_engine_full_evals` makes unrelated lottery tests flake. Every test that
inserts a `Game` needs a `finally: await _delete_games(...)`. The existing eval-worker tests already
follow this (`tests/test_eval_worker_endpoints.py:5464-5466`).

### Pitfall 10: reports directory is committed

`reports/` is **not** gitignored except for four specific subpaths (`.gitignore:233-241`:
`reports/benchmark/benchmarks-generated.*`, `reports/data/sweep-*/`, `reports/data/persona-sweep-*/`,
`reports/data/persona-recal-*/`). So `reports/opening-cache-repair/opening-cache-repair-YYYY-MM-DD.md`
**will be committed** — which is what CACHEFIX-07/11 want (the report is the trail). Make sure the
report contains no PII (the db-report skill's precedent is to exclude emails/usernames; the per-user
table in CACHEFIX-07 must use user **ids** only).

## Code Examples

### Rederive per-game transaction (recommended skeleton)

```python
# Composed from: app/services/eval_apply.py:2876-2881 (lock), :992 (classifier),
#                app/models/drill_item.py:15-27 (prune rationale)
from app.services.eval_apply import _classify_and_fill_oracle, _game_write_lock_key

async def _rederive_one_game(session: AsyncSession, game_id: int, user_id: int) -> None:
    await session.execute(
        sa.text("SELECT pg_advisory_xact_lock(:lock_key)"),
        {"lock_key": _game_write_lock_key(game_id)},
    )
    before = await _snapshot_flaw_counts(session, game_id, user_id)   # + accuracy/acpl

    await _classify_and_fill_oracle(
        session, game_id, engine_result_map={}, flaw_pv_blobs=None, blobs_pending=True
    )
    # _write_oracle_counts + _refresh_blobs_completed already ran inside.

    pruned = await session.execute(
        sa.text(
            "DELETE FROM drill_items di WHERE di.user_id = :uid AND di.game_id = :gid"
            " AND NOT EXISTS (SELECT 1 FROM game_flaws gf"
            "                 WHERE gf.user_id = di.user_id AND gf.game_id = di.game_id"
            "                   AND gf.ply = di.ply)"
        ),
        {"uid": user_id, "gid": game_id},
    )
    after = await _snapshot_flaw_counts(session, game_id, user_id)
    await _write_repair_game_row(session, game_id, before, after, pruned.rowcount)
```

### Propagate statement (asyncpg-safe)

```sql
-- Source shape: SEED-164 §Step 4, with CAST() added per app/services/eval_apply.py:517-527
UPDATE game_positions p
SET eval_cp = CAST(:new_cp AS smallint),
    eval_mate = CAST(:new_mate AS smallint)
FROM game_positions n
WHERE n.full_hash = CAST(:full_hash AS bigint)
  AND n.ply BETWEEN 1 AND 20                       -- ix_gp_full_hash_opening
  AND p.game_id = n.game_id
  AND p.user_id = n.user_id
  AND p.ply = n.ply - 1                            -- post-move shift
  AND p.eval_cp   IS NOT DISTINCT FROM CAST(:old_cp   AS smallint)
  AND p.eval_mate IS NOT DISTINCT FROM CAST(:old_mate AS smallint)
RETURNING p.game_id, p.user_id, p.ply, n.ply AS hash_ply
```

### CACHEFIX-12 diff at the submit call site

```python
# app/routers/eval_remote.py — right after line 1284 (engine_result_map construction)
_worker_evaluated_plies: frozenset[int] = frozenset(engine_result_map)

# ... line 1302 _merge_dedup_pv_into_engine_map(...) mutates engine_result_map ...

# built before the write session opens (line ~1384)
_cache_targets = (
    []
    if is_lichess_eval_game
    else [
        t
        for t in targets
        if not t.is_terminal
        and t.ply <= DEDUP_MAX_PLY
        and t.ply in _worker_evaluated_plies
        and t.full_hash not in dedup_map
    ]
)

# ... inside the apply_full_eval(...) call:
    update_opening_cache=bool(_cache_targets),
    upsert_opening_cache_fn=_upsert_opening_cache,   # import from app.services.eval_drain
    engine_targets_for_cache=_cache_targets,
```

Note: `apply_full_eval` **asserts** both companions are non-None whenever
`update_opening_cache=True` (`app/services/eval_apply.py:2900-2906`), so gating the flag on a
non-empty list is fine but passing `True` with an empty list is also legal (the upsert no-ops).
Importing `_upsert_opening_cache` from `eval_drain` into `eval_remote` creates a router→service
import; `eval_remote.py` already imports from `eval_drain` (`_build_flaw_blob_lease_positions` is
imported in tests from there) — verify no circular import at plan time.

## db-report Skill Integration (CACHEFIX-09 / D-10)

`.claude/skills/db-report/SKILL.md` is 398 lines. §3 "Sanity Checks" begins at line 193 with a bullet
list of the checks, then one `### Check X — …` block each. The established block shape
[VERIFIED: .claude/skills/db-report/SKILL.md:193-199, 202-254, 282-300]:

1. A bullet in the §3 intro list naming the check and the question it answers.
2. `### Check X — <name>`
3. `#### Background (read before interpreting results)` — why the numbers mean what they mean,
   including "history note" warnings against re-deriving past mistakes.
4. `### Query N — <name>` with the SQL in a ```sql fence, plus a note if the query is heavy
   (Query 11 carries *"Heavier query: aggregates all of `game_positions` … Run it last."*).
5. `#### Check X output format` — numbered presentation instructions.
6. A **verdict line**: `Verdict line (Check A): **PASS** if … ; **INVESTIGATE** otherwise.`
7. A `> Reference (prod snapshot YYYY-MM-DD): …` blockquote with the baseline numbers.

**Recommended additions:**
- **Check C — Opening cache vs lichess median.** The seed's cross-check SQL verbatim. Verdict:
  `PASS if n_bad <= 5`. Reference blockquote: `2026-09-09 baseline: 25,444 / 87`. Mark it heavy
  (it joins `game_positions` twice over every lichess-analysed game) and say "run it last, alongside
  Query 11". Add the `count(*) FILTER (WHERE disagreements >= 1)` line once the column exists (D-10).
- **Check D — Opening bounce rate.** `|eval_P - eval_{P-1}| >= 200 AND |eval_{P+1} - eval_{P-1}| <= 60`,
  plies 2-19. Reference blockquote with the recorded noise floors: cache-free benchmark DB 0.618% any
  bounce / 0.235% in the 250-360cp band; prod engine games legacy 0.798% / 0.298%, mid 0.625% /
  0.243%, recent 0.844% / 0.271%. Verdict must say **coarse sanity check only** — the poison is
  ~0.1-0.2pp on top of a ~0.6% legitimate blunder-then-miss rate, so this check never fails a repair
  on its own.

Also update §3's intro sentence "Run both unless the user asks for one" → "Run all four…" and the
report layout's `## 3. Sanity Checks` section stays as-is.

## Sentry Conventions

| Context | Pattern | Source |
|---|---|---|
| Script init | `if settings.SENTRY_DSN: sentry_sdk.init(dsn=settings.SENTRY_DSN, environment=settings.ENVIRONMENT)` | `scripts/backfill_flaws.py:130-131`; `scripts/gen_red_herring_pool.py:818-819` |
| Per-item error, continue | `sentry_sdk.set_context("<name>", {"game_id": …, "user_id": …}); sentry_sdk.capture_exception(exc)` then `continue` | `scripts/backfill_flaws.py:~203-215` |
| Service tag | `sentry_sdk.set_tag("source", "full_eval_drain")` | `app/services/eval_drain.py:1025`; `app/services/eval_apply.py:1434` |
| Fixed message + context (D-12 shape) | `sentry_sdk.set_context("eval", {...}); sentry_sdk.set_tag("source", "full_eval_drain"); sentry_sdk.capture_message("full-drain: all engine evals failed for game — leaving pending", level="warning")` | `app/services/eval_drain.py:1021-1029` |
| Background-loop isolation | `with sentry_sdk.isolation_scope():` around the whole try/except | `app/services/eval_drain.py:1163` |

For D-12 use exactly this shape with a fixed string, e.g.
`"opening-cache: candidate disagreed twice — possible hash/eval misalignment"`, plus
`set_tag("source", "opening-cache")` and `set_context("opening_cache", {"full_hash": …,
"stored_cp": …, "new_cp": …, "disagreements": …, "source_game_id": …})`.

## Test Infrastructure

| Facility | Location | Note |
|---|---|---|
| Per-run DB cloned from a migrated template | `tests/conftest.py:309-370` (`test_engine`, session-scoped) | Template auto-refreshes when the Alembic head changes; `_TEMPLATE_ADVISORY_LOCK_KEY = 7_777_777_777` (`tests/conftest.py:75`) serializes the refresh |
| `pytest` config | `pyproject.toml:76-86` | `asyncio_mode = "auto"`, session-scoped loops, `addopts = "--ignore=tests/scripts/benchmarks --ignore=tests/scripts/tagger"` |
| Stockfish session fixture | `tests/conftest.py:553-575` (`engine_started`) | Skips silently if the binary is missing — **do not depend on it**; inject a fake pool instead |
| Submit-endpoint fixtures | `tests/test_eval_worker_endpoints.py:60-62` (`eval_worker_session_maker`), `:65-86` (`eval_worker_test_user`, `_TEST_USER_ID`) | session-scoped |
| Session redirection | `_patch_router_session(monkeypatch, session_maker)` at `tests/test_eval_worker_endpoints.py:315-338` | Patches `async_session_maker` on **three** modules: `eval_remote`, `eval_drain`, `eval_apply` |
| Minimal accepted submit | `_atomic_request(game_id, eval_dicts)` at `tests/test_eval_worker_endpoints.py:4899-4922` → `AtomicSubmitRequest(game_id, sf_version="Stockfish 18", worker_schema_version=1, evals=[AtomicSubmitEval(ply, eval_cp, eval_mate, best_move, pv)], blob_nodes=[])`; call `await _apply_atomic_submit(game_id, req, worker_id="test-worker", last_ip=None)` directly (bypasses the HTTP auth gate) | `tests/test_eval_worker_endpoints.py:5432-5434` |
| Game/positions helpers | `_insert_game` (`:96`), `_insert_game_positions` (`:137`), `_get_game_position` (`:~176`), `_delete_games` (`:282`) | |
| Cache helpers | `_insert_opening_cache` (`:4924`), `_insert_opening_cache_with_pv` (`:4939`), `_delete_opening_cache` (`:4957`) | Reuse for CACHEFIX-12 tests |
| Existing `_upsert_opening_cache` tests | `tests/services/test_eval_drain.py:1094-1370` (fill, first-write-wins conflict, intra-batch dedup collapse); `tests/test_eval_worker_endpoints.py:5470-5525` (pv self-heal) | |
| Existing gate tests using `OPENING_CACHE_BACKFILL_SQL` | `tests/services/test_full_eval_drain.py:375, 434, 496, 1041, 1097, 1299` | See Pitfall 3 |
| Advisory-lock tests | `tests/services/test_eval_apply.py:1113-1190` — proves the lock is xact-scoped, not session-scoped | Copy the technique for the rederive lock test |
| Script test template | `tests/scripts/test_gen_red_herring_pool.py` (fake `EnginePool`, injected `session_maker`, per-test cleanup) | The model for `tests/scripts/test_opening_cache_repair.py` |
| Script test precedent with committed data | `tests/test_backfill_flaws.py:1-25` docstring: *"Uses session-maker injection against the per-run test DB so run_backfill never touches a real --db target. The game must have committed data (not just a rollback-scoped db_session) since run_backfill opens its own sessions internally"* | |

### Testing SIGTERM-mid-batch resume

There is **no in-repo precedent for a subprocess-signal test** [VERIFIED: grep for `SIGTERM`/`signal.`
across `tests/` found only unrelated hits]. Two workable designs, in order of preference:

1. **In-process cancellation injection (recommended for CI).** Monkeypatch the batch's commit or the
   fake `EnginePool.evaluate` to raise `asyncio.CancelledError` (or a sentinel exception) on the Nth
   call. Assert: the uncommitted batch's audit rows are still `pending`, the cursor
   (`last_game_id_walked`) is unchanged, and a second `run_screen(...)` call reprocesses exactly that
   batch and no other. Deterministic, no subprocess, runs under `-n auto`.
2. **Real SIGTERM subprocess test (for the dev smoke, not CI).** `subprocess.Popen(["uv","run","python",
   "scripts/opening_cache_repair.py","screen","--db","dev"])`, `time.sleep(n)`,
   `proc.send_signal(signal.SIGTERM)`, wait, then re-invoke and diff the audit-table counts. Keep this
   in the **dev smoke procedure** (a documented operator step in the plan's verification), not as a
   pytest test — it is slow, timing-dependent, and needs Stockfish.

Success criterion 1 says "a simulated kill (SIGTERM mid-batch)"; design 1 satisfies "resumes without
duplicating or skipping rows" as an automated gate, and design 2 satisfies the literal SIGTERM as an
operator-run smoke. Do both and say which is which.

## State of the Art

| Old (as the seed/CONTEXT describe it) | Current (verified in tree) | Impact |
|---|---|---|
| "Extract the oracle-count block at `eval_apply.py` ~1335-1375" | Already extracted as `_write_oracle_counts` at `app/services/eval_apply.py:1311` | CACHEFIX-06 becomes a rename, not a refactor |
| "`_classify_and_fill_oracle` (~992)" | Correct — `app/services/eval_apply.py:992` | — |
| "`apply_full_eval` (~2775-2931)" | `app/services/eval_apply.py:2759-2995` | Minor drift |
| "`_upsert_opening_cache` (~line 437)" | Correct — `app/services/eval_drain.py:437` | — |
| "`_fetch_cached_opening_hashes` (~211)" | Correct — `app/routers/eval_remote.py:211` | — |
| "`_apply_atomic_submit` (~1167); comment at ~1369" | Both exact | — |
| "`_apply_flaw_blob_submit` (~951)" | Correct | — |
| "no game-row locking exists in the drain/submit write paths" | True for **games rows**; but a per-game **advisory** lock exists in `apply_full_eval` since 2026-08-23 (FLAWCHESS-9F/8G) | D-04's remedy changes |
| "`_classify_and_fill_oracle`'s delete-then-insert reclassification" (stale comment) | Fixed in 214-05 Task 2; it is a diff/upsert | Memory `atomic-eval-submit-incremental-lease` is correct |
| `scripts/reclassify_positions.py` (named in `backfill_flaws.py`'s docstring) | Does not exist | Docstring is stale; fix it while adding `--from-repair-table` |
| "planning must read the writer in `app/repositories/train_repository.py` and decide delete-vs-keep" (seed 5.6) | `train_repository.py` never writes `HerringPool` — read-only | D-08 (keep) is already settled; count only |

**Deprecated/outdated:** `scripts/archive/backfill_opening_eval_cache.py` and
`scripts/archive/backfill_accuracy_acpl.py` — referenced by the seed as history only; do not resurrect.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The Stockfish binary is present on the dev/operator box (the drain runs there) | Environment Availability | Screen/confirm cannot run locally; the plan's dev-smoke step blocks. Cheap to check: `uv run python -c "from app.services.engine import _STOCKFISH_PATH; print(_STOCKFISH_PATH)"` |
| A2 | `eval_entry._classify_and_insert_flaws`'s population (games with `evals_completed_at IS NULL`) is disjoint from the repair's carrier games | D-04 inventory | A fresh-import game could theoretically resurrect a flaw rederive removed. Confirm by checking the entry-lane queue predicate, or add the advisory lock there too |
| A3 | Prod's orphan proportions resemble dev's (22.5% true orphan vs 36.8% under the strict rule) | Pitfall 6 | The over-deletion magnitude differs; the *mechanism* is verified either way. Measure on prod during the `seed` stage before running `screen` |
| A4 | The 6 `OPENING_CACHE_BACKFILL_SQL` tests all break under a `confirmed` read filter | Pitfall 3 | Fewer/more tests to update than estimated — a plan-time detail, not a design risk |
| A5 | Importing `_upsert_opening_cache` from `eval_drain` into `eval_remote` creates no circular import | CACHEFIX-12 example | Import error at startup; trivially caught by any test run. Verify at plan time with `uv run python -c "import app.main"` |
| A6 | Prod `calibrate` will produce a `confirm_floor` roughly equivalent to ~50cp near equality (the seed's expectation), so `OPENING_CACHE_AGREE_MAX_SCORE_DELTA` is a small number | D-11 | If the measured p99 is large, CACHEFIX-08's promotion becomes too permissive. The constant is written *after* the prod calibrate (D-01 ordering guarantees the number exists), so this self-corrects |
| A7 | The tick currently passes lichess-eval games' opening plies into `engine_targets` (and therefore into `_upsert_opening_cache`), contradicting the "lichess never seeds the cache" rule | Write-Path Anatomy | If true, the cache has a second (small) provenance leak worth a note in the report; if false, the submit-path filter can mirror the tick exactly. Verify against `tests/services/test_full_eval_drain.py:450` |

## Open Questions

1. **`--from-repair-table` host: `backfill_flaws.py` or `opening_cache_repair.py`?**
   - What we know: the seed says extend `backfill_flaws.py`; its existing write path is
     blob-destructive; CACHEFIX-06 forbids a second classifier call site.
   - What's unclear: whether "second call site" means a second call to `classify_game_flaws` (which
     `_classify_and_fill_oracle` already is) or a second module invoking the classifier at all.
   - Recommendation: put the rederive loop in `opening_cache_repair.py` calling
     `_classify_and_fill_oracle` (one classifier writer, unchanged), and add
     `backfill_flaws.py --from-repair-table` as a thin delegating wrapper so the seed's literal
     instruction is honoured. Surface the choice to the user in the plan.

2. **Batched vs. operator-run status-derived marking for CACHEFIX-08.**
   - What we know: Alembic runs on container startup; the marking UPDATE touches ~2.5M rows; no
     batched-migration precedent exists in this repo.
   - Recommendation: batch inside the migration (keyset walk on `full_hash`, 50k rows per statement)
     — it keeps the "no manual production step" property the `initial_fen` migration's docstring
     values. If the user prefers, move it to a `mark-confirmed` subcommand.

3. **`blobs_pending` for rederive.**
   - What we know: `True` suppresses raw ungated tactic tags on brand-new flaws (matching both live
     lanes); `False` restores pre-Phase-143 behaviour.
   - Recommendation: `True`. Record it as a plan decision with the Phase 147 strict-zero rationale.

4. **`opening_cache_audit.status` as `TEXT` vs `SMALLINT`.**
   - What we know: CLAUDE.md says high-cardinality tables use `SMALLINT` + `IntEnum` + `CHECK`;
     2.57M rows is high-cardinality by that rule; the seed and CACHEFIX-01 both specify `TEXT CHECK`.
   - Recommendation: follow the seed (`TEXT` + `CHECK`), document the deviation and its reason
     (operator-facing audit trail, 8 short values, table is not query-hot) in the model docstring.

5. **Does the tick leak lichess-eval opening evals into the cache?** (A7)
   - Recommendation: resolve during planning by reading
     `tests/services/test_full_eval_drain.py::test_dedup_excludes_analyzed_source`; if it leaks, add a
     one-line `is_lichess_eval_game` guard in `_full_drain_tick`'s `engine_targets_for_cache` and note
     it in the report as an additional (small) poison source.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio (`asyncio_mode = "auto"`) |
| Config file | `pyproject.toml:76-86` |
| Quick run command | `uv run pytest tests/scripts/test_opening_cache_repair.py -x -q` |
| Full suite command | `uv run pytest -n auto -x` (CI runs serial — see memory `project_serial_ci_caplog_alembic`) |
| Type gate | `uv run ty check app/ tests/ scripts/` |
| Lint/format | `uv run ruff format app/ tests/ scripts/ analysis/` ; `uv run ruff check . --fix` |
| Function-size gate | `uv run python scripts/check_function_size.py app/ --fail-over-depth 4 --fail-over-loc 200` (app/ only) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | Failing signal | File Exists? |
|--------|----------|-----------|-------------------|----------------|-------------|
| CACHEFIX-01 | 4 tables exist at head; models round-trip; autogenerate emits no diff | integration | `uv run pytest tests/test_alembic_autogen_filter.py tests/models -q` | table missing / autogen emits `drop_table` for an audit table | ❌ Wave 0 |
| CACHEFIX-02 | Every stage refuses out-of-order (`finished_at` unset ⇒ exit non-zero, no writes) | unit | `uv run pytest tests/scripts/test_opening_cache_repair.py -k out_of_order -x` | a stage runs and mutates status rows | ❌ Wave 0 |
| CACHEFIX-02 | Resume: injected `CancelledError` mid-batch leaves statuses + cursor untouched; re-run redoes exactly that batch, no duplicates | unit | `… -k resume -x` | duplicate `opening_cache_repair_rows` PK violation, or a skipped audit row | ❌ Wave 0 |
| CACHEFIX-02 | `--dry-run` writes nothing on every stage | unit | `… -k dry_run -x` | any row count changes | ❌ Wave 0 |
| CACHEFIX-03 | `screen` refuses with unset `screen_floor` | unit | `… -k floor_required -x` | screen proceeds and flags rows | ❌ Wave 0 |
| CACHEFIX-03 | Hash mismatch: a carrier whose replayed hash ≠ cache key is retried up to `MAX_CARRIERS_PER_HASH=3`, then `hash_mismatch`; **never** evaluated, cache untouched | unit (fake pool records boards) | `… -k hash_mismatch -x` | fake pool recorded a board for a mismatched hash, or cache row changed | ❌ Wave 0 |
| CACHEFIX-03 | `screened_clean` vs `flagged` boundary at exactly `screen_floor` (inclusive) | unit | `… -k screen_boundary -x` | off-by-one at the boundary | ❌ Wave 0 |
| CACHEFIX-03 | orphan rule (per Pitfall 6) counts and reports before deleting; `--dry-run` never deletes | unit | `… -k orphan -x` | a cache row deleted under `--dry-run` | ❌ Wave 0 |
| CACHEFIX-04 | `confirmed_bad` overwrites the cache row (cp, mate, best_move, pv); `confirmed_clean` leaves it byte-identical | unit | `… -k confirm -x` | cache row mutated on the clean branch | ❌ Wave 0 |
| CACHEFIX-05 | Old-value predicate: a row carrying a *different* value is NOT touched; a matching row IS; NULL `eval_mate` matches via `IS NOT DISTINCT FROM` | unit | `… -k propagate_predicate -x` | independently-evaluated row rewritten, or the NULL-mate case skipped | ❌ Wave 0 |
| CACHEFIX-05 | Shift: eval lands on row `n.ply - 1`; `best_move`/`pv` on row `n` only when equal to the old cached values | unit | `… -k propagate_shift -x` | eval written to the wrong row | ❌ Wave 0 |
| CACHEFIX-05 | Re-running propagate finds zero rows (idempotent) | unit | `… -k propagate_idempotent -x` | second run rewrites rows | ❌ Wave 0 |
| CACHEFIX-06 | Rederive preserves `allowed_pv_lines`/`missed_pv_lines` + 8 tactic columns on a surviving flaw | unit | `… -k rederive_preserves_blobs -x` | blobs NULLed — the delete-then-insert regression | ❌ Wave 0 |
| CACHEFIX-06 | Rederive removes a now-non-flaw ply, adds a new one, updates `games.{white,black}_{mistakes,blunders}` + accuracy/ACPL | unit | `… -k rederive_counts -x` | oracle columns stale | ❌ Wave 0 |
| CACHEFIX-06 | Rederive clears `games.blobs_completed_at` when a new NULL-blob flaw appears | unit | `… -k rederive_rearm -x` | stamp survives ⇒ game never re-picked by tier-4 | ❌ Wave 0 |
| CACHEFIX-06 | `drill_items` with no surviving `game_flaws` row are pruned; `drill_solves` untouched; `herring_pool` untouched (D-08/D-09) | unit | `… -k rederive_drills -x` | a `drill_solve` or `herring_pool` row deleted | ❌ Wave 0 |
| CACHEFIX-06 / D-04 | Rederive holds `pg_advisory_xact_lock(_game_write_lock_key(gid))`; a concurrent blob submit for a removed ply leaves `game_flaws` empty at that ply and does not 500 | integration | `uv run pytest tests/test_eval_worker_endpoints.py -k blob_submit_no_resurrect -x` | flaw row reappears, or the submit raises `StaleDataError` | ❌ Wave 0 |
| CACHEFIX-06 | Per-game exception ⇒ `status='failed'` + `error` + Sentry capture + loop continues | unit | `… -k rederive_failure -x` | run aborts, or the game is left `pending` with no error | ❌ Wave 0 |
| CACHEFIX-07 | `report` is read-only (row counts unchanged before/after) and writes the dated file | unit | `… -k report -x` | any write, or missing file | ❌ Wave 0 |
| CACHEFIX-08 | candidate → promote on an agreeing second source (`n_sources=2, confirmed=true`, longer pv kept) | unit | `uv run pytest tests/services/test_eval_drain.py -k promote -x` | promotion on first write | ❌ Wave 0 (R2) |
| CACHEFIX-08 | candidate → replace + `disagreements++`; Sentry fires **only** at `disagreements == 2` (D-12) | unit | `… -k disagree -x` | Sentry at the first disagreement | ❌ Wave 0 (R2) |
| CACHEFIX-08 | confirmed rows never overwritten by the tick path | unit | `… -k confirmed_immutable -x` | eval changes | ❌ Wave 0 (R2) |
| CACHEFIX-08 / D-13 | same `source_game_id` neither promotes nor counts as a disagreement | unit | `… -k self_promotion -x` | `n_sources` reaches 2 from one game | ❌ Wave 0 (R2) |
| CACHEFIX-08 | both read paths ignore candidates (`_fetch_dedup_evals` and `_fetch_cached_opening_hashes`) | unit | `uv run pytest tests/services/test_full_eval_drain.py tests/test_eval_worker_endpoints.py -k confirmed_only -x` | candidate transplanted or lease-omitted | ❌ Wave 0 (R2) |
| CACHEFIX-08 | migration marks `screened_clean`/`confirmed_clean`/`repaired` as `confirmed=true, n_sources=2`; everything else candidate | integration | `… -k migration_marking -x` | an unscreened row marked confirmed | ❌ Wave 0 (R2) |
| CACHEFIX-08 | `OPENING_CACHE_BACKFILL_SQL` has a deterministic `ORDER BY` and its gate predicates are unchanged; the 6 gate tests still pass | unit | `uv run pytest tests/services/test_full_eval_drain.py -q` | gate tests fail with an empty dedup map | ✅ exists, needs update |
| CACHEFIX-09 | (skill file — no automated test) | manual | run the `db-report` skill against dev and confirm Checks C+D appear with verdict lines | check missing or unverdicted | n/a |
| CACHEFIX-10 | `legacy-sample` refuses before `calibrate` finished; emits the decision line either way | unit | `… -k legacy_sample -x` | runs without a floor, or emits no decision | ❌ Wave 0 |
| CACHEFIX-12 | An accepted atomic submit leaves cache rows for its opening plies | integration | `uv run pytest tests/test_eval_worker_endpoints.py -k submit_writes_cache -x` | `opening_position_eval` unchanged after the submit | ❌ Wave 0 |
| CACHEFIX-12 | A **second** game reaching the same positions gets them omitted from its lease via `_fetch_cached_opening_hashes` | integration | `… -k lease_shrinks_after_submit -x` | lease still carries the cached plies | ❌ Wave 0 |
| CACHEFIX-12 | A cache-omitted ply (value came from `dedup_map` via `_merge_dedup_pv_into_engine_map`) is **not** written back to the cache | integration | `… -k submit_no_self_write -x` | the cache row's `written_at`/`n_sources` moves on a submit that evaluated nothing | ❌ Wave 0 |
| CACHEFIX-12 | Trusted-operator gating unchanged (401/403 paths still fire) | integration | `uv run pytest tests/test_eval_worker_endpoints.py -k operator_token -q` | auth regression | ✅ exists |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/scripts/test_opening_cache_repair.py -x -q`
  (or the specific file the task touched) + `uv run ty check app/ tests/ scripts/`.
- **Per wave merge:** `uv run pytest tests/scripts/test_opening_cache_repair.py
  tests/test_eval_worker_endpoints.py tests/services/test_eval_drain.py
  tests/services/test_eval_apply.py tests/services/test_full_eval_drain.py
  tests/test_backfill_flaws.py -q`.
- **Phase gate (each of the two squash-merges):** the full CLAUDE.md pre-merge gate —
  `ruff format`, `ruff check --fix`, `ty check` (both venvs), `check_function_size.py`,
  `uv run pytest -n auto -x`, `(cd frontend && npm run lint && npm test -- --run)`.

### Wave 0 Gaps

- [ ] `tests/scripts/test_opening_cache_repair.py` — the bulk of CACHEFIX-02..07/10; needs a
      `_FakePool` (copy `tests/scripts/test_gen_red_herring_pool.py`) and committed-data fixtures
      (copy `tests/test_backfill_flaws.py`'s session-maker injection note).
- [ ] `tests/models/test_opening_cache_audit_models.py` (or fold into an existing models test) —
      CACHEFIX-01 round-trip + CHECK-constraint rejection.
- [ ] New cases appended to `tests/test_eval_worker_endpoints.py` — CACHEFIX-12 (3 cases) and the
      D-04 no-resurrect integration case.
- [ ] New cases appended to `tests/services/test_eval_drain.py` — CACHEFIX-08 candidate/promote/
      disagree/self-promotion (release 2).
- [ ] Updates to the 6 existing `OPENING_CACHE_BACKFILL_SQL` gate tests in
      `tests/services/test_full_eval_drain.py` (release 2).
- [ ] No framework install needed.

### Dev-Smoke Procedure (operator step, success criterion 1)

Run against dev only. **Never** `bin/reset_db.sh`.

1. `docker compose -f docker-compose.dev.yml -p flawchess-dev up -d` (already running).
2. `uv run alembic upgrade head` — confirm the 4 audit tables exist.
3. **Snapshot** `opening_position_eval` (`\copy … to '/tmp/opening_cache_dev_backup.csv' csv`) so the
   smoke is reversible; record the row count (106,615 as of 2026-09-09).
4. **Inject a synthetic poison row** (Pitfall 7): pick a dev cache hash with ≥5 carriers at ply 1..20,
   record its `eval_cp`, `UPDATE opening_position_eval SET eval_cp = 305 WHERE full_hash = …`.
5. `uv run python scripts/opening_cache_repair.py seed --db dev` — assert
   `count(opening_cache_audit) == count(opening_position_eval)`.
6. `… calibrate --db dev --n 50` (small n; dev has few post-2026-08-20 rows) — assert both floors set.
7. `… screen --db dev --limit 200`. Mid-run, `kill -TERM <pid>`. Re-run the same command.
   **Failing signal:** any audit row with two `screened_at` values, any duplicate
   `opening_cache_repair_rows`, or `last_game_id_walked` moving backwards.
8. `… confirm --db dev` — assert the injected hash reaches `confirmed_bad` and the cache row is back
   to its recorded value.
9. `… propagate --db dev` — assert `opening_cache_repair_rows` has one row per carrier at
   `ply = n.ply - 1`, and re-running finds zero.
10. `… rederive --db dev` — assert on one affected game: blobs preserved on surviving flaws,
    `games.blobs_completed_at` cleared if a new flaw appeared, `drill_items` pruned only where the
    flaw is gone, `herring_pool` count unchanged.
11. `… report --db dev` — assert the file lands under `reports/opening-cache-repair/` and the
    verification block runs.
12. `… legacy-sample --db dev --n 20` — assert the decision line prints.
13. Repeat step 7's kill for `confirm`, `propagate` and `rederive` (each must resume cleanly).
14. Restore: re-apply the recorded original `eval_cp` if the repair did not, and diff the cache
    row count against the snapshot; investigate any orphan-driven deletion (Pitfall 6).

### Prod Acceptance (CACHEFIX-11) — queries with failing signals

Run through `bin/prod_db_tunnel.sh`; paste every result into the phase summary.

| # | Assertion | Query | Failing signal |
|---|---|---|---|
| 1 | Cache row repaired | `SELECT eval_cp, best_move FROM opening_position_eval WHERE full_hash = -3185735734450884963;` | `eval_cp` not ≈ +9, or `best_move` ≠ `e2e3` |
| 2 | Audit status | `SELECT status, old_cp, full_cp, delta_score FROM opening_cache_audit WHERE full_hash = -3185735734450884963;` | status ≠ `repaired` |
| 3 | Discovery game evals | `SELECT ply, eval_cp FROM game_positions WHERE game_id = 2356581 AND ply IN (4,5,6) ORDER BY ply;` | ply 5 not ≈ +9, or ply 4 ≠ 9 / ply 6 ≠ 12 (unchanged) |
| 4 | Discovery game flaws | `SELECT ply, severity, is_lucky, is_miss, is_squandered FROM game_flaws WHERE game_id = 2356581 ORDER BY ply;` | any row at ply 5 or 6; **or** the ply-21 severity-2 row missing |
| 5 | Oracle counts | `SELECT white_blunders, black_blunders, white_accuracy, white_acpl FROM games WHERE id = 2356581;` | `white_blunders` ≠ 0 or `black_blunders` ≠ 1 |
| 6 | Carriers cleared | `SELECT count(*) FROM game_positions gp JOIN game_positions prev ON prev.game_id = gp.game_id AND prev.ply = gp.ply - 1 WHERE gp.full_hash = -3185735734450884963 AND prev.eval_cp = 305;` | non-zero (baseline 226 → expect 0) |
| 7 | 9 named hashes | `SELECT full_hash, status FROM opening_cache_audit WHERE full_hash IN (3250950765068847520, -1357424544074167494, 3912952322572315143, -4495720059219567338, -3692655065124884866, 6991966663941067682, -4230257548248121256, -7106566961782875842, -3185735734450884963);` | any status ≠ `repaired` |
| 8 | **Primary signal** — residual histogram vs lichess-internal IQR control | the seed's `width_bucket` query (`SEED-164` §Blast radius, second SQL block) run before and after | any band above the noise floor where `n_cache` materially exceeds `n_ctrl` (baseline 50 vs 20 at 150-250cp, 35 vs 6 at 250-400cp — after repair these must converge) |
| 9 | lichess cross-check | the seed's first SQL block | `n_bad` not dropped from 87 to a handful; each residual must be individually explained as a genuine trap-line depth disagreement |
| 10 | Opening bounce rate (coarse) | `\|eval_P − eval_{P−1}\| ≥ 200 AND \|eval_{P+1} − eval_{P−1}\| ≤ 60`, plies 2-19, engine games, sampled | rate **above** the pre-repair legacy 0.798% / 0.298% — a rise means the repair introduced bounces. A flat rate is expected and acceptable (the poison is only ~0.1-0.2pp) |
| 11 | Benchmark DB untouched | `SELECT count(*) FROM opening_position_eval;` on `:5433` before release 1 | non-zero before CACHEFIX-12 ships (would contradict the "cache-free" diagnosis) |
| 12 | Benchmark lane gains dedup (CACHEFIX-12) | same query after the lane progresses post-release-1 | still 0 rows ⇒ the submit-path cache write is not firing |
| 13 | No benchmark re-clone / `gen_benchmarks` re-run happened | operator attestation in the summary | any benchmark regeneration in the phase's git log |
| 14 | Changelog | `git diff main -- CHANGELOG.md` | no user-facing bullet under `## [Unreleased]` |

## Sources

### Primary (HIGH confidence)

All of the following were opened and quoted this session (2026-09-09):

- `app/services/eval_drain.py` (`_upsert_opening_cache` 437-517, `OPENING_CACHE_BACKFILL_SQL` 181-202,
  `_DEDUP_MAX_PLY` 157, `_full_drain_tick` 875-1140, `_missing_flaw_pv_targets` 520)
- `app/services/eval_apply.py` (`_game_write_lock_key` 121-148, `_collect_full_ply_targets` 210-329,
  `_fetch_dedup_evals` 334-366, `_resolve_full_eval` 369-394, `_post_move_eval` 397-412,
  `_apply_full_eval_results` 648-780, `_classify_and_fill_oracle` 992-1163, `_diff_upsert_flaw_rows`
  1239-1308, `_write_oracle_counts` 1311-1379, `_write_flaw_pvs` 1382-1442, `_classify_with_overlay`
  1445-1504, `_batch_update_flaw_pv_lines` 1782-1813, `_refresh_blobs_completed` 1816-1845,
  `apply_full_eval` 2759-2995)
- `app/routers/eval_remote.py` (`require_operator_token` 173-203, `_fetch_cached_opening_hashes`
  211-232, `_lease_position_redundant` 234-266, `_merge_dedup_pv_into_engine_map` 268-297,
  `_apply_flaw_blob_submit` 951-1080, `_apply_atomic_submit` 1167-1434)
- `app/repositories/game_flaws_repository.py` 133-260 (`bulk_insert_game_flaws`, `TACTIC_TAG_COLUMNS`,
  `FLAW_BLOB_COLUMNS`, `bulk_update_tactic_tags`, `delete_flaws_for_game`, `delete_flaw_plies`,
  `bulk_update_game_flaw_rows`)
- `app/services/eval_entry.py` 545-625, `app/services/eval_queue_service.py` (grep, 731-834)
- `app/services/eval_utils.py` 50-120; `app/services/zobrist.py` 100-180;
  `app/services/engine.py` 100-175, 240-340, 370-470; `app/services/flaws_service.py` 46-48, 81,
  321-360, 946-1030; `app/services/train_pool.py` 1218-1275
- `app/models/opening_position_eval.py` (full), `app/models/game_position.py` (full),
  `app/models/game_flaw.py` 1-80, `app/models/drill_item.py` (full), `app/models/game.py` (grep)
- `alembic/env.py` 1-150; `alembic/versions/20260823_184840_e55d2651a373…py` (full);
  `alembic/versions/20260815_084711_0ac0176294fd…py` (full);
  `alembic/versions/20260727_214735_03df30e3c008…py` 1-60; head-walk over all 122 revisions
- `scripts/backfill_flaws.py` (full), `scripts/resweep_holed_games.py` (full),
  `scripts/gen_red_herring_pool.py` 810-860, `scripts/benchmark_lane.py` 919-969,
  `scripts/import_stress_monitor.py` 378-400, `ls scripts/` + `ls scripts/archive/`
- `tests/conftest.py` 309-378, 553-576; `tests/test_eval_worker_endpoints.py` 60-95, 96-180, 282-340,
  4899-4980, 5330-5525; `tests/scripts/test_gen_red_herring_pool.py` 1-70;
  `tests/test_backfill_flaws.py` 1-50; `tests/test_alembic_autogen_filter.py` 1-60; `pyproject.toml`
  76-98
- `.claude/skills/db-report/SKILL.md` 27-105, 193-330, tail
- `CLAUDE.md`, `docs/dev-tooling.md` 1-35, `CHANGELOG.md` 1-20, `.gitignore` (grep),
  `.planning/notes/eval-completion-columns.md`, `220-CONTEXT.md`,
  `SEED-164-…md`, ROADMAP §Phase 220
- Dev DB measurements via `db_url_for_target('dev')`, 2026-09-09 (row counts, orphan analysis, lichess
  cross-check); `docker ps` for container availability

### Secondary (MEDIUM confidence)

- PostgreSQL 18 docs §5.7.1 "Adding a Column" — metadata-only constant DEFAULT
  [CITED: https://www.postgresql.org/docs/18/ddl-alter.html]
- PostgreSQL 18 `ALTER TABLE` reference — `ACCESS EXCLUSIVE` unless noted
  [CITED: https://www.postgresql.org/docs/18/sql-altertable.html]

### Tertiary (LOW confidence)

- Items A1-A7 in the Assumptions Log.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no external packages; every in-repo symbol was opened and quoted.
- Architecture / write-path anatomy: HIGH — exact signatures, filters and call sites read end to end.
- D-04 concurrency: HIGH for the writer inventory and statement shapes (each grep'd and read);
  MEDIUM for the `eval_entry` disjointness claim (A2).
- Schema / migrations: HIGH in-repo (head walked programmatically); MEDIUM for the PG lock/DEFAULT
  behaviour (official docs, not probed against this server).
- Pitfalls: HIGH — Pitfalls 1-5 and 8-10 are quoted from in-repo docstrings/code; Pitfall 6 and 7 are
  measured against the dev DB this session.
- Test infrastructure: HIGH — fixtures and helpers read at their definition sites.

**Research date:** 2026-09-09
**Valid until:** 2026-10-09 for the in-repo findings (a Phase 22x refactor of `eval_apply.py` would
invalidate the line numbers, not the conclusions); indefinite for the PostgreSQL doc citations.
