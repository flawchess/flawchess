# Phase 84: Data plumbing — mirror-rate audit - Research

**Researched:** 2026-05-12
**Domain:** Backend Pydantic v2 schema extension + service-layer mirror-bucket identity (FastAPI / SQLAlchemy 2.x async)
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Section 2 audit (DATA-02 — already wired):**
- **D-01:** Section 2 is already wired. `MaterialRow.opponent_score: float | None` + `MaterialRow.opponent_games: int` were added in Phase 60 (`app/services/endgame_service.py:824-855`), wired into `/api/endgames/overview` via `ScoreGapMaterialResponse.material_rows` (`app/schemas/endgames.py:215-237, 285-303`), and consumed by `EndgameScoreGapSection.tsx:111-145` (`opponentRate()` + `MIRROR_BUCKET`). The Skill peer baseline `Opp Skill` is derivable from the existing `MaterialRow[conversion].opponent_score` + `MaterialRow[recovery].opponent_score` — no new payload field needed. No backend work for Section 2.
- **D-02:** Audit deliverable is inline in the phase summary (SUMMARY.md), not a separate `.planning/notes/` file.

**Section 3 schema extension (LOCKED):**
- **D-03:** Add four fields at the end of `ConversionRecoveryStats` in `app/schemas/endgames.py:19-42`, matching the `MaterialRow` pattern (`float | None` for `_pct`, plain `int` for `_games`):
  - `opponent_conversion_pct: float | None`
  - `opponent_conversion_games: int`
  - `opponent_recovery_pct: float | None`
  - `opponent_recovery_games: int`

  Field ordering: append after `recovery_draws`. No defaults. Update model docstring referencing Phase 84.
- **D-04:** Mirror identities (same-game symmetry, scoped to one `EndgameClass = X`):
  - `opp_conv_pct[X] = (user_recovery_games[X] − user_recovery_wins[X] − user_recovery_draws[X]) / user_recovery_games[X]`
  - `opp_recov_pct[X] = (user_conversion_losses[X] + user_conversion_draws[X]) / user_conversion_games[X]`

  Conv is a win-rate (wins only); Recov is a save-rate (wins + draws). Formulas are NOT copy-paste symmetric.
- **D-05:** Threshold gating reuses `_MIN_OPPONENT_SAMPLE = 10` (`app/services/endgame_service.py:233`). Do not introduce a parallel `PER_CLASS_OPPONENT_SAMPLE_MIN`. Gate the `_pct` field on the **mirror** sample size, not the field's own bucket:
  - `opponent_conversion_pct` is `None` when `recovery_games < 10` (else computed).
  - `opponent_recovery_pct` is `None` when `conversion_games < 10` (else computed).
  - `_games` companion fields are always `int` (mirror sample size, possibly `0`), never `None`.
- **D-06:** Wiring site: between line 355 (after `recovery_pct = ...`) and line 357 (`conversion_stats = ConversionRecoveryStats(...)`) in `_aggregate_endgame_stats()`. No new DB query. No new accumulator key.
- **D-07:** Percentage convention: `round(x, 1)` to match the existing `conversion_pct` / `recovery_pct` style (0.0-100.0 scale with one decimal). Do NOT switch to 0.0-1.0 mid-method.
- **D-08:** The four fields are derivable client-side. Ship the schema fields anyway for consistency with `MaterialRow` (one wire shape across Section 2 + Section 3, single backend identity, no FE math drift risk in Phase 87). Flag if implementation cost balloons.

**Sig-test pattern:**
- **D-09:** Wald-z sig-test pattern for Section 3 peer bullets is **Phase 87 scope**. Phase 84 locks only the data shape.

**Phase scope:**
- **D-10:** Phase 84 stays standalone (not folded into 86/87).
- **D-11:** Plan count: 1 plan (was 3 pre-pivot). Planner may split into 2 if audit copy is >~30 lines.

### Claude's Discretion

- **Test placement:** Append a new test class (e.g. `TestPerTypeOpponentBaseline`) inside `TestAggregateEndgameStats` OR add a sibling class alongside `TestScoreGapMaterialOpponentBaseline` — planner picks the seam that matches existing structure.
- **Row-construction helper choice:** `TestAggregateEndgameStats` uses bare tuples (`tests/test_endgame_service.py:184-205`); Section 2 mirror tests use `_FakeRow` (`:1381-1404`). Planner picks whichever fits the chosen test class location.
- **Single-plan vs split:** If audit copy is >~30 lines, planner may split into 2 plans.

### Deferred Ideas (OUT OF SCOPE)

- **Per-class `_MIN_OPPONENT_SAMPLE_PER_CLASS`** — reuse global threshold.
- **Sig-test methodology on per-type peer bullets** — Phase 87 scope (Wald-z on signed difference).
- **Skill peer-bullet sig-test methodology** — Phase 86 scope (SEC2-08).
- **Cell-specific (rating × TC) per-class baselines** (`FUT-04`) — out of scope for v1.17.
- **Per-class Endgame Skill metric** — global composite only.
- **DATA-01 per-type cohort p50 codegen** — DROPPED 2026-05-12 (single-bullet doctrine). Do NOT reintroduce `p50` to `PerClassBands` or `PER_CLASS_GAUGE_ZONES`.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DATA-02 | Mirror-bucket peer rates (`opponentRate` for Conv / Parity / Recov / Skill components in Section 2 and per-type Conv / Recov in Section 3) are exposed on `/api/endgames/overview`; audit existing schema; extend only if not already present. Skill `Opp Skill` derived frontend-side from `opp_conv` + `opp_recov`. | Section 2: already exposed via `MaterialRow.opponent_score` / `opponent_games` (file:line evidence below) — audit is a confirmation in prose. Section 3: gap — `ConversionRecoveryStats` does NOT carry opponent fields. Four new fields land on `ConversionRecoveryStats`, wired in `_aggregate_endgame_stats` via the Phase 60 mirror identity. |

