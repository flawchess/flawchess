# Phase 248: Blunder-Check Refutation Stats and Calibration - Pattern Map

**Mapped:** 2026-11-09
**Files analyzed:** 14 (11 modified, 3 new + report outputs)
**Analogs found:** 14 / 14 (all tracked; Phase 247 code is the primary analog for everything except the calibration script)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `alembic/versions/2026111x_..._phase_248_maia_refutation.py` (new) | migration | schema | `alembic/versions/20261108_120000_a7d3f1c9e247_phase_247_maia_flaw_stats.py` | exact |
| `app/models/game_flaw.py` | model | CRUD | same file, lines 97-114 (247 Maia columns) | exact |
| `app/models/game.py` | model | CRUD | same file, lines 263-270 (`maia_flaws_completed_at`) | exact |
| `app/services/maia_flaw_stats.py` | utility (pure) | transform | same file, `compute_maia_flaw_stats` / `_rank` (lines 29-150) | exact |
| `app/services/maia_flaw_scoring.py` | service | batch / request-response (post-commit hook) | same file (`_flaw_fingerprint_select`, `_derive_flaw_stats`, `score_game`, `write_game_maia_scores`) | exact |
| `app/repositories/game_flaws_repository.py` | repository | CRUD (bulk update, stamp) | same file, `MAIA_FLAW_COLUMNS` (178), `bulk_update_flaw_maia_stats` (284), `mark_/clear_maia_flaws_completed` (299-335) | exact |
| `scripts/backfill_maia_flaws.py` | operator script | batch (sharded) | same file | exact |
| `scripts/blunder_check_calibration.py` (new) | operator script (read-only report) | batch read + transform -> file I/O | `scripts/backfill_maia_flaws.py` (engine/Maia lifecycle, `db_url_for_target`), `scripts/remote_eval_worker.py:67-71` (`_run_all_moves_pass` import) | role-match |
| `tests/services/test_maia_flaw_stats.py` | test | pure unit | same file | exact |
| `tests/services/test_maia_flaw_scoring.py` | test | DB integration | same file (fixtures 87-130, call-count test 657, reclassify 828) | exact |
| `tests/scripts/test_backfill_maia_flaws.py` | test | DB integration | same file (219 run_shard, 251 partition, 273 rerun, 444 status) | exact |
| `tests/scripts/test_blunder_check_calibration.py` (new) | test | pure unit | `tests/services/test_maia_flaw_stats.py` (pure-function style) | role-match |
| `tests/services/test_full_eval_drain.py`, `tests/test_eval_worker_endpoints.py` | test | integration | existing 247 assertions on `maia_flaws_completed_at` in those files | exact |
| `reports/blunder-check/*.md` (new outputs) | report | file output | `reports/maia-flaws-backfill/prod-coverage.md` | role-match |

No call-site edits needed in `eval_drain.py`, `eval_remote.py`, `eval_apply.py`, `backfill_flaws.py`, `opening_cache_repair.py` (RESEARCH Q8): they all reach `score_game_flaws_after_apply` or `clear_maia_flaws_completed`.

## Pattern Assignments

### `alembic/versions/..._phase_248_maia_refutation.py` (migration)

**Analog:** `alembic/versions/20261108_120000_a7d3f1c9e247_phase_247_maia_flaw_stats.py` (62 lines). Copy the docstring shape ("Deliberately metadata-only: no server_default, no CHECK constraint, no index and no data UPDATE ..."), set `down_revision = "a7d3f1c9e247"` (current head; verify with `uv run alembic heads`).

```python
def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("game_flaws", sa.Column("maia_played_prob", sa.REAL(), nullable=True))
    op.add_column("game_flaws", sa.Column("maia_played_rank", sa.SmallInteger(), nullable=True))
    ...
    op.add_column(
        "games",
        sa.Column("maia_flaws_completed_at", sa.DateTime(timezone=True), nullable=True),
    )

def downgrade() -> None:
    op.drop_column("games", "maia_flaws_completed_at")
    op.drop_column("game_flaws", "maia_effective_moves")  # reverse order
```
For 248: `maia_refutation_prob` REAL, `maia_refutation_rank` SmallInteger, `games.maia_refutation_completed_at` DateTime(tz). No index (D-22).

---

### `app/models/game_flaw.py` and `app/models/game.py` (model)

**Analog:** `app/models/game_flaw.py:97-114`
```python
    # Phase 247 Maia per-flaw stats (D-01). All nullable, NULL = not scored (or Maia could
    # not score this row). Written only by app/services/maia_flaw_scoring.py, never by
    # flaw_record_to_row, so a delete-free diff/upsert preserves them by omission (D-09).
    #   rank  = 1 + number of legal moves with STRICTLY higher Maia probability
    ...
    maia_played_prob: Mapped[Optional[float]] = mapped_column(REAL, nullable=True)
    maia_played_rank: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
```
Add a Phase 248 comment block stating: refutation = `COALESCE(game_positions.best_move, pv[0])` at `ply + 1`, Elo = blunderer's, only user-side blunders (severity 2), never in `flaw_record_to_row`.

