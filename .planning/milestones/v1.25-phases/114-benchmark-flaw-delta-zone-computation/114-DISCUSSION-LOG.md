# Phase 114: Benchmark Flaw-Delta Zone Computation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-10
**Phase:** 114-benchmark-flaw-delta-zone-computation
**Areas discussed:** Estimator / denominator policy, Combo-zone scope + thin samples, Per-user inclusion threshold, Zone delivery format

---

## Estimator / denominator policy

The user opened by challenging the entire count-rate vs proportion split from SEED-040,
arguing all metrics are differences of proportions with different denominators. The
discussion ran several rounds; the selection options below are the convergence points.

**Round 1 — per-user estimator shape**

| Option | Description | Selected |
|--------|-------------|----------|
| Game OR opportunity as unit | Dense families per-game-averaged rate (pairing kept); sparse families pooled proportion | |
| Unify all to pooled proportion | Single pooled estimator; drops within-game pairing | |
| Let me reframe it | — | ✓ (user reframed) |

**Round 2 — sparse-metric estimator**

| Option | Description | Selected |
|--------|-------------|----------|
| Pooled proportion (conversion) | Sparse = pooled your_prop−opp_prop; game-unit becomes a 115 CI choice | |
| Move-rate, game-unit everywhere | Switch sparse to per-100-moves; one estimator; loses conversion semantics | |
| Note cluster-bootstrap for 115 | — | (user reframed again) ✓ |

**Round 3 — denominator policy**

| Option | Description | Selected |
|--------|-------------|----------|
| Per-100-moves for all 13 | Full unification | |
| Keep opportunity denoms for the 4 | SEED-040 as written | |
| Hybrid: opp denom only squandered/lucky | Compromise | |

(User asked Claude to reassess its own recommendation rather than pick.)

**Round 4 — final lock**

| Option | Description | Selected |
|--------|-------------|----------|
| Lock unification, next area | All 13 = paired per-game (your_tag−opp_tag)/your_moves×100; amends SEED-040, voids FLAWCMP-02 | ✓ |
| Lock, but revisit squandered later | Plan-time exposure-confound check for squandered/lucky | |
| Keep discussing the estimator | — | |

**User's choice:** Unify all 13 metrics to the per-100-of-your-moves paired per-game delta.
**Notes:** Claude initially recommended keeping the two-group split, then reversed under the
user's reasoning. The deciding arguments: (1) opportunity-denominator exposure-conditioning is
only partial in a you−opp paired design (asymmetric cancellation); (2) ELO-matched pairing
makes the confound second-order, which simultaneously makes per-100-moves adequate and the
opportunity denominator unnecessary; (3) the split's cost (two estimators, sparse 0/0, thinner
IQR zones, recalibration tax, mixed units, Wilson) outweighs the second-order purity; (4)
impact-weighted per-100-moves better serves leak-finding. Residual `squandered`/`lucky`
exposure disclosed via a Phase 115 tooltip, not corrected. Amends SEED-040 + voids FLAWCMP-02.

---

## Combo-zone scope + thin samples

| Option | Description | Selected |
|--------|-------------|----------|
| Compute uniformly + viability diagnostic | 2 combos as 2 more metrics + per-metric viability columns for FLAWCMP-04 | ✓ |
| Compute, no special diagnostic | Combos computed, no viability columns | |
| Defer combos to zoneless | 11 metrics only; combos ship zoneless in v1 | |

**User's choice:** Compute uniformly + viability diagnostic.
**Notes:** Unification made combos trivial (two more uniform metrics). The viability diagnostic
gives Phase 115 the data to satisfy FLAWCMP-04 without re-deriving combo viability.

**Thin-cell handling**

| Option | Description | Selected |
|--------|-------------|----------|
| Suppress cell, fall back to marginal | Cell zone emitted only above contributor floor; else null → 115 uses marginal/global zone | ✓ |
| Emit anyway + coverage flag | Always emit, tagged degenerate | |
| Decide floor + fallback at plan time | Lock principle, planner sets exact floor | |

**User's choice:** Suppress thin cells; fall back to the marginal/global zone the collapse
verdict already produces.
**Notes:** Reuses existing benchmark sparse-cell methodology; no degenerate narrow band ships.

---

## Per-user inclusion threshold

| Option | Description | Selected |
|--------|-------------|----------|
| Uniform min-games floor, N at plan time | Single floor across all 13 metrics; N measured at plan time; keep ≥30-per-cell | ✓ |
| Align floor with 115 section gate | Per-user floor = FLAWCMP-05 live-user gate | |
| Include all analyzed users | Any user with ≥1 analyzed game; rely on ≥30-per-cell only | |

**User's choice:** Uniform min-analyzed-games floor; exact N at plan time.
**Notes:** Uniform floor matches the unified estimator (no per-tag opportunity counts to gate
on). Existing ≥30-contributing-users-per-cell floor kept on top.

---

## Zone delivery format

| Option | Description | Selected |
|--------|-------------|----------|
| Report-only → editorial constants in 115 | 114 emits report (raw Q1/Q3 + marginals + verdicts + viability); 115 hand-authors zones with editorial judgment | ✓ |
| Report + committed structured artifact | 114 commits a CI-drift-checked Python/JSON zone artifact 115 imports | |
| DB table (CDF pattern) | Benchmark DB table of zone bounds | |

**User's choice:** Report-only; Phase 115 hand-authors editorial constants (`endgame_zones.py`
pattern).
**Notes:** Honors the seed's lightweight mandate (no CDF infra) and the project's
editorial-judgment-over-IQR rule for zone bands. The gitignored generator JSON intermediate
keeps the raw numbers correct without a new committed artifact.

## Claude's Discretion

- Chapter placement/numbering in SKILL.md + report layout (new top-level chapter mirroring §3).
- `scripts/benchmarks/` module structure, SQL, and the per-game move-count denominator source
  (`game_flaws` lacks total moves → join `game_positions`).
- Exact viability-diagnostic columns.
- Whether to add a `test_chapter*_diff.py`-style gate for the new chapter (recommended).

## Deferred Ideas

None — discussion stayed within phase scope. Tactic-motif bullets (SEED-039) remain zoneless
out-of-scope; eval-coverage raising (SEED-012) stays an upstream concern.
