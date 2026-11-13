# Phase 250: Facepalm-Blunder Selection (SEED-261110-p7k) - Context

**Gathered:** 2026-11-12 (distilled from SEED-261110-p7k, the label study in
`reports/blunder-check/leg2-labels-2026-11-11.tsv` and owner answers in session; not a discuss-phase run)
**Status:** Parked (owner, 2026-11-12). Resume planning once the short-stored-line fix (SEED-261112-s4v) is in and
the truncated lines are re-evaluated on prod. On resume: re-check the pass rates and, if possible, the labels
against the corrected lines, since the label study ran on the truncated lines as stored.

<domain>
## Phase Boundary

Phase 249 selects blunder-check windows with a findability rule (249 D-06) built on single-move Maia probabilities.
Owner spot checks showed it lets through blunders that are too hard to see (Window 14). A label study (190 owner
labels, six sets, the last five blind) produced a replacement that needs no new Stockfish work: the facepalm-blunder
rule. This phase stores what the rule needs, backfills it, swaps the selection predicate, and retires the Maia columns
the old rule used. Deliverables:

1. Two stored facts per user-side blunder on `game_flaws`: the reply spread and the line material result.
2. A scorer used by both the go-forward hook (new games) and a prod backfill script.
3. The blunder-check candidate predicate rewritten onto the new rule, thresholds as named constants.
4. A re-run of the calibration and spot-check reports against the new rule.
5. Removal of the nine Maia columns nothing reads any more.

</domain>

<decisions>
## Implementation Decisions

### The rule (owner, 2026-11-12)
- **D-01: One rule for every user blunder.** A user-side blunder (engine drop >= `BLUNDER_DROP`, unchanged) is a
  facepalm blunder when all three hold. No special cases for missed punishments, no per-case branches. This replaces
  249 D-06 and overturns 249 D-08 ("no capture/check/mate rule").
  1. **Peers rarely play it:** `maia_played_prob <= PLAYED_PROB_MAX` (0.3). Already stored (Phase 247).
  2. **The punishment is obvious:** reply spread `<= REPLY_SPREAD_MAX` (3.0). Reply spread = effective number of
     opponent replies at ply+1: `exp(entropy)` of the Maia policy at the user's pinned Elo
     (`pinned_elo_for_mover`), over the top moves up to 90% cumulative mass, at most 8, renormalised. This
     truncation is part of the definition: the labels were scored with it.
  3. **It loses material fast:** following the stored refutation line (`game_positions.pv` at flaw ply + 1) for
     `LINE_DEPTH` (3) plies, the blunderer is down `>= LINE_LOSS_MIN` (2) points net, or is mated within the depth.
- **D-02: Material count along the line** (reference implementation: `capture_loss` in
  `temp/blunder-check/refine.py`, exploratory, to be rewritten as app code with tests):
  - piece values 1 / 3 / 3 / 5 / 9; only captures count, promotions are not material;
  - the blunder move's own capture counts in the blunderer's favour (baseline is the position before the blunder);
  - the blunderer's recapture at depth + 1 is included when the line has it;
  - an opponent capture of a piece that the blunderer's previous line move placed there without capturing is
    ignored (engine desperado or spite check in a lost position);
  - a line that ends on an opponent capture before depth + 1 gets a static-exchange recapture credit;
  - a blunder with no stored line does not qualify (about 7% of sampled user blunders).
- **D-03: False alarms are worse than misses** (owner). Tune for the share of fair positions among passers, not for
  coverage. 85% fair was accepted as good enough for the beta; the refined count measured 62 fair / 2 unfair on the
  labels (in-sample for set 6). Expect the rule to drop roughly half of what the owner would call a facepalm blunder.
- **D-04: Thresholds are named constants** next to the existing blunder-check selection constants, one per knob in
  the seed's knob table (line depth, material lost, played probability, reply spread, mate on/off). One depth for
  all ratings in this phase.

### Storage (Claude's recommendation, owner to confirm at planning)
- **D-05: Store raw facts, not the verdict,** so every knob stays tunable without recomputation. On `game_flaws`,
  nullable, NULL = not scored:
  - `maia_reply_spread` REAL;
  - the net line loss at depths 1, 3 and 5 (three SMALLINT) and the ply of mate within the line (SMALLINT, NULL =
    no mate). Depth 1, 3, 5 are the depths measured in the study.
  The planner may propose a tighter shape, but the predicate must stay a plain SQL filter on `game_flaws`.
