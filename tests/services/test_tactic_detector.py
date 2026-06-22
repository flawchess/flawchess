"""Fixture-driven precision tests for the Phase 124 tactic-motif detector (TACDET-03).

FIXTURE PROVENANCE (D-09): every positive fixture is a REAL prod mistake/blunder
position sampled from the dev DB (game_flaws joined to game_positions.pv at
flaw_ply+1), bucketed by the detector and CONFIRMED BY HUMAN INSPECTION. The shared
hard-negative set is real quiet/positional prod errors whose refutation contains no
tactic. NONE of these fixtures are derived from cook.py output (the AGPL reference) —
sourcing is our own prod data + the detector under test; labels are confirmed by
inspection. See .planning/phases/124-schema-tactic-detector/124-RESEARCH.md.

FIXTURE FORMAT (Claude's discretion per RESEARCH §Fixture format): each positive is
`(fen_after_flaw, pv_uci, expected_motif)`. We store the FEN *after* the flawed move
(the detector's actual input) rather than (fen_before, move_san) — this removes the
SAN-reparse failure mode (RESEARCH Pitfall 6) and is exactly what detect_tactic_motif
consumes. Hard-negatives are `(fen_after_flaw, pv_uci)` and must return None.

CIRCULAR FIXTURE WARNING (D-12 / SC#5 — Phase 127):
  These fixtures are detector-bucketed (circular): positions were labelled by running
  the same detector under test, then confirmed by inspection. This means the precision
  bars here measure the detector's self-consistency, NOT its agreement with an
  independent ground truth. The bars are vacuous in a strict sense — a regressed
  detector that consistently mis-classifies will still appear to pass if its errors
  are stable across runs.

  The AUTHORITATIVE precision/recall numbers for the Phase 127 detector now come from
  the independent lichess CC0 puzzle harness at:
      tests/scripts/tagger/test_detector_precision.py
  That harness scores against 4368 stratified CC0 puzzles (database.lichess.org)
  with per-motif floors set from measured numbers (D-09). It is the CI precision gate.

  These tests REMAIN as fast per-commit signature/regression guards (they run in the
  default pytest suite and catch signature changes, PV-parsing errors, and obvious
  mis-classifications) but their precision bars are NO LONGER the authoritative trust
  source (D-12). Do not lower these bars to pass a regressed detector; investigate the
  regression in the CC0 harness instead.

D-10 TIERED PRECISION BARS (precision-first; recall NOT gated):
  Core 8     >= CORE_PRECISION_BAR  (0.90)
  tier-3 + named-mate >= TIER3_PRECISION_BAR (0.95)
A motif that cannot reach >=10 hand-confirmed prod fixtures is QUERY-SUPPRESSED
(_QUERY_SUPPRESSED_MOTIFS) — its detector still STORES the motif int (D-11); the
bar is recorded but not enforced (xfail) until validated in a later phase (Q-011).
This is the documented Q-011 risk carry-forward, NOT a silently-lowered bar.
"""

from __future__ import annotations

import chess
import pytest

from app.services.tactic_detector import (
    MATE_MOTIFS,
    MOVE_TYPE_MOTIFS,
    TacticMotif,
    TacticMotifInt,
    _INT_TO_MOTIF,
    _MOTIF_TO_INT,
    detect_tactic_motif,
)

# D-10 precision bars (named constants — never lower these to pass a flaky detector).
CORE_PRECISION_BAR = 0.90
TIER3_PRECISION_BAR = 0.95

# Core 8 motifs (>=90% bar); everything else is tier-3 / named-mate (>=95% bar).
_CORE_MOTIFS: frozenset[TacticMotif] = frozenset(
    {
        "fork",
        "hanging-piece",
        "pin",
        "skewer",
        "double-check",
        "discovered-attack",
        "back-rank-mate",
        "mate",
    }
)

# Motifs that lack >=10 hand-confirmed prod fixtures and are therefore query-suppressed
# (stored per D-11, surfaced suppressed until per-motif validation — Q-011 / RESEARCH OQ2).
_QUERY_SUPPRESSED_MOTIFS: frozenset[TacticMotif] = frozenset(
    {
        "double-check",  # Core 8, but only 1 prod occurrence in the dev sample
        "interference",  # 1 prod occurrence
        "smothered-mate",  # 2 prod occurrences
        "self-interference",  # 0 prod occurrences in dev sample
        "sacrifice",  # 0 (rarely the priority winner; hanging/geometric pre-empt)
        "arabian-mate",  # 0 prod occurrences
        "boden-mate",  # 0 prod occurrences
        "double-bishop-mate",  # 0 prod occurrences
    }
)

# === Per-motif positive fixtures (real prod flaws, hand-confirmed) ===

_FORK_FIXTURES: list[tuple[str, str, TacticMotif]] = [
    # Rebuilt in Phase 131 Plan 02 from CC0 lichess puzzle fixtures where the new
    # cook fork predicate (is_in_bad_spot forker prune + skip pawn victims +
    # hanging-victim not-an-attacker clause + scan all pov moves except the last)
    # correctly fires as TP.
    ("6k1/5p1p/R3b1p1/8/8/5PP1/1r2BK1P/8 b - - 0 28", "b2e2 f2e2 e6c4 e2f2 c4a6", "fork"),
    (
        "r2r2k1/p1p5/8/4p1Np/1P3p1P/1R3P2/P5P1/2Bq2QK b - - 0 25",
        "d1g1 h1g1 d8d1 g1f2 d1c1",
        "fork",
    ),
    ("8/6pk/1p2p2p/4Pn2/1P6/3Q3P/5qP1/5R1K b - - 9 39", "f2f1 d3f1 f5g3 h1g1 g3f1", "fork"),
    (
        "2k3rr/pbppqp2/1p2p3/4b3/1PP1B1pp/P3P3/2QB1PPP/2R2RK1 w - - 1 17",
        "e4b7 c8b7 c2e4 b7b8 e4e5",
        "fork",
    ),
    (
        "4r1k1/pBp2ppp/8/2b5/3n4/3P4/PPP3Pn/R1BKR3 b - - 1 18",
        "e8e1 d1e1 d4c2 e1d2 c2a1",
        "fork",
    ),
    (
        "2r3k1/pRr4p/6p1/5pQ1/4pP2/8/q4P1P/5R1K w - - 4 33",
        "b7c7 c8c7 g5d8 g8g7 d8c7",
        "fork",
    ),
    ("8/1p2p2p/3q2pk/8/3PpQ2/6nP/PP4P1/5RK1 b - - 6 32", "d6f4 f1f4 g3e2 g1f2 e2f4", "fork"),
    (
        "3R4/1r1P2k1/5p1p/3n1Pp1/8/8/5K1P/8 w - - 1 51",
        "d8g8 g7g8 d7d8q g8g7 d8d5",
        "fork",
    ),
    (
        "4r3/kp3p2/p1r4p/P1bp2p1/5nP1/1Q3P2/7P/2R2B1K w - - 3 39",
        "c1c5 c6c5 b3b6 a7a8 b6c5",
        "fork",
    ),
    (
        "5r2/5Pkp/5qp1/4N3/1P3Q2/7P/6PK/8 w - - 1 51",
        "f4f6 g7f6 e5d7 f6f7 d7f8",
        "fork",
    ),
    (
        "r3r1k1/1q3pb1/1p1p2p1/pP4Np/2PpbP2/P5P1/3B2BP/R1R2Q1K b - - 4 23",
        "e4g2 f1g2 b7g2 h1g2 e8e2",
        "fork",
    ),
    (
        "8/2p5/3p2k1/1b1P3p/p2qQ2P/6P1/PP6/1K2R3 b - - 3 36",
        "d4e4 e1e4 b5d3 b1a1 d3e4",
        "fork",
    ),
    (
        # Reclassified in Phase 131 Plan 02: the new strict cook discovered-attack
        # predicate (prev.from_square in between) no longer fires here; capturing-defender
        # wins dispatch at depth 4. The previous "discovered-attack" label was from the
        # old broad sub-case-2 predicate.
        "r1b1r1k1/ppp2ppp/2np4/2b1P1N1/2B2B2/2P4P/PP4PR/R3K3 b Q - 1 1",
        "c6e5 c4b3 h7h6 e1c1 h6g5 f4g5 c8f5 g2g4 f5e6 h2h1 e6b3 a2b3",
        "capturing-defender",
    ),
    (
        # Not a fork: reclassified in Phase 131 Plan 02 to "clearance" (clearance fires
        # earlier at depth 4 than the fork in this position with the new cook predicate)
        "r3r1k1/ppp2ppp/2npb3/2b1P1N1/2B2B2/1PP4P/P5PR/R3K3 b Q - 0 1",
        "e6c4 b3c4 c6e5 e1c1 e5c4 g5f3 e8e4 g2g3 c5e3 f4e3 e4e3 f3d4",
        "clearance",
    ),
    (
        # Not a fork: returns hanging-piece (hanging-piece fires at depth 0 before fork)
        "r3r1k1/ppp2ppp/8/4N3/7R/1P4b1/P1P1QnK1/q7 b - - 1 1",
        "g3h4 e2f2 h4f2 e5f3 e8e2 b3b4 f2h4 g2h3 a1h1 f3h2 e2g2 h3h4",
        "hanging-piece",
    ),
]

_HANGING_PIECE_FIXTURES: list[tuple[str, str, TacticMotif]] = [
    (
        "6k1/pp1N2p1/4p3/1q1p1R1p/2p5/8/P1P1Q1PP/6K1 b - - 0 1",
        "b5d7 f5f1 h5h4 e2e5 a7a6 e5b8 g8h7 b8f8 h7g6 h2h3 b7b5 f1f4",
        "hanging-piece",
    ),
    (
        "r1bqk2r/1pp2pp1/p1n1p1Bp/3pP3/3P4/P1P2N2/2P2PPP/R1BQ1RK1 b kq - 0 1",
        "f7g6 d1d3",
        "hanging-piece",
    ),
    (
        "8/6p1/5k2/2p5/4rK2/P1P5/1P6/8 w - - 0 2",
        "f4e4 f6e6 c3c4 e6f6 b2b3 f6e6 e4f4 e6f6 a3a4 f6e6 f4g5 e6e5",
        "hanging-piece",
    ),
    (
        "2rr2k1/5pp1/3Rpnb1/2p4p/PpP4B/1B5P/1P3PP1/4R1K1 b - - 1 1",
        "d8d6 h4g5 g8h8 e1a1 d6a6 g5f4 g6e4 a4a5 e4c6 b3d1 h5h4 b2b3",
        "hanging-piece",
    ),
    (
        "5k2/pq2Npp1/2B1p2p/8/1P6/4r2P/3B1PP1/3R2K1 b - - 1 1",
        "b7e7 d2e3 e7b4 d1d8 f8e7 d8d7 e7f8 d7a7 f7f5 a7a8 f8e7 a8a4",
        "hanging-piece",
    ),
    ("3qr1k1/5ppp/5R2/1Q2n3/3p4/8/PPPN2PP/R6K b - - 0 1", "g7f6 a1f1", "hanging-piece"),
    (
        "3k1r2/p7/1pp5/5N1b/6n1/6BB/PPPK4/8 b - - 1 1",
        "f8f5 h3g2 d8d7 g2e4 f5f8 b2b4 g4f2 e4h7 d7c8 g3e5 h5g4 e5g7",
        "hanging-piece",
    ),
    (
        "r1b1kbnr/p2p1ppp/1p2pqn1/1Pp5/4PP2/P2P1NP1/2P4P/RNBQKB1R b KQkq - 0 1",
        "f6a1 c1d2 a1f6 f1g2 d7d6 c2c4 f6d8 e1g1 a8b8 b1c3 h7h5 f3g5",
        "hanging-piece",
    ),
    ("r3kbnr/p4ppp/1p3qn1/1Ppp4/5Pb1/P2PNNP1/2P4P/2BQKB1R w Kkq - 1 2", "e3g4", "hanging-piece"),
    (
        "8/p2r4/1p6/1P3B1P/1kP4K/6P1/8/8 w - - 1 2",
        "f5d7 b4c5 h5h6 c5d6 d7h3 d6c5 h3f5 c5d4 h6h7 d4c4 h7h8q c4b4",
        "hanging-piece",
    ),
    (
        "r3k1nr/pppq2pp/1Nnp4/4p3/1PB1P1b1/P1PP1N2/6PP/R1BQK2R b KQkq - 0 1",
        "a7b6 e1g1",
        "hanging-piece",
    ),
    ("r4rk1/6pp/1p2pb2/p7/3P4/1P2pbN1/P4PPP/2R1R1K1 w - - 0 2", "g2f3", "hanging-piece"),
    ("rn1qkbnr/pp2pppp/2p5/8/3P4/3b2N1/PPP2PPP/R1BQK1NR w KQkq - 0 2", "d1d3", "hanging-piece"),
]

