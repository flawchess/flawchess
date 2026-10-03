---
phase: 226-browser-engine-throughput-underfill-root-split-continuous-dispatch
plan: 06
subsystem: infra
tags: [stockfish, node-tooling, root-split, grade-content, D-16]

# Dependency graph
requires:
  - phase: 226-01
    provides: "splitAcrossFreeEngines fan-out helper, dormant gradeRoot/rootSplitStats/freeCount on scripts/lib/stockfish-pool.mjs, ROOT_SPLIT_ABSENT_MESSAGE/ROOT_SPLIT_MODULE_SPECIFIER constants, nodeGrade's {clearHash} option in calibration-providers.mjs"
  - phase: 226-04
    provides: "engine-grading-depth-ab.mjs's exported BUILTIN_POSITIONS/resolvePositions, reused directly for this tool's --openings/--fens position resolution"
  - phase: 226-05
    provides: "engine_throughput_226_verdict.py's _CONTENT_REQUIRED_COLUMNS content TSV contract this tool's output matches column-for-column"
provides:
  - "scripts/engine-root-split-content.mjs: D-16's grade-content bound and projected-gain instrument, measuring real root candidate sets under Clear-Hash (exact bound) and warm-hash (with its own single-vs-single noise floor) for both a prototype (in-tool) split and the real pool.gradeRoot split source"
  - "engine-root-split-content-{hash}-{source}-{stamp}.tsv output matching engine_throughput_226_verdict.py's content contract column-for-column, ready for Plan 226-07/226-12's step-0 and arm-A21S runs"
affects: [226-07, 226-08, 226-12]

# Actuals (#2632)
actuals:
  tokens: 8756
  tasks: 2
  commits: 1
  plan_head_before: 1f98182ea07ef28dc4aaa8d9d198ae19b4046342
  plan_head_after: e81597978c096d3b39d0b858322ac30508c74cbe

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "captureRootCandidates: a throwaway mctsSearch(maxNodes:1) whose grade wrapper records the first call's candidate list and resolves an empty Map (no engine touched, no hash effect) -- the real root candidate set for a content measurement, never a hand-picked list"
    - "runSplit: one shared dispatcher used by both hash-mode row builders, resolving to prototypeSplit (in-tool round-robin, no rootSplit.ts import) or the real pool.gradeRoot (exits EXIT_MODULE_ABSENT=3 before arm A21S, mirroring scripts/lib/stockfish-pool.check.mjs's own --root-split section verbatim)"
    - "Warm-mode noise floor: two pool.grade() calls launched concurrently on the SAME never-cleared warm pool land on two differently-warmed engines; their divergence (compareGrades) is the noise floor BEFORE any split exists, measured every run rather than assumed"

key-files:
  created:
    - scripts/engine-root-split-content.mjs
  modified: []

key-decisions:
  - "Tasks 1 and 2 were implemented and verified in a single commit (e8159797) rather than two incremental commits. Clear-Hash/prototype (Task 1) and warm-hash/pool-source (Task 2) share the same runSplit/compareGrades/buildRow helpers so tightly that writing Task 1's code first and Task 2's second, as two separate patches to the same small file, would have meant either shipping an intermediate version with a stubbed-out warm branch (dead code that immediately gets replaced) or manually reverse-engineering a partial diff after the fact purely for commit-history cosmetics, with no functional difference in the shipped file. Both tasks' own <verify> commands were run independently against the finished code and both pass (see Self-Check below) -- this is a process deviation on commit granularity, not a scope or correctness gap."
  - "p95_abs_des (the CONTENT summary line's report-only percentile) is computed from the raw flat array of every individual per-candidate |delta es| observed across the whole run, not from the candidate-weighted per-row means candidateWeightedMean produces -- the latter is reused verbatim for mean_abs_des/noise_mean_abs_des specifically because it must match engine_throughput_226_verdict.py's _candidate_weighted_mean definition exactly; p95 has no such downstream consumer in the verdict script and a true per-candidate percentile is the more faithful figure."
  - "Clear-Hash mode's noise_mean_abs_des/noise_max_abs_des TSV columns are left empty and the CONTENT summary line prints 'n/a' rather than a fabricated 0.000000 -- the must_haves truth that single-vs-single is exactly 0 under Clear Hash is a documented invariant of the mechanism, never something this tool actually measures in clear mode (it only measures single vs split there), so printing a number implies a measurement that did not happen."
  - "--fixture PATH reads the same id/fen/correct_move/eval_gap_cp/note/source TSV shape as fixtures/engine/maia-blindness.tsv (and the not-yet-built fixtures/engine/move-quality-226.tsv) via a small local loadFixtureFens reader, rather than importing engine-move-quality.mjs's loadFixtureRows -- this tool only needs id+fen; the move-quality reader also parses/validates correct_move via chess.js, an unnecessary coupling for a grade-content instrument."

