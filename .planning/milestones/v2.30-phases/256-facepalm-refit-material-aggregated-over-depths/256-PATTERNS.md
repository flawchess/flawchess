# Phase 256: Facepalm Refit on Material Aggregated over Depths - Pattern Map

**Mapped:** 2026-11-16
**Files analyzed:** 17 (2 new, 15 modified)
**Analogs found:** 17 / 17 (every analog is git-tracked; verified with `git ls-files`)

This phase is a refactor of existing code, so most "analogs" are the file itself (extend in place,
keep its conventions). The one genuinely new module (`app/services/facepalm_material.py`) copies
`scripts/blunder_check/decaying_mean.py` for the Python side and the `_loss_sql` / `_missed_sql`
builders of `app/services/facepalm_score.py` for the SQL side.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `app/services/facepalm_material.py` (NEW) | service (pure) | transform | `scripts/blunder_check/decaying_mean.py` (Python) + `app/services/facepalm_score.py:304-330` (SQL) | exact |
| `app/services/blunder_check_rules.py` | config | n/a | itself `:58-100` (`MaterialForm` / `SpreadForm` / `FACEPALM_*` block) | exact |
| `app/services/facepalm_score.py` | service (twins) | transform + SQL expr | itself | exact |
| `scripts/blunder_check/decaying_mean.py` | utility | transform | re-export from `facepalm_material.py` | exact |
| `scripts/blunder_check/fit_facepalm.py` | script (batch fit) | batch / file-I/O | itself (`select_spread_form`, `choose_candidate`, `_holdout`) | exact |
| `scripts/blunder_check/sample.py` | script (cache) | file-I/O | itself `:78-82`, `:200-225`, `:528-544` | exact |
| `scripts/blunder_check/render.py`, `spot_check.py` | script (report) | transform | read `played_3` / `best_3` as properties, no change if kept | exact |
| `app/services/maia_flaw_scoring.py` (`_row_score` `:740-752`) | service | transform | itself | exact |
| `tests/services/test_facepalm_material.py` (NEW) | test (unit) | — | `tests/scripts/test_decaying_mean.py` | exact |
| `tests/services/test_facepalm_score.py` | test (unit + DB parity) | — | itself (`_sql_scores`, `_assert_parity`, `test_gated_spread_null_with_zero_loss`) | exact |
| `tests/scripts/test_fit_facepalm.py` | test | — | itself | exact |
| `tests/scripts/test_decaying_mean.py` | test | — | itself | exact |
| `tests/facepalm_models.py` | test fixture | — | `PHASE_250_MODEL` | exact |
| `tests/facepalm_seed.py` | test fixture | — | itself | exact |
| `tests/services/facepalm_owner_fixtures.py` / `test_facepalm_owner_fixtures.py` | test fixture | — | itself | exact |
| `tests/scripts/test_blunder_check_calibration.py` (`_blunder` helper) | test | — | itself | exact |
| `CHANGELOG.md` | docs | — | `## [Unreleased]` at `:9` | exact |
| `reports/blunder-check/facepalm-features-<date>.tsv`, `facepalm-fit-<date>.md` | report artifacts | operator output | `facepalm-features-2026-11-15.tsv`, `facepalm-fit-2026-11-15.md` | exact |

## Pattern Assignments

### `app/services/facepalm_material.py` (NEW, pure service, transform)

**Analog (Python):** `scripts/blunder_check/decaying_mean.py` (whole file, 90 lines). Copy structure, then
adapt: series become tuples ordered by depth (not dicts), per-depth loss/gain take `loss_floor` /
`missed_floor` / `missed_cap` / `missed_mate` from the model, and a mate within `LINE_DEPTH` is handled by
the caller (short-circuit, RESEARCH Pattern 2 rule 2).

Imports + constants (`decaying_mean.py:19-35`):
```python
from __future__ import annotations

from collections.abc import Mapping, Sequence

from app.services.blunder_check_rules import (
    FACEPALM_MISSED_CAP,
    FACEPALM_MISSED_MATE,
    LOSS_CAP,
    MATE_LOSS,
)
from app.services.line_material import LINE_LOSS_DEPTHS, material_at_depth

# Odd depths only: even slots are mid-exchange values (Phase 254 D-17).
DECAY_DEPTHS: tuple[int, ...] = LINE_LOSS_DEPTHS
# Weight ratio between consecutive odd depths, fixed by the owner (not fitted).
DECAY_RATIO: float = 0.5
DECAY_WEIGHTS: tuple[float, ...] = tuple(DECAY_RATIO**index for index in range(len(DECAY_DEPTHS)))
```
Move `DECAY_RATIO` into `blunder_check_rules.py` as `MATERIAL_DECAY_RATIO` and import it here.

