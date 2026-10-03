---
phase: 226-browser-engine-throughput-underfill-root-split-continuous-dispatch
verified: 2026-10-02T08:15:00Z
status: passed
score: 9/9 must-haves verified
covered_files:
  - .planning/phases/226-browser-engine-throughput-underfill-root-split-continuous-dispatch/226-01-PLAN.md
  - .planning/phases/226-browser-engine-throughput-underfill-root-split-continuous-dispatch/226-01-SUMMARY.md
  - .planning/phases/226-browser-engine-throughput-underfill-root-split-continuous-dispatch/226-02-PLAN.md
  - .planning/phases/226-browser-engine-throughput-underfill-root-split-continuous-dispatch/226-02-SUMMARY.md
  - .planning/phases/226-browser-engine-throughput-underfill-root-split-continuous-dispatch/226-03-PLAN.md
  - .planning/phases/226-browser-engine-throughput-underfill-root-split-continuous-dispatch/226-03-SUMMARY.md
  - .planning/phases/226-browser-engine-throughput-underfill-root-split-continuous-dispatch/226-04-PLAN.md
  - .planning/phases/226-browser-engine-throughput-underfill-root-split-continuous-dispatch/226-04-SUMMARY.md
  - .planning/phases/226-browser-engine-throughput-underfill-root-split-continuous-dispatch/226-05-PLAN.md
  - .planning/phases/226-browser-engine-throughput-underfill-root-split-continuous-dispatch/226-05-SUMMARY.md
  - .planning/phases/226-browser-engine-throughput-underfill-root-split-continuous-dispatch/226-06-PLAN.md
  - .planning/phases/226-browser-engine-throughput-underfill-root-split-continuous-dispatch/226-06-SUMMARY.md
  - .planning/phases/226-browser-engine-throughput-underfill-root-split-continuous-dispatch/226-07-PLAN.md
  - .planning/phases/226-browser-engine-throughput-underfill-root-split-continuous-dispatch/226-07-SUMMARY.md
  - .planning/phases/226-browser-engine-throughput-underfill-root-split-continuous-dispatch/226-08-PLAN.md
  - .planning/phases/226-browser-engine-throughput-underfill-root-split-continuous-dispatch/226-08-SUMMARY.md
  - .planning/phases/226-browser-engine-throughput-underfill-root-split-continuous-dispatch/226-09-PLAN.md
  - .planning/phases/226-browser-engine-throughput-underfill-root-split-continuous-dispatch/226-09-SUMMARY.md
  - .planning/phases/226-browser-engine-throughput-underfill-root-split-continuous-dispatch/226-10-PLAN.md
  - .planning/phases/226-browser-engine-throughput-underfill-root-split-continuous-dispatch/226-10-SUMMARY.md
  - .planning/phases/226-browser-engine-throughput-underfill-root-split-continuous-dispatch/226-11-PLAN.md
  - .planning/phases/226-browser-engine-throughput-underfill-root-split-continuous-dispatch/226-11-SUMMARY.md
  - .planning/phases/226-browser-engine-throughput-underfill-root-split-continuous-dispatch/226-12-PLAN.md
  - .planning/phases/226-browser-engine-throughput-underfill-root-split-continuous-dispatch/226-12-SUMMARY.md
  - .planning/phases/226-browser-engine-throughput-underfill-root-split-continuous-dispatch/226-13-PLAN.md
  - .planning/phases/226-browser-engine-throughput-underfill-root-split-continuous-dispatch/226-13-SUMMARY.md
  - .planning/phases/226-browser-engine-throughput-underfill-root-split-continuous-dispatch/226-14-PLAN.md
  - .planning/phases/226-browser-engine-throughput-underfill-root-split-continuous-dispatch/226-14-SUMMARY.md
  - CHANGELOG.md
  - bin/preset-supervisor.sh
  - docs/flawchess-engine-explained-2026-07-06.md
  - fixtures/engine/move-quality-226.tsv
  - frontend/src/hooks/useBotGameEngineDispatch.ts
  - frontend/src/hooks/useFlawChessEngine.test.tsx
  - frontend/src/hooks/useFlawChessEngine.ts
  - frontend/src/lib/engine/__tests__/mctsSearch.roundFill.test.ts
  - frontend/src/lib/engine/__tests__/mctsSearch.test.ts
  - frontend/src/lib/engine/__tests__/rootSplit.test.ts
  - frontend/src/lib/engine/__tests__/workerPool.test.ts
  - frontend/src/lib/engine/botBudget.ts
  - frontend/src/lib/engine/mctsSearch.ts
  - frontend/src/lib/engine/rootSplit.ts
  - frontend/src/lib/engine/types.ts
  - frontend/src/lib/engine/workerPool.ts
  - frontend/src/lib/engine/workerPoolDispatch.ts
  - frontend/src/lib/engine/workerPoolState.ts
  - scripts/build-move-quality-fixture.mjs
  - scripts/calibration-harness.mjs
  - scripts/engine-dispatch-stop-rule.mjs
  - scripts/engine-grading-depth-ab.mjs
  - scripts/engine-move-quality.mjs
  - scripts/engine-root-split-content.mjs
  - scripts/engine-search-trace.mjs
  - scripts/engine_throughput_226_calibration.py
  - scripts/engine_throughput_226_verdict.py
  - scripts/lib/calibration-determinism.check.mjs
  - scripts/lib/calibration-providers.mjs
  - scripts/lib/node-engine-providers.mjs
  - scripts/lib/stockfish-pool.check.mjs
  - scripts/lib/stockfish-pool.mjs
  - tests/scripts/test_engine_throughput_226_calibration.py
  - tests/scripts/test_engine_throughput_226_verdict.py
