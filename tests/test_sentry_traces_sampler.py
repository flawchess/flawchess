"""Tests for the Sentry traces sampler (app.main._sentry_traces_sampler).

The remote eval worker polls /api/eval/remote/* continuously; those transactions
must be excluded from tracing so they don't flood the span quota, while all other
routes keep the configured sample rate.
"""

import pytest

from app.core.config import settings
from app.main import _UNTRACED_PATH_PREFIX, _sentry_traces_sampler


def _ctx(path: str) -> dict[str, object]:
    return {"asgi_scope": {"type": "http", "path": path}}


@pytest.mark.parametrize(
    "path",
    [
        "/api/eval/remote/lease",
        "/api/eval/remote/submit",
        "/api/eval/remote/atomic-lease",
        "/api/eval/remote/flaw-blob-lease",
        "/api/eval/remote/entry-submit",
    ],
)
def test_remote_worker_paths_are_not_traced(path: str) -> None:
    assert _sentry_traces_sampler(_ctx(path)) == 0.0


@pytest.mark.parametrize(
    "path",
    ["/api/openings/positions", "/api/health", "/api/eval/other", "/"],
)
def test_other_paths_use_configured_rate(path: str) -> None:
    assert _sentry_traces_sampler(_ctx(path)) == settings.SENTRY_TRACES_SAMPLE_RATE


def test_prefix_matches_router_mount() -> None:
    # The router mounts under /api (main.py) with prefix /eval/remote — guard against
    # drift between the mount and the untraced prefix constant.
    assert _UNTRACED_PATH_PREFIX == "/api/eval/remote/"


def test_missing_asgi_scope_falls_back_to_configured_rate() -> None:
    # A non-ASGI transaction (e.g. a manually started span) has no asgi_scope.
    assert _sentry_traces_sampler({}) == settings.SENTRY_TRACES_SAMPLE_RATE
