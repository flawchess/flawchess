"""Tests for scripts/engine_throughput_226_calibration.py — Phase 226 calibration statistics.

Covers 226-03-PLAN.md's two `<behavior>` blocks: Task 1's end-to-end null check
(`load_parity_verdict`, `null_check`) and Task 2's powered verdict / refit
decision / Maia-anchor identity check.

Every ``ParityVerdictResult``-shaped fixture below is built by hand (never by
calling `calibration_parity_verdict.parity_verdict` itself) so these tests
exercise only this module's own arithmetic on numbers with a known-by-
construction answer — mirroring `test_engine_search_fixes_verdict.py`'s
`_family_result`/`_parity_verdict` helpers for its Task 2 calibration-branch
section.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Mirrors tests/scripts/test_cohort_cdf_seed_artifact.py's sys.path bootstrap
# (also used by test_engine_search_fixes_verdict.py): `scripts/` must be on
# sys.path directly so this module's own bare `from calibration_parity_verdict
# import ...` resolves, in addition to the `scripts.` package import below.
_SCRIPTS_DIR = str(Path(__file__).resolve().parent.parent.parent / "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from scripts.engine_throughput_226_calibration import (  # noqa: E402
    Item,
    PoweredVerdict,
    load_parity_verdict,
    maia_anchor_identity,
    null_check,
    powered_verdict,
    refit_decision,
)

from calibration_parity_verdict import (  # noqa: E402
    ExposedCellResult,
    Family,
    FamilyResult,
    ParityVerdictResult,
)

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_A2_VS_A0_JSON = (
    _REPO_ROOT
    / "reports"
    / "data"
    / "engine-search-fixes-225"
    / "calibration"
    / "verdict-a2-vs-a0.json"
)

_BASE_THRESHOLDS: dict[Family, float] = {"maia": 85.0, "sf": 50.0}


# ==============================================================================
# Shared fixture builders — a ParityVerdictResult with only the fields these
# functions read populated to meaningful values; everything else is a
# harmless, structurally-valid placeholder (same convention as
# test_engine_search_fixes_verdict.py's `_family_result`).
# ==============================================================================


def _exposed_cell(
    bot_elo: int, bot_blend: float, shift: float, se_shift: float
) -> ExposedCellResult:
    return {
        "bot_elo": bot_elo,
        "bot_blend": bot_blend,
        "shift": shift,
        "se_shift": se_shift,
        "outside_ci": False,
    }


def _family_result(
    pooled_shift: float,
    pooled_se: float,
    pooled_threshold: float = 999.0,
    null_shift: float = 0.0,
    null_within_threshold: bool = True,
    exposed_cells: list[ExposedCellResult] | None = None,
) -> FamilyResult:
    return {
        "null_control": {
            "shift": null_shift,
            "se_shift": 1.0,
            "threshold": 999.0,
            "within_threshold": null_within_threshold,
        },
        "pooled": {
            "shift": pooled_shift,
            "se": pooled_se,
            "threshold": pooled_threshold,
            "within_threshold": abs(pooled_shift) <= pooled_threshold,
            "n_cells": 4,
        },
        "exposed_cells": exposed_cells if exposed_cells is not None else [],
    }


def _null_parity(
    sf_shift: float, sf_se: float, maia_shift: float = 0.0, maia_se: float = 10.0
) -> ParityVerdictResult:
    """A synthetic ParityVerdictResult shaped like an A0b-vs-A0a comparison,
    used only to drive `null_check`'s pooled-shift/se arithmetic."""
    return {
        "maia": _family_result(maia_shift, maia_se),
        "sf": _family_result(sf_shift, sf_se),
        "shape_guard_triggered": [],
        "verdict": "holds",
    }


# ==============================================================================
# Task 1 behaviors — null_check, load_parity_verdict
# ==============================================================================


