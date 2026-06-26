# Phase 125: Backfill Tactic Motifs — Research

**Researched:** 2026-06-18
**Domain:** Operational backfill — Python async batch script, PostgreSQL coverage reporting
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Phase 125 completes on the dev DB: the dev backfill is run, the coverage
  report passes on dev, and a documented prod runbook is ready. Prod execution is a
  deferred operational step outside the completion gate.
- **D-02:** Use `backfill_flaws.py --db dev --full-evald-only`. Smoke-test first with
  `--dry-run` / `--limit` before the full run.
- **D-03:** Let it rip concurrently — no pause or throttle needed. No Stockfish; race
  with eval-completion writes is benign (same classify path, identical rows).
- **D-04:** Prove honest coverage with a coverage report + NULL breakdown: (a) overall %
  non-NULL `tactic_motif`, (b) by-motif counts, (c) NULL split (no-PV vs PV-but-no-fire),
  (d) spot-check samples per NULL bucket.
- **D-05:** Idempotency check: re-run on a sample (or `--limit`) and assert rows are
  identical. Already guaranteed by delete-then-insert scoped to `(game_id, user_id)`.
- **D-06:** `backfill_flaws.py` recomputes the ENTIRE flaw record. Phase 124 only added
  tactic detection inside `_build_flaw_record` without touching other classify logic.
  Confirm non-tactic columns are byte-identical after the run.

### Claude's Discretion

- Coverage-report format and location (ad-hoc SQL vs a small `scripts/` helper vs a
  reusable query) — pick what makes the dev verification clean and re-runnable on prod.
- Prod-runbook format/location (a markdown note under `.planning/` or `scripts/`, or
  inline in the phase artifacts).
- Sample sizes for the spot-check and idempotency re-run.

### Deferred Ideas (OUT OF SCOPE)

- Prod backfill execution — runbook delivered this phase; actual prod run is a later
  operational step.
- Benchmark-DB backfill.
- Query-time suppression surfacing (Phase 126 concern).
- Any frontend, `/api/library/tactic-comparison`, chips, or comparison UI (Phase 126).
- Lichess-eval-only games — handled automatically via existing tier-3 idle fleet.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TACSCH-03 | Existing `game_flaws` rows backfilled with motif + piece for all self-eval'd games (`full_evals_completed_at` set, ~131k prod); lichess-eval-only games keep `tactic_motif = NULL` until full-eval'd via existing tier-3 idle fleet | `backfill_flaws.py --full-evald-only` targets exactly this cohort; script verified to support all required flags; dev rehearsal confirmed |
</phase_requirements>

---

## Summary

Phase 125 is an operational backfill with no new feature code. Phase 124 delivered the
detector (`detect_tactic_motif`), the three `game_flaws` columns, and wired detection
into `classify_game_flaws`. `scripts/backfill_flaws.py` already produces tactic motifs
as a side effect of its full flaw recompute; it already supports every flag named in the
decisions. The phase has three concrete deliverables: (1) run the backfill on the dev DB,
(2) produce and pass a coverage/NULL-breakdown report, and (3) document a prod runbook.

**Primary recommendation:** The backfill script needs no code changes. The only
plausibly-new code is the coverage-report query/helper for D-04, which is a read-only
SQL artifact. Recommend a small `scripts/coverage_report_tactic_motifs.py` helper so it
is re-runnable on prod with `--db dev|benchmark|prod`.

The D-06 blast-radius analysis reveals one important nuance: the eval-coverage denominator
fix (`831bae38`, 2026-06-15) changed `_compute_eval_coverage` so that short games
(previously <= 8 movable positions scored < 90% under the old formula) now pass the gate.
This means the backfill may write **new** flaw rows for approximately 126 short full-eval'd
games in dev that currently have zero or sparse coverage. The non-tactic columns for
already-stored rows will be byte-identical; the tactic columns are net-new everywhere.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Flaw recompute (detect + store) | Script (batch) | Database | `backfill_flaws.py` drives; PostgreSQL holds state |
| Tactic detection | Service layer (pure CPU) | — | `classify_game_flaws` -> `_detect_tactic_for_flaw` -> `detect_tactic_motif`; no I/O |
| Coverage reporting | Script (read-only SQL) | — | One-shot analysis + re-run on prod; no API layer needed |
| Idempotency guarantee | Database (delete-then-insert) | Script | `delete_flaws_for_game` + `bulk_insert_game_flaws` per `(game_id, user_id)` |
| Prod runbook | Documentation | Script | Exact commands + expected output; human-executed deferred step |

---

## Standard Stack