_PIN_FIXTURES: list[tuple[str, str, TacticMotif]] = [
    # Rebuilt in Phase 131 Plan 02 from CC0 lichess puzzle fixtures where the new
    # cook pin predicate (pin_prevents_attack + pin_prevents_escape two-sub-test port)
    # correctly fires as TP.
    ("7k/1pQ3b1/p2p1np1/3Pp2p/4P2q/1P4NP/P4BPK/8 b - - 3 33", "f6g4 h2g1 g4f2 g1f2 h4f4", "pin"),
    (
        "2q1r1k1/3r2pp/p2P4/8/8/1PQ5/P1K5/3R2R1 b - - 0 43",
        "e8e2 d1d2 e2d2 c2d2 d7d6",
        "pin",
    ),
    (
        "8/1p6/p3pk2/2q5/3Q3p/1P4nP/P4PP1/3R2K1 b - - 6 45",
        "c5d4 d1d4 g3e2 g1f1 e2d4",
        "pin",
    ),
    (
        "r4k1r/1b3p2/pN1q2pp/1p2p3/3BP3/2PQ4/PP4PP/R6K w - - 0 31",
        "d4c5 d6c5 b6d7 f8g7 d7c5",
        "pin",
    ),
    ("5R2/4Q1pk/7p/pp4r1/2p5/2P2PPR/r1q2PK1/8 w - - 2 37", "h3h6 h7h6 f8h8", "pin"),
    (
        "r4rk1/p1b3pp/5n2/2p5/P2p2q1/3P4/2P2PBN/R1BQR1K1 b - - 4 22",
        "c7h2 g1h2 g4h4 h2g1 f6g4",
        "pin",
    ),
    (
        "R3rk2/5b2/8/5RP1/4n1K1/8/8/8 w - - 7 47",
        "a8e8 f8e8 f5e5 e8d7 e5e4",
        "pin",
    ),
    (
        "1k5r/ppq5/2p5/4n3/5QBN/3r2PK/PP3RP1/4R3 b - - 1 24",
        "h8h4 h3h4 e5g6 h4g5 g6f4 e1e8 d3d8 e8d8 c7d8",
        "pin",
    ),
    (
        "4r1k1/5pbp/p5p1/2N5/5Pb1/1P1rB1P1/P4K1P/2R1R3 b - - 4 29",
        "d3e3 e1e3 g7d4 c1c4 d4e3",
        "pin",
    ),
    (
        "6rk/pp2pq2/2p4p/5P1b/2PP1Q2/1P2P1R1/P2r3P/2R4K w - - 2 27",
        "f4h6 f7h7 g3g8 h8g8 c1g1 g8f7 h6h7",
        "pin",
    ),
    (
        "2k1r3/1p4bp/p2B4/2P1Nbp1/3R1P2/1P6/P6P/2K5 b - - 0 28",
        "g5f4 d4f4 g7h6 e5f7 h6f4",
        "pin",
    ),
    (
        "8/pkp5/1pbbp1r1/5P1p/8/1P2R1BP/2PR2PK/8 b - - 0 31",
        "g6g3 e3g3 h5h4 d2d6 h4g3 h2g3 c7d6",
        "pin",
    ),
    (
        # Not a pin: hanging-piece fires at depth 0 with priority
        "r1b1r1k1/pp1B1ppp/3bp3/2pP4/8/5N2/PqP2PPP/RN1Q1RK1 b - - 0 1",
        "c8d7 b1d2 e6d5 a1b1 b2f6 b1b7 d7c6 b7b1 h7h5 h2h4 f6g6 f1e1",
        "hanging-piece",
    ),
    (
        # Not a pin: clearance fires instead
        "r1bqk1nr/pppp1ppp/2nb4/8/4Pp2/2NP4/PPP1N1PP/R1BQKB1R b KQkq - 1 1",
        "d8h4 e1d2 g8f6 d1e1 h4h5 a2a4 e8g8 h2h3 f8e8 a4a5 d6b4 e2f4",
        "clearance",
    ),
]

_SKEWER_FIXTURES: list[tuple[str, str, TacticMotif]] = [
    # Rebuilt for cook's relational predicate (plan 02): scan pov moves from 2nd+;
    # capture with ray piece; op.from_square in between(from, to); is_in_bad_spot accept.
    # All 12 entries are TP fixtures from the CC0 precision harness (plan 02 measured).
    (
        "6k1/r7/1r1RK2R/8/8/6P1/7P/8 b - - 12 36",
        "b6d6 e6d6 a7a6 d6d5 a6h6",
        "skewer",
    ),
    (
        "4r3/7p/8/1R2r3/1Kpk4/P1R4P/1P6/8 b - - 0 43",
        "e5b5 b4b5 e8b8 b5c6 b8b2",
        "skewer",
    ),
    (
        "8/1pb1nk1p/5pp1/2Pp4/1P3P2/7P/r2BB1P1/2R1K3 b - - 0 29",
        "a2d2 e1d2 c7f4 d2d1 f4c1",
        "skewer",
    ),
    (
        # Replaced in Phase 131 Plan 02: the 8/1q1krR2... position now returns "pin"
        # because the new cook pin sub-test fires at an earlier depth than the skewer.
        "7r/pp1q2k1/2pb2p1/5pN1/2BP1P2/4r3/PPP5/2KR3Q w - - 3 24",
        "h1h8 g7h8 d1h1 h8g7 h1h7 g7f6 h7d7",
        "skewer",
    ),
    (
        "4rk1r/ppR4p/2pp2p1/2n5/8/2P1R3/P4PPP/6K1 w - - 2 29",
        "e3e8 f8e8 c7c8 e8f7 c8h8",
        "skewer",
    ),
    (
        "7r/7p/p1p1k3/N3n1R1/1P6/P4p2/4bK1P/4B3 w - - 0 34",
        "g5e5 e6e5 e1c3 e5d5 c3h8",
        "skewer",
    ),
    (
        "r4rk1/1Q2nppp/8/p7/2Bp4/P2P1PPq/1P5P/R4RK1 b - - 0 20",
        "a8b8 b7e7 b8b2 f1f2 b2f2 g1f2 h3h2 f2f1 h2h1",
        "skewer",
    ),
    (
        "4r3/2kb4/4pp2/1pN1p3/1P2P3/3B2pP/2PKR1Pr/8 w - - 13 44",
        "c5d7 c7d7 d3b5 d7e7 b5e8",
        "skewer",
    ),
    (
        "8/5k2/4p1p1/3b1p2/1p1K4/2nB1P2/2PB2P1/1rR5 w - - 6 38",
        "c1b1 c3b1 d2b4",
        "skewer",
    ),
    (
        "6k1/5p1p/p5p1/3bP3/1p6/1Pq2N1P/P1PQ2P1/1K6 b - - 1 32",
        "c3d2 f3d2 d5g2",
        "skewer",
    ),
    (
        "2k1r3/1p1r2p1/1pn4p/8/B1b1p3/2P4P/5PPN/R3K2R w KQ - 2 27",
        "a4c6 b7c6 a1a8 c8c7 a8e8",
        "skewer",
    ),
    (
        "3r2k1/p2P1pp1/7p/8/R3P3/P7/r1P4P/2KR4 b - - 2 30",
        "a2a1 c1b2 a1d1",
        "skewer",
    ),
]

_DISCOVERED_ATTACK_FIXTURES: list[tuple[str, str, TacticMotif]] = [
    # Rebuilt for cook's relational predicate (plan 02): scan pov moves from 2nd+;
    # require prev.from_square in between(from, capture_sq); recapture short-circuit.
    # All 12 entries are TP fixtures from the CC0 precision harness (plan 02 measured).
    (
        "3r4/r2N1k2/3R2pp/1pP2p2/8/P7/1P4PP/6K1 w - - 12 35",
        "d7e5 f7e8 d6d8 e8d8 e5c6 d8c8 c6a7",
        "discovered-attack",
    ),
    (
        "8/pb3k1p/1p2pb2/8/3BPP2/8/P4KBP/8 w - - 1 28",
        "d4f6 f7f6 e4e5 f6f5 g2b7",
        "discovered-attack",
    ),
    (
        "2rqr1kb/pp3p2/4b1pB/3np1P1/3nN3/5P2/PP5Q/1K1R1BNR w - - 1 21",
        "h6f8 g8f8 h2h8 f8e7 h8e5 d8c7 e5c7 d5c7 d1d4",
        "discovered-attack",
    ),
    (
        "r2qkb1r/pppbnppp/2n5/1B6/3N4/8/PPP2PPP/RNBQR1K1 b kq - 5 9",
        "c6d4 d1d4 d7b5",
        "discovered-attack",
    ),
    (
        "2r1k2r/1q1p1pbp/1p2p1p1/p1n2n2/2PN4/1PB1P1P1/P1Q2P1P/RN2KR2 w Qk - 0 17",
        "d4f5 g6f5 c3g7",
        "discovered-attack",
    ),
    (
        "r1bqk2r/pp2bppp/2n2n2/2p3B1/3pN3/3P2P1/PP2PPBP/2RQK1NR b Kkq - 1 9",
        "f6e4 g2e4 e7g5",
        "discovered-attack",
    ),
    (
        "r2q1r2/1b1n1pkp/p3p1p1/1ppnP3/4B3/P1N2N1P/1PP2PP1/R1Q2RK1 b - - 1 15",
        "d5c3 b2c3 b7e4",
        "discovered-attack",
    ),
    (
        "2r1q1k1/pp1b1p1p/3B2p1/4n1P1/8/3Q2P1/P3P1B1/3R2K1 w - - 0 26",
        "d6e5 e8e5 d3d7",
        "discovered-attack",
    ),
    (
        "8/2r3pk/1p4n1/1Pb3Pp/p4P2/P3N1P1/1BP4K/4R3 b - - 0 33",
        "c5e3 e1e3 c7c2 h2h3 c2b2",
        "discovered-attack",
    ),
    (
        "r5k1/ppqn3p/2p2np1/3pNb2/8/3P1N1P/P1P2P2/Q3RBK1 w - - 2 21",
        "e5d7 f5d7 a1f6",
        "discovered-attack",
    ),
    (
        "r2qkb1r/pp1b1ppp/2n2p2/1BP5/3N4/8/PPP2PPP/R1BQ1RK1 b kq - 2 11",
        "c6d4 d1d4 d7b5 f1e1 f8e7",
        "discovered-attack",
    ),
    (
        "r4rk1/1bq1bppp/p1np1n2/1p6/3NP3/6N1/PPB2PPP/R1BQR1K1 b - - 0 16",
        "c6d4 d1d4 c7c2",
        "discovered-attack",
    ),
]

_BACK_RANK_MATE_FIXTURES: list[tuple[str, str, TacticMotif]] = [
    # Phase 131-03: all 13 replaced with CC0 TPs from the precision harness
    # (old fixtures passed the broken detector but not cook's own-blocker gate).
    (
        "4R1rk/p1p2prp/3p1Q2/3P4/2P5/1P4P1/q4P1P/4b1K1 w - - 0 27",
        "e8g8 h8g8 f6d8",
        "back-rank-mate",
    ),
    (
        "3R2rk/1p3prp/p3p3/5b2/7q/P1Q5/1PP5/1K1R4 w - - 4 34",
        "d8g8 h8g8 c3c8 h4d8 c8d8",
        "back-rank-mate",
    ),
    ("8/1R4bk/r2p2p1/3Pp2p/1P2P3/5R2/6PP/7K b - - 0 41", "a6a1 f3f1 a1f1", "back-rank-mate"),
    ("3r2k1/ppp2ppp/8/3r4/8/2PbR3/PP1K1PPP/4R3 w - - 0 19", "e3e8 d8e8 e1e8", "back-rank-mate"),
    (
        "r5k1/p4pp1/1p6/1Pp1BP2/P1Pp2Q1/3Pq2R/4r1PP/1R5K b - - 0 32",
        "e2e1 b1e1 e3e1",
        "back-rank-mate",
    ),
    (
        "1n3r1k/rp2R2n/p2p2BQ/2pN1q2/8/8/PPP2PPP/R5K1 b - - 1 21",
        "f5f2 g1h1 f2f1 a1f1 f8f1",
        "back-rank-mate",
    ),
    ("4r2k/5R1p/pq1p1Np1/1p6/8/P2Qr3/BP4PP/7K b - - 2 31", "e3e1 d3f1 e1f1", "back-rank-mate"),
    ("1B4k1/7p/4p1p1/2r5/p2p1R2/Pb1P4/6PP/2R4K b - - 0 35", "c5c1 f4f1 c1f1", "back-rank-mate"),
    (
        "r5k1/pp3ppp/2b1p3/4P3/6q1/3r4/5QPP/B4RK1 w - - 0 27",
        "f2f7 g8h8 f7f8 a8f8 f1f8",
        "back-rank-mate",
    ),
    (
        "2r3k1/1p3ppp/p1r5/3p1p1P/P2P2P1/2P5/1P2R3/4R1K1 w - - 0 27",
        "e2e8 c8e8 e1e8",
        "back-rank-mate",
    ),
    (
        "r1b1r1k1/p1p2ppp/8/2p1q3/4P3/2p2Q2/PPP3PP/R1B2RK1 w - - 0 16",
        "f3f7 g8h8 f7f8 e8f8 f1f8",
        "back-rank-mate",
    ),
    (
        "3r2k1/p3Qppp/4p3/8/8/P2qP3/6PP/5RK1 w - - 3 30",
        "e7f7 g8h8 f7f8 d8f8 f1f8",
        "back-rank-mate",
    ),
    ("3r2k1/6pp/1p6/2b1B3/P1P5/1R6/5RPP/7K b - - 0 35", "d8d1 f2f1 d1f1", "back-rank-mate"),
]

