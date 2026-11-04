---
quick_id: 261104-hxl
mode: quick
phase: quick-261104-hxl
plan: 01
type: execute
wave: 1
depends_on: []
autonomous: true
requirements: ["QUICK-261104-hxl"]
files_modified:
  - app/services/opening_insights_service.py
  - app/schemas/opening_insights.py
  - tests/services/test_opening_insights_service.py
  - frontend/src/types/insights.ts
  - frontend/src/components/openings/stats/PlayedBeforeToggle.tsx
  - frontend/src/components/openings/stats/RepertoireList.tsx
  - frontend/src/components/openings/stats/OpeningFindings.tsx
  - frontend/src/lib/analytics.ts
  - frontend/src/components/openings/__tests__/OpeningFindings.test.tsx
  - frontend/src/pages/openings/StatsTab.tsx
  - CHANGELOG.md

estimate:
  tokens: 70000
  raw_tokens: 70000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "Each findings section (Moves that Work, Moves that Cost You) returns up to 10 current-repertoire findings no matter how many stale findings rank above them, plus up to 10 stale findings, each group in Wilson-bound order"
    - "On Opening Stats, stale findings (is_current false) no longer sit among the top cards: they live in a per-section 'Played before (n)' group, collapsed by default, showing all its cards (max 10) when expanded, with no nested 'N more'"
    - "Expanding a findings 'Played before' group sends exactly one panel-open event with target 'opening-insights-played-before'; collapsing, mounting and auto-expanding send none"
    - "A section with zero current but some stale findings shows 'Nothing stands out as {Color} in your current repertoire yet.' and renders its 'Played before' group already open"
    - "The merged 'Moves that Stand Out' empty block appears only when both sections have neither current nor stale findings; a section with neither keeps 'Nothing stands out as {Color} yet.'"
    - "The repertoire 'Played before' toggle renders and tracks exactly as before, now through the shared component"
  artifacts:
    - path: "app/services/opening_insights_service.py"
      provides: "CURRENT_FINDINGS_CAP and STALE_FINDINGS_CAP; _partition_section returning capped current group then capped stale group"
      contains: "STALE_FINDINGS_CAP: int = 10"
    - path: "frontend/src/components/openings/stats/PlayedBeforeToggle.tsx"
      provides: "Shared 'Played before (n)' collapsible toggle used by RepertoireList and OpeningFindings"
      exports: ["PlayedBeforeToggle"]
    - path: "frontend/src/components/openings/stats/OpeningFindings.tsx"
      provides: "Per-section split by is_current with a collapsed stale group"
      contains: "PlayedBeforeToggle"
    - path: "frontend/src/lib/analytics.ts"
      provides: "Registered panel target for the findings Played before expand"
      contains: "opening-insights-played-before"
  key_links:
    - from: "app/services/opening_insights_service.py _partition_section"
      to: "frontend/src/components/openings/stats/OpeningFindings.tsx FindingsSubsection"
      via: "the four response lists carry both groups; the frontend splits on the existing is_current flag"
      pattern: "is_current"
    - from: "frontend/src/components/openings/stats/OpeningFindings.tsx"
      to: "frontend/src/components/openings/stats/PlayedBeforeToggle.tsx"
      via: "import { PlayedBeforeToggle }"
      pattern: "PlayedBeforeToggle"
    - from: "frontend/src/components/openings/stats/RepertoireList.tsx"
      to: "frontend/src/components/openings/stats/PlayedBeforeToggle.tsx"
      via: "import { PlayedBeforeToggle } with testId repertoire-played-before-toggle"
      pattern: "PlayedBeforeToggle"
    - from: "frontend/src/components/openings/stats/OpeningFindings.tsx"
      to: "frontend/src/lib/analytics.ts PANEL_TARGETS"
      via: "trackFeature('panel-open', { target: 'opening-insights-played-before' })"
      pattern: "opening-insights-played-before"
---

