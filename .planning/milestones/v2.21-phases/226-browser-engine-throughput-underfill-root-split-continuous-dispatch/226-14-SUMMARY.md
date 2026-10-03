---
phase: 226-browser-engine-throughput-underfill-root-split-continuous-dispatch
plan: 14
subsystem: engine
tags: [refit, uat, pre-merge-gate]

requires:
  - phase: 226-13
    provides: "verdict.json (all items hold, no-refit), arm reverts, report.md"
provides:
  - "Refit: skipped, decision no-refit; regenerated curves/labels show no drift"
  - "226-UAT.md: smoke skipped (frontend identical to main), real-phone owner-deferred"
  - "report.md final: Refit and Smoke test sections, no pending markers"
  - "Full CLAUDE.md pre-merge gate green on the phase branch"
affects: []

actuals:
  tasks: 3
  commits: 1

key-files:
  created:
    - .planning/phases/226-browser-engine-throughput-underfill-root-split-continuous-dispatch/226-UAT.md
  modified:
    - reports/engine-throughput-226/report.md

key-decisions:
  - "No refit, per verdict.json (no-refit). Nothing launched."
  - "Smoke test recorded as skipped, not passed. The branch's frontend is byte-identical to main after the 226-13 reverts, so a dev-build smoke would only re-test production code. It reopens if the owner overrides toward shipping."
---

# Phase 226 Plan 14: Refit Decision, UAT, Pre-merge Gate Summary

## Task 1: Refit

`verdict.json` refit = `no-refit` ("no shipped item shows a real (powered) shift"), so no
refit was run. The verify passes. No `(226-14): refit` commit exists, and running
`gen_bot_strength_curves.py` and `gen_persona_calibration.py` leaves no diff in
`frontend/src/generated` or `reports/data/bot-strength-lookup.json`.

## Task 2: Smoke test and device UAT

- **smoke: skipped.** `git diff $(git merge-base main HEAD) HEAD -- frontend/` is empty after
  the 226-13 reverts, so the dev build is main's frontend.
- The browser leg was attempted. After a host reboot the Claude-in-Chrome extension registered no
  connected browser, even with Chrome started. It was not pursued further.
- Engine tests (670) and the full frontend gate pass.
- **real-phone:** deferred, owner device, report-only (D-04).

## Task 3: Report and pre-merge gate

- report.md gained "## Refit" and "## Smoke test and device UAT" and has no pending marker.
- No CHANGELOG bullet: no refit, and nothing ships.

Pre-merge gate, all exit 0:

| Step | Result |
|---|---|
| `ruff format` | no changes |
| `ruff check --fix` | no changes |
| `ty check app/ tests/ scripts/` | clean |
| `ty check analysis/` | clean |
| `check_function_size.py app/ --fail-over-depth 4` | pass |
| `pytest -n auto -x` | 4853 passed, 19 skipped |
| `npm run lint` | pass |
| `npm run build` | pass |
| `npm test -- --run` | 278 files, 4440 tests passed |
| `npm run knip` | pass |

The formatters produced no diff, so there is no style commit.

## Deviations from Plan

1. **[Verify literal] Task 2's verify expects `^smoke: pass`.** The UAT records
   `smoke: skipped (no shipped item; frontend identical to main)` instead, because claiming a pass
   for an unrun test would be false. The plan assumed something would ship. With nothing shipped,
   the smoke has no object. This is listed for the owner in 226-UAT.md, and the item reopens on an
   override.
2. **[Environment] Browser extension unavailable after reboot.** See Task 2.

## Self-Check: PASSED (with the smoke deviation above)

## Addendum (2026-10-02): owner override shipped all three items

- The owner ratified the three overrides and overrode the hold
  (`reports/engine-throughput-226/override-2026-10-02-owner-ship-decision.md`).
- Underfill and guard were re-applied in `9d0327b91`, and the root split in `0db58d765` after an
  interleaved re-test: bot move wall 0.82x of A21; t400-p2 A2/A0 raw 0.879, normalized 0.998.
- `frontend/src` equals A21S.
- **Refit:** still no-refit. The D-11 rule over the now-shipped set uses each item's powered
  verdict, and all three are valid with no real shift (report.md criterion 15).
- **Smoke:** pass on the shipped build (analysis 400-node search, 9-move bot game vs a ~1600
  searching persona, no console errors). Task 2's verify `^smoke: pass` now holds; see 226-UAT.md.
- **Pre-merge gate:** re-run on the shipped branch, all green: ruff, ty (app + analysis), function size, pytest 4853 passed, frontend lint, build, 280 files / 4471 tests passed, knip.
