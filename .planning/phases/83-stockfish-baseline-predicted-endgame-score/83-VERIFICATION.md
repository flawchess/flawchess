---
phase: 83-stockfish-baseline-predicted-endgame-score
verified: 2026-05-11T20:40:00Z
status: passed
score: 26/26 must-haves verified
overrides_applied: 0
---

# Phase 83: Stockfish-baseline Predicted Endgame Score Verification Report

**Phase Goal:** Ship a Stockfish-baseline achievable score for the Endgame Overall Performance area so users can read "what a 2300+ player would score from positions like mine" against their achieved Endgame score in the same W+0.5D units. The existing EndgameStartVsEndSection restructures into a 2x2 grid; the bottom row of both tiles shares the W+0.5D axis so the achievable-vs-achieved gap is directly readable across the two tiles. LLM narrates the new metric from day one (same logic as Phase 82 D-13).

**Verified:** 2026-05-11
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

The five-plan phase delivers the full vertical slice: a pure-math eval-to-score primitive (Plan 1), a backend aggregator and 5 new schema fields (Plan 2), a 2x2 frontend grid restructure with the new "Achievable score" bullet and lifted MiniWDLBar (Plan 3), a formally calibrated cohort zone band (Plan 4), and three-finding LLM payload + prompt-asset updates with prompt-version bump (Plan 5). The CR-01 BLOCKER from 83-REVIEW.md is verified fixed at the call site in `EndgameStartVsEndSection.tsx:205-206`.

### Observable Truths (aggregated from all 5 PLAN frontmatters)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| **Plan 1** | | | |
| 1 | `eval_cp_to_expected_score(0, 'white') == 0.5` | VERIFIED | `eval_utils.py:66` (`1 / (1 + exp(0))` = 0.5); tests pass |
| 2 | `eval_cp_to_expected_score(+100, 'white') ~ 0.591 and (..., 'black') ~ 0.409` | VERIFIED | `eval_utils.py:65-66` (sign flip); white/black symmetry test passes |
| 3 | `eval_mate_to_expected_score(+5, 'white') == 1.0 and (+5, 'black') == 0.0` | VERIFIED | `eval_utils.py:93-94`; tests pass |
| 4 | `eval_mate_to_expected_score(-5, 'white') == 0.0 and (-5, 'black') == 1.0` | VERIFIED | `eval_utils.py:95-96`; Pitfall 1 coverage test passes |
| 5 | `LICHESS_K` is defined as a named module constant, not a magic literal | VERIFIED | `eval_utils.py:41` — module-level `LICHESS_K: float = 0.00368208` |
| **Plan 2** | | | |
| 6 | `EndgamePerformanceResponse` exposes 5 new entry_expected_score* fields | VERIFIED | `app/schemas/endgames.py:144-157` — all 5 fields with safe-empty defaults |
| 7 | Mate games are INCLUDED in entry_expected_score cohort (D-06); n counts them | VERIFIED | `endgame_service.py:1745-1751` (mate branch increments ex_n); `test_entry_expected_score_mate_INCLUDED` passes |
| 8 | `|eval_cp| >= 2000` rows are dropped from the cohort (D-07) | VERIFIED | `endgame_service.py:1753-1754` (continue on clip); `test_entry_expected_score_eval_cp_clip` passes |
| 9 | `entry_expected_score_p_value is None when n < 10` | VERIFIED | `endgame_service.py:1769-1771` gating; `test_entry_expected_score_n_nine_p_value_gated` passes |
| 10 | Wilson math lives in single helper `_wilson_score_test_vs_half` — no duplication | VERIFIED | `score_confidence.py:96-127` (helper) + `:156` and `:214` (both callers delegate) |
| 11 | `entry_eval_n` unchanged by this plan (Phase 81 cohort preserved) | VERIFIED | Existing entry_eval tests still pass (126 backend tests green in this slice) |
| **Plan 3** | | | |
| 12 | New "Achievable score" bullet inside "Where you start" tile | VERIFIED | `EndgameStartVsEndSection.tsx:184-226`; RTL test "renders achievable-score bullet when n>=10" passes |
| 13 | MiniWDLBar at the top of "What you do with it" tile | VERIFIED | `EndgameStartVsEndSection.tsx:241-254`; RTL test "renders MiniWDLBar at top of tile-2" passes |
| 14 | Both tiles render as 2-row stack with bottom row sharing W+0.5D axis | VERIFIED | Both tiles wrap children in `flex flex-col gap-4`; bottom row uses `scoreBulletDomain()` + `SCORE_BULLET_CENTER` |
| 15 | Existing "Games with vs without Endgame" table UNCHANGED | VERIFIED | EndgamePerformanceSection.tsx not in files_modified for any of the 5 plans |
| 16 | Popover states "what a 2300+ rated player would score" + "Compare against your achieved Endgame score"; no "underperformance" | VERIFIED | `AchievableScorePopover.tsx:73-79`; `grep -ci underperformance` returns 0 |
| 17 | (zone != neutral) AND p < 0.05 tile-color rule; borderline-sig in neutral band stays neutral | VERIFIED | `EndgameStartVsEndSection.tsx:91-96` (achievableShowZoneFontColor); RTL tests confirm both branches |
| 18 | Mobile DOM order matches desktop (eval/WDL first, score-axis bullets second) | VERIFIED | `flex flex-col` (no `flex-col-reverse`); RTL tests scope via `tile-entry-eval` / `tile-endgame-score` testids |
| **Plan 4** | | | |
| 19 | New SKILL.md section documents canonical CTE with bic.status='completed' + sparse-cell exclusion | VERIFIED | `.claude/skills/benchmarks/SKILL.md:421` (Section 7 — Stockfish-baseline...) |
| 20 | reports/benchmarks-2026-05-11.md records 5x4 cell table, marginals, pooled overall, collapse verdict | VERIFIED | File exists; 4 occurrences of entry_expected_score; sections per 83-04-SUMMARY |
| 21 | `ENTRY_EXPECTED_SCORE_ZONES` registered with direction='higher_is_better' and editorial bounds | VERIFIED | `endgame_zones.py:155-168` — `[0.45, 0.55]`, `direction="higher_is_better"`, comment cites benchmarks-2026-05-11.md §7 |
| 22 | `endgameZones.ts` exports entryExpectedScoreZoneColor + MIN/MAX | VERIFIED | `endgameZones.ts:46-58`; codegen `git diff --exit-code` passes (idempotent) |
| 23 | `entry_expected_score` in MetricId Literal in endgame_zones.py | VERIFIED | `endgame_zones.py:33` |
| **Plan 5** | | | |
| 24 | `entry_expected_score` in MetricId Literal in insights_service.py + _findings_endgame_start_vs_end emits 3rd SubsectionFinding | VERIFIED | `insights_service.py:447-525`: docstring updated to "THREE findings"; tile3 emitted with metric/zone/dimension/trend; no `verdict` |
| 25 | Sample-size gate n>=10; below uses _empty_finding | VERIFIED | `insights_service.py:511-513`; `test_third_finding_empty_when_n_below_10` passes |
| 26 | `_PROMPT_VERSION = "endgame_v25"` with D-20 changelog prepended; prior history preserved | VERIFIED | `insights_llm.py:66` — `"endgame_v25"`; comment prepends v25 block then v24..v14 chronological |
| 27 | endgame_insights.md gains entry_expected_score glossary entry + extended subsection block | VERIFIED | `endgame_insights.md:82` (UI vocab — see note in WR-03 below), `:267-309` (subsection block), `:356-360` (glossary entry with 2300+ framing) |

