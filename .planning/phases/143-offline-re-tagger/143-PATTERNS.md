# Phase 143: Offline Re-tagger - Pattern Map

**Mapped:** 2026-06-30
**Files analyzed:** 7
**Analogs found:** 7 / 7

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `scripts/retag_flaws.py` (renamed from `backfill_tactic_tags.py`) | script | batch, CRUD | `scripts/backfill_tactic_tags.py` (the file itself) | exact — extend + `git mv` |
| `app/services/forcing_line_gate.py` | service | transform | `app/services/forcing_line_gate.py` (self) | self-modification — add `margin` param |
| `app/services/flaws_service.py` | service | transform | `app/services/flaws_service.py` (self) | self-modification — add `_classify_tactic_gated` |
| `app/services/eval_drain.py` | service | event-driven | `app/services/eval_drain.py` (self) | self-modification — thread `flaw_pv_blobs` into classify call |
| `app/repositories/game_flaws_repository.py` | repository | CRUD | `app/repositories/game_flaws_repository.py` (self) | self-modification — docstring only |
| `tests/services/test_forcing_line_gate.py` | test | — | `tests/services/test_forcing_line_gate.py` (self) | exact — extend existing test classes |
| `reports/retag/retag-YYYY-MM-DD.md` | report | — | `reports/tactic-tagger/tactic-tagger-2026-06-23.md` | convention match |

---

## Pattern Assignments

### `scripts/retag_flaws.py` (script, batch CRUD) — renamed from `scripts/backfill_tactic_tags.py`

**Analog:** `scripts/backfill_tactic_tags.py` (the file is the analog — extend + `git mv`)

**Module docstring pattern** (lines 1-65 of `scripts/backfill_tactic_tags.py`):
The existing docstring explains why a dedicated script, scope flags, batching rationale,
and the prod-run recommendation. Update it to reflect:
- New role: re-derive tactic tags from stored JSONB blobs, applying the forcing-line gate
- The `--margin` flag and RETAG-01 goal (tunable engine-free re-derivation)
- Why a gate-free refresh no longer exists (D-01: once gate is in the live classify path,
  a gate-free backfill would diverge from production)

**Imports pattern** (lines 67-106):
```python
from __future__ import annotations

import argparse
import asyncio
import multiprocessing as mp
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import sentry_sdk
from sqlalchemy import Row, or_, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import db_url_for_target, settings
from app.models.game_flaw import GameFlaw
from app.models.game_position import GamePosition
from app.models.game import Game  # noqa: F401 — register FK chain
from app.models.oauth_account import OAuthAccount  # noqa: F401
from app.models.user import User  # noqa: F401
from app.repositories.game_flaws_repository import TACTIC_TAG_COLUMNS, bulk_update_tactic_tags
from app.services.flaws_service import _detect_tactic_for_flaw  # or _classify_tactic_gated post-D-02
```

**New import for gate** (add alongside the `flaws_service` import):
```python
from app.services.forcing_line_gate import ONLY_MOVE_WIN_PROB_MARGIN
```

**`_PosRow` dataclass — extend for `eval_cp`** (lines 113-123):
```python
@dataclass(frozen=True)
class _PosRow:
    move_san: str | None
    pv: str | None
    eval_mate: int | None
    eval_cp: int | None          # new — for gate's already-winning reject (pre_flaw_eval_cp)
```

**`_FlawWork` dataclass — extend for blobs + margin** (lines 206-223):
```python
@dataclass(frozen=True)
class _FlawWork:
    user_id: int
    game_id: int
    ply: int
    fen: str
    cur: _PosRow | None
    nxt: _PosRow | None
    old_tuple: tuple[int | None, ...]
    allowed_pv_blob: list[Any] | None   # new — allowed_pv_lines JSONB (list[dict] | None)
    missed_pv_blob:  list[Any] | None   # new — missed_pv_lines JSONB
    margin: float                        # new — passed from --margin CLI arg
```

