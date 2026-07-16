---
phase: 173
slug: anchor-ladder-self-calibration-seed-101
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-15
---

# Phase 173 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> No `REQUIREMENTS.md` entries map to this phase (SEED-101 backlog work); the
> CONTEXT.md decisions D-01…D-13 are the phase's requirements and are mapped below.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework (Node side)** | Node built-in `node:assert/strict`, run as standalone `.check.mjs` scripts (existing project convention — NOT vitest; no browser/DOM harness needed) |
| **Framework (Python side)** | pytest (existing convention; `tests/scripts/test_backfill_eval.py` is the precedent for testing a `scripts/*.py` file) |
| **Config file** | none for `.check.mjs` (run via `node --import ./scripts/lib/frontend-alias-hook.mjs <file>`); pytest config in `pyproject.toml` |
| **Quick run command** | `node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/calibration-game-loop.check.mjs` (Node piece) / `uv run pytest tests/scripts/test_calibration_anchor_fit.py` (Python piece) |
| **Full suite command** | `uv run pytest -n auto` (backend, includes the new fit test) + run each new `.check.mjs` once (`calibration-anchors` / `calibration-game-loop` / `calibration-anchor-schedule`) — these are developer-invoked, not wired into npm/CI |
| **Estimated runtime** | Unit checks ~seconds each; the real D-11 anchor-vs-anchor sweep (Plan 04) is multi-hour and manual-only |

---

## Sampling Rate

- **After every task commit:** Run the relevant `.check.mjs` / `pytest -k <keyword>` for the piece just built. The real multi-hour engine run is NOT part of this cadence.
- **After every plan wave:** Run `uv run pytest -n auto` + all new `.check.mjs` files once.
- **Before `/gsd-verify-work`:** Full suite green (all `.check.mjs` + `test_calibration_anchor_fit.py`).
- **Max feedback latency:** ~30 seconds for unit checks (the D-11 sweep is a distinct, separately-tracked deliverable, not a feedback loop).

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 173-01-01 | 01 | 1 | D-09 | T-173-01 / — | `parseAnchorSpec('sf8')`/`('sf10')` no longer throw; sf8/sf10 are folklore labels/ordering-only, never a fit input | unit | `node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/calibration-anchors.check.mjs` | ❌ W0 (new check) | ⬜ pending |
| 173-01-02 | 01 | 1 | D-08, D-10 | T-173-01 | Extracted game loop is byte-identical to the pre-extraction bot harness (no behavior change) | integration | `node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/calibration-game-loop.check.mjs && … calibration-pruning.check.mjs && … calibration-determinism.check.mjs` | ✅ (determinism/pruning pre-exist) · ❌ W0 (game-loop check new) | ⬜ pending |
| 173-02-01 | 02 | 2 | D-01, D-02, D-04 | T-173-06 | Connectivity guard rejects a disconnected / under-cross-linked graph; probe-band gate keeps [0.2,0.8] | unit | `node --import ./scripts/lib/frontend-alias-hook.mjs scripts/lib/calibration-anchor-schedule.check.mjs` | ❌ W0 (new check) | ⬜ pending |
| 173-02-02 | 02 | 2 | D-03, D-08, D-10, D-13 | T-173-07 / T-173-08 | Fail-loud CLI + pair-keyed `--resume`; durable one-row-per-game TSV; D-13 caveat in pairs footer | unit (syntax + side-effect-free import) | `node --check scripts/calibration-anchor-ladder.mjs && node --import ./scripts/lib/frontend-alias-hook.mjs -e "import('./scripts/calibration-anchor-ladder.mjs').then(()=>console.log('IMPORT-OK'))"` | ❌ W0 (new script) | ⬜ pending |
| 173-03-01 | 03 | 1 | D-04, D-05, D-06 | T-173-03 / T-173-04 / T-173-05 | RED: fit tests fail (ModuleNotFound) before implementation exists | unit (TDD RED) | `uv run pytest tests/scripts/test_calibration_anchor_fit.py 2>&1 \| grep -Eq 'ModuleNotFoundError\|ImportError\|No module named' && echo RED-OK` | ❌ W0 (new file) | ⬜ pending |
| 173-03-02 | 03 | 1 | D-04, D-05, D-06, D-07 | T-173-03 / T-173-04 / T-173-05 | GREEN: fit converges to known ground truth, `maia1500==1500` pinned, draws fold 0.5/0.5, bootstrap CI finite, residuals flagged cross-family | unit (TDD GREEN) | `uv run pytest tests/scripts/test_calibration_anchor_fit.py -x` | ✅ after 173-03-01 | ⬜ pending |
| 173-04-01 | 04 | 3 | D-11 | T-173-09 | Real sweep runs only after all unit checks green; reports connectivity-OK (≥2 cross-family links); ledger non-truncated | manual (multi-hour) | see Manual-Only Verifications | N/A (produced by the run) | ⬜ pending |
| 173-04-02 | 04 | 3 | D-12, D-13 | T-173-10 | `INTERNAL_RATING.maia1500===1500`, all 10 anchors numeric, D-13 "NOT human ELO" caveat present | unit (import assertion) | `node --import ./scripts/lib/frontend-alias-hook.mjs -e "import('./scripts/lib/calibration-internal-scale.mjs').then(m=>{const r=m.INTERNAL_RATING; if(r.maia1500!==1500) throw new Error('scale not pinned'); if(Object.keys(r).length<10) throw new Error('missing anchors'); console.log('SCALE-OK', JSON.stringify(r));})"` | ❌ (produced by 173-04-01 run) | ⬜ pending |
| 173-04-03 | 04 | 3 | D-12 | T-173-10 | Findings note states compression verdict, carries D-13 caveat, closes 168-RESEARCH OQ2 | grep gate | `test -f .planning/notes/2026-07-15-anchor-ladder-self-calibration-findings.md && grep -qi "compress" … && grep -qi "NOT human ELO" … && grep -qi "Open Question 2" … && echo NOTE-OK` | ❌ (produced by 173-04-02) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

