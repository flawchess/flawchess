# Phase 221: Tactic-Tagger Real-Game Precision — Pattern Map

**Mapped:** 2026-09-12
**Files analyzed:** 16 (11 modified, 5 new)
**Analogs found:** 16 / 16 (every new file has an in-repo analog; this phase is almost entirely
"extend the file you are editing, in its own established style")

All analog paths below were verified git-TRACKED (`git ls-files`). No install/runtime mirrors are
referenced.

---

## File Classification

| New/Modified File | New? | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|------|-----------|----------------|---------------|
| `app/services/forcing_line_gate.py` | mod | service (pure predicate module) | transform | itself — `_is_forced_mate_firing` (`:289-305`), `_truncate_at_still_winning_floor` (`:~270-286`) | exact (self-analog) |
| `app/services/tactic_detector.py` | mod | service (pure predicate module) | transform | itself — `_clearance_prior_move_is_valid` (`:1968-1983`), `_capturing_defender_fires_at` loop (`:2175-2181`), `MIN_SACRIFICE_DROP` (`:80`), `_TIER3_REGISTRY` (`:2373-2383`) | exact (self-analog) |
| `app/services/flaws_service.py` | mod | service (orchestration) | request-response / transform | itself — `_classify_tactic_gated` (`:560-622`), `_solver_color_for` (`:543-558`), `_pov_mate` (`:215-220`) | exact (self-analog) |
| `scripts/retag_flaws.py` | mod | script (operator, offline batch) | batch + CRUD | itself — `_write_retag_report` (`:523+`), `_accumulate_motif_counts` (`:472-521`), `_worker_recompute` (`:285-338`) | exact (self-analog) |
| `scripts/tactic_tagger_report.py` | mod | script (analysis/report) | batch transform | itself — `_score` (`:192`), `_build_report` (`:241`), `GOALS` (`:115`) | exact (self-analog) |
| `scripts/research/oracle_compare.py` | new (moved) | script (analysis-only, no DB) | batch transform | `scripts/ab_validate_gate.py:1-48` (read-only harness header + import bootstrap) | role-match |
| `scripts/research/dev_probe.py` | new (moved) | script (analysis-only, read DB) | batch read | `scripts/ab_validate_gate.py` (`--db`, `db_url_for_target`, `create_async_engine`, `:947-948`, `:1030-1052`) | exact |
| `scripts/research/<sample_realgame_tags>.py` | new | script (operator, read-only sampler → CSV) | batch read → file-I/O | `scripts/ab_validate_gate.py` (read-only + `--db` + report writer); `scripts/opening_cache_repair.py:1-28` (operator docstring + required `--db` + `--dry-run`) | role-match |
| `fixtures/tagger/realgame_tags.csv` | new | fixture data | file-I/O | `fixtures/tagger/detector_fixture_train.csv` (header `PuzzleId,FEN,PreFlawFEN,FirstMove,PV,Themes,Rating`) | exact |
| `tests/scripts/tagger/conftest.py` | mod | test fixture/loader | file-I/O | itself — `PuzzleRow` + `_load_split` (`:39-70`), `build_detector_board` (`:72-95`) | exact (self-analog) |
| `tests/scripts/tagger/precision_floors.py` | mod | config/constants (measurement record) | — | itself — `SUPPRESSED_MOTIFS` (`:~200-247`), `PRECISION_FLOOR` (`:~295+`) | exact (self-analog) |
| `tests/scripts/tagger/test_detector_precision.py` | mod | test (harness gate) | batch transform | itself — `_compute_metrics` (`:70-115`), `test_detector_precision_and_recall` (`:221`) | exact (self-analog) |
| `tests/services/test_forcing_line_gate.py` | mod | test (pure unit) | transform | itself — `_cp_node`/`_mate_node`/`_only_move_node` (`:43-56`), `class TestConstants` (`:62-75`) | exact (self-analog) |
| `tests/services/test_tactic_detector.py` | mod | test (pure unit, fixture tables) | transform | itself — `_CLEARANCE_FIXTURES` (`:726`), `TestSacrificeCookAndChain` (`:2312`) | exact (self-analog) |
| `tests/services/test_flaws_service.py` | mod | test (async service unit) | request-response | itself — `TestClassifyTacticGated` (`:2676`), `TestClassifyTacticGatedBlobsPending` (`:2801-2897`), `test_missed_dest_sq_gate` (`:1966`) | exact (self-analog) |
| `tests/scripts/test_retag_flaws.py` | mod | test (script integration, dev DB) | batch + CRUD | itself — `test_dry_run_writes_report_file` (`:324-357`), `report_dir=tmp_path` injection (`:314`, `:344`, `:388`) | exact (self-analog) |
| `app/repositories/library_repository.py` (conditional) | mod | repository (constant map) | — | itself — `FAMILY_TO_MOTIF_INTS` (`:153-172`); precedent recorded in `precision_floors.py:200-221` | exact |
| `frontend/src/lib/tacticComparisonMeta.ts` + `tacticMotifDefinitions.ts` (conditional) | mod | frontend config/copy | — | the existing 4-site family pattern in `tacticComparisonMeta.ts` (`:117-123`, `:140`, `:172`, `:197`, `:380-387`) | exact |

