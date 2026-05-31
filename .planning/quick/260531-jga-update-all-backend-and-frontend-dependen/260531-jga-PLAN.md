---
phase: quick-260531-jga
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - uv.lock
  - pyproject.toml
  - frontend/package.json
  - frontend/package-lock.json
  - CLAUDE.md
autonomous: true
requirements: []
must_haves:
  truths:
    - "uv.lock holds the newest versions satisfying existing pyproject.toml constraints (caps preserved)"
    - "frontend/package.json caret ranges point at latest in-major versions; package-lock.json refreshed"
    - "The full local gate passes: ruff format/check, ty, pytest, frontend lint/test/build, knip"
    - "overrides block and Dependabot transitive pins are intact"
  artifacts:
    - path: "uv.lock"
      provides: "Upgraded backend lockfile"
    - path: "frontend/package-lock.json"
      provides: "Upgraded frontend lockfile"
  key_links: []
---

<objective>
Refresh all backend and frontend dependencies (including dev deps) to the latest versions WITHIN the currently declared majors/constraints, then prove the refresh is safe by running the full local gate and fixing any breakage in place.

Purpose: Routine low-risk dependency hygiene. NOT an aggressive major-version migration.
Output: Upgraded `uv.lock`, upgraded `frontend/package-lock.json` + bumped caret ranges in `frontend/package.json`, optionally refreshed `>=` floors in `pyproject.toml`, optionally a corrected CLAUDE.md "Tech Stack" section.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
@pyproject.toml
@frontend/package.json
</context>

<scope_guardrails>
LOCKED scope — "latest within current majors". Do NOT deviate:

Backend:
- Run `uv lock --upgrade` to pull the newest versions satisfying the EXISTING constraints in `pyproject.toml`.
- Do NOT lift the deliberate caps: `pydantic-ai-slim[anthropic,google]>=1.85,<2.0` and `genai-prices>=0.0.56,<0.1.0`. These stay exactly as written.
- Dev deps (pytest, pytest-asyncio, pytest-cov, ruff, ty, zstandard) ARE in scope — they upgrade via the same `uv lock --upgrade`.
- OPTIONAL: raise `>=` lower-bound floors in `pyproject.toml` to the newly-locked versions only if it adds clarity/value. The primary deliverable is the upgraded `uv.lock`. Do not change any `<` upper caps.

Frontend:
- Bump every caret (`^`) range in `frontend/package.json` (dependencies AND devDependencies) to the latest version WITHIN THE CURRENT MAJOR, then run `npm install` to refresh `package-lock.json`.
- Do NOT bump any package to a NEW major. The `~5.9.3` typescript pin keeps its tilde semantics (latest 5.9.x).
- PRESERVE the `overrides` block (`fast-uri`, `@babel/plugin-transform-modules-systemjs`, `hono`, `qs`) and any Dependabot transitive-dep pins exactly — these are intentional security pins. Do not remove or weaken them. If `npm install` rewrites pinned transitive versions, restore the intended pins.

Do NOT update ROADMAP.md (this is a quick task).
</scope_guardrails>

<tasks>

<task type="auto">
  <name>Task 1: Upgrade backend deps and verify the backend gate</name>
  <files>uv.lock, pyproject.toml</files>
  <action>
Ensure the dev DB is up (CLAUDE.md): `docker compose -f docker-compose.dev.yml -p flawchess-dev up -d`.

Run `uv lock --upgrade` to refresh `uv.lock` to the newest versions satisfying the existing `pyproject.toml` constraints. Keep the `<2.0` / `<0.1.0` caps on `pydantic-ai-slim` and `genai-prices` untouched. Then `uv sync` to install the upgraded set.

Capture the before/after version deltas (diff the lock or note key bumps: fastapi, uvicorn, sqlalchemy, pydantic, pydantic-ai-slim, sentry-sdk, fastapi-users, httpx, ruff, ty, pytest*) for the SUMMARY.

OPTIONAL: bump `>=` lower-bound floors in `pyproject.toml` to the newly-locked versions where it clarifies the real minimum. Do not touch any `<` upper cap.

Run the backend gate and FIX any breakage introduced by the upgrades rather than reverting:
- `uv run ruff format app/ tests/`
- `uv run ruff check app/ tests/ --fix`
- `uv run ty check app/ tests/` (zero errors required)
- `uv run pytest -x`

Common upgrade fallout to fix in place: a new ruff release flagging new lint rules (apply autofix, or adjust code minimally), a `ty` release surfacing new type errors (annotate / narrow / add a scoped `# ty: ignore[rule]` with reason), a pydantic/pydantic-ai minor changing a deprecated API. Fix the code, do not pin away the upgrade.

ESCAPE HATCH: if one specific package's in-major bump causes breakage you cannot reasonably fix within this task's scope, pin THAT ONE package back to its previous working version (add an explicit `==<old>` or `<=<bound>` constraint in pyproject.toml, re-lock) and record the package + reason in the SUMMARY. Do not abandon the whole upgrade for one bad package.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/flawchess && uv run ruff format --check app/ tests/ && uv run ruff check app/ tests/ && uv run ty check app/ tests/ && uv run pytest -x</automated>
  </verify>
  <done>uv.lock holds upgraded versions (caps preserved); ruff format/check clean, ty zero errors, pytest passes. Any escape-hatch pin is noted for the SUMMARY.</done>