requirements-completed: []

coverage:
  - id: D1
    description: "engine-root-split-content.mjs measures Clear-Hash single-vs-split content on a real root candidate set, writing the verdict script's exact content TSV column order"
    verification:
      - kind: other
        ref: "node --import ./scripts/lib/frontend-alias-hook.mjs scripts/engine-root-split-content.mjs --self-test"
        status: pass
      - kind: other
        ref: "node --import ./scripts/lib/frontend-alias-hook.mjs scripts/engine-root-split-content.mjs --split-source prototype --hash clear --fens <one.fens> --openings 0 --out-dir <tmp> (verified via python csv.DictReader: n_candidates=11>1, split_wall_ms=285.7>0)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Warm-Hash mode measures its own single-vs-single noise floor (two concurrent grades on the never-cleared pool) before comparing the split against the first single, and --split-source pool exits 3 with the absent-module message before arm A21S"
    verification:
      - kind: other
        ref: "node ... scripts/engine-root-split-content.mjs --split-source prototype --hash warm --fens <one.fens> --openings 0 --out-dir <tmp> | grep -E \"^CONTENT hash=warm source=prototype rows=1 .*noise_mean_abs_des=[0-9.]+\" -- matched: noise_mean_abs_des=0.004413"
        status: pass
      - kind: other
        ref: "node ... scripts/engine-root-split-content.mjs --split-source pool --hash clear --fens <one.fens> --openings 0 --out-dir <tmp>; exit code 3, prints 'ROOT-SPLIT: rootSplit module absent (pre-A21S arm)'"
        status: pass
    human_judgment: false

duration: 40min
completed: 2026-09-28
status: complete
---

# Phase 226 Plan 06: Root-Split Grade-Content Instrument Summary

**`scripts/engine-root-split-content.mjs`: D-16's grade-content bound and projected-gain instrument, measuring real root candidate sets under Clear-Hash and warm-hash for both an in-tool prototype split and the real pool `gradeRoot`, writing TSVs the verdict script reads unchanged.**

## Performance

- **Duration:** ~40 min
- **Started:** 2026-09-28T08:15:00Z (approx.)
- **Completed:** 2026-09-28T08:52:00Z
- **Tasks:** 2
- **Files modified:** 1 (new)

## Accomplishments