**Match-quality note:** this phase has almost no greenfield. The dominant pattern instruction is
"clone the sibling function in the same file", not "copy a different module". Only three files are
genuinely new-shaped: the sampler script, the research-script relocation, and `realgame_tags.csv`.

---

## Pattern Assignments

### `app/services/forcing_line_gate.py` (service, transform) — TAGFIX-01

**Analog:** itself. Two sibling shapes to clone.

**1. Node-read helper pattern** (`forcing_line_gate.py:289-305` — read the blob node at the firing
index, convert to solver perspective, return a bool/scalar, nesting ≤ 2, docstring records the
degradation mode):

```python
def _is_forced_mate_firing(
    line: Sequence[PvNode],
    solver_color: Literal["white", "black"],
    firing_depth: int | None,
) -> bool:
    """Return True if the firing node delivers a forced mate for the solver (Phase 144).
    ...
    The firing node is at index firing_depth (the detector's tactic depth); None defaults
    to index 0 (mate motifs fire at depth 0 in practice).
    ...
    """
```

The new `_solver_cp_at_firing(...)` (RESEARCH § Implementation Map 1) is its direct sibling:
same parameter order (`line, solver_color, firing_depth`), same bounds guard, same
one-rule-one-function posture declared in the module docstring (`:47-49`: "No I/O, no DB,
stdlib + eval_utils only… unit-testable in isolation").

**2. Solver-perspective conversion** — do NOT invent a new sign convention. The module already
uses exactly one form (`:271`, `:282`, `:355`):

```python
            if bm is None and b is not None:
                # Non-mate: convert to solver-perspective and check floor.
                solver_cp = b if solver_color == "white" else -b
                if solver_cp < STILL_WINNING_FLOOR_CP:
                    break  # Conversion has fizzled; exclude this node and stop.
```

and for mates, `eval_mate_to_expected_score(bm, solver_color) == 1.0`.

**3. Named-constant provenance comment style** (`:64-80` — this is the house style for the two new
tier floors and the depth cap; multi-paragraph, names the upstream source, names the measurement
that set the value, links the report):

```python
# D-08: reject the whole motif if the pre-flaw position was already winning by a large
# margin from the solver's perspective (lichess-puzzler already-winning reject). Phase 144
# raised this from 300 to 600 cp, then to 800 cp in the VALID-02 A/B sweep: FlawChess tags
# real-game tactics (not puzzles)... See reports/retag/ab-validation-2026-06-30.md.
ALREADY_WINNING_CP_THRESHOLD: int = 800

# D-09: stop extending the line at the first solver node whose best-move eval drops
# below +200 cp from the solver's perspective (lichess-puzzler cook_advantage Cp(200)).
STILL_WINNING_FLOOR_CP: int = 200
```

**4. Orchestrator pattern** (`:427-470`) — `apply_forcing_line_filter` is a FLAT sequence of
`# D-0x:` commented steps, each one line of logic delegating to a helper. The new floor check
must be one such step (`if not forced_mate and not _passes_winning_floor(...): return False`),
with the logic inside the helper. Nesting in the orchestrator stays at 1.

**5. New keyword parameter, appended last, defaulted** — the existing `firing_depth`/`margin`
params show the shape and the docstring Args style; `motif_int: int | None = None` goes after
`margin` so the ~50 existing call sites keep compiling (RESEARCH § Primary recommendation).

---

### `app/services/tactic_detector.py` (service, transform) — TAGFIX-03/-04/-05, floor map

**Analog:** itself.

**1. Predicate constant with cook provenance** (`:76-80` — clone for
`SACRIFICE_CLEARANCE_MAX_DEPTH` and the tier-floor constants; cite the cook section AND the
review that motivated the divergence):

```python
# Minimum material-point drop below the starting position that constitutes a sacrifice.
# Cook §7: sacrifice fires when pov is down ≥2 points vs start AFTER at least the 2nd pov move.
# 2 = minor piece (bishop/knight) threshold — queens (9) and rooks (5) are always >= 2.
MIN_SACRIFICE_DROP: int = 2
```

**2. Extracted-clause helper pattern** (`:1968-1983` — the precedent for keeping
`detect_clearance` under the depth-4 hard cap; module-level, takes only the locals it needs,
docstring names the cook condition numbers it implements):

```python
def _clearance_prior_move_is_valid(prev_move: chess.Move, move: chess.Move) -> bool:
    """Conditions 3-5: the prior pov move must be eligible to have set up this clearance.

    Not a promotion, and its destination square doesn't collide with either endpoint
    of the clearing move ...
    """
    if prev_move.promotion is not None:
        return False
    if prev_move.to_square == move.from_square:
        return False
    if prev_move.to_square == move.to_square:
        return False
    return True
```

Copy this exact shape for D-07's `_clearance_line_is_used(board_after, dest, pov) -> bool` and the
"attacks a higher-value or hanging piece" clause (reuse `_is_defended` `:291-316`,
`_PIECE_VALUES` `:45-57`, `_VALUES_NO_KING` `:59-66` — do not hand-roll a new attackers check).

**3. Even-k scan loop + index-convention docstring** (`detect_sacrifice`, `:2183-2213`) — the
function D-05/D-06 edits, and the canonical loop shape for the depth cap:

```python
    # Promotion guard (Pitfall 7): check OPPONENT moves (odd indices), not pov moves.
    if any(m.promotion for m in moves[1::2]):
        return False, None, 0, None

    initial = _material_diff(boards[0], pov)

    # Scan from the 2nd pov move onward (k=2, 4, 6, ...): cook scans diffs[1::2][1:].
    for k in range(2, len(moves), 2):
        if k + 1 >= len(boards):
            break
        diff_after = _material_diff(boards[k + 1], pov)
        if diff_after - initial <= -MIN_SACRIFICE_DROP:
            return True, None, TACTIC_CONFIDENCE_HIGH, k

    return False, None, 0, None
```

`detect_clearance`'s docstring (`:1996-2009`) carries the full **Index convention** block
(`moves[k]` / `boards[k]` / `boards[k+1]` …). D-05's `boards[k+3]` check must extend that block in
the sacrifice docstring the same way — this is how the repo keeps the cook↔ours index mapping
auditable.

**4. Registry-tuple pattern + tier→floor map placement** (`:2352-2418`). Registries are
`list[tuple[TacticMotif, int]]` with a per-line rank comment; the comment block above each
registry explains the dominance rationale:

```python
_TIER3_REGISTRY: list[tuple[TacticMotif, int]] = [
    ("deflection", TacticMotifInt.DEFLECTION),
    ...
    ("self-interference", TacticMotifInt.SELF_INTERFERENCE),   # ← D-12 removes this tuple only
    ("clearance", TacticMotifInt.CLEARANCE),
    ("capturing-defender", TacticMotifInt.CAPTURING_DEFENDER),
    ("sacrifice", TacticMotifInt.SACRIFICE),
]
```

D-01's floor map goes immediately after `_MOVE_TYPE_REGISTRY` (`:2408-2412`) and should be
**derived from** these registries (plus `MATE_MOTIFS`) rather than re-listing motif names, so it
cannot drift. Expose one public reader, `floor_cp_for_motif(motif_int: int) -> int | None`, for the
gate to import (direction `gate → detector` is cycle-free; RESEARCH § Where the tier→floor map
lives).

**5. Bug-fix comment discipline (CLAUDE.md)** — each of the seven port fixes replaces a commented
wrong line; the comment must be rewritten, e.g. the obsolete WR-02 block at `:886-892` and the
trapped-piece exclusion comment at `:951-954` (`# Empty-escape-set exclusion (D-06
precision-first): no moves → not trapped.`) must go with the code, not be left describing removed
behaviour. Note the matching stale paragraph in `forcing_line_gate.py:299-305` (the slim-blob
odd-firing-depth note that exists only because of the DA k−1 quirk).

---

### `app/services/flaws_service.py` (service, orchestration) — TAGFIX-02/-06

**Analog:** itself.

**1. The gate-skip conjunct to change** (`:604-616` — verbatim; line 609 is TAGFIX-02's target,
and line 618 must keep its `blobs_pending` semantics):

```python
    if (
        motif is not None
        and pv_blob is not None
        and len(pv_blob) > 0
        and pre_flaw_eval_cp is not None
    ):
        solver_color = _solver_color_for(n, orientation)
        # Bug B: pass the detected firing depth so only the solver nodes up to the
        # tactic's firing point need be forced (the conversion tail is exempt).
        if not apply_forcing_line_filter(
            pv_blob, solver_color, pre_flaw_eval_cp, firing_depth=depth, margin=margin
        ):
            return None, None, None, None
    if blobs_pending and motif is not None and pv_blob is None and pre_flaw_eval_cp is not None:
        return None, None, None, None
    return motif, piece, conf, depth
```

**2. Sentinel-documenting docstring pattern** (`:570-602`) — `_classify_tactic_gated`'s docstring
enumerates every input sentinel and its outcome (`pv_blob is None`, `[]`, `blobs_pending`,
`pre_flaw_eval_cp is None`). TAGFIX-02 **rewrites** the "gate is likewise skipped when
pre_flaw_eval_cp is None" paragraph; the `[]` and `blobs_pending` paragraphs must survive
verbatim in meaning. This docstring is the contract the 4 `TestClassifyTacticGatedBlobsPending`
tests pin.

**3. Perspective helpers to reuse, not re-derive** (`:215-220`, `:543-558`):

```python
def _solver_color_for(n: int, orientation: Literal["allowed", "missed"]) -> Literal["white", "black"]:
    if orientation == "allowed":
        return "black" if n % 2 == 0 else "white"
    return "white" if n % 2 == 0 else "black"
```

`_pov_mate(pos, mover_color)` is the only sanctioned `eval_mate` sign conversion in the file — D-04's
already-winning-by-mate reject and D-03's `game_positions` fallback must both go through it.

**4. Board-construction site + its defense-in-depth comment** (`:461-472` — TAGFIX-06 edits here;
keep the `turn` override and re-assert it after the push):

```python
    fen_before_flaw = fen_map.get(n, "")
    if not fen_before_flaw:
        return None, None, None, None

    # fen_map now stores the full board.fen() (Phase 148 D-02) ... This
    # explicit override is redundant ... but harmless, and is kept as a defense-in-depth guard
    # against a partial/legacy fen_map entry — not required for correctness.
    board_before = chess.Board(fen_before_flaw)
    board_before.turn = chess.WHITE if n % 2 == 0 else chess.BLACK
```

**5. SAN-parse guard pattern** — the file's established form is
`try: ... except (ValueError, chess.IllegalMoveError): pass` with a comment naming the pitfall
(see the docstring notes at `:455-458`). D-09's push must use it and fall back to the stackless
build, never raise.

**6. Function-size mitigation** — extract `_gate_eval_inputs(n, orientation, positions) -> (cp, mate)`
(RESEARCH § Function-Size Headroom) rather than growing `_classify_tactic_gated`'s branch count.

---

### `scripts/retag_flaws.py` (script, batch + CRUD) — TAGFIX-09

**Analog:** itself.

**1. Sparse positions build to fix** (`:305-315`) — `positions[ply-1] = work.prv` must be added
here (guarded on `ply >= 1`) or the retag drifts from the live path:

```python
    positions: list[Any] = [_EMPTY_POS] * (ply + 2)
    if work.cur is not None:
        positions[ply] = work.cur
    if work.nxt is not None:
        positions[ply + 1] = work.nxt
    # fen_map only needs the flaw's own ply — the kernel reads fen_map.get(ply).
    fen_map = {ply: work.fen}
    pre_flaw_eval_cp = work.prv.eval_cp if work.prv is not None else None
```

Note the docstring above it (`:286-303`) explains the sparse-list contract and the Bug-A history —
extend that docstring in the same voice when `ply-1` is filled.

**2. Counter-accumulator pattern for the new "shifted" bucket** (`:472-521`) — the function takes
one `Counter[str]` per bucket per orientation, decodes ints via `TacticMotifInt(...).name` in a
`try/except ValueError`, and documents the `old_tuple` column layout in the docstring:

```python
        old_allowed_motif: int | None = old_tuple[0]  # type: ignore[assignment]
        if old_allowed_motif is not None:
            try:
                name = TacticMotifInt(old_allowed_motif).name
            except ValueError:
                name = str(old_allowed_motif)
            new_allowed_motif: int | None = effective_new[0]  # type: ignore[assignment]
            if new_allowed_motif is None:
                motif_removed_allowed[name] += 1
            else:
                motif_survived_allowed[name] += 1
```

Add `motif_shifted_*` Counters in exactly this shape (`old is not None and new is not None and
old != new`), plus a depth-shift counter for the odd-depth acceptance claim.

**3. Report writer with injectable `report_dir`** (`:523-560`) — the pattern that makes the report
testable; note the docstring's "Called only when --dry-run is active" line, which TAGFIX-09 must
update when the report is also written on the writing run:

```python
        report_dir: Output directory for the report. Defaults to the committed
            reports/retag/ path. Tests inject a tmp dir so the suite never writes
            into the version-controlled tree. The directory is created if missing.
    ...
    if report_dir is None:
        report_dir = Path(__file__).resolve().parent.parent / "reports" / "retag"
    report_path = report_dir / f"retag-{date_str}.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
```

**4. Argparse style** (`:172-250`) — `--db` is `choices=["dev","benchmark","prod"], required=True`,
every help string states the port/tunnel or the operational consequence; `dest=` is spelled out
for hyphenated flags. The stale `--db prod` read-only claim in the module docstring (`:74-76`) is
a doc fix in this file.

---

### `scripts/tactic_tagger_report.py` + `tests/scripts/tagger/*` (harness) — TAGFIX-07

**Analog:** the existing CC0 harness. The real-game table slots in beside it, sharing the
build-board → detect → decode shape but with **different bucket semantics** (no FNs).

**1. Fixture loader pattern** (`tests/scripts/tagger/conftest.py:33-70`) — clone for the real-game
CSV: a `TypedDict` row with per-field comments, a module-level path constant under
`_FIXTURE_DIR`, a `csv.DictReader` loader, and a session-scoped pytest fixture:

```python
_FIXTURE_DIR = Path(__file__).resolve().parents[3] / "fixtures" / "tagger"
_FIXTURE_PATHS: dict[Split, Path] = {
    "train": _FIXTURE_DIR / "detector_fixture_train.csv",
    ...
}

class PuzzleRow(TypedDict):
    """A single row from a committed fixture CSV."""
    puzzle_id: str
    fen: str  # board-after-flaw FEN (Moves[0] already applied)
    pre_flaw_fen: str  # published pre-blunder FEN (cook's game.board())
    first_move: str  # UCI string: the blunder that created the puzzle position
    pv: str  # space-joined UCI refutation moves (Moves[1:])
    ...

def _load_split(split: Split) -> list[PuzzleRow]:
    """Read a committed fixture CSV ('train' or 'test'). No DB, no network."""
    with open(_FIXTURE_PATHS[split], newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
```

`RealGameRow`'s `label` field is `Literal["real", "incidental", "wrong"]` (CLAUDE.md: never bare
`str` for a fixed set); `orientation` is `Literal["allowed", "missed"]`.