Per-depth series loop (`decaying_mean.py:46-53`), the shape to keep (early `continue`, depth <= 3):
```python
    for depth in DECAY_DEPTHS:
        if played_mate_ply is not None and played_mate_ply <= depth:
            series[depth] = MATE_LOSS
            continue
        material = material_at_depth(played_material, depth)
        series[depth] = None if material is None else min(LOSS_CAP, max(0, -material))
```
Note the differences to resolve: today's helper floors loss at 0 and gain at 0 unconditionally; the app
version must apply `model.loss_floor` / `model.missed_floor` (None = unfloored) exactly like
`loss_feature` / `missed_feature` (`facepalm_score.py:181-222`).

Aggregate (`decaying_mean.py:80-90`), copy as is for `decaying_mean`:
```python
def decaying_mean(series: Mapping[int, int | None]) -> float | None:
    total = 0.0
    weight_sum = 0.0
    for depth, weight in zip(DECAY_DEPTHS, DECAY_WEIGHTS, strict=True):
        value = series.get(depth)
        if value is None:
            continue
        total += weight * value
        weight_sum += weight
    return None if weight_sum == 0.0 else total / weight_sum
```
`first_stable`: sketch in RESEARCH Pattern 2 (lines 387-395); assumption A1.

**Analog (SQL):** `app/services/facepalm_score.py:304-330`. Copy the NULL-guard-before-LEAST rule and the
1-based slot index:
```python
def _loss_sql(columns: FacepalmColumns, model: FacepalmModel) -> ColumnElement[Any]:
    played_3 = columns.played_material[LINE_DEPTH]
    capped = func.least(-played_3, LOSS_CAP)
    if model.loss_floor is not None:
        capped = func.greatest(capped, model.loss_floor)
    return case(
        (columns.mate_ply <= LINE_DEPTH, literal(float(MATE_LOSS))),
        (played_3.is_(None), null()),
        else_=capped,
    )
```
```python
def _missed_sql(columns, model):
    played_3 = columns.played_material[LINE_DEPTH]
    best_3 = columns.best_material[LINE_DEPTH]
    played_positive = case((played_3 > 0, played_3), else_=literal(0))
    raw = best_3 - played_positive
    if model.missed_floor is not None:
        raw = func.greatest(raw, model.missed_floor)
    return case(
        (columns.best_mate_ply <= LINE_DEPTH, literal(float(model.missed_mate))),
        (best_3.is_(None), literal(0.0)),
        (played_3.is_(None), literal(0.0)),
        else_=func.least(raw, model.missed_cap),
    )
```
Generalise `LINE_DEPTH` to a `depth` parameter, unroll over `DECAY_DEPTHS`, keep every operand
`Float`-typed (`cast(..., Float)`, `literal(w, Float)`) so PostgreSQL divides in double precision
(RESEARCH Pattern 3 / Pitfall 4). Imports to copy: `facepalm_score.py:58`
`from sqlalchemy import ColumnElement, Float, case, func, literal, null, type_coerce` (+ `cast`, `and_`).
No `except` blocks, so no Sentry. Must not import from `scripts.*`.

---

### `app/services/blunder_check_rules.py` (config)

**Analog:** itself, `:83-97`. Add `MaterialInput`, `FACEPALM_MATERIAL_INPUT`, `FACEPALM_LOSS_GATE`,
`MATERIAL_DECAY_RATIO` right after the existing Literal/selector pair, same comment style:
```python
MaterialForm = Literal["combined", "split"]
SpreadForm = Literal["always", "loss_only", "best_prob_for_misses"]
FACEPALM_MATERIAL_FORM: MaterialForm = "split"
# Coefficient of the missed term in the split form (0.0 = the term is not in the model).
FACEPALM_MISSED_COEF: float = 0.0891
```
Release step: update the provenance comment block `:67-72` (features TSV, report name, and the exact
`--check-constants` command if forced flags were used) and the `FACEPALM_SCORE_MIN` comment `:55-58`.

---

### `app/services/facepalm_score.py` (twins)

**Analog:** itself. Edit sites (line numbers from the current file):
- `:104-129` `FacepalmModel`: add `material_input: MaterialInput = "depth_3"` and `loss_gate: float | None = None`
  after `pre_spread_coef`, defaults reproduce today (D-12 of 254; `PHASE_250_MODEL` relies on it).
