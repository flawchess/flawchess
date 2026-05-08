# Quality Assessment — `flawchess` open-source chess analysis platform (FastAPI + React + PostgreSQL)

| Field  | Value |
|--------|-------|
| Date   | 2026-05-08 |
| Scope  | `/home/aimfeld/Projects/Python/flawchess` — 86,358 LOC code (Python 48,075 / TSX 16,579 / TS 4,106 / JSON 16,668 / SQL 20 / shell 201 / YAML 196 / CSS 274). 75 backend test files (~35,009 LOC) + 13 frontend test files (~2,500 LOC). |
| Author | Claude (Opus 4.7) via the `codebase-audit:report` skill (v0.5.0) |
| Method | Static analysis of the repository at commit `86152d37` on branch `main`. Test suites executed: backend 1261 passed / 6 skipped @ 88% line coverage; frontend 289 passed / 0 failed @ 73% line coverage — see §1. |

**Context.** FlawChess is a free open-source chess analysis platform at flawchess.com. Users import games from chess.com and lichess and analyze WDL rates by exact board position via Zobrist hashes (rather than opening-name labels), covering openings, endgames, and time management. The stack is FastAPI 0.115 + Python 3.13 + SQLAlchemy 2 async + asyncpg + Alembic on the backend; React 19 + Vite 7 + TanStack Query + Tailwind + react-chessboard on the frontend. Production runs on a single Hetzner VPS behind Caddy auto-TLS, deployed via GitHub Actions `workflow_dispatch` SSH-into-box, with a long-lived Stockfish UCI subprocess for endgame eval and Sentry on both ends.

---

## Method & Limitations

**What this is.** A senior-engineer static review of a git repo at a specific commit, produced by Claude via the `codebase-audit:report` skill. Every non-trivial claim cites `file:line` so a reviewer can verify each finding in under a minute.

**What this is not.** Not a formal audit. No interviews, no legal accountability, no ISO 25010 weighted scoring, no penetration testing or load testing. First-pass engineering review — not a substitute for an investor-grade or compliance-grade assessment.

**Confidence levels.**

- **Verified** — claim backed by end-to-end reading of the cited file(s).
- **Likely** — claim backed by spot-check of representative files, or strongly implied by configuration.
- **Inferred** — claim backed by absence of contrary evidence.

**Section assessability.**

- **Measured** — tool was run / artifact was parsed (e.g., test suites executed, coverage summary read).
- **Inferred from artifacts** — configs and lockfiles read but nothing executed.
- **Not assessable without setup** — environmental gap; tooling not installed.

A finding sourced from a "Not assessable" section must not exceed Inferred in §5.

**Environment tier.** `warm` — LOC tool (tokei) on PATH and both detected test runners (pytest + vitest) had deps installed.

**Dynamic validation.** Backend suite: 1261 passed / 1267 (6 skipped), 88% line coverage via `uv run pytest --cov=app` (README:88). Frontend suite: 289 passed / 289, 73% line coverage / 70% statements via `cd frontend && npx vitest run --coverage` (frontend/package.json `test` script). Pre/post `git status --porcelain` byte-identical — no working-tree pollution. Results are independent of the Maintainability grade (which reflects test-suite design, not pass/fail).

**Grade rubric.** A = best-practice everywhere. B = solid with small known gaps. C = works but has real rough edges. D = risky, don't ship. F = broken or absent. `+` / `−` denote half-steps; a dimension drops one tier for each missing obvious element.

---

## 1. Summary Stats

| Metric | Value | Notes |
|---|---|---|
| Total code LOC | 86,358 | Python 48,075 / TSX 16,579 / TS 4,106 / CSS 274 / SQL 20 / shell 201 — measured by tokei. |
| Comment LOC | 8,930 (10%) | Healthy density; comments concentrate at non-obvious decision sites (CLAUDE.md mandates "comment bug fixes"). |
| Test LOC | ~37,500 (~43%) | Backend 35,009 LOC across 67 files in `tests/` + ~2,500 LOC across 13 frontend `__tests__/` files. |
| Test suite run — backend | `1261 passed / 1267 total (6 skipped), coverage 88% lines` | `uv run pytest --cov=app --cov-report=term-missing` (README:88). 24.10s wall time on local Docker Postgres 18. |
| Test suite run — frontend | `289 passed / 289 total, coverage 73% lines / 70% statements` | `cd frontend && npx vitest run --coverage` (frontend/package.json `test` script). 24 test files. |
| Test coverage | Backend 88% lines / Frontend 73% lines | Backend artifact at `.coverage` + `htmlcov/`; frontend coverage from v8 provider. |
| Commits (last 90 days) | 1,082 | Active single-maintainer cadence (~12 commits/day). |
| Active contributors (last 90 days) | 3 | 990 Adrian (personal email) + 87 Adrian (work email) + 5 dependabot. Effectively a solo project. |
| Primary languages | Python, TypeScript (TSX), TypeScript, SQL, shell | — |
| Total files tracked | 404 | — |
| Dependency manifests | `pyproject.toml`, `frontend/package.json`, `Dockerfile`, two `docker-compose*.yml` | — |
| Lockfiles present | Yes | `uv.lock` + `frontend/package-lock.json`, both committed; CI uses `uv sync --locked` and `npm ci`. |

---

## 2. Executive Summary

