# Phase 134: trapped-piece fixture expansion (Option B) + cook-predicate reimplementation, conditional unsuppress — Research

**Researched:** 2026-06-23
**Domain:** chess tactic detection (python-chess), CC0 fixture sampling, precision-floor gating
**Confidence:** HIGH (every claim cross-checked against source with file:line; no external packages introduced)

## Summary

trapped-piece is the single biggest false-positive source in the tactic tagger today: **0 TP / 153 FP, P 0.000** in the combined report `[VERIFIED: reports/tactic-tagger/tactic-tagger-2026-06-23.md:42]`, and only `28 TRAIN / 11 TEST = 39` ground-truth labels `[VERIFIED: same report L74]`. It is held out of users by `SUPPRESSED_MOTIFS` `[VERIFIED: tests/scripts/tagger/precision_floors.py:204]` and (redundantly) by the `_TACTIC_CHIP_CONFIDENCE_MIN` query lever. The fixture is too thin to gate honestly — one FP tanks precision — so the path is: **(1)** expand the `trappedPiece` fixture to ~1000 via a *per-motif* oversample cap that leaves every other motif's selected rows byte-identical (Option B / D-EXP-02); **(2)** reimplement `detect_trapped_piece` from cook's `util.is_trapped` predicate (prose only, AGPL boundary); **(3)** conditionally unsuppress only if precision clears ~≥0.80 TRAIN holding on TEST (D-EXP-03).

