# Phase 60: Opponent-based baseline for Endgame Conversion & Recovery — Context

**Gathered:** 2026-04-13
**Status:** Ready for planning
**Mode:** Discuss (`--auto --chain`; all gray-area calls pre-resolved in user conversation before workflow launch)

<domain>
## Phase Boundary

The "Endgame Conversion & Recovery" section (rendered by `EndgameScoreGapSection`) compares each material bucket's user score against `overall_score` — the user's weighted average across all games. That baseline is not rating-calibrated: a 1500-rated user in Recovery is expected to underperform a globally-weighted average, so the bullet chart's "warning zones" had to be hand-tuned per bucket (`NEUTRAL_ZONES` at lines 20-24) to compensate.

This phase replaces that global-average baseline with a **self-calibrating opponent baseline**: for each row, compare the user's score in that bucket against the opponents' score in the mirror-image situation, computed from the exact same filtered game set. Because matchmaking places the user against similarly-rated opponents, the opponent's conversion/even/recovery rate is automatically rating-calibrated and respects the user's filter-selected subset (platform, time control, color, rated, opponent strength, recency).

In scope:
- Backend `_compute_score_gap_material` (`app/services/endgame_service.py:492`) — compute opponent per-bucket score and sample size via same-game symmetry; no new SQL, no new query, no schema beyond the existing `ScoreGapMaterialResponse` path.
- Schema `MaterialRow` (`app/schemas/endgames.py:163`) — add `opponent_score: float | None` and `opponent_games: int`. Drop `overall_score` from `ScoreGapMaterialResponse` if it becomes unused in this section (verify no other consumer first).
- Frontend `EndgameScoreGapSection.tsx` — swap bullet-chart baseline, update `NEUTRAL_ZONES`, handle muted/hidden state when baseline is None, update column header, info-popover copy, and per-row diff label (both desktop table + mobile cards per the CLAUDE.md "apply changes to mobile too" rule).
- Frontend types (`frontend/src/types/endgames.ts:88`) — mirror backend field additions.
- Tests — update existing `_compute_score_gap_material` assertions; add coverage for opponent symmetry math, the 10-game muting threshold, and updated label/popover copy.

Out of scope (separate phase if ever needed):
- Per-endgame-type breakdowns ("Results by Endgame Type" table and per-category conv/recov aggregates) — this phase touches **only** the aggregate Endgame Conversion & Recovery section.
- Time-pressure / clock-stats sections — already self-calibrated via their own mechanisms.
- The Endgame Score Difference display (`endgame_score - non_endgame_score` — a different bullet/chip in the section header area).
- Reshaping backend query or repository layer — data to compute the opponent baseline is already present.
</domain>

<decisions>
## Implementation Decisions

### 1. Opponent baseline via same-game symmetry — no second query needed

**Math:** Each game has a single `user_material_imbalance`. The opponent observes its negation, so a game classified in the user's Conversion bucket (imb ≥ +1 persistent) is, from the opponent's perspective, a Recovery situation (imb_opp ≤ −1 persistent). Even↔Even. Recovery↔Conversion.

Within any bucket's game set, the opponent's score is exactly `1 − user_score` (since `user_wins + draws/2 + opponent_wins + draws/2 = games`, so opponent_score = (opp_wins + draws/2)/games = 1 − user_score).

Therefore the opponent baseline to display alongside each user-perspective row:

| User row (bucket) | Opponent baseline computed from | Sample size used |
| --- | --- | --- |
| Conversion | `1 − user_score[Recovery]` | `user_games[Recovery]` |
| Even | `1 − user_score[Even]` | `user_games[Even]` |
| Recovery | `1 − user_score[Conversion]` | `user_games[Conversion]` |

**Why:** Pure apples-to-apples — the opponent's conversion rate *against this specific user* under *this specific filter set* is the correct rating-calibrated peer baseline. Requires zero new queries; we already iterate all bucket counts in `_compute_score_gap_material`. This keeps the implementation lean and preserves the filter story automatically (whatever filters produced `material_rows` also produced the opponent's mirror rows).

