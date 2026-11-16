# Phase 256: Facepalm Refit on Material Aggregated over Depths - Research

**Researched:** 2026-11-16
**Domain:** In-repo Python (pure score twins, SQLAlchemy 2.x expression over PostgreSQL arrays, numpy logistic fit script), operator runs against prod
**Confidence:** HIGH for the code map and constraints (every file read this session); MEDIUM for the two definitions the probe did not record (first-stable onset discount and fallback)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Carried forward (not re-discussed)
- The score is a query-time expression over stored facts; a refit is a constants deploy with no UPDATE pass over
  prod (254 D-01). The Python and SQL twins stay in parity.
- The score is a ranking, never presented as a probability (250 D-01). False alarms are worse than misses
  (250 D-03). User-side blunders only, no engine at scoring time (250 D-06, D-07).
- Fitted values are named constants in `app/services/blunder_check_rules.py`; `--check-constants` reproduces them
  from a committed features TSV (250 D-04). Fit choices are made by the fit script and confirmed by the owner,
  never hand-tuned.
- Label 1 means "the facepalm score should be above 70%" (254 D-23). One label file,
  `reports/blunder-check/facepalm-labels.tsv` (254 D-22).
- `FACEPALM_SCORE_MIN` is set by the owner at a blocking checkpoint (254 D-13). The report shows fair / unfair
  among passers at cuts from about 50% to 70%, split by loss-type and miss-type, and the drill pool size.
- An unknown best line contributes `missed = 0`; the row keeps its loss-only score (254 D-18).
- Owner's goal (seed, 2026-11-16): a meaningful score. How many pure misses pass the drill cut is secondary.
- Fixed by the seed, not fitted: the decay ratio is 1/2; the aggregate reads only the odd depths 1, 3, 5, 7, 9
  (even slots are mid-exchange values, 254 D-17); weights are normalised over the known depths.
- Drill and library lambda stay 1.0 (254 D-03, D-04).

#### Timing and coverage
- **D-01: The refit runs when label set 8 is labelled.** The labels are the only gate (60 rows, n 241 to 300,
  0 labelled on 2026-11-16). The plan needs a first precondition step that stops when set 8 has unlabelled rows.
- **D-02: The phase does not wait for Phase 252.** Features are pulled from prod as the lines are at that time. If
  252's repair and the gap-fill line pass (254 D-21) are done by then, they are used; otherwise NULL slots are
  skipped. No planned re-run after 252.
- **D-03: Depth 3 is still required for a row to be scored.** The coverage rule is unchanged: a row whose played
  line does not reach depth 3 (and has no mate that settles it) stays unscored. The aggregate adds depths 5, 7, 9
  where they exist. Coverage grows through 252's repair, not through this phase. (Depth 1 alone is the position
  right after the blunderer's own move and can rarely show a loss.)

#### Unknown best-move probability (254 WR-01)
- **D-04: A no-loss row with a NULL `maia_best_prob` is unscored.** Under the `best_prob_for_misses` spread form,
  both twins return None / NULL when the row's loss is not above the gate and the best-move probability is NULL,
  as a NULL spread already does under `always`. Rows that lose material are unaffected. Those rows leave the drill
  pool and the library Facepalm filter and show no chip. Prod size 2026-11-16: 14,826 of 2,178,931 rows with
  scoring inputs (0.68%) have a NULL best prob, 14,592 of them also lack a best line.
- **D-05: The fit follows the same rule.** A label row that the shipped model would leave unscored under D-04 is
  excluded from the fit under that spread form, and the report counts such rows.

#### Selection rule
- **D-06: Three candidates, the same input for the loss and the missed gain.** (a) decaying mean, (b) first stable
  value (the same balance at two odd depths in a row), discounted by its onset, (c) depth 3 as the reference. No
  mixed candidates (for example loss at depth 3 with the missed gain as a mean) and no single-depth candidates
  other than depth 3.
- **D-07: The choice is made by repeated cross-validation over sets 1 to 8,** on seed means, with the script's
  existing criteria (cross-validated AUC, then the fair share at the selection threshold), as Phase 254 did for
  the forms.
- **D-08: Set 8 is also a hold-out check.** Each candidate is additionally fitted on sets 1 to 7 and scored on set
  8 untouched; the report shows both results per candidate. Reason: the decaying mean was picked as the best of
  about 11 candidates on sets 1 to 7, and set 8 is the only fresh data, drawn where the candidates differ. If the
  cross-validated choice and the set 8 hold-out disagree, the owner decides at the D-13 checkpoint.
