# Deferred Items — quick-260414-ae4

## Pre-existing ruff F841 errors (out of scope)

Two unused-variable warnings exist in `app/services/endgame_service.py` at lines 913
(`game_id`) and 916 (`termination`), both introduced in Phase 55 (commit `0a21775e`,
2026-04-12). They are unrelated to the 6-ply threshold change. The variables are
destructured from a tuple row but never read — Phase 55 likely intended to keep the
row-unpacking block self-documenting for all columns, but ruff flags these as unused.

Not fixed in this task because:
- Out of quick-260414-ae4 scope (pre-existing, not caused by these changes).
- Fixing is trivial but touches unrelated code under active use.

Either suppress with `# noqa: F841` (self-documenting intent) or remove the two
assignments. Defer to a future cleanup pass or a dedicated code-review quick task.