- `:133-147` `FACEPALM_MODEL`: add the two new constants.
- `:150-161` `FacepalmFacts`: `played_3` / `best_3` -> `played_material` / `best_material`
  (`Sequence[int | None] | None`, mirroring `FacepalmColumns:164-178`); keep `played_3` / `best_3` as
  `@property` via `material_at_depth(..., LINE_DEPTH)`.
- `:244-253` `_spread_term` (WR-01): replace `loss <= 0` with `not loses(loss, model.loss_gate)`; on the
  bpfm pure-miss branch return None when `best_prob is None` and coef != 0. Today:
```python
def _spread_term(model, facts, loss):
    if model.spread_form != "always" and loss <= 0:
        # A pure miss: no reply spread; best_prob_for_misses swaps in the best-move term.
        if model.spread_form == "best_prob_for_misses":
            return _best_prob_term(model, facts.best_prob)
        return 0.0
    if facts.reply_spread is None:
        return None
    return model.spread_coef * facts.reply_spread
```
- `:343-355` `_spread_sql` (WR-01 SQL): `case((loss > 0, spread), else_=pure_miss)` becomes
  `case((_loses_sql(loss, model.loss_gate), spread), else_=_pure_miss_sql(...))`, where `_pure_miss_sql`
  yields `null()` for a NULL best prob. Keep `_best_prob_term` / `_best_prob_sql` (`:237-241`, `:333-340`)
  unchanged for the additive path (`_optional_terms:256-263`, `_optional_sql:358-370`).
- `:266-301` `facepalm_score` and `:373-399` `facepalm_score_sql`: replace the `loss_feature(...)` /
  `_loss_sql` / `missed_feature(...)` / `_missed_sql` calls with a dispatch on `model.material_input`
  (RESEARCH "Python twin dispatch" sketch, lines 656-667). Coverage gate (D-03) stays first.
- `:1-50` docstring: rewrite term rules. Keep "if either side changes, update the other".
- Comment the WR-01 fix at the fix site (CLAUDE.md "Comment bug fixes").

---

### `scripts/blunder_check/decaying_mean.py` (utility)

Keep its sampler API (`loss_series`, `gain_series`, `decaying_mean`, `DECAY_*`; used by
`miss_labels.py`) but import the weights/mean from `app/services/facepalm_material.py` so there is one
implementation. Its docstring `:8` already anticipates this ("The later refit phase may reuse or move it").

---

### `scripts/blunder_check/fit_facepalm.py` (batch fit)

**Analog:** itself. Patterns to copy:

Constants style (`:107-130`), add `MATERIAL_INPUTS` (preference order D-09), `LOSS_GATE_CANDIDATES = (None, 1.0)`,
`REASON_NO_BEST_PROB`, and change `TRAIN_SETS`/`TEST_SET`/`TRAIN_SETS_TEXT`:
```python
MATERIAL_FORMS: tuple[MaterialForm, ...] = ("combined", "split")
SPREAD_FORMS: tuple[SpreadForm, ...] = ("always", "loss_only", "best_prob_for_misses")
MISSED_FLOOR_CANDIDATES: tuple[int | None, ...] = (None, 0)
...
TRAIN_SETS: tuple[str, ...] = ("1", "2", "3", "4", "5", "7")
TEST_SET: str = "6"
TRAIN_SETS_TEXT: str = "1-5 and 7"
...
REASON_NO_SPREAD: str = "NULL reply_spread"
EXCLUSION_REASONS: tuple[str, ...] = (...)
```

`CandidateSpec` (`:511-534`): frozen dataclass with `__post_init__` validation; add
`material_input: MaterialInput` and `loss_gate: float | None` fields with defaults.

Stage builder to copy for the gate candidates (`select_spread_form`, `:1102-1126`): generate specs with
`dataclasses.replace(incumbent.spec, ...)`, `_fit_all`, `_stage_from_fits(..., forced_by=...)`.

Selection rule to reuse (`choose_candidate`, `:999-1028`): AUC within `AUC_TIE_TOLERANCE`, then fair share
within `FAIR_SHARE_TIE_TOLERANCE`, then fewer free coefs. New `choose_material_input` copies the first two
steps and breaks the final tie by `MATERIAL_INPUTS` order (D-09).

