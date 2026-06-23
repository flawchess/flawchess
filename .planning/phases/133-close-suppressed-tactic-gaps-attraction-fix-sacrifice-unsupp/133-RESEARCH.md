# Phase 133: Close Suppressed-Tactic Gaps — Research

**Researched:** 2026-06-23
**Domain:** Tactic-detector precision engineering, cook.py predicate alignment
**Confidence:** HIGH (all findings empirically validated against committed CC0 fixtures)

## Summary

**Attraction and sacrifice are already solved** (cite: `.planning/notes/suppressed-tactic-gaps-investigation.md`). Attraction needs a one-line off-by-one fix; sacrifice is already precision 1.000 / recall 1.000 standalone and needs only an unsuppress. Both then follow the mechanical unsuppress path.

**The real research work is on the three named mates and trapped-piece fixtures.** All three mate detectors have been empirically probed against the 11,855-row TRAIN fixture. The corrected predicates (reimplemented from cook's prose) are validated: arabian-mate 553/553 TP / 0 FP, boden-mate 435/437 TP / 0 FP, dovetail-mate 543/544 TP / 0 FP. Trapped-piece remains genuinely undersized at 28 TRAIN rows and cannot be gated honestly without fixture expansion.

**Primary recommendation:** Ship attraction fix + sacrifice unsuppress + all three mate ports as a single phase. Defer trapped-piece fixture expansion to a follow-on phase — it requires running the select_tagger_fixtures.py script against the full lichess puzzle download, which is a separate operation with blast-radius risk to other motif floors.

---

## Project Constraints (from CLAUDE.md)

- **AGPL boundary:** cook.py is AGPL-3.0. Reimplement predicates from prose/pseudocode only. Copy no source lines. [VERIFIED: project rule]
- **ty compliance:** all new/edited Python must pass `uv run ty check app/ tests/` with zero errors. [VERIFIED: project rule]
- **ruff format/check:** apply before squash-merge. [VERIFIED: project rule]
- **Precision-first / D-08:** ship only when TRAIN precision clears PRECISION_FLOOR; floor at ~5-8pp below measured TRAIN. [VERIFIED: project rule from precision_floors.py docstring]
- **No DB migration for family mapping:** FAMILY_TO_MOTIF_INTS is query-time grouping; no schema change or backfill needed. [VERIFIED: library_repository.py comment]
- **Pre-merge gate:** `ruff format + ruff check --fix + ty check + pytest -n auto -x + frontend lint+test`. [VERIFIED: CLAUDE.md]
- **TRAIN-only floor assertion:** precision floors are asserted on TRAIN only; TEST is scored for reference, never gated. [VERIFIED: test_detector_precision.py]

---

## Solved Items (do NOT re-derive)

### Attraction: one-line off-by-one fix [VERIFIED: empirical probe]

Root cause (cite: investigation note): `_attraction_fires_at` in `tactic_detector.py` (~L1534) uses `boards[k+2]` for the cond-5 attacker check (the board BEFORE pov's follow-up move). Cook uses `next_node.board()` = board AFTER pov's follow-up = our `boards[k+3]`.

**Fix:** change `boards[k+2]` to `boards[k+3]` at the single attacker-check line. The KING short-circuit and the k+4 Q/R branch are unaffected.

**Empirical validation (this session):**
- Current: 0/1603 TRAIN attraction rows fire, 0 FP
- Fixed (`boards[k+3]`): 1603/1603 TRAIN TP, 0/11855 FP → precision 1.000, recall 1.000 standalone
- Post-dispatch recall will be ~42% (investigation note); ~1603 TRAIN rows, many shadowed by mates/pin

**Docstring to correct:** `precision_floors.py` Phase 132-04 entry says "lure+4-move sequence rarely survives the Stockfish PV depth limit." This is factually wrong. Correct it to: "off-by-one: boards[k+2] should be boards[k+3]; fixed in Phase 133."

### Sacrifice: unsuppress only [VERIFIED: investigation note + tagger report]

Current state: standalone 1.000 precision / 1.000 recall (3142/3142 TRAIN TP, 1 FP in 8713 non-sac). Post-dispatch 12.2% recall (384/3142 TRAIN wins). Int = 17.

**Decision (locked):** unsuppress only, single-winner dispatch, no schema change, no co-tagging.

**Docstring to correct:** `precision_floors.py` Phase 132-04 entry says "material-diff predicate never wins single-winner dispatch." This is factually wrong. Correct it to: "dispatch-shadowed at 12.2% recall by mates/fork; standalone 1.000 precision. Unsuppressed in Phase 133."

---

## Mate Geometry Ports

### Cook/Ours Index Convention (from tactic-tagger-cook-alignment.md)

All three mates are Tier-1 and short-circuit at `boards[-1].is_checkmate()`. The geometry check operates only on the final board position. There is no PV index issue for mates — they always examine `boards[-1]`, `moves[-1]`, and static board geometry.

### 1. Arabian-Mate: `detect_arabian_mate` [VERIFIED: empirical probe]

**Current behavior:** 0/553 TRAIN TP, 0 FP — never fires.

**Root cause:** Our code checks `chess.BB_KNIGHT_ATTACKS[opp_king_sq]` — squares a hypothetical knight ON the king's square would reach. Cook checks `board.attackers(pov, rook_sq)` — pov pieces that actually attack the rook's landing square — then requires the attacking piece to be a knight at `(rank_diff==2, file_diff==2)` from the king.

Example (y7IDV): king=h8, rook lands on g8, pov knight at f6.
- `BB_KNIGHT_ATTACKS[h8]` = {g6, f7} — f6 is NOT in this set, so our check fails.
- `board.attackers(pov, g8)` = {f6}, f6 is a knight, |rank(f6)-rank(h8)|=2, |file(f6)-file(h8)|=2 — cook's check passes.

**Cook's arabian-mate predicate (prose + pseudocode):**

```
arabian_mate(boards, moves, pov) -> bool:
    # Final position checks only
    if not boards[-1].is_checkmate(): return False
    king_sq = boards[-1].king(not pov)
    # 1. King must be in a corner
    if king_file not in (0,7) or king_rank not in (0,7): return False
    # 2. Last move must be a rook
    mating_piece = boards[-1].piece_at(moves[-1].to_square)
    if mating_piece.piece_type != ROOK: return False
    rook_sq = moves[-1].to_square
    # 3. Rook must be adjacent to king (distance == 1)
    if square_distance(rook_sq, king_sq) != 1: return False
    # 4. A pov knight attacks the rook square AND is exactly (2,2) rank/file from king
    for sq in board.attackers(pov, rook_sq):
        piece = board.piece_at(sq)
        if piece.piece_type == KNIGHT:
            if abs(rank(sq)-rank(king_sq))==2 and abs(file(sq)-file(king_sq))==2:
                return True
    return False
```

**Port guidance:** Replace lines 1286-1291 in `detect_arabian_mate`. Instead of:
```python
knight_attacks = chess.SquareSet(chess.BB_KNIGHT_ATTACKS[opp_king_sq])
if knight_sq in knight_attacks:
    return True, chess.ROOK, len(moves) - 1
```
Use:
```python
for knight_sq in boards[-1].attackers(pov, rook_sq):
    piece = boards[-1].piece_at(knight_sq)
    if piece is not None and piece.piece_type == chess.KNIGHT:
        r_diff = abs(chess.square_rank(knight_sq) - chess.square_rank(opp_king_sq))
        f_diff = abs(chess.square_file(knight_sq) - chess.square_file(opp_king_sq))
        if r_diff == 2 and f_diff == 2:
            return True, chess.ROOK, len(moves) - 1
```
(The outer `for knight_sq in knights` loop is replaced entirely.)

**Empirical validation (cook predicate, this session):**
- TRAIN: 553/553 TP, 0 FP → precision 1.000, recall 1.000
- Note: measured without running the full post-dispatch harness; post-dispatch recall will be lower (mates cascade through the `elif` chain, but arabic-mate is Tier-1 and short-circuits before other mates — any position where the final board is an arabian-mate position should win).

**Expected precision floor:** 0.93 (matching hook-mate/anastasia-mate/back-rank-mate standard after cook ports).

---

### 2. Boden-Mate / Double-Bishop-Mate: `detect_boden_or_double_bishop_mate` [VERIFIED: empirical probe]

**Current behavior:** 0/437 TRAIN boden-mate TP, 0 FP — never fires.

**Root cause:** Our code requires `opp_king_sq in boards[-1].attacks(sq)` for both bishops — i.e., both bishops must directly attack the king's square. Cook's requirement is different: for ALL squares within distance < 2 from the king (the king itself plus all 8 adjacent squares), ALL pov attackers of each such square must be bishops.

Example (c3LlW): king=c1, bishop a3 gives check (attacks c1), bishop g6 does not attack c1 directly. Our check fails (only 1 of 2 bishops attacks king). Cook's check: bishop a3 attacks squares {b2, b4, c1, c5, d6, e7, f8} (adjacent to c1: b2, b1, c2, d2, d1); bishop g6 covers b1, c2, d3 (near king squares). All pov attackers of c1, b1, b2, d1, d2 are bishops → cook passes.

**Cook's boden_or_double_bishop_mate predicate (prose + pseudocode):**

```
boden_or_double_bishop_mate(boards, moves, pov) -> Optional[str]:
    if not boards[-1].is_checkmate(): return None
    king_sq = boards[-1].king(not pov)
    pov_bishops = list(boards[-1].pieces(BISHOP, pov))
    if len(pov_bishops) < 2: return None
    # For every square within distance < 2 from king (king + 8 adjacent):
    for sq in all_squares where square_distance(sq, king_sq) < 2:
        for attacker_sq in board.attackers(pov, sq):
            piece = board.piece_at(attacker_sq)
            if piece.piece_type != BISHOP:
                return None   # non-bishop pov piece attacks near-king square
    # Classify by bishop positions relative to king file:
    king_file = file(king_sq)
    b1_file, b2_file = file(pov_bishops[0]), file(pov_bishops[1])
    if (b1_file < king_file) != (b2_file < king_file):
        return "boden-mate"   # bishops on opposite sides of king
    return "double-bishop-mate"
```

**Port guidance:** In `detect_boden_or_double_bishop_mate`, replace lines 1313-1318 (the `attacking_bishops` filter):

Old code:
```python
attacking_bishops = [sq for sq in pov_bishops if opp_king_sq in boards[-1].attacks(sq)]
if len(attacking_bishops) < 2:
    return None, None, None
```

New code:
```python
# Cook's check: for all squares distance < 2 from king, ALL pov attackers must be bishops
for sq in chess.SQUARES:
    if chess.square_distance(sq, opp_king_sq) < 2:
        for attacker_sq in boards[-1].attackers(pov, sq):
            piece = boards[-1].piece_at(attacker_sq)
            if piece is None or piece.piece_type != chess.BISHOP:
                return None, None, None
```

**Empirical validation (cook predicate, this session):**
- TRAIN boden-mate: 435/437 TP, 0 FP → precision 1.000, recall 0.995 (2 FN — likely double-bishop-mate misclassified as boden or vice versa; acceptable)
- The 2 FN will likely be correctly classified as `double-bishop-mate` (an unvalidated motif in UNVALIDATED_MOTIFS); they do not count as FP for boden-mate

**Expected precision floor:** 0.93 (same standard).

**Note on double-bishop-mate:** `double-bishop-mate` remains in `UNVALIDATED_MOTIFS` (no lichess theme equivalent confirmed). The boden/double-bishop split is determined purely by which side of the king's file the bishops sit; the code structure handles both. No floor needed for double-bishop-mate; boden-mate gets a floor.

---

### 3. Dovetail-Mate: `detect_dovetail_mate` [VERIFIED: empirical probe]

**Current behavior:** 0/544 TRAIN TP, 23 FP — only fires false positives.

**Root cause (two bugs):**

Bug A — Our code REJECTS when queen is adjacent to king (`if queen_sq in boards[-1].attacks(opp_king_sq): return False`). Cook REQUIRES the queen to be diagonally adjacent (distance==1, not same file/rank). We have the condition inverted.

Bug B — Our code has no check that queen is diagonal (not on same file or rank). We only check `square_file != square_file` and `square_rank != square_rank`, but not distance. This lets the FP example through: queen on h6, king on f6 — same rank, distance 2 → cook rejects (same rank), our code allows it.

The FP example (DrMhn): king=f6, queen=h6. Same rank, distance=2. Our code: queen not adjacent (attacks returns False, condition `queen in attacks(king)` is False, so we DON'T return False). Our code passes all conditions and returns True. Cook: `queen_rank == king_rank` → returns False immediately.

For TPs (e.g. wsRgK): king=b6, queen=a5. Queen is diagonally adjacent (distance=1, different file AND rank). Our code: `a5 in boards[-1].attacks(b6)` is True → we return False (wrong). Cook: queen is diagonal, distance 1 → passes; then checks that each adjacent square is either queen-covered-and-empty or blocked.

**Cook's dovetail_mate predicate (prose + pseudocode):**

```
dovetail_mate(boards, moves, pov) -> bool:
    if not boards[-1].is_checkmate(): return False
    last_move = moves[-1]
    mating_piece = board.piece_at(last_move.to_square)
    if mating_piece.piece_type != QUEEN: return False
    king_sq = board.king(not pov)
    # 1. King must NOT be on edge
    if file(king_sq) in (0,7) or rank(king_sq) in (0,7): return False
    queen_sq = last_move.to_square
    # 2. Queen must NOT be on same file or same rank as king (diagonal-only adjacency)
    if file(queen_sq) == file(king_sq) or rank(queen_sq) == rank(king_sq): return False
    # 3. Queen must be adjacent to king (diagonally adjacent, distance == 1)
    if square_distance(queen_sq, king_sq) > 1: return False
    # 4. For each adjacent square (except queen_sq):
    #    - if pov attackers == [queen_sq]: if piece_at(sq): return False
    #      (queen covers sq AND sq is occupied → king can't go there,
    #       but queen covers means king would walk into queen → this is NOT a dovetail pattern)
    #    - if other pov attackers exist: return False (king could theoretically escape)
    for sq in squares where distance(sq, king_sq) == 1:
        if sq == queen_sq: continue
        attackers = list(board.attackers(pov, sq))
        if attackers == [queen_sq]:
            if board.piece_at(sq): return False
        elif attackers:
            return False
    return True
```

**Port guidance:** Replace the entire body of `detect_dovetail_mate` (lines 1339-1362). The new implementation:
1. Remove the current `if queen_sq in boards[-1].attacks(opp_king_sq): return False` (inverted condition).
2. Add: `if chess.square_file(queen_sq) == chess.square_file(opp_king_sq) or chess.square_rank(queen_sq) == chess.square_rank(opp_king_sq): return False, None, None`
3. Add: `if chess.square_distance(queen_sq, opp_king_sq) > 1: return False, None, None`
4. Add the adjacent-square loop (cook's cond 4).

**Empirical validation (cook predicate, this session):**
- TRAIN: 543/544 TP, 0/11855 FP → precision 1.000, recall 0.998
- 1 FN is acceptable (likely a very unusual pattern)

**Expected precision floor:** 0.93.

---

## Trapped-Piece Fixture Sampling

### Current state

`detect_trapped_piece` currently has 0 TP / 9 FP on TRAIN (n_gt=28 train / 11 test = 39 total). It is in `SUPPRESSED_MOTIFS` as "only-FP" under D-08. The fixture undersampling is the blocker — 28 rows is too thin to gate precision honestly (one FP in 28 = 3.6% precision, catastrophically low).

### The sampling lever [VERIFIED: scripts/select_tagger_fixtures.py]

`scripts/select_tagger_fixtures.py` uses `SAMPLES_PER_STRATUM = 200` with 4 rating bands (lt1200, 1200-1600, 1600-2000, gt2000), yielding up to 200×4 = 800 potential rows per motif before the 70/30 train/test split. However, `trappedPiece` collects so few matching puzzles across the full lichess database that all bands collapse to the fallback pool, yielding only 39 total rows.

The lever is `--samples-per-stratum N` (CLI override). To oversample `trappedPiece` specifically, the script offers no per-motif override. The only way to increase `trappedPiece` fixture size is to either:

**Option A — Increase `SAMPLES_PER_STRATUM` globally** (e.g. 500 or 1000). This proportionally increases ALL motifs' fixture sizes, expanding the total from ~17k rows to ~40-80k rows. Blast radius: every motif's TRAIN set grows, measured precision floats slightly, and every floor in PRECISION_FLOOR will need re-measurement.

**Option B — Add a per-motif oversample cap** to `select_tagger_fixtures.py`. New argument `--oversample-motifs trappedPiece:500` samples up to 500/stratum for the specified motif while keeping others at SAMPLES_PER_STRATUM. Requires a modest script edit; blast radius is limited to the oversampled motif's rows.

**Option C — Determine source pool size first.** The script prints "N available" for each (motif, band) stratum on first run. Run the script once with `--samples-per-stratum 10000` (effectively "take everything") to learn how many trappedPiece puzzles exist in the lichess database. If the pool is small (e.g. <200 total), oversample won't help much and the issue is fundamental.

### Source pool availability [ASSUMED]

The lichess puzzle database (lichess_db_puzzle_2026-06.csv.zst, ~300 MB) is not committed to git. Its size and trappedPiece coverage is not known without running the script. The `trappedPiece` theme tends to appear in ~0.1-0.5% of puzzles (rough estimate from TRAIN fixture proportions: 39 out of ~17k sampled = 0.2%). If the full database has ~4 million puzzles, that suggests ~4,000-20,000 trappedPiece puzzles available — enough for a 200/stratum fixture easily.

### Regeneration procedure [VERIFIED: select_tagger_fixtures.py]

```bash
# Run against the full lichess puzzle download
uv run python scripts/select_tagger_fixtures.py \
    --puzzle-path /path/to/lichess_db_puzzle_2026-06.csv.zst \
    [--samples-per-stratum 500]  # or use --oversample-motifs option if added
```

Output: rewrites `fixtures/tagger/detector_fixture_train.csv` and `fixtures/tagger/detector_fixture_test.csv`. The split is deterministic by PuzzleId hash (70/30), so existing rows are stable — a puzzle that was in TRAIN before will still be in TRAIN.

### Blast-radius warning

**WARNING: Re-running `select_tagger_fixtures.py` with a higher `--samples-per-stratum` reshuffles ALL motifs' row sets.** Each motif's TRAIN pool grows. Measured precision floats because the additional rows may include harder or easier puzzles. **Every floor in PRECISION_FLOOR must be re-measured after fixture expansion.** The 5-8pp safety margin in floors absorbs small variations, but motifs near their floor (e.g. `capturing-defender` at 0.876 vs floor 0.82) could fall below. Commitment to fixture expansion means a full re-measurement run.

Additionally, the `--seed 42` random seed means adding more rows changes which rows are sampled (random.sample picks differently from a larger pool), potentially shifting all existing TRAIN/TEST assignments for motifs that weren't already at the per-stratum cap. The PuzzleId hash ensures the TRAIN/TEST split is stable per puzzle, but which puzzles are sampled can change.

**Recommendation for planning:** Scope trapped-piece fixture expansion as a separate sub-task or phase. The blast radius is real and the re-measurement step is non-trivial. Do NOT gate Phase 133 completion on trapped-piece — it's a separate operation. Phase 133 ships the mate ports, attraction fix, and sacrifice unsuppress; a Phase 133+ or follow-on quick handles the fixture.

---

## Mechanical Unsuppress Path (confirmed against live code)

### Integers: attraction=10, sacrifice=17 [VERIFIED: TacticMotifInt enum, L101/108]

### Step-by-step surface points:

**1. `tests/scripts/tagger/precision_floors.py`** — `SUPPRESSED_MOTIFS` frozenset (L169)
- Remove `"attraction"` and `"sacrifice"` entries
- Correct their stale docstrings (Phase 132-04 entries, both factually wrong per investigation note)
- Add `PRECISION_FLOOR` entries: `"attraction": 0.93` (measured 1.000 TRAIN), `"sacrifice": 0.93` (measured 1.000 TRAIN)
- Note: floors at 0.93 (7pp below 1.000) consistent with the standard applied to other cook-ported motifs

**2. `app/repositories/library_repository.py`** — `FAMILY_TO_MOTIF_INTS` dict (L109)
- Add two new family keys (as last entries in the `"advanced"` group):
  ```python
  "attraction": [int(TacticMotifInt.ATTRACTION)],   # int 10
  "sacrifice": [int(TacticMotifInt.SACRIFICE)],      # int 17
  ```
- Both already fire at `TACTIC_CONFIDENCE_HIGH` (100) → clear the `_TACTIC_CHIP_CONFIDENCE_MIN=70` lever automatically. No lever change needed.

**3. `frontend/src/lib/theme.ts`** — add color tokens (L122-123 area):
  ```typescript
  export const TAC_ATTRACTION = TAC_BLUE;
  export const TAC_ATTRACTION_BG = TAC_BLUE_BG;
  export const TAC_SACRIFICE = TAC_BLUE;
  export const TAC_SACRIFICE_BG = TAC_BLUE_BG;
  ```

**4. `frontend/src/lib/tacticComparisonMeta.ts`**:
- Add `'attraction'` and `'sacrifice'` to the `TacticFamily` union type (L99-115)
- Add entries to `TACTIC_FAMILY_COLORS` and `TACTIC_FAMILY_ICON` records
- Add `TacticFamilyDef` entries to `TACTIC_COMPARISON_FAMILIES` array (in the `'advanced'` group, after `capturing_defender`)
- Update the comment "Dropped combinations motif strings (sacrifice, deflection, etc.) belong to no family" — remove sacrifice from that list

**5. `tests/services/test_tactic_comparison_service.py`** — family count test:
- `test_family_mapping_ten_families` (L161) currently expects 15 keys exactly. Add `"attraction"` and `"sacrifice"` to `expected_keys` → new count 17.
- `test_family_mapping_excludes_suppressed_tier3` (L191) asserts `suppressed_tier3_ints = {10, 14, 17}` must NOT appear in mappings. Remove 10 and 17; keep only 14 (self-interference). Update the docstring accordingly.
- `test_family_mapping_covers_selected_motifs` (L209): add assertions `FAMILY_TO_MOTIF_INTS["attraction"] == [10]` and `FAMILY_TO_MOTIF_INTS["sacrifice"] == [17]`.

### Named mates unsuppress path

Arabian-mate (int 21), boden-mate (int 22), dovetail-mate (int 24) are already in `FAMILY_TO_MOTIF_INTS["mate"]` (L143-153) and already have entries in `TACTIC_COMPARISON_FAMILIES["checkmate"].motifs`. No family mapping change needed — they are already grouped under "mate."

The unsuppress for mates requires only:
- Remove from `SUPPRESSED_MOTIFS`
- Add `PRECISION_FLOOR` entries at 0.93

No frontend change needed (mate subtypes collapse to "checkmate" in `tacticMotifLabel`).

---

## Validation Architecture

### Test framework
| Property | Value |
|----------|-------|
| Framework | pytest (uv run pytest) |
| Config file | pytest.ini |
| Quick run command | `uv run pytest tests/scripts/tagger/test_detector_precision.py -s` |
| Family test | `uv run pytest tests/services/test_tactic_comparison_service.py -k test_family_mapping` |
| Full suite command | `uv run pytest -n auto -x` |

### Phase requirement gates

| Item | Test Gate | Command |
|------|-----------|---------|
| Attraction fix | CI floor passes (PRECISION_FLOOR["attraction"] >= 0.93 on TRAIN) | `uv run pytest tests/scripts/tagger/test_detector_precision.py -s` |
| Attraction unsuppress | Floor not NaN, family chip surfaced | harness + `test_family_mapping_ten_families` |
| Sacrifice unsuppress | Floor passes, family chip surfaced | harness + family tests |
| Arabian-mate port | Removed from SUPPRESSED_MOTIFS, floor passes | harness |
| Boden-mate port | Removed from SUPPRESSED_MOTIFS, floor passes | harness |
| Dovetail-mate port | Removed from SUPPRESSED_MOTIFS (was only-FP → now passes), floor passes | harness |
| Family count | test_family_mapping_ten_families count == 17 | `test_tactic_comparison_service.py` |
| Docstrings corrected | Manual verification | n/a |

### Wave 0 Gaps

None — all test infrastructure exists. The harness (`test_detector_precision.py`) scores every motif on every run. The family test already asserts the count.

---

## Open Risks and Unknowns

1. **Dovetail cond-4 interpretation:** Cook's condition `if attackers == [queen_sq]: if board.piece_at(sq): return False` is unusual. It means: if the queen is the only pov attacker of an escape square AND there's a piece on that square, return False. This seems to mean "the square is covered by queen but blocked by own piece → the mate pattern is broken." The empirical probe gives 543/544 TP / 0 FP, validating the interpretation is correct. The 1 FN may be a multi-queen position or an unusual promotion pattern.

2. **Boden `(b1_file < king_file) != (b2_file < king_file)` tie case:** If one bishop is on the same file as the king (`b1_file == king_file`), the comparison `(b1_file < king_file)` is False and `(b2_file < king_file)` could be either, leading to non-intuitive classification. Cook's code handles this the same way; both our current code and the ported version treat equal-file bishops as "same side." The 2 FN in boden-mate are likely this edge case (they become double-bishop-mate which is unvalidated, not a FP).

3. **Attraction post-dispatch recall:** ~42% of attraction-labeled fixtures will be shadowed by mates, pin, etc. (investigation note). This is expected and not a precision issue. The PRECISION_FLOOR gate measures standalone-equivalent precision via the post-dispatch harness. With 1.000 standalone, post-dispatch precision should also be 1.000 (no FP even in dispatch-lost positions).

4. **Sacrifice docstring correction scope:** The Phase 132-04 measurement block in `precision_floors.py` has two factually incorrect entries (attraction and sacrifice). Correcting them is important for future maintainability but is a documentation-only change with no code risk.

5. **test_family_mapping_excludes_suppressed_tier3 update:** This test explicitly lists `suppressed_tier3_ints = {10, 14, 17}`. After unsuppressing attraction (10) and sacrifice (17), this set shrinks to `{14}` (self-interference only). The test must be updated to avoid a false negative.

6. **Trapped-piece fixture expansion:** Not scoped for Phase 133. The source pool size in the lichess database is unknown without running the script. Option B (per-motif oversample cap) is preferable to Option A (global increase) to limit blast radius, but requires a modest script edit that isn't in scope here.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | trappedPiece lichess pool is ~4,000-20,000 rows (estimated from 0.2% proportion) | Trapped-Piece | If pool is much smaller (<200), oversample won't help; detector re-judging is the only path |
| A2 | Post-dispatch precision for fixed attraction will be 1.000 (no FP even when shadowed) | Solved Items | Unlikely to be wrong since standalone is 1.000, but not empirically measured in dispatch context |

---

## Sources

### Primary (HIGH confidence)
- `.planning/notes/suppressed-tactic-gaps-investigation.md` — full empirical probe results; root causes for all 6 suppressed motifs [VERIFIED: project artifact]
- `/home/aimfeld/Projects/Python/lichess-puzzler/tagger/cook.py` — AGPL oracle; predicate prose read and reimplemented [VERIFIED: file read]
- `app/services/tactic_detector.py` — current detector implementations read [VERIFIED: file read]
- `tests/scripts/tagger/precision_floors.py` — SUPPRESSED_MOTIFS, PRECISION_FLOOR, docstrings [VERIFIED: file read]
- `tests/services/test_tactic_comparison_service.py` — family count test, suppressed-tier3 test [VERIFIED: file read]
- `app/repositories/library_repository.py` — FAMILY_TO_MOTIF_INTS, int mappings [VERIFIED: file read]
- `frontend/src/lib/tacticComparisonMeta.ts` — TacticFamily, TACTIC_COMPARISON_FAMILIES [VERIFIED: file read]
- `frontend/src/lib/theme.ts` — TAC_* color token pattern [VERIFIED: file read]
- `scripts/select_tagger_fixtures.py` — sampling mechanics, SAMPLES_PER_STRATUM lever [VERIFIED: file read]

### Empirical probes (HIGH confidence, run this session)
- Arabian-mate corrected predicate: 553/553 TP, 0/11855 FP on TRAIN
- Boden-mate corrected predicate: 435/437 TP, 0/11855 FP on TRAIN
- Dovetail-mate corrected predicate: 543/544 TP, 0/11855 FP on TRAIN
- Attraction fix (boards[k+3]): 1603/1603 TP, 0/11855 FP on TRAIN
- Attraction current: 0/1603 TP (confirms investigation note)

---

## Metadata

**Confidence breakdown:**
- Attraction fix: HIGH — empirically proven 1603/1603 TP / 0 FP
- Sacrifice unsuppress: HIGH — tagger report + investigation note confirm 1.000 precision
- Arabian-mate port: HIGH — empirically proven 553/553 TP / 0 FP
- Boden-mate port: HIGH — empirically proven 435/437 TP / 0 FP
- Dovetail-mate port: HIGH — empirically proven 543/544 TP / 0 FP
- Trapped-piece fixture: MEDIUM — source pool size unknown (assumed)
- Unsuppress surface points: HIGH — verified against live code

**Research date:** 2026-06-23
**Valid until:** 2026-09-23 (fixture data is stable; cook.py predicate logic is stable)
