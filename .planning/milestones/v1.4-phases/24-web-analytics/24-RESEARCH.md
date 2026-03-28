# Phase 24: Web Analytics - Research

**Researched:** 2026-03-22
**Domain:** Self-hosted web analytics (Umami), Docker Compose, Caddy reverse proxy, React SPA tracking
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Umami (self-hosted). Not Plausible CE, not GoAccess, not Cloudflare Web Analytics, not Plausible Cloud.
- **D-02:** Shared PostgreSQL instance — Umami gets its own database (`umami`) within the existing `db` container. No separate PostgreSQL container.
- **D-03:** Subdomain at `analytics.flawchess.com` — Caddy handles auto-TLS.
- **D-04:** Dashboard is private (login required).
- **D-05:** Umami's built-in user/password auth. Default admin account on first run.

### Claude's Discretion
- Umami version and Docker image selection
- Caddy reverse proxy config details for the subdomain
- Data retention configuration
- Environment variable naming conventions
- Umami tracking script integration in the React frontend

### Deferred Ideas (OUT OF SCOPE)
- Update privacy policy page (`/privacy`) to mention analytics — do after analytics is live
- Public analytics dashboard — revisit later if desired
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ANLY-01 | Site owner can view page visit counts and trends over time | Umami built-in dashboard with time-series charts |
| ANLY-02 | Site owner can see top pages/routes by visit count | Umami built-in Pages report |
| ANLY-03 | Site owner can see visitor referrer sources | Umami built-in Referrers report |
| ANLY-04 | Analytics collection respects user privacy (no cookie consent required) | Umami is cookieless by design; no GDPR consent needed |
| ANLY-05 | Analytics solution has minimal server resource footprint (RAM/CPU) | Umami uses ~100-250 MB RAM at low traffic; NODE_OPTIONS cap available |
</phase_requirements>

---

## Summary

Umami is a self-hosted, privacy-first analytics platform. It stores no cookies and collects no personal data, which is why no GDPR cookie consent banner is required. Version 2 (Docker image tag `postgresql-latest`) is the stable production release; version 3 launched in late 2025 with cohorts and segmentation but is newer. The recommended approach is to pin to a specific version tag rather than `latest` for reproducible deploys.

Umami runs as a Node.js application on port 3000 and requires a single environment variable: `DATABASE_URL`. It manages its own schema via Prisma migrations on first boot — no manual `CREATE TABLE` needed. The only prerequisite is that the target database exists in PostgreSQL.

For this project, Umami will be added as a fourth Docker Compose service (`umami`) alongside `db`, `backend`, and `caddy`. Caddy will proxy `analytics.flawchess.com` → `umami:3000`. The existing `db` container needs a new database (`umami`) and a dedicated user created via an init SQL script or one-time `psql` command on the production server. The React frontend embeds a `<script>` tag in `frontend/index.html`. Umami's tracker intercepts `pushState`/`replaceState` calls via the History API, so React Router SPA navigation is tracked automatically without extra React code.

**Primary recommendation:** Use `ghcr.io/umami-software/umami:postgresql-v2.13.2` (or the latest stable v2.x tag), share the existing `db` container with a new `umami` database, proxy through Caddy, and insert the tracking `<script>` into `frontend/index.html`.

---

## Standard Stack

### Core
| Component | Version | Purpose | Why Standard |
|-----------|---------|---------|--------------|
| Umami | `postgresql-v2.13.2` (latest stable v2) | Analytics server | Privacy-first, PostgreSQL native, low RAM |
| Docker image | `ghcr.io/umami-software/umami:postgresql-latest` | Container | Official image from umami-software |
| PostgreSQL | 18 (existing `db` container) | Data store | Already present; Umami supports pg 12.14+ |

> **Version note:** Umami v3 launched November 2025. It is newer and includes cohorts/segmentation. For a low-traffic site focused on stability, v2 is safer. If using `postgresql-latest`, verify which version it resolves to at deploy time. Consider pinning to a specific digest or tag.

### Supporting
| Component | Version | Purpose | When to Use |
|-----------|---------|---------|-------------|
| Caddy 2.x | existing | Reverse proxy + auto-TLS for `analytics.flawchess.com` | Already in stack |
| `NODE_OPTIONS=--max-old-space-size=256` | n/a | Cap Node.js heap | Set in umami service env to guard against memory spikes |

