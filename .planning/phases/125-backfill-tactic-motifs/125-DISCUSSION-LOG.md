# Phase 125: Backfill Tactic Motifs - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-18
**Phase:** 125-backfill-tactic-motifs
**Areas discussed:** Execution venue, DB-load posture, Verification, Environment scope, Phase-completion boundary

---

## Execution venue

| Option | Description | Selected |
|--------|-------------|----------|
| On the prod server | Run inside the prod box against localhost DB. Fast, survives laptop sleep, no tunnel. | |
| Tunnel from local | Follow existing `--db prod` pattern via SSH tunnel. Simpler but slow/fragile for 131k games. | |
| Discuss tradeoffs | Talk through resumability, wall-clock, tunnel risk. | |

**User's choice:** "Can we do it in the dev DB, just to see if it works, and build from there? We can do it in prod later."
**Notes:** Reframed the phase to a dev-first rehearsal; prod execution deferred. Drove the D-01 phase boundary.

---

## DB-load posture

| Option | Description | Selected |
|--------|-------------|----------|
| Let it rip concurrently | Run alongside the eval fleet, no pause. Pure-CPU, no Stockfish, benign write race. | ✓ |
| Pause/throttle the fleet | Quiesce the eval drain / run off-peak to minimize contention. | |
| Discuss | Talk through contention, batch size, write-race guarding. | |

**User's choice:** Let it rip concurrently
**Notes:** Backfill produces identical rows to the live eval-drain write path, so the concurrent race is benign. → D-03.

---

## Verification (acceptance bar for SC#1)

| Option | Description | Selected |
|--------|-------------|----------|
| Coverage report + NULL breakdown | % non-NULL motif, by-motif counts, NULL split (no-PV vs PV-but-no-fire), spot-check samples. | ✓ |
| Spot-check only | A few targeted queries + manual inspection, no structured report. | |
| You design the bar | Claude proposes verification in the plan. | |

**User's choice:** Coverage report + NULL breakdown
**Notes:** The NULL split (no PV at `flaw_ply+1` vs PV-present-but-no-detector) is what makes "honest coverage" verifiable. → D-04.

---

## Environment scope

| Option | Description | Selected |
|--------|-------------|----------|
| Prod only | Backfill prod alone with a dry-run smoke test first. | |
| Dev rehearsal then prod | Full dry-run on dev first, then prod. | ✓ |
| Also backfill benchmark | Additionally run on benchmark for future tactic-motif zones. | |

**User's choice:** Dev rehearsal then prod
**Notes:** Combined with the execution answer → dev now, prod later (deferred). Benchmark explicitly deferred.

---

## Phase-completion boundary

| Option | Description | Selected |
|--------|-------------|----------|
| Dev verified + prod runbook | Phase completes on dev backfill + passing coverage report + documented prod runbook; prod execution outside the gate. | ✓ |
| Dev then prod, both in-phase | Keep prod inside the completion gate. | |
| Dev only, re-scope SC | Spin prod into its own follow-up phase/seed. | |

**User's choice:** Dev verified + prod runbook
**Notes:** ROADMAP SC#1 recorded as met-on-dev / prod-pending. → D-01.

---

## Claude's Discretion

- Coverage-report format/location (ad-hoc SQL vs `scripts/` helper vs reusable query).
- Prod-runbook format/location.
- Sample sizes for spot-check and idempotency re-run.

## Deferred Ideas

- Prod backfill execution (runbook this phase; run later).
- Benchmark-DB backfill (future tactic-motif benchmark zones).
- Query-time suppression surfacing (Phase 126).
