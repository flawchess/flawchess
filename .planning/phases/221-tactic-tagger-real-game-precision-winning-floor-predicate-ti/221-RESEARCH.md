# Phase 221: Tactic-Tagger Real-Game Precision — Winning Floor, Predicate Tightening & Port Fixes (SEED-165) - Research

**Researched:** 2026-09-12
**Domain:** Chess tactic-motif detection (cook.py-aligned predicates), forcing-line gating, offline prod re-tagging
**Confidence:** HIGH (every code claim read from the file this session; every numeric claim either measured this session or quoted from the committed review report)

## Summary

This phase is **entirely in-repo, zero new dependencies, zero migration**. Everything it needs
already exists: the gate (`app/services/forcing_line_gate.py`), the single classify path
(`app/services/flaws_service.py::_classify_tactic_gated`), the detector registries
(`app/services/tactic_detector.py`), the CC0 fixture harness (`tests/scripts/tagger/`), the
offline re-tagger (`scripts/retag_flaws.py`) and the prod tunnel (`bin/prod_db_tunnel.sh`).
The work is a set of precise, small diffs plus one new fixture CSV and one new scored table.

Three things dominate the plan's risk and are **not** obvious from the requirement text:

1. **`scripts/retag_flaws.py::_worker_recompute` builds a SPARSE positions list that does not
   contain `positions[ply-1]`** (`retag_flaws.py:295-301` — only `ply` and `ply+1` are filled).
   Every other `_classify_tactic_gated` call site passes a full ply-indexed list. If TAGFIX-01's
   blob-missing fallback or TAGFIX-02's `eval_mate`-derived already-winning reject read
   `positions[n-1]`, the **prod retag would silently behave differently from the live path** —
   exactly the SC4 no-drift property the script's own docstring claims to guarantee. The plan
   must set `positions[ply-1] = work.prv` (guarded on `ply >= 1`) in the same task.
2. **The retag's per-motif delta report is written ONLY under `--dry-run`**
   (`retag_flaws.py:800-810`), and it tracks **removed/survived only — there is no "shifted"
   bucket** (`_accumulate_motif_counts`, `retag_flaws.py:470-528`). TAGFIX-09 asks for
   removed/**survived**/**shifted** on the real (writing) run. Both are code changes, not
   operator procedure.
3. **The fixture gate does not run in the default local test command.**
   `pyproject.toml:86` sets `addopts = "--ignore=tests/scripts/tagger"`, so `uv run pytest -n auto -x`
   (the CLAUDE.md pre-merge gate) skips it entirely. CI runs it as a separate step
   (`.github/workflows/ci.yml:136-137`). Every plan that touches a detector must run
   `uv run pytest tests/scripts/tagger -q` explicitly.

I measured the combined effect of three of the changes on the TRAIN fixture this session
(sacrifice persistence + depth cap 4, discovered-attack `return`-on-recapture + depth `k`,
`self-interference` out of the registry): **no precision floor is breached, sacrifice recall falls
0.115 → 0.050 with FP staying at 0, and discovered-attack precision RISES 0.990 → 1.000** while
eleven other motifs gain true positives from the freed dispatch slots. Full table in
§ Code Examples / Measured Simulation.

**Primary recommendation:** Sequence the phase as (0) freeze the prod real-game sample BEFORE any
code change, (1) port fixes + registry removal, (2) gate floor + None-cp fix, (3) sacrifice /
clearance predicates, (4) missed parity, (5) harness + real-game scoring, (6) dev retag smoke,
(7) release + prod retag. Add `motif_int` to `apply_forcing_line_filter` as a **defaulted keyword
argument** (`motif_int: int | None = None`, floor skipped when None) so the ~50 existing gate unit
tests and `scripts/ab_validate_gate.py` keep compiling unchanged.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Winning floor (forcing_line_gate.py / _classify_tactic_gated)**

- **D-01:** **Per-tier floor at the firing node.** The solver-perspective eval of the blob
  node at the firing depth (odd depths rounded up to the solver node; `bm` checked before
  `b`) must be a mate for the solver or cp ≥ floor: **+200 for tier-3 (deflection,
  attraction, intermezzo, x-ray, interference, clearance, capturing-defender, sacrifice)
  and tier-5 move-type motifs (promotion, under-promotion, en-passant); 0 ("not losing")
  for tier-1/2 geometric motifs (hanging-piece, fork, pin, skewer, double-check,
  discovered-check, discovered-attack, trapped-piece).** Mate motifs are exempt (a mate
  line is winning by definition). Both floors are named constants; the tier→floor map
  lives next to the dispatcher's tier registry so it cannot drift from it. Rationale: a
  fork that wins a piece while still behind is coachable; a "sacrifice" or "clearance"
  while losing never is; +200 is lichess-puzzler's advantage floor, which the fixture
  labels implicitly assume.
- **D-02:** **Firing node only.** Node 0 is not checked; a genuine attacking sacrifice is
  legitimately below the floor at node 0 and converts deeper.
