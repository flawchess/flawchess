---
phase: 76-frontend-score-coloring-confidence-badges-label-reframe
verified: 2026-04-28T17:11:00Z
status: passed_with_notes
score: 11/11 must-haves verified
overrides_applied: 0
manual_qa: deferred
review_findings:
  blocker: 0
  high: 0
  medium: 2
  low: 4
  info: 5
notes:
  - "MD-01 (MEDIUM, OpeningFindingCard.tsx:88-98): Confidence-line tooltip uses Tooltip which suppresses non-mouse pointers — D-10/D-25 mobile-parity violation. Recommend swap to InfoPopover before merge to satisfy locked decision; not a goal-blocker because the textual content (Confidence + level word) is still visible without the tooltip."
  - "MD-02 (MEDIUM, score_confidence.py:41): compute_confidence_bucket(n=0) raises ZeroDivisionError. Latent — current SQL HAVING gates ensure n>=1; harden when convenient."
  - "4 LOW + 5 INFO findings catalogued in 76-REVIEW.md (LO-01..LO-04, plus info items). All non-blocking polish."
  - "Manual mobile QA at 375px auto-approved per AUTO_MODE policy. Seven concrete check items documented in 76-08-SUMMARY.md as post-merge user action."
quality_gates:
  backend_pytest: "1156 passed (per 76-08-SUMMARY; spot-check of touched-file subset green: 14/14 in test_score_confidence + test_opening_insights_arrow_consistency)"
  backend_ty: "All checks passed"
  backend_ruff: "All checks passed"
  frontend_lint: "0 errors"
  frontend_knip: "clean"
  frontend_tsc: "clean"
  frontend_vitest: "161 passed (spot-check arrowColor.test.ts: 25/25 green)"
---

# Phase 76: Frontend — Score Coloring, Confidence Badges, Label Reframe — Verification Report

**Phase Goal:** Migrate Move Explorer + Opening Insights UI from win-rate-based prose and the 4-arg arrow-color signature onto a score-based / confidence-aware contract, with shared backend confidence helper, extended `NextMoveEntry` payload, score-tinted rows + arrows, "Confidence" indicator on cards, four section-title InfoPopovers, and INSIGHT-UI-04 descope.

