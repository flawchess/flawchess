---
phase: 227-browser-engine-continuous-dispatch-against-a-relaxed-determi
plan: 05
subsystem: calibration-harness
tags: [calibration, dispatch-mode, ledger, resume, supervisor, determinism]

requires:
  - phase: 227-02
    provides: "scripts/lib/dispatch-mode.mjs (parseDispatchModeFlag, defaultDispatchMode, assertDispatchModeLive), FLAWCHESS_DISPATCH_MODE"
  - phase: 227-01
    provides: "makeNodeProviders maiaFifo option"
provides:
  - "calibration-harness --dispatch-mode round|continuous (default app constant), live-probed before engine bring-up"
  - "dispatch_mode as the 22nd (last) raw ledger column; --resume refuses a different mode or a pre-227 ledger"
  - "PRESET_SUPERVISOR_DISPATCH_MODE passed on every supervisor launch and crash-resume"
  - "determinism check pinned to round mode plus app/harness dispatch parity assertion"
affects: [227-08, 227-10, 227-11, 227-13]

actuals:
  tokens: 14000
  tasks: 2
  commits: 2
plan_head_before: cb82bf558f50333e574f9f646ae446f08257f3a1
plan_head_after: 26a6f6ac1feafb9c944beeccf7bbcb04af1f8810

tech-stack:
  added: []
  patterns:
    - "Append-at-end ledger columns (D-08 discipline) extended with dispatch_mode"
    - "Resume refusals run before the live dispatch probe and before any engine bring-up"

key-files:
  created: []
  modified:
    - scripts/calibration-harness.mjs
    - scripts/lib/calibration-ledger-schema.check.mjs
    - scripts/lib/calibration-determinism.check.mjs
    - bin/preset-supervisor.sh

key-decisions:
  - "Resume refusal order: ledger replay (incl. dispatch_mode mismatch) runs before assertDispatchModeLive, so scenario (e) never depends on Plan 227-10 landing the continuous loop"
  - "ledgerRowLine throws (fixed 'Invalid dispatch mode' message) on a row without a valid mode rather than writing 'undefined' into a ledger"
  - "playGame defaults dispatchMode to defaultDispatchMode() so any caller measures the app's shipped mode; the determinism check pins 'round' explicitly"

requirements-completed: []

duration: 25min
completed: 2026-10-02
status: complete
---

# Phase 227 Plan 05: Calibration harness dispatch-mode parity Summary

**The calibration harness now runs the app's dispatch flag end to end: `--dispatch-mode` (supervisor env `PRESET_SUPERVISOR_DISPATCH_MODE`) feeds the bot budget after a live probe, every ledger row records `dispatch_mode`, and `--resume` refuses to mix arms.**

## Accomplishments

- **Harness (`scripts/calibration-harness.mjs`)**: `--dispatch-mode` parsed via `parseDispatchModeFlag`, default `defaultDispatchMode()`. `main()` calls `assertDispatchModeLive(mctsSearch, mode)` after the `--resume` replay and before `setupHarnessEngines`, exiting with the error's `exitCode` (continuous exits 3 today until Plan 227-10). `playGame` takes `dispatchMode` and spreads it into the bot `SearchBudget`; `playCellAnchorGames` forwards `args.dispatchMode`. `setupHarnessEngines` passes `maiaFifo: true` (D-14, Pitfall 4).
- **Ledger**: `dispatch_mode` appended last to `RAW_LEDGER_COLUMNS` (22 columns), written by `ledgerRowLine`, parsed by `parsePriorLedgerRow`. `applyPriorLedgerRows` throws `--resume: dispatch_mode mismatch ...` for any prior row whose mode differs from the active one. A 21-column (pre-227) ledger is refused by the header check with a message naming the missing `dispatch_mode` column.
- **Supervisor (`bin/preset-supervisor.sh`)**: `PRESET_SUPERVISOR_DISPATCH_MODE` read next to SEED and passed as `--dispatch-mode` inside `launch()` (cold start and every crash-resume). Header documents an A1 example.
- **Schema check**: pinned 22-column contract, mode round trip (round and continuous), invalid-mode write refusal, pre-227 refusal, and scenario (e): CLI `--resume` with `--dispatch-mode continuous` against a round ledger exits non-zero with the mismatch message.
- **Determinism check**: `dispatchMode: 'round'` on every bot budget and `playGame` call (7 sites), a ROUND-MODE PIN comment citing D-11 and 226 D-05/D-07, and the parity assertion printing `PASS: dispatch parity — harness default mode equals FLAWCHESS_DISPATCH_MODE`.

