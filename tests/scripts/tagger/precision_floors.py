"""Per-motif precision floor constants for the tagger validation harness.

Floors are set from the MEASURED numbers produced by the harness against the TRAIN
fixture. They are downstream of measurement — never hardcoded before the
harness runs — and are asserted on TRAIN only (the held-out TEST set is never used
to set floors; see test_detector_precision.py).

Measurement run summary (2026-06-19, 11,855-row TRAIN CC0 fixture — re-sampled at
200/stratum and split 70/30 train/test to reduce overfitting risk; the fork
relevance gate applied, since removed). TEST precision shown for reference (held out, not gated):

  Motif                  TP    FP    FN   P(train) Recall  P(test)
  -----------------------------------------------------------------------
  anastasia-mate        458    99     0    0.822   1.000   0.857
  arabian-mate            0     0   553    NaN     0.000   NaN    (never fires)
  attraction              0    10  1603    0.000   0.000   0.000
  back-rank-mate        854  2182     2    0.281   0.998   0.271
  boden-mate              0     0   437    NaN     0.000   NaN    (never fires)
  capturing-defender      0     3   610    0.000   0.000   NaN    (only-FP)
  clearance              13    17   712    0.433   0.018   0.833
  deflection             24   160  1153    0.130   0.020   0.141
  discovered-attack     204   855   800    0.193   0.203   0.198
  double-check           28     0   719    1.000   0.037   1.000
  dovetail-mate           0    23   544    0.000   0.000   0.000  (only-FP)
  fork                 1218  1567   339    0.437   0.782   0.400
  hanging-piece          97     1   637    0.990   0.132   0.952
  hook-mate             529   101    39    0.840   0.931   0.841
  interference           21     0   575    1.000   0.035   1.000
  intermezzo              0     5   702    0.000   0.000   0.000  (only-FP)
  mate                 1013     0  4714    1.000   0.177   1.000
  pin                   336   428   867    0.440   0.279   0.439  (gate fix)
  sacrifice               0     0  3142    NaN     0.000   NaN    (never fires)
  skewer                149   770   523    0.162   0.222   0.154
  smothered-mate        468     0     0    1.000   1.000   1.000
  x-ray                   0    10   642    0.000   0.000   0.000  (only-FP)

Train and held-out test precision track closely for every shipped motif (max gap a
few pp), so the post-127 detector generalizes rather than overfitting the fixture.

Move-type and discovered-check measurement run (2026-06-20, same 11,855-row TRAIN fixture with all 29
motifs present). New motifs:

  Motif                  TP    FP    FN   P(train) Recall  P(test)  Floor posture
  -----------------------------------------------------------------------------------------
  discovered-check       44     6   960    0.880   0.044   0.833    Normal % floor (1004 TRAIN labels)
  trapped-piece           0     9    28    0.000   0.000   0.000    Only-FP → SUPPRESSED
  en-passant              0     0    12    NaN     0.000   NaN      Never fires → SUPPRESSED
  promotion               1     0   179    1.000   0.006   NaN      Thin (1 TP); % floor at 0.60
  under-promotion         0     0     4    NaN     0.000   NaN      n=4; never fires → SUPPRESSED

Measurement run (2026-06-22, same 11,855-row TRAIN fixture). Cook-aligned
ports for fork, skewer, discovered-attack, pin; TEST is the 5,164-row held-out split:

  Motif                  TP    FP    FN   P(train) P(test)  Decision
  -----------------------------------------------------------------------------------------
  fork                  993     1   564    1.000   0.998    SHIPPED — exceeds 0.90 TEST
  skewer                432     0   240    1.000   1.000    SHIPPED — exceeds 0.90 TEST
  discovered-attack     321     2   136    0.995   1.000    SHIPPED — exceeds 0.90 TEST
  pin                   453   149   750    0.752   0.819    was SUPPRESSED — below 0.90 TEST
  pin (odd-board fix)   699    49   504    0.934   0.944    SHIPPED — odd-board scan (see below)

Measurement run (2026-06-23, same 11,855-row TRAIN / 5,164-row TEST fixture).
Cook-aligned AND-chain rewrites for deflection (11 conditions) and clearance (9 conditions),
replacing graded `_grade(met, total)` voting with exact relational AND-chains:

  Motif                  TP    FP    FN   P(train) P(test)  Decision
  -----------------------------------------------------------------------------------------
  deflection            162     1  1015    0.994   1.000    SHIPPED — exceeds 0.90 TEST
  clearance             199    19   526    0.913   0.952    SHIPPED — exceeds 0.90 TEST

Measurement run (2026-06-23, same 11,855-row TRAIN / 5,164-row TEST fixture).
Cook-aligned AND-chain rewrites for capturing-defender (9 conditions, init-board defender
test) and intermezzo (zwischenzug signature: moves[k-3] original-capture + was-legal-earlier),
both replacing graded voting with exact relational AND-chains:

  Motif                  TP    FP    FN   P(train) P(test)  Decision
  -----------------------------------------------------------------------------------------
  capturing-defender    326    49   284    0.869   0.903    SHIPPED — exceeds 0.90 TEST
  intermezzo             39     4   663    0.907   1.000    SHIPPED — exceeds 0.90 TEST

Measurement run (2026-06-23, same 11,855-row TRAIN / 5,164-row TEST fixture).
Cook AND-chain ports for attraction (§4 lure+capture+attack+follow-up), x-ray (§6 three-
same-square guard + between-square geometry), and sacrifice (§7 material-diff predicate):

  Motif                  TP    FP    FN   P(train) P(test)  Decision
  -----------------------------------------------------------------------------------------
  attraction              0     0  1603    NaN     NaN      SUPPRESSED — 0 TP on TRAIN
                                                             after this cook port. An off-by-one
                                                             in cond-5 (attacker board was boards[k+2],
                                                             should be boards[k+3]) produced 0 TP.
                                                             Fixed in the next run below.
  x-ray                 225     0   417    1.000   1.000    SHIPPED — exceeds 0.90 TEST. Cook three-
                                                             same-square AND-chain (moves[k-2].to ==
                                                             moves[k-1].to == moves[k].to + between-
                                                             square geometry + non-king recapturer).
                                                             Floor set at 0.93 (~7pp below TRAIN 1.000).
  sacrifice               0     0  3142    NaN     NaN      SUPPRESSED — 0 TP in this run because
                                                             the detector is standalone-precision 1.000
                                                             but its recall is limited by dispatch order:
                                                             higher-priority mates, fork, and pin
                                                             shadow it in ~92% of positions. Fixed in
                                                             the next run via unsuppress-only (no co-tag
                                                             needed); see the next block.
  interference          269     3   327    0.989   0.992    NO REGRESSION from interference logic
  (post-attraction)                                          (detect_interference UNCHANGED). Prior
  (post-sacrifice)                                           measurement (0.985 TRAIN / 0.986 TEST)
                                                             was mid-port, before sacrifice fixture
                                                             collision fixes. Final measurement after
                                                             all cook ports: 0.989 TRAIN / 0.992 TEST.
                                                             Floor 0.80 still holds with large headroom.

Measurement run (2026-06-23, same 11,855-row TRAIN / 5,164-row TEST fixture).
Detector fixes for attraction (boards[k+3] off-by-one), arabian-mate (cook attacker-of-
rook-sq knight geometry), boden-mate (cook near-king bishop-only attacker loop), and
dovetail-mate (cook diagonal-adjacency + escape-square loop, both bugs A and B). Sacrifice
is unsuppress-only (standalone precision already 1.000; unsuppressed without code change):

  Motif                  TP    FP    FN   P(train) P(test)  Decision
  -----------------------------------------------------------------------------------------
  attraction            654     0   949    1.000   ~1.000   SHIPPED — off-by-one fixed.
                                                             Floor set at 0.93 (~7pp below TRAIN 1.000).
  arabian-mate          553     0     0    1.000   ~1.000   SHIPPED — cook attacker-of-rook-sq + (2,2)
                                                             knight geometry.
                                                             Floor set at 0.93 (~7pp below TRAIN 1.000).
  boden-mate            435     0     2    1.000   ~1.000   SHIPPED — cook near-king bishop-only
                                                             attacker loop.
                                                             Floor set at 0.93 (~7pp below TRAIN 1.000).
  dovetail-mate         543     0     1    1.000   ~1.000   SHIPPED — cook diagonal-adjacency + escape-
                                                             square loop.
                                                             Floor set at 0.93 (~7pp below TRAIN 1.000).
  sacrifice             236     0  2906    1.000   ~1.000   SHIPPED — unsuppress-only.
                                                             Standalone precision 1.000 / recall 0.075
                                                             post-dispatch (shadowed by higher-priority
                                                             mates/fork/pin in ~92% of positions).
                                                             Floor set at 0.93 (~7pp below TRAIN 1.000).

Measurement notes:
  - discovered-check (1004 TRAIN labels, 397 TEST): fires at P=0.880 train / 0.833 test.
    Recall is ~4.4% — the motif shadows only non-mating discovered-check lines (the other
    960 FN are positions tagged discoveredCheck that also contain mate, fork, or skewer at a
    higher-priority tier). Floor set at 0.80 (~8pp below measured).
  - trapped-piece (fixture expansion — ~1065 combined: 748 TRAIN / 317 TEST):
    the fixture was expanded from the thin 28/11 baseline via the per-motif --oversample-motifs
    cap (trapped-piece:250/stratum) against the fresh 2026-06 lichess dump (full-regen
    variant). The cook capture-chain-anchored is_trapped
    predicate achieved P(train)=1.000 (565 TP, 0 FP) / P(test)=1.000
    (239 TP, 0 FP), deltaP=0.000 — clearing the ≥0.80 bar on both sets. Shipped:
    removed from SUPPRESSED_MOTIFS, PRECISION_FLOOR added below.
  - en-passant (expanded fixture — 1960 TRAIN / 845 TEST labels):
    P(train)=P(test)=1.000 (~590 TP, 0 FP), R≈0.30. The old note ("NaN, 12
    labels, never fires") described the thin pre-expansion fixture; the larger fixture leaves
    enough residual rows where no higher-priority tactic wins the Tier-5 dispatch for the
    detector to fire cleanly. Unsuppressed and shipped as an "Advanced" chip family. Floor
    0.93. Still structurally validated by the _EN_PASSANT_FIXTURES fast-guard set.
  - promotion (176 TRAIN labels including underPromotion, 57 TEST): fires once (TP=1, FP=0,
    P=1.000 train). Like en-passant, most promotion rows have a higher-priority tactic.
    1 TP is very thin but the precision is 100% — floor set conservatively at 0.60 to allow
    for variance while still catching zero-precision regressions.
  - under-promotion (expanded fixture — 780 TRAIN / 332 TEST labels):
    P(train)=P(test)=1.000 (~91 TP, 0 FP), R≈0.12. The old note ("NaN, n=4,
    Tier-1 mate pre-empts every case") described the thin pre-expansion fixture. On the larger
    fixture it fires cleanly on the residual; thinner TP pool than en-passant, so the floor is
    0.90 (slightly more conservative). Unsuppressed and shipped as an "Advanced" chip family.
    Still structurally validated by the _UNDER_PROMOTION_FIXTURES fast-guard set, whose
    `test_positives_fire_expected_motif[under-promotion]` is the never-regress assertion.
  - pin (cook port, then node-set fix): the full cook two-sub-test port lifted TEST
    precision from 0.474 to 0.819 but stayed below the 0.90 ship bar, so it was suppressed.
    The follow-up fix found the remaining gap was a node-set bug: detect_pin scanned
    EVERY board in the PV, whereas cook checks pins only on the boards that follow a POV
    (winning-side) move. boards[0] is pov-to-move, so pov's moves land on the ODD indices
    (boards[1], boards[3], ...). Scanning only those (`range(1, len(boards), 2)`) removes the
    incidental / pre-existing pins that fired on pov-to-move boards inside opponent forcing
    lines (attraction, deflection, sacrifice). Isolated precision 0.477 -> 0.947; post-dispatch
    0.752 -> 0.934 TRAIN / 0.819 -> 0.944 TEST, recall held (~0.60). Pin is now SHIPPED with a
    0.90 floor. FAMILY_TO_MOTIF_INTS already carries it.

Precision floors are set at ~5-8pp below the measured TRAIN value (rounded to 0.05)
to give a stable CI gate that fails on genuine regressions, not normal variance.
Motifs with NaN precision (never fire) or only-FP (0 TP, >0 FP) are in SUPPRESSED_MOTIFS.

Suppression notes:
  Tier-3 motifs in SUPPRESSED_MOTIFS are filtered at query time via the
  MIN_TACTIC_CHIP_CONFIDENCE lever in library_repository.py (currently 70).
  Tier-1/2/5 motifs (confidence always 100) cannot be suppressed via this lever —
  their detectors fire rarely enough that they do not materially affect the UI in
  practice, but their floors are omitted from PRECISION_FLOOR (no gate for motifs
  that do not reliably fire).

Real-game floors are a SEPARATE, orthogonal measurement:
  PRECISION_FLOOR above scores the detector against cook.py's lichess-puzzler
  labels on CC0 puzzles — capped, forcing, curated lines. REALGAME_REAL_SHARE_FLOOR
  below scores the SAME detector against a hand-labelled sample of ~150 real
  `game_flaws` tags — 12-ply-capped, non-forcing, sometimes-losing engine PVs from
  actual user games. A motif can legitimately have high puzzle precision AND low
  real-game real-share at the same time: this is not a contradiction.
  The puzzle fixture is structurally blind to losing lines, capped PVs and
  non-forcing tails — see the review report
  `reports/tactic-tagger/tactic-tagger-review-2026-09-12.md` §3. Never conflate
  the two floor dicts, and never "fix" a real-game floor regression by relaxing
  PRECISION_FLOOR (or vice versa) — they measure different populations.

`discoveredCheck` labels are NOT cook output. cook's `TagKind` (this
  local AGPL clone) has no `discoveredCheck` theme at all — of the 2,854 TRAIN+TEST
  fixture rows carrying the lichess `discoveredCheck` label, only 1,585 (56%)
  satisfy `cook.discovered_check` when recomputed via `scripts/research/
  oracle_compare.py` (measured 2026-09-12; see the review report §3). Our
  `discovered-check`'s measured PRECISION_FLOOR is therefore scored against a
  lichess theme whose provenance is NOT cook — most likely lila-side or crowd
  voting. Re-scoring `discovered-check` against a different, cook-derived label
  source is explicitly OUT OF SCOPE (documented only); do not attempt it as a
  drive-by fix.

An oracle comparison exists at `scripts/research/oracle_compare.py`.
  It replays every committed fixture row through both our standalone detector
  functions and cook.py itself (the local AGPL lichess-puzzler clone, imported
  by path at runtime only — see its own module docstring for the boundary), and
  prints a three-way agreement table (`both` / `cookOnly` / `oursOnly` / `neither`)
  per motif. "Matches cook" means: for every fixture row, our detector's fire/
  no-fire verdict for that motif equals cook's recomputed verdict for the
  corresponding cook function (see the mapping inside `oracle_compare.py::ours` /
  `::cooks`). Two prior "precision-first" deviations from cook were disproved by
  this comparison and must not be reintroduced by a future precision pass:
    1. Fork's "relevance gate" (`material_at_end < material_at_start ->
       skip`) — NOT in cook. Removing it cost 130 detections for ZERO measured
       precision change (all 130 were sac-then-mate lines cook itself tags).
    2. Trapped-piece's empty-escape exclusion (`if not escape_moves: return
       False`) — NOT in cook (cook: an immobile attacked non-pawn/non-king piece
       IS trapped). Reverting it cost 107 detections for ZERO new false
       positives.
  The clearance strengthening (vacating-piece restriction, "line is used" clause,
  depth cap) IS a deliberate divergence from cook (unlike the two disproved
  deviations above) — a fixture recall drop on that motif is EXPECTED BY DESIGN.
  Relaxing it to recover fixture recall is the failure mode to prevent; a third
  "precision-first" deviation from cook has to argue against a recorded
  measurement, not intuition. See the block comment directly above the
  `sacrifice` and `clearance` PRECISION_FLOOR entries below for the full
  divergence record (a sacrifice persistence rule was also tried and retired).

Deliberate divergences from cook for `sacrifice` and `clearance` (2026-09-12) — see the
block comment above the `sacrifice` and `clearance` entries in PRECISION_FLOOR for
the full record. In short: `clearance` gained a vacating-piece restriction, a
"line is used" clause, and a depth cap; `sacrifice` gained a depth cap and a
persistence rule (since retired). The clearance additions are a DELIBERATE,
never-relax divergence from cook — recall falling on the CC0 fixture is
expected by design, precision must not fall (it did not: both stay at 1.000
TRAIN/TEST). `sacrifice` and `clearance` are ALSO scored against hand-labelled
real-game rows via REALGAME_REAL_SHARE_FLOOR (a separate, orthogonal measurement —
see that section's own docstring); the two floor dicts can legitimately
disagree, and the real-game number is the one that matters. Never relax the
clearance additions to recover either measurement — the depth cap
(`SACRIFICE_CLEARANCE_MAX_DEPTH`) is the only sanctioned lever if a future
measurement finds clearance's cut too soft (clearance is currently SUPPRESSED
regardless — see SUPPRESSED_MOTIFS).

Retiring the sacrifice persistence rule (2026-09-13): an operator review of the
hand-labelled real-game rows overturned the assumption the rule rested on —
two of the four rows it measured as "correctly dropped" are genuine
sacrifices its literal persistence check cannot distinguish from a delayed
recapture. No board-derivable replacement discriminator survived the
evidence (three candidates tried, all fail on at least one confirmed-real or
confirmed-wrong row). `detect_sacrifice` is reverted to cook's unguarded
predicate; the depth cap is unchanged (it was never implicated). The
persistence rule was a reasonable, measured hypothesis that a later, larger
piece of evidence disproved. See the block comment above the `sacrifice`
PRECISION_FLOOR entry and the `sacrifice` REALGAME_REAL_SHARE_FLOOR entry for
the full measurement.

Final consolidated PRECISION_FLOOR measurement across the sacrifice/clearance
rework (TRAIN 18,632 rows / TEST 8,017 rows, same CC0 fixture every table above scored
against), taken AFTER clearance's suppression (the last detector/registry change of that
work) so these are the true final numbers. TP counts moved purely from downstream
dispatch redistribution as the sacrifice/clearance depth cap and persistence rule,
discovered-attack's depth=k, the per-tier winning floor, and finally clearance's
registry removal landed, and from clearance's own removal freeing its former
dispatch wins to other motifs. No PRECISION_FLOOR value was lowered anywhere in that
work — every floor below still holds with the same or larger headroom than when it
was last set, so none needed raising either (the one exception, discovered-attack,
was already raised 0.93->0.95 earlier to lock in its own zero-FP gain).
`clearance` is SUPPRESSED (TP=0 by design -- the motif can never win dispatch
again; see SUPPRESSED_MOTIFS above):

  Motif                  TRAIN TP  TRAIN FP  TRAIN P   TEST TP  TEST FP  TEST P
  ------------------------------------------------------------------------------
  anastasia-mate               460        0    1.000       219        0   1.000
  arabian-mate                 537        0    1.000       251        0   1.000
  attraction                   857        0    1.000       389        0   1.000
  back-rank-mate                891       0    1.000       358        0   1.000
  boden-mate                    442       0    1.000       161        0   1.000
  capturing-defender            350       0    1.000       137        0   1.000
  clearance (SUPPRESSED)          0       0      NaN         0        0     NaN
  deflection                    650       2    0.997       258        1   0.996
  discovered-attack              475      0    1.000       218        0   1.000
  discovered-check               677     33    0.954       277       19   0.936
  double-check                   232      0    1.000        81        0   1.000
  dovetail-mate                  522      0    1.000       249        0   1.000
  en-passant                    1243      0    1.000       542        0   1.000
  fork                          1203      3    0.998       518        0   1.000
  hanging-piece                  631      0    1.000       271        0   1.000
  hook-mate                      602      0    1.000       213        0   1.000
  interference                   348      1    0.997       170        0   1.000
  intermezzo                     486      0    1.000       212        0   1.000
  mate                           2543     0    1.000      1094        0   1.000
  pin                             988     2    0.998       425        0   1.000
  promotion                     1852      0    1.000       814        0   1.000
  sacrifice                      208      0    1.000        77        0   1.000
  skewer                          509     0    1.000       234        0   1.000
  smothered-mate                  474     0    1.000       242        0   1.000
  trapped-piece                   657     0    1.000       282        0   1.000
  under-promotion                247     0    1.000       111        0   1.000
  x-ray                            273    0    1.000       108        0   1.000

Retiring sacrifice's persistence check (2026-09-13) SUPERSEDES the table above
(see the divergence block above the `sacrifice` PRECISION_FLOOR entry): its TP
count rose sharply (more candidates now fire) and a handful of other motifs
lost a small number of TPs to sacrifice's newly-widened dispatch wins — pure
redistribution, same pattern as every prior change. No FP count changed
anywhere; no floor breached; only sacrifice's own floor changes (0.93 unchanged
in value, now backed by 456/196 TP instead of 208/77):

  Motif                  TRAIN TP  TRAIN FP  TRAIN P   TEST TP  TEST FP  TEST P
  ------------------------------------------------------------------------------
  anastasia-mate               460        0    1.000       219        0   1.000
  arabian-mate                 537        0    1.000       251        0   1.000
  attraction                   853        0    1.000       388        0   1.000
  back-rank-mate                891       0    1.000       358        0   1.000
  boden-mate                    442       0    1.000       161        0   1.000
  capturing-defender            350       0    1.000       137        0   1.000
  clearance (SUPPRESSED)          0       0      NaN         0        0     NaN
  deflection                    630       2    0.997       251        1   0.996
  discovered-attack              463      0    1.000       214        0   1.000
  discovered-check               675     33    0.953       277       19   0.936
  double-check                   232      0    1.000        78        0   1.000
  dovetail-mate                  522      0    1.000       249        0   1.000
  en-passant                    1233      0    1.000       540        0   1.000
  fork                          1198      3    0.998       516        0   1.000
  hanging-piece                  631      0    1.000       271        0   1.000
  hook-mate                      602      0    1.000       213        0   1.000
  interference                   340      1    0.997       162        0   1.000
  intermezzo                     464      0    1.000       198        0   1.000
  mate                           2543     0    1.000      1094        0   1.000
  pin                             983      2    0.998       424        0   1.000
  promotion                     1760      0    1.000       764        0   1.000
  sacrifice                      456      0    1.000       196        0   1.000
  skewer                          489     0    1.000       226        0   1.000
  smothered-mate                  474     0    1.000       242        0   1.000
  trapped-piece                  649     0    1.000       276        0   1.000
  under-promotion                240     0    1.000       107        0   1.000
  x-ray                            270    0    1.000       107        0   1.000

Reproduced via `uv run pytest tests/scripts/tagger -q -k test_detector_precision_and_recall -s`.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Motifs suppressed from the precision floor gate
# ---------------------------------------------------------------------------

# Motifs excluded from the assert-precision->= floor gate:
#   - "never fires": NaN precision, 0 TP and 0 FP in the TRAIN measurement run.
#   - "only-FP": 0 TP, >0 FP — zero precision; the detector misfires but never lands a
#     true positive. Named mates here are confidence=100 (cannot suppress via the lever);
#     tier-3 here are suppressed at query time by MIN_TACTIC_CHIP_CONFIDENCE.
SUPPRESSED_MOTIFS: frozenset[str] = frozenset(
    {
        # Unvalidated motifs (no lichess theme equivalent) — excluded from measurement.
        # Self-interference stays in this
        # suppressed set AND is also undispatchable — the ("self-interference",
        # SELF_INTERFERENCE) tuple was removed from _TIER3_REGISTRY (tactic_detector.py),
        # so no PV can ever produce int 14 through the dispatcher again. The int, the
        # reverse-map entry and detect_self_interference are all retained for existing
        # persisted rows and direct unit calls; the full prod retag clears
        # every persisted int-14 row. Dev has zero such rows, so only the prod acceptance
        # query can verify that leg — this fixture harness cannot.
        "self-interference",
        "double-bishop-mate",
        # Clearance is SUPPRESSED (decided 2026-09-12).
        # The keep bar ("keep only if real-game real_share >= 0.80 AND surviving >=
        # REALGAME_MIN_ROWS_FOR_FLOOR") measured real_share=0.667 (2/3 surviving) with
        # only 3 of 16 sampled rows surviving the strengthened predicate — both
        # conditions miss (the row count alone is decisive: a 3-row denominator is not
        # a passing measurement regardless of its share). The ("clearance",
        # TacticMotifInt.CLEARANCE) tuple is removed from _TIER3_REGISTRY
        # (tactic_detector.py) so no PV can ever dispatch it again; the family entry is
        # removed from FAMILY_TO_MOTIF_INTS (library_repository.py) and from
        # frontend/src/lib/tacticComparisonMeta.ts's Advanced group. The enum member
        # (TacticMotifInt.CLEARANCE = 15), _INT_TO_MOTIF[15], _MOTIF_TO_INT["clearance"]
        # and detect_clearance are all retained for existing persisted rows and direct
        # unit calls; the full prod retag clears every persisted int-15 row.
        "clearance",
        # Motifs that were once suppressed and have since shipped (trapped-piece,
        # en-passant, under-promotion, pin, attraction, sacrifice, arabian-mate,
        # boden-mate, dovetail-mate) are no longer listed here; their measurements are in
        # the module docstring and their floors in PRECISION_FLOOR below. promotion (28)
        # is shipped-but-unmapped with its own floor below.
    }
)

# ---------------------------------------------------------------------------
# Per-motif precision floors — set from measured TRAIN numbers
# ---------------------------------------------------------------------------

# Floors sit ~5-8pp below the measured TRAIN precision so the CI gate fails on genuine
# regressions without being brittle to fixture variance. These are the never-regress
# floors; aspirational improvement targets live in GOALS in scripts/tactic_tagger_report.py.
#
# NOTE: the original low floors (back-rank-mate 0.281, fork 0.437, pin 0.440, skewer 0.162,
# discovered-attack 0.163, deflection 0.130) were raised by cook-aligned AND-chain
# rewrites. back-rank over-fires onto corner mates; the geometric detectors carry
# large FP pools. pin's gate fix lifted it 0.413 -> 0.440; the cook port
# raised it further to 0.934 TRAIN. The deflection rewrite raised deflection 0.130 -> 0.994
# TRAIN and clearance 0.348 -> 0.913 TRAIN.
#
# discovered-attack dropped from 0.193 to 0.163 because discovered-check
# (Tier 2, rank 4) now correctly intercepts discovered-attack Sub-case 1 positions — those
# are tagged discovered-check, not discovered-attack, which is correct. The existing
# floor 0.15 still passes (0.163 > 0.15).

PRECISION_FLOOR: dict[str, float] = {
    # --- Tier 2 geometric material-winners (confidence=100) ---
    # Cook-aligned ports (measured 2026-06-22): fork, skewer, discovered-attack floors
    # set to ~5-7pp below measured TRAIN.
    # fork: the relevance gate was removed (not in cook; oracle comparison measured it
    # costing 130 detections for zero precision). TRAIN
    # TP 1168->1184 (+16), FP unchanged (3), P 0.997 (unchanged, 3dp); TEST TP 509->514
    # (+5), FP 0. Floor held at 0.93 (still ~6pp below TRAIN). Later downstream dispatch
    # redistribution (winning floor, sacrifice/clearance depth cap): TRAIN TP 1184->1202 (+18),
    # TEST TP 514->516 (+2), FP unchanged (3 train, 0 test). Floor unchanged at 0.93.
    "fork": 0.93,  # train 0.998 / test 1.000 (1203 TP, 3 FP; final measurement, post clearance suppression)
    "skewer": 0.93,  # train 1.000 / test 1.000 (432 TP, 0 FP; cook port)
    # discovered-attack: the recapture guard now RETURNS
    # (short-circuits the whole predicate) instead of CONTINUE-ing past it, and the
    # returned depth is the pov move index k (not the prior port's max(0, k-1)).
    # TRAIN FP 5->0 (P 0.990->1.000), TP 489->456 (the removed FPs and a handful of
    # now-correctly-excluded recapture lines); TEST FP 4->0 (P 0.982->1.000), TP
    # 216->208. Floor RAISED 0.93->0.95 (~5pp below the new 1.000 TRAIN, matching
    # the file's house convention) to lock in the zero-FP gain. Later downstream
    # dispatch redistribution: TRAIN TP 456->465 (+9), TEST TP 208->211 (+3), FP
    # unchanged (0 both). Floor unchanged at 0.95.
    "discovered-attack": 0.95,  # train 1.000 / test 1.000 (475 TP, 0 FP; final measurement, post clearance suppression)
    # Pin fix (measured 2026-06-22): scan only POV-move result boards (odd PV
    # indices = cook's node set) instead of every board. 0.819 -> 0.944 test / 0.752 -> 0.934
    # train, recall held (~0.60). Floor at the 0.90 ship bar (TRAIN 0.934 clears it).
    # Full-regen re-measure: the larger 2026-06 fixture surfaces more pin FPs.
    # n(train) 1203 -> 1499, P(train) 0.936 -> 0.899 (TP=936, FP=105). Lowered 0.90 -> 0.85
    # (~5pp below new TRAIN; TEST 0.916 clears). Detector unchanged.
    # Tagger precision pass (cook _pin_prevents_escape faithful fix): added cook's missing
    # guard (pinned piece not itself attacking the attacker) + pseudo-legal escape test.
    # Cut incidental-pin FPs 105 -> 2; P(train) 0.899 -> 0.998, P(test) -> 1.000, recall held.
    # Raised floor 0.85 -> 0.92 (~8pp below TRAIN) to lock in the gain.
    "pin": 0.92,  # train 0.998 / test 1.000 (951 TP, 2 FP; cook pin_prevents_escape fix)
    "double-check": 0.93,  # train 1.000 / test 1.000 (never-regress lock; raised from 0.80)
    # discovered-check (never-regress lock, measured 2026-06-22):
    # floor raised from 0.80 to 0.85 (hold ≥0.85).
    # Whole-line scan: detect_discovered_check now scans EVERY pov move
    # (cook.discovered_check `mainline[1::2]`), not just moves[0]. Recall 0.16 -> 0.337
    # train / 0.314 -> 0.322 test; precision 0.953 train / 0.936 test (~1pp train dip, test
    # up). Floor held at the ≥0.85 lock (TRAIN 0.953 clears comfortably).
    "discovered-check": 0.85,  # train 0.953 / test 0.936 (≥0.85 lock; whole-line scan)
    # --- Tier 1 mates (confidence=100) ---
    "mate": 0.95,  # train 1.000 / test 1.000 (unchanged)
    "smothered-mate": 0.93,  # train 1.000 / test 1.000 (never-regress lock; raised from 0.90)
    # Cook geometry tightening (measured 2026-06-22):
    # back-rank-mate: 0.281 -> 1.000 train (own-blocker test + back-rank-checker requirement).
    # anastasia-mate: 0.822 -> 1.000 train (king+1 blocker + king+3 knight geometry + file gate).
    # hook-mate: 0.840 -> 1.000 train (knight-adjacent-to-king constraint added).
    # Floors raised to ~7pp below new measured TRAIN (conservative given mates are small-count motifs).
    "back-rank-mate": 0.93,  # train 1.000 / test 1.000 (was 0.20; cook port)
    "anastasia-mate": 0.93,  # train 1.000 / test 1.000 (was 0.75; cook port)
    "hook-mate": 0.93,  # train 1.000 / test 1.000 (was 0.80; cook port)
    # --- Tier 3 graded + Tier 4 ---
    # deflection: cook 11-condition AND-chain rewrite. TRAIN 0.994 (162 TP, 1 FP),
    # TEST 1.000 (62 TP, 0 FP). Floor set at 0.93 (~6pp below TRAIN 0.994).
    # Tagger precision pass: corrected the deflection port to cook (king_values not values;
    # is_check/attacks on grandpa.board()=boards[k-1] not the init board). FP 9->1, and recall
    # rose 0.14->0.32 (the old boards/values both over-fired and under-caught). P 0.959->0.998.
    # Condition 10 restored to cook's single OR (attacks(orig)
    # OR promotion-same-file-and-reachable), not an if/elif that skipped the attacks disjunct
    # for every promotion move. TRAIN TP 490->618 (+128), FP unchanged (2); TEST TP 197->247
    # (+50), FP 0->1 (still comfortably above floor). Floor held at 0.92.
    # Later downstream dispatch redistribution: TRAIN TP 618->641 (+23), TEST TP
    # 247->252 (+5), FP unchanged (2 train, 1 test). Floor unchanged at 0.92.
    "deflection": 0.92,  # train 0.997 / test 0.996 (650 TP, 2 FP; final measurement, post clearance suppression)
    # clearance: cook 9-condition AND-chain rewrite. TRAIN 0.913 (199 TP, 19 FP),
    # TEST 0.952 (99 TP, 5 FP). Floor set at 0.87 (~5pp below TRAIN 0.913).
    # Tagger precision pass: cook clearance condition 7 checked the opponent's FUTURE response
    # (moves[k+1]); cook uses the opponent's PRIOR move (moves[k-1]). FP 13->0, recall 0.39->0.44.
    #
    # Deliberate divergence from cook (see the module docstring): three additions to
    # cook's 9-condition chain. (1) The vacating (prior pov) move must not be a king or
    # pawn move (a dev hand review found 9 of 12 sampled clearance tags were king
    # retreats, pawn pushes, or piece shuffles — not real clearances). (2) The
    # clearing move must actually USE the newly-opened line (gives check, or
    # attacks a higher-value or hanging opponent piece) — cook has no such test.
    # (3) The scan caps at SACRIFICE_CLEARANCE_MAX_DEPTH=4 (shared with
    # sacrifice) — dev average firing depth for clearance was 3.73 vs
    # 0.00-1.35 for the geometric motifs. Recall falls by design (measured:
    # TRAIN TP 399->216 recall 0.457->0.247, TEST TP 159->90 recall 0.449->0.254);
    # precision must NOT fall and does not (1.000 -> 1.000 both splits, 0 FP
    # throughout). A future precision pass must NOT relax these three additions
    # to recover fixture recall; if a real-game measurement finds the cut too
    # soft, SACRIFICE_CLEARANCE_MAX_DEPTH is the lever, never a re-litigation of
    # the three additions.
    #
    # Outcome (2026-09-12): SUPPRESSED. The real-game keep bar (real_share >= 0.80)
    # was measured at real_share=0.667 with only 3 of 16 rows surviving (below
    # REALGAME_MIN_ROWS_FOR_FLOOR=8) — the SUPPRESS branch of the keep/
    # suppress decision. `clearance` is now in SUPPRESSED_MOTIFS, removed from
    # _TIER3_REGISTRY (tactic_detector.py) so no PV can dispatch it, and removed
    # from FAMILY_TO_MOTIF_INTS / tacticComparisonMeta.ts's Advanced group. This
    # CC0-fixture PRECISION_FLOOR entry (0.93, 216 TP TRAIN, 0 FP — still exactly
    # correct as a STANDALONE-predicate measurement) is commented out rather than
    # deleted for the historical record; it no longer gates anything because
    # `test_detector_precision_and_recall` only asserts floors for un-suppressed
    # motifs.
    # "clearance": 0.93,  # train 1.000 / test 1.000 (216 TP, 0 FP; depth-capped, strengthened predicate)
    # Tagger precision pass: lichess `interference` = cook self_interference OR interference; the
    # old port did a single non-ray-aware self_interference-shaped check. Now fires on either
    # faithful variant. FP 8->1, recall 0.43->0.59. P 0.967->0.997.
    "interference": 0.92,  # train 0.997 / test 1.000 (357 TP, 1 FP; cook either-variant fix)
    # capturing-defender: cook 9-condition AND-chain rewrite. Tagger precision
    # pass added cook's missing `not prev.board().is_check()` guard (boards[k-1]) + ray-aware
    # hanging test — this declines intermezzo lines (checking zwischenzug before recapture)
    # that were the entire FP source. P(train) 0.869 -> 1.000, P(test) -> 1.000, recall held.
    # Raised floor 0.82 -> 0.93 (~7pp below TRAIN) to lock in the gain.
    "capturing-defender": 0.93,  # train 1.000 / test 1.000 (377 TP, 0 FP; cook is-check guard fix)
    # intermezzo: cook zwischenzug AND-chain (moves[k-3] original-capture +
    # was-legal-earlier condition + opponent non-attacker gate). TRAIN 0.907 (39 TP, 4 FP),
    # TEST 1.000 (25 TP, 0 FP). Floor set at 0.85 (~6pp below TRAIN 0.907, rounded to 0.05).
    # Full-regen re-measure: the larger 2026-06 fixture surfaces more intermezzo
    # FPs. n(train) 702 -> 751, P(train) 0.938 -> 0.759 (TP=22, FP=7). Lowered 0.85 -> 0.70
    # (~6pp below new TRAIN; TEST 0.750 clears). Detector unchanged.
    # Tagger precision pass: reimplemented intermezzo to cook's exact control flow (early-exit
    # at the first qualifying pov capture) + the first-move (k=2) case using the flaw move from
    # boards[0].move_stack. P(train) 0.800 -> 1.000, P(test) -> 1.000, and recall 0.03 -> 0.61
    # (the k=2 first-move zwischenzugs were previously undetectable). Floor 0.70 -> 0.92.
    "intermezzo": 0.92,  # train 1.000 / test 1.000 (457 TP, 0 FP; cook control-flow + k=2 fix)
    # x-ray: cook three-same-square AND-chain (moves[k-2].to == moves[k-1].to
    # == moves[k].to, between-square geometry, non-king recapturer). TRAIN 1.000 (225 TP, 0 FP),
    # TEST 1.000 (103 TP, 0 FP). Floor set at 0.93 (~7pp below TRAIN 1.000, rounded to 0.01).
    "x-ray": 0.93,  # train 1.000 / test 1.000 (cook three-same-square AND-chain)
    # hanging-piece floor confirmed. Depth-primary dispatch changed
    # which motif wins when hanging-piece competes with geometrics, reducing train from
    # 0.990 to 0.909; floor stays at 0.90 (still 1pp above train, within 5-8pp band goal).
    # The original "0.95 puzzle precision" target refers to the test-set measure at the first baseline.
    # Full-regen re-measure: the larger 2026-06 fixture surfaces many more
    # hanging-piece FPs. n(train) 734 -> 857, P(train) 0.915 -> 0.743 (TP=625, FP=216).
    # Tagger precision pass: ported cook's hanging_piece gates (ray-aware is_hanging, check-gate,
    # king-exclusion, material-maintenance boards[3] >= boards[1]) AND cook's recapture exclusion
    # (values[op_capture] >= values[captured]), computed from the flaw move on boards[0].move_stack
    # — production already passes that board; the gate now builds it the same way (PreFlawFEN +
    # push). FPs 216 -> 0 with ZERO true-positive loss. P(train) 0.743 -> 1.000, P(test) -> 1.000.
    # Floor 0.68 -> 0.92.
    "hanging-piece": 0.92,  # train 1.000 / test 1.000 (631 TP, 0 FP; cook gates + recapture exclusion)
    # --- Tier 5 move-type (whole-line scan) ---
    # The three move-type detectors now scan EVERY pov move (cook's
    # promotion/under_promotion/en_passant `mainline[1::2]`), not just moves[0], and the
    # dispatcher gates Tier 5 behind `if not candidates` so move-type is a STRICT residual
    # fallback (any real tactic in tiers 1-4 always wins). Precision stays 1.000 / 0 FP on
    # both splits (move-type only wins on residual lines lichess also tags), and recall
    # jumps: promotion 0.05 -> 0.487 train / 0.481 test, en-passant 0.30 -> 0.622 / 0.626,
    # under-promotion 0.12 -> 0.324 / 0.349. Floors unchanged (all clear comfortably).
    "promotion": 0.60,  # train 1.000 / test 1.000 (1816 TP, 0 FP; whole-line residual scan)
    "en-passant": 0.93,  # train 1.000 / test 1.000 (1219 TP, 0 FP; whole-line residual scan)
    "under-promotion": 0.90,  # train 1.000 / test 1.000 (253 TP, 0 FP; whole-line residual scan)
    # --- Formerly suppressed motifs (measured 2026-06-23, cook ports) ---
    # All five measured at TRAIN 1.000 / 0 FP; floors set at 0.93 (~7pp below, rounded to 0.05).
    "attraction": 0.93,  # train 1.000 / test ~1.000 (654 TP, 0 FP; cook port)
    #
    # Deliberate divergence from cook (see the module docstring): cook's predicate fires
    # whenever pov is down >= MIN_SACRIFICE_DROP at ANY pov move from the 2nd
    # onward, with no recovery test and no depth limit — 32% of cook's own
    # sacrifice puzzles are delayed recaptures / zwischenzugs. A persistence rule
    # (the deficit must still hold after the NEXT pov move (boards[k+3]), or the
    # line must end first) was tried and RETIRED, see below. The depth cap stays:
    # the scan is capped at SACRIFICE_CLEARANCE_MAX_DEPTH=4 (shared with clearance;
    # dev average firing depth 4.78 vs 0.00-1.35 for the geometric motifs). With the
    # persistence rule recall fell (measured: TRAIN TP 397->177 recall 0.111->0.050,
    # TEST TP 183->70 recall 0.118->0.045) at unchanged precision (1.000, 0 FP).
    #
    # Why the persistence rule was retired (2026-09-13): an operator spot-check of
    # the hand-labelled real-game rows (fixtures/tagger/realgame_tags.csv 0064, 0133)
    # found two rows it wrongly dropped ARE genuine sacrifices — their material
    # recovers at boards[k+3] because the sacrifice worked (Nxd6, gxf8=Q+ are the
    # tactic's own follow-ups), which is exactly the shape the literal persistence
    # check cannot distinguish from a delayed recapture. Three board-derivable
    # candidate discriminators were measured against the corrected label set and
    # NONE separates the two populations: "recovery overshoots the entry baseline"
    # also fires on row 0134 (confirmed NOT a real sacrifice — relabelled
    # real->wrong); "deficit depth" does not separate them (0134 reaches the same
    # -3 minimum as genuine row 0064); "the opponent chose to accept" matches
    # 0064's shape but not 0133's (both of pov's early moves there are captures,
    # not a quiet offer). A rule known to fail a confirmed-real row must not ship —
    # `detect_sacrifice` was reverted to cook's unguarded predicate (the depth cap
    # is orthogonal to the persistence rule and was never implicated). The
    # per-tier winning floor (already shipped) independently covers the case the
    # persistence rule was built for: of the 7 real-game rows it removed beyond
    # cook's own predicate, the winning floor alone would have kept exactly the 3
    # genuine/plausible sacrifices and rejected the other 4 (three deep-losing
    # lines plus row 0134). Never re-introduce a persistence check on
    # `detect_sacrifice` without new eval access or a materially larger labelled
    # sample — the rule was not a bad idea, but no board-derivable version of it
    # survived the operator's evidence.
    # Measured effect of the revert: TRAIN TP 208->456 (recall 0.128, up from
    # 0.050), TEST TP 77->196 (recall 0.127, up from 0.045); FP unchanged at 0
    # both splits, precision unchanged at 1.000 both splits. A handful of other
    # motifs lost a small number of TRAIN/TEST TPs to sacrifice's newly-widened
    # dispatch wins (pure redistribution) — no other motif's FP count changed and
    # every floor still clears with headroom (see the final-consolidation table in
    # the module docstring; unchanged by the revert except sacrifice's own row).
    "sacrifice": 0.93,  # train 1.000 / test 1.000 (456 TP, 0 FP; persistence rule retired)
    "arabian-mate": 0.93,  # train 1.000 / test ~1.000 (553 TP, 0 FP; cook port)
    # Corrected the file-relation test to cook's
    # actual asymmetric formula ((bishop_squares[0] left-of-king-file) ==
    # (bishop_squares[1] right-of-king-file), not a symmetric opposite-sides XOR).
    # TRAIN TP 441->442 (+1; the one row where the SECOND bishop by square-index
    # order sits on the king's file). double-bishop-mate stays SUPPRESSED (unchanged
    # by this fix; see the module-docstring oracle finding for the much larger,
    # separately-tracked firing gap on both motifs). Floor unchanged.
    "boden-mate": 0.93,  # train 1.000 / test ~1.000 (442 TP, 0 FP; file-test fix)
    "dovetail-mate": 0.93,  # train 1.000 / test ~1.000 (543 TP, 0 FP; cook port)
    # --- Formerly suppressed motif (measured 2026-06-23, cook captured-chain port) ---
    # trapped-piece: cook capture-chain-anchored is_trapped predicate. TRAIN 1.000 (565 TP, 0 FP),
    # TEST 1.000 (239 TP, 0 FP). deltaP=0.000. Floor set at 0.92 (~8pp below TRAIN 1.000).
    # Later downstream dispatch redistribution: TRAIN TP 565->634 (+69), TEST TP
    # 239->276 (+37), FP unchanged (0 both) (the empty-escape revert,
    # sacrifice/clearance depth cap, discovered-attack depth=k). Floor
    # unchanged at 0.92.
    "trapped-piece": 0.92,  # train 1.000 / test 1.000 (657 TP, 0 FP; final measurement, post clearance suppression)
}

# ---------------------------------------------------------------------------
# Real-game never-regress floors — orthogonal to
# PRECISION_FLOOR above (see the module docstring's "Real-game floors are a
# SEPARATE, orthogonal measurement" paragraph). Scored against the hand-labelled
# fixtures/tagger/realgame_tags.csv sample via
# tests/scripts/tagger/test_detector_precision.py::_compute_realgame_metrics.
# ---------------------------------------------------------------------------

# A motif needs at least this many SURVIVING real-game rows (both orientations
# combined) before its real_share is gated — below this the denominator is too
# thin for the measurement to mean anything (a single mislabel would swing the
# share by >10pp). Matches PER_STRATUM_OVERSAMPLED in
# scripts/research/sample_realgame_tags.py: the four oversampled motifs each
# clear this bar with rows to spare (16 surviving), every other motif (4
# surviving, the thin control rate) does not and is reported but not gated.
REALGAME_MIN_ROWS_FOR_FLOOR: int = 8

# Post-fix finalisation (2026-09-12). All floors below are
# re-seeded from the measurement AFTER every detector/gate change
# landed, against the SAME frozen 164-row fixtures/tagger/
# realgame_tags.csv sampled before any of those changes — see
# tests/scripts/tagger/test_detector_precision.py::test_realgame_real_share_floor
# for the reproducible measurement. This SUPERSEDES the pre-fix baseline
# (sacrifice 0.32, clearance 0.38, intermezzo 0.70, x-ray 0.82). Each
# value is seeded ~0.05 below the measured post-fix real_share, clamped to
# [0.0, 1.0], rounded DOWN to stay conservative. Only motifs whose surviving
# count clears REALGAME_MIN_ROWS_FOR_FLOOR get an entry — every other tagged
# motif in the CSV is reported in the table but never gated.
REALGAME_REAL_SHARE_FLOOR: dict[str, float] = {
    # sacrifice: floor re-seeded 2026-09-13 after the persistence rule was retired
    # (see the sacrifice block in PRECISION_FLOOR). With the persistence rule in
    # place the measured real_share DROPPED to 0.222 (2/9 surviving were `real`; 7 of
    # the original 16 rows were suppressed by the winning floor plus the persistence
    # rule), BELOW the pre-fix floor (0.32, itself derived from the pre-fix 0.375
    # measurement). Several rows a human labelled `real` are attacking sacrifices
    # that fully repay via a DIFFERENT tactical point 1-2 plies later (row 0064: a
    # knight sac at k=2 objectively winning at +264cp, material fully recovers via an
    # unrelated bishop capture at k=4) — exactly the "delayed compensation" shape the
    # persistence rule was designed to exclude. The operator spot-check then showed
    # rows 0064 and 0133 are genuine sacrifices the rule wrongly dropped, and row 0134
    # was mislabelled `real` (White never offers material) and is corrected to
    # `wrong`. With the persistence rule retired, re-scored on the SAME frozen 164-row
    # fixture: surviving 9->13, real_surviving 2->5, real_share 0.222->0.385. This
    # CLEARS not only the pre-fix floor (0.32) but the pre-fix MEASUREMENT itself
    # (0.375). Floor re-seeded ~0.05 below the new measurement (0.385 - 0.05 = 0.335,
    # rounded down to 0.33), same convention as every other entry in this dict. Never
    # patched around a code defect — the code is now believed CORRECT (cook's
    # unguarded predicate + the independent winning floor), and this is a genuine
    # re-measurement, not a regression tolerance widening.
    "sacrifice": 0.33,  # post-revert: surviving 13, real_surviving 5, real_share 0.385
    # intermezzo: measured real_share 0.750 (12/16 real) — UNCHANGED from the pre-fix
    # baseline. The missed-orientation move stack was expected to be the main lever
    # here, but tests/scripts/tagger/conftest.py::build_realgame_board already pushes
    # a move on both orientations (simulating the production board build), so this
    # fixture's intermezzo score was never subject to the old stackless bug measured
    # separately against dev. Floor unchanged at 0.70 (re-confirmed post-fix).
    "intermezzo": 0.70,  # post-fix: surviving 16, real_surviving 12, real_share 0.750
    # x-ray: measured real_share 0.875 (14/16 real) — UNCHANGED from the pre-fix
    # baseline. x-ray's strict AND-chain (three-same-square + between-square geometry)
    # was already precision-clean; the winning floor and the depth cap (x-ray is not
    # sacrifice/clearance, so the cap does not apply to it) neither raised nor lowered
    # this motif's real-game behaviour. Floor unchanged at 0.82 (re-confirmed
    # post-fix).
    "x-ray": 0.82,  # post-fix: surviving 16, real_surviving 14, real_share 0.875
    # `clearance` had a floor here in the pre-fix baseline (0.38, 7/16 real =
    # 0.4375). POST-FIX: only 3 of 16 rows survive the strengthened predicate (13
    # correctly suppressed), below REALGAME_MIN_ROWS_FOR_FLOOR=8 — the denominator is
    # too thin to trust regardless of its real_share (which, among the 3 survivors,
    # is 0.667: 2 real). A surviving count below the minimum takes the SUPPRESS
    # branch outright (a handful of rows is not a passing measurement): `clearance`
    # has its PRECISION_FLOOR entry commented out and is in SUPPRESSED_MOTIFS. No
    # REALGAME_REAL_SHARE_FLOOR entry for `clearance` — a suppressed, undispatchable
    # motif (int 15 remains encodable/decodable/storable for the existing rows the
    # prod retag will clear).
    # "clearance": 0.38,  # SUPPRESSED 2026-09-12: real_share 0.667 among
    #                       3 surviving rows (< REALGAME_MIN_ROWS_FOR_FLOOR=8) —
    #                       both branch conditions miss; see PRECISION_FLOOR's
    #                       clearance entry and SUPPRESSED_MOTIFS above for the
    #                       full keep/suppress decision record.
}
