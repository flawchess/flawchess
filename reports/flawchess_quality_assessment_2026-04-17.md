# Quality Assessment — `flawchess` open-source chess analysis platform

| Field  | Value                                                                                       |
|--------|---------------------------------------------------------------------------------------------|
| Date   | 2026-04-17                                                                                  |
| Scope  | `/home/aimfeld/Projects/Python/flawchess` (≈23,188 LOC Python backend, ≈13,087 LOC TypeScript frontend, 36 test files / 17,806 LOC of tests, 38 Alembic migrations) |
| Author | Claude (Opus 4.7) via the `quality-assessment` skill                                        |
| Method | Static analysis of the repository at commit `54eb33e` on branch `main`. No tests were run; backend coverage read from existing `.coverage` / `htmlcov/status.json`. |

**Context.** FlawChess is a free, open-source chess analysis platform live at `flawchess.com`. Users import their games from chess.com and lichess; the backend computes Zobrist hashes for every half-move and answers WDL (win/draw/loss) queries by position. Stack is FastAPI 0.115 + SQLAlchemy 2 async + PostgreSQL 18, with a React 19 + Vite 5 + TanStack Query frontend served by Caddy. Single-box Hetzner deployment behind Docker Compose, Sentry on both ends, single active maintainer, MIT licence.

---

## 1. Summary Stats

| Metric | Value | Notes |
|---|---|---|
| Total code LOC | ≈36,275 (Python 23,188 + TS 13,087) | `scc` exact counts; SQL/YAML/Shell/CSS/Dockerfile add ~720 more |
| Comment LOC | 5,376 (14.8% of code) | Python 4,391 / TS 985. Most are rationale, not boilerplate |
| Test LOC | 17,806 across 36 files | Test/code ratio ≈ 49%. Healthy for a service of this shape |
| Test coverage | ≈89% backend (from existing `htmlcov`) | Read from `htmlcov/status.json`. Frontend has `@vitest/coverage-v8` installed (recently added in commit `26ed58c`) but no artifact committed |
| Commits (last 90 days) | 765 | Very active. Single active maintainer (678) plus one alias (87) |
| Active contributors (last 90 days) | 2 (same person, two emails) | Effectively single-maintainer |
| Primary languages | Python, TypeScript, SQL | — |
| Total tracked source files | 136 Python + 97 TypeScript | Plus 774 Markdown (mostly `.planning/` GSD artefacts, not production docs) |
| Dependency manifests | `pyproject.toml`, `frontend/package.json`, `Dockerfile`, `frontend/Dockerfile`, `docker-compose.yml` | — |
| Lockfiles present | Yes (both) | `uv.lock` and `frontend/package-lock.json`; verified in CI via `uv sync --locked` and `npm ci` |

---

## 2. Executive Summary

| Dimension | Grade | One-line finding |
|---|---|---|
| Architecture | **A−** | Router/service/repository layering followed consistently; shared `query_utils.apply_game_filters` used in 13 sites across 4 repos; `endgame_service.py` at 1,534 LOC is the one god-file outlier. |
| Code duplication | **A** | `apply_game_filters` is the single source of truth for filters; `DEFAULT_ELO_THRESHOLD` centralised in `query_utils.py:11`. No duplicated logic observed. |
| Error handling / Observability | **A−** | 12 `sentry_sdk.capture_exception()` sites across 6 files with deliberate retry-last-attempt discipline; `_sentry_before_send` fingerprints transient DB errors (`main.py:22-38`). Frontend mirrors via global `queryClient.ts` handlers. |
| Secrets / config | **A−** | No secrets tracked in git (`git ls-files` returns only `.env.example`); `prod.env` exists locally with real values but is gitignored. `SECRET_KEY` default is the placeholder `"change-me-in-production"`. |
| Code smells | **A** | Zero `TODO`/`FIXME`/`XXX`/`HACK` markers in `app/`, `tests/`, or `frontend/src/`. Knip + ruff + ty + eslint all gated in CI. |
| Maintainability / tests | **A** | ≈89% backend coverage, 49% test/code LOC ratio, real Postgres service container in CI, seven-gate pipeline (ruff → ty → pytest → eslint → build → vitest → knip). |
| Security | **A−** | OAuth CSRF double-submit cookie cites CVE-2025-68481 (`auth.py:85-96`); no raw SQL; PII-off Sentry; rate-limiter on guest signup. Minor: manual base64 decode of Google `id_token` without signature verification (defensible, fragile). |
| Database design | **A** | Every FK has explicit `ondelete=CASCADE` (6/6 models); deliberate `SmallInteger`/`Float(24)`/`BigInteger` choices with inline rationale; partial + covering indexes justified by workload. |
| Frontend quality | **A** | `strict` + `noUncheckedIndexedAccess` + `noUnusedLocals` enabled; **zero** `as any` / `@ts-ignore`; theme tokens centralised in `lib/theme.ts`; `data-testid` / `aria-label` discipline followed across 42 files. |
| Observability | **B** | Sentry fingerprinting both tiers, `/api/health`, `send_default_pii=False`. Missing: JSON/structured logging, request correlation IDs, slow-query hook, `/metrics` endpoint. |
| Performance | **A−** | N+1 deliberately avoided with documented batching (`openings_service.py:299-349`); covering index with `INCLUDE(material_imbalance)` for endgame aggregation; explicit `_BATCH_SIZE` tuning comment. No blocking I/O in async. |
| Disaster recovery / backups | **B−** | Hetzner automatic daily whole-server snapshots with 7-day retention cover a full disk loss (documented in README). No in-repo logical backup (`pg_dump`), no WAL archiving / PITR, no tested-restore record. |
| Data privacy / GDPR | **C+** | Privacy page exists at `/privacy`, honest about Sentry/Hetzner. Account deletion is email-only — no `DELETE /api/users/me` endpoint, though the `ondelete=CASCADE` schema would support one cleanly. |
| Dependency management | **C+** | Lockfiles committed and verified in CI; `python:3.13-slim` and pinned uv copy-from image. **No Dependabot / Renovate**, no `pip-audit` / `npm audit` in CI. |
| Frontend bundle / perf | **C+** | Main `index-*.js` is 998 KB raw / ≈285 KB gzipped — above the 250 KB mobile budget. **Zero code-splitting** (no `React.lazy` / dynamic `import(`). A stray 660 KB `prerender-*.js` also sits in `dist/`. Source maps not published. |
| CI/CD execution speed | **A** | Median 151 s across last 10 `main`-branch runs (min 140 s, one 15,250 s deploy-with-wait outlier). Single-job serial pipeline, already fast; manual `workflow_dispatch` deploy with SSH + `/api/health` check. |

