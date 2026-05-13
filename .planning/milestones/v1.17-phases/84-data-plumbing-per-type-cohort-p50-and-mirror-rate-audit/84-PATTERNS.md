# Phase 84: Data plumbing — mirror-rate audit - Pattern Map

**Mapped:** 2026-05-12 (regenerated post-pivot; supersedes prior DATA-01 codegen mapping)
**Files analyzed:** 4 (2 modified source, 1 modified tests, 1 created audit prose)
**Analogs found:** 4 / 4 (every target mirrors an in-repo pattern; no greenfield)

**Pivot note.** The prior `84-PATTERNS.md` (now overwritten) covered DATA-01 codegen targets (`app/services/endgame_zones.py`, `scripts/gen_endgame_zones_ts.py`, `frontend/src/generated/endgameZones.ts`, `tests/services/test_endgame_zones.py`). DATA-01 was dropped 2026-05-12 by the single-bullet doctrine (see `.planning/notes/v1.17-single-bullet-doctrine.md`); those files are **out of scope** for Phase 84 and intentionally absent from the classification table below.

## File Classification

| New/Modified File | Action | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|--------|------|-----------|----------------|---------------|
| `app/schemas/endgames.py` | modify | schema (Pydantic v2 response model) | response-shape | `MaterialRow` (same file, lines 215-237) | exact (same file, same pattern family) |
| `app/services/endgame_service.py` | modify | service (aggregation / business logic) | transform (in-memory mirror identity) | `_compute_score_gap_material` mirror block (same file, lines 824-855) | exact (same file, sibling function, same identity scaled per-class) |
| `tests/test_endgame_service.py` | modify | test (unit) | request-response (function under test) | `TestScoreGapMaterialOpponentBaseline` (same file, lines 1381-1474) for assertions; `TestAggregateEndgameStats` (same file, lines 181-211) for row-construction convention | exact (both templates live in target file) |
| `…/84-data-plumbing-…/SUMMARY.md` § Section 2 audit | create | doc (prose audit deliverable) | static text | n/a — the audit content is locked by CONTEXT D-01/D-02; closest format reference is any prior phase SUMMARY § that cites file:line evidence | n/a (prose; no code analog) |

## Pattern Assignments

### `app/schemas/endgames.py` (schema, response-shape)

**Analog:** `MaterialRow` in the same file (lines 215-237). Section 3's four new fields on `ConversionRecoveryStats` deliberately copy the `MaterialRow.opponent_score: float | None` + `MaterialRow.opponent_games: int` pair shape so Section 2 and Section 3 carry one wire convention across the `/api/endgames/overview` response.

**Existing `ConversionRecoveryStats` to extend** (lines 19-42):

```python
class ConversionRecoveryStats(BaseModel):
    """Inline conversion/recovery stats for one endgame category (D-06, D-08, D-09).
    ...
    """

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

**Pattern to copy from `MaterialRow`** (lines 234-237):

```python
# opponent_score: mirror-bucket score (1 - user_score); None when sample < _MIN_OPPONENT_SAMPLE.
opponent_score: float | None
# opponent_games: opponent's sample size (== swap-bucket game count).
opponent_games: int
```

**Extension (per CONTEXT D-03):** append four required fields after `recovery_draws`. No defaults (consistent with sibling fields — none of the existing fields default). Update the docstring to add a "Phase 84:" paragraph referencing the mirror identity per `EndgameClass`. Field types match the Phase 60 convention exactly: `float | None` for the `_pct`, plain `int` for the `_games`.

```python
# Phase 84: opponent baseline via same-game mirror identity (D-03, D-04).
opponent_conversion_pct: float | None  # None when recovery_games < _MIN_OPPONENT_SAMPLE
opponent_conversion_games: int          # == recovery_games (mirror sample, possibly 0)
opponent_recovery_pct: float | None    # None when conversion_games < _MIN_OPPONENT_SAMPLE
opponent_recovery_games: int            # == conversion_games (mirror sample, possibly 0)
```

**Comment-at-fix-site rule (CLAUDE.md).** The two `_pct` fields are gated on the **mirror** bucket size, not the own bucket size — that asymmetry is non-obvious and is the most likely pitfall (RESEARCH Pitfall 2). The inline comment must spell out the gating bucket explicitly so future readers don't guess.

---

### `app/services/endgame_service.py` (service, transform)

**Analog:** `_compute_score_gap_material` mirror-bucket block at lines 824-855 in the same file (the Phase 60 in-repo template). Phase 84 scales the same identity per-`EndgameClass` instead of per-`MaterialBucket`.

**Source-of-truth excerpt (Phase 60 template)** (lines 824-855):

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
            label=_MATERIAL_BUCKET_LABELS[b2],
            games=bucket_games[b2],
            ...
            opponent_score=opponent_score,
            opponent_games=swap_games,
        )
    )
```

