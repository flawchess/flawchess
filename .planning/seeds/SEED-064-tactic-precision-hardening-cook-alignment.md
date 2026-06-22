---
id: SEED-064
status: dormant
planted: 2026-06-22
planted_during: v1.28 Tactic Tagging (current_phase 999.1 BACKLOG)
trigger_when: when starting the next tactic-tagger quality phase — i.e. before the tactic-tag chips / you-vs-opponent motif comparison are trusted in the product. Precondition for surfacing fork/pin/skewer/discovered-attack tags with confidence.
scope: Medium
source: /gsd-explore session 2026-06-22 (this file is the distilled output); reports/tactic-tagger/tactic-tagger-2026-06-20.md; SEED-057 (pin gate, resolved); lichess-puzzler clone at /home/aimfeld/Projects/Python/lichess-puzzler
---

# SEED-064: Tactic precision hardening via faithful cook.py alignment (Tier 1 + Tier 2)

## Why This Matters

The tactic tagger ships tags that users do not trust. On the dev DB (73,318 flaws,
35,721 with an `allowed_tactic_motif`), **82.6% of all tactic tags come from the four
lowest-precision geometric motifs**, all at confidence 100 (always shown, cannot be
hidden by the `_TACTIC_CHIP_CONFIDENCE_MIN` lever):

| Motif | Prod tags (allowed) | % of all tags | P(test) on puzzles |
|---|--:|--:|--:|
| fork | 10,168 | 28.5% | 0.40 |
| discovered-attack | 6,936 | 19.4% | 0.17 |
| pin | 6,801 | 19.0% | 0.44 |
| skewer | 5,612 | 15.7% | 0.15 |
| back-rank-mate | 1,633 | 4.6% | 0.27 |

Volume-weighted held-out precision across these five is **~0.31** — roughly two of every
three tactic chips a user sees are wrong. (And 0.31 is an *upper bound*: the harness scores
a TP whenever our motif is *any* of the puzzle's themes — generous multi-label intersection
credit, D-10 — so the strict "did we name the right motif" precision is lower still.)

The product goal (one `missed` + one `allowed` tactic per flaw, precision-first) means a wrong
chip destroys trust while a NULL chip costs nothing. So the fix is precision, not recall.

## Core Insight: cook.py is the oracle, so faithful replication is the precision ceiling

Every theme label on our validation fixture was produced by `ornicar/lichess-puzzler`'s
`tagger/cook.py` (cloned locally at `/home/aimfeld/Projects/Python/lichess-puzzler`). Our
detector (`app/services/tactic_detector.py`) is a clean-room reimplementation of its heuristics
(Phase 124). Consequence: **our precision problem is predicate divergence.** Where our predicate
is looser or different from cook's, we over-fire (false positives). The theoretical ceiling is
reached by replicating cook's exact predicates, motif by motif. We are allowed to do this — the
heuristics aren't copyrightable; only the AGPL *source* is. Reimplement from pseudocode, never
paste cook.py bodies (the existing Phase 124 constraint).

This rules out the alternatives:
- **ML — wrong tool.** The labels are deterministic output of a readable algorithm; a model would
  approximate cook.py with worse fidelity and lose explainability + the `tactic_piece` byproduct.
- **Blind `/loop` on `--check-goals` — insufficient alone.** It overfits the train split and stalls.
  Use it as the *measurement/regression harness*; the *guidance* is cook.py's pseudocode.

## Scope

**In scope — Tier 1 (mates) + Tier 2 (geometric).** Two workstreams:

### Workstream A — Predicate alignment (raises puzzle precision)
Port cook.py's exact predicate for each firing motif; measure on the CC0 puzzle fixture.
Priority by prod volume × precision gap:

| Motif | Now P(test) | Target | Key cook.py divergence (diagnosed this session) |
|---|--:|--:|---|
| skewer | 0.15 | >0.9 or suppress | Our detector is badly broken. cook: a ray-piece capture where the opponent's *prior move* placed a piece on the capture square, that piece is ray-defended, lies *between* the mover's from/to, mover worth more, capture square "in bad spot". |
| discovered-attack | 0.17 | >0.9 or suppress | Over-fires. cook: discovered *check*, OR a capture whose square was vacated by an *earlier* player move revealing the attack. Tighten; respect the discovered-check vs discovered-attack split (D-03). |
| back-rank-mate | 0.27 | >0.9 | Over-fires on corner mates. cook: final position is checkmate AND defender king on back rank AND escape squares all blocked/attacked (one-square carve-out) AND ≥1 checker on the back rank. |
| fork | 0.40 | >0.9 or suppress | **Missing gate:** our `detect_fork` (tactic_detector.py:333) never checks the forker is safe. cook requires the forking piece *not be in a "bad spot"* (not hanging/capturable on the fork square) and counts victims that are higher-value OR (hanging AND undefended). Add the forker-safety gate. Recall is already 0.78 — precision-only fix. |
| pin | 0.44 | >0.9 or suppress | SEED-057 lifted it 0.41→0.44; remaining gap needs cook's `pin_prevents_attack` / `pin_prevents_escape` exact logic. |
| anastasia-mate | 0.86 | >0.9 | Small lift. |
| hook-mate | 0.84 | >0.9 | Small lift. |
| discovered-check | 0.83 | hold ≥0.85 | Already strong; don't regress when tightening discovered-attack. |