**Bottom line.** FlawChess is a production-grade codebase on every axis relating to code craft: layering, DB design, type discipline, test coverage, Sentry wiring, and security fundamentals are all A-tier. The main finding a reviewer would flag is **no automated dependency updates (Dependabot/Renovate) and no vulnerability scanning in CI** — an unusual gap for a project otherwise this disciplined. Secondary items: the mobile-first PWA ships a single ≈285 KB-gzipped chunk with no code splitting, and backups lean entirely on Hetzner's daily-snapshot feature (7-day retention, no PITR, no logical-backup second layer). Remaining work is closing those gaps, not rewriting anything.

---

## 3. What the App Actually Does — Operational Picture

1. **Signup** via `POST /api/auth/register`, `/api/auth/google/authorize → /callback`, or `/api/auth/guest/create` (`app/routers/auth.py:40-231`). Guest creation is IP-rate-limited to 5/hour (`ip_rate_limiter.py:11-12`, applied at `auth.py:225`).
2. **Import** via `POST /api/imports` (`routers/imports.py:24-65`) — returns immediately, spawns a background `asyncio.create_task(import_service.run_import(job_id))`. Job state is kept in-process with a DB-backed fallback for post-restart visibility.
3. **Fetch** via `services/chesscom_client.py` (monthly archives, semaphore-gated, 150 ms inter-request delay) and `services/lichess_client.py` (NDJSON streaming). Both use `httpx.AsyncClient` only. Retries use exponential backoff with Sentry capture only on the final attempt.
4. **Normalise + classify** — every game passes through `services/normalization.py`, every position through `services/position_classifier.py` (material signature, imbalance, opposite-color bishops, backrank_sparse, mixedness, endgame class 1-6). Results are persisted in `game_positions` at import time, never re-derived at query time.
5. **Persist** — `import_service.py` commits in chunks of `_BATCH_SIZE = 28` games (`import_service.py:32-37`), a figure carefully tuned against the 7.6 GB + 2 GB swap Hetzner box.
6. **Query** — three analysis entry points:
   - **Openings** (`routers/openings.py` → `openings_service.py`): indexed lookup on `(user_id, full_hash | white_hash | black_hash)`.
   - **Endgames** (`routers/endgames.py` → `endgame_service.py`): uses the covering index `ix_gp_user_endgame_game` with `INCLUDE(material_imbalance)` (`game_position.py:29-34`) for index-only scans.
   - **Stats** (`routers/stats.py` → `stats_service.py`): time-series, ELO filtering, most-played.
7. **Bookmark** (`routers/position_bookmarks.py`): users save positions via Zobrist `target_hash`; FEN and SAN stored for display.
8. **Bulk delete games** (`DELETE /api/imports/games`, `routers/imports.py:162-174`) — cascades via FK. There is no counterpart `DELETE /api/users/me`.

### Deployment & infrastructure

- Stack: FastAPI/Uvicorn (Python 3.13) + React 19 SPA served by Caddy 2.11.2 + PostgreSQL 18 + Umami analytics, all in a single `docker-compose.yml`.
- Host: single Hetzner Cloud VM (4 vCPU / 7.6 GB RAM + 2 GB swap / 75 GB NVMe).
- Deploy flow: PR merges to `main` do NOT auto-deploy. `bin/deploy.sh` or a manual `workflow_dispatch` in GitHub Actions triggers the `deploy` job in `.github/workflows/ci.yml:78-123`, which SSHes in, pulls, rebuilds with `--no-cache`, and polls `/api/health` for up to 180 s.
- CI workflow: `.github/workflows/ci.yml` — gates in order: ruff → ty → pytest (with real Postgres service container) → eslint → `npm run build` → vitest → knip.
- Alembic migrations run automatically on backend container startup (`deploy/entrypoint.sh`).

### Disaster Recovery & Backups

