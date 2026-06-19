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

Precision floors are set at ~5-8pp below the measured TRAIN value (rounded to 0.05)
to give a stable CI gate that fails on genuine regressions, not normal variance.
Motifs with NaN precision (never fire) or only-FP (0 TP, >0 FP) are in SUPPRESSED_MOTIFS.

Suppression notes:
  Tier-3 motifs in SUPPRESSED_MOTIFS are filtered at query time via the
  _TACTIC_CHIP_CONFIDENCE_MIN lever in library_repository.py (currently 70).
  Tier-1/2 motifs (confidence always 100) cannot be suppressed via this lever —
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
        # Never fires (0 TP, 0 FP): NaN precision — no gate needed. (TRAIN, 11855 rows)
        "arabian-mate",
        "boden-mate",
        "sacrifice",
        # Only-FP (0 TP, >0 FP): zero precision. Named mate (confidence=100, no lever):
        "dovetail-mate",  # 0 TP, 23 FP
        # Only-FP tier-3, suppressed via _TACTIC_CHIP_CONFIDENCE_MIN=70:
        "attraction",  # 0 TP, 10 FP
        "intermezzo",  # 0 TP, 5 FP
        "x-ray",  # 0 TP, 10 FP
        "capturing-defender",  # 0 TP, 3 FP
        # Unvalidated motifs (no lichess theme equivalent) — excluded from measurement.
        "self-interference",
        "double-bishop-mate",
    }
)

# ---------------------------------------------------------------------------
# Per-motif precision floors — set from measured TRAIN numbers (D-09)
# ---------------------------------------------------------------------------

# Floors sit ~5-8pp below the measured TRAIN precision so the CI gate fails on genuine
# regressions without being brittle to fixture variance. These are the never-regress
# floors; aspirational improvement targets live in GOALS in scripts/tactic_tagger_report.py.
#
# NOTE: back-rank-mate (0.281), fork (0.437), pin (0.440), skewer (0.162),
# discovered-attack (0.193), deflection (0.130) remain well below a "trustworthy" bar.
# back-rank over-fires onto corner mates; the geometric detectors carry large FP pools.
# pin's SEED-057 gate fix (parity + reject-before-accept ordering) lifted it 0.413 -> 0.440;
# further gains require detector hardening (drive it via the GOALS loop), not a floor edit.

PRECISION_FLOOR: dict[str, float] = {
    # --- Tier 2 geometric material-winners (confidence=100) ---
    "fork": 0.35,  # train 0.437 / test 0.400
    "pin": 0.40,  # train 0.440 / test 0.439 (SEED-057 gate fix; re-set from 0.35 to lock the gain)
    "skewer": 0.10,  # train 0.162 / test 0.154
    "discovered-attack": 0.15,  # train 0.193 / test 0.198
    "double-check": 0.80,  # train 1.000 / test 1.000 (28 TP, 0 FP)
    # --- Tier 1 mates (confidence=100) ---
    "mate": 0.95,  # train 1.000 / test 1.000
    "smothered-mate": 0.90,  # train 1.000 / test 1.000
    "anastasia-mate": 0.75,  # train 0.822 / test 0.857
    "hook-mate": 0.80,  # train 0.840 / test 0.841
    "back-rank-mate": 0.20,  # train 0.281 / test 0.271 — over-fires on corner mates
    # --- Tier 3 graded + Tier 4 ---
    "clearance": 0.35,  # train 0.433 / test 0.833 (low train n)
    "interference": 0.80,  # train 1.000 / test 1.000 (21 TP, 0 FP)
    "deflection": 0.10,  # train 0.130 / test 0.141 — most FPs <70 confidence (query-suppressed)
    "hanging-piece": 0.90,  # train 0.990 / test 0.952
}
