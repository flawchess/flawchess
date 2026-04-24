---
phase: 63-findings-pipeline-zone-wiring
plan: 03
subsystem: backend/schemas
tags: [python, pydantic, literal-types, schemas, insights, endgame, tdd]

# Dependency graph
requires:
  - "63-01 — Zone/Trend/SampleQuality/Window/MetricId/SubsectionId Literal aliases in app/services/endgame_zones.py"
provides:
  - "app/schemas/insights.py — FilterContext, SubsectionFinding, EndgameTabFindings Pydantic v2 models"
  - "FlagId Literal (4 values per D-09): baseline_lift_mutes_score_gap, clock_entry_advantage, no_clock_entry_advantage, notable_endgame_elo_divergence"
  - "SectionId Literal (4 values): overall, metrics_elo, time_pressure, type_breakdown"
  - "Re-exports of Zone/Trend/SampleQuality/Window/MetricId/SubsectionId from endgame_zones (single import path for Plan 04 consumers)"
  - "27 schema tests in tests/test_insights_schema.py"
affects:
  - "63-04 (compute_findings): will import FilterContext, SubsectionFinding, EndgameTabFindings and emit findings; NaN-serialisation-to-null contract is now testable"
  - "Phase 65 (LLM endpoint): field names are LOCKED — renaming forces a prompt revision"
  - "Phase 67 (regression test): findings_hash stability depends on declaration order fixed here"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pydantic v2 re-export idiom: `from X import Name as Name` so ty and ruff treat re-exports as intentional (no unused-import warnings, no redeclaration)"
    - "`Field(default_factory=list)` for mutable list defaults (Pydantic v2 disallows bare `[]` as class-body default)"
    - "Plain `float` field for value (no `Field(ge=...)`) so NaN round-trips as JSON null for the empty-window convention"
    - "`__all__` as explicit re-export manifest — documents the 11-name public surface for star imports"

key-files:
  created:
    - "app/schemas/insights.py (186 lines)"
    - "tests/test_insights_schema.py (325 lines, 27 tests)"
  modified: []

key-decisions:
  - "as_of typed as datetime.datetime (not str). Critical-guidelines from the executor prompt and PATTERNS.md §`insights.py` module structure both specify datetime. The plan's inline action code sample showed `str` but Pydantic serialises datetime to ISO-8601 in model_dump_json — same on-wire shape, with tighter input validation."
  - "Used the `from endgame_zones import Name as Name` idiom (not `__all__` alone) so ty/ruff see the re-exports as intentional. `__all__` is still declared for star-import hygiene; the two belts-and-braces confirm both at import-time (the `as Name` annotation) and at introspection-time (the __all__ list)."
  - "FilterContext.color documented with a three-point caveat docstring noting (a) not forwarded to endgame_service, (b) not fed to LLM prompt per INS-03, (c) wiring is a Plan 63-04 concern. Schema stays faithful to the user's filter state; the downstream consumer is responsible for dropping it."

patterns-established:
  - "Schema module layout: module docstring citing requirements -> stdlib imports -> pydantic imports -> re-imports with `Name as Name` idiom -> `__all__` -> module-owned Literal aliases -> BaseModel classes."
  - "SubsectionFinding docstring lists the empty-window convention verbatim so every future reader (including the Phase 65 prompt-assembly author) sees the null-value contract at the top of the model."

requirements-completed:
  - FIND-01
  - FIND-05

# Metrics
duration: ~6min
completed: 2026-04-20
---

# Phase 63 Plan 03: Insights Schema Module Summary

**Pydantic v2 schemas for the endgame findings pipeline: FilterContext, SubsectionFinding, EndgameTabFindings, plus FlagId (4 D-09 values) and SectionId (4 CONTEXT.md specifics values) Literals, plus re-exports of Zone/Trend/SampleQuality/Window/MetricId/SubsectionId from endgame_zones.**

## Performance

- **Started:** 2026-04-20T18:46:00Z (approx — wave 2 kickoff)
- **Completed:** 2026-04-20T18:50:22Z
- **Tasks:** 1 (TDD: RED + GREEN, no REFACTOR needed)
- **Files created:** 2 (app/schemas/insights.py, tests/test_insights_schema.py)
- **Files modified:** 0

## Accomplishments

### Schema module line count and field count per class

| Class               | Fields | Optional fields                                  |
| ------------------- | -----: | ------------------------------------------------ |
| `FilterContext`     |      6 | all 6 have defaults (recency / opponent_strength / color / time_controls / platforms / rated_only) |
| `SubsectionFinding` |     12 | 2 default to None (parent_subsection_id, dimension) |
| `EndgameTabFindings`|      5 | none — all required on construction              |

Module totals: 186 lines, 2 module-owned Literal aliases (FlagId, SectionId), 6 re-exported Literal aliases, 3 BaseModel classes.

### FlagId contents confirmed (D-09 verbatim)

The four flag IDs are locked. They appear in `FlagId` exactly as CONTEXT.md D-09 lists:

