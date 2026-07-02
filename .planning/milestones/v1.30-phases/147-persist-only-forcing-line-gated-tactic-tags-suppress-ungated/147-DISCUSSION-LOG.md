# Phase 147: Persist only forcing-line-gated tactic tags - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-01
**Phase:** 147-persist-only-forcing-line-gated-tactic-tags-suppress-ungated
**Areas discussed:** Old-corpus tag suppression (A), Local full-drain fate (B)

---

## Gray-area selection

| Option | Description | Selected |
|--------|-------------|----------|
| Phase scope: A+B or A-first split | Keep bundled (roadmap) vs ship A alone first | |
| Endpoint versioning (B) | New lease+submit pair vs new submit only | |
| Local full-drain fate (B) | Keep as fallback vs retire vs keep-now-retire-later | ✓ |
| Old-corpus tag suppression (A) | Go-forward only vs suppress old corpus too | ✓ |

**User's choice:** Discuss "Local full-drain fate" and "Old-corpus tag suppression".
**Notes:** The two unselected areas were treated as accepting defaults — phase scope stays bundled
(D-01), endpoint versioning uses the seed-lean new pair (D-02).

---

## Old-corpus tag suppression (A)

| Option | Description | Selected |
|--------|-------------|----------|
| Go-forward only (seed lean) | Thread blobs_pending only from _apply_submit; leave old rows for tier-4 | |
| Suppress old corpus too | Also NULL raw cp-tags on pre-142 rows now; clean invariant, needs backfill | ✓ |

**User's choice:** Suppress old corpus too (overrides seed lean).
**Notes:** Deliberately traded "changes what users see for old games until tier-4 catches up" for a
clean "no ungated tags anywhere" invariant. Expands Part A beyond the ~15-line classify change.

### Old-corpus suppression mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| One-shot backfill script | scripts/backfill_*.py, run manually, idempotent | |
| Alembic data migration | Guarded UPDATE runs automatically on deploy | ✓ |
| Reactive only (no bulk) | Let tier-4 D-07 retag each old row (= seed lean) | |

**User's choice:** Alembic data migration.
**Notes:** Carve-outs mandatory and identical to go-forward (keep mate-adjacent + D-06 `[]`
sentinels; suppress only `allowed_pv_lines IS NULL AND pre_flaw_eval_cp IS NOT NULL`). Claude flagged
a planner constraint: batch the UPDATE and confirm partial-index use so the migration doesn't stall
container startup on the high-cardinality `game_flaws` table.

---

## Local full-drain fate (B)

| Option | Description | Selected |
|--------|-------------|----------|
| Keep as fallback (seed lean) | Leave _full_drain_tick untouched as local spare capacity | ✓ |
| Retire it | Remove for a single write path / zero asymmetry | |
| Keep now, retire later | Keep this phase, defer retirement gated on prod observation | |

**User's choice:** Keep as fallback (seed lean accepted).
**Notes:** It was never a request path, so it never had the SEED-071 timeout problem; already gates
inline. Retirement captured as a deferred idea.

---

## Q5 (classifier/schema version tag on new submit)

| Option | Description | Selected |
|--------|-------------|----------|
| Lock: include version tag | Server rejects/relabels skewed workers | |
| Leave Q5 to the planner | Server-authoritative re-classify + A's NULL net already bound blast radius | ✓ |
| Explore more gray areas | — | |

**User's choice:** Leave Q5 to the planner.
**Notes:** Treated as a robustness nicety, not load-bearing, given the server re-classifies
authoritatively and A provides the graceful-degradation net.

---

## Claude's Discretion

- Q5 version tag (deferred to planner).
- Q4 worker hint-classify data availability (research verification — confirm no hidden DB dep via
  `derive_user_result`).
- Parameter naming/threading, migration batching strategy, new endpoint schema shapes + caps,
  worker loop cadence/back-pressure, MultiPV-2→1 full-ply optimization, dev-first validation gate.

## Deferred Ideas

- Retire `_full_drain_tick` once fleet gate is observed reliable in prod.
- Retire tier-4 + old `/lease`+`/submit` + `/flaw-blob-*` endpoints once the pre-B old corpus drains.
- Worker full-ply pass MultiPV-2 → MultiPV-1 (Phase 146 carryover, research-confirm).
