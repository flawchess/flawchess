# Phase 144: User-28 A/B Validation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-30
**Phase:** 144-user-28-a-b-validation
**Areas discussed:** Sample size, A/B harness, Margin selection rule, Hand-check workflow

---

## Sample size

| Option | Description | Selected |
|--------|-------------|----------|
| Accept the 216 blob flaws | Run A/B on the 216 existing blob flaws today, no engine work; per-motif with small-N caveats | ✓ |
| Enlarge via live re-analysis first | Re-analyze user-28 dev games through the eval drain to populate more blobs (engine time) | |
| Add prod-28 as descriptive reference | Keep dev-28 as control, also report prod-28 ratios (sanity-only per VALID-01) | |

**User's choice:** Accept the 216 blob flaws.
**Notes:** User first asked whether running `retag_flaws.py` for user 28 before the A/B would help.
Clarified that retag re-derives *tags* from existing blobs and cannot create blobs — only an engine
pass writes blobs. With that corrected, and given the "keep 0.35 unless hand-check fails" rule, user
chose to accept the 216 as a confirmation-check sample. Verified against dev DB: 34,055 total flaws,
216 with blobs (100 allowed-tagged + 71 missed-tagged).

---

## A/B harness

| Option | Description | Selected |
|--------|-------------|----------|
| Dedicated ab-validate script | New `scripts/ab_validate_gate.py`: load blobs once, ungated vs gated in-memory, no DB writes | ✓ |
| Extend retag_flaws.py with --no-gate | Add a baseline mode to the rollout re-tagger | |
| Two dry-run passes + diff | Run retag --dry-run twice and diff the logs | |

**User's choice:** Dedicated ab-validate script.
**Notes:** Keeps the rollout tool clean; single-purpose, write-free. The old arm must be genuinely
ungated (NOT `--margin 0`, which still applies the already-winning/mate/one-mover logic).

---

## Margin selection rule

| Option | Description | Selected |
|--------|-------------|----------|
| Max noise removed, FN ceiling | Sweep a grid, pick largest margin under an FN ceiling | |
| Keep 0.35 unless hand-check fails | Treat 0.35 as default; only move off it if hand-check shows it's wrong | ✓ |
| Sweep, you pick from the table | Generate full table, user picks the value directly | |

**User's choice:** Keep 0.35 unless hand-check fails.
**Notes:** A/B is a confirmation check, not a fine-grained sweep. VALID-02 SC4 "commit final margin"
is satisfied by confirming 0.35 + recording the A/B justification (no value change unless 0.35 fails).

---

## Hand-check workflow

| Option | Description | Selected |
|--------|-------------|----------|
| Markdown w/ FEN+PV+lichess link | Committed reports/retag markdown; user adjudicates in-browser | ✓ |
| Random sample | Pure random ~30 | |
| Motif-stratified sample | Sample proportionally across motifs | (fallback) |

**User's choice:** Markdown w/ FEN+PV+lichess link; hand-check ALL dropped cases if ≤30, else
motif-stratified ~30.
**Notes:** Inherently HUMAN-UAT — requires the user's chess judgment. Produces an explicit
false-negative count (good tags killed) folded into the A/B summary.

---

## Claude's Discretion

- Exact `ab_validate_gate.py` CLI flags / signatures, the per-motif/depth table shape, the
  `reports/retag/` filename, the lichess deep-link format, how the ungated arm reuses the detection
  kernel, and whether a small context neighbourhood sweep (0.30/0.40) is included.

## Deferred Ideas

- Enlarging the dev blob sample via a fresh engine pass / `backfill_multipv.py` — Phase 145.
- prod-28 as a larger descriptive sanity reference — available per VALID-01, not opted into here.