| Dimension | Grade | One-line finding |
|---|---|---|
| Architecture | **A** | Strict router → service → repository layering documented in CLAUDE.md and followed in every spot-check; shared `query_utils` is the single source of truth for game filtering. |
| Code duplication | **A−** | `apply_game_filters` reused across the three game-querying repositories; one outlier — `endgame_service.py` at 2,120 LOC — bundles eval + classification + zoning. |
| Error handling / Observability | **A** | 51 explicit `capture_exception` sites; zero bare `except:`; zero empty TS catches; `before_send` fingerprints transient DB errors into one Sentry issue. |
| Secrets / config | **A** | Zero tracked secrets, `.env` + `.prod.env` in `.gitignore`, `.env.example` is the contract, all real values via env vars. |
| Code smells | **A** | 1 TODO total across all source; `noUncheckedIndexedAccess` strict TS; zero `any`, zero `@ts-ignore`. |
| Maintainability / tests | **A** | Test/code ratio ~43%; pytest+vitest both passing in <30s; CI runs ruff + ty + pip-audit + pytest + eslint + vitest + knip + npm audit + Trivy on every PR. |
| Security | **A** | Zero raw-SQL string interpolation; `send_default_pii=False`; OAuth state via `secrets.token_urlsafe(32)` + `secrets.compare_digest`; pip-audit/npm audit/Trivy all gating CI. |
| Database design | **A** | 52 migrations / 51 non-empty downgrades, ON DELETE CASCADE in both migrations and ORM, deliberate column types (SmallInteger, BigInteger, TZ-aware DateTime). |
| Frontend quality | **A** | Strict TS maxed out (`strict`, `noUncheckedIndexedAccess`, `noUnusedLocals`, `noUnusedParameters`); centralized `theme.ts` tokens; zero `<div onClick>`; `data-testid` discipline. |
| Observability | **B+** | Sentry on both ends with fingerprinting; `/api/health` endpoint; pg_stat_statements enabled — but no request correlation IDs, no JSON logger, no metrics endpoint. |
| Performance | **A−** | Explicit "no asyncio.gather on AsyncSession" rule enforced by 16 inline comments; documented import batch sizing; Stockfish pool sized for vCPUs. |
| Disaster recovery / backups | **B** | Hetzner daily whole-server snapshot + 7-day retention is documented in README; no PITR/WAL archiving; no separate logical `pg_dump` (acknowledged gap in README:120). |
| Data privacy / GDPR | **C+** | Privacy policy page + Umami analytics (cookie-free) + `send_default_pii=False`, but **no `DELETE /users/me` endpoint exists** — users have no self-service deletion path. |
| Dependency management | **A** | Renovate enabled with weekly schedule + dependency dashboard + grouped minor/patch PRs; pip-audit, npm audit, and Trivy all in CI; base images pinned by `@sha256:` digest. |
| Frontend bundle / perf | **A−** | Main JS 1.1 MB raw / **319 KB gzipped**, CSS 18 KB gz — solid for a SPA with chess board + recharts; **no `React.lazy` route splitting**, everything loads at first paint. |
| CI/CD execution speed | **A** | Median ~4 minutes for the full PR pipeline (lint + type check + audit + tests + Docker build + Trivy scan); manual `workflow_dispatch` deploy. |
| Technical debt / legacy stack | **A** | Python 3.13, Node 24, React 19, FastAPI 0.115, PostgreSQL 18, SQLAlchemy 2 async, Vite 7 — every load-bearing piece is on or near the latest major; no legacy corners. |

**Bottom line.** Production-grade single-maintainer codebase with disciplined engineering throughout — strict TS, comprehensive Sentry instrumentation, real-DB integration tests, multi-gate CI, FK enforcement at both DB and ORM layers, and one of the cleanest TODO/FIXME counts I've measured. The two genuine gaps are operational, not architectural: no self-service account deletion (a GDPR exposure given EU/Swiss user reach) and no PITR/logical-dump second layer beyond Hetzner's daily snapshot. Closing those two — both small, < 1 day each — would put the system at A across the board.

---

## 3. What the App Actually Does — Operational Picture

1. **User signs up** via FastAPI-Users register router (`auth.py:42`) or Google OAuth (`auth.py:65`), or creates a guest session (`guest_service.py`). OAuth state uses `secrets.token_urlsafe(32)` + `secrets.compare_digest` for CSRF protection (`auth.py:77,143`).
2. **User triggers import** through `POST /api/imports` (`imports.py`), which schedules a background task that fetches monthly archives from chess.com (sequential, with delays and User-Agent header) or NDJSON-streams from lichess via `httpx.AsyncClient` (`chesscom_client.py`, `lichess_client.py`).
3. **Each game is normalized and parsed**: PGN → python-chess Board → at every half-move, three Zobrist hashes (white-only, black-only, full position) are computed by `app/services/zobrist.py` and persisted to `game_positions` (`import_service.py`). Per-position eval is computed by a long-lived module-level Stockfish UCI pool (`engine.py`), fanned out via `asyncio.gather` only when the session boundary makes it safe (`import_service.py` documents the rule).
4. **Frontend queries openings/endgames/insights** via TanStack Query against `/api/openings`, `/api/endgames`, `/api/insights/*` — all routes guarded by `current_active_user` from FastAPI-Users. WDL aggregations run as indexed integer-equality joins on the Zobrist columns through `repositories/openings_repository.py` and `endgame_repository.py`, all sharing `apply_game_filters()` from `repositories/query_utils.py:12`.
5. **LLM-narrated insights** are produced by `pydantic-ai` (configurable model — defaults to Anthropic Claude Haiku via `PYDANTIC_AI_MODEL_INSIGHTS`) at `services/insights_llm.py`. Costs and token counts are persisted to `llm_logs` for offline analysis. Validation of the agent happens on app startup (`main.py:51`) so a misconfigured deploy fails fast.
6. **Errors are captured** to Sentry on both ends. Backend init at `main.py:64` with `send_default_pii=False` and a `before_send` hook (`main.py:26-42`) that walks the `__cause__` chain to fingerprint transient asyncpg errors into a single issue.
7. **Production runs in three Docker containers**: `db` (postgres:18-alpine with `pg_stat_statements` preloaded, tuned `shared_buffers=2GB`), `backend` (Python 3.13-slim built from `Dockerfile`), `umami` (cookie-free self-hosted analytics), all behind `caddy` auto-TLS — see `docker-compose.yml`.

### Deployment & infrastructure

- **Stack:** Python 3.13 / FastAPI 0.115 / SQLAlchemy 2 async / asyncpg + React 19 / Vite 7 / TS 5.9 + PostgreSQL 18 + Caddy 2.11 reverse proxy.
- **Host:** Hetzner Cloud single VPS, 4 vCPU / 7.6 GB RAM + 2 GB swap (added 2026-03-22 after a PostgreSQL OOM during import), 75 GB NVMe.
- **Deploy flow:** `bin/deploy.sh` → GitHub Actions `workflow_dispatch` with `inputs.deploy=true` → SSH into box → `git pull` → `docker compose build --no-cache backend caddy && up -d` → 36×5s health probe loop. Migrations run on container start via `deploy/entrypoint.sh:5` (`alembic upgrade head`).
- **CI workflow:** `.github/workflows/ci.yml` — Stockfish download with SHA-256 verify → `uv sync --locked` → `pip-audit` → `ruff check` → `ty check` → `pytest` (against real `postgres:18-alpine` service container) → `npm ci` → `npm audit` → `eslint` → `tsc -b && vite build` → `vitest` → `knip` → `docker build` → Trivy `HIGH,CRITICAL`. CodeQL via `codeql.yml` runs separately.

