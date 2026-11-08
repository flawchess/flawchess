# Phase 247: Maia Stats on game_flaws (SEED-261108-zkp) - Research

**Researched:** 2026-11-08
**Domain:** Backend data pipeline: Postgres schema migration, eval-apply write path, ONNX (Maia-3) inference, multi-process backfill over an SSH tunnel
**Confidence:** HIGH for code-path findings (read this session with file:line evidence); MEDIUM for prod-scale numbers (from the seed plus dev-DB probes; prod SELECTs are listed for the orchestrator)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Locked by SEED-261108-zkp (carried forward, not re-discussed)
- **D-01: Columns.** Typed, nullable, not JSONB (NULL = not scored): `maia_played_prob` REAL,
  `maia_played_rank` SMALLINT, `maia_best_prob` REAL, `maia_best_rank` SMALLINT, `maia_second_prob` REAL,
  `maia_second_rank` SMALLINT, `maia_top_prob` REAL, `maia_effective_moves` REAL (2^H, with H the Shannon entropy in
  bits of Maia's policy over all legal moves). Rank = 1 + the number of legal moves with strictly higher Maia
  probability. "Best" = `game_positions.best_move` at the flaw ply; "second" = Stockfish's second-best move at the
  flaw ply (seed: `missed_pv_lines[0].su`; the researcher must confirm that this field is the second-best root
  move). The columns are added nullable with no default (a metadata-only ALTER on 7.6M rows).
- **D-02: No `maia_elo` column** (owner decision). The Elo is derivable via `games`. Accepted cost: a retune of the
  chess.com-to-lichess conversion means a re-run.
- **D-03: Elo** comes from `pinned_elo_for_mover` (`app/services/best_move_candidates.py`), fed symmetrically as both
  `elo_self` and `elo_oppo`, for parity with the analysis-board Maia card.
- **D-04: One inference per flaw.** A full-policy helper next to `score_move` in `app/services/maia_engine.py`
  (reuses `mask_and_softmax`) returns everything D-01 needs from one forward pass.
- **D-05: Per-game completion stamp** on `games`, mirroring `best_moves_completed_at` and its `is_maia_available()`
  guardrail: never stamp unless a Maia session was actually loaded. Stamp games with zero flaws too, so the backfill
  selector terminates.
- **D-06: Exact positions only.** The backfill rebuilds positions by replaying `games.pgn`, never from
  `game_flaws.fen` (that is `board_fen()` only; guessed castling or en-passant rights skew the legal-move softmax).
- **D-07: Out of scope:** blunder-check selection, UI and thresholds (SEED-261108-dk0); the Flaws-tab filter UI;
  Maia WDL; full-policy or top-k storage; Elo-ladder curves; Maia on non-flaw moves.

#### Re-analysis semantics
- **D-08: A Maia-loaded eval-apply re-scores every flaw** in the game on each apply (new and surviving plies alike)
  and stamps the game. One write path, never stale; the cost equals the go-forward cost.
- **D-09: Reclassification without Maia** keeps surviving values. This covers `scripts/backfill_flaws.py`,
  `scripts/opening_cache_repair.py`, and an eval-apply on a backend where `is_maia_available()` is False. Rules:
  - Surviving flaw plies keep their Maia columns, preserved by omission in the 4-way diff/upsert of
    `_classify_and_fill_oracle`, the same mechanism as `FLAW_BLOB_AND_TACTIC_COLUMNS`.
  - New flaw plies are inserted with the Maia columns NULL.
  - The game's Maia stamp is cleared (set NULL), so the re-runnable backfill re-scores the whole game, including any
    `maia_best_*` or `maia_second_*` values that went stale because Stockfish's best move changed.
  - Deleted flaw plies take their values with them (the row goes).

#### Benchmark DB
- **D-10: The script is ready for the benchmark DB; it runs there later.** The backfill script takes a `--db prod|benchmark` target and
  is tested against both. This phase runs it on prod only. The benchmark run (5.48M flaws, 812k games, about 12 h on
  9 processes, local writes) happens when the data story needs it. The benchmark DB gets the columns through the
  normal migration (`bin/benchmark_db.sh start` applies Alembic).

#### Straggler catch-up
- **D-11: The re-runnable script is the only catch-up path.** The backfill selects games with flaws and a NULL Maia stamp,
  so re-running it is idempotent and catches anything D-09 unstamped or a crash left behind. No new drain or lottery
  tier. `backfill_flaws.py` and `opening_cache_repair.py` print a one-line reminder to run the Maia backfill when they
  unstamped games.

#### Completion
- **D-12: The phase is done only after the full prod backfill.** Order: (1) go-forward scoring ships to prod (the deploy itself is the
  owner's call, so the plan pauses there for a go-ahead); (2) the orchestrator runs the full backfill against prod over
  the tunnel (detached via setsid + Monitor, not in an executor subagent); (3) a final catch-up re-run; (4) coverage
  verification on prod: at least 99% of flaws in fully evaluated games carry `maia_played_prob`, and the NULL
  remainder is explained by bucket (unreplayable PGN, missing rating, and so on).

### Claude's Discretion
- **Edge cases (defaults the owner accepted without discussion):** guest flaws are scored like everyone else (go-forward
  covers them anyway; 27.7k rows is noise). A missing Stockfish best or second move leaves only that pair NULL, while the
  played, top and effective values are still written. When the flaw ply has no second legal move, `maia_second_*` stays NULL. A game with no
  usable rating falls back to `pinned_elo_for_mover`'s own chain; if no Elo results, its flaws stay NULL. An
  unreplayable PGN, or a replay that disagrees with the stored flaw, leaves the game's flaws NULL with a counted
  reason. In every case the game is still stamped, so the selector terminates.
- Stamp column name (suggested: `games.maia_flaws_completed_at`), migration shape, and whether the selector needs a
  partial index.
- Backfill internals: process count (8-10 on the 16-core box), batch and commit size, checkpoint format, ordering
  (recently active users first, then newer games first, kept deterministic), and how prod writes are batched over the tunnel.
- Go-forward wiring: where in `apply_full_eval` the scoring runs and how it reuses the in-memory boards.

### Deferred Ideas (OUT OF SCOPE)
- Benchmark-DB backfill run: deferred to the data-story phase (the script is ready, per D-10).
- Automatic catch-up drain tier: rejected for now (D-11); revisit only if unstamped games pile up in practice.
</user_constraints>

<phase_requirements>
## Phase Requirements

No REQUIREMENTS.md IDs; the coverage contract is CONTEXT D-01..D-12 plus the discretion items.

| ID | Description | Research Support |
|----|-------------|------------------|
| D-01 | 8 typed nullable columns; rank/entropy definitions; best/second sources | Migration shape (§Pattern 1); pure stats function (§Code Examples); `su` confirmed as the second-best root move, with lane caveats (§Q1, Pitfall 1) |
| D-02 | No `maia_elo` column | Nothing to build; Elo recomputable from `games` via `pinned_elo_for_mover` |
| D-03 | Elo via `pinned_elo_for_mover`, symmetric | §Q6: never returns None; the caller must skip when the mover's raw rating is NULL |
| D-04 | One inference per flaw, full-policy helper | §Q5: `full_policy()` refactor of `score_move` (§Code Examples) |
| D-05 | Per-game stamp, guardrail, stamp zero-flaw games | `games.maia_flaws_completed_at`; guardrail = `is_maia_available()`, never row counts (§Pattern 2) |
| D-06 | Exact positions via PGN replay | Go-forward reuses `_FullPlyEvalTarget.board` (pre-push, full FEN); backfill replays `games.pgn` and checks `board.board_fen() == game_flaws.fen` |
| D-07 | Out of scope list | Respected; no UI, no WDL, no top-k |
| D-08 | Maia-loaded apply re-scores every flaw and stamps | §Q3: post-commit scorer in both live lanes (Pattern 3) |
| D-09 | Reclassify without Maia: keep survivors, NULL new, clear stamp | §Q4: Maia columns are never in `flaw_record_to_row`, so preservation is automatic in all 4 buckets; stamp clear goes inside `_classify_and_fill_oracle`. The `backfill_flaws.py` default branch is delete-then-insert and DOES lose values (Pitfall 4) |
| D-10 | `--db prod\|benchmark`, tested against both | `db_url_for_target` precedent; session-maker injection for tests; dry-run smoke on the local benchmark DB |
| D-11 | Re-runnable script is the only catch-up; reminder lines | Stamp-as-checkpoint selector; `_classify_and_fill_oracle` reports whether it cleared a stamp (Pattern 4) |
| D-12 | Full prod backfill + catch-up + ≥99% coverage by bucket | Operator runbook (§Pattern 6); coverage SQL (§Q9) |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Backend stack: FastAPI, Python 3.14, uv, SQLAlchemy 2.x async `select()` API, asyncpg, Alembic, Pydantic v2. httpx only (not relevant here).
- `routers/` hold no business logic; `services/` hold logic; `repositories/` hold DB access ("no SQL in services"). eval_apply.py already mixes SQL in; new SQL should go in `app/repositories/game_flaws_repository.py` (and a games-stamp helper) where practical.
- **Never `asyncio.gather` on the same `AsyncSession`.** Sessions must be closed before CPU-heavy work (precedent: `_build_best_move_candidates`).
- FK constraints mandatory (none needed: new columns reference nothing). Avoid native PG ENUM. SMALLINT for small ints on high-cardinality tables; REAL for probabilities. No JSONB here (asyncpg `None` → `null::jsonb` trap).
- **No magic numbers**: named constants for batch size, shard count, thread count, rank base, etc.
- **Never bare `str` for a fixed value set**: use `Literal[...]` for NULL-reason buckets, `--db` targets, lane source tags.
- **ty**: zero errors on `uv run ty check app/ tests/ scripts/`; explicit return types; `Sequence[...]` for covariant params; `# ty: ignore[rule]` with reason only where unfixable. A fresh worktree needs `uv sync --group maia-inference` or maia imports show up as unresolved.
- **Nesting depth ≤ 4** in `app/` (gated by `scripts/check_function_size.py`); about 100 logic lines per function and cognitive complexity ≤ 15 as soft targets.
- **Sentry**: `capture_exception()` in every non-trivial `except` in `app/services`/`app/routers`; never embed variables in messages (use `set_context`/`set_tag`); skip expected conditions.
- **Comment bug fixes** at the fix site.
- **Time-dependent endpoints** take `now_utc` from `dev_now_utc`. The stamp is a write-time timestamp like `best_moves_completed_at` (`datetime.now(timezone.utc)` in eval_apply), so this rule does not apply.
- **Pre-merge gate** (ruff format/check, ty ×2, function-size gate, `pytest -n auto -x`, frontend gate) before the squash-merge to `main`; CHANGELOG `[Unreleased]` entry at merge.
- **GSD scope discipline**: nothing beyond the phase. **`bin/reset_db.sh` is forbidden** without explicit permission (plans must not depend on a DB reset). **`bin/deploy.sh` is the only deploy path**, and the deploy is the owner's call (D-12).

## Summary

The phase is schema plus write-path plumbing plus a long operator run. The code facts that shape the plan:

1. **`missed_pv_lines[0].su` is the second-best root move at the flaw ply, but which search produced it depends on the lane.** Node 0 of the "missed" line is keyed at `flaw_ply` (`eval_apply.py:1578`), and its `su` is `second_uci` = `info_list[1].pv[0]` of a MultiPV-2 search on that board (`engine.py:691-698`). In the local drain that search is the same whole-game MultiPV-2 pass that produced `game_positions.best_move`, so best and second are consistent. Remote workers produce `best_move` with a MultiPV-1 pass and the blob node 0 with a **separate** MultiPV-2 search (`scripts/remote_eval_worker.py` `_eval_atomic_game`), so `su` can occasionally equal the stored `best_move`. On dev that happens for 13 of 27,261 flaws (0.05%). Treat `su == best_move` as "second unavailable" (pair NULL, counted).

2. **Preserve-by-omission is already automatic for the Maia columns.** `flaw_record_to_row` (`game_flaws_repository.py:101-127`) never emits Maia keys, so every UPDATE bucket (fresh and preserve) leaves them alone, and INSERTs leave them NULL. D-09 needs **no change to the diff/upsert**. It needs (a) a stamp clear inside `_classify_and_fill_oracle` and (b) a separate Maia write. Do **not** add Maia columns to `FLAW_BLOB_AND_TACTIC_COLUMNS` or to `flaw_record_to_row`.

3. **Inference cannot run inside `apply_full_eval` without either predicting the flaw set or holding the write transaction for about 1 s.** The authoritative flaw plies are known only after `_classify_and_fill_oracle` runs inside the write transaction (under the per-game advisory lock). Recommended: a **post-commit scorer** shared by go-forward and backfill. After the lane's commit: read the flaw inputs (short session) → infer off-session in `asyncio.to_thread` using the in-memory `targets` boards → reopen a short write session, take the per-game advisory lock, re-verify an input fingerprint, write the 8 columns, stamp. One implementation serves the drain, atomic-submit, (recommended) tier-4 blob submit, and the backfill script.

**Primary recommendation:** Add the columns and stamp in one Alembic revision (no index). Add a pure `compute_maia_flaw_stats()` and `maia_engine.full_policy()`. Clear the stamp in `_classify_and_fill_oracle`. Add one shared scorer module used post-commit by the live lanes and by a sharded (`md5(id) % N`), stamp-checkpointed, multi-process backfill script with single-threaded ORT sessions.

## Answers to the Orchestrator's Questions (with evidence)

### Q1. Is `missed_pv_lines[0].su` the second-best root move at the flaw ply?

**Yes, with a lane caveat.** Evidence:

- Missed-line node 0 is the flaw-ply position: `node0_ply = flaw_ply if line == "missed" else flaw_ply + 1` [VERIFIED: app/services/eval_apply.py:1578], and node 0 takes its second-best from `second_best_map.get(node0_ply)` with `su: str = su_raw if su_raw is not None else ""` [VERIFIED: eval_apply.py:1580-1583].
- `second_uci` is the second PV's first move: `if len(info_list) > 1: ... second_pv = info_list[1].get("pv"); second_uci: str = second_pv[0].uci() if second_pv else ""` / `else: ... second_uci = ""` [VERIFIED: app/services/engine.py:691-698]. `""` = single legal move (and also "engine gave no second PV").
- PvNode shape: `b: int | None`, `bm: int | None`, `s: int | None`, `sm: int | None`, `su: str` [VERIFIED: app/services/forcing_line_gate.py:112-116]. **There is no best-move UCI in the blob.** Node 0's `b`/`bm`/`s`/`sm` are evals, not moves.

Per lane:

| Lane | Where `best_move` comes from | Where missed node 0 `su` comes from | Consistent? |
|---|---|---|---|
| Local drain (`_full_drain_tick`) | whole-game `evaluate_nodes_multipv2` pass (`eval_drain.py:1438-1478`) | same pass, `second_best_map[t.ply]` (`eval_drain.py:1474-1478`); dedup-transplanted opening plies get a fresh search (`_fill_engine_game_flaw_second_best`, `eval_drain.py:1022-1061`) | Yes (dedup plies: best from the cache, second from a fresh search, can differ) |
| Remote atomic-submit | worker's MultiPV-1 `_eval_positions` | worker's separate MultiPV-2 at blob token `"{flaw}:missed:0"` (`remote_eval_worker.py` `_eval_atomic_game`, `_build_blob_walk_targets`); assembled by `_assemble_one_line_blob` (`eval_apply.py:1963-2001`) | Usually; two independent searches |
| Tier-4 blob lease/submit | stored `best_move` from the earlier pass | worker MultiPV-2 at the leased node 0 FEN (`_build_flaw_blob_lease_positions`, `eval_apply.py:1918-1936`) | Usually |
| Lichess-eval games | our engine's best_move (full MultiPV-2 pass is also run on lichess games, `eval_drain.py:1388-1394`) | same as the lane above | As above |

When `su` is absent: `missed_pv_lines IS NULL` (flaw not yet blobbed, pending tier-4); `[]` (sentinel: un-walkable line, e.g. NULL PV at the flaw ply in the atomic/tier-4 lanes, `eval_apply.py:1925-1930`); `su == ""` (single legal move, or no second PV). In the drain lane node 0 always exists when the flaw ply is a target, because `_walk_pv_boards` always returns at least the start board.

Dev DB probe this session (69,671 flaws): `missed_pv_lines` NULL 39,610 · `[]` 559 · `su=''` 2,241 · `su` present 27,261. Dev under-runs tier-4, so its NULL share is not representative. The seed reports prod non-NULL blobs for 7,600,177 of 7,605,748 flaws [CITED: SEED-261108-zkp]. Collision probe (dev): `su == game_positions.best_move` for **13 of 27,261** flaws [VERIFIED: dev DB query this session].

**Recommendation:** source "second" from `missed_pv_lines->0->>'su'` read from the DB **after** the apply commits, in both go-forward and backfill. That is exactly what was persisted, so the two paths agree by construction. Treat `su` as unavailable when it is `''`, absent, not a legal move in the policy, or equal to `best_uci` (reason `second_equals_best`). Only the second pair goes NULL.

### Q2. Every path that writes game_flaws rows, and what each does

Grep of all writers (`bulk_insert_game_flaws`, `delete_flaws_for_game`, `delete_flaw_plies`, `bulk_update_game_flaw_rows`, `bulk_update_tactic_tags`, `_batch_update_flaw_pv_lines`, `_classify_and_fill_oracle`) [VERIFIED: grep this session]:

| Path | Code | Changes flaw set / best_move? | Maia loaded in that process? | Action |
|---|---|---|---|---|
| Local full drain | `eval_drain._full_drain_tick` → `apply_full_eval` → `_classify_and_fill_oracle` (`eval_apply.py:2949`) | yes | prod backend yes (Dockerfile syncs `maia-inference`); tests no unless faked | classify clears stamp; **post-commit scorer** re-scores + stamps (D-08) |
| Remote atomic-submit | `eval_remote._apply_atomic_submit` → `apply_full_eval` (`eval_remote.py:1424-1459`) | yes | backend applies it, so yes | same as drain |
| Tier-3 lichess branch (b) / resweep re-arms | go through `_full_drain_tick`/atomic | yes | yes | covered by the two rows above |
| Tier-4b best-move (drain + `/bestmove-submit`) | `_tier4b_minimal_drain_tick`, `_apply_bestmove_submit` | no (writes `game_best_moves` only; "`game_flaws` is never read or written", `eval_apply.py:2563-2565`) | yes | **none** |
| Tier-4 flaw-blob lease/submit | `eval_remote.py:889, 915, 1075` (`_batch_update_flaw_pv_lines`, `bulk_update_tactic_tags`) | no flaw-set change, but **fills `missed_pv_lines` → `su` becomes available** | backend, yes | **recommended:** run the post-commit scorer for that game (otherwise `maia_second_*` stays NULL forever on a stamped game). See Open Question 1 |
| Entry lane (import-time) | `eval_entry._classify_and_insert_flaws` → `bulk_insert_game_flaws` ON CONFLICT DO NOTHING (`eval_entry.py:593`) | inserts new plies only, for games with `evals_completed_at IS NULL` (`eval_entry.py:410-411`) | n/a | none needed: the game's stamp is NULL then (pre-full-eval) |
| `scripts/backfill_flaws.py` default branch | `delete_flaws_for_game` + `bulk_insert_game_flaws` (`backfill_flaws.py:393-402`) | yes, **delete-then-insert wipes Maia values** | no | clear stamp per written game + D-11 reminder |
| `backfill_flaws.py --oracle-gap` | `_classify_and_fill_oracle` (`backfill_flaws.py:182`) | yes | no | clear-in-classify covers it; reminder |
| `backfill_flaws.py --from-repair-table` → `opening_cache_repair.run_rederive` | `_classify_and_fill_oracle(session, game_id, {}, ...)` (`opening_cache_repair.py:2040`) | yes; and the earlier `propagate` stage rewrites `game_positions.best_move` in bulk (`opening_cache_repair.py:1373-1380`) without classifying | no | clear-in-classify covers rederived games; reminder. Edge: a propagated game that rederive finds `GameNotAnalyzed` never reaches classify (`_rederive_reclassify_game` returns None, `opening_cache_repair.py:2034-2036`). Clear the stamp there too |
| `scripts/retag_flaws.py` | `bulk_update_tactic_tags` only (`retag_flaws.py:849`) | no | no | none |
| Game deletion | FK `ondelete=CASCADE` | rows go | n/a | none |

### Q3. Where scoring runs, board reuse, session discipline, ply convention

**Ply convention** [VERIFIED: app/services/flaws_service.py:781-786, 835-844]: a `game_flaws` row at ply N is the move played **from** the position after N half-moves. `fen = board_fen()` of `fen_map[n]`, and `move_san = positions[n].move_san`. `game_positions.best_move` at row N is the best move **from** position N, decision-keyed and **not** shifted: "best_move stays decision-ply-keyed (best move FROM row k's position), so it is NOT shifted" [VERIFIED: eval_apply.py:689-690]. Only eval_cp/eval_mate are post-move shifted (row P = eval of P+1, `_post_move_eval`, `eval_apply.py:410-422`). So **all three Maia inputs (played, best, second) are keyed at the same ply N and the same pre-move board.**

**In-memory boards:** `_FullPlyEvalTarget.board` is a `board.copy()` of the **pre-push** board at that ply, with full castling/ep state from a real PGN walk, and `move_uci = node.move.uci()` is the played move [VERIFIED: eval_apply.py:290-303]. `t.board.fen()` is what `score_move` already receives (`eval_apply.py:2379`). Both live lanes build `targets` with `_collect_full_ply_targets` (drain `eval_drain.py:1384`, atomic `eval_remote.py:1275`). It returns `[]` for invalid custom roots (`eval_apply.py:257-268`).

**Why not inside `apply_full_eval`:** the authoritative flaw plies exist only after `_classify_and_fill_oracle` runs in the write session (`eval_apply.py:2949-2955`, under `pg_advisory_xact_lock`, `:2934-2937`). Running about 7.5 inferences (prod ~150 ms each per the `eval_apply.py:2214-2218` comment, so ~1.1 s) inside that transaction holds a pooled connection (pool 10+10, `app/core/database.py:23-24`) plus row locks on every submit. The precedent `_build_best_move_candidates` explicitly reads metadata in a short session "CLOSED before any Maia inference" and writes later (`eval_apply.py:2167-2174`). The alternative, pre-classifying before the write session (as `_build_flaw_multipv2_blobs` does via `_classify_with_overlay`, `eval_apply.py:1615-1621`), **mispredicts lichess-eval games**: that overlay replaces lichess %evals with our engine evals, while the write path preserves lichess evals (`eval_apply.py:738-760`). It also needs a "did prediction cover the authoritative set" check.

**Recommended wiring (post-commit scorer, Pattern 3):**
- Drain: in `_full_drain_tick`, after `outcome = await commit_unless_game_deleted(...)` (`eval_drain.py:1570`) and after the `outcome is None` early return, call `await score_game_flaws_after_apply(async_session_maker, game_id, targets)`. Do this before the `if not stamp_complete: return False` at `:1578`, so D-08's "each apply" holds. The cost of Path-B re-scoring is small.
- Atomic: in `_apply_atomic_submit` after the `outcome is None` 404 branch (`eval_remote.py:1461-1467`), same call with the router module's `async_session_maker`.
- Pass the **lane module's** `async_session_maker` as a parameter. Tests monkeypatch it per module (`apply_full_eval` docstring, `eval_apply.py:2862-2866`).
- Inference inside the scorer runs in `asyncio.to_thread` (precedent `eval_apply.py:2219`; "onnxruntime releases the GIL, and InferenceSession.run is safe to call concurrently from several threads").
- Exceptions: catch, `sentry_sdk.set_context("maia_flaws", {"game_id": ...})`, `set_tag("source", lane)`, `capture_exception()`, and **leave the game unstamped** (the eval commit already happened, so the backfill is the catch-up). Never stamp after a failed pass.

### Q4. Preserve-by-omission mechanics

- `flaw_record_to_row` returns only: `user_id, game_id, ply, severity, tempo, phase, is_miss, is_lucky, is_reversed, is_squandered, fen, allowed_tactic_motif, allowed_tactic_piece, allowed_tactic_confidence, allowed_tactic_depth, missed_tactic_motif, missed_tactic_piece, missed_tactic_confidence, missed_tactic_depth` [VERIFIED: app/repositories/game_flaws_repository.py:101-127].
- `FLAW_BLOB_AND_TACTIC_COLUMNS = ("allowed_pv_lines", "missed_pv_lines") + TACTIC_TAG_COLUMNS` [VERIFIED: game_flaws_repository.py:167-170]. It only strips keys **from rows produced by `flaw_record_to_row`** for the preserve bucket (`eval_apply.py:1281-1285`).
- `bulk_update_game_flaw_rows` = ORM bulk-update-by-PK; "A column absent from a dict is left untouched" [VERIFIED: game_flaws_repository.py:246-264].
- Inserts use `pg_insert(GameFlaw).values(rows).on_conflict_do_nothing()` (`:146`). Absent Maia keys → column default NULL.

**Consequence:** with no Maia keys in `flaw_record_to_row`, surviving rows in **both** update buckets keep their Maia values, new rows get NULL, and deleted rows go. That is D-09 exactly, with zero diff/upsert change. The Maia write is a **separate** PK-keyed update helper (e.g. `bulk_update_flaw_maia_stats(session, rows)` reusing `update(GameFlaw)` executemany, all dicts carrying the same 11 keys = 3 PK + 8 Maia) plus a `MAIA_FLAW_COLUMNS` tuple as the single source of truth. Writing NULL into REAL/SMALLINT binds a real SQL NULL; the JSONB trap does not apply.

**Stale comment** (owner memory): the comment at `eval_apply.py:~1327` is now the "Shouldn't happen... be defensive" line inside `refresh_game_flaw_counts_and_accuracy`. The diff/upsert docstring (`eval_apply.py:1007-1049`) correctly says "not delete-then-insert". I did not find a remaining stale "delete-then-insert" claim in eval_apply. `backfill_flaws.py`'s **default branch really is** delete-then-insert (`backfill_flaws.py:391-402`), by design.

### Q5. maia_engine internals

- Session: module-global `_session: onnxruntime.InferenceSession | None` (`maia_engine.py:68`). `start_maia()` is async and idempotent, defers `import onnxruntime`, and checks the model SHA-256 `"405bf76c15727dad8728b352c06a8f3c1b80fb2760e8d666b32485c63d75b856"` (`:58`). It creates `onnxruntime.InferenceSession(str(_MODEL_PATH), providers=["CPUExecutionProvider"])` with **no SessionOptions** (`:110-112`), so ORT default threading applies. `stop_maia()` sets `_session = None` (`:144-148`). `is_maia_available()` returns `_session is not None` (`:131-141`) [VERIFIED: app/services/maia_engine.py].
- `score_move(fen, elo, played_uci)`: encodes `encode_board(fen)` → float32 `(1, 64, 12)`; `elo_in = np.array([elo_to_input(elo)])`; feeds `{"tokens", "elo_self": elo_in, "elo_oppo": elo_in}` (symmetric); runs `["logits_move"]`; `probs = mask_and_softmax(policy.tolist(), fen)`; returns `probs.get(played_uci)` [VERIFIED: maia_engine.py:151-175].
- `mask_and_softmax(policy, fen)` builds `chess.Board(fen)`, iterates `board.legal_moves`, mirrors squares when Black is to move, indexes the 4352-vocab, and does a stable softmax in Python doubles; returns `{uci: prob}` over **legal moves only** [VERIFIED: app/services/maia_encoding.py:168-203]. It depends on the full FEN (side to move, castling, ep). That is why D-06 forbids `game_flaws.fen`.
- **Threads:** ORT `intra_op_num_threads = 0` (default) = "Number of physical CPU Cores" [CITED: onnxruntime.ai/docs/performance/tune-performance/threading.html]. Measured this session on the 16-core dev box: **80.5 ms/position at 1 thread vs 95.3 ms at the default** [VERIFIED: scratch benchmark this session]. This supports the seed's "scale by processes". A backfill with 9 processes on default threads would oversubscribe the cores, so `start_maia` needs an optional `intra_op_num_threads` argument (default None = unchanged backend behavior); the backfill passes 1.
- Multi-process: each process has its own module global, so it needs its own `start_maia()` (spawn context). The model is about 43.6 MiB on disk.
- Tests already fake presence with `monkeypatch.setattr(maia_engine, "_session", object())` and mock `eval_apply_module.score_move` (`tests/test_eval_worker_endpoints.py:6351-6355`, `tests/services/test_full_eval_drain.py:2682, 2771, 2846, 2948`). **`test_non_tier4b_claim_still_takes_full_path` (`test_full_eval_drain.py:2846`) runs the full drain with a sentinel `object()` session**, so a new `full_policy` call would hit `object().run` → AttributeError. The plan must (a) make the scorer's inference function a module attribute that tests can monkeypatch, and (b) keep the fail-safe "exception → no stamp".

### Q6. pinned_elo_for_mover

Signature `pinned_elo_for_mover(*, raw_rating: int, platform: Platform, time_control_bucket: TimeControlBucket | None, is_correspondence: bool) -> float` [VERIFIED: app/services/best_move_candidates.py:79-122]. Chain: `platform == "flawchess"` → raw; `time_control_bucket is None` → raw; else `normalize_to_lichess_blitz(...)`. If that returns None (correspondence, or out of the table range), fall back to raw. Then `clamp_to_ladder_bounds` to [600, 2600] (`maia_encoding.py:62-63, 143-146`). **It never returns None, and it requires a non-None int.** The "no Elo" case is the caller's: the precedent skips when `raw_rating is None` (`eval_apply.py:2369-2372`). Inputs come from `games.white_rating/black_rating/platform/time_control_bucket/time_control_str` via `_fetch_rating_metadata` (`eval_apply.py:2304-2329`) and `is_correspondence_time_control` (`app/services/normalization.py:34-47`). `Platform = Literal["chess.com", "lichess", "flawchess", "pgn"]` [VERIFIED: app/schemas/normalization.py:15]. `"pgn"` falls through to the lichess branch of `normalize_to_lichess_blitz` (`chesscom_to_lichess.py:358-372`), which is parity with whatever the board does today.

**Mover color:** the precedent uses ply parity (`mover_color_for_ply`, `best_move_candidates.py:70-73`). Prefer `board.turn` of the replayed/target board. It is correct for custom-FEN games that start with Black to move, which parity gets wrong. Dev probe: 197 of 69,671 flaws have a NULL mover rating by parity [VERIFIED: dev DB].

### Q7. Migration shape

- Current head: `e2a7c4f9b244` (`alembic heads` output; `revision: str = "e2a7c4f9b244"` at `alembic/versions/20261102_120000_e2a7c4f9b244_phase_244_sr_ladder_due_date_push.py:58`) [VERIFIED].
- Prior art for a nullable stamp: `op.add_column("games", sa.Column("best_moves_completed_at", sa.DateTime(timezone=True), nullable=True))` [VERIFIED: alembic/versions/20260717_035706_939c3d99868d_phase_176_best_moves_completed_at.py]. Prior art for REAL: `sa.Column("maia_prob", sa.REAL(), nullable=False)` (`20260716_125231_903b54b77161`), model `from sqlalchemy.dialects.postgresql import REAL` (`app/models/game_best_move.py:19,40`).
- `ADD COLUMN` with no default is metadata-only (no rewrite) [CITED: postgresql.org/docs/current/sql-altertable.html]. All environments run Postgres 18.6 (`docker-compose*.yml`). It takes a brief ACCESS EXCLUSIVE lock; migrations run at container start against a quiescent backend (`20260916_120000_c3a9e1f70003...py:24-26` states this convention and why indexes are non-concurrent).
- **No CHECK constraints.** `ADD CONSTRAINT ... CHECK` validates with a full scan under ACCESS EXCLUSIVE. Ranks/probabilities are not enum-like, so the CLAUDE.md CHECK rule (for enum SMALLINTs) does not apply.
- **No partial index on the stamp.** Reasons: (1) at backfill start every game is NULL, so the index would cover the whole table; (2) Postgres blocks HOT updates when any indexed column, **including partial-index predicate columns**, changes [ASSUMED: PG internals, RelationGetIndexAttrBitmap includes predicate attrs], so an index on `maia_flaws_completed_at` would make all ~1M stamp updates non-HOT and bloat every `games` index; (3) the selector runs a few times by hand; a seq scan of `games` plus a semi-join on `ix_game_flaws_game_id` takes seconds. `games` already has `toast_tuple_target=256` [VERIFIED: dev pg_class.reloptions], so its main tuples are small.
- `game_flaws` existing indexes: PK `(user_id, game_id, ply)`, `ix_game_flaws_game_id`, `ix_game_flaws_user_severity`, partial `ix_game_flaws_blob_backfill (game_id) WHERE allowed_pv_lines IS NULL` [VERIFIED: dev pg_indexes]. The Maia columns are unindexed, so updates are HOT-eligible when a page has room.

### Q8. Backfill prior art

- `--db` + `db_url_for_target(target)` with `DbTarget = Literal["dev", "test", "prod", "benchmark"]` [VERIFIED: app/core/config.py:217-236]; tunnel on `localhost:15432` (`bin/prod_db_tunnel.sh:5,9`); injectable `session_maker` for tests (`backfill_flaws.py:245,281-284`); Sentry init if `SENTRY_DSN` (`:278-279`); per-game advisory lock `_game_write_lock_key` reused by scripts (`backfill_flaws.py:168-171`).
- `retag_flaws.py`: keyset paging, `ProcessPoolExecutor(mp_context=mp.get_context("spawn"))` CPU pool with the DB in the parent (`retag_flaws.py:940-945`), change-only executemany updates, `--throttle-ms`. The 2026-10 prod retag wrote 4.76M rows in 3h17m over the tunnel [CITED: CONTEXT/owner memory].
- **Hash-residue sharding** precedent: `('x' || substr(md5(id::text || :seed), 1, 8))::bit(32)::bigint AS h ... WHERE h % CAST(:num_shards AS bigint) = CAST(:shard AS bigint)` [VERIFIED: scripts/engine_disagreement_study/seed153_scan_sample.py:129-136]. Its docstring records the rank-window double-scan/skip bug (`:29-43`).
- **ES-lottery priority** to mirror (deterministically): user weight from `recency_col_sql="u.last_activity"` (`eval_queue_service.py:665, 810, 896`); game weight from TC multiplier `GAME_TC_WEIGHTS` and recency `g.played_at` / `g.full_pv_completed_at` (`:689, 913`). Deterministic equivalent: `ORDER BY u.last_activity DESC NULLS LAST, g.played_at DESC NULLS LAST, g.id DESC`. Drop the TC weighting: it is a lottery fairness device, not "priority".

### Q9. Coverage verification

Denominator per `.planning/notes/eval-completion-columns.md`: "flaws in fully evaluated games" = `games.full_evals_completed_at IS NOT NULL` (source-agnostic, includes lichess %eval games). Do not use `has_engine_full_evals`; that would drop the lichess games that dominate. See §Pattern 6 for the SQL.

### Q10. Testing strategy

- Real ONNX is available locally (`onnxruntime 1.29.0`, numpy 2.5.2 [VERIFIED: uv run this session]) and in CI (`uv sync --locked --group maia-inference`, `.github/workflows/ci.yml:50`). Real-session tests guard with `pytest.importorskip("onnxruntime")` (`tests/services/test_maia_engine.py`, `test_maia_parity.py`). A parity corpus exists at `tests/fixtures/maia_parity/corpus.json`.
- Eval-apply tests fake Maia presence with the `_session = object()` sentinel and mock the scorer. Write-path goldens dump an **explicit** column list (`tests/services/write_path_golden_scenarios.py:61-80`), so new columns do not break them.
- Isolation gotchas: the tier-3 eval lottery is GLOBAL+random, so every non-guest `Game` insert needs `finally:` cleanup; use a unique module-level `_TEST_USER_ID` (grep for collisions; precedent `108060`, `99_400`). **The backfill selector is global too**, so tests must scope it with `--user-id` (or an explicit `game_ids` filter) or they will pick up other tests' games under `-n auto`.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Maia columns + stamp | Database / Storage | — | Typed nullable columns on `game_flaws`/`games`; Alembic |
| Policy inference (`full_policy`) | API / Backend (maia_engine) | — | Process-global ORT session; CPU in a worker thread |
| Stats derivation (rank/entropy/top) | API / Backend (pure module) | — | Pure function, no I/O, testable without onnx |
| Go-forward scoring | API / Backend (eval lanes post-commit) | Database | Runs after the drain/atomic commit; session-free inference |
| Reclassify unstamp (D-09) | API / Backend (`_classify_and_fill_oracle`) | Database | One choke point for every reclassifier |
| Backfill | Operator script (dev box) | Database (prod via tunnel) | Multi-process CPU locally, DB writes over the tunnel |
| Coverage verification | Database (SQL) | Operator | Read-only SELECT by the orchestrator |

No browser/frontend tier involvement.

## Standard Stack

### Core (all already in the repo, nothing new to install)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| onnxruntime | 1.29.0 (pinned exactly, `pyproject.toml:64`) | Maia-3 inference | Pinned after a segfault history; never bump here (owner memory: no ORT bump) |
| numpy | 2.5.2 (group `maia-inference`) | Tensor plumbing | Deferred import, as in `score_move` |
| python-chess | 1.11.x | PGN replay, legal moves | Project standard |
| SQLAlchemy async + asyncpg | 2.x | Writes | Project standard |
| Alembic | existing | Migration | Project standard |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Post-commit scorer | In-transaction scoring with pre-classify prediction | Atomic, but mispredicts lichess-eval games and needs a subset check, or holds the txn for ~1 s/submit |
| N independent shard processes | Parent-DB + ProcessPool (retag pattern) | The pool pattern keeps one DB connection but needs read/compute/write pipelining in the parent. Shards are simpler, overlap I/O naturally, and use md5 sharding, which CONTEXT requires |
| ORM bulk-update-by-PK | `UPDATE ... FROM (VALUES ...)` with CASTs | VALUES saves a little over the tunnel; ORM executemany is the proven 4.76M-row precedent and an existing helper |

**Installation:** none. `uv sync --group maia-inference` in any fresh worktree.

## Package Legitimacy Audit

No external packages are installed by this phase. All dependencies (onnxruntime 1.29.0, numpy, python-chess, SQLAlchemy, asyncpg, Alembic) are already locked in `uv.lock`.

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
                 GO-FORWARD (prod backend, Maia loaded)
 claim/lease ──► engine pass (drain) / worker submit (atomic)
                      │ targets[] (pre-push boards, move_uci)
                      ▼
        write session: apply_full_eval  [advisory lock]
          evals → _classify_and_fill_oracle (4-way diff/upsert,
                   Maia cols untouched, CLEAR maia_flaws_completed_at)
          → completion decision → COMMIT
                      │
                      ▼  (if is_maia_available())
        score_game_flaws_after_apply(session_maker, game_id, targets)
          1. short read: flaw plies + fen + missed su, best_move@ply, ratings
          2. to_thread: full_policy(board.fen(), elo) per flaw → stats
          3. short write [advisory lock]: verify fingerprint unchanged
             → UPDATE 8 cols by PK → stamp now()  → COMMIT
          (any exception → Sentry, leave unstamped)

  tier-4 /flaw-blob-submit COMMIT ──► (recommended) same scorer, boards from PGN replay

                 NO-MAIA RECLASSIFIERS
  backfill_flaws.py (default: delete+insert → clear stamp) ─┐
  backfill_flaws.py --oracle-gap / --from-repair-table ─────┼─► stamp NULL ─► reminder line
  opening_cache_repair rederive (via _classify_and_fill_oracle)┘

                 BACKFILL (dev box → prod tunnel)
  parent: select games WHERE stamp IS NULL AND EXISTS flaws, per shard
          (md5(id) % N), ORDER BY last_activity, played_at, id DESC
     ├─ shard proc 0 (own ORT session, 1 thread, own DB conn) ─┐
     ├─ ...                                                    ├─► batch: read inputs → replay PGN
     └─ shard proc N-1                                         ┘    → score → locked verify+write+stamp → commit
  stamp = checkpoint; re-run = catch-up; per-shard JSON counters → report
```

### Recommended Project Structure
```
app/services/maia_engine.py          # + full_policy(fen, elo); score_move delegates; start_maia(intra_op_num_threads=None)
app/services/maia_flaw_stats.py      # NEW pure: MaiaFlawStats, compute_maia_flaw_stats(), reason Literal
app/services/maia_flaw_scoring.py    # NEW: load inputs, score (sync, to_thread), guarded write, go-forward wrapper
app/repositories/game_flaws_repository.py  # + MAIA_FLAW_COLUMNS, bulk_update_flaw_maia_stats(), stamp set/clear helpers
app/models/game_flaw.py / game.py    # + 8 columns / + maia_flaws_completed_at
alembic/versions/2026MMDD_..._phase_247_maia_flaw_stats.py
scripts/backfill_maia_flaws.py       # NEW sharded backfill
tests/services/test_maia_flaw_stats.py, test_maia_flaw_scoring.py, tests/scripts/test_backfill_maia_flaws.py
```

### Pattern 1: Migration (one revision)
```python
# down_revision = "e2a7c4f9b244"
def upgrade() -> None:
    for name, type_ in (
        ("maia_played_prob", sa.REAL()), ("maia_played_rank", sa.SmallInteger()),
        ("maia_best_prob", sa.REAL()), ("maia_best_rank", sa.SmallInteger()),
        ("maia_second_prob", sa.REAL()), ("maia_second_rank", sa.SmallInteger()),
        ("maia_top_prob", sa.REAL()), ("maia_effective_moves", sa.REAL()),
    ):
        op.add_column("game_flaws", sa.Column(name, type_, nullable=True))
    op.add_column("games", sa.Column("maia_flaws_completed_at", sa.DateTime(timezone=True), nullable=True))
# downgrade: drop in reverse. No data backfill, no index.
```

### Pattern 2: Guardrail
Stamp only when `maia_engine.is_maia_available()` is True **and** the pass completed without exception. Never infer from the row count (the `_build_best_move_candidates` precedent at `eval_apply.py:2963-2967`). The backfill aborts at startup if `start_maia()` did not load a session.

### Pattern 3: Post-commit guarded write (shared by go-forward and backfill)
Inside one write transaction per batch (go-forward: a batch of 1):
1. `pg_advisory_xact_lock(_game_write_lock_key(gid))` for each game, in ascending id order (precedent: `backfill_flaws.py:168-171`, `eval_remote.py:1055-1058`). Live writers take a single lock per transaction, so no deadlock cycle is possible.
2. Re-read the fingerprint `{(ply, fen, best_move, su)}` per game and compare with what was scored. On mismatch, skip the game (leave it unstamped). Precedent for the in-lock re-read: `eval_remote.py:1044-1070` (FLAWCHESS-8D).
3. Backfill only: also require `maia_flaws_completed_at IS NULL` (go-forward always overwrites).
4. `bulk_update_flaw_maia_stats` (PK + 8 cols), then `UPDATE games SET maia_flaws_completed_at = now() WHERE id = ANY(:ids)`.

Keep the batch at ≤ 50 games: each advisory lock takes a shared lock-table slot.

### Pattern 4: Unstamp inside `_classify_and_fill_oracle`
After `_diff_upsert_flaw_rows` (i.e. only when classification actually wrote), run `UPDATE games SET maia_flaws_completed_at = NULL WHERE id = :gid AND maia_flaws_completed_at IS NOT NULL RETURNING id`. Change the function's return value from `None` to a small result (e.g. `maia_unstamped: bool`; the "not analyzed" early returns give False) so scripts can count and print the D-11 reminder. Callers: `eval_apply.py:2949`, `backfill_flaws.py:182`, `opening_cache_repair.py:2040`. Also add an explicit clear in the `backfill_flaws.py` default branch (after delete+insert) and in `_rederive_reclassify_game` when it returns None for a game whose best_move was propagated.

### Pattern 5: Backfill process model
- `--db {dev,benchmark,prod}` (adding `dev` follows the `backfill_flaws.py` precedent; flag this to the owner, since D-10 names only prod|benchmark), `--workers N` (default 9), `--num-shards`/`--shard` (run a single shard by hand), `--user-id`, `--limit`, `--batch-games` (default ~50), `--dry-run`, optional `--throttle-ms`.
- Each shard process: `asyncio.run(...)`, its own `create_async_engine(url, pool_size=1, max_overflow=0, pool_pre_ping=True)`, `await start_maia(intra_op_num_threads=1)`, abort if `not is_maia_available()`.
- Shard membership: `('x' || substr(md5(g.id::text), 1, 8))::bit(32)::bigint % :num_shards = :shard`.
- Ordering snapshot at shard start (ids only, about 110k per shard on prod); iterate in batches; each batch re-reads its inputs.
- Per game: `chess.pgn.read_game`, walk the mainline collecting `board.copy()` + `move.uci()` at flaw plies; verify `board.board_fen() == flaw.fen`; mover = `board.turn`; elo via `pinned_elo_for_mover` or the `no_rating` reason; `full_policy` once per flaw; `compute_maia_flaw_stats`.
- **The checkpoint is the DB stamp.** Also write a per-shard JSON (`reports/maia-flaws-backfill/{db}-{UTC timestamp}-shard{k}.json`) with counters by reason, games/flaws done, and rate. Timestamped names avoid the same-day report collision (owner memory).
- Logging: `print(..., flush=True)` (Python 3.14 logs can look frozen behind a 128 KiB buffer). Monitor progress through the DB stamped count, not the log.

### Pattern 6: Operator runbook (orchestrator, not an executor)
1. Owner go-ahead → deploy (`bin/deploy.sh` / `/deploy`), which applies the migration on prod. Verify the backend startup log shows "Maia ONNX session loaded" (`maia_engine.py:128`).
2. `bin/prod_db_tunnel.sh`; `setsid nohup uv run python scripts/backfill_maia_flaws.py --db prod --workers 9 > logs/... 2>&1 &`; watch with Monitor and an until-loop on `SELECT count(*) FROM games WHERE maia_flaws_completed_at IS NOT NULL`. Bash caps foreground commands at 10 min.
3. Catch-up re-run (same command; picks up only NULL-stamped games with flaws).
4. Coverage SQL:
```sql
WITH f AS (
  SELECT f.maia_played_prob, f.maia_best_prob, f.maia_second_prob, g.maia_flaws_completed_at AS stamp,
         CASE WHEN f.ply % 2 = 0 THEN g.white_rating ELSE g.black_rating END AS mover_rating
  FROM game_flaws f JOIN games g ON g.id = f.game_id
  WHERE g.full_evals_completed_at IS NOT NULL)
SELECT count(*) AS denom,
  count(*) FILTER (WHERE maia_played_prob IS NOT NULL) AS scored,
  round(100.0 * count(*) FILTER (WHERE maia_played_prob IS NOT NULL) / NULLIF(count(*),0), 3) AS pct_scored,
  count(*) FILTER (WHERE maia_played_prob IS NULL AND stamp IS NULL) AS null_unstamped,
  count(*) FILTER (WHERE maia_played_prob IS NULL AND stamp IS NOT NULL AND mover_rating IS NULL) AS null_no_rating,
  count(*) FILTER (WHERE maia_played_prob IS NULL AND stamp IS NOT NULL AND mover_rating IS NOT NULL) AS null_other,
  count(*) FILTER (WHERE maia_played_prob IS NOT NULL AND maia_best_prob IS NULL) AS best_pair_null,
  count(*) FILTER (WHERE maia_played_prob IS NOT NULL AND maia_second_prob IS NULL) AS second_pair_null
FROM f;
```
Split `null_other` using the script's reason counters (`pgn_unparseable`, `fen_mismatch`, `ply_beyond_mainline`, `played_not_legal`). The parity-based `mover_rating` misattributes custom-FEN Black-first games; that is negligible. Then `VACUUM (ANALYZE) game_flaws;` (7.6M updated rows leave dead tuples), and check `pg_stat_user_tables.n_dead_tup`.

### Anti-Patterns to Avoid
- **Adding Maia keys to `flaw_record_to_row` or `FLAW_BLOB_AND_TACTIC_COLUMNS`.** That would make fresh-bucket updates write NULL over values and break D-09.
- **Scoring from `game_flaws.fen`**: no castling/ep, which gives a wrong legal-move set (D-06).
- **Stamping on an empty result** or after an exception (D-05).
- **Rank-window sharding** (`ROW_NUMBER() OVER ...`) on a growing table, which double-scans and skips.
- **Running Maia inside the write transaction**, or `asyncio.gather` on one session.
- **Default ORT threads in multi-process runs** (oversubscription; measured slower even single-process).
- **Running the full prod backfill inside an executor subagent** (the agent dies, owner memory). The orchestrator runs it detached.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Legal-move softmax + vocab mirroring | new mask logic | `maia_encoding.mask_and_softmax` | Parity-verified vs the client (0.01%) |
| Elo conversion | own normalization | `pinned_elo_for_mover` | Board parity (D-03) |
| Per-game write serialization | row locks / FOR UPDATE | `_game_write_lock_key` + `pg_advisory_xact_lock` | The project avoids FOR KEY SHARE (deadlock with the user deleter, `eval_apply.py:2764-2777`) |
| Deleted-game FK race in the write | custom handling | `commit_unless_game_deleted` (`eval_apply.py:2748-2812`) | FLAWCHESS-A0 |
| PK-keyed partial-column update | `ON CONFLICT ... COALESCE` | ORM bulk update by PK (`update(GameFlaw)` executemany) | Preservation by omission; proven at 4.76M rows |
| DB target URLs | hardcoded DSNs | `db_url_for_target` | `.env`-sourced, consistent across scripts |
| Shard hashing | Python `hash()` | `md5(id::text)` residue | Stable across processes and re-runs |

## Runtime State Inventory

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | prod `game_flaws` ~7.61M rows (27.7k guest) need 8 new values; prod `games` (~1M with flaws) need the stamp; benchmark DB 5.48M flaws / 812k games (deferred run) | Migration (schema) + backfill (data). Benchmark: migration only, via `bin/benchmark_db.sh start` |
| Live service config | none (no feature flag needed; go-forward is gated by Maia availability) | none |
| OS-registered state | none | none |
| Secrets/env vars | `DATABASE_URL_PROD` / `DATABASE_URL_BENCHMARK` in `.env` (secret-read hook blocks `.env`; never read or print it) | none (code reads via settings) |
| Build artifacts | prod backend image must have the `maia-inference` group (already true); the benchmark-lane backend on :8001 runs whatever main-tree code is checked out, so it needs the migration applied before restart (owner memory) | Deploy; `bin/benchmark_db.sh start` before restarting :8001 |

## Common Pitfalls

### Pitfall 1: `su` comes from a different search than `best_move`
**What goes wrong:** `maia_second_*` describes the same move as `maia_best_*`. **Why:** worker MultiPV-1 best vs a separate MultiPV-2 blob search; dedup-cache best vs fresh second. **How to avoid:** if `su == best_uci`, set the second pair NULL (reason `second_equals_best`). **Warning sign:** `maia_second_rank = maia_best_rank AND maia_second_prob = maia_best_prob` rows.

### Pitfall 2: Late blobs leave `maia_second_*` NULL on a stamped game
**What goes wrong:** atomic-submit flaws the worker did not blob (`blobs_pending=True` path) have `missed_pv_lines IS NULL` at scoring time. Tier-4 fills it later, but the game is already stamped, so neither the backfill nor go-forward revisits it. **How to avoid:** run the scorer after `/flaw-blob-submit` commits (Open Question 1). **Warning sign:** a growing `second_pair_null` with `missed_pv_lines->0->>'su'` present.

### Pitfall 3: Sentinel `_session = object()` in existing tests
`test_non_tier4b_claim_still_takes_full_path` will crash in `full_policy`. Patch the scorer's inference entry point in such tests. The fail-safe catch must not stamp.

### Pitfall 4: `backfill_flaws.py` default branch destroys Maia values
Delete-then-insert (`backfill_flaws.py:391-402`) wipes blobs, tags, **and** Maia values for every game it touches. D-09's "surviving plies keep their values" holds only for the diff/upsert branches. Clear the stamp per written game so the Maia backfill restores them, and print the reminder.

### Pitfall 5: Global selector in tests
The backfill's `stamp IS NULL AND EXISTS flaws` sees leaked games from other modules under `-n auto`. Always pass `user_id`/`game_ids` in tests; clean up in `finally`.

### Pitfall 6: Python 3.14 output buffering and the 10-minute Bash cap
Use `flush=True`, `setsid nohup`, and Monitor on the DB stamp count. Commit any same-day report before a re-run.

### Pitfall 7: Prod write volume
7.6M row updates double `game_flaws` heap churn. Fillfactor is 100, so the first pass is mostly non-HOT. Plan a `VACUUM (ANALYZE) game_flaws`, and use `--throttle-ms` if it overlaps peak traffic. The orchestrator should check `pg_total_relation_size('game_flaws')` and free disk before the run.

### Pitfall 8: Custom-FEN games and ply parity
Use `board.turn` for the mover. `_collect_full_ply_targets` returns `[]` for invalid roots. The backfill should count these games as `pgn_unparseable`/`invalid_root` and still stamp them.

## Code Examples

### Full policy (refactor of score_move, D-04)
```python
# Source: app/services/maia_engine.py:151-175 (existing score_move body)
def full_policy(fen: str, elo: float) -> dict[str, float] | None:
    if _session is None:
        return None
    try:
        import numpy as np  # deferred — maia-inference group
    except ImportError:
        return None
    tokens = np.array(encode_board(fen), dtype=np.float32).reshape(1, NUM_SQUARES, PLANES_PER_SQUARE)
    elo_in = np.array([elo_to_input(elo)], dtype=np.float32)
    outputs = _session.run([_LOGITS_OUTPUT], {_TOKENS_INPUT: tokens, _ELO_SELF_INPUT: elo_in, _ELO_OPPO_INPUT: elo_in})
    policy = np.asarray(outputs[0]).reshape(-1).astype(np.float32)
    return mask_and_softmax(policy.tolist(), fen)

def score_move(fen: str, elo: float, played_uci: str) -> float | None:
    probs = full_policy(fen, elo)
    return None if probs is None else probs.get(played_uci)
```
`start_maia(*, intra_op_num_threads: int | None = None)`: when not None, build `onnxruntime.SessionOptions()`, set `.intra_op_num_threads`, and pass `sess_options=`.

### Pure stats (D-01)
```python
RANK_BASE: int = 1  # rank = RANK_BASE + #moves with strictly higher prob

class MaiaFlawStats(TypedDict):
    maia_played_prob: float | None; maia_played_rank: int | None
    maia_best_prob: float | None;   maia_best_rank: int | None
    maia_second_prob: float | None; maia_second_rank: int | None
    maia_top_prob: float | None;    maia_effective_moves: float | None

def _rank(probs: Mapping[str, float], uci: str | None) -> tuple[float | None, int | None]:
    if uci is None or uci not in probs:
        return None, None
    p = probs[uci]
    return p, RANK_BASE + sum(1 for q in probs.values() if q > p)

def compute_maia_flaw_stats(probs, played_uci, best_uci, second_uci) -> MaiaFlawStats | None:
    if not probs or played_uci not in probs:
        return None                      # caller counts reason "played_not_legal"
    if not second_uci or second_uci == best_uci:
        second_uci = None                # "" sentinel / single legal move / collision
    entropy_bits = -sum(p * math.log2(p) for p in probs.values() if p > 0.0)
    ...  # played/best/second via _rank; top = max(probs.values()); effective = 2.0 ** entropy_bits
```
Single legal move: H = 0 → effective 1.0, top 1.0, second NULL. Ties share a rank (strict `>`).

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Only stored Maia value is `game_best_moves.maia_prob` (gem/great candidates) | Per-flaw Maia stats on `game_flaws` | this phase | Enables face-palm selection (SEED-261108-dk0) |
| `score_move` discards the full policy | `full_policy` + derived stats | this phase | One inference per flaw |

**Deprecated/outdated:** none.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Postgres disables HOT when a partial-index **predicate** column changes | Q7 | If wrong, a partial index would be cheaper than stated; the recommendation (no index) still holds on the full-table-at-start argument |
| A2 | Treating `su == best_move` as "second unavailable" matches the owner's intent | Q1, Pitfall 1 | Owner may prefer storing it raw; 0.05% of rows on dev |
| A3 | The flaw ply set depends only on data the fingerprint covers (evals at write time); the fingerprint `(ply, fen, best_move, su)` catches every relevant concurrent change | Pattern 3 | A missed change → stale `maia_best_*` until the next reclassify; low impact |
| A4 | Prod Maia cost ≈ 150 ms/position (code comment) → go-forward ≈ 1.1 s CPU per analyzed game, inline in atomic-submit latency | Q3 | Higher submit latency under load; mitigable by a background task (not recommended without measurement) |
| A5 | Prod throughput is about 9 procs × ~12 positions/s ≈ 16-18 h compute (seed: 65-78 ms; measured 80 ms here with other load present) | Pattern 5 | A longer run; no correctness risk |
| A6 | Adding `dev` to `--db` choices is acceptable despite D-10 naming prod|benchmark | Pattern 5 | Trivial; drop it if the owner objects |
| A7 | All games touched by `opening_cache_repair propagate` reach `rederive` (upserted `pending`, seen in `_propagate_one_hash`) | Q2 | Missed unstamp → stale best stats for opening plies of a few games |

## Open Questions

1. **Re-score after tier-4 `/flaw-blob-submit`?**
   - What we know: it fills `missed_pv_lines` for flaws that had no blob. Without action, `maia_second_*` stays NULL on an already-stamped game, permanently.
   - What's unclear: the prod share of flaws blobbed late (orchestrator SELECT S2 below).
   - Recommendation: call the shared scorer after that commit (a 3-line hook; the backend has Maia). The minimal alternative is to clear the stamp there and rely on manual re-runs (D-11). It is not a new lottery tier, so D-11 is respected either way. Needs the owner's nod.
2. **Store `second` when it equals `best`?** Recommendation: NULL plus a counted reason (A2).
3. **Gate the go-forward scorer on `stamp_complete`?** Recommendation: no (literal D-08); the Path-B extra cost is small.

**Prod SELECTs for the orchestrator (read-only; use TABLESAMPLE to stay light):**
```sql
-- S1: second-best availability
SELECT count(*) total,
  count(*) FILTER (WHERE missed_pv_lines IS NULL) blob_null,
  count(*) FILTER (WHERE jsonb_array_length(missed_pv_lines) = 0) blob_empty,
  count(*) FILTER (WHERE missed_pv_lines->0->>'su' = '') su_empty,
  count(*) FILTER (WHERE length(missed_pv_lines->0->>'su') >= 4) su_present
FROM game_flaws TABLESAMPLE SYSTEM (1);
-- S2: late-blob exposure (flaws in full-eval'd games still awaiting tier-4)
SELECT count(*) FROM game_flaws f JOIN games g ON g.id = f.game_id
WHERE g.full_evals_completed_at IS NOT NULL AND f.allowed_pv_lines IS NULL;
-- S3: su == best_move collision rate + best_move NULL at the flaw ply
SELECT count(*) n,
  count(*) FILTER (WHERE gp.best_move IS NULL) best_null,
  count(*) FILTER (WHERE f.missed_pv_lines->0->>'su' = gp.best_move) su_eq_best
FROM game_flaws f TABLESAMPLE SYSTEM (1)
JOIN game_positions gp ON gp.game_id = f.game_id AND gp.user_id = f.user_id AND gp.ply = f.ply;
-- S4: mover rating NULL + denominator size
SELECT count(*) denom_flaws,
  count(*) FILTER (WHERE (f.ply % 2 = 0 AND g.white_rating IS NULL) OR (f.ply % 2 = 1 AND g.black_rating IS NULL)) mover_rating_null,
  count(DISTINCT f.game_id) games_with_flaws
FROM game_flaws f JOIN games g ON g.id = f.game_id WHERE g.full_evals_completed_at IS NOT NULL;
-- S5: sizes before the run
SELECT pg_size_pretty(pg_total_relation_size('game_flaws')), pg_size_pretty(pg_total_relation_size('games'));
```

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| uv / Python | all | ✓ | Python 3.14.3 (uv) | — |
| onnxruntime + numpy | inference, tests | ✓ | 1.29.0 / 2.5.2 | — |
| Dev Postgres (Docker) | tests | ✓ | flawchess-dev-db-1 (PG 18.6) | — |
| Benchmark Postgres | D-10 smoke | ✓ (container running) | flawchess-benchmark-db-1 | `bin/benchmark_db.sh start` |
| Prod tunnel | backfill | script present (`bin/prod_db_tunnel.sh`, port 15432) | — | orchestrator starts it |
| CPU / RAM for 9 procs | backfill | 16 cores, 30 GB (15 GB available at research time) | — | fewer workers |

**Missing dependencies with no fallback:** none.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (asyncio_mode=auto), per-xdist-worker cloned Postgres |
| Config file | `pyproject.toml` (`addopts` ignores `tests/scripts/benchmarks`, `tests/scripts/tagger`) |
| Quick run command | `uv run pytest tests/services/test_maia_flaw_stats.py tests/services/test_maia_flaw_scoring.py -x` |
| Full suite command | `uv run pytest -n auto -x` (CI runs serially; run the serial suite once before release) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| D-01 | rank (ties, strict >), entropy → effective moves, top, single legal move, missing best/second, `su==best` | unit (pure) | `uv run pytest tests/services/test_maia_flaw_stats.py -x` | ❌ Wave 0 |
| D-01/D-07 | migration adds 9 nullable columns; model matches | integration (template DB auto-refresh) | `uv run pytest tests/services/test_maia_flaw_scoring.py -k schema -x` | ❌ Wave 0 |
| D-04 | `full_policy` sums to 1 over legal moves; `score_move == full_policy[played]`; parity corpus | unit, real ORT (importorskip) | `uv run pytest tests/services/test_maia_engine.py -x` | ✅ extend |
| D-04 | `start_maia(intra_op_num_threads=1)` loads | unit, real ORT | same | ✅ extend |
| D-05 | no stamp when Maia absent; no stamp on scorer exception; zero-flaw game stamped | integration | `uv run pytest tests/services/test_maia_flaw_scoring.py -k stamp -x` | ❌ Wave 0 |
| D-06 | backfill uses replayed FEN (castling/ep case); `fen_mismatch` counted | integration | `uv run pytest tests/scripts/test_backfill_maia_flaws.py -k replay -x` | ❌ Wave 0 |
| D-08 | drain + atomic-submit apply with Maia writes all 8 cols for new AND surviving plies and stamps | integration | `uv run pytest tests/services/test_full_eval_drain.py tests/test_eval_worker_endpoints.py -k maia_flaw -x` | ✅ extend |
| D-09 | Maia-absent reclassify: survivors keep values, new plies NULL, deleted rows gone, stamp cleared | integration | `uv run pytest tests/services/test_maia_flaw_scoring.py -k reclassify -x` | ❌ Wave 0 |
| D-09 | `backfill_flaws.py` (default, --oracle-gap) and opening_cache_repair rederive clear the stamp + print the reminder | integration | `uv run pytest tests/test_backfill_flaws.py tests/scripts/test_opening_cache_repair.py -k maia -x` | ✅ extend |
| D-10 | `--db benchmark` resolves; dry-run against an injected session maker; shard residue partitions disjointly and exhaustively | integration | `uv run pytest tests/scripts/test_backfill_maia_flaws.py -x` | ❌ Wave 0 |
| D-11 | re-run is idempotent (no stamped game re-scored); stamped-by-other skip; fingerprint mismatch skip | integration | same file `-k rerun` | ❌ Wave 0 |
| D-12 | prod coverage ≥ 99% by bucket | manual-only (operator SQL on prod) | Pattern 6 SQL | n/a |
| golden | write-path goldens unchanged | regression | `uv run pytest tests/services/test_flaw_upsert_equivalence.py -x` | ✅ |

Mutation discipline (owner memory): prove each D-09 test by reverting the clear/omission and watching it fail. A "half-invariant" check is not enough.

### Sampling Rate
- **Per task commit:** the quick run plus the touched test file(s).
- **Per wave merge:** `uv run pytest -n auto -x`.
- **Phase gate:** the full pre-merge gate (CLAUDE.md) before `/gsd-verify-work`; dev smoke of the backfill (`--db dev --user-id 28 --limit 200`) and benchmark dry-run.

### Wave 0 Gaps
- [ ] `tests/services/test_maia_flaw_stats.py`: pure stats
- [ ] `tests/services/test_maia_flaw_scoring.py`: scorer read/score/guarded-write, guardrail, reclassify semantics
- [ ] `tests/scripts/test_backfill_maia_flaws.py`: selector, shards, replay reasons, idempotence
- [ ] Update `tests/services/test_full_eval_drain.py::test_non_tier4b_claim_still_takes_full_path` (sentinel session) to patch the new inference entry point

## Security Domain

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no (no new endpoint; the tier-4 hook rides an existing operator-token endpoint) | existing `require_operator_token` |
| V5 Input Validation | yes (worker-submitted `su`/evals feed stats) | Server re-derives everything from DB rows; `su` used only as a dict key into the legal-move policy (illegal → NULL) |
| V6 Cryptography | no | — |

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SQL injection in VALUES/IN lists | Tampering | Bound params only (project rule); no f-string values |
| Worker-tampered blob `su` | Tampering | Lookup-only against the server-computed legal policy; collisions NULL |
| Prod credential exposure | Information disclosure | `.env` never read/printed; tunnel via existing script |

## Sources

### Primary (HIGH confidence)
- Repository files read this session: `app/services/eval_apply.py` (lines 1-340, 654-1340, 1369-2063, 2152-3054), `app/services/eval_drain.py` (1022-1601), `app/routers/eval_remote.py` (1040-1090, 1176-1483), `app/services/maia_engine.py`, `app/services/maia_encoding.py`, `app/services/best_move_candidates.py`, `app/repositories/game_flaws_repository.py`, `app/models/game_flaw.py`, `app/models/game.py`, `app/services/engine.py` (312-699), `app/services/flaws_service.py` (120-150, 335-370, 770-850), `app/services/eval_entry.py` (386-605), `app/services/eval_queue_service.py` (95-505), `scripts/backfill_flaws.py`, `scripts/retag_flaws.py` (header), `scripts/opening_cache_repair.py` (1355-1400, 1472-1578, 1705-1760, 2000-2120), `scripts/remote_eval_worker.py` (320-585), `scripts/engine_disagreement_study/seed153_scan_sample.py` (25-136), the alembic migrations named above, `tests/services/test_maia_engine.py`, `tests/services/write_path_golden_scenarios.py`, CI workflow.
- Dev DB probes (docker psql): blob/su distribution, su==best collision, rating-NULL counts, `game_flaws` indexes, reloptions.
- Local benchmark: ORT 1 thread 80.5 ms vs default 95.3 ms per position.
- Context7 `/websites/onnxruntime_ai`: threading defaults.

### Secondary (MEDIUM confidence)
- SEED-261108-zkp / CONTEXT measurements (prod counts, 65-78 ms, retag precedent).
- PostgreSQL ALTER TABLE docs (metadata-only ADD COLUMN).

### Tertiary (LOW confidence)
- HOT-update behaviour with partial-index predicate columns (A1).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH (no new packages, versions verified locally).
- Architecture: HIGH for path enumeration and mechanics (code read); MEDIUM for the recommended post-commit design (a judgment call, alternatives documented).
- Pitfalls: HIGH (each tied to code or a dev probe), MEDIUM on prod magnitudes until S1-S5 run.

**Research date:** 2026-11-08
**Valid until:** 2026-12-08 (stable internal code; re-check eval_apply line numbers if other phases land first)
