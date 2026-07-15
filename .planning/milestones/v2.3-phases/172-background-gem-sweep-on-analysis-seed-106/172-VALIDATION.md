---
phase: 172
slug: background-gem-sweep-on-analysis-seed-106
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-14
---

# Phase 172 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from `172-RESEARCH.md` § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework (frontend)** | Vitest + @testing-library/react (existing: `frontend/src/lib/__tests__/gemMove.test.ts`, `frontend/src/pages/__tests__/Analysis.test.tsx` — already mocks `useStockfishGradingEngine` / `useMaiaEngine` / `useStockfishEngine` module-wide) |
| **Framework (backend)** | pytest + pytest-asyncio, per-run isolated DB (`tests/conftest.py`) |
| **Config file** | `frontend/vite.config.ts` (vitest colocated); backend via `pyproject.toml` |
| **Quick run (frontend)** | `cd frontend && npm test -- --run <path>` |
| **Quick run (backend)** | `uv run pytest tests/test_opening_lookup.py -x -q` |
| **Full suite (frontend)** | `cd frontend && npm run lint && npm test -- --run && npx tsc -b --noEmit && npm run knip` |
| **Full suite (backend)** | `uv run pytest -n auto -x` |
| **Estimated runtime** | frontend targeted ~5–15s; backend targeted ~10s; full gate several minutes |

---

## Sampling Rate

- **After every task commit:** the relevant unit test file(s) from the map below, plus `uv run ty check app/ tests/` (backend tasks) or `npx tsc -b --noEmit` (frontend tasks).
- **After every plan wave:** `uv run pytest -n auto -x`; `cd frontend && npm run lint && npm run knip && npx tsc -b --noEmit && npm test -- --run`.
- **Before `/gsd-verify-work`:** the full pre-merge gate (CLAUDE.md) green, PLUS a manual UAT pass (see Manual-Only Verifications).
- **Max feedback latency:** < 30s for targeted runs.

---

## Per-Task Verification Map

Task IDs are filled in by the planner. Success criteria (SC) map to the phase's ROADMAP criteria.

| SC | Behavior | Test Type | Automated Command | File Exists |
|----|----------|-----------|-------------------|-------------|
| 1 | Free prefilter converts SAN→UCI before comparing to `EvalPoint.best_move` (a naive `played === best_move` never matches — RESEARCH pitfall), and excludes plies ≤ `opening_ply_count` | unit | `npm test -- --run src/lib/__tests__/gemSweep.test.ts` | ❌ Wave 0 (new pure module) |
| 2 | **Yield-to-cursor.** A live gem-grading request started while a sweep candidate is mid-flight resolves without waiting on the sweep's queue/worker | unit (load-bearing — see Half-Invariant Risk) | `npm test -- --run src/lib/__tests__/gemSweep.test.ts` | ❌ Wave 0 |
| 3 | **Rung pin (behavior change).** Changing `selectedElo` (the slider) does NOT change which nodes classify as gems; changing the mover DOES change the rung used | unit | `npm test -- --run src/hooks/__tests__/useMaiaEloDefault.test.ts` | Existing file, new cases |
| 4 | A card with `analysis_state === 'no_engine_analysis'` never triggers a sweep-start effect | unit | `npm test -- --run src/pages/__tests__/Analysis.test.tsx` | Existing file, new cases |
| 5 | `GEM_MAIA_MAX_PROB === 0.2`; a probability of 0.15 that failed C1 before now passes | unit | `npm test -- --run src/lib/__tests__/gemMove.test.ts` | Existing file — **hardcoded `0.1` assertion at `gemMove.test.ts:58-59` must be updated to `0.2`** |
| 6 | `find_opening_ply_count` returns correct depth for exact / partial / no-match / empty-moves; `resolveMarkerIcon` and the board corner marker apply `severity > gem > book` | unit | `uv run pytest tests/test_opening_lookup.py -x -q`; `npm test -- --run src/components/analysis/__tests__/VariationTree.test.tsx src/components/board/__tests__/boardMarkers.test.tsx` | Existing files, new cases |
| 7 | Sweep-start fires on the analysis-readiness FALSE→TRUE **transition**, not only at mount (bot game opened mid-tier-1-analysis) | unit | `npm test -- --run src/pages/__tests__/Analysis.test.tsx` | Existing file, new case (mirrors the rj5 "flips from unanalyzed to analyzed" test already there) |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `frontend/src/lib/__tests__/gemSweep.test.ts` — new. Covers free-prefilter purity (SC1) and, critically, the **yield-to-cursor invariant (SC2)** as a genuine contention test: start a live gem-grading request, THEN start a sweep candidate, and assert the live request resolves without delay attributable to the sweep. A test that only asserts "the sweep resolves gems" does **not** prove this.
- [ ] `tests/test_opening_lookup.py` — new test class for `find_opening_ply_count` (exact match, partial match / game leaves book, no match, empty moves list).
- [ ] `frontend/src/hooks/__tests__/useMaiaEloDefault.test.ts` — extend with the D1 behavior-change regression: slider changes must not move the pinned per-node rung.
- [ ] `frontend/src/components/analysis/__tests__/VariationTree.test.tsx` — extend `resolveMarkerIcon` with a `book`-only case and a `severity + book` case (severity wins).
- [ ] `frontend/src/components/board/__tests__/boardMarkers.test.tsx` — extend with a `book` marker render case.

---

## Half-Invariant Risk (project memory: mutation-test gap closures)

D5's yield-to-cursor requirement is exactly the invariant shape that `tsc` / `eslint` / `knip` / existing tests are **structurally blind to**. A sweep that technically "runs in the background" but shares a worker or hook instance with the live path will pass every type check and every test that does not specifically construct contention. RESEARCH confirms the mechanism: `useMaiaEngine.analyze()` **silently drops** a second concurrent request rather than queuing it, and neither `useStockfishGradingEngine` nor `useMaiaEngine` has any priority/preemption concept.

**Prove it the way this project's memory prescribes:** implement the sweep sharing a worker with the live path first, confirm the contention test goes **RED**, then apply the isolation fix and confirm it turns green. Grep / symbol-presence is not acceptable evidence for SC2.

---

## Manual-Only Verifications

| Behavior | SC | Why Manual | Test Instructions |
|----------|----|------------|-------------------|
| Badges fill in *ahead of* the cursor with no perceptible lag on the current position | 1, 2 | Perceived latency is not unit-testable | Open a real, already-analyzed game; step briskly forward through the mainline; gem and book badges should already be rendered on plies ahead of the cursor, and stepping must not feel slower than today |
| Bot game opened mid-tier-1-analysis gets swept when evals land | 7 | Requires a live backend analysis run | Play a bot game, open it from the Library while its tier-1 analysis is still running, wait for the evals to arrive, confirm the sweep starts without a reload |
| Real-game gem frequency is sane at the raised threshold | 5 | Deliberately not measured pre-ship (SEED-106) | Judge absolute gem rates on real games during UAT; the Phase 165 TSV is an enriched sample, so only its ratios transfer |
| Move-8 gem still rendered at move 60 on a long game | — | Cache-eviction behavior under a shared `LIVE_EVAL_CACHE_MAX = 256` budget | Open a long game (100+ plies) with variations explored, step to the end, scroll back and confirm early gem badges are still present |

---

## Validation Sign-Off

- [ ] All tasks have automated verify or a Wave 0 dependency
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] SC2 (yield-to-cursor) is proven by a RED-then-green contention test, not by symbol presence
- [ ] No watch-mode flags
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
