---
phase: 136-usestockfishengine-hook-wasm-setup
plan: "01"
subsystem: infra
tags: [stockfish, wasm, pwa, vite, ci, engine, service-worker]

# Dependency graph
requires: []
provides:
  - "frontend/public/engine/stockfish-18-lite-single.js vendored Emscripten JS glue for single-thread Stockfish 18 lite WASM"
  - "frontend/public/engine/stockfish-18-lite-single.wasm binary (7.0 MB, single-thread NNUE lite)"
  - "stockfish@18.0.8 exact-pinned npm dependency (provenance anchor for vendored binaries)"
  - "vite.config.ts: optimizeDeps.exclude=['stockfish'] + workbox.globIgnores=['**/*.wasm']"
  - "CI step: COOP/COEP absence guard + application/wasm MIME check via curl -I on vite preview"
  - "PLAT-01 (no COOP/COEP headers, CI-guarded) and PLAT-02 (iOS-safe SW wasm handling) satisfied"
affects:
  - "136-02 (Plan 02 consumes /engine/stockfish-18-lite-single.js path constant + node-env integration test imports stockfish package)"
  - "future engine phases"

# Tech tracking
tech-stack:
  added:
    - "stockfish@18.0.8 (nmrugg/stockfish.js, GPL-3.0, vendored WASM build)"
  patterns:
    - "Vendored static binaries in frontend/public/engine/ served verbatim at /engine/* URL path (no vite-plugin-static-copy)"
    - "Exact version pin (no caret) for packages with committed-to-git binary artifacts"
    - "globIgnores: ['**/*.wasm'] in VitePWA workbox block to exclude large WASM from iOS SW precache"
    - "CI curl -I guard on vite preview port to assert header/MIME invariants"

key-files:
  created:
    - "frontend/public/engine/stockfish-18-lite-single.js"
    - "frontend/public/engine/stockfish-18-lite-single.wasm"
  modified:
    - "frontend/package.json"
    - "frontend/package-lock.json"
    - "frontend/knip.json"
    - "frontend/vite.config.ts"
    - ".github/workflows/ci.yml"
    - "README.md"

key-decisions:
  - "Vendor binaries from node_modules/stockfish/bin/ (not src/ — package structure changed; bin/ is the correct path in v18.0.8)"
  - "Exact pin 18.0.8 (no caret) so the committed vendored files always match the package the integration test imports"
  - "Add stockfish to knip.json ignoreDependencies: the package has no direct import in Plan 01 source files; Plan 02 integration test adds dynamic import('stockfish')"
  - "Worker process boundary chosen for GPLv3 isolation: keeps GPL non-infective for FlawChess application code"

patterns-established:
  - "Engine Worker path: new Worker('/engine/stockfish-18-lite-single.js') — classic (non-module) Worker, Emscripten requirement"
  - "WASM exclusion: workbox.globIgnores=['**/*.wasm'] — browser HTTP cache handles engine caching, not SW precache"
  - "Header guard pattern: npm run preview & PID=$!; sleep 3; curl -sf -I; kill $PID — reusable for future static-header CI assertions"

requirements-completed: [PLAT-01, PLAT-02]

# Metrics
duration: 5min
completed: 2026-06-26
status: complete
---

# Phase 136 Plan 01: useStockfishEngine Hook + WASM Setup (Platform Foundation) Summary

**Stockfish 18 lite single-thread WASM (7.0 MB) vendored at frontend/public/engine/, CI guards locking in COOP/COEP absence and application/wasm MIME type**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-06-26T10:05:00Z
- **Completed:** 2026-06-26T10:10:47Z
- **Tasks:** 3 (Task 1 pre-approved, Tasks 2-3 executed)
- **Files modified:** 6 files, 2 binary files created

