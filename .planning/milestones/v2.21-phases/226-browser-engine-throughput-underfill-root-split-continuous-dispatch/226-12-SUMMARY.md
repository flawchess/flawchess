---
phase: 226-browser-engine-throughput-underfill-root-split-continuous-dispatch
plan: 12
subsystem: engine
tags: [gate, calibration, move-quality, throughput, root-split, orchestrator-run]

requires:
  - phase: 226-11
    provides: "Arm A21S (f6c1f7a54); arms A0 3fe340ce9, A2 756d2a4a1, A21 29f543f27"
provides:
  - "Every gate number the accept rule needs, committed under reports/data/engine-throughput-226/gate/ (throughput, stop rule, MQ off/on + rerun, warm arm, A21S content clear/warm, determinism, calibration cells and verdicts for A2/A21/A21S)"
  - "gates: STATUS complete, exit 0; UNDERFILL hold (t400-p2 wall ratio 1.125 > 1.05), GUARD hold and ROOT_SPLIT hold (stacked on underfill; root split also fails Clear-Hash content 0.0209 > 0.0168), REFIT no-refit"
  - "Report-only CPU-normalized throughput analysis (reports/engine-throughput-226/analysis-2026-10-01-cpu-normalized-throughput.md): raw wall drift is per-grade CPU (machine state); normalized, the full stack is ~7-9% faster than A0a except t400-p2 (~1%)"
affects: [226-13, 226-14]

actuals:
  tasks: 3
  commits: 7
  plan_head_before: f6c1f7a5452389d744d61e51f284a026d5cea5f4
  plan_head_after: 6226ca9f3

key-files:
  created:
    - reports/engine-throughput-226/override-2026-09-29-content-tool-single-candidate.md
    - reports/engine-throughput-226/override-2026-10-01-pitfall1-blend0-cell.md
    - reports/engine-throughput-226/analysis-2026-10-01-cpu-normalized-throughput.md
    - reports/data/engine-throughput-226/gate/ (all arms)
    - reports/data/sweep-226-{a2,a21,a21s}-*/calibration-harness-*.tsv (force-added)
  modified:
    - scripts/engine-root-split-content.mjs

key-decisions:
  - "Task 1: lock-and-run. The accept rule was kept exactly as committed before any gate data existed (orchestrator decision under the owner's autonomy instruction, the pre-registration-consistent choice). Revising a bound after the step-0 data would be post-hoc fitting."
  - "Rule over plan prose where they differ: no fresh A0 throughput run (A2 compares to step-0 A0a), each arm fully measured before the next, --pool-size 4 on stop-rule and MQ commands."
  - "A21S calibration cells were fed into freed slots (at most 10 concurrent) instead of waiting for the whole A2+A21 batch."
  - "The blend-0 human1100 cell's root-split calls=0 is recorded as an override, not a Pitfall-1 STOP: blend<=0 makes a single Maia policy call with no search (selectBotMove.ts:128), so gradeRoot is unreachable at every arm, and the cell is the verdict tool's null control."
---

# Phase 226 Plan 12: Gate Runs (Throughput, Stop Rule, MQ, Content, Calibration) Summary

All gate data is measured after the accept-rule lock, committed, and the mechanical verdict is
computable end to end. `gates` exits 0 with STATUS complete. All three items hold and the refit
decision is no-refit.

## Arms

| Arm | SHA | Content |
|---|---|---|
| A0 | 3fe340ce9 | tooling only, baseline (step-0 A0a data) |
| A2 | 756d2a4a1 | + round underfill fix |
| A21 | 29f543f27 | + root comparability guard |
| A21S | f6c1f7a54 | + root grade split |
| A21SC | absent | D-17 not fired (CANDIDATE_CAP_ARM_ACTIVE = False) |

Content assertions (accept rule §1) passed for every arm before any run.

## Task 1: Lock decision

Lock-and-run. The accept rule stayed untouched. Two later deviations are separate dated override
documents (below), never edits to the rule file.

## Task 2: Wall-clock data (dbe4fb49d)

Runs were on an idle box, with the 1-minute load average logged below 2.0 before every step.
The scratchpad load logs are gone, so the commit body of dbe4fb49d is the record. One sequential
driver ran each arm fully before the next.

