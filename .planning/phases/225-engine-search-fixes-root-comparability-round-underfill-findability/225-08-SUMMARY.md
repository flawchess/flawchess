---
phase: 225-engine-search-fixes-root-comparability-round-underfill-findability
plan: 08
subsystem: engine-measurement
tags: [gate-verdict, revert, changelog, docs, seeds, phase-close]

requires:
  - phase: 225-07
    provides: "committed gate data under reports/data/engine-search-fixes-225/ (throughput, move-quality, stop-rule, calibration TSVs and verdict JSONs)"
provides:
  - "reports/engine-search-fixes-225/verdict.json and report.md: the mechanical verdict (item2 hold, item1 hold, item3 independent) and the phase report citing it in the accept rule's evaluation order"
  - "Phase branch holding only item 3 (findability fallback) — items 1 and 2 reverted per D-14"
  - "docs/flawchess-engine-explained-2026-07-06.md: parity effect paragraph, guard-held note, deliberate-residual documentation (near-tie branch, deadline cut with measured 18% exposure), rewritten findability paragraph for D-10a"
  - "CHANGELOG.md [Unreleased]/Changed: one bullet for item 3; none for the held items"
  - ".planning/seeds/SEED-173 (item 4 + flatness/deadline guarding), SEED-174 (held items follow-up); SEED-170 closed"
affects: []

actuals:
  tokens: 21447
  tasks: 3
  commits: 9
  plan_head_before: acb09a2f94afae11285a81cce0ade3ac1d2b4510
  plan_head_after: 8ebbd959f3978e4276ea3d8fdee01d0f70b05195

tech-stack:
  added: []
  patterns:
    - "D-14 application via git revert --no-commit per commit, newest-first, with subject reworded to revert(225-08): hold item N ...; auto-merged cleanly against Plan 225-06's later edits to the same test file (mctsSearch.test.ts) with no manual conflict resolution needed"

key-files:
  created:
    - reports/engine-search-fixes-225/verdict.json
    - reports/engine-search-fixes-225/report.md
    - .planning/seeds/SEED-173-engine-non-root-candidate-cap.md
    - .planning/seeds/SEED-174-engine-search-fixes-held-items-follow-up.md
  modified:
    - docs/flawchess-engine-explained-2026-07-06.md
    - CHANGELOG.md
    - frontend/src/lib/engine/mctsSearch.ts
    - frontend/src/lib/engine/types.ts
    - frontend/src/lib/engine/botBudget.ts
    - frontend/src/lib/engine/__tests__/mctsSearch.test.ts
    - frontend/src/hooks/useFlawChessEngine.test.tsx
    - .planning/seeds/closed/SEED-170-engine-root-comparability-and-round-underfill.md

key-decisions:
  - "Reverted item 1's two (225-05) commits before item 2's three (225-04) commits (both newest-first within their own item), matching the plan's explicit order; both reverts auto-merged against Plan 225-06's overlapping edits to mctsSearch.test.ts with git's own three-way merge — no manual hunk-picking was needed, and the resulting clear-winner test (nodesEvaluated stops at 1) matches pre-Phase-225 semantics exactly"
  - "SEED-173 and SEED-174 are separate seeds (not folded into one) because their trigger conditions differ: SEED-173 (item 4 + flatness/deadline guarding) triggers on a future throughput bottleneck or high measured deadline exposure; SEED-174 (held items) triggers on a willingness to re-measure item 1/2 from scratch, including investigating the calibration baseline drift"
  - "Engine doc's new parity-effect paragraph is placed in §6 immediately before the findability paragraph (both are 'judgment calls inside the search'), rather than in §3a/§4 where the underlying expectimax math lives, since the parity effect's practical consequence (the bot's early-stop comparison) is a judgment call about search behavior, not a restatement of the value math itself"

requirements-completed: []

