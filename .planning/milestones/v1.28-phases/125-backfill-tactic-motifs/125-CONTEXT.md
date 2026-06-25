# Phase 125: Backfill Tactic Motifs - Context

**Gathered:** 2026-06-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 125 is an **operational backfill**, not new detection code. Phase 124 already
delivered the detector (`detect_tactic_motif`), the three `game_flaws` columns
(`tactic_motif` / `tactic_piece` / `tactic_confidence`), and wired detection into the
single classify path. `scripts/backfill_flaws.py` already produces tactic motifs as a
side effect of its full flaw recompute, and already supports `--db`, `--full-evald-only`,
`--dry-run`, `--limit`, OOM-safe batching, and idempotent delete-then-insert.

This phase **runs that script on the dev DB, proves coverage is honest via a
coverage/NULL-breakdown report, and produces a documented prod runbook.** The prod
execution itself is a deferred operational step outside this phase's completion gate
(see D-01).

**In scope:**
- Run `backfill_flaws.py --db dev --full-evald-only` over the dev DB's ~11.2k
  full-eval'd games.
- A coverage-report query/helper that proves SC#1 ("honest coverage; NULL = genuine
  no-fire, not skipped").
- An idempotency re-run check (SC#3 — already built in, must be verified).
- A documented prod runbook (exact command, expected load, verification queries) ready
  for a later prod run.

**Out of scope:**
- Executing the prod backfill (deferred — runbook only this phase; D-01).
- Benchmark-DB backfill (future tactic-motif benchmark zones — deferred).
- Query-time suppression of the 8 sub-bar motifs (Phase 126 concern — the backfill
  stores ALL fired motifs per Phase 124 D-11).
- Any frontend, `/api/library/tactic-comparison`, chips, or comparison UI (Phase 126).
- Lichess-eval-only games (auto-handled — see D-06, SC#2 needs zero work).

</domain>

<decisions>
## Implementation Decisions

### Execution scope & phase boundary
- **D-01:** Phase 125 **completes on the dev DB**: the dev backfill is run, the coverage
  report passes on dev, and a documented prod runbook is ready. **Prod execution is a
  deferred operational step outside the completion gate.** ROADMAP SC#1 names prod's
  ~131k games — record it as **met-on-dev / prod-pending** (the dev rehearsal proves the
  mechanism; the prod run is a later, low-risk operational step using the runbook).
  Dev representativeness verified: dev has **11,199 full-eval'd games**, 89k flaw rows,
  18k positions with PVs, and `tactic_motif = 0` everywhere (never backfilled) — a real
  run that genuinely exercises the path.
- **D-02:** Use `backfill_flaws.py --db dev --full-evald-only`. The `--full-evald-only`
  flag targets the flaw-eligible set directly (`full_evals_completed_at IS NOT NULL`) and
  auto-skips lichess-eval-only games, which is exactly SC#2 (no bespoke job needed).
  Smoke-test first with `--dry-run` / `--limit` before the full run.

### DB-load posture
- **D-03:** **Let it rip concurrently** — run alongside the active eval drain / remote
  fleet, no pause or throttle. The backfill is pure-CPU detection + DB reads/writes with
  **no Stockfish invocation**, and the OOM history was import memory pressure, not this
  kind of load. The race with eval-completion writes to `game_flaws` is benign: both
  paths call the same `classify_game_flaws` + `flaw_record_to_row` and produce identical
  rows. On dev this is trivially safe; the prod runbook carries the same posture (batch
  size `BACKFILL_GAMES_PER_BATCH = 100` is the existing OOM-safe default — only tune if a
  prod soak shows pressure).

### Verification — the real acceptance bar (SC#1)
- **D-04:** Prove honest coverage with a **coverage report + NULL breakdown**, not just
  spot-checks. The report must show, over mistake+blunder flaws on full-eval'd games:
  1. % with a non-NULL `tactic_motif` (overall coverage).
  2. By-motif counts (which detectors fired, distribution).
  3. **The NULL split** — flaws with **no PV** at `flaw_ply + 1` (genuinely undetectable)
     vs flaws **with a PV but no detector fired** (genuine low-confidence no-fire). This
     split is what makes "NULL = honest, not skipped" *verifiable*. Dev's sparse PVs
     (18k) make this distinction concretely visible.
  4. Spot-check a small sample from each NULL bucket to confirm the classification.
- **D-05:** **Idempotency check (SC#3):** re-run the backfill on a sample (or `--limit`)
  and assert the resulting rows are identical (no duplication, no corruption). Already
  guaranteed by delete-then-insert scoped to `(game_id, user_id)`, but must be
  demonstrated, not just asserted.

### Recompute blast-radius safety (flagged to researcher/planner)
- **D-06:** `backfill_flaws.py` recomputes the **entire** flaw record (delete-then-insert
  ALL of a game's flaws), not just the tactic columns. Phase 124 only added tactic
  detection inside `_build_flaw_record` without touching severity/tempo/phase logic, so
  the non-tactic columns **should** be byte-identical after the run. **Confirm this** —
  e.g. a before/after comparison of non-tactic columns on a dev sample, or reason from the
  diff that no other classify logic changed since dev's last `game_flaws` materialization.
  Guards against a silent recompute drift surfacing as a "tactic backfill."

### Claude's Discretion
- Coverage-report format and location (ad-hoc SQL vs a small `scripts/` helper vs a
  reusable query) — pick what makes the dev verification clean and re-runnable on prod.
- Prod-runbook format/location (a markdown note under `.planning/` or `scripts/`, or
  inline in the phase artifacts).
- Sample sizes for the spot-check and idempotency re-run.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### The backfill tool & write path (the core of this phase)
- `scripts/backfill_flaws.py` — the tool. Already supports `--db`, `--full-evald-only`,
  `--dry-run`, `--limit`, batching (`BACKFILL_GAMES_PER_BATCH = 100`), idempotent
  delete-then-insert. The phase runs this; it likely needs **no code change**.
- `app/services/flaws_service.py` — `classify_game_flaws`, `_detect_tactic_for_flaw`
  (~359), `_build_flaw_record` (~412); the `FlawRecord` tactic fields (~135). The
  recompute path that produces tactic motifs.
- `app/services/tactic_detector.py` — `detect_tactic_motif` dispatcher (Phase 124).
- `app/repositories/game_flaws_repository.py` — `flaw_record_to_row` (writes
  `tactic_motif` / `tactic_piece` / `tactic_confidence`, ~118), `delete_flaws_for_game`,
  `bulk_insert_game_flaws`.
- `app/repositories/flaws_repository.py` — `fetch_game_positions_ordered`.

### Phase 124 foundation (decisions this phase inherits)
- `.planning/phases/124-schema-tactic-detector/124-CONTEXT.md` — D-01..D-12 (schema,
  priority order, precision bars, `tactic_piece` semantics, **D-11 store-all /
  suppress-at-query**).
- `.planning/phases/124-schema-tactic-detector/124-VERIFICATION.md` — precision gate
  PASSED: 16 validated motifs surfaced, 8 in `_QUERY_SUPPRESSED_MOTIFS` (a Phase 126 gate
  input, NOT a Phase 125 filter — backfill stores everything).
- `.planning/notes/tactic-tagging-architecture.md` — the load-bearing decision record.

### Roadmap & requirements
- `.planning/milestones/v1.28-ROADMAP.md` — Phase 125 goal + SC#1/2/3, Phase 126
  dependency on populated `tactic_motif` rows.
- `.planning/REQUIREMENTS.md` — TACSCH-03.
- `CLAUDE.md` — OOM history (import pressure, not this load), DB-target host:port mapping,
  `bin/prod_db_tunnel.sh` (for the deferred prod runbook), batching mandate.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `scripts/backfill_flaws.py` — does the whole job already. `--full-evald-only` targets
  the eligible set and auto-excludes lichess-eval-only games (SC#2 for free). The only
  plausibly-new code this phase is the coverage-report query/helper (D-04).
- `scripts/backfill_eval.py` — precedent for `--db dev|benchmark|prod` script structure
  and the prod-tunnel pattern (informs the deferred runbook).

### Established Patterns
- All three flaw-write paths (import hook, `reclassify_positions.py`, `backfill_flaws.py`)
  call the SAME `classify_game_flaws` + `flaw_record_to_row` — so the backfill output
  matches what the live eval drain writes (this is what makes the concurrent-run race
  benign, D-03).
- Delete-then-insert per `(game_id, user_id)` = idempotent recompute (D-05, SC#3).
- `BACKFILL_GAMES_PER_BATCH = 100` named constant, commit-per-batch (OOM-safe, D-03).

### Integration Points
- No new wiring needed — Phase 124 already routes `detect_tactic_motif` output through
  `_build_flaw_record` → `flaw_record_to_row` → `game_flaws` columns. The backfill simply
  re-runs that path over the eligible games.
- Verification connects via read-only SQL over `game_flaws` (tactic columns) joined to
  `game_positions.pv` (the NULL-split, D-04).

</code_context>

<specifics>
## Specific Ideas

- Dev-DB snapshot at discussion time (informs the rehearsal scale and the coverage
  report's expected shape): 189,419 total games, **11,199 full-eval'd**, 89,007 flaw
  rows, **0** with `tactic_motif` (pre-backfill baseline), 18,035 positions with PVs.
- The sparse PV count vs flaw count is a feature for verification: it makes the
  "no-PV NULL" vs "PV-but-no-fire NULL" split (D-04) concretely measurable rather than
  hypothetical.

</specifics>

<deferred>
## Deferred Ideas

- **Prod backfill execution** — runbook delivered this phase (D-01); the actual prod run
  over ~131k games is a later operational step (let-it-rip posture, same verification
  report on prod).
- **Benchmark-DB backfill** — would give future tactic-motif **benchmark zones** (Phase
  126 "benchmark zone where available"). Larger scope (1M+ games), its own concern; not
  in 125.
- **Query-time suppression surfacing** — which of the 16 validated vs 8 suppressed motifs
  to surface is a Phase 126 decision. Phase 125 stores all fired motifs unconditionally.

None of these belong in Phase 125 scope.

</deferred>

---

*Phase: 125-backfill-tactic-motifs*
*Context gathered: 2026-06-18*
