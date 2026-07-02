# Phase 143: Offline Re-tagger - Context

**Gathered:** 2026-06-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver a pure-offline re-tagger that re-derives `game_flaws` tactic tags from the stored
MultiPV=2 JSONB blobs (Phase 142) **with no engine pass**, applying the forcing-line gate at a
tunable margin, idempotently, via the single shared classify path. Plus: wire the gate into that
live classify path, complete/audit the GATE-03 (mate-priority) and GATE-04 (defender-branch) unit
coverage, and emit a committed per-motif tag-delta report.

**In scope:**
1. Wire `forcing_line_gate.apply_forcing_line_filter()` into the live tactic classify path so new
   game analysis is gated (GATE-03, GATE-04 going live; single classify path for SC4). (RETAG-02)
2. Parameterize the gate by margin (add a `margin` arg to `apply_forcing_line_filter` /
   `is_solver_node_forced`, defaulting to `ONLY_MOVE_WIN_PROB_MARGIN`). (RETAG-01)
3. The offline re-tagger CLI: **extend `scripts/backfill_tactic_tags.py` and `git mv` it to
   `scripts/retag_flaws.py`** — add JSONB-blob loading + `--margin` + gate application, reusing the
   existing keyset paging / worker pool / change-only batched UPDATE. (RETAG-01, RETAG-02)
4. A committed `reports/` markdown with per-motif removed/survived tag-delta counts, re-runnable.
   (RETAG SC1)
5. Audit + fill the GATE-03 mate-priority and GATE-04 defender-branch unit tests against the exact
   roadmap SC wording (notably a multi-ply "branch-then-reconverge" case). (GATE-03, GATE-04)

**Out of scope (later phases):** user-28 A/B old-vs-new diff + committing the final
`ONLY_MOVE_WIN_PROB_MARGIN` (Phase 144); `backfill_multipv.py --db prod` + corpus retag rollout +
per-motif chip-count monitoring (Phase 145). The MultiPV engine pass and blob storage are done
(Phase 142); the gate constants and core gate logic exist (Phase 141) — this phase parameterizes
and wires them, it does not re-decide the thresholds or the blob shape.

</domain>

<decisions>
## Implementation Decisions

### Script strategy (RETAG-01, RETAG-02)
- **D-01:** **Extend `scripts/backfill_tactic_tags.py`, then `git mv` it to `scripts/retag_flaws.py`.**
  Rationale: once the gate is wired into the live classify path (D-02), `backfill_tactic_tags.py`'s
  own purpose — "refresh tactic columns to match the live detector" — *requires* loading the blobs
  and applying the gate too, or it would recompute tags that diverge from production. There is no
  longer a coherent gate-free refresh tool to keep separate: the re-tagger and the detector-refresh
  tool are the same operation. `--margin` + blob-loading is the only real delta; keyset paging, the
  spawn-worker pool, change-only batched UPDATE, and `--db/--user-id/--dry-run/--limit/--throttle-ms`
  are reused verbatim. The `git mv` preserves git history and satisfies the roadmap name (Phases 144
  and 145 reference `retag_flaws.py`). Update the module docstring to reflect the gate/margin role.
- **D-01a:** Keep `--user-id` / `--dry-run` / `--db` (roadmap-required) and the inherited
  `--limit` / `--workers` / `--throttle-ms`. Add `--margin` (float, defaults to the module constant).
  `--only-tagged` is now subtler: post-gate the goal is *suppression* of existing tags, so a full
  refresh (omit `--only-tagged`) is the default for a margin sweep; the planner should keep the flag
  but document that it can't discover newly-gated-in tags (it never could discover new detections).

### Gate integration & "single classify path" (RETAG-02, SC4)
- **D-02:** **Wire the gate into the live classify path now** (not deferred to Phase 145). The gate
  becomes part of `_detect_tactic_for_flaw` (or a thin combined classify helper) reading the stored
  blobs; the re-tagger and the live eval-drain share that one path, guaranteeing no drift (SC4).
- **D-02a:** **Acceptable consequence (flagged):** new games analyzed between Phase 143 and 145 get
  gated at the *provisional* `0.35` margin before Phase 144 validates it. This self-heals — Phase
  145's corpus retag re-applies the **final committed** margin to *every* flaw (including those
  analyzed in the 143→145 window). The live default stays `0.35` until Phase 144 commits the final
  value; only the constant changes, not the wiring.
