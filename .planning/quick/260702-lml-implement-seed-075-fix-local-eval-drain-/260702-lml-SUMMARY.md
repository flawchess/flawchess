---
quick_id: 260702-lml
title: "Implement SEED-075: fix local eval drain re-minting ungated cp-based tactic tags"
date: 2026-07-02
status: complete
---

# Summary — Quick Task 260702-lml

Closed SEED-075: the local in-process eval drain re-minted raw ungated cp-based tactic
tags, violating the Phase 147 strict-zero invariant (75 rows on prod, growing).

## What changed

- **`app/services/eval_drain.py`** (`_full_drain_tick`, ~line 2642): pass
  `blobs_pending=True` to `_classify_and_fill_oracle`, matching the atomic go-forward
  paths in `eval_remote.py`. A flaw with `eval_cp` present but no assembled continuation
  blob now has its motif suppressed to NULL (instead of persisted raw), and self-heals
  when the tier-4 D-07 gated retag lands the real blob. Added a comment documenting the
  bug per CLAUDE.md.
- **`tests/services/test_full_eval_drain.py`**: added
  `TestLocalDrainBlobsPendingSuppression::test_drain_suppresses_cp_flaw_tag_with_no_blob`,
  mirroring the atomic-submit suppression test. Confirmed it fails against the pre-fix
  default (`blobs_pending=False`) and passes with the fix.

## Why this is safe

`blobs_pending` only affects the branch `motif detected AND pv_blob is None AND
pre_flaw_eval_cp is not None`. Legitimately-blobbed flaws still run the forcing-line gate
unchanged; D-06 `[]`-sentinel and mate-adjacent (`eval_cp IS NULL`) FINAL cases are never
suppressed. `_build_flaw_multipv2_blobs` returns a dict (never None) at this call site, so
there is no over-suppression of "old" games.

## Verification

- ruff format / ruff check / ty check — clean.
- Targeted suites (`test_full_eval_drain`, `test_flaws_service`,
  `test_eval_worker_endpoints`) — 262 passed.
- Full backend suite — green.
- Prod drain-down (existing 75 → 0 via tier-4) is out-of-band; go-forward count should
  stop climbing immediately once deployed.

## Follow-ups

None required. Candidate 2 (`[]` sentinel for un-walkable local-drain lines) deliberately
skipped — suppression + tier-4 self-heal fully satisfies the invariant.