**Verified:** 2026-04-28T17:11:00Z
**Status:** passed_with_notes
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #   | Truth                                                                                                                       | Status     | Evidence                                                                                                                                                                                                                                              |
| --- | --------------------------------------------------------------------------------------------------------------------------- | ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Shared `score_confidence.py` module exists with `compute_confidence_bucket`, used by BOTH services                          | VERIFIED   | `app/services/score_confidence.py:22-61` defines `compute_confidence_bucket(w, d, losses, n) -> tuple[Literal[...], float]`. Imported at `opening_insights_service.py:39` (used line 388) and `openings_service.py:24` (used line 448).               |
| 2   | `OpeningInsightFinding` (Pydantic + TS) carries `score`/`confidence`/`p_value` and no `loss_rate`/`win_rate`                | VERIFIED   | `app/schemas/opening_insights.py:73-81` (score/confidence/p_value with Field constraints, no loss_rate/win_rate). `frontend/src/types/insights.ts:69-88` mirrors exactly.                                                                              |
| 3   | `NextMoveEntry` (Pydantic + TS) extended with `score`/`confidence`/`p_value`                                                | VERIFIED   | `app/schemas/openings.py:185-207` (score/confidence/p_value added). `frontend/src/types/api.ts:93-108` mirrors. Service populates them at `openings_service.py:447-448`.                                                                                |
| 4   | `compute_insights` re-sorts each section by `(confidence DESC, |score-0.50| DESC)`                                          | VERIFIED   | `opening_insights_service.py:270-281` defines `_CONFIDENCE_RANK` (high=0, medium=1, low=2) and `_rank_section` sorts by `(_CONFIDENCE_RANK[f.confidence], -abs(f.score - 0.5))`.                                                                       |
| 5   | `getArrowColor` rewritten to score-based effect-size buckets with 3-arg signature `(score, gameCount, isHovered)`            | VERIFIED   | `frontend/src/lib/arrowColor.ts:38-48` — `getArrowColor(score, gameCount, isHovered)`. Bucket boundaries match D-12: ≥0.60 DARK_GREEN, ≥0.55 LIGHT_GREEN, ≤0.40 DARK_RED, ≤0.45 LIGHT_RED, else GREY. Strict `>=`/`<=`. `LIGHT_COLOR_THRESHOLD`/`DARK_COLOR_THRESHOLD` removed. |
| 6   | All callers use new 3-arg signature with `entry.score`                                                                      | VERIFIED   | `MoveExplorer.tsx:235`: `getArrowColor(entry.score, entry.game_count, false)`. `Openings.tsx:407`: `getArrowColor(entry.score, entry.game_count, isHovered)`. No remaining 4-arg callers found.                                                       |
| 7   | MoveExplorer renders a Conf column between Games and Results, with `low`/`med`/`high` labels                                | VERIFIED   | `MoveExplorer.tsx:179-183` adds `<th>Conf</th>`. `MoveExplorer.tsx:302-304` renders `<td>` with `entry.confidence === 'medium' ? 'med' : entry.confidence`. Plain grey text per D-08. Mute trigger extends to `confidence === 'low'` at line 228-229. |
| 8   | OpeningFindingCard renders score-prose ("You score X% as &lt;Color&gt; after &lt;san&gt;") AND a "Confidence: ..." line in BOTH mobile and desktop | VERIFIED   | `OpeningFindingCard.tsx:75-86` (proseLine) and `:89-98` (confidenceLine). Mobile branch lines 137-151 includes both `proseLine` and `confidenceLine`. Desktop branch lines 154-166 includes both. UNRELIABLE_OPACITY mute at lines 53-58.                       |
| 9   | OpeningInsightsBlock renders four InfoPopover triggers (one per section header), each with shared copy                       | VERIFIED   | `OpeningInsightsBlock.tsx:14-27` defines single `OPENING_INSIGHTS_POPOVER_COPY` (Draft A locked text). `FindingsSection` lines 229-235 renders one `<InfoPopover>` per section. `SECTIONS` array lines 52-77 has 4 entries → 4 popovers.               |
| 10  | INSIGHT-UI-04 marked DESCOPED in REQUIREMENTS.md per D-04                                                                   | VERIFIED   | `.planning/REQUIREMENTS.md:29` — `[x]` checkbox + strikethrough original text + "DESCOPED 2026-04-28 per Phase 76 D-04" + footer amendment line at line 68.                                                                                            |
| 11  | CHANGELOG.md `## [Unreleased]` has Phase 76 entries (Added/Changed/Fixed)                                                   | VERIFIED   | `CHANGELOG.md` lines 9-25 — 3 Added, 4 Changed, 1 Fixed bullets, all annotated `(Phase 76)`.                                                                                                                                                          |

**Score:** 11/11 truths verified

### Required Artifacts

