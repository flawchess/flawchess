# Phase 127: Detector Hardening & Validation - Research

**Researched:** 2026-06-19
**Domain:** Pure-Python chess tactic detector, lichess CC0 puzzle validation, Alembic migration
**Confidence:** HIGH (all findings grounded in direct code reads and confirmed external sources)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01**: Relevance-gate every non-mate detector — fires only on a *real* instance (wins material / is forcing), not geometric presence alone. Directly fixes `detect_pin` line 308 ("pin exists … that's enough") and removes Case-B-at-any-depth phantom hits.
- **D-02**: Dispatch non-mate motifs by `min(depth)` — the existing priority tiers become the equal-depth tiebreak only. Relevance gate (D-01) is a required companion.
- **D-03**: Mates: keep D-07 dominance AND exempt mate tags from the depth filter. A forced mate in the line is always the tag; mate tags render regardless of the depth filter.
- **D-04**: Store raw half-move ply index from `flaw_ply+1` (the detector loop index — already known, currently discarded). Player-facing unit is Phase 129.
- **D-05**: Detector contract becomes `(fired, piece, confidence, depth)`; dispatcher selects `min(depth)` with priority tiebreak.
- **D-06**: Harness must validate depth-vs-puzzle-Rating correlation as a first-class output of SC#2.
- **D-07**: Committed stratified fixture. One-time `scripts/` selector samples N puzzles per motif-theme + Rating band; CI test runs offline. Selector is re-runnable.
- **D-08**: Precision blocks, recall reports. Per-motif precision floor is a hard CI gate; recall is measured and printed but non-blocking.
- **D-09**: Tiered precision floor. Core 8 + geometric + mates ≈ ≥0.90 (confirm during planning against measured fixture numbers). Tier-3 fuzzy motifs shipped suppressed if they miss the floor, via existing `tactic_confidence` query-suppression lever.
- **D-10**: Multi-label theme matching. Credit a precision hit when our motif is in the puzzle's theme set. Explicit motif→lichess-theme map; explicit list of motifs with no lichess equivalent (marked unvalidated).
- **D-11**: No AGPL `cook.py`. Use CC0 puzzle data only. Record boundary in harness docstring.
- **D-12**: Supersede the circular fixtures. CI precision/recall numbers come from the independent puzzle set, not `tests/services/test_tactic_detector.py` self-labeled fixtures.
- **D-13**: Dev re-backfill in-phase; prod deferred to runbook. Existing `scripts/backfill_flaws.py` reused, no new script.
- **D-14 (LOCKED, user directive)**: Harness/tagger tests in `tests/scripts/tagger/` — a new default-excluded directory (parallel to `tests/scripts/benchmarks/`). Add `--ignore=tests/scripts/tagger` to `pyproject.toml` `addopts` alongside the existing benchmark ignore. Directory creation and `--ignore=` entry must land together.

### Claude's Discretion

- Exact precision floor value(s) per tier (D-09 says ≈0.90 for core; confirm during planning against measured fixture numbers).
- Fixture sample size N per motif-theme and Rating-band stratification granularity (D-07).
- The precise form of the relevance/forcing gate per detector (D-01) — material-delta vs forcing-line membership vs both; planner's call, validated by the harness precision delta (SC#3).

### Deferred Ideas (OUT OF SCOPE)

- Player-facing depth unit + beginner/intermediate/advanced thresholds — Phase 129.
- Prod re-backfill execution — runbook step after 127 ships.
- Hardening currently-suppressed tier-3 motifs so they pass the precision floor.
- Re-ranking by confidence (drop fork below 0.8 so also-detected pin wins) — explicitly rejected in architecture note.
</user_constraints>

---

## Summary

Phase 127 has three tightly coupled deliverables: (1) return `depth` from every detector and store a nullable `tactic_depth` SmallInteger on `game_flaws`; (2) build a read-only validation harness that scores the detector against the lichess CC0 puzzle database reporting precision AND recall per motif; (3) fix the deep-scan / loose-pin false positives in `detect_fork` and `detect_pin` via a relevance gate.

The depth and precision work are one task, not two tracks: the depth return IS the input the `min(depth)` dispatcher needs, and the relevance gate is what keeps early junk hits from beating real deep combinations. All detector changes are pure-Python with no I/O or engine calls. The integration ripple is small: four functions changed (`detect_*` signatures, dispatcher selection logic, `_detect_tactic_for_flaw` in `flaws_service.py`, one Alembic migration). The harness is new infrastructure (selector script, committed fixture CSV, excluded test dir) but reads no database — it is a pure offline Python/chess computation over a flat file.

The dev DB currently holds 73,201 `game_flaws` rows, 32,712 of which carry tactic tags. The top tagged motifs are fork (10,083), discovered-attack (6,305), pin (6,299), and skewer (4,778) — the same motifs most likely to carry false positives from the deep-scan and loose-pin bugs. The dev re-backfill (D-13) must run against all tagged games after the precision fix lands; `backfill_flaws.py` already supports this without modification.

**Primary recommendation:** Treat D-01 (relevance gate) and D-05 (4-tuple signature + `min(depth)` dispatch) as a single atomic unit. Neither works correctly without the other. Build and validate them together before building the harness, so the harness measures the fixed detector, not the broken one.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Detector signature change (4-tuple) | Backend service | — | Pure Python transform in `tactic_detector.py`; no I/O |
| Dispatcher min(depth) selection | Backend service | — | Logic change in `detect_tactic_motif`; single function |
| Relevance gate per detector | Backend service | — | Material-delta / forcing check inside each `detect_*` body |
| `tactic_depth` column | Database/Storage | Backend migration | New nullable SmallInteger; Alembic migration |
| `game_flaws` write path update | Backend service | Repository | `FlawRecord` TypedDict + `flaw_record_to_row` mapping |
| Puzzle selector script | Backend scripts | — | One-time offline Python script; reads CSV, writes fixture |
| Committed fixture | Repository | — | Static CSV file committed to git; no DB needed |
| Validation harness (precision/recall) | Backend tests | — | Pure offline Python test in excluded dir |
| CI precision gate | CI/CD | — | Dedicated step with explicit path override |
| Dev re-backfill | Backend scripts | — | `backfill_flaws.py --db dev` reused without change |

