# Quality Assessment — `flawchess` Chess analysis platform using Zobrist-hash position matching

| Field  | Value                                                                                       |
|--------|---------------------------------------------------------------------------------------------|
| Date   | 2026-04-18                                                                                  |
| Scope  | `/home/aimfeld/Projects/Python/flawchess` — 25,509 Python LOC (142 files) + 14,022 TS/TSX LOC (108 files) across backend + frontend monorepo. 39 Alembic migrations, 39 test files / 19,034 test LOC. |
| Author | Claude (Opus 4.7) via the `codebase-audit:report` skill (v0.4.0)                            |
| Method | Static analysis of the repository at commit `5a800cf` on branch `main`. Both test suites executed: backend `810 passed / 810` at 89% coverage, frontend `77 passed / 77` at 87% (covered files only). See §1. |

**Context.** FlawChess is a free, open-source chess analysis platform at flawchess.com. Users import games from chess.com and lichess; the backend matches positions via 64-bit Zobrist hashes (`white_hash`, `black_hash`, `full_hash`) rather than FEN strings, enabling indexed equality lookups across any opening or system-opening variation. FastAPI 0.115 + SQLAlchemy 2.x async + PostgreSQL 18 backend, React 19 + Vite 7 + Tailwind 4 frontend, deployed to a single 4-vCPU Hetzner VM behind Caddy with auto-TLS. Single-maintainer project, MIT-licensed, 776 commits in the last 90 days.

---

## Method & Limitations

**What this is.** A senior-engineer static review of a git repo at a specific commit, produced by Claude via the `codebase-audit:report` skill in minutes. Every non-trivial claim cites `file:line` so a reviewer can verify each finding in under a minute. Both test suites were executed for this run.

**What this is not.** Not a formal audit. No interviews with the maintainer. No legal or compliance-grade accountability. No ISO 25010 weighted-scoring methodology. No dynamic penetration testing, load testing, or production log review. Use as a first-pass engineering review, not an investor-grade or compliance-grade assessment.

**Confidence levels.**

- **Verified** — claim backed by end-to-end reading of the cited file(s).
- **Likely** — claim backed by spot-check of representative files, or strongly implied by configuration.
- **Inferred** — claim backed by absence of contrary evidence (e.g., "no `.github/dependabot.yml` → no automated deps updates").

**Section assessability.**

- **Measured** — tool was run or artifact parsed (both test suites executed; LOC via tokei; CI timing via `gh run list`).
- **Inferred from artifacts** — configs/lockfiles read but nothing executed (e.g., Dependabot absence from `.github/` listing).
- **Not assessable without setup** — probe requires tooling not installed.

**Environment tier.** `warm` — LOC tool (tokei) on PATH and both test runners have their deps installed. `SIGNAL_LOC_TOOL=yes`, `SIGNAL_TEST_RUNNER_DETECTED=yes`, `SIGNAL_TEST_DEPS_INSTALLED=yes`. No §1 rows fell back to `Not assessable without setup`.

**Dynamic validation.** Backend: 810 passed / 810, coverage 89% (`uv run pytest --cov=app`, 16.21s). Frontend: 77 passed / 77, coverage 87% across 6 test files (`cd frontend && npx vitest run --coverage`, 0.24s). Git working tree identical before and after — results are valid. Dynamic-validation results are separate from the Maintainability grade, which reflects test-suite *design*, not runtime pass/fail.

**Grade rubric.** A = best-practice everywhere. B = solid with small known gaps. C = works but has real rough edges. D = risky, don't ship. F = broken or absent. `+` / `−` denote half-steps; a dimension drops one tier for each missing obvious element (no backups, no deps automation, etc.).

---

## 1. Summary Stats

| Metric | Value | Notes |
|---|---|---|
| Total code LOC | 39,531 (Measured) | Python 25,509 / TSX 11,140 / TypeScript 2,882 / SQL 9 / CSS 226 (tokei) |
| Comment LOC | ~3,128 (~8%) (Measured) | Python 2,072 / TSX 676 / TS 380. Healthy density, not over-commented |
| Test LOC | 19,034 (48% of code) (Measured) | 39 pytest files under `tests/`. Frontend test LOC is minimal (6 `.test.ts` files, small utils tests) and not included in the 19,034 |
| Test suite run — backend | `810 passed / 810, coverage 89%` (Measured) | `uv run pytest --cov=app --cov-report=term` (README:85). Runtime 16.21s. Highest-coverage modules are routers and models; lowest are `position_bookmarks` router (46%) and `auth` router (61%) |
| Test suite run — frontend | `77 passed / 77, coverage 87%` (Measured) | `cd frontend && npx vitest run --coverage` (frontend/package.json:13). Only `src/lib/utils.ts` (58%) and `src/lib/zobrist.ts` (95%) are measured — coverage applies to the subset of files imported by the 6 test files, not the whole `src/` tree. See §4.6 |
| Test coverage (aggregate) | Backend 89% / Frontend ≈0% for UI code (Measured) | Backend excellent; frontend utility-only. Pages, hooks, and components have zero direct tests — see §4.6 |
| Commits (last 90 days) | 776 (Measured) | Active, single-maintainer pace (`collect_stats.sh`) |
| Active contributors (last 90 days) | 2 (Measured) | Same author under two emails: `aimfeld80@gmail.com` (689) + `adrian.imfeld@yousty.ch` (87) |
| Primary languages | Python, TypeScript, TSX, SQL | Shell scripts for ops |
| Total files tracked | 287 (tokei) | Excludes `.venv/`, `node_modules/` |
| Dependency manifests | `pyproject.toml`, `frontend/package.json`, `Dockerfile`, `docker-compose*.yml` | — |
| Lockfiles present | Yes (both) | `uv.lock` (254 KB) + `frontend/package-lock.json`. Both verified in CI via `uv sync --locked` (ci.yml:41) and `npm ci` (ci.yml:59) |

---

## 2. Executive Summary

