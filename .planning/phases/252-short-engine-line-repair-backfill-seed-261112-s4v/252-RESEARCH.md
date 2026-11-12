# Phase 252: Short Engine Line Repair Backfill - Research

**Researched:** 2026-11-12
**Domain:** Operator backfill over prod/benchmark Postgres (Stockfish re-search via python-chess), tier-4 flaw-blob lane changes, benchmark §5 refresh
**Confidence:** HIGH for code paths and engine behaviour (read and probed this session); MEDIUM for sizing (prod numbers not queryable from this agent)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Best-move consistency
- **D-01:** The line re-search is pinned to the stored `best_move` (python-chess `root_moves`), so the repaired pv
  always starts with the stored best move. Answer keys, `game_best_moves`, gem badges and Maia stats stay valid and
  need no recompute. The phase does not overwrite an existing `best_move`.
- **D-02:** Where no `best_move` is stored, or the stored one is illegal in the position, search freely and write
  both the pv and its first move as `best_move`.

#### Re-walk scope and order
- **D-03:** Only the blob whose line was repaired is re-walked. The flaw's other blob and its values stay
  untouched. The tier-4 selector keys on `allowed_pv_lines IS NULL` today and must be extended so a flaw with only
  one NULL line is picked up, and the submit must write only that line.
- **D-04:** Processing order is newest games first (by game date, across all users), for the line repair and for
  the re-walk. The re-walk therefore needs an ordered claim instead of the random lottery, for this backfill.

#### Bound-valued evals
- **D-05:** Evals are not repaired in this phase. The pilot measures, on a sample, how many mistake/blunder
  classifications would flip between the stored eval and an exact re-search. If the flip rate is material, capture
  a follow-up seed; do not widen this phase.
- **D-06:** Blob node values of untouched walks and all `game_best_moves` rows stay as they are. Only re-walked
  blobs get exact values. No badge measurement.

#### Run mechanics
- **D-07:** The line repair is an operator script run from the owner's box: local Stockfish pool, writes over the
  DB tunnel, resumable, with a `--db` switch in the style of `scripts/retag_flaws.py`. No new server endpoint and
  no worker release for the line repair.
- **D-08:** During the line repair the worker on that box is stopped and the script uses all engines. Live
  analysis relies on the server pool; the script does not check for other version-3 workers (owner's call: the
  server pool is enough at 1-5k new games a day).
- **D-09:** Step order: prod line repair, then prod re-walk on the fleet, with the benchmark line repair on the
  owner's box running alongside the prod re-walk. Benchmark re-walk, retag and zone refresh last.
- **D-10:** A 1% pilot runs first. If it passes, the full runs start automatically, without waiting for the owner.
  The run stops and returns to the owner when any of these holds:
  - more than about 3% of re-searched lines are still 1-2 plies, mates excluded (repair does not stick);
  - measured throughput puts the prod line repair beyond 10 days or the re-walk beyond 8 weeks;
  - any failed batch, a row-count mismatch, or prod DB connections or latency climbing during pilot writes;
  - the eval measurement (D-05) shows more than about 2% of mistake/blunder classifications flipping.
  The thresholds are named constants in the script, not prose.
  — **Reversibility:** one-way — the repair overwrites `game_positions.pv` and blob columns in place on prod; there
  is no stored copy of the old values, so the pilot gates and a dry-run mode are the only safety net.

### Claude's Discretion
- Batch sizes, commit cadence, progress reporting and the report format of the scripts.
- How the ordered re-walk claim is implemented (flag on the existing tier-4 claim, or a backfill-only claim).
- Whether the benchmark runs reuse the same script unchanged or need lane-specific handling.
- The exact SQL for excluding legitimately short lines (mate scores and terminal positions).

### Deferred Ideas (OUT OF SCOPE)
- Full or partial re-evaluation of bound-valued evals: only if the D-05 measurement shows a material flip rate;
  would be its own phase.
- Recomputing gem and great-move badges from exact best-move values.
- Regrading `drill_solves` solved against short lines.
- The stale `ANALYSIS_FREE_RUN_MIN_MULTIPV` doc comment in `frontend/src/pages/Analysis.tsx` (the second line is
  not always present); fix when Phase 249 has merged.

Reviewed Todos (not folded): `todo.match-phase` returned keyword-only matches; none relates to this phase.
</user_constraints>

<phase_requirements>
## Phase Requirements

No requirement IDs (ROADMAP: "Requirements: TBD"). The planner should map plans to the five CONTEXT scope items:

| Scope item | Description | Research support |
|---|---|---|
| S1 | Re-search stored 1-2 ply non-terminal `game_positions.pv` rows with the fixed wrapper | Pattern 1 (pinned search), Pattern 2 (selector SQL), Pitfalls 1-4 |
| S2 | Re-walk only the repaired blob line through tier 4 | Pattern 3 (fill-NULL-only tier-4), Pattern 4 (just-in-time feeder), Pitfalls 5-8 |
| S3 | Pick up `[]` opening-line sentinels whose position has no usable pv | Pattern 2 (selector B), feeder predicate |
| S4 | Benchmark: repair, re-walk, retag, §5 re-run, `tactic_delta_zones.py` update | "Benchmark lane" section, Pitfall 10 |
| S5 | D-05 flip measurement (no repair) | Pattern 5 |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Python 3.14, SQLAlchemy 2.x async `select()`, asyncpg; httpx only; no `requests`.
- **Never `asyncio.gather` on the same `AsyncSession`**; open no session during the engine gather.
- ty must pass with zero errors (`uv run ty check app/ tests/ scripts/`); explicit return types; `Literal[...]` for fixed sets (e.g. `--db`, line `"allowed" | "missed"`); `Sequence[...]` params; suppress only with `# ty: ignore[rule]` + reason.
- No magic numbers: every threshold (D-10 gates, batch sizes, windows, timeouts) is a named constant.
- Nesting depth <= 4 in `app/` (gated by `scripts/check_function_size.py app/ --fail-over-depth 4`); aim for 3; ~100 logic lines per function soft.
- Sentry: `capture_exception` in non-trivial excepts in `app/services`/`app/routers`; never embed variables in messages; use `set_context`/`set_tag`.
- Comment bug fixes at the fix site.
- Time-dependent endpoints use `dev_now_utc` (not relevant to the scripts, relevant if any endpoint changes).
- Pre-merge gate (MANDATORY before squash-merge): ruff format/check, ty (app/tests/scripts and analysis/), function-size gate, `uv run pytest -n auto -x`, frontend lint/build/test/knip.
- `bin/reset_db.sh` never; `bin/deploy.sh` is the only deploy path; deploy is the owner's call.
- Changelog bullet under `## [Unreleased]` when the phase merges.
- Prod: `max_connections=50`, app pool up to 20, keep all operator connections under ~25 (`docs/production-runbook.md:36`).
- GSD scope discipline: no unplanned features; flag rather than implement.

## Summary

