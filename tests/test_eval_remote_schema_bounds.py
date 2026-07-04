"""Bound-validation tests for worker eval-submit schemas (code-review 2026-07-02, #11).

An out-of-range value from a buggy/compromised worker used to flow through to the DB and
raise a DBAPIError → 500 → an unresolvable retry-loop. The schemas now reject it at the
API boundary (a ValidationError, which FastAPI renders as 422). These tests assert both
that valid/None payloads still pass and that each out-of-range field is rejected.
"""

import pytest
from pydantic import ValidationError

from app.schemas.eval_remote import (
    EVAL_CP_MAX,
    EVAL_MATE_MIN,
    MAX_PLY,
    MAX_PV_LEN,
    AtomicSubmitEval,
    EntrySubmitEval,
    SubmitEval,
)


def test_submit_eval_accepts_valid_and_null() -> None:
    # Nulls must pass (single-legal-move / no-pv positions) despite the int bounds.
    SubmitEval(ply=1, eval_cp=None, eval_mate=None, best_move=None, pv=None)
    SubmitEval(ply=10, eval_cp=100, eval_mate=None, best_move="e7e8q", pv="e2e4 e7e5")


def test_submit_eval_rejects_eval_cp_above_max() -> None:
    with pytest.raises(ValidationError):
        SubmitEval(ply=1, eval_cp=EVAL_CP_MAX + 1, eval_mate=None, best_move=None, pv=None)


def test_submit_eval_rejects_eval_cp_below_min() -> None:
    with pytest.raises(ValidationError):
        SubmitEval(ply=1, eval_cp=-40000, eval_mate=None, best_move=None, pv=None)


def test_submit_eval_rejects_eval_mate_below_min() -> None:
    with pytest.raises(ValidationError):
        SubmitEval(ply=1, eval_cp=None, eval_mate=EVAL_MATE_MIN - 1, best_move=None, pv=None)


def test_submit_eval_rejects_ply_above_max() -> None:
    with pytest.raises(ValidationError):
        SubmitEval(ply=MAX_PLY + 1, eval_cp=None, eval_mate=None, best_move=None, pv=None)


def test_submit_eval_rejects_negative_ply() -> None:
    with pytest.raises(ValidationError):
        SubmitEval(ply=-1, eval_cp=None, eval_mate=None, best_move=None, pv=None)


def test_submit_eval_rejects_overlong_best_move() -> None:
    # 6 chars > the String(5) column would otherwise DBAPIError.
    with pytest.raises(ValidationError):
        SubmitEval(ply=1, eval_cp=None, eval_mate=None, best_move="abcdef", pv=None)


def test_submit_eval_rejects_multi_kb_pv() -> None:
    with pytest.raises(ValidationError):
        SubmitEval(ply=1, eval_cp=None, eval_mate=None, best_move=None, pv="x" * (MAX_PV_LEN + 1))


def test_atomic_submit_eval_rejects_out_of_range() -> None:
    with pytest.raises(ValidationError):
        AtomicSubmitEval(ply=1, eval_cp=99999, eval_mate=None, best_move=None, pv=None)


def test_entry_submit_eval_rejects_out_of_range() -> None:
    with pytest.raises(ValidationError):
        EntrySubmitEval(game_id=1, ply=MAX_PLY + 1, eval_cp=None, eval_mate=None)
    # Valid payload still passes.
    EntrySubmitEval(game_id=1, ply=5, eval_cp=50, eval_mate=None)