_MATE_FIXTURES: list[tuple[str, str, TacticMotif]] = [
    ("6k1/pp4p1/4R3/3p3p/2p5/8/PqP1QKPP/8 w - - 1 2", "e6e8 g8f7 e2e6", "mate"),
    (
        "3r4/pb3pk1/1p6/2p1R1P1/8/1Pp1K1P1/P2r1P1N/R7 b - - 1 1",
        "d8d3 e3f4 d2f2 h2f3 d3f3 f4g4 b7c8 e5e6 c8e6 g4h4 f2h2",
        "mate",
    ),
    (
        "8/8/2nkr3/p5P1/Pp6/1P2Q2P/1P6/2K1R3 w - - 0 2",
        "e3e6 d6c7 e6f7 c7b6 e1e6 b6c5 f7d7 c5b6 e6c6",
        "mate",
    ),
    (
        "rn3rk1/1ppRp2p/6p1/p7/5PP1/2P1BQ1P/P1P5/2K4R w - - 1 2",
        "f3d5 g8h8 e3d4 f8f6 d7d8 h8g7 d8g8 g7h6 d5g5",
        "mate",
    ),
    (
        "8/6kp/p1r3p1/4P3/1qpQ2B1/7P/1P6/5RRK w - - 0 2",
        "e5e6 g7h6 d4f4 h6g7 f4f6 g7g8 f6d8 g8g7 f1f7 g7h6 d8h4",
        "mate",
    ),
    (
        "k4r2/8/p1RQ4/1p2p2p/1P6/3P2P1/q4P1P/6K1 w - - 1 2",
        "d6f8 a8b7 f8c8 b7a7 c6c7 a7b6 c7b7",
        "mate",
    ),
    (
        "6k1/3N1p1p/r1p1q1p1/7b/3p1n2/3P2Q1/2P2PPP/4RK2 b - - 1 1",
        "e6e1 f1e1 a6a1 e1d2 a1d1",
        "mate",
    ),
    ("6k1/3N1p1p/r1p1q1p1/7b/3p4/3P2Q1/2P1nPPP/4RK2 w - - 1 2", "g3b8 e6e8 b8e8 g8g7 e8f8", "mate"),
    (
        "1Q6/5pkp/r1p1q1p1/2N4b/3p4/3P2P1/2P2PP1/4RK2 b - - 0 1",
        "e6e1 f1e1 a6a1 b8b1 a1b1 e1d2 b1d1",
        "mate",
    ),
    ("6k1/3b2pp/p2Qp3/3p1pK1/3q4/1P5P/P7/8 b - - 1 1", "h7h6 g5h5 d7e8", "mate"),
    ("4r3/R7/2pk4/p6p/2PK3P/4r3/P7/6R1 b - - 1 1", "c6c5", "mate"),
    (
        "r3kb1r/p4ppp/2p1pq2/3p4/6P1/2NQBn1P/PPP2PK1/R4R2 b kq - 1 1",
        "f3h4 g2g3 f6f3 g3h4 f8e7 e3g5 e7g5 h4h5 f3f6 d3d5 f6h6",
        "mate",
    ),
    (
        "2r2rk1/5ppp/Q3p1n1/3p4/2P4q/1B2P1b1/1B4K1/R4R2 b - - 1 1",
        "h4h2 g2f3 g6h4 f3g4 f7f5 g4g5 h4f3 f1f3 h2h6",
        "mate",
    ),
]

_DEFLECTION_FIXTURES: list[tuple[str, str, TacticMotif]] = [
    (
        "r1b1r1k1/pp3p2/n4P1p/3B2p1/P2PN2B/1P6/3K4/6R1 b - - 1 1",
        "a6c7 h4g5 c7d5 g5e3 g8h7 g1g7 h7h8 e4d6 c8e6 e3h6 e8g8 d6f7",
        "deflection",
    ),
    (
        "rn2kb1r/pp3ppp/1qp5/8/3pn3/7B/PPP3PP/RNBQ1R1K b kq - 1 1",
        "e4f6 c1h6 b8d7 d1e1 e8d8 h6f4 b6b5 b1d2 g7g5 h3d7 f6d7 f4g3",
        "deflection",
    ),
    (
        "rnb1kbnr/p1p1pppp/1p6/3q4/8/5N2/PPPP1PPP/RNBQKB1R w KQkq - 0 2",
        "b1c3 d5e6 f1e2 c8a6 e1g1 a6e2 c3e2 g7g6 d2d4 f8g7 c1f4 e6d7",
        "clearance",
    ),
    (
        "8/5p1k/5qpp/4p3/8/4Q2P/5PPK/8 b - - 1 1",
        "f6f4 h2h1 f4e3 f2e3 h7g7 h1g1 g7f6 g1f2 f6g5 g2g3 g5f5 f2f3",
        "deflection",
    ),
    (
        "r7/2pkb2p/p5pn/5N2/8/6P1/PPP4P/2KR4 b - - 0 1",
        "d7e8 f5e7 e8e7 d1d4 h6f5 d4a4 e7d7 b2b3 c7c5 a4e4 d7d6 e4a4",
        "deflection",
    ),
    (
        "2r1k1nr/p4ppp/b1p1p3/3pP3/3N4/1NP5/PP3P1P/R3K2R w KQk - 1 2",
        "b3c5 g8e7 c5a6 c6c5 d4b3 c5c4 b3c5 e7g6 e1c1 e8e7 h1e1 g6h4",
        "deflection",
    ),
    (
        "5rk1/pQN1bpp1/7p/2P5/1P6/4q3/P5P1/3R3K w - - 1 2",
        "c7d5 e3e2 d5e7 g8h7 b7d7 f8e8 e7f5 e8e4 c5c6 e2f2 c6c7 e4g4",
        "deflection",
    ),
    (
        "3rq1k1/5rp1/p5Rp/1p5Q/3P4/N1P1b3/PP4P1/R6K b - - 1 1",
        "f7f6 a1e1 f6g6 a3c2 g6e6 h5h3 d8d5 g2g4 d5g5 h3f3 h6h5 e1e3",
        "deflection",
    ),
    (
        "r2q1r1k/ppp2pp1/2np3p/5Pb1/2B1P1Q1/2NP3P/PPP3P1/R3K2R b KQ - 1 1",
        "c6d4 c4b3 a7a5 e1g1 c7c6 g1h1 g5f6 g4h5 d8e7 a2a4 d4b3 c2b3",
        "clearance",
    ),
    (
        "r2q1r1k/1p3pp1/p1pp3p/5P2/4P1Q1/1PNPbR1P/1PP3P1/R6K b - - 1 1",
        "e3d4 a1f1 d4c3 b2c3 f7f6 g4g6 a6a5 g2g4 d8e8 h3h4 b7b5 h1g2",
        "deflection",
    ),
    (
        "r1b1k1nr/pppp1ppp/1bn2q2/8/3PPB2/2N2N2/PPP3PP/R2QKB1R w KQkq - 1 2",
        "c3d5 f6g6 f1d3 d7d6 e1g1 g8e7 d1d2 c8g4 d5b6 a7b6 e4e5 g6h5",
        "clearance",
    ),
    (
        # Reclassified in Phase 131 Plan 02: the new cook skewer predicate (op.from in
        # between + is_in_bad_spot) now fires here at depth 4 with higher priority than
        # deflection. The position has a genuine skewer by cook's definition.
        "8/p5pp/P7/1Pp3P1/2P4P/r3k3/2K5/6R1 w - - 1 2",
        "g1g3 e3f4 g3a3 h7h6 b5b6 a7b6 a6a7 b6b5 a7a8q b5c4 a8f3 f4e5",
        "skewer",
    ),
    (
        "5rk1/pp3ppp/r3p3/3pP1q1/4n3/P3P2P/1PQ2PP1/RN3RK1 w - - 1 2",
        "b1c3 g5e5 c3e4 d5e4 a1d1 a6c6 c2a4 a7a6 a4b4 b7b5 d1d4 e5c7",
        "deflection",
    ),
]

_ATTRACTION_FIXTURES: list[tuple[str, str, TacticMotif]] = [
    (
        "6R1/kp6/B7/Q1p4p/3q4/P2r1p2/1PP2K1P/8 w - - 0 2",
        "f2f1 d3d1 a5e1 d1e1 f1e1 d4e3 e1d1 a7a6 g8a8 a6b6 c2c3 e3e2",
        "attraction",
    ),
    (
        "r2qk3/p1p1bp2/2pn4/3pPp1r/5Qpp/2PP4/PP4PP/RNBR2K1 w q - 1 2",
        "e5d6 e7d6 f4f1 a8b8 b2b3 e8f8 d1e1 c6c5 c1f4 d8f6 f1f2 f8g7",
        "attraction",
    ),
    (
        "4r2k/7p/8/2P4P/1p1b4/1P2p2q/P5R1/5QK1 w - - 1 2",
        "f1e2 h3f5 g2g3 f5f2 e2f2 e3f2 g1g2 e8e1 g3f3 e1g1 g2h3 f2f1q",
        "clearance",
    ),
    (
        "b3k1b1/7p/pp1p1pp1/2pPb3/P1P3b1/2NN1NP1/2NK1P2/7N w - - 1 2",
        "d3e5 f6e5 f3g5 h7h6 c2e3 g4d7 g5e4 e8e7 g3g4 g8f7 g4g5 h6h5",
        "attraction",
    ),
    (
        "8/8/7R/4K3/p7/P6p/7k/8 b - - 1 1",
        "h2g2 e5d4 h3h2 d4c4 h2h1r h6h1 g2h1 c4b4 h1g2 b4a4 g2f3 a4b5",
        "attraction",
    ),
    (
        "2k4r/1pbq2pp/p3p3/8/P1p1PNn1/R4Q2/1P1P2PP/2R3K1 b - - 1 1",
        "c7b6 g1h1 g4f2 f3f2 b6f2 c1c4 c8b8 a3d3 d7e7 d3f3 f2b6 h2h3",
        "attraction",
    ),
    (
        "2r5/4Q2n/p5pk/1p1p4/2r5/2P5/P4PP1/3R2K1 b - - 1 1",
        "c4e4 e7d6 c8e8 d1d5 e8e6 d6h2 h6g7 d5d7 e6e7 d7e7 e4e7 h2d6",
        "attraction",
    ),
    (
        "3rr1k1/ppp2pp1/1bn2q1p/3p1b2/1P2p3/PNPP1PPP/4N1B1/R2QK2R w KQ - 0 2",
        "f3e4 d5e4 d3d4 f5e6 h1f1 f6e7 f1f4 e6d5 a1b1 e7e6 h3h4 g7g5",
        "attraction",
    ),
    (
        "1qr4r/1p1knp2/pB2p2p/3pb1pP/8/P2B1Q2/1P3PP1/2R1R1K1 b - - 1 1",
        "e5h2 g1f1 b8f4 f3f4 h2f4 c1d1 e7c6 d3e4 f4e5 g2g3 d7e7 e4b1",
        "attraction",
    ),
    (
        "2r2rk1/ppp3pp/2np4/3Np3/1P2P1b1/P4N2/2P2PPP/R4RK1 b - - 0 1",
        "g4f3 g2f3 f8f7 c2c3 c8f8 b4b5 c6d8 a3a4 d8e6 a4a5 e6g5 f3f4",
        "attraction",
    ),
    (
        "r1bq1rk1/pppp1ppp/2n4n/2b1P1N1/2Bp4/8/PPP2PPP/RNBQ1RK1 b - - 0 1",
        "c6e5 c4d3 f7f5 f1e1 d7d6 d1h5 d8f6 c1f4 f6g6 h5g6 e5g6 f4d2",
        "clearance",
    ),
    (
        "rq3b1r/p1p1kbp1/2p2n1p/3p4/3P1P2/2NQPN2/P1P3PP/RR4K1 b - - 1 1",
        "b8c8 f3e5 f7e8 c3e2 e7d8 b1b2 a8b8 b2b8 c8b8 c2c4 f8d6 a1b1",
        "attraction",
    ),
    (
        "2r1rk2/pp2q1bQ/3p2p1/3P1p2/2P1p3/1P4N1/P4PPP/R3R1K1 b - - 1 1",
        "g7a1 h7g6 e7f6 g6f6 a1f6 g3f5 f6c3 e1e2 c3b4 a2a4 f8f7 g2g4",
        "attraction",
    ),
]

_CLEARANCE_FIXTURES: list[tuple[str, str, TacticMotif]] = [
    (
        "3r2k1/p1br1pp1/bpp2q1p/2pPpN2/2P1P3/1P3N1P/P4PP1/R2Q1RK1 w - - 1 2",
        "f5e3 f6f4 f3d2 c6d5 e3d5 f4h4 d1f3 a6b7 f1d1 d8f8 a1c1 f7f5",
        "clearance",
    ),
    (
        "r5r1/pppqkpB1/3p1N1p/4p3/3nP2b/3PKB2/PPP4P/R2Q3R w - - 1 2",
        "f6d7 g8g7 d7e5 d6e5 c2c3 h4g5 e3f2 d4e6 h2h4 g5f4 h1g1 a8g8",
        "clearance",
    ),
    (
        "rn2kb1r/ppp2ppp/4p3/3p4/3PNB1q/7N/PPP1P2P/R2QK2R w KQkq - 1 2",
        "e4f2 h4e7 d1d3 b8c6 e1c1 f7f6 h3g1 g7g5 f4g3 e8c8 h2h4 g5g4",
        "clearance",
    ),
    (
        "r1bqk1nr/pppp1p1p/2nb4/6p1/4Pp2/2NP2P1/PPP1N2P/R1BQKB1R b KQkq - 0 1",
        "f4f3 e2g1 g5g4 c1e3 h7h5 d1d2 d8f6 e1c1 d6b4 h2h3 g8e7 d3d4",
        "clearance",
    ),
    (
        "r1bqk3/p2pnp1p/1p1p1n2/8/4P1r1/3P1pP1/PPP5/R1BQKBNR w KQq - 0 2",
        "d1f3 g4g6 c1f4 c8b7 e1c1 b6b5 c1b1 a8c8 g1e2 d8b6 f1g2 b5b4",
        "clearance",
    ),
    (
        "r2qk3/pb1pnprp/1p1p1n2/8/4P1P1/3P1Q1B/PPP5/R1B1K1NR b KQq - 0 1",
        "e7c6 g4g5 f6g8 g1e2 a8c8 e1d1 c6e5 f3f2 d8c7 e2d4 b7a6 c1e3",
        "clearance",
    ),
    (
        "r1bq1rk1/2p2ppp/1pn1p3/p1PpP3/3P4/P4NP1/2P2P1P/R2QKB1R b KQ - 0 1",
        "b6c5 c2c3 c5c4 a3a4 c6b8 f1g2 c8d7 e1g1 c7c5 d4c5 d8e7 f3d4",
        "clearance",
    ),
    (
        "1rb2rk1/2p3pp/2B1pq2/p1Pp4/4p3/P1P2NP1/5P1P/1R1QK2R w K - 1 2",
        "b1b8 f6c3 f3d2 c3c5 e1g1 c5c6 d1b3 h7h6 b3e3 c6d6 f1c1 c7c5",
        "hanging-piece",
    ),
    (
        "r3k2r/pp1b2pp/2n1pp2/2PpP3/5Bn1/5N2/PPP2PPP/RN2K2R b KQkq - 1 1",
        "f6e5 h2h3 e8g8 f4g3 e5e4 f3d2 g4h6 g3d6 f8f6 e1g1 h6f5 c2c4",
        "clearance",
    ),
    (
        "rnbqkbnr/pp2pppp/2p5/3p3Q/4P3/2N5/PPPP1PPP/R1B1KBNR b KQkq - 1 1",
        "g8f6 h5e2 e7e5 a2a3 f8d6 d2d3 e8g8 g2g3 f8e8 f1h3 b8d7 g1f3",
        "clearance",
    ),
    (
        "5r1r/1kp4p/p2pQ3/1p2p3/1P6/q5P1/2PR1P1P/3R2K1 w - - 0 2",
        "c2c4 a3b3 d1c1 b7b8 e6d7 b3f3 c4b5 f8f7 d7h3 e5e4 c1e1 h8e8",
        "clearance",
    ),
    (
        "r2r2k1/6p1/3p2qp/2p5/4bpN1/P6P/1PP2PP1/2RQ1RK1 w - - 1 2",
        "f2f3 e4c6 d1d2 d8b8 c2c3 g8h7 h3h4 b8b6 c1a1 c5c4 a1e1 a8b8",
        "clearance",
    ),
    (
        "1k6/p1p2pqp/Bp1p4/8/4P3/2P5/P1P1R3/4KR2 w - - 1 2",
        "e2e3 f7f6 f1f5 c7c6 a2a4 b8c7 a6e2 a7a6 e3f3 g7g6 e1d2 b6b5",
        "clearance",
    ),
]

