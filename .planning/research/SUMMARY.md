# Project Research Summary

**Project:** FlawChess v1.30 — Forcing-Line Tactic Gate
**Domain:** Chess tactic tagger quality — MultiPV=2 engine pass + JSONB persistence + offline re-tagger
**Researched:** 2026-06-29
**Confidence:** HIGH

## Executive Summary

The v1.30 milestone addresses a known mismatch between the tactic detector's training domain (lichess puzzles — fully forced lines) and its production environment (real-game refutation PVs where many nodes are not forced). The fixture precision gate scores ~0.998 micro-precision on synthetic puzzles, but that harness cannot see the non-forced tail that generates the clearance/sacrifice/capturing-defender noise observed in production. Research confirmed that modelling the gate on lichess-puzzler's `is_valid_attack` logic is the correct approach, and that the full implementation requires no new PyPI dependency, no changes to `tactic_detector.py`, and no new table beyond two nullable JSONB columns on the existing `game_flaws` table.

The recommended architecture is a strict 5-phase dependency chain: schema first, then the MultiPV=2 engine pass, then the offline re-tagger, then an A/B experiment on user-28, then corpus backfill and rollout. The most important design property — confirmed by all four research files — is that the JSONB blobs decouple the expensive engine pass from the cheap gate logic. Once blobs are stored, every threshold change, new filter rule, or margin tweak is a pure-Python offline re-tag (seconds) with no engine re-pass. This property must be preserved in implementation.

The primary risks are (a) MultiPV=2 ordering reliability at the 1M-node budget — must be verified via margin histogram before committing the budget in Phase 142; (b) mate-score saturation causing the sigmoid gate to incorrectly suppress mating combinations — requires a mate-priority check before the sigmoid comparison; and (c) the A/B validation methodology in Phase 144 conflating gate effect with eval non-determinism if old-tagger replay calls the engine instead of reading stored `eval_cp` from dev's DB.

## Key Findings

### Recommended Stack

The existing stack handles everything: python-chess 1.11.x already ships the `multipv=2` overload for `protocol.analyse()`, SQLAlchemy 2.x already ships `JSONB` from `sqlalchemy.dialects.postgresql`, and the asyncpg dialect auto-registers the JSON codec on every connection via `on_connect()`. The only required source change is that `analyse(..., multipv=2)` returns `list[InfoDict]` (not a scalar `InfoDict`), which means the existing `_analyse_with_pv` cannot be repurposed — a parallel sibling method `_analyse_multipv2` must be added to `EnginePool`.

**Core technologies:**
- `python-chess 1.11.x` (`protocol.analyse(board, limit, multipv=2)`) — returns `list[InfoDict]`, best-first; `infos[0]` is the best line, `infos[1]` the second; guard `len(infos) > 1` for single-legal-move positions
- `SQLAlchemy JSONB` (`from sqlalchemy.dialects.postgresql import JSONB`) — follow the `llm_log.py` pattern exactly; `Mapped[list[Any] | None]`, no `MutableDict` (write-once blobs), no manual codec setup
- `PostgreSQL 18 TOAST` — automatic for values over ~2 KB; the 12-node pv_lines blob is ~600 bytes, so inline storage applies; TOAST deferred loading is automatic and requires no app-side config

No new PyPI dependency. No new table. The sidecar table (`game_flaw_pv_lines`) the design note flagged as a fallback is not needed — TOAST provides equivalent physical decoupling without a JOIN.

### Expected Features

The forcing-line gate corroborates all constants and rules from the design note. Every figure below is verified directly against `generator/generator.py` and `generator/util.py` in the lichess-puzzler v50 clone.