def test_null_check_within_threshold_se_floor_below_base() -> None:
    parity = _null_parity(sf_shift=10.0, sf_se=25.0)
    result = null_check(parity, _BASE_THRESHOLDS, se_multiplier=1.96, escalation_factor=2.0)
    sf = result["sf"]
    assert sf["threshold"] == pytest.approx(50.0)
    assert sf["se_floor"] == pytest.approx(49.0)
    assert sf["model_check_fired"] is False
    assert sf["escalate"] is False


def test_null_check_se_floor_wins_over_base_threshold() -> None:
    parity = _null_parity(sf_shift=10.0, sf_se=30.0)
    result = null_check(parity, _BASE_THRESHOLDS, se_multiplier=1.96, escalation_factor=2.0)
    assert result["sf"]["threshold"] == pytest.approx(58.8)


def test_null_check_model_check_fires_without_escalating() -> None:
    parity = _null_parity(sf_shift=-70.0, sf_se=25.0)
    result = null_check(parity, _BASE_THRESHOLDS, se_multiplier=1.96, escalation_factor=2.0)
    sf = result["sf"]
    assert sf["model_check_fired"] is True
    assert sf["threshold"] == pytest.approx(70.0)
    assert sf["escalate"] is False


def test_null_check_escalates_beyond_double_base() -> None:
    parity = _null_parity(sf_shift=120.0, sf_se=25.0)
    result = null_check(parity, _BASE_THRESHOLDS, se_multiplier=1.96, escalation_factor=2.0)
    assert result["sf"]["escalate"] is True


def test_null_check_raises_on_nan_pooled_se() -> None:
    parity = _null_parity(sf_shift=10.0, sf_se=float("nan"))
    with pytest.raises(ValueError, match="NaN"):
        null_check(parity, _BASE_THRESHOLDS, se_multiplier=1.96, escalation_factor=2.0)


def test_load_parity_verdict_reads_committed_a2_vs_a0() -> None:
    verdict = load_parity_verdict(_A2_VS_A0_JSON)
    assert verdict["sf"]["pooled"]["se"] == pytest.approx(36.3, abs=0.1)


def test_load_parity_verdict_raises_on_missing_family_key(tmp_path: Path) -> None:
    bad = tmp_path / "bad-verdict.json"
    bad.write_text(json.dumps({"maia": {}}), encoding="utf-8")
    with pytest.raises(ValueError, match="sf"):
        load_parity_verdict(bad)


# ==============================================================================
# Task 2 behaviors — powered_verdict, refit_decision, maia_anchor_identity
# ==============================================================================

_POWERED_THRESHOLDS: dict[Family, float] = {"maia": 85.0, "sf": 50.0}


def test_powered_verdict_void_when_null_control_outside_threshold() -> None:
    parity: ParityVerdictResult = {
        "maia": _family_result(pooled_shift=5.0, pooled_se=10.0, pooled_threshold=85.0),
        "sf": _family_result(
            pooled_shift=5.0,
            pooled_se=10.0,
            pooled_threshold=50.0,
            null_within_threshold=False,
        ),
        "shape_guard_triggered": [],
        "verdict": "void",
    }
    result = powered_verdict("underfill", parity, _POWERED_THRESHOLDS, z_guard=1.96)
    assert result["validity"] == "void"
    assert result["real_shift"] is None


def test_powered_verdict_beyond_threshold_gives_real_shift() -> None:
    parity: ParityVerdictResult = {
        "maia": _family_result(pooled_shift=5.0, pooled_se=10.0, pooled_threshold=85.0),
        "sf": _family_result(pooled_shift=60.0, pooled_se=10.0, pooled_threshold=50.0),
        "shape_guard_triggered": [],
        "verdict": "fails",
    }
    result = powered_verdict("underfill", parity, _POWERED_THRESHOLDS, z_guard=1.96)
    assert result["sf"]["beyond_threshold"] is True
    assert result["real_shift"] is True