covered_digest: "v2:sha256:204ad77730eea478c4a2e72b114bc76126744166ed8aa9ff70b35059d89b3a83"
behavior_unverified: 0
overrides_applied: 4
overrides:
  - must_have: "Items ship only if the pre-registered gate passes them (mechanical verdict: underfill hold, guard hold (stacked), root split hold (stacked + Clear-Hash content))"
    reason: "Owner ship decision overriding the mechanical hold verdict. Underfill's only failing config (t400-p2, 1.125) is machine-speed drift (CPU-normalized 0.991; interleaved re-test A2/A0 raw 0.879, normalized 0.998). Guard was held only by stacking. Root split fails Clear-Hash content (0.0209 vs 0.0168) but the owner accepts slightly different play for a substantial gain; interleaved bot-move re-test confirmed A21S/A21 = 0.809/0.841/0.819. verdict.json intentionally unchanged (mechanical record). Record: reports/engine-throughput-226/override-2026-10-02-owner-ship-decision.md"
    accepted_by: "owner (Adrian Imfeld), in chat"
    accepted_at: "2026-10-02"
  - must_have: "D-13 trace anomaly reading (cBFTV flip classified as tree-shape side effect)"
    reason: "Ratified; code review WR-07 (trace edges keyed by child FEN) independently supports it. override-2026-09-29-d13-trace-anomaly.md"
    accepted_by: "owner (Adrian Imfeld), in chat"
    accepted_at: "2026-10-02"
  - must_have: "Content tool single-candidate reading (engine-root-split-content.mjs)"
    reason: "Ratified. override-2026-09-29-content-tool-single-candidate.md"
    accepted_by: "owner (Adrian Imfeld), in chat"
    accepted_at: "2026-10-02"
  - must_have: "Pitfall-1 blend-0 cell (a21s human1100 calls=0 is structural)"
    reason: "Ratified. override-2026-10-01-pitfall1-blend0-cell.md"
    accepted_by: "owner (Adrian Imfeld), in chat"
    accepted_at: "2026-10-02"
---

# Phase 226: Browser Engine Throughput Verification Report

**Phase Goal:** Cut bot-move latency and analysis wall time by fixing Stockfish scheduling (idle-box re-measure; re-land round underfill fix + root comparability guard; split the round-1 root grade across idle SF workers with L-2/L-3/L-4; no-Clear-Hash calibration arm), behind a pre-registered gate.
**Verified:** 2026-10-02
**Status:** passed (with warnings, none blocking)
**Re-verification:** Yes. Supersedes the 2026-10-01 `human_needed` report; its three human items are resolved by the owner (override-2026-10-02-owner-ship-decision.md, 226-UAT.md items 1-3), item 4 (real phone) is report-only per D-04.

## Judgement frame