| Criterion | Result |
|---|---|
| Underfill throughput (A2 vs A0a, ≤ 1.05) | t50-p4 1.038, t400-p4 0.992, t50-p2 0.983, **t400-p2 1.125 (fail)** |
| Guard S1 (A21 max wall ≤ 12,100 ms) | 8,321 ms, pass |
| Guard S2 (early-stop retention) | A21 10 vs A2 10, pass |
| Root-split determinism | PASS |
| Root-split T-50 (A21S/A21 ≤ 0.97) | 0.969, pass |
| Root-split other configs (≤ 1.05) | t400-p4 0.635, t50-p2 0.752, t400-p2 0.950, pass |
| Root-split Clear-Hash content (≤ 0.01680) | **0.02092 (fail)**, argmax flip rate 7.9% |
| Root-split warm content (≤ 0.02521) | 0.01548, pass, argmax flip rate 5.3% |
| Warm arm (report-only) | 0/60 plies differing at A21 and at A21S |

The A21S content tool aborted on a one-candidate root (HEzVd). It was fixed in b79a39538 and
the override is 953d2ad70 (pending owner ratification).

## Task 3: Move quality and calibration

**MQ** (60 positions, paired, allowance 1):
- Underfill (A2 vs A0a, off): cBFTV pass-to-regression. The fresh-process rerun reproduced it
  (the 45c1037e2 body says otherwise; the committed verdict data is authoritative). Net 1, passes.
  cBFTV is the D-13 side-effect position.
- Guard (A21 vs A2, on): net 0, passes.
- Root split (A21S vs A21): off net −1 (cBFTV regression-to-pass), on net −1 (Dj8iG
  regression-to-pass). Both pass, and both are improvements.
- `reruns`: NO RERUNS REQUIRED.

**Calibration** (5 runbook cells, 50 games per (cell, anchor), seed 1, pinned anchors). Pooled
shift ± se:

| Comparison | Maia family | SF family | Null control | Verdict |
|---|---|---|---|---|
| A2 vs A0a | +18.7 ± 27.1 | +12.6 ± 27.2 | within | holds |
| A21 vs A2 | −22.2 ± 27.0 | −46.7 ± 27.1 | within | holds |
| A21S vs A21 | +15.2 ± 27.4 | +30.7 ± 27.2 | within | fails (shape guard at 1500/0.5: Maia +75, SF −102) |

All pooled shifts are within the powered thresholds (Maia 85, SF 53.5). No item ships, so none of
these feeds the refit decision: `gates` reports no-refit.

**Pitfall-1 root-split log check:**
- Every a2/a21 cell: `splits=0`.
- a21s light1300 2472, light1900 2118, deep1500 1167, deep2300 970 splits, all with 0 premise
  violations.
- a21s human1100 `calls=0`: the blend-0 null control (override ef0e8cc6a).

Copy-back: all `sweep-226-{a2,a21,a21s}-*/calibration-harness-*.tsv` are force-added (`git
ls-files`: 30 a2/a21 and 15 a21s files). No gate file existed only in a worktree. All three arm
worktrees were then removed.

## Deviations from Plan

1. **[Tool defect] Content tool single-candidate assertion.** Fixed in b79a39538; override
   953d2ad70.
2. **[Rule literal] Pitfall-1 STOP not taken for the blend-0 cell.** Override ef0e8cc6a, which
   explains why `calls=0` is structural.
3. **[Infra] Host suspend and reboot.** The host suspended for about 40h and then rebooted while
   a21s-deep1500 was at game 162/200. The supervisor was relaunched with the pinned command and
   resumed from the ledger. Calibration is node-capped, so the strength data is unaffected. Only
   the per-game `elapsed_ms` of the games around the suspend is inflated.
4. **[Report-only addition] CPU-normalized throughput analysis** (554b4c0e2). Raw wall ratios
   track per-grade Stockfish CPU, which drifted up to 1.75× between runs of identical work:
   A21 t400-p4 used 228 ms/grade against A2's 139 ms at the same 6,400 grades. The underfill
   t400-p2 fail (1.125) matches a 13% per-grade CPU rise with unchanged pipeline efficiency
   (0.991 normalized). The root split's raw 0.63 at t400-p4 is A21's drift reversing; normalized
   it is ~4% at t50-p4 and ~0 at 400 nodes. The verdict is unchanged. This is input for the
   owner's decision.

## Owner review required

- Ratify or reject: `override-2026-09-29-d13-trace-anomaly.md`,
  `override-2026-09-29-content-tool-single-candidate.md`,
  `override-2026-10-01-pitfall1-blend0-cell.md`.
- The mechanical verdict holds everything, mainly because one throughput config is affected by
  machine drift (see the analysis). Decide whether to keep it or record an override.

## Self-Check: PASSED

`reruns` prints NO RERUNS REQUIRED. `gates` exits 0 on committed data. Every arm's cells and
verdict JSONs are committed. `git worktree list` shows only the main checkout.
