# Phase 22: CI/CD & Monitoring - Research

**Researched:** 2026-03-21
**Domain:** GitHub Actions CI/CD, Sentry error monitoring (Python/FastAPI + React)
**Confidence:** HIGH

## Summary

Phase 22 wires together two independent concerns: automated deploy pipeline via GitHub Actions and production error visibility via Sentry. Both are well-understood, heavily documented domains with stable tooling — research found no significant gotchas beyond the specifics already locked in CONTEXT.md.

The CI/CD pipeline follows a standard pattern: push to main triggers a job that runs pytest (with a PostgreSQL service container), ruff check, and npm lint; on success it SSHes into the VPS and runs `docker compose up -d --build`, then polls `/api/health`. No GHCR involved — the build happens on the server, matching the existing manual deploy flow exactly.

Sentry integration is straightforward on both sides. The backend uses `sentry-sdk[fastapi]` initialized before app creation; the frontend uses `@sentry/react` with React 19's `reactErrorHandler` on `createRoot`, plus an `ErrorBoundary` wrapping `<App>`. The frontend DSN comes from `VITE_SENTRY_DSN` baked into the bundle at Docker build time, passed as a Docker build arg reading from the server's `.env`.

**Primary recommendation:** Wire both concerns in a single phase branch. They share zero code — the workflow YAML is fully independent of Sentry SDK initialization — so tasks can run in two parallel streams.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**CI/CD Pipeline Design**
- Trigger: push to `main` triggers full pipeline (test → deploy)
- PR checks: run tests + linters on pull_request events targeting main (no deploy step)
- Test step: pytest (with PostgreSQL service container), ruff check, npm run lint
- No frontend tests yet — linting only for now
- Build happens on the server, not in CI — no GHCR registry needed

**Deploy Strategy**
- SSH into VPS, `git pull origin main`, `docker compose up -d --build`
- Only rebuilds changed images, recreates affected containers (not full down/up)
- Post-deploy health check: curl `/api/health` endpoint, fail CI job if no response within 60s
- On deploy failure: pipeline fails visibly in GitHub Actions — no automatic rollback. Manual investigation via SSH
- Sentry DSN passed to frontend build via `docker compose build` args reading from `.env` on server — no extra CI secrets for DSN

**Sentry Integration**
- Single Sentry project for FlawChess (one DSN for both backend and frontend)
- Backend: sentry-sdk with FastAPI integration, captures unhandled exceptions with request context
- Backend: performance traces enabled at low sample rate (e.g., 10%) for request latency visibility
- Frontend: @sentry/react SDK with Sentry.ErrorBoundary wrapping app
- Frontend: ErrorBoundary shows "Something went wrong" fallback UI with reload button on crash
- Frontend DSN: VITE_SENTRY_DSN env var baked into JS bundle at build time (standard Vite pattern)
- Environment tagging: distinguish production vs development errors in Sentry

**Secret Management in CI**
- Dedicated SSH key pair for CI deploys (not personal key) — public key in deploy@server authorized_keys, private key as GitHub Actions secret `SSH_PRIVATE_KEY`
- Server host and SSH user stored as GitHub Secrets: `SSH_HOST`, `SSH_USER`
- Production `.env` stays on server only — CI never touches app secrets (DB password, auth secrets, etc.)
- Only CI secrets needed: `SSH_PRIVATE_KEY`, `SSH_HOST`, `SSH_USER`

### Claude's Discretion
- GitHub Actions workflow YAML structure and job naming
- Sentry SDK initialization details (traces_sample_rate value, ignored errors list)
- ErrorBoundary fallback UI design
- SSH known_hosts handling in CI (ssh-keyscan or strict host checking)
- Health check retry logic (poll interval, timeout)

