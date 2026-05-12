# Phase 84: Data plumbing — per-type cohort p50 + mirror-rate audit — Pattern Map

**Mapped:** 2026-05-12
**Files analyzed:** 7 (5 modified, 2 created)
**Analogs found:** 7 / 7 (every modified file extends or directly mirrors an in-repo pattern from Phase 60 / 63 / 82 / 83)

## File Classification

| File | New/Modified | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|---|
| `app/services/endgame_zones.py` | modified | dataclass extension + constant table | static module-level lookup | self (existing `PerClassBands` dataclass, lines 320-339) | exact (extend existing dataclass + table) |
| `scripts/gen_endgame_zones_ts.py` | modified | codegen emitter | string formatting / file write | self (`_format_per_class_gauge_zones`, lines 67-78) | exact (extend existing emitter clause) |
| `frontend/src/generated/endgameZones.ts` | regenerated | generated TS output | build artifact | self (lines 65-72) | exact (regenerated, not hand-edited) |
| `app/schemas/endgames.py` | modified | Pydantic v2 response schema | wire I/O | `MaterialRow.opponent_score` / `opponent_games` (lines 215-237) | exact (Phase 60 already-shipped pattern; Section 3 mirrors Section 2) |
| `app/services/endgame_service.py` | modified | service-layer accumulator | aggregation / transform | `_compute_score_gap_material` mirror-bucket block (lines 824-855) | exact (per-class adaptation of Phase 60 same-game-symmetry pattern) |
| `tests/services/test_endgame_zones.py` | modified (append) | unit test class | assertion / sanity | `TestRegistrySanity` (lines 192-240) | role-match (registry/dataclass sanity tests) |
| `tests/test_endgame_service.py` | modified (append) | unit test class | assertion / fixture-driven | `TestScoreGapMaterialOpponentBaseline` (lines 1381-1474) | exact (per-class adaptation of Section 2 mirror-identity tests) |
| `84-01-SUMMARY.md` (or similar) | created | inline audit doc | documentation | Phase 83 D-16 ENTRY_EXPECTED_SCORE summary doc | role-match (deferred — planner produces) |

## Pattern Assignments

### `app/services/endgame_zones.py` (dataclass extension, static lookup)

**Analog:** self — extend existing `PerClassBands` dataclass + `PER_CLASS_GAUGE_ZONES` table

**Source-of-truth context (lines 310-339):**
```python
# PER_CLASS_GAUGE_ZONES — per-endgame-class typical bands for Conversion and
# Recovery. Source: reports/benchmarks-2026-05-01.md (260501-s0u benchmark
# calibration v2), pooled p25/p75 per class. Codegen'd to frontend via
# scripts/gen_endgame_zones_ts.py.
@dataclass(frozen=True)
class PerClassBands:
    """Typical [lower, upper] bands for Conversion and Recovery for one endgame type."""

    conversion: tuple[float, float]
    recovery: tuple[float, float]


PER_CLASS_GAUGE_ZONES: Mapping[EndgameClass, PerClassBands] = {
    "rook": PerClassBands(conversion=(0.65, 0.75), recovery=(0.26, 0.36)),
    "minor_piece": PerClassBands(conversion=(0.63, 0.73), recovery=(0.31, 0.41)),
    "pawn": PerClassBands(conversion=(0.67, 0.79), recovery=(0.23, 0.34)),
    "queen": PerClassBands(conversion=(0.73, 0.83), recovery=(0.20, 0.30)),
    "mixed": PerClassBands(conversion=(0.65, 0.75), recovery=(0.28, 0.38)),
    "pawnless": PerClassBands(conversion=(0.70, 0.80), recovery=(0.21, 0.31)),
}
```

**Extension pattern (D-01 + D-03 + D-04):**
- Add one field `p50: tuple[float, float]` to the frozen dataclass — keep field order `(conversion, recovery, p50)` so the dataclass docstring + table layout reads top-down.
- Populate every existing `PerClassBands(...)` row with a `p50=(c, r)` kwarg using the 6 values from D-03 (2dp rounded per Open Question 1 recommendation).
- Comment near the table must read: `"pooled per-class typical centre, source: §6 mean (≈ per-user p50)"` per D-04 wording.