## Task Commits

1. Task 1 (tracer): `452aadc8d` (`feat(227-05)`)
2. Task 2: `26a6f6ac1` (`test(227-05)`)

Tracer gate: Task 1 `<verify>` commands were all run end to end before expansion (schema check, syntax checks, Python reader tests).

## Verification Results

- `calibration-ledger-schema.check.mjs`: all scenarios PASS (column contract 22, round trips, pre-D-08 and pre-227 refusals, anchor guard, mode-mismatch guard, writer smoke).
- `bash -n bin/preset-supervisor.sh`, `node --check scripts/calibration-harness.mjs`, `grep PRESET_SUPERVISOR_DISPATCH_MODE`: PASS.
- `uv run pytest tests/scripts/test_calibration_anchor_fit.py tests/scripts/test_engine_throughput_226_calibration.py -q`: 27 passed (extra column tolerated).
- `calibration-determinism.check.mjs` default run: exit 0, both `PASS: dispatch parity` and `PASS: calibration determinism` lines (30-ply blend=1 game identical). Well inside the 10-minute cap.
- `--no-clear-hash --games 1`: `WARM-ARM SUMMARY games=1 plies_compared=15 plies_differing=0` (positive ply count). An earlier run with a bad out-dir (unset `$TMPDIR`) printed `plies_compared=8` before failing on the mkdir only; rerun with `mktemp -d` passed.
- Neighbouring checks that import the harness: `calibration-persona-cell-schedule`, `calibration-pruning`, `calibration-near-free-metrics`, `dispatch-mode` (round -> round): all PASS. Manual probe: `--dispatch-mode continuous` without `--resume` exits 3 with `CONTINUOUS-NOT-IMPLEMENTED` before any engine starts.
- Acceptance greps: `'dispatch_mode'` is the last `RAW_LEDGER_COLUMNS` entry; `maiaFifo: true` sits inside `setupHarnessEngines`; `grep -c "dispatchMode: 'round'"` in the determinism check = 7 (>= 2).

## Mutation Check (T-227-09)

Disabled the resume refusal (`if (false && row.dispatchMode !== args.dispatchMode)`): scenario (e) failed (`expected /dispatch_mode mismatch/` against the CLI stderr), so the guard is genuinely exercised. Reverted; check passes again.

## Deviations from Plan

None - plan executed exactly as written. Two small additions inside the planned scope: a 21-column pre-227 refusal scenario in the schema check (the plan asked the header-check message to "stay loud"), and `ledgerRowLine` validating the mode so a missing value can never be written. The existing null-`meanMoveMs` schema assertion (which assumed that column was last) was updated to match the new column order.

## Known Stubs

None.

## Threat Flags

None. No new network, auth, or trust-boundary surface; no packages installed (`npm ci` / `uv sync` only restored lockfile state in the worktree).

## Notes for downstream plans

- Plan 227-10 flips the probe so `--dispatch-mode continuous` passes `assertDispatchModeLive`; nothing in this plan needs to change.
- Sweeps for D-15 (Plan 227-11): launch with `PRESET_SUPERVISOR_DISPATCH_MODE=round` (A0) and `=continuous` (A1) under `bin/preset-supervisor.sh`. Any existing 21-column ledger can no longer be resumed (all prior sweeps are complete).

## Self-Check: PASSED

- Modified files exist (`scripts/calibration-harness.mjs`, `scripts/lib/calibration-ledger-schema.check.mjs`, `scripts/lib/calibration-determinism.check.mjs`, `bin/preset-supervisor.sh`).
- Commits `452aadc8d` and `26a6f6ac1` exist on the worktree branch.