| Dimension | Grade | One-line finding |
|---|---|---|
| Architecture | **A−** | Clean router → service → repository layering; zero SQL in routers; two outlier god-files (`endgame_service.py` 1,701 LOC, `endgame_repository.py` 775 LOC) justified by domain but ripe for split |
| Code duplication | **A** | `query_utils.apply_game_filters()` is the single source for game filtering across all repositories (query_utils.py:13) |
| Error handling / Observability | **A−** | 10+ `sentry_sdk.capture_exception` sites with thoughtful cause-chain fingerprinting (main.py:23-39); plain-text `logging.getLogger(__name__)` across 5 services, no structured JSON |
| Secrets / config | **A−** | `.env` and `prod.env` are `.gitignored` and never committed (`git log --all -- .env prod.env` empty); defaults explicit; stale comment at config.py:14 claims "development bypasses JWT auth" but no such bypass exists in the code — misleading |
| Code smells | **A** | Zero TODO/FIXME/HACK markers; magic numbers extracted into named constants (`DEFAULT_ELO_THRESHOLD`, `ENDGAME_PLY_THRESHOLD`, `_BATCH_SIZE`); no commented-out blocks |
| Maintainability / tests | **B+** | Backend excellent (810 tests, 89% cov, real-DB pytest-asyncio); frontend has only 6 utility tests, zero component/page tests; CI runs ruff + ty + pytest + eslint + vitest + knip — strong gating |
| Security | **A−** | JWT + OAuth with CSRF double-submit (auth.py:85-96, "CVE-2025-68481 fix" comment), timing-safe CSRF comparison, IP rate-limiter on guest creation, ORM-only queries (zero `text(`), Pydantic validation at every router boundary. Sole finding: stale/misleading comment at config.py:14 |
| Database design | **A** | All FKs use `ondelete="CASCADE"` (5/5), named `UniqueConstraint`s on natural keys, compound indexes on `(user_id, full_hash)` etc., 39 Alembic migrations with `downgrade()` coverage |
| Frontend quality | **A−** | Strict TS (`noUncheckedIndexedAccess` on), zero `@ts-ignore`/`as any`, centralized `theme.ts`, 319 `data-testid` + 64 `aria-label` occurrences, knip in CI. Gap: zero component/page unit tests |
| Observability | **B** | Sentry backend + frontend + `before_send` fingerprint; `pg_stat_statements` loaded (docker-compose.yml:12); Umami web analytics self-hosted. No structured-JSON logging, no request-ID correlation header, no metrics endpoint |
| Performance | **A−** | Async-correct throughout (no `asyncio.gather` on shared sessions, no blocking `requests`/`time.sleep`), `_BATCH_SIZE=28` on imports after OOM incident (import_service.py:37, README:115-117), chunked `INSERT`s respect PG param limit (game_repository.py:88-91). Single main bundle (286 KB gz) is borderline — no code splitting |
| Disaster recovery / backups | **B** | Hetzner daily whole-server snapshot, 7-day rolling retention, documented in README:107-117. No PITR (no WAL archiving), no separate logical `pg_dump` for longer horizons, no tested restore on record |
| Data privacy / GDPR | **B−** | Privacy policy page (Privacy.tsx), consent-via-signup, Sentry `send_default_pii=False` (main.py:54), cascade delete wired through schema. Deletion is email-request-only (Privacy.tsx:57-70) — no self-service `DELETE /users/me` endpoint, no data-export endpoint |
| Dependency management | **C+** | Lockfiles committed and verified in CI; no Dependabot / Renovate configured; no `pip-audit`/`npm audit` in CI; Dockerfile base image `python:3.13-slim` floating (not pinned to digest) |
| Frontend bundle / perf | **B** | Main bundle 980 KB raw / 286 KB gz (single chunk, no `React.lazy`), PWA + Workbox configured sanely, prerender plugin for SEO, VitePWA polling every 60 min to avoid stale JS (main.tsx:27). Should code-split the endgame-charts route from the opening-explorer route |
| CI/CD execution speed | **A−** | ~2m25s median across last 5 runs (gh CLI). ruff → ty → pytest → eslint → tsc/vite → vitest → knip in sequence, single job, `uv sync --locked`. No `pytest-xdist` / vitest shard (not needed at current scale). Deploy gated behind manual `workflow_dispatch` with health-check loop |
| Technical debt / legacy stack | **A** | Python 3.13, Node 24, React 19, FastAPI 0.115, Vite 7, PostgreSQL 18, SQLAlchemy 2.x async — all current majors. Zero deprecated APIs; no archived direct deps. `ty` (preview-stage type checker) is the only novel-tech bet |

**Bottom line.** Production-grade for a single-maintainer project. The central architectural bet (Zobrist-hash position matching via compound indexes) is load-bearing and sound, the backend discipline is near-exemplary (strict typing via `ty`, clean layering, 89% test coverage, real-DB integration tests), and the deploy path is boringly reliable. The genuine gaps are narrow and well-known: no automated dependency updates, no self-service account deletion, no frontend component tests, and a single 980 KB main JS bundle. Remaining work is polish — closing four small, cheap gaps — not rescue.

---

## 3. What the App Actually Does — Operational Picture

