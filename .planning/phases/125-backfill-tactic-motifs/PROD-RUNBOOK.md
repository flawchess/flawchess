# Prod Backfill Runbook: Tactic Motifs (Phase 125)

> **DEFERRED** — prod execution is OUTSIDE the Phase 125 completion gate (D-01).
> Phase 125 is complete on dev. Run this runbook when ready to backfill prod.

---

## Prerequisites

1. **SSH tunnel up:**
   ```bash
   bin/prod_db_tunnel.sh
   ```
   This forwards prod PostgreSQL to `localhost:15432`. Must be running before any `--db prod` command.

2. **Verify tunnel is live:**
   ```bash
   psql "$(grep DATABASE_URL_PROD .env | cut -d= -f2-)" -c "SELECT COUNT(*) FROM game_flaws;"
   ```
   Expect a row count (hundreds of thousands). Any connection error means the tunnel is not up or `.env` is missing `DATABASE_URL_PROD`.

3. **Confirm `.env` has `DATABASE_URL_PROD`:**
   ```bash
   grep DATABASE_URL_PROD .env
   ```

4. **Confirm SSH host `flawchess` is reachable:**
   ```bash
   ssh -q flawchess exit && echo "OK" || echo "UNREACHABLE"
   ```

---

## Commands (in order)

### Step 1 — Open SSH tunnel

```bash
bin/prod_db_tunnel.sh
```

### Step 2 — Dry-run smoke (no writes)

```bash
uv run python scripts/backfill_flaws.py --db prod --full-evald-only --dry-run --limit 50
```

Expected output: `Games to process: 50`, `Flaw rows counted: <N>` (non-zero), `Errors: 0`. No DB writes.
If flaw-rows count is 0 or errors > 0, stop and investigate before proceeding.

### Step 3 — Full prod backfill

```bash
uv run python scripts/backfill_flaws.py --db prod --full-evald-only
```

Expected output (see scale/posture notes below):
```
Batch size: 100 games per commit
Scope: full-eval'd games only (full_evals_completed_at IS NOT NULL)
Games to process: ~131,000
...
Backfill complete:
  Games processed: ~131,000
  Games skipped (no analysis): <some>
  Errors: 0
  Flaw rows written: <large number>
```

### Step 4 — Coverage report (verification)

```bash
uv run python scripts/coverage_report_tactic_motifs.py --db prod
```

See the Verification section below for expected output shape.

### Step 5 — Close SSH tunnel

```bash
bin/prod_db_tunnel.sh stop
```

---

## Expected Load and Posture

### Scale

- **Prod full-eval'd games:** ~131,000 (architecture note 2026-06-17; grows as the eval drain processes more games).
- **Dev rehearsal:** 11,199 games, 68,165 flaw rows written, 0 errors, ~3 min wall-clock (03:09:34 to 03:12:52).
- **Prod estimate:** ~35 min (linear extrapolation from dev: 131,000 / 11,199 * 3 min). This is an estimate; actual time depends on prod position count per game and DB I/O.

### Batching

`BACKFILL_GAMES_PER_BATCH = 100` is the named constant in `scripts/backfill_flaws.py`. Each batch commits independently (OOM-safe). Do not change this unless a prod soak shows sustained DB pressure; the dev run confirmed 100 is safe.

### Concurrency posture (D-03)

Let it rip. No throttle or pause needed. The backfill is pure CPU (no Stockfish invocation). The race with the live eval drain is benign: both paths call the same `classify_game_flaws` + `flaw_record_to_row` and produce identical rows.

---

## Verification

### Coverage report output shape

Run `uv run python scripts/coverage_report_tactic_motifs.py --db prod` after the backfill. Expected shape (based on dev run):

```
=== Tactic Motif Coverage Report ===
Scope: mistake+blunder flaws on full-eval'd games

Overall:
  Total M+B flaw rows:     <N>
  Flaws with PV at ply+1:  <has_pv>    (~18-19% expected)  <- tactic-detectable
  Flaws without PV:        <no_pv>     (~81% expected)      <- genuinely undetectable

After Backfill:
  Non-NULL tactic_motif:   <tagged>    (<% of has-PV rows>)
  PV present, no fire:     <pv_no_fire> (honest low-confidence no-fires)

By-motif (non-NULL): [table]

NULL split: no_pv_null = <N> | pv_no_fire = <N>
```

### Expected ratios

- **No-PV ratio: ~81%** of M+B flaws will have `tactic_motif = NULL` because no PV exists at `flaw_ply + 1`. This is the dev-observed ratio (55,249 / 68,165 = 81.1%). This is a ratio expectation, not a hard gate. The bar is: NULL = honest (no PV or low-confidence no-fire), not skipped.
- **By-motif shape:** fork / discovered-attack / pin / skewer should dominate; mate-family and rarer motifs in the long tail. Dev by-motif: fork 2,997 | discovered-attack 1,903 | pin 1,884 | skewer 1,439 | clearance 468 | hanging-piece 301 | back-rank-mate 289 | mate 182 | deflection 64 | and smaller counts for rarer motifs.

### NULL split interpretation

The coverage report's NULL split separates:
- `no_pv_null` — flaws where `game_positions.pv` is NULL at `flaw_ply + 1` (genuinely undetectable; no refutation line stored).
- `pv_no_fire` — flaws where a PV exists but no detector fired (honest low-confidence; precision-first design from Phase 124).

A high `no_pv_null` count (around 81%) is correct and expected on prod. The `pv_no_fire` count reflects the precision bar, not a coverage gap.

---

## Idempotency and Safety

The backfill is safe to re-run. Each game is processed via `delete_flaws_for_game` followed by `bulk_insert_game_flaws`, scoped to `(game_id, user_id)`. A partial or interrupted run can be resumed by simply re-running the full command; already-processed games will produce identical rows (no duplication, no data corruption).

There is no destructive operation beyond the per-game delete-then-insert recompute. No schema migration, no cross-user writes, no Stockfish invocation, no external API calls.

---

## Rollback

No rollback is needed — the backfill only populates three previously-NULL columns (`tactic_motif`, `tactic_piece`, `tactic_confidence`). If a re-run is needed for any reason, the idempotency guarantee (above) makes a clean re-run the correct approach. Non-tactic columns (`severity`, `tempo`, `phase`, `is_miss`, `is_lucky`, `is_reversed`, `is_squandered`, `fen`) are byte-identical after recompute (confirmed on dev via before/after diff on a fixed 50-game >9-position sample, 368 rows, empty diff).

---

## Dev Rehearsal Reference

Executed on dev 2026-06-18 (Plan 02). Full results:

| Metric | Dev Value |
|--------|-----------|
| Full-eval'd games | 11,199 |
| Flaw rows written | 68,165 |
| Errors | 0 |
| Wall-clock (backfill only) | ~3 min |
| No-PV ratio | 81.1% (55,249 / 68,165) |
| Non-NULL tactic_motif | 9,613 (74.4% of has-PV rows) |
| PV present, no fire | 3,303 |
| Idempotency | Confirmed (empty re-run diff) |
| Non-tactic column drift | None (empty D-06 diff) |

---

*Phase: 125-backfill-tactic-motifs*
*Runbook written: 2026-06-18*
*Prod execution: deferred (D-01)*
