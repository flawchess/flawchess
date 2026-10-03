---
phase: 225-engine-search-fixes-root-comparability-round-underfill-findability
plan: 06
subsystem: engine
tags: [findability, rankScore, typescript, vitest, treeCommon, selectBotMove]

requires:
  - phase: 225-engine-search-fixes-root-comparability-round-underfill-findability (plan 225-05)
    provides: A21 arm (root comparability guard) — this plan is independent of A21/item 1/item 2 and never touches bot-tree code
provides:
  - "rankScore(pYou, pRef, value, fallbackValue): the findability sort now blends toward V_fallback (never toward 0) — f*V + (1-f)*min(V, V_fallback), f = min(1, pYou/pRef) — fixing SEED-170 item 3 (a hard-to-find winning move no longer ranks below a much worse findable one)"
  - "rankFallbackValue(children): exported V_fallback helper — the prior-weighted mean of the root's own children, reusing backupExpectation behind an explicit zero-total guard that returns 0 (not backupExpectation's own 0.5 default), so a zero-prior root reduces to the pre-Phase-225 f*V formula (D-10b amended)"
  - "buildRankedLines computes V_fallback once per call from every root child's {prior, value}, before the scoring loop, and passes it to every rankScore call (treeCommon.ts)"
  - "P_REF_ANCHORS/pRefForElo unchanged (D-10e) — item 3 touches only the blend target, never the findability curve"
  - "Rewritten findability.test.ts (grid bounds, saturation, pRef<=0 guard, fallback-0 reduction, the D-10c clamp, rankFallbackValue normalization/zero-total/empty, and the two D-03 regression cases restated with V_fallback pinned by a stated rule) plus rewritten mctsSearch/fallbackExpectimax 'Phase 159 D-01 findability ranking', INJECT-02, and T=1/T=2 composition tests, and a new selectBotMove.test.ts D-10d bot-invariance describe"
  - "FINAL (Phase 225 measurement gate, item 3 arm): commit fd8d9200f3ec68bea2e256e57a8ba77d0d5dbb5d — the last (225-06) commit touching frontend/src/lib/engine"
affects: [225-07, 225-08, engine-search-fixes-225 measurement gate (item 3: qualitative + D-10c/D-10d unit tests)]

actuals:
  tokens: 11800
  tasks: 2
  commits: 2
  plan_head_before: 3a4ce288eb5c4dc118148ac5c6ddf11f5d29a848
  plan_head_after: fd8d9200f3ec68bea2e256e57a8ba77d0d5dbb5d

tech-stack:
  added: []
  patterns:
    - "V_fallback is computed exactly once per buildRankedLines call, over the SAME child population as the scoring loop (same `uci !== null` filter), mirroring pRef's existing once-per-call computation — never recomputed per child"
    - "rankFallbackValue reuses backupExpectation behind an explicit zero-total guard rather than hand-rolling a third expectation formula (RESEARCH C-4) — the guard's 0 default is deliberately DIFFERENT from backupExpectation's own 0.5 default (D-10b: 0 reduces rankScore to the pre-Phase-225 f*V, 0.5 would silently reintroduce an unwanted pull)"
    - "Every restated fixture pins V_fallback via a rule stated BEFORE running (unlisted prior mass valued at UNLISTED_PRIOR_VALUE = 0.5), never chosen after seeing whether a case passes (Pitfall 5)"

key-files:
  created: []
  modified:
    - frontend/src/lib/engine/findability.ts
    - frontend/src/lib/engine/treeCommon.ts
    - frontend/src/lib/engine/__tests__/findability.test.ts
    - frontend/src/lib/engine/__tests__/mctsSearch.test.ts
    - frontend/src/lib/engine/__tests__/fallbackExpectimax.test.ts
    - frontend/src/lib/engine/__tests__/selectBotMove.test.ts

