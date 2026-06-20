---
id: SEED-058
status: dormant
planted: 2026-06-19
planted_during: v1.28 Tactic Tagging (phase 128)
trigger_when: when expanding tactic-motif coverage or revisiting the tactic detector / tagger precision
scope: medium
---

# SEED-058: Add new tactic motifs (discovered-check, trapped-piece, en-passant, promotion/under-promotion) to close lichess-theme coverage gaps

## Why This Matters

The tactic-tagger report (2026-06-19) cross-referenced against lichess `puzzleTheme.xml`
surfaced tactical puzzle themes that FlawChess's detector
(`app/services/tactic_detector.py::detect_tactic_motif`) cannot emit at all. Four
are genuinely tactical, deterministically detectable, and high-frequency on lichess —
adding them is low-risk coverage growth, and one (`discovered-check`) is nearly free
because the logic already exists.

## What to Add (priority order)

1. **discovered-check** — HIGH ROI, nearly free. The detection already lives inside
   `detect_discovered_attack` ("Sub-case 1: discovered check" branch, ~`tactic_detector.py:547`)
   but is folded into the `discovered-attack` motif. Split it into its own motif.
   Maps to lichess theme `discoveredCheck`. High frequency.

2. **trapped-piece** — the originally-requested gap. New detector: enumerate the
   attacked piece's legal escape squares and confirm all of them either lose material
   or remain attacked (the piece cannot escape capture). Distinct from `hanging-piece`
   (can't-escape over the next move(s) vs free-to-capture-right-now). Maps to lichess
   theme `trappedPiece`. Moderate effort, high frequency.

3. **en-passant** — trivial, ~100% precision. The solution move is an en-passant
   capture (one-line check). Maps to lichess theme `enPassant`. Niche but free.

4. **promotion / under-promotion** — trivial, high precision. Move is a pawn promotion
   (`promotion`) / promotion to a non-queen (`under-promotion`). Maps to lichess themes
   `promotion` / `underPromotion`. ⚠️ These are move-TYPE tags more than tactical
   motifs and risk diluting the motif chip — flag for a quick PRODUCT CALL before
   shipping the chip surface. The detection itself is harmless; the question is whether
   to surface them as chips.

## Per-motif implementation recipe (same 5 steps each)

a. New `TacticMotif` Literal value (`tactic_detector.py:103`) + `_INT_TO_MOTIF` IntEnum entry.
b. Detector function or branch.
c. `motif_theme_map.py` entry (`tests/scripts/tagger/`) mapping motif → lichess theme.
d. Dispatch-order placement in `detect_tactic_motif`.
e. Precision floor in `tests/scripts/tagger/precision_floors.py`, baselined from a
   fresh harness run on TRAIN (D-09). Never lower an existing floor to pass.

## When to Surface

**Trigger:** when expanding tactic-motif coverage, or when revisiting the tactic
detector / tagger precision (e.g. a future "tactic coverage" phase, or while fixing
the suppressed named-mate detectors in SEED-057's neighborhood).

## Scope Estimate

**Medium** — roughly one phase. `discovered-check` / `en-passant` / `promotion` are
hours each; `trapped-piece` needs real escape-square logic and a careful precision
baseline. The product call on promotion chips may split item 4 out.

## Explicitly OUT OF SCOPE (considered and rejected)

- **More named-mate patterns** (epaulette / corner / killBox / vukovic / opera /
  balestra / blindSwine / pillsbury / morphy / swallowtail / triangle) — BLOCKED on
  first fixing the existing SUPPRESSED named-mate detectors. `arabian` / `boden` /
  `dovetail` currently fire at zero precision; adding more named mates is negative ROI
  until those work. (Related: SEED-057.)
- **Non-motif lichess metadata themes** — game phase (opening/middlegame/endgame),
  endgame TYPE (rook/pawn/knight/bishop/queen/queenRook — FlawChess classifies these
  separately via `endgame_zones.py`), eval bands (advantage/crushing/equality),
  length/difficulty (already encoded by `tactic_depth`), source meta
  (master/masterVsMaster/superGM/playerGames/mix).
- **Fuzzy / positional themes** — zugzwang, exposedKing, kingside/queensideAttack,
  attackingF2F7, advancedPawn, quietMove, defensiveMove, collinearMove. These are
  eval/judgement-driven, not deterministic geometry, and would be low precision.

## Breadcrumbs

- `app/services/tactic_detector.py:103` — `TacticMotif` Literal (24 motifs today)
- `app/services/tactic_detector.py:532-560` — `detect_discovered_attack`, already
  contains the discovered-check sub-case to split out
- `tests/scripts/tagger/motif_theme_map.py` — motif → lichess-theme map
- `tests/scripts/tagger/precision_floors.py` — never-regress floors (D-09)
- `reports/tactic-tagger/tactic-tagger-2026-06-19.md` — source report
- lichess `puzzleTheme.xml` — canonical theme list
- Related: SEED-057 (pin gate parity + depth-index bug; same detector family)

## Notes

Captured from the tactic-tagger report session 2026-06-19. The report itself only
lists motifs the detector can emit, so these gaps are invisible there by construction.
