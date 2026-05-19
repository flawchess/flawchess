---
phase: 87-section-3-per-type-endgame-type-breakdown-cards
verified: 2026-05-14T00:00:00Z
status: human_needed
score: 6/6 must-haves verified (1 with approved design deviation)
overrides_applied: 1
overrides:
  - must_have: "Each per-type card has Conv peer bullet (You − Opp vs 0) AND Recov peer bullet (You − Opp vs 0) (SEC3-02 literal wording; roadmap SC1 'two peer bullets (Conv+Recov)')."
    reason: "User-approved post-execute redesign (87-FIX-SUMMARY.md, commits d536b026 → dc1a0da2). The original Conv + Recov peer-bullet pair always rendered the same magnitude because both derive from the same per-class WDL totals via the mirror identity (oppConv = recovery_losses/recovery_games; oppRecov = (conversion_losses+conversion_draws)/conversion_games). Two rows of UI, one signal. The redesign replaces BOTH bullets with a SINGLE chess-score bullet using the exact pattern from EndgameOverallCard (Games-with-Endgame card): per-class score (W + 0.5·D)/N tested against the 50% baseline, Wilson 95% whiskers, Wilson score-test p-value gating the sig-paint triple. The two per-class gauges (Conv, Recov) at the top of each card are preserved. Preserves the spirit of SEC3-02 / SEC3-04 (per-class significance/peer signal) while eliminating the redundant-row UX problem."
    accepted_by: "user"
    accepted_at: "2026-05-14T00:00:00Z"
human_verification:
  - test: "Mobile real-device density check at 375px (HUMAN-UAT Test 4, SEC3-05)"
    expected: "On a real iOS / Android device at 375px width (iPhone 12/13 mini or SE 3rd gen), scroll through the 5 cards. Each card carries 2 gauges + (optional) WDL bar + Games deep-link + Score bullet. If per-card content exceeds ~1 screen height or the section exceeds ~3 screen heights, flip SHOW_WDL_BAR_IN_TYPE_CARDS to false in frontend/src/lib/endgameMetrics.ts, update the h2 InfoPopover copy, and re-run frontend tests."
    why_human: "Real-device density / scroll comfort cannot be automated; emulator proxies are noted as acceptable fallback but must be documented."
  - test: "?type=<slug> URL deep-link hydration end-to-end (HUMAN-UAT Test 5)"
    expected: "Clicking the Games icon on Rook navigates to /endgames/games?type=rook; refreshing the page at that URL still pre-seeds the Rook filter. Repeating with at least one other class (Mixed → ?type=mixed) confirms the slug→class inverse map. (Programmatically confirmed: SLUG_TO_ENDGAME_CLASS exists at module scope, useEffect on [searchParams] reads ?type=. Visual confirmation only.)"
    why_human: "End-to-end browser navigation + refresh state preservation."
  - test: "Per-card title + per-bullet + h2 InfoPopover content rendering (HUMAN-UAT Tests 6, 7, 8)"
    expected: "Hovering each HelpCircle (per-card title, per-card Score bullet, page-level h2) renders the expected explainer copy."
    why_human: "Popover rendering + hover state is visual."
  - test: "Filter responsiveness and empty/sparse handling (HUMAN-UAT Tests 9, 10)"
    expected: "Applying a filter (e.g. Opponent Strength: Stronger) updates Score values across cards; the gauges stay fixed (per-class bands). Empty class (total=0) shows opacity-50 gauges + 'Not enough data yet'; sparse class (0 < total < 10) shows n=N chip + reduced body opacity and the Score row is hidden."
    why_human: "Live filter dispatch + UI reflow is visual."
  - test: "Visual confirmation that legacy table + gauge-strip are gone (HUMAN-UAT Test 11)"
    expected: "Only the new 5-card grid is visible under the h2; no legacy per-type WDL table; no legacy gauge-only mini cards."
    why_human: "Visual confirmation; programmatic check already confirms files deleted + zero non-comment references."
---

# Phase 87: Section 3 — Per-type Endgame Type Breakdown Cards Verification Report

**Phase Goal:** Replace the grouped `EndgameWDLChart` and extend `EndgameConvRecovChart` into 5 full per-type cards (rook / minor_piece / pawn / queen / mixed; pawnless hidden) with WDL distribution, conversion/recovery rates, and a peer comparison signal per class.