# Quick 261104-hxl: hide stale moves in Opening Stats findings behind "Played before"

<objective>
In Opening Stats, "Moves that Work" and "Moves that Cost You" show the backend's top 10 findings per
section with current-repertoire and stale (not played recently) moves mixed in Wilson-bound order (D-38).
Stale moves ranked above current ones crowd current moves out of the 10. This task (1) makes the backend
cap the two groups separately: up to 10 current plus up to 10 stale per section (locked decision 1,
partially reversing D-38), and (2) makes the frontend show only current moves in the main grid, with the
stale ones in a per-section collapsed "Played before (n)" group that mirrors the repertoire's Most Played
"Played before" toggle (locked decisions 2 and 3), plus tests and a changelog bullet (locked decision 4).

Purpose: the top cards answer "what works / costs me in what I play now"; older lines stay one click away.
Output: backend partition + tests, shared PlayedBeforeToggle, per-section stale group + tests, CHANGELOG bullet.

Locked decisions (from /gsd-explore, do not revisit) are cited below as LD-1..LD-4, matching the numbered
list in the quick-task brief.

Shape note: tracer-first is not applied. The end-to-end wire this task depends on (is_current stamped on
every finding by the backend and rendered by FindingCard) has shipped since Phase 242, and the backend and
frontend halves are each independently testable against it, so a thin end-to-end slice would add no
information. Task 1 (backend) and Task 2 (frontend) do not depend on each other; Task 3 closes out.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@CLAUDE.md
@frontend/CLAUDE.md
@app/services/opening_insights_service.py
@app/schemas/opening_insights.py
@frontend/src/components/openings/stats/OpeningFindings.tsx
@frontend/src/components/openings/stats/RepertoireList.tsx

Interface facts the executor needs (verified at HEAD 7827334e4):

- `app/services/opening_insights_service.py`: module docstring line 7 says "top 10 per section in that
  order, any confidence (D-38)"; the card-cap constant block is at lines 67-72 (`FINDINGS_CARD_CAP: int = 10`
  with a D-37/D-38 comment); `_partition_section(ranked: list[OpeningInsightFinding]) -> list[OpeningInsightFinding]`
  at line 845 returns the first 10; `_build_sections` docstring at ~line 952 mentions the cap and the eval
  enrichment ("at most ... per section"). `_build_sections` calls `_partition_section` per section and runs
  `_fetch_eval_metrics` on the partition output only (Pitfall 8), so enrichment automatically follows the
  new group sizes with no other change.
- `app/schemas/opening_insights.py`: `OpeningInsightFinding.is_current` field comment at lines 108-110
  ("False adds the card's 'Not played recently' archive icon; it does not change the card order") and the
  `OpeningInsightsResponse` docstring at lines 115-124 (names the cap, "at most ... (10) findings each").
- `tests/services/test_opening_insights_service.py`: imports the cap constant and `_partition_section` at
  lines 35-42; partition tests at lines 1496-1534 (`_finding_for(name, *, confidence, is_current=True, p_value)`
  helper at 1479, `_names` at 1492); `test_partition_caps_without_moving_current_findings_first` (line 1517)
  asserts the old mixed cap and must be replaced; end-to-end test
  `test_card_list_is_capped_in_wilson_order_and_eval_runs_on_cards_only` (line 1579) asserts 10 cards with
  one stale among them and must be updated. `_rows_with_n`, `_patch_confidence_by_n`, `_run_compute`,
  `LONG_AGO`/`RECENT`/`CUTOFF` and the `mock_resolve_cutoffs` fixture already exist. At equal score 0.30 a
  weakness ranks larger n first (the Wilson upper bound falls with n).