```python
FlagId = Literal[
    "baseline_lift_mutes_score_gap",
    "clock_entry_advantage",
    "no_clock_entry_advantage",
    "notable_endgame_elo_divergence",
]
```

`tests/test_insights_schema.py::TestFlagIdAndSectionId::test_flag_id_has_exactly_four_values` asserts `set(get_args(FlagId)) == {...}` so any drift trips the test immediately.

### Sample `model_dump_json()` output (shape Plan 04 will hash)

A two-finding payload covering the happy path (first finding, rich sample) and the empty-window convention (second finding, NaN -> null):

```json
{
  "as_of": "2026-04-20T12:00:00Z",
  "filters": {
    "recency": "3months",
    "opponent_strength": "any",
    "color": "white",
    "time_controls": ["blitz"],
    "platforms": ["chess.com"],
    "rated_only": true
  },
  "findings": [
    {
      "subsection_id": "overall",
      "parent_subsection_id": null,
      "window": "all_time",
      "metric": "score_gap",
      "value": 0.08,
      "zone": "typical",
      "trend": "stable",
      "weekly_points_in_window": 45,
      "sample_size": 420,
      "sample_quality": "rich",
      "is_headline_eligible": true,
      "dimension": null
    },
    {
      "subsection_id": "endgame_elo_timeline",
      "parent_subsection_id": null,
      "window": "all_time",
      "metric": "endgame_elo_gap",
      "value": null,
      "zone": "typical",
      "trend": "n_a",
      "weekly_points_in_window": 0,
      "sample_size": 0,
      "sample_quality": "thin",
      "is_headline_eligible": false,
      "dimension": {
        "platform": "chess.com",
        "time_control": "blitz"
      }
    }
  ],
  "flags": ["clock_entry_advantage"],
  "findings_hash": ""
}
```

**Observations for Plan 04:**

- `value: float('nan')` serialises to JSON `null`. No `Field(ge=...)` on `value`, so NaN is accepted at construction time. Plan 04's hash post-processor can rely on this.
- `datetime.datetime` with UTC tzinfo serialises to ISO-8601 with a trailing `Z`. `findings_hash` excludes `as_of`, so day-to-day hash stability is preserved.
- `dimension: dict[str, str] | None` serialises as-is when populated; no sorting — Plan 04's `json.dumps(sort_keys=True)` step will sort the inner dict for canonical form.
- Field order matches the locked declaration order in all three models (confirmed by `test_field_order_locked` per class).

### Field-order decisions vs RESEARCH.md

None. Field order in every class matches RESEARCH.md §"SubsectionFinding and EndgameTabFindings Schemas" and §"FilterContext Schema" exactly:

- `FilterContext`: recency, opponent_strength, color, time_controls, platforms, rated_only
- `SubsectionFinding`: subsection_id, parent_subsection_id, window, metric, value, zone, trend, weekly_points_in_window, sample_size, sample_quality, is_headline_eligible, dimension
- `EndgameTabFindings`: as_of, filters, findings, flags, findings_hash

The plan action code specified `as_of: str` with a comment "ISO date"; the executor prompt's `<critical_guidelines>` specified `as_of (datetime)` and PATTERNS.md §`insights.py` module structure also said `as_of: datetime`. I used `datetime.datetime` — narrower input validation, identical JSON output shape (ISO-8601 string).

### Test coverage (27 tests, all passing)

| Test class                        | Tests | Coverage                                                       |
| --------------------------------- | ----: | -------------------------------------------------------------- |
| `TestFilterContext`               |     6 | defaults, populated, 3x Literal-reject, field-order-locked     |
| `TestSubsectionFinding`           |     7 | required-only, populated, NaN-round-trip, 3x Literal-reject, field-order-locked |
| `TestEndgameTabFindings`          |     4 | minimal, populated, flag-reject, field-order-locked            |
| `TestFlagIdAndSectionId`          |     2 | FlagId has 4 values, SectionId has 4 values                    |
| `TestReExportsFromEndgameZones`   |     6 | Zone, Trend, SampleQuality, Window, MetricId, SubsectionId all `is` the endgame_zones aliases |
| `TestModuleAll`                   |     1 | `__all__` contains the 11 expected names                       |
| (module-level)                    |     1 | NaN sanity for callers                                         |

## Task Commits

1. **RED — Task 1: Failing tests for insights schemas** - `4364391` (test)
2. **GREEN — Task 1: Implement insights schema module** - `1ad4e5a` (feat)

No REFACTOR commit was created — the implementation is a pure schema file with no duplication to collapse and no refactoring opportunity.

## Files Created/Modified

- `app/schemas/insights.py` (186 lines) — new module. Module docstring references FIND-01 / FIND-05, lock rationale, and the declaration-order constraint for findings_hash. Imports are: `datetime`, `typing.Literal`, `pydantic.BaseModel/Field`, plus 6 explicit `from app.services.endgame_zones import X as X` re-exports. `__all__` declares 11 names (3 models + 2 module-owned Literals + 6 re-exports).
- `tests/test_insights_schema.py` (325 lines, 27 tests) — new file. 7 TestClass suites plus one module-level test. Tests use `pytest.raises(ValidationError)` for Literal rejection, `json.loads(model_dump_json())` for NaN-serialisation round-trip, `typing.get_args` for Literal introspection, and `is` identity checks for re-export verification.

