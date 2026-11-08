# Phase 247: Maia Stats on game_flaws - Pattern Map

**Mapped:** 2026-11-08
**Files analyzed:** 16 (5 new source/script, 8 modified, 3+ test files)
**Analogs found:** 15 / 16

**Path correction vs RESEARCH.md:** `_apply_atomic_submit` and `/flaw-blob-submit` live in
`app/routers/eval_remote.py` (lines 1176 and 1093), not `app/services/eval_remote.py` (that file does not exist).
The research line numbers `eval_remote.py:1044-1070, 1455-1467` refer to the router.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `alembic/versions/2026MMDD_..._phase_247_maia_flaw_stats.py` (NEW) | migration | schema | `alembic/versions/20260717_035706_939c3d99868d_phase_176_best_moves_completed_at.py` | exact (minus data stamp + index) |
| `app/models/game_flaw.py` (MOD, +8 cols) | model | — | same file, tactic columns lines 88-96; `app/models/game_best_move.py:19,40` for REAL | exact |
| `app/models/game.py` (MOD, +`maia_flaws_completed_at`) | model | — | same file, `best_moves_completed_at` lines 255-262 | exact |
| `app/services/maia_engine.py` (MOD: `full_policy`, `score_move` delegates, `start_maia(intra_op_num_threads=None)`) | service | transform (CPU) | same file, `score_move` lines 151-175, `start_maia` lines ~100-128 | exact |
| `app/services/maia_flaw_stats.py` (NEW, pure) | utility | transform | RESEARCH Code Examples "Pure stats"; no pure-stats analog needed | research-pattern |
| `app/services/maia_flaw_scoring.py` (NEW: read, to_thread infer, guarded write+stamp) | service | request-response / batch | `eval_apply._build_best_move_candidates` (2152-2235) + in-lock re-read in `app/routers/eval_remote.py:1043-1087` | role-match (composite) |
| `app/repositories/game_flaws_repository.py` (MOD: `MAIA_FLAW_COLUMNS`, `bulk_update_flaw_maia_stats`, stamp set/clear helpers) | repository | CRUD | same file, `bulk_update_game_flaw_rows` (~246-264), `FLAW_BLOB_AND_TACTIC_COLUMNS` (~155-170); `eval_apply._mark_best_moves_completed` (827-841) for stamp | exact |
| `app/services/eval_apply.py` (MOD: `_classify_and_fill_oracle` clears stamp, returns result) | service | CRUD | same function lines 995-1135 | exact |
| `app/services/eval_drain.py` (MOD: post-commit scorer call in `_full_drain_tick`) | service | event-driven | same file 1565-1582 | exact |
| `app/routers/eval_remote.py` (MOD: post-commit scorer in `_apply_atomic_submit` ~1461 and after `/flaw-blob-submit` commit ~1087, D-14) | router hook | request-response | same file | exact |
| `scripts/backfill_maia_flaws.py` (NEW) | script | batch, multi-process | `scripts/backfill_flaws.py` (args, session maker, Sentry, advisory lock) + `scripts/engine_disagreement_study/seed153_scan_sample.py:125-136` (md5 shard) + `scripts/retag_flaws.py:943-945` (spawn context) | role-match (composite) |
| `scripts/backfill_flaws.py` (MOD: clear stamp in default delete+insert branch ~391-402, reminder line) | script | batch | same file | exact |
| `scripts/opening_cache_repair.py` (MOD: count unstamps from `_classify_and_fill_oracle` ~2040, clear in `_rederive_reclassify_game` None branch ~2034, reminder) | script | batch | same file | exact |
| `tests/services/test_maia_flaw_stats.py` (NEW) | test | unit | `tests/services/test_maia_engine.py` | role-match |
| `tests/services/test_maia_flaw_scoring.py` (NEW) + extend `tests/services/test_full_eval_drain.py`, `tests/test_eval_worker_endpoints.py` | test | integration | `tests/services/test_full_eval_drain.py:2682-2948` (`_session = object()` sentinel) | exact |
| `tests/scripts/test_backfill_maia_flaws.py` (NEW) | test | integration | `tests/test_backfill_flaws.py` (injected session_maker) | role-match |

