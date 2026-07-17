---
phase: 174-backend-maia-inference-best-move-storage-spike-gated
plan: 02
subsystem: build
tags: [docker, uv, dependency-isolation, onnxruntime, numpy, maia, worker-image, gems-06]

# Dependency graph
requires:
  - phase: 174-backend-maia-inference-best-move-storage-spike-gated
    provides: The isolated `maia-inference` uv group (onnxruntime==1.20.1 + numpy), created in Plan 01 and kept out of [project.dependencies].
provides:
  - Backend Dockerfile installs the maia-inference group (--group maia-inference on the final uv sync); the worker image stays lean.
  - tests/test_dependency_isolation.py — automated GEMS-06 guard proving the worker dep-set excludes onnxruntime/numpy while the backend set includes them.
affects: [174-03, 174-04, 174-05, backend-maia-inference, remote-worker-image]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "uv opt-in dependency group as image-composition boundary: backend Dockerfile requests `--group maia-inference`, worker Dockerfile's plain `uv sync --locked --no-dev` excludes it by construction."
    - "Docker-free isolation test: `uv export --frozen --no-dev [--group X]` models each image's exact install shape and asserts on the resolved package set, no image build required."

key-files:
  created:
    - tests/test_dependency_isolation.py
  modified:
    - Dockerfile

key-decisions:
  - "Added --group maia-inference only to the backend Dockerfile's final `uv sync` (line 15), matching the objective's 'one-line change' and the grep==1 gate; the uv cache mount keeps the onnxruntime wheel cached across builds, so a separate --no-install-project group layer was unnecessary."
  - "Test drives `uv export --frozen` (not a Docker build) for a fast, deterministic dep-set assertion, backed by static pyproject/Dockerfile/worker-script guards that run even where uv is absent (export tests skip gracefully)."

requirements-completed: [GEMS-06]

coverage:
  - id: D1
    description: "Backend Docker image installs the maia-inference group (onnxruntime + numpy); the worker image does not."
    requirement: "GEMS-06"
    verification:
      - kind: other
        ref: "grep -c 'group maia-inference' Dockerfile == 1; grep -c 'maia-inference|onnxruntime' Dockerfile.worker == 0"
        status: pass
    human_judgment: false
  - id: D2
    description: "Automated proof that the worker install shape excludes onnxruntime/numpy and the backend shape includes onnxruntime==1.20.1, with neither in [project.dependencies]."
    requirement: "GEMS-06"
    verification:
      - kind: unit
        ref: "tests/test_dependency_isolation.py (7 tests: uv-export worker/backend shapes + static pyproject/Dockerfile/worker-script guards)"
        status: pass
    human_judgment: false

# Metrics
duration: 8min
completed: 2026-07-16
status: complete
---

# Phase 174 Plan 02: Maia-Inference Image Isolation Summary

**The backend Docker image now installs the isolated `maia-inference` group (onnxruntime + numpy) via a one-line `--group maia-inference` on its final `uv sync`, while `Dockerfile.worker` stays byte-unchanged and lean — proven by a 7-test Docker-free isolation guard (GEMS-06).**

## GEMS-06 Gate / Prohibition Status

**ENFORCED.** All verification gates and prohibitions hold:

- `grep -c 'group maia-inference' Dockerfile` == **1** (backend opts in).
- `grep -c 'maia-inference\|onnxruntime' Dockerfile.worker` == **0** (worker stays lean).
- `Dockerfile.worker` and `scripts/remote_eval_worker.py` are **byte-unchanged** vs the pre-plan base (no worker modification, no Maia/onnxruntime import added to the worker script — count 0).
- `onnxruntime`/`numpy` are **absent from `[project.dependencies]`** (the shared set) — they live only in the opt-in `maia-inference` group.
- `uv run pytest tests/test_dependency_isolation.py` — **7 passed**.

## Accomplishments

- Added `--group maia-inference` to the backend `Dockerfile`'s final `uv sync --locked --no-dev` (line 15) with a comment explaining the group carries the Maia inference stack and that the worker image deliberately omits it (GEMS-06). Left `Dockerfile.worker` completely untouched — its plain `uv sync` naturally excludes the opt-in group, which is the entire isolation mechanism.
- Created `tests/test_dependency_isolation.py` (7 tests) proving the invariant without a Docker build:
  - `uv export --frozen --no-dev` (worker shape) resolves a set that excludes onnxruntime AND numpy.
  - `uv export --frozen --no-dev --group maia-inference` (backend shape) includes onnxruntime==1.20.1 and numpy.
  - Static pyproject guards: onnxruntime/numpy sit ONLY under `[dependency-groups].maia-inference`, never in `[project.dependencies]` and never in any other group.
  - Static Dockerfile guards: `Dockerfile.worker`'s uv sync carries no `--group`/`--extra`; the backend `Dockerfile`'s does request `--group maia-inference`.
  - Worker-script guard: `scripts/remote_eval_worker.py` imports no Maia/onnxruntime.
  - uv-export tests skip gracefully (`shutil.which('uv')`) where uv is unavailable; static tests always run.

## Task Commits

1. **Task 1: backend Dockerfile installs the group** — `9746973f` (feat)
2. **Task 2: isolation test** — `60f6a8d9` (test)

## Files Created/Modified

- `Dockerfile` — added `--group maia-inference` to the final `uv sync` (backend-only) (modified)
- `tests/test_dependency_isolation.py` — 7-test GEMS-06 isolation guard (created)

## Decisions Made

- Single-line Dockerfile change (final `uv sync` only), matching the plan's "one-line change" objective and the `grep==1` gate. The existing `--mount=type=cache,target=/root/.cache/uv` on the final `RUN` keeps the ~110-140 MB onnxruntime wheel cached across builds, so adding the group to the earlier `--no-install-project` layer was unnecessary for build-cache correctness.
- Test asserts on `uv export` resolved dep-sets (fast, no image build) plus static pyproject/Dockerfile/worker-script guards, so isolation is enforced even in environments without uv (export tests skip, static tests still fail loud on a regression).

## Deviations from Plan

None - plan executed exactly as written. (The comment on the modified Dockerfile line was reworded so it did not repeat the literal string `group maia-inference`, keeping the `grep -c` gate at exactly 1 as the plan asserts — a trivial wording adjustment, not a behavioral deviation.)

## Ruff / ty / test status

- `uv run ruff format` + `uv run ruff check --fix` on the new test: clean (1 file reformatted, no lint issues).
- `uv run ty check tests/test_dependency_isolation.py`: All checks passed.
- `uv run pytest tests/test_dependency_isolation.py`: 7 passed.

## Issues Encountered

None. `uv export` group semantics behaved as expected in uv 0.10.9 (the plan's `pyproject.toml`-parsing fallback was not needed, though it is retained as static defense-in-depth).

## User Setup Required

None.

## Next Phase Readiness

- The backend image build now pulls the Maia inference stack; downstream plans (174-03+) that wire the Maia session lifecycle and inference code paths can assume onnxruntime/numpy are present in the backend runtime and absent from the worker.
- The isolation test is a standing regression guard: any future move of onnxruntime/numpy into `[project.dependencies]`, or any `--group`/onnxruntime leak into `Dockerfile.worker`/`remote_eval_worker.py`, fails the suite.

## Self-Check: PASSED

- `Dockerfile` and `tests/test_dependency_isolation.py` present on disk.
- Both task commits (`9746973f`, `60f6a8d9`) present in git history.