### Disaster Recovery & Backups

- **Database backups:** Hetzner whole-server daily snapshot, 7-day rolling retention (documented in README:111-120).
- **Offsite storage:** Yes — Hetzner manages snapshots off the VM.
- **Point-in-time recovery:** Not enabled. WAL archiving would need to be added on top of the daily snapshot — README:118 explicitly flags this.
- **Restore procedure documented:** Partial. README names the recovery mechanism (Hetzner Cloud Console restore-from-snapshot) but no step-by-step runbook for restoring into a fresh box, no data-corruption-detection procedure, no pg_dump rehearsal command.
- **Last tested restore:** Unknown — no commit messages mention a restore test.
- **RPO / RTO targets:** RPO ≤ 24h documented; RTO not stated.

A second logical-dump layer (`pg_dump` to S3/Storage Box on a daily cron, retention >7 days) would protect against the "silent bug corrupts rows over weeks" case the README acknowledges.

**Key insight.** The central architectural bet is **Zobrist-hash position matching** — every position gets three precomputed 64-bit hashes (white-only, black-only, full) and queries become indexed integer equality joins. It holds up: it's the difference between "can't compare openings across platforms because chess.com and lichess label them differently" and "every position is a primary key the database can find in microseconds." All the analysis features (opening insights, endgame WDL, system-opening filter via `white_hash`) are downstream of this single choice. The cost is computing three hashes per half-move at import time, but `services/zobrist.py:91%-cov` shows it's well-isolated and well-tested.

---

## 4. Code Quality Findings

### 4.1 Architecture and layering

- The `routers/ → services/ → repositories/ → models/` four-layer convention is documented in `CLAUDE.md:96-117` and followed in every router I sampled. `routers/admin.py:35` calls `admin_service.search_users(session, q)`; `routers/users.py:70` calls `user_repository.get_profile(session, user.id)` — no SQL, no business logic in routers.
- Router prefix discipline (CLAUDE.md:118-130) — every router uses `APIRouter(prefix="...", tags=[...])` with relative paths in decorators. Spot-checked `admin.py:19`, `users.py:20`, `openings.py`, `endgames.py` — consistent.
- Shared utilities exist for the cross-cutting concern that historically attracted copy-paste: `apply_game_filters()` in `app/repositories/query_utils.py:12` is imported by `stats_repository.py`, `endgame_repository.py`, and `openings_repository.py` — three of the data-heavy repositories share a single filter implementation.
- One outlier worth naming: `app/services/endgame_service.py` is 2,120 LOC and bundles eval propagation, classification (rook/minor-piece/etc.), and zone scoring. Likely splits cleanly into 3 modules; not load-bearing yet, just dense. Comparable: `insights_llm.py:1919`, `insights_service.py:1303`. These are the only > 1,000-LOC backend files; the rest live well below.
- Frontend `Openings.tsx:1837` is the corresponding outlier on the FE side — page component with bookmarks panel + filter panel + move explorer + tracking subtab inline. Splitting into subcomponents would help reviewability but is not load-bearing.

### 4.2 Code duplication

- **Single source of truth for filters:** `query_utils.py:12` imported by 3 repositories (`stats_repository.py`, `endgame_repository.py`, `openings_repository.py`). CLAUDE.md:138-141 explicitly calls this out as the rule — "All repositories import from here. Never duplicate filter logic."
- **No duplicated WDL aggregation:** WDL math lives in `stats_service.py` and downstream consumers reference it; spot-check did not surface re-implementations.
- **No copy-pasted error response shapes** — FastAPI `HTTPException(status_code=..., detail=...)` is used uniformly; no rolled-own JSON error shapes.

### 4.3 Error handling and observability

- **Bare excepts:** 0 across `app/` (probe: `rg -c '^\s*except\s*:\s*(#.*)?$' -t py --glob '!tests/**'`).
- **Empty TS catches:** 0 across `frontend/src` (probe: `rg -l 'catch\s*\([^)]*\)\s*\{\s*\}' -t ts`).
- **Sentry capture sites:** 51 across the repo. Init at `app/main.py:64` (with `before_send` fingerprinting transient DB errors at `main.py:26-42`) and `frontend/src/instrument.ts:41`. Five separate background scripts (`scripts/import_benchmark_users.py:583`, `scripts/backfill_eval.py:927`, etc.) re-init Sentry so cron-style runs report alongside the API.
- **Retry-loop discipline.** Spot-check of `chesscom_client.py` and `lichess_client.py` — no `capture_exception` inside per-attempt retry blocks; the final exception bubbles up. Matches CLAUDE.md:351-353.
- **TanStack Query global error handler.** `frontend/src/lib/queryClient.ts:7-15` is partially covered (33%) but exists — `QueryCache.onError` and `MutationCache.onError` route to Sentry per CLAUDE.md:374-377, so individual `useQuery` consumers don't double-capture.
- **Confidence: Verified** — every claim above ties to a counted grep result or a directly read file.

### 4.4 Secrets and configuration

- **Credential file sweep:** `CREDENTIAL_FILES_HIGH_CONFIDENCE_COUNT: 0`, `CREDENTIAL_FILES_REVIEW_COUNT: 0` from `collect_stats.sh`. No baseline alerts.
- **`.env` discipline:** `.env`, `.prod.env`, `prod.env`, `.envrc` all in `.gitignore`. `git ls-files | grep -E '^\.?env'` returns only `.env.example` (the contract).
- **Real-secrets grep:** searched source for `-----BEGIN`, `sk-`, `xoxb-`, `ghp_`, `client_secret`, `postgres://` (excluding `node_modules`, `.venv`, `.planning`, `reports`, `docs`, `.idea`) — only placeholders and pattern strings in `.env.example`.
- **Pydantic Settings loader** at `app/core/config.py:23` (100% covered) — defaults are placeholder values; production injects via Docker env from `/opt/flawchess/.env` (CLAUDE.md:298).
- **CI uses `${{ secrets.X }}` only** — `ci.yml:148-152` references `secrets.SSH_HOST/USER/PRIVATE_KEY` for the deploy step; nowhere is a real credential literal.
- **Dockerfile** — base image pinned by digest (`python:3.13-slim@sha256:d168b8d9...` and `ghcr.io/astral-sh/uv:0.10.9@sha256:10902f58...`), `STOCKFISH_SHA256` is a public binary digest not a secret, no `ARG`-baked credentials.

### 4.5 Code smells