### Deferred Ideas (OUT OF SCOPE)
- Sentry session replay (error-only mode) — tracked as MON-04 in v1.x requirements
- Structured JSON logging with Sentry trace ID correlation — tracked as MON-05 in v1.x requirements
- GHCR-based image builds — revisit if server build times become a bottleneck
- Automatic rollback on failed deploy — revisit if deploy failures become frequent
- Branch protection rules — can add later to enforce PR workflow
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DEPLOY-07 | GitHub Actions CI/CD pipeline: test → build → SSH deploy on push to main | GitHub Actions service container patterns for PostgreSQL + pytest; SSH deploy via appleboy/ssh-action or raw ssh |
| MON-01 | Sentry error monitoring on backend capturing unhandled exceptions with request context | sentry-sdk 2.55.0 with FastAPI/StarletteIntegration; init before FastAPI app creation |
| MON-02 | Sentry error monitoring on frontend capturing JS errors with React ErrorBoundary | @sentry/react 10.45.0; React 19 reactErrorHandler on createRoot + ErrorBoundary on App |
</phase_requirements>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| sentry-sdk[fastapi] | 2.55.0 | Backend error + performance monitoring | Official Sentry Python SDK; FastAPI extra auto-enables StarletteIntegration + FastApiIntegration |
| @sentry/react | 10.45.0 | Frontend error monitoring + ErrorBoundary | Official Sentry React SDK; provides reactErrorHandler for React 19 createRoot hooks |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| GitHub Actions (ubuntu-latest) | N/A | CI runner | Standard for open source repos, free tier sufficient |
| actions/checkout | v4 | Checkout code in CI | Required first step in all jobs |
| actions/setup-python | v5 | Install Python 3.13 in CI | Required before uv |
| actions/setup-node | v4 | Install Node in CI | Required before npm run lint |
| appleboy/ssh-action | v1 | Execute SSH commands on VPS | Purpose-built GitHub Action, widely used, avoids manual ssh config boilerplate |

**Installation (backend):**
```bash
uv add "sentry-sdk[fastapi]"
```

**Installation (frontend):**
```bash
cd frontend && npm install @sentry/react
```

**Version verification (confirmed 2026-03-21):**
- `sentry-sdk`: 2.55.0 (released 2026-03-17, verified via pypi.org)
- `@sentry/react`: 10.45.0 (verified via `npm view @sentry/react version`)

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| appleboy/ssh-action | Raw ssh in run step | ssh-action handles key setup cleanly; raw ssh requires manual `ssh-keyscan` + key file creation — either works, but ssh-action is less boilerplate |
| PostgreSQL service container in CI | Docker Compose in CI | Service container is lighter; compose would require running the full stack |

## Architecture Patterns

### Recommended Project Structure
```
.github/
└── workflows/
    └── ci.yml           # Single workflow: test job + deploy job (on main only)
app/
└── core/
    └── config.py        # Add SENTRY_DSN, ENVIRONMENT fields
app/
└── main.py              # sentry_sdk.init() before FastAPI app creation
frontend/
└── src/
    ├── instrument.ts    # Sentry.init() — imported first in main.tsx
    └── main.tsx         # Import instrument.ts first; reactErrorHandler on createRoot
    └── App.tsx          # Sentry.ErrorBoundary wrapping main content
frontend/
└── Dockerfile           # Add ARG VITE_SENTRY_DSN; ENV VITE_SENTRY_DSN
docker-compose.yml       # Add build args for caddy service to pass VITE_SENTRY_DSN
.env.example             # Document SENTRY_DSN and VITE_SENTRY_DSN
```

### Pattern 1: GitHub Actions Workflow with Two Jobs

**What:** A single `ci.yml` with a `test` job (always runs) and a `deploy` job (runs only on push to main, depends on `test`).

**When to use:** Standard for projects with a single production branch. PR events run test only; pushes to main run test then deploy.

```yaml
# Source: https://docs.github.com/en/actions/writing-workflows/workflow-syntax-for-github-actions
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:18-alpine
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: flawchess_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
      - name: Install uv
        run: pip install uv
      - name: Install dependencies
        run: uv sync --locked
      - name: Lint (ruff)
        run: uv run ruff check .
      - name: Run pytest
        env:
          TEST_DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/flawchess_test
        run: uv run pytest
      - uses: actions/setup-node@v4
        with:
          node-version: "24"
      - name: Install frontend deps
        run: npm ci
        working-directory: frontend
      - name: Lint (eslint)
        run: npm run lint
        working-directory: frontend

  deploy:
    needs: test
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    runs-on: ubuntu-latest
    steps:
      - name: Deploy via SSH
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.SSH_HOST }}
          username: ${{ secrets.SSH_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            cd /opt/flawchess
            git pull origin main
            docker compose up -d --build
      - name: Health check
        run: |
          for i in $(seq 1 12); do
            if curl -sf https://flawchess.com/api/health; then
              echo "Health check passed"
              exit 0
            fi
            echo "Attempt $i/12 failed, waiting 5s..."
            sleep 5
          done
          echo "Health check failed after 60s"
          exit 1
```