coverage:
  - id: D1
    description: "verdict.json and report.md render the Phase 225 gate mechanically (item2 hold, item1 hold, item3 independent), citing every criterion in the accept rule's evaluation order without re-judging any of them"
    verification:
      - kind: other
        ref: "uv run python scripts/engine_search_fixes_verdict.py gates --data-dir reports/data/engine-search-fixes-225 --out-json reports/engine-search-fixes-225/verdict.json (exit 0, status complete)"
        status: pass
      - kind: other
        ref: "git log --format=%H -- reports/engine-search-fixes-225/accept-rule.md returns exactly one SHA (1b5313b96, the add-commit, never modified)"
        status: pass
    human_judgment: false
  - id: D2
    description: "D-14 applied: item 1 and item 2's code and tests are reverted from the phase branch (newest-first); item 3's code and tests are untouched; no refit or recalibration occurred"
    verification:
      - kind: other
        ref: "git diff --name-only <A0 SHA> HEAD -- frontend/src returns exactly item 3's six declared files (findability.ts, treeCommon.ts, and their four test files) — no item 1/2 file present"
        status: pass
      - kind: other
        ref: "grep -c rootGuardBoostAllowance across types.ts, botBudget.ts, mctsSearch.ts, mctsSearch.test.ts, useFlawChessEngine.test.tsx returns 0 in every file"
        status: pass
    human_judgment: false
  - id: D3
    description: "The reverted mctsSearch.test.ts clear-winner test matches pre-Phase-225 semantics (stops at node 1), not item 1's guarded behavior"
    verification:
      - kind: unit
        ref: "frontend/src/lib/engine/__tests__/mctsSearch.test.ts#mctsSearch — Phase 168.5 D-05/D-06 bot-play stop rule > clear-winner: a dominant root move stops the search before maxNodes, with stopReason early-stop (asserts nodesEvaluated === 1)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Engine doc explains the parity effect, names both deliberate residuals (near-tie branch, deadline cut) with the measured D-04 exposure, and states the guard was evaluated and held; findability paragraph is rewritten for D-10a with the Nb5 story updated for D-10e"
    verification:
      - kind: other
        ref: "grep -ci parity docs/flawchess-engine-explained-2026-07-06.md (2) and grep -ci 'deadline|time-pressure|time pressure' (2)"
        status: pass
    human_judgment: true
    rationale: "Whether the prose reads clearly and honestly (not just that the required keywords are present) is a judgment call a human reviewer should sanity-check, even though the mechanical grep gates pass."
  - id: D5
    description: "CHANGELOG.md [Unreleased] carries exactly one bullet for item 3 and none for the held items"
    verification:
      - kind: other
        ref: "grep -n 'Analysis suggestions in a winning position' CHANGELOG.md (present); grep -n 'faster bot moves|near-equal candidate|forced or near-forced replies' CHANGELOG.md (absent)"
        status: pass
    human_judgment: false
  - id: D6
    description: "SEED-173 (item 4 + flatness/deadline) and SEED-174 (held items) are planted; SEED-170 is closed with a status: closed line and moved to .planning/seeds/closed/"
    verification:
      - kind: other
        ref: "test -f SEED-173 && test -f SEED-174 && test ! -e SEED-170 (old path) && grep -q '^status: closed' SEED-170 (new path)"
        status: pass
    human_judgment: false
  - id: D7
    description: "The full CLAUDE.md pre-merge gate is green on the final phase branch: ruff format/check, ty (app/tests/scripts and analysis/), function-size gate, pytest -n auto -x, and the frontend lint/build/test/knip chain"
    verification:
      - kind: other
        ref: "uv run ruff format/check --fix (clean), uv run ty check app/ tests/ scripts/ (clean), uv run --project analysis --with ty ty check analysis/ (clean), check_function_size.py (0 breaches), uv run pytest -n auto -x (4781 passed, 20 skipped); ( cd frontend && npm run lint && npm run build && npm test -- --run && npm run knip ) (0 lint errors, build succeeds, 4421/4421 tests passed across 275 files, knip clean save for the pre-existing .css config hint)"
        status: pass
    human_judgment: false

duration: 65min
completed: 2026-09-28
status: complete
---

# Phase 225 Plan 08: Gate Verdict, D-14 Close-out and Phase Report Summary

**The pre-registered Phase 225 gate closed exactly as it scored: item 3 (findability fallback) ships; item 1 (root comparability guard) and item 2 (round underfill fix) are held — MQ-2's confirmed `cBFTV` regression flip and a calibration decision-branch failure that traces back to the unchanged baseline itself already failing the same parity check against July-21 — and both are reverted from the phase branch with no refit, per D-14.**

## Performance

- **Duration:** ~65 min
- **Started:** 2026-09-28T04:00:00Z (approx)
- **Completed:** 2026-09-28T05:05:00Z (approx)
- **Tasks:** 3
- **Files modified:** 13 (across all 8 commits: 4 created, 9 modified/reverted, 1 deleted, 1 renamed)

## Accomplishments