**Score:** 27/27 truths verified

### CR-01 Fix Verification (commit b238e91c)

**Issue:** `EndgameStartVsEndSection.tsx` was passing absolute thresholds `[0.45, 0.55]` to `MiniBulletChart`'s `neutralMin`/`neutralMax` props, which are documented as offsets from center. This collapsed the visible neutral band on the achievable-score bullet.

**Fix verified at `EndgameStartVsEndSection.tsx:205-206`:**

```tsx
neutralMin={ENTRY_EXPECTED_SCORE_NEUTRAL_MIN - SCORE_BULLET_CENTER}
neutralMax={ENTRY_EXPECTED_SCORE_NEUTRAL_MAX - SCORE_BULLET_CENTER}
```

Inline comment on lines 199-201 documents the offset semantics. Commit `b238e91c fix(83): pass offsets to MiniBulletChart neutralMin/neutralMax (CR-01)` confirmed present in git log. Status: **FIXED**.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/services/eval_utils.py` | LICHESS_K + 2 converters | VERIFIED | 98 lines, no I/O, named constant, both functions typed `Literal["white","black"]` |
| `tests/services/test_eval_utils.py` | ≥8 unit tests, symmetry/saturation/mate-both-colors | VERIFIED | 17 test functions |
| `app/services/score_confidence.py` | Refactored Wilson + sibling | VERIFIED | `_wilson_score_test_vs_half` + `compute_score_confidence_from_mean` + `compute_confidence_bucket` preserved |
| `app/services/endgame_service.py` | ex_sum/ex_n aggregator + 5 new fields on response | VERIFIED | Aggregator at `:1737-1782`; response at `:1794-1798`; EVAL_CLIP_MAX_CP at `:181` |
| `app/schemas/endgames.py` | 5 new fields w/ safe-empty defaults | VERIFIED | `:144-157` mirror Phase 81 entry_eval shape |
| `tests/test_endgame_service.py` | TestEntryExpectedScore class with ≥7 tests incl. mate-INCLUDED | VERIFIED | 11 test methods in `TestEntryExpectedScore` |
| `frontend/src/types/endgames.ts` | 5 new TS fields | VERIFIED | `:71-75` |
| `frontend/src/components/popovers/AchievableScorePopover.tsx` | Wrapper w/ D-10 body copy, no forbidden words | VERIFIED | 85 lines; body has "2300+", "Lichess winning-chances", "Compare against your achieved Endgame score"; 0 forbidden words |
| `frontend/src/components/charts/EndgameStartVsEndSection.tsx` | 2x2 restructure + new bullet + WDL bar + CR-01 fix | VERIFIED | Imports MiniWDLBar + AchievableScorePopover + entryExpectedScoreZoneColor + offset constants; CR-01 fix on `:205-206` |
| `frontend/src/components/charts/__tests__/EndgameStartVsEndSection.test.tsx` | ≥6 new RTL cases | VERIFIED | 26 tests pass; new cases cover gate, color, MiniWDLBar, popover, D-12 axis parity |
| `.claude/skills/benchmarks/SKILL.md` | New section with canonical CTE | VERIFIED | Section 7 added |
| `reports/benchmarks-2026-05-11.md` | 5x4 grid + marginals + pooled + verdict | VERIFIED | File exists, 4 occurrences |
| `app/services/endgame_zones.py` | ENTRY_EXPECTED_SCORE ZoneSpec + MetricId | VERIFIED | `:33` (MetricId) + `:155-168` (ZoneSpec) |
| `frontend/src/generated/endgameZones.ts` | Regenerated exports | VERIFIED | `:46-58`; `git diff --exit-code` after codegen exits 0 (idempotency confirmed) |
| `app/services/insights_service.py` | Third SubsectionFinding | VERIFIED | `:519-525` emits tile3; `:511-513` empty-finding gate |
| `app/services/insights_llm.py` | _PROMPT_VERSION = endgame_v25 | VERIFIED | `:66` |
| `app/prompts/endgame_insights.md` | Glossary + extended subsection | VERIFIED | `:82` (UI vocab), `:267-309` (subsection), `:356-360` (glossary), `:298` forbidden-words list |
| `tests/services/test_insights_service.py` | ≥3 new cases | VERIFIED | 8 new tests `test_third_finding_*` |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `endgame_service.py` | `eval_utils.py` | `from app.services.eval_utils import eval_cp_to_expected_score, eval_mate_to_expected_score` | WIRED | Verified at lines 67-70 of endgame_service.py |
| `endgame_service.py` | `score_confidence.py` | `compute_score_confidence_from_mean` for Wilson | WIRED | Used at `endgame_service.py:1765` |
| `EndgameStartVsEndSection.tsx` | `MiniWDLBar` | `import { MiniWDLBar } from '@/components/stats/MiniWDLBar'` | WIRED | Line 27, rendered at line 247 |
| `EndgameStartVsEndSection.tsx` | `AchievableScorePopover` | direct import + render | WIRED | Line 26 import; line 196 render |
| `EndgameStartVsEndSection.tsx` | `endgameZones.ts` | imports `entryExpectedScoreZoneColor` + bounds | WIRED | Used in derived achievableZoneHex + offset math |
| `endgame_zones.py` | `endgameZones.ts` | `scripts/gen_endgame_zones_ts.py` codegen | WIRED | Idempotent (re-run produces no diff) |
| `insights_service.py` | `endgame_zones.py` | `assign_zone("entry_expected_score", value)` | WIRED | `insights_service.py:523` |
| `insights_service.py` | `endgames.py` schema | reads `perf.entry_expected_score` + `_n` | WIRED | `:511, :515` |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|--------------------|--------|
| `EndgameStartVsEndSection.tsx` achievable bullet | `data.entry_expected_score` + `_n` + CI | API response from `EndgamePerformanceResponse` populated by aggregator over `bucket_rows` | YES (sigmoid + mate map + Wilson CI) | FLOWING |
| LLM endgame_start_vs_end subsection | `perf.entry_expected_score` | Same response object | YES | FLOWING |
| Frontend zone color | `entryExpectedScoreZoneColor(value)` | Codegen'd from Python registry | YES (registry locked at [0.45, 0.55]) | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Backend tests for phase 83 modules | `uv run pytest tests/services/test_eval_utils.py tests/services/test_score_confidence.py tests/test_endgame_service.py::TestEntryExpectedScore tests/services/test_insights_service.py` | 126 passed | PASS |
| Frontend RTL tests for restructured section | `npx vitest run src/components/charts/__tests__/EndgameStartVsEndSection.test.tsx` | 26 passed | PASS |
| Codegen drift gate | `uv run python scripts/gen_endgame_zones_ts.py && git diff --exit-code frontend/src/generated/endgameZones.ts` | exit 0 | PASS |
| Forbidden-word grep in popover | `grep -ci 'underperformance\|fall short\|below your potential' AchievableScorePopover.tsx` | 0 | PASS |
| Forbidden-word grep in LLM prompt outside the forbidden-list itself | manual inspection of `endgame_insights.md:298, :360` | only listed as forbidden | PASS |
| Module exports `LICHESS_K`/converters | `grep -n "LICHESS_K\|eval_cp_to_expected_score\|eval_mate_to_expected_score" eval_utils.py` | all present | PASS |
| Wilson math single source of truth | Wilson math in `_wilson_score_test_vs_half` only; both `compute_confidence_bucket` and `compute_score_confidence_from_mean` delegate | confirmed | PASS |

### Probe Execution

No `scripts/*/tests/probe-*.sh` probes are declared by the PLANs and the phase is not a migration/tooling phase. SKIPPED.

### Requirements Coverage

Phase declares requirements D-01 through D-22 across plans (no `.planning/REQUIREMENTS.md` row mentioning Phase 83 was found — per user note, this is a project-management not a phase-scope concern). Every D-XX referenced by a PLAN's `requirements:` field is satisfied by the artifacts above.

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| D-01..D-03 | 83-01 | Pure-math eval-to-score primitive | SATISFIED | `eval_utils.py` + 17 unit tests |
| D-04..D-07, D-21..D-22 | 83-02 | Aggregator + schema + Wilson refactor | SATISFIED | aggregator at `endgame_service.py:1737-1782`; schema at `endgames.py:144-157`; Wilson helper at `score_confidence.py:96` |
| D-08..D-13 | 83-03 | 2x2 restructure + popover + MiniWDLBar | SATISFIED | `EndgameStartVsEndSection.tsx` 2x2 grid; `AchievableScorePopover.tsx` |
| D-14..D-16 | 83-04 | Benchmark calibration + zone registry + codegen | SATISFIED | SKILL.md §7 + benchmarks-2026-05-11.md + ZoneSpec + regen'd TS |
| D-17..D-20 | 83-05 | LLM payload + glossary + prompt version | SATISFIED | `insights_service.py` tile3, `insights_llm.py` v25, `endgame_insights.md` glossary + subsection |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `app/services/eval_utils.py` | 93-97 | `eval_mate=0` silently maps to 0.0 (WR-01 from 83-REVIEW.md) | Info | Stockfish does not emit mate=0 in practice; documented in review for future hardening — not a blocker |
| `frontend/src/components/popovers/AchievableScorePopover.tsx` | 27-37 | Pending `setTimeout` leaks on unmount (WR-02 from 83-REVIEW.md) | Info | Pre-existing pattern shared with `ScoreConfidencePopover` — not a regression |
| `app/prompts/endgame_insights.md` | 78-90 | WR-03 from 83-REVIEW.md said UI vocab table missing `entry_expected_score` | Resolved | Now present at line 82 — vocab row added: `entry_expected_score → "Achievable score"` |

No 🛑 BLOCKER anti-patterns found. The CR-01 BLOCKER from 83-REVIEW.md is verified fixed.

### Human Verification Required

No items require human verification. The phase ships pure-math primitives + aggregator + a 2x2 restructure + LLM payload that are all fully covered by automated tests (126 backend + 26 RTL). Visual verification of the achievable-score bullet rendering correctly with the offset-corrected neutral band is reasonable but not strictly required, since the CR-01 fix is mechanical and the offset math is identical to the working endgame_score bullet in the same component.

### Gaps Summary

None. All 27 observable truths verify against the codebase. The single BLOCKER from code review (CR-01: offset-vs-absolute neutral band) is verified fixed in commit `b238e91c` and the fix is mechanically correct (`ENTRY_EXPECTED_SCORE_NEUTRAL_MIN - SCORE_BULLET_CENTER` = -0.05; `MAX - CENTER` = +0.05, matching the working endgame_score bullet's offsets).

Notes (informational, not gaps):
- Phase 83 plan/research/context files were unpushed to origin/main at execution time and merged via commit `0b035e18`. Plans landed on the phase branch via wave merges. Not a verification gap.
- Phase 83 is not yet listed in ROADMAP.md Progress section. Per user note, roadmap entries are user-managed.
- 83-REVIEW.md WR-01/WR-02/IN-01/IN-02/IN-03 are deferred polish items, not blockers.

---

_Verified: 2026-05-11T20:40:00Z_
_Verifier: Claude (gsd-verifier)_
