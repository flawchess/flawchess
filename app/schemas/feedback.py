"""Pydantic v2 schemas for the feedback endpoint."""

import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# Named constants (no magic numbers per CLAUDE.md)
_MAX_FEEDBACK_LEN = 2000
_MAX_PAGE_URL_LEN = 500
_MIN_RATING = 1
_MAX_RATING = 5

# Which entry point produced a feedback row. Mirrors ck_feedback_source in the DB and the
# frontend FeedbackSource type (frontend/src/types/feedback.ts).
FeedbackSource = Literal["floating_button", "milestone_ask"]


class FeedbackCreate(BaseModel):
    """Request body for submitting user feedback."""

    # D-07: length guard at the boundary; min_length=1 ensures empty text yields 422 (D-03)
    text: str = Field(min_length=1, max_length=_MAX_FEEDBACK_LEN)
    # D-03: rating is optional (1-5 stars) — keeps submission friction low
    rating: int | None = Field(default=None, ge=_MIN_RATING, le=_MAX_RATING)
    # min_length=1 mirrors the text guard: reject empty page_url from direct API callers
    page_url: str = Field(min_length=1, max_length=_MAX_PAGE_URL_LEN)
    # The default keeps a stale SPA bundle (which never sends source) working during a deploy;
    # anything outside the Literal is rejected with 422 before any SQL runs.
    source: FeedbackSource = "floating_button"


class FeedbackResponse(BaseModel):
    """Response schema for a submitted feedback row."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime.datetime
