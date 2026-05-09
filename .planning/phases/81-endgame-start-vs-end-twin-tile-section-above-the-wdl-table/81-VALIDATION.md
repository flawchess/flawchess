---
phase: 81
slug: endgame-start-vs-end-twin-tile-section-above-the-wdl-table
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-09
---

# Phase 81 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (backend) + vitest 2.x (frontend) |
| **Config file** | `pyproject.toml` (backend), `frontend/vitest.config.ts` (frontend) |
| **Quick run command** | `uv run pytest tests/services/test_endgame_service.py tests/repositories/test_endgame_repository.py -x -q` (backend) / `cd frontend && npm test -- --run src/components/charts/__tests__ src/pages/__tests__/Endgames` (frontend) |
| **Full suite command** | `uv run pytest -x` (backend) / `cd frontend && npm test -- --run` (frontend) |
| **Estimated runtime** | ~30s backend quick / ~120s backend full / ~15s frontend quick / ~60s frontend full |

---

## Sampling Rate

- **After every task commit:** Run quick command for the surface touched (backend or frontend)
- **After every plan wave:** Run the full suite for that surface
- **Before `/gsd-verify-work`:** Both full suites must be green; `uv run ty check app/ tests/` clean; `cd frontend && npm run knip && npm run lint` clean
- **Max feedback latency:** 30 seconds per task

---

## Per-Task Verification Map

(Filled in during planning — placeholder rows match the planner's anticipated task layout.)

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 81-01-* | 01 | 1 | D-11, D-12 | — | mate-excluded; signed-from-user-perspective | unit | `uv run pytest tests/repositories/test_endgame_repository.py -k entry_eval -x` | ❌ W0 | ⬜ pending |
| 81-02-* | 02 | 1 | D-07, D-08, D-10 | — | n<10 → None; p<0.05 verdict | unit | `uv run pytest tests/services/test_eval_confidence.py tests/services/test_score_confidence.py -x` | ✅ | ⬜ pending |
| 81-03-* | 03 | 1 | D-11 (response shape) | — | response includes 4 new fields with valid types | contract | `uv run pytest tests/api/test_endgame_router.py -k performance -x` | ❌ W0 | ⬜ pending |
| 81-04-* | 04 | 2 | D-01..D-04, D-09, D-15..D-17 | — | renders above WDL table; mobile ordering; color zones | component | `cd frontend && npm test -- --run src/components/endgame/EndgameStartVsEndSection` | ❌ W0 | ⬜ pending |
| 81-05-* | 05 | 2 | D-05, D-06 | — | n<10 placeholder; both-empty hides section | component | `cd frontend && npm test -- --run src/components/endgame/EndgameStartVsEndSection` | ❌ W0 | ⬜ pending |
| 81-06-* | 06 | 3 | D-13, D-14 | — | accordion adds 2 paragraphs in correct order | snapshot/dom | `cd frontend && npm test -- --run src/pages/__tests__/Endgames` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/repositories/test_endgame_repository.py` — extend with entry-eval aggregation cases (n<10, mate-excluded, signed-by-color, multi-class dedupe)
- [ ] `tests/api/test_endgame_router.py` — extend `/api/endgame/performance` contract test for 4 new fields
- [ ] `frontend/src/components/endgame/__tests__/EndgameStartVsEndSection.test.tsx` — new test file for the section component
- [ ] `frontend/src/pages/__tests__/Endgames.test.tsx` — extend (or create) for accordion paragraph + DOM-order assertions

*Existing infrastructure (`tests/services/test_eval_confidence.py`, `test_score_confidence.py`, `MiniBulletChart.test.tsx`, `BulletConfidencePopover.test.tsx`, `ScoreConfidencePopover.test.tsx`) covers the math + chart + popover surfaces — no new framework setup needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Visual parity with Openings ExplorerTab score bullet | D-16, "match Openings page visual language exactly" | Subjective visual — diff requires side-by-side eyeballing | Open `/openings` and `/endgames` in dev; confirm score-bullet domain, neutral band, colors are visually identical |
| Mobile ordering & stacking | D-04, D-17 | Layout responsiveness needs viewport resize | Resize browser to <`lg` (≤1024px); confirm tiles stack vertically with entry-eval first, score second |
| Concept-accordion paragraph wording | D-13 | Final copy iterated with the user during execution | Open the `endgame-concepts-trigger` accordion; confirm two new paragraphs read naturally and use "we can't tell" framing |
| Popover content (n, p-value, verdict, methodology) | D-03, "n + p inside popover only" | Hover-state behavior + copy review | Hover/tap each tile's info icon; confirm `BulletConfidencePopover` and `ScoreConfidencePopover` show n, p, CI, verdict |
| Three-state color verdict | D-09, D-10 | Cross-user data check | Impersonate users with (a) sig positive entry eval, (b) sig negative, (c) p≥0.05 — verify green/red/neutral |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
