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

Task IDs are `261-PP-TN` (plan PP, task N). Every test file marked "new" is created by the task itself (test first
where the task is `tdd="true"`), so no separate Wave 0 plan is needed.

| Task ID | Wave | Decision | Behavior | Threat Ref | Test Type | Automated Command | File Exists | Status |
|---------|------|----------|----------|------------|-----------|-------------------|-------------|--------|
| 261-01-T1 | 1 | Snapshot (seed), D-04 | A composed blunder window records arm MAIN, P = 0.8, the loader score and its five inputs, and the type facts; a herring records nothing; `alembic check` clean | T-261-01 | integration (DB) | `uv run pytest tests/services/test_blunder_check_selection.py -k "records" -x` | ✅ extend | ⬜ pending |
| 261-01-T2 | 1 | D-06, D-08, D-09, D-12, type side and floor | Fixture 13 swing 0, 154 swing 5, 153 swing 2; short line uses the deepest settled depth; mate on the type side only; best_move-only gives no missed swing; 0.4999 hard, 0.5 not | — | unit | `uv run pytest tests/services/test_blunder_check_feedback.py -x` | ❌ new | ⬜ pending |
| 261-01-T3 | 1 | Migration | CHECKs reject a herring with an arm, an arm without a score, out-of-range values; downgrade / upgrade round-trips | T-261-02 | integration (DB) | `uv run pytest tests/repositories/test_blunder_check_window_snapshot.py -x` and `uv run alembic downgrade -1 && uv run alembic upgrade head && uv run alembic check` | ❌ new | ⬜ pending |
| 261-02-T1 | 1 | D-01, D-02 | Neutral chip renders "Facepalm 43%", neutral tint, popover without type and with "that level" | T-261-04, T-261-05 | component | `npm --prefix frontend test -- src/components/library/__tests__/FacepalmChip.test.tsx` | ❌ new | ⬜ pending |
| 261-02-T2 | 1 | D-02 | Typed library chip unchanged; neutral wording pinned; `facepalm.test.ts` moved from the boolean to the `'opponent'` audience (vitest is the only detector, tsc skips tests); lint, build, full vitest, knip green | T-261-04 | component + unit | `npm --prefix frontend test -- src/lib/__tests__/facepalm.test.ts src/components/library/__tests__/` | ✅ extend | ⬜ pending |
| 261-03-T1 | 2 | Draw, Main arm 0.70 (seed) | A forced exploration slot serves a below-cut scored blunder with an EXPLORATION record; a main slot never does; unscored served by neither; the cut pass of `_fill_from_pool` takes main-arm slots only | T-261-06 | integration (DB) | `uv run pytest tests/services/test_blunder_check_selection.py -k "below_cut or unscored" -x` | ✅ extend | ⬜ pending |
| 261-03-T2 | 2 | Draw (shared-pool trap, plain frame), arm survival | Exploration never draws from a cut batch or through the cut pass (single-option unit tests fail on every run if the guard goes); the scored probe keeps cut-loaded games in its frame; the arm survives conversion, redraw and refill | T-261-08 | unit + integration | `uv run pytest tests/services/test_blunder_check_selection.py -k "cut_batch or keeps_the or next_probe or refill_from_own or exclude_ids" -x` | ✅ extend | ⬜ pending |
| 261-03-T3 | 2 | Share (seed), D-10, D-11 | Seeded share within 0.02 of 0.2 for own and foreign; scored probe keeps below-cut games and still drops served, opponent-side, unscored; no random-arm flakes | T-261-07 | unit + integration | `uv run pytest tests/services/test_blunder_check_rules.py -k "slot or share or named" -x` | ✅ extend | ⬜ pending |
| 261-04-T1 | 2 | D-01, D-03 | Feedback paragraph follows the verdict sentence with chip and lines; every fixture file carries `feedback: null` (per-file grep, since no gate type-checks test files) | T-261-10 | component | `npm --prefix frontend test -- src/components/train/blunder-check/__tests__/BlunderCheckSolution.test.tsx src/lib/__tests__/blunderCheckSolution.test.ts` | ✅ extend | ⬜ pending |
| 261-04-T2 | 2 | D-03, D-04, D-05, D-07, D-09 | Exact copy and order; strip and card; none for false alarm, herring, null or missing feedback | T-261-10, T-261-11 | component + unit | same as 261-04-T1, then the full frontend gate | ✅ extend | ⬜ pending |
| 261-05-T1 | 2 | Calibration script | Dev run prints the share section and band tables | T-261-12 | smoke (dev, read-only) | `uv run python scripts/blunder_check/caught_rate.py --db dev` | ❌ new | ⬜ pending |
| 261-05-T2 | 2 | Calibration script, share acceptance | Bands, reached denominator, false alarms beside, Wilson, legacy fallback, share verdict | T-261-13 | unit | `uv run pytest tests/scripts/test_caught_rate.py -x` | ❌ new | ⬜ pending |
| 261-06-T1 | 3 | Counts as normal (seed), D-04, D-06 | HTTP end to end: exploration window's solution carries the snapshot feedback; points enter session and weekly aggregate; no arm or score before the answer | T-261-17 | integration (HTTP) | `uv run pytest tests/routers/test_blunder_check_exploration.py -x` | ❌ new | ⬜ pending |
| 261-06-T2 | 3 | D-04, D-05, D-06, snapshot | Legacy null; caught and missed carry feedback; false alarm key set unchanged; feedback survives the game delete | T-261-15, T-261-16 | router | `uv run pytest tests/routers/test_blunder_check_solution.py -x` | ✅ extend | ⬜ pending |
| 261-07-T1 | 4 | Release gate | End-to-end test, one changelog bullet (the draw is not announced), full pre-merge gate with the `-n auto` suite (executor) | — | gate | `uv run pytest -n auto -x` after the CLAUDE.md gate | ✅ | ⬜ pending |
| 261-07-T2 | 4 | Release gate, D-10 | Serial backend suite green (orchestrator, detached); prod EXPLAIN of the scored foreign and nearest picks: index access, warm median within max(2 x cut, 200 ms) | T-261-19, T-261-20 | gate + manual (orchestrator) | `uv run pytest -x` detached, then `grep -cx "exit=0" temp/261-explore/serial-pytest.log` prints 1 | — | ⬜ pending |
| 261-07-T3 | 4 | D-03 in the app; share acceptance | Paragraph on desktop and phone; share follow-up recorded in STATE.md | — | manual (orchestrator) | — | — | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/services/test_blunder_check_feedback.py` — D-06 to D-09, D-12 (reuses `tests/services/line_material_fixtures.py`); created by 261-01-T2
- [ ] `tests/scripts/test_caught_rate.py` for the calibration script; created by 261-05-T1 / T2
- [x] Seed helper with a per-ply pv map: not needed. The type line is pinned at the unit level on the committed line
      fixtures (261-01-T2); the DB-level tests use the seed's NULL pv and assert swing NULL / mate false.

---

## Manual-Only Verifications

| Behavior | Decision | Why Manual | Test Instructions |
|----------|----------|------------|-------------------|
| Backend suite green when run serially (as CI runs it) | Release gate | Runs tens of minutes, past the 600 s tool cap; an executor's background job dies with it | 261-07-T2 step 0: the orchestrator starts `uv run pytest -x` detached (setsid nohup) with the log at `temp/261-explore/serial-pytest.log`, waits with Monitor, and requires the last line `exit=0` before any merge |
| The foreign and nearest-foreign picks without the cut stay cheap on prod | D-10 | Needs the prod data volume; run by the orchestrator, read-only | 261-07-T2: `EXPLAIN (ANALYZE, BUFFERS)` of the four statements in `temp/261-explore/pick-explain.sql`; pass when no Seq Scan on game_flaws and the scored warm median is at most max(2 x cut, 200 ms) |
| Served exploration share on prod | Share acceptance | Needs real sessions after release | About a week after release: `uv run python scripts/blunder_check/caught_rate.py --db prod --since <release date>`; accept when n >= 500 and the 95% Wilson interval overlaps [0.18, 0.26] (recorded in STATE.md by 261-07-T3) |
| Feedback paragraph in the running app | D-03 | Layout and popover on real viewports | 261-07-T3: dev app, desktop card and 375 px strip |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s for the quick run
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
