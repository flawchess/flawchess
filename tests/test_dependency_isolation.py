"""Dependency-isolation guard for the Maia-3 inference stack (Phase 174, GEMS-06).

The remote-worker image (`Dockerfile.worker`) runs `scripts/remote_eval_worker.py`
(pure Stockfish, no FastAPI app, no Maia code path) and is updated manually by
operators. Bloating it with the ~110-140 MB onnxruntime/numpy inference stack it
never uses is wasteful and couples the fleet to an unused dependency.

Isolation mechanism: `onnxruntime`/`numpy` live ONLY in the opt-in
`[dependency-groups].maia-inference` group, never in the shared
`[project.dependencies]`. Both Dockerfiles historically ran the identical
`uv sync --locked --no-dev` (no `--group`), so the group is excluded from BOTH by
construction. The backend `Dockerfile` opts in with `--group maia-inference`; the
worker `Dockerfile.worker` stays untouched.

These tests prove that invariant WITHOUT building a Docker image:

* the worker's exact install shape (`uv export --no-dev`, no group) resolves a set
  that excludes onnxruntime AND numpy;
* the backend's shape (`--group maia-inference`) DOES include onnxruntime==1.20.1;
* statically, both packages sit ONLY under the maia-inference group in
  `pyproject.toml`, never under `[project.dependencies]`;
* `Dockerfile.worker`'s uv sync carries no `--group`/`--extra`, while the backend
  `Dockerfile`'s does request `--group maia-inference`.

`uv` may be unavailable in some environments (e.g. a minimal CI image); the
export-driven tests skip gracefully there. The static pyproject/Dockerfile tests
need no external tooling and always run.
"""

import re
import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = REPO_ROOT / "pyproject.toml"
BACKEND_DOCKERFILE = REPO_ROOT / "Dockerfile"
WORKER_DOCKERFILE = REPO_ROOT / "Dockerfile.worker"

INFERENCE_GROUP = "maia-inference"
# Packages that must stay isolated to the backend (never in the worker image).
ISOLATED_PACKAGES = ("onnxruntime", "numpy")
# The exact pin required by the vendored model (>=1.22 segfaults it — see Plan 01).
ONNXRUNTIME_PIN = "onnxruntime==1.20.1"

# Match a top-level requirements-txt package line like "numpy==2.5.1 \" (ignoring
# "# via onnxruntime" provenance comments and hash continuation lines).
_REQUIREMENT_LINE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)==", re.MULTILINE)


def _uv_available() -> bool:
    return shutil.which("uv") is not None


