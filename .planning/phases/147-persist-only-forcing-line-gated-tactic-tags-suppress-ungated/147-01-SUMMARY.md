---
phase: 147-persist-only-forcing-line-gated-tactic-tags-suppress-ungated
plan: 01
subsystem: api
tags: [tactic-detection, forcing-line-gate, eval-remote, flaws-service, tdd]

requires:
  - phase: 146-offload-live-submit-forcing-line-continuation-eval-to-remote-worker
    provides: blob_map={} unconditional at _apply_submit (D-03), tier-4 flaw-blob-lease/submit pipeline
provides:
  - blobs_pending threaded through classify_game_flaws -> _build_flaw_record -> _classify_tactic_gated (independent, default False parameter)
  - suppression branch in _classify_tactic_gated (blobs_pending AND motif AND pv_blob is None AND pre_flaw_eval_cp is not None -> NULL)
  - _apply_submit passes blobs_pending=True, closing the ungated-tag window at the go-forward write site
affects: [147-02, 147-03, 147-04, 147-05, 147-06]

tech-stack:
  added: []
  patterns:
    - "Independent boolean signal threaded through a pure classify pipeline (never derived from a sibling parameter) to change behavior only at one call site"
    - "Monkeypatch _detect_tactic_for_flaw at the flaws_service module level to get a deterministic motif through the real gate logic (mirrors TestPreFlawEvalParity._patch_detector)"

key-files:
  created: []
  modified:
    - app/services/flaws_service.py
    - app/services/eval_drain.py
    - app/routers/eval_remote.py
    - tests/services/test_flaws_service.py
    - tests/test_eval_worker_endpoints.py

key-decisions:
  - "blobs_pending is a real default-False kwarg on all four functions, never derived from flaw_pv_blobs/pv_blob truthiness (Pitfall 1)"
  - "Suppression predicate uses `pv_blob is None` (not falsy) so the D-06 []-sentinel is never re-suppressed"
  - "Mate-adjacent (pre_flaw_eval_cp is None) and D-06 []-sentinel flaws are FINAL cases that always keep their raw tag, even under blobs_pending=True"
  - "_full_drain_tick and _build_flaw_multipv2_blobs classify calls are untouched (default False) — local drain output is unchanged (D-05)"

requirements-completed: [SEED-074]

coverage:
  - id: D1
    description: "cp-based flaw with deferred blob submitted through the remote path persists NULL tactic tags instead of the raw motif"
    requirement: "SEED-074"
    verification:
      - kind: unit
        ref: "tests/services/test_flaws_service.py::TestClassifyTacticGatedBlobsPending::test_blobs_pending_true_cp_flaw_no_blob_suppresses"
        status: pass
      - kind: integration
        ref: "tests/test_eval_worker_endpoints.py::test_submit_suppresses_cp_flaw_tag_then_blob_submit_self_heals"
        status: pass
    human_judgment: false
  - id: D2
    description: "Mate-adjacent and D-06 []-sentinel flaws are FINAL cases and keep their raw tag under blobs_pending=True"
    requirement: "SEED-074"
    verification:
      - kind: unit
        ref: "tests/services/test_flaws_service.py::TestClassifyTacticGatedBlobsPending::test_blobs_pending_true_mate_adjacent_keeps_raw"
        status: pass
      - kind: unit
        ref: "tests/services/test_flaws_service.py::TestClassifyTacticGatedBlobsPending::test_blobs_pending_true_sentinel_empty_blob_keeps_raw"
        status: pass
    human_judgment: false
  - id: D3
    description: "A subsequent /flaw-blob-submit (existing D-07 gated retag) fills the correctly-gated tag on a previously-suppressed flaw (self-heal)"
    requirement: "SEED-074"
    verification:
      - kind: integration
        ref: "tests/test_eval_worker_endpoints.py::test_submit_suppresses_cp_flaw_tag_then_blob_submit_self_heals"
        status: pass
    human_judgment: false
  - id: D4
    description: "Local drain (_full_drain_tick) and discovery-only classify (_build_flaw_multipv2_blobs) are unaffected — default blobs_pending=False preserved"
    requirement: "SEED-074"
    verification:
      - kind: unit
        ref: "tests/services/test_flaws_service.py::TestClassifyTacticGatedBlobsPending::test_blobs_pending_false_default_cp_flaw_no_blob_keeps_raw"
        status: pass
      - kind: other
        ref: "uv run ty check app/ tests/ (zero errors) + uv run pytest -n auto (3077 passed, full backend suite)"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-07-01
status: complete
---

# Phase 147 Plan 01: Thread blobs_pending suppression signal + close the go-forward gap Summary

**Threads an independent `blobs_pending: bool = False` signal through the classify pipeline (`classify_game_flaws` → `_build_flaw_record` → `_classify_tactic_gated`, plus `eval_drain._classify_and_fill_oracle`) and sets it `True` at `_apply_submit`, so a remote-submit cp-based flaw with a deferred continuation blob persists NULL tactic tags instead of the raw ungated motif, self-healing via the existing tier-4 D-07 gated retag.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-07-01T20:42Z
- **Completed:** 2026-07-01T21:00Z
- **Tasks:** 2 completed
- **Files modified:** 4 (app/services/flaws_service.py, app/services/eval_drain.py, app/routers/eval_remote.py, tests/services/test_flaws_service.py, tests/test_eval_worker_endpoints.py — 5 total)

## Accomplishments

