# Phase 131: Tactic precision hardening via cook.py predicate alignment - Context

**Gathered:** 2026-06-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Raise per-motif tactic-tag **precision** toward >0.9 by faithfully replicating
`ornicar/lichess-puzzler`'s `tagger/cook.py` predicates motif-by-motif (Workstream A),
fix the missed-vs-played false-alarm at the call site (Workstream B), and change dispatch
to **shallowest-tactic-wins**. Precision-first: a wrong chip destroys user trust, a NULL
chip costs nothing — so the optimization target is precision, not recall (recall is ungated).

**In scope:** Tier 1 (mates) + Tier 2 (geometric) motifs only.
- Workstream A — port cook's exact predicate for each firing motif (skewer, discovered-attack,
  back-rank-mate, fork, pin, anastasia-mate, hook-mate, discovered-check), plus the two shared
  utility ports (ray-aware `is_defended`, `is_in_bad_spot`, and `king_values` with king=99).
- Dispatch rework — make depth the **primary** key (shallowest-tactic-wins), mate gated on the
  Stockfish mate-in-x score, equal-depth tiebreak by existing tier/rank, hanging-piece first-class.
- Workstream B — suppress a `missed` tactic when the flaw move went to the same target as the best line.
- Dev re-backfill of `game_flaws` tactic columns (real-data validation of the fix).

**Out of scope:** All Tier-3 tactics (deflection, attraction, intermezzo, x-ray, interference,
clearance, capturing-defender, sacrifice) — leave suppressed, defer to a later phase. ML (rejected).
A hand-labeled prod-flaw precision set (deferred — CC0 puzzle fixture stays ground truth). Prod
re-backfill execution (runbook step, outside the phase gate). No new motifs. No dev DB reset.

</domain>

<decisions>
## Implementation Decisions

