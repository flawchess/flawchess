"""Unit tests for select_tagger_fixtures._stratified_sample (D-EXP-02 Option B).

Tests verify:
  (a) --oversample-motifs raises the target motif's sample count.
  (b) A control motif that does NOT co-occur on any target-motif row selects
      the SAME PuzzleIds in both the default and the oversampled call, proving
      the per-motif RNG re-seed isolation is exact for non-co-occurring motifs.

No database. No .csv.zst. Pure sampling-function tests only.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root on sys.path so 'scripts' and 'tests.scripts.tagger' are importable.
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_PROJECT_ROOT))

from scripts.select_tagger_fixtures import (  # noqa: E402
    DEFAULT_SEED,
    SAMPLES_PER_STRATUM,
    _stratified_sample,
)

# ---------------------------------------------------------------------------
# Named constants (no bare literals per CLAUDE.md)
# ---------------------------------------------------------------------------

# A large cap that guarantees the target motif is oversampled beyond SAMPLES_PER_STRATUM.
OVERSAMPLE_CAP_FOR_TEST: int = 1_000

# Rating values that land in distinct bands (lt1200 and 1200-1599).
RATING_LOW: int = 1000
RATING_MID: int = 1400

# Synthetic FEN / PV strings (not validated by chess logic in this test).
_DUMMY_FEN: str = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
_DUMMY_PV: str = "e7e5"
_DUMMY_FIRST_MOVE: str = "e2e4"


# ---------------------------------------------------------------------------
# Synthetic data builders
# ---------------------------------------------------------------------------


def _make_candidate(
    puzzle_id: str,
    rating: int,
    matched_motifs: list[str],
) -> dict[str, str]:
    """Return a minimal candidate dict matching _stratified_sample's expected schema."""
    return {
        "PuzzleId": puzzle_id,
        "FEN": _DUMMY_FEN,
        "FirstMove": _DUMMY_FIRST_MOVE,
        "PV": _DUMMY_PV,
        "Themes": " ".join(matched_motifs),  # space-separated like the real CSV
        "Rating": str(rating),
        "_rating_int": str(rating),
        "_matched_motifs": ",".join(matched_motifs),
    }


def _build_candidates(
    target_motif: str,
    control_motif: str,
    n_target: int,
    n_control: int,
    rating: int,
) -> list[dict[str, str]]:
    """Build synthetic candidates with NO co-occurrence between target and control.

    All target-motif rows carry ONLY the target motif; all control-motif rows
    carry ONLY the control motif. This guarantees the isolation property: raising
    the target cap cannot affect the control motif's draw at all.
    """
    candidates: list[dict[str, str]] = []
    for i in range(n_target):
        candidates.append(
            _make_candidate(
                puzzle_id=f"TARGET_{i:05d}",
                rating=rating,
                matched_motifs=[target_motif],
            )
        )
    for i in range(n_control):
        candidates.append(
            _make_candidate(
                puzzle_id=f"CTRL_{i:05d}",
                rating=rating,
                matched_motifs=[control_motif],
            )
        )
    return candidates


def _puzzle_ids_for_motif(rows: list[dict[str, str]], motif: str) -> set[str]:
    """Return PuzzleIds of rows that were sampled for the given motif."""
    return {r["PuzzleId"] for r in rows if motif in r["_matched_motifs"].split(",")}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_oversample_raises_target_motif_count() -> None:
    """Oversampling the target motif yields more rows for it than the default call."""
    target_motif = "trapped-piece"
    control_motif = "fork"

    # Provide more candidates than SAMPLES_PER_STRATUM so there's headroom to oversample.
    n_target = OVERSAMPLE_CAP_FOR_TEST
    n_control = SAMPLES_PER_STRATUM + 50

    candidates = _build_candidates(
        target_motif=target_motif,
        control_motif=control_motif,
        n_target=n_target,
        n_control=n_control,
        rating=RATING_LOW,
    )

    # Default call (no oversample).
    default_rows = _stratified_sample(
        candidates,
        samples_per_stratum=SAMPLES_PER_STRATUM,
        seed=DEFAULT_SEED,
    )
    default_target_ids = _puzzle_ids_for_motif(default_rows, target_motif)

    # Oversample call (raises the target motif's cap to OVERSAMPLE_CAP_FOR_TEST).
    oversample_rows = _stratified_sample(
        candidates,
        samples_per_stratum=SAMPLES_PER_STRATUM,
        oversample_map={target_motif: OVERSAMPLE_CAP_FOR_TEST},
        seed=DEFAULT_SEED,
    )
    oversample_target_ids = _puzzle_ids_for_motif(oversample_rows, target_motif)

    assert len(oversample_target_ids) > len(default_target_ids), (
        f"Expected oversample to yield more {target_motif} rows than default "
        f"({len(oversample_target_ids)} > {len(default_target_ids)} expected)"
    )


def test_control_motif_selection_unchanged_after_oversample() -> None:
    """Control motif's selected PuzzleIds are identical with and without oversample.

    This proves the per-motif RNG re-seed (Pitfall 1 mitigation): raising the cap
    for the target motif does NOT change which PuzzleIds are drawn for an unrelated
    control motif that shares no candidates with the target.
    """
    target_motif = "trapped-piece"
    control_motif = "fork"

    # Provide enough candidates to fill both motifs beyond the default cap.
    n_target = OVERSAMPLE_CAP_FOR_TEST
    n_control = SAMPLES_PER_STRATUM + 50

    candidates = _build_candidates(
        target_motif=target_motif,
        control_motif=control_motif,
        n_target=n_target,
        n_control=n_control,
        rating=RATING_LOW,
    )

    # Default call.
    default_rows = _stratified_sample(
        candidates,
        samples_per_stratum=SAMPLES_PER_STRATUM,
        seed=DEFAULT_SEED,
    )
    default_control_ids = _puzzle_ids_for_motif(default_rows, control_motif)

    # Oversample call — same seed, raises only the target motif cap.
    oversample_rows = _stratified_sample(
        candidates,
        samples_per_stratum=SAMPLES_PER_STRATUM,
        oversample_map={target_motif: OVERSAMPLE_CAP_FOR_TEST},
        seed=DEFAULT_SEED,
    )
    oversample_control_ids = _puzzle_ids_for_motif(oversample_rows, control_motif)

    assert default_control_ids == oversample_control_ids, (
        f"Control motif '{control_motif}' selection changed after oversampling '{target_motif}'. "
        f"Only in default: {default_control_ids - oversample_control_ids}. "
        f"Only in oversample: {oversample_control_ids - default_control_ids}. "
        "Per-motif re-seed isolation is broken."
    )
