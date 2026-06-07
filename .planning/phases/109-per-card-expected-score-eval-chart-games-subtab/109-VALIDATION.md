---
phase: 109
slug: per-card-expected-score-eval-chart-games-subtab
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-07
---

# Phase 109 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio (backend); Vitest (frontend) |
| **Config file** | `pyproject.toml` (backend); `frontend/vitest.config.ts` (frontend) |
| **Quick run command** | `uv run pytest tests/services/test_eval_chart_service.py -x` |
| **Full suite command** | `uv run pytest -n auto` (backend); `cd frontend && npm test -- --run` |
| **Estimated runtime** | ~5s quick unit / ~60s full backend suite |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/services/test_eval_chart_service.py -x`
- **After every plan wave:** Run `uv run pytest -n auto`
- **Before `/gsd-verify-work`:** Full backend suite + `cd frontend && npm run lint && npm test -- --run` must be green
- **Max feedback latency:** ~5 seconds (quick unit run)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| eval-series-white-pov | backend | 1 | LIBG-10 | — | N/A | unit | `uv run pytest tests/services/test_eval_chart_service.py -k white_perspective -x` | ❌ W0 | ⬜ pending |
| both-color-detection | backend | 1 | LIBG-10 | — | N/A | unit | `uv run pytest tests/services/test_eval_chart_service.py -k both_color -x` | ❌ W0 | ⬜ pending |
| is-user-discriminator | backend | 1 | LIBG-10 | — | N/A | unit | `uv run pytest tests/services/test_eval_chart_service.py -k is_user -x` | ❌ W0 | ⬜ pending |
| phase-transitions | backend | 1 | LIBG-10 | — | N/A | unit | `uv run pytest tests/services/test_eval_chart_service.py -k phase_transitions -x` | ❌ W0 | ⬜ pending |
| opponent-tag-strip | backend | 1 | LIBG-10 | — | N/A | unit | `uv run pytest tests/services/test_eval_chart_service.py -k opponent_tags -x` | ❌ W0 | ⬜ pending |
| null-eval-handling | backend | 1 | LIBG-10 | — | N/A | unit | `uv run pytest tests/services/test_eval_chart_service.py -k null_eval -x` | ❌ W0 | ⬜ pending |
| router-inline-payload | backend | 2 | LIBG-10 | — | N/A | integration | `uv run pytest tests/test_library_router.py -x -k eval_series` | extend | ⬜ pending |
| router-unanalyzed-null | backend | 2 | LIBG-10 | — | N/A | integration | `uv run pytest tests/test_library_router.py -x -k unanalyzed` | extend | ⬜ pending |
| no-n-plus-1 | backend | 2 | LIBG-10 | — | N/A | integration | query-count assertion in router test | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/services/test_eval_chart_service.py` — pure unit tests for the new eval-series builder:
  - white-perspective ES line correctness (eval_cp → es via `eval_cp_to_expected_score(.., "white")`; mate → 1.0/0.0)
  - mover-POV both-color flaw detection (player + opponent, B/M/I)
  - `is_user` flag assignment (`mover_color == game.user_color`)
  - phase-transition first-ply extraction (≤2 lines, no ply-0 line)
  - opponent tag strip (`miss`, `lucky-escape` absent from opponent markers; mover-framed tags present)
  - null eval → `es: null` in series
  - Reuse the `_make_pos()` / `_make_game()` fixture pattern from `tests/services/test_flaws_service.py`
- [ ] Query-count / no-N+1 assertion harness in `tests/test_library_router.py` (single batched `game_positions` query for the page)

*Frontend `EvalChart.tsx` rendering is verified via HUMAN-UAT (recharts SVG output is not unit-asserted on this project); component existence + `data-testid` are checkable.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Three-equal-thirds desktop card + mobile stacking | LIBG-10 | Visual layout; recharts SVG render | Load Library → Games on desktop + 375px; confirm analyzed cards show miniboard+info · chart · tags as equal thirds; unanalyzed cards show NoAnalysisState pill in col 2 |
| Dual-marker dots (filled player / hollow opponent), 6 styles | LIBG-10 | Visual + density tuning per D-09 | Hover/tap dots; confirm filled=you, hollow=opponent, color=severity; tooltips label "You"/"Opponent"; inaccuracies legible |
| Two-region area shading + midline + ≤2 phase lines | LIBG-10 | Visual gradient render | Confirm light-grey above 0.5 / dark-grey below; dashed midline; phase lines only where transitions occur |
| Gzipped payload delta is negligible (no perceptible regression) | LIBG-10 | Network measurement | Measure gzipped `GET /library/games` response before/after; record delta in plan/summary |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