The phase has three engineering parts and one long operational tail. (1) A new operator script re-searches short stored lines with the already-fixed `EnginePool` wrapper, pinned to the stored best move via python-chess `root_moves`, which needs one keyword threaded through `_acquire_and_analyse` -> `_collect_analysis_infos` -> `protocol.analysis(...)`. A real-Stockfish probe this session confirmed that a pinned 1M-node search spends the full node budget, returns `pv[0] == pinned move` and an 18-31 ply line, and that native Stockfish 18 **silently ignores an illegal `searchmoves` move and searches freely**, so legality must be checked in Python before pinning. (2) The tier-4 blob lane must learn per-line NULLs: the claim itself is game-level (`games.blobs_completed_at IS NULL`) and needs no change, but `_refresh_blobs_completed`, `_build_flaw_blob_lease_positions`, `_apply_flaw_blob_submit` and the two sentinel branches of `/flaw-blob-lease` all key on `allowed_pv_lines IS NULL` and all write **both** blob columns. Switching the tier-4 write to a fill-NULL-only (`COALESCE(existing, new)`) UPDATE makes all three write sites safe for single-line re-walks at once. (3) A blocking discovery: the prod in-process server-pool drain (`EVAL_AUTO_DRAIN_ENABLED` defaults to `true` in `docker-compose.yml:106`) claims tier-4 games through `claim_eval_job` and runs the **full** every-ply re-evaluation path (`_full_drain_tick`), which overwrites `eval_cp`, re-classifies flaws (diff/upsert) and rebuilds both blobs. Any repaired game that the server pool picks would violate D-03, D-05 and D-06. The drain must route `TIER_BLOB_BACKFILL` claims to a blob-only tick (or skip tier 4).

The ordering decision (D-04) is best met without touching the hot claim SQL: NULL the repaired lines **just in time**, in newest-first windows, from an operator "feeder" that tops up a small pending window. Up-front NULLing would remove the affected blunders from the Train pool (`answer_key_present` requires a non-NULL, non-empty `missed_pv_lines`), inflate `blob_pending_count`, and drop the games from the Library tactic comparison (`Game.blobs_completed_at.isnot(None)`) for the whole multi-week re-walk. An ordered in-server claim would also need a new partial index (a migration) to avoid a top-N sort over the whole pending set on every worker poll, the exact failure mode the tier-4 docstring documents (84.8% of prod DB time before `blobs_completed_at` existed). The feeder keeps the pending set small, so the existing lottery stays cheap and approximately newest-first.

The re-walk only gets fleet time when rung 3 (`/atomic-lease?scope=idle`, tier-3 never-analyzed backlog) is empty, because workers try rungs in order (`scripts/remote_eval_worker.py` `_run_cycle`). The 3.5-week estimate assumes no tier-3 backlog and v3 workers (the Hetzner boxes were on schema 2). Both are prod facts the orchestrator must read before the re-walk projection is meaningful.

**Primary recommendation:** One operator script `scripts/repair_short_lines.py` with subcommands (`repair`, `feed`, `measure-flips`, `status`), a 6-line `root_moves` thread-through in `engine.py`, a fill-NULL-only tier-4 write path with per-line lease/tag logic, and a blob-only branch for `TIER_BLOB_BACKFILL` in `_full_drain_tick`. No migration, no worker release, no schema-version bump; one server deploy before the re-walk.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|---|---|---|---|
| Pinned line re-search (S1) | Operator script on owner's box (local `EnginePool`) | DB (writes over tunnel) | D-07: no endpoint, no worker release; CPU stays off prod |
| Short-line / sentinel selection | DB (SQL over `game_flaws` + `game_positions`) | Script (python-chess terminal check) | Mate exclusion is SQL; terminal/draw endings need board replay |
| Re-walk ordering + NULLing (S2) | Operator feeder script | DB | Keeps hot claim SQL unchanged, bounds user-visible gap |
| Re-walk compute | Remote worker fleet (tier-4 rung 4) | Server pool (blob-only drain tick) | Existing lane; worker is token-opaque, no release needed |
| Blob assembly, tag re-derivation, Maia re-score | API/backend (`_apply_flaw_blob_submit`) | — | Server-authoritative today; extend per line |
| D-05 flip measurement | Operator script (read-only + local engines) | — | No writes |
| §5 refresh, zone registry | Benchmark DB + `scripts/benchmarks/chapter5.py` | `app/services/tactic_delta_zones.py` (code) | Existing fast path and registry rule |

## Standard Stack

No new packages. Everything uses what the repo already pins.

### Core
| Library | Version | Purpose | Why Standard |
|---|---|---|---|
| python-chess (`chess`) | 1.11.2 [VERIFIED: uv.lock:369-370] | `UciProtocol.analysis(..., root_moves=...)`, PGN replay, terminal checks | Already the engine layer; `root_moves` is a first-class kwarg |
| Stockfish | 18 [VERIFIED: `~/.local/stockfish/sf` `id name Stockfish 18`] | 1M-node searches | Same binary as fleet |
| SQLAlchemy async + asyncpg | repo pins | DB I/O | Project standard |
| sentry_sdk | repo pins | script error capture | Same pattern as `retag_flaws.py` |

### Supporting (in-repo, reuse, never re-implement)
| Asset | Purpose |
|---|---|
| `app/services/engine.py` `EnginePool`, `_select_final_infos`, `_pv_to_uci_string`, `PV_CAP_PLIES` | fixed wrapper, pv string cap |
| `app/services/eval_apply.py` `pv_ply_count`, `cached_pv_usable`, `CACHED_PV_MIN_PLIES`, `_walk_pv_boards`, `_game_write_lock_key` | short-line rule, walk semantics, per-game lock |
| `app/services/flaws_service.py` `_recompute_fen_map`, `_classify_tactic_gated`, `_ply_to_es`, `_classify_mate_ladder`, `classify_severity` | full FEN map, tag path, severity ladder (D-05) |
| `app/core/config.py` `db_url_for_target` | `--db dev|benchmark|prod` resolution |
| `scripts/retag_flaws.py` | final engine-free retag sweep (benchmark; optional prod) |
| `scripts/benchmarks/chapter5.py` `compute()` / `python -m scripts.benchmarks.chapter5` | §5 fast path |

**Installation:** none. Fresh worktree setup: `uv sync --group maia-inference` (memory: otherwise 3 phantom ty errors) and `cd frontend && npm ci` before the pre-merge gate. The worktree currently has no `.venv` [VERIFIED: `ls -a` this session].

## Package Legitimacy Audit

No external packages are installed by this phase. Audit not applicable.

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
                          OWNER'S BOX (worker stopped, D-08)
 games (newest first) ──► [repair] work list ──► per batch: load flaws + pv rows (k-1,k)
                                                     │
                                       SQL: pv <= 2 plies AND row k-1 eval_mate IS NULL
                                       (+ [] sentinel at ply<=20 with NULL/short pv)
                                                     │
                                       Python: replay PGN, drop terminal/draw-ending lines
                                                     │
                              best_move legal? ──yes──► pinned search (root_moves=[best_move])
                                                no/NULL ─► free search, also write best_move (D-02)
                                                     │
                                  guarded UPDATE game_positions.pv (IS NOT DISTINCT FROM old)
                                                     │                    │
                                           report + gates (D-10)     undo log (optional)
                                                     │
                 ┌───────────────────────────────────┘
                 ▼
 [feed] newest-first windows: lines whose blob is shorter than its pv allows
        ──► SET <that column> = NULL (SQL literal), games.blobs_completed_at = NULL
                 │                        (top up when pending window < LOW_WATER)
                 ▼
 PROD SERVER: _claim_tier4_blob (unchanged lottery over the small pending set)
        ├─► /flaw-blob-lease ──► lease only NULL lines ──► FLEET (v3 workers, MultiPV-2)
        │                                                   │
        │   /flaw-blob-submit ◄─────────────────────────────┘
        │        fill-NULL-only blob write, tags for NULL lines only, _refresh_blobs_completed (OR probe),
        │        Maia re-score
        └─► server-pool drain (claim_eval_job bundled path) ──► NEW blob-only tick (no eval rewrite)

 [measure-flips] sample engine games ──► exact re-search (and a control re-search) ──► severity flip report
