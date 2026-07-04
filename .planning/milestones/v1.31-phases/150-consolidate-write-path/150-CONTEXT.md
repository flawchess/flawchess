# Phase 150: Consolidate Write Path - Context

**Gathered:** 2026-07-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Unify the copy-pasted eval write path into single shared code paths. Four seams, consolidated in dependency order (each step shrinks the next):

- **R1 / WRITE-01:** Path A/B/C completion decision + guarded `eval_jobs` stamp → one `apply_completion_decision(...)`, replacing 3 verbatim copies (`eval_drain.py` ×1, `eval_remote.py` ×2).
- **R4 / WRITE-02:** classify preamble (load positions + in-memory post-move overlay + classify once per tick) → one shared helper, replacing 4 repeated sites (`_flaw_engine_plies`, `_missing_flaw_pv_targets`, `_build_flaw_multipv2_blobs`, `_derive_atomic_sentinel_lines`).
- **R3 / WRITE-03:** `_classify_and_fill_oracle` replaces delete-then-insert with a per-ply diff/upsert; `_snapshot_preserved_flaw_blobs` / `_restore_preserved_flaw_blobs` are deleted; an old-vs-new equivalence test proves identical output. **The one medium-risk item — this is the authoritative write.**
- **R7 / WRITE-04:** shared submit/tick orchestration → new `app/services/eval_apply.py`; split `eval_drain.py` (entry lane / full lane / shared write path); router stops importing private drain helpers.
- **Ride-alongs:** **R5 / WRITE-05** (`EnginePool` one generic acquire/analyse/restart method, replacing 3 near-identical copies) and **R6 / WRITE-06** (parameterize the tier-3/tier-4 Efraimidis–Spirakis lottery into one implementation).

**Server-side only.** No worker protocol change, no fleet redeploy (fleet confirmed fully on atomic-lease/submit — Phase 149). **No behavior change** — the current (post-149, post-8D-fix) code IS the spec; this phase is a structure-only refactor.

**Out of scope** (per review §7 "not recommended" + SEED-080): merging entry/full lanes, changing the post-move convention, queue/broker rewrite, worker protocol changes, R14 tier-3 lease (deferred), SEED-078 streaming, a 426 version-rejection gate.
</domain>

<decisions>
## Implementation Decisions

The user selected the two **R3** gray areas to deep-dive (the risky authoritative-write rewrite). The other two areas (module split, ride-alongs + rollout) were explicitly delegated as sensible defaults — see "Claude's Discretion" below.

### R3 — Equivalence proof (DISCUSSED)

