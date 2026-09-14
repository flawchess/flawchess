# Phase 221: Tactic-Tagger Real-Game Precision — Winning Floor, Predicate Tightening & Port Fixes (SEED-165) - Context

**Gathered:** 2026-09-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Make the persisted `allowed_*` / `missed_*` tactic tags describe tactics the user could
actually have used or avoided, on real-game engine PVs (12-ply capped, non-forcing,
sometimes losing) rather than only on curated puzzle lines. Deliverables, all in the
existing detector / gate / retag code paths (no engine pass, no migration, no schema
change):

1. Forcing-gate fixes: a solver-winning floor at the firing node; the gate is never
   skipped when `pre_flaw_eval_cp` is None (mate-adjacent flaws).
2. `sacrifice` gets a persistence rule and a depth cap; `clearance` is strengthened and
   kept only if it clears a real-game precision bar, otherwise suppressed.
3. Seven fixture-verified cook-port fixes (deflection, fork, trapped-piece,
   discovered-attack ×2, boden edge, dead `self-interference` motif).
4. Missed-orientation parity (move stack on the missed pass; recapture exclusion applied
   on both sides).
5. A hand-labelled real-game gate (`fixtures/tagger/realgame_tags.csv`) scored beside the
   CC0 fixture gate and CI-asserted per motif.
6. One release, one offline prod retag (`scripts/retag_flaws.py --db prod`, full
   refresh) with a before/after report and acceptance queries.

Evidence base (read before planning): the review report and SEED-165 in canonical refs.

</domain>

<decisions>
## Implementation Decisions

### Winning floor (forcing_line_gate.py / _classify_tactic_gated)
- **D-01:** **Per-tier floor at the firing node.** The solver-perspective eval of the blob
  node at the firing depth (odd depths rounded up to the solver node; `bm` checked before
  `b`) must be a mate for the solver or cp ≥ floor: **+200 for tier-3 (deflection,
  attraction, intermezzo, x-ray, interference, clearance, capturing-defender, sacrifice)
  and tier-5 move-type motifs (promotion, under-promotion, en-passant); 0 ("not losing")
  for tier-1/2 geometric motifs (hanging-piece, fork, pin, skewer, double-check,
  discovered-check, discovered-attack, trapped-piece).** Mate motifs are exempt (a mate
  line is winning by definition). Both floors are named constants; the tier→floor map
  lives next to the dispatcher's tier registry so it cannot drift from it. Rationale: a
  fork that wins a piece while still behind is coachable; a "sacrifice" or "clearance"
  while losing never is; +200 is lichess-puzzler's advantage floor, which the fixture
  labels implicitly assume.
- **D-02:** **Firing node only.** Node 0 is not checked; a genuine attacking sacrifice is
  legitimately below the floor at node 0 and converts deeper.
