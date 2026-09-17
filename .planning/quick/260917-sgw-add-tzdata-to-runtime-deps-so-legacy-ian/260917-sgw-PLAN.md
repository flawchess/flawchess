---
phase: quick-260917-sgw
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - pyproject.toml
  - uv.lock
  - tests/test_tzdata_dependency.py
autonomous: false
requirements: [TZ-01, TZ-02, TZ-03]

estimate:
  tokens: 35000
  raw_tokens: 35000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "In the production runtime image, `ZoneInfo(\"Europe/Kiev\")` and the other legacy IANA aliases resolve instead of raising ZoneInfoNotFoundError."
    - "`PUT /train/settings` with `timezone: \"Europe/Kiev\"` no longer 422s (Sentry FLAWCHESS-9W)."
    - "`local_today` / `local_hour` / `seconds_until_end_of_local_day` compute in the user's actual zone for a legacy alias instead of silently falling back to UTC."
    - "A committed regression test fails on the pre-fix tree and passes after the fix, on the developer machine, despite the dev machine having full system tzdata."
    - "D-06 (reject an unresolvable zone with 422) and the scheduler's UTC fallback are unchanged."
  artifacts:
    - pyproject.toml
    - uv.lock
    - tests/test_tzdata_dependency.py
  key_links:
    - "`tzdata` lives in `[project] dependencies` — the one table BOTH `Dockerfile` (`uv sync --no-dev --group maia-inference --group push`) and `Dockerfile.worker` (`uv sync --no-dev`) install, so both images get the zone data from a single edit."
    - "`zoneinfo` searches system TZPATH first and only then the `tzdata` package, so the package fills the trimmed-base-image gaps without overriding system zones."
---

<objective>
Fix Sentry issue FLAWCHESS-9W: `PUT /train/settings` returns 422
(`Unrecognized IANA timezone: 'Europe/Kiev'`) for real production users, because the
prod runtime base image `python:3.14-slim` (pinned by digest in `Dockerfile` line 1)
ships a TRIMMED system tzdata with no `backward` compatibility links, and the `tzdata`
PyPI package is not a project dependency.

Two defects, one cause:

1. **Loud** — `app/schemas/train.py:360-374` `TrainSettingsUpdate._validate_timezone`
   calls `ZoneInfo(value)` and raises. Affected users cannot save Train settings at all.
2. **Silent** — `app/services/train_scheduler.py:145`, `:169`, `:216` each catch
   `ZoneInfoNotFoundError, ValueError` and fall back to `DEFAULT_TIMEZONE`, so any user
   already stored with a legacy alias gets reminders, due dates and session windows in
   the WRONG timezone with no error anywhere.

Both close by adding the `tzdata` package. Do NOT change `_validate_timezone`'s
reject-on-unresolvable behavior (D-06 is deliberate) and do NOT change the scheduler's
UTC fallback. The bare multi-except `except ZoneInfoNotFoundError, ValueError:` is valid
Python 3.14 (PEP 758) — it is not a bug, leave it alone.

Purpose: a Ukrainian user on a browser that still reports `Europe/Kiev` can save Train
settings, and every already-stored legacy alias starts computing in the right zone.
Output: one runtime dependency, a regenerated lock, and a regression test that is proven
to fail without the fix on a dev machine that cannot otherwise reproduce the bug.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@CLAUDE.md

@pyproject.toml
@app/schemas/train.py
@app/services/train_scheduler.py
</context>

<verified_facts>
Everything below was re-verified against the working tree at planning time:

- `grep -rn tzdata pyproject.toml uv.lock` → no matches. Not a direct dep, not transitive.
- `app/schemas/train.py:15` imports `ZoneInfo, ZoneInfoNotFoundError`; the validator is at
  `:360-374` inside `class TrainSettingsUpdate` (fields: `timezone`, `weekday_mask`,
  `puzzles_per_session`, `reminder_enabled`, `reminder_hour`, `reminder_intent_at` —
  all required, `reminder_intent_at` is required-but-nullable per D-02).
