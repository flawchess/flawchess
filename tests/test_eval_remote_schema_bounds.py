"""Bound-validation tests for worker eval-submit schemas (code-review 2026-07-02, #11).

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

# Phase 149 WR-02 (code review 2026-07-04): test_submit_eval_accepts_valid_and_null
# and the seven test_submit_eval_rejects_* bound tests (all exercised the
# now-deleted Gen-1 SubmitEval schema in isolation) deleted along with the
# schema class itself. The same Field bounds live on AtomicSubmitEval (Phase
# 147), covered by test_atomic_submit_eval_rejects_out_of_range below.


def test_atomic_submit_eval_rejects_out_of_range() -> None:
    with pytest.raises(ValidationError):
        AtomicSubmitEval(ply=1, eval_cp=99999, eval_mate=None, best_move=None, pv=None)


def test_entry_submit_eval_rejects_out_of_range() -> None:
    with pytest.raises(ValidationError):
        EntrySubmitEval(game_id=1, ply=MAX_PLY + 1, eval_cp=None, eval_mate=None)
    # Valid payload still passes.
    EntrySubmitEval(game_id=1, ply=5, eval_cp=50, eval_mate=None)
