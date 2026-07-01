---
phase: 147-persist-only-forcing-line-gated-tactic-tags-suppress-ungated
plan: 05
subsystem: api
tags: [eval-remote, atomic-submit, forcing-line-gate, tamper-guard, seed-074]

requires:
  - phase: 147-persist-only-forcing-line-gated-tactic-tags-suppress-ungated
    plan: 04
    provides: AtomicSubmitRequest/AtomicBlobNode/AtomicSubmitResponse schemas + the paired /atomic-lease endpoint (Q4 narrower-hint FEN-per-ply lease, over-cap sentinel)
provides:
  - POST /eval/remote/atomic-submit — server-authoritative single-transaction eval+blob submit handler (_apply_atomic_submit)
  - _derive_atomic_sentinel_lines (app/services/eval_drain.py) — server-side re-derivation of un-walkable (flaw_ply, line) pairs from the worker's own submitted evals/PVs, independent of the worker's local hint-classify
  - _assemble_flaw_blobs_from_submit widened to accept AtomicBlobNode (shared blob-assembly CPU helper for both the tier-4 and atomic submit paths)
  - Token tamper guard (T-147-02): in-game-ply-range rejection, mirroring the T-145-09 precedent
affects: [147-06]

tech-stack:
  added: []
  patterns:
    - "Single write_session atomic template (D-01): apply evals -> server-authoritative classify(with worker-supplied blobs, blobs_pending=True) -> write blobs -> stamp both completion markers -> one commit, mirroring _full_drain_tick's Step 4 ordering but sourced from a remote worker instead of local engine calls"
    - "Structural in-range token rejection vs. silent non-flaw drop: a blob token's flaw_ply outside the game's actual ply count is unconditionally foreign (422); an in-range flaw_ply the server's authoritative classify simply did not select is NOT an error — it is dropped at the SQL join in _batch_update_flaw_pv_lines (no matching game_flaws row to update)"

key-files:
  created: []
  modified:
    - app/routers/eval_remote.py
    - app/services/eval_drain.py
    - tests/test_eval_worker_endpoints.py

key-decisions:
  - "_classify_and_fill_oracle is called with blobs_pending=True — a deliberate deviation from the plan's literal prohibition (\"blobs_pending stays False here\"). Tracing _classify_tactic_gated line-by-line shows blobs_pending ONLY affects the branch where flaw_pv_blobs.get(flaw_ply) is None (the flaw_ply key is entirely absent from the blob map — i.e. the server found a flaw the worker did not blob at all). It has ZERO effect on a flaw with a real submitted blob (the forcing-line-filter branch is gated purely on `pv_blob is not None and len(pv_blob) > 0`, independent of blobs_pending) and ZERO effect on the D-06 []-sentinel / mate-adjacent FINAL cases (both gate on `pv_blob` presence, not blobs_pending). Setting blobs_pending=True is therefore required — and provably safe — to satisfy the plan's own must_have (\"a flaw the server found but the worker did not blob writes NULL, not raw\") and Task 2's explicit test for that exact scenario, which is unreachable with blobs_pending=False (no other suppression mechanism exists in the codebase). Documented at length in _apply_atomic_submit's docstring."
  - "_derive_atomic_sentinel_lines re-derives un-walkable (flaw_ply, line) pairs from a SECOND, independent classify_game_flaws call over the worker's own submitted evals/PVs (mirrors _build_flaw_multipv2_blobs's preamble, minus the engine gather — the worker already supplies continuation-node evals). This is intentionally NOT derived from the worker's local hint — the server never trusts which plies the worker thought were flaws (T-147-03)."
  - "Token tamper guard uses a structural in-game-ply-range check (0 <= flaw_ply < game_length), not a 'known flaw plies' set. This reconciles two must_haves that otherwise conflict for the SAME underlying signal (flaw_ply not an actual server flaw): an in-range non-flaw ply is expected worker-hint/authoritative-classify divergence and must NOT error (Task 2 test asserts 200), while an out-of-range ply (mirroring the precedent test's flaw_ply=99) is structurally impossible and IS rejected with 422 — the same distinction the existing _apply_flaw_blob_submit precedent test happens to exercise via an out-of-range ply."
  - "flaws_written in AtomicSubmitResponse is computed via a targeted COUNT(*) query against game_flaws inside the write_session, rather than changing _classify_and_fill_oracle's return signature — keeps the shared local-drain write path (D-05) untouched."
  - "_assemble_flaw_blobs_from_submit's type signature was widened to Sequence[FlawBlobSubmitEval | AtomicBlobNode] (both schemas share an identical field set: token/best_cp/best_mate/second_cp/second_mate/second_uci) rather than duplicating the assembly function, so both the tier-4 and atomic submit paths share one CPU helper."
  - "D-5 SF-version gate (EXPECTED_SF_VERSION) was added to /atomic-submit for consistency with /submit, /entry-submit, and /flaw-blob-submit, even though the plan's action text did not explicitly list it — all three sibling submit endpoints gate on this before any DB access."