- `app/services/train_scheduler.py` resolves a zone at `:145` (`local_today`), `:169`
  (`local_hour`) and `:216` (`seconds_until_end_of_local_day`), each with the same
  `except ZoneInfoNotFoundError, ValueError: zone = ZoneInfo(DEFAULT_TIMEZONE)` shape.
  `DEFAULT_TIMEZONE = "UTC"` at `:75`.
- Repo-wide, `zoneinfo` appears ONLY in those two modules plus a docstring mention in
  `app/repositories/train_repository.py:379`.
- On this dev machine today: `importlib.util.find_spec("tzdata")` is `None`,
  `importlib.metadata.version("tzdata")` raises `PackageNotFoundError`, and with
  `zoneinfo.reset_tzpath([])` even `ZoneInfo.no_cache("Europe/Kyiv")` raises. With the
  normal TZPATH, `ZoneInfo("Europe/Kiev")` succeeds — which is exactly why no existing
  test catches this.
- Base image ref is derivable as `head -1 Dockerfile | awk '{print $2}'` →
  `python:3.14-slim@sha256:cad9a2c8...25ef6`, and that image is already pulled locally.
</verified_facts>

<decisions>
**Where the dependency goes — `[project] dependencies`, not a group.**
`Dockerfile` (backend) runs `uv sync --locked --no-dev --group maia-inference --group push`;
`Dockerfile.worker` runs `uv sync --locked --no-dev`. Both install `[project] dependencies`,
so one edit covers both images.

**Does the worker image need it?** Strictly, no: `scripts/remote_eval_worker.py` is a pure
HTTP + Stockfish client that uses `datetime.timezone.utc` only, and the `app.*` modules it
imports (`app.core.config`, `app.services.engine`, `app.services.eval_drain`,
`app.services.flaws_service`) reach no `zoneinfo` call site. It gets the package anyway,
deliberately: `tzdata` is a pure-data wheel of a few hundred KB (no code, no transitive
deps), it belongs in the dependency table that declares what `app.*` needs at runtime, and
carving out a separate group to keep it out of the worker would be over-engineering that
silently regresses the day a worker-reachable `app.*` path touches a zone. The existing
`maia-inference` / `push` carve-outs exist because those pull heavy native wheels
(onnxruntime, cryptography) — that reasoning does not transfer to a data-only wheel.

**Regression-test design — emptied TZPATH, not a bare alias assert.** A naive
`TrainSettingsUpdate(timezone="Europe/Kiev", ...)` assertion passes on this dev machine
WITH THE BUG PRESENT (system tzdata resolves it), so it would prove nothing. The test
instead runs with `zoneinfo.reset_tzpath([])` + `ZoneInfo.clear_cache()`, which makes the
`tzdata` package the only possible source, and additionally asserts the distribution is
installed. Verified: today, under that harness, both the validator and `local_today` fail.

**Known harness caveat, to be written into the test module docstring:** with TZPATH emptied
AND `tzdata` absent, even `ZoneInfo("UTC")` is unavailable, so the scheduler's UTC fallback
raises instead of silently returning the UTC date. In prod the same missing-package
condition surfaces as a *silent* wrong-zone fallback (system tzdata has `UTC`, just not the
`backward` aliases). The test therefore asserts the correct Kyiv-local date, never an
exception type — it passes only when the alias resolves from the package either way.
</decisions>

<tasks>

<task type="checkpoint:human-verify" gate="blocking-human">
  <name>Task 1: Package legitimacy gate for the new PyPI dependency</name>
  <what-built>
Nothing is installed yet — this gate runs BEFORE the dependency edit in Task 3.

This quick task has no RESEARCH.md and therefore no `## Package Legitimacy Audit` table,
so the fallback policy applies and the package is classified `[ASSUMED]`. Under
`gate="blocking-human"` this never auto-approves, in any mode.

About to add ONE new runtime dependency: `tzdata` (PyPI). Expected provenance:
- Homepage / source: https://github.com/python/tzdata — the `python` GitHub org.
- It is the package CPython's own `zoneinfo` documentation names as the first-party
  fallback data source; `zoneinfo` imports it under exactly that name.
- Pure data (IANA tz database files), no executable code, no transitive dependencies.
- Expect a very high download count and a long release history tracking IANA releases.
  </what-built>
  <how-to-verify>