The pre-registered mechanical verdict (verdict.json) is `hold` for all three items and remains the record. The project convention is that an owner override recorded in the VERIFICATION frontmatter is the legitimate way to ship against it, and the owner made that decision on 2026-10-02 after reading the report, the CPU-normalized analysis and the interleaved re-test. This report therefore verifies (a) the measurement contract was executed faithfully, (b) the shipped code is what the override says it is and satisfies L-2/L-3/L-4, and (c) the claimed latency gain is supported by data. It does not re-litigate the override.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Accept rule committed before any gate data and never edited | VERIFIED | `git log -- accept-rule.md` is the single commit `3fe340ce9`. verdict.json is the single commit `770b4b89a`; both untouched by the override commits. |
| 2 | Step-0 idle-box re-measure, A0a/A0b null recorded | VERIFIED | `reports/data/engine-throughput-226/step0/{profile,calibration,warm-arm,content,mq,stop,throughput,trace}` present; D-09 section in report.md. |
| 3 | No-Clear-Hash calibration arm exists, reusable | VERIFIED | `scripts/lib/calibration-determinism.check.mjs` warm arm; gate warm-arm data present. |
| 4 | Verdict is mechanical and reproducible | VERIFIED | Re-ran `engine_throughput_226_verdict.py gates` in this pass: exit 0, output dict-equal to committed `verdict.json` (all hold, no-refit, missing []). |
| 5 | Shipped frontend code equals arm A21S | VERIFIED | `git diff f6c1f7a54 HEAD -- frontend/src` is empty (also 9d0327b91 and 0db58d765 present on branch). |
| 6 | Root split satisfies L-2 (any missing sub-grade aborts the whole grade, never a partial merge) | VERIFIED (code + probe); test-coverage WARNING | `workerPoolDispatch.ts` `gradeRoot`: a shard counts as complete only if `req.completed === true` (set solely in the `bestmove` branch); any non-completed settle sets `groupFailed`, aborts the group controller (siblings get `stop`); `finish()` resolves an empty Map on `groupFailed \|\| signal.aborted`. A throwaway probe test (3 shards complete with real grades, 4th watchdog-fires) resolved size 0 and left a cache miss: passes on the shipped code, then removed. Mutation check: deleting the `groupFailed = true` line passes all 121 workerPool tests, so the shard-failure-with-completed-siblings path has no regression test (the existing L-2 unit test goes through the outer-abort path, and the watchdog test has no completed siblings). See Warning 1. |
| 7 | L-3: merge before the single cache write; shards neither read nor write cache | VERIFIED | Shard requests submitted with `{readCache:false, writeCache:false}`; `handleLine` bestmove branch gates its write on `writeCache !== false`; the group does one merged `gradeCache.write` on success only. Mutation (`if (true)` in the bestmove gate) fails the L-2/L-3 cache-miss test, so a shard cache write is guarded. |
| 8 | L-4: fan-out sized from live idle slots; k<=1 delegates to `grade` | VERIFIED | `k = min(countIdleReadySlots, candidates, ROOT_SPLIT_MAX_SHARDS)`; `countIdleReadySlots` returns 0 on a non-empty pending queue; `k <= 1` returns `grade(...)`. Mutation (hard-coded k=99) fails 4 tests (busy-slot k=3, pending-queue, mobile pool 2, k<=1). |
| 9 | Both app call sites pass `gradeRoot`; root-only routing | VERIFIED | `useFlawChessEngine.ts` providers object and `useBotGameEngineDispatch.ts` `buildBotMoveDeps` both pass `pool.gradeRoot`; `mctsSearch.ts:584` routes `leaf.isRoot ? providers.gradeRoot : undefined`, falling back to `grade`. `types.ts` declares `gradeRoot?` optional. |

**Score:** 9/9 truths verified; 0 behavior-unverified.

### Latency goal evidence

| Claim | Evidence | Status |
|-------|----------|--------|
| Bot move about 18% faster (CHANGELOG) | Re-computed from the committed `retest-2026-10-02/stop-*.log`: A0 71.6/68.5/68.8 s (mean 69.6), A21 70.5/67.6/67.5, A21S 57.0/56.8/55.3; A21S/A21 0.809/0.841/0.819; A21S/A0 about 0.81. Matches override doc §4. About 8% is pure speed, about 10% is earlier stop (mean nodes at stop 24.25 vs 28.88 vs 29.06), which the engine doc describes as playing "very slightly differently". | VERIFIED |
| Analysis searches "a bit faster" (CHANGELOG) | CPU-normalized wall per grade is about 1% at t400-p2 and roughly 0 at 400 nodes for the root split; underfill is about 5-8% normalized on the desktop pool; the t400-p2 interleaved pair (A2/A0 raw 0.879, normalized 0.998) shows no code effect there. Hedged wording is defensible but the 400-node gain is small and not demonstrated beyond noise. | WARNING 3 |

