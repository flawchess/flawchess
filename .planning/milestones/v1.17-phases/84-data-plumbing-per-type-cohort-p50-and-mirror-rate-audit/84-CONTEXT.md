# Phase 84: Data plumbing — mirror-rate audit - Context

**Gathered:** 2026-05-12
**Status:** Ready for planning
**Pivot note:** Regenerated 2026-05-12 after single-bullet doctrine pivot. The original CONTEXT covered DATA-01 (per-type cohort p50 codegen) + DATA-02 (mirror-rate audit + Section 3 extension). DATA-01 is dropped entirely. Only DATA-02 remains. See `.planning/notes/v1.17-single-bullet-doctrine.md`.

<domain>
## Phase Boundary

Single requirement: **DATA-02 — mirror-bucket peer-rate audit + Section 3 schema extension.** Phase 84 ships:

1. **Section 2 audit (already-present).** Confirm in writing that `/api/endgames/overview` already exposes the components Phase 86 needs for the Conv / Parity / Recov / Skill peer bullets:
   - `MaterialRow.opponent_score` + `MaterialRow.opponent_games` on each of the three buckets (`conversion` / `parity` / `recovery`) — Section 2's Conv / Parity / Recov peer bullets.
   - Skill card's derived `Opp Skill` is computed frontend-side in Phase 86 from `MaterialRow[conversion].opponent_score` (= `opp_conv`) + `MaterialRow[recovery].opponent_score` (= `opp_recov`), so no new payload field is required for it.
   No backend work expected here — the audit deliverable is prose with file:line citations.

2. **Section 3 extension (new fields).** Add four mirror-bucket fields to `ConversionRecoveryStats` (`app/schemas/endgames.py:19-42`):
   - `opponent_conversion_pct: float | None`
   - `opponent_conversion_games: int`
   - `opponent_recovery_pct: float | None`
   - `opponent_recovery_games: int`

   Populate them in `_aggregate_endgame_stats()` (`app/services/endgame_service.py:240-392`) using the same same-game symmetry identity Phase 60 introduced for Section 2, scoped to one `EndgameClass`. The per-type cards in Phase 87 will read these directly instead of recomputing from user WDL fields client-side.

Frontend changes are out of scope. No new statistical methods. No benchmark refresh. No DB schema change. No new DB queries — all per-type fields the mirror identity needs are already in the accumulator.

</domain>

<decisions>
## Implementation Decisions

### DATA-02 Section 2 audit (LOCKED)

- **D-01:** **Section 2 is already wired.** `MaterialRow.opponent_score: float | None` + `MaterialRow.opponent_games: int` were added in Phase 60 (`app/services/endgame_service.py:824-855`), wired into `/api/endgames/overview` via `ScoreGapMaterialResponse.material_rows` (`app/schemas/endgames.py:215-237, 285-303`), and consumed by `EndgameScoreGapSection.tsx:111-145` (`opponentRate()` + `MIRROR_BUCKET`). The Skill peer baseline `Opp Skill` is derivable from the existing `MaterialRow[conversion].opponent_score` + `MaterialRow[recovery].opponent_score` — no new payload field needed. **No backend work for Section 2.**

- **D-02:** **Audit deliverable is inline in the phase summary**, not a separate `.planning/notes/` file. The summary records: which fields are already present, where they live in the codebase (file:line), how Phase 86 derives `Opp Skill` from existing components, and what gating threshold applies. Cross-references Phase 60 as the originating phase.

### DATA-02 Section 3 schema extension (LOCKED)

- **D-03:** Add four fields **at the end** of `ConversionRecoveryStats` in `app/schemas/endgames.py:19-42`, matching the `MaterialRow` pattern (`float | None` for the `_pct`, plain `int` for the `_games`):
  - `opponent_conversion_pct: float | None`
  - `opponent_conversion_games: int`
  - `opponent_recovery_pct: float | None`
  - `opponent_recovery_games: int`

  Field ordering: append after `recovery_draws`. No defaults (all existing fields are required; new fields stay required). Update the model docstring to mention the new fields and reference Phase 84.