- **D-03:** **Blob missing → fall back to `game_positions` evals, same floor.** Allowed:
  eval after the flaw (`positions[n].eval_cp` / `eval_mate`, refuter's perspective).
  Missed: eval before the flaw (`positions[n-1]`, mover's perspective). No tag is skipped
  or suppressed merely for lacking a blob.
- **D-04:** **The gate is never skipped because `pre_flaw_eval_cp` is None.** The
  already-winning reject is derived from `eval_mate` when cp is absent: **a forced mate
  for the solver before the flaw = already winning = reject** (mate-motif tags stay
  exempt, as today). The rest of the gate (only-move, floors, strips, one-mover discard)
  runs on the blob exactly as for cp-scored flaws. The `blobs_pending` and `[]`-sentinel
  behaviours are unchanged.

### Sacrifice & clearance (tactic_detector.py)
- **D-05:** **Sacrifice persistence:** the material deficit must still be ≥
  `MIN_SACRIFICE_DROP` after the *next* pov move (`boards[k+3]`), or the line must end
  before that board. Drops the delayed-recapture / zwischenzug shape (32% of cook's own
  sacrifice puzzles). Documented as a deliberate divergence from cook in
  `precision_floors.py`; fixture recall will fall, precision must not.
- **D-06:** **Depth cap 4 for sacrifice and clearance only** (named constant). Other
  tier-3 motifs keep the full-line scan (deflection's deep hits are mostly real).
- **D-07:** **Clearance: strengthen, then bar.** Add to cook's predicate: the vacating
  (prior pov) move is not a king or pawn move; the ray piece's clearing move *uses* the
  line (gives check, or attacks a higher-value or hanging opponent piece from its new
  square); depth cap (D-06); winning floor (D-01). Measure on the fixture and on the
  real-game set. **Keep only if real-game precision ≥ 0.8; otherwise suppress** (remove
  from the shipped families and the frontend "Advanced" group, keep the int, retag clears
  rows). Either outcome is recorded with numbers in the summary.
- **D-08:** **Same sacrifice rules in both orientations** (one detector, one predicate).

### Missed-orientation parity (flaws_service.py)
- **D-09:** The missed pass builds `board_before` from `fen_map[n-1]` plus the opponent's
  previous move (`positions[n-1].move_san`) so the move stack carries it exactly like the
  allowed pass carries the flaw move. Unblocks intermezzo at k=2 on missed lines.
- **D-10:** **cook's hanging-piece recapture exclusion applies on the missed side too**
  (a recapture is not a "hanging piece"; "you didn't recapture" is a different message,
  out of scope). Parity with the allowed pass and with cook; the 33/302 dev rows become
  NULL.
- **D-11:** **Discovered-attack depth = k** (move index, like skewer), not k−1. Accept the
  consequences: same-k forks/skewers now beat it on the tier tiebreak, the UI difficulty
  shifts one ply deeper, the WR-02 hand-confirmed fixture is re-tuned, and the full retag
  removes all odd stored depths. — **Reversibility:** costly — reverting after the retag
  means another full prod retag.

### Port fixes (fixture-verified against the oracle comparison)
- **D-12:** Deflection promotion branch restored to cook's OR (`square ∈ attacks(orig)` OR
  the promotion same-file clause). Fork's D-01 relevance gate removed (not cook; −130
  detections for no precision). Trapped-piece empty-escape exclusion reverted (cook:
  immobile attacked piece ⇒ trapped; 0 new FPs). Discovered-attack returns (not
  continues) on a recapture. Boden/double-bishop file edge aligned. `self-interference`
  removed from `_TIER3_REGISTRY` (int 14 and the detector function kept for existing
  rows/tests; the retag clears persisted 14s).

### Real-game gate & rollout
- **D-13:** **Real-game labelled set:** ~150 prod tags stratified by motif × orientation,
  sampled *before* the fixes so before/after is scored on identical inputs; each row
  carries game_id, ply, orientation, full FEN, PV, blob eval at firing, motif, depth,
  label ∈ {real, incidental, wrong}, rationale. Stored in
  `fixtures/tagger/realgame_tags.csv` (no live prod dependency in tests). **Claude labels
  all rows; the operator spot-checks ~20** (recorded in the summary). Scored by
  `scripts/tactic_tagger_report.py` (per-motif real-share, before/after) and **CI-asserted
  per motif** in `tests/scripts/tagger/test_detector_precision.py` with floors set from
  the post-fix measurement (D-09 style, never-regress).
- **D-14:** **One release, one retag.** All detector and gate changes land in one
  squash-merge; after `/deploy`, `scripts/retag_flaws.py --db prod` runs as a **full
  refresh (no `--only-tagged`)** from the local box through `bin/prod_db_tunnel.sh` (the
  same read-write path Phase 220 used; the Phase 143/145 "tunnel is read-only" note is
  stale). Writes the per-motif removed/survived/shifted report under `reports/retag/`; the
  TAGFIX-09 acceptance queries are pasted into the summary. Dev retag first as the smoke.

### Claude's Discretion
- Exact placement of the tier→floor map and the eval-reading helper (gate module vs
  flaws_service), as long as the single classify path (SC4) is preserved.
- The precise "attacks a higher-value or hanging piece" helper for clearance (reuse
  `_is_defended` / `_PIECE_VALUES`).
- Sampling mechanics for the real-game set (SQL + a small script under `scripts/research/`).
- Floor values in `precision_floors.py` after re-measurement; new fixture rows for the
  fast-guard tests.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Evidence and scope
- `reports/tactic-tagger/tactic-tagger-review-2026-09-12.md` — the full review: prod/dev
  eval-at-firing tables, gate-skip analysis, sacrifice/clearance hand reviews, the oracle
  divergence table (§4), fix simulations, reproduction commands.
- `reports/tactic-tagger/review-2026-09-12-scripts/oracle_compare.py` — cook.py oracle
  comparison (analysis-only; imports the local AGPL clone by path; copy no source).
- `reports/tactic-tagger/review-2026-09-12-scripts/dev_probe.py` — dev-DB replay with
  material trajectory / blob-eval diagnostics; reuse for the dev retag smoke.
- `.planning/seeds/SEED-165-tactic-tagger-real-game-precision.md` — distilled diagnosis.
- `.planning/ROADMAP.md` §Phase 221 — TAGFIX-01..09 requirement definitions and success
  criteria.

### Prior design records this phase builds on
- `.planning/notes/tactic-forcing-line-gate.md` — gate design, lichess-puzzler constants,
  why the still-winning floor exists.
- `.planning/notes/tactic-tagger-cook-alignment.md` — cook↔ours index convention (read
  before touching any detector loop).
- `.planning/notes/suppressed-tactic-gaps-investigation.md` — sacrifice/attraction history
  (note: its "odd-board parity" remark about sacrifice is superseded; the current port
  matches cook on every fixture row).
- `tests/scripts/tagger/precision_floors.py` — floors and per-motif measurement history;
  every detector change updates its block.
- `reports/retag/ab-validation-2026-06-30.md` — how Phase 144 justified the current gate
  constants (do not re-litigate `ONLY_MOVE_CP_GAP_THRESHOLD` / 800cp already-winning).

### Memory notes that constrain the work
- `atomic-eval-submit-incremental-lease` — post-move shift (row P = eval of P+1),
  4-way diff/upsert, pv on transplants.
- `no-dev-db-reset-in-plans` — never gate completion on `bin/reset_db.sh`.
- `run-device-uat-yourself` — the ~20-row spot-check is the only human leg; automate
  everything else.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/services/forcing_line_gate.py`: `PvNode`, `is_solver_node_forced`,
  `_is_forced_mate_firing` (already reads the blob node at `firing_depth`; the floor
  helper is a sibling), `eval_utils.eval_cp_to_expected_score` /
  `eval_mate_to_expected_score` for perspective-safe reads.
- `app/services/flaws_service.py::_classify_tactic_gated` — the single classify path
  (SC4); the gate-skip branch and the `pre_flaw_eval_cp` plumbing live here;
  `_pov_mate` / `_solver_color_for` already convert `eval_mate` to solver perspective.
- `app/services/tactic_detector.py`: `_is_defended`, `_is_in_bad_spot`, `_PIECE_VALUES`,
  `_material_diff`, `_solver_move_indices`; `_GEOMETRIC_REGISTRY` / `_TIER3_REGISTRY` /
  `_MOVE_TYPE_REGISTRY` define the tiers the floor map keys on.
- `scripts/retag_flaws.py` — offline re-tagger (keyset paging, spawn workers, change-only
  UPDATE, `--db`, `--dry-run`, `--limit`, per-motif delta report writer).
- `scripts/tactic_tagger_report.py` + `tests/scripts/tagger/{conftest,motif_theme_map,
  precision_floors,test_detector_precision}.py` — the fixture harness; the real-game set
  slots in as a second scored table with the same TP/FP shape (label == real).
- `app/repositories/library_repository.py::FAMILY_TO_MOTIF_INTS` and
  `frontend/src/lib/tacticComparisonMeta.ts` — the only two places to touch if clearance
  is suppressed (plus the family-count test).

### Established Patterns
- Detector function contract: `(fired, piece, depth)` / tier-3 `(fired, piece, conf,
  depth)`; depth = pov move index k (skewer, deflection, clearance…) — D-11 brings
  discovered-attack in line.
- Every threshold is a named module constant with provenance in its comment; floors in
  `precision_floors.py` sit ~5–8pp below measured TRAIN.
- Build fixture boards via `build_detector_board` (pre-flaw FEN + push), never bare
  `chess.Board(fen)`, so move-stack predicates behave as in production.
- Prod operator runs go through `bin/prod_db_tunnel.sh` with `--db prod` scripts, batched
  commits, one `AsyncSession` per worker.

### Integration Points
- Gate floor: `apply_forcing_line_filter(line, solver_color, pre_flaw_eval_cp,
  firing_depth, margin)` gains a motif-tier (or motif int) argument; the fallback evals
  need `positions[n]` / `positions[n-1]` threaded from `_build_flaw_record`.
- Missed pass: `_detect_tactic_for_flaw(orientation="missed")` builds the board from
  `fen_map[n-1]` + `positions[n-1].move_san`; `_recompute_fen_map` already stores full
  FENs.
- Retag: no change needed beyond the shared classify path; the delta report already
  exists.
- Frontend: only if clearance is suppressed (remove the Advanced-group entry) and the
  `tacticMotifDefinitions.ts` copy for sacrifice may mention "material given up and not
  immediately regained".

</code_context>

<specifics>
## Specific Ideas

- The prod acceptance query from the review (§2.1) is the acceptance instrument:
  `allowed_pv_lines -> (depth + depth % 2)`, solver is white iff `ply % 2 = 1` (allowed)
  / `ply % 2 = 0` (missed); targets: losing-line share < 5% per motif, < 2% overall,
  allowed sacrifice down by the predicted order of magnitude, missed intermezzo within 3×
  of allowed, zero rows with motif 14.
- Sacrifice survivors after floor + persistence on dev (54 of 697) are the reference set
  for "what a good sacrifice tag looks like": queen/exchange sacs into mate, Bxh6 gxh6
  Rd1, Rh3 queen traps.
- Clearance "line is used" examples the strengthened predicate must still catch:
  `Na6+ Ka8 [Qc7]`, `Rc8→g8+ … [c8=Q]`; examples it must reject: `Kh1→g2 … [Rh1]`,
  `f6→f5 … [Rf6]`, `Bh8 … [Qf6]`.

</specifics>

<deferred>
## Deferred Ideas

- "You missed a recapture" as its own coaching signal (distinct from hanging-piece) —
  new capability, not this phase.
- Multi-label / co-tag storage so sacrifice can coexist with the shallower motif that
  wins dispatch — rejected in Phase 133, still out of scope.
- Re-scoring `discovered-check` against a label source other than cook (lila-side /
  crowd) — documented only (TAGFIX-08).
- Per-motif floors for deflection / intermezzo / promotion beyond the tier split — revisit
  with the real-game gate numbers after this phase.

### Reviewed Todos (not folded)
- `2026-05-18-wr01-pt33-invalid-tailwind-score-axis-label.md`,
  `172-deferred-review-findings.md`,
  `2026-03-11-bitboard-storage-for-partial-position-queries.md`,
  `2026-08-29-variation-tree-nested-button.md` — keyword matches only; unrelated to
  tactic tagging.

</deferred>

---

*Phase: 221-tactic-tagger-real-game-precision-winning-floor-predicate-tightening-port-fixes-seed-165*
*Context gathered: 2026-09-12*
