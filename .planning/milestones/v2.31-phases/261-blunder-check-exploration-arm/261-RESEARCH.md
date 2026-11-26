# Phase 261: Blunder-Check Exploration Arm (SEED-261121-t50) - Research

**Researched:** 2026-11-22
**Domain:** brownfield drill selection (FastAPI / SQLAlchemy async / Postgres), one migration, solution wire schema, React solution view, one read-only analysis script
**Confidence:** HIGH (almost everything below was read from the code this session; no new libraries)

## Summary

The drill applies the facepalm cut in exactly three places: the SQL game probe
`_unserved_qualifying_blunder_exists` (used by all three `pick_*_game_ids` functions through
`require_facepalm`), the SQL loader `load_blunder_flaws`, and the Python re-check in
`_blunder_candidate`. Nothing orders or weights by score: `judge_game` sorts flaws by ply,
`assign_windows` sorts options by `(game_id, first_ply, blunder_ply)` only for seed
reproducibility and then takes `rng.choice` over all fitting options of all eligible games. So
"among several eligible blunders of the picked game the draw chooses at random, never by score"
already holds once the cut is removed for the exploration slot.

The one real trap for "a plain random sample of what the drill would serve with no cut" is
**pool sharing**. Pools are per origin and keep every loaded batch for the whole session. A batch
loaded by the cut probe contains only games that hold a blunder at 0.70 or more. If an exploration
slot may draw from such a batch, exploration over-samples games with high-score blunders, which is
a dependence on the current score (the thing the owner rejected). Exploration slots must draw only
from batches loaded by the no-cut ("scored") probe; main slots may draw from any batch (the cut is
applied per candidate).

The type line is fully computable with existing pure functions: `quiet_line_facts` /
`quiet_best_line_facts` give `LineFacts` with `loss_by_depth`, `mate_ply`, `opponent_mate_ply`;
`loss_by_depth` / `gain_by_depth` give the per-odd-depth series; "deepest settled odd depth" is the
last non-None element of the series (settledness is monotone in depth). `_new_window` already has
the PGN, all `GamePosition` rows (with `pv` and `best_move` loaded) and the blunder ply. The only
gaps: `load_blunder_flaws` returns the score but not its five inputs, and the library
`FacepalmChip` / popover / explanation all require a `FacepalmType` and name it, which D-02 forbids
in the drill.

**Primary recommendation:** add `arm` to `SlotPlan` (default `"main"`), draw it in `draw_slot_plan`
for blunder slots, load all *scored* owner-side blunders with their inputs, move the 0.70 cut from
the judge to option time (per slot arm), tag each batch with the probe that loaded it, fill
exploration slots first and only from non-cut batches, preserve the arm with `dataclasses.replace`
everywhere a plan is rewritten, and snapshot score + inputs + type-line facts in `_new_window`.

## Project Constraints (from CLAUDE.md)

