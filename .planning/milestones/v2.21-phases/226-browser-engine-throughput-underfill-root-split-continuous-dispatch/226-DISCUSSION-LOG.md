# Phase 226: Browser Engine Throughput - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-28
**Phase:** 226-browser-engine-throughput-underfill-root-split-continuous-dispatch
**Areas discussed:** Phase split & scope, Determinism contract, Calibration gate & A0 drift

---

## Phase split & scope

| Option | Description | Selected |
|--------|-------------|----------|
| Split: 226 = steps 0-2, 227 = step 3 | Size step 3 on the post-226 idle profile; own design, review, accept rule | ✓ |
| One phase, all steps | One accept rule and calibration pass; long phase ending on the 198 risk | |
| 226 = steps 0-2 only, no 227 yet | Decide later whether continuous dispatch is still worth a phase | |

| Option (WebGPU desktop Maia measurement) | Description | Selected |
|--------|-------------|----------|
| 227 prerequisite | Only sizes continuous dispatch on desktop; root split is SF-bound | ✓ |
| 226, measure-only task | Collect now on another machine | |
| Skip it | Size 227 on wasm Maia only | |

| Option (no-Clear-Hash arm) | Description | Selected |
|--------|-------------|----------|
| 226 | Root split gate must see the shipped warm-hash configuration | ✓ |
| 227 | Only relaxed determinism strictly needs it | |

| Option (mobile measurement) | Description | Selected |
|--------|-------------|----------|
| Node 2-worker pool gates, real phone report-only | Reproducible gate, device as sanity check | ✓ |
| Node 2-worker pool only | No device run | |
| Real phone gates | Faithful but noisy and manual | |

**User's choice:** all recommended options.

---

## Determinism contract

| Option (relaxed property) | Description | Selected |
|--------|-------------|----------|
| Expected score within tolerance | Statistical over a fixture vs round-mode baseline, no MQ regression increase | ✓ |
| Same top move on >= X% of fixture | Noisy on near-ties | |
| Same rankedLines order in top N | Strictest; fails on irrelevant near-ties | |

| Option (tolerance) | Description | Selected |
|--------|-------------|----------|
| Anchored to measured shipped noise floor | k x round-mode-vs-round-mode warm-hash divergence | ✓ |
| Fixed number now | e.g. mean abs delta es <= 0.02 | |

| Option (deterministic path) | Description | Selected |
|--------|-------------|----------|
| Retain round mode behind a budget flag | Bit-identical at any c; A0 arm; rollback by flag | ✓ |
| c=1 only | One runner; c=4 tests become statistical | |

| Option (226 root split bit-identity) | Description | Selected |
|--------|-------------|----------|
| Yes, keep it exact in 226 | Whole pool idle at round 1 in the harness | ✓ |
| No, adopt the relaxed target already | Needs 227's statistical gate in 226 | |

**User's choice:** all recommended options.

---

## Calibration gate & A0 drift

Context presented: Phase 225's `a2-vs-a0` attribution had se 36.3 vs a ±50 threshold (~1.4 se),
so a no-effect change fails one of two families ~30% of the time.

| Option (A0 drift) | Description | Selected |
|--------|-------------|----------|
| Run A0 twice in-session | A0a vs A0b = empirical null; answers drift and sizes thresholds | ✓ |
| Same-session A0 only, no investigation | Cheapest; threshold stays a guess | |
| Investigate the drift as its own task first | Could eat the phase | |

| Option (check power) | Description | Selected |
|--------|-------------|----------|
| Powered: more games per cell | <= ~5% null false-fail from the A0a/A0b null | ✓ |
| Phase 199 check verbatim | ~30% null false-fail | |
| Report-only | Calibration never blocks | |

| Option (on a real shift) | Description | Selected |
|--------|-------------|----------|
| Ship + one refit in 226 | Bug fix; personas were calibrated on the buggy loop; reverses 225 D-14 here | ✓ |
| Hold the item (225 D-14) | No refit | |
| Ship, refit in a separate phase | Labels slightly off until later | |

| Option (arm stacking) | Description | Selected |
|--------|-------------|----------|
| A0 -> A2 -> A21 -> A21S | 225 stacking plus root split | ✓ |
| Combine underfill + guard | One fewer sweep, no split attribution | |
| Fully independent arms off A0 | Cleanest attribution, misses interactions, more sweeps | |

**User's choice:** all recommended options.

---

## Claude's Discretion

- Underfill re-land verdict (area not selected): trace `cBFTV` A0 vs A2 trees first; widen the
  move-quality fixture to >= 50 positions; paired regression-count criterion with an allowance
  from the A0a/A0b flip rate; move quality stays blocking (a refit does not cover it).
- Root split throughput / grade-content bounds fixed in the accept rule from step-0 numbers.
- Non-root candidate cap only if step-0 profiling shows it matters.

## Deferred Ideas

- Continuous dispatch -> Phase 227 (added to ROADMAP.md in this session with user consent).
- Cross-FEN Maia batching: only with WebGPU numbers (227).