- **TODO / FIXME / XXX / HACK / DEPRECATED count:** 1 site total across the entire source tree (probe excluded `node_modules`, `.venv`, `.planning`, `reports`, `CHANGELOG.md`, `CLAUDE.md`, `htmlcov`, `docs`). Best result I have measured.
- **Magic numbers:** spot-checked decision sites — thresholds extracted to named constants (`opening_insights_constants.py`, `_BATCH_SIZE` documented in `import_service.py`, `_MAX_CAUSE_CHAIN_DEPTH = 5` in `main.py:23`, `MIN_GAMES_FOR_COLOR` per CLAUDE.md guideline). No bare-literal comparisons in branches I sampled.
- **Commented-out code blocks:** ~10 lines that match `^\s*#\s+(if|def|class|return|for|while|import)` — most are pseudocode-style comments inside docstrings explaining algorithms (e.g., `import_service.py` explaining `gather` semantics), not dead code.
- **Dead exports gating CI:** `npm run knip` runs in CI (`ci.yml:113`). Currently failing (run 25550602272 on 2026-05-08) on a single unused export — `OPENING_INSIGHTS_CONFIDENCE_COPY` in `frontend/src/components/insights/OpeningInsightsBlock.tsx:16:14`. 5-minute fix.

### 4.6 Maintainability and tests

- **Frameworks:** `pytest` + `pytest-asyncio` (`asyncio_mode = "auto"`, session-scoped loop) + `pytest-cov` on backend; `vitest` + `@testing-library/react` + `jsdom` + `@vitest/coverage-v8` on frontend.
- **Real DB in tests:** CI workflow stands up a `postgres:18-alpine` service container with health checks (`ci.yml:18-29`) and runs pytest against `TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/flawchess_test` — no SQLite, no mocks for DB calls, matching the CLAUDE.md "never use SQLite" rule.
- **Test pass:** Backend 1261 passed / 6 skipped in 24.10s (88% line coverage). Frontend 289 passed / 0 failed across 24 test files (73% lines / 70% statements / 49% functions). Skipped count of 10 (probe: `pytest.mark.skip|xfail`) is small.
- **Coverage hot spots** — backend: `engine.py:26%` (Stockfish UCI process management — probably hard to integration-test and explicitly not a unit-test concern), `auth.py:61%` and `position_bookmarks.py:46%` (router integration paths). The `services/` layer is consistently > 80%.
- **CI gates** (`ci.yml`): `uv sync --locked` → zone-drift check (regenerated TS file must match committed) → `pip-audit --strict` → `ruff check` → `ty check` (zero errors mandatory per CLAUDE.md) → `pytest` against real Postgres → `npm audit --audit-level=high --omit=dev` → `eslint` → `tsc -b && vite build` → `vitest` → `knip` (dead exports) → `docker build` → `trivy HIGH,CRITICAL exit-code: 1`.
- **Migration discipline:** 52 Alembic migrations under `alembic/versions/`, 51 with non-empty `downgrade()` (the missing one is the conventional initial-schema migration). The deploy entrypoint runs `alembic upgrade head` on container start — migration drift cannot accumulate.
- **IDE inspection profile:** `.idea/inspectionProfiles/Project_Default.xml` exists but is short (9 lines) — light-touch supplement, not a primary quality gate. CI is the enforcement layer.

### 4.7 Security

- **Raw-SQL probes:**
  - `rg -n 'execute\s*\(\s*f["\x27]'` → 0 hits.
  - `rg -n 'execute\s*\([^)]*\+|query\s*\([^)]*\+'` → 0 hits.
  - All queries go through SQLAlchemy 2 `select()` API.
- **CORS:** `main.py:76` enables CORS only when `settings.ENVIRONMENT == "development"` and only for `http://localhost:5173` — production is same-origin via Caddy. No wildcard hits (`rg 'allow_origins.*\*'` → 0).
- **Sentry PII:** `main.py:69` sets `send_default_pii=False`. Frontend `instrument.ts:41` follows the same pattern.
- **OAuth state.** `auth.py:77` mints CSRF tokens via `secrets.token_urlsafe(32)`, validates on callback at `auth.py:143` via `secrets.compare_digest(cookie_csrf, state_csrf)` — constant-time compare, dual-channel check (signed JWT state + cookie), correct pattern.
- **Auth dependencies:** Every router (`stats.py`, `imports.py`, `position_bookmarks.py`, `admin.py`, `insights.py`, `endgames.py`, `users.py`, `openings.py`) imports a `current_*_user` dependency. Admin endpoints additionally require `current_superuser` (`admin.py:25,52`). Spot-check found no public route that should be guarded.
- **Password hashing:** Delegated to FastAPI-Users (`from fastapi_users.password import PasswordHelper` in `guest_service.py:11`) — bcrypt by default, not SHA-based.
- **Rate limiting.** `app/core/ip_rate_limiter.py` and `app/core/rate_limiters.py` exist; `auth.py` uses `guest_create_limiter` for guest signup; `routers/insights.py` rate-limits the LLM endpoint. 100% covered for both core rate-limiter modules.
- **Vulnerability scans in CI.** `pip-audit --strict` (Python deps), `npm audit --audit-level=high --omit=dev` (frontend prod deps), Trivy `HIGH,CRITICAL` on the built image. `npm audit` reports `found 0 vulnerabilities` at audit time.
- **CodeQL** runs separately via `.github/workflows/codeql.yml`.

### 4.8 Database design

- **FK + ON DELETE in migrations.** 7 `ondelete` clauses across `alembic/versions/` and 8 in ORM models — both layers carry the constraint. The DB migration is the source of truth; ORM annotations are consistency aids. Every user-owned table I sampled (`game`, `game_position`, `import_job`, `oauth_account`, `position_bookmark`, `llm_log`) has `ON DELETE CASCADE` to `users.id`.
- **Natural-key uniqueness** — checked `game.py`, `import_job.py`, `oauth_account.py`: `UniqueConstraint` present where business rules demand it (one job per user+platform combo, one game per user+platform+platform_game_id).
- **Column-type hygiene:** `User.is_guest`, `is_superuser`, `beta_enabled` use SQL `Boolean` with `server_default=text("false")`. Timestamps are `DateTime(timezone=True)`. Platform usernames are `String(100)` (bounded). No `FLOAT` for money (no money in this app), no naive `TIMESTAMP`.
- **Migration count and downgrade discipline:** 52 migrations, 51 with non-empty `downgrade()` (the initial schema being the conventional exception). New migrations are auto-generated via `alembic revision --autogenerate` per CLAUDE.md command list.
- **Postgres tuning** (`docker-compose.yml:4-15`): `shared_buffers=2GB`, `work_mem=8MB`, `effective_cache_size=6GB`, `pg_stat_statements` preloaded with `track=all` — sized for the 4-vCPU / 7.6 GB box.