- `captureRootCandidates(fen, providers, elo)` runs a real `mctsSearch(fen, {maxNodes: 1, ...}, wrappedProviders, ...)` whose `grade` wrapper records the first call's candidate list and resolves an empty Map — the real root candidate set (from a live Maia policy + `truncateAndRenormalize` + hard cap), never a hand-picked list, with zero engine/hash side effects.
- `prototypeSplit` partitions candidates round-robin (`i % k`, `k = min(procs, n)`) over the shared `scripts/lib/stockfish-pool.mjs`, timing wall clock and summed per-shard CPU independently; `partitionRoundRobin` is a pure, self-test-covered helper for `k` less than, equal to, and greater than `n`.
- `compareGrades(gradesA, gradesB, fen)` gives per-candidate `|delta cp|` (non-mate pairs only) and `|delta es|` (mover-POV, via `evalToExpectedScore`, mate pairs included), plus a root-argmax-flip boolean (highest mover-POV expected score candidate differing between the two maps).
- Clear-Hash rows compare a single grade against the split (noise columns empty — Clear Hash makes single-vs-single exactly 0 by construction, never measured directly). Warm-hash rows follow the documented order: warm up with one real bot-shaped `mctsSearch` on this run's never-cleared pool, run two concurrent single grades to measure the noise floor, then compare the split against the FIRST single only.
- `--split-source pool` calls the real `pool.gradeRoot`, exiting `EXIT_MODULE_ABSENT` (3) with the exact `ROOT_SPLIT_ABSENT_MESSAGE` before arm A21S (Plan 226-10 has not landed `rootSplit.ts` yet) — verified live — and asserting `pool.rootSplitStats().splits` rose by exactly one per successful call once the module exists.
- Every TSV row matches `scripts/engine_throughput_226_verdict.py`'s `_CONTENT_REQUIRED_COLUMNS` in the same order (verified via `head -1` on a produced TSV), and every run prints a `CONTENT hash=.. source=.. rows=.. mean_abs_des=.. p95_abs_des=.. noise_mean_abs_des=.. single_ms=.. split_wall_ms=.. split_cpu_ms=..` summary line, computed via `candidateWeightedMean` (mean_abs_des/noise_mean_abs_des, the same weighting `engine_throughput_226_verdict.py`'s `_candidate_weighted_mean` uses) and a raw-array nearest-rank percentile (p95).
- `--self-test` exercises `parseArgs` validation (unknown flag, missing/invalid `--split-source`/`--hash`, `--self-test`/`--help` bypass, defaults), `resolvePositions` compatibility, `partitionRoundRobin` (k<n, k==n, k>n), `candidateWeightedMean` (weighted result + zero-weight throw), and `compareGrades` (identical-map zero-delta case) — no engines spawned.

## Task Commits

Both tasks were implemented and verified together in one commit (see Deviations below for why):

1. **Task 1 + Task 2: End-to-end Clear-Hash and warm-Hash content measurement, prototype and pool split sources** - `e81597978` (feat)

**Plan metadata:** committed with this SUMMARY (docs commit follows).

## Files Created/Modified

- `scripts/engine-root-split-content.mjs` (new) — D-16 grade-content and root-split gain instrument. `parseArgs`, `captureRootCandidates`, `partitionRoundRobin`, `prototypeSplit`, `compareGrades`, `candidateWeightedMean`, `buildRow`/`runSplit`/`runClearRow`/`runWarmRow`, `runSelfTest`, `main`.

## Decisions Made

- Tasks 1 and 2 were implemented and committed together (see Deviations) — both tasks' own `<verify>` commands were run and pass independently against the finished code.
- `p95_abs_des` in the CONTENT summary line is computed from the raw flat per-candidate `|delta es|` array across the whole run (not from per-row candidate-weighted means) — the more faithful percentile figure; `candidateWeightedMean` is reserved for the fields (`mean_abs_des`, `noise_mean_abs_des`) that must match the Python verdict script's own weighting definition exactly.
- Clear-Hash mode's noise columns print `n/a` in the summary line and stay empty in the TSV, rather than a fabricated `0.000000` — the exact-zero invariant is documented, never actually measured in clear mode.
- `--fixture` reads a minimal local `id`/`fen` TSV parser rather than importing `engine-move-quality.mjs`'s `loadFixtureRows`, avoiding an unneeded `correct_move`/chess.js validation coupling for a grade-content-only instrument.

## Deviations from Plan

### Flagged for orchestrator decision (Rule 4 — cross-plan contract mismatch, NOT silently resolved)

