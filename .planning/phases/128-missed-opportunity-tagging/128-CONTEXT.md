# Phase 128: Missed-Opportunity Tagging - Context

**Gathered:** 2026-06-19
**Status:** Ready for planning

<domain>
## Phase Boundary

A flaw can carry **both** the tactic the flaw-maker *missed* (the line they should have
played, from the `flaw_ply` PV) **and** the tactic they *allowed* (the refutation that
punishes the flaw, from the `flaw_ply+1` PV) — distinguished by **column source**, with
**no `tactic_pov` column**. Concretely:

1. Rename the existing single tactic column set to mover-relative `allowed_*` (data
   preserved) and add a parallel `missed_*` set.
2. Run a **second detector pass** on the `flaw_ply` PV (`pov = the mover`, SEED-054 data)
   to populate `missed_*`. A flaw may have **neither / one / both** sets filled.
3. Expose **both orientations** through the backend filter + flaw/comparison schemas.
4. Idempotent backfill, gated on SEED-054 `pv[flaw_ply]` availability.

**Out of scope (Phase 129):** the depth (difficulty) slider, the missed/allowed UI toggle,
chips, the player-facing depth unit, any mobile UI. Phase 128 builds the API/schema
**contract** that 129 binds to; it does not build UI.

**Out of scope (no new motifs):** the detector motif set is frozen at Phase 127's. This phase
runs the *existing* detectors over a *second* PV — it does not add or harden motifs.

</domain>

<decisions>
## Implementation Decisions

### Storage shape (SC#4 — the explicitly-deferred decision)
- **D-01 (LOCKED):** **Inline 8 columns on `game_flaws`**, not a child table. Matches the
  existing wide `game_flaws` pattern (`tempo`, `phase`, `is_miss` are inline) and avoids a
  join for just two orientations. The child table only earns its keep with a foreseeable
  third PV source; there isn't one. Final column set:
  - `allowed_tactic_motif / allowed_tactic_piece / allowed_tactic_confidence / allowed_tactic_depth`
  - `missed_tactic_motif / missed_tactic_piece / missed_tactic_confidence / missed_tactic_depth`

### Migration = rename + add (all four existing columns are renames, NOT just three)
- **D-02:** The Phase 124 columns ARE the refutation, so they become `allowed_*`:
  - `tactic_motif → allowed_tactic_motif`
  - `tactic_piece → allowed_tactic_piece`
  - `tactic_confidence → allowed_tactic_confidence`
  - **`tactic_depth → allowed_tactic_depth`** — NOTE: the design note (written same-day)
    framed `allowed_tactic_depth` as "new", but **Phase 127 already added `tactic_depth`**
    (`game_flaw.py:78`). So it is a *fourth rename*, data-preserving (127's dev re-backfill
    populated it on dev), **not** a new column. Don't drop+re-add.
  - **New columns:** `missed_tactic_motif / missed_tactic_piece / missed_tactic_confidence /
    missed_tactic_depth` — all nullable `SmallInteger`, NULL on pre-existing rows until the
    missed pass runs.
- Net: 4 `ALTER … RENAME COLUMN` + 4 `ADD COLUMN` in one Alembic migration. No data loss;
  `allowed_*` keeps every Phase 124/125/127 tag.

### Detector second pass (missed_*) — reuse the 127 contract unchanged
- **D-03 (LOCKED):** Detectors are orientation-agnostic — `detect_tactic_motif(board, pv)`
  with `pov = board.turn`. The missed pass calls the **same dispatcher** with:
  - `board = board_before` (the pre-flaw **decision** position; `fen_map[n]` with the turn
    set from ply parity, exactly as `_detect_tactic_for_flaw` already builds `board_before`).
  - `pv = pv_by_ply.get(n)` (live drain) or `positions[n].pv` (backfill) — the **`flaw_ply`**
    PV, i.e. the SEED-054 "instead-of" line. (The allowed pass uses `n+1` / `positions[n+1].pv`.)
  - `pov = board_before.turn` (the **mover** — the flaw-maker, who should have played this line).