The key structural facts that shape this plan: the detector and the **family map + frontend chip already exist** for trapped-piece (Phase 129's 10-family taxonomy added `trapped_piece` to both `FAMILY_TO_MOTIF_INTS` `[VERIFIED: app/repositories/library_repository.py:137]` and `tacticComparisonMeta.ts` `[VERIFIED: frontend/src/lib/tacticComparisonMeta.ts:260]`). So the "unsuppress mechanical path" for this motif is *smaller* than the generic Phase 133 path — only `SUPPRESSED_MOTIFS` removal + a `PRECISION_FLOOR` add + the `GOALS` entry are actually needed; the family/chip edits are already done. Both the CI harness and the report score the **post-dispatch winner** (`detect_tactic_motif`), not standalone firing, which bounds trapped-piece's achievable recall and is the dominant landmine.

**Primary recommendation:** Three-wave plan — (W1) add `--oversample-motifs` to `select_tagger_fixtures.py`, run it against a fresh lichess `.csv.zst`, regenerate fixtures, verify byte-identical isolation via `git diff`, re-measure only the floors the multi-label leakage actually moved; (W2) reimplement `detect_trapped_piece` from cook's `is_trapped` prose, iterate via `--check-goals`; (W3) conditional unsuppress gated on ~≥0.80. Treat ≥0.80 as a real possibility but not a certainty — cook curates its solution lines; we run a raw Stockfish PV.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Fixture sampling (per-motif cap) | Python maintenance script (`scripts/`) | — | Offline, one-shot; not request-path. Reads uncommitted `.csv.zst`, writes committed CSVs |
| Trapped-piece detection | Backend service (`app/services/tactic_detector.py`) | — | Pure-CPU, no DB/engine call; runs inside `detect_tactic_motif` dispatch |
| Precision gate / floors | Test layer (`tests/scripts/tagger/`) | — | CI assertion on TRAIN; the authoritative ship/suppress signal |
| Unsuppress wiring | Test floor table + repo family map + frontend meta | — | Family map + chip already present; only floor table + GOALS need edits |
| Goal-seeking loop | `scripts/tactic_tagger_report.py --check-goals` | — | Drives `/loop`; scores post-dispatch winner |

No HTTP, no migration, no schema change in this phase. `game_flaws` stores raw motif INTs; families are query-time grouping `[VERIFIED: app/repositories/library_repository.py:101-103]`.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| (none mapped) | Traceability via CONTEXT.md decisions; phase has no formal REQ IDs. D-EXP-01/02/03 are the locked decisions (see User Constraints). | This research documents the cook predicate, the Option-B cap design, the multi-label leakage scope, the mechanical unsuppress path, and the precision gate. |

## User Constraints (from ROADMAP Phase 134 — no CONTEXT.md exists yet)

> This phase has **no CONTEXT.md** (discuss-phase skipped). Locked decisions live in the ROADMAP Phase 134 block, copied verbatim below. Treat them with the authority of CONTEXT.md `## Decisions`.

### Locked Decisions (from /gsd-explore 2026-06-23)

- **D-EXP-01 — Target is trapped-piece, NOT hanging-piece.** The original request named "hanging-piece," but hanging-piece already ships healthy (Tier 4, floor 0.90, P 0.915/0.889, R 0.69). trapped-piece is the actual gap Phase 133 deferred. **Do not touch hanging-piece.** `[VERIFIED: ROADMAP L454; hanging-piece P 0.915/0.889 R 0.688/0.706 at report L51]`
- **D-EXP-02 — Per-motif cap (Option B), not a global resample.** A global `SAMPLES_PER_STRATUM` bump reshuffles all fixtures and re-measures every floor; Option B isolates the change to the oversampled motifs. **Caveat:** isolation is near-total but NOT perfect — new `trappedPiece` puzzles are multi-label and nudge co-occurring motifs' GT counts slightly; verify which committed floors actually move and re-measure only those. `[VERIFIED: ROADMAP L455]`
- **D-EXP-03 — Unsuppress only if it clears a floor.** No forced ship. ~≥0.80 TRAIN holding on TEST is the bar; below it, keep suppressed with the improved detector + fixtures committed (still removes the FP source from the eventual ship surface and leaves a real test set). `[VERIFIED: ROADMAP L456]`

### Claude's Discretion
- Detector internals (how to translate cook's `is_trapped` prose into our `boards[]`/PV-array convention).
- The exact `--oversample-motifs` CLI surface and the per-motif cap value (≥1000 target for trapped-piece; soft top-ups for en-passant/promotion/under-promotion as far as the lichess DB allows).
- Whether to top up the other thin motifs in the same run or a separate run.

### Deferred Ideas (OUT OF SCOPE)
- hanging-piece changes (D-EXP-01).
- Global `SAMPLES_PER_STRATUM` increase (D-EXP-02 rejects Option A).
- Any dispatch rework — Phase 131 already inverted to shallowest-wins.
- Prod re-backfill / live-wrong-tag urgency — tactic tagging is not yet in prod.
- Co-tag / multi-label motif surfacing (rejected for sacrifice in Phase 133; not in scope here).

## Standard Stack

No new packages. This phase is entirely internal to existing modules.

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| python-chess | 1.11.x | board, legal_moves, attackers, pin detection | Already the project chess engine `[CITED: CLAUDE.md Tech Stack]` |
| zstandard | (installed) | stream-read the lichess `.csv.zst` | Already imported in `select_tagger_fixtures.py` `[VERIFIED: scripts/select_tagger_fixtures.py:55]` |
| pytest (+ pytest-xdist) | — | harness + floor gate | Existing test infra |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| hashlib (stdlib) | — | deterministic SHA-1 PuzzleId split | Already used `[VERIFIED: scripts/select_tagger_fixtures.py:332]` |
| csv (stdlib) | — | fixture read/write | Already used |

**Installation:** none required.

## Package Legitimacy Audit

> Not applicable — this phase installs no external packages. All code lives in existing modules using already-vendored dependencies (python-chess, zstandard, stdlib).

## Architecture Patterns

### System Architecture Diagram

```
                  ┌────────────────────────────────────────────────────────┐
   lichess        │  scripts/select_tagger_fixtures.py  (OFFLINE, one-shot) │
   db_puzzle  ───▶│  stream .csv.zst → _puzzle_motifs(themes) match          │
   .csv.zst       │     → _stratified_sample(per-motif cap)  ◀── NEW: cap    │
   (~300MB,       │     → _split_train_test(SHA-1 PuzzleId hash, 70/30)      │
    uncommitted)  │     → write detector_fixture_{train,test}.csv (COMMITTED)│
                  └───────────────────────────┬────────────────────────────┘
                                              │ committed fixtures
                                              ▼
   ┌──────────────────────────────────────────────────────────────────────┐
   │  detect_tactic_motif(board, pv)   (app/services/tactic_detector.py)    │
   │   _parse_pv → boards[], moves[]                                         │
   │   Tier1 mates short-circuit → else collect all firings →               │
   │   DEPTH-PRIMARY, then TIER, then RANK sort  (shallowest-wins, P131)     │
   │   ▲ detect_trapped_piece (Tier 2, rank 6) competes here  ◀── REWRITE    │
   └───────────────┬──────────────────────────────┬───────────────────────┘
                   │ post-dispatch winner          │ post-dispatch winner
                   ▼                                ▼
   ┌──────────────────────────┐     ┌────────────────────────────────────────┐
   │ test_detector_precision  │     │ tactic_tagger_report.py --check-goals    │
   │  TRAIN floor gate (CI)    │     │  GOALS table → exit 1 until met (/loop)  │
   │  PRECISION_FLOOR assert   │     │  --eval-set train|test                   │
   └──────────────────────────┘     └────────────────────────────────────────┘
```

Both consumers feed off `detect_tactic_motif` — the **post-dispatch winner**, not the standalone `detect_trapped_piece` `[VERIFIED: tests/scripts/tagger/test_detector_precision.py:92; scripts/tactic_tagger_report.py:203]`.

### Pattern 1: Cook full-port-then-suppress (the 131/132/133 playbook)
**What:** Reimplement cook's exact relational predicate from prose (no source copy), measure on TRAIN, ship if it clears the bar, otherwise suppress. Floors set ~5-8pp below measured TRAIN, rounded to 0.05.
**When to use:** Every motif precision-hardening in this milestone.
**Evidence:** `[VERIFIED: tests/scripts/tagger/precision_floors.py:174-176]` (floor band) and the 131-03/132/133 measurement blocks at L51-135.

### Pattern 2: Per-PuzzleId deterministic split = isolation guarantee
**What:** Each puzzle lands in TRAIN or TEST by `sha1(PuzzleId) % 100 < round(test_fraction*100)` `[VERIFIED: scripts/select_tagger_fixtures.py:326-334]`. Stable across runs, sample sizes, seeds. This is *why* Option B can keep other motifs' rows identical: if the per-motif cap doesn't change which PuzzleIds get sampled for an unaffected motif, those rows are byte-for-byte identical AND on the same side of the split.

### Anti-Patterns to Avoid
- **Don't tune the detector against 28 rows.** Expand the fixture first, then re-judge `[VERIFIED: .planning/notes/suppressed-tactic-gaps-investigation.md:51-52]`.
- **Don't raise `SAMPLES_PER_STRATUM` globally** (Option A) — rejected by D-EXP-02; it reshuffles every motif's pool and forces re-measuring every floor.
- **Don't add a dispatch rework** — Phase 131 already inverted to shallowest-wins; trapped-piece stays Tier 2 rank 6.
- **Don't change hanging-piece** (D-EXP-01).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| "Is this piece trapped?" | A from-scratch escape enumerator | Port cook's `util.is_trapped` predicate (prose) | cook's predicate is the AGPL oracle the CC0 labels were generated by; matching it maximizes precision |
| "Is a piece defended (incl. X-ray)?" | New ray-defense logic | Existing `_is_defended` `[VERIFIED: tactic_detector.py:291]` | Already a faithful `util.is_defended` port |
| "Is a piece in a bad spot?" | New attacked-and-loose check | Existing `_is_in_bad_spot` `[VERIFIED: tactic_detector.py:318]` | Already a faithful `util.is_in_bad_spot` port |
| Train/test split | Re-roll random seeds | Existing SHA-1 PuzzleId hash `[VERIFIED: select_tagger_fixtures.py:326]` | Deterministic isolation is load-bearing for Option B |
| Family→ints + chip wiring | Re-add the chip | Already present for trapped_piece | Phase 129 10-family taxonomy already wired it |

**Key insight:** The two helpers cook's `is_trapped` calls (`is_in_bad_spot`, the legal-escape loop) already exist in our codebase as faithful ports. The reimplementation is mostly *re-assembling* those helpers into cook's exact `is_trapped` shape — not new geometry.

## Cook's trapped-piece predicate (PROSE ONLY — AGPL boundary, no source copy)

> Reimplement from this description. Copy NO source from `cook.py`/`util.py` (131 D-10). `[CITED: lichess-puzzler/tagger/cook.py def trapped_piece; util.py def is_trapped]`

**cook's `trapped_piece(puzzle)` driver (the call-site shape):**
Cook scans the player's moves in the solution line starting from the second player move. For each such player move, it looks at the square the player moved *to* and asks: did the player just *capture* a non-pawn piece there? If so, it identifies the relevant square as follows — if the immediately preceding opponent move also landed on that same square (i.e. the opponent had just moved that piece there), then the "trapped" square of interest is the square that opponent piece came *from*; otherwise it is the capture square itself. It then asks whether, on the board *before* that preceding opponent move, the piece on that square-of-interest was trapped (`is_trapped`). If yes → the puzzle is tagged trappedPiece.

The conceptual claim: **a piece is "trapped" if, the move before it was won, it had no safe square to flee to** — the player then simply collected it.

**cook's `util.is_trapped(board, square)` predicate (the core test — this is what `detect_trapped_piece` must mirror):**
Given a board and the square of the candidate (opponent) piece, return True only when ALL of the following hold:
1. The board is **not in check** and the piece on `square` is **not pinned** (a pinned or in-check piece's immobility is a different motif, excluded).
2. The piece is **not a pawn and not a king** (only N/B/R/Q can be "trapped" in this sense).
3. The piece **is currently in a bad spot** (`is_in_bad_spot`: it is attacked AND either hanging or capturable by a strictly-lower-value non-king attacker).
4. For **every legal move of that piece** (escape candidates):
   - If the escape square holds a capturable piece worth **≥** the trapped piece's own value, the escape is *good* → NOT trapped (it can trade up or equal). Return False.
   - Otherwise push the escape and check: if the piece is **not in a bad spot** on the new square, that escape is *safe* → NOT trapped. Return False (then pop).
5. If no escape avoided a bad spot (and none captured an equal-or-greater piece) → the piece is **trapped**. Return True.

Implicit: if the piece has **no legal moves at all**, cook's loop never returns False inside it, so `is_trapped` returns True for an immobile-but-attacked non-pawn/non-king that is in a bad spot and not pinned/in-check. (This differs from our current detector — see the divergence note below.)

**How trapped-piece differs from hangingPiece (cook):**
- `hanging_piece` fires when the player's *first* solution move captures a non-pawn piece that was **already hanging** (undefended) at the start — a free capture, no escape needed `[CITED: cook.py def hanging_piece]`.
- `trapped_piece` fires deeper in the line: the piece was **not** capturable for free, but it had **no safe escape**, so it gets rounded up over the next moves. The defining contrast is **"capturable now for free" (hanging) vs. "has moves but all moves lose material / stay in a bad spot" (trapped)** `[VERIFIED: this contrast is already encoded in our docstring, tactic_detector.py:934-935]`.

## Current `detect_trapped_piece` — why it fires 0 TP / 153 FP

**Dispatch registration:** Tier 2 (geometric), `_GEOMETRIC_REGISTRY` rank 6 (last) `[VERIFIED: tactic_detector.py:2297]`; mapped in `_GEOMETRIC_DETECTOR_FNS` `[VERIFIED: tactic_detector.py:2307]`; `TacticMotifInt.TRAPPED_PIECE = 26` `[VERIFIED: tactic_detector.py:118]`.

**Current logic** `[VERIFIED: tactic_detector.py:926-973]`:
1. Loop pov turns at even move-indices; for each `board_after = boards[i+1]`, scan all squares for an opponent non-pawn piece.
2. Gate: piece must be under pov attack (`board_after.attackers(pov, sq)`).
3. Gate: skip if `_is_hanging` (free capture now = hanging-piece, not trapped) `[VERIFIED: L963]`.
4. Gate: set `board.turn = opp`, then `_escape_squares_all_lose_material(...)` — fire if non-empty escape set AND every escape lands where pov wins material `[VERIFIED: L966-971]`.

**Helper `_escape_squares_all_lose_material`** `[VERIFIED: tactic_detector.py:854-923]`: builds the victim's legal destination set; returns False (not trapped) if empty (pinned/no moves); for each escape, pushes it and returns False if the destination has no pov attacker OR pov's cheapest attacker value ≥ victim value; returns True only if every escape has a strictly-cheaper pov attacker.

**Why 0 TP / 153 FP** (gap analysis vs cook):
- **Scope mismatch (the dominant cause of low precision).** Our detector scans **every opponent non-pawn piece on every pov-result board** and fires whenever any of them is "all-escapes-lose-material." Cook's `trapped_piece` is far narrower: it only fires when the **player actually captured a non-pawn piece** in the solution line AND that piece (or the square it came from) was `is_trapped` on the board *before* the preceding opponent move `[CITED: cook.py def trapped_piece lines structure]`. Our version invents trapped-piece judgments on incidental pieces nowhere in the solution's capture chain → false positives.
- **Different "trapped" test.** Cook's `is_trapped` requires `is_in_bad_spot` first (attacked + hanging-or-takeable-by-lower) and treats an escape that **captures an equal-or-greater piece** as a refutation of trapped-ness `[CITED: util.is_trapped]`. Our `_escape_squares_all_lose_material` uses a simpler SEE-ish "cheapest pov attacker < victim value" rule and an explicit `_is_hanging` pre-gate `[VERIFIED: L963, L915]`. The pre-gate excludes the hanging case (correct intent) but the firing condition is not anchored to the capture chain.
- **0 TP specifically:** because the fixture has only 28 TRAIN rows AND because trapped-piece is Tier 2 rank 6 — it loses dispatch to fork/skewer/pin/discovery whenever those co-fire shallower, and loses to mates always. So even on the few genuine trappedPiece puzzles, a higher-priority motif typically wins. The 153 FP are positions where NO shallower motif fired and our over-broad scan invented a trapped judgment.

**Behavioral divergence to flag for the planner:** cook's `is_trapped` treats *no legal moves* (immobile, attacked, not pinned/in-check) as trapped; our `_escape_squares_all_lose_material` returns False on an empty escape set `[VERIFIED: L888-890]`. The planner should decide whether to mirror cook here. Likely keep the empty-set exclusion (precision-first), but it is a deliberate deviation, not an accident.

## Option B — per-motif oversample cap

### Current sampling mechanics `[VERIFIED: scripts/select_tagger_fixtures.py]`
- `SAMPLES_PER_STRATUM = 200` `[L69]`, 4 rating bands (`lt1200, lt1600, lt2000, gt2000`) `[L85, L104-118]` → up to 800 candidate rows/motif before dedup + 70/30 split `[TEST_FRACTION = 0.30, L73]`.
- `_stratified_sample` `[L251-318]`: builds `pool[(motif, band)]`; if a band pool `< MIN_STRATUM_SIZE (10)` `[L81]` it **collapses** to a per-motif all-bands fallback pool `[L288-304]`; samples `min(samples_per_stratum, pool_size)`; dedups by PuzzleId via a global `selected_ids` set `[L296-299]`.
- `MOTIF_TO_THEMES["trapped-piece"] = ("trappedPiece",)` `[VERIFIED: tests/scripts/tagger/motif_theme_map.py:54]`.
- **Why trapped-piece only got 39:** `trappedPiece` is rare in lichess; all four bands fall below `MIN_STRATUM_SIZE`, collapse to a tiny fallback pool, and the whole pool yields 39 unique rows `[CONFIRMED by report n_gt=39 and the 133 investigation L46-49]`.

### How to add the per-motif cap (Option B)
Add a CLI arg `--oversample-motifs` parsing `motif:N` pairs into a dict, e.g. `--oversample-motifs trapped-piece:1000` (use the FlawChess motif key, since `_stratified_sample` iterates `MOTIF_TO_THEMES.keys()`). Thread it into `_stratified_sample` so the per-stratum sample count becomes `oversample_map.get(motif, samples_per_stratum)` at both the collapsed-fallback branch `[L294]` and the normal branch `[L306]`. Default empty dict = current behavior.

**Target sizing:** trapped-piece → ~1000 total (≈700 train / 300 test via the 70/30 hash split). With band collapse, the fallback pool is sampled once at `N` per the collapse branch, so `N≈1000` (not split across 4 bands) is the right cap for a collapsing motif. The planner should confirm by running with a large cap first (see Open Q + Pitfall 6).

### Is raising one motif's cap truly isolated? — Near-total, NOT perfect (D-EXP-02 caveat)
**Isolated parts:**
- The **iteration order** over motifs is `sorted(MOTIF_TO_THEMES.keys())` `[L285]`, fixed regardless of caps. Each motif draws from its own `pool[(motif, band)]`, which is unchanged for non-oversampled motifs.
- `random.sample(pool, n)` with `random.seed(args.seed)` `[L413]` is deterministic *given the same call sequence and the same n*. **Critical subtlety:** because motifs are processed in sorted order and trapped-piece sorts AFTER many motifs alphabetically (t...), raising trapped-piece's `n` consumes *more* draws from the shared `random` stream **after** those earlier motifs are already sampled. Motifs sorted alphabetically **before** "trapped-piece" (fork, hanging-piece, mate, pin, skewer, sacrifice, etc. — anything < "trapped-piece") are sampled with identical `n` and identical RNG state → **byte-identical rows**. Motifs sorted **after** "trapped-piece" (under-promotion, x-ray) draw from a *shifted* RNG state and may select different rows even though their own `n` is unchanged.

  ⚠️ **This is a real gotcha the planner must handle.** Verify empirically (Pitfall 6). Two mitigations if x-ray/under-promotion rows drift: (a) re-seed the RNG per-motif (`random.seed(hash((seed, motif)))`) so each motif's draw is independent of others' `n` — the cleanest fix and worth doing in the same script edit; or (b) accept the drift and re-measure x-ray/under-promotion floors too. Recommend (a): per-motif re-seed makes Option B's isolation exact for ALL non-oversampled motifs, collapsing the blast radius to *only* the multi-label leakage below.

### Multi-label leakage (the unavoidable, intended residue)
New `trappedPiece` puzzles are **multi-label**: each also carries other lichess themes. They enter the *combined fixture*, so any OTHER motif whose theme co-occurs on those puzzles gets **new ground-truth rows** (its `n` / recall denominator grows, and a detector that fires on them shifts TP/FP). The harness credits via theme intersection `[VERIFIED: test_detector_precision.py:97-111]`, so:
- **Co-occurring motifs' GT counts shift** for whichever themes ride along with `trappedPiece`. Empirically, trappedPiece puzzles commonly also carry: `hangingPiece`, `fork`, `pin`, `advantage/crushing` (not motifs), `middlegame/endgame` (not motifs), `master`, `short/long` (not motifs). Of our *measured* motifs, the realistic co-movers are **hanging-piece, fork, pin, skewer, deflection, sacrifice, mate** — but only those that actually appear on trappedPiece-labeled rows AND get sampled into the fixture as *new* rows (a trappedPiece puzzle already sampled under another motif's stratum is deduped by `selected_ids`, so the marginal new rows are the ones that entered *only* because trapped-piece's cap rose).
- **Action (D-EXP-02):** after regeneration, diff the per-motif `n(train)/n(test)` columns in the report against the 2026-06-23 baseline; re-measure **only** the floors whose `n` (and thus precision) actually moved. Do NOT pre-emptively re-measure all 24 floors.

### Input needed: the lichess `.csv.zst`
- `scripts/select_tagger_fixtures.py --puzzle-path /path/to/lichess_db_puzzle_YYYY-MM.csv.zst` `[VERIFIED: L371-376]`.
- Source: **database.lichess.org/#puzzles** (`lichess_db_puzzle.csv.zst`, ~300 MB, CC0) `[VERIFIED: docstring L9-11, L29]`. **Not committed to git** `[VERIFIED: L10-11]`. The planner must download it (one-shot, manual) before the regeneration task. This is a **HUMAN/manual prerequisite** — flag it as a `checkpoint:human` or an environment dependency, not an automated step.

## The unsuppress mechanical path (and what's gated on ≥0.80)

From the Phase 133 mechanical recipe `[VERIFIED: .planning/notes/suppressed-tactic-gaps-investigation.md:80-92]`, the generic 5-step unsuppress is: (1) remove from `SUPPRESSED_MOTIFS`; (2) add `PRECISION_FLOOR`; (3) add `FAMILY_TO_MOTIF_INTS` family; (4) add frontend `TACTIC_GROUPS` entry; (5) update the family-count test.

**For trapped-piece specifically, steps 3-5 are ALREADY DONE** (Phase 129's 10-family taxonomy):
| Step | Generic path | trapped-piece status | Edit needed? |
|------|--------------|----------------------|--------------|
| 1. Remove from `SUPPRESSED_MOTIFS` | required | currently present `[VERIFIED: precision_floors.py:204]` | **YES — if ≥0.80** |
| 2. Add `PRECISION_FLOOR` | required | absent | **YES — if ≥0.80** (set ~5-8pp below measured TRAIN) |
| 3. `FAMILY_TO_MOTIF_INTS["trapped_piece"]` | required | **already present** `[VERIFIED: library_repository.py:137-139]` | no |
| 4. Frontend `TACTIC_GROUPS` / `tacticComparisonMeta.ts` | required | **already present** `[VERIFIED: tacticComparisonMeta.ts:114,142,163,260-264]` + def `[tacticMotifDefinitions.ts:20]` | no |
| 5. Family-count test | required | **already counts trapped_piece** in `ALL_FAMILIES` `[VERIFIED: TacticComparisonGrid.test.tsx:68; FlawFilterControl.test.tsx:57]` | no (count unchanged) |
| 6. `GOALS` entry in `tactic_tagger_report.py` | (implicit) | currently excluded `[VERIFIED: tactic_tagger_report.py:151-152]` | **YES — add for the /loop** (precision target ~0.80, recall None) |

**Gated on the ≥0.80 decision (D-EXP-03): steps 1, 2, and the GOALS shift.** If trapped-piece cannot clear ~≥0.80 TRAIN-holding-on-TEST:
- Leave it in `SUPPRESSED_MOTIFS`, add no `PRECISION_FLOOR`.
- **Still commit** the improved detector + expanded fixtures (removes the FP source from the eventual ship surface; leaves a real test set) `[VERIFIED: ROADMAP D-EXP-03 L456]`.
- **Update the docstring measurement notes** in `precision_floors.py:142-146` to reflect the new (larger-fixture) trapped-piece numbers regardless of ship/suppress.

**No DB migration / no backfill change** for the family mapping (query-time grouping) `[VERIFIED: library_repository.py:101-103; investigation note L89]`. A dev re-backfill is optional real-data validation only; the CC0 harness is authoritative `[VERIFIED: investigation note L90-92]`.

## The precision/recall gate + report harness

### CI floor gate — `tests/scripts/tagger/test_detector_precision.py`
- Scores `detect_tactic_motif` (post-dispatch) on TRAIN and TEST `[VERIFIED: L92, L230-233]`.
- TP/FP/FN via theme-intersection multi-label credit `[VERIFIED: L97-111]`.
- **Asserts `precision_train[motif] >= PRECISION_FLOOR[motif]` on TRAIN only**, for each non-suppressed motif `[VERIFIED: L161-182, L261-267]`. TEST is printed (with a train→test ΔP overfit column) but never gated `[VERIFIED: L233-252]`. Suppressed motifs print "SUPPRESSED" and are skipped from the gate `[VERIFIED: L167-168, L243]`.

### Goal-seeking loop — `scripts/tactic_tagger_report.py --check-goals`
- `GOALS` table = aspirational `/loop` targets, distinct from floors `[VERIFIED: tactic_tagger_report.py:100-153]`. `--check-goals` exits 1 until every goal dimension is met `[VERIFIED: L568-577]`. `--eval-set train|test` selects the split (default train) `[VERIFIED: L552-557]`.
- Scores the **post-dispatch winner** `[VERIFIED: L203-204]`.
- The `tactic-tagger-report` skill wraps this for the `/loop` self-improvement flow `[VERIFIED: SKILL via report docstring L22-24]`.

### Data flow to regenerate fixtures + re-measure
1. Download `lichess_db_puzzle_*.csv.zst` (manual).
2. `uv run python scripts/select_tagger_fixtures.py --puzzle-path … --oversample-motifs trapped-piece:1000` → overwrites `fixtures/tagger/detector_fixture_{train,test}.csv` (both committed, ~1.7MB / 0.7MB today) `[VERIFIED: git ls-files; L430-431]`.
3. `git diff --stat fixtures/tagger/` → confirm isolation (see Blast-radius).
4. `uv run pytest tests/scripts/tagger/test_detector_precision.py -x` → see which floors fail.
5. `PYTHONPATH=. uv run python scripts/tactic_tagger_report.py` → regenerate the dated report; diff `n(train)/n(test)` vs 2026-06-23 baseline to find which floors the leakage moved.
6. Re-measure + update only those `PRECISION_FLOOR` entries (+ trapped-piece if shipping).

**Which committed floors could the leakage force a re-measure of?** Only motifs that (a) sort alphabetically after "trapped-piece" (x-ray, under-promotion) IF the RNG-stream drift is not mitigated by per-motif re-seed, and (b) any measured motif whose theme co-occurs on the *newly added* trappedPiece rows — realistically **hanging-piece, fork, pin, skewer, deflection, sacrifice** and possibly **mate**. The exact set is empirical (step 5). With per-motif re-seed (recommended), (a) disappears entirely and only (b) remains.

## Common Pitfalls

### Pitfall 1: RNG-stream coupling defeats "byte-identical"
**What goes wrong:** Raising trapped-piece's `n` shifts the shared `random` stream, changing rows for motifs sorted *after* it.
**Why:** single global `random.seed` + sequential `random.sample` over sorted motifs `[VERIFIED: select_tagger_fixtures.py:413, 285, 295/307]`.
**How to avoid:** per-motif re-seed (`random.seed(hash((args.seed, motif)))`) inside `_stratified_sample`, OR re-measure x-ray/under-promotion floors.
**Warning signs:** `git diff` shows changed rows for motifs you didn't touch.

### Pitfall 2: Scoring the standalone detector instead of the post-dispatch winner
**What goes wrong:** trapped-piece may look great standalone but produce few/no post-dispatch TPs because Tier 2 rank 6 loses to fork/skewer/pin/discovery/mates.
**Why:** both harness and report call `detect_tactic_motif` (the winner), not `detect_trapped_piece` `[VERIFIED: test L92; report L203]`.
**How to avoid:** judge ship/suppress on post-dispatch numbers (what the gate uses). When iterating the detector, probe standalone to debug, but gate on dispatch.
**Warning signs:** standalone precision 1.0 but report still shows few trapped-piece TPs.

### Pitfall 3: Treating ≥0.80 as guaranteed reachable
**What goes wrong:** cook curates puzzle *solution* lines; we run a raw Stockfish PV that can diverge from cook's clean relational chain deep in the line — the same x-ray-depth risk flagged in Phase 132 `[VERIFIED: ROADMAP L389]`. trapped-piece's combined TP-depth was blank (`–`, never fired) `[VERIFIED: report L74]`, so depth behavior is unknown until it fires.
**How to avoid:** D-EXP-03 already handles this — full-port-then-conditional-unsuppress. Plan for the suppressed outcome too (commit detector + fixtures, no floor).

### Pitfall 4: Source pool might be smaller than ~1000
**What goes wrong:** If lichess has < ~1000 trappedPiece puzzles, the cap can't reach 1000; en-passant (n_gt 19) and under-promotion (n_gt 8) are *intrinsically* rare and will NOT reach 1000 — acceptable soft target `[VERIFIED: ROADMAP L447]`.
**How to avoid:** run once with a huge cap to learn pool size (the script prints "N available" per stratum `[VERIFIED: L300-315]`); set the cap to the achievable ceiling.

### Pitfall 5: Test isolation — eval-lottery memory does NOT apply here
**What goes wrong:** worry about the eval_queue lottery leak. **It doesn't apply** — this phase touches no `Game`/`eval_queue` rows; it's pure fixture + detector + floor work. No DB inserts. `[VERIFIED: scope is tactic_detector.py + scripts + tests/scripts/tagger, no game inserts]`
**Note for planner:** the per-run-DB isolation (Phase 100) means the harness tests are DB-free anyway (they read committed CSVs).

### Pitfall 6: Verifying byte-identical isolation
**What goes wrong:** Assuming isolation without checking.
**How to avoid:** see Blast-radius Verification below.

## Blast-radius Verification (concrete commands)

After regenerating with the per-motif cap:

```bash
cd "$(git rev-parse --show-toplevel)"

# 1. Stat-level: how many lines changed in each committed fixture
git diff --stat fixtures/tagger/detector_fixture_train.csv fixtures/tagger/detector_fixture_test.csv

# 2. Prove non-trapped motifs are byte-identical: extract rows that do NOT carry
#    the trappedPiece theme from OLD vs NEW and diff. If isolation holds (with
#    per-motif re-seed), the only diff should be added trappedPiece rows.
git show HEAD:fixtures/tagger/detector_fixture_train.csv | grep -v 'trappedPiece' | sort > /tmp/old_nontrapped.csv
grep -v 'trappedPiece' fixtures/tagger/detector_fixture_train.csv | sort > /tmp/new_nontrapped.csv
diff /tmp/old_nontrapped.csv /tmp/new_nontrapped.csv && echo "ISOLATED: non-trapped rows byte-identical"

# 3. Identify which floors actually moved: regenerate the report and diff the n() columns
PYTHONPATH=. uv run python scripts/tactic_tagger_report.py
#    Compare the per-motif n(train)/n(test) + P(train) columns of the new dated report
#    against reports/tactic-tagger/tactic-tagger-2026-06-23.md (the baseline).

# 4. Run the gate to see concrete floor failures (the authoritative signal)
uv run pytest tests/scripts/tagger/test_detector_precision.py -x -q
```

A motif whose `n(train)` is unchanged AND whose rows are byte-identical cannot have moved — skip it. Re-measure only motifs with changed `n` or a failing floor.

## Runtime State Inventory

> N/A — greenfield-style detector/fixture change. No rename/migration. No stored data, live service config, OS-registered state, secrets, or build artifacts reference any renamed string. **None — verified by scope (tactic_detector.py + scripts + tests/scripts/tagger; no DB writes, no migration, no config).**

## Code Examples

### Per-motif cap threading (shape, not a copy)
```python
# scripts/select_tagger_fixtures.py — _stratified_sample signature + use
def _stratified_sample(candidates, samples_per_stratum=SAMPLES_PER_STRATUM,
                       oversample_map: dict[str, int] | None = None):
    oversample_map = oversample_map or {}
    ...
    for motif in sorted(MOTIF_TO_THEMES.keys()):
        random.seed(hash((BASE_SEED, motif)))      # Pitfall 1 mitigation (per-motif RNG)
        cap = oversample_map.get(motif, samples_per_stratum)
        for band in all_bands:
            ...
            n = min(cap, len(band_pool))           # was: min(samples_per_stratum, ...)
```
Source pattern: existing `_stratified_sample` `[VERIFIED: scripts/select_tagger_fixtures.py:251-318]`.

### Detector assembly from existing ports (shape)
```python
# Mirror cook util.is_trapped using EXISTING helpers (no new geometry):
#   _is_in_bad_spot(board, sq)            # tactic_detector.py:318  (= util.is_in_bad_spot)
#   board.is_check(), board.is_pinned(color, sq), legal_moves loop
#   piece value compare via _piece_value  # tactic_detector.py:270
# Anchor firing to the SOLUTION CAPTURE CHAIN (cook's driver), not a full-board scan.
```
Source helpers verified at `[tactic_detector.py:270, 318]`.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Self-labeled detector-bucketed fixtures | Independent CC0 puzzle harness (precision+recall, TRAIN/TEST split) | Phase 127 | trapped-piece judged against external ground truth |
| `_grade(met,total)` voting detectors | cook exact relational AND-chains | Phases 131/132/133 | the precision lever this phase applies to trapped-piece |
| Per-tier dispatch | Depth-primary, then tier, then rank (shallowest-wins) | Phase 131 | trapped-piece (Tier 2 rank 6) loses to shallower motifs — caps its recall |
| Global `SAMPLES_PER_STRATUM` only | (this phase) per-motif `--oversample-motifs` cap | Phase 134 | isolates fixture growth to chosen motifs |

**Deprecated/outdated:**
- precision_floors.py docstring trapped-piece note (L142-146) describes the 28-row fixture; will be stale after expansion — update it.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | lichess has enough `trappedPiece` puzzles to reach ~1000 (133 estimate: ~4k-20k available) `[ASSUMED, from 133-RESEARCH L259]` | Option B | If pool < ~1000, cap reaches a lower ceiling; detector still re-judged on a larger-but-smaller-than-1000 set — acceptable per soft-target framing |
| A2 | Co-moving themes on trappedPiece puzzles are mainly hanging-piece/fork/pin/skewer/deflection/sacrifice/mate `[ASSUMED, from general lichess theme co-occurrence]` | Multi-label leakage | If other motifs co-move, more floors re-measure; the report-diff step (verification) catches the true set empirically — low risk |
| A3 | trapped-piece can plausibly reach ≥0.80 post-dispatch after a faithful cook port `[ASSUMED]` | Gate | If unreachable, D-EXP-03 keeps it suppressed — designed-for outcome, not a failure |
| A4 | Per-motif re-seed fully isolates non-co-moving motifs `[ASSUMED — standard RNG reasoning, verify empirically]` | Pitfall 1 | If not, re-measure x-ray/under-promotion floors; verification step catches it |

## Open Questions

1. **Actual `trappedPiece` pool size in the current lichess DB.**
   - Known: rare (~0.2% of sampled in the 39/17k baseline `[133-RESEARCH L259]`).
   - Unclear: absolute count; whether ~1000 is reachable.
   - Recommendation: first regeneration run with a huge cap (e.g. `trapped-piece:100000`) just to read the printed "N available"; then set the real cap.

2. **Empty-escape-set handling — mirror cook (trapped) or keep our exclusion (not trapped)?**
   - cook's `is_trapped` returns True for an immobile attacked non-pawn/non-king; ours returns False on empty escape set `[VERIFIED: util.is_trapped vs L888-890]`.
   - Recommendation: decide during planning; precision-first leans toward keeping the exclusion, but test both against the expanded fixture.

3. **Whether to top up en-passant/promotion/under-promotion in the same run.**
   - They're intrinsically rare (soft target, won't reach 1000). Doing them in the same `--oversample-motifs` call is free; their floors are mostly suppressed/thin already.
   - Recommendation: include them — more data can't hurt and the cap is per-motif isolated.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `lichess_db_puzzle_*.csv.zst` (~300MB, CC0) | fixture regeneration | ✗ (not committed; must download) | — | none — blocks the regeneration task until downloaded |
| python-chess | detector + selector | ✓ | 1.11.x | — |
| zstandard | `.csv.zst` streaming | ✓ | installed (imported) | — |
| dev Postgres | NOT needed for harness (reads CSVs) | n/a | — | — |

**Missing dependencies with no fallback:** the lichess puzzle `.csv.zst` download — a **manual human prerequisite** before the fixture-regeneration wave. Flag as `checkpoint:human`.

## Validation Architecture

> nyquist_validation = true `[VERIFIED: .planning/config.json]` — section included.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-xdist (`-n auto` local) |
| Config file | `pyproject.toml` (tagger dir included via existing CI step) |
| Quick run command | `uv run pytest tests/scripts/tagger/test_detector_precision.py -x -q` |
| Full suite command | `uv run pytest -n auto` |

### Phase Requirements → Test Map
| Req | Behavior | Test Type | Automated Command | File Exists? |
|-----|----------|-----------|-------------------|-------------|
| Option B cap | per-motif cap raises trapped-piece, isolates others | unit + manual diff | `git diff --stat fixtures/tagger/` + a unit test on `_stratified_sample(oversample_map=...)` | ❌ Wave 0 (add a selector unit test) |
| Detector rewrite | post-dispatch precision on expanded fixture | harness | `uv run pytest tests/scripts/tagger/test_detector_precision.py -x` | ✅ |
| Conditional unsuppress | floor present+passing iff ≥0.80, else suppressed | harness | same | ✅ |
| Goal loop | `--check-goals` exits 0 when target met | script | `PYTHONPATH=. uv run python scripts/tactic_tagger_report.py --check-goals --eval-set test` | ✅ |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/scripts/tagger/test_detector_precision.py -x -q`
- **Per wave merge:** `uv run pytest -n auto` + `uv run ty check app/ tests/` + `uv run ruff check . --fix && uv run ruff format .`
- **Phase gate:** full suite green + frontend `npm run lint && npm test -- --run` (only if any frontend file touched — likely none) before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] `tests/scripts/test_select_tagger_fixtures.py` — a small unit test asserting `--oversample-motifs`/`oversample_map` raises the target motif's sample count and (with per-motif re-seed) leaves a control motif's selection unchanged. Currently no test exercises `_stratified_sample` directly.
- [ ] No framework install needed.

## Security Domain

> `security_enforcement` not set to false → nominally enabled, but this phase has **no attack surface**: no HTTP route, no user input, no auth, no DB write, no crypto, no external network call at request time. The only external input is the offline CC0 `.csv.zst` (trusted public dataset, parsed by the existing streaming reader with `errors="replace"` `[VERIFIED: select_tagger_fixtures.py:182]`).

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | marginal | CSV parse already guards bad FEN/moves/ratings (`try/except`, `continue`) `[VERIFIED: L199-218]` |
| V2/V3/V4 (auth/session/access) | no | no request path |
| V6 Cryptography | no | SHA-1 used only as a deterministic bucket hash, not security `[VERIFIED: L332]` |

### Known Threat Patterns
| Pattern | STRIDE | Mitigation |
|---------|--------|------------|
| Malicious puzzle CSV | Tampering | Download only from database.lichess.org (CC0); parser skips malformed rows |

No new threats introduced.

## Sources

### Primary (HIGH confidence)
- `app/services/tactic_detector.py` — detect_trapped_piece (926-973), `_escape_squares_all_lose_material` (854-923), helpers `_is_defended`/`_is_in_bad_spot` (291/318), dispatch registries (2290-2333), TacticMotifInt (88-118).
- `scripts/select_tagger_fixtures.py` — full sampling/split/CLI (1-436).
- `tests/scripts/tagger/precision_floors.py` — SUPPRESSED_MOTIFS (198-220), PRECISION_FLOOR (242-309), measurement notes (8-185).
- `tests/scripts/tagger/test_detector_precision.py` — gate + scoring (1-268).
- `tests/scripts/tagger/motif_theme_map.py` — MOTIF_TO_THEMES (44-81).
- `scripts/tactic_tagger_report.py` — GOALS (100-153), `--check-goals`/`--eval-set` (540-577), scoring (203-204).
- `app/repositories/library_repository.py` — FAMILY_TO_MOTIF_INTS incl. trapped_piece (109-183), confidence lever (60).
- `frontend/src/lib/tacticComparisonMeta.ts` (114,142,163,193,260-264), `tacticMotifDefinitions.ts` (20), `TacticComparisonGrid.test.tsx` (66-72,334).
- `reports/tactic-tagger/tactic-tagger-2026-06-23.md` — current precision/recall + n_gt table.
- `/home/aimfeld/Projects/Python/lichess-puzzler/tagger/cook.py` + `util.py` — AGPL oracle (trapped_piece, is_trapped, is_in_bad_spot, is_defended, hanging_piece) — used as PROSE reference only.

### Secondary (MEDIUM confidence)
- `.planning/notes/suppressed-tactic-gaps-investigation.md` — trapped-piece undersampling, mechanical path, Option B framing.
- `.planning/phases/133-*/133-RESEARCH.md` + `133-VERIFICATION.md` — descope rationale, Option A/B/C analysis, blast-radius warning, pool-size estimate.
- ROADMAP Phase 131/132/133/134 blocks — playbook, locked decisions.

### Tertiary (LOW confidence)
- trappedPiece pool-size and co-occurring-theme estimates — assumptions, verify at regeneration time.

## Metadata

**Confidence breakdown:**
- Cook predicate: HIGH — read directly from source, described in prose.
- Current-detector gap: HIGH — code read line-by-line.
- Option B isolation: MEDIUM-HIGH — mechanics verified; the RNG-stream coupling (Pitfall 1) is reasoned and must be verified empirically.
- Mechanical unsuppress path: HIGH — family/chip presence verified in code; only floor/GOALS edits remain.
- Pool size / leakage scope: MEDIUM — empirically determined at regeneration; verification commands provided.

**Research date:** 2026-06-23
**Valid until:** ~2026-07-23 (stable; the lichess DB grows monthly but the mechanics don't change).
