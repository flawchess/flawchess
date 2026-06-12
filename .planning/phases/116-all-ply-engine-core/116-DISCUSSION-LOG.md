# Phase 116: All-Ply Engine Core - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-12
**Phase:** 116-All-Ply Engine Core
**Areas discussed:** Dedup + eval provenance, Completion marker shape, Interim drain structure, Memory bound mechanism

---

## Dedup + eval provenance

**Q1: Which existing evals may the ply≤20 dedup reuse?**

| Option | Description | Selected |
|--------|-------------|----------|
| Parity-only | Only lichess %evals + new pipeline evals; legacy depth-15 ignored; worst case the accepted +26% ceiling | ✓ |
| Any existing eval | Max hit rate, no provenance needed, shallow evals leak into output | |
| You decide | | |

**Q2: How should the dedup identify parity evals?**

| Option | Description | Selected |
|--------|-------------|----------|
| Marker-gated | Only rows of games with the new full-analysis marker set — parity by construction, no migration | ✓ |
| Marker-gated + lichess heuristic | Also reuse legacy %evals via coverage heuristic — higher day-one hit rate, fragile | |
| eval_source column | Explicit provenance column + fuzzy legacy backfill | |

**Q3: What happens to legacy depth-15 evals when the full pass analyzes a game?**

| Option | Description | Selected |
|--------|-------------|----------|
| Overwrite with 1M | Uniform parity per game; one-time small stat shift accepted | ✓ |
| Preserve existing | No stat churn, permanent mixed-budget rows | |
| You decide | | |

**Notes:** During discussion Claude found `Game.is_analyzed` (`white_blunders IS NOT NULL`)
already discriminates lichess %eval games from everything else, eliminating the need for
any heuristic to implement the preserve-%evals / overwrite-depth-15 split (D-116-04,
derived — no user question needed).

---

## Completion marker shape

**Q1: What shape should the marker take?**

| Option | Description | Selected |
|--------|-------------|----------|
| Timestamp column | `full_evals_completed_at` on games, mirrors `evals_completed_at` + partial index | ✓ |
| Status enum column | pending/analyzing/completed — duplicates 117 queue state | |
| Separate analysis-state table | Front-loads 117 queue design | |

**Q2: Pre-mark already-covered games at migration time?**

| Option | Description | Selected |
|--------|-------------|----------|
| Verified backfill | Mark games where every non-terminal ply already has an eval — provable by SQL | ✓ |
| Let the drain discover them | Cold dedup start, coverage undercounts | |
| You decide | | |

**Q3: Marker set when some positions failed?**

| Option | Description | Selected |
|--------|-------------|----------|
| Mark complete | D-09 carried forward: NULL holes, Sentry, no retry loop | ✓ |
| Threshold retry | Only mark at ≥N% success — rebuilds the retry loop D-09 avoided | |
| You decide | | |

---

## Interim drain structure

**Q1: Relation to the existing entry-ply drain?**

| Option | Description | Selected |
|--------|-------------|----------|
| Second coroutine | run_eval_drain untouched; new full-ply drain with own marker/pick | ✓ |
| In-place upgrade | One lane; fresh imports wait hours for stats | |
| You decide | | |

**Q2: Live in prod with 116, or dormant until 117?**

| Option | Description | Selected |
|--------|-------------|----------|
| Live in 116 | LIFO interim pick, guest filter included, real QUEUE-07 soak | ✓ |
| Dormant until 117 | Flag-gated, no soak, big-bang activation in 117 | |
| Live, but window-capped | Front-loads tier-2 window logic | |

**Q3: Yield policy toward higher-priority work?**

| Option | Description | Selected |
|--------|-------------|----------|
| Gate between games | Check active import OR entry-ply pending before each game pick | ✓ |
| Gate on active imports only | Quick lane could crawl after a restart backlog | |
| Free-run on SCHED_IDLE | Contention is pool slots, not CPU — doesn't help | |

---

## Memory bound mechanism

**Q1: How to establish/enforce the bound?**

| Option | Description | Selected |
|--------|-------------|----------|
| Measure + document | Real per-worker RSS measurement; accounting in CLAUDE.md + code comment; no runtime machinery | ✓ |
| Measure + startup guard | Adds cgroup-reading runtime check for a deploy-time value | |
| Estimate from components | Assumption-based headroom despite OOM history | |

**Q2: Pool size in this phase?**

| Option | Description | Selected |
|--------|-------------|----------|
| Raise to 6 if accounting clears | (Premise was stale — prod already at 6) | |
| Keep current size in 116 | | |
| Other (free text) | "STOCKFISH_POOL_SIZE has been set at 6 in prod for several weeks, running stable. Either we keep it or bump it to 8 (using all 8 vCPU)" | ✓ |

**Q2b (follow-up): Keep 6 or bump to 8?**

| Option | Description | Selected |
|--------|-------------|----------|
| 8, contingent on checks | Ship 8 if memory accounting fits 4g AND prod soak shows API latency unaffected; fallback 6 | ✓ |
| Keep 6 | Spike-validated configuration, zero new risk | |

**Notes:** User corrected stale CLAUDE.md info (pool was never re-lowered after the
hotfix era; 6 has been stable for weeks). CLAUDE.md correction folded into this phase's
docs pass.

---

## Claude's Discretion

- Engine call plumbing for the node-budget search (keep UCI options centralized per ENG-03)
- 1M-node per-eval timeout (replace `_TIMEOUT_S = 2.0`)
- Dedup index shape + marker-gate join (no cross-user full_hash index exists today)
- Per-game fan-out granularity and write-transaction shape
- Terminal-position exclusion mechanics
- Verified-backfill execution shape (migration vs one-shot script)

## Deferred Ideas

- Pool-priority mechanism inside EnginePool (117 if gate-between-games proves too coarse)
- Window-capped automatic analysis (117/118, QUEUE-04 / D-3)
- `eval_source` provenance column (only if client workers land, SEED-012 D-8 phase 2)
