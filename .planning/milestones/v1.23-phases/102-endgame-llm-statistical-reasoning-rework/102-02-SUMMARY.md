---
phase: 102-endgame-llm-statistical-reasoning-rework-v1-23
plan: 02
subsystem: api
tags: [llm, insights, endgame, prompt, percentile, time-pressure, vocabulary-audit]

# Dependency graph
requires:
  - phase: 102-01
    provides: "pctl= annotation on summary lines, time_pressure_cards on EndgameTabFindings, real net_timeout_rate scalar, _format_time_pressure_score_gap_chart_block"
provides:
  - "System prompt teaches pctl= with zone-as-sole-gate rule, cohort framing, granularity rule"
  - "System prompt teaches time_pressure_score_gap_by_time chart (5 quintiles per TC)"
  - "System prompt declares net_timeout_rate as real emitted scalar (no longer stub)"
  - "Overview cap relaxed to ≤500 words / ≤5 paragraphs when ≥3 distinct narratable signals"
  - "Vocabulary audit corrections aligned to concepts accordion + five tooltip popover bodies"
  - "_PROMPT_VERSION bumped endgame_v35 → endgame_v36 (single cache invalidation on deploy)"
affects: [102-UAT, insights_llm_cache]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Prompt versioning: prepend-at-front changelog inside _PROMPT_VERSION inline comment"
    - "Zone-as-sole-gate invariant documented in prompt (pctl= never reopens a closed gate)"

key-files:
  created: []
  modified:
    - app/prompts/endgame_insights.md
    - app/services/insights_llm.py
    - tests/services/test_insights_llm.py

key-decisions:
  - "Vocabulary audit: entry_expected_score UI label corrected to 'Entry Eval Score' (was 'Achievable Score') — EndgameOverallEntryCard.tsx confirms the rendered label; AchievableScorePopover.tsx is not the primary reference"
  - "Vocabulary audit: achievable_score_gap page-level UI label corrected to 'Eval Score Gap' (was 'Achievable Score Gap') — EndgameOverallPerformanceSection.tsx confirms"
  - "Vocabulary audit: score_gap vocabulary table entry corrected to 'Endgame Score Gap' (was 'Endgame vs Non-Endgame Score Gap') — EndgameOverallPerformanceSection.tsx line 220 confirms"
  - "Vocabulary audit: entry_eval_pawns UI label corrected to 'Entry Eval' (was 'Endgame Entry Eval') — EndgameOverallEntryCard.tsx line 86 confirms"

requirements-completed: [LLM-02, LLM-03, LLM-04, LLM-05, LLM-06]

# Metrics
duration: ~20min
completed: 2026-06-01
---

# Phase 102 Plan 02: Endgame LLM Prompt Statistical-Reasoning Teaching Summary

**System prompt updated with percentile narration rules, new time-pressure chart teaching, stale reference purge, relaxed overview cap, and vocabulary corrections aligned to live UI labels; _PROMPT_VERSION bumped to endgame_v36 for a single clean cache invalidation**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-06-01T17:55:00Z
- **Completed:** 2026-06-01T18:12:44Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- Added "Percentile annotations (pctl=)" section: gate rule (D-04 — zone is sole emission gate; extreme pctl in typical zone does NOT open gate), cohort framing rule (D-05 — "vs ~{anchor}-rated {tc} players", never "globally"), granularity rule (D-06 — per-TC TPCTL direct; page-level game-count-weighted), worked example, no-parallel-significance guard
- Replaced all `time_pressure_vs_performance` / `[low-time-gap]` references (9 occurrences → 0) with `time_pressure_score_gap_by_time` teaching: 5 quintiles per TC (Q0=max pressure, Q4=min pressure), score_delta + typical_band columns, low-clock divergence as central story
- Declared `net_timeout_rate` as a real emitted scalar (no longer always-empty stub) in glossary
- Updated cross-section link (endgame_start_vs_end) and recommendations rule to use new chart
- Relaxed overview cap to ≤500 words / ≤5 paragraphs when ≥3 distinct narratable signals exist; both occurrences (line 9 output contract + Overview rule section) updated consistently; all four guards preserved: silence-is-not-valid, no-fabrication, within-noise, flat-trend
- Vocabulary audit: corrected 4 label mismatches against the Endgame Statistics Concepts accordion (Endgames.tsx lines 382-580) and five tooltip popover bodies
- Bumped `_PROMPT_VERSION` from `endgame_v35` to `endgame_v36` with prepended changelog entry; prior v35 history intact; updated 5 test assertions + 2 docstrings