</task>

<task type="auto">
  <name>Task 2: Upgrade frontend deps and verify the frontend gate</name>
  <files>frontend/package.json, frontend/package-lock.json</files>
  <action>
For each dependency and devDependency in `frontend/package.json` with a caret (`^`) range, bump the range to the latest version WITHIN THE CURRENT MAJOR. Determine latest in-major versions via `npm view <pkg> versions --json` (or `npm outdated` in the frontend dir, reading the "Wanted"/in-major column — but Wanted respects the existing caret so prefer `npm view` to find the true latest in-major). Keep `typescript` on `~5.9.x` (tilde). Do NOT cross any major boundary (e.g. react stays 19.x, vite stays 7.x, vitest stays 4.x, tailwindcss stays 4.x, react-router-dom stays 7.x, etc.).

PRESERVE the `overrides` block and any Dependabot transitive pins verbatim. After editing `package.json`, run `npm install` (in `frontend/`) to refresh `package-lock.json`. If `npm install` weakens a pinned override/transitive version, restore the intended pin.

Capture before/after deltas of the notable frontend bumps for the SUMMARY.

Run the full frontend gate and FIX any breakage in place (not by reverting):
- `npm run lint`
- `npm test -- --run`
- `npm run build` (tsc -b + vite build — a dep refresh can break the TS/Vite build)
- `npm run knip` (CI dead-export/unused-dep gate)

Common fallout to fix: a new eslint/typescript-eslint release flagging new rules (autofix or minimal code adjustment), a `@types/*` bump tightening types (narrow / adjust), a Vite/plugin minor changing config expectations, knip flagging a now-unused transitive. Fix the code.

ESCAPE HATCH: same as Task 1 — if one specific in-major frontend bump causes unfixable breakage, pin that single package back to its previous working version in `package.json`, re-run `npm install`, and note the package + reason in the SUMMARY.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/flawchess/frontend && npm run lint && npm test -- --run && npm run build && npm run knip</automated>
  </verify>
  <done>package.json caret ranges are at latest in-major; package-lock.json refreshed; overrides + Dependabot pins intact; lint, test, build, and knip all pass. Any escape-hatch pin noted for the SUMMARY.</done>
</task>

<task type="auto">
  <name>Task 3: Refresh stale CLAUDE.md Tech Stack section (secondary)</name>
  <files>CLAUDE.md</files>
  <action>
Secondary, do-if-cheap. Update the "## Tech Stack" section of CLAUDE.md so the version callouts reflect the actual post-upgrade manifests, not stale values. The section currently claims "FastAPI 0.115.x" and "Vite 5" while the repo is already on newer versions (Vite 7, etc.).

Read the freshly-upgraded `pyproject.toml` / `uv.lock` and `frontend/package.json` and correct any version numbers in the Tech Stack bullets (FastAPI, Vite, React, SQLAlchemy, python-chess, etc.) to match reality. Prefer major-version or `.x` granularity (e.g. "Vite 7", "FastAPI 0.11x") so the section does not need editing on every minor bump. Do not rewrite the section's structure — just correct the numbers. Touch nothing else in CLAUDE.md.

If the version drift is trivial or already accurate after the upgrades, a no-op is acceptable — note it in the SUMMARY.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/flawchess && grep -n -i "Vite 5\|FastAPI 0.115" CLAUDE.md; test $(grep -c -i "Vite 5\|FastAPI 0.115" CLAUDE.md) -eq 0</automated>
  </verify>
  <done>CLAUDE.md Tech Stack version callouts match the actual upgraded manifests; no stale "Vite 5" / "FastAPI 0.115.x" strings remain (or the section was already accurate).</done>
</task>

</tasks>

<verification>
After all tasks, run the COMPLETE local gate from CLAUDE.md as the single source of truth (dev DB must be up on localhost:5432):

Backend:
- `uv run ruff format --check app/ tests/`
- `uv run ruff check app/ tests/`
- `uv run ty check app/ tests/`
- `uv run pytest -x`

Frontend (in `frontend/`):
- `npm run lint`
- `npm test -- --run`
- `npm run build`
- `npm run knip`

Confirm the `overrides` block in `frontend/package.json` and any Dependabot transitive pins are byte-for-byte preserved, and the `<2.0` / `<0.1.0` backend caps are untouched.
</verification>

<success_criteria>
- `uv lock --upgrade` applied; `uv.lock` upgraded with the two backend caps preserved.
- All frontend caret ranges at latest in-major; `package-lock.json` refreshed; no new majors; overrides + security pins intact.
- Full local gate green (backend ruff/ty/pytest + frontend lint/test/build/knip).
- Any breakage was fixed in place; any unavoidable single-package pin-back is documented in the SUMMARY with the package name and reason.
- CLAUDE.md Tech Stack version callouts corrected (or confirmed accurate).
- ROADMAP.md NOT modified.
</success_criteria>

<output>
Create `.planning/quick/260531-jga-update-all-backend-and-frontend-dependen/260531-jga-SUMMARY.md` when done. Include: notable backend version deltas, notable frontend version deltas, any code fixes required by the upgrades, and any escape-hatch pin-backs (package + reason).
</output>
