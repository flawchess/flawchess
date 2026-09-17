---
phase: quick-260917-qte
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - alembic/versions/<new_revision>.py
  - app/models/user.py
  - app/repositories/user_repository.py
  - app/routers/imports.py
  - app/services/import_service.py
  - app/services/guest_cleanup_service.py
  - app/services/activity_queries.py
  - app/services/activity_stats.py
  - frontend/src/pages/activity/render.js
  - frontend/src/pages/activity/ActivityPage.tsx
  - tests/test_guest_cleanup_service.py
  - tests/test_imports_router.py
  - tests/test_admin_activity_stats.py
autonomous: true
requirements: [QTE-01, QTE-02, QTE-03, QTE-04]

estimate:
  tokens: 95000
  raw_tokens: 95000
  tasks: 5
  confidence: low

must_haves:
  truths:
    - "A user whose games+import_jobs were purged (guest cleanup or DELETE /games) is excluded from the funnel, time-to-import, stickiness and conversion-compare cohorts instead of counting as 'never imported'."
    - "The Activity page footnotes how many registered accounts and how many guest sessions were excluded as purged, per cohort."
    - "The funnel has four stages; 'Chess account linked' is gone."
    - "A promoted guest stays in the GUEST funnel and GUEST time-to-import cohort, not the registered one."
    - "Deletion behaviour is unchanged: guest cleanup and DELETE /games still delete games AND import_jobs."
    - "users.lifetime_games_imported, users.first_import_started_at and users.games_purged_at survive a purge and are backfilled for existing rows."
  artifacts:
    - alembic/versions/<new_revision>.py
    - app/models/user.py
    - app/services/activity_queries.py
    - frontend/src/pages/activity/render.js
  key_links:
    - "import_service._flush_batch_with_progress increments users.lifetime_games_imported in the SAME session as the job-counter persist."
    - "activity_stats.build_payload wires fetch_purged_excluded into Payload.purged_excluded, which render.js reads for the footnote."
---

<objective>
Fix the Activity dashboard's guest-activation undercount. Guest 30-day cleanup and
`DELETE /api/games` both delete a user's `games` AND `import_jobs` rows while keeping the
`users` row, so every game-derived dashboard card reads purged users as "never imported".
The purge is one-sided (a promoted guest is never purged), so the numbers are skewed in one
direction.

Deletion behaviour is load-bearing and must NOT change: `import_service.py:575` uses
`import_job_repository.get_latest_for_user_platform` as the incremental-fetch cursor, so a
surviving job row would leave a returning user with an almost-empty library. The fix lives in
the schema + the queries.

Purpose: turn a measurement artifact ("95 guests link an account and then never import") back
into a real number.
Output: three retained-fact columns on `users`, four write sites stamping them, four activity
queries reading them, and a per-cohort excluded-purged footnote on the page.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
@frontend/CLAUDE.md
@.planning/quick/260917-qte-fix-activity-dashboard-guest-activation-/260917-qte-CONTEXT.md

@app/services/activity_queries.py
@app/services/activity_stats.py
@app/services/guest_cleanup_service.py
@app/routers/imports.py
@app/models/user.py
@app/repositories/user_repository.py
@frontend/src/pages/activity/render.js
@frontend/src/pages/activity/ActivityPage.tsx
</context>

<planning_notes>
Decomposed horizontally (schema -> writes -> reads -> UI -> gate) rather than as a tracer
slice. The architecture is already proven end to end: this is three additive columns on an
existing table feeding four existing query functions that already render through an existing
payload. A thin vertical slice would add no information and would fragment the four write
sites across tasks.

Verified line numbers (current `main`, 2026-09-17) — CONTEXT.md's were approximate:
- `app/routers/imports.py:52` `@router.post("")`, `:86` `update_platform_username`,
  `:89` `await session.commit()`, `:105` `create_import_job`.
- `app/routers/imports.py:497` `@router.delete("/games")`, `:498` `delete_all_games`,
  `:520` `delete(ImportJob)`, `:528` `await session.commit()`.
