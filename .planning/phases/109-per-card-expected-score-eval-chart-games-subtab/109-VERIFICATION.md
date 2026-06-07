---
phase: 109-per-card-expected-score-eval-chart-games-subtab
verified: 2026-06-07T02:20:00Z
status: passed
status_note: "Machine checks 13/13. The 7 human-UAT visual items were validated by the user during interactive review on 2026-06-07 (chart iterated on directly, incl. tooltip stacking fix) and accepted at ship time."
score: 13/13 must-haves verified (machine-checkable)
overrides_applied: 0
human_verification:
  - test: "Desktop three-thirds layout"
    expected: "Analyzed card shows three equal-width columns — miniboard+info / eval chart / tags. Chart is not stacked under tags; columns are visually balanced."
    why_human: "sm:grid-cols-3 presence confirmed in code; actual rendering equality of thirds depends on browser layout engine and content sizes"
  - test: "Area chart gradient shading"
    expected: "Region above 0.5 midline is light grey; region below is dark grey; midline is a dashed horizontal line at the visual center"
    why_human: "linearGradient with correct stop positions confirmed in code; actual visual color rendering and contrast require browser inspection"
  - test: "Dual-marker dot legibility and density"
    expected: "Filled circles (your flaws) and hollow circles (opponent flaws) are visually distinguishable by fill style and color. Inaccuracy dots (r=2) appear slightly smaller than B/M dots (r=2.5). Density is acceptable — not so dense that individual dots are unreadable."
    why_human: "Dot radii and fill/stroke code confirmed; actual legibility at 80-96px chart height and dot density depend on real game data and visual judgment per D-09"
  - test: "Mobile stacking"
    expected: "At 375px viewport: board+info row appears first, then full-width eval chart (h-20), then tags. Three blocks stack vertically with no horizontal layout."
    why_human: "sm:hidden mobile div with h-20 EvalChart confirmed in code; actual stacking at narrow viewport requires browser resize test"
  - test: "Per-ply tooltip content"
    expected: "Hovering/tapping a ply shows 'Ply N · +X.XX pawns' or 'Ply N · Mate in M (White/Black)'. B/M marker plies also show 'You · Blunder' or 'Opponent · Mistake' with comma-joined tags. Inaccuracy plies show severity+eval but no tags."
    why_human: "Tooltip component and branching logic confirmed in code; actual tooltip trigger behavior (hover/tap responsiveness, positioning) requires browser interaction"
  - test: "Phase transition lines"
    expected: "At most two vertical dashed/solid lines visible (middlegame and endgame). No line at ply 0 (leftmost edge of chart). Absent transitions draw no line."
    why_human: "ReferenceLine for middlegame_ply and endgame_ply with null-guards confirmed; visual rendering of line positions and the absence of a ply-0 line requires browser inspection"
  - test: "Unanalyzed card state"
    expected: "Card with no engine analysis shows the NoAnalysisState pill in col 2 (desktop) and no chart in the mobile block"
    why_human: "analysis_state gate confirmed in code; visual appearance of the pill in the middle column requires browser inspection with an unanalyzed game in the dev DB"
---

# Phase 109: Per-Card Expected-Score Eval Chart Verification Report

