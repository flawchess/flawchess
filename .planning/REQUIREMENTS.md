# Requirements: FlawChess — v1.30 Forcing-Line Tactic Gate

**Defined:** 2026-06-29
**Core Value:** Position-precise WDL across openings + endgames + time pressure on top of users' actual chess.com / lichess games, with personalized LLM commentary and an auto-generated opening-strengths/weaknesses report. This milestone hardens the tactic "cause-of-error" axis (v1.28) so its tags reflect *real forced tactics*, not incidental geometry in the non-forced tail of an engine PV.

**Source:** SEED-070 + `notes/tactic-forcing-line-gate.md`; corroborated by `.planning/research/SUMMARY.md` (HIGH confidence).

## v1 Requirements

Requirements for the v1.30 milestone. Each maps to a roadmap phase (141–145).

### Storage Substrate (STORE)

- [x] **STORE-01**: `game_flaws` gains nullable JSONB columns `allowed_pv_lines` / `missed_pv_lines` — each a per-node array of `{best cp, best mate, second cp, second mate, second-best UCI}` (white-perspective cp, matching the existing `eval_cp` convention) — via one Alembic migration.
- [x] **STORE-02**: No existing stats/read path regresses when the blob columns land — every `select(GameFlaw)` query site is audited and converted to explicit column projections so the JSONB blobs never leak into stats scans (`mistake-stats`, `flaw-comparison`, benchmark delta).

### Forcing-Line Gate (GATE)

- [x] **GATE-01**: A pure, engine-free, independently unit-testable `forcing_line_gate` module credits a motif only when its firing node — and every solver node leading to it — passes the only-move margin `p(best) − p(second) > ONLY_MOVE_WIN_PROB_MARGIN` (via `eval_utils.LICHESS_K`), with all thresholds as named constants. The margin is a *tunable* parameter: it defaults to lichess-puzzler's 0.35 (their +0.7 in −1..+1 space) as a **starting** value, NOT a fixed constant — the final value is chosen empirically in VALID-02. Note this margin is a best-vs-second-best *forced-ness* test on the refutation line, orthogonal to the 15pp move-severity blunder threshold.
- [x] **GATE-02**: The gate applies the already-winning reject (pre-flaw eval > `ALREADY_WINNING_CP_THRESHOLD` = 300 cp, using existing `game_positions.eval_cp` at the flaw ply), the still-winning floor (stop extending below `STILL_WINNING_FLOOR_CP` = 200 cp), a trailing-only-move strip, and a one-mover discard.
- [x] **GATE-03**: Mate scores are handled by a mate-priority hierarchy that runs *before* the sigmoid comparison — only-best-is-mate → forced; both-mate → shorter distance forced; else fall through to sigmoid — so mate-in-1 and genuine mating combinations are never suppressed by sigmoid saturation.
- [x] **GATE-04**: Uniqueness is checked at solver nodes only; defender-node ambiguity does not kill a line (branch-then-reconverge is treated as forced).

### MultiPV Engine Pass (MPV)

- [x] **MPV-01**: `EnginePool` computes MultiPV=2 per flaw-line node (best + second eval cp/mate + second-best UCI) via a dedicated `_analyse_multipv2` method (the `list[InfoDict]` return type forbids reusing `_analyse_with_pv`), persisting the result into the JSONB columns on every new analysis.
- [x] **MPV-02**: The MultiPV pass is wired into the eval drain and the remote-worker lease/submit contract additively (backward-compatible with un-upgraded workers), reusing the module-level `EnginePool` within the 4g container RSS budget.
- [x] **MPV-03**: The node budget for trustworthy best-vs-second ordering is validated via a margin histogram on ≥200 dev flaw positions before lock-in (raise budget if >10% of positions fall within ±0.05 of the margin).

### Offline Re-tagger (RETAG)