**Key notes:**
- `needs: test` ensures deploy never runs if tests fail.
- `if: github.ref == 'refs/heads/main' && github.event_name == 'push'` prevents deploy on PRs even if they somehow match the branch filter.
- Health check polls every 5s for up to 60s (12 attempts × 5s = 60s).

### Pattern 2: Backend Sentry Init (before FastAPI app)

**What:** `sentry_sdk.init()` must be called before the FastAPI `app = FastAPI(...)` line. The `[fastapi]` extra auto-registers `StarletteIntegration` and `FastApiIntegration`.

**When to use:** Always — placement before app creation ensures middleware registration works correctly.

```python
# Source: https://docs.sentry.io/platforms/python/integrations/fastapi/
# app/main.py — init BEFORE FastAPI app creation
import sentry_sdk
from app.core.config import settings

if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        traces_sample_rate=0.1,  # 10% of requests traced for performance data
        send_default_pii=False,  # Do not send user PII (emails, IPs) by default
    )

app = FastAPI(title="FlawChess", version="0.1.0", lifespan=lifespan)
```

**Key notes:**
- Guard with `if settings.SENTRY_DSN:` so dev environments without DSN don't attempt Sentry init.
- `[fastapi]` extra automatically activates `FastApiIntegration` and `StarletteIntegration` — no explicit import needed.
- `traces_sample_rate=0.1` captures 10% of transactions — sufficient for latency visibility without cost.
- `environment=settings.ENVIRONMENT` tags events as `production` vs `development` in Sentry.

### Pattern 3: Frontend Sentry Init (React 19 + Vite)

**What:** Sentry recommends a dedicated `instrument.ts` file imported first in `main.tsx`. React 19's `createRoot` error hooks replace the need for a top-level `ErrorBoundary` for uncaught errors, but `Sentry.ErrorBoundary` is still useful for rendering fallback UI on component crashes.

**When to use:** This pattern is the current Sentry recommendation as of React 19.

```typescript
// Source: https://docs.sentry.io/platforms/javascript/guides/react/
// frontend/src/instrument.ts
import * as Sentry from "@sentry/react";

Sentry.init({
  dsn: import.meta.env.VITE_SENTRY_DSN,
  environment: import.meta.env.MODE,   // "production" or "development"
  integrations: [
    Sentry.browserTracingIntegration(),
  ],
  tracesSampleRate: 0.1,
  // Only initialize in production — guard in main.tsx, not here
});
```

```typescript
// frontend/src/main.tsx
import "./instrument";  // MUST be first import
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import * as Sentry from "@sentry/react";
import "./index.css";
import App from "./App.tsx";

createRoot(document.getElementById("root")!, {
  onUncaughtError: Sentry.reactErrorHandler(),
  onCaughtError: Sentry.reactErrorHandler(),
  onRecoverableError: Sentry.reactErrorHandler(),
}).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
```

```tsx
// frontend/src/App.tsx — wrap outermost content with ErrorBoundary
import * as Sentry from "@sentry/react";

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <AuthProvider>
          <Sentry.ErrorBoundary
            fallback={
              <div className="flex flex-col items-center justify-center min-h-screen gap-4">
                <p className="text-destructive">Something went wrong.</p>
                <button onClick={() => window.location.reload()}>Reload</button>
              </div>
            }
          >
            <AppRoutes />
          </Sentry.ErrorBoundary>
          <Toaster richColors />
        </AuthProvider>
      </Router>
    </QueryClientProvider>
  );
}
```

**Key notes:**
- `import.meta.env.MODE` is set by Vite to `"production"` during `npm run build` and `"development"` during `npm run dev`. No extra configuration needed.
- Guard Sentry init: if `VITE_SENTRY_DSN` is empty string (dev without DSN set), Sentry gracefully no-ops. No conditional needed.
- `replayIntegration()` is intentionally excluded — deferred to MON-04.

