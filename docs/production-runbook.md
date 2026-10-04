# Production Runbook

Operational reference for the FlawChess production server. The root `CLAUDE.md` keeps only the guardrails; the values and commands live here.

> **Deploy only via `bin/deploy.sh`** (or the `/deploy` skill, which wraps the whole PR → CI → deploy → verify flow). Never deploy by direct SSH.

## Server

The production server is reachable via `ssh flawchess` (configured in the user's SSH config). Deploy user is `deploy`, app lives at `/opt/flawchess`.

```bash
# SSH into server
ssh flawchess

# Check services
ssh flawchess "cd /opt/flawchess && docker compose ps"

# View backend logs
ssh flawchess "cd /opt/flawchess && docker compose logs --tail=50 backend"

# Restart backend only
ssh flawchess "cd /opt/flawchess && docker compose restart backend"

# Full restart (data persists in named volumes)
ssh flawchess "cd /opt/flawchess && docker compose down && docker compose up -d"
```

- Domain: flawchess.com (Caddy handles auto-TLS)
- Stack: PostgreSQL 18 + FastAPI/Uvicorn + Caddy 2.11.4
- Hetzner Cloud CPX42, 8 vCPUs, 16 GB RAM + 4 GB swap (`/swapfile`), 160 GB NVMe

## Current prod config

Source of truth, not historical. The repeated 2026 OOM-kills traced to import memory pressure (not Stockfish); the incident-by-incident history lives in git (see `reports/import-stress-test/` and the `docker-compose.yml` db-service comments). The values that matter now:

- **Postgres tuning lives in `docker-compose.yml` db `command:`** — the single source of truth, not migrations, not `postgresql.auto.conf`: `shared_buffers=2GB`, `effective_cache_size=8GB`, `work_mem=16MB`, `maintenance_work_mem=512MB`, `max_connections=30`, `max_wal_size=8GB`, `wal_compression=on`. **Do not raise `shared_buffers` above 2GB** — it amplifies checkpoint flush size and revisits the OOM history.
- **`shm_size: "256m"`** on the db service (a Docker option, NOT a Postgres flag): Docker's 64 MB `/dev/shm` default exhausts under parallel-query DSM segments and surfaces as a misleading `asyncpg.DiskFullError`. A bare `docker compose restart db` does NOT apply a changed `shm_size` — recreate the container (`docker compose up -d db` or `bin/deploy.sh`).
- **SQLAlchemy pool** `10 + 10` overflow; backend/db containers have `mem_limit`/`memswap_limit` set (no swap → contained OOM-restart).
- **`STOCKFISH_POOL_SIZE=6`** in prod (stable; ~368 MB/worker → fits the 4g backend container). Raising to 8 is gated on a 24h soak of API latency + container RSS.

## Umami analytics

Self-hosted Umami (`analytics.flawchess.com`) lives in the `umami` compose service and its own `umami` database on the shared Postgres. Since Phase 229 every identified session carries the account's `users.id` (as text) in `distinct_id`.

### Version pin (D-17)

The image is pinned in `docker-compose.yml` (`ghcr.io/umami-software/umami:3.4.0`, `pull_policy: missing`). The CI deploy runs a plain `docker compose up -d` without a pull, so the pin is the upgrade mechanism: bump the tag and release through `bin/deploy.sh`; `up -d` pulls the tag the server does not have yet and recreates the container. Umami applies its own migrations on start (3.4.0 adds `25_add_annotation` and `26_add_api_key`, both additive). Read-only post-deploy checks:

```bash
# Expect tag 3.4.0
ssh flawchess "cd /opt/flawchess && docker compose images umami"

# Migrations applied, no crash loop
ssh flawchess "cd /opt/flawchess && docker compose logs --tail=50 umami"
```

Cloudflare caches `analytics.flawchess.com/script.js` for up to a day (`cache-control: max-age=86400`), so the tracker a browser runs can lag the server version.

### Deleting an account's analytics (D-18)

When a user requests deletion, delete the app account first, then remove their Umami rows by `distinct_id` (= `users.id` as text) in the app website `0ca19960-2398-4caf-b321-8039708fa7ef`. Table and column names below were checked against the Umami v3.4.0 `prisma/schema.prisma`.

Weekly Train standings (`train_weekly_standings`) need no manual step: deleting the `users` row sets `user_id` to NULL and the `trg_train_weekly_standings_erase_name` trigger replaces the stored name with "Deleted user"; the medal slot stays.

- The read-only `flawchess-umami-db` MCP can run the preview count first.
- Anonymous pre-login sessions carry no `distinct_id` and cannot be matched (they hold no account identifier).
- A session is shared when it links more than one `distinct_id`; this is only possible for sessions recorded before the 3.4.0 upgrade (3.4.0 puts the distinct id into the session hash). For a shared session only this user's `session_link` and `session_data` rows are removed and the session's events stay.

Open an interactive psql (`UMAMI_DB_USER` from `.env`, default `umami`):

```bash
ssh -t flawchess "cd /opt/flawchess && docker compose exec db psql -U umami -d umami"
```

Run the preview block first, replacing the placeholder with the account's `users.id`. Check both counts before running the delete block, which ends in `ROLLBACK` as a dry run: change it to `COMMIT` only after the dry run reports the expected row counts.

```sql
\set did 'REPLACE_WITH_USERS_ID'
\set site '0ca19960-2398-4caf-b321-8039708fa7ef'

-- 1. Preview: how many sessions are linked to this distinct_id
SELECT count(*) FROM (
  SELECT session_id FROM session_link WHERE website_id = :'site' AND distinct_id = :'did'
  UNION
  SELECT session_id FROM session WHERE website_id = :'site' AND distinct_id = :'did'
) s;

-- 2. Shared-session pre-check: sessions in that set that also link another distinct_id
SELECT l.session_id, count(DISTINCT l.distinct_id) AS distinct_ids
FROM session_link l
WHERE l.website_id = :'site'
  AND l.session_id IN (SELECT session_id FROM session_link WHERE website_id = :'site' AND distinct_id = :'did')
GROUP BY l.session_id
HAVING count(DISTINCT l.distinct_id) > 1;
```

Delete block (paste separately, after reviewing the preview):

```sql
-- 3. Delete (one transaction)
BEGIN;

CREATE TEMP TABLE target_sessions ON COMMIT DROP AS
  SELECT session_id FROM session_link WHERE website_id = :'site' AND distinct_id = :'did'
  UNION
  SELECT session_id FROM session WHERE website_id = :'site' AND distinct_id = :'did';

CREATE TEMP TABLE shared_sessions ON COMMIT DROP AS
  SELECT session_id FROM session_link
  WHERE website_id = :'site' AND session_id IN (SELECT session_id FROM target_sessions)
  GROUP BY session_id HAVING count(DISTINCT distinct_id) > 1;

-- Sessions that belong to this user alone get a full delete
CREATE TEMP TABLE exclusive_sessions ON COMMIT DROP AS
  SELECT session_id FROM target_sessions WHERE session_id NOT IN (SELECT session_id FROM shared_sessions);

DELETE FROM event_data WHERE website_id = :'site' AND website_event_id IN (
  SELECT event_id FROM website_event WHERE website_id = :'site' AND session_id IN (SELECT session_id FROM exclusive_sessions));
DELETE FROM revenue        WHERE website_id = :'site' AND session_id IN (SELECT session_id FROM exclusive_sessions);
DELETE FROM session_replay WHERE website_id = :'site' AND session_id IN (SELECT session_id FROM exclusive_sessions);
DELETE FROM heatmap_event  WHERE website_id = :'site' AND session_id IN (SELECT session_id FROM exclusive_sessions);
DELETE FROM website_event  WHERE website_id = :'site' AND session_id IN (SELECT session_id FROM exclusive_sessions);
DELETE FROM session_data   WHERE website_id = :'site' AND session_id IN (SELECT session_id FROM exclusive_sessions);
DELETE FROM session_link   WHERE website_id = :'site' AND session_id IN (SELECT session_id FROM exclusive_sessions);
DELETE FROM session        WHERE website_id = :'site' AND session_id IN (SELECT session_id FROM exclusive_sessions);

-- Shared sessions: only this distinct_id's own rows go, the other user's data stays
DELETE FROM session_data WHERE website_id = :'site' AND distinct_id = :'did';
DELETE FROM session_link WHERE website_id = :'site' AND distinct_id = :'did';
UPDATE session SET distinct_id = NULL WHERE website_id = :'site' AND distinct_id = :'did';

-- Dry run by default: replace ROLLBACK with COMMIT once the counts above look right
ROLLBACK;
```

## Weekly leaderboard medals

Weeks are finalized lazily: the first `GET /train/leaderboard` or `GET /train/medals/unclaimed` after a week's Sunday 24:00 UTC deadline plus 5 minutes of grace freezes that week into `train_weekly_standings` (see `app/services/train_medals.py`). There is no cron or scheduler.

- **Eligibility is read at finalization time, not at the deadline.** `users.leaderboard_hidden` is evaluated live when the week is finalized, so with low traffic (for example the first Monday-morning visit) a user who toggles "Hide me from leaderboards" between the deadline and that first request is excluded, and users below them move up a rank. The reverse also holds. This is a known, accepted behavior; medals are permanent once written.
- **Manual trigger.** `finalize_due_weeks` is idempotent and global: the `train_weekly_finalizations` marker row is the lock, so re-running it never double-awards a week. To finalize without waiting for a visit, load either endpoint once as any registered user.
- **Dev cleanup only.** Deleting a week from `train_weekly_finalizations` (the FK cascades its standings rows) lets the next request finalize it again. Never do this in prod: it discards already-awarded medals.

## Infrastructure notes

- Hetzner Cloud Firewall: inbound TCP 22/80/443 + ICMP from any.
- Alembic migrations run automatically on backend container startup via `deploy/entrypoint.sh`.
- `.env` on the server at `/opt/flawchess/.env` — never commit production secrets.
- Docker BuildKit cache capped at 3 GB by a daily cron (`/etc/cron.d/docker-builder-prune`, 3am UTC) — each deploy rebuilds images on the server, so the cache fills the disk without it. Inspect with `docker system df` (containerd image store, not `/var/lib/docker/buildkit`).
- VAPID key rotation (Web Push, only on suspected key compromise): follow `docs/push-vapid-rotation-runbook.md`.
- Remote Stockfish worker setup: see `REMOTE_WORKER.md`.
- `deploy/Caddyfile` carries an inline Cloudflare IP range list (`trusted_proxies` / `client_ip_headers`, SEED-161 group 1) so Caddy resolves the real visitor IP from `Cf-Connecting-Ip` instead of forwarding the Cloudflare anycast peer address. Refresh it by running `bin/check_cloudflare_ips.sh` and pasting any drift back between the `# BEGIN cloudflare-ranges` / `# END cloudflare-ranges` markers. A stale list does not error, it silently degrades client-IP attribution for requests arriving via a range missing from the list.
- **AI crawlers are allowed on purpose.** ChatGPT referrals (`utm_source=chatgpt.com` plus the chatgpt.com referrer) are a real acquisition channel, so nothing may disallow AI crawlers. The committed `frontend/public/robots.txt` allows everything except `/import`, `/openings`, `/global-stats`, `/api/`. If the served `https://flawchess.com/robots.txt` ever shows a `# BEGIN Cloudflare Managed content` block (per-bot `Disallow: /` lines for GPTBot, ClaudeBot, Google-Extended, CCBot, ... and a `Content-Signal: ... ai-train=no` line), that block is injected at the Cloudflare edge, not by the repo. The dashboard toggle for it is **AI Crawl Control → Signals → Enable Bot Preference Sync**, but as of 2026-09-15 that toggle silently reverts: it only writes `bot_preference_sync_enabled`, while the older `is_robots_txt_managed` flag on the same zone `bot_management` setting stays true and keeps the block. The fix that worked was a direct write of both flags from the dashboard's DevTools console (same-origin, cookie auth; there is no API token configured for this zone):

  ```js
  const u='/api/v4/zones/<zone-id>/bot_management';
  await (await fetch(u,{method:'PUT',credentials:'include',headers:{'content-type':'application/json'},
    body:JSON.stringify({is_robots_txt_managed:false, bot_preference_sync_enabled:false})})).json();
  ```

  The zone id is in the dashboard's own API calls (Network tab). Edge blocking of AI crawlers is a separate per-crawler switch under **AI Crawl Control → Security** and was already off. Verify with `curl -s https://flawchess.com/robots.txt` (the block is gone once the file starts with `User-agent: *` from the repo file; Cloudflare caches robots.txt, so purge it if the old copy lingers).

  **Re-verify after the Sept 2026 crawler-control migration.** Cloudflare announced on 2026-09-15 that zones which had "Managed Robots.txt" enabled are auto-migrated over the following week to the new Search / Training / Agent controls, with Training defaulting to "Disallow AI Training", which is the same robots.txt block by another name. Once the "Block AI Bots" switch is gone from the dashboard, confirm the new controls read Search: Allow, Training: Allow, Agent: Allow and re-run the curl check above; if the block is back, repeat the `bot_management` PUT and purge robots.txt.
