---
id: SEED-014
status: dormant
planted: 2026-05-10
planted_during: /gsd-explore session immediately after Phase 82 (LLM prompt awareness of "Where you start" / "What you do with it") completed
trigger_when: scoping the next endgame analytics phase, or whenever the next round of Endgame-Insights tile work comes up
scope: phase (single, ~3 plans) — eval→expected-score conversion + new bullet-chart metric in "Where you start" + (optional) prompt awareness
---

# SEED-014: Stockfish-baseline expected score for endgame entries — juxtaposed with achieved score

## Why This Matters

Phases 81 and 82 established the "Where you start" / "What you do with it" pair:

- **"Where you start"** — `entry_eval_mean_pawns`, signed Stockfish eval at endgame entry (sig-tested against 0).
- **"What you do with it"** — `endgame_score` (W=1/D=0.5/L=0), Wilson-tested against 50%.

These are powerful diagnostics, but they live in **different units** (centipawns vs score). The user has to mentally translate "+0.46 pawns at entry" into "expected score from that position" to judge whether 46.6% achieved is over- or under-performance. Today the LLM does that translation in prose; the UI cannot.

The proposal: convert each per-game endgame-entry `eval_cp` to an **expected score** in [0, 1] via the Lichess sigmoid, then surface the cohort distribution of those expected scores as a **second bullet chart inside "Where you start"**, juxtaposed with the existing `endgame_score` bullet chart in "What you do with it". Same units (W+0.5D ∈ [0,1]), same Wilson-style CI machinery, same visual idiom — directly readable as "Stockfish-baseline expectation vs achieved".

This is a finer-grained complement to Conversion / Parity / Recovery, which today uses **discrete eval thresholds** at ±1.0 pawns (`EVAL_ADVANTAGE_THRESHOLD = 100` in `app/services/endgame_service.py:166`). A position at +0.99 vs +1.01 currently flips between "parity" and "conversion" with very different implicit baselines; the sigmoid handles the transition smoothly and uses the full eval magnitude (a +5.0 entry has a ~0.95 expectation; a +1.1 entry has ~0.66 — both bucketed identically as "conversion" today).

## When to Surface

Trigger any of:

1. The next time Endgame Insights tile work or zone calibration is on the table.
2. A user notices "my entry eval was clearly positive, but my score was 50% — is that good or bad?" and the LLM narration alone doesn't make the gap visually obvious.
3. Roadmap planning for an Endgame Insights v2 milestone.

## Proposed Scope (3 plans)

### Plan 1 — Add `app/services/eval_utils.py` with the Lichess conversion

Single new module with one constant and two pure functions:

- `LICHESS_K = 0.00368208` (per Lichess accuracy/winning-chances doc, sigmoid scale).
- `eval_cp_to_expected_score(eval_cp: int, user_color: Literal["white", "black"]) -> float` — applies sign flip per `user_color` (mirroring the convention in `_classify_endgame_bucket` in `endgame_service.py:170-204`), returns `1 / (1 + exp(-LICHESS_K * user_eval_cp))`.
- `eval_mate_to_expected_score(eval_mate: int, user_color: Literal["white", "black"]) -> float` — returns `1.0` if user is the side mating, `0.0` otherwise. Do NOT route mate scores through the sigmoid (a mate-in-3 with `|eval_cp| ≈ 2900` would map to ~0.999, not 1.0, and the Phase 82 `|eval_cp| < 2000` filter excludes them anyway).
- Unit tests covering: sign of `eval_cp` for both colors, the sigmoid is centred at 0.5, mate-for-user → 1.0, mate-against-user → 0.0, NULL handling raises (callers filter NULLs upstream).

This module will also be reusable later if we ever want expected-score on the Openings side (low-priority — opening-end evals cluster around 0, so the sigmoid will mostly emit 0.50 and the signal-to-noise is poor; out of scope here, see "Why not Openings" below).

### Plan 2 — Per-game cohort metric in `endgame_repository.py` / `endgame_service.py`

Mirror the existing `entry_eval_mean_pawns` plumbing (`endgame_repository.py:793-841`, `endgame_service.py:1670-1712`):