## Accomplishments
- Task 1 (SUS gate): Human approved stockfish@18.0.8 provenance before install (v18.0.8, nmrugg/stockfish.js, 29k weekly downloads, GPL-3.0, postinstall is symlink-only)
- Task 2: stockfish@18.0.8 installed exact-pinned, engine binaries vendored from node_modules/stockfish/bin/ to frontend/public/engine/ (7.0 MB wasm, 21 KB JS glue), GPLv3 provenance note added to README.md
- Task 3: vite.config.ts wired (optimizeDeps.exclude + workbox.globIgnores), CI step added that asserts no COOP/COEP headers on page AND application/wasm MIME on /engine/*.wasm
- A1 verified: vendored wasm is 7,295,411 bytes (7.0 MB), within expected range
- A3 verified: local `npm run preview` + `curl -I` confirms `content-type: application/wasm` on the wasm asset

## Task Commits

1. **Task 1: SUS gate (pre-approved)** - no commit (checkpoint only, no files changed)
2. **Task 2: Install + pin stockfish, vendor engine binaries, README provenance** - `aed74997` (feat)
3. **Task 3: Wire vite.config.ts (optimizeDeps + globIgnores) and add CI COOP/COEP guard** - `993a5899` (feat)
4. **Rule 2 fix: knip ignoreDependencies** - `68e66cf9` (fix)

## Files Created/Modified
- `frontend/public/engine/stockfish-18-lite-single.js` - Emscripten JS glue (21 KB), verbatim from stockfish@18.0.8 bin/
- `frontend/public/engine/stockfish-18-lite-single.wasm` - Single-thread NNUE lite WASM binary (7,295,411 bytes / 7.0 MB)
- `frontend/package.json` - Added `"stockfish": "18.0.8"` exact pin to dependencies (no caret)
- `frontend/package-lock.json` - Lock file updated for stockfish@18.0.8
- `frontend/knip.json` - Added `"stockfish"` to `ignoreDependencies` (Rule 2 fix)
- `frontend/vite.config.ts` - Added `optimizeDeps.exclude: ['stockfish']` + `workbox.globIgnores: ['**/*.wasm']`
- `.github/workflows/ci.yml` - New CI step after vitest, before knip: curl -I guards on vite preview
- `README.md` - GPLv3 provenance note for vendored engine binaries

## Decisions Made
- **Bin path deviation:** RESEARCH.md and PATTERNS.md referenced `node_modules/stockfish/src/` but the actual package structure in v18.0.8 uses `node_modules/stockfish/bin/`. Files were copied from `bin/` — the correct location (verified by `find`).
- **Knip `ignoreDependencies`:** No frontend source file imports the `stockfish` package in Plan 01. Plan 02's integration test will use `import('stockfish')` dynamically. To prevent CI knip gate failure on the Plan 01 PR, `stockfish` was added to `ignoreDependencies`. This can be revisited after Plan 02 lands.
- **Exact pin vs. caret:** `"stockfish": "18.0.8"` (no `^`) ensures the vendored binary bytes in git always match what the integration test in Plan 02 will boot. A caret would allow a future npm update to misalign the committed files.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added stockfish to knip.json ignoreDependencies**
- **Found during:** Task 3 acceptance verification (`npm run knip`)
- **Issue:** knip flagged `stockfish` as an unused dependency (0 source imports in Plan 01). CI would fail the `Dead code check (knip)` step.
- **Fix:** Added `"stockfish"` to `ignoreDependencies` in `frontend/knip.json`. The package IS used — as the provenance anchor for the vendored binaries, and Plan 02's integration test will import it dynamically.
- **Files modified:** `frontend/knip.json`
- **Verification:** `npm run knip` exits 0 after the fix
- **Committed in:** `68e66cf9`

---

**Total deviations:** 1 auto-fixed (1 missing critical)
**Impact on plan:** Necessary to prevent CI failure. No scope creep. Stockfish exclusion in knip is intentional until Plan 02 adds the dynamic import.

### Minor Discovery (no action needed)
- `node_modules/stockfish/src/` does not exist in v18.0.8; files are in `bin/`. PATTERNS.md referenced the older path. Files were copied from the correct `bin/` location. No plan change needed.

## Issues Encountered
None beyond the knip deviation above.

## User Setup Required
None - no external service configuration required.

## Verification Results

| Check | Result |
|-------|--------|
| A1: vendored wasm size | 7,295,411 bytes (7.0 MB) — within ~7 MB expected range |
| A3: vite preview MIME | `content-type: application/wasm` on /engine/stockfish-18-lite-single.wasm — CONFIRMED |
| No COOP/COEP headers | Page response carries no Cross-Origin-Opener-Policy or Cross-Origin-Embedder-Policy — CONFIRMED |
| sw.js excludes wasm | `dist/sw.js` has no precache entry for `stockfish-18-lite-single.wasm` — CONFIRMED |
| knip gate | 0 errors after adding stockfish to ignoreDependencies |
| vitest (1150 tests) | All pass |

## Next Phase Readiness
- Plan 02 can immediately implement `useStockfishEngine.ts` — engine path `/engine/stockfish-18-lite-single.js` is available in dist
- Plan 02's integration test can `import('stockfish')` from the pinned package
- The CI guard will catch any future accidental introduction of COOP/COEP headers or wrong WASM MIME

---
*Phase: 136-usestockfishengine-hook-wasm-setup*
*Completed: 2026-06-26*