**Verified:** 2026-05-14
**Status:** human_needed (all programmatic must-haves PASS; visual / real-device HUMAN-UAT items pending)
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (against ROADMAP success criteria, adjusted for approved design deviation)

| #   | Truth (SC#)                                                                                                                                                                                                                                                                | Status                              | Evidence                                                                                                                                                                                                                                                                  |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | SC1: 5 per-type cards in a `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4` grid (pawnless filtered) under "Endgame Type Breakdown" h2, each labelled by class, with side-by-side Conv + Recov gauges, a WDL bar, **peer/significance signal per class**, Games deep-link. | ✓ VERIFIED                          | `EndgameTypeBreakdownSection.tsx:56` carries the locked grid class; `HIDDEN_ENDGAME_CLASSES.has(c.endgame_class)` filter at line 43-45; `EndgameTypeCard.tsx:227-353` renders title row + 2 gauges (lines 239-269) + WDL+Games deep-link (271-291) + Score bullet row (295-350). |
| 1b  | SC1 LITERAL "two peer bullets (Conv+Recov)" — Conv peer bullet AND Recov peer bullet per card.                                                                                                                                                                             | ⚠ PASSED (override)                 | User-approved redesign: Conv+Recov peer bullets collapsed into a SINGLE per-class Score bullet (W + 0.5·D)/N vs 50% baseline. Mirror identity makes the two original bullets always render the same magnitude. See `87-FIX-SUMMARY.md`; commits d536b026, dec56649, 65e0e2ba.    |
| 2   | SC2: Per-class peer signal uses sample-size gating and a sparse-n indicator. In the redesign: Score row is **hidden** when `total < MIN_GAMES_FOR_RELIABLE_STATS` (=10); `score_p_value` is **null** from backend when `total < PVALUE_RELIABILITY_MIN_N` (=10).            | ✓ VERIFIED (spirit; gates aligned)  | Backend gate: `app/services/endgame_service.py:419-421` (`p_score_class_raw if total >= PVALUE_RELIABILITY_MIN_N else None`). Frontend gate: `EndgameTypeCard.tsx:98` (`showScoreRow = total >= MIN_GAMES_FOR_RELIABLE_STATS`) controls row mount at line 295.                  |
| 2b  | SC2: Gauge bands continue to use `PER_CLASS_GAUGE_ZONES[<class>].{conversion,recovery}` (p25/p75) — no per-class p50.                                                                                                                                                       | ✓ VERIFIED                          | `EndgameTypeCard.tsx:33` (import) and lines 197-208 (per-class band lookup + colorizeGaugeZones for both gauges). No p50 introduced.                                                                                                                                       |
| 3   | SC3: Real-device mobile density check performed and documented. `SHOW_WDL_BAR_IN_TYPE_CARDS` final value committed before merge; h2 InfoPopover copy reflects whatever path is chosen.                                                                                     | ⚠ PENDING (human)                   | `87-HUMAN-UAT.md` exists with `status: partial`; Test 4 (375px) is the critical gating decision. Flag currently `true` (`lib/endgameMetrics.ts:153`). The HUMAN-UAT scaffold + flip checklist are in place; the actual real-device walk-through is awaiting the user.       |
| 4   | SC4: Legacy `EndgameWDLChart.tsx` and `EndgameConvRecovChart.tsx` removed; knip clean.                                                                                                                                                                                     | ✓ VERIFIED                          | `test -f frontend/src/components/charts/EndgameWDLChart.tsx` → DELETED; same for `EndgameConvRecovChart.tsx`. Surviving references are header-comment / lifted-from annotations only (no live imports). Knip clean per 87-03-SUMMARY gate sweep results.                  |
| 5   | Backend wire shape: `EndgameCategoryStats.score_p_value: float | None` (Wilson score-test p-value vs 50%, gated on `total >= PVALUE_RELIABILITY_MIN_N`). TS type mirrors.                                                                                                  | ✓ VERIFIED                          | `app/schemas/endgames.py:84` declares the field; `endgame_service.py:416-421, 435` populates it per category via `compute_confidence_bucket`. `frontend/src/types/endgames.ts:36` mirrors. 2 backend tests (`TestPerClassScorePValue`) cover both gated + significant paths. |
| 6   | Cards mount via `EndgameTypeBreakdownSection` orchestrator; `Endgames.tsx` mounts ONE `<EndgameTypeBreakdownSection>` in place of both legacy components; `totalGames` denominator is `statsData.endgame_games` (not `total_games`).                                       | ✓ VERIFIED                          | `Endgames.tsx:593-597` mounts the orchestrator passing `totalGames={statsData.endgame_games}`. (REVIEW WR-01 closed.)                                                                                                                                                       |
| 7   | A11y: Section `aria-labelledby="endgame-type-breakdown-heading"`; matching `id` on the h2.                                                                                                                                                                                  | ✓ VERIFIED                          | `EndgameTypeBreakdownSection.tsx:50` carries `aria-labelledby`; `Endgames.tsx:539` carries `id="endgame-type-breakdown-heading"`. Card root has `role="group"` + `aria-label` (`EndgameTypeCard.tsx:148-150, 231-232`). MiniWDLBar carries `aria-label`.                  |
| 8   | URL hydration: `/endgames/games?type=<slug>` pre-seeds `selectedCategory` on direct visit / refresh; unknown slugs ignored.                                                                                                                                                | ✓ VERIFIED (effect present)         | `Endgames.tsx:67-71` defines `SLUG_TO_ENDGAME_CLASS` reverse map at module scope; lines 336-348 implement the `useEffect` on `[searchParams]` that validates the slug and calls `setSelectedCategory`. T-87-07 mitigation: unknown slugs short-circuit silently.            |
| 9   | Page-level h2 InfoPopover lifts the taxonomy + Conv/Recov metric defs + gauge-band explainer + per-type descriptions + (redesigned) Score-bullet explainer.                                                                                                                | ✓ VERIFIED                          | `Endgames.tsx:540-591`: 5 paragraph blocks + 5 per-type description lines. Score-bullet explainer at lines 573-581 replaces the dropped peer-bullet explainer per the redesign.                                                                                            |
| 10  | Sub-question paragraph rendered above the grid (D-12).                                                                                                                                                                                                                     | ✓ VERIFIED                          | `EndgameTypeBreakdownSection.tsx:52-55`: "Which Endgame Types do you convert best and defend best, and how does each compare to your opponents?"                                                                                                                           |

