# Blunder-check spot-check

Windows drawn the way the feature draws them (250 D-12): each slot is independently a herring (about 33%, all judged moves safe) or a blunder window, with length L uniform over 3 to 5 user moves. About 20 windows per Elo bucket, at most one per game, drawn with a fixed seed. A blunder window shows its facepalm score inputs after the answer.

Thresholds: facepalm score at least 0.7, eval band [0.10, 0.90] on the pre-move ES. A recommendation only; nothing here is wired into app code.

How to read: for each window, play through the lead-in and the judged moves on the board (the game link opens the game on FlawChess at the first judged move), decide whether the position is a fair question, then compare with the answer. A blunder window is fair when the refutation or the missed move is something a player of that rating could find. Moves are in SAN; a stored move that is not legal on the replayed board prints as its UCI with the word illegal.

### <800

#### Window 1: allowed (length 5, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=3227076&ply=4
- **User rating:** 706 (pinned Maia Elo 706)
- **FEN before the lead-in:** `r1bqkbnr/pppp1ppp/2n5/4p2Q/4P3/8/PPPP1PPP/RNB1KBNR w KQkq - 2 3`
- **Lead-in:** 3. Bc4
- **Judged user moves:**
  - 3... g6 (Good, pre-move ES 0.53), reply 4. Qf3
- **FEN before the answer move:** `r1bqkbnr/pppp1p1p/2n3p1/4p3/2B1P3/5Q2/PPPP1PPP/RNB1K1NR b KQkq - 1 4`
- **Answer:** blunder 4... Nd4 (pre-move ES 0.52, ES after 0.02).
- **Refutation:** Qxf7#.
- **Score inputs:** facepalm score 0.993, played prob 0.063, reply spread 1.50, played material 3 -1, mate ply 1.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.559, pre-blunder spread 5.87.

#### Window 2: allowed (length 5, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=3182764&ply=61
- **User rating:** 246 (pinned Maia Elo 600)
- **FEN before the lead-in:** `N7/R1R5/4k3/8/1P2p3/8/1q5P/5K2 b - - 1 31`
- **Lead-in:** 31... e3
- **Judged user moves:**
- **FEN before the answer move:** `N7/R1R5/4k3/8/1P6/4p3/1q5P/5K2 w - - 0 32`
- **Answer:** blunder 32. Ke1 (pre-move ES 0.50, ES after 0.02).
- **Refutation:** Qd2+.
- **Score inputs:** facepalm score 0.969, played prob 0.062, reply spread 9.34, played material 3 0, mate ply 3.
- **Missed inputs:** best material 3 5, missed gain 5, best move prob 0.004, pre-blunder spread 12.39.

#### Window 3: herring (length 4, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2047552&ply=16
- **User rating:** 564 (pinned Maia Elo 600)
- **FEN before the lead-in:** `r2qkb1r/ppp3pp/2n1b3/4pp2/4NP2/6P1/PPPP3P/R1BQK1NR w KQkq - 0 9`
- **Lead-in:** 9. Nc3
- **Judged user moves:**
  - 9... Bb4 (Good, pre-move ES 0.74), reply 10. Nb5
  - 10... a6 (Good, pre-move ES 0.72), reply 11. Nc3
  - 11... O-O (Good, pre-move ES 0.80), reply 12. Nge2
  - 12... Qf6 (Good, pre-move ES 0.76), reply 13. Na4
- **Answer:** all safe (every judged move is Good).

#### Window 4: allowed (length 5, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=1075362&ply=13
- **User rating:** 375 (pinned Maia Elo 600)
- **FEN before the lead-in:** `r1bqk2r/pppp1pbp/2n1p1p1/4P1Nn/2PP4/2N5/PP3PPP/R1BQKB1R b KQkq - 2 7`
- **Lead-in:** 7... O-O
- **Judged user moves:**
  - 8. g4 (Good, pre-move ES 0.73), reply 8... h6
- **FEN before the answer move:** `r1bq1rk1/pppp1pb1/2n1p1pp/4P1Nn/2PP2P1/2N5/PP3P1P/R1BQKB1R w KQ - 0 9`
- **Answer:** blunder 9. Nxf7 (pre-move ES 0.77, ES after 0.50).
- **Refutation:** Rxf7.
- **Score inputs:** facepalm score 0.872, played prob 0.033, reply spread 3.54, played material 3 -2, mate ply n/a.
- **Missed inputs:** best material 3 3, missed gain 3, best move prob 0.072, pre-blunder spread 7.04.

#### Window 5: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=1920483&ply=26
- **User rating:** 167 (pinned Maia Elo 600)
- **FEN before the lead-in:** `r1bq1rk1/ppp3p1/3p3p/3Pp1BQ/3bP3/P7/1PP2PPP/R4RK1 w - - 0 14`
- **Lead-in:** 14. Bxd8
- **Judged user moves:**
  - 14... Rxd8 (Good, pre-move ES 0.22), reply 15. Rfd1
  - 15... Bxb2 (Good, pre-move ES 0.24), reply 16. Rab1
  - 16... Bc3 (Good, pre-move ES 0.18), reply 17. Qf3
  - 17... Ba5 (Good, pre-move ES 0.23), reply 18. h3
  - 18... Rf8 (Good, pre-move ES 0.27), reply 19. Qb3
- **Answer:** all safe (every judged move is Good).

#### Window 6: allowed (length 3, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=1642279&ply=24
- **User rating:** 353 (pinned Maia Elo 600)
- **FEN before the lead-in:** `r1b1k2r/ppp3pp/3b1p2/3q4/4p3/3P2Q1/PP1N1PPP/nNB2K1R w kq - 0 13`
- **Lead-in:** 13. Qxg7
- **Judged user moves:**
- **FEN before the answer move:** `r1b1k2r/ppp3Qp/3b1p2/3q4/4p3/3P4/PP1N1PPP/nNB2K1R b kq - 0 13`
- **Answer:** blunder 13... Qf7 (pre-move ES 0.87, ES after 0.58).
- **Refutation:** Qxh8+.
- **Score inputs:** facepalm score 0.995, played prob 0.011, reply spread 2.51, played material 3 -6, mate ply n/a.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.208, pre-blunder spread 7.73.

#### Window 7: herring (length 3, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2274977&ply=19
- **User rating:** 222 (pinned Maia Elo 600)
- **FEN before the lead-in:** `r2q1rk1/ppp2ppp/3p1n2/4p3/N1BnP1b1/3PBP2/PPP3PP/R2Q1RK1 b - - 0 10`
- **Lead-in:** 10... Nxf3+
- **Judged user moves:**
  - 11. gxf3 (Good, pre-move ES 0.73), reply 11... Bh3
  - 12. Re1 (Good, pre-move ES 0.73), reply 12... Nxe4
  - 13. fxe4 (Good, pre-move ES 0.83), reply 13... c6
- **Answer:** all safe (every judged move is Good).

#### Window 8: allowed (length 5, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=3182438&ply=20
- **User rating:** 254 (pinned Maia Elo 600)
- **FEN before the lead-in:** `r2qk1nr/pbp3pp/1p2p3/3nP3/3P4/3B4/PP3PPP/RN1QK1NR w KQkq - 4 11`
- **Lead-in:** 11. Qh5+
- **Judged user moves:**
  - 11... g6 (Good, pre-move ES 0.37), reply 12. Bxg6+
  - 12... hxg6 (Good, pre-move ES 0.32), reply 13. Qxh8
- **FEN before the answer move:** `r2qk1nQ/pbp5/1p2p1p1/3nP3/3P4/8/PP3PPP/RN2K1NR b KQq - 0 13`
- **Answer:** blunder 13... Qd7 (pre-move ES 0.28, ES after 0.11).
- **Refutation:** Qxg8+.
- **Score inputs:** facepalm score 0.966, played prob 0.022, reply spread 1.43, played material 3 -3, mate ply n/a.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.094, pre-blunder spread 12.39.

#### Window 9: allowed (length 3, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=2607361&ply=38
- **User rating:** 450 (pinned Maia Elo 600)
- **FEN before the lead-in:** `4qrk1/pr2nppp/4p3/2Q5/8/2B1PP2/PPPR1P1P/6K1 w - - 0 20`
- **Lead-in:** 20. b4
- **Judged user moves:**
  - 20... Rb8 (Good, pre-move ES 0.86), reply 21. Qxa7
  - 21... Ra8 (Good, pre-move ES 0.84), reply 22. Qd4
- **FEN before the answer move:** `r3qrk1/4nppp/4p3/8/1P1Q4/2B1PP2/P1PR1P1P/6K1 b - - 2 22`
- **Answer:** blunder 22... Rxa2 (pre-move ES 0.83, ES after 0.02).
- **Refutation:** Qxg7#.
- **Score inputs:** facepalm score 0.972, played prob 0.375, reply spread 4.47, played material 3 0, mate ply 1.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.086, pre-blunder spread 8.55.

#### Window 10: allowed (length 5, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=1918374&ply=10
- **User rating:** 137 (pinned Maia Elo 600)
- **FEN before the lead-in:** `r1bqkb1r/ppp2p1p/2np1np1/4p3/2B1P3/3P1Q2/PPP2PPP/RNB1K1NR w KQkq - 0 6`
- **Lead-in:** 6. Nc3
- **Judged user moves:**
  - 6... Be6 (Good, pre-move ES 0.55), reply 7. Nd5
- **FEN before the answer move:** `r2qkb1r/ppp2p1p/2npbnp1/3Np3/2B1P3/3P1Q2/PPP2PPP/R1B1K1NR b KQkq - 3 7`
- **Answer:** blunder 7... a6 (pre-move ES 0.56, ES after 0.14).
- **Refutation:** Nxf6+.
- **Score inputs:** facepalm score 0.935, played prob 0.023, reply spread 3.95, played material 3 -3, mate ply n/a.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.118, pre-blunder spread 10.37.

#### Window 11: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=1596863&ply=1
- **User rating:** 278 (pinned Maia Elo 600)
- **FEN before the lead-in:** `rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1`
- **Lead-in:** 1... e5
- **Judged user moves:**
  - 2. Nf3 (Good, pre-move ES 0.53), reply 2... d6
  - 3. Bc4 (Good, pre-move ES 0.56), reply 3... Be6
  - 4. d3 (Good, pre-move ES 0.57), reply 4... d5
  - 5. exd5 (Good, pre-move ES 0.64), reply 5... Bxd5
  - 6. Nxe5 (Good, pre-move ES 0.64), reply 6... Bxc4
- **Answer:** all safe (every judged move is Good).

#### Window 12: mixed (length 4, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=1597465&ply=24
- **User rating:** 268 (pinned Maia Elo 600)
- **FEN before the lead-in:** `r2q1rk1/ppp2ppp/3p4/1Nb1p3/2P1P1b1/5N2/PPP1QP2/R1B2RK1 w - - 0 13`
- **Lead-in:** 13. Qd2
- **Judged user moves:**
- **FEN before the answer move:** `r2q1rk1/ppp2ppp/3p4/1Nb1p3/2P1P1b1/5N2/PPPQ1P2/R1B2RK1 b - - 1 13`
- **Answer:** blunder 13... d5 (pre-move ES 0.86, ES after 0.38).
- **Refutation:** Nxe5.
- **Missed best move:** Bxf3.
- **Score inputs:** facepalm score 0.741, played prob 0.004, reply spread 10.97, played material 3 0, mate ply n/a.
- **Missed inputs:** best material 3 3, missed gain 3, best move prob 0.799, pre-blunder spread 2.75.

#### Window 13: allowed (length 5, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=3081322&ply=24
- **User rating:** 670 (pinned Maia Elo 670)
- **FEN before the lead-in:** `r2q1rk1/ppp2ppp/4bn2/bPp1p3/4P3/2P2P1N/P2B2PP/R2QKB1R w KQ - 0 13`
- **Lead-in:** 13. Ng5
- **Judged user moves:**
- **FEN before the answer move:** `r2q1rk1/ppp2ppp/4bn2/bPp1p1N1/4P3/2P2P2/P2B2PP/R2QKB1R b KQ - 1 13`
- **Answer:** blunder 13... Bxc3 (pre-move ES 0.71, ES after 0.26).
- **Refutation:** Bxc3.
- **Score inputs:** facepalm score 0.893, played prob 0.022, reply spread 2.24, played material 3 -2, mate ply n/a.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.176, pre-blunder spread 14.00.

#### Window 14: mixed (length 4, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=3243656&ply=36
- **User rating:** 403 (pinned Maia Elo 600)
- **FEN before the lead-in:** `r1b3k1/pp1r1pp1/3p3p/3P4/2B2B2/1P6/P1P2PPP/4R1K1 w - - 0 19`
- **Lead-in:** 19. Bd3
- **Judged user moves:**
  - 19... Rd8 (Good, pre-move ES 0.39), reply 20. Bxd6
- **FEN before the answer move:** `r1br2k1/pp3pp1/3B3p/3P4/8/1P1B4/P1P2PPP/4R1K1 b - - 0 20`
- **Answer:** blunder 20... Rxd6 (pre-move ES 0.51, ES after 0.02).
- **Refutation:** Re8#.
- **Missed best move:** Bg4.
- **Score inputs:** facepalm score 0.975, played prob 0.875, reply spread 2.02, played material 3 3, mate ply 1.
- **Missed inputs:** best material 3 1, missed gain -2, best move prob 0.038, pre-blunder spread 1.89.