**`_worker_recompute` — extend to call gated classify** (lines 226-249):
```python
def _worker_recompute(work: _FlawWork) -> tuple[int | None, ...] | None:
    ply = work.ply
    positions: list[Any] = [_EMPTY_POS] * (ply + 2)
    if work.cur is not None:
        positions[ply] = work.cur
    if work.nxt is not None:
        positions[ply + 1] = work.nxt
    fen_map = {ply: work.fen}
    pre_flaw_eval_cp = work.cur.eval_cp if work.cur is not None else None
    # Replace direct _detect_tactic_for_flaw calls with _classify_tactic_gated
    # (the gated wrapper added in D-02). Pass blobs + eval_cp + margin.
    allowed = _classify_tactic_gated(
        ply, fen_map, positions, "allowed",
        pv_blob=work.allowed_pv_blob,
        pre_flaw_eval_cp=pre_flaw_eval_cp,
        margin=work.margin,
    )
    missed = _classify_tactic_gated(
        ply, fen_map, positions, "missed",
        pv_blob=work.missed_pv_blob,
        pre_flaw_eval_cp=pre_flaw_eval_cp,
        margin=work.margin,
    )
    new_tuple = (*allowed, *missed)
    return None if new_tuple == work.old_tuple else new_tuple
```

**`_fetch_flaw_page` — add JSONB blob columns to SELECT** (lines 274-311):
```python
stmt = select(
    GameFlaw.user_id,
    GameFlaw.game_id,
    GameFlaw.ply,
    GameFlaw.fen,
    *(getattr(GameFlaw, col) for col in TACTIC_TAG_COLUMNS),
    GameFlaw.allowed_pv_lines,   # new — JSONB list[dict] | None; deferred on entity but OK here
    GameFlaw.missed_pv_lines,    # new
)
# existing WHERE / ORDER BY / LIMIT unchanged
```

**`_load_positions_for_page` — add `eval_cp`** (lines 314-336):
```python
stmt = select(
    GamePosition.user_id,
    GamePosition.game_id,
    GamePosition.ply,
    GamePosition.move_san,
    GamePosition.pv,
    GamePosition.eval_mate,
    GamePosition.eval_cp,        # new
).where(tuple_(GamePosition.user_id, GamePosition.game_id, GamePosition.ply).in_(keys))
return {
    (uid, gid, ply): _PosRow(move_san=move_san, pv=pv, eval_mate=eval_mate, eval_cp=eval_cp)
    for uid, gid, ply, move_san, pv, eval_mate, eval_cp in result.all()
}
```

**`_make_works` — pass blobs + margin** (lines 252-271):
```python
_FlawWork(
    user_id=flaw.user_id,
    game_id=flaw.game_id,
    ply=ply,
    fen=flaw.fen,
    cur=pos_by_key.get((flaw.user_id, flaw.game_id, ply)),
    nxt=pos_by_key.get((flaw.user_id, flaw.game_id, ply + 1)),
    old_tuple=_tactic_tuple(flaw),
    allowed_pv_blob=flaw.allowed_pv_lines,  # new
    missed_pv_blob=flaw.missed_pv_lines,    # new
    margin=margin,                           # new — threaded from run_backfill arg
)
```

**CLI `--margin` arg — add to `_parse_args`** (lines 139-198 pattern):
```python
parser.add_argument(
    "--margin",
    type=float,
    default=ONLY_MOVE_WIN_PROB_MARGIN,
    help=(
        "Forcing-line gate win-prob margin (default: ONLY_MOVE_WIN_PROB_MARGIN=0.35). "
        "A larger value suppresses more tags; use --dry-run to preview before writing."
    ),
)
```

