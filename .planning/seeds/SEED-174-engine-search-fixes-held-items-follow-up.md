---
id: SEED-174
status: dormant
planted: 2026-09-28
planted_during: Phase 225 close (engine search fixes — root comparability, round underfill,
  findability fallback)
trigger_when: a future engine-search unit is willing to re-measure the round underfill fix from
  scratch with a wider or re-derived move-quality fixture, and/or investigate the calibration
  drift that made Phase 225's own unchanged baseline fail against the July-21 curves
scope: SEED-170 items 1 (root comparability guard on the bot's clear-winner early stop) and 2
  (round underfill fix in selectPath) — both held at Phase 225's pre-registered gate; D-14
  forbids a refit or recalibration as the remedy, so this is a follow-up unit, not a rerun
---

# SEED-174: Phase 225 held items — round underfill (item 2) and root comparability guard (item 1)

Phase 225's gate (`reports/engine-search-fixes-225/accept-rule.md`, rendered by
`scripts/engine_search_fixes_verdict.py gates`) held both bot-tree items. Per D-14, the phase does
NOT refit or recalibrate to make them pass — both are reverted from the phase branch (revert
commits `e20ca2e4c`, `3015aa03f`, `ed99c22d5`, `e01e56e41`, `11118b230` in
`225-08`) and captured here as a follow-up. Full numbers: `reports/engine-search-fixes-225/report.md`.

## Item 2 — round underfill fix in `selectPath` (held)

**Failing criterion:** MQ-2 (move quality, A2 vs A0, stop rule off). A2 stop-off has **5**
move-quality regressions against A0 stop-off's **4** (`es(bot_move) - es(correct) <= -0.05`).
The extra regression is a **confirmed** pass-to-regression flip on fixture position `cBFTV`
(A0 correctly plays `e4c6`, es 0.975; A2 plays `e2g4`, es 0.405) — confirmed by a fresh-process
rerun reproducing the same flip byte-for-byte, per the project's re-run-before-trusting-a-flip
rule. All other 11 of the 12 maia-blindness positions are identical between A0 and A2.

Throughput itself passed cleanly (T-50 ratio 0.9450, T-400 ratio 0.9529, both well under the 1.05
no-regression bound) — the underlying bug (round collapse to 1-2 effective concurrency on peaked
positions) is real and the fix's throughput behavior is not in question. What failed is a single
move-quality fixture row, on a 12-position fixture with no slack for a single flip (base
regression count 4 of 12).

**Arm SHAs:** A0 `1b5313b9648d9be1116bb519a1d51e8627f3ec15`, A2
`a9d5113efed9270d02692c9b97e87508ecc414b2`.

**Calibration:** `item2_pass = false` (see below — item 2's own calibration attribution
(`a2_vs_a0`) also fails, independently of MQ-2).

## Item 1 — root comparability guard on the clear-winner stop (held)

**Failing criterion:** held automatically because item 2 (which A21 stacks on top of) is held —
D-14/D-13's rule states item 1 was never measured without item 2, so item 1 cannot ship
regardless of its own numbers once item 2 fails. For the record, item 1's own criteria on their
own numbers: S1 passed (A21 max wall 8,343 ms, well under the 12,100 ms ceiling), S2 passed (A21
retained all 10 of A2's early stops), and MQ-1 passed (A21 stop-on 4 regressions, matching A2's 4
exactly, no flip). Item 1's bot-tree code itself introduced no new move-quality regression on
this fixture.

**Arm SHA:** A21 `27beff12fb22d009b1f30c2b5552ba9cba4aad0e`.

## Calibration (both items)

The primary calibration verdict (A21 vs the committed July-21 curves) **fails**: Maia pooled
shift **-97.9** (se 41.4, threshold ±85.0, outside), SF pooled shift **-40.0** (se 32.9, threshold
±50.0, within). This routed to the pre-registered `decision` branch (D-13 amended), which measured
A0 and A2 against July-21 too:

| Verdict | Result | Maia pooled shift | SF pooled shift |
|---|---|---|---|
| a21-vs-july (primary) | fails | -97.9 | -40.0 |
| a0-vs-july | fails | -71.9 | -81.4 (outside) |
| a2-vs-july | void | -73.5 | +29.2 |
| a2-vs-a0 (item 2 attribution) | fails | +4.0 | +117.2 (outside) |
| a21-vs-a2 (item 1 attribution) | fails | -30.5 | -67.5 (outside) |

`a0-vs-july` fails (SF family outside its own threshold), so `baseline_drift = true`: **Phase
225's own unchanged baseline (`main`'s engine code plus only harness tooling) already fails the
same parity check against the July-21 curves.** Per the decision-branch table, with drift: item 2
passes iff `a2_vs_a0` holds (it does not — fails), so `item2_pass = false`; item 1 passes iff item
2 passes AND `a21_vs_a2` holds — item 2 already fails, so `item1_pass = false` regardless.

This baseline drift is a fact worth carrying into any follow-up: whatever moved the SF-family
pooled shift outside threshold at A0 predates any Phase 225 code change, and a future unit
re-measuring item 2 or item 1 alone will hit the same drift unless it is investigated first (or
the follow-up unit's own accept rule accounts for it explicitly, the way Phase 225's decision
branch did).

## What NOT to do

**D-14 forbids a refit or a 24-persona recalibration as the remedy for this held result — under
any outcome.** A held item is a first-class phase result, not an invitation to retune thresholds
or curves after seeing the data. Any follow-up must be its own new unit, with its own
pre-registered accept rule, not a re-run of Phase 225's own accept rule with adjusted numbers.

## Related

- `reports/engine-search-fixes-225/accept-rule.md`, `reports/engine-search-fixes-225/report.md`,
  `reports/engine-search-fixes-225/verdict.json`.
- `.planning/seeds/closed/SEED-170-engine-root-comparability-and-round-underfill.md` — the parent
  seed.
- `.planning/seeds/SEED-173-engine-non-root-candidate-cap.md` — item 4 and the flatness/deadline
  guarding idea, deferred separately.
- `reports/bot-parity-199/report.md` — the calibration parity rule this phase reused verbatim,
  and the Phase 199 pooled shifts (Maia -57.7, SF -9.9) this phase's own shifts sit next to as
  context.
