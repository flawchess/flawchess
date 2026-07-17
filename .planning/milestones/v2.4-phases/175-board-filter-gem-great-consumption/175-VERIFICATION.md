---
phase: 175-board-filter-gem-great-consumption
verified: 2026-07-17T01:39:12Z
status: gaps_found
score: 3/4 roadmap truths fully verified (1 partial — functional demotion complete, administrative seed-closure outstanding)
behavior_unverified: 0
overrides_applied: 0
gaps:
  - truth: "useGemSweep.ts is retired (or demoted to a documented free-play-only fallback for positions with no stored analysis); SEED-107 closes as superseded."
    status: partial
    reason: "The functional half is fully done and verified (useGemSweep.ts carries a demotion docstring, both live gem mechanisms gate on !gameHasStoredBestMoveData/!currentNodeCoveredByStoredData, tests pass). The administrative half — 'SEED-107 closes as superseded' — was NOT done: .planning/seeds/SEED-107-gem-sweep-starved-by-live-engines.md still has status: dormant and still lives in .planning/seeds/ (never git mv'd to .planning/seeds/closed/), even though 175-05-SUMMARY.md's frontmatter and body both assert 'SEED-107 closes as superseded' as an accomplished fact. Per CLAUDE.md's own seed-lifecycle convention ('Move to closed/ when done') and the roadmap's own Success Criterion 2 wording, this is a real, observable discrepancy between the SUMMARY narrative and the repo state."
    artifacts:
      - path: ".planning/seeds/SEED-107-gem-sweep-starved-by-live-engines.md"
        issue: "status: dormant, still in the active seeds/ folder; not closed despite SUMMARY claiming closure"
    missing:
      - "Update SEED-107's frontmatter status to closed/superseded and git mv it to .planning/seeds/closed/ (SEED-107 already carried superseded_by: SEED-108 in its frontmatter from planting time, so this is a pure housekeeping step, not new analysis)."
---

# Phase 175: Board & Filter — Gem/Great Consumption Verification Report

