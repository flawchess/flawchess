# Phase 128: Missed-Opportunity Tagging - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-19
**Phase:** 128-missed-opportunity-tagging
**Areas discussed:** Storage shape, Backfill sequencing, Filter/schema scope, Missed-pass confidence/precision gating

---

## Storage shape (SC#4 — explicitly deferred to discuss)

| Option | Description | Selected |
|--------|-------------|----------|
| Inline 8 columns | missed_* + allowed_* inline on game_flaws; matches the wide pattern, no join for 0-2 orientations | ✓ |
| Child table | game_flaw_tactics(flaw_id, orientation, …), 0-2 rows/flaw; only earns its keep with a 3rd PV source | |

**User's choice:** Inline 8 columns
**Notes:** Confirms the design note's lean. Rename existing `tactic_* → allowed_*`, add `missed_*`. See CONTEXT D-01/D-02.

---

## Backfill sequencing (SEED-054 pv[flaw_ply] prod backfill still pending)

| Option | Description | Selected |
|--------|-------------|----------|
| Dev in-phase + prod runbook | Dev backfill as the gate; prod runbook runs after SEED-054's pv backfill lands (mirrors 127 D-13) | ✓ |
| Block on SEED-054 prod first | Treat SEED-054 prod pv backfill as a hard prereq so prod missed_* runs in-phase | |
| Discuss further | — | |

**User's choice:** Dev in-phase + prod runbook
**Notes:** Prod runbook ordering: SEED-054 pv backfill → then a single folded `classify` re-sweep filling 127's corrected allowed_* + allowed_tactic_depth + 128's missed_*. See CONTEXT D-11/D-12/D-13.

---

## Backend filter / schema scope (vs Phase 129 UI)

| Option | Description | Selected |
|--------|-------------|----------|
| Full orientation-aware filter + schema | Filter accepts orientation (missed/allowed); schemas expose both sets; 129 only wires UI | ✓ |
| Schema-only, minimal filter | Expose both sets but keep filter allowed-only; add orientation param in 129 with UI | |
| Discuss further | — | |

**User's choice:** Full orientation-aware filter + schema
**Notes:** Matches SC#5. Default-orientation behavior is Claude's discretion (preserve current allowed-only Library default); 129's UI default is missed. See CONTEXT D-07/D-08/D-09/D-10.

---

## Missed-pass confidence/precision gating

| Option | Description | Selected |
|--------|-------------|----------|
| Reuse 127 gate/floors unchanged | Detectors are orientation-agnostic; same relevance gate, confidence floor, suppression | ✓ |
| Add a missed-orientation validation pass | Extend the 127 puzzle harness to score the instead-of orientation separately | |
| Discuss further | — | |

**User's choice:** Reuse 127 gate/floors unchanged
**Notes:** Missed pass = `detect_tactic_motif(board_before, pv[flaw_ply], pov=mover)`. Depth indexed from flaw_ply (not flaw_ply+1) — document the baseline shift. See CONTEXT D-03/D-04/D-05/D-06.

---

## Claude's Discretion

- Exact `orientation` filter param name/shape and where the unspecified default lands (D-08).
- Split vs parametrize `_detect_tactic_for_flaw` (D-06).
- Migration revision structure (one revision for the 4 renames + 4 adds, strongly preferred).
- Backfill batch size / `--db` plumbing (reuse `scripts/backfill_flaws.py`).

## Deferred Ideas

- Phase 129: depth slider, missed/allowed toggle, chips, player-facing depth unit, mobile UI.
- Phase 129 UI choice: whether to surface the "opponent missed" scouting orientation.
- Prod re-backfill execution (SEED-054 pv + folded 127/128 classify re-sweep) — runbook, post-ship.
- Re-ranking by confidence / multi-motif-per-PV storage — rejected in the architecture note.
