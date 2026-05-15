# Phase 87.1 — Deferred Items

## From Plan 01 (zones registry + codegen + SKILL.md §3.4.2)

### Pre-existing test failures (out of scope per scope-boundary rule)

Surfaced incidentally during the full pytest sweep at Plan 01 verification. Neither failure touches `endgame_zones`, the codegen script, or `SKILL.md`:

- `tests/test_impersonation.py::test_impersonation_token_returns_target_user` — DB-dependent integration test, fails in the worktree without the Docker dev DB running.
- `tests/test_last_activity_middleware.py::TestLastActivityIntegration::test_last_activity_set_after_authenticated_request` — same DB-dependent pattern; pre-existing flake.

Both pre-date Phase 87.1. Not in scope for Plan 01 (registry / codegen / docs only). If they're a project-wide concern, surface separately — Phase 87.1 will not fix them.

### Benchmark calibration run for §3.4.2 (intentional deferral per Plan 01 scope)

Plan 01 ships `PER_CLASS_GAUGE_ZONES[<class>].achievable_score_gap = (-0.05, 0.05)` placeholders mirroring the global `ZONE_REGISTRY["endgame_type_achievable_score_gap"]` band. The actual `/benchmarks` query in SKILL.md §3.4.2 is documented but not executed. A future calibration run (any time after Phase 87.1 ships — orthogonal to Plans 02-04) will update both registry entries to data-driven per-class bands. The placeholder bands are functional for V1.