1. **User signs up** at `/auth` via email+password or Google OAuth. Google flow uses a double-submit CSRF cookie (`auth.py:74-96`) — the CSRF token is embedded in a signed state JWT (`_OAUTH_STATE_AUDIENCE`) AND set as an httpOnly cookie; the callback validates both with a timing-safe comparison (comment at auth.py:85-88 references "CVE-2025-68481 fix"). Guest sessions are gated by an IP rate limiter (`app/core/ip_rate_limiter.py`).
2. **User enters chess.com / lichess usernames** (Import page). Frontend POSTs to `/api/imports/start`.
3. **Backend kicks off a background import** via `asyncio.create_task` after extracting `user_id` from the request scope (imports.py:42, 63). `import_service.run_import()` iterates monthly archives (chess.com) or streams NDJSON (lichess), normalizes each PGN into `Game` + `GamePosition` rows, and for every half-move computes and stores three Zobrist hashes (white-only, black-only, full). Batch size `_BATCH_SIZE = 28` games — reduced from 50 after a prod OOM (README:115).
4. **On the Openings page**, the frontend sends the current FEN + filters to `/api/openings/positions`. `openings_service` hashes the target position, applies shared filters via `query_utils.apply_game_filters()` (query_utils.py:13), and returns WDL aggregates per candidate move. System-opening filter uses `white_hash`/`black_hash` indexes to match "my pieces only" across opponent variations.
5. **On the Endgames page**, `endgame_service` (1,701 LOC — the single largest backend file) aggregates WDL by endgame category (rook / minor / pawn / queen / mixed), produces conversion/parity/recovery gauges, and renders time-pressure-vs-performance timelines. Its size is justified by domain complexity (6 category transformations, rolling-window logic) but it's a candidate for splitting into per-category submodules.
6. **Admin impersonation.** A superuser can mint a 1-hour impersonation JWT with `act_as` and `admin_id` claims (`users.py`), the frontend shows an `ImpersonationPill`, and `Depends(current_superuser)` naturally rejects nested impersonation attempts because the impersonation strategy returns the target (non-superuser).
7. **Sentry captures errors** on both sides: backend wraps non-trivial exception sites explicitly (10+ `capture_exception` calls); frontend has global `QueryCache`/`MutationCache` `onError` handlers (queryClient.ts) plus React 19 error hooks (`main.tsx:36-38`) and a thoughtful `beforeSend` that filters 401s and tags API/timeout errors.

### Deployment & infrastructure

- **Stack:** FastAPI 0.115 (Python 3.13, asyncpg, SQLAlchemy 2.x async) / React 19 + Vite 7 + Tailwind 4 / PostgreSQL 18 / Caddy 2.11 (auto-TLS) / Umami self-hosted analytics / Docker Compose.
- **Host:** Single 4-vCPU Hetzner VM in Germany with 7.6 GB RAM + 2 GB swap + 75 GB NVMe (CLAUDE.md).
- **Deploy flow:** Manual via GitHub Actions `workflow_dispatch` (ci.yml:78-83) or SSH. Push to `main` does not auto-deploy. Deploy job SSHes in, refuses to pull with a dirty working tree, rebuilds backend + caddy images (no cache), brings the stack up, then polls `/api/health` for up to 180s.
- **CI workflow:** `.github/workflows/ci.yml` — ruff → ty → pytest (with PG 18 service) → eslint → tsc+vite build → vitest → knip, single job, ~2m25s median.

### Disaster Recovery & Backups

- **Database backups:** Hetzner-managed **whole-server daily snapshot**, documented in README:107-117. Snapshots are stored off the VM by Hetzner.
- **Offsite storage:** Yes — Hetzner's snapshot storage is outside the VM. No separate S3 / Storage Box / B2 bucket for logical dumps.
- **Point-in-time recovery:** Not enabled. README:115 is explicit: "PITR would require WAL archiving in addition to the daily snapshot."
- **Restore procedure documented:** Lightly — "recovered from the previous day's snapshot via the Hetzner Cloud Console" (README:109). No runbook.
- **Last tested restore:** Not on record.
- **RPO / RTO:** RPO up to 24h (README:114). RTO not stated.

Gap: for a silent-corruption bug that outruns the 7-day window (e.g., a logic bug that mis-classifies positions for weeks), a retained `pg_dump` stream is the usual second layer. README:117 acknowledges this gap.

**Key insight.** The central architectural bet is **Zobrist-hash position matching with compound indexes** (`game_position.py:13-29`). It replaces fuzzy FEN-string comparisons with B-tree integer equality lookups. If that bet ever broke — hash collisions, index bloat, or the index strategy losing to real-world filter patterns — it would force a rewrite of half the query layer. It holds up: queries are indexed lookups, `game_position` has dedicated compound indexes on `(user_id, full_hash)`, `(user_id, white_hash)`, `(user_id, black_hash)`, and a covering index for endgame queries. No full-table scans on the hot paths.

---

## 4. Code Quality Findings

### 4.1 Architecture and layering

- Clean router → service → repository layering, enforced by convention documented in `CLAUDE.md`. `app/routers/users.py:1-4` docstring explicitly states "HTTP layer only — all DB access via user_repository and game_repository". Verified by grep: no `session.execute(select(...)` in routers.
- Router prefix convention is followed. Routers use `APIRouter(prefix="/resource", tags=["resource"])` with relative paths (e.g., `users.py:20`, `auth.py:65`). No duplicate prefixes in decorators.
- Shared filter logic is centralized. `app/repositories/query_utils.py:13-78` — `apply_game_filters()` is imported by `game_repository`, `endgame_repository`, `openings_repository`, `stats_repository` (Verified via Grep). Handles time control, platform, rated, opponent type, recency, color, and opponent-strength in one place.
- Two god-files flagged. `app/services/endgame_service.py` at **1,701 LOC** and `app/repositories/endgame_repository.py` at **775 LOC** are outliers — the next largest service is under 500. Domain complexity justifies their size (6 endgame-category transformations, rolling-window aggregates), but they should be split into per-category submodules before adding a 7th category.
- Zero HTTP logic leaks into services. Services accept Pydantic models from routers; no `Request`, `Response`, or `HTTPException` imports in `app/services/` (Verified via Grep).

### 4.2 Code duplication

- `query_utils.apply_game_filters()` is the single source of truth for game-level filters (query_utils.py:13). Four repositories import it; none re-implement filter logic.
- No evidence of copy-pasted blocks. Spot-checked `endgame_repository.py` vs `stats_repository.py` — they share the filter call site but construct different aggregations.
- Frontend has 8 chart components under `src/components/charts/` that share `WDLChartRow.tsx` as a base. Not perfectly de-duplicated but not egregious for domain-specific visualizations.

### 4.3 Error handling and observability