No new packages. This phase uses the project's existing stack exclusively.

| Component | Version | Purpose |
|-----------|---------|---------|
| `scripts/backfill_flaws.py` | (project) | Batch recompute driver — already complete |
| `app/services/flaws_service.py` | (project) | `classify_game_flaws` + `_detect_tactic_for_flaw` — already wired |
| `app/services/tactic_detector.py` | (project) | `detect_tactic_motif` dispatcher — Phase 124, already validated |
| `app/repositories/game_flaws_repository.py` | (project) | `flaw_record_to_row`, `delete_flaws_for_game`, `bulk_insert_game_flaws` |
| SQLAlchemy 2.x async | 2.x | ORM — `select()` API, no legacy 1.x |
| asyncpg | (uv lockfile) | Async PostgreSQL driver |
| python-chess | 1.11.x | Chess board logic in `detect_tactic_motif` |

**No new dependencies to install.**

## Package Legitimacy Audit

Not applicable — no new packages installed in this phase.

---

## Architecture Patterns

### System Architecture Diagram

```
dev DB (full_evals_completed_at IS NOT NULL: 11,199 games)
    |
    v
backfill_flaws.py --db dev --full-evald-only
    |
    +-- Phase 1: load game IDs (stmt.where(Game.full_evals_completed_at.isnot(None)))
    |
    +-- Phase 2: batch loop (BACKFILL_GAMES_PER_BATCH = 100)
    |       |
    |       +-- per game:
    |           fetch_game_positions_ordered(session, game_id, user_id)
    |               |
    |               v
    |           classify_game_flaws(game_obj, positions)
    |               |
    |               +-- _compute_eval_coverage() -> gate (<0.90 -> GameNotAnalyzed)
    |               +-- _recompute_fen_map(game.pgn)
    |               +-- _run_all_moves_pass(positions) -- both colors
    |               +-- for each mistake/blunder:
    |                   _build_flaw_record(n, ..., fen_map, positions)
    |                       |
    |                       v
    |                   _detect_tactic_for_flaw(n, fen_map, positions)
    |                       reads: positions[n+1].pv  <- SEED-039 refutation line
    |                       calls: detect_tactic_motif(board_after_flaw, pv_str)
    |                           -> (tactic_motif_int, tactic_piece, tactic_confidence)
    |               |
    |               v
    |           flaw_record_to_row(user_id, game_id, flaw)
    |               writes: tactic_motif, tactic_piece, tactic_confidence
    |               |
    |               v
    |           delete_flaws_for_game(game_id, user_id)   -- idempotent delete
    |           bulk_insert_game_flaws(rows)               -- ON CONFLICT DO NOTHING
    |
    +-- commit per batch (OOM-safe)
    |
    v
coverage_report query (read-only SQL)
    game_flaws JOIN games JOIN game_positions (at ply+1)
        -> overall % non-NULL tactic_motif
        -> by-motif counts
        -> NULL split: no-PV-at-ply+1 vs PV-present-but-no-fire
```

### Recommended Project Structure

No new directories. One new file:

```
scripts/
├── backfill_flaws.py       # existing — no changes needed
├── backfill_eval.py        # existing — precedent for --db pattern + prod runbook
└── coverage_report_tactic_motifs.py  # NEW — D-04 coverage report helper
```

The coverage report script follows the `backfill_eval.py` pattern: `--db dev|benchmark|prod`,
standard `db_url_for_target`, async main, timestamped log output. It runs read-only SQL only.

### Pattern 1: `--full-evald-only` Targeting Query

The exact `_parse_args` / `run_backfill` CLI surface (verified from `scripts/backfill_flaws.py`):

```python
# Source: scripts/backfill_flaws.py (verified)
parser.add_argument("--db", choices=["dev", "benchmark", "prod"], required=True)
parser.add_argument("--user-id", type=int, default=None, dest="user_id")
parser.add_argument("--dry-run", action="store_true", dest="dry_run")
parser.add_argument("--limit", type=int, default=None)
parser.add_argument("--full-evald-only", action="store_true", dest="full_evald_only")
```

Targeting query for `--full-evald-only` (verified, `run_backfill` lines 159-171):

```python
# Source: scripts/backfill_flaws.py (verified)
stmt = select(Game.id, Game.user_id)
if full_evald_only:
    stmt = stmt.where(Game.full_evals_completed_at.isnot(None))
stmt = stmt.order_by(Game.id)
if limit is not None:
    stmt = stmt.limit(limit)
```

### Pattern 2: Tactic Detection Input Chain (Verified)

