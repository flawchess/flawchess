---
phase: 241-codebase-cleanup
plan: 33
subsystem: frontend-engine
tags: [cleanup, comments, typescript, worker-pool, maia, engine-assets]

requires:
  - phase: 241-02
    provides: "cleanup.py scan/diff/ledger/codemod"
  - phase: 241-04
    provides: "fe_support.py TypeScript token diff"
provides:
  - "frontend/src/lib/engine worker-pool, Maia host, asset and runtime-source modules free of planning tags"
  - "ledgers/241-33.txt covering all 12 INVENTORY rows of the scope"
affects: [241-60]

actuals:
  tokens: 115000
  tasks: 2
  commits: 2
plan_head_before: a38bb172f4c134a339d99ea99fd725cb439756eb
plan_head_after: dd1e45187544ed13b382bd9b417e81dba81cedd4

tech-stack:
  added: []
  patterns:
    - "Hand edits applied as exact (old, new) pairs through a scratch script that requires each old text to occur exactly once; scratch files live in temp/241-33 (gitignored)"

key-files:
  created:
    - .planning/phases/241-codebase-cleanup/ledgers/241-33.txt
  modified:
    - frontend/src/lib/engine/maiaWorkerHost.ts
    - frontend/src/lib/engine/workerPool.ts
    - frontend/src/lib/engine/workerPoolState.ts
    - frontend/src/lib/engine/workerPoolDispatch.ts
    - frontend/src/lib/engine/workerPoolLifecycle.ts
    - frontend/src/lib/engine/workerPoolWatchdog.ts
    - frontend/src/lib/engine/engineAssetProgress.ts
    - frontend/src/lib/engine/engineAssetCache.ts
    - frontend/src/lib/engine/maiaQueue.ts
    - frontend/src/lib/engine/gradingLadder.ts
    - frontend/src/lib/engine/ortRuntimeSource.ts
    - frontend/src/lib/engine/stockfishWorkerSource.ts
    - frontend/src/lib/engine/maiaPolicyCache.ts
    - frontend/src/lib/engine/maiaPageKillSentinel.ts
    - frontend/src/lib/engine/iosWebKit.ts
    - frontend/src/lib/engine/wasmSimd.ts
    - frontend/src/lib/engine/liveEngineWorkers.ts

key-decisions:
  - "INV-L1370 edge-cache sentence written: every runtime-fetched /maia/* and /engine/* URL carries the ?v=<n> query, so the claim that a cache-version bump also invalidates the Cloudflare edge is true today"
  - "INV-L1307 (B row) LEFT: the ortRuntimeSource.ts byte constants and their doc lines are untouched"
  - "Closed-seed pointers (SEED-126, 158, 171, 180, 195, 106) dropped; SEED-129 (open, deferred rated-puzzle benchmark) kept as (see SEED-129) in gradingLadder.ts"

requirements-completed: [D-01, D-04, D-10, D-11, D-12, D-13, D-15]

duration: 75min
completed: 2026-10-16
status: complete
---

# Phase 241 Plan 33: Engine Worker Pool and Asset Modules Comment Cleanup Summary

**Planning tags are gone from the Stockfish worker pool, the Maia worker host and the engine asset modules (17 files, 404 tagged lines scanned), 11 of 12 INVENTORY rows applied and the stale-constant B row left, with an empty non-comment token diff against PHASE_BASE.**

## Accomplishments

- Task 1 (`dc1f4ffa6`): maiaWorkerHost, workerPool, workerPoolState, workerPoolDispatch, workerPoolLifecycle, workerPoolWatchdog. Rows L1266, L1269, L1308, L1309, L1312, L1313, L1341 applied.
- Task 2 (`dd1e45187`): engineAssetProgress, engineAssetCache, maiaQueue, gradingLadder, ortRuntimeSource, stockfishWorkerSource, maiaPolicyCache, maiaPageKillSentinel, iosWebKit, wasmSimd, liveEngineWorkers. Rows L1306, L1311, L1370, L1371 applied; L1307 left.
- `workerErrorContext.ts` was clean in the scan and stays untouched (its "used to report" history wording is not a planning tag; not inventoried).
- The comments now describe current behavior: the priority queue is "FIFO in practice, field reserved", the required-asset set lists all three assets, `EngineProviders.grade` is described by its real 3-arg shape, the cache-version changelog is replaced by the bump rule.

## Ledger counts (ledgers/241-33.txt)

| Status | Rows |
|---|---|
| APPLIED | 11 (L1266, L1269, L1306, L1308, L1309, L1311, L1312, L1313, L1341, L1370, L1371) |
| LEFT | 1 (L1307, B row) |
| MOVED / SKIPPED / DEFERRED | 0 |

One extra `#` comment line records the secondary workerPoolLifecycle.ts clause of INV-L1311 (the ledger parser accepts only plain `INV-L<n>` lines).

## INV-L1370 edge-cache finding