**2. Production-identical board build — mandatory** (`conftest.py:72-95`). Do not call
`chess.Board(fen)` in the new loader/scorer; this helper *is* the pattern (and its docstring is the
prose justification for TAGFIX-06):

```python
def build_detector_board(row: PuzzleRow) -> chess.Board:
    """Build the detector input board the SAME way production calls it. ..."""
    pre = row["pre_flaw_fen"]
    first_move = row["first_move"]
    if pre and first_move:
        try:
            board = chess.Board(pre)
            board.push(chess.Move.from_uci(first_move))
            return board
        except ValueError, chess.IllegalMoveError, AssertionError:
            pass
    return chess.Board(row["fen"])
```

(Note the bare-tuple `except A, B:` form — valid here per RESEARCH Pitfall 8; match the file.)

**3. Scoring-loop pattern** (`test_detector_precision.py:70-115`) — build board, `detect_tactic_motif`,
decode via `_INT_TO_MOTIF`, then bucket per motif with `defaultdict(int)`:

```python
    for row in rows:
        # Build the board the SAME way production calls the detector (flaw move on the move
        # stack), so the floor gate verifies the detector identically to production.
        board = build_detector_board(row)
        motif_int, _piece, _confidence, depth = detect_tactic_motif(board, row["pv"])
        detected_motif = _INT_TO_MOTIF.get(motif_int) if motif_int is not None else None
```

