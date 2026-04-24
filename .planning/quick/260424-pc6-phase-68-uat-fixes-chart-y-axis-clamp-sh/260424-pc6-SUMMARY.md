---
quick_task: 260424-pc6-phase-68-uat-fixes
phase_context: 68-endgame-score-timeline-dual-line-shaded-gap
type: execute
completed: 2026-04-24
commits:
  - 4f150d8 fix(260424-pc6): clamp endgame score timeline y-axis to 20-80%
  - aecdebb fix(260424-pc6): render shaded score-timeline bands by dropping <g> wrapper
  - d5dae75 feat(260424-pc6): restructure score_timeline prompt emission (v14)
tags:
  - uat
  - endgame
  - frontend
  - charts
  - prompt
  - cache-invalidation
---

# Quick Task 260424-pc6 — Phase 68 UAT Fixes

Three concrete UAT fixes for Phase 68's dual-line endgame score timeline:
y-axis clamp, broken shaded band, and noisy/misleading prompt emission.

## Y-axis clamp (Task 1)

`SCORE_TIMELINE_Y_DOMAIN` in `frontend/src/components/charts/EndgamePerformanceSection.tsx`
flipped from `[0, 100]` to `[20, 80]`. `SCORE_TIMELINE_Y_TICKS` updated to
`[20, 30, 40, 50, 60, 70, 80]`. Matches the Time Pressure vs Performance
chart's `Y_AXIS_DOMAIN = [0.2, 0.8]` treatment; typical score values now
fill the plot area instead of hugging the middle of a 0-100 range.

`allowDataOverflow={false}` kept as-is. Task 2 did not need to flip it —
the diagnosis pointed elsewhere.

## Shaded-band diagnosis + fix (Task 2)

**Confirmed hypothesis: hypothesis 4 — `<g>` wrapper broke Recharts child discovery.**

Recharts' `generateCategoricalChart` discovers chart elements via
`findAllByType` over `React.Children.toArray(children)`. That helper
(`node_modules/recharts/lib/util/ReactUtils.js:88`) matches each direct
child's `type.displayName` against the target component type — it does
NOT recurse into DOM elements. A `<g data-testid="score-band-above">`
wrapper had React type `"g"` (string), which Recharts' scan skipped
entirely. The nested `<Area>` inside the `<g>` was therefore never
registered with the chart axes, and no `<path>` was ever emitted.

jsdom still rendered the `<g data-testid>` DOM node regardless of
whether any `<Area>`-produced path lived inside it, which is why the
existing testid-based tests passed while the browser rendered nothing.

**Fix:** drop the `<g>` wrappers. Render each `<Area>` as a DIRECT child
of `ComposedChart` and mark it via a dedicated className
(`SCORE_BAND_ABOVE_CLASS = 'score-band-above'` and `SCORE_BAND_BELOW_CLASS
= 'score-band-below'`, exported as module constants). Recharts forwards
the className onto its `<Layer>` via `clsx('recharts-area', className)`,
so tests can query the rendered SVG by class name.

Tests switched from `screen.getByTestId('score-band-above')` to
`container.querySelector(\`.${SCORE_BAND_ABOVE_CLASS}\`)`. Added one
regression test asserting that each rendered band layer actually
contains an SVG `<path>` — that assertion would have caught the
original bug because the pre-fix DOM had the `<g>` wrapper but no
inner path.

No need for hypothesis 2 (null-gap workaround) or hypothesis 3 (domain
clamp clipping). The ranged `[low, high]` tuple + null-gap pattern
works fine once the Area is discoverable.

## Prompt restructure (Task 3)

`score_timeline` subsection now emits three metrics per window instead
of two dim-tagged `score_gap` findings. The old shape emitted:

```
[summary score_gap | part=endgame]   ← labelled "gap" but carried absolute endgame %
[summary score_gap | part=non_endgame] ← labelled "gap" but carried absolute non-endgame %
```

which misled the LLM. The new shape emits one finding per distinct
metric id:

| Metric | Scalar value | Series payload | Headline eligible |
|---|---|---|---|
| `endgame_score` | mean endgame-side Score | per-week endgame_score | yes (trend gate) |
| `non_endgame_score` | mean non-endgame-side Score | per-week non_endgame_score | no (partner) |
| `score_gap` | aggregate score_difference | per-week signed gap | no (overall owns it) |

No `dimension` tag on any of them — each metric id is unique, so per-dim
fan-out is not needed to keep summary headers distinct. Deterministic
order: `endgame_score` → `non_endgame_score` → `score_gap`.

Decided to emit `gap_series` rather than leave it `None` — matches the
fanout convention of `endgame_metrics` / `conversion_recovery_by_type`
(one series per metric) and gives the LLM the gap's own trajectory
without forcing it to subtract two series mentally.

### Constant-n suppression

`_render_series_block` now detects when every point carries the same
`n`. When it does, a single `[n=<N> for every point]` disclosure line
sits after the series header and the per-point `(n=<N>)` suffix is
dropped. The `endgame_elo_gap` variant is exempt because its per-point
`gap=X, elo=Y (n=Z)` format still carries a variable `elo=` field.

This fires naturally on `score_timeline` series (rolling-100-game window
produces identical N per bucket) and does NOT fire on
`clock_diff_timeline` / `type_win_rate_timeline` / `endgame_elo_timeline`
whose per-bucket counts vary.

### Registry

New `MetricId` entries `endgame_score` and `non_endgame_score` in
`app/services/endgame_zones.py`. Both carry a full-range `[0, 1]`
typical band — there is no calibrated cohort band for "your endgame
Score in isolation" (the zoned signal is `score_gap`, not absolute
score), so every value resolves to `"typical"`. A matching guard in
`_format_zone_bounds` suppresses the `(typical …)` tag for these
metrics so the prompt does not show meaningless bounds.