```

### Recommended Project Structure
```
scripts/repair_short_lines.py          # subcommands: repair | feed | measure-flips | status
app/services/engine.py                 # root_moves kwarg threaded through (D-01)
app/services/eval_apply.py             # per-line NULL probe/lease, fill-NULL-only writer, shared blob-apply core
app/routers/eval_remote.py             # lease/submit use the per-line helpers
app/services/eval_drain.py             # TIER_BLOB_BACKFILL -> blob-only tick
tests/scripts/test_repair_short_lines.py
tests/services/test_engine_bound_lines.py (+ root_moves cases) / tests/services/test_engine_nodes.py (real SF)
tests/test_eval_worker_endpoints.py    (+ single-NULL-line lease/submit/sentinel cases)
tests/services/test_eval_apply.py      (+ OR probe, fill-NULL-only writer)
tests/services/test_full_eval_drain.py (+ blob-only tick keeps evals)
reports/line-repair/                   # committed run reports (pilot, full, flips)
temp/line-repair/                      # gitignored: work list, cursor, optional undo log
```

### Pattern 1: Pinned search through the fixed wrapper (D-01, D-02)

**Current code** [VERIFIED: app/services/engine.py:459-477, 601-687]: `_collect_analysis_infos(protocol, board, limit, multipv)` calls `await protocol.analysis(board, limit, multipv=multipv)`; `_acquire_and_analyse(self, board, limit, timeout, *, multipv: int | None = None)` wraps it and returns `_select_final_infos(infos, multipv)`. `_select_final_infos` guarantees, per multipv index, "last exact line (pv, no bound key), else last bound line (pv), else last score-only line" and returns the raw line objects unmerged (docstring at engine.py:426-441).

**python-chess API** [VERIFIED: installed chess/engine.py:1705 `async def analysis(self, board, limit=None, *, multipv=None, game=None, info=INFO_ALL, root_moves: Optional[Iterable[chess.Move]] = None, options={})`; :1574-1580 `if root_moves is not None: builder.append("searchmoves") ...`]. python-chess does **not** validate root moves.

**Probe this session** (Stockfish 18, Hash 32, Threads 1, `Limit(nodes=1_000_000)`, raw stream, last exact line) [VERIFIED: scratchpad probe output]:

| Position | Pin | pv[0] | pv plies | nodes | wall |
|---|---|---|---|---|---|
| repro FEN `8/p6R/4rkp1/...` | a7a6 (= free best) | a7a6 | 26 | 1,000,157 | 0.81s |
| same | f6g5 (not best) | f6g5 | 28 | 1,000,330 | 0.87s |
| Italian middlegame | f3g5 (= best) | f3g5 | 28 | 1,000,453 | 1.39s |
| 1.e4 | e7e5 (= best) | e7e5 | 31 | 1,000,152 | 1.14s |
| repro FEN | **e2e4 (illegal)** | **a7a6** (free search) | 1 (a trailing lowerbound line) | 200,217 | — |

So: pinning does not short-circuit the search under a node limit, and an illegal pin silently degrades to a free search.

**Change:** add `root_moves: Sequence[chess.Move] | None = None` (keyword-only, default None so every existing caller is byte-identical) to `_collect_analysis_infos` and `_acquire_and_analyse`, pass it into `protocol.analysis(...)`, and add a public method (or a kwarg on `evaluate_nodes_with_pv`) for the script. MultiPV stays None (the remote atomic lane stores per-ply pv at MultiPV-1, `scripts/remote_eval_worker.py:293-307`).

```python
# Source: app/services/engine.py (proposed delta; existing names verbatim)
async def _collect_analysis_infos(
    protocol: chess.engine.UciProtocol,
    board: chess.Board,
    limit: chess.engine.Limit,
    multipv: int | None,
    root_moves: Sequence[chess.Move] | None = None,
) -> list[chess.engine.InfoDict]:
    analysis = await protocol.analysis(board, limit, multipv=multipv, root_moves=root_moves)
    ...
```

Script-side contract (pure helper, unit-testable):
```python
def pick_pin(board: chess.Board, stored_best_move: str | None) -> chess.Move | None:
    """D-01/D-02: the stored best move when legal in `board`, else None (free search)."""
    if not stored_best_move:
        return None
    try:
        move = chess.Move.from_uci(stored_best_move)
    except ValueError:
        return None
    return move if board.is_legal(move) else None
```
After the search: if pinned and `pv[0] != pin`, treat as a failed row (defence in depth for the silent-drop behaviour). If not pinned (D-02), write `best_move = pv[0]` in the same UPDATE.

### Pattern 2: Selecting what to repair (S1 + S3)

Storage facts [VERIFIED: app/services/eval_apply.py:443-456 `_post_move_eval` "the eval stored at row `ply` is the eval of the position AFTER the move at `ply`"; app/models/game_position.py:139 `move_san` "SAN of the move played FROM this position (leading to ply+1)"; eval_apply.py:1969-1977 flaw lines `("missed", flaw_ply), ("allowed", flaw_ply + 1)`]:
- `pv` at row k is the line from position k; the eval OF position k is on row k-1.
- Missed line of flaw N walks `pv` at row N; allowed line walks `pv` at row N+1. One repaired row k can feed two lines: missed of flaw k and allowed of flaw k-1.
- `pv` is written only at flaw plies N and N+1 (`_write_flaw_pvs`, eval_apply.py:1420-1465), so drive selection from `game_flaws`, not a scan of 75M `game_positions` rows.

**Selector A (short lines), validated read-only on the dev DB this session:**
```sql
-- per batch of game ids (newest first); node0 rows of every flaw
WITH node0 AS (
  SELECT DISTINCT f.user_id, f.game_id, n.node0_ply
  FROM game_flaws f
  CROSS JOIN LATERAL (VALUES (f.ply), (f.ply + 1)) AS n(node0_ply)
  WHERE f.game_id = ANY(:game_ids)
)
SELECT n.user_id, n.game_id, n.node0_ply, gp.pv, gp.best_move
FROM node0 n
JOIN game_positions gp
  ON gp.user_id = n.user_id AND gp.game_id = n.game_id AND gp.ply = n.node0_ply
LEFT JOIN game_positions prev
  ON prev.user_id = n.user_id AND prev.game_id = n.game_id AND prev.ply = n.node0_ply - 1
WHERE gp.pv IS NOT NULL
  AND array_length(string_to_array(gp.pv, ' '), 1) < :min_plies   -- CACHED_PV_MIN_PLIES = 3
  AND prev.eval_mate IS NULL;                                       -- mate score of position k