**Phase Goal:** The analysis board and the Library games filter read gem/great data from the stored backend rows instead of recomputing it client-side, so markers appear instantly regardless of device or live-engine load.
**Requirements:** BOARD-01, BOARD-02, FILT-01
**Verified:** 2026-07-17T01:39:12Z
**Status:** gaps_found (1 minor, low-effort administrative gap; all functional/behavioral deliverables verified)
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (from ROADMAP.md Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Opening an analyzed game shows gem/great markers sourced from `EvalPoint`'s stored fields, appearing immediately with no sweep delay and no dependency on device power/live-engine load | ✓ VERIFIED | `app/schemas/library.py:51,55` (`EvalPoint.best_move_tier`/`maia_prob`); `app/services/library_service.py` `_build_eval_series` classifies via `classify_best_move` (never infers from row presence — Pitfall 3, proven by a documented mutation self-check in 175-02-SUMMARY.md); `frontend/src/pages/Analysis.tsx:704-728,1810-1839` (`storedTierByPly`, `resolveMarkerFor` consults stored tier FIRST for any mainline ply); behavioral test `Analysis.test.tsx:1138-1186` (stored-gem/stored-great renders with **no** live grading/Maia call asserted); human-verify checkpoint (Task 3, 175-05-PLAN.md) **approved by the user 2026-07-17** confirming first-paint marker appearance and zero DevTools worker activity on mainline nav. |
| 2 | `useGemSweep.ts` is retired (or demoted to a documented free-play-only fallback for positions with no stored analysis); SEED-107 closes as superseded | ⚠️ PARTIAL | **Demotion (functional half): VERIFIED.** `frontend/src/hooks/useGemSweep.ts:1-18` carries a "DEMOTED to a fallback-only mechanism" docstring; `Analysis.tsx:1693-1697` (`needParentGemGrade` gains `!currentNodeCoveredByStoredData`), `Analysis.tsx:1779` (`useGemSweep({ enabled: ... && !gameHasStoredBestMoveData })`); behavioral tests `Analysis.test.tsx` "Sweep demotion" describe block + `useGemSweep.test.ts` stored-data-disables-sweep / unanalyzed-still-runs cases, all passing. **SEED-107 closure: FAILED.** See `gaps` above — the seed file was never moved to `closed/` nor had its status updated, despite the SUMMARY claiming closure. |
| 3 | The Library Games filter panel gains "has gem"/"has great" toggles built on the existing flaw/tactic `EXISTS`-based game-filter machinery, and applying a toggle returns only games with a qualifying stored row | ✓ VERIFIED | Backend: `app/repositories/library_repository.py:755` (`best_move_exists_from_table`, correlated EXISTS mirroring `flaw_exists_from_table`); `app/repositories/query_utils.py:118-119,306-308` (`apply_game_filters(has_gem=, has_great=)`); `app/routers/library.py:89-90,132-133` (Query params threaded through). Frontend: `frontend/src/components/filters/FlawFilterControl.tsx:518` (section gated on `onHasGemToggle \|\| onHasGreatToggle` handler presence — the post-verify fix, commit `666c8265`); `GamesTab.tsx:327-350,507-534` (both desktop + mobile render sites pass the handlers); `FlawsTab.tsx` passes neither (confirmed absent by grep — filter correctly does NOT render there). Full round-trip: `useLibrary.ts:85-86` → `api/client.ts` → `GET /library/games?has_gem=&has_great=`. Tests: 11 backend tests (`test_query_utils.py`/`test_library_repository.py`/`test_library_router.py -k "has_gem or has_great"`) + 94 frontend tests (`FlawFilterControl`/`useFlawFilterStore`/`useLibrary`/`client`) all pass — independently re-run during this verification, not just trusted from SUMMARY. |
| 4 | The gem/great filter composes correctly with every other existing game filter (time control, color, rated, opponent type, recency) | ✓ VERIFIED | `tests/test_query_utils.py::test_apply_game_filters_has_gem_composes_with_flaw_and_metadata_filters` compiles the SQL with `time_control`, `rated`, `color`, and `flaw_severity` simultaneously and asserts both `game_best_moves` and `game_flaws` EXISTS clauses are present (not a parallel/exclusive path) — re-run during this verification, passed. `test_library_router.py::test_has_gem_composes_with_color_filter` covers the HTTP boundary. Frontend threads through the single `buildLibraryParams` → `libraryApi.getGames` path with no parallel fetch (grep-confirmed, no second call site). |

**Score:** 3/4 truths fully verified, 1 truth partially verified (functional substance done; a documented administrative claim in the SUMMARY does not match repo state)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/services/best_move_candidates.py::best_move_tier_sql`/`_es_sql` | SQL twin of `classify_best_move`, imports (never re-declares) shared constants | ✓ VERIFIED | Confirmed at lines 179/198; imports `LICHESS_K`, `MATE_CP_EQUIVALENT`, `MISTAKE_DROP`, `GEM_MAIA_MAX_PROB`, `GREAT_MAIA_MAX_PROB` from their existing modules (grep: no re-declaration, no `0.00368208` literal). |
| `app/repositories/library_repository.py::best_move_exists_from_table` | Correlated EXISTS over `game_best_moves`, `player_only_gate` scoped | ✓ VERIFIED | Line 755; cross-user isolation + player-parity tests pass. |
| `app/repositories/library_repository.py::fetch_page_best_moves` | Batched fetch, `dict[int, dict[int, GameBestMove]]`, no N+1 | ✓ VERIFIED | Line 1245. |
| `app/schemas/library.py::EvalPoint.best_move_tier`/`.maia_prob` | Literal union + float, null-safe | ✓ VERIFIED | Lines 51/55. |
| `apply_game_filters(has_gem=, has_great=)` | Single composition point | ✓ VERIFIED | `query_utils.py:118-119`. |
| `GET /library/games?has_gem=&has_great=` | HTTP boundary | ✓ VERIFIED | `routers/library.py:89-90`. |
| `frontend/src/lib/theme.ts::GREAT_ACCENT`/`GREAT_ACCENT_BG` | Theme-only color source | ✓ VERIFIED | Lines 87/90; no hard-coded great color found outside theme.ts (grep). |
| `frontend/src/lib/greatGlyph.ts::GREAT_GLYPH` | Single-source glyph record | ✓ VERIFIED | Full file confirmed. |
| `frontend/src/components/icons/GreatMoveIcon.tsx` | Custom SVG "!" badge | ✓ VERIFIED | Present, imports `GREAT_GLYPH`. |
| `frontend/src/lib/gemMove.ts::classifyGreat`/`GREAT_MAIA_MAX_PROB` | Fallback-only classifier | ✓ VERIFIED | Lines 53/84/96; cross-reference comment to backend present. |
| `frontend/src/types/library.ts::EvalPoint.best_move_tier`/`.maia_prob` | TS mirror of backend schema | ✓ VERIFIED | Lines 124/128. |
| `frontend/src/components/board/boardMarkers.tsx` great branch | Board corner badge | ✓ VERIFIED | `grep -n great` shows the field + render branch. |
| `frontend/src/hooks/useFlawFilterStore.ts::hasGem`/`.hasGreat` | Filter state + `isFlawFilterNonDefault` gate | ✓ VERIFIED | Present in interface, defaults, and the non-default gate. |
| `frontend/src/components/filters/FlawFilterControl.tsx` "Best Moves" section | Two independent toggles, Games-tab-only | ✓ VERIFIED (post-fix) | Gated on handler presence (line 518), not the originally-planned but broken `!showTacticFilter` discriminator — the post-verify fix (commit `666c8265`) is real and independently confirmed by grepping both `GamesTab.tsx` (passes handlers, 2 sites) and `FlawsTab.tsx` (passes neither). |
| `frontend/src/pages/Analysis.tsx` per-node stored-tier resolution | `storedTierByPly` + `resolveMarkerFor` | ✓ VERIFIED | Lines 704-728, 1810-1839; row-absence-authoritative logic confirmed by direct code read, not just SUMMARY narrative. |
| `useGemSweep.enabled`/`needParentGemGrade` fallback-only gates | Both mechanisms gate on "no stored tier" | ✓ VERIFIED | `Analysis.tsx:1697,1779`. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `best_move_tier_sql` | `best_move_exists_from_table` | direct call | ✓ WIRED | Confirmed in repository source. |
| `best_move_exists_from_table` | `apply_game_filters` | `has_gem`/`has_great` composition | ✓ WIRED | `query_utils.py:306-308`. |
| `apply_game_filters` | `GET /library/games` | router → service → repo chain | ✓ WIRED | Grep across all three layers shows unbroken threading. |
| `fetch_page_best_moves` | `_build_eval_series` | `best_moves_by_ply` param | ✓ WIRED | `library_service.py` per-position lookup. |
| Backend `EvalPoint` | TS `EvalPoint` (`types/library.ts`) | field-for-field mirror | ✓ WIRED | Literal unions match exactly. |
| `EvalPoint.best_move_tier` (Plan 02/03) | `Analysis.tsx` mainline resolution | `storedTierByPly` | ✓ WIRED | Confirmed. |
| "node has stored tier?" signal | `useGemSweep.enabled` AND `needParentGemGrade` | `gameHasStoredBestMoveData`/`currentNodeCoveredByStoredData` | ✓ WIRED | Both mechanisms independently confirmed gated on the same underlying signal (Pitfall 2 requirement). |
| `FlawFilterControl` toggle | `useFlawFilterStore.hasGem`/`.hasGreat` | `GamesTab.tsx` handlers | ✓ WIRED | Confirmed at both render sites. |
| `useFlawFilterStore` | `buildLibraryParams` → `libraryApi.getGames` | `useLibrary.ts:85-86` | ✓ WIRED | Confirmed, conditional inclusion mirrors `rated`. |

### Behavioral Spot-Checks (re-run independently during this verification, not trusted from SUMMARY)

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| SQL twin agrees with `classify_best_move` on fixture matrix incl. boundaries | `uv run pytest tests/services/test_best_move_candidates.py -k tier_sql -x` | 11 passed | ✓ PASS |
| `has_gem`/`has_great` filter, union, cross-user isolation, pagination | `uv run pytest tests/test_query_utils.py -k best_move tests/test_library_repository.py -k best_move_exists tests/test_library_router.py -k "has_gem or has_great" -x` | 11 passed | ✓ PASS |
| `EvalPoint` tier assembly, Pitfall 3/5 invariants | `uv run pytest tests/services/test_library_service.py -k eval_series tests/test_library_router.py -k eval_series -x` | 9 passed | ✓ PASS |
| Backend type safety (phase-175 files only) | `uv run ty check app/ tests/` | 3 diagnostics, all in `app/services/maia_engine.py` (pre-existing, environmental `onnxruntime`/`numpy` unresolved-import, NOT phase 175 — confirmed by file/line) | ✓ PASS (phase-scoped) |
| Backend lint (phase-175 files) | `uv run ruff check <phase-175 files>` | All checks passed | ✓ PASS |
| Great-tier primitives + board markers | `cd frontend && npm test -- --run gemMove boardMarkers` | 39 passed | ✓ PASS |
| Filter UI + param threading | `cd frontend && npm test -- --run FlawFilterControl useFlawFilterStore useLibrary client` | 94 passed | ✓ PASS |
| Analysis mainline stored-tier consumption + sweep demotion | `cd frontend && npm test -- --run Analysis useGemSweep` | 281 passed | ✓ PASS |
| Frontend type safety | `cd frontend && npx tsc -b` | clean | ✓ PASS |
| Frontend lint | `cd frontend && npm run lint` | 0 errors (3 pre-existing warnings in `coverage/` artifacts, unrelated) | ✓ PASS |
| Frontend dead-export check | `cd frontend && npm run knip` | clean | ✓ PASS |
| "row-absence is authoritative" behavior (not just symbol presence) | Read `Analysis.test.tsx:1167-1186` | Test seeds data that WOULD classify as a gem if the live path ran, then asserts no marker AND `lastLiveGemGradingCall()?.fen` is null — a genuine behavior proof, not a presence check | ✓ PASS |
| "Best Moves" filter renders on Games tab, NOT Flaws tab (per the post-verify bug fix) | Grep `GamesTab.tsx`/`FlawsTab.tsx` for `onHasGemToggle`/`onHasGreatToggle` | GamesTab passes both handlers at 2 render sites; FlawsTab passes neither at either of its 2 render sites | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|-----------------|--------------|--------|----------|
| BOARD-01 | 175-02, 175-03, 175-05 | Board shows stored gem/great markers | ✓ SATISFIED | Backend `EvalPoint` fields + frontend rendering on every surface (board, badge, popover, variation tree, chart), confirmed instant-paint by approved human-verify checkpoint. |
| BOARD-02 | 175-05 | `useGemSweep` retired/demoted; SEED-107 closes | ⚠️ PARTIALLY SATISFIED | Demotion is functionally complete and tested; SEED-107 administrative closure is outstanding (see gap). |
| FILT-01 | 175-01, 175-04 | Library filter by has-gem/has-great | ✓ SATISFIED | Backend EXISTS filter + frontend toggles, bug-fixed and re-verified to actually render on the real Games tab. |

No orphaned requirements — REQUIREMENTS.md maps exactly BOARD-01, BOARD-02, FILT-01 to Phase 175, and all three are claimed by at least one plan's `requirements:` frontmatter.

Note: `.planning/REQUIREMENTS.md`'s traceability table still shows BOARD-01/BOARD-02/FILT-01 as "Pending" and their checkboxes unchecked — this is expected pre-merge state (not a phase gap); it is typically flipped at milestone/phase-close bookkeeping, not during execution/verification.

### Anti-Patterns Found

None. Scanned all 23 files touched across the 5 plans for `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` and "not yet implemented"/"coming soon"/"not available" — zero matches (one unrelated pre-existing string, "Tactic line not available for this flaw," in `VariationTree.tsx`, is an existing UI copy string unrelated to gem/great and was not introduced by this phase).

### Deviations From Plan (self-reported in SUMMARYs, independently spot-checked)

- **175-03:** `MovesByRatingChart.tsx` modified though not in `files_modified` frontmatter — verified as a genuine plan-list omission (the plan's own D-02b truth requires chart coverage), not scope creep. Confirmed present and correct (`case 'great':` at line 194).
- **175-04 → post-verify fix (commit `666c8265`):** The "Best Moves" section was gated on `!showTacticFilter`, which is false on BOTH library tabs (both pass `showTacticFilter=true`), so the filter never rendered on the real Games tab despite the Task-1 test passing (it rendered with the unrealistic default `showTacticFilter=false`). This was caught by the plan's own blocking human-verify step in 175-05 and fixed by gating on handler presence instead. **Independently re-verified in this pass**: the fix is real, correctly discriminates Games vs. Flaws tabs, and all related tests pass.
- **175-05:** `MaiaMoveQualityBar.tsx` modified though not in `files_modified` frontmatter — same category of omission as 175-03's chart fix; confirmed present (`isGreat` prop wired at line 537).

None of these deviations affect goal achievement — they are documented, justified, and independently confirmed correct.

### Human Verification Required

None outstanding. The phase's one `checkpoint:human-verify` gate (175-05 Task 3 — instant stored-tier markers + fallback-only live compute) is documented as approved by the user on 2026-07-17 in 175-05-SUMMARY.md, matching the explicit context note provided for this verification run.

### Gaps Summary

One gap, low severity, low effort:

**SEED-107 was not actually closed despite being claimed closed.** The phase's engineering work fully satisfies BOARD-02's functional intent — `useGemSweep` is demoted (not deleted), documented as a fallback, and both live gem mechanisms (Phase-163 live-at-cursor + Phase-172 sweep) are gated to fire only when no stored tier exists, all proven by passing behavioral tests plus an approved human-verify checkpoint. However, the roadmap's own Success Criterion 2 text bundles a second, distinct claim into the same bullet — "SEED-107 closes as superseded" — and that specific claim is false as of this verification: `.planning/seeds/SEED-107-gem-sweep-starved-by-live-engines.md` still carries `status: dormant` and still lives in the active `.planning/seeds/` directory, never `git mv`'d to `.planning/seeds/closed/`. This is exactly the kind of "SUMMARY narrative vs. repo state" mismatch this verification is designed to catch (175-05-SUMMARY.md's own frontmatter `key-decisions` and body assert closure as fact). The fix is a one-line status edit plus a `git mv` — no design or engineering work is required, since SEED-107's frontmatter already declared `superseded_by: SEED-108` at planting time (2026-07-15, before this phase even started).

**Recommendation:** Close this out as a trivial follow-up (either a same-branch fixup commit before merge, or a `/gsd-quick` task) rather than a full replan — the phase's functional/behavioral goal is fully achieved.

---

*Verified: 2026-07-17T01:39:12Z*
*Verifier: Claude (gsd-verifier)*
