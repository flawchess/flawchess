---
phase: quick-260724-gnd
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app/repositories/user_import_settings_repository.py
  - app/routers/users.py
  - app/services/import_service.py
  - tests/test_import_service.py
autonomous: true
requirements: [UAT-186-RACE, UAT-186-BUDGET]
must_haves:
  truths:
    - "A scope-expanding import-settings PATCH made while an import job runs survives the job's cursor writes: the next Sync re-walks the backlog from the top."
    - "A TC enabled after the first sync imports its post-anchor games uncapped via the backward walk (played_at >= created_at), matching the semantics a TC enabled at first sync gets from the forward pass."
    - "The backlog game_cap budget still gates pre-anchor games: at-cap pre-anchor games are rejected; under-cap pre-anchor games are admitted and counted."
    - "_import_scope_expanded has exactly ONE implementation shared by the PATCH endpoint and run_import."
  artifacts:
    - app/services/import_service.py
    - app/repositories/user_import_settings_repository.py
    - tests/test_import_service.py
  key_links:
    - "run_import backward-pass completion -> settings reload -> _import_scope_expanded(snapshot, reloaded) -> reset_backfill_cursors"
    - "_run_backward_pass created_at -> _run_chesscom/_run_lichess_backward_pass -> _admit_backward_game anchor param"
---

<objective>
Fix two Phase 186 import-filter bugs diagnosed against dev user 28 / chess.com hikaru, plus regression tests.

1. RACE: a running import job's periodic + final cursor persist clobbers the cursor reset that a mid-run scope-expanding settings PATCH performed, so the next Sync resumes "before the last-walked month" and never re-walks the backlog a newly enabled TC (or raised cap) now wants. Fix: re-check for scope expansion at the end of run_import (after the backward pass's final cursor flush) and reset cursors again if it expanded during the run.

2. BUDGET: `_admit_backward_game` charges post-anchor games (played_at >= users.created_at) against the per-TC backlog cap. For a TC enabled after the first sync, its post-creation games can only arrive via the backward walk (the forward window is bounded by last_synced_at), so they eat the cap instead of arriving uncapped. Fix: thread the backlog anchor into `_admit_backward_game` and admit post-anchor games WITHOUT incrementing live_counts, mirroring the forward pass's uncapped post-anchor semantics.

Purpose: a TC enabled mid-life now backfills correctly (cap backlog + uncapped post-creation games), matching a TC enabled at first sync.
Output: shared `_import_scope_expanded`, end-of-run reset in run_import, anchor-aware `_admit_backward_game`, regression tests.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@CLAUDE.md
@app/services/import_service.py
@app/routers/users.py
@app/repositories/user_import_settings_repository.py
@app/schemas/normalization.py

Interface facts (already verified against the code):
- `_import_scope_expanded(previous: ImportSettingsRow, updated: ImportSettingsRow) -> bool` currently lives in `app/routers/users.py:41`; `ImportSettingsRow` is defined in `app/repositories/user_import_settings_repository.py:34` (frozen dataclass: tc_bullet/tc_blitz/tc_rapid/tc_classical + game_cap).
- `run_import` (import_service.py:690) loads the job-start snapshot at `settings = await _load_import_settings(job.user_id)` (line 729, an `ImportSettingsRow`), runs `_run_forward_pass` then `_run_backward_pass`, then `_complete_import_job` (line 760).
- `_run_backward_pass` (line 915) receives `created_at: datetime` (the backlog anchor) and dispatches to `_run_chesscom_backward_pass` (line 1047) and `_run_lichess_backward_pass` (line 1125); BOTH call `_admit_backward_game` (chess.com at line 1102, lichess in its batch loop).
- `_admit_backward_game` (line 1002) signature: `(game, enabled_tc_buckets, live_counts, existing_platform_game_ids, game_cap) -> bool`. Order of checks: dedup -> bucket None/disabled -> at-cap reject -> increment.
- `NormalizedGame.played_at: datetime | None` (app/schemas/normalization.py:48), timezone-aware.
- `reset_backfill_cursors(session, *, user_id)` NULLs all three cursor columns; caller commits.
- `get_settings(session, *, user_id) -> ImportSettingsRow | None` is the read-only reload path.
- Test helper `_make_normalized_game(*, time_control_bucket, platform_game_id=None, played_at=None, ...)` (tests/test_import_service.py:3316) already supports `played_at`. Existing `_admit_backward_game` unit tests: `TestAdmitBackwardGame` at line 3506.
</context>

