# Phase 261: Blunder-Check Exploration Arm (SEED-261121-t50) - Context

**Gathered:** 2026-11-22
**Status:** Ready for planning

<domain>
## Phase Boundary

The blunder-check drill only serves blunders at or above `FACEPALM_SCORE_MIN` (0.70 since Phase 259), so user
answers can never validate or refit the facepalm score below the cut. This phase delivers:

1. An exploration arm: about 20% of blunder slots are filled by a random draw with no score cut.
2. A serve-time record on `blunder_check_windows`: the arm, the sampling probability, a snapshot of the score
   and its inputs, and the type-line facts.
3. Avatar feedback in the solution view: the snapshotted score, a type line and a "hard to catch" line.
4. A calibration script under `scripts/blunder_check/`.

Not in this phase: the one-tap "unfair" flag, review gates or a stop rule for the arm, a fit on user answers, any
change to the main cut (0.70), the herring share, the window length or the timing. The calibration analysis
itself runs later, on demand.

</domain>

<decisions>
## Implementation Decisions

### Carried forward from the seed (owner, 2026-11-21; not re-discussed)
- **Share:** one coin flip per blunder slot, share in one named constant (20%), own and foreign slots alike.
  Randomised per window, never per user.
- **Draw:** the existing game-first probe without the score cut, on scored rows only (the inputs must exist to
  be snapshotted). Among several eligible blunders of the picked game the draw chooses at random, never by score.
  Every other judge filter stays for both arms (owner side only, served-once, early-ply floor, undecided
  position, classified case, window-position fit).
- **Main arm:** keeps the 0.70 cut. This phase does not change it.
- **Counts as normal:** exploration windows give points, streaks, medals and leaderboard score like any other
  window. No marker the user can see.
