# Requirements: FlawChess v1.15 — Eval-Based Endgame Classification

**Milestone goal:** Replace the material-imbalance + 4-ply persistence proxy for endgame conversion/recovery classification with Stockfish eval (depth 15) populated into the existing `eval_cp` / `eval_mate` columns on `game_positions`. Backfill historical span-entry positions across benchmark + prod, eval new span-entry positions during import going forward, refactor endgame queries to threshold on eval, and remove the proxy entirely (hard cutover).

**Source:** Validation report at `reports/conv-recov-validation-2026-05-02.md` flagged that the proxy holds at ~81.5% agreement vs Stockfish on the populated subset (22% lichess-only eval coverage) but misses ~24% of substantive material-edge sequences. Queen and pawnless classes underperform structurally.

---

## v1.15 Requirements

### Engine Integration (ENG)

- [ ] **ENG-01**: Stockfish (recent stable version, pinned) is available inside the backend Docker image and runs as a long-lived UCI process — not a per-call subprocess fork.
- [ ] **ENG-02**: A thin engine wrapper module exposes a single async-friendly API for evaluating a board position at depth 15, returning `(eval_cp, eval_mate)` with white-perspective sign convention matching the existing column semantics in `app/services/zobrist.py`.
- [ ] **ENG-03**: The wrapper is shared by the backfill script and the import path so engine lifecycle (startup, hash size, depth) is configured in exactly one place.

### Backfill (FILL)

- [ ] **FILL-01**: A backfill script identifies endgame span-entry rows where both `eval_cp` and `eval_mate` are NULL, replays SAN from the game's `pgn` column to that ply, evaluates the position, and writes back. A span entry is `MIN(ply)` of a `(game_id, endgame_class)` group with `count(ply) ≥ ENDGAME_PLY_THRESHOLD`.
- [ ] **FILL-02**: The script is idempotent (safe to re-run; skips rows already populated), resumable (interruption mid-run does not require restart from scratch), and dedupes evaluations by `full_hash` so identical positions are not re-evaluated.
- [ ] **FILL-03**: The script runs to completion against the benchmark database first; the operator validates results before running it against prod.
- [ ] **FILL-04**: After the prod backfill completes, every endgame span-entry row in prod has either `eval_cp` or `eval_mate` populated (existing lichess `%eval` annotations are trusted and not overwritten).

### Import Pipeline (IMP)

- [ ] **IMP-01**: When a game is imported, after endgame classification has marked positions with `endgame_class`, the import worker evaluates each per-class span-entry position and writes `eval_cp` / `eval_mate` to those rows where the lichess `%eval` annotation did not already populate them.
- [ ] **IMP-02**: Import-time evaluation does not block other imports for an unbounded duration — typical games (1-3 span entries × ~70 ms at depth 15) add well under 1 second per game to the import path.

### Endgame Service Refactor (REFAC)

- [ ] **REFAC-01**: `query_endgame_entry_rows`, `query_endgame_bucket_rows`, and `query_endgame_elo_timeline_rows` in `app/repositories/endgame_repository.py` are rewritten to threshold on `eval_cp` and `eval_mate` at the span-entry row instead of `material_imbalance` at entry plus a contiguity-checked persistence lookup at entry + 4 plies.
- [ ] **REFAC-02**: Conversion / parity / recovery classification follows the rule: apply user-color sign flip first, then `(eval_mate > 0) OR (eval_cp ≥ 100) → conversion`; mirror for recovery; else parity. Mate scores at any value count as max conversion / recovery.
- [ ] **REFAC-03**: `_MATERIAL_ADVANTAGE_THRESHOLD`, `PERSISTENCE_PLIES`, the `array_agg(... ORDER BY ply)[PERSISTENCE_PLIES + 1]` patterns, and the contiguity case-expression are deleted from the codebase. The proxy is gone — hard cutover, no fallback.
- [ ] **REFAC-04**: Index `ix_gp_user_endgame_game` is updated via Alembic migration so the new eval-based query stays index-only (the `INCLUDE` columns reflect what the rewritten queries actually read).
- [ ] **REFAC-05**: The `material_imbalance` column on `game_positions` is preserved — it remains useful for other features and is not coupled to the conv/recov classification anymore.

### Validation (VAL)

- [ ] **VAL-01**: After the benchmark backfill, `/conv-recov-validation` is re-run and the report shows ~100% agreement on the populated subset by construction (proxy and ground-truth both derive from the same `eval_cp` / `eval_mate` columns).
- [ ] **VAL-02**: Headline endgame gauges on the live UI for representative test users do not shift by more than expected for any `(rating, TC)` cell — operator-level smoke check, not a hard numeric threshold (the new classification is more accurate, so some shifts are expected and welcome).

---

## Future Requirements

(deferred — gated on full benchmark ingest, SEED-006)

- [ ] Classifier validation replication at 10–100x scale (Phase B gate)
- [ ] Rating-stratified material-vs-eval offset analysis
- [ ] Parity proxy validation against Stockfish eval
- [ ] `/benchmarks` skill upgrade — population baselines and rating-bucketed zone thresholds applied to `frontend/src/lib/theme.ts`

(SEED-010 Library milestone — full multi-phase milestone, gated until v1.15 ships)

---

## Out of Scope (this milestone)

- **Re-evaluating positions that already have a lichess `%eval` annotation** — the validation report demonstrated lichess evals are accurate enough for classification; re-evaluating burns CPU for no agreement gain. Trust them.
- **Adding new columns** — `eval_cp` / `eval_mate` already exist; no schema growth is needed for this milestone. Span entries are derivable from `endgame_class` + `ply` aggregation.
- **Tuning the ±100 cp threshold or experimenting with per-class thresholds** — the validation report flagged queen and pawnless underperform on the proxy, but with engine eval as ground truth those classes are now classified directly. Per-class threshold tuning is out of scope; we use the same ±100 cp boundary uniformly.
- **Removing or deprecating the `material_imbalance` column** — it has other consumers (e.g. potential future positional features). Decoupled but kept.
- **Eval coverage outside endgame span entries** — opening / middlegame positions are not part of this milestone. Only span-entry rows are filled.
- **Tactical filters or per-ply eval timeline data** — those are part of SEED-010 Library and depend on a different (broader) eval pass, not this targeted backfill.

---

## Traceability

| REQ-ID    | Phase | Notes                                   |
|-----------|-------|-----------------------------------------|
| ENG-01    | TBD   | Pending roadmap                         |
| ENG-02    | TBD   | Pending roadmap                         |
| ENG-03    | TBD   | Pending roadmap                         |
| FILL-01   | TBD   | Pending roadmap                         |
| FILL-02   | TBD   | Pending roadmap                         |
| FILL-03   | TBD   | Pending roadmap                         |
| FILL-04   | TBD   | Pending roadmap                         |
| IMP-01    | TBD   | Pending roadmap                         |
| IMP-02    | TBD   | Pending roadmap                         |
| REFAC-01  | TBD   | Pending roadmap                         |
| REFAC-02  | TBD   | Pending roadmap                         |
| REFAC-03  | TBD   | Pending roadmap                         |
| REFAC-04  | TBD   | Pending roadmap                         |
| REFAC-05  | TBD   | Pending roadmap                         |
| VAL-01    | TBD   | Pending roadmap                         |
| VAL-02    | TBD   | Pending roadmap                         |
