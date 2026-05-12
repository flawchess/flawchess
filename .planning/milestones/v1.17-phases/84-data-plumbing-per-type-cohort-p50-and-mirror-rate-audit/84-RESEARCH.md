# Phase 84: Data plumbing — per-type cohort p50 + mirror-rate audit - Research

**Researched:** 2026-05-12
**Domain:** Backend codegen + Pydantic schema extension (FastAPI / SQLAlchemy / Python 3.13 stack — no new libraries)
**Confidence:** HIGH

## Summary

Phase 84 is a small, contained backend phase prefixing the v1.17 frontend refactors. Two prerequisites:
1. **DATA-01** — Add an explicit `p50: tuple[float, float]` field to the `PerClassBands` frozen dataclass in `app/services/endgame_zones.py` (lines 320-326), populate it for the 6 endgame classes from `reports/benchmarks-2026-05-12.md` §6 pooled-by-class summary, and extend `_format_per_class_gauge_zones()` in `scripts/gen_endgame_zones_ts.py` (lines 67-78) to emit `p50` as a nested object `{ conversion: <num>, recovery: <num> }`. CI drift guard re-runs the codegen with `git diff --exit-code`, so the committed `frontend/src/generated/endgameZones.ts` must be regenerated in the same commit.
2. **DATA-02** — Section 2 mirror-bucket plumbing (`MaterialRow.opponent_score` / `opponent_games`) is already wired (Phase 60, `app/services/endgame_service.py:824-855`). For Section 3, extend `ConversionRecoveryStats` in `app/schemas/endgames.py:19-42` with 4 new fields (`opponent_conversion_pct`, `opponent_conversion_games`, `opponent_recovery_pct`, `opponent_recovery_games`) and populate them in `_aggregate_endgame_stats()` in `app/services/endgame_service.py:240-388` using the same mirror identity as Section 2 (opp wins in user's mirror bucket = user losses there). Audit findings live inline in `84-01-SUMMARY.md`, not a separate file.

Frontend changes are out of scope — Phase 84 only ships the codegen extension, the per-type schema fields, the inline audit doc, and unit tests.

**Primary recommendation:** Three plans as locked by D-11: (1) DATA-01 codegen extension + drift-guard regen + zone tests, (2) DATA-02 schema + service wiring + service tests, (3) audit doc inline in the phase summary. Round p50 values to 2 decimal places to match the IQR band granularity already in `PER_CLASS_GAUGE_ZONES` (e.g. `(0.65, 0.75)`).

## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Extend `PerClassBands` dataclass at `app/services/endgame_zones.py:320-326` with a new `p50: tuple[float, float]` field, ordered `(conversion_p50, recovery_p50)` to mirror existing `conversion`/`recovery` IQR tuples. Single source of truth — IQR and centre tick stay colocated. **Rejected alternatives:** a separate `PER_CLASS_P50` mapping (drift risk); frontend midpoint-of-IQR computation (inaccurate — pooled per-class p50 is offset from IQR midpoint on pawn/queen/pawnless).
- **D-02:** Update `_format_per_class_gauge_zones()` at `scripts/gen_endgame_zones_ts.py:67-78` to emit a third key per class: `{ conversion: [lo, hi], recovery: [lo, hi], p50: { conversion: <num>, recovery: <num> } }`. Emit `p50` as a nested object (NOT a tuple) for cleaner downstream typing. Re-run codegen; CI drift guard catches any hand-edit.
- **D-03:** p50 values from `reports/benchmarks-2026-05-12.md` §6 "Pooled-by-class summary (excl sparse cell)":

  | class | p50.conversion | p50.recovery |
  |---|---:|---:|
  | rook | 0.7098 | 0.2963 |
  | minor_piece | 0.6949 | 0.3278 |
  | pawn | 0.7379 | 0.2754 |
  | queen | 0.7744 | 0.2343 |
  | mixed | 0.6940 | 0.3111 |
  | pawnless | 0.7913 | 0.1976 |

  Plan may round to 2 dp; round-half-even is fine.
- **D-04:** Source comment must say "pooled per-class typical centre, source: §6 mean (≈ per-user p50)" — §6 reports pooled means, not per-user p50 medians, but they diverge by ≤0.01 on these distributions (§5 confirms).
- **D-05:** No drift recommendations from §6 are applied this phase (pawnless conversion / recovery flagged in §6 "Recommendations" but deferred). Phase 84 keeps live IQR bands unchanged; only adds `p50`.
- **D-06:** Section 2 audit (already-present): `MaterialRow.opponent_score: float | None` + `opponent_games: int` added in Phase 60 at `app/services/endgame_service.py:840-854`, wired into `/api/endgames/overview` via `ScoreGapMaterialResponse.material_rows`, consumed by `EndgameScoreGapSection.tsx:141-144` `opponentRate()`. No backend work needed for Section 2.
- **D-07:** Section 3 extension (new fields). Add 4 fields to `ConversionRecoveryStats` (`app/schemas/endgames.py:19-42`):
  - `opponent_conversion_pct: float | None`
  - `opponent_conversion_games: int`
  - `opponent_recovery_pct: float | None`
  - `opponent_recovery_games: int`

  Mirror identities (same-game symmetry, scoped to one `EndgameClass`):
  - `opp_conv_pct[X] = (user_recovery_games − user_recovery_wins − user_recovery_draws) / user_recovery_games`
  - `opp_recov_pct[X] = (user_conversion_losses + user_conversion_draws) / user_conversion_games`

  `None` when the user's mirror-bucket sample is below `_MIN_OPPONENT_SAMPLE` (the same threshold Section 2 uses). Wire up wherever `EndgameCategoryStats` / `ConversionRecoveryStats` are constructed.
- **D-08 (flag):** The 4 new fields are derivable client-side from existing per-type WDL fields. User locked the schema extension for consistency with `MaterialRow`; flag this so the planner can re-surface the trade-off if implementation cost is non-trivial.
- **D-09:** Sig-test pattern for per-type peer bullets is Phase 87 scope, not this phase. Phase 84 locks only the data shape.
- **D-10:** Audit deliverable is inline in `84-01-SUMMARY.md`. No separate `.planning/notes/` audit file.
- **D-11:** Phase 84 stays standalone, 3 plans expected.

### Claude's Discretion

- Rounding of p50 values to 2 dp or 4 dp — planner picks one and stays consistent with the IQR band emitter.
- Whether to add a parallel `PER_CLASS_OPPONENT_SAMPLE_MIN` constant (probably reuse `_MIN_OPPONENT_SAMPLE` from `endgame_service.py`).
- Test placement: `tests/services/test_endgame_zones.py` for p50 field presence; `tests/test_endgame_service.py` for per-type opponent field population.

### Deferred Ideas (OUT OF SCOPE)

- Pawnless band shifts flagged in `reports/benchmarks-2026-05-12.md` §6 Recommendations (sparse sample, ~1,365 users). Defer to a future zones-calibration phase.
- Cell-specific (rating × TC) per-class baselines (`FUT-04`) — out of scope for v1.17.
- `PER_CLASS_OPPONENT_SAMPLE_MIN` per-class threshold (separate from the global one) — only worth doing if Phase 87 hits sparse-n problems. Reuse the existing global threshold.
- Per-class Endgame Skill metric — global composite only.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DATA-01 | Explicit per-type cohort p50 values are exposed to the frontend for Section 3 bullets via `gen_endgame_zones_ts.py` / `endgame_zones.py` extension. | Confirmed: existing `PerClassBands` carries only `(conversion, recovery)` IQR tuples; `_format_per_class_gauge_zones()` emits only the IQR. p50 must be added in both places. Benchmark source confirmed at `reports/benchmarks-2026-05-12.md` §6 lines 435-440 (values match D-03 exactly). |
| DATA-02 | Mirror-bucket peer rates exposed on `/api/endgames/overview` payload (audit existing schema; extend only if not already present). | Confirmed: Section 2 (`MaterialRow.opponent_score` / `opponent_games`) is already wired at `endgame_service.py:824-855` + `endgames.py:235-237`. Section 3 (`ConversionRecoveryStats`) is NOT — it carries per-type WDL fields but no opponent fields. Schema + service extension required. Mirror identity verified against `EndgameScoreGapSection.tsx:141-145` `opponentRate()` (same `loss_pct` / `loss_pct + draw_pct` math, just scoped per-class instead of per-bucket). |

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Define authoritative per-class p50 constants | Backend / Python (`app/services/endgame_zones.py`) | — | Phase 63 D-01 locks Python as authoritative for zone thresholds; TS is codegen'd mirror. No FE-only constants. |
| Codegen Python → TypeScript mirror | Build script (`scripts/gen_endgame_zones_ts.py`) | CI drift guard (`.github/workflows/ci.yml:47-50`) | Single emitter function `_format_per_class_gauge_zones()`. `git diff --exit-code` post-codegen blocks drift. |
| Compute per-type opponent rates from user WDL | API / Backend service (`app/services/endgame_service.py::_aggregate_endgame_stats`) | — | Same-game symmetry identity (opp wins in user's mirror bucket = user losses there). The accumulator already has all numerator/denominator fields; no new DB queries. |
| Expose per-type opponent rates on wire | API schema (`app/schemas/endgames.py::ConversionRecoveryStats`) | — | Mirrors the `MaterialRow.opponent_score` / `opponent_games` Section 2 wire pattern. Surfaces under `EndgameStatsResponse.categories[*].conversion`. |
| Frontend consumption of new fields | Frontend (Phase 87) | — | Out of scope for Phase 84. Phase 87 will read `PER_CLASS_GAUGE_ZONES[<class>].p50.{conversion,recovery}` and `EndgameCategoryStats.conversion.opponent_*` for per-type bullets. |

## Standard Stack

This is an in-house refactor on the existing FlawChess Python 3.13 / FastAPI / Pydantic v2 stack. No new libraries needed.

### Existing assets used (all already in repo)
| Library / module | Version | Purpose | Why standard |
|---|---|---|---|
| Pydantic v2 (BaseModel) | 2.x | Add 4 fields to `ConversionRecoveryStats` schema | Project-wide validation layer; all wire schemas use it. |
| Python `dataclasses` (frozen) | stdlib 3.13 | Extend `PerClassBands` with a `p50` field | Already used for `ZoneSpec`, `PerClassBands`; frozen immutability is established pattern. |
| `typing.Literal` | stdlib 3.13 | `EndgameClass = Literal[...]` preserved across the new dict-keyed access | Project rule: no bare strings for endgame class (CLAUDE.md type safety). |
| pytest | 8.x (declared in `pyproject.toml`) | Unit tests for new field presence/values, mirror-identity invariants, None-threshold semantics | Project standard; tests already split by concern (`test_endgame_zones.py` for zones, `test_endgame_service.py` for service). |
| ty (type checker) | latest pinned | Validate type annotations on the new tuple field and `float \| None` fields | CI runs `uv run ty check app/ tests/` between ruff and pytest. New annotations must pass. |
| ruff | latest pinned | Format + lint | CI gate. |

### Don't install anything new
No external library is needed. The phase is purely additive — one new field on a dataclass, one new emitter clause, four new fields on a Pydantic model, and corresponding service-layer wiring.

## Architecture Patterns

### System Architecture Diagram

```
                        ┌──────────────────────────────────────────────┐
                        │ reports/benchmarks-2026-05-12.md §6          │
                        │ (pooled-by-class means; D-03 source of truth)│
                        └────────────────────┬─────────────────────────┘
                                             │ (manual transcription, 2 dp)
                                             ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ app/services/endgame_zones.py                                              │
│   PerClassBands (frozen @dataclass)                                        │
│     ├ conversion: tuple[float, float]    ← unchanged                       │
│     ├ recovery:   tuple[float, float]    ← unchanged                       │
│     └ p50:        tuple[float, float]    ← NEW (DATA-01)                   │
│   PER_CLASS_GAUGE_ZONES: Mapping[EndgameClass, PerClassBands]              │
└────────────────────┬───────────────────────────────────────────────────────┘
                     │
                     │ imported by:
                     │
            ┌────────┴───────────────────────────┐
            ▼                                    ▼
┌──────────────────────────────┐   ┌────────────────────────────────────┐
│ scripts/gen_endgame_zones_ts │   │ (other consumers unchanged:        │
│   _format_per_class_gauge_   │   │  per_class_zone_spec /             │
│   zones()                    │   │  assign_per_class_zone —           │
│   emits p50 as { conversion, │   │  these don't read p50)             │
│   recovery } nested obj      │   │                                    │
└────────┬─────────────────────┘   └────────────────────────────────────┘
         │ writes:
         ▼
┌──────────────────────────────────────────┐
│ frontend/src/generated/endgameZones.ts   │
│   PER_CLASS_GAUGE_ZONES = {              │
│     rook: { conversion: [...],           │
│             recovery: [...],             │
│             p50: { conversion: 0.71,     │
│                    recovery: 0.30 } },   │
│     ...                                  │
│   } as const;                            │
└──────────────────────────────────────────┘
         ▲
         │ (Phase 87 consumer, NOT this phase)
         ▼
   (Section 3 per-class cohort bullet centre tick)


┌────────────────────────────────────────────────────────────────────────────┐
│ DATA-02: ConversionRecoveryStats schema + service wiring                   │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│ app/services/endgame_service.py::_aggregate_endgame_stats                  │
│   For each EndgameClass:                                                   │
│     ┌─ conv_data: {games, wins, draws}  (already accumulated)              │
│     │  ► conversion_losses = games − wins − draws                          │
│     │                                                                      │
│     └─ recov_data: {games, wins, draws}  (already accumulated)             │
│        ► recovery_losses = games − wins − draws                            │
│                                                                            │
│     NEW: mirror-identity computation (scoped to this class):               │
│       opp_conv_pct  = recovery_losses / recovery_games  (if ≥ MIN else None)│
│       opp_conv_games = recovery_games                                      │
│       opp_recov_pct = (conversion_losses + conversion_draws) /             │
│                        conversion_games  (if ≥ MIN else None)              │
│       opp_recov_games = conversion_games                                   │
│                                                                            │
│   Construct ConversionRecoveryStats(                                       │
│     ... existing 10 fields ...                                             │
│     opponent_conversion_pct=opp_conv_pct,                                  │
│     opponent_conversion_games=opp_conv_games,                              │
│     opponent_recovery_pct=opp_recov_pct,                                   │
│     opponent_recovery_games=opp_recov_games,                               │
│   )                                                                        │
│                                                                            │
│ app/schemas/endgames.py::ConversionRecoveryStats                           │
│   ► add 4 fields (Pydantic v2 BaseModel; non-default placement)            │
│                                                                            │
│ Wire surfaces under EndgameStatsResponse.categories[*].conversion          │
│ which composes into EndgameOverviewResponse.stats (untouched)              │
└────────────────────────────────────────────────────────────────────────────┘
```

### Project Structure (relevant files)

```
app/
├── services/
│   ├── endgame_zones.py        # DATA-01: add p50 to PerClassBands + table
│   └── endgame_service.py      # DATA-02: wire opponent_* into ConversionRecoveryStats
├── schemas/
│   └── endgames.py             # DATA-02: extend ConversionRecoveryStats with 4 fields
scripts/
└── gen_endgame_zones_ts.py     # DATA-01: extend _format_per_class_gauge_zones()
frontend/src/generated/
└── endgameZones.ts             # DATA-01 codegen output (regenerated, committed)
tests/
├── services/
│   └── test_endgame_zones.py   # DATA-01 unit tests (p50 presence, values, type)
└── test_endgame_service.py     # DATA-02 unit tests (mirror identity, None semantics)
.planning/milestones/v1.17-phases/84-*/
└── 84-01-SUMMARY.md            # D-10: inline audit doc (Section 2 already-wired + Section 3 fields added + mirror identities documented)
```

### Pattern 1: Python authoritative, TS codegen'd

**What:** All endgame zone constants are defined in Python (`app/services/endgame_zones.py`); `scripts/gen_endgame_zones_ts.py` writes a TS mirror. CI runs the script and `git diff --exit-code` blocks any drift. Hand-editing `frontend/src/generated/endgameZones.ts` is prohibited (the `// AUTO-GENERATED — do not edit by hand.` header is enforced by reviewer convention and the CI gate).

**When to use:** Adding any new zone band, threshold, or per-class constant intended for both backend assignment logic and frontend rendering.

**Example (the existing pattern this phase extends):**

```python
# app/services/endgame_zones.py:320-326 (current)
@dataclass(frozen=True)
class PerClassBands:
    """Typical [lower, upper] bands for Conversion and Recovery for one endgame type."""
    conversion: tuple[float, float]
    recovery: tuple[float, float]

PER_CLASS_GAUGE_ZONES: Mapping[EndgameClass, PerClassBands] = {
    "rook": PerClassBands(conversion=(0.65, 0.75), recovery=(0.26, 0.36)),
    # ...
}
```

```python
# scripts/gen_endgame_zones_ts.py:67-78 (current)
def _format_per_class_gauge_zones() -> str:
    lines: list[str] = []
    for cls, bands in PER_CLASS_GAUGE_ZONES.items():
        c_lo, c_hi = bands.conversion
        r_lo, r_hi = bands.recovery
        lines.append(f"  {cls}: {{ conversion: [{c_lo}, {c_hi}], recovery: [{r_lo}, {r_hi}] }},")
    return "\n".join(lines) + "\n"
```

CI invocation (`.github/workflows/ci.yml:47-50`):
```yaml
- name: Zone drift check
  run: |
    uv run python scripts/gen_endgame_zones_ts.py
    git diff --exit-code frontend/src/generated/endgameZones.ts
```

### Pattern 2: Same-game mirror-bucket symmetry

**What:** The opponent's WDL in a same-game set equals the user's flipped WDL: `opp_wins = user_losses`, `opp_draws = user_draws`, `opp_losses = user_wins`. Cross-bucket symmetry: user "conversion" games (user entered with ≥+100cp) are by definition opponent "recovery" games (opp entered with ≤−100cp). Scoping this to a single `EndgameClass` X keeps the identity exact: opp's conv rate in class X = opp's win rate when opp entered with ≥+100cp = user's loss rate in user's recovery bucket of class X.

**When to use:** Any per-class peer baseline that mirrors a user statistic. This phase wires it into `ConversionRecoveryStats`; Phase 87 will consume it.

**Example (Section 2 template — already shipped in Phase 60):**

```python
# app/services/endgame_service.py:824-855 (existing pattern to mirror)
swap: dict[MaterialBucket, MaterialBucket] = {
    "conversion": "recovery",
    "parity": "parity",
    "recovery": "conversion",
}
for bucket_key in ("conversion", "parity", "recovery"):
    b2: MaterialBucket = bucket_key
    swap_bucket = swap[b2]
    swap_games = bucket_games[swap_bucket]
    if swap_games >= _MIN_OPPONENT_SAMPLE:
        opponent_score: float | None = 1.0 - bucket_score[swap_bucket]
    else:
        opponent_score = None
    # ...
```

**Adaptation for Section 3 (per-class):** The DATA-02 wire-up runs inside `_aggregate_endgame_stats` after computing `conversion_*` and `recovery_*` per class. The numerator already lives in the existing per-class accumulators (`conv[endgame_class]`, `recov[endgame_class]`). All four mirror values are arithmetic from those accumulators — no new DB query, no new aggregation pass.

### Anti-Patterns to Avoid

- **Hand-editing `frontend/src/generated/endgameZones.ts`** — the CI drift guard will fail. Always regenerate via `uv run python scripts/gen_endgame_zones_ts.py` and commit the output in the same commit as the Python change.
- **Adding a separate `PER_CLASS_P50` map** — drift risk between IQR and centre tick. D-01 explicitly rejects this; keep `p50` on `PerClassBands`.
- **Computing p50 as the midpoint of IQR on the frontend** — D-01 rejects this. The pooled per-class p50 is offset from the IQR midpoint on at least pawn, queen, and pawnless (§6 of the benchmarks report confirms).
- **Using a bare `str` for endgame class in any new schema field** — CLAUDE.md type-safety rule. New service code must keep `Literal["rook", "minor_piece", "pawn", "queen", "mixed", "pawnless"]` (= `EndgameClass`) typing.
- **Using `# type: ignore` instead of `# ty: ignore[rule-name]`** — CLAUDE.md ty-compliance rule. None of the planned changes should need a suppression; if they do, use `ty:` form with rule name and reason.
- **Recomputing opponent rates per-call in the service when the accumulator has the inputs** — derive from the already-built `conv[endgame_class]` / `recov[endgame_class]` dicts; don't iterate raw rows twice.
- **Treating `opponent_games` as `int | None`** — CLAUDE.md / Phase 60 pattern: only the `_pct` fields go to `None` below threshold; `_games` is always `int` (use `0` for empty / unconverted samples). Matches `MaterialRow.opponent_games: int`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---|---|---|---|
| Drift detection between Python source-of-truth and TS mirror | A custom checksum / manual sync step | Run `scripts/gen_endgame_zones_ts.py` in CI + `git diff --exit-code` (already in `ci.yml:47-50`) | Existing project pattern (Phase 63 D-01); zero new infra. |
| Mirror-bucket opponent rate "computed on the frontend" | A second TS helper that re-derives `opponent_conversion_pct` from `loss_pct` in Phase 87 | Surface the field on the API schema (D-07) — same pattern as `MaterialRow.opponent_score` | Consistency with Section 2's existing wire format. Avoids two code paths drifting (the same issue D-08 flags but D-07 resolves). |
| Per-class `_MIN_OPPONENT_SAMPLE` threshold | A new `PER_CLASS_OPPONENT_SAMPLE_MIN` constant | Reuse the existing `_MIN_OPPONENT_SAMPLE = 10` in `endgame_service.py:233` | Phase 60 set the threshold globally; Phase 84 deferred ideas explicitly list this as out-of-scope unless Phase 87 hits sparse-n issues. |
| Custom benchmark statistic for p50 | Recomputing from raw DB | Use the published `reports/benchmarks-2026-05-12.md` §6 values verbatim (D-03) | Single canonical source; consumed by other v1.17 phases. |

**Key insight:** This is a "thread an existing pattern" phase, not a "design a new system" phase. Every architectural decision is anchored to a prior phase (60, 63, 82, 83), and the planner should resist the urge to invent new abstractions.

## Common Pitfalls

### Pitfall 1: Pydantic v2 — default values on new schema fields create ordering issues
**What goes wrong:** Adding `opponent_conversion_pct: float | None = None` BEFORE existing required fields raises `PydanticUserError` (non-default arg after default).
**Why it happens:** Pydantic v2 inherits Python's rule that fields with defaults must come after fields without defaults when using positional-style construction. The class is built via `BaseModel` but the same constraint applies.
**How to avoid:** Add the 4 new fields at the END of `ConversionRecoveryStats`. None of the existing 10 fields have defaults (all are required `int` / `float`), so the new `float | None` field can either (a) be required (no default) and appended, or (b) be `float | None = None` and appended — both work. Service-layer constructors must pass all 4 explicitly in both cases (cleaner and matches the existing `ConversionRecoveryStats(...)` instantiation at `endgame_service.py:357-368`).
**Warning signs:** ty / pytest collection error at module import time; not at test-run time.

### Pitfall 2: Codegen output bytes differ from current emission
**What goes wrong:** The codegen produces a single TS object literal per class. Adding a third key changes the formatting; any whitespace / trailing-comma drift from the current emission style causes the CI drift guard to fail on the FIRST run of the codegen even though no logic is broken.
**Why it happens:** The current `_format_per_class_gauge_zones()` puts the whole `{ conversion: [...], recovery: [...] }` on one line. Adding `p50` to that line keeps the pattern; splitting across lines changes whitespace and triggers diff on every existing class entry.
**How to avoid:** Append `p50` as a third key on the same line. Example output: `rook: { conversion: [0.65, 0.75], recovery: [0.26, 0.36], p50: { conversion: 0.71, recovery: 0.30 } },`. Re-run codegen locally and commit both the script + the regenerated `endgameZones.ts` in one commit.
**Warning signs:** CI "Zone drift check" step fails with a multi-line diff covering every class — that's whitespace, not logic.

### Pitfall 3: Mirror identity confusion — recovery_pct vs save rate
**What goes wrong:** `ConversionRecoveryStats.recovery_pct` is the user's `(wins + draws) / games` save rate (D-09), NOT a pure win rate. The opponent's "recovery" in the same mirror identity should also be `(opp_wins + opp_draws) / games_in_user_conversion_bucket` = `(user_losses + user_draws) / user_conversion_games`. Mixing up the user's win-rate-for-conversion-bucket and save-rate-for-recovery-bucket is the easiest place to introduce an off-by-1pp error.
**Why it happens:** Conversion is defined as pure win rate (`conversion_pct = conversion_wins / conversion_games`); Recovery is defined as save rate (`recovery_pct = (recovery_wins + recovery_draws) / recovery_games`). The two have asymmetric definitions, so the mirror formulas are not symmetric either.
**How to avoid:** Use these exact formulas, matching D-07:
- `opp_conv_pct[X]`: opp's wins (= user's losses) in user's recovery bucket of class X, scaled to opp's conv definition (pure win rate) → `(user_recovery_games − user_recovery_wins − user_recovery_draws) / user_recovery_games`.
- `opp_recov_pct[X]`: opp's wins + draws (= user's losses + draws) in user's conversion bucket of class X, scaled to opp's recov definition (save rate) → `(user_conversion_losses + user_conversion_draws) / user_conversion_games`.
Wire a test that constructs a 60/40 symmetric scenario per class (analogous to `test_opponent_baseline_symmetric_60_40` at `test_endgame_service.py:1405`).
**Warning signs:** Test where `opp_recov_pct == 1 - user_conv_pct` exactly — this would be true only if conversion were also a save rate; the actual identity has a draw-adjusted offset.