**Type-safety pattern (existing, do not change):**
- `Mapping[EndgameClass, PerClassBands]` annotation stays correct after the value type expands.
- `EndgameClass = Literal[...]` imported from `app.schemas.endgames` — keep this.

**Downstream consumers (do NOT touch):**
- `per_class_zone_spec()` (lines 390-403) reads `bands.conversion` / `bands.recovery` only; safe.
- `assign_per_class_zone()` (lines 406-420) delegates to `per_class_zone_spec()`; safe.

---

### `scripts/gen_endgame_zones_ts.py` (codegen emitter)

**Analog:** self — extend `_format_per_class_gauge_zones()` (lines 67-78)

**Current emitter:**
```python
def _format_per_class_gauge_zones() -> str:
    """Emit the PER_CLASS_GAUGE_ZONES object literal.

    Each class entry has { conversion: [lower, upper], recovery: [lower, upper] }.
    Consumers wrap with colorizeGaugeZones() on the FE side, same as FIXED_GAUGE_ZONES.
    """
    lines: list[str] = []
    for cls, bands in PER_CLASS_GAUGE_ZONES.items():
        c_lo, c_hi = bands.conversion
        r_lo, r_hi = bands.recovery
        lines.append(f"  {cls}: {{ conversion: [{c_lo}, {c_hi}], recovery: [{r_lo}, {r_hi}] }},")
    return "\n".join(lines) + "\n"
```

**Extension pattern (D-02):**
- Unpack `p50_c, p50_r = bands.p50` alongside the existing IQR tuples.
- Append `p50: { conversion: <num>, recovery: <num> }` as a **third key on the same line** (Pitfall 2: line-wrapping triggers whitespace-only diff on every class). Use `f"p50: {{ conversion: {p50_c}, recovery: {p50_r} }}"`.
- Update the docstring to mention the new key.
- Update the comment above `export const PER_CLASS_GAUGE_ZONES` in `_render()` (lines 136-140) to reference the new `p50` key.

**Floating-point formatting (Pitfall 6):**
- The existing IQR emission uses raw f-string interpolation of Python floats (`{c_lo}` → `0.65`, `{r_hi}` → `0.3` after trailing-zero stripping). Be consistent: emit p50 values the same way. 2dp Python floats `0.71`, `0.30` will render as `0.71`, `0.3` — that's the existing convention, do not switch to `:.2f` mid-file.

**CI drift guard (existing, do not touch):**
- `.github/workflows/ci.yml:47-50` runs `uv run python scripts/gen_endgame_zones_ts.py && git diff --exit-code frontend/src/generated/endgameZones.ts`. The regenerated TS file must be committed in the same commit as the Python changes.

---

### `frontend/src/generated/endgameZones.ts` (regenerated output)

**Analog:** self — current emitted shape (lines 65-72)

**Current shape:**
```ts
export const PER_CLASS_GAUGE_ZONES = {
  rook: { conversion: [0.65, 0.75], recovery: [0.26, 0.36] },
  minor_piece: { conversion: [0.63, 0.73], recovery: [0.31, 0.41] },
  pawn: { conversion: [0.67, 0.79], recovery: [0.23, 0.34] },
  queen: { conversion: [0.73, 0.83], recovery: [0.2, 0.3] },
  mixed: { conversion: [0.65, 0.75], recovery: [0.28, 0.38] },
  pawnless: { conversion: [0.7, 0.8], recovery: [0.21, 0.31] },
} as const;
```

**Expected post-regeneration shape (D-02):**
```ts
export const PER_CLASS_GAUGE_ZONES = {
  rook: { conversion: [0.65, 0.75], recovery: [0.26, 0.36], p50: { conversion: 0.71, recovery: 0.3 } },
  // ... 5 more classes ...
} as const;
```

**Rule (Phase 63 D-01):** Do NOT hand-edit. Regenerate by running `uv run python scripts/gen_endgame_zones_ts.py`.

---

### `app/schemas/endgames.py` (Pydantic v2 response schema)

**Analog:** `MaterialRow` (same file, lines 215-237) — the already-shipped Phase 60 pattern that Section 3 mirrors