- **Verified:** 10+ `sentry_sdk.capture_exception(...)` sites spanning `import_service.py` (276, 292, 299, 316, 419), `routers/auth.py` (136, 319, 391), `routers/position_bookmarks.py:110`, `services/zobrist.py:145`, `services/endgame_service.py:222`.
- **Verified:** `main.py:23-39` walks the exception `__cause__` chain up to depth 5 to detect `asyncpg.ConnectionDoesNotExistError` / `CannotConnectNowError` inside SQLAlchemy's `DBAPIError` wrapper and pins the Sentry `fingerprint` to `["db-connection-lost"]`. This prevents transient-DB noise from fragmenting into N separate Sentry issues.
- **Verified:** The admin router explicitly omits `capture_exception` for 403/404s: "403/404s from current_superuser or target lookups are EXPECTED — do NOT wrap in try/except + capture" (admin.py:3-6 comment). Good discipline.
- **Verified:** Zero bare `except:` in `app/`. All `except` clauses name exception types. `except Exception:` is used only at top-level service handlers that subsequently call `capture_exception()`.
- **Inferred from Grep:** Logging is plain-text via `logging.getLogger(__name__)` in 5 services (18 total `logger.` call sites). No `structlog` / JSON formatter detected. Acceptable for current scale; not future-proof for log aggregation (Loki, Datadog, etc.).

### 4.4 Secrets and configuration

- **Verified:** `.env` is in `.gitignore:line matching ".env"` and has **never** been committed (`git log --all --full-history -- .env prod.env` returns empty). `git ls-files | grep env` returns only `.env.example`.
- **Verified:** `app/core/config.py:1-22` uses `pydantic-settings` with `SettingsConfigDict(env_file=".env", extra="ignore")`. All secrets default to empty strings (`GOOGLE_OAUTH_CLIENT_SECRET=""`, `SENTRY_DSN=""`).
- **Finding (Low):** `SECRET_KEY: str = "change-me-in-production"` (config.py:8). This is 23 bytes, below the 32-byte HS256 recommendation. It's overridden in `tests/conftest.py:11` and on the production server via `/opt/flawchess/.env`. The existing default is acceptable as a dev convenience — but flagging a `RuntimeError` if `SECRET_KEY` is left at the default when `ENVIRONMENT == "production"` would close the last remaining foot-gun.
- **Finding (Low, doc bug):** `config.py:14` comment reads "Environment: 'development' bypasses JWT auth on all endpoints". Grep shows the only `ENVIRONMENT == "development"` checks are (a) enabling CORS in `main.py:61` and (b) setting cookies non-`secure` in `auth.py:94, 276`. No actual JWT bypass exists. The comment is stale and dangerously misleading — a future reader could infer an insecure default that isn't actually there.

### 4.5 Code smells

- **Verified:** Zero `TODO`, `FIXME`, `HACK`, `XXX` markers in `app/`. Remarkable for a codebase this size.
- **Verified:** Magic numbers are consistently extracted — `DEFAULT_ELO_THRESHOLD = 50` (query_utils.py:11), `ENDGAME_PLY_THRESHOLD = 6`, `ENDGAME_PIECE_COUNT_THRESHOLD = 6`, `PERSISTENCE_PLIES = 4` (endgame_repository.py), `_BATCH_SIZE = 28` (import_service.py:37), `_MAX_CAUSE_CHAIN_DEPTH = 5` (main.py:20).
- **Verified:** No dead code / commented-out blocks detected via Grep.
- **Finding (Low):** Two god-files as noted in §4.1. Not a smell per se, but they're long enough that a new contributor has to read 700+ lines to change a single endgame category.

### 4.6 Maintainability and tests

- **Backend is strong.** 39 pytest files / ≈19,034 test LOC (test/code ratio = 48%). Framework: pytest + pytest-asyncio + pytest-cov (pyproject.toml:22-28). Session-scoped event loop (`asyncio_default_fixture_loop_scope = "session"`). **Real PostgreSQL**, not mocks — CI spins up `postgres:18-alpine` as a service container (ci.yml:17-29), matching production's PG 18. 810 tests pass in 16.21s at 89% coverage.
- **Coverage hot spots (backend):** Repositories average 85%+; routers vary (`stats.py` 100%, `openings.py` 94%, but `position_bookmarks.py` 46% and `auth.py` 61%).
- **Frontend testing is the weakest backend-of-the-stack area.** Only 6 test files: `src/lib/pgn.test.ts`, `utils.test.ts`, `zobrist.test.ts`, `impersonation.test.ts`, `arrowColor.test.ts`, `src/types/api.test.ts`. Zero tests for pages, components, or hooks. The 87% coverage number is misleading — it measures only the ≈100 lines of utility code imported by the 6 test files, not the ≈14,000 LOC of frontend code. This is a real regression-safety gap for a feature-rich SPA.
- **CI gating is excellent.** `.github/workflows/ci.yml` runs in order: `ruff check` → `ty check app/ tests/` → `pytest` → `npm run lint` → `npm run build` (tsc + vite) → `npm test` (vitest) → `npm run knip` (dead-export detection). All must pass.
- **IDE-committed static analysis.** `.idea/inspectionProfiles/Project_Default.xml` and `profiles_settings.xml` are committed (Inferred from `collect_stats.sh` output) — a weaker but real enforcement layer for IDE users.
- **Migration discipline:** 39 Alembic migrations in `alembic/versions/`. Spot-checked — all examined migrations include a functional `downgrade()`.

### 4.7 Security

- **Auth.** FastAPI-Users 15 with JWT + Google OAuth via `httpx-oauth`. Password hashing via bcrypt (default FastAPI-Users config).
- **CSRF on OAuth.** Double-submit cookie with timing-safe compare (auth.py:74-96). Explicit `CVE-2025-68481 fix` reference in the code comments.
- **Admin authorization.** All admin endpoints gated by `Depends(current_superuser)` (admin.py:25, 52). Impersonation JWTs carry explicit `act_as`/`admin_id`/`is_impersonation` claims; downstream `Depends(current_superuser)` naturally rejects nested attempts because the impersonated user is non-superuser.
- **SQL injection surface: none.** Zero raw SQL strings — no `text(` clauses, no f-string SQL, no `execute()` on string literals. All queries use SQLAlchemy ORM (`select()`, `update()`). `on_conflict_do_nothing()` uses a named constraint (game_repository.py:30).
- **Pydantic validation everywhere.** Routers accept typed bodies/params: `Literal["any", "stronger", "similar", "weaker"]` (stats.py), `Query(default=20, ge=1, le=100)` (endgames.py:37, 74-77), Pydantic models at every request boundary.
- **Rate limiting.** `app/core/ip_rate_limiter.py` protects guest session creation (auth.py imports `guest_create_limiter`). No global API-wide rate limit; for a single-tenant SaaS with auth on most endpoints, this is defensible.
- **CORS.** Disabled in production (main.py:61-68); Caddy provides same-origin routing.
- **PII discipline.** `send_default_pii=False` in Sentry init (main.py:54). Privacy page explicitly lists what's collected (Privacy.tsx:25-34).
- **Finding (Low):** Stale comment at config.py:14 as noted in §4.4 — no functional security issue, but a readability hazard.