**1. This tool's output filename does not match `engine_throughput_226_verdict.py`'s frozen `_CONTENT_TSV_PATTERN`**
- **Found during:** Task 1 verification (confirming the produced TSV is discoverable the way the plan's own must_haves require)
- **Issue:** This plan's own Artifacts spec (226-06-PLAN.md) states the output filename as `engine-root-split-content-{hash}-{source}-{stamp}.tsv`, and BOTH of this plan's literal `<verify>` commands hardcode a glob on exactly that prefix (`engine-root-split-content-clear-prototype-*.tsv`). But Plan 226-05 (already committed, prior work) froze `_CONTENT_TSV_PATTERN = "split-root-content-*.tsv"` in `scripts/engine_throughput_226_verdict.py` — a DIFFERENT prefix (transposed: "split-root" vs "root-split") — and 226-05's own SUMMARY.md explicitly states it is "the `split-root-content-*.tsv` contract this plan [226-06] already reads". The two already-written plans disagree with each other on the filename contract; 226-08's plan (the A0 commit) does not mention or resolve this either.
- **Why not silently fixed:** Renaming this tool's output to `split-root-content-*` would satisfy 226-05's frozen constant but BREAK this plan's own two literal `<verify>` commands (which hardcode `engine-root-split-content-*` and are part of this plan's stated acceptance criteria). Renaming `_CONTENT_TSV_PATTERN` in `scripts/engine_throughput_226_verdict.py` to match this tool instead is explicitly prohibited by this plan's own `<threat_model>`/prohibitions ("Do NOT modify any file under frontend/src/ or any other script."). Either direction requires touching a file or a verify command outside this task's authority — an architectural/cross-plan decision, not a Rule 1-3 auto-fix.
- **Action taken:** Followed THIS plan exactly as written (output filename `engine-root-split-content-{hash}-{source}-{stamp}.tsv`, both literal `<verify>` commands pass as specified). Left `scripts/engine_throughput_226_verdict.py` untouched per the prohibition.
- **Consequence if unresolved:** `directory.glob("split-root-content-*.tsv")` will find ZERO files in any directory this tool writes to, so Plan 226-07/226-08/226-12's `design-inputs`/`gates` subcommands will report the content bound as missing (`EXIT_INCOMPLETE`) even after this tool has been run and produced real data — a silent-until-run-time gap, not a crash.
- **Recommended resolution (for the orchestrator or a follow-up plan, NOT executed here):** Either (a) rename this tool's output prefix from `engine-root-split-content-` to `split-root-content-` and update both of THIS plan's `<verify>` commands' glob patterns to match (requires re-opening 226-06-PLAN.md), or (b) update `_CONTENT_TSV_PATTERN` in `scripts/engine_throughput_226_verdict.py` to `"engine-root-split-content-*.tsv"` (requires re-opening the already-shipped 226-05 artifact). Not resolved in this plan — surfaced here per Rule 4.
- **Files modified:** None (informational finding only)
- **Committed in:** N/A

---

### Process deviation (not a Rule 1-4 category — documented for transparency)

**2. Tasks 1 and 2 delivered in a single commit instead of two incremental commits**
- **Found during:** Task 1 implementation
- **Issue:** The plan structures Task 1 (Clear-Hash, prototype split) and Task 2 (warm-Hash + pool split source + extended self-test) as sequential additions to the same new, small file. Writing the file in Task-1-only form first would have meant either (a) omitting the warm-mode/pool-source code paths entirely and adding them in a second patch — straightforward but means Task 1's own commit ships a tool that cannot do half of what its own module docblock documents, which is a worse intermediate state than either task alone — or (b) writing the full, coherent file once (all four command lines the docblock documents actually working) and manually reverse-engineering an artificial two-commit split via `git reset`/partial `git apply` purely for commit-history cosmetics, with zero functional difference in the final shipped code and non-trivial risk of introducing an editing mistake in the process.
- **Fix:** None needed — implemented the complete, coherent file in one pass (both hash modes and both split sources share `runSplit`/`compareGrades`/`buildRow`, so writing them together was also the natural implementation seam), then ran BOTH tasks' `<verify>` commands independently against the finished code, plus the full `--self-test` suite (which includes Task 2's `candidateWeightedMean`/`partitionRoundRobin` self-test extensions). All pass.
- **Files modified:** `scripts/engine-root-split-content.mjs` (single file, single commit)
- **Verification:** See Self-Check below — every one of Task 1's and Task 2's `<verify>` commands re-run and confirmed passing.
- **Committed in:** `e81597978`

