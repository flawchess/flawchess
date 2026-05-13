---
phase: 85-section-1-games-with-vs-without-endgame-cards
verified: 2026-05-13T21:20:00Z
status: human_needed
score: 9/9 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Visual UAT of 3-card composite section on the Endgames page"
    expected: "Card 1 'Games ending in Middlegame' (WDL + score), Card 2 'At Endgame Entry' (entry eval + achievable score, no WDL), Card 3 'Endgame results' (WDL + score), Score Gap tile under Card 2 on desktop / stacked at bottom on mobile. Legacy table gone. Sig-gating tints score values in clearly lopsided cohorts. No section-root h3 or InfoPopover above the cards."
    why_human: "Plan 04 Task 3 was a blocking checkpoint:human-verify that the autonomous executor deferred. Plan 05 is autonomous and replaces the section structure entirely, but visual layout, mobile stacking behavior, popover copy, and sig-gating appearance cannot be verified programmatically."
---

# Phase 85: Section 1 — Games with vs without Endgame cards Verification Report

**Phase Goal:** Replace `EndgamePerformanceSection` table with two side-by-side cards (No / Yes) on lg+, stacked on mobile — then redesigned mid-flight (Plan 05) into a single 3-card composite section: "Games ending in Middlegame" | "At Endgame Entry" | "Endgame results" with the Score Gap repositioned under Card 2 on desktop. Semantic equivalence: Card 1 = "without endgame" (SEC1-01 "Games without Endgame"); Card 3 = "with endgame" (SEC1-01 "Games with Endgame").

**Verified:** 2026-05-13T21:20:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Backend `EndgamePerformanceResponse` exposes `non_endgame_score_p_value: float | None` with identical n>=10 gating to `endgame_score_p_value` | VERIFIED | `app/schemas/endgames.py:153`; service `endgame_service.py:1769-1771` computes via `compute_confidence_bucket` on `non_endgame_wdl`; wired at line 1824 |
| 2 | Frontend `EndgamePerformanceResponse` carries `non_endgame_score_p_value: number | null` | VERIFIED | `frontend/src/types/endgames.ts:67` — field present |
| 3 | `EndgameOverallPerformanceSection.tsx` renders a 3-card composite (Cards 1+3 = WDL+score; Card 2 = entry eval + achievable score, no WDL) | VERIFIED | File exists at 418 lines; testids `tile-games-ending-middlegame`, `tile-at-endgame-entry`, `tile-endgame-results` all present (lines 361, 227, 375) |
| 4 | Card 1 and Card 3 show WDL bar + score bullet anchored at 0.50 (±0.15, sig-gated); Card 2 has NO WDL bar | VERIFIED | `MiniWDLBar` rendered in `EndgameCard` helper; `EntryCard` (Card 2) has no `MiniWDLBar`; `ENDGAME_TILE_SCORE_DOMAIN=0.15`, `SCORE_BULLET_CENTER` used; sig-gating triple (`isConfident`, `deriveLevel`, zone check) at lines 116-119 |
| 5 | Endgame Score Gap sits under Card 2 on desktop via `lg:col-start-2`; label "Endgame Score Gap"; value from `scoreGap.score_difference`; no sig gating | VERIFIED | Line 386: `lg:col-start-2`; line 389: label text; line 403: `value={scoreGap.score_difference}`; zone-color-only logic (lines 343-347), no sig-test |
| 6 | Legacy `EndgameStartVsEndSection.tsx`, `EndgameGamesWithWithoutSection.tsx`, `EndgamePerformanceSection.tsx` files no longer exist; no live imports | VERIFIED | All three files absent; `grep` of live imports and JSX mounts returns empty |
| 7 | `Endgames.tsx` mounts only `EndgameOverallPerformanceSection` (gated on `scoreGapData`); no mount of either legacy section remains | VERIFIED | `Endgames.tsx:21` import; `Endgames.tsx:420-422` single mount gated on `scoreGapData` |
| 8 | Frontend pipeline green: lint, typecheck, vitest (343 tests), knip, build | VERIFIED | All five gates passed: lint 0 warnings, tsc clean, 343 tests pass, knip clean, build succeeds |
| 9 | Backend pipeline green: ruff check, ty check, pytest (4 p-value tests pass) | VERIFIED | `ruff check` clean, `ty check` 0 errors, 4 p-value tests pass |

**Score:** 9/9 truths verified

---

### Deferred Items

