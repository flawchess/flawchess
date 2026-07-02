---
quick_id: 260702-lml
title: "Implement SEED-075: fix local eval drain re-minting ungated cp-based tactic tags"
date: 2026-07-02
status: complete
---

# Quick Task 260702-lml: Fix local eval drain re-minting ungated cp-based tactic tags

## Problem

SEED-075. Phase 147 established the strict-zero invariant "no ungated cp-based tactic
tag is ever persisted." One producer was never converted: the local in-process eval
drain. `app/services/eval_drain.py:2642` called `_classify_and_fill_oracle(...)` without
`blobs_pending`, so it defaulted to `False`. For any flaw with `eval_cp` present but no
continuation blob assembled into `flaw_pv_blobs` this pass, the suppression branch in
`flaws_service._classify_tactic_gated` (`:583`) never fired and the raw cp-based motif was
persisted ungated. Verified on prod 2026-07-02: 75 such rows (44 allowed + 31 missed),
growing (was ~9 on 2026-07-01), because live analysis mints faster than the tier-4 drain.

## Fix (SEED Candidate 1 — pass the correct signal)

Pass `blobs_pending=True` at the local drain call site, mirroring the atomic go-forward
path (`eval_remote.py` `_apply_submit` `:312` and the worker blob-submit `:1254`, both
already `True`). This suppresses the raw tag to NULL for any flaw whose blob wasn't
assembled this pass; the tier-4 D-07 gated retag later lands the real blob and re-tags.

Confirmed safe / correct:
- Only affects flaws where `pv_blob is None` AND `pre_flaw_eval_cp is not None`
  (the leak). Flaws that DID get a blob run the forcing-line gate unchanged.
- D-06 `[]`-sentinel and mate-adjacent (`eval_cp IS NULL`) FINAL cases are never
  suppressed by this branch.
- `_build_flaw_multipv2_blobs` at the drain site always returns a dict (never None), so
  there is no "old game, blobs None → suppress everything" over-suppression risk.

## Tasks

1. `app/services/eval_drain.py:2642` — pass `blobs_pending=True` to
   `_classify_and_fill_oracle`; add a comment explaining the SEED-075 bug fix.
2. `tests/services/test_full_eval_drain.py` — add
   `TestLocalDrainBlobsPendingSuppression::test_drain_suppresses_cp_flaw_tag_with_no_blob`,
   mirroring the atomic-submit suppression test: blunder at ply 2 (cp-based pre-flaw
   eval), fixed HANGING_PIECE motif on "allowed", `_build_flaw_multipv2_blobs` stubbed to
   `{}` (no blob), assert `allowed_tactic_motif IS NULL` after the drain tick. Verified
   the test fails with the pre-fix default (`blobs_pending=False`).

## Verification

- `uv run ruff format` / `ruff check` / `ty check` — clean.
- `tests/services/test_full_eval_drain.py`, `test_flaws_service.py`,
  `test_eval_worker_endpoints.py` — 262 passed.
- Full backend suite — green.
- Prod (out of band, needs `bin/prod_db_tunnel.sh`): the go-forward ungated count should
  stop climbing; the existing 75 drain toward 0 via tier-4.

## Out of scope

- Candidate 2 (`[]` D-06 sentinel for genuinely un-walkable local-drain lines) — not
  needed for the strict-zero invariant; suppression + tier-4 self-heal is sufficient and
  aligns with Phase 147 intent.
- No DB schema change, no new endpoint, no migration.