def test_powered_verdict_z_guard_fires_in_both_families() -> None:
    maia_cells = [_exposed_cell(1500, 0.5, shift=25.0, se_shift=10.0)]  # z = 2.5
    sf_cells = [_exposed_cell(1500, 0.5, shift=21.0, se_shift=10.0)]  # z = 2.1
    parity: ParityVerdictResult = {
        "maia": _family_result(
            pooled_shift=5.0, pooled_se=10.0, pooled_threshold=85.0, exposed_cells=maia_cells
        ),
        "sf": _family_result(
            pooled_shift=5.0, pooled_se=10.0, pooled_threshold=50.0, exposed_cells=sf_cells
        ),
        "shape_guard_triggered": [],
        "verdict": "holds",
    }
    result = powered_verdict("root_split", parity, _POWERED_THRESHOLDS, z_guard=1.96)
    assert result["z_guard_cells"] == [(1500, 0.5)]
    assert result["real_shift"] is True


def test_powered_verdict_z_guard_does_not_fire_on_single_family() -> None:
    maia_cells = [_exposed_cell(1500, 0.5, shift=25.0, se_shift=10.0)]  # z = 2.5
    sf_cells = [_exposed_cell(1500, 0.5, shift=12.0, se_shift=10.0)]  # z = 1.2
    parity: ParityVerdictResult = {
        "maia": _family_result(
            pooled_shift=5.0, pooled_se=10.0, pooled_threshold=85.0, exposed_cells=maia_cells
        ),
        "sf": _family_result(
            pooled_shift=5.0, pooled_se=10.0, pooled_threshold=50.0, exposed_cells=sf_cells
        ),
        "shape_guard_triggered": [],
        "verdict": "holds",
    }
    result = powered_verdict("root_split", parity, _POWERED_THRESHOLDS, z_guard=1.96)
    assert result["z_guard_cells"] == []
    assert result["real_shift"] is False


def test_powered_verdict_raises_on_zero_se_shift() -> None:
    maia_cells = [_exposed_cell(1500, 0.5, shift=25.0, se_shift=0.0)]
    sf_cells = [_exposed_cell(1500, 0.5, shift=21.0, se_shift=10.0)]
    parity: ParityVerdictResult = {
        "maia": _family_result(
            pooled_shift=5.0, pooled_se=10.0, pooled_threshold=85.0, exposed_cells=maia_cells
        ),
        "sf": _family_result(
            pooled_shift=5.0, pooled_se=10.0, pooled_threshold=50.0, exposed_cells=sf_cells
        ),
        "shape_guard_triggered": [],
        "verdict": "holds",
    }
    with pytest.raises(ValueError, match="se_shift"):
        powered_verdict("root_split", parity, _POWERED_THRESHOLDS, z_guard=1.96)


def _void_verdict(label: str) -> PoweredVerdict:
    parity: ParityVerdictResult = {
        "maia": _family_result(pooled_shift=5.0, pooled_se=10.0, pooled_threshold=85.0),
        "sf": _family_result(
            pooled_shift=5.0, pooled_se=10.0, pooled_threshold=50.0, null_within_threshold=False
        ),
        "shape_guard_triggered": [],
        "verdict": "void",
    }
    return powered_verdict(label, parity, _POWERED_THRESHOLDS, z_guard=1.96)


def _real_shift_verdict(label: str) -> PoweredVerdict:
    parity: ParityVerdictResult = {
        "maia": _family_result(pooled_shift=5.0, pooled_se=10.0, pooled_threshold=85.0),
        "sf": _family_result(pooled_shift=60.0, pooled_se=10.0, pooled_threshold=50.0),
        "shape_guard_triggered": [],
        "verdict": "fails",
    }
    return powered_verdict(label, parity, _POWERED_THRESHOLDS, z_guard=1.96)


