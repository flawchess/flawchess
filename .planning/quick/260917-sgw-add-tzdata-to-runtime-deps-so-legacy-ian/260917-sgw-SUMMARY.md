---
phase: quick-260917-sgw
plan: 01
subsystem: infra
tags: [tzdata, zoneinfo, docker, uv, pydantic, train]

# Dependency graph
requires: []
provides:
  - "tzdata PyPI package as a [project] dependency so both Dockerfile and Dockerfile.worker install full IANA backward-compat aliases"
  - "tests/test_tzdata_dependency.py — packaging regression test with a package-only TZPATH fixture"
affects: [train-settings, train-scheduler, docker-images]

# Actuals (#2632)
actuals:
  tokens: 2060
  tasks: 2
  commits: 2
plan_head_before: c57c11d4d

# Tech tracking
tech-stack:
  added: [tzdata==2026.4]
  patterns: [package-only-TZPATH fixture for reproducing trimmed-base-image bugs on a full-tzdata dev machine]

key-files:
  created:
    - tests/test_tzdata_dependency.py
  modified:
    - pyproject.toml
    - uv.lock

key-decisions:
  - "tzdata lives in [project] dependencies (unpinned), not a dependency-group, so one edit covers both Dockerfile and Dockerfile.worker."
  - "Regression test uses zoneinfo.reset_tzpath([]) + ZoneInfo.clear_cache() to force package-only resolution — a bare alias assert would pass on this dev machine even with the bug present."
  - "Package legitimacy for tzdata (PyPI, github.com/python/tzdata, PSF-authored, zero transitive deps, Apache-2.0) verified via PyPI JSON API and approved by user 2026-09-17 (Task 1, gate=blocking-human)."

patterns-established:
  - "Package-only TZPATH fixture pattern for any future zoneinfo-adjacent regression that a full-tzdata dev machine cannot otherwise reproduce."

requirements-completed: [TZ-01, TZ-02, TZ-03]

coverage:
  - id: D1
    description: "tzdata added to [project] dependencies; uv.lock regenerated with only the tzdata entry + flawchess dependency edge"
    requirement: "TZ-01"
    verification:
      - kind: unit
        ref: "tests/test_tzdata_dependency.py::test_tzdata_distribution_is_installed"
        status: pass
    human_judgment: false
  - id: D2
    description: "Legacy IANA aliases (Europe/Kiev, Asia/Calcutta, US/Pacific, America/Buenos_Aires, Asia/Saigon) resolve under a package-only TZPATH, plus canonical controls Europe/Kyiv and UTC"
    requirement: "TZ-02"
    verification:
      - kind: unit
        ref: "tests/test_tzdata_dependency.py::test_legacy_aliases_resolve_from_package_only[*]"
        status: pass
    human_judgment: false
  - id: D3
    description: "TrainSettingsUpdate accepts timezone=\"Europe/Kiev\" (the exact Sentry FLAWCHESS-9W payload shape) instead of 422ing"
    requirement: "TZ-02"
    verification:
      - kind: unit
        ref: "tests/test_tzdata_dependency.py::test_train_settings_update_accepts_legacy_alias"
        status: pass
    human_judgment: false
  - id: D4
    description: "local_today resolves Europe/Kiev to the correct local date instead of silently falling back to UTC"
    requirement: "TZ-03"
    verification:
      - kind: unit
        ref: "tests/test_tzdata_dependency.py::test_local_today_resolves_alias_instead_of_falling_back"
        status: pass
    human_judgment: false
  - id: D5
    description: "Fix verified where the bug actually lives: pinned python:3.14-slim base image cannot resolve Europe/Kiev; Dockerfile.worker's builder stage (uv sync --locked --no-dev) resolves all 5 legacy aliases + 2 controls"
    verification:
      - kind: integration
        ref: "docker build -f Dockerfile.worker --target builder + container probe (see 'Container Proof' below)"
        status: pass
    human_judgment: false

# Metrics
duration: 20min
completed: 2026-09-17
status: complete
---

