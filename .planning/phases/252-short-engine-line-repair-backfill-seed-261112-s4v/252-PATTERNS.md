# Phase 252: Short Engine Line Repair Backfill - Pattern Map

**Mapped:** 2026-11-12
**Files analyzed:** 14 (new + modified)
**Analogs found:** 13 / 14

All analog paths verified git-tracked (`git ls-files`) in the `flawchess-252` worktree.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `scripts/repair_short_lines.py` (NEW; `repair`/`feed`/`measure-flips`/`status`) | operator script | batch (engine + DB guarded UPDATE) | `scripts/opening_cache_repair.py` (engine pool + guarded `IS NOT DISTINCT FROM` UPDATE + `--db`) and `scripts/retag_flaws.py` (CLI, report, dry-run, throttle) | exact |
| `app/services/engine.py` (MOD: `root_moves` kwarg) | service | request-response (UCI) | itself: `multipv` kwarg threading `_collect_analysis_infos` (l.459-477) -> `_acquire_and_analyse` (l.601) -> `evaluate_nodes_with_pv` (l.713) | exact |
| `app/services/eval_apply.py` (MOD: OR probe, per-line lease, fill-NULL-only writer, extracted blob-apply core) | service | CRUD/batch | itself: `_batch_update_flaw_pv_lines` (l.1817-1848), `_refresh_blobs_completed` (l.1851-1880), `_build_flaw_blob_lease_positions` (l.1883-1989) | exact |
| `app/routers/eval_remote.py` (MOD: `/flaw-blob-lease` sentinel + over-cap branches, `_apply_flaw_blob_submit`) | router | request-response | itself l.906-942, l.954-1123 | exact |
| `app/services/eval_drain.py` (MOD: `TIER_BLOB_BACKFILL` -> blob-only tick) | service | event-driven (drain tick) | `_tier4b_minimal_drain_tick` (l.1156+) and its dispatch at l.1398-1402 | exact |
| `tests/scripts/test_repair_short_lines.py` (NEW) | test | DB integration | `tests/scripts/test_opening_cache_repair.py`, `tests/scripts/test_retag_flaws.py` | exact |
| `tests/services/engine_fakes.py` (MOD: record `root_moves`) | test fake | — | itself `ScriptedAnalysisProtocol.analysis` (l.83-100) | exact |
| `tests/services/test_engine_bound_lines.py` (MOD) | test | unit | itself | exact |
| `tests/services/test_engine_nodes.py` (MOD, real SF pinned case) | test | integration | itself (`skip_if_no_stockfish`) | exact |
| `tests/test_eval_worker_endpoints.py` (MOD, single-NULL-line cases) | test | endpoint integration | itself (existing `flaw_blob` tests) | exact |
| `tests/services/test_eval_apply.py` (MOD) | test | DB | itself | exact |
| `tests/services/test_full_eval_drain.py` (MOD, blob tick keeps evals) | test | integration | itself (tier-4b minimal-tick tests) | exact |
| `app/services/tactic_delta_zones.py` + `tests/services/test_tactic_delta_zones.py` (MOD after §5 refresh) | config/registry | transform | itself; generated via `python -m scripts.benchmarks.chapter5` | exact |
| `reports/line-repair/*.md` (NEW reports) | report artifact | file-I/O | `reports/retag/retag-2026-09-13.md` (written by `_write_retag_report`, retag_flaws.py l.649) | role-match |

## Pattern Assignments

### `scripts/repair_short_lines.py` (operator script, batch)

**Primary analog:** `scripts/opening_cache_repair.py` (3568 lines; read targeted ranges only). It already does exactly this phase's shape: local `EnginePool` re-search + guarded rewrite of `game_positions.best_move`/`pv` over `--db`.

**Engine pool sizing** (opening_cache_repair.py l.242-257) — copy verbatim, add `--engines`/`--pool-size`:
```python
def _pool_from_env(pool_size: int | None = None) -> EnginePool:
    if pool_size is not None:
        size = max(1, pool_size)
        print(f"engine pool: {size} worker(s) (--pool-size)", flush=True)
    else:
        size = read_pool_size()
        print(f"engine pool: {size} worker(s) (STOCKFISH_POOL_SIZE)", flush=True)
    return EnginePool(size)
```
Import line (l.80): `from app.services.engine import EnginePool, get_stockfish_version, read_pool_size  # noqa: E402`.

