---
phase: "261"
slug: "blunder-check-exploration-arm"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-11-22"
---

# Phase 261 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: `261-RESEARCH.md` § Validation Architecture. This phase has no REQ-IDs; the contract is the
> CONTEXT.md decisions (D-01 to D-12 and the "Carried forward from the seed" list).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (pytest-asyncio, xdist) for the backend; vitest for the frontend |
| **Config file** | `pyproject.toml`, `tests/conftest.py`; `frontend/vite.config.*` |
| **Quick run command** | `uv run pytest tests/services/test_blunder_check_rules.py tests/services/test_blunder_check_candidates.py tests/services/test_blunder_check_selection.py -x` |
| **Full suite command** | `uv run pytest -n auto -x` and `( cd frontend && npm run lint && npm run build && npm test -- --run && npm run knip )` |
| **Estimated runtime** | quick about 60 seconds; full suite several minutes |

---

## Sampling Rate

- **After every task commit:** Run the quick run command plus the touched test file
- **After every plan wave:** Run `uv run pytest -n auto -x` and the frontend block
- **Before `/gsd-verify-work`:** The full pre-merge gate from `CLAUDE.md` must be green
- **Max feedback latency:** about 60 seconds for the quick run

---

## Per-Task Verification Map

Task IDs are assigned by the planner; the rows below are keyed by decision until the plans exist.

| Decision | Behavior | Threat Ref | Test Type | Automated Command | File Exists | Status |
|----------|----------|------------|-----------|-------------------|-------------|--------|
| Share (seed) | Seeded `draw_slot_plan`: exploration share among blunder slots equals the share constant within 0.02 (n = 30000 draws); herring slots are never exploration; own and foreign both about 20% | — | unit | `uv run pytest tests/services/test_blunder_check_rules.py -k slot` | ✅ extend | ⬜ pending |
| Draw (seed) | A forced exploration slot serves a below-cut scored blunder; a forced main slot never does; an unscored blunder is served by neither | — | integration (DB) | `uv run pytest tests/services/test_blunder_check_selection.py -k exploration` | ❌ W0 | ⬜ pending |
| Draw (seed) | An exploration slot never fills from a batch loaded by the cut probe | — | unit | same file | ❌ W0 | ⬜ pending |
| Draw (seed) | The arm survives the own-to-foreign conversion, the shape redraw and the foreign-to-own refill | — | integration | same file | ❌ W0 | ⬜ pending |
| Draw (seed) | The probe without the cut returns games with only below-cut scored blunders, and still excludes served, opponent-side and unscored rows | — | integration | `uv run pytest tests/repositories/test_blunder_check_repository.py -k scored` | ❌ W0 | ⬜ pending |
| Main arm 0.70 | Existing cut tests unchanged and green | — | regression | `uv run pytest tests/repositories/test_blunder_check_repository.py tests/services/test_blunder_check_candidates.py` | ✅ | ⬜ pending |
| Counts as normal | An exploration window's points enter session points and the leaderboard | — | integration | `uv run pytest tests/routers/test_blunder_check_drill.py tests/services/test_train_leaderboard.py` | ✅ extend | ⬜ pending |
| Snapshot | A composed window carries the arm, the sampling probability, the score equal to the loader score and the five inputs; a herring carries none | — | integration | selection tests | ❌ W0 | ⬜ pending |
| Migration | Upgrade and downgrade run; the CHECKs reject a herring with an arm and an arm without a score | — | integration | `uv run alembic upgrade head` plus a repository test expecting `IntegrityError` | ❌ W0 | ⬜ pending |
| D-08 | Fixture 13 gives swing 0 and no line; fixture 154 gives a line; a short line uses the deepest settled depth | — | unit | `uv run pytest tests/services/test_blunder_check_feedback.py` | ❌ W0 | ⬜ pending |
| D-09 | A played line mating the blunderer gives the allowed-mate line; a best line mating gives the missed-mate line; mate beats material | — | unit | same file | ❌ W0 | ⬜ pending |
| D-12 | `best_move` only (no pv), not mating, gives no "misses" line | — | unit | same file | ❌ W0 | ⬜ pending |
| D-06 / D-07 | Score 0.4999 is hard to catch, 0.5 is not; the copy differs for caught and missed | — | unit (backend and vitest) | same file plus `npm test -- blunderCheckSolution` | ❌ W0 | ⬜ pending |
| D-04 | A window with a snapshot has `feedback`; a legacy window has none | — | router | `uv run pytest tests/routers/test_blunder_check_solution.py` | ✅ extend | ⬜ pending |
| D-05 | A false-alarm solution has no feedback, also for a low-score window | — | router | same file | ✅ extend | ⬜ pending |
| D-01 / D-02 | The drill chip shows the snapshotted percentage; its popover names no type and says neither "your" nor "their" | — | component | `npm test -- BlunderCheckSolution` | ✅ extend | ⬜ pending |
| D-03 | The second paragraph follows the verdict sentence in the card and in the strip | — | component | same | ✅ extend | ⬜ pending |
| Calibration script | Pure aggregation: bands, Wilson bounds, reached windows as the denominator, false alarms beside it, legacy fallback | — | unit | `uv run pytest tests/scripts/` (the script's test file) | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/services/test_blunder_check_feedback.py` — D-06 to D-09, D-12 (reuses `tests/services/line_material_fixtures.py`)
- [ ] A test file under `tests/scripts/` for the calibration script
- [ ] Seed helper: `seed_judged_game` cannot set `pv` today; an optional per-ply pv map is needed if a DB-level
      type-line test is wanted

---

## Manual-Only Verifications

| Behavior | Decision | Why Manual | Test Instructions |
|----------|----------|------------|-------------------|
| The foreign and nearest-foreign picks without the cut stay cheap on prod | D-10 | Needs the prod data volume; run by the orchestrator, read-only | `EXPLAIN (ANALYZE, BUFFERS)` of both picks on prod before release |
| Served exploration share on prod | Share acceptance | Needs real sessions after release | Count served exploration windows over ended blunder windows about a week after release, against the planner's tolerance |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s for the quick run
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
