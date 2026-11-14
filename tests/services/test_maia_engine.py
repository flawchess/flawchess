"""Unit tests for app/services/maia_engine.py.

Covers the five lifecycle/inference behaviors:
  1. start_maia() with onnxruntime absent -> no raise, _session stays None.
  2. start_maia() twice with onnxruntime present -> idempotent, one session.
  3. stop_maia() without a prior start -> no-op, no raise.
  4. score_move() with _session None -> None.
  5. score_move() with a session -> played move's policy probability in [0, 1].

The no-op test forces the ImportError by inserting a None sentinel into
sys.modules (the documented way to make `import onnxruntime` raise ImportError
WITHOUT uninstalling the group). The real-session tests are guarded with
pytest.importorskip so the default no-group suite skips them cleanly.
"""

from __future__ import annotations

import hashlib
import json
import sys
from collections.abc import Iterator, Mapping
from pathlib import Path

import chess
import pytest

from app.services import maia_engine
from app.services.maia_encoding import POLICY_VOCAB_SIZE, elo_to_input
from app.services.maia_flaw_stats import compute_maia_flaw_stats, reply_spread

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


# ─── Lean image boots without onnxruntime ─────────────────────────────────────


async def test_noop_without_onnxruntime(monkeypatch: pytest.MonkeyPatch) -> None:
    """A backend image booted WITHOUT the maia-inference group MUST NOT crash:
    start_maia() catches ImportError, disables Maia, leaves the session None."""
    # A None sentinel in sys.modules makes `import onnxruntime` raise ImportError,
    # forcing the guard path even when the package is installed locally.
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


# ─── Model-pin integrity ───────────────────────────────────────────


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


async def test_full_policy_feeds_flaw_stats() -> None:
    """Tracer: one real Maia forward pass yields the played probability (compute_maia_flaw_stats)
    and the reply-spread input (reply_spread), and agrees with score_move."""
    pytest.importorskip("onnxruntime")
    if not _MODEL_PATH.exists():
        pytest.skip("vendored Maia model not present")
    entry = json.loads(_CORPUS_PATH.read_text())["entries"][0]
    elo = float(entry["pinned_elo"])
    maia_engine._session = None
    try:
        await maia_engine.start_maia()
        probs = maia_engine.full_policy(entry["fen"], elo)
        assert probs is not None
        stats, reasons = compute_maia_flaw_stats(probs, played_uci=entry["played_uci"])
        scored = maia_engine.score_move(entry["fen"], elo, entry["played_uci"])
    finally:
        await maia_engine.stop_maia()
    assert reasons == []
    assert stats is not None
    assert scored is not None
    played_prob = stats["maia_played_prob"]
    assert played_prob is not None
    assert abs(played_prob - scored) <= 1e-9
    assert max(probs.values()) >= played_prob
    assert 1.0 <= reply_spread(probs) <= len(probs)


# A start-like position with all four castling rights, and a position where a white
# pawn on the seventh rank can promote (including capture-promotions).
_CASTLING_FEN = "r3k2r/pppq1ppp/2n1bn2/3pp3/3PP3/2N1BN2/PPPQ1PPP/R3K2R w KQkq - 0 1"
_PROMOTION_FEN = "1n2k3/P7/8/8/8/8/8/4K3 w - - 0 1"
_SUM_TOL = 1e-6
_THREADS_ONE = 1


async def test_full_policy_matches_legal_moves_and_sums_to_one() -> None:
    """Real ORT: keys == legal UCIs, values sum to 1, score_move == full_policy[uci]
    for every legal move, and two calls return equal dicts (D-04)."""
    pytest.importorskip("onnxruntime")
    if not _MODEL_PATH.exists():
        pytest.skip("vendored Maia model not present")
    maia_engine._session = None
    try:
        await maia_engine.start_maia()
        for fen in (_CASTLING_FEN, _PROMOTION_FEN):
            elo = 1500.0
            probs = maia_engine.full_policy(fen, elo)
            assert probs is not None
            legal = {move.uci() for move in chess.Board(fen).legal_moves}
            assert set(probs) == legal
            assert abs(sum(probs.values()) - 1.0) <= _SUM_TOL
            assert maia_engine.full_policy(fen, elo) == probs
            for uci in legal:
                assert maia_engine.score_move(fen, elo, uci) == probs[uci]
    finally:
        await maia_engine.stop_maia()


def test_full_policy_none_without_session() -> None:
    """No loaded session -> full_policy and score_move both return None (D-04)."""
    maia_engine._session = None
    assert maia_engine.full_policy(_CASTLING_FEN, 1500.0) is None
    assert maia_engine.score_move(_CASTLING_FEN, 1500.0, "e1g1") is None


class _RecordingSession:
    """Fake ORT session: records feeds, returns one all-zero logits array."""

    def __init__(self) -> None:
        self.feeds: Mapping[str, object] = {}

    def run(self, names: list[str], feeds: Mapping[str, object]) -> list[object]:
        import numpy as np

        self.feeds = feeds
        return [np.zeros((1, POLICY_VOCAB_SIZE), dtype=np.float32)]


def test_full_policy_symmetric_elo_feed() -> None:
    """D-03: elo_self and elo_oppo are the same elo_to_input(elo) array."""
    np = pytest.importorskip("numpy")
    session = _RecordingSession()
    maia_engine._session = session  # ty: ignore[invalid-assignment]  # test fake for the ORT session
    elo = 1337.0
    probs = maia_engine.full_policy(_CASTLING_FEN, elo)
    assert probs is not None
    elo_self = session.feeds[maia_engine._ELO_SELF_INPUT]
    elo_oppo = session.feeds[maia_engine._ELO_OPPO_INPUT]
    assert np.array_equal(elo_self, elo_oppo)
    assert np.array_equal(elo_self, np.array([elo_to_input(elo)], dtype=np.float32))
    n_legal = len(list(chess.Board(_CASTLING_FEN).legal_moves))
    assert all(abs(p - 1.0 / n_legal) <= _SUM_TOL for p in probs.values())


async def test_start_maia_thread_option_passthrough(monkeypatch: pytest.MonkeyPatch) -> None:
    """start_maia(intra_op_num_threads=1) passes sess_options with that thread count;
    a plain start_maia() passes no sess_options (backend behavior unchanged)."""
    ort = pytest.importorskip("onnxruntime")
    calls: list[dict[str, object]] = []

    def _recorder(*args: object, **kwargs: object) -> object:
        calls.append(dict(kwargs))
        return object()

    monkeypatch.setattr(ort, "InferenceSession", _recorder)
    monkeypatch.setattr(maia_engine, "_model_bytes_ok", lambda: True)

    maia_engine._session = None
    await maia_engine.start_maia(intra_op_num_threads=_THREADS_ONE)
    assert len(calls) == 1
    opts = calls[0]["sess_options"]
    assert opts.intra_op_num_threads == _THREADS_ONE  # ty: ignore[unresolved-attribute]  # recorded SessionOptions

    maia_engine._session = None
    await maia_engine.start_maia()
    assert len(calls) == 2
    assert "sess_options" not in calls[1]


async def test_start_maia_single_thread_loads() -> None:
    """Real ORT: a single-thread session loads and Maia reports available."""
    pytest.importorskip("onnxruntime")
    if not _MODEL_PATH.exists():
        pytest.skip("vendored Maia model not present")
    maia_engine._session = None
    try:
        await maia_engine.start_maia(intra_op_num_threads=_THREADS_ONE)
        assert maia_engine.is_maia_available()
    finally:
        await maia_engine.stop_maia()