For the real-game table the buckets are `real_surviving / surviving / suppressed` — **do not reuse
the `fn_count` branch**; a suppressed incidental row is a win, not a miss (RESEARCH § The scoring
seam).

**4. Floor-constant + measurement-record pattern** (`precision_floors.py`) — every floor carries a
trailing comment with the measured train/test numbers and the change that produced them:

```python
    "clearance": 0.93,  # train 1.000 / test 1.000 (388 TP, 0 FP; cook condition-7 board fix)
    "intermezzo": 0.92,  # train 1.000 / test 1.000 (457 TP, 0 FP; cook control-flow + k=2 fix)
```

`REALGAME_REAL_SHARE_FLOOR: dict[str, float]` goes beside `PRECISION_FLOOR` in this exact style.
`SUPPRESSED_MOTIFS` is a `frozenset[str]` whose membership changes are recorded as dated inline
comments *inside the set body* rather than deleted lines — reuse that for D-07's possible
`"clearance"` addition, and for TAGFIX-08's two new docstring blocks.

**5. New test function, not an extended one** — `test_detector_precision_and_recall` (`:221`) keeps
its single responsibility; add `test_realgame_real_share_floor` alongside. Table-printing helper
`_print_set_table` (`:132-175`) shows the suppressed/floor/status column convention to mirror.