**Pattern excerpt (MaterialRow, lines 226-237):**
```python
class MaterialRow(BaseModel):
    """One row in the eval-stratified WDL table ..."""

    bucket: MaterialBucket
    label: str
    games: int
    win_pct: float  # 0-100
    draw_pct: float  # 0-100
    loss_pct: float  # 0-100
    score: float  # 0.0-1.0, formula: (win_pct + draw_pct/2) / 100
    # opponent_score: mirror-bucket score (1 - user_score); None when sample < _MIN_OPPONENT_SAMPLE.
    opponent_score: float | None
    # opponent_games: opponent's sample size (== swap-bucket game count).
    opponent_games: int
```

**Current target dataclass (`ConversionRecoveryStats`, lines 19-42):**
```python
class ConversionRecoveryStats(BaseModel):
    conversion_pct: float
    conversion_games: int
    conversion_wins: int
    conversion_draws: int
    conversion_losses: int

    recovery_pct: float
    recovery_games: int
    recovery_saves: int
    recovery_wins: int
    recovery_draws: int
```

**Extension pattern (D-07):**
- Append 4 fields **at the end** of `ConversionRecoveryStats` (Pitfall 1 — none of the existing fields have defaults, but the new ones must not appear before required fields if defaults are introduced):
  ```python
  # Phase 84 (DATA-02): per-type opponent baselines via same-game symmetry,
  # mirroring MaterialRow.opponent_score / opponent_games (Phase 60).
  # opponent_*_pct gates on the MIRROR sample (not the field's own bucket):
  #   opponent_conversion_pct gates on recovery_games >= _MIN_OPPONENT_SAMPLE
  #   opponent_recovery_pct   gates on conversion_games >= _MIN_OPPONENT_SAMPLE
  opponent_conversion_pct: float | None
  opponent_conversion_games: int
  opponent_recovery_pct: float | None
  opponent_recovery_games: int
  ```
- Match `MaterialRow`'s nullability convention exactly: `_pct` fields are `float | None`, `_games` are always `int` (never `None`; use `0` for empty samples — see Pitfall "Treating `opponent_games` as `int | None`" in RESEARCH.md).
- Comment style mirrors `MaterialRow` inline comments (one-line `# field: meaning`).

**Update docstring** on `ConversionRecoveryStats` to mention the new opponent fields and reference Phase 84.

---

### `app/services/endgame_service.py` (service accumulator wiring)

**Analog:** `_compute_score_gap_material` mirror-bucket block (same file, lines 824-855) — the Section 2 template

**Pattern excerpt (Section 2, lines 824-855):**
```python
# Phase 60: opponent baseline via same-game symmetry. The opponent's
# score in any game set is 1 - user_score (arithmetic identity from
# user_wins + draws/2 + opp_wins + draws/2 = games). Mirror buckets:
# user Conversion <-> opponent Recovery, Even <-> Even.
swap: dict[MaterialBucket, MaterialBucket] = {
    "conversion": "recovery",
    "parity": "parity",
    "recovery": "conversion",
}

material_rows: list[MaterialRow] = []
for bucket_key in ("conversion", "parity", "recovery"):
    b2: MaterialBucket = bucket_key
    swap_bucket = swap[b2]
    swap_games = bucket_games[swap_bucket]
    if swap_games >= _MIN_OPPONENT_SAMPLE:
        opponent_score: float | None = 1.0 - bucket_score[swap_bucket]
    else:
        opponent_score = None
    win_pct, draw_pct, loss_pct = bucket_pct[b2]
    material_rows.append(
        MaterialRow(
            bucket=b2,
            ...
            opponent_score=opponent_score,
            opponent_games=swap_games,
        )
    )
```

**Insertion site (existing `_aggregate_endgame_stats`, lines 322-388):**
The accumulator already computes `conversion_games / wins / draws / losses` and `recovery_games / wins / draws / saves` per `endgame_class`. The mirror-identity wiring goes between line 355 (after `recovery_pct = ...`) and line 357 (`conversion_stats = ConversionRecoveryStats(...)`).