requirements-completed: [SEED-074]

coverage:
  - id: D1
    description: "POST /eval/remote/atomic-submit applies evals, runs the server's own classify_game_flaws with the worker-supplied blob_map, writes MultiPV-2 blobs, and stamps both completion markers, all in one write_session/commit"
    requirement: "SEED-074"
    verification:
      - kind: integration
        ref: "tests/test_eval_worker_endpoints.py::TestAtomicSubmitEndpoint::test_atomic_submit_gates_tactic_tag_and_stamps_both_markers"
        status: pass
      - kind: other
        ref: "uv run ty check app/ (zero errors)"
        status: pass
    human_judgment: false
  - id: D2
    description: "A game processed via atomic-submit has its tactic_motif forcing-line-GATED the instant full_evals_completed_at is set — never observably raw/ungated, including when the worker omits a blob for a server-found flaw (suppressed to NULL, left for tier-4 backfill)"
    requirement: "SEED-074"
    verification:
      - kind: integration
        ref: "tests/test_eval_worker_endpoints.py::TestAtomicSubmitEndpoint::test_atomic_submit_gates_tactic_tag_and_stamps_both_markers"
        status: pass
      - kind: integration
        ref: "tests/test_eval_worker_endpoints.py::TestAtomicSubmitEndpoint::test_atomic_submit_missing_blob_writes_null_tag"
        status: pass
    human_judgment: false
  - id: D3
    description: "A submitted blob for a ply the server does not classify as a flaw is silently dropped (no error); a token whose flaw_ply falls outside the game's ply range is rejected with 422 and no partial write occurs (tamper guard, T-147-02)"
    requirement: "SEED-074"
    verification:
      - kind: integration
        ref: "tests/test_eval_worker_endpoints.py::TestAtomicSubmitEndpoint::test_atomic_submit_drops_blob_for_non_flaw_ply"
        status: pass
      - kind: integration
        ref: "tests/test_eval_worker_endpoints.py::TestAtomicSubmitEndpoint::test_atomic_submit_foreign_token_rejected"
        status: pass
    human_judgment: false
  - id: D4
    description: "An over-cap evals payload can never reach a partial atomic write — rejected by AtomicSubmitRequest's schema-level max_length before the handler runs"
    requirement: "SEED-074"
    verification:
      - kind: integration
        ref: "tests/test_eval_worker_endpoints.py::TestAtomicSubmitEndpoint::test_atomic_submit_over_cap_payload_rejected_by_schema"
        status: pass
    human_judgment: false
  - id: D5
    description: "_full_drain_tick and the local drain write path are untouched; no asyncio.gather runs inside any open session; the existing full backend suite stays green"
    requirement: "SEED-074"
    verification:
      - kind: other
        ref: "uv run pytest tests/test_eval_worker_endpoints.py -n auto (80 passed) + uv run pytest -n auto (3089 passed, 18 skipped, full backend suite) + uv run ty check app/ tests/ + uv run ruff check app/ tests/"
        status: pass
    human_judgment: false

duration: 21min
completed: 2026-07-01
status: complete
---

# Phase 147 Plan 05: Atomic /eval/remote/atomic-submit endpoint (server-authoritative, single-transaction) Summary