**Must have (v1.30 table stakes):**
- MultiPV=2 engine pass + JSONB storage (`allowed_pv_lines`, `missed_pv_lines` on `game_flaws`) — everything else depends on this
- Solver-node only-move gate: `p(best) − p(second) > ONLY_MOVE_WIN_PROB_MARGIN` (0.35) — applied only at even-indexed PV nodes (solver's turn); derived from lichess's +0.7 in −1..+1 space via the algebra `2*p − 1` → exact translation, no new constant
- Already-winning reject: `flaw_pre_eval > ALREADY_WINNING_CP_THRESHOLD` (300 cp) — high-yield cheap filter using existing `game_positions.eval_cp` at `flaw_ply`; no new engine work
- Still-winning floor: stop PV walk when `best_cp < STILL_WINNING_FLOOR_CP` (200 cp) — cuts deep-tail fizzle
- Trailing-only-move strip + one-mover discard — suppresses tags on trivially forced continuations
- Offline re-tagger (`scripts/retag_flaws.py`) — pure Python; `--dry-run --margin --user-id` flags
- User-28 A/B validation — per-motif tags removed, hand-check ~30 dropped cases, false-negative count
- Corpus backfill + rollout

**Should have (zero extra engine cost — store now, surface later):**
- Second-best UCI (`"su"` field per JSONB node) — free from MultiPV=2; future-proofs "both-winning-captures" exception

**Defer to v2+:**
- "Both-winning-captures" exception — implement if hand-check false-negative rate exceeds ~10%
- Defender-node ambiguity rule — no evidence of this noise class in the corpus
- Tablebase uniqueness (Syzygy) — multi-hundred-MB dependency, near-zero real-game reach

### Architecture Approach

The gate fits into the existing `routers → services → repositories` layering without structural change. The key pattern is gate-as-pre-filter, detector unchanged: `forcing_line_gate.py` (new, pure math) is called from `flaws_service.py::_detect_tactic_for_flaw` before `detect_tactic_motif`, and `tactic_detector.py` is never modified. A second key pattern is two-phase flaw processing: `_full_drain_tick` calls `classify_game_flaws` twice — once in-memory before the write session (to identify flaw plies for the MultiPV=2 gather) and once inside the write session (authoritative write). This preserves the hard constraint against `asyncio.gather` inside an `AsyncSession`.

**Major components:**
1. `app/services/forcing_line_gate.py` (NEW) — `PvNode` TypedDict, `is_solver_node_forced()`, `apply_forcing_line_filter()`; no DB, no engine; independently unit-testable
2. `app/services/engine.py` (MODIFIED) — add `_analyse_multipv2()` / `evaluate_nodes_multipv2()` alongside existing `_analyse_with_pv`; same 1M-node budget and 5s timeout as starting point; separate method required because `multipv=2` changes the return type to `list[InfoDict]`
3. `app/services/eval_drain.py` (MODIFIED) — add step 3b: `_run_multipv2_pass()` helper gathers MultiPV results after the existing all-ply pass, before the write session opens
4. `app/services/flaws_service.py` (MODIFIED) — `_detect_tactic_for_flaw` gains optional `pv_lines_by_ply` param; gate pre-filter inserted before `detect_tactic_motif`; backward compat when param absent
5. `scripts/backfill_multipv.py` (NEW) — fills JSONB for existing `game_flaws` rows using module-level `EnginePool` (not a second independent pool)
6. `scripts/retag_flaws.py` (NEW) — reads stored blobs, applies gate, updates tactic columns; pure offline

**Confirmed unchanged:** `tactic_detector.py`, `game_positions` table, `apply_game_filters()`, `eval_queue_service.py`, all existing `classify_game_flaws` callers (new param defaults to `None`).

### Critical Pitfalls

1. **MultiPV=2 ordering unreliable at 1M nodes** — at roughly half the effective depth of single-PV, the best-vs-second margin is noisy for near-equal moves. In Phase 142, plot the margin distribution on 200–500 flaw positions before finalizing the node budget. If more than 10% of positions land within ±0.05 of 0.35, increase budget to 1.5–2M nodes.

2. **Mate-score saturation suppresses mating tactics** — `eval_mate_to_expected_score` returns 1.0 for any forced mate; best=mate-in-3 vs second=mate-in-9 gives `1.0 − 1.0 = 0.0 < 0.35` and incorrectly fails the gate. In Phase 143, implement the priority hierarchy: (a) if only best is mate → forced; (b) if both are mates → compare distances (shorter = forced); (c) fall through to sigmoid. Mate-in-1 must never be suppressed.

3. **A/B validation conflating gate effect with eval non-determinism** — old-tagger replay must read `eval_cp` from dev's DB and must not call the engine. Prod-28 is sanity reference only, not an A/B control.

4. **JSONB leaking into stats queries via ORM `select(GameFlaw)`** — after the Phase 141 migration, every existing query using `select(GameFlaw)` starts fetching the new blob columns. Audit all query sites before committing the migration; convert to explicit column projections.

5. **Second EnginePool in backfill pushing RSS into OOM zone** — QUEUE-07 accounting: 6 workers ~1,586 MB Stockfish + ~300 MB FastAPI = ~1.9 GB in the 4g container. Phase 145 backfill must reuse the module-level `EnginePool`.

## Implications for Roadmap

The 5-phase dependency chain is non-negotiable: each phase's output is a required input to the next. The JSONB blobs are the load-bearing artifact — once stored, all subsequent phases are engine-free and fast to iterate.

### Phase 141: JSONB Schema + Gate Logic
**Rationale:** Everything else depends on the ORM model and migration existing. The gate service can be written and unit-tested immediately without engine or DB.
**Delivers:** `allowed_pv_lines` / `missed_pv_lines` JSONB columns on `game_flaws`; `forcing_line_gate.py` with all constants and logic; Alembic migration; query-site audit confirming no stats path selects the new columns.
**Addresses:** JSONB storage (table stakes), gate constants (`ONLY_MOVE_WIN_PROB_MARGIN = 0.35`, `ALREADY_WINNING_CP_THRESHOLD = 300`, `STILL_WINNING_FLOOR_CP = 200`)
**Avoids:** Pitfall 6 (JSONB leaking into stats queries) — audit is part of this phase's definition of done

### Phase 142: MultiPV=2 Engine Pass + Eval Drain + Remote Worker
**Rationale:** The JSONB columns must exist (Phase 141) before anything can be written to them. This phase wires the expensive engine work; its output is stored blobs in `game_flaws`.
**Delivers:** `engine.py` `_analyse_multipv2` / `evaluate_nodes_multipv2`; `eval_drain.py` step 3b (`_run_multipv2_pass`); extended `SubmitRequest` (additive, backward-compatible); updated `remote_worker.py`; margin histogram on 200+ dev flaw positions confirming node budget.
**Uses:** `python-chess multipv=2` list API; existing `_NODES_BUDGET` (1M nodes) as starting point
**Avoids:** Pitfall 10 (list API misread — separate `_analyse_multipv2` method required); Pitfall 1 (ordering reliability — histogram gates the budget before merge); Pitfall 2 (RSS — reuse module-level pool)

### Phase 143: Offline Re-tagger
**Rationale:** JSONB blobs must be populated (Phase 142). This phase produces the tooling for all threshold iteration and the corpus rollout.
**Delivers:** `scripts/retag_flaws.py` with gate logic, mate-priority hierarchy, solver-vs-defender parity; `scripts/backfill_multipv.py`; unit tests covering mate combinations and defender-branching positions; per-position margin output for Phase 144 analysis.
**Implements:** gate-as-pre-filter architecture; mate-priority check before sigmoid; trailing-only-move strip; one-mover discard
**Avoids:** Pitfall 5 (mate saturation — priority hierarchy before sigmoid); Pitfall 7 (defender/solver parity — unit test with defender-branching position); Pitfall 9 (AGPL slip — implement from design note prose only, not open lichess-puzzler files)

### Phase 144: User-28 A/B Validation
**Rationale:** The margin (0.35) is a starting point. Validation must confirm noise reduction without excessive false negatives before committing the constant.
**Delivers:** `backfill_multipv.py --user-id 28` run on dev; per-motif tags removed and survived; hand-check of ~30 dropped cases with good-tags-killed count; depth-shift distribution; confirmed margin committed to `LICHESS_FORCING_MARGIN`.
**Avoids:** Pitfall 3 (eval non-determinism — old-tagger replay reads dev's stored `eval_cp`, never calls engine); Pitfall 4 (false negatives unmeasured — per-motif hand-check is mandatory)

### Phase 145: Corpus Backfill + Rollout
**Rationale:** Margin is confirmed (Phase 144). This phase makes the gate user-visible in production.
**Delivers:** `backfill_multipv.py --db prod` populates JSONB for all analyzed `game_flaws`; `retag_flaws.py --db prod` applies gate; tactic chip counts monitored per motif before/after; live drain now writes JSONB for all new games.
**Avoids:** Pitfall 2 (RSS — reuse module-level pool; document pool-size arithmetic before any size change); Pitfall 8 (backfill idempotency — `WHERE allowed_pv_lines IS NULL` guard; MultiPV pass is NOT gated on `lichess_evals_at` because second-best is new data not from lichess)

### Phase Ordering Rationale

- Schema strictly first: `SubmitRequest` extension, `FlawRecord` keys, and the repository write path all reference the new columns.
- Engine pass before re-tagger: the re-tagger has no input without stored JSONB.
- Validation before corpus backfill: committing the wrong margin to prod requires a second full backfill; the offline re-tagger makes margin iteration trivial on dev but expensive on prod.
- The JSONB decoupling property is what makes Phase 144 and 145 fast — the entire margin-tuning loop in Phase 144 is engine-free and takes seconds per iteration.

### Research Flags

Phases with standard patterns (research-phase not needed):
- **Phase 141:** Pure schema + pure-math gate; SQLAlchemy JSONB follows existing `llm_log.py` pattern
- **Phase 144:** Operational validation; methodology fully specified in the design note and PITFALLS.md
- **Phase 145:** Backfill follows `backfill_flaws.py` pattern; rollout is a prod run of already-validated scripts

Phases where specific sub-decisions need care during planning:
- **Phase 142:** Node budget must be decided empirically via margin histogram — plan should include histogram step as a mandatory gate before merge
- **Phase 143:** Mate-priority hierarchy and solver/defender parity need explicit unit-test coverage called out in the plan

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | python-chess `multipv=2` API and SQLAlchemy JSONB pattern both verified against official docs + codebase source; asyncpg codec auto-registration confirmed in existing `llm_log.py` working pattern |
| Features | HIGH | All constants verified directly against lichess-puzzler v50 source at the local clone; sigmoid translation `0.7 (−1..+1) → 0.35 (0..1)` is exact algebra |
| Architecture | HIGH | Derived from first-party source reading of `engine.py`, `eval_drain.py`, `flaws_service.py`, `eval_remote.py`, `game_flaws_repository.py`; all integration points confirmed |
| Pitfalls | HIGH | Grounded in documented project history (QUEUE-07 RSS accounting, eval non-determinism memory file, OOM history, AGPL boundary from cook.py alignment) |

**Overall confidence:** HIGH

### Gaps to Address

These are expected open items, not research failures:

- **Node budget for MultiPV=2:** 1M nodes is the correct starting point; the margin histogram in Phase 142 determines whether 1.5–2M is needed. Decision criterion: if more than 10% of positions fall within ±0.05 of 0.35, increase the budget.
- **Per-motif margin:** Global 0.35 may prove too aggressive for shallow motifs (fork, pin at depth 1-2). Phase 144 hand-check will reveal whether per-motif tuning is warranted; a single global constant is acceptable for v1.30.
- **False-negative rate for "both-winning-captures" positions:** Unknown until Phase 144. If hand-check shows consistent killing of real tactics on this class, the "both-winning-captures" exception should be promoted from v2+ to a Phase 145 add-on. The `"su"` field being stored in Phase 142 ensures no re-engine-pass is needed to implement it.

## Sources

### Primary (HIGH confidence)
- `app/services/engine.py` (codebase) — `_analyse_with_pv`, `EnginePool`, `_NODES_BUDGET`, `_NODES_TIMEOUT_S`, QUEUE-07 RSS accounting; `_HASH_MB = 32`, `_THREADS = 1`
- `app/models/llm_log.py` (codebase) — existing `JSONB` import, `Mapped[dict | None]` annotation, no `MutableDict`; confirms asyncpg codec is automatic
- `app/services/eval_utils.py` (codebase) — `LICHESS_K = 0.00368208`, `eval_cp_to_expected_score`, `eval_mate_to_expected_score`; confirms sigmoid saturation for mate rows
- `app/services/tactic_detector.py` (codebase) — `_solver_move_indices`; confirms even-index = solver, odd-index = defender
- `/home/aimfeld/Projects/Python/lichess-puzzler` (local clone, v50) — `generator/util.py:53` (`MULTIPLIER = -0.00368208`), `generator/generator.py:60` (0.7 margin), lines 185/114/216-221 (+300/+200 cp and length rules); read for facts/constants only, AGPL boundary respected
- `.planning/notes/tactic-forcing-line-gate.md` — source design note (SEED-070); all claims corroborated against the above

### Secondary (MEDIUM confidence)
- python-chess 1.11.2 engine docs (websearch) — `analyse()` multipv overload signature; `list[InfoDict]` return type
- SQLAlchemy discussion #11318 (websearch) — maintainer confirms `Mapped[dict | None]` + `JSONB` column type annotation
- asyncpg + SQLAlchemy JSONB codec issue #5584 (websearch) — confirms automatic `json.loads` decoder registration by the asyncpg dialect

---
*Research completed: 2026-06-29*
*Ready for roadmap: yes*