| Artifact                                                      | Expected                                                       | Status      | Details                                                                                                  |
| ------------------------------------------------------------- | -------------------------------------------------------------- | ----------- | -------------------------------------------------------------------------------------------------------- |
| `app/services/score_confidence.py`                            | New module, `compute_confidence_bucket` returns (bucket, p)    | VERIFIED    | 62 lines. Imports SCORE_PIVOT, half-width constants. Migrated body, widened signature.                   |
| `app/services/opening_insights_service.py`                    | Imports compute_confidence_bucket; sorts by confidence DESC    | VERIFIED    | Import at line 39; usage at 388; `_rank_section` at 270-281.                                             |
| `app/services/openings_service.py`                            | Imports compute_confidence_bucket; populates NextMoveEntry     | VERIFIED    | Import at line 24; usage at 447-448 alongside score derivation.                                          |
| `app/schemas/openings.py` `NextMoveEntry`                     | Adds score/confidence/p_value Pydantic fields                  | VERIFIED    | Lines 199-207 with Field constraints + Literal type.                                                     |
| `app/schemas/opening_insights.py` `OpeningInsightFinding`     | Has score/confidence/p_value, no loss_rate/win_rate            | VERIFIED    | Lines 73-81. No loss_rate/win_rate references in schema.                                                 |
| `frontend/src/lib/arrowColor.ts`                              | 3-arg signature; score buckets; old thresholds removed          | VERIFIED    | Lines 38-48. `LIGHT_COLOR_THRESHOLD`/`DARK_COLOR_THRESHOLD` removed (grep confirms no occurrences).      |
| `frontend/src/lib/openingInsights.ts`                         | Stale constants removed; helpers retained                      | VERIFIED    | `INSIGHT_RATE_THRESHOLD`, `INSIGHT_THRESHOLD_COPY`, `MIN_GAMES_FOR_INSIGHT` not present (grep + tests). |
| `frontend/src/types/insights.ts` `OpeningInsightFinding`      | score/confidence/p_value added; loss_rate/win_rate removed     | VERIFIED    | Lines 69-88 mirror Pydantic schema.                                                                      |
| `frontend/src/types/api.ts` `NextMoveEntry`                   | score/confidence/p_value added                                 | VERIFIED    | Lines 93-108.                                                                                            |
| `frontend/src/components/move-explorer/MoveExplorer.tsx`      | Conf column + score-tint + extended mute (n<10 OR low)          | VERIFIED    | Header line 183, cell 302-304, mute trigger 228-229, score-tint 235.                                    |
| `frontend/src/components/insights/OpeningFindingCard.tsx`     | Score prose + Confidence line + mute, both mobile & desktop    | VERIFIED    | Both layouts include proseLine + confidenceLine. Mute at 53-58.                                          |
| `frontend/src/components/insights/OpeningInsightsBlock.tsx`   | Four InfoPopover triggers using shared copy                    | VERIFIED    | One InfoPopover per FindingsSection × 4 sections; copy constant at lines 14-27.                          |
| `tests/services/test_score_confidence.py`                     | New unit test file for migrated helper                         | VERIFIED    | File exists; spot-check 14 tests passed in 0.10s alongside arrow consistency test.                       |
| `frontend/src/lib/arrowColor.test.ts`                         | Score-based bucket boundary tests                              | VERIFIED    | Spot-check 25/25 tests passed in vitest run.                                                             |

### Key Link Verification

| From                          | To                                       | Via                                | Status | Details                                                                                            |
| ----------------------------- | ---------------------------------------- | ---------------------------------- | ------ | -------------------------------------------------------------------------------------------------- |
| opening_insights_service      | score_confidence.compute_confidence_bucket | `from .. import` + call           | WIRED  | Import line 39, call line 388 with `(row.w, row.d, row.l, row.n)`.                                  |
| openings_service              | score_confidence.compute_confidence_bucket | `from .. import` + call           | WIRED  | Import line 24, call line 448 with `(w, d, lo, gc)`.                                                |
| MoveExplorer.tsx              | NextMoveEntry.confidence/score           | direct field reads                 | WIRED  | `entry.score` (line 235), `entry.confidence` (228, 303). Mute trigger uses confidence.              |
| OpeningFindingCard.tsx        | OpeningInsightFinding.score/confidence    | direct field reads + render        | WIRED  | `finding.score` (line 46), `finding.confidence` (54, 90, 95). Tooltip wraps confidence indicator.   |
| OpeningInsightsBlock.tsx      | InfoPopover                              | imported component + 4 instances   | WIRED  | Import line 5; rendered inside FindingsSection lines 229-235; SECTIONS has 4 entries.              |
| Openings.tsx                  | getArrowColor                            | 3-arg call with entry.score        | WIRED  | Line 407: `getArrowColor(entry.score, entry.game_count, isHovered)`.                                |
| MoveExplorer.tsx              | getArrowColor                            | 3-arg call for row tint            | WIRED  | Line 235: `getArrowColor(entry.score, entry.game_count, false)`.                                    |

### Data-Flow Trace (Level 4)

| Artifact                  | Data Variable          | Source                                                                  | Produces Real Data | Status   |
| ------------------------- | ---------------------- | ----------------------------------------------------------------------- | ------------------ | -------- |
| MoveExplorer Conf column  | entry.confidence       | NextMoveEntry → openings_service.get_next_moves → compute_confidence_bucket(w,d,lo,gc) | Yes (live SQL aggregates feed Wald computation) | FLOWING  |
| MoveExplorer row tint     | entry.score            | openings_service.get_next_moves line 447 (W + 0.5D)/N                   | Yes                | FLOWING  |
| OpeningFindingCard prose  | finding.score          | opening_insights_service classify_row (Phase 75) + ranked at line 280   | Yes                | FLOWING  |
| OpeningFindingCard conf   | finding.confidence     | opening_insights_service line 388 — compute_confidence_bucket           | Yes                | FLOWING  |
| OpeningInsightsBlock sort | findings array         | API response sorted server-side per D-03                                | Yes                | FLOWING  |
| Section InfoPopover copy  | OPENING_INSIGHTS_POPOVER_COPY | Static React fragment (Draft A locked)                          | N/A (static)       | FLOWING  |