- **D-04:** **Mirror identities** (same-game symmetry, scoped to one `EndgameClass = X`):
  - `opp_conv_pct[X] = (user_recovery_games[X] − user_recovery_wins[X] − user_recovery_draws[X]) / user_recovery_games[X]`
    *(opponent's conversion = opponent's win-rate when opponent entered with eval advantage = user's loss-rate when user entered with eval deficit in class X)*
  - `opp_recov_pct[X] = (user_conversion_losses[X] + user_conversion_draws[X]) / user_conversion_games[X]`
    *(opponent's recovery = opponent's draw+win-rate when opponent entered with eval deficit = user's loss+draw-rate when user entered with eval advantage in class X)*

  Note the asymmetry: Conversion is a *win-rate* (wins only in numerator), Recovery is a *save-rate* (wins + draws in numerator). The mirror formulas are NOT a copy-paste of each other.

- **D-05:** **Threshold gating** reuses `_MIN_OPPONENT_SAMPLE = 10` from `app/services/endgame_service.py:233` (the same constant Section 2 uses on `MaterialRow.opponent_score`). Do not introduce a parallel `PER_CLASS_OPPONENT_SAMPLE_MIN`. Gate the `_pct` field on the **mirror** sample size, not the field's own bucket size:
  - `opponent_conversion_pct` is `None` when `recovery_games < 10` (else computed).
  - `opponent_recovery_pct` is `None` when `conversion_games < 10` (else computed).
  - `_games` companion fields are always `int` (== mirror sample size, possibly `0`), never `None`.

- **D-06:** **Wiring site:** between line 355 (after `recovery_pct = ...`) and line 357 (`conversion_stats = ConversionRecoveryStats(...)`) in `_aggregate_endgame_stats()`. The accumulator already has every numerator/denominator the mirror identity needs (`conversion_games`, `conversion_wins`, `conversion_draws`, `conversion_losses`, `recovery_games`, `recovery_wins`, `recovery_draws`). No new DB query. No new accumulator key.

- **D-07:** **Percentage convention:** `round(x, 1)` to match the existing `conversion_pct` / `recovery_pct` style at lines 346, 354 (0.0-100.0 scale with one decimal). Do NOT switch to a 0.0-1.0 scale mid-file. The `MaterialRow.opponent_score` is 0.0-1.0 because that schema uses score-style values; this schema uses percent-style. The two existing fields set the local convention.

- **D-08 (flagged trade-off, resolved → ship the schema fields):** The four new fields are *derivable client-side* from the existing per-type WDL fields. Section 2 itself uses both: `MaterialRow.opponent_score` is on the schema AND `EndgameScoreGapSection.opponentRate()` re-derives from WDL as a sanity check. The user locked the schema extension at discuss-phase for consistency with `MaterialRow` (one wire shape across Section 2 + Section 3, single backend identity, no FE math drift risk in Phase 87). Flag this in plan-phase so the planner can re-surface if implementation cost balloons; otherwise ship the schema fields as locked.

### DATA-02 Sig-test pattern (NOT in this phase)

- **D-09:** The Wald-z sig-test pattern for the Section 3 peer bullets is **Phase 87 scope**, not this phase. Phase 84 locks only the data shape. Phase 87 will use Wald-z on the signed difference `myRate − oppRate` gated on `MIN_OPPONENT_BASELINE_GAMES`, mirroring `EndgameScoreGapSection.tsx`'s Section 2 pattern.

### Phase scope and plan count (LOCKED)

- **D-10:** **Phase 84 stays standalone** (not folded into Phase 86 or 87). Rationale: keeping the schema change as its own phase preserves a clean reference for Phase 87 (one schema change traces to one phase commit). Roadmap explicitly offered the collapse option; user rejected.

- **D-11:** **Plan count: 1 plan (was 3 pre-pivot).** Post-pivot scope is small enough to live in a single plan:
  - Section 3 schema extension on `ConversionRecoveryStats` (4 fields).
  - Service wiring in `_aggregate_endgame_stats` (mirror identity per class).
  - Unit tests in `tests/test_endgame_service.py` (mirror identity, threshold boundary, zero-sample safety).
  - Audit deliverable inline in the plan SUMMARY.md (Section 2 already-wired cross-refs, Section 3 new fields documented, `Opp Skill` derivation note for Phase 86).

  Planner may split into 2 plans (one for schema/service/tests, one for audit) if it judges the audit is heavy enough to warrant its own commit — but a single plan is the expected default given the audit collapses to a paragraph or two.

### Claude's Discretion

- **Test placement.** Append a new test class (e.g. `TestPerTypeOpponentBaseline`) inside `tests/test_endgame_service.py`'s existing `TestAggregateEndgameStats`, OR add a sibling class alongside `TestScoreGapMaterialOpponentBaseline` — planner picks the seam that matches existing structure best.
- **Row-construction helper choice.** Existing aggregate tests use bare tuples (`tests/test_endgame_service.py:184-205`); Section 2 mirror tests use a `_FakeRow` helper (`:1381-1404`). Planner picks whichever fits the chosen test class location — do not invent a new helper if either existing convention suffices.
- **Single-plan vs split.** If the audit copy is non-trivial (more than ~30 lines), planner may split into 2 plans.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### v1.17 spec & roadmap
- `.planning/milestones/v1.17-ROADMAP.md` — Phase 84 success criterion (mirror-rate audit only)
- `.planning/REQUIREMENTS.md` — DATA-02 wording (lines 53-55); v1 count = 27 post-pivot
- `.planning/notes/v1.17-single-bullet-doctrine.md` — pivot rationale; explains why DATA-01 was dropped and what cascading changes hit Phases 84-88

### Section 2 audit references (already-wired)
- `app/schemas/endgames.py:215-237` — `MaterialRow` with `opponent_score: float | None` + `opponent_games: int` (the pattern Section 3 mirrors)
- `app/schemas/endgames.py:285-303` — `ScoreGapMaterialResponse.material_rows` (composed into overview response)
- `app/schemas/endgames.py:475-491` — `EndgameOverviewResponse` (the `/api/endgames/overview` wire shape)
- `app/services/endgame_service.py:824-855` — Phase 60 mirror-bucket computation (`swap_bucket` + `_MIN_OPPONENT_SAMPLE` gate + `opponent_score = 1.0 - bucket_score[swap_bucket]`)
- `frontend/src/components/charts/EndgameScoreGapSection.tsx:111-145` — `MIRROR_BUCKET` map + `opponentRate()` frontend helper; the pattern Phase 86 + 87 follow

### Section 3 extension targets (new fields land here)
- `app/schemas/endgames.py:19-42` — `ConversionRecoveryStats` (extend with the 4 opponent fields at end)
- `app/schemas/endgames.py:45-61` — `EndgameCategoryStats` (carries `ConversionRecoveryStats`; no change here)
- `app/services/endgame_service.py:233` — `_MIN_OPPONENT_SAMPLE = 10` constant (reuse)
- `app/services/endgame_service.py:240-392` — `_aggregate_endgame_stats()` (mirror identity wiring at lines 355-357)
- `app/services/endgame_service.py:357-368` — current `ConversionRecoveryStats(...)` constructor call (extend kwargs)

### Test references
- `tests/test_endgame_service.py:184-205` — bare-tuple row-construction convention used by `TestAggregateEndgameStats`
- `tests/test_endgame_service.py:1381-1474` — `TestScoreGapMaterialOpponentBaseline` Section 2 mirror-identity tests (template for the per-type version)
- `tests/test_endgame_service.py:1405-1432` — symmetric 60/40 mirror test (`test_opponent_baseline_symmetric_60_40`)
- `tests/test_endgame_service.py:1446-1474` — below/at-threshold boundary tests

### Prior phase context (mirror infrastructure history)
- `.planning/milestones/v1.10-phases/60-*/60-CONTEXT.md` — Phase 60 introduced mirror-bucket opponent baseline + `MIN_OPPONENT_BASELINE_GAMES`
- `.planning/milestones/v1.15-phases/78-*` / `79-*` — eval-based endgame classification (REFAC-02), the substrate `ConversionRecoveryStats` sits on top of

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`_MIN_OPPONENT_SAMPLE = 10`** (`app/services/endgame_service.py:233`) — single threshold constant for opponent-baseline gating across Section 2 + Section 3.
- **`_aggregate_endgame_stats`** (`app/services/endgame_service.py:240-392`) — already computes every numerator/denominator the mirror identity needs. No new DB query, no new accumulator key.
- **`MaterialRow.opponent_score` + `opponent_games` pattern** (`app/schemas/endgames.py:215-237`) — direct template for the four new `ConversionRecoveryStats` fields. Same `float | None` + `int` shape.
- **`TestScoreGapMaterialOpponentBaseline` test pattern** (`tests/test_endgame_service.py:1381-1474`) — direct template for per-type mirror-identity tests (symmetric 60/40, below-threshold, at-threshold).

### Established Patterns
- **Same-game mirror-bucket symmetry** (Phase 60): opp_wins(in user's bucket X) = user_losses(in user's bucket X); cross-bucket: user "conversion" games are by definition opponent "recovery" games. Scoping to one `EndgameClass` keeps the identity exact.
- **`_pct` = `float | None`, `_games` = `int`** (Phase 60 convention): `_pct` is gated on the mirror sample size (`None` below threshold); `_games` always emits the int sample size (possibly 0, never `None`).
- **Pydantic v2 schema field ordering**: `ConversionRecoveryStats` and `MaterialRow` both lack defaults; appending new required fields is safe as long as all constructor call sites pass them.
- **`EndgameClass` Literal typing** (CLAUDE.md type-safety rule): all dict keys and field types stay `EndgameClass = Literal[...]`. The new mirror identities operate per `EndgameClass`; do not collapse to bare `str`.
- **`round(x, 1)` percent convention** (lines 346, 354): one decimal on 0.0-100.0 scale; do not switch to 0.0-1.0 score-style mid-method.

### Integration Points
- `EndgameOverviewResponse.stats.categories[*].conversion.*` — where the four new per-type opponent fields surface on the wire (Phase 87 consumer).
- `EndgameStatsResponse.categories[*].conversion.*` — same path on the secondary `/api/endgames/stats` endpoint; the schema extension automatically covers both endpoints.
- `_compute_score_gap_material` (`endgame_service.py:824-855`) — untouched; Section 2 path stays as-is.

### Sentry
- No new exceptional paths. The mirror-identity arithmetic is pure (subtraction + division, both guarded by the existing `if sample >= threshold` gate). Do not add new `capture_exception` sites in this phase.

</code_context>

<specifics>
## Specific Ideas

- **Field order in the schema:** keep the four new fields contiguous and append them after `recovery_draws` (don't interleave with `conversion_*` / `recovery_*` groups).
- **Naming:** `opponent_conversion_*` and `opponent_recovery_*` (not `opp_conv_*` shorthand) to stay consistent with `MaterialRow.opponent_score` / `opponent_games` and to avoid mixing shorthand and verbose names on the wire.
- **Comment in `_aggregate_endgame_stats`:** one short comment block citing Phase 60 + the mirror identity, like the existing Phase 60 comment at `endgame_service.py:824-829`. Code comment only — no docstring inflation.
- **Single-plan default:** the audit copy collapses to a SUMMARY.md section, not a separate plan, unless the planner judges otherwise.

</specifics>

<deferred>
## Deferred Ideas

- **Per-class `_MIN_OPPONENT_SAMPLE_PER_CLASS`** — only worth doing if Phase 87 hits sparse-n problems at the per-type level. Reuse the global threshold.
- **Sig-test methodology on per-type peer bullets** — Phase 87 scope (Wald-z on signed difference, mirrors Section 2). Do not implement here.
- **Skill peer-bullet sig-test methodology** — Phase 86 scope (SEC2-08 open question — Wald-z directly on derived difference vs propagation from component CIs vs computation on raw outcomes).
- **Cell-specific (rating × TC) per-class baselines** (`FUT-04` in REQUIREMENTS.md) — out of scope for v1.17.
- **Per-class Endgame Skill metric** — global composite only; out of scope per REQUIREMENTS.md.
- **DATA-01 per-type cohort p50 codegen** — DROPPED 2026-05-12 (single-bullet doctrine pivot). Do NOT reintroduce `p50` to `PerClassBands` or `PER_CLASS_GAUGE_ZONES`.

</deferred>

---

*Phase: 84-data-plumbing-per-type-cohort-p50-and-mirror-rate-audit (directory name retains pre-pivot scope; can be renamed at phase close)*
*Context regenerated: 2026-05-12 (post-pivot)*