**Analog:** `app/models/game.py:263-270`
```python
    # Phase 247: per-game marker for the Maia per-flaw stats pass
    # (game_flaws.maia_* columns). Stamped by app/services/maia_flaw_scoring.py only
    # when maia_engine.is_maia_available() and the scoring pass for the game completed
    # without an exception (D-05); stamped for zero-flaw games too. NULL = not scored,
    # or cleared by a Maia-absent reclassification (D-09). No index on purpose.
    maia_flaws_completed_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
```
Place `maia_refutation_completed_at` directly after it with the same comment shape (stamped also for games with zero user-side blunders; cleared together with the 247 stamp).

---

### `app/services/maia_flaw_stats.py` (pure utility, transform)

**Analog:** same file.
- Reason literal to extend (lines 37-50): `MaiaReason = Literal["played_not_legal", ..., "single_legal_move"]` -> add `"no_legal_reply"`, `"refutation_missing"`, `"refutation_not_legal"`.
- TypedDict + null factory pattern (lines 53-75): `class MaiaFlawStats(TypedDict)` / `def null_maia_stats() -> MaiaFlawStats`. Mirror as `MaiaRefutationStats` / `null_refutation_stats()`.
- Rank, reuse do not copy (lines 78-81):
```python
def _rank(probs: Mapping[str, float], uci: str) -> int:
    """RANK_BASE + number of legal moves strictly more probable than `uci`."""
    own = probs[uci]
    return RANK_BASE + sum(1 for p in probs.values() if p > own)
```
- Guard-then-compute shape (`_best_reason` lines 90-95, `compute_maia_flaw_stats` 112-150): return `(stats, reasons)`; cast with `float(...)` / `int(...)`. RESEARCH "Pure refutation stats" sketch gives the exact function body for `compute_refutation_stats`.

---

### `app/services/maia_flaw_scoring.py` (service, post-commit batch)

**Analog:** same file. Edits, with the code they extend:

1. Input dataclass + fingerprint (lines 85-94):
```python
@dataclass(frozen=True, slots=True)
class FlawMaiaInput:
    ply: int
    fen: str
    best_uci: str | None
    second_uci: str | None

def fingerprint_of(flaws: Sequence[FlawMaiaInput]) -> frozenset[FlawFingerprint]:
    return frozenset((f.ply, f.fen, f.best_uci, f.second_uci) for f in flaws)
```
Add `severity: int`, `refutation_uci: str | None`; widen the tuple (and the `FlawFingerprint` alias). `GameMaiaInputs` (97-110) gains `user_color: Literal["white", "black"]`, loaded from `Game.user_color` in `load_game_maia_inputs`.

2. Fingerprint select (lines 127-154): add `GameFlaw.severity` and a second outer join on `gp_next = aliased(GamePosition)` at `ply == GameFlaw.ply + 1` with `sa.func.coalesce(gp_next.best_move, sa.func.nullif(sa.func.split_part(gp_next.pv, " ", 1), ""))` (RESEARCH Pattern 2). Keep the single shared select for load and in-lock re-read.