- `app/services/import_service.py:676` `_flush_batch_with_progress`, `:682` `_flush_batch`,
  `:696` `await session.commit()`.
- `app/services/guest_cleanup_service.py:64` `_purge_guest`, `:97` `delete(ImportJob)`,
  `:128` `reset_backfill_cursors`, `:129` `await session.commit()`.
- `app/services/activity_queries.py:52` `_PROMOTED_GUEST`, `:58` `_GUEST_COHORT`,
  `:61` `class Payload`, `:437` `fetch_funnel`, `:487` `fetch_time_to_import`,
  `:527` `fetch_stickiness`, `:558` `fetch_conversion` (UNTOUCHED),
  `:591` `fetch_conversion_compare`.
- `app/services/activity_stats.py:88-92` payload wiring.
- `frontend/src/pages/activity/render.js:28-29` module state, `:40-42` `apply()`,
  `:155-169` caveat/header spans, `:225-232` `renderFunnelCard`, `:234-247`
  `renderTtiStickCards`.
- `frontend/src/pages/activity/ActivityPage.tsx:349-372` funnel card,
  `:544-579` the `<ul className="caveats">` footer.
- Current alembic head: `c3a9e1f70003`.

One implementation choice inside CONTEXT.md's Change 3 ("return the excluded count per cohort
so the page can footnote it"): rather than changing the return shape of all four query
functions (and the chart helpers that consume them), ONE new `fetch_purged_excluded` returns
`{"registered": N, "guest": N}` over the same `users.created_at >= window_start` cohort all
four cards use. One count genuinely covers all four cards, and no existing return shape or
chart helper has to change.
</planning_notes>

<tasks>

<task type="auto">
  <name>Task 1: Add the three retained-fact columns to users, with backfill</name>
  <files>app/models/user.py, alembic/versions/&lt;generated&gt;.py</files>
  <action>
Add three columns to `User` in `app/models/user.py`, below `promoted_at` (currently ends at
line 51), each with a comment explaining that it is a RETAINED FACT — it deliberately
survives the games/import_jobs purge that `guest_cleanup_service._purge_guest` and
`DELETE /api/games` perform, so the Activity dashboard can still tell "never imported" from
"imported, then purged":

- `first_import_started_at: Mapped[datetime | None]` — `DateTime(timezone=True)`, nullable,
  `default=None`.
- `lifetime_games_imported: Mapped[int]` — `Integer`, `nullable=False`,
  `server_default=text("0")`, `default=0`. INTEGER, not BIGINT (CLAUDE.md column-type rule).
- `games_purged_at: Mapped[datetime | None]` — `DateTime(timezone=True)`, nullable,
  `default=None`.

Import `Integer` from sqlalchemy alongside the existing `Boolean, DateTime, String, func, text`.
No ForeignKey and no ENUM are involved here (these are scalar columns on `users`, not
references), so the FK/ENUM rules in CLAUDE.md's "Database design rules" do not apply.

Then generate the migration with `uv run alembic revision --autogenerate -m "quick qte users
import retention facts"` and hand-edit the generated file:

- Confirm `down_revision` is `'c3a9e1f70003'` (the current head). Do not chain from anything else.
- Keep the three autogenerated `op.add_column` calls; confirm the `lifetime_games_imported`
  one carries `nullable=False` and `server_default=sa.text("0")`.
- Remove any unrelated drift the autogenerator picked up — this migration touches `users` only.
- Append a backfill block to `upgrade()` AFTER the add_columns, as two `op.execute` statements:

  (a) per-user aggregate from `import_jobs`, setting `lifetime_games_imported` to
  `COALESCE(SUM(games_imported), 0)` and `first_import_started_at` to `MIN(started_at)`,
  joined via a subquery grouped by `user_id`. Users with no jobs keep the `0` / `NULL`
  defaults.

  (b) the purge estimate: set `games_purged_at = users.last_activity` for rows where a
  platform username is set (`chess_com_username IS NOT NULL OR lichess_username IS NOT NULL`)
  AND no `import_jobs` row exists (`NOT EXISTS`).