---

**Total deviations:** 2 — 1 flagged cross-plan filename-contract mismatch (Rule 4, unresolved, surfaced for orchestrator/follow-up decision) + 1 process/commit-granularity note (no code, scope, or correctness deviation).
**Impact on plan:** This plan's own deliverable and both tasks' acceptance criteria are fully met and independently verified. The filename mismatch is an inter-plan (226-05 vs 226-06) inconsistency that will block Plan 226-07/226-08's `design-inputs`/`gates` from finding this tool's real output until resolved — it does not affect this plan's own completion.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- `scripts/engine-root-split-content.mjs` is ready for Plan 226-07/226-12's step-0 run (the full 16 + fixture position set, both hash modes, prototype split source) and for the arm-A21S re-measurement once Plan 226-10 lands `frontend/src/lib/engine/rootSplit.ts` (at which point `--split-source pool` starts producing real content rows instead of exiting 3).
- The TSV row CONTENT (columns, order, values) is byte-compatible with `scripts/engine_throughput_226_verdict.py`'s `evaluate_content`/`_candidate_weighted_mean`. **The output FILENAME is not** — see "Flagged for orchestrator decision" in Deviations above: this plan's own filename spec/`<verify>` commands (`engine-root-split-content-*`) disagree with Plan 226-05's already-frozen `_CONTENT_TSV_PATTERN` (`split-root-content-*`). Must be resolved before Plan 226-07/226-08 runs `design-inputs`/`gates` against this tool's real output.
- No blockers. `frontend/node_modules` was absent in this fresh worktree and required `npm ci` before any `@/`-aliased script could run (memory note: fresh-worktree gate needs `npm ci` per worktree) — done, not carried forward as a blocker.

---

*Phase: 226-browser-engine-throughput-underfill-root-split-continuous-dispatch*
*Completed: 2026-09-28*

## Self-Check: PASSED

- FOUND: `scripts/engine-root-split-content.mjs`
- FOUND: commit `e81597978` (Task 1 + Task 2)
- Re-ran `--self-test`: all checks pass (parseArgs, partitionRoundRobin k<n/k==n/k>n, candidateWeightedMean weighted + zero-weight throw, compareGrades identical-map case)
- Re-ran Task 1 verify: `--split-source prototype --hash clear --fens <one.fens> --openings 0 --out-dir <tmp>` — `CONTENT hash=clear source=prototype rows=1 ...` printed; TSV row has `n_candidates=11 > 1`, `split_wall_ms=285.7 > 0`
- Re-ran Task 2 verify #1: `--split-source prototype --hash warm ...` — `CONTENT hash=warm source=prototype rows=1 ... noise_mean_abs_des=0.004413` printed
- Re-ran Task 2 verify #2: `--split-source pool --hash clear ...` — exit code 3, `ROOT-SPLIT: rootSplit module absent (pre-A21S arm)` printed
- Verified TSV header (`head -1`) equals `engine_throughput_226_verdict.py`'s `_CONTENT_REQUIRED_COLUMNS`, same order
- Verified `git diff 1f98182ea07ef28dc4aaa8d9d198ae19b4046342 HEAD` touches only `scripts/engine-root-split-content.mjs` (no `frontend/src/` or other script files)