---

## Detector Code Reality

### Current Signatures (all return 2-tuples or 3-tuples)

**Core 8 detectors** — all return `tuple[bool, int | None]`:
- `detect_fork(boards, moves, pov)` → `(fired, forking_piece_type)`
- `detect_hanging_piece(boards, moves, pov)` → `(fired, victim_piece_type)`
- `detect_pin(boards, moves, pov)` → `(fired, line_piece_type)`
- `detect_skewer(boards, moves, pov)` → `(fired, line_piece_type)`
- `detect_double_check(boards, moves, pov)` → `(fired, None)` always
- `detect_discovered_attack(boards, moves, pov)` → `(fired, unveiled_attacker_type)`
- `detect_back_rank_mate(boards, moves, pov)` → `(fired, mating_piece_type)`
- `detect_generic_mate(boards, moves, pov)` → `(fired, mating_piece_type)`

**Named-mate detectors** — all return `tuple[bool, int | None]` (except boden/double-bishop):
- `detect_smothered_mate`, `detect_anastasia_mate`, `detect_hook_mate`, `detect_arabian_mate`, `detect_dovetail_mate` → `(fired, piece_type)`
- `detect_boden_or_double_bishop_mate(boards, moves, pov)` → `(TacticMotif | None, int | None)` (unique shape — returns the motif string, not bool)

**Tier-3 detectors** — all return `tuple[bool, int | None, int]`:
- `detect_deflection`, `detect_attraction`, `detect_intermezzo`, `detect_x_ray`, `detect_interference`, `detect_self_interference`, `detect_clearance`, `detect_capturing_defender`, `detect_sacrifice`

**Dispatcher** `detect_tactic_motif(board_after_flaw, pv_str)`:
- Current return: `tuple[int | None, int | None, int | None]` — `(tactic_motif_int, tactic_piece, tactic_confidence)`
- Phase 127 return: `tuple[int | None, int | None, int | None, int | None]` — adds `tactic_depth`

### Phase 127 Contract

Every `detect_*` function becomes a **4-tuple**:
- Core 8 + named-mate: `tuple[bool, int | None, int | None]` → `tuple[bool, int | None, int | None]` where third element is `depth` (currently absent — these return 2-tuples)
  - More precisely: `(fired, piece, depth)` where depth is the loop index `i` at fire time
- Tier-3: `tuple[bool, int | None, int, int | None]` where last element is depth
  - More precisely: `(fired, piece, confidence, depth)`
- Dispatcher adds 4th element to its return: `(motif_int, piece, confidence, depth)`

### Registry Contents (exact, from code read)

**`_NAMED_MATE_REGISTRY`** — 5 entries (smothered, anastasia, hook, arabian, dovetail), plus boden/double-bishop handled via `detect_boden_or_double_bishop_mate` outside the loop, plus back-rank and generic mate:
```python
_NAMED_MATE_REGISTRY = [
    ("smothered-mate", TacticMotifInt.SMOTHERED_MATE),
    ("anastasia-mate", TacticMotifInt.ANASTASIA_MATE),
    ("hook-mate",      TacticMotifInt.HOOK_MATE),
    ("arabian-mate",   TacticMotifInt.ARABIAN_MATE),
    ("dovetail-mate",  TacticMotifInt.DOVETAIL_MATE),
]
```

**`_GEOMETRIC_REGISTRY`** — 5 entries in priority order:
```python
_GEOMETRIC_REGISTRY = [
    ("fork",              TacticMotifInt.FORK),
    ("skewer",            TacticMotifInt.SKEWER),
    ("pin",               TacticMotifInt.PIN),
    ("discovered-attack", TacticMotifInt.DISCOVERED_ATTACK),
    ("double-check",      TacticMotifInt.DOUBLE_CHECK),
]
```

**`_TIER3_REGISTRY`** — 9 entries:
```python
_TIER3_REGISTRY = [
    ("deflection",          TacticMotifInt.DEFLECTION),
    ("attraction",          TacticMotifInt.ATTRACTION),
    ("intermezzo",          TacticMotifInt.INTERMEZZO),
    ("x-ray",               TacticMotifInt.X_RAY),
    ("interference",        TacticMotifInt.INTERFERENCE),
    ("self-interference",   TacticMotifInt.SELF_INTERFERENCE),
    ("clearance",           TacticMotifInt.CLEARANCE),
    ("capturing-defender",  TacticMotifInt.CAPTURING_DEFENDER),
    ("sacrifice",           TacticMotifInt.SACRIFICE),
]
```

**`hanging-piece`** is Tier 4 (catch-all, outside all registries) — dispatched last.

### The Two Named Offenders

**`detect_fork` (line 255)** — the deep-scan bug:
```python
for i in range(0, len(moves), 2):  # pov's turns at even indices
    # ... checks if move at index i is a fork ...
    if len(victims) >= 2:
        return True, mover_type
```
`i` is ALREADY the depth (half-moves from `flaw_ply+1`). Returning `i` as depth costs nothing. The bug: it scans the entire PV (up to 12 plies) for ANY fork by pov, not just the first/forcing one. A fork at `i=10` in a non-forcing continuation gets the same tag as a fork at `i=0`.