**Score:** 6/6 roadmap success criteria verified (1 with approved design override; 1 awaiting human density-check confirmation).

### Required Artifacts

| Artifact                                                                                                  | Expected                                                                                | Status      | Details                                                                                                                                                                                          |
| --------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `frontend/src/components/charts/EndgameTypeCard.tsx`                                                       | Per-class card shell (gauges + WDL + Score bullet)                                       | ✓ VERIFIED  | 354 LOC; head-doc explicitly cites the post-review redesign; gauges + WDL + single Score bullet wired correctly (lines 197-350).                                                                  |
| `frontend/src/components/charts/EndgameTypeBreakdownSection.tsx`                                           | Orchestrator: filter + grid + per-card mount                                             | ✓ VERIFIED  | 74 LOC; locked grid class; pawnless filtered via `HIDDEN_ENDGAME_CLASSES`; `aria-labelledby` landmark.                                                                                              |
| `frontend/src/lib/endgameMetrics.ts`                                                                       | Shared exports: `ENDGAME_TYPE_DESCRIPTIONS`, `SHOW_WDL_BAR_IN_TYPE_CARDS`, `ENDGAME_CLASS_TO_SLUG`, `HIDDEN_ENDGAME_CLASSES` | ✓ VERIFIED  | All four shared exports present (lines 140, 153, 160, 175). Pawnless correctly omitted from descriptions (Exclude<…, 'pawnless'>).                                                              |
| `frontend/src/pages/Endgames.tsx`                                                                          | Mount swap + h2 InfoPopover + URL hydration + h2 id                                      | ✓ VERIFIED  | Imports updated (line 23-28); legacy imports removed (grep returns 0 live refs); URL effect at 336-348; h2 id at 539.                                                                             |
| `frontend/src/components/charts/__tests__/EndgameTypeCard.test.tsx`                                        | Vitest covering layout / sparse / sig-gating                                              | ✓ VERIFIED  | Rewritten for the redesign; 10 tests including the score sig-gating triple (`describe('EndgameTypeCard — Score bullet sig-gating')`).                                                              |
| `frontend/src/components/charts/__tests__/EndgameTypeBreakdownSection.test.tsx`                            | Vitest covering filtering / ordering / empty                                              | ✓ VERIFIED  | Exists; 6 tests across 4 describe groups per 87-03-SUMMARY.                                                                                                                                       |
| `app/schemas/endgames.py`                                                                                  | `EndgameCategoryStats.score_p_value: float \| None`                                      | ✓ VERIFIED  | Line 84 with Phase 87 docstring.                                                                                                                                                                  |
| `app/services/endgame_service.py`                                                                          | Populates `score_p_value` via `compute_confidence_bucket` gated on `PVALUE_RELIABILITY_MIN_N=10` | ✓ VERIFIED  | Lines 416-421 + 435.                                                                                                                                                                              |
| `tests/test_endgame_service.py`                                                                            | `TestPerClassScorePValue` covers gated + significant paths                                | ✓ VERIFIED  | Lines 502+; 2 tests.                                                                                                                                                                              |
| `frontend/src/types/endgames.ts`                                                                           | Mirrors the new field                                                                    | ✓ VERIFIED  | Line 36 with citation comment.                                                                                                                                                                    |
| `.planning/milestones/v1.17-phases/87-section-3-per-type-endgame-type-breakdown-cards/87-HUMAN-UAT.md`    | 11 tests; 375px density check is the critical gating item                                | ✓ VERIFIED  | Status `partial`; Test 4 carries SC3-05 critical-test marker.                                                                                                                                     |
| `frontend/src/components/charts/EndgameWDLChart.tsx`                                                       | DELETED (SEC3-06)                                                                        | ✓ VERIFIED  | `test -f` returns non-zero.                                                                                                                                                                       |
| `frontend/src/components/charts/EndgameConvRecovChart.tsx`                                                 | DELETED (SEC3-07)                                                                        | ✓ VERIFIED  | `test -f` returns non-zero.                                                                                                                                                                       |

