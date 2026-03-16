---
phase: 11-schema-and-import-pipeline
verified: 2026-03-16T19:00:00Z
status: human_needed
score: 5/5 must-haves verified
human_verification:
  - test: "Run the full test suite with `uv run pytest` and confirm 265 tests pass"
    expected: "All 265 tests pass with no failures"
    why_human: "Only the 3 directly affected test files (55 tests) were run during verification; the full suite count from SUMMARY (265 passed) needs a fresh run to confirm no regressions."
  - test: "Confirm MEXP-01 ply-0 semantics are intentional: ply-0 row has move_san='e4' (first move SAN), not NULL"
    expected: "Product owner/phase author confirms the PLAN semantics (ply-0 has first move SAN) supersede the REQUIREMENTS.md wording ('NULL at ply 0'); or REQUIREMENTS.md is updated to match"
    why_human: "REQUIREMENTS.md states 'NULL at final position and ply 0' but the PLAN behavior spec and all tests enforce ply-0 = first move SAN. The SUMMARY calls this a deliberate decision. A human must confirm this is accepted or update REQUIREMENTS.md."
---

# Phase 11: Schema and Import Pipeline Verification Report

**Phase Goal:** game_positions carries move_san so every position knows the move played from it, unblocking all downstream explorer work.
**Verified:** 2026-03-16T19:00:00Z
**Status:** human_needed (automated checks passed; two items require human confirmation)
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| #  | Truth                                                                              | Status     | Evidence                                                                                              |
|----|------------------------------------------------------------------------------------|------------|-------------------------------------------------------------------------------------------------------|
| 1  | game_positions table has a nullable move_san VARCHAR(10) column                   | VERIFIED   | `app/models/game_position.py` line 33: `Mapped[Optional[str]] = mapped_column(String(10), nullable=True)` |
| 2  | Covering index ix_gp_user_full_hash_move_san exists on (user_id, full_hash, move_san) | VERIFIED | Model `__table_args__` line 17; migration line 25 creates the index; `alembic current` shows `d861bce078a5 (head)` |
| 3  | hashes_for_game returns 5-tuples with move_san as the SAN of the move played FROM each position | VERIFIED | `app/services/zobrist.py` line 77: return type `list[tuple[int, int, int, int, str \| None]]`; loop computes `board.san(move)` BEFORE `board.push(move)` |
| 4  | Final position row has move_san=None; ply-0 has the first move SAN for games with moves | VERIFIED | `zobrist.py` line 123 appends `(len(moves), wh, bh, fh, None)`; loop entry at ply=0 appends move_san from `board.san(move)` before push; tests `test_hashes_for_game_returns_move_san`, `test_hashes_for_game_move_san_null_on_final_ply`, `test_hashes_for_game_move_san_ply_zero` all pass |
| 5  | Import pipeline populates move_san in position_rows via the updated 5-tuple unpack | VERIFIED   | `import_service.py` line 315: `for ply, white_hash, black_hash, full_hash, move_san in hash_tuples:`; line 324: `"move_san": move_san,` |

**Score:** 5/5 truths verified

---

### Required Artifacts

| Artifact                                                                              | Expected                                          | Status   | Details                                                                              |
|---------------------------------------------------------------------------------------|---------------------------------------------------|----------|--------------------------------------------------------------------------------------|
| `app/models/game_position.py`                                                        | move_san column definition and covering index     | VERIFIED | Contains both `move_san` column (line 33) and `ix_gp_user_full_hash_move_san` index (line 17) |
| `app/services/zobrist.py`                                                            | Extended hashes_for_game returning 5-tuples       | VERIFIED | Signature updated (line 77); loop restructured; final-position append (line 123)     |
| `app/services/import_service.py`                                                     | Updated _flush_batch with 5-tuple unpack          | VERIFIED | Line 315 unpacks 5-tuple; line 324 includes `"move_san": move_san` in dict           |
| `alembic/versions/20260316_180737_d861bce078a5_add_move_san_to_game_positions.py`    | Migration adding column and index                 | VERIFIED | `op.add_column` with `String(length=10), nullable=True`; `op.create_index` for `ix_gp_user_full_hash_move_san`; downgrade drops index then column |

---

### Key Link Verification

