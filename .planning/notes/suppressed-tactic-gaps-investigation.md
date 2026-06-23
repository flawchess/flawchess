---
title: Suppressed-tactic gap investigation (attraction off-by-one, sacrifice-as-co-tag, mate geometry, trapped-piece fixtures)
date: 2026-06-23
context: /gsd-explore session after Phases 131/132 shipped. Empirical probing of the 6 in-scope suppressed motifs (excl. tier-5 en-passant/under-promotion). Feeds Phase 133 planning.
---

# Suppressed-tactic gaps — root causes (validated by probe, not docstring)

Source report: `reports/tactic-tagger/tactic-tagger-2026-06-23.md`. All numbers below
are from direct probes against the committed fixtures (`tests/scripts/tagger/conftest.py`
`_load_split`), TRAIN = 11,855 rows / TEST = 5,164 rows.

The six suppressed motifs (excluding tier-5) fail for **three structurally different
reasons**. The `precision_floors.py` docstrings misdiagnosed two of them.

## Group A — bugs / geometry (detector-internal)

### attraction — ONE-LINE off-by-one (NOT "PV depth", as the docstring claims)
- `precision_floors.py` says: *"0 TP on TRAIN ... lure+4-move sequence rarely survives
  the Stockfish PV depth limit."* **This is wrong.** PV depth (≤12 plies) is plenty.
- Real cause: in `_attraction_fires_at` (tactic_detector.py ~L1534), cook condition 5
  (the "player attacks the attracted square" check) is computed on **`boards[k+2]`** —
  the board *before* pov's follow-up move. pov's piece is still on its origin square, so
  `moves[k+2].to_square` is never in `boards[k+2].attackers(pov, attracted_sq)`. The
  chain dies 100% at this condition (probe: 1700 rows reach it, **0 pass**).
- cook uses `next_node.board()` = the board *after* pov's follow-up = our **`boards[k+3]`**.
- **Fix = change `boards[k+2]` → `boards[k+3]` for the cond-5 attacker check** (the KING
  short-circuit and the k+4 Q/R branch are unaffected).
- Proven result with the fix:
  - Standalone: fires on **1603/1603 TRAIN + 677/677 TEST** attraction-labeled rows
    (≈100% recall), **0 FP** on non-attraction rows → **precision 1.000 both splits**.
  - Post-dispatch (depth-primary, single-winner): attraction WINS **654/1603 (41%) TRAIN,
    290/677 (43%) TEST**. The rest go to genuinely shallower co-tactics (mate,
    anastasia-mate, pin) — correct multi-label behavior, not real FNs.
  - At ~42% post-dispatch recall it would be one of the *higher*-recall Tier-3 motifs
    (deflection ships at 0.15, x-ray 0.36). n_gt = 2280 (2nd-largest theme).

### arabian-mate / boden-mate / dovetail-mate — geometry never/wrongly matches
- arabian (NaN, n_gt 794) and boden (NaN, n_gt 605) **never fire** — geometry too strict.
- dovetail (0 TP / 23 FP, n_gt 774) fires only false positives — geometry wrong.
- These are Tier-1, short-circuit on geometry. Same class of problem 131-03 already
  solved for back-rank / anastasia / hook by faithfully porting cook's mate geometry.
  Detectors exist (`detect_arabian_mate`, `detect_boden_or_double_bishop_mate`,
  `detect_dovetail_mate`); the fix is porting cook geometry, like 131-03. Effort: medium.

## Group B — fixture undersampling (trapped-piece)
- n_gt = **39** total (28 TRAIN / 11 TEST). Cannot honestly gate precision at that count —
  one FP tanks it. Detector is `detect_trapped_piece` with a strict D-06 SEE gate
  (currently 0 TP / 9 FP → only-FP → suppressed).
- Fix is **upstream**: oversample the `trappedPiece` theme in
  `scripts/select_tagger_fixtures.py` so the gate has a real denominator, *then* re-judge
  the detector. Don't tune the detector against 28 rows.

## Group C — dispatch / architecture (sacrifice)
- `precision_floors.py` says sacrifice *"never wins single-winner dispatch."* **Also wrong** —
  the 2026-06-23 report shows it at **1.000 precision / 0.122 recall, shipped-able**.