- Per game in the cohort, compute one expected score (sigmoid for `eval_cp`, or 0/1 for `eval_mate`), filtered identically to entry-eval (mate excluded — actually keep mate here; mate is meaningful as expected score 0/1 and the existing entry-eval filter only excludes mate because mate has no centipawn value to average; expected-score has a defined value for mate, so we **keep** mate games and only drop NULL/NULL rows).
- Aggregate per user: mean per-game expected score, n.
- Sig test: Wilson interval against 50% (the project's chess-score Wilson util — per memory `feedback_wilson_chess_score.md`, do not editorialize methodology). Output: `entry_expected_score`, `entry_expected_score_n`, `entry_expected_score_p_value`, plus the CI bounds the bullet chart needs.
- New schema field on `EndgameStartVsEnd` (or wherever the tile pair lives — see Phase 81 `app/schemas/endgames.py:124-140`).

Note on the test: it's technically paired with `endgame_score` (each game contributes both). Two independent Wilson CIs slightly understate the precision of the *gap*. For a single-sentence verdict you'd want a paired test. For the visual juxtaposition, two CIs is the right call — users compare bands. Don't editorialize this in prose; just ship the two bullet charts.

### Plan 3 — UI: 2×2 stacked layout across the twin tiles

Restructure both tiles so each hosts **two stacked rows of equal width**, with the bottom row directly comparable across tiles:

**"Where you start"** stacks:
1. **"Endgame entry eval"** + bullet chart (already exists, centipawn axis)
2. **"Predicted score"** + bullet chart (NEW, W+0.5D axis ∈ [0,1])

**"What you do with it"** stacks:
1. **"Win / Draw / Loss"** + WDL chart (REPEATED from the "Games with vs without Endgame" section — same component, scoped to endgame games only)
2. **"Endgame score"** + bullet chart (already exists, W+0.5D axis ∈ [0,1])

This gives a clean 2×2 grid: equal-width charts, eval-on-top for context, **the two bottom-row bullet charts share the same W+0.5D axis and cohort-band styling so the predicted-vs-achieved gap is directly readable across the two tiles**. The top row similarly juxtaposes "what the position looked like" (signed centipawns) with "what actually happened" (WDL split).

Notes:

- The WDL chart in row 1 of "What you do with it" reuses the existing component from "Games with vs without Endgame" — scoped to the endgame-only subset (same cohort as the rest of the tile). Don't reimplement; lift and parameterize.
- Cohort band for the new "Predicted score" chart: derived from `/benchmarks` (extend SKILL.md as Plan 4 below if we want a formal calibration; or pool the in-prod cohort distribution as a v1 shortcut). Lean toward formal /benchmarks calibration — consistency with Phase 82's bands matters more than a one-week shortcut.
- Tile-color rule: if Phase 82's `(zone in green/red) AND p < 0.05` rule landed (Phase 81 D-09 amendment), apply the same rule. Otherwise reuse whatever rule "Where you start" currently uses for entry-eval.
- Mobile stacking order: same as desktop (eval/WDL on top, score-axis charts on bottom), so the "compare the bottom row" affordance survives the responsive collapse.

### Plan 4 — (Optional) Extend `/benchmarks` SKILL.md with an `entry_expected_score` section

Mirror the Phase 82 pattern (`reports/benchmarks-YYYY-MM-DD.md`): pooled distribution, TC × ELO cells, marginals, Cohen's d collapse verdict, recommended bands. Lock the bands into `endgame_zones.py` as `ENTRY_EXPECTED_SCORE_ZONES` and regenerate `endgameZones.ts`.

If skipped, the v1 ships with hand-picked or pooled-IQR bands; rerun /benchmarks before the next zone-recalibration sweep.

### Plan 5 — (Optional, small) Prompt awareness in `app/prompts/endgame_insights.md`

Add `entry_expected_score` to the glossary (definition: "Stockfish-baseline expected score from your endgame-entry positions, via the Lichess winning-chances sigmoid; this is what a 2300+ rated player would score from those positions"). Expand the `endgame_start_vs_end` subsection guidance: the LLM should narrate the **gap** between `entry_expected_score` and `endgame_score` as the headline diagnostic, with `entry_eval_pawns` as the explanatory unit. Bump `_PROMPT_VERSION` in `insights_llm.py`.

This is small and natural, but split-able — could ship as a /gsd-quick task after Plans 1-3 are in production.

## Design Decisions Captured Now

- **Lichess sigmoid, not Stockfish native WDL.** Stockfish's `get_wdl_stats()` is more material-aware but requires re-evaluating positions at runtime; we already store `eval_cp` from prior backfills (`scripts/backfill_eval.py`). The Lichess curve is the standard mapping for historical centipawn data. Source: Lichess accuracy/winning-chances doc and Lichess team blog (sigmoid `1 / (1 + e^(-0.00368208 * cp))`).
- **Framing: "Stockfish baseline" / "ceiling", not "expected" or "underperformance".** The Lichess curve was fitted on 2300+ rapid games. A 1500 player will systematically score below it from positive-eval positions and above it from negative-eval positions. Calling the gap "underperformance" misleads (it's mostly rating-tilt). Calling it "gap to perfect play" or "Stockfish baseline" reframes the systematic bias as the **point** — weaker players want to see the ceiling.
- **Why not Openings.** End-of-opening evals cluster around 0 cp, so the sigmoid emits ~0.50 nearly everywhere. The actual game outcome is dominated by middle/endgame play, not opening choice. Tooltip would mostly show "expected 0.51, actual 0.47" across the board — eyeball-cost without signal. Endgame entry evals span a wide range (-300 to +300+ cp) and the player's job *is* to convert/defend, so the gap is informative.
- **Why per-game (not per-eval-bin) aggregation.** Per-game gives a cohort distribution of expected scores ∈ (0, 1) and another of actual scores ∈ {0, 0.5, 1}; both feed the project's Wilson chess-score util the same way `endgame_score` does today. Per-bin would be more diagnostic ("you score below baseline specifically when entering at +1.0…+2.0") but a much bigger UI lift and inconsistent with the existing bullet-chart idiom. Per-game wins on consistency.
- **Per-game expected score vs Conv/Recov.** Not redundant. Conv/Recov uses 3 hard-thresholded buckets and collapses each to a binary outcome; expected-score is continuous in eval and uses W+0.5D. They answer different questions: "how do you handle clearly winning/losing/balanced positions" vs "how close to optimal play do you score on average".

## Edge Cases (capture before they evaporate)

- **Sign convention.** `eval_cp` and `eval_mate` are stored white-perspective; conversion must flip sign per `user_color`. Mirror `_classify_endgame_bucket` (`endgame_service.py:170-204`) — same trap that Phase 82 had to handle.
- **Mate scores.** Map directly to expected score 0.0 or 1.0 depending on whose side is mating; do NOT route through the sigmoid. The current Phase 82 entry-eval pipeline excludes mates because there's no centipawn to average; the expected-score pipeline should **include** them with the 0/1 mapping (a forced mate against the user is a real expected-score signal).
- **NULL eval coverage.** Coverage of `eval_cp`/`eval_mate` on `endgame_span_entry` rows is not 100% on prod (per `scripts/backfill_eval.py` history). Cohort filter must require `eval_cp IS NOT NULL OR eval_mate IS NOT NULL`. Document n in the response so the bullet chart's "based on N games" footer matches what users see for entry-eval.
- **`|eval_cp| < 2000` clip.** Phase 82 applies this clip to entry-eval to prevent mate-in-12 outliers from skewing means. Expected-score uses the sigmoid which saturates around ±800 cp anyway, so the clip is mostly redundant — but **apply it for consistency** with Phase 82's "what counts as an analyzable endgame entry" cohort definition. Mate handling above takes care of true forced mates separately.
- **Naming collision.** `endgame_score` is already taken (Phase 81 — the achieved score in "What you do with it"). The new field needs a different key. Lean `entry_expected_score` (parallel to `entry_eval_mean_pawns`).

## Methodology Lessons Inherited from Phase 82

If Plan 4 (formal /benchmarks section) is on the table, copy the canonical CTE verbatim from `/benchmarks` SKILL.md — `lichess_username` join (NOT `benchmark_user_id`, which is ~30% populated), `bic.status='completed'`, `g.time_control_bucket::text = bsu.tc_bucket`, equal-footing `|opp_rating - user_rating| <= 100`, sparse-cell exclusion. See SEED-013 "Methodology Lessons" section for the full list — every one of those gotchas applies here too.

## Estimated Effort

3 plans for the core ship (Plans 1-3): ~1.5 days. Plus 1-2 plans optional (Plan 4 /benchmarks: ~half a day; Plan 5 prompt: ~1 hour). Smaller than Phase 82 because the data plumbing is shorter (sigmoid is a one-liner; no zone collapse-verdict work unless Plan 4 lands).

## Cross-references

- Phase 81 (twin-tile section): `.planning/phases/81-endgame-start-vs-end-twin-tile-section-above-the-wdl-table/`
- Phase 82 (LLM prompt awareness): `.planning/phases/82-llm-prompt-awareness-of-endgame-start-vs-end-metrics/`
- Conv/Recov eval thresholds: `app/services/endgame_service.py:162-211` (`EVAL_ADVANTAGE_THRESHOLD`, `_classify_endgame_bucket`)
- Entry-eval plumbing to mirror: `app/repositories/endgame_repository.py:793-841`, `app/services/endgame_service.py:1670-1712`
- Schema fields: `app/schemas/endgames.py:124-140`
- Zones registry: `app/services/endgame_zones.py` → `frontend/src/generated/endgameZones.ts` (regen via `scripts/gen_endgame_zones_ts.py`)
- /benchmarks skill: `.claude/skills/benchmarks/SKILL.md`
- Related seeds: SEED-013 (Phase 82 — direct predecessor), SEED-002 / SEED-006 (benchmark population zone work)
- Source for Lichess sigmoid: Lichess accuracy / winning-chances method, scaling constant `K = 0.00368208`