1. Open https://pypi.org/project/tzdata/
2. Confirm the project links / homepage resolve to github.com/python/tzdata (the `python`
   org, not a lookalike account).
3. Confirm the release history is long and version numbers track IANA releases
   (`2025.x` / `2026.x` style), not a single recent upload.
4. Confirm the download count is in the many-millions-per-month range, consistent with a
   stdlib-adjacent package.
5. Confirm the page shows no maintainer-transfer or typosquat warning.
  </how-to-verify>
  <resume-signal>Reply "approved" to let Task 3 install it, or describe what looked wrong
  to halt the task.</resume-signal>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Add the regression test and prove it goes RED on the unfixed tree</name>
  <files>tests/test_tzdata_dependency.py</files>
  <behavior>
    - `test_tzdata_distribution_is_installed`: `importlib.metadata.version("tzdata")` returns
      a version string instead of raising `PackageNotFoundError`.
    - `test_legacy_aliases_resolve_from_package_only`: parametrized over the legacy aliases
      `Europe/Kiev`, `Asia/Calcutta`, `US/Pacific`, `America/Buenos_Aires`, `Asia/Saigon`
      plus the canonical controls `Europe/Kyiv` and `UTC`; under the package-only fixture,
      `ZoneInfo(alias)` constructs without raising.
    - `test_train_settings_update_accepts_legacy_alias`: under the package-only fixture,
      `TrainSettingsUpdate(timezone="Europe/Kiev", ...)` validates and round-trips
      `timezone == "Europe/Kiev"` (the exact Sentry FLAWCHESS-9W payload shape).
    - `test_local_today_resolves_alias_instead_of_falling_back`: under the package-only
      fixture, `local_today("Europe/Kiev", PROBE_UTC)` returns `date(2026, 9, 18)` while
      `PROBE_UTC.date()` is `2026-09-17`, proving the scheduler used the Kyiv zone and not
      the UTC fallback. (Verified arithmetic: 2026-09-17 22:30Z is 2026-09-18 01:30+03:00 in
      Kyiv, which is on EEST at that date.)
  </behavior>
  <action>Create `tests/test_tzdata_dependency.py` as a packaging-regression module (root of
  `tests/`, matching the existing root-level `test_*.py` convention).

  Write a module docstring that states: the prod-only cause (trimmed system tzdata in the
  pinned `python:3.14-slim` base image, no `backward` links), the Sentry issue id
  FLAWCHESS-9W, why a bare alias assert would be a no-op on a dev machine with full system
  tzdata, and the harness caveat from the plan's `<decisions>` block (with TZPATH emptied and
  the package absent, even the UTC fallback is unavailable, whereas prod degrades silently —
  so the assertions target resolved values, never exception types).

  Add a `package_only_tzpath` fixture that calls `zoneinfo.reset_tzpath([])` followed by
  `ZoneInfo.clear_cache()`, yields, and in a `finally` restores with `zoneinfo.reset_tzpath()`
  plus another `ZoneInfo.clear_cache()`. The cache clear on entry is load-bearing: `ZoneInfo`
  memoizes per key, so a zone another test already resolved from system tzdata would be
  handed back and the assertion would pass spuriously. Annotate the fixture return as
  `Iterator[None]` and give every test `-> None`, per the repo's ty rules.

  No magic literals in the bodies: hoist the alias list, the canonical controls and the probe
  instant into module-level named constants (for example `LEGACY_ALIASES`,
  `CANONICAL_ZONES`, `PROBE_UTC`, `EXPECTED_KYIV_DATE`). Build the `TrainSettingsUpdate`
  payload from a small named helper or constant dict so the one timezone under test is the
  only thing that varies.

  Tests are synchronous and touch no database.

  Then prove the module is a real discriminator: run it on the CURRENT, UNFIXED tree and
  confirm every one of the four tests FAILS. Record the observed failure output in the
  SUMMARY as the RED evidence. If any test passes before the fix, that test is a no-op —
  redesign it before moving on.</action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/flawchess &amp;&amp; uv run ruff format tests/test_tzdata_dependency.py &amp;&amp; uv run ruff check tests/test_tzdata_dependency.py &amp;&amp; uv run ty check tests/ &amp;&amp; ! uv run pytest tests/test_tzdata_dependency.py -q &amp;&amp; echo "RED CONFIRMED: the module fails on the unfixed tree"</automated>
  </verify>
  <done>`tests/test_tzdata_dependency.py` exists, is lint/format/type clean, and the whole
  module fails on the pre-fix tree. The RED output is captured for the SUMMARY.</done>
