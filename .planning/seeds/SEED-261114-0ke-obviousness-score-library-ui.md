---
id: SEED-261114-0ke
status: dormant
planted: 2026-11-14
planted_during: Phase 250 executing (facepalm-blunder selection); /gsd-explore session with the owner
trigger_when: Phase 250 is closed AND the Phase 252 short-engine-line repair backfill has finished on prod, so facepalm_score coverage is final
scope: small, one phase. Backend filter params and schema field, frontend range slider, card chip and popover
---

# SEED-261114-0ke: Obviousness score in the library UI (facepalm score surfaced to users)

Show the Phase 250 `facepalm_score` to users under the name "Obviousness": a range filter in the library Tags
side panel and a chip on the Flaws-tab cards. Replaces the deferred item "Library side-panel range filter on the
facepalm score" in `250-CONTEXT.md`.

## Why This Matters

The score decides which blunders the blunder-check drill serves, but it is invisible. Surfacing it lets the owner
and users see how obvious the model judges a blunder, browse the low end the drill never serves (the drill only
takes scores >= `FACEPALM_SCORE_MIN`, 0.7 today), and find their most careless blunders in the library.

## Decisions (owner, 2026-11-14)

1. **Name:** "Obviousness" as the filter label, `Obvious 84%` as the card chip. "Facepalm" stays internal only
   (potentially insulting). "Blatant / Blatancy" was considered and rejected: it carries blame and is a harder
   word for non-native speakers. Other rejected options: Visibility, Spottable, Oversight, Avoidable, Howler.
2. **Not a probability.** 250 D-01 holds: the score is a ranking, not calibrated across all blunders, and no copy
   may present it as a share of peers. The chip reads as a degree ("84% obvious"). Add a short popover: the
   model's judgement of how obvious the blunder was, not a probability. Avoid wording like "avoidable" or
   "chance you'd see it".
3. **Range filter** in the library Tags side panel, for the Games and Flaws tabs, modelled on the tactic depth
   filter.
   - Full range 0-100% = no filter (same convention as the tactic depth full range).
   - A narrowed range keeps only flaws with a non-NULL `facepalm_score` in range. Mistakes, inaccuracies and
     user blunders without a stored line drop out.
   - Tag filters already apply to the user's flaws only (`player_only_gate`), so opponent scoring is not needed.
   - On the Games tab the range joins the single flaw `EXISTS`, so it combines with severity, tags and tactic
     filters on the same flaw row.
4. **Flaws-tab cards** show the `Obvious N%` chip when the flaw has a score, nothing otherwise.
5. **Out of scope:** no score in the blunder-check solution speech bubble (owner considered it, then dropped it).
6. **Rename is UI copy only.** The column and code stay `facepalm_score`.
7. **Values may shift** when the model is refitted (repaired lines, later drill answers). The owner accepts this.

## When to Surface

**Trigger:** Phase 250 is closed AND the Phase 252 backfill has finished on prod.

Before that the scores on prod are incomplete or computed from truncated lines, so a filter would show misleading
coverage.

## Scope Estimate

**Small**, one phase:
- Backend: `min`/`max` score query params on the library endpoints, a clause in the shared flaw filter, the score
  on the flaw card schema.
- Frontend: a range slider in the Tags panel (reuse the tactic depth pattern), filter-store state, the chip and
  popover on the flaw card.

## Breadcrumbs

- `.planning/phases/250-facepalm-blunder-selection/250-CONTEXT.md` (D-01 score definition and copy rule; deferred
  list)
- `app/services/facepalm_score.py`, `app/services/blunder_check_rules.py` (`FACEPALM_SCORE_MIN`)
- `app/models/game_flaw.py` (`facepalm_score` REAL, NULL when any input is missing)
- `app/routers/library.py` (`min_tactic_depth` / `max_tactic_depth` params: the pattern to copy)
- `app/repositories/query_utils.py` (flaw `EXISTS` in `apply_game_filters`),
  `app/repositories/library_repository.py` (`build_flaw_filter_clauses`, `flaw_exists_from_table`,
  `player_only_gate`, `_TACTIC_DEPTH_FULL_MIN/MAX`)
- `app/schemas/library.py` (flaw card schemas)
- `frontend/src/components/filters/TacticDepthFilter.tsx`, `frontend/src/components/filters/FlawFilterControl.tsx`,
  `frontend/src/hooks/useFlawFilterStore.ts`, `frontend/src/lib/tacticDepth.ts`

## Notes

Open details for discuss-phase: slider step (5% suggested), whether a narrowed range shows a hint that only
scored blunders remain, chip placement and color on the card.