#### Window 15: allowed (length 5, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=2253932&ply=21
- **User rating:** 496 (pinned Maia Elo 600)
- **FEN before the lead-in:** `r2qk1nr/p3ppbp/2p3p1/3pP3/8/2N5/PPP1QPPP/R1B2RK1 b kq - 3 11`
- **Lead-in:** 11... e6
- **Judged user moves:**
- **FEN before the answer move:** `r2qk1nr/p4pbp/2p1p1p1/3pP3/8/2N5/PPP1QPPP/R1B2RK1 w kq - 0 12`
- **Answer:** blunder 12. Qe3 (pre-move ES 0.48, ES after 0.30).
- **Refutation:** d4.
- **Score inputs:** facepalm score 0.765, played prob 0.014, reply spread 6.30, played material 3 -2, mate ply n/a.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.023, pre-blunder spread 15.17.

#### Window 16: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=1870316&ply=1
- **User rating:** 741 (pinned Maia Elo 741)
- **FEN before the lead-in:** `rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1`
- **Lead-in:** 1... e5
- **Judged user moves:**
  - 2. Nc3 (Good, pre-move ES 0.52), reply 2... Nf6
  - 3. Nf3 (Good, pre-move ES 0.50), reply 3... Nc6
  - 4. Bc4 (Good, pre-move ES 0.51), reply 4... Bb4
  - 5. a3 (Good, pre-move ES 0.52), reply 5... Bxc3
  - 6. bxc3 (Good, pre-move ES 0.52), reply 6... Nxe4
- **Answer:** all safe (every judged move is Good).

#### Window 17: herring (length 3, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=3173861&ply=72
- **User rating:** 725 (pinned Maia Elo 725)
- **FEN before the lead-in:** `8/p2B2pp/r3p3/2k2p2/8/4b1PK/7P/1R6 w - - 0 37`
- **Lead-in:** 37. Rb5+
- **Judged user moves:**
  - 37... Kd4 (Good, pre-move ES 0.85), reply 38. Rb4+
  - 38... Kc5 (Good, pre-move ES 0.84), reply 39. Rb5+
  - 39... Kd6 (Good, pre-move ES 0.85), reply 40. Be8
- **Answer:** all safe (every judged move is Good).

#### Window 18: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2447370&ply=11
- **User rating:** 658 (pinned Maia Elo 658)
- **FEN before the lead-in:** `r1bqkbnr/pp1p2pp/2p2p2/3Pp3/1nB1P3/2N2N2/PPP2PPP/R1BQK2R b KQkq - 1 6`
- **Lead-in:** 6... b5
- **Judged user moves:**
  - 7. Bb3 (Good, pre-move ES 0.69), reply 7... Ne7
  - 8. a3 (Good, pre-move ES 0.78), reply 8... Na6
  - 9. O-O (Good, pre-move ES 0.75), reply 9... Nc5
  - 10. Ba2 (Good, pre-move ES 0.71), reply 10... Rb8
  - 11. b4 (Good, pre-move ES 0.77), reply 11... Na6
- **Answer:** all safe (every judged move is Good).

#### Window 19: allowed (length 4, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=2785732&ply=60
- **User rating:** 475 (pinned Maia Elo 600)
- **FEN before the lead-in:** `2r3k1/5pp1/1P2pn1p/2p5/1r6/8/5PPP/1RB2RK1 w - - 1 31`
- **Lead-in:** 31. Ba3
- **Judged user moves:**
  - 31... Rxb1 (Good, pre-move ES 0.53), reply 32. Rxb1
  - 32... Rb8 (Good, pre-move ES 0.52), reply 33. b7
- **FEN before the answer move:** `1r4k1/1P3pp1/4pn1p/2p5/8/B7/5PPP/1R4K1 b - - 0 33`
- **Answer:** blunder 33... c4 (pre-move ES 0.54, ES after 0.13).
- **Refutation:** Bd6.
- **Score inputs:** facepalm score 0.952, played prob 0.357, reply spread 2.82, played material 3 -4, mate ply n/a.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.296, pre-blunder spread 5.38.

#### Window 20: allowed (length 3, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=1405351&ply=27
- **User rating:** 233 (pinned Maia Elo 600)
- **FEN before the lead-in:** `2rk3r/pp3ppp/5n2/2b5/2p1PBN1/8/PPP3PP/R3KB1R b KQ - 0 14`
- **Lead-in:** 14... Nxg4
- **Judged user moves:**
  - 15. O-O-O+ (Good, pre-move ES 0.49), reply 15... Ke8
  - 16. Bxc4 (Good, pre-move ES 0.63), reply 16... Nf2
- **FEN before the answer move:** `2r1k2r/pp3ppp/8/2b5/2B1PB2/8/PPP2nPP/2KR3R w - - 1 17`
- **Answer:** blunder 17. Rhf1 (pre-move ES 0.68, ES after 0.48).
- **Refutation:** Nxd1.
- **Score inputs:** facepalm score 0.831, played prob 0.161, reply spread 1.91, played material 3 -2, mate ply n/a.
- **Missed inputs:** best material 3 1, missed gain 1, best move prob 0.288, pre-blunder spread 11.75.

### 800-1199

#### Window 1: allowed (length 3, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=2744876&ply=66
- **User rating:** 573 (pinned Maia Elo 1063)
- **FEN before the lead-in:** `3r2k1/R4ppp/1p2p3/8/7q/5P2/6P1/3Q2K1 w - - 2 34`
- **Lead-in:** 34. Qc1
- **Judged user moves:**
  - 34... Qd4+ (Good, pre-move ES 0.86), reply 35. Kh2
- **FEN before the answer move:** `3r2k1/R4ppp/1p2p3/8/3q4/5P2/6PK/2Q5 b - - 5 35`
- **Answer:** blunder 35... Qd1 (pre-move ES 0.86, ES after 0.11).
- **Refutation:** Qxd1.
- **Score inputs:** facepalm score 0.995, played prob 0.010, reply spread 2.82, played material 3 -9, mate ply n/a.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.232, pre-blunder spread 8.13.

#### Window 2: herring (length 3, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2900926&ply=1
- **User rating:** 1171 (pinned Maia Elo 1171)
- **FEN before the lead-in:** `rnbqkbnr/pppppppp/8/8/3P4/8/PPP1PPPP/RNBQKBNR b KQkq - 0 1`
- **Lead-in:** 1... d5
- **Judged user moves:**
  - 2. Nf3 (Good, pre-move ES 0.53), reply 2... e6
  - 3. e3 (Good, pre-move ES 0.52), reply 3... Bb4+
  - 4. c3 (Good, pre-move ES 0.54), reply 4... Bd6
- **Answer:** all safe (every judged move is Good).

#### Window 3: allowed (length 4, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=1079920&ply=68
- **User rating:** 668 (pinned Maia Elo 1123)
- **FEN before the lead-in:** `r4r2/2Q3pk/p4p2/1p5p/1P1PpNb1/PKq5/2P5/R2n1B2 w - - 8 35`
- **Lead-in:** 35. Qxc3
- **Judged user moves:**
  - 35... Nxc3 (Good, pre-move ES 0.87), reply 36. Kxc3
  - 36... Rac8+ (Good, pre-move ES 0.87), reply 37. Kb3
- **FEN before the answer move:** `2r2r2/6pk/p4p2/1p5p/1P1PpNb1/PK6/2P5/R4B2 b - - 2 37`
- **Answer:** blunder 37... Be2 (pre-move ES 0.88, ES after 0.50).
- **Refutation:** unknown.
- **Score inputs:** facepalm score 0.978, played prob 0.000, reply spread 1.56, played material 3 -3, mate ply n/a.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.358, pre-blunder spread 9.18.

#### Window 4: mixed (length 5, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=2866196&ply=38
- **User rating:** 810 (pinned Maia Elo 1064)
- **FEN before the lead-in:** `r4rk1/p4p2/Q2N1p1p/3pn3/8/2PP2P1/PP1Nq2P/2KR3R w - - 0 20`
- **Lead-in:** 20. Nf5
- **Judged user moves:**
  - 20... Nxd3+ (Good, pre-move ES 0.12), reply 21. Kc2
- **FEN before the answer move:** `r4rk1/p4p2/Q4p1p/3p1N2/8/2Pn2P1/PPKNq2P/3R3R b - - 1 21`
- **Answer:** blunder 21... Nc5 (pre-move ES 0.83, ES after 0.03).
- **Refutation:** Qxe2.
- **Missed best move:** Nb4+.
- **Score inputs:** facepalm score 0.994, played prob 0.051, reply spread 3.02, played material 3 -10, mate ply n/a.
- **Missed inputs:** best material 3 6, missed gain 5, best move prob 0.371, pre-blunder spread 9.70.

#### Window 5: allowed (length 4, blunder at 4)

- **Game:** https://flawchess.com/analysis?game_id=1079119&ply=29
- **User rating:** 730 (pinned Maia Elo 1162)
- **FEN before the lead-in:** `rnbqr1k1/pp1n2pp/8/3pP3/P2P4/B5P1/7P/R2QKBNR b KQ - 0 15`
- **Lead-in:** 15... Nc6
- **Judged user moves:**
  - 16. Nf3 (Good, pre-move ES 0.49), reply 16... Ncxe5
  - 17. dxe5 (Good, pre-move ES 0.58), reply 17... Nxe5
  - 18. Nxe5 (Good, pre-move ES 0.57), reply 18... Rxe5+
- **FEN before the answer move:** `r1bq2k1/pp4pp/8/3pr3/P7/B5P1/7P/R2QKB1R w KQ - 0 19`
- **Answer:** blunder 19. Be2 (pre-move ES 0.60, ES after 0.34).
- **Refutation:** Bg4.
- **Score inputs:** facepalm score 0.713, played prob 0.768, reply spread 5.71, played material 3 -3, mate ply n/a.
- **Missed inputs:** best material 3 n/a, missed gain n/a, best move prob 0.200, pre-blunder spread 1.91.

#### Window 6: allowed (length 3, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=2739861&ply=103
- **User rating:** 1500 (pinned Maia Elo 1149)
- **FEN before the lead-in:** `8/p3b2p/k1p3p1/8/8/1R5P/PPP2r2/R1K5 b - - 7 52`
- **Lead-in:** 52... Bd6
- **Judged user moves:**
  - 53. Kd1 (Good, pre-move ES 0.19), reply 53... h5
  - 54. Ke1 (Good, pre-move ES 0.67), reply 54... Bc5
- **FEN before the answer move:** `8/p7/k1p3p1/2b4p/8/1R5P/PPP2r2/R3K3 w - - 2 55`
- **Answer:** blunder 55. Kd1 (pre-move ES 0.67, ES after 0.15).
- **Refutation:** Rf1+.
- **Score inputs:** facepalm score 0.992, played prob 0.031, reply spread 2.86, played material 3 -5, mate ply n/a.
- **Missed inputs:** best material 3 -1, missed gain -1, best move prob 0.022, pre-blunder spread 6.88.

#### Window 7: herring (length 4, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=3233892&ply=25
- **User rating:** 1500 (pinned Maia Elo 1149)
- **FEN before the lead-in:** `r2qk2r/p3bppp/2p1p1n1/3pP3/3p4/7P/PPPN1PPB/R2Q1RK1 b kq - 7 13`
- **Lead-in:** 13... O-O
- **Judged user moves:**
  - 14. Nf3 (Good, pre-move ES 0.34), reply 14... c5
  - 15. c3 (Good, pre-move ES 0.32), reply 15... dxc3
  - 16. bxc3 (Good, pre-move ES 0.29), reply 16... Qa5
  - 17. Qc2 (Good, pre-move ES 0.29), reply 17... Rab8
- **Answer:** all safe (every judged move is Good).

#### Window 8: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2832675&ply=23
- **User rating:** 978 (pinned Maia Elo 1165)
- **FEN before the lead-in:** `r2q1rk1/p1p2p1p/2p2np1/2Pp1b2/3P4/P1Q1P3/1P3PPP/R1B1KB1R b KQ - 0 12`
- **Lead-in:** 12... Rb8
- **Judged user moves:**
  - 13. Bd3 (Good, pre-move ES 0.67), reply 13... Qd7
  - 14. O-O (Good, pre-move ES 0.63), reply 14... Rfe8
  - 15. Qc2 (Good, pre-move ES 0.62), reply 15... Bxd3
  - 16. Qxd3 (Good, pre-move ES 0.59), reply 16... Kg7
  - 17. b4 (Good, pre-move ES 0.61), reply 17... Qe6
- **Answer:** all safe (every judged move is Good).

#### Window 9: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2863789&ply=13
- **User rating:** 927 (pinned Maia Elo 1134)
- **FEN before the lead-in:** `r1bq1rk1/pppp1ppp/1bn2n2/4p3/1PB1P3/P1PP1N2/5PPP/RNBQK2R b KQ - 0 7`
- **Lead-in:** 7... a5
- **Judged user moves:**
  - 8. b5 (Good, pre-move ES 0.45), reply 8... Ne7
  - 9. Bg5 (Good, pre-move ES 0.46), reply 9... Ng6
  - 10. Bxf6 (Good, pre-move ES 0.42), reply 10... Qxf6
  - 11. O-O (Good, pre-move ES 0.38), reply 11... c6
  - 12. Nbd2 (Good, pre-move ES 0.41), reply 12... Nf4
- **Answer:** all safe (every judged move is Good).

#### Window 10: herring (length 4, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2864938&ply=1
- **User rating:** 895 (pinned Maia Elo 1114)
- **FEN before the lead-in:** `rnbqkbnr/pppppppp/8/8/3P4/8/PPP1PPPP/RNBQKBNR b KQkq - 0 1`
- **Lead-in:** 1... d5
- **Judged user moves:**
  - 2. Bf4 (Good, pre-move ES 0.53), reply 2... Nc6
  - 3. e3 (Good, pre-move ES 0.54), reply 3... Nf6
  - 4. Nf3 (Good, pre-move ES 0.54), reply 4... Bg4
  - 5. Bd3 (Good, pre-move ES 0.53), reply 5... Bxf3