- **Runs indefinitely:** no review gate, no stop rule. Lowering or stopping the arm is a constants change.
- **The score shown is the serve-time snapshot,** so it stays stable across refits. Copy stays neutral about
  whose blunder it is (many served blunders are from other users' games).
- **Type line side:** the facepalm type (allowed loss / missed win, 257 D-02), the one classification the score
  and the library stats use. `window_case` is not used for it. If that side has no qualifying swing, there is no
  type line, even when the other side has one.
- **Type line floor:** a material swing of at least 2 points (piece values 1 / 3 / 3 / 5 / 9), or a mate. A lost
  pawn gets no line; a lost exchange (2) does. The floor is never applied to the stored `material_loss` /
  `material_missed` (decaying means). The drill walks the stored engine lines at serve time for the one blunder
  the window serves and stores the result on the window. No new `game_flaws` column.

### Feedback display
- **D-01: The score is shown with the library's Facepalm chip** (`FacepalmChip` with its popover), fed by the
  snapshotted score. One look for the score across the app.
- **D-02: The drill's chip popover explains the score only.** It does not name the facepalm type, unlike the
  Flaws card. The type appears in the drill only through the type line under its own rule, so a positional
  blunder is never labelled "allowed loss" there. The score-meaning sentence must stay neutral about whose
  blunder it is (the library's `facepalmScoreMeaning` says "your" / "their" level).
- **D-03: The new lines are a second short paragraph after the existing verdict sentence** ("Nxe6 was a blunder.
  You missed it +3. Best was Bxf4."). The points sentence stays first; chip, type line and "hard to catch" line
  follow. Applies to the desktop card and the phone / tablet strip alike.
- **D-04: Every blunder window with a snapshot shows the feedback,** caught or missed, both arms. Nothing in the
  UI depends on the arm. Windows served before this phase (no snapshot) show nothing new.
- **D-05: A false alarm shows nothing new.** The false-alarm solution keeps handing out no case and no blunder
  (`FalseAlarmSolution`), also when the unreached blunder had a low score.

### "Hard to catch" line
- **D-06: The cut is a snapshotted score below 50%,** one named constant in Phase 259 score units. Re-checked on
  the new score on 2026-11-22: the caught rate drops clearly only below 0.5 (see Specifics). It is tied to the
  score, never to the arm, and shows together with the chip and the type line when there is one.
- **D-07: Wording as in the seed.** Missed: "This one was hard to catch." Caught: "Well spotted, this one was
  hard to catch."

### Type line rule
- **D-08: The swing is read at the deepest settled odd depth of the Phase 259 quiet walk.** The quiet rule
  (259 D-02) gives a balance at each odd depth 1, 3, 5, 7, 9; the type line uses the last odd depth the stored
  line still covers. A knight lost at depth 3 and won back by depth 7 gets no line; a fork that only wins at
  depth 5 gets one. No second material rule: the walk and the per-depth loss / gain rules of Phase 259 are
  reused (`quiet_line_facts`, `quiet_best_line_facts`, `loss_by_depth`, `gain_by_depth`).
- **D-09: The mate wording applies when the stored line reaches mate.** "The blunder allows checkmate" when the
  played line (the blunder plus the stored refutation line) ends with the blunderer mated; "The blunder misses
  checkmate" when the stored best line mates the opponent. A forced mate the engine only reports by eval, beyond
  the stored line, does not count. Mate takes precedence over the material wording.
- **Copy (seed):** "The blunder allows a material loss" / "The blunder allows checkmate" / "The blunder misses a
  material win" / "The blunder misses checkmate".

### Settled by measurement (2026-11-22, not discussed further)
- **D-10: No new index for the exploration probe.** The own-game probe without the cut is an index-only scan on
  `ix_game_flaws_facepalm_inputs` (79 ms on prod user 28, 21,147 blunder rows). The foreign probe only loses a
  predicate. The planner still confirms the foreign pick with EXPLAIN on prod before release.
- **D-11: No special rule for the served-once consumption.** Exploration windows use up low-score own blunders
  like any other served window. Pools are large enough (median 1,984 scored own blunders per drill user, 10th
  percentile 305).
- **D-12: The best-move line is still stored after the Phase 259 drop release** (`game_positions.pv` at the flaw
  ply; 98.5% of scored blunders have it, 1.1% only `best_move`). A missing best line gives no "misses" line,
  mirroring `missed = 0` for an unknown best line (254 D-18).

### Claude's Discretion
The owner did not select "Record, script, acceptance" for discussion. Defaults proposed in the session and
accepted with "I'm ready for context":
- **Pre-phase windows keep a NULL arm,** as a separate legacy population (served under the 0.50 cut and partly
  under the old score). No backfill to "main".
- **Both arms get the snapshot** (score, `loss`, `missed`, `maia_played_prob`, `maia_best_prob`, the best-reply
  probability) and the type-line facts. Herring windows carry none.
- **Calibration script:** caught rate by score band with Wilson intervals (`app/services/score_confidence.py`
  `wilson_bounds`), split by arm and `is_own`; reached windows as the denominator, false alarms before the
  blunder reported beside it. It reads the snapshot, and for legacy windows the live score where the game still
  exists.
- **Acceptance for the share:** a seeded test of the slot draw against the 20% constant, plus a prod count of
  served exploration windows over ended blunder windows after release. Slot redraws and own-to-foreign
  conversions may shift the served share slightly; the planner sets the tolerance.
- Column names and types on `blunder_check_windows`, how the arm is encoded (the project rule: SMALLINT +
  IntEnum + CHECK or TEXT + CHECK, no native ENUM), whether the type-line facts are stored as a swing value plus
  a mate flag or as a small enum.
- How the exploration draw is wired into the pools (`_Pool`, `load_blunder_flaws`, `_blunder_candidate`'s score
  gate, `assign_windows`), and what an exploration slot does when its origin has no supply (it should follow the
  existing own-to-foreign conversion and keep its arm).
- What "the sampling probability" column holds (the arm share at serve time is the minimum).
- The wire schema change (`BlunderSolution` gets the score and the feedback facts; the window wire schema
  changes once).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Seed and roadmap
- `.planning/seeds/SEED-261121-t50-blunder-check-exploration-arm.md` — owner decisions 1 to 7, design points, the
  avatar feedback rules, the random-draw-or-bands comparison. Its Evidence numbers are from the old score and
  are superseded by "Specifics" below.
- `.planning/ROADMAP.md` (Phase 261) — goal, scope and out-of-scope list.

### Prior phase decisions
- `.planning/phases/259-facepalm-first-principles-refit/259-CONTEXT.md` — D-02 (quiet rule), D-03 (decaying
  mean), D-05 (stored `loss` / `missed`), D-07 / D-08 (best-reply probability), D-15 (0.70 cut), D-17 (covering
  index).
- `.planning/phases/257-facepalm-rate-library-stats/257-CONTEXT.md` — D-02 (facepalm type on the material
  inputs), D-10 (type copy in the library).
- `.planning/phases/250-facepalm-blunder-selection/250-CONTEXT.md` — D-01 (score meaning), D-12 to D-17 (slot
  shares, origins, served-once).
- `.planning/phases/249-blunder-check-playable-mvp/249-CONTEXT.md` — D-10 (no repeats; the false-alarm solution
  hands out no blunder), D-14 (points), D-15 (own tables).
- `.planning/phases/251-blunder-check-schedule-streak-and-leaderboards-seed-261108-d/251-CONTEXT.md` — streaks,
  medals and leaderboards the exploration windows count towards.

### Reports
- `reports/blunder-check/facepalm-fit-2026-11-22.md` — the Phase 259 fit and the owner section for the 0.70 cut.

### Project rules
- `CLAUDE.md` — database design rules (no native ENUM, FK and CHECK rules), `Literal` types, nesting depth gate,
  changelog rule, pre-merge gate.
- `frontend/CLAUDE.md` — styling, testids, popover copy rules.
- `docs/production-runbook.md` — prod limits for any operator check (`max_connections` 50).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/services/blunder_check_rules.py`: `draw_slot_plan` (the one place a slot is drawn; `SlotPlan` carries
  origin and shape today), `FACEPALM_SCORE_MIN`, the share constants.
- `app/repositories/blunder_check_repository.py`: `_unserved_qualifying_blunder_exists` (the probe; the score
  predicate is one condition in its list), `pick_own_game_ids`, `pick_foreign_game_ids`,
  `pick_nearest_foreign_game_ids`, `load_blunder_flaws` (filters `score >= FACEPALM_SCORE_MIN` and returns the
  score), `NewWindow` / `_window_row`.
- `app/services/blunder_check_candidates.py`: `_blunder_candidate` re-checks the score gate in Python;
  `assign_windows` picks with `rng.choice` over all options of all eligible games.
- `app/services/blunder_check_selection.py`: `compose_windows`, `_Pool`, `_fill_from_source`,
  `_convert_empty_own_to_foreign`, `_new_window` (where the snapshot and the type-line facts would be built; it
  has the game's positions and PGN).
- `app/services/line_material.py`: `quiet_line_facts`, `quiet_best_line_facts`, `LineFacts` (`loss_by_depth`,
  `mate_ply`, `opponent_mate_ply`). `app/services/facepalm_material.py`: `loss_by_depth`, `gain_by_depth`.
  `app/services/facepalm_inputs.py`: `facepalm_material_inputs` (callers pass `best_pv or best_move`).
- `app/services/facepalm_score.py`: `facepalm_expr`, `facepalm_score` (Python twin), `facepalm_type_of`.
- `app/services/score_confidence.py`: `wilson_bounds`.
- Frontend: `frontend/src/components/library/FacepalmChip.tsx`, `FacepalmBadgePopover.tsx`,
  `FacepalmExplanation.tsx`, `frontend/src/lib/facepalm.ts` (`toFacepalmPct`, `facepalmScoreMeaning`,
  `FACEPALM_TYPE_LABEL`).

### Established Patterns
- The score is a query-time SQL expression with a Python twin; the snapshot stores its value and inputs at
  composition time (windows are pre-inserted when the session is composed).
- Windows are self-sufficient snapshots (`start_fen`, `move_ucis`); a deleted foreign game only NULLs `game_id`.
- Verdict copy is built in `frontend/src/lib/blunderCheckSolution.ts` (`blunderCopy`, `SolutionCopy` parts) and
  rendered by `SolutionVerdict` in `BlunderCheckSolution.tsx` (card on desktop, strip on phones and tablets).

### Integration Points
- Migration: new nullable columns on `blunder_check_windows` (existing rows stay NULL).
- Wire: `app/schemas/blunder_check.py` `BlunderSolution` (carries no score today); `FalseAlarmSolution` and
  `HerringSolution` stay unchanged.
- The game owner's blunders only: `player_only_gate` on the game's own `user_color`.
- Uncommitted changes in `app/services/flaws_service.py` and `app/services/forcing_line_gate.py` (mate-tag
  fixes from another session) were in the working tree on 2026-11-22. They are not part of this phase.

</code_context>

<specifics>
## Specific Ideas

### Re-measurement on the Phase 259 score (prod, 2026-11-22)

336 ended blunder windows from 38 users since 2026-11-19 (36 / 110 / 126 / 64 per day, the last day partial).
At 20% that is about 15 to 25 exploration windows a day.

| Phase 259 score | Reached | Caught | False alarm before the blunder |
|---|---|---|---|
| below 0.3 | 7 | 57% | 1 |
| 0.3 to 0.5 | 17 | 12% | 4 |
| 0.5 to 0.6 | 25 | 44% | 3 |
| 0.6 to 0.7 | 31 | 52% | 9 |
| 0.7 to 0.8 | 34 | 47% | 3 |
| 0.8 to 0.9 | 70 | 41% | 4 |
| 0.9 to 1.0 | 112 | 71% | 16 |

- Overall 53% caught; 57% at 0.7 and above (n = 216), 48% in 0.5 to 0.7 (n = 56), 25% below 0.5 (n = 24).
  These windows were served under the old score and the 0.50 cut, so the low bands are a selected sample.
- Natural distribution of scored owner-side blunders (1% sample, 22,135 scored rows; 6.7% of the sample is
  unscored): below 0.3 39.8%, 0.3 to 0.5 12.5%, 0.5 to 0.7 12.4%, 0.7 and above 35.3%. About 52% of exploration
  windows will land below 0.5 (about 10% of all blunder windows) and get the "hard to catch" line. This is
  before the judge's other filters.
- Pools of the 38 drill users (own, owner-side, scored blunders): median 1,984, 10th percentile 305, minimum
  153; at 0.70 and above: median 614, 10th percentile 88, minimum 41.
- Own-game probe without the cut on user 28: 79 ms, index-only scan on `ix_game_flaws_facepalm_inputs`.
- Stored lines on scored blunders (0.5% sample, 11,315 rows): best line present on 98.5%, at least 5 plies on
  97.1%, `best_move` only on 1.1%; the refutation line on 100%.

### Copy
- Type line: "The blunder allows a material loss" / "The blunder allows checkmate" / "The blunder misses a
  material win" / "The blunder misses checkmate".
- "Hard to catch": "This one was hard to catch." / "Well spotted, this one was hard to catch."

</specifics>

<deferred>
## Deferred Ideas

- **One-tap "unfair" flag on the feedback** (deferred by the owner, 2026-11-21). Revisit if the caught rate
  tracks the score poorly even on the random sample.
- **A fit on user answers** with per-user terms, once a few thousand answers exist.
- **Review gates or a stop rule for the arm** (declined by the owner).
- **If the drill still looks too hard:** the herring share, the window length or the timing (seed, Evidence).

### Reviewed Todos (not folded)
- `172-deferred-review-findings`, "Bitboard storage for partial-position queries", "WR-01 pt-33 invalid Tailwind
  class", `2026-08-29-variation-tree-nested-button`: keyword matches only, unrelated to the drill.

</deferred>

---

*Phase: 261-blunder-check-exploration-arm*
*Context gathered: 2026-11-22*