- **D-09: The decaying mean wins ties against depth 3** (within `AUC_TIE_TOLERANCE` and
  `FAIR_SHARE_TIE_TOLERANCE`). Depth 3 stays only if it is clearly better. Reason: the owner finds a single depth
  unintuitive, and the mean gives misses a real material coefficient (0.15 to 0.39 in the seed's probe).
- **D-10: Final constants are fitted on all eight sets.**

#### Defaults for the areas not discussed (owner: use the seed and Phase 254)
- **D-11: The "loses material" gate is decided by the fit.** Under a mean, `loss > 0` flips on any small late loss
  and switches the spread term between the loss form and the best-move-probability form. The fit compares a gate
  threshold of 1 against no gate (`loss > 0`) with the D-07 criteria; the report states the choice. The gate is one
  named constant used by both twins and by the fit.
- **D-12: WR-03 is fixed in the fit script.** The exclusion becomes spread-form aware: a NULL `reply_spread` row
  stays in the fit when the candidate's spread form is gated and the row's loss is not above the gate. The report
  counts the rows that qualify only under a gated form.
- **D-13: One blocking owner checkpoint** after the fit report: the owner confirms the chosen input (and settles a
  D-08 disagreement) and sets `FACEPALM_SCORE_MIN`. The report lists, as information and not as automatic gates:
  the two owner fixtures (games 817357 ply 24 and 820181 ply 65), the 15 commented set 7 rows with their expected
  range and old and new scores, window 14 (game 2099808 ply 23, must still fall below the cut), and the pure-miss
  pass rate at each cut.
- **D-14: The material-form, spread-form and optional-input stages of the fit are re-run** on the new input, as
  the 254 fit ran them; the shipped shape ("split", `best_prob_for_misses`) is not assumed.
- **D-15: Release as a normal constants and code release** with a changelog bullet. Scores change for every user
  (library chip, Facepalm filter, drill pool); no migration, no backfill.

### Claude's Discretion
- How a mate enters the aggregate (for example the mate value from the mate ply onward). A mate within depth 3
  must keep scoring as today's `MATE_LOSS` / `FACEPALM_MISSED_MATE` case, not as "nothing lost or missed".
- The per-depth floor and cap of the gain series (`decaying_mean.py` floors the per-depth gain at 0; the shipped
  `FACEPALM_MISSED_FLOOR` is None), decided by the fit.
- How the SQL twin expresses the aggregate over the 9-slot arrays, and whether `decaying_mean.py` moves into
  `app/services/` so the twins and the scripts share one implementation.
- Names of the new constants, the exact onset discount of the first stable value, report layout.
- `TRAIN_SETS` / `TEST_SET` bookkeeping in `fit_facepalm.py` (set 6 was the hold-out so far).
- Whether the calibration and spot-check reports are re-run in full or only the tables D-13 needs.

### Deferred Ideas (OUT OF SCOPE)
- **Scoring rows with a played line shorter than depth 3:** not here (D-03); revisit only if 252's repair leaves
  a relevant share unscored.
- **Mixed inputs** (loss at depth 3, missed gain as a mean) and other single depths: left out to keep the
  candidate count low (D-06).
- **Other inputs from the 2026-11-15 review:** "the gain is a simple capture of an undefended piece", "the best
  move is the only winning move", a separate small model for pure misses.
- **Largest loss at any depth for "neither" rows** (AUC 0.73 on 23 rows in the probe).
- **Loss-aversion weight for the drill below 1.0:** waits for GM Noel Studer's answer (254 deferred).
</user_constraints>

<phase_requirements>
## Phase Requirements (coverage set = CONTEXT decisions)

No formal REQ-IDs. The planner maps D-01..D-15 to tasks.

| ID | Description | Research Support |
|----|-------------|------------------|
| D-01 | Precondition: stop when set 8 has unlabelled rows | Label file layout and a ready check command, section "D-01 precondition" |
| D-02 | Pull features from prod as lines are, no 252 wait | `facepalm_features.py` already writes all 18 slots; prod command in "Operator runs" |
| D-03 | Depth 3 still required to score | Coverage gate stays `played[3]` / mate within `LINE_DEPTH` for every input (Pattern 2) |
| D-04 | NULL best prob on a no-loss row unscores (twins) | Exact edit map for `_spread_term` / `_spread_sql` (WR-01 map) |
| D-05 | Fit excludes the same rows, counts them | Per-spec exclusion design (WR-03 map, Pattern 5) |
| D-06 | Three inputs, same input for loss and gain | `MaterialInput` Literal, Python + SQL builders for all three (Patterns 1-3) |
| D-07 | Repeated CV over sets 1-8, existing criteria | Per-input staged pipeline, `choose_candidate` reuse (Pattern 4) |
| D-08 | Set 8 hold-out per candidate | Pipeline on sets 1-7, score set 8; leakage pitfall in today's `_holdout` (Pitfall 2) |
| D-09 | Decaying mean wins ties vs depth 3 | `choose_material_input` with an explicit preference order (Pattern 4) |
| D-10 | Final constants on all eight sets | Unchanged `fit_candidate` on all usable rows |
| D-11 | Loss gate 1 vs none, decided by the fit | `FACEPALM_LOSS_GATE: float | None`, stage-2 candidates (Pattern 6) |
| D-12 | WR-03 spread-form-aware exclusion | Line map of `_exclusion_reason:318` / `spec_row_values:570-598` |
| D-13 | Owner checkpoint with fixtures, commented rows, Window 14, pure-miss pass rates, pool | Report section + calibration re-run ("Operator runs") |
| D-14 | Re-run stages 1-3 per input | Pattern 4 |
| D-15 | Normal constants + code release, changelog bullet | `CHANGELOG.md:9` `## [Unreleased]` |
</phase_requirements>

## Summary

This is an internal refactor-plus-refit of three pieces that already exist and are well tested: the score twins
(`app/services/facepalm_score.py`, Python and SQLAlchemy), the fit script (`scripts/blunder_check/fit_facepalm.py`)
and the operator tooling (`facepalm_features.py`, `blunder_check_calibration.py`). No new library, no migration, no
prod write. The committed features TSV already carries all nine slots of both lines
(`played_mat_1..9`, `best_mat_1..9`, verified header), so the fit needs no new feature pull until set 8 is labelled;
only the fit's loader and design matrix must read the arrays instead of slot 3.

The design that keeps the 254 invariants intact: add two shape selectors to `FacepalmModel`
(`material_input: MaterialInput` and `loss_gate: float | None`, defaults `"depth_3"` / `None` so every existing
model, including the frozen `PHASE_250_MODEL`, scores exactly as today), switch `FacepalmFacts` from the scalars
`played_3` / `best_3` to the stored arrays (mirroring `FacepalmColumns`), and put the per-depth series and the two
aggregates in one new pure module `app/services/facepalm_material.py` with a Python implementation and a SQL
builder each, unrolled over the five odd depths so the SQL twin stays a plain column expression usable in SELECT,
WHERE and ORDER BY. Implement all three inputs in both twins up front: then the refit stays "constants only" and
the owner can pick any input at the D-13 checkpoint without code after it.

A useful fact for planning: on the 199 usable rows of the 2026-11-15 features there are **zero** rows with a NULL
reply spread and **zero** with a NULL best probability (computed this session). WR-01 / WR-03 therefore cannot move
the fit on sets 1-7; only set 8 rows can. That makes a strong regression test possible before the labels exist:
the refactored fit, forced to `depth_3`, must reproduce today's shipped constants from
`facepalm-features-2026-11-15.tsv`.

**Primary recommendation:** Build `facepalm_material.py` (Python + SQL, all three inputs, mate short-circuit within
`LINE_DEPTH`), extend `FacepalmModel` / `FacepalmFacts`, fix WR-01 in both twins, rework the fit into a per-input
staged pipeline with per-candidate row sets and a set-8 hold-out run on sets 1-7, pin it with the 2026-11-15
reproduction test; then (after D-01) run features, fit, calibration and the owner checkpoint inline from the
orchestrator.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Per-depth series and aggregates (Python) | API / Backend (`app/services/facepalm_material.py`, pure) | Scripts import it | `app/` must not import `scripts/`; twins and fit share one implementation |
| Score as SQL expression | Database / Storage (PostgreSQL evaluates the CASE tree) | API builds it (`facepalm_expr`) | 254 D-01: query-time expression, chip and filter from one bound object |
| Fitted constants | API / Backend (`blunder_check_rules.py`) | — | 250 D-04: named constants, reproduced by `--check-constants` |
| Model selection, report | Operator scripts (`fit_facepalm.py`) | — | Reads a committed TSV only, no DB |
| Feature pull, calibration | Operator scripts against prod (read-only engine) | Orchestrator runs them | Prod tunnel and Maia; subagents lack prod access |
| Library chip / filter, drill pool | Readers in `app/repositories/` | — | Unchanged callers of `facepalm_expr(lam)` |

## Standard Stack

No new dependency. Everything runs on what is installed.

### Core (in use, versions verified this session)
| Library | Version | Purpose | Note |
|---------|---------|---------|------|
| SQLAlchemy | 2.0.52 [VERIFIED: `import sqlalchemy` in .venv] | SQL twin (`case`, `cast`, `literal`, ARRAY index) | `select()` 2.x API only (CLAUDE.md) |
| PostgreSQL | 18.6 dev container [VERIFIED: `select version()` on flawchess-dev-db-1] | Evaluates the expression; 1-based array index | `arr[3]` = depth 3 |
| numpy | 2.5.2 [VERIFIED: .venv] | IRLS logistic fit, CV | Existing in `fit_facepalm.py` |
| python-chess | 1.11.2 [VERIFIED: .venv] | `line_facts` / `best_line_facts` in the feature pull | Existing |
| Python | 3.14.3 [VERIFIED: .venv] | — | ty must stay clean |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Unrolled CASE over five odd slots | `unnest(arr) WITH ORDINALITY` subquery | A correlated subquery per row; awkward inside the drill EXISTS probe and the library filter, harder to keep in exact parity. Do not use. |
| All three inputs in the SQL twin up front | SQL only for the winner after the checkpoint | Breaks "refit = constants only" (254 pattern, `blunder_check_rules.py:79` comment) and puts code after the owner's decision. Do not use. |
| New `facepalm_material.py` | Put series code inside `facepalm_score.py` (427 lines) | That file would pass about 650 lines and mix two concerns. Use the new module. |

**Installation:** none.

## Package Legitimacy Audit

No external package is installed by this phase. Nothing to audit.

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Verified code facts the plan depends on

All read this session with the Read tool; values quoted verbatim.

**Constants** (`app/services/blunder_check_rules.py`):
- `:58` `FACEPALM_SCORE_MIN: float = 0.5`; `:62` `LINE_DEPTH: int = 3`; `:64` `LOSS_CAP: int = 5`; `:66` `MATE_LOSS: int = 5`
- `:83-84` `MaterialForm = Literal["combined", "split"]`, `SpreadForm = Literal["always", "loss_only", "best_prob_for_misses"]`
- `:85` `FACEPALM_MATERIAL_FORM: MaterialForm = "split"`; `:76` `FACEPALM_LOSS_COEF: float = 1.0129`; `:87` `FACEPALM_MISSED_COEF: float = 0.0891`
- `:91-93` `FACEPALM_MISSED_FLOOR: int | None = None`, `FACEPALM_MISSED_CAP: int = 5`, `FACEPALM_MISSED_MATE: int = 5`
- `:94` `FACEPALM_SPREAD_FORM: SpreadForm = "best_prob_for_misses"`; `:97` `FACEPALM_BEST_PROB_COEF: float = 1.0405`
- `:67-72` comment block naming `facepalm-features-2026-11-15.tsv` and `facepalm-fit-2026-11-15.md`; update it in the release.

**Depths** (`app/services/line_material.py`): `:46` `LINE_LOSS_DEPTHS: tuple[int, ...] = (1, 3, 5, 7, 9)`;
`:53` `LINE_MATERIAL_SLOTS: int = 9`; `:105-112` `material_at_depth(material, depth)` returns None for a missing or
short array (`array[depth - 1]`).

**Set-8 sampler helper** (`scripts/blunder_check/decaying_mean.py`): `:32` `DECAY_DEPTHS: tuple[int, ...] = LINE_LOSS_DEPTHS`,
`:34` `DECAY_RATIO: float = 0.5`, `:35` `DECAY_WEIGHTS: tuple[float, ...] = tuple(DECAY_RATIO**index for index in range(len(DECAY_DEPTHS)))`.
`loss_series` (`:38-53`) uses `MATE_LOSS` from `played_mate_ply <= depth` on and `min(LOSS_CAP, max(0, -material))`;
`gain_series` (`:56-77`) uses `FACEPALM_MISSED_MATE` from `best_mate_ply <= depth` on and floors at 0; no
short-circuit for a mate within depth 3. Used by `miss_labels.py:129-132, 424, 443, 449, 882-895`.

**Stored arrays** (`app/models/game_flaw.py`): `:154-159` `played_line_material` / `best_line_material` are
`ARRAY(SmallInteger)`, nullable; `:22-27` CHECK `cardinality(...) = 9 AND array_lower(..., 1) = 1` (NOT VALID).
`:133` `line_mate_ply` = "first line ply after which the blunderer is mated"; `:147-148` `best_line_mate_ply` =
"ply at which the best line mates the opponent, the best move counting as ply 0".

**Mate plies vs array slots** (`line_material.py:224-239`): once the blunderer is mated inside the walked line, every
deeper depth returns the material at the mate, not a mate value. So a mate beyond depth 3 is invisible in the arrays;
the aggregate must override from the mate ply on (as `decaying_mean.loss_series` does).

**Label file** (`reports/blunder-check/facepalm-labels.tsv`): header (line 1) is
`n	set	elo	move	link	engine_drop	expected_loss	reply_loss	practical_loss	played_prob	reply_spread	line_loss3	mate3	label	comment`.
Set 8 rows look like line 232: `241	8	1593	Ra8+	https://flawchess.com/analysis?game_id=2022738&ply=88` followed by nine
empty cells and an empty `label`, **14 fields, no `comment` cell** (15 since 2026-11-16, when a `blitz_elo` column was inserted after `elo` at the owner's request; all readers go by header name) (so `csv.DictReader` returns `None` for
`comment`). Labelled rows carry `0`, `1` or `0.5` in `label` (lines 228-231). Set counts (computed): sets 1-4 have
20 rows each, sets 5-7 50 each, set 8 60 rows, all with an empty label on 2026-11-16; n runs 1-300 with 21-30 absent.

**Features TSV** (`reports/blunder-check/facepalm-features-2026-11-15.tsv` line 1): columns
`n set game_id ply label pinned_elo played_prob reply_spread best_prob pre_spread played_mat_1 .. played_mat_9 line_mate_ply best_mat_1 .. best_mat_9 best_mate_ply best_uci pv_source pv_plies best_pv_plies note`.
The arrays are already there; `fit_facepalm.FACTS_REQUIRED_COLUMNS` (`:156-168`) only requires `played_mat_3` /
`best_mat_3` and `_facts_row` (`:272-288`) reads only those.

**Fit constants** (`scripts/blunder_check/fit_facepalm.py`): `:81` `FIT_SELECTION_THRESHOLD: float = 0.7`;
`:82` `FIT_THRESHOLDS: tuple[float, ...] = (0.5, 0.6, 0.7, 0.8, 0.9)`; `:88` `EXIT_CONSTANTS_MISMATCH: int = 6`;
`:107` `FACTS_LOSS_FLOOR: int = 0`; `:112` `MISSED_FLOOR_CANDIDATES: tuple[int | None, ...] = (None, 0)`;
`:113-114` `MISSED_CAP_WIDE: int = 9`, `MISSED_CAP_CANDIDATES: tuple[int, ...] = (LOSS_CAP, MISSED_CAP_WIDE)`;
`:117` `REPEAT_SEEDS: int = 5`; `:119` `FAIR_SHARE_TIE_TOLERANCE: float = 0.01`; `:126` `AUC_TIE_TOLERANCE: float = 0.005`;
`:128-130` `TRAIN_SETS: tuple[str, ...] = ("1", "2", "3", "4", "5", "7")`, `TEST_SET: str = "6"`, `TRAIN_SETS_TEXT: str = "1-5 and 7"`.

**Data facts from the 2026-11-15 TSV** (computed this session with a scratch script over the committed file; decided
rows only, n = 221): 199 scored (22 unscored by D-03); among the 199: NULL `reply_spread` 0, NULL `best_prob` 0;
played line reaches depth 9 on 198; played mate within 3 plies 7, beyond 3 plies 4; best-line mate within 3 plies
7, beyond 3 plies 5; best line entirely unknown 31; decaying-mean loss strictly between 0 and 1 on 42 rows;
"loses material" flips between depth 3 and the mean on 26 rows (gate `> 0`) or 24 rows (gate `>= 1`); loss input
moves by a pawn or more on 26 rows, gain input on 53. First stable value: loss always has a stable pair (onset
index 0: 155, 1: 36, 2: 7, 3: 1); gain has no stable pair on 18 rows, so the fallback rule matters.

**Owner fixtures** (computed this session from `tests/services/line_material_fixtures.py:211-234` with the app's
`line_facts` / `best_line_facts`): 817357:24 played `[0]*9`, best `[3]*9`; 820181:65 played `[5]*9`, best `[10]*9`;
no mates. Constant arrays, so every candidate input gives the same material values as depth 3 (loss 0, gain 3 and
5). Their score can only move through the new coefficients.

## Architecture Patterns

### System Architecture Diagram

```
                       stored facts on game_flaws (9-slot arrays, mate plies, Maia inputs)
                                              |
            +---------------------------------+----------------------------------+
            |                                                                    |
   Python twin facepalm_score(facts, lam, model)              SQL twin facepalm_score_sql(columns, lam, model)
            |                                                                    |
   coverage gate (D-03): mate_ply <= 3 -> MATE_LOSS;        same gate as CASE: mate_ply <= 3 / played[3] IS NULL
   played[3] unknown -> None                                                     |
            |                                                                    |
   model.material_input ----------------------------------------------- unrolled per-depth CASE (depths 1,3,5,7,9)
     depth_3      -> loss_feature / missed_feature (today)                 depth_3 -> today's _loss_sql/_missed_sql
     decaying_mean-> facepalm_material.decaying_mean(series)               decaying_mean -> sum(w*v)/sum(w known)
     first_stable -> facepalm_material.first_stable(series)                first_stable  -> CASE ladder over pairs
            |                                                                    |
   loses = loss > 0 (gate None) or loss >= gate               same comparison in CASE
            |                                                                    |
   spread term: always / loss_only / best_prob_for_misses     same; pure-miss branch NULL when best_prob NULL (D-04)
            |                                                                    |
   z -> sigmoid -> score or None                               z -> 1/(1+exp(-z)) -> double or NULL
            |                                                                    |
   fit_facepalm.py design matrix, sample.py calibration,      facepalm_expr(lam): library_repository (chip, filter,
   maia_flaw_scoring._row_score (report counts)               markers), blunder_check_repository (drill pool),
                                                              backfill_maia_flaws.py status
```

### Recommended file layout

```
app/services/
├── blunder_check_rules.py   # + MaterialInput Literal, FACEPALM_MATERIAL_INPUT, FACEPALM_LOSS_GATE, MATERIAL_DECAY_RATIO
├── facepalm_material.py     # NEW: per-depth series, decaying_mean, first_stable (Python) + SQL builders
└── facepalm_score.py        # FacepalmModel/FacepalmFacts fields, dispatch on material_input, gate, WR-01
scripts/blunder_check/
├── decaying_mean.py         # keeps its sampler API; imports weights/mean from the app module
├── fit_facepalm.py          # arrays in FitRow, per-input pipeline, per-spec exclusion, set-8 hold-out, owner section
├── sample.py / render.py / spot_check.py   # BlunderRecord carries arrays (cache v4), played_3/best_3 as properties
tests/services/
├── test_facepalm_material.py  # NEW (Wave 0)
```

### Pattern 1: New model and facts fields (defaults reproduce today)

```python
# app/services/blunder_check_rules.py (next to MaterialForm / SpreadForm)
MaterialInput = Literal["depth_3", "decaying_mean", "first_stable"]
FACEPALM_MATERIAL_INPUT: MaterialInput = "depth_3"     # set by the refit
# "Loses material" for the gated spread forms: None = any loss above 0, a number g = loss >= g (D-11).
FACEPALM_LOSS_GATE: float | None = None                # set by the refit
# Weight ratio between consecutive odd depths of the aggregate inputs, fixed by the owner (seed), not fitted.
MATERIAL_DECAY_RATIO: float = 0.5

# app/services/facepalm_score.py
@dataclass(frozen=True, slots=True)
class FacepalmModel:
    ...
    material_input: MaterialInput = "depth_3"
    loss_gate: float | None = None

@dataclass(frozen=True, slots=True, kw_only=True)
class FacepalmFacts:
    played_prob: float | None
    reply_spread: float | None
    played_material: Sequence[int | None] | None      # replaces played_3 (9 slots, slot N = depth N)
    mate_ply: int | None
    best_material: Sequence[int | None] | None = None # replaces best_3
    best_mate_ply: int | None = None
    best_prob: float | None = None
    pre_spread: float | None = None

    @property
    def played_3(self) -> int | None:  # derived, for reports and tests
        return material_at_depth(self.played_material, LINE_DEPTH)
```
`MaterialInput` and the new constant names are a recommendation [ASSUMED: naming is Claude's discretion]. Keep the
defaults `"depth_3"` / `None`: `PHASE_250_MODEL` (`tests/facepalm_models.py:17-23`) relies on defaults being the
pre-refit shape (D-12 of 254), and `test_new_twin_reproduces_phase_250_score` keeps passing unchanged.

### Pattern 2: Material inputs (one implementation, both twins)

Rules (recommended; all three inputs share them):
1. **Coverage (D-03):** `mate_ply <= LINE_DEPTH` gives loss `MATE_LOSS`; else `played[3]` unknown gives None (row
   unscored). Identical for every input, so all candidates are fitted on the same rows.
2. **Mate within `LINE_DEPTH` short-circuits** for every input: loss `MATE_LOSS`, missed `model.missed_mate`, exactly
   today's values (CONTEXT: "must keep scoring as today's ... case"). Without it a played mate at ply 3 averages to
   `(m1 + 0.9375*5)/1.9375` (about 2.4) under the decaying mean.
3. **Mate beyond `LINE_DEPTH`** enters per depth from the mate ply on: loss depth d is `MATE_LOSS` when
   `mate_ply <= d`; gain depth d is `missed_mate` when `best_mate_ply <= d` (the `decaying_mean.py` convention).
4. **Per-depth loss:** `min(-played[d], LOSS_CAP)`, raised to `model.loss_floor` when not None (the depth-3 rule
   applied per depth); None when `played[d]` is None.
5. **Per-depth gain:** `best[d] - max(0, played[d])`, raised to `model.missed_floor` when not None, capped at
   `model.missed_cap`; None when either slot is None. The fit keeps choosing floor {None, 0} and cap {5, 9} per depth
   (stage 1).
6. **Decaying mean:** weights `MATERIAL_DECAY_RATIO**i` over depths (1, 3, 5, 7, 9); sum over known depths divided by
   the sum of their weights; None when none known. Missed None becomes 0.0 (D-18).
7. **First stable** [ASSUMED definition, not recorded by the probe]: the first index i (0..3) where depth i and depth
   i+1 are both known and equal; value `v_i * MATERIAL_DECAY_RATIO**i` (onset discount reuses the owner-fixed
   ratio: onset depth 1 counts full, depth 3 half, ...). Fallback when no pair is stable: the last known value,
   discounted by its own index. None when nothing is known (missed then 0.0). Only even-index arithmetic on small
   integers and powers of two, so Python and SQL are exact.
8. **Only odd slots are read**; even slots never enter (254 D-17).

```python
# app/services/facepalm_material.py (sketch; keep every function at nesting depth <= 3)
MATERIAL_DEPTHS: Final[tuple[int, ...]] = LINE_LOSS_DEPTHS
DECAY_WEIGHTS: Final[tuple[float, ...]] = tuple(
    MATERIAL_DECAY_RATIO**index for index in range(len(MATERIAL_DEPTHS))
)
Series = tuple[float | None, ...]  # one value per MATERIAL_DEPTHS entry

def decaying_mean(series: Series) -> float | None:
    total = weight_sum = 0.0
    for value, weight in zip(series, DECAY_WEIGHTS, strict=True):
        if value is None:
            continue
        total += weight * value
        weight_sum += weight
    return None if weight_sum == 0.0 else total / weight_sum

def first_stable(series: Series) -> float | None:
    for index in range(len(series) - 1):
        value, following = series[index], series[index + 1]
        if value is not None and value == following:
            return value * DECAY_WEIGHTS[index]
    for index in reversed(range(len(series))):
        if series[index] is not None:
            return series[index] * DECAY_WEIGHTS[index]
    return None
```

### Pattern 3: SQL twin of the aggregates (unrolled, Float-typed, explicit NULL guards)

```python
# Source: verified compile output this session (SQLAlchemy 2.0.52, postgresql dialect)
def _loss_depth_sql(played: Any, mate_ply: Any, depth: int, loss_floor: int | None) -> ColumnElement[Any]:
    slot = played[depth]                        # 1-based PostgreSQL index = depth
    capped = func.least(-slot, LOSS_CAP)
    if loss_floor is not None:
        capped = func.greatest(capped, loss_floor)
    return case(
        (mate_ply <= depth, literal(float(MATE_LOSS), Float)),
        (slot.is_(None), null()),               # guard BEFORE least/greatest: they skip NULLs in PostgreSQL
        else_=cast(capped, Float),
    )

def decaying_mean_sql(series: Sequence[ColumnElement[Any]]) -> ColumnElement[Any]:
    num = sum_of(literal(w, Float) * func.coalesce(v, literal(0.0, Float)) for v, w in zip(series, DECAY_WEIGHTS))
    den = sum_of(case((v.is_(None), literal(0.0, Float)), else_=literal(w, Float)) for v, w in zip(series, DECAY_WEIGHTS))
    return case((den == 0.0, null()), else_=num / den)

def first_stable_sql(series: Sequence[ColumnElement[Any]]) -> ColumnElement[Any]:
    stable = [
        (and_(series[i].isnot(None), series[i] == series[i + 1]), series[i] * literal(DECAY_WEIGHTS[i], Float))
        for i in range(len(series) - 1)
    ]
    fallback = [
        (series[i].isnot(None), series[i] * literal(DECAY_WEIGHTS[i], Float))
        for i in reversed(range(len(series)))
    ]
    return case(*stable, *fallback, else_=null())
```
`sum_of` is a small left fold (`functools.reduce(operator.add, ...)`). Verified this session: with Float-typed
operands SQLAlchemy emits `... / CAST(CASE ... END AS FLOAT)`; with an untyped denominator (for example
`func.nullif(...)` or an integer slot) it emits `CAST(... AS NUMERIC)`. Keep every operand Float (`cast(x, Float)`,
`literal(w, Float)`) so PostgreSQL computes in double precision like Python. Weights are powers of two and values
small integers, so the sums are exact in both twins and the one division rounds identically.

### Pattern 4: Fit as a per-input staged pipeline

```
for input in MATERIAL_INPUTS = ("decaying_mean", "first_stable", "depth_3"):   # preference order (D-09)
    stage 1 (D-06): material form x missed floor x missed cap  (+ baseline reference)
    stage 2 (D-07, D-11): always | loss_only x gate {None, 1.0} | best_prob_for_misses x gate {None, 1.0}
    stage 3 (D-08): + best_prob (unless stage 2 uses it), + pre_spread
    -> final[input]; holdout[input] = same pipeline run on sets 1-7 only, coefficients on 1-7, scored on set 8
chosen input = choose_material_input(final scores)   # AUC, then fair share, then MATERIAL_INPUTS order
constants = final[chosen].model (fitted on all eight sets, D-10)
```
- `choose_material_input` uses `choose_candidate`'s two tolerances but breaks a remaining tie by the
  `MATERIAL_INPUTS` order, not by free coefficients (D-09 overrides "fewer coefficients" at this level; the three
  finals can differ in coefficient count after stage 3).
- `CandidateSpec` gains `material_input: MaterialInput` and `loss_gate: float | None`; `spec_label`, `model_from_spec`,
  `MODEL_CONSTANT_NAMES`, `model_constants_block`, `_EXACT_FIELDS` gain `FACEPALM_MATERIAL_INPUT` / `FACEPALM_LOSS_GATE`.
- Add `--material-input {auto,decaying_mean,first_stable,depth_3}` and `--loss-gate {auto,none,1}` next to
  `--material-form` / `--spread-form` (same "forced by" reporting). If the owner overrides the CV choice at D-13,
  the constants come from the forced run and `--check-constants` must run with the same flags; record the exact
  command in the `blunder_check_rules.py:67-72` comment.
- Runtime: about 15 candidates x 5 seeds x 10 folds per input, x3 inputs, x2 (all sets and sets 1-7), on ~250 rows.
  Seconds. The synthetic module fixture in `test_fit_facepalm.py` (1200 rows) roughly triples its time.

### Pattern 5: Per-candidate rows (WR-03, D-05, D-12)

Split today's `_exclusion_reason` into a base filter (label, played prob, D-03 coverage; same for every candidate)
and a spec filter evaluated per candidate:

```python
def _spec_exclusion(row: FitRow, spec: CandidateSpec) -> str | None:
    loss = material_loss_of(row, spec)          # the twin's own loss input for spec.material_input
    if spec.spread_form == "always" or loses(loss, spec.loss_gate):
        return REASON_NO_SPREAD if row.reply_spread is None else None
    if spec.spread_form == "best_prob_for_misses" and row.best_prob is None:
        return REASON_NO_BEST_PROB              # D-05: the shipped twin would leave it unscored (D-04)
    return None                                 # D-12: gated form, not losing, spread never read
```
`CandidateFit` must carry its own `rows` (and labels), because `oof`, the D-13 tables and the hold-out are aligned
to them. Report per candidate the row count, and in `## Data` the rows excluded per reason per spread form and the
count that "qualify only under a gated form" (D-12).

### Pattern 6: The loss gate in both twins

```python
def loses(loss: float, gate: float | None) -> bool:      # Python
    return loss > 0 if gate is None else loss >= gate

def _loses_sql(loss: ColumnElement[Any], gate: float | None) -> ColumnElement[bool]:  # SQL
    return loss > 0 if gate is None else loss >= gate
```
Use `>=` for the numeric gate: a pawn lost at every depth gives a mean of exactly 1.0 and must count as losing.
For integer depth-3 losses `> 0` and `>= 1` are the same predicate, so under `depth_3` the two gate candidates
produce identical fits; list `None` first so a tie keeps "no gate".

### Anti-Patterns to Avoid
- **GREATEST / LEAST over a possibly NULL slot:** PostgreSQL skips NULLs; guard `IS NULL` in an earlier CASE branch
  (the existing `_missed_sql` docstring states the same rule).
- **A subquery or `unnest` in the expression:** readers bind the expression once and use it in SELECT and WHERE
  (`library_repository.py:1192`, `blunder_check_repository.py:411, 225`); keep it a scalar column expression.
- **Importing `scripts.*` from `app/`:** the shared implementation lives in `app/services/`.
- **Changing `metrics.material_type` to the aggregate:** keep the report's loss-type / miss-type split at depth 3 so
  the D-13 tables stay comparable with the 2026-11-15 report and with how sets 7 and 8 were drawn.

## Exact edit map for WR-01 and WR-03

### WR-01 (D-04) in `app/services/facepalm_score.py`
| Lines | Today | Change |
|---|---|---|
| `:237-241` `_best_prob_term` | returns `0.0` for coef 0 or `best_prob is None` | Keep for the ADDITIVE path (`_optional_terms`), unchanged behaviour |
| `:244-253` `_spread_term` | `if model.spread_form != "always" and loss <= 0:` then `return _best_prob_term(...)` under bpfm | Replace `loss <= 0` with `not loses(loss, model.loss_gate)`; under bpfm call a new `_pure_miss_term`: `0.0` if `best_prob_coef == 0.0`, `None` if `best_prob is None`, else `coef * log(best_prob + PLAYED_PROB_OFFSET)` |
| `:333-340` `_best_prob_sql` | `case((best_prob.is_(None), literal(0.0)), else_=...)` | Keep for the additive path (`_optional_sql:358-370`) |
| `:343-355` `_spread_sql` | `case((loss > 0, spread), else_=pure_miss)` with `pure_miss = _best_prob_sql(...)` | `case((_loses_sql(loss, model.loss_gate), spread), else_=_pure_miss_sql(...))`; `_pure_miss_sql` returns `literal(0.0)` for coef 0, else `case((best_prob.is_(None), null()), else_=coef * ln(...))` |
| `:266-301` `facepalm_score` | `spread = None if loss is None else _spread_term(...)`; `if loss is None or spread is None: return None` | Already propagates a None spread term, no structural change |
| Module docstring `:22-41` | describes depth-3 inputs and "0 when best_prob is None" | Rewrite the term rules (inputs, gate, D-04) |

Keep the zero-coefficient omission rule: a `best_prob_coef` of 0.0 must never unscore a row.

### WR-03 (D-12) and D-05 in `scripts/blunder_check/fit_facepalm.py`
| Lines | Today | Change |
|---|---|---|
| `:318-330` `_exclusion_reason` | drops every `reply_spread is None` row (`:326-327`) | Remove the spread check from the base filter; move to `_spec_exclusion` (Pattern 5) |
| `:333-343` `split_usable` | one usable list for all candidates | Keep as the base filter; add the per-spec filter in `fit_candidate` / `_fit_all` |
| `:570-598` `spec_row_values` | `spread = _require(row.reply_spread)` at `:581` before the `gated_off` guard (`:582`) | Compute `loss` via the twin's input for `spec`, `gated_off = spec.spread_form != "always" and not loses(loss, spec.loss_gate)`, read the spread only when not gated off |
| `:563-567` `_best_prob_value` | `loss > 0` gate | Use `loses(loss, spec.loss_gate)` |
| `:137-144` reasons | `REASON_NO_SPREAD` etc. | Add `REASON_NO_BEST_PROB` |
| `:1442-1460` `_facts_data_section` | counts per reason | Add D-05 and D-12 counts |
| `:1570-1598` `_d13_sections` | uses `outcome.usable` with `outcome.chosen.oof` | Use the chosen candidate's own rows (else misalignment once row sets differ) |

### Other fit edits
| Lines | Change |
|---|---|
| `:156-168` `FACTS_REQUIRED_COLUMNS`, `:200-217` `FitRow`, `:272-288` `_facts_row` | Read all nine `played_mat_N` / `best_mat_N`; `FitRow` carries tuples `played_material` / `best_material` (keep `line_loss_3` derived for the legacy path) |
| `:128-130` `TRAIN_SETS` / `TEST_SET` | `("1", ..., "7")`, `"8"`, text `"1-7"` |
| `:1340-1356` `_split_section` | Heading is the literal `"## Sets 1-5 vs set 6"` (`:1342`); derive it from the constants; per input |
| `:809-828` `_holdout` | Fits the spec chosen on all sets; replace by the per-input pipeline on sets 1-7 (Pitfall 2) |
| `:838-861` `score_extras` | Build `FacepalmFacts` with arrays |
| `:1192-1220` `run_facts_fit` | Wrap in the per-input loop |
| `:1668-1707` `_parse_args` | `--material-input`, `--loss-gate`, optional `--labels` (comments for the owner section) |

## D-01 precondition

The fit reads the features TSV only; unlabelled rows already land in "Extra rows" (`REASON_NO_LABEL`, tested by
`test_unlabelled_set_eight_rows_are_extras_not_fit_rows`). So the gate must be an explicit first step on the label
file. A label cell counts as labelled when it is exactly `0`, `1` or `0.5`; set 8 must have 60 rows:

```bash
uv run python -c "import csv,sys; rows=[r for r in csv.DictReader(open('reports/blunder-check/facepalm-labels.tsv'), delimiter='\t') if r['set']=='8']; bad=[r['n'] for r in rows if (r['label'] or '').strip() not in ('0','1','0.5')]; print(len(rows), 'set-8 rows,', len(bad), 'unlabelled:', ' '.join(bad)); sys.exit(1 if bad or len(rows)!=60 else 0)"
```
Exit 1 means stop and leave the plan pending. Optionally also check the first 231 lines are unchanged since commit
`2a4549903` (cell-wise by `n` and header name, not a plain `git diff`, since the `blitz_elo` column inserted on 2026-11-16 shifts every line), so an accidental edit of sets 1-7 is
seen before the fit.

## Operator runs (orchestrator, inline, prod tunnel)

Subagents have no prod access and long DB runs die inside executors; plan these as orchestrator steps.

1. `bin/prod_db_tunnel.sh`; check prod connections stay well under 50.
2. Features (no `--pv-cache`, so current lines are read, D-02):
   `uv run --group maia-inference python scripts/blunder_check/facepalm_features.py --db prod --labels reports/blunder-check/facepalm-labels.tsv --extra 2099808:23 --out reports/blunder-check/facepalm-features-$(date -u +%F).tsv`
   Expect 290 label rows plus the extra. The summary line reports NULL score inputs and NULL best lines. Record
   the Phase 252 state at that time (D-02). Owner fixtures 817357:24 / 820181:65 are dev-DB games (254-11 did not
   find them on prod); score them from the committed fixture facts instead.
3. Fit: `uv run python scripts/blunder_check/fit_facepalm.py --features <tsv> --labels reports/blunder-check/facepalm-labels.tsv --out reports/blunder-check/facepalm-fit-$(date -u +%F).md`
4. Paste the report's constants in the working tree, then the prod calibration as 254-11 did (writes the
   calibration and spot-check reports, about 15 to 30 minutes):
   `uv run --group maia-inference python scripts/blunder_check_calibration.py --db prod --sample-permille 25 --cache temp/blunder-check/prod-cache-$(date -u +%F).json`
   The cache must be fresh (version bump, Pitfall 9). Run it detached with a log if it may outlast the session
   (prod reboots around 02:15 UTC).
5. D-13 checkpoint (blocking): show the input comparison, the set-8 hold-out per input, the stage tables, D-13 tables,
   the owner section, the calibration pool-by-cut and pass shares by material type.
6. After the owner's answer: constants (and `FACEPALM_SCORE_MIN`) committed, `--check-constants` exits 0, tests that
   pin fixtures / Window 14 updated, changelog bullet, full pre-merge gate.

Re-run the calibration in full (recommendation for the discretion item): it is one command, the pool-by-cut and
pass-share tables D-13 needs come from it, and the spot-check report is written by the same run.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Line material per depth | A new capture walker | `line_facts` / `best_line_facts` (`line_material.py:291-325`) and the stored arrays | Exchange, desperado, recapture rules exist once (250 D-02) |
| Logistic fit, CV, AUC | sklearn or a new harness | `fit_logistic`, `cv_predictions`, `auc`, `choose_candidate` in `fit_facepalm.py` | Deterministic, tested, already what `--check-constants` reproduces |
| Twin parity harness | A new DB fixture | `_sql_scores` VALUES grid in `test_facepalm_score.py:282-320`, `seed_flaw_rows` | Handles bind limits and NULL typing (the typing row) |
| Seeding reader tests at a target score | Hard-coded facts | `tests/facepalm_seed.facepalm_fact_columns` | Solves through the Python twin for any model |
| Read-only prod access | Raw engine | `make_readonly_engine` (`sample.py`), used by features and calibration | T-254-33 mitigation |

## Common Pitfalls

### Pitfall 1: Candidates fitted on different rows
**What goes wrong:** D-05 / D-12 make the usable rows depend on spread form, gate and input; AUCs on different row
sets are not strictly comparable, and `_d13_sections` (`outcome.usable` with `outcome.chosen.oof`) misaligns.
**How to avoid:** every `CandidateFit` carries its rows; the report shows a row count per candidate. On the
2026-11-15 rows the sets are identical (0 NULL spread, 0 NULL best prob), so the effect is limited to set 8 rows.
**Warning signs:** a length mismatch error in the D-13 tables, or stage rows with different "rows" values.

### Pitfall 2: Set 8 leaks into the hold-out
**What goes wrong:** today's `_holdout` (`:809-828`) refits the coefficients of a spec that was chosen with all sets,
so set 8 labels influenced the shape. D-08 asks for set 8 "untouched".
**How to avoid:** run the whole per-input pipeline on sets 1-7, then fit and score set 8. Report n per input; about
55 decided set-8 rows means hold-out AUC noise of several hundredths, so the report should say so.

### Pitfall 3: Hard-coded hold-out heading
`_split_section` prints `"## Sets 1-5 vs set 6"` (`:1342`) and `test_report_has_d13_sections` asserts it
(`test_fit_facepalm.py:990`). Derive the heading from `TRAIN_SETS_TEXT` / `TEST_SET` and update the test. The
synthetic writer uses `FACTS_SETS: int = 7` (`:478`), so set 8 must be added there or the hold-out is empty.

### Pitfall 4: NUMERIC division and NULL-skipping LEAST/GREATEST in SQL
Covered in Pattern 3. A NUMERIC cast still gives the right value within tolerance but loses the exact-parity
property; a GREATEST over a NULL slot silently returns the other argument.

### Pitfall 5: Mates in the arrays
After a mate the arrays keep the material at the mate (`line_material.py:236-238`), so without the per-depth mate
override a mate at ply 5 to 9 reads as a small or zero loss. And without the short-circuit a mate within depth 3
is averaged down. Test both with fixtures (played mate ply 3 and 5; best mate ply 0, 2 and 4).

### Pitfall 6: WR-01 touches only the pure-miss branch
The additive best-prob path (spread forms `always` / `loss_only` with `best_prob_coef != 0`) still reads NULL as 0
(D-18 consistency, `test_unknown_best_prob_contributes_zero`). Split that test: additive model unchanged, bpfm on a
no-loss row now None (both twins), bpfm on a losing row unchanged.

### Pitfall 7: Reader-test seeding after WR-01
`tests/facepalm_seed.facepalm_fact_columns` starts its grid at `played_3 = 0` with `maia_best_prob` None
(`:49-60, 99-111`). Under the shipped bpfm form those rows become unscored, so the grid skips them; very low target
scores may then raise "no seed grid point reaches the target score". Add a fixed seed best probability (a named
constant) to the seeded facts and to `_rest_of_z`, and switch `_material_array` callers to arrays.

### Pitfall 8: `FacepalmFacts` ripple
Constructors to update (grep this session): `app/services/maia_flaw_scoring.py:740-752` (`_row_score`, already has the
arrays), `scripts/blunder_check/sample.py:208-222` (`BlunderRecord.facepalm_score`), `fit_facepalm.py:838-861`,
`tests/facepalm_seed.py:69-71`, `tests/services/facepalm_owner_fixtures.py` (both fixtures), test helpers
`_facts` / `_facts_of` / `_facts_of_flaw` in `test_facepalm_score.py:197-260, 747-757`,
`test_maia_flaw_scoring.py:443-450, 941-946, 964-969, 1053-1058`, `test_blunder_check_calibration.py` `_blunder` helper
(`:393-447`), `test_fit_facepalm.py:740-753`. Scalar test inputs map cleanly to a constant odd-slot array: every
input gives the same value for a constant array, so most numeric assertions survive.

### Pitfall 9: Calibration cache format
`sample.py:82` `CACHE_VERSION: int = 3` stores depth-3 facts only (`FlawRow` shrinks the arrays in `_flaw_row`, `:529-544`). Carry
the arrays in `FlawRow` / `BlunderRecord` (`to_dict` / `from_dict`), keep `played_3` / `best_3` as derived
properties for `render.py:936-941, 1028-1030` and `spot_check.py:480-524`, and bump to 4 so an old cache is refused.

### Pitfall 10: Window 14 and the old TSV
`test_window_14_*` (`test_facepalm_score.py:656-691`) read `facepalm-features-2026-11-15.tsv` and assert the row is
unscored (1-ply line). If 252 has repaired its line by execution time, the new TSV will score it; then the test must
read the new TSV and assert the score is None or below `FACEPALM_SCORE_MIN` (D-13 "must still fall below the cut").

### Pitfall 11: ty in a fresh worktree
Run `uv run --group maia-inference ty check app/ tests/ scripts/` (without the group, three phantom errors appear in
a fresh worktree). The `Sequence[int | None]` (not `list`) parameter rule from CLAUDE.md applies to the new arrays.

### Pitfall 12: Features from `pv`, scores from stored arrays
`facepalm_features.py` recomputes the arrays from `game_positions.pv`; the app reads `game_flaws` arrays written by
the last line pass. If 252 repaired a line but the gap-fill pass has not run, the fit sees a longer line than the
app scores. D-02 accepts this; state it in the fit report's data section with the 252 status.

### Pitfall 13: Gitignored key file
`temp/blunder-check/set8-key-2026-11-16.json` is ignored (`.gitignore:5` `/temp`, verified with `git check-ignore`).
Never `git add -f` it; never read it while the owner is still labelling (blind set).

## Code Examples

### Python twin dispatch (sketch)
```python
def material_loss(facts: FacepalmFacts, model: FacepalmModel) -> float | None:
    if facts.mate_ply is not None and facts.mate_ply <= LINE_DEPTH:
        return float(MATE_LOSS)
    played_3 = material_at_depth(facts.played_material, LINE_DEPTH)
    if played_3 is None:
        return None  # D-03: every input needs depth 3
    if model.material_input == "depth_3":
        return loss_feature(-played_3, facts.mate_ply, loss_floor=model.loss_floor)
    series = loss_series(facts.played_material, facts.mate_ply, loss_floor=model.loss_floor)
    return aggregate(series, model.material_input)
```

### Regression test that pins the refactor before the labels exist
```python
# tests/scripts/test_fit_facepalm.py
def test_depth_3_fit_reproduces_the_2026_11_15_constants(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(fit_facepalm, "FACEPALM_MODEL", PHASE_254_MODEL)  # frozen in tests/facepalm_models.py
    argv = ["--features", str(FEATURES_2026_11_15), "--out", str(tmp_path / "r.md"),
            "--material-input", "depth_3", "--check-constants"]
    assert fit_facepalm.main(argv) == fit_facepalm.EXIT_OK
```
Holds because the 2026-11-15 rows have no NULL spread or best prob and integer losses make the two gate candidates
identical. Freeze the 254 model (`intercept -0.7583`, played `-0.4146`, spread `-0.2585`, loss `1.0129`, missed `0.0891`,
best_prob `1.0405`, split, floor None, cap 5, mate 5, bpfm) as `PHASE_254_MODEL` next to `PHASE_250_MODEL`.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Stored `facepalm_score` column | Query-time `facepalm_expr` | Phase 254 (R2, 2026-11-15) | A refit is a constants deploy |
| Material read at depth 3 | Aggregate over depths 1-9 (this phase) | Phase 256 | Missed gain expected to earn a real coefficient |
| NULL best prob read as 0 on pure misses | Unscored (D-04) | Phase 256 | 0.68% of scored prod rows leave pool and filter |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | First stable: onset discount `MATERIAL_DECAY_RATIO**index`, fallback = last known value discounted by its index | Pattern 2 | Probe numbers (0.872) not reproduced; candidate ranks differently. Low impact: decaying mean is the working choice |
| A2 | A mate within `LINE_DEPTH` short-circuits every input to today's mate values | Pattern 2 | If the owner meant "mate value from the mate ply on" only, 7 + 7 label rows move; confirm at D-13 |
| A3 | Per-depth floor/cap (not on the aggregate) | Pattern 2 | Alternative changes rows with negative mid-line gains only |
| A4 | Numeric gate uses `>=` | Pattern 6 | `>` would treat a constant one-pawn loss as not losing |
| A5 | Names `MaterialInput`, `FACEPALM_MATERIAL_INPUT`, `FACEPALM_LOSS_GATE`, `MATERIAL_DECAY_RATIO`, `REASON_NO_BEST_PROB`, `PHASE_254_MODEL` | Patterns | Cosmetic |
| A6 | Report: comparison table + chosen input's stages first, other inputs after; owner section via `--labels` | Pattern 4 | Cosmetic |

## Open Questions

1. **Mate short-circuit (A2).** Recommendation: implement the short-circuit and list it in the report's chosen-model
   section so the owner sees it at D-13.
2. **What counts as a D-08 disagreement?** Recommendation: the input with the highest set-8 AUC differs from the CV
   choice by more than `AUC_TIE_TOLERANCE`; the report flags it and the owner decides.
3. **252 state at execution.** Unknown until then (252-06 has no SUMMARY on 2026-11-16). Record it in the fit report.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Dev PostgreSQL (docker `flawchess-dev-db-1`) | SQL twin parity tests | ✓ | 18.6 | — |
| uv | All commands | ✓ | 0.10.9 | — |
| onnxruntime (maia-inference group) | Feature pull, calibration oddness | ✓ | 1.29.0 | `--oddness-sample 0` for calibration |
| Prod tunnel `bin/prod_db_tunnel.sh` | Features, calibration | script present; orchestrator only | — | none (blocking for the refit plan) |
| Owner labels for set 8 | D-01 | ✗ (0 of 60 on 2026-11-16) | — | none; code plans can run before |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (xdist), per-worker cloned PostgreSQL DB (`tests/conftest.py`) |
| Config file | `pyproject.toml` |
| Quick run command | `uv run pytest -n auto tests/services/test_facepalm_score.py tests/services/test_facepalm_material.py tests/services/test_facepalm_owner_fixtures.py tests/scripts/test_fit_facepalm.py tests/scripts/test_decaying_mean.py` (today's four existing files: 170 passed in 23 s) |
| Full suite command | `uv run pytest -n auto -x` plus the CLAUDE.md pre-merge gate |

### Decision → Test Map
| ID | Behavior | Type | Command | Exists? |
|----|----------|------|---------|---------|
| D-03 | Every input unscored when played[3] unknown and no mate within 3 | unit | `pytest tests/services/test_facepalm_material.py -k coverage` | ❌ Wave 0 |
| D-06 | Series, decaying mean, first stable, mate rules, odd slots only, NULL skipping | unit | `pytest tests/services/test_facepalm_material.py` | ❌ Wave 0 |
| D-06 | SQL twin parity for every input x gate x shape, NULLs and varied arrays | integration (DB) | `pytest tests/services/test_facepalm_score.py -k parity` | partial (depth-3 grid only) |
| D-06 | `facepalm_expr` over seeded stored facts equals the Python twin for aggregate models | integration (DB) | `pytest tests/services/test_facepalm_score.py -k stored_facts` | partial |
| D-04 | NULL best prob on a no-loss bpfm row: None in both twins; losing row and additive form unchanged | unit + DB | `pytest tests/services/test_facepalm_score.py -k best_prob` | ❌ (existing test asserts the old behaviour) |
| D-05/D-12 | Per-spec exclusion and counts; NULL-spread pure miss kept under gated form | unit | `pytest tests/scripts/test_fit_facepalm.py -k exclusion` | ❌ Wave 0 |
| D-07/D-09 | Input choice by AUC, share, then preference order | unit | `pytest tests/scripts/test_fit_facepalm.py -k material_input` | ❌ Wave 0 |
| D-08 | Hold-out pipeline on sets 1-7, scored on set 8, per input | unit | `pytest tests/scripts/test_fit_facepalm.py -k holdout` | ❌ Wave 0 |
| D-11 | Gate candidates in stage 2; `loses()` semantics in both twins | unit + DB | `pytest -k gate` | ❌ Wave 0 |
| D-12 (254) | Defaults reproduce the Phase 250 score | unit | `pytest tests/services/test_facepalm_score.py::test_new_twin_reproduces_phase_250_score` | ✅ |
| refactor | Forced depth_3 fit reproduces the 2026-11-15 constants | script | `pytest tests/scripts/test_fit_facepalm.py -k 2026_11_15` | ❌ Wave 0 |
| D-10 | Shipped constants reproduce from the new committed TSV (`--check-constants` exit 0) | script | new test on the new TSV, after the paste | ❌ (release plan) |
| D-13 | Owner fixtures carry arrays; outcome under the new model pinned | unit + DB | `pytest tests/services/test_facepalm_owner_fixtures.py` | partial (scalars, old outcome) |
| calibration | `BlunderRecord` arrays, cache v4 refuses v3 | unit | `pytest tests/scripts/test_blunder_check_calibration.py` | partial |
| parity | `decaying_mean.py` (sampler) equals the app aggregate where definitions agree | unit | `pytest tests/scripts/test_decaying_mean.py` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** the quick run command above (plus `ty` on touched files).
- **Per wave merge:** `uv run pytest -n auto -x`.
- **Phase gate:** the full CLAUDE.md pre-merge gate, including `scripts/check_function_size.py app/ --fail-over-depth 4`.
- Prove the WR-01 / WR-03 tests by reverting each fix and watching them fail (project rule for gap closures).

### Wave 0 Gaps
- [ ] `tests/services/test_facepalm_material.py`: series, aggregates, mate rules, the queen-trade best line
      `(1, 1, 1, 1, 10, 10, 1, 1, 1)` (decaying mean with cap 5: (1 + 0.5 + 0.25*5 + 0.125 + 0.0625) / 1.9375), the
      `-3, -3, 0, ...` early-swing row, arrays that stop at depth 3 / 5, garbage in even slots.
- [ ] Parity grid for aggregate models in `test_facepalm_score.py` (separate grid with varied arrays rather than
      multiplying the existing 6,048-row grid by every input and gate).
- [ ] `PHASE_254_MODEL` in `tests/facepalm_models.py` and the 2026-11-15 reproduction test.
- [ ] Synthetic facts writer in `test_fit_facepalm.py` fills all nine slots (varied across depths) and set 8.

## Security Domain

`security_enforcement` is absent from `.planning/config.json`, so enabled. Surface is small: no endpoint, schema or
migration change.

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no (readers keep `GameFlaw.user_id` scoping) | existing IDOR guards unchanged |
| V5 Input Validation | yes (operator TSV parsing) | `csv.DictReader`, `_opt_int` / `_opt_float`, FitError on a foreign file |
| V6 Cryptography | no | — |

| Pattern | STRIDE | Mitigation |
|---------|--------|------------|
| Accidental prod write from features / calibration | Tampering | `make_readonly_engine` (read-only transactions) |
| SQL injection via the expression | Tampering | Only model constants enter, bound as parameters by SQLAlchemy; no user input |
| Heavier expression slows drill / library queries | Denial of service | Unrolled CASE adds arithmetic only; optionally re-run the `EXPLAIN (ANALYZE)` check of `reports/blunder-check/facepalm-expression-prod-check.md` after deploy |
| Blind set-8 key disclosed | Information disclosure | Key stays in gitignored `temp/` |

## Project Constraints (from CLAUDE.md)

- `Literal` types for fixed value sets (`MaterialInput`, gate modes on the CLI); no bare `str`.
- ty clean (`app/ tests/ scripts/`), explicit return types, `Sequence[...]` for covariant parameters, `# ty: ignore[rule]` only when unfixable.
- Nesting depth <= 4 in `app/` (gated); keep the new helpers small (one per series / aggregate / SQL builder).
- No magic numbers: named constants for the decay ratio, gate candidates, set ids, seed best probability.
- Comment bug fixes at the fix site (WR-01 and WR-03 explain what broke and why).
- Sentry rule applies only to `app/services` except blocks; the new module has no `except`.
- Pre-merge gate before the squash-merge; changelog bullet under `## [Unreleased]` (`CHANGELOG.md:9`).
- Never run `bin/reset_db.sh`; never read `.env`; deploy only via `bin/deploy.sh` / `/deploy` (owner's call).
- Work only inside the phase scope; IN-01..IN-03 of the 254 review are not part of this phase.

## Sources

### Primary (HIGH confidence, read this session)
- `app/services/facepalm_score.py` (whole file), `app/services/blunder_check_rules.py:40-114`, `app/services/line_material.py`,
  `app/models/game_flaw.py:1-165`
- `scripts/blunder_check/fit_facepalm.py` (whole file), `facepalm_features.py` (whole file), `decaying_mean.py`,
  `sample.py` (record, cache, loader), `spot_check.py:470-530`, `metrics.py:84-205`
- `tests/services/test_facepalm_score.py`, `tests/scripts/test_fit_facepalm.py`, `tests/scripts/test_decaying_mean.py`,
  `tests/services/facepalm_owner_fixtures.py`, `tests/services/test_facepalm_owner_fixtures.py`, `tests/facepalm_seed.py`,
  `tests/facepalm_models.py`
- `reports/blunder-check/facepalm-fit-2026-11-15.md`, the features TSV and label TSV headers, `facepalm-expression-prod-check.md`
- 254 REVIEW (WR-01, WR-03), REVIEW-DISPOSITION, CONTEXT, 254-11 SUMMARY / PLAN, quick 261116-mco SUMMARY, the seed
- Local probes: SQLAlchemy compile output for Float vs NUMERIC division; counts over the 2026-11-15 TSV; owner fixture arrays

### Secondary / Tertiary
- None. No web research was needed for an in-repo phase.

## Metadata

**Confidence breakdown:**
- Code map and edit sites: HIGH (files read, line numbers quoted)
- Twin design (all inputs, unrolled SQL): HIGH (compile behaviour verified, parity argument from exact arithmetic)
- First-stable definition and mate short-circuit: MEDIUM (owner-facing choices, logged as A1 / A2)
- Pitfalls: HIGH (each traced to a line)

**Research date:** 2026-11-16
**Valid until:** until the next change to `facepalm_score.py` or `fit_facepalm.py` (stable otherwise)