### Phase scoping
- **D-01 [informational]:** **One phase**, not two. Workstream A (detector predicate alignment) + the dispatch
  rework + Workstream B (call-site missed-vs-played gate) ship together. The dispatch change
  shifts the TP/FP mix the precision harness measures (shallowest-wins makes hanging-piece win
  more, deeper forks win less), so it MUST be decided with Workstream A — not bolted on after, or
  the precision numbers move under us. B is small and independent but folds in cleanly. (Resolves
  seed Open-Q1; the user did not request a split, so the seed's recommendation stands.)

### Broken-motif effort policy
- **D-02:** **Attempt the full cook port for ALL in-scope geometrics, suppress any that miss 0.9.**
  Do the complete relational rebuild even for the two worst motifs — skewer (0.15) and
  discovered-attack (0.17) — then measure on the held-out TEST split. Any motif still <0.9 at full
  cook fidelity is **suppressed** (`tactic_motif` NULL / below the `_TACTIC_CHIP_CONFIDENCE_MIN`
  lever), not shipped. Honest expectation per the seed: skewer and discovered-attack are deeply
  broken and may plateau below 0.9 — suppressing skewer alone removes ~16% of all tags (mostly
  false), an explicitly endorsed trade. The full port is the precision *ceiling*; we want to know
  the real ceiling before suppressing, not pre-suppress on assumption.

### Workstream B missed-vs-played gate
- **D-03:** **Destination-square match only.** On the missed pass, suppress the missed tactic when
  the flaw move's destination square equals the best line's first-move destination square. This
  cleanly covers the wrong-recapture case (best line: capture the rook with the knight; player:
  captured the same rook with the wrong piece → the player plainly *saw* the piece → not a missed
  tactic). Do NOT additionally require same captured-piece value — dest-square match is sufficient
  and simpler; revisit only if a unit fixture surfaces a false suppression. (Resolves seed Open-Q3.)
- **D-04:** **Validate Workstream B separately from the puzzle harness.** This bug is invisible to
  the CC0 fixture (a puzzle has no "move the player actually played"). Validate with hand-built
  `(flaw_move, best_line)` unit fixtures in `tests/services/test_tactic_detector.py` (or a sibling)
  plus a manual prod spot-check of missed-side hanging-piece/fork tags. A green puzzle report does
  NOT prove these false alarms are gone. Blast radius is large — missed side is dominated by fork
  5,847 / pin 5,679 / discovered-attack 5,617 / skewer 4,259, far beyond the 328 missed
  hanging-piece rows.

### Dispatch / resolution — shallowest-tactic-wins (LOCKED by seed, carried forward)
- **D-05:** **Depth becomes the PRIMARY dispatch key.** This is a change from the status quo: the
  current dispatcher (`detect_tactic_motif`, `tactic_detector.py:1798-1804`) sorts by
  `(tier, rank, depth)` with depth only a tertiary tiebreaker, so tier/rank dominate. The new
  behavior makes depth primary for non-mate tactics; tier/rank break ties only at equal depth.
  Favors a **ply-outer / detector-inner** walk with early-exit over the current
  detector-outer collect-then-sort. (Note: Phase 127 D-02 intended min-depth dispatch; the live
  code does not implement it as primary — this phase makes it primary.)
- **D-06:** **Mate first, gated on the Stockfish mate-in-x score — NOT `is_checkmate` at the PV end.**
  The PV is capped at ~12 plies (`PV_CAP_PLIES`, `engine.py:99`), so a long forced mate is truncated
  and never shows checkmate; a scan-the-end check would miss it. Gate the mate path on Stockfish's
  mate-in-x signal, then run the named-mate detectors (smothered / back-rank / anastasia / hook / …)
  on the mating position. Mate outranks a shallower piece-win (being mated is the more severe error).
- **D-07:** **hanging-piece is a first-class winner, never demoted as a catch-all.** When a
  hanging-piece (depth 0) competes with a deeper geometric tactic, the hanging-piece wins because it
  is shallowest. Rationale (resolves seed Open-Q4c, RESOLVED 2026-06-22): a piece left/missed en
  prise is the **root cause** and most **fundamental skill** error; a deep fork is a downstream
  consequence. It is also our highest-precision detector (0.95 vs fork 0.40), so preferring it when
  shallowest aligns pedagogy and trust. The Tier-4 rank is a dispatch/precision-claiming artifact,
  not a statement of instructional value.

### cook.py predicate alignment (LOCKED by seed + note, carried forward)
- **D-08:** **Port the two shared utilities first — they leak across many motifs.** (1) ray-aware
  `is_defended` (treats a piece as defended if it has a normal OR X-ray/ray defender behind a
  friendly ray piece) replacing the non-ray `_is_hanging` (`tactic_detector.py:256`); (2)
  `is_in_bad_spot(square)` (piece is attacked AND (hanging OR capturable by a lower-valued non-king))
  — used as a *prune* in fork and an *accept* in skewer; we lack it entirely. Also add `king_values`
  (`{P1,N3,B3,R5,Q9,K99}`) so attacking the enemy king counts as a high-value fork/skewer target.
- **D-09:** **Per-motif divergences are specified in the cook-alignment note** (the implementation
  reference). Targets: skewer >0.9 or suppress; discovered-attack >0.9 or suppress (preserve the
  discovered-check-wins-first split, D-03 of seed); back-rank-mate >0.9 (own-blocker test +
  back-rank-checker requirement); fork >0.9 or suppress (add forker-safety `is_in_bad_spot` prune,
  skip pawn victims, use `king_values`, the hanging-victim "not an attacker of the fork square"
  clause, stop scanning the last pov move); pin >0.9 or suppress (the full `pin_prevents_attack` /
  `pin_prevents_escape` two-sub-test port via `board.pin`); anastasia-mate / hook-mate small lifts
  to >0.9. Lock against regression (no detector work): mate (1.00), smothered-mate (1.00),
  double-check (1.00), discovered-check (hold ≥0.85), hanging-piece puzzle-precision (0.95).
- **D-10:** **AGPL boundary.** Reimplement every predicate from the plain-English pseudocode in the
  cook-alignment note; copy NO `cook.py` source (AGPL-3.0; heuristics aren't copyrightable, source
  is). Continues the Phase 124 / Phase 127 D-11 constraint; a reviewer/grep confirms no source paste.

### Shipping gate (LOCKED by seed)
- **D-11:** **Judge on the TEST split + ΔP, never TRAIN** (overfit guard). A motif ships only if it
  clears >0.9 puzzle precision on the held-out TEST split. Can't reach 0.9 even at full cook
  fidelity → leave suppressed. Recall is whatever falls out — not gated (Phase 127 D-08). Use
  `scripts/tactic_tagger_report.py --check-goals` (raise GOALS to precision 0.9 for in-scope motifs;
  recall ungated) as the measurement/regression harness; re-run `/tactic-tagger-report` for the full
  table. CC0 fixtures already exist for all in-scope motifs (fork n=2185, pin n=1739, skewer n=976,
  discovered-attack n=1461, back-rank n=1198) — no new puzzle data needed.

### Re-backfill scope
- **D-12:** **Dev re-backfill in-phase; prod deferred to a runbook** (Phase 127 D-13 precedent). The
  precision fix makes the existing ~131k tags actively wrong, and they are already live in the Phase
  126 comparison UI, so "do nothing" leaves known-wrong tags rendering. Re-run the corrected detector
  over the tagged games **on dev** via `scripts/backfill_flaws.py` (this is also the real-data
  validation of the fix beyond fixtures). **Prod** re-backfill is a documented runbook step executed
  outside the phase gate; new drains pick up corrected code automatically. The offline CC0 harness
  remains the authoritative precision signal (Phase 127 D-09). **No dev DB reset** — backfill runs
  against the existing dev DB. (Resolves seed Open-Q2.)

### Claude's Discretion
- Exact suppression mechanism per failing motif (confidence value vs NULL emission) — reuse the
  existing `tactic_confidence` query-suppression lever; planner confirms.
- TRAIN/TEST split mechanics and exact ΔP reporting format in the harness (planner/researcher).
- Whether Workstream B unit fixtures live in `test_tactic_detector.py` or a sibling file (D-04).
- The precise control-flow shape of the ply-outer/detector-inner walk (D-05) — planner's call,
  validated by the precision delta on the harness.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase source — read first
- `.planning/seeds/SEED-064-tactic-precision-hardening-cook-alignment.md` — the condensed phase
  spec: why precision (not recall), cook-is-the-oracle insight, two workstreams, the
  shallowest-tactic-wins dispatch decision, out-of-scope list, shipping gate.
- `.planning/notes/tactic-tagger-cook-alignment.md` — **the implementation reference.** Faithful
  cook.py pseudocode: the cook↔ours index convention, the shared `is_defended` (ray-aware) /
  `is_in_bad_spot` / `king_values` gaps, and per-motif divergences for
  skewer/discovered-attack/back-rank/fork/pin/anastasia/hook + discovered-check.

### Prior tactic phases (decisions that constrain this phase)
- `.planning/phases/127-detector-hardening-validation/127-CONTEXT.md` — depth semantics, the
  validation harness, relevance-gate (D-01), min-depth dispatch intent (D-02), precision-blocks /
  recall-reports (D-08), tiered precision floor (D-09), multi-label theme matching (D-10), AGPL
  boundary (D-11), dev-in-phase / prod-deferred re-backfill (D-13).
- `.planning/notes/tactic-tagging-architecture.md` — single `tactic_motif` column, `tactic_confidence`
  as query-time precision knob, motif set + tiers, named-mate capture, severity gate, priority/mate
  dominance.

### Detector + integration code
- `app/services/tactic_detector.py` — `detect_fork:333` (missing forker-safety gate), `detect_pin`,
  `_is_hanging:256` (non-ray; replace with ray-aware `is_defended`), `_piece_value` (no king entry),
  `detect_tactic_motif:1798-1804` (the `(tier, rank, depth)` sort to invert to depth-primary).
  Tier registries `_NAMED_MATE_REGISTRY` / `_GEOMETRIC_REGISTRY` / `_TIER3_REGISTRY`.
- `app/services/flaws_service.py:424-434` — the missed pass (`detect_tactic_motif(board_before,
  best_pv)`); Workstream B dest-square gate lands here. `move_san_of_flaw` used only on the allowed
  branch today.
- `app/services/engine.py:99` — `PV_CAP_PLIES = 12` (why mate must be gated on the Stockfish score,
  D-06).
- `scripts/backfill_flaws.py` — runs `classify_game_flaws`; the dev re-backfill path (D-12).
- `app/models/game_flaw.py` — `tactic_motif` / `tactic_piece` / `tactic_confidence` / `tactic_depth`
  columns.
- `tests/services/test_tactic_detector.py` — home for the Workstream B `(flaw_move, best_line)` unit
  fixtures (D-04).

### Validation tooling
- `scripts/tactic_tagger_report.py` — `--check-goals` mode (raise GOALS to 0.9 for in-scope motifs,
  recall ungated); the `/tactic-tagger-report` skill for the full per-motif table.
- `reports/tactic-tagger/tactic-tagger-2026-06-20.md` — the precision baseline this phase improves on.
- lichess CC0 puzzle fixture (already committed; `database.lichess.org/#puzzles` is the source) —
  ground truth for Workstream A. No new puzzle data needed for in-scope motifs.

### AGPL reference (read for pseudocode, never copy source)
- `/home/aimfeld/Projects/Python/lichess-puzzler/tagger/cook.py` and `util.py` — the oracle.
  Reimplement predicates from the cook-alignment note's prose; copy no source (D-10).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`tactic_confidence` query-suppression lever** — already the mechanism for "tag→NULL at query
  time" (`AND tactic_confidence >= t`). Failing motifs (D-02/D-11) are suppressed through it; no new
  suppression machinery needed.
- **`scripts/backfill_flaws.py` + `classify_game_flaws`** — the existing recompute path; the dev
  re-backfill (D-12) reuses it, no new script.
- **`scripts/tactic_tagger_report.py --check-goals`** — the measurement/regression harness already
  exists (Phase 127); this phase raises GOALS and drives precision against it.
- **Per-detector loop indices already carry depth** (Phase 127 added the 4-tuple `(fired, piece,
  confidence, depth)` contract) — the depth-primary dispatch (D-05) consumes data already produced.

### Established Patterns
- **Detector = pure CPU, reads stored `pv` at `flaw_ply+1`**, `pov = board_after_flaw.turn`. No
  engine in the detector; hardening stays inside this contract (the mate-in-x gate, D-06, reads the
  already-stored Stockfish score, not a new engine call).
- **Single tag per flaw, clean `GROUP BY tactic_motif`** — the dispatch change (D-05) must preserve
  "exactly one winning motif"; it changes *which* motif wins, not the cardinality.
- **Slow detector/harness tests live in a default-excluded directory** (Phase 127 D-14,
  `tests/scripts/tagger/` parallel to `tests/scripts/benchmarks/`), run on demand / in CI with an
  explicit path. The precision gate is a dedicated CI step, not part of `uv run pytest -n auto`.

### Integration Points
- Shared-utility ports (`is_defended` ray-aware, `is_in_bad_spot`, `king_values`) ripple into
  fork/pin/skewer/hanging/interference — every consumer must be re-verified for regression after the
  port (D-08 leaks across motifs).
- Dispatch inversion (D-05) is the highest-blast-radius change: ply-outer/detector-inner walk with
  early-exit replaces detector-outer collect-then-sort; preserve mate-first (D-06) and the
  hanging-piece-first-class rule (D-07).
- Workstream B (D-03) is a localized call-site gate in `flaws_service.py:424-434`, independent of the
  detector internals but validated separately (D-04).

</code_context>

<specifics>
## Specific Ideas

- The governing product value: a wrong, *visible* tag erodes trust in a stats product more than a
  missing one. This is why every gray-area call resolved precision-first — full port then suppress
  (D-02), dest-square gate to kill false "you missed it" alarms (D-03), dev re-backfill so
  known-wrong tags stop rendering (D-12).
- The four lowest-precision geometrics (fork/discovered-attack/pin/skewer) are 82.6% of all tag
  volume at confidence 100 (always shown). Volume-weighted held-out precision across the top five is
  ~0.31 today — roughly two of three chips a user sees are wrong. This phase's job is to make that
  honest.

</specifics>

<deferred>
## Deferred Ideas

- **Prod re-backfill execution** — runbook step after this phase ships (D-12); lichess-only-eval
  games fill in over time via the existing tier-3 idle fleet.
- **All Tier-3 tactics** (deflection, attraction, intermezzo, x-ray, interference, clearance,
  capturing-defender, sacrifice) — ~1.8% of tag volume, already query-suppressed; cook's logic is
  sequence-relational and our reimplementations use loose `met >= N` thresholds. Low ROI now; defer
  to a later phase.
- **A hand-labeled prod-flaw precision set** — explicitly deferred; the CC0 puzzle fixture stays the
  ground truth for Workstream A, accepting that Workstream B is validated separately.
- **Adding the captured-piece-value check to the Workstream B comparator** — only if unit fixtures
  expose a false suppression (D-03); not in scope unless evidence demands it.
- **SEED-058** (new tactic motifs / lichess coverage), **SEED-062** (tactic-comparison orientation
  basis) — separate seeds, not this phase.

### Reviewed Todos (not folded)
- The todo matcher surfaced only generic keyword false-positives (Phase 70 requirements amendments,
  Recovery-score-gap popover copy, a Tailwind score-axis label) — none touch tactic precision.
  Reviewed and not folded; out of scope.

</deferred>

---

*Phase: 131-tactic-precision-hardening-cook-alignment*
*Context gathered: 2026-06-22*