## Task Commits

1. **Task 1+2: Prompt — percentile teaching, time-pressure chart, stale ref purge, overview cap, vocab audit** - `72cebe4d`
2. **Task 3: Version bump endgame_v35 → endgame_v36 + test updates** - `963c425a`

## Files Created/Modified

- `app/prompts/endgame_insights.md` — 48 insertions, 25 deletions: new "Percentile annotations" section, updated time-pressure glossary, new chart block teaching, section-layout table fix, overview cap relaxation, vocabulary corrections
- `app/services/insights_llm.py` — _PROMPT_VERSION bumped with prepended v36 changelog
- `tests/services/test_insights_llm.py` — 5 assertions updated from endgame_v35 → endgame_v36; worked-example assertion updated for "Entry Eval Score" rename; 2 docstrings updated

## D-10 Vocabulary Audit Record

### Sources Checked

1. **Endgame Statistics Concepts accordion** (`frontend/src/pages/Endgames.tsx` lines 382-580) — authoritative label/definition source
2. **MetricStatPopover** (`frontend/src/components/popovers/MetricStatPopover.tsx`) — shell around MetricStatTooltip for 6 Overall Performance tooltips
3. **MetricStatTooltip** (`frontend/src/components/popovers/MetricStatTooltip.tsx`) — tooltip body with sign conventions (score baseline=0.5 unsigned; gap baseline=0 signed; pawns signed)
4. **WdlConfidenceTooltip** (`frontend/src/components/insights/WdlConfidenceTooltip.tsx`) — Wilson score test vs 50% body; "strength/weakness/difference" verdict vocabulary
5. **EvalConfidenceTooltip** (`frontend/src/components/insights/EvalConfidenceTooltip.tsx`) — Wald z-test body; "advantage/disadvantage/deviation" verdict vocabulary; `evalContext='endgame-entry'` path uses "average Stockfish eval at the position where the endgame begins"
6. **AchievableScorePopover** (`frontend/src/components/popovers/AchievableScorePopover.tsx`) — "Achievable Score" label in this component's aria-label; Wilson test vs 50%; but the card renders "Entry Eval Score" as the visible label (resolved by checking EndgameOverallEntryCard.tsx)
7. **PercentileChip** (`frontend/src/components/charts/PercentileChip.tsx`) — 3-bullet popover: direct percentile statement with "vs ~{anchor}-rated players in {tc}" framing (per-TC) or "similarly-rated players, aggregated across the time controls you play" (aggregated); recent-games basis; filter independence; UI filters do not affect percentile

### Corrections Applied

| Term | Before (prompt) | After (prompt) | Source confirming live label |
|------|-----------------|----------------|------------------------------|
| `entry_expected_score` UI label | "Achievable Score" | "Entry Eval Score" | `EndgameOverallEntryCard.tsx` line 145: `Entry Eval Score:` / line 155: `name="Entry Eval Score"` |
| `achievable_score_gap` UI label | "Achievable Score Gap" | "Eval Score Gap" | `EndgameOverallPerformanceSection.tsx` line 193: `name="Eval Score Gap"` |
| `score_gap` vocabulary table entry | "Endgame vs Non-Endgame Score Gap" | "Endgame Score Gap" | `EndgameOverallPerformanceSection.tsx` line 220: `label="Endgame Score Gap:"` |
| `entry_eval_pawns` UI label | "Endgame Entry Eval" | "Entry Eval" | `EndgameOverallEntryCard.tsx` line 86: `Entry Eval:` |
| Narration example | `"Achievable 49%, you scored 52%"` | `"Entry Eval Score 49%, you scored 52%"` | align with corrected label |
| "Achievable Score Gap" family reference | Glossary and disambiguation | "Eval Score Gap" | Updated in type_achievable_score_gap section |