key-decisions:
  - "The old two-candidate T=1/T=2 composition fixture (mctsSearch.test.ts and fallbackExpectimax.test.ts) no longer demonstrates a real T=1->T=2 reversal under D-10a — e2e4 already wins at T=1 because V_fallback pulls toward it, not away — so both files' composition tests were replaced with a three-candidate fixture (e2e3/e1d2/e2e4) whose mediocre third candidate (e1d2, -300cp) keeps V_fallback low enough at T=1 that e2e4 does not yet clear pRefForElo(600), while T=2's flattening still pushes e2e4's renormalized prior over it. Numerically verified before committing (node script), per the plan's explicit instruction to adjust cp values if the derivation disagreed."
  - "Both files' INJECT-02 tests had their organic grades SWAPPED (e2e3 10cp, e1d2 50cp, was e2e3 50cp/e1d2 10cp) so the injected-move-ranks-above-weaker-organic assertion depends on the actual rankScore comparison under the new formula, not on which organic candidate happened to already grade better under the old fixture."
  - "UNLISTED_PRIOR_VALUE = 0.5 (findability.test.ts) is the single pinned rule for every D-03 fixture's V_fallback, stated in the file before any test result — never retrofitted to make a case pass (Pitfall 5)."

requirements-completed: []

coverage:
  - id: D-10a
    description: "rankScore = f*V + (1-f)*min(V, V_fallback), f = min(1, P/Pref): f=1 gives exactly V, min(V,V_fallback) <= rankScore <= V always, a move below V_fallback sorts by its own V"
    verification:
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/findability.test.ts#rankScore — stays within [min(value, fallback), value] for every combination in the grid (D-10a invariant)"
        status: pass
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/findability.test.ts#rankScore — returns exactly value (strict equality) when pYou >= pRef — saturation at factor 1, for any fallback"
        status: pass
    human_judgment: false
  - id: D-10b
    description: "V_fallback is the prior-weighted MEAN of root children's values (normalized by total prior), 0 when total prior is 0 (not backupExpectation's own 0.5), reusing backupExpectation behind an explicit zero-total guard"
    verification:
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/findability.test.ts#rankFallbackValue — normalizes by total prior — a weighted MEAN, not the raw weighted sum"
        status: pass
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/findability.test.ts#rankFallbackValue — returns 0 (not backupExpectation's own 0.5 default) when every prior is 0"
        status: pass
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/findability.test.ts#rankFallbackValue — returns 0 for an empty list"
        status: pass
    human_judgment: false
  - id: D-10c
    description: "A low-prior move with V below V_fallback never ranks above a findable move with higher V; removing the min() clamp makes the clamp test fail"
    verification:
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/findability.test.ts#rankScore — D-10c: clamps a low-prior move already below V_fallback to its own value — never promoted"
        status: pass
      - kind: other
        ref: "Manual mutation check performed and reverted this plan (removed min() from rankScore) — see Mutation Check section"
        status: pass
    human_judgment: true
    rationale: "The mutation check is a one-time manual revert-and-confirm procedure per the project's mutation-test rule, not a repeatable automated test; recorded here as evidence."
  - id: D-10c-anchors
    description: "P_REF_ANCHORS unchanged; the D-03 cases use V_fallback pinned by 'unlisted prior mass valued at 0.5': @600 Qxf2 still beats Nb5 and Rxf2, and @1000 is restated at Qb8 0.60 vs chart 0.58 where findability still wins"
    verification:
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/findability.test.ts#D-03 regression cases (restated for D-10a) — @600 and @1000 cases"
        status: pass
      - kind: other
        ref: "grep -cE anchor pattern over findability.ts confirms all 6 P_REF_ANCHORS entries byte-unchanged"
        status: pass
    human_judgment: false
  - id: D-10e
    description: "The Phase 159 'demotes' tests in mctsSearch/fallbackExpectimax are rewritten to the new semantics (far-better hard-to-find move now ranks first); T=2 composition tests keep a real T=1->T=2 reversal through a three-candidate fixture"
    verification:
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/mctsSearch.test.ts#mctsSearch — Phase 159 D-01 findability ranking (Phase 225 D-10a/D-10e) — promotes the far-better hard-to-find move..."
        status: pass
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/fallbackExpectimax.test.ts#fallbackExpectimax — Phase 159 D-01 findability ranking (Phase 225 D-10a/D-10e) — promotes the far-better hard-to-find move..."
        status: pass
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/mctsSearch.test.ts#mctsSearch — Phase 159 policy temperature — composes with D-01 findability: reverses the T=1 winner at T=2 via a three-candidate fixture"
        status: pass
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/fallbackExpectimax.test.ts#fallbackExpectimax — Phase 159 policy temperature — composes with D-01 findability: reverses the T=1 winner at T=2 via a three-candidate fixture"
        status: pass
    human_judgment: false
  - id: INJECT-02-regression
    description: "The INJECT-02 ranking tests still fail when the injected prior is forced to 0 (fixture re-derived under D-10a), so item 3 does not silently disarm them"
    verification:
      - kind: other
        ref: "Manual mutation check performed and reverted this plan (forced injected prior to 0 in mergeExtraRootMoves) — see Mutation Check section"
        status: pass
    human_judgment: true
    rationale: "Mutation check is a one-time manual revert-and-confirm procedure, recorded here as evidence rather than a standing automated gate."
  - id: D-10d
    description: "selectBotMove picks the identical move for every permutation of the same rankedLines (blend 1, blend 0.5 with a fixed-seed rng, and with a style), proving item 3 cannot change bot play"
    verification:
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/selectBotMove.test.ts#selectBotMove — D-10d: order-invariant under any rankedLines permutation — all three tests (blend 1, blend 0.5, blend 1 + style)"
        status: pass
    human_judgment: false

