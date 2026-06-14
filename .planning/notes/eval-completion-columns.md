# Eval & PV completion columns on `games`

The `games` table carries **four** timestamp columns that track the eval/PV state of a
game. They interact in non-obvious ways, and `full_evals_completed_at` in particular is
**not** a clean "we analyzed this with our engine" marker. This note documents what each
column means, why the design splits completion from provenance, and how to count games
correctly.

Relevant decisions: **D-116-05** (full-eval column), **D-117-06 / D-117-07**
(provenance), **D-117-12** (PV dimension).

## The four columns

| column | meaning | who sets it | source-agnostic? |
|---|---|---|---|
| `lichess_evals_at` | **Provenance.** Lichess %evals were ingested at import. | import only (lichess games) | no — lichess only |
| `evals_completed_at` | Cheap/partial eval gate (endgame-entry / depth-15). **Not** an "analyzed" gate. | `import_service.py` (mostly at import) | yes |
| `full_evals_completed_at` | **All-ply eval completion.** Source-agnostic by design. | engine drain (`eval_drain.py:449`) | yes |
| `full_pv_completed_at` | **best_move / PV capture** for all plies. | engine drain (`eval_drain.py:465`), same pass as the eval | no — engine only |

### `lichess_evals_at` — provenance
Set **only** at import when a lichess game arrives with computer %evals. `NULL` means the
evals are engine-written (or absent). This is the durable "these are lichess post-move
%evals" signal, kept separate from the oracle/flaw count columns so engine-filled games
don't blur it (D-117-06/07).

### `evals_completed_at` — partial gate, not "analyzed"
Set on ~100% of games, mostly at import time, by the import hot-lane. It marks the cheap
endgame-entry / depth-15 eval pass, **not** full-game analysis. Do not use it to mean
"this game has been analyzed."

### `full_evals_completed_at` — completion, not provenance
Marks that **every ply** has an eval, **from any source**. A lichess game imported with
full %evals genuinely is all-ply-complete, so it is correctly marked complete — this tells
the engine drain *"don't waste Stockfish here"* (the drain picks
`WHERE full_evals_completed_at IS NULL`, `eval_queue_service.py`).

> **Gotcha:** in code this column is written **only** by the engine drain. But the Phase
> 116 migration that introduced it backfilled it to mirror `evals_completed_at`. For
> lichess games `evals_completed_at` = import time, so those rows show
> `full_evals_completed_at ≈ imported_at`. That is a **backfill artifact, not a live
> import stamp.** Don't conclude the import path stamps this column.

### `full_pv_completed_at` — PV dimension
Marks that `best_move` (principal variation) was written for all plies. Written by the
engine drain in the **same pass** as the eval, so for our own work eval and PV complete
together. It is a separate column as a **backfill hedge**: PV capture was added in Phase
117, so engine games analyzed before that are eval-complete but PV-null, and a PV-only
drain can find them without redoing evals. Lichess-provenance games are PV-null by nature
(lichess ships %evals, not PVs) — which is why eval-transplant recovery gates on
`lichess_evals_at IS NULL` (it needs *our* 1M-node `best_move`, D-117-07).

## How to count correctly

**Games fully analyzed by our Stockfish** (canonical, intent-aligned):

```sql
SELECT COUNT(*) FROM games
WHERE full_evals_completed_at IS NOT NULL
  AND lichess_evals_at IS NULL        -- engine-written, not a lichess freebie
  AND full_pv_completed_at IS NOT NULL;
```

**Throughput tracking** (eval and PV land together, so PV can be dropped):

```sql
SELECT date_trunc('hour', full_evals_completed_at) AS hour, COUNT(*) AS analyzed
FROM games
WHERE full_evals_completed_at IS NOT NULL AND lichess_evals_at IS NULL
GROUP BY 1 ORDER BY 1 DESC;
```

**Backlog** (games still needing our analysis): `full_evals_completed_at IS NULL`.

### Canonical accessors (use these, don't hand-roll)

Two hybrid properties on `Game` encode the two provenance-aware predicates so callers
stop re-deriving (and mis-deriving) them. They are **not** complements — Lichess %eval
games and partially-evaled Lichess games fall in neither set:

| property | predicate | meaning |
|---|---|---|
| `Game.has_engine_full_evals` | `full_evals_completed_at IS NOT NULL AND lichess_evals_at IS NULL` | we already engine-analyzed it |
| `Game.needs_engine_full_evals` | `full_evals_completed_at IS NULL AND lichess_evals_at IS NULL` | needs our engine (the D-118-03 tier-2 enqueue window) |

`is_analyzed` (`white_blunders IS NOT NULL`) is the separate, **source-agnostic** coverage
notion (Lichess freebies count) — don't confuse it with `has_engine_full_evals`.

Do **not** use a `full_evals_completed_at - imported_at` time-gap heuristic to separate
engine work from lichess freebies. It happens to agree with the provenance gate (the
timestamps are bimodal: <5s for migration-backfilled lichess rows vs months for real
engine work), but `lichess_evals_at IS NULL` is the correct, design-aligned filter.

## Prod snapshot (2026-06-14)

| metric | value |
|---|---|
| `full_evals_completed_at` set (any source) | 32,242 |
| lichess provenance (`lichess_evals_at IS NOT NULL`) | 30,047 |
| **engine-written by us** (`lichess_evals_at IS NULL`) | **2,217** |
| backlog (`full_evals_completed_at IS NULL`) | ~569,110 |

Full-game analysis effectively began at the **pool=8 restart, 00:00 UTC 2026-06-14**
(before that the drain ran only sporadically; the large May/June completion days were
lichess import freebies, not engine work). Steady-state throughput ≈ **5.1 games/min**
(~266 positions/min). At that rate the backlog clears in roughly **77 days**.