- **D-04:** **Reuse the 127 relevance gate, confidence floor, and `tactic_confidence`
  query-suppression unchanged.** No separate missed-orientation harness pass (the same
  motif-detection code runs over a PV; precision is a property of the detector, not the PV
  source). The "instead-of" line distribution is the engine's own best continuation — if
  anything *cleaner* (more forcing/winning) than a refutation, so the relevance gate holds.
- **D-05:** **Depth baseline differs by one ply between the two sets, by design.**
  `allowed_tactic_depth` is the loop index within the `flaw_ply+1` PV; `missed_tactic_depth`
  is the loop index within the `flaw_ply` PV (which starts one ply earlier — at the
  decision position). Both are "ply at which the motif fires within *its own* PV." Document
  this in the model comment so the Phase 129 slider treats them consistently (both are
  detector-loop indices; neither is an absolute game ply).
- **D-06:** Refactor `_detect_tactic_for_flaw` (`flaws_service.py:363`) to be
  orientation-parametrized (or split into `_detect_allowed` / `_detect_missed`) so
  `_build_flaw_record` (`:411`) calls it twice and fills both 4-tuples on `FlawRecord`.
  `pv_by_ply` already carries **both** `flaw_ply` and `flaw_ply+1` PVs from the SEED-054
  drain change (`eval_drain.py:795-811`), so no new PV plumbing is needed in the live path.

### Backend filter + schema (SC#5)
- **D-07 (LOCKED):** **Full orientation-aware filter + schema in Phase 128.** The filter
  accepts an **`orientation ∈ {missed, allowed}`** dimension alongside the existing
  `tactic_families`; the flaw card + comparison schemas expose **both** column sets. Phase
  129 only wires UI controls to this contract — it adds no new backend filter logic.
- **D-08:** Default-orientation behavior when `orientation` is unspecified is **Claude's
  discretion at planning time**, but the safe default is to **preserve current Library
  behavior** (i.e. unspecified ⇒ `allowed`, since today's `tactic_families` filter queries
  what becomes `allowed_tactic_motif`). Phase 129's UI default is **missed** (the trainable
  orientation) — that's a UI default, set there, not a backend default.
- **D-09:** The orientation switch selects the matching column set in **both** filter sites:
  `query_utils.build_flaw_filter_clauses` / `apply_game_filters` (`query_utils.py:201-227`)
  **and** `library_repository` (`:196-201`, `:470-476`). Reuse the existing
  `_TACTIC_CHIP_CONFIDENCE_MIN` (70) and `FAMILY_TO_MOTIF_INTS` map for both orientations —
  the family→int mapping is motif-identity, orientation-independent.
- **D-10:** Narration follows the **column-set × `is_opponent_expr(ply, user_color)`** matrix
  from the design note — no new perspective storage. `is_opponent_expr` (`query_utils.py:23`,
  unit-tested) is the single source. (Surfacing copy itself is Phase 129; 128 just keeps the
  schema orientation-labeled so 129 can apply the matrix.)

### Backfill (SC#5) — dev in-phase, prod via runbook
- **D-11 (LOCKED):** **Dev backfill is the phase gate; prod is a deferred runbook step**
  (mirrors Phase 127 D-13). In-phase: run the missed pass + `allowed_tactic_depth` fill over
  the tagged dev games (also the real-data validation of the missed pass). Idempotent on
  **`missed_tactic_motif IS NULL`** (and depth-NULL for the allowed-depth fill).
- **D-12:** **SEED-054 is NOT a gate the planner has to design around.** The user confirmed
  (2026-06-19) the SEED-054 `pv[flaw_ply]` **prod backfill is already underway and will
  complete before the 128 flaw/tactic backfill runs.** So the planner should **assume
  `pv[flaw_ply]` is available at prod-backfill time** — do **not** build any pre-flight
  coverage check, gating, or blocking logic into the 128 backfill for this dependency. The
  missed pass simply reads the PV; rows that still lack one resolve to NULL `missed_*`
  (honest, D-13), no special-casing.
  - **Efficiency note for the planner:** Phase 127's prod re-backfill is also still pending
    (D-13 runbook). Since the missed pass lives inside `classify_game_flaws`, a **single**
    prod `classify` re-backfill can fill corrected `allowed_*` (127), `allowed_tactic_depth`,
    AND `missed_*` in one pass — fold 127's and 128's prod runbooks together rather than
    re-sweeping twice. Reuse `scripts/backfill_flaws.py`.