**Edge case — opponent bucket empty:** When a user's swap-bucket has zero games, the baseline is `None`. Frontend must handle this cleanly (see decision #3).

### 2. Minimum-sample threshold: 10 games in the opponent's bucket

Match the WDL-bar mute threshold used elsewhere (e.g. Opening Explorer moves list). If the swap-bucket game count < 10:
- Backend emits `opponent_score: None` and `opponent_games: <actual count>` for that row.
- Frontend hides the bullet chart and the numeric `diff` label for that row, substituting a short muted caption: `"n < 10 — baseline unavailable"` (exact wording left to executor / finalize in plan).

Do **not** fall back to the global average — the user explicitly chose option (a), clean single-metric replacement.

**Constant location:** Add `_MIN_OPPONENT_SAMPLE = 10` near `_MATERIAL_ADVANTAGE_THRESHOLD` in `endgame_service.py`. Use CLAUDE.md's no-magic-numbers rule. Frontend re-exports or duplicates the constant for display logic (prefer a single `MIN_OPPONENT_BASELINE_GAMES` constant in a shared frontend lib file since threshold must be visible for muting logic and potentially for copy).

### 3. UI changes — scope is the three bullet charts + their labels/copy

**Desktop table header (line 95-97 today):**
- Before: `Score vs Overall Score ({overallFormatted})`
- After: `Score vs Opponent` (per-row opponent score appears next to the diff; no single constant in header since the baseline differs per row).

**Mobile card label (line 186-188 today):** Same directional change — change the "Score vs Overall Score (X.XX)" line to show the per-row opponent score, e.g. `Score vs Opponent (0.44)` where `0.44` is that row's specific `opponent_score`.

**Per-row diff label:**
- Before: `{row.score.toFixed(2)} ({diffLabel})` where diffLabel = `±0.08` vs overall.
- After: `{row.score.toFixed(2)} vs {opponent_score.toFixed(2)} ({diffLabel})` where diff = `row.score − row.opponent_score`. When `opponent_score is None`, render the user's own score alone with a muted `n < 10` suffix.

**Info popover (lines 54-64):** Rewrite the entire body to explain the self-calibrating peer comparison. Draft (executor may refine wording):

> The table shows how your score in each material situation compares to how your opponents perform against you in the mirror situation. When you enter an endgame with a material advantage (Conversion), your baseline is your opponents' performance when they enter endgames with an advantage (i.e. games where you were down material). This is self-calibrating — your opponents are rating-matched by the platform, so the baseline automatically adapts as you climb. Bars near the neutral zone mean you're performing about the same as equally-rated players in the same situation; to the right, you outperform; to the left, you underperform. Baselines are hidden when the opponent sample is smaller than 10 games.

**NEUTRAL_ZONES rework:** With the new baseline the expected diff is **zero** for all three buckets (equally-matched players should score equally in mirrored situations). Replace the per-bucket asymmetric zones with a single symmetric zone — `{ min: -0.03, max: 0.03 }` for all buckets. (3pp feels right as "essentially matched"; planner should confirm this reads well visually and tune if the executor finds the zone too narrow/wide during UI review.)

Since all three buckets now share the same zone, collapse the per-bucket `NEUTRAL_ZONES` record into a pair of constants (`NEUTRAL_ZONE_MIN`, `NEUTRAL_ZONE_MAX`) at the top of the file.

### 4. Schema: add fields, consider dropping `overall_score`

Add to `MaterialRow`:
```python
opponent_score: float | None   # opponent's score in the mirror bucket; None when sample < 10
opponent_games: int            # opponent's sample size (== swap-bucket game count)
```

**`overall_score` disposition:** Still lives on `ScoreGapMaterialResponse`. It was consumed only by `EndgameScoreGapSection` header and mobile card labels — both of which change in this phase. If grep confirms no other consumer, **drop it** from the response. If grep finds a surviving consumer, leave it but mark it as deprecated in the docstring. Planner: include the grep as a step before deciding.

