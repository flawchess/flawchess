# Phase 124: Schema + Tactic Detector - Context

**Gathered:** 2026-06-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 124 delivers a **pure-CPU tactic-motif detector** plus the schema to store its
output. For any flawed move that has a stored refutation PV (`game_positions.pv` at
`flaw_ply + 1`), the detector names **one** tactic motif (+ piece + confidence) by
reimplementing the `ornicar/lichess-puzzler` `cook.py` heuristics in original code (no
AGPL source copied). It runs inside the existing single classify path
(`classify_game_flaws` eval-drain flow-through and `backfill_flaws.py` recompute) for
**both** the player's and the opponent's flaws, with **no new Stockfish invocation**.

**In scope:** Alembic migration (new columns), the detector module + all detectors,
priority-order tiebreak, the per-motif `tactic_piece` semantics, the
`tactic_confidence` grading, the hand-labeled fixture validation set, and wiring into
the classify path.

**Out of scope (later phases):** running the backfill over prod (Phase 125), the
`/api/library/tactic-comparison` endpoint, motif chips, the MiniBulletChart grid, and
all frontend (Phase 126). No `is_opponent` column (derived at query time via
`is_opponent_expr`).
</domain>

<decisions>
## Implementation Decisions

### Schema (migration)
- **D-01:** The migration adds **three** nullable `SmallInteger` columns to
  `game_flaws`: `tactic_motif` (enum), `tactic_piece` (python-chess PieceType 1–6),
  and `tactic_confidence` (0–100). **NOTE the discrepancy:** ROADMAP Success Criterion
  #1 and the original TACSCH-01/02 requirements mention only two columns
  (`tactic_motif`, `tactic_piece`); `tactic_confidence` was locked later in the
  architecture note ("Winner-confidence column" section). Build all three. Existing
  rows carry NULL in all three after migration.
- **D-02:** `tactic_motif` is a single enum (at most one per flaw) — NOT a bitmask, NOT
  a join table. Encode via an `IntEnum` following the `EndgameClassInt` precedent
  (`app/services/endgame_service.py:108`): a `*Int` IntEnum + `_INT_TO_*` /
  `_*_TO_INT` dicts mapping to a `Literal[...]` motif-name type.
- **D-03:** Named-mate subtypes are stored **fine-grained, not collapsed**
  (`smothered`, `anastasia`, `hook`, `arabian`, `boden`, `double-bishop`, `dovetail`,
  `back-rank-mate`, generic `mate`). Coarsening to "mate" is free at query time
  (`WHERE tactic_motif IN (MATE_MOTIFS)`); refining a collapsed `mate` would require a
  full re-detect over 131k+ rows. Each named-mate detector is a separate function, so
  capture cost is ~zero.

### Detector scope (this phase implements + validates everything)
- **D-04:** Phase 124 implements **and Q-011-validates ALL detectors now** — Core 8
  (`fork`, `hanging-piece`, `pin`, `skewer`, `double-check`, `discovered-attack`,
  `back-rank-mate`, generic `mate`) **+ all 8 tier-3** (`deflection`, `intermezzo`,
  `x-ray`, `interference`/`self-interference`, `clearance`, `attraction`,
  `capturing-defender`, `sacrifice`) **+ the named-mate subtype functions**. This is a
  large phase by deliberate choice. **Risk flagged to planner:** the tier-3 + named-mate
  heuristics carry the bulk of the validation burden, and Phase 125 backfill is gated on
  every implemented detector clearing its Q-011 precision bar.
- **D-05:** Severity gate = **mistakes + blunders** (not blunders-only — a
  missed/allowed fork can be mistake-sized). Implement as a **tunable threshold
  constant**, not a hardcoded assumption.
- **D-06:** Excluded motifs (NOT cause-of-error, do not implement): move-type
  descriptors, attack-theme positional tags, puzzle metadata,
  crushing/advantage/equality, oneMove/short/long, endgame-type tags. `overloading` is
  a `return False` stub in cook — unavailable. (Full list in the architecture note.)