# Quick Task 260917-sgw: Add tzdata to runtime deps Summary

**Added `tzdata` to `[project] dependencies` closing Sentry FLAWCHESS-9W (legacy IANA aliases like `Europe/Kiev` 422ing on `PUT /train/settings`), proven with a package-only-TZPATH regression test and a container probe against the actual pinned prod base image.**

## Performance

- **Duration:** ~20 min
- **Tasks:** 3 (Task 1 discharged by orchestrator before spawn; Task 2 + Task 3 executed here)
- **Files modified:** 3 (`pyproject.toml`, `uv.lock`, `tests/test_tzdata_dependency.py`)

## Task 1: Package legitimacy gate — DISCHARGED (evidence recorded per orchestrator instruction)

Not run by this executor — already discharged before spawn. Evidence recorded verbatim as instructed:

> Source: https://pypi.org/pypi/tzdata/json (fetched 2026-09-17)
> - name/summary: `tzdata` — "Provider of IANA time zone data"
> - author: Python Software Foundation <datetime-sig@python.org>; maintainer: belopolsky
> - Homepage AND Source both: https://github.com/python/tzdata (matches the expected repo named in the plan)
> - Documentation: https://tzdata.python.org | Bug Reports: github.com/python/tzdata/issues
> - license: Apache-2.0
> - latest version: 2026.4, released 2026-09-12T12:56:01Z
> - requires_dist: none (zero transitive dependencies; pure-data wheel, no executable code)
> - Verdict: first-party CPython/PSF package, legitimate. User approved 2026-09-17.

## Accomplishments

- Added a regression test module (`tests/test_tzdata_dependency.py`) proven RED on the unfixed tree (all 10 parametrized cases failed) before the fix landed.
- Added `tzdata` (unpinned) to `[project] dependencies` in `pyproject.toml` with an explanatory bug-fix comment; regenerated `uv.lock` with a diff scoped to exactly the `tzdata` package entry and the `flawchess` dependency edge.
- Proved the fix in a container against the actual pinned prod base image (`python:3.14-slim@sha256:cad9a2c8...25ef6`), since this dev machine's full system tzdata cannot reproduce the bug locally.
- Ran the full backend pre-merge gate: ruff format/check, ty (`app/`, `tests/`, `scripts/`, `analysis/`), function-size/nesting-depth check, and the full pytest suite (4723 passed, 19 skipped, 0 failed).
- `git diff app/` is empty — `TrainSettingsUpdate._validate_timezone`'s D-06 reject-on-unresolvable behavior and `train_scheduler.py`'s UTC fallback are byte-identical to before.

## RED Evidence (Task 2, pre-fix tree)

Confirmed `tzdata` absent from the venv (`importlib.util.find_spec("tzdata")` → `None`) before writing the test, then ran the new module:

```
FAILED tests/test_tzdata_dependency.py::test_tzdata_distribution_is_installed
FAILED tests/test_tzdata_dependency.py::test_legacy_aliases_resolve_from_package_only[Europe/Kiev]
FAILED tests/test_tzdata_dependency.py::test_legacy_aliases_resolve_from_package_only[Asia/Calcutta]
FAILED tests/test_tzdata_dependency.py::test_legacy_aliases_resolve_from_package_only[US/Pacific]
FAILED tests/test_tzdata_dependency.py::test_legacy_aliases_resolve_from_package_only[America/Buenos_Aires]
FAILED tests/test_tzdata_dependency.py::test_legacy_aliases_resolve_from_package_only[Asia/Saigon]
FAILED tests/test_tzdata_dependency.py::test_legacy_aliases_resolve_from_package_only[Europe/Kyiv]
FAILED tests/test_tzdata_dependency.py::test_legacy_aliases_resolve_from_package_only[UTC]
FAILED tests/test_tzdata_dependency.py::test_train_settings_update_accepts_legacy_alias
FAILED tests/test_tzdata_dependency.py::test_local_today_resolves_alias_instead_of_falling_back
10 failed, 2 warnings in 4.32s
```

