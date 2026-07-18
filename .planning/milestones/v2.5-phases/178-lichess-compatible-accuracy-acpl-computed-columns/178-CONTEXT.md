# Phase 178: Lichess-compatible accuracy & ACPL (computed columns) - Context

**Gathered:** 2026-07-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Compute per-game **accuracy** and **ACPL** for every analyzed game using
lichess's exact formulas, from the per-ply evals already stored in
`game_positions.eval_cp` / `eval_mate`. One uniform methodology so games are
comparable across chess.com / lichess / self-analyzed and over time.

**In scope:**
- Migration that (a) adds `*_imported` columns preserving the current
  platform-provided values, and (b) repurposes the canonical `accuracy` / `acpl`
  columns to hold our uniform lichess-formula values.
- A single Python compute path (lichess formulas) used at BOTH the live hook
  (full-eval completion) and in a `scripts/backfill_*.py`.
- Complete-per-ply-eval-sequence gate (holes → leave NULL).
- A validation script comparing our computed values against the preserved
  `*_imported` values, plus hand-checked fixture unit tests.

**Out of scope (deferred):**
- Any API / frontend surfacing of these values (a later phase).
- Recomputing `inaccuracies` / `mistakes` / `blunders` counts — left entirely
  untouched.
- Running the production backfill (~718k games) — code + script ship here;
  the prod run is a separate operator step after deploy.

</domain>

<decisions>
## Implementation Decisions

### Column strategy — repurpose canonical, preserve platform data (supersedes SEED-110 D-01/D-02)

SEED-110 originally proposed four *new* `*_computed` columns leaving the existing
columns untouched. **This is reversed.** Instead:

- **D-01:** The *canonical* columns `white_accuracy` / `black_accuracy` /
  `white_acpl` / `black_acpl` become **our uniform lichess-formula values** for
  every analyzed game. This makes the canonical name the consistent cross-platform
  metric, so no future "swap the app to `_computed`" migration is ever needed.
- **D-02:** The current platform-provided values move into **new `*_imported`
  columns** as the preserved comparison signal:
  `white_accuracy_imported` / `black_accuracy_imported` /
  `white_acpl_imported` / `black_acpl_imported`.
  (Note the asymmetric current provenance: `*_accuracy` holds **chess.com**
  accuracy today; `*_acpl` holds **lichess** ACPL today. Both simply become
  "whatever the source platform reported" under the `_imported` name — the
  `_imported` columns will be sparse by construction.)
- **D-03:** Migration flow: add `*_imported` columns → copy existing values in →
  NULL the canonical columns → our code (hook + backfill) refills the canonical
  columns. Keep the existing column types: `REAL` for accuracy (matches
  `white_accuracy`), `SmallInteger` for acpl (matches `white_acpl`).
- **D-04:** **Only accuracy + acpl are moved/repurposed.**
  `inaccuracies` / `mistakes` / `blunders` are left **completely untouched** —
  `white_blunders IS NOT NULL` is the project's `is_analyzed` sentinel and those
  three columns are the load-bearing "oracle" flaw counts read across
  `library_repository` / `library_service`. Moving them is out of scope and
  high-risk.

### Scope — backend columns only

- **D-05:** No API or frontend changes. Verified during discussion that
  `accuracy` / `acpl` are **not surfaced to the frontend today** (no FE
  references; not in `app/schemas/library.py`) and are NOT in any game/library
  API response schema returned to the client. So repurposing the canonical
  columns has **no user-visible display change and no backfill display gap** —
  nothing reads them for display yet. A future phase surfaces them.

### Backfill

- **D-06:** Ship the migration, compute path, live hook, and
  `scripts/backfill_*.py` (verified on dev). Running the ~718k-game **prod
  backfill is a separate operator step** after deploy — phase completion is NOT
  gated on it. Batch + `--db dev|benchmark|prod` per the existing
  `scripts/backfill_*.py` convention.

### Validation

- **D-07:** Include a validation script comparing our computed `accuracy` / `acpl`
  against the preserved `*_imported` values across the DB — especially our lichess-game
  ACPL vs `*_acpl_imported` (lichess's own), which should track closely and is the
  primary correctness signal. **Plus** hand-checked fixture unit tests against a
  known lichess game's published accuracy/ACPL (verifies the formula port in
  isolation).

### Formulas — locked (confirmed from lichess source, see SEED-110)

- **D-08:** Win% from cp: `50 + 50*clamp(2/(1+exp(-0.00368208*cp))-1, -1, +1)`,
  with `cp` ceiled to ±1000 BEFORE the sigmoid; mate → ±1000 by sign.
- **D-09:** Per-move accuracy from Win% drop:
  `clamp(103.1668100711649*exp(-0.04354415386753951*(before-after)) - 3.166924740191411 + 1, 0, 100)`
  (evals from the **moving player's** POV; the trailing **+1** uncertainty bonus
  is real).
