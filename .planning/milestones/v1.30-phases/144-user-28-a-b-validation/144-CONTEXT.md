# Phase 144: User-28 A/B Validation - Context

**Gathered:** 2026-06-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Measure the forcing-line gate's effect **engine-free** on dev's stored MultiPV=2 evals for user 28:
quantify noise removed vs good tags killed (per-motif removed/survived + depth-shift), hand-check
the dropped cases for chess correctness (explicit false-negative count), and commit the final
`ONLY_MOVE_WIN_PROB_MARGIN` with an A/B summary justifying the value.

**In scope:**
1. A dedicated A/B harness (`scripts/ab_validate_gate.py`) that loads user-28's stored blobs once
   and runs tactic detection in two arms — **ungated (old)** vs **gated-at-margin (new)** — fully
   in-memory, **no engine call, no DB writes**. (VALID-01)
2. A committed `reports/retag/` markdown: per-motif tags removed/survived, depth-shift
   distribution, small-N caveats, and a hand-check case list. (VALID-02)
3. Hand-check of the dropped cases (HUMAN-UAT: the user's chess judgment) → explicit false-negative
   count. (VALID-02)
4. Commit the final `ONLY_MOVE_WIN_PROB_MARGIN` in `forcing_line_gate.py` with the A/B summary as
   justification. Default rule: **keep 0.35 unless the hand-check shows it fails.** (VALID-02)

**Out of scope (later phase):** `backfill_multipv.py --db prod` + corpus retag rollout + before/after
per-motif chip-count monitoring — **Phase 145**. Enlarging the dev blob sample via a fresh engine
pass (see D-01) is explicitly NOT done in this phase.

</domain>

<decisions>
## Implementation Decisions

### Sample size (VALID-01)
- **D-01:** **Accept the 216 existing blob-bearing dev-28 flaws as-is** (100 allowed-tagged + 71
  missed-tagged). No engine work. Rationale: `retag_flaws.py` re-derives *tags* from blobs but does
  NOT create blobs — only an engine pass does. Enlarging the sample would require re-analyzing
  user-28's dev games through the live eval drain (hours of local Stockfish) or building Phase-145's
  `backfill_multipv.py` early (scope creep). Given the "confirm 0.35" rule (D-03), 216 is sufficient
  to confirm/reject the provisional margin. Report per-motif counts **with explicit small-N caveats**
  (some motifs may have ≤5 cases).
- **D-01a:** **dev-28 only.** prod-28 is NOT pulled in as a reference in this phase (user did not opt
  into the prod sanity check). VALID-01 reserves prod-28 as sanity-only, never an A/B control.

### A/B harness mechanism (VALID-01)
- **D-02:** **Dedicated `scripts/ab_validate_gate.py`** (not an extension of `retag_flaws.py`). It
  loads the 216 blobs + flaw-ply `eval_cp` once, then for each flaw runs the tactic-detection kernel
  twice over the same stored inputs: **ungated** (old arm) and **gated at the test margin** (new arm),
  in-memory, no DB writes. Emits per-motif removed/survived, depth-shift distribution, and the
  dropped-case list. Rationale: a single-purpose validation tool keeps the rollout tool
  (`retag_flaws.py`) clean and avoids overloading it with a validation-only mode.
- **D-02a:** **The "old" arm is genuinely ungated, not `--margin 0`.** `margin=0` still applies the
  mate hierarchy, already-winning reject (>300cp), and one-mover discard, so it is NOT the pre-gate
  baseline. The harness must run detection with `apply_forcing_line_filter` bypassed entirely for the
  old arm (mirror the pre-143 classify path), and with the gate at the test margin for the new arm.
  Both arms read the SAME stored blobs (isolates the gate's effect from `eval_cp` cross-machine
  non-determinism — VALID-01).

### Margin selection (VALID-02)
- **D-03:** **Keep the provisional 0.35 unless the hand-check shows it fails.** This is a confirmation
  check, not a fine-grained sweep. Generate the removed/survived table at 0.35 (optionally a small
  neighbourhood, e.g. 0.30/0.35/0.40, for context), but the default committed value stays 0.35 unless
  the hand-check reveals it is clearly killing good tags or leaving obvious noise.
- **D-03a:** **VALID-02 SC4 ("final margin committed") is satisfied by confirming 0.35 + the A/B
  summary justification** — if 0.35 is confirmed, no constant change is needed; the "commit" is the
  recorded justification (the A/B summary + a pointer comment at the constant). Only change the value
  if the hand-check fails 0.35.

### Hand-check workflow (VALID-02) — HUMAN-UAT
- **D-04:** **Surface dropped cases as committed `reports/retag/` markdown**: each case = motif, FEN,
  the PV / refutation line, and a **lichess analysis deep-link** so the user adjudicates in-browser.
  The user marks each **false negative (good tag killed)** vs **correct drop (noise)**; the FN count
  folds into the A/B summary. This step requires the user's chess judgment — it is a HUMAN-UAT gate,
  not something the executor decides.
- **D-04a:** **Hand-check ALL dropped cases when the count is ≤30** (at 0.35 on 216 flaws the drop set
  is likely a handful — no sampling needed at this scale). **Fall back to motif-stratified ~30** only
  if the gate drops more than ~30, so each noisy motif (sacrifice / clearance / capturing-defender)
  gets eyeballs.

### Claude's Discretion
- Exact `ab_validate_gate.py` CLI flags and function signatures; the precise per-motif/depth table
  shape and the `reports/retag/` filename (suggest `reports/retag/ab-validation-YYYY-MM-DD.md`); the
  lichess deep-link URL format; how the ungated arm reuses the detection kernel (a `gate=False`
  param on `_classify_tactic_gated` vs a thin ungated wrapper); whether the small neighbourhood sweep
  (0.30/0.40) is included for context. Planner/executor decide within the decisions above.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone spec & requirements (authoritative)
- `.planning/notes/tactic-forcing-line-gate.md` — design source; §"Open knobs" (margin tuning) and
  §"Storage" (engine-free re-tag). **AGPL boundary: heuristics/constants/names only — copy NO
  lichess-puzzler source.**
- `.planning/REQUIREMENTS.md` §VALID (VALID-01, VALID-02) — this phase's requirements and the exact
  "engine-free, isolate gate from eval_cp non-determinism, prod-28 sanity-only" wording.
- `.planning/ROADMAP.md` §"Phase 144" — the 4 success criteria this phase is graded on.

### Prior-phase context (locked, do not re-decide)
- `.planning/phases/143-offline-re-tagger/143-CONTEXT.md` — gate is already live in the classify path
  (D-02), `--margin` is a threaded param (D-03), `retag_flaws.py` re-derives tags from blobs, and the
  per-motif delta report pattern (D-04). The provisional 0.35 default stays live until this phase
  commits the final value.
- `.planning/phases/142-multipv-2-engine-pass-eval-drain-remote-worker/142-CONTEXT.md` — locked blob
  shape (`b/bm/s/sm/su`, white-perspective cp), every-node storage, and the D-04 fact that old/
  un-upgraded analysis leaves blobs NULL (this is WHY dev-28 only has 216 blob flaws — Phase 145
  backfills the corpus).
- `.planning/phases/141-jsonb-schema-gate-logic/141-CONTEXT.md` — gate constants and the mate
  hierarchy (already implemented; do not re-decide).

### Code surfaces (the load-bearing files)
- `app/services/forcing_line_gate.py` — `apply_forcing_line_filter()` / `is_solver_node_forced()`
  (margin param), `_resolve_mate_priority()`, and `ONLY_MOVE_WIN_PROB_MARGIN = 0.35` (line 52) —
  the constant this phase commits. `margin=0` is NOT a no-gate bypass (see D-02a).
- `app/services/flaws_service.py` — `_classify_tactic_gated()` (~525) is the single gated classify
  path; the live call site (~558) calls `apply_forcing_line_filter(...)`. The A/B harness needs both
  this gated path and an **ungated** variant (the pre-143 detection without the gate) for the old arm.
- `scripts/retag_flaws.py` — the rollout re-tagger (extended in Phase 143). Reference for blob-loading
  / page-fetch / `--margin` threading; the new A/B script borrows its blob-loading query shape but is
  a separate, write-free tool (D-02).
- `app/models/game_flaw.py` — `allowed_pv_lines` / `missed_pv_lines` (deferred JSONB) + the 8 tactic
  tag columns.

### Report convention
- `reports/retag/` (currently empty, `.gitkeep`) — output dir for the A/B summary + hand-check case
  list (D-04). Follow the benchmarks / db-report committed-markdown convention.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_classify_tactic_gated()` (`flaws_service.py` ~525) — the gated classify kernel; the new arm
  reuses it at the test margin. The old arm needs the same detection minus the gate call.
- `retag_flaws.py` blob-loading (`_fetch_flaw_page` projecting the two JSONB columns + flaw-ply
  `eval_cp`) — the query shape the A/B script borrows for loading the 216 blobs.
- `forcing_line_gate.apply_forcing_line_filter(margin=...)` — already param-threaded (143 D-03), so
  the new arm just calls it at the test margin; no gate code changes needed.

### Established Patterns
- Detection is replayed from stored blobs (no engine) — the same engine-free pattern as the
  re-tagger; the A/B is detection-twice + diff, write-free.
- Committed `reports/` markdown (benchmarks / db-report / retag) — the deliverable convention.

### Integration Points
- New: `scripts/ab_validate_gate.py` (read-only DB, no writes) → `reports/retag/` markdown.
- `forcing_line_gate.py` `ONLY_MOVE_WIN_PROB_MARGIN` — committed (confirmed or changed) at phase end.

### Load-bearing feasibility finding (verified against dev DB)
- User 28 (dev) has **34,055 flaws but only 216 carry MultiPV blobs** (100 allowed-tagged + 71
  missed-tagged). The A/B universe is exactly these 216. This is the direct consequence of 142 D-04
  (only post-142 re-analyzed games get blobs). Drives D-01 (accept 216) and the small-N caveats.

</code_context>

<specifics>
## Specific Ideas

- User's explicit confirmation: a dedicated A/B script is preferred over overloading `retag_flaws.py`.
- The hand-check is the decision gate: 0.35 stands unless the user's eyeball review of dropped cases
  shows real tactics being killed. The lichess deep-link per case is the adjudication surface.
- Keep the run engine-free and fast — both A/B arms replay the same 216 stored blobs in-memory.

</specifics>

<deferred>
## Deferred Ideas

- Enlarging the dev blob sample via a fresh engine pass / `backfill_multipv.py` — out of scope here;
  prod corpus backfill + rollout is **Phase 145**.
- prod-28 as a larger descriptive sanity reference — available per VALID-01 but not opted into this
  phase; can be added later if dev-28's 216 prove too thin.
- None of the above is scope creep — discussion stayed within the A/B-validation boundary.

</deferred>

---

*Phase: 144-user-28-a-b-validation*
*Context gathered: 2026-06-30*