### Prompt version

`_PROMPT_VERSION` bumped `endgame_v13` → `endgame_v14`. Cached LLM
reports from v13 invalidate automatically via the prompt-version cache
key.

### Documentation

`app/prompts/endgame_insights.md` §"How to read [summary] and [series]
blocks":

- Old paragraph about the two-part-dim-tagged shape replaced with a
  three-metric-summary description including literal `[summary
  endgame_score]` / `[summary non_endgame_score]` / `[summary
  score_gap]` examples.
- New paragraph describes the `[n=<N> for every point]` disclosure
  shortcut for constant-N series.
- Metric glossary adds per-metric entries for `endgame_score` and
  `non_endgame_score` right below `score_gap`, matching the brevity of
  existing entries.

## Files modified

- `frontend/src/components/charts/EndgamePerformanceSection.tsx` — y-axis
  clamp + drop `<g>` wrappers + export band class-name constants +
  expanded diagnosis comment on `EndgameScoreOverTimeChart`.
- `frontend/src/components/charts/__tests__/EndgamePerformanceSection.test.tsx`
  — switch testid assertions to className queries; add regression test
  proving each band emits an SVG `<path>`.
- `app/services/insights_service.py` — rewrite `_findings_score_timeline`
  to emit three findings per window keyed on distinct metrics.
- `app/services/insights_llm.py` — constant-n suppression in
  `_render_series_block`; `_format_zone_bounds` skip for the new
  per-part metrics; `_PROMPT_VERSION` bumped to `endgame_v14`.
- `app/services/endgame_zones.py` — `MetricId` Literal expanded;
  `ZONE_REGISTRY` entries added for `endgame_score` / `non_endgame_score`.
- `app/prompts/endgame_insights.md` — v14 emitter-shape documentation +
  new metric glossary entries.
- `tests/services/test_insights_llm.py` — all v13 literals bumped to
  v14; `TestPromptVersionAndBody` guards updated (both positive and
  negative invariants); `test_user_prompt_shape` rewritten for the 3-
  metric shape; renamed `test_score_timeline_emits_two_summaries_…` to
  `test_score_timeline_emits_three_summaries_three_series_deterministic_order`
  with new assertions; new regression tests
  `test_constant_n_series_emits_disclosure_and_drops_per_point_suffix`
  and `test_variable_n_series_keeps_per_point_suffix`.
- `tests/services/test_insights_service_series.py` — renamed
  `test_score_timeline_emits_two_findings_per_window` to
  `test_score_timeline_emits_three_findings_per_window`; rewrote
  `test_score_timeline_series_uses_absolute_per_side_values` for the
  3-metric shape; rewrote the end-to-end `TestScoreTimelineIntegration`
  test for the new shape.
- `tests/services/test_endgame_zones.py` — sanity test's expected
  ZONE_REGISTRY key set includes the two new per-part metrics.
- `tests/test_insights_router.py` — bumped three v13 literals to v14.

## Verification

- `npm run lint` / `npm run build` / `npm run knip` — clean.
- `npm test` — 107/107 passed across 9 test files (including the new
  band-path regression guard).
- `uv run ruff check app/ tests/` — clean.
- `uv run ty check app/ tests/` — clean.
- `uv run pytest tests/services/test_insights_llm.py
  tests/services/test_insights_service_series.py
  tests/services/test_insights_service.py tests/test_insights_router.py` —
  118/118 passed.
- `uv run pytest` (full suite) — 1059/1067 passed.

## Deferred Issues

`tests/test_reclassify.py` (8 tests) fails independently of this task
with `ForeignKeyViolationError` on `games.user_id=1`. Verified
pre-existing on the branch via `git stash` — running the file in
isolation against the clean Phase 68 base (commit 80bde9b) produces
the same 8 failures. Out of scope per quick-task constraints; flagged
here for a future fixture-fix quick task.

## Tests (UAT, pending manual verification by user)

The five pending items in
`.planning/phases/68-endgame-score-timeline-dual-line-shaded-gap/68-HUMAN-UAT.md`
should be manually verified by the user running the dev environment:

1. Y-axis shows 20/30/40/50/60/70/80 tick labels on the score timeline.
2. Mobile layout unchanged.
3. Info popover content unchanged from Phase 68 Plan 02.
4. Tooltip behavior unchanged.
5. LLM report narrates with neutral per-part labels; `prompt_version`
   in `llm_logs` = `endgame_v14`; no `(n=N)` repetition on every
   bucket; `[n=<N> for every point]` disclosure visible.

UAT flip not automated per plan instructions — let the user drive the
flip after manual verification.

## Self-Check: PASSED

- Commits present in git log: `git log --oneline -4`
  - `d5dae75 feat(260424-pc6): restructure score_timeline prompt emission (v14)`
  - `aecdebb fix(260424-pc6): render shaded score-timeline bands by dropping <g> wrapper`
  - `4f150d8 fix(260424-pc6): clamp endgame score timeline y-axis to 20-80%`
- `_PROMPT_VERSION = "endgame_v14"` present in `app/services/insights_llm.py`.
- `[summary endgame_score]` / `[summary non_endgame_score]` / `[summary
  score_gap]` present in `app/prompts/endgame_insights.md`.
- `[n=<N> for every point]` disclosure documented in the prompt file.
- Frontend + backend test suites green (excluding the pre-existing,
  unrelated `test_reclassify.py` failures).