All analog paths verified git-tracked.

## Pattern Assignments

### Migration (NEW)

**Analog:** `alembic/versions/20260717_035706_939c3d99868d_phase_176_best_moves_completed_at.py`

Header/revision shape (copy verbatim, set `down_revision = "e2a7c4f9b244"`):
```python
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "939c3d99868d"
down_revision: Union[str, Sequence[str], None] = "1eda5daba951"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "games",
        sa.Column("best_moves_completed_at", sa.DateTime(timezone=True), nullable=True),
    )
```
Do NOT copy the analog's one-time `UPDATE` stamp or its `create_index` (RESEARCH Q7: no index, no CHECK, no default).
Downgrade: `op.drop_column` in reverse order. Body per RESEARCH Pattern 1 (8 `game_flaws` cols: `sa.REAL()` / `sa.SmallInteger()`).

### `app/models/game_flaw.py` (MOD)

Copy style of lines 92-96:
```python
allowed_tactic_depth: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
```
REAL import precedent: `from sqlalchemy.dialects.postgresql import REAL` (`app/models/game_best_move.py:19`). So
`maia_played_prob: Mapped[Optional[float]] = mapped_column(REAL, nullable=True)`. Add a comment block above (style of 85-88) documenting rank = 1 + #strictly-higher and effective = 2^H. Do NOT mark `deferred=True` (that is the JSONB blob family's leak guard).

### `app/models/game.py` (MOD)

Copy lines 255-262 exactly, renaming:
```python
    # NULL = best-move pass not yet attempted (or attempted with Maia absent).
    # Self-termination predicate: ...
    best_moves_completed_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
```
Comment must state: NULL = not scored, or cleared by a Maia-absent reclassify (D-09); stamped also for zero-flaw games (D-05). No `Index(...)` in `__table_args__`.

### `app/services/maia_engine.py` (MOD)

**Analog:** same file. Current `score_move` (lines 151-175) is the body to lift into `full_policy`:
```python
    if _session is None:
        return None
    try:
        import numpy as np  # deferred — isolated maia-inference group alongside onnxruntime
    except ImportError:
        return None
    tokens = np.array(encode_board(fen), dtype=np.float32).reshape(1, NUM_SQUARES, PLANES_PER_SQUARE)
    elo_in = np.array([elo_to_input(elo)], dtype=np.float32)
    feeds = {_TOKENS_INPUT: tokens, _ELO_SELF_INPUT: elo_in, _ELO_OPPO_INPUT: elo_in}
    outputs = _session.run([_LOGITS_OUTPUT], feeds)
    policy = np.asarray(outputs[0]).reshape(-1).astype(np.float32)
    probs = mask_and_softmax(policy.tolist(), fen)
    return probs.get(played_uci)
```
`score_move` becomes `probs = full_policy(fen, elo); return None if probs is None else probs.get(played_uci)`.
`start_maia` session construction to extend (keep its try/except + `sentry_sdk.capture_exception()` + success log):
```python
        _session = onnxruntime.InferenceSession(
            str(_MODEL_PATH), providers=["CPUExecutionProvider"]
        )
```
Add keyword-only `intra_op_num_threads: int | None = None`; when set, build `onnxruntime.SessionOptions()` and pass `sess_options=`. Default None keeps backend behavior unchanged.

### `app/services/maia_flaw_stats.py` (NEW, pure)

No codebase analog; use RESEARCH.md "Pure stats (D-01)" code example (TypedDict `MaiaFlawStats`, `_rank` with strict `>`, `RANK_BASE = 1` named constant, `second == best` -> None per D-15). Reason buckets must be a `Literal[...]` (e.g. `"played_not_legal", "no_rating", "pgn_unparseable", "fen_mismatch", "ply_beyond_mainline", "second_equals_best", "invalid_root"`). TypedDict for internal data per CLAUDE.md (precedent `app/services/stats_service.py`).