**Wiring site (per CONTEXT D-06):** between line 355 (after `recovery_pct = …`) and line 357 (`conversion_stats = ConversionRecoveryStats(…)`) inside the `for endgame_class in wdl:` loop (loop opens at line 324, the per-class numerator/denominator block runs through line 355). No new accumulator key, no new DB query — `conversion_games`, `conversion_wins`, `conversion_draws`, `conversion_losses`, `recovery_games`, `recovery_wins`, `recovery_draws` are already local at line 355.

**Extension pattern (per CONTEXT D-04, D-05, D-07):**

```python
# Phase 84: opponent baselines via same-game mirror identity, scoped per
# EndgameClass (D-04). Conv = win-rate, Recov = save-rate — the two
# formulas are asymmetric (Conv: wins only in numerator; Recov: wins +
# draws). Gating reuses _MIN_OPPONENT_SAMPLE on the *mirror* bucket size
# (Phase 60 pattern, see _compute_score_gap_material lines 824-855).
opponent_conversion_pct: float | None
if recovery_games >= _MIN_OPPONENT_SAMPLE:
    recovery_losses = recovery_games - recovery_wins - recovery_draws
    opponent_conversion_pct = round(recovery_losses / recovery_games * 100, 1)
else:
    opponent_conversion_pct = None
opponent_conversion_games = recovery_games

opponent_recovery_pct: float | None
if conversion_games >= _MIN_OPPONENT_SAMPLE:
    opponent_recovery_pct = round(
        (conversion_losses + conversion_draws) / conversion_games * 100, 1
    )
else:
    opponent_recovery_pct = None
opponent_recovery_games = conversion_games
```

**Constructor extension (lines 357-368):** the existing `ConversionRecoveryStats(…)` call already passes ten kwargs; append four more (D-03 ordering — append after `recovery_draws`). All four kwargs are required by the schema (no defaults).

**Key divergences from the Phase 60 template (deliberate):**

| Aspect | Phase 60 (lines 824-855) | Phase 84 (new wiring) |
|--------|--------------------------|-----------------------|
| Scoping | per `MaterialBucket` | per `EndgameClass` (loop iteration already open) |
| Mirror map | explicit `swap: dict[MaterialBucket, MaterialBucket]` literal | inline arithmetic — only two mirror identities (conv↔recov within one class), a dict would be over-engineering (RESEARCH "Anti-Patterns" §1; also CLAUDE.md "Don't invent context dataclasses…") |
| Scale | 0.0-1.0 score-style (`opponent_score`) | 0.0-100.0 percent-style with `round(x, 1)` to match local `conversion_pct` / `recovery_pct` convention at lines 346, 354 (CONTEXT D-07) |
| Numerator | symmetric `1.0 - bucket_score[swap_bucket]` | asymmetric: Conv = `recovery_losses / recovery_games`, Recov = `(conversion_losses + conversion_draws) / conversion_games` (CONTEXT D-04 — Conv is a win-rate, Recov is a save-rate) |
| Threshold | `_MIN_OPPONENT_SAMPLE = 10` (line 233) | **same constant reused** (CONTEXT D-05 — do not introduce a parallel `PER_CLASS_OPPONENT_SAMPLE_MIN`) |
| `_games` typing | `int` (always emits `swap_games`, possibly `0`) | `int` (always emits `recovery_games` / `conversion_games`, possibly `0`) |
| ty narrowing | explicit `opponent_score: float | None` annotation at first assignment (line 840) | same explicit annotation on `opponent_conversion_pct` / `opponent_recovery_pct` locals (RESEARCH Pitfall 7) |