duration: ~20min
completed: 2026-09-27
status: complete
---

# Phase 225 Plan 06: V_fallback Findability Ranking Summary

**`rankScore` now blends a move's practical score toward `V_fallback` — the prior-weighted mean of the root's own children, i.e. what the player scores by just playing like a human at their rating — instead of toward 0, fixing SEED-170 item 3: a hard-to-find winning move no longer ranks below a much worse findable one, while a below-average hard-to-find move is still never promoted.**

## Performance

- **Duration:** ~20 min
- **Completed:** 2026-09-27
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Fixed SEED-170 item 3 (analysis-board suggestion ordering only; bot play is provably order-independent — see D-10d below). The old formula (`min(1, pYou/pRef) * value`) scored "didn't find the move" as 0, so a hard-to-find winning move in an otherwise winning position could sort below a much worse but findable move. The new formula (D-10a) blends toward `V_fallback` instead:

  ```ts
  rankScore(pYou, pRef, value, fallbackValue) {
    if (pRef <= 0) return value;
    const f = Math.min(1, pYou / pRef);
    return f * value + (1 - f) * Math.min(value, fallbackValue);
  }
  ```

  `f = 1` still gives exactly `value` (the modal/highest-prior move can never be boosted above its own V). The `min(value, fallbackValue)` clamp is what keeps the module's founding "rankScore only demotes" argument true: without it, a hard-to-find BLUNDER (value well below V_fallback) would get pulled UP toward the average — the clamp instead lets a below-fallback move sort purely by its own (already low) value, never promoted and never further penalized.