</phase_requirements>

## Project Constraints (from CLAUDE.md)

**Type safety (firm):**
- `EndgameClass = Literal["rook", "minor_piece", "pawn", "queen", "mixed", "pawnless"]` — never bare `str` for the class key. The new mirror identities operate per `EndgameClass`; do not collapse to `dict[str, ...]`.
- All backend code must pass `uv run ty check app/ tests/` with zero errors. ty runs between ruff and pytest in CI.
- Use `# ty: ignore[rule-name]` (not `# type: ignore`) when suppression is unavoidable. None expected for this phase.
- Explicit return type annotations on new helpers (none expected here — wiring is inline inside `_aggregate_endgame_stats`).
- For `float | None` fields, when a local variable is conditionally assigned (computed value or `None`), annotate the local explicitly so ty's flow narrowing keeps the optional type alive into the constructor kwarg. Phase 60 line 840 shows the pattern: `opponent_score: float | None = 1.0 - ...`.

**Coding guidelines:**
- No magic numbers — reuse `_MIN_OPPONENT_SAMPLE = 10` (`app/services/endgame_service.py:233`). Do NOT introduce a new threshold constant.
- Nesting depth soft ≤ 3 / hard ≤ 4. The wiring lives inside an existing `for endgame_class in wdl:` loop at depth 1; the new arithmetic adds depth 2 at most.
- Logic LOC: the new block is small enough (~15-20 lines) to inline. Don't extract a helper unless ty forces it.

**Sentry:**
- Per CLAUDE.md, the mirror-identity arithmetic is pure (subtraction + division, guarded by the existing sample-size gate). No new `capture_exception` sites required.

**Backend conventions:**
- FastAPI 0.115.x + Pydantic v2 + SQLAlchemy 2.x async + asyncpg. Python 3.13.
- Pydantic v2 model: `ConversionRecoveryStats` extends inline (existing class). New fields are required (no defaults), consistent with sibling fields.

## Summary

DATA-02 splits cleanly into two deliverables. **Section 2 is an audit-only confirmation:** every field the Phase 86 cards consume (Conv / Parity / Recov peer bullets + the derived Skill peer baseline) is already exposed on `MaterialRow` via `opponent_score` + `opponent_games`. Phase 60 shipped this. The audit's job is to document the file:line evidence in SUMMARY.md and explain how Phase 86 computes `Opp Skill` from `MaterialRow[conversion].opponent_score` + `MaterialRow[recovery].opponent_score` without a new payload field. **Section 3 needs a small backend extension:** `ConversionRecoveryStats` does not currently carry opponent fields, so four new fields (`opponent_conversion_pct`, `opponent_conversion_games`, `opponent_recovery_pct`, `opponent_recovery_games`) are appended to the schema and populated in `_aggregate_endgame_stats` via the same same-game symmetry identity Phase 60 introduced for Section 2, scoped per `EndgameClass`.

The mirror identities are arithmetic, not statistical: within one class X, the user's recovery games are by definition the opponent's conversion games (each user-recovery game = the opponent entered with eval advantage). So `opp_conv[X]` = opponent's win rate when opponent had eval advantage = user's loss rate when user had eval deficit in X = `(recovery_games − recovery_wins − recovery_draws) / recovery_games`. Symmetrically, `opp_recov[X]` = opponent's save rate (wins + draws) when opponent had eval deficit = user's losses + draws when user had eval advantage in X = `(conversion_losses + conversion_draws) / conversion_games`. The asymmetry between Conv (win-rate) and Recov (save-rate) means the two formulas are NOT copy-paste symmetric — that is the single most likely place to break this.

All numerators and denominators are already in the accumulator at line 339-355. No new DB query, no new accumulator key, no new threshold constant. The whole change is ~20 lines of wiring + 4 schema fields + 5 tests.