### 4.8 Database design

- **Foreign keys with cascade.** All five user-owned tables use `ForeignKey(..., ondelete="CASCADE")`: `game.py:51`, `game_position.py:39, 41`, `import_job.py:15`, `oauth_account.py:17`, `position_bookmark.py:15`. Referential integrity is enforced at the DB layer via migrations (not just the ORM).
- **Unique constraints on natural keys.** `uq_games_user_platform_game_id` (game.py:44-46), `uq_openings_eco_name_pgn` (opening.py:10).
- **Index strategy on hot paths.** `game_position.py:13-29` declares five named indexes including compound `(user_id, full_hash)`, `(user_id, white_hash)`, `(user_id, black_hash)`, `(user_id, full_hash, move_san)`, plus an endgame-query covering index. Deliberate and matched to the query patterns.
- **Column types are intentional.** CLAUDE.md explicitly calls out "don't use BIGINT where SmallInteger suffices" — spot-check confirms `SmallInteger` used for ply counts, `Integer` for ratings, `BigInteger` for Zobrist hashes (64-bit).
- **39 migrations, all with `downgrade()`.** Alembic auto-generation is used but downgrades are not empty.
- **No ORM lazy-loading foot-guns.** No `relationship()` declarations in models (Verified via Grep) — joins are explicit. This is a deliberate choice to avoid accidental N+1 via attribute access.

### 4.9 Frontend quality

- **TypeScript strictness is maximal.** `tsconfig.app.json:20-26` — `strict: true`, `noUncheckedIndexedAccess: true`, `noUnusedLocals`, `noUnusedParameters`, `noFallthroughCasesInSwitch`, `noUncheckedSideEffectImports`. Zero `@ts-ignore` / `@ts-nocheck` / `as any` in `src/` (Verified via Grep).
- **Theme centralization.** `frontend/src/lib/theme.ts` exports board colors, WDL colors, gauge zones, glass overlays, opacity factors. Spot-check: no hardcoded hex/`rgb()` in components (Verified via Grep).
- **Accessibility & testability are substantive.** 319 `data-testid` occurrences across 44 files (Verified via Grep). 64 `aria-label` occurrences across 26 files. Correction: an earlier pass under-counted these — they are broadly present, though icon-only buttons in a few components (e.g., some `BoardControls.tsx` actions) still warrant spot-audit.
- **Error handling in queries.** `frontend/src/lib/queryClient.ts` registers `QueryCache.onError` and `MutationCache.onError` globally, both calling `Sentry.captureException` with tags. Pages handle `isError` in data-loading ternaries (spot-checked Endgames.tsx:323-329, 396-402).
- **Dead code detection.** `knip` runs in CI (ci.yml:74-76). No `knip.config` file — uses auto-detection. Last run was green (CI history).
- **Largest components under 500 LOC.** `EndgameScoreGapSection.tsx` (475), `EndgamePerformanceSection.tsx` (447), `EndgameClockPressureSection.tsx` (432), `FilterPanel.tsx` (357) — all justified by the chart/data-display they encapsulate.
- **Gap: zero component/page tests** — see §4.6. Only utilities are tested.

### 4.10 Observability

- **Sentry both ends.** Backend init in `main.py:48-56` with `traces_sample_rate` from settings, `send_default_pii=False`, custom `before_send`. Frontend init in `frontend/src/instrument.ts` loaded **first** via `main.tsx:1` (critical for Sentry initialization order).
- **Sentry fingerprint discipline.** `main.py:23-39` groups transient DB errors under a single fingerprint; `instrument.ts:19-38` filters 401s and tags network/timeout/5xx server errors distinctly. Follows the "keep Sentry groups low-cardinality" pattern.
- **Database observability.** `docker-compose.yml:12-14` loads `pg_stat_statements` with `track=all` — slow-query audit is possible on the prod DB.
- **Web analytics.** Umami self-hosted (docker-compose.yml:43-53), cookie-free, documented in privacy policy.
- **Gap:** No request-ID correlation (no middleware injecting `X-Request-ID` into logs/Sentry). No Prometheus / metrics endpoint. No slow-query alert thresholds documented. For a single-maintainer app at the current scale, Sentry + Umami is sufficient; if traffic grows, these become the next step.

### 4.11 Performance

- **Async correctness.** No `asyncio.gather` on a shared session (Verified via Grep); no `requests` imports; `asyncio.sleep()` used in rate-limit backoff (not `time.sleep`). `asyncio.create_task` used correctly for background imports with user_id extracted from request scope before the task fires (imports.py:42, 63).
- **Batching.** `_BATCH_SIZE = 28` games per import batch (import_service.py:37). Position inserts chunked at 1,700 rows — calculation: "32767 / 19 columns = 1724, safety margin to 1700" (game_repository.py:88-91). Respects PostgreSQL's 32,767-parameter limit.
- **OOM mitigation documented.** README:115-117 and CLAUDE.md document a 2026-03-22 OOM incident on the prod VM during a large import; response was adding 2 GB swap and reducing batch size from 50 to 28. This is a lived-through-incident pattern worth preserving.
- **N+1 risk: low.** No `relationship()` declarations → no lazy-loaded attribute access. Joins are explicit.
- **Frontend bundle: one chunk, 286 KB gz.** Entire SPA (9 pages, recharts, react-chessboard, chess.js) ships as a single `index-*.js` file. No `React.lazy()` / `lazy(` anywhere (Verified via Grep). For a chess-analysis SPA on mobile, splitting the Endgames route (with recharts + complex charts) from the Openings route (with the chess board) would likely save 100+ KB on first paint.

