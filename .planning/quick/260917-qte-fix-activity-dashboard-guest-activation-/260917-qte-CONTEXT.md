---
quick_id: 260917-qte
date: 2026-09-17
status: locked
---

# Context — Activity dashboard guest-activation undercount

All decisions below were made by the user in session and are LOCKED. Do not revisit.

## Root cause (verified in code, not hypothesis)

`app/services/guest_cleanup_service.py::_purge_guest` (30-day inactivity sweep, wired into
`app/main.py:183` so it IS running in production) and `DELETE /api/games`
(`app/routers/imports.py:495`) both delete a user's `games` AND `import_jobs` rows, while
deliberately keeping the `users` row — including `chess_com_username` / `lichess_username`
(D-05, Phase 187).

Every Activity-dashboard card that derives activation from `import_jobs` or `games` therefore
reads those users as "never imported". This is the entire explanation for the reported
"95 guests link an account and then never import" — it is a measurement artifact, not a UX
dead end.

`_purge_guest` re-checks `is_guest = true` inside the purge transaction, so a promoted guest is
never purged. The deletion is therefore ONE-SIDED: it only ever erases history from
NON-converted guests. `fetch_conversion_compare`'s "Imported games" and "Played the bot" rows
are inflated in one direction as a direct result.

## Constraint: do NOT change the deletion behaviour

Deleting `import_jobs` is load-bearing. `app/services/import_service.py:575` uses
`import_job_repository.get_latest_for_user_platform` as the incremental-fetch cursor. A
surviving job row would make a returning user re-sync only games since the last import,
leaving them with an almost-empty library. The fix belongs in the schema + queries.

## Change 1 — migration: three retained-fact columns on `users`

- `first_import_started_at TIMESTAMPTZ NULL`
- `lifetime_games_imported INTEGER NOT NULL DEFAULT 0`
- `games_purged_at TIMESTAMPTZ NULL`

Backfill in the same migration:

- `lifetime_games_imported` = `COALESCE(SUM(import_jobs.games_imported), 0)` per user
- `first_import_started_at` = `MIN(import_jobs.started_at)` per user
- `games_purged_at` = `users.last_activity` for rows where a platform username is set AND no
  `import_jobs` row exists. Comment in the migration that this is an ESTIMATE — the true purge
  timestamp is unrecoverable — and that it covers BOTH the guest-cleanup population and the
  `DELETE /games` population (registered users are affected too).

Follow the project's DB rules in CLAUDE.md (no native ENUM, explicit FK ondelete, etc.).

## Change 2 — write sites

1. `app/routers/imports.py` (~line 86, `POST /imports`): set `first_import_started_at` to now
   ONLY when it is currently NULL, in the same transaction as `update_platform_username`.
   Take "now" from the `dev_now_utc` dependency, never `datetime.now()` inline (CLAUDE.md).
2. `app/services/import_service.py::_flush_batch_with_progress` (~line 687): increment
   `users.lifetime_games_imported` by `imported` in the SAME session/transaction as the
   existing job-counter persist. This is the only place games actually land.
3. `app/services/guest_cleanup_service.py::_purge_guest` AND the `DELETE /games` handler
   (`app/routers/imports.py:495`): stamp `games_purged_at` = now in the same transaction as
   the deletes.

## Change 3 — `app/services/activity_queries.py`

Exclude purged users (`games_purged_at IS NOT NULL`) from the cohort of every game-derived
card, and return the excluded count per cohort so the page can footnote it.

Affected: `fetch_funnel` (~437), `fetch_time_to_import` (~487), `fetch_stickiness` (~527),
`fetch_conversion_compare` (~592).

`fetch_conversion` (~558) is NOT affected — `promoted_at` survives the purge. Leave it alone.

- `fetch_funnel`: DROP the "Chess account linked" stage entirely. It is a phantom stage:
  `linked` is written at `imports.py:86`, one line before the `import_jobs` row is created at
  `:90`, inside the same request — it is not a distinct user action. New stages:
  `Account created` / `Import started` / `At least 1 game imported` / `{N}+ games imported`.
  Predicates:
  - started  = `first_import_started_at IS NOT NULL OR linked`
    (the `OR linked` is the EXACT legacy fallback for pre-migration rows, because `linked`
    provably implies an import was started)
  - imported = `lifetime_games_imported > 0`
  - library  = live `games` count >= `FUNNEL_GAMES_THRESHOLD`
- `fetch_time_to_import`: source the first-import timestamp from
  `users.first_import_started_at` instead of `MIN(import_jobs.started_at)`.
- `fetch_stickiness` and `fetch_conversion_compare`: use `lifetime_games_imported > 0`
  instead of summing `import_jobs`.

## Change 4 — cohort-split consistency (approved in the same change)

`fetch_funnel` and `fetch_time_to_import` split cohorts on raw `u.is_guest`, while the
conversion queries use `_GUEST_COHORT = "(u.is_guest OR u.promoted_at IS NOT NULL)"`. Switch
both to `_GUEST_COHORT` so a promoted guest stays in the guest funnel instead of jumping to
the registered funnel mid-cohort. The commit message must note that this shifts historical
numbers on both cards.

## Frontend

Update `frontend/src/pages/activity/render.js` (and `charts.js` if the funnel chart needs it)
for the dropped funnel stage, and render a footnote showing the excluded-purged count per
cohort. Follow `frontend/CLAUDE.md`.

## Tests

- `tests/test_guest_cleanup_service.py`: assert `games_purged_at` is stamped by the purge and
  that the username columns still survive it.
- `tests/test_imports_router.py`: assert `DELETE /games` stamps `games_purged_at`; assert
  `first_import_started_at` is set on the first import and is NOT overwritten by a later one.
- Activity-queries tests: a purged user must be excluded from the funnel, time-to-import,
  stickiness and conversion-compare cohorts; a promoted guest must count in the GUEST funnel.

## Gate

Run the full pre-merge gate from CLAUDE.md at the end. Do NOT run `bin/reset_db.sh`.
Work against the existing dev DB.