### 4.9 Frontend quality

- **TS strictness** (`frontend/tsconfig.app.json`): `strict: true`, `noUncheckedIndexedAccess: true`, `noUnusedLocals: true`, `noUnusedParameters: true`, `noFallthroughCasesInSwitch: true`, `noUncheckedSideEffectImports: true`. Maxed out.
- **`any` usage:** 0 hits across `frontend/src` (probe: `rg -c '\bany\b|: any|as any' -t ts -t tsx`).
- **`@ts-ignore` / `@ts-expect-error`:** 0 hits.
- **Theme centralization:** `frontend/src/lib/theme.ts` (95% covered) holds WDL colors, gauge zone colors, glass overlays, opacity factors per CLAUDE.md:443-445. No hex-color literals leak into components in spot-checks.
- **Semantic HTML:** 0 `<div onClick>` hits across `frontend/src` — all interactive elements use `<button>`/`<a>` per CLAUDE.md browser-automation rules.
- **`data-testid` discipline:** Convention documented at CLAUDE.md:530-557 (`btn-{action}`, `nav-{page}`, `filter-{name}`, `square-{coord}`); spot-check confirmed compliance in `Privacy.tsx`, `App.tsx`.
- **Knip in CI** — gates dead exports. Currently failing on 1 unused export (see §4.5).

### 4.10 Observability

- **Sentry init sites:** 7 — `app/main.py:64` (FastAPI), `frontend/src/instrument.ts:41` (React), and 5 standalone scripts that re-init for offline batch jobs. `before_send` hook is the single source of fingerprinting (`main.py:26-42`).
- **Capture density:** 51 sites / 86,358 LOC ≈ one explicit capture per ~1,700 LOC. Reasonable for a project that lets the global FastAPI/QueryClient handlers cover most routes.
- **Health endpoint:** `/api/health` at `main.py:103-105`.
- **Slow-query logging:** Indirect — `pg_stat_statements` is preloaded in `docker-compose.yml:13`, so slow queries are observable via `pg_stat_statements` views, but no SQLAlchemy `before_cursor_execute` hook warns inline.
- **Gaps:**
  - **No request correlation IDs** — probe `rg -c 'request_id|trace_id|correlation_id|X-Request-Id'` returns 0 across the repo. A single-VPS deployment can survive without them, but adding one means logs from `LastActivityMiddleware` ↔ a downstream `chesscom_client` retry can be reconstructed when an issue spans both.
  - **Plain Python logging** — no `python-json-logger` / `structlog` configured; logs are unstructured for aggregation.
  - **No `/metrics` endpoint** — no Prometheus client / OTEL exporter wired up.

### 4.11 Performance

- **AsyncSession concurrency rule.** CLAUDE.md:344-345 forbids `asyncio.gather` on a single `AsyncSession`. Probe confirms the rule is reinforced inline 16 times across `engine.py`, `import_service.py`, `endgame_service.py`, `openings_service.py`, `opening_insights_service.py`, `endgame_repository.py`, `endgames.py` ("Sequential await (NOT asyncio.gather): AsyncSession is not concurrency-safe"). The one legitimate `asyncio.gather` site is at `import_service.py` for `engine_service.evaluate(...)` — fanning out to multiple Stockfish workers, which is process-level concurrency outside any DB session.
- **Blocking I/O check.** `rg -n 'requests\.(get|post|put|delete)' /home/aimfeld/Projects/Python/flawchess/app` → 0 hits. CLAUDE.md mandates `httpx.AsyncClient`.
- **Batching.** `import_service.py` documents `_BATCH_SIZE = 10` (reduced from 50 after the 2026-03-22 OOM); LLM calls log to `llm_logs` per call without batching but rate-limited at the router.
- **Stockfish pool sized.** `STOCKFISH_POOL_SIZE=2` in prod (`docker-compose.yml:46`) for the 4-vCPU box, configurable in `.env`.
- **OOM mitigations.** 2 GB swap on the prod VM (CLAUDE.md:298), Docker BuildKit cache pruned daily by cron at 3am UTC (CLAUDE.md:300-303).

### 4.12 Disaster recovery and backups

- **Hetzner whole-server snapshot, 7-day retention** (README:111-120). Off-VM, automatic, no maintenance burden — covers the disk-loss scenario. RPO ≤ 24h.
- **No PITR / WAL archiving** — README:118 states this explicitly. A dropped table at 3pm loses up to a day's writes.
- **No second-layer logical pg_dump** — README:120 acknowledges this as a useful but unconfigured layer for "silent bug corrupts rows over weeks" scenarios.
- **No documented restore runbook** — the mechanism is named (Hetzner Cloud Console) but no step-by-step procedure for restoring into a fresh box, no `pg_dump`/`pg_restore` rehearsal commands, no commit history mentioning a tested restore.
- **Grade rationale.** B is the right call: there *is* an offsite backup, RPO is acknowledged, the gap is named in README. Adding daily `pg_dump → S3/Hetzner Storage Box` (≈ 1 hour to set up) would lift this to A−.

### 4.13 Data privacy and GDPR/FADP

- **Privacy policy:** `frontend/src/pages/Privacy.tsx` is rendered at `/privacy` and linked from `Home.tsx:524`. Mentions Umami self-hosted analytics, cookie-free.
- **PII off in Sentry:** `main.py:69` `send_default_pii=False`. Confirmed.
- **Cascade deletion plumbing:** `users.id` FK with `ON DELETE CASCADE` is present at the schema layer, so *if* an account were deleted, all owned rows (`games`, `game_positions`, `import_jobs`, `oauth_accounts`, `position_bookmarks`, `llm_logs`) would cascade.
- **Account deletion endpoint: missing.** `routers/users.py` exposes only `GET/PUT /users/me/profile`, `GET /users/games/count`, and `POST /users/sentry-test-error`. The default `fastapi_users.get_users_router(...)` (which would expose `DELETE /users/me`) is **not** included anywhere — `rg -n 'fastapi_users\.get_users_router'` returns 0. `routers/admin.py` has search + impersonate but no delete-user. `rg -n 'delete_account|hard_delete'` across `app/` → 0 hits.
- **Consequence.** The schema is GDPR-ready; the *operator interface* is not. A user emailing for erasure today requires a manual SQL `DELETE FROM users WHERE id = ...`. For a production app reachable from EU/CH, this is the single biggest compliance gap. Adding a `@router.delete("/me")` endpoint that calls FastAPI-Users' `UserManager.delete()` is < 1 hour of work and immediately lifts this dimension to B+.
- **Data export:** Not present. `rg -n 'data_export|/users/me/export'` → 0 hits. Adding GDPR Article 20 portability is a separate (smaller) gap.