_X_RAY_FIXTURES: list[tuple[str, str, TacticMotif]] = [
    (
        "r1br2k1/p1b2pp1/1pp2q1p/2pPp3/4P3/5NNP/PPP2PP1/R2Q1RK1 w - - 0 2",
        "c2c4 c6d5 c4d5 c8d7 a2a4 a7a6 b2b3 b6b5 d1e2 c7d6 f1b1 d8c8",
        "x-ray",
    ),
    (
        "8/7k/3Kp2p/3n2p1/1p2r3/1Rb5/8/8 b - - 1 1",
        "e4e1 b3b1 e1b1 d6e6 d5f6 e6f5 b1f1 f5e6 h7g6 e6e7 h6h5 e7e6",
        "x-ray",
    ),
    (
        "3n4/8/4P3/1Pk2K2/6P1/8/8/8 b - - 1 1",
        "c5d6 e6e7 d6e7 f5g6 d8e6 b5b6 e7d7 g6f5 d7d6 b6b7 e6d4 f5e4",
        "x-ray",
    ),
    (
        "8/4k3/2P4p/1p1pP3/1P3K2/8/7P/8 w - - 1 2",
        "f4e3 d5d4 e3d4 e7f7 c6c7 f7g6 c7c8q g6g5 d4d5 g5f4 e5e6 f4e3",
        "x-ray",
    ),
    (
        "rnbqk1nr/pppp1ppp/8/2b1p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 1 2",
        "f3e5 b8c6 e5c6 d7c6 c2c3 d8e7 d1e2 c5b6 a2a4 a7a5 d2d4 f7f5",
        "x-ray",
    ),
    (
        "2r3k1/ppN2ppp/2np4/4p1B1/P3P1n1/3P1N2/1PP2qPP/R2Q3K w - - 1 2",
        "c7d5 c6b4 d5b4 f2c5 d1e2 g4f2 h1g1 f2h3 g1f1 h3g5 c2c3 g5f3",
        "x-ray",
    ),
    (
        "6k1/p1r2p2/4pQp1/r2pP2p/2qP1R1P/8/5PP1/3R2K1 w - - 0 2",
        "d1b1 a5a1 b1a1 c4c2 g1h1 g8h7 f4f3 c2b2 a1f1 b2c2 f6d8 h7g7",
        "x-ray",
    ),
    (
        "2kr3r/ppp1b1pp/2q1p2n/5pN1/2P2B2/3P4/PP3PPP/R2Q1RK1 b - - 0 1",
        "e6e5 d1e2 e7f6 f4c1 c6d7 d3d4 e5d4 e2d3 d8e8 f1d1 h6g4 g5f3",
        "x-ray",
    ),
    # NOTE: r1bqkb1r position removed (Phase 128.1 Plan 01): after f6e4 b1c3 e4c3,
    # the white queen on d1 has only one escape (e2) where black knight (value 3) is
    # cheaper than the queen (value 9) — trapped-piece (Tier 2) beats x-ray (Tier 3)
    # per D-03. Position reclassified to _TRAPPED_PIECE_FIXTURES.
    # ("r1bqkb1r/pppp1ppp/2n2n2/8/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq - 1 1",
    #  "f6e4 b1c3 e4c3 d2c3 f8c5 b2b4 c5e7 b4b5 c6b8 d1d5 e8g8 f1d3",
    #  "x-ray"),
    (
        "r1b2rk1/pp2b3/2pq1nP1/3p1P2/B2Q4/2N5/PPP2P2/2KR3R w - - 1 2",
        "d4h4 f6h5 h4h5 d6f4 c1b1 g8g7 h5h7 g7f6 h1h6 c8f5 g6g7 f4h6",
        "x-ray",
    ),
    (
        "5k2/p6p/1r2bp2/4p3/KP1p4/5PR1/1P3P1P/7R b - - 1 1",
        "e6c4 b4b5 c4b5 a4b3 b5d3 b3a2 d3e2 f3f4 d4d3 f4e5 d3d2 g3g1",
        "x-ray",
    ),
    (
        "8/8/5K1k/6pr/6R1/8/8/8 w - - 0 2",
        "g4g2 g5g4 g2g4 h5h2 g4g5 h2b2 g5c5 b2b6 f6f7 b6b7 f7f6 b7b4",
        "x-ray",
    ),
]

_INTERMEZZO_FIXTURES: list[tuple[str, str, TacticMotif]] = [
    (
        "r1b2rk1/p3qppp/2p1p3/3pBn2/1PnP1Q2/2P2NP1/4PPBP/R4RK1 b - - 1 1",
        "f7f6 e5b8 e7b7 b8c7 e6e5 c7e5 f6e5 f3e5 f5d6 f4h4 c8e6 e2e3",
        "intermezzo",
    ),
    # NOTE: r1b1k2r position removed (Phase 128.1 Plan 01): at depth 8 the black queen
    # on f6 is trapped by white pawns (all escapes attacked by cheaper pieces) — the new
    # trapped-piece detector (Tier 2) fires before intermezzo (Tier 3) per D-03.
    # Replacement from TRAIN:
    (
        "5rk1/p4p2/1p2bn1p/5Kp1/4P3/1q3NNP/3Q1PP1/7R w - - 2 31",
        "f5f6 f8e8 f3d4 b3a4 d4f5 e6f5 f6f5",
        "hanging-piece",
    ),
    (
        "1q2r1k1/1b4np/p3pbp1/P2p4/8/B3QNP1/5PBP/4R1K1 w - - 1 2",
        "e3b6 b7a8 e1b1 b8c8 h2h4 g7f5 a3b2 f6b2 b6b2 c8d8 b2e5 d5d4",
        "intermezzo",
    ),
    (
        "5r2/6pk/2p5/p4ppP/8/2PB4/PP6/1K2R3 b - - 1 1",
        "h7h6 e1f1 g7g6 h5g6 h6g6 a2a4 g5g4 b2b4 g6g5 b1c2 g4g3 d3e2",
        "intermezzo",
    ),
    (
        "8/1p1r2k1/2p4R/p1P3Pp/1b3N1P/4PK2/8/8 w - - 1 2",
        "f4h5 g7f8 h6h8 f8e7 g5g6 b4c3 g6g7 c3g7 h5g7 d7d5 h4h5 e7f7",
        "intermezzo",
    ),
    (
        "8/6Rp/1r2kp2/p7/1p2P1P1/5K2/P6P/8 b - - 0 1",
        "a5a4 g7a7 b4b3 a2b3 a4b3 a7a1 b3b2 a1b1 e6e5 f3e3 b6b3 e3d2",
        "intermezzo",
    ),
    (
        "8/5pp1/p1p4p/P1Pk4/3P4/3K3P/6P1/8 w - - 0 2",
        "g2g4 g7g6 h3h4 f7f6 h4h5 g6h5 g4h5 d5e6 d3e4 f6f5 e4f4 e6f6",
        "intermezzo",
    ),
    (
        "r1bq1rk1/pp1nbppp/2pp4/4P3/2P1n3/1P3NP1/PB2PPBP/RN1Q1RK1 w - - 1 2",
        "d1c2 f7f5 e5f6 d7f6 b1c3 e4c3 c2c3 a7a5 e2e4 a5a4 a1e1 a4b3",
        "intermezzo",
    ),
    (
        "8/4k3/8/3R4/P1p1p3/2K1P3/1r6/8 w - - 0 2",
        "c3b2 e7e6 d5c5 c4c3 b2c3 e6d6 c3c4 d6e6 a4a5 e6e7 a5a6 e7e6",
        "hanging-piece",
    ),
    (
        "5k1Q/ppp2p2/8/6p1/8/4P2P/q4PP1/3R2K1 b - - 1 1",
        "f8e7 h8e5 a2e6 e5g5 e6f6 d1d7 e7d7 g5f6 a7a5 g1h2 b7b5 h3h4",
        "intermezzo",
    ),
    (
        "6k1/pp2bpp1/2prr2p/5q2/1PPP4/P2RPPP1/2Q3KP/R7 w - - 1 2",
        "e3e4 f5g6 a1d1 e7f8 d4d5 c6d5 e4d5 e6e5 c2f2 g6f5 f3f4 e5e4",
        "intermezzo",
    ),
    (
        "r4b1r/pp2pkp1/4bnBp/q7/8/2P1BP2/PPQ2P1P/3RR1K1 b - - 1 1",
        "f7g8 e3f4 e6f7 g6f7 g8f7 c2b3 f7g6 d1d4 h8g8 f4e5 g6h7 b3b7",
        "intermezzo",
    ),
    (
        "6k1/8/6pp/1p2Kp2/1Pp2P2/P2r3P/8/3R4 w - - 1 2",
        "d1a1 g8f7 a3a4 b5a4 a1a4 d3e3 e5d5 g6g5 b4b5 g5g4 a4a2 c4c3",
        "intermezzo",
    ),
]

_CAPTURING_DEFENDER_FIXTURES: list[tuple[str, str, TacticMotif]] = [
    # NOTE: r3k2N position removed (Phase 128.1 Plan 01): after e6a2 (bishop to a2),
    # the white rook on b1 has only one escape (a1) where black bishop wins it —
    # trapped-piece (Tier 2) beats capturing-defender (Tier 3) per D-03.
    (
        "r5k1/p1p1B2p/4N3/4n1pr/5pn1/1P3P2/P5P1/R4RK1 b - - 0 1",
        "g4e3 e6g5 h7h6 g5e4 g8f7 e7c5 e3f1 a1f1 e5d3 c5d4 h5d5 d4c3",
        "capturing-defender",
    ),
    (
        "r5k1/p1p1B2p/4N3/4n1pr/5pn1/1P3P2/P5P1/R4RK1 b - - 0 1",
        "g4e3 e6g5 h7h6 g5e4 g8f7 e7c5 e3f1 a1f1 e5d3 c5d4 h5d5 d4c3",
        "capturing-defender",
    ),
    (
        "bn2kbnr/4q3/3p1pp1/2pPp2p/1pP1P2P/4BN2/1PB2PP1/1N1QK2R b Kk - 0 1",
        "f8h6 d1e2 h6e3 e2e3 a8b7 e1g1 g8h6 b1d2 e8f8 f1a1 f8g7 f3e1",
        "capturing-defender",
    ),
    (
        "r1bk2nr/ppp3pp/1b6/4p3/1PP1P3/3B4/P5PP/RNB1K2R b KQ - 0 1",
        "b6d4 b1a3 d4a1 c1d2 g8f6 a3c2 a1b2 e1g1 h7h6 f1b1 b2d4 c2d4",
        "capturing-defender",
    ),
    (
        "rnbqkb1r/p2p1ppp/1p2pn2/2p5/2B1P3/2N2Q2/PPPP1PPP/R1B1K1NR w KQkq - 0 2",
        "e4e5 b8c6 e5f6 g7f6 c4b3 c8b7 d2d3 a7a6 f3h3 b6b5 c3e2 c6e5",
        "capturing-defender",
    ),
    (
        "rnbq1rk1/pppp1ppp/5n2/2b1p3/2P1P3/1P1P4/P3BPPP/RNBQK1NR b KQ - 0 1",
        "c5d4 g2g4 a7a5 g4g5 f6e8 h2h4 d4a1 h4h5 b8c6 h5h6 g7g6 g1f3",
        "capturing-defender",
    ),
    (
        "r1bqkbnr/1pp2pp1/p1np3p/3Np3/2B1P3/3P1Q2/PPPB1PPP/R3K1NR w KQkq - 0 2",
        "d5b6 g8f6 b6a8 b7b5 c4b3 c6d4 f3d1 d6d5 g1f3 c8g4 h2h3 g4f3",
        "capturing-defender",
    ),
    (
        "6k1/6pp/2p5/2bp4/8/3nRB2/3N2PP/5K2 b - - 0 1",
        "c5e3 f1e2 e3d2 e2d3 d2b4 h2h4 g8f7 h4h5 f7e7 d3c2 e7d6 f3e2",
        "hanging-piece",
    ),
    (
        "r4rk1/1p1b1p1p/3p1p2/p1p2P2/4P2P/P2Bn3/1PP1NRP1/2K4R b - - 0 1",
        "c5c4 f2f3 c4d3 f3g3 g8h8 c2d3 a8c8 c1d2 e3c2 e2c3 c2d4 d2e3",
        "capturing-defender",
    ),
    (
        "rn3rk1/ppp1pp1p/5np1/8/8/2P1BB1P/P1P2PP1/3RK2R w K - 1 2",
        "f3b7 b8d7 b7a8 f8a8 c3c4 g8f8 e1g1 f8e8 f1e1 f6e4 f2f3 e4d6",
        "capturing-defender",
    ),
]