```
Use `CACHED_PV_MIN_PLIES` (eval_apply.py:113, value `3`) as the bound so the repair and the cache share one definition [VERIFIED: eval_apply.py:113 `CACHED_PV_MIN_PLIES: int = 3`]. `LEFT JOIN prev` keeps flaws at ply 0 (no row -1). Dev numbers (dev DB, not prod): 66,018 pv rows, 14,805 short (22.4%), 735 of those excluded by the mate rule, 248 short rows with `best_move IS NULL`, 132 short rows whose `pv` first move differs from `best_move`.

**Terminal / draw endings (Python, after SQL):** replay the game PGN once per game (keep the move stack so repetition is visible), walk the stored pv with `_walk_pv_boards` semantics, and skip the row when the final board `is_game_over(claim_draw=True)` (checkmate, stalemate, insufficient material, threefold/fifty-move claimable). Count these as `legit_short` in the report; they are the ~6% "legitimately short" class from the seed (1,947 of 33,501). They must be excluded **before** the D-10 "still short" denominator, otherwise they alone trip the 3% gate.

**Selector B (S3, `[]` opening sentinels):** a flaw line whose blob is `'[]'::jsonb`, whose node0 ply `<= DEDUP_MAX_PLY` (`DEDUP_MAX_PLY: int = 20`, app/models/game_position.py:44 [VERIFIED]), whose node0 position is non-terminal, and whose node0 `pv IS NULL` or is short. Repair = search and write the pv (and best_move when NULL). Dev has 24 allowed + 96 missed such lines with NULL pv, 0 with a short pv; count prod in the pilot.

**Dedupe:** on dev, opening short rows dedupe only 2,844 -> 2,708 distinct `(full_hash, best_move)` keys (5%). Recommend no cross-batch dedupe unless the prod pilot shows a materially higher duplicate share.

**Guests:** the tier-4 lottery excludes guests, so a guest game's repaired line would never be re-walked. Recommend excluding guest users from the repair work list [ASSUMED: owner preference; dev had 0 guest short rows].

### Pattern 3: Tier-4 lane per-line NULLs (D-03)

Every site that keys on, or writes, the blob columns [VERIFIED by Read this session]:

| Site | Today | Change |
|---|---|---|
| `_claim_tier4_blob` (eval_queue_service.py:711-836) | games-only predicate `full_evals_completed_at IS NOT NULL AND blobs_completed_at IS NULL`, backed by `ix_games_blob_backfill_pending` | **none** (the feeder clears `blobs_completed_at`) |
| `_refresh_blobs_completed` (eval_apply.py:1851-1880) | probe `allowed_pv_lines IS NULL`, stamps/clears `games.blobs_completed_at` | probe `allowed_pv_lines IS NULL OR missed_pv_lines IS NULL`; uses the `game_id` index per game, no new index needed |
| `_build_flaw_blob_lease_positions` (eval_apply.py:1883-1989) | flaws with `allowed_pv_lines IS NULL`; leases both lines | select `ply` + which columns are NULL; lease/sentinel only NULL lines |
| `/flaw-blob-lease` all-sentinel branch (eval_remote.py:906-916) | writes `([], [])` for each sentinel ply | fill-NULL-only write |
| `/flaw-blob-lease` over-cap branch (eval_remote.py:928-942) | selects `allowed IS NULL` plies, writes `([], [])` | OR predicate; fill-NULL-only write |
| `_apply_flaw_blob_submit` (eval_remote.py:954-1123) | NULL plies by `allowed IS NULL`; tags all 8 columns; `_batch_update_flaw_pv_lines` writes both columns | per-line NULL set from the read phase; tags only for NULL lines (4 columns per line); fill-NULL-only write; idempotency gate "no NULL line left" |
| `_batch_update_flaw_pv_lines` (eval_apply.py:1817-1848) | `SET allowed_pv_lines = v..., missed_pv_lines = v...` | **leave as is** (shared with `_diff_upsert_flaw_rows`, eval_apply.py:1348, which must overwrite); add a sibling fill-NULL-only writer |

Fill-NULL-only writer (the key simplification: callers can keep passing `([], [])` or a both-line map; existing non-NULL blobs are never touched, so D-03 holds at all three write sites, and a both-NULL flaw behaves exactly as today):
```python
# Source: modelled on _batch_update_flaw_pv_lines (eval_apply.py:1817-1848)
sql = sa.text(
    "UPDATE game_flaws"
    " SET allowed_pv_lines = COALESCE(game_flaws.allowed_pv_lines, v.allowed_pv_lines),"
    "     missed_pv_lines  = COALESCE(game_flaws.missed_pv_lines,  v.missed_pv_lines)"
    f" FROM (VALUES {values_sql}) AS v(ply, allowed_pv_lines, missed_pv_lines)"
    " WHERE game_flaws.game_id = :game_id AND game_flaws.ply = v.ply"
)
```
Never bind Python `None` into a JSONB slot here; always pass a JSON list (the assembler already returns `[]` for unleased lines).

Tag re-derivation: `_classify_tactic_gated(n, fen_map, positions, orientation, pv_blob, pre_flaw_eval_cp, ...)` [VERIFIED: flaws_service.py:679-689] is per-orientation; the allowed result depends only on the allowed blob and `positions[ply+1].pv`. Compute and write only the re-walked orientation's four columns (`bulk_update_tactic_tags` is an ORM bulk UPDATE by PK, so a dict with PK + four tag keys updates only those four, repositories/game_flaws_repository.py:198-217).

Maia: `score_game_flaws_after_apply` already runs after a non-empty submit (eval_remote.py:1118-1121) and rebuilds from `games.pgn`; it covers the D-02 `best_move` writes too, since every D-02 row is a short row whose line gets re-walked.

**No migration, no worker release, no schema-version bump.** Tokens stay `"{flaw_ply}:{line}:{node_k}"` and the worker is token-opaque. `WORKER_SCHEMA_VERSION_MIN: int = 3` [VERIFIED: eval_remote.py:166] and `WORKER_SCHEMA_VERSION: int = 3` [VERIFIED: scripts/remote_eval_worker.py:118] already gate `/flaw-blob-lease`. One server deploy is required before the re-walk (prod), and a restart of the `:8001` benchmark backend on the new code before the benchmark re-walk.

### Pattern 4: Just-in-time re-walk feeder (D-04)

**Re-walk predicate (stateless, validated on dev):** a line needs a re-walk when its stored blob is shorter than the walk its current pv allows. Walk length is `1 + min(n, PV_CAP_PLIES)` boards; only even nodes are leased, odd indices are placeholders, so a complete blob has `2 * floor(min(n, 12) / 2) + 1` elements [VERIFIED: eval_apply.py:1977-1987 lease loop, 2034-2052 assembler; engine.py:109 `PV_CAP_PLIES: int = 12`].
```sql
-- per line (node0_ply = flaw.ply for missed, flaw.ply + 1 for allowed)
blob IS NOT NULL
AND gp.pv IS NOT NULL
AND jsonb_array_length(blob) < 2 * (LEAST(array_length(string_to_array(gp.pv, ' '), 1), 12) / 2) + 1
```
It catches repaired short lines (1-element or 3-element blob, now 12-ply pv) and S3 `[]` lines once their pv is written. On dev before any repair it matches only 21 allowed + 12 missed lines (node gaps), so it is a clean signal after the repair.

**Feeder loop (operator script, owner's box, one DB connection):**
1. Work list = the same newest-first game list the repair used (frozen at start, cursor persisted under `temp/line-repair/`).
2. Every `FEED_POLL_S`, count pending games in the fed set (`blobs_completed_at IS NULL`). When below `FEED_LOW_WATER`, take the next `FEED_BATCH_GAMES` games, and in one transaction: `UPDATE game_flaws SET <col> = NULL` (SQL literal NULL, never an ORM `None`, see Pitfall 6) for each line matching the predicate (predicate re-evaluated inside the UPDATE, so it is idempotent), then `UPDATE games SET blobs_completed_at = NULL WHERE id = ANY(:ids)` for the games with at least one NULLed line. Take `pg_advisory_xact_lock(_game_write_lock_key(game_id))` per game, the same lock the submit path takes (eval_remote.py:1080-1083).
3. Report per window: lines NULLed, games fed, drain rate (games/h, lines/h), projected weeks remaining (D-10 8-week gate).

Why not an ordered in-server claim: an `ORDER BY played_at DESC` claim over a large pending set runs on every worker poll and needs a new partial index on `(played_at) WHERE <pending>` (a migration) to avoid a sort per call; the tier-4 docstring records what a scan-shaped claim cost before (eval_queue_service.py:723-738). It also does not fix the user-visible gap of up-front NULLing (Pitfall 7). With a small fed window the existing ES lottery (user pick weighted by `last_activity`, game pick by recency and TC) drains the window in hours, which gives newest-first at window granularity. If the owner insists on strict in-window order, the fallback is a server env flag that switches Stage 2 to `ORDER BY played_at DESC` **within the picked user**, which stays cheap under `ix_games_user_played_at`.

### Pattern 5: D-05 flip measurement

Severity of the move at ply n uses rows n-1 and n [VERIFIED: flaws_service.py:398-410 `_run_all_moves_pass`: `es_before = _ply_to_es(positions[n - 1], mover)`, `es_after = _ply_to_es(positions[n], mover)`, mate ladder when either row has `eval_mate`, else `classify_severity(es_before - es_after)`; thresholds `INACCURACY_DROP: float = 0.05`, `MISTAKE_DROP: float = 0.10`, `BLUNDER_DROP: float = 0.15` at flaws_service.py:47-49].

Design:
- Sample engine-evaluated games only (`full_evals_completed_at IS NOT NULL AND lichess_evals_at IS NULL`; lichess evals are lichess's). Sample by `md5(id::text)` residue (benchmark DB is not static; same habit on prod). Re-search **every** position of each sampled game (position n+1 is shared by moves n and n+1, so whole games cost about one search per ply). About 200 games x ~80 plies is ~16k searches, under an hour on 8 engines.
- Re-search unpinned, 1M nodes, MultiPV-1 (the remote atomic lane's mode; the server-pool drain stores MultiPV-2 evals, so mode mismatch is part of the noise) [ASSUMED: which mode wrote most stored evals].
- Rebuild per-ply eval rows with the post-move shift (eval of position n+1 on row n), and run the **same** functions (`_ply_to_es`, `_classify_mate_ladder`, `classify_severity`) on stored vs re-searched rows. Report: of stored M/B moves, the share that drop below mistake or change severity; of stored non-M/B moves, new M/B per stored M/B.
- **Control arm:** a second independent re-search of the same positions (clear hash between arms, e.g. a fresh pool). Exact-vs-exact flips are pure search non-determinism (memory: eval_cp is not reproducible across runs). Report the gate number as D-10 defines it (stored vs exact) and the control next to it; when the raw rate trips 2%, the stop returns to the owner with both numbers.

### Anti-Patterns to Avoid
- **Up-front NULLing of all repaired blobs:** weeks-long Train pool, Library tactic and `blob_pending_count` regressions (Pitfall 7).
- **Reusing `_batch_update_flaw_pv_lines` for the tier-4 path:** it overwrites the untouched line.
- **Passing `root_moves` without a Python legality check:** Stockfish drops illegal moves and searches freely.
- **`update(GameFlaw).values(missed_pv_lines=None)`:** writes `null::jsonb`, not SQL NULL (Pitfall 6).
- **Scanning `game_positions` for `pv IS NOT NULL`:** 75M rows on prod; drive from `game_flaws` per batch.
- **Holding a DB session open across the engine gather;** open short sessions per batch read and per batch write.
- **Running the multi-day repair from an executor subagent:** executors die (~40 min); launch from the orchestrator with `setsid nohup` + Monitor.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---|---|---|---|
| Final-line selection from Stockfish | parsing `analysis.multipv` / `analysis.info` | `EnginePool._acquire_and_analyse` -> `_select_final_infos` | merged dict keeps a stale `lowerbound` key (j47 SUMMARY) |
| pv string formatting / cap | own join/cap | `_pv_to_uci_string` (cap `PV_CAP_PLIES`) | same 12-ply cap as stored lines |
| Short-line rule | a new literal `<= 2` | `pv_ply_count` / `CACHED_PV_MIN_PLIES` | single definition shared with the opening cache |
| Full FEN per ply | replay from `game_flaws.fen` | `_recompute_fen_map(pgn)` | castling / en-passant correctness (Phase 221) |
| Tactic re-derivation | calling detectors directly | `_classify_tactic_gated` | the live classify path (no drift) |
| Severity for D-05 | re-implementing drop math | `_ply_to_es`, `_classify_mate_ladder`, `classify_severity` | mate ladder is subtle |
| DB target resolution | own URLs | `db_url_for_target` | `.env`-sourced, never printed |
| Per-game write serialization | ad hoc locks | `pg_advisory_xact_lock(_game_write_lock_key(game_id))` | same key space as the submit path |
| §5 zones | hand SQL, hand-transcribed literals | `python -m scripts.benchmarks.chapter5`, then derive literals mechanically (`../flawchess/temp/261014-rux/derive_bands.py` precedent, gitignored in the main checkout) | skill rule "Generate, never hand-transcribe" |

## Runtime State Inventory

| Category | Items Found | Action Required |
|---|---|---|
| Stored data | prod `game_positions.pv` short rows (~3.4M, seed); `game_flaws.allowed_pv_lines` / `missed_pv_lines` built from them; `[]` opening sentinels; `games.blobs_completed_at` stamps; benchmark DB equivalents (~1M short rows) | data repair (script), feeder NULL + re-walk, `blobs_completed_at` reset by feeder |
| Live service config | worker fleet `worker_schema_version` (Hetzner boxes were 2 at context time); benchmark `:8001` backend runs whatever checkout it was launched from; prod `EVAL_AUTO_DRAIN_ENABLED` default `true` (docker-compose.yml:106 [VERIFIED]) | update workers to v3 (git pull + restart); restart `:8001` on new code; server deploy with the drain fix |
| OS-registered state | owner's-box remote worker process (stop during repair, D-08; restart for the re-walk) | operator step |
| Secrets/env vars | none renamed; `DATABASE_URL_PROD`/`_BENCHMARK` read via `db_url_for_target`; `:8001` launch flags per runbook | none |
| Build artifacts | worker Docker image (`Dockerfile.worker`) built from repo; no change needed (no worker code change) | none |

## Common Pitfalls

### Pitfall 1: Illegal pin silently becomes a free search
**What goes wrong:** pv starts with a different move than `best_move`; answer key and pv disagree.
**Why:** native Stockfish ignores illegal `searchmoves` (probe above); python-chess sends them unchecked.
**How to avoid:** `pick_pin` legality check; post-check `pv[0] == pin` else count as failed row.
**Warning signs:** report column `pin_mismatch > 0`.

### Pitfall 2: Legitimately short lines trip the 3% gate
**What goes wrong:** mate-in-1/2 and lines ending in stalemate/insufficient material/repetition re-search short again.
**How to avoid:** SQL mate exclusion on row k-1 plus Python game-over check on the pv end (with move stack); evaluate the new result the same way (new score is mate, or new pv ends game over) before counting it as "still short".

### Pitfall 3: Concurrent writers on the same game
**What goes wrong:** an atomic re-lease or the PV-recovery pass writes `pv` between the script's read and write.
**How to avoid:** guarded UPDATE `WHERE gp.pv IS NOT DISTINCT FROM v.old_pv` (the k56 heal precedent) with `RETURNING`; classify missing rows as `concurrently_changed` or `game_deleted` by a re-read; only an unexplained difference is the D-10 "row-count mismatch".

### Pitfall 4: Engine timeouts on a busy box
**What goes wrong:** `_NODES_TIMEOUT_S: float = 5.0` [VERIFIED: engine.py:105] trips when the box is loaded (engines run `SCHED_IDLE`), producing holes.
**How to avoid:** pass a generous `timeout_s` from the script (`evaluate_nodes_with_pv` already accepts it); retry a failed row once at the end of the batch; report failures; a failed **batch** (DB error) is the D-10 stop, a single timed-out row is not.

### Pitfall 5: Server-pool drain fully re-evaluates re-walk games
**What goes wrong:** `claim_eval_job` bundled path falls through to `_claim_tier4_blob` (eval_queue_service.py:1030-1085); `_full_drain_tick` special-cases only `TIER_BESTMOVE_BACKFILL` (eval_drain.py:1401-1402) and otherwise re-searches every ply and calls `apply_full_eval` with `preserve_existing_evals` False, i.e. rewrites evals, re-classifies flaws and rebuilds both blobs.
**Why it matters here:** violates D-03/D-05/D-06 and can reshuffle flaw sets (drill item orphans) for every repaired game the server pool happens to claim. Same on the benchmark `:8001` backend (drain enabled, pool 1).
**How to avoid:** route `TIER_BLOB_BACKFILL` to a blob-only tick: build the lease with `_build_flaw_blob_lease_positions`, evaluate the FENs in-process with `engine_service.evaluate_nodes_multipv2` (no session open), then call the same apply core as `/flaw-blob-submit` (extract it from `_apply_flaw_blob_submit` into `eval_apply.py`). Fallback if the planner wants a narrower change: skip tier 4 in the bundled path entirely. Either way, prove it with a test that a tier-4 drain tick leaves `eval_cp` untouched (mutation-check by reverting).

### Pitfall 6: JSONB `null` is not SQL NULL
**What goes wrong:** ORM `None` into a JSONB column writes `null::jsonb`; `IS NULL` predicates (and `answer_key_pending`) miss it, the line is never re-walked.
**How to avoid:** feeder uses raw SQL `SET col = NULL`; the fill-NULL-only writer never binds `None`. Test with `IS NULL` and `jsonb_typeof`.

### Pitfall 7: User-visible gap while a line is NULL
**What goes wrong:** a NULL `missed_pv_lines` removes the blunder from the Train pool (`answer_key_present`, train_pool.py:708-746) and counts toward `blob_pending_count` (`answer_key_pending`, train_pool.py:924-949); a NULL `blobs_completed_at` removes the game from Library tactic stats (library_repository.py:1796-1800, 2194-2198).
**How to avoid:** just-in-time windows (Pattern 4), small `FEED_LOW_WATER` / `FEED_BATCH_GAMES`.

### Pitfall 8: The re-walk gets no fleet time
**What goes wrong:** workers try rungs in order: explicit atomic, entry, **idle atomic (tier 3)**, flaw-blob, best-move (remote_eval_worker.py `_run_cycle` docstring ~984-1015). A non-empty tier-3 backlog starves rung 4; v2 workers get 204 on rung 4.
**How to avoid:** orchestrator reads tier-3 backlog and `worker_heartbeats` versions before the re-walk pilot; the feeder's measured drain rate is the honest projection for the 8-week gate.

### Pitfall 9: Prod connection budget and write pressure
**How to avoid:** `create_async_engine(url, pool_size=1, max_overflow=0, pool_pre_ping=True)` (backfill_maia_flaws.py:455-457 pattern); one connection for `repair`, one for `feed`; the pilot samples `SELECT count(*) FROM pg_stat_activity` and its own commit latency against a baseline (named thresholds); `--throttle-ms` like retag. Write volume is small (~8 rows/s over 5 days).

### Pitfall 10: §5 basis excludes blob-pending games
**What goes wrong:** the lane requires `g.blobs_completed_at IS NOT NULL` (chapter5.py `_base_games_cte`, SKILL §5 table); running §5 mid re-walk drops games.
**How to avoid:** run §5 only after the benchmark re-walk drains and the retag sweep finishes; regenerate the diff gate (`tests/scripts/benchmarks/test_chapter5_diff.py`, run by explicit path) from the same run; the `has_zone` set (9 of 38, owner-accepted) may change and needs an owner checkpoint.

### Pitfall 11: Tags lag the repaired pv on lines that are not re-walked
**What goes wrong:** tag detectors read the pv string at rows N/N+1 (`_detect_tactic_for_flaw`); a pv repaired 2 -> 3 plies keeps a 3-element blob (not re-walked) but its tag inputs changed.
**How to avoid:** final engine-free `retag_flaws.py --db benchmark` sweep (in scope); recommend the same on prod after the re-walk (~3.5h, reports/retag/retag-2026-09-13.md sizing). Run it after, never before, the re-walk.

## Code Examples

### Operator script skeleton (pattern sources: retag_flaws.py, backfill_maia_flaws.py)
```python
# scripts/repair_short_lines.py (shape only)
DbTarget = Literal["dev", "benchmark", "prod"]
Subcommand = Literal["repair", "feed", "measure-flips", "status"]