**`run_backfill` — add `margin` param + report writer** (lines 365-491 pattern):
```python
async def run_backfill(
    *,
    db: str,
    user_id: int | None,
    only_tagged: bool,
    dry_run: bool,
    limit: int | None,
    workers: int | None = None,
    throttle_ms: int = 0,
    margin: float = ONLY_MOVE_WIN_PROB_MARGIN,  # new
    session_maker: async_sessionmaker[AsyncSession] | None = None,
) -> None: ...
```

**Error handling pattern** (lines 458-468):
```python
except Exception as exc:
    last = flaws[-1]
    sentry_sdk.set_context(
        "retag_flaws",   # rename context key to match new script name
        {"page": page_num, "last_game_id": last.game_id, "last_ply": last.ply},
    )
    sentry_sdk.capture_exception(exc)
    raise
```

**Report writer — inline in `run_backfill`** (pattern from dry-run accumulation):
```python
# During the page loop, accumulate per-motif counts in a Counter:
from collections import Counter
motif_removed: Counter[str] = Counter()
motif_survived: Counter[str] = Counter()

# In the page loop, after computing updates:
for flaw, new_tuple in zip(flaws, results, strict=True):
    old_allowed_motif = flaw.allowed_tactic_motif
    if old_allowed_motif is not None:
        new_allowed_motif = new_tuple[0] if new_tuple is not None else old_allowed_motif
        motif_name = TacticMotifInt(old_allowed_motif).name  # decode int → name
        if new_allowed_motif is None:
            motif_removed[motif_name] += 1
        else:
            motif_survived[motif_name] += 1
    # Same for missed_tactic_motif (index 4 in old_tuple / new_tuple)

# After the loop, write reports/retag/retag-YYYY-MM-DD.md if dry_run:
if dry_run:
    _write_retag_report(margin, user_id, motif_removed, motif_survived)
```

---

### `app/services/forcing_line_gate.py` (service, transform) — add `margin` param

**Analog:** self (lines 52-60 constants, ~153 `is_solver_node_forced`, ~265 `apply_forcing_line_filter`)

**Constants pattern** (lines 52-60 — no changes to constants, only function signatures):
```python
ONLY_MOVE_WIN_PROB_MARGIN: float = 0.35
ALREADY_WINNING_CP_THRESHOLD: int = 300
STILL_WINNING_FLOOR_CP: int = 200
```

**`is_solver_node_forced` — add `margin` param** (line ~153, research-confirmed):
```python
# BEFORE (current):
def is_solver_node_forced(
    node: PvNode,
    solver_color: Literal["white", "black"],
) -> bool: ...
# line ~189: return p_best - p_second > ONLY_MOVE_WIN_PROB_MARGIN

# AFTER (D-03):
def is_solver_node_forced(
    node: PvNode,
    solver_color: Literal["white", "black"],
    margin: float = ONLY_MOVE_WIN_PROB_MARGIN,
) -> bool: ...
# line ~189 becomes: return p_best - p_second > margin
```

**`apply_forcing_line_filter` — add `margin` param and thread it** (line ~265, research-confirmed):
```python
# BEFORE (current):
def apply_forcing_line_filter(
    line: Sequence[PvNode],
    solver_color: Literal["white", "black"],
    pre_flaw_eval_cp: int,
) -> bool: ...
# line ~309: all(is_solver_node_forced(node, solver_color) for node in solver_nodes)

# AFTER (D-03):
def apply_forcing_line_filter(
    line: Sequence[PvNode],
    solver_color: Literal["white", "black"],
    pre_flaw_eval_cp: int,
    margin: float = ONLY_MOVE_WIN_PROB_MARGIN,
) -> bool: ...
# line ~309 becomes:
# all(is_solver_node_forced(node, solver_color, margin) for node in solver_nodes)
```

Private functions (`_resolve_mate_priority`, `_truncate_at_still_winning_floor`,
`_strip_trailing_only_moves`, `_is_already_winning`) require NO changes.

---

### `app/services/flaws_service.py` (service, transform) — add `_classify_tactic_gated`