- **Answer:** all safe (every judged move is Good).

#### Window 11: mixed (length 3, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=1830139&ply=61
- **User rating:** 588 (pinned Maia Elo 1070)
- **FEN before the lead-in:** `5rk1/5p1p/1p2p1p1/4Q3/p3P2K/6P1/2P4P/5b2 b - - 1 31`
- **Lead-in:** 31... f6
- **Judged user moves:**
- **FEN before the answer move:** `5rk1/7p/1p2ppp1/4Q3/p3P2K/6P1/2P4P/5b2 w - - 0 32`
- **Answer:** blunder 32. Qf4 (pre-move ES 0.65, ES after 0.04).
- **Refutation:** g5+.
- **Missed best move:** Qxe6+.
- **Score inputs:** facepalm score 0.988, played prob 0.019, reply spread 5.19, played material 3 -8, mate ply n/a.
- **Missed inputs:** best material 3 n/a, missed gain n/a, best move prob 0.866, pre-blunder spread 2.01.

#### Window 12: herring (length 3, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2960817&ply=42
- **User rating:** 1197 (pinned Maia Elo 1197)
- **FEN before the lead-in:** `3r1rk1/1pp3pp/p3p3/5p2/3P3P/P4N2/1Pn2PP1/R4RK1 w - - 1 22`
- **Lead-in:** 22. Rac1
- **Judged user moves:**
  - 22... Nxd4 (Good, pre-move ES 0.51), reply 23. Nxd4
  - 23... Rxd4 (Good, pre-move ES 0.51), reply 24. Rxc7
  - 24... Rxh4 (Good, pre-move ES 0.52), reply 25. f3
- **Answer:** all safe (every judged move is Good).

#### Window 13: pure_miss (length 4, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=2607000&ply=37
- **User rating:** 678 (pinned Maia Elo 1130)
- **FEN before the lead-in:** `r1b1k1nr/5pp1/p2qp2p/1pp5/8/P2P2P1/BPPQ1PP1/R4RK1 b kq - 0 19`
- **Lead-in:** 19... Nf6
- **Judged user moves:**
  - 20. Qf4 (Good, pre-move ES 0.17), reply 20... e5
  - 21. Qf3 (Good, pre-move ES 0.20), reply 21... O-O
- **FEN before the answer move:** `r1b2rk1/5pp1/p2q1n1p/1pp1p3/8/P2P1QP1/BPP2PP1/R4RK1 w - - 2 22`
- **Answer:** blunder 22. Rad1 (pre-move ES 0.67, ES after 0.12).
- **Missed best move:** Qxa8.
- **Score inputs:** facepalm score 0.835, played prob 0.044, reply spread 5.03, played material 3 -2, mate ply n/a.
- **Missed inputs:** best material 3 5, missed gain 5, best move prob 0.674, pre-blunder spread 3.80.

#### Window 14: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=3069284&ply=17
- **User rating:** 999 (pinned Maia Elo 1178)
- **FEN before the lead-in:** `r3kb1r/Np1qpppp/2p5/1B1p1bn1/3P4/2N1P3/PPP2PPP/R2QK2R b KQkq - 1 9`
- **Lead-in:** 9... Rxa7
- **Judged user moves:**
  - 10. Bd3 (Good, pre-move ES 0.18), reply 10... g6
  - 11. f4 (Good, pre-move ES 0.20), reply 11... Ne4
  - 12. h3 (Good, pre-move ES 0.21), reply 12... Ng3
  - 13. Qf3 (Good, pre-move ES 0.16), reply 13... Nxh1
  - 14. O-O-O (Good, pre-move ES 0.16), reply 14... e6
- **Answer:** all safe (every judged move is Good).

#### Window 15: allowed (length 4, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=2881484&ply=15
- **User rating:** 1103 (pinned Maia Elo 1103)
- **FEN before the lead-in:** `r1bq1rk1/ppp1bppp/2n1pn2/8/2QP4/5NP1/PP2PPBP/RNB2RK1 b - - 0 8`
- **Lead-in:** 8... Na5
- **Judged user moves:**
- **FEN before the answer move:** `r1bq1rk1/ppp1bppp/4pn2/n7/2QP4/5NP1/PP2PPBP/RNB2RK1 w - - 1 9`
- **Answer:** blunder 9. Qb3 (pre-move ES 0.56, ES after 0.11).
- **Refutation:** Nxb3.
- **Score inputs:** facepalm score 0.997, played prob 0.002, reply spread 1.44, played material 3 -6, mate ply n/a.
- **Missed inputs:** best material 3 n/a, missed gain n/a, best move prob 0.341, pre-blunder spread 4.50.

#### Window 16: allowed (length 5, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=1651573&ply=1
- **User rating:** 565 (pinned Maia Elo 1102)
- **FEN before the lead-in:** `rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1`
- **Lead-in:** 1... e5
- **Judged user moves:**
  - 2. Nf3 (Good, pre-move ES 0.53), reply 2... Nc6
  - 3. Bc4 (Good, pre-move ES 0.53), reply 3... Qf6
- **FEN before the answer move:** `r1b1kbnr/pppp1ppp/2n2q2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4`
- **Answer:** blunder 4. Ng5 (pre-move ES 0.62, ES after 0.22).
- **Refutation:** Qxg5.
- **Score inputs:** facepalm score 0.956, played prob 0.006, reply spread 3.48, played material 3 -3, mate ply n/a.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.198, pre-blunder spread 5.03.

#### Window 17: herring (length 3, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2854630&ply=46
- **User rating:** 776 (pinned Maia Elo 1048)
- **FEN before the lead-in:** `2r2rk1/R4p1p/3p2p1/1q1P3n/1pp1P3/1B3P2/1P2Q1PP/5RK1 w - - 1 24`
- **Lead-in:** 24. g3
- **Judged user moves:**
  - 24... Qb6+ (Good, pre-move ES 0.81), reply 25. Qf2
  - 25... Qxf2+ (Good, pre-move ES 0.79), reply 26. Kxf2
  - 26... cxb3 (Good, pre-move ES 0.81), reply 27. Rb7
- **Answer:** all safe (every judged move is Good).

#### Window 18: allowed (length 3, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=2427060&ply=18
- **User rating:** 790 (pinned Maia Elo 1055)
- **FEN before the lead-in:** `r1bq2k1/ppp2rp1/2n4p/2bnp3/2B5/2PP1Q2/PP3PPP/RNB1K2R w KQ - 0 10`
- **Lead-in:** 10. Bxd5
- **Judged user moves:**
  - 10... Bxf2+ (Good, pre-move ES 0.24), reply 11. Kf1
- **FEN before the answer move:** `r1bq2k1/ppp2rp1/2n4p/3Bp3/8/2PP1Q2/PP3bPP/RNB2K1R b - - 1 11`
- **Answer:** blunder 11... Be6 (pre-move ES 0.33, ES after 0.12).
- **Refutation:** Bxe6.
- **Score inputs:** facepalm score 0.987, played prob 0.108, reply spread 2.54, played material 3 -8, mate ply n/a.
- **Missed inputs:** best material 3 -2, missed gain -2, best move prob 0.409, pre-blunder spread 9.97.

#### Window 19: herring (length 4, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2544895&ply=1
- **User rating:** 792 (pinned Maia Elo 1196)
- **FEN before the lead-in:** `rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1`
- **Lead-in:** 1... e5
- **Judged user moves:**
  - 2. Nf3 (Good, pre-move ES 0.53), reply 2... d6
  - 3. d4 (Good, pre-move ES 0.56), reply 3... Bg4
  - 4. h3 (Good, pre-move ES 0.60), reply 4... Bh5
  - 5. Be2 (Good, pre-move ES 0.61), reply 5... Nc6
- **Answer:** all safe (every judged move is Good).

#### Window 20: allowed (length 3, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=1329594&ply=14
- **User rating:** 974 (pinned Maia Elo 974)
- **FEN before the lead-in:** `rn2kbnr/p1p1qppp/1p6/3b4/8/5N2/PPPPNPPP/R1BQK2R w KQkq - 0 8`
- **Lead-in:** 8. O-O
- **Judged user moves:**
  - 8... Bxf3 (Good, pre-move ES 0.81), reply 9. gxf3
  - 9... Nf6 (Good, pre-move ES 0.81), reply 10. Nd4
- **FEN before the answer move:** `rn2kb1r/p1p1qppp/1p3n2/8/3N4/5P2/PPPP1P1P/R1BQ1RK1 b kq - 2 10`
- **Answer:** blunder 10... Nd5 (pre-move ES 0.84, ES after 0.21).
- **Refutation:** Re1.
- **Score inputs:** facepalm score 0.971, played prob 0.059, reply spread 3.49, played material 3 -4, mate ply n/a.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.084, pre-blunder spread 12.71.

### 1200-1599

#### Window 1: allowed (length 5, blunder at 5)

- **Game:** https://flawchess.com/analysis?game_id=682800&ply=29
- **User rating:** 1384 (pinned Maia Elo 1544)
- **FEN before the lead-in:** `rnb2rk1/p1p4p/1p2p1p1/4P3/3p1P2/4P1q1/PPPKN1P1/R2Q1B1R b - - 1 15`
- **Lead-in:** 15... Qxe3+
- **Judged user moves:**
  - 16. Ke1 (Good, pre-move ES 0.23), reply 16... Ba6
  - 17. Qxd4 (Good, pre-move ES 0.62), reply 17... Qxd4
  - 18. Nxd4 (Good, pre-move ES 0.60), reply 18... Rxf4
  - 19. Nxe6 (Good, pre-move ES 0.64), reply 19... Re4+
- **FEN before the answer move:** `rn4k1/p1p4p/bp2N1p1/4P3/4r3/8/PPP3P1/R3KB1R w - - 1 20`
- **Answer:** blunder 20. Kd1 (pre-move ES 0.67, ES after 0.29).
- **Refutation:** Bxf1.
- **Score inputs:** facepalm score 0.943, played prob 0.087, reply spread 2.70, played material 3 -3, mate ply n/a.
- **Missed inputs:** best material 3 3, missed gain 3, best move prob 0.273, pre-blunder spread 2.52.

#### Window 2: mixed (length 5, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=867320&ply=46
- **User rating:** 1349 (pinned Maia Elo 1507)
- **FEN before the lead-in:** `r5k1/ppp2p1p/2bp2p1/2q4r/4BQ2/1P5P/P4PP1/4RRK1 w - - 0 24`
- **Lead-in:** 24. Bxc6
- **Judged user moves:**
  - 24... Qxc6 (Good, pre-move ES 0.63), reply 25. Re7
  - 25... Rf5 (Good, pre-move ES 0.62), reply 26. Qc4
- **FEN before the answer move:** `r5k1/ppp1Rp1p/2qp2p1/5r2/2Q5/1P5P/P4PP1/5RK1 b - - 3 26`
- **Answer:** blunder 26... Rc5 (pre-move ES 0.82, ES after 0.02).
- **Refutation:** Qxf7+.
- **Missed best move:** Qxc4.
- **Score inputs:** facepalm score 0.992, played prob 0.135, reply spread 1.18, played material 3 -2, mate ply 3.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.706, pre-blunder spread 3.10.

#### Window 3: herring (length 3, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=1550805&ply=7
- **User rating:** 1576 (pinned Maia Elo 1576)
- **FEN before the lead-in:** `rnbqk1nr/ppp2ppp/4p3/3p4/1bPP4/2N2N2/PP2PPPP/R1BQKB1R b KQkq - 3 4`
- **Lead-in:** 4... Bxc3+
- **Judged user moves:**
  - 5. bxc3 (Good, pre-move ES 0.56), reply 5... c6
  - 6. cxd5 (Good, pre-move ES 0.57), reply 6... cxd5
  - 7. Bg5 (Good, pre-move ES 0.56), reply 7... f6
- **Answer:** all safe (every judged move is Good).

#### Window 4: herring (length 4, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=3254278&ply=8
- **User rating:** 858 (pinned Maia Elo 1278)
- **FEN before the lead-in:** `r1bqk1nr/pp1pppbp/2n3p1/2p5/2B1P3/2PP4/PP3PPP/RNBQK1NR w KQkq - 1 5`
- **Lead-in:** 5. Nf3
- **Judged user moves:**
  - 5... e6 (Good, pre-move ES 0.51), reply 6. a4
  - 6... d5 (Good, pre-move ES 0.53), reply 7. exd5
  - 7... exd5 (Good, pre-move ES 0.54), reply 8. Ba2
  - 8... Nf6 (Good, pre-move ES 0.55), reply 9. O-O
- **Answer:** all safe (every judged move is Good).

#### Window 5: herring (length 3, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2742151&ply=58
- **User rating:** 1368 (pinned Maia Elo 1528)
- **FEN before the lead-in:** `r1r5/pp1b2Q1/4ppP1/3k4/8/qPb1PN2/PNP4P/1K5n w - - 0 30`
- **Lead-in:** 30. Qxd7+
- **Judged user moves:**
  - 30... Ke4 (Good, pre-move ES 0.71), reply 31. Nd2+
  - 31... Kf5 (Good, pre-move ES 0.69), reply 32. Qd3+
  - 32... Kg5 (Good, pre-move ES 0.75), reply 33. Nf3+