# D-10 gates (named constants, values from CONTEXT)
MAX_STILL_SHORT_SHARE: float = 0.03
MAX_LINE_REPAIR_DAYS: float = 10.0
MAX_REWALK_WEEKS: float = 8.0
MAX_CLASSIFICATION_FLIP_SHARE: float = 0.02
PILOT_FRACTION: float = 0.01
# Discretion (starting values, tune in the pilot) [ASSUMED]
GAMES_PER_BATCH: int = 200
SEARCH_TIMEOUT_S: float = 30.0
FEED_BATCH_GAMES: int = 2000
FEED_LOW_WATER: int = 500
FEED_POLL_S: float = 300.0

def _make_session_maker(db: DbTarget) -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(db_url_for_target(db), pool_size=1, max_overflow=0, pool_pre_ping=True)
    return async_sessionmaker(engine, expire_on_commit=False)
```
Per batch: short read session (games' PGN, flaws, rows k-1/k) -> close -> replay + classify rows -> `asyncio.gather(pool.<pinned search>(...))` with no session open -> short write session: guarded `UPDATE game_positions SET pv = v.pv, best_move = COALESCE(game_positions.best_move, v.best_move) FROM (VALUES ...) ... WHERE pv IS NOT DISTINCT FROM v.old_pv RETURNING game_id, ply` -> commit -> append to report counters and cursor. Note `best_move` is written only where it was NULL or illegal: for the illegal case use an explicit per-row flag in the VALUES list rather than COALESCE.

### Long-run launch (orchestrator, memory "Long operator runs")
```bash
cd /home/aimfeld/Projects/Games/flawchess-252 && setsid nohup bash -c \
  'PYTHONUNBUFFERED=1 uv run python scripts/repair_short_lines.py repair --db prod --engines 8; echo EXIT=$?' \
  >> temp/line-repair/repair-prod.log 2>&1 < /dev/null & disown