- `blobs_pending: bool = False` added as an independent, explicitly-passed parameter (never derived from `flaw_pv_blobs`/`pv_blob`) to `classify_game_flaws`, `_build_flaw_record`, `_classify_tactic_gated` (flaws_service.py) and `_classify_and_fill_oracle` (eval_drain.py); forwarded per-orientation from `_build_flaw_record`'s two `_classify_tactic_gated` calls (allowed and missed).
- New suppression branch in `_classify_tactic_gated`: when `blobs_pending` AND a motif was detected AND `pv_blob is None` AND `pre_flaw_eval_cp is not None`, returns `(None, None, None, None)` — the cp-based flaw's tag is suppressed rather than persisted ungated. Uses `pv_blob is None` (not falsy) so the D-06 `[]`-sentinel is never re-suppressed. Mate-adjacent (`pre_flaw_eval_cp is None`) and `[]`-sentinel flaws fall through unchanged (FINAL cases, D-06 KEEP rule).
- `_apply_submit` (eval_remote.py) now passes `blobs_pending=True` to `_classify_and_fill_oracle`, closing the ungated-tag window at the go-forward write site. `blob_map` argument behavior is unchanged (Phase 146 D-03: always `{}` on this path).
- `_full_drain_tick` (line ~2549) and the discovery-only classify in `_build_flaw_multipv2_blobs` (line ~1200) are untouched — both keep the default `blobs_pending=False`, so local drain / discovery output is unchanged (D-05, Pitfall 1).
- Unit tests directly exercise all four `_classify_tactic_gated` carve-outs (suppress / mate-adjacent KEEP / `[]`-sentinel KEEP / `blobs_pending=False` default KEEP).
- A new router test (`test_submit_suppresses_cp_flaw_tag_then_blob_submit_self_heals`) drives the full flow end to end through real HTTP endpoints: `/submit` → NULL tags + both completion markers stamped → `/flaw-blob-submit` (existing D-07 gated retag, unmodified) → tag filled with the real gated result.

## Task Commits

Each task was committed atomically:

1. **Task 1: Thread blobs_pending through the classify pipeline and add the suppression branch** — `cd7a50fc` (feat)
2. **Task 2: Set blobs_pending=True at _apply_submit and add unit + router tests** — `bb1d17dd` (feat)

**Plan metadata:** pending (docs: complete plan — committed after this SUMMARY)

## Files Created/Modified

- `app/services/flaws_service.py` — `blobs_pending` kwarg + suppression branch on `_classify_tactic_gated`; forwarded through `_build_flaw_record` (both orientations) and `classify_game_flaws`.
- `app/services/eval_drain.py` — `blobs_pending` kwarg on `_classify_and_fill_oracle`, forwarded into its `classify_game_flaws` call. `_full_drain_tick` and `_build_flaw_multipv2_blobs` call sites left untouched (default False).
- `app/routers/eval_remote.py` — `_apply_submit` passes `blobs_pending=True` to `_classify_and_fill_oracle`; updated the surrounding comment.
- `tests/services/test_flaws_service.py` — new `TestClassifyTacticGatedBlobsPending` class (4 tests: suppress, mate-adjacent KEEP, `[]`-sentinel KEEP, default-False KEEP).
- `tests/test_eval_worker_endpoints.py` — new end-to-end router test proving submit-suppress-then-blob-submit-self-heal; existing `test_apply_submit_passes_none_to_classify` spy signature updated to accept the new `blobs_pending` kwarg (Deviation, see below).

## Decisions Made

- `blobs_pending` is a real default-False keyword parameter on all four functions, never derived from `flaw_pv_blobs is None` (per the plan's explicit prohibition and Pitfall 1).
- The suppression predicate uses `pv_blob is None`, not truthiness, so the D-06 `[]`-sentinel (an un-fillable blob) is never re-suppressed — it's a FINAL case per the existing D-06 KEEP rule.
- Mate-adjacent flaws (`pre_flaw_eval_cp is None`) have no cp value to gate-check against even once a blob eventually lands, so they are excluded from the suppression condition entirely (FINAL case).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed a spy-test signature break caused by the new `_classify_and_fill_oracle` kwarg**
- **Found during:** Task 2 verification (`uv run pytest tests/test_eval_worker_endpoints.py -k "phase146 or apply_submit_passes_none"`)
- **Issue:** `test_apply_submit_passes_none_to_classify` monkeypatches `_classify_and_fill_oracle` with a `spy_classify(session, game_id, engine_result_map, flaw_pv_blobs=None)` stub that forwards to the original. Once `_apply_submit` started passing `blobs_pending=True`, the stub raised `TypeError: got an unexpected keyword argument 'blobs_pending'`.
- **Fix:** Added `blobs_pending=False` to the spy's signature and forwarded it to the wrapped original call.
- **Files modified:** `tests/test_eval_worker_endpoints.py`
- **Verification:** `uv run pytest tests/test_eval_worker_endpoints.py -k "phase146 or apply_submit_passes_none"` — 4 passed.
- **Committed in:** `bb1d17dd` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - blocking test regression caused directly by this plan's own change)
**Impact on plan:** Necessary to keep the existing Phase 146 spy test green after adding the new parameter. No scope creep — no other call sites of `_classify_and_fill_oracle` needed changes (confirmed via grep: only `_apply_submit` and `_full_drain_tick` call it).

## Issues Encountered

None beyond the deviation above. `ruff format` reformatted both touched source files after the initial edits (pre-existing formatting drift plus the new code); re-ran the full targeted test + ty + ruff suite after formatting to confirm no regressions.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The go-forward suppression path (D-01, D-03) is live at `_apply_submit`; `147-02`+ can build on this without re-deriving the pipeline threading.
- Full backend suite (3077 passed, 18 skipped) green after this plan, confirming no blast radius beyond the touched files.
- `uv run ty check app/ tests/` and `uv run ruff check app/ tests/` both pass with zero errors.

---
*Phase: 147-persist-only-forcing-line-gated-tactic-tags-suppress-ungated*
*Completed: 2026-07-01*
