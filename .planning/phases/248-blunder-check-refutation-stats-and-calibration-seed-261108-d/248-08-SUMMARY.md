---
phase: 248
plan: 08
status: complete
report_commit: 7ed12276c
---

# 248-08 Summary: prod calibration report and spot-check

## Task 1: read-only prod run

- Preconditions: 248-07 pct_scored 99.823, 247-07 pct_scored 99.570, no backfill process alive, onnxruntime 1.29.0.
- Run 13:37:25 to 13:51:35 UTC (14 min), detached, EXIT=0: 26,529 sampled games at 25 permille, 22,424 per-user
  groups, 9,000 Good moves scored with Maia (0 not scorable). pg_stat_activity went from 20 to 21 (one connection).
- Cache `temp/blunder-check/prod-cache-2026-11-10.json` (70 MB, gitignored), exploratory report in temp/blunder-check/.
- **Control agreement: 191,633 of 191,741 = 99.9%**, so no investigation was needed.
- Sample per bucket (user-side rated non-guest blunders): <800 7,027; 800-1199 10,354; 1200-1599 14,690;
  1600-1999 16,409; 2000-2399 7,866; 2400+ 1,601; all 57,947 (26,477 games, 79 guest excluded, 52 skipped for a ply gap).
- Arrow-oddness AUC, drill at the chosen values against unselected: overall 0.791 vs 0.772 (+0.019). Exploratory run at
  R = X' = 0.2, drill AUC per bucket: <800 0.776, 800-1199 0.775, 1200-1599 0.787, 1600-1999 0.793, 2000-2399 0.811,
  2400+ 0.783.

## Task 2: recommended constants

- **R = 0.3, X' = 0.2, eval band [0.10, 0.90]** (recommendation only, D-18). The rationale is in the report under
  "Recommended constants".
- Re-rendered from the cache to compare: R=0.2/X'=0.2 median 986 blunder windows, 42 users under 50, AUC gap +0.018;
  R=0.3/X'=0.2 median 927, 43 under 50, +0.019; R=0.3/X'=0.3 median 897, 43 under 50, +0.024.
- Final render: `reports/blunder-check/blunder-check-calibration-2026-11-10.md` plus
  `reports/blunder-check/spot-check-2026-11-10.md` (120 windows, 20 per bucket, 35 herrings, about 29%).
- Sanity read (7 windows: <800 W2, W4, W5 and W7; 1600-1999 W2 and W3; 2400+ W1). The hung-queen cases (<800 W5
  4.Qd5?? Nxd5, 1600-1999 W2 7...Qxd4?? Nxd4) read as true face-palms. 1600-1999 W3 (16...Kf7, refutation c4) is
  positional/indirect even at Maia probability 0.72: the kind of window the owner should judge. 2400+ W1 is a pure
  miss at pre-move ES 0.84 (Rg1+ missed, Maia 0.97). No user ids or usernames appear (game links only).
  Cosmetic: a window with the blunder at position 1 prints an empty "Judged user moves:" list.
- D-19: `git show --name-only 7ed12276c` lists only the two reports/blunder-check/ files. No constant is wired into app/
  or frontend/.