- **Answer:** all safe (every judged move is Good).

#### Window 6: allowed (length 4, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=2112131&ply=16
- **User rating:** 921 (pinned Maia Elo 1353)
- **FEN before the lead-in:** `r2qk2r/pbpnppbp/1p3np1/3p4/4P3/2NPBN1P/PPP1BPP1/R2QK2R w KQkq - 0 9`
- **Lead-in:** 9. e5
- **Judged user moves:**
- **FEN before the answer move:** `r2qk2r/pbpnppbp/1p3np1/3pP3/8/2NPBN1P/PPP1BPP1/R2QK2R b KQkq - 0 9`
- **Answer:** blunder 9... d4 (pre-move ES 0.47, ES after 0.21).
- **Refutation:** exf6.
- **Score inputs:** facepalm score 0.857, played prob 0.046, reply spread 2.60, played material 3 -2, mate ply n/a.
- **Missed inputs:** best material 3 n/a, missed gain n/a, best move prob 0.089, pre-blunder spread 3.28.

#### Window 7: allowed (length 4, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=2337315&ply=68
- **User rating:** 1206 (pinned Maia Elo 1206)
- **FEN before the lead-in:** `8/3N1p2/2p4k/3p1Qn1/pp3b2/1Pq5/P1P3P1/1K1R4 w - - 0 35`
- **Lead-in:** 35. Rh1+
- **Judged user moves:**
  - 35... Kg7 (Good, pre-move ES 0.10), reply 36. Qxf4
- **FEN before the answer move:** `8/3N1pk1/2p5/3p2n1/pp3Q2/1Pq5/P1P3P1/1K5R b - - 0 36`
- **Answer:** blunder 36... a3 (pre-move ES 0.12, ES after 0.02).
- **Refutation:** Qxg5#.
- **Score inputs:** facepalm score 0.982, played prob 0.501, reply spread 2.34, played material 3 -3, mate ply 1.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.163, pre-blunder spread 4.74.

#### Window 8: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2680500&ply=1
- **User rating:** 1331 (pinned Maia Elo 1331)
- **FEN before the lead-in:** `rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1`
- **Lead-in:** 1... d5
- **Judged user moves:**
  - 2. exd5 (Good, pre-move ES 0.57), reply 2... Qxd5
  - 3. Nc3 (Good, pre-move ES 0.57), reply 3... Qd8
  - 4. d4 (Good, pre-move ES 0.57), reply 4... e6
  - 5. Nf3 (Good, pre-move ES 0.57), reply 5... Bd6
  - 6. Bd3 (Good, pre-move ES 0.60), reply 6... Nc6
- **Answer:** all safe (every judged move is Good).

#### Window 9: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2849876&ply=23
- **User rating:** 1150 (pinned Maia Elo 1352)
- **FEN before the lead-in:** `r3k1nr/p4ppp/2p1p3/q2pP3/3P2b1/2R1BN2/PP3PPP/3QK2R b Kkq - 0 12`
- **Lead-in:** 12... Ne7
- **Judged user moves:**
  - 13. a3 (Good, pre-move ES 0.46), reply 13... O-O-O
  - 14. O-O (Good, pre-move ES 0.70), reply 14... Nf5
  - 15. Rxc6+ (Good, pre-move ES 0.72), reply 15... Kd7
  - 16. Rc5 (Good, pre-move ES 0.79), reply 16... Qb6
  - 17. Qa4+ (Good, pre-move ES 0.89), reply 17... Ke7
- **Answer:** all safe (every judged move is Good).

#### Window 10: allowed (length 4, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=480041&ply=81
- **User rating:** 1341 (pinned Maia Elo 1498)
- **FEN before the lead-in:** `8/8/5k2/1B3P1p/2p1K2P/2r5/8/8 b - - 1 41`
- **Lead-in:** 41... Rh3
- **Judged user moves:**
  - 42. Bxc4 (Good, pre-move ES 0.11), reply 42... Rxh4+
- **FEN before the answer move:** `8/8/5k2/5P1p/2B1K2r/8/8/8 w - - 0 43`
- **Answer:** blunder 43. Kf3 (pre-move ES 0.10, ES after 0.02).
- **Refutation:** Rxc4.
- **Score inputs:** facepalm score 0.927, played prob 0.188, reply spread 2.26, played material 3 -3, mate ply n/a.
- **Missed inputs:** best material 3 2, missed gain 2, best move prob 0.121, pre-blunder spread 2.46.

#### Window 11: allowed (length 3, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=2955830&ply=8
- **User rating:** 820 (pinned Maia Elo 1227)
- **FEN before the lead-in:** `rnbqkb1r/pp2pppp/5n2/3p4/3P1B2/8/PPP2PPP/RN1QKBNR w KQkq - 0 5`
- **Lead-in:** 5. Nf3
- **Judged user moves:**
  - 5... e6 (Good, pre-move ES 0.48), reply 6. Bd3
  - 6... Nbd7 (Good, pre-move ES 0.45), reply 7. c3
- **FEN before the answer move:** `r1bqkb1r/pp1n1ppp/4pn2/3p4/3P1B2/2PB1N2/PP3PPP/RN1QK2R b KQkq - 0 7`
- **Answer:** blunder 7... Bd6 (pre-move ES 0.45, ES after 0.13).
- **Refutation:** Bxd6.
- **Score inputs:** facepalm score 0.957, played prob 0.011, reply spread 3.09, played material 3 -3, mate ply n/a.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.037, pre-blunder spread 6.49.

#### Window 12: mixed (length 4, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=2336186&ply=63
- **User rating:** 1308 (pinned Maia Elo 1308)
- **FEN before the lead-in:** `1q4k1/5pp1/1p5p/1Qpn4/P7/5P1P/1P4P1/4R1K1 b - - 1 32`
- **Lead-in:** 32... Kh7
- **Judged user moves:**
- **FEN before the answer move:** `1q6/5ppk/1p5p/1Qpn4/P7/5P1P/1P4P1/4R1K1 w - - 2 33`
- **Answer:** blunder 33. Re5 (pre-move ES 0.90, ES after 0.12).
- **Refutation:** Qxe5.
- **Missed best move:** Qd3+.
- **Score inputs:** facepalm score 0.996, played prob 0.015, reply spread 1.80, played material 3 -5, mate ply n/a.
- **Missed inputs:** best material 3 3, missed gain 3, best move prob 0.428, pre-blunder spread 6.46.

#### Window 13: allowed (length 4, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=2554690&ply=13
- **User rating:** 1596 (pinned Maia Elo 1404)
- **FEN before the lead-in:** `r1bqk1nr/ppp2ppp/1bnp4/8/2BPP3/2N2N2/PP3PPP/R1BQK2R b KQkq - 2 7`
- **Lead-in:** 7... Bg4
- **Judged user moves:**
- **FEN before the answer move:** `r2qk1nr/ppp2ppp/1bnp4/8/2BPP1b1/2N2N2/PP3PPP/R1BQK2R w KQkq - 3 8`
- **Answer:** blunder 8. Bxf7+ (pre-move ES 0.56, ES after 0.27).
- **Refutation:** Kxf7.
- **Score inputs:** facepalm score 0.850, played prob 0.112, reply spread 1.56, played material 3 -2, mate ply n/a.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.028, pre-blunder spread 9.11.

#### Window 14: allowed (length 4, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=1083321&ply=28
- **User rating:** 811 (pinned Maia Elo 1215)
- **FEN before the lead-in:** `r2qk2r/4n1pp/p2p1p2/1ppN4/2BnP3/3Q4/PP3PPP/R4RK1 w kq - 0 15`
- **Lead-in:** 15. Nxe7
- **Judged user moves:**
  - 15... bxc4 (Good, pre-move ES 0.78), reply 16. Qxc4
  - 16... Qxe7 (Good, pre-move ES 0.78), reply 17. b4
- **FEN before the answer move:** `r3k2r/4q1pp/p2p1p2/2p5/1PQnP3/8/P4PPP/R4RK1 b kq - 0 17`
- **Answer:** blunder 17... cxb4 (pre-move ES 0.83, ES after 0.49).
- **Refutation:** Qxd4.
- **Score inputs:** facepalm score 0.955, played prob 0.070, reply spread 1.10, played material 3 -3, mate ply n/a.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.182, pre-blunder spread 11.47.

#### Window 15: allowed (length 4, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=2952214&ply=8
- **User rating:** 1554 (pinned Maia Elo 1554)
- **FEN before the lead-in:** `r1bqkb1r/pp1ppppp/2n2n2/8/3NP3/8/PPP2PPP/RNBQKB1R w KQkq - 1 5`
- **Lead-in:** 5. Nc3
- **Judged user moves:**
  - 5... e5 (Good, pre-move ES 0.46), reply 6. Ndb5
  - 6... d6 (Good, pre-move ES 0.46), reply 7. Nd5
- **FEN before the answer move:** `r1bqkb1r/pp3ppp/2np1n2/1N1Np3/4P3/8/PPP2PPP/R1BQKB1R b KQkq - 1 7`
- **Answer:** blunder 7... a6 (pre-move ES 0.47, ES after 0.13).
- **Refutation:** Nbc7+.
- **Score inputs:** facepalm score 0.879, played prob 0.071, reply spread 1.28, played material 3 -2, mate ply n/a.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.645, pre-blunder spread 3.40.

#### Window 16: allowed (length 4, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=1548132&ply=19
- **User rating:** 950 (pinned Maia Elo 1436)
- **FEN before the lead-in:** `r2q1rk1/pp1n1ppp/2p1pn2/5b2/1bBPP3/1PN2N2/PB3PPP/R2Q1RK1 b - - 0 10`
- **Lead-in:** 10... Bxc3
- **Judged user moves:**
  - 11. Bxc3 (Good, pre-move ES 0.39), reply 11... Nxe4
- **FEN before the answer move:** `r2q1rk1/pp1n1ppp/2p1p3/5b2/2BPn3/1PB2N2/P4PPP/R2Q1RK1 w - - 0 12`
- **Answer:** blunder 12. Re1 (pre-move ES 0.39, ES after 0.15).
- **Refutation:** Nxc3.
- **Score inputs:** facepalm score 0.965, played prob 0.025, reply spread 1.34, played material 3 -3, mate ply n/a.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.125, pre-blunder spread 3.69.

#### Window 17: herring (length 3, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=1802416&ply=112
- **User rating:** 1555 (pinned Maia Elo 1555)
- **FEN before the lead-in:** `8/5k2/2r1p2p/1p1pK3/3P3P/R1P5/8/8 w - - 0 57`
- **Lead-in:** 57. Ra7+
- **Judged user moves:**
  - 57... Ke8 (Good, pre-move ES 0.50), reply 58. Ra5
  - 58... Rxc3 (Good, pre-move ES 0.50), reply 59. Rxb5
  - 59... Re3+ (Good, pre-move ES 0.51), reply 60. Kf6
- **Answer:** all safe (every judged move is Good).

#### Window 18: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=822440&ply=52
- **User rating:** 1392 (pinned Maia Elo 1552)
- **FEN before the lead-in:** `1r4k1/3n1p1p/1r2p1p1/p1ppP3/PP3P2/2P5/4N1PP/1R3RK1 w - - 1 27`
- **Lead-in:** 27. g4
- **Judged user moves:**
  - 27... cxb4 (Good, pre-move ES 0.76), reply 28. cxb4
  - 28... Rxb4 (Good, pre-move ES 0.76), reply 29. Rxb4
  - 29... Rxb4 (Good, pre-move ES 0.77), reply 30. Ra1
  - 30... Nc5 (Good, pre-move ES 0.83), reply 31. Nc3
  - 31... Ne4 (Good, pre-move ES 0.86), reply 32. Nxe4
- **Answer:** all safe (every judged move is Good).

#### Window 19: allowed (length 4, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=704421&ply=50
- **User rating:** 1493 (pinned Maia Elo 1578)
- **FEN before the lead-in:** `5b2/pp5p/2kp4/2p1pNpP/3pP1P1/P2P1r2/1PP5/R3K3 w Q - 2 26`
- **Lead-in:** 26. Ke2
- **Judged user moves:**
- **FEN before the answer move:** `5b2/pp5p/2kp4/2p1pNpP/3pP1P1/P2P1r2/1PP1K3/R7 b - - 3 26`
- **Answer:** blunder 26... Re3+ (pre-move ES 0.66, ES after 0.10).
- **Refutation:** Nxe3.
- **Score inputs:** facepalm score 0.941, played prob 0.003, reply spread 1.43, played material 3 -2, mate ply n/a.
- **Missed inputs:** best material 3 1, missed gain 1, best move prob 0.652, pre-blunder spread 2.36.

#### Window 20: allowed (length 4, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=1876698&ply=30
- **User rating:** 1075 (pinned Maia Elo 1461)
- **FEN before the lead-in:** `r4rk1/pbn2ppp/1p2p3/2b5/1n6/2N2NB1/PP2BPPP/R2q1RK1 w - - 0 16`
- **Lead-in:** 16. Raxd1
- **Judged user moves:**
- **FEN before the answer move:** `r4rk1/pbn2ppp/1p2p3/2b5/1n6/2N2NB1/PP2BPPP/3R1RK1 b - - 0 16`
- **Answer:** blunder 16... Rad8 (pre-move ES 0.64, ES after 0.19).
- **Refutation:** Bxc7.
- **Score inputs:** facepalm score 0.933, played prob 0.078, reply spread 3.54, played material 3 -3, mate ply n/a.
- **Missed inputs:** best material 3 3, missed gain 3, best move prob 0.644, pre-blunder spread 4.05.