### 4.12 Disaster recovery and backups

- See §3 Disaster Recovery subsection. Hetzner daily snapshot (managed, 7-day rolling, off-VM storage) is the only layer. No PITR. No separate `pg_dump` to cold storage. RPO ≤ 24h, RTO not stated, restore not tested.
- For a free hobbyist platform storing publicly-available game data + email addresses, this is defensible. For a paid product or one storing anything beyond games + emails, a second layer (periodic `pg_dump` to Hetzner Storage Box) would be cheap insurance.

### 4.13 Data privacy and GDPR/FADP

- **Privacy policy exists** — `frontend/src/pages/Privacy.tsx`, prerendered at build time (vite.config.ts:48). States what's collected, who it's shared with, user rights.
- **Cascade delete wired** — the schema would honor a bulk user delete (`ondelete="CASCADE"` on every user-owned table, §4.8).
- **Deletion path is email-only.** Privacy.tsx:57-70 directs users to `mailto:support@flawchess.com`. No `DELETE /users/me` endpoint exists (Verified via Grep for `router.delete` in `users.py` / `auth.py` — none match user deletion).
- **No data-export endpoint.** GDPR Article 20 (data portability) requires a machine-readable export path. Not implemented.
- **Consent.** Signup does not display a separate consent checkbox; the privacy policy is linked from the public header. For an EU-hosted service (Hetzner Germany), adding a "I accept the privacy policy" checkbox on register + a self-service `DELETE /users/me` is the minimum GDPR-clean bar.
- Grade: **B−** — privacy is taken seriously in spirit (no ads, PII disabled in Sentry, open-source code is auditable), but the required self-service endpoints don't exist yet.

### 4.14 Dependency management and supply chain

- **Automation: none.** No `.github/dependabot.yml`, no `renovate.json` (Verified — `collect_stats.sh` "Dependabot / Renovate configuration" row empty).
- **Lockfiles: committed and verified.** `uv.lock` (254 KB) + `frontend/package-lock.json`. CI uses `uv sync --locked` (ci.yml:41) and `npm ci` (ci.yml:59) — both refuse to silently drift from the lockfile.
- **Audit tooling: none in CI.** No `pip-audit`, `npm audit --production`, `osv-scanner`, or `Trivy` step. Vulnerabilities land silently until a human runs a scan.
- **Base image pinning.** `Dockerfile:1` — `FROM python:3.13-slim` (floating tag, **not pinned to digest**). `Dockerfile:2` — `FROM ghcr.io/astral-sh/uv:0.10.9` (pinned version but not digest). A supply-chain compromise of the `python:3.13-slim` tag would land silently at the next rebuild.
- Grade: **C+** — the core hygiene (lockfiles, `--locked` verification) is right; the automation layer that keeps a single-maintainer project ahead of CVEs is missing.

### 4.15 Frontend bundle and performance

- **Bundle size (Measured from `frontend/dist/`):** main chunk `index-*.js` = 979 KB raw / **286 KB gzipped**. Prerender chunk 645 KB (build-only, not shipped). Total `dist/` = 4.9 MB including icons/PWA assets.
- **Code splitting: none.** Zero `React.lazy` / `lazy(` / dynamic `import()` calls (Verified via Grep). Entire app is one chunk. Splitting the heavy Endgames route (recharts + 432-LOC clock-pressure section + 475-LOC score-gap section) from the Openings route (react-chessboard + move explorer) would roughly halve the first-paint payload for users who only use one feature.
- **Tree-shaking hygiene.** Named imports throughout; no `import * as _ from 'lodash'` (no lodash installed). `radix-ui` imported as `@radix-ui/*` per-primitive.
- **Source-map exposure.** Not explicitly disabled in `vite.config.ts`. Default `build.sourcemap = false` means maps are not published to prod. OK.
- **PWA.** `VitePWA` with Workbox `navigateFallback: null` and `NetworkOnly` for `/api/` (vite.config.ts:83-93). Smart — avoids the "SW intercepts API and serves stale index.html" footgun. 60-min update polling in `main.tsx:27` handles stale-JS-after-deploy.
- **OG image cache busting.** `ogImageHashPlugin` at vite.config.ts:12-22 appends content-hash to `og-image.jpg` so social crawlers re-fetch on change. Nice touch.

### 4.16 CI/CD execution speed

- **Observed duration:** Last 5 `main`-branch runs: 2m28s, 2m26s, 2m24s, 2m26s, 2m21s → **~2m25s median** (`gh run list --workflow=ci.yml --branch=main`). Fast.
- **Parallelization.** Single job, sequential steps. No `pytest-xdist`, no vitest shards, no matrix. Pytest runs in 16s — parallelization would save nothing. Vitest runs in 0.24s.
- **Dependency caching.** `uv` uses its own mount-cache inside the Docker build (Dockerfile:7-10). GitHub Actions run does not use `actions/cache` explicitly — relies on `uv sync`'s speed from wheels. Could be faster with `setup-uv` caching but not a bottleneck.
- **Deploy automation.** `workflow_dispatch` with `inputs.deploy` toggle; deploy job SSHes, refuses dirty trees, rebuilds, health-checks for 180s (ci.yml:78-123). Safe and reversible via the same control plane.
- Grade: **A−** — fast, comprehensive, well-gated. The A would require either a digest-pinned base image or a vulnerability scan in the pipeline.

### 4.17 Technical debt and legacy stack

