# Phase 126: Comparison Stats + Frontend - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-18
**Phase:** 126-comparison-stats-frontend
**Areas discussed:** Beta gate boundary, Motif filter scope, Grid granularity, Display details, Motif filter UX, Top-N ranking

---

## Beta gate boundary

| Option | Description | Selected |
|--------|-------------|----------|
| Backend + frontend (defense in depth) | Endpoint 403/empty + omit tactic_motif for non-beta + frontend hide | |
| Backend-enforced, frontend follows | New endpoint beta-gated server-side; existing flaw cards keep data, FE hides chips | |
| Frontend-only hide | All endpoints unchanged; FE checks beta_enabled and hides chips/grid/filters | ✓ |

**User's choice:** Frontend-only hide
**Notes:** Tactic-comparison serves the user their own chess data, so the gate is a feature-rollout flag, not a security boundary. Trade-off (tactic data reachable via direct API by non-beta users) flagged and accepted (D-01a).

---

## Motif filter scope

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — add a motif filter control | New beta-gated "filter by tactic motif" control (added scope) | ✓ |
| No — comparison grid + chips only | "Filters" meant existing game filters; no new control | |
| Defer motif filter to a follow-up | Ship chips + grid now; backlog the filter | |

**User's choice:** Yes — add a motif filter control
**Notes:** Beyond the literal TACCMP/TACUI requirements; flagged as scope addition per the scope guardrail and explicitly approved (D-05).

---

## Grid granularity

| Option | Description | Selected |
|--------|-------------|----------|
| Collapsed families | Fixed small set of families, named-mates collapse to "mate" | |
| Top-N by volume/significance | Show N motifs by most data / strongest gap | ✓ |
| All motifs clearing the sample gate | One bullet per individual motif with enough samples | |

**User's choice:** Top-N by volume/significance (refined to ~6 families ranked by significant gap — see Top-N ranking)

---

## Display details (multi-select)

| Option | Description | Selected |
|--------|-------------|----------|
| Hide low-confidence chips | Apply Phase 124 tactic_confidence threshold | ✓ |
| Headline rate = per-game | Per-game as the displayed metric | ✓ |
| Chip on both list + single card | Chip in flaw list rows AND single-game card | ✓ |

**User's choice:** All three selected (D-04, D-09, D-10)

---

## Motif filter UX

| Option | Description | Selected |
|--------|-------------|----------|
| In the FilterPanel, multi-select families | Beta-gated "Tactic motif" section in the drawer, multi-select by family | ✓ |
| Chip row above the flaw list, single-select | Tappable chip row, single motif | |
| In FilterPanel, single-select individual motif | Drawer section, one specific motif | |

**User's choice:** In the FilterPanel, multi-select families (D-06)

---

## Top-N ranking

| Option | Description | Selected |
|--------|-------------|----------|
| ~6 families, ranked by significant gap | Collapse to families, ~6 rows by largest Wilson-gated gap, volume fallback | ✓ |
| ~8 individual motifs by volume | Individual motifs by sample volume | |
| Top by gap, no family collapse | Individual motifs by significant gap, no collapse | |

**User's choice:** ~6 families, ranked by significant gap (D-07/D-08)

---

## Claude's Discretion

- Exact sample-gate and low-confidence chip thresholds (named constants, align with v1.25).
- Endpoint/service/repository file layout (follow the flaw-comparison analog).
- Final family taxonomy + key mapping and the family color palette in `theme.ts`.
- Motif-definition popover copy.
- MiniBulletChart benchmark-zone graceful degradation where no tactic benchmark exists.

## Deferred Ideas

- Backend hard-gating of tactic data behind beta_enabled (revisit if beta becomes a true access boundary).
- Per-100-blunders as a first-class displayed metric.
- Tactic-motif benchmark zones (population baselines for the bullet grid).
