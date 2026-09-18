# Guest activation baseline — Phase 224 (2026-09-17)

**Date recorded:** 2026-09-17
**Window:** `users.created_at >= 2026-06-19` (a 90-day cohort window ending on this note's
date, stated as an explicit range — `2026-06-19` to `2026-09-17` — rather than "last 90
days", so the after-reading uses the identical `:first` bound instead of a value that has
drifted forward with the calendar).

**Sources:**
- Prod PostgreSQL, via the read-only `flawchess-prod-db` MCP role over `bin/prod_db_tunnel.sh`
  (`docs/dev-tooling.md` — dedicated read-only role, separate from the app's read-write
  connection).
- Umami (a separate database on the same prod host; credentials live in `.env`, which the
  secret-read guard denies — read by a human operator, never automated. See `224-RESEARCH.md`
  Open Question 3.)

**S-7 (locked, not re-opened):** Lever A and Lever B are reported as **four separate
numbers below — no combined "guest conversion" number is computed or reported anywhere in
this note, on the Activity dashboard, or in any downstream summary of this phase.**

---

## Lever A, metric 1 — guest import-start rate

**Definition:** of guests (`_GUEST_COHORT`) created in the window, the share who started an
import (`first_import_started_at IS NOT NULL OR linked`), with purged guests excluded
(`games_purged_at IS NULL`) exactly as `fetch_funnel` already does. This is the guest-only
slice of `app/services/activity_queries.py::fetch_funnel`'s stage-2 predicate, reused
verbatim rather than re-spelled, so the before/after readings are provably the same
definition.

```sql
-- Lever A, metric 1: guest import-start rate (guest slice of fetch_funnel's predicate)
WITH u AS (
  SELECT u.id,
         (u.is_guest OR u.promoted_at IS NOT NULL) AS guest,   -- _GUEST_COHORT
         (u.chess_com_username IS NOT NULL OR u.lichess_username IS NOT NULL) AS linked,
         u.first_import_started_at
  FROM users u
  WHERE u.created_at >= CAST(:first AS date)
    AND u.games_purged_at IS NULL
)
SELECT
  count(*) FILTER (WHERE u.guest) AS g_created,
  count(*) FILTER (
    WHERE u.guest AND (u.first_import_started_at IS NOT NULL OR u.linked)
  ) AS g_started
FROM u;
-- :first = '2026-06-19'
```

**Result (read 2026-09-17, prod read-only role via `bin/prod_db_tunnel.sh`):** `g_created = 367`, `g_started = 125` → **34.1%** of surviving guests created since 2026-06-19 started an import. (The cohort is 367 rather than 468 because this metric excludes purged guests, `games_purged_at IS NULL`, exactly as `fetch_funnel` does; Lever B metric 1 below keeps purged guests in its denominator.)

**Comparison (not a measured value — prior published reading, for context only):**
`growth-recommendations-2026-09-15.md` §2 finding 2 (as amended in place by the 2026-09-17 purge-artifact correction) reported
226 of 468 guests started an import over its own 90-day window (48%). That number is NOT
copied into the result row above; it is quoted here only as the pre-phase reference point
the after-reading will be compared against.

---

## Lever A, metric 2 — `/welcome` landings

**Definition:** pageviews (or sessions — state which) whose URL path is `/welcome`, and the
denominator of home visitors who landed on `/` and produced at least one subsequent event,
both over the same window stated above. This is an operator reading from the Umami UI or
its underlying database; it is never fetched automatically (D-10a; Umami credentials are
`.env`-gated and the secret-read guard denies that file).

**Umami query path (commit this so the after-reading uses the identical measurement):**
- UI: `https://analytics.flawchess.com` → the app site (not the stories site) → set the date
  range to `2026-06-19`–`2026-09-17` → Pages report, filter path = `/welcome`, read the
  pageview (or session) count.