**Adaptation pattern (per-class scope, Pitfall 3 + Pitfall 4):**
```python
# Phase 84 (DATA-02): per-type opponent baseline via same-game symmetry,
# scoped to one EndgameClass. Mirrors Phase 60's score-gap material wiring
# (lines 824-855). Conv is win-rate, Recov is save-rate — formulas are
# asymmetric (see Pitfall 3 in RESEARCH.md). _MIN_OPPONENT_SAMPLE = 10
# (line 233) gates on the MIRROR sample (Pitfall 4).
opp_conv_losses_equiv = recovery_games - recovery_wins - recovery_draws
if recovery_games >= _MIN_OPPONENT_SAMPLE:
    opp_conv_pct: float | None = round(opp_conv_losses_equiv / recovery_games * 100, 1)
else:
    opp_conv_pct = None

opp_recov_saves_equiv = conversion_losses + conversion_draws
if conversion_games >= _MIN_OPPONENT_SAMPLE:
    opp_recov_pct: float | None = round(opp_recov_saves_equiv / conversion_games * 100, 1)
else:
    opp_recov_pct = None

conversion_stats = ConversionRecoveryStats(
    ... existing 10 kwargs ...
    opponent_conversion_pct=opp_conv_pct,
    opponent_conversion_games=recovery_games,   # mirror sample (always int, never None)
    opponent_recovery_pct=opp_recov_pct,
    opponent_recovery_games=conversion_games,   # mirror sample
)
```

**Conventions enforced (CLAUDE.md):**
- `round(x, 1)` matches the existing `conversion_pct` / `recovery_pct` style (lines 346, 354). Do NOT switch to 0.0-1.0; Open Question 3 recommends matching 1dp percent.
- No new constants — reuse `_MIN_OPPONENT_SAMPLE` from line 233.
- No `# type: ignore`; use `# ty: ignore[rule-name]` only if absolutely required.
- Do not invent a context dataclass for the 4 derived values (CLAUDE.md "Don't invent context dataclasses").

---

### `tests/services/test_endgame_zones.py` (append `TestPerClassP50`)

**Analog:** `TestRegistrySanity` (same file, lines 192-240) — registry shape tests

**Pattern excerpt (registry sanity style):**
```python
class TestRegistrySanity:
    """Sanity checks on registry shape and constants."""

    def test_all_scalar_metrics_have_entries(self) -> None:
        ...
        assert set(ZONE_REGISTRY.keys()) == {
            "score_gap",
            ...
        }

    def test_bucketed_recovery_matches_benchmark(self) -> None:
        """260503: recovery typical band tightened ..."""
        for bucket in ("conversion", "parity", "recovery"):
            spec = BUCKETED_ZONE_REGISTRY["recovery_save_pct"][bucket]
            assert spec.typical_lower == 0.24
            ...
```

**Import block (existing, top of file, lines 6-13):**
```python
from app.services.endgame_zones import (
    BUCKETED_ZONE_REGISTRY,
    NEUTRAL_TIMEOUT_THRESHOLD,
    ZONE_REGISTRY,
    assign_bucketed_zone,
    assign_zone,
    sample_quality,
)
```

**Extension pattern (append a new class):**
- New class `TestPerClassP50` at the end of the file.
- Import `PER_CLASS_GAUGE_ZONES` (add to the existing import block at lines 6-13 to keep imports tidy).
- 3-5 test methods covering: presence of `p50` on every class, value match against the published benchmark (per-class with `pytest.approx(..., abs=0.005)`), and the soft IQR-contains-p50 sanity check (skip pawnless per D-05).
- Follow the `def test_xxx(self) -> None:` annotation style (matches existing `TestRegistrySanity` methods at lines 195, 225).

---

### `tests/test_endgame_service.py` (append per-type opponent tests to `TestAggregateEndgameStats`)

**Analog:** `TestScoreGapMaterialOpponentBaseline` (same file, lines 1381-1474) — the Section 2 mirror-identity test pattern

