"""Schemas for the milestone feedback ask (SEED-191, Phase 234).

The ask state lives in ``users.prompt_state`` under ``FEEDBACK_ASK_ID`` and is
validated by ``FeedbackAskState`` on every read and on every value a guarded
UPDATE returns (SEED-191 #8: Pydantic instead of a DB CHECK). Eligibility and
the view/snooze/done lifecycle are SEED-191 #6 and #7.

``FeedbackAskView`` deliberately carries no round field: both rounds render the
same copy (D-02), so the client only needs to know whether the ask is active.
"""

import datetime
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field

# Key of this ask inside users.prompt_state (a future ask adds another key).
FEEDBACK_ASK_ID: Final = "feedback_v1"
# Distinct UTC activity days (today included) before a user is asked.
FEEDBACK_ASK_MIN_ACTIVE_DAYS: Final = 5
# Further active days that must pass after a snooze before the single re-ask.
FEEDBACK_ASK_REASK_GAP_DAYS: Final = 10
# Counted views (at most one per UTC day) that auto-snooze an ignored ask.
FEEDBACK_ASK_MAX_VIEWS: Final = 3
# Rounds of asking: the first ask plus one re-ask, then never again.
FEEDBACK_ASK_MAX_ROUNDS: Final = 2

FeedbackAskAction = Literal["view", "snooze", "done"]


class FeedbackAskState(BaseModel):
    """Stored shape of ``users.prompt_state[FEEDBACK_ASK_ID]``."""

    # Catches a typo'd key written by the transition SQL.
    model_config = ConfigDict(extra="forbid")

    status: Literal["snoozed", "done"] | None = None  # None = currently asking
    # A Literal cannot reference FEEDBACK_ASK_MAX_ROUNDS; keep them in step.
    round: Literal[1, 2] = 1
    views: int = Field(default=0, ge=0)  # counted views in the current round
    last_view_date: datetime.date | None = None  # UTC day of the last counted view
    snoozed_at_days: int | None = None  # active_days when the ask was snoozed
    snoozed_by: Literal["click", "views"] | None = None


class FeedbackAskView(BaseModel):
    """What the client sees: only whether the ask is active (no round field, D-02)."""

    active: bool


class FeedbackAskActionRequest(BaseModel):
    """Request body for POST /users/me/feedback-ask."""

    model_config = ConfigDict(extra="forbid")

    action: FeedbackAskAction
