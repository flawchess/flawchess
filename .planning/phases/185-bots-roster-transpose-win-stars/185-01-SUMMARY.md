---
phase: 185-bots-roster-transpose-win-stars
plan: 01
subsystem: api
tags: [fastapi, sqlalchemy, alembic, postgres, pydantic, bots]

# Dependency graph
requires:
  - phase: 167-bot-play-store-on-finish
    provides: store_bot_game_service's created-gated post-insert UPDATE pattern (PGN/URL stamp) and the platform='flawchess' games row this phase extends
  - phase: 183-persona-registry-bots-page
    provides: BotGameSettings.personaId already threaded through useBotGame.ts on the frontend (not yet wired to the wire request — that's Plan 03)
provides:
  - "Nullable games.persona_id column (String(30), no CHECK, no backfill)"
  - "StoreBotGameRequest.persona_id (length-bound, optional) persisted only on create"
  - "GET /bots/persona-wins aggregation endpoint, JWT-scoped, excludes draws/losses/NULL-persona/non-flawchess rows"
  - "app.repositories.game_repository.update_bot_game_persona_id + count_wins_by_persona"
affects: [185-02-grid-transpose, 185-03-frontend-win-stars]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Post-insert targeted UPDATE gated on `created` (extends the existing Phase 167 PGN/URL stamp block, same D-11 idempotency guard)"
    - "win_cond copied verbatim from stats_repository.query_results_by_time_control (no third divergent WDL copy)"
    - "Length-bounded client-supplied string field at the Pydantic boundary (mirrors tc_preset's CR-01 pattern)"

key-files:
  created:
    - alembic/versions/20260722_160246_411a8de89c4b_add_persona_id_to_games.py
    - tests/repositories/test_game_repository_persona_wins.py
  modified:
    - app/models/game.py
    - app/schemas/bots.py
    - app/routers/bots.py
    - app/services/store_bot_game_service.py
    - app/repositories/game_repository.py
    - tests/routers/test_bots.py
    - tests/schemas/test_bots.py

key-decisions:
  - "PersonaWinsResponse is a bare `dict[str, int]` type alias, not a wrapped envelope model — matches count_games_by_platform's existing dict-return convention and the frontend research's `useQuery<PersonaWinsResponse>` usage as the JSON body itself"
  - "No CHECK constraint / regex validation on persona_id — length bound only (Field(max_length=30)), per RESEARCH A1/A4: the persona roster is a frontend-only, milestone-evolving TS module, not a DB-tracked entity"
  - "Backend returns raw (uncapped) win counts; the min(wins, 3) display cap is Plan 03's frontend responsibility (RESEARCH A2)"
  - "Migration is a bare metadata-only op.add_column with no server_default and no backfill UPDATE — verified via the acceptance-criteria grep (0 matches for server_default|UPDATE|op.execute after excluding docstring prose)"

patterns-established:
  - "Mutation-verified test coverage: reverting the `is_not(None)` filter or the created-gate was confirmed (then reverted) to make the corresponding test fail — not just grep/symbol-presence checked"

requirements-completed: []  # No formal REQ-IDs for this post-milestone phase (see plan frontmatter)

coverage:
  - id: D1
    description: "persona_id round-trips from POST /bots/games to games.persona_id (persona games only; custom-mode/omitted stays NULL)"
    verification:
      - kind: integration
        ref: "tests/routers/test_bots.py::test_persona_win_round_trips_to_persona_wins_endpoint"
        status: pass
      - kind: integration
        ref: "tests/routers/test_bots.py::test_persona_id_persisted_on_create"
        status: pass
    human_judgment: false
  - id: D2
    description: "GET /bots/persona-wins returns per-user win-only, non-NULL-persona counts, requires auth, no cross-user leakage"
    verification:
      - kind: integration
        ref: "tests/routers/test_bots.py::test_persona_wins_requires_auth"
        status: pass
      - kind: integration
        ref: "tests/routers/test_bots.py::test_persona_wins_scoped_to_authenticated_user"
        status: pass
      - kind: unit
        ref: "tests/repositories/test_game_repository_persona_wins.py::TestCountWinsByPersona"
        status: pass
    human_judgment: false
  - id: D3
    description: "Overlong persona_id (>30 chars) rejected with 422 at the Pydantic boundary"
    verification:
      - kind: unit
        ref: "tests/schemas/test_bots.py::TestStoreBotGameRequestValidation::test_persona_id_over_max_length_rejected"
        status: pass
    human_judgment: false
  - id: D4
    description: "Duplicate resubmit of the same game_uuid does not re-write persona_id (D-11 idempotency preserved)"
    verification:
      - kind: integration
        ref: "tests/routers/test_bots.py::test_persona_id_unchanged_on_idempotent_resubmit"
        status: pass
    human_judgment: false
  - id: D5
    description: "Migration adds a nullable column with no backfill UPDATE and no server_default (pre-existing games earn nothing)"
    verification:
      - kind: other
        ref: "grep -v '^#' <migration> | grep -c -E 'server_default|UPDATE|op.execute' => 0; uv run alembic upgrade head"
        status: pass
    human_judgment: false

duration: 35min
completed: 2026-07-22
status: complete
---

# Phase 185 Plan 01: Backend Persona Win Tracking Summary

**Nullable `games.persona_id` column + `GET /bots/persona-wins` aggregation endpoint, wired end-to-end through the existing Phase 167 store-on-finish path with zero new architectural layers.**

## Performance

- **Duration:** 35 min
- **Started:** 2026-07-22T16:00:36Z
- **Completed:** 2026-07-22T16:36:00Z
- **Tasks:** 2 (tracer + edge coverage)
- **Files modified:** 8 (1 new migration, 1 new test file, 6 modified)

## Accomplishments
- Nullable `games.persona_id` (String(30)) added via a fast metadata-only Alembic migration — no default, no backfill, applies cleanly at head
- `StoreBotGameRequest.persona_id` persists through the existing `if created:` post-insert block in `store_bot_game_service`, preserving D-11 idempotency (a duplicate resubmit never rewrites it)
- `GET /bots/persona-wins` returns per-user, win-only, non-NULL-persona counts via `count_wins_by_persona`, reusing `stats_repository`'s `win_cond` verbatim
- Full edge-case coverage: schema length bounds, idempotent no-rewrite, auth-required, two-user scoping, and aggregation exclusions (draws/losses/NULL-persona/non-flawchess platform) — all mutation-verified (reverting the guard makes the test fail)

## Task Commits

1. **Task 1: Backend persona_id round-trip + win-aggregation endpoint (tracer)** - `fea31faf` (feat)
2. **Task 2: Backend edge coverage — schema bounds, idempotency, aggregation exclusions, auth scoping** - `aa5f7eb7` (test)

## Files Created/Modified
- `alembic/versions/20260722_160246_411a8de89c4b_add_persona_id_to_games.py` - metadata-only nullable column add, no backfill
- `app/models/game.py` - `Game.persona_id` mapped column
- `app/schemas/bots.py` - `_MAX_PERSONA_ID_LENGTH`, `StoreBotGameRequest.persona_id`, `PersonaWinsResponse` (bare `dict[str, int]` alias)
- `app/repositories/game_repository.py` - `update_bot_game_persona_id`, `count_wins_by_persona`
- `app/services/store_bot_game_service.py` - extends the existing `if created:` block with the persona_id write
- `app/routers/bots.py` - `GET /persona-wins` route
- `tests/routers/test_bots.py` - tracer round-trip test + persist-on-create, idempotent-unchanged, auth-required, two-user-scoping tests
- `tests/schemas/test_bots.py` - persona_id None/omitted/30-char/31-char cases
- `tests/repositories/test_game_repository_persona_wins.py` (new) - `count_wins_by_persona` win/draw/loss/NULL-persona/platform/user-scoping cases + `update_bot_game_persona_id` write test

## Decisions Made
- `PersonaWinsResponse` defined as a bare `dict[str, int]` type alias rather than a wrapped Pydantic envelope model, matching `count_games_by_platform`'s existing dict-return convention and the frontend research's direct `useQuery<PersonaWinsResponse>` usage
- No CHECK constraint or regex on `persona_id` — length bound only, since the persona roster is a frontend-only, milestone-evolving TS module (RESEARCH A1)
- Backend returns raw (uncapped) win counts; the `min(wins, 3)` display cap is deferred to Plan 03's frontend (RESEARCH A2)
- Reworded the migration docstring to avoid the literal substrings "UPDATE"/"server_default" in prose (they appeared in a sentence describing what the migration deliberately does NOT do), so the plan's acceptance-criteria grep check returns a clean 0

## Deviations from Plan

None - plan executed exactly as written. Both tasks (tracer + edge coverage) match the plan's `<action>` and `<acceptance_criteria>` verbatim.

## Issues Encountered

None. The tracer's automated verify (`uv run alembic upgrade head && uv run pytest tests/routers/test_bots.py -x -k "persona"`) passed on first run; edge-coverage tests passed on first run; mutation checks (reverting the `is_not(None)` filter and the created-gate) confirmed the tests genuinely enforce those guarantees, then were reverted cleanly (`git checkout --`).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Backend vertical slice is complete and merge-gate clean: full backend suite (`uv run pytest -n auto`) 3541 passed / 21 skipped; `uv run ruff check app/ tests/` clean; no new `ty check` errors (the 3 pre-existing `onnxruntime`/`numpy` unresolved-import errors in `maia_engine.py` are unrelated — missing optional `maia-inference` uv group locally, not introduced by this plan)
- Plan 03 (frontend win stars) can now wire `useBotPersonaWins()` against `GET /bots/persona-wins` and add `persona_id` to `toStoreRequest()` in `useStoreBotGame.ts` — both server-side contracts are stable
- Plan 02 (grid transpose) is independent of this plan (frontend-only, no dependency)

---
*Phase: 185-bots-roster-transpose-win-stars*
*Completed: 2026-07-22*

## Self-Check: PASSED

All created/modified files found on disk; both task commit hashes (`fea31faf`, `aa5f7eb7`) found in `git log`.
