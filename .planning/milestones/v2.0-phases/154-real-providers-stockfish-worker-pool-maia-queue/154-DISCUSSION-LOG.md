# Phase 154: Real Providers (Stockfish Worker Pool + Maia Queue) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-06
**Phase:** 154-Real Providers (Stockfish Worker Pool + Maia Queue)
**Areas discussed:** Adaptive pool sizing, Worker warm-up timing, Eval-bar mutual exclusion, Maia queue granularity

---

## Adaptive pool sizing

| Option | Description | Selected |
|--------|-------------|----------|
| Cap + mobile floor | Desktop = clamp(hardwareConcurrency − 2, 2, 4); mobile = 2. Mobile = hardwareConcurrency ≤ 4 OR pointer:coarse; no UA sniff. | ✓ |
| Conservative mobile = 1 | Same desktop cap, mobile = single worker. Safest, slower on phones. | |
| Fixed deviceMemory tiers | Buckets by navigator.deviceMemory; degrades to a guess on Safari. | |

**User's choice:** Cap + mobile floor
**Notes:** Named tunable constants, revisited after real-device UAT.

---

## Worker warm-up timing

| Option | Description | Selected |
|--------|-------------|----------|
| Lazy on first request | Spawn SF pool + Maia worker on first search; terminate on idle/unmount. Low idle memory, slightly slower first result. | ✓ |
| Eager on page load | Snappy first result, ~1.5GB+ resident up front — risky vs Safari ceiling. | |
| Hybrid | Maia worker eager, SF pool lazy. | |

**User's choice:** Lazy on first request
**Notes:** Mirrors existing enabled-gated worker lifecycle; idle memory is the binding mobile concern.

---

## Eval-bar mutual exclusion (POOL-04)

| Option | Description | Selected |
|--------|-------------|----------|
| Engine wins, gate in 155 | Standalone eval bar pauses while engine pool runs the same position. 154 makes the pool abortable; the "engine busy" gate is wired in the 155 hook (flag to researcher). | ✓ |
| Eval bar wins | Pool waits until the eval bar finishes its depth, then runs. | |
| Defer policy to 155 | 154 only guarantees abortability; decide yielding direction entirely in 155. | |

**User's choice:** Engine wins, gate in 155
**Notes:** During an engine run the objective root eval is already computed, so pausing the redundant standalone bar is a feature. 154's obligation is a clean abort/lifecycle surface only.

---

## Maia inference granularity

| Option | Description | Selected |
|--------|-------------|----------|
| Only needed ELOs, own cache | Per node request just the distinct {w,b} ELOs (often 2), not the full ladder. Cache keyed by (fen, elo), separate from the chart. | ✓ |
| Full ladder, shared cache | Compute full ladder per position so one cache serves chart + engine; pays full cost per node. | |

**User's choice:** Only needed ELOs, own cache
**Notes:** Worker's eloInputs is already an array — pass [eloW, eloB] deduped; minimal worker change. Roadmap already locks a separate worker instance.

---

## Claude's Discretion

- SAN↔UCI conversion at the maiaQueue boundary (maskAndSoftmax emits SAN; policy() needs UCI).
- Priority-queue internals / scheduling data structure (POOL-02) — researcher territory; must pass a queue-ordering test.
- grade() → worker dispatch mapping across the pool (one grade = one worker's MultiPV; concurrency fans out).
- Per-worker abort/navigation handling (reuse stop-before-go), grade-depth / movetime constants, cache caps, Maia worker Sentry forwarding.

## Deferred Ideas

None — discussion stayed within phase scope. (SAB multithreading, per-ELO sigmoids, time-pressure conditioning, Maia-2 remain deferred in REQUIREMENTS.md → Future Requirements. React hook / UI / arrows / game-review overlay are Phases 155–157.)