_ANASTASIA_MATE_FIXTURES: list[tuple[str, str, TacticMotif]] = [
    # Phase 131-03: all replaced with CC0 TPs from the precision harness
    # (old fixtures passed the loose knight check but not cook's king+1/king+3 geometry).
    ("5rk1/5pp1/2N1n1p1/8/1p1pR3/1P6/r5PP/3R2K1 w - - 0 34", "c6e7 g8h7 e4h4", "anastasia-mate"),
    ("1kbQ4/p1p4p/2q5/8/4N1p1/3P4/PPP1nPPK/R4R2 b - - 0 22", "c6h6 d8h4 h6h4", "anastasia-mate"),
    ("4Q3/6pk/1p2p3/1Pn1P1K1/5PP1/8/r7/8 b - - 8 44", "c5e4 g5h4 a2h2", "anastasia-mate"),
    (
        "r6r/pppk4/3p2p1/2bPp1BP/1P6/3P4/P1P1n1PK/R2Q1R2 b - - 0 21",
        "h8h5 g5h4 h5h4",
        "anastasia-mate",
    ),
    ("1b6/7p/1pp1N1pk/4n3/4PR2/1PP5/rP5P/6K1 w - - 6 35", "f4h4", "anastasia-mate"),
    (
        "r4r2/3bN1pk/p3p3/1p1P4/q7/2R5/P4PPP/2R3K1 w - - 0 27",
        "c3h3 a4h4 h3h4",
        "anastasia-mate",
    ),
    ("5rk1/5pp1/7p/1P3Pb1/3R2P1/8/KPPn4/4R3 b - - 6 29", "f8a8 d4a4 a8a4", "anastasia-mate"),
    ("2k2b2/pppq4/2np4/8/3PP1b1/1BP5/PP2nQPK/R4R2 b - - 0 22", "d7h7 f2h4 h7h4", "anastasia-mate"),
    ("8/4N1pk/p2K4/2pP1R2/4q2p/8/8/8 w - - 0 49", "f5h5", "anastasia-mate"),
    ("5R2/8/4N1pk/p7/Pn1p2r1/1P6/8/1K6 w - - 0 38", "f8h8", "anastasia-mate"),
    ("r5k1/1pp3pp/3ppr2/pP2p3/P1P1P1P1/3P4/4nPPK/R2B1R2 b - - 5 23", "f6h6", "anastasia-mate"),
    ("r1b3k1/ppp2ppp/8/3P4/4r3/8/PPPQn1PK/4RR2 b - - 0 17", "e4h4", "anastasia-mate"),
    ("Q7/3pkp2/p3pr2/2b5/PpP5/1P6/3NnPPK/R4R2 b - - 0 25", "f6h6", "anastasia-mate"),
]

_DOVETAIL_MATE_FIXTURES: list[tuple[str, str, TacticMotif]] = [
    (
        "6R1/1pr1k1p1/p5b1/2npq1P1/4p3/P1P5/NP3Q2/1K6 b - - 1 1",
        "e4e3 b1c1 e3f2 g8g7 e5g7 b2b3 f2f1q c1d2 c5b3 d2e3 g7e5",
        "dovetail-mate",
    ),
    (
        "3r2k1/7p/1QR2qp1/8/4r3/1P5P/1PP2Pp1/5RK1 b - - 0 1",
        "g2f1q g1f1 d8d1 f1g2 f6g5 g2f3 e4f4 f3e2 g5h5 e2e3 h5e5",
        "dovetail-mate",
    ),
    (
        "1r3rk1/5pp1/p2p3p/3Bp1q1/2K1P3/3P4/PPP1N2R/R2Q4 b - - 1 1",
        "f8c8 d5c6 c8c6 c4d5 c6c5 d5d6 b8c8 d3d4 g5d8",
        "dovetail-mate",
    ),
    (
        "1r3r2/pp2Q3/3N1pk1/2pP1p1p/b7/6P1/PPP3BP/2K5 w - - 1 2",
        "g2h3 a4c2 c1c2 f8f7 e7f7 g6h6 d6f5 h6g5 f7g7",
        "dovetail-mate",
    ),
    (
        "2n2r2/r2P2kp/p2pRpp1/1p6/5P1Q/1P4P1/Pq4BP/4R2K w - - 1 2",
        "e6e7 c8e7 e1e7 f8f7 e7f7 g7f7 h4h7 f7e6 d7d8n e6f5 h7h3",
        "dovetail-mate",
    ),
    (
        "3k4/p2rrp1p/1q1p1Q2/3P4/8/6R1/PP4PP/4R2K w - - 1 2",
        "e1c1 b6g1 h1g1 d7c7 g3g8 d8d7 f6f5 e7e6 d5e6 f7e6 f5h7",
        "dovetail-mate",
    ),
    (
        "2r2k2/pp4n1/2p5/4PP2/3P2P1/1P2qB2/P1Q3K1/7R w - - 1 2",
        "h1h8 f8e7 c2c5 e7f7 c5c4 f7e7 f5f6 e7d7 c4f7",
        "dovetail-mate",
    ),
    ("7q/6k1/4pN1p/5QpP/p1P5/1r4P1/5P2/6K1 w - - 0 2", "f5g6 g7f8 g6e8 f8g7 e8e7", "dovetail-mate"),
    (
        "r6k/2p2pp1/p2p3p/2b1p2q/1PP1PP2/P4n2/2P1QPKP/R4R2 b - - 1 1",
        "h5h2 g2f3 h2h3",
        "dovetail-mate",
    ),
    (
        "2kr3r/pp5p/1bp5/8/4q2P/B2n1Q2/2KP1PP1/R6R b - - 1 1",
        "e4a4 c2c3 b6a5 a3b4 a5b4 c3c4 a4c2",
        "dovetail-mate",
    ),
    ("r4r2/1pp3pk/p2p4/3Np3/2B1P3/3PPnqb/PPP1K3/R2Q3R b - - 1 1", "g3g2", "dovetail-mate"),
    ("3R4/4k1pp/p4pq1/2p3r1/4b3/P5QP/1P3PP1/6K1 w - - 1 2", "g3d6 e7f7 d6d7", "dovetail-mate"),
    (
        "r3k2r/pp4pp/2p5/3p1b2/B2P2nq/3P4/PP3PPb/R1BQR2K b kq - 1 1",
        "h2e5 h1g1 h4f2 g1h1 f2h4 h1g1 h4h2 g1f1 h2h1 f1e2 h1g2",
        "dovetail-mate",
    ),
]

_HOOK_MATE_FIXTURES: list[tuple[str, str, TacticMotif]] = [
    # Phase 131-03: first 2 fixtures replaced with CC0 TPs (old fixtures had knight at
    # Chebyshev distance 2 from king, which fails cook's rook←knight←pawn chain constraint).
    ("4RNk1/p5p1/2p4p/3n1P2/1Pq5/8/P5PP/6K1 w - - 0 33", "f8g6 g8f7 e8f8", "hook-mate"),
    ("r5k1/1p4pp/3p3b/3Pp3/2P1N1RP/np4R1/1P3P2/K7 b - - 1 31", "a3c2 a1b1 a8a1", "hook-mate"),
    ("r4br1/2k2p1p/2nNpBp1/2PpPn2/8/2N5/P3QPPP/1R4K1 w - - 1 2", "b1b7", "hook-mate"),
    ("8/pp1kpp1R/4r3/3r4/1P1P2p1/P1PR1nP1/5P2/5K2 b - - 1 1", "e6e1 f1g2 e1g1", "hook-mate"),
    ("7r/8/4R2p/4P1p1/3k1n1P/3rN3/5PP1/2R3K1 w - - 1 2", "c1c4", "hook-mate"),
    ("7r/6RP/3pkp2/p1p1bN2/2PpP3/r7/6P1/5RK1 w - - 1 2", "g7e7", "hook-mate"),
    ("8/2p3R1/ppk1p3/1N5p/2P5/P7/nPPK1P2/7r w - - 0 2", "g7c7", "hook-mate"),
    ("6k1/7p/6p1/1r1p2P1/p1nB4/P1PK4/1P2rP2/1R5R b - - 1 1", "e2d2", "hook-mate"),
    (
        "1k4n1/1p4bp/pN6/2P2p2/8/2PKB3/q4PbP/1R2R3 w - - 0 2",
        "e3f4 g7e5 f4e5 b8a7 e5b8 a7b8 e1e8 b8c7 e8c8",
        "hook-mate",
    ),
    (
        "5k2/R4p2/1p3NpN/2p1P3/5B2/1b1r3P/1P3PP1/6K1 w - - 1 2",
        "a7a8 d3d8 a8d8 f8g7 d8g8",
        "hook-mate",
    ),
]

_DOUBLE_CHECK_FIXTURES: list[tuple[str, str, TacticMotif]] = [
    ("8/pp1RPk1p/4r1p1/8/8/7P/1P4P1/7K w - - 1 2", "e7e8q f7e8", "double-check"),
]

_INTERFERENCE_FIXTURES: list[tuple[str, str, TacticMotif]] = [
    (
        "2rr2k1/pb3pp1/1p3q1p/3p4/1PnN4/P2QPP2/2B3PP/2RR2K1 w - - 1 2",
        "d3h7 g8f8 c2f5 c8a8 f5g4 g7g6 h7h6 f8g8 c1c3 a7a5 b4b5 b7c8",
        "clearance",
    ),
]

_SMOTHERED_MATE_FIXTURES: list[tuple[str, str, TacticMotif]] = [
    ("r2qkb1r/pp1bnppp/2n1p3/1B1p1N2/8/2P5/PP2QPPP/RNB2RK1 w kq - 1 2", "f5d6", "smothered-mate"),
    ("r2q1rk1/1pp2ppp/4pn2/3pNb1P/3n4/2N5/P2BPPP1/3RKB1R b K - 1 1", "d4c2", "smothered-mate"),
]

_SELF_INTERFERENCE_FIXTURES: list[tuple[str, str, TacticMotif]] = []

_SACRIFICE_FIXTURES: list[tuple[str, str, TacticMotif]] = []

_ARABIAN_MATE_FIXTURES: list[tuple[str, str, TacticMotif]] = []

_BODEN_MATE_FIXTURES: list[tuple[str, str, TacticMotif]] = []

_DOUBLE_BISHOP_MATE_FIXTURES: list[tuple[str, str, TacticMotif]] = []

# === Shared hard-negative set (real quiet prod errors -> None) ===

