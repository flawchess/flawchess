---
id: SEED-261122-s0j
status: closed. Milestone v2.31.
closed: 2026-11-23
closed_reason: shipped as Phase 262 (promotions as material, key-move gate on the type rule, refit; release #506; prod promotion pass 124,216 rows). The benchmark DB pass stays with SEED-261120-bzq
promoted_to: Phase 262 (2026-11-23)
planted: 2026-11-22
planted_during: Phase 259 (facepalm first-principles refit), owner question about pawn breakthroughs
trigger_when: after Phase 259 ships, or when the next facepalm material-rule change or material re-backfill is planned (bundle with it)
scope: medium. One phase, backend only. The rule change is small; the cost is the material re-backfill (prod and benchmark) and the coefficient refit
---

# SEED-261122-s0j: Facepalm material rule: count promotions as material

**Promoted 2026-11-23 to Phase 262** (`.planning/ROADMAP.md`), together with the key-move gate fix (see the
refinement at the end).

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

## Refinement 2026-11-23 (readiness review, before Phase 262)

Replay of all 21,147 scored dev blunders (severity 2) with promotions counted as material; the replay reproduces
every stored `material_loss` / `material_missed` under the current rule. Probe:
`.planning/phases/262-facepalm-promotions-and-key-move-gate/spike/promo_probe.py`.

| Effect of counting promotions | Rows |
|---|---|
| A promotion token in either line or the played move | 797 (3.8%) |
| Inputs change | 624 (3.0%) |
| Loss up / down | 354 / 53 |
| Missed up / down | 241 / 102 |
| Score up / down | 497 / 127 |
| Enters / leaves the 0.7 cut | 121 / 25 |
| Type missed win to allowed loss / reverse | 243 / 44 |

About 6,690 rows pass 0.7 today, so the net change is about +1.4%.

- **The evidence above was one-sided.** It counts only blunders the score misses. The captured promoted queen is
  a false-alarm source too: 102 rows lose missed gain and 25 leave the cut.
- **Smaller code change.** Adding the promotion gain inside `_victim_value` covers the quiet walk, the first
  move and the end-of-line static exchange; `_count_step` and `_quiet_walk_end` need no change. A blunderer's
  promotion then has a non-zero value, so it no longer sets the desperado square; pin that with a test.
- **Open question answered.** At least 13 of the 291 labelled rows have a promotion as the best move or the
  reply (6 labelled 1, 7 labelled 0; the features TSV holds no full lines, so this is a lower bound). The refit
  must be re-run; a promotion is not automatically a facepalm.
- **Targeted backfill.** Only rows with a promotion token can change, so the prod pass covers about 3.8% of the
  rows. Run it before the benchmark backfill of SEED-261120-bzq.

### Key-move gate (added to the phase by the owner, 2026-11-23)

The key-move term is gated on `loss > 0`, the type on `loss > 0 and loss >= missed`. Any loss above zero swaps
the best-move term (coefficient 2.08) for the reply term (0.91).

| Group (dev, 21,147 rows) | Rows | Mean score | Share at 0.7 or above |
|---|---|---|---|
| Allowed loss | 10,974 | 0.634 | 49.6% |
| Pure missed win (loss 0, missed above 0) | 5,265 | 0.235 | 10.4% |
| No material in either line | 3,180 | 0.073 | 0.1% |
| Loss above 0 but typed missed win | 1,728 | 0.568 | 40.1% |

- At zero missed gain, rows with a loss between 0 and 0.2 average 0.245 against 0.073 at zero loss. With a missed
  gain of 1.5 or more, 37.0% pass 0.7 against 23.8%.
- Scoring the 1,728 mixed rows on the best move with today's coefficients would take 345 out of the cut and
  bring 49 in. This is an upper bound without a refit.
- The promotion rule moves 243 more rows across the gate. Dev game 1457348 ply 99 goes from 0.00 to 0.92 on an
  added loss of 2.42.
- Decision: gate the key-move term on the type rule, in the same phase and the same refit.

### Checked and dropped

- Draw blunders: stalemate, dead position or threefold within 9 plies of the played line occur in 29 rows
  (0.14%). Not worth a rule.
- Blunders with no material in either line (15%) stay a known limit of a material-based score.