---

### `tests/test_endgame_service.py` (test, unit)

**Primary analog (assertions / cases):** `TestScoreGapMaterialOpponentBaseline` at lines 1381-1474. Provides the canonical case-set: symmetric 60/40 mirror, empty mirror bucket, below-threshold (9 games), at-threshold (10 games).

**Secondary analog (row construction):** `TestAggregateEndgameStats` at lines 181-211 — uses **bare tuples** `(game_id, endgame_class_int, result, user_color, eval_cp, eval_mate)` to feed `_aggregate_endgame_stats`. The `_FakeRow` helper at line 1391 is scoped to `_compute_score_gap_material` tests and is **not** the natural fit here.

**Source-of-truth excerpt (Section 2 mirror template, `test_opponent_baseline_symmetric_60_40`, lines 1405-1432):**

```python
def test_opponent_baseline_symmetric_60_40(self):
    """User Conv 60% over 100 games and User Recov 40% over 100 games:
    Conv row's opponent_score == 1 - 0.40 = 0.60 (mirror of Recov),
    Recov row's opponent_score == 1 - 0.60 = 0.40 (mirror of Conv)."""
    conv_rows = [self._conversion_row(i, "1-0") for i in range(60)] + [
        self._conversion_row(i + 60, "0-1") for i in range(40)
    ]
    rec_rows = [self._recovery_row(i + 100, "1-0") for i in range(40)] + [
        self._recovery_row(i + 140, "0-1") for i in range(60)
    ]
    ...
    assert conv.opponent_score == pytest.approx(0.60, abs=1e-9)
    assert conv.opponent_games == 100
```

**Source-of-truth excerpt (row-construction convention for `_aggregate_endgame_stats`, lines 197-211):**

```python
rows = [
    (1, 1, "1-0", "white", 100, None),       # rook conversion win
    (2, 3, "1-0", "white", 50, None),        # pawn conversion win
    (3, 3, "1-0", "white", 0, None),         # pawn parity win
    (4, 3, "0-1", "white", -100, None),      # pawn recovery loss
]
result = _aggregate_endgame_stats(rows)
```