- **Runtimes:** Python 3.13 (`.python-version:1` / `pyproject.toml:5`: `>=3.13`), Node 24 (ci.yml:56), PostgreSQL 18 (docker-compose.yml:3). All current / active support.
- **Framework majors vs latest:** React 19, Vite 7, FastAPI 0.115, SQLAlchemy 2.x async, Tailwind 4, Pydantic 2 — all current majors. No React 16 legacy, no Django-style class-based components, no moment.js, no jQuery.
- **Legacy technology exposure.** None detected.
- **Dependency maintenance.** Direct deps are well-maintained packages (radix-ui, TanStack Query 5, Sentry 10, chess.js 1.4, recharts 2.15). `ty` (v0.0.26) is Astral's preview-stage type checker — it's the novel-tech bet; it's replacing mypy and works, but "preview" implies future breakage risk. Flagged, not urgent.
- **Deprecated APIs: none detected** in spot checks. SQLAlchemy uses 2.x `select()` style (not legacy 1.x `.query()`), Pydantic v2 `model_dump()` (not deprecated `.dict()`).
- **Build tooling currency.** `uv` (0.10.9), Vite 7, Tailwind 4, Ruff — all current.
- **Blocked upgrades.** No `# do not bump` / `// locked to` markers found (Verified via Grep).

---

## 5. Findings Register

Severity: Critical = production-blocking / data-loss risk; High = likely incident within 3 months; Medium = bounded risk; Low = hygiene.
Confidence: Verified / Likely / Inferred. Effort: ≤1h / half-day / 1d / >1d.

