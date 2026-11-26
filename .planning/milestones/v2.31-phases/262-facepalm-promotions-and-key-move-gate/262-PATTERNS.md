# Phase 262: Facepalm Promotions as Material and Key-Move Gate - Pattern Map

**Mapped:** 2026-11-23
**Files analyzed:** 13 (2 new, 11 modified)
**Analogs found:** 13 / 13 (all analog paths verified git-tracked)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `scripts/backfill_promotion_material.py` (NEW) | operator script | batch (keyset page, recompute, change-only UPDATE) | `scripts/retag_flaws.py` (structure) + `scripts/backfill_maia_flaws.py` (one-connection engine, signals, `_log`) | exact (retag is row-scoped game_flaws recompute with dry run) |
| `tests/scripts/test_backfill_promotion_material.py` (NEW) | test (DB integration) | batch | `tests/scripts/test_retag_flaws.py` (dry run / idempotency) + `tests/scripts/test_backfill_maia_flaws.py` (`make_game`, REAL tolerance, line facts) | exact |
| `app/services/line_material.py` | service (pure) | transform | self (`_victim_value`, `_exchange_value`) | in-place |
| `app/services/facepalm_score.py` | service (SQL + Python twin) | transform / query expr | self (`_key_move_term`, `_key_move_sql`, `facepalm_type_of`, `facepalm_type_sql`) | in-place |
| `app/services/blunder_check_rules.py` | config (constants) | n/a | self | in-place |
| `app/services/facepalm_zones.py` | config docstring | n/a | self | in-place (D-08 note only) |
| `scripts/blunder_check/fit_facepalm.py` | offline script | batch | self (`missing_reason`, `design_row`) | in-place |
| `scripts/blunder_check/facepalm_features.py` | offline script | file-I/O transform | self (`_has_null_score_input`) | in-place |
| `scripts/blunder_check/caught_rate.py` | offline report | batch read | self (lines 327-361) | in-place |
| `scripts/backfill_maia_flaws.py` | operator script status | read | self (lines 1066-1084) | in-place |
| `tests/services/test_line_material.py`, `tests/services/line_material_fixtures.py`, `test_facepalm_inputs.py`, `test_facepalm_score.py` | test (unit) | transform | self | extend |
| `tests/scripts/test_fit_facepalm.py`, `test_facepalm_features.py`, `test_caught_rate.py` | test | batch | self | extend |
| `docs/dev-tooling.md`, `CHANGELOG.md` | docs | n/a | existing `backfill_maia_flaws.py` section | in-place |

## Pattern Assignments

### `scripts/backfill_promotion_material.py` (operator script, batch)

**Primary analog:** `scripts/retag_flaws.py` (1037 lines). It already does exactly the phase's shape: PK keyset pages over `game_flaws`, engine-free recompute through the app's single code path, UPDATE only changed rows, `--dry-run`, injectable `session_maker` and `report_dir` for tests. Prefer it over line mode of `backfill_maia_flaws.py`, which is game-scoped and stamps games (RESEARCH Finding 5).

**Module docstring** (retag_flaws.py lines 1-98): states why a dedicated script, scope, batching, DB targets, run location, usage. Copy that layout; for this phase add D-06 reversibility note and the undo log path under `temp/`.

**Imports / bootstrap** (retag_flaws.py lines 102-135):
```python
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Any, Literal

import sentry_sdk
from sqlalchemy import Row, or_, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Bootstrap project root so `app.*` imports resolve when running as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import db_url_for_target, settings  # noqa: E402
from app.models.game_flaw import GameFlaw  # noqa: E402
from app.models.game_position import GamePosition  # noqa: E402

# GameFlaw/GamePosition carry FKs to games → users → oauth_accounts. Importing only the
# queried models leaves those parent tables unregistered and select() raises
# NoReferencedTableError at compile time, so register the whole chain.
from app.models.game import Game  # noqa: E402, F401
from app.models.oauth_account import OAuthAccount  # noqa: E402, F401
from app.models.user import User  # noqa: E402, F401
```
Add for this phase: `from app.services.maia_flaw_scoring import replay_flaw_boards` and `from app.services.facepalm_inputs import facepalm_material_inputs` (the single writer, 259 D-05), `from app.services.facepalm_score import facepalm_type_of` (type-flip counts), and for dry run `from scripts.blunder_check.sample import make_readonly_engine`.

**Constants** (retag_flaws.py line 153): `FLAWS_PER_BATCH = 2000` named, commented. Also name the promotion regex(es), sample size, sample seed, float tolerance.