None. All items in the phase scope are addressed by Plans 01-05.

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/schemas/endgames.py` | `non_endgame_score_p_value: float | None = None` on `EndgamePerformanceResponse` | VERIFIED | Line 153, with docstring |
| `app/services/endgame_service.py` | Wilson p-value computation on `non_endgame_wdl`, wired to response | VERIFIED | Lines 1762-1771 (compute), 1824 (wire) |
| `tests/test_endgame_service.py` | `test_non_endgame_score_p_value_gated_below_n_ten` covering both gate branches | VERIFIED | Lines 4107-4130; 4 tests pass |
| `frontend/src/types/endgames.ts` | `non_endgame_score_p_value: number | null` in `EndgamePerformanceResponse` | VERIFIED | Line 67 |
| `frontend/src/components/charts/EndgameOverallPerformanceSection.tsx` | 3-card composite section | VERIFIED | 418 lines, all required testids present, CR-01 offset-form preserved |
| `frontend/src/components/charts/__tests__/EndgameOverallPerformanceSection.test.tsx` | Component tests: layout, score math, sig-gating, empty-state, Card 2 rows | VERIFIED | All 6+ test categories present; 343 tests pass suite-wide |
| `frontend/src/pages/__tests__/Endgames.overallPerformance.test.tsx` | Page-level tests: single-mount, negative assertions for legacy sections | VERIFIED | File exists; negative assertions for `endgame-start-vs-end-section` and `endgame-games-with-without-section` present |
| `frontend/src/components/charts/EndgameScoreOverTimeChart.tsx` | Extracted chart (Plan 02, not deleted) | VERIFIED | File exists |
| `frontend/src/components/charts/EndgameGamesWithWithoutSection.tsx` | MUST NOT EXIST | VERIFIED | File absent |
| `frontend/src/components/charts/EndgameStartVsEndSection.tsx` | MUST NOT EXIST | VERIFIED | File absent |
| `frontend/src/components/charts/EndgamePerformanceSection.tsx` | MUST NOT EXIST | VERIFIED | File absent |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `Endgames.tsx` | `EndgameOverallPerformanceSection` | import + JSX mount | WIRED | Line 21 (import), line 421 (mount) |
| `EndgameOverallPerformanceSection` (Cards 1+3) | `data.non_endgame_score_p_value` / `data.endgame_score_p_value` | props to `EndgameCard` | WIRED | Lines 366, 380 |
| `EndgameOverallPerformanceSection` (Score Gap) | `scoreGap.score_difference` | `MiniBulletChart value=` | WIRED | Line 403 |
| `EndgameCard` (score row) | `wilsonBounds(score, total)` | `scoreConfidence.ts` | WIRED | Line 121 |
| `EndgameCard` (sig gating) | `isConfident(deriveLevel(p, n))` | `significance.ts` + local helper | WIRED | Lines 86-91, 116-119 |
| `EntryCard` (achievable score) | CR-01 offset-form `neutralMin/Max` | `ENTRY_EXPECTED_SCORE_NEUTRAL_MIN - SCORE_BULLET_CENTER` | WIRED | Lines 302-303 |
| `app/services/endgame_service.py` | `compute_confidence_bucket` | Wilson p-value call on `non_endgame_wdl` | WIRED | Lines 1762-1771 |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `EndgameOverallPerformanceSection` | `data.non_endgame_wdl`, `data.endgame_wdl`, `data.non_endgame_score_p_value` | API response via `overviewData` TanStack Query in `Endgames.tsx` | Yes — backend aggregates live DB rows | FLOWING |
| `EndgameOverallPerformanceSection` | `scoreGap.score_difference` | `overviewData.score_gap_material` | Yes — computed from game data | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Backend p-value gate: None below n=10, float in [0,1] above | `uv run pytest tests/test_endgame_service.py -x -k "non_endgame_score_p_value"` | 4 passed | PASS |
| Frontend component tests (all 343) | `cd frontend && npm test -- --run` | 343 passed | PASS |
| TypeScript compilation | `cd frontend && npx tsc --noEmit` | 0 errors | PASS |
| ESLint | `cd frontend && npm run lint -- --max-warnings=0` | 0 warnings | PASS |
| Knip (dead exports) | `cd frontend && npm run knip` | Clean | PASS |
| Production build | `cd frontend && npm run build` | Succeeded | PASS |
| Backend ruff + ty | `uv run ruff check app/ tests/ && uv run ty check app/ tests/` | All checks passed | PASS |

---

### Probe Execution

No probe scripts declared for this phase.

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| SEC1-01 | Plans 03, 05 | Two side-by-side cards on lg+ (No / Yes), stacked on mobile | SATISFIED | Redesign: Card 1 "Games ending in Middlegame" (= no endgame) + Card 3 "Endgame results" (= with endgame) in `lg:grid-cols-3`; semantic equivalence confirmed by CONTEXT redesign notes |
| SEC1-02 | Plans 03, 05 | Each card shows WDL bar | SATISFIED | `MiniWDLBar` in `EndgameCard` helper; Card 2 intentionally excluded per redesign (checkpoint metric, no WDL); Cards 1+3 have WDL bars |
| SEC1-03 | Plans 01, 02, 03, 05 | Per-card chess-score bullet anchored at 0.50, Wilson CI, Wilson p-value | SATISFIED | `wilsonBounds`, `SCORE_BULLET_CENTER=0.5`, `ENDGAME_TILE_SCORE_DOMAIN=0.15`; `non_endgame_score_p_value` + `endgame_score_p_value` both consumed |
| SEC1-04 | Plans 03, 05 | Full-width Score Gap footer bullet (Yes − No, center 0) | SATISFIED | `endgame-score-gap` tile with `lg:col-start-2` placement; `value=scoreGap.score_difference`; `center=0`, `SCORE_GAP_NEUTRAL_MIN/MAX`, `SCORE_GAP_DOMAIN=0.20` |
| SEC1-05 | Plans 03, 05 | Per-card score row `InfoPopover` explaining 0.50 natural anchor | SATISFIED | `InfoPopover` in `EndgameCard` with copy explaining balanced-WDL anchor vs population p50 (lines 163-170) |
| SEC1-06 | Plans 01, 02, 03, 05 | Sig gating: n >= MIN_GAMES_FOR_RELIABLE_STATS AND p < 0.05 AND outside neutral band | SATISFIED | `deriveLevel` + `isConfident` + `scoreZoneColor !== ZONE_NEUTRAL` triple at lines 116-120 |
| SEC1-07 | Plans 04, 05 | Legacy `EndgamePerformanceSection` table removed; knip clean | SATISFIED | `EndgamePerformanceSection.tsx`, `EndgameStartVsEndSection.tsx`, `EndgameGamesWithWithoutSection.tsx` all absent; knip clean |

All 7 SEC1 requirements satisfied.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | No TBD/FIXME/XXX markers found in phase-modified files | — | None |

Scanned `EndgameOverallPerformanceSection.tsx`, `app/schemas/endgames.py`, `app/services/endgame_service.py`, `tests/test_endgame_service.py`. No debt markers found.

The only `return null`-adjacent pattern is the conditional rendering gates (`showWdl ? ... : <p>Not enough data yet</p>`) which are correct empty-state implementations, not stubs.

---

### Human Verification Required

**Plan 04 contained a `checkpoint:human-verify` task (Task 3, blocking) that the autonomous executor deferred to the orchestrator.** Plan 05 replaced the section design entirely (autonomous: true), but the visual UAT checkpoint was never explicitly signed off.

#### 1. Visual UAT of the 3-card Endgame Overall Performance section

**Test:** Start the dev environment (`bin/run_local.sh`), visit `http://localhost:5173/endgames`, log in (or use guest mode with imported games).

