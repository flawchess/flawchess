# Quick 261121-ha7: Preliminary facepalm IQR bands from prod data - Context

**Gathered:** 2026-11-21 (owner approved "option 1, in a worktree")
**Worktree:** `/home/aimfeld/Projects/Games/flawchess-facepalm-bands`, branch `quick/facepalm-prelim-bands` (off `main`).
Phase 258 runs concurrently in the main checkout; this task merges after 258.

## Goal

The Library Stats facepalm rows get a typical band and red/green verdicts now, instead of waiting for
SEED-261120-bzq. Two surfaces, one data source (`/library/facepalm-comparison`, `FacepalmBullet`):

- the "Facepalm blunders / 100 moves" tile in Flaw Stats (`FlawTiles.tsx` `FacepalmTile`, the `facepalm` row),
- the "Facepalm blunders" card in You vs. your opponents (`FacepalmCard.tsx`, three rows: `facepalm`,
  `facepalm_missed_win`, `facepalm_allowed_loss`).

The band is on the paired gap (you minus opponents, per 100 of your moves), exactly like the flaw rows.

## Why prod and not the benchmark DB

Checked 2026-11-21: only 18% of benchmark-DB blunders carry `played_line_material` (6.8% of lichess-eval
games, 50% of our own analyses) until the Phase 252 benchmark re-walk, so a benchmark-DB band would describe
a skewed subset. Prod has 93.8% line material and 98.8% `maia_best_prob` coverage. These bands are
**provisional**; SEED-261120-bzq replaces them with benchmark-DB zones (per Elo x TC) once 252 has finished.

## Measured quartiles, Phase 257 model (2026-11-21, superseded below)

Query: `261121-ha7-prod-quartiles.sql` (this directory). Basis: prod, non-guest users, human opponents,
chess.com + lichess, the most recent 1000 games per user x TC within 36 months
(`RECENT_GAMES_PER_TC_CAP`, `RECENCY_WINDOW_MONTHS`: the Phase 258 snapshot window), analyzed games only
(`full_evals_completed_at`), stats cut `FACEPALM_STATS_MIN` = 0.7, `FACEPALM_LIBRARY_LAMBDA`, the 257 type rule.
Per user x TC: mean of per-game paired deltas per 100 user moves (the `_paired_series` rule). Kept when
>= 20 analyzed games (`FLAW_COMPARISON_GATE`) and >= 0.8 scored coverage on both sides
(`FACEPALM_MIN_SCORED_COVERAGE`, the low-coverage rule). Score SQL verified identical to `facepalm_expr`
on 58,295 dev blunders.

| TC | users | games | facepalm Q1 / Q3 | missed win Q1 / Q3 | allowed loss Q1 / Q3 |
|---|---|---|---|---|---|
| bullet | 88 | 46,606 | -0.367 / +0.719 | -0.116 / +0.188 | -0.318 / +0.625 |
| blitz | 392 | 222,447 | -0.196 / +0.380 | -0.098 / +0.070 | -0.203 / +0.370 |
| rapid | 482 | 226,455 | -0.313 / +0.287 | -0.075 / +0.072 | -0.294 / +0.254 |
| classical | 123 | 17,120 | -0.852 / +0.179 | -0.065 / +0.121 | -0.805 / +0.068 |

Medians (facepalm): bullet +0.281, blitz +0.076, rapid -0.055, classical -0.333. Users' own facepalm rate
medians (per 100 moves): bullet 3.43, blitz 2.17, rapid 1.99, classical 0.92.

## Re-run on the Phase 259 model (2026-11-22, SUPERSEDES the table above)

Phase 259 switched the score to the stored scalar inputs (`material_loss`, `material_missed`,
`maia_best_reply_prob`) with refit coefficients. Same basis and gates as above; the score and type
SQL in `261121-ha7-prod-quartiles.sql` is now `facepalm_expr` / `facepalm_type_expr` compiled from
the app, unedited (no hand rewrite, so no parity check is needed). The branch was rebased onto main
(258 + 259) at the same time.

| TC | users | games | facepalm Q1 / Q3 | missed win Q1 / Q3 | allowed loss Q1 / Q3 |
|---|---|---|---|---|---|
| bullet | 88 | 46,606 | -0.320 / +0.721 | -0.104 / +0.162 | -0.325 / +0.700 |
| blitz | 395 | 223,546 | -0.216 / +0.368 | -0.098 / +0.064 | -0.195 / +0.386 |
| rapid | 486 | 228,211 | -0.311 / +0.284 | -0.078 / +0.080 | -0.317 / +0.274 |
| classical | 125 | 17,365 | -0.907 / +0.130 | -0.064 / +0.097 | -1.026 / +0.041 |

Medians (facepalm): bullet +0.267, blitz +0.021, rapid -0.035, classical -0.394. Users' own facepalm
rate medians (per 100 moves): bullet 3.68, blitz 2.44, rapid 2.24, classical 1.13.