</task>

<task type="auto">
  <name>Task 3: Add `tzdata` to runtime deps, relock, and prove GREEN in a container</name>
  <files>pyproject.toml, uv.lock</files>
  <action>Add `"tzdata"` (unpinned — it is a rolling IANA data release and pinning it would
  freeze the world's timezone rules) to the `[project] dependencies` list in
  `pyproject.toml`, not to a `[dependency-groups]` entry. Place it with a short bug-fix
  comment directly above it, per the repo's comment-bug-fixes rule: the pinned
  `python:3.14-slim` runtime base image ships a trimmed system tzdata with no `backward`
  compatibility links, so legacy aliases such as `Europe/Kiev` raised
  `ZoneInfoNotFoundError` in prod only (Sentry FLAWCHESS-9W); `zoneinfo` searches system
  TZPATH first and falls back to this package, so it fills the gap without overriding system
  zones; and it sits in `[project] dependencies` on purpose so both `Dockerfile` and
  `Dockerfile.worker` pick it up.

  Regenerate the lock with `uv lock` (not `uv lock --upgrade` — do not sweep unrelated
  packages into this fix) and then `uv sync` so the local venv has the package. Confirm the
  `uv.lock` diff adds only the `tzdata` entry plus the `flawchess` dependency edge; if it
  touches anything else, stop and report rather than committing an incidental upgrade.

  Change nothing in `app/`. `_validate_timezone` keeps rejecting unresolvable zones (D-06)
  and the scheduler keeps its UTC fallback.

  Then prove the fix where the bug actually lives — a container, since this machine cannot
  reproduce the failure. Derive the base ref from the Dockerfile rather than hardcoding a
  digest (`BASE=$(head -1 Dockerfile | awk '{print $2}')`). First re-establish the baseline:
  run the probe against the bare base image and confirm `Europe/Kiev` is MISSING there.
  Then build only the `builder` stage of `Dockerfile.worker` (`docker build -f
  Dockerfile.worker --target builder`) — it is the leanest stage that runs
  `uv sync --locked --no-dev`, i.e. exactly the `[project] dependencies` set, and the backend
  image installs a strict superset of it, so a pass there covers both images — and run the
  probe from `/app/.venv/bin/python`. The `--locked` flag makes the build itself a lock-drift
  check.

  Finally run the backend pre-merge gate. The frontend is untouched by this task, so the
  frontend leg of the gate is not needed; say so in the SUMMARY.</action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/flawchess &amp;&amp; grep -v '^[[:space:]]*#' pyproject.toml | grep -c '"tzdata"' &amp;&amp; BASE=$(head -1 Dockerfile | awk '{print $2}') &amp;&amp; ! docker run --rm "$BASE" python -c "from zoneinfo import ZoneInfo; ZoneInfo('Europe/Kiev')" &amp;&amp; echo "BASELINE OK: pinned base image cannot resolve the legacy alias" &amp;&amp; docker build -f Dockerfile.worker --target builder -t flawchess-tzdata-check:local . &amp;&amp; docker run --rm flawchess-tzdata-check:local /app/.venv/bin/python -c "import importlib.metadata as md; from zoneinfo import ZoneInfo; [ZoneInfo(z) for z in ('Europe/Kiev','Asia/Calcutta','US/Pacific','America/Buenos_Aires','Asia/Saigon','Europe/Kyiv','UTC')]; print('ALL ZONES OK IN IMAGE, tzdata', md.version('tzdata'))" &amp;&amp; uv run pytest tests/test_tzdata_dependency.py -q &amp;&amp; uv run ruff format --check app/ tests/ scripts/ analysis/ &amp;&amp; uv run ruff check . &amp;&amp; uv run ty check app/ tests/ scripts/ &amp;&amp; uv run python scripts/check_function_size.py app/ --fail-over-depth 4 --fail-over-loc 200 &amp;&amp; uv run pytest -n auto -x -q</automated>
  </verify>
  <done>`tzdata` is a `[project]` dependency with an explanatory comment, `uv.lock` adds only
  that package, the container probe prints `ALL ZONES OK IN IMAGE` against a base image that
  demonstrably lacks the aliases, `tests/test_tzdata_dependency.py` is GREEN, and the backend
  pre-merge gate passes.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| PyPI → build → prod runtime image | A new third-party package enters the production image via `uv sync --locked`. |
| Browser → `PUT /train/settings` | Untrusted `timezone` string crosses into a `ZoneInfo` lookup. |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-sgw-SC | Tampering | `tzdata` PyPI install (`pyproject.toml` / `uv.lock`) | high | mitigate | No RESEARCH.md audit table exists in quick mode, so `tzdata` is `[ASSUMED]`: Task 1 is a blocking human checkpoint verifying https://pypi.org/project/tzdata/ resolves to github.com/python/tzdata before any install. `uv lock` (never `--upgrade`) plus a reviewed lock diff pins the exact artifact hashes; `uv sync --locked` in both Dockerfiles fails the build on any drift. |
| T-sgw-01 | Denial of Service | `TrainSettingsUpdate._validate_timezone` | low | accept | The validator still rejects unresolvable zones with a 422 (D-06 unchanged); `ZoneInfo` lookups are cached and bounded by the tz database's key set, so an attacker cannot force unbounded work. Widening the resolvable key set to the full IANA `backward` list is the fix's whole point, not new exposure. |
| T-sgw-02 | Information Disclosure | 422 error body echoing the submitted `timezone` | low | accept | Pre-existing, unchanged by this task: the message reflects only the caller's own input back to the caller, with no server state. |
| T-sgw-03 | Tampering | `tests/test_tzdata_dependency.py` mutating process-global `zoneinfo` TZPATH | low | mitigate | The fixture restores TZPATH and clears the `ZoneInfo` cache in a `finally`; tests within a pytest process run sequentially and `-n auto` workers are separate processes, so no cross-test leakage. |
</threat_model>

<verification>
- `uv run pytest tests/test_tzdata_dependency.py -q` — GREEN after the fix; the same command
  was proven RED in Task 2 before it.
- Container probe against the digest-pinned base image: the bare base image lacks
  `Europe/Kiev`; the `Dockerfile.worker` builder stage with the locked deps resolves all of
  `Europe/Kiev`, `Asia/Calcutta`, `US/Pacific`, `America/Buenos_Aires`, `Asia/Saigon`,
  `Europe/Kyiv`, `UTC`.
- `git diff uv.lock` shows only the `tzdata` package entry and the `flawchess` dependency edge.
- `git diff app/` is empty — D-06 and the scheduler fallback are untouched.
- Backend pre-merge gate: `ruff format --check`, `ruff check .`, `ty check app/ tests/ scripts/`,
  `pytest -n auto -x`. Frontend legs skipped (no frontend files touched).
</verification>

<success_criteria>
- A `PUT /train/settings` body with `timezone: "Europe/Kiev"` validates instead of 422ing,
  proven by a test that fails without the fix.
- `local_today` / `local_hour` / `seconds_until_end_of_local_day` compute in the aliased zone
  rather than silently falling back to UTC.
- The production runtime image and the remote-worker image both carry the full IANA zone set,
  from a single `[project] dependencies` edit.
- No behavior change in `app/`: D-06's reject-on-unresolvable and the scheduler's UTC fallback
  are byte-identical.
- CHANGELOG `## [Unreleased]` gains a user-facing bullet when this merges to `main` (a fix
  users in `Europe/Kiev`-reporting browsers can feel).
</success_criteria>

<output>
Create `.planning/quick/260917-sgw-add-tzdata-to-runtime-deps-so-legacy-ian/260917-sgw-SUMMARY.md` when done.
Include the RED output from Task 2 and the container probe output from Task 3 as evidence.
</output>