### 1600-1999

#### Window 1: allowed (length 5, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=1976882&ply=17
- **User rating:** 2026 (pinned Maia Elo 1992)
- **FEN before the lead-in:** `r2qk2r/pp1Nbppp/4pn2/3p4/3P4/2N5/PPP2PPP/R1BQK2R b KQkq - 0 9`
- **Lead-in:** 9... Qxd7
- **Judged user moves:**
  - 10. O-O (Good, pre-move ES 0.47), reply 10... O-O
  - 11. Bg5 (Good, pre-move ES 0.46), reply 11... h6
- **FEN before the answer move:** `r4rk1/pp1qbpp1/4pn1p/3p2B1/3P4/2N5/PPP2PPP/R2Q1RK1 w - - 0 12`
- **Answer:** blunder 12. Bxh6 (pre-move ES 0.49, ES after 0.22).
- **Refutation:** gxh6.
- **Score inputs:** facepalm score 0.948, played prob 0.000, reply spread 1.03, played material 3 -2, mate ply n/a.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.118, pre-blunder spread 2.37.

#### Window 2: allowed (length 5, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=1638778&ply=29
- **User rating:** 1317 (pinned Maia Elo 1647)
- **FEN before the lead-in:** `4rrk1/ppp2ppp/2nq4/8/3P4/2P5/P1PQB1PP/R4RK1 b - - 0 15`
- **Lead-in:** 15... Ne5
- **Judged user moves:**
  - 16. Qf4 (Good, pre-move ES 0.51), reply 16... Ng6
  - 17. Qxd6 (Good, pre-move ES 0.50), reply 17... cxd6
- **FEN before the answer move:** `4rrk1/pp3ppp/3p2n1/8/3P4/2P5/P1P1B1PP/R4RK1 w - - 0 18`
- **Answer:** blunder 18. Rab1 (pre-move ES 0.50, ES after 0.19).
- **Refutation:** Rxe2.
- **Score inputs:** facepalm score 0.919, played prob 0.012, reply spread 1.66, played material 3 -2, mate ply n/a.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.457, pre-blunder spread 4.61.

#### Window 3: pure_miss (length 4, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=509065&ply=22
- **User rating:** 1427 (pinned Maia Elo 1799)
- **FEN before the lead-in:** `r2q1rk1/pp1n1ppp/2pbpnb1/4N3/3P1B2/6N1/PPP1QPPP/R3KB1R w KQ - 1 12`
- **Lead-in:** 12. O-O-O
- **Judged user moves:**
- **FEN before the answer move:** `r2q1rk1/pp1n1ppp/2pbpnb1/4N3/3P1B2/6N1/PPP1QPPP/2KR1B1R b - - 2 12`
- **Answer:** blunder 12... h6 (pre-move ES 0.57, ES after 0.22).
- **Missed best move:** Bxe5.
- **Score inputs:** facepalm score 0.960, played prob 0.001, reply spread 3.70, played material 3 -3, mate ply n/a.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.238, pre-blunder spread 7.30.

#### Window 4: herring (length 4, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2699116&ply=24
- **User rating:** 1730 (pinned Maia Elo 1730)
- **FEN before the lead-in:** `r2q1rk1/pp1n1ppp/2p1p3/3n4/2QP1P2/2N2NP1/PP3P1P/R4RK1 w - - 3 13`
- **Lead-in:** 13. Nxd5
- **Judged user moves:**
  - 13... cxd5 (Good, pre-move ES 0.52), reply 14. Qb3
  - 14... Rb8 (Good, pre-move ES 0.50), reply 15. Rac1
  - 15... a6 (Good, pre-move ES 0.48), reply 16. Ne5
  - 16... Nxe5 (Good, pre-move ES 0.48), reply 17. fxe5
- **Answer:** all safe (every judged move is Good).

#### Window 5: herring (length 4, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2591427&ply=0
- **User rating:** 1690 (pinned Maia Elo 1907)
- **FEN before the lead-in:** `rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1`
- **Lead-in:** 1. e4
- **Judged user moves:**
  - 1... e6 (Good, pre-move ES 0.47), reply 2. Nc3
  - 2... d5 (Good, pre-move ES 0.46), reply 3. exd5
  - 3... exd5 (Good, pre-move ES 0.50), reply 4. d4
  - 4... Nf6 (Good, pre-move ES 0.50), reply 5. Bd3
- **Answer:** all safe (every judged move is Good).

#### Window 6: allowed (length 4, blunder at 4)

- **Game:** https://flawchess.com/analysis?game_id=1943786&ply=65
- **User rating:** 1387 (pinned Maia Elo 1770)
- **FEN before the lead-in:** `2R5/5pkp/1p4p1/3r4/3qp3/7P/PP2QPP1/6K1 b - - 2 33`
- **Lead-in:** 33... Qd1+
- **Judged user moves:**
  - 34. Qxd1 (Good, pre-move ES 0.46), reply 34... Rxd1+
  - 35. Kh2 (Good, pre-move ES 0.45), reply 35... Rd2
  - 36. Rc6 (Good, pre-move ES 0.46), reply 36... Rxb2
- **FEN before the answer move:** `8/5pkp/1pR3p1/8/4p3/7P/Pr3PPK/8 w - - 0 37`
- **Answer:** blunder 37. Rxb6 (pre-move ES 0.42, ES after 0.08).
- **Refutation:** Rxb6.
- **Score inputs:** facepalm score 0.987, played prob 0.021, reply spread 1.49, played material 3 -4, mate ply n/a.
- **Missed inputs:** best material 3 n/a, missed gain n/a, best move prob 0.006, pre-blunder spread 3.48.

#### Window 7: allowed (length 3, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=2682497&ply=23
- **User rating:** 1856 (pinned Maia Elo 1677)
- **FEN before the lead-in:** `r2q1rk1/1b3ppp/p1nbpn2/1p1pN3/3P1P2/PP1B4/1BPN2PP/R2Q1RK1 b - - 0 12`
- **Lead-in:** 12... Nd7
- **Judged user moves:**
  - 13. Rf3 (Good, pre-move ES 0.55), reply 13... f6
- **FEN before the answer move:** `r2q1rk1/1b1n2pp/p1nbpp2/1p1pN3/3P1P2/PP1B1R2/1BPN2PP/R2Q2K1 w - - 0 14`
- **Answer:** blunder 14. Bxh7+ (pre-move ES 0.56, ES after 0.32).
- **Refutation:** Kxh7.
- **Score inputs:** facepalm score 0.830, played prob 0.414, reply spread 1.17, played material 3 -2, mate ply n/a.
- **Missed inputs:** best material 3 3, missed gain 3, best move prob 0.139, pre-blunder spread 4.35.

#### Window 8: allowed (length 5, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=1320428&ply=107
- **User rating:** 1832 (pinned Maia Elo 1832)
- **FEN before the lead-in:** `8/1B6/p1p2k2/P1P4p/b4K1P/2P5/8/8 b - - 0 54`
- **Lead-in:** 54... Bb5
- **Judged user moves:**
- **FEN before the answer move:** `8/1B6/p1p2k2/PbP4p/5K1P/2P5/8/8 w - - 1 55`
- **Answer:** blunder 55. Bxc6 (pre-move ES 0.88, ES after 0.14).
- **Refutation:** Bxc6.
- **Score inputs:** facepalm score 0.946, played prob 0.001, reply spread 1.03, played material 3 -2, mate ply n/a.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.631, pre-blunder spread 2.89.

#### Window 9: allowed (length 4, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=1215723&ply=20
- **User rating:** 1217 (pinned Maia Elo 1643)
- **FEN before the lead-in:** `rn1qr1k1/ppp2pp1/3b1n1p/3p2B1/3P4/2NB1Q1P/PPP2PP1/R4RK1 w - - 0 11`
- **Lead-in:** 11. Bxf6
- **Judged user moves:**
  - 11... Qxf6 (Good, pre-move ES 0.23), reply 12. Qxf6
  - 12... gxf6 (Good, pre-move ES 0.24), reply 13. Rae1
- **FEN before the answer move:** `rn2r1k1/ppp2p2/3b1p1p/3p4/3P4/2NB3P/PPP2PP1/4RRK1 b - - 1 13`
- **Answer:** blunder 13... c6 (pre-move ES 0.29, ES after 0.05).
- **Refutation:** Rxe8+.
- **Score inputs:** facepalm score 0.991, played prob 0.137, reply spread 1.50, played material 3 -5, mate ply n/a.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.277, pre-blunder spread 4.97.

#### Window 10: allowed (length 5, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=2742717&ply=25
- **User rating:** 1788 (pinned Maia Elo 1899)
- **FEN before the lead-in:** `3rkb1r/p3pppp/2p5/8/Q7/4Pq2/PP3P1P/R1B1K1R1 b Qk - 1 13`
- **Lead-in:** 13... e6
- **Judged user moves:**
  - 14. Bd2 (Good, pre-move ES 0.48), reply 14... Be7
- **FEN before the answer move:** `3rk2r/p3bppp/2p1p3/8/Q7/4Pq2/PP1B1P1P/R3K1R1 w Qk - 2 15`
- **Answer:** blunder 15. Rg3 (pre-move ES 0.47, ES after 0.17).
- **Refutation:** Qh1+.
- **Score inputs:** facepalm score 0.989, played prob 0.212, reply spread 1.79, played material 3 -5, mate ply n/a.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.013, pre-blunder spread 6.94.

#### Window 11: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2597314&ply=10
- **User rating:** 1266 (pinned Maia Elo 1615)
- **FEN before the lead-in:** `rnbq1rk1/ppp1ppbp/3p1np1/8/2PP1B2/2N2N2/PP2PPPP/R2QKB1R w KQ - 4 6`
- **Lead-in:** 6. Qd2
- **Judged user moves:**
  - 6... Nbd7 (Good, pre-move ES 0.48), reply 7. Bh6
  - 7... e5 (Good, pre-move ES 0.48), reply 8. Bxg7
  - 8... Kxg7 (Good, pre-move ES 0.46), reply 9. dxe5
  - 9... Nxe5 (Good, pre-move ES 0.53), reply 10. Nxe5
  - 10... dxe5 (Good, pre-move ES 0.52), reply 11. Qg5
- **Answer:** all safe (every judged move is Good).

#### Window 12: allowed (length 3, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=3217951&ply=29
- **User rating:** 1271 (pinned Maia Elo 1618)
- **FEN before the lead-in:** `1n1qk2r/r3bppp/p3pn2/1p4N1/2pP4/2P1BB2/PP3PPP/R2QR1K1 b k - 7 15`
- **Lead-in:** 15... Nd5
- **Judged user moves:**
- **FEN before the answer move:** `1n1qk2r/r3bppp/p3p3/1p1n2N1/2pP4/2P1BB2/PP3PPP/R2QR1K1 w k - 8 16`
- **Answer:** blunder 16. Nxf7 (pre-move ES 0.56, ES after 0.39).
- **Refutation:** Kxf7.
- **Score inputs:** facepalm score 0.903, played prob 0.039, reply spread 1.10, played material 3 -2, mate ply n/a.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.019, pre-blunder spread 5.64.

#### Window 13: herring (length 3, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=868392&ply=29
- **User rating:** 1468 (pinned Maia Elo 1616)
- **FEN before the lead-in:** `2kr1b1r/pp1n1pp1/4p1p1/1B1p2P1/3P1q2/8/PPQN1P1P/R3K2R b KQ - 3 15`
- **Lead-in:** 15... Kb8
- **Judged user moves:**
  - 16. Rc1 (Good, pre-move ES 0.21), reply 16... Nb6
  - 17. Nb3 (Good, pre-move ES 0.19), reply 17... Bb4+
  - 18. Ke2 (Good, pre-move ES 0.15), reply 18... Rc8
- **Answer:** all safe (every judged move is Good).

#### Window 14: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=3120413&ply=1
- **User rating:** 1891 (pinned Maia Elo 1891)
- **FEN before the lead-in:** `rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1`
- **Lead-in:** 1... c5
- **Judged user moves:**
  - 2. Nf3 (Good, pre-move ES 0.53), reply 2... e6
  - 3. c3 (Good, pre-move ES 0.54), reply 3... Nc6
  - 4. d4 (Good, pre-move ES 0.53), reply 4... cxd4
  - 5. cxd4 (Good, pre-move ES 0.54), reply 5... d5
  - 6. e5 (Good, pre-move ES 0.54), reply 6... Bb4+
- **Answer:** all safe (every judged move is Good).

#### Window 15: allowed (length 5, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=1432790&ply=32
- **User rating:** 1375 (pinned Maia Elo 1760)
- **FEN before the lead-in:** `r1q2rk1/pp4p1/2p1pn1p/8/2Q5/2N5/PPP2PPP/2KR3R w - - 0 17`
- **Lead-in:** 17. Rhe1
- **Judged user moves:**
  - 17... Nd5 (Good, pre-move ES 0.42), reply 18. Ne4
  - 18... Qc7 (Good, pre-move ES 0.42), reply 19. Nc5
- **FEN before the answer move:** `r4rk1/ppq3p1/2p1p2p/2Nn4/2Q5/8/PPP2PPP/2KRR3 b - - 5 19`
- **Answer:** blunder 19... Rae8 (pre-move ES 0.51, ES after 0.36).
- **Refutation:** Nxe6.
- **Score inputs:** facepalm score 0.723, played prob 0.047, reply spread 1.88, played material 3 -1, mate ply n/a.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.273, pre-blunder spread 9.03.

