# Phase 84: Data plumbing — per-type cohort p50 + mirror-rate audit - Context

**Gathered:** 2026-05-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Two prerequisites for the v1.17 Section 2 (4-card metrics) and Section 3 (per-type breakdown cards) refactors:

1. **DATA-01 — Per-type cohort p50 codegen.** Extend `PER_CLASS_GAUGE_ZONES` in `app/services/endgame_zones.py` so each `EndgameClass × {conversion, recovery}` carries an explicit `p50` centre tick alongside the existing `(p25, p75)` typical band. Regenerate `frontend/src/generated/endgameZones.ts` via `scripts/gen_endgame_zones_ts.py`. The CI drift guard on the codegen continues to pass.
2. **DATA-02 — Mirror-bucket peer-rate audit + per-type extension.** Confirm in writing that Section 2's `MaterialRow` already exposes `opponent_score` + `opponent_games` on `/api/endgames/overview` (Phase 60). Section 3's per-type `EndgameCategoryStats.conversion` (`ConversionRecoveryStats`) does NOT carry opponent fields today; extend it to expose `opponent_conversion_pct` / `opponent_conversion_games` / `opponent_recovery_pct` / `opponent_recovery_games` so Section 3's peer bullets in Phase 87 read from a uniform schema (matching Section 2's `MaterialRow` pattern).

Frontend changes are out of scope — Phase 84 ships only the codegen extension, the per-type schema fields, the audit doc, and unit tests. Section 2 and Section 3 UI cards land in Phases 86 / 87.

</domain>

<decisions>
## Implementation Decisions

### DATA-01: Per-type p50 codegen shape (LOCKED)

- **D-01:** Extend the existing `PerClassBands` dataclass in `app/services/endgame_zones.py:320-326` with a `p50: tuple[float, float]` field, ordered `(conversion_p50, recovery_p50)` to mirror the existing `conversion` / `recovery` IQR tuples. Single source of truth per class — IQR and centre tick stay colocated. Rejected: a separate `PER_CLASS_P50` mapping (risk of drift between the two maps). Rejected: midpoint-of-IQR computation on the frontend (inaccurate — pooled per-class p50 is offset from IQR midpoint on at least pawn / queen / pawnless; see `reports/benchmarks-2026-05-12.md` §6).

- **D-02:** Update `scripts/gen_endgame_zones_ts.py:67-78` so `_format_per_class_gauge_zones()` emits a third key per class: `{ conversion: [lo, hi], recovery: [lo, hi], p50: { conversion: <num>, recovery: <num> } }`. Emit `p50` as a nested object (not a tuple) because the frontend consumer reads it as `PER_CLASS_GAUGE_ZONES[<class>].p50.conversion` — easier to type-narrow than a positional tuple. Re-run the codegen as part of the plan; CI drift guard catches accidental hand edits.

- **D-03:** p50 values are sourced from **`reports/benchmarks-2026-05-12.md` §6 "Pooled-by-class summary (excl sparse cell)"**, the `conv` / `recov` columns. Lock the published pooled values verbatim (no editorial tightening — `feedback_zone_band_judgement.md` governs IQR colour bands, not centre ticks). Initial values:

  | class | p50.conversion | p50.recovery |
  |---|---:|---:|
  | rook | 0.7098 | 0.2963 |
  | minor_piece | 0.6949 | 0.3278 |
  | pawn | 0.7379 | 0.2754 |
  | queen | 0.7744 | 0.2343 |
  | mixed | 0.6940 | 0.3111 |
  | pawnless | 0.7913 | 0.1976 |

  Plan-phase may round to 2dp (matches the IQR band granularity, e.g. `(0.65, 0.75)`). Rounding decision deferred to the plan; round half-even is fine.

- **D-04:** Note on terminology: `benchmarks-2026-05-12.md` §6 reports **pooled means**, not per-user p50 medians. For these per-class distributions they diverge by ≤0.01 (the per-user p50 columns in §5 confirm: e.g. conv p50 = 0.719 pooled vs mean 0.711). The 2dp-rounded values agree either way. Comment in `endgame_zones.py` should say "pooled per-class typical centre, source: §6 mean (≈ per-user p50)" so future readers know which statistic was canonicalised.

- **D-05:** No drift recommendations from `benchmarks-2026-05-12.md` are applied in this phase (pawnless conversion ~0.79 vs live `(0.70, 0.80)`; pawnless recovery ~0.20 vs live `(0.21, 0.31)`). Both are flagged in §6 "Recommendations" with sparse sample warnings — defer the band shift to a separate calibration phase. Phase 84 keeps the live IQR bands unchanged; only adds `p50`.

### DATA-02: Mirror-bucket peer-rate audit + per-type extension (LOCKED with a flag)

- **D-06:** **Section 2 audit (already-present):** Document in the plan that `MaterialRow.opponent_score: float | None` and `MaterialRow.opponent_games: int` were added in Phase 60 (`app/services/endgame_service.py:840-854`), wired into `/api/endgames/overview` via `ScoreGapMaterialResponse.material_rows`, and consumed by `EndgameScoreGapSection.tsx:141-144` (`opponentRate()` function). No backend work needed for Section 2.

