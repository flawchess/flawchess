---
phase: 128-missed-opportunity-tagging
verified: 2026-06-19T12:00:00Z
status: passed
score: 5/5
behavior_unverified: 0
overrides_applied: 0
---

# Phase 128: Missed-Opportunity Tagging — Verification Report

**Phase Goal:** A flaw can carry both the tactic the flaw-maker *missed* (the line they should have played) and the tactic they *allowed* (the refutation), distinguished without a perspective column.
**Verified:** 2026-06-19
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Existing tactic columns renamed to `allowed_tactic_*` (data preserved) and `allowed_tactic_depth` added; new `missed_tactic_*` set added (motif/piece/confidence/depth) | VERIFIED | `app/models/game_flaw.py` lines 87-94: 8 `mapped_column` attributes (`allowed_tactic_motif/piece/confidence/depth`, `missed_tactic_motif/piece/confidence/depth`) all `Optional[int]` nullable SmallInteger. Migration `b6e2978df54f`: 4 `op.alter_column(..., new_column_name=...)` renames + 4 `op.add_column` adds; `down_revision = '9be5294cfe3c'`. No `tactic_motif`/`tactic_confidence`/`tactic_piece`/`tactic_depth` bare column attributes remain on the model. |
| 2 | Detector runs a second pass on `flaw_ply` PV with `pov = the mover`, populating `missed_*`; a flaw may have neither, one, or both column sets filled | VERIFIED | `app/services/flaws_service.py`: `_detect_tactic_for_flaw` has `orientation: Literal["allowed", "missed"] = "allowed"` param and explicit return type `tuple[int\|None, int\|None, int\|None, int\|None]`. `_build_flaw_record` calls it twice — lines 478-485. `orientation="missed"` selects `pv_by_ply.get(n)` / `positions[n].pv` and calls `detect_tactic_motif(board_before, pv)` without pushing the flaw move. Dev backfill results (human-verified): missed_only=6,718, both=18,201, neither=30,900 — confirms neither/one/both matrix. |
| 3 | No `tactic_pov` column exists — orientation is the column source; user-perspective derived via `is_opponent_expr`; narration follows column-set × is_opponent matrix | VERIFIED | `grep -rn "tactic_pov" app/` returns no matches. `is_opponent_expr` defined in `query_utils.py` (lines 23, 58-71) and imported and used in `library_repository.py`. Schema fields are orientation-labeled (`allowed_tactic_motif`, `missed_tactic_motif`) with no `tactic_pov` column anywhere in the codebase. |
| 4 | The inline-columns-vs-child-table decision is recorded (lean inline) | VERIFIED | Recorded in `128-CONTEXT.md` as D-01 (LOCKED): "Inline 8 columns on `game_flaws`, not a child table." Design note `notes/missed-vs-allowed-tactic-design.md` lines 63-66 documents the rationale. `128-ARTIFACTS.md` lists SC#4 as covered by D-01. |
| 5 | Backend filtering and comparison/flaw schemas expose both orientations; backfill is idempotent and gated on SEED-054 PV availability | VERIFIED | `library_repository.py`: `TacticOrientation = Literal["missed", "allowed"]` (line 49); `_tactic_cols(orientation)` helper returns `(motif_col, conf_col)` ORM pair; `build_flaw_filter_clauses`, `query_flaws`, `fetch_tactic_comparison` all accept `orientation: TacticOrientation = "allowed"`. `query_utils.py` `apply_game_filters` has same `orientation` param. `app/schemas/library.py`: `FlawMarker` and `FlawListItem` expose `allowed_tactic_motif`, `allowed_tactic_confidence`, `missed_tactic_motif`, `missed_tactic_confidence`. Backfill idempotency confirmed by human-verify: second run counts identical to first. No SEED-054 pre-flight gate in `scripts/backfill_flaws.py` — PV-less rows resolve to NULL missed_* (honest, D-13). |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/models/game_flaw.py` | 8 inline tactic columns (allowed_* + missed_*) | VERIFIED | Lines 87-94: all 8 `mapped_column` attributes present; no bare `tactic_motif/piece/confidence/depth` attributes remain |
| `alembic/versions/20260619_173929_b6e2978df54f_rename_tactic_cols_to_allowed_add_.py` | Data-preserving rename+add migration; down_revision 9be5294cfe3c | VERIFIED | `upgrade()`: 4 `op.alter_column(..., new_column_name=...)` + 4 `op.add_column`; `downgrade()`: 4 `op.drop_column` + 4 reverse renames; `down_revision = '9be5294cfe3c'` |
| `app/repositories/game_flaws_repository.py` | `flaw_record_to_row` maps all 8 tactic fields | VERIFIED | Lines 120-128: all 8 DB column keys mapped using `.get()` defensive pattern |
| `app/services/flaws_service.py` | Orientation-parametrized detection; both passes in `_build_flaw_record` | VERIFIED | `_detect_tactic_for_flaw` has `orientation: Literal["allowed","missed"]` param; `_build_flaw_record` calls it twice (lines 478-485) |
| `app/repositories/query_utils.py` | Orientation-aware `tactic_families` filter in `apply_game_filters` | VERIFIED | `orientation: Literal["missed","allowed"] = "allowed"` param; imports `_tactic_cols` from `library_repository`; selects column pair via helper |
| `app/repositories/library_repository.py` | Orientation-aware filter + chip read + comparison aggregation | VERIFIED | `TacticOrientation` defined here (line 49); `_tactic_cols()` helper (lines 118-131); chip read populates all 4 orientation-labeled fields |
| `app/schemas/library.py` | Both orientation column sets on flaw/marker/list schemas | VERIFIED | `FlawMarker`: `allowed_tactic_motif/confidence`, `missed_tactic_motif/confidence` (lines 66-70); `FlawListItem`: same 4 fields (lines 185-188); no bare `tactic_motif:` field remains |
| `.planning/phases/128-missed-opportunity-tagging/128-PROD-RUNBOOK.md` | Deferred prod re-backfill runbook | VERIFIED | File exists; documents folded 127+128 single-pass prod classify re-sweep as explicitly NOT run in-phase |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `flaws_service._build_flaw_record` | `flaws_service._detect_tactic_for_flaw` | Two calls with orientation="allowed" and orientation="missed" | VERIFIED | Lines 478-485: both calls present; missed call uses `orientation="missed"` |
| `app/repositories/query_utils.py` | `app/repositories/library_repository.py` | `FAMILY_TO_MOTIF_INTS` + `_tactic_cols` lazy import | VERIFIED | `from app.repositories.library_repository import FAMILY_TO_MOTIF_INTS, _tactic_cols` at line 211 |
| `scripts/backfill_flaws.py` | `app/services/flaws_service.classify_game_flaws` | Full recompute path drives both detector passes | VERIFIED | `grep -c "classify_game_flaws" scripts/backfill_flaws.py` = 5; no new gating |

### Data-Flow Trace (Level 4)

Not applicable — this phase produces schema columns, a detector pipeline, and backend filter/schema APIs, not a data-rendering component. The data flow was validated by the human-verified dev backfill producing 24,919 missed-tagged rows and 0 fabricated missed_* tags on 35,003 PV-less rows.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| No bare `GameFlaw.tactic_` ORM references in `app/` | `grep -rn "GameFlaw\.tactic_" app/ --include="*.py"` | 0 matches | PASS |
| No `tactic_pov` column anywhere | `grep -rn "tactic_pov" app/ tests/ --include="*.py"` | 0 matches | PASS |
| `flaw_record_to_row` maps all 8 DB keys | `grep -c "missed_tactic\|allowed_tactic" app/repositories/game_flaws_repository.py` | 8 keys present | PASS |
| `FlawRecord` carries both 4-tuples | `grep -c "missed_tactic_motif_int\|allowed_tactic_motif_int" app/services/flaws_service.py` | Both present | PASS |
| Migration uses rename-not-rebuild for 4 allowed_* | Content of migration b6e2978df54f | 4 `op.alter_column(new_column_name=...)`, no `op.drop_column` for renamed set | PASS |
| Full backend suite passes | Reported in 128-03-SUMMARY (final gate): `uv run pytest -n auto -x` | 2818 passed, 15 skipped | PASS |
| `ty check` clean | Reported in all plan SUMMARYs | All checks passed | PASS |

### Probe Execution

Not applicable — no phase-declared probes. The phase gate was the human-verified dev backfill (Plan 04 checkpoint:human-verify), which was completed and approved.

### Requirements Coverage

No formal REQ IDs were assigned per the phase (explicitly noted in ROADMAP.md as "to be assigned during discuss-phase"). All 5 ROADMAP Success Criteria serve as the coverage contract and are verified above as SC#1-SC#5 = Truths 1-5.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `app/models/game_flaw.py` | 82-86 | Comment references `tactic_motif`/`tactic_confidence` in docstring explanation | Info | These are explanatory docstring references to the general concept, not ORM column references — the actual `mapped_column` attributes are all correctly named `allowed_*`/`missed_*`. Not a stub. |

No debt markers (TBD/FIXME/XXX), no missing implementations, no orphaned artifacts found.

### Human Verification Required

None. The only human verification item in this phase was the Plan 04 Task 2 blocking checkpoint (dev backfill coverage + idempotency), which was completed and approved by the user prior to submitting this phase for verification. Evidence: total_flaws 73,225; allowed_tagged 35,607 (all with depth); missed_tagged 24,919; missed_only 6,718; both 18,201; neither 30,900; idempotent second run identical; 0 fabricated missed_* tags on 35,003 PV-less rows.

### Gaps Summary

No gaps. All 5 success criteria are verified in the codebase.

---

_Verified: 2026-06-19T12:00:00Z_
_Verifier: Claude (gsd-verifier)_