No HOLLOW_PROP / DISCONNECTED / STATIC findings.

### Behavioral Spot-Checks

| Behavior                                                  | Command                                                                        | Result            | Status |
| --------------------------------------------------------- | ------------------------------------------------------------------------------ | ----------------- | ------ |
| score_confidence + arrow consistency Python tests pass    | `uv run pytest tests/services/test_score_confidence.py tests/services/test_opening_insights_arrow_consistency.py -q` | 14 passed in 0.10s | PASS   |
| arrowColor.test.ts (Phase 76 score-based)                 | `cd frontend && npx vitest run src/lib/arrowColor.test.ts`                     | 25 tests passed   | PASS   |
| Stale constants removed (regression)                      | `grep -rn "LIGHT_COLOR_THRESHOLD\|DARK_COLOR_THRESHOLD\|INSIGHT_RATE_THRESHOLD\|INSIGHT_THRESHOLD_COPY" frontend/src/` | Only test-asserted absences | PASS   |
| compute_confidence_bucket called consistently both services | grep `compute_confidence_bucket\|score_confidence` in services/                | Both services import + call shared helper | PASS   |

Full-suite gates already executed by orchestrator per 76-08-SUMMARY.md (1156 pytest, 161 vitest, ty/ruff/lint/knip/tsc all clean) — not re-run here.

### Requirements Coverage

| Requirement   | Source Plan       | Description                                                          | Status     | Evidence                                                                                                           |
| ------------- | ----------------- | -------------------------------------------------------------------- | ---------- | ------------------------------------------------------------------------------------------------------------------ |
| INSIGHT-UI-01 | 76-03             | arrowColor migrated from loss-rate to score; effect-size only         | SATISFIED  | arrowColor.ts:38-48 score buckets; 25/25 vitest assertions pass.                                                   |
| INSIGHT-UI-02 | 76-05             | Move Explorer row tint score-based, WDL bars unchanged                | SATISFIED  | MoveExplorer.tsx:235 row tint via getArrowColor(entry.score,...). MiniWDLBar untouched (line 309).                  |
| INSIGHT-UI-03 | 76-01, 76-02, 76-05 | Three-level confidence indicator (low/med/high) on moves-list rows  | SATISFIED  | NextMoveEntry.confidence wired end-to-end; Conf column renders labels at MoveExplorer.tsx:302-304.                  |
| INSIGHT-UI-04 | (descoped)        | Soften severity copy per SEED-008                                     | DESCOPED   | REQUIREMENTS.md:29 marked `[x]` DESCOPED 2026-04-28 per D-04. Footer amendment line at 68 documents rationale.    |
| INSIGHT-UI-05 | 76-06             | Confidence badge on each Opening Insights card                        | SATISFIED  | OpeningFindingCard.tsx:89-98 confidence line; mute extends per D-11; both mobile & desktop layouts.                 |
| INSIGHT-UI-06 | 76-07             | Explainer popover triggered by `?` icon on section title              | SATISFIED  | OpeningInsightsBlock.tsx:229-235 InfoPopover per section × 4. Copy constant lines 14-27 (locked Draft A).           |
| INSIGHT-UI-07 | 76-05, 76-06, 76-08 | Mobile parity for all changes at 375px                              | NEEDS_HUMAN | Conf column markup viewport-agnostic; OpeningFindingCard mobile branch includes confidenceLine; manual 375px QA deferred per AUTO_MODE (see notes). MD-01 (Tooltip → InfoPopover) flagged as a mobile-parity concern for the card's confidence indicator. |

No orphaned requirements: REQUIREMENTS.md lines 59-65 map INSIGHT-UI-01..07 to Phase 76; all accounted for.

### Anti-Patterns Found

