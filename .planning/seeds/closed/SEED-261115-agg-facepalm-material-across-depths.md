---
id: SEED-261115-agg
status: closed. Milestone v2.30.
closed: 2026-11-18
closed_reason: shipped as Phase 256 (refit on the decaying mean over odd depths, squash-merge b2a66e3b7, release #486). Successor: SEED-261117-hfb (validation against Lichess puzzle ratings)
promoted_to: Phase 256 (2026-11-16)
planted: 2026-11-15
planted_during: Phase 254 plan 11 (refit with the set 7 miss labels); owner review of the fit
trigger_when: the next facepalm refit. Best after Phase 252's prod line repair and the gap-fill line pass (Phase 254 D-21), when more label rows have a best line and deeper depths are better covered.
scope: small to medium. No backfill and no new stored facts (all depths 1-9 of both lines are stored, the score is computed at query time). Fit tooling tries aggregate material inputs, both score twins get the chosen aggregate, one refit and a constants release.
---

# SEED-261115-agg: Facepalm material inputs aggregated over all depths, not read at depth 3

The score reads the played line's loss and the best line's missed gain at one depth (`LINE_DEPTH` = 3). The
owner finds a single depth unintuitive, and for misses depth 3 looks like the worst choice. Test inputs that
summarise the whole stored line: how much is gained or lost once the line settles, and how soon.

## Why This Matters

The 2026-11-15 refit (Phase 254, `reports/blunder-check/facepalm-fit-2026-11-15.md`) gave the missed gain a
coefficient of 0.0891 against 1.0129 for the loss. Pure misses can reach about 67% at most, so only the cut
of 0.50 lets them into the drill. The owner's two fixture misses (games 817357 ply 24 and 820181 ply 65)
score 0.15, and 9 of the owner's 15 commented set 7 rows miss their expected range.

Among the 63 labelled pure misses the fair share is about 30% at every missed size (only missed mates stand
out: 5 of 6 fair), while the best-move probability separates them (2 of 27 fair below 30%, 19 of 36 above).
So size at depth 3 carries no signal; the open question is whether a better material summary does.

## Evidence (2026-11-15, single input, no model, not cross-validated)

221 decided labels in `reports/blunder-check/facepalm-features-2026-11-15.tsv`. AUC of the input alone
against the owner's labels; pure misses as defined by the depth-3 rule (59 rows).

Single depths:

| Depth | Loss, all rows | Missed size, pure misses | Pure misses at that depth |
|---|---|---|---|
| 1 | 0.76 | 0.65 | 45 |
| 3 | 0.80 | 0.53 | 59 |
| 5 | 0.75 | 0.64 | 50 |
| 7 | 0.73 | 0.66 | 54 |
| 9 | 0.70 | 0.67 | 49 |

Aggregates over the stored depths:

| Aggregate | Loss, all rows | Missed size, pure misses |
|---|---|---|
| Depth 3 only (shipped) | 0.80 | 0.53 |
| Mean of all depths | 0.77 | 0.60 |
| Median | 0.76 | 0.63 |
| Last known depth | 0.70 | 0.61 |
| Lowest point of the line | 0.78 | 0.68 |
| Highest point of the line | 0.69 | 0.52 |

- Losses: depth 3 stays the best single input; the lowest point and the mean are close.
- Misses: every aggregate except the highest point beats depth 3; the lowest point of the best line (the gain
  that is there at every depth) is the best.
- Mid-exchange spikes explain it. One label row's best line reads 1, 1, 1, 1, 10, 10, 1, 1, 1: a queen trade
  in progress at depths 5 and 6, a real gain of 1.
- Coverage: an aggregate uses whatever depths exist, so 211 label rows get a loss value against 199 at
  depth 3. On prod 16.1% of user-side blunders are unscored today because the played line stops before
  depth 3 (`reports/maia-flaws-backfill/prod-facepalm-line-pass-254.md`).
- Caution: about 59 pure misses, so AUC differences of 0.1 are within the noise (roughly +-0.08). Enough to
  justify the test, not to change the model.

## What a plain aggregate loses

Depth also says how soon the consequence arrives, which is part of how obvious a blunder is: a piece lost
on the next move is a facepalm, the same piece lost eight plies later is a deep tactic. That is the likely
reason depth 3 beats the mean for losses and "last known depth" is the worst.

## Candidate inputs to test

1. Settled gain / loss: the lowest point of the best line for gains, and the matching robust value of the
   played line for losses (ignores mid-exchange spikes).
2. How soon it materialises: the first depth at which the gain or loss appears and then stays.
3. For comparison: the single depths 1, 5, 7, 9 for the missed term, with the loss kept at depth 3.
4. Other ideas raised in the same review, untested: "the gain is a simple capture of an undefended piece";
   "the best move is the only winning move"; a separate small model for pure misses (overfit risk with
   about 60 rows).

All of 1 to 3 come from the stored arrays (`played_line_material`, `best_line_material`, 9 slots), so no
prod pass is needed; even slots are mid-exchange values by construction (Phase 254 D-17).

## Constraints

- Keep the query-time design (Phase 254 D-01): the chosen aggregate must be expressible in the SQL twin over
  the stored arrays, with the Python twin kept in parity.
- Cross-validate inside the full model with repeated seeds, as `fit_facepalm.py` does for the forms; choose on
  seed means, prefer fewer coefficients on a tie.
- Keep the owner's label meaning (label 1 = "should score above 70%", D-23) and re-check the 15 commented
  set 7 rows and the two owner fixtures under the new model.
- More miss labels would help more than any input change if the differences stay inside the noise.

## Carried over from the Phase 254 code review (2026-11-16)

Two review findings touch the fit and belong in this refit (details in
`.planning/phases/254-facepalm-score-missed-gains-and-loss-aversion-knob-seed-2611/254-REVIEW.md`):

- **WR-01:** a NULL `maia_best_prob` adds 0 to the best-move term, so the row scores as if the best move were
  as easy as possible. On prod 14,826 of 2,178,931 rows with scoring inputs (0.68%) have a NULL best prob.
  Decide: leave such rows unscored, or use a neutral constant.
- **WR-03:** `fit_facepalm.py` drops every row with a NULL `reply_spread`, although the gated spread forms never
  read it on no-loss rows. This thins the miss-heavy part of the fit.

## Probe of 2026-11-16 (after Phase 254 shipped; owner review)

Owner's goal: a meaningful score. How many pure misses pass the drill cut is secondary.

Quick harness on `facepalm-features-2026-11-15.tsv` (full model, 10-fold cross-validation over 10 seeds; not
`fit_facepalm.py`, so the numbers are indicative). The same aggregate is used for the loss and the missed gain,
over the odd depths 1, 3, 5, 7, 9 (even slots are mid-exchange values). AUC on the same 199 rows:

| Input for both terms | AUC |
|---|---|
| Decaying mean, each later odd depth counts half (weights 1, 1/2, 1/4, 1/8, 1/16, normalised over known depths) | 0.916 |
| Plain mean | 0.896 |
| Depth 3 (shipped) | 0.880 |
| First stable value (same balance at two odd depths in a row), discounted by its onset | 0.872 |
| First stable value | 0.860 |
| Value of the longest run | 0.845 |
| Most frequent value | 0.842 |
| Final stable value (= last depth) | 0.832 |
| Lowest point | 0.778 |

- Decaying mean against depth 3, paired bootstrap: AUC gain 0.035, 95% range 0.007 to 0.065. Decay 0.2 to 0.6
  gives 0.914 to 0.918, so fix the decay at 1/2 and do not fit it. Held out: wins on set 6 (0.945 vs 0.904) and
  set 7 (0.905 vs 0.875), loses on set 5 (0.934 vs 0.954). Best of about 11 candidates, so the gain is optimistic.
- The gain coefficient rises from 0.15 to 0.39, so misses get a real material signal and the lambda knob matters.
- Stabilised balance (owner's idea) loses to depth 3: the early swing is itself the signal (rows like
  `-3, -3, 0, ...` are labelled fair), and 36 of 198 full played lines still change at depth 9. Only 26 of 199
  rows move their loss input by a pawn or more between depth 3 and the decaying mean, so few labels can tell the
  rules apart. Keep "first stable value, discounted" as a candidate for the refit.
- Within pure misses the best-move probability carries the ranking (AUC 0.80 alone); a pure-miss offset fits
  negative, so the low miss pass rate is what the labels ask for.
- Among "neither" rows the largest loss at any depth has AUC 0.73 (23 rows).

## Decided with the owner (2026-11-16)

- Refit around the decaying mean; candidates in `fit_facepalm.py`: decaying mean, first stable value
  (discounted), depth 3 as the reference.
- Label set 8, about 60 rows, blind, appended to `reports/blunder-check/facepalm-labels.tsv` (the same file as
  sets 1 to 7): about 45 rows where depth 3 and the decaying mean differ by a pawn or more (losses recovered by
  depth 3, losses that appear at depth 5 or later, mid-line spikes; split between losses and misses) and about
  15 plain pure misses. No short-line group: Phase 252 repairs truncated lines.
- Open for the phase: the "loses material" gate (loss > 0 flips on any small late loss under a mean; test a
  threshold of 1 against no gate), WR-01, WR-03.
- Order: a quick task for the sampler and the draw now, then a phase for the refit, executed once set 8 is labelled.

## Promoted (2026-11-16)

Phase 256 in ROADMAP.md. Decisions from the discuss phase:
`.planning/phases/256-facepalm-refit-material-aggregated-over-depths/256-CONTEXT.md`.
