# Phase 84: Data plumbing — per-type cohort p50 + mirror-rate audit - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-12
**Phase:** 84-data-plumbing-per-type-cohort-p50-and-mirror-rate-audit
**Areas discussed:** p50 shape, p50 source, Section 3 mirror, Phase scope

---

## p50 shape

| Option | Description | Selected |
|--------|-------------|----------|
| Extend PerClassBands with p50 | Add `p50: tuple[float, float]` (conv_p50, recov_p50) to the existing PerClassBands dataclass. Single source of truth per class — IQR + p50 colocated. Codegen emits `PER_CLASS_GAUGE_ZONES[<cls>].p50` alongside conversion/recovery bands. | ✓ |
| Separate PER_CLASS_P50 map | Leave PerClassBands as (p25, p75) only; add a new `PER_CLASS_P50: Mapping[EndgameClass, {conversion: float, recovery: float}]` beside it. Cleaner separation; minor risk of the two maps drifting. | |
| Use IQR midpoint, no codegen change | Compute p50 as (lower + upper) / 2 in the frontend. Zero backend work but inaccurate — benchmark-2026-05-12 §6 shows real p50s drift from IQR midpoint (e.g. queen conv pooled 0.774 vs midpoint 0.78; pawnless conv 0.79 vs midpoint 0.75). | |

**User's choice:** Extend PerClassBands with p50.
**Notes:** Emit p50 on TS side as a nested object (`{ conversion: <num>, recovery: <num> }`) rather than a tuple — easier to type-narrow downstream.

---

## p50 source

| Option | Description | Selected |
|--------|-------------|----------|
| Pooled means from benchmarks-2026-05-12 §6 | Already computed: rook 0.710 / 0.296, minor_piece 0.695 / 0.328, pawn 0.738 / 0.275, queen 0.774 / 0.234, mixed 0.694 / 0.311, pawnless 0.791 / 0.198 (conv / recov). Reuses the same dump that drives the live IQR bands. Note: §6 says "pooled mean" not "pooled p50" — for skewed dists they differ. | ✓ |
| Re-run /benchmarks for true per-class p50 | The current report exposes pooled means; per-user p50 (the per-user median, then pooled) is the more honest centre tick. Extend the benchmark skill output to emit per-class per-user p50 before locking the values. Adds ~half day. | |
| Lock midpoint of live (p25, p75) | Mathematically `0.5 * (p25 + p75)` per class — works as a tick but isn't grounded in observed data. Only viable if option 3 is chosen for shape (no real-data anchor). | |

**User's choice:** Pooled means from benchmarks-2026-05-12 §6.
**Notes:** Claude flagged that §6 reports pooled means, but the §5 per-user p50 marginals confirm mean ≈ p50 within 0.01 for these distributions. After 2dp rounding the values agree. No-op editorially.

---

## Section 3 mirror

| Option | Description | Selected |
|--------|-------------|----------|
| Extend ConversionRecoveryStats with opponent fields | Add `opponent_conversion_pct` / `opponent_conversion_games` / `opponent_recovery_pct` / `opponent_recovery_games` to ConversionRecoveryStats (the inline section on EndgameCategoryStats). Mirror-by-class symmetry: opp_conv on type X = 1 − myRecov on type X. Backend extension required; SEC3 peer bullets ship in Phase 87. | ✓ |
| Audit-only, defer mirror data to Phase 87 | Confirm in writing that per-type opponent data isn't on the schema today; punt the actual backend extension into Phase 87 (where it gets consumed). Phase 84 keeps its tight "data-plumbing prerequisite" framing; Phase 87 gets one more plan. | |
| Drop SEC3 peer bullets entirely; only cohort bullets in Section 3 | Section 3 already has a mobile-density fallback in the v1.17 spec (SEC3-05). Pre-commit to dropping per-type peer bullets and avoid the backend extension. Loses the per-type opponent signal but simplifies the phase substantially. | |

**User's choice:** Extend ConversionRecoveryStats with opponent fields.
**Notes:** Claude flagged in CONTEXT.md D-08 that the four new fields are derivable client-side from the existing per-type WDL fields (`conversion_wins/draws/losses/games`, `recovery_wins/draws/saves/games`). Section 2 already double-implements (`MaterialRow.opponent_score` AND `opponentRate()` recompute from WDL). User locked the schema extension for consistency with the Section 2 pattern. Plan-phase may revisit if implementation cost is non-trivial.

---

## Phase scope

| Option | Description | Selected |
|--------|-------------|----------|
| Keep Phase 84 standalone | Ship DATA-01 (codegen extension) + DATA-02 (per-type opponent backend extension) + written audit as Phase 84. Phase 85+ inherits a clean schema. Roadmap-as-planned. | ✓ |
| Collapse into Phase 85/86 plan-phase | Per the v1.17 roadmap's own flag: "Phase may collapse into Phase 85/86 plan-phase if DATA-02 is confirmed already-present and DATA-01 is a one-plan codegen extension." If DATA-02 turns out to be a small backend extension and DATA-01 is one plan, fold them into Phase 85/86. Updates ROADMAP.md and REQUIREMENTS.md traceability. | |

**User's choice:** Keep Phase 84 standalone.
**Notes:** Standalone is preferred even though DATA-02 turned out to be small. Reason: keeps a clean schema-change commit boundary so Phase 87 traces directly back to one phase.

---

## Claude's Discretion

- Rounding of p50 values to 2 dp or 4 dp — planner picks and stays consistent with the IQR band emitter.
- Whether to add a parallel `PER_CLASS_OPPONENT_SAMPLE_MIN` constant — probably reuse `_MIN_OPPONENT_SAMPLE` from `endgame_service.py`.
- Test placement (`test_endgame_zones.py` vs `test_endgame_service.py` split).
- Audit deliverable format — Claude proposed inline in `84-01-SUMMARY.md`, no separate `.planning/notes/` file.

## Deferred Ideas

- **Pawnless band shifts** flagged in `reports/benchmarks-2026-05-12.md` §6 Recommendations (conv 0.70→0.74 lower, 0.80→0.84 upper; recov 0.21→0.15 lower, 0.31→0.25 upper). Sparse n=1,365; not load-bearing for v1.17. Defer to a future zones-calibration pass.
- **Cell-specific (rating × TC) per-class baselines** (FUT-04 in REQUIREMENTS.md) — out of scope for v1.17.
- **Per-class `PER_CLASS_OPPONENT_SAMPLE_MIN`** — only if Phase 87 hits sparse-n problems.
- **Per-class Endgame Skill metric** — already out of scope per REQUIREMENTS.md.
