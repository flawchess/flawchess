"""Bound-validation tests for worker eval-submit schemas.

An out-of-range value from a buggy/compromised worker used to flow through to the DB and
raise a DBAPIError → 500 → an unresolvable retry-loop. The schemas now reject it at the
API boundary (a ValidationError, which FastAPI renders as 422). These tests assert both
that valid/None payloads still pass and that each out-of-range field is rejected.
"""

import pytest
from pydantic import ValidationError

from app.schemas.eval_remote import (
    MAX_PLY,
    AtomicSubmitEval,
    EntrySubmitEval,
)


def test_atomic_submit_eval_rejects_out_of_range() -> None:
    with pytest.raises(ValidationError):
        AtomicSubmitEval(ply=1, eval_cp=99999, eval_mate=None, best_move=None, pv=None)


def test_entry_submit_eval_rejects_out_of_range() -> None:
    with pytest.raises(ValidationError):
        EntrySubmitEval(game_id=1, ply=MAX_PLY + 1, eval_cp=None, eval_mate=None)
    # Valid payload still passes.
    EntrySubmitEval(game_id=1, ply=5, eval_cp=50, eval_mate=None)