- Put a comment above (b) recording, in prose: that this is an ESTIMATE because the true purge
  timestamp is unrecoverable; that it covers BOTH the guest-cleanup population and the
  `DELETE /games` population, so registered users are affected too; and that a row whose
  `last_activity` is NULL stays NULL here and is therefore NOT treated as purged by the
  dashboard queries (an accepted, documented residual, since `last_activity` is the only
  timestamp available to stand in).

- `downgrade()` drops the three columns in reverse order.

Write the module docstring in the style of
`alembic/versions/20260913_144712_7d6bb75aae54_phase_222_train_onboarding_seen.py`: what the
columns are, why they exist, and what the backfill does.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/flawchess &amp;&amp; uv run alembic upgrade head &amp;&amp; uv run alembic heads &amp;&amp; uv run ty check app/ &amp;&amp; uv run pytest tests/test_guest_cleanup_service.py -q -x</automated>
  </verify>
  <done>
`uv run alembic heads` reports exactly one head, the new revision. `uv run alembic upgrade
head` applies cleanly against the existing dev DB (no reset). `uv run alembic downgrade -1`
followed by `upgrade head` also works. The three columns exist on `users`, and the existing
guest-cleanup suite still passes against the refreshed test template.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Stamp the three columns at all four write sites</name>
  <files>app/repositories/user_repository.py, app/routers/imports.py, app/services/import_service.py, app/services/guest_cleanup_service.py, tests/test_imports_router.py, tests/test_guest_cleanup_service.py</files>
  <behavior>
    - First `POST /api/imports` for a user sets `users.first_import_started_at`; a second, later `POST /api/imports` leaves the original value untouched.
    - `DELETE /api/games` stamps `users.games_purged_at` and leaves `chess_com_username` / `lichess_username` intact.
    - `guest_cleanup_service._purge_guest` stamps `users.games_purged_at` and leaves both platform username columns intact.
    - `_purge_guest` on a guest who became ineligible mid-tick (the `still_eligible is None` early return) stamps nothing.
  </behavior>
  <action>
Four write sites. Do NOT change any deletion behaviour — `import_jobs` rows are still deleted
at both purge sites; that is the incremental-fetch cursor reset and it stays.

1. `app/repositories/user_repository.py` — add
   `stamp_first_import_started_at(session, user_id, now) -> None` next to
   `update_platform_username` (line 71). It issues
   `update(User).where(User.id == user_id, User.first_import_started_at.is_(None)).values(first_import_started_at=now)`
   then `await session.flush()`. The `IS NULL` predicate in the WHERE clause is what makes it
   first-write-wins; do not read-then-write. Also add
   `stamp_games_purged_at(session, user_id, now) -> None` doing the unconditional equivalent
   for `games_purged_at`. Both take the instant as a parameter — neither reads a clock.

2. `app/routers/imports.py::start_import` (line 53) — add
   `now_utc: Annotated[datetime.datetime, Depends(dev_now_utc)]` to the signature and
   `from app.core.dev_clock import dev_now_utc` plus `import datetime` to the imports. Call
   `user_repository.stamp_first_import_started_at(session, user_id, now_utc)` immediately
   after the `update_platform_username` call (line 86-88) and BEFORE the `await
   session.commit()` at line 89, so it lands in the same transaction as the username write.
   Take "now" from the dependency, never `datetime.now()` inline (CLAUDE.md). The
   already-active-job early return above (line 74) correctly skips this: an active job means
   the first import already started and already stamped.

3. `app/routers/imports.py::delete_all_games` (line 498) — add the same `now_utc` dependency
   parameter and call `user_repository.stamp_games_purged_at(session, user.id, now_utc)`
   after the `reset_backfill_cursors` call and before the `await session.commit()` at line
   528, so the stamp commits atomically with the deletes.