def _export_package_names(*extra_args: str) -> set[str]:
    """Return the set of normalized top-level package names uv would install.

    `--frozen` prevents any lockfile mutation during the test run. The requested
    args mirror a Dockerfile's `uv sync` install shape (minus the layer plumbing).
    """
    result = subprocess.run(
        ["uv", "export", "--frozen", "--no-dev", "--format", "requirements-txt", *extra_args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return {name.lower().replace("_", "-") for name in _REQUIREMENT_LINE.findall(result.stdout)}


@pytest.mark.skipif(
    not _uv_available(), reason="uv not installed; export-based isolation check skipped"
)
def test_worker_dep_set_excludes_inference_stack() -> None:
    """The worker's install shape (`uv sync --no-dev`, no group) omits onnxruntime + numpy."""
    worker_packages = _export_package_names()  # matches Dockerfile.worker:31
    for package in ISOLATED_PACKAGES:
        assert package not in worker_packages, (
            f"{package!r} leaked into the worker dependency set — it must stay opt-in "
            f"in the {INFERENCE_GROUP!r} group so Dockerfile.worker stays lean (GEMS-06)."
        )


@pytest.mark.skipif(
    not _uv_available(), reason="uv not installed; export-based isolation check skipped"
)
def test_backend_dep_set_includes_pinned_onnxruntime() -> None:
    """The backend's install shape (`--group maia-inference`) DOES pull the pinned stack."""
    backend_packages = _export_package_names("--group", INFERENCE_GROUP)
    for package in ISOLATED_PACKAGES:
        assert package in backend_packages, (
            f"{package!r} missing from the backend dependency set even with "
            f"--group {INFERENCE_GROUP}; the backend image needs the inference stack."
        )


def _load_pyproject() -> dict:
    with PYPROJECT.open("rb") as fh:
        return tomllib.load(fh)


def test_inference_packages_absent_from_project_dependencies() -> None:
    """onnxruntime/numpy must NOT sit in the shared [project.dependencies] set."""
    data = _load_pyproject()
    project_deps = data["project"]["dependencies"]
    joined = " ".join(project_deps).lower()
    for package in ISOLATED_PACKAGES:
        assert package not in joined, (
            f"{package!r} appears in [project.dependencies]; that set is shared with the "
            f"lean worker image. It belongs ONLY in [dependency-groups].{INFERENCE_GROUP}."
        )


def test_inference_packages_present_only_in_maia_group() -> None:
    """onnxruntime (pinned) + numpy live in the maia-inference group and nowhere else."""
    data = _load_pyproject()
    groups = data["dependency-groups"]
    assert INFERENCE_GROUP in groups, f"expected a [dependency-groups].{INFERENCE_GROUP} group"

    group_deps = groups[INFERENCE_GROUP]
    joined = " ".join(group_deps).lower()
    assert ONNXRUNTIME_PIN in joined, (
        f"expected {ONNXRUNTIME_PIN!r} pinned in the {INFERENCE_GROUP} group "
        "(>=1.22 segfaults the vendored model — see Plan 01)."
    )
    assert "numpy" in joined, f"expected numpy in the {INFERENCE_GROUP} group"

    # No OTHER group may carry the isolated packages (only maia-inference).
    for name, deps in groups.items():
        if name == INFERENCE_GROUP:
            continue
        other = " ".join(deps).lower()
        for package in ISOLATED_PACKAGES:
            assert package not in other, (
                f"{package!r} unexpectedly appears in the {name!r} group; it must be "
                f"isolated to {INFERENCE_GROUP!r} alone."
            )


def _uv_sync_lines(dockerfile: Path) -> list[str]:
    """Return the `uv sync` invocation lines from a Dockerfile (joined continuations)."""
    text = dockerfile.read_text()
    # Collapse backslash-newline line continuations so each RUN reads as one line.
    collapsed = text.replace("\\\n", " ")
    return [line.strip() for line in collapsed.splitlines() if "uv sync" in line]


def test_worker_dockerfile_uv_sync_has_no_group_or_extra() -> None:
    """Dockerfile.worker's uv sync must not opt into any group/extra (stays lean)."""
    lines = _uv_sync_lines(WORKER_DOCKERFILE)
    assert lines, "expected at least one `uv sync` line in Dockerfile.worker"
    for line in lines:
        assert "--group" not in line, (
            f"Dockerfile.worker's uv sync must not carry --group (GEMS-06): {line!r}"
        )
        assert "--extra" not in line, (
            f"Dockerfile.worker's uv sync must not carry --extra (GEMS-06): {line!r}"
        )
    # Extra belt-and-suspenders: no inference package/group named anywhere in the file.
    worker_text = WORKER_DOCKERFILE.read_text().lower()
    assert INFERENCE_GROUP not in worker_text
    assert "onnxruntime" not in worker_text


def test_backend_dockerfile_opts_into_maia_group() -> None:
    """The backend Dockerfile's final uv sync requests --group maia-inference."""
    lines = _uv_sync_lines(BACKEND_DOCKERFILE)
    assert any(f"--group {INFERENCE_GROUP}" in line for line in lines), (
        f"expected a `uv sync ... --group {INFERENCE_GROUP}` line in the backend Dockerfile"
    )


def test_remote_eval_worker_imports_no_inference_stack() -> None:
    """The worker process must never import Maia/onnxruntime (no code-path leak)."""
    worker_src = (REPO_ROOT / "scripts" / "remote_eval_worker.py").read_text().lower()
    assert "onnxruntime" not in worker_src
    assert "maia" not in worker_src