#### Window 16: herring (length 3, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2077915&ply=6
- **User rating:** 1841 (pinned Maia Elo 1657)
- **FEN before the lead-in:** `rn1qkbnr/pp2pppp/2p5/3pPb2/3P4/8/PPP2PPP/RNBQKBNR w KQkq - 1 4`
- **Lead-in:** 4. c3
- **Judged user moves:**
  - 4... e6 (Good, pre-move ES 0.48), reply 5. Nf3
  - 5... a6 (Good, pre-move ES 0.48), reply 6. Bd3
  - 6... Bxd3 (Good, pre-move ES 0.49), reply 7. Qxd3
- **Answer:** all safe (every judged move is Good).

#### Window 17: allowed (length 4, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=2111110&ply=30
- **User rating:** 1432 (pinned Maia Elo 1731)
- **FEN before the lead-in:** `r2q1rk1/1pp2ppp/1p1p1n2/5bN1/2B1nP2/1Q6/PP4PP/R1B1R1K1 w - - 4 16`
- **Lead-in:** 16. Nxf7
- **Judged user moves:**
- **FEN before the answer move:** `r2q1rk1/1pp2Npp/1p1p1n2/5b2/2B1nP2/1Q6/PP4PP/R1B1R1K1 b - - 0 16`
- **Answer:** blunder 16... d5 (pre-move ES 0.49, ES after 0.17).
- **Refutation:** Nxd8.
- **Score inputs:** facepalm score 0.992, played prob 0.117, reply spread 1.28, played material 3 -6, mate ply n/a.
- **Missed inputs:** best material 3 n/a, missed gain n/a, best move prob 0.500, pre-blunder spread 4.45.

#### Window 18: pure_miss (length 4, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=495314&ply=58
- **User rating:** 1754 (pinned Maia Elo 1991)
- **FEN before the lead-in:** `6k1/B5pp/3q1p2/2p1bP2/4Q3/3P2P1/P6P/7K w - - 0 30`
- **Lead-in:** 30. d4
- **Judged user moves:**
  - 30... cxd4 (Good, pre-move ES 0.47), reply 31. Bxd4
- **FEN before the answer move:** `6k1/6pp/3q1p2/4bP2/3BQ3/6P1/P6P/7K b - - 0 31`
- **Answer:** blunder 31... h6 (pre-move ES 0.78, ES after 0.50).
- **Missed best move:** Qxd4.
- **Score inputs:** facepalm score 0.740, played prob 0.006, reply spread 1.35, played material 3 0, mate ply n/a.
- **Missed inputs:** best material 3 3, missed gain 3, best move prob 0.840, pre-blunder spread 1.68.

#### Window 19: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2219576&ply=27
- **User rating:** 1492 (pinned Maia Elo 1774)
- **FEN before the lead-in:** `r1b2rk1/pp1n2pp/2p2pn1/q7/3P4/2N1PN2/PP2BPPP/2RQK2R b K - 2 14`
- **Lead-in:** 14... f5
- **Judged user moves:**
  - 15. Qb3+ (Good, pre-move ES 0.72), reply 15... Kh8
  - 16. O-O (Good, pre-move ES 0.72), reply 16... Nf6
  - 17. Bd3 (Good, pre-move ES 0.71), reply 17... Ne7
  - 18. Ng5 (Good, pre-move ES 0.72), reply 18... Ned5
  - 19. Nxd5 (Good, pre-move ES 0.73), reply 19... cxd5
- **Answer:** all safe (every judged move is Good).

#### Window 20: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=3264242&ply=1
- **User rating:** 1909 (pinned Maia Elo 1983)
- **FEN before the lead-in:** `rnbqkbnr/pppppppp/8/8/3P4/8/PPP1PPPP/RNBQKBNR b KQkq - 0 1`
- **Lead-in:** 1... d5
- **Judged user moves:**
  - 2. Nf3 (Good, pre-move ES 0.53), reply 2... e6
  - 3. c4 (Good, pre-move ES 0.52), reply 3... Nf6
  - 4. g3 (Good, pre-move ES 0.53), reply 4... Nbd7
  - 5. Bg2 (Good, pre-move ES 0.53), reply 5... c6
  - 6. O-O (Good, pre-move ES 0.54), reply 6... Bd6
- **Answer:** all safe (every judged move is Good).

### 2000-2399

#### Window 1: pure_miss (length 5, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=500348&ply=75
- **User rating:** 1910 (pinned Maia Elo 2090)
- **FEN before the lead-in:** `5rk1/2p1p1b1/1p1p4/3Pp3/1PP5/4NrP1/5PK1/3R3R b - - 3 38`
- **Lead-in:** 38... Kf7
- **Judged user moves:**
- **FEN before the answer move:** `5r2/2p1pkb1/1p1p4/3Pp3/1PP5/4NrP1/5PK1/3R3R w - - 4 39`
- **Answer:** blunder 39. Rdf1 (pre-move ES 0.87, ES after 0.50).
- **Missed best move:** Kxf3.
- **Score inputs:** facepalm score 0.793, played prob 0.003, reply spread 5.01, played material 3 0, mate ply n/a.
- **Missed inputs:** best material 3 5, missed gain 5, best move prob 0.869, pre-blunder spread 1.98.

#### Window 2: allowed (length 5, blunder at 4)

- **Game:** https://flawchess.com/analysis?game_id=607292&ply=39
- **User rating:** 1979 (pinned Maia Elo 2133)
- **FEN before the lead-in:** `1n3rk1/1p2qp2/pNp1bbpp/2P1p3/1P2P3/5NP1/P1QR1PBP/6K1 b - - 0 20`
- **Lead-in:** 20... Rd8
- **Judged user moves:**
  - 21. Rxd8+ (Good, pre-move ES 0.54), reply 21... Qxd8
  - 22. Qd2 (Good, pre-move ES 0.54), reply 22... Qxd2
  - 23. Nxd2 (Good, pre-move ES 0.50), reply 23... Bxa2
- **FEN before the answer move:** `1n4k1/1p3p2/pNp2bpp/2P1p3/1P2P3/6P1/b2N1PBP/6K1 w - - 0 24`
- **Answer:** blunder 24. Nd7 (pre-move ES 0.50, ES after 0.15).
- **Refutation:** Nxd7.
- **Score inputs:** facepalm score 0.979, played prob 0.002, reply spread 1.02, played material 3 -3, mate ply n/a.
- **Missed inputs:** best material 3 n/a, missed gain n/a, best move prob 0.336, pre-blunder spread 5.86.

#### Window 3: allowed (length 5, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=2810167&ply=117
- **User rating:** 1951 (pinned Maia Elo 2076)
- **FEN before the lead-in:** `8/8/8/R5k1/5p2/4r1p1/2K3P1/3Bb3 b - - 17 59`
- **Lead-in:** 59... Kf6
- **Judged user moves:**
  - 60. Ra4 (Good, pre-move ES 0.50), reply 60... Ke7
- **FEN before the answer move:** `8/4k3/8/8/R4p2/4r1p1/2K3P1/3Bb3 w - - 20 61`
- **Answer:** blunder 61. Re4+ (pre-move ES 0.50, ES after 0.07).
- **Refutation:** Rxe4.
- **Score inputs:** facepalm score 0.998, played prob 0.001, reply spread 1.05, played material 3 -5, mate ply n/a.
- **Missed inputs:** best material 3 1, missed gain 1, best move prob 0.797, pre-blunder spread 1.91.

#### Window 4: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=626431&ply=24
- **User rating:** 1949 (pinned Maia Elo 2013)
- **FEN before the lead-in:** `2kr1b1r/ppqnpp2/2p4p/3p2p1/3P4/2PQP1P1/PP1N1PP1/RN2K2R w KQ - 1 13`
- **Lead-in:** 13. Nf3
- **Judged user moves:**
  - 13... Bg7 (Good, pre-move ES 0.54), reply 14. Nbd2
  - 14... Kb8 (Good, pre-move ES 0.54), reply 15. O-O-O
  - 15... e5 (Good, pre-move ES 0.54), reply 16. dxe5
  - 16... Nxe5 (Good, pre-move ES 0.51), reply 17. Qf5
  - 17... Rhe8 (Good, pre-move ES 0.50), reply 18. Kb1
- **Answer:** all safe (every judged move is Good).

#### Window 5: allowed (length 4, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=572586&ply=70
- **User rating:** 1791 (pinned Maia Elo 2016)
- **FEN before the lead-in:** `8/8/p3rk2/1p1Rp2p/4K1p1/P4P2/1PP2P1P/8 w - - 0 36`
- **Lead-in:** 36. fxg4
- **Judged user moves:**
  - 36... hxg4 (Good, pre-move ES 0.33), reply 37. b4
- **FEN before the answer move:** `8/8/p3rk2/1p1Rp3/1P2K1p1/P7/2P2P1P/8 b - - 0 37`
- **Answer:** blunder 37... Kg5 (pre-move ES 0.32, ES after 0.09).
- **Refutation:** Rxe5+.
- **Score inputs:** facepalm score 0.787, played prob 0.027, reply spread 1.23, played material 3 -1, mate ply n/a.
- **Missed inputs:** best material 3 n/a, missed gain n/a, best move prob 0.002, pre-blunder spread 2.03.

#### Window 6: allowed (length 3, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=2310865&ply=57
- **User rating:** 1804 (pinned Maia Elo 2029)
- **FEN before the lead-in:** `4r1k1/p3r1pp/1qp5/8/P2pP1P1/7P/3Q2K1/2R4R b - - 0 29`
- **Lead-in:** 29... Rxe4
- **Judged user moves:**
- **FEN before the answer move:** `4r1k1/p5pp/1qp5/8/P2pr1P1/7P/3Q2K1/2R4R w - - 0 30`
- **Answer:** blunder 30. Rhf1 (pre-move ES 0.22, ES after 0.07).
- **Refutation:** Re2+.
- **Score inputs:** facepalm score 0.981, played prob 0.036, reply spread 2.42, played material 3 -4, mate ply n/a.
- **Missed inputs:** best material 3 n/a, missed gain n/a, best move prob n/a, pre-blunder spread 6.24.

#### Window 7: herring (length 4, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=3020655&ply=16
- **User rating:** 2214 (pinned Maia Elo 2214)
- **FEN before the lead-in:** `rn1qk2r/ppp2ppp/1b1p1n2/3Pp3/2B1P1b1/2P2N2/PP3PPP/RNBQR1K1 w kq - 1 9`
- **Lead-in:** 9. Nbd2
- **Judged user moves:**
  - 9... O-O (Good, pre-move ES 0.46), reply 10. h3
  - 10... Bh5 (Good, pre-move ES 0.47), reply 11. Nf1
  - 11... h6 (Good, pre-move ES 0.48), reply 12. Ng3
  - 12... Bg6 (Good, pre-move ES 0.47), reply 13. Nh4
- **Answer:** all safe (every judged move is Good).

#### Window 8: allowed (length 4, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=3245834&ply=17
- **User rating:** 2144 (pinned Maia Elo 2199)
- **FEN before the lead-in:** `r2qkb1r/pp1b1pp1/2n1p3/2ppPn1p/3P3P/2PB1N2/PPN2PP1/R1BQK2R b KQkq - 2 9`
- **Lead-in:** 9... g6
- **Judged user moves:**
- **FEN before the answer move:** `r2qkb1r/pp1b1p2/2n1p1p1/2ppPn1p/3P3P/2PB1N2/PPN2PP1/R1BQK2R w KQkq - 0 10`
- **Answer:** blunder 10. O-O (pre-move ES 0.64, ES after 0.48).
- **Refutation:** Nxh4.
- **Score inputs:** facepalm score 0.747, played prob 0.019, reply spread 2.82, played material 3 -1, mate ply n/a.
- **Missed inputs:** best material 3 1, missed gain 1, best move prob 0.376, pre-blunder spread 5.19.

#### Window 9: herring (length 3, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2704672&ply=84
- **User rating:** 2298 (pinned Maia Elo 2252)
- **FEN before the lead-in:** `5k2/6RR/1p1r2p1/8/3N2P1/2n1P3/5r2/2K5 w - - 5 43`
- **Lead-in:** 43. Ra7
- **Judged user moves:**
  - 43... Kg8 (Good, pre-move ES 0.17), reply 44. Rhc7
  - 44... Na2+ (Good, pre-move ES 0.50), reply 45. Kd1
  - 45... Nb4 (Good, pre-move ES 0.50), reply 46. Rc8+
- **Answer:** all safe (every judged move is Good).

#### Window 10: allowed (length 3, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=2628536&ply=36
- **User rating:** 2067 (pinned Maia Elo 2067)
- **FEN before the lead-in:** `2kr4/pp1qbpp1/2n2n2/2p1p1B1/4P3/2P3Pr/PPQNB3/2KR2R1 w - - 3 19`
- **Lead-in:** 19. Nc4
- **Judged user moves:**
- **FEN before the answer move:** `2kr4/pp1qbpp1/2n2n2/2p1p1B1/2N1P3/2P3Pr/PPQ1B3/2KR2R1 b - - 4 19`
- **Answer:** blunder 19... Qc7 (pre-move ES 0.47, ES after 0.18).
- **Refutation:** Bxf6.
- **Score inputs:** facepalm score 0.902, played prob 0.266, reply spread 2.29, played material 3 -3, mate ply n/a.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.701, pre-blunder spread 2.14.

