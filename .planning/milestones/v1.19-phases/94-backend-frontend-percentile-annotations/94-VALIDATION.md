---
phase: 94
slug: backend-frontend-percentile-annotations
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-23
---

# Phase 94 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Backend framework** | pytest 7.x (`uv run pytest`) |
| **Frontend framework** | vitest (`cd frontend && npm test -- --run`) |
| **Config files** | `pyproject.toml` (pytest config), `frontend/vitest.config.ts` |
| **Backend quick run** | `uv run pytest tests/services/test_endgame_service.py tests/services/test_global_percentile_cdf.py -x` |
| **Backend full suite** | `uv run pytest -x` |
| **Frontend quick run** | `cd frontend && npm test -- --run src/components/charts/__tests__ src/components/percentile/__tests__` |
| **Frontend full suite** | `cd frontend && npm run lint && npm test -- --run` |
| **Type checks** | `uv run ty check app/ tests/`; frontend types validated by `cd frontend && npx tsc --noEmit` |
| **Estimated quick runtime** | ~30 seconds (backend quick + frontend quick) |
| **Estimated full runtime** | ~3 minutes (pytest + lint + vitest) |

---

## Sampling Rate

- **After every task commit:** Backend quick OR frontend quick, scoped to the touched layer
- **After every plan wave:** Full suite for the touched layer (backend or frontend)
- **Before `/gsd:verify-work`:** Backend full suite + frontend full suite + `uv run ty check app/ tests/` must all be green
- **Max feedback latency:** 60 seconds after task commit

---

## Per-Task Verification Map

> The planner fills task IDs once `PLAN.md` files exist. The skeleton below records the per-requirement coverage strategy; the planner expands each row to one row per task and fills in concrete task IDs.

| Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | Status |
|------|------|-------------|------------|-----------------|-----------|-------------------|--------|
| 01 (backend) | 1 | PCTL-02 | — | API emits nullable `*_percentile` for the 4 in-scope metrics; null when below reliability gate | unit + integration | `uv run pytest tests/services/test_endgame_service.py -k percentile -x` | ⬜ pending |
| 01 (backend) | 1 | PCTL-06 | — | Below reliability-N gate → `*_percentile` is None; chip absent | unit | `uv run pytest tests/services/test_endgame_service.py -k reliability_gate -x` | ⬜ pending |
| 01 (backend) | 1 | PCTL-02 schema | — | New nullable fields appear on response models alongside existing siblings; non-breaking | unit | `uv run pytest tests/schemas/test_endgames_schema.py -x` (or equivalent) | ⬜ pending |
| 02 (FE chip component) | 2 | PCTL-03 | — | `PercentileChip` renders "top X%" with honest rounding; never "bottom Y%" | unit | `cd frontend && npm test -- --run PercentileChip` | ⬜ pending |
| 02 (FE chip component) | 2 | PCTL-05 | — | Banded colors come from `theme.ts` constants (no hard-coded values) | unit + lint | `cd frontend && npm test -- --run PercentileChip && npm run lint` | ⬜ pending |
| 02 (FE chip component) | 2 | PCTL-04 | — | Popover flavor routes correctly: 3 metrics → skill-isolating, Conv → improvement-focus | unit | `cd frontend && npm test -- --run PercentileChip` | ⬜ pending |
| 02 (FE chip component) | 2 | PCTL-03 flames | — | 1 flame at p90, 2 at p95, 3 at p99; highest tier only | unit | `cd frontend && npm test -- --run PercentileChip` | ⬜ pending |
| 03 (FE wiring) | 3 | PCTL-05 mobile | — | Chip renders on desktop + 375px mobile; chip absent on Recovery card + raw % gauges | component | `cd frontend && npm test -- --run EndgameOverallPerformanceSection EndgameMetricCard` | ⬜ pending |
| 03 (FE wiring) | 3 | PCTL-06 wire | — | Wired rows render chip only when API `*_percentile` is non-null | component | `cd frontend && npm test -- --run EndgameOverallPerformanceSection EndgameMetricCard` | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/services/test_endgame_service.py` already exists — extend with `*_percentile` assertions (no new file). Confirm path during planner spawn; if absent, planner adds a Wave 0 stub.
- [ ] `tests/schemas/test_endgames_schema.py` (or the project's equivalent schema-contract test) — extend with the 4 new nullable fields. Wave 0 stub if missing.
- [ ] `frontend/src/components/percentile/__tests__/PercentileChip.test.tsx` — new Vitest file alongside the new component (planner-owned).
- [ ] Extend `frontend/src/components/charts/__tests__/EndgameOverallPerformanceSection.test.tsx` and `frontend/src/components/charts/__tests__/EndgameMetricCard.test.tsx` with chip-present / chip-absent assertions on the 4 affected rows.

*No new framework install required — pytest + vitest infrastructure already in place.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Visual chip styling at 375px mobile width | PCTL-05 mobile parity | Visual fidelity (pill shape, color contrast, flame icon size, right-alignment wrap) requires human eyes | After backend + frontend deploys: open Stats page on iPhone or Chrome DevTools 375px width; verify chip is right-aligned, readable, and color bands match `theme.ts` |
| Popover copy reads as deliberate companions (skill-isolating vs improvement-focus) on the same Stats page | PCTL-04 | Editorial judgement (per `feedback_popover_copy_minimalism.md`) | UAT: tap both Endgame Score Gap chip and Conversion ΔES chip on the same page; verify copy doesn't contradict |
| Honest rounding ("top 0.1%" not "top 0.137%"; "top 50%" near median; "top 99%" at percentile 1) | PCTL-03 | Number-formatting edge cases best verified against real production user data | UAT: pick a known production user via `flawchess-prod-db` tunnel and confirm chip phrasing matches their CDF position |
| Flame tier escalation reads cleanly (1 → 2 → 3 flames doesn't crowd the chip at mobile width) | PCTL-03 / PCTL-05 | Visual density best judged by eye | UAT at 375px: synthetic user at p99 (3 flames) should still fit beside the value without overflow |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (none expected — pytest + vitest infrastructure exists)
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter (planner flips this once the per-task map is fully populated)

**Approval:** pending