_HARD_NEGATIVES: list[tuple[str, str]] = [
    ("r2q1rk1/5ppp/p2bpn2/1p1p1bB1/3Q4/2NB4/PPP2PP1/R4R1K w - - 1 2", "d3f5 e6f5"),
    ("8/8/1p3nkp/3n1Np1/P5P1/5K1P/1P3P2/8 b - - 1 1", "h6h5"),
    ("q4rk1/p1pnp2p/3p1bp1/3P1b2/2P5/6P1/PP2NP1P/R1BQK2R b KQ - 0 1", "d7e5"),
    ("5rk1/B6p/3pb1p1/2p5/2n5/6P1/P4P1P/R1R3K1 w - - 1 2", "c1b1"),
    ("5r2/B4k1p/3pb1p1/2p5/2n5/6P1/P4P1P/2R1R1K1 b - - 1 1", "f8a8 a7c5"),
    ("r7/8/6p1/2pk4/6pR/8/P4P1P/6K1 w - - 0 2", "h4g4 c5c4"),
    (
        "r7/8/6R1/3k4/2p5/8/P4P1P/6K1 b - - 0 1",
        "c4c3 g6g5 d5d4 g5g4 d4d3 g4g3 d3d2 g3g7 a8c8 g7d7 d2e2 d7e7",
    ),
    ("8/p4p2/1p4pp/3k4/1P1P1P2/3K3P/P5P1/8 b - - 0 1", "a7a6 f4f5"),
    ("8/p7/1p6/3k4/1P1P1P1p/5K2/P7/8 b - - 1 1", "d5d4 f3g4"),
    ("2k1R2r/1pp2p2/p4Np1/8/6PP/5Pn1/PPP5/2K5 b - - 1 1", "h8e8 f6e8"),
    (
        "2k1N3/1pp2p2/p5p1/8/6PP/5P2/PPP1n3/2K5 w - - 1 2",
        "c1d2 e2f4 d2e3 f4g2 e3f2 g2h4 e8f6 c8d8 f6e4 d8e7 f2g3 g6g5",
    ),
    (
        "3k4/1p3p2/p1p2Np1/5P2/4K1P1/2P5/PP6/4n3 w - - 0 2",
        "f5g6 f7g6 g4g5 e1g2 f6g4 d8e7 a2a4 e7d8 g4e5 g2h4 a4a5 d8e8",
    ),
    (
        "8/1p2k3/p1p2Np1/6K1/6P1/2P2n2/PP6/8 w - - 1 2",
        "g5g6 a6a5 f6e4 f3e5 g6h5 e7f8 b2b3 b7b6 g4g5 f8g7 e4d6 b6b5",
    ),
    ("r7/pp1k1ppp/8/3p4/1b6/2B2n1P/PP3P2/R2K3R b - - 1 1", "b4c3"),
    ("3r4/pp3pkp/2p2pp1/8/1QP3P1/1P5P/P2q1P2/4R1K1 w - - 1 2", "b4d2"),
    (
        "8/8/4k2P/6R1/2p1p3/2P1K1P1/2b5/8 b - - 0 1",
        "e6f6 g5g8 f6e7 h6h7 c2b3 g3g4 e7d7 g4g5 b3d1 h7h8q d1g4 g5g6",
    ),
    (
        "8/5k2/7P/8/2p1p1R1/2P1K1P1/2b5/8 b - - 1 1",
        "c2a4 h6h7 a4d7 g4g8 d7f5 h7h8q f7e6 g3g4 e6d6 g4f5 d6c7",
    ),
    (
        "8/8/6kP/7b/2p4R/2P1K1P1/8/8 w - - 1 2",
        "h4h5 g6h5 h6h7 h5g4 h7h8q g4f5 h8e8 f5g5 e3e4 g5f6 e4f4 f6g7",
    ),
    ("r3k2r/1ppnn1p1/p2q1p2/3p3p/3P1PPP/2NQ4/PPP1N3/2KRR3 b kq - 0 1", "h5g4 e2g3"),
    ("2rqkbr1/1bpnpp2/p4n1p/1p1pB1p1/3P4/2NBPN1P/PPPQ1PP1/2KRR3 b - - 1 1", "f6e4 d2e2"),
    ("2rq1br1/1bpnpk2/p4p1p/1p2B1pQ/3Pp3/2N1P2P/PPPN1PP1/2KRR3 b - - 1 1", "g8g6"),
    ("2r1qbr1/1bpnp1k1/p4p1p/1p4p1/3Pp1Q1/2N1P1BP/PPPN1PP1/2KRR3 b - - 1 1", "e7e6 g4e2"),
    (
        "1Q3bk1/7p/6p1/3r1p2/4bP1P/8/1P3PPK/8 b - - 1 1",
        "d5d2 h2g3 h7h5 f2f3 e4c6 b8b3 g8h7 b3c3 d2d6 b2b4 h7g8 b4b5",
    ),
    ("1Q3b2/6kp/6p1/3r1p2/4bP1P/8/1P3PPK/8 w - - 1 2", "f2f3"),
    ("r2q1rk1/pp1b1pbp/2pQ2p1/4n3/8/2N3B1/PPP1BPPP/R4RK1 b - - 1 1", "f8e8 a1c1"),
    (
        "8/8/1p6/2b4p/4rk2/8/3R4/3K4 w - - 0 2",
        "d2h2 f4g4 d1c2 h5h4 c2d3 g4g3 h2h1 e4g4 d3c3 h4h3 c3b3 g3g2",
    ),
    (
        "8/8/1p6/2bRr2p/5k2/8/8/3K4 w - - 1 2",
        "d5d3 h5h4 d1c2 f4g4 d3b3 h4h3 b3b1 g4g3 b1b5 e5e3 b5b1 h3h2",
    ),
    ("2r2rk1/1Q1qbppp/2n2n2/4p3/2Pp1P2/P2P4/3B1PBP/RN2K2R w KQ - 1 2", "b7d7"),
    ("2r1r1k1/3n1ppp/5b2/4n3/2PpBB2/P2P4/3N1P1P/R3R1K1 b - - 1 1", "d7c5"),
    ("Q2r2k1/5p1p/6p1/8/3p1P2/3n4/7P/R5K1 b - - 0 1", "d8a8"),
]

# A real checkmate line where detect_fork also fires — proves mate dominance (D-07).
_MATE_PLUS_FORK: tuple[str, str] = (
    "3r4/pb3pk1/1p6/2p1R1P1/8/1Pp1K1P1/P2r1P1N/R7 b - - 1 1",
    "d8d3 e3f4 d2f2 h2f3 d3f3 f4g4 b7c8 e5e6 c8e6 g4h4 f2h2",
)

# ---------------------------------------------------------------------------
# Phase 128.1 Plan 01: new Tier-2 motifs
# ---------------------------------------------------------------------------

# Positive fixtures for discovered-check (int 25).
# Sourced from TRAIN rows tagged discoveredCheck, non-mate positions only
# (mate positions are pre-empted by Tier-1; discovered-check fires when the
# first pov move gives a discovered check — the checking piece is NOT the mover).
_DISCOVERED_CHECK_FIXTURES: list[tuple[str, str, TacticMotif]] = [
    # Confirmed from TRAIN (discoveredCheck theme, detector fires discovered-check):
    (
        "r4rk1/2p1ppbp/6p1/p2qP3/1PR2B2/4PN2/1P1Q2PP/K1R5 b - - 0 22",
        "a5b4 a1b1 a8a1 b1a1 d5a8 a1b1 b4b3 d2a5 a8a5",
        "discovered-check",
    ),
    (
        "1r6/2pkP3/3P4/4P2p/3R2p1/4R3/1p5r/5K2 w - - 1 47",
        "d6c7 d7c7 e3c3",
        "discovered-check",
    ),
    (
        "4r1k1/6pp/1n2P3/4P3/8/pQ3BP1/3p1q1P/1R5K w - - 2 39",
        "e6e7 g8h8 b3f7 f2f3 f7f3",
        "discovered-check",
    ),
    (
        "3r1k2/ppq3r1/2p2N1Q/4p3/8/P2B4/1PP4K/R7 b - - 4 27",
        "e5e4 h2h1 c7g3 d3e4 f8e7 a1f1 d8d6",
        "discovered-check",
    ),
    (
        "8/4k3/5R2/1r3pK1/1p1Pp3/1P2P3/P7/8 b - - 7 50",
        "f5f4 g5f4 e7f6",
        "discovered-check",
    ),
    (
        "8/8/5p1p/6p1/R2Pk3/4n3/4K3/8 w - - 0 47",
        "d4d5 e4d5 e2e3",
        "discovered-check",
    ),
    # Additional confirmed from TRAIN (discoveredCheck theme, detector wins dispatch):
    (
        "8/8/6k1/p3q1N1/1p6/1P4R1/6PK/8 w - - 5 49",
        "g5f3 e5g3 h2g3",
        "discovered-check",
    ),
    (
        "r1b2rk1/ppb4p/n1p1p3/2P3q1/2BPQp2/P6P/1P3PPB/2KR2NR b - - 0 16",
        "f4f3 c1c2 f3g2",
        "discovered-check",
    ),
    (
        "3r4/4k2p/6pP/R4b2/P7/1PPnP3/3K1PP1/7R b - - 4 34",
        "d3f2 d2e2 f2h1",
        "discovered-check",
    ),
    (
        "r4rk1/pp2b1pp/6p1/2pPp3/2B5/2P2n1P/PP1B1PK1/R4R2 w - - 0 18",
        "d5d6 g8h8 d6e7",
        "discovered-check",
    ),
    (
        "8/8/5B2/b1p5/1p6/3k1P2/B5PP/4K3 b - - 0 39",
        "b4b3 e1f2 b3a2",
        "discovered-check",
    ),
    (
        "r4rk1/5ppp/1p6/1Bq5/2P3P1/6Q1/PP3nP1/RN3RK1 b - - 0 20",
        "f2e4 g3f2 e4f2",
        "discovered-check",
    ),
    # Reclassified from _DISCOVERED_ATTACK_FIXTURES in Phase 128.1 Plan 01: d4d3
    # is a pawn move that reveals the black queen on c5 giving check — D-03 split.
    (
        "3r1rk1/p3n1pp/4p3/2q5/3pQP2/1P3N1P/P5P1/3R1RK1 b - - 1 1",
        "d4d3",
        "discovered-check",
    ),
]

# Positive fixtures for trapped-piece (int 26).
# These are positions where detect_trapped_piece fires: an opponent non-pawn piece
# is under attack by pov AND every legal escape square loses material (D-06 strict
# gate).  The lichess 'trappedPiece' theme covers a broader definition (any piece that
# is captured via forcing lines), so detector-confirmed firings are used here instead
# of raw CSV rows tagged trappedPiece — the two sets overlap only partially (D-08
# precision floors are deferred to Plan 02).
_TRAPPED_PIECE_FIXTURES: list[tuple[str, str, TacticMotif]] = [
    # Confirmed from TRAIN/TEST (dispatcher returns trapped-piece with v3 gate):
    (
        "7Q/1pp2k2/1q2p1rp/3p1p1N/1p1P1P2/2P2P2/P1K5/8 w - - 0 34",
        "h8h7 f7f8 h7g6",
        "trapped-piece",
    ),
    (
        "r5nr/pp1q3k/n1p1b1pp/4Q3/3PP2P/5N2/PPP2PP1/RN2K2R w KQ - 1 15",
        "f3g5 h6g5 h4g5",
        "trapped-piece",
    ),
    (
        "3k1B2/7R/2pP4/1p3p2/4n3/6qP/6P1/6K1 w - - 5 45",
        "f8e7 d8e8 d6d7 e8d7 e7h4",
        "trapped-piece",
    ),
    (
        "8/pp6/1q3p2/8/2rrRP2/k6P/2BQ2PK/8 w - - 0 40",
        "e4e3 a3b2 c2d3",
        "trapped-piece",
    ),
    (
        "r1bqr1k1/ppp2ppp/2p2n2/2b5/N3P3/3P3P/PPP2PP1/R1BQKB1R b KQ - 2 8",
        "f6e4 a4c5 e4c3",
        "trapped-piece",
    ),
    (
        "4r1k1/1p3ppp/p2r4/2nb4/1P1N1K2/P1n1P2P/2BN1PP1/R1R5 b - - 4 24",
        "c5e6 d4e6 c3e2",
        "trapped-piece",
    ),
    (
        "r4r1k/pb3p1p/1p2pP2/2p2nQ1/3pP2P/P4N2/qPP2PR1/2K4R w - - 1 22",
        "f3e5 h7h6 g5g7 f5g7 f6g7 h8h7 e5d7",
        "trapped-piece",
    ),
    (
        "1r2r1k1/p4ppp/8/6P1/2R2P2/1n5P/PP3P2/1K2BB1R b - - 0 26",
        "e8e1 b1c2 e1c1 c2d3 b8d8",
        "hanging-piece",
    ),
    (
        "r2q4/pQ5n/1p3rpk/2p4p/7N/6R1/PP4PP/4R1K1 w - - 4 26",
        "g3g6 f6g6 h4f5",
        "trapped-piece",
    ),
    (
        "r7/pb5k/1p2p3/8/2PP4/2P2pBP/5Pr1/R3R2K b - - 4 28",
        "g2g3 f2g3 f3f2",
        "trapped-piece",
    ),
    (
        "2R5/Q4ppk/1p2r2p/4n3/4q3/1P2B2P/P4PP1/6K1 b - - 0 30",
        "e5f3 g2f3 e6g6 g1h2 e4f3",
        "trapped-piece",
    ),
    (
        "8/6R1/5p2/8/2rk4/5P2/2bK2PP/8 w - - 3 47",
        "g7g4 d4e5 g4c4",
        "trapped-piece",
    ),
    # Reclassified from _CAPTURING_DEFENDER_FIXTURES (Phase 128.1 Plan 01): after
    # e6a2 (black bishop moves to a2), white rook on b1 is attacked by the bishop
    # and its only escape (Ra1) is met by Bxa1 — black bishop cheaper than rook,
    # rook loses material. trapped-piece (Tier 2) beats capturing-defender (Tier 3).
    (
        "r3k2N/ppp3pp/3bbn2/8/4p3/8/PPnN1PPP/1RB2RK1 b q - 1 1",
        "e6a2 b2b3 a2b1 d2b1 d6b4 f1d1 c7c5 c1b2 c2d4 g1f1 e8e7 b2d4",
        "trapped-piece",
    ),
]

# ---------------------------------------------------------------------------
# Phase 128.1 Plan 02: move-type family (Tier 5 — en-passant, promotion, under-promotion)
# ---------------------------------------------------------------------------
# Move-type motifs fire ONLY when no real tactic fires (D-03/D-04 lowest tier).
# These fixtures use simple clean positions where no real tactic pre-empts the
# move-type tag. Fixture counts are thin by design (D-08 sparsity caveat) — they
# are placed in _MOVE_TYPE_FIXTURE_SETS, NOT in _VALIDATED_FIXTURE_SETS, to
# exempt them from the >=10 richness rule (test_validated_motifs_have_enough_fixtures).

_EN_PASSANT_FIXTURES: list[tuple[str, str, TacticMotif]] = [
    # Simple en-passant captures where no real tactic fires.
    # FEN has en-passant square set, pov's first move is the ep capture.
    # (board_after_flaw = board with pov to move, ep square set)
    ("8/8/8/3Pp3/8/8/8/K1k5 w - e6 0 1", "d5e6", "en-passant"),
    ("8/8/8/Pp6/8/8/8/K1k5 w - b6 0 1", "a5b6", "en-passant"),
    ("k7/8/8/8/pP6/8/8/k1K5 b - b3 0 1", "a4b3", "en-passant"),
    ("k7/8/8/8/3pP3/8/8/7K b - e3 0 1", "d4e3", "en-passant"),
]