- **D-13:** Lichess-only `pv[flaw_ply]` coverage fills in over time via the existing idle
  tier-3 fleet (new drains store both PVs automatically); the backfill is the catch-up, not
  the steady-state path. NULL `missed_*` on rows lacking a `flaw_ply` PV is **honest** (same
  posture as 127's NULL depth) — never fabricate.

### Claude's Discretion
- Exact filter param name/shape for `orientation` (enum `Literal["missed","allowed"]` vs a
  pair of booleans) and where the default lands (D-08).
- Whether to split `_detect_tactic_for_flaw` into two named functions or parametrize it (D-06).
- Migration column ordering / whether to batch the rename+add in one revision (D-01/D-02 —
  one revision strongly preferred).
- Backfill batch size and `--db` plumbing (reuse `scripts/backfill_flaws.py` patterns).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Design notes (the source of this phase — read first)
- `.planning/notes/missed-vs-allowed-tactic-design.md` — **THE design record.** The two
  orthogonal axes, the dual mover-relative column decision (no `tactic_pov`), the
  rename-not-rebuild migration, the narration matrix, the inline-vs-child-table open
  decision (now D-01), depth-as-difficulty.
- `.planning/notes/tactic-tagging-architecture.md` — locked architecture: single-tag-per-flaw
  (`GROUP BY` cleanliness), `tactic_confidence` as the query-time precision knob, motif set +
  tiers, D-07 priority/mate dominance.
- `.planning/notes/tactic-detector-precision-gaps.md` — deep-scan/loose-pin precision record
  (fixed in 127); the relevance-gate rationale the missed pass inherits.

### Prior phase context (decisions carried forward)
- `.planning/phases/127-detector-hardening-validation/127-CONTEXT.md` — the 4-tuple detector
  contract `(fired, piece, confidence, depth)`, depth-first dispatch + relevance gate (D-01),
  precision floors / query-suppression (D-08/D-09), the dev-in-phase / prod-runbook
  re-backfill precedent (D-13). The missed pass reuses ALL of this unchanged (D-03/D-04).

### Seed (the missed-pass data dependency)
- `.planning/seeds/closed/SEED-054-best-move-pv-at-flaw-ply.md` — stores `pv` at `flaw_ply`
  (the missed-pass input); idempotent local-machine prod backfill via
  `scripts/backfill_best_move_pv.py`. **Prod backfill still pending** (D-12).

### Detector + integration code
- `app/models/game_flaw.py:68-78` — the four tactic columns to rename (`tactic_*`) +
  the four `missed_tactic_*` to add (D-01/D-02).
- `app/services/flaws_service.py:363` `_detect_tactic_for_flaw`, `:411` `_build_flaw_record`,
  `:138-141` `FlawRecord` tactic fields — the second-pass integration point (D-06).
- `app/services/tactic_detector.py` — `detect_tactic_motif` dispatcher (orientation-agnostic;
  called with `board_before` + `flaw_ply` PV + `pov=mover` for the missed pass, D-03).
- `app/services/eval_drain.py:795-811` — drain already writes/passes PVs at **both**
  `flaw_ply` and `flaw_ply+1` (SEED-054); `:716-723` builds `pv_by_ply` for live classify.
- `app/repositories/query_utils.py:23` `is_opponent_expr` (perspective, D-10);
  `:88,201-227` `tactic_families` filter + `FAMILY_TO_MOTIF_INTS` (orientation-aware, D-09).
- `app/repositories/library_repository.py:51` `_TACTIC_CHIP_CONFIDENCE_MIN`, `:196-201`
  filter clause, `:470-476` chip read — second filter/read site to make orientation-aware (D-09).
- `app/repositories/game_flaws_repository.py:118-122` — the write path mapping
  `FlawRecord` → DB columns (extend for `missed_*` + renamed `allowed_*`).
- `app/schemas/library.py:53-63,172-175` — flaw/chip schema fields to expose both
  orientations (D-07).
- `app/services/library_service.py` — tactic_families pass-through (rename ripple).
- `scripts/backfill_flaws.py` — the dev re-backfill path (D-11) + folded prod runbook (D-12).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`pv_by_ply` already dual-PV** — the SEED-054 drain change (`eval_drain.py:795-811`)
  persists and passes PVs at both `flaw_ply` and `flaw_ply+1`. The missed pass reads
  `pv_by_ply.get(n)` with **zero** new PV plumbing in the live path.
- **`_detect_tactic_for_flaw` already builds `board_before`** (`flaws_service.py:399-400`,
  turn set from ply parity) — the exact board the missed pass needs. The diff is which PV
  to feed (`n` vs `n+1`) and which board to pass to the detector (`board_before` vs
  `board_after_flaw`) + `pov`.
- **`tactic_confidence` query-suppression + `FAMILY_TO_MOTIF_INTS`** — both reusable for
  `missed_*` unchanged; the family→int map is motif-identity, orientation-independent (D-09).
- **`scripts/backfill_flaws.py` + `classify_game_flaws`** — the existing recompute kernel;
  the dev re-backfill and the folded prod runbook reuse it (D-11/D-12), no new script for
  the missed pass itself.

### Established Patterns
- **Detector = pure CPU over a stored PV, `pov = board.turn`** — the missed pass stays
  inside this contract (no engine, no OOM exposure).
- **Single tag per orientation, clean `GROUP BY <orientation>_tactic_motif`** — the dispatch
  still returns exactly one winning motif per PV; now there are two independent PVs → up to
  two tags per flaw, one per column set.
- **Nullable SmallInteger tactic columns, NULL = honest absence** — `missed_*` NULL on rows
  without a `flaw_ply` PV (lichess coverage still filling) is the same posture as 127's NULL
  depth. Never fabricate.

### Integration Points
- **Rename ripple** touches: model → migration → `game_flaws_repository` write path →
  `query_utils` filter → `library_repository` filter + chip read → `library_service` →
  `library.py` schema. Every `tactic_motif`/`tactic_piece`/`tactic_confidence`/`tactic_depth`
  reference becomes `allowed_*`. Grep-driven; the scout list above is the full set in `app/`.
- **Second pass** adds: orientation param to `_detect_tactic_for_flaw`, a second call in
  `_build_flaw_record`, four `missed_*` fields on `FlawRecord`, four write-path mappings.
- **Filter contract** adds: an `orientation` dimension to the flaw filter (both sites) and
  both column sets to the flaw/comparison schemas (the Phase 129 UI binds to this).

</code_context>

<specifics>
## Specific Ideas

- The user took all four recommended options cleanly (inline storage; dev-in-phase +
  prod-runbook backfill; full orientation-aware filter+schema; reuse 127 gate/floors). No
  freeform amendments — the design note + 127 context already captured the intent.
- Governing value (inherited from 127): a wrong *visible* tag erodes trust more than a
  missing one — so `missed_*` stays NULL rather than guessing when the `flaw_ply` PV is
  absent, and reuses the precision-first confidence gate.

</specifics>

<deferred>
## Deferred Ideas

- **Depth (difficulty) slider, missed/allowed toggle, chips, player-facing depth unit,
  mobile UI** — Phase 129 (Tactic Filter UI). 128 builds the backend contract only.
- **Surfacing "opponent missed a fork" (scouting orientation)** — the design-note matrix row
  marked "probably not surfaced"; a Phase 129 UI choice, not a 128 storage concern (the data
  is derivable from `missed_*` + `is_opponent_expr` regardless).
- **Prod re-backfill execution** (SEED-054 pv + folded 127/128 `classify` re-sweep) — runbook
  step after 128 ships (D-12), executed outside the phase gate.
- **Re-ranking by confidence / multi-motif-per-PV storage** — explicitly rejected in the
  architecture note; not revisited.

None of the above is in Phase 128 scope.

</deferred>

---

*Phase: 128-missed-opportunity-tagging*
*Context gathered: 2026-06-19*