### `app/services/maia_flaw_scoring.py` (NEW)

**Analog A (session discipline + off-thread inference + Sentry fail-safe):** `app/services/eval_apply.py:2152-2235` `_build_best_move_candidates`:
```python
        rating_metadata = await _fetch_rating_metadata(game_id)
        if rating_metadata is None:
            return []
        white_rating, black_rating, platform, tc_bucket, is_correspondence = rating_metadata

        # Run in a worker thread: the Maia score_move calls inside
        # take ~150 ms each ... onnxruntime releases the GIL, and InferenceSession.run
        # is safe to call concurrently from several threads.
        return await asyncio.to_thread(
            _assemble_candidate_rows, game_id, candidate_targets, ...
        )
    except Exception:
        sentry_sdk.set_context("best_move_candidates", {"game_id": game_id})
        sentry_sdk.capture_exception()
        return []
```
Reuse `_fetch_rating_metadata` (`eval_apply.py:~2304-2329`) and `pinned_elo_for_mover` (`app/services/best_move_candidates.py:79`); skip when mover raw rating is None (precedent `eval_apply.py:2369-2372`). Mover via `board.turn`, not ply parity. On exception: `set_context("maia_flaws", {...})`, `set_tag("source", lane)`, capture, and do NOT stamp.

**Analog B (in-lock re-read before write):** `app/routers/eval_remote.py:1043-1087` (FLAWCHESS-8D):
```python
    async with async_session_maker() as write_session:
        await write_session.execute(
            sa.text("SELECT pg_advisory_xact_lock(:lock_key)"),
            {"lock_key": _game_write_lock_key(game_id)},
        )
        surviving_plies: set[int] = set(
            (await write_session.execute(
                sa.select(GameFlaw.ply).where(GameFlaw.game_id == game_id, GameFlaw.user_id == game.user_id)
            )).scalars().all()
        )
        blob_map = {ply: blob for ply, blob in blob_map.items() if ply in surviving_plies}
        ...
        await write_session.commit()
```
Extend the re-read to a fingerprint `{(ply, fen, best_move, missed su)}`; mismatch -> skip, leave unstamped. Lock games in ascending id order for multi-game batches (backfill). Take the `session_maker` as a parameter (lane module's maker; tests monkeypatch per module). Make the inference entry point a module attribute so tests can monkeypatch it (Pitfall 3).

Guardrail: decide stamping from `maia_engine.is_maia_available()` (see `eval_apply.py:2960-2964` comment "NEVER inferred from best_move_rows being empty").

### `app/repositories/game_flaws_repository.py` (MOD)

**Tuple constant analog** (lines ~153-170):
```python
TACTIC_TAG_COLUMNS: tuple[str, ...] = ("allowed_tactic_motif", ...)
FLAW_BLOB_AND_TACTIC_COLUMNS: tuple[str, ...] = ("allowed_pv_lines", "missed_pv_lines") + TACTIC_TAG_COLUMNS
```
Add `MAIA_FLAW_COLUMNS` as its own tuple. Do NOT add it to `FLAW_BLOB_AND_TACTIC_COLUMNS` and do NOT add Maia keys to `flaw_record_to_row` (lines 101-127); preservation-by-omission is automatic (RESEARCH Q4).

**Bulk update analog** (`bulk_update_game_flaw_rows`, ~246-264):
```python
    if not rows:
        return
    await session.execute(update(GameFlaw), rows)
```
New `bulk_update_flaw_maia_stats` = same body; every dict carries 3 PK + all 8 Maia keys (same key set per executemany).

**Stamp helper analog** (`app/services/eval_apply.py:827-841` `_mark_best_moves_completed`):
```python
    now_ts = datetime.now(timezone.utc)
    games_table = Game.__table__
    stmt = (
        update(games_table)  # ty: ignore[invalid-argument-type]
        .where(games_table.c.id == game_id)
        .values(best_moves_completed_at=now_ts)
    )
    await session.execute(stmt)
```
Set helper: `.where(games_table.c.id.in_(ids))`. Clear helper: `.values(maia_flaws_completed_at=None)` plus `.where(... .isnot(None)).returning(games_table.c.id)` so the caller learns whether it unstamped.

### `app/services/eval_apply.py` `_classify_and_fill_oracle` (MOD)

Signature at 995-1001 currently returns `None`. Insert the clear right after `await _diff_upsert_flaw_rows(...)` (lines 1123-1131), before `refresh_game_flaw_counts_and_accuracy`. Change return to a small result (bool or TypedDict) with early "not analyzed" returns giving False. Update the three callers: `eval_apply.py:2949`, `scripts/backfill_flaws.py:182`, `scripts/opening_cache_repair.py:2040`. On the Maia-loaded go-forward path the clear is immediately followed by the post-commit scorer re-stamping (D-08).

### `app/services/eval_drain.py` `_full_drain_tick` (MOD)

Insertion point (lines 1570-1578):
```python
        outcome = await commit_unless_game_deleted(write_session, game_id, _write)

    if outcome is None:
        logger.info("full_eval_drain: game %s deleted before write, discarding tick", game_id)
        return False

    _failed_ply_count, stamp_complete, _flaws_written = outcome
    # <-- call score_game_flaws_after_apply(async_session_maker, game_id, targets) HERE (D-08/D-13, before Path B return)
    if not stamp_complete:
        return False
```

### `app/routers/eval_remote.py` (MOD)

- Atomic submit: after the `if outcome is None: ... raise HTTPException(404)` block (~1461-1467), before `if stamp_complete: _signal_flaw_completion(owner_id)`. Router stays thin: one call into the service.
- Flaw-blob submit (D-14): after `await write_session.commit()` at ~1087, outside the `async with`, call the shared scorer (boards rebuilt from PGN replay since no `targets` exist there). Only when `is_maia_available()`.

### `scripts/backfill_maia_flaws.py` (NEW)

**Arg parsing analog:** `scripts/backfill_flaws.py:94-135`:
```python
    parser.add_argument(
        "--db",
        choices=["dev", "benchmark", "prod"],
        required=True,
        help="DB target: dev (localhost:5432), benchmark (localhost:5433), prod (via SSH tunnel).",
    )
    parser.add_argument("--user-id", type=int, default=None, dest="user_id", ...)
    parser.add_argument("--dry-run", action="store_true", dest="dry_run", ...)
    parser.add_argument("--limit", type=int, default=None, ...)
```
Entry: `asyncio.run(run_backfill(**vars(_parse_args())))` (`backfill_flaws.py:437`).

**Engine/Sentry/session-maker injection** (`backfill_flaws.py:~278-284`):
```python
    if settings.SENTRY_DSN:
        sentry_sdk.init(dsn=settings.SENTRY_DSN, environment=settings.ENVIRONMENT)
    if session_maker is None:
        url = db_url_for_target(db)
        engine = create_async_engine(url, pool_pre_ping=True)
        session_maker = async_sessionmaker(engine, expire_on_commit=False)
```
(`db_url_for_target`, `DbTarget` from `app/core/config.py:217-236`.) Shard procs: `pool_size=1, max_overflow=0`.

**Advisory lock in script** (`backfill_flaws.py:168-171`):
```python
        await session.execute(
            text("SELECT pg_advisory_xact_lock(:lock_key)"),
            {"lock_key": _game_write_lock_key(game_id)},
        )
```

**Hash-residue sharding** (`scripts/engine_disagreement_study/seed153_scan_sample.py:129-136`; drop the seed):
```sql
('x' || substr(md5(id::text || :seed), 1, 8))::bit(32)::bigint AS h
...
WHERE h % CAST(:num_shards AS bigint) = CAST(:shard AS bigint)
```

**Spawn context** (`scripts/retag_flaws.py:945`): `mp.get_context("spawn")`; here spawn N shard processes, each running its own `asyncio.run`, `await start_maia(intra_op_num_threads=1)`, abort if `not is_maia_available()`.

Logging: `print(..., flush=True)` (or the `_log` helper style in backfill_flaws.py). Per-shard JSON report under `reports/maia-flaws-backfill/{db}-{UTC ts}-shard{k}.json`. Selector: `stamp IS NULL AND EXISTS(flaws)`, ordered `u.last_activity DESC NULLS LAST, g.played_at DESC NULLS LAST, g.id DESC`; zero-flaw games stamped too (D-05) — note the selector only finds games with flaws, so go-forward handles zero-flaw stamping.

### `scripts/backfill_flaws.py` (MOD)

Default branch (lines 391-402) is delete-then-insert:
```python
                    await delete_flaws_for_game(session, game_id=game_id_val, user_id=game_user_id)
                    rows = [flaw_record_to_row(...) for flaw in flaw_list]
                    await bulk_insert_game_flaws(session, rows)
```
Add the stamp-clear helper call after the insert (count it), and a final one-line D-11 reminder when count > 0. `--oracle-gap` path (`_rederive_oracle_gap_game`, 160-187) consumes the new `_classify_and_fill_oracle` return value.

### Tests

- **Sentinel Maia presence:** `monkeypatch.setattr(maia_engine, "_session", object())` and mock `eval_apply_module.score_move` (`tests/services/test_full_eval_drain.py:2682, 2771, 2846, 2948`; `tests/test_eval_worker_endpoints.py:6351-6355`). `test_non_tier4b_claim_still_takes_full_path` (2846) must also patch the new scorer's inference attribute.
- **Real ORT:** `pytest.importorskip("onnxruntime")` as in `tests/services/test_maia_engine.py:95`; extend `test_score_move_returns_played_move_probability` (line 110) with a `full_policy` sum-to-1 / parity check.
- **Isolation:** unique module `_TEST_USER_ID`, `finally:` cleanup for every non-guest Game; scope backfill selector with `user_id`/`game_ids` (Pitfall 5).
- **Goldens:** `tests/services/write_path_golden_scenarios.py:61-80` uses an explicit column list, so unaffected.

## Shared Patterns

### Per-game write serialization
**Source:** `_game_write_lock_key` + `pg_advisory_xact_lock` (`app/services/eval_apply.py:2934-2937`, `scripts/backfill_flaws.py:168-171`).
**Apply to:** scorer write phase, backfill writes.

### Maia guardrail
**Source:** `app/services/maia_engine.py` `is_maia_available()` + `eval_apply.py:2960-2964` comment.
**Apply to:** every stamp decision. Never from row counts; never after an exception.

### Sentry in services
**Source:** `eval_apply.py` `_build_best_move_candidates` except block (`set_context` + `capture_exception`, no variables in messages).
**Apply to:** `maia_flaw_scoring.py`, backfill script.

### Deleted-game race on commit
**Source:** `commit_unless_game_deleted` (`eval_apply.py:2748-2812`), used at `eval_drain.py:1570` and router ~1459.
**Apply to:** scorer write if it can race game deletion (or rely on PK update matching zero rows; ORM bulk-update-by-PK raises StaleDataError on a vanished row, so filter to surviving plies as in the FLAWCHESS-8D re-read).

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `app/services/maia_flaw_stats.py` | utility | transform | Entropy/rank math is new; use RESEARCH.md Code Examples |

## Metadata

**Analog search scope:** `app/services`, `app/repositories`, `app/models`, `app/routers`, `alembic/versions`, `scripts/`, `tests/services`
**Files scanned:** ~14
**Pattern extraction date:** 2026-11-08
