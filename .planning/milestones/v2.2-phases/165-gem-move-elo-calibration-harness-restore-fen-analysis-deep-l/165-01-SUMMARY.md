---
phase: 165-gem-move-elo-calibration-harness-restore-fen-analysis-deep-l
plan: 01
subsystem: tooling
tags: [node, onnxruntime-web, stockfish, uci, maia, gem-move, calibration, chess.js, type-stripping]

# Dependency graph
requires: []
provides:
  - Committed `scripts/lib/frontend-alias-hook.mjs` Node resolve hook (`@/...` -> `frontend/src/*.ts`) for importing live frontend TS from headless scripts with zero new packages
  - Committed `scripts/lib/gem-parity.check.mjs` — Wave 0 tripwire asserting the imported classifyGem/summarizeForGem/evalToExpectedScore/MISTAKE_DROP reproduce hand-derived results
  - Committed `scripts/gem-elo-calibration.mjs` — headless gem-ELO calibration harness (Maia 6-rung + Stockfish C2 + stratified CSV sampling -> TSV)
affects: [166-gem-move-ceiling-recalibration (deferred D-08 follow-up), any future headless-frontend-TS Node tooling]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Node v24 type-stripping + a tiny `@/` module resolve hook (registerHooks) to import live frontend TypeScript from a `.mjs` script with zero new packages/build steps"
    - "createRequire(frontend/package.json) + dynamic import(pathToFileURL(...)) to resolve frontend-vendored runtime deps (onnxruntime-web, chess.js) from a script outside frontend/src"
    - "Two-pass streaming stratified reservoir sampling (Algorithm R, seeded mulberry32 PRNG) over a multi-GB CSV, with EXPENSIVE per-row validation applied lazily only to reservoir-slot candidates"
    - "Vendored Stockfish WASM driven headlessly via a spawned Node child process (copy .js->.cjs AND matching-basename .wasm, since Emscripten glue resolves the wasm binary by basename-of-script, not original filename)"

key-files:
  created:
    - scripts/lib/frontend-alias-hook.mjs
    - scripts/lib/gem-parity.check.mjs
    - scripts/gem-elo-calibration.mjs
  modified:
    - .gitignore

key-decisions:
  - "Grade ALL legal root moves for Stockfish C2 (MultiPV = min(legal, 32), no searchmoves) rather than the frontend's display-union-restricted C2 — intentional divergence per RESEARCH Landmine 3, needed for an honest playedIsBest in calibration"
  - "Lazy per-row FEN/SAN validation: only rows that actually win a reservoir slot get the expensive new Chess(fen).move(san) check, not all ~22M CSV rows — keeps small --n smoke runs fast (~25s total)"
  - "Dedupe quantile-derived strata edges before sampling: tied `score` boundary values otherwise produce degenerate empty strata that silently undercount --n"

patterns-established:
  - "Pattern: headless Node harness importing live frontend TS via `@/` alias resolve hook + type-stripping — reusable for any future gem/eval/engine calibration tooling without a bundler"

requirements-completed: [SEED-094]

coverage:
  - id: D1
    description: "scripts/lib/frontend-alias-hook.mjs + scripts/lib/gem-parity.check.mjs: @/ resolve hook loads live frontend TS, and the gem-parity check confirms imported classifyGem/summarizeForGem/evalToExpectedScore/MISTAKE_DROP reproduce hand-derived fixture results"
    requirement: "SEED-094"
    verification:
      - kind: other
        ref: "node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/gem-parity.check.mjs (exits 0, prints PASS)"
        status: pass
    human_judgment: false
  - id: D2
    description: "scripts/gem-elo-calibration.mjs: end-to-end harness runs at --n 5, samples via stratified reservoir, grades via real Stockfish C2 + 6-rung Maia forward passes, emits a D-05-schema TSV + drop-off summary TSV to reports/data/"
    requirement: "SEED-094"
    verification:
      - kind: other
        ref: "node --import ./scripts/lib/frontend-alias-hook.mjs scripts/gem-elo-calibration.mjs --n 5 --seed 1 --movetime 800 (exit 0; wrote gem-elo-calibration-<ts>.tsv + -summary.tsv; header matches D-05 column order; gem-detection rate correctly drops 20%->0% across rungs)"
        status: pass
    human_judgment: false

duration: 17min
completed: 2026-07-11
status: complete
---

# Phase 165 Plan 01: Gem-ELO Calibration Harness Summary

**Headless Node harness measuring raw Maia probability of played "brilliant" moves across 6 ELO rungs + a single Stockfish C2 grade, importing live frontend gem logic via a zero-dependency `@/` type-stripping resolve hook.**

## Performance

- **Duration:** 17 min
- **Started:** 2026-07-11T12:46:00Z
- **Completed:** 2026-07-11T13:03:00Z
- **Tasks:** 2
- **Files modified:** 4 (3 created, 1 gitignore fix)

