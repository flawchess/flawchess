# Phase 24: Web Analytics - Context

**Gathered:** 2026-03-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Add privacy-friendly, low-resource web analytics to track page visits, top routes, and referrer sources. Site owner can view a dashboard showing usage trends. No cookie consent banner required.

</domain>

<decisions>
## Implementation Decisions

### Analytics tool
- **D-01:** Umami (self-hosted), not Plausible CE (too resource-heavy — needs ClickHouse), not GoAccess (can't track SPA client-side route transitions), not Cloudflare Web Analytics (ad-blocker blind spot for developer audience, no data ownership), not Plausible Cloud (too expensive at ~$9/mo)

### Database hosting
- **D-02:** Shared PostgreSQL instance — Umami gets its own database (e.g., `umami`) within the existing `db` container. No separate PostgreSQL container. Lower RAM footprint than running two PostgreSQL processes.

### Dashboard access
- **D-03:** Subdomain at `analytics.flawchess.com` — Caddy handles auto-TLS. Clean URL, no subpath rewriting issues.
- **D-04:** Dashboard is private (login required). Can be made public later if desired.

### Authentication
- **D-05:** Umami's built-in user/password system. Default admin account on first run.

### Claude's Discretion
- Umami version and Docker image selection
- Caddy reverse proxy config details for the subdomain
- Data retention configuration
- Environment variable naming conventions
- Umami tracking script integration in the React frontend

</decisions>

<specifics>
## Specific Ideas

- Server is resource-constrained (Hetzner CX32: 2 vCPUs, 3.7 GB RAM + 2 GB swap) — RAM overhead from Umami must stay minimal
- Traffic is low (niche chess analysis site) — DB growth from pageview rows is negligible compared to existing `game_positions` table
- If VPS gets tight on RAM, Umami could be migrated to Umami Cloud free tier (10k events/month) as a fallback

</specifics>

<canonical_refs>
## Canonical References

No external specs — requirements are fully captured in decisions above and REQUIREMENTS.md (ANLY-01 through ANLY-05).

### Deployment
- `docker-compose.yml` — Production Docker stack (PostgreSQL + backend + Caddy)
- `deploy/Caddyfile` — Caddy reverse proxy config (add analytics subdomain here)
- `frontend/Dockerfile` — Frontend build + Caddy runtime image

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Existing PostgreSQL container (`db` service) — Umami connects to it with a separate database
- Caddy reverse proxy — add `analytics.flawchess.com` block for Umami

### Established Patterns
- Docker Compose services pattern — add Umami as a new service alongside `db`, `backend`, `caddy`
- Environment variables via `.env` file — Umami config follows same pattern

### Integration Points
- `docker-compose.yml` — new `umami` service definition
- `deploy/Caddyfile` — new server block for `analytics.flawchess.com`
- `frontend/index.html` or React root — Umami tracking `<script>` tag
- Production `.env` at `/opt/flawchess/.env` — Umami database credentials

</code_context>

<deferred>
## Deferred Ideas

- Update privacy policy page (`/privacy`) to mention analytics data collection — should be done after analytics is live
- Public analytics dashboard — revisit later if desired

</deferred>

---

*Phase: 24-web-analytics*
*Context gathered: 2026-03-22*
