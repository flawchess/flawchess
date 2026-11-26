---
phase: "249"
slug: "blunder-check-playable-mvp"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-11-10"
---

# Phase 249 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Seeded from 249-RESEARCH.md
> "Validation Architecture"; the per-task map is filled once plans exist.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (+ pytest-asyncio, xdist) backend; vitest frontend |
| **Config file** | `pyproject.toml`, `tests/conftest.py` (per-worker cloned DBs); `frontend/vite.config.ts` test block |
| **Quick run command** | `uv run pytest tests/services/test_blunder_check_rules.py tests/routers/test_blunder_check.py -x` |
| **Full suite command** | `uv run pytest -n auto -x` and `npm --prefix frontend test -- --run` |
| **Estimated runtime** | ~30 s quick, ~6 min full backend |

---

## Sampling Rate

- **After every task commit:** Run the quick command for the touched module
- **After every plan wave:** Run `uv run pytest -n auto -x` + `npm --prefix frontend test -- --run`
- **Before `/gsd-verify-work`:** Full pre-merge gate (CLAUDE.md) must be green
- **Max feedback latency:** 60 seconds for the quick command

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 249-01-01 | 01 | 1 | D-02..D-06 | T-249-01 | report and app share one rule implementation | unit | `uv run pytest tests/services/test_blunder_check_rules.py tests/scripts/test_blunder_check_metrics.py tests/scripts/test_blunder_check_calibration.py -x` | ❌ W0 | ⬜ pending |
| 249-01-02 | 01 | 1 | D-03..D-08, D-11, D-14 | T-249-01 | stored blunder must be recomputed as blunder | unit (tdd) | `uv run pytest tests/services/test_blunder_check_candidates.py -x` | ❌ W0 | ⬜ pending |
| 249-02-01 | 02 | 1 | D-01, D-15 | T-249-02..04 | non-beta 403, anon 401, user-scoped reads | migration + router | `uv run alembic upgrade head && uv run alembic check`; `uv run pytest tests/routers/test_blunder_check_sessions.py -x` | ❌ W0 | ⬜ pending |
| 249-02-02 | 02 | 1 | D-09, D-10, D-15, D-19 | T-249-05, T-249-06 | one open session; guests excluded from foreign picks | repository (DB) | `uv run pytest tests/repositories/test_blunder_check_repository.py -x` | ❌ W0 | ⬜ pending |
| 249-03-01 | 03 | 2 | D-02, D-03, D-07, D-15 | T-249-07 | compose payload carries no key material | router | `uv run pytest tests/routers/test_blunder_check_sessions.py -x` | ❌ | ⬜ pending |
| 249-03-02 | 03 | 2 | D-09, D-10, D-11 | T-249-08, T-249-09 | foreign fallback by rating, no repeats, race | service (DB) + router | `uv run pytest tests/services/test_blunder_check_selection.py tests/routers/test_blunder_check_sessions.py -x` | ❌ | ⬜ pending |
| 249-04-01 | 04 | 3 | D-12, D-16, D-17 | T-249-10 | start payload exact key set | router | `uv run pytest tests/routers/test_blunder_check_drill.py -x` | ❌ | ⬜ pending |
| 249-04-02 | 04 | 3 | D-10, D-12, D-13, D-16, D-18 | T-249-10..14 | server grading, ceiling, resume = 15 s minus real elapsed (no allowance), window order, claim, IDOR | unit (tdd) + router | `uv run pytest tests/services/test_blunder_check_grading.py tests/routers/test_blunder_check_drill.py -x` | ❌ | ⬜ pending |
| 249-04-03 | 04 | 3 | D-14 | — | Score % incl. unreached blunder | router | `uv run pytest tests/routers/test_blunder_check_drill.py -x -k "finish or score"` | ❌ | ⬜ pending |
| 249-05-01 | 05 | 4 | D-12, D-17 | T-249-15 | better move claimed once, server points | router | `uv run pytest tests/routers/test_blunder_check_solution.py -x` | ❌ | ⬜ pending |
| 249-05-02 | 05 | 4 | D-09, D-10, D-14, D-16, D-17 | T-249-16..18 | false alarm withholds blunder; no foreign identity | unit (tdd) + router | `uv run pytest tests/services/test_blunder_check_grading.py tests/routers/test_blunder_check_solution.py -x` | ❌ | ⬜ pending |
| 249-06-01 | 06 | 4 | D-01 | T-249-19 | beta tab; Start composes through the real client | vitest + tsc | `npm --prefix frontend test -- --run src/pages/__tests__/Train.subnav.test.tsx`; `npm --prefix frontend run build` | ❌ | ⬜ pending |
| 249-06-02 | 06 | 4 | D-12, D-18 | — | reducer: resume without extra time, one answer per prompt, lead-in and feedback + move + reply inside the 3 s allowance | vitest (tdd) | `npm --prefix frontend test -- --run src/lib/__tests__/blunderCheckDrill.test.ts`; `npm --prefix frontend run build` | ❌ | ⬜ pending |
| 249-06-03 | 06 | 4 | D-01, D-19 | T-249-19, T-249-29 | non-beta redirect, Today latch, one compose per double click, no Umami | vitest + lint | `npm --prefix frontend test -- --run src/lib/__tests__/trainRoute.test.ts src/pages/__tests__/Train.subnav.test.tsx src/components/train/blunder-check/__tests__/BlunderCheckTab.test.tsx`; `npm --prefix frontend run lint` | ❌ | ⬜ pending |
| 249-07-01 | 07 | 5 | D-09, D-12 | — | move + reply only after a server-graded Safe | vitest + tsc | `npm --prefix frontend test -- --run src/components/train/blunder-check/__tests__/BlunderCheckTab.test.tsx`; `npm --prefix frontend run build` | ❌ | ⬜ pending |
| 249-07-02 | 07 | 5 | D-12, D-13, D-18 | T-249-20 | timeout fires once; resume uses the server's remaining time | vitest (tdd) | `npm --prefix frontend test -- --run src/hooks/__tests__/useMoveTimer.test.ts src/components/train/blunder-check/__tests__/BlunderCheckTab.test.tsx`; `npm --prefix frontend run lint` | ❌ | ⬜ pending |
| 249-07-03 | 07 | 5 | D-14, D-19 | T-249-21 | Score % from the server; no Umami events | vitest + knip | `npm --prefix frontend test -- --run src/components/train/blunder-check/__tests__/BlunderCheckTab.test.tsx`; `npm --prefix frontend run knip` | ❌ | ⬜ pending |
| 249-08-01 | 08 | 6 | D-12, D-17 | T-249-22 | server tier and points shown | vitest + tsc | `npm --prefix frontend test -- --run src/components/train/blunder-check/__tests__/BlunderCheckTab.test.tsx src/pages/__tests__/Train.subnav.test.tsx`; `npm --prefix frontend run build` | ❌ | ⬜ pending |
| 249-08-02 | 08 | 6 | D-12, D-14 | — | Best/Game/Your lines searched one at a time; one reducer path to Next | vitest (tdd) + tsc | `npm --prefix frontend test -- --run src/lib/__tests__/blunderCheckDrill.test.ts src/components/train/blunder-check/__tests__/BlunderCheckSolution.test.tsx src/components/train/blunder-check/__tests__/BlunderCheckTab.test.tsx`; `npm --prefix frontend run build` | ❌ | ⬜ pending |
| 249-08-03 | 08 | 6 | D-09, D-10, D-16, D-19 | T-249-23, T-249-24 | foreign copy never "your move"; false alarm reveals nothing | vitest (tdd) | `npm --prefix frontend test -- --run src/components/train/blunder-check/__tests__/BlunderCheckSolution.test.tsx src/components/train/blunder-check/__tests__/BlunderCheckTab.test.tsx` | ❌ | ⬜ pending |
| 249-09-01 | 09 | 7 | D-01, D-12..D-14, D-18, D-19 | T-249-27 | agent-run browser UAT; beta flag restored | manual (agent) + router regression | `uv run pytest tests/routers/test_blunder_check_sessions.py tests/routers/test_blunder_check_drill.py tests/routers/test_blunder_check_solution.py -x` | ✅ after W6 | ⬜ pending |
| 249-09-03 | 09 | 7 | D-01 | T-249-25, T-249-26 | owner go-ahead before deploy; prod 401/403; owner asked before any change if the prod beta flag is false | ship | `git rev-list --left-right --count main...origin/main`; `curl -s -o /dev/null -w '%{http_code}' https://flawchess.com/api/blunder-check/sessions/open` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `seed_blunder_check_game(...)` test helper: game with contiguous `game_positions`, `full_evals_completed_at`,
      `best_move` at blunder plies, user-side severity-2 `game_flaws` with Maia pairs; `finally` cleanup; unique user ids
- [ ] Deterministic RNG injection point in the session composer
- [ ] Beta user fixture (register + flip `beta_enabled`)
- [x] Prod latency probe (done by the orchestrator, 249-RESEARCH "Prod Latency Probe")

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Drill feel: lead-in pace, arrow prompt, timer, forfeit animation and sounds | D-12, D-13 | Visual/audio timing | Agent-run browser UAT with a beta-enabled dev user (project memory: run human-action checkpoints yourself) |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