## Accomplishments
- `scripts/lib/frontend-alias-hook.mjs` — a ~40-line Node module resolve hook (via `node:module`'s `registerHooks`) rewriting `@/...` specifiers to `frontend/src/*.ts`, relying on Node v24's native TypeScript type-stripping to load them. Zero new npm packages.
- `scripts/lib/gem-parity.check.mjs` — asserts the imported `classifyGem`/`summarizeForGem` reproduce hand-derived best/second-best expected scores and gem booleans for a fixed fixture, and that `MISTAKE_DROP`/`GEM_MAIA_MAX_PROB` still equal their documented values (zero-drift tripwire per T-165-02).
- `scripts/gem-elo-calibration.mjs` — the full harness: two-pass streaming stratified reservoir sampling over the 22.4M-row `temp/brilliants_no_stalemates.csv` (never loaded fully into memory), one Stockfish C2 grade per position (all legal moves, MultiPV capped at 32) plus one batched 6-rung Maia `onnxruntime-web` forward pass, emitting a D-05-schema TSV (raw probs + gem-at-0.1 booleans + clickable `?fen=` analysis links) and a sibling drop-off summary TSV.
- Smoke-tested at `--n 5`: sampled exactly 5 stratified positions, graded them with the real vendored Stockfish + Maia engines, and produced a plausible gem-detection-rate-vs-ELO curve (20% at rung 600, dropping to 0% by rung 1000+ — the expected calibration signal per SEED-094).

## Task Commits

Each task was committed atomically:

1. **Task 1: Frontend `@/` resolve hook + gem-logic parity check** - `7d14c0ad` (feat)
2. **Task 2: Gem-ELO calibration harness** - `813d31c3` (feat)

_No separate plan-metadata commit yet — STATE.md/ROADMAP.md/REQUIREMENTS.md update follows this SUMMARY in the standard state-update + final-commit steps._

## Files Created/Modified
- `scripts/lib/frontend-alias-hook.mjs` - Node resolve hook rewriting `@/...` to `frontend/src/*.ts` for headless imports of live frontend TS
- `scripts/lib/gem-parity.check.mjs` - Wave 0 assertion that imported gem logic reproduces hand-derived fixture results (zero-drift tripwire)
- `scripts/gem-elo-calibration.mjs` - the calibration harness (CLI, CSV sampling, Maia + Stockfish grading, TSV/summary emission)
- `.gitignore` - added `!scripts/lib/` exception (see Deviations)

## Decisions Made
- Grade Stockfish C2 over ALL legal root moves (MultiPV = min(legalCount, `--multipv-cap`), no `searchmoves`) rather than mirroring the frontend's display-union-restricted grading — intentional per RESEARCH Landmine 3, since calibration needs an honest best-vs-runner-up over the whole legal-move set.
- Apply expensive per-row FEN/SAN validation (`new Chess(fen).move(san)`) lazily, only to CSV rows that actually win a stratified-reservoir slot, rather than to all ~22.4M rows — keeps the two required streaming passes fast (a few seconds each on a warm page cache) regardless of `--n`.
- Distribute `--n` across strata via `floor(n/S)` + remainder (not a flat `ceil(n/S)`), so small `--n` smoke runs land on the requested count instead of inflating to the strata count.
- Skip the UCI `ucinewgame` command between graded positions (documented as optional in RESEARCH Q3) — simpler, and hash-table reuse across distinct FENs has no correctness impact, only a possible minor search-depth variance.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `.gitignore`'s Python-boilerplate `lib/` pattern silently ignored `scripts/lib/`**
- **Found during:** Task 1 (creating `scripts/lib/frontend-alias-hook.mjs` and `scripts/lib/gem-parity.check.mjs`)
- **Issue:** The repo's Python-oriented `.gitignore` has a bare `lib/` pattern (matches any directory named `lib` anywhere), with only `!frontend/src/lib/` explicitly un-ignored. The new `scripts/lib/` directory was silently caught by the same rule — `git status` showed nothing for the two new files.
- **Fix:** Added a `!scripts/lib/` exception mirroring the existing `!frontend/src/lib/` override.
- **Files modified:** `.gitignore`
- **Verification:** `git check-ignore -v scripts/lib/*.mjs` returns no match after the fix; both files staged and committed successfully.
- **Committed in:** `7d14c0ad` (Task 1 commit)

**2. [Rule 1 - Bug] Vendored Stockfish's Emscripten glue resolves its `.wasm` binary by the SCRIPT's basename, not the original filename**
- **Found during:** Task 2 smoke test — Stockfish never emitted `uciok`, timing out after 30s.
- **Issue:** The vendored `stockfish-18-lite-single.js` glue computes its wasm path as `path.join(__dirname, basename(__filename, ext) + '.wasm')` when run directly under Node (`require.main === module`). Copying only the `.js` to a differently-named `.cjs` in `os.tmpdir()` left it looking for a `.wasm` file matching the NEW basename, which didn't exist — the process aborted on `ENOENT` before ever reaching the UCI CLI.
- **Fix:** `spawnStockfish()` now copies BOTH the `.js` (as `<runId>.cjs`) AND the `.wasm` (renamed to `<runId>.wasm`) into the same temp directory, so the basename match holds.
- **Files modified:** `scripts/gem-elo-calibration.mjs`
- **Verification:** Manually reproduced against a standalone copy in the scratchpad dir (confirmed the `uciok`/`readyok`/`option name ...` UCI handshake once both files were present with matching basenames), then confirmed the full harness smoke run completes and grades positions.
- **Committed in:** `813d31c3` (Task 2 commit)

**3. [Rule 1 - Bug] Quantile-derived strata edges collided on tied `score` values, producing empty strata that undercounted `--n`**
- **Found during:** Task 2 smoke test — `--n 5` sampled only 4 positions instead of 5.
- **Issue:** The CSV's `score` field is heavily discretized at its low end (many rows share e.g. `3.7`/`3.8`/`3.9` exactly). Two adjacent quantile cut points computed from the sorted-score array could land on the same tied value, making the earlier stratum's `score <= edge` predicate swallow every row that would have belonged to the next stratum — leaving it permanently empty. Debug instrumentation confirmed 4 of 15 strata were empty (counts `[..., 0, ..., 0, 0, ..., 0, ...]`) purely from this collision, not from a genuine gap in the data.
- **Fix:** Dedupe the raw quantile edges (`[...new Set(rawEdges)]` — the array is already sorted ascending, so `Set` preserves order) and derive the effective stratum count from `edges.length + 1` rather than the nominal `STRATA_COUNT`, guaranteeing every stratum is non-empty by construction.
- **Files modified:** `scripts/gem-elo-calibration.mjs`
- **Verification:** Re-ran `--n 5 --seed 1`: sampled exactly 5 positions (previously 4); a standalone debug script confirmed per-stratum row counts are now all non-zero after dedup.
- **Committed in:** `813d31c3` (Task 2 commit)

**4. [Rule 1 - Bug] Unused direct `evalToExpectedScore` import left as dead code**
- **Found during:** Task 2 code-quality pass (post-smoke-test)
- **Issue:** The plan's "New symbols imported" list included `evalToExpectedScore`, but the harness never calls it directly — it's exercised transitively through `summarizeForGem` (which imports it internally from the same `@/lib/liveFlaw` module). The first draft imported it anyway and suppressed the unused-import smell with a `void evalToExpectedScore;` line.
- **Fix:** Removed the direct import and the `void` workaround; added a comment at the `@/lib/liveFlaw` import site explaining `evalToExpectedScore` is validated directly by the Wave 0 gem-parity check and exercised transitively here via `summarizeForGem`.
- **Files modified:** `scripts/gem-elo-calibration.mjs`
- **Verification:** Re-ran the `--n 5` smoke test and the gem-parity check after the cleanup — both still pass.
- **Committed in:** `813d31c3` (Task 2 commit)

---

**Total deviations:** 4 auto-fixed (1 blocking gitignore fix, 2 bugs found during smoke testing, 1 code-quality cleanup)
**Impact on plan:** All four were necessary for the harness to actually run and be committable as specified. No scope creep — no architectural changes, no new dependencies, `GEM_MAIA_MAX_PROB`/`gemMove.ts` untouched per the plan's explicit boundary.

## Issues Encountered
- The full `--n 3000` (~2.5h) soak run was NOT executed as part of this plan — per the plan's own acceptance criteria and assumptions, only the `--n 5` smoke run was required for Wave 0 sign-off; the full soak is deferred to manual verification (the plan's stated `success_criteria`: "Full `--n 3000` soak (~2.5 h) is runnable but deferred to manual verification").
- The `temp/brilliants_no_stalemates.csv` input (2.2GB, gitignored) was present in the local dev environment, so the smoke test ran against the real dataset rather than a synthetic fallback — no limitation to document there.