# Monitor: poll `kill -0 <python3 pid>` or the EXIT= marker, not `pgrep -f <pattern>`.
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|---|---|---|---|
| `protocol.analyse()` merged result | raw stream, last exact line per index (`_select_final_infos`) | 2026-11-12, quick 261112-j47, release #471 | new searches no longer truncated; this phase repairs old rows |
| short cached opening pv reused | 1-2 ply cached pv treated as missing, heals | 261112-k56, #472 | no separate cache repair needed |
| tier-4 blob = both lines NULL | per-line NULL (this phase) | Phase 252 | enables single-line re-walk |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|---|---|---|
| A1 | Fleet/box throughput (~1 search per engine-second; 3.5 weeks re-walk) from the seed, not a pilot | Summary, Pattern 4 | D-10 time gates trip; pilot measures it |
| A2 | Prod tier-3 backlog is empty most of the time, so rung 4 gets fleet time | Pitfall 8 | re-walk stalls; needs orchestrator SELECT |
| A3 | MultiPV-1 is the right mode for the D-05 re-search | Pattern 5 | flip rate slightly mis-measured; control arm bounds it |
| A4 | Guests excluded from the repair | Pattern 2 | wasted searches on lines never re-walked (or owner wants them) |
| A5 | Benchmark repair scope = classical + rapid lane games (`FULL_ANALYSIS_TRANCHES`), blitz not included | Benchmark section | blitz lane games stay damaged until a later §5 blitz refresh |
| A6 | Connection/latency thresholds and feeder window sizes (starting values) | Code Examples | gates too loose/tight; tune in pilot |
| A7 | Blob-only drain tick for `TIER_BLOB_BACKFILL` is acceptable for natural (non-repair) tier-4 games too (they then get `[]` for NULL-pv lines, like the remote lane) | Pitfall 5 | behaviour change for natural backlog; alternative: gate on `full_pv_completed_at IS NOT NULL` or skip tier 4 in bundled path |
| A8 | `pg_stat_activity` row count is readable by the prod app role | Pitfall 9 | gate must use the script's own latency only |
| A9 | S3 scope limited to ply <= `DEDUP_MAX_PLY` per seed | Pattern 2 | non-opening `[]` + NULL pv lines left as is; pilot counts them |
| A10 | An optional local undo log (old pv/best_move per row, JSONL under `temp/line-repair/`) is welcome despite CONTEXT calling the repair one-way | Security | none if declined; cheap safety if accepted |