### Pattern 4: Passing VITE_SENTRY_DSN Through Docker Build

**What:** Vite bakes env vars prefixed with `VITE_` into the JS bundle at build time. The value must be available during `docker compose build`, not at runtime. The server `.env` file contains `VITE_SENTRY_DSN`; `docker-compose.yml` passes it as a build arg.

```yaml
# docker-compose.yml — caddy service (which builds the frontend)
  caddy:
    build:
      context: .
      dockerfile: frontend/Dockerfile
      args:
        - VITE_SENTRY_DSN=${VITE_SENTRY_DSN}
    # ... rest unchanged
```

```dockerfile
# frontend/Dockerfile — declare ARG so it's available during npm run build
FROM node:24-alpine AS builder
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
ARG VITE_SENTRY_DSN
ENV VITE_SENTRY_DSN=$VITE_SENTRY_DSN
RUN npm run build
# ... runtime stage unchanged
```

**Key notes:**
- `ARG VITE_SENTRY_DSN` makes the build arg available in the Dockerfile layer; `ENV` then sets it as an environment variable so Vite can read it.
- If `VITE_SENTRY_DSN` is absent from `.env`, Docker passes an empty string — Sentry init silently no-ops.
- CI never receives the DSN — it only SSHes in and runs `docker compose up -d --build` on the server where `.env` already exists.

### Pattern 5: SSH known_hosts Handling in CI

**What:** `appleboy/ssh-action` handles SSH key setup internally. When using raw `ssh` in a `run` step, `ssh-keyscan` is the standard approach.

**When to use:** `appleboy/ssh-action` is preferred — it avoids manual `~/.ssh/` setup.

**If raw ssh is needed:**
```bash
mkdir -p ~/.ssh
ssh-keyscan -H ${{ secrets.SSH_HOST }} >> ~/.ssh/known_hosts
echo "${{ secrets.SSH_PRIVATE_KEY }}" > ~/.ssh/deploy_key
chmod 600 ~/.ssh/deploy_key
ssh -i ~/.ssh/deploy_key ${{ secrets.SSH_USER }}@${{ secrets.SSH_HOST }} "..."
```

### Anti-Patterns to Avoid

- **Calling `sentry_sdk.init()` after `app = FastAPI(...)`:** The SDK won't register middleware properly. Always init first.
- **Using `import.meta.env.VITE_SENTRY_DSN` without the `ARG`/`ENV` in Dockerfile:** The var is empty at build time, Sentry is never initialized in production.
- **`docker compose down && docker compose up -d --build` in deploy:** This tears down the DB container unnecessarily. Use `docker compose up -d --build` (recreates only changed services).
- **Storing `SSH_PRIVATE_KEY` with trailing newline stripped:** SSH keys must include the trailing newline. GitHub Secrets preserve it — do not strip.
- **Running health check against `http://localhost/api/health` from GitHub Actions runner:** The runner can't reach the VPS localhost. Health check must hit the public domain (`https://flawchess.com/api/health`).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SSH command execution in CI | Bash ssh + manual key file setup | appleboy/ssh-action@v1 | Handles key injection, known_hosts, connection retries |
| Error capture in FastAPI | Custom exception middleware | sentry-sdk[fastapi] | Captures request context, user info, breadcrumbs automatically |
| React error boundary + reporting | Custom ErrorBoundary class + fetch to backend | Sentry.ErrorBoundary | Integrates capture with ErrorBoundary lifecycle automatically |
| Performance tracing | Custom middleware timing | sentry-sdk traces_sample_rate | Automatic span creation for routes, DB queries |

**Key insight:** Sentry's `[fastapi]` extra registers integrations automatically — no explicit `integrations=[FastApiIntegration()]` required in basic setups, though explicit configuration is needed for `failed_request_status_codes` customization.

## Common Pitfalls

### Pitfall 1: TEST_DATABASE_URL mismatch in CI
**What goes wrong:** Tests connect to the wrong DB or fail to connect because `TEST_DATABASE_URL` in the CI environment doesn't match what the PostgreSQL service container exposes.
**Why it happens:** `conftest.py` reads `settings.TEST_DATABASE_URL` which defaults to `localhost:5432/flawchess_test`. The service container in GitHub Actions maps to `localhost:5432` with different credentials (postgres/postgres, not flawchess/flawchess).
**How to avoid:** Set the `TEST_DATABASE_URL` env var in the CI workflow step to match the service container credentials: `postgresql+asyncpg://postgres:postgres@localhost:5432/flawchess_test`.
**Warning signs:** Tests fail immediately with `asyncpg.exceptions.InvalidAuthorizationSpecificationError` or connection refused.

