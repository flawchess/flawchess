---
phase: 129-tactic-filter-ui
reviewed: 2026-06-20T00:00:00Z
depth: standard
files_reviewed: 14
files_reviewed_list:
  - app/repositories/library_repository.py
  - app/repositories/query_utils.py
  - app/routers/library.py
  - app/schemas/library.py
  - app/services/library_service.py
  - frontend/src/lib/tacticComparisonMeta.ts
  - frontend/src/lib/tacticMotifDefinitions.ts
  - frontend/src/lib/theme.ts
  - frontend/src/types/library.ts
  - frontend/src/components/filters/__tests__/FlawFilterControl.test.tsx
  - frontend/src/components/library/__tests__/TacticComparisonGrid.test.tsx
  - frontend/src/components/library/__tests__/TacticMotifChip.test.tsx
  - tests/services/test_tactic_comparison_service.py
  - tests/test_flaw_predicate.py
findings:
  critical: 0
  warning: 3
  info: 5
  total: 8
status: issues_found
---

# Phase 129: Code Review Report

**Reviewed:** 2026-06-20
**Depth:** standard
**Files Reviewed:** 14
**Status:** issues_found

## Summary

Reviewed the gap-closure work (plans 129-04 backend taxonomy redesign + 129-05 frontend) that expands the tactic-family taxonomy from 6 families to 10 (`fork | skewer | pin | x_ray | double_check | discovered_check | discovered_attack | trapped_piece | hanging | mate`) and drops the old `combinations` family.

The core cross-stack contract is **correct and verified**: the 10 backend `FAMILY_TO_MOTIF_INTS` keys match the frontend `TacticFamily` union string-for-string, the per-family motif-int → motif-string mappings reconcile exactly against `_INT_TO_MOTIF` in `tactic_detector.py`, and the `theme.ts` `TAC_*` tokens cover all 10 families. No orphaned `pin_skewer` / `discovery` / `combinations` keys remain in executable code (only in explanatory comments documenting the removal). Dropped combinations ints (9, 10, 11, 13, 14, 15, 16, 17) correctly map to no family, and unknown/dropped family keys are silently no-op'd via `.get(fam, [])`, so stale URL params are inert.

No BLOCKER-class defects found. The findings below are correctness/maintainability concerns: stale docstrings that misstate family counts (now actively misleading after the 6→10 change), a confidence-gate asymmetry between the Games-tab and Flaws-tab tactic filters that can surface games with no displayable chip, an orientation-basis mismatch in the comparison-grid family narrowing, and several dead/duplicated artifacts left behind by the redesign.

## Warnings

### WR-01: `fetch_tactic_comparison` docstring still claims "6 tactic families / 12 COUNT columns" after the 6→10 expansion

**File:** `app/repositories/library_repository.py:1599`, `app/repositories/library_repository.py:1607`
**Issue:** The function docstring is the primary place this phase needed to update, and it was missed. The summary line reads "Per-game player/opp counts for all **6 tactic families**" and the Returns clause reads "one row per game_id with **12 COUNT columns (6 families × player/opp)**", while the body two lines below correctly comments "Build 20 COUNT columns (10 families × player/opp)" and the loop iterates `FAMILY_TO_MOTIF_INTS.items()` (now 10). A reader trusting the docstring will mis-size the row shape and may believe families were dropped from this query. This is exactly the kind of stale cross-module fact the taxonomy redesign was supposed to sweep.
**Fix:**
```python
"""Per-game player/opp counts for all 10 tactic families over the analyzed+filtered set.
...
Returns one row per game_id with 20 COUNT columns (10 families × player/opp).
"""
```
Also fix the same "6 family rows" wording in the `get_tactic_comparison` service comment at `app/services/library_service.py:1420` ("Each fetch returns 6 family rows for one orientation" → 10).

### WR-02: Games-tab tactic-family filter omits the confidence gate, so it can return games whose only matching tactic never renders a chip

