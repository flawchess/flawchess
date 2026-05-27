# Quick Task 260527-q0b: PercentileChip Tooltip Per-TC Breakdown — Context

**Gathered:** 2026-05-27
**Status:** Locked from /gsd-explore session

<domain>
## Task Boundary

Rewrite the `PercentileChipPopoverBody` bullet 2 so it surfaces a per-TC
breakdown (concrete game counts + per-TC value + per-TC percentile) for
aggregated chips, and a simplified one-line "n_games + value" framing for
per-TC chips. The current copy "Based on your most recent 3000 rated games
per time control over the last 36 months" misleads users into thinking they
have 3000 games per TC.

Scope: backend wire-shape widening (no new computation) + frontend popover
rewrite + Vitest updates. Bullets 1, 3, 4 unchanged.

</domain>

<decisions>
## Implementation Decisions (locked from /gsd-explore)

### Aggregated chip tooltip — bullet 2 new shape

5 affected flavors: `score-gap`, `achievable`, `parity`, `conversion`, `recovery`.

```
Based on a weighted average of <metric_label> percentiles from up to 3000
games per time control over the last 36 months. Only games vs opponents
within +/-100 Elo are used:
- bullet: <value> over <n_games> games -> <percentile> percentile
- blitz: <value> over <n_games> games -> <percentile> percentile
- ...
```

Per-TC line rules:
- **Above floor with percentile**: render `<tc>: <value> over <n_games> games -> <percentile> percentile`.
- **Above floor but percentile is None** (CDF out-of-range — already dropped from the weighted-mean num+denom by `_aggregate_per_tc_percentile`): **drop the line entirely.** Do NOT render it.
- **Played but below floor** (no row in `per_tc_rows`, user has > 0 games in that TC): render `<tc>: insufficient games`.
- **Zero games in TC**: omit the line entirely.

TC ordering: `bullet`, `blitz`, `rapid`, `classical`.

### Per-TC chip tooltip — bullet 2 simplified

3 affected flavors: `time-pressure-score-gap`, `clock-gap`, `net-flag-rate`.

Bullet 2 (Option A — terser):
```
Based on <n_games> of your recent <tc> games over the last 36 months, vs
opponents within +/-100 Elo. Your value: <value>.
```

### Value formatters per flavor (frontend)

- `score-gap`, `achievable`, `parity`, `conversion`, `recovery`, `time-pressure-score-gap`:
  signed score, 2 decimals (e.g. `+0.12`, `-0.04`). Matches chart precision.
- `clock-gap`: signed integer percent (e.g. `+5%`, `-3%`). Multiply raw fraction by 100 and round.
- `net-flag-rate`: signed integer percent (e.g. `-2%`, `+1%`). Same convention.

### Percentile display in per-TC lines

Integer in [1, 99] — same clamp as the chip face (`MIN_PERCENT=1`, `MAX_PERCENT=99`).
No `p` prefix. Trailing word "percentile" provides the unit.

### Backend wire shape

Add a `PerTcBreakdownOut` Pydantic model:
```python
class PerTcBreakdownOut(BaseModel):
    tc: TimeControlBucket  # Literal["bullet", "blitz", "rapid", "classical"]
    value: float | None    # None when below floor with games > 0
    n_games: int           # user's game count in this TC (>= 0)
    percentile: float | None  # None when above floor but CDF out-of-range
```

Branch semantics on frontend:
- `value != null && percentile != null`: above floor with percentile → render full line.
- `value != null && percentile == null`: above floor but CDF out-of-range → DROP line.
- `value == null && n_games > 0`: below floor → render "insufficient games" line.
- `n_games == 0`: should not be emitted by backend, but if it appears, frontend drops it.

For the 5 aggregated chips, add `*_per_tc: list[PerTcBreakdownOut]` alongside the existing `*_percentile` scalar:
- `ScoreGapMaterialResponse.score_gap_per_tc`
- `ScoreGapMaterialResponse.score_gap_conv_per_tc`
- `ScoreGapMaterialResponse.score_gap_parity_per_tc`
- `ScoreGapMaterialResponse.recovery_score_gap_per_tc`
- `EndgamePerformanceResponse.achievable_score_gap_per_tc`