### Pitfall 4: `_MIN_OPPONENT_SAMPLE` threshold semantics — applies to MIRROR sample, not own sample
**What goes wrong:** Setting `opponent_conversion_pct = None` when `recovery_games < _MIN_OPPONENT_SAMPLE`, but accidentally also gating the `conversion_pct` field on the recovery sample, or gating opponent fields on `conversion_games` instead of `recovery_games`.
**Why it happens:** The user's stat is gated on the user's own sample size; the opponent's stat is gated on the MIRROR sample (where the opponent's actions actually happened). The two thresholds live in different buckets per stat. Section 2's pattern at `endgame_service.py:838-842` uses `swap_games`, not the row's own `bucket_games[b2]`, for the threshold check — replicate that exactly.
**How to avoid:** Mirror map explicit in code:
- `opponent_conversion_*` gates on `user_recovery_games >= _MIN_OPPONENT_SAMPLE`
- `opponent_recovery_*` gates on `user_conversion_games >= _MIN_OPPONENT_SAMPLE`
Add a test for the "below threshold" case (analogous to `test_opponent_baseline_below_threshold_9_games` at `test_endgame_service.py:1446`).
**Warning signs:** A user with 100 conversion games and 5 recovery games shows `opponent_conversion_pct` as a value (should be None — opp's conv sample is the user's recovery sample = 5 < 10).

