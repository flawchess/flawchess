---
phase: 260-facepalm-first-class-move-quality
review: 260-REVIEW.md
recorded: 2026-11-22
findings: 8
fixed: 6
open: 2
---

# Phase 260 review disposition

| Finding | Severity | Disposition | Commit | Note |
|---------|----------|-------------|--------|------|
| WR-01 | warning | fixed | b65a84714, 3b05ba0f0 | A full severity selection (all three tags) is treated like no tag at the shared game filter and the clause builder (D-08). Revert-checked: 4 tests fail without it. |
| WR-02 | warning | fixed | 780acf96f | Chip score / severity clause agreement pin and the user_id ValueError guard pin restored. |
| IN-01 | info | open (owner) | - | An old `?severity=blunder` URL or a cached bundle with both old tiers selected now excludes facepalms. Intended by D-09; owner decides whether a hint or changelog sentence is wanted. |
| IN-02 | info | fixed | 661c881c6 | Stale comments corrected. |
| IN-03 | info | fixed | 5b5963001 | Board badge and Explain bar call `flawMoveCategory`. |
| IN-04 | info | open (UAT) | - | Desktop card geometry constants need a real-browser measurement (D-15, D-16, D-25). |
| IN-05 | info | fixed | e0fa14445 | Facepalm fill, swatch and pill background derive from one oklch source. |
| IN-06 | info | fixed | de3e6e252 | Parity test reads the frontend cut (D-21). |

Gates after the fixes: backend `pytest -n auto` 6869 passed / 8 skipped, ruff, ty, function-size gate, frontend lint, build, tests and knip all exit 0.