**Session maker with injection + target banner** (opening_cache_repair.py l.291-307) — copy, but use the single-connection pool from `scripts/backfill_maia_flaws.py` l.455-457 (`pool_size=1, max_overflow=0, pool_pre_ping=True`) for the prod connection budget:
```python
def _resolve_session_maker(db, session_maker):
    if session_maker is not None:
        return session_maker, None, False
    engine = create_async_engine(db_url_for_target(db), pool_pre_ping=True)
    print(f"Target: {engine.url.host}:{engine.url.port}/{engine.url.database} ({db})")
    return async_sessionmaker(engine, expire_on_commit=False), engine, True
```

**Guarded UPDATE** (opening_cache_repair.py l.1355-1389) — the concurrency guard + CAST convention to copy for the pv rewrite:
```python
# Every bind uses CAST(x AS t), never `x::t` -- asyncpg cannot infer the parameter
# type of a NULL bind on an `IS NOT DISTINCT FROM` comparison otherwise.
_PROPAGATE_PV_SQL = text(
    "UPDATE game_positions n"
    " SET pv = CAST(:new_pv AS text)"
    " WHERE ...  AND n.pv IS NOT DISTINCT FROM CAST(:old_pv AS text)"
    " RETURNING n.game_id, n.user_id, n.ply"
)
```
New script keys on `(user_id, game_id, ply)` from a VALUES list (batched, see `_batch_update_flaw_pv_lines` VALUES construction below) and writes `best_move` only for D-02 rows (explicit per-row flag, not blanket COALESCE).

**Signal handling / resumability:** `_install_signal_handlers` (opening_cache_repair.py l.186-199) for graceful stop; cursor file under `temp/line-repair/` (no progress table: CONTEXT says no migration, unlike `OpeningCacheRepairProgress`).

**Terminal-position handling precedent:** `_carrier_targets` (l.260-288) uses `_collect_full_ply_targets(..., include_terminal=True)` and documents a dev-smoke bug fix in the docstring; follow the same "comment the fix site" style.

**CLI + report + dry-run** (analog `scripts/retag_flaws.py`):
- `_parse_args` l.187-265: `--db` with `choices=["dev", "benchmark", "prod"], required=True`; `--dry-run`, `--limit`, `--throttle-ms` (`dest="throttle_ms"`, "Sleep this many milliseconds after each page commit"). Use argparse subparsers for the four subcommands; type `DbTarget = Literal["dev","benchmark","prod"]`.
- `run_backfill` signature l.868-880: keyword-only args with injectable `session_maker: async_sessionmaker[AsyncSession] | None = None` and `report_dir: Path | None = None` (tests pass tmp dir). Copy this injection contract for every subcommand entrypoint, plus an injectable `pool` like `run_screen(..., pool: EnginePool | None = None)` (opening_cache_repair.py l.860-866).
- Sentry init l.900-901: `if settings.SENTRY_DSN: sentry_sdk.init(dsn=settings.SENTRY_DSN, environment=settings.ENVIRONMENT)`.
- Startup `_log(...)` banner of mode/target/batch size (l.910-920).
- Report writer: `_write_retag_report` (l.649) -> `reports/line-repair/`.

**Constants block:** module-level typed constants as in opening_cache_repair.py l.105-125 (`REPAIR_BATCH_ROWS: int = 500`, `SCREEN_GAMES_PER_BATCH: int = 200`); put the D-10 gates here (`MAX_STILL_SHORT_SHARE`, `MAX_LINE_REPAIR_DAYS`, `MAX_REWALK_WEEKS`, `MAX_CLASSIFICATION_FLIP_SHARE`, `PILOT_FRACTION`) and reuse `CACHED_PV_MIN_PLIES` / `pv_ply_count` from `app/services/eval_apply.py` l.113-122 instead of a literal 2/3.

**Feeder lock:** reuse `_game_write_lock_key` (eval_apply.py l.146) exactly like the submit path (eval_remote.py l.1080-1083):
```python
await write_session.execute(
    sa.text("SELECT pg_advisory_xact_lock(:lock_key)"),
    {"lock_key": _game_write_lock_key(game_id)},
)
```
Feeder NULLs with raw SQL `SET <col> = NULL` (never ORM `None`, JSONB null pitfall).

---

### `app/services/engine.py` (service, UCI request-response)

