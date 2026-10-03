---
phase: 227-browser-engine-continuous-dispatch-against-a-relaxed-determi
plan: 12
subsystem: engine
tags: [gate, verdict, webgpu, owner-decision, continuous-dispatch]

requires:
  - phase: 227-11
    provides: "complete MQ, throughput and calibration gate data"
provides:
  - "Owner WebGPU interleaved leg (judged D-07 input) and the local wasm interleaved leg (report-only)"
  - "reports/continuous-dispatch-227/verdict.json (ship-eligible, no-refit, virtual-loss trigger false)"
  - "reports/continuous-dispatch-227/report.md and owner-decision.md (ship)"
affects: [227-13]

plan_head_before: d04facd2f
plan_head_after: b8304facc

actuals:
  tasks: 3
  commits: 4

requirements-completed: []

coverage:
  - id: D1
    description: "Owner WebGPU leg committed and valid; local wasm leg committed"
    verification:
      - kind: other
        ref: "uv run python scripts/engine_dispatch_227_verdict.py webgpu --json reports/data/continuous-dispatch-227/webgpu/continuous-leg.json (exit 0, median 0.676, pass)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Mechanical verdict rendered from committed data and reported"
    verification:
      - kind: other
        ref: "gates rerun into a temp file reproduces verdict.json byte-for-byte (sorted JSON); mechanical ship-eligible"
        status: pass
    human_judgment: false
  - id: D3
    description: "Owner decision recorded with basis; accept rule unedited"
    verification:
      - kind: other
        ref: "owner-decision.md **Decision:** ship; accept-rule.md has exactly one commit"
        status: pass
    human_judgment: true
---

# 227-12 SUMMARY: verdict, report, owner decision

## Commits

| Commit | What |
|---|---|
| `cd7b17672` | `chore(227-12): owner WebGPU interleaved bot-move leg (D-07)` (landed during the 227-11 calibration sweep) |
| `bfa50f7c0` | `chore(227-12): local wasm interleaved bot-move leg (D-06, report-only)` |
| `e8f263951` | `docs(227-12): gate verdict and report` |
| `b8304facc` | `docs(227-12): owner decision (ship)` |

The plan's single `chore(227-12): WebGPU and local interleaved bot-move legs` commit became two, because the owner's
leg arrived hours before the box was free for the local leg.

## Task 1: WebGPU legs

Owner leg (Edge 154 / Windows, 32 threads, pool 4, shader-f16, served over the tailnet): per-round ratios 0.6112,
0.8416, 0.6761; **median 0.6761, D-07 pass** (bar 1.03). Maia latency per backend, median / p90 ms: webgpu idle
17.1 / 19.5, webgpu Stockfish-busy 23.4 / 26.5, wasm idle 25.0 / 26.7, wasm Stockfish-busy 27.9 / 30.4.
Report-only: 69.3 ms per node round vs 55.3 ms per node continuous (about 20 percent per node; the rest of the wall
gain is earlier stop-rule stops).

Local wasm leg (Linux Chrome 154, no WebGPU adapter): 36 rows, every mode observed, ratios 0.724 / 0.600 / 0.637.
The tab was hidden for the whole run (`visibilityState` hidden; the round-2 dispatch probe stalled until a screenshot
activated the tab), so its timings are background-throttled. Rows 19-36 carry `wallMs` rounded to 0.001 ms because the
page JSON had to be extracted in chunks. Both caveats are in the commit message and the report.

## Task 2: verdict and report

`gates` exit 0, status complete: **mechanical `ship-eligible`, `refit_if_shipped` `no-refit`, `virtual_loss_trigger`
false** (no trace run, `gate/trace/` intentionally absent). Spot-checks, report vs verdict.json:
stop-off D -0.00452 (verdict `decision_d` -0.00451638), `t400-p4` ratio 0.8582 (`geometric_mean` 0.858244), Maia pooled
shift +33.1 +- 28.1 (`pooled_shift` 33.111, `pooled_se` 28.126). All match.

## Task 3: owner decision

The owner chose **ship** on 2026-10-03, following the mechanical outcome in full. No override document. The accept
rule has exactly one commit.

## Deviations from Plan

1. Two commits for the two WebGPU legs instead of one (timing, see above).
2. The local wasm leg ran in a hidden tab; report-only either way, flagged.

## Self-Check: PASSED

- Task 1 verify: twin `webgpu` exit 0 on the owner leg; both JSONs tracked.
- Task 2 verify: `gates` into a temp file exits 0 and reproduces verdict.json; mechanical/refit/trigger fields present;
  report has the D-07 section; both files tracked.
- Task 3 verify: `**Decision:** ship` line present; owner-decision.md tracked; accept rule unchanged.
