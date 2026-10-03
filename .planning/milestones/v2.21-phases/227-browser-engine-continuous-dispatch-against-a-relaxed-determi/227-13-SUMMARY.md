---
phase: 227-browser-engine-continuous-dispatch-against-a-relaxed-determi
plan: 13
subsystem: engine
tags: [ship, continuous-dispatch, smoke, docs, dev-tool-removal]

requires:
  - phase: 227-12
    provides: "owner decision ship; verdict ship-eligible, no-refit"
provides:
  - "FLAWCHESS_DISPATCH_MODE = 'continuous' (one-line flip, rollback by flipping back)"
  - "227-UAT.md: smoke pass, real-phone deferred"
  - "Dev engine bench removed; CHANGELOG and engine doc describe continuous dispatch; final report"
affects: []

plan_head_before: 80d1fe84f
plan_head_after: 58196b019

actuals:
  tasks: 3
  commits: 4

requirements-completed: []

coverage:
  - id: D1
    description: "Flag matches the ship decision; no refit (refit_if_shipped no-refit); regeneration leaves no drift"
    verification:
      - kind: other
        ref: "Task 1 verify (decision ship, refit no-refit, 0 refit commits; gen_bot_strength_curves + gen_persona_calibration, git diff clean)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Shipped engine smoke-tested in the dev build"
    verification:
      - kind: e2e
        ref: "227-UAT.md smoke: pass (analysis board 400 nodes + 7-move bot game, console clean, mode continuous)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Dev tool removed, docs updated, pre-merge gate green"
    verification:
      - kind: other
        ref: "no frontend/src/dev/engineBench, no route, no engine-bench-227 in dist; full CLAUDE.md pre-merge gate exit 0"
        status: pass
    human_judgment: false
---

# 227-13 SUMMARY: ship continuous dispatch

## Commits

| Commit | What |
|---|---|
| `e9fc9a079` | `feat(227): ship continuous dispatch (FLAWCHESS_DISPATCH_MODE = 'continuous', D-13)`, one file (`botBudget.ts`: the constant and its doc comment) |
| `a56865ece` | `test(227-13): smoke of shipped continuous dispatch; real-phone deferred` (plus a one-word typo fix commit) |
| `58196b019` | `docs(227-13): remove dev engine bench, changelog and engine doc for continuous dispatch, final report` |

## Task 1: decision executed

Decision **ship**, `refit_if_shipped` **no-refit**: flipped the constant only, no refit. After the flip:
`npx vitest run src/lib/engine` 34 files / 777 tests pass, `npm run build` exit 0, `dispatch-mode.check.mjs --mode
round` prints `DISPATCH-PROBE round -> round` and `--mode continuous` prints `DISPATCH-PROBE continuous -> continuous`
(both exit 0). Regenerating curves and persona labels leaves no diff.

## Task 2: smoke

Dev build, page-side `FLAWCHESS_DISPATCH_MODE` read as `continuous`.
- Analysis board (middlegame FEN, 400 nodes): ranked lines Ng5 +1.1 and h3 +0.6 rendered. Console check with filter
  `error|Error|unhandled|rejection|warn`: "No console errors or exceptions found".
- Bot game vs Tank the Ox (~1500): `1. e4 e5 2. Nc3 Nf6 3. Bc4 Bc5 4. d3 d6 5. a3 O-O 6. Na4 Bb6 7. Nf3`, replies
  prompt. Console check with filter `error|Error|unhandled|rejection|Uncaught`: "No console messages found".
- Real phone: deferred to the owner (report-only).

## Task 3: tool removal, docs, gate

- Removed `frontend/src/dev/engineBench/` (7 files incl. tests) and the DEV-gated lazy import and route in `App.tsx`;
  `frontend/src/dev` is gone. knip clean; `dist` contains neither `engine-bench-227` nor `EngineBench`.
- CHANGELOG `[Unreleased]` / Changed: bot moves about 19% faster again, analysis search about 14% faster, Maia and
  Stockfish kept busy at the same time; notes the loss of move-for-move reproducibility.
- Engine doc §4 "Several expansions at once" rewritten for continuous dispatch (in flight, arrival order, no pending
  re-pick, the Phase 226 fill fix kept, stop cancels everything, reproducibility given up at more than one worker); the
  §4 ranking sentence no longer claims perfect reproducibility.
- report.md: Outcome, Refit, Smoke test and device UAT, Dev tool sections; no pending markers.
- Pre-merge gate: ruff format (no changes), ruff check, ty (app/tests/scripts and analysis), nesting-depth gate (1077
  functions, no breaches), `pytest -n auto -x` 4982 passed / 19 skipped, frontend lint, build, 281 files / 4550 tests,
  knip: all exit 0.

## Deviations from Plan

1. **Task 1 verify script.** It reads `verdict.json['refit_if_shipped']['decision']`, but the twin writes
   `refit_if_shipped` as a plain string (`"no-refit"`). Ran the same check reading the string; the plan file was
   not edited.
2. **CHANGELOG wording** says "about 19% faster again" because the existing Phase 226 bullet already claims 18% for bot
   moves.

## Self-Check: PASSED

- Task 1 verify (string-adapted) and regen drift check pass.
- Task 2 verify: `smoke: pass` and `real-phone: deferred` lines present; UAT tracked.
- Task 3 verify: tool gone, route gone, build passes, no marker in dist; changelog bullet present on ship; report has
  "## Refit" and no pending marker; full pre-merge gate exit 0.