- Added exported `rankFallbackValue(children: readonly BackupChild[]): number` (D-10b amended) — the prior-weighted MEAN over the root's own children, normalized by total prior (root priors do not sum to 1 after the hard candidate cap and injected `extraRootMoves`). Reuses `backupExpectation` behind an explicit zero-total guard that returns `0` — deliberately NOT `backupExpectation`'s own `0.5` degenerate default, because `0` is what makes `rankScore` reduce exactly to the pre-Phase-225 `f * value` formula when there is no prior mass to average over (RESEARCH C-4: no hand-rolled third expectation formula).
- `treeCommon.ts`'s `buildRankedLines` computes `V_fallback` once per call (before the scoring loop, over the identical `uci !== null`-filtered child population the loop itself scores), mirroring how `pRef` is already computed once per call — and passes it as `rankScore`'s 4th argument.
- Rewrote `findability.ts`'s module header and `rankScore`/`rankFallbackValue` docblocks to state the new invariant (`min(V, V_fallback) <= rankScore <= V`), why the clamp exists, and what `V_fallback` means. `P_REF_ANCHORS`/`pRefForElo` are byte-unchanged (D-10e — verified by the acceptance-criteria grep over all 6 anchor entries).
- Rewrote `findability.test.ts` entirely: grid-bounds invariant test, saturation, the `pRef <= 0` guard, the fallback-0 reduction to the pre-Phase-225 formula, the D-10c clamp test, three `rankFallbackValue` tests (normalization, zero-total, empty), and the two D-03 regression cases restated with `V_fallback` pinned by a stated rule (`UNLISTED_PRIOR_VALUE = 0.5`, per Pitfall 5 — chosen BEFORE running any test, never retrofitted).
- Rewrote the Phase 159 "demotes the low-prior/high-V move" tests in both `mctsSearch.test.ts` and `fallbackExpectimax.test.ts` to the new semantics: the far-better hard-to-find move (e2e4, evalCp 700) now ranks FIRST above the findable-but-worse move (e2e3, evalCp 100) — the accepted, user-confirmed reversal of Phase 159's original showcase fixture (D-10e).
- Replaced both files' T=1/T=2 policy-temperature composition tests: the OLD two-candidate fixture no longer demonstrates a real reversal (e2e4 already wins at T=1 under the V_fallback pull), so both were rewritten with a three-candidate fixture (e2e3/e1d2/e2e4) whose mediocre third candidate (e1d2, evalCp -300) keeps `V_fallback` low enough at T=1 that e2e4 doesn't yet clear `pRefForElo(600)`, while T=2's flattening still pushes it over — asserting BOTH the T=1 winner (e2e3) and the T=2 winner (e2e4) explicitly.
- Re-derived both files' INJECT-02 tests with swapped organic grades (e2e3 10cp, e1d2 50cp — was e2e3 50cp/e1d2 10cp) so the injected-move-ranks-above-weaker-organic assertion depends on the actual D-10a rankScore comparison rather than which organic candidate happened to already grade better.
- Updated the INJECT-02 comment above `mergeExtraRootMoves` (`treeCommon.ts`): under D-10a a 0 prior no longer scores exactly 0, it scores the clamped `min(value, V_fallback)` floor — but that floor still sorts below every findable move above `V_fallback`, so seeding a real (non-zero) prior for an injected candidate still matters.
- Added a new `D-10d` describe to `selectBotMove.test.ts` proving `selectBotMove` returns the IDENTICAL move for every permutation (identity, reversed, rotated, and a "findability-like" lowest-score-first order) of the same `rankedLines`, at blend 1 (argmax), blend 0.5 (a fresh fixed-seed `mulberry32` per call), and with a style applied — the structural proof that item 3 (a sort-only change) cannot change bot play, since `argmaxLine` scans every line and `botSampling.ts`'s `weightedPick` UCI-sorts before sampling.
- Performed and recorded both required mutation checks (see below): reverting the clamp or the INJECT-02 prior-seeding fix makes the corresponding tests fail; both reverted before any commit.
- Confirmed the `(225-05 A21) -> (225-06)` engine diff is limited to exactly the six files this plan declared in `files_modified`, and that `mctsSearch.ts`, `types.ts`, `botBudget.ts`, `select.ts`, `backup.ts`, `scripts`, and `bin` are all untouched (content assertion, `accept-rule.md` §1).

## Task Commits

1. **Task 1 (V_fallback ranking end to end: formula, fallback value, buildRankedLines wiring, mctsSearch ordering, RED->GREEN)** — `426c10407` (fix)
2. **Task 2 (remaining ordering tests, INJECT-02 re-derivation, D-10d bot-invariance proof, mutation checks)** — `fd8d9200f` (test)

**FINAL (Phase 225 measurement gate, item 3 arm, `reports/engine-search-fixes-225/accept-rule.md`):** `fd8d9200f3ec68bea2e256e57a8ba77d0d5dbb5d` — the last `(225-06)` commit touching `frontend/src/lib/engine`.