### Required Artifacts

| Artifact | Status | Details |
|----------|--------|---------|
| `frontend/src/lib/engine/rootSplit.ts` | VERIFIED | Pure round-robin partition/merge; merge never fabricates a missing candidate; imported by `workerPoolDispatch.ts`. |
| `workerPool.ts` / `workerPoolDispatch.ts` / `workerPoolState.ts` | VERIFIED | `gradeRoot` on the `WorkerPool` interface and facade, dispatch implementation, `readCache/writeCache/completed` request flags. |
| `mctsSearch.ts` underfill + guard + root routing | VERIFIED | Substantive diff (218 lines), covered by `mctsSearch.roundFill.test.ts`, `mctsSearch.test.ts`. |
| Gate tooling (verdict twin, calibration reducer, warm arm, pool, MQ fixture) | VERIFIED | Unchanged since prior verification apart from `engine-root-split-content.mjs` (14 lines); verdict reproduces. |
| `reports/data/engine-throughput-226/retest-2026-10-02/` | VERIFIED | stop A0/A21/A21S x3 and t400-p2 A0/A2 x1 present with `driver.log` load-average gate; numbers in override doc match the logs. |
| `reports/engine-throughput-226/override-2026-10-02-owner-ship-decision.md` | VERIFIED | Records ratification, ship decision, re-test results §4/§6, final root-split decision §5. |
| SEED-176/177/178 | VERIFIED | In `.planning/seeds/closed/`; SEED-171 carries the override note. |
| CHANGELOG `[Unreleased]` and engine doc | VERIFIED | Bullet under Changed; engine doc has the "Several expansions at once" and "Splitting the first look across idle workers" paragraphs, consistent with L-2/L-3 behavior. |

### Key Link Verification

| From | To | Via | Status |
|------|----|-----|--------|
| `useFlawChessEngine.ts` | `pool.gradeRoot` | providers object | WIRED |
| `useBotGameEngineDispatch.ts` | `pool.gradeRoot` | `buildBotMoveDeps` | WIRED |
| `mctsSearch.ts` `dispatchExpansion` | `providers.gradeRoot` (root only) | `leaf.isRoot ? ... : undefined) ?? providers.grade` | WIRED |
| `workerPoolDispatch.gradeRoot` | `rootSplit.partitionCandidates/mergeShardGrades` | import | WIRED |
| `workerPoolDispatch.gradeRoot` | `grade` (k<=1) | direct call | WIRED |

### Data-Flow Trace (Level 4)

Not applicable (no rendered dynamic data added). The grades flow from real Stockfish worker `info`/`bestmove` lines through `handleLine` accumulators into the merged Map and the single cache write.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Engine unit tests | `cd frontend && npx vitest run src/lib/engine` | 33 files, 701 tests passed | PASS |
| Type check | `cd frontend && npx tsc -b` | rc 0, no output | PASS |
| Verdict reproduces | `python3 scripts/engine_throughput_226_verdict.py gates --out-json <tmp>` | exit 0, equals committed verdict.json | PASS |
| D-11 refit rule over the shipped set | `load_parity_verdict` + `powered_verdict` (thresholds 85.0 / 53.5428, z 1.96) on `gate/calibration/verdict-{a2-vs-a0a,a21-vs-a2,a21s-vs-a21}.json`, then `refit_decision` with underfill, guard, root_split shipped | all three valid, `real_shift` False, no z-guard cells; decision `no-refit` | PASS |
| L-2 shard-failure probe (temporary test, removed) | 3 shards complete, 4th watchdog fires | size 0, cache miss afterward | PASS |
| Mutation: drop `groupFailed = true` | vitest workerPool | 121 pass (not caught) at verification; after the follow-up test, 1 fails (caught) | RESOLVED (Warning 1) |
| Mutation: shard writes cache | vitest workerPool | 1 fails (caught) | PASS |
| Mutation: k ignores idle slots | vitest workerPool | 4 fail (caught) | PASS |
| Retest numbers | parsed `stop-*-r{1,2,3}.log` | wall, nodes at stop and early-stop counts match override doc §4 | PASS |
| Full pre-merge gate (pytest 4853, frontend 4471, ruff/ty/knip/lint/build) | not re-run in full here (reported by the owner session) | n/a | SKIP |

