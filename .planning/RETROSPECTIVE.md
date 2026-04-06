# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.8 — Guest Access

**Shipped:** 2026-04-06
**Phases:** 4 | **Delivered via:** PR #37

### What Was Built
- Guest session foundation: is_guest User model flag, JWT-based guest sessions with 30-day auto-refresh, IP rate limiting
- Guest frontend: "Use as Guest" buttons on homepage and auth page, persistent guest banner
- Email/password promotion: backend promotion service, register-page promotion flow preserving all imported data
- Google SSO promotion: OAuth promotion route with guest identity preservation across redirect, email collision handling
- Security: CVE-2025-68481 Google OAuth CSRF vulnerability patched with double-submit cookie validation
- UX polish: import page guest guard, auth page logo linking, delete button disabled during active imports

### What Worked
- Guest as first-class User row (is_guest=True) — promotion is a single UPDATE, no FK migration needed
- Bearer transport for guest JWTs — avoided dual-transport complexity entirely
- Register-page promotion instead of separate modal — reused existing form, cleaner UX, less code
- PR-based workflow (feature branch → squash merge) kept main clean during multi-phase development

### What Was Inefficient
- Entire milestone developed outside GSD discuss→plan→execute workflow — no SUMMARY.md, VERIFICATION.md, or PLAN.md files exist for phases 44-47
- GSD state tracking stayed at 0% despite all work being complete — planning artifacts diverged from actual progress
- Quick tasks (UI polish commits between roadmap creation and PR merge) weren't tracked in any GSD artifact

### Patterns Established
- Guest user pattern: is_guest flag on User model, synthetic email (`@guest.local`), promotion via in-place UPDATE
- OAuth CSRF protection: double-submit cookie pattern for all OAuth callbacks
- Import guard: disable destructive actions (delete) while import is running

### Key Lessons
1. When developing outside GSD's formal workflow (e.g., rapid feature branch work), the planning artifacts become stale immediately — either commit to the workflow or accept the tracking gap
2. Guest-as-User-row is much simpler than a separate guest model — promotion is trivial, no FK migration, no special-casing in queries
3. Register-page promotion beats a dedicated modal — reuses existing validation, error handling, and styling

---

## Milestone: v1.3 — Project Launch

**Shipped:** 2026-03-22
**Phases:** 4 | **Plans:** 10

### What Was Built
- Full rebrand from Chessalytics to FlawChess (20 files, PWA manifest, logo, GitHub org transfer)
- Docker Compose production stack: multi-stage Dockerfiles, Caddy auto-TLS, entrypoint with auto-migrations
- Deployed to Hetzner VPS (CX32, 2 vCPUs, 3.7GB RAM) at flawchess.com
- GitHub Actions CI/CD: test + lint + SSH deploy + health check polling
- Sentry error monitoring on both FastAPI backend and React frontend
- Public homepage with feature sections, FAQ, register/login CTA
- SEO fundamentals: meta tags, Open Graph, robots.txt, sitemap.xml
- Privacy policy page at /privacy
- Per-platform rate limiter (asyncio.Semaphore) for chess.com/lichess import protection
- Professional README with screenshots and self-hosting instructions
- 14 quick tasks: lichess import fix, arrow sorting, tooltip→popover, mobile UX, board controls, tab renaming, filter heights, bookmarks, /api prefix, brown theme, new-user routing, README, time control fix, WDL bar fix

### What Worked
- Deployment-first ordering (Phase 21 before 22/23) meant CI/CD and launch readiness could be tested against the live server
- Cloud-init + Docker Compose gave a reproducible single-command server setup
- Caddy as sole internet-facing entry point simplified TLS and routing (no nginx config)
- asyncio.Semaphore for rate limiting avoided adding Redis/Celery infrastructure
- Quick tasks handled all post-launch polish (14 tasks) without disrupting phase work
- Swap file added reactively when PostgreSQL OOM-killed during large import — proactive monitoring would have been better

### What Was Inefficient
- Plan 21-02 (cloud-init cleanup + deploy checkpoint) was never formally executed — deployment happened organically during 21-01 and manual setup. Skipped at milestone completion.
- Some SUMMARY.md files have poor/missing one_liner frontmatter fields — summary-extract continues to return null
- Phase 22 plan checkboxes in ROADMAP.md were never updated to [x] despite being complete — bookkeeping drift from manual execution
- OOM kill on production required emergency swap file and batch size reduction — should have configured swap in cloud-init from the start

### Patterns Established
- `ENVIRONMENT` env var controlling CORS (disabled in production, enabled in dev)
- Backend `expose` only in docker-compose.yml (no `ports`) — Caddy proxies all traffic
- Sentry DSN injected at Docker build time via `ARG`/`ENV` for frontend bundle
- `_BATCH_SIZE = 10` for import to prevent OOM on constrained servers
- asyncio.Semaphore lazy-init pattern to avoid event loop not started error

