# Phase 69: Benchmark DB Infrastructure & Ingestion Pipeline - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-25
**Phase:** 69 — Benchmark DB Infrastructure & Ingestion Pipeline
**Areas discussed:** Cheat contamination, Storage scope & retention, Sampling strategy, INGEST-06 migration scope, plus emergent: per-user-history sampling pivot

---

## Cheat contamination

| Option | Description | Selected |
|--------|-------------|----------|
| Older dumps + accept residual | Use 6-12 month-old dumps so most cheats are banned (originally proposed; corrected — Lichess does not re-publish dumps after bans propagate) | |
| Bans-list cross-reference at ingest | Pre-pass + Lichess `/api/users/status` cross-ref | |
| Document & accept bias | No filtering, document residual upward bias in 2000+ buckets | ✓ |
| CPL outlier rejection | Out of scope (no Stockfish eval available for non-eval games) | |
| Defer to Phase 70 verdict | Rely on Phase 70 gate as safety net | |

**User's choice:** "Yes, document & accept" with Phase 70 gate as safety net.
**Notes:** User flagged the original "older dumps where bans propagated" claim as unsubstantiated. Verified via WebFetch and WebSearch on database.lichess.org and the lichess-org/database GitHub issues — no documentation of post-publication dump updates. Reframing: older dumps don't sanitize themselves; only a bans-list cross-ref against the current ban state catches retroactive flags. User accepted residual bias is acceptable for v1.12 since Phase 70's gate is keyed on cells (Pawn / Rook / Minor) where contamination is minimal.

---

## Storage scope & retention

| Question | Option | Description | Selected |
|----------|--------|-------------|----------|
| Months ingested | One month, expand if needed | Start with one Lichess monthly dump | ✓ |
| Months ingested | Two-three months upfront | Pre-emptive multi-month ingest | |
| Months ingested | Adaptive multi-pass | Per-cell quota-based incremental | |
| Raw dump retention | Delete after parse | Re-download if re-ingest needed | ✓ |
| Raw dump retention | Keep one current dump | Cache for fast iteration | |
| Raw dump retention | Keep all | Full reproducibility archive | |

**User's choices:** "One month, expand if needed" + "Delete after parse"
**Notes:** D-02 was later clarified after the user-sampling pivot — "one month" applies to the **selection scan**, not to ingest itself (which sources from Lichess API per-user, not from dumps).

---

## Sampling strategy

| Option | Description | Selected |
|--------|-------------|----------|
| First-N per cell | Single-pass streaming with per-cell counter | ✓ (initially, then superseded) |
| Hash-stratified Bernoulli | Pre-set per-cell admission probabilities | |
| Two-pass count + sample | Scan-counts then sample by cell rate | |

**User's initial choice:** "First-N per cell"

### Player-opportunities sub-question

| Option | Description | Selected |
|--------|-------------|----------|
| Player-opportunities | Quota counts both player-sides; admit if either cell has room | ✓ |
| Games (assigned to one cell) | Pick one player-side per game | |
| Games (counted in both cells) | Increment both cells; skip when either is full | |

**User's choice:** "Player-opportunities" (D-05; preserved through later pivot)

### Pivot to user-level sampling (emergent gray area)

User raised: "Our benchmark will contain many games from different players, rather than full user game histories. That means it will be harder to calculate per user-metrics or timelines. Can we still use the data for validating our metrics and their zones?"

Analysis showed Phase 73's zone calibration uses both population-pooled rates (random-sample friendly) AND per-user-rate distributions (full-history friendly). Random-game sampling supports the first but not the second.

| Option | Description | Selected |
|--------|-------------|----------|
| Sample by users (multi-month dump scan) | U2: pre-select N players per cell, scan multiple monthly dumps for their games | |
| Sample by users (existing import pipeline) | U1: pre-select N players per cell from one dump, then call existing `import_service.run_import` per username via Lichess API | ✓ |
| Two-tier sampling | Random-game stratum + selected-user stratum | |
| Hybrid scope split | Keep random-game; per-user-distribution zones stay on prod data | |