**Primary recommendation:** Single plan, 3 task groups: (1) extend `ConversionRecoveryStats` with 4 fields + docstring, (2) wire the mirror identity into `_aggregate_endgame_stats` between lines 355 and 357 using `_MIN_OPPONENT_SAMPLE` for gating on the mirror bucket's `_games`, (3) add 5 unit tests (symmetric mirror, below-threshold-None, at-threshold-10, zero-sample safety, schema shape). Audit copy collapses into the plan's SUMMARY.md.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| New schema fields on `ConversionRecoveryStats` | Pydantic schema (`app/schemas/endgames.py`) | — | API wire shape definition; no service or DB logic. |
| Mirror-identity arithmetic (`opp_conv`, `opp_recov`) | Service layer (`app/services/endgame_service.py:_aggregate_endgame_stats`) | — | Pure arithmetic over the existing accumulator; same tier that already builds `ConversionRecoveryStats`. |
| Threshold gating (`_MIN_OPPONENT_SAMPLE` reuse) | Service layer (constant at `endgame_service.py:233`) | — | Shared with Section 2's `_compute_score_gap_material`; single source of truth. |
| Unit tests for mirror identity | Test layer (`tests/test_endgame_service.py`) | — | Mirrors `TestScoreGapMaterialOpponentBaseline` template, scoped to `TestAggregateEndgameStats`. |
| Section 2 audit prose | Documentation (plan's SUMMARY.md) | — | Cross-references existing Phase 60 wiring; zero code change. |

No frontend tier in scope. Phase 84 is backend-only. Phase 87 will consume `EndgameCategoryStats.conversion.opponent_*` from the frontend, but that wiring lands in Phase 87.

## Standard Stack

This is a contained backend extension on an established stack — nothing new to install.

### Core (already in repo, reused)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Pydantic | v2 (≥ 2.x) | Response model definition (`ConversionRecoveryStats`) | Project-wide validation layer; CLAUDE.md mandates Pydantic v2 throughout. [VERIFIED: existing schemas use it] |
| Python | 3.13 | Type-annotated dataclasses + `Literal` types | Project baseline. [VERIFIED: CLAUDE.md tech stack] |
| pytest | (project pinned) | Unit tests via existing `tests/test_endgame_service.py` | Already the testing layer. [VERIFIED: `uv run pytest` in CLAUDE.md commands] |
| ty | (project pinned) | Type checker, gates CI | CLAUDE.md mandates zero-error compliance. [VERIFIED: CLAUDE.md] |
| ruff | (project pinned) | Lint + format | CLAUDE.md mandates. [VERIFIED: CLAUDE.md] |

### Supporting (no additions)

No new libraries. The work is schema extension + arithmetic + tests using existing infrastructure.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Schema fields on `ConversionRecoveryStats` | Compute opp rates client-side from existing WDL fields | Locked by D-08: ship schema fields for consistency with `MaterialRow` and to avoid FE math drift between Section 2 and Section 3. The cost is small (~20 LOC backend) and the contract is more legible. |
| Reuse `_MIN_OPPONENT_SAMPLE = 10` | Introduce `PER_CLASS_OPPONENT_SAMPLE_MIN` | Locked by D-05: parallel constants drift. Single threshold is correct. |
| Mirror identity in service | Compute in router or repository | Locked by service-layer convention (CLAUDE.md "Backend Layout"). Repositories do DB access only; routers do HTTP only. Mirror identity is business logic. |

**No installation required.** All existing dependencies.

## Architecture Patterns

### System Architecture Diagram

```
                     +-------------------+
DB rows ────────────▶│ _aggregate_       │── EndgameCategoryStats list
(game_id, class_int, │  endgame_stats    │    .conversion: ConversionRecoveryStats
 result, color,      │                   │       .conversion_pct (existing)
 eval_cp, eval_mate) │ accumulator:      │       .conversion_games (existing)
                     │   wdl[class]      │       .conversion_wins (existing)
                     │   conv[class]     │       .conversion_draws (existing)
                     │   recov[class]    │       .conversion_losses (existing)
                     │                   │       .recovery_pct (existing)
                     │ per class:        │       .recovery_games (existing)
                     │   compute existing│       .recovery_saves (existing)
                     │   conv/recov pcts │       .recovery_wins (existing)
                     │                   │       .recovery_draws (existing)
                     │   NEW: mirror     │       .opponent_conversion_pct (NEW)
                     │     identity:     │       .opponent_conversion_games (NEW)
                     │     opp_conv from │       .opponent_recovery_pct (NEW)
                     │       recov_*     │       .opponent_recovery_games (NEW)
                     │     opp_recov from│
                     │       conv_*      │── flows through:
                     │                   │   EndgameStatsResponse.categories
                     │   gate on         │   EndgameOverviewResponse.stats.categories
                     │   _MIN_OPPONENT_  │     /api/endgames/stats
                     │     SAMPLE (10)   │     /api/endgames/overview
                     +-------------------+

Existing Section 2 path (unchanged, audit-only confirmation):
DB rows ──▶ _compute_score_gap_material (endgame_service.py:824-855)
              ─ swap-bucket mirror ─▶ MaterialRow.opponent_score / opponent_games
              ─▶ ScoreGapMaterialResponse.material_rows
              ─▶ EndgameOverviewResponse.score_gap_material
              ─▶ EndgameScoreGapSection.tsx opponentRate() / MIRROR_BUCKET
```

### Recommended Project Structure

No new files. Edit in place:

```
app/
├── schemas/
│   └── endgames.py            # extend ConversionRecoveryStats (lines 19-42)
├── services/
│   └── endgame_service.py     # wire mirror identity in _aggregate_endgame_stats (between lines 355-357)
tests/
└── test_endgame_service.py    # new test class for per-type mirror identity
```

### Pattern 1: Same-game mirror-bucket symmetry (Phase 60 template)

**What:** Within one scope (one `EndgameClass` for Section 3; one `MaterialBucket` for Section 2), the opponent's outcome is the user's outcome flipped: opp_wins = user_losses, opp_draws = user_draws, opp_losses = user_wins. Cross-bucket: user's "conversion" games (user entered with eval ≥ +1.0) are by definition the opponent's "recovery" games (opponent entered with eval ≤ −1.0).

**When to use:** Computing opponent baselines without a separate DB query or benchmark — pure arithmetic identity from same-game data already in the accumulator.

**Existing Section 2 template** (`app/services/endgame_service.py:824-855`):
```python
# Source: app/services/endgame_service.py:824-855 (Phase 60 in-repo template)
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
    material_rows.append(MaterialRow(
        # ...
        opponent_score=opponent_score,
        opponent_games=swap_games,
    ))
```

### Pattern 2: Per-type mirror identity (Section 3 — this phase)

**What:** Scoped to a single `EndgameClass`. Conv is a win-rate (numerator = wins only), Recov is a save-rate (numerator = wins + draws). The mirror formulas must reflect that asymmetry. Reference: D-04 in CONTEXT.

**Code shape** (target wiring at `endgame_service.py:355-357`, between `recovery_pct = ...` and the `ConversionRecoveryStats(...)` constructor):

```python
# Source: derived from Phase 60 template (endgame_service.py:824-855), scoped per EndgameClass.
# Conv = win-rate, Recov = save-rate (wins+draws). The two mirror formulas are NOT symmetric.
# opp_conv[X] = user_recov_losses[X] / user_recovery_games[X]
#             = (recovery_games - recovery_wins - recovery_draws) / recovery_games
# opp_recov[X] = (user_conv_losses[X] + user_conv_draws[X]) / user_conversion_games[X]

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

Then pass through to the constructor:
```python
conversion_stats = ConversionRecoveryStats(
    conversion_pct=conversion_pct,
    # ... existing kwargs ...
    recovery_draws=recovery_draws,
    opponent_conversion_pct=opponent_conversion_pct,
    opponent_conversion_games=opponent_conversion_games,
    opponent_recovery_pct=opponent_recovery_pct,
    opponent_recovery_games=opponent_recovery_games,
)
```

### Pattern 3: `_pct = float | None`, `_games = int` (Phase 60 convention)

The `_pct` field is gated on the **mirror** sample size and is `None` below threshold. The `_games` companion field is always `int` — it reports the mirror bucket's actual count, possibly `0`. Never emit `None` for `_games`. This matches `MaterialRow.opponent_score: float | None` + `MaterialRow.opponent_games: int`.

### Anti-Patterns to Avoid

- **Gating on the own bucket size, not the mirror bucket size.** `opponent_conversion_pct` gates on `recovery_games >= 10`, NOT on `conversion_games >= 10`. The "sample size" for the opponent baseline is the mirror bucket's count because that's where the opponent's analogous games actually came from.
- **Copy-pasting the conversion formula into recovery.** Conv uses `(games − wins − draws) / games` (= losses / games, a win-rate from the loser's perspective). Recov uses `(losses + draws) / games` (= save-rate from the loser's perspective). Different numerators.
- **Introducing a `PER_CLASS_OPPONENT_SAMPLE_MIN` constant.** Reuse `_MIN_OPPONENT_SAMPLE = 10`.
- **Switching to 0.0-1.0 scale mid-method.** Stay on `round(x, 1)` with 0.0-100.0 percent style to match `conversion_pct` / `recovery_pct`. The `MaterialRow.opponent_score` is 0.0-1.0 because that schema uses score-style values — this schema uses percent-style. Don't cross the streams.
- **Adding a new DB query or accumulator key.** Every numerator and denominator is already in the existing `conv[endgame_class]` and `recov[endgame_class]` accumulators (`endgame_service.py:264-271`).
- **Treating `_games` as `int | None`.** Schema is `int`. A zero-sample mirror bucket emits `0`, not `None`.
- **Per-EndgameClass class-mapped dict for the mirror.** Section 2 uses `swap: dict[MaterialBucket, MaterialBucket]` because there are three buckets. Section 3's mirror is conceptually `conv ↔ recov` within one class — no per-class lookup is needed; the identity is local to the loop iteration over `endgame_class`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Opponent baseline computation | Separate aggregation query joining games to itself by opponent_id | Same-game symmetry identity (the user's losses ARE the opponent's wins for that game) | Phase 60 established this. Pure arithmetic, no extra query, exact. |
| Threshold constant for the new fields | `PER_CLASS_OPPONENT_SAMPLE_MIN = 10` | `_MIN_OPPONENT_SAMPLE = 10` (`endgame_service.py:233`) | D-05 LOCKED. Parallel constants drift over time. |
| Percentage scaling helper | New `_pct_round` helper | Inline `round(x, 1)` matching lines 346 + 354 | Two more call sites don't justify abstraction. |
| Mirror-bucket map for per-type | Dict literal scoping conv→recov / recov→conv per class | Inline arithmetic in the loop body | There are exactly two mirror identities, and they're written out in plain math. A dict would be over-engineering. |
| Pydantic field validator for the new fields | `@field_validator` ensuring `_pct ∈ [0, 100]` | Trust the computation | Existing `conversion_pct` / `recovery_pct` have no validators; consistency wins. The math is bounded by construction. |

**Key insight:** This phase is a 4-field schema extension + ~20 LOC of arithmetic with a complete in-repo template at `endgame_service.py:824-855`. Resist any urge to add abstraction. The whole change should diff cleanly.

## Common Pitfalls

### Pitfall 1: Conv-Recov formula asymmetry

**What goes wrong:** Engineer writes `opp_recov = (recovery_games - recovery_wins - recovery_draws) / recovery_games` (copy-pasted from `opp_conv`) and ships the mirror formula symmetrically. The tests pass for symmetric-WDL inputs but produce wrong values on real data.
**Why it happens:** Both fields look like "opponent rate," so mental shortcut treats them as symmetric. They are NOT: Conv is a win-rate (only wins in numerator), Recov is a save-rate (wins + draws in numerator). The mirror swaps "opponent's outcome" for "user's outcome flipped," but the *definition of rate* differs between the two cards.
**How to avoid:** Write the two formulas with their numerators spelled out:
  - `opp_conv_pct = (recovery_games − recovery_wins − recovery_draws) / recovery_games` *(opponent's wins from a recovery game = user's losses)*
  - `opp_recov_pct = (conversion_losses + conversion_draws) / conversion_games` *(opponent's wins + draws from a conversion game = user's losses + draws)*
**Warning signs:** Test for symmetric 50/50 inputs both pass but a 60/40 asymmetric case has `opp_recov_pct` matching `opp_conv_pct` numerically when they shouldn't.

### Pitfall 2: Gating on the wrong sample

**What goes wrong:** Engineer gates `opponent_conversion_pct` on `conversion_games >= _MIN_OPPONENT_SAMPLE` instead of `recovery_games >= _MIN_OPPONENT_SAMPLE`.
**Why it happens:** The field is called `opponent_conversion`, so it feels like the conversion-games sample size should gate it. But the data backing `opp_conv` came from the user's recovery games (same-game symmetry, cross-bucket), so the relevant sample is the mirror bucket.
**How to avoid:** Restate the gating rule out loud: "`opponent_conversion_pct` is `None` when the **mirror** bucket (recovery) has fewer than 10 games."
**Warning signs:** Test where `conversion_games = 100` and `recovery_games = 5` expects `opponent_conversion_pct is None` but the code returns a computed value (the engineer gated on the wrong side).

### Pitfall 3: `_games: int | None` drift

**What goes wrong:** Engineer types `opponent_conversion_games: int | None` to mirror `opponent_conversion_pct: float | None`, then emits `None` for the zero-sample case.
**Why it happens:** Visual parity feels right ("both are `_*` companions, both can be missing"). But `MaterialRow.opponent_games: int` is the locked convention (Phase 60).
**How to avoid:** Type strictly `int`. Emit `recovery_games` (or `conversion_games`) directly — possibly `0`, never `None`.
**Warning signs:** ty check passes but a schema-shape test asserting `isinstance(stats.opponent_conversion_games, int)` fails when the mirror is empty.

### Pitfall 4: Percent vs score-style scale drift

**What goes wrong:** Engineer writes `opponent_conversion_pct = recovery_losses / recovery_games` (0.0-1.0 score-style) because `MaterialRow.opponent_score` is on 0.0-1.0 scale.
**Why it happens:** The closest in-repo template (`endgame_service.py:824-855`) emits a 0.0-1.0 `opponent_score`. But `ConversionRecoveryStats.conversion_pct` and `recovery_pct` are 0.0-100.0 with `round(x, 1)`.
**How to avoid:** Stay local — match the convention of the existing fields in the same schema. Use `round(x / games * 100, 1)`.
**Warning signs:** Test expecting `opponent_conversion_pct = 60.0` for a 60% mirror gets `0.6`.

### Pitfall 5: Adding a parallel threshold constant

**What goes wrong:** Engineer creates `PER_CLASS_OPPONENT_SAMPLE_MIN = 10` in `endgame_service.py` and uses it for the new fields, leaving `_MIN_OPPONENT_SAMPLE` for Section 2.
**Why it happens:** "Per-class is different from per-bucket, so it deserves its own constant" reasoning.
**How to avoid:** D-05 LOCKED — reuse `_MIN_OPPONENT_SAMPLE`. Single source of truth.
**Warning signs:** Code review surfaces two `= 10` constants in the same file. Drift risk on the next threshold tweak.

### Pitfall 6: DivByZero on empty class

**What goes wrong:** Class X exists in `wdl` but has zero `conversion_games` or zero `recovery_games`; the new arithmetic divides by zero.
**Why it happens:** A class can accumulate `wdl` entries from any bucket (conv / parity / recov), so a class might have `parity_games = 100` but `conversion_games = 0`.
**How to avoid:** The existing pattern at lines 346 and 354 already guards with `if conversion_games > 0 else 0.0` and `if recovery_games > 0 else 0.0`. The new gating uses `>= _MIN_OPPONENT_SAMPLE (= 10)`, which is strictly tighter than `> 0`. So when the gate fails the `_pct` field is `None` and no division happens. **The gating IS the guard.** No separate `if > 0` needed. Confirm in the test for `conversion_games = 0` that `opponent_recovery_pct is None` (and `opponent_recovery_games == 0`).
**Warning signs:** `ZeroDivisionError` raised in the new code path on a sparse class. If this happens, the gate was bypassed.

### Pitfall 7: ty narrowing on `float | None` locals

**What goes wrong:** ty errors like `Possibly unbound: opponent_conversion_pct` when assigning conditionally without annotation.
**Why it happens:** Python's flow analysis treats `if ...: x = ... ; else: x = None` as flow-narrowed but ty wants an explicit annotation on the local for `float | None` to be preserved through the constructor call.
**How to avoid:** Annotate the local on first reference: `opponent_conversion_pct: float | None`. Matches the existing Phase 60 pattern at line 840: `opponent_score: float | None = 1.0 - ...`.
**Warning signs:** `uv run ty check app/` reports an unbound or type-mismatch on the new locals. Fix with the annotation pattern from line 840.

## Runtime State Inventory

Not applicable — this phase is a contained schema extension + arithmetic addition. No rename, refactor, or string replacement. No stored data, no live service config, no OS-registered state, no secrets/env vars, no build artifacts to invalidate.

## Code Examples

### Schema extension target (`app/schemas/endgames.py:19-42`)

```python
# Source: app/schemas/endgames.py:19-42 (current shape; new fields appended after recovery_draws)
class ConversionRecoveryStats(BaseModel):
    """Inline conversion/recovery stats for one endgame category (D-06, D-08, D-09).

    [existing docstring lines 20-30 retained]

    Phase 84: opponent baselines via same-game mirror identity, scoped per
    endgame class. opponent_conversion = opponent's win rate when opponent
    entered with eval advantage (derived from user_recovery_*); opponent_recovery
    = opponent's save rate when opponent entered with eval deficit (derived from
    user_conversion_*). Gated on _MIN_OPPONENT_SAMPLE (mirror bucket size).
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

    # Phase 84: opponent baseline via same-game mirror identity (D-03, D-04).
    opponent_conversion_pct: float | None  # None when recovery_games < _MIN_OPPONENT_SAMPLE
    opponent_conversion_games: int  # == recovery_games (mirror sample size, possibly 0)
    opponent_recovery_pct: float | None  # None when conversion_games < _MIN_OPPONENT_SAMPLE
    opponent_recovery_games: int  # == conversion_games (mirror sample size, possibly 0)
```

### Service wiring target (`app/services/endgame_service.py:355-368`)

```python
# Source: app/services/endgame_service.py:355-368 (current shape with new block inserted)
# After existing line 354: recovery_pct = round(recovery_saves / recovery_games * 100, 1) if ...

# Phase 84: opponent baselines via same-game mirror identity, scoped per
# EndgameClass (D-04). Conv = win-rate, Recov = save-rate — formulas are
# asymmetric. Gating reuses _MIN_OPPONENT_SAMPLE on the mirror bucket size
# (Phase 60 pattern, endgame_service.py:824-855).
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
    opponent_conversion_pct=opponent_conversion_pct,
    opponent_conversion_games=opponent_conversion_games,
    opponent_recovery_pct=opponent_recovery_pct,
    opponent_recovery_games=opponent_recovery_games,
)
```

### Test template (mirror Section 2's `TestScoreGapMaterialOpponentBaseline`)

```python
# Source: derived from tests/test_endgame_service.py:1405-1474 (Section 2 template)
# scoped to TestAggregateEndgameStats (per-type version)

def test_per_type_opponent_baseline_symmetric_60_40(self):
    """User Conv 60% over 10 games + User Recov save-rate 40% over 10 games in rook:
    opponent_conversion_pct == 60.0 (= 6/10 user-recov losses)
    opponent_recovery_pct == 40.0 (= 4/10 user-conv [losses + draws])
    """
    # rook conversion: 10 games, 6 wins, 0 draws, 4 losses (60% win-rate)
    conv_rows = [(i, 1, "1-0", "white", 150, None) for i in range(6)] + [
        (i + 6, 1, "0-1", "white", 150, None) for i in range(4)
    ]
    # rook recovery: 10 games, 2 wins, 2 draws, 6 losses (40% save-rate)
    rec_rows = [(i + 10, 1, "1-0", "white", -150, None) for i in range(2)] + [
        (i + 12, 1, "1/2-1/2", "white", -150, None) for i in range(2)
    ] + [(i + 14, 1, "0-1", "white", -150, None) for i in range(6)]
    result = _aggregate_endgame_stats(conv_rows + rec_rows)
    rook = next(c for c in result if c.endgame_class == "rook")
    # opp_conv from user_recov: 6 user losses / 10 recov games = 60%
    assert rook.conversion.opponent_conversion_pct == pytest.approx(60.0, abs=0.05)
    assert rook.conversion.opponent_conversion_games == 10
    # opp_recov from user_conv: (4 losses + 0 draws) / 10 conv games = 40%
    assert rook.conversion.opponent_recovery_pct == pytest.approx(40.0, abs=0.05)
    assert rook.conversion.opponent_recovery_games == 10
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Cohort/p50 opponent baseline (population median) | Mirror-bucket same-game symmetry (per rating × TC, rating-tier-conditioned by construction) | Phase 60 (Section 2); 2026-05-12 single-bullet doctrine pivot extended to all Conv/Parity/Recov/Skill cards | Removes rating-tier confound. Filter-responsive. No new benchmark precomputation. |
| Material-imbalance + 4-ply persistence proxy | Stockfish eval at endgame-entry ply (eval_cp / eval_mate) | REFAC-02 (Phases 78/79) | 100% eval coverage substrate for `ConversionRecoveryStats`. |
| Per-bucket only (Section 2) | Per-bucket + per-type (Section 2 + Section 3) | Phase 84 (this phase) | Per-type cards in Phase 87 read directly from the schema instead of re-deriving from user WDL. |

**Deprecated / outdated:**
- **DATA-01 per-type cohort p50 codegen** — dropped 2026-05-12. Do NOT reintroduce `p50` to `PerClassBands` or `PER_CLASS_GAUGE_ZONES`.
- **Material-imbalance bucket label / 4-ply persistence proxy** — `MaterialBucket` is kept as a wire-compat name for `bucket` field on `MaterialRow`, but the underlying classification is eval-based (REFAC-02). Don't write new code that re-derives material imbalance.

## Assumptions Log

This research has no `[ASSUMED]` claims requiring user confirmation. All factual claims are tagged `[VERIFIED: file:line]` against the in-repo code, or `[CITED: CONTEXT.md D-XX]` against the locked decisions in CONTEXT.md.

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| — | (none) | — | — |

**Table is empty:** All claims in this research were verified against the codebase (`app/schemas/endgames.py`, `app/services/endgame_service.py`, `tests/test_endgame_service.py`, `frontend/src/components/charts/EndgameScoreGapSection.tsx`) or cited from CONTEXT.md / single-bullet doctrine note / REQUIREMENTS.md / ROADMAP.md.

## Open Questions

1. **Test class placement seam (Claude's discretion per CONTEXT).**
   - What we know: Two viable seams — append to `TestAggregateEndgameStats` (bare-tuple convention, line 184-205) or add a sibling `TestPerTypeOpponentBaseline` near `TestScoreGapMaterialOpponentBaseline` (line 1381, `_FakeRow` convention).
   - What's unclear: which seam best matches reviewers' mental map.
   - Recommendation: Append to `TestAggregateEndgameStats` (or add a new sub-class within it). Rationale: the function under test is `_aggregate_endgame_stats`, not `_compute_score_gap_material`; co-locating tests with the function reduces grep distance. The `_FakeRow` helper at line 1381 is scoped to `TestScoreGapMaterial`'s setup and not reusable across functions.

2. **Single plan vs split (Claude's discretion).**
   - What we know: Audit copy collapses to a short SUMMARY.md section (file:line citations + a paragraph on `Opp Skill` derivation). Schema + service + tests is ~50 LOC of diff.
   - What's unclear: whether a planner reading this would prefer the audit as its own commit.
   - Recommendation: Single plan. The audit is short (~15 lines in SUMMARY.md) and reads naturally alongside the schema commit because the schema extension is what the audit motivates ("Section 2 already exposes everything; Section 3 needs the four new fields, here they are").

## Environment Availability

Not applicable — no external tools, services, or runtimes beyond the existing project stack (Python 3.13, uv, pytest, ty, ruff, PostgreSQL via existing Docker compose). No new package installs.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (project-pinned in `pyproject.toml`) |
| Config file | `pyproject.toml` (pytest section) |
| Quick run command | `uv run pytest tests/test_endgame_service.py -k opponent -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DATA-02 | Symmetric mirror-identity: user conv 60% + user recov save-rate 40% in class X → opp_conv == 60%, opp_recov == 40% | unit | `uv run pytest tests/test_endgame_service.py -k test_per_type_opponent_baseline_symmetric -x` | Test file exists; new test method to add. |
| DATA-02 | Below-threshold (mirror has 9 games) → `_pct` is `None`, `_games == 9` | unit | `uv run pytest tests/test_endgame_service.py -k test_per_type_opponent_baseline_below_threshold -x` | Test file exists; new test method to add. |
| DATA-02 | At-threshold (mirror has exactly 10 games) → `_pct` computed (non-None), `_games == 10` | unit | `uv run pytest tests/test_endgame_service.py -k test_per_type_opponent_baseline_at_threshold -x` | Test file exists; new test method to add. |
| DATA-02 | Zero-sample safety (mirror has 0 games) → `_pct is None`, `_games == 0`, no `ZeroDivisionError` | unit | `uv run pytest tests/test_endgame_service.py -k test_per_type_opponent_baseline_zero_sample -x` | Test file exists; new test method to add. |
| DATA-02 | Schema shape: `ConversionRecoveryStats` has the 4 new fields with correct types (`float \| None`, `int`, `float \| None`, `int`) | unit | `uv run pytest tests/test_endgame_service.py -k test_per_type_opponent_baseline_schema_shape -x` | Test file exists; new test method to add. |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_endgame_service.py -k opponent -x` (covers both Section 2 Phase 60 mirror tests AND the new Section 3 per-type mirror tests; under ~3 seconds)
- **Per wave merge:** `uv run pytest tests/test_endgame_service.py`
- **Phase gate:** `uv run pytest` + `uv run ty check app/ tests/` + `uv run ruff check .` all green before `/gsd-verify-work`

### Wave 0 Gaps

None — existing test infrastructure covers all phase requirements. `tests/test_endgame_service.py` exists with `TestAggregateEndgameStats` (line 181) and `TestScoreGapMaterialOpponentBaseline` (line 1381) both providing direct templates. Bare-tuple row helpers and `_FakeRow` helper both exist. pytest framework configured. No new fixtures needed.

## Security Domain

Phase 84 is a backend-internal schema extension + arithmetic addition. No new endpoint, no new request shape, no new authentication surface, no new input validation, no new persistence, no new external HTTP call, no new secrets. The four new fields are derived from existing accumulator data already gated through `/api/endgames/overview`'s existing auth + user-scoping (the same scoping `EndgameStatsResponse.categories` already enjoys). No security surface change.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | unchanged (existing FastAPI-Users auth on `/api/endgames/overview`) |
| V3 Session Management | no | unchanged |
| V4 Access Control | no | unchanged (existing user_id-scoped queries in `_aggregate_endgame_stats` callers) |
| V5 Input Validation | no | no new input; Pydantic v2 schema validates the output shape on serialization |
| V6 Cryptography | no | n/a |

### Known Threat Patterns

None introduced. The mirror-identity arithmetic is pure (subtraction + division, gated by sample-size threshold). No SQL, no eval, no shell, no network, no file I/O. Per CLAUDE.md Sentry rules, no new `capture_exception` sites required.

## Sources

### Primary (HIGH confidence — verified against in-repo code)

- `app/schemas/endgames.py:1-15` — `EndgameClass` Literal definition + module docstring. [VERIFIED]
- `app/schemas/endgames.py:19-42` — `ConversionRecoveryStats` current shape (target of extension). [VERIFIED]
- `app/schemas/endgames.py:45-61` — `EndgameCategoryStats` carrying `ConversionRecoveryStats` inline. [VERIFIED]
- `app/schemas/endgames.py:215-237` — `MaterialRow` with `opponent_score: float | None` + `opponent_games: int` (the pattern template). [VERIFIED]
- `app/schemas/endgames.py:279-305` — `ScoreGapMaterialResponse.material_rows` (Section 2 wire shape). [VERIFIED]
- `app/schemas/endgames.py:475-491` — `EndgameOverviewResponse` (the `/api/endgames/overview` composed response). [VERIFIED]
- `app/services/endgame_service.py:230-237` — `_MIN_OPPONENT_SAMPLE = 10` constant + rationale comment. [VERIFIED]
- `app/services/endgame_service.py:240-392` — `_aggregate_endgame_stats` (target wiring function). [VERIFIED]
- `app/services/endgame_service.py:341-368` — current per-class numerator/denominator computation + `ConversionRecoveryStats(...)` constructor call (insertion site lines 355-357). [VERIFIED]
- `app/services/endgame_service.py:824-855` — Phase 60 Section 2 mirror-bucket implementation (the direct template). [VERIFIED]
- `frontend/src/components/charts/EndgameScoreGapSection.tsx:111-145` — `MIRROR_BUCKET` map + `opponentRate()` frontend helper (consumer pattern Phase 86/87 will follow). [VERIFIED]
- `tests/test_endgame_service.py:180-205` — `TestAggregateEndgameStats` bare-tuple row convention. [VERIFIED]
- `tests/test_endgame_service.py:1381-1474` — `TestScoreGapMaterialOpponentBaseline` (per-type test template; symmetric / below-threshold / at-threshold patterns). [VERIFIED]
- `.planning/milestones/v1.17-phases/84-data-plumbing-per-type-cohort-p50-and-mirror-rate-audit/84-CONTEXT.md` — D-01 through D-11 (locked decisions). [CITED]
- `.planning/notes/v1.17-single-bullet-doctrine.md` — pivot rationale + cascading impacts on Phases 84-88. [CITED]
- `.planning/REQUIREMENTS.md:53` — DATA-02 wording. [CITED]
- `.planning/milestones/v1.17-ROADMAP.md` — Phase 84 success criterion. [CITED]
- `CLAUDE.md` — backend conventions, type-safety rules, Sentry rules, coding guidelines. [CITED]

### Secondary (MEDIUM confidence)

None needed. The phase is fully in-repo verified.

### Tertiary (LOW confidence)

None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; existing Pydantic v2 + pytest stack verified in `pyproject.toml` and `CLAUDE.md`.
- Architecture: HIGH — direct in-repo template at `endgame_service.py:824-855` (Phase 60); wiring site fully specified by D-06.
- Pitfalls: HIGH — pitfalls derived from real arithmetic asymmetries (Conv vs Recov numerators) and Phase 60 conventions, plus explicit guidance from CONTEXT.md D-04, D-05, D-07.

**Research date:** 2026-05-12
**Valid until:** 2026-06-11 (30 days — small contained change, low churn risk; in-repo template is stable)

## RESEARCH COMPLETE

**Phase:** 84 - Data plumbing — mirror-rate audit
**Confidence:** HIGH

### Key Findings

- **Section 2 is already wired** — no backend work. `MaterialRow.opponent_score` (`float | None`) + `opponent_games` (`int`) on each of the three buckets (conv/parity/recov) ship on `/api/endgames/overview` via `ScoreGapMaterialResponse.material_rows` (Phase 60). Frontend already consumes via `EndgameScoreGapSection.tsx:111-145`. Skill peer baseline `Opp Skill` derives client-side in Phase 86 from `MaterialRow[conversion].opponent_score` + `MaterialRow[recovery].opponent_score` — no new payload field.
- **Section 3 needs a small extension** — `ConversionRecoveryStats` does NOT currently carry opponent fields. Four new fields (`opponent_conversion_pct`, `opponent_conversion_games`, `opponent_recovery_pct`, `opponent_recovery_games`) appended after `recovery_draws`. Wired in `_aggregate_endgame_stats` between lines 355-357 via the same-game mirror identity.
- **Mirror formulas are asymmetric** — Conv is a win-rate (`opp_conv = recovery_losses / recovery_games`), Recov is a save-rate (`opp_recov = (conversion_losses + conversion_draws) / conversion_games`). Different numerators. Most likely pitfall is copy-paste symmetry.
- **Gating is on the mirror bucket** — `opponent_conversion_pct` gates on `recovery_games >= _MIN_OPPONENT_SAMPLE`, NOT on `conversion_games`. Reuse `_MIN_OPPONENT_SAMPLE = 10` from line 233 — do NOT introduce a parallel constant.
- **`_games` is always `int`** — schema convention from Phase 60. Emit `recovery_games` / `conversion_games` directly (possibly `0`), never `None`. The `_pct` field is `float | None`; the `_games` companion is `int`.

### File Created

`/home/aimfeld/Projects/Python/flawchess/.planning/milestones/v1.17-phases/84-data-plumbing-per-type-cohort-p50-and-mirror-rate-audit/84-RESEARCH.md`

### Confidence Assessment

| Area | Level | Reason |
|------|-------|--------|
| Standard Stack | HIGH | No new dependencies; reuses existing Pydantic v2 + pytest. |
| Architecture | HIGH | Direct in-repo template at `endgame_service.py:824-855`; wiring site fully specified by D-06. |
| Pitfalls | HIGH | Derived from real arithmetic asymmetries + Phase 60 conventions, with explicit guidance from CONTEXT.md D-04, D-05, D-07. |

### Open Questions

- Test class placement seam (recommendation: append to `TestAggregateEndgameStats`, bare-tuple convention).
- Single plan vs split (recommendation: single plan — audit copy is short enough to live inline in SUMMARY.md).

### Ready for Planning

Research complete. Planner can now create PLAN.md files. Default expected shape: 1 plan, 3 task groups (schema extension, service wiring, tests), audit collapsed into SUMMARY.md.