### Pitfall 5: ConversionRecoveryStats is constructed in exactly one place
**What goes wrong:** Searching the codebase for additional construction sites and updating multiple call sites unnecessarily.
**Why it happens:** Past phases (60, 78, 82) added similar fields to multiple schemas; ConversionRecoveryStats is misleadingly simple by comparison.
**How to avoid:** It's constructed only at `app/services/endgame_service.py:357` (inside `_aggregate_endgame_stats`). Tests construct it via the service helper, not directly. Only one wire-up point.
**Warning signs:** `grep -rn "ConversionRecoveryStats(" app/` returns more than one match outside `endgame_service.py:357` and the schema definition.

### Pitfall 6: Floating-point formatting drift in codegen
**What goes wrong:** `f"{0.30}"` emits `"0.3"`, `f"{0.20}"` emits `"0.2"` (Python's default `repr`/`str` strips trailing zeros). The current generated file already has `recovery: [0.2, 0.3]` for queen — confirmed at `frontend/src/generated/endgameZones.ts:69`. If p50 values are passed as Python floats (e.g. `0.30`), they'll emit as `0.3`, which is fine, but if you transcribe verbatim as `0.2963` and round in Python (`round(0.2963, 2) = 0.3`), emission becomes `0.3` (single-digit decimal). Mixed precision across classes (e.g. `0.7098 → 0.71`, but `0.6940 → 0.69`) is fine; the worry is unexpected stripping.
**Why it happens:** Python's f-string formatting of floats uses `repr` by default, which strips trailing zeros. Recharts / consumer code reads these as numbers and is whitespace-agnostic, but the CI drift guard is byte-exact.
**How to avoid:** Decide 2dp vs 4dp at the planner level and use a fixed-precision format string consistently: e.g. `f"{p50_c:.2f}"` for 2dp. Don't mix raw `f"{val}"` with rounded values — the formatting must be deterministic. Match the IQR style: current code emits IQR values with no `:.Nf` format string (uses raw Python repr), so 2dp values like `0.70`, `0.71` will render as `0.7`, `0.71`. If you want stable 2dp display, use `:.2f`; if you want consistency with the existing emission style, use the raw `f"{val}"` and accept trailing-zero stripping.
**Warning signs:** Codegen produces `p50: { conversion: 0.7, recovery: 0.3 }` for rook and `p50: { conversion: 0.69, recovery: 0.33 }` for minor_piece in the same file — inconsistency caused by `repr` of `0.70` vs `0.69`.

## Runtime State Inventory

Not applicable — Phase 84 is not a rename / refactor / migration phase. No databases, services, OS-registered state, secrets, or build artifacts carry stale identifiers that need updating.

- Stored data: None — adding fields to API response, not changing stored data. PostgreSQL schema is untouched. No Alembic migration.
- Live service config: None — no n8n / Datadog / Tailscale references to endgame stats schema field names.
- OS-registered state: None.
- Secrets/env vars: None.
- Build artifacts: `frontend/src/generated/endgameZones.ts` is regenerated by codegen (in-repo build artifact; the only one). No installed-package egg-info, Docker image tag, or npm global concerns.

## Code Examples

### Example 1: Extending `PerClassBands` (DATA-01)

```python
# app/services/endgame_zones.py — after edit
# Source: app/services/endgame_zones.py:320-339 (existing pattern)

@dataclass(frozen=True)
class PerClassBands:
    """Typical [lower, upper] bands and centre p50 tick for Conv/Recov.

    p50 is the pooled per-class typical centre, source: reports/benchmarks-2026-05-12.md
    §6 mean (≈ per-user p50, diverges by ≤0.01 — see §5). Used by Section 3
    cohort bullet centre tick (Phase 87 consumer).
    """

    conversion: tuple[float, float]
    recovery: tuple[float, float]
    p50: tuple[float, float]  # (conversion_p50, recovery_p50)


PER_CLASS_GAUGE_ZONES: Mapping[EndgameClass, PerClassBands] = {
    "rook":        PerClassBands(conversion=(0.65, 0.75), recovery=(0.26, 0.36), p50=(0.71, 0.30)),
    "minor_piece": PerClassBands(conversion=(0.63, 0.73), recovery=(0.31, 0.41), p50=(0.69, 0.33)),
    "pawn":        PerClassBands(conversion=(0.67, 0.79), recovery=(0.23, 0.34), p50=(0.74, 0.28)),
    "queen":       PerClassBands(conversion=(0.73, 0.83), recovery=(0.20, 0.30), p50=(0.77, 0.23)),
    "mixed":       PerClassBands(conversion=(0.65, 0.75), recovery=(0.28, 0.38), p50=(0.69, 0.31)),
    "pawnless":    PerClassBands(conversion=(0.70, 0.80), recovery=(0.21, 0.31), p50=(0.79, 0.20)),
}
```

### Example 2: Extending `_format_per_class_gauge_zones` (DATA-01)

```python
# scripts/gen_endgame_zones_ts.py — after edit
# Source: scripts/gen_endgame_zones_ts.py:67-78 (existing pattern)

def _format_per_class_gauge_zones() -> str:
    """Emit the PER_CLASS_GAUGE_ZONES object literal.

    Each class entry has { conversion: [lower, upper], recovery: [lower, upper],
    p50: { conversion: <num>, recovery: <num> } }. Consumers wrap conversion/recovery
    with colorizeGaugeZones() on the FE side; p50 feeds the cohort bullet centre tick.
    """
    lines: list[str] = []
    for cls, bands in PER_CLASS_GAUGE_ZONES.items():
        c_lo, c_hi = bands.conversion
        r_lo, r_hi = bands.recovery
        p50_c, p50_r = bands.p50
        lines.append(
            f"  {cls}: {{ conversion: [{c_lo}, {c_hi}], "
            f"recovery: [{r_lo}, {r_hi}], "
            f"p50: {{ conversion: {p50_c}, recovery: {p50_r} }} }},"
        )
    return "\n".join(lines) + "\n"
```

Expected TS emission (using 2dp values as example):
```ts
export const PER_CLASS_GAUGE_ZONES = {
  rook: { conversion: [0.65, 0.75], recovery: [0.26, 0.36], p50: { conversion: 0.71, recovery: 0.3 } },
  minor_piece: { conversion: [0.63, 0.73], recovery: [0.31, 0.41], p50: { conversion: 0.69, recovery: 0.33 } },
  // ...
} as const;
```

### Example 3: Extending `ConversionRecoveryStats` (DATA-02 schema)

```python
# app/schemas/endgames.py — after edit
# Source: app/schemas/endgames.py:19-42 (existing pattern)

class ConversionRecoveryStats(BaseModel):
    """Inline conversion/recovery stats for one endgame category.

    Phase 60 / Phase 84: opponent_* fields mirror MaterialRow's pattern,
    derived from same-game symmetry within this class. opp_conv_pct gates on
    user_recovery_games (the mirror sample); opp_recov_pct gates on
    user_conversion_games. Both go to None when the mirror sample is below
    _MIN_OPPONENT_SAMPLE (== 10, defined in endgame_service.py).
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

    # Phase 84 (DATA-02): per-type opponent baselines via same-game symmetry,
    # mirroring MaterialRow.opponent_score / opponent_games (Phase 60).
    opponent_conversion_pct: float | None
    opponent_conversion_games: int
    opponent_recovery_pct: float | None
    opponent_recovery_games: int
```

### Example 4: Wiring opponent rates in service (DATA-02 wire-up)

```python
# app/services/endgame_service.py — after edit
# Source: app/services/endgame_service.py:340-368 (existing _aggregate_endgame_stats body)

# ... existing per-class accumulator math computes:
#   conversion_games, conversion_wins, conversion_draws, conversion_losses, conversion_pct
#   recovery_games,   recovery_wins,   recovery_draws,   recovery_saves,    recovery_pct

# Mirror identity (same-game symmetry, scoped to this class):
# opp_conv = opp_wins in user's recovery bucket of class X
#          = user_losses in user's recovery bucket of class X
#          = recovery_games - recovery_wins - recovery_draws
opp_conv_losses_equiv = recovery_games - recovery_wins - recovery_draws
if recovery_games >= _MIN_OPPONENT_SAMPLE:
    opp_conv_pct: float | None = round(opp_conv_losses_equiv / recovery_games * 100, 1)
else:
    opp_conv_pct = None

# opp_recov = opp_wins + opp_draws in user's conversion bucket of class X
#           = user_losses + user_draws in user's conversion bucket of class X
opp_recov_saves_equiv = conversion_losses + conversion_draws
if conversion_games >= _MIN_OPPONENT_SAMPLE:
    opp_recov_pct: float | None = round(opp_recov_saves_equiv / conversion_games * 100, 1)
else:
    opp_recov_pct = None

conversion_stats = ConversionRecoveryStats(
    conversion_pct=conversion_pct,
    conversion_games=conversion_games,
    conversion_wins=conversion_wins,
    conversion_draws=conversion_draws,
    conversion_losses=conversion_losses,
    recovery_pct=recovery_pct,
    recovery_games=recovery_games,
    recovery_saves=recovery_saves,
    recovery_wins=recovery_wins,
    recovery_draws=recovery_draws,
    opponent_conversion_pct=opp_conv_pct,
    opponent_conversion_games=recovery_games,  # mirror sample
    opponent_recovery_pct=opp_recov_pct,
    opponent_recovery_games=conversion_games,  # mirror sample
)
```

Note: percentages on `_pct` fields are 0-100 (matches existing `conversion_pct` / `recovery_pct` convention at `endgame_service.py:346, 354`). DO NOT switch to 0.0-1.0 — that would break Section 3's existing per-class reads.

### Example 5: Mirror identity unit test (per-type, follows Phase 60 template)

```python
# tests/test_endgame_service.py — new tests in TestAggregateEndgameStats
# Source: tests/test_endgame_service.py:1405-1432 (Section 2 template to follow)

def test_per_type_opponent_conversion_pct_mirror_identity(self):
    """For class=rook, user Conv 60% (60W/0D/40L) and user Recov 40% (40W/0D/60L):
    opp_conv_pct on rook = user_losses_in_recovery / recovery_games
                         = 60 / 100 = 60.0%.
    opp_recov_pct on rook = (user_conv_losses + user_conv_draws) / conv_games
                          = (40 + 0) / 100 = 40.0%.
    """
    rows = (
        [(i, 1, "1-0", "white", 150, None) for i in range(60)]       # conv wins
        + [(i + 60, 1, "0-1", "white", 150, None) for i in range(40)]  # conv losses
        + [(i + 100, 1, "1-0", "white", -150, None) for i in range(40)]  # recov wins
        + [(i + 140, 1, "0-1", "white", -150, None) for i in range(60)]  # recov losses
    )
    result = _aggregate_endgame_stats(rows)
    rook = next(c for c in result if c.endgame_class == "rook")
    assert rook.conversion.opponent_conversion_pct == pytest.approx(60.0, abs=0.1)
    assert rook.conversion.opponent_conversion_games == 100  # mirror = recovery_games
    assert rook.conversion.opponent_recovery_pct == pytest.approx(40.0, abs=0.1)
    assert rook.conversion.opponent_recovery_games == 100   # mirror = conversion_games


def test_per_type_opponent_pct_none_below_threshold(self):
    """User has 100 conv games but only 9 recov games -> opp_conv_pct is None
    (mirror sample 9 < _MIN_OPPONENT_SAMPLE=10), opp_conv_games == 9.
    opp_recov_pct is still computed (mirror sample = 100 >= 10).
    """
    rows = (
        [(i, 1, "1-0", "white", 150, None) for i in range(100)]
        + [(i + 100, 1, "0-1", "white", -150, None) for i in range(9)]
    )
    result = _aggregate_endgame_stats(rows)
    rook = next(c for c in result if c.endgame_class == "rook")
    assert rook.conversion.opponent_conversion_pct is None
    assert rook.conversion.opponent_conversion_games == 9
    assert rook.conversion.opponent_recovery_pct is not None
    assert rook.conversion.opponent_recovery_games == 100
```

### Example 6: p50 field presence unit test (follows existing pattern)

```python
# tests/services/test_endgame_zones.py — new test class
# Source: tests/services/test_endgame_zones.py:191-240 (TestRegistrySanity template)

class TestPerClassP50:
    """Phase 84 (DATA-01): per-class p50 centre tick on PerClassBands."""

    def test_all_six_classes_have_p50(self) -> None:
        """PER_CLASS_GAUGE_ZONES carries p50 for every EndgameClass.

        Source: reports/benchmarks-2026-05-12.md §6 pooled-by-class summary.
        """
        from app.services.endgame_zones import PER_CLASS_GAUGE_ZONES
        for cls in ("rook", "minor_piece", "pawn", "queen", "mixed", "pawnless"):
            bands = PER_CLASS_GAUGE_ZONES[cls]
            assert isinstance(bands.p50, tuple)
            assert len(bands.p50) == 2
            conv_p50, recov_p50 = bands.p50
            assert 0.0 <= conv_p50 <= 1.0
            assert 0.0 <= recov_p50 <= 1.0

    def test_rook_p50_matches_benchmark(self) -> None:
        """Source: reports/benchmarks-2026-05-12.md §6, line 435 (rook row)."""
        from app.services.endgame_zones import PER_CLASS_GAUGE_ZONES
        conv_p50, recov_p50 = PER_CLASS_GAUGE_ZONES["rook"].p50
        assert conv_p50 == pytest.approx(0.71, abs=0.005)
        assert recov_p50 == pytest.approx(0.30, abs=0.005)

    def test_p50_inside_iqr_for_most_classes(self) -> None:
        """Sanity check: pooled p50 generally falls inside the IQR band, though
        D-05 notes pawnless conversion sits at the high edge of [0.70, 0.80].
        This is a soft check — it documents the relationship, not enforces it."""
        from app.services.endgame_zones import PER_CLASS_GAUGE_ZONES
        for cls in ("rook", "minor_piece", "pawn", "queen", "mixed"):
            bands = PER_CLASS_GAUGE_ZONES[cls]
            c_lo, c_hi = bands.conversion
            r_lo, r_hi = bands.recovery
            conv_p50, recov_p50 = bands.p50
            assert c_lo <= conv_p50 <= c_hi, f"{cls} conv_p50={conv_p50} outside [{c_lo}, {c_hi}]"
            assert r_lo <= recov_p50 <= r_hi, f"{cls} recov_p50={recov_p50} outside [{r_lo}, {r_hi}]"
```

## State of the Art

Not a research-driven phase. The implementation pattern is established by Phase 60 (mirror-bucket opponent baseline), Phase 63 (Python-authoritative zone registry with codegen + CI drift guard), and Phase 82/83 (most recent codegen extensions).

| Old Approach | Current Approach | When Changed | Impact |
|---|---|---|---|
| Frontend-only zone constants in `EndgameScoreGapSection.tsx` (`FIXED_GAUGE_ZONES` literal) | Python-authoritative + TS codegen via `gen_endgame_zones_ts.py` | Phase 63 D-01 (`zone-registry-rollup`) | All new bands go through Python; FE imports from `generated/endgameZones.ts`. |
| Section 2 peer baseline = global average of all users (Phase 53) | Mirror-bucket same-game symmetry (`opponent_score = 1 − user_score[swap_bucket]`), gated on `_MIN_OPPONENT_SAMPLE=10` | Phase 60 | Filter-responsive, self-calibrating opponent signal. Phase 84 extends this to per-class. |
| Per-class p50 implicit (consumer infers from IQR midpoint) | Per-class p50 explicit on `PerClassBands` | Phase 84 (this phase) | Section 3 cohort bullets in Phase 87 read the centre tick directly; no FE-side derivation. |

**Deprecated/outdated:** None relevant to this phase.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|---|---|---|
| A1 | Rounding p50 values to 2dp matches the IQR band granularity (e.g. `(0.65, 0.75)`) and avoids the trailing-zero-stripping inconsistency in Pitfall 6 | Recommendation in Summary + Example 1 / 2 | Plan-phase may pick 4dp instead; both are allowed by D-03. The codegen byte output and the test tolerance change accordingly. No functional risk. |
| A2 | `ConversionRecoveryStats` is constructed only at `endgame_service.py:357`; no other module instantiates it directly. Confirmed via `grep -n "ConversionRecoveryStats(" app/` → one hit. | Pitfall 5 + Example 4 | If a test fixture or another service quietly constructs the schema with positional args, adding 4 new required fields breaks it. ty + pytest would catch at collection time. Low risk. |
| A3 | The 4 new fields use 0-100 scale for `_pct` (matching existing `conversion_pct` / `recovery_pct`), not 0.0-1.0 | Example 4 | If Phase 87 consumers expect 0.0-1.0 like `MaterialRow.score`, there's a unit mismatch. The decision is forced by the existing fields on the same dataclass — keeping uniform scale within `ConversionRecoveryStats` is the safest call. Plan-phase should confirm. |
| A4 | `ScoreGapTimelinePoint`, `MaterialRow`, and other `ScoreGapMaterialResponse` consumers are untouched by this phase | Architectural map | If Section 3 frontend in Phase 87 needs `MaterialRow`-style fields (e.g. parity opponent) for the per-type card, that's a Phase 87 schema additive change, not a Phase 84 regression. |

## Open Questions (RESOLVED)

1. **2dp vs 4dp p50 formatting** — What precision should `_format_per_class_gauge_zones()` emit for p50 values?
   - What we know: D-03 allows either; the existing IQR emission uses raw Python float repr (e.g. `0.65`, `0.2` for `0.20`).
   - What's unclear: Whether the planner wants byte-stable 2dp (`f"{val:.2f}"`) or default repr that strips trailing zeros.
   - Recommendation: **2dp via `f"{val:.2f}"`** for visual consistency with the published benchmarks table and to avoid the inconsistency described in Pitfall 6. Verify the existing IQR emission style is unchanged (don't accidentally reformat lines that already exist).
   - **RESOLVED:** 2dp via `f"{val:.2f}"` for byte-stable emission. Rationale: matches IQR band granularity (also 2dp), avoids trailing-zero-strip drift (Pitfall 6), and the ≤0.005 precision loss is well below any user-visible threshold for the bullet centre tick.

2. **Test placement for codegen output** — Should there be an integration test that runs `gen_endgame_zones_ts.py` and parses the result?
   - What we know: CI runs the codegen + `git diff --exit-code`. That's effectively an integration test.
   - What's unclear: Whether unit-level Python tests should reach into the emitted TS or just verify `PerClassBands.p50` is populated.
   - Recommendation: **Keep Python tests at the dataclass level only** (Example 6). The CI drift guard covers TS output; duplicating that in unit tests reads as belt-and-suspenders and increases test maintenance.
   - **RESOLVED:** Dataclass-level Python tests in `tests/services/test_endgame_zones.py::TestPerClassP50` only. Rationale: CI drift guard (`gen_endgame_zones_ts.py + git diff --exit-code`) already covers the TS emission. Duplicating the assertion in TS would create two-source-of-truth drift risk.

3. **Rounding strategy on `_pct` opponent fields** — The existing `conversion_pct` / `recovery_pct` use `round(x, 1)` for 1dp percent values. Should the new opponent fields match?
   - What we know: Lines 346 and 354 in `endgame_service.py` use `round(..., 1)`. Phase 60's `MaterialRow.score` is full-precision float.
   - Recommendation: **Match the existing `round(..., 1)` style** (1dp percentage on `_pct` fields) for consistency within the same dataclass. Example 4 reflects this.
   - **RESOLVED:** `round(..., 1)` matching the existing convention at `app/services/endgame_service.py:346, 354` on `conversion_pct` / `recovery_pct`. Rationale: same scale, same precision, same display convention. Tests use `pytest.approx(..., abs=0.1)`.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|---|---|---|---|---|
| Python 3.13 | Backend codegen + tests | ✓ | 3.13 (per `pyproject.toml` and CLAUDE.md) | — |
| uv | `uv run python scripts/gen_endgame_zones_ts.py`, `uv run pytest`, `uv run ty check`, `uv run ruff` | ✓ (project standard) | — | — |
| pytest | Unit tests | ✓ | 8.x (project dep) | — |
| ty | Type check on new schema field | ✓ | latest pinned in pyproject | — |
| Node / npm | Frontend lint / build NOT part of this phase | n/a | n/a | Phase 84 doesn't touch FE source beyond the codegen output, which is checked-in TS. The frontend build only consumes the regenerated `endgameZones.ts` when Phase 85+ runs. |
| Dev PostgreSQL | Not required (no DB queries / migrations) | n/a | n/a | Pure schema + service refactor; no DB touch. |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** None.

## Validation Architecture

### Test Framework

| Property | Value |
|---|---|
| Framework | pytest 8.x (declared in `pyproject.toml`) |
| Config file | `pyproject.toml` (project standard) + existing `tests/` tree |
| Quick run command | `uv run pytest tests/services/test_endgame_zones.py tests/test_endgame_service.py -x` |
| Full suite command | `uv run pytest` |
| Zone drift guard | `uv run python scripts/gen_endgame_zones_ts.py && git diff --exit-code frontend/src/generated/endgameZones.ts` |
| Type check | `uv run ty check app/ tests/` (zero errors required per CLAUDE.md) |
| Lint | `uv run ruff check .` |
| Format | `uv run ruff format .` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|---|---|---|---|---|
| DATA-01 | `PerClassBands.p50` exists for all 6 classes, type is `tuple[float, float]`, values in `[0, 1]` | unit | `uv run pytest tests/services/test_endgame_zones.py::TestPerClassP50 -x` | NEW (added Wave 0) |
| DATA-01 | `PerClassBands.p50` values match the published benchmark per class (allow 2dp tolerance for round-half-even) | unit | `uv run pytest tests/services/test_endgame_zones.py::TestPerClassP50::test_rook_p50_matches_benchmark -x` (and analogues per class) | NEW |
| DATA-01 | Codegen produces `endgameZones.ts` that includes a `p50: { conversion: …, recovery: … }` key for each of the 6 classes | integration (CI drift guard) | `uv run python scripts/gen_endgame_zones_ts.py && git diff --exit-code frontend/src/generated/endgameZones.ts` | EXISTS (`.github/workflows/ci.yml:47-50`) |
| DATA-01 | (Sanity) p50 falls inside the IQR band for most classes (documents the relationship; pawnless flagged in D-05) | unit | `uv run pytest tests/services/test_endgame_zones.py::TestPerClassP50::test_p50_inside_iqr_for_most_classes -x` | NEW |
| DATA-02 | `ConversionRecoveryStats` carries 4 new fields with correct types (`float \| None` for `_pct`, `int` for `_games`) | unit (schema shape) | `uv run pytest tests/test_endgame_service.py -k opponent -x` + `uv run ty check app/ tests/` | EXISTS file; NEW tests |
| DATA-02 | Mirror identity: opp_conv_pct = user_losses_in_recovery / recovery_games (per-class scoped) | unit | `uv run pytest tests/test_endgame_service.py::TestAggregateEndgameStats::test_per_type_opponent_conversion_pct_mirror_identity -x` | NEW |
| DATA-02 | Mirror identity: opp_recov_pct = (user_conv_losses + user_conv_draws) / conversion_games (per-class scoped) | unit | `uv run pytest tests/test_endgame_service.py::TestAggregateEndgameStats::test_per_type_opponent_recovery_pct_mirror_identity -x` | NEW |
| DATA-02 | `opponent_*_pct` is `None` when mirror sample < 10; `opponent_*_games` always populated regardless | unit | `uv run pytest tests/test_endgame_service.py::TestAggregateEndgameStats::test_per_type_opponent_pct_none_below_threshold -x` | NEW |
| DATA-02 | `opponent_*_pct` is computed at the boundary (mirror sample == 10) | unit | `uv run pytest tests/test_endgame_service.py::TestAggregateEndgameStats::test_per_type_opponent_pct_at_threshold_10 -x` | NEW |
| DATA-02 | Zero-sample class: when both `conversion_games == 0` and `recovery_games == 0`, fields stay sane (no DivByZero) | unit | `uv run pytest tests/test_endgame_service.py::TestAggregateEndgameStats::test_per_type_opponent_zero_sample -x` | NEW |

### Measurable Behaviors Exposed

- **New `p50` field exposes:** the per-class typical centre tick (one float per class × {conversion, recovery}). Measurable as a value lookup on `PER_CLASS_GAUGE_ZONES[<class>].p50.{conversion,recovery}` from the frontend, and as `bands.p50` on the Python dataclass. Phase 87 will compare a user's per-class rate to this tick; this phase only confirms the value is present and matches the benchmark.
- **New opponent fields expose:** the same-game-symmetric opponent baseline for one `EndgameClass`. Measurable as four fields on each `ConversionRecoveryStats` instance under `EndgameStatsResponse.categories[*].conversion`. The 0-100 percentage scale matches the existing `conversion_pct` / `recovery_pct` convention on the same dataclass. Phase 87 will compute `myRate − oppRate` for per-class peer bullets; this phase only locks the wire shape and verifies the identity.

### Sampling Rate

- **Per task commit:** `uv run pytest tests/services/test_endgame_zones.py tests/test_endgame_service.py -x` (target zone + service modules, ~2 seconds)
- **Per wave merge:** `uv run pytest && uv run ty check app/ tests/ && uv run ruff check . && uv run python scripts/gen_endgame_zones_ts.py && git diff --exit-code frontend/src/generated/endgameZones.ts`
- **Phase gate:** Full suite green before `/gsd-verify-work`, including the CI drift guard and ty zero-errors.

### Wave 0 Gaps

- [ ] `tests/services/test_endgame_zones.py::TestPerClassP50` — covers DATA-01 (new test class, ~3 tests + per-class values). Existing file structure has `TestAssignZone`, `TestRegistrySanity`, etc. — append a new class.
- [ ] `tests/test_endgame_service.py::TestAggregateEndgameStats` per-type opponent tests — covers DATA-02 (new tests appended to existing class around line 220). Existing test patterns at lines 1405-1470 (Phase 60 Section 2 mirror) are the direct template.
- [ ] (No new test FILES required.) (No framework install required.) (No conftest changes required.)

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---|---|---|
| V2 Authentication | no | Phase 84 adds fields to an authenticated endpoint (`/api/endgames/overview`) that already enforces auth via FastAPI-Users; no auth-layer changes. |
| V3 Session Management | no | No session-handling changes. |
| V4 Access Control | no | Endpoint authz unchanged; the new fields surface only the user's own opponent baseline (derived from the user's own games via same-game symmetry). No PII / no cross-user data leak. |
| V5 Input Validation | yes | New Pydantic v2 fields on `ConversionRecoveryStats` are response-only (output); Pydantic enforces type at serialization. No new input validation needed. |
| V6 Cryptography | no | No cryptographic primitives. |
| V8 Data Protection | no | No new PII. Opponent-derived stats are arithmetic identities on the user's own WDL — same data the user already sees. |
| V14 Configuration | no | No config changes. |

### Known Threat Patterns for FastAPI / Pydantic v2 stack

| Pattern | STRIDE | Standard Mitigation |
|---|---|---|
| Schema field added with sensitive data leaking cross-user | Information Disclosure | Verified: opponent stats are derived per-call from the requesting user's own filtered games (same-game symmetry), not joined to any other user's data. The DB query in `_aggregate_endgame_stats` is gated by `user_id` on every path. |
| Default value on Pydantic field allows None where caller expects int | Tampering / Logic | `opponent_*_games: int` (no default; always populated as the mirror sample size, even when below the threshold — matches Phase 60 `MaterialRow.opponent_games: int`). `opponent_*_pct: float \| None` (intentional). |
| Drift between Python source and TS mirror introducing inconsistent zone classification | Tampering | Existing CI drift guard (`ci.yml:47-50`) prevents committed inconsistency. |
| Float-precision divergence between Python computation and frontend display | Logic | `round(..., 1)` on percentage fields, matching existing convention. Tests use `pytest.approx(..., abs=0.1)`. |

No new threats specific to this phase. The pattern is purely additive on existing, audited endpoints.

## Sources

### Primary (HIGH confidence)

- `app/services/endgame_zones.py` (lines 1-435, full file read) - `PerClassBands` + `PER_CLASS_GAUGE_ZONES` location and shape; existing patterns
- `app/services/endgame_service.py` (lines 220-388 and 770-865 read) - `_aggregate_endgame_stats` accumulator structure; Section 2 mirror-bucket template
- `app/schemas/endgames.py` (lines 1-491 full file read) - `ConversionRecoveryStats`, `EndgameCategoryStats`, `MaterialRow`, `EndgameOverviewResponse` shapes
- `scripts/gen_endgame_zones_ts.py` (lines 1-157 full file read) - codegen function to extend + invocation pattern
- `frontend/src/generated/endgameZones.ts` (lines 1-75 full file read) - current emitted TS shape; trailing-zero stripping behaviour confirmed (`0.2`, `0.3`)
- `frontend/src/components/charts/EndgameScoreGapSection.tsx` (lines 100-160 read) - `MIRROR_BUCKET` map + `opponentRate()` helper; confirms mirror-identity math
- `reports/benchmarks-2026-05-12.md` §6 (lines 431-465 read) - p50 values verified: rook 0.7098/0.2963, minor_piece 0.6949/0.3278, pawn 0.7379/0.2754, queen 0.7744/0.2343, mixed 0.6940/0.3111, pawnless 0.7913/0.1976 — exact match with D-03
- `tests/services/test_endgame_zones.py` (lines 1-241 full file read) - existing test patterns for `TestRegistrySanity`, boundary tests; template for new `TestPerClassP50` class
- `tests/test_endgame_service.py` (lines 220-320 + 1380-1470 read) - existing test patterns for `_aggregate_endgame_stats` and `TestScoreGapMaterialOpponentBaseline` (Section 2 template)
- `.github/workflows/ci.yml` (lines 40-65 read) - CI drift-guard invocation confirmed at lines 47-50

### Secondary (MEDIUM confidence)

- `.planning/REQUIREMENTS.md` - DATA-01 / DATA-02 wording authoritative
- `.planning/milestones/v1.17-ROADMAP.md` - Phase 84 success criteria authoritative
- `.planning/milestones/v1.17-phases/84-*/84-CONTEXT.md` - locked decisions D-01 through D-11
- CLAUDE.md - type-safety, ty-compliance, no-bare-strings, mirror-mobile-when-touching-FE rules

### Tertiary (LOW confidence)

None — every claim in this research is verified against actual code or the locked CONTEXT.md.

## Project Constraints (from CLAUDE.md)

Directives that apply to this phase:

- **No magic numbers** — extract `_MIN_OPPONENT_SAMPLE` (already a constant at `endgame_service.py:233`); reuse it for the mirror sample threshold check. Don't inline `10`.
- **Type safety / no bare `str`** — keep `EndgameClass = Literal[...]` throughout. New schema fields use `float | None` and `int`, no `Any`.
- **ty compliance** — all new code must pass `uv run ty check app/ tests/` with zero errors. Annotate return types on any new helper. Use `Sequence[str]` over `list[str]` for parameter annotations only if the function accepts both lists and tuples.
- **Comment bug fixes / non-obvious code** — annotate the mirror-identity computation with the same-game-symmetry rationale and the `_MIN_OPPONENT_SAMPLE` reuse reason. Example 4 illustrates.
- **Function size limits** — `_aggregate_endgame_stats` is already a ~150-line accumulator with the additions; under the 200 logic-LOC hard limit. The added mirror-identity block is ~12 lines per class — well within limits. Don't introduce a context dataclass for the 4 new accumulator outputs (Pitfall 5 + CLAUDE.md "don't invent context dataclasses for fewer than 3 threaded fields").
- **No `asyncio.gather` on the same `AsyncSession`** — not applicable; this phase doesn't touch async paths.
- **Sentry** — `_aggregate_endgame_stats` already has a Sentry capture for unknown class ints (lines 287-292); no new exception sites added.
- **`MIN_OPPONENT_BASELINE_GAMES` vs `_MIN_OPPONENT_SAMPLE`** — note: `endgame_service.py` defines `_MIN_OPPONENT_SAMPLE = 10` (the backend threshold). The frontend has a `MIN_OPPONENT_BASELINE_GAMES` constant used in `EndgameScoreGapSection.tsx` for the gating display. These are conceptually the same threshold but live in two places. This phase doesn't change either; Phase 87 will read the backend-supplied `opponent_*_games` and apply the frontend constant for display gating. Document this in the audit doc.
- **Browser automation rules / `data-testid`** — not applicable (no FE changes).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — Python 3.13 / Pydantic v2 / pytest already in pyproject; no new deps.
- Architecture: HIGH — every modified file location is verified; the wire path through `_aggregate_endgame_stats → EndgameStatsResponse.categories → EndgameOverviewResponse.stats` is read directly from code.
- Pitfalls: HIGH — anchored to concrete file:line references and the Section 2 template, not speculation. Pitfall 6 (float formatting) is the only one inferred from Python semantics rather than observed; it's documented as a "warning sign", not a known regression.
- Benchmarks values (D-03): HIGH — verified verbatim against `reports/benchmarks-2026-05-12.md` lines 435-440.

**Research date:** 2026-05-12
**Valid until:** 2026-06-11 (~30 days — stable codebase, no external dependency churn expected on Python/Pydantic/pytest stack in this window)