## Decisions Made

- **as_of typed as datetime.datetime** — The plan action code sample showed `as_of: str  # ISO date`; the executor prompt `<critical_guidelines>` and PATTERNS.md both specified `datetime`. Chose `datetime` for tighter input validation. Pydantic v2 serialises `datetime` to ISO-8601 string in `model_dump_json` automatically — identical on-wire shape, and callers passing a string still work via Pydantic's built-in coercion. Acceptance criteria verify command (`as_of='2026-04-20'`) would have passed under either type; passing `datetime.datetime(2026, 4, 20, tzinfo=datetime.timezone.utc)` works in both the sample script (updated to use datetime) and the tests.

- **Explicit `from endgame_zones import Name as Name` re-export idiom** — Rather than relying solely on `__all__` for re-export intent, every re-exported name uses the `as Name` form. This is the PEP 484 explicit-re-export idiom: it tells type-checkers (ty) and linters (ruff) that the import is intentional public surface, avoiding both unused-import warnings and the need to redeclare the aliases (which would violate the "Plan 01 owns the source" principle). `__all__` is still declared for star-import hygiene and for `TestModuleAll` to assert against.

- **value: float with no Field(ge=...) constraint** — The empty-window convention requires `float('nan')` to round-trip as JSON null. A `Field(ge=...)` constraint would reject NaN at construction time, breaking the contract Plan 04 relies on. The model stays permissive on `value`; zone/trend/sample_quality Literals provide the semantic constraints that matter.

- **FilterContext.color three-point caveat docstring** — The docstring spells out (1) color is not forwarded to endgame_service (which has no color filter), (2) color is not fed to the LLM prompt per INS-03, (3) Plan 63-04 is responsible for dropping it before calling endgame_service. This makes the "schema-vs-consumer responsibility" split explicit at the point the confused reader looks first.

## Deviations from Plan

**Minor — as_of type tightening (datetime vs str).** The plan action code sample showed `as_of: str  # ISO date, e.g. "2026-04-20"` but the executor prompt's `<critical_guidelines>` and PATTERNS.md §`insights.py` module structure both specified `datetime`. I honored the two authoritative sources. No behavioural difference on the JSON wire format; stricter input validation.

Otherwise: plan executed exactly as written. No auto-fixes, no blocking issues, no architectural changes needed.

## Issues Encountered

None. TDD cycle ran cleanly: RED phase failed with `ModuleNotFoundError` as expected (module didn't exist), GREEN phase passed all 27 tests on first run, no iteration needed. ty and ruff clean on first run.

## User Setup Required

None. Backend-only pure-Python schema definition.

## Next Wave Readiness

Plan 63-04 (`insights_service.compute_findings`) can import:
- `FilterContext`, `SubsectionFinding`, `EndgameTabFindings` from `app.schemas.insights`
- `FlagId`, `SectionId` from `app.schemas.insights`
- `Zone`, `Trend`, `SampleQuality`, `Window`, `MetricId`, `SubsectionId` from `app.schemas.insights` (single import path — no need to reach into `endgame_zones`)

The NaN-null-serialisation contract is verified by `test_nan_value_serializes_to_json_null`. Plan 04's hash computation can rely on it.

No blockers or concerns.

## Self-Check

Verifying every claim in this SUMMARY:

- FOUND: app/schemas/insights.py (186 lines, confirmed via wc -l)
- FOUND: tests/test_insights_schema.py (325 lines, 27 tests, confirmed via wc -l and pytest -v)
- FOUND: commit 4364391 in git log (RED — test)
- FOUND: commit 1ad4e5a in git log (GREEN — feat)
- PASS: `uv run pytest tests/test_insights_schema.py -v` -> 27 passed in 0.11s
- PASS: `uv run ty check app/ tests/` -> All checks passed
- PASS: `uv run ruff check .` -> All checks passed
- PASS: Plan verify command (`uv run python -c "from app.schemas.insights import EndgameTabFindings, ...; print(findings.model_dump_json())"`) -> prints JSON
- PASS: Re-export identity check (`from app.schemas.insights import MetricId as A; from app.services.endgame_zones import MetricId as B; assert A is B`) -> exits 0
- PASS: Star import (`from app.schemas.insights import *`) -> exits 0
- PASS: FlagId has exactly 4 D-09 values (asserted via `typing.get_args` in test)
- PASS: SectionId has exactly 4 values (asserted via `typing.get_args` in test)
- PASS: Field order locked in all three classes (asserted via `model_fields.keys()` in per-class test)

## Self-Check: PASSED

---
*Phase: 63-findings-pipeline-zone-wiring*
*Completed: 2026-04-20*
