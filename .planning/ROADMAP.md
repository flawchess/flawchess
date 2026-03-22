# Roadmap: FlawChess

## Milestones

- ✅ **v1.0 Initial Platform** — Phases 1-10 (shipped 2026-03-15)
- ✅ **v1.1 Opening Explorer & UI Restructuring** — Phases 11-16 (shipped 2026-03-20)
- ✅ **v1.2 Mobile & PWA** — Phases 17-19 (shipped 2026-03-21)
- 🚧 **v1.3 Project Launch** — Phases 20-24 (in progress)

## Phases

<details>
<summary>✅ v1.0 Initial Platform (Phases 1-10) — SHIPPED 2026-03-15</summary>

- [x] Phase 1: Data Foundation (2/2 plans) — completed 2026-03-11
- [x] Phase 2: Import Pipeline (4/4 plans) — completed 2026-03-12
- [x] Phase 3: Analysis API (2/2 plans) — completed 2026-03-12
- [x] Phase 4: Frontend and Auth (3/3 plans) — completed 2026-03-12
- [x] Phase 5: Position Bookmarks (5/5 plans) — completed 2026-03-13
- [x] Phase 6: Browser Automation Optimization (2/2 plans) — completed 2026-03-13
- [x] Phase 7: Game Statistics and Charts (3/3 plans) — completed 2026-03-14
- [x] Phase 8: Games and Bookmark Tab Rework (3/3 plans) — completed 2026-03-14
- [x] Phase 9: Game Cards, Username Import, Pagination (8/8 plans) — completed 2026-03-15
- [x] Phase 10: Auto-Generate Position Bookmarks (4/4 plans) — completed 2026-03-15

</details>

<details>
<summary>✅ v1.1 Opening Explorer & UI Restructuring (Phases 11-16) — SHIPPED 2026-03-20</summary>

- [x] Phase 11: Schema and Import Pipeline (1/1 plan) — completed 2026-03-16
- [x] Phase 12: Backend Next-Moves Endpoint (2/2 plans) — completed 2026-03-16
- [x] Phase 13: Frontend Move Explorer Component (2/2 plans) — completed 2026-03-16
- [x] Phase 14: UI Restructuring (3/3 plans) — completed 2026-03-17
- [x] Phase 15: Enhanced Game Import Data (3/3 plans) — completed 2026-03-18
- [x] Phase 16: Game Card UI Improvements (3/3 plans) — completed 2026-03-18

</details>

<details>
<summary>✅ v1.2 Mobile & PWA (Phases 17-19) — SHIPPED 2026-03-21</summary>

- [x] Phase 17: PWA Foundation + Dev Workflow (1/1 plan) — completed 2026-03-20
- [x] Phase 18: Mobile Navigation (1/1 plan) — completed 2026-03-20
- [x] Phase 19: Mobile UX Polish + Install Prompt (3/3 plans) — completed 2026-03-21

</details>

### 🚧 v1.3 Project Launch (In Progress)

**Milestone Goal:** Rebrand to FlawChess, deploy to production on Hetzner, and ship everything needed for a public launch.

- [x] **Phase 20: Rename & Branding** — Rename codebase to FlawChess, create logo, update PWA manifest, transfer repo
- [x] **Phase 21: Docker & Deployment** — Containerize app, deploy to Hetzner with Caddy auto-TLS, configure env
- [x] **Phase 22: CI/CD & Monitoring** — Automate deploys via GitHub Actions, add Sentry error tracking (backend + frontend) (completed 2026-03-21)
- [ ] **Phase 23: Launch Readiness** — Analytics, About page, SEO, privacy policy, import queue, README
- [ ] **Phase 24: Theme Management** — Unified color theme across Tailwind, react-chessboard, charts, and branded buttons

## Phase Details

### Phase 20: Rename & Branding
**Goal**: FlawChess brand is fully established — name, logo, and identity consistent everywhere before any external services are created
**Depends on**: Phase 19
**Requirements**: BRAND-01, BRAND-02, BRAND-03, BRAND-04
**Success Criteria** (what must be TRUE):
  1. No instance of "Chessalytics" remains in code, config, docs, or git remotes (`grep -ri chessalytics` returns no matches in tracked files)
  2. The FlawChess logo appears as favicon, PWA icon, and in the app header
  3. Installing the PWA on a phone shows "FlawChess" as the app name with the new logo icon
  4. Git remote points to the flawchess GitHub organization
**Plans**: 2 plans

Plans:
- [x] 20-01-PLAN.md — Rename all code/config/docs from Chessalytics to FlawChess + apple-touch-icon placeholder
- [x] 20-02-PLAN.md — GitHub repo transfer to flawchess org + git remote update

### Phase 21: Docker & Deployment
**Goal**: FlawChess runs in production at flawchess.com — containerized, TLS-terminated, with persistent data and migrations-on-startup
**Depends on**: Phase 20
**Requirements**: DEPLOY-01, DEPLOY-02, DEPLOY-03, DEPLOY-04, DEPLOY-05, DEPLOY-06
**Success Criteria** (what must be TRUE):
  1. `docker compose up` on a fresh machine starts all services and the app is reachable at the configured domain
  2. Visiting flawchess.com serves the app over HTTPS with a valid Let's Encrypt certificate
  3. `curl https://flawchess.com/health` returns JSON (not HTML), confirming Caddy routes correctly
  4. Restarting containers after `docker compose down && docker compose up` preserves all user data
  5. No secrets or credentials exist in code or Docker images — all config comes from `.env` on the server
