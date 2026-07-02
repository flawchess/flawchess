# Phase 144: User-28 A/B Validation - Research

**Researched:** 2026-06-30
**Domain:** Python scripting — engine-free tactic-gate A/B harness + committed-markdown report
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01:** Accept the 216 existing blob-bearing dev-28 flaws as-is (100 allowed-tagged + 71
missed-tagged). No engine work. Report per-motif counts with explicit small-N caveats.

**D-01a:** dev-28 only. prod-28 is NOT pulled in as a reference in this phase.

**D-02:** Dedicated `scripts/ab_validate_gate.py` (not an extension of `retag_flaws.py`). Loads
216 blobs + flaw-ply `eval_cp` once, runs tactic-detection kernel twice over same stored inputs
(ungated vs gated-at-margin), in-memory, no DB writes.

**D-02a:** The "old" arm is genuinely ungated, not `--margin 0`. `margin=0` still applies the
mate hierarchy, already-winning reject (>300 cp), and one-mover discard — NOT the pre-gate
baseline. The harness must run detection with `apply_forcing_line_filter` bypassed entirely.

**D-03:** Keep the provisional 0.35 unless the hand-check shows it fails. Optionally generate
the table at 0.30/0.35/0.40 for context. Default committed value stays 0.35 unless hand-check
reveals it is clearly killing good tags or leaving obvious noise.

**D-03a:** VALID-02 SC4 ("final margin committed") is satisfied by confirming 0.35 + A/B
summary justification — if 0.35 is confirmed, no constant change is needed. Only change the
value if the hand-check fails 0.35.

**D-04:** Surface dropped cases as committed `reports/retag/` markdown: each case = motif, FEN,
the PV / refutation line, and a lichess analysis deep-link for in-browser adjudication.
User marks each false negative vs correct drop; FN count folds into A/B summary.

**D-04a:** Hand-check ALL dropped cases when the count is ≤30. Fall back to motif-stratified
~30 only if the gate drops more than ~30.

### Claude's Discretion

Exact `ab_validate_gate.py` CLI flags and function signatures; the precise per-motif/depth
table shape and `reports/retag/` filename (suggest `reports/retag/ab-validation-YYYY-MM-DD.md`);
the lichess deep-link URL format; how the ungated arm reuses the detection kernel (a `gate=False`
param on `_classify_tactic_gated` vs a thin ungated wrapper); whether the small neighbourhood
sweep (0.30/0.40) is included for context. Planner/executor decide within the decisions above.

### Deferred Ideas (OUT OF SCOPE)

- Enlarging the dev blob sample via a fresh engine pass / `backfill_multipv.py` — Phase 145.
- prod-28 as a larger descriptive sanity reference — not opted into this phase.
- Corpus backfill + rollout + before/after per-motif chip-count monitoring — Phase 145.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| VALID-01 | A user-28 dev A/B runs old and new tagger logic against the same stored MultiPV evals (engine-free), isolating the gate's effect from `eval_cp` cross-machine non-determinism; prod-28 is sanity-only | §Standard Stack, §Architecture Patterns (query shape, blob loading, ungated arm mechanism) |
| VALID-02 | A/B measures noise removed and good tags killed — per-motif removed/survived, depth-shift distribution, hand-check of dropped cases with explicit false-negative count — and final margin committed | §Architecture Patterns (report convention, depth-shift definition, dropped-case surface), §Code Examples |
</phase_requirements>

---

## Summary

Phase 144 is a single-purpose read-only validation script (`scripts/ab_validate_gate.py`) that
loads user-28's 216 MultiPV-blob-bearing flaws from the dev DB once, runs tactic detection twice
over the same stored inputs (ungated vs gated at the test margin), diffs the results, and emits
a committed markdown report to `reports/retag/`. No engine, no writes.

The central code question — resolved by reading the load-bearing files — is how to construct
the ungated arm. The correct approach is to call `_detect_tactic_for_flaw` directly from
`app/services/flaws_service.py`, bypassing `_classify_tactic_gated` and thus never invoking
`apply_forcing_line_filter`. This is option (b) from the CONTEXT's Claude's Discretion items:
a thin ungated wrapper, no production code changes.