The `local_today` failure surfaced the harness caveat documented in the module docstring exactly as predicted: with TZPATH emptied AND `tzdata` absent, even the scheduler's `ZoneInfo(DEFAULT_TIMEZONE)` UTC-fallback line itself raised `ZoneInfoNotFoundError('No time zone found with key UTC')` — proving the fixture makes the package the only possible zone-data source, and that on this harness (unlike prod) the missing-package condition surfaces loudly rather than silently.

## Container Proof (Task 3, post-fix)

Baseline — the bare pinned base image (derived via `BASE=$(head -1 Dockerfile | awk '{print $2}')` → `python:3.14-slim@sha256:cad9a2c871761c413caa6fdd6441c783451e740a48aaeba60ae62a8b53525ef6`) cannot resolve the legacy alias:

```
$ docker run --rm "$BASE" python -c "from zoneinfo import ZoneInfo; ZoneInfo('Europe/Kiev')"
...
zoneinfo._common.ZoneInfoNotFoundError: 'No time zone found with key Europe/Kiev'
EXIT_CODE=1
```

Fix — built only the `builder` stage of `Dockerfile.worker` (`uv sync --locked --no-dev`, exactly the `[project] dependencies` set; `--locked` also verifies no lock drift). Build succeeded and installed `tzdata==2026.4`. Probe from `/app/.venv/bin/python` inside the image:

```
ALL ZONES OK IN IMAGE, tzdata 2026.4
```

Local suite after the fix: `tests/test_tzdata_dependency.py` — 10 passed. Full backend suite: `4723 passed, 19 skipped in 99.82s`.

## Task Commits

Each task was committed atomically on `main`:

1. **Task 2: Add the regression test and prove RED** — `fe408cac3` (test)
2. **Task 3: Add `tzdata` to runtime deps, relock, prove GREEN in container** — `b17fda109` (fix)

Task 1 was a checkpoint (no code change, no commit).

## Files Created/Modified

- `tests/test_tzdata_dependency.py` — packaging regression test; `package_only_tzpath` fixture forces `zoneinfo` to resolve only from the `tzdata` PyPI package.
- `pyproject.toml` — added `tzdata` (unpinned) to `[project] dependencies` with an explanatory bug-fix comment.
- `uv.lock` — regenerated via `uv lock` (not `--upgrade`); diff is scoped to the `tzdata` package entry and the `flawchess` dependency edge only.

## Decisions Made

- `tzdata` in `[project] dependencies`, not a `[dependency-groups]` entry — one edit covers both `Dockerfile` (backend) and `Dockerfile.worker` (remote worker), matching the plan's stated rationale (both `uv sync` invocations install `[project] dependencies`).
- Regression test forces a package-only TZPATH rather than asserting on a bare alias, since this dev machine's full system tzdata already resolves every legacy alias today — a naive assert would never go RED.
- Restored `--group maia-inference --group push` in the local dev venv after the plan's literal `uv sync` (no groups) step, since that step transiently uninstalled `onnxruntime`/`numpy`/`flatbuffers`/`protobuf` that were present before this task started. This was necessary to run the full pre-merge gate (many test modules import `app.main`/`app.services.maia_engine`, which import `onnxruntime` at module scope) and to leave the developer's local environment as it was found. Not a deviation from the plan's file-level intent — `pyproject.toml`/`uv.lock` are unaffected by which local groups are synced.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Restored `maia-inference`/`push` groups in local venv**
- **Found during:** Task 3, after the plan's literal `uv sync` (no groups) step
- **Issue:** Plan's `uv sync` step (matching `Dockerfile.worker`'s minimal install) uninstalled `onnxruntime`, `numpy`, `flatbuffers`, `protobuf` from the local dev venv, which had them installed beforehand. Running the full pre-merge pytest suite without them would fail broadly (many modules import `app.services.maia_engine` at collection time).
- **Fix:** Ran `uv sync --group maia-inference --group push` to restore the local dev venv to its pre-task state before running the pre-merge gate.
- **Files modified:** None (venv-only, no `pyproject.toml`/`uv.lock` change beyond the already-committed `tzdata` addition).
- **Verification:** Full pytest suite ran clean (4723 passed, 19 skipped, 0 failed).
- **Committed in:** N/A (local environment state, not a tracked file).