**Analog:** `_detect_tactic_for_flaw` at line ~401 (the kernel being wrapped)

**Current `_detect_tactic_for_flaw` signature** (line 401, research-verified):
```python
def _detect_tactic_for_flaw(
    n: int,
    fen_map: dict[int, str],
    positions: list[GamePosition],
    pv_by_ply: Mapping[int, str] | None = None,
    orientation: Literal["allowed", "missed"] = "allowed",
) -> tuple[int | None, int | None, int | None, int | None]:
    # Returns (tactic_motif_int, tactic_piece, tactic_confidence, tactic_depth)
```

**New `_classify_tactic_gated` wrapper** (add near line 401, Option A from research):
```python
def _classify_tactic_gated(
    n: int,
    fen_map: dict[int, str],
    positions: list[GamePosition],
    orientation: Literal["allowed", "missed"],
    pv_blob: list[PvNode] | None,           # None = gate skipped (pre-Phase-142 rows)
    pre_flaw_eval_cp: int | None,           # None = gate skipped
    pv_by_ply: Mapping[int, str] | None = None,
    margin: float = ONLY_MOVE_WIN_PROB_MARGIN,
) -> tuple[int | None, int | None, int | None, int | None]:
    """Run tactic detection then apply the forcing-line gate (D-02, SC4 single classify path).

    When pv_blob or pre_flaw_eval_cp is None (pre-Phase-142 rows), the gate is
    skipped and the raw detect result is returned unchanged (backward compat).
    Gate condition is `pv_blob is not None` (not `if pv_blob`) — an empty list
    is a valid blob that should be rejected by the one-mover discard.
    """
    motif, piece, conf, depth = _detect_tactic_for_flaw(
        n, fen_map, positions, pv_by_ply, orientation
    )
    if motif is not None and pv_blob is not None and pre_flaw_eval_cp is not None:
        solver_color = _solver_color_for(n, orientation)
        if not apply_forcing_line_filter(pv_blob, solver_color, pre_flaw_eval_cp, margin):
            return None, None, None, None
    return motif, piece, conf, depth
```

**`_solver_color_for` helper** (ply-parity convention from research §3, matches line 444-446):
```python
def _solver_color_for(
    n: int,
    orientation: Literal["allowed", "missed"],
) -> Literal["white", "black"]:
    # Even ply: white moved (made the flaw).
    # "allowed": refuter (solver) is the opponent.
    # "missed": flaw-maker (solver) is white.
    if orientation == "allowed":
        return "black" if n % 2 == 0 else "white"
    return "white" if n % 2 == 0 else "black"
```

**`_build_flaw_record` call site** (lines 523-530 — switch to gated wrapper):
```python
# BEFORE:
allowed = _detect_tactic_for_flaw(n, fen_map, positions, pv_by_ply, orientation="allowed")
missed  = _detect_tactic_for_flaw(n, fen_map, positions, pv_by_ply, orientation="missed")

# AFTER (D-02): blobs come from caller, not DB (blobs not yet written at classify time)
allowed = _classify_tactic_gated(
    n, fen_map, positions, "allowed",
    pv_blob=flaw_pv_blobs.get(n, (None, None))[0] if flaw_pv_blobs else None,
    pre_flaw_eval_cp=...,   # planner decides exact source (positions[n].eval_cp)
)
missed = _classify_tactic_gated(
    n, fen_map, positions, "missed",
    pv_blob=flaw_pv_blobs.get(n, (None, None))[1] if flaw_pv_blobs else None,
    pre_flaw_eval_cp=...,
)
```

---

### `app/services/eval_drain.py` (service, event-driven) — thread `flaw_pv_blobs` into classify

**Analog:** self — the existing `_classify_and_fill_oracle` call site (line ~688) and
`_full_drain_tick` blob ordering (lines 2286-2329, research-verified)

