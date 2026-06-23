---
quick_id: 260618-aiq
type: quick
slug: fix-in-process-eval-drain-to-tag-tactic-
date: 2026-06-18
files_modified:
  - app/services/flaws_service.py
  - app/services/eval_drain.py
  - tests/services/test_flaws_service.py
---

<objective>
Make the in-process eval drain tag tactic motifs LIVE, instead of leaving
tactic_motif NULL until a later backfill_flaws.py run.
</objective>

<root_cause>
`app/services/eval_drain.py:_classify_and_fill_oracle` runs
`classify_game_flaws(game, positions)` (which reads `positions[ply+1].pv` via
`_detect_tactic_for_flaw`) BEFORE it writes the freshly-computed PVs into
`game_positions` (the batched PV UPDATE happens ~80 lines later, L753-769). So at
classify time `positions[ply+1].pv` is still NULL and every live classify writes
`tactic_motif = NULL`. The PV lands in the DB one step later, usable only by a
subsequent backfill.

Confirmed empirically during Phase 125 verification: 22+ freshly-drained games had
0 tagged flaws despite a valid PV at every flaw ply; a targeted
`backfill_flaws.py --user-id 28` immediately produced 8/11, 6/9, 7/12 tags on the
same games.
</root_cause>

<tasks>

<task>
  <name>Task 1: Thread an explicit PV override through classify so the drain tags live</name>
  <files>app/services/flaws_service.py, app/services/eval_drain.py</files>
  <action>
    flaws_service.py:
    - `from collections.abc import Mapping` (new import).
    - `classify_game_flaws(game, positions, pv_by_ply: Mapping[int, str] | None = None)`.
    - Thread `pv_by_ply` through `_build_flaw_record` into `_detect_tactic_for_flaw`.
    - In `_detect_tactic_for_flaw`, resolve pv as: `pv_by_ply.get(n + 1)` when
      pv_by_ply is provided, else fall back to `positions[n+1].pv`
      (preserves backfill behavior EXACTLY when pv_by_ply is None).

    eval_drain.py `_classify_and_fill_oracle`:
    - Build `pv_by_ply = {ply: entry[3] for ply, entry in engine_result_map.items() if entry[3] is not None}`
      and pass it: `classify_game_flaws(game, positions, pv_by_ply=pv_by_ply)`.
    - Do NOT change the other two `classify_game_flaws` callers (L~815 _preclassify,
      L~1414 entry-ply drain) — they correctly read PVs from the DB.
    - Do NOT mutate in-memory `GamePosition.pv` (would over-persist PVs at every
      evaluated ply via ORM autoflush, violating the flaw-adjacent-only storage policy).
  </action>
  <verify>uv run ty check app/ tests/ && uv run ruff check app/ tests/</verify>
  <done>The full drain passes engine PVs into classify; backfill path unchanged.</done>
</task>

<task>
  <name>Task 2: Regression test for live PV-override tagging</name>
  <files>tests/services/test_flaws_service.py</files>
  <action>
    Add a unit test on `classify_game_flaws`: with positions whose `pv` is None at
    the flaw+1 ply (plus the required `move_san` at the flaw ply), passing
    `pv_by_ply={flaw_ply+1: <known-firing hanging-piece PV>}` yields a flaw record
    with a non-NULL `tactic_motif_int`; and with `pv_by_ply=None` it stays None.
    Reuse the D-09 hanging-piece (board_fen, pv) pattern from
    tests/test_backfill_flaws.py / tests/services/test_tactic_detector.py.
  </action>
  <verify>uv run pytest tests/services/test_flaws_service.py -q</verify>
  <done>A passing test pins both the override-fires and no-override-NULL paths.</done>
</task>

</tasks>

<success_criteria>
The in-process drain tags tactic motifs at classify time (verified live on dev:
newly-drained games gain tags). The backfill path is byte-for-byte unchanged when
pv_by_ply is None. ty + ruff clean; targeted tests pass.
</success_criteria>

<note>
Bug found during Phase 125 verification of the live drain path. NOT part of Phase
125 scope (125 is the historical backfill). Phase 124 shipped the detector/schema;
this wires the detector into the live in-process drain.
</note>