**6. CSV header** — `fixtures/tagger/detector_fixture_train.csv` line 1 is the analog:
`PuzzleId,FEN,PreFlawFEN,FirstMove,PV,Themes,Rating`. The new file's recommended header is
`row_id,game_id,ply,orientation,pre_flaw_fen,push_move_uci,pv,motif,depth,solver_color,eval_at_firing,label,rationale`
(RESEARCH § TAGFIX-07) — same flat, quoted-FEN, space-joined-UCI-PV conventions.

---

### `scripts/research/*.py` (script, analysis-only) — TAGFIX-08

**Analog:** `scripts/ab_validate_gate.py:1-48` — the repo's read-only, engine-free analysis-script
header, which is exactly the posture the two relocated scripts must adopt to survive
`ruff check .` / `ty check scripts/` (39 ruff + 2 ty findings measured as-is):

```python
"""Engine-free A/B gate-validation harness for Phase 144 (VALID-01, VALID-02).

Read-only: performs ZERO DB writes — no commits, no UPDATE statements.
Engine-free: zero Stockfish calls, no chess engine instantiation of any kind.
...
AGPL boundary: gate heuristics, constants, and names only — copy NO lichess-puzzler source.
See forcing_line_gate.py for the full boundary comment.

Usage:
    uv run python scripts/ab_validate_gate.py --db dev
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
...
# Bootstrap project root so `app.*` imports resolve when running as a script.
```