- **D-07:** **Section 3 extension (new fields):** Add four fields to `ConversionRecoveryStats` (`app/schemas/endgames.py:19-42`):
  - `opponent_conversion_pct: float | None` — opponent's conv rate in the same class (= user's loss rate in user's recovery bucket of that class)
  - `opponent_conversion_games: int` — opponent's conv sample size (= user's recovery_games)
  - `opponent_recovery_pct: float | None` — opponent's recov rate in the same class (= user's loss+draw rate in user's conversion bucket of that class)
  - `opponent_recovery_games: int` — opponent's recov sample size (= user's conversion_games)

  Mirror identities (same-game symmetry, scoped to one `EndgameClass`):
  - `opp_conv_pct[X] = (user_recovery_games − user_recovery_wins − user_recovery_draws) / user_recovery_games`
  - `opp_recov_pct[X] = (user_conversion_losses + user_conversion_draws) / user_conversion_games`

  Set to `None` when the user's mirror-bucket sample is below `_MIN_OPPONENT_SAMPLE` (the same threshold Section 2 uses on `MaterialRow.opponent_score`). Wire up in `app/services/endgame_service.py` wherever `EndgameCategoryStats` / `ConversionRecoveryStats` are constructed.

- **D-08 (flag for plan-phase):** All four fields are **derivable client-side** from the existing per-type fields (`conversion_games` / `conversion_wins` / `conversion_draws` / `conversion_losses` and `recovery_games` / `recovery_wins` / `recovery_draws` / `recovery_saves`). Section 2 itself uses both: `MaterialRow.opponent_score` is on the schema AND `EndgameScoreGapSection.opponentRate()` recomputes from WDL. Plan-phase must explicitly confirm the schema extension is worth shipping (consistency with `MaterialRow` pattern) vs. computing client-side only (no backend churn). User locked the schema extension; flag this so the planner can re-surface the trade-off if implementation cost is non-trivial.

- **D-09:** Sig-test pattern for the per-type peer bullets (Phase 87 consumer): Wald-z vs 0 on the difference `myRate − oppRate`, gated on `MIN_OPPONENT_BASELINE_GAMES` per type. Same pattern as Section 2's peer bullets in `EndgameScoreGapSection.tsx`. Not implemented in Phase 84 — only the data shape is locked here.