**Logging, flushed** (backfill_maia_flaws.py lines 274-277; use this one, not retag's unflushed version, because the run is `setsid nohup` with redirected stdout):
```python
def _log(msg: str = "") -> None:
    """Print a UTC-timestamped line, flushed (Python 3.14 block-buffers redirected stdout)."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)
```

**Cooperative SIGTERM** (backfill_maia_flaws.py lines 270-271, 394-405):
```python
_stop_requested: bool = False

def _install_signal_handlers() -> None:
    """Cooperative SIGINT/SIGTERM: finish the current batch, write the report, exit."""
    global _stop_requested
    _stop_requested = False

    def _request_stop(signum: int, _frame: object) -> None:
        global _stop_requested
        _log(f"signal {signum} received, stopping after this batch")
        _stop_requested = True

    signal.signal(signal.SIGINT, _request_stop)
    signal.signal(signal.SIGTERM, _request_stop)
```

**One-connection engine with test injection** (backfill_maia_flaws.py lines 637-643; retag lines 903-906 omit `pool_size=1`, do NOT copy that part):
```python
engine = None
if session_maker is None:
    engine = create_async_engine(
        db_url_for_target(db), pool_size=1, max_overflow=0, pool_pre_ping=True
    )
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
```
Dry run: `make_readonly_engine(db_url_for_target(db))` (scripts/blunder_check/sample.py lines 110-118: `pool_size=1, max_overflow=0, pool_pre_ping=True, connect_args=readonly_connect_args()`).

**CLI** (retag_flaws.py lines 187-264): `--db choices=["dev","benchmark","prod"] required`, `--user-id`, `--dry-run`, `--limit`, `--throttle-ms`. Drop `--workers` / `--margin` (replay is cheap; one process). Add `--report-dir`, `--undo-log`, `--sample-size`. Main block (lines 1025-1037) narrows `args.db` to `Literal[...]` before calling `asyncio.run(run_...)`.

**Keyset page fetch** (retag_flaws.py lines 423-466):
```python
if after is not None:
    # Keyset pagination on the (user_id, game_id, ply) PK — uses the PK index and is
    # resumable, unlike OFFSET which degrades on large tables (prod has millions).
    stmt = stmt.where(tuple_(GameFlaw.user_id, GameFlaw.game_id, GameFlaw.ply) > after)
stmt = stmt.order_by(GameFlaw.user_id, GameFlaw.game_id, GameFlaw.ply).limit(limit)
```
Combine with the RESEARCH candidate filter (Finding 5): join `games` (`facepalm_line_completed_at IS NOT NULL`, plus `pgn`), `game_positions p0` at `ply`, LEFT JOIN `p1` at `ply + 1`, `severity = 2`, and the token OR (`p1.pv ~ '(^| )[a-h][27][a-h][18][qrbn]( |$)'`, same on `p0.pv`, `p0.best_move ~ '^[a-h][27][a-h][18][qrbn]$'`, `p0.move_san LIKE '%=%'`). Express with SQLAlchemy `.regexp_match()` / `.like()` and `aliased(GamePosition)`; keep the regex a named constant. Select columns as a tuple (retag docstring lines 431-436 explains why: no ORM entities). Include NULL stored loss rows.

**Per-row recompute** (pattern from line mode, app/services/maia_flaw_scoring.py lines 396-427 `replay_flaw_boards(pgn_text, plies) -> (dict[ply, (board, played_uci)], reason)`): group a page by game, call once per game, guard `board.board_fen() == row.fen`, count board failures, then:
```python
inputs = facepalm_material_inputs(board, played_uci, p1_pv, p0_pv or p0_best_move)
```
(signature at app/services/facepalm_inputs.py lines 56-70).

**Change test in float32** (RESEARCH "float32 comparison for the pass"):
```python
def as_real(value: float | None) -> float | None:
    """The value PostgreSQL REAL stores for `value` (float4 round trip)."""
    return None if value is None else struct.unpack("f", struct.pack("f", value))[0]
```

**Page loop + Sentry** (retag_flaws.py lines 787-865 `_process_page`): fetch, compute, `if not dry_run: write; commit`, `except Exception: sentry_sdk.set_context("<script>", {"page": ..., "last_game_id": ..., "last_ply": ...}); sentry_sdk.capture_exception(exc); raise`. IDs in context, never in the message (CLAUDE.md). Outer loop (lines 937-996): page_size vs `--limit`, `after = (last.user_id, last.game_id, last.ply)`, progress line with "would change" / "changed", throttle only when writing. Add `if _stop_requested: break`.

**Guarded UPDATE** (new; precedent for `IS NOT DISTINCT FROM` guard is `scripts/repair_short_lines.py` lines 456-470):
```sql
UPDATE game_flaws SET material_loss = :new_loss, material_missed = :new_missed
WHERE user_id = :u AND game_id = :g AND ply = :p
  AND material_loss IS NOT DISTINCT FROM :old_loss
  AND material_missed IS NOT DISTINCT FROM :old_missed
```
Count rowcount 0 as `guard_misses`. Bind old values exactly as read. Note the CHECK that writes the pair together (test_backfill_maia_flaws.py line 1003 comment), so always set both.

**Report** (retag_flaws.py `_write_retag_report` lines 649-785, written every run, dry run or not, into an injectable `report_dir`): counters candidates, would-change/changed, loss up/down, missed up/down, NULL to value, type flips (via `facepalm_type_of`), board failures, guard misses, sample mismatches. A dataclass report like `ShardReport` in backfill_maia_flaws.py with `asdict` to JSON is an acceptable alternative.

**Nesting gate:** retag's `_process_page` docstring (lines 801-806) documents splitting for depth <= 4; keep the same seams (`_fetch_page`, `_recompute_page`, `_write_page`, `_sample_check`).

---

### `tests/scripts/test_backfill_promotion_material.py` (DB integration test)

**Analog:** `tests/scripts/test_retag_flaws.py` (dry-run / idempotency structure) with the committed-game factory of `tests/scripts/test_backfill_maia_flaws.py`.

**Module docstring + cleanup rule** (test_retag_flaws.py lines 1-20): list the cases (dry run writes 0, real run updates only changed rows, re-run changes 0, guard miss counted, token filter UCI and SAN, non-token row untouched, float32 no phantom change). Committed data, deleted in teardown (eval-lottery isolation memory).

**Imports** (test_retag_flaws.py lines 22-40):
```python
from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.game import Game
from app.models.game_flaw import GameFlaw
from app.models.game_position import GamePosition
from app.models.user import User
from app.services.facepalm_inputs import facepalm_material_inputs
from scripts import backfill_promotion_material as backfill
```

**Constants** (test_backfill_maia_flaws.py lines 48-59): unique `_TEST_USER_ID` (grep tests/ for collisions; 247_001 and 143_030 are taken), `_REAL_REL_TOL = 1e-6` with the comment "The stored scalars are REAL (float32)".

**Session factory** (test_backfill_maia_flaws.py lines 75-77):
```python
@pytest_asyncio.fixture
async def session_factory(test_engine: Any) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(test_engine, expire_on_commit=False)
```

**Committed game factory with teardown** (test_backfill_maia_flaws.py lines 88-160+, `make_game`): ensure user exists, `Game(... pgn=..., facepalm_line_completed_at=func.now())`, one `GamePosition` per ply with `pv` / `best_move` / `move_san` per ply, `GameFlaw(severity=2, fen=<board_fen>, material_loss=..., material_missed=...)`; delete `Game` in teardown (cascade). The retag fixture (test_retag_flaws.py lines 98-216) is the shorter single-game version. Use a promotion PGN; the RESEARCH Finding 1 FENs need a PGN with `[SetUp "1"][FEN ...]` headers, since `replay_flaw_boards` reads the PGN.

**Expected values from the app function, not hard-coded** (test_backfill_maia_flaws.py lines 905-917):
```python
def _fact_columns(pre: chess.Board, played: str, line: str | None) -> dict[str, Any]:
    return {
        "line_mate_ply": quiet_line_facts(pre, played, line).mate_ply,
        "material_loss": facepalm_material_inputs(pre, played, line, None).loss,
    }
```
Seed the "old" pair by hand, run, assert `pytest.approx(new, rel=_REAL_REL_TOL)`.

**Run with injection** (test_retag_flaws.py lines 304-320): `await backfill.run_...(db="dev", dry_run=..., session_maker=session_factory, report_dir=tmp_path, undo_log=tmp_path / ...)`, then read rows back and assert on the report file in `tmp_path`. Idempotency test: second real run reports 0 changed (test_retag_flaws.py lines 416-455). Guard-miss test: mutate the stored pair between read and write by monkeypatching the recompute step (or a hook) and assert count, mirroring `_set_flaw` helper (test_backfill_maia_flaws.py lines 853-863).

---

### `app/services/line_material.py` (service, transform)

In-place. Current `_victim_value` lines 128-133 and `_exchange_value` lines 147-156 (quoted in RESEARCH Finding 1). Copy the RESEARCH "D-01 inside `_victim_value`, reused by the SEE" block: add `_promotion_gain(move)`, add it in `_victim_value`, replace the gain lookup in `_exchange_value` with `_victim_value(board, capture)` and a bug-fix comment at the site (CLAUDE.md). Rewrite the docstring line "promotions are not material" (line 12) and note Pitfalls 4 and 5.

### `app/services/facepalm_score.py` (twins)

In-place: gate at lines 218-222 (`_key_move_term`), 261-271 (`_key_move_sql`), type at 323-332 / 343-358. Add the shared condition (RESEARCH "Pattern: one shared condition, two twins"):
```python
def is_allowed_loss(loss: float, missed: float | None) -> bool:
    return loss > 0 and loss >= (0.0 if missed is None else missed)

def _allowed_loss_sql(columns: FacepalmColumns) -> ColumnElement[bool]:
    return and_(columns.loss > 0, columns.loss >= func.coalesce(columns.missed, literal(0.0)))
```
NULL guard stays the first CASE branch. `facepalm_type_sql` already uses `func.coalesce(columns.missed, literal(0.0))`, so reuse it there.

### `scripts/blunder_check/fit_facepalm.py`

`missing_reason` (lines 358-373, `if loss > 0:`) and `design_row` (lines 417-434, `losing = loss > 0`): replace with `is_allowed_loss(loss, missed)`; add a gate parameter (`Literal["type", "loss"]`, default type) for the D-05 reference line. `_shape_material` (line ~355) already returns `(loss, missed)`.

### `scripts/blunder_check/facepalm_features.py`

`_has_null_score_input` lines 625-632: `return row.reply_prob is None if loss > 0 else row.best_prob is None` becomes `is_allowed_loss(loss, row.quiet.missed)` (check field name). Keep the existing bug-fix comment style (lines 626-628).

### `scripts/backfill_maia_flaws.py` (status counters)

Lines 1066-1084 `value_filters`: `GameFlaw.material_loss > 0` / `<= 0` follow the shared condition. Use a `FacepalmColumns` over `GameFlaw` with `_allowed_loss_sql` (or a public SQL helper) and its `not_()`; `not_` is already imported (line 138).

### `scripts/blunder_check/caught_rate.py`

Lines 327-361: add a timezone-aware `FACEPALM_262_SWITCH_AT` constant and split on `blunder_check_sessions.started_at` (not `ended_at`), per RESEARCH Finding 7. Wilson bounds via `app.services.score_confidence.wilson_bounds`.

### `app/services/blunder_check_rules.py`, `app/services/facepalm_zones.py`

Paste fitted constants as printed by `fit_facepalm.py` `## Constants` block; update the comment at line ~90 (formula / gate). `facepalm_zones.py`: docstring note only (D-08).

## Shared Patterns

### One connection, prod-safe operator run
**Source:** `scripts/backfill_maia_flaws.py` lines 637-643; `scripts/blunder_check/sample.py` lines 110-118
**Apply to:** the new pass script (write: `pool_size=1, max_overflow=0`; dry run: `make_readonly_engine`). Never print the URL; resolve it via `db_url_for_target`.

### Sentry in scripts
**Source:** `scripts/retag_flaws.py` lines 900-901 (`if settings.SENTRY_DSN: sentry_sdk.init(...)`) and lines 849-864 (`set_context` + `capture_exception` + re-raise).
**Apply to:** the new pass script.

### Python/SQL twin parity
**Source:** `tests/services/test_facepalm_score.py` (`test_sql_twin_parity_grid`, `test_sql_type_twin_parity_grid`, `test_expr_matches_python_twin_over_stored_facts`)
**Apply to:** every gate edit; add a mixed row (loss 1.0, missed 3.0, reply None) per RESEARCH Finding 3.

### REAL float tolerance
**Source:** `tests/scripts/test_backfill_maia_flaws.py` line 59 `_REAL_REL_TOL = 1e-6`; `tests/services/test_facepalm_owner_fixtures.py` line 29 `STORED_FLOAT_TOLERANCE = 1e-6`
**Apply to:** the pass script change test (float32 round trip) and its tests.

### Committed-data test cleanup
**Source:** `tests/scripts/test_retag_flaws.py` lines 211-216 (delete `Game` in teardown)
**Apply to:** the new DB test (non-guest Game inserts must be cleaned up for the eval lottery tests).

## No Analog Found

None. The undo log file (rows `(user_id, game_id, ply, old_loss, old_missed, new_loss, new_missed)` under gitignored `temp/promotion-pass/`) has no direct precedent (`repair_short_lines.py` lines 29-39 records that the owner declined one there); write it as a simple TSV/JSONL appended per committed batch.

## Metadata

**Analog search scope:** `scripts/`, `scripts/blunder_check/`, `tests/scripts/`, `app/services/`
**Files scanned:** ~12
**Pattern extraction date:** 2026-11-23