Working tree restored after each mutation (`git status` shows only the pre-existing untracked `frontend/public/sound/alternatives/`).

### Probe Execution

No probe scripts declared or conventional for this phase (`scripts/*/tests/probe-*.sh` absent). SKIPPED.

### Requirements Coverage

No requirement IDs for this phase; none orphaned.

### Anti-Patterns Found

No `TBD|FIXME|XXX` in the shipped engine files or `engine-root-split-content.mjs`. No stubs: `gradeRoot` is a full implementation. Code review (226-REVIEW.md, 0 critical / 7 warning / 4 info, all tooling-side) remains deferred per 226-REVIEW-DISPOSITION.md.

### Human Verification Required

None blocking. Real-phone dev-build bot-latency run is owner-deferred and report-only (D-04, never blocks); 226-UAT.md records it as skipped.

### Findings (WARNING level, none blocking)

1. **L-2 regression protection is half-built.** The code is correct (probe confirmed), but deleting `groupFailed = true` in `workerPoolDispatch.ts` leaves every workerPool test green. The "some shards completed, one failed" path is only exercised via outer-signal abort (which `finish()` catches through `signal.aborted`) and via an all-fail watchdog (merge of empties is empty anyway). Recommended: add a test where 3 shards complete with real grades and the 4th watchdog-fires, asserting an empty result and a cache miss on a following `grade()` (the probe used for this verification does exactly that). Outside this phase's closed scope unless the owner wants it folded in. **RESOLVED (orchestrator follow-up, 2026-10-02):** the test was added to `workerPool.test.ts` ("L-2: 3 shards completing before the 4th watchdog-fires (no outer abort)..."). With `groupFailed = true` commented out it fails (1 failed / 121 passed), and restored it passes. Engine suite 702/702.
2. **report.md is partly stale after the override.** The header still says "Three exist, all pending owner ratification", the Headline table and "Owner decisions pending" section still describe the mechanical state, and the "Owner override and re-test" section says the t400-p2 pair was ABBA while the override doc (§6) and `driver.log` show it was cut to one AB pair. The override sections and override doc are correct; the earlier prose is the record of the pre-override verdict. **RESOLVED:** the header now says the overrides were ratified, the decisions section is retitled as resolved, and the t400-p2 line states the single AB pair with its numbers. The CHANGELOG bullet now claims only the demonstrated bot-move gain (Warning 3).
3. **"Analysis searches a bit faster" is weakly supported.** The only demonstrated, interleaved wall gain is the 400-node-irrelevant bot path (about 19%); the 400-node effect is about 0-8% normalized and one raw gate config pointed the wrong way due to drift. The CHANGELOG wording is hedged, but a stricter reading would drop the claim.
4. **Part of the bot-move gain is behavioral, not speed.** About 10 of the 18 points come from the stop rule firing at different node counts (4 earlier, 1 later of 5 positions). This is disclosed in the override doc and the engine doc and accepted by the owner; MQ shows one regression-to-pass and none the other way, and powered calibration shows no real shift. Real-phone latency is untested (D-04).
5. **A21S vs A21 shape-guard cell (1500/0.5)**: Maia +75, SF -102, opposite signs; Phase 199 CI-overlap guard fires but the pre-registered z-guard does not and all pooled shifts are in threshold. Informational; recorded in report.md criterion 15.

### Gaps Summary

No gaps. The measurement contract was executed faithfully and the mechanical record is intact; the owner override is recorded in frontmatter; the shipped code is bit-for-bit arm A21S and implements L-2/L-3/L-4 with both app call sites wired; the bot-move gain reproduces from committed re-test logs; the D-11 refit rule over the shipped set yields no-refit. Remaining items are advisory (test hardening, report prose, CHANGELOG wording).

---

_Verified: 2026-10-02_
_Verifier: Claude (gsd-verifier)_