_PROMOTION_FIXTURES: list[tuple[str, str, TacticMotif]] = [
    # Queen promotions where no real tactic fires.
    # From lichess TRAIN: ZUGdw (g2g1q, no real tactic pre-empts).
    ("8/P7/2K5/8/3N4/8/4b1pk/8 b - - 2 66", "g2g1q d4e2 g1a7", "promotion"),
    # Curated clean positions: no check, no fork, no other tactic
    ("8/6P1/8/8/8/8/8/k1K5 w - - 0 1", "g7g8q", "promotion"),
    ("8/3P4/8/8/8/8/8/k1K5 w - - 0 1", "d7d8q", "promotion"),
    ("6k1/6P1/6K1/8/8/8/8/8 w - - 0 1", "g7g8q", "promotion"),
]

_UNDER_PROMOTION_FIXTURES: list[tuple[str, str, TacticMotif]] = [
    # Non-queen promotions where no real tactic fires.
    # (D-01 dominance: under-promotion MUST tag here, never "promotion")
    ("8/6P1/8/8/8/8/8/k1K5 w - - 0 1", "g7g8n", "under-promotion"),
    ("8/6P1/8/8/8/8/8/k1K5 w - - 0 1", "g7g8r", "under-promotion"),
    ("8/6P1/8/8/8/8/8/k1K5 w - - 0 1", "g7g8b", "under-promotion"),
    ("8/P7/8/8/8/8/8/k1K5 w - - 0 1", "a7a8n", "under-promotion"),
]

# Move-type fixture sets: checked by test_positives_fire_expected_motif and
# the partition-completeness assert, but EXEMPT from the >=10 richness rule
# (D-08 sparsity caveat explicitly accepts thin move-type samples).
_MOVE_TYPE_FIXTURE_SETS: list[list[tuple[str, str, TacticMotif]]] = [
    _EN_PASSANT_FIXTURES,
    _PROMOTION_FIXTURES,
    _UNDER_PROMOTION_FIXTURES,
]
_MOVE_TYPE_IDS: list[str] = [
    "en-passant",
    "promotion",
    "under-promotion",
]

_VALIDATED_FIXTURE_SETS: list[list[tuple[str, str, TacticMotif]]] = [
    _FORK_FIXTURES,
    _HANGING_PIECE_FIXTURES,
    _PIN_FIXTURES,
    _SKEWER_FIXTURES,
    _DISCOVERED_ATTACK_FIXTURES,
    _BACK_RANK_MATE_FIXTURES,
    _MATE_FIXTURES,
    _DEFLECTION_FIXTURES,
    _ATTRACTION_FIXTURES,
    _CLEARANCE_FIXTURES,
    _X_RAY_FIXTURES,
    _INTERMEZZO_FIXTURES,
    _CAPTURING_DEFENDER_FIXTURES,
    _ANASTASIA_MATE_FIXTURES,
    _DOVETAIL_MATE_FIXTURES,
    _HOOK_MATE_FIXTURES,
    _DISCOVERED_CHECK_FIXTURES,  # Plan 128.1-01
    _TRAPPED_PIECE_FIXTURES,  # Plan 128.1-01
]
_SUPPRESSED_FIXTURE_SETS: list[list[tuple[str, str, TacticMotif]]] = [
    _DOUBLE_CHECK_FIXTURES,
    _INTERFERENCE_FIXTURES,
    _SMOTHERED_MATE_FIXTURES,
    _SELF_INTERFERENCE_FIXTURES,
    _SACRIFICE_FIXTURES,
    _ARABIAN_MATE_FIXTURES,
    _BODEN_MATE_FIXTURES,
    _DOUBLE_BISHOP_MATE_FIXTURES,
]
_VALIDATED_IDS: list[str] = [
    "fork",
    "hanging-piece",
    "pin",
    "skewer",
    "discovered-attack",
    "back-rank-mate",
    "mate",
    "deflection",
    "attraction",
    "clearance",
    "x-ray",
    "intermezzo",
    "capturing-defender",
    "anastasia-mate",
    "dovetail-mate",
    "hook-mate",
    "discovered-check",  # Plan 128.1-01
    "trapped-piece",  # Plan 128.1-01
]
_SUPPRESSED_IDS: list[str] = [
    "double-check",
    "interference",
    "smothered-mate",
    "self-interference",
    "sacrifice",
    "arabian-mate",
    "boden-mate",
    "double-bishop-mate",
]


def _bar_for(motif: TacticMotif) -> float:
    """The D-10 precision bar that applies to a motif."""
    return CORE_PRECISION_BAR if motif in _CORE_MOTIFS else TIER3_PRECISION_BAR


def _run_fixtures(
    fixtures: list[tuple[str, str, TacticMotif]],
) -> list[tuple[TacticMotif | None, TacticMotif]]:
    """Run the detector over positive fixtures.

    Returns [(predicted_motif_or_None, expected_motif), ...]. Maps the detector's
    int output back to a motif string via _INT_TO_MOTIF for comparison.

    Phase 127: detect_tactic_motif now returns a 4-tuple (motif_int, piece, confidence, depth).
    """
    results: list[tuple[TacticMotif | None, TacticMotif]] = []
    for fen, pv, expected in fixtures:
        board = chess.Board(fen)
        motif_int, _piece, _conf, _depth = detect_tactic_motif(board, pv)
        # Depth assertion: when a motif fires, depth must be a non-negative int (SC#1).
        if motif_int is not None:
            assert _depth is not None and _depth >= 0, (
                f"motif {_INT_TO_MOTIF.get(motif_int)} fired but depth is {_depth!r} on {fen}"
            )
        predicted = _INT_TO_MOTIF[motif_int] if motif_int is not None else None
        results.append((predicted, expected))
    return results


def _compute_precision(
    motif: TacticMotif,
    positives: list[tuple[str, str, TacticMotif]],
) -> tuple[float, int, int]:
    """Precision = TP / (TP + FP) for `motif` over (positives + shared hard-negatives).

    TP: a fixture whose expected motif is `motif` and the detector predicts `motif`.
    FP: a fixture (positive of any motif, or a hard-negative) where the detector
        predicts `motif` but the expected label is NOT `motif`.
    A missed positive (expected `motif`, predicted other/None) is a False Negative —
    it does NOT lower precision (recall is not gated, D-10).

    Returns (precision, tp, fp). Precision is 1.0 when TP+FP == 0 (no claims made).
    """
    tp = fp = 0
    # Positive fixtures for this motif (TP / partial-FN source).
    for predicted, expected in _run_fixtures(positives):
        if predicted == motif:
            if expected == motif:
                tp += 1
            else:
                fp += 1
    # Hard-negatives: any prediction of `motif` here is a false positive.
    for fen, pv in _HARD_NEGATIVES:
        board = chess.Board(fen)
        motif_int, _piece, _conf, _depth = detect_tactic_motif(board, pv)
        if motif_int is not None and _INT_TO_MOTIF[motif_int] == motif:
            fp += 1
    denom = tp + fp
    return (1.0 if denom == 0 else tp / denom), tp, fp


# ---------------------------------------------------------------------------
# Encoding sanity (TacticMotifInt <-> TacticMotif round-trip)
# ---------------------------------------------------------------------------


class TestTacticMotifInt:
    def test_int_motif_roundtrip(self) -> None:
        for member in TacticMotifInt:
            motif = _INT_TO_MOTIF[member.value]
            assert _MOTIF_TO_INT[motif] == member.value

    def test_all_29_motifs_encoded(self) -> None:
        # Plan 128.1-01 adds discovered-check (25) and trapped-piece (26).
        # Plan 128.1-02 adds en-passant (27), promotion (28), under-promotion (29).
        assert len(_INT_TO_MOTIF) == 29
        assert len(_MOTIF_TO_INT) == 29


# ---------------------------------------------------------------------------
# Per-motif detection: every positive fixture must fire its motif (recall
# evidence — NOT gated, but documents detector behavior on real prod data).
# ---------------------------------------------------------------------------

_ALL_FIXTURE_SETS = _VALIDATED_FIXTURE_SETS + _SUPPRESSED_FIXTURE_SETS + _MOVE_TYPE_FIXTURE_SETS


@pytest.mark.parametrize(
    "fixtures",
    _ALL_FIXTURE_SETS,
    ids=_VALIDATED_IDS + _SUPPRESSED_IDS + _MOVE_TYPE_IDS,
)
def test_positives_fire_expected_motif(
    fixtures: list[tuple[str, str, TacticMotif]],
) -> None:
    """Every hand-confirmed positive fires its expected motif (det. is deterministic)."""
    if not fixtures:
        pytest.skip("no prod fixtures for this motif (structurally validated elsewhere)")
    for predicted, expected in _run_fixtures(fixtures):
        assert predicted == expected


def test_validated_motifs_have_enough_fixtures() -> None:
    """Validated motifs carry >=10 hand-confirmed positives (fixture richness).

    Move-type motifs are EXEMPT from this rule (D-08 sparsity caveat): en-passant,
    promotion, and under-promotion have naturally thin fixture counts in the CC0 puzzle
    set (12/176/4 TRAIN labels respectively), and their precision is ~100% by
    construction (trivial move-shape detection). They are tracked in
    _MOVE_TYPE_FIXTURE_SETS, not _VALIDATED_FIXTURE_SETS.
    """
    for fixtures in _VALIDATED_FIXTURE_SETS:
        motif = fixtures[0][2]
        assert len(fixtures) >= 10, f"{motif} has only {len(fixtures)} fixtures"


# ---------------------------------------------------------------------------
# Hard negatives: the catch-all must not over-fire on real quiet prod errors.
# ---------------------------------------------------------------------------


class TestHardNegatives:
    def test_all_hard_negatives_return_none(self) -> None:
        assert len(_HARD_NEGATIVES) >= 20
        for fen, pv in _HARD_NEGATIVES:
            board = chess.Board(fen)
            motif_int, piece, conf, depth = detect_tactic_motif(board, pv)
            assert motif_int is None, f"over-fire {_INT_TO_MOTIF.get(motif_int)} on {fen}"
            assert piece is None and conf is None and depth is None


# ---------------------------------------------------------------------------
# D-10 precision bars (the accuracy gate — TACDET-03, milestone risk Q-011).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "fixtures",
    _VALIDATED_FIXTURE_SETS,
    ids=_VALIDATED_IDS,
)
def test_precision_bar_validated(
    fixtures: list[tuple[str, str, TacticMotif]],
) -> None:
    """Validated motifs meet their D-10 bar over (positives + hard-negatives)."""
    motif = fixtures[0][2]
    precision, tp, _fp = _compute_precision(motif, fixtures)
    assert tp >= 1, f"{motif}: no true positives"
    assert precision >= _bar_for(motif), f"{motif} precision {precision:.3f} < bar"


@pytest.mark.parametrize(
    "fixtures",
    _SUPPRESSED_FIXTURE_SETS,
    ids=_SUPPRESSED_IDS,
)
def test_suppressed_motifs_documented_and_storable(
    fixtures: list[tuple[str, str, TacticMotif]],
) -> None:
    """Query-suppressed motifs: bar NOT enforced, but the detector still STORES the
    motif (D-11 — suppression is a query-time decision, never a detect-time NULL).

    For motifs with >=1 prod fixture we prove the dispatcher returns a non-None int.
    For zero-data motifs we assert the motif is structurally storable (encodable +
    in the dispatcher's registry), which is the D-11 guarantee.
    """
    # The fixture list can be empty (zero-data motif), so resolve the motif from
    # the _SUPPRESSED_FIXTURE_SETS ordering rather than from fixtures[0].
    idx = _SUPPRESSED_FIXTURE_SETS.index(fixtures)
    suppressed_order: list[TacticMotif] = [
        "double-check",
        "interference",
        "smothered-mate",
        "self-interference",
        "sacrifice",
        "arabian-mate",
        "boden-mate",
        "double-bishop-mate",
    ]
    motif: TacticMotif = suppressed_order[idx]
    assert motif in _QUERY_SUPPRESSED_MOTIFS
    # Structurally storable: encodable in both directions.
    assert motif in _MOTIF_TO_INT
    assert _INT_TO_MOTIF[_MOTIF_TO_INT[motif]] == motif
    # If we have a prod fixture, prove it actually stores (non-None int).
    if fixtures:
        fen, pv, _ = fixtures[0]
        motif_int, _piece, _conf, _depth = detect_tactic_motif(chess.Board(fen), pv)
        assert motif_int is not None


def test_suppressed_set_matches_validated_partition() -> None:
    """Every motif is either validated, suppressed, or in the move-type family.

    Partition: validated ∪ suppressed ∪ move_type == set(_INT_TO_MOTIF.values()).
    No motif may be silently dropped. Move-type motifs are exempt from the
    >=10 fixture richness rule (D-08 sparsity caveat) but MUST appear in one partition.
    """
    validated = {fs[0][2] for fs in _VALIDATED_FIXTURE_SETS}
    move_type = {fs[0][2] for fs in _MOVE_TYPE_FIXTURE_SETS}
    assert validated.isdisjoint(_QUERY_SUPPRESSED_MOTIFS)
    assert validated.isdisjoint(move_type)
    assert _QUERY_SUPPRESSED_MOTIFS.isdisjoint(move_type)
    assert validated | _QUERY_SUPPRESSED_MOTIFS | move_type == set(_INT_TO_MOTIF.values())


# ---------------------------------------------------------------------------
# Priority order (D-07): mate dominates; hanging-piece is the catch-all (last).
# ---------------------------------------------------------------------------