### Alternatives Considered (all rejected per D-01)
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Umami | Plausible CE | Requires ClickHouse — too resource-heavy for this VPS |
| Umami | GoAccess | Server-side log parser, cannot track SPA client-side route transitions |
| Umami | Cloudflare Web Analytics | No data ownership; ad-blocker blind spot for developer audience |

---

## Architecture Patterns

### Docker Compose Addition

Add `umami` as a new service in `docker-compose.yml`. It connects to the existing `db` service via internal Docker networking.

```yaml
# Source: https://umami.is/docs/install + project pattern
umami:
  image: ghcr.io/umami-software/umami:postgresql-latest
  environment:
    DATABASE_URL: postgresql://${UMAMI_DB_USER}:${UMAMI_DB_PASSWORD}@db:5432/umami
    APP_SECRET: ${UMAMI_APP_SECRET}
    NODE_OPTIONS: "--max-old-space-size=256"
  expose:
    - "3000"
  depends_on:
    db:
      condition: service_healthy
  restart: unless-stopped
```

- No port mapping to host needed — Caddy reaches it via `umami:3000` on the Docker internal network.
- `APP_SECRET` is a random string used to sign session cookies (generate with `openssl rand -hex 32`).
- `DATABASE_URL` uses the internal Docker service name `db` as host.

### Caddy Subdomain Block

Add a new server block to `deploy/Caddyfile`:

```
analytics.flawchess.com {
    reverse_proxy umami:3000
}
```

Caddy auto-obtains a TLS certificate for `analytics.flawchess.com` via ACME/Let's Encrypt. No additional TLS config needed.

### Database Provisioning

Umami needs a pre-existing PostgreSQL database. It runs its own schema migrations on startup via Prisma. Two tasks required:

1. Create the database and user (one-time, production server only).
2. Grant privileges.

```sql
-- Run once on production: ssh flawchess, then psql
CREATE USER umami WITH PASSWORD 'your-password';
CREATE DATABASE umami OWNER umami;
GRANT ALL PRIVILEGES ON DATABASE umami TO umami;
\c umami
GRANT ALL ON SCHEMA public TO umami;
```

Umami's Prisma migrator will create all tables on first boot.

### React Frontend Tracking Script

Insert into `frontend/index.html` `<head>`:

```html
<!-- Source: https://umami.is/docs/tracker-configuration -->
<script
  defer
  src="https://analytics.flawchess.com/script.js"
  data-website-id="REPLACE_WITH_WEBSITE_ID"
  data-domains="flawchess.com"
></script>
```

- `data-domains` restricts tracking to production only — the script silently no-ops on localhost/staging.
- `data-website-id` comes from Umami dashboard after adding the site (post-deploy step).
- `defer` ensures it does not block page render.
- The script URL is the Umami subdomain `/script.js` endpoint.

### SPA Route Tracking

Umami's tracker patches `history.pushState` and `history.replaceState` to fire pageview events automatically. React Router uses these APIs for navigation. **No React-specific wrapper or hook is needed.** The default script handles SPA route changes.

If manual tracking is ever needed (e.g., to track a specific event), the global `umami.track()` API is available:

```js
// Manual event tracking (optional, not needed for basic pageviews)
window.umami.track('button-click', { label: 'import-games' });
```

### Anti-Patterns to Avoid
- **Running a second PostgreSQL container for Umami:** Wastes ~80-100 MB RAM on this VPS. Use the existing `db` container with a separate database (D-02).
- **Using `postgresql-latest` tag without pinning:** Image updates can break deploys. Consider pinning to a version tag after verifying the current one.
- **Exposing port 3000 to host:** Umami is internal-only. Caddy handles external access. No `ports:` mapping needed on the umami service.
- **Putting `data-website-id` before Umami is configured:** The website ID must be registered in the Umami admin dashboard first. The script will silently discard events if the ID is unknown.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Pageview counting | Custom FastAPI endpoint + DB table | Umami | Handles deduplication, bot filtering, referrer parsing, time-series aggregation |
| Privacy-compliant tracking | Custom cookieless tracker | Umami | Umami is GDPR-compliant by design; building a compliant tracker involves IP anonymization, data residency, retention policies |
| SPA route detection | React Router listener + manual fetch | Umami's History API patch | Already built in |
| Dashboard UI | Admin page in React | Umami's built-in dashboard | Full-featured with trends, top pages, referrers, countries |
| TLS for analytics subdomain | Manual cert management | Caddy auto-TLS | Already used for flawchess.com |

---

