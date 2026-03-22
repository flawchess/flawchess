# Roadmap: FlawChess

## Milestones

- ✅ **v1.0 Initial Platform** — Phases 1-10 (shipped 2024-03-15)
- ✅ **v1.1 Opening Explorer & UI Restructuring** — Phases 11-16 (shipped 2024-03-20)
- ✅ **v1.2 Mobile & PWA** — Phases 17-19 (shipped 2024-03-21)
- ✅ **v1.3 Project Launch** — Phases 20-23 (shipped 2026-03-22)
- **v1.4 Improvements** — Phase 24

## Phases

<details>
<summary>✅ v1.0 Initial Platform (Phases 1-10) — SHIPPED 2024-03-15</summary>

- [x] Phase 1: Data Foundation (2/2 plans) — completed 2024-03-11
- [x] Phase 2: Import Pipeline (4/4 plans) — completed 2024-03-12
- [x] Phase 3: Analysis API (2/2 plans) — completed 2024-03-12
- [x] Phase 4: Frontend and Auth (3/3 plans) — completed 2024-03-12
- [x] Phase 5: Position Bookmarks (5/5 plans) — completed 2024-03-13
- [x] Phase 6: Browser Automation Optimization (2/2 plans) — completed 2024-03-13
- [x] Phase 7: Game Statistics and Charts (3/3 plans) — completed 2024-03-14
- [x] Phase 8: Games and Bookmark Tab Rework (3/3 plans) — completed 2024-03-14
- [x] Phase 9: Game Cards, Username Import, Pagination (8/8 plans) — completed 2024-03-15
- [x] Phase 10: Auto-Generate Position Bookmarks (4/4 plans) — completed 2024-03-15

</details>

<details>
<summary>✅ v1.1 Opening Explorer & UI Restructuring (Phases 11-16) — SHIPPED 2024-03-20</summary>

- [x] Phase 11: Schema and Import Pipeline (1/1 plan) — completed 2024-03-16
- [x] Phase 12: Backend Next-Moves Endpoint (2/2 plans) — completed 2024-03-16
- [x] Phase 13: Frontend Move Explorer Component (2/2 plans) — completed 2024-03-16
- [x] Phase 14: UI Restructuring (3/3 plans) — completed 2024-03-17
- [x] Phase 15: Enhanced Game Import Data (3/3 plans) — completed 2024-03-18
- [x] Phase 16: Game Card UI Improvements (3/3 plans) — completed 2024-03-18

</details>

<details>
<summary>✅ v1.2 Mobile & PWA (Phases 17-19) — SHIPPED 2024-03-21</summary>

- [x] Phase 17: PWA Foundation + Dev Workflow (1/1 plan) — completed 2024-03-20
- [x] Phase 18: Mobile Navigation (1/1 plan) — completed 2024-03-20
- [x] Phase 19: Mobile UX Polish + Install Prompt (3/3 plans) — completed 2024-03-21

</details>

<details>
<summary>✅ v1.3 Project Launch (Phases 20-23) — SHIPPED 2026-03-22</summary>

- [x] Phase 20: Rename & Branding (2/2 plans) — completed 2026-03-21
- [x] Phase 21: Docker & Deployment (2/2 plans) — completed 2026-03-21
- [x] Phase 22: CI/CD & Monitoring (2/2 plans) — completed 2026-03-21
- [x] Phase 23: Launch Readiness (4/4 plans) — completed 2026-03-22

</details>

### v1.4 Improvements

- [ ] Phase 24: Web Analytics (0/2 plans) — not started
  - **Goal:** Add privacy-friendly, low-resource web analytics to track page visits, top routes, and referrer sources
  - **Requirements:** ANLY-01, ANLY-02, ANLY-03, ANLY-04, ANLY-05
  - **Plans:** 2 plans
    - [ ] 24-01-PLAN.md — Add Umami service to Docker Compose, Caddy subdomain, and env vars
    - [ ] 24-02-PLAN.md — Deploy Umami, add tracking script to frontend, verify end-to-end
  - **Success criteria:**
    1. Site owner can view a dashboard showing page visit counts and trends
    2. Top pages by visit count are visible
    3. Referrer sources are tracked and displayed
    4. No cookie consent banner is needed (privacy-friendly solution)
    5. Analytics adds negligible RAM/CPU overhead to the Hetzner VPS

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Data Foundation | v1.0 | 2/2 | Complete | 2024-03-11 |
| 2. Import Pipeline | v1.0 | 4/4 | Complete | 2024-03-12 |
| 3. Analysis API | v1.0 | 2/2 | Complete | 2024-03-12 |
| 4. Frontend and Auth | v1.0 | 3/3 | Complete | 2024-03-12 |
| 5. Position Bookmarks | v1.0 | 5/5 | Complete | 2024-03-13 |
| 6. Browser Automation | v1.0 | 2/2 | Complete | 2024-03-13 |
| 7. Game Statistics | v1.0 | 3/3 | Complete | 2024-03-14 |
| 8. Bookmark Tab Rework | v1.0 | 3/3 | Complete | 2024-03-14 |
| 9. Game Cards & Import | v1.0 | 8/8 | Complete | 2024-03-15 |
| 10. Auto Bookmarks | v1.0 | 4/4 | Complete | 2024-03-15 |
| 11. Schema & Pipeline | v1.1 | 1/1 | Complete | 2024-03-16 |
| 12. Next-Moves API | v1.1 | 2/2 | Complete | 2024-03-16 |
| 13. Move Explorer UI | v1.1 | 2/2 | Complete | 2024-03-16 |
| 14. UI Restructuring | v1.1 | 3/3 | Complete | 2024-03-17 |
| 15. Enhanced Import | v1.1 | 3/3 | Complete | 2024-03-18 |
| 16. Game Card UI | v1.1 | 3/3 | Complete | 2024-03-18 |
| 17. PWA Foundation + Dev Workflow | v1.2 | 1/1 | Complete | 2024-03-20 |
| 18. Mobile Navigation | v1.2 | 1/1 | Complete | 2024-03-20 |
| 19. Mobile UX Polish + Install Prompt | v1.2 | 3/3 | Complete | 2024-03-21 |
| 20. Rename & Branding | v1.3 | 2/2 | Complete | 2026-03-21 |
| 21. Docker & Deployment | v1.3 | 2/2 | Complete | 2026-03-21 |
| 22. CI/CD & Monitoring | v1.3 | 2/2 | Complete | 2026-03-21 |
| 23. Launch Readiness | v1.3 | 4/4 | Complete | 2026-03-22 |
| 24. Web Analytics | v1.4 | 0/2 | Not started | — |