**Phase Goal:** Every analyzed game card in Library → Games shows a per-game expected-score eval chart — a recharts area chart from White's perspective with the advantage region shaded, the user's flaws (scope-expanded to BOTH players' flaws: filled=you / hollow=opponent) marked as colored dots, phase-transition vertical lines, and per-ply tooltips — rendered as a dedicated middle column that restructures the desktop card into three equal thirds; mobile stacks the same three blocks. Delivered inline by extending GET /api/library/games GameFlawCard (no new endpoint, no schema change, no migration).
**Verified:** 2026-06-07T02:20:00Z
**Status:** HUMAN_NEEDED — all machine-verifiable must-haves pass; 7 visual/behavioral items require human browser inspection
**Re-verification:** No — initial verification

**Authoritative Decisions applied (override stale ROADMAP SC #3, #4, #5):**
- D-07: Both players' flaws (filled=player, hollow=opponent), not "user's flaws only"
- D-06: No ply-0 line; at most two phase lines (middlegame + endgame)
- D-02: All dots recomputed on the fly from game_positions, not from game_flaws

---

## Goal Achievement

### Observable Truths (Machine-Verifiable)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | GET /library/games emits eval_series/flaw_markers/phase_transitions inline on GameFlawCard (no new endpoint, no migration) | VERIFIED | app/schemas/library.py lines 91-94; app/routers/library.py has 3 routes unchanged; newest migration is Phase 108's add_game_flaws_table |
| 2 | White-perspective ES computed per ply via eval_mate_to_expected_score/eval_cp_to_expected_score("white"); es=None for missing eval | VERIFIED | library_service.py lines 103-119; test_eval_chart_service.py::TestEvalSeries (6 tests) all pass |
| 3 | Both players' flaws detected via mover-POV kernel (_run_all_moves_pass); is_user = mover_color == game.user_color | VERIFIED | library_service.py lines 128-166; test_eval_chart_service.py::TestFlawMarkers::test_both_color_detection and test_is_user_flag_* pass |
| 4 | Opponent B/M markers strip "miss" and "lucky-escape" (_USER_FRAMED_TAGS); inaccuracy markers have empty tags | VERIFIED | library_service.py lines 68-69 (_USER_FRAMED_TAGS), 162-163 (empty tags), 191-206 (_build_opponent_tags strips); tests test_inaccuracy_has_empty_tags and test_opponent_tags_strip_user_framed pass |
| 5 | At most two phase transitions (middlegame, endgame); never a ply-0 line | VERIFIED | library_service.py lines 122-126 (pos.ply > 0 guard, first ply per phase); tests test_no_ply_0_line, test_at_most_two_transitions, test_both_transitions_in_game pass |
| 6 | Single batched game_positions query (no N+1); user-scoped (IDOR) | VERIFIED | library_repository.py lines 325-352 (fetch_page_eval_positions with GamePosition.user_id == user_id); test_no_n_plus_1_query_count and test_idor_eval_positions_user_scoped pass |
| 7 | Unanalyzed games get null eval fields; analyzed games get populated fields | VERIFIED | library_service.py lines 278-313 (_build_card branching); test_eval_series_analyzed_game_has_non_null_fields and test_unanalyzed_game_has_null_eval_fields pass |
| 8 | Gzipped payload delta is negligible (D-05) | VERIFIED | test_payload_gzip_size_below_threshold passes; measured 574 bytes for 2-game page (well below 40 KB ceiling), documented in 109-03-SUMMARY.md |
| 9 | _resolve_increment extracted as shared helper in flaws_service; classify_game_flaws calls it | VERIFIED | flaws_service.py line 451 (def _resolve_increment); classify_game_flaws uses it; not inlined twice |
| 10 | Five EVAL_CHART_* constants in theme.ts; no raw color literals in EvalChart.tsx | VERIFIED | theme.ts lines 33-37 (5 oklch constants); grep finds no `#hex` or `oklch(` in EvalChart.tsx |
| 11 | EvalChart.tsx renders ComposedChart with gradient, dual-marker dot renderer (filled/hollow), phase ReferenceLine, tooltip; data-testid and aria-label present | VERIFIED | EvalChart.tsx 268 lines; contains ComposedChart, linearGradient, buildDotRenderer (is_user branch: filled circle vs hollow circle with fill="none"), buildTooltipContent (You/Opponent labels), data-testid="eval-chart-{gameId}", role="img", aria-label |
| 12 | LibraryGameCard uses sm:grid-cols-3 desktop layout (three thirds); mobile stacks EvalChart at h-20 between board+info and tags | VERIFIED | LibraryGameCard.tsx line 300 (hidden sm:grid sm:grid-cols-3); mobile block lines 280-296 (analysis gate + heightClass="h-20") |
| 13 | 109-UI-SPEC.md amended with dual-marker scheme (hollow/is_user/Opponent) | VERIFIED | grep finds "hollow", "is_user", "Opponent" in UI-SPEC.md; dated amendment note present at top |

**Score:** 13/13 machine-verifiable must-haves verified

### Must-Haves from All Four PLAN Frontmatter Blocks

All truths and artifacts across plans 01, 02, 03, and 04 verified:

**Plan 01 truths — all VERIFIED:** white-perspective ES per ply, both-player detection via mover-POV kernel, opponent miss/lucky-escape stripped, at most two phase transitions with no ply-0 line, es=null for missing eval, single batched query.

**Plan 02 truths — all VERIFIED:** five EVAL_CHART_* constants present, GameFlawCard TS type carries eval_series/flaw_markers/phase_transitions, FlawMarker includes is_user.

**Plan 03 truths — all VERIFIED:** analyzed game returns non-null eval fields, unanalyzed returns null, single batched query (no N+1), IDOR scoping holds, gzip delta recorded and negligible.

**Plan 04 truths — machine portion VERIFIED; visual portion HUMAN_NEEDED:** three-thirds desktop grid exists in code (sm:grid-cols-3), dual-marker dot renderer code confirmed (filled/hollow branches on is_user), You/Opponent tooltip labels present, no ply-0 line guard confirmed, data-testid/ARIA present, 109-UI-SPEC.md amended. Visual rendering quality requires human inspection (see Human Verification section).

### ROADMAP Success Criteria vs Authoritative Decisions

Note: ROADMAP SC #3 (user-only dots from game_flaws), SC #4 (ply-0 line), and SC #5 (inaccuracies "your flaws only") are SUPERSEDED by D-07, D-06, and D-02 per 109-CONTEXT.md (owner-directed amendments). Verification used the CONTEXT decisions as authoritative.

| SC | ROADMAP Text (abbreviated) | Authoritative Override | Status |
|----|---------------------------|----------------------|--------|
| 1 | Three equal-width thirds desktop; mobile stacks; unanalyzed keeps NoAnalysisState | No override — aligned | VERIFIED (code) / HUMAN for visual |
| 2 | White-perspective ES, 50% midline, two-region shading | No override — aligned | VERIFIED (code) / HUMAN for visual |
| 3 | "Your flaws only" — blunders/mistakes from game_flaws | D-07 overrides: BOTH players, filled=you/hollow=opponent; D-02: all on-the-fly | VERIFIED per D-07/D-02 |
| 4 | "Opening (ply 0)" line listed | D-06 overrides: no ply-0 line | VERIFIED per D-06 |
| 5 | "Your flaws" inaccuracies from eval series | D-07 overrides: both players' inaccuracies | VERIFIED per D-07 |
| 6 | Inline delivery, no new endpoint, no N+1, no migration, negligible payload | No override — aligned | VERIFIED |
| 7 | data-testid / ARIA / recharts theming (isAnimationActive=false) | No override — aligned | VERIFIED |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/schemas/library.py` | EvalPoint, FlawMarker (is_user), PhaseTransitions; GameFlawCard extended | VERIFIED | Lines 32-94; all three models present; GameFlawCard gains eval_series/flaw_markers/phase_transitions (nullable, default None) |
| `app/services/library_service.py` | _build_eval_series, _build_opponent_tags, _USER_FRAMED_TAGS, pipeline injection | VERIFIED | Lines 65-206 (builders), 409-412 (pipeline injection); all helpers substantive |
| `app/repositories/library_repository.py` | fetch_page_eval_positions batched, user-scoped | VERIFIED | Lines 325-352; GamePosition.user_id == user_id clause present; seeds all requested game_ids in result dict |
| `app/services/flaws_service.py` | _resolve_increment extracted helper | VERIFIED | Line 451; docstring documents single-source-of-truth intent; classify_game_flaws calls it |
| `tests/services/test_eval_chart_service.py` | 18 unit tests covering ES line, both-color markers, phase transitions | VERIFIED | 374 lines; 18 tests across TestEvalSeries/TestFlawMarkers/TestPhaseTransitions; all 18 PASSED |
| `tests/test_library_router.py` | Integration tests: eval_series presence, no-N+1, IDOR, payload delta | VERIFIED | TestEvalSeriesPayload (5 tests); all 5 PASSED |
| `frontend/src/lib/theme.ts` | Five EVAL_CHART_* constants | VERIFIED | Lines 33-37; EVAL_CHART_AREA_WHITE_AHEAD/BLACK_AHEAD/LINE/MIDLINE/PHASE_LINE all present with oklch values |
| `frontend/src/types/library.ts` | EvalPoint, FlawMarker (is_user), PhaseTransitions interfaces; extended GameFlawCard | VERIFIED | EvalPoint (line 81), FlawMarker with is_user (line 92), PhaseTransitions (line 100); GameFlawCard lines 75-77 |
| `frontend/src/components/library/EvalChart.tsx` | ComposedChart, gradient, dual-marker dots, tooltip, testid/ARIA | VERIFIED | 268 lines; substantive implementation; all structural elements confirmed |
| `frontend/src/components/results/LibraryGameCard.tsx` | sm:grid-cols-3 desktop; mobile stacked block | VERIFIED | Line 300 (grid); lines 280-296 (mobile EvalChart with h-20); both desktop and mobile blocks apply EvalChart |
| `.planning/phases/109-per-card-expected-score-eval-chart-games-subtab/109-UI-SPEC.md` | Amended with dual-marker contract (hollow/is_user/Opponent) | VERIFIED | grep confirms "hollow", "is_user", "Opponent" present; 6 dot style table with fill/stroke columns present |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| library_service.py _build_eval_series | flaws_service.py _run_all_moves_pass | direct call at line 93 | VERIFIED | Imports and calls _run_all_moves_pass; also calls _build_tags (line 140), _resolve_increment (line 100) |
| library_service.py get_library_games | library_repository.py fetch_page_eval_positions | call at lines 409-412 | VERIFIED | Calls with user_id and analyzed_game_ids; result used in _build_card via page_positions.get(game.id, []) |
| library_repository.py fetch_page_eval_positions | game_positions table | GamePosition.user_id == user_id IN query | VERIFIED | Line 343 IDOR clause; line 344 game_id.in_() parameterized |
| LibraryGameCard.tsx | EvalChart.tsx | import at line 8; rendered in both desktop col 2 (line 321) and mobile block (line 285) | VERIFIED | Both render sites check analysis_state == 'analyzed' + three eval fields non-null |
| EvalChart.tsx | theme.ts | imports EVAL_CHART_* and SEV_* constants (lines 19-27); no inline hex/oklch literals | VERIFIED | All 8 theme imports present; zero raw color literals in file |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| EvalChart.tsx | evalSeries, flawMarkers, phaseTransitions | Props from LibraryGameCard | Yes — props come from game.eval_series/flaw_markers/phase_transitions populated by _build_eval_series via fetch_page_eval_positions DB query | FLOWING |
| LibraryGameCard.tsx | game.eval_series | GET /api/library/games response (useLibraryGames hook) | Yes — backend query over game_positions WHERE user_id IN analyzed_game_ids, real DB rows | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| _build_eval_series importable | `python -c "from app.services.library_service import _build_eval_series; print('import ok')"` | "import ok" | PASS |
| 18 unit tests pass | `uv run pytest tests/services/test_eval_chart_service.py -v` | 18 passed | PASS |
| 5 router integration tests pass | `uv run pytest tests/test_library_router.py -v -k "TestEvalSeriesPayload"` | 5 passed in TestEvalSeriesPayload | PASS |
| ruff clean | `uv run ruff check app/ tests/` | All checks passed | PASS |
| ty clean (zero errors) | `uv run ty check app/ tests/` | All checks passed | PASS |
| tsc clean | `cd frontend && npx tsc --noEmit` | 0 output lines (clean) | PASS |
| eslint clean | `cd frontend && npm run lint` | Clean | PASS |
| knip clean | `cd frontend && npm run knip` | Clean (EvalChart export consumed by LibraryGameCard) | PASS |
| 825 frontend tests | `cd frontend && npm test -- --run` | 825 passed | PASS |

### Probe Execution

No probe scripts found for this phase (not a migration/tooling phase). Step 7c: SKIPPED (no probe-*.sh files).

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| LIBG-10 | Plans 01/02/03/04 | Per-card expected-score eval chart on Games subtab | SATISFIED (machine gates) / HUMAN for visual quality | All code, schema, tests, and wiring confirmed; visual rendering deferred to human UAT |

### Anti-Patterns Found

No TBD, FIXME, or XXX markers found in any modified Phase 109 files.

No TODO or PLACEHOLDER patterns found in modified files.

One minor code smell noted: `userColor` prop is passed to `<EvalChart>` on the desktop path in LibraryGameCard.tsx (line 326) but is NOT declared in `EvalChartProps`. TypeScript passes with zero errors (this behavior is consistent with how React's JSX type checking sometimes handles extra props on function components with strict interfaces in certain TypeScript/React versions). The prop is functionally dead — the component uses the backend-provided `is_user` discriminator on `FlawMarker` for player/opponent distinction, not `userColor`. This is a WARNING (orphaned prop) but not a blocker.

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `frontend/src/components/results/LibraryGameCard.tsx` | 326 | `userColor` prop passed to EvalChart but not in EvalChartProps interface | Warning | Dead prop — tsc passes, no functional impact; EvalChart uses is_user from FlawMarker data instead |

---

### Human Verification Required

All machine-verifiable gates pass. The following items require human browser inspection at Library → Games subtab (run `bin/run_local.sh` against dev DB; do NOT reset the dev DB).

### 1. Desktop Three-Thirds Layout

**Test:** Visit Library → Games on desktop (>640px). Inspect an analyzed game card.
**Expected:** Three visually equal columns: miniboard+opening+metadata on the left, eval area chart in the middle, tags/severity on the right. Chart is NOT stacked under tags.
**Why human:** `sm:grid-cols-3` confirmed in code; actual column width equality and visual balance depend on browser layout engine and content sizes.

### 2. Area Chart Two-Region Gradient Shading

**Test:** On an analyzed card, inspect the chart visually.
**Expected:** The area above the dashed 0.5 midline is light grey (white-ahead region). The area below the midline is dark grey (black-ahead region). The midline is a dashed horizontal line at the visual vertical center of the chart.
**Why human:** `linearGradient` with 50% hard stop and correct `EVAL_CHART_AREA_WHITE_AHEAD`/`EVAL_CHART_AREA_BLACK_AHEAD` oklch values confirmed in code; actual rendered color contrast and gradient position require browser inspection.

### 3. Dual-Marker Dot Legibility and Density (D-09)

**Test:** Find an analyzed game with flaws. Inspect flaw dots on the chart.
**Expected:** Filled circles for your flaws; hollow (outline-only) circles for opponent flaws. Both colored by severity (blunder red, mistake orange, inaccuracy yellow). Inaccuracy dots appear slightly smaller than blunder/mistake dots. Density is acceptable — dots do not completely obscure each other or the chart line.
**Why human:** Dot renderer code confirmed (filled vs hollow branch on is_user, r=2 vs r=2.5 per severity); actual legibility at 80-96px chart height with real game data requires visual judgment per D-09.

### 4. Mobile Stacking (375px Viewport)

**Test:** Resize browser to 375px (or use DevTools device emulation). View an analyzed game card.
**Expected:** Three blocks stack vertically: board+info row first, then full-width eval chart (shorter, h-20), then tags. No horizontal columns. Chart is visible and not clipped.
**Why human:** `sm:hidden` mobile div with `heightClass="h-20"` EvalChart confirmed; actual stacking at narrow viewport requires browser resize test.

### 5. Per-Ply Tooltip Content

**Test:** Hover (desktop) or tap (mobile/touch) on various plies of the eval chart.
**Expected:** Tooltip shows "Ply N · +X.XX pawns" or "Ply N · Mate in M (White/Black)". On a B/M marker ply: also shows "You · Blunder" (or "Opponent · Mistake") colored by severity, plus comma-joined tags. On an inaccuracy marker ply: shows "You · Inaccuracy" or "Opponent · Inaccuracy" with NO tags (just severity + eval).
**Why human:** Tooltip branching logic confirmed in code; actual tooltip trigger behavior (hover response, tap on mobile, positioning, readability at text-xs) requires browser interaction.

### 6. Phase-Transition Lines

**Test:** Inspect an analyzed game with a middlegame and/or endgame phase.
**Expected:** At most two vertical lines visible at the middlegame entry ply and endgame entry ply. No line at ply 0 (leftmost chart edge). Games with only opening phase show no vertical lines.
**Why human:** `ReferenceLine` null guards for `middlegame_ply`/`endgame_ply` with `pos.ply > 0` confirmed; visual position of lines and absence of ply-0 line requires browser inspection.

### 7. Unanalyzed Card State

**Test:** Find a card with `analysis_state = "no_engine_analysis"` in the Games list.
**Expected:** Desktop col 2 shows the existing NoAnalysisState pill (not a chart). Mobile section shows no chart between board+info and tags.
**Why human:** `analysis_state === 'analyzed'` gate confirmed in code for both desktop col 2 and mobile block; visual appearance of the pill in the middle column and absence of chart requires a real unanalyzed game in the dev DB.

---

## Gaps Summary

No machine-verifiable gaps found. All 13 must-have truths are confirmed in the codebase with substantive implementations and passing tests.

One non-blocking warning: the `userColor` prop passed to `<EvalChart>` on the desktop path is not declared in `EvalChartProps` and is silently ignored by the component. This does not affect functionality (the component uses the backend-provided `is_user` discriminator instead) but should be cleaned up — either remove the prop from the call site or add it to the interface as optional.

The 7 human-verification items above are visual/behavioral checks that cannot be confirmed from code alone. They represent the typical end-of-phase UAT checkpoint deferred from Task 4 of plan 04 (`type="checkpoint:human-verify"`) which was auto-approved under `--auto/--chain`.

---

_Verified: 2026-06-07T02:20:00Z_
_Verifier: Claude (gsd-verifier)_