- [x] **RETAG-01**: An offline re-tagger re-derives tactic tags purely from the stored JSONB (no engine), tunable via CLI flags (`--dry-run` / `--margin` / `--user-id` / `--db`), making every threshold change a seconds-fast `/loop`-able re-derivation.
- [x] **RETAG-02**: The re-tagger is idempotent and updates the `game_flaws` tactic columns in place via the single classify path.

### Validation (VALID)

- [x] **VALID-01**: A user-28 dev A/B runs the old and new tagger logic against the *same* stored MultiPV evals (engine-free), isolating the gate's effect from `eval_cp` cross-machine non-determinism; prod-28 is a sanity reference only, not an A/B control.
- [x] **VALID-02**: The A/B measures noise removed **and** good tags killed — per-motif tags removed/survived, depth-shift distribution, and a hand-check of ~30 dropped cases with an explicit false-negative count — and the final margin is committed.

### Backfill + Rollout (SHIP)

- [ ] **SHIP-01**: A corpus backfill populates JSONB for existing analyzed `game_flaws` rows with a `WHERE allowed_pv_lines IS NULL` idempotency guard, reusing the module-level `EnginePool`; the MultiPV pass is NOT gated on `lichess_evals_at` (second-best is new data, not a lichess freebie).
- [ ] **SHIP-02**: The gated tags are rolled out to production, the live drain writes JSONB for all new games, and per-motif tactic chip counts are monitored before/after.

## v2 Requirements

Deferred to a future release. Tracked but not in this roadmap.

### Gate Refinements (GATEX)

- **GATEX-01**: "Both-winning-captures" exception — credit a tactic when the second-best move is *also* winning/also a capture (uses the stored `"su"` UCI; no engine re-pass). Promote from v2 to a Phase 145 add-on only if the Phase 144 hand-check shows a false-negative rate >~10% on this class.
- **GATEX-02**: Per-motif margin tuning (shallow motifs like fork/pin may want a different margin than deep clearance/sacrifice). A single global 0.35 is acceptable for v1.30.
- **GATEX-03**: Defender-node ambiguity rule (store/consume second-best at defender nodes) — no evidence of this noise class in the corpus yet.
- **GATEX-04**: Tablebase (Syzygy) uniqueness as a forcing signal — multi-hundred-MB dependency, near-zero real-game reach.

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Copying any lichess-puzzler source | AGPL-3.0 — heuristics/constants/names are facts (free to reimplement in original code); source is not. Same boundary as Phase 124/125. |
| Puzzle-grade depth-50 / 25M-node searches | We need trustworthy best-vs-second *ordering*, not puzzle-certainty; the all-ply 1M-node budget is the starting point. |
| Changes to `detect_tactic_motif` / the fixture precision gate | The gate is a *pre-filter* in the caller layer; the 29-motif detector and its ≥0.95 fixture precision stay byte-for-byte unchanged. |
| New stats surfaces / frontend cards for the gate | This milestone improves the *quality* of existing tactic tags; no new UI contract. |
| Sidecar `game_flaw_pv_lines` table | TOAST provides equivalent physical decoupling without a JOIN; inline JSONB is the choice. Sidecar remains the documented fallback if `game_flaws` must later stay narrow. |

## Traceability

Which phases cover which requirements. Filled during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| STORE-01 | Phase 141 | Complete |
| STORE-02 | Phase 141 | Complete |
| GATE-01 | Phase 141 | Complete |
| GATE-02 | Phase 141 | Complete |
| GATE-03 | Phase 143 | Complete |
| GATE-04 | Phase 143 | Complete |
| MPV-01 | Phase 142 | Complete |
| MPV-02 | Phase 142 | Complete |
| MPV-03 | Phase 142 | Complete |
| RETAG-01 | Phase 143 | Complete |
| RETAG-02 | Phase 143 | Complete |
| VALID-01 | Phase 144 | Complete |
| VALID-02 | Phase 144 | Complete |
| SHIP-01 | Phase 145 | Pending |
| SHIP-02 | Phase 145 | Pending |