**Critical ordering constraint** (research §3 Pitfall 4):
```
# Current order in _full_drain_tick (lines 2286-2329):
Step 3d: flaw_pv_blobs = await _build_flaw_multipv2_blobs(...)  # blobs in memory, NO session
Step 4 (write_session):
    await _classify_and_fill_oracle(write_session, game_id, engine_result_map)  # BEFORE blobs in DB
    await _run_multipv2_pass(write_session, game_id, flaw_pv_blobs)             # writes blobs
```

Blobs are NOT yet in the DB when `_classify_and_fill_oracle` runs. Pass `flaw_pv_blobs`
as a parameter to `_classify_and_fill_oracle` so classify can read blobs from memory.

**`_classify_and_fill_oracle` signature change:**
```python
# BEFORE:
async def _classify_and_fill_oracle(
    session: AsyncSession,
    game_id: int,
    engine_result_map: ...,
) -> None: ...

# AFTER (D-02 — add optional flaw_pv_blobs param):
async def _classify_and_fill_oracle(
    session: AsyncSession,
    game_id: int,
    engine_result_map: ...,
    flaw_pv_blobs: dict[int, tuple[list[PvNode] | None, list[PvNode] | None]] | None = None,
) -> None: ...
# flaw_pv_blobs maps flaw_ply -> (allowed_blob, missed_blob); None = no blobs (old games)
```

**Call site in `_full_drain_tick`** — pass the in-memory blobs:
```python
# BEFORE:
await _classify_and_fill_oracle(write_session, game_id, engine_result_map)

# AFTER:
await _classify_and_fill_oracle(write_session, game_id, engine_result_map, flaw_pv_blobs)
```

---

### `app/repositories/game_flaws_repository.py` (repository) — docstring update only

**Analog:** self (lines 152, 172)

**Docstring lines to update** (lines 152 and 172):
```python
# line 152 — BEFORE:
# The 8 tactic-tag columns refreshed in isolation by backfill_tactic_tags.py.

# line 152 — AFTER:
# The 8 tactic-tag columns refreshed in isolation by retag_flaws.py.

# line 172 (inside bulk_update_tactic_tags docstring) — BEFORE:
# Used by backfill_tactic_tags.py to refresh tactic tags after a detector change

# line 172 — AFTER:
# Used by retag_flaws.py to refresh tactic tags after a detector change or gate margin change
```

No logic changes to `TACTIC_TAG_COLUMNS` or `bulk_update_tactic_tags`.

---

### `tests/services/test_forcing_line_gate.py` (test) — extend existing classes

**Analog:** self (468 lines — read in full; extend, do not rewrite)

**Existing test imports pattern** (lines 21-28):
```python
from app.services.forcing_line_gate import (
    ALREADY_WINNING_CP_THRESHOLD,
    ONLY_MOVE_WIN_PROB_MARGIN,
    STILL_WINNING_FLOOR_CP,
    PvNode,
    apply_forcing_line_filter,
    is_solver_node_forced,
)
```

**Existing helper functions** (lines 36-48 — reuse in new tests):
```python
def _cp_node(b: int, s: int | None = None) -> PvNode: ...
def _mate_node(bm: int, sm: int | None = None) -> PvNode: ...
def _only_move_node(b: int) -> PvNode: ...
```

**SC3 gap test — multi-ply defender ambiguity** (add to `TestOnlyMoveMargin` or a new
`TestDefenderBranching` class after line 162):
```python
def test_multi_ply_defender_ambiguity_does_not_kill_line(self) -> None:
    """Multiple ambiguous defender nodes in a 5-node line do not kill a forced solver line.

    [S0=forced, D0=ambiguous, S1=forced, D1=ambiguous, S2=forced] — branch-then-reconverge
    at BOTH D0 and D1; solver continuations S0/S1/S2 are all forced. The line must pass.
    Residual SC3 gap (Phase 143 GATE-04): the existing tests cover only single-node defender
    ambiguity; this verifies the multi-ply "branch-then-reconverge" case.
    """
    line: list[PvNode] = [
        _cp_node(b=800, s=0),    # S0 solver — forced (large gap)
        _cp_node(b=100, s=50),   # D0 defender — ambiguous (s close to b); NOT checked
        _cp_node(b=800, s=0),    # S1 solver — forced
        _cp_node(b=100, s=80),   # D1 defender — highly ambiguous; NOT checked
        _cp_node(b=800, s=0),    # S2 solver — forced
    ]
    assert apply_forcing_line_filter(line, "white", pre_flaw_eval_cp=0) is True
```