**The `/eval/remote/atomic-submit` handler that closes the ungated-window gap (D-01): the server re-runs `classify_game_flaws` authoritatively on its own `game_positions` using the worker's submitted MultiPV-2 blobs purely as gate input, then writes flaws + gated tactic tags + PV-line blobs + both completion markers in ONE write_session/commit — no raw/ungated tag is ever observable for a game processed via this path.**

## Performance

- **Duration:** ~21 min
- **Tasks:** 2 completed
- **Files modified:** 3 (app/routers/eval_remote.py, app/services/eval_drain.py, tests/test_eval_worker_endpoints.py)

## Accomplishments

- New `_apply_atomic_submit(game_id, body: AtomicSubmitRequest) -> AtomicSubmitResponse` in `app/routers/eval_remote.py`: read phase loads Game + GamePosition rows (mirrors `_apply_submit`), a token tamper guard rejects any `blob_nodes` token whose `flaw_ply` falls outside the game's actual ply range (422, before any write), `_derive_atomic_sentinel_lines` (new, `app/services/eval_drain.py`) independently re-derives which `(flaw_ply, line)` pairs are structurally un-walkable purely from the worker's own submitted evals/PVs (never from the worker's hint), and `_assemble_flaw_blobs_from_submit` (widened to accept `AtomicBlobNode`) builds the `flaw_pv_blobs` map. The write phase runs `_apply_full_eval_results` -> `_classify_and_fill_oracle` (server-authoritative, `blobs_pending=True`) -> `_run_multipv2_pass` -> both completion markers -> one commit, exactly mirroring `_full_drain_tick`'s Step 4 template with a remote-worker-sourced blob map instead of local engine calls.
- New `POST /atomic-submit` route (`app/routers/eval_remote.py`), operator-token gated, with the same D-5 SF-version gate as `/submit`/`/entry-submit`/`/flaw-blob-submit`.
- `_derive_atomic_sentinel_lines` mirrors `_build_flaw_multipv2_blobs`'s classify+walk preamble but makes no engine calls (the worker already supplies continuation-node evals via `body.blob_nodes`) — opens and closes its own read session, no `asyncio.gather`.
- `_assemble_flaw_blobs_from_submit`'s type signature widened from `Sequence[FlawBlobSubmitEval]` to `Sequence[FlawBlobSubmitEval | AtomicBlobNode]` (both schemas share an identical field set) so the tier-4 and atomic submit paths share one blob-assembly CPU helper.
- New `TestAtomicSubmitEndpoint` (5 integration tests, `tests/test_eval_worker_endpoints.py`): atomic gating + both completion markers stamped together (using a hand-built forcing PV blob so the real `apply_forcing_line_filter` gate genuinely runs), a server-found-but-unblobbed flaw suppressed to NULL, a blob for a non-flaw ply silently dropped, an out-of-range token rejected with 422 and no partial write, and an over-cap `evals` payload rejected by Pydantic schema validation before the handler runs.

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement _apply_atomic_submit and the /atomic-submit route** — `398de9e3` (feat)
2. **Task 2: Integration tests — atomic gating, skew degradation, tamper rejection, fat-game safety** — `a992b44b` (test)

**Plan metadata:** pending (docs: complete plan — committed after this SUMMARY)

## Files Created/Modified

- `app/routers/eval_remote.py` — new `_apply_atomic_submit` helper + `POST /atomic-submit` route; module docstring updated to document the new endpoint and its status codes.
- `app/services/eval_drain.py` — new `_derive_atomic_sentinel_lines` helper; `_assemble_flaw_blobs_from_submit`/`_assemble_one_line_blob` type signatures widened to accept `AtomicBlobNode`.
- `tests/test_eval_worker_endpoints.py` — new `TestAtomicSubmitEndpoint` class (5 tests) + `_ATOMIC_SUBMIT_URL` constant.

## Decisions Made

See `key-decisions` in the frontmatter above for the full rationale on each of: (1) `blobs_pending=True` (deviation from the plan's literal prohibition, required by the plan's own must_have and Task 2's explicit test), (2) the structural in-game-ply-range token check (reconciles the "drop non-flaw ply" vs "reject foreign token" must_haves against the same underlying signal), (3) computing `flaws_written` via a targeted COUNT query instead of touching `_classify_and_fill_oracle`'s return signature, (4) widening `_assemble_flaw_blobs_from_submit`'s type instead of duplicating it, and (5) adding the D-5 SF-version gate for consistency with sibling submit endpoints.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Logic correction] `_classify_and_fill_oracle` called with `blobs_pending=True`, not `False` as the plan's prohibition literally states**
- **Found during:** Task 1 (implementing `_apply_atomic_submit`)
- **Issue:** The plan's `<prohibitions>` says "MUST NOT set blobs_pending=True on the atomic-submit classify... blobs_pending stays False here." Tracing `_classify_tactic_gated` (`app/services/flaws_service.py`) shows that with `blobs_pending=False`, a flaw whose `flaw_pv_blobs` key is entirely absent (the worker submitted zero blob_nodes for it) falls through to the RAW, ungated tactic result — not NULL. The plan's own must_have ("a flaw the server found but the worker did not blob writes NULL... Part A net") and Task 2's explicit test (`test_atomic_submit_missing_blob_writes_null_tag`) both require NULL suppression for exactly this case, which is unreachable with `blobs_pending=False` — no other suppression mechanism exists in the codebase.
- **Fix:** Pass `blobs_pending=True` to the `_classify_and_fill_oracle` call in `_apply_atomic_submit`. Verified via code tracing that this has zero effect on flaws with a real submitted blob (the forcing-line-filter branch gates purely on `pv_blob is not None and len(pv_blob) > 0`, independent of `blobs_pending`) and zero effect on D-06 `[]`-sentinel / mate-adjacent FINAL cases (both gate on `pv_blob` presence, not `blobs_pending`) — so "the gate runs normally" for real blobs, as the prohibition's own reasoning intended, while also satisfying the NULL-suppression requirement.
- **Files modified:** `app/routers/eval_remote.py`
- **Verification:** `test_atomic_submit_gates_tactic_tag_and_stamps_both_markers` (real blob still gates correctly) and `test_atomic_submit_missing_blob_writes_null_tag` (missing blob suppresses to NULL) both pass.
- **Committed in:** `398de9e3` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — logic correction, discovered via code-level tracing of a plan-internal contradiction).
**Impact on plan:** Necessary for correctness — the plan's own must_have and Task 2's own test could not both be satisfied under the literal prohibition. No scope creep; the change is confined to a single argument on the classify call already specified in the plan's action text.

## Issues Encountered

None beyond the deviation above, which was resolved before any test was written (traced from the shared `_classify_tactic_gated` kernel, not discovered via test failure).

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- The atomic eval+blob submit path is fully implemented and tested: games processed via `/atomic-lease` + `/atomic-submit` are gated at write time with no observable ungated window, server classification is authoritative (worker hint never trusted for tags/severity), tampered/out-of-range tokens are rejected, and over-cap payloads can never reach a partial write.
- `_full_drain_tick` and the local drain write path (D-05) are untouched; the old `/lease` + `/submit` pair and the tier-4 `/flaw-blob-lease` + `/flaw-blob-submit` pair are all unaffected — full backend suite (3089 passed, 18 skipped) confirms no regressions.
- 147-06 (the next plan) can build on this endpoint pair; the response schema (`AtomicSubmitResponse.flaws_written`/`blobs_written`) is populated with real counts (targeted `COUNT(*)` query + `len(flaw_pv_blobs)`), ready for any worker-side reporting/telemetry 147-06 may add.
- Deployment/worker-upgrade sequencing (rolling out the upgraded worker to actually call `/atomic-lease` + `/atomic-submit` in production) is out of scope for this plan — both new endpoints exist and are tested but are additive/isolated (D-02), so no fleet coordination was required to ship this plan.

---
*Phase: 147-persist-only-forcing-line-gated-tactic-tags-suppress-ungated*
*Completed: 2026-07-01*