Already at/above bar (lock against regression, no work): mate (1.00), smothered-mate (1.00),
double-check (1.00), hanging-piece puzzle-precision (0.95 — but see Workstream B).

### Workstream B — Missed-vs-played gate (the hidden false alarm; NOT puzzle-measurable)
The missed pass (`flaws_service.py:424-434`) scores `detect_tactic_motif(board_before, best_pv)`
and **never compares against the move the player actually played** (`move_san_of_flaw` is used only
on the "allowed" branch). So when the best line is "capture the hanging rook with the knight" and
the player captured the same rook *with the wrong piece*, we emit `missed = hanging-piece`, conf 100
— a false "you missed it" when the player plainly saw the piece and executed it wrong.

Fix: on the missed pass, **suppress the missed tactic when the flaw move's destination square equals
the best line's first-move destination** (the player went to the same target → not a missed tactic).
This generalizes across every capture-based missed motif (missed side is dominated by fork 5,847 /
pin 5,679 / discovered-attack 5,617 / skewer 4,259), so the blast radius is far larger than the 328
missed hanging-piece rows alone.

**Critical:** this bug is invisible to the puzzle harness — a puzzle has no "move the player actually
played." Validate Workstream B with hand-built `(flaw_move, best_line)` unit fixtures + a prod
spot-check, NOT the precision report. A green puzzle report does not prove these false alarms are gone.

## Out of Scope

- **All Tier-3 tactics** (deflection, attraction, intermezzo, x-ray, interference, clearance,
  capturing-defender, sacrifice). They are ~1.8% of tag volume, already query-suppressed (conf <70),
  and per-user too rare for a meaningful Wilson comparison. Leave suppressed; defer to a later phase.
  (cook's tier-3 logic is sequence-relational and our reimplementations use loose `met >= N`
  thresholds — fixable, but low ROI now.)
- **ML** — rejected (see Core Insight).
- **A hand-labeled prod-flaw precision set** — explicitly deferred. Decision this session: stick with
  the CC0 puzzle fixture as ground truth for Workstream A, accepting the known blind spot that
  Workstream B is validated separately.

## Shipping Gate (per motif)

- Puzzle precision **> 0.9** on the held-out TEST split (judge on TEST + ΔP, never TRAIN — overfit guard).
- Can't reach 0.9 even at full cook fidelity → **leave suppressed** (`tactic_motif` stays NULL / below the
  confidence lever). Recall is whatever falls out — not gated (D-08).
- **Honest expectation:** not all four geometrics will reach 0.9. Skewer (0.15) and discovered-attack
  (0.17) are deeply broken and may plateau below — in which case suppress them. Suppressing skewer alone
  removes ~16% of all tags (mostly false). Fewer trustworthy chips beat many noisy ones — the trade the
  product owner endorsed.

## Validation & Tooling

- **Workstream A:** `scripts/tactic_tagger_report.py --check-goals` (raise `GOALS` to precision 0.9 for
  the in-scope motifs; recall ungated). Re-run `/tactic-tagger-report` for the full table. The CC0
  fixtures already exist; no new puzzle data needed for the in-scope motifs (fork n=2185, pin n=1739,
  skewer n=976, discovered-attack n=1461, back-rank n=1198 — all ample). (Thin motifs trapped-piece/
  promotion/en-passant/under-promotion need more puzzles, but they're not in this phase.)
- **Workstream B:** new `(flaw_move, best_line)` unit fixtures in `tests/services/test_tactic_detector.py`
  (or a sibling) + a manual prod spot-check of missed-side hanging-piece/fork tags.
- Reference: read cook.py predicates at `/home/aimfeld/Projects/Python/lichess-puzzler/tagger/cook.py`
  and `util.py`; reimplement from pseudocode (AGPL — no source copied; reviewer/grep confirms).

## Open Questions for Phase Discussion

1. One phase or two? Workstream A (detector predicate alignment) and B (call-site missed-vs-played gate)
   are independent and could split. Recommendation: one phase, B is small.
2. After re-tightening, re-backfill the dev `game_flaws` tactic columns so the prod distribution reflects
   the new detector? (Offline CC0 harness is the authoritative precision signal per D-09; re-backfill is
   cosmetic for the dev DB but needed before any prod ship.)
3. Confirm the Workstream B comparator: destination-square match only, or also require same captured-piece
   value? (Dest-square match cleanly covers the wrong-recapture case; revisit if unit fixtures surface edge
   cases.)

## Related

- SEED-057 (pin gate parity + depth bug) — resolved; pin still needs the cook `pin_prevents_*` port here.
- SEED-058 (new tactic motifs / lichess coverage), SEED-062 (tactic-comparison orientation basis).
- **Full Workstream-A per-motif spec:** `.planning/notes/tactic-tagger-cook-alignment.md` — faithful
  cook.py pseudocode (index convention, the shared `is_in_bad_spot` / ray-aware `is_defended` gaps, and
  per-motif divergences for skewer/discovered-attack/back-rank/fork/pin/anastasia/hook). This seed is the
  condensed version; that note is the implementation reference.