**File:** `app/repositories/query_utils.py:236-255` (vs `app/repositories/library_repository.py:330-337`)
**Issue:** `build_flaw_filter_clauses` (Flaws tab) ANDs `conf_col >= _TACTIC_CHIP_CONFIDENCE_MIN` into each tactic branch, but `apply_game_filters` (Games tab, the `tactic_families` EXISTS path) deliberately omits it ("no confidence gate — Pitfall 3"). The result is an observable inconsistency: filtering the Games tab by e.g. `fork` can match a game whose only fork motif has confidence below 70, yet that game's card will show **no fork chip** (chip display is gated at 70 in `_build_card` / `query_flaws`). The user sees a game in a fork-filtered list with no visible fork — looks like a bug. The two filter surfaces should agree on what "has a tactic in family X" means, which was the SEED-038 cross-tab-unification premise. The comment asserts this is intentional ("Pitfall 3 preserved") but does not justify why the Games tab should match below-threshold events the user can never see. Flagging for an explicit decision rather than silent divergence; if intentional, the rationale belongs in the docstring, not just a pitfall reference.
**Fix:** Either gate the Games-tab EXISTS on confidence to match chip/Flaws-tab semantics:
```python
branch = (
    motif_col.in_(motif_ints)
    & (_conf_col >= _TACTIC_CHIP_CONFIDENCE_MIN)
    & _depth_ok(depth_col, motif_col, max_tactic_depth)
)
```
(`_conf_col` is already unpacked and discarded in the loop at line 239), or document the deliberate asymmetry with a one-line rationale at the call site. Note SEED-060 already tracks the related `player_only_gate` omission on this same EXISTS — this confidence-gate gap is adjacent and worth resolving together.

### WR-03: `get_tactic_comparison` per-orientation fetch passes `tactic_families` but neither `orientation` nor `max_tactic_depth`, so family narrowing and the displayed bullets can rest on different game sets

**File:** `app/services/library_service.py:1419-1434`
**Issue:** `_filter_kwargs` carries `tactic_families` into both the gate `count_filtered_and_analyzed` and both `fetch_tactic_comparison` calls. Inside `fetch_tactic_comparison`, `tactic_families` flows into `_filtered_games_base` → `apply_game_filters` with its **default** `orientation="allowed"` and `max_tactic_depth=None`. So when a user has narrowed to e.g. `tactic_families=["fork"]`, the comparison-grid *game set* is filtered on the **allowed** column only (the apply_game_filters default), while the per-game family counts are computed for **both** missed and allowed orientations (the grid shows both per D-09). The grid's `analyzed_n` denominator and the bullet population then key off mismatched orientation semantics. Subtle because this endpoint has no orientation query param, but the inherited family narrowing still hard-codes one orientation. At worst the "X of 20" gate count and the bullet rates rest on different game populations.
**Fix:** Confirm intended semantics for tactic-comparison family narrowing. If the grid should narrow on "either" (to match its dual-orientation display), thread `orientation="either"` explicitly into the `tactic_families` path for this endpoint rather than inheriting the `"allowed"` default. Add a test asserting the gate `analyzed_n` and bullet population share an orientation basis when `tactic_families` is set.

## Info

### IN-01: Dropped-combinations motif definitions are now dead data in `tacticMotifDefinitions.ts`

**File:** `frontend/src/lib/tacticMotifDefinitions.ts:29-36`
**Issue:** The 8 combinations motif definitions (`sacrifice`, `deflection`, `attraction`, `intermezzo`, `interference`, `self-interference`, `clearance`, `capturing-defender`) remain in `TACTIC_MOTIF_DEFINITIONS`. They are reachable only via `TacticMotifChip`/`TagChip`, both of which now look up `TACTIC_FAMILY_FOR_MOTIF[motif]` first and render `null` for any motif with no family — so these entries can never be displayed. They are not dead *exports* (the whole record is still imported), so knip won't catch them, but they are dead *entries* that mislead future readers into thinking those motifs surface somewhere.
**Fix:** Delete the 8 dropped-family entries, or add a comment marking them intentionally retained for the `TACTIC_MOTIF_DEFINITIONS[motif] ?? motif` raw-string fallback (the only consumer that would touch them). Prefer deletion for clarity.