**Analog:** the existing `multipv` threading. Current code (l.459-477):
```python
async def _collect_analysis_infos(
    protocol: chess.engine.UciProtocol,
    board: chess.Board,
    limit: chess.engine.Limit,
    multipv: int | None,
) -> list[chess.engine.InfoDict]:
    analysis = await protocol.analysis(board, limit, multipv=multipv)
```
`_acquire_and_analyse(self, board, limit, timeout, *, multipv: int | None = None)` at l.601-607; its docstring (l.609-615) says "Only genuine difference across callers is whether `multipv` is passed" — update that sentence when adding `root_moves`. Add `root_moves: Sequence[chess.Move] | None = None` keyword-only with None default on both, and either a kwarg on `evaluate_nodes_with_pv(self, board, *, timeout_s: float | None = None)` (l.713-740) or a sibling public method. Return contract `(eval_cp, eval_mate, best_move_uci, pv_uci_string)` stays.

---

### `app/services/eval_apply.py` (service, CRUD)

**Fill-NULL-only writer — analog `_batch_update_flaw_pv_lines` (l.1817-1848):**
```python
params: dict[str, Any] = {"game_id": game_id}
values_parts: list[str] = []
for i, (ply, (allowed_blobs, missed_blobs)) in enumerate(blob_map.items()):
    params[f"ply_{i}"] = ply
    params[f"allowed_{i}"] = json.dumps(allowed_blobs)
    params[f"missed_{i}"] = json.dumps(missed_blobs)
    values_parts.append(
        f"(CAST(:ply_{i} AS smallint), CAST(:allowed_{i} AS jsonb), CAST(:missed_{i} AS jsonb))"
    )
values_sql = ", ".join(values_parts)
sql = sa.text(
    f"UPDATE game_flaws"  # noqa: S608 — no user input; params are bound
    f" SET allowed_pv_lines = v.allowed_pv_lines,"
    f"     missed_pv_lines = v.missed_pv_lines"
    f" FROM (VALUES {values_sql}) AS v(ply, allowed_pv_lines, missed_pv_lines)"
    f" WHERE game_flaws.game_id = :game_id"
    f" AND game_flaws.ply = v.ply"
)
```
New sibling: identical body, SET becomes `COALESCE(game_flaws.allowed_pv_lines, v.allowed_pv_lines)` / same for missed. Leave the original untouched (used by `_diff_upsert_flaw_rows`, l.1348, which must overwrite). Docstring style: "Does NOT catch exceptions — caller decides fault tolerance. Guard: empty blob_map is a no-op."

**OR probe — `_refresh_blobs_completed` (l.1851-1880):** change only the probe SQL
```python
"SELECT 1 FROM game_flaws WHERE game_id = :game_id AND allowed_pv_lines IS NULL LIMIT 1"
```
to `(allowed_pv_lines IS NULL OR missed_pv_lines IS NULL)`; keep the bidirectional stamp and "Does NOT commit" contract. Note docstring mentions `ix_game_flaws_blob_backfill` index-only probe; the OR form loses that, update the comment (per-game `game_id` index is fine).

**Lease builder:** `_build_flaw_blob_lease_positions` (l.1883-1989) — keep token format `"{flaw_ply}:{line}:{node_k}"`; select which columns are NULL and lease only those lines. Use `Literal["allowed", "missed"]` for the line type.

**Extracted blob-apply core:** move the read/lock/assemble/tag/write body out of `_apply_flaw_blob_submit` (eval_remote.py l.954-1123) into eval_apply.py so the router and the new drain tick share it (same as tier-4b shares `_build_bestmove_lease_positions` with `/bestmove-lease`).

---

### `app/routers/eval_remote.py` (router, request-response)

**Analog:** itself. Keep the in-lock re-read pattern (l.1075-1095): advisory lock, then re-select surviving plies before writing (comment explains StaleDataError fix — keep). Replace both-column writes in the all-sentinel branch (l.906-916) and over-cap branch (l.928-942) with the fill-NULL-only writer; over-cap selector uses the OR predicate. Tags: write only the re-walked orientation's 4 columns via `bulk_update_tactic_tags` (repositories/game_flaws_repository.py l.198-217, ORM bulk by PK, so a dict of PK + 4 keys touches only those). Keep Sentry `capture_exception` + `set_context` in excepts, no variables in messages. Router stays thin: logic goes to eval_apply.