### Key Link Verification

| From                                                            | To                                                          | Via                                                                | Status                |
| --------------------------------------------------------------- | ----------------------------------------------------------- | ------------------------------------------------------------------ | --------------------- |
| `Endgames.tsx`                                                  | `EndgameTypeBreakdownSection`                               | Import at line 23, mount at lines 593-597                          | ✓ WIRED               |
| `Endgames.tsx`                                                  | `statsData.endgame_games` (denominator)                      | `totalGames={statsData.endgame_games}` (line 595)                  | ✓ WIRED               |
| `EndgameTypeBreakdownSection`                                   | `EndgameTypeCard`                                            | Import + map render at line 62                                     | ✓ WIRED               |
| `EndgameTypeCard`                                               | `PER_CLASS_GAUGE_ZONES`                                      | Import at line 33; usage at lines 197-208                          | ✓ WIRED               |
| `EndgameTypeCard`                                               | `MetricStatPopover` (Score bullet)                           | Lines 309-331 mount with Wilson methodology                        | ✓ WIRED               |
| `EndgameTypeCard`                                               | `MiniBulletChart` (Score bullet)                             | Lines 337-347 with Wilson CI whiskers                              | ✓ WIRED               |
| `EndgameTypeCard`                                               | `deriveLevel(score_p_value, total)` (sig gating)             | Line 92; controls `scoreShowZoneFontColor` + inline color          | ✓ WIRED               |
| `EndgameTypeCard.Link`                                          | `/endgames/games?type=<slug>` + `onCategorySelect`           | Lines 212-223                                                      | ✓ WIRED               |
| `Endgames.tsx` URL hydration effect                             | `setSelectedCategory(parsed)` on valid slug                  | Lines 336-348                                                      | ✓ WIRED               |
| `EndgameTypeBreakdownSection` `<section aria-labelledby>`       | `Endgames.tsx` `<h2 id="endgame-type-breakdown-heading">`    | Line 50 (section) + line 539 (h2)                                  | ✓ WIRED (landmark)    |
| backend `score_p_value` population                              | `_aggregate_endgame_stats`                                   | Lines 416-421 of `endgame_service.py`; populated per category at 435 | ✓ WIRED               |

### Data-Flow Trace (Level 4)