**Plans**: 2 plans

Plans:
- [x] 21-01-PLAN.md — Docker infrastructure: Dockerfiles, Compose, Caddyfile, entrypoint, CORS conditional, .env.example
- [x] 21-02-PLAN.md — Cloud-init cleanup + deploy to Hetzner VPS (checkpoint)

### Phase 22: CI/CD & Monitoring
**Goal**: Deploys are automated and errors in production are captured before users report them
**Depends on**: Phase 21
**Requirements**: DEPLOY-07, MON-01, MON-02
**Success Criteria** (what must be TRUE):
  1. Pushing to `main` triggers a GitHub Actions run that tests, builds on the server via SSH, and deploys — all without manual steps
  2. An unhandled exception in the FastAPI backend appears in the Sentry dashboard within 60 seconds
  3. A JavaScript error thrown in the React frontend appears in the Sentry dashboard within 60 seconds
**Plans**: 2 plans

Plans:
- [ ] 22-01-PLAN.md — GitHub Actions CI/CD workflow (test + SSH deploy + health check)
- [ ] 22-02-PLAN.md — Sentry error monitoring (backend sentry-sdk + frontend @sentry/react + Docker build args)

### Phase 23: Launch Readiness
**Goal**: FlawChess is ready for public users — analytics running, content complete, rate-limit protection in place, README polished
**Depends on**: Phase 22
**Requirements**: MON-03, CONT-01, CONT-02, CONT-03, STAB-01, BRAND-05
**Success Criteria** (what must be TRUE):
  1. Visiting flawchess.com/about shows an About page explaining the Zobrist-hash position-matching USP, a FAQ, and a visible register/login CTA
  2. The About page title and meta description appear correctly when the URL is shared on social media (Open Graph preview)
  3. A sitemap.xml and robots.txt are served at the correct paths and the About page is indexed by search crawlers
  4. A privacy policy page exists at /privacy and accurately names all data processors (Sentry, analytics tool, auth)
  5. Two simultaneous import requests (one chess.com, one lichess) complete without either returning a 429 or triggering a rate-limit ban
  6. Page views are recorded in the analytics dashboard without requiring cookie consent from users
**Plans**: TBD

Plans:
- [ ] 23-01: TBD

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Data Foundation | v1.0 | 2/2 | Complete | 2026-03-11 |
| 2. Import Pipeline | v1.0 | 4/4 | Complete | 2026-03-12 |
| 3. Analysis API | v1.0 | 2/2 | Complete | 2026-03-12 |
| 4. Frontend and Auth | v1.0 | 3/3 | Complete | 2026-03-12 |
| 5. Position Bookmarks | v1.0 | 5/5 | Complete | 2026-03-13 |
| 6. Browser Automation | v1.0 | 2/2 | Complete | 2026-03-13 |
| 7. Game Statistics | v1.0 | 3/3 | Complete | 2026-03-14 |
| 8. Bookmark Tab Rework | v1.0 | 3/3 | Complete | 2026-03-14 |
| 9. Game Cards & Import | v1.0 | 8/8 | Complete | 2026-03-15 |
| 10. Auto Bookmarks | v1.0 | 4/4 | Complete | 2026-03-15 |
| 11. Schema & Pipeline | v1.1 | 1/1 | Complete | 2026-03-16 |
| 12. Next-Moves API | v1.1 | 2/2 | Complete | 2026-03-16 |
| 13. Move Explorer UI | v1.1 | 2/2 | Complete | 2026-03-16 |
| 14. UI Restructuring | v1.1 | 3/3 | Complete | 2026-03-17 |
| 15. Enhanced Import | v1.1 | 3/3 | Complete | 2026-03-18 |
| 16. Game Card UI | v1.1 | 3/3 | Complete | 2026-03-18 |
| 17. PWA Foundation + Dev Workflow | v1.2 | 1/1 | Complete | 2026-03-20 |
| 18. Mobile Navigation | v1.2 | 1/1 | Complete | 2026-03-20 |
| 19. Mobile UX Polish + Install Prompt | v1.2 | 3/3 | Complete | 2026-03-21 |
| 20. Rename & Branding | v1.3 | 2/2 | Complete | 2026-03-21 |
| 21. Docker & Deployment | v1.3 | 2/2 | Complete | 2026-03-21 |
| 22. CI/CD & Monitoring | 2/2 | Complete    | 2026-03-21 | - |
| 23. Launch Readiness | v1.3 | 0/TBD | Not started | - |
| 24. Theme Management | v1.3 | 0/TBD | Not started | - |

### Phase 24: Theme Management
**Goal**: Define a unified color theme in one place (CSS variables + JS constants) that covers Tailwind utilities, react-chessboard squares, chart colors, and branded buttons — then fine-tune until the palette feels cohesive with the detective horsey logo
**Depends on**: Phase 23
**Requirements**: TBD
**Plans**: 0 plans

Plans:
- [ ] TBD (run /gsd:plan-phase 24 to break down)

---
*Created: 2026-03-11*
*v1.0 shipped: 2026-03-15*
*v1.1 shipped: 2026-03-20*
*v1.2 shipped: 2026-03-21*
*v1.3 started: 2026-03-21*