| File                                       | Line   | Pattern                                                  | Severity   | Impact                                                                                  |
| ------------------------------------------ | ------ | -------------------------------------------------------- | ---------- | --------------------------------------------------------------------------------------- |
| OpeningFindingCard.tsx                     | 88-98  | Tooltip wrapping non-interactive `<p>`; mouse-only trigger | WARNING    | MD-01 — D-10/D-25 mobile parity not satisfied for the card's confidence indicator.       |
| score_confidence.py                        | 41     | Unconditional `(w + 0.5*d) / n` — ZeroDivisionError if n=0 | WARNING    | MD-02 — latent crash. Current SQL HAVING gates n>=1 so unreachable today.                |
| opening_insights_service.py                | 280    | `_CONFIDENCE_RANK[f.confidence]` (KeyError on contract drift) | INFO    | LO-01 polish; Pydantic Literal makes it unreachable today.                               |
| OpeningFindingCard.tsx                     | 43-50  | Comment describes unreachable case (post-effect-size gate) | INFO       | LO-02 — misleading docstring; defensive code itself is harmless.                         |
| OpeningFindingCard.tsx                     | 48-49  | Hard-coded `50` (CLAUDE.md anti-magic-number)             | INFO       | LO-03 — `SCORE_PIVOT * 100` would be cleaner.                                           |
| score_confidence.py                        | 22-24  | `losses` parameter accepted but unused                    | INFO       | LO-04 — kept for (W,D,L,N) calling convention symmetry; documented in docstring lines 38-40. |

### Human Verification Required

Auto-approved per AUTO_MODE policy at the Phase 76-08 checkpoint. Seven manual checks documented in 76-08-SUMMARY.md as **post-merge user action** (manual_qa: deferred):

1. **Move Explorer Conf column at 375px** — all four columns (Move, Games, Conf, WDL) render without horizontal scroll on iPhone SE emulation; `low/med/high` legible at `text-xs`.
2. **Low-confidence row mute** — row with `game_count < 10` or `confidence = "low"` renders at ~50% opacity.
3. **InfoPopover tap-target × 4** — single tap on `?` icon next to each section title opens popover; tap outside dismisses; ≥44×44px effective touch area.
4. **Card confidence tooltip** — tap or long-press on "Confidence: medium/low/high" surfaces the level-specific explainer copy. **NB:** MD-01 may cause this to fail on touch devices (Tooltip is mouse-only). Recommend re-checking after MD-01 fix.
5. **Visual mute + deep-link pulse** — bookmark a low-confidence position; deep-link pulse fires over the muted row tint without one wiping the other.
6. **Score-prose rounding edge case** — finding with `score = 0.499` in weakness section displays `49.9%` (toFixed(1) fallback), not `50%`.
7. **Section tint sanity** — red-tinted Insights cards never display ≥50%; green-tinted cards never display ≤50%.

### Gaps Summary

No goal-blocking gaps. All 11 must-haves verify against codebase evidence: shared `score_confidence` helper exists and is consumed by both services, schemas (Pydantic + TS) carry the new contract, sort + score-bucket logic match D-03/D-12 boundaries, MoveExplorer/OpeningFindingCard/OpeningInsightsBlock render all required surfaces in both desktop and mobile layouts, INSIGHT-UI-04 descoped with audit trail, CHANGELOG entries present.

Two MEDIUM findings from code review (MD-01, MD-02) are non-blocking but worth addressing:

- **MD-01** (recommended pre-merge fix per 76-REVIEW.md): The Confidence-line tooltip violates D-10 ("tap-friendly tooltip pattern") because it uses the shared `Tooltip` component which suppresses non-mouse pointers. Section-title popovers correctly use `InfoPopover`; the card was missed. Suggested fix in 76-REVIEW.md is a 12-line swap to `InfoPopover` + test update from hover to click assertions.
- **MD-02** (latent): `compute_confidence_bucket(... n=0)` raises `ZeroDivisionError`. Add `if n <= 0: return "low", 1.0` guard or assert upstream invariant uniformly.

Manual mobile QA deferred per AUTO_MODE — seven concrete check items in 76-08-SUMMARY.md to be executed post-merge by the user. Item 4 (card confidence tooltip on touch) is at risk pending MD-01 resolution.

---

_Verified: 2026-04-28T17:11:00Z_
_Verifier: Claude (gsd-verifier)_