## Open Questions (RESOLVED)

All eight items are resolved, either by the CONTEXT "Measured on prod at plan time" block (read-only, 2026-11-12), by a
plan-time decision, or by a measurement a plan performs before any write that depends on it.

1. **Prod sizes (read-only, run via `flawchess-prod-db` MCP):** Selector A count on prod (short non-mate node0 rows, distinct games, split guest/non-guest and lichess-eval/engine); Selector B count (`[]` lines at node0 ply <= 20 with NULL/short pv, and the same beyond ply 20); opening duplicate share by `(full_hash, best_move)`. The dev-validated SQL is in Pattern 2.
   **RESOLVED:** guests are excluded outright (D-13), so the guest split is moot. The Selector A and B counts, the beyond-ply-20 `[]` count (`sentinel_beyond_dedup_ply`), the still-short share and the projected days are measured by plan 06 Task 1's read-only dry-run preview on prod and shown at the one-way checkpoint (plan 06 Task 2) before any prod write. Opening dedupe: not done (dev showed a 5% duplicate share; the opening cache heals on its own since #472, CONTEXT scope).
2. **Single-NULL flaws today:** `count(*) WHERE (allowed_pv_lines IS NULL) <> (missed_pv_lines IS NULL)` on prod (0 on dev). Non-zero means the OR probe will re-open some games on deploy.
   **RESOLVED:** 0 on prod (CONTEXT measured block); re-checked after the deploy in plan 05 Task 3.
3. **Tier-3 backlog and natural tier-4 backlog on prod:** `count(*) FROM games WHERE full_evals_completed_at IS NULL AND lichess_evals_at IS NULL` (non-guest) and `... full_evals_completed_at IS NOT NULL AND blobs_completed_at IS NULL` (non-guest).
   **RESOLVED:** both 0 for non-guests (CONTEXT measured block); re-recorded as context in plan 05 Task 3 and plan 07 Task 1.
4. **Fleet versions:** `worker_heartbeats` (worker_schema_version, last seen) to confirm v3 before the re-walk.
   **RESOLVED:** 4 workers on version 2, 2 on version 3 (CONTEXT measured block). D-15: updating them is not a precondition; version-2 workers stay harmless (plan 03 Task 3) and the 8-week gate uses the measured drain rate.
5. **Ordering column:** `count(*) FILTER (WHERE played_at IS NULL)` on prod games (0 on dev); order `played_at DESC NULLS LAST, id DESC`.
   **RESOLVED:** 27 games (CONTEXT measured block); plan 01 orders `played_at DESC NULLS LAST, id DESC`.
6. **Connection baseline:** `SELECT count(*) FROM pg_stat_activity` at a quiet and a busy hour, to set the D-10 connection threshold.
   **RESOLVED:** 17 connections (CONTEXT measured block). Plan 01's gate measures its own baseline at run start and trips at baseline + MAX_CONNECTION_RISE (10); plan 05 Task 3 re-records the baseline after the deploy.
7. **Benchmark:** the same counts restricted to `benchmark_selection` armed classical + rapid, and whether blitz lane games should be included (A5).
   **RESOLVED:** scope is the classical and rapid lane tranches only (ROADMAP Phase 252 goal, seed Part B step 4), implemented as `--scope lane` over `FULL_ANALYSIS_TRANCHES` (plan 01 Task 3); blitz is not included. The counts are measured by the benchmark pilot run in plan 07 Task 2 before its full run starts.
8. **Prod retag after the re-walk:** in or out of this phase (recommend in, as the last step).
   **RESOLVED:** in, as the last prod step after the re-walk drains (D-14, plan 07 Task 3).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|---|---|---|---|---|