Concrete deltas the relocation needs, all visible by diffing against this analog: `from __future__
import annotations`; one import per line (no `import sys, json, collections`); `# noqa: E402`
on post-`sys.path` imports; `# ty: ignore[unresolved-import]` **with a reason** on `import cook` /
`from model import Puzzle`; explicit return annotations on every function; and a clean
`raise SystemExit(0)` when the AGPL clone is absent (TAGFIX-08's "skip cleanly").

**DB connection pattern for `dev_probe.py` and the sampler** (`ab_validate_gate.py:43-48`, `:947-948`):

```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.config import db_url_for_target, settings  # noqa: E402
...
        url = db_url_for_target(db)
        engine = create_async_engine(url, pool_pre_ping=True)
```

One session, sequential queries (never `asyncio.gather` on one `AsyncSession`).

**Operator-script docstring for the sampler** — `scripts/opening_cache_repair.py:1-28` is the
Phase-220 precedent for a prod-touching operator surface: what it does, why the `--db` target is
required, and a literal `Usage:` block:

```python
"""Phase 220 opening eval cache repair pipeline operator surface (SEED-164, CACHEFIX-01..07).
...
The --db target is REQUIRED so this never silently runs against the wrong
database. dev=localhost:5432, benchmark=localhost:5433, prod=localhost:15432
(via bin/prod_db_tunnel.sh).

Usage:
    uv run python scripts/opening_cache_repair.py seed --db dev
    uv run python scripts/opening_cache_repair.py seed --db prod --dry-run
    uv run python scripts/opening_cache_repair.py screen --db dev --limit 100
"""
```

The sampler is read-only, so it needs `--db` + `--limit` + an output path, not `--dry-run`.

---

### Test files (`tests/services/*`, `tests/scripts/test_retag_flaws.py`)

**`tests/services/test_forcing_line_gate.py`** — analog is its own header (`:1-56`). Reuse the
existing blob builders rather than writing new dict literals; add `class TestWinningFloorAtFiring`
with the same `# ---` banner-comment + docstring-per-test convention, and pin the new constants in
`TestConstants` (`:62-75`):

```python
def _cp_node(b: int, s: int | None = None) -> PvNode:
    """Construct a centipawn-only PvNode (white-perspective)."""
    return PvNode(b=b, bm=None, s=s, sm=None, su="e2e4" if s is not None else "")

def _mate_node(bm: int, sm: int | None = None) -> PvNode:
    """Construct a mate PvNode (white-perspective, positive = white mating)."""
    return PvNode(b=None, bm=bm, s=None, sm=sm, su="e2e4" if sm is not None else "")
```

The module docstring's closing line is the property to preserve: "This module is intentionally
free of database sessions, async fixtures, and Stockfish worker processes -- their absence IS the
Phase 141 success criterion #2 guarantee."

**`tests/services/test_tactic_detector.py`** — clearance/sacrifice negatives go into the existing
fixture-table + parametrize pattern (`_CLEARANCE_FIXTURES` at `:726`, `TestSacrificeCookAndChain`
at `:2312`). CONTEXT's worked examples (`Na6+ Ka8 [Qc7]` fire; `Kh1→g2 … [Rh1]` reject) become
rows in those tables.

**`tests/services/test_flaws_service.py`** — new `TestMissedOrientationParity` sits near
`test_missed_dest_sq_gate` (`:1966`); the TAGFIX-06 move-stack assertions MUST live here, not in
`test_tactic_detector.py` (Pitfall 3: a detector-level test cannot see the production board
build). The 4 `TestClassifyTacticGatedBlobsPending` tests (`:2801-2897`) stay **unmodified** — that
is the regression signal for TAGFIX-02.

**`tests/scripts/test_retag_flaws.py`** — clone `test_dry_run_writes_report_file` (`:324-357`) for
the non-dry-run report and the "shifted" column. The load-bearing pattern is the injected
`report_dir=tmp_path` plus content assertions on section headings:

```python
        await run_backfill(
            db="dev", user_id=user_id, only_tagged=False, dry_run=True, limit=None,
            workers=1, margin=ONLY_MOVE_WIN_PROB_MARGIN,
            session_maker=session_factory, report_dir=tmp_path,
        )
        report_files = list(tmp_path.glob("retag-*.md"))
        assert len(report_files) >= 1, f"Expected a retag report in {tmp_path}, found none"
        latest = max(report_files, key=lambda p: p.stat().st_mtime)
        content = latest.read_text()
        assert "Allowed-orientation tag changes" in content, "Report missing allowed table"
```

Note `session_maker=` / `report_dir=` are the two injection seams that keep this suite off the
committed tree and on the per-session cloned dev DB.

---

## Shared Patterns

### Named constants with provenance
**Source:** `app/services/forcing_line_gate.py:57-92`; `app/services/tactic_detector.py:76-80`
**Apply to:** the two tier floors, `SACRIFICE_CLEARANCE_MAX_DEPTH`, the clearance value delta, and
every new floor in `precision_floors.py`.
Rule: module-level, annotated (`: int` / `: float`), with a comment naming (a) the upstream source
(cook §N / lichess-puzzler constant), (b) the measurement or report that set the value, (c) why the
previous value changed. Never a bare literal in a conditional.

### Solver/mover perspective conversion
**Source:** `forcing_line_gate.py:282` (`cp if solver_color == "white" else -cp`);
`flaws_service.py:215-220` (`_pov_mate`); `flaws_service.py:543-558` (`_solver_color_for`)
**Apply to:** the firing-node floor read, the D-03 `game_positions` fallback, the D-04 mate-derived
already-winning reject.
Rule: the gate module is the single source of eval-sign truth for blob nodes; `_pov_mate` is the
single converter for `GamePosition.eval_mate`. Inventing a third sign path is the known bug class
(Phase 148 CR-01, memory `project_eval_cp_post_move_sampler_defect`).

### One-rule-one-function, nesting ≤ 3
**Source:** `forcing_line_gate.py:86-89` banner ("Private predicate helpers — each rule is its own
small function (CLAUDE.md function-size discipline; nesting hard-cap 4)");
`tactic_detector.py:1968` (`_clearance_prior_move_is_valid`)
**Apply to:** every new clause in `detect_clearance`, the gate floor, `_gate_eval_inputs`.
Verify with `uv run python scripts/check_function_size.py app/ --fail-over-depth 4 --fail-over-loc 200`
(currently **zero breaches** across 705 app functions, so any breach is attributable to this phase).

### Cook index-convention docstring block
**Source:** `tactic_detector.py:1996-2009` (`detect_clearance`) and `:2192-2198` (`detect_sacrifice`)
**Apply to:** any detector loop change (D-05's `boards[k+3]`, D-11's depth `k`).
Rule: state `moves[k]` / `boards[k]` / `boards[k+1]` meanings in the docstring before editing the
loop; cross-check `.planning/notes/tactic-tagger-cook-alignment.md`.

### Injectable output/IO seams in scripts
**Source:** `scripts/retag_flaws.py:523-552` (`report_dir: Path | None = None`) consumed by
`tests/scripts/test_retag_flaws.py:314`
**Apply to:** the retag report change and the new sampler script (CSV output path must be
parameterised so a test or a re-run cannot clobber the committed fixture).

### Required `--db` operator CLI
**Source:** `scripts/retag_flaws.py:180-185`; `scripts/opening_cache_repair.py:18-28`
**Apply to:** the sampler and `dev_probe.py`.
Rule: `choices=["dev","benchmark","prod"], required=True`; help text names the port/tunnel; prod =
`localhost:15432` via `bin/prod_db_tunnel.sh`; resolve the URL with `db_url_for_target()`, never a
hand-built DSN.

### AGPL boundary comment
**Source:** `forcing_line_gate.py:~30-50` (referenced by every port site);
`tests/scripts/tagger/conftest.py:15-19`; `test_detector_precision.py:25-31`
**Apply to:** all seven port fixes, `scripts/research/oracle_compare.py`, and the new CSV loader.
Rule: state that only prose/heuristics/constant *names* cross the boundary and that cook.py is
neither vendered nor ported; keep the CC0-data claim attached to any fixture file.

### Bug-fix comment at the fix site
**Source:** `flaws_service.py:496-503` (the "Bug fix (Phase 148 code review CR-01)" block);
`retag_flaws.py:296-303` (the Bug-A `pre_flaw_eval_cp` note)
**Apply to:** all seven port fixes and the TAGFIX-01/-02 gate changes — and **delete/rewrite** the
comments describing the removed behaviour (`tactic_detector.py:886-892` WR-02,
`:951-954` empty-escape, `forcing_line_gate.py:299-305` slim-blob odd-depth,
`retag_flaws.py:74-76` tunnel-is-read-only).

---

## No Analog Found

None. Every file in scope has a tracked in-repo analog (usually itself).

Two items are analog-*shaped* but semantically new, and the planner should say so explicitly so an
executor does not copy the wrong semantics:

| File | Role | Data Flow | Caveat |
|------|------|-----------|--------|
| `fixtures/tagger/realgame_tags.csv` + its scorer | fixture / harness | file-I/O → transform | Shape copies `detector_fixture_train.csv` + `_compute_metrics`, but the **bucket semantics differ**: `real_surviving / surviving / suppressed`, no FN column. Reusing the puzzle harness's FN branch reads backwards (a suppressed incidental row is a win). |
| `scripts/research/<sampler>.py` | script | batch read → CSV | No existing script writes a *committed fixture* from prod. Closest analogs write reports under `reports/`. Frozen-before-the-fix sampling (D-13) is a new operational property: the CSV must be committed before any detector edit lands. |

---

## Metadata

**Analog search scope:** `app/services/`, `app/repositories/`, `scripts/`, `tests/services/`,
`tests/scripts/`, `tests/scripts/tagger/`, `fixtures/tagger/`, `frontend/src/lib/`
**Files read this session:** 12 (targeted, non-overlapping ranges)
**Tracked-source verification:** `git ls-files` confirmed for every analog path named above
**Pattern extraction date:** 2026-09-12
