---
quick_id: 260618-aiq
type: quick
slug: fix-in-process-eval-drain-to-tag-tactic-
date: 2026-06-18
status: complete
files_modified:
  - app/services/flaws_service.py
  - app/services/eval_drain.py
  - tests/services/test_flaws_service.py
---

# Quick Task 260618-aiq: Live tactic tagging in the in-process eval drain

**The in-process eval drain now tags tactic motifs at classify time; verified live
on dev (9 games drained post-fix → 37/53 M+B flaws tagged, vs 0 before the fix).**

## Problem

`app/services/eval_drain.py:_classify_and_fill_oracle` ran `classify_game_flaws`
(which reads `positions[ply+1].pv` via `_detect_tactic_for_flaw`) BEFORE writing the
freshly-computed PVs into `game_positions` (the batched PV UPDATE runs ~80 lines
later). So at classify time `positions[ply+1].pv` was NULL and every live classify
wrote `tactic_motif = NULL`; tags only appeared on a later `backfill_flaws.py` run.

Found during Phase 125 verification of the live drain path. Confirmed empirically:
22+ freshly-drained games had 0 tags despite a valid PV at every flaw ply; a targeted
`backfill_flaws.py --user-id 28` immediately produced 8/11, 6/9, 7/12 tags on the
same games (the stored PVs were valid; only the live-classify ordering was wrong).

## Fix

Thread an explicit PV override through the classify path (no ORM mutation):

- `app/services/flaws_service.py`:
  - `from collections.abc import Mapping`.
  - `classify_game_flaws(game, positions, pv_by_ply: Mapping[int, str] | None = None)`.
  - Threaded `pv_by_ply` through `_build_flaw_record` into `_detect_tactic_for_flaw`.
  - `_detect_tactic_for_flaw` resolves the PV as `pv_by_ply.get(n + 1)` when provided,
    else falls back to `positions[n + 1].pv` — backfill behavior is byte-for-byte
    unchanged when `pv_by_ply is None`.
- `app/services/eval_drain.py:_classify_and_fill_oracle`:
  - Builds `pv_by_ply = {ply: entry[3] for ply, entry in engine_result_map.items() if entry[3] is not None}`
    and passes it to `classify_game_flaws`.
  - The other two `classify_game_flaws` callers (`_preclassify`, entry-ply drain) are
    unchanged — they correctly read PVs from the DB.
  - The in-memory `GamePosition.pv` is NOT mutated (would over-persist PVs at every
    evaluated ply via ORM autoflush, violating the flaw-adjacent-only storage policy).

## Tests

`tests/services/test_flaws_service.py::TestTacticIntegration::test_pv_by_ply_override_tags_when_positions_pv_is_none`:
with refutation PVs absent from `game_positions` (the live-drain state), the control
(no override) leaves both the white ply-4 and black ply-5 blunders NULL, and the
override (`pv_by_ply={5: "d5c4", 6: "f3g4"}`) tags both as HANGING_PIECE with
confidence 100.

## Verification

- `uv run pytest tests/services/test_flaws_service.py -q` → 122 passed.
- `uv run pytest tests/test_backfill_flaws.py -q` → 7 passed (backfill path unchanged).
- `uv run pytest tests/services/test_eval_drain.py tests/services/test_full_eval_drain.py tests/services/test_eval_drain_stage_b.py -q` → 53 passed, 4 skipped.
- `uv run ty check app/ tests/` → clean. `uv run ruff check` → clean.
- **Live on dev (definitive):** after reloading the dev server, 9 games drained in
  ~70s yielded 37/53 M+B flaws tagged (≈70%, matching the has-PV fire rate). Before
  the fix the same window produced 0 tags.

## Notes

- NOT part of Phase 125 scope (125 is the historical backfill). Phase 124 shipped the
  detector + schema; this wires the detector into the live in-process drain so newly
  imported/drained games are tagged without a follow-up backfill.
- Committed on the phase-125 branch (`branch_name` null in quick config). Consider
  cherry-picking onto its own branch off `main` if you want it reviewed/merged
  independently of Phase 125.
