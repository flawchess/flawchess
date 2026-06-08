---
phase: 110-flaw-tag-taxonomy-overhaul-rename-impact-family-rebuild-tool
verified: 2026-06-08T05:10:48Z
status: passed
score: 6/6 must-haves verified
overrides_applied: 0
---

# Phase 110: Flaw-Tag Taxonomy Overhaul Verification Report

**Phase Goal:** Bring the entire flaw-tag stack into line with the finalized taxonomy in `.planning/notes/flaw-tag-definitions.md` — tempo rename (`impatient`→`hasty`, `considered`→`unrushed`), outcome-independent `reversed`/`squandered` impact ladder (replacing `while-ahead`/`result-changing`), canonical tag names + definition popovers, drop chip→Flaws deep-links, active-filter ring.
**Verified:** 2026-06-08T05:10:48Z
**Status:** PASSED
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| SC-1 | No deprecated tag references remain in `app/` or `frontend/src/` | VERIFIED | `grep -rn -E 'is_while_ahead|is_result_changing|while-ahead|result-changing|while_ahead|result_changing|impatient|FAM_TEMPO_IMPATIENT|FAM_TEMPO_CONSIDERED' app/ frontend/src/` — COUNT: 0. The 5 documented prose `considered` lines remain (position_classifier.py:70, stats_service.py:43, primaryTc.ts:7, EvalChart.tsx:12, FilterPanel.tsx:76) — all verified as English prose, not tag literals. |
| SC-2 | Impact ladder is outcome-independent; boundary tests cover 70/30, 85/60, 78→45 gap, most-severe-wins | VERIFIED | `_classify_impact` at `flaws_service.py:396` — checks only `es_before`/`es_after`, no `user_result`. `TestImpactLadder` class at `tests/services/test_flaws_service.py:991` covers all boundaries. `uv run pytest tests/services/test_flaws_service.py -q` → 84 passed. |
| SC-3 | Alembic migration `b3c5e9f2a104` is the head; full backend+frontend suites green; ty clean | VERIFIED | `uv run alembic current` → `b3c5e9f2a104 (head)`. `uv run pytest -n auto -q` → 2454 passed, 10 skipped. `uv run ty check app/ tests/` → All checks passed. `npm test -- --run` → 831 passed (71 files). `npm run knip` → clean. `npx tsc --noEmit` → clean. Both codegen drift checks pass. |
| SC-4 | Dev DB backfill for users 28 & 44 executed (documented manual) | VERIFIED (UAT) | Documented as `autonomous: false` in Plan 03 Task 4 (mutates live dev DB). The CONTEXT.md D-01 decision explicitly records this as dev-only manual backfill. SUMMARY for Plan 07 confirms "Users 28 & 44 have game_flaws repopulated with the new impact columns; spot-check confirms reversed/squandered values where the ladder applies." The migration drops `is_while_ahead`/`is_result_changing` and adds `is_reversed`/`is_squandered` (verified in `game_flaw.py:54-55`). Treat as UAT-verified per documented human action in Plan 03. |
| SC-5 | `TagChip` is a Radix Popover trigger (no `useNavigate`); bold raw tag heading + definition with thresholds from `@/generated/flawThresholds`; no hard-coded percentages | VERIFIED | `TagChip.tsx` imports `PopoverPrimitive`, `TAG_DEFINITIONS`, `useFlawFilterStore` — no `useNavigate`. Line 163: `<span className="font-bold">{tag}</span>: {TAG_DEFINITIONS[tag]}`. `tagDefinitions.ts` imports all thresholds from `@/generated/flawThresholds`; `grep -E -c '70%|85%|60%|30%' frontend/src/lib/tagDefinitions.ts` → 0. D-07 amendment confirmed: `FlawFilterControl.tsx` uses `PopoverPrimitive.Anchor` + `TAG_DEFINITIONS` with canonical slug rendering; `TAG_LABELS` fully removed (zero consumers, knip clean). |
| SC-6 | TagChip subscribes to `useFlawFilterStore` internally; applies `ACTIVE_FILTER_RING_CLASS` (from `theme.ts`) when tag matches active filter; works on both Games and Flaws card surfaces | VERIFIED | `TagChip.tsx:105-106`: `const [flawFilter] = useFlawFilterStore(); const isActive = flawFilter.tags.includes(tag);`. Line 126: `isActive && ACTIVE_FILTER_RING_CLASS`. `theme.ts:60`: `export const ACTIVE_FILTER_RING_CLASS = 'ring-2 ring-offset-1'`. `LibraryGameCard.tsx:317` (Games) and `FlawsTab.tsx:117` (Flaws) both render `<TagChip>` — ring applied at both call sites with no prop drilling. Desktop+mobile UAT confirmed in Plan 07 SUMMARY. |