Pipeline entry to wrap per input (`run_facts_fit`, `:1192-1225`):
```python
    usable, excluded = split_usable(rows)
    stage1 = select_material_form(usable, settings, material_mode)
    stage2 = select_spread_form(usable, stage1.chosen, settings, spread_mode)
    stage3 = select_pre_inputs(usable, stage2.chosen, settings)
    chosen = stage3[-1].chosen
    return FactsOutcome(..., split=_holdout(usable, lambda part: spec_design_matrix(part, chosen.spec), settings.threshold), ...)
```
Replace `_holdout` (`:809-828`, which refits a spec chosen on all sets, Pitfall 2) by running the same
pipeline on `TRAIN_SETS` rows and scoring `TEST_SET` rows; keep `SplitResult` as the result type.

WR-03 edit sites: `_exclusion_reason` `:318-330` (drop the `reply_spread is None` check from the base
filter), `spec_row_values` `:570-598` (today `spread = _require(row.reply_spread)` runs before
`gated_off = spec.spread_form != "always" and loss <= 0`; read spread only when not gated off),
`_best_prob_value` `:563-567` (`loss > 0` -> `loses(loss, spec.loss_gate)`). Add `_spec_exclusion`
(RESEARCH Pattern 5) and give `CandidateFit` (`:921`) its own rows.

Other sites: `FACTS_REQUIRED_COLUMNS :156-168`, `FitRow :200-217`, `_facts_row :272-288` (read all nine
slots), `score_extras :838-861` (arrays into `FacepalmFacts`), `_split_section :1340-1356` (derive heading
from constants), `_parse_args :1668-1707` (`--material-input`, `--loss-gate` with `Literal` modes,
mirroring `MaterialFormMode` / `SpreadFormMode`).

---

### `scripts/blunder_check/sample.py` (cache, file-I/O)

**Analog:** itself. Bump the cache version with a comment in the same style (`:78-82`):
```python
# Version 3 (Phase 254, D-01): blunder records carry the facepalm FACTS (...) and the report
# scores them with the model in the checkout; a version 2 cache holds a stored score instead and
# no longer loads.
CACHE_VERSION: int = 3
```
`_flaw_row` (`:528-544`) currently shrinks arrays: `played_3=material_at_depth(row[6], LINE_DEPTH)`. Keep
the full arrays on `FlawRow` / `BlunderRecord` (and `to_dict` / `from_dict`), expose `played_3` / `best_3`
as properties for `render.py` / `spot_check.py`. `BlunderRecord.facepalm_score` (`:208-222`) builds
`FacepalmFacts(... played_3=self.played_3, best_3=self.best_3 ...)`: switch to arrays.

### `app/services/maia_flaw_scoring.py` (`_row_score`)

`:740-752` already has the arrays; drop the `material_at_depth(..., LINE_DEPTH)` shrink:
```python
            played_3=material_at_depth(row["played_line_material"], LINE_DEPTH),
            ...
            best_3=material_at_depth(row["best_line_material"], LINE_DEPTH),
```
-> `played_material=row["played_line_material"]`, `best_material=row["best_line_material"]`.

---

### `tests/services/test_facepalm_material.py` (NEW)

**Analog:** `tests/scripts/test_decaying_mean.py:1-40`. Copy the `array(*odd)` helper (builds a 9-slot
array from five odd-depth values, even slots copy the previous odd) and the plain-function test style:
```python
def array(*odd: int | None) -> list[int | None]:
    slots: list[int | None] = []
    for index, value in enumerate(odd):
        slots.append(value)
        if index < len(odd) - 1:
            slots.append(value)
    return slots

def test_weights_derive_from_the_ratio() -> None:
    assert DECAY_DEPTHS == (1, 3, 5, 7, 9)
    assert DECAY_WEIGHTS == (1.0, 0.5, 0.25, 0.125, 0.0625)
```
Cases from RESEARCH Wave 0: queen-trade best line `(1,1,1,1,10,10,1,1,1)`, `-3,-3,0,...` early swing,
arrays stopping at depth 3 / 5, garbage in even slots, played mate ply 3 and 5, best mate ply 0/2/4.

### `tests/services/test_facepalm_score.py` (unit + DB parity)