### Key Lessons
1. Production memory constraints matter — 3.7GB RAM with PostgreSQL + FastAPI + Caddy is tight; swap is essential from day one
2. Human verification checkpoints (deploy steps) don't fit well into automated execution — they should be separate milestone gates, not plans
3. Caddy is excellent for small deployments — auto-TLS, reverse proxy, static file serving in one config
4. Rate limiter design should match the bottleneck — per-platform semaphore is simpler than global queue for chess.com/lichess with different rate limits

---

## Milestone: v1.2 — Mobile & PWA

**Shipped:** 2026-03-21
**Phases:** 3 | **Plans:** 5

### What Was Built
- PWA with service worker, chess-themed icons, Workbox caching (NetworkOnly for API)
- Mobile bottom navigation bar with direct tabs + "More" drawer (vaul-based)
- Click-to-move chessboard on touch devices with sticky board on Openings page
- 44px touch targets on all interactive elements, overflow fixes at 375px
- Android/iOS in-app install prompts (beforeinstallprompt + manual iOS banner)
- Dev workflow: LAN hosting + Cloudflare Tunnel for HTTPS phone testing
- 7 quick tasks: lichess import fix, arrow sorting, tooltip→popover, mobile card layouts, board controls reorder, tab renaming, filter height consistency

### What Worked
- Frontend-only milestone scope (no backend/API changes) kept complexity low and iteration fast
- Pure Tailwind `sm:` breakpoints for mobile/desktop switching — no JS detection needed
- vaul library for drawer component — handled scroll lock, backdrop, iOS momentum out of the box
- Quick tasks handled all polish (tab renaming, button heights, card layouts) without phase overhead
- Duplicating mobile Openings layout (vs trying to make one layout responsive) avoided fighting sticky positioning