4. `app/services/import_service.py::_flush_batch_with_progress` (line 676) — inside the
   existing `async with async_session_maker() as session` block, after
   `imported = await _flush_batch(...)` (line 682) and before the commit at line 696,
   increment the user's counter in that SAME session:
   `update(User).where(User.id == job.user_id).values(lifetime_games_imported=User.lifetime_games_imported + imported)`.
   Guard it with `if imported:` so a zero-import batch takes no row lock. `update` is already
   imported at line 23; add `from app.models.user import User` next to the existing
   `from app.models.game import Game` (line 28). Add a comment noting this is the only place
   games actually land, and that the counter is deliberately a lifetime total that survives a
   later purge.

5. `app/services/guest_cleanup_service.py::_purge_guest` (line 64) — after the
   `reset_backfill_cursors` call (line 128) and before `await session.commit()` (line 129),
   call `user_repository.stamp_games_purged_at(session, guest_id, datetime.now(timezone.utc))`.
   A background loop is not an endpoint, so the `dev_now_utc` dependency does not apply here;
   `datetime.now(timezone.utc)` matches how this module already reads the clock for `cutoff`
   (line 85). Import `user_repository` alongside the existing
   `from app.repositories import game_repository, user_import_settings_repository` (line 30).
   Add a comment stating that this stamp is what lets the Activity dashboard tell a purged
   guest from one who never imported, and that it must stay inside the same transaction as
   the deletes.

Tests — write them before the implementation and watch them fail:

- `tests/test_guest_cleanup_service.py`: a test in `TestPurgeGuestEndToEnd` asserting that
  after `_purge_guest`, the user row has a non-NULL `games_purged_at` and both
  `chess_com_username` and `lichess_username` still hold their pre-purge values. Reuse the
  file's existing `_seed_eligible_guest_with_game` (line 492) / `_set_last_activity` (line
  481) helpers and the `real_session_maker` fixture. Add a second test asserting the
  ineligible-mid-tick early return (line 94-95) leaves `games_purged_at` NULL.
- `tests/test_imports_router.py`: in `TestDeleteAllGamesCursorReset`, assert `DELETE
  /api/games` stamps `games_purged_at`. In `TestPostImports`, assert the first `POST
  /api/imports` sets `first_import_started_at` and that a later `POST /api/imports` (after the
  first job is no longer active) does NOT overwrite it — pin the original timestamp value.
  Follow the existing `POST /api/imports` request shape used from line 139 onward.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/flawchess &amp;&amp; uv run pytest tests/test_guest_cleanup_service.py tests/test_imports_router.py -q -x &amp;&amp; uv run ty check app/ tests/</automated>
  </verify>
  <done>
All four write sites stamp inside the existing transaction; no new `session.commit()` was
added anywhere. The new tests pass and the pre-existing tests in both files still pass. No
`delete(ImportJob)` statement was removed or weakened.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Read the retained facts in activity_queries, exclude purged users</name>
  <files>app/services/activity_queries.py, app/services/activity_stats.py, tests/test_admin_activity_stats.py</files>
  <behavior>
    - A user with `games_purged_at` set is absent from the funnel, time-to-import, stickiness and conversion-compare cohorts (all counts drop by one, including the `Account created` stage).
    - `fetch_purged_excluded` returns the per-cohort count of those excluded users, split registered vs guest.
    - A promoted guest (`is_guest=false`, `promoted_at` set) counts in the GUEST columns of the funnel and time-to-import, not the registered ones.
    - The funnel returns exactly four rows and no row is labelled "Chess account linked".
    - A user with `lifetime_games_imported > 0` but zero surviving `import_jobs` rows still counts as an importer in the funnel, stickiness and conversion-compare.
  </behavior>
  <action>
All edits in `app/services/activity_queries.py`. `fetch_conversion` (line 558) is NOT affected
— `promoted_at` survives the purge — so leave it exactly as it is.

