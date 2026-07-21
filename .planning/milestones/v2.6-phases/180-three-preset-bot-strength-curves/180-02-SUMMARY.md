---
phase: 180-three-preset-bot-strength-curves
plan: 02
subsystem: calibration
tags: [bradley-terry, mle, elo, calibration, g_preset, stdlib, python]

# Dependency graph
requires:
  - phase: 173-anchor-ladder-self-calibration
    provides: calibration_anchor_fit.py Zermelo/MM fit + INTERNAL_RATING internal scale
provides:
  - "fit_bot_cell_rating: single-parameter pinned-anchor MLE (1 free bot strength vs 10 FIXED anchors)"
  - "Two-fits-per-cell driver emitting G_preset = rating_vs_maia - rating_vs_sf directly (never merged)"
  - "load_bot_cells TSV loader + bootstrap_bot_cell_ci parametric CI + combine_preset_g_preset per-preset scalar"
  - "_write_bot_curves: caveated bot-curves JSON envelope (interface SEED-104 consumes)"
  - "New --bot-input/--out-bot-curves CLI path; anchor-ladder path untouched"
affects: [180-04 operator sweep, SEED-104 human-ELO offset formula]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Single-free-parameter specialization of the N-anchor Zermelo/MM fixed point"
    - "Two independent per-family fits against a shared fixed-rating dict (Pitfall 3: never average G_preset away)"
    - "Parametric multinomial bootstrap (aggregate counts sufficient since anchors held fixed, A3/A4)"

key-files:
  created: []
  modified:
    - scripts/calibration_anchor_fit.py
    - tests/scripts/test_calibration_anchor_fit.py

key-decisions:
  - "Fixed anchor ratings sourced from reports/data/anchor-ladder-internal-scale.json (--internal-scale-json), not hardcoded from the .mjs — single source of truth, stays in sync"
  - "Reported BOTH per-cell g_preset and a per-preset inverse-CI-weighted combined scalar (open-Q3 recommendation)"
  - "Parametric bootstrap resamples per-anchor W/D/L multinomially; anchor uncertainty deliberately not propagated (A4)"

patterns-established:
  - "Bot-cell fit path is fully additive: existing --input/--out-js/--out-json anchor-ladder mode is byte-for-byte unchanged"
---

# Phase 180 Plan 02: Bot-Cell Strength-Curve Fit (fit_bot_cell_rating + G_preset) Summary

Extended `scripts/calibration_anchor_fit.py` with a single-parameter pinned-anchor Bradley-Terry/Elo MLE that fits one bot cell's strength against the 10 fixed Phase-173 anchors, run twice per cell (vs-Maia, vs-SF) to emit the cross-family style gap `G_preset` directly, plus a bot-curves JSON writer mirroring the anchor-ladder envelope and pytest ground-truth coverage.

## What Was Built

**Task 1 — fit path (`scripts/calibration_anchor_fit.py`, commit ce3d0fd2):**
- `fit_bot_cell_rating(win_counts_vs_fixed, games_vs_fixed, fixed_ratings, tol, max_iter) -> float` — specializes the file's Zermelo/MM iteration from N free anchors to 1 free bot strength against N FIXED opponents. Reuses `RATING_SCALE`, `DEFAULT_FIT_TOL`, `DEFAULT_FIT_MAX_ITER`; applies a per-anchor continuity clamp (`_clamp_bot_win_counts`) mirroring `_clamp_win_counts`'s `epsilon = 1/(SCORE_CLAMP_EPSILON_DIVISOR*games)` formula. Fail-loud (T-180-02) on empty games or an unknown anchor label.
- `load_bot_cells(path)` — aggregates the harness's per-(cell,anchor) WDL TSV by `(bot_elo, bot_blend)`, splitting each row's W/D/L into Maia/SF family dicts; fail-loud on a missing required column; carries the optional `beyond_ladder` flag through.
- `fit_all_bot_cells(...)` — two `fit_bot_cell_rating` calls per cell against the SAME fixed dict, `g_preset = rating_vs_maia - rating_vs_sf` computed directly (Pitfall 3).
- `bootstrap_bot_cell_ci(...)` — parametric multinomial bootstrap per anchor family.
- `combine_preset_g_preset(...)` — per-preset inverse-CI-weighted combined `G_preset` scalar (open-Q3: report both per-cell and combined).
- `_write_bot_curves(...)` — JSON envelope with the verbatim INTERNAL-SCALE caveat (T-180-03), per-cell ratings/CIs/`g_preset`/`beyond_ladder`, and a `per_preset` block.
- New CLI: `--bot-input`, `--out-bot-curves`, `--internal-scale-json`. Anchor-ladder path (`--input`/`--out-js`/`--out-json`) left intact — its flags relaxed from `required=True` to a mode-branch validation.

**Task 2 — pytest (`tests/scripts/test_calibration_anchor_fit.py`, commit 624bbe00):**
- `test_fit_bot_cell_rating_synthetic_ground_truth` — exact-BT synthetic counts recover a known 1450 rating within 1 Elo.
- `test_g_preset_sign` — asymmetric fixture (beats SF harder than Maia) yields a clearly-signed negative `g_preset` from two separate fits.
- `test_fit_bot_cell_rating_rejects_bad_input` — empty games and an unknown anchor label each raise `ValueError`.

## Gate Results

- `ast.parse` clean; `fit_bot_cell_rating`, `_write_bot_curves`, `--bot-input` all present; 4 `fit_bot_cell_rating(` occurrences (1 def + 2 driver call sites + 1 bootstrap).
- `uv run ruff format` / `uv run ruff check --fix`: clean (fixed one E741 ambiguous `l`).
- `uv run ty check scripts/calibration_anchor_fit.py tests/scripts/test_calibration_anchor_fit.py`: zero errors. Stdlib-only (no numpy/scipy).
- `uv run pytest tests/scripts/test_calibration_anchor_fit.py -k "fit_bot_cell_rating or g_preset" -x`: 3 passed. Full file: 10 passed (7 prior + 3 new).
- Smoke test: ground-truth recovery exact (err 0.0), JSON round-trip produces `_caveat`/`cells`/`per_preset`.

## Deviations from Plan

**1. [Rule 3 - Blocking] `--internal-scale-json` flag for fixed anchor ratings**
- **Found during:** Task 1 CLI wiring.
- **Issue:** The plan's read_first suggested hardcode-importing the 10 fixed INTERNAL_RATING values from `scripts/lib/calibration-internal-scale.mjs`, but that is a JS module Python cannot import.
- **Fix:** Added `--internal-scale-json` (default `reports/data/anchor-ladder-internal-scale.json`) + `load_fixed_ratings()` reading the `internal_rating` key. This is the JSON the anchor-ladder path itself writes, so the two stay in sync without duplicating the numbers.
- **Files modified:** scripts/calibration_anchor_fit.py
- **Commit:** ce3d0fd2

Otherwise the plan was executed as written. The aggregated bot-cell TSV column names (`bot_elo`, `bot_blend`, `anchor`, `wins`, `draws`, `losses`) were aligned to the existing harness per-(cell,anchor) TSV schema already in `reports/data/`.

## Known Stubs

None. The bot-curves JSON is a data-shape contract consumed by Plan 04's operator sweep and SEED-104; no runtime stub introduced.

## Self-Check: PASSED
- FOUND: scripts/calibration_anchor_fit.py
- FOUND: tests/scripts/test_calibration_anchor_fit.py
- FOUND commit: ce3d0fd2 (feat 180-02 fit path)
- FOUND commit: 624bbe00 (test 180-02)
