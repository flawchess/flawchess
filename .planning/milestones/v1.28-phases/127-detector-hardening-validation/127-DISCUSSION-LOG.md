# Phase 127: Detector Hardening & Validation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-19
**Phase:** 127-detector-hardening-validation
**Areas discussed:** Precision-fix strategy, Depth semantics & unit, Validation harness design, Re-backfill scope

---

## Precision-fix strategy

Opened by asking the governing philosophy (precision-first hard-drop vs balanced keep+decay). The user paused — leaning balanced but wanting to understand the tradeoff first. The discussion reframed the whole area away from the depth-bound/decay framing.

| Option | Description | Selected |
|--------|-------------|----------|
| Precision-first (hard depth-bound, drop deep hits) | Kills Case-B deep noise deterministically, but also kills real deep combinations (Case A), guts the depth-as-difficulty axis, and zeroes inherently-multi-ply tier-3 motifs | |
| Balanced (keep + confidence-decay-by-depth) | Keeps Case A and tier-3, tunable SQL knob — but decay is monotone in depth while wrongness is not, so it can't separate "deep real" from "deep noise"; only dims everything deep | |
| **Relevance-gate + earliest-depth dispatch (synthesis)** | Gate each detector to fire only on a real instance (fixes Case B at any depth + phantom-early hits); dispatch non-mates by min(depth) with priority as equal-depth tiebreak (adaptive, keeps Case A); depth stored for difficulty only | ✓ |

**User's choice:** The synthesis. Key user contribution: proposed "depth should come before priority" (earliest-firing motif is the cause of error; a hanging piece at ply 1 should win over a fork 5 plies later despite fork's higher priority). Agreed, refined to "depth first, priority as equal-depth tiebreak", with the relevance gate as required companion.

**Sub-decision — mates under the always-on depth filter:** The user flagged that a mate-in-3 is "deep" but must never be hidden from beginners by the filter. Resolved: depth ≈ difficulty holds for material tactics but breaks for mates; keep D-07 mate-dominance for the primary tag AND exempt mate tags from the depth filter. The "shallow material win then deeper mate" conflict is rare in practice, so keeping D-07 is cheap.

**Notes:** This area absorbed the original "depth semantics" area — the depth-return (SC#1) turned out to be the exact input depth-first dispatch needs, so the two are one task. Confidence-decay and hard depth-bound both dropped as precision mechanisms.

---

## Validation harness design

| Option | Description | Selected |
|--------|-------------|----------|
| **Committed stratified fixture** | One-time scripts/ selector → committed sample (stratified by motif-theme + Rating band); CI runs offline, deterministic, reproducible | ✓ (data source) |
| Runtime download in CI | Always current but slow, flaky, non-reproducible; numbers drift between unrelated builds | |
| On-demand script only (no CI) | Low maintenance but under-delivers SC#5 (wants CI numbers from the independent set) | |
| **Precision blocks, recall reports** | Per-motif precision floor is a hard CI gate; recall measured but non-blocking (low recall = acceptable conservative under-tagging) | ✓ (pass/fail policy) |
| Both precision and recall block | Strongest, but a recall gate fights the deliberate under-tagging philosophy; flaky | |
| Report-only, no gate | Lowest friction; weakens SC#5 to advisory | |
| **Tiered floor: core blocks, tier-3 gated-by-validation** | Core+geometric+mates high blocking bar; tier-3 ships only if it clears the floor else suppressed-until-validated | ✓ (floor shape) |
| Uniform floor for all motifs | Simpler to state, but tier-3 likely can't clear it → broad blocks or suppress-most-of-tier-3 anyway | |

**User's choice:** Committed stratified fixture + precision-blocks/recall-reports + tiered floor.
**Notes:** No AGPL cook.py (SC#4) reaffirmed — CC0 data only. Multi-label theme matching + explicit unvalidated-motif list noted as planner detail. Depth-vs-puzzle-Rating promoted to a first-class harness output because the Phase 129 filter is always-on.

---

## Re-backfill scope

| Option | Description | Selected |
|--------|-------------|----------|
| **Dev backfill in-phase, prod deferred to runbook** | 127 re-runs corrected detector over ~131k tagged games on dev (also real-data validation); prod deferred per Phase 125 D-01 precedent; new drains corrected automatically | ✓ |
| Ship code + harness only, all backfill deferred | Smallest 127, but leaves known-wrong tags rendering in the live Phase 126 UI for an unbounded window | |
| Dev + prod backfill both in-phase | Fixes everywhere immediately, but pulls a long prod data op into the phase gate against precedent | |

**User's choice:** Dev backfill in-phase, prod deferred to runbook.
**Notes:** Surfaced the wrinkle that SC#1's "NULL is honest" covers depth-NULL, but the precision fix makes existing tags *actively wrong* (not just missing depth) and they're already live in the Phase 126 UI — which is why doing nothing isn't neutral.

---

## Claude's Discretion

- Exact precision floor value(s) per tier (≈0.90 for core; confirm against measured fixture numbers during planning).
- Fixture sample size N per motif-theme and Rating-band stratification granularity.
- Precise form of the per-detector relevance/forcing gate (material-delta vs forcing-line membership vs both), validated by the harness precision delta.

## Deferred Ideas

- Player-facing depth unit + beginner/intermediate/advanced thresholds → Phase 129.
- Prod re-backfill execution → runbook after 127 ships.
- Hardening currently-suppressed tier-3 motifs to surface them → future phase.
- Confidence re-ranking (multi-motif storage) → already rejected in the architecture note; not revisited.
