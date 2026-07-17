"""Unit tests for app/services/maia_engine.py (Phase 174 Plan 04, GEMS-03).

Covers the five lifecycle/inference behaviors:
  1. start_maia() with onnxruntime absent -> no raise, _session stays None (D-03a).
  2. start_maia() twice with onnxruntime present -> idempotent, one session.
  3. stop_maia() without a prior start -> no-op, no raise.
  4. score_move() with _session None -> None.
  5. score_move() with a session -> played move's policy probability in [0, 1].

The D-03a no-op test forces the ImportError by inserting a None sentinel into
sys.modules (the documented way to make `import onnxruntime` raise ImportError
WITHOUT uninstalling the group). The real-session tests are guarded with
pytest.importorskip so the default no-group suite skips them cleanly.
"""

from __future__ import annotations

import hashlib
import json
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

from app.services import maia_engine

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_MODEL_PATH = _REPO_ROOT / "frontend" / "public" / "maia" / "maia3_simplified.onnx"
_CORPUS_PATH = _REPO_ROOT / "tests" / "fixtures" / "maia_parity" / "corpus.json"


@pytest.fixture(autouse=True)
def _reset_session() -> Iterator[None]:
    """Isolate the module-global session across tests: force it None before each
    test and tear any real session down afterwards."""
    maia_engine._session = None
    yield
    maia_engine._session = None


# ─── D-03a: lean image boots without onnxruntime ──────────────────────────────


async def test_noop_without_onnxruntime(monkeypatch: pytest.MonkeyPatch) -> None:
    """A backend image booted WITHOUT the maia-inference group MUST NOT crash:
    start_maia() catches ImportError, disables Maia, leaves the session None."""
    # A None sentinel in sys.modules makes `import onnxruntime` raise ImportError,
    # forcing the D-03a guard path even when the package is installed locally.
    monkeypatch.setitem(sys.modules, "onnxruntime", None)
    maia_engine._session = None

    await maia_engine.start_maia()  # must not raise

    assert maia_engine._session is None


async def test_score_move_returns_none_without_session() -> None:
    """score_move() is a no-op (returns None) when no session is loaded — the
    caller treats None as 'no Maia candidate'."""
    maia_engine._session = None
    assert (
        maia_engine.score_move(
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", 1500.0, "e2e4"
        )
        is None
    )


async def test_stop_maia_without_start_is_noop() -> None:
    """stop_maia() before any start is a safe no-op."""
    maia_engine._session = None
    await maia_engine.stop_maia()  # must not raise
    assert maia_engine._session is None


# ─── Model-pin integrity (T-174-09) ───────────────────────────────────────────


def test_model_sha256_pin_matches_vendored_file() -> None:
    """The SHA-256 the engine cross-checks against MUST equal the actual vendored
    model bytes — otherwise every real start_maia() would (correctly) refuse to
    load. Guards the pin itself against silent drift."""
    if not _MODEL_PATH.exists():
        pytest.skip("vendored Maia model not present")
    digest = hashlib.sha256(_MODEL_PATH.read_bytes()).hexdigest()
    assert digest == maia_engine._MODEL_SHA256


# ─── Real-session behavior (group-gated) ──────────────────────────────────────


async def test_start_maia_idempotent_with_session() -> None:
    """Two start_maia() calls load exactly one session (idempotent)."""
    pytest.importorskip("onnxruntime")
    if not _MODEL_PATH.exists():
        pytest.skip("vendored Maia model not present")
    maia_engine._session = None
    try:
        await maia_engine.start_maia()
        first = maia_engine._session
        assert first is not None
        await maia_engine.start_maia()
        assert maia_engine._session is first  # same object — no reload
    finally:
        await maia_engine.stop_maia()
    assert maia_engine._session is None


async def test_score_move_returns_played_move_probability() -> None:
    """With a loaded session, score_move() returns the played move's policy
    probability in [0, 1], matching the parity corpus within a loose tolerance."""
    pytest.importorskip("onnxruntime")
    if not _MODEL_PATH.exists():
        pytest.skip("vendored Maia model not present")
    entry = json.loads(_CORPUS_PATH.read_text())["entries"][0]
    maia_engine._session = None
    try:
        await maia_engine.start_maia()
        prob = maia_engine.score_move(entry["fen"], float(entry["pinned_elo"]), entry["played_uci"])
    finally:
        await maia_engine.stop_maia()
    assert prob is not None
    assert 0.0 <= prob <= 1.0
    # Sanity: matches the independently-captured client-equivalent reference.
    assert abs(prob - float(entry["expected_maia_prob"])) <= 0.02