**D-03 margin-param test** (add to `TestOnlyMoveMargin` or new `TestMarginParam` class):
```python
def test_margin_param_is_respected_by_is_solver_node_forced(self) -> None:
    """is_solver_node_forced respects a passed-in margin rather than the module constant (D-03)."""
    # Node with a delta between 0.1 and 0.5 (passes at margin=0.1, fails at margin=0.5).
    # p(400,"white") - p(200,"white") ≈ 0.799 - 0.677 = 0.122.
    node = _cp_node(b=400, s=200)
    assert is_solver_node_forced(node, "white", margin=0.1) is True
    assert is_solver_node_forced(node, "white", margin=0.5) is False

def test_apply_filter_margin_param_is_respected(self) -> None:
    """apply_forcing_line_filter threads the margin param to is_solver_node_forced (D-03)."""
    line: list[PvNode] = [
        _cp_node(b=400, s=200),  # S0 — forced at 0.1, not at 0.5
        _cp_node(b=0, s=-100),   # D0 — defender, ignored
        _cp_node(b=400, s=200),  # S1 — forced at 0.1, not at 0.5
    ]
    assert apply_forcing_line_filter(line, "white", pre_flaw_eval_cp=0, margin=0.1) is True
    assert apply_forcing_line_filter(line, "white", pre_flaw_eval_cp=0, margin=0.5) is False
```

**Existing test class structure to place new tests after** (confirmed line ranges):
- `TestConstants` ~56-69
- `TestOnlyMoveMargin` ~77-162 — single-defender test is at line 148-161 (last test in class)
- `TestMatePriority` ~169-249 — SC2 fully satisfied, no new tests needed
- `TestAlreadyWinning` ~256-311
- `TestStillWinningFloor` ~319-383
- `TestLineStripping` ~391-468 — `test_defender_re_convergence_does_not_kill_line` at 442-457

New tests can go in `TestOnlyMoveMargin` (for the multi-ply defender and margin-param tests)
or in a new class appended after `TestLineStripping`. Either is fine; the planner decides.

---

### `reports/retag/retag-YYYY-MM-DD.md` (report) — new directory + file

**Analog:** `reports/tactic-tagger/tactic-tagger-2026-06-23.md`

**Report header convention** (from tactic-tagger report, lines 1-10):
```markdown
# FlawChess Re-tagger Report

**Generated:** YYYY-MM-DD HH:MM:SS UTC
**Margin:** 0.35 (or the --margin value passed to retag_flaws.py)
**Scope:** all users / user-ID N
**Mode:** dry-run (no writes)
**Flaws examined:** N
**Flaw rows that would change:** N
```

**Table convention** (follow tactic-tagger `| T | Motif | ... |` pipe-table style):
```markdown
## Allowed-orientation tag changes

| Motif | Previously tagged | Gate suppressed | Survived | Suppression % |
|-------|------------------|-----------------|----------|---------------|
| fork  | N                | N               | N        | N%            |
| pin   | N                | N               | N        | N%            |
...

## Missed-orientation tag changes

| Motif | Previously tagged | Gate suppressed | Survived | Suppression % |
|-------|------------------|-----------------|---------|---------------|
...

## Summary

**Total allowed tags suppressed:** N / N_total (N%)
**Total missed tags suppressed:** N / N_total (N%)
```