Shared shape change: each affected `u` CTE gains `AND u.games_purged_at IS NULL` on its
`WHERE`, and selects `FROM users u` (aliased) so the `_GUEST_COHORT` fragment at line 58 can
be interpolated the way `fetch_conversion` already does it.

- `fetch_funnel` (line 437): drop the `j` CTE entirely. Rebuild the `u` CTE as
  `SELECT u.id, ({_GUEST_COHORT}) AS guest, (u.chess_com_username IS NOT NULL OR
  u.lichess_username IS NOT NULL) AS linked, u.first_import_started_at,
  u.lifetime_games_imported FROM users u WHERE u.created_at >= CAST(:first AS date) AND
  u.games_purged_at IS NULL`. Keep the `g` CTE (live `games` count) unchanged. Filter the
  outer aggregate on `u.guest` / `NOT u.guest` instead of `u.is_guest`. Stages drop from five
  to four — delete the `r_linked`/`g_linked` columns and the `"Chess account linked"` label.
  Predicates:
    - started  = `(u.first_import_started_at IS NOT NULL OR u.linked)`
    - imported = `u.lifetime_games_imported > 0`
    - library  = `coalesce(g.games, 0) >= :threshold` (unchanged)
  The final list comprehension indexes shift from `row[i + 5]` to `row[i + 4]`.
  Keep the existing docstring's cohort-window note (D3) and add two sentences: why the linked
  stage is gone (`linked` is written one line before the `import_jobs` row is created, inside
  the same request, so it was never a distinct user action), and why `OR u.linked` is kept
  as the legacy fallback for pre-migration rows.

- `fetch_time_to_import` (line 487): drop the `j` CTE and the LEFT JOIN entirely. The `u` CTE
  becomes `SELECT u.id, ({_GUEST_COHORT}) AS guest, u.created_at, u.first_import_started_at
  FROM users u WHERE u.created_at >= CAST(:first AS date) AND u.games_purged_at IS NULL`, and
  every `j.first_job` in the bucket predicates becomes `u.first_import_started_at`. The
  `NOT u.is_guest` / `u.is_guest` filters become `NOT u.guest` / `u.guest`. Five buckets and
  the `row[i + 5]` indexing are unchanged.

- `fetch_stickiness` (line 527): `u` CTE becomes `SELECT u.id, u.is_guest,
  (u.lifetime_games_imported > 0) AS imported FROM users u WHERE u.created_at >= CAST(:first
  AS date) AND u.games_purged_at IS NULL`; drop the `j` CTE and its join; the outer SELECT
  groups on `u.is_guest, u.imported`. This card KEEPS raw `is_guest` — CONTEXT.md's Change 4
  names only `fetch_funnel` and `fetch_time_to_import` for the `_GUEST_COHORT` switch. Do not
  over-apply it here.

- `fetch_conversion_compare` (line 591): add `u.lifetime_games_imported` to the `u` CTE's
  select list and `AND u.games_purged_at IS NULL` to its WHERE; drop the `j` CTE and its
  join; replace both `coalesce(j.total, 0) > 0` predicates with `u.lifetime_games_imported >
  0`. Add a comment recording that this card's denominators now differ from `fetch_conversion`
  (line 558), which deliberately keeps every guest because `promoted_at` survives a purge.

- New `fetch_purged_excluded(conn, window_start) -> dict[str, int]`, placed next to
  `fetch_funnel`. One query over `users u WHERE u.created_at >= CAST(:first AS date) AND
  u.games_purged_at IS NOT NULL`, returning
  `count(*) FILTER (WHERE NOT ({_GUEST_COHORT}))` and `count(*) FILTER (WHERE
  {_GUEST_COHORT})` as `{"registered": int, "guest": int}`. Docstring: this is the count the
  four game-derived cards above dropped, per cohort, so the page can footnote it. Note that
  one count covers all four cards because they share the same `users.created_at` cohort window.