### What Was Inefficient
- react-chessboard drag-and-drop caused persistent black screen on mobile — spent multiple iterations trying to fix before disabling drag entirely
- Touch target sizing required understanding CSS specificity interactions between component libraries (shadcn's data-attribute selectors) and custom classes — `min-h-11` vs `h-11` vs `h-11!` depending on component
- summary-extract CLI still returns null for one_liner — SUMMARY.md files lack the expected frontmatter field

### Patterns Established
- `min-h-11 sm:min-h-0` pattern for ToggleGroupItem/SelectTrigger mobile touch targets (min-height overrides component's fixed height)
- `h-11 sm:h-7` for custom buttons to match ToggleGroup/Select heights exactly
- `h-11!` (Tailwind important) when overriding data-attribute-based component styles (e.g., TabsList)
- `h-11 w-11 sm:h-8 sm:w-8` for icon-only buttons (44px mobile, 32px desktop)
- `allowDragging: false` + onSquareClick for mobile chessboard interaction
- `bg-muted/50 hover:bg-muted! border border-border/40` for collapsible trigger styling

### Key Lessons
1. Disable drag-and-drop early on mobile — HTML5 DnD simply doesn't work on iOS Safari, and react-chessboard's touch handling causes rendering bugs
2. CSS specificity matters with component libraries — shadcn uses `data-[size=sm]:h-7` which beats plain `h-7`; use `min-h` to override or Tailwind's `!` modifier
3. Mobile layout duplication is sometimes the right trade-off — fighting CSS to make one responsive layout work everywhere costs more than maintaining two clear layouts
4. Quick tasks are ideal for mobile polish — button heights, tab names, card layouts are all self-contained changes that don't warrant phase planning

---

## Milestone: v1.1 — Opening Explorer & UI Restructuring

**Shipped:** 2026-03-20
**Phases:** 6 | **Plans:** 15

### What Was Built
- Move explorer: next-move W/D/L stats, click-to-navigate, transposition warnings, board arrows
- UI restructuring: tabbed Openings hub, dedicated Import page, shared filter sidebar
- Enhanced import: clock data, termination, time control fix, username-scoped sync
- Game cards: 3-row layout, lucide-react icons, hover/tap minimap, null-safe metadata
- Bug fixes: data isolation, Google SSO last_login, cache clearing

### What Worked
- Phase dependency chain (11→12→13→14→15→16) allowed clean incremental delivery
- Human verification phase (14-03) caught real issues: hooks ordering bug, tab naming, import page redesign
- Quick tasks (19 total) handled polish effectively without disrupting phase work
- DB wipe decision removed migration complexity entirely for v1.1

### What Was Inefficient
- Phase 15 was renumbered mid-milestone (chart consolidation replaced by enhanced import data) — caused confusion in file naming with two "15-*" directories
- GCUI requirements were left at "Planned" status in traceability table despite being complete — bookkeeping drift
- summary-extract CLI returned null for one_liner fields — summaries lacked structured frontmatter fields

### Patterns Established
- Tab content as JSX variables (defined before return, reused in multiple Tabs instances)
- QueryClient singleton pattern for cross-cutting auth/cache concerns
- Username-scoped sync boundaries for multi-username import
- Single TooltipProvider wrapping lists to avoid per-item context overhead

### Key Lessons
1. Phase renumbering creates file system confusion — prefer adding at end (Phase 16) over replacing existing phase numbers
2. Human verification phases catch real bugs that automated tests miss (hooks ordering, UX issues)
3. Quick tasks are effective for UI polish during milestone execution — keeps phase scope clean

---

## Milestone: v1.6 — UI Polish & Improvements

**Shipped:** 2026-03-30
**Phases:** 6 | **Plans:** 11

### What Was Built
- Centralized theme system: CSS variables, brand-brown/charcoal Tailwind utilities, SVG feTurbulence noise texture class
- Charcoal containers with noise texture applied across all pages, brand subtab highlighting
- Shared WDLChartRow component replacing all inconsistent WDL chart implementations (custom bars, Recharts)
- Openings reference table: 3641 entries from TSV dataset, openings_dedup view, SQL-side WDL aggregation
- Most Played Openings redesign: top 10 per color, filter support, dedicated table UI, minimap popover
- Opening Statistics rework: section reordering, default chart data from most-played when no bookmarks, chart-enable toggle
- Bookmark card redesign: bigger minimap (72px), chart-enable toggle in button row, suggestions from most-played data
- Mobile drawer sidebars: Vaul-based right-side drawers for filters and bookmarks, deferred filter apply on close
- 26 quick tasks across the milestone

### What Worked
- Theme-first phase ordering (34→35→36→37→38→39) meant each phase built on the previous — shared components before consuming features
- WDL chart refactoring (Phase 35) paid off immediately — Phases 36-38 could use WDLChartRow without reimplementing
- SQL-side WDL aggregation (func.count.filter) moved counting from Python loops to SQL, measurable performance improvement
- Deferred filter apply pattern on mobile prevents API spam — filters accumulate, single request on sidebar close
- PR-based workflow for phases kept main clean while allowing iterative development

### What Was Inefficient
- Traceability table in REQUIREMENTS.md went stale — ORT-03 was implemented but unchecked, MOB-01-07 showed "Not started" despite completion
- Phase count in MILESTONES.md shows 8 instead of 6 (includes backlog phases in count) — CLI counting is approximate
- No milestone audit was run before completion — requirement drift went undetected until manual check

### Patterns Established
- `charcoal-texture` CSS class for consistent container styling with SVG noise
- WDLChartRow as single source of truth for all WDL visualizations
- Deferred state pattern: local state in sidebar, commit on close
- Openings reference table with precomputed FEN/ply_count for position lookup
- chart-enable toggle with localStorage persistence for user preferences

### Key Lessons
1. Requirement traceability tables need automated updates — manual status tracking drifts as soon as execution begins
2. Theme/component infrastructure phases early in a UI milestone pay compound dividends across subsequent phases
3. Milestone audits should be run proactively, not skipped — catching stale requirements at completion adds unnecessary friction
4. SQL-side aggregation (func.count.filter) is worth the migration cost — Python-side counting doesn't scale

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Plans | Key Change |
|-----------|--------|-------|------------|
| v1.0 | 10 | 36 | Established GSD workflow, phase/plan structure |
| v1.1 | 6 | 15 | Added human verification phases, heavy quick task usage |
| v1.2 | 3 | 5 | Frontend-only scope, mobile-first patterns, CSS specificity lessons |
| v1.3 | 4 | 10 | First production deployment, CI/CD, monitoring, launch readiness, 14 quick tasks |
| v1.4 | 1 | 2 | Self-hosted Umami analytics, minimal-scope milestone |
| v1.5 | 9 | 18 | Backend-heavy: position classifier, endgame analytics, engine analysis import |
| v1.6 | 6 | 11 | UI polish: theme system, shared components, openings table, mobile drawers, 26 quick tasks |
| v1.7 | 6 | 11 | Consolidation: ty type checking, knip dead exports, import speed 2x, SQL aggregations |
| v1.8 | 4 | N/A | Guest access via feature branch + PR, outside GSD workflow — no formal plans |

### Top Lessons (Verified Across Milestones)

1. DB wipe for schema changes is worth it in early development — migration complexity slows iteration
2. Human verification catches integration issues that unit tests miss
3. Quick tasks are the right tool for UI polish — confirmed across v1.1 (19 tasks), v1.2 (7 tasks), v1.3 (14 tasks), v1.6 (26 tasks)
4. CSS specificity with component libraries requires understanding the full chain — min-h/h/important patterns now documented
5. Production memory constraints need upfront planning — swap file and batch size tuning should be in initial deployment config
6. Human verification checkpoints (manual deploy steps) don't fit automated plan execution — use milestone gates instead
7. Infrastructure-first ordering pays off — theme/shared components early in UI milestones, DB schema early in backend milestones
8. Requirement traceability tables drift under manual maintenance — consider automated status syncing