- Probe: standalone `detect_sacrifice` (current odd-board parity) fires on **3142/3142
  TRAIN + 1377/1377 TEST** sacrifice rows, **1 FP in 8713** non-sac TRAIN →
  **precision 1.000, recall 1.000 standalone**. Not broken; never was.
  - Note: cook's literal even-board parity (`diffs[1::2][1:]`) gives 0.65 precision (worse).
    Our current odd-board scan is the *correct* one — do not "fix" it to match cook's index.
- The "0.122 recall" is **purely post-dispatch**: sacrifice wins single-winner dispatch on
  only **12.2% (384 TRAIN)** of sac rows. The other 88% are shadowed mostly by **mates**
  (~70%: mate/back-rank/anastasia/smothered/hook) + fork/pin — arguably correctly tagged.
- **Greek-gift result (the user's specific ask):** of 49 greek-gift-shaped puzzles
  (B captures h7/h2/g7/g2 as pov's 1st move), **32 (65%) are ALREADY tagged sacrifice**
  (they win dispatch — an attacking bishop sac rarely yields a forced mate within the PV
  cap, so no mate shadows it). They're just suppressed at query time today.

## DECISION (user, this session)
- **Scope = ship Group A + B + sacrifice; defer the rest of C.**
- **sacrifice: "just unsuppress" (single-winner), NO schema change.** User accepts that
  sacrifice loses to higher-priority tags when they co-occur. Co-tag / multi-label
  (every sac shows a secondary badge) was explicitly rejected as too big a lift.
  Unsuppressing surfaces 12.2% of sacs incl. 65% of greek gifts at 1.000 precision.
- **attraction: fix the off-by-one + unsuppress.** It joins Group A as a bug, not Group C.
- **Stale docstrings to correct:** the attraction "PV depth" claim and the sacrifice
  "never wins dispatch" claim in `precision_floors.py` are both factually wrong.

## Mechanical unsuppress path (sacrifice int 17, attraction int 10)
Both currently "map to no family" (`library_repository.py` ~L156) so they never reach the
UI even when they fire. Both fire at `TACTIC_CONFIDENCE_HIGH` (100) → they clear the
`_TACTIC_CHIP_CONFIDENCE_MIN`=70 lever automatically. To ship a motif:
1. Remove from `SUPPRESSED_MOTIFS` (`tests/scripts/tagger/precision_floors.py`).
2. Add a `PRECISION_FLOOR[...]` entry (set ~5–8pp below measured TRAIN, per D-09).
3. Add to `FAMILY_TO_MOTIF_INTS` (`library_repository.py`) as a new family.
4. Add the frontend `TACTIC_GROUPS` "advanced" entry (mirror deflection/intermezzo/etc).
5. Update the family-count test (`test_family_mapping_ten_families` — count changes).
- No DB migration / no backfill change needed for the family mapping (query-time grouping).
- Tactic tagging is **not yet in prod**, so no prod re-backfill / no live-wrong-tags
  urgency (cf. 131 D-12). A dev re-backfill is optional real-data validation only; the CC0
  fixture harness remains the authoritative precision signal.

## Probe reproductions (for the planner)
All probes: `chess.Board(row["fen"])` → `_parse_pv(board, row["pv"])` → call the standalone
detector; compare standalone firing vs `detect_tactic_motif` (post-dispatch winner) via
`_INT_TO_MOTIF`. `pv = Moves[1:]` (the real lichess solution line, NOT a re-analysis), so
`boards[0]` is pov-to-move and pov moves land on even move-indices.

## Refs
- `.planning/notes/tactic-tagger-cook-alignment.md` — cook↔ours index convention.
- `/home/aimfeld/Projects/Python/lichess-puzzler/tagger/cook.py` — AGPL oracle
  (`attraction` ~L369, `sacrifice` ~L184; reimplement from prose, copy no source — 131 D-10).
- `.planning/phases/132-*/132-CONTEXT.md` — full-port-then-suppress playbook, TEST+ΔP gate.
