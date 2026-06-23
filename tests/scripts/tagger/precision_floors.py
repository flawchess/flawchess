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
  - trapped-piece (28 TRAIN labels): TP=0, FP=9 → only-FP. The detector fires on 9
    positions that our v3 SEE gate classifies as "all escapes lose material" but whose
    lichess label is not trappedPiece (broader coverage in lichess theme). Zero precision →
    added to SUPPRESSED_MOTIFS. The D-06 strict gate is precision-first by design;
    fast-guard fixtures in _TRAPPED_PIECE_FIXTURES remain as structural regression guards.
  - en-passant (12 TRAIN labels): NaN (never fires at Tier 5). The 12 enPassant rows all
    have a higher-priority real tactic (fork, pin, discovered-check, mate, etc.) that wins
    the dispatch. Move-type only fires on the residual; the residual has 0 enPassant-labeled
    rows → NaN. Added to SUPPRESSED_MOTIFS. The detector itself is structurally validated
    by fast-guard fixtures in _EN_PASSANT_FIXTURES.
  - promotion (176 TRAIN labels including underPromotion, 57 TEST): fires once (TP=1, FP=0,
    P=1.000 train). Like en-passant, most promotion rows have a higher-priority tactic.
    1 TP is very thin but the precision is 100% — floor set conservatively at 0.60 to allow
    for variance while still catching zero-precision regressions.
  - under-promotion (4 TRAIN / 4 TEST labels): TP=0, FP=0, NaN. Both the 4 TRAIN and 4 TEST
    underPromotion-labeled rows also carry arabian-mate (back-rank-mate / smothered-mate
    territory), so Tier-1 mate pre-empts under-promotion in every case. D-08 approach (i)
    chosen: NO percentage floor is assigned. Structural validation is provided by the
    _UNDER_PROMOTION_FIXTURES fast-guard set (4 curated positions that DO return
    "under-promotion" because no real tactic fires). The fast-guard test
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
        "self-interference",
        "double-bishop-mate",
        # Phase 128.1-01 (measured 2026-06-20):
        "trapped-piece",  # 0 TP, 9 FP — only-FP; D-06 strict gate is precision-first
        # Phase 128.1-02 move-type family (measured 2026-06-20):
        # These three never fire in the harness because every real-world en-passant /
        # promotion / under-promotion puzzle also has a higher-priority real tactic that
        # wins the dispatch at Tier 5.  Structural validation is via fast-guard fixtures;
        # see the measurement notes in the module docstring above.
        "en-passant",  # 0 TP, 0 FP — NaN, all shadowed by real tactics at TRAIN
        "under-promotion",  # 0 TP, 0 FP — NaN, n=4 labels, all have Tier-1 mates (D-08 approach i)
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
    "fork": 0.93,  # train 1.000 / test 0.998 (993 TP, 1 FP; phase 131-02 cook port)
    "skewer": 0.93,  # train 1.000 / test 1.000 (432 TP, 0 FP; phase 131-02 cook port)
    "discovered-attack": 0.93,  # train 0.995 / test 1.000 (321 TP, 2 FP; phase 131-02 cook port)
    # Phase 131 pin fix (measured 2026-06-22): scan only POV-move result boards (odd PV
    # indices = cook's node set) instead of every board. 0.819 -> 0.944 test / 0.752 -> 0.934
    # train, recall held (~0.60). Floor at the 0.90 ship bar (TRAIN 0.934 clears it).
    "pin": 0.90,  # train 0.934 / test 0.944 (699 TP, 49 FP post-dispatch; phase 131 odd-board fix)
    "double-check": 0.93,  # train 1.000 / test 1.000 (phase 131-03 lock; raised from 0.80)
    # Phase 131-03 (D-09 never-regress lock, measured 2026-06-22):
    # discovered-check: floor raised from 0.80 to 0.85 per D-09 (hold ≥0.85; train 0.913 / test 0.884).
    # The depth-primary dispatch (plan-01) shifted some DA sub-case-1 positions to discovered-check,
    # keeping train above the new 0.85 floor.
    "discovered-check": 0.85,  # train 0.913 / test 0.884 (D-09 lock ≥0.85; raised from 0.80)
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
    "deflection": 0.93,  # train 0.994 / test 1.000 (phase 132-02 cook 11-condition AND-chain)
    # clearance: Phase 132-02 cook 9-condition AND-chain rewrite. TRAIN 0.913 (199 TP, 19 FP),
    # TEST 0.952 (99 TP, 5 FP). Floor set at 0.87 (~5pp below TRAIN 0.913).
    "clearance": 0.87,  # train 0.913 / test 0.952 (phase 132-02 cook 9-condition AND-chain)
    "interference": 0.80,  # train 1.000 / test 1.000 (21 TP, 0 FP)
    # capturing-defender: Phase 132-03 cook 9-condition AND-chain rewrite (init-board defender
    # test, value gate, _is_hanging, prev-op not-recapture, etc.). TRAIN 0.869 (326 TP, 49 FP),
    # TEST 0.903 (132 TP, 14 FP). Floor set at 0.82 (~5pp below TRAIN 0.869, rounded to 0.01).
    "capturing-defender": 0.82,  # train 0.869 / test 0.903 (phase 132-03 cook AND-chain)
    # intermezzo: Phase 132-03 cook zwischenzug AND-chain (moves[k-3] original-capture +
    # was-legal-earlier condition + opponent non-attacker gate). TRAIN 0.907 (39 TP, 4 FP),
    # TEST 1.000 (25 TP, 0 FP). Floor set at 0.85 (~6pp below TRAIN 0.907, rounded to 0.05).
    "intermezzo": 0.85,  # train 0.907 / test 1.000 (phase 132-03 cook AND-chain)
    # x-ray: Phase 132-04 cook three-same-square AND-chain (moves[k-2].to == moves[k-1].to
    # == moves[k].to, between-square geometry, non-king recapturer). TRAIN 1.000 (225 TP, 0 FP),
    # TEST 1.000 (103 TP, 0 FP). Floor set at 0.93 (~7pp below TRAIN 1.000, rounded to 0.01).
    "x-ray": 0.93,  # train 1.000 / test 1.000 (phase 132-04 cook three-same-square AND-chain)
    # Phase 131-03: hanging-piece floor confirmed. Depth-primary dispatch (plan-01) changed
    # which motif wins when hanging-piece competes with geometrics, reducing train from
    # 0.990 to 0.909; floor stays at 0.90 (still 1pp above train, within 5-8pp band goal).
    # D-09 "0.95 puzzle precision" refers to the test-set measure at Phase 127/128 baseline.
    "hanging-piece": 0.90,  # train 0.909 / test 0.884 (confirmed; 0.90 floor still passes)
    # --- Tier 5 move-type (Phase 128.1-02, measured 2026-06-20) ---
    # promotion: TP=1, FP=0, P=1.000 train (TEST=NaN, never fires on held-out set).
    # Very thin (1 TP) but 100% precision. Floor set conservatively at 0.60 to catch
    # zero-precision regressions while tolerating 1-sample variance. en-passant and
    # under-promotion are in SUPPRESSED_MOTIFS (NaN / n=4 respectively — D-08).
    "promotion": 0.60,  # train 1.000 (1 TP, 0 FP) — thin but structurally correct
    # --- Phase 133 unsuppressed motifs (measured 2026-06-23, phase 133 cook ports) ---
    # All five measured at TRAIN 1.000 / 0 FP; floors set at 0.93 (~7pp below, rounded to 0.05).
    "attraction": 0.93,  # train 1.000 / test ~1.000 (654 TP, 0 FP; phase 133 cook port)
    "sacrifice": 0.93,  # train 1.000 / test ~1.000 (236 TP, 0 FP; phase 133 unsuppress-only)
    "arabian-mate": 0.93,  # train 1.000 / test ~1.000 (553 TP, 0 FP; phase 133 cook port)
    "boden-mate": 0.93,  # train 1.000 / test ~1.000 (435 TP, 0 FP; phase 133 cook port)
    "dovetail-mate": 0.93,  # train 1.000 / test ~1.000 (543 TP, 0 FP; phase 133 cook port)
}