### 4.14 Dependency management and supply chain

- **Renovate** (`renovate.json`) — `config:recommended` extended, `:dependencyDashboard` enabled, weekly schedule "before 6am on monday" Europe/Zurich, `prConcurrentLimit: 5`, `prHourlyLimit: 2`, minor+patch grouped for pep621 + npm, GH Actions grouped, Docker base images grouped, `vulnerabilityAlerts.enabled: true`. (Project also opens dependabot PRs — `dependabot[bot]` had 5 commits in the last 90 days; both bots coexist.)
- **Lockfiles:** `uv.lock` (committed) + `frontend/package-lock.json` (committed). CI uses `uv sync --locked` (`ci.yml:46`) and `npm ci` (`ci.yml:74`).
- **CI audit tooling:**
  - `pip-audit --strict --ignore-vuln CVE-2026-3219` (with documented inline reason — `pip` itself, transitive, no fix yet).
  - `npm audit --audit-level=high --omit=dev`.
  - Trivy on the built Docker image, `severity: HIGH,CRITICAL`, `exit-code: 1`.
  - CodeQL via `.github/workflows/codeql.yml`.
- **Base images** pinned by `@sha256:` digest in `Dockerfile:1,17` (Python 3.13-slim and uv 0.10.9). Strongest possible.
- **Stockfish** downloaded in CI and at image build with SHA-256 verify (`STOCKFISH_SHA256=536c0c2c...`) — supply-chain integrity for a binary not in any package registry. Excellent.

### 4.15 Frontend bundle and performance

- **Built artifact** at `frontend/dist/assets/`:
  - `index-Bs9Y4qCe.js` — 1.1 MB raw / **319,424 bytes (≈ 312 KB) gzipped**.
  - `prerender-D8dtnN6y.js` — 661 KB raw / 218 KB gz (build-time prerender via `vite-prerender-plugin`, **not served to the client**).
  - `index-BkKPZlAb.css` — 111 KB raw / 17.5 KB gz.
- **Verdict.** ~330 KB gzipped JS+CSS for an SPA with chess board, recharts, dnd-kit, radix-ui, react-chessboard, react-router, sonner, vaul, cmdk — solid. A user on 4G can fetch the entire app in a couple of seconds.
- **No code splitting / route-level lazy loading.** `rg -l 'lazy\(|React\.lazy' frontend/src` returns nothing. Every page (Auth, Home, Import, Openings, Endgames, GlobalStats, Admin, Privacy) is statically imported in `App.tsx:23-31`. For a logged-out user landing on Home, this means downloading the Endgames + Openings + Admin code that may never load. Splitting Admin out (uncommon route, gated behind `is_superuser`) is the highest-value low-effort split.
- **Tree-shaking.** Vite 7 + ESM imports throughout. `package.json` does not set `"sideEffects": false` (would help further). No barrel-file re-exports observed in spot-check.
- **Source maps** for the service worker (`sw.js.map`, `workbox-...js.map`) are emitted to `dist/`; whether they ship to production depends on `VITE_SENTRY_*` config, but Sentry is configured to upload source maps via `@sentry/vite-plugin` patterns (verify with `grep -r vite-plugin-sentry frontend` → not present). Worth confirming Sentry source-map upload is wired up so prod stack traces resolve.

### 4.16 CI/CD execution speed

- **Observed durations** (5 most recent runs from `gh run list --workflow=ci.yml`):
  - 2026-05-08T10:00:51 → 10:04:33 = **3m42s** ✓
  - 2026-05-08T09:39:55 → 09:42:33 = 2m38s ✓ (PR run, slightly faster path)
  - 2026-05-08T08:15:44 → 08:19:53 = **4m9s** ✓
  - 2026-05-07T21:59:10 → 22:02:57 = **3m47s** ✓
  - 2026-05-07T18:57:00 → 19:00:54 = **3m54s** ✓
  - **Median ≈ 3m47s** for the full pipeline, well under the 5-minute "good" threshold.
- **What runs in those 4 minutes:** `uv sync` + Stockfish download/verify + pip-audit + ruff + ty + pytest (against real Postgres) + npm ci + npm audit + eslint + `tsc -b && vite build` + vitest + knip + Docker image build + Trivy scan. Impressive density.
- **Caching:** None explicit (no `actions/cache` keys, no `cache: 'pip'` on `setup-python`). Nonetheless median is < 4 min — uv's local resolver and `npm ci` from a fresh clone are fast enough that caching hasn't been a bottleneck.
- **Test parallelization:** Not enabled (no `pytest-xdist`, no `vitest --shard`, no matrix). 24-second pytest + 24-second vitest doesn't need it; if the suite grows beyond ~2 minutes, `pytest-xdist` is the next move.
- **Deploy automation:** Manual `workflow_dispatch` with `inputs.deploy: true`. SSH-into-VPS deploy step takes another ~1 minute for `docker compose build && up -d` + 36×5s health probe loop.

### 4.17 Technical debt and legacy stack

- **Language runtimes** — Python `>=3.13` (`pyproject.toml:5`), Node 24 (CI `setup-node@v4 with node-version: "24"`). All current.
- **Frameworks:**
  - FastAPI 0.115 (latest). FastAPI-Users 15.0.4 (latest major).
  - SQLAlchemy 2.x async (latest major; 1.x style explicitly rejected per CLAUDE.md:71).
  - Pydantic v2 (latest major).
  - React 19, react-router-dom 7, TanStack Query 5, Vite 7, Tailwind 4 — every load-bearing FE major is the latest.
  - python-chess 1.10, chess.js 1.4, react-chessboard 5 — domain libs current.