For the 3 per-TC chips on `TimePressureTcCard`, the `value` and `n_games` are already in the `PercentileRow` consumed at `endgame_service.py:2072`. Add two fields per chip family:
- `time_pressure_score_gap_n_games: int | None`, `time_pressure_score_gap_value: float | None`
- `clock_gap_n_games: int | None`, `clock_gap_value: float | None`
- `net_flag_rate_n_games: int | None`, `net_flag_rate_value: float | None`

Per-TC card chips already know their own TC from `card.tc`. The value is the chip-cohort value (PercentileRow.value), which may differ from the headline metric value displayed on the card (e.g. Clock Gap percentile is computed against a different sample than the displayed Clock Gap mean). Render the PercentileRow value in the tooltip even when it differs — the tooltip discloses the basis of the percentile, not the card's headline number.

### Per-TC game-count source (for "insufficient games" detection)

The endgame service already computes per-TC game counts elsewhere (used for `_aggregate_per_tc_percentile` weight). For TCs with games but no PercentileRow (below floor), the n_games for that TC comes from the same `endgame_rows`/`bucket_rows` aggregation that drives WDL counts — group by `time_control_bucket` and count rows.

Pragmatic alternative: compute the per-TC game counts once at the top of the response builder from the existing rows, build a `dict[TimeControlBucket, int]` of total games per TC, then iterate the 4 buckets producing `PerTcBreakdownOut` entries:
- If TC in `per_tc_rows`: emit row with value, n_games, percentile from PercentileRow.
- Elif TC has games > 0 in the per-TC game count dict: emit row with value=None, n_games=count, percentile=None.
- Else: omit.

</decisions>

<specifics>
## Specifics

- Existing helper `_aggregate_per_tc_percentile` at `app/services/endgame_service.py:1267` — verified to compute a game-count-weighted mean. The new prose "weighted average of percentiles" is factually accurate.
- `PercentileRow` at `app/repositories/user_benchmark_percentiles_repository.py:42` already carries `value`, `percentile`, `n_games` per (user, metric, TC).
- `percentile_rows` fetched once per request at `endgame_service.py:2539`/`2920` and threaded through `_compute_score_gap_material`, `_compute_endgame_performance` (and the time pressure card builder at `:2072`).
- Frontend `PercentileChipPopoverBody` at `frontend/src/components/charts/PercentileChip.tsx:158` — bullet 2 lines `192-194`. Bullets 1, 3, 4 stay unchanged.
- Vitest at `frontend/src/components/charts/__tests__/PercentileChip.test.tsx` — bullet 2 assertions need updating across all 8 flavors. The flame-icon regression guard (Test 9) and the bullet 4 anchor disclosure tests remain unchanged.
- Per-TC chips already know their TC from `card.tc` — only need n_games + value props plumbed onto the chip.

</specifics>

<canonical_refs>
## Canonical References

- `frontend/src/components/charts/PercentileChip.tsx` — current bullet 2 (lines 192-194)
- `app/services/endgame_service.py:1267` — `_aggregate_per_tc_percentile`
- `app/services/endgame_service.py:2072` — per-TC chip percentile attachment
- `app/repositories/user_benchmark_percentiles_repository.py:42` — `PercentileRow`
- CLAUDE.md — pre-PR checklist, ty rules, theme.ts constants, no em-dashes in user-facing copy
- MEMORY: `feedback_popover_copy_minimalism.md` — popover prose minimalism (this change adds concrete data points, not jargon)
- MEMORY: `feedback_percentile_chip_tooltip_disclosure.md` — percentile chip MUST disclose benchmark composition, recent-games basis, filter independence, per-metric rating correlation. This change strengthens "recent-games basis" disclosure by making n_games concrete.

</canonical_refs>
