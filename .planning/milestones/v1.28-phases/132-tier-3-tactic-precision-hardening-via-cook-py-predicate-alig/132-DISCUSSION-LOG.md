# Phase 132: Tier-3 tactic precision hardening via cook.py predicate alignment - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-23
**Phase:** 132-tier-3-tactic-precision-hardening-via-cook-py-predicate-alig
**Areas discussed:** Effort policy / triage, sacrifice scope, Dev re-backfill, Harness scoring basis

---

## Gray-area selection

Four gray areas (the ROADMAP's four open scope questions) were presented as a single multiSelect.
The user delegated all four to Claude with two explicit directives rather than discussing each:

> "You decide, but try to port as much as possible with a best effort attempt. Do a dev re-backfill
> using scripts/backfill_tactic_tags.py"

---

## Effort policy / triage

| Option | Description | Selected |
|--------|-------------|----------|
| Full port ALL 6 then suppress (131 D-02 parity) | Best-effort rebuild of every in-scope motif, suppress misses on TEST; "know the real ceiling" | ✓ |
| Surgical (full-port deflection+clearance, suppress near-zero ones) | Spend effort only on high-ROI motifs given Tier-3 is ~1.8% of volume | |

**User's choice:** Full port all, best-effort ("port as much as possible").
**Notes:** Reaffirms Phase 131 D-02. Captured as D-01. x-ray depth-risk folds in as D-03
(best-effort, not infinite-effort — cut short and suppress if PV-divergence ceiling proves real).

---

## sacrifice scope

| Option | Description | Selected |
|--------|-------------|----------|
| Include in port-then-suppress sweep | Port the material-diff co-tag, likely ends suppressed | ✓ (Claude's call under "port as much as possible") |
| Exclude as out-of-scope-by-nature | It's a co-tag, not a geometric motif, never fires (NaN) | |

**User's choice:** Delegated. Claude included it per the best-effort directive.
**Notes:** Captured as D-02. If the single-winner post-dispatch harness can't score a co-tag,
document and leave suppressed — don't fight the harness.

---

## Dev re-backfill

| Option | Description | Selected |
|--------|-------------|----------|
| Run dev re-backfill | Real-data validation of the port | ✓ |
| Skip (CC0 fixture is authoritative) | No prod urgency since tagging isn't deployed | |

**User's choice:** Run it, via `scripts/backfill_tactic_tags.py` (user named the script explicitly).
**Notes:** Captured as D-04. That script is purpose-built (tactic-columns-only, kernel-parity,
change-only UPDATEs) and cheaper than Phase 131's `backfill_flaws.py`. No prod re-backfill, no DB reset.

---

## Harness scoring basis

| Option | Description | Selected |
|--------|-------------|----------|
| Keep post-dispatch winner scoring as sole gate | Measures shipped reality; small-n/noisy for deep motifs | ✓ (Claude's call) |
| Add standalone-firing view to isolate predicate quality | Diagnostic during tuning, not a gate | partial — allowed as tuning aid only |

**User's choice:** Delegated. Confirmed factually that `tactic_tagger_report.py:193` already scores
the post-dispatch winner; kept it as the sole gate (D-05), with a standalone view permitted only as
a tuning diagnostic.
**Notes:** Bounds the phase ROI ceiling — Tier-3 motifs only win dispatch when nothing shallower
fires (~1.8% of tags). Stated explicitly in CONTEXT.md.

---

## Claude's Discretion

- All four gray areas were delegated ("you decide"); the two directives constrained D-01 (best-effort
  full port) and D-04 (dev re-backfill via the named script). sacrifice scope (D-02), x-ray cutoff
  (D-03), and harness basis (D-05) were resolved by Claude under those directives.

## Deferred Ideas

- Prod re-backfill / prod deployment of tactic tagging (not in prod).
- Hand-labeled prod-flaw precision set (CC0 fixture stays ground truth).
- SEED-058 (new motifs / lichess coverage), SEED-062 (comparison orientation basis).
- Promoting a standalone-firing precision view to a permanent harness gate.