3. Split `_derive_flaw_stats` (lines 264-299), do not grow it. The Elo block to extract as `_mover_elo(inputs, board)`:
```python
    # board.turn, not ply parity: a custom-FEN game may start with Black to move.
    raw_rating = inputs.white_rating if board.turn == chess.WHITE else inputs.black_rating
    if raw_rating is None:
        return None, ["no_rating"]
    elo = pinned_elo_for_mover(
        raw_rating=raw_rating,
        platform=inputs.platform,
        time_control_bucket=inputs.time_control_bucket,
        is_correspondence=inputs.is_correspondence,
    )
    probs = full_policy(board.fen(), elo)
    if probs is None:
        raise MaiaInferenceUnavailableError("full_policy returned None with Maia available")
```
New `_derive_refutation(pre_board, played_uci, elo, refutation_uci)` per RESEARCH Pattern 1: `post = pre_board.copy(stack=False)` (boards from `boards_from_targets` are the drain's live boards), legality check before inference, same `MaiaInferenceUnavailableError` raise. User-side test via `_SEVERITY_INT["blunder"]` (`app/repositories/game_flaws_repository.py:30`) and `mover_is_white_at_ply` (`app/repositories/query_utils.py:61`), never inline `% 2`.

4. Row builder (`_flaw_row`, ~301-323): every row carries PK + all keys; out-of-scope rows get `null_refutation_stats()` in full mode:
```python
    row: dict[str, Any] = {"user_id": inputs.user_id, "game_id": inputs.game_id, "ply": flaw.ply}
    row.update(stats if stats is not None else null_maia_stats())
```
5. `score_game(inputs, boards)` (325-343): add `mode: ScoringMode = "full"`; in refutation mode replay only blunder plies and emit uniform-key rows (PK + `MAIA_REFUTATION_COLUMNS`) for in-scope flaws only.

6. Write (`_outcome_for` 375-388, `write_game_maia_scores` 391-428): the stamp read is
```python
sa.select(Game.id, Game.maia_flaws_completed_at).where(Game.id.in_(game_ids))
```
make the stamp column mode-dependent for `require_unstamped`; finish with `bulk_update_flaw_maia_stats` + stamp call(s) (full: both stamps; refutation: new stamp only). Keep `_lock_games_ascending` and `MAX_GAMES_PER_WRITE_TXN` untouched.

7. Entry hook `score_game_flaws_after_apply` (436-475): no structural change; keep `is_maia_available()` guard, session-free `asyncio.to_thread(score_game, ...)`, `StaleDataError` info-log, and the Sentry block:
```python
    except Exception:
        sentry_sdk.set_context("maia_flaws", {"game_id": game_id, "lane": source})
        sentry_sdk.set_tag("source", "maia_flaws")
        sentry_sdk.capture_exception()
        return False
```

---

### `app/repositories/game_flaws_repository.py` (repository, CRUD)

**Analog:** same file.
- Column tuple (178-187): `MAIA_FLAW_COLUMNS: tuple[str, ...] = (...)` -> add separate `MAIA_REFUTATION_COLUMNS = ("maia_refutation_prob", "maia_refutation_rank")`. Never add to `flaw_record_to_row` or `FLAW_BLOB_AND_TACTIC_COLUMNS` (preserve-by-omission, D-08).
- Bulk update (284-296): `await session.execute(update(GameFlaw), rows)`; update docstring to "uniform keys per call" (full mode: 10 keys; refutation mode: 2 keys).
- Stamp (299-314): copy `mark_maia_flaws_completed` as `mark_maia_refutation_completed` (same `update(games_table)  # ty: ignore[invalid-argument-type]` idiom, `.values(...=datetime.now(timezone.utc))`).
- Clear (317-335): extend `clear_maia_flaws_completed` to set both columns NULL with `WHERE id = :id AND (a IS NOT NULL OR b IS NOT NULL)`; keep the `-> bool` return contract (five callers rely on it).

---

### `scripts/backfill_maia_flaws.py` (operator script, sharded batch)

**Analog:** same file.
- Constants/Literals block (74-96): add `BackfillMode = Literal["full", "refutation"]`, `BACKFILL_MODE_CHOICES`, keep `SHARD_RESIDUE_SQL` as is.
- Selector (99-109) to make mode-dependent:
```python
WHERE g.maia_flaws_completed_at IS NULL
  AND EXISTS (SELECT 1 FROM game_flaws f WHERE f.game_id = g.id)
  AND {SHARD_RESIDUE_SQL} % CAST(:num_shards AS bigint) = CAST(:shard AS bigint)
  {{user_clause}}
```
Refutation: `g.maia_refutation_completed_at IS NULL AND g.maia_flaws_completed_at IS NOT NULL AND EXISTS(...)`. Keep the `.format(user_clause=..., limit_clause=...)` + bound-params approach (`select_shard_game_ids`, 126-149).
- Thread `mode` through `_shard_kwargs` (591), `_shard_process_entry` (445-475), `run_shard` (379), `_score_batch` (219), `_write_scores` (257); report file name carries the mode (`_write_report`, 184).
- Status (`_STATUS_QUERIES` 555-566, `fetch_status` 568): add refutation-mode queries; the user-blunder total should be a Core query using `is_opponent_expr` (no inline parity in code).
- Maia lifecycle to keep (434-442):
```python
async def _start_maia_and_run(**shard_kwargs: Any) -> int:
    await maia_engine.start_maia(intra_op_num_threads=MAIA_THREADS_PER_PROCESS)
    if not maia_engine.is_maia_available():
        _log("Maia is unavailable in this process (onnxruntime or model missing); nothing done")
        return EXIT_MAIA_UNAVAILABLE
```
- `ShardReport` (158): add `refutations_scored`, `refutations_null`, `refutations_from_pv`; `_combined_total_line` (606) sums them.

---

### `scripts/blunder_check_calibration.py` (new, read-only report)

**Analogs:** `scripts/backfill_maia_flaws.py` (header, sys.path/import block lines ~55-72, `_log` 115, `--db` `Literal` choices, `_start_maia_and_run`), `scripts/remote_eval_worker.py:67-71` for importing the private flaw pass:
```python
# _walk_pv_boards / _run_all_moves_pass are leading-underscore "module-private" by
...
from app.services.flaws_service import _run_all_moves_pass  # noqa: E402
```
Engine pattern from `backfill_maia_flaws.py:542` plus the read-only GUC (RESEARCH, verify on dev that an INSERT fails):
```python
engine = create_async_engine(
    db_url_for_target(db), pool_size=1, max_overflow=0,
    connect_args={"server_settings": {"default_transaction_read_only": "on"}},
)
```
Reuse, do not re-implement: `_run_all_moves_pass` (flaws_service.py:373), `_ply_to_es` (196), `INACCURACY_DROP` (47), `pinned_elo_for_mover`, `maia_engine.full_policy`, `replay_flaw_boards` (maia_flaw_scoring.py:225), md5 residue sampling (`SHARD_RESIDUE_SQL`). Keep functions small: pipeline stages `_sample` / `_classify` / `_grid` / `_window_fit` / `_render`. Output `reports/blunder-check/blunder-check-calibration-YYYY-MM-DD.md` + `spot-check-YYYY-MM-DD.md`. Named constants for Elo bucket edges, grid values, `HAZARD`, `LEAD_IN_PLIES`, `MAX_MISS_SHARE`, sample permille. `MissCase = Literal[...]` per RESEARCH "Miss case" sketch.

---

### Tests

- `tests/services/test_maia_flaw_scoring.py`: reuse fixtures `session_factory` (87), autouse `_maia_present` (92-96, monkeypatches `maia_engine._session` and `maia_flaw_scoring.full_policy`), `make_game` factory (99+; extend with `user_color`, per-ply `best_move`/`pv` at ply+1, severity). Copy the call-spy shape from `test_one_full_policy_call_per_flaw` (657-680) for (a) one extra call per user-side blunder only, (b) Elo argument = blunderer's for both colors (Pitfall 2), (c) zero calls for missing/illegal refutation. Copy `test_fingerprint_changed_skips_write` (418) for a mid-flight ply+1 `best_move` change; `test_reclassify_without_maia_keeps_survivors_nulls_new_unstamps` (828) for both stamps cleared and refutation preserved by omission; `test_stamp_zero_flaw_game` (560) for zero-user-blunder stamping; `test_schema_maia_columns_typed_nullable` (261) for the new columns.
- `tests/scripts/test_backfill_maia_flaws.py`: mirror `test_run_shard_scores_and_stamps_user_games` (219), `test_shard_partition_disjoint_exhaustive` (251), `test_rerun_selects_nothing_and_changes_nothing` (273), `test_status_counts` (444) in `--mode refutation`; add a selector test that base-unstamped games are excluded.
- `tests/services/test_maia_flaw_stats.py`: pure tests for `compute_refutation_stats` (ties share rank, empty policy, missing, illegal).
- `tests/scripts/test_blunder_check_calibration.py`: pure-function tests only (miss case, Good judgement, hazard weights, supply cap); no prod DB.

## Shared Patterns

### Maia guardrail and session-free inference
**Source:** `app/services/maia_flaw_scoring.py:436-475`. Apply to scorer and both scripts: never stamp unless `is_maia_available()`; no DB session open during `full_policy`.

### Sentry
**Source:** `maia_flaw_scoring.py` except block (above). Context/tag only, no variables in messages. Scripts call `sentry_sdk.init` per process (`backfill_maia_flaws.py:461-462`).

### Ply parity single source
**Source:** `app/repositories/query_utils.py:61` `mover_is_white_at_ply` (Python), `:71` `is_opponent_expr` (SQL). Apply to scorer, backfill status, calibration queries. Ad-hoc MCP coverage SQL may inline it (247 precedent).

### Preserve-by-omission
**Source:** `app/models/game_flaw.py:97-101` comment + `MAIA_FLAW_COLUMNS` separation. New columns live only in `MAIA_REFUTATION_COLUMNS`.

### DB targeting
**Source:** `app.core.config.db_url_for_target`, `--db` Literal with no silent prod default, `pool_size=1, max_overflow=0` per process; `_print_banner` (backfill 540-552) never prints the URL.

### Reports
**Source:** `reports/maia-flaws-backfill/` (dated markdown + JSON shard reports). New dir `reports/blunder-check/`.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| (calibration statistics: hazard window fit, AUC, threshold grid inside `scripts/blunder_check_calibration.py`) | analysis logic | transform | No existing script computes these; use RESEARCH Q6/Q7 formulas. The script shell itself has analogs (above). |

## Metadata

**Analog search scope:** `app/services/`, `app/repositories/`, `app/models/`, `alembic/versions/`, `scripts/`, `tests/services/`, `tests/scripts/`, `reports/`
**Files scanned:** ~15
**Pattern extraction date:** 2026-11-09
