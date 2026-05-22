# Phase 93: Global Percentile Benchmark Artifact - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-22
**Phase:** 93-global-percentile-benchmark-artifact
**Areas discussed:** TS codegen integration

---

## Gray Areas Surfaced (4)

Claude presented 4 gray areas: artifact shape & metadata, per-user inclusion floor, TS codegen integration, report depth vs SKILL.md. User selected only **TS codegen integration** for discussion. The other 3 are deferred to Claude's discretion in CONTEXT.md (planner resolves in PLAN.md without needing user input).

---

## TS codegen integration

### Round 1 — Original framing (presumed locked from SEED-019)

| Option | Description | Selected |
|--------|-------------|----------|
| Sibling script + sibling .ts | New `scripts/gen_global_percentile_cdf_ts.py` emits `frontend/src/generated/globalPercentileCdf.ts`. Each generated TS file has one shape. | |
| Extend existing script + append to endgameZones.ts | Mixed concerns inside one TS file; one CI gate. | |
| Extend existing script + emit separate .ts file | Compromise: one script, two TS surfaces. | |

**User's response:** "I don't understand why the frontend needs the percentile tables at all. Can't we just produce the percentile in the backend and send it to the frontend as part of the API responses?"

**Claude's analysis:** User is correct. Walked through the actual Phase 94/95 consumers:
- PCTL-02: backend interpolates user value against `GLOBAL_PERCENTILE_CDF` → emits scalar `{metric}_percentile` in API response
- PCTL-03: frontend renders chip from that scalar
- PCTL-04: popover copy is metric-aware framing — no CDF numbers shown to user
- LLM-05: LLM payload uses the same scalar

No client-side CDF consumer exists in v1.19. The TS codegen mirror was pattern-matched against `endgame_zones.py`, which legitimately needs a TS mirror because gauge band painting happens client-side. The CDF is server-side-only.

### Round 2 — Refined question

| Option | Description | Selected |
|--------|-------------|----------|
| Drop the TS mirror entirely | Phase 93 ships Python-only. Update ROADMAP.md SC #2 and REQUIREMENTS.md PCTL-01 to drop the TS drift-guard clause. | ✓ |
| Keep the TS mirror — future-proof | Build the codegen pipeline pre-emptively. | |
| Keep but defer | Note as deferred idea, ship Python-only. | |

**User's choice:** Drop it entirely. Rationale: there is no current or planned frontend consumer; if a future client-side CDF viz ships (sparkline, what-if widget), the codegen mirror is added then. Don't pre-build infrastructure for hypothetical consumers.

**Persistence:**
- `.planning/ROADMAP.md` Phase 93 top bullet + Phase Details + Success Criterion #2 updated to drop the TS drift-guard clause and clarify the artifact is Python-only.
- `.planning/REQUIREMENTS.md` PCTL-01 updated to drop the TS drift-guard clause and clarify backend interpolates at request time.
- `.planning/seeds/SEED-019-global-percentile-annotations-on-endgame-metrics.md` annotated with a "Phase 93 discuss refinement (2026-05-22)" note so future readers understand the seed's TS codegen guidance is superseded.

---

## Claude's Discretion

Three of the four originally surfaced gray areas were not picked by the user and are left to the planner to resolve in PLAN.md without coming back to the user:

1. **Artifact shape & metadata** — exact dataclass design for `GLOBAL_PERCENTILE_CDF`, whether to carry `BENCHMARK_DB_SNAPSHOT_MONTH` + per-metric `n_users` for audit trail. Recommend yes (small cost, real benefit for future recalibrations). Follow the typed-Mapping pattern in `endgame_zones.py`.
2. **Per-user inclusion floor per metric** — keep the pre-flight's per-metric floors (≥30/30 for Endgame Score Gap, ≥20 for Achievable + Section 2 ΔES) or unify. Recommend keeping per-metric to preserve continuity with the pre-flight, but planner is free to argue for a unified floor with reasoning.
3. **Report depth vs SKILL.md** — slim (breakpoint tables + per-rating-bucket sanity check) vs rich (full pre-flight-style per-bucket distributions + skew/kurt + ELO collapse verdicts). Either is acceptable for SC #3; lean rich to match the pre-flight precedent.

## Deferred Ideas

- **TS codegen mirror of the CDF** — deferred until a client-side consumer materializes (sparkline of user's global position, "what value puts me in the top X%" widget, offline what-if calculator). Captured in CONTEXT.md `<deferred>`.
- **Tier-4 per-type CDFs** — already deferred in REQUIREMENTS.md §Future Requirements; sample-thin per-type slices. Revisit with a hard sample gate in a follow-on phase.
- **Opening insights percentile annotations** — out of scope for v1.19; candidate for a future Opening Insights v2 milestone.
