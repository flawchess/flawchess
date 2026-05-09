---
phase: 81
slug: endgame-start-vs-end-twin-tile-section-above-the-wdl-table
status: approved
nyquist_compliant: true
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
| **Quick run command** | `uv run pytest tests/test_endgame_service.py tests/test_endgames_router.py -x -q` (backend) / `cd frontend && npm test -- --run src/components/charts/__tests__/EndgameStartVsEndSection.test.tsx src/pages/__tests__/Endgames.startVsEnd.test.tsx src/lib/__tests__/endgameEntryEvalZones.test.ts` (frontend) |
| **Full suite command** | `uv run pytest -x` (backend) / `cd frontend && npm test -- --run` (frontend) |
| **Estimated runtime** | ~30s backend quick / ~120s backend full / ~15s frontend quick / ~60s frontend full |

---

## Sampling Rate

- **After every task commit:** Run quick command for the surface touched (backend or frontend)
- **After every plan wave:** Run the full suite for that surface
- **Before `/gsd-verify-work`:** Both full suites must be green; `uv run ty check app/ tests/` clean; `cd frontend && npm run knip && npm run lint && npm run build` clean
- **Max feedback latency:** 30 seconds per task

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 81-01-* | 01 | 1 | D-07, D-08, D-10, D-11, D-12 | — | mate-excluded; signed-from-user-perspective; n<10 → None; per-game dedupe | unit + contract | `uv run pytest tests/test_endgame_service.py tests/test_endgames_router.py -x` | ✅ (extends existing) | ⬜ pending |
| 81-02-* | 02 | 1 | D-11 (TS mirror), D-15 (axis), Q1/A1 (neutral band) | — | type mirror; zone-color helper resolves to ZONE_SUCCESS/DANGER/NEUTRAL | unit | `cd frontend && npm test -- --run src/lib/__tests__/endgameEntryEvalZones.test.ts` | ❌ W0 | ⬜ pending |
| 81-03-* | 03 | 2 | D-01..D-06, D-09, D-10, D-15, D-16, D-17 | — | n<10 placeholder; both-empty hides section; mobile stack order; color="white" prop locked | component | `cd frontend && npm test -- --run src/components/charts/__tests__/EndgameStartVsEndSection.test.tsx` | ❌ W0 | ⬜ pending |
| 81-04-* | 04 | 3 | D-01, D-02, D-13, D-14, D-18, D-19, D-20, D-21 | — | DOM order (section above WDL); accordion paragraphs in correct order; D-21 negative-scope (existing testids preserved); "Opponent Strength filter" literal text | page integration | `cd frontend && npm test -- --run src/pages/__tests__/Endgames.startVsEnd.test.tsx` | ❌ W0 | ⬜ pending |
| 81-05-* | 05 | 4 | D-04, D-09, D-13, D-16, D-17 | — | visual parity, mobile stacking, popover content, three-state color on real users | manual UAT | (none — checkpoint) | n/a | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_endgame_service.py` — extend with entry-eval aggregation cases (n<10 → None for both p-values; mate-excluded count; signed-by-color sign-flip; per-game dedupe across multi-class spans)
- [ ] `tests/test_endgames_router.py` — extend `/api/endgames/overview` (or `/performance`) contract test for the 6 new fields (4 from D-11 + 2 CI bounds)
- [ ] `frontend/src/lib/__tests__/endgameEntryEvalZones.test.ts` — new test file; covers `ENDGAME_ENTRY_EVAL_DOMAIN_PAWNS = 2.0`, neutral band ±0.75, and the zone-color helper's three-state output
- [ ] `frontend/src/components/charts/__tests__/EndgameStartVsEndSection.test.tsx` — new component test; covers two-tile layout, color zones (sig+/sig−/null), n<10 placeholder, mobile-order, both-empty hide
- [ ] `frontend/src/pages/__tests__/Endgames.startVsEnd.test.tsx` — new page integration test; covers DOM order (section above WDL), accordion paragraph presence + order (D-13/D-14), D-21 negative-scope (`perf-wdl-table` / `score-gap-difference` / `endgame-score-timeline-chart` still rendered), and "Opponent Strength filter" literal text

*Existing infrastructure (`tests/services/test_eval_confidence.py`, `tests/services/test_score_confidence.py`, `MiniBulletChart.test.tsx`, `BulletConfidencePopover.test.tsx`, `ScoreConfidencePopover.test.tsx`) covers the math + chart + popover surfaces — no new framework setup needed; helpers `compute_eval_confidence_bucket` (Wald-z) and `compute_confidence_bucket` (Wilson) are reused unchanged.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Visual parity with Openings ExplorerTab score bullet | D-16, "match Openings page visual language exactly" | Subjective visual — diff requires side-by-side eyeballing | Open `/openings` and `/endgames` in dev; confirm score-bullet domain, neutral band, colors are visually identical |
| Mobile ordering & stacking | D-04, D-17 | Layout responsiveness needs viewport resize | Resize browser to <`lg` (≤1024px); confirm tiles stack vertically with entry-eval first, score second |
| Concept-accordion paragraph wording | D-13 | Final copy iterated with the user during execution | Open the `endgame-concepts-trigger` accordion; confirm two new paragraphs read naturally and use "we can't tell" framing; Tile 2 paragraph references "Opponent Strength filter" as plain text |
| Popover content (n, p-value, verdict, methodology) | D-03, "n + p inside popover only" | Hover-state behavior + copy review | Hover/tap each tile's info icon; confirm `BulletConfidencePopover` (with `color="white"`) and `ScoreConfidencePopover` (without `lastPlayedAt`) show n, p, CI, verdict |
| Three-state color verdict | D-09, D-10 | Cross-user data check | Impersonate users with (a) sig positive entry eval, (b) sig negative, (c) p≥0.05 — verify green/red/neutral |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies (tasks in 81-01..81-04 all have `<automated>` blocks; 81-05 is a manual UAT checkpoint by design)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify (every task in execution waves 1-3 has `<automated>` verify)
- [x] Wave 0 covers all MISSING references (5 new test files / extensions enumerated above)
- [x] No watch-mode flags (all FE test commands use `-- --run`)
- [x] Feedback latency < 30s (per-surface quick commands ~15-30s)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-05-09 (post-revision after plan-checker BLOCKER 1+2 + WARNINGS 1-6 fixes)