**`detect_pin` (lines 316-336)** — the loose-pin bug:
```python
for board in boards:         # iterates ALL 13 boards
    for sq in chess.SQUARES:
        # ... finds any pinned opponent piece ...
        # Simplified: pin exists and the pinner is a ray piece — that's enough.
        return True, pinner.piece_type
```
This scans every position in the PV for ANY pin by any pov ray piece, regardless of depth, and returns immediately on the first hit. No material check, no forcing check.

**Depth extraction for `detect_pin`**: Unlike `detect_fork` which already has loop index `i`, `detect_pin` iterates `for board in boards:` — it needs to track board index explicitly: `for board_idx, board in enumerate(boards):`. Depth for a pin found in `boards[k]` = `k - 1` (board index 0 is before pov's first move; the pin in boards[k] occurred after move k-1). Alternatively, rewrite to iterate boards at pov-move positions: `for i in range(0, len(moves), 2):` — the pov's board after move i is `boards[i+1]`, and the opponent board is `boards[i]` (a pin on the opponent at board `i` was created by pov's move `i-1`). The simplest is: `for k, board in enumerate(boards): depth = k`.

---

## Dispatcher Change (D-02/D-05)

### Current dispatcher (lines 1227-1307)

The dispatcher runs three ordered passes (mate → geometric → tier-3 → hanging-piece), returning the first motif that fires. Selection is purely first-in-registry order within tiers. `detect_tactic_motif` returns a 3-tuple `(motif_int, piece, confidence)`.

### Phase 127 dispatcher change

The dispatcher must now:
1. Run ALL non-mate detectors (not first-fire), collecting `(motif, piece, confidence, depth)` for every detector that fires.
2. Select the winner by `min(depth)` across the collected firings.
3. Use the existing priority-tier order as the equal-depth tiebreak (a fork and pin both firing at depth 2 → fork wins, since fork is higher in `_GEOMETRIC_REGISTRY`).
4. Mate detectors retain their D-03 dominance (always checked first, always win if fired, exempt from depth filter).
5. `hanging-piece` (Tier 4) participates in the depth-min selection like any geometric motif.

**Implementation shape:**

```python
# --- Tier 1: mate (unchanged — dominates always) ---
for motif_str, motif_int in _NAMED_MATE_REGISTRY:
    fired, piece, depth = fn(boards, moves, pov)
    if fired:
        return int(motif_int), piece, TACTIC_CONFIDENCE_HIGH, depth

# boden/double-bishop, back-rank, generic mate — similar

# --- Collect all non-mate firings ---
candidates: list[tuple[int, int | None, int, int]] = []  # (priority_rank, piece, confidence, depth)
# Run geometric (with priority rank 0..4), tier-3 (rank 5..13), hanging (rank 14)
# For each that fires: candidates.append((rank, piece, confidence, depth))

# Select winner: min depth, then min priority_rank as tiebreak
if candidates:
    winner = min(candidates, key=lambda c: (c[3], c[0]))
    return winner_motif_int, winner[1], winner[2], winner[3]

return None, None, None, None
```

**Preserves "exactly one motif per flaw"**: `min()` always produces one winner (ties broken by rank, which is deterministic).

**D-03 mate dominance**: Mates are checked first and returned immediately if fired — they never enter the `candidates` pool. Correct.

---

## Relevance Gate (D-01)

### What each detector currently has access to

All detectors receive `(boards: list[chess.Board], moves: list[chess.Move], pov: chess.Color)`. From these they can compute:

- **Material delta**: `_material_diff(board, pov)` — already exists in the module. The difference `_material_diff(board_at_depth, pov) - _material_diff(boards[0], pov)` measures how much pov gains at depth d.
- **Forcing moves**: `board.is_check()`, `board.is_capture(move)` — these signal forcing continuations. A forcing sequence is one where each intermediate move is either a check or a capture.
- **Immediate capture**: `board_before.piece_at(move.to_square) is not None` — the first pov move is a capture (strongest forcing signal).

### Proposed concrete gate

For **`detect_fork`** (deep-scan fix):
- Gate: the fork at depth `i` fires only if `_material_diff(boards[i+1], pov) > _material_diff(boards[0], pov)` — pov has gained material by the fork ply, OR the fork is the very first pov move (`i == 0`).
- Simpler alternative: require at least one victim to be actually captured in a subsequent pov move within the PV. This is more robust but requires lookahead.
- Cheapest reliable gate: require `i == 0` (first pov move is the fork) OR the line to `i` is forcing (all intermediate non-pov moves are checks or captures responding to threats). The context note's "Case A" (real deep combination) is precisely a combination where the intermediate moves are forced replies.

For **`detect_pin`** (loose-pin fix):
- Gate: the pin at board index `k` fires only if the pinned piece is one that pov WILL capture in a subsequent move in the PV. Check `moves[j].to_square == pinned_sq` for some later pov move `j > k`.
- Simpler gate: require that the pin creates immediate material gain — the pinned piece has higher value than the pinner AND the pin prevents the pinned piece from defending something pov captures at `k+2` or `k+4`.
- Minimum viable gate (precision first): require that at depth `k`, `_material_diff(boards[k], pov) >= _material_diff(boards[0], pov)` — the line so far hasn't lost pov material. This eliminates "pin in a losing continuation" but not "incidental pin in a winning continuation."

**The planner must choose the gate form** (Claude's Discretion). The harness will measure the precision delta, validating the choice. The research recommendation:

- For `detect_fork`: `material_gained = _material_diff(boards[i+1], pov) - _material_diff(boards[0], pov) > 0` OR `i == 0`. This is one line of code reusing existing `_material_diff`.
- For `detect_pin`: add a `_pin_wins_material(boards, moves, pov, pin_board_idx, pinned_sq)` helper that checks if pov captures the pinned piece in a later move. Falls back to `_material_diff` check if no direct capture found.
- For **other geometric detectors** (`detect_skewer`, `detect_discovered_attack`): apply the same `_material_diff` gate — `_material_diff(boards[i+1], pov) > _material_diff(boards[0], pov)`. They already loop over specific positions so depth `i` is known.

**`_material_diff` is already implemented** at line 217:
```python
def _material_diff(board: chess.Board, pov: chess.Color) -> int:
    """Sum of pov piece values minus opponent piece values. Excludes kings."""
```

---

## Integration Ripple

### `FlawRecord` TypedDict (`flaws_service.py`)

Currently:
```python
tactic_motif_int: int | None
tactic_piece: int | None
tactic_confidence: int | None
```

Phase 127 adds:
```python
tactic_depth: int | None
```

This is the only TypedDict change. All callers of `classify_game_flaws` receive the richer dict.

### `_detect_tactic_for_flaw` (`flaws_service.py` lines 360-405)

Currently returns `(tactic_motif_int, tactic_piece, tactic_confidence)` — 3-tuple from `detect_tactic_motif`. Phase 127: unpack a 4-tuple. The function signature and caller in `_build_flaw_record` both need one extra variable.

### `_build_flaw_record` (`flaws_service.py` line 426)

Currently:
```python
tactic_motif_int, tactic_piece, tactic_confidence = _detect_tactic_for_flaw(...)
return FlawRecord(..., tactic_motif_int=..., tactic_piece=..., tactic_confidence=...)
```

Phase 127: unpack one more variable, pass `tactic_depth=tactic_depth`.

### `flaw_record_to_row` (`game_flaws_repository.py`)

Currently maps `FlawRecord` to a dict for `pg_insert(GameFlaw).values(...)`. Phase 127 adds `"tactic_depth": flaw["tactic_depth"]` to the returned dict.

### `GameFlaw` model (`app/models/game_flaw.py`)

Currently has `tactic_motif`, `tactic_piece`, `tactic_confidence` (all nullable SmallInteger). Phase 127 adds:
```python
tactic_depth: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
```
Follows the exact same pattern as the three existing tactic columns.

### Alembic Migration

The Phase 124 migration (`20260617_120000_phase_124_tactic_motifs.py`) is the exact template:
- Naming convention: `20260619_HHMMSS_phase_127_tactic_depth.py`
- Single `op.add_column` call: `sa.Column("tactic_depth", sa.SmallInteger(), nullable=True)`
- No backfill in the migration (pre-existing rows get NULL — "honest" per D-04)
- Safe for inline deploy via `entrypoint.sh` (PostgreSQL 18 nullable column add is a catalog-only operation, no table rewrite)

---

## lichess CC0 Puzzle Database

### Format (VERIFIED)

**[CITED: database.lichess.org]**

CSV columns: `PuzzleId, FEN, Moves, Rating, RatingDeviation, Popularity, NbPlays, Themes, GameUrl, OpeningTags`

**FEN**: Position BEFORE the opponent makes their move. This is NOT the position the player sees — it is one move before the puzzle starts.

**Moves** (critical for harness): Space-separated UCI moves. 
- **First move = opponent's last move** (the blunder/setup that created the puzzle position).
- **Second move onwards = solution** (what the player must play).
- Example: `e8f7 e2e6 f7f8 e6f7` — `e8f7` is the opponent's blunder, `e2e6` is the player's first solution move.

**How to feed the detector**: The harness must apply the first Moves entry to the FEN, producing the "board after flaw" that the detector expects. `board_after_flaw = FEN + first_move applied`. Then `pv_str = " ".join(moves[1:])` (the solution is the refutation PV).

**Themes**: Space-separated camelCase theme names (multi-label). Examples: `fork pin middlegame`, `mate mateIn2 backRankMate`.

**License**: CC0 / Public Domain. [VERIFIED: database.lichess.org]

**cook.py**: AGPL-3.0 — `tagger/cook.py` in lichess-puzzler. The puzzle labels were generated by cook.py but the published dataset is CC0. Using the data is not using the AGPL code. [CITED: tactic-detector-precision-gaps.md]

### Motif → Lichess Theme Map (D-10)

**[CITED: https://github.com/lichess-org/lila/blob/master/translation/source/puzzleTheme.xml + HuggingFace README]**

| Our motif | Lichess theme | Notes |
|-----------|---------------|-------|
| `fork` | `fork` | Direct match |
| `hanging-piece` | (none) | Lichess has `hangingPiece` — verify exact spelling in data |
| `pin` | `pin` | Direct match |
| `skewer` | `skewer` | Direct match |
| `double-check` | `doubleCheck` | camelCase |
| `discovered-attack` | `discoveredAttack` | camelCase |
| `back-rank-mate` | `backRankMate` | camelCase |
| `mate` + named mates | `mate`, `mateIn1`, `mateIn2`, `mateIn3`, `mateIn4`, `mateIn5` | Generic; use `mate` as catch-all |
| `smothered-mate` | `smotheredMate` | camelCase |
| `anastasia-mate` | `anastasiaMate` | camelCase |
| `hook-mate` | `hookMate` | camelCase |
| `arabian-mate` | `arabianMate` | camelCase |
| `boden-mate` | `bodenMate` | camelCase |
| `double-bishop-mate` | (verify in data) | May not appear as labeled theme |
| `dovetail-mate` | `dovetailMate` | camelCase |
| `deflection` | `deflection` | Direct match |
| `attraction` | `attraction` | Direct match |
| `intermezzo` | `intermezzo` | Direct match |
| `x-ray` | `xRayAttack` | camelCase with suffix |
| `interference` | `interference` | Direct match |
| `self-interference` | (none found) | **No lichess equivalent — unvalidated** |
| `clearance` | `clearance` | Direct match |
| `capturing-defender` | `capturingDefender` | camelCase — CONFIRMED in HuggingFace README |
| `sacrifice` | `sacrifice` | Direct match |

**Motifs with no lichess equivalent (D-10 — explicitly unvalidated):**
- `self-interference` — not in the puzzle theme vocabulary
- `double-bishop-mate` — verify in actual data; may be under a different label

**Note**: `hanging-piece` should map to `hangingPiece` but the exact spelling must be verified against the actual CSV column values when the selector script runs.

### Puzzle Dataset Size

The current lichess puzzle database contains approximately 4 million puzzles (as of 2026). A stratified sample of N=50–100 per motif per Rating band (e.g., <1200, 1200–1600, 1600–2000, >2000) would yield ~400–800 puzzles per motif across rating bands, or ~2,000–5,000 total fixtures — offline tests over this count run in seconds.

---

## Harness Architecture (D-07/D-08/D-14)

### Directory Structure

```
scripts/
├── select_tagger_fixtures.py     # one-time selector (reads full puzzle CSV, emits fixture)
tests/
├── scripts/
│   ├── benchmarks/              # existing, excluded from default runs
│   │   ├── conftest.py
│   │   ├── test_chapter1_diff.py
│   │   └── ...
│   └── tagger/                  # NEW — parallel structure to benchmarks/
│       ├── __init__.py
│       ├── conftest.py          # fixture loading helper
│       └── test_detector_precision.py  # precision/recall harness
fixtures/
└── tagger/
    └── detector_fixture.csv     # committed stratified sample (hundreds of rows)
```

### `pyproject.toml` Change (D-14)

Current:
```toml
addopts = "--ignore=tests/scripts/benchmarks"
```

Phase 127:
```toml
addopts = "--ignore=tests/scripts/benchmarks --ignore=tests/scripts/tagger"
```

The directory `tests/scripts/tagger/` and the `--ignore=` entry MUST be committed together (D-14 — no dangling ignore for a non-existent dir).

### `tests/scripts/benchmarks/` Exclusion Pattern

From code read:
- `conftest.py` — `benchmark_session` fixture that skips if benchmark DB unreachable
- Test files: plain pytest tests decorated with `pytestmark = pytest.mark.asyncio`
- Run on demand: `uv run pytest tests/scripts/benchmarks`
- CI: not currently in a dedicated CI step (benchmark tests are local-only)

**For the tagger harness** (D-14): the CI precision gate is a dedicated step targeting `tests/scripts/tagger` with an explicit path. This is the key difference from benchmarks (which are local-only). The harness conftest.py does NOT need a DB connection skip fixture — the harness is entirely offline (reads from the committed fixture CSV). No asyncio needed for the harness itself.

### Selector Script (`scripts/select_tagger_fixtures.py`)

Input: full lichess puzzle CSV (user downloads separately, ~1 GB zst).
Output: `fixtures/tagger/detector_fixture.csv` with columns `PuzzleId, FEN, FirstMove, PV, Themes, Rating`.

Processing:
1. Parse the full CSV (use `csv.reader` or `pandas`)
2. For each row, split `Moves` → `first_move = moves[0]`, `pv = " ".join(moves[1:])`
3. Apply `first_move` to `FEN` to produce `fen_after_first_move` (this is `board_after_flaw`)
4. Filter to puzzles with at least one motif in our motif→theme map
5. Stratified sample: N per (our_motif, rating_band) where rating_band = `<1200 | 1200-1600 | 1600-2000 | >2000`
6. Emit the committed fixture

### Harness Test (`tests/scripts/tagger/test_detector_precision.py`)

For each row in the fixture:
1. Parse `fen_after_first_move` → `chess.Board` (set turn from FEN or apply first_move)
2. Parse `pv` as the refutation PV string
3. Call `detect_tactic_motif(board_after_flaw, pv)`
4. Compare returned `motif_int` against themes in `Themes` column via the motif→theme map

Precision/Recall per motif:
- **Precision**: `true_positives / (true_positives + false_positives)` — among puzzles we tagged motif M, how many actually have theme T(M)?
- **Recall**: `true_positives / (true_positives + false_negatives)` — among puzzles with theme T(M), how many did we tag with motif M?

**D-08 gate**: `assert precision[motif] >= PRECISION_FLOOR[motif]` for each shipped motif. Recall only printed.

**Depth-vs-Rating correlation** (D-06): for puzzles where we detected a motif correctly, compute `correlation(tactic_depth, puzzle_rating)`. Pearson correlation or simple rank correlation; report it. A correlation near 0 flags that the depth dimension is not tracking puzzle difficulty.

---

## CI Integration Pattern

### Current CI (ci.yml)

The default pytest step in CI is:
```yaml
- name: Run pytest
  env:
    DATABASE_URL_TEST: postgresql+asyncpg://postgres:postgres@localhost:5432/flawchess_test
  run: uv run pytest
```

`uv run pytest` reads `pyproject.toml`'s `addopts = "--ignore=tests/scripts/benchmarks"`. Benchmark tests are NOT run in CI (they require the benchmark DB at port 5433, which CI does not spin up).

### Phase 127 CI Addition (D-14)

Add a new dedicated step to `ci.yml` AFTER the default pytest step:
```yaml
- name: Tagger precision gate
  run: uv run pytest tests/scripts/tagger -v
```

This step has NO database dependency (the harness is offline). It requires only the committed fixture CSV and the detector code. It must run on every CI invocation (not skipped in CI).

Key difference from benchmarks: benchmarks need a real DB → local-only. Tagger harness is offline → CI-safe.

---

## Dev Re-Backfill (D-13)

### Existing `backfill_flaws.py` API

```bash
uv run python scripts/backfill_flaws.py --db dev                    # all users
uv run python scripts/backfill_flaws.py --db dev --user-id 28       # single user
uv run python scripts/backfill_flaws.py --db dev --dry-run          # count only
uv run python scripts/backfill_flaws.py --db dev --full-evald-only  # only full-eval'd games
```

The script calls `classify_game_flaws` → `flaw_record_to_row` → `bulk_insert_game_flaws`. Batch size is 100 games per commit. No modification needed — Phase 127 changes flow through `classify_game_flaws` automatically once the detector contract is updated.

### Dev DB Current State (verified via MCP query)

| Metric | Value |
|--------|-------|
| Total `game_flaws` rows | 73,201 |
| Rows with `tactic_motif` set | 32,712 (44.7%) |
| Rows without `tactic_motif` (NULL) | 40,489 |
| Top motif: fork (int=1) | 10,083 |
| Discovered-attack (int=6) | 6,305 |
| Pin (int=3) | 6,299 |
| Skewer (int=4) | 4,778 |
| Clearance (int=15) | 1,614 |
| Back-rank-mate (int=7) | 1,366 |

The re-backfill scope: all 73,201 rows (delete-then-insert makes it idempotent). With batch size 100 and ~30ms per game this is roughly 20–30 minutes for full dev re-backfill. The `--full-evald-only` flag limits to the taggable set.

### `tactic_confidence` Query-Suppression Lever (D-09)

Tier-3 motifs that miss the precision floor are suppressed via the query layer: repositories add `AND tactic_confidence >= :floor` where floor is set high enough to filter out low-confidence tier-3 tags. The `tactic_confidence` column stores 0-100 for tier-3 and 100 for core 8. No schema change or re-backfill needed to adjust the suppression — a constant change in the query layer suffices.

---

## Precision Floor Calibration (D-09)

**CRITICAL: The exact floor value cannot be finalized before a first harness run.**

The CONTEXT.md says "≈ ≥0.90 for core — confirm during planning against measured fixture numbers." This means the plan must sequence:

1. Build harness infrastructure (selector + fixture + test framework)
2. Run selector against full puzzle CSV → generate initial fixture
3. Run harness on the pre-fix detector → measure baseline precision/recall
4. Apply relevance gate (D-01) + min(depth) dispatch (D-02)
5. Run harness on the fixed detector → measure improved precision/recall
6. Set precision floors based on actual measured numbers (≥0.90 for core, ≥0.90 for named mates, tier-3 floor TBD)

**The plan must NOT hardcode 0.90 as a fixed constant before this measurement.** The harness test should define precision floor constants in a separate config file that is populated after the measurement step.

**Expected motifs with no lichess equivalent** (will show recall=N/A and be listed as "unvalidated" in harness output):
- `self-interference`
- Possibly `double-bishop-mate` (verify)

---

## Common Pitfalls

### Pitfall 1: FEN/Moves convention for harness

The FEN in the lichess puzzle CSV is the position BEFORE the opponent's move. The first entry in Moves IS that opponent's move. To feed the detector:
- Apply `Moves[0]` to the FEN board → this yields `board_after_flaw` (the position the detector expects)
- `pv_str = " ".join(Moves[1:])` → the solution is the refutation PV

Getting this wrong (using the raw FEN without applying the first move, or including the first move in the PV) gives the detector the wrong position/line.

### Pitfall 2: `detect_pin` board index to depth mapping

`detect_pin` currently iterates `for board in boards:`. Board index 0 is `board_after_flaw` (no moves played yet from the refuting side's POV). The pin in `boards[k]` means pov delivered the pin at move `k-1`. Depth = `k - 1` if using board index, or equivalently restructure to `for i in range(0, len(moves), 2): board = boards[i]` where depth = `i`.

### Pitfall 3: `detect_boden_or_double_bishop_mate` special shape

This function returns `(TacticMotif | None, int | None)` — NOT `(bool, int | None)`. It is handled separately in the dispatcher outside the loop. Phase 127 must add depth tracking here too; since these are mates (last board), depth = `len(moves)`.

### Pitfall 4: Mate depth semantics (D-03)

For all mate detectors, the mate fires at `boards[-1]` (final board). Depth = `len(moves) - 1` (0-indexed from pov's first move). Since mates are exempt from the depth filter (D-03), the stored depth on mates is correct but purely informational — it does NOT participate in the `min(depth)` dispatch.

### Pitfall 5: `detect_skewer` loop structure

`detect_skewer` iterates `for i in range(1, len(moves)):` (ALL moves) but filters `if i % 2 != 0: continue` to only process pov's moves. Depth when it fires at index `i` = `i`. The loop start at 1 (not 0) means skewer only fires on pov's moves at depth ≥ 1 (never depth 0). This is intentional (skewer needs a second move to expose the piece behind).

### Pitfall 6: `ty` type checking

The Phase 127 signature changes affect every `detect_*` function's return type and the dispatcher's return type. `ty` is enforced in CI (`uv run ty check app/ tests/`). The return type annotations on every `detect_*` and on `detect_tactic_motif` must be updated to the new 4-tuple shapes, or the build will fail.

The module docstring also documents the return convention — update it to reflect the new `(fired, piece, confidence, depth)` contract.

### Pitfall 7: `double-check` depth

`detect_double_check` iterates `for i in range(1, len(boards)):` and filters `if (i % 2) != 1: continue`. When it fires at board index `i`, the corresponding move index is `i - 1`. Depth = `i - 1`.

---

## Architecture Patterns

### Collector Pattern for Min-Depth Dispatch

```python
# In detect_tactic_motif, after mate checks:
Candidate = tuple[int, int | None, int, int, int]  # (priority_rank, piece, confidence, depth, motif_int)
candidates: list[Candidate] = []

# Run all non-mate detectors, collecting firings:
for rank, (motif_str, motif_int) in enumerate(_GEOMETRIC_REGISTRY):
    fired, piece, depth = _GEOMETRIC_DETECTOR_FNS[motif_str](boards, moves, pov)
    if fired:
        candidates.append((rank, piece, TACTIC_CONFIDENCE_HIGH, depth, int(motif_int)))

# Tier-3 with offset rank
for rank_offset, (motif_str, motif_int) in enumerate(_TIER3_REGISTRY):
    fired, piece, confidence, depth = _TIER3_DETECTOR_FNS[motif_str](boards, moves, pov)
    if fired:
        candidates.append((len(_GEOMETRIC_REGISTRY) + rank_offset, piece, confidence, depth, int(motif_int)))

# hanging-piece (Tier 4, highest rank)
hp_fired, hp_piece, hp_depth = detect_hanging_piece(boards, moves, pov)
if hp_fired:
    candidates.append((len(_GEOMETRIC_REGISTRY) + len(_TIER3_REGISTRY), hp_piece, TACTIC_CONFIDENCE_HIGH, hp_depth, TacticMotifInt.HANGING_PIECE))

if candidates:
    # min depth wins; equal-depth ties broken by priority rank (lower rank = higher priority)
    winner = min(candidates, key=lambda c: (c[3], c[0]))
    return winner[4], winner[1], winner[2], winner[3]
```

### Relevance Gate Pattern (Material Delta)

```python
# Gate for detect_fork: fire only if pov gained material by depth i, or i==0
material_at_fire = _material_diff(boards[i + 1], pov)
material_at_start = _material_diff(boards[0], pov)
if material_at_fire <= material_at_start and i > 0:
    continue  # skip this fork — it's in a non-winning continuation
```

This reuses `_material_diff` which already exists and is pure (no I/O, no allocation beyond a few integer additions).

---

## Standard Stack (No New Packages)

Phase 127 introduces no new packages. All work is within the existing stack:

| Tool | Version | Purpose | Status |
|------|---------|---------|--------|
| `python-chess` | 1.11.x | Board manipulation, move parsing | Existing |
| `pytest` | 8.x | Harness test framework | Existing |
| `csv` | stdlib | Fixture file reading | Existing |

The selector script reads a gzip/zstd compressed CSV. The `zstandard` package is already in `[dependency-groups] dev`:
```toml
"zstandard>=0.22",
```
This covers decompressing the `.zst` download (same pattern as `scripts/select_benchmark_users.py`).

---

## Package Legitimacy Audit

No external packages are added in Phase 127. This section is not applicable.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Board state after move | Custom FEN parser | `chess.Board.push()` | python-chess handles castling, en passant, promotion |
| Pin detection | Geometry from scratch | `board.pin(color, sq)` + `chess.BB_ALL` sentinel | python-chess already implements — see Pitfall 2 in existing test file |
| Attack ray detection | Custom ray scanner | `board.attacks(sq)`, `board.attackers(color, sq)` | python-chess |
| Checkmate detection | Custom mate detection | `board.is_checkmate()` | python-chess |
| CSV parsing | Custom parser | `csv.reader` or `pandas` | Stdlib handles quoted fields correctly |
| Pearson correlation | Numpy/scipy | `statistics.correlation` (Python 3.12+ stdlib) | No new dependency needed for a simple correlation |

---

## Open Questions

1. **Exact `hanging-piece` theme name in lichess data**
   - What we know: HuggingFace README lists `hangingPiece` as a theme
   - What's unclear: exact capitalization in actual CSV rows; theme may appear as `hangingPiece` or `hanging`
   - Recommendation: the selector script should print the 50 most common themes when first run, to validate the map

2. **`double-bishop-mate` lichess theme**
   - What we know: confirmed `dovetailMate`, `hookMate`, `arabianMate`, `smotheredMate`, `anastasiaMate`, `bodenMate` — all confirmed from HuggingFace/puzzleTheme.xml
   - What's unclear: whether `double-bishop-mate` has a lichess equivalent (could be `doubleBishopMate` or absent)
   - Recommendation: check during selector run; mark as unvalidated if not found

3. **Precision floor values after first harness run**
   - What we know: CONTEXT.md says ≈0.90 for core
   - What's unclear: actual achievable precision on the fixed detector against CC0 data
   - Recommendation: plan must include a measurement wave before the floor is locked

4. **Fixture size N per stratum**
   - What we know: total puzzle DB is ~4M puzzles; most motifs have hundreds of matching puzzles per rating band
   - What's unclear: exact count available per uncommon motifs (e.g., `dovetail-mate`, `hook-mate`)
   - Recommendation: N=50 per stratum, with a minimum threshold of 10 (if < 10 puzzles found for a stratum, collapse rating bands); log coverage in selector output

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x (existing) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (existing) |
| Quick run command | `uv run pytest tests/scripts/tagger -v` |
| Full suite command | `uv run pytest -n auto` (excludes tagger via addopts) |

### Phase Requirements → Test Map

| Req | Behavior | Test Type | Automated Command | File Exists? |
|-----|----------|-----------|-------------------|-------------|
| SC#1 | Every detector returns depth | Unit | `uv run pytest tests/services/test_tactic_detector.py -x` | Existing (needs update) |
| SC#1 | `tactic_depth` stored in game_flaws | Integration | (dev re-backfill verification) | HUMAN-UAT |
| SC#2 | Precision ≥ floor per motif | Harness | `uv run pytest tests/scripts/tagger -v` | Wave 0 |
| SC#2 | Recall printed per motif | Harness | same | Wave 0 |
| SC#2 | Depth-vs-Rating correlation | Harness | same | Wave 0 |
| SC#3 | Fork/pin precision improves | Harness delta | same | Wave 0 |
| SC#4 | No AGPL code in harness | Code review | `grep -r cook.py tests/ scripts/` | Manual |
| SC#5 | Self-labeled fixture circularity documented | Doc update | Read test docstring | Manual |

### Sampling Rate

- Per task commit: `uv run pytest tests/services/test_tactic_detector.py -x` (fast, catches signature regressions)
- Per wave merge: `uv run pytest -n auto -x` (full default suite, excludes tagger)
- Phase gate: full suite green + `uv run pytest tests/scripts/tagger -v` green

### Wave 0 Gaps

- [ ] `tests/scripts/tagger/__init__.py` — empty file, directory creation
- [ ] `tests/scripts/tagger/conftest.py` — fixture loading helper (loads `fixtures/tagger/detector_fixture.csv`)
- [ ] `tests/scripts/tagger/test_detector_precision.py` — precision/recall harness
- [ ] `fixtures/tagger/detector_fixture.csv` — committed stratified sample (requires selector script run)
- [ ] `scripts/select_tagger_fixtures.py` — one-time selector

---

## Security Domain

`security_enforcement` is not set to false in config; section included. This phase is pure internal data processing (CPU-only detector, offline file reading, no network, no auth). ASVS categories do not meaningfully apply to pure transformation logic on locally-held data.

| ASVS Category | Applies | Notes |
|---------------|---------|-------|
| V2 Authentication | No | No new auth surface |
| V3 Session Management | No | No new sessions |
| V4 Access Control | No | No new endpoints or data access |
| V5 Input Validation | Partial | `pv_str` parsing in detector already guarded by `try/except ValueError` |
| V6 Cryptography | No | No cryptographic operations |

The selector script reads an external CSV download — no network calls, just filesystem I/O. The fixture CSV is committed to git (no runtime download).

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Bool return from detectors | 4-tuple with depth | Phase 127 | Enables min-depth dispatch and depth storage |
| Priority-first dispatch | Min-depth dispatch with priority tiebreak | Phase 127 | Fixes Case-B deep false positives |
| Self-labeled test fixtures | CC0 lichess puzzle harness | Phase 127 | Independent precision/recall ground truth |
| Geometric presence alone | Geometric presence + relevance gate | Phase 127 | Eliminates phantom early/deep hits |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `hanging-piece` maps to `hangingPiece` in lichess theme vocab | Motif→Theme Map | Harness excludes hanging-piece from validation; easily corrected in selector |
| A2 | `double-bishop-mate` has a lichess equivalent theme | Motif→Theme Map | Marked unvalidated; no functional impact |
| A3 | Pearson correlation is computable from ~50-100 samples per stratum | Depth-Rating correlation | May lack statistical power; spearman correlation as fallback |
| A4 | Full puzzle CSV is downloadable as `.zst` (same format as Lichess monthly PGN) | Selector script | `zstandard` already in dev deps; if format differs, use `gzip` fallback |

---

## Sources

### Primary (HIGH confidence)

- Direct code reads: `app/services/tactic_detector.py` (all 1308 lines), `app/services/flaws_service.py` (all 799 lines), `app/models/game_flaw.py`, `app/repositories/game_flaws_repository.py`
- `alembic/versions/20260617_120000_phase_124_tactic_motifs.py` — migration pattern
- `pyproject.toml` — test exclusion pattern
- `.github/workflows/ci.yml` — CI step structure
- `.planning/phases/127-detector-hardening-validation/127-CONTEXT.md` — 14 locked decisions
- `.planning/notes/tactic-detector-precision-gaps.md` — problem record
- `.planning/notes/missed-vs-allowed-tactic-design.md` — depth-as-difficulty rationale
- `.planning/notes/tactic-tagging-architecture.md` — dispatcher priority, motif set, registries

### Secondary (MEDIUM confidence)

- [CITED: database.lichess.org] — FEN/Moves convention, CSV schema, CC0 license
- [CITED: HuggingFace Lichess/chess-puzzles README] — confirmed theme names including `capturingDefender`, `xRayAttack`, `smotheredMate`, `anastasiaMate`, `hookMate`, `arabianMate`, `bodenMate`
- [CITED: lichess puzzleTheme.xml] — confirmed tactical theme names in camelCase

### Tertiary (LOW confidence)

- Dev DB query result: 73,201 total flaws, 32,712 tagged — accurate at time of research (2026-06-19)

---

## Metadata

**Confidence breakdown:**
- Detector code reality: HIGH — all findings from direct code reads
- Integration ripple: HIGH — traced through all affected files
- lichess puzzle format: HIGH — confirmed via official source
- Theme vocabulary: MEDIUM — confirmed core motifs; `hanging-piece` and `double-bishop-mate` need verification in actual data
- Precision floor values: LOW — cannot be determined without first harness run (by design)

**Research date:** 2026-06-19
**Valid until:** 2026-07-19 (stable codebase; lichess puzzle format is stable)