class TestPriorityOrder:
    def test_mate_dominates_over_fork(self) -> None:
        """A checkmate line that ALSO contains a fork returns a mate motif, not fork."""
        if _MATE_PLUS_FORK is None:
            pytest.skip("no mate-plus-fork fixture available in prod sample")
        fen, pv = _MATE_PLUS_FORK
        motif_int, _piece, _conf, _depth = detect_tactic_motif(chess.Board(fen), pv)
        assert motif_int is not None
        assert _INT_TO_MOTIF[motif_int] in MATE_MOTIFS

    def test_all_mate_fixtures_return_mate_family(self) -> None:
        """back-rank/generic mate fixtures resolve to a MATE_MOTIFS member (tier-1)."""
        for fixtures in (_BACK_RANK_MATE_FIXTURES, _MATE_FIXTURES):
            for predicted, _expected in _run_fixtures(fixtures):
                assert predicted in MATE_MOTIFS

    def test_hanging_piece_is_catch_all_last(self) -> None:
        """hanging-piece fixtures resolve to hanging-piece — nothing higher pre-empted,
        proving it sits at the bottom of the priority chain (D-07)."""
        for predicted, _expected in _run_fixtures(_HANGING_PIECE_FIXTURES):
            assert predicted == "hanging-piece"

    def test_discovered_check_dominates_discovered_attack(self) -> None:
        """D-03: discovered-check (Tier 2, lower index) beats discovered-attack on the
        same PV — the discovering move that gives check tags as discovered-check."""
        # This fixture is a discovered check: pov's first move reveals a check from
        # another pov piece.  Before Plan 128.1-01, detect_discovered_attack would fire
        # here (Sub-case 1).  After the split, discovered-check must win instead.
        fen = "1r6/2pkP3/3P4/4P2p/3R2p1/4R3/1p5r/5K2 w - - 1 47"
        pv = "d6c7 d7c7 e3c3"
        motif_int, _piece, _conf, _depth = detect_tactic_motif(chess.Board(fen), pv)
        assert motif_int is not None
        assert _INT_TO_MOTIF[motif_int] == "discovered-check", (
            f"expected 'discovered-check', got '{_INT_TO_MOTIF.get(motif_int)}'"
        )

    def test_depth_primary_hanging_beats_deeper_trapped(self) -> None:
        """D-05/D-07: hanging-piece (Tier 4, depth 0) beats trapped-piece (Tier 2, depth 4)
        because depth is the primary sort key — shallowest tactic wins.

        Previously (tier-primary dispatch) trapped-piece would win because Tier 2 < Tier 4.
        Under D-05 depth-primary dispatch, depth 0 < depth 4, so hanging-piece wins.
        This is correct per D-07: missing an en-prise piece is the root-cause error.

        Position: black pov plays Rxe1 (rook captures undefended White Bishop on e1),
        hanging-piece fires at depth 0. Deeper in the PV, the white bishop on f1 becomes
        trapped (depth 4). Depth-primary dispatch resolves to hanging-piece.
        """
        fen = "1r2r1k1/p4ppp/8/6P1/2R2P2/1n5P/PP3P2/1K2BB1R b - - 0 26"
        pv = "e8e1 b1c2 e1c1 c2d3 b8d8"
        motif_int, _piece, _conf, _depth = detect_tactic_motif(chess.Board(fen), pv)
        assert motif_int is not None
        assert _INT_TO_MOTIF[motif_int] == "hanging-piece", (
            f"expected 'hanging-piece' (depth 0 beats trapped-piece depth 4 under D-05), "
            f"got '{_INT_TO_MOTIF.get(motif_int)}'"
        )

    def test_under_promotion_dominates_promotion(self) -> None:
        """D-01: under-promotion (non-queen) NEVER tags as 'promotion'.

        When moves[0] promotes to a knight, the dispatcher must return 'under-promotion'
        (Tier 5, rank 0) and NEVER 'promotion' (Tier 5, rank 1). Under-promotion is
        ranked first in _MOVE_TYPE_REGISTRY exactly to enforce this dominance.
        """
        # White promotes a pawn to a knight — no other tactic fires.
        fen = "8/6P1/8/8/8/8/8/k1K5 w - - 0 1"
        pv = "g7g8n"
        motif_int, _piece, _conf, _depth = detect_tactic_motif(chess.Board(fen), pv)
        assert motif_int is not None, "under-promotion should fire"
        assert _INT_TO_MOTIF[motif_int] == "under-promotion", (
            f"expected 'under-promotion', got '{_INT_TO_MOTIF.get(motif_int)}'"
        )

    def test_real_tactic_beats_promotion_motif(self) -> None:
        """D-04: a fork that happens to involve a promotion returns the real tactic,
        not a move-type tag — move-type is the lowest tier and loses to any real tactic.

        Position: the refuting move is a queen promotion that also forks two pieces.
        The fork detector (Tier 2) must win over promotion (Tier 5).
        """
        # 8/P7/2K5/8/3N4/8/4b1pk/8 b - - 2 66: pv = 'g2g1q d4e2 g1a7'
        # After g2g1q (black promotes to queen), then white Nd4-e2 (escaping), then
        # Qg1-a7 (black queen attacks white king via discovery). Currently returns None.
        # This position does NOT have a fork — it returns None currently (no real tactic).
        # Use a position where the promotion itself wins a piece (hence a fork-like pattern).
        # The CTcQ7 fixture: c7c8n forks rook and other piece, has fork + underPromotion themes.
        # Themes include fork, so real tactic (fork) must win over move-type.
        fen = "6r1/k1P5/7p/B2pp2Q/p3P3/P2P3P/2P2qr1/1R5K w - - 1 30"
        pv = "a5b6 f2b6 c7c8n g8c8 b1b6"
        motif_int, _piece, _conf, _depth = detect_tactic_motif(chess.Board(fen), pv)
        assert motif_int is not None
        # The real tactic (fork or another real motif) must win — NOT promotion/under-promotion
        assert _INT_TO_MOTIF[motif_int] not in MOVE_TYPE_MOTIFS, (
            f"expected a real tactic, got move-type '{_INT_TO_MOTIF.get(motif_int)}'"
        )

    def test_depth_primary_dispatch(self) -> None:
        """D-05/D-07: depth is the primary dispatch key (Phase 131 Plan 01 Task 2).

        Case 1 — shallowest wins: hanging-piece at depth 0 beats fork at depth 0 and
        trapped-piece at depth 4. When two motifs fire, the one at lesser depth wins;
        equal-depth ties break by tier then rank.

        Case 2 — equal-depth tiebreak: fork (Tier 2) and hanging-piece (Tier 4) both
        fire at depth 0 — fork wins via tier tiebreak (2 < 4). This is correct per D-07:
        when the fork IS at depth 0, it is equally shallow and more specific than the
        hanging capture.
        """
        # --- Case 1: hanging-piece depth 0 beats trapped-piece depth 4 ---
        # Black pov plays Rxe1 (depth 0), capturing the undefended White Bishop on e1.
        # hanging-piece fires at depth 0. Deeper in the PV (depth 4) the White Bishop f1
        # becomes trapped. Depth-primary dispatch returns hanging-piece (the shallower motif).
        fen_case1 = "1r2r1k1/p4ppp/8/6P1/2R2P2/1n5P/PP3P2/1K2BB1R b - - 0 26"
        pv_case1 = "e8e1 b1c2 e1c1 c2d3 b8d8"
        motif_int_1, _piece_1, _conf_1, depth_1 = detect_tactic_motif(
            chess.Board(fen_case1), pv_case1
        )
        assert motif_int_1 is not None
        assert _INT_TO_MOTIF[motif_int_1] == "hanging-piece", (
            f"Case 1: expected 'hanging-piece' (depth 0) to beat trapped-piece (depth 4) "
            f"under depth-primary dispatch (D-05), got '{_INT_TO_MOTIF.get(motif_int_1)}'"
        )
        assert depth_1 == 0, f"Case 1: expected depth 0, got {depth_1}"

        # --- Case 2: equal-depth — fork (Tier 2) beats hanging-piece (Tier 4) ---
        # White Knight on e5 captures the undefended Black Bishop on f7 (hanging-piece fires
        # at depth 0) and simultaneously attacks Black King h8 and Black Rook d6 (fork fires
        # at depth 0). Both fire at depth 0; tier tiebreak: fork (Tier 2) beats
        # hanging-piece (Tier 4).
        fen_case2 = "7k/5b2/3r4/4N3/8/8/8/4K3 w - - 0 1"
        pv_case2 = "e5f7 h8g8 f7d6"
        motif_int_2, _piece_2, _conf_2, depth_2 = detect_tactic_motif(
            chess.Board(fen_case2), pv_case2
        )
        assert motif_int_2 is not None
        assert _INT_TO_MOTIF[motif_int_2] == "fork", (
            f"Case 2: expected 'fork' (Tier 2) to beat 'hanging-piece' (Tier 4) at equal "
            f"depth 0 via tier tiebreak (D-05), got '{_INT_TO_MOTIF.get(motif_int_2)}'"
        )
        assert depth_2 == 0, f"Case 2: expected depth 0, got {depth_2}"


# NOTE (D-10, precision-first): this suite intentionally asserts ONLY precision +
# detector determinism. It NEVER gates recall ("found N of M tactics") — a missed
# detection is an accepted False Negative, never a test failure.


# === Workstream B: missed dest-square gate (D-03 / D-04) ===
#
# These fixtures validate the call-site gate in _detect_tactic_for_flaw (flaws_service.py):
# when the flaw move's destination square equals the best line's first-move destination
# square, the missed tactic is SUPPRESSED (the player demonstrably saw the target piece —
# they captured it with the wrong piece type).  A different destination means the player
# moved away entirely, so normal detection proceeds.
#
# These tests call _detect_tactic_for_flaw directly with hand-built (flaw_move, best_line)
# fixtures (D-04) — NOT the CC0 puzzle harness, which has no concept of "the move the
# player actually played".
#
# Test fixtures use SimpleNamespace to satisfy the positions[n].move_san / eval_mate
# duck-type without requiring a live DB session.


def test_missed_dest_sq_gate() -> None:
    """D-03 / D-04: suppress missed tactic when flaw dest == best-line first-move dest.

    Scenario: White Rook on d5 captures the undefended Black Rook on e5 (the flaw move
    — right target, wrong piece type).  The best line was Nxe5 (Knight f3 captures e5 for
    a stronger result).  Both flaw move and best PV first move go to e5, so the player
    demonstrably SAW the piece.  The missed-tactic tag should be SUPPRESSED.

    This test FAILS before Task 2 (the gate does not yet exist) because
    _detect_tactic_for_flaw returns the hanging-piece motif instead of (None, None, None, None).

    Edge case included: a non-capture flaw move (King to g2) that goes to a different square
    is the non-suppression path; see test_missed_no_suppression for that case.  Here we also
    verify the suppression holds even when the flaw move SAN is not a recapture of a piece
    owned by the opponent (the dest-square equality criterion is the ONLY criterion, D-03).
    """
    from types import SimpleNamespace

    from app.services.flaws_service import _detect_tactic_for_flaw

    # Position: White Rook d5, White Knight f3, White King f1,
    #           Black Rook e5 (unprotected), Black King g8.
    # board_fen (piece-placement only, no side-to-move — set via ply parity in the function).
    fen = "6k1/8/8/3Rr3/8/5N2/8/5K2"

    # n=0 (even ply → White to move)
    n = 0
    fen_map = {n: fen}

    # Flaw move: White Rook on d5 captures Black Rook on e5 — "Rxe5" in SAN.
    # move_san is the move the PLAYER actually played (the flaw).
    flaw_move_san = "Rxe5"

    # Best PV: f3e5 (Knight captures e5 — delivers the stronger result).
    # The first move of the PV also goes to e5 → same destination → SUPPRESS.
    best_pv = "f3e5"

    pos = SimpleNamespace(move_san=flaw_move_san, pv=None, eval_mate=None)
    positions = [pos]

    # Pass the PV via pv_by_ply so the function doesn't need positions[n].pv.
    result = _detect_tactic_for_flaw(
        n,
        fen_map,
        positions,  # ty: ignore[invalid-argument-type]  # SimpleNamespace duck-types GamePosition
        pv_by_ply={n: best_pv},
        orientation="missed",
    )

    assert result == (None, None, None, None), (
        f"Expected suppression (None, None, None, None) when flaw dest == best-line dest "
        f"(D-03 wrong-recapture gate), got {result!r}. "
        "This fails RED before the dest-square gate is added (Task 2)."
    )


def test_missed_no_suppression() -> None:
    """D-03 / D-04: normal detection proceeds when flaw dest != best-line first-move dest.

    Scenario: White Knight on f3 can capture the undefended Black Rook on e5 (the missed
    tactic).  Instead the player played Nd4 (Knight to d4) — a completely different square.
    Destinations differ (d4 vs e5), so the dest-square gate must NOT fire and normal
    detection should return the hanging-piece motif.

    This test passes both before and after the gate is added — it is a non-regression
    guard ensuring the gate does not cause false suppression when destinations differ.
    """
    from types import SimpleNamespace

    from app.services.flaws_service import _detect_tactic_for_flaw

    # Position: White Knight f3, White King f1,
    #           Black Rook e5 (unprotected), Black King g8.
    fen = "6k1/8/8/4r3/8/5N2/8/5K2"

    # n=0 (even ply → White to move)
    n = 0
    fen_map = {n: fen}

    # Flaw move: Nd4 — the Knight moves to d4 instead of capturing on e5.
    flaw_move_san = "Nd4"

    # Best PV: f3e5 (Knight captures e5, picking up the hanging rook).
    # Flaw dest (d4) != best-PV first dest (e5) → no suppression.
    best_pv = "f3e5"

    pos = SimpleNamespace(move_san=flaw_move_san, pv=None, eval_mate=None)
    positions = [pos]

    motif_int, piece, conf, depth = _detect_tactic_for_flaw(
        n,
        fen_map,
        positions,  # ty: ignore[invalid-argument-type]  # SimpleNamespace duck-types GamePosition
        pv_by_ply={n: best_pv},
        orientation="missed",
    )

    assert motif_int is not None, (
        "Expected a non-None motif when flaw dest (d4) != best-line dest (e5) — "
        "the dest-square gate must not suppress when destinations differ (D-03)."
    )