The planner's assumption (project memory says the cache version was once browser-only and the Cloudflare edge needed a manual purge) was checked before writing the sentence. Result: the claim holds today. `versionedEngineAssetUrl()` builds `ENGINE_PATH` (maia-worker.js), `ORT_RUNTIME_WASM_ONLY_PATH`, `ORT_RUNTIME_ASYNCIFY_PATH`, `STOCKFISH_ENGINE_GLUE_PATH` and `STOCKFISH_ENGINE_WASM_PATH`, and `frontend/public/maia/maia-worker.js` builds `MODEL_PATH`, the `importScripts` URLs and both `wasmPaths` objects through `versionedAssetUrl()` with the `assetVersionQuery` from the init message. Cloudflare keys on the full URL, so a version bump produces URLs no edge has cached. The memory entry predates the versioned-URL change. The sentence "also invalidates the Cloudflare edge, so no manual purge is needed" was therefore written.

## Codemod vs hand edits

| | Codemod (safe tag shapes) | Hand edits |
|---|---|---|
| Task 1 files | 66 lines in 6 files | about 185 lines (31 + 8 + 19 + 22 + 34 + 57 exact-text replacements, some spanning several lines) |
| Task 2 files | 46 lines in 9 files | about 114 lines (10 + 32 + 13 + 15 + 12 + 14 + 8 + 7 exact-text replacements) |

Every codemod result was reviewed with `git diff -U0`; no broken sentence was left.

## Non-inventoried fixes (Rule 2, STYLE-GUIDE §2.2)

- workerPoolState.ts header: the "WR-01 history" paragraph (a narration of a closed review finding) became a present-tense rule on why the leaf definitions stay in this file.
- workerPoolLifecycle.ts: "equivalent guard below" corrected to "above" (replaceDeadSlot precedes runSpawnConstructionLoop), part of INV-L1341.
- workerPool.ts: the `GradeCache` header no longer says "byte-identical to the pre-extraction closure"; "SEED-170 'Explicitly out of scope'" became a plain statement.
- maiaWorkerHost.ts: the retired `modelBuffer` / `G-213-8` handoff comments became "no model bytes ride along" rules; the Phase 219 UAT narration in `respawnPinnedToWasm` became a present-tense reason.
- engineAssetProgress.ts: `Hotfix 2026-09-06` / `Bug fix (...)` provenance dropped, kept as "why" clauses; `engineGateRequired` no longer quotes "53.0 MB" or "pair".
- gradingLadder.ts: "Phase 199's combined sweep ... Landing this before Phase 199 is deliberate" became a timeless statement of the re-sweep requirement and the revert target.
- iosWebKit.ts: the "seed file keeps the history" sentence became "older readings no longer apply".

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Environment prep in a fresh worktree**
- `npm --prefix frontend ci` (lockfile install, no new packages) before the baseline; `uv run` created `.venv` on first use. `uv sync --group maia-inference` was not needed (no ty run in this plan).

**2. [Plan note] Ledger comment line**
- The plan asks for a `INV-L1311 (secondary workerPoolLifecycle.ts): STATUS` line; the parser rejects it, so it is a `#` comment line (listed above).

**3. [Environment] source_scan_tests.sh Python half run serially**
- Per the parallel-execution note: `--fe` half as-is; the Python half run without `-n 4` (shared dev Postgres). Same file list, same results.

**Total deviations:** 1 blocking env prep, 2 plan notes; no code, constant, URL, testid, Sentry or Umami change.

## Verification

| Command | Result |
|---|---|
| `cleanup.py scan --gate --scope scopes/241-33.txt` | exit 0 (18 files, 0 matches) |
| `cleanup.py diff --scope scopes/241-33.txt` | exit 0 (no residue) |
| `cleanup.py ledger --scope scopes/241-33.txt --ledger ledgers/241-33.txt` | exit 0 |
| `npm --prefix frontend run lint` | clean (before and after) |
| `source_scan_tests.sh --fe` | 9 files, 131 tests passed (same as untouched baseline) |
| Python half, serial | 95 passed + 5 passed |
| `npx vitest run src/lib/engine` | 790 passed |

## Known Stubs

None.

## Threat Flags

None. Comments only; `ENGINE_ASSET_CACHE_VERSION`, byte constants, asset paths, Sentry tags and messages are unchanged (the token diff proves it). T-241-50 mitigated by the INV-L1370 check above.

## Observations outside scope (not changed)

- `frontend/public/maia/maia-worker.js` and `frontend/public/maia/README.md` still carry quick-task and Phase 213 tags in comments; they are not in scopes/241-33.txt.
- INV-L1307 stays: the ORT byte constants (13_961_845 / 25_749_873 at 1.29.0) are stale versus the vendored 1.27.0 files (INVENTORY §7.2 #13, a code change).

## Self-Check: PASSED

Ledger and edited files verified present; commits `dc1f4ffa6` and `dd1e45187` are ancestors of HEAD.

---
*Phase: 241-codebase-cleanup*
*Completed: 2026-10-16*