<tasks>

<task type="auto">
  <name>Task 1: Fix both bugs — shared scope predicate + end-of-run reset + anchor-aware budget</name>
  <files>app/repositories/user_import_settings_repository.py, app/routers/users.py, app/services/import_service.py</files>
  <action>
Three coordinated source changes, no logic duplication.

(a) SHARE `_import_scope_expanded`. Move the function verbatim from `app/routers/users.py` (line 41) into `app/repositories/user_import_settings_repository.py` (place it near `ImportSettingsRow`, after `_to_row`). Keep its exact body and docstring. In `app/routers/users.py`, delete the local definition and import it from the repository module (add `_import_scope_expanded` to the existing `from app.repositories.user_import_settings_repository import ImportSettingsRow` line, or reference it via the already-imported `user_import_settings_repository` module — pick whichever matches the file's existing style; the PATCH handler call at line 235 must keep working unchanged). Do NOT change the PATCH behavior.

(b) RACE FIX in `run_import` (import_service.py). The job-start snapshot is the `settings` value already loaded at line 729. After `_run_backward_pass` returns (line 750-758) and BEFORE `_complete_import_job` (line 760), reload the current settings row in a fresh session (`user_import_settings_repository.get_settings`), and if it is not None and `_import_scope_expanded(settings, reloaded)` is True, open a session, call `reset_backfill_cursors(session, user_id=job.user_id)`, and commit. This runs after the backward pass's final cursor flush, so the reset is the last write and wins. Add a bug-fix comment at the site (CLAUDE.md "Comment bug fixes"): explain that a scope-expanding PATCH mid-run has its cursor reset clobbered by the running job's final cursor persist, so we re-check the job-start snapshot vs the reloaded row and reset again if the scope expanded during the run — covers both chess.com and lichess cursors since reset_backfill_cursors NULLs all three. Import `_import_scope_expanded` from the repository module (do not redefine).

(c) BUDGET FIX. Add an `anchor: datetime` parameter to `_admit_backward_game` (import_service.py:1002). Immediately after the dedup check and the `bucket is None / not in enabled_tc_buckets` check (keep both intact), before the at-cap check, add: if `game.played_at is not None and game.played_at >= anchor`, return True WITHOUT touching live_counts (post-anchor games are uncapped, mirroring the forward pass — they cannot arrive via the forward window once a TC is enabled after the first sync, so the backward walk delivers them but they must not consume the backlog cap). Extend the fix-comment already on this function to cover the new post-anchor branch. Thread `created_at` from `_run_backward_pass` (it is the `created_at` param, line 919/940) down through `_run_chesscom_backward_pass` and `_run_lichess_backward_pass` (add an `anchor: datetime` param to both, pass `created_at` from `_run_backward_pass`) into each `_admit_backward_game` call (chess.com line 1102-1104; lichess call in its batch loop). Use `Sequence`/existing typing conventions; keep frozenset params as-is.

Run `uv run ruff format app/ && uv run ruff check app/ --fix && uv run ty check app/` — zero ty errors required.
  </action>
  <verify>
    <automated>uv run ty check app/ && uv run ruff check app/services/import_service.py app/routers/users.py app/repositories/user_import_settings_repository.py</automated>
  </verify>
  <done>`_import_scope_expanded` is defined once in the repository module and imported by both users.py and import_service.py; `run_import` resets cursors after the backward pass when the reloaded settings expanded scope vs the job-start snapshot; `_admit_backward_game` takes an `anchor` and admits post-anchor games without incrementing live_counts, threaded from `_run_backward_pass` through both platform backward passes. ty passes clean.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Regression tests for both fixes</name>
  <files>tests/test_import_service.py</files>
  <behavior>
    - Budget (extend TestAdmitBackwardGame): a post-anchor game (played_at >= anchor) in an enabled at-cap bucket is admitted (returns True) and live_counts is NOT incremented. A pre-anchor game (played_at < anchor) under cap is admitted and live_counts increments. A pre-anchor game at cap is rejected (returns False) and live_counts unchanged. Update existing TestAdmitBackwardGame calls to pass the new `anchor` argument.
    - Race: with a job-start settings snapshot narrower than the reloaded (post-PATCH) settings row (e.g. snapshot has tc_blitz=False, reloaded has tc_blitz=True), `_import_scope_expanded(snapshot, reloaded)` is True, and run_import (or the extracted reset step) calls `reset_backfill_cursors` for the user after job completion. Prefer testing the end-of-run reset via a focused test: seed a settings row, start run_import with a snapshot, mutate the row mid-run to a wider scope, assert cursors are NULL after the job completes. If wiring a full run_import is too heavy, assert the reload-vs-snapshot comparison drives reset_backfill_cursors (spy/mock) — but the shared `_import_scope_expanded` truth table (expand on TC-on and cap-raise; no reset on narrow/no-op) MUST be covered.
  </behavior>
  <action>
Add tests in tests/test_import_service.py alongside the existing `TestAdmitBackwardGame` (line 3506) and the `TestBackwardPass` integration tests (line 3547). Reuse `_make_normalized_game(..., played_at=...)` for anchor cases (it already accepts played_at). Choose an anchor like `datetime(2020,1,1, tzinfo=timezone.utc)`; post-anchor game `played_at=datetime(2024,...)`, pre-anchor `played_at=datetime(2015,...)`. For the race test, follow the existing run_import integration-test mocking pattern in this file (mocked httpx client + patched fetch generators) if you wire the full path; otherwise a targeted test that (1) proves the `_import_scope_expanded` truth table via the shared import and (2) asserts run_import's end-of-run step invokes `reset_backfill_cursors` when the reloaded row widened scope. Do not weaken the CR-01 dedup or D-15 None-bucket assertions in the existing tests — only add the `anchor` argument.
  </action>
  <verify>
    <automated>uv run pytest tests/test_import_service.py -k "AdmitBackwardGame or scope_expand or backward" -q</automated>
  </verify>
  <done>New tests fail if either fix is reverted (post-anchor game charged against cap, or end-of-run reset removed) and pass with both fixes in place. Existing TestAdmitBackwardGame tests updated for the new anchor param and still green. `uv run ty check tests/` passes.</done>
</task>

</tasks>

<threat_model>
No new trust boundary: the PATCH endpoint, its auth scoping (T-186-01: user_id only from current_active_user), and its input validation are unchanged. This is an internal correctness fix to cursor-reset timing and backlog-budget accounting; no new external input, no new packages, no new attack surface. Post-anchor admission is bounded by the platform history walk (D-07 stop condition still fires once every enabled bucket's backlog budget fills or history is exhausted), so it cannot cause an unbounded fetch.
</threat_model>

<verification>
- `uv run ruff format app/ tests/` then `uv run ruff check app/ tests/ --fix` clean.
- `uv run ty check app/ tests/` zero errors.
- `uv run pytest tests/test_import_service.py -k "AdmitBackwardGame or scope_expand or backward" -q` green (targeted module per quick-task constraint; full suite is the pre-merge gate, run later).
- Revert-check (mutation): temporarily revert the post-anchor branch OR the end-of-run reset and confirm the new test(s) fail (per feedback_mutation_test_gap_closures — prove the fix, don't grep for it).
</verification>

<success_criteria>
- One shared `_import_scope_expanded`, used by the PATCH endpoint and run_import.
- run_import resets backfill cursors after the backward pass when scope expanded mid-run (both platforms).
- `_admit_backward_game` admits post-anchor games uncapped; pre-anchor budget gating (cap + CR-01 dedup + D-15) intact.
- Regression tests present and passing; ty + ruff clean on touched files.
</success_criteria>

<output>
Create `.planning/quick/260724-gnd-fix-backfill-cursor-reset-race-and-budge/260724-gnd-SUMMARY.md` when done.
</output>