The test scaffolds are created inside the first task of each plan (checks live beside the
code they verify; the fit test suite is written RED-first). No separate pre-wave exists,
but these files MUST exist before their sibling implementation is accepted:

- [ ] `tests/scripts/test_calibration_anchor_fit.py` — RED-first suite covering D-04/D-05/D-06, including a **synthetic ground-truth fixture** (known anchor strengths + hand-computable expected fit) so the convergence test has a real correctness oracle (Plan 173-03 Task 1).
- [ ] `scripts/lib/calibration-anchors.check.mjs` — sf8/sf10 parse check, D-09 (Plan 173-01 Task 1).
- [ ] `scripts/lib/calibration-game-loop.check.mjs` — structural check for the extracted mover-agnostic loop, mirroring `calibration-pruning.check.mjs` (Plan 173-01 Task 2).
- [ ] `scripts/lib/calibration-anchor-schedule.check.mjs` — probe/measure band gate + connectivity guard as pure logic, D-01/D-02/D-04 (Plan 173-02 Task 1).

Pre-existing infrastructure reused unchanged: `calibration-determinism.check.mjs` and
`calibration-pruning.check.mjs` (the D-08 no-behavior-change gate for the loop extraction).

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| The real anchor-vs-anchor sweep produces the raw + pairs TSV | D-11 | Multi-hour engine run (no MCTS → hours, not days), CPU-bound, launched by Adrian on his own machine; resumable via `--resume`. Not a fast feedback loop. | 1. Confirm all Plan 01/02/03 unit checks green. 2. `node --import ./scripts/lib/frontend-alias-hook.mjs scripts/calibration-anchor-ladder.mjs --stockfish-procs 12` (resume with `--resume reports/data/anchor-ladder-<ts>.tsv`, same seed, if interrupted). 3. Confirm `anchor-ladder-<ts>.tsv` + `-pairs.tsv` exist, last raw line ends in a newline (not truncated), and a connectivity-OK line (≥2 cross-family links) printed. Report the `<ts>` filename for the fit task. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies (173-04-01 is the sole manual D-11 deliverable, gated on all unit checks green first)
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (4 new check/test files above)
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s for unit checks
- [ ] `nyquist_compliant: true` set in frontmatter (set by validate-phase §6)

**Approval:** pending
