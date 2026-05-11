---
phase: 82
slug: llm-prompt-awareness-of-endgame-start-vs-end-metrics
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-10
---

# Phase 82 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Backend framework** | pytest 8.x (`uv run pytest`) |
| **Frontend framework** | Vitest |
| **Type check** | `uv run ty check app/ tests/` |
| **Backend quick run** | `uv run pytest tests/services/test_insights_service.py tests/services/test_insights_llm.py tests/test_endgame_zones.py -x` |
| **Backend full suite** | `uv run pytest` |
| **Frontend quick run** | `npm test -- --run frontend/src/lib/__tests__/endgameEntryEvalZones.test.ts frontend/src/components/charts/__tests__/EndgameStartVsEndSection.test.tsx` |
| **Frontend full suite** | `npm test` |
| **Estimated quick runtime** | ~30 seconds (backend) + ~10 seconds (frontend) |

---

## Sampling Rate

- **After every task commit:** Run the relevant quick command (backend or frontend depending on the file changed).
- **After every plan wave:** Run backend full suite + frontend full suite + ty check.
- **Before `/gsd-verify-work`:** Full backend + frontend suites must be green; `uv run ty check app/ tests/` must report zero errors.
- **Max feedback latency:** 60 seconds (combined quick runs).

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Behavior | Test Type | Automated Command | File Exists |
|---------|------|------|----------|-----------|-------------------|-------------|
| 82-01-* | 01 | 1 | MetricId / SubsectionId rename type-checks | type | `uv run ty check app/ tests/` | ✅ existing |
| 82-01-* | 01 | 1 | `_findings_score_timeline` emits renamed metrics | unit | `uv run pytest tests/services/test_insights_llm.py -k "score_timeline" -x` | ✅ existing (needs update) |
| 82-01-* | 01 | 1 | `entry_eval_pawns` ZoneSpec classifies at ±0.50 boundaries | unit | `uv run pytest tests/test_endgame_zones.py -k "entry_eval" -x` | ❌ Wave 0 |
| 82-01-* | 01 | 1 | `endgame_score` ZoneSpec classifies at ±0.45/0.55 boundaries | unit | `uv run pytest tests/test_endgame_zones.py -k "endgame_score and zone" -x` | ❌ Wave 0 |
| 82-01-* | 01 | 1 | `_findings_endgame_start_vs_end` populated case (both n≥10) | unit | `uv run pytest tests/services/test_insights_service.py -k "endgame_start_vs_end" -x` | ❌ Wave 0 |
| 82-01-* | 01 | 1 | `_findings_endgame_start_vs_end` empty case (both n<10) | unit | `uv run pytest tests/services/test_insights_service.py -k "endgame_start_vs_end_empty" -x` | ❌ Wave 0 |
| 82-02-* | 02 | 2 | `_PROMPT_VERSION == "endgame_v23"` | unit | `uv run pytest tests/services/test_insights_llm.py -k "prompt_version" -x` | ✅ existing (needs update) |
| 82-02-* | 02 | 2 | Glossary entries for `entry_eval_pawns` + `endgame_score` present | unit | `uv run pytest tests/services/test_insights_llm.py -k "glossary" -x` | ✅ existing (needs extension) |
| 82-02-* | 02 | 2 | Mapping table includes `endgame_start_vs_end \| overall` row | unit | `uv run pytest tests/services/test_insights_llm.py -k "mapping_table" -x` | ✅ existing (needs extension) |
| 82-02-* | 02 | 2 | Subsection block for `endgame_start_vs_end` rendered | unit | `uv run pytest tests/services/test_insights_llm.py -k "endgame_start_vs_end_block" -x` | ❌ Wave 0 |
| 82-03-* | 03 | 2 | Frontend ENDGAME_ENTRY_EVAL_NEUTRAL constants = ±0.50 | unit | `npm test -- --run frontend/src/lib/__tests__/endgameEntryEvalZones.test.ts` | ✅ existing (needs update) |
| 82-03-* | 03 | 2 | Tile-color rule: `(zone in [strong\|weak]) AND p<0.05` colors | unit | `npm test -- --run frontend/src/components/charts/__tests__/EndgameStartVsEndSection.test.tsx` | ✅ existing (needs update) |
| 82-03-* | 03 | 2 | Borderline value (e.g. +0.46, p<0.001) renders neutral | unit | same as above | ✅ existing (needs new case) |
| 82-04-* | 04 | 3 | Live insights endpoint narrates both findings | manual | `bin/run_local.sh` + browser visit `/endgames` + inspect LLM narration | manual |
| 82-04-* | 04 | 3 | CHANGELOG entry under `## [Unreleased]` | grep | `grep -F "endgame_start_vs_end" CHANGELOG.md` | ✅ existing |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/services/test_insights_service.py` — add `TestFindingsEndgameStartVsEnd` class with cases: populated (both n≥10), empty (both n<10), mixed sparse (one tile empty), zone classification (entry_eval in strong/weak/typical, endgame_score in strong/weak/typical).
- [ ] `tests/test_endgame_zones.py` (or wherever `assign_zone` is currently tested) — add boundary tests for `entry_eval_pawns` at ±0.50 and `endgame_score` at 0.45 / 0.55.
- [ ] `tests/services/test_insights_llm.py` — add subsection-block test for `endgame_start_vs_end` rendering; update existing `score_timeline` assertions for renamed metric IDs; update `_PROMPT_VERSION` assertion to `endgame_v23`.
- [ ] `frontend/src/components/charts/__tests__/EndgameStartVsEndSection.test.tsx` — add cases for the amended tile-color rule (sig + colored zone → colored; sig + neutral zone → neutral). Update existing `entry_eval_mean_pawns: 0.5` boundary case to `0.4` to remain a neutral input under ±0.50 (RESEARCH.md finding 5).

---

## Manual-Only Verifications

| Behavior | Why Manual | Test Instructions |
|----------|-----------|-------------------|
| LLM narration mentions "where you start" + "what you do with it" | LLM output is non-deterministic; visual review needed | Run `bin/run_local.sh`, log in to dev account with ≥10 endgame games, open `/endgames` page, click "Generate insights" (or equivalent), verify the rendered narration mentions both metrics. |
| Tile coloring matches LLM narration | Cross-component visual coherence check | On same `/endgames` view: verify that any tile rendered with green/red has corresponding LLM narration; any tile rendered neutral is either silent or narrated only via `[near edge]` suffix. |
| No regression on Conv/Parity/Recovery section | Side-by-side visual check | On `/endgames`: verify the existing Conv/Parity/Recovery cards still render and their LLM narration still appears. |

---

## Validation Sign-Off

- [ ] All tasks have an `<automated>` verify command or are listed under Manual-Only with rationale
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all `❌ Wave 0` references in the table above
- [ ] No watch-mode flags in command strings (Vitest uses `--run`, pytest is non-watch by default)
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter once gates pass

**Approval:** pending