- **D-02b:** The re-tagger must run the **full classify** (detection kernel + gate) from stored
  inputs, not just read existing tag columns — so a second run on the same data + same margin
  produces identical output (idempotency, SC4). Mirror how the current script re-runs the shared
  `_detect_tactic_for_flaw` kernel rather than reimplementing detection.

### Margin threading (RETAG-01)
- **D-03:** **Parameterize the gate functions.** Add a `margin: float = ONLY_MOVE_WIN_PROB_MARGIN`
  parameter to `apply_forcing_line_filter` (threaded down to `is_solver_node_forced`). No global
  mutation — clean, testable, and worker-pool-safe (spawn workers re-import the module; a global
  override would have to be re-set per worker). The committed constant remains the live default; the
  CLI `--margin` flows through the call, not through the module global.

### Per-motif delta report (RETAG SC1)
- **D-04:** **Committed `reports/` markdown**, timestamped, following the benchmarks / db-report
  convention: per-motif removed/survived counts (and, where cheap, depth/quality breakdown). Must be
  re-runnable so a `--margin` sweep / `/loop` regenerates it; it feeds Phase 144's A/B directly.
  Planner picks the exact path (suggest `reports/retag/retag-YYYY-MM-DD.md`) and whether the script
  writes it or a sibling reporting helper does.

### GATE-03 / GATE-04 scope (mate-priority + defender)
- **D-05:** **Logic already exists (Phase 141); this phase is audit-and-fill, not net-new logic.**
  `forcing_line_gate.py` already implements `_resolve_mate_priority` (only-best-is-mate → forced;
  both-mates → shorter forced; mate-in-1 never suppressed) and solver-only uniqueness (defender
  nodes skipped). `tests/services/test_forcing_line_gate.py` already has `TestMatePriority` (both
  colors) and `test_defender_ambiguity_does_not_kill_line` (docstring: "D-01 pulled forward from
  Phase 143"). Phase 143's remaining GATE work: verify the existing coverage against the *exact* SC2
  /SC3 wording and add the residual case the current tests don't cover — a **multi-ply
  "branch-then-reconverge"** line (defender branches, line reconverges to forced solver
  continuation), since the existing defender test is a single-node case. If the audit finds a true
  logic gap (not just a missing test), fix it in `forcing_line_gate.py` and note the deviation.

### Claude's Discretion
- Exact CLI flag names beyond the locked set, the precise combined-classify helper signature and
  where it lives (inside `flaws_service._detect_tactic_for_flaw` vs a thin wrapper both the drain and
  the re-tagger call), the report file path/format details, the blob-loading query shape (extend
  `_fetch_flaw_page` to also project the two deferred JSONB columns + the flaw-ply `eval_cp` for the
  already-winning reject), and the worker-payload shape for passing blobs across the process boundary
  — planner/executor decide within the decisions above.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone spec & requirements (authoritative)
- `.planning/notes/tactic-forcing-line-gate.md` — design source for the gate; §"Storage" (blob
  shape, engine-free re-tag) and §"Open knobs" (margin tuning). **AGPL boundary: heuristics /
  constants / names only — copy NO lichess-puzzler source.**
- `.planning/REQUIREMENTS.md` §GATE (GATE-03, GATE-04) and §RETAG (RETAG-01, RETAG-02) — this
  phase's requirements and the exact margin-as-tunable wording.
- `.planning/ROADMAP.md` §"Phase 143" — the 4 success criteria this phase is graded on.
- `.planning/phases/141-jsonb-schema-gate-logic/141-CONTEXT.md` — gate constants and the D-01 note
  that the **full mate hierarchy + its tests were already implemented in 141** (do not re-decide).
- `.planning/phases/142-multipv-2-engine-pass-eval-drain-remote-worker/142-CONTEXT.md` — the locked
  blob shape (`b/bm/s/sm/su`, white-perspective cp), every-node storage, and the JSONB write path.

### Gate + classify code (the load-bearing surfaces)
- `app/services/forcing_line_gate.py` — `apply_forcing_line_filter()` (line ~186, add `margin`
  param), `is_solver_node_forced()` (~74), `_resolve_mate_priority()` (~35), `_truncate_at_still_
  winning_floor` / `_strip_trailing_only_moves`, and the constants `ONLY_MOVE_WIN_PROB_MARGIN=0.35`,
  `ALREADY_WINNING_CP_THRESHOLD=300`, `STILL_WINNING_FLOOR_CP=200`. `PvNode` TypedDict is the blob.
- `tests/services/test_forcing_line_gate.py` — existing `TestMatePriority`,
  `test_defender_ambiguity_does_not_kill_line`, `TestOnlyMoveMargin` (468 lines); extend here.
- `app/services/flaws_service.py` — `_detect_tactic_for_flaw()` (~401–500): the single classify
  kernel shared by the live eval drain and the re-tagger. The gate wires in here (or a thin wrapper).
  `allowed` = refutation line at `flaw_ply+1`, `missed` = best-move line at `flaw_ply`.
- `app/models/game_flaw.py` — `allowed_pv_lines` / `missed_pv_lines` (deferred JSONB, ~120–121);
  the 8 tactic-tag columns the re-tagger UPDATEs.

### The script being extended/renamed
- `scripts/backfill_tactic_tags.py` — the optimized base: keyset paging (`_fetch_flaw_page`),
  position loading (`_load_positions_for_page`), spawn-worker pool + picklable `_FlawWork`,
  change-only `bulk_update_tactic_tags`, `FLAWS_PER_BATCH=2000`, all CLI flags. `git mv` target:
  `scripts/retag_flaws.py`.
- `app/repositories/game_flaws_repository.py` — `TACTIC_TAG_COLUMNS`, `bulk_update_tactic_tags`.
- Report convention model: the `benchmarks` / `db-report` skills' committed `reports/` markdown.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `scripts/backfill_tactic_tags.py` — ~90% of the re-tagger already exists here (paging, workers,
  idempotent change-only UPDATE, `--db/--user-id/--dry-run/--limit/--throttle-ms`). The re-tagger is
  this script + blob loading + `--margin` + gate application. This is the basis for D-01.
