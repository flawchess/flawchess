"""Frozen facepalm models that tests pin explicitly (Phase 254).

`FACEPALM_MODEL` is the shipped, refitted model and moves with every refit. A test written against
an earlier model (the Phase 250 reproduction, the legacy features table, the "owner fixtures
improved" check) must pin that model here instead of reading the shipped constants.
"""

from __future__ import annotations

from typing import Final

from app.services.facepalm_score import FacepalmModel

# The Phase 250 model (fitted 2026-11-13 on facepalm-features-2026-11-13.tsv), frozen: loss
# floored at 0, no missed term, the reply spread on every row, no optional inputs. The shape
# fields keep the FacepalmModel defaults, which are exactly those pre-refit values (D-12).
PHASE_250_MODEL: Final[FacepalmModel] = FacepalmModel(
    intercept=-1.4193,
    played_coef=-0.6629,
    spread_coef=-0.3304,
    loss_coef=1.1570,
    loss_floor=0,
)

# The Phase 254 model (refitted 2026-11-15 on facepalm-features-2026-11-15.tsv, report
# facepalm-fit-2026-11-15.md), frozen for the Phase 256 reproduction test: a depth-3 fit of that
# table must keep producing these constants whatever the shipped FACEPALM_MODEL becomes. The
# material input and the loss gate keep their FacepalmModel defaults (depth_3, no gate), which are
# exactly the Phase 254 behaviour.
PHASE_254_MODEL: Final[FacepalmModel] = FacepalmModel(
    intercept=-0.7583,
    played_coef=-0.4146,
    spread_coef=-0.2585,
    loss_coef=1.0129,
    loss_floor=0,
    material_form="split",
    missed_coef=0.0891,
    missed_floor=None,
    missed_cap=5,
    missed_mate=5,
    spread_form="best_prob_for_misses",
    best_prob_coef=1.0405,
    pre_spread_coef=0.0,
)