- `class Payload` (line 61): add `purged_excluded: dict[str, int]` after `conversion_compare`.
- `app/services/activity_stats.py::build_payload` (line 68-93): add
  `purged_excluded=await queries.fetch_purged_excluded(conn, window.window_start),` after the
  `conversion_compare=` line.

Tests in `tests/test_admin_activity_stats.py`:
- Add `purged_excluded={}` to `fake_payload` (line 102) so the TypedDict stays schema-complete.
- New direct-query tests against `test_engine`, following the baseline-delta pattern
  `test_fetch_train_funnel_seeded_cohort` (line 620) uses — snapshot each `fetch_*` result
  BEFORE seeding and assert on the delta, because the shared engine carries rows from other
  tests. Seed four users inside a fixed window: a plain registered importer, a purged user
  (platform username set, `games_purged_at` stamped, `lifetime_games_imported > 0`, no
  `import_jobs` rows), a promoted guest (`is_guest=false`, `promoted_at` set), and a guest who
  never imported. Assert: the purged user adds nothing to `fetch_funnel`, `fetch_time_to_import`,
  `fetch_stickiness` or `fetch_conversion_compare`; the promoted guest lands in the GUEST
  column of `fetch_funnel` and `fetch_time_to_import`; `fetch_purged_excluded` counts the
  purged user under the right cohort key; `fetch_funnel` returns 4 rows and no label equals
  "Chess account linked".
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/flawchess &amp;&amp; uv run pytest tests/test_admin_activity_stats.py -q -x &amp;&amp; uv run ty check app/ tests/ &amp;&amp; grep -n 'import_jobs' app/services/activity_queries.py</automated>
  </verify>
  <done>
The new and pre-existing `tests/test_admin_activity_stats.py` tests pass. `ty` is clean. The
`grep` shows `import_jobs` surviving ONLY in `fetch_imports` (line 382-396) — the four
cohort queries no longer aggregate it. `fetch_conversion` is byte-identical to before.
  </done>
</task>

<task type="auto">
  <name>Task 4: Wire the dropped stage and the excluded-purged footnote into the page</name>
  <files>frontend/src/pages/activity/render.js, frontend/src/pages/activity/ActivityPage.tsx</files>
  <action>
`frontend/src/pages/activity/render.js`:
- Add `PURGED` to the module-level state declaration (line 28-29, alongside `CONVCMP`),
  initialised to `null`.
- In `apply(payload)` (line 31-43), add `PURGED=payload.purged_excluded;`.
- `renderFunnelCard()` (line 225-232) needs no index arithmetic change — it maps over
  `FUNNEL` and only special-cases index 0, so four rows render as-is. Confirm this by reading
  it rather than editing blind.
- In the function that fills the caveat/header spans (the block around line 155-169 that sets
  `#cav-funnel`, `#cav-promoted`, `#cav-features`), fill two new spans from `PURGED`:
  `#cav-purged-reg` and `#cav-purged-guest`. Degrade to the file's existing `DASH` constant
  (line 16) when `PURGED` is falsy, matching how the rest of the file handles a missing
  denominator — never print `undefined`.

`frontend/src/pages/activity/ActivityPage.tsx`:
- Funnel card note (line 350-354): the copy currently says "Linking a chess.com or lichess
  username is the gate: once it is linked, the import fires within seconds and almost never
  fails." That sentence describes the stage this change deletes. Replace it with copy that
  describes the four remaining stages. Do not leave stale prose referring to a linked stage.
- Add one `<li>` to the `<ul className="caveats">` footer (line 545-579), in the same
  `<b>headline</b> then explanation` shape as its siblings. It states that accounts whose game
  history was purged (guest 30-day cleanup, or a user deleting their games) are excluded from
  the funnel, time-to-import, stickiness and converter-comparison cards, because their
  `import_jobs` rows are gone and they would otherwise read as "never imported". It carries
  the two counts via `<span id="cav-purged-reg">—</span>` and
  `<span id="cav-purged-guest">—</span>`, initialised to the em-dash like the sibling spans.