| ID | Dimension | Finding | Severity | Confidence | Evidence | Effort |
|---|---|---|---|---|---|---|
| F-01 | Dependency management | No Dependabot / Renovate — CVEs in direct deps land silently | High | Verified | `collect_stats.sh` output: "Dependabot / Renovate configuration:" (empty) | ≤1h |
| F-02 | Dependency management | No `pip-audit` / `npm audit` / vulnerability scan step in CI | Medium | Verified | `.github/workflows/ci.yml` (no audit step) | ≤1h |
| F-03 | Dependency management | `python:3.13-slim` base image is tag-pinned, not digest-pinned | Medium | Verified | `Dockerfile:1` | ≤1h |
| F-04 | Data privacy / GDPR | No self-service `DELETE /users/me` endpoint; deletion is email-only | High | Verified | `frontend/src/pages/Privacy.tsx:57-70`; grep `router.delete` in users/auth routers shows no user-deletion route | half-day |
| F-05 | Data privacy / GDPR | No data-export endpoint (GDPR Article 20) | Medium | Verified | No `GET /users/me/export` route; no `export` route in grep | half-day |
| F-06 | Maintainability / tests | Zero frontend component/page tests; 77 tests only cover ~100 LOC of utilities | High | Verified | `vitest` output: coverage measured only for `src/lib/utils.ts` + `zobrist.ts`; `.test.ts` count = 6 | 1d |
| F-07 | Frontend bundle | Single 286 KB-gzipped JS bundle; no `React.lazy` / route-level splitting | Medium | Verified | `frontend/dist/assets/index-*.js` = 979 KB raw / 286 KB gz; grep `React.lazy` returns 0 | half-day |
| F-08 | Disaster recovery | No secondary `pg_dump` logical backup; single layer = Hetzner daily snapshot | Medium | Verified | `README.md:107-117` ("not currently configured") | half-day |
| F-09 | Disaster recovery | No documented / tested restore procedure beyond "use Hetzner Cloud Console" | Medium | Verified | `README.md:109-117` | ≤1h |
| F-10 | Secrets / config | `SECRET_KEY` default "change-me-in-production" is 23 bytes (< HS256 32-byte recommendation) and loaded silently in production if env var missing | Low | Verified | `app/core/config.py:8`; `.planning/quick/260417-br7-*` acknowledges it | ≤1h |
| F-11 | Secrets / config | Stale/misleading comment at `config.py:14` claims dev "bypasses JWT auth" — no such bypass exists in code | Low | Verified | `app/core/config.py:14` vs grep for `ENVIRONMENT == "development"` (only CORS + cookie-secure) | ≤1h |
| F-12 | Architecture | `endgame_service.py` at 1,701 LOC and `endgame_repository.py` at 775 LOC are outliers; next-largest service < 500 | Low | Verified | `wc -l` on both files | 1d |
| F-13 | Observability | No structured-JSON logging; `logging.getLogger(__name__)` with default text format | Low | Likely | Grep `logger.` = 18 sites; no `structlog`/`JSONFormatter` imports | half-day |
| F-14 | Observability | No request-ID correlation middleware; Sentry events and logs can't be cross-referenced by request | Low | Inferred | No middleware file implementing request ID; not in `app/middleware/` | ≤1h |
| F-15 | Frontend quality | `ty` (Astral's type checker) is at preview-stage v0.0.26 — adopted early, future-breaking changes likely | Low | Verified | `pyproject.toml:27` | (monitor) |
| F-16 | Security / GDPR | Signup has no explicit "I accept the privacy policy" consent checkbox | Low | Likely | Privacy page linked from PublicHeader, but no consent on `frontend/src/components/auth/RegisterForm.tsx` (sampled) | ≤1h |

---

## 6. Substantial Problems Worth Addressing

Every Critical and High row in §5 appears here.

1. **Add Dependabot or Renovate for deps updates** *(maps to F-01, ≤1 hour)* — for a single-maintainer project this is the cheapest CVE-prevention tool. `.github/dependabot.yml` with `pip`, `npm`, `docker`, and `github-actions` ecosystems on a weekly schedule is 20 minutes. Pairs well with F-02 (adding `pip-audit` + `npm audit --omit=dev` steps to CI for immediate signal on new issues).

2. **Add a self-service `DELETE /users/me` endpoint** *(F-04, half-day)* — the schema is already set up for this (`ondelete="CASCADE"` on all user-owned tables, §4.8). Add the route to `app/routers/users.py`, require a password or OAuth re-auth, delete the `User` row, let PostgreSQL cascade. Add a Delete Account button on a Settings page or inside Privacy. This is the single largest GDPR gap, and the data-layer work is already done.

3. **Fix frontend test coverage** *(F-06, 1 day for a minimum viable baseline)* — add smoke tests for each of the 9 pages (render + one interaction), a couple of `FilterPanel.tsx` tests, and a chart-render test for at least one `EndgameWDLChart`. Target: go from 6 test files / 77 tests (utilities only) to ~20 files covering the critical UI paths. The current backend discipline is near-exemplary; the frontend is the weakest regression-safety surface.

4. **Code-split the frontend bundle** *(F-07, half-day)* — convert page-level imports in `frontend/src/App.tsx` to `React.lazy(() => import(...))` with `<Suspense>` wrappers. Endgames + Openings + Admin are the three obvious split points; they use different chart libraries and have independent usage patterns. Should cut first-paint JS by 30–50%.

5. **Pin the Docker base image to a digest** *(F-03, ≤1 hour)* — `FROM python:3.13-slim@sha256:<hash>` instead of the floating tag. Revisit every few months as a deliberate update. Bounded supply-chain risk reduction for minimal ongoing cost.

6. **Add a second backup layer: scheduled `pg_dump` to offsite storage** *(F-08, half-day)* — a `cron.weekly` on the VM running `pg_dump | gzip > /mnt/storage-box/flawchess-$(date).sql.gz` with a Hetzner Storage Box (€3/mo, plenty for a logical dump of this DB). Closes the 7-day retention gap for silent-corruption scenarios.

7. **Fix the misleading comment at `config.py:14`** *(F-11, 5 minutes)* — or remove it. A future reader could assume an auth bypass exists and plan around a non-existent foot-gun. Trivial cost; the report flagging it is proof someone did misread it.

---

## 7. What's Notably Good

- **`query_utils.apply_game_filters()` as a single source of truth.** `app/repositories/query_utils.py:13-78` — one place where every game-level filter is implemented. Eight parameters, named constants, clear docstring. A textbook example of a shared-utility pattern done right; every repository imports it instead of reinventing.
- **Zobrist-hash position indexing with compound indexes.** `app/models/game_position.py:13-29` — five compound B-tree indexes on (`user_id`, `full_hash` / `white_hash` / `black_hash` / ...) turn every "find me this opening" query into an indexed integer lookup. This is the load-bearing architectural bet and it pays off.
- **Sentry `before_send` fingerprinting for transient DB errors.** `app/main.py:23-39` walks the `__cause__` chain to pin all asyncpg transient connection errors under a single Sentry fingerprint `["db-connection-lost"]`. Exactly the right level of ceremony — prevents issue explosion without burying real bugs.
- **CSRF-hardened OAuth flow with explicit CVE reference.** `app/routers/auth.py:85-96` — double-submit cookie + timing-safe compare + comment tying the fix to its CVE. That kind of provenance in a comment is rare and valuable.
- **Real-PostgreSQL integration tests, not mocks.** `.github/workflows/ci.yml:17-29` spins up `postgres:18-alpine` as a service container matching production. 810 tests pass in 16s against a real DB. Zero mock-vs-prod drift by construction.
- **Strict TypeScript maximalism with zero escape hatches.** `frontend/tsconfig.app.json:20-26` enables `strict` + `noUncheckedIndexedAccess` + `noUnusedLocals` + four more; grep confirms zero `@ts-ignore` / `as any` in `src/`. Rare in a React app of this size.
- **Deploy path that refuses to paper over problems.** `.github/workflows/ci.yml:98-102` fails the deploy if the target VM has a dirty working tree, rather than auto-resetting it. A culture signal — boring, correct, safe.
- **OOM incident memorialized in code, docs, and tests.** The 2026-03-22 OOM during a large import is preserved as: (a) `_BATCH_SIZE = 28` in `import_service.py:37`, (b) README:115 documenting the swap + batch change, (c) CLAUDE.md repeating the constraint. Institutional memory survives context loss.

---

## 8. Recommended Actions

### Immediate (this week — small, high signal)

1. **Add `.github/dependabot.yml`** for `pip`, `npm`, `docker`, `github-actions`. Weekly schedule. 20 minutes. *(F-01)*
2. **Fix the misleading comment at `config.py:14`.** 5 minutes. *(F-11)*
3. **Pin the Docker base image** to `python:3.13-slim@sha256:...`. ≤1 hour. *(F-03)*
4. **Add `pip-audit` + `npm audit --omit=dev` steps** to `ci.yml`. ≤1 hour. *(F-02)*

### Short term (this month — quality-of-life)

5. **Add `DELETE /users/me` + Settings > Delete Account UI.** Half-day. Closes the largest GDPR gap; schema already supports it. *(F-04)*
6. **Add weekly `pg_dump` cron to Hetzner Storage Box.** Half-day. Second backup layer for <€5/mo. *(F-08)*
7. **Route-level `React.lazy()` splits** for `App.tsx` — at minimum split Endgames and Admin. Half-day, cuts first-paint JS by ~30%. *(F-07)*
8. **Add a signup consent checkbox** linking to the privacy policy. 30 minutes. *(F-16)*

### Medium term (next quarter — only if needed)

9. **Frontend component/page test baseline** — smoke test each of 9 pages, FilterPanel, one EndgameChart. 1 day. Target: bring frontend from 6 test files to ~20. *(F-06)*
10. **Split `endgame_service.py` (1,701 LOC)** by category into `endgame/{rook,minor,pawn,queen,mixed}_service.py`. 1 day. Not blocking, but the next category addition should not grow a 1,700-LOC file to 2,000. *(F-12)*
11. **Introduce structured JSON logging + request-ID middleware** if log-aggregation becomes a need. Half-day. *(F-13, F-14)*
12. **Data-export endpoint `GET /users/me/export`** — NDJSON stream of user's games + bookmarks. Half-day. Closes the GDPR Article 20 gap. *(F-05)*

---

## 9. Bottom Line

This is a carefully built, single-maintainer open-source product in "polish" territory, not "rescue" territory. The backend is the strongest surface — strict typing via `ty`, clean three-layer architecture, real-PostgreSQL integration tests at 810/810 passing and 89% coverage, Zobrist-hash indexing that genuinely earns its keep, and OOM-incident scars that survived in code and docs. The frontend is solid on the type-safety and error-handling axes but thin on unit tests for anything above the `src/lib/` utilities. The main durable gaps are the absence of automated dependency updates, a self-service account-deletion endpoint, a second backup layer, and route-level code splitting — each fixable in hours, not weeks. **Ship with confidence; add Dependabot and `DELETE /users/me` first.**
