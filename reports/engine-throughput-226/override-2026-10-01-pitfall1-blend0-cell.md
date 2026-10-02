# Accept-rule override: Pitfall-1 root-split log check, blend-0 cell

**Date:** 2026-10-01
**Decided by:** Orchestrator-authored under the owner's autonomy instruction (Plan 226-12 Task 3,
step 3); **pending owner ratification.**
**Scope:** Plan 226-12 Task 3 step 3 ("each A21S cell's run.log has a `root-split:` line with
splits > 0 ... a violation: STOP"), as it applies to the one blend-0 runbook cell,
`a21s-human1100`. Every other A21S cell, and every A2/A21 cell, is checked literally.
**Rule file:** NOT edited.
**Revert target:** treat this override as void and re-open the Pitfall-1 check for the owner. No
data is discarded: the human1100 cell is identical in mechanism across A21 and A21S (see below).

---

## What happened

The Pitfall-1 log check over the finished calibration cells:

| Cell | `root-split:` line |
|------|--------------------|
| a2-*, a21-* (all 10) | `calls=0 splits=0` (expected: no split at A2/A21) |
| a21s-light1300 | `calls=2718 splits=2472 premise_violations=0` |
| a21s-light1900 | `calls=2394 splits=2118 premise_violations=0` |
| a21s-deep2300 | `calls=1108 splits=970 premise_violations=0` |
| a21s-deep1500 | checked in the 226-12 SUMMARY once the cell finishes |
| **a21s-human1100** | **`calls=0 splits=0 premise_violations=0`** |

## Why the human1100 line is not an unsplit-arm measurement

- human1100 runs `preset-supervisor.sh <arm>-human1100 0 1100`, i.e. **blend = 0**.
- `frontend/src/lib/engine/selectBotMove.ts:128` (`if (blend <= 0)`): the full-human regime makes
  exactly one `deps.policy()` call and samples from the Maia prior. There is no search, so
  `providers.gradeRoot` is never reached at any arm. `calls=0` (not merely `splits=0`) shows the
  code path was never entered. This is not a split that was attempted and declined.
- The cell's non-zero `bot_eval_count` is the harness's own cp-loss scoring through `pool.grade`,
  which is not the root-split path.
- Pitfall 1 (226-RESEARCH.md) guards against "calibration measures a bot that doesn't ship". The
  three searched A21S cells already prove the A21S harness routes root grades through the split
  (thousands of splits each). The human1100 bot is the same bot at A21 and A21S by construction.
- The design already relies on this: `calibration_parity_verdict.py` reports the blend-0 cell as
  `null_control`, separate from the four `exposed_cells`. A null control that engaged the split
  would no longer be a null control.

## Consequence

The literal STOP is not taken. The human1100 cell stays in `a21s-cells.json` and in
`verdict-a21s-vs-a21.json` unchanged, as the runbook's five-cell set requires. Its expected
contribution to the A21S-vs-A21 shift is noise around zero.