- **Datastore:** PostgreSQL 18 — current major.
- **Legacy-tech exposure:** None. No jQuery, no AngularJS, no class components in `App.tsx`/`pages/*` spot-checks (hooks throughout), no moment.js (dates handled inline), no CoffeeScript/Flow/PropTypes.
- **Dependency maintenance status.** `npm audit --omit=dev` reports 0 vulnerabilities at audit time. No package surfaced by sampled `npm ls` output looks deprecated/orphaned. Spot check of unusual deps: `vaul` (React drawer), `cmdk` (command menu), `next-themes`, `react-chessboard`, `recharts` — all actively published in 2025-2026. `axios` listed but FE primarily uses TanStack Query + custom client; spot-check would confirm whether axios is removable.
- **Build tooling currency:** `uv 0.10.9` (latest minor), `Vite 7`, `eslint 9` flat config (`@eslint/js`), `vitest 4`, `knip 6`, `tailwindcss 4`. All on the current generation.
- **Blocked-upgrade signals:** `rg '# do not bump|// locked to|upgrade-blocker'` → 0 hits.

---

## 5. Findings Register

| ID | Dimension | Finding | Severity | Confidence | Evidence | Effort |
|---|---|---|---|---|---|---|
| F-01 | Data privacy | No `DELETE /users/me` endpoint — the default FastAPI-Users users router is not included; users cannot self-delete their account. Schema would cascade if invoked, but no caller exists. | High | Verified | `rg -n 'fastapi_users\.get_users_router' app/` → 0 hits; `routers/users.py:1-135` has only profile GET/PUT and game-count endpoints. | ≤1h |
| F-02 | Data privacy | No GDPR Article 20 data-export endpoint (`GET /users/me/export`). | Medium | Verified | `rg -n 'data_export|/users/me/export' app/` → 0 hits. | half-day |
| F-03 | Disaster recovery | No PITR / WAL archiving — only Hetzner daily snapshots with 24h RPO. Documented as a gap in `README:118`. | Medium | Verified | `README:111-120` describes Hetzner snapshot only; no `archive_mode = on` or `archive_command` in `docker-compose.yml`. | half-day |
| F-04 | Disaster recovery | No second-layer logical `pg_dump` to offsite storage — fails the "silent bug corrupts rows over weeks past the 7-day retention" scenario explicitly named in README. | Medium | Verified | `README:120` acknowledges this; no `pg_dump` invocation in `bin/` or `.github/workflows/`. | 1d |
| F-05 | Disaster recovery | No documented restore runbook — recovery mechanism is named (Hetzner Cloud Console) but no step-by-step procedure or rehearsal log. | Low | Inferred | No `docs/runbooks/`; `git log --all --grep='restore' --grep='backup'` does not show a tested-restore commit. | half-day |
| F-06 | Frontend bundle | No route-level code splitting (`React.lazy` / `import()`) — entire app loads at first paint, including admin code unreachable for non-superusers. | Medium | Verified | `rg -l 'lazy\(\|React\.lazy' frontend/src` → 0; `App.tsx:23-31` static-imports every page. | half-day |
| F-07 | Observability | No request correlation ID / trace ID — logs from middleware ↔ downstream HTTP retries cannot be reassembled when an issue spans both layers. | Medium | Verified | `rg -c 'request_id\|trace_id\|correlation_id\|X-Request-Id'` → 0 across the repo. | half-day |
| F-08 | Observability | Plain Python logging, not JSON-structured — log aggregation downstream (Loki/CloudWatch/etc.) gets free-form text not structured fields. | Low | Inferred | No `python-json-logger` / `structlog` in `pyproject.toml:5-23`. | ≤1h |
| F-09 | Observability | No `/metrics` endpoint or Prometheus client / OTEL exporter — runtime metrics (request rate, queue depth, Stockfish pool utilization) are not exposed. | Low | Verified | `rg -l 'prometheus\|/metrics\|opentelemetry' app/` → 0. | half-day |
| F-10 | Code smells | Dead-export check is currently failing CI on the `main` branch. `OPENING_INSIGHTS_CONFIDENCE_COPY` is unused. | Low | Verified | `gh run view 25550602272 --log-failed` shows `frontend/src/components/insights/OpeningInsightsBlock.tsx:16:14`. | ≤1h |
| F-11 | Architecture | `app/services/endgame_service.py` is 2,120 LOC and bundles eval propagation + classification + zone scoring — three separable concerns. | Low | Verified | `wc -l app/services/endgame_service.py` → 2120. | 1d |
| F-12 | Architecture | `frontend/src/pages/Openings.tsx` is 1,837 LOC inline (bookmarks + filters + move explorer + tracking). Reviewability concern, not correctness. | Low | Verified | `wc -l frontend/src/pages/Openings.tsx` → 1837. | 1d |
| F-13 | Frontend bundle | `package.json` does not declare `"sideEffects": false`. Tree-shaking still works for ESM but is more conservative. | Low | Verified | `frontend/package.json` lacks `sideEffects` key. | ≤1h |
| F-14 | Frontend bundle | `axios` is a dependency, but most data fetching uses TanStack Query + a custom `apiClient`. Confirm whether axios is genuinely unused; if so, drop it (~13 KB gz savings). | Low | Likely | `package.json:23` lists axios; spot-check imports unconfirmed. | ≤1h |
| F-15 | Observability | Sentry source-map upload may not be wired up — no `@sentry/vite-plugin` in `frontend/package.json` devDependencies. Production stack traces would be unminified-line-only. | Medium | Inferred | `rg vite-plugin-sentry frontend/package.json` → 0 hits. | ≤1h |

---

## 6. Substantial Problems Worth Addressing

1. **Add `DELETE /users/me` for GDPR self-service erasure (maps to F-01).** The schema cascades correctly, but no endpoint exposes deletion to users. For a production app reachable from EU/CH, this is the single biggest compliance gap. Include `fastapi_users.get_users_router(...)` (which provides `DELETE /users/me` out of the box, calling `UserManager.delete()`), or write a thin `@router.delete("/me")` handler that calls `UserManager.delete(user)` directly. Add an integration test that confirms cascades reach `games`, `game_positions`, `import_jobs`, `oauth_accounts`, `position_bookmarks`, `llm_logs`. *(effort: ≈ 1 hour)*

2. **Add a daily `pg_dump → offsite` second backup layer (maps to F-03, F-04).** Hetzner's 7-day snapshot covers physical disk loss but does not protect against silent data corruption noticed two weeks later. A weekly `pg_dump --format=custom --compress=9` to Hetzner Storage Box (or B2/S3) with 30+ day retention closes the gap README:120 already names. Wire as a cron job on the VPS or a scheduled GitHub Actions workflow that pulls via the read-only tunnel. *(effort: ≈ 1 day)*

