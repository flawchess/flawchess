---
phase: 129-tactic-filter-ui
plan: "04"
subsystem: api
tags: [tactic-filter, taxonomy, family-mapping, backend, python, sqlalchemy]

requires:
  - phase: 129-01
    provides: depth filter + orientation toggle for tactic families (TACUI-04)
  - phase: 128-1
    provides: DISCOVERED_CHECK=25 and TRAPPED_PIECE=26 motif ints

provides:
  - 10-family FAMILY_TO_MOTIF_INTS taxonomy (the cross-stack contract for plan 129-05)
  - "combinations" family dropped; those ints (9-17) now belong to no family
  - test_tactic_comparison_produces_overflow: regression proving G-01 closed at data layer

affects:
  - 129-05 (frontend must mirror these 10 key strings string-for-string as TacticFamily union)
  - 126-comparison (Phase 126 tactic comparison reuses FAMILY_TO_MOTIF_INTS — now 10 families)
  - 128-chips (Phase 128 chip config loop iterates FAMILY_TO_MOTIF_INTS.items() — now 10 × 2 cols)

tech-stack:
  added: []
  patterns:
    - "FAMILY_TO_MOTIF_INTS is the single backend source of truth; all consumers iterate it dynamically (.keys()/.items()/.get(fam, [])) — no hard-coded family count anywhere"
    - "dropped/unknown family key → FAMILY_TO_MOTIF_INTS.get(fam, []) returns [] → no-op EXISTS clause (T-129-10 mitigation)"

key-files:
  created: []
  modified:
    - app/repositories/library_repository.py
    - app/services/library_service.py
    - app/schemas/library.py
    - app/routers/library.py
    - app/repositories/query_utils.py
    - tests/services/test_tactic_comparison_service.py
    - tests/test_flaw_predicate.py

key-decisions:
  - "10-family taxonomy: fork, skewer, pin, x_ray, double_check, discovered_check, discovered_attack, trapped_piece, hanging, mate — in display order (cross-stack contract)"
  - "combinations family dropped entirely (ints 9-17 now belong to no family); no migration needed"
  - "mate int set unchanged (ints 7-8, 18-24); _depth_ok mate exemption preserved"
  - "No DB migration, no data backfill: families are a query-time grouping only"
  - "All consumers iterate FAMILY_TO_MOTIF_INTS dynamically — no code change needed in query_utils, library_service get_tactic_comparison, or chip-config loop"

requirements-completed: [TACUI-05, TACUI-08]

duration: 7min
completed: 2026-06-20
status: complete
---

# Phase 129 Plan 04: Tactic Family Taxonomy Redesign Summary

**Replaced 6-family FAMILY_TO_MOTIF_INTS with the authoritative 10-family taxonomy, closing UAT gap G-01 (More Tactics accordion unreachable) and making each Tier-2 tactic motif its own standalone family**

## Performance

- **Duration:** ~7 min
- **Started:** 2026-06-20T11:46:45Z
- **Completed:** 2026-06-20T11:53:56Z
- **Tasks:** 3
- **Files modified:** 7

## Accomplishments

- Rewrote `FAMILY_TO_MOTIF_INTS` from 6 families to the 10-family taxonomy (fork, skewer, pin, x_ray, double_check, discovered_check, discovered_attack, trapped_piece, hanging, mate) — the cross-stack contract plan 129-05 must mirror string-for-string
- Dropped the `combinations` family (DEFLECTION..SACRIFICE, ints 9-17); those ints now belong to no family and are excluded from all chip/grid/EXISTS surfaces
- Confirmed no DB migration and no data backfill required (game_flaws stores raw SmallInteger motif codes; families are a query-time grouping only)
- Added regression tests proving G-01 is closed: `test_family_mapping_10_produces_overflow` (data-layer) and `test_tactic_comparison_produces_overflow` (service-layer) confirm that with 10 families the top-6 selection always leaves 4 overflow families, making the More Tactics accordion (D-14) exercisable
- Full backend suite green (2822 passed, 15 skipped)

## No-Migration Finding (Plan Requirement)

`game_flaws.allowed_tactic_motif` and `game_flaws.missed_tactic_motif` are `SmallInteger` columns storing raw `TacticMotifInt` integer codes. The `FAMILY_TO_MOTIF_INTS` dict is a presentation-layer grouping evaluated at query time via `.get(fam, [])` expansion. Changing the family→int mapping re-groups existing rows automatically — no Alembic migration and no data backfill are required.

**Dropped-combinations visibility effect:** Existing game_flaws rows carrying the 8 dropped combinations ints (9=DEFLECTION, 10=ATTRACTION, 11=INTERMEZZO, 13=INTERFERENCE, 14=SELF_INTERFERENCE, 15=CLEARANCE, 16=CAPTURING_DEFENDER, 17=SACRIFICE) remain intact in the database but no longer appear under any family chip, grid, or EXISTS expansion. Those flaws are invisible to the family surfaces — the only user-visible data effect.

## Locked Cross-Stack Contract

The 10 family-key strings plan 129-05 (frontend) must mirror exactly:

