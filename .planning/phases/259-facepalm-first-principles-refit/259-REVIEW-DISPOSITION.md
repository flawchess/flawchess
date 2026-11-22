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
| WR-03 | warning | fixed | Collapsed to the one stored rule: `material_loss` / `material_missed` always take the decaying mean; `first_stable`, `aggregate`, `loss_feature`, `missed_feature` and `MaterialInput` deleted. Stored values of all 291 label rows recompute unchanged |
| IN-01 | info | fixed | Docstrings in `facepalm_material.py` and `line_material.py` and the calibration report text in `render.py` describe the scalars, not the dropped arrays |
| IN-02 | info | fixed | `sample.py` comment now documents cache version 6 |