- **D-06: Scope = user-side blunders only** (severity blunder, mover is the game's user), as in Phase 248's
  refutation stats. Not mistakes, not the opponent's moves.

### Computation
- **D-07: No Stockfish, no worker lane.** Reply spread is one Maia inference at ply+1 on the server, added to the
  existing post-apply Maia hook (`score_game_flaws_after_apply`; Phase 248's refutation scoring already runs Maia at
  ply+1 there). The line loss is a pure replay of the stored line.
- **D-08: Backfill script** for the roughly 2.3M existing user blunders, same pattern as
  `scripts/backfill_maia_flaws.py` (hash-residue shards, stamp-as-checkpoint, resumable). Same scorer as the hook.
- **D-09: Selection swap.** `app/services/blunder_check_candidates.py` and
  `app/repositories/blunder_check_repository.py` read the new columns in place of the best / refutation pairs. All
  other Phase 249 selection decisions stand (hazard model, Good bar, eval band, supply order, no repeats).
- **D-10: Calibration re-run.** Re-run the Phase 248 calibration and spot-check scripts on prod with the new
  predicate (`scripts/blunder_check/`), and report supply per rating band: the rule passes about 16-30% of user
  blunders below 2000, 17% at 2000-2399 and 7% at 2400+ in the samples, so pool size at low game counts and at
  high ratings must be checked.

### Column cleanup (owner intent 2026-11-11, confirmed direction 2026-11-12)
- **D-11: Keep `maia_played_prob`. Drop the other nine** once the new selection is live and checked on prod:
  `maia_played_rank`, `maia_best_prob`, `maia_best_rank`, `maia_second_prob`, `maia_second_rank`, `maia_top_prob`,
  `maia_effective_moves`, `maia_refutation_prob`, `maia_refutation_rank`. Readers today are the Maia scoring and
  backfill code, the D-06 selection, and the calibration scripts; no frontend or API reader. The drop is the last
  plan of the phase so a rollback to D-06 stays possible until then. Stop computing them in the hook at the same
  time. Check SEED-261110-cqk (chess.com-style miss classification) for a claim on `maia_best_*` before dropping.

### Claude's Discretion
- Column names for the line-loss values and where the scorer module lives.
- Whether the line loss is computed in the same hook as reply spread or at flaw-classification time.
- Backfill shard count and pacing (prod RAM and DB are the binding constraints, not CPU).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `.planning/seeds/SEED-261110-p7k-blunder-check-peer-loss-selection.md` — full history: rules tried, the label
  study, set 5 and 6 results, refinements, the knob table, cautions.
- `reports/blunder-check/leg2-labels-2026-11-11.tsv` — 190 owner labels with per-row values.
- `.planning/phases/249-blunder-check-playable-mvp/249-CONTEXT.md` — D-03..D-11 selection decisions that stand,
  D-06 and D-08 that this phase replaces.
- `temp/blunder-check/refine.py`, `pvmat.py`, `mech.py`, `set6.py` — exploratory reference code (gitignored, on the
  dev box only): `capture_loss`, reply spread via `peer_legs.top_moves` + `mech.eff`.
- `app/services/maia_flaw_scoring.py`, `app/repositories/game_flaws_repository.py`, `scripts/backfill_maia_flaws.py`
  — Phase 247/248 scoring and backfill pattern to extend.

</canonical_refs>

<specifics>
## Specific Ideas

- Fixtures for the material count should include the six unfair set-6 passers (#153, #156, #165, #170, #176, #177)
  and the four fair positions the refinements dropped (#13, #35, #154, #184); the seed lists what each one shows.
- Window 14 (game 2099808, flaw ply 23) must fail the new rule (reply spread 4.4).

</specifics>

<deferred>
## Deferred Ideas

- **Facepalm filter tag** for games and flaw lists: needs reply spread for whatever the tag covers and a decision
  on opponent blunders (Maia at the opponent's rating).
- **Rating-dependent line depth** (5 to 7 plies above 2000, to catch forks that cash in later): enlarges the pool
  there but has no labels to back it.
- **Short stored engine lines** (1-2 plies with no obvious reason): separate investigation started 2026-11-12; this
  phase only handles them with the D-02 recapture credit.
- **Stockfish-based legs** (expected loss, reply loss, practical loss, worker lane): the fallback design in the
  seed, not needed by this rule.
- **A fresh blind label set** for the refined count, and labels above 2000 from a stronger player.

</deferred>

---

*Phase: 250-facepalm-blunder-selection*
*Context gathered: 2026-11-12*
