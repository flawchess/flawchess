---
phase: 259
source: 259-REVIEW.md
updated: 2026-11-22
---

# Phase 259 Review Disposition

| Finding | Severity | Disposition | Note |
|---------|----------|-------------|------|
| WR-01 | warning | fixed | `miss_labels` buckets a miss on the stored gain when depth 3 has none (`_candidate_missed`), with a regression test |
| WR-02 | warning | fixed | `facepalm_features._has_null_score_input` reads the inputs the scalar score reads, with a regression test |
| WR-03 | warning | open | Unused generality: `depth_3` / `first_stable` material inputs, `aggregate`, `loss_feature`, `missed_feature`; only `decaying_mean` is ever used. App-code refactor after the release, left for the owner to schedule |
| IN-01 | info | open | Docstrings in `facepalm_material.py` and `line_material.py` still describe the dropped Postgres arrays |
| IN-02 | info | fixed | `sample.py` comment now documents cache version 6 |