```
fork | skewer | pin | x_ray | double_check | discovered_check | discovered_attack | trapped_piece | hanging | mate
```

In display order. These are the `TacticFamily` union member strings.

## Task Commits

1. **Task 1: Rewrite FAMILY_TO_MOTIF_INTS to 10-family taxonomy** — `0916c787` (feat)
2. **Task 2: Update backend consumers + tests for new family set** — `d8bbbd4a` (feat)
3. **Task 3: Cross-phase regression grep + full backend gate** — `5801bce0` (chore)

## Files Created/Modified

- `app/repositories/library_repository.py` — FAMILY_TO_MOTIF_INTS rewritten to 10 families; comment updated to describe new taxonomy + no-migration rationale; count_cols comment updated from 12/6 to 20/10
- `app/services/library_service.py` — `_compute_tactic_bullets` docstring updated: "6 families" → "10 families (Plan 04 G-01)"
- `app/schemas/library.py` — `TacticBullet.family` comment updated from `"fork", "pin_skewer"` to `"fork", "skewer" (10-family taxonomy, plan 129-04)`
- `app/routers/library.py` — tactic_families docstring example updated from `pin_skewer` to `skewer`
- `app/repositories/query_utils.py` — tactic_families docstring example updated from `pin_skewer` to `skewer`
- `tests/services/test_tactic_comparison_service.py` — replaced 4 old-taxonomy tests; added 5 new tests: `test_family_mapping_ten_families`, `test_family_mapping_excludes_combinations`, `test_family_mapping_covers_selected_motifs`, `test_family_mapping_10_produces_overflow`, `test_combinations_request_is_noop`, `test_tactic_comparison_produces_overflow`
- `tests/test_flaw_predicate.py` — replaced `pin_skewer` with `pin` in tactic family clause test

## Consumer Audit

All consumers iterate `FAMILY_TO_MOTIF_INTS` dynamically:
- `app/repositories/query_utils.py:227` — `FAMILY_TO_MOTIF_INTS.get(fam, [])` expansion (no-op for unknown/dropped keys; T-129-10 mitigation)
- `app/services/library_service.py:1267` — `list(FAMILY_TO_MOTIF_INTS.keys())` in `_compute_tactic_bullets`
- `app/services/library_service.py:1456` — `list(FAMILY_TO_MOTIF_INTS.keys())` in `get_tactic_comparison` for `all_families`
- `app/repositories/library_repository.py:1632` — `FAMILY_TO_MOTIF_INTS.items()` in chip-config loop (now emits 20 COUNT cols × 2 orientations)

None required code changes.

## Cross-Phase Grep Result

```
grep -rn "pin_skewer|\"discovery\"|'discovery'|combinations" app/ tests/
```

Remaining hits after fixes:

| File | Hit | Disposition |
|------|-----|-------------|
| `app/repositories/library_repository.py:70-71` | Comment describing dropped `pin_skewer` / `combinations` families | Intentional — new comment explains the taxonomy change |
| `app/services/tactic_detector.py:28,304` | "combinations" as ordinary English word (chess combinations in detector comments) | Benign — not a family key reference |
| `tests/services/test_tactic_comparison_service.py` | Multiple — new test code intentionally references "combinations" to verify the no-op | Intentional test assertions |
| `tests/test_openings_service.py`, `tests/services/test_canonical_slice_*`, etc. | "combinations" as ordinary English word (result × color combinations, etc.) | Benign |
| `app/repositories/benchmark_cohort_cdf_repository.py` | "combinations" as ordinary English word | Benign |
| `app/repositories/query_utils.py:34` | "combinations" as ordinary English word in ply-parity comment | Benign |

**No live FAMILY_TO_MOTIF_INTS key, EXISTS expansion, or comparison assertion still uses old family keys.**

## Deviations from Plan

### Minor additional fixes (Rule 2 — missing critical documentation)

**1. [Rule 2 - Missing] Fixed stale docstring examples in router and query_utils**
- **Found during:** Task 3 cross-phase grep
- **Issue:** `app/routers/library.py:244` and `app/repositories/query_utils.py:123` still had `"fork", "pin_skewer"` as docstring examples for `tactic_families`
- **Fix:** Updated to `"fork", "skewer"` and "unknown/dropped keys are silently ignored"
- **Files modified:** app/routers/library.py, app/repositories/query_utils.py
- **Committed in:** `5801bce0` (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (documentation — stale docstring examples)
**Impact on plan:** Trivial. No behavior change, only comment/docstring accuracy.

## Issues Encountered

None.

## Next Phase Readiness

- Plan 129-05 (frontend) can now implement `TacticFamily` as a union of exactly these 10 key strings: `fork | skewer | pin | x_ray | double_check | discovered_check | discovered_attack | trapped_piece | hanging | mate`
- The backend emits up to 20 bullets (10 families × 2 orientations) — frontend must handle the larger response
- The overflow accordion (D-14) is now reachable because `len(FAMILY_TO_MOTIF_INTS) > 6` guarantees `ranked_families[6:]` is always non-empty

---
*Phase: 129-tactic-filter-ui*
*Completed: 2026-06-20*