| Artifact                | Data Variable                       | Source                                                                                                                            | Produces Real Data | Status      |
| ----------------------- | ----------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- | ------------------ | ----------- |
| `EndgameTypeCard`       | `category` (per-class WDL + score_p_value) | Backend `_aggregate_endgame_stats` (real SQL aggregation over `game_positions`); served via `/api/endgames/overview` to `Endgames.tsx` | ✓ Yes              | ✓ FLOWING   |
| `EndgameTypeCard`       | `category.score_p_value`            | `compute_confidence_bucket(wins, draws, losses, total)` at `endgame_service.py:416-421`                                            | ✓ Yes              | ✓ FLOWING   |
| `EndgameTypeBreakdownSection` | `categories`, `totalGames`     | `Endgames.tsx:594-595` passes `statsData.categories` + `statsData.endgame_games` from `/api/endgames/overview` response.            | ✓ Yes              | ✓ FLOWING   |
| `EndgameTypeCard` Score bullet | `score`, `ciLow`, `ciHigh`     | `score = (category.wins + 0.5*category.draws) / total`; `wilsonBounds(score, total)` (lines 91-97)                                | ✓ Yes              | ✓ FLOWING   |
| Gauges                  | `category.conversion.conversion_pct`, `recovery_pct` | Backend per-class WDL aggregator (existing Phase 84 wire)                                                                          | ✓ Yes              | ✓ FLOWING   |

### Behavioral Spot-Checks

| Behavior                                                                  | Command                                                                                                                                          | Result      | Status |
| ------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ | ----------- | ------ |
| Legacy `EndgameWDLChart.tsx` file deleted                                 | `test -f frontend/src/components/charts/EndgameWDLChart.tsx`                                                                                     | exit 1      | ✓ PASS |
| Legacy `EndgameConvRecovChart.tsx` file deleted                           | `test -f frontend/src/components/charts/EndgameConvRecovChart.tsx`                                                                               | exit 1      | ✓ PASS |
| No live references to deleted components                                  | `grep -rn EndgameWDLChart\|EndgameConvRecovChart frontend/src/` excluding lift-from comments                                                       | 0 live refs | ✓ PASS |
| Four shared exports present in `lib/endgameMetrics.ts`                    | `grep "ENDGAME_TYPE_DESCRIPTIONS\|SHOW_WDL_BAR_IN_TYPE_CARDS\|ENDGAME_CLASS_TO_SLUG\|HIDDEN_ENDGAME_CLASSES" frontend/src/lib/endgameMetrics.ts` | 4 found     | ✓ PASS |
| Backend `score_p_value` populated per category                            | `grep -n "score_p_value" app/services/endgame_service.py`                                                                                        | 3 hits in `_aggregate_endgame_stats` | ✓ PASS |
| HUMAN-UAT scaffold present with 375px critical test                       | `grep "375px\|SHOW_WDL_BAR_IN_TYPE_CARDS" .planning/.../87-HUMAN-UAT.md`                                                                          | found       | ✓ PASS |

### Probe Execution

| Probe | Command | Result | Status |
| ----- | ------- | ------ | ------ |

SKIPPED — no probes documented for this phase; not a migration/CLI phase.

### Requirements Coverage