- Router: `APIRouter(prefix=..., tags=...)`, relative paths; routers HTTP only, logic in services, SQL only in repositories.
- No native PostgreSQL ENUM. Low-volume domain columns: SMALLINT + IntEnum + CHECK, or TEXT + CHECK. `blunder_check_windows` already uses SMALLINT + IntEnum + CHECK for `window_case`, `outcome`, `better_move_tier` (follow that).
- FK with explicit `ondelete` (no new FK needed here). CHECK constraints for value sets.
- No magic numbers: the 20% share, the 50% "hard to catch" cut and the 2-point type-line floor are named constants.
- `Literal[...]` for fixed value sets in schemas, service and repository signatures; `Sequence` for covariant params.
- ty: zero errors (`uv run ty check app/ tests/ scripts/`), explicit return types, `# ty: ignore[rule]` only with reason.
- Nesting depth <= 4 per function (`scripts/check_function_size.py app/ --fail-over-depth 4`); frontend eslint `max-depth` 4.
- Never `asyncio.gather` on one `AsyncSession`; sequential awaits.
- Sentry: `capture_exception` in non-trivial `except` blocks in services/routers; no variables in messages.
- Comment bug fixes at the fix site.
- Frontend: `data-testid` on interactive elements; `text-sm` floor except info popover bodies; theme colors in `theme.ts`; knip (no dead exports); run `npm run build` for type changes (lint/test don't type-check); no Prettier.
- Umami: popover testids must not interpolate free values; `useTrackedPopoverOpen` builds the target.
- Changelog: user-facing bullets under `## [Unreleased]` when the phase merges.
- Pre-merge gate (ruff format/check, ty x2, function-size gate, `pytest -n auto -x`, frontend lint/build/test/knip).
- Do not run `bin/reset_db.sh`; do not touch `.env` files; never gate a plan on a dev DB reset.
- GSD scope: nothing outside the phase (no unfair flag, no change to the 0.70 cut, herring share, length, timing).
- Prose: em-dashes sparingly.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Carried forward from the seed (owner, 2026-11-21; not re-discussed)
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

#### Feedback display
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

#### "Hard to catch" line
- **D-06: The cut is a snapshotted score below 50%,** one named constant in Phase 259 score units. Re-checked on
  the new score on 2026-11-22: the caught rate drops clearly only below 0.5 (see Specifics). It is tied to the
  score, never to the arm, and shows together with the chip and the type line when there is one.
- **D-07: Wording as in the seed.** Missed: "This one was hard to catch." Caught: "Well spotted, this one was
  hard to catch."

#### Type line rule
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

#### Settled by measurement (2026-11-22, not discussed further)
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

### Deferred Ideas (OUT OF SCOPE)
- **One-tap "unfair" flag on the feedback** (deferred by the owner, 2026-11-21). Revisit if the caught rate
  tracks the score poorly even on the random sample.
- **A fit on user answers** with per-user terms, once a few thousand answers exist.
- **Review gates or a stop rule for the arm** (declined by the owner).
- **If the drill still looks too hard:** the herring share, the window length or the timing (seed, Evidence).
</user_constraints>

<phase_requirements>
## Phase Requirements

No REQ-IDs are mapped to this phase. The contract is CONTEXT.md D-01 to D-12 plus the "Carried
forward from the seed" list. The planner should map plans to these decision IDs instead; the
Validation Architecture section below gives one automated check per decision.
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Arm coin flip per blunder slot | API / Backend (pure rules, `blunder_check_rules.draw_slot_plan`) | — | The one place a slot is drawn; pure and seed-testable |
| No-cut game probe, scored rows only | Database / Storage (repository SQL) | — | The probe is SQL (`_unserved_qualifying_blunder_exists`); covering index already exists (D-10) |
| Per-slot cut, pool provenance, arm preservation | API / Backend (`blunder_check_selection`, `blunder_check_candidates`) | — | Pure composition logic, no SQL |
| Serve-time snapshot + type-line walk | API / Backend (`_new_window`, new pure feedback module) | Database (new columns) | Needs PGN replay and stored lines; computed once per served window |
| Feedback decision (type line literal, hard-to-catch) | API / Backend (service, solution build) | — | Constants live in one place (backend); client only maps literals to copy |
| Feedback rendering | Browser / Client (`SolutionVerdict`, chip variant) | — | Pure copy and chip; both desktop card and phone strip share `SolutionVerdict` |
| Calibration analysis | Script (`scripts/blunder_check/`) reading DB read-only | — | On-demand operator tool, never in the app |

## Standard Stack

No new libraries. Everything uses the existing stack.

### Core (in use, versions from CLAUDE.md)
| Library | Purpose | Note |
|---------|---------|------|
| SQLAlchemy 2.x async + Alembic | migration and repository queries | migration chains on head `f3a7b9c1e259` [VERIFIED: `uv run alembic heads` this session] |
| python-chess 1.11.x | PGN replay and the quiet walk | already used by `line_material.py` and `build_snapshot` |
| Pydantic v2 | wire schema `BlunderSolution` | discriminated union `WindowSolutionResponse` |
| React 19 + TS, vitest | `SolutionVerdict`, chip variant, copy | hand-maintained types in `frontend/src/types/blunderCheck.ts` (no generator) |

**Installation:** none.

## Package Legitimacy Audit

Not applicable: this phase installs no external packages. **Packages removed:** none. **Flagged:** none.

## Architecture Patterns

### System Architecture Diagram

```
compose_windows(rng)
   |
   v
draw_slot_plan(rng) x count  --> SlotPlan(origin, shape, arm)   [arm: blunder slots only, P(exploration)=EXPLORATION_SHARE]
   |
   v
per origin (own first, then foreign, then own as last resort):
   _fill_from_source  -- round loop --> choose probe for the round:
        exploration blunder slot empty & scored supply left -> probe "scored"  (score IS NOT NULL)
        else main blunder slot empty & cut supply left      -> probe "cut"     (score >= 0.70)
        else herring slot empty                              -> probe "plain"
          |
          v
   repo.pick_*_game_ids(min_score=...)  -> game ids
          |
          v
   _load_batch: load games, positions, ALL scored owner-side blunders (+ score + 5 inputs), served sets
          |  judge_game(min_score=None)  -> candidates carry facepalm_score
          v
   _Pool.batches[game_id] = _Batch(..., probe="scored"|"cut"|"plain", flaws_by_ply)
          |
          v
   _fill_from_pool: (1) exploration slots <- assign_windows(games from non-"cut" batches, min_score=None)
                    (2) main/herring slots <- assign_windows(all games, min_score=FACEPALM_SCORE_MIN)
          |                                      (one window per game across both calls)
          v
   redraws / own->foreign conversion / foreign->own refill: dataclasses.replace(plan, ...) keeps arm
   |
   v
_new_window(item):  snapshot (start_fen, move_ucis)            [existing]
                    arm, arm_probability                        [new]
                    score + 5 inputs from flaws_by_ply[blunder] [new]
                    type-line facts: quiet walk on pv@ply+1 / pv@ply (or best_move)  [new]
   |
   v
insert_session / append_windows -> blunder_check_windows row
   ...
window ends -> GET .../solution -> _blunder_solution: feedback (score, type_line literal, hard_to_catch)
                                    (false alarm / herring: unchanged, no feedback)
   |
   v
frontend solutionCopy -> SolutionVerdict paragraph 1 (points sentence) + paragraph 2 (chip, type line, hard-to-catch)
```

### Recommended file touch list
```
app/services/blunder_check_rules.py        # EXPLORATION_SHARE, SlotArm, SlotPlan.arm, draw_slot_plan, HARD_TO_CATCH_SCORE_MAX, TYPE_LINE_MIN_SWING
app/repositories/blunder_check_repository.py # min_score on probe + picks; load_blunder_flaws (scored, inputs); NewWindow + _window_row
app/services/blunder_check_candidates.py   # candidate carries score; cut moved to option time (min_score kwarg)
app/services/blunder_check_selection.py    # probe choice, batch provenance, arm-aware fill, replace(), _new_window snapshot
app/services/blunder_check_feedback.py     # NEW pure module: type-line facts + feedback decision
app/models/blunder_check.py                # WindowArm IntEnum + columns + CHECKs
alembic/versions/2026xxxx_..._phase_261_blunder_check_exploration_arm.py
app/services/blunder_check_service.py      # BlunderSolutionData.feedback
app/schemas/blunder_check.py               # BlunderFeedback, BlunderSolution.feedback
app/routers/blunder_check.py               # map feedback
frontend/src/types/blunderCheck.ts         # BlunderFeedback type
frontend/src/lib/blunderCheckSolution.ts   # feedback copy in SolutionCopy
frontend/src/components/train/blunder-check/BlunderCheckSolution.tsx  # SolutionVerdict paragraph 2
frontend/src/components/library/Facepalm{Chip,BadgePopover,Explanation}.tsx + lib/facepalm.ts + lib/theme.ts  # neutral variant
scripts/blunder_check/caught_rate.py       # NEW calibration script (name at planner's discretion)
```

### Current code facts the plan depends on

**Slot plan and shares** [VERIFIED: app/services/blunder_check_rules.py:138-140, 157, 176-181, 326-335]:
```python
HERRING_SHARE: float = 1 / 3
OWN_BLUNDER_SHARE: float = 1 / 3
FOREIGN_BLUNDER_SHARE: float = 1 - HERRING_SHARE - OWN_BLUNDER_SHARE
SlotOrigin = Literal["own", "foreign"]
@dataclass(frozen=True)
class SlotPlan:
    origin: SlotOrigin
    shape: WindowShape
def draw_slot_plan(rng: random.Random) -> SlotPlan:
    roll = rng.random()
    if roll < HERRING_SHARE:
        origin: SlotOrigin = "own" if rng.random() < HERRING_OWN_SHARE else "foreign"
        return SlotPlan(origin, draw_herring_shape(rng))
    if roll < HERRING_SHARE + OWN_BLUNDER_SHARE:
        return SlotPlan("own", draw_blunder_shape(rng))
    return SlotPlan("foreign", draw_blunder_shape(rng))
```
Cut and lambda [VERIFIED: blunder_check_rules.py:64, 113]: `FACEPALM_SCORE_MIN: float = 0.7`,
`FACEPALM_DRILL_LAMBDA: float = 1.0`.

**Every place the cut is applied today** [VERIFIED: read this session]:
1. `blunder_check_repository.py:405` inside `_unserved_qualifying_blunder_exists`:
   `facepalm_expr(FACEPALM_DRILL_LAMBDA) >= FACEPALM_SCORE_MIN,` used by `pick_own_game_ids`
   (l.437-446), `pick_foreign_game_ids` (l.488-491), `pick_nearest_foreign_game_ids` (l.539-542),
   each only when `require_facepalm` is true.
2. `blunder_check_repository.py:671` inside `load_blunder_flaws`: `score >= FACEPALM_SCORE_MIN,`.
3. `blunder_check_candidates.py:203`:
   `if flaw.facepalm_score is None or flaw.facepalm_score < FACEPALM_SCORE_MIN:`.
No other file in `app/` reads `FACEPALM_SCORE_MIN` (grep this session; `scripts/backfill_maia_flaws.py`
and `scripts/blunder_check/render.py` read it for reporting only).

**What the loader returns** [VERIFIED: blunder_check_repository.py:631-677]: `BlunderFlawRow(ply,
severity, is_miss, facepalm_score)`. It does NOT return the five inputs. The query selects from
`GameFlaw` joined to `Game` with `player_only_gate(GameFlaw.ply, Game.user_color)`.

**Input column names on `game_flaws`** [VERIFIED: app/models/game_flaw.py:143, 174, 187-189 and
facepalm_score.py:299-307 `_game_flaw_columns`]: `maia_played_prob`, `material_loss`,
`material_missed`, `maia_best_prob`, `maia_best_reply_prob` (all `REAL`, nullable). The covering
index `ix_game_flaws_facepalm_inputs` (game_flaw.py:39) INCLUDEs exactly these plus `ply`, partial on
`severity = 2`.

**Rewrites of a plan that would drop an arm** [VERIFIED: blunder_check_selection.py]:
- l.589 `_redraw_and_refill`: `plans[slot] = SlotPlan(origin, _redraw_shape(shape, rng))`
- l.696 `_refill_from_own`: `plans[slot] = SlotPlan("own", shape)`
- l.710 `_convert_empty_own_to_foreign`: `plans[slot] = SlotPlan("foreign", plans[slot].shape)`
All three must become `dataclasses.replace(plan, ...)`.

**What `_new_window` has** [VERIFIED: blunder_check_selection.py:288-296, 729-754, 601-628]:
`batch.game.pgn`, `batch.positions` (contiguous by ply, columns `ply, eval_cp, eval_mate, move_san,
best_move, pv, phase`), `pick.blunder_ply`, `pick.case`, `pick.shape`, `batch.is_own`. It does not
have the flaw row (score, inputs): add `flaws_by_ply` to `_Batch` (already loaded in `_load_batch`).

**Window model values** [VERIFIED: app/models/blunder_check.py:53-68, 148, 157]:
`HERRING = 0`, `ALLOWED = 1`, `PURE_MISS = 2`, `MIXED = 3`; `CLEARED = 0`, `CAUGHT = 1`,
`MISSED = 2`, `FALSE_ALARM = 3`; `"window_case IN (0, 1, 2, 3)"`, `"outcome IS NULL OR outcome IN (0, 1, 2, 3)"`.

### Pattern 1: Arm on the slot plan (default "main")

**What:** `SlotArm = Literal["main", "exploration"]`, `SlotPlan.arm: SlotArm = "main"` (third field with
a default, so the many tests that build `SlotPlan("own", shape)` positionally keep compiling and stay
main-arm). `EXPLORATION_SHARE: float = 0.2`. `draw_slot_plan` draws `rng.random() < EXPLORATION_SHARE`
only on the two blunder branches.

```python
# Sketch (names are proposals)
SlotArm = Literal["main", "exploration"]
EXPLORATION_SHARE: float = 0.2

def draw_slot_arm(rng: random.Random) -> SlotArm:
    return "exploration" if rng.random() < EXPLORATION_SHARE else "main"

# in draw_slot_plan, blunder branches:
    return SlotPlan("own", draw_blunder_shape(rng), draw_slot_arm(rng))
```
Note: this extra `rng.random()` shifts the RNG stream for `draw_slot_plan` callers.
`scripts/blunder_check/spot_check.py:273` also calls `draw_slot_plan(bucket_rng)`; its tests
(`tests/scripts/test_blunder_check_calibration.py` ~1473-1561) assert properties and same-seed
equality, not fixed picks [VERIFIED: grep], so a stream shift is expected to be harmless. Run them.

**Sampling probability column:** store `P(arm)`: `EXPLORATION_SHARE` for exploration windows,
`1 - EXPLORATION_SHARE` for main windows. This records the share in force at serve time, so a later
constants change stays analyzable (inverse-probability weights if ever needed).

### Pattern 2: Probe choice and batch provenance (the core of the draw)

- Repository: `_unserved_qualifying_blunder_exists(..., min_score: float | None = FACEPALM_SCORE_MIN)`.
  `None` replaces the cut predicate with `facepalm_expr(FACEPALM_DRILL_LAMBDA).isnot(None)` (scored rows
  only). Thread `min_score` through the three `pick_*` functions as a keyword with the cut as default
  (the 9 existing `require_facepalm=True` test calls keep their meaning).
- Selection: a private `Probe = Literal["plain", "cut", "scored"]`; `_PickFn` / `_NearestPickFn`
  take the probe instead of the bool. `_Batch` gets `probe: Probe`.
- `_fill_from_source` keeps two exhaustion flags. Round rule: an empty exploration blunder slot with
  scored supply left -> "scored"; else an empty main blunder slot with cut supply left -> "cut"; else
  an empty herring slot -> "plain"; else stop. An empty "scored" pick also exhausts "cut" (the cut set
  is a subset). An empty "cut" pick exhausts only main.
- `_load_nearest_foreign`: same choice ("scored" if any empty exploration blunder slot, else "cut" if
  any empty main blunder slot, else "plain").
- `_Pool.candidates(reach, *, for_exploration: bool)` excludes `probe == "cut"` batches for exploration.
  "plain" batches are statistically safe for exploration (a uniform game sample restricted to games
  with a judge-eligible blunder is the same distribution as the "scored" probe's), but they occur only
  after scored supply is exhausted, so excluding only "cut" is enough.

### Pattern 3: Cut at option time, not in the judge

- `load_blunder_flaws` loads every scored owner-side blunder (`score.isnot(None)` instead of
  `score >= FACEPALM_SCORE_MIN`) plus the five inputs (`BlunderFlawRow` grows five fields; the
  `FlawLike` protocol is unchanged).
- `BlunderCandidate` gets `facepalm_score: float`. `_blunder_candidate` / `judge_game` take
  `min_score: float | None = FACEPALM_SCORE_MIN`; selection passes `None` so candidates carry their
  score; existing direct callers (tests) keep the cut by default. A NULL score still never qualifies.
- `assign_windows(..., min_score: float | None = FACEPALM_SCORE_MIN)`; `_blunder_options` filters
  `candidate.facepalm_score >= min_score` when `min_score` is not None.
- `_fill_from_pool` runs two `assign_windows` calls per fill, exploration slots first (non-cut games,
  `min_score=None`), then the remaining slots of that origin (all games, cut), threading the used game
  ids. Filling exploration first keeps its sample from being thinned by main picks of high-score games.
- `_Filled` gets `arm` (from `plans[slot].arm`) so `_new_window` can write it.

### Pattern 4: Type-line facts (pure, new module)

```python
# app/services/blunder_check_feedback.py (sketch; names are proposals)
# Sources: app/services/line_material.py, facepalm_material.py, facepalm_score.py (read this session)
@dataclass(frozen=True)
class TypeLineFacts:
    swing: int | None   # value at the deepest settled odd depth on the type side, None if none settled
    mate: bool          # allowed side: played line mates the blunderer; missed side: best line mates the opponent

def type_line_facts(pre_board, played_uci, refutation_pv, best_pv_or_move, facepalm_type) -> TypeLineFacts:
    played = quiet_line_facts(pre_board, played_uci, refutation_pv)
    if facepalm_type == "allowed_loss":
        series = loss_by_depth(played.material_array(), played.mate_ply, loss_floor=FACEPALM_LOSS_FLOOR)
        return TypeLineFacts(_deepest(series), played.mate_ply is not None)
    best = quiet_best_line_facts(pre_board, best_pv_or_move)
    series = gain_by_depth(played.material_array(), best.material_array(), best.opponent_mate_ply,
                           missed_floor=FACEPALM_MISSED_FLOOR, missed_cap=FACEPALM_MISSED_CAP,
                           missed_mate=FACEPALM_MISSED_MATE)
    return TypeLineFacts(_deepest(series), best.opponent_mate_ply is not None)

def _deepest(series: MaterialSeries) -> int | None:
    known = [v for v in series if v is not None]
    return None if not known else round(known[-1])
```
Values used [VERIFIED: blunder_check_rules.py:98, 102-104; line_material.py:49]:
`FACEPALM_LOSS_FLOOR: int | None = 0`, `FACEPALM_MISSED_FLOOR: int | None = 0`,
`FACEPALM_MISSED_CAP: int = 5`, `FACEPALM_MISSED_MATE: int = 5`,
`LINE_LOSS_DEPTHS: tuple[int, ...] = (1, 3, 5, 7, 9)`.

Decision (at solution time, constants in `blunder_check_rules`): mate -> `"allowed_mate"` /
`"missed_mate"`; else `swing >= TYPE_LINE_MIN_SWING` (2) -> `"allowed_material"` / `"missed_material"`;
else None. Type side from `facepalm_type_of(snapshot_loss, snapshot_missed)` (facepalm_score.py:323-332:
`"allowed_loss" if loss > 0 and loss >= missed else "missed_win"`). `hard_to_catch = score < HARD_TO_CATCH_SCORE_MAX` (0.5).
Because the chip floors (`toFacepalmPct`: `Math.floor(score * 100)`), `score < 0.5` is exactly "chip shows 49% or less".

Inputs at `_new_window` (same convention as the write hook, maia_flaw_scoring.py:541-542 and 280-295):
pre-board = PGN mainline after `moves[:blunder_ply]`; `played_uci = moves[blunder_ply].uci()`;
`refutation_pv = positions[blunder_ply + 1].pv` (guard the index, as `_refutation_uci` does);
best line = `positions[blunder_ply].pv or positions[blunder_ply].best_move`.

**D-08 / D-09 mapping onto existing returns (gap check):**
- Settledness is monotone: `_quiet_loss` returns None only when `len(steps) < depth and not mated and
  not ends_in_exchange` (line_material.py:250), so once a depth is None every deeper depth is None. A
  line that ends inside an exchange settles every depth (SEE). "Last non-None element" is therefore
  exactly "deepest odd depth the stored line still covers". No gap.
- Missed side: `gain_by_depth` is None at a depth unless BOTH lines settle it, so the missed swing's
  deepest depth is bounded by the shorter of the two lines. This is the reused 259 rule, but the
  planner should know it (an owner-visible nuance, not a bug).
- `loss_by_depth` / `gain_by_depth` cap at 5 (`LOSS_CAP` / `FACEPALM_MISSED_CAP`) and floor at 0. The
  2-point decision is unaffected (2 < 5); a stored swing of 5 means "5 or more".
- Mate (D-09): `LineFacts.mate_ply` (played line, blunderer mated) and `LineFacts.opponent_mate_ply`
  (best line, opponent mated; 0 when the best move itself mates). Both exist. No gap.
- D-12: best_move only (no pv) gives a one-token best line; `quiet_best_line_facts` returns all-None
  unless that move mates, so no "misses a material win" line. Matches D-12.
- The stored `game_flaws.line_mate_ply` / `best_line_mate_ply` columns still exist (game_flaw.py:159,
  173) but the seed says not to depend on them; the fresh walk is the source.

### Pattern 5: Snapshot columns (migration)

Proposal (all nullable; existing rows stay NULL; ADD COLUMN without default is catalog-only):

| Column | Type | Meaning |
|---|---|---|
| `selection_arm` | SMALLINT | `WindowArm` IntEnum: `MAIN = 0`, `EXPLORATION = 1`; NULL for herrings and legacy |
| `arm_probability` | REAL | P(arm) at serve time (0.8 / 0.2) |
| `facepalm_score` | REAL | drill score at serve time (`facepalm_expr(FACEPALM_DRILL_LAMBDA)`) |
| `facepalm_played_prob` | REAL | `maia_played_prob` |
| `facepalm_loss` | REAL | `material_loss` |
| `facepalm_missed` | REAL | `material_missed` |
| `facepalm_best_prob` | REAL | `maia_best_prob` (may be NULL on a scored losing row) |
| `facepalm_reply_prob` | REAL | `maia_best_reply_prob` (may be NULL on a scored row that loses nothing) |
| `type_swing` | SMALLINT | deepest-settled swing on the type side, 0..5, NULL when no depth settled |
| `type_mate` | BOOLEAN | mate on the type side within the stored line |

CHECKs (literal values in the migration, never imported constants, like `f3a7b9c1e259`):
- `selection_arm IS NULL OR selection_arm IN (0, 1)`
- `(selection_arm IS NULL) = (arm_probability IS NULL)` and `arm_probability > 0 AND arm_probability <= 1` (NULL passes)
- `(selection_arm IS NULL) = (facepalm_score IS NULL)` (both arms snapshot; legacy and herrings carry none)
- `window_case <> 0 OR selection_arm IS NULL` (a herring never carries an arm)
- `(facepalm_score IS NULL) = (type_mate IS NULL)`; `facepalm_score IS NULL OR facepalm_score BETWEEN 0 AND 1`
- `(facepalm_score IS NULL) OR (facepalm_played_prob IS NOT NULL AND facepalm_loss IS NOT NULL AND facepalm_missed IS NOT NULL)`
- `type_swing IS NULL OR type_swing >= 0`

The table is small (hundreds of windows a day since 2026-11-19), so validating CHECKs on ADD is fine;
NOT VALID is not needed [ASSUMED: row count not queried this session].

Swing + mate (as the seed says) rather than a frozen enum: the 2-point floor stays a constant applied
at read time, and the raw swing is usable in analysis. The type side is re-derived from the snapshotted
loss / missed with the lambda-free, coefficient-free 257 D-02 rule (stable). If the owner prefers a frozen
decision, a `type_line SMALLINT` enum is the alternative; the wire contract is the same.

`NewWindow` gets the new fields with `None` defaults (existing test constructions keep working);
`_window_row` maps them.

### Pattern 6: Wire and frontend

- Schema: `BlunderTypeLineWire = Literal["allowed_material", "allowed_mate", "missed_material", "missed_mate"]`;
  `class BlunderFeedback(BaseModel): score: float; type_line: BlunderTypeLineWire | None; hard_to_catch: bool`;
  `BlunderSolution.feedback: BlunderFeedback | None` (None for legacy windows). `FalseAlarmSolution`,
  `HerringSolution` unchanged (D-05). The arm is never on the wire (no user-visible marker, D-04).
- Service: `BlunderSolutionData.feedback` built in `_blunder_solution` (service l.1125-1160) when
  `window.facepalm_score is not None`; router `_blunder_solution_schema` (router l.398-419) maps it.
- Frontend types are hand-written (`frontend/src/types/blunderCheck.ts:167-190`), no generator
  (`frontend/src/generated/` holds four unrelated files) [VERIFIED: ls].
- Copy: extend `SolutionCopy` with `feedback: { score: number; lines: string[] } | null`, built in
  `blunderCopy` (blunderCheckSolution.ts:216-239); herring and false-alarm copies return `feedback: null`.
  `SolutionVerdict` (BlunderCheckSolution.tsx:232-254) renders a second `<p>` after the summary: chip,
  type line, hard-to-catch line. `SolutionVerdict` is used by both the desktop `TrainVerdictCard` and
  the phone/tablet `TrainVerdictStrip` (l.372-386), so one change covers D-03 on all layouts.
- Chip (D-01 + D-02 gap): `FacepalmChip` requires `type`, `gameId: number`, `ply`; it tints by type and
  its popover names the type (`FacepalmExplanation` renders `FACEPALM_TYPE_LABEL[type]` and the
  aria-label includes the type). Needed: a neutral variant: `type?: FacepalmType` (absent -> neutral
  tint, no type line in the popover, aria-label without type), an explicit `testId` (drill:
  `blunder-check-facepalm-badge`, a fixed literal; `gameId` can be NULL in the drill), and a neutral
  score-meaning sentence. `facepalmScoreMeaning(byOpponent)` needs a third audience; proposed copy
  "...should have been easy to see for a player at that level, a low one that it was probably hard to
  see" [ASSUMED: copy wording, owner to confirm]. Neutral tint: add an exported token to `theme.ts`
  (`FAM_NEUTRAL` / `FAM_NEUTRAL_BG` exist at theme.ts:183-184 but are not exported).

### Anti-Patterns to Avoid
- **Building a new `SlotPlan(origin, shape)` anywhere in selection:** drops the arm silently to "main". Use `dataclasses.replace`.
- **Letting exploration slots draw from cut-probe batches:** biases the "plain sample" by the current score.
- **Filtering exploration by score anywhere** (band draws, ordering, "random below 0.7"): rejected by the owner.
- **Sending the arm or any pre-end score:** pre-end payloads must stay as in the D-16 wire contract.
- **Reading the live `game_flaws` score at solution time for new windows:** shows refit-dependent values and fails for deleted foreign games; read the snapshot.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Material walk / mate detection | a second material rule | `quiet_line_facts`, `quiet_best_line_facts`, `loss_by_depth`, `gain_by_depth` | D-08 forbids a second rule; desperado and SEE edge cases already handled |
| Score at serve time | Python recompute | the `facepalm_score` column `load_blunder_flaws` already selects (`facepalm_expr`) | the same bound expression selected the row |
| Type side | `window_case` | `facepalm_type_of(loss, missed)` | seed: one classification |
| Confidence intervals | own formula | `app/services/score_confidence.py` `wilson_bounds(p, n, z=CI_Z_95)` | project standard |
| Read-only DB in the script | raw engine | `scripts/blunder_check/sample.py` `make_readonly_engine(db_url_for_target(args.db))` | read-only transactions + statement timeout, URL never logged |
| PGN replay | new parser | `blunder_check_selection._mainline` | already handles parse failures |

## Common Pitfalls

### Pitfall 1: Arm lost on a plan rewrite
**What goes wrong:** exploration slots that convert own->foreign, get a redrawn shape, or fall back
foreign->own become main slots; the served share drops below 20% with no error.
**How to avoid:** `dataclasses.replace` in all three rewrite sites; test each path with a forced
exploration plan and assert the served window's arm.

### Pitfall 2: Exploration sample biased by pool sharing
**What goes wrong:** the first own round uses the cut probe (main slot empty), the batch is kept, and
an exploration slot later draws from it.
**How to avoid:** batch provenance and the exploration-first, "scored"-first round order (Pattern 2);
a unit test of `_Pool.candidates(for_exploration=True)` that excludes a "cut" batch.

### Pitfall 3: Score cut still applied in the judge or loader
**What goes wrong:** removing the SQL predicate but keeping the `_blunder_candidate` re-check (or the
reverse) silently makes exploration a main-arm copy.
**How to avoid:** composition test seeding only a below-cut scored blunder: a forced exploration slot
serves it, a forced main slot never does.

### Pitfall 4: Unscored rows leaking into exploration
**What goes wrong:** dropping the cut predicate entirely (instead of `IS NOT NULL`) serves rows with no
inputs, which cannot be snapshotted and break the `(selection_arm IS NULL) = (facepalm_score IS NULL)` CHECK
at insert (an IntegrityError that is not the open-session race and is re-raised by `insert_session`).
**How to avoid:** `isnot(None)` in both the probe and the loader; the candidate keeps `None -> not a candidate`.

### Pitfall 5: Existing tests become flaky through the random arm
**What goes wrong:** tests that compose with the real `draw_slot_plan` and seed below-cut blunders may
now randomly serve them. Most selection, router and cooldown tests patch `draw_slot_plan` to
`SlotPlan("own", shape)` (main by default) [VERIFIED: grep of tests], but every composing test that
does not patch must be checked.
**How to avoid:** grep for `compose_windows` / session-start tests without a `draw_slot_plan` patch;
pin `EXPLORATION_SHARE` to 0 (monkeypatch) where a test asserts the cut.

### Pitfall 6: Eval lottery / foreign-pick isolation
**What goes wrong:** seeded non-guest fully evaluated games leak into other tests' foreign picks and the
tier-3 lottery.
**How to avoid:** `tests/blunder_check_seed.py` contract: every seeded game deleted in `finally`
(`delete_games`), sessions via `delete_blunder_check_sessions`. Foreign tests set
`FOREIGN_SAMPLE_PERCENT` to 100.

### Pitfall 7: Frontend fixtures and the build
**What goes wrong:** adding a required `feedback` field to `BlunderSolution` breaks every TS fixture
(`blunderCheckSolution.test.ts`, `BlunderCheckSolution.test.tsx`, `BlunderCheckTab.test.tsx`,
`blunderCheckDrill.test.ts`); `npm run lint` and `npm test` do not type-check.
**How to avoid:** add `feedback: null` to fixtures; run `npm run build`; knip for the new exports.

### Pitfall 8: Leaking the case of an unreached blunder
**What goes wrong:** putting feedback into `FalseAlarmSolution` reveals the blunder (249 D-10, D-05).
**How to avoid:** feedback only on `BlunderSolution`; a router test that a false-alarm solution of a
low-score window has no `feedback` key.

### Pitfall 9: Foreign probe plan on prod
**What goes wrong:** the foreign TABLESAMPLE pick without the cut could plan differently.
**How to avoid:** D-10 checkpoint: the orchestrator runs EXPLAIN (ANALYZE, BUFFERS) of the
"scored" foreign and nearest picks on prod before release (subagents have no prod MCP).

### Pitfall 10: Nesting-depth gate on the reworked round loop
**What goes wrong:** `_fill_from_source` with two exhaustion flags and three probes easily exceeds depth 4.
**How to avoid:** a small pure `_next_probe(empty_plans, exhausted) -> Probe | None` helper.

## Code Examples

### No-cut probe predicate
```python
# Source: app/repositories/blunder_check_repository.py:403-409 (current), adapted
score = facepalm_expr(FACEPALM_DRILL_LAMBDA)
score_condition = score.isnot(None) if min_score is None else score >= min_score
conditions: list[ColumnElement[bool]] = [
    GameFlaw.game_id == game_id_col,
    score_condition,
    player_only_gate(GameFlaw.ply, user_color_col),
    not_(already_served),
]
```

### Calibration script skeleton
```python
# Pattern from scripts/blunder_check/facepalm_features.py:360, 664, 701 and sample.py:110-118
DB_TARGETS: tuple[str, ...] = ("dev", "prod")
engine = make_readonly_engine(db_url_for_target(args.db))
# Ended blunder windows: window_case <> 0 AND outcome IS NOT NULL.
# reached = outcome IN (CAUGHT=1, MISSED=2); false alarm before the blunder = outcome FALSE_ALARM (3).
# Score: COALESCE(w.facepalm_score, live facepalm_expr(FACEPALM_DRILL_LAMBDA)) via LEFT JOIN game_flaws
#   ON game_id = w.game_id AND ply = w.blunder_ply (legacy windows; NULL when the game is gone).
# Group: arm in {exploration, main, legacy} x is_own x band; caught/reached with wilson_bounds.
```
Bands as in CONTEXT Specifics: below 0.3, 0.3-0.5, 0.5-0.6, 0.6-0.7, 0.7-0.8, 0.8-0.9, 0.9-1.0 (named
constant tuple). Put the aggregation in a pure function so `tests/scripts/` can test it without a DB.
Prod runs via `bin/prod_db_tunnel.sh` with one connection (prod `max_connections` is 50).

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| 0.50 drill cut, old score | 0.70 cut on the Phase 259 first-principles score | Phase 259, live (#498, #499; schema `f3a7b9c1e259`) | windows since then are main-arm-like but carry no arm (legacy) |
| Score read live | Score snapshotted per window | this phase | refit-stable feedback and analysis |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `blunder_check_windows` is small enough to validate new CHECKs on ADD without NOT VALID | Pattern 5 | a long lock at deploy; check the prod row count first |
| A2 | Neutral score-meaning copy "for a player at that level" | Pattern 6 | owner copy preference; low risk |
| A3 | The drill chip should use a neutral tint (not the type tint) | Pattern 6 | if the owner wants the library tint, the type would show through color, against D-02's intent |
| A4 | Spot-check script tests do not pin exact seeded picks, so the extra RNG draw is harmless | Pattern 1 | a few script tests may need re-seeding |
| A5 | The served exploration share lands slightly above 20% (exploration slots fill more easily) | Validation | acceptance tolerance needs to allow it |

## Open Questions

1. **Chip tint in the drill.** D-01 says the library chip, D-02 says the popover does not name the type.
   The library chip is tinted by type and the popover is the only place that explains the tint.
   Recommendation: neutral tint in the drill (A3); confirm with the owner at plan review.
2. **Swing + mate vs a frozen type-line enum.** Recommendation: swing + mate per the seed (Pattern 5).
3. **"Facepalm blunder: 70% or more" line in the drill popover.** It is score-only (allowed by D-02), but it
   names a library concept. Recommendation: keep it for one look across the app.
4. **Served share tolerance.** See Validation; recommendation: accept when the Wilson 95% interval of
   exploration / ended blunder windows over the first 500+ windows contains a value in [0.18, 0.26].

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| uv | backend tests, migration | ✓ | 0.10.9 | — |
| Node | frontend build/tests | ✓ | v24.19.0 | — |
| Dev Postgres (docker `flawchess-dev-db-1`) | pytest, alembic | ✓ (running) | 18 | — |
| Prod read access (tunnel) | D-10 EXPLAIN, post-release share count, calibration run | orchestrator only | — | owner/orchestrator runs it; subagents lack prod MCP |

**Missing with no fallback:** none.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (+ pytest-asyncio, xdist) backend; vitest frontend |
| Config file | `pyproject.toml`, `tests/conftest.py`; `frontend/vite.config.*` |
| Quick run command | `uv run pytest tests/services/test_blunder_check_rules.py tests/services/test_blunder_check_candidates.py tests/services/test_blunder_check_selection.py -x` |
| Full suite command | `uv run pytest -n auto -x` and `( cd frontend && npm run lint && npm run build && npm test -- --run && npm run knip )` |

### Decision -> Test Map
| Decision | Behavior | Test Type | Automated Command | File Exists? |
|----------|----------|-----------|-------------------|-------------|
| Share (seed) | seeded `draw_slot_plan`: exploration share among blunder slots == `EXPLORATION_SHARE` within 0.02 (n=30000 draws, ~20000 blunder slots, SE ~0.003); herring slots never exploration; own and foreign both ~20% | unit | `pytest tests/services/test_blunder_check_rules.py -k slot` | ✅ extend `TestSlotShares` |
| Draw (seed) | forced exploration slot serves a below-cut scored blunder; forced main slot never does; unscored blunder never served by either | integration (DB) | `pytest tests/services/test_blunder_check_selection.py -k exploration` | ❌ new tests |
| Draw (seed) | exploration slot never fills from a "cut" batch (`_Pool.candidates(for_exploration=True)`) | unit | same file | ❌ |
| Draw (seed) | arm survives own->foreign conversion, redraw and foreign->own refill | integration | same file | ❌ |
| Draw (seed) | probe without cut returns games with only below-cut scored blunders, still excludes served, opponent-side and unscored | integration | `pytest tests/repositories/test_blunder_check_repository.py -k scored` | ❌ |
| Main arm 0.70 | existing cut tests unchanged and green | regression | `pytest tests/repositories/test_blunder_check_repository.py tests/services/test_blunder_check_candidates.py` | ✅ |
| Counts as normal | exploration window's points enter session points / leaderboard (no arm filter in `train_leaderboard_repository`, `train_repository`) | integration | `pytest tests/routers/test_blunder_check_drill.py tests/services/test_train_leaderboard.py` | ✅ (add one exploration case) |
| Snapshot | composed window carries arm, arm_probability, score equal to the loader score, the five inputs; herring carries none | integration | selection tests | ❌ |
| Migration | upgrade/downgrade; CHECKs reject herring with arm, arm without score | integration | `uv run alembic upgrade head` + a repository test inserting a bad row expecting IntegrityError | ❌ |
| D-08 | fixture 13 (`expected_quiet_loss=(3, 0, 0, 0, 0)`) -> swing 0, no line; fixture 154 (`(1, 1, 2, 4, 6)`) -> swing 5 (capped), line; short line -> deepest settled depth used | unit | `pytest tests/services/test_blunder_check_feedback.py` | ❌ new (reuse `tests/services/line_material_fixtures.py`) |
| D-09 | played line mating the blunderer -> allowed_mate; best line mating -> missed_mate; mate beats material | unit | same | ❌ |
| D-12 | best_move only (no pv), non-mating -> no missed line | unit | same | ❌ |
| D-06/D-07 | score 0.4999 -> hard_to_catch; 0.5 -> not; copy differs caught vs missed | unit (backend + vitest) | same + `npm test -- blunderCheckSolution` | ❌ |
| D-04 | solution of a window with snapshot has `feedback`; legacy window (NULL snapshot) has `feedback: null` | router | `pytest tests/routers/test_blunder_check_solution.py` | ✅ extend |
| D-05 | false-alarm solution has no feedback key even for a low-score window | router | same | ✅ extend |
| D-01/D-02 | drill chip renders the snapshotted %, popover has no type label and no "your"/"their" | component | `npm test -- BlunderCheckSolution` | ✅ extend |
| D-03 | second paragraph after the summary in card and strip | component | same | ✅ extend |
| Calibration script | pure aggregation: bands, Wilson bounds, reached denominator, false alarms beside, legacy fallback | unit | `pytest tests/scripts/test_<script>.py` | ❌ |
| D-10 | EXPLAIN of the scored foreign / nearest pick on prod | manual (orchestrator) | — | checkpoint |
| Share acceptance (prod) | served exploration / ended blunder windows after release | manual (orchestrator) | SQL count after ~1 week | checkpoint |

### Sampling Rate
- **Per task commit:** the quick run command plus the touched test file.
- **Per wave merge:** `uv run pytest -n auto -x` and the frontend block.
- **Phase gate:** the full pre-merge gate from CLAUDE.md, green before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] `tests/services/test_blunder_check_feedback.py` (D-06 to D-09, D-12)
- [ ] `tests/scripts/test_<calibration script>.py`
- [ ] seed helper: `seed_judged_game` cannot set `pv` today; add an optional per-ply pv map if a DB-level type-line test is wanted (the quiet SEED_PGN gives swing 0 otherwise)

## Security Domain

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | unchanged (FastAPI-Users) |
| V3 Session Management | no | unchanged |
| V4 Access Control | yes | solution read stays scoped by `user_id` from the auth dependency (`get_window_for_user`, IDOR guard) |
| V5 Input Validation | no new input | no new request fields |
| V6 Cryptography | no | — |

### Known Threat Patterns
| Pattern | STRIDE | Mitigation |
|---------|--------|------------|
| Pre-answer leak of difficulty or arm (user infers a low-score blunder exists) | Information disclosure | feedback only in the post-end solution; no arm on any payload; no new field on `WindowStartResponse` / `AnswerResponse` / `WindowProgress` (D-16 wire contract) |
| Unreached blunder revealed via feedback | Information disclosure | no feedback on `FalseAlarmSolution` (D-05) |
| Foreign owner identification | Information disclosure | snapshot carries only scalars, no owner ids; copy neutral |
| Analysis script writes to prod | Tampering | `make_readonly_engine` (read-only transactions, statement timeout) |

## Sources

### Primary (HIGH confidence, read this session)
- `app/services/blunder_check_rules.py`, `blunder_check_selection.py`, `blunder_check_candidates.py`
- `app/repositories/blunder_check_repository.py`
- `app/services/line_material.py`, `facepalm_material.py`, `facepalm_inputs.py`, `facepalm_score.py`, `maia_flaw_scoring.py` (l.280-335, 480-550)
- `app/models/blunder_check.py`, `app/models/game_flaw.py`
- `app/schemas/blunder_check.py`, `app/services/blunder_check_service.py` (l.200-340, 1025-1227), `app/routers/blunder_check.py` (l.385-445)
- `frontend/src/lib/blunderCheckSolution.ts`, `facepalm.ts`, `components/train/blunder-check/BlunderCheckSolution.tsx`, `components/library/Facepalm{Chip,BadgePopover,Explanation}.tsx`, `types/blunderCheck.ts`
- `tests/services/test_blunder_check_rules.py`, `test_blunder_check_selection.py`, `tests/blunder_check_seed.py`, `tests/facepalm_seed.py`, `tests/services/line_material_fixtures.py`
- `scripts/blunder_check/sample.py`, `spot_check.py`, `facepalm_features.py`, `app/core/config.py` (`db_url_for_target`), `app/services/score_confidence.py` (`wilson_bounds`)
- `uv run alembic heads` -> `f3a7b9c1e259 (head)`; `.planning/STATE.md` (Phase 259 releases live, schema `f3a7b9c1e259`)

### Secondary / Tertiary
- none (no web research needed)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH (no new dependencies)
- Architecture: HIGH (all seams read; the pool-provenance design is reasoning on verified code)
- Pitfalls: HIGH for code-level ones; MEDIUM for prod plan behavior (D-10 checkpoint)

**Research date:** 2026-11-22
**Valid until:** 2026-12-22 (or until the selection code changes)