_Note: Task 1 carried `tdd="true"`. `findability.ts`'s `rankScore` and `treeCommon.ts`'s `buildRankedLines` were changed to the new 4-argument formula and V_fallback wiring in the same commit as the rewritten tests (per the plan's explicit "RED: rewrite findability.test.ts ... GREEN: change rankScore ... commit test and fix" single-commit instruction). RED evidence was captured by temporarily reverting `rankScore` back to the old 3-argument formula on the ALREADY-committed fix and confirming the rewritten tests fail exactly as expected — see below — then restoring byte-identical before continuing._

## RED Evidence (old 3-argument formula, Task 1)

After landing the fix, `rankScore` was temporarily reverted to the old formula (`if (pRef<=0) return value; return Math.min(1, pYou/pRef) * value;`, ignoring `fallbackValue` entirely) and the rewritten suites re-run:

```
FAIL findability.test.ts > rankScore > stays within [min(value, fallback), value] for every combination in the grid (D-10a invariant)
  AssertionError: expected 0 to be greater than or equal to 0.1
FAIL findability.test.ts > rankScore > D-10c: clamps a low-prior move already below V_fallback to its own value — never promoted
  AssertionError: expected 0.01666666666666667 to be 0.2
FAIL mctsSearch.test.ts > ... > promotes the far-better hard-to-find move ...
  AssertionError: expected 'e2e3' to be 'e2e4'
```

3 failed, 43 passed. The file was then restored byte-identical (`diff` confirmed) and re-run green (80/80 across `findability.test.ts`, `mctsSearch.test.ts`, `treeCommon.test.ts`) before continuing.

## Mutation Check (project mutation-test rule)

Both mutations were applied to a working copy, run, and reverted — restored file confirmed byte-identical via `diff` before any further work; the mutated state was never staged.

**(a) D-10c clamp: removed `min(value, fallbackValue)` from `rankScore`, leaving `f*value + (1-f)*fallbackValue`:**
```
npx vitest run src/lib/engine/__tests__/findability.test.ts -t "D-10c"
```
Result: **1 failed**. `expected 0.5666666666666667 to be 0.2` — without the clamp, the low-prior below-fallback move (V=0.2) got pulled up toward the 0.6 fallback (f=0.01/0.12≈0.083 → 0.083*0.2+0.917*0.6≈0.567), exactly the promotion-of-a-blunder failure mode the clamp exists to prevent.

**(b) INJECT-02 prior-seeding: forced `mergeExtraRootMoves` (`treeCommon.ts`) to seed every injected UCI with prior `0` (`merged.set(uci, 0)`), instead of its share of the kept candidates' mass:**
```
npx vitest run src/lib/engine/__tests__/mctsSearch.test.ts src/lib/engine/__tests__/fallbackExpectimax.test.ts -t "INJECT-02"
```
Result: **2 failed** (one per file). `expected 1 to be less than 0` in both — with the injected e2e4's prior forced to 0, its rankScore drops to `min(value, V_fallback) ≈ 0.523`, below e1d2's saturated `≈0.546`, so it sorted AFTER e1d2 instead of before it — exactly the INJECT-02 regression these tests exist to catch.

Both mutations were reverted (confirmed byte-identical to the pre-mutation files via `diff`) and the full target suite reconfirmed green: `npx vitest run src/lib/engine/__tests__/mctsSearch.test.ts src/lib/engine/__tests__/findability.test.ts src/lib/engine/__tests__/fallbackExpectimax.test.ts src/lib/engine/__tests__/selectBotMove.test.ts` — 88/88 passed.

## Files Created/Modified

- `frontend/src/lib/engine/findability.ts` — `rankScore` takes a required 4th `fallbackValue` argument (D-10a); new exported `rankFallbackValue(children)` (D-10b amended); rewritten module header and both docblocks. `P_REF_ANCHORS`/`pRefForElo` byte-unchanged.
- `frontend/src/lib/engine/treeCommon.ts` — `buildRankedLines` computes `V_fallback` once per call and passes it to every `rankScore` call; updated docblocks (the function's own header and the `mergeExtraRootMoves` INJECT-02 comment).
- `frontend/src/lib/engine/__tests__/findability.test.ts` — fully rewritten to the 4-argument signature: grid bounds, saturation, guards, the D-10c clamp, `rankFallbackValue` tests, and the restated D-03 cases.
- `frontend/src/lib/engine/__tests__/mctsSearch.test.ts` — rewrote the "demotes"->"promotes" test, replaced the T=1/T=2 composition test with a three-candidate fixture, re-derived the INJECT-02 test with swapped organic grades.
- `frontend/src/lib/engine/__tests__/fallbackExpectimax.test.ts` — mirrors the same three rewrites (parity with `mctsSearch.test.ts`, ENGINE-06).
- `frontend/src/lib/engine/__tests__/selectBotMove.test.ts` — new `D-10d` describe (order-invariance proof under three regimes: blend 1, blend 0.5, blend 1 + style).

## Decisions Made

- The old two-candidate T=1/T=2 composition fixture stopped demonstrating a real reversal once D-10a shipped (e2e4 already wins at T=1). Rather than weaken the test to a no-op assertion, both files got a three-candidate fixture verified numerically (via a scratch node script) before committing, per the plan's explicit "verify the derivation numerically before committing; if the run disagrees, adjust the cp values" instruction.
- `UNLISTED_PRIOR_VALUE = 0.5` (findability.test.ts) is the single pinned rule for every D-03 fixture's `V_fallback`, stated in the file header before any test result — the exact numbers (Vfallback ≈ 0.4258 @600, ≈ 0.529 @1000) were derived analytically and independently confirmed via a node script before being written into the test, never chosen after seeing a pass/fail.
- `rankFallbackValue`'s zero-total guard returns `0`, not `backupExpectation`'s own `0.5` — this is the D-10b-amended departure from a naive reuse, called out explicitly in both the source docblock and a dedicated unit test.

## Deviations from Plan

None — plan executed exactly as written, including the explicit "if the run disagrees, adjust the cp values" contingency for the T=1/T=2 fixture (the first candidate numbers I derived matched on the first run; no adjustment was needed).

## Issues Encountered

None. Every fixture's hand-derived numbers (via an independent node scratch script implementing `truncateAndRenormalize`, `applyPolicyTemperature`, `rankFallbackValue`, and `rankScore`) matched the actual `mctsSearch`/`fallbackExpectimax` output on the first vitest run; `eslint`, `tsc -b`, the full vitest suite (4426 tests, +7 over 225-05's 4419), `knip`, and `engine-move-quality.mjs --self-test` all passed on the first attempt after the fix.

## Verification Run Log (Task 2 full gate)

- `npx vitest run src/lib/engine/__tests__/mctsSearch.test.ts src/lib/engine/__tests__/findability.test.ts src/lib/engine/__tests__/fallbackExpectimax.test.ts src/lib/engine/__tests__/selectBotMove.test.ts` — 88 passed.
- `npm run lint` — clean (0 errors, 0 warnings).
- `npm run build` (`tsc -b` + vite) — succeeded, no type errors (confirms the single production `rankScore` call site in `treeCommon.ts` carries the required 4th argument).
- `npm test -- --run` — 276 test files, 4426 tests, all passed.
- `npm run knip` — clean (same pre-existing `.css` config hint as 225-05, unrelated).
- `node --import ./scripts/lib/frontend-alias-hook.mjs scripts/engine-move-quality.mjs --self-test` (run from repo root) — `ALL CHECKS PASSED`, exit 0.

## Content Assertion (accept-rule.md §1)

`git diff --name-only <A21 SHA> HEAD -- frontend/src` (A21 = `27beff12fb22d009b1f30c2b5552ba9cba4aad0e`, Phase 225 Plan 05's arm) returns exactly:
```
frontend/src/lib/engine/__tests__/fallbackExpectimax.test.ts
frontend/src/lib/engine/__tests__/findability.test.ts
frontend/src/lib/engine/__tests__/mctsSearch.test.ts
frontend/src/lib/engine/__tests__/selectBotMove.test.ts
frontend/src/lib/engine/findability.ts
frontend/src/lib/engine/treeCommon.ts
```
— exactly this plan's declared `files_modified`. `git diff --quiet <225-05 commit> HEAD -- frontend/src/lib/engine/mctsSearch.ts frontend/src/lib/engine/types.ts frontend/src/lib/engine/botBudget.ts frontend/src/lib/engine/select.ts frontend/src/lib/engine/backup.ts scripts bin` returns EMPTY — no bot-tree code or tooling touched.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- FINAL (`fd8d9200f3ec68bea2e256e57a8ba77d0d5dbb5d`) is ready for the Phase 225 measurement gate's item-3 qualitative check (a handful of winning positions where a hard-to-find move previously ranked below a much worse findable one) plus the D-10c/D-10d unit tests already committed here.
- No blockers. Item 3 is fully independent of items 1/2 and the A21 arm — it never touches `mctsSearch.ts`, `types.ts`, `botBudget.ts`, `select.ts`, `backup.ts`, or any bot-tree code, and D-10d structurally proves bot play cannot change as a result.
- Plans 225-07/225-08 can proceed independently against this commit.

---
*Phase: 225-engine-search-fixes-root-comparability-round-underfill-findability*
*Completed: 2026-09-27*

## Self-Check: PASSED

- FOUND: frontend/src/lib/engine/findability.ts
- FOUND: frontend/src/lib/engine/treeCommon.ts
- FOUND: frontend/src/lib/engine/__tests__/findability.test.ts
- FOUND: frontend/src/lib/engine/__tests__/mctsSearch.test.ts
- FOUND: frontend/src/lib/engine/__tests__/fallbackExpectimax.test.ts
- FOUND: frontend/src/lib/engine/__tests__/selectBotMove.test.ts
- FOUND commit: 426c10407 (fix, Task 1)
- FOUND commit: fd8d9200f (test, Task 2, FINAL)