- Denominator: the home page's visitors who produced at least one subsequent event in the
  same window (the same basis `growth-recommendations-2026-09-15.md` used for "home
  visitors who clicked anything").
- Equivalent SQL, if reading the Umami Postgres database directly (`docker compose exec db
  psql -U "$UMAMI_DB_USER" umami`, per Task 4's instructions) rather than the UI, so the
  after-reading can reuse this exact filter regardless of which path the operator takes:

```sql
-- Lever A, metric 2: /welcome landings (Umami website_event table, app site only)
SELECT count(*) AS welcome_landings
FROM website_event
WHERE url_path = '/welcome'
  AND created_at BETWEEN '2026-06-19' AND '2026-09-17'
  AND website_id = '0ca19960-2398-4caf-b321-8039708fa7ef';  -- app site, frontend/index.html data-website-id
```

  The denominator (home visitors who produced at least one subsequent event) is read from
  the Umami UI's funnel/behaviour view rather than a single-table query, since it requires
  session-level grouping Umami's UI already computes.

**Result:** `PENDING OPERATOR READING` (Task 4 of this plan — deferred by the user to the end-of-phase test; paste `landings=<N> denominator=<M> basis=<pageviews|sessions>` and this line gets the two numbers, the percentage, the basis and the reading date)

**Comparison (prior published reading, for context only):** 390 of 1,051 home visitors who
clicked anything landed on `/welcome`, per `growth-recommendations-2026-09-15.md` §2 finding
2. This number is unaffected by the 2026-09-17 purge-artifact correction (it is
Umami-sourced, not `import_jobs`-derived).

---

## Lever B, metric 1 — guest promotion rate

**Definition:** of guests (`_GUEST_COHORT`) created in the window, the share with
`promoted_at IS NOT NULL`. This is `app/services/activity_queries.py::fetch_conversion`
verbatim — no new query, because this number is **already on the Activity dashboard's
conversion card today**, so the after-reading needs no hand-run SQL at all.

```sql
-- Lever B, metric 1: guest promotion rate (fetch_conversion, verbatim)
WITH u AS (
  SELECT id, (u.promoted_at IS NOT NULL) AS converted   -- _PROMOTED_GUEST
  FROM users u
  WHERE created_at >= CAST(:first AS date)
    AND (u.is_guest OR u.promoted_at IS NOT NULL)        -- _GUEST_COHORT
),
a AS (SELECT user_id, count(DISTINCT activity_date) AS days FROM user_activity GROUP BY 1)
SELECT count(*) AS sessions,
       count(*) FILTER (WHERE u.converted) AS converted,
       round(avg(coalesce(a.days, 0)) FILTER (WHERE u.converted), 2) AS days_converted,
       round(avg(coalesce(a.days, 0)) FILTER (WHERE NOT u.converted), 2) AS days_guest
FROM u LEFT JOIN a ON a.user_id = u.id;
-- :first = '2026-06-19'
```

**Result (read 2026-09-17, prod read-only role via `bin/prod_db_tunnel.sh`):** `sessions = 468`, `converted = 74` → **15.8%** guest promotion rate; `days_converted = 3.28`, `days_guest = 1.41` distinct active days on average.

---

## Lever B, metric 2 — guest Train sessions completed

**Definition (D-11/D-12):** a "guest Train session completed" is `drill_sessions.status =
'completed'` for a user in `_GUEST_COHORT` created in the window, dated strictly before that
user's `promoted_at` (or forever, for a user never promoted). A promoted user's later
sessions count as registered activity, not guest activity. Purged guests
(`games_purged_at IS NOT NULL`) are excluded, the same predicate the funnel cards use,
footnoted by `fetch_purged_excluded`'s `guest` key. This is a NEW query
(`app/services/activity_queries.py::fetch_guest_train`, added in this plan's Task 1) —
`fetch_train` carries no `users` join at all, so there was nothing to filter.

```sql
-- Lever B, metric 2: guest Train sessions completed (fetch_guest_train, verbatim)
SELECT count(*) AS sessions_completed, count(DISTINCT d.user_id) AS users
FROM drill_sessions d
JOIN users u ON u.id = d.user_id
WHERE u.created_at >= CAST(:first AS date)
  AND (u.is_guest OR u.promoted_at IS NOT NULL)   -- _GUEST_COHORT
  AND u.games_purged_at IS NULL
  AND d.status = 'completed'
  AND d.session_date < COALESCE(u.promoted_at::date, 'infinity'::date);
-- :first = '2026-06-19'
```

**Result (read 2026-09-17, prod read-only role via `bin/prod_db_tunnel.sh`):** `sessions_completed = 0`, `users = 0` — the expected pre-merge answer (see below).

**Expectation:** before this phase merges, Train has never been reachable by a guest
(`_reject_guest` in `app/routers/train.py`, removed by a sibling plan in this phase per S-2).
This reading is therefore expected to be **0 or near 0** — that is the correct pre-merge
answer, not a failed query, and the after-reading is what makes this row meaningful. Do not
mistake a `0` here for a bug.

**How the three prod rows were read:** the gsd-executor subagent that authored this note could not reach the query-only `flawchess-prod-db` MCP tool (subagents inherit only user-scoped MCP servers), so the orchestrating session ran the three committed queries above verbatim on 2026-09-17 through that MCP tool, over `bin/prod_db_tunnel.sh` with the dedicated read-only role, and pasted the raw result columns into the Result lines. No query text was altered; `:first` was bound to `'2026-06-19'` in all three.

---

## What changed, and what it invalidates for the after-reading

- The Umami `signup-cta` event's `train-gate` source **stops being emitted** by this phase
  (the guest gate it instrumented, `_reject_guest`, is removed). Its historical rows stay in
  Umami as a permanent record of the pre-phase state — they must **not** be summed into any
  after-reading total, or the after-reading would double-count a source that no longer
  fires.
- `welcome` survives as a `signup-cta` source (the rewritten `/welcome` page keeps its own
  "Sign up free" button).
- `train-score` is a **new** `signup-cta` source (the Train score-screen sign-up ask added by
  a sibling plan in this phase, S-4/S-7). Its counts have no pre-phase baseline to compare
  against by construction — it did not exist before.

## D-09 acceptance, recorded for this phase's closing

No new abuse guard is added for the widened Train/import audience this phase creates. The
backstop is the existing `guest_create_limiter` (5 guest creates per hour per IP, resolved
from the Cloudflare-forwarded client IP in `app/core/ip_rate_limiter.py` /
`app/routers/auth.py`), plus the one-open-session-per-user partial unique index on
`drill_sessions` and the one-session-per-day compose rule already in
`train_repository.py`. Research (`224-RESEARCH.md` Finding on D-09) verified
`POST /auth/guest` still runs through `guest_create_limiter` with the Cloudflare header path
intact; no guest-specific Train ceiling or filler-only mode was added or is planned.