**User's reasoning:** "If we sample users, we could select users based on a monthly dump, and then just use our existing pipeline to fetch their whole game histories."

**Notes:** U1 reuses ~80% of existing code (import_service, lichess_client, position_classifier, zobrist) and gives deeper per-user histories than U2.

### Schema flag and cap sub-questions

User pushed back on initial `is_benchmark` flag and per-user cap proposals:
- "Why would we need an is_benchmark flag? We have a separate benchmark DB where all users are benchmark users."
- "Not sure we should have a per user cap, probably not."
- "We might have to accept cohort drift."

All three accepted: D-08 (no flag), D-09 (no game-count cap), D-10 (accept drift, per-game bucketing handles it).

### Eval coverage and selection threshold

User: "Users will have evals for a subset of their games. We should probably accept this and store games without evals anyway, to preserve the game history. But we should select users in the initial monthly dump who have several games with evals, so the chance is higher that they evals also for prior games."

Locked: D-11 (full history including non-eval games), D-12 (selection threshold ≥ K eval-bearing games).

### Time window cap

| Option | Description | Selected |
|--------|-------------|----------|
| 12 months + 20k warning | My proposal | |
| 36 months + 20k hard cap | User counter-proposal — wants solid per-user estimates | ✓ |

**User's reasoning:** "We want solid estimates per user."
**Notes:** User chose hard skip over warning at 20k threshold. Storage flag raised: 36 months × N=500 players/cell may push storage to 150-250 GB, exceeding INGEST-05's 50-100 GB target. Resolved as planning-time tunable (D-15) — pilot first, resize N to fit budget.

---

## INGEST-06 migration scope

| Question | Option | Description | Selected |
|----------|--------|-------------|----------|
| Existing prod backfill | Leave NULL forever | New columns NULL on existing rows; new imports populate | ✓ |
| Existing prod backfill | Reimport prod users opportunistically | Trigger reimport on next login | |
| Existing prod backfill | Lazy fill on next import refresh | Re-fetch metadata when user re-imports | |
| Lichess metadata source | API per-game (verify, fallback NULL) | Spike whether `/api/games/export` returns depth | ✓ |
| Lichess metadata source | Constant per dump source | `eval_source_version='lichess-monthly-dump-YYYY-MM'`, `eval_depth=18` | |
| Lichess metadata source | Skip eval_depth, only source | Defer depth tracking to v1.13 | |

**User's choices:** "Leave NULL forever" + "Lichess API per-game (verify, fallback NULL)"
**Notes:** No prod-side backfill; Phase 70+ queries benchmark DB anyway. eval_source_version is a constant string per source ("lichess-pgn"), eval_depth populated when API surfaces it.

---

## Claude's Discretion

- Exact zgrep / streaming pre-filter tool for the dump selection scan
- Centipawn convention verification format (script self-test vs one-off note)
- MCP server local port, Postgres user/password setup, exact `docker-compose.benchmark.yml` structure
- Stub User row schema strategy in benchmark DB (sentinel email, password hash placeholder, is_active value)
- Ingestion outer-loop checkpoint structure for the list of selected usernames + per-user state
- Selection-scan player-bucketing algorithm details for players whose snapshot-month games span multiple TCs

## Deferred Ideas

- Bans-list cross-reference for cheats (v1.13+ if Phase 71 flags 2000+ as anomalous)
- Hybrid two-tier sampling (overbuilt for v1.12 MVP)
- CPL-based outlier rejection (no Stockfish eval available)
- Phase 69 split into 69 + 69.1 (not split; preserve as `/gsd-insert-phase` option if planner finds effort delta)
- Refresh cadence policy (belongs in Phase 73)
- Multi-month dump scan ingestion (U2 — rejected in favor of U1)
- Backfill of `eval_depth` / `eval_source_version` for prod games (out of scope per D-06)
- chess.com population baselines (explicitly v1.13+ per REQUIREMENTS.md `CHESS-COM-BL-01`)
- `is_benchmark` User flag (rejected — DB instance isolation suffices)
- Per-user game cap (rejected — 36-month window + 20k outlier skip handles it)