| From                        | To                            | Via                                         | Status  | Details                                                                   |
|-----------------------------|-------------------------------|---------------------------------------------|---------|---------------------------------------------------------------------------|
| `app/services/zobrist.py`   | `app/services/import_service.py` | hashes_for_game return value unpacked in _flush_batch | WIRED | `import_service.py` line 315 contains exact pattern `for ply, white_hash, black_hash, full_hash, move_san in hash_tuples:` |
| `app/models/game_position.py` | alembic migration            | Alembic autogenerate reads model metadata   | WIRED   | Migration `d861bce078a5` contains both `ix_gp_user_full_hash_move_san` and `move_san`; applied at head |

---

### Requirements Coverage

| Requirement | Source Plan | Description                                                                                                 | Status         | Evidence                                                                                                       |
|-------------|-------------|-------------------------------------------------------------------------------------------------------------|----------------|----------------------------------------------------------------------------------------------------------------|
| MEXP-01     | 11-01-PLAN  | game_positions table has a `move_san` column storing the SAN of the move played from each position (NULL at final position; REQUIREMENTS.md also says "and ply 0" — see note) | SATISFIED (see note) | Column exists as `String(10), nullable=True`; final position appends `None`; ply-0 has move SAN per PLAN spec |
| MEXP-02     | 11-01-PLAN  | game_positions has a covering index on `(user_id, full_hash, move_san)` for fast aggregation               | SATISFIED      | Index `ix_gp_user_full_hash_move_san` defined in model and created by migration `d861bce078a5`                 |
| MEXP-03     | 11-01-PLAN  | Import pipeline populates `move_san` for every position during game import                                  | SATISFIED      | `_flush_batch` unpacks 5-tuples and includes `"move_san": move_san` in every position_rows dict entry         |

**Note on MEXP-01 ply-0 semantics:** REQUIREMENTS.md states "NULL at final position and ply 0". The PLAN's behavior spec explicitly requires ply-0 to carry the first move SAN (e.g. "e4"), and all tests enforce this. The SUMMARY records this as a deliberate override: "STATE.md note saying 'ply-0 has NULL' was superseded by the plan's explicit behavior spec." The REQUIREMENTS.md description is inconsistent with the implementation. This is flagged for human confirmation below.

**Orphaned requirements check:** No requirements mapped to Phase 11 in REQUIREMENTS.md other than MEXP-01, MEXP-02, MEXP-03. All three are accounted for.

---

### Anti-Patterns Found

| File                      | Line | Pattern      | Severity | Impact                                                                 |
|---------------------------|------|--------------|----------|------------------------------------------------------------------------|
| `app/models/game_position.py` | 35   | `F821 Undefined name 'Game'` (ruff) | INFO  | Pre-existing issue from before Phase 11; `# type: ignore[name-defined]` comment already present; forward string reference `"Game"` is intentional SQLAlchemy pattern; not introduced by this phase |

No blockers or new anti-patterns introduced by Phase 11.

---

### Human Verification Required

#### 1. Full Test Suite Regression Check

**Test:** Run `uv run pytest` from the project root.
**Expected:** All 265 tests pass (as reported in SUMMARY). The 3 directly affected test files (55 tests) were confirmed passing during this verification.
**Why human:** Only the subset of 55 tests in the 3 affected files was run during automated verification. The full suite count needs a fresh run to confirm no regressions in unrelated tests.

#### 2. MEXP-01 Ply-0 Semantics Confirmation

**Test:** Review REQUIREMENTS.md MEXP-01 description against the actual implementation behavior, and confirm the decision is accepted.
**Expected:** Either (a) product owner confirms ply-0 carrying the first move SAN is the correct behavior and REQUIREMENTS.md is updated to remove "and ply 0" from the NULL clause, or (b) a bug is filed if the original NULL-at-ply-0 semantics were truly required.
**Why human:** REQUIREMENTS.md says "NULL at final position and ply 0" but the PLAN spec says ply-0 holds the first move SAN, and all tests enforce this. The SUMMARY explicitly notes this was a deliberate override. A human must confirm this tradeoff is accepted for Phase 12 to build on it correctly.

---

### Gaps Summary

No gaps. All 5 must-have truths are verified against the actual codebase. All 4 required artifacts exist, are substantive, and are wired. Both key links are verified. All 3 requirement IDs are satisfied. No blocker anti-patterns were introduced.

The `human_needed` status is due to: (1) the full suite was not re-run in this session and (2) a requirements documentation inconsistency on ply-0 semantics needs human acceptance.

---

_Verified: 2026-03-16T19:00:00Z_
_Verifier: Claude (gsd-verifier)_
