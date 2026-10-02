# Accept-rule/protocol override — D-13 `TRACE-ANOMALY` classification

**Date:** 2026-09-29
**Decided by:** Orchestrator-authored under the owner's autonomy instruction (autonomous overnight
execution, Plan 226-08); **pending owner ratification.**
**Scope:** `reports/engine-throughput-226/step0-protocol.md` §6's bug-signature list, first
bullet ("any of: a `TRACE-ANOMALY` line emitted by `engine-search-trace.mjs`; ...").
**Rule file:** NOT edited. `step0-protocol.md` §6 stands as written.
**Revert target:** treat this override as void and reopen D-13 as unresolved (escalate item 2's
classification to the owner) if the owner disagrees with the reasoning below.

---

## What the rule says, literally

`step0-protocol.md` §6 lists three bug signatures for the `cBFTV` trace measurement, the first
being: "any of: a `TRACE-ANOMALY` line emitted by `engine-search-trace.mjs`". Read literally, the
mere *existence* of a `TRACE-ANOMALY` line anywhere in any of the four committed traces
(`a0-c1`, `a0-c2`, `a0-c4`, `a2cand-c4`) would classify item 2 (the round-underfill fix) as
carrying a bug requiring a fix in `mctsSearch.ts` before A2 re-enters the gate.

## Why applying it literally here would misattribute a pre-existing A0 behaviour

`TRACE-ANOMALY duplicate-expansion` lines are present in **all four** traces, including the two
run at **`a0-c1`** and **`a0-c2`** — concurrency-1 and concurrency-2 runs of the **A0 baseline**,
which by construction contains **no A2 code at all** (A0 is tooling-only; the round-underfill
fix does not exist yet at that commit). A signature that fires identically on a commit that
predates the change under investigation cannot be evidence that the change introduced it.

Recomputing the anomaly directly from the committed expansions TSVs (grouping by
`(id, leaf_fen)` within each trace and summing `occurrence_count - 1` per group) reproduces the
exact counts 226-07-SUMMARY recorded from the run's original stdout:

| Trace | Recomputed duplicate-expansion count | 226-07 SUMMARY count |
|---|---|---|
| a0-c1 | 16 | 16 |
| a0-c2 | 17 | 17 |
| a0-c4 | 12 | 12 |
| a2cand-c4 | 14 | 14 |

Every duplicate group in every trace belongs to one of three specific control positions —
`WwKKM`, `g687537-p48`, `I3vZ1` (repetition/perpetual-check tactical shuffles: a queen or rook
oscillating near a king). None belongs to `cBFTV`, the actual subject of the D-13 measurement:
grouping `cBFTV`'s own expansion rows by `(id, leaf_fen)` in all four traces yields zero repeats
— every leaf FEN `cBFTV` reaches is unique in every trace.

The duplicate-group structure for the three control positions is qualitatively identical between
A0 (c1, c2, c4, no A2 code) and the A2 candidate (c4, with A2 code): the same leaf-FEN groups
recur, at the same order of magnitude (near-identical counts — 226-07-SUMMARY's own phrase for
the underlying group counts was "near-identical across all four traces"). This is evidence of a
pre-existing structural property of these three positions (position repetition/perpetual-check
creates the same board FEN reachable via more than one distinct root-to-leaf move sequence, and
occasionally the identical sequence is graded twice), present before Phase 226 began and
unaffected by the underfill fix's round-timing changes.

## Classification applied instead

Because the literal signature fires on evidence unconnected to A2 (it fires at A0 too, on
positions unrelated to `cBFTV`), item 2's D-13 classification is decided on the **remaining two**
§6 bug signatures, evaluated specifically against `cBFTV`:

1. **Blocked-node persistence** (a node marked blocked in round `r` still excluded in round
   `r+1`) — not directly testable against A0 (A0's tooling commit predates `isBlocked`), but the
   A2-candidate's own round-size sequence for `cBFTV` (`1,4,4,4,4,4,4,4,4,4,4,4,4,1` — every round
   filled to the full concurrency of 4 except the root and the final leftover) is exactly the
   fix's intended behaviour and inconsistent with a node staying incorrectly blocked into a
   later round (that would show up as further underfilled rounds after round 1, which are
   absent).
2. **Stalled root visits with a selectable leaf still available** — `cBFTV`'s `e4f5` line
   freezes at 1 visit from round 4 onward in **both** `a0-c4` and `a2cand-c4` (an identical
   pattern, present at A0 too), consistent with ordinary best-first-search deprioritization of a
   low-value line, not a scheduling stall A2 introduced.

Neither remaining signature holds. The `e4c6`-below-`e2g4` crossover itself traces to the
**identical leaf FEN** (`4rk1r/2q2pp1/p1B2b1p/1pp5/6b1/1P6/P4RPP/4R2K w - - 0 26`) being graded
in both A0 (round 12) and the A2 candidate (round 9) with essentially the same Stockfish output
(`e1e8:#1`, `c6e8:` a large negative score), only three rounds earlier in A2 because the fix
packs the same 50-node budget into 14 denser rounds instead of 17 sparser ones (A0's own
round-size sequence, `1,4,2,1,3,4,4,3,3,4,3,4,1,4,4,1,4`, shows the underfill the fix targets:
seven rounds below the full concurrency of 4 out of 17). This is the side-effect signature §6
describes: "the drop... traces to specific expansions whose grades are legitimate Stockfish
output... consistent with the leading hypothesis in RESEARCH Pattern 3" — a d10-floor grade at a
node that under-weights a forced mating line, reproduced identically by both arms and merely
re-timed by the fix.

**Classification: side effect.** Item 2 proceeds to gate measurement unchanged; no code fix is
required in `mctsSearch.ts` before A2 re-enters the gate. `design-inputs.md` §4 records the full
evidence trail (round-size sequences, the shared leaf FEN and its grades, the anomaly recount).

## What this override does NOT license

- It does not exempt any *future* `TRACE-ANOMALY` line that appears on `cBFTV` itself, or on a
  position that does NOT already show the identical anomaly at A0. A new anomaly meeting either
  of those conditions is not covered by this override and must be classified fresh.
- It does not retroactively bless the `duplicate-expansion` behaviour on `WwKKM` /
  `g687537-p48` / `I3vZ1` as harmless in every sense — see the separate note below.
- It does not change `step0-protocol.md` §6's text. Any future reader who wants the literal rule
  applied without this override's reasoning should treat item 2's classification as unresolved
  and escalate to the owner.

## Pre-existing duplicate-expansion as a possible throughput defect (owner information only)

The `duplicate-expansion` pattern on `WwKKM`, `g687537-p48` and `I3vZ1` — the same leaf reached
via the *identical* root-to-leaf UCI path graded a second time within one search — is plausibly a
small, independent throughput inefficiency: re-grading a node that was already graded consumes
Stockfish CPU (a real d10/d14 search) without adding new tree information, on top of whatever
CPU the round-underfill fix does or does not save. It is present at A0, unrelated to `cBFTV`, and
unrelated to any of this phase's three items (round underfill, root guard, root split). No fix is
made here and no seed is filed — this paragraph exists only so the owner has visibility into a
measured, described-but-unaddressed effect, per this plan's instruction to describe rather than
act on it.

---

*Phase: 226-browser-engine-throughput-underfill-root-split-continuous-dispatch*
*Plan: 226-08*