- `RepertoireList.tsx`: local `PlayedBeforeToggle({count, hint, expanded, onToggle})` at lines 53-83 uses
  `GROUP_HEADING_CLASS` (line 20, used nowhere else in the file), `cn`, `ChevronDown` (rotates 180deg when
  expanded), `aria-expanded`, and hard-codes `data-testid="repertoire-played-before-toggle"`. Its expand
  handler tracks `trackFeature('panel-open', { target: 'opening-stats-more' })` on expand only. The group
  wrapper is `<div className="space-y-2" data-testid="repertoire-group-played-before">`.
- `OpeningFindings.tsx`: `FindingCardGrid` (first `INITIAL_VISIBLE_PER_SECTION` = 4 cards plus `ShowMoreButton`,
  tracks `opening-insights-more`) renders cards with testId `${testId}-card-${i}` inside
  `${testId}-list`, where `testId = opening-findings-${kind}`; `FindingsSubsection` picks grid vs the
  `${testId}-empty` line "Nothing stands out as {Color} yet."; `FindingsSections` renders `MergedEmpty`
  when every section's `cards` list is empty. `FindingCard` already marks `!finding.is_current` with the
  `${testId}-stale-icon` ("Not played recently").
- `frontend/src/lib/analytics.ts`: `PANEL_TARGETS` const array at lines 364-378 (contains
  `'opening-insights-more'`, `'opening-stats-more'`); `analytics.test.ts` checks every entry is a kebab slug.
