# Deferred items (Phase 85)

## Pre-existing `ruff format --check .` drift (out of scope for Phase 85)

`uv run ruff format --check .` reports 93 files would be reformatted as of
this phase's base commit. None of the files are touched by this phase's
plans; the drift predates phase 85 and is reproducible against the
`main`-branch working tree at `/home/aimfeld/Projects/Python/flawchess`.

Plan 85-04 acceptance criterion listed `uv run ruff format --check .` as a
gate; per the SCOPE BOUNDARY rule the executor did NOT auto-format 93
untouched files (would balloon the PR with churn unrelated to Section 1)
and is logging the gap here instead. `uv run ruff check .`, `uv run ty
check app/ tests/`, and `uv run pytest` all exit 0.

Suggested follow-up: a dedicated `/gsd-quick` or chore PR that runs
`uv run ruff format .` repo-wide and commits the result, then verifies CI
stays green.