#### Window 11: allowed (length 5, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=1231975&ply=54
- **User rating:** 2135 (pinned Maia Elo 2068)
- **FEN before the lead-in:** `6k1/5p1p/4pp2/R2p4/1Pb5/6PP/P1r2PBK/8 w - - 1 28`
- **Lead-in:** 28. b5
- **Judged user moves:**
- **FEN before the answer move:** `6k1/5p1p/4pp2/RP1p4/2b5/6PP/P1r2PBK/8 b - - 0 28`
- **Answer:** blunder 28... Rxa2 (pre-move ES 0.74, ES after 0.16).
- **Refutation:** Rxa2.
- **Score inputs:** facepalm score 0.930, played prob 0.199, reply spread 1.34, played material 3 -3, mate ply n/a.
- **Missed inputs:** best material 3 n/a, missed gain n/a, best move prob 0.532, pre-blunder spread 3.52.

#### Window 12: herring (length 3, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=3013700&ply=44
- **User rating:** 2106 (pinned Maia Elo 2174)
- **FEN before the lead-in:** `r2q1rk1/1p2bpp1/p3pn1p/4B3/P2p4/2P3NP/1P3PP1/R2QR1K1 w - - 0 23`
- **Lead-in:** 23. cxd4
- **Judged user moves:**
  - 23... Qd5 (Good, pre-move ES 0.53), reply 24. Rc1
  - 24... Rfc8 (Good, pre-move ES 0.57), reply 25. Qd3
  - 25... Rc6 (Good, pre-move ES 0.55), reply 26. Rxc6
- **Answer:** all safe (every judged move is Good).

#### Window 13: herring (length 4, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=1528147&ply=63
- **User rating:** 2351 (pinned Maia Elo 2351)
- **FEN before the lead-in:** `3r2k1/ppqr1pp1/4pn1p/1PP5/2QP4/5N1P/R3RPP1/6K1 b - - 2 32`
- **Lead-in:** 32... a6
- **Judged user moves:**
  - 33. bxa6 (Good, pre-move ES 0.61), reply 33... bxa6
  - 34. Rxa6 (Good, pre-move ES 0.61), reply 34... Nd5
  - 35. Ne5 (Good, pre-move ES 0.67), reply 35... Re7
  - 36. Nc6 (Good, pre-move ES 0.78), reply 36... Red7
- **Answer:** all safe (every judged move is Good).

#### Window 14: herring (length 4, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=1231539&ply=77
- **User rating:** 1937 (pinned Maia Elo 2068)
- **FEN before the lead-in:** `6k1/5pp1/7p/8/2R3P1/7P/5PK1/3r4 b - - 0 39`
- **Lead-in:** 39... Rd7
- **Judged user moves:**
  - 40. Rc8+ (Good, pre-move ES 0.50), reply 40... Kh7
  - 41. Kg3 (Good, pre-move ES 0.50), reply 41... g5
  - 42. h4 (Good, pre-move ES 0.50), reply 42... Kg6
  - 43. Rc6+ (Good, pre-move ES 0.50), reply 43... Kg7
- **Answer:** all safe (every judged move is Good).

#### Window 15: allowed (length 5, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=500631&ply=43
- **User rating:** 2027 (pinned Maia Elo 2092)
- **FEN before the lead-in:** `q3kb1r/5ppp/p2p2b1/1p1P4/4p3/1BP1P3/PP1Q2PP/R4RK1 b k - 1 22`
- **Lead-in:** 22... Be7
- **Judged user moves:**
  - 23. Bc2 (Good, pre-move ES 0.66), reply 23... O-O
- **FEN before the answer move:** `q4rk1/4bppp/p2p2b1/1p1P4/4p3/2P1P3/PPBQ2PP/R4RK1 w - - 4 24`
- **Answer:** blunder 24. Bxe4 (pre-move ES 0.64, ES after 0.20).
- **Refutation:** Bxe4.
- **Score inputs:** facepalm score 0.947, played prob 0.000, reply spread 1.03, played material 3 -2, mate ply n/a.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.169, pre-blunder spread 6.51.

#### Window 16: mixed (length 5, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=2483420&ply=64
- **User rating:** 1942 (pinned Maia Elo 2071)
- **FEN before the lead-in:** `4b3/4q1bk/2n1p1pp/3pP3/r2P2P1/2p1BNK1/3Q1P2/1B5R w - - 0 33`
- **Lead-in:** 33. Qc2
- **Judged user moves:**
- **FEN before the answer move:** `4b3/4q1bk/2n1p1pp/3pP3/r2P2P1/2p1BNK1/2Q2P2/1B5R b - - 1 33`
- **Answer:** blunder 33... Nb4 (pre-move ES 0.61, ES after 0.24).
- **Refutation:** Qxc3.
- **Missed best move:** Nxd4.
- **Score inputs:** facepalm score 0.809, played prob 0.095, reply spread 2.93, played material 3 -2, mate ply n/a.
- **Missed inputs:** best material 3 n/a, missed gain n/a, best move prob 0.056, pre-blunder spread 9.90.

#### Window 17: herring (length 3, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=764116&ply=32
- **User rating:** 2150 (pinned Maia Elo 2150)
- **FEN before the lead-in:** `2r1r1k1/pbq2ppp/1p1b1n2/2ppN3/3Pn3/1P1QP1N1/PB2BPPP/2R1R1K1 w - - 16 17`
- **Lead-in:** 17. Nf5
- **Judged user moves:**
  - 17... Bf8 (Good, pre-move ES 0.48), reply 18. f3
  - 18... Nd6 (Good, pre-move ES 0.48), reply 19. dxc5
  - 19... bxc5 (Good, pre-move ES 0.52), reply 20. b4
- **Answer:** all safe (every judged move is Good).

#### Window 18: allowed (length 3, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=1947755&ply=39
- **User rating:** 2081 (pinned Maia Elo 2031)
- **FEN before the lead-in:** `4rrk1/1p1q1pp1/p2p1b1p/3P4/2P5/1P2P3/P3N1PP/2RQR1K1 b - - 0 20`
- **Lead-in:** 20... Rxe3
- **Judged user moves:**
- **FEN before the answer move:** `5rk1/1p1q1pp1/p2p1b1p/3P4/2P5/1P2r3/P3N1PP/2RQR1K1 w - - 0 21`
- **Answer:** blunder 21. Nd4 (pre-move ES 0.37, ES after 0.13).
- **Refutation:** Rxe1+.
- **Score inputs:** facepalm score 0.935, played prob 0.094, reply spread 2.15, played material 3 -3, mate ply n/a.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.578, pre-blunder spread 3.86.

#### Window 19: allowed (length 4, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=2670222&ply=40
- **User rating:** 2121 (pinned Maia Elo 2184)
- **FEN before the lead-in:** `5rk1/rbqn1p2/p3p1p1/P3p2p/1pN1P3/3B3P/1PP1QPP1/R4RK1 w - - 5 21`
- **Lead-in:** 21. g4
- **Judged user moves:**
  - 21... h4 (Good, pre-move ES 0.46), reply 22. g5
  - 22... Nc5 (Good, pre-move ES 0.45), reply 23. Qg4
- **FEN before the answer move:** `5rk1/rbq2p2/p3p1p1/P1n1p1P1/1pN1P1Qp/3B3P/1PP2P2/R4RK1 b - - 2 23`
- **Answer:** blunder 23... Qc6 (pre-move ES 0.45, ES after 0.29).
- **Refutation:** Rfe1.
- **Score inputs:** facepalm score 0.765, played prob 0.002, reply spread 3.45, played material 3 -1, mate ply n/a.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.120, pre-blunder spread 6.86.

#### Window 20: pure_miss (length 5, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=3023011&ply=33
- **User rating:** 2344 (pinned Maia Elo 2247)
- **FEN before the lead-in:** `r1b2rk1/pp3pp1/1qp2b1p/8/n2N3P/2B1QB2/PPP2PP1/1K1R3R b - - 0 17`
- **Lead-in:** 17... Nxc3+
- **Judged user moves:**
  - 18. Qxc3 (Good, pre-move ES 0.16), reply 18... Be6
- **FEN before the answer move:** `r4rk1/pp3pp1/1qp1bb1p/8/3N3P/2Q2B2/PPP2PP1/1K1R3R w - - 1 19`
- **Answer:** blunder 19. g4 (pre-move ES 0.38, ES after 0.14).
- **Missed best move:** Qe3.
- **Score inputs:** facepalm score 0.879, played prob 0.265, reply spread 3.23, played material 3 -3, mate ply n/a.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.579, pre-blunder spread 3.83.

### 2400+

#### Window 1: mixed (length 5, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=1519371&ply=34
- **User rating:** 2860 (pinned Maia Elo 2600)
- **FEN before the lead-in:** `r2q1r1k/1p1b1pp1/4p2p/p1b1Pn2/3p2Q1/P2B1N2/1PP2PPP/R1B1R1K1 w - - 6 18`
- **Lead-in:** 18. Qh5
- **Judged user moves:**
  - 18... Be7 (Good, pre-move ES 0.38), reply 19. g4
- **FEN before the answer move:** `r2q1r1k/1p1bbpp1/4p2p/p3Pn1Q/3p2P1/P2B1N2/1PP2P1P/R1B1R1K1 b - - 0 19`
- **Answer:** blunder 19... f6 (pre-move ES 0.49, ES after 0.17).
- **Refutation:** gxf5.
- **Missed best move:** Nh4.
- **Score inputs:** facepalm score 0.976, played prob 0.001, reply spread 1.40, played material 3 -3, mate ply n/a.
- **Missed inputs:** best material 3 -1, missed gain -1, best move prob 0.458, pre-blunder spread 3.38.

#### Window 2: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=643062&ply=49
- **User rating:** 2637 (pinned Maia Elo 2584)
- **FEN before the lead-in:** `7k/pp6/n1pp2p1/2nPp3/2P5/P1N1P2P/1P4B1/1K6 b - - 1 25`
- **Lead-in:** 25... Nb8
- **Judged user moves:**
  - 26. b4 (Good, pre-move ES 0.76), reply 26... Ncd7
  - 27. Ne4 (Good, pre-move ES 0.77), reply 27... cxd5
  - 28. cxd5 (Good, pre-move ES 0.74), reply 28... b5
  - 29. Nxd6 (Good, pre-move ES 0.76), reply 29... a6
  - 30. h4 (Good, pre-move ES 0.74), reply 30... Kg7
- **Answer:** all safe (every judged move is Good).

#### Window 3: herring (length 4, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=644277&ply=46
- **User rating:** 2658 (pinned Maia Elo 2600)
- **FEN before the lead-in:** `4r1k1/pp3ppp/2p2n2/3r4/3Np3/1P2P1Pq/P3QP1P/2R1R1K1 w - - 6 24`
- **Lead-in:** 24. Qf1
- **Judged user moves:**
  - 24... Qg4 (Good, pre-move ES 0.69), reply 25. h3
  - 25... Qg6 (Good, pre-move ES 0.67), reply 26. Rcd1
  - 26... h5 (Good, pre-move ES 0.65), reply 27. Nc2
  - 27... h4 (Good, pre-move ES 0.69), reply 28. g4
- **Answer:** all safe (every judged move is Good).

#### Window 4: pure_miss (length 3, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=656760&ply=113
- **User rating:** 2633 (pinned Maia Elo 2581)
- **FEN before the lead-in:** `8/3K1kp1/2P4p/8/8/2r5/1R6/8 b - - 4 57`
- **Lead-in:** 57... g5
- **Judged user moves:**
  - 58. c7 (Good, pre-move ES 0.50), reply 58... Kg6
- **FEN before the answer move:** `8/2PK4/6kp/6p1/8/2r5/1R6/8 w - - 1 59`
- **Answer:** blunder 59. c8=Q (pre-move ES 0.83, ES after 0.50).
- **Missed best move:** Rb6+.
- **Score inputs:** facepalm score 0.986, played prob 0.046, reply spread 1.13, played material 3 -4, mate ply n/a.
- **Missed inputs:** best material 3 1, missed gain 1, best move prob 0.933, pre-blunder spread 1.39.

#### Window 5: allowed (length 4, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=1526570&ply=39
- **User rating:** 2925 (pinned Maia Elo 2600)
- **FEN before the lead-in:** `3rr1k1/pp3p1p/2p1qBp1/8/2n1B3/2P4P/PP2QPP1/R3R1K1 b - - 0 20`
- **Lead-in:** 20... Qxf6
- **Judged user moves:**
  - 21. Qxc4 (Good, pre-move ES 0.79), reply 21... Rd2
- **FEN before the answer move:** `4r1k1/pp3p1p/2p2qp1/8/2Q1B3/2P4P/PP1r1PP1/R3R1K1 w - - 1 22`
- **Answer:** blunder 22. Re2 (pre-move ES 0.79, ES after 0.39).
- **Refutation:** b5.
- **Score inputs:** facepalm score 0.939, played prob 0.262, reply spread 3.90, played material 3 -4, mate ply n/a.
- **Missed inputs:** best material 3 -1, missed gain -1, best move prob 0.649, pre-blunder spread 2.64.

#### Window 6: allowed (length 4, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=656212&ply=27
- **User rating:** 2707 (pinned Maia Elo 2600)
- **FEN before the lead-in:** `1r1q1rk1/pb2bppp/n4n2/3pN3/2pP4/P1N3P1/1B2PPBP/R2QR1K1 b - - 3 14`
- **Lead-in:** 14... Nc7
- **Judged user moves:**
  - 15. Rb1 (Good, pre-move ES 0.50), reply 15... Bd6
  - 16. e4 (Good, pre-move ES 0.52), reply 16... dxe4
