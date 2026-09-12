---
id: SEED-165
status: promoted (→ Phase 221, 2026-09-12)
planted: 2026-09-12
planted_during: ad-hoc tactic-tagger review (reports/tactic-tagger/tactic-tagger-review-2026-09-12.md)
trigger_when: next tactic-quality window; MUST land before any data story or benchmark that uses tactic-motif rates (sacrifice/clearance rates are ~50-80% noise today)
scope: one phase — forcing-gate winning floor + gate-skip fix, sacrifice/clearance predicate tightening, seven fixture-verified cook-port fixes, missed-orientation parity, a real-game hand-labelled gate beside the fixture gate, offline prod retag
---

# SEED-165: Tactic tags fire on losing lines and on cook.py's weakest predicates

## Symptom

Users see "allowed sacrifice" / "allowed clearance" chips that describe no tactic they
could have avoided, plus occasional missed real tactics. The 2026-09-02 fixture report
shows 0.998 precision, so the fixture gate cannot see it.

## Diagnosis (2026-09-12, full detail in `reports/tactic-tagger/tactic-tagger-review-2026-09-12.md`)

1. **The detector is a near-exact cook.py clone on puzzle lines** (oracle run over all
   26,649 fixture rows). Remaining errors are about *which lines* the predicates run on.
2. **Tags fire where the tagging side is losing.** Solver-perspective eval at the firing
   node, read from the stored MultiPV blob (prod 3% sample): 78% of allowed `sacrifice`,
   47% of `clearance`, 23% of `intermezzo`, 13% of `deflection`, 11% of all allowed tags.
   Sacrifice is ~7.7% of the 777k allowed tags (~60k rows) and 56% of all losing-line tags.
3. **Two gate holes.** (a) `_classify_tactic_gated` skips the whole forcing gate when
   `pre_flaw_eval_cp is None` (mate-ladder flaws): 77% of allowed sacrifice tags in prod.
   (b) Nothing requires the solver to be winning at the firing node (Phase 144 moved the
   +200 floor to the conversion tail), and the only-move cp-gap test passes trivially in
   lost positions (all 60 losing missed-sacrifice tags in dev were gated and passed).
4. **cook's `sacrifice` is "down ≥2 at any pov move ≥2"**: 32% of cook's own sacrifice
   puzzles are delayed recaptures; avg firing depth 5.2 in prod. **cook's `clearance`** is
   loose geometry: 9 of 12 hand-reviewed dev tags were king retreats, pawn pushes, piece
   shuffles.
5. **Cook-port divergences** (fixture-verified): deflection promotion OR-branch (−297
   recall), fork D-01 gate not in cook (−130, zero precision gain), trapped-piece immobile
   exclusion (−107, zero FP cost), discovered-attack `continue` vs `return` (+16 FP),
   boden/double-bishop file edge, dead `self-interference` (14) still in dispatch (can win
   and persist an invisible tag), discovered-attack depth stored as k−1 on 100% of rows.
6. **Missed orientation has no move stack**: intermezzo cannot fire at k=2 (prod 188
   allowed vs 6 missed) and the hanging-piece recapture exclusion is off (33/302 dev rows).
7. `discoveredCheck` labels are not cook output (cook never emits the theme); our port only
   reproduces 56% of them.

## Fix simulations (dev DB, 8,324 tags)

- Solver floor +100 at firing: −324/551 allowed sacrifice, −69/161 clearance, −21/64
  intermezzo, −24/109 deflection, −44/1213 hanging-piece, −24/923 fork.
- Sacrifice floor + persistence (deficit still ≥2 after the next pov move): 697 → 54,
  survivors hand-checked as genuine sacrifices.
- Fork without the D-01 gate and trapped-piece with cook's immobile rule: both reproduce
  cook exactly on every fixture row, 0 new FPs vs labels.

## Explicitly not in this seed

New motifs, ML, schema changes, MultiPV re-evaluation (the retag is offline via
`scripts/retag_flaws.py`), frontend changes beyond copy, changing `PV_CAP_PLIES`.