Frontend mirror (`frontend/src/types/endgames.ts`): add `opponent_score: number | null` and `opponent_games: number` to `MaterialRow`; drop `overall_score` from `ScoreGapMaterialResponse` if backend drops it.

### 5. Tests

**Backend — `tests/test_endgame_service.py`:**
- Update existing tests that assert on `overall_score` or absence of opponent fields.
- Add `TestScoreGapMaterialOpponentBaseline`:
  - Symmetric case: user Conversion 60%/100 games, user Recovery 40%/100 games → opp_conversion baseline (on user Conversion row) = 0.60, opp_recovery baseline (on user Recovery row) = 0.40. (Numbers chosen so the mirror math is easy to verify.)
  - Empty-swap case: user Recovery has 0 games → user Conversion row's `opponent_score` is None, `opponent_games` == 0.
  - Below-threshold case: user Recovery has 9 games → user Conversion row's `opponent_score` is None, `opponent_games` == 9.
  - At-threshold case: user Recovery has 10 games → user Conversion row's `opponent_score` is computed and non-None.
- Preserve the existing bucket-sum invariant test (`sum(material_rows.games) == endgame_wdl.total`).

**Backend — `tests/test_endgames_router.py`:** update response-shape assertions if any reference `overall_score` or the old `MaterialRow` shape.

**Frontend — component tests (if present for `EndgameScoreGapSection`):** update fixtures to include `opponent_score` / `opponent_games`; add a case for the muted state. If no component test exists today, do NOT add one just for this phase — existing coverage pattern for this file is via type checks + manual UI review.

### 6. Filter interaction

No change needed. The opponent baseline is derived from the same `entry_rows` that already went through `apply_game_filters()` via `query_endgame_entry_rows` (and friends) before reaching `_compute_score_gap_material`. Whatever filters the user has active — color, time control, platform, rated, opponent strength, recency — automatically shape both the user's and the opponent's subset identically.

**Verification angle for planner:** add a brief integration-style test or a manual verification step confirming that toggling a filter changes both the user score and the opponent score in lockstep.

### Folded todos

None — no pending todos matched this phase's scope.
</decisions>

<code_context>
## Existing Code Insights

- **`_compute_score_gap_material`** already iterates each bucket's wins/draws/losses (`app/services/endgame_service.py:492-639`). Computing `opponent_score = 1 − user_score` per swap-bucket is a 6-line addition after the existing `material_rows` list is built. No new passes over data, no new queries.
- **`MaterialRow.score`** is `(win_pct + draw_pct/2) / 100` in `[0.0, 1.0]`. Opponent's score in the same game set is `1 − score` exactly — arithmetic identity, no rounding drift beyond what the existing score rounding already imposes.
- **Frontend bullet chart** (`MiniBulletChart` consumed by `EndgameScoreGapSection` lines 132-138 desktop, 193-198 mobile) takes `value`, `neutralMin`, `neutralMax`. Swap is a pure prop change — no new component or rendering logic.
- **Existing `overall_score`** lives on `ScoreGapMaterialResponse` only for this section's header/mobile-card baseline display. Removal is localized; verify via `grep -rn "overall_score" frontend/src app` before deleting.
- **Filter pipeline** is untouched — `apply_game_filters()` already shapes `entry_rows` upstream in `query_endgame_entry_rows`. Cross-phase consistency with time-pressure self-calibration (Phases 54-55) achieved without touching their code.
- **No backfill, no migration.** This is a pure read-path change. No DB schema edits, no alembic revision, no reimport needed.
</code_context>

<specifics>
## Specific Ideas