## Common Pitfalls

### Pitfall 1: Database Not Pre-Created
**What goes wrong:** Umami crashes on startup with a Prisma connection error (`database "umami" does not exist`).
**Why it happens:** Unlike some tools, Umami does not auto-create the database — it only runs schema migrations on an existing database.
**How to avoid:** Run the `CREATE DATABASE umami` SQL before first `docker compose up`.
**Warning signs:** Container enters a crash-loop restart immediately after first boot.

### Pitfall 2: `caddy` Container Cannot Reach `umami` Service
**What goes wrong:** `analytics.flawchess.com` returns a 502 Bad Gateway.
**Why it happens:** The `caddy` service is built from `frontend/Dockerfile`, which bakes the `Caddyfile` into the image at build time. If the Caddyfile is updated but the image is not rebuilt, the old config is used.
**How to avoid:** After updating `deploy/Caddyfile`, rebuild the caddy image: `docker compose up -d --build caddy`.
**Warning signs:** 502 errors despite Umami container being healthy.

### Pitfall 3: Default Admin Credentials Left Unchanged
**What goes wrong:** Anyone who discovers `analytics.flawchess.com` can log in.
**Why it happens:** Umami initializes with `admin` / `umami` on first run.
**How to avoid:** Change the password immediately after first login, before DNS goes live or the site is indexed.
**Warning signs:** n/a — this is a post-deploy manual step.

### Pitfall 4: `data-website-id` Hard-Coded Before Website Is Registered
**What goes wrong:** Pageviews are sent but silently discarded by Umami because the website ID is unknown.
**Why it happens:** The website ID is generated by Umami after you add a site in the dashboard — it cannot be pre-determined.
**How to avoid:** Plan the deploy in two steps: (1) bring up Umami, add the site, copy the ID; (2) update `index.html` with the real ID and rebuild the frontend.
**Warning signs:** Umami dashboard shows zero events despite traffic.

### Pitfall 5: Umami Memory Spikes Under Node.js GC
**What goes wrong:** Umami's Node.js process grows beyond 500 MB RAM over time.
**Why it happens:** V8's garbage collector can hold memory longer than expected under sustained load.
**How to avoid:** Set `NODE_OPTIONS: "--max-old-space-size=256"` in the umami service environment to cap the heap.
**Warning signs:** Gradual RAM growth visible in `docker stats`.

### Pitfall 6: `data-domains` Omitted — Tracking Fires in Dev
**What goes wrong:** Development visits pollute production analytics.
**Why it happens:** Without `data-domains`, Umami tracks every environment where the HTML is served.
**How to avoid:** Always include `data-domains="flawchess.com"` in the script tag.
**Warning signs:** Analytics show unusually high event counts or localhost referrers.

---

## Code Examples

### Verified Docker Compose Service Definition
```yaml
# Source: https://umami.is/docs/install (adapted for shared-db pattern)
umami:
  image: ghcr.io/umami-software/umami:postgresql-latest
  environment:
    DATABASE_URL: postgresql://${UMAMI_DB_USER}:${UMAMI_DB_PASSWORD}@db:5432/umami
    APP_SECRET: ${UMAMI_APP_SECRET}
    NODE_OPTIONS: "--max-old-space-size=256"
  expose:
    - "3000"
  depends_on:
    db:
      condition: service_healthy
  restart: unless-stopped
```

### Verified Caddy Subdomain Block
```
# Source: Caddy docs + existing Caddyfile pattern
analytics.flawchess.com {
    reverse_proxy umami:3000
}
```

### Verified Tracking Script Tag
```html
<!-- Source: https://umami.is/docs/tracker-configuration -->
<script
  defer
  src="https://analytics.flawchess.com/script.js"
  data-website-id="REPLACE_WITH_WEBSITE_ID_FROM_UMAMI_DASHBOARD"
  data-domains="flawchess.com"
></script>
```