- **D-10:** Game-level accuracy is NOT a plain mean: seed sequence with the
  initial position at 15cp, sliding volatility window
  `windowSize = clamp(nMoves//10, 2, 8)`, per-window weight
  `clamp(pop_stddev(window), 0.5, 12)`, then per color
  `(weightedMean(acc, weights) + harmonicMean(acc)) / 2`. Start padded with
  `windowSize-2` copies of the first window. (This windowed aggregation is why
  the complete-sequence gate matters and why SQL-only is impractical.)
- **D-11:** ACPL = arithmetic mean of `max(0, before_cp - after_cp)` (mover's POV,
  evals capped ±1000). Plain mean, NOT the volatility/harmonic aggregation.

### Claude's Discretion / for research

Left to the researcher + planner (not user decisions):
- Exact **live-hook seam** — likely at full-eval completion (`full_evals_completed_at`
  set by the drain) and/or `lichess_evals_at` at import; confirm the sequence is
  guaranteed complete there.
- **Eval sign convention + post-move shift** — verify how `game_positions.eval_cp`
  is signed and the row-P-holds-position-P+1 shift (see memory
  `atomic_eval_submit_incremental_lease`) so `before`/`after` map to the right plies
  and Black inversion is correct.
- **Terminal ply / checkmate eval handling**, and games with 0–1 moves.
- Exact **data-move migration mechanics** and the complete-sequence gate query.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Design & formulas (authoritative)
- `.planning/seeds/SEED-110-lichess-compatible-accuracy-acpl.md` — locked design
  intent + the confirmed lichess formulas (win%, per-move accuracy, windowed
  aggregation, ACPL). **Note:** its columns decision D-01/D-02 (four new
  `*_computed` columns) is SUPERSEDED by this CONTEXT (repurpose canonical +
  `*_imported`). Formulas and the complete-sequence-gate rationale still stand.
- Lichess source cited in the seed: `scalachess .../eval.scala`,
  `lila modules/analyse/.../AccuracyPercent.scala`, lila PR #11148
  (the `-0.00368208` constant).

### Codebase integration points
- `app/models/game.py` §162–175 — the accuracy/acpl/i-m-b column definitions to
  migrate; note the exact current types (`REAL`, `SmallInteger`) and the
  provenance comments.
- `app/services/eval_apply.py` §~1073 — where import-time counts/values are
  written today (candidate seam context for the live hook).
- `app/services/eval_drain.py` — full-eval drain that sets
  `full_evals_completed_at` (the likely live-hook trigger).
- `scripts/backfill_full_evals.py` (and siblings) — the `--db` + batching
  convention the new backfill script should follow.

### Eval semantics (must-read before mapping before/after)
- Memory `project_atomic_eval_submit_incremental_lease` — post-move shift
  (row P may hold eval of position P+1); critical for correct before/after ply mapping.
- Memory `project_eval_completion_columns` — the four eval-completion columns and
  what "analyzed by us" vs "lichess freebie" means for eval provenance.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `scripts/backfill_full_evals.py` / `backfill_eval.py` — template for the new
  `scripts/backfill_accuracy_acpl.py` (batching, `--db`, `--user-id` flags).
- Existing migration patterns in `alembic/` for adding nullable columns with
  `CHECK`/partial-index conventions.

### Established Patterns
- The single-Python-path requirement (hook + backfill call the same function)
  mirrors how flaw classification is shared between drain and backfill.
- Column-type discipline (CLAUDE.md): `REAL` accuracy, `SmallInteger` acpl — match
  the columns being repurposed.

### Integration Points
- Live hook fires when a game's full per-ply eval sequence is complete (drain
  `full_evals_completed_at`, or `lichess_evals_at` at import) — researcher to pin
  the exact seam and confirm completeness there.
- `game_positions.eval_cp` / `eval_mate` is the input; sign convention + post-move
  shift must be handled before before/after mapping.

</code_context>

<specifics>
## Specific Ideas

- The `_imported` naming is deliberate: these columns mean "the value the source
  platform reported to us at import" (chess.com accuracy for chess.com games,
  lichess ACPL for lichess games), kept purely as a comparison/validation signal.
- The whole point of repurposing the canonical columns (rather than adding
  `_computed`) is to avoid a second migration later where the app has to switch
  from `*` to `*_computed`. The canonical name IS the uniform metric from now on.

</specifics>

<deferred>
## Deferred Ideas

- **Surfacing computed accuracy/ACPL in the API + frontend** — its own future
  phase. This phase only populates DB columns.
- **Uniform recomputation of inaccuracy/mistake/blunder counts** with lichess
  thresholds — out of scope; those columns stay as-is (they are the `is_analyzed`
  sentinel + oracle counts).
- **Running the prod backfill to 100% coverage** — operator step after deploy,
  not gated in this phase.

</deferred>

---

*Phase: 178-lichess-compatible-accuracy-acpl-computed-columns*
*Context gathered: 2026-07-18*