---

### `app/services/eval_drain.py` (service, drain tick)

**Analog:** tier-4b dispatch and minimal tick. Dispatch (l.1398-1402):
```python
# A TIER_BESTMOVE_BACKFILL claim takes the minimal
# candidate-only path — never the full every-ply gather + apply_full_eval
# reclassify below.
if tier == TIER_BESTMOVE_BACKFILL:
    return await _tier4b_minimal_drain_tick(game_id, user_id)
```
Add `if tier == TIER_BLOB_BACKFILL: return await _tier4_blob_drain_tick(game_id, user_id)` (import from `app.models.eval_jobs` alongside l.41). Model `_tier4_blob_drain_tick` on `_tier4b_minimal_drain_tick` (l.1156+) whose docstring flow is: build lease positions (no engine) -> zero/over-cap -> stamp directly and return True -> otherwise ONE `asyncio.gather` of engine calls with NO session open (use `engine_service.evaluate_nodes_multipv2`) -> short write session calling the shared apply core. Comment the Pitfall-5 reason at the dispatch site.

---

### `tests/services/engine_fakes.py` (test fake)

`ScriptedAnalysisProtocol.analysis` (l.83-100) currently takes `**kwargs: object` and records `self.calls.append((limit, multipv))`. Add `self.root_moves_calls: list[...]` and record `kwargs.get("root_moves")` (do not change the `calls` tuple shape; existing tests assert it).

---

### `tests/scripts/test_repair_short_lines.py` (test, DB integration)

**Analog:** `tests/scripts/test_retag_flaws.py` (header l.1-60) + `tests/scripts/test_opening_cache_repair.py`.
- Module docstring listing cases (a)/(b)/... style.
- Session-maker injection against the per-run test DB; committed data (not rollback-scoped) because the script opens its own sessions.
- Unique module user id constant (retag uses `_TEST_USER_ID = 143_030`; pick a fresh 252_xxx range, not 992xx).
- `finally` cleanup deleting User/Game/GamePosition/GameFlaw (eval lottery isolation).
- Inject a fake `EnginePool`/evaluator (opening_cache_repair tests pass `pool=`), `report_dir=tmp_path`.
- Named test constants, no magic numbers (`_PGN = "1. e4 e5 2. Nf3 *"`, `_EVAL_PLY_*`).

## Shared Patterns

### DB target resolution
**Source:** `app.core.config.db_url_for_target` (used in retag_flaws.py l.905, opening_cache_repair.py l.305). Apply to every subcommand; never use the app's global session maker.

### Short-line definition
**Source:** `app/services/eval_apply.py` l.113-122 (`CACHED_PV_MIN_PLIES = 3`, `pv_ply_count`, `cached_pv_usable`). Apply to selector SQL bind (`:min_plies`), D-10 still-short gate, tests.

### Per-game write serialization
**Source:** `_game_write_lock_key` (eval_apply.py l.146) + `pg_advisory_xact_lock` (eval_remote.py l.1080-1083). Apply to the feeder, the repair writes, the blob-apply core.

### No session across engine gather
**Source:** `_tier4b_minimal_drain_tick` docstring (eval_drain.py l.1176-1181) and research "short read session -> close -> gather -> short write session". Apply to repair batches, measure-flips, the new drain tick.

### Sentry in scripts/services
**Source:** retag_flaws.py l.900-901 init; CLAUDE.md `set_context` rule. Apply to script entrypoints and modified eval_apply/eval_remote/eval_drain excepts.

### Reuse, do not re-implement
`_select_final_infos`/`_pv_to_uci_string`/`PV_CAP_PLIES` (engine.py), `_recompute_fen_map`, `_classify_tactic_gated`, `_ply_to_es`, `_classify_mate_ladder`, `classify_severity` (flaws_service.py), `scripts/retag_flaws.py` for the final retag sweep, `python -m scripts.benchmarks.chapter5` for §5.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `feed` subcommand of `scripts/repair_short_lines.py` | operator feeder | event-driven polling | No existing script tops up a pending window by polling; build from Pattern 4 in RESEARCH.md, reusing the lock + raw-SQL NULL conventions above |

## Metadata

**Analog search scope:** `scripts/`, `app/services/`, `app/routers/`, `tests/scripts/`, `tests/services/`
**Files scanned:** ~12
**Pattern extraction date:** 2026-11-12