**Pattern excerpt (Section 2 mirror-identity test, lines 1405-1432):**
```python
def test_opponent_baseline_symmetric_60_40(self):
    """User Conv 60% over 100 games and User Recov 40% over 100 games:
    Conv row's opponent_score == 1 - 0.40 = 0.60 (mirror of Recov), ..."""
    conv_rows = [self._conversion_row(i, "1-0") for i in range(60)] + [
        self._conversion_row(i + 60, "0-1") for i in range(40)
    ]
    rec_rows = [self._recovery_row(i + 100, "1-0") for i in range(40)] + [
        self._recovery_row(i + 140, "0-1") for i in range(60)
    ]
    entry_rows = conv_rows + rec_rows
    endgame_wdl = self._make_wdl(100, 0, 100)
    non_endgame_wdl = self._make_wdl(0, 0, 0)
    result = _compute_score_gap_material(endgame_wdl, non_endgame_wdl, entry_rows)
    conv = result.material_rows[0]
    rec = result.material_rows[2]
    assert conv.opponent_score == pytest.approx(0.60, abs=1e-9)
    assert conv.opponent_games == 100
    ...
```

**Boundary tests (lines 1446-1474):**
- `test_opponent_baseline_below_threshold_9_games`: swap-bucket sample = 9, expect `opponent_score is None`, `opponent_games == 9`.
- `test_opponent_baseline_at_threshold_10_games`: swap-bucket sample = 10, expect non-None.

**Row shape convention (lines 184-188 of `TestAggregateEndgameStats`):**
```
(game_id, endgame_class_int, result, user_color, eval_cp, eval_mate)
where endgame_class_int is 1=rook, 2=minor_piece, ...
```

**Adaptation pattern (append to `TestAggregateEndgameStats`, around line 360):**
- Construct rows directly as tuples (matching the existing `_aggregate_endgame_stats` test style at lines 199-205, 216-219, 231-234) — do NOT replicate the `_FakeRow` dataclass helper used in `TestScoreGapMaterialOpponentBaseline`. The aggregate tests use bare tuples.
- Use `_aggregate_endgame_stats(rows)` not `_compute_score_gap_material(...)`.
- Pick the row by class: `rook = next(c for c in result if c.endgame_class == "rook")`.
- Assert on `rook.conversion.opponent_conversion_pct` / `opponent_conversion_games` / `opponent_recovery_pct` / `opponent_recovery_games`.
- Required test cases (RESEARCH.md "Phase Requirements → Test Map"):
  1. `test_per_type_opponent_conversion_pct_mirror_identity` — symmetric 60/40 case, verify both opp_conv_pct and opp_recov_pct.
  2. `test_per_type_opponent_pct_none_below_threshold` — 100 conv + 9 recov: opp_conv_pct is None, opp_conv_games == 9; opp_recov_pct populated, opp_recov_games == 100.
  3. `test_per_type_opponent_pct_at_threshold_10` — boundary case at exactly 10 mirror games.
  4. `test_per_type_opponent_zero_sample` — both conv_games == 0 and recov_games == 0 case: no DivByZero, fields stay sane.
- Use `pytest.approx(value, abs=0.1)` for 1dp percentage tolerance (matches existing `round(..., 1)` precision).

---

### `84-01-SUMMARY.md` (audit doc, D-10)

**Analog:** Phase 83's plan-summary doc (in `.planning/milestones/v1.16-phases/83-*/`) — same milestone-track structure

**Content pattern (planner produces):**
- Section 2 audit (already-wired):
  - Cite Phase 60 commit/phase reference.
  - List file:line refs: `app/services/endgame_service.py:824-855`, `app/schemas/endgames.py:215-237`, `frontend/src/components/charts/EndgameScoreGapSection.tsx:111-145`.
  - Confirm: no backend work needed for Section 2.
- Section 3 fields added:
  - Enumerate the 4 new `ConversionRecoveryStats` fields.
  - Document mirror identities (from D-07 and Pitfall 3).
  - Note threshold reuse: `_MIN_OPPONENT_SAMPLE = 10` (gates on mirror sample, not own sample).
- Cross-reference: Phase 87 will consume these fields for per-type peer bullets.
- Note threshold-constant duality: backend `_MIN_OPPONENT_SAMPLE` vs frontend `MIN_OPPONENT_BASELINE_GAMES` (RESEARCH.md "Project Constraints" final bullet).

---

## Shared Patterns

### Pattern A: Python-authoritative + TS codegen + CI drift guard (Phase 63 D-01)

**Source:** `app/services/endgame_zones.py` + `scripts/gen_endgame_zones_ts.py` + `.github/workflows/ci.yml:47-50`

**Apply to:** Any new zone band, threshold, or per-class constant. In this phase, the new `p50` field on `PerClassBands`.