- **FEN before the answer move:** `1r1q1rk1/pbn2ppp/3b1n2/4N3/2pPp3/P1N3P1/1B3PBP/1R1QR1K1 w - - 0 17`
- **Answer:** blunder 17. Nxe4 (pre-move ES 0.55, ES after 0.22).
- **Refutation:** Bxe4.
- **Score inputs:** facepalm score 0.972, played prob 0.160, reply spread 1.80, played material 3 -4, mate ply n/a.
- **Missed inputs:** best material 3 n/a, missed gain n/a, best move prob 0.788, pre-blunder spread 2.05.

#### Window 7: allowed (length 3, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=1516884&ply=73
- **User rating:** 2648 (pinned Maia Elo 2600)
- **FEN before the lead-in:** `8/pp4k1/3N1n1p/6p1/2B5/B1P4r/P3K3/8 b - - 4 37`
- **Lead-in:** 37... Rxc3
- **Judged user moves:**
- **FEN before the answer move:** `8/pp4k1/3N1n1p/6p1/2B5/B1r5/P3K3/8 w - - 0 38`
- **Answer:** blunder 38. Bb2 (pre-move ES 0.44, ES after 0.05).
- **Refutation:** Rc2+.
- **Score inputs:** facepalm score 0.904, played prob 0.456, reply spread 1.36, played material 3 -3, mate ply n/a.
- **Missed inputs:** best material 3 n/a, missed gain n/a, best move prob 0.233, pre-blunder spread 4.08.

#### Window 8: allowed (length 5, blunder at 4)

- **Game:** https://flawchess.com/analysis?game_id=1522904&ply=98
- **User rating:** 2505 (pinned Maia Elo 2505)
- **FEN before the lead-in:** `8/7k/3R4/p7/Pp1p4/1Pb4p/4N3/1K6 w - - 0 50`
- **Lead-in:** 50. Nxc3
- **Judged user moves:**
  - 50... h2 (Good, pre-move ES 0.48), reply 51. Rd7+
  - 51... Kh6 (Good, pre-move ES 0.49), reply 52. Rd6+
  - 52... Kh5 (Good, pre-move ES 0.48), reply 53. Rd5+
- **FEN before the answer move:** `8/8/8/p2R3k/Pp1p4/1PN5/7p/1K6 b - - 5 53`
- **Answer:** blunder 53... Kh4 (pre-move ES 0.47, ES after 0.07).
- **Refutation:** Rxd4+.
- **Score inputs:** facepalm score 0.704, played prob 0.083, reply spread 1.45, played material 3 -1, mate ply n/a.
- **Missed inputs:** best material 3 n/a, missed gain n/a, best move prob 0.514, pre-blunder spread 3.06.

#### Window 9: allowed (length 4, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=1515061&ply=81
- **User rating:** 2812 (pinned Maia Elo 2600)
- **FEN before the lead-in:** `8/5p2/2p2k2/2Pb1p1p/1r3P1P/3BK1P1/8/R7 b - - 1 41`
- **Lead-in:** 41... Rb3
- **Judged user moves:**
- **FEN before the answer move:** `8/5p2/2p2k2/2Pb1p1p/5P1P/1r1BK1P1/8/R7 w - - 2 42`
- **Answer:** blunder 42. Ra6 (pre-move ES 0.50, ES after 0.13).
- **Refutation:** Be4.
- **Score inputs:** facepalm score 0.983, played prob 0.013, reply spread 2.98, played material 3 -4, mate ply n/a.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.626, pre-blunder spread 3.74.

#### Window 10: allowed (length 5, blunder at 5)

- **Game:** https://flawchess.com/analysis?game_id=1511195&ply=164
- **User rating:** 2759 (pinned Maia Elo 2600)
- **FEN before the lead-in:** `b7/P4k2/8/2K5/5B2/8/8/8 w - - 2 83`
- **Lead-in:** 83. Be3
- **Judged user moves:**
  - 83... Bb7 (Good, pre-move ES 0.50), reply 84. Bd2
  - 84... Ba8 (Good, pre-move ES 0.50), reply 85. Bc3
  - 85... Bb7 (Good, pre-move ES 0.50), reply 86. Kb6
  - 86... Ba8 (Good, pre-move ES 0.50), reply 87. Bb4
- **FEN before the answer move:** `b7/P4k2/1K6/8/1B6/8/8/8 b - - 11 87`
- **Answer:** blunder 87... Bb7 (pre-move ES 0.50, ES after 0.00).
- **Refutation:** Kxb7.
- **Score inputs:** facepalm score 0.976, played prob 0.001, reply spread 1.75, played material 3 -3, mate ply n/a.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.264, pre-blunder spread 5.37.

#### Window 11: allowed (length 5, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=1523069&ply=96
- **User rating:** 2878 (pinned Maia Elo 2600)
- **FEN before the lead-in:** `8/7r/4k3/4p2P/n1K2p2/5P2/1p4P1/1R4B1 w - - 1 49`
- **Lead-in:** 49. Kb3
- **Judged user moves:**
- **FEN before the answer move:** `8/7r/4k3/4p2P/n4p2/1K3P2/1p4P1/1R4B1 b - - 2 49`
- **Answer:** blunder 49... Rxh5 (pre-move ES 0.50, ES after 0.29).
- **Refutation:** Kxa4.
- **Score inputs:** facepalm score 0.866, played prob 0.283, reply spread 1.39, played material 3 -2, mate ply n/a.
- **Missed inputs:** best material 3 5, missed gain 5, best move prob 0.149, pre-blunder spread 7.09.

#### Window 12: herring (length 3, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=1516651&ply=31
- **User rating:** 2821 (pinned Maia Elo 2600)
- **FEN before the lead-in:** `r2r2k1/ppqN1pbp/2p1b1p1/2B5/4P3/1P3NP1/P1P1QPBP/R3R1K1 b - - 0 16`
- **Lead-in:** 16... Bxa1
- **Judged user moves:**
  - 17. Rxa1 (Good, pre-move ES 0.86), reply 17... Rxd7
  - 18. Re1 (Good, pre-move ES 0.86), reply 18... Rad8
  - 19. Qe3 (Good, pre-move ES 0.85), reply 19... Qa5
- **Answer:** all safe (every judged move is Good).

#### Window 13: allowed (length 3, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=642935&ply=106
- **User rating:** 2681 (pinned Maia Elo 2600)
- **FEN before the lead-in:** `R7/5p1k/4pP1P/4Kn1b/1p1P1B2/5r2/P7/8 w - - 7 54`
- **Lead-in:** 54. Ra7
- **Judged user moves:**
  - 54... Bg6 (Good, pre-move ES 0.85), reply 55. Rb7
  - 55... Rd3 (Good, pre-move ES 0.87), reply 56. Rd7
- **FEN before the answer move:** `8/3R1p1k/4pPbP/4Kn2/1p1P1B2/3r4/P7/8 b - - 12 56`
- **Answer:** blunder 56... Rxd4 (pre-move ES 0.88, ES after 0.50).
- **Refutation:** Rxd4.
- **Score inputs:** facepalm score 0.944, played prob 0.003, reply spread 1.37, played material 3 -2, mate ply n/a.
- **Missed inputs:** best material 3 1, missed gain 1, best move prob 0.184, pre-blunder spread 5.19.

#### Window 14: allowed (length 3, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=612985&ply=19
- **User rating:** 2281 (pinned Maia Elo 2433)
- **FEN before the lead-in:** `rn2kb1r/1b1qnppp/pp2p3/3pP3/2pP1P2/2P2N2/PPBN2PP/R1BQ1RK1 b kq - 1 10`
- **Lead-in:** 10... Ng6
- **Judged user moves:**
  - 11. Ng5 (Good, pre-move ES 0.77), reply 11... h6
- **FEN before the answer move:** `rn2kb1r/1b1q1pp1/pp2p1np/3pP1N1/2pP1P2/2P5/PPBN2PP/R1BQ1RK1 w kq - 0 12`
- **Answer:** blunder 12. Nxf7 (pre-move ES 0.81, ES after 0.53).
- **Refutation:** Qxf7.
- **Score inputs:** facepalm score 0.764, played prob 0.625, reply spread 1.44, played material 3 -2, mate ply n/a.
- **Missed inputs:** best material 3 1, missed gain 1, best move prob 0.078, pre-blunder spread 3.54.

#### Window 15: mixed (length 3, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=654820&ply=43
- **User rating:** 2495 (pinned Maia Elo 2441)
- **FEN before the lead-in:** `2r1nnk1/1p2rppp/p1p5/P1Pp1b2/3P1BP1/1RN4P/1P3PB1/5RK1 b - - 0 22`
- **Lead-in:** 22... Bd3
- **Judged user moves:**
- **FEN before the answer move:** `2r1nnk1/1p2rppp/p1p5/P1Pp4/3P1BP1/1RNb3P/1P3PB1/5RK1 w - - 1 23`
- **Answer:** blunder 23. Rd1 (pre-move ES 0.73, ES after 0.23).
- **Refutation:** Bc2.
- **Missed best move:** Nxd5.
- **Score inputs:** facepalm score 0.807, played prob 0.185, reply spread 2.33, played material 3 -2, mate ply n/a.
- **Missed inputs:** best material 3 1, missed gain 1, best move prob 0.363, pre-blunder spread 4.14.

#### Window 16: allowed (length 5, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=641104&ply=84
- **User rating:** 2523 (pinned Maia Elo 2471)
- **FEN before the lead-in:** `8/6p1/4n2p/3r1k2/3p4/5NPP/3RKP2/8 w - - 6 43`
- **Lead-in:** 43. Kd3
- **Judged user moves:**
- **FEN before the answer move:** `8/6p1/4n2p/3r1k2/3p4/3K1NPP/3R1P2/8 b - - 7 43`
- **Answer:** blunder 43... Nc5+ (pre-move ES 0.50, ES after 0.16).
- **Refutation:** Kc4.
- **Score inputs:** facepalm score 0.940, played prob 0.149, reply spread 1.14, played material 3 -3, mate ply n/a.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.399, pre-blunder spread 5.96.

#### Window 17: allowed (length 4, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=1516434&ply=53
- **User rating:** 2813 (pinned Maia Elo 2600)
- **FEN before the lead-in:** `8/5k1p/1pp1p1nb/p2pPp1Q/3P1P2/1PP1B2P/P3N2K/4q3 b - - 1 27`
- **Lead-in:** 27... Kg7
- **Judged user moves:**
  - 28. Qf3 (Good, pre-move ES 0.30), reply 28... b5
  - 29. Ng3 (Good, pre-move ES 0.35), reply 29... Nh4
- **FEN before the answer move:** `8/6kp/2p1p2b/pp1pPp2/3P1P1n/1PP1BQNP/P6K/4q3 w - - 2 30`
- **Answer:** blunder 30. Nh5+ (pre-move ES 0.38, ES after 0.22).
- **Refutation:** Kg6.
- **Score inputs:** facepalm score 0.878, played prob 0.292, reply spread 3.11, played material 3 -3, mate ply n/a.
- **Missed inputs:** best material 3 n/a, missed gain n/a, best move prob 0.140, pre-blunder spread 3.51.

#### Window 18: allowed (length 5, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=3012528&ply=20
- **User rating:** 2290 (pinned Maia Elo 2445)
- **FEN before the lead-in:** `r3k1nr/ppp2p1p/3p4/n1bNp3/2BqP1Q1/8/PPPP2PP/R1BK1R2 w kq - 1 11`
- **Lead-in:** 11. d3
- **Judged user moves:**
  - 11... Nxc4 (Good, pre-move ES 0.15), reply 12. c3
  - 12... Qxd3+ (Good, pre-move ES 0.52), reply 13. Ke1
- **FEN before the answer move:** `r3k1nr/ppp2p1p/3p4/2bNp3/2n1P1Q1/2Pq4/PP4PP/R1B1KR2 b kq - 1 13`
- **Answer:** blunder 13... c6 (pre-move ES 0.50, ES after 0.06).
- **Refutation:** Rxf7.
- **Score inputs:** facepalm score 0.993, played prob 0.060, reply spread 2.00, played material 3 -9, mate ply n/a.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.052, pre-blunder spread 8.48.

#### Window 19: herring (length 4, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=1512905&ply=8
- **User rating:** 2641 (pinned Maia Elo 2587)
- **FEN before the lead-in:** `r1bqkb1r/ppp2ppp/2np1n2/4p3/4P3/2N2N2/PPPPBPPP/R1BQK2R w KQkq - 0 5`
- **Lead-in:** 5. d4
- **Judged user moves:**
  - 5... exd4 (Good, pre-move ES 0.44), reply 6. Nxd4
  - 6... Be7 (Good, pre-move ES 0.45), reply 7. O-O
  - 7... O-O (Good, pre-move ES 0.45), reply 8. Be3
  - 8... Re8 (Good, pre-move ES 0.45), reply 9. f4
- **Answer:** all safe (every judged move is Good).

#### Window 20: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=641840&ply=20
- **User rating:** 2484 (pinned Maia Elo 2433)
- **FEN before the lead-in:** `r1bqk2r/pppp1p1p/6p1/2b1P3/2P5/2P3Q1/P4PPP/R1B1KB1R w KQkq - 0 11`
- **Lead-in:** 11. Bg5
- **Judged user moves:**
  - 11... Be7 (Good, pre-move ES 0.44), reply 12. Bh6
  - 12... Bf8 (Good, pre-move ES 0.44), reply 13. Bxf8
  - 13... Kxf8 (Good, pre-move ES 0.47), reply 14. Be2
  - 14... Qe7 (Good, pre-move ES 0.50), reply 15. O-O
  - 15... Kg7 (Good, pre-move ES 0.52), reply 16. f4
- **Answer:** all safe (every judged move is Good).
