"""Unit tests for the in-memory Stage-B compute registry.

Quick 260529-015 Task 1 — covers mark/clear/is_computing semantics:
idempotency, harmless no-op clear, and per-uid independence.

The registry is plain module-level state (a ``set[int]``), so these tests
need no DB and no event loop. State is reset between tests by discarding the
test uids in a fixture (mirroring the ``_remove_job`` cleanup pattern in
tests/routers/test_imports_readiness.py).
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from app.services import percentile_compute_registry

# Named test user ids per CLAUDE.md no-magic-numbers rule.
_TEST_UID_A = 990150
_TEST_UID_B = 990151


@pytest.fixture(autouse=True)
def _clean_registry() -> Iterator[None]:
    """Ensure the test uids are not marked before/after each test."""
    percentile_compute_registry.clear(_TEST_UID_A)
    percentile_compute_registry.clear(_TEST_UID_B)
    yield
    percentile_compute_registry.clear(_TEST_UID_A)
    percentile_compute_registry.clear(_TEST_UID_B)


def test_unmarked_user_is_not_computing() -> None:
    assert percentile_compute_registry.is_computing(_TEST_UID_A) is False


def test_mark_then_is_computing_true() -> None:
    percentile_compute_registry.mark(_TEST_UID_A)
    assert percentile_compute_registry.is_computing(_TEST_UID_A) is True


def test_clear_then_is_computing_false() -> None:
    percentile_compute_registry.mark(_TEST_UID_A)
    percentile_compute_registry.clear(_TEST_UID_A)
    assert percentile_compute_registry.is_computing(_TEST_UID_A) is False


def test_double_mark_single_clear_is_not_computing() -> None:
    """Idempotent set add/discard — no refcount, one clear suffices."""
    percentile_compute_registry.mark(_TEST_UID_A)
    percentile_compute_registry.mark(_TEST_UID_A)
    percentile_compute_registry.clear(_TEST_UID_A)
    assert percentile_compute_registry.is_computing(_TEST_UID_A) is False


def test_clear_unmarked_user_is_noop() -> None:
    """clear on an unmarked user must not raise (set.discard)."""
    percentile_compute_registry.clear(_TEST_UID_A)
    assert percentile_compute_registry.is_computing(_TEST_UID_A) is False


def test_uids_are_independent() -> None:
    percentile_compute_registry.mark(_TEST_UID_A)
    assert percentile_compute_registry.is_computing(_TEST_UID_A) is True
    assert percentile_compute_registry.is_computing(_TEST_UID_B) is False
    percentile_compute_registry.mark(_TEST_UID_B)
    percentile_compute_registry.clear(_TEST_UID_A)
    assert percentile_compute_registry.is_computing(_TEST_UID_A) is False
    assert percentile_compute_registry.is_computing(_TEST_UID_B) is True