**Rule:**
1. Define the constant in Python (`endgame_zones.py`).
2. Extend the emitter (`gen_endgame_zones_ts.py`) to write it into the TS mirror.
3. Run the emitter locally; commit both Python + regenerated `endgameZones.ts` in one commit.
4. CI runs the emitter again with `git diff --exit-code` — drift fails the build.

**Anti-pattern:** Hand-editing `frontend/src/generated/endgameZones.ts`. The file header literally says `// AUTO-GENERATED — do not edit by hand.`

### Pattern B: Same-game mirror-bucket symmetry (Phase 60)

**Source:** `app/services/endgame_service.py:824-855`

**Apply to:** Any per-bucket or per-class peer baseline derived from the user's own games. In this phase, the per-class opponent fields on `ConversionRecoveryStats`.

**Identity:** opp_wins(in user's bucket X) = user_losses(in user's bucket X); opp_draws = user_draws. Cross-bucket: user "conversion" games are by definition opponent "recovery" games. Scoping to one `EndgameClass` keeps the identity exact.

**Threshold:** `_MIN_OPPONENT_SAMPLE = 10` (`endgame_service.py:233`). Gate the `_pct` field on the **mirror** sample size, not the field's own bucket size. `_games` companion field is always `int` (== mirror sample size, possibly 0).

**Anti-pattern:** Computing opponent rates on the frontend from the user's WDL fields — duplicates the math and creates two drift-prone code paths (D-08 trade-off; D-07 resolves by surfacing on the wire).

### Pattern C: Pydantic v2 schema field ordering (Pitfall 1)

**Source:** `MaterialRow` (lines 215-237) and `ConversionRecoveryStats` (lines 19-42) both lack defaults — all fields required.

**Apply to:** `ConversionRecoveryStats` extension.

**Rule:** Append new fields at the END of the model. Service-layer constructors must pass all new fields explicitly (matches the existing `ConversionRecoveryStats(...)` call at `endgame_service.py:357-368`).

### Pattern D: `EndgameClass` Literal typing (CLAUDE.md type-safety)

**Source:** `app/schemas/endgames.py:15` — `EndgameClass = Literal["rook", "minor_piece", "pawn", "queen", "mixed", "pawnless"]`

**Apply to:** All new accumulator keys, schema field types, dict annotations.

**Rule:** Never bare `str`. Use `EndgameClass` (backend) or `EndgameClassKey` (frontend). The `Mapping[EndgameClass, PerClassBands]` annotation on `PER_CLASS_GAUGE_ZONES` is the canonical example.

### Pattern E: Sentry capture for unexpected DB shapes (CLAUDE.md Sentry rules)

**Source:** `app/services/endgame_service.py:287-292`
```python
sentry_sdk.set_context("invalid_endgame_class", {"class_int": endgame_class_int})
sentry_sdk.set_tag("source", "endgame_aggregate")
sentry_sdk.capture_exception(ValueError("Unknown endgame_class integer from DB"))
```

**Apply to:** No new sites in this phase — the new mirror-identity arithmetic is pure (no DB / no external IO / no exceptional paths). Do not add new captures.

## No Analog Found

None. Every modified/created file in this phase extends or directly mirrors an in-repo pattern from Phase 60, 63, 82, or 83. The audit doc (`84-01-SUMMARY.md`) is the only "create-from-scratch" artifact, and its analog is the Phase 83 plan-summary doc structure used across all v1.16/v1.17 phases.

## Metadata

**Analog search scope:**
- `app/services/endgame_zones.py` (full file)
- `app/services/endgame_service.py` (lines 220-388, 800-865 — accumulator + Section 2 mirror block)
- `app/schemas/endgames.py` (lines 1-80, 200-260 — `ConversionRecoveryStats` + `MaterialRow`)
- `scripts/gen_endgame_zones_ts.py` (full file)
- `frontend/src/generated/endgameZones.ts` (full file)
- `tests/services/test_endgame_zones.py` (lines 1-241 — full existing file)
- `tests/test_endgame_service.py` (lines 181-360, 1380-1474 — aggregate-stats + Section 2 opponent baseline classes)

**Files scanned:** 7
**Pattern extraction date:** 2026-05-12