### IN-02: `tacticMotifDefinitions.ts` header comment claims "24 TacticMotif Literal strings"; the enum now has 29

**File:** `frontend/src/lib/tacticMotifDefinitions.ts:4`
**Issue:** Header says "Keys match the **24** TacticMotif Literal strings in `app/services/tactic_detector.py` exactly." The backend `TacticMotif` Literal now has 29 members (25=`discovered-check`, 26=`trapped-piece`, 27=`en-passant`, 28=`promotion`, 29=`under-promotion`). The record correctly includes `discovered-check`/`trapped-piece` but the count is stale, and the 3 move-type motifs are absent (correctly out of chip scope, but the comment doesn't say so).
**Fix:** Update the count to 29 and note the 3 move-type motifs are intentionally excluded (chip surfacing out of scope per D-09).

### IN-03: `TacticComparisonResponse` JSDoc in `types/library.ts` still describes the pre-129 "up to 6 family rows" contract

**File:** `frontend/src/types/library.ts:325-332`
**Issue:** The JSDoc says "bullets: ordered by rank ..., **up to 6 family rows**" and references `FLAW_COMPARISON_GATE` for `analyzed_gate`. After 129 the response carries up to 20 bullets (10 families × 2 orientations, top-6 families first then overflow), and the gate mirrors `TACTIC_COMPARISON_GATE`. The interface fields are correct; only the prose is stale.
**Fix:** Replace with the Phase 129 contract: "up to 20 entries (10 families × missed/allowed), top-6 families first then overflow; analyzed_gate mirrors TACTIC_COMPARISON_GATE."

### IN-04: Backend `TacticComparisonResponse` docstrings say "up to 12 ... (6 families × 2)"; actual cap is 20

**File:** `app/schemas/library.py:392-393`, also `app/routers/library.py:237-238`
**Issue:** Two docstrings state "up to 12 orientation-tagged bullets (6 families x 2 orientations)". The service emits bullets for all 10 families (top-6 + 4 overflow), each with up to 2 orientations, so the real cap is 20 — which the test suite (`test_full_response_bullets`) correctly asserts (`<= 20`). The "12" / "6 families x 2" figure is the pre-overflow understanding and contradicts the shipped behavior and the test.
**Fix:** Update both docstrings to "up to 20 orientation-tagged bullets (10 families × 2 orientations); top-6 families first, then overflow."

### IN-05: `_compute_tactic_bullets` sorts internally, but the caller fully re-orders by Missed `you_rate`, and the helper's docstring contradicts its own `bullets.sort` call

**File:** `app/services/library_service.py:1332-1344` (helper) vs `1447-1473` (caller re-rank)
**Issue:** `_compute_tactic_bullets` ends with `bullets.sort(key=_sort_key)` (sig-first, |delta|, volume), but `get_tactic_comparison` rebuilds emission order entirely from `_missed_rank_key` (Missed `you_rate` desc, tie-broken by position-in-`missed_bullets`). The helper's sort survives only as the tie-break ordinal for families with equal `you_rate`. Not a bug — output is deterministic — but the double-sort obscures intent, and the helper docstring literally says "Return all families **unsorted**" on the line above a `bullets.sort(...)` call.
**Fix:** Either drop the helper's `bullets.sort` (the caller's rank is authoritative) and fix the contradictory "unsorted" docstring, or document that the helper sort exists solely to seed the `_missed_rank_key` position tie-break. Prefer making a single ranking authority explicit.

---

_Reviewed: 2026-06-20_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