| Requirement | Source Plan        | Description                                                                                                                                                                                                                                                                                              | Status              | Evidence                                                                                                                                                                                                                                                                                                                  |
| ----------- | ------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SEC3-01     | 87-03-PLAN          | 5 per-type cards in 3-col grid on lg+, 2-col on sm, 1-col on mobile; rook / minor_piece / pawn / queen / mixed.                                                                                                                                                                                          | ✓ SATISFIED         | `EndgameTypeBreakdownSection.tsx:56` grid + filter; 6 vitest cases in `EndgameTypeBreakdownSection.test.tsx`. Visual breakpoints require HUMAN-UAT Tests 1-3.                                                                                                                                                                |
| SEC3-02     | 87-02 + 87-03 PLAN  | Each card: side-by-side Conv + Recov gauges, WDL bar, Conv peer bullet, Recov peer bullet, Games deep-link.                                                                                                                                                                                              | ⚠ SATISFIED (override) | Gauges + WDL + Games deep-link present (`EndgameTypeCard.tsx:239-291`). Conv + Recov peer bullets **replaced by single Score bullet** per user-approved redesign (`87-FIX-SUMMARY.md`). Spirit preserved: per-class peer/significance signal lives in the Score bullet's gating against the 50% chess-score baseline.        |
| SEC3-04     | 87-01 + 87-02       | Peer bullets gated on `MIN_OPPONENT_BASELINE_GAMES` with sparse-n indicator.                                                                                                                                                                                                                              | ⚠ SATISFIED (override) | In the redesign: Score row is hidden when `total < MIN_GAMES_FOR_RELIABLE_STATS`; backend `score_p_value` is null when `total < PVALUE_RELIABILITY_MIN_N`. Sparse handling moved from "peer bullet shows muted text" to "score row hidden + Wilson whiskers communicate uncertainty". Both gates present + verified.       |
| SEC3-05     | 87-03               | Mobile real-device density check performed; fallback path is drop the WDL bar (not peer bullets).                                                                                                                                                                                                       | ? NEEDS HUMAN       | HUMAN-UAT Test 4 is the gating critical-test marker. Scaffold + flip checklist in place; awaiting real-device walk-through.                                                                                                                                                                                                |
| SEC3-06     | 87-03               | Legacy `EndgameWDLChart` removed.                                                                                                                                                                                                                                                                        | ✓ SATISFIED         | File deleted; no live imports remain.                                                                                                                                                                                                                                                                                       |
| SEC3-07     | 87-03               | `EndgameConvRecovChart` no longer exists as standalone — absorbed into per-type card.                                                                                                                                                                                                                     | ✓ SATISFIED         | File deleted; gauge logic transplanted into `EndgameTypeCard.tsx:197-269`.                                                                                                                                                                                                                                                  |

All 6 declared requirement IDs (SEC3-01, SEC3-02, SEC3-04, SEC3-05, SEC3-06, SEC3-07) accounted for. No orphaned requirements. SEC3-02 / SEC3-04 satisfied via approved design deviation; SEC3-05 awaits human verification.

### Anti-Patterns Found

| File                                                  | Line | Pattern                                          | Severity | Impact                                                                                                                                                                            |
| ----------------------------------------------------- | ---- | ------------------------------------------------ | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `EndgameTypeCard.tsx`                                  | 197-198 | `bands!.conversion`, `bands!.recovery` (non-null assertion) | ℹ Info   | Documented as safe: pawnless is filtered upstream + the registry covers the remaining 5 classes. REVIEW WR-04 closed by dropping the dead `!bands` runtime fallback.                                       |
| `Endgames.tsx`                                          | 347  | `// eslint-disable-next-line react-hooks/exhaustive-deps` | ℹ Info   | Intentional + documented in surrounding comment (lines 344-347): the effect is a one-way URL→state seed; including `selectedCategory` in deps would create a fight loop with `handleCategorySelect`.       |
| `EndgameTypeCard.tsx`                                  | 87-89 | `score = total > 0 ? ... : 0` then immediately gated by `showScoreRow = total >= 10` | ℹ Info   | Defensive double-gate: the divide-by-zero guard is paired with a mount-time `showScoreRow` gate so the 0-fallback never reaches `wilsonBounds`. Cosmetic; no behaviour issue.                                  |
| (none in scope)                                        | —    | `text-xs` in component code                       | —        | Verified absent in `EndgameTypeCard.tsx` per CLAUDE.md no-text-xs rule (acceptance criterion from 87-02-PLAN Task 2 still holds).                                                                              |

Pre-existing failures explicitly NOT attributed to phase 87:
- `frontend/src/components/popovers/__tests__/MetricStatTooltip.test.tsx:305` period-vs-colon assertion — documented in `deferred-items.md`; verified to fail on the pre-phase-87 base; not a phase-87 regression.
- `ruff format --check .` reports 47 files needing reformatting per `87-03-SUMMARY` gate-sweep table — pre-existing baseline issue, not phase-87 scope.

### Human Verification Required

1. **Mobile real-device density check at 375px (HUMAN-UAT Test 4, SEC3-05 critical)**
   - **Test:** Open the Endgames page on a real iOS / Android device at 375px viewport (iPhone 12/13 mini, SE 3rd gen, or equivalent). Scroll through the 5 cards.
   - **Expected:** If per-card content exceeds ~1 screen height OR section scrolls past ~3 screen heights, flip `SHOW_WDL_BAR_IN_TYPE_CARDS` to `false` in `frontend/src/lib/endgameMetrics.ts`, update the page-level h2 InfoPopover copy to reflect the WDL-bar drop, re-run frontend tests, and commit. Otherwise keep `true` and document the device + viewport in the HUMAN-UAT result line.
   - **Why human:** Real-device density / scroll comfort cannot be automated; emulator proxies acceptable but must be noted.