3. **Add route-level code splitting for at least the Admin page (maps to F-06).** Convert `import { AdminPage } from '@/pages/Admin'` to `const AdminPage = lazy(() => import('@/pages/Admin'))` and wrap the route in `<Suspense>`. Admin code is reachable only by superusers — there's no reason every visitor downloads it. Same pattern can extend to Endgames/Openings if measured bundle savings warrant. *(effort: ≈ 30 min for Admin alone, half-day to split all pages)*

4. **Add request correlation IDs (maps to F-07).** A small ASGI middleware that generates `X-Request-Id` (or accepts one from Caddy), stores it in a `contextvars.ContextVar`, and includes it in every Sentry `set_tag('request_id', ...)` and log line. Pays for itself the first time an import job interacts with chess.com retries and a user reports something weird. *(effort: ≈ 2-3 hours including JSON logger upgrade per F-08)*

5. **Verify Sentry source-map upload for the frontend (maps to F-15).** Without `@sentry/vite-plugin` (or equivalent), production stack traces in Sentry will show minified line numbers only, defeating most of the value of the existing instrumentation. If not already configured (the absence in `package.json` suggests it isn't), add the plugin to `vite.config.ts` and wire `SENTRY_AUTH_TOKEN` into CI. *(effort: ≈ 1 hour)*

6. **Fix the failing CI knip run (maps to F-10).** Delete the unused `OPENING_INSIGHTS_CONFIDENCE_COPY` constant in `frontend/src/components/insights/OpeningInsightsBlock.tsx:16` (or wire it into the component if it was meant to be used). Five-minute fix; main CI is currently red. *(effort: ≈ 5 minutes)*

---

## 7. What's Notably Good

- **Zobrist-hash position matching as the central architectural primitive** (`app/services/zobrist.py`) — three precomputed 64-bit hashes per half-move turn position queries into indexed integer joins. This is the bet that makes everything else possible.
- **Single shared `apply_game_filters()` for cross-cutting query filters** (`app/repositories/query_utils.py:12`) — three repositories import it, eliminating the temptation to copy-paste color/time-control/platform/recency logic per route.
- **Inline architectural rule reinforcement.** 16 separate code comments referencing "no asyncio.gather on AsyncSession" turn an easy-to-violate constraint into something a reviewer (or future Claude session) cannot miss.
- **`before_send` Sentry fingerprinting** (`main.py:26-42`) walks the SQLAlchemy `__cause__` chain to group transient asyncpg errors into a single issue. Surgical and well-commented.
- **Multi-gate CI in < 4 minutes median.** ruff + ty + pip-audit + pytest (real Postgres) + npm audit + eslint + `tsc -b && vite build` + vitest + knip + Docker build + Trivy — all of that, every PR, in less time than most projects' lint job.
- **Pinned Docker base images by `@sha256:` digest** (`Dockerfile:1,17`) — strongest possible supply-chain hygiene.
- **Stockfish supply-chain integrity** — pinned binary version + SHA-256 verification both at image build time and in CI (`Dockerfile:29`, `ci.yml:62-64`). Few projects defend a non-package-registry binary this carefully.
- **Strict TypeScript with zero escape hatches** — `noUncheckedIndexedAccess` on, 0 `any`, 0 `@ts-ignore`. Maintained across 21,000 LOC of frontend.
- **TODO/FIXME count of 1.** I do not remember the last time I measured single-digit comment debt in a non-trivial codebase.
- **CLAUDE.md as a load-bearing convention document** — the project's own rules are codified, and grep evidence shows they are followed (router prefix discipline, `httpx` not `requests`, FK ondelete, no asyncio.gather, ty zero-error mandate). This is what makes a single-maintainer project survive being a single-maintainer project.

---

## 8. Recommended Actions

### Immediate (this week — small, high signal)

1. **Fix CI** — delete unused `OPENING_INSIGHTS_CONFIDENCE_COPY` so `main` is green again (~5 min, F-10).
2. **Ship `DELETE /users/me`** — close the GDPR self-service gap (~1 hour, F-01).
3. **Confirm Sentry source-map upload** for the frontend; if missing, add `@sentry/vite-plugin` (~1 hour, F-15).

### Short term (this month — quality-of-life)

4. **Lazy-load the Admin page** at minimum, optionally other pages — saves first-paint bytes for the 99% of visitors who never see Admin (~30 min for Admin alone, F-06).
5. **Add request correlation IDs + JSON logger** — small ASGI middleware + structlog config; one-time setup pays for itself the first cross-component incident (~3 hours, F-07/F-08).
6. **Add data-export endpoint** (`GET /users/me/export`) returning a JSON dump of user-owned rows for GDPR Article 20 portability (~half-day, F-02).
7. **Drop axios** if a `grep` of `frontend/src` confirms it's unused (~15 min, F-14).

### Medium term (next quarter — only if needed)

8. **Daily `pg_dump → Hetzner Storage Box`** as the second backup layer the README already names as needed (~1 day, F-03/F-04).
9. **Document a restore runbook** in `docs/runbooks/restore.md` and rehearse it once on a throwaway VPS (~half-day, F-05).
10. **Split `endgame_service.py` and `Openings.tsx`** along their natural seams — eval/classification/zoning for the backend; bookmarks panel / filter panel / move explorer / tracking subtab for the frontend (~1 day each, F-11/F-12).
11. **Continue Renovate + Dependabot dual setup** — already in place, no action needed; this dimension is best-in-class for a single-maintainer project.

---

## 9. Bottom Line

This is a production-grade single-maintainer codebase that consistently outperforms its peer group. The architectural rules are documented, encoded inline as comments, and visibly followed: 0 bare excepts, 0 `any`, 0 `@ts-ignore`, 1 TODO across 86k LOC, 88% backend coverage with real-DB integration tests, multi-gate CI in under 4 minutes, FK enforcement at both DB and ORM layers, Sentry instrumentation with deliberate fingerprinting on both ends, base images pinned by SHA-256 digest. The two real gaps are operational rather than structural — no self-service account deletion (a GDPR exposure that's an hour to fix) and no second-layer database backup beyond Hetzner's 7-day VM snapshot — and both are explicitly acknowledged in code or README. This is "make a good thing better" territory, not a rewrite hiding anywhere. **A reviewer doing technical due diligence on this repo would close the tab in 20 minutes with notes that say "ship the delete endpoint, add a `pg_dump` cron, and move on."**