### No Issues Found

- **Endgame Types** labels: prompt uses "Rook, Minor Piece, Pawn, Queen, Mixed" — matches accordion exactly
- **Endgame Class vs Endgame Type**: `grep -c "Endgame Class" app/prompts/endgame_insights.md` = 0 (only internal `endgame_class=` payload identifiers remain)
- **Conversion / Parity / Recovery** labels: prompt uses "(Win)", "(Score)", "(Save)" suffixes — consistent with UI
- **Endgame ELO / Non-Endgame ELO**: prompt vocabulary matches accordion
- **Score Gap** short form for per-type metric: correct per existing dual-label rule
- **MetricStatTooltip sign conventions**: percent gap metrics (baseline=0) → signed (+/-); score-vs-50% → unsigned; pawns → signed. Prompt narration conventions align.
- **WdlConfidenceTooltip**: uses "strength/weakness" vocabulary; prompt uses same — consistent
- **EvalConfidenceTooltip**: uses "advantage/disadvantage/deviation" vocabulary for eval-based metrics; prompt uses same for `entry_eval_pawns` — consistent
- **PercentileChip cohort framing**: chip bullet 1 says "vs ~{anchor}-rated players in {tc}" for per-TC chips; prompt D-05 framing rule matches this exactly

## Deviations from Plan

None — plan executed exactly as written. All acceptance criteria pass:
- `grep -c "time_pressure_vs_performance\|low-time-gap" app/prompts/endgame_insights.md` == 0
- `grep -c "~300 words" app/prompts/endgame_insights.md` == 0
- `grep -n "time_pressure_score_gap_by_time" app/prompts/endgame_insights.md` returns 8 hits
- `grep -ni "pctl|percentile" app/prompts/endgame_insights.md` shows percentile teaching block
- `grep -i "does NOT open the gate" app/prompts/endgame_insights.md` returns a hit
- `grep -niE "up to ~?500 words|up to 5 (short )?paragraphs" app/prompts/endgame_insights.md` returns 2 hits
- `grep -ni "≥3|3 distinct" app/prompts/endgame_insights.md` shows signal gate
- `grep -c "Endgame Class" app/prompts/endgame_insights.md` == 0
- `grep -c "endgame_v36" app/services/insights_llm.py` == 1 (assignment)
- `grep -n "v36 (.*Phase 102" app/services/insights_llm.py` returns a hit
- `uv run pytest tests/services/test_insights_llm.py -x -q`: 102 passed
- `uv run ty check app/ tests/`: All checks passed
- `uv run ruff check app/ tests/`: All checks passed

## Known Stubs

None — all plan objectives fully implemented.

## Threat Flags

None — no new network endpoints, auth paths, schema changes, or untrusted input paths. All changes are to static server-side prompt text and a server-controlled version constant (T-102-04/T-102-05/T-102-06 in the plan's threat model, disposition: accept).

## Self-Check: PASSED

- `app/prompts/endgame_insights.md`: FOUND
- `app/services/insights_llm.py`: FOUND
- `tests/services/test_insights_llm.py`: FOUND
- Commits `72cebe4d`, `963c425a`: FOUND in git log
- `uv run pytest tests/services/test_insights_llm.py -x -q`: 102 passed
- `uv run ty check app/ tests/`: All checks passed
- `uv run ruff check app/ tests/`: All checks passed

---
*Phase: 102-endgame-llm-statistical-reasoning-rework-v1-23*
*Completed: 2026-06-01*