## User Setup Required
None - no external service configuration required. The harness's only external input (`temp/brilliants_no_stalemates.csv`) is a local, gitignored dataset file already present in this environment; a future run on a machine without it will fail fast on the CSV read with a clear ENOENT, not silently.

## Next Phase Readiness
- The harness is committed, reusable, and parameterized (`--n`, `--seed`, `--movetime`, `--multipv-cap`, `--csv`, `--out-dir`, `--rungs`) — ready for a full `--n 3000` soak run whenever the empirical basis for the deferred D-08 ELO-scaled iso-rarity gem ceiling is needed.
- This plan intentionally did NOT touch `gemMove.ts`/`GEM_MAIA_MAX_PROB` — that recalibration remains a separate follow-up seed, unblocked by this harness's TSV output.
- Plan 02 of this phase (the `?fen=` analysis deep-link restoration) is independent of this plan's harness work and can proceed without depending on it.

---
*Phase: 165-gem-move-elo-calibration-harness-restore-fen-analysis-deep-l*
*Completed: 2026-07-11*

## Self-Check: PASSED

- FOUND: scripts/lib/frontend-alias-hook.mjs
- FOUND: scripts/lib/gem-parity.check.mjs
- FOUND: scripts/gem-elo-calibration.mjs
- FOUND: .planning/phases/165-gem-move-elo-calibration-harness-restore-fen-analysis-deep-l/165-01-SUMMARY.md
- FOUND commit: 7d14c0ad (Task 1)
- FOUND commit: 813d31c3 (Task 2)
- FOUND commit: b06d08d5 (SUMMARY.md)