### Process Incident — Commit Landed on Wrong Branch, Recovered

**Not a deviation from the plan's code changes, but flagging prominently because it affected git history mechanics:**

While Task 3's long-running steps executed (relock, `uv sync`, Docker build, full pytest suite — several minutes total), a **concurrent agent** working on Phase 224 ("Guest activation") checked out a new branch `gsd/phase-224-guest-activation-welcome-removal-and-guest-train` in this **same, non-worktree working directory** (this quick task's `isolation_note` explicitly stated worktree isolation was degraded to sequential/main-checkout mode for this run). That agent made two docs commits on that branch. When I then ran `git add pyproject.toml uv.lock && git commit`, the commit landed on `gsd/phase-224-...` (HEAD had moved out from under me) instead of `main`.

**Recovery:** Verified the working tree was clean, confirmed `main` still pointed at the correct prior commit (`fe408cac3`, Task 2's commit), then `git checkout main && git cherry-pick db60dd9d2` — content-identical cherry-pick (verified via `git diff db60dd9d2 b17fda109` — empty) onto `main` as `b17fda109`. Did **not** touch the `gsd/phase-224-...` branch itself (removing the stray commit from it would be rewriting another agent's branch history while it may still be in use) — that branch still carries an extra `fix(260917-sgw): ...` commit (`db60dd9d2`) on top of its own two docs commits, which is harmless to leave (a stray commit already present on `main` too) but worth a human glance before that phase branch is squash-merged, so its merge message doesn't misattribute this fix.

- **Root cause:** Running a "sequential" (non-worktree) executor in the same checkout as a concurrently-active agent is a race on `HEAD`/working-tree state — this is a known category (see project memory `project_execute_phase_isolation_sentinel_ttl` and `project_gsd_commit_helper_recreates_phase_branch`), but this specific case (a second, unrelated agent's own checkout, not a GSD phase re-dispatch) is a new instance of it.
- **Impact:** None to the shipped fix — `main` has the correct 2 commits in the correct order, content verified byte-identical via diff. The only residue is the harmless stray commit on the `gsd/phase-224-...` branch.
- **Recommendation:** Flag to the user/orchestrator that quick-task and phase-execution agents should not run in the same non-worktree checkout at the same time.

---

**Total deviations:** 1 auto-fixed (Rule 3, local venv state) + 1 process incident (recovered, no code impact).
**Impact on plan:** None on the shipped fix's correctness or scope. The branch-recovery incident is purely a git-mechanics footnote, fully resolved on `main`.

## Issues Encountered

- See "Process Incident" above — resolved via cherry-pick, no data loss, no scope change.

## Follow-ups (not performed — out of this quick task's scope per constraints)

- **CHANGELOG.md** — a user-facing `## [Unreleased]` bullet for this fix is a merge-time item per the plan; not added here per this run's explicit constraints.
- **Stray commit on `gsd/phase-224-...` branch** — see Process Incident above; a human should confirm that branch's eventual squash-merge doesn't re-attribute `db60dd9d2`'s changes to Phase 224.

## Next Phase Readiness

- `tzdata` is now a first-class runtime dependency; no further Train-timezone follow-up is expected from this fix.
- The `package_only_tzpath` fixture pattern in `tests/test_tzdata_dependency.py` is reusable for any future `zoneinfo`-adjacent regression that a full-tzdata dev machine can't otherwise reproduce.

---
*Quick task: 260917-sgw*
*Completed: 2026-09-17*

## Self-Check: PASSED

- FOUND: `tests/test_tzdata_dependency.py`
- FOUND: `tzdata` in `pyproject.toml`
- FOUND: `tzdata` in `uv.lock`
- FOUND: commit `fe408cac3` (Task 2)
- FOUND: commit `b17fda109` (Task 3, cherry-picked recovery)
- Confirmed `git branch --show-current` → `main`