- **D-10:** Audit deliverable is inline in `84-01-SUMMARY.md` (the data-plumbing plan's summary). No separate `.planning/notes/` audit file — keeps the phase artefact-light. The summary records: Section 2 already wired (cite Phase 60 + line numbers), Section 3 fields added (list new schema fields), mirror identities documented.

### Phase Scope (LOCKED)

- **D-11:** Phase 84 stays standalone (3 plans expected): (1) `endgame_zones.py` p50 extension + codegen + drift-guard re-run, (2) `ConversionRecoveryStats` schema extension + service wiring + unit tests, (3) audit + cross-link in `84-SUMMARY.md`. Roadmap explicitly flagged a collapse-into-85/86 option — rejected. Reason: even if DATA-01 is one plan and DATA-02 is one small backend plan, keeping them as a separate phase preserves a clean reference for the Phase 87 consumer (one schema change traces to one phase commit). User confirmed.

### Claude's Discretion

- Rounding of p50 values to 2 dp or 4 dp — planner picks one and stays consistent with the IQR band emitter.
- Whether to add a parallel `PER_CLASS_OPPONENT_SAMPLE_MIN` constant (probably reuse `_MIN_OPPONENT_SAMPLE` from `endgame_service.py`).
- Test placement: `tests/services/test_endgame_zones.py` for p50 field presence; `tests/services/test_endgame_service.py` for per-type opponent field population — planner decides exact file split.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### v1.17 spec & roadmap
- `.planning/milestones/v1.17-ROADMAP.md` — full milestone roadmap, Phase 84 success criteria
- `.planning/REQUIREMENTS.md` — DATA-01 and DATA-02 wording (Phase 84 requirements)
- `.planning/notes/endgame-stats-card-redesign.md` — source design notes for v1.17

### Benchmark data (p50 source)
- `reports/benchmarks-2026-05-12.md` §6 "Pooled-by-class summary (excl sparse cell)" — pooled means per `EndgameClass` × `{conversion, recovery}`; values to lock into `PER_CLASS_GAUGE_ZONES.p50`
- `reports/benchmarks-2026-05-12.md` §5.4–§5.7 — per-user p50 marginals confirming mean ≈ p50 within 0.01 for these distributions

### Codegen + zone registry (DATA-01)
- `app/services/endgame_zones.py:320-339` — `PerClassBands` dataclass + `PER_CLASS_GAUGE_ZONES` map; codegen source of truth
- `app/services/endgame_zones.py:390-420` — `per_class_zone_spec()` / `assign_per_class_zone()` consumers
- `scripts/gen_endgame_zones_ts.py:67-78` — `_format_per_class_gauge_zones()` codegen function to extend
- `frontend/src/generated/endgameZones.ts:65-72` — current `PER_CLASS_GAUGE_ZONES` emitted output (do NOT hand-edit; regenerated)

### Mirror-bucket schema + service (DATA-02)
- `app/schemas/endgames.py:19-42` — `ConversionRecoveryStats` (extend with four opponent fields)
- `app/schemas/endgames.py:45-61` — `EndgameCategoryStats` (carries `ConversionRecoveryStats`)
- `app/schemas/endgames.py:215-237` — `MaterialRow` (the Section 2 pattern to mirror; already has `opponent_score` + `opponent_games`)
- `app/schemas/endgames.py:475-491` — `EndgameOverviewResponse` (the `/api/endgames/overview` composed response)
- `app/services/endgame_service.py:830-855` — Section 2 mirror-bucket computation (`swap_bucket` logic + `opponent_score` assignment), the pattern to mirror for per-type
- `frontend/src/components/charts/EndgameScoreGapSection.tsx:111-145` — Section 2's `MIRROR_BUCKET` + `opponentRate()` frontend mirror; pattern Phase 87 will follow per-type

### Prior phase context (mirror infrastructure history)
- `.planning/milestones/v1.10-phases/60-*/60-CONTEXT.md` — Phase 60 introduced mirror-bucket opponent baseline + `MIN_OPPONENT_BASELINE_GAMES`
- `.planning/milestones/v1.16-phases/83-stockfish-baseline-predicted-endgame-score/83-CONTEXT.md` — most recent zones codegen extension precedent (D-16 ENTRY_EXPECTED_SCORE codegen pattern)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`PerClassBands` dataclass** (`app/services/endgame_zones.py:320`) — extend with one new field rather than creating a parallel structure. Frozen dataclass; immutable instantiation pattern already in place.
- **`_format_per_class_gauge_zones()`** (`scripts/gen_endgame_zones_ts.py:67`) — single function emits the per-class TS literal; one-line extension to include a `p50` key.
- **`_MIN_OPPONENT_SAMPLE`** + `MaterialRow.opponent_score` assignment pattern (`app/services/endgame_service.py:836-854`) — direct template for the per-type extension. Same `None`-when-below-threshold semantics.
- **`opponentRate()` frontend helper** (`EndgameScoreGapSection.tsx:141`) — Phase 87 will need an analogous per-class helper; not built in this phase, but the API shape is locked here.

### Established Patterns
- **Python authoritative, TS codegen'd** (Phase 63 D-01): All zone constants are defined in `endgame_zones.py`; `scripts/gen_endgame_zones_ts.py` mirrors them. CI runs the codegen + `git diff --exit-code` to block drift. Hand-editing `endgameZones.ts` is prohibited.
- **Schema-level opponent fields are `T | None`** when sample is below threshold; companion `_games` field is always `int` (never None). Section 3 extension follows this exactly.
- **`endgame_class`-keyed dicts use `EndgameClass` Literal** for backend, `EndgameClassKey` for frontend. The `Mapping[EndgameClass, PerClassBands]` annotation stays correct; only the value type expands.
- **No bare strings for endgame class** (CLAUDE.md type-safety rule): all schema additions stay typed with `EndgameClass = Literal[...]`.

### Integration Points
- `EndgameOverviewResponse.stats.categories[*].conversion` — where the new per-type opponent fields surface on the wire
- `EndgameOverviewResponse.score_gap_material.material_rows[*].opponent_score` — already-present Section 2 path (untouched)
- `frontend/src/generated/endgameZones.ts` — sole consumer surface for the new `p50` field

</code_context>

<specifics>
## Specific Ideas

- p50 emit shape on TS side: `p50: { conversion: 0.71, recovery: 0.30 }` (nested object), not `p50: [0.71, 0.30]` (tuple). Easier downstream typing for the bullet centre-tick consumer.
- Avoid backfilling `_MIN_OPPONENT_SAMPLE` decisions during this phase — reuse whatever constant Section 2 currently honours and surface it in the per-type wiring without renaming.

</specifics>

<deferred>
## Deferred Ideas

- **Pawnless band shifts** flagged in `reports/benchmarks-2026-05-12.md` §6 Recommendations (conv `[0.70, 0.80] → [0.74, 0.84]`; recov `[0.21, 0.31] → [0.15, 0.25]`). Sparse sample (1,365 users); not load-bearing for v1.17 UI work. Defer to a future zones-calibration phase or fold into a `/benchmarks` follow-up.
- **Cell-specific (rating × TC) per-class baselines** (`FUT-04` in REQUIREMENTS.md) — out of scope for v1.17 milestone; do not touch the per-class zone shape beyond adding `p50`.
- **`PER_CLASS_OPPONENT_SAMPLE_MIN`** per-class threshold (separate from the global one) — only worth doing if Phase 87 hits sparse-n problems. Leave unimplemented; reuse the existing global threshold.
- **Per-class Skill metric** (mentioned out-of-scope in REQUIREMENTS.md "Out of Scope" table) — global composite only.

</deferred>

---

*Phase: 84-data-plumbing-per-type-cohort-p50-and-mirror-rate-audit*
*Context gathered: 2026-05-12*
