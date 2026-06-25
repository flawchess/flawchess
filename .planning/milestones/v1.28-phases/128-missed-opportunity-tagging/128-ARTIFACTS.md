# Phase 128 — Artifacts, Source Audit & Decision Coverage

## Artifacts this phase produces

### New columns on `game_flaws` (Plan 01)
- `missed_tactic_motif` — nullable SmallInteger (TacticMotifInt enum) — NEW
- `missed_tactic_piece` — nullable SmallInteger (python-chess PieceType) — NEW
- `missed_tactic_confidence` — nullable SmallInteger (0-100) — NEW
- `missed_tactic_depth` — nullable SmallInteger (loop index within the flaw_ply PV) — NEW

### Renamed columns on `game_flaws` (Plan 01 — NOT new identities, data-preserving renames)
- `tactic_motif → allowed_tactic_motif`
- `tactic_piece → allowed_tactic_piece`
- `tactic_confidence → allowed_tactic_confidence`
- `tactic_depth → allowed_tactic_depth` (the D-02 fourth rename — Phase 127 already added `tactic_depth`)

### Alembic revision (Plan 01)
- One new revision, `down_revision = '9be5294cfe3c'` (current head: add_tactic_depth_to_game_flaws). 4 `alter_column` renames + 4 `add_column`. Revision id assigned at autogenerate time (record in 128-01-SUMMARY.md).

### FlawRecord TypedDict keys (Plan 01 / Plan 02)
- Renamed: `tactic_motif_int/piece/confidence/depth → allowed_tactic_motif_int/piece/confidence/depth`
- New: `missed_tactic_motif_int/piece/confidence/depth`

### Detector entry point (Plan 02)
- `_detect_tactic_for_flaw` gains an `orientation: Literal["missed", "allowed"]` parameter (parametrized, not split — per D-06 discretion). `detect_tactic_motif` (the dispatcher) is unchanged — it is already orientation-agnostic (`pov = board.turn`).

### Filter / schema contract (Plan 03)
- `TacticOrientation = Literal["missed", "allowed"]` — NEW type alias (owned by `library_repository.py`)
- `orientation: TacticOrientation = "allowed"` param on `apply_game_filters` (query_utils) + the library_repository filter/chip functions + `get_tactic_comparison` (library_service)
- Pydantic schema fields (flaw card / FlawMarker / flaw list / comparison): `tactic_motif/tactic_confidence` renamed to `allowed_tactic_motif/allowed_tactic_confidence`; NEW `missed_tactic_motif/missed_tactic_confidence`

### Backfill (Plan 04)
- No new script; `scripts/backfill_flaws.py` recompute path drives both passes via `classify_game_flaws`. No new CLI flags. NEW: `128-PROD-RUNBOOK.md` (deferred folded 127+128 prod re-backfill).

---

## Multi-Source Coverage Audit

### GOAL (ROADMAP phase goal)
> A flaw can carry both the tactic the flaw-maker *missed* and the tactic they *allowed*, distinguished without a perspective column.
- COVERED by Plans 01 (storage), 02 (missed pass), 03 (no tactic_pov; orientation = column source).

### REQ (phase_req_ids)
- None assigned ("(to be assigned during discuss-phase)"). The 5 ROADMAP Success Criteria + D-01..D-13 serve as the coverage contract (per planning_context).

### ROADMAP Success Criteria
| SC | Description | Covered by |
|----|-------------|-----------|
| SC#1 | rename to allowed_*, add allowed_tactic_depth + missed_* set | Plan 01 |
| SC#2 | second pass on flaw_ply PV, pov=mover; neither/one/both | Plan 02 |
| SC#3 | no tactic_pov; orientation = column source; is_opponent_expr matrix | Plan 02 (no pov col), Plan 03 (schema labeling) |
| SC#4 | inline-columns-vs-child-table decision recorded | D-01 (inline) — Plan 01 implements |
| SC#5 | filter + schemas expose both orientations; idempotent backfill gated on PV availability | Plan 03 (filter/schema), Plan 04 (backfill) |

### RESEARCH
- No RESEARCH.md (intentionally skipped). CONTEXT.md `<canonical_refs>`/`<code_context>` serve the analog-mapping role; all referenced files were read during planning.

### CONTEXT (D-01..D-13 decision coverage)
| Decision | Covered by |
|----------|-----------|
| D-01 inline 8 columns | Plan 01 Task 1 |
| D-02 4 renames (incl. tactic_depth) + 4 adds, data-preserving | Plan 01 Task 1; Plan 03 Task 1 (ripple) |
| D-03 orientation-agnostic dispatcher, missed = board_before + flaw_ply PV + pov=mover | Plan 02 Task 1 |
| D-04 reuse 127 gate/floor/suppression, no new harness | Plan 02 Task 1 (acceptance: no new detector/harness) |
| D-05 depth baseline differs one ply, documented in model comment | Plan 01 Task 1 (model comment) |
| D-06 parametrize _detect_tactic_for_flaw, two calls in _build_flaw_record | Plan 02 Tasks 1+2 |
| D-07 full orientation-aware filter + schema in 128 | Plan 03 Tasks 2+3 |
| D-08 unspecified ⇒ allowed (preserve Library behavior) | Plan 03 Task 2 (default="allowed") |
| D-09 both filter sites; reuse FAMILY_TO_MOTIF_INTS + _TACTIC_CHIP_CONFIDENCE_MIN | Plan 03 Task 2 |
| D-10 schema orientation-labeled for is_opponent_expr matrix; no narration copy | Plan 03 Task 3 |
| D-11 dev backfill is the gate; idempotent on missed_tactic_motif IS NULL | Plan 04 Tasks 1+2 |
| D-12 no SEED-054 pre-flight gate; fold prod runbook with 127's | Plan 04 Task 1 |
| D-13 NULL missed_* on PV-less rows is honest, never fabricated | Plan 04 Task 1 + checkpoint spot-check |

All 13 decisions traceable. No unplanned source items. Deferred Ideas (depth slider, missed/allowed UI toggle, chips UI, mobile UI, scouting orientation, prod re-backfill execution, re-ranking) are Phase 129 / explicitly out of scope and correctly absent from these plans.