Half-widths (bullet / blitz / rapid / classical): facepalm 0.53 / 0.30 / 0.30 / 0.52 (was 0.55 / 0.29 /
0.30 / 0.52), missed win 0.14 / 0.09 / 0.08 / 0.09 (was 0.16 / 0.09 / 0.08 / 0.10), allowed loss
0.52 / 0.30 / 0.30 / 0.54 (was 0.48 / 0.29 / 0.28 / 0.44).

## Decisions (LOCKED)

- **D-01 Registry.** New module `app/services/facepalm_zones.py`, mirroring `flaw_delta_zones.py`:
  `FACEPALM_ZONES: Final[Mapping[FacepalmMetric, Mapping[TimeControlBucket, ZoneBand]]]` built with
  `symmetric_band(q1, q3)` from the 3-dp quartiles above (reuse `ZoneBand` and `symmetric_band` from
  `flaw_delta_zones`, do not copy them), plus an accessor `facepalm_zone(metric, tc) -> ZoneBand`. Per TC, no
  Elo keying, centred on 0 (the significance gate tests against 0). Module docstring: basis as above,
  PROVISIONAL, prod-derived not benchmark-derived, replaced by SEED-261120-bzq, regenerate after a facepalm
  refit or a stats-cut change, evidence path `.planning/quick/261121-ha7-.../261121-ha7-prod-quartiles.sql`.
  `FacepalmMetric` lives in `app/schemas/library.py`, which imports `flaw_delta_zones`; avoid an import cycle
  (move or re-declare the Literal where flaw_delta_zones does it for its metrics, planner's call).
  Resulting half-widths (ceil to 0.01): facepalm 0.55 / 0.29 / 0.30 / 0.52, missed win 0.16 / 0.09 / 0.08 / 0.10,
  allowed loss 0.48 / 0.29 / 0.28 / 0.44 (bullet / blitz / rapid / classical). A test pins these.
- **D-02 Backend bullets.** `_build_facepalm_bullet` takes the TC and sets `zone_lo` / `zone_hi` from the registry
  and `has_zone=True` on both return paths, like `_build_flaw_bullet`. `FacepalmBullet.has_zone` default and the
  257 D-13 docstrings (schema, service) are updated. Significance is unchanged.
- **D-03 Verdict colours.** Frontend: `facepalmMetricCell` stops setting `noVerdict`, so tile and card dots get
  the standard `effectiveVerdict` (outside the band AND 99% significant = better/worse, else typical). Remove the
  `noVerdict` field from `GapCell` only if nothing else uses it after this change. Tile number colour stays
  `FACEPALM_BAND_SWATCH`.
- **D-04 Popover copy.** Both facepalm popovers (tile and card rows) drop `omitDirection` ("Fewer is better."
  shows, like every flaw row). The range line reads **"Typical gap among FlawChess players: {lo} to {hi}."**
  (not "players at your level", since the band has no Elo keying, and never the word "benchmark"), followed by the
  same chance / verdict sentence `rangeLine` in `GapPopover.tsx` appends. Build it in `facepalmRangeNote.ts`
  (reuse `gapWords`, `isChanceGap`, `effectiveVerdict` and the verdict sentences; export what is needed rather
  than duplicating strings). No "preliminary" caveat in user copy (popover minimalism); the provisional status
  lives in code and the seed. Remove `COPY_NO_RANGE` and any "no typical range" copy elsewhere (grep
  `facepalm.ts`, `FacepalmCard.tsx`, `FlawTiles.tsx`, info popovers).
- **D-05 Types are never compared with each other.** Each type row has its own band from its own distribution.
  No cross-type copy.
- **D-06 Scope fence.** Do not touch the Phase 258 surface (`fetch_facepalm_comparison`, the anchor/windowing,
  the basis line, `get_facepalm_comparison` beyond passing the TC into the bullet builder). Keep the diff in
  `library_service.py` minimal to ease the merge after 258.
- **D-07 Docs.** Append a note to `.planning/seeds/SEED-261120-bzq-*.md`: provisional prod bands shipped in
  `app/services/facepalm_zones.py` by quick 261121-ha7; item 2 of its scope now means replacing them with
  benchmark-DB zones. Add a `CHANGELOG.md` `## [Unreleased]` bullet (user-facing: facepalm rows in Library Stats
  now show a typical range and are coloured when clearly better or worse than typical).
- **D-08 Tests.** Backend: registry test (all 3 metrics x 4 TCs present, the half-widths above), bullet builder
  tests flipped from `has_zone False / zones 0` to the registry values (grep tests for `has_zone` on facepalm).
  Frontend: `facepalmRangeNote`, `FacepalmCard`, `FlawTiles`, `flawComparisonMeta` tests updated for verdict
  colour and the new copy.

## Gate

Before reporting done, run in the worktree: `uv sync --locked --group maia-inference` and `npm ci` (fresh
worktree), then ruff format/check, ty (app/ tests/ scripts/), `check_function_size.py --fail-over-depth 4`, the
touched backend test files plus `uv run pytest -n auto -x`, and in `frontend/` `npm run lint && npm run build &&
npm test -- --run && npm run knip`. The full pre-merge gate runs again at squash-merge time after 258.
