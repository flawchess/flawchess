# Deferred Items — quick-260428-tgg

## Pre-existing ruff format drift (out of scope)

`uv run ruff format --check .` reports 92 files would be reformatted on this
branch, but verifying on the pristine task base (commit 2951cdb, before any
edits from this task) shows the SAME 92 files would be reformatted. The drift
is pre-existing and unrelated to this quick task's changes.

Per the executor scope-boundary policy ("only auto-fix issues DIRECTLY caused
by the current task's changes"), reformatting 92 unrelated test files is NOT
in scope here. Fixing it would muddy the task's diff and risk merge conflicts
with concurrent feature branches.

The two files this task did touch that needed reformatting (one wide line in
the new `test_ranking_small_n_high_effect...` test and pre-existing two-line
function signatures in `openings_service.py`) were handled correctly:
- `tests/services/test_opening_insights_service.py`: reformatted as part of
  Task 2 to keep my own additions clean.
- `app/services/openings_service.py`: the format diff is on lines I did NOT
  touch (lines 55-67, `derive_user_result` signature) and is therefore
  pre-existing drift; left alone.

Recommended follow-up: a separate quick task to run `uv run ruff format .`
across the entire repo and commit the result as a single chore commit.