Follow `frontend/CLAUDE.md`: this page uses its own `styles.css` classes (`.note`,
`.caveats`, `.eyebrow`), not Tailwind, so keep using them — do not introduce Tailwind
utilities or a `text-xs`. No new interactive element is added, so no new `data-testid` is
required. Do not touch `charts.js`: the `funnel()` helper is row-count agnostic and no chart
return shape changed.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/flawchess/frontend &amp;&amp; npm run lint &amp;&amp; npm test -- --run &amp;&amp; npm run build</automated>
  </verify>
  <done>
`npm run lint`, `npm test -- --run` and `npm run build` all pass (the build is what
type-checks the TSX — lint and vitest do not). The funnel card copy no longer mentions
linking a username as a stage, and the caveats list has a purged-exclusion entry whose two
count spans are filled by `render.js` from `payload.purged_excluded`.
  </done>
</task>

<task type="auto">
  <name>Task 5: Full pre-merge gate</name>
  <files>(no new files — gate only; commit any formatter/lint output)</files>
  <action>
Run the complete pre-merge gate from CLAUDE.md, in order, and resolve every finding. Do NOT
run `bin/reset_db.sh` — work against the existing dev DB, which Task 1's migration already
upgraded.

Run each of:
  uv run ruff format app/ tests/ scripts/ analysis/
  uv run ruff check . --fix
  uv run ty check app/ tests/ scripts/
  uv run --project analysis --with ty ty check analysis/
  uv run python scripts/check_function_size.py app/ --fail-over-depth 4 --fail-over-loc 200
  uv run pytest -n auto -x
  ( cd frontend && npm run lint && npm test -- --run )

Plus `cd frontend && npm run build`, since this change touches TSX and the shared payload
shape and neither lint nor vitest type-checks.

If any step modifies files, commit that with a `style(...)` / `chore(...)` prefix, separate
from the feature commits.

The final feature commit message must record that the `_GUEST_COHORT` switch in `fetch_funnel`
and `fetch_time_to_import` shifts historical numbers on both cards: a promoted guest now stays
in the guest funnel instead of jumping to the registered funnel mid-cohort.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/flawchess &amp;&amp; uv run ruff format --check app/ tests/ scripts/ analysis/ &amp;&amp; uv run ruff check . &amp;&amp; uv run ty check app/ tests/ scripts/ &amp;&amp; uv run python scripts/check_function_size.py app/ --fail-over-depth 4 --fail-over-loc 200 &amp;&amp; uv run pytest -n auto -x -q</automated>
  </verify>
  <done>
Every gate step exits 0. The frontend leg (`npm run lint`, `npm test -- --run`,
`npm run build`) also passes. Working tree is clean apart from intended commits, and the
commit message notes the historical-number shift from the `_GUEST_COHORT` switch.
  </done>
</task>

</tasks>

<verification>
- `uv run alembic heads` shows one head, the new revision, chained from `c3a9e1f70003`.
- `grep -n 'import_jobs' app/services/activity_queries.py` matches only inside `fetch_imports`.
- `grep -n 'Chess account linked' app/ frontend/src -r` returns nothing.
- `grep -n 'delete(ImportJob)' app/routers/imports.py app/services/guest_cleanup_service.py`
  still matches both sites — deletion behaviour is unchanged.
- Full pre-merge gate green.
</verification>

<success_criteria>
- A purged user (guest cleanup or `DELETE /games`) no longer counts as "never imported" on the
  funnel, time-to-import, stickiness or converter-comparison cards, and is instead footnoted
  as excluded, per cohort.
- The funnel has four stages and the phantom "Chess account linked" stage is gone.
- A promoted guest is counted in the guest cohort on the funnel and time-to-import cards.
- `import_jobs` and `games` are still deleted at both purge sites; the incremental-fetch
  cursor behaviour in `import_service.py:575` is untouched.
</success_criteria>

<output>
Create `.planning/quick/260917-qte-fix-activity-dashboard-guest-activation-/260917-qte-SUMMARY.md` when done.
</output>