| Stockfish binary | repair, measure-flips, real-engine tests | yes | Stockfish 18 at `~/.local/stockfish/sf` | none needed |
| CPU cores (owner's box) | engine pool | yes | `nproc` = 16 | — |
| Dev Postgres | tests, dev dry runs | yes | container `flawchess-dev-db-1` up | — |
| Benchmark Postgres | benchmark repair, §5 | yes | container `flawchess-benchmark-db-1` up | `bin/benchmark_db.sh start` |
| Prod DB tunnel | prod runs | not checked (owner-run) | — | `bin/prod_db_tunnel.sh` (port 15432) |
| uv | everything | yes | 0.10.9 | — |
| Worktree `.venv` | tests/gate | **no** | — | `uv sync --group maia-inference` |
| `frontend/node_modules` in worktree | pre-merge gate | **no** | — | `cd frontend && npm ci` |

**Missing dependencies with no fallback:** none.
**Missing with fallback:** worktree venv and node_modules (one-time setup).

## Validation Architecture

### Test Framework
| Property | Value |
|---|---|
| Framework | pytest + pytest-asyncio (`asyncio_mode = "auto"`, pyproject.toml:84), xdist locally |
| Config file | `pyproject.toml` (`addopts = "--ignore=tests/scripts/benchmarks --ignore=tests/scripts/tagger"`, :93) |
| Quick run command | `uv run pytest tests/test_eval_worker_endpoints.py tests/services/test_eval_apply.py tests/scripts/test_repair_short_lines.py -n auto -q -k "flaw_blob or blob or repair"` |
| Full suite command | `uv run pytest -n auto -x` |

### Phase Requirements -> Test Map
| Scope | Behavior | Test Type | Automated Command | File Exists? |
|---|---|---|---|---|
| S1/D-01 | `root_moves` reaches `protocol.analysis` (fake records kwargs); default None unchanged | unit | `uv run pytest tests/services/test_engine_bound_lines.py -q` | extend; `ScriptedAnalysisProtocol.analysis` must record `root_moves` |
| S1/D-01 | real pinned search: `pv[0] == pin`, > 2 plies | integration (real SF, `skip_if_no_stockfish`, generous timeout constant, never patch prod constant) | `uv run pytest tests/services/test_engine_nodes.py -q -k pinned` | extend |
| S1/D-02 | NULL/illegal best_move -> free search, best_move written; legal -> unchanged | unit + DB | `uv run pytest tests/scripts/test_repair_short_lines.py -q` | Wave 0 |
| S1 | mate (row k-1) and game-over endings excluded; guard skip on concurrent change; dry-run writes nothing; report written to tmp dir | DB integration (fake evaluator injected) | same | Wave 0 |
| S2/D-03 | lease leases only the NULL line; submit writes only that line (other blob byte-identical); only that line's 4 tag columns change; all-sentinel and over-cap branches do not clobber the non-NULL line; `blobs_completed_at` stays NULL while a missed line is NULL | endpoint integration | `uv run pytest tests/test_eval_worker_endpoints.py -n auto -q -k flaw_blob` | extend |
| S2 | both-NULL flaw behaves exactly as before (existing tests stay green) | regression | same | exists |
| S2/Pitfall 5 | tier-4 drain tick leaves `eval_cp`/`eval_mate`/flaw set untouched | integration | `uv run pytest tests/services/test_full_eval_drain.py -n auto -q -k blob` | extend |
| S2/D-04 | feeder NULLs only predicate-matching lines with SQL NULL, respects low-water/window, idempotent re-run | DB integration | `uv run pytest tests/scripts/test_repair_short_lines.py -q -k feed` | Wave 0 |
| S5 | flip function: stored vs re-searched severity, mate ladder routed | unit | `uv run pytest tests/scripts/test_repair_short_lines.py -q -k flip` | Wave 0 |
| S4 | §5 numbers after refresh | gate (explicit path) | `uv run pytest tests/scripts/benchmarks/test_chapter5_diff.py -q` | regenerate |
| S4 | registry pins | unit | `uv run pytest tests/services/test_tactic_delta_zones.py -q` | update |

Test conventions: every test inserting a non-guest `Game` deletes it in `finally` (global lottery isolation); use the per-module user-id ranges, not 992xx; prove each gap closure by reverting the fix and watching the test fail (memory: mutation-test gap closures).

### Sampling Rate
- **Per task commit:** the quick command for the touched area.
- **Per wave merge:** `uv run pytest -n auto -x`.
- **Phase gate:** full pre-merge gate (CLAUDE.md) green before verify; plus a serial run of the eval-lane files (memory: serial CI hides isolation bugs).

### Wave 0 Gaps
- [ ] `tests/scripts/test_repair_short_lines.py` (selector, pin, guard, dry-run, feeder, flip function)
- [ ] `tests/services/engine_fakes.py`: record `root_moves` in `ScriptedAnalysisProtocol.analysis`
- [ ] Worktree setup: `uv sync --group maia-inference`, `cd frontend && npm ci`

## Security Domain

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---|---|---|
| V2 Authentication | no (no new endpoint) | operator token on `/eval/remote/*` unchanged |
| V3 Session Management | no | — |
| V4 Access Control | yes (existing) | `require_operator_token`; token-tamper guard in submit kept (tokens validated against the re-derived lease, now per line) |
| V5 Input Validation | yes | bound SQL params only; `--db` restricted to `Literal`; worker tokens parsed by `_parse_token` |
| V6 Cryptography | no | — |

### Known Threat Patterns
| Pattern | STRIDE | Mitigation |
|---|---|---|
| Script writes to the wrong DB | Tampering | `--db` required, logged target label, `--dry-run`, pilot first |
| Prod overload (connections, WAL) | Denial of service | pool_size=1, throttle, connection/latency gate (D-10) |
| Irreversible overwrite of pv/blobs | Tampering/Repudiation | guarded UPDATE, dry-run, pilot gates; optional local undo log (A10) |
| Submit of a token for a non-NULL line | Tampering | lease re-derivation leases only NULL lines, so such tokens are rejected (422) as today |

## Sources

### Primary (HIGH confidence)
- Code read this session: `app/services/engine.py`, `app/services/eval_apply.py`, `app/routers/eval_remote.py`, `app/services/eval_queue_service.py`, `app/services/eval_drain.py`, `app/services/flaws_service.py`, `app/services/train_pool.py`, `app/repositories/library_repository.py`, `app/models/game*.py`, `scripts/retag_flaws.py`, `scripts/backfill_maia_flaws.py`, `scripts/remote_eval_worker.py`, `scripts/benchmarks/chapter5.py`, `app/services/tactic_delta_zones.py`, `docker-compose.yml`, `docs/benchmark-lane-runbook.md`, `.claude/skills/benchmarks/SKILL.md`, tests fakes.
- Installed python-chess 1.11.2 source (`chess/engine.py` `analysis`, `_go`).
- Real Stockfish 18 probe (pinned / illegal `searchmoves`) and read-only dev-DB SQL validation, this session.
- Seed SEED-261112-s4v and quick-task SUMMARYs 261112-j47, 261112-k56.

### Secondary / Tertiary
- None (no web sources needed).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH (no new deps; API verified in installed source and by probe)
- Architecture: HIGH for the tier-4 and drain findings (code read); MEDIUM for the feeder choice (design judgement within the discretion area)
- Pitfalls: HIGH (each tied to a read code path or a probe)
- Sizing: MEDIUM/LOW (seed estimates; prod counts are open items)

**Research date:** 2026-11-12
**Valid until:** 2026-12-12 (stable code paths; re-check if Phase 250 or any eval-lane work lands first)
