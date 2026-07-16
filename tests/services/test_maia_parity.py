"""Pytest wrapper for the Phase 174 D-02 Maia parity gate (GEMS-04).

Runs the SAME tier-stability + epsilon assertions as scripts/maia_parity_spike.py,
but uses pytest.importorskip("onnxruntime") so the default (no-group) suite skips
cleanly while a group-synced run (`uv sync --group maia-inference`) exercises the
gate. The standalone script remains the canonical D-02 runner; this wrapper wires
the gate into CI/the normal pytest flow so a future onnxruntime/model bump that
breaks parity is caught by the suite, not only by a manual script run (Pitfall 2).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

# Both live only in the isolated maia-inference group — skip the whole module (not
# error at collection) when the default no-group suite runs without them.
np = pytest.importorskip("numpy")
onnxruntime = pytest.importorskip("onnxruntime")

from app.services.maia_encoding import (  # noqa: E402
    NUM_SQUARES,
    PLANES_PER_SQUARE,
    encode_board,
    elo_to_input,
    mask_and_softmax,
)
from scripts.maia_parity_spike import (  # noqa: E402
    PARITY_EPSILON,
    classify_tier,
)

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_MODEL_PATH = _REPO_ROOT / "frontend" / "public" / "maia" / "maia3_simplified.onnx"
_CORPUS_PATH = _REPO_ROOT / "tests" / "fixtures" / "maia_parity" / "corpus.json"


@pytest.fixture(scope="module")
def maia_session():
    if not _MODEL_PATH.exists():
        pytest.skip(f"vendored Maia model missing at {_MODEL_PATH}")
    return onnxruntime.InferenceSession(str(_MODEL_PATH), providers=["CPUExecutionProvider"])


def _corpus_entries() -> list[dict]:
    return json.loads(_CORPUS_PATH.read_text())["entries"]


def _python_maia_prob(session, entry: dict) -> float:
    tokens = np.array(encode_board(entry["fen"]), dtype=np.float32).reshape(
        1, NUM_SQUARES, PLANES_PER_SQUARE
    )
    elo_in = np.array([elo_to_input(float(entry["pinned_elo"]))], dtype=np.float32)
    outputs = session.run(
        ["logits_move"], {"tokens": tokens, "elo_self": elo_in, "elo_oppo": elo_in}
    )
    policy = np.asarray(outputs[0]).reshape(-1).astype(np.float32)
    return mask_and_softmax(policy.tolist(), entry["fen"])[entry["played_uci"]]


@pytest.mark.parametrize(
    "entry", _corpus_entries(), ids=lambda e: f"{e['played_san']}@{e['pinned_elo']}"
)
def test_parity_tier_and_epsilon(maia_session, entry: dict) -> None:
    """Each fixture ply tier-matches the client reference AND is within PARITY_EPSILON."""
    py_prob = _python_maia_prob(maia_session, entry)
    exp_prob = float(entry["expected_maia_prob"])

    # (1) Tier-stability — the load-bearing D-01 check.
    assert classify_tier(py_prob) == entry["expected_tier"], (
        f"{entry['played_san']}@{entry['pinned_elo']}: python prob {py_prob:.6f} -> "
        f"{classify_tier(py_prob)}, expected tier {entry['expected_tier']}"
    )
    # (2) Loose epsilon on the raw probability.
    assert abs(py_prob - exp_prob) <= PARITY_EPSILON, (
        f"{entry['played_san']}@{entry['pinned_elo']}: drift "
        f"{abs(py_prob - exp_prob):.6f} > PARITY_EPSILON {PARITY_EPSILON}"
    )
