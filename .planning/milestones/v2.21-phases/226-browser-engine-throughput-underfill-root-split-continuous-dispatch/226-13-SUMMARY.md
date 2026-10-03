---
phase: 226-browser-engine-throughput-underfill-root-split-continuous-dispatch
plan: 13
subsystem: engine
tags: [verdict, ship-hold, reverts, seeds]
status: partial

requires:
  - phase: 226-12
    provides: "Committed gate data; arms A2 756d2a4a1, A21 29f543f27, A21S f6c1f7a54"
provides:
  - "reports/engine-throughput-226/verdict.json (gates output, exit 0, status complete)"
  - "Every arm-tagged engine commit reverted; frontend/src/lib/engine and frontend/src/hooks identical to main"
  - "SEED-171 Phase 226 outcome section; follow-up seeds SEED-176 (underfill), SEED-177 (root guard), SEED-178 (root split)"
affects: [226-14, 227]

actuals:
  tasks: 3
  commits: 8
  plan_head_before: fcaf1202abf0537021bbb92e2e263eb55eaddaa2
  plan_head_after: 8522bdc95d4984f81f59268181eeb2f4a1485172

key-files:
  created:
    - reports/engine-throughput-226/verdict.json
    - .planning/seeds/SEED-176-reland-round-underfill-fix.md
    - .planning/seeds/SEED-177-reland-root-comparability-guard.md
    - .planning/seeds/SEED-178-root-grade-split.md
  modified:
    - .planning/seeds/SEED-171-browser-engine-throughput.md
    - frontend/src/lib/engine/ (six arm-commit reverts; net zero versus main)

key-decisions:
  - "Verdict applied exactly: nothing ships. Underfill held (t400-p2 wall ratio 1.1252 > 1.05), guard held (stacked on underfill; its own S1/S2/MQ pass), root split held (stacked, and Clear-Hash content 0.02092 > 0.01680). Refit: no-refit."
  - "report.md: the executor's Write was refused by the subagent report-file hook; the orchestrator wrote and committed it from the executor's handback content (numbers spot-checked against committed data), adding one report-only stop-rule observation."
---

# Phase 226 Plan 13: Verdict application

**All three items hold under the pre-registered verdict, the six arm commits are reverted so the
branch carries main's engine behavior, SEED-171 records the outcome, and three follow-up seeds
exist. `reports/engine-throughput-226/report.md` was NOT written: the Write tool refused it for
this subagent (message: subagents should return findings as text). It was not worked around.**

## What was done

### Task 1 (tracer): verdict.json (770b4b89a), report.md blocked

`VIRTUAL_ENV= uv run python scripts/engine_throughput_226_verdict.py gates --data-dir
reports/data/engine-throughput-226 --out-json reports/engine-throughput-226/verdict.json` exited 0:

```
STATUS complete
UNDERFILL_THROUGHPUT: passed=False
UNDERFILL: hold
GUARD: hold
ROOT_SPLIT: hold
REFIT: no-refit
```

`verdict.json` committed. report.md: two Write attempts were refused. All report content was
gathered and verified against committed data and is in the handback message for the orchestrator
to write and commit. The SEED-171 outcome section and the three seeds already cite
`reports/engine-throughput-226/report.md`.

### Task 2: apply hold, no docs or changelog (reverts 719fdfe60, de1a589b0, d87765a94, 51c6c5550, c6b314c4f, 746848d25)

Reverted newest first, one `git revert --no-edit` each, message amended to
`revert(226-13): hold {item} per verdict`:

| Revert | Reverts | Item |
|---|---|---|
| 719fdfe60 | f6c1f7a54 feat(226-11) wire gradeRoot (arm A21S) | root split |
| de1a589b0 | 849a9bea2 feat(226-11) WorkerPool.gradeRoot (arm A21S) | root split |
| d87765a94 | aa77ad1aa test(226-10) gradeRoot tests (arm A21S) | root split |
| 51c6c5550 | 2f5c4aad3 feat(226-10) routing and split helpers (arm A21S) | root split |
| c6b314c4f | 29f543f27 feat(226-09) root comparability guard (arm A21) | guard |
| 746848d25 | 756d2a4a1 fix(226-09) round underfill fix (arm A2) | underfill |

No conflicts. `3fe340ce9` (arm A0, the accept rule) was not reverted: it is a docs commit, not an
engine commit. No tooling, harness, report, override or fix(226-12) commit was reverted.

Checks after the reverts:
- `git diff $(git merge-base main HEAD) HEAD -- frontend/src/lib/engine frontend/src/hooks`: empty.
  `git diff ... -- frontend CHANGELOG.md docs`: empty. Nothing remains versus main.
- `npm ci` in `frontend/` (lockfile only, no new package), `npx vitest run src/lib/engine` (run from
  `frontend/`): 31 files, 670 tests passed. `npm run build`: succeeded.
- Engine doc `docs/flawchess-engine-explained-2026-07-06.md` has no mention of underfill, root
  guard or root split, so it is unchanged. `CHANGELOG.md` unchanged (no bullet: nothing ships).

### Task 3: seeds (8522bdc95)

SEED-171 gained a "Phase 226 outcome" section (per-item outcome with deciding numbers, idle-box
re-measurement versus the loaded-box table, D-17 outcome, refit decision, step 3 as Phase 227 with
the WebGPU prerequisite). New seeds, next free numbers (SEED-175 was the highest):
SEED-176 (underfill, A2 `756d2a4a1`), SEED-177 (root guard, A21 `29f543f27`), SEED-178 (root split,
A21S `f6c1f7a54`). ROADMAP.md and STATE.md untouched.

## Deviations from Plan

1. **[Plan text] verify one-liners use `v['ship']`.** `verdict.json`'s `items.<item>` objects carry
   `outcome` ("ship"/"hold") and `reasons`, not a `ship` boolean. The verify logic was evaluated
   with `v['outcome'] == 'ship'`: no item ships, no changelog bullet added, every held item has a
   follow-up seed referencing `engine-throughput-226`.
2. **[Blocked deliverable] report.md not written.** The Write tool returned "Subagents should
   return findings as text, not write report files" for both attempts. Other files (seeds,
   SUMMARY.md) were accepted. The block was not circumvented (no heredoc, no renamed file). The
   task-1 automated verify (`grep -q "D-06"` and `"D-09"` in report.md) could not pass from
   the executor. **Resolved by the orchestrator:** report.md written from the handback content,
   numbers spot-checked against committed data (stop-rule table, D-09 figures), plus a report-only
   note that the stop rule fires sooner with the root split (24.25 vs 28.88 nodes, 19% less wall).
3. **[Rule 1 style] Plan said to commit `docs(226-13): ...` for the doc and changelog.** No such
   commit exists because no doc or changelog change was warranted.

## Threat flags

None. No package installed (`npm ci` uses the lockfile); no new surface.

## Known Stubs

None.

## Pre-existing observations (not touched)

- Plan 226-12 SUMMARY notes the `45c1037e2` commit body disagrees with the committed verdict data
  on whether the `cBFTV` flip reproduced; the data (reproduced) is authoritative and is what
  verdict.json reports.

## Self-Check

- verdict.json present and tracked; six revert commits present in `git log`; three seed files and
  the SEED-171 section present; engine tests and build green; engine diff versus main empty.
- report.md: written and committed by the orchestrator after the executor returned (see Deviation 2). Task 1 verify (`grep D-06`, `grep D-09`) passes.

## Self-Check: PASSED