- **Database backups:** Covered by **Hetzner's automatic daily whole-server backup** (7-day rolling retention), documented in `README.md` under "Backups & Recovery". No in-repo logical backup: grepping `bin/`, `deploy/`, `scripts/`, `.github/workflows/`, and both compose files for `pg_dump|pg_basebackup|wal-g|wal-e|barman|restic|borg` returns nothing.
- **Offsite storage:** Hetzner-managed snapshots live off the VM (in Hetzner's snapshot service). No secondary destination (S3 / Storage Box / B2).
- **Point-in-time recovery:** Not enabled. WAL archiving is off (`docker-compose.yml` sets `shared_buffers`, `work_mem`, `pg_stat_statements`; not `archive_mode` / `archive_command` / `wal_level=replica`). Snapshot cadence is daily, so RPO is up to 24 hours.
- **Restore procedure documented:** Partially. `README.md` now names the mechanism and retention; no step-by-step runbook for performing the restore in the Hetzner Cloud Console.
- **Last tested restore:** Unknown / not recorded.
- **RPO / RTO targets:** Not formally defined. RPO ≤ 24 h implied by daily snapshots; RTO governed by Hetzner snapshot-restore latency.

A full disk loss, VM loss, accidental `docker compose down -v`, or ransomware event is recoverable from yesterday's Hetzner snapshot. The gaps that remain are (a) no logical `pg_dump` second layer, so a corrupted-data incident that goes unnoticed for more than 7 days would exceed retention; (b) no WAL archiving, so losses within the last 24 hours are unrecoverable; (c) no tested restore. A nightly `pg_dump` piped to a Hetzner Storage Box (~€3.20/month for 1 TB) gives a longer-retention logical fallback and is ≈2 hours of work.

**Key insight.** The central architectural bet is **Zobrist-hash position matching stored at import time**. Every position for every user is reduced to three 64-bit integers (`full_hash`, `white_hash`, `black_hash`), indexed compositely with `user_id`. Position queries become indexed integer equality lookups, not FEN-string comparisons or PGN tree walks. The bet holds up: openings analysis, the system-opening filter via side-specific hashes, transposition counts, and next-move aggregation all fall out of it cleanly, and the ORM layer stays free of raw SQL.

---

## 4. Code Quality Findings

### 4.1 Architecture and layering

- Convention is documented in `CLAUDE.md:82-95` and followed: routers at `app/routers/` are HTTP-only, services at `app/services/` hold orchestration, repositories at `app/repositories/` hold DB access.
- Spot-checked `routers/openings.py`, `routers/users.py`, `routers/stats.py`, `routers/endgames.py`: no SQL, no business logic, only `Depends(get_async_session)` + `Depends(current_active_user)` + dispatch to services.
- Router prefix convention (`CLAUDE.md:104-113`) is followed. The one exception — `routers/auth.py:31` uses `APIRouter()` with no prefix — is legitimate because it composes FastAPI-Users sub-routers at different mount points.
- **One outlier god-file:** `services/endgame_service.py` is 1,534 LOC (confirmed via `wc -l`). It spans classification, aggregation, per-class span detection, and gauge computation. Splitting into `endgame_classification.py` + `endgame_aggregation.py` + `endgame_gauges.py` would be the single biggest readability win in the backend. No business rule lives in multiple places as a result, but the file is hard to hold in working memory.
- `services/__init__.py`, `repositories/__init__.py`, `routers/__init__.py` are all empty — no barrel re-exports, imports are by module. Clean.

### 4.2 Code duplication

- `apply_game_filters()` at `app/repositories/query_utils.py:13-78` is the single source of truth for time-control, platform, rated, opponent-type, color, recency, and opponent-strength filtering. Imported and called **13 times across 4 files** (`stats_repository.py`, `endgame_repository.py`, `openings_repository.py`, `query_utils.py`). No reimplementation observed.
- `DEFAULT_ELO_THRESHOLD = 50` (`query_utils.py:11`) is reused across `stats_service.py`, `endgame_service.py`, `routers/stats.py`, `routers/endgames.py`, `schemas/openings.py`. Exactly the "named constant, single definition" pattern the house style calls for.
- Pydantic schemas in `app/schemas/` are the only place filter request shapes are defined; router signatures use `Annotated[..., Depends]`, no ad-hoc dict typing.
- Frontend does not generate API types from OpenAPI — `frontend/src/types/api.ts` is hand-written. Minor drift risk, but not broken today.

### 4.3 Error handling and observability

- **12 `sentry_sdk.capture_exception()` sites across 6 files** in `app/` (ripgrep confirmed): `import_service.py` (5), `routers/auth.py` (3), `zobrist.py`, `endgame_service.py`, `openings_service.py`, `routers/position_bookmarks.py` (1 each). Reasonable density for 23 k LOC (~1 per 1,900 LOC).
- Retry discipline is deliberate and documented in-code: `chesscom_client.py:99-100` and `lichess_client.py:125-126` both carry comments saying "Sentry capture omitted — last-attempt error re-raises to run_import() top-level handler which calls capture_exception". This is exactly the noise-suppression pattern the rubric rewards.
- `_sentry_before_send` at `main.py:22-38` walks `__cause__` chains (capped at depth 5) to fingerprint `asyncpg.CannotConnectNowError` / `ConnectionDoesNotExistError` as a single Sentry issue. "`before_send` with fingerprinting" pattern present.
- Context/tags are used per the CLAUDE.md rule: e.g. `import_service.py` sets `sentry_sdk.set_context("import", {"job_id": ..., "user_id": ..., "platform": ...})` before capture — variables never land in the exception message itself.
- `except Exception:` blocks (≈12) are either (a) Sentry capture-and-reraise, (b) "never let tracking break a request" guards in `middleware/last_activity.py`, or (c) PGN-replay robustness in `openings_service.py`. No bare `except:`, no silent swallowing.
- Frontend: `lib/queryClient.ts` wires `QueryCache.onError` and `MutationCache.onError` into `Sentry.captureException` globally. `instrument.ts` drops 401s and regex-ignores browser-extension DOM noise.

### 4.4 Secrets and configuration

- `git ls-files | grep -E '^\.env|prod\.env'` returns **only `.env.example`**. `prod.env` exists locally with real production secrets but is gitignored and was never committed. Correct but narrow — the file is one `git add -A` from being leaked; consider moving it out of the repo tree.
- `app/core/config.py:8` — `SECRET_KEY: str = "change-me-in-production"` is an obvious placeholder. `tests/conftest.py` overrides with a 32-byte test value.
- `deploy/cloud-init.yml` uses `CHANGE_ME_STRONG_PASSWORD` / `CHANGE_ME_GENERATE_WITH_openssl_rand_hex_32` literal placeholders with `openssl rand -hex 32` comments.
- CI workflow references secrets via `${{ secrets.SSH_HOST }}`, `${{ secrets.SSH_USER }}`, `${{ secrets.SSH_PRIVATE_KEY }}`. No plaintext.
- Dockerfile is clean — no `ARG`-baked credentials, no `ENV` with real values, `FROM python:3.13-slim` (pinned major.minor, not digested but acceptable).
- Nit: `deploy/init-dev-db.sql` has `CREATE USER flawchess WITH PASSWORD 'flawchess'` which is fine for dev (prod uses `POSTGRES_PASSWORD` from compose) but a scanner may flag it. A one-line comment saying "dev only" would preempt.

### 4.5 Code smells

- **Zero** `TODO|FIXME|XXX|HACK|DEPRECATED` markers in `app/`, `tests/`, or `frontend/src/` (ripgrep across all three returns only a single hit inside `frontend/package-lock.json`, which is vendor content). Unusually clean for 36 k LOC.
- Magic numbers are consistently extracted:
  - `_BATCH_SIZE = 28` with rationale block (`import_service.py:32-37`)
  - `_MAX_CAUSE_CHAIN_DEPTH = 5` (`main.py:19`)
  - `_ACTIVITY_THROTTLE = timedelta(hours=1)` (`middleware/last_activity.py:30`)
  - `_GUEST_CREATE_MAX_REQUESTS = 5`, `_GUEST_CREATE_WINDOW_SECONDS = 3600` (`ip_rate_limiter.py:11-12`)
  - `DEFAULT_ELO_THRESHOLD = 50` (`query_utils.py:11`)
  - Frontend: `MIN_GAMES_FOR_RELIABLE_STATS = 10`, `UNRELIABLE_OPACITY = 0.5` (`lib/theme.ts`)
- Knip (dead-export detection) runs in CI; ruff catches `F401`/`F811` in Python; ESLint + `typescript-eslint` on the frontend. Dead-code detection is automated, not aspirational.

### 4.6 Maintainability and tests

- **36 test files, 17,806 test LOC, 49% test/code LOC ratio.** Framework: pytest + `pytest-asyncio` with `asyncio_mode = "auto"` and session-scoped loop (`pyproject.toml:31-33`).
- **Real Postgres in CI.** `.github/workflows/ci.yml:16-29` spins a `postgres:18-alpine` service container and exports `TEST_DATABASE_URL`. `tests/conftest.py` runs Alembic `upgrade head` against `flawchess_test` once per session and truncates tables (excluding `alembic_version` and the seeded `openings` reference table) between tests. Integration-test infrastructure, not mock-only.
- **~89% backend coverage** (from `.coverage` / `htmlcov/status.json`). Frontend coverage artifact not committed, though `@vitest/coverage-v8` was just added (`26ed58c`).
- **CI gates (all required):** ruff lint → ty type check (zero errors project-wide) → pytest → eslint → `tsc -b && vite build` → vitest → knip.
- **38 Alembic migrations, all with `downgrade()`.** Two are `pass`-only (data-repair migrations where reversing is a no-op: `20260403_200000_repair_bookmark_hashes_...` and `20260403_203535_repair_bookmark_fens_...`); the rest invert destructive changes including enum conversions. A one-line docstring on the `pass` cases would be cleaner but not blocking.
- No `pytest-xdist` / no parallelization. At ≈151 s median CI wallclock, this is not the bottleneck.

### 4.7 Security

- **Auth dependency applied uniformly.** `current_active_user` from `fastapi_users.current_user(active=True)` is attached on every state-changing and user-scoped endpoint across `openings.py`, `users.py`, `stats.py`, `endgames.py`, `imports.py`, `position_bookmarks.py`.
- **No raw SQL.** Grep for `text(` in `app/` returns 3 hits, all DDL (`postgresql_where=text("endgame_class IS NOT NULL")`, `server_default=text("false")`). No f-string / concatenation into `execute()`.
- **OAuth CSRF patched.** `auth.py:85-96` mints a `secrets.token_urlsafe(32)` CSRF token embedded in a 600-second audience-tagged JWT signed with `SECRET_KEY`, and sets a parallel `httpOnly` / `secure` / `samesite=lax` cookie. Callback verifies both with `secrets.compare_digest`. Comment explicitly cites CVE-2025-68481. A separate audience (`_OAUTH_PROMOTE_STATE_AUDIENCE`) prevents replay between login and guest-promote flows.
- **CORS.** `main.py:60-67` applies `CORSMiddleware(allow_origins=["http://localhost:5173"])` **only when `ENVIRONMENT == "development"`**; production relies on Caddy same-origin. Correct.
- **PII off.** `sentry_sdk.init(send_default_pii=False, ...)` at `main.py:53`. Frontend Sentry drops 401s entirely.
- **Password hashing.** Delegated to FastAPI-Users (bcrypt). No custom hashing code.
- **Rate limiting.** IP-based sliding window on guest account creation only (`ip_rate_limiter.py`, applied at `auth.py:225`). No rate limit on `/auth/jwt/login` or `/auth/register` — low-severity because brute force against a known email is the only attack, but worth noting.
- **Minor issue: unverified Google `id_token` base64 decode.** `auth.py:162-167` and `:360-365` split the id_token and base64-decode its payload without verifying the signature. A code comment acknowledges the tradeoff: "token was just received over TLS from Google". Defensible today, fragile against a future refactor. `google-auth`'s `id_token.verify_oauth2_token` would close the gap in ~2 lines.

### 4.8 Database design

- **Every FK has explicit `ondelete`.** 6/6 `ForeignKey` declarations across 6 model files all carry `ondelete="CASCADE"` (one uses lowercase `"cascade"` per FastAPI-Users convention). 100% compliance with `CLAUDE.md:118-120`.
- **Unique constraints on natural keys.** `games.uq_games_user_platform_game_id(user_id, platform, platform_game_id)` (`game.py:43-47`), `openings.uq_openings_eco_name_pgn` (`opening.py:10`). Prevents duplicate imports.
- **Column types are deliberate.** `BigInteger` for 64-bit Zobrist hashes; `SmallInteger` for `ply`, `material_count`, `material_signature` bytes, `eval_cp`, `eval_mate`, `endgame_class` (with a rationale comment at `game_position.py:81` citing GROUP BY speed and storage); `Float(24)` (REAL, 4 bytes) for `clock_seconds`, `white_accuracy`, `black_accuracy` rather than 8-byte DOUBLE PRECISION; `DateTime(timezone=True)` on user timestamps. No FLOAT-for-money.
- **Indexes are workload-justified.** `game_position.py:11-34` declares five indexes: three partial-hash composites for the three query paths, one covering index for next-moves aggregation, one partial + covering index for endgame GROUP BY with `postgresql_include=["material_imbalance"]` to support index-only scans. Each has a comment naming the query it serves.
- **Migration downgrade coverage.** 38/38 present; two `pass`-only (acceptable for data repair).
- PostgreSQL ENUM types (`gameresult`, `color`, `termination`, `timecontrolbucket`) declared at `game.py:19-38` with `create_type=False` so Alembic controls lifecycle — not `String` with a CHECK constraint; the type is enforced DB-wide.

### 4.9 Frontend quality

- `tsconfig.app.json:20-26` enables `strict`, `noUncheckedIndexedAccess`, `noUnusedLocals`, `noUnusedParameters`, `erasableSyntaxOnly`, `noFallthroughCasesInSwitch`, `noUncheckedSideEffectImports`. Maximum strictness.
- **Zero `as any` / `: any` / `@ts-ignore` / `@ts-expect-error`** across `frontend/src/` (ripgrep confirms 0 matches). Extraordinary for a 13 k LOC React codebase.
- **Theme centralised.** All semantic colors (WDL, gauge zones, endgame thresholds) live in `frontend/src/lib/theme.ts:6-73`. Spot-checked components use those tokens; stray hex literals only appear in shadcn-scaffolded `tabs.tsx` / `chart.tsx` or one-off neutral icon colors, not semantic usage.
- **Semantic HTML.** `<div onClick>` / `<span onClick>` returns zero matches. The mobile "More" nav is a proper `<button>` with `aria-label`.
- **Test-id discipline.** 358 occurrences of `aria-label` or `data-testid` across 42 files, following the kebab-case component-prefixed convention (`btn-import`, `nav-openings`, `chessboard`). Matches the `CLAUDE.md:366-383` browser-automation contract exactly.
- Knip in CI blocks dead exports from being merged.

### 4.10 Observability

- `_sentry_before_send` with `__cause__` walking (`main.py:22-38`). Good.
- `/api/health` (`main.py:85-87`) returns `{"status": "ok"}` — used by deploy health-check loop.
- `send_default_pii=False` — no user emails / IPs to Sentry.
- Umami self-hosted analytics (`docker-compose.yml:42-53`) for cookie-free page-view tracking.
- **Gaps.** No structured/JSON logging (`logging.getLogger(__name__)` + default string formatting across 5 files). No request-correlation ID (grep for `request_id|correlation_id|X-Request-ID` returns zero hits). No `/metrics` Prometheus endpoint. No SQLAlchemy `before_cursor_execute` slow-query hook. Uptime monitor not in the repo — possibly external but not verifiable from here.
- For a single-box single-maintainer service these are nice-to-haves. A minimal win: `python-json-logger` formatter + a `RequestIDMiddleware` that pushes a UUID header into `logging` contextvars.

### 4.11 Performance

- **N+1 awareness.** `openings_service.py:299-349` explicitly batches: one `DISTINCT ON (full_hash)` query picks representative games, one `IN`-clause query pulls PGNs, then PGN replay happens in-process. Comment at the top names the anti-pattern being avoided.
- **Async safety.** `asyncio.gather` is explicitly NOT used on a shared `AsyncSession` — `endgame_service.py:1415` and `endgame_repository.py:516, 602` carry comments saying "All queries run sequentially on one AsyncSession — no asyncio.gather" / "no concurrency benefit from asyncio.gather here". Matches `CLAUDE.md:263`.
- **Blocking I/O in async.** Grep for `requests\.|berserk|time\.sleep` yields only string-literal mentions in comments / docstrings. No blocking HTTP client, no `time.sleep` in async paths.
- **Batching.** `_BATCH_SIZE = 28` (`import_service.py:37`) with rationale block citing the 7.6 GB + 2 GB swap memory budget.
- **Index-only scans.** Endgame covering index with `postgresql_include=["material_imbalance"]` (`game_position.py:29-34`) is designed for GROUP BY on game_id, endgame_class with imbalance aggregation.
- **OOM mitigations.** Swap configured in production (`CLAUDE.md:178`); batch size tuned downward after OOM incident (visible in migration trail). Umami container capped via `NODE_OPTIONS: --max-old-space-size=256`.
- No Redis / no in-process cache — fine for a read-heavy app with well-tuned Postgres.

### 4.12 Disaster recovery and backups

Restating §3's finding: backups are provided by **Hetzner's automatic daily whole-server backup** with 7-day rolling retention, documented in `README.md` → "Backups & Recovery". Snapshots are managed by Hetzner and stored off the VM, so a full disk loss is recoverable from the previous day's snapshot through the Hetzner Cloud Console. The grep for in-repo backup tooling (`pg_dump`, `pg_basebackup`, `wal-g`, `barman`, `restic`, `borg`, `rsync`) returns nothing, which is expected — the backup layer lives in Hetzner's infrastructure, not in the repo.

Remaining gaps:
- **No logical `pg_dump` second layer.** A data-corruption bug that lands silently and only surfaces after 7 days cannot be rolled back — the daily snapshots have aged out by then. A nightly `docker exec -t db pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" | gzip | ssh storage-box 'cat > /backups/flawchess-$(date +%F).sql.gz'` with 30+ day retention on a Hetzner Storage Box (~€3.20/month for 1 TB) gives a longer-retention fallback. ≈2 hours.
- **No WAL archiving / PITR.** RPO is bounded at 24 hours (the daily snapshot cadence). For a service where 24 hours of lost imports would be painful, enabling `archive_mode = on` + `archive_command` into a bucket would bring RPO under a minute.
- **No tested restore.** The snapshot mechanism is documented but not exercised. A ~30-minute dry run against a temporary Hetzner instance would confirm the runbook and catch any surprises.
- **No step-by-step restore runbook.** README names the mechanism and retention but does not walk through "step 1 open Hetzner Cloud Console, step 2 select snapshot ..." detail.

Grade: **B−**. Daily offsite snapshots with 7-day retention are a real baseline. The grade reflects that baseline minus the gaps above — no PITR, no logical-backup second layer, no documented/tested restore runbook.

### 4.13 Data privacy and GDPR/FADP

- **Privacy policy** at `/privacy` (`frontend/src/pages/Privacy.tsx`). Honest about Sentry (IP + browser + action on error), Hetzner (EU/DE hosting), Umami (self-hosted, cookie-free), bcrypt.
- **Account deletion is email-only:** "request deletion ... by emailing support@flawchess.com" (`Privacy.tsx:58-69`). There is **no `DELETE /api/users/me` endpoint** (grep for `delete_account|deleteAccount|hard_delete|anonymize|DELETE.*users/me` returns zero hits). `DELETE /api/imports/games` exists but only clears games, not the user.
- The `ondelete=CASCADE` schema means a manual `DELETE FROM users WHERE id = X` cleanly cascades to games, game_positions, import_jobs, position_bookmarks, and oauth_account. The operator can comply; it requires a DB query rather than a user-facing button.
- **Data export** (right to portability): absent. No `GET /api/users/me/export` endpoint.
- **Consent flows:** `LoginForm.tsx` / `RegisterForm.tsx` do not require explicit checkbox consent. Defensible for a free service with linked privacy policy, though a lawyer would prefer a checkbox.
- `send_default_pii=False` on Sentry. Frontend drops 401s. No obvious PII in logs.

Grade is **C+** because the manual-deletion path works but is operator-dependent. A `DELETE /api/users/me` that triggers the cascade would take ≈30 minutes to write and lift the grade to A−.

### 4.14 Dependency management and supply chain

- **Automation:** `.github/` contains only `workflows/`. **No `dependabot.yml`**, **no `renovate.json`**, no scheduled `uv tree --outdated` / `npm outdated` workflow.
- **Lockfiles:** `uv.lock` and `frontend/package-lock.json` both tracked. CI verifies them: `uv sync --locked` and `npm ci`.
- **Audit tooling in CI:** **Absent.** No `pip-audit`, no `npm audit`, no `govulncheck`-equivalent. CI does not fail on known CVEs.
- **Base image pinning:** Dockerfile `FROM python:3.13-slim AS builder` (pinned major.minor, not digested but acceptable). `frontend/Dockerfile` uses `node:24-alpine` similarly. Caddy `2.11.2` exactly pinned. A nice pattern: `COPY --from=ghcr.io/astral-sh/uv:0.10.9 /uv /uvx /bin/` (Dockerfile:2) — pinned uv, no `curl | bash`.
- **Overall:** The thinnest supply-chain story in the report. The fix is cheap: a ~15-line `.github/dependabot.yml` covering `pip`, `npm`, and `github-actions` weekly, plus one `npm audit --omit=dev --audit-level=high` step in `ci.yml`. That alone lifts this dimension to A−.

### 4.15 Frontend bundle and performance

- **Production bundle size:** `frontend/dist/assets/` contains:
  - `index-EXE12nRt.js` = 998 KB raw / **≈285 KB gzipped** (typical Vite compression ratio)
  - `index-DXpbyF1R.css` = 96 KB
  - `prerender-B6s8BXE6.js` = 660 KB — this is the prerender entry and should not ship to clients; `index.html` does not reference it, but it's still in `dist/` and Caddy will serve it if requested directly. Either exclude from the final image or configure Caddy to 404 on it.
- **Code splitting / lazy loading:** **Zero.** Ripgrep for `React\.lazy|lazy\(|import\(` returns zero matches in `frontend/src/`. All 7 pages plus chart components (recharts), `react-chessboard`, `chess.js`, `@dnd-kit/*`, and `radix-ui` ship in the entry bundle. A user hitting `/privacy` downloads the chess engine and the chart library.
- **Tree-shaking:** `package.json` has no `"sideEffects"` field — default is `true`, limiting shaking. `"sideEffects": ["**/*.css"]` would help.
- **Source maps:** `dist/` contains `sw.js.map` and `workbox-*.js.map` but no main-bundle `index-*.js.map` — production source maps are NOT exposed. Good. Sentry source-map upload is not wired, though, so production stack traces in Sentry are minified-only.
- **Caching:** Vite content-hashes assets; Caddy sets `Cache-Control: public, max-age=31536000, immutable` on `/assets/*`. Correct.
- **PWA:** Installable, offline via workbox, `navigateFallback: null` with `/api/*` as `NetworkOnly` (`vite.config.ts:85-93`). Correct handling.

Grade **C+** on bundle / splitting; everything else is fine.

### 4.16 CI/CD execution speed

- **Observed workflow duration:** **Median 151 s** across the last 10 runs (min 140 s). A single 15,250 s outlier is a `workflow_dispatch` deploy that includes the 180 s health-check loop plus SSH-idle — representative only of deploy runs, not CI runs. Under the 5-minute "green" band for CI-only runs.
- **Test parallelization:** No `pytest-xdist`. Tests run serially. Not the bottleneck.
- **Dependency caching:** `actions/setup-python@v5` used without `cache: pip` (uv manages its own cache in-process); `actions/setup-node@v4` without `cache: npm` but `npm ci` against committed lockfile is deterministic. Not optimal (no runner cache hits between runs), but visibly fast enough.
- **Matrix / sharding:** None. Single job, single runner.
- **Deploy automation:** Manual `workflow_dispatch` with `inputs.deploy: true`. SSH + `docker compose build --no-cache backend caddy && docker compose up -d`, followed by a 180-second `/api/health` poll. A "fail fast if working tree dirty" guard on the remote (`ci.yml:98-102`) prevents production drift. Deploys are gated on `main` AND `workflow_dispatch` AND `inputs.deploy==true`, never on push — deliberate per `CLAUDE.md:211-212`.

---

## 5. Substantial Problems Worth Addressing

Numbered by priority, not by section order.

1. **No Dependabot / Renovate and no dependency audit in CI.** (§4.14) A single `.github/dependabot.yml` with `pip`, `npm`, and `github-actions` ecosystems on a weekly schedule, plus one `npm audit --omit=dev --audit-level=high` step in `ci.yml`, closes the whole gap. Highest leverage-per-minute item in the report for a project with 36 frontend deps and 12 Python deps. *(effort: ≈20 minutes)*

2. **Backup strategy relies on Hetzner daily snapshots only.** (§4.12, §3) The daily whole-server backup with 7-day retention handles full disk / VM loss but leaves three gaps: no logical `pg_dump` second layer (a silent data-corruption bug that goes unnoticed for >7 days exceeds retention), no WAL archiving (RPO bounded at 24 hours), and no tested restore. Add a nightly `pg_dump` to a Hetzner Storage Box with 30+ day retention, run one dry-run restore into a throwaway instance, and document the Hetzner Cloud Console restore flow in the README. *(effort: ≈2 hours)*

3. **`DELETE /api/users/me` endpoint missing.** (§4.13) The `ondelete=CASCADE` schema already does the hard part; the handler is essentially `await session.delete(user); await session.commit(); return 204`. Add it, wire a "Delete my account" button on the profile page, update the privacy policy to point at the button instead of email support. Converts the email-based GDPR path into self-service. *(effort: ≈45 minutes including a test)*

4. **Frontend bundle is a single ≈285 KB-gzipped chunk on a mobile-first PWA.** (§4.15) Route-level code splitting via `React.lazy(() => import('./pages/...'))` for `ImportPage`, `EndgamesPage`, `GlobalStatsPage`, `PrivacyPage` should trim the initial chunk by 30-40%. Add `"sideEffects": ["**/*.css"]` to `frontend/package.json` while you're there. Also confirm whether the 660 KB `prerender-*.js` is intentionally shipped — if not, exclude it from the production build or Caddy serve path. *(effort: ≈1 hour)*

5. **`endgame_service.py` is 1,534 LOC.** (§4.1) The one layering outlier. Split into `endgame_classification.py` (pure position-to-class logic), `endgame_aggregation.py` (SQL aggregation helpers invoked by repo + router), `endgame_gauges.py` (zone computation). No behaviour change; just brings the largest file below the ~500 LOC mental-TOC threshold. Do this after the test suite is green so you can lean on it. *(effort: ≈3 hours)*

6. **No JSON logs, no request correlation ID.** (§4.10) A single-box low-traffic service can live without this today, but as soon as you're correlating a Sentry issue with a DB query or an import timeout, you'll wish you had it. Add `python-json-logger` + a tiny `RequestIDMiddleware` that emits a UUID header and pushes it into `logging` contextvars. Consider a SQLAlchemy `before_cursor_execute` / `after_cursor_execute` pair to log queries above 500 ms at `warn`. *(effort: ≈2 hours)*

7. **`prod.env` with real production secrets sits in the repo tree.** (§4.4) Gitignored and never committed, so technically not leaked — but one careless `git add -A` from the wrong directory would leak it. Move to `~/.config/flawchess/prod.env` and adjust any loader reference. *(effort: ≈15 minutes)*

8. **Google `id_token` signature is decoded without verification.** (§4.7) `auth.py:162-167` and `:360-365` base64-decode the id_token payload and trust it because the TLS channel to Google is authenticated. Defensible today, brittle against a future refactor that proxies the token. `google-auth`'s `id_token.verify_oauth2_token(id_token, requests.Request(), CLIENT_ID)` closes the gap in ~2 lines. *(effort: ≈30 minutes)*

---

## 6. What's Notably Good

- **Zobrist-hash position matching stored at import time.** The central architectural bet. Three indexed 64-bit integers per position + composite `(user_id, *_hash)` indexes turn every board-state query into an integer equality lookup. `game_position.py:11-34`.
- **Single `apply_game_filters()` with 13 call sites across 4 repositories.** No duplicated filter logic anywhere. `query_utils.py:13-78`.
- **Complete FK-with-`ondelete` discipline — 6/6 models.** Every user-owned table cascades cleanly.
- **Covering indexes designed around real GROUP BY queries.** `ix_gp_user_endgame_game` with `postgresql_include=["material_imbalance"]` is an index-only-scan enabler with a comment explaining which query it serves.
- **Sentry retry-last-attempt discipline, documented in-code.** `chesscom_client.py:99-100` and `lichess_client.py:125-126` both carry the same citation comment. Noise suppression with rationale.
- **Zero `TODO`/`FIXME`/`XXX` across 36 k LOC**, zero `as any`/`@ts-ignore` across 13 k LOC of TypeScript. The code lives in the present.
- **`ty` type-check is a CI gate.** `ci.yml` fails the build on any error; suppressions in-source use the specific rule name and a reason.
- **Real Postgres in CI** via service container + per-session Alembic upgrade + between-test truncate (`ci.yml:16-29` + `conftest.py`). Integration tests, not mock theatre.
- **OAuth CSRF (CVE-2025-68481) double-submit cookie is textbook.** `auth.py:85-96` with timing-safe compare and distinct audiences for login vs. guest-promote flows.

---

## 7. Recommended Actions

### Immediate (this week — small, high signal)

1. **`.github/dependabot.yml` + `npm audit` step in CI** (Problem 1). ≈20 minutes.
2. **Move `prod.env` out of the repo tree** (Problem 7). ≈15 minutes.

### Short term (this month — quality-of-life)

3. **Nightly `pg_dump` to Hetzner Storage Box + documented restore runbook** (Problem 2). Secondary layer behind Hetzner's daily snapshots; covers the corruption-older-than-7-days scenario. ≈2 hours.
4. **`DELETE /api/users/me` endpoint + "Delete account" button** (Problem 3). ≈45 minutes.
5. **Route-level code splitting via `React.lazy`** (Problem 4). ≈1 hour.
6. **Verify Google `id_token` signature via `google-auth`** (Problem 8). ≈30 minutes.
7. **Commit a frontend coverage baseline** (`npx vitest run --coverage`). Not in the problems list, but rounds out the coverage story now that `@vitest/coverage-v8` is installed. ≈10 minutes.

### Medium term (next quarter — only if needed)

8. **Split `endgame_service.py` into three focused files** (Problem 5). ≈3 hours, no user-visible change.
9. **JSON logging + request correlation ID + slow-query warn threshold** (Problem 6). ≈2 hours.
10. **(If moving toward multi-process scale)** Replace in-memory caches — `_last_updated` (`middleware/last_activity.py`), the `_jobs` registry (`services/import_service.py`), and the IP rate limiter (`ip_rate_limiter.py`) — with Redis-backed equivalents. All three already comment on their single-process assumptions.

---

## 8. Bottom Line

FlawChess is an unusually disciplined single-maintainer codebase. Layering, database design, type safety, test coverage (≈89%), and Sentry wiring all meet a bar a reviewer would hold up as a reference. Zero TODOs in 36 k LOC, zero `as any` in 13 k LOC of TypeScript, every ForeignKey has `ondelete`, every except block either captures to Sentry or has a documented reason not to — this is craftsmanship, not "works on my machine". The weak spots are narrow and specific: **no Dependabot**, **no `DELETE /users/me` endpoint**, a **mobile-first PWA shipping a single ≈285 KB-gzipped chunk with no code-splitting**, and **backups that lean entirely on Hetzner's daily-snapshot feature** with no logical `pg_dump` / PITR second layer. Close those gaps in a focused afternoon and the project crosses from "very good open-source side project" to "production-ready small SaaS". There is no rewrite hiding in here.
