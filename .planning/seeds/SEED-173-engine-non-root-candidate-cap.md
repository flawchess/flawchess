---
id: SEED-173
status: dormant
planted: 2026-09-28
planted_during: Phase 225 close (engine search fixes — root comparability, round underfill,
  findability fallback)
trigger_when: deep-node MultiPV grading cost shows up as a bottleneck after the round-fill fix
  ships (a follow-up to SEED-174, since item 2 is currently held), or the next engine milestone,
  whichever comes first; separately, the flatness-branch/deadline-cut guarding half revisits only
  if a future measurement shows the D-04 deadline exposure is high
scope: a candidate-count cap (~6-8) below the root in truncateAndRenormalize (SEED-170 item 4);
  and, independently, whether to guard the near-tie (flatness) branch or the wall-clock deadline
  cut in the bot's early-stop rule
---

# SEED-173: Non-root candidate cap, and the deferred flatness/deadline guarding idea

Two independent deferred ideas from Phase 225 (SEED-170), captured together at phase close per
D-15 and the "Deferred Ideas" section of `225-CONTEXT.md`.

## 1. Non-root candidate cap (SEED-170 item 4, D-15)

`truncateAndRenormalize` has no count cap on non-root nodes; only the root gets
`ROOT_CANDIDATE_HARD_CAP = 15`. `applyPolicyTemperature` also reshapes non-root nodes where the
root player moves, so at temperature up to 2.0 a deep node can need 20+ moves to reach the 0.9
probability mass. Each extra candidate adds a MultiPV line to that node's grade (cost roughly
linear in candidate count), while a 2%-prior tail move barely changes the expectation.

A cap of ~6-8 is a one-constant change, but it changes bot strength (fewer candidates considered
at deep non-root nodes shifts the expectimax average), so it needs its own throughput and
calibration arm for attribution — it cannot be folded into another item's measurement. Its
benefit (MultiPV cost reduction at high-temperature deep own-nodes) is unmeasured; Phase 225 did
not build any instrumentation for it. Item 2's throughput win, had it shipped, would have reduced
the urgency (round underfill was the larger confirmed bug); with item 2 currently held (see
SEED-174), this item's priority is unchanged from Phase 225's original assessment — still
deferred, not elevated.

**Revisit when:** deep-node MultiPV grading cost is independently identified as a bottleneck (a
future throughput measurement showing grade CPU dominated by non-root, high-candidate-count
nodes), or at the next engine milestone generally.

## 2. Guarding the flatness branch and the deadline cut (D-03/D-04)

Phase 225's root comparability guard (item 1, held — see SEED-174) only ever proposed guarding
the clear-winner branch of the bot's early-stop rule. Two related spots were deliberately left
unguarded regardless of item 1's own outcome:

- **The flatness (near-tie) branch** (D-03): fires when every root child is within 0.02 of each
  other. Stopping on a near-tie is low-stakes — whichever move is nominally "ahead" by a hair is
  not a meaningfully different recommendation — so this was never a guard candidate, only a
  documented residual.
- **The wall-clock deadline cut** (D-04, `deadlineSearch.ts`): never waits on anything, because a
  guard could overrun the deadline and make the bot flag. `botBudget.ts` already documents a
  deadline-cut bot as intentionally weaker.

Phase 225 measured the deadline cut's exposure (report-only, never a gate criterion): **18%**
(0.18) of post-`minNodes` snapshots across the 16-position stop-rule set had an unsettled
in-window root child on the board when a deadline cut fired, pooled across arms A2 and A21 (both
arms show the identical fraction — see `reports/engine-search-fixes-225/report.md`, "D-04
deadline exposure"). The accept rule's own caveat applies: this metric cannot see `isClosed`
through `RankedLine`, so a terminal root child would be a false positive, though the measured
16-position set has none.

**Revisit only if** a future measurement shows this exposure fraction is high (18% was not judged
against any pre-registered bar in Phase 225 — it was report-only by design, D-04 — so whether 18%
counts as "high" is an open question for whoever revisits this, not a threshold Phase 225 set).

## Related

- `.planning/seeds/closed/SEED-170-engine-root-comparability-and-round-underfill.md` — the
  parent seed this phase resolved (items 1-3 measured; item 1 and 2 held, item 3 shipped, item 4
  deferred to this seed).
- `.planning/seeds/SEED-174-engine-search-fixes-held-items-follow-up.md` — the held-item
  follow-up (items 1 and 2, MQ-2 regression and calibration failure).
- `reports/engine-search-fixes-225/accept-rule.md`, `reports/engine-search-fixes-225/report.md`.