### New .env Variables to Add
```bash
# Umami analytics
UMAMI_DB_USER=umami
UMAMI_DB_PASSWORD=<strong-random-password>
UMAMI_APP_SECRET=<openssl rand -hex 32>
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Umami supports MySQL + PostgreSQL | PostgreSQL only in v2+ | ~2022 | No MySQL needed for this project anyway |
| Separate PostgreSQL container for Umami | Share existing PostgreSQL instance | Community best practice | Saves ~80-100 MB RAM |
| `umami/umami` Docker Hub image | `ghcr.io/umami-software/umami` (GitHub Container Registry) | ~2023 | Official image moved; old Docker Hub image is outdated |
| v2 stable | v3 available (Nov 2025) | Nov 2025 | v3 adds cohorts/segmentation; v2 remains stable and supported |

**Deprecated/outdated:**
- `umami/umami` on Docker Hub: not maintained; use `ghcr.io/umami-software/umami:postgresql-latest` instead.
- MySQL support: dropped in v2; PostgreSQL only.

---

## Open Questions

1. **Umami v2 vs v3**
   - What we know: v3 launched Nov 2025, adds cohorts and segmentation, PostgreSQL-only. v2 is stable.
   - What's unclear: Whether `postgresql-latest` resolves to v2 or v3 at current deploy time; whether v3 has any breaking configuration changes.
   - Recommendation: At deploy time, run `docker pull ghcr.io/umami-software/umami:postgresql-latest` and check the reported version. Either v2 or v3 will work for this use case. Planner should note this as a deploy-time verification step.

2. **Website ID unavailable until Umami is running**
   - What we know: The `data-website-id` in `index.html` must match a site registered in Umami's admin UI.
   - What's unclear: Whether a placeholder/dummy ID can be used without errors, or whether missing ID causes JS errors.
   - Recommendation: Plan the deploy as two waves: Wave 1 = infrastructure (Umami + Caddy), Wave 2 = frontend script tag. The website ID is added after Wave 1 confirms Umami is healthy.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `uv run pytest tests/ -x -q` |
| Full suite command | `uv run pytest` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ANLY-01 | Umami dashboard shows visit counts/trends | manual-only | n/a | n/a |
| ANLY-02 | Top pages visible in Umami UI | manual-only | n/a | n/a |
| ANLY-03 | Referrer sources visible in Umami UI | manual-only | n/a | n/a |
| ANLY-04 | No cookie banner required; Umami collects no cookies | smoke | `curl -I https://flawchess.com` — verify no `Set-Cookie` from tracking | n/a |
| ANLY-05 | RAM footprint minimal | smoke | `docker stats --no-stream` — verify umami < 300 MB | n/a |

**Note:** All ANLY requirements are infrastructure/UI verification. No new Python unit tests are needed. Validation is manual smoke testing post-deploy:
1. Browse several pages on flawchess.com
2. Open Umami dashboard at `analytics.flawchess.com`
3. Confirm pageviews appear, top pages are listed, referrers are shown

### Sampling Rate
- **Per task commit:** No automated test applies — infra changes only
- **Per wave merge:** Manual smoke: confirm Umami dashboard at `analytics.flawchess.com` loads and shows data
- **Phase gate:** Dashboard shows live data from at least one real browser session before `/gsd:verify-work`

### Wave 0 Gaps
None — no new Python test files needed. Existing test suite is unaffected by this phase.

---

## Sources

### Primary (HIGH confidence)
- [Umami Official Docs — Install](https://umami.is/docs/install) — Docker image, DATABASE_URL format, default port, first-run credentials
- [Umami Official Docs — Tracker Configuration](https://umami.is/docs/tracker-configuration) — Script tag attributes, data-domains, data-auto-track, data-website-id

### Secondary (MEDIUM confidence)
- [Umami GitHub Discussion #2893 — Client-side routing](https://github.com/umami-software/umami/discussions/2893) — SPA History API tracking behavior
- [Umami GitHub Discussion #2715 — Memory sizing](https://github.com/umami-software/umami/discussions/2715) — ~100-256 MB RAM at modest traffic
- [OpenSourceForYou — Umami v3 Launch](https://www.opensourceforu.com/2025/11/umami-v3-launches-with-new-interface-cohorts-and-advanced-segmentation/) — v3 released Nov 2025

### Tertiary (LOW confidence — WebSearch only)
- Community blog posts on self-hosting Umami with Docker Compose (multiple, consistent with official docs on DATABASE_URL pattern)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — confirmed via official Umami docs
- Architecture patterns: HIGH — Docker Compose pattern from official docs, Caddy pattern from existing project
- Pitfalls: MEDIUM — database pre-creation and default credentials from official docs; caddy rebuild and memory from community sources
- SPA tracking: MEDIUM — History API patching documented behavior but GitHub discussion shows some uncertainty; practical risk is LOW for this use case

**Research date:** 2026-03-22
**Valid until:** 2026-09-22 (stable tooling; Umami v2 is mature)