- No `StatsTab`/`RepertoireList` remount on colour switch: component state persists across the White/Black
  switch, so derived open state must react to the current colour's data (see Task 2).
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Backend caps current and stale findings separately (LD-1)</name>
  <files>app/services/opening_insights_service.py, app/schemas/opening_insights.py, tests/services/test_opening_insights_service.py, frontend/src/types/insights.ts</files>
  <read_first>app/services/opening_insights_service.py (lines 1-12, 60-75, 840-860, 945-975), app/schemas/opening_insights.py (lines 100-130), tests/services/test_opening_insights_service.py (lines 20-45, 1468-1615), frontend/src/types/insights.ts (lines 100-112)</read_first>
  <behavior>
    - 3 stale findings ranked above 12 current findings: `_partition_section` returns 13 findings, the first 10 current ones in ranked order followed by all 3 stale ones in ranked order (current cap is independent of the stale count).
    - 2 current and 12 stale findings: returns the 2 current then the first 10 stale in ranked order (stale capped at its own cap).
    - Interleaved current/stale input: relative Wilson order is preserved within each group; output is the current group then the stale group.
    - All-current input keeps every confidence in ranked order (existing `test_partition_keeps_every_confidence_in_wilson_order` still passes unchanged); empty input returns an empty list.
    - End to end through compute_insights: 14 same-score weakness rows with sizes 100, 110, ..., 230 where the rows at index 0 and 2 (sizes 100 and 120) were played long ago and the other 12 recently: the white_weaknesses list holds 12 findings, the 10 current ones being sizes 140-230 (sizes 110 and 130 are cut), the 2 stale ones sizes 100 and 120; the eval batch is called once and its hashes equal exactly the 12 returned findings' resulting_full_hash values.
  </behavior>
  <action>
    Write the tests first (RED), then implement (GREEN), per LD-1.

    Tests in tests/services/test_opening_insights_service.py: change the import of the old single cap constant to the two new constants. Replace test_partition_caps_without_moving_current_findings_first with three tests covering the first three behavior bullets (suggested names: test_partition_caps_current_independently_of_stale, test_partition_caps_stale_at_its_own_cap, test_partition_keeps_wilson_order_within_each_group), built with the existing `_finding_for` helper (is_current=False for stale) and asserted with `_names`, and assert the caps equal 10 via the new constants (e.g. CURRENT_FINDINGS_CAP == 10 and STALE_FINDINGS_CAP == 10). Update test_card_list_is_capped_in_wilson_order_and_eval_runs_on_cards_only to the 14-row scenario in the last behavior bullet (sizes list of 14, played list LONG_AGO, RECENT, LONG_AGO then 11 RECENT, a bucket entry for every size as today); rename its docstring to describe the separate caps; assert the 12 returned n_games, the current/stale split by is_current, and that the queried eval hashes equal the returned card hashes (count CURRENT_FINDINGS_CAP + 2). Leave the other partition tests as they are. Run the tests and confirm the new ones fail before implementing.

    Implementation in app/services/opening_insights_service.py: replace the single card-cap constant with two named constants, CURRENT_FINDINGS_CAP: int = 10 and STALE_FINDINGS_CAP: int = 10, and rewrite the comment above them: the top findings by direction-aware Wilson bound, any confidence (D-37/D-38), capped separately for current-repertoire and stale findings because stale findings ranked above current ones crowded current ones out of a shared 10 (quick 261104-hxl, 2026-11-04, partially reverses D-38's no-current-first rule); the frontend shows the stale group in a collapsed "Played before" group and still owns how many current cards show before "N more". Rewrite `_partition_section` to filter the ranked list into current (is_current True) and stale (is_current False) in one pass each, slice each to its own cap, and return the current slice followed by the stale slice; no re-sort, so Wilson order is kept within each group. Keep the signature and return type. Update its docstring to say exactly this and that the full ranked list is already in memory (no second fetch). Update the module docstring line 7 to "top 10 current plus top 10 stale findings per section, each in that order, any confidence". Update the `_build_sections` docstring so the cap wording names both caps and the enrichment bound reads "at most CURRENT_FINDINGS_CAP + STALE_FINDINGS_CAP per section". Make sure no remaining reference to the old constant name is left in app/ or tests/.

    Schema app/schemas/opening_insights.py: update the is_current field comment to say False puts the card in the section's collapsed "Played before" group on the frontend (and still adds the "Not played recently" icon), and that the backend caps current and stale findings separately. Update the OpeningInsightsResponse docstring: each list holds up to CURRENT_FINDINGS_CAP (10) current findings followed by up to STALE_FINDINGS_CAP (10) stale ones, each group in direction-aware Wilson order, any confidence; the frontend splits them on is_current.

    Frontend type comment frontend/src/types/insights.ts: mirror the schema wording on the is_current comment (False means the card shows in the section's "Played before" group; the backend lists current findings first). Comment-only change, no type change.
  </action>
  <verify>
    <automated>uv run pytest tests/services/test_opening_insights_service.py tests/routers/test_insights_openings.py -q && uv run ruff check app/services/opening_insights_service.py app/schemas/opening_insights.py tests/services/test_opening_insights_service.py && uv run ty check app/ tests/ scripts/ && grep -q "STALE_FINDINGS_CAP: int = 10" app/services/opening_insights_service.py && grep -q "CURRENT_FINDINGS_CAP: int = 10" app/services/opening_insights_service.py</automated>
  </verify>
  <done>Both caps exist as named constants (neither "STALE_FINDINGS_CAP: int = 10" nor "CURRENT_FINDINGS_CAP: int = 10" matches at HEAD; both match after); `_partition_section` returns up to 10 current then up to 10 stale in Wilson order; the new and updated tests pass, the old mixed-cap test is gone, ty reports zero errors, and every docstring/comment named above describes the separate caps.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Per-section "Played before (n)" group in Opening Findings via a shared toggle (LD-2, LD-3, LD-4)</name>
  <files>frontend/src/components/openings/stats/PlayedBeforeToggle.tsx, frontend/src/components/openings/stats/RepertoireList.tsx, frontend/src/components/openings/stats/OpeningFindings.tsx, frontend/src/lib/analytics.ts, frontend/src/components/openings/__tests__/OpeningFindings.test.tsx</files>
  <read_first>frontend/src/components/openings/stats/OpeningFindings.tsx, frontend/src/components/openings/stats/RepertoireList.tsx (lines 1-83, 149-224), frontend/src/components/openings/__tests__/OpeningFindings.test.tsx, frontend/src/components/openings/__tests__/RepertoireList.test.tsx (lines 185-225), frontend/src/lib/analytics.ts (lines 364-379)</read_first>
  <behavior>
    - A section with 2 current and 3 stale findings: the main grid renders only the current ones (`opening-findings-weakness-card-0` and `-card-1`, no `-card-2`); `opening-findings-weakness-played-before-toggle` reads "Played before (3)" with aria-expanded "false" and no `opening-findings-weakness-played-before-card-*` is rendered.
    - Stale findings never count toward "N more": 4 current plus 3 stale renders no `opening-findings-weakness-btn-more`.
    - Clicking the toggle with 1 current and 10 stale shows `opening-findings-weakness-played-before-card-0` through `-card-9` in a 2-column grid, renders no nested `opening-findings-weakness-played-before-btn-more`, flips aria-expanded to "true" and records exactly one panel-open event with target 'opening-insights-played-before'; clicking again collapses and records nothing more.
    - A stale card in the group keeps its archive icon: after expanding, `opening-findings-strength-played-before-card-0-stale-icon` has aria-label "Not played recently"; current cards have none.
    - Zero current and 2 stale (White, weakness): `opening-findings-weakness-empty` reads "Nothing stands out as White in your current repertoire yet.", the toggle starts with aria-expanded "true", both stale cards are visible, and no panel-open event is recorded (auto-open is not a user action).
    - Only stale findings in one section and nothing in the other: no `opening-findings-empty` block; the other section shows "Nothing stands out as White yet."; both subsections render. With all four lists empty, the existing merged-empty test still passes.
    - No toggle renders for a section without stale findings.
    - RepertoireList tests pass unchanged (same `repertoire-played-before-toggle` testid, "Played before (3)" text, cutoff hint, 'opening-stats-more' tracking).
  </behavior>
  <action>
    Write or adjust the OpeningFindings tests first (RED), then implement (GREEN).

    Tests (frontend/src/components/openings/__tests__/OpeningFindings.test.tsx, per LD-4): add a describe block "OpeningFindings Played before (stale findings)" with one test per behavior bullet above (use the existing makeFinding with is_current: false for stale ones and the existing panelOpenTargets helper). Rewrite the existing test "shows when each finding was last played and marks older ones with the archive icon": the stale card now lives in the played-before group, so assert the current card-0 has a last-played date and no stale icon, then expand `opening-findings-strength-played-before-toggle` and assert the stale icon on `opening-findings-strength-played-before-card-0`. Update the file's header comment to mention the Played before group. Keep every other existing test as is.

    Shared toggle (LD-2, extract instead of duplicating): create frontend/src/components/openings/stats/PlayedBeforeToggle.tsx exporting only the PlayedBeforeToggle component (react-refresh/only-export-components), moved verbatim from RepertoireList.tsx with its group-heading class constant (kept module-local, not exported). Props: count (number), expanded (boolean), onToggle (() => void), testId (string, becomes data-testid) and an optional hint (string, rendered only when non-empty as today). Add a one-line doc comment saying it is the collapsed "Played before (n)" heading shared by the repertoire and the move findings. In RepertoireList.tsx delete the local component and the now-unused heading class constant, import the shared one, and pass testId "repertoire-played-before-toggle" plus the existing hint. At HEAD both the ChevronDown icon import and the cn import in RepertoireList.tsx are used only by the moved component, so they move with it (keep Sparkles); eslint/knip flag any leftover. Rendering and tracking of the repertoire stay the same.

    Analytics: add 'opening-insights-played-before' to PANEL_TARGETS in frontend/src/lib/analytics.ts right after 'opening-insights-more' (enumerated literal, D-04; new target, existing names untouched per D-01).

    OpeningFindings.tsx (LD-2, LD-3):
    - Hoist the grid class string used by FindingCardGrid into a module constant (e.g. FINDING_GRID_CLASS, same value) and reuse it for the stale grid.
    - Add a PlayedBeforeGroup component taking the stale findings, the section testId, an autoExpand flag, and the two open callbacks. Hold a nullable user override in state (null until the user clicks); the effective open state is the override when set, otherwise autoExpand. This keeps auto-open reactive when the colour switch or a filter change swaps the data (the component is not remounted on colour switch) and never tracks on mount (D-03). The toggle handler computes the next state from the effective one, calls trackFeature('panel-open', { target: 'opening-insights-played-before' }) only when opening, then stores the override. Render a wrapper div with className "space-y-2" and data-testid `${testId}-played-before`, the shared PlayedBeforeToggle with count = stale length and testId `${testId}-played-before-toggle` (no hint: the insights response carries no cutoff date), and, when open, the grid with data-testid `${testId}-played-before-list` holding every stale FindingCard with testId `${testId}-played-before-card-${i}` (no "N more" inside the group; the backend caps stale at 10).
    - FindingsSubsection: split the section's cards into current (is_current true) and stale (is_current false). Body: current non-empty renders FindingCardGrid with the current cards only (its "N more" counts current cards only); current empty renders the `${testId}-empty` line, worded "Nothing stands out as {Color} in your current repertoire yet." when stale is non-empty and "Nothing stands out as {Color} yet." when it is empty. Pull the empty-line choice into a small helper or component so FindingsSubsection stays flat (no nested ternary, max-depth 4). After the body, render PlayedBeforeGroup when stale is non-empty, with autoExpand true when current is empty.
    - FindingsSections keeps its merged-empty check on the full per-section list (both groups), which already means "no current and no stale in either section"; add a short comment saying so.
    - Update the OpeningFindings component doc comment: each section shows the backend's top 10 current findings (first four, rest behind "N more") and up to 10 stale ones in a collapsed "Played before (n)" group, opened from the start when the section has no current findings.
    Mobile: OpeningFindings is the only renderer of FindingCard and has one responsive layout, so there is no second markup to update.
  </action>
  <verify>
    <automated>cd frontend && npm test -- src/components/openings/__tests__/OpeningFindings.test.tsx src/components/openings/__tests__/RepertoireList.test.tsx src/lib/__tests__/analytics.test.ts && npm run lint && grep -q "opening-insights-played-before" src/lib/analytics.ts && grep -q "PlayedBeforeToggle" src/components/openings/stats/OpeningFindings.tsx</automated>
  </verify>
  <done>OpeningFindings shows only current cards in each section's grid, stale cards behind a collapsed "Played before (n)" toggle (auto-open when the section has no current cards), one panel-open event per user expand with the new registered target, the merged empty block only when both sections are fully empty; RepertoireList renders through the shared PlayedBeforeToggle with unchanged tests; vitest and eslint (max-depth 4) pass. At HEAD neither "opening-insights-played-before" in analytics.ts nor "PlayedBeforeToggle" in OpeningFindings.tsx matches; both match after.</done>
</task>

<task type="auto">
  <name>Task 3: Changelog bullet, stale comment fix, and the verification sweep (LD-4)</name>
  <files>CHANGELOG.md, frontend/src/pages/openings/StatsTab.tsx</files>
  <read_first>CHANGELOG.md (lines 1-40), frontend/src/pages/openings/StatsTab.tsx (lines 140-152)</read_first>
  <action>
    CHANGELOG.md (LD-4): add one user-facing bullet as the first item under "### Changed" in "## [Unreleased]", no em-dash, wording along the lines of: Openings Stats: in "Moves that Work" and "Moves that Cost You", moves you have not played recently now sit in a collapsed "Played before" group under each list, so the up to 10 cards on top all come from your current repertoire. Keep the exact phrase "Moves that Cost You" in the bullet.

    frontend/src/pages/openings/StatsTab.tsx: the JSX comment above the OpeningFindings element says "top 10 per section"; reword it to "top 10 current findings per section plus a collapsed Played before group, the 95% gate only colours them (D-38)". Comment-only.

    Then run the quick-task verification sweep and fix anything it reports: uv run ruff format app/ tests/ scripts/ (apply), uv run ruff check ., uv run ty check app/ tests/ scripts/, uv run python scripts/check_function_size.py app/ --fail-over-depth 4, and in frontend/ npm run lint, npm run build (tsc -b catches prop/type drift from the extracted component), the openings test folder, and npm run knip (the new PlayedBeforeToggle export must be imported by both RepertoireList and OpeningFindings). If ruff format changes files, include them in a style(...) commit.
  </action>
  <verify>
    <automated>grep -q "Moves that Cost You" CHANGELOG.md && uv run ruff format --check app/ tests/ scripts/ && uv run ruff check . && uv run ty check app/ tests/ scripts/ && uv run python scripts/check_function_size.py app/ --fail-over-depth 4 && cd frontend && npm run lint && npm run build && npm test -- src/components/openings src/lib/__tests__/analytics.test.ts && npm run knip</automated>
  </verify>
  <done>CHANGELOG [Unreleased] has the new Changed bullet ("Moves that Cost You" has no match in CHANGELOG.md at HEAD and matches after); the StatsTab comment matches the new behaviour; ruff format/check, ty, the nesting-depth gate, frontend lint, build, the openings tests and knip all pass.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| API -> browser | GET opening insights returns the authenticated user's own findings; unchanged endpoint, unchanged auth |
| browser -> Umami | panel-open feature event leaves the browser |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-261104-01 | Denial of service | `_build_sections` eval enrichment | low | mitigate | Enrichment stays bounded by the two named caps (at most 20 findings per section, 40 per colour) and still runs on the partition output only, never the uncapped ranked list (Pitfall 8); asserted by the updated end-to-end test that checks the eval batch hashes equal the returned cards |
| T-261104-02 | Information disclosure | `trackFeature` panel-open target | low | mitigate | Target is the enumerated literal 'opening-insights-played-before' registered in PANEL_TARGETS (D-04); no SAN, FEN, opening name or ids in the event; the registry type makes a free-form value a build error |
| T-261104-03 | Information disclosure | insights response | low | accept | No new fields: the response already carried stale findings and is_current; only list lengths change. Hashes stay stringified as before |
| T-261104-SC | Tampering | npm/pip installs | low | accept | No package installs in this plan; nothing to gate |
</threat_model>

<verification>
- `uv run pytest tests/services/test_opening_insights_service.py tests/routers/test_insights_openings.py -q` passes.
- `cd frontend && npm test -- src/components/openings src/lib/__tests__/analytics.test.ts` passes.
- `uv run ruff check .`, `uv run ty check app/ tests/ scripts/`, `uv run python scripts/check_function_size.py app/ --fail-over-depth 4` clean.
- `cd frontend && npm run lint && npm run build && npm run knip` clean.
- Manual spot check (optional, dev server): on Openings > Stats a colour with older lines shows "Played before (n)" under each findings list, collapsed; a colour whose findings are all older shows the "in your current repertoire" line with the group open.
</verification>

<success_criteria>
- Backend: each of the four lists holds up to 10 current findings then up to 10 stale findings, Wilson order within each group, capped by CURRENT_FINDINGS_CAP and STALE_FINDINGS_CAP; all D-38 comments/docstrings updated.
- Frontend: stale findings only appear inside a per-section collapsed "Played before (n)" group that looks like the repertoire's, through one shared component; auto-open when a section has no current findings; merged empty only when everything is empty; one tracked expand per user click.
- Tests cover every behaviour listed in Tasks 1 and 2; CHANGELOG carries the bullet.
</success_criteria>

<output>
Create `.planning/quick/261104-hxl-hide-stale-moves-in-opening-findings-beh/261104-hxl-SUMMARY.md` when done
</output>