**Extension pattern (per CONTEXT D-04, D-05, D-07, D-11 + Claude's discretion on placement):**

Append a new test class to `TestAggregateEndgameStats` (recommended seam, RESEARCH Open Question 1) — co-located with the function under test, using the bare-tuple row convention already established at lines 197-211. Do **not** import or reuse `_FakeRow`; bare tuples suffice and match the existing convention for `_aggregate_endgame_stats`.

Test cases (each maps to a DATA-02 validation requirement in `84-RESEARCH.md` Validation Architecture):

1. **`test_per_type_opponent_baseline_symmetric_60_40`** — User Conv 60% (6W/0D/4L over 10 games, eval `+150`) and User Recov save-rate 40% (2W/2D/6L over 10 games, eval `-150`) in `rook` class → `opponent_conversion_pct == 60.0` (= `(10 - 2 - 2) / 10 * 100`), `opponent_recovery_pct == 40.0` (= `(4 + 0) / 10 * 100`). **Asserts the formula asymmetry** (RESEARCH Pitfall 1).
2. **`test_per_type_opponent_baseline_below_threshold`** — mirror bucket has 9 games → `_pct is None`, `_games == 9`. **Asserts the `< 10` gate**.
3. **`test_per_type_opponent_baseline_at_threshold`** — mirror bucket has exactly 10 games → `_pct` is non-None, `_games == 10`. **Asserts the `>=` boundary** (CONTEXT D-05).
4. **`test_per_type_opponent_baseline_zero_sample`** — mirror bucket has 0 games → `_pct is None`, `_games == 0`, no `ZeroDivisionError`. **Asserts the gating-is-the-guard property** (RESEARCH Pitfall 6).
5. **`test_per_type_opponent_baseline_schema_shape`** — construct stats with non-trivial data; assert `isinstance(stats.opponent_conversion_pct, float)`, `isinstance(stats.opponent_conversion_games, int)`, `stats.opponent_recovery_pct is None or isinstance(stats.opponent_recovery_pct, float)`, `isinstance(stats.opponent_recovery_games, int)`. **Asserts the `_games: int` convention** (RESEARCH Pitfall 3) and that the new fields exist (regression guard against a future stale-schema mistake).

Class seam: a sub-class `class TestPerTypeOpponentBaseline(TestAggregateEndgameStats):` is fine, or append methods directly to `TestAggregateEndgameStats`. Planner picks; both stay inside the existing test class hierarchy and reuse the bare-tuple convention.

---

### Phase SUMMARY.md § "Section 2 audit" (doc, static text)

**Analog:** no in-repo code analog (this is prose). Closest format reference is the audit-style sections that prior phases include in their SUMMARY.md citing file:line evidence (e.g. cross-references in `.planning/milestones/v1.10-phases/60-*/` for the original Phase 60 mirror-bucket wiring).

**Required content** (per CONTEXT D-02):

1. **What's already wired** — bullet list of the components Phase 86 needs, each with file:line citation:
   - `MaterialRow.opponent_score: float | None` + `MaterialRow.opponent_games: int` — `app/schemas/endgames.py:215-237`.
   - `ScoreGapMaterialResponse.material_rows` carries the three-row table on `/api/endgames/overview` — `app/schemas/endgames.py:279-305`.
   - `EndgameOverviewResponse` composes the response — `app/schemas/endgames.py:475-491`.
   - Phase 60 wiring in `_compute_score_gap_material` — `app/services/endgame_service.py:824-855`.
   - Frontend consumer pattern (`MIRROR_BUCKET` map + `opponentRate()` helper) — `frontend/src/components/charts/EndgameScoreGapSection.tsx:111-145`.
2. **How Phase 86 derives `Opp Skill`** — one paragraph: Skill is a composite, so `Opp Skill` is computed client-side using the same composite formula as `Your Skill`, fed by `MaterialRow[conversion].opponent_score` (`opp_conv`) and `MaterialRow[recovery].opponent_score` (`opp_recov`) already on the wire. No new payload field for Skill.
3. **Threshold gating** — explicit note that `_MIN_OPPONENT_SAMPLE = 10` (`app/services/endgame_service.py:233`) is the single threshold across Section 2 and Section 3.
4. **Cross-reference** — Phase 60 introduced the mirror-bucket pattern; Phase 84 extends it per-class for Section 3.

**Length target:** ~15 lines in SUMMARY.md (CONTEXT D-11 — if it balloons past ~30 lines, planner may split into a second plan; otherwise it lives inline alongside the schema/service/test plan).

## Shared Patterns

### Pattern A: Same-game mirror-bucket symmetry (Phase 60)

**Source:** `app/services/endgame_service.py:824-855`
**Identity:** Within one scope, `opp_wins(in user bucket X) = user_losses(in user bucket X)`. Cross-bucket: user's conversion games are by definition opponent's recovery games (and vice versa) — opponent entered with the opposite eval sign.
**Gating rule:** `_MIN_OPPONENT_SAMPLE = 10` applies to the **mirror bucket's** game count, **not** the field's own bucket. The "sample" backing an opponent baseline is the mirror bucket because that's where the analogous games physically came from. Restated for Phase 84:
- `opponent_conversion_pct` is `None` when `recovery_games < 10`.
- `opponent_recovery_pct` is `None` when `conversion_games < 10`.
**Apply to:** the service wiring in `_aggregate_endgame_stats` (the one new block) and to every test case that exercises the boundary.

### Pattern B: Pydantic v2 schema field ordering on `ConversionRecoveryStats`

**Source convention:** `ConversionRecoveryStats` (`app/schemas/endgames.py:19-42`) and `MaterialRow` (`app/schemas/endgames.py:215-237`) both lack defaults — every field is required.
**Rule:** the four new fields are appended after `recovery_draws` (CONTEXT D-03 — keep the four contiguous; do not interleave with the existing conv/recov groups). No defaults. All constructor call sites must pass them; there is exactly one constructor site in the codebase, `endgame_service.py:357-368`, and Phase 84 modifies it. No other producer constructs `ConversionRecoveryStats` (verified — the only inbound construction is in `_aggregate_endgame_stats`).
**Apply to:** the schema edit and the single constructor extension.

### Pattern C: `EndgameClass` Literal typing (CLAUDE.md type-safety rule)

**Source:** `app/schemas/endgames.py:15` — `EndgameClass = Literal["rook", "minor_piece", "pawn", "queen", "mixed", "pawnless"]`.
**Rule:** every dict keyed by class uses `dict[EndgameClass, …]`, every function parameter that takes a class uses `EndgameClass`, no bare `str`. The new mirror identity operates inside the existing `for endgame_class in wdl:` loop (line 324), where `endgame_class: EndgameClass` is already in scope — no new typing surface is introduced for the wiring itself. Tests assert on `category.endgame_class == "rook"` (literal string), which is type-compatible.
**Apply to:** every new local that is per-class (none introduced in this phase — the new locals are scalars).

### Pattern D: `round(x, 1)` percent convention in `_aggregate_endgame_stats`

**Source:** existing `conversion_pct = round(conversion_wins / conversion_games * 100, 1) if conversion_games > 0 else 0.0` at `endgame_service.py:345-347` and `recovery_pct = round(recovery_saves / recovery_games * 100, 1) if recovery_games > 0 else 0.0` at `endgame_service.py:353-355`.
**Rule:** stay on 0.0-100.0 scale with one decimal for every `_pct` field on `ConversionRecoveryStats`. Do not switch to a 0.0-1.0 score-style scale mid-method (CONTEXT D-07). The Phase 60 template uses 0.0-1.0 because `MaterialRow.score` is score-style; `ConversionRecoveryStats` is percent-style — different schemas, different local conventions. The "guard" via `> 0` that the existing fields use is unnecessary for the new fields because the `>= _MIN_OPPONENT_SAMPLE` gate is strictly tighter (10 > 0); the gate IS the divide-by-zero guard (RESEARCH Pitfall 6).
**Apply to:** the two new `_pct` computations in the service wiring.

### Pattern E (cross-cutting): Comment-at-fix-site for non-obvious gating

**Source:** CLAUDE.md "Comment bug fixes" + the existing Phase 60 comment block at `endgame_service.py:824-829`.
**Rule:** the non-obvious decisions in Phase 84 — (1) gating on the mirror bucket size, not the own bucket size; (2) Conv-vs-Recov formula asymmetry; (3) percent-not-score scale — must each be flagged inline. One block-comment above the new wiring suffices (matching the existing Phase 60 comment style); the schema doc-comment above each `opponent_*_pct` field also spells out the gating-bucket asymmetry.
**Apply to:** the service wiring block and the schema field comments.

## No Analog Found

| File | Reason |
|------|--------|
| (none) | Every code change in this phase has an in-repo template. The SUMMARY.md audit prose has no code analog by nature (it is documentation), but its content is fully specified by CONTEXT D-01/D-02 and the file:line references listed in the canonical refs section of `84-CONTEXT.md`. |

## Metadata

**Analog search scope:**
- `app/schemas/endgames.py` (full file scanned; targets at lines 1-70, 200-310)
- `app/services/endgame_service.py` (targets at lines 225-385, 815-865)
- `tests/test_endgame_service.py` (targets at lines 175-225, 1375-1480)
- `frontend/src/components/charts/EndgameScoreGapSection.tsx` — referenced only as a downstream-consumer fingerprint for the audit prose; not directly modified

**Files scanned (read):** 4

**Pattern extraction date:** 2026-05-12

**Supersedes:** prior `84-PATTERNS.md` covering DATA-01 codegen targets (`app/services/endgame_zones.py`, `scripts/gen_endgame_zones_ts.py`, `frontend/src/generated/endgameZones.ts`, `tests/services/test_endgame_zones.py`) — those targets are out of scope for Phase 84 post-pivot. See `.planning/notes/v1.17-single-bullet-doctrine.md`.
