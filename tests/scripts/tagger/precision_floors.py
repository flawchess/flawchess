"""Per-motif precision floor constants for the tagger validation harness.

Floors are set from the MEASURED numbers produced by the harness against the TRAIN
fixture. They are downstream of measurement per D-09 — never hardcoded before the
harness runs — and are asserted on TRAIN only (the held-out TEST set is never used
to set floors; see test_detector_precision.py).

Measurement run summary (2026-06-19, 11,855-row TRAIN CC0 fixture — re-sampled at
200/stratum and split 70/30 train/test to reduce overfitting risk; post-D-01
relevance gate applied). TEST precision shown for reference (held out, not gated):

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
  pin                   336   428   867    0.440   0.279   0.439  (SEED-057 gate fix)
  sacrifice               0     0  3142    NaN     0.000   NaN    (never fires)
  skewer                149   770   523    0.162   0.222   0.154
  smothered-mate        468     0     0    1.000   1.000   1.000
  x-ray                   0    10   642    0.000   0.000   0.000  (only-FP)

Train and held-out test precision track closely for every shipped motif (max gap a
few pp), so the post-127 detector generalizes rather than overfitting the fixture.

Phase 128.1-02 measurement run (2026-06-20, same 11,855-row TRAIN fixture with all 29
motifs present). New motifs from Plans 01 and 02:

  Motif                  TP    FP    FN   P(train) Recall  P(test)  Floor posture
  -----------------------------------------------------------------------------------------
  discovered-check       44     6   960    0.880   0.044   0.833    Normal % floor (1004 TRAIN labels)
  trapped-piece           0     9    28    0.000   0.000   0.000    Only-FP → SUPPRESSED (D-08)
  en-passant              0     0    12    NaN     0.000   NaN      Never fires → SUPPRESSED (D-08)
  promotion               1     0   179    1.000   0.006   NaN      Thin (1 TP); % floor at 0.60
  under-promotion         0     0     4    NaN     0.000   NaN      n=4; never fires → SUPPRESSED (D-08 approach i)

Phase 131-02 measurement run (2026-06-22, same 11,855-row TRAIN fixture). Cook-aligned
ports for fork, skewer, discovered-attack, pin; TEST is the 5,164-row held-out split:

  Motif                  TP    FP    FN   P(train) P(test)  Decision
  -----------------------------------------------------------------------------------------
  fork                  993     1   564    1.000   0.998    SHIPPED — exceeds 0.90 TEST
  skewer                432     0   240    1.000   1.000    SHIPPED — exceeds 0.90 TEST
  discovered-attack     321     2   136    0.995   1.000    SHIPPED — exceeds 0.90 TEST
  pin (131-02)          453   149   750    0.752   0.819    was SUPPRESSED — below 0.90 TEST
  pin (131 fix)         699    49   504    0.934   0.944    SHIPPED — odd-board scan (see below)

Phase 132-02 measurement run (2026-06-23, same 11,855-row TRAIN / 5,164-row TEST fixture).
Cook-aligned AND-chain rewrites for deflection (11 conditions) and clearance (9 conditions),
replacing graded `_grade(met, total)` voting with exact relational AND-chains:

  Motif                  TP    FP    FN   P(train) P(test)  Decision
  -----------------------------------------------------------------------------------------
  deflection            162     1  1015    0.994   1.000    SHIPPED — exceeds 0.90 TEST
  clearance             199    19   526    0.913   0.952    SHIPPED — exceeds 0.90 TEST

Phase 132-03 measurement run (2026-06-23, same 11,855-row TRAIN / 5,164-row TEST fixture).
Cook-aligned AND-chain rewrites for capturing-defender (9 conditions, init-board defender
test) and intermezzo (zwischenzug signature: moves[k-3] original-capture + was-legal-earlier),
both replacing graded voting with exact relational AND-chains:

  Motif                  TP    FP    FN   P(train) P(test)  Decision
  -----------------------------------------------------------------------------------------
  capturing-defender    326    49   284    0.869   0.903    SHIPPED — exceeds 0.90 TEST
  intermezzo             39     4   663    0.907   1.000    SHIPPED — exceeds 0.90 TEST

Phase 132-04 measurement run (2026-06-23, same 11,855-row TRAIN / 5,164-row TEST fixture).
Cook AND-chain ports for attraction (§4 lure+capture+attack+follow-up), x-ray (§6 three-
same-square guard + between-square geometry), and sacrifice (§7 material-diff predicate):

  Motif                  TP    FP    FN   P(train) P(test)  Decision
  -----------------------------------------------------------------------------------------
  attraction              0     0  1603    NaN     NaN      SUPPRESSED — D-03 cutoff: 0 TP on TRAIN
                                                             after Phase 132 cook port. An off-by-one
                                                             in cond-5 (attacker board was boards[k+2],
                                                             should be boards[k+3]) produced 0 TP.
                                                             Fixed in Phase 133; see Phase 133 block.
  x-ray                 225     0   417    1.000   1.000    SHIPPED — exceeds 0.90 TEST. Cook three-
                                                             same-square AND-chain (moves[k-2].to ==
                                                             moves[k-1].to == moves[k].to + between-
                                                             square geometry + non-king recapturer).
                                                             Floor set at 0.93 (~7pp below TRAIN 1.000).
  sacrifice               0     0  3142    NaN     NaN      SUPPRESSED — 0 TP in Phase 132 because
                                                             the detector is standalone-precision 1.000
                                                             but its recall is limited by dispatch order:
                                                             higher-priority mates, fork, and pin
                                                             shadow it in ~92% of positions. Fixed in
                                                             Phase 133 via unsuppress-only (no co-tag
                                                             needed); see Phase 133 block.
  interference          269     3   327    0.989   0.992    NO REGRESSION from interference logic
  (post-attraction)                                          (detect_interference UNCHANGED). Prior
  (post-sacrifice)                                           measurement (0.985 TRAIN / 0.986 TEST)
                                                             was mid-port, before sacrifice fixture
                                                             collision fixes. Final measurement after
                                                             all cook ports: 0.989 TRAIN / 0.992 TEST.
                                                             Floor 0.80 still holds with large headroom.

Phase 133 measurement run (2026-06-23, same 11,855-row TRAIN / 5,164-row TEST fixture).
Detector fixes for attraction (boards[k+3] off-by-one), arabian-mate (cook attacker-of-
rook-sq knight geometry), boden-mate (cook near-king bishop-only attacker loop), and
dovetail-mate (cook diagonal-adjacency + escape-square loop, both bugs A and B). Sacrifice
is unsuppress-only (standalone precision already 1.000; unsuppressed without code change):

  Motif                  TP    FP    FN   P(train) P(test)  Decision
  -----------------------------------------------------------------------------------------
  attraction            654     0   949    1.000   ~1.000   SHIPPED — off-by-one fixed (phase 133-01).
                                                             Floor set at 0.93 (~7pp below TRAIN 1.000).
  arabian-mate          553     0     0    1.000   ~1.000   SHIPPED — cook attacker-of-rook-sq + (2,2)
                                                             knight geometry (phase 133-01).
                                                             Floor set at 0.93 (~7pp below TRAIN 1.000).
  boden-mate            435     0     2    1.000   ~1.000   SHIPPED — cook near-king bishop-only
                                                             attacker loop (phase 133-01).
                                                             Floor set at 0.93 (~7pp below TRAIN 1.000).
  dovetail-mate         543     0     1    1.000   ~1.000   SHIPPED — cook diagonal-adjacency + escape-
                                                             square loop (phase 133-01).
                                                             Floor set at 0.93 (~7pp below TRAIN 1.000).
  sacrifice             236     0  2906    1.000   ~1.000   SHIPPED — unsuppress-only (phase 133-02).
                                                             Standalone precision 1.000 / recall 0.075
                                                             post-dispatch (shadowed by higher-priority
                                                             mates/fork/pin in ~92% of positions).
                                                             Floor set at 0.93 (~7pp below TRAIN 1.000).

Measurement notes:
  - discovered-check (1004 TRAIN labels, 397 TEST): fires at P=0.880 train / 0.833 test.
    Recall is ~4.4% — the motif shadows only non-mating discovered-check lines (the other
    960 FN are positions tagged discoveredCheck that also contain mate, fork, or skewer at a
    higher-priority tier). Floor set at 0.80 (~8pp below measured).
  - trapped-piece (Phase 134 fixture expansion — ~1065 combined: 748 TRAIN / 317 TEST):
    the fixture was expanded from the thin 28/11 baseline via the per-motif --oversample-motifs
    cap (trapped-piece:250/stratum) against the fresh 2026-06 lichess dump (D-EXP-02 Option B,
    full-regen variant — see Phase 134 SUMMARY). The cook capture-chain-anchored is_trapped
    predicate (Phase 134 Plan 02) achieved P(train)=1.000 (565 TP, 0 FP) / P(test)=1.000
    (239 TP, 0 FP), deltaP=0.000 — clearing the D-EXP-03 ≥0.80 bar on both sets. Shipped
    phase 134: removed from SUPPRESSED_MOTIFS, PRECISION_FLOOR added below.
  - en-passant (Quick 260623, Phase-134 expanded fixture — 1960 TRAIN / 845 TEST labels):
    P(train)=P(test)=1.000 (~590 TP, 0 FP), R≈0.30. The old Phase-128.1-02 note ("NaN, 12
    labels, never fires") described the thin pre-expansion fixture; the larger fixture leaves
    enough residual rows where no higher-priority tactic wins the Tier-5 dispatch for the
    detector to fire cleanly. Unsuppressed and shipped as an "Advanced" chip family. Floor
    0.93. Still structurally validated by the _EN_PASSANT_FIXTURES fast-guard set.
  - promotion (176 TRAIN labels including underPromotion, 57 TEST): fires once (TP=1, FP=0,
    P=1.000 train). Like en-passant, most promotion rows have a higher-priority tactic.
    1 TP is very thin but the precision is 100% — floor set conservatively at 0.60 to allow
    for variance while still catching zero-precision regressions.
  - under-promotion (Quick 260623, Phase-134 expanded fixture — 780 TRAIN / 332 TEST labels):
    P(train)=P(test)=1.000 (~91 TP, 0 FP), R≈0.12. The old Phase-128.1-02 note ("NaN, n=4,
    Tier-1 mate pre-empts every case") described the thin pre-expansion fixture. On the larger
    fixture it fires cleanly on the residual; thinner TP pool than en-passant, so the floor is
    0.90 (slightly more conservative). Unsuppressed and shipped as an "Advanced" chip family.
    Still structurally validated by the _UNDER_PROMOTION_FIXTURES fast-guard set, whose
    `test_positives_fire_expected_motif[under-promotion]` is the never-regress assertion.
  - pin (Phase 131-02 -> Phase 131 fix): the full cook two-sub-test port lifted TEST
    precision from 0.474 to 0.819 but stayed below the 0.90 ship bar, so 131-02 suppressed it.
    The Phase 131 follow-up fix found the remaining gap was a node-set bug: detect_pin scanned
    EVERY board in the PV, whereas cook checks pins only on the boards that follow a POV
    (winning-side) move. boards[0] is pov-to-move, so pov's moves land on the ODD indices
    (boards[1], boards[3], ...). Scanning only those (`range(1, len(boards), 2)`) removes the
    incidental / pre-existing pins that fired on pov-to-move boards inside opponent forcing
    lines (attraction, deflection, sacrifice). Isolated precision 0.477 -> 0.947; post-dispatch
    0.752 -> 0.934 TRAIN / 0.819 -> 0.944 TEST, recall held (~0.60). Pin is now SHIPPED with a
    0.90 floor. FAMILY_TO_MOTIF_INTS already carries it (G-01 10-family contract).

Precision floors are set at ~5-8pp below the measured TRAIN value (rounded to 0.05)
to give a stable CI gate that fails on genuine regressions, not normal variance.
Motifs with NaN precision (never fire) or only-FP (0 TP, >0 FP) are in SUPPRESSED_MOTIFS.

Suppression notes:
  Tier-3 motifs in SUPPRESSED_MOTIFS are filtered at query time via the
  _TACTIC_CHIP_CONFIDENCE_MIN lever in library_repository.py (currently 70).
  Tier-1/2/5 motifs (confidence always 100) cannot be suppressed via this lever —
  their detectors fire rarely enough that they do not materially affect the UI in
  practice, but their floors are omitted from PRECISION_FLOOR (no gate for motifs
  that do not reliably fire).

Real-game floors are a SEPARATE, orthogonal measurement (Phase 221, TAGFIX-07 /
D-13):
  PRECISION_FLOOR above scores the detector against cook.py's lichess-puzzler
  labels on CC0 puzzles — capped, forcing, curated lines. REALGAME_REAL_SHARE_FLOOR
  below scores the SAME detector against a hand-labelled sample of ~150 real
  `game_flaws` tags — 12-ply-capped, non-forcing, sometimes-losing engine PVs from
  actual user games. A motif can legitimately have high puzzle precision AND low
  real-game real-share at the same time: this is not a contradiction, it is the
  entire finding SEED-165 rests on (the puzzle fixture is structurally blind to
  losing lines, capped PVs and non-forcing tails — see the review report
  `reports/tactic-tagger/tactic-tagger-review-2026-09-12.md` §3). Never conflate
  the two floor dicts, and never "fix" a real-game floor regression by relaxing
  PRECISION_FLOOR (or vice versa) — they measure different populations.

`discoveredCheck` labels are NOT cook output (TAGFIX-08). cook's `TagKind` (this
  local AGPL clone) has no `discoveredCheck` theme at all — of the 2,854 TRAIN+TEST
  fixture rows carrying the lichess `discoveredCheck` label, only 1,585 (56%)
  satisfy `cook.discovered_check` when recomputed via `scripts/research/
  oracle_compare.py` (measured 2026-09-12; see the review report §3). Our
  `discovered-check`'s measured PRECISION_FLOOR is therefore scored against a
  lichess theme whose provenance is NOT cook — most likely lila-side or crowd
  voting. Re-scoring `discovered-check` against a different, cook-derived label
  source is explicitly OUT OF SCOPE for this phase (documented only, per the
  CONTEXT.md `## Deferred Ideas` list); do not attempt it as a drive-by fix.

An oracle comparison exists at `scripts/research/oracle_compare.py` (TAGFIX-08).
  It replays every committed fixture row through both our standalone detector
  functions and cook.py itself (the local AGPL lichess-puzzler clone, imported
  by path at runtime only — see its own module docstring for the boundary), and
  prints a three-way agreement table (`both` / `cookOnly` / `oursOnly` / `neither`)
  per motif. "Matches cook" means: for every fixture row, our detector's fire/
  no-fire verdict for that motif equals cook's recomputed verdict for the
  corresponding cook function (see the mapping inside `oracle_compare.py::ours` /
  `::cooks`). Two prior "precision-first" deviations from cook were disproved by
  this comparison and must not be reintroduced by a future precision pass:
    1. Fork's D-01 "relevance gate" (`material_at_end < material_at_start ->
       skip`) — NOT in cook. Removing it cost 130 detections for ZERO measured
       precision change (all 130 were sac-then-mate lines cook itself tags).
    2. Trapped-piece's empty-escape exclusion (`if not escape_moves: return
       False`) — NOT in cook (cook: an immobile attacked non-pawn/non-king piece
       IS trapped). Reverting it cost 107 detections for ZERO new false
       positives.
  D-05's sacrifice persistence rule (RETIRED in plan 08 — see below) and D-07's
  clearance strengthening ARE deliberate divergences from cook (unlike the two
  disproved deviations above) — a fixture recall drop on those two motifs
  specifically is EXPECTED BY DESIGN. Relaxing D-07 to recover fixture recall
  is the failure mode this phase exists to prevent; a third "precision-first"
  deviation from cook has to argue against a recorded measurement, not
  intuition. See the block comment directly above the `sacrifice` and
  `clearance` PRECISION_FLOOR entries below for the full divergence record
  (Phase 221 TAGFIX-03/04), INCLUDING plan 08's amendment retiring D-05.

Phase 221 TAGFIX-03/TAGFIX-04 deliberate divergences from cook (2026-09-12,
plan 05) — see the block comment above the `sacrifice` and `clearance` entries
in PRECISION_FLOOR for the full record. In short: `sacrifice` gained a
persistence rule (D-05) and a shared depth cap (D-06); `clearance` gained a
vacating-piece restriction, a "line is used" clause (D-07), and the same depth
cap (D-06). Both are DELIBERATE, never-relax divergences from cook — recall
falling on the CC0 fixture is expected by design, precision must not fall (it
did not: both stay at 1.000 TRAIN/TEST). `sacrifice` and `clearance` are ALSO
scored against hand-labelled real-game rows via REALGAME_REAL_SHARE_FLOOR
(a separate, orthogonal measurement — see that section's own docstring); the
two floor dicts can legitimately disagree, and the real-game number is the one
this phase optimises. Never relax D-07 to recover either measurement — the
depth cap (`SACRIFICE_CLEARANCE_MAX_DEPTH`) is the only sanctioned lever if a
future measurement finds clearance's cut too soft (clearance is currently
SUPPRESSED regardless — see SUPPRESSED_MOTIFS).

Phase 221 plan 08 (2026-09-13, gap closure — AMENDS the paragraph above): the
221-D13-SPOTCHECK.md operator review overturned the assumption D-05 rested on
— two of the four rows it measured as "correctly dropped" are genuine
sacrifices D-05's literal persistence rule cannot distinguish from a delayed
recapture. No board-derivable replacement discriminator survived the
evidence (task 1's measurement — three candidates tried, all fail on at least
one confirmed-real or confirmed-wrong row). `detect_sacrifice` is reverted to
cook's unguarded predicate; D-06's depth cap is UNCHANGED (it was never
implicated). D-05 is retired, not "was always wrong" — it was a reasonable,
measured hypothesis that a later, larger piece of evidence (the operator's
hand review) disproved. See the block comment above the `sacrifice`
PRECISION_FLOOR entry and the `sacrifice` REALGAME_REAL_SHARE_FLOOR entry for
the full measurement.

Phase 221 plan 06 (2026-09-12) — final consolidated PRECISION_FLOOR measurement
across the whole phase (TRAIN 18,632 rows / TEST 8,017 rows, same CC0 fixture
every plan above scored against), taken AFTER task 2's clearance suppression
(the last detector/registry change in the phase) so these are the true final
numbers. TP counts moved purely from downstream dispatch redistribution as
plans 02/04/05 landed and, in this table, from clearance's own removal freeing
its former dispatch wins to other motifs (sacrifice/clearance's depth cap and
persistence rule, D-11's discovered-attack depth=k, the D-01 winning floor, and
finally clearance's registry removal). No PRECISION_FLOOR value was lowered
anywhere in the phase — every floor below still holds with the same or larger
headroom than when it was last set, so none needed raising in this plan either
(the one exception, discovered-attack, was already raised 0.93->0.95 in plan
02 to lock in its own zero-FP gain). `clearance` is SUPPRESSED (TP=0 by
design -- the motif can never win dispatch again; see SUPPRESSED_MOTIFS above):

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

Phase 221 plan 08 (2026-09-13, gap closure) — SUPERSEDES the table above:
sacrifice's D-05 persistence check was retired (see the divergence block
above the `sacrifice` PRECISION_FLOOR entry), so its TP count rose sharply
(more candidates now fire) and a handful of other motifs lost a small number
of TPs to sacrifice's newly-widened dispatch wins — pure redistribution, same
pattern as every prior plan in this phase. No FP count changed anywhere; no
floor breached; only sacrifice's own floor changes (0.93 unchanged in value,
now backed by 456/196 TP instead of 208/77):

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
# Motifs suppressed from the precision floor gate (SC#5 / D-09)
# ---------------------------------------------------------------------------

# Motifs excluded from the assert-precision->= floor gate:
#   - "never fires": NaN precision, 0 TP and 0 FP in the TRAIN measurement run.
#   - "only-FP": 0 TP, >0 FP — zero precision; the detector misfires but never lands a
#     true positive. Named mates here are confidence=100 (cannot suppress via the lever);
#     tier-3 here are suppressed at query time by _TACTIC_CHIP_CONFIDENCE_MIN.
SUPPRESSED_MOTIFS: frozenset[str] = frozenset(
    {
        # Unvalidated motifs (no lichess theme equivalent) — excluded from measurement.
        # Phase 221 (2026-09-12, TAGFIX-05 fix 7 / D-12): self-interference stays in this
        # suppressed set AND is now ALSO undispatchable — the ("self-interference",
        # SELF_INTERFERENCE) tuple was removed from _TIER3_REGISTRY (tactic_detector.py),
        # so no PV can ever produce int 14 through the dispatcher again. The int, the
        # reverse-map entry and detect_self_interference are all retained for existing
        # persisted rows and direct unit calls; the full prod retag (TAGFIX-09) clears
        # every persisted int-14 row. Dev has zero such rows, so only the prod acceptance
        # query can verify that leg — this fixture harness cannot.
        "self-interference",
        "double-bishop-mate",
        # Phase 221 (2026-09-12, TAGFIX-04 / D-07, plan 06): clearance is SUPPRESSED.
        # D-07's bar ("keep only if real-game real_share >= 0.80 AND surviving >=
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
        # unit calls; the full prod retag (TAGFIX-09) clears every persisted int-15 row.
        "clearance",
        # Phase 134 (2026-06-23): trapped-piece is NO LONGER suppressed — cook capture-chain-
        # anchored predicate achieved P(train)=1.000 / P(test)=1.000 (565 TP, 0 FP) on the
        # ~1065-row expanded fixture. Floor added below; FAMILY_TO_MOTIF_INTS + frontend chips
        # were already wired in Phase 129 (G-01 10-family contract).
        # Quick 260623: en-passant and under-promotion are NO LONGER suppressed. On the
        # Phase-134 expanded fixture they fire reliably at P(train)=P(test)=1.000 (the old
        # Phase-128.1-02 "never fires / NaN" rationale described the thin 12/4-label fixture).
        # Floors added below; FAMILY_TO_MOTIF_INTS + frontend "Advanced" chips wired in the
        # same change. promotion (28) stays shipped-but-unmapped with its own floor below.
        # Phase 131 pin precision fix (measured 2026-06-22): pin is NO LONGER suppressed.
        # Restricting detect_pin to POV-move result boards (odd PV indices, the cook node set)
        # lifted it from 0.819 to 0.944 TEST / 0.934 TRAIN — clears the 0.90 ship bar. Floor
        # added below; FAMILY_TO_MOTIF_INTS already carries pin (G-01 10-family contract).
        # Phase 133 (measured 2026-06-23): attraction, sacrifice, arabian-mate, boden-mate,
        # and dovetail-mate are NO LONGER suppressed — see Phase 133 measurement block above.
        # Floors added below; FAMILY_TO_MOTIF_INTS + frontend chips added in plan 133-02.
    }
)

# ---------------------------------------------------------------------------
# Per-motif precision floors — set from measured TRAIN numbers (D-09)
# ---------------------------------------------------------------------------

# Floors sit ~5-8pp below the measured TRAIN precision so the CI gate fails on genuine
# regressions without being brittle to fixture variance. These are the never-regress
# floors; aspirational improvement targets live in GOALS in scripts/tactic_tagger_report.py.
#
# NOTE: pre-Phase-132 low floors (back-rank-mate 0.281, fork 0.437, pin 0.440, skewer 0.162,
# discovered-attack 0.163, deflection 0.130) were raised by cook-aligned AND-chain rewrites in
# Phase 131 and 132. back-rank over-fires onto corner mates; the geometric detectors carry
# large FP pools. pin's SEED-057 gate fix lifted it 0.413 -> 0.440; Phase 131-02 cook port
# raised it further to 0.934 TRAIN. Phase 132-02 raised deflection 0.130 -> 0.994 TRAIN and
# clearance 0.348 -> 0.913 TRAIN.
#
# discovered-attack dropped from 0.193 to 0.163 because Phase 128.1-01 discovered-check
# (Tier 2, rank 4) now correctly intercepts discovered-attack Sub-case 1 positions — those
# are tagged discovered-check, not discovered-attack, which is correct by D-03. The existing
# floor 0.15 still passes (0.163 > 0.15).

PRECISION_FLOOR: dict[str, float] = {
    # --- Tier 2 geometric material-winners (confidence=100) ---
    # Phase 131-02 (cook-aligned ports, measured 2026-06-22):
    # fork, skewer, discovered-attack: floors raised to ~5-7pp below measured TRAIN.
    # pin: moved to SUPPRESSED_MOTIFS (below 0.90 TEST bar at full cook fidelity — D-02/D-11).
    # Phase 221 TAGFIX-05 fix 2 (D-12): removed the D-01 relevance gate (not in cook;
    # oracle comparison measured it costing 130 detections for zero precision). TRAIN
    # TP 1168->1184 (+16), FP unchanged (3), P 0.997 (unchanged, 3dp); TEST TP 509->514
    # (+5), FP 0. Floor held at 0.93 (still ~6pp below TRAIN).
    # Phase 221 plan 06 final consolidation: TRAIN TP 1184->1202 (+18), TEST TP
    # 514->516 (+2), FP unchanged (3 train, 0 test) — further downstream
    # dispatch redistribution from plans 04/05 (winning floor, sacrifice/
    # clearance depth cap). Floor unchanged at 0.93.
    "fork": 0.93,  # train 0.998 / test 1.000 (1203 TP, 3 FP; phase 221 final measurement, post clearance suppression)
    "skewer": 0.93,  # train 1.000 / test 1.000 (432 TP, 0 FP; phase 131-02 cook port)
    # Phase 221 TAGFIX-05 fixes 4-5 (D-11/D-12): the recapture guard now RETURNS
    # (short-circuits the whole predicate) instead of CONTINUE-ing past it, and the
    # returned depth is the pov move index k (not the prior port's max(0, k-1)).
    # TRAIN FP 5->0 (P 0.990->1.000), TP 489->456 (the removed FPs and a handful of
    # now-correctly-excluded recapture lines); TEST FP 4->0 (P 0.982->1.000), TP
    # 216->208. Floor RAISED 0.93->0.95 (~5pp below the new 1.000 TRAIN, matching
    # the file's house convention) to lock in the zero-FP gain.
    # Phase 221 plan 06 final consolidation: TRAIN TP 456->465 (+9), TEST TP
    # 208->211 (+3), FP unchanged (0 both) — further downstream dispatch
    # redistribution from plans 04/05. Floor unchanged at 0.95.
    "discovered-attack": 0.95,  # train 1.000 / test 1.000 (475 TP, 0 FP; phase 221 final measurement, post clearance suppression)
    # Phase 131 pin fix (measured 2026-06-22): scan only POV-move result boards (odd PV
    # indices = cook's node set) instead of every board. 0.819 -> 0.944 test / 0.752 -> 0.934
    # train, recall held (~0.60). Floor at the 0.90 ship bar (TRAIN 0.934 clears it).
    # Phase 134 (full-regen re-measure): the larger 2026-06 fixture surfaces more pin FPs.
    # n(train) 1203 -> 1499, P(train) 0.936 -> 0.899 (TP=936, FP=105). Lowered 0.90 -> 0.85
    # (~5pp below new TRAIN; TEST 0.916 clears). Detector unchanged (Plan 02 owns geometry).
    # Tagger precision pass (cook _pin_prevents_escape faithful fix): added cook's missing
    # guard (pinned piece not itself attacking the attacker) + pseudo-legal escape test.
    # Cut incidental-pin FPs 105 -> 2; P(train) 0.899 -> 0.998, P(test) -> 1.000, recall held.
    # Raised floor 0.85 -> 0.92 (~8pp below TRAIN) to lock in the gain.
    "pin": 0.92,  # train 0.998 / test 1.000 (951 TP, 2 FP; cook pin_prevents_escape fix)
    "double-check": 0.93,  # train 1.000 / test 1.000 (phase 131-03 lock; raised from 0.80)
    # Phase 131-03 (D-09 never-regress lock, measured 2026-06-22):
    # discovered-check: floor raised from 0.80 to 0.85 per D-09 (hold ≥0.85).
    # Quick 260623 (whole-line scan): detect_discovered_check now scans EVERY pov move
    # (cook.discovered_check `mainline[1::2]`), not just moves[0]. Recall 0.16 -> 0.337
    # train / 0.314 -> 0.322 test; precision 0.953 train / 0.936 test (~1pp train dip, test
    # up). Floor held at the D-09 ≥0.85 lock (TRAIN 0.953 clears comfortably).
    "discovered-check": 0.85,  # train 0.953 / test 0.936 (D-09 lock ≥0.85; whole-line scan)
    # --- Tier 1 mates (confidence=100) ---
    "mate": 0.95,  # train 1.000 / test 1.000 (unchanged)
    "smothered-mate": 0.93,  # train 1.000 / test 1.000 (phase 131-03 lock; raised from 0.90)
    # Phase 131-03 (cook geometry tightening, measured 2026-06-22):
    # back-rank-mate: 0.281 -> 1.000 train (own-blocker test + back-rank-checker requirement).
    # anastasia-mate: 0.822 -> 1.000 train (king+1 blocker + king+3 knight geometry + file gate).
    # hook-mate: 0.840 -> 1.000 train (knight-adjacent-to-king constraint added).
    # Floors raised to ~7pp below new measured TRAIN (conservative given mates are small-count motifs).
    "back-rank-mate": 0.93,  # train 1.000 / test 1.000 (was 0.20; phase 131-03 cook port)
    "anastasia-mate": 0.93,  # train 1.000 / test 1.000 (was 0.75; phase 131-03 cook port)
    "hook-mate": 0.93,  # train 1.000 / test 1.000 (was 0.80; phase 131-03 cook port)
    # --- Tier 3 graded + Tier 4 ---
    # deflection: Phase 132-02 cook 11-condition AND-chain rewrite. TRAIN 0.994 (162 TP, 1 FP),
    # TEST 1.000 (62 TP, 0 FP). Floor set at 0.93 (~6pp below TRAIN 0.994).
    # Tagger precision pass: corrected the deflection port to cook (king_values not values;
    # is_check/attacks on grandpa.board()=boards[k-1] not the init board). FP 9->1, and recall
    # rose 0.14->0.32 (the old boards/values both over-fired and under-caught). P 0.959->0.998.
    # Phase 221 TAGFIX-05 fix 1 (D-12): condition 10 restored to cook's single OR (attacks(orig)
    # OR promotion-same-file-and-reachable), not an if/elif that skipped the attacks disjunct
    # for every promotion move. TRAIN TP 490->618 (+128), FP unchanged (2); TEST TP 197->247
    # (+50), FP 0->1 (still comfortably above floor). Floor held at 0.92.
    # Phase 221 plan 06 final consolidation: TRAIN TP 618->641 (+23), TEST TP
    # 247->252 (+5), FP unchanged (2 train, 1 test) — further downstream
    # dispatch redistribution from plans 04/05. Floor unchanged at 0.92.
    "deflection": 0.92,  # train 0.997 / test 0.996 (650 TP, 2 FP; phase 221 final measurement, post clearance suppression)
    # clearance: Phase 132-02 cook 9-condition AND-chain rewrite. TRAIN 0.913 (199 TP, 19 FP),
    # TEST 0.952 (99 TP, 5 FP). Floor set at 0.87 (~5pp below TRAIN 0.913).
    # Tagger precision pass: cook clearance condition 7 checked the opponent's FUTURE response
    # (moves[k+1]); cook uses the opponent's PRIOR move (moves[k-1]). FP 13->0, recall 0.39->0.44.
    #
    # Phase 221 TAGFIX-04 (D-06/D-07, plan 05, DELIBERATE divergence from cook —
    # see the module docstring's Phase 221 paragraph): three additions to cook's
    # 9-condition chain. (1) The vacating (prior pov) move must not be a king or
    # pawn move (a dev hand review found 9 of 12 sampled clearance tags were king
    # retreats, pawn pushes, or piece shuffles — not real clearances). (2) The
    # clearing move must actually USE the newly-opened line (gives check, or
    # attacks a higher-value or hanging opponent piece) — cook has no such test.
    # (3) The scan caps at SACRIFICE_CLEARANCE_MAX_DEPTH=4 (shared with
    # sacrifice, D-06) — dev average firing depth for clearance was 3.73 vs
    # 0.00-1.35 for the geometric motifs. Recall falls by design (measured:
    # TRAIN TP 399->216 recall 0.457->0.247, TEST TP 159->90 recall 0.449->0.254);
    # precision must NOT fall and does not (1.000 -> 1.000 both splits, 0 FP
    # throughout). A future precision pass must NOT relax these three additions
    # to recover fixture recall; if a real-game measurement finds the cut too
    # soft, SACRIFICE_CLEARANCE_MAX_DEPTH is the lever, never a re-litigation of
    # D-07. `clearance`'s survival past this phase is contingent on a real-game
    # real-share bar of 0.8 (REALGAME_REAL_SHARE_FLOOR below, measured in the
    # same plan) — decided by plan 06, not this one.
    #
    # Phase 221 plan 06 (2026-09-12, D-07): SUPPRESSED. The real-game bar above
    # was measured at real_share=0.667 with only 3 of 16 rows surviving (below
    # REALGAME_MIN_ROWS_FOR_FLOOR=8) — the SUPPRESS branch of the D-07 keep/
    # suppress decision. `clearance` is now in SUPPRESSED_MOTIFS, removed from
    # _TIER3_REGISTRY (tactic_detector.py) so no PV can dispatch it, and removed
    # from FAMILY_TO_MOTIF_INTS / tacticComparisonMeta.ts's Advanced group. This
    # CC0-fixture PRECISION_FLOOR entry (0.93, 216 TP TRAIN, 0 FP — still exactly
    # correct as a STANDALONE-predicate measurement) is commented out rather than
    # deleted for the historical record; it no longer gates anything because
    # `test_detector_precision_and_recall` only asserts floors for un-suppressed
    # motifs.
    # "clearance": 0.93,  # train 1.000 / test 1.000 (216 TP, 0 FP; phase 221 D-06/D-07 strengthening)
    # Tagger precision pass: lichess `interference` = cook self_interference OR interference; the
    # old port did a single non-ray-aware self_interference-shaped check. Now fires on either
    # faithful variant. FP 8->1, recall 0.43->0.59. P 0.967->0.997.
    "interference": 0.92,  # train 0.997 / test 1.000 (357 TP, 1 FP; cook either-variant fix)
    # capturing-defender: Phase 132-03 cook 9-condition AND-chain rewrite. Tagger precision
    # pass added cook's missing `not prev.board().is_check()` guard (boards[k-1]) + ray-aware
    # hanging test — this declines intermezzo lines (checking zwischenzug before recapture)
    # that were the entire FP source. P(train) 0.869 -> 1.000, P(test) -> 1.000, recall held.
    # Raised floor 0.82 -> 0.93 (~7pp below TRAIN) to lock in the gain.
    "capturing-defender": 0.93,  # train 1.000 / test 1.000 (377 TP, 0 FP; cook is-check guard fix)
    # intermezzo: Phase 132-03 cook zwischenzug AND-chain (moves[k-3] original-capture +
    # was-legal-earlier condition + opponent non-attacker gate). TRAIN 0.907 (39 TP, 4 FP),
    # TEST 1.000 (25 TP, 0 FP). Floor set at 0.85 (~6pp below TRAIN 0.907, rounded to 0.05).
    # Phase 134 (full-regen re-measure): the larger 2026-06 fixture surfaces more intermezzo
    # FPs. n(train) 702 -> 751, P(train) 0.938 -> 0.759 (TP=22, FP=7). Lowered 0.85 -> 0.70
    # (~6pp below new TRAIN; TEST 0.750 clears). Detector unchanged (Plan 02 owns geometry).
    # Tagger precision pass: reimplemented intermezzo to cook's exact control flow (early-exit
    # at the first qualifying pov capture) + the first-move (k=2) case using the flaw move from
    # boards[0].move_stack. P(train) 0.800 -> 1.000, P(test) -> 1.000, and recall 0.03 -> 0.61
    # (the k=2 first-move zwischenzugs were previously undetectable). Floor 0.70 -> 0.92.
    "intermezzo": 0.92,  # train 1.000 / test 1.000 (457 TP, 0 FP; cook control-flow + k=2 fix)
    # x-ray: Phase 132-04 cook three-same-square AND-chain (moves[k-2].to == moves[k-1].to
    # == moves[k].to, between-square geometry, non-king recapturer). TRAIN 1.000 (225 TP, 0 FP),
    # TEST 1.000 (103 TP, 0 FP). Floor set at 0.93 (~7pp below TRAIN 1.000, rounded to 0.01).
    "x-ray": 0.93,  # train 1.000 / test 1.000 (phase 132-04 cook three-same-square AND-chain)
    # Phase 131-03: hanging-piece floor confirmed. Depth-primary dispatch (plan-01) changed
    # which motif wins when hanging-piece competes with geometrics, reducing train from
    # 0.990 to 0.909; floor stays at 0.90 (still 1pp above train, within 5-8pp band goal).
    # D-09 "0.95 puzzle precision" refers to the test-set measure at Phase 127/128 baseline.
    # Phase 134 (full-regen re-measure): the larger 2026-06 fixture surfaces many more
    # hanging-piece FPs. n(train) 734 -> 857, P(train) 0.915 -> 0.743 (TP=625, FP=216).
    # Tagger precision pass: ported cook's hanging_piece gates (ray-aware is_hanging, check-gate,
    # king-exclusion, material-maintenance boards[3] >= boards[1]) AND cook's recapture exclusion
    # (values[op_capture] >= values[captured]), computed from the flaw move on boards[0].move_stack
    # — production already passes that board; the gate now builds it the same way (PreFlawFEN +
    # push). FPs 216 -> 0 with ZERO true-positive loss. P(train) 0.743 -> 1.000, P(test) -> 1.000.
    # Floor 0.68 -> 0.92.
    "hanging-piece": 0.92,  # train 1.000 / test 1.000 (631 TP, 0 FP; cook gates + recapture exclusion)
    # --- Tier 5 move-type (Phase 128.1-02; whole-line scan Quick 260623) ---
    # Quick 260623: the three move-type detectors now scan EVERY pov move (cook's
    # promotion/under_promotion/en_passant `mainline[1::2]`), not just moves[0], and the
    # dispatcher gates Tier 5 behind `if not candidates` so move-type is a STRICT residual
    # fallback (any real tactic in tiers 1-4 always wins). Precision stays 1.000 / 0 FP on
    # both splits (move-type only wins on residual lines lichess also tags), and recall
    # jumps: promotion 0.05 -> 0.487 train / 0.481 test, en-passant 0.30 -> 0.622 / 0.626,
    # under-promotion 0.12 -> 0.324 / 0.349. Floors unchanged (all clear comfortably).
    "promotion": 0.60,  # train 1.000 / test 1.000 (1816 TP, 0 FP; whole-line residual scan)
    "en-passant": 0.93,  # train 1.000 / test 1.000 (1219 TP, 0 FP; whole-line residual scan)
    "under-promotion": 0.90,  # train 1.000 / test 1.000 (253 TP, 0 FP; whole-line residual scan)
    # --- Phase 133 unsuppressed motifs (measured 2026-06-23, phase 133 cook ports) ---
    # All five measured at TRAIN 1.000 / 0 FP; floors set at 0.93 (~7pp below, rounded to 0.05).
    "attraction": 0.93,  # train 1.000 / test ~1.000 (654 TP, 0 FP; phase 133 cook port)
    #
    # Phase 221 TAGFIX-03 (D-05/D-06, plan 05, DELIBERATE divergence from cook —
    # see the module docstring's Phase 221 paragraph): cook's predicate fires
    # whenever pov is down >= MIN_SACRIFICE_DROP at ANY pov move from the 2nd
    # onward, with no recovery test and no depth limit — 32% of cook's own
    # sacrifice puzzles are delayed recaptures / zwischenzugs, which is exactly
    # the shape this drops. D-05 requires the deficit to still hold after the
    # NEXT pov move (boards[k+3]), or the line to end first; D-06 caps the scan
    # at SACRIFICE_CLEARANCE_MAX_DEPTH=4 (shared with clearance; dev average
    # firing depth 4.78 vs 0.00-1.35 for the geometric motifs). Recall falls by
    # design (measured: TRAIN TP 397->177 recall 0.111->0.050, TEST TP 183->70
    # recall 0.118->0.045); precision must NOT fall and does not (1.000 -> 1.000
    # both splits, 0 FP throughout).
    #
    # Phase 221 plan 08 (2026-09-13, gap closure — D-13 operator spot-check
    # AMENDS the above): D-05 is RETIRED. The operator's 221-D13-SPOTCHECK.md
    # review found two frozen real-game rows (fixtures/tagger/realgame_tags.csv
    # 0064, 0133) that D-05 wrongly dropped ARE genuine sacrifices — their
    # material recovers at boards[k+3] because the sacrifice worked (Nxd6,
    # gxf8=Q+ are the tactic's own follow-ups), which is exactly the shape D-05's
    # literal persistence check cannot distinguish from a delayed recapture. Task
    # 1 of plan 08 measured three board-derivable candidate discriminators (see
    # CONTEXT.md's "lead worth checking first") against the corrected label set
    # and found NONE separates the two populations: "recovery overshoots the
    # entry baseline" also fires on row 0134 (confirmed NOT a real sacrifice —
    # relabelled real->wrong this same plan); "deficit depth" does not separate
    # them (0134 reaches the same -3 minimum as genuine row 0064); "the opponent
    # chose to accept" matches 0064's shape but not 0133's (both of pov's early
    # moves there are captures, not a quiet offer). Per this plan's own
    # instruction, a rule known to fail a confirmed-real row must not ship —
    # `detect_sacrifice` was reverted to cook's unguarded predicate (D-06 depth
    # cap kept unchanged; it is orthogonal to D-05 and was never implicated).
    # D-01's per-tier winning floor (TAGFIX-01, already shipped) independently
    # covers the case D-05 was built for: of the 7 real-game rows D-05 removed
    # beyond cook's own predicate, D-01's floor alone would have kept exactly
    # the 3 genuine/plausible sacrifices and rejected the other 4 (three
    # deep-losing lines plus row 0134). Never re-introduce a persistence check
    # on `detect_sacrifice` without new eval access or a materially larger
    # labelled sample — this amendment is not "D-05 was a bad idea", it is
    # "no board-derivable version of D-05 survived the operator's evidence".
    # Measured effect of the revert: TRAIN TP 208->456 (recall 0.128, up from
    # 0.050), TEST TP 77->196 (recall 0.127, up from 0.045); FP unchanged at 0
    # both splits, precision unchanged at 1.000 both splits. A handful of other
    # motifs lost a small number of TRAIN/TEST TPs to sacrifice's newly-widened
    # dispatch wins (pure redistribution, same pattern as every prior Phase 221
    # plan) — no other motif's FP count changed and every floor still clears
    # with headroom (see the plan 06 final-consolidation table above; unchanged
    # by this amendment except sacrifice's own row).
    "sacrifice": 0.93,  # train 1.000 / test 1.000 (456 TP, 0 FP; phase 221 plan 08, D-05 retired)
    "arabian-mate": 0.93,  # train 1.000 / test ~1.000 (553 TP, 0 FP; phase 133 cook port)
    # Phase 221 TAGFIX-05 fix 6 (D-12): corrected the file-relation test to cook's
    # actual asymmetric formula ((bishop_squares[0] left-of-king-file) ==
    # (bishop_squares[1] right-of-king-file), not a symmetric opposite-sides XOR).
    # TRAIN TP 441->442 (+1; the one row where the SECOND bishop by square-index
    # order sits on the king's file). double-bishop-mate stays SUPPRESSED (unchanged
    # by this fix; see the module-docstring oracle finding for the much larger,
    # separately-tracked firing gap on both motifs). Floor unchanged.
    "boden-mate": 0.93,  # train 1.000 / test ~1.000 (442 TP, 0 FP; phase 221 D-12 file-test fix)
    "dovetail-mate": 0.93,  # train 1.000 / test ~1.000 (543 TP, 0 FP; phase 133 cook port)
    # --- Phase 134 unsuppressed motif (measured 2026-06-23, phase 134 cook captured-chain port) ---
    # trapped-piece: cook capture-chain-anchored is_trapped predicate. TRAIN 1.000 (565 TP, 0 FP),
    # TEST 1.000 (239 TP, 0 FP). deltaP=0.000. Floor set at 0.92 (~8pp below TRAIN 1.000).
    # Phase 221 plan 06 final consolidation: TRAIN TP 565->634 (+69), TEST TP
    # 239->276 (+37), FP unchanged (0 both) — downstream dispatch
    # redistribution from plans 02/04/05 (fix 3's empty-escape revert,
    # sacrifice/clearance depth cap, discovered-attack depth=k). Floor
    # unchanged at 0.92.
    "trapped-piece": 0.92,  # train 1.000 / test 1.000 (657 TP, 0 FP; phase 221 final measurement, post clearance suppression)
}

# ---------------------------------------------------------------------------
# Real-game never-regress floors (Phase 221, TAGFIX-07 / D-13) — orthogonal to
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

# Phase 221 plan 06 (2026-09-12) — POST-FIX finalisation. All floors below are
# re-seeded from the measurement AFTER every TAGFIX-01..06 detector/gate change
# landed (plans 02-05), against the SAME frozen 164-row fixtures/tagger/
# realgame_tags.csv plan 01 sampled before any of those changes — see
# tests/scripts/tagger/test_detector_precision.py::test_realgame_real_share_floor
# for the reproducible measurement. This SUPERSEDES the pre-fix baseline plan 01
# seeded (sacrifice 0.32, clearance 0.38, intermezzo 0.70, x-ray 0.82). Each
# value is seeded ~0.05 below the measured post-fix real_share, clamped to
# [0.0, 1.0], rounded DOWN to stay conservative. Only motifs whose surviving
# count clears REALGAME_MIN_ROWS_FOR_FLOOR get an entry — every other tagged
# motif in the CSV is reported in the table but never gated.
REALGAME_REAL_SHARE_FLOOR: dict[str, float] = {
    # POST-FIX (plan 06) measured real_share DROPPED to 0.222 (2/9 surviving are
    # `real`; 7 of the original 16 rows correctly suppressed by D-01's winning
    # floor + D-05's persistence rule). This is BELOW the pre-fix floor (0.32,
    # itself derived from the pre-fix 0.375 measurement) — D-05's persistence
    # rule was expected to RAISE real-share but instead measured LOWER on this
    # frozen sample. Root cause (traced row-by-row in plan 05's SUMMARY "Known
    # Issues"): several rows a human labelled `real` are attacking sacrifices
    # that fully repay via a DIFFERENT tactical point 1-2 plies later (row
    # 0064: a knight sac at k=2 objectively winning at +264cp, material fully
    # recovers via an unrelated bishop capture at k=4) — exactly the "delayed
    # compensation" shape D-05 is designed to exclude, applied faithfully to a
    # case the (executor-assigned, operator-unverified) label judged
    # differently. Floor re-seeded ~0.05 below the new measurement (0.222 -
    # 0.05 = 0.172, rounded down to 0.17). Carried forward as an operator
    # spot-check item for 221-UAT.md.
    #
    # Phase 221 plan 08 (2026-09-13, gap closure — SUPERSEDES the plan 06
    # number above): the operator spot-check landed (221-D13-SPOTCHECK.md) and
    # overturned the assumption behind it — rows 0064 and 0133 are genuine
    # sacrifices D-05 wrongly dropped, and row 0134 (the fourth contested row)
    # was mislabelled `real` and is corrected to `wrong` this same plan (White
    # never offers material). D-05 is RETIRED (see the PRECISION_FLOOR
    # divergence block above for the full measurement); re-scored on the SAME
    # frozen 164-row fixture: surviving 9->13, real_surviving 2->5, real_share
    # 0.222->0.385. This CLEARS not only the pre-fix floor (0.32) but the
    # pre-fix MEASUREMENT itself (0.375) — the outcome the phase's own CONTEXT.md
    # named as possible if D-05 proved net-harmful once D-01 existed. Floor
    # re-seeded ~0.05 below the new measurement (0.385 - 0.05 = 0.335, rounded
    # down to 0.33), same convention as every other entry in this dict. Never
    # patched around a code defect — the code is now believed CORRECT (cook's
    # unguarded predicate + D-01's independent winning floor), and this is a
    # genuine re-measurement, not a regression tolerance widening.
    "sacrifice": 0.33,  # plan 08 post-revert: surviving 13, real_surviving 5, real_share 0.385
    # measured real_share 0.750 (12/16 real) — UNCHANGED from plan 01's pre-fix
    # baseline. D-09 (missed-orientation move stack) was expected to be the
    # main lever here, but tests/scripts/tagger/conftest.py::build_realgame_
    # board was written in plan 01 to ALREADY push a move on both
    # orientations (simulating the post-D-09 production board build, ahead of
    # D-09 landing in flaws_service.py in plan 04) — so this fixture's
    # intermezzo score was never subject to the pre-D-09 stackless bug plan 01
    # measured separately against dev. Floor unchanged at 0.70 (re-confirmed
    # post-fix; only the provenance note changes, not the value).
    "intermezzo": 0.70,  # post-fix: surviving 16, real_surviving 12, real_share 0.750
    # measured real_share 0.875 (14/16 real) — UNCHANGED from plan 01's
    # pre-fix baseline. x-ray's strict AND-chain (three-same-square +
    # between-square geometry) was already precision-clean; D-01's winning
    # floor and D-06's depth cap (x-ray is not sacrifice/clearance, so D-06
    # does not apply to it) neither raised nor lowered this motif's real-game
    # behaviour. Floor unchanged at 0.82 (re-confirmed post-fix).
    "x-ray": 0.82,  # post-fix: surviving 16, real_surviving 14, real_share 0.875
    # `clearance` had a floor here in the pre-fix baseline (0.38, 7/16 real =
    # 0.4375). POST-FIX: only 3 of 16 rows survive the strengthened D-07
    # predicate (13 correctly suppressed), below REALGAME_MIN_ROWS_FOR_FLOOR=8
    # — the denominator is too thin to trust regardless of its real_share
    # (which, among the 3 survivors, is 0.667: 2 real). Per this plan's own
    # "## The D-07 branch contract", a surviving count below the minimum
    # takes the SUPPRESS branch outright (a handful of rows is not a passing
    # measurement) — executed in this plan's next task, which comments out
    # `clearance`'s PRECISION_FLOOR entry too and adds it to SUPPRESSED_
    # MOTIFS. No REALGAME_REAL_SHARE_FLOOR entry for `clearance` after this
    # plan — a suppressed, undispatchable motif from here on (int 15 remains
    # encodable/decodable/storable for the existing rows the prod retag will
    # clear).
    # "clearance": 0.38,  # SUPPRESSED 2026-09-12 (D-07): real_share 0.667 among
    #                       3 surviving rows (< REALGAME_MIN_ROWS_FOR_FLOOR=8) —
    #                       both branch conditions miss; see PRECISION_FLOOR's
    #                       clearance entry and SUPPRESSED_MOTIFS above for the
    #                       full D-07 keep/suppress decision record.
}