**Path convention:** `reports/retag/retag-YYYY-MM-DD.md`
The `reports/retag/` directory does not yet exist — the script must create it:
```python
report_path = Path(__file__).resolve().parent.parent / "reports" / "retag" / f"retag-{date}.md"
report_path.parent.mkdir(parents=True, exist_ok=True)
report_path.write_text(content)
```

---

## Shared Patterns

### Sentry error capture (apply to `scripts/retag_flaws.py` exception handler)
**Source:** `scripts/backfill_tactic_tags.py` lines 458-468
```python
sentry_sdk.set_context(
    "retag_flaws",
    {"page": page_num, "last_game_id": last.game_id, "last_ply": last.ply},
)
sentry_sdk.capture_exception(exc)
raise
# NEVER embed variables in the exception message (CLAUDE.md: fragments Sentry grouping)
```

### Keyset pagination (preserve verbatim in `_fetch_flaw_page`)
**Source:** `scripts/backfill_tactic_tags.py` lines 305-309
```python
stmt = stmt.where(tuple_(GameFlaw.user_id, GameFlaw.game_id, GameFlaw.ply) > after)
stmt = stmt.order_by(GameFlaw.user_id, GameFlaw.game_id, GameFlaw.ply).limit(limit)
```

### Change-only UPDATE (preserve verbatim — no WAL for no-op rows)
**Source:** `scripts/backfill_tactic_tags.py` lines 339-362 (`_updates_from_results`)
```python
for flaw, new_tuple in zip(flaws, results, strict=True):
    if new_tuple is None:
        continue  # no-op — skip to avoid needless WAL
    update_row: dict[str, object] = {"user_id": ..., "game_id": ..., "ply": ...}
    update_row.update(dict(zip(TACTIC_TAG_COLUMNS, new_tuple, strict=True)))
    updates.append(update_row)
```

### Spawn-worker pool (preserve verbatim — fork inherits async loops)
**Source:** `scripts/backfill_tactic_tags.py` lines 419-421
```python
executor = ProcessPoolExecutor(
    max_workers=worker_count,
    mp_context=mp.get_context("spawn"),
)
```

### JSONB deferred columns — select explicit columns, not full ORM entities
**Source:** RESEARCH.md §4 (Pitfall 1), `app/models/game_flaw.py` lines 120-121
```python
# deferred=True on allowed_pv_lines / missed_pv_lines means select(GameFlaw) never loads them.
# Selecting the column attribute explicitly in _fetch_flaw_page bypasses deferred loading:
GameFlaw.allowed_pv_lines,
GameFlaw.missed_pv_lines,
# asyncpg auto-deserializes JSONB to list[dict] — cast to list[PvNode] for type-checker only.
```

### Gate-skip for None blobs (backward compat with pre-Phase-142 rows)
**Source:** RESEARCH.md §4 Pitfall 2
```python
# Gate condition: pv_blob is not None  (not `if pv_blob`)
# An empty list [] is a valid blob that SHOULD go through the gate and be rejected.
# NULL means pre-Phase-142 row — skip the gate entirely for backward compat.
if motif is not None and pv_blob is not None and pre_flaw_eval_cp is not None:
    if not apply_forcing_line_filter(pv_blob, solver_color, pre_flaw_eval_cp, margin):
        return None, None, None, None
```

### No asyncio.gather on the same AsyncSession
**Source:** CLAUDE.md hard rule; already respected in `backfill_tactic_tags.py`
```python
# DB access stays in the parent process (one connection, sequential queries).
# ProcessPoolExecutor workers do pure-CPU detection only — no session access.
```

---

## No Analog Found

All files have analogs. No entries in this section.

---

## Metadata

**Analog search scope:** `scripts/`, `app/services/`, `app/repositories/`, `tests/services/`, `reports/`
**Files scanned:** 7 primary files (all verified reads per RESEARCH.md sources)
**Pattern extraction date:** 2026-06-30