def _no_shift_verdict(label: str) -> PoweredVerdict:
    parity: ParityVerdictResult = {
        "maia": _family_result(pooled_shift=5.0, pooled_se=10.0, pooled_threshold=85.0),
        "sf": _family_result(pooled_shift=5.0, pooled_se=10.0, pooled_threshold=50.0),
        "shape_guard_triggered": [],
        "verdict": "holds",
    }
    return powered_verdict(label, parity, _POWERED_THRESHOLDS, z_guard=1.96)


def test_refit_decision_shipped_real_shift_gives_refit() -> None:
    verdicts: dict[Item, PoweredVerdict] = {"underfill": _real_shift_verdict("underfill")}
    shipped: dict[Item, bool] = {"underfill": True}
    result = refit_decision(verdicts, shipped)
    assert result["decision"] == "refit"
    assert result["reasons"]


def test_refit_decision_held_item_real_shift_alone_gives_no_refit() -> None:
    verdicts: dict[Item, PoweredVerdict] = {
        "underfill": _no_shift_verdict("underfill"),
        "candidate_cap": _real_shift_verdict("candidate_cap"),
    }
    shipped: dict[Item, bool] = {"underfill": True, "candidate_cap": False}
    result = refit_decision(verdicts, shipped)
    assert result["decision"] == "no-refit"


def test_refit_decision_void_on_shipped_item_gives_escalate() -> None:
    verdicts: dict[Item, PoweredVerdict] = {"underfill": _void_verdict("underfill")}
    shipped: dict[Item, bool] = {"underfill": True}
    result = refit_decision(verdicts, shipped)
    assert result["decision"] == "escalate"
    assert result["reasons"]


def test_refit_decision_missing_verdict_for_shipped_item_gives_escalate() -> None:
    verdicts: dict[Item, PoweredVerdict] = {}
    shipped: dict[Item, bool] = {"underfill": True}
    result = refit_decision(verdicts, shipped)
    assert result["decision"] == "escalate"


# ==============================================================================
# Task 2 behavior — maia_anchor_identity
# ==============================================================================

_LEDGER_ROW_A_MAIA_IDENTICAL = {
    "pass": "measure",
    "anchor": "maia1100",
    "game_index": "0",
    "result": "win",
    "plies": "42",
    "reason": "checkmate",
    "cp_loss_sum": "120.00",
}
_LEDGER_ROW_B_MAIA_IDENTICAL = dict(_LEDGER_ROW_A_MAIA_IDENTICAL)

_LEDGER_ROW_A_MAIA_DIFFERING = {
    "pass": "measure",
    "anchor": "maia1500",
    "game_index": "1",
    "result": "win",
    "plies": "50",
    "reason": "checkmate",
    "cp_loss_sum": "80.00",
}
_LEDGER_ROW_B_MAIA_DIFFERING = {
    **_LEDGER_ROW_A_MAIA_DIFFERING,
    "result": "loss",
    "reason": "resign",
}

_LEDGER_ROW_A_SF_ONLY = {
    "pass": "measure",
    "anchor": "sf3",
    "game_index": "2",
    "result": "win",
    "plies": "60",
    "reason": "checkmate",
    "cp_loss_sum": "300.00",
}
_LEDGER_ROW_B_SF_ONLY = {**_LEDGER_ROW_A_SF_ONLY, "result": "loss"}


def test_maia_anchor_identity_counts_matched_identical_and_differing() -> None:
    ledger_a = [
        _LEDGER_ROW_A_MAIA_IDENTICAL,
        _LEDGER_ROW_A_MAIA_DIFFERING,
        _LEDGER_ROW_A_SF_ONLY,
    ]
    ledger_b = [
        _LEDGER_ROW_B_MAIA_IDENTICAL,
        _LEDGER_ROW_B_MAIA_DIFFERING,
        _LEDGER_ROW_B_SF_ONLY,
    ]
    result = maia_anchor_identity(ledger_a, ledger_b)
    # sf3 rows are excluded entirely (anchor does not start with "maia").
    assert result["matched"] == 2
    assert result["identical"] == 1
    assert result["differing"] == [("measure", "maia1500", 1)]