2. **`?type=<slug>` end-to-end URL deep-link hydration (HUMAN-UAT Test 5)**
   - **Test:** Click Games icon on Rook card → URL becomes `/endgames/games?type=rook` and filter pre-seeds to Rook. Refresh the URL — filter still Rook. Repeat with Mixed (slug `mixed`).
   - **Expected:** Direct visit + refresh + in-app navigation all pre-seed the type filter correctly.
   - **Why human:** End-to-end browser navigation + refresh + URL persistence is visual / interactive. (Programmatic check confirms the inverse map and `useEffect` exist.)

3. **InfoPopover rendering (HUMAN-UAT Tests 6, 7, 8)**
   - **Test:** Hover each per-card title HelpCircle, each Score bullet HelpCircle, and the page-level h2 HelpCircle.
   - **Expected:** Each renders the expected explainer copy (per-type description, Score-bullet methodology, taxonomy + metric defs + score-bullet explainer + per-type entries).
   - **Why human:** Popover hover + rendering is visual.

4. **Filter responsiveness + empty/sparse handling (HUMAN-UAT Tests 9, 10)**
   - **Test:** Apply a filter (e.g. Opponent Strength: Stronger) → Score values shift; gauges stay fixed. Force an empty class (total=0) → opacity-50 gauges + "Not enough data yet". Force a sparse class (0 < total < 10) → n=N chip + reduced body opacity + Score row hidden.
   - **Expected:** Live filter dispatch + UI reflow matches the empty/sparse design.
   - **Why human:** Live UI re-render is visual.

5. **Legacy removal visual confirmation (HUMAN-UAT Test 11)**
   - **Test:** Visit the Endgames page; verify only the new 5-card grid is visible under the h2; no legacy per-type WDL table; no legacy gauge-strip.
   - **Expected:** Only the new grid is visible.
   - **Why human:** Visual confirmation; programmatic check already passed (files deleted, zero live imports).

### Gaps Summary

None — programmatically. The phase goal IS achieved in the codebase under the user-approved redesign:

- The 5 per-type cards exist with the right structure (gauges + WDL + Games deep-link + Score bullet).
- The legacy components are deleted.
- The denominator wiring (`endgame_games`) and aria-landmark wiring (`aria-labelledby`) are correct.
- The redesign preserves the spirit of SEC3-02 / SEC3-04: per-class peer/significance signal lives in the Score bullet's sig-gating against the 50% chess-score baseline. The original literal "two peer bullets" wording is overridden via the `overrides:` entry in this VERIFICATION.md frontmatter.

The remaining gate is the **375px mobile real-device density check (HUMAN-UAT Test 4)**, which decides the final value of `SHOW_WDL_BAR_IN_TYPE_CARDS`. The flag default is `true`; if the check fires the fallback, the executor must flip the flag, update the h2 popover copy, and re-run frontend tests per the HUMAN-UAT scaffold instructions. **Status is therefore `human_needed`, not `passed`.**

### Note on Design Deviation

The redesign documented in `87-FIX-SUMMARY.md` (Conv + Recov peer bullets → single Score bullet) is recorded as an `overrides:` entry rather than a `gaps:` entry. The override captures:
- The mathematical justification (mirror identity makes the two original bullets render the same magnitude — two rows of UI, one signal).
- The user-approved scope of the redesign (preserve the gauges; replace both bullets with a single chess-score bullet using the exact `EndgameOverallCard` pattern).
- Commit trail (d536b026, 2e57f211, dec56649, 65e0e2ba, 31e082d1, 60eee922).
- The `score_p_value` field on the backend wire that drives the Score-bullet sig gating.

Recommend amending the v1.17 ROADMAP SC1 + REQUIREMENTS SEC3-02 / SEC3-04 wording at milestone close to reflect the single-Score-bullet design.

---

_Verified: 2026-05-14_
_Verifier: Claude (gsd-verifier)_