The gated arm calls `_classify_tactic_gated` at the test margin exactly as `retag_flaws.py`
does, reusing the established SC4 single-classify-path posture. The blob-loading query
(from `retag_flaws.py`'s `_fetch_flaw_page`) is borrowed verbatim and simplified: at 216 rows
a single non-paginated query suffices instead of keyset pagination.

**Primary recommendation:** Build `ab_validate_gate.py` as a standalone, DB-read-only script.
Ungated arm = `_detect_tactic_for_flaw` directly. Gated arm = `_classify_tactic_gated` at
the test margin. Dropped cases rendered with lichess deep-links for human adjudication.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Blob loading | DB (read-only query) | — | `game_flaws.allowed_pv_lines` / `missed_pv_lines` JSONB + `game_positions.eval_cp` are persisted data, read via SQLAlchemy async |
| Tactic detection (both arms) | Python in-process | — | Pure CPU kernel (`_detect_tactic_for_flaw`); no engine, no DB writes |
| Gate logic | Python in-process | — | `apply_forcing_line_filter` / `is_solver_node_forced` are pure-math functions (no I/O) |
| Report writing | Filesystem | — | Committed markdown to `reports/retag/ab-validation-YYYY-MM-DD.md` |
| Hand-check adjudication | Human | — | HUMAN-UAT gate; false-negative judgment requires chess knowledge |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy async | 2.x (project) | Async DB access for blob loading | Established project ORM; `async_sessionmaker` pattern is used by `retag_flaws.py` |
| asyncpg | project | PostgreSQL async driver; auto-deserializes JSONB to `list[dict]` | Already wired in project; no manual JSONB setup needed |
| python-chess | 1.11.x (project) | Board reconstruction for FEN/PV manipulation | Used by `_detect_tactic_for_flaw`; transitive dep |
| argparse | stdlib | CLI flags | Established pattern in all scripts/ |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| collections.Counter | stdlib | Per-motif removed/survived counts | Same pattern as `retag_flaws.py`'s motif counters |
| pathlib.Path | stdlib | Report output path construction | Same as `_write_retag_report` |
| urllib.parse.quote | stdlib | FEN URL-encoding for lichess deep-links | Encode spaces in FEN for URL |

No new packages. The A/B script is a pure composition of existing project internals.

## Package Legitimacy Audit

No external packages are installed in this phase. All dependencies are project-internal
(SQLAlchemy, asyncpg, python-chess already in `pyproject.toml`) or stdlib.

**Packages removed due to SLOP verdict:** none
**Packages flagged as suspicious:** none

## Architecture Patterns

### System Architecture Diagram

```
dev DB (read-only)
        |
        | SELECT user_id=28, allowed/missed_pv_lines IS NOT NULL
        v
[Load 216 flaws: ply, fen, 8 tactic cols, allowed_pv_lines, missed_pv_lines]
        |
        | SELECT positions (ply, ply+1) for each flaw
        v
[pos_by_key: (user_id, game_id, ply) -> _PosRow(move_san, pv, eval_mate, eval_cp)]
        |
        +------------------------------------+
        |                                    |
   [Ungated arm]                        [Gated arm]
   _detect_tactic_for_flaw(...)         _classify_tactic_gated(...)
   (no apply_forcing_line_filter)       (apply_forcing_line_filter at margin)
        |                                    |
        +------------ diff ---- per-flaw ----+
                         |
          +--------------+--------------+
          |                             |
   [Removed tags]               [Survived tags]
   motif, fen, pv line          motif, depth (for depth-shift)
   lichess deep-link
          |
          v
   reports/retag/ab-validation-YYYY-MM-DD.md
   (+ ONLY_MOVE_WIN_PROB_MARGIN comment in forcing_line_gate.py)
```

### Recommended Project Structure

No new folders. The script follows established conventions:

```
scripts/
└── ab_validate_gate.py   # new: A/B harness (read-only, write-free)
reports/retag/
├── .gitkeep              # already exists
└── ab-validation-2026-MM-DD.md   # new: committed report output
app/services/
└── forcing_line_gate.py  # ONLY_MOVE_WIN_PROB_MARGIN updated comment at line 52
tests/scripts/
└── test_ab_validate_gate.py   # new: unit + integration tests
```

### Pattern 1: Ungated Arm (Option B — Recommended)

**What:** Call `_detect_tactic_for_flaw` directly, bypassing `_classify_tactic_gated` entirely.
This is the pre-143 detection path with no gate logic invoked.

**When to use:** The "old arm" in the A/B comparison.

**Why option (b) over option (a):**
- No production code changes. `_classify_tactic_gated` remains unmodified.
- The A/B script is a standalone validation tool; coupling a `gate=False` param into the
  production classify path for a one-off validation would violate separation of concerns.
- The pattern of importing `_`-prefixed functions from `flaws_service.py` is already
  established: `retag_flaws.py` imports `_classify_tactic_gated` (also `_`-prefixed).
- `_detect_tactic_for_flaw` is the exact kernel that `_classify_tactic_gated` wraps.
  Calling it directly is minimal and faithful.

```python
# Source: app/services/flaws_service.py line 406-412
# Ungated arm — genuinely pre-143, no gate invoked
from app.services.flaws_service import _detect_tactic_for_flaw

# Build minimal positions list (same pattern as retag_flaws.py _worker_recompute):
positions: list[Any] = [_EMPTY_POS] * (ply + 2)
if cur is not None:
    positions[ply] = cur
if nxt is not None:
    positions[ply + 1] = nxt
fen_map = {ply: flaw_fen}

ungated_allowed = _detect_tactic_for_flaw(ply, fen_map, positions, None, "allowed")
ungated_missed  = _detect_tactic_for_flaw(ply, fen_map, positions, None, "missed")
```

### Pattern 2: Gated Arm

**What:** Call `_classify_tactic_gated` at the test margin. This is identical to
`retag_flaws.py`'s `_worker_recompute`, reusing the SC4 single-classify-path guarantee.

```python
# Source: app/services/flaws_service.py line 525-560
# and scripts/retag_flaws.py _worker_recompute
from app.services.flaws_service import _classify_tactic_gated

gated_allowed = _classify_tactic_gated(
    ply, fen_map, positions,
    orientation="allowed",
    pv_blob=allowed_pv_blob,          # from game_flaws.allowed_pv_lines JSONB
    pre_flaw_eval_cp=pre_flaw_eval_cp, # from positions[ply].eval_cp (white-perspective)
    margin=test_margin,               # default: ONLY_MOVE_WIN_PROB_MARGIN = 0.35
)
gated_missed = _classify_tactic_gated(
    ply, fen_map, positions,
    orientation="missed",
    pv_blob=missed_pv_blob,
    pre_flaw_eval_cp=pre_flaw_eval_cp,
    margin=test_margin,
)
```

**Gate bypass condition (verified from source, line 556):**
`_classify_tactic_gated` skips the gate when `pv_blob is None OR pre_flaw_eval_cp is None`.
Both arms see the same skip behavior for mate-adjacent flaws (where `eval_cp` is None).

### Pattern 3: Blob Loading Query (from retag_flaws.py)

**What:** Load the 216 user-28 blob-bearing flaws. Since there are only 216 rows (vs millions
for prod), a single non-paginated query replaces the keyset-pagination loop.

```python
# Source: scripts/retag_flaws.py _fetch_flaw_page (lines 361-404)
# Simplified for single-shot load of user-28's 216 blob-bearing flaws.
from sqlalchemy import or_, select
from app.models.game_flaw import GameFlaw
from app.repositories.game_flaws_repository import TACTIC_TAG_COLUMNS

stmt = select(
    GameFlaw.user_id,
    GameFlaw.game_id,
    GameFlaw.ply,
    GameFlaw.fen,                    # board_fen() before the flaw — used for lichess link
    *(getattr(GameFlaw, col) for col in TACTIC_TAG_COLUMNS),  # 8 tactic cols (existing tags)
    GameFlaw.allowed_pv_lines,       # deferred on entity; OK in explicit select — auto-JSONB
    GameFlaw.missed_pv_lines,        # deferred on entity; auto-deserializes to list[dict]
).where(
    GameFlaw.user_id == user_id,     # user_id = 28
    or_(
        GameFlaw.allowed_pv_lines.isnot(None),
        GameFlaw.missed_pv_lines.isnot(None),
    )
).order_by(GameFlaw.user_id, GameFlaw.game_id, GameFlaw.ply)
```

Positions query (same as `_load_positions_for_page`, lines 407-433):
```python
from app.models.game_position import GamePosition

stmt = select(
    GamePosition.user_id,
    GamePosition.game_id,
    GamePosition.ply,
    GamePosition.move_san,           # needed for allowed-pass board setup
    GamePosition.pv,                 # PV string for detection + dropped-case surface
    GamePosition.eval_mate,          # for has_forced_mate flag in detect_tactic_motif
    GamePosition.eval_cp,            # white-perspective cp — gate's already-winning reject
).where(...)
```

### Pattern 4: Depth-Shift Definition

**What:** "Depth-shift" is a population-level distribution comparison, not a per-case diff.
`tactic_depth` (stored in `allowed_tactic_depth` / `missed_tactic_depth`, also returned as
the 4th element of the `_detect_tactic_for_flaw` tuple) is the loop index within the PV
where the motif fires (detector-loop index, per `game_flaw.py` line 79-87).

**Report shape for depth-shift:**
The gate removes tags entirely (suppressed → None) rather than changing depth of survived tags.
The depth-shift analysis shows the DISTRIBUTION of depths across both populations:

| Motif | Arm | Depth 0 | Depth 1 | Depth 2 | Depth 3+ | Mean depth |
|-------|-----|---------|---------|---------|----------|-----------|
| fork | ungated | N | N | N | N | X.X |
| fork | gated | N | N | N | N | X.X |

A shallower mean depth in the gated population confirms the gate is removing the
"deep-disconnected and incidental-tail tags" the design note predicted.

For cases where both arms detect the same motif (survived), depth should be identical — the
gate does not change which PV node the detector fires on, only whether the motif is credited.

### Pattern 5: Dropped-Case Surface (Hand-Check Report)

Each dropped case is a flaw where the ungated arm produces `motif is not None` but the gated
arm returns `(None, None, None, None)` for the same orientation.

Required fields per case:
- **Orientation**: `allowed` (opponent punished user's mistake) or `missed` (user missed a tactic)
- **Motif name**: `TacticMotifInt(motif_int).name` (e.g. `"clearance"`, `"sacrifice"`)
- **FEN**: `game_flaw.fen` (piece-placement before the flaw, from `board_fen()`)
- **Tactic depth**: from ungated arm's 4th return value
- **PV line**: `positions[ply+1].pv` (allowed) or `positions[ply].pv` (missed) — the stored
  refutation/best-move PV string as stored in `game_positions.pv`
- **Lichess deep-link**: reconstructed from FEN (see §Code Examples)

### Pattern 6: Lichess Analysis Deep-Link URL

**What:** URL format for opening a position in the lichess analysis board. [ASSUMED]

```python
# Source: training knowledge — not found in project codebase. Tag [ASSUMED].
import urllib.parse

def lichess_analysis_url(board_fen: str, ply: int) -> str:
    """Build lichess analysis URL from board_fen() + side-to-move inferred from ply parity.

    game_flaw.fen is board_fen() (piece placement only: no castling, en passant).
    Reconstruct a minimal FEN: '{piece_placement} {side} - - 0 1'
    """
    side = "w" if ply % 2 == 0 else "b"
    full_fen = f"{board_fen} {side} - - 0 1"
    encoded = urllib.parse.quote(full_fen, safe="")
    return f"https://lichess.org/analysis?fen={encoded}"
```

[ASSUMED] The lichess analysis URL format is `https://lichess.org/analysis?fen={url_encoded_fen}`.
Spaces in the FEN must be percent-encoded (not underscore). The lichess board accepts partial
FENs (piece placement + side-to-move with placeholder castling/ep rights).

### Pattern 7: Report Convention (`reports/retag/`)

`reports/retag/` currently contains only `.gitkeep` [VERIFIED: filesystem].
The directory is committed in git and is the established output location.

The existing report convention from `_write_retag_report` (retag_flaws.py line 513-608):
- Metadata header: Generated timestamp, script name, margin value, scope, mode, counts
- Pipe tables for per-motif statistics
- Summary totals at the bottom
- Footer pointing to the generating script

Suggested filename: `reports/retag/ab-validation-YYYY-MM-DD.md` (from CONTEXT Claude's
Discretion). The A/B report is richer than the dry-run retag report and should include
additional sections:

```markdown
# FlawChess A/B Gate Validation Report

**Generated:** {ts}
**Script:** `scripts/ab_validate_gate.py`
**DB:** dev, user-id 28
**Margin tested:** {margin}
**Total blob-bearing flaws:** 216 (100 allowed-tagged + 71 missed-tagged in stored DB)

## Executive Summary

| Metric | Count |
|--------|-------|
| Ungated tags (allowed) | N |
| Gated tags survived (allowed) | N |
| Gate suppressed (allowed) | N ({pct}%) |
| Ungated tags (missed) | N |
| Gated tags survived (missed) | N |
| Gate suppressed (missed) | N ({pct}%) |

## Per-Motif: Allowed Orientation

| Motif | Ungated | Suppressed | Survived | Suppression % |
|-------|---------|------------|----------|---------------|
...

## Per-Motif: Missed Orientation

...

## Depth-Shift Distribution

| Motif | Arm | Depth 0 | Depth 1 | Depth 2 | Depth 3+ | Mean |
...

## Dropped Cases — Hand-Check Required (HUMAN-UAT)

| # | Orientation | Motif | Depth | Lichess Analysis |
|---|-------------|-------|-------|-----------------|
| 1 | allowed | clearance | 4 | [position](https://lichess.org/analysis?fen=...) |
...

### Full PV Lines for Dropped Cases

#### Case 1 — clearance (allowed, depth 4)
FEN: `{fen}`
PV: `{pv_string}`
Gate reject reason: ...

## False Negative Count (HUMAN-UAT — fill in after hand-check)

- **Total dropped:** N
- **False negatives (good tags killed):** _[fill in]_
- **Correct drops (noise):** _[fill in]_

## A/B Summary & Margin Justification

Margin 0.35 {confirmed/changed to X} based on hand-check results.
ONLY_MOVE_WIN_PROB_MARGIN pointer comment updated in `forcing_line_gate.py`.

*Generated by `scripts/ab_validate_gate.py --db dev --user-id 28 --margin 0.35`.*
```

### Anti-Patterns to Avoid

- **`--margin 0` as the ungated arm**: `margin=0` still applies the already-winning reject
  (>300 cp), still-winning floor (200 cp), and one-mover discard. It is NOT the pre-gate
  baseline. Only bypassing `apply_forcing_line_filter` entirely gives the genuine old arm.
- **Writing to the DB**: the A/B script must be read-only. No `session.commit()`. No tactic
  column updates. No blob writes.
- **Calling the engine**: the entire value of the stored blobs is that re-detection is
  engine-free. The A/B script must not instantiate `EnginePool` or call Stockfish.
- **Loading full ORM entities for `game_flaw`**: `allowed_pv_lines` / `missed_pv_lines` are
  `deferred=True` on the ORM entity (STORE-02 leak guard). Always select them explicitly as
  column attributes (same as `_fetch_flaw_page`'s `GameFlaw.allowed_pv_lines` projection).
- **Comparing blobs across machines**: the whole point of both arms reading the SAME stored
  blobs is to isolate gate logic from `eval_cp` cross-machine non-determinism (VALID-01).
  Never run one arm on dev blobs and the other on prod blobs.
- **Using `asyncio.gather` on the same `AsyncSession`**: CLAUDE.md hard rule. The A/B
  script has no parallelism need (216 rows, pure CPU), so execute sequentially.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Gate logic | Custom only-move check | `apply_forcing_line_filter` / `is_solver_node_forced` (forcing_line_gate.py) | Already implements mate hierarchy, already-winning reject, floor, strip — Phase 141/143 |
| Detection kernel | Custom PV walker | `_detect_tactic_for_flaw` (flaws_service.py line 406) | Single classify path; SC4 guarantee |
| Motif name lookup | `if motif == 1: name = "pin"` | `TacticMotifInt(motif_int).name` | Enum is the canonical name registry |
| DB connection setup | Custom asyncpg connect | `db_url_for_target(db)` + `create_async_engine` + `async_sessionmaker` | Pattern from retag_flaws.py; handles dev/benchmark/prod routing |
| JSONB deserialization | Manual JSON parsing | Let asyncpg auto-deserialize | asyncpg auto-registers JSONB codec; `allowed_pv_lines` arrives as `list[dict]` |
| Solver-color inference | Ad-hoc ply-parity check | `_solver_color_for(n, orientation)` (flaws_service.py line 508) | Already handles the even/odd ply + orientation combination |

**Key insight:** This phase is a composition of existing building blocks. The total new code
is the A/B comparison loop + report formatter. Every chess/gate/DB building block already exists.

## Common Pitfalls

### Pitfall 1: `margin=0` Is Not the Ungated Baseline

**What goes wrong:** Script passes `margin=0.0` to the "old" arm, expecting the gate to be
a no-op. Gate still applies the already-winning reject (>300 cp), still-winning floor, and
one-mover discard — all of which were added in Phase 143 alongside the margin check.

**Why it happens:** `apply_forcing_line_filter`'s margin parameter only controls the
`is_solver_node_forced` sigmoid threshold. The structural filters (D-08, D-09, D-10) are
applied unconditionally before `is_solver_node_forced` is ever called.

**How to avoid:** Ungated arm calls `_detect_tactic_for_flaw` directly (option b). Never calls
`_classify_tactic_gated` or `apply_forcing_line_filter` for the old arm.

**Warning signs:** If ungated arm and gated arm produce identical results for a blob where the
pre-flaw position is >300 cp, the ungated arm is still running the already-winning reject.

### Pitfall 2: Empty Blob List vs None

**What goes wrong:** Testing `if pv_blob:` treats an empty list `[]` the same as `None`, but
`_classify_tactic_gated` (line 549-551) explicitly documents: gate condition is
`pv_blob is not None`, not `if pv_blob`. An empty blob must go through the gate and be
rejected by the one-mover discard.

**How to avoid:** Use `pv_blob is not None` for gate-skip check. For the ungated arm, this
is moot (no gate invoked), but the A/B diff logic should handle `[] vs None` carefully.

### Pitfall 3: pre_flaw_eval_cp Is None for Mate-Adjacent Flaws

**What goes wrong:** `positions[n].eval_cp` is `None` when the flaw ply has a mate evaluation
(eval_mate is set instead). Both arms skip the gate for these flaws (`_classify_tactic_gated`
line 556: `pre_flaw_eval_cp is not None`). If the A/B doesn't handle this, it may
miscount these as "gated suppressed" when they are actually gate-skipped by both arms.

**How to avoid:** When `pre_flaw_eval_cp is None`, both arms return the raw detection result.
The diff for such flaws should always show 0 suppression (both arms agree). Flag any
discrepancy in mate-adjacent cases as a bug.

### Pitfall 4: FEN for Lichess URL Is Piece-Placement Only

**What goes wrong:** `game_flaw.fen` is `board.board_fen()` (piece-placement only, per
`game_flaw.py` line 68 comment). Passing this raw to a lichess URL gives a malformed FEN.

**How to avoid:** Reconstruct a minimal FEN before URL-encoding:
`f"{flaw.fen} {'w' if flaw.ply % 2 == 0 else 'b'} - - 0 1"`.
Castling rights and en passant are unknown (safe to use `-`); lichess renders the position
correctly from piece placement + side-to-move alone. [ASSUMED]

### Pitfall 5: Small-N Motifs Can Mislead

**What goes wrong:** Reporting "100% suppressed" for a motif with 1 case overstates the
gate's impact. Some motifs (clearance, sacrifice, self-interference, x-ray) may have ≤5
cases in user-28's 216 blobs.

**How to avoid:** Add a small-N caveat column or footnote in the report table. Flag any
motif with `N < 5` or `N < 10` explicitly. Do not draw conclusions about those motifs.

### Pitfall 6: AGPL Boundary

**What goes wrong:** Accidentally copying code from the lichess-puzzler repository at
`/home/aimfeld/Projects/Python/lichess-puzzler` while researching the gate logic.

**How to avoid:** The gate is already implemented in `forcing_line_gate.py`. The A/B script
only calls existing project code. Do not read or reference lichess-puzzler source for this
phase. Heuristics, constants, and function names are fine (they are facts); source is not.

## Code Examples

### Verified: `_classify_tactic_gated` Signature and Gate Invocation

```python
# Source: app/services/flaws_service.py lines 525-560 [VERIFIED: Read tool]
def _classify_tactic_gated(
    n: int,
    fen_map: dict[int, str],
    positions: list[GamePosition],
    orientation: Literal["allowed", "missed"],
    pv_blob: list[PvNode] | None,
    pre_flaw_eval_cp: int | None,
    pv_by_ply: Mapping[int, str] | None = None,
    margin: float = ONLY_MOVE_WIN_PROB_MARGIN,
) -> tuple[int | None, int | None, int | None, int | None]:
    motif, piece, conf, depth = _detect_tactic_for_flaw(
        n, fen_map, positions, pv_by_ply, orientation
    )
    # Gate applied only when: motif detected AND blob present AND eval_cp present.
    if motif is not None and pv_blob is not None and pre_flaw_eval_cp is not None:
        solver_color = _solver_color_for(n, orientation)
        if not apply_forcing_line_filter(pv_blob, solver_color, pre_flaw_eval_cp, margin):
            return None, None, None, None
    return motif, piece, conf, depth
```

### Verified: `_detect_tactic_for_flaw` Signature (the Ungated Kernel)

```python
# Source: app/services/flaws_service.py lines 406-412 [VERIFIED: Read tool]
def _detect_tactic_for_flaw(
    n: int,
    fen_map: dict[int, str],
    positions: list[GamePosition],
    pv_by_ply: Mapping[int, str] | None = None,
    orientation: Literal["allowed", "missed"] = "allowed",
) -> tuple[int | None, int | None, int | None, int | None]:
    ...
```

Note: `orientation` parameter is keyword-arg–safe (use `orientation=` explicitly).

### Verified: `apply_forcing_line_filter` Signature

```python
# Source: app/services/forcing_line_gate.py lines 269-318 [VERIFIED: Read tool]
def apply_forcing_line_filter(
    line: Sequence[PvNode],         # the JSONB blob list (list[dict] from asyncpg)
    solver_color: Literal["white", "black"],  # from _solver_color_for(n, orientation)
    pre_flaw_eval_cp: int,          # white-perspective cp at flaw ply
    margin: float = ONLY_MOVE_WIN_PROB_MARGIN,  # tunable; default 0.35
) -> bool:
    ...  # True = gate PASSES (motif credited); False = gate REJECTS (motif suppressed)
```

### Verified: TACTIC_TAG_COLUMNS

```python
# Source: app/repositories/game_flaws_repository.py lines 154-163 [VERIFIED: Read tool]
TACTIC_TAG_COLUMNS: tuple[str, ...] = (
    "allowed_tactic_motif",
    "allowed_tactic_piece",
    "allowed_tactic_confidence",
    "allowed_tactic_depth",
    "missed_tactic_motif",
    "missed_tactic_piece",
    "missed_tactic_confidence",
    "missed_tactic_depth",
)
```

### Verified: PvNode Blob Shape

```python
# Source: app/services/forcing_line_gate.py lines 63-87 [VERIFIED: Read tool]
# and app/models/game_flaw.py lines 107-116
class PvNode(TypedDict):
    b:  int | None   # best_cp — white-perspective centipawns (None if best is mate)
    bm: int | None   # best_mate — mate-in-N (positive=white mating; None if not mate)
    s:  int | None   # second_cp — white-perspective cp (None if no legal 2nd or 2nd is mate)
    sm: int | None   # second_mate — mate-in-N for 2nd best (None if not mate)
    su: str          # second-best UCI string e.g. "e2e4", or "" if no 2nd move
```

Asyncpg auto-deserializes JSONB to `list[dict]` matching this shape. The gate casts at
read time via `eval_cp_to_expected_score(cp, solver_color)`.

### Verified: `_FlawWork` / `_worker_recompute` — Template for A/B Per-Flaw Struct

```python
# Source: scripts/retag_flaws.py lines 256-332 [VERIFIED: Read tool]
# The A/B script can define a lighter struct since it needs no margin threading
# to worker processes (216 rows, single-process is instant):
@dataclass(frozen=True)
class _AbWork:
    user_id: int
    game_id: int
    ply: int
    fen: str            # game_flaws.fen — board_fen() before flaw
    cur: _PosRow | None # position at ply (for missed pass, eval_cp source)
    nxt: _PosRow | None # position at ply+1 (for allowed pass)
    old_tuple: tuple[int | None, ...]   # existing 8 tactic cols (ungated baseline)
    allowed_pv_blob: list[Any] | None
    missed_pv_blob: list[Any] | None
```

### Verified: ONLY_MOVE_WIN_PROB_MARGIN Location

```python
# Source: app/services/forcing_line_gate.py line 52 [VERIFIED: Read tool]
ONLY_MOVE_WIN_PROB_MARGIN: float = 0.35

# Comment to add at phase end (D-03a):
# ONLY_MOVE_WIN_PROB_MARGIN = 0.35  # confirmed by Phase 144 A/B hand-check
# See reports/retag/ab-validation-YYYY-MM-DD.md for noise-removed vs false-negative data.
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|-----------------|--------------|--------|
| Tag all motifs that fire in stored PV | Gate motifs by forcing-line criterion before crediting | Phase 141/143 | Removes non-forced/deep/incidental tags |
| Margin=0.35 provisional | Margin confirmed/committed | Phase 144 (this phase) | Locks the constant based on empirical hand-check |
| Single classify path `_classify_tactic_gated` | A/B compares ungated `_detect_tactic_for_flaw` vs gated path | Phase 144 (this phase) | Measures gate's contribution in isolation from eval noise |

**Deprecated/outdated:**
- Old "detector refresh" tool: superseded by `retag_flaws.py` which includes the gate (per retag_flaws.py module docstring). Do not add a gate-free refresh mode to `retag_flaws.py`.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Lichess analysis URL format: `https://lichess.org/analysis?fen={url_encoded_fen}` with spaces as `%20` | §Code Examples / Pitfall 4 | Links in hand-check report would 404; user must navigate manually instead |
| A2 | `game_flaw.fen` + reconstructed `"w"/"b" - - 0 1"` produces a valid lichess analysis FEN | §Pitfall 4 | Same as A1; partial FENs are widely accepted by lichess but not verified here |

**If this table is empty:** All other claims in this research were verified or cited — no user
confirmation needed for the implementation path.

## Open Questions

1. **Lichess deep-link URL format**
   - What we know: `https://lichess.org/analysis` accepts FEN parameters [ASSUMED]
   - What's unclear: exact query param name (`?fen=` vs `/analysis/{fen}`) and whether
     partial FENs (piece placement + side only) render correctly without JS errors
   - Recommendation: use `?fen={urllib.parse.quote(full_fen)}` and test one link manually
     before committing the report. The hand-check step is human-performed anyway, so the
     user will notice immediately if links are broken.

2. **Small-N motif coverage in the 216 blobs**
   - What we know: 216 total blob-bearing flaws; 100 allowed-tagged, 71 missed-tagged
     in the stored DB (from CONTEXT.md feasibility finding)
   - What's unclear: how these are distributed across motifs (clearance/sacrifice/
     capturing-defender are the expected noisy motifs per the design note, but exact counts
     are not known before running the script)
   - Recommendation: run a quick SQL count query during implementation to size the report
     per-motif section appropriately and set small-N thresholds.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker (dev DB) | Blob loading | Assumed ✓ | per project | `docker compose -f docker-compose.dev.yml -p flawchess-dev up -d` |
| Python 3.13 / uv | Script execution | ✓ | per CLAUDE.md | — |
| `app.services.flaws_service._detect_tactic_for_flaw` | Ungated arm | ✓ | confirmed line 406 | — |
| `app.services.flaws_service._classify_tactic_gated` | Gated arm | ✓ | confirmed line 525 | — |
| `app.services.forcing_line_gate.apply_forcing_line_filter` | Gate verification | ✓ | confirmed line 269 | — |

No new environment dependencies. Dev DB must be running before executing the script or tests.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (project standard) |
| Config file | `pyproject.toml` (project root) |
| Quick run command | `uv run pytest tests/scripts/test_ab_validate_gate.py -x` |
| Full suite command | `uv run pytest -n auto -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| VALID-01 | Ungated arm never calls `apply_forcing_line_filter` | unit | `uv run pytest tests/scripts/test_ab_validate_gate.py::test_ungated_arm_bypasses_gate -x` | ❌ Wave 0 |
| VALID-01 | Both arms read same stored blobs (no engine) | unit | `uv run pytest tests/scripts/test_ab_validate_gate.py::test_both_arms_use_same_blobs -x` | ❌ Wave 0 |
| VALID-01 | Gated arm produces fewer-or-equal tags than ungated arm | unit | `uv run pytest tests/scripts/test_ab_validate_gate.py::test_gated_lte_ungated -x` | ❌ Wave 0 |
| VALID-02 | Report written to reports/retag/ with all required sections | unit | `uv run pytest tests/scripts/test_ab_validate_gate.py::test_report_output -x` | ❌ Wave 0 |
| VALID-02 | Dropped-case list contains motif + FEN + PV + lichess URL per case | unit | `uv run pytest tests/scripts/test_ab_validate_gate.py::test_dropped_case_fields -x` | ❌ Wave 0 |
| VALID-02 | End-to-end against dev DB user-28 produces non-empty report | integration | `uv run pytest tests/scripts/test_ab_validate_gate.py::test_e2e_dev_user28 -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/scripts/test_ab_validate_gate.py -x`
- **Per wave merge:** `uv run pytest -n auto -x`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/scripts/test_ab_validate_gate.py` — covers all VALID-01, VALID-02 unit cases
- [ ] Test uses session-maker injection pattern from `test_retag_flaws.py` (model to follow)
- [ ] Test uses `_FORCING_BLOB` / `_NON_FORCING_BLOB` fixture patterns from `test_retag_flaws.py`
- [ ] Integration test requires dev DB running; should be `@pytest.mark.integration` or
  placed in a directory that the `addopts --ignore` pattern excludes from CI

## Security Domain

> No authentication, no external input parsing, no user data exposed. The A/B script is
> a local dev tool run by the developer with direct DB access. ASVS is not applicable.

The only security-relevant note: the script reads production-adjacent data if run with
`--db prod`, but in this phase it is scoped to `--db dev --user-id 28` only.

## Sources

### Primary (HIGH confidence)

- `app/services/flaws_service.py` lines 406-560 — `_detect_tactic_for_flaw`, `_solver_color_for`, `_classify_tactic_gated` — all function signatures, gate invocation site [VERIFIED: Read tool]
- `app/services/forcing_line_gate.py` lines 1-319 — `apply_forcing_line_filter`, `is_solver_node_forced`, `ONLY_MOVE_WIN_PROB_MARGIN`, `PvNode` TypedDict, gate logic [VERIFIED: Read tool]
- `scripts/retag_flaws.py` lines 1-799 — `_fetch_flaw_page`, `_load_positions_for_page`, `_worker_recompute`, `_write_retag_report`, query shapes, report template [VERIFIED: Read tool]
- `app/models/game_flaw.py` lines 1-122 — `allowed_pv_lines`/`missed_pv_lines` JSONB columns (deferred), 8 tactic-tag columns, `fen` column, PvNode blob shape docs [VERIFIED: Read tool]
- `app/repositories/game_flaws_repository.py` lines 154-163 — `TACTIC_TAG_COLUMNS` canonical list [VERIFIED: Read tool]
- `tests/scripts/test_retag_flaws.py` lines 1-80 — test patterns, `_FORCING_BLOB`/`_NON_FORCING_BLOB` fixtures, session-maker injection [VERIFIED: Read tool]
- `.planning/phases/144-user-28-a-b-validation/144-CONTEXT.md` — locked decisions D-01 through D-04a [VERIFIED: Read tool]
- `.planning/REQUIREMENTS.md` §VALID — VALID-01, VALID-02 exact wording [VERIFIED: Read tool]

### Secondary (MEDIUM confidence)

- `reports/retag/` (filesystem) — currently only `.gitkeep`; empty committed directory [VERIFIED: Bash]
- `reports/multipv-validation/validate-multipv-budget-2026-06-30.md` — report metadata header convention [VERIFIED: Read tool]
- `.planning/notes/tactic-forcing-line-gate.md` — AGPL boundary statement, gate model design, depth-shift intent [VERIFIED: Read tool]

### Tertiary (LOW confidence)

- Lichess analysis URL format `https://lichess.org/analysis?fen={encoded}` — [ASSUMED] from training knowledge; not found in project codebase

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all deps are project-internal; no new packages
- Architecture: HIGH — verified directly from production code (function signatures, line numbers, query shapes)
- Ungated arm mechanism: HIGH — option (b) confirmed by reading `_detect_tactic_for_flaw` and `_classify_tactic_gated` at source level
- Pitfalls: HIGH — all derived from comments in the source code (the "pv_blob is not None not `if pv_blob`" pitfall is literally documented in `_classify_tactic_gated`'s docstring)
- Lichess URL format: LOW — [ASSUMED]; use and test manually

**Research date:** 2026-06-30
**Valid until:** Stable — this is a closed-scope validation phase with no external dependencies; research is valid until the gate code changes.
