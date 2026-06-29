# Phase 136: `useStockfishEngine` Hook + WASM Setup - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-26
**Phase:** 136-usestockfishengine-hook-wasm-setup
**Areas discussed:** Verification surface, Engine file delivery, Tab-hide pause

---

## Verification surface

| Option | Description | Selected |
|--------|-------------|----------|
| Tests only, no UI | UCI-parser unit tests + 1 headless Worker integ test (FEN→eval). No route/harness ships in 136; manual verify deferred to P138. | ✓ |
| Throwaway dev harness | Dev-only `/engine-test` route mounting the hook on a fixed FEN, dumping eval/pv/depth as text; deleted in 137/138. Visual + iOS check this phase. | |
| Reuse an existing board | Wire hook onto an existing board behind a temp toggle to verify live, then unwire. Realistic but touches out-of-phase code. | |

**User's choice:** Tests only, no UI
**Notes:** Manual / on-device verification deferred to Phase 138. Flagged in CONTEXT.md that a real headless Worker boot under Vitest is non-trivial (`Worker` not native in node) — planner must pick the harness mechanism (`@vitest/web-worker` / `node:worker_threads` / stockfish-node) with a documented fallback.

---

## Engine file delivery

| Option | Description | Selected |
|--------|-------------|----------|
| Commit to public/engine/ | Copy the two files into `public/engine/` and commit. No new dep, reproducible offline builds; cost is a ~7 MB blob in git. | ✓ |
| vite-plugin-static-copy | Add the dev-dep plugin to copy files from `node_modules/stockfish/src/` at build time. Git stays lean; depends on npm package version + dev-server serving. | |

**User's choice:** Commit to public/engine/
**Notes:** `optimizeDeps.exclude: ['stockfish']` still required even with manual vendoring. `stockfish` v18 kept as a pinned dependency for provenance + README GPLv3 acknowledgement.

---

## Tab-hide pause (PLAT-02)

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-resume analysis | On hide, `stop` (worker stays alive); on return, auto re-`go` on current position. Seamless live eval on return, no re-init. | ✓ |
| Pause, resume on interaction | On hide, stop and idle; on return, stay paused until next move/toggle. Saves CPU if user returns passively. | |

**User's choice:** Auto-resume analysis
**Notes:** Worker is reused (never terminated on hide), so no WASM re-init cost on return.

---

## Claude's Discretion

- UCI state-machine internals (enum naming, MultiPV map keying, debounce/stop wiring), the secondary `go nodes` safety valve, and the exact tab-resume `go`-param handling are left to the planner/executor within the locked bounds (lite-single build, `go movetime 1500`, MultiPV=2, 150ms debounce, stop-pending guard, no COOP/COEP).

## Deferred Ideas

- On-device (iOS Safari / low-end Android) manual verification → Phase 138 gate.
- Real-device `movetime` calibration → Phase 138 / UAT smoke check.
- `go nodes` desktop mode / adjustable engine strength → out of v1.29 scope.
- Multi-thread WASM engine (ENGINE-V2-01, D-3) → deferred to v2.