- **D-03:** **Blob missing → fall back to `game_positions` evals, same floor.** Allowed:
  eval after the flaw (`positions[n].eval_cp` / `eval_mate`, refuter's perspective).
  Missed: eval before the flaw (`positions[n-1]`, mover's perspective). No tag is skipped
  or suppressed merely for lacking a blob.
- **D-04:** **The gate is never skipped because `pre_flaw_eval_cp` is None.** The
  already-winning reject is derived from `eval_mate` when cp is absent: **a forced mate
  for the solver before the flaw = already winning = reject** (mate-motif tags stay
  exempt, as today). The rest of the gate (only-move, floors, strips, one-mover discard)
  runs on the blob exactly as for cp-scored flaws. The `blobs_pending` and `[]`-sentinel
  behaviours are unchanged.

**Sacrifice & clearance (tactic_detector.py)**

- **D-05:** **Sacrifice persistence:** the material deficit must still be ≥
  `MIN_SACRIFICE_DROP` after the *next* pov move (`boards[k+3]`), or the line must end
  before that board. Drops the delayed-recapture / zwischenzug shape (32% of cook's own
  sacrifice puzzles). Documented as a deliberate divergence from cook in
  `precision_floors.py`; fixture recall will fall, precision must not.
- **D-06:** **Depth cap 4 for sacrifice and clearance only** (named constant). Other
  tier-3 motifs keep the full-line scan (deflection's deep hits are mostly real).
- **D-07:** **Clearance: strengthen, then bar.** Add to cook's predicate: the vacating
  (prior pov) move is not a king or pawn move; the ray piece's clearing move *uses* the
  line (gives check, or attacks a higher-value or hanging opponent piece from its new
  square); depth cap (D-06); winning floor (D-01). Measure on the fixture and on the
  real-game set. **Keep only if real-game precision ≥ 0.8; otherwise suppress** (remove
  from the shipped families and the frontend "Advanced" group, keep the int, retag clears
  rows). Either outcome is recorded with numbers in the summary.
- **D-08:** **Same sacrifice rules in both orientations** (one detector, one predicate).

**Missed-orientation parity (flaws_service.py)**

- **D-09:** The missed pass builds `board_before` from `fen_map[n-1]` plus the opponent's
  previous move (`positions[n-1].move_san`) so the move stack carries it exactly like the
  allowed pass carries the flaw move. Unblocks intermezzo at k=2 on missed lines.
- **D-10:** **cook's hanging-piece recapture exclusion applies on the missed side too**
  (a recapture is not a "hanging piece"; "you didn't recapture" is a different message,
  out of scope). Parity with the allowed pass and with cook; the 33/302 dev rows become
  NULL.
- **D-11:** **Discovered-attack depth = k** (move index, like skewer), not k−1. Accept the
  consequences: same-k forks/skewers now beat it on the tier tiebreak, the UI difficulty
  shifts one ply deeper, the WR-02 hand-confirmed fixture is re-tuned, and the full retag
  removes all odd stored depths. — **Reversibility:** costly — reverting after the retag
  means another full prod retag.

**Port fixes (fixture-verified against the oracle comparison)**

- **D-12:** Deflection promotion branch restored to cook's OR (`square ∈ attacks(orig)` OR
  the promotion same-file clause). Fork's D-01 relevance gate removed (not cook; −130
  detections for no precision). Trapped-piece empty-escape exclusion reverted (cook:
  immobile attacked piece ⇒ trapped; 0 new FPs). Discovered-attack returns (not
  continues) on a recapture. Boden/double-bishop file edge aligned. `self-interference`
  removed from `_TIER3_REGISTRY` (int 14 and the detector function kept for existing
  rows/tests; the retag clears persisted 14s).

**Real-game gate & rollout**

- **D-13:** **Real-game labelled set:** ~150 prod tags stratified by motif × orientation,
  sampled *before* the fixes so before/after is scored on identical inputs; each row
  carries game_id, ply, orientation, full FEN, PV, blob eval at firing, motif, depth,
  label ∈ {real, incidental, wrong}, rationale. Stored in
  `fixtures/tagger/realgame_tags.csv` (no live prod dependency in tests). **Claude labels
  all rows; the operator spot-checks ~20** (recorded in the summary). Scored by
  `scripts/tactic_tagger_report.py` (per-motif real-share, before/after) and **CI-asserted
  per motif** in `tests/scripts/tagger/test_detector_precision.py` with floors set from
  the post-fix measurement (D-09 style, never-regress).
- **D-14:** **One release, one retag.** All detector and gate changes land in one
  squash-merge; after `/deploy`, `scripts/retag_flaws.py --db prod` runs as a **full
  refresh (no `--only-tagged`)** from the local box through `bin/prod_db_tunnel.sh` (the
  same read-write path Phase 220 used; the Phase 143/145 "tunnel is read-only" note is
  stale). Writes the per-motif removed/survived/shifted report under `reports/retag/`; the
  TAGFIX-09 acceptance queries are pasted into the summary. Dev retag first as the smoke.

### Claude's Discretion

- Exact placement of the tier→floor map and the eval-reading helper (gate module vs
  flaws_service), as long as the single classify path (SC4) is preserved.
- The precise "attacks a higher-value or hanging piece" helper for clearance (reuse
  `_is_defended` / `_PIECE_VALUES`).
- Sampling mechanics for the real-game set (SQL + a small script under `scripts/research/`).
- Floor values in `precision_floors.py` after re-measurement; new fixture rows for the
  fast-guard tests.

### Deferred Ideas (OUT OF SCOPE)

- "You missed a recapture" as its own coaching signal (distinct from hanging-piece) —
  new capability, not this phase.
- Multi-label / co-tag storage so sacrifice can coexist with the shallower motif that
  wins dispatch — rejected in Phase 133, still out of scope.
- Re-scoring `discovered-check` against a label source other than cook (lila-side /
  crowd) — documented only (TAGFIX-08).
- Per-motif floors for deflection / intermezzo / promotion beyond the tier split — revisit
  with the real-game gate numbers after this phase.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TAGFIX-01 | Solver-winning floor at the firing node (per-tier, blob + `game_positions` fallback) | § Implementation Map 1; `forcing_line_gate.py:289-305` (`_is_forced_mate_firing` — the node-read pattern to clone), `:385-461` (public orchestrator), `tactic_detector.py:2352-2418` (tier registries the map keys on). Import-graph check: no cycle either direction. |
| TAGFIX-02 | Gate never skipped when `pre_flaw_eval_cp` is None | § Implementation Map 2; the skip branch is the single `and pre_flaw_eval_cp is not None` at `flaws_service.py:609`; `_pov_mate` at `:215-220`, `_solver_color_for` at `:543-558`. |
| TAGFIX-03 | `detect_sacrifice` persistence + depth cap | § Implementation Map 3; `tactic_detector.py:2183-2213`; measured effect in § Measured Simulation (TP 409→177, FP 0, P 1.000). |
| TAGFIX-04 | Clearance strengthen-or-suppress with a real-game bar | § Implementation Map 4; `tactic_detector.py:1985-2070`; suppression blast radius in § Clearance Suppression Checklist (7 files). |
| TAGFIX-05 | Seven fixture-verified port fixes | § Implementation Map 5 — one exact line anchor per fix; D-11's single flipping fixture identified by experiment (§ Measured Simulation). |
| TAGFIX-06 | Missed-orientation parity (move stack + recapture exclusion) | § Implementation Map 6; `flaws_service.py:466-520`; `fen_map[n-1] + positions[n-1].move_san` index proof in § Pitfall 1. |
| TAGFIX-07 | Real-game gate CSV + scoring + CI floor | § Implementation Map 7; fixture CSV shape at `fixtures/tagger/detector_fixture_train.csv`; scorer seam `tactic_tagger_report.py::_score` / `test_detector_precision.py::_compute_metrics`; sampling SQL verified on dev (§ Sampling Mechanics). |
| TAGFIX-08 | Harness hygiene + `scripts/research/` relocation | § Implementation Map 8; **39 ruff findings measured** on the two scripts as-is (§ Pitfall 7). |
| TAGFIX-09 | Prod retag + acceptance + CHANGELOG | § Implementation Map 9; retag report gaps (dry-run-only, no "shifted"); acceptance SQL run on dev this session (§ Acceptance Instrument). |
</phase_requirements>

---

## Project Constraints (from CLAUDE.md)

Directives that bind this phase; the planner must not produce tasks that contradict them.

| Constraint | Where it bites in Phase 221 |
|---|---|
| **No magic numbers** — every threshold a named constant with provenance in its comment | The two tier floors, the sacrifice/clearance depth cap, the clearance "higher value" delta. Follow the existing style in `forcing_line_gate.py:57-92` (multi-paragraph provenance comments). |
| **Never bare `str` for a fixed set** — use `Literal[...]` | The new real-game label column is `Literal["real", "incidental", "wrong"]`, not `str`. Orientation is already `Literal["allowed","missed"]`. |
| **`uv run ty check app/ tests/ scripts/` zero errors** | `scripts/research/*.py` lands inside the checked tree — see Pitfall 7. Suppress only with `# ty: ignore[rule-name]`; `unused-ignore-comment = "warn"` (`pyproject.toml:168-170`) means a stale ignore is itself a finding. |
| **Comment bug fixes at the fix site** | Each of the seven port fixes replaces an existing wrong-but-commented line; the comment must be rewritten, not left describing the old behaviour (e.g. the WR-02 block at `tactic_detector.py:886-892` becomes obsolete the moment D-11 lands). |
| **Nesting depth hard 4, logic LOC hard 200** | `check_function_size.py app/` reports **OK, no breaches** today across all 705 app functions (measured this session), so there is headroom — but `detect_clearance` (already 4 nested levels inside a `for`) and `_classify_tactic_gated` are the two that grow. See § Function-Size Headroom. |
| **No `asyncio.gather` on one `AsyncSession`** | The sampling script and the retag both use one session per worker; `retag_flaws.py` already does the right thing (DB in the parent, CPU in spawn workers). |
| **Sentry: `capture_exception` in non-trivial excepts, never variables in messages** | New sampling / research scripts are analysis-only and may skip Sentry; any change inside `app/services/` must not swallow a new exception silently. |
| **No `bin/reset_db.sh`** | Explicit in CONTEXT and in the `no-dev-db-reset-in-plans` memory note. The dev retag smoke runs against the existing dev DB. |
| **GitLab Flow / one squash-merge** | D-14: all detector + gate changes in a single squash-merge; the prod retag happens after `/deploy`. |
| **Pre-merge gate is mandatory but INCOMPLETE here** | It does not include `pytest tests/scripts/tagger`. Add that command to every plan's verification block. |

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Motif predicates (sacrifice, clearance, fork, …) | Pure-Python service (`tactic_detector.py`) | — | No I/O, no DB; the only imports are `enum`, `typing`, `chess` (verified `tactic_detector.py:31-36`). Keeps it unit-testable and fixture-scorable offline. |
| Solver-winning floor / only-move gate | Pure-Python service (`forcing_line_gate.py`) | — | Same posture: stdlib + `eval_utils` only. The floor belongs here, not in the detector — it is a property of the *line*, not of the geometry. |
| Tier→floor mapping | Service (`tactic_detector.py`, next to the registries) | Gate imports it | D-01 requires it "next to the dispatcher's tier registry". Direction `gate → detector` is safe; `detector → gate` would create a cycle if the detector wanted `STILL_WINNING_FLOOR_CP`. |
| Blob-missing eval fallback | Service (`flaws_service.py::_classify_tactic_gated`) | — | It is the only layer that holds both `positions` and the blob. Putting it in the gate would force the gate to know about `GamePosition`, breaking its "no DB types" property. |
| Persisted tag columns | Repository (`game_flaws_repository.bulk_update_tactic_tags`) | — | Already the single write seam used by the re-tagger. |
| Family → motif-int mapping (chip surface) | Repository (`library_repository.FAMILY_TO_MOTIF_INTS`) | Frontend `tacticComparisonMeta.ts` mirrors the keys | Cross-stack string contract asserted by `test_family_mapping_ten_families`. |
| Offline re-derivation at prod scale | Script (`scripts/retag_flaws.py`) | DB | Keyset paging + spawn workers + change-only UPDATE already built. |
| Fixture + real-game scoring | Test harness (`tests/scripts/tagger/`) + `scripts/tactic_tagger_report.py` | — | The report script imports the harness modules so CI and the report can never disagree. |

**Assignment sanity check:** no capability in this phase belongs to the frontend tier. The only
frontend touch is the conditional clearance suppression (copy + one type union entry), which is a
presentation concern and correctly sits there.

---

## Standard Stack

**No new packages. No package installs. No `Package Legitimacy Audit` section is required for this
phase** — the phase adds zero external dependencies. Everything below is already in `pyproject.toml`
and in the lockfile.

### Core (already present)
| Library | Version | Purpose | Why standard |
|---------|---------|---------|--------------|
| `python-chess` | 1.11.x (per CLAUDE.md) | Board replay, `SquareSet.between`, `attacks`, `attackers`, `is_pinned` | Already the detector's only third-party import `[VERIFIED: app/services/tactic_detector.py:36]` |
| `SQLAlchemy` (async) + `asyncpg` | 2.x | Keyset-paged retag, sampling queries | `scripts/retag_flaws.py:114-116` |
| `pytest` | — | Fixture gate + unit tests | `pyproject.toml:76-86` |
| `ruff` / `ty` | `>=0.4.0` / `>=0.0.26` | Pre-merge gate | `pyproject.toml:33-34` |

### Alternatives considered
| Instead of | Could use | Tradeoff |
|------------|-----------|----------|
| Hand-labelled real-game CSV (TAGFIX-07) | Extend the CC0 puzzle fixture | Rejected upstream: § 3 of the review proves the puzzle fixture is structurally blind to losing lines, capped PVs and non-forcing tails. A different *puzzle* set cannot see the failure class. |
| Adding `motif_int` as a required gate param | A separate `check_winning_floor()` called by `_classify_tactic_gated` | Viable, and arguably cleaner (keeps `apply_forcing_line_filter`'s signature frozen), but splits the gate decision across two call sites and breaks the "gate is one pure function" property the module docstring advertises. Recommend the defaulted-kwarg form. |

---

## Architecture Patterns

### System architecture — the tag write path

```
                        ┌───────────────────────── inputs ─────────────────────────┐
   game PGN ──► _recompute_fen_map ──► fen_map{ply: full FEN}                       │
   game_positions[ply] ──► move_san / pv / eval_cp / eval_mate                      │
   game_flaws[ply] ──► allowed_pv_lines / missed_pv_lines (JSONB list[PvNode])      │
                        └──────────────────────────────────────────────────────────┘
                                              │
             ┌────────────────────────────────┴────────────────────────────────┐
             │  _classify_tactic_gated(n, fen_map, positions, orientation,     │
             │                         pv_blob, pre_flaw_eval_cp, margin, …)   │  ← SC4 single path
             └────────────────────────────────┬────────────────────────────────┘
                                              │
                   ┌──────────────────────────┴──────────────────────────┐
                   │                                                     │
         _detect_tactic_for_flaw(orientation)               apply_forcing_line_filter(blob, …)
                   │                                                     │
      ┌────────────┴────────────┐                    ┌───────────────────┴───────────────────┐
  allowed: board_before          missed: board_before  D-08 already-winning reject             │
          + push(flaw move)       (TODAY: bare FEN,    D-09 conversion-tail truncation          │
                                   NO move stack)      D-10 trailing-strip + one-mover discard  │
                   │                     ▲             D-07 only-move at every solver node      │
                   │                     └── TAGFIX-06 fix: fen_map[n-1] + push(prev move)      │
                   │                                   ★ TAGFIX-01 NEW: winning floor @ firing  │
                   ▼                                                                            │
          detect_tactic_motif  ──► Tier1 mates (short-circuit)                                  │
                                   Tier2 geometric ─┐                                           │
                                   Tier3 fuzzy ─────┼─► depth-primary winner                    │
                                   Tier4 hanging ───┤   (_select_shallowest_candidate)           │
                                   Tier5 move-type ─┘   ★ D-11 changes DA's depth key            │
                                              │                                                 │
                                              └──────────────► (motif, piece, conf, depth) ──────┘
                                                                        │
                                    ┌───────────────────────────────────┴───────────────────────┐
                     4 callers of _classify_tactic_gated (all must stay identical):
                       1. flaws_service._build_flaw_record      (live drain, FULL positions)
                       2. routers/eval_remote.py:1044/1047      (remote submit, FULL positions)
                       3. scripts/retag_flaws.py:318/327        (offline retag, ★SPARSE positions)
                       4. scripts/ab_validate_gate.py:434/443   (A/B tool, FULL positions)
                                                                        │
                                                   bulk_update_tactic_tags ──► game_flaws (8 cols)
```

### Implementation map — one block per requirement

#### 1. TAGFIX-01 — solver-winning floor at the firing node

**Current signatures (read this session):**

```python
# app/services/forcing_line_gate.py:385
def apply_forcing_line_filter(
    line: Sequence[PvNode],
    solver_color: Literal["white", "black"],
    pre_flaw_eval_cp: int,
    firing_depth: int | None = None,
    margin: float = ONLY_MOVE_WIN_PROB_MARGIN,
) -> bool:
```

```python
# app/services/forcing_line_gate.py:95 — PvNode (all cp values WHITE-perspective)
class PvNode(TypedDict):
    b: int | None    # best_cp, None when the best move is a forced mate
    bm: int | None   # best_mate, +ve = white mates
    s: int | None    # second_cp
    sm: int | None   # second_mate
    su: str          # second-best move UCI, "" when none
```

**The node-read pattern to clone** (`forcing_line_gate.py:289-305`) — note it does **not** round
the index; it reads `line[firing_depth]` directly and documents the slim-blob degradation:

```python
def _is_forced_mate_firing(line, solver_color, firing_depth) -> bool:
    idx = firing_depth if firing_depth is not None else 0
    if idx < 0 or idx >= len(line):
        return False
    bm = line[idx]["bm"]
    return bm is not None and eval_mate_to_expected_score(bm, solver_color) == 1.0
```

**The floor helper is its sibling.** Recommended shape (matches the module's one-rule-one-function
discipline, keeps nesting at 2):

```python
def _solver_cp_at_firing(line, solver_color, firing_depth) -> tuple[int | None, int | None]:
    """Return (solver_mate, solver_cp) at the firing node, rounding odd depths UP to the
    solver node (odd index = defender ply; the solver node that produced it is idx+1).
    `bm` is checked before `b` (D-01)."""
    idx = 0 if firing_depth is None else firing_depth + (firing_depth % 2)
    if idx < 0 or idx >= len(line):
        return None, None
    node = line[idx]
    bm = node["bm"]
    if bm is not None:
        return (bm if solver_color == "white" else -bm), None
    b = node["b"]
    if b is None:
        return None, None
    return None, (b if solver_color == "white" else -b)
```

Solver perspective is derived exactly as everywhere else in the module: `cp if solver_color ==
"white" else -cp` (`forcing_line_gate.py:135, 271, 355`), and for mates via
`eval_mate_to_expected_score(bm, solver_color) == 1.0`.

**Where the tier→floor map lives.** Import-graph facts (verified this session):

- `app/services/tactic_detector.py` imports **only** `enum`, `typing`, `chess` — zero app imports.
- `app/services/forcing_line_gate.py` imports **only** `typing` + `app.services.eval_utils`.
- `app/services/eval_utils.py` imports `math`, `datetime`, `typing`, `app.core.config`.

So `forcing_line_gate → tactic_detector` is **cycle-free**, and `tactic_detector →
forcing_line_gate` is *also* cycle-free today. Two viable placements:

| Option | Shape | Cost |
|---|---|---|
| **(a) recommended** — map in `tactic_detector.py` beside the registries (`:2352-2418`), with its own named floor constants; gate imports `floor_cp_for_motif(motif_int) -> int \| None` | Honours D-01's "next to the registry" literally; no private cross-module imports; the map can be *derived* from `_GEOMETRIC_REGISTRY` / `_TIER3_REGISTRY` / `_MOVE_TYPE_REGISTRY` / `MATE_MOTIFS` so it cannot drift | The `+200` value is duplicated from `STILL_WINNING_FLOOR_CP`; mitigate with an explicit comment cross-referencing it (they are conceptually the same lichess-puzzler `cook_advantage` constant) |
| (b) map in `forcing_line_gate.py`, importing the registries from the detector | Floor constants stay next to `STILL_WINNING_FLOOR_CP` | Imports three private `_*_REGISTRY` names across modules, or requires making them public |

Either way, **add the parameter as a defaulted keyword**:

```python
def apply_forcing_line_filter(..., margin=ONLY_MOVE_WIN_PROB_MARGIN, motif_int: int | None = None) -> bool:
```

so the ~50 existing positional/keyword call sites in `tests/services/test_forcing_line_gate.py`,
`tests/services/test_eval_drain.py` and `scripts/ab_validate_gate.py` keep working unchanged.

**Post-D-11, odd firing depths are nearly extinct.** Dev DB measurement this session:
discovered-attack (int 6) has **226/226 allowed rows with odd depth**; the only other odd-depth
rows are 63 generic-mate (int 8) rows from the Phase-148 truncated-mate fallback
(`depth = len(moves) - 1`, `tactic_detector.py:2470-2478`). Mate motifs are floor-exempt, so after
D-11 the rounding rule is almost a no-op — implement it anyway for correctness, and say so in the
docstring.

**D-03 fallback — exactly which position to read:**

| Orientation | Fallback source | Why | Solver perspective |
|---|---|---|---|
| `allowed` | `positions[n]` (`eval_cp` / `eval_mate`) | `positions[N].eval_cp` is the eval **AFTER** move N (`flaws_service.py:359-370`, the "eval-AFTER landmine"), i.e. the position after the flaw, refuter to move | `_solver_color_for(n, "allowed")` = `"black" if n % 2 == 0 else "white"` |
| `missed` | `positions[n-1]` | eval after move n−1 = the board before the flaw move, mover to move | `_solver_color_for(n, "missed")` = `"white" if n % 2 == 0 else "black"` |

#### 2. TAGFIX-02 — the gate is never skipped for a None `pre_flaw_eval_cp`

The skip is a single conjunct. `flaws_service.py:604-616` (verbatim):

```python
    if (
        motif is not None
        and pv_blob is not None
        and len(pv_blob) > 0
        and pre_flaw_eval_cp is not None      # ← line 609, TAGFIX-02 removes this
    ):
        solver_color = _solver_color_for(n, orientation)
        if not apply_forcing_line_filter(
            pv_blob, solver_color, pre_flaw_eval_cp, firing_depth=depth, margin=margin
        ):
            return None, None, None, None
```

Because `apply_forcing_line_filter`'s third parameter is typed `int` (not `int | None`), dropping
the guard means the caller must supply *something*. Two sub-decisions the plan must make explicit:

- Widen to `pre_flaw_eval_cp: int | None` and add `pre_flaw_eval_mate: int | None = None`, with
  `_is_already_winning` becoming a two-branch helper (mate-for-solver ⇒ reject; else cp compare;
  both `None` ⇒ no already-winning reject, gate continues); **or**
- Keep the `int` type and pass `0` when cp is absent, carrying the mate signal separately. Less
  honest; the `0` would read as "equal position" to any future rule.

Recommend the first. `_pov_mate` already does the perspective conversion
(`flaws_service.py:215-220`):

```python
def _pov_mate(pos: GamePosition, mover_color: Literal["white", "black"]) -> int | None:
    if pos.eval_mate is None:
        return None
    return pos.eval_mate if mover_color == "white" else -pos.eval_mate
```

so `_pov_mate(positions[n-1], _solver_color_for(n, orientation)) > 0` is "the solver had a forced
mate before the flaw" ⇒ already winning ⇒ reject (D-04), with mate-motif tags exempt exactly as the
existing `forced_mate` exemption at `forcing_line_gate.py:441` does.

**Sentinels that must not change** (docstring `flaws_service.py:577-602`):
- `pv_blob is None` (pre-Phase-142 rows) → gate skipped, raw result returned.
- `pv_blob == []` (D-06 "could not assemble") → gate skipped; this is a FINAL case.
- `blobs_pending=True and motif is not None and pv_blob is None and pre_flaw_eval_cp is not None`
  → suppress to NULL (`flaws_service.py:618`). **This line reads `pre_flaw_eval_cp is not None`
  too** — it is the "mate-adjacent is a FINAL case, never suppressed by blobs_pending" carve-out.
  TAGFIX-02 changes the gate skip but the CONTEXT says "the `blobs_pending` … behaviours are
  unchanged", so line 618 must keep its semantics even if the variable it keys on changes shape.
  Flag this as a review point: it is easy to "clean up" both lines together and silently change
  the blobs_pending contract that `tests/services/test_flaws_service.py:2801-2897`
  (`TestClassifyTacticGatedBlobsPending`, 4 tests) pins.

#### 3. TAGFIX-03 — sacrifice persistence + depth cap

`tactic_detector.py:2183-2213` (the whole predicate; the loop body is 6 lines):

```python
    if any(m.promotion for m in moves[1::2]):
        return False, None, 0, None
    initial = _material_diff(boards[0], pov)
    for k in range(2, len(moves), 2):
        if k + 1 >= len(boards):
            break
        diff_after = _material_diff(boards[k + 1], pov)
        if diff_after - initial <= -MIN_SACRIFICE_DROP:      # ← line 2210
            return True, None, TACTIC_CONFIDENCE_HIGH, k
```

D-05 inserts the persistence test on `boards[k+3]` **before** returning; D-06 caps `k`. The cook↔ours
index convention (`.planning/notes/tactic-tagger-cook-alignment.md`, "Index convention" table)
makes `boards[k+3]` unambiguous:

| index | meaning |
|---|---|
| `moves[k]` | this pov move (even k) |
| `boards[k]` | board **before** this pov move |
| `boards[k+1]` | board **after** this pov move ← where the deficit is measured today |
| `moves[k+1]` | the opponent's reply |
| `boards[k+2]` | board after the opponent's reply |
| `moves[k+2]` | **the next pov move** |
| `boards[k+3]` | board **after the next pov move** ← D-05's persistence board |

"or the line must end before that board" ⇒ `if k + 3 < len(boards): <check>` else accept.

Note `MIN_SACRIFICE_DROP: int = 2` already exists (`tactic_detector.py:80`) with cook provenance;
the depth cap needs a new sibling constant, e.g. `SACRIFICE_CLEARANCE_MAX_DEPTH: int = 4`
(shared with clearance per D-06).

#### 4. TAGFIX-04 — clearance strengthen or suppress

`detect_clearance` is `tactic_detector.py:1985-2070`, a 9-condition AND-chain inside
`for k in range(2, len(moves), 2)`. The three additions map onto existing local variables:

| D-07 clause | Available locals at the decision point | Suggested test |
|---|---|---|
| vacating move is not a king or pawn move | `prev_move = moves[k-2]`, `init_board = boards[k-2]` | `init_board.piece_type_at(prev_move.from_square) not in (chess.KING, chess.PAWN)` |
| the clearing move **uses** the line | `board_after = boards[k+1]`, `move.to_square` | `board_after.is_check()` **or** a new helper over `board_after.attacks(move.to_square)` |
| depth cap | `k` | `if k > SACRIFICE_CLEARANCE_MAX_DEPTH: break` |

Reusable helpers for the "attacks a higher-value or hanging piece" clause (all already ported
faithfully from cook, AGPL-clean):

- `_PIECE_VALUES` (`:45-57`, KING=99) and `_VALUES_NO_KING` (`:59-66`)
- `_is_defended(board, piece, sq)` — **ray-aware** (`:291-316`); `not _is_defended(...)` is the
  project's "hanging" test
- `_is_in_bad_spot(board, sq)` (`:318-344`)

Mirror `detect_fork`'s victim loop (`:425-445`) exactly so the two predicates stay stylistically
identical and equally reviewable.

**Function-size warning:** `detect_clearance` already runs `for → if(cond1) … if(cond7) → if(inner)`
= depth 3 inside the function body. Adding a victim loop inside the `for` reaches depth 4 (the hard
cap). Extract the "line is used" test into a module-level helper
(`_clearance_line_is_used(board_after, dest, pov) -> bool`), the same way
`_clearance_prior_move_is_valid` (`:1968-1983`) and `_deflection_fires_at` were extracted.
`scripts/check_function_size.py app/ --fail-over-depth 4 --fail-over-loc 200` reports **OK across
all 705 app functions today** (measured this session), so any breach introduced here is
attributable to this phase.

#### 5. TAGFIX-05 — the seven port fixes, with exact anchors

| # | Fix | Anchor (verified this session) | Current text | Change |
|---|---|---|---|---|
| 1 | Deflection promotion OR-branch | `tactic_detector.py:1574-1580` | `if is_promotion: … if not (same_file and pov_attacks_from_init): return None` / `elif square not in grandpa_board.attacks(orig_sq): return None` | cook: `square in attacks(orig)` **OR** `(is_promotion and same_file and pov_attacks_from_init)`. Expected +297 detections (review §4). |
| 2 | Remove fork's D-01 relevance gate | `tactic_detector.py:407-408` | `if i > 0 and material_at_end < material_at_start:` `    continue` | delete both lines (and the `material_at_start` / `material_at_end` locals at `:399-400` if unused afterwards) + the docstring paragraph at `:389-393`. Expected +130. |
| 3 | Revert trapped-piece empty-escape exclusion | `tactic_detector.py:951-954` | `# Empty-escape-set exclusion (D-06 precision-first): no moves → not trapped.` / `if not escape_moves: return False` | cook: immobile attacked non-pawn/non-king ⇒ trapped ⇒ `return True` (the Gate-5 fallthrough already returns True on an empty loop, so **deleting the early return is sufficient**). Update the docstring block at `:920-925`. Expected +107, 0 new FPs. |
| 4 | Discovered-attack `return` on recapture | `tactic_detector.py:851-853` | `op = moves[k - 1]` / `if op.to_square == capture_sq:` / `    continue` | `return False, None, None`. **Do not touch the visually identical line at `:720`** — that one is inside `detect_skewer` and is correct there. Expected −16 FPs. |
| 5 | Discovered-attack depth = k | `tactic_detector.py:893` | `return True, capturer.piece_type, max(0, k - 1)` | `return True, capturer.piece_type, k`; delete/replace the WR-02 comment block at `:886-892` and the slim-blob paragraph in `forcing_line_gate.py:299-305` that exists only because of it. |
| 6 | Boden / double-bishop file edge | `tactic_detector.py:1411-1418` | `if (b1_file < king_file) != (b2_file < king_file): return "boden-mate"` | The edge is a bishop sitting **on** the king's file: `b_file < king_file` is False for both "same file" and "right of file", so a same-file bishop is bucketed right. cook's rule is "opposite sides", which a bishop on the file satisfies for neither. Expected: 6 rows move double-bishop → boden. Both motifs are Tier-1 mates and both map to the `mate` family (`library_repository.py:153-163`), so this is cosmetic for the UI but required for oracle parity. |
| 7 | `self-interference` out of dispatch | `tactic_detector.py:2379` (registry entry) | `("self-interference", TacticMotifInt.SELF_INTERFERENCE),` | Remove the tuple from `_TIER3_REGISTRY`. **Keep** `TacticMotifInt.SELF_INTERFERENCE = 14` (`:105`), `_INT_TO_MOTIF[14]` (`:181`), `detect_self_interference` (`:1918`) and the `_TIER3_DETECTOR_FNS["self-interference"]` entry — or remove that dict entry too; the dispatcher only iterates the *registry* (`:2504-2509`), so the dict entry is inert either way. Existing tests that must still pass: `test_all_29_motifs_encoded` (`test_tactic_detector.py:1635-1639`), `test_suppressed_motifs_documented_and_storable` (`:1731`), `test_family_mapping_excludes_suppressed_tier3` (`test_tactic_comparison_service.py:201-218`, asserts int 14 is unmapped). |

#### 6. TAGFIX-06 — missed-orientation parity

`flaws_service.py:466-472` (verbatim) is where the missed board is built today:

```python
    board_before = chess.Board(fen_before_flaw)
    board_before.turn = chess.WHITE if n % 2 == 0 else chess.BLACK

    if orientation == "missed":
```

`fen_before_flaw = fen_map.get(n, "")` (`:461`). Because `fen_map[k]` is the board **after k
half-moves** (`_recompute_fen_map`, `:321-353`: `fens = {0: board.fen()}` then
`fens[ply] = board.fen()` after each push), the D-09 construction is:

```python
prev_fen = fen_map.get(n - 1, "")
prev_san = positions[n - 1].move_san if 1 <= n < len(positions) else None
if n >= 1 and prev_fen and prev_san:
    try:
        b = chess.Board(prev_fen)
        b.push(b.parse_san(prev_san))       # b is now the pre-flaw position WITH a move stack
        board_before = b
    except ValueError, chess.IllegalMoveError:
        pass                                 # fall back to the stackless build
```

`positions[k].move_san` is the move played **from** ply k (`_build_flaw_record`, `:625-628`), so
`positions[n-1].move_san` lands on ply n. The resulting board is byte-identical in position to
`chess.Board(fen_map[n])` **plus** a one-move stack — exactly what `build_detector_board`
(`tests/scripts/tagger/conftest.py:68-90`) reproduces for the fixture harness.

Two consumers become live on the missed side (review §2.5):
- `detect_intermezzo`'s k=2 branch (`tactic_detector.py:1750-1757`) reads `boards[0].move_stack`
  and currently `return False` when it is empty.
- `detect_hanging_piece`'s recapture exclusion (cook's `values[op_capture] >= values[captured]`),
  which D-10 says must now apply. Dev: 33 of 302 missed hanging-piece rows are plain recaptures.

**Do not drop the existing `board_before.turn` override.** The docstring at `:463-468` calls it
defense-in-depth against a partial/legacy `fen_map` entry; the D-09 path should apply the same
assertion after the push.

**Ordering caution:** the `_same_dest_as_best_line` dest-square gate (`:485-490`) parses the flaw
SAN against `board_before`. Pushing the *previous* move onto that board does not change the
position, so `parse_san` still resolves identically — but the plan should keep the gate reading the
same board object to avoid a subtle SAN-disambiguation difference.

#### 7. TAGFIX-07 — the real-game gate

**Existing CSV shape** (`fixtures/tagger/detector_fixture_train.csv`, header verified):
`PuzzleId,FEN,PreFlawFEN,FirstMove,PV,Themes,Rating`.

**Recommended `realgame_tags.csv` header** (the detector needs the same three inputs the fixture
gives it: a pre-flaw FEN, the move to push, and the PV):

```
row_id,game_id,ply,orientation,pre_flaw_fen,push_move_uci,pv,motif,depth,solver_color,eval_at_firing,label,rationale
```

- `push_move_uci` = the flaw move for `orientation="allowed"`, the opponent's previous move for
  `orientation="missed"` (post-D-09 both orientations push something).
- `label ∈ {real, incidental, wrong}` — a `Literal`, not `str` (CLAUDE.md).
- `eval_at_firing` is a frozen snapshot of the blob read (a string like `M4` / `-320`), so the CSV
  is self-contained and the test never touches a DB.

**The scoring seam.** Both scorers share one shape (`test_detector_precision.py:_compute_metrics`,
`tactic_tagger_report.py:_score`): build the board, call `detect_tactic_motif`, map the int back via
`_INT_TO_MOTIF`, then per-motif TP/FP/FN. For the real-game table:

- **TP** = row's stored `motif` is re-detected **and** `label == "real"`.
- **FP** = re-detected **and** `label in {"incidental", "wrong"}`.
- Rows whose motif disappears after the fixes are *removals*, not FNs — report them in a third
  column ("suppressed"), because a suppressed incidental row is a **win**, not a miss. Do not reuse
  the puzzle harness's FN semantics here; it will read backwards.
- Real-share per motif = `real_surviving / surviving`, and the CI floor asserts on that.

**Where the floor lives:** a new dict beside `PRECISION_FLOOR` in `precision_floors.py` (e.g.
`REALGAME_REAL_SHARE_FLOOR: dict[str, float]`), asserted in a new test function in
`test_detector_precision.py` so the existing `test_detector_precision_and_recall` keeps its single
responsibility. Both run in the CI "Tagger precision gate" step.

#### 8. TAGFIX-08 — harness hygiene + `scripts/research/`

`scripts/research/` **does not exist yet** (verified). Creating it puts the two scripts inside the
tree that `ruff check .`, `ruff format --check … scripts/` and `ty check … scripts/` all cover
(`.github/workflows/ci.yml:83-90`). Measured cost of moving them as-is: **39 ruff errors** and **2
ty diagnostics** (the `import cook` / `from model import Puzzle` unresolved-imports). See Pitfall 7
for the required cleanup pattern.

For `precision_floors.py`, TAGFIX-08 adds two documentation blocks to the module docstring: the
`discoveredCheck`-labels-are-not-cook fact (review §3: cook's `TagKind` lacks the theme; only 1,585
of 2,854 labelled rows satisfy `cook.discovered_check`), and an "oracle comparison exists / what
'matches cook' means per motif" note so a future precision pass does not re-introduce the fork D-01
gate or the trapped-piece exclusion.

#### 9. TAGFIX-09 — prod retag + acceptance

**What `scripts/retag_flaws.py` already gives you:**

| Capability | Where | Notes |
|---|---|---|
| `--db {dev,benchmark,prod}` | `:178-184` | prod = `DATABASE_URL_PROD` = `localhost:15432` (`app/core/config.py:28`), i.e. through `bin/prod_db_tunnel.sh` (`LOCAL_PORT=15432`, `ssh -fN -L`) |
| Keyset paging on `(user_id, game_id, ply)` | `:404-409` | resumable, index-backed |
| Spawn worker pool, DB in parent only | `:690-707` | `--workers`, `--throttle-ms` |
| Change-only batched UPDATE | `:446-468` + `bulk_update_tactic_tags` | no-op rows skipped (no WAL) |
| `--only-tagged`, `--limit`, `--dry-run`, `--margin` | `:186-243` | D-14 requires **omitting** `--only-tagged` |
| Per-motif removed/survived report | `:521-618` | ⚠ **dry-run only**, ⚠ **no "shifted" bucket** |

**Gaps the plan must close in code:**

1. Write the delta report on the real run too (today `if dry_run:` at `:800`), and rename the
   "Mode" line accordingly.
2. Add a **shifted** counter to `_accumulate_motif_counts` (`:470-528`): `old is not None and new
   is not None and old != new`. D-11 alone will shift every discovered-attack row's *depth*; a
   motif shift happens when a same-k fork/skewer now beats it on the tier tiebreak. Consider a
   fourth counter for depth-only shifts, since the acceptance criterion "zero rows with an odd
   stored depth for motif 6" is a depth claim.
3. Fix the stale docstring at `:74-76` — *"T-143-05: `--db prod` writes require running on the prod
   server. The local SSH tunnel (`bin/prod_db_tunnel.sh`) is read-only."* Phase 220 ran writes over
   the tunnel from the local box (`220-06-SUMMARY.md:45`: "screen 2.57M rows in 10h48m (pool 28
   over the tunnel); … propagate 4,097 hashes / 11,286 cells in 7 min"). D-14 makes this
   correction explicit; leaving the docstring wrong would contradict the plan the next operator
   reads.
4. Set `positions[ply-1] = work.prv` in `_worker_recompute` (`:295-301`) — see § Pitfall 2.

**Motif-14 clearing:** a full refresh (no `--only-tagged`) recomputes every flaw. After
`self-interference` leaves `_TIER3_REGISTRY`, no PV can produce int 14, so every persisted 14 is
overwritten with whatever else wins dispatch (or NULL). **The dev DB has ZERO motif-14 rows**
(measured this session: `a14=0, m14=0` over 70,918 flaws), so the dev smoke **cannot** prove this
leg — only the prod acceptance query can. Call that out in the plan so nobody claims the dev run
validated it.

---

## Don't Hand-Roll

| Problem | Don't build | Use instead | Why |
|---|---|---|---|
| Reading the solver-perspective eval from a blob node | A new inline `if solver_color == "white"` block in `flaws_service` | A sibling helper in `forcing_line_gate.py` next to `_is_forced_mate_firing` (`:289`) | The module's whole design contract is "one rule, one small pure function, unit-testable with zero fixtures" (`forcing_line_gate.py:44-46`). Adding perspective logic in the service breaks the property that the gate is the single source of eval-sign truth. |
| Board-with-move-stack construction in tests | `chess.Board(fen)` | `build_detector_board(row)` (`tests/scripts/tagger/conftest.py:68`) | A bare board has an empty `move_stack`, so cook's recapture exclusion and intermezzo's k=2 branch silently never fire. This is the exact defect TAGFIX-06 fixes in production. |
| Re-deriving PVs / evals for the retag | An engine pass | `scripts/retag_flaws.py` reading `game_flaws.allowed_pv_lines` / `missed_pv_lines` | The blobs are already stored; the phase is explicitly "no MultiPV re-evaluation". |
| A second classify path for the re-tagger | Calling `_detect_tactic_for_flaw` + gate directly | `_classify_tactic_gated` | SC4 no-drift. `retag_flaws.py:126-134` documents exactly why. |
| A prod-connected test for the real-game gate | pytest fixture hitting `--db prod` | The committed `realgame_tags.csv` | D-13: "no live prod dependency in tests". Also makes before/after scored on identical inputs. |
| Ray-aware "is this piece defended" | A fresh `board.attackers(...)` check | `_is_defended` (`tactic_detector.py:291`) | It already removes the front ray attacker and re-checks — the non-ray version (`_is_hanging`, `:275`) is the documented legacy helper with known false positives. |
| Family/motif int bookkeeping for a suppression | Ad-hoc edits | Follow the Phase-134 precedent recorded in `precision_floors.py:200-221` | Seven coupled files; see the checklist below. |

**Key insight:** every heuristic this phase touches was already ported from cook.py under an
explicit AGPL boundary (prose-not-source). The failure mode to avoid is **re-inventing a
"precision-first" deviation** — the review proved that both prior deviations (fork's D-01 gate,
trapped-piece's empty-escape exclusion) cost recall for zero measured precision. TAGFIX-08's
documentation block exists precisely to stop a third one.

### Clearance suppression checklist (only if D-07's bar is missed)

1. `tests/scripts/tagger/precision_floors.py` — add `"clearance"` to `SUPPRESSED_MOTIFS`
   (`:225-247`), remove/comment its `PRECISION_FLOOR` entry (`:303`).
2. `app/repositories/library_repository.py` — delete the `"clearance"` family (`:170-172`).
3. `tests/services/test_tactic_comparison_service.py::test_family_mapping_ten_families` (`:161-200`)
   — the assertion is `set(FAMILY_TO_MOTIF_INTS.keys()) == expected_keys` with **20** keys; drop
   `"clearance"` and update the docstring count.
4. `tests/services/test_tactic_comparison_service.py::test_family_mapping_excludes_suppressed_tier3`
   (`:201-218`) — `suppressed_tier3_ints = {14}` becomes `{14, 15}`.
5. `frontend/src/lib/tacticComparisonMeta.ts` — remove `'clearance'` from the `TacticFamily` union
   (`:140`), `TACTIC_FAMILY_COLORS` (`:172`), `TACTIC_FAMILY_ICON` (`:197`), and the Advanced-group
   entry (`:380-387`); update the "19 tactic family keys" doc comment (`:117-123`) which is already
   stale at 20.
6. `frontend/src/lib/tacticMotifDefinitions.ts:44` — the `clearance` copy string.
7. Grep for unused imports afterwards (`DoorOpen`, `TAC_CLEARANCE`, `TAC_CLEARANCE_BG`) — ESLint
   will catch them, `tsc -b` will not (memory: `feedback_frontend_run_tsc_build`; run
   `npm run build` because `npm run lint` + `npm test` do **not** type-check).

**No generated file drifts.** `frontend/src/generated/` contains only `botStrengthCurves.ts`,
`endgameZones.ts`, `flawThresholds.ts`, `personaCalibration.ts` — none carries tactic families, and
no `scripts/gen_*.py` emits one (verified this session). So the CI drift gate is not in play.

---

## Runtime State Inventory

This is a **data-mutating** phase (the prod retag rewrites 8 columns on ~3.18M flaw rows). After
every file in the repo is updated, what still holds the old values?

| Category | Items found | Action required |
|---|---|---|
| **Stored data** | `game_flaws.allowed_tactic_motif / _piece / _confidence / _depth` and the four `missed_tactic_*` columns — prod ~777k allowed + ~383k missed tags (review §1), dev 5,602 + 2,722 (measured). `game_flaws.allowed_pv_lines` / `missed_pv_lines` JSONB blobs are **read-only inputs** and are NOT rewritten. | **Data migration** via `scripts/retag_flaws.py --db prod` full refresh (TAGFIX-09). Not a code-only change. |
| | Persisted `tactic_motif = 14` (self-interference) rows: prod sample suggests ~130; **dev has 0** (measured this session). | Cleared by the same full refresh. Only prod can verify. |
| | Persisted **odd** `allowed_tactic_depth` on discovered-attack: 226/226 in dev (measured), 100% per review. | Cleared by the same full refresh (D-11). |
| **Live service config** | None. No n8n workflow, Datadog tag, Tailscale ACL or Cloudflare rule references a tactic motif. | None — verified by grep over `deploy/` and the skills inventory. |
| **OS-registered state** | None. No cron/systemd/pm2 job is named after a motif; the re-tagger is an operator-run script, not a scheduled job. | None. |
| **Secrets / env vars** | None new. The retag reads `DATABASE_URL_PROD` from `.env` (never touched). | None. |
| **Build artifacts / caches** | Frontend bundle only if clearance is suppressed (the family string ships in the JS bundle). No Python package metadata, no Docker tag, no CDN-cached asset is affected (the tactic chips are data-driven, not asset-driven). | Normal deploy rebuild. |
| **Derived/aggregate tables** | `game_flaws` tactic columns feed the Library comparison grid and the Train pool via `library_repository` / `train_pool` queries at read time — **no materialised aggregate** of motif counts exists. | None — the grid recomputes from the columns. |

---

## Common Pitfalls

### Pitfall 1 — the post-move eval shift (row P = eval of P+1)

`positions[N].eval_cp` is the eval **AFTER** move N (`flaws_service.py:359-370`, and the
`atomic-eval-submit-incremental-lease` memory note). This is the exact bug class Phase 143 already
fixed once: `pre_flaw_eval_cp` used to read `positions[n]` and was corrected to `positions[n-1]`
(`flaws_service.py:643-655`, an eight-line comment explaining it). TAGFIX-01's D-03 fallback puts a
*second* eval read on this landmine, and this time the two orientations read **different** indices
(`positions[n]` allowed, `positions[n-1]` missed). Write one helper with the orientation switch
inside it and unit-test both branches; do not inline two `positions[...]` expressions.

**Warning sign:** if the allowed fallback rejects nothing while the missed fallback rejects
everything (or vice versa), the index is off by one.

### Pitfall 2 — `retag_flaws.py` builds a positions list without `ply-1`

`_worker_recompute` (`retag_flaws.py:293-301`, verbatim):

```python
    positions: list[Any] = [_EMPTY_POS] * (ply + 2)
    if work.cur is not None:
        positions[ply] = work.cur
    if work.nxt is not None:
        positions[ply + 1] = work.nxt
```

`work.prv` exists (`_FlawWork.prv`, `:267`) and `_load_positions_for_page` already fetches ply−1
with its full `move_san / pv / eval_mate / eval_cp` (`:413-442`), but it is only used to extract
`pre_flaw_eval_cp` (`:311`). So:

- The **missed** D-03 fallback would read `_EMPTY_POS` (all `None`) in the retag and a real
  `GamePosition` in the live drain → **silent divergence** between the retag and a fresh analysis.
- TAGFIX-02's `eval_mate`-at-ply-n−1 is not plumbed into the worker at all today.
- TAGFIX-06's D-09 board build needs `positions[n-1].move_san` **and** `fen_map[n-1]`. The retag's
  `fen_map` is `{ply: work.fen}` — a **single entry** (`:303-304`) — so the missed pass in the
  retag would fall back to the stackless board while production uses the stacked one. That is a
  second, independent divergence.

**Mitigation the plan must schedule as one task:** set `positions[ply-1] = work.prv` (guard
`ply >= 1`), and extend `_FlawWork` with `prev_fen: str | None` so `fen_map` can carry
`{ply-1: prev_fen, ply: fen}`. `game_flaws.fen` is *piece-placement only*
(`flaws_service.py:682-690`) whereas `fen_map` holds full FENs — so `prev_fen` must come from
`game_positions`/PGN replay, not from a second `game_flaws` row. Two workable sources: add
`GamePosition.fen`-equivalent reconstruction, or ship the previous move UCI/SAN and derive the
board by *popping* — simplest correct option is to carry `prev_move_san` + reconstruct via
`chess.Board(work.fen_full)` if a full pre-flaw FEN is available. **This is the single largest
unknown in the phase — see Open Question 1.**

There is a cheap fallback: `retag_flaws.py` could stop synthesising a positions list and instead
load the game PGN once per page and call `_recompute_fen_map`, exactly as `eval_remote.py:1029`
does. That costs one extra column on the page query (`games.pgn`) and a per-game FEN-map cache —
`dev_probe.py` already demonstrates that pattern (`fen_cache[gid] = _recompute_fen_map(r["pgn"])`).

### Pitfall 3 — `chess.Board(fen)` vs `build_detector_board`

The **fast-guard** tests in `tests/services/test_tactic_detector.py` build bare boards:
`_run_fixtures` does `board = chess.Board(fen)` (`:1579`) and `_HARD_NEGATIVES` likewise (`:1615`).
Only the CC0 harness (`tests/scripts/tagger/`) and `scripts/tactic_tagger_report.py` use
`build_detector_board`. Consequence: **new fixtures added to `test_tactic_detector.py` for the
missed-orientation parity work cannot exercise the move stack.** Either add a stack-aware fixture
tuple shape there, or put those cases in `tests/services/test_flaws_service.py` where a real
`fen_map` + `positions` are available. Memory note `project_tactic_detector_flaw_move_context`
records this exact trap.

### Pitfall 4 — the fixture gate is excluded from the default test run

`pyproject.toml:86`: `addopts = "--ignore=tests/scripts/benchmarks --ignore=tests/scripts/tagger"`.
A green `uv run pytest -n auto -x` proves **nothing** about detector precision. CI compensates with
a dedicated step (`ci.yml:136-137`), but the local pre-merge gate in CLAUDE.md does not. Every plan
touching `tactic_detector.py` must list `uv run pytest tests/scripts/tagger -q` explicitly.
Runtime measured this session: **~10 s** for the whole harness (1 test, ~17k fixture rows) — cheap
enough to run per task.

### Pitfall 5 — tagger fixture regen is NOT an option here

`scripts/select_tagger_fixtures.py` re-sampling requires the exact same ~300 MB lichess dump to stay
byte-identical (memory: `project_tagger_fixture_regen_dump_identity`; the dump is not committed).
This phase must **re-measure floors against the existing committed CSVs**, never regenerate them.
Any plan task that says "regenerate the fixture" is wrong.

### Pitfall 6 — the precision gate is scored against cook's labels, so "recall drop" is expected and fine

`precision_floors.py` floors are asserted on TRAIN only, and only on **precision**
(`test_detector_precision.py:255-268`). D-05/D-07 deliberately diverge from cook, so recall falls by
design. The failure mode is a reviewer "fixing" the recall drop by relaxing the persistence rule.
The divergence must be written into the `precision_floors.py` docstring in the same commit
(TAGFIX-03 says so explicitly).

### Pitfall 7 — moving the research scripts into `scripts/` puts them under the CI lint gate

Measured this session by copying `oracle_compare.py` + `dev_probe.py` into a scratch dir and running
the project's own config: **39 ruff errors** (`E401` multiple imports on one line, `E702` semicolons,
`E731` lambda assignment, `F401` unused imports, `E741` ambiguous names) and **2 ty
`unresolved-import` diagnostics** (`import cook`, `from model import Puzzle`). `ruff check .` scans
the whole repo (`ci.yml:84`) and `ty check app/ tests/ scripts/` covers `scripts/` (`ci.yml:90`).
Required pattern for the AGPL-clone import (also satisfies "skip cleanly when absent"):

```python
_PUZZLER = Path("/home/aimfeld/Projects/Python/lichess-puzzler/tagger")
if not _PUZZLER.is_dir():
    print("lichess-puzzler clone not found — skipping (analysis-only script).")
    raise SystemExit(0)
sys.path.insert(0, str(_PUZZLER))
import cook  # ty: ignore[unresolved-import] -- AGPL clone, present only on the analysis box
```

`ruff format --check … scripts/` also runs in CI (`ci.yml:87`), so both files must be formatted.

### Pitfall 8 — `except A, B:` is valid Python 3.14, not a bug

`flaws_service.py:419`, `:538` and `tests/scripts/tagger/conftest.py:87` all read
`except ValueError, chess.IllegalMoveError:` with no parentheses. This is PEP 758 (Python 3.14
unparenthesised except groups); `ast.parse` on the file succeeds (verified this session). Do **not**
"fix" these to tuples as part of a drive-by cleanup — it would be pure churn in a phase whose diff
should stay surgical.

### Pitfall 9 — two visually identical recapture lines

`if op.to_square == capture_sq: continue` appears at **`tactic_detector.py:720`** (inside
`detect_skewer`, correct as-is) and **`:852`** (inside `detect_discovered_attack`, the D-12 fix
target). A `sed`-style replace-all would silently break skewer, which currently measures P=1.000
train/test. Anchor the edit by function, not by string.

### Pitfall 10 — eval non-determinism means dev numbers will not match prod exactly

`eval_cp` is not reproducible across machines (memory: `project_eval_nondeterminism`), so the dev
retag delta is directionally comparable to the review's prod simulation, never numerically equal.
Success criterion 3 already phrases it as "within reason"; the plan should not assert exact counts
against dev.

---

## Code Examples

### Measured simulation — combined effect of three changes on the TRAIN fixture

Run this session with monkey-patched detectors (sacrifice persistence + depth cap 4;
discovered-attack `return`-on-recapture + depth `k`; `self-interference` removed from
`_TIER3_REGISTRY`), scored with the harness's own `_compute_metrics` logic over the committed
11,855-row TRAIN split. `[VERIFIED: measured in-session, scratch script over fixtures/tagger/detector_fixture_train.csv]`

| Motif | TP before → after | FP before → after | P before → after | R before → after | Floor | Verdict |
|---|---|---|---|---|---|---|
| **sacrifice** | 409 → **177** (−232) | 0 → 0 | 1.000 → **1.000** | 0.115 → **0.050** | 0.93 | PASS — precision held, recall drop is the intended D-05 divergence |
| **discovered-attack** | 490 → 464 (−26) | 5 → **0** | 0.990 → **1.000** | 0.260 → 0.246 | 0.93 | PASS — precision *improves*, matching the review's −16 FP prediction |
| fork | 1168 → 1182 (+14) | 3 → 3 | 0.997 | 0.563 → 0.569 | 0.93 | PASS |
| skewer | 472 → 500 (+28) | 0 → 0 | 1.000 | 0.646 → 0.684 | 0.93 | PASS |
| pin | 967 → 983 (+16) | 2 → 2 | 0.998 | 0.645 → 0.656 | 0.92 | PASS |
| intermezzo | 462 → 482 (+20) | 0 → 0 | 1.000 | 0.615 → 0.642 | 0.92 | PASS |
| promotion | 1816 → 1925 (+109) | 0 → 0 | 1.000 | 0.487 → 0.516 | 0.60 | PASS |
| en-passant | 1219 → 1230 (+11) | 0 → 0 | 1.000 | 0.622 → 0.628 | 0.93 | PASS |
| deflection | 490 → 498 (+8) | 2 → 2 | 0.996 | 0.326 → 0.331 | 0.92 | PASS |
| interference | 338 → 346 (+8) | 1 → 1 | 0.997 | 0.560 → 0.573 | 0.92 | PASS |
| under-promotion | 253 → 264 (+11) | 0 → 0 | 1.000 | 0.324 → 0.338 | 0.90 | PASS |
| attraction / capturing-defender / trapped-piece / x-ray / double-check / discovered-check | +1..+4 TP each | unchanged | unchanged | slight ↑ | — | PASS |
| clearance, hanging-piece, mate, all named mates | unchanged | unchanged | unchanged | unchanged | — | PASS |

**No floor is breached.** The TP gains on eleven motifs are the dispatch slots freed by sacrifice
and self-interference no longer stealing shallow wins — i.e. the port fixes are recall-positive for
the rest of the taxonomy, not just neutral. (This simulation did **not** include the deflection OR
branch, the fork gate removal, the trapped-piece revert or the boden edge, which the review
independently measures as +297 / +130 / +107 / 6-rows-reclassified against the oracle.)

### Measured experiment — which fixture D-11 re-tunes

Ran all 23 fast-guard fixture sets in `tests/services/test_tactic_detector.py` through the
dispatcher twice, once with discovered-attack returning `k−1` and once with `k`:

- **10 fixtures change**, all in `_DISCOVERED_ATTACK_FIXTURES`.
- **9 of them only shift depth 1 → 2**; the detected motif is unchanged.
- **Exactly 1 flips motif**: `"8/2r3pk/1p4n1/1Pb3Pp/p4P2/P3N1P1/1BP4K/4R3 b - - 0 33"` with PV
  `c5e3 e1e3 c7c2 h2h3 c2b2` goes `discovered-attack (depth 1)` → **`fork` (depth 2)**
  (`test_tactic_detector.py:465-469`).

That row is the "hand-confirmed discovered-attack fixture" the WR-02 comment
(`tactic_detector.py:886-892`) warns about. D-11 accepts the flip; the plan must re-label that
tuple (move it into `_FORK_FIXTURES`, or annotate it in place the way the two Phase-133
"Reclassified" entries at `:443-453` were).

### The acceptance instrument (§2.1), verified runnable on dev

```sql
WITH t AS (
  SELECT f.allowed_tactic_motif m, f.allowed_tactic_depth d,
         (f.ply % 2 = 1) AS solver_white,                       -- allowed: refuter is white iff ply is odd
         f.allowed_pv_lines -> (f.allowed_tactic_depth + (f.allowed_tactic_depth % 2)) AS node
  FROM game_flaws f
  WHERE f.allowed_tactic_motif IS NOT NULL
    AND f.allowed_pv_lines IS NOT NULL
    AND f.allowed_tactic_depth IS NOT NULL
), e AS (
  SELECT m, d,
    CASE WHEN node->>'bm' IS NOT NULL
         THEN (CASE WHEN solver_white THEN (node->>'bm')::int ELSE -(node->>'bm')::int END) END AS mate,
    CASE WHEN node->>'bm' IS NULL AND node->>'b' IS NOT NULL
         THEN (CASE WHEN solver_white THEN (node->>'b')::int  ELSE -(node->>'b')::int  END) END AS cp
  FROM t WHERE node IS NOT NULL
)
SELECT m, count(*) n, round(avg(d),2) avg_depth,
  count(*) FILTER (WHERE mate > 0)             mate_for,
  count(*) FILTER (WHERE cp >= 200)            ge200,
  count(*) FILTER (WHERE cp >= 0 AND cp < 200) zero_199,
  count(*) FILTER (WHERE cp < 0 OR mate < 0)   losing,
  round(100.0*count(*) FILTER (WHERE cp < 0 OR mate < 0)/count(*),1) losing_pct
FROM e GROUP BY m ORDER BY n DESC;
```

For the **missed** orientation swap `allowed_*` → `missed_*` and `ply % 2 = 1` → `ply % 2 = 0`.
On prod add `TABLESAMPLE SYSTEM (3)` to `game_flaws` as the review did.

**Dev baseline produced by running exactly this, 2026-09-12** (the before side of the
before/after):

| motif int | motif | n | avg depth | mate_for | ≥+200 | 0..199 | losing | losing % |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 8 | mate | 1258 | 2.79 | 1257 | 1 | 0 | 0 | 0.0 |
| 2 | hanging-piece | 1192 | 0.00 | 26 | 1111 | 18 | 37 | 3.1 |
| 1 | fork | 918 | 0.57 | 33 | 845 | 26 | 14 | 1.5 |
| 3 | pin | 404 | 0.84 | 24 | 339 | 20 | 21 | 5.2 |
| **17** | **sacrifice** | 392 | **4.78** | 4 | 54 | 24 | **310** | **79.1** |
| 6 | discovered-attack | 221 | 1.35 | 4 | 207 | 5 | 5 | 2.3 |
| **15** | **clearance** | 126 | **3.73** | 8 | 39 | 20 | **59** | **46.8** |
| 10 | attraction | 110 | 1.18 | 9 | 91 | 4 | 6 | 5.5 |
| 4 | skewer | 105 | 2.90 | 10 | 78 | 9 | 8 | 7.6 |
| 9 | deflection | 103 | 3.01 | 15 | 64 | 9 | 15 | 14.6 |
| 25 | discovered-check | 100 | 1.52 | 17 | 73 | 4 | 6 | 6.0 |
| 28 | promotion | 78 | 3.59 | 13 | 43 | 5 | 17 | 21.8 |
| 26 | trapped-piece | 66 | 2.88 | 0 | 49 | 11 | 6 | 9.1 |
| **11** | **intermezzo** | 62 | 2.29 | 1 | 33 | 12 | **16** | **25.8** |
| 13 | interference | 17 | 3.41 | 0 | 13 | 0 | 4 | 23.5 |
| 12 | x-ray | 7 | 3.14 | 0 | 3 | 0 | 4 | 57.1 |
| 29 | under-promotion | 5 | 2.80 | 0 | 1 | 0 | 4 | 80.0 |

Dev reproduces the prod shape (review §2.1: sacrifice 78%, clearance 47%, intermezzo 23%). Note
x-ray and under-promotion are also badly affected but too thin to be listed in the review — the
per-tier floor (D-01: x-ray is tier-3 ⇒ +200; under-promotion is tier-5 ⇒ +200) covers both.

### Dev orientation asymmetry the D-09 fix targets

Measured this session over `game_flaws`:

| motif | allowed rows | missed rows | ratio |
|---|---:|---:|---:|
| intermezzo (11) | 64 | **2** | 32× |
| hanging-piece (2) | 1213 | 302 | 4.0× |
| sacrifice (17) | 551 | 146 | 3.8× |
| fork (1) | 923 | 454 | 2.0× |

The 32× intermezzo gap is the signature of the missing move stack (prod: 188 vs 6, 31×). After
D-09 the acceptance target is "missed intermezzo within 3× of allowed".

---

## Sampling Mechanics (TAGFIX-07 / D-13)

**Freeze the sample BEFORE any code change.** The whole point of D-13 is before/after on identical
inputs; once the detector changes, the population of tagged rows changes and the sample is no
longer drawable.

Recommended shape for `scripts/research/sample_realgame_tags.py` (analysis-only, `--db prod`
read-only, one `AsyncSession`, no `asyncio.gather`):

1. **Stratify** with a window function so no motif can dominate:
   `ROW_NUMBER() OVER (PARTITION BY motif, orientation ORDER BY md5((game_id::text||ply::text)))`,
   take the first N per stratum. Use an `md5` hash ordering, **not** `random()` — reproducibility,
   and the `project_benchmark_db_not_static` memory note (a growing table makes rank-window shards
   double-scan; a hash residue is stable).
2. Over-sample the motifs the phase is about (sacrifice, clearance, intermezzo, x-ray) and keep a
   thin control of the high-precision ones (fork, hanging-piece, mate) so a regression on those is
   detectable. ~150 rows total per D-13.
3. **Join what the detector needs:** `game_flaws` (motif/depth/blobs) ⋈ `game_positions p_prev`
   (ply−1: `move_san`, `eval_cp`, `eval_mate`) ⋈ `game_positions p_cur` (ply: `move_san`, `pv`) ⋈
   `game_positions p_next` (ply+1: `pv`) ⋈ `games` (`pgn`, for `_recompute_fen_map` to get the full
   pre-flaw FEN). `dev_probe.py:16-28` is a working template for exactly this join — reuse it.
4. Compute `eval_at_firing` with the same expression as the acceptance SQL (round odd depth up,
   `bm` before `b`) and freeze it into the CSV.
5. Write the CSV with `csv.DictWriter`; leave `label` and `rationale` empty for the labelling pass.

**Access:** `bin/prod_db_tunnel.sh` opens `ssh -fN -L 15432:127.0.0.1:5432 flawchess`;
`db_url_for_target("prod")` resolves to `DATABASE_URL_PROD` = `…@localhost:15432/flawchess`
(`app/core/config.py:28, 222-238`). The `flawchess-prod-db` MCP server is query-only and also
requires the tunnel — fine for exploration, but the sampler should go through `db_url_for_target`
so the target is auditable in the printed banner (the Phase-220 T-220-02 mitigation).

---

## Function-Size Headroom

`uv run python scripts/check_function_size.py app/ --fail-over-depth 4 --fail-over-loc 200` →
**"OK: 705 functions scanned, no breaches"** (measured this session). The three files this phase
edits are individually clean too (82 functions, no breaches).

Functions that grow and their current structural shape:

| Function | File:line | Current max nesting | Growth | Mitigation |
|---|---|---:|---|---|
| `detect_clearance` | `tactic_detector.py:1985` | 3 (`for` → `if` → `if`) | +2 clauses, one needing a victim loop | Extract `_clearance_line_is_used(...)` — mirrors the existing `_clearance_prior_move_is_valid` extraction at `:1968` |
| `detect_sacrifice` | `:2183` | 2 | +1 nested `if` | Fits; stays at 3 |
| `apply_forcing_line_filter` | `forcing_line_gate.py:385` | 1 | +1 floor check | Put the floor logic in the `_solver_cp_at_firing` sibling; the orchestrator stays flat |
| `_classify_tactic_gated` | `flaws_service.py:560` | 2 | +fallback branch | Extract `_gate_eval_inputs(n, orientation, positions) -> (cp, mate)`; keeps the wrapper readable and directly unit-testable |
| `_worker_recompute` | `retag_flaws.py:279` | 1 | +2 assignments | Fits (and `scripts/` is not gated by CI anyway — `ci.yml:101-104` gates `app/` only) |

CLAUDE.md's "refactor bloated code on sight" does **not** trigger here: nothing is currently in
breach. Do not open an unscoped refactor.

---

## State of the Art

| Old approach | Current approach | When changed | Impact on this phase |
|---|---|---|---|
| Detector tuned/validated on lichess puzzles only | Puzzle fixture **plus** a hand-labelled real-game gate | This phase (TAGFIX-07) | The fixture gate is necessary-not-sufficient; the review §3 proves it is structurally blind to the failure class |
| "Precision-first" hand-tightenings of cook predicates | Cook-faithful port + measured, documented deliberate divergences only | This phase (TAGFIX-05/-08) | Two prior deviations cost 237 detections for zero measured precision |
| `STILL_WINNING_FLOOR_CP` applied to the whole line | Phase 144 (Bug B) scoped it to the **conversion tail**, exempting the firing node | Phase 144, 2026-06-30 | That exemption is exactly the hole TAGFIX-01 closes — with a *per-tier* floor rather than restoring the blanket +200 |
| `--db prod` writes require running on the prod server | Writes over `bin/prod_db_tunnel.sh` from the local box are proven at 2.5M-row scale | Phase 220, 2026-09 | `retag_flaws.py`'s docstring (`:74-76`) is stale and must be corrected |

**Deprecated / superseded:**
- The "odd-board parity" remark about sacrifice in
  `.planning/notes/suppressed-tactic-gaps-investigation.md` — superseded; the current port matches
  cook on every fixture row (CONTEXT canonical_refs says so explicitly).
- The WR-02 `k−1` rationale block (`tactic_detector.py:886-892`) and the slim-blob paragraph it
  spawned in `forcing_line_gate.py:299-305` — both become dead prose once D-11 lands.

---

## Environment Availability

| Dependency | Required by | Available | Version | Fallback |
|---|---|---|---|---|
| Dev PostgreSQL (Docker, :5432) | dev retag smoke, dev acceptance SQL | ✓ | container `flawchess-dev-db-1`, up 26 h healthy | none needed |
| Prod DB via `bin/prod_db_tunnel.sh` (:15432) | TAGFIX-07 sampling, TAGFIX-09 retag + acceptance | ✓ (script present, Phase-220 precedent) | `ssh -fN -L 15432:127.0.0.1:5432 flawchess` | Operator must start it; the script is idempotent (`lsof` guard) |
| `lichess-puzzler` clone (`/home/aimfeld/Projects/Python/lichess-puzzler`) | TAGFIX-05 oracle verification, TAGFIX-08 script move | ✓ (referenced by the alignment note and `oracle_compare.py:9`) | AGPL-3.0, analysis-only | The script must `raise SystemExit(0)` when absent — required by TAGFIX-08 ("skip cleanly") |
| CC0 lichess puzzle dump (~300 MB) | fixture **re-generation** only | ✗ (not committed) | — | **Not needed** — this phase re-measures against the committed CSVs, never regenerates |
| Stockfish binary | — | ✓ (CI installs sf_18) | — | Not used: the phase is explicitly engine-free |
| Node/npm | frontend leg only if clearance is suppressed | ✓ | node 24 in CI | — |

**Missing dependencies with no fallback:** none.
**Missing with fallback:** the CC0 dump (fallback: don't regenerate — which is also the correct
behaviour per Pitfall 5).

---

## Validation Architecture

### Test framework

| Property | Value |
|---|---|
| Framework | pytest (`asyncio_mode = "auto"`), `pyproject.toml:76-86` |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run (unit, per task) | `uv run pytest tests/services/test_forcing_line_gate.py tests/services/test_tactic_detector.py -q` |
| Fixture gate (per detector change) | `uv run pytest tests/scripts/tagger -q` — **~10 s measured**; NOT in the default run |
| Full suite (pre-merge) | `uv run pytest -n auto -x` **plus** `uv run pytest tests/scripts/tagger -q` |
| Static gates | `uv run ruff check . --fix`, `uv run ruff format app/ tests/ scripts/ analysis/`, `uv run ty check app/ tests/ scripts/`, `uv run python scripts/check_function_size.py app/ --fail-over-depth 4 --fail-over-loc 200` |
| Frontend (clearance-suppression leg only) | `cd frontend && npm run lint && npm test -- --run && npm run build` |

### Requirement → test map

| Req | Behaviour to prove | Test type | File | Automated command | Exists? |
|---|---|---|---|---|---|
| TAGFIX-01 | Floor rejects a tier-3 motif whose firing node is < +200 solver-perspective; accepts ≥ +200; accepts a solver mate; 0-floor tier-2 motif accepted at +50 and rejected at −50; odd firing depth rounds **up**; `bm` wins over `b`; unknown/`None` motif_int skips the floor (back-compat) | unit | `tests/services/test_forcing_line_gate.py` (new `class TestWinningFloorAtFiring`) | `uv run pytest tests/services/test_forcing_line_gate.py -q` | ❌ new — helpers `_cp_node` / `_mate_node` / `_only_move_node` at `:41-56` already exist |
| TAGFIX-01 (D-03) | Blob `None` + `positions[n]` eval below floor (allowed) → suppressed; `positions[n-1]` (missed) → suppressed; blob `None` + winning eval → credited; **no** tag suppressed merely for lacking a blob | unit | `tests/services/test_flaws_service.py` (extend `TestClassifyTacticGated`, `:2676`) | `uv run pytest tests/services/test_flaws_service.py -q` | ❌ new |
| TAGFIX-02 | `pre_flaw_eval_cp=None` + `eval_mate` for solver → rejected (non-mate motif); same with a mate motif → credited; `pre_flaw_eval_cp=None` + no mate → gate still runs on the blob (only-move can still reject); `blobs_pending` and `[]` behaviours byte-identical | unit | `tests/services/test_flaws_service.py::TestClassifyTacticGated` + `TestClassifyTacticGatedBlobsPending` (`:2801`) | as above | ⚠ 4 existing blobs_pending tests must stay green **unmodified** — that is the regression signal |
| TAGFIX-03 | Deficit recovered on `boards[k+3]` → no fire; deficit persists → fires; line ends before `k+3` → fires; `k=6` → no fire (cap 4); both orientations identical (D-08) | unit | `tests/services/test_tactic_detector.py::TestSacrificeCookAndChain` (`:2312`) | `uv run pytest tests/services/test_tactic_detector.py -q` | ⚠ extend |
| TAGFIX-03 | Fixture precision floor for `sacrifice` still met after the divergence | harness | `tests/scripts/tagger/test_detector_precision.py` | `uv run pytest tests/scripts/tagger -q` | ✅ exists — **measured passing**: P(train) 1.000 vs floor 0.93 |
| TAGFIX-04 | King-move vacating → no fire; pawn-push vacating → no fire; ray move giving check → fires; ray move attacking a higher-value piece → fires; quiet shuffle → no fire; depth 6 → no fire. CONTEXT's worked examples are the fixtures: fire `Na6+ Ka8 [Qc7]`, `Rc8→g8+ … [c8=Q]`; reject `Kh1→g2 … [Rh1]`, `f6→f5 … [Rf6]`, `Bh8 … [Qf6]` | unit | `tests/services/test_tactic_detector.py` (`_CLEARANCE_FIXTURES` at `:726` + a new negatives class) | `uv run pytest tests/services/test_tactic_detector.py -q` | ⚠ extend |
| TAGFIX-04 | Real-game clearance real-share ≥ 0.8 **or** clearance suppressed everywhere | harness + unit | `tests/scripts/tagger/test_detector_precision.py` + the 4 suppression assertions in § Clearance Suppression Checklist | `uv run pytest tests/scripts/tagger -q && uv run pytest tests/services/test_tactic_comparison_service.py -q` | ❌ new |
| TAGFIX-05 | Each of the 7 fixes: the specific fixture rows that change, plus "no shipped floor drops" | harness | `tests/scripts/tagger/test_detector_precision.py`; the flipped WR-02 fixture re-labelled in `test_tactic_detector.py:465-469` | `uv run pytest tests/scripts/tagger -q && uv run pytest tests/services/test_tactic_detector.py -q` | ✅/⚠ — floors exist; the flipped fixture must be moved or annotated or `test_positives_fire_expected_motif[discovered-attack]` **fails** |
| TAGFIX-05 | Oracle parity: 0 "cook only" for deflection/fork/trapped-piece, 0 "ours only" for discovered-attack (SC1) | analysis script | `scripts/research/oracle_compare.py` | `uv run python scripts/research/oracle_compare.py` (manual, needs the clone) | ✅ exists (to be moved) |
| TAGFIX-05 | int 14 can never be dispatched | unit | new assertion: `14 not in {int(i) for _, i in _TIER3_REGISTRY}`, plus the existing `test_all_29_motifs_encoded` and `test_family_mapping_excludes_suppressed_tier3` | `uv run pytest tests/services/test_tactic_detector.py tests/services/test_tactic_comparison_service.py -q` | ❌ new (one line) |
| TAGFIX-06 | Missed pass board carries a one-move stack (`board.move_stack` length 1, `board.peek() == prev move`); intermezzo fires at k=2 on a missed line; a missed hanging-piece that is a plain recapture returns NULL (D-10); a missed flaw at ply 0 or with a malformed prev SAN falls back safely | unit | `tests/services/test_flaws_service.py` (new `class TestMissedOrientationParity`, near `test_missed_dest_sq_gate` at `:1966`) | `uv run pytest tests/services/test_flaws_service.py -q` | ❌ new — **must live here, not in `test_tactic_detector.py`** (Pitfall 3) |
| TAGFIX-07 | The real-game CSV loads, every row has a `Literal` label, and per-motif real-share ≥ floor | harness | `tests/scripts/tagger/test_detector_precision.py` (new `test_realgame_real_share_floor`) + a loader in `conftest.py` | `uv run pytest tests/scripts/tagger -q` | ❌ new |
| TAGFIX-08 | `scripts/research/*.py` pass lint/format/type and exit 0 when the clone is absent | static + smoke | — | `uv run ruff check . && uv run ruff format --check scripts/ && uv run ty check scripts/`; then run each script with the clone path renamed | ❌ new |
| TAGFIX-09 | Retag report includes removed/survived/**shifted** and is written on a non-dry run; the `--db prod` docstring is corrected | unit | `tests/scripts/test_retag_flaws.py` (751 lines, already covers the report writer with an injected `report_dir`) | `uv run pytest tests/scripts/test_retag_flaws.py -q` | ⚠ extend |
| TAGFIX-09 | Acceptance: losing-share < 5 % per motif / < 2 % overall; allowed sacrifice down an order of magnitude; missed intermezzo within 3× of allowed; zero motif-14 rows | operator SQL | § Acceptance Instrument, run through the tunnel | manual, pasted into the SUMMARY | ❌ new (query text exists, verified runnable on dev) |
| TAGFIX-09 | CHANGELOG `[Unreleased]` bullet | doc | `CHANGELOG.md` | grep | ❌ new |

### Sampling rate

- **Per task commit:** the unit file(s) touched by that task (`test_forcing_line_gate.py` /
  `test_tactic_detector.py` / `test_flaws_service.py` / `test_retag_flaws.py`), ~seconds.
- **Per detector-touching task:** `uv run pytest tests/scripts/tagger -q` (~10 s) — non-negotiable,
  since the default suite excludes it.
- **Per wave merge:** `uv run pytest -n auto -x` + `uv run pytest tests/scripts/tagger -q` +
  ruff/ty/function-size.
- **Phase gate (pre-squash-merge):** full CLAUDE.md pre-merge gate **plus** the tagger gate, plus
  the frontend leg if clearance was suppressed.

### Wave 0 gaps

- [ ] `tests/services/test_forcing_line_gate.py::TestWinningFloorAtFiring` — covers TAGFIX-01
- [ ] `tests/services/test_flaws_service.py::TestMissedOrientationParity` — covers TAGFIX-06
- [ ] `tests/scripts/tagger/conftest.py` — a `realgame_fixture` session fixture + `RealGameRow`
      TypedDict loader for `fixtures/tagger/realgame_tags.csv` (TAGFIX-07)
- [ ] `tests/scripts/tagger/precision_floors.py` — `REALGAME_REAL_SHARE_FLOOR` dict (TAGFIX-07)
- [ ] `fixtures/tagger/realgame_tags.csv` — must be sampled from prod **before** any detector edit
- [ ] No framework install needed.

---

## Security Domain

`security_enforcement` is not set to `false` in `.planning/config.json` (the key is absent), so this
section is included.

### Applicable ASVS categories

| ASVS category | Applies | Standard control |
|---|---|---|
| V2 Authentication | no | No auth surface is touched; the retag is an operator script. |
| V3 Session management | no | — |
| V4 Access control | **yes (operational)** | `--db prod` is a destructive-capable path. Existing control: explicit `--db` choice resolved through `db_url_for_target` with an unknown-target `ValueError` (`config.py:222-238`); the Phase-220 T-220-02 mitigation (print and read the resolved `host:port/database` banner before running, `--dry-run` first) should be re-applied verbatim. |
| V5 Input validation | **yes** | Two new untrusted-ish inputs: (a) the `realgame_tags.csv` `label` column — parse into a closed `Literal` set and fail loudly on anything else, never `str`; (b) PV/SAN strings from the DB — already handled by `_parse_pv`'s `ValueError` guard (`tactic_detector.py:241-262`) and the `except ValueError, chess.IllegalMoveError` guards in `flaws_service`. The new D-09 `parse_san` call **must** be inside such a guard. |
| V6 Cryptography | no | The `md5()` in the sampling SQL is a *sampling hash*, not a security primitive — say so in a comment so a future audit does not flag it. |
| V7 Error handling / logging | **yes** | CLAUDE.md: never embed variables in exception messages (Sentry grouping). The retag already does this correctly (`retag_flaws.py:745-755` uses `set_context`). Any new `except` in `app/services/` needs `sentry_sdk.capture_exception`. |
| V12 Files & resources | **yes (light)** | `fixtures/tagger/realgame_tags.csv` is read with an explicit path built from `Path(__file__).resolve().parents[3]` (the existing pattern at `conftest.py:31-35`) — no user-supplied path. |

### Known threat patterns for this stack

| Pattern | STRIDE | Standard mitigation |
|---|---|---|
| Wrong `--db` target against production | Tampering | Explicit `--db` on every command, resolved target banner printed and read, `--dry-run` first (Phase-220 precedent) |
| Un-throttled mass UPDATE on a live prod DB | Denial of service | `--throttle-ms` + `FLAWS_PER_BATCH = 2000` commits + off-peak run; the OOM history is called out in `retag_flaws.py:63-65` |
| Retag diverging from the live classify path | Tampering (data integrity) | SC4 single path + the `positions[ply-1]` fix (Pitfall 2); `tests/scripts/test_retag_flaws.py:620-740` already exists as the drift guard |
| PGN/PV replay raising on malformed data | DoS / availability | `_parse_pv` raises `ValueError`, callers guard; `detect_tactic_motif` is contractually "never raises" (`:2613-2620`) |
| AGPL contamination from the oracle clone | Legal / compliance | `scripts/research/` imports the clone **by path at runtime**, copies no source, and exits cleanly when absent (TAGFIX-08) — the same boundary the two alignment notes already document |

---

## Assumptions Log

| # | Claim | Section | Risk if wrong |
|---|---|---|---|
| A1 | Adding `motif_int` as a defaulted kwarg to `apply_forcing_line_filter` keeps all existing call sites and ~50 unit-test invocations compiling unchanged | Implementation Map 1 | Low — I read the call sites, but did not execute the full gate test file with a modified signature. Mitigation: the first task's verification is `pytest tests/services/test_forcing_line_gate.py`. |
| A2 | The boden/double-bishop divergence is a bishop sitting **on** the king's file | Implementation Map 5 #6 | Medium — I read the file-comparison expression (`:1415`) and reasoned about it, but did NOT reproduce the 6 divergent rows against cook. The plan must re-run `oracle_compare.py` to confirm before writing the fix. |
| A3 | The 33/302 dev missed hanging-piece recapture rows and the 12-sample clearance hand review are accurate as reported | Pitfall / D-10 | Low — quoted from the committed review report; I did not re-derive them. They set expectations, not gates. |
| A4 | `retag_flaws.py`'s single-entry `fen_map` will break the D-09 missed-board build in the retag path | Pitfall 2 | Medium — logically certain from the code (`fen_map = {ply: work.fen}` and D-09 needs `fen_map[n-1]`), but I did not execute the retag with a D-09 patch. If wrong, the fix is a no-op; if right and unaddressed, the retag silently under-tags missed intermezzo. |
| A5 | `game_flaws.fen` (piece-placement only) is unusable as the D-09 previous-position source in the retag | Pitfall 2 / Open Q 1 | Low — `flaws_service.py:682-690` states the column contract explicitly. |
| A6 | Suppressing clearance requires exactly the 7 touchpoints listed | Clearance checklist | Low — enumerated by grep this session; a missed frontend usage would surface as a TS error in `npm run build`. |
| A7 | The prod tunnel supports the write volume of a full 3.18M-row retag comfortably | TAGFIX-09 | Medium — Phase 220 proved 2.57M reads + ~11k writes over the tunnel, not ~1M UPDATEs. Throughput, not capability, is the open variable; `--throttle-ms` and an overnight window are the mitigation. The alternative (run on the prod server) remains available. |
| A8 | `[ASSUMED]` The combined simulation's per-motif TP gains will hold once the *remaining* four port fixes (deflection OR, fork gate, trapped-piece, boden) are also applied | Measured Simulation | Low-medium — the four unsimulated fixes are all recall-positive per the oracle table, so gains should compound, but dispatch is winner-take-all and interactions are possible. The fixture gate is the check. |

---

## Open Questions

1. **How does the re-tagger get a previous-ply FEN for the D-09 missed board?**
   - What we know: `_worker_recompute` has `work.fen` (the flaw ply's piece-placement-only FEN from
     `game_flaws.fen`) and `work.prv` (a `_PosRow` with `move_san`), and builds `fen_map = {ply:
     work.fen}`. `_recompute_fen_map` needs the game PGN, which the page query does not load.
   - What's unclear: whether to (a) load `games.pgn` per page + cache per `game_id` (the
     `dev_probe.py` pattern, costs memory and a join), or (b) reconstruct the previous board by
     popping the previous move off a full pre-flaw FEN — which `game_flaws.fen` cannot provide.
   - Recommendation: **(a)**, joined on the existing page query with a per-page `{game_id: fen_map}`
     cache. Add `games.pgn` to `_fetch_flaw_page` and drop the synthetic `fen_map`/positions
     scaffolding in favour of the real ones — this also fixes Pitfall 2's positions gap in the same
     stroke, and makes the retag structurally identical to `eval_remote.py:1028-1049`. Measure the
     page-query cost on dev before committing to it (PGNs are large; `FLAWS_PER_BATCH = 2000`).

2. **Does the 0-floor for tier-1/2 motifs use `cp >= 0` or `cp > 0`?**
   - D-01 says `cp ≥ floor` with floor 0, i.e. a dead-equal firing node is *credited*. The dev table
     shows `zero_199` buckets are small for tier-2 (fork 26/918, hanging-piece 18/1192), so the
     distinction moves few rows.
   - Recommendation: implement `>=` exactly as written; make the boundary an explicit unit test so
     the choice is visible rather than incidental.

3. **What counts as "the line ends" for D-05's persistence rule when the PV is capped at
   `PV_CAP_PLIES`?**
   - A capped 12-ply PV ends artificially. 45 % of fixture sacrifices fire on the last pov move
     (review §2.3), so "line ends ⇒ accept" readmits a large share of exactly the shape D-05 targets.
   - Recommendation: implement D-05 literally (accept when `k+3 >= len(boards)`), then check the
     measured sacrifice survivor count against the review's "697 dev tags → 54 survivors"
     simulation. My TRAIN simulation gives 177 survivors of 409 — a much softer cut than the dev
     simulation, which suggests the fixture's short lines make "line ends" fire often. If the dev
     retag shows the cut is too soft, the depth cap (D-06) is the lever, not a re-litigation of D-05.

4. **Is a fourth "depth-shifted" counter wanted in the retag report?**
   - TAGFIX-09 says removed/survived/shifted. D-11 changes the *depth* of every surviving
     discovered-attack row without changing the motif — that is a real, reportable change that a
     motif-only "shifted" counter would miss entirely.
   - Recommendation: report both (`motif_shifted`, `depth_shifted`); it is ~6 lines in
     `_accumulate_motif_counts`.

5. **Should the `--margin` flag stay?**
   - Out of scope to change, but the plan should confirm the prod retag is run at the **default**
     margin (`ONLY_MOVE_WIN_PROB_MARGIN = 0.35`) so the before/after isolates this phase's changes.
     Hard constraint: no change to `ONLY_MOVE_CP_GAP_THRESHOLD`.

---

## Sources

### Primary (HIGH confidence — read or executed this session)
- `app/services/forcing_line_gate.py` (461 lines, read in full)
- `app/services/tactic_detector.py` (targeted reads: `:1-240`, `:241-460`, `:809-1040`, `:1369-1425`,
  `:1505-1615`, `:1704-1780`, `:1918-2075`, `:2183-2245`, `:2320-2637`)
- `app/services/flaws_service.py` (`:195-235`, `:297-720`)
- `scripts/retag_flaws.py` (808 lines, read in full)
- `scripts/tactic_tagger_report.py`, `tests/scripts/tagger/{conftest,precision_floors,motif_theme_map,test_detector_precision}.py`
- `app/routers/eval_remote.py:990-1065`, `app/services/eval_apply.py:1200-1245`, `scripts/ab_validate_gate.py:415-455`
- `app/repositories/library_repository.py:119-208`, `app/models/game_flaw.py`, `app/core/config.py:22-52, 222-238`
- `frontend/src/lib/tacticComparisonMeta.ts`, `frontend/src/lib/tacticMotifDefinitions.ts:44`
- `pyproject.toml`, `.github/workflows/ci.yml`, `bin/prod_db_tunnel.sh`, `CHANGELOG.md`
- **Executed:** `uv run pytest tests/scripts/tagger -q` (1 passed, 9.85 s); the D-11 fixture-flip
  experiment; the combined-change TRAIN simulation; `check_function_size.py app/` (OK, 705 fns);
  `ruff check` + `ty check` on the two research scripts (39 + 2 findings); three dev-DB read-only
  SQL batches including the full §2.1 acceptance query.

### Secondary (committed project documents)
- `reports/tactic-tagger/tactic-tagger-review-2026-09-12.md` — the evidence base (prod 3 % sample
  tables, gate-skip analysis, oracle divergence table §4, fix simulations)
- `.planning/seeds/SEED-165-tactic-tagger-real-game-precision.md`
- `.planning/notes/tactic-tagger-cook-alignment.md` — the cook↔ours index convention
- `.planning/notes/tactic-forcing-line-gate.md` — gate design + lichess-puzzler constant provenance
- `.planning/ROADMAP.md` §Phase 221, `.planning/STATE.md`, `221-CONTEXT.md`
- `.planning/phases/220-.../220-06-SUMMARY.md:45` — the prod-tunnel write precedent
- `reports/tactic-tagger/review-2026-09-12-scripts/{oracle_compare,dev_probe}.py`
- `.claude/skills/tactic-tagger-report/SKILL.md`

### Tertiary (LOW confidence)
- None. No web search was required; no external claim is load-bearing in this document.

---

## Metadata

**Confidence breakdown:**
- Code shapes / file:line anchors: **HIGH** — every anchor opened with `Read`/`sed` this session and
  quoted verbatim.
- Measured deltas (TRAIN simulation, D-11 fixture flip, dev acceptance table, lint counts, harness
  runtime, function-size status): **HIGH** — executed this session, output pasted above.
- Prod-scale numbers (78 % sacrifice losing, 777k allowed tags, ~130 motif-14 rows, +297/+130/+107
  oracle deltas): **MEDIUM** — quoted from the committed review report, not re-derived; the dev
  equivalents I *did* measure reproduce the same shape.
- The `retag_flaws.py` positions/fen_map divergence (Pitfall 2): **HIGH** on the code fact,
  **MEDIUM** on the consequence — reasoned from the code, not executed with a patched detector.
- Boden/double-bishop root cause (A2): **MEDIUM** — reasoned, not oracle-verified.

**Research date:** 2026-09-12
**Valid until:** 2026-10-12 (stable in-repo domain; invalidated earlier only by a change to
`tactic_detector.py`, `forcing_line_gate.py`, `flaws_service.py` or the fixture CSVs)
