---
id: SEED-261122-s0j
status: dormant
planted: 2026-11-22
planted_during: Phase 259 (facepalm first-principles refit), owner question about pawn breakthroughs
trigger_when: after Phase 259 ships, or when the next facepalm material-rule change or material re-backfill is planned (bundle with it)
scope: medium. One phase, backend only. The rule change is small; the cost is the material re-backfill (prod and benchmark) and the coefficient refit
---

# SEED-261122-s0j: Facepalm material rule: count promotions as material

## Why This Matters

The facepalm score is blind to pawn breakthroughs. `app/services/line_material.py` counts captures only
("promotions are not material"), and the score has no eval term to fall back on (it reads Maia probabilities
and the two material numbers only). So a blunder that allows a pawn to queen, or misses one's own
breakthrough, behaves as if nothing was lost:

- `material_loss` / `material_missed` are 0 for the promotion itself.
- The row is typed `missed_win` instead of `allowed_loss`, because `loss = 0`.
- The key-move term reads `maia_best_prob` instead of `maia_best_reply_prob`, so an "allowed a breakthrough"
  blunder is scored on the wrong move.
- A captured promoted piece is mispriced: the capturer is credited 9 although the owner invested only a pawn,
  so stopping a pawn by taking it on the queening square looks like winning a queen.

Some of these blunders are very obvious (a pawn one or two steps from queening, simply not stopped) and are
exactly the rows where a zero is most wrong.

## Proposal

- Credit a promotion at the promoting ply as the promoted piece minus the pawn (+8 for a queen), for the side
  that promotes.
- Treat a promotion as non-quiet, so the quiet walk continues through an immediate recapture. This also fixes
  the captured-queen mispricing.
- Do NOT extend the 9-ply horizon. The obvious cases fall inside it, and deep breakthroughs are the
  hard-to-see ones the decaying mean already discounts (depth 9 carries about 3% of the weight). Lines where
  the engine sees an unstoppable pawn but the stored line ends before it queens stay invisible; accepted.

## Evidence

Dev DB, 2026-11-22, 21,147 scored rows at the top severity (assumed to be the blunder level, enum not
checked). Promotions by either side are counted, so these are upper bounds.

| Refutation line | Rows | Of which `material_loss = 0` |
|---|---|---|
| Promotion within 9 plies | 456 (2.2%) | 274 (1.3%) |
| Promotion beyond 9 plies | 97 | 57 |

Another 95 rows have a promotion in the best line with no material in either line (missed breakthroughs).
Stored lines average about 11.4 plies.

## When to Surface

**Trigger:** after Phase 259 ships, or when the next facepalm material-rule change or material re-backfill is
planned. Bundle it with that work, since any rule change pays the same backfill cost.

## Scope Estimate

**Medium.** The code change is confined to the counting rule in `line_material.py` (`_victim_value`,
`_count_step`, `_quiet_walk_end`) and its tests. Per 259 D-05, a change to the material rule needs a re-run of
the material backfill (prod and benchmark) and a coefficient refit.

Open question to settle first: do the owner's labelled rows contain enough promotion cases to move the fit, or
does the refit just reproduce the current coefficients?

## Breadcrumbs

- `app/services/line_material.py` — the quiet-point walk and the "captures only" rule (module docstring).
- `app/services/facepalm_material.py` — `decaying_mean`, `loss_by_depth`, `gain_by_depth`.
- `app/services/facepalm_score.py` — the type rule and the key-move term gated on `loss > 0`.
- `app/services/facepalm_inputs.py` — the write-time caller.
- `.planning/phases/259-facepalm-first-principles-refit/259-CONTEXT.md` — D-02 (quiet rule), D-03 (decaying
  mean), D-05 (rule changes need a backfill).
- Related seeds: SEED-261121-tau (first-principles refit), SEED-261122-j9p (facepalm as a move quality).