- `forcing_line_gate.apply_forcing_line_filter()` — implemented and unit-tested at the default
  margin; needs only a `margin` parameter (D-03) and a live call site (D-02).
- `_detect_tactic_for_flaw()` — the shared detection kernel both the live drain and the current
  backfill script already call; the natural seam for gate integration (single classify path, SC4).

### Established Patterns
- Gate logic + mate/defender tests were **pulled forward into Phase 141** — confirm-and-extend, do
  not rebuild (D-05).
- `_detect_tactic_for_flaw` reads positions (move_san / pv / eval_mate) at `ply` and `ply+1`; the
  gate additionally reads the two stored JSONB blob lines + the flaw-ply `eval_cp`. Extend the page
  fetch to project those, then pass them into the (now gated) classify.
- Change-only UPDATE + no-op skip (no WAL) is how idempotency + speed are achieved; preserve it.

### Integration Points
- `forcing_line_gate.py` — `margin` param on the public fns.
- `flaws_service._detect_tactic_for_flaw` (or a thin wrapper) — the live gate call site (D-02).
- `scripts/retag_flaws.py` (renamed) — `_fetch_flaw_page` projects the JSONB columns; `_FlawWork`
  carries the blob lines + `pre_flaw_eval_cp`; `_worker_recompute` applies the gate at `--margin`.
- A `reports/` markdown writer for the per-motif delta (D-04).

</code_context>

<specifics>
## Specific Ideas

- User's explicit steer: prefer extending the existing, optimized `scripts/backfill_tactic_tags.py`
  over a brand-new script — borrow its ideas at minimum. Honored as D-01 (extend + `git mv`).
- The `--margin` flag is the whole point of RETAG-01: every threshold change must be a seconds-fast,
  engine-free, `/loop`-able re-derivation against stored blobs. Keep the run fast (the current script
  is DB-round-trip-bound, ~950 flaws/s at 8 workers on a local DB; run prod on the server).
- Idempotency check (SC4): a second run at the same `--margin` must produce byte-identical tag
  output. The change-only UPDATE makes the second run a no-op (0 rows changed) — that *is* the
  idempotency evidence the verifier can assert.

</specifics>

<deferred>
## Deferred Ideas

- User-28 A/B old-vs-new diff, per-motif removed/survived across depth buckets, ~30-case hand-check,
  and committing the final `ONLY_MOVE_WIN_PROB_MARGIN` — **Phase 144**.
- `backfill_multipv.py --db prod` (blob backfill for old-worker / pre-142 games),
  `retag_flaws.py --db prod` corpus rollout with `WHERE allowed_pv_lines IS NULL` idempotency, and
  before/after per-motif chip-count monitoring — **Phase 145**.
- Solver-only blob storage (halve MultiPV cost) — explicit later optimization (Phase 141 D-03 locked
  every-node storage).
- None of the above is scope creep — discussion stayed within the offline-re-tagger boundary.

</deferred>

---

*Phase: 143-offline-re-tagger*
*Context gathered: 2026-06-30*