The PV lives at `positions[n+1].pv` (one ply after the flawed move — SEED-044 post-move
convention). The code guard in `_detect_tactic_for_flaw` is:

```python
# Source: app/services/flaws_service.py lines 374-391 (verified)
pv: str | None = positions[n + 1].pv if n + 1 < len(positions) else None
# ... if not (fen_before_flaw and pv and move_san_of_flaw): return None, None, None
```

Three conditions must all be non-empty for detection to fire:
1. `fen_before_flaw` — from `fen_map.get(n, "")` (empty if PGN replay failed at ply n)
2. `pv` — from `positions[n+1].pv` (NULL when no full-eval stored for this game/ply)
3. `move_san_of_flaw` — from `positions[n].move_san` (NULL on terminal position, but flaws can't be at terminal)

### Pattern 3: Idempotency Mechanism (Verified)

```python
# Source: scripts/backfill_flaws.py lines 241-253 (verified)
await delete_flaws_for_game(session, game_id=game_id_val, user_id=game_user_id)
rows = [flaw_record_to_row(user_id=game_user_id, game_id=game_id_val, flaw=flaw)
        for flaw in flaw_list]
await bulk_insert_game_flaws(session, rows)
```

`delete_flaws_for_game` uses `DELETE WHERE game_id = ? AND user_id = ?` (both columns — no
cross-user deletion possible). `bulk_insert_game_flaws` uses `ON CONFLICT DO NOTHING` on the PK
`(user_id, game_id, ply)`. The combination means: re-running the backfill on the same game
produces identical rows (delete clears the slate, insert writes fresh). [VERIFIED: scripts/backfill_flaws.py, app/repositories/game_flaws_repository.py]

### Pattern 4: Coverage Report SQL (D-04 Design)

The NULL-split join requires `game_positions` at `ply = flaw_ply + 1`. Since the `pv` column
lives at `game_positions.pv` and the composite PK is `(user_id, game_id, ply)`, the join is:

```sql
-- Source: derived from app/models/game_position.py + app/models/game_flaw.py (verified)
-- Overall coverage on M+B flaws for full-eval'd games
SELECT
    COUNT(*) AS total_mb_flaws,
    COUNT(gp_next.pv) AS has_pv,
    COUNT(*) FILTER (WHERE gp_next.pv IS NOT NULL AND gf.tactic_motif IS NOT NULL) AS tagged,
    COUNT(*) FILTER (WHERE gp_next.pv IS NOT NULL AND gf.tactic_motif IS NULL) AS pv_no_fire,
    COUNT(*) FILTER (WHERE gp_next.pv IS NULL) AS no_pv_null
FROM game_flaws gf
JOIN games g ON g.id = gf.game_id AND g.user_id = gf.user_id
LEFT JOIN game_positions gp_next
    ON gp_next.game_id = gf.game_id
    AND gp_next.user_id = gf.user_id
    AND gp_next.ply = gf.ply + 1
WHERE g.full_evals_completed_at IS NOT NULL
  AND gf.severity IN (1, 2);

-- By-motif counts
SELECT
    gf.tactic_motif,
    COUNT(*) AS count
FROM game_flaws gf
JOIN games g ON g.id = gf.game_id AND g.user_id = gf.user_id
WHERE g.full_evals_completed_at IS NOT NULL
  AND gf.severity IN (1, 2)
  AND gf.tactic_motif IS NOT NULL
GROUP BY gf.tactic_motif
ORDER BY count DESC;
```

### Anti-Patterns to Avoid

- **Running without `--full-evald-only`:** without the flag, the script loads ALL games
  including those without full evals. The coverage gate still skips them, but it wastes
  time loading all positions for ~600k+ games. Always use `--full-evald-only` for this phase.
- **Running without `--dry-run` first:** always smoke-test with `--dry-run --limit 20`
  before the full run. The dry-run classifies without writing, so it exercises the classify
  path without modifying the DB.
- **Forgetting `bin/prod_db_tunnel.sh` for prod:** the prod DB is on `localhost:15432` via
  SSH tunnel — the tunnel must be up before `--db prod`. See `backfill_eval.py` precedent.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Idempotent batch writes | Custom upsert logic | Existing `delete_flaws_for_game` + `bulk_insert_game_flaws` | Already correct, tested, OOM-safe |
| Tactic detection | New detector code | `detect_tactic_motif` in `tactic_detector.py` | Phase 124, precision-validated (51 tests pass, 16 motifs at >= 0.90 precision bar) |
| NULL-split verification | Manual row counting | Coverage report SQL with PV LEFT JOIN | Precisely separates no-PV bucket from PV-present-but-no-fire bucket |
| DB connection for prod | Direct SSH / `psql` | `bin/prod_db_tunnel.sh` + `--db prod` | Standard prod-safe pattern (matches `backfill_eval.py` runbook) |

---

## Runtime State Inventory

Not applicable to this phase. Phase 125 is a pure data backfill, not a rename or
migration. There is no runtime state (service names, OS task scheduler entries, stored
keys, or build artifacts) that needs updating.

---

## Common Pitfalls

### Pitfall 1: PV Coverage is Sparse (19% of M+B Flaws on Dev)

**What goes wrong:** The developer expects most flaws to get a tactic tag and is surprised
when the majority remain NULL.

**Why it happens:** `game_positions.pv` is stored only at `flaw_ply + 1` positions, and the
full-eval drain only writes PVs for games that have been fully processed by the remote
eval worker. Dev has 18,035 PVs total, but only 12,916 land at `flaw_ply + 1` for flaws on
full-eval'd games. That is 19.0% of 68,150 eligible M+B flaw rows.

**How to avoid:** Frame the acceptance bar correctly — "NULL rows reflect genuine low-confidence
or no-PV, not skipped." The coverage report's NULL split (no-PV vs PV-present-but-no-fire)
is exactly the proof. Do not treat a low overall non-NULL % as a failure. [VERIFIED: dev DB query]

**Warning signs:** If the coverage report shows 0% non-NULL after a full (non-dry-run)
backfill, the tactic columns are not being written — check `flaw_record_to_row` uses `.get()`
on the tactic fields (lines 118-120 of `game_flaws_repository.py`).

### Pitfall 2: D-06 Blast-Radius — Short Games May Gain New Flaw Rows

**What goes wrong:** The before/after non-tactic column comparison flags "new" flaw rows as
evidence of column drift.

**Why it happens:** The eval-coverage denominator fix (`831bae38`, 2026-06-15) changed
`_compute_eval_coverage` to divide by `len(positions) - 1` instead of `len(positions)`. Games
with <= 8 movable positions previously scored < 90% and returned `GameNotAnalyzed`; now they
pass the gate. Dev has approximately 126 full-eval'd games with <= 9 positions. Some had zero
flaw rows (because they were classified as `GameNotAnalyzed`) and may gain new rows post-backfill.
This is correct behavior, not drift. [VERIFIED: dev DB query; 126 short games, 1 existing flaw row on these games]

**How to avoid:** The before/after comparison should scope to games with > 9 positions (or any
game that already had flaw rows). The plan must document that gaining new rows for short games
is expected and correct.

**Warning signs:** If a game that had N flaw rows before now has M != N rows (excluding new
short-game rows), that is drift in non-tactic classification and must be investigated.

### Pitfall 3: `ON CONFLICT DO NOTHING` Masks Corrupted Rows

**What goes wrong:** The backfill is run on a game that already has flaw rows, but
`delete_flaws_for_game` is skipped (e.g., script modified incorrectly to skip deletes).
The `ON CONFLICT DO NOTHING` in `bulk_insert_game_flaws` then silently ignores new rows.

**Why it happens:** `bulk_insert_game_flaws` uses `ON CONFLICT DO NOTHING` as a guard for
the import hook (which cannot delete-then-insert). The backfill correctly deletes first.

**How to avoid:** The backfill code path always calls `delete_flaws_for_game` before
`bulk_insert_game_flaws`. Verify the sequence in the code — do not modify it.

### Pitfall 4: Concurrent Eval-Drain Race is Benign (not a pitfall)

The eval drain also writes to `game_flaws` via the same `classify_game_flaws` path. A race
between the backfill and the drain on the same game produces identical rows (same code path,
same inputs), so `ON CONFLICT DO NOTHING` on the drain side silently no-ops. The backfill's
delete-then-insert on a game being actively eval-drained could briefly delete rows that the
drain rewrites, but the final state is correct. This is documented in D-03. [ASSUMED: based on code analysis]

### Pitfall 5: Prod Tunnel Must Be Running Before `--db prod`

**What goes wrong:** `--db prod` fails with a connection error because the SSH tunnel is not up.

**Why it happens:** Prod PostgreSQL is on `localhost:15432` via `bin/prod_db_tunnel.sh` (SSH
port-forward). Without the tunnel, the connection attempt fails immediately.

**How to avoid:** The prod runbook must document: (1) `bin/prod_db_tunnel.sh` first,
(2) verify tunnel with `psql postgresql://...@localhost:15432`, (3) then run the backfill,
(4) `bin/prod_db_tunnel.sh stop` afterward. See `backfill_eval.py` docstring for the precedent.

---

## Code Examples

### Confirmed CLI Invocations

```bash
# Source: scripts/backfill_flaws.py (verified argparse surface)

# Step 1: Smoke-test (dry-run, first 20 games)
uv run python scripts/backfill_flaws.py --db dev --full-evald-only --dry-run --limit 20

# Step 2: Full dev backfill
uv run python scripts/backfill_flaws.py --db dev --full-evald-only

# Step 3: Idempotency re-run (same as Step 1 but after full run)
uv run python scripts/backfill_flaws.py --db dev --full-evald-only --dry-run --limit 100

# Prod backfill (deferred — after tunnel is up)
bin/prod_db_tunnel.sh
uv run python scripts/backfill_flaws.py --db prod --full-evald-only
bin/prod_db_tunnel.sh stop
```

### `flaw_record_to_row` Tactic Fields (Verified)

```python
# Source: app/repositories/game_flaws_repository.py lines 118-120 (verified)
return {
    # ... non-tactic fields ...
    # Tactic family (Phase 124 — D-01): use .get() so older construction paths
    # that omit these keys map to None rather than KeyError.
    "tactic_motif": flaw.get("tactic_motif_int"),
    "tactic_piece": flaw.get("tactic_piece"),
    "tactic_confidence": flaw.get("tactic_confidence"),
}
```

### `_detect_tactic_for_flaw` PV Access (Verified)

```python
# Source: app/services/flaws_service.py lines 373-377 (verified)
fen_before_flaw = fen_map.get(n, "")
pv: str | None = positions[n + 1].pv if n + 1 < len(positions) else None
move_san_of_flaw: str | None = positions[n].move_san

if not (fen_before_flaw and pv and move_san_of_flaw):
    return None, None, None
```

---

## D-04 Coverage Report: Concrete Recommendation

**Format:** A standalone `scripts/coverage_report_tactic_motifs.py` script.

**Rationale:** The backfill_eval.py precedent shows this pattern is clean and re-runnable.
A script is better than ad-hoc SQL for Phase 125 because:
1. It can be run identically on prod later (the deferred prod runbook step).
2. It formats the output in a readable way with section headers and % labels.
3. It can be committed and reviewed alongside the plan.

A reusable query in the repository layer would be overkill — this is a one-off verification
output, not an endpoint query. Ad-hoc SQL in the plan document is not re-runnable.

**Required output sections (from D-04):**

```
=== Tactic Motif Coverage Report ===
Scope: mistake+blunder flaws on full-eval'd games

Overall:
  Total M+B flaw rows:     68,150  (expected; dev baseline)
  Flaws with PV at ply+1:  12,916  (19.0%) <- tactic-detectable
  Flaws without PV:        55,234  (81.0%) <- genuinely undetectable

After Backfill:
  Non-NULL tactic_motif:   X       (Y% of has-PV rows)
  By-motif counts:         [table]

NULL split:
  No PV at ply+1:          55,234  <- no_pv_null bucket
  PV present, no fire:     X       <- pv_no_fire bucket (honest low-confidence)

Spot-check samples:
  [3 rows from no_pv_null bucket]
  [3 rows from pv_no_fire bucket]
```

**Acceptance bar (SC#1):** The no_pv_null count must match the `no_pv` number from the
pre-backfill SQL (55,234 on dev). The pv_no_fire bucket can be any size — these are
precision-first genuine low-confidence no-fires, not errors.

---

## D-06 Blast-Radius Verification Approach

**Proposed approach:** Before/after comparison on non-tactic columns for a sample of games
that already had flaw rows (to exclude the short-game new-row effect).

```bash
# Before backfill: snapshot non-tactic columns for a sample
psql postgresql://flawchess:flawchess@localhost:5432/flawchess -c "
  COPY (
    SELECT user_id, game_id, ply, severity, tempo, phase,
           is_miss, is_lucky, is_reversed, is_squandered, fen
    FROM game_flaws
    WHERE (user_id, game_id) IN (
      SELECT user_id, id FROM games
      WHERE full_evals_completed_at IS NOT NULL
      ORDER BY id LIMIT 50
    )
    ORDER BY user_id, game_id, ply
  ) TO '/tmp/before_backfill_sample.csv' CSV HEADER
"

# After backfill: same query, compare with diff
```

**Simpler alternative (recommended for plan):** The plan can reason from the git diff
that only `tactic_motif`, `tactic_piece`, `tactic_confidence` fields were added in
Phase 124. No severity, tag, tempo, phase, or FEN logic changed. This reasoning is
documented in the Phase 124 VERIFICATION.md (10/10 truths, no anti-patterns).

One exception documented in Pitfall 2: short games (<=9 positions) may gain new rows.
The plan should document this as expected and scope the "non-tactic columns byte-identical"
assertion to games with > 9 positions that already had flaw rows.

---

## Dev DB Ground Truth (Verified 2026-06-18)

All counts verified via `mcp__flawchess-db__query` / asyncpg against the dev DB.

| Metric | Value | Source |
|--------|-------|--------|
| Full-eval'd games (`full_evals_completed_at IS NOT NULL`) | 11,199 | [VERIFIED: dev DB] |
| Total `game_flaws` rows | 89,007 | [VERIFIED: dev DB] |
| `game_flaws` rows on full-eval'd games (M+B) | 68,150 | [VERIFIED: dev DB] |
| `game_flaws` rows with `tactic_motif IS NOT NULL` | 0 | [VERIFIED: dev DB] |
| `game_positions` rows with `pv IS NOT NULL` | 18,035 | [VERIFIED: dev DB] |
| PVs on full-eval'd game positions | 12,916 | [VERIFIED: dev DB] |
| M+B flaws with PV at `flaw_ply + 1` (detectable) | 12,916 (19.0%) | [VERIFIED: dev DB] |
| M+B flaws without PV at `flaw_ply + 1` (no-PV NULL) | 55,234 (81.0%) | [VERIFIED: dev DB] |
| M+B mistakes with PV / without PV | 5,363 / 22,891 | [VERIFIED: dev DB] |
| M+B blunders with PV / without PV | 7,553 / 32,343 | [VERIFIED: dev DB] |
| Flaws with no `ply+1` position (last-ply edge case) | 6 | [VERIFIED: dev DB] |
| Full-eval'd games with <= 9 positions (D-06 edge case) | 126 | [VERIFIED: dev DB] |
| Flaw rows on those 126 short games (pre-backfill) | 1 | [VERIFIED: dev DB] |
| `game_flaws` rows on non-full-eval'd games | 20,857 | [VERIFIED: dev DB] |

The `total_game_flaws (89,007) = full-evald (68,150) + non-full-evald (20,857)` checks out.

---

## `_QUERY_SUPPRESSED_MOTIFS` (Phase 126 Input, NOT a Phase 125 Filter)

The 8 suppressed motifs are defined in `tests/services/test_tactic_detector.py` (verified,
lines 60-71). Phase 125 stores all fired motifs unconditionally (D-11 from Phase 124).
Phase 126 decides which to surface in the UI. The suppressed set is:

```python
# Source: tests/services/test_tactic_detector.py lines 60-71 (verified)
_QUERY_SUPPRESSED_MOTIFS = frozenset({
    "double-check",       # 1 prod occurrence in dev sample
    "interference",       # 1 prod occurrence
    "smothered-mate",     # 2 prod occurrences
    "self-interference",  # 0 prod occurrences in dev sample
    "sacrifice",          # 0 (rarely priority winner; geometric/hanging pre-empt)
    "arabian-mate",       # 0 prod occurrences
    "boden-mate",         # 0 prod occurrences
    "double-bishop-mate", # 0 prod occurrences
})
```

The planner must ensure the coverage report's by-motif table includes these 8 to confirm
they exist in the DB (or are genuinely absent). Do not add query-time suppression to the
backfill or the report.

---

## Prod Runbook Inputs (for Deferred Execution)

**DB target:** `localhost:15432` via `bin/prod_db_tunnel.sh` (SSH port-forward).
**Expected scale:** ~131,000 full-eval'd games (prod 2026-06-17 per architecture note).
**Batching:** `BACKFILL_GAMES_PER_BATCH = 100` (named constant — do not change unless
prod soak shows pressure per D-03).
**Concurrency posture:** Let it rip (D-03) — no Stockfish, pure CPU, benign race.
**Estimated run time:** [ASSUMED: ~11,199 dev games in several minutes; prod 131k ~ 12× longer, likely 30-90 min depending on position count per game and DB I/O]

**Runbook document location recommendation:** `.planning/phases/125-backfill-tactic-motifs/PROD-RUNBOOK.md`.
This keeps the runbook adjacent to the phase artifacts and is easy to reference.

**Runbook template (for planner):**

```markdown
# Prod Backfill Runbook: Tactic Motifs (Phase 125)

## Prerequisites
- SSH tunnel must be up: `bin/prod_db_tunnel.sh`
- Verify tunnel: `psql postgresql://<url>@localhost:15432/flawchess -c "SELECT COUNT(*) FROM game_flaws"`
- .env must contain DATABASE_URL_PROD

## Commands
1. Smoke-test (dry-run, 50 games):
   uv run python scripts/backfill_flaws.py --db prod --full-evald-only --dry-run --limit 50
2. Full prod backfill:
   uv run python scripts/backfill_flaws.py --db prod --full-evald-only
3. Coverage report:
   uv run python scripts/coverage_report_tactic_motifs.py --db prod
4. Close tunnel:
   bin/prod_db_tunnel.sh stop

## Verification
- Coverage report must show: total flaws = ~N (prod baseline), no_pv_null bucket expected ~81% (same ratio as dev)
- tactic_motif non-NULL % should match dev ratio on has-PV rows
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `_compute_eval_coverage`: divides by `len(positions)` (counts terminal) | Divides by `len(positions) - 1` (excludes terminal) | Phase 125 research: `831bae38` 2026-06-15 | ~126 short games now pass the coverage gate; backfill may produce new flaw rows for them (Pitfall 2) |
| No tactic columns in `game_flaws` | `tactic_motif`, `tactic_piece`, `tactic_confidence` (all NULL pre-backfill) | Phase 124, 2026-06-18 | Backfill populates these for all full-eval'd games with PV at flaw_ply+1 |
| `pv` column in `game_positions`: stored during full-eval drain | Same | Phase 117 (SEED-044) | Existing data — backfill consumes it, no new engine pass |

**Deprecated/outdated in this context:**
- `is_opponent` stored column: voided in v1.25 (FLAWX-03); derived at query time via `is_opponent_expr(ply, games.user_color)`.
- `es_before`, `es_after`, `move_san` on `game_flaws`: dropped in Phase 112 (D-07); sourced via `game_positions` join at query time.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + pytest-xdist |
| Config file | `pyproject.toml` (addopts includes project markers) |
| Quick run command | `uv run pytest tests/services/test_tactic_detector.py -q` |
| Full suite command | `uv run pytest -n auto` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TACSCH-03 | `backfill_flaws.py` writes `tactic_motif`/`tactic_piece`/`tactic_confidence` for full-eval'd games | integration | `uv run pytest tests/scripts/test_backfill_flaws.py -x` | Check if exists |
| TACSCH-03 | Idempotency: re-run produces identical rows | integration | `uv run pytest tests/scripts/test_backfill_flaws.py::test_idempotent -x` | Check if exists |
| TACSCH-03 | Lichess-eval-only games keep tactic_motif = NULL | integration | `uv run pytest tests/scripts/test_backfill_flaws.py::test_full_evald_only -x` | Check if exists |

### Sampling Rate

- Per verification: `uv run pytest tests/services/test_tactic_detector.py -q` (existing, 51 tests)
- Phase gate: full suite green before `/gsd-verify-work`

### Wave 0 Gaps

`tests/test_backfill_flaws.py` EXISTS (verified) and covers dry-run, real-run, and
idempotency from Phase 108. However, it does NOT assert the tactic columns because it
predates Phase 124. The test fixture uses synthetic GamePosition rows with no `pv` set,
so tactic_motif will always be NULL in the current fixture.

Phase 125 Wave 0 must add or extend this test to cover tactic column population:

- [ ] `tests/test_backfill_flaws.py` — add a test that seeds a GamePosition with a real
  `pv` value at `flaw_ply + 1`, runs `run_backfill`, and asserts that the resulting
  `GameFlaw` row has `tactic_motif IS NOT NULL` (detection fired) or confirms that
  `tactic_motif IS NULL` when pv is absent (no-PV NULL bucket). One test covers both
  paths.

Note: `run_backfill` already accepts an injectable `session_maker` (line 119 of
`backfill_flaws.py`) — the integration test can inject a session scoped to test fixtures
without touching the real dev DB. The existing `committed_analyzed_game` fixture can be
extended to add a `pv` field to one of the positions at `blunder_ply + 1`.

---

## Security Domain

No new attack surfaces introduced. This phase runs a script that:
- Reads from the DB using existing ORM queries with parameterized binds (no string interpolation)
- Writes via the existing `delete_flaws_for_game` + `bulk_insert_game_flaws` path (scoped to `(game_id, user_id)` — no cross-user write possible)
- Has no HTTP endpoints, no auth, no external API calls

ASVS categories: not applicable to a batch script with no network surface.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker (dev DB) | `backfill_flaws.py --db dev` | ✓ | PostgreSQL 18 (confirmed running) | — |
| `uv` | Script execution | ✓ | (project standard) | — |
| `bin/prod_db_tunnel.sh` | Prod runbook | ✓ | (exists in scripts/) | — |
| SSH to flawchess host | Prod runbook | Not verified | — | Admin must verify before prod run |

**Missing dependencies with no fallback:** none for dev execution. SSH access to prod must be
verified before the deferred prod run.

---

## Open Questions

1. **Does `tests/test_backfill_flaws.py` cover tactic columns?**
   - What we know: `tests/test_backfill_flaws.py` EXISTS (verified) and covers dry-run,
     real-run, and idempotency. It does NOT assert tactic columns (`tactic_motif`,
     `tactic_piece`, `tactic_confidence`) because it was written for Phase 108, before
     tactic detection existed. The existing fixture uses positions with no `pv` field.
   - What's unclear: nothing — the gap is confirmed.
   - Recommendation: Wave 0 adds one test that seeds a `pv` at `flaw_ply + 1` and asserts
     tactic_motif is populated after backfill.

2. **Expected tactic detection rate on has-PV flaws**
   - What we know: 12,916 flaws have PV at ply+1. The detector fires when the PV contains
     a recognizable motif. Based on Phase 124 validation fixtures (16 motifs with real prod
     flaws), detection rates vary by motif.
   - What's unclear: what % of the 12,916 PV-present flaws will fire (could be 30-80%).
   - Recommendation: run `--dry-run` first to get the classify output, then check the
     actual rate in the coverage report. No pre-set acceptance bar on this %; the bar is
     "NULL = honest, not skipped."

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Prod backfill will take 30-90 min for ~131k games | Prod Runbook Inputs | Low — timing; operator monitors, no correctness risk |
| A2 | Concurrent eval-drain race produces identical rows (D-03 assumption) | Common Pitfalls #4 | Very Low — same code path; race is acknowledged in D-03; worst case: one delete-then-insert races with a drain write and both write correct rows |

---

## Sources

### Primary (HIGH confidence)

- `scripts/backfill_flaws.py` — entire file read; CLI surface, targeting query, batch loop, idempotency pattern all verified. [VERIFIED: codebase]
- `app/services/flaws_service.py` — `classify_game_flaws`, `_detect_tactic_for_flaw`, `_build_flaw_record`, `FlawRecord` tactic fields, `_compute_eval_coverage` fix — all verified. [VERIFIED: codebase]
- `app/services/tactic_detector.py` — full detector dispatcher, `detect_tactic_motif`, registries, `_QUERY_SUPPRESSED_MOTIFS` (via test file). [VERIFIED: codebase]
- `app/repositories/game_flaws_repository.py` — `flaw_record_to_row` tactic field writes, `delete_flaws_for_game`, `bulk_insert_game_flaws`. [VERIFIED: codebase]
- `app/repositories/flaws_repository.py` — `fetch_game_positions_ordered`. [VERIFIED: codebase]
- `app/models/game_flaw.py` — `tactic_motif`, `tactic_piece`, `tactic_confidence` ORM columns. [VERIFIED: codebase]
- `app/models/game_position.py` — `pv` column location and semantics. [VERIFIED: codebase]
- `.planning/phases/124-schema-tactic-detector/124-VERIFICATION.md` — 10/10 truths verified, `_QUERY_SUPPRESSED_MOTIFS` location confirmed. [VERIFIED: planning docs]
- Dev DB queries — all ground truth numbers in "Dev DB Ground Truth" section. [VERIFIED: asyncpg queries against localhost:5432/flawchess]

### Secondary (MEDIUM confidence)

- `.planning/phases/125-backfill-tactic-motifs/125-CONTEXT.md` — decisions D-01..D-06. [CITED: planning docs]
- `.planning/notes/tactic-tagging-architecture.md` — prod coverage numbers (130,996 self-eval'd games on 2026-06-17). [CITED: planning docs]

### Tertiary (LOW confidence)

- None. All claims are verified from code or CONTEXT.md.

---

## Metadata

**Confidence breakdown:**
- Backfill script CLI surface: HIGH — verified line-by-line from source
- Dev DB ground truth: HIGH — verified via direct DB queries
- D-04 coverage report SQL design: HIGH — derived from verified ORM model and schema
- D-06 blast-radius analysis: HIGH — verified via git log + DB query of affected games
- Prod timing estimate: LOW — extrapolated from dev scale

**Research date:** 2026-06-18
**Valid until:** 2026-07-18 (stable domain; no external dependencies)