### Pitfall 2: Sentry DSN empty in production bundle
**What goes wrong:** Frontend Sentry never initializes — JS errors silently swallowed with no Sentry event.
**Why it happens:** `VITE_SENTRY_DSN` was not in server `.env`, or the `ARG`/`ENV` lines were not added to `frontend/Dockerfile`, or the `args:` block was not added to `docker-compose.yml`.
**How to avoid:** Verify the value is baked in by inspecting the built JS: `grep -r "sentry.io" frontend/dist/assets/` after a build.
**Warning signs:** Sentry dashboard shows zero frontend events after deploying; no errors in browser console.

### Pitfall 3: `docker compose up -d --build` times out SSH connection
**What goes wrong:** `appleboy/ssh-action` times out because `docker compose up -d --build` takes longer than the action's default connection timeout.
**Why it happens:** Building both backend (Python) and frontend (Node) Docker images can take 3-5 minutes cold; the SSH action may drop the connection.
**How to avoid:** Set `command_timeout` on `appleboy/ssh-action` to a generous value (e.g., `10m`). Alternatively, use `nohup` and poll health separately — but a generous timeout is simpler.
**Warning signs:** CI shows SSH connection closed mid-deploy; `docker compose up` was still running on server.

### Pitfall 4: `alembic upgrade head` runs during `docker compose up -d --build`
**What goes wrong:** Not a pitfall — this is by design. `deploy/entrypoint.sh` already runs `alembic upgrade head` before Uvicorn starts. Zero action needed in CI.
**Why it matters:** No separate migration step is needed in the CI workflow; `--build` triggers a new backend image which runs migrations on startup.

### Pitfall 5: Health check hitting HTTP instead of HTTPS
**What goes wrong:** `curl http://flawchess.com/api/health` returns a 301 redirect and `curl -f` treats redirects as failures (exit code 22) or follows them to HTTPS.
**How to avoid:** Use `curl -sf https://flawchess.com/api/health` or `curl -sfL http://flawchess.com/api/health` (with `-L` to follow redirects).

## Code Examples

### Backend config.py additions
```python
# Source: app/core/config.py
class Settings(BaseSettings):
    # ... existing fields ...
    SENTRY_DSN: str = ""          # Empty string = Sentry disabled
    ENVIRONMENT: str = "production"
```

### GitHub Actions workflow (skeleton — full version in Pattern 1)
```yaml
# Source: https://docs.github.com/en/actions/writing-workflows/workflow-syntax-for-github-actions
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:18-alpine
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: flawchess_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
    steps:
      - uses: actions/checkout@v4
      # ... setup-python, uv sync, ruff, pytest, setup-node, npm ci, npm lint

  deploy:
    needs: test
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    runs-on: ubuntu-latest
    steps:
      - uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.SSH_HOST }}
          username: ${{ secrets.SSH_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          command_timeout: 10m
          script: |
            cd /opt/flawchess
            git pull origin main
            docker compose up -d --build
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| React 18 `<Sentry.ErrorBoundary>` as root error capture | React 19 `reactErrorHandler` on `createRoot` hooks | React 19 / @sentry/react 8+ | ErrorBoundary still useful for fallback UI, but root capture now uses createRoot hooks |
| `sentry-sdk` without extra | `sentry-sdk[fastapi]` | sentry-sdk 1.14+ | Auto-registers FastAPI/Starlette integrations; no manual `integrations=[]` list needed |
| `POSTGRES_DB=flawchess` in CI service | Separate `flawchess_test` DB | Always best practice | Avoids accidental writes to dev DB; conftest.py already uses `TEST_DATABASE_URL` |

**Deprecated/outdated:**
- `sentry-sdk` with `integrations=[StarletteIntegration(), FastApiIntegration()]` explicit list: Still works but not required when using `[fastapi]` extra.
- `replaysIntegration()` in base setup: Deferred to MON-04; adds bundle weight for a feature not yet needed.

## Open Questions

1. **uv installation in CI**
   - What we know: `uv` is not pre-installed on `ubuntu-latest` GitHub Actions runners. The CLAUDE.md shows `uv sync` as the standard command.
   - What's unclear: Best installation method — `pip install uv`, `curl -LsSf https://astral.sh/uv/install.sh | sh`, or `astral-sh/setup-uv` action (exists as of 2025).
   - Recommendation: Use `astral-sh/setup-uv@v4` action — purpose-built, handles PATH, versions pinnable. Fallback: `pip install uv`.

