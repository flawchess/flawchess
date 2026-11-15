"""Schemas for the feature-discovery dot route (phase 255).

The route state lives in ``users.prompt_state[FEATURE_ROUTE_KEY]``, is written only by
``feature_route_repository``'s guarded UPDATEs, and is validated by ``FeatureRouteState``
on every read and on every value an UPDATE returns (Pydantic validation instead of a DB
CHECK, the documented prompt_state exception from migration f4b9d2c7e815).
"""

import datetime
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field

# Key of the route inside users.prompt_state. Never versioned or renamed: a new feature
# is a new step ID inside it, not a new key.
FEATURE_ROUTE_KEY: Final = "feature_route"

# Append-only, in D-06 route order. Step IDs are stored per user and never renamed or
# removed (a new feature is a new ID). Mirrored by FeatureRouteStepId in
# frontend/src/types/users.ts and the order of FEATURE_ROUTE in
# frontend/src/lib/featureRoute.ts, pinned by a list test on both sides (D-09).
FeatureRouteStepId = Literal[
    "import",
    "train",
    "bots",
    "openings",
    "openings-played-as",
    "openings-filters",
    "openings-stats",
    "endgames",
    "library-stats",
]

FeatureRouteAction = Literal["current", "done", "skip"]

# D-10: a step with the dot on it is shown on its first three active days and skipped on
# the first profile load of the fourth. The client twin lives in
# frontend/src/lib/featureRoute.ts; the server re-checks it in SQL (_SKIP_SQL), so a
# client cannot skip early.
FEATURE_ROUTE_SKIP_ACTIVE_DAYS: Final = 3


class FeatureRouteStepRecord(BaseModel):
    """One resolved step in ``steps``."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["done", "skipped"]
    date: datetime.date  # UTC day (from dev_now_utc) the step was resolved
    # Whether the step was the current (dotted) step when it was resolved; kept so the
    # route can be measured in Postgres.
    with_dot: bool


class FeatureRouteCurrent(BaseModel):
    """The step the dot currently sits on, with the active-day count when it got there."""

    model_config = ConfigDict(extra="forbid")

    step: str
    since_days: int = Field(ge=1)


class FeatureRouteState(BaseModel):
    """Stored shape of ``users.prompt_state[FEATURE_ROUTE_KEY]``."""

    model_config = ConfigDict(extra="forbid")

    # Keyed by plain str on purpose: a stored ID must always validate, even one a later
    # release removed from the Literal.
    steps: dict[str, FeatureRouteStepRecord] = Field(default_factory=dict)
    current: FeatureRouteCurrent | None = None


class FeatureRouteActionRequest(BaseModel):
    """Request body for POST /users/me/feature-route."""

    model_config = ConfigDict(extra="forbid")

    action: FeatureRouteAction
    step: FeatureRouteStepId