Reuse `_sql_scores` (`:282-320`, VALUES grid with a typing row, chunked) and `_assert_parity`
(`:323-336`) for a separate aggregate-model grid with varied arrays. Template for the WR-01 regression
(both twins, one row): `test_gated_spread_null_with_zero_loss` `:529-542`:
```python
    row: GridRow = (0.1, None, _material_array(5), None, _material_array(10), None, 0.3, None)
    python_score = facepalm_score(_facts_of(row), lam=1.0, model=model)
    (sql_score,) = await _sql_scores(test_engine, [row], model, 1.0)
    assert sql_score == pytest.approx(python_score, abs=PARITY_TOLERANCE)
```
Split `test_unknown_best_prob_contributes_zero` (`:559-568`): additive model unchanged, bpfm no-loss
row now None, bpfm losing row unchanged (Pitfall 6). Update `_facts` / `_facts_of` / `_facts_of_flaw`
(`:197-260`, `:747-757`) to arrays; `_material_array(slot3)` (`:167`) already exists.
Window 14 tests `:656-691` may need to read the new TSV (Pitfall 10).

### `tests/facepalm_models.py`

Add `PHASE_254_MODEL` next to `PHASE_250_MODEL`, same `Final[FacepalmModel]` + provenance comment:
```python
PHASE_250_MODEL: Final[FacepalmModel] = FacepalmModel(
    intercept=-1.4193,
    played_coef=-0.6629,
    spread_coef=-0.3304,
    loss_coef=1.1570,
    loss_floor=0,
)
```
254 values: intercept -0.7583, played -0.4146, spread -0.2585, loss 1.0129, loss_floor 0, split,
missed 0.0891, missed_floor None, cap 5, mate 5, bpfm, best_prob 1.0405.

### `tests/scripts/test_fit_facepalm.py`

Add the 2026-11-15 reproduction test (RESEARCH lines 672-677), monkeypatching `FACEPALM_MODEL` to
`PHASE_254_MODEL` and forcing `--material-input depth_3 --check-constants`. Synthetic writer
(`FACTS_SETS: int = 7`, fit script `:478` per RESEARCH) must fill all nine slots and include set 8;
update the asserted hold-out heading (`:990`).

### `tests/facepalm_seed.py`, `tests/services/facepalm_owner_fixtures.py`, `tests/scripts/test_blunder_check_calibration.py`

Constructor ripple only (Pitfall 8): `FacepalmFacts(played_3=..., best_3=...)` -> arrays. Owner fixtures
(`facepalm_owner_fixtures.py:1-30`, data-only dataclass `OwnerFixtureFacts(game_id, ply, facts)`) become
constant arrays `[0]*9`/`[3]*9` and `[5]*9`/`[10]*9`. `facepalm_seed.py`: add a named seed best-prob
constant (Pitfall 7).

## Shared Patterns

### Twin parity (Python + SQL)
**Source:** `app/services/facepalm_score.py:44-46`, `:373-399`
**Apply to:** every scoring change (material input, gate, WR-01)
- Every term rule is implemented once in Python and once in SQL; docstring cross-references both.
- NULL handling via explicit `case((x.is_(None), ...))` before `func.least` / `func.greatest`.
- Zero coefficients omit their term at build time in both twins (`_optional_sql:358-370`).
- Final cast: `type_coerce(1.0 / (1.0 + func.exp(-z)), Float(asdecimal=False))`.
- Pinned by `tests/services/test_facepalm_score.py` `_sql_scores` + `_assert_parity`.

### Literal-typed shape selectors
**Source:** `app/services/blunder_check_rules.py:83-85`, `fit_facepalm.py` `MaterialFormMode` / `SpreadFormMode`
**Apply to:** `MaterialInput`, CLI `--material-input` / `--loss-gate` modes. Never bare `str`.

### Frozen dataclasses with validated shape
**Source:** `FacepalmModel` (`facepalm_score.py:104-129`), `CandidateSpec` (`fit_facepalm.py:511-534`)
**Apply to:** new fields on both; validation in `__post_init__` raising `ValueError`.

### Fit selection and reporting
**Source:** `choose_candidate` (`fit_facepalm.py:999-1028`), `_stage_from_fits`, `forced_by` strings
**Apply to:** gate stage, per-input loop, `choose_material_input`.

### Read-only prod access for operator runs
**Source:** `make_readonly_engine` in `scripts/blunder_check/sample.py` (used by `facepalm_features.py`
and `blunder_check_calibration.py`). Operator runs stay orchestrator-inline (prod tunnel).

## No Analog Found

None. `first_stable` (Python and SQL) has no existing implementation; use RESEARCH Pattern 2 / 3
sketches (assumption A1), built in the same style as `decaying_mean`.

## Metadata

**Analog search scope:** `app/services/`, `scripts/blunder_check/`, `tests/services/`, `tests/scripts/`, `tests/`
**Files scanned:** 12
**Pattern extraction date:** 2026-11-16