2. **Deploy user git permissions on VPS**
   - What we know: The VPS deploy user is `deploy` and the app lives at `/opt/flawchess`. The deploy flow is `git pull origin main`.
   - What's unclear: Whether `deploy` user has SSH key configured for GitHub access (to `git pull` from a private repo), or if the repo is public.
   - Recommendation: If repo is public, `git pull` works without credentials. If private, a GitHub deploy key must be set on the server. Verify before implementing.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.23.x |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `uv run pytest tests/test_auth.py -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DEPLOY-07 | GitHub Actions workflow file exists and is valid YAML | smoke/manual | `python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"` | ❌ Wave 0 |
| DEPLOY-07 | `/api/health` endpoint returns `{"status": "ok"}` | unit | `uv run pytest tests/test_health.py -x` | ❌ Wave 0 |
| MON-01 | `sentry_sdk.init()` called with DSN when SENTRY_DSN is set | unit | `uv run pytest tests/test_sentry_backend.py -x` | ❌ Wave 0 |
| MON-02 | `Sentry.init()` present in instrument.ts with VITE_SENTRY_DSN | manual | inspect `frontend/src/instrument.ts` | ❌ Wave 0 |
| MON-02 | ErrorBoundary wraps AppRoutes in App.tsx | manual | inspect `frontend/src/App.tsx` | ❌ Wave 0 |

**Note:** MON-01 unit test is low value — Sentry init is a side-effect-based integration that is best verified manually in the Sentry dashboard (throw a test error, confirm it appears within 60s). A simple smoke test checking the config field is present is sufficient for automated coverage.

### Sampling Rate
- **Per task commit:** `uv run pytest -x` (full backend suite, ~10s with in-memory fixtures)
- **Per wave merge:** `uv run pytest && cd frontend && npm run lint`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `.github/workflows/ci.yml` — covers DEPLOY-07 (workflow creation is an implementation artifact, not a test file)
- [ ] `tests/test_health.py` — smoke test for `/api/health` endpoint (may already be implicitly covered; check existing test files)

**Note:** The `/api/health` endpoint already exists in `app/main.py`. No new test infrastructure is required beyond confirming an existing or new health endpoint test.

## Sources

### Primary (HIGH confidence)
- https://docs.sentry.io/platforms/python/integrations/fastapi/ — FastAPI Sentry integration, init pattern, traces_sample_rate
- https://docs.sentry.io/platforms/javascript/guides/react/ — @sentry/react setup, React 19 reactErrorHandler, ErrorBoundary
- https://pypi.org/project/sentry-sdk/ — confirmed version 2.55.0 released 2026-03-17
- npm registry `npm view @sentry/react version` — confirmed version 10.45.0

### Secondary (MEDIUM confidence)
- https://docs.github.com/en/actions/guides/creating-postgresql-service-containers — PostgreSQL service container pattern for GitHub Actions
- https://github.com/marketplace/actions/docker-compose-ssh-deployment — SSH deploy action ecosystem overview
- appleboy/ssh-action@v1 — widely used, well-maintained SSH action

### Tertiary (LOW confidence)
- WebSearch results on `astral-sh/setup-uv` action existence — mentioned in community posts, not verified against official docs

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — versions verified from registries 2026-03-21
- Architecture: HIGH — patterns verified from official Sentry docs and GitHub Actions docs
- Pitfalls: HIGH — derived from existing conftest.py analysis + official docs + direct code inspection
- Open questions: LOW — uv CI installation method and deploy user git permissions need runtime verification

**Research date:** 2026-03-21
**Valid until:** 2026-04-21 (Sentry SDK moves fast; re-verify React 19 integration pattern if > 30 days)