### Priority order (Q-010 — the tiebreak when several motifs fire on one PV)
- **D-07:** Fixed priority order (this order **is** the card's wording):
  1. **Mates** — named subtype > `back-rank-mate` > generic `mate`.
     **Mate ALWAYS dominates** any co-firing geometric motif (a forced-mate PV is
     labelled by its mate type regardless of a delivering fork/pin).
  2. **Geometric material-winners:** `fork` > `skewer` > `pin` > `discovered-attack` >
     `double-check`.
  3. **Tier-3 fuzzy:** `deflection` > `attraction` > `intermezzo` > `x-ray` >
     `interference`/`self-interference` > `clearance` > `capturing-defender` >
     `sacrifice`.
  4. **`hanging-piece`** — **always last** (catch-all). Nearly every winning refutation
     captures something loose; hanging-piece only wins when NO more specific motif
     fires. It is the honest "you just dropped a piece, no combination" bucket.
- **D-08:** Intra-tier order within tiers 2 and 3 is **provisional** — per Q-010 step 2
  it can be tuned once the detector exists and real multi-motif co-occurrence is sampled.
  The single-column + GROUP BY design and the inter-tier order (D-07) are firm.

### Validation + accuracy bar (Q-011 — the named technical risk)
- **D-09:** Build a hand-labeled fixture set: **~10–15 positives per motif** drawn from
  our **own prod flaws** (`game_flaws` + `game_positions.pv`, labelled by inspection —
  NOT by running `cook.py`), plus a **shared hard-negative set**.
- **D-10:** **Tiered precision bar (precision-first; recall NOT gated):** Core 8 must
  hit **≥90% precision**; tier-3 + named-mate detectors held to **≥95%**. A motif that
  misses its bar is left **query-suppressed** (stored but never surfaced), never
  mis-tagged. Backfill (Phase 125) is gated on every detector clearing its bar.
- **D-11:** **Confidence handling — always write, suppress at query time.** When any
  detector fires, store the **priority-winner's** `tactic_motif` + `tactic_confidence`
  (core motifs = fixed high value, e.g. 100, since cook is boolean; tier-3 = a graded
  per-motif score — defining that scoring function is the tier-3 Q-011 work). **Never
  withhold at detect time.** `tactic_motif = NULL` means **no detector fired**.
  Low-confidence suppression is purely a query-time `AND tactic_confidence >= :t`
  decision (sweep thresholds in SQL, no re-backfill). Known limitation (accepted):
  winner-confidence thresholds the winner only — it cannot re-rank.

### tactic_piece semantics (Q-012 — stored-but-unsurfaced in v1, re-backfillable)
- **D-12:** Capture a piece with a **clean semantic wherever one is well-defined; NULL
  otherwise:**
  - `fork` → forking/attacking piece (highest-value attacker)
  - `hanging-piece` → the **victim** (the piece you hung that the refutation captures)
  - `pin` / `skewer` → the **line piece** delivering it (B/R/Q only)
  - all mates (named + back-rank + generic) → the **mating** piece
  - `discovered-attack` → the **unveiled attacking** piece
  - `sacrifice` → the **sacrificed** piece
  - `capturing-defender` → the **captured defender**
  - `deflection` / `attraction` → the **target** piece (deflected/attracted)
  - **NULL (genuinely ambiguous / multi-piece):** `double-check`, `x-ray`,
    `interference`/`self-interference`, `clearance`, `intermezzo`, and any case where
    the per-motif rule is ambiguous.

### Claude's Discretion
- Detector module layout, the PV-parsing helper that builds the `(board, line, pov)`
  the heuristics expect (pov = the refuting side, i.e. the non-flawed mover), fixture
  file format/location, and the exact int values assigned to each motif in the enum.
- The precise graded scoring function per tier-3 motif (constrained by the D-10 bar).
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Architecture & decisions (READ FIRST)
- `.planning/notes/tactic-tagging-architecture.md` — the load-bearing decision record.
  Compute path, both-color coverage, full motif inventory (core 8 + tier-3 + excluded),
  severity gate, the three-column schema incl. `tactic_confidence`, the
  capture-broadly-store-now philosophy, and the Q-010/011/012 framing. **Supersedes the
  stale SEED-039 premises.**
- `.planning/research/questions.md` — Q-010 (priority order), Q-011 (validation set +
  accuracy bar), Q-012 (per-motif `tactic_piece` semantic). Q-007 (per-user
  analyzed-game distribution — context for why piece-level UI is deferred).
- `.planning/REQUIREMENTS.md` — TACSCH-01/02 (+ the later `tactic_confidence`),
  TACDET-01/02/03/04. (Note TACSCH text predates the third column — see D-01.)
- `.planning/milestones/v1.28-ROADMAP.md` — phase goals/success criteria for 124–126.

### External source (heuristics only — DO NOT copy code)
- `ornicar/lichess-puzzler` `tagger/cook.py` — the heuristics being reimplemented in
  original code. AGPL-3.0: heuristics/ideas are fair game, source text is not. Validate
  against our own hand-labeled fixtures, NOT against cook.py output.

### Integration code references
- `app/services/flaws_service.py` — `classify_game_flaws` (line ~615),
  `_run_all_moves_pass` (~307, both colors), `_build_flaw_record`, `_build_tags`,
  `_recompute_fen_map` (~281): the detector integration point.
- `scripts/backfill_flaws.py` — runs the same `classify_game_flaws`; the recompute path.
- `app/models/game_flaw.py` — add the three columns here.
- `app/models/game_position.py` — `best_move`, `pv` columns (the data source);
  `PV_CAP_PLIES = 12` lives in `app/services/engine.py` (PV is a single 12-ply line —
  deep enough for full mate lines; not a constraint).
- `app/services/endgame_service.py:108` — `EndgameClassInt` IntEnum: the encoding
  precedent for `tactic_motif`.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `EndgameClassInt` (`endgame_service.py:108`) + its `_INT_TO_CLASS` / `_CLASS_TO_INT`
  dicts — copy this exact pattern for the motif enum (IntEnum + Literal + two dicts).
- `game_flaws` already materializes BOTH colors' flaws (Phase 113, D-06); the
  all-moves pass in `classify_game_flaws` evaluates both sides. The detector inherits
  both-color coverage for free — no player-only filter to remove.
- `is_opponent_expr(ply, games.user_color)` — query-time helper for the player/opponent
  split (Phase 126 consumer). No `is_opponent` column needed.

### Established Patterns
- One nullable `SmallInteger` column per derived attribute on `game_flaws` (tempo,
  phase, severity precedent). `tactic_motif`/`tactic_piece`/`tactic_confidence` follow it.
- Tunable thresholds extracted as named constants (cf. `EVAL_COVERAGE_MIN`,
  `_BATCH_SIZE`). The severity gate constant (D-05) follows this.

### Integration Points
- Detector slots into `classify_game_flaws`: the `positions` list passed in already
  contains `game_positions.pv`. Read the PV at `flaw_ply + 1` for the flaw at ply `n`,
  build `(board, line, pov)`, run the detectors, apply the D-07 priority order, write
  `tactic_motif` + `tactic_piece` + `tactic_confidence` onto the flaw record.
- `backfill_flaws.py` reaches the same code path — no separate detector wiring.

</code_context>

<specifics>
## Specific Ideas

- Verified prod mapping (architecture note): game 975197, user 44 — `pv` keyed at
  `flaw_ply + 1` (clean 1:1 post-move shift), present for both colors' flaws. The
  detector reads that ply directly; no board reconstruction or synthetic search.
- Coverage on day one: ~131k self-eval'd games (`full_evals_completed_at` set) are
  tactic-taggable now; ~13.6k lichess-eval-only games keep `tactic_motif = NULL` until
  full-eval'd via the existing tier-3 idle fleet (Phase 125 concern, no bespoke tooling).
- Precision-first rationale: the product compares **rates** (you-vs-opponent), so a
  false-positive tag biases the comparison more than a missing tag — hence the
  asymmetric ≥90/≥95 bars and the willingness to leave detectors query-suppressed.

</specifics>

<deferred>
## Deferred Ideas

- **Piece-level you-vs-opponent UI** (TACPIECE-01) — `motif × piece_type` (~6×6) fragments
  the already-thin per-user samples (Q-007: median ~6 analyzed games). Data captured now
  via `tactic_piece`; UI surfaced in a later milestone only where samples clear the
  Wilson floor.
- **Surfacing named-mate subtypes** — v1 surfaces the coarse "mate" grouping; the
  specific subtype is stored-but-unsurfaced until each named-mate detector is validated.
  Surfacing decision belongs to Phase 126, not 124.
- **True standalone `missed-X` detection** (TACMISS-01) — needs motif detection in the
  player's own PV and a second axis; deferred. (The v1 `missed` view is reconstructed as
  a join over adjacent opponent `allowed` rows + the existing `is_miss` tag.)

None of these are in Phase 124 scope.

</deferred>

---

*Phase: 124-schema-tactic-detector*
*Context gathered: 2026-06-17*