- **D-01 — Strategy: golden-snapshot.** Prove the new per-ply diff/upsert reproduces today's output by capturing the resulting `game_flaws` table state from **current HEAD** code against real fixtures, committing it as golden test data, then asserting the diff/upsert reproduces it byte-for-byte.
  - **Mitigation for the drift risk (user-accepted):** the golden MUST be generated from current HEAD (post-149, post-FLAWCHESS-8D-fix) — so it captures *correct* behavior, not the old snapshot/restore-era quirks. **Commit the generator script** (reproducible), so a reviewer can regenerate the golden and confirm it still matches HEAD before trusting the equivalence assertion. Golden data + generator live together.
  - Rejected alternatives: dual-run test-first (Claude's recommendation — truest de-risk, but user prefers the snapshot artifact); hand-authored matrix (weakest — encodes intended, not actual, behavior).

- **D-02 — Scenario matrix: FULL.** The equivalence test must cover every known incremental-retry case — these ARE the bug history the phase exists to close:
  1. Fresh full submit (all flaws new, all blobbed).
  2. Residual-hole retry — worker re-evals only the holes and does NOT re-blob already-done midgame flaws; their blobs + tactic tags must survive (SEED-076, the reason snapshot/restore exists).
  3. Borderline ply flips **OUT** of flaw status between submits — row must disappear, no StaleDataError (FLAWCHESS-8D).
  4. Borderline ply flips **IN** to flaw status.
  5. Entry-pass rows (NULL tactic columns) replaced by the full/oracle pass (the reason delete-then-insert was authoritative, not `ON CONFLICT DO NOTHING`).
  6. Opening dedup-transplanted plies — pv stays NULL, must not write a `[]`-sentinel that permanently taints the blob (quick 260703-qgp).
  7. `blobs_pending=True` suppression — cp-based flaw whose continuation blob is deferred to tier-4 is suppressed to NULL, not persisted raw/ungated (Phase 147 D-01/D-03).

### R3 — Blob/tag preservation semantics (DISCUSSED)

- **D-03 — Diff/upsert must natively reproduce snapshot/restore.** The whole point of R3 is to make blob preservation a property of the write, not a delete-then-restore compensation layer. Per ply in the freshly-classified desired flaw set:
  - **New ply** (not previously present) → insert; blob/tags from the submit if it carried them, else NULL (awaiting tier-4).
  - **Existing ply, submit carries a fresh blob** (ply ∈ the current `freshly_blobbed` signal) → overwrite blob + 8 tactic-tag columns with fresh values.
  - **Existing ply, submit did NOT re-blob it** → **preserve** the existing blob + tactic-tag columns (do not null them). This is what `_restore_preserved_flaw_blobs` achieves today.
  - **Previously-present ply no longer a flaw** → delete the row (this is the 8D case — must be a clean delete, never a 0-row bulk-update).
  - Keep the existing "fresh" signal (`freshly_blobbed` set derived from `_run_multipv2_pass`); the change is applying it inline in the upsert, not via snapshot → classify(delete-then-insert) → restore.

- **D-04 — Preserved-column set = single source of truth.** The 10 preserved columns (`allowed_pv_lines`, `missed_pv_lines` + the 8 `{allowed,missed}_tactic_{motif,piece,confidence,depth}` columns) are currently a hand-maintained literal duplicated in BOTH `_snapshot_preserved_flaw_blobs` and `_restore_preserved_flaw_blobs`. In the consolidated path, derive this set from **one** definition (a module-level `FLAW_BLOB_COLUMNS` constant or model introspection) so a future 11th tactic/blob column cannot be silently nulled by the upsert. This directly removes the "add a column, forget to preserve it" seam — the exact class of latent bug this phase targets.

### Claude's Discretion — delegated defaults (NOT deep-discussed)
The user delegated these as locked-by-requirements. Capture as researcher/planner guidance; **flag (don't silently override)** if research surfaces a reason to deviate.

- **D-05 — R7 module split:** New `app/services/eval_apply.py` exposing `apply_full_eval(...)` (the post-R1/R3/R4 `_apply_atomic_submit` body), consumed by BOTH `_full_drain_tick` and the router. Split `eval_drain.py` (currently 3013 lines) along the review's seam: entry lane / full lane / shared write path. Router (`eval_remote.py`) stops importing private drain helpers (it currently imports a block from `eval_drain.py` at line 81+) and returns to a thin HTTP layer per the router convention. Thin re-export shims only if a clean move is genuinely blocked — flag it, don't default to leaving the leak.
- **D-06 — R5/R6 ride-alongs:** Both firmly IN scope (small, and they shrink the surface). Planner MAY defer R6 (ES-lottery parameterization) to a follow-up if R3 balloons — but flag it, don't drop silently. R5 (EnginePool generic method) stays.
- **D-07 — Sequencing & rollout:** Execute in dependency order R1 → R4 → R3 → R7 (each shrinks the next); R5/R6 ride along. Single local squash-merge to `main` after the full pre-merge gate (backend ruff/ty/pytest + frontend). No incremental prod deploys between steps — this is a pure no-behavior-change refactor with no worker/schema change, so it ships as one release at the milestone boundary. Frontend is untouched (backend-only phase); the frontend gate should be a no-op but still run per the pre-merge gate.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone source & requirements
- `reports/reviews/pipeline-review-fable-2026-07-04.md` — the pipeline architecture review this whole milestone implements. **Write-path recommendations: R1 (line 242), R3 (246), R4 (248), R7 (256), R5/R6 ride-alongs, dependency chain note (289).** NOTE path drift: SEED-080/ROADMAP cite `reports/pipeline-review-2026-07-04.md`; the file actually lives at `reports/reviews/pipeline-review-fable-2026-07-04.md`.
- `.planning/seeds/SEED-080-pipeline-consolidation-milestone.md` — maps each WRITE requirement to a review recommendation (R1/R4/R3/R7/R5/R6) with pre-149 line-number breadcrumbs (note: line numbers predate Phase 149's deletions — re-locate symbols, don't trust exact lines).
- `.planning/REQUIREMENTS.md` (WRITE-01…06, lines 39-44) — the locked requirement text.
- `.planning/ROADMAP.md` §"Phase 150: Consolidate Write Path" (lines 167-180) — goal + 5 success criteria.
- `.planning/phases/149-retire-prune/149-CONTEXT.md` — immediate predecessor; confirms fleet-on-atomic + server-side-only scope this phase inherits.

### Bug history the R3 rewrite must not regress (from auto-memory + git)
- FLAWCHESS-8D (StaleDataError on `_restore_preserved_flaw_blobs` bulk-update-by-PK when a snapshotted ply drops out of flaw status) — fixed by intersecting snapshot with surviving plies; the diff/upsert must handle this natively (D-02 scenario 3).
- SEED-076 (incremental/cache-aware leasing → residual-hole retries; the reason snapshot/restore exists) — D-02 scenario 2.
- quick 260703-qgp (dedup transplants must carry pv via `engine_result_map`, else tier-4 writes a `[]`-sentinel that permanently taints the blob) — D-02 scenario 6.
- Phase 147 D-01/D-03 (`blobs_pending=True` suppresses ungated cp tags to NULL) — D-02 scenario 7.

### Source files touched
- `app/services/eval_drain.py` (3013 lines) — `_classify_and_fill_oracle` (705, delete-then-insert → diff/upsert, R3); classify-preamble sites `_flaw_engine_plies` (901), `_missing_flaw_pv_targets` (979), `_build_flaw_multipv2_blobs` (1216), `_derive_atomic_sentinel_lines` (1340) (R4); `apply_completion_decision` copy (R1); `_full_drain_tick` (R7 consumer). Target of the entry/full/shared-write split (R7).
- `app/routers/eval_remote.py` (1401 lines) — `_snapshot_preserved_flaw_blobs` (961) + `_restore_preserved_flaw_blobs` (1014) to DELETE (R3); `_apply_atomic_submit` (1060) body → `eval_apply.py` (R7); 2 completion-decision copies (R1); private-helper import block at line 81+ to remove (R7).
- `app/services/eval_apply.py` — NEW module (R7 target).
- `app/services/engine.py` (647 lines) — `EnginePool` 3 acquire/analyse/restart copies → one generic method (R5).
- `app/services/eval_queue_service.py` (864 lines) — tier-3/tier-4 ES lottery to parameterize (R6).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_apply_atomic_submit` (`eval_remote.py:1060`) is the canonical "evals → authoritative classify → blob write → both completion markers, one write_session" template (Phase 147 D-01/D-02). It already sequences the operations R7 will move wholesale into `apply_full_eval`.
- The `freshly_blobbed: set[int]` signal already flows into `_restore_preserved_flaw_blobs` — reuse it verbatim as the diff/upsert's "take fresh vs preserve" discriminator (D-03).
- `classify_game_flaws(...)` is already the single classify entry point; R4 unifies the *preamble* (load positions + overlay in-memory evals/PVs) that currently precedes it at 4 sites, not classify itself.

### Established Patterns
- `_classify_and_fill_oracle` runs inside the Step 4 write session so flaw rows, oracle counts, and PVs commit atomically with the evals (T-117-11). The diff/upsert MUST preserve this single-transaction property.
- DB errors in `bulk_insert_game_flaws` / oracle-count UPDATE intentionally propagate (WR-01) so the write transaction aborts and completion markers are NOT committed. The diff/upsert must keep the same fail-closed contract; only per-flaw PV writes stay individually fault-tolerant.
- Post-move off-by-one (D-117-02): row at ply N holds the eval of position N+1; pv for a flaw at ply N is written at ply N+1. Any preamble/write refactor must preserve this convention (out of scope to change it — review §7).
- CLAUDE.md: `AsyncSession` is never used concurrently; ty must pass zero errors; Sentry captures in non-trivial except blocks with variables in `set_context`, not the message.

### Integration Points
- The classify preamble's "overlay in-memory PVs (`engine_result_map`) before classify" step is load-bearing for live tactic tagging (260618-aiq) and sentinel derivation — R4's unified helper must thread `engine_result_map` / `flaw_pv_blobs` through unchanged.
- `apply_completion_decision` guards the `eval_jobs` stamp (Path A/B/C); R1 must keep the guard semantics identical across all 3 call sites (they differ only by a Sentry `source_tag` today).

</code_context>

<specifics>
## Specific Ideas

- The user chose golden-snapshot over dual-run despite the drift caveat; the accepted mitigation (generate from HEAD + commit the reproducible generator) is the standing answer if a reviewer later questions whether the golden reflects real behavior.
- The single-source-of-truth preserved-column set (D-04) is the user's clearest signal of intent for this phase: it's not just deleting duplication, it's removing the *class* of seam that generates these bugs. Prefer solutions that make a future column-addition safe-by-construction over ones that merely centralize the current list.

</specifics>

<deferred>
## Deferred Ideas

None new — discussion stayed within phase scope. Milestone-level deferrals already recorded in SEED-080: entry/full lane merge, post-move convention change, queue/broker rewrite, worker protocol changes, R14 tier-3 lease, SEED-078 streaming, 426 version-rejection gate.

</deferred>

---

*Phase: 150-Consolidate-Write-Path*
*Context gathered: 2026-07-04*