- Ran `scripts/engine_search_fixes_verdict.py gates` against the committed Plan 225-07 gate data: `status complete`, T-50/T-400/MQ-1/S1/S2 all pass, MQ-2 fails (a confirmed pass-to-regression flip on fixture position `cBFTV`), calibration's primary verdict fails and routes to the pre-registered `decision` branch, which found the phase's own unchanged baseline (A0) already fails the same July-21 parity check — `baseline_drift: true`. Final item decisions: item2 hold, item1 hold (held automatically once item 2 is held, since A21 was never measured without item 2), item3 independent.
- Wrote `reports/engine-search-fixes-225/report.md`: the four arm SHAs and content-assertion results, the D-02 allowance and method, one subsection per criterion in the accept rule's own evaluation order (validity, T-50/T-400, MQ-2, S1, S2, MQ-1, calibration with the full decision-branch attribution table), and report-only sections for the D-04 deadline exposure (18%, identical across A2/A21), nodes-at-stop median/p90, the item-3 ordering table (zero of 12 maia-blindness positions change `analysis_move` between A2 and FINAL stop-off — this fixture wasn't designed to showcase item 3's reordering), and the calibration shift placed next to Phase 199's own pooled shifts as context only.
- Applied D-14: reverted all five `(225-04)`/`(225-05)` code commits that touched `frontend/src`, newest-first (item 1's two commits, then item 2's three), with `revert(225-08): hold item N ...` subjects. Both item boundaries auto-merged cleanly against Plan 225-06's later, non-overlapping edits to `mctsSearch.test.ts` — no manual conflict resolution was required. The resulting `mctsSearch.ts`/`types.ts`/`botBudget.ts` are byte-identical to their pre-225-04 state (0 occurrences of `rootGuardBoostAllowance` anywhere), and the clear-winner stop-rule test reverted to its pre-Phase-225 assertion (`nodesEvaluated === 1`). `git diff --name-only <A0 SHA> HEAD -- frontend/src` now returns exactly item 3's six declared files.
- Updated `docs/flawchess-engine-explained-2026-07-06.md` §6: added a new "parity effect" paragraph (why an unexpanded root child and an expanded one aren't directly comparable; what the guard would have fixed; that it was measured and held, linking the report; the two spots deliberately left unguarded — the near-tie branch and the wall-clock deadline cut, with its measured ~18% exposure fraction). Rewrote the findability paragraph for D-10a: a hard-to-find move is now pulled toward what a typical move scores in that position rather than toward zero, so a hard-to-find move far better than every findable alternative can still top the list; updated the Nb5 story to note the reordering (D-10e).
- Added one CHANGELOG.md `[Unreleased]`/`### Changed` bullet for item 3 (analysis suggestions in a winning position no longer bury a far-better hard-to-find move). No bullet for item 1 or item 2 — both held.
- Planted `.planning/seeds/SEED-173-engine-non-root-candidate-cap.md` (item 4's candidate cap plus the deferred flatness/deadline-cut guarding idea, with the measured 18% D-04 exposure) and `.planning/seeds/SEED-174-engine-search-fixes-held-items-follow-up.md` (the held items' failing criteria, arm SHAs, calibration decision-branch numbers, and the D-14 reminder that a refit is not the remedy). Closed SEED-170 into `.planning/seeds/closed/` with a `status: closed` line naming what shipped, what was held, and where each follow-up lives.
- Ran the full CLAUDE.md pre-merge gate: `ruff format`/`check --fix` clean, `ty check` clean on both `app/`+`tests/`+`scripts/` and `analysis/`, the nesting-depth gate clean (1068 functions scanned), `pytest -n auto -x` green (4781 passed, 20 skipped), and the frontend chain (`lint`, `build`, `test -- --run`, `knip`) all green — 4421/4421 tests across 275 files (down from 225-06's 4426/276, exactly the item 1/2 test files removed by the reverts), no lint errors, successful `tsc -b`+vite build, knip clean save for the same pre-existing `.css` config hint every prior Phase 225 plan recorded.

## Task Commits

1. **Task 1: gates output + phase report** — `098b42ff9` (docs)
2. **Task 2 (D-14 revert, item 1, part 1 of 2)** — `e20ca2e4c` (revert)
3. **Task 2 (D-14 revert, item 1, part 2 of 2)** — `3015aa03f` (revert)
4. **Task 2 (D-14 revert, item 2, part 1 of 3)** — `ed99c22d5` (revert)
5. **Task 2 (D-14 revert, item 2, part 2 of 3)** — `e01e56e41` (revert)
6. **Task 2 (D-14 revert, item 2, part 3 of 3)** — `11118b230` (revert)
7. **Task 2: engine doc + changelog** — `8b304f6b0` (docs)
8. **Task 3: seeds (SEED-173/174, close SEED-170)** — `c628c0b34` (docs)

**Plan metadata:** `8ebbd959f` (docs: complete plan — SUMMARY.md + STATE.md)

_Note: Task 3's pre-merge gate run itself produced no file changes (ruff/ty/pytest/frontend all clean on the first pass), so no additional `style`/`chore` commit was needed._

## Files Created/Modified

- `reports/engine-search-fixes-225/verdict.json` — mechanical gate output (new).
- `reports/engine-search-fixes-225/report.md` — the phase report (new).
- `docs/flawchess-engine-explained-2026-07-06.md` — new parity-effect paragraph, rewritten findability paragraph.
- `CHANGELOG.md` — one item-3 bullet under `[Unreleased]`/`### Changed`.
- `frontend/src/lib/engine/mctsSearch.ts`, `types.ts`, `botBudget.ts`, `__tests__/mctsSearch.test.ts`, `frontend/src/hooks/useFlawChessEngine.test.tsx` — reverted to pre-item-1/2 state.
- `frontend/src/lib/engine/__tests__/mctsSearch.roundFill.test.ts` — deleted (item 2's test file, created and fully reverted within this plan).
- `.planning/seeds/SEED-173-engine-non-root-candidate-cap.md`, `.planning/seeds/SEED-174-engine-search-fixes-held-items-follow-up.md` — new.
- `.planning/seeds/closed/SEED-170-engine-root-comparability-and-round-underfill.md` — moved from `.planning/seeds/`, status set to closed.

## Decisions Made

See `key-decisions` in the frontmatter: revert ordering and clean auto-merge against Plan 225-06's edits; SEED-173/174 kept as two seeds with distinct trigger conditions; parity-effect paragraph placed in §6 alongside the findability paragraph rather than in the value-math sections.

## Deviations from Plan

None — plan executed exactly as written. One thing worth naming explicitly rather than treating as a deviation: the plan anticipated a possible manual conflict in `mctsSearch.test.ts` between the item-1 reverts and Plan 225-06's edits ("expect a conflict there ... resolve it by hand"). In practice `git revert` auto-merged both item-1 commits cleanly with no conflict markers, because Plan 225-06 never touched the specific `describe` block (`Phase 168.5 D-05/D-06 bot-play stop rule`) that item 1's commits modified — the two plans' edits to the same file were in disjoint regions. The resulting file was verified to match pre-Phase-225 semantics exactly (the clear-winner test's `nodesEvaluated` assertion is `1`, not item 1's guarded `3`).

## Issues Encountered

None. `docker compose -f docker-compose.dev.yml -p flawchess-dev up -d` reported `Recreate`/`Recreated` for the dev DB container on first invocation this session (likely a config drift from a prior session, not caused by this plan); the container came up healthy within seconds and every subsequent `pytest` run against it passed normally.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Phase 225 is closed. The phase branch (`gsd/phase-225-engine-search-fixes-root-comparability-round-underfill-findability`) holds exactly item 3 (findability fallback) plus all measurement tooling and reports from Plans 225-01 through 225-08 — ready for the local squash-merge to `main` per the project's GitLab-Flow workflow (`docs/git-workflow.md`).
- Follow-up work is captured, not scheduled: SEED-173 (item 4 + flatness/deadline guarding) and SEED-174 (re-measuring items 1/2, including the calibration baseline-drift finding) are both `dormant`, awaiting their own trigger conditions.
- No blockers.

---
*Phase: 225-engine-search-fixes-root-comparability-round-underfill-findability*
*Completed: 2026-09-28*

## Self-Check: PASSED

- FOUND: reports/engine-search-fixes-225/verdict.json
- FOUND: reports/engine-search-fixes-225/report.md
- FOUND: docs/flawchess-engine-explained-2026-07-06.md (modified)
- FOUND: CHANGELOG.md (modified)
- FOUND: .planning/seeds/SEED-173-engine-non-root-candidate-cap.md
- FOUND: .planning/seeds/SEED-174-engine-search-fixes-held-items-follow-up.md
- FOUND: .planning/seeds/closed/SEED-170-engine-root-comparability-and-round-underfill.md
- MISSING (expected, intentionally reverted): frontend/src/lib/engine/__tests__/mctsSearch.roundFill.test.ts
- FOUND commit: 098b42ff9 (docs, Task 1)
- FOUND commit: e20ca2e4c (revert, item 1)
- FOUND commit: 3015aa03f (revert, item 1)
- FOUND commit: ed99c22d5 (revert, item 2)
- FOUND commit: e01e56e41 (revert, item 2)
- FOUND commit: 11118b230 (revert, item 2)
- FOUND commit: 8b304f6b0 (docs, Task 2)
- FOUND commit: c628c0b34 (docs, Task 3)
- FOUND commit: 8ebbd959f (docs, plan metadata: SUMMARY.md + STATE.md)
- CONFIRMED: `uv run pytest -n auto -x` — 4781 passed, 20 skipped
- CONFIRMED: frontend `lint`/`build`/`test -- --run`/`knip` — all green, 4421/4421 tests
- CONFIRMED: `git status --porcelain` clean