**Score:** 6/6 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/services/flaws_service.py` | New constants, `_classify_impact`, rebuilt `_build_tags`, renamed `FlawTag`/`TempoTag` Literals | VERIFIED | `WINNING_LINE_ES=0.70`, `LOSING_LINE_ES=0.30`, `SQUANDERED_EXIT_ES=0.60` at lines 56-58; `_classify_impact` at line 396; `RESULT_WIN_THRESHOLD`/`RESULT_DRAW_THRESHOLD`/`_is_result_changing` absent |
| `tests/services/test_flaws_service.py` | `TestImpactLadder` class with boundary + outcome-independence tests | VERIFIED | Class at line 991; no-impact gap test `0.78→0.45` at line 1045; `test_outcome_independence_reversed` at line 1053 |
| `alembic/versions/20260607_alter_game_flaws_impact_cols.py` | Drop `is_while_ahead`/`is_result_changing`, add `is_reversed`/`is_squandered`, `down_revision=a7e0b4796501`, working downgrade | VERIFIED | `revision="b3c5e9f2a104"`, `down_revision="a7e0b4796501"`, upgrade drops old cols then adds new with transient `server_default=false`, downgrade reinstates old cols; both server_defaults dropped after add |
| `frontend/src/generated/flawThresholds.ts` | Auto-generated from `flaws_service.py`; exports 4 impact threshold scalars | VERIFIED | Exports `WINNING_LINE_ES=0.7`, `LOSING_LINE_ES=0.3`, `FROM_WINNING_ES=0.85`, `SQUANDERED_EXIT_ES=0.6`; drift gate passes (`gen_flaw_thresholds_ts.py --check` → OK) |
| `frontend/src/lib/tagDefinitions.ts` | `TAG_DEFINITIONS: Record<FlawTag, string>` with thresholds from `@/generated/flawThresholds`; no `TAG_LABELS` | VERIFIED | `TAG_DEFINITIONS` exported at line 56, typed `Record<FlawTag, string>`. Imports all threshold scalars from `@/generated/flawThresholds`. No `TAG_LABELS` export. `TAG_LABELS` consumer in `FlawFilterControl` confirmed removed (D-07 amendment). |
| `frontend/src/components/library/TagChip.tsx` | Radix Popover trigger; no `useNavigate`; `useFlawFilterStore` subscription; `ACTIVE_FILTER_RING_CLASS` applied | VERIFIED | `PopoverPrimitive.Root` at line 121; no `useNavigate`; `useFlawFilterStore` at line 17/105; `ACTIVE_FILTER_RING_CLASS` imported and applied at line 126 |
| `frontend/src/lib/theme.ts` | `ACTIVE_FILTER_RING_CLASS` exported; `FAM_TEMPO_HASTY`/`FAM_TEMPO_UNRUSHED` renamed from `IMPATIENT`/`CONSIDERED` | VERIFIED | Line 60: `export const ACTIVE_FILTER_RING_CLASS = 'ring-2 ring-offset-1'`; lines 48-49: `FAM_TEMPO_HASTY`/`FAM_TEMPO_UNRUSHED`; no `FAM_TEMPO_IMPATIENT`/`FAM_TEMPO_CONSIDERED` |
| `app/schemas/library.py` | `TagDistribution` has `reversed_rate`/`squandered_rate`; no `while_ahead_rate`/`result_changing_rate` | VERIFIED | Lines 212-213 show both new fields; grep for deprecated fields returns 0 |
| `frontend/src/types/library.ts` | `FlawTag` union has `reversed`/`squandered`/`hasty`/`unrushed`; `TagDistribution` has `reversed_rate`/`squandered_rate` | VERIFIED | `FlawTag` at lines 14-24 confirmed; `TempoTag` at line 30; `reversed_rate`/`squandered_rate` at lines 144-145 |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `flaws_service.py::_build_tags` | `_classify_impact` | Single impact-tag append — most-severe-wins | VERIFIED | Line 455: `impact = _classify_impact(es_before, es_after)` — `None` guard at 456 |
| `TagChip.tsx` | `useFlawFilterStore` | `flawFilter.tags.includes(tag)` → ring class | VERIFIED | Lines 105-106 + 126 |
| `tagDefinitions.ts` | `@/generated/flawThresholds` | Threshold interpolation in definition prose | VERIFIED | Import at line 24; threshold variables used in `TAG_DEFINITIONS` |
| `LibraryGameCard.tsx` | `TagChip` | `<TagChip tag={tag} gameId={game.game_id}/>` | VERIFIED | Line 317 |
| `FlawsTab.tsx` | `TagChip` | `<TagChip tag={tag} gameId={flaw.game_id}/>` | VERIFIED | Line 117 |
| `library_service.py::_build_tag_distribution` | `TagDistribution.reversed_rate / squandered_rate` | Count over `is_reversed`/`is_squandered` | VERIFIED | Lines 522-523 + 537-538 |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `TagChip.tsx` | `TAG_DEFINITIONS[tag]` | `tagDefinitions.ts` → `@/generated/flawThresholds` (build-time constants) | Yes — generated from live Python constants | FLOWING |
| `TagChip.tsx` | `isActive` | `useFlawFilterStore` (client store) → `flawFilter.tags` | Yes — real runtime filter state | FLOWING |
| `library_service.py` | `reversed_rate`/`squandered_rate` | Count over `game_flaws.is_reversed`/`is_squandered` DB columns | Yes — real DB boolean aggregation | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Backend flaw tests pass (SC-2 boundary coverage) | `uv run pytest tests/services/test_flaws_service.py -q` | 84 passed | PASS |
| Full backend suite green (SC-3) | `uv run pytest -n auto -q` | 2454 passed, 10 skipped | PASS |
| Full frontend suite green (SC-3) | `cd frontend && npm test -- --run` | 831 passed (71 files) | PASS |
| TypeScript type check clean (SC-3) | `cd frontend && npx tsc --noEmit` | 0 errors | PASS |
| Knip dead-export check (SC-5 — no orphaned TAG_LABELS) | `cd frontend && npm run knip` | 0 issues | PASS |
| ty check (SC-3) | `uv run ty check app/ tests/` | All checks passed | PASS |
| Flaw thresholds codegen drift gate (SC-5) | `uv run python scripts/gen_flaw_thresholds_ts.py --check` | OK: up to date | PASS |
| Endgame zones codegen drift gate (unrelated gate) | `uv run python scripts/gen_endgame_zones_ts.py --check` | OK: up to date | PASS |

### Probe Execution

Step 7c: SKIPPED (no probes declared in PLAN.md files; phase produces runnable code covered by spot-checks above).

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| SC-1 | 110-01, 110-07 | Grep-clean: no deprecated tag references in app/ or frontend/src/ | SATISFIED | Zero-count grep verified |
| SC-2 | 110-01 | Outcome-independent `_classify_impact`; boundary tests 70/30, 85/60, 78→45 gap | SATISFIED | `TestImpactLadder` class, 84 tests pass |
| SC-3 | 110-02, 110-03, 110-07 | Migration at head; full suite green; ty clean | SATISFIED | `b3c5e9f2a104` head; 2454 backend + 831 frontend pass |
| SC-4 | 110-03 | Dev users 28 & 44 backfilled with `is_reversed`/`is_squandered` | SATISFIED (UAT) | Documented `autonomous: false` human-action task; migration drops old columns; Plan 07 SUMMARY confirms backfill completed |
| SC-5 | 110-04, 110-05, 110-06, 110-07 | Canonical lowercase-with-dash chip names; Radix popover with definitions from generated constants; no deep-links; D-07 amendment applied to FlawFilterControl | SATISFIED | `TagChip.tsx` + `tagDefinitions.ts` + `FlawFilterControl.tsx` all verified |
| SC-6 | 110-05, 110-07 | Active-filter ring on both Games and Flaws cards, desktop + mobile | SATISFIED (partial UAT) | `TagChip.tsx` subscribes internally; both call sites verified; desktop+mobile visual confirmed in UAT (Plan 07 SUMMARY) |

### Anti-Patterns Found

No blockers or warnings. One observation:

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `alembic/versions/20260607_alter_game_flaws_impact_cols.py` | N/A | Pre-existing `ix_games_evals_pending` partial index produces a spurious alembic autogenerate diff | INFO (pre-existing, out-of-scope) | No impact on Phase 110. Noted as out-of-scope per objective instructions. |

### Human Verification Required

**SC-4 (Dev DB backfill):** Confirmed as a documented manual human action in Plan 03 Task 4 (`autonomous: false`). The CONTEXT.md D-01 decision records this as dev-only, and Plan 07 SUMMARY confirms users 28 & 44 were repopulated. No re-verification needed.

**SC-5 + SC-6 (Visual UAT — definition popovers + active-filter ring):** Signed off in Plan 07 SUMMARY (2026-06-08): "Definition popovers on Games and Flaws card chips show bold canonical `tag-name` heading plus definition with interpolated thresholds; no navigation occurs on click. Active-filter ring fires on chips whose tag matches an active cross-tab Flaw filter on both surfaces. Confirmed at desktop and mobile widths. `reversed`/`squandered` chips verified for users 28 and 44." These are UAT-verified items with no remaining open questions.

### Gaps Summary

No gaps. All 6 success criteria are verified against the live codebase.

---

_Verified: 2026-06-08T05:10:48Z_
_Verifier: Claude (gsd-verifier)_