- **Symmetry implementation sketch:** after the existing bucket loop, build the final `MaterialRow` list with a tiny lookup: `swap = {"conversion": "recovery", "even": "even", "recovery": "conversion"}`. Then for each row `b` set `opponent_score = 1 - bucket_score[swap[b]]` when `bucket_games[swap[b]] >= MIN_OPPONENT_SAMPLE` else `None`. Include `opponent_games = bucket_games[swap[b]]` always, so the frontend can show the muted caption with the real count.
- **Copy: wording direction.** The user approved "implementer's judgment" on wording. Preferred axis: "opponent" singular for baseline label, "opponents" plural in popover narrative (fits how time-pressure copy already reads in related sections). Avoid the word "peer" — user didn't use it and "opponent" maps more directly to what's on the screen. Avoid "expected" (implies a prediction model); use "baseline" instead.
- **Neutral zone sanity check:** 3pp (`±0.03`) is tight. If the executor finds the zone visually cramped in the bullet chart (e.g. the neutral band becomes a hairline), widen to `±0.05` rather than the old asymmetric zones. Do **not** revert to per-bucket asymmetric zones — that would defeat the self-calibrating purpose.
- **Muted rendering option:** simplest is to render the bullet-chart cell as a muted text span (`<span className="text-xs text-muted-foreground">n &lt; 10</span>`) when `opponent_score === null`, instead of the bullet bar. Keep the user's own score visible in the Score column — just the vs-opponent comparison is suppressed.
- **Admin vs non-admin:** no admin gating added or removed in this phase. The section is visible to all users today and remains so.
- **API versioning:** no version bump needed — `/endgames` response is still internal to the frontend and non-breaking additions (new optional fields) + removal of an unused field (`overall_score`) can go in a single commit.
- **Verify with MCP `flawchess-db` during UI review:** pick a real user's filters, pull bucket counts, eyeball that `1 − user_score[Recovery]` matches the opponent_score shown in the Conversion row for that user.
</specifics>

<deferred>
## Deferred Ideas

- **Global peer baseline across all users** (as a secondary reference alongside opponent baseline) — user explicitly rejected, option (a). If a future product need surfaces "I want to know how I stack up against all users at my level regardless of who I play", that's a separate phase requiring a global aggregate materialized view.
- **Applying opponent-based baseline to per-endgame-type breakdown** — user explicitly out-of-scope for phase 60. Could be a follow-up phase if the aggregate version lands well.
- **Absolute benchmarks ("top players convert at 85%")** — not in scope; the bullet chart is designed for relative comparison. If added, belongs in a separate informational chip, not this section.
</deferred>

<canonical_refs>
## Canonical References

- `.planning/ROADMAP.md` — Phase 60 definition (goal + 6 success criteria)
- `.planning/phases/59-fix-endgame-conv-recov-per-game-stats/59-CONTEXT.md` — bucket accounting rules (NULL→Even, group-then-pick dedupe, conversion-over-recovery tiebreak) that this phase preserves unchanged
- `.planning/phases/54-time-pressure-clock-stats-table/54-CONTEXT.md` and `55-CONTEXT.md` — the self-calibrating time-pressure metrics whose design philosophy this phase extends to material buckets
- `app/services/endgame_service.py:485-639` — `_compute_score_gap_material`, primary edit site for decisions #1, #2, #4
- `app/schemas/endgames.py:160-196` — `MaterialBucket`, `MaterialRow`, `ScoreGapMaterialResponse` — schema edits per decision #4
- `app/repositories/query_utils.py` — `apply_game_filters()` shared filter utility (no edit, but shapes the subset that makes opponent baseline filter-respecting per decision #6)
- `frontend/src/components/charts/EndgameScoreGapSection.tsx` — full rewrite of desktop table + mobile cards copy/bullet logic per decision #3
- `frontend/src/types/endgames.ts:86-103` — `MaterialRow` / `ScoreGapMaterialResponse` TS mirror; add `opponent_score` / `opponent_games`
- `tests/test_endgame_service.py::TestScoreGapMaterialInvariant` — existing invariant test to preserve + sibling class for new opponent-baseline tests
- `tests/test_endgames_router.py` — response-shape assertions; update if touched by schema change
- User conversation transcript (2026-04-13) — where the 10-game threshold, option (a) clean replacement, same-filter respect, scope limitation to the aggregate section, and "implementer's judgment on wording" were locked in
</canonical_refs>