**Expected — layout:**
- Under the "Endgame Overall Performance" h2 on the Endgames page: a question line "Do you perform better or worse when games reach an endgame?" with no section h3 or info-icon above the cards.
- Three cards side-by-side on lg+ viewports: LEFT "Games ending in Middlegame", CENTER "At Endgame Entry", RIGHT "Endgame results".
- On mobile (< 1024px) the three cards stack vertically (middlegame, entry, results top-to-bottom).
- Cards 1 and 3 each show a WDL bar + "Score: NN%" row with a bullet anchored at 50%.
- Card 2 shows TWO rows only (no WDL bar): "Endgame entry eval: ±X.Xp" with Cpu icon, and "Achievable score: NN%".
- A "Endgame Score Gap" tile sits below Card 2 on desktop (column 2) and after Card 3 on mobile.

**Expected — sig gating:**
- Score values in Cards 1 and 3 are tinted (green or red) only when the score is clearly lopsided AND n >= 10 AND p < 0.05.
- Scores near 50% or with small n remain default text color.

**Expected — legacy removal:**
- No "Games with vs without Endgame" section h3 anywhere on the page.
- No legacy WDL table (`Endgame | Games | Win/Draw/Loss | Score | Score Gap` headers).
- The "Where you start" and "What you do with it" tiles from the old `EndgameStartVsEndSection` are gone.

**Expected — popovers:**
- Hovering the info icon on the Score row of Cards 1 or 3 shows the 0.50 natural anchor explanation (no rating-tier confound, not a population statistic).
- No em-dash in popover copy, or at most one per paragraph.

**Why human:** Visual layout, mobile stacking, popover appearance, sig-gating color rendering, and absence of the legacy table cannot be verified programmatically.

---

### Gaps Summary

No technical gaps. All 9 must-have truths are VERIFIED. All 7 SEC1 requirements are SATISFIED. All automated gates (lint, typecheck, vitest, knip, build, ruff, ty, pytest) pass. The single outstanding item is the human visual UAT checkpoint that was deferred by the executor in Plan 04 and not reinstated in Plan 05.

---

_Verified: 2026-05-13T21:20:00Z_
_Verifier: Claude (gsd-verifier)_
