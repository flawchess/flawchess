# Blunder-check spot-check

Windows drawn the way the feature draws them (250 D-12): each slot is independently a herring (about 33%, all judged moves safe) or a blunder window, with length L uniform over 3 to 5 user moves. About 20 windows per Elo bucket, at most one per game, drawn with a fixed seed. A blunder window shows its facepalm score inputs after the answer.

Thresholds: facepalm score at least 0.7, eval band [0.10, 0.90] on the pre-move ES. A recommendation only; nothing here is wired into app code.

How to read: for each window, play through the lead-in and the judged moves on the board (the game link opens the game on FlawChess at the first judged move), decide whether the position is a fair question, then compare with the answer. A blunder window is fair when the refutation or the missed move is something a player of that rating could find. Moves are in SAN; a stored move that is not legal on the replayed board prints as its UCI with the word illegal.

### <800

#### Window 1: allowed (length 5, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=1549865&ply=35
- **User rating:** 674 (pinned Maia Elo 674)
- **FEN before the lead-in:** `r3r1k1/ppp3pp/5P2/2B3Nb/8/2P2P2/P5PP/2KRR3 b - - 0 18`
- **Lead-in:** 18... gxf6
- **Judged user moves:**
  - 19. Rxe8+ (Good, pre-move ES 0.86), reply 19... Rxe8
- **FEN before the answer move:** `4r1k1/ppp4p/5p2/2B3Nb/8/2P2P2/P5PP/2KR4 w - - 0 20`
- **Answer:** blunder 20. Ne6 (pre-move ES 0.84, ES after 0.51).
- **Refutation:** Rxe6.
- **Score inputs:** facepalm score 0.971, played prob 0.041, reply spread 1.53, line loss 3 3, mate ply n/a.

#### Window 2: mixed (length 5, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=1429418&ply=34
- **User rating:** 373 (pinned Maia Elo 600)
- **FEN before the lead-in:** `r2q1rk1/5ppp/p1pb4/4R3/3pN1Q1/5P1P/PPP4P/R5K1 w - - 2 18`
- **Lead-in:** 18. Rg5
- **Judged user moves:**
- **FEN before the answer move:** `r2q1rk1/5ppp/p1pb4/6R1/3pN1Q1/5P1P/PPP4P/R5K1 b - - 3 18`
- **Answer:** blunder 18... Qb6 (pre-move ES 0.69, ES after 0.02).
- **Refutation:** Rxg7+.
- **Missed best move:** g6.
- **Score inputs:** facepalm score 0.727, played prob 0.021, reply spread 3.21, line loss 3 1, mate ply 9.

#### Window 3: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=1919370&ply=12
- **User rating:** 694 (pinned Maia Elo 694)
- **FEN before the lead-in:** `r1bqkb1r/pppp2pp/2n5/4p3/2B1n3/2N2N2/PPP2PPP/R1BQK2R w KQkq - 0 7`
- **Lead-in:** 7. Nxe4
- **Judged user moves:**
  - 7... d5 (Good, pre-move ES 0.16), reply 8. Bxd5
  - 8... Bf5 (Good, pre-move ES 0.15), reply 9. Bxc6+
  - 9... bxc6 (Good, pre-move ES 0.14), reply 10. Nc3
  - 10... Bb4 (Good, pre-move ES 0.17), reply 11. Qxd8+
  - 11... Rxd8 (Good, pre-move ES 0.16), reply 12. O-O
- **Answer:** all safe (every judged move is Good).

#### Window 4: allowed (length 5, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=1429193&ply=37
- **User rating:** 212 (pinned Maia Elo 600)
- **FEN before the lead-in:** `r2kr3/ppp2Q1p/5p2/2bpq3/8/2NP4/PPP4P/R1BK4 b - - 0 19`
- **Lead-in:** 19... Re7
- **Judged user moves:**
  - 20. Qg8+ (Good, pre-move ES 0.17), reply 20... Re8
- **FEN before the answer move:** `r2kr1Q1/ppp4p/5p2/2bpq3/8/2NP4/PPP4P/R1BK4 w - - 3 21`
- **Answer:** blunder 21. Qxh7 (pre-move ES 0.20, ES after 0.02).
- **Refutation:** Qe1#.
- **Score inputs:** facepalm score 0.954, played prob 0.574, reply spread 5.10, line loss 3 -1, mate ply 1.

#### Window 5: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=1920524&ply=1
- **User rating:** 232 (pinned Maia Elo 600)
- **FEN before the lead-in:** `rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1`
- **Lead-in:** 1... e5
- **Judged user moves:**
  - 2. Nf3 (Good, pre-move ES 0.53), reply 2... Nf6
  - 3. Nc3 (Good, pre-move ES 0.54), reply 3... Nc6
  - 4. d4 (Good, pre-move ES 0.52), reply 4... exd4
  - 5. Nxd4 (Good, pre-move ES 0.52), reply 5... Nxd4
  - 6. Qxd4 (Good, pre-move ES 0.61), reply 6... Qe7
- **Answer:** all safe (every judged move is Good).

#### Window 6: mixed (length 3, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=1662147&ply=10
- **User rating:** 381 (pinned Maia Elo 600)
- **FEN before the lead-in:** `rnbqkb1r/pppp1ppp/4n3/4pQ2/2B3P1/8/PPPP1P1P/RNB1K1NR w KQkq - 4 6`
- **Lead-in:** 6. d3
- **Judged user moves:**
- **FEN before the answer move:** `rnbqkb1r/pppp1ppp/4n3/4pQ2/2B3P1/3P4/PPP2P1P/RNB1K1NR b KQkq - 0 6`
- **Answer:** blunder 6... Nd4 (pre-move ES 0.80, ES after 0.02).
- **Refutation:** Qxf7#.
- **Missed best move:** d5.
- **Score inputs:** facepalm score 0.993, played prob 0.133, reply spread 2.04, line loss 3 1, mate ply 1.

#### Window 7: herring (length 3, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2274977&ply=55
- **User rating:** 222 (pinned Maia Elo 600)
- **FEN before the lead-in:** `8/5ppk/3P3p/r1B5/3P4/1P4Pb/7K/4R3 b - - 2 28`
- **Lead-in:** 28... Bg4
- **Judged user moves:**
  - 29. Re4 (Good, pre-move ES 0.77), reply 29... Ra2+
  - 30. Kg1 (Good, pre-move ES 0.78), reply 30... Ra1+
  - 31. Kf2 (Good, pre-move ES 0.79), reply 31... Ra2+
- **Answer:** all safe (every judged move is Good).

#### Window 8: allowed (length 5, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=2447273&ply=23
- **User rating:** 633 (pinned Maia Elo 633)
- **FEN before the lead-in:** `rn2kb1r/1ppnq1p1/p1b1p2p/3pPp2/3P1P2/P1NB1N2/1PP1Q1PP/R1B2RK1 b kq - 0 12`
- **Lead-in:** 12... Nb6
- **Judged user moves:**
  - 13. a4 (Good, pre-move ES 0.65), reply 13... N8d7
  - 14. b3 (Good, pre-move ES 0.67), reply 14... Qb4
- **FEN before the answer move:** `r3kb1r/1ppn2p1/pnb1p2p/3pPp2/Pq1P1P2/1PNB1N2/2P1Q1PP/R1B2RK1 w kq - 1 15`
- **Answer:** blunder 15. Ba3 (pre-move ES 0.72, ES after 0.28).
- **Refutation:** Qxc3.
- **Score inputs:** facepalm score 0.915, played prob 0.159, reply spread 2.57, line loss 3 3, mate ply n/a.

#### Window 9: allowed (length 3, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=2096061&ply=24
- **User rating:** 254 (pinned Maia Elo 600)
- **FEN before the lead-in:** `r2q1rk1/p1p1bppp/2p5/2np1b2/3Q4/2N1BN2/PPP2PPP/R4RK1 w - - 1 13`
- **Lead-in:** 13. Na4
- **Judged user moves:**
  - 13... Nxa4 (Good, pre-move ES 0.66), reply 14. Bd2
  - 14... Nc5 (Good, pre-move ES 0.86), reply 15. Bc3
- **FEN before the answer move:** `r2q1rk1/p1p1bppp/2p5/2np1b2/3Q4/2B2N2/PPP2PPP/R4RK1 b - - 3 15`
- **Answer:** blunder 15... Bxc2 (pre-move ES 0.86, ES after 0.02).
- **Refutation:** Qxg7#.
- **Score inputs:** facepalm score 0.990, played prob 0.258, reply spread 1.98, line loss 3 0, mate ply 1.

#### Window 10: allowed (length 5, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=2035728&ply=9
- **User rating:** 132 (pinned Maia Elo 600)
- **FEN before the lead-in:** `r1bqkb1r/pppppppp/2n2n2/8/3PP3/2N2P2/PPP1N1PP/R1BQKB1R b KQkq - 0 5`
- **Lead-in:** 5... e5
- **Judged user moves:**
  - 6. dxe5 (Good, pre-move ES 0.63), reply 6... Nh5
- **FEN before the answer move:** `r1bqkb1r/pppp1ppp/2n5/4P2n/4P3/2N2P2/PPP1N1PP/R1BQKB1R w KQkq - 1 7`
- **Answer:** blunder 7. Bg5 (pre-move ES 0.71, ES after 0.26).
- **Refutation:** Qxg5.
- **Score inputs:** facepalm score 0.905, played prob 0.018, reply spread 6.61, line loss 3 3, mate ply n/a.

#### Window 11: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=1596992&ply=18
- **User rating:** 570 (pinned Maia Elo 600)
- **FEN before the lead-in:** `r3kb1r/pp3p1p/2n1bqp1/2P1p3/1P1pP3/P1P2P2/6PP/RN1QKBNR w KQkq - 0 10`
- **Lead-in:** 10. Bb5
- **Judged user moves:**
  - 10... Bh6 (Good, pre-move ES 0.65), reply 11. Qa4
  - 11... O-O (Good, pre-move ES 0.80), reply 12. Bxc6
  - 12... bxc6 (Good, pre-move ES 0.82), reply 13. Qxc6
  - 13... Rac8 (Good, pre-move ES 0.90), reply 14. Qa4
  - 14... d3 (Good, pre-move ES 0.88), reply 15. Nd2
- **Answer:** all safe (every judged move is Good).

#### Window 12: allowed (length 4, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=1650373&ply=5
- **User rating:** 494 (pinned Maia Elo 600)
- **FEN before the lead-in:** `rnb1kbnr/pppp1ppp/5q2/4p3/4P3/3PB3/PPP2PPP/RN1QKBNR b KQkq - 2 3`
- **Lead-in:** 3... c5
- **Judged user moves:**
- **FEN before the answer move:** `rnb1kbnr/pp1p1ppp/5q2/2p1p3/4P3/3PB3/PPP2PPP/RN1QKBNR w KQkq - 0 4`
- **Answer:** blunder 4. Bxc5 (pre-move ES 0.55, ES after 0.18).
- **Refutation:** Bxc5.
- **Score inputs:** facepalm score 0.882, played prob 0.072, reply spread 1.64, line loss 3 2, mate ply n/a.

#### Window 13: allowed (length 5, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=3277014&ply=32
- **User rating:** 450 (pinned Maia Elo 600)
- **FEN before the lead-in:** `r2r2k1/ppp2ppp/8/8/4N1P1/4bn1P/PP6/R3KB1R w KQ - 1 17`
- **Lead-in:** 17. Ke2
- **Judged user moves:**
- **FEN before the answer move:** `r2r2k1/ppp2ppp/8/8/4N1P1/4bn1P/PP2K3/R4B1R b - - 2 17`
- **Answer:** blunder 17... Nd2 (pre-move ES 0.79, ES after 0.27).
- **Refutation:** Kxe3.
- **Score inputs:** facepalm score 0.929, played prob 0.085, reply spread 3.13, line loss 3 3, mate ply n/a.

#### Window 14: allowed (length 4, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=2349734&ply=13
- **User rating:** 587 (pinned Maia Elo 600)
- **FEN before the lead-in:** `r2qkbnr/ppp2p1p/2np2p1/4p3/2B1P3/2N2Q1P/PPPP1PP1/R1B2RK1 b kq - 0 7`
- **Lead-in:** 7... Nf6
- **Judged user moves:**
  - 8. d3 (Good, pre-move ES 0.58), reply 8... Nd4
- **FEN before the answer move:** `r2qkb1r/ppp2p1p/3p1np1/4p3/2BnP3/2NP1Q1P/PPP2PP1/R1B2RK1 w kq - 1 9`
- **Answer:** blunder 9. Qe3 (pre-move ES 0.53, ES after 0.35).
- **Refutation:** Nxc2.
- **Score inputs:** facepalm score 0.945, played prob 0.427, reply spread 6.26, line loss 3 6, mate ply n/a.

#### Window 15: allowed (length 4, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=2349712&ply=26
- **User rating:** 578 (pinned Maia Elo 600)
- **FEN before the lead-in:** `rnb2rk1/pp3ppp/8/2p2N2/2B3P1/2B5/PP5P/R3K2n w - - 0 14`
- **Lead-in:** 14. Ke2
- **Judged user moves:**
- **FEN before the answer move:** `rnb2rk1/pp3ppp/8/2p2N2/2B3P1/2B5/PP2K2P/R6n b - - 1 14`
- **Answer:** blunder 14... g6 (pre-move ES 0.84, ES after 0.02).
- **Refutation:** Ne7#.
- **Score inputs:** facepalm score 0.969, played prob 0.114, reply spread 6.96, line loss 3 0, mate ply 1.

#### Window 16: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=1870342&ply=1
- **User rating:** 239 (pinned Maia Elo 600)
- **FEN before the lead-in:** `rnbqkbnr/pppppppp/8/8/3P4/8/PPP1PPPP/RNBQKBNR b KQkq - 0 1`
- **Lead-in:** 1... d5
- **Judged user moves:**
  - 2. Nc3 (Good, pre-move ES 0.53), reply 2... Nf6
  - 3. Bf4 (Good, pre-move ES 0.50), reply 3... Nc6
  - 4. Nb5 (Good, pre-move ES 0.58), reply 4... e6
  - 5. Nxc7+ (Good, pre-move ES 0.79), reply 5... Ke7
  - 6. Nxa8 (Good, pre-move ES 0.81), reply 6... Kd7
- **Answer:** all safe (every judged move is Good).

#### Window 17: herring (length 3, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=3174092&ply=20
- **User rating:** 733 (pinned Maia Elo 733)
- **FEN before the lead-in:** `r2qk2r/pp3ppp/2p2n2/2p1p3/3nP3/3PQN2/NPP2PPP/2KR1B1R w kq - 0 11`
- **Lead-in:** 11. Nxe5
- **Judged user moves:**
  - 11... Qa5 (Good, pre-move ES 0.27), reply 12. Kb1
  - 12... O-O (Good, pre-move ES 0.25), reply 13. Nc4
  - 13... Qb5 (Good, pre-move ES 0.28), reply 14. c3
- **Answer:** all safe (every judged move is Good).

#### Window 18: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2447745&ply=11
- **User rating:** 705 (pinned Maia Elo 705)
- **FEN before the lead-in:** `r1bqkb1r/ppp1pppp/2n2n2/6N1/2B5/2N5/PPPP1PPP/R1BQK2R b KQkq - 7 6`
- **Lead-in:** 6... e6
- **Judged user moves:**
  - 7. O-O (Good, pre-move ES 0.50), reply 7... h6
  - 8. Nge4 (Good, pre-move ES 0.52), reply 8... Nxe4
  - 9. Nxe4 (Good, pre-move ES 0.52), reply 9... Be7
  - 10. d3 (Good, pre-move ES 0.53), reply 10... Bd7
  - 11. a3 (Good, pre-move ES 0.57), reply 11... Nd4
- **Answer:** all safe (every judged move is Good).

#### Window 19: allowed (length 4, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=2275331&ply=15
- **User rating:** 239 (pinned Maia Elo 600)
- **FEN before the lead-in:** `r2qkb1r/ppp2ppp/3pbP2/8/2BQ4/8/PPP2PPP/RNB1K2R b KQkq - 0 8`
- **Lead-in:** 8... Bxc4
- **Judged user moves:**
  - 9. fxg7 (Good, pre-move ES 0.84), reply 9... Bxg7
  - 10. Qxg7 (Good, pre-move ES 0.83), reply 10... Qe7+
- **FEN before the answer move:** `r3k2r/ppp1qpQp/3p4/8/2b5/8/PPP2PPP/RNB1K2R w KQkq - 1 11`
- **Answer:** blunder 11. Kd1 (pre-move ES 0.83, ES after 0.02).
- **Refutation:** Qe2#.
- **Score inputs:** facepalm score 0.986, played prob 0.189, reply spread 3.49, line loss 3 0, mate ply 1.

#### Window 20: allowed (length 3, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=2746846&ply=10
- **User rating:** 711 (pinned Maia Elo 711)
- **FEN before the lead-in:** `rnbq1rk1/ppp1ppbp/3p1np1/8/8/1P2P1P1/PBPP1PBP/RN1QK1NR w KQ - 1 6`
- **Lead-in:** 6. Ne2
- **Judged user moves:**
  - 6... e5 (Good, pre-move ES 0.52), reply 7. h3
  - 7... Nc6 (Good, pre-move ES 0.53), reply 8. Ba3
- **FEN before the answer move:** `r1bq1rk1/ppp2pbp/2np1np1/4p3/8/BP2P1PP/P1PPNPB1/RN1QK2R b KQ - 2 8`
- **Answer:** blunder 8... Nd5 (pre-move ES 0.56, ES after 0.22).
- **Refutation:** Bxd5.
- **Score inputs:** facepalm score 0.845, played prob 0.017, reply spread 8.35, line loss 3 3, mate ply n/a.

### 800-1199

#### Window 1: allowed (length 3, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=2817833&ply=34
- **User rating:** 988 (pinned Maia Elo 988)
- **FEN before the lead-in:** `4rrk1/1p1q1pbp/p1p2n2/2Pp1pp1/3P1N2/4P3/PP1B1PPP/R2Q1RK1 w - - 0 18`
- **Lead-in:** 18. Ne2
- **Judged user moves:**
  - 18... Nh5 (Good, pre-move ES 0.54), reply 19. Nc3
- **FEN before the answer move:** `4rrk1/1p1q1pbp/p1p5/2Pp1ppn/3P4/2N1P3/PP1B1PPP/R2Q1RK1 b - - 3 19`
- **Answer:** blunder 19... h6 (pre-move ES 0.55, ES after 0.17).
- **Refutation:** Qxh5.
- **Score inputs:** facepalm score 0.918, played prob 0.043, reply spread 4.82, line loss 3 3, mate ply n/a.

#### Window 2: herring (length 3, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2900904&ply=1
- **User rating:** 1160 (pinned Maia Elo 1160)
- **FEN before the lead-in:** `rnbqkbnr/pppppppp/8/8/3P4/8/PPP1PPPP/RNBQKBNR b KQkq - 0 1`
- **Lead-in:** 1... d5
- **Judged user moves:**
  - 2. Nf3 (Good, pre-move ES 0.52), reply 2... Bf5
  - 3. e3 (Good, pre-move ES 0.53), reply 3... a6
  - 4. c4 (Good, pre-move ES 0.53), reply 4... e6
- **Answer:** all safe (every judged move is Good).

#### Window 3: allowed (length 4, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=2865834&ply=21
- **User rating:** 817 (pinned Maia Elo 1067)
- **FEN before the lead-in:** `r1b2rk1/1pp1nppp/p3pq2/3p4/3n1P2/2NB1N1P/PPPQ1PP1/R4RK1 b - - 1 11`
- **Lead-in:** 11... Nxf3+
- **Judged user moves:**
  - 12. gxf3 (Good, pre-move ES 0.22), reply 12... Nc6
  - 13. a3 (Good, pre-move ES 0.25), reply 13... Nd4
- **FEN before the answer move:** `r1b2rk1/1pp2ppp/p3pq2/3p4/3n1P2/P1NB1P1P/1PPQ1P2/R4RK1 w - - 1 14`
- **Answer:** blunder 14. Rfe1 (pre-move ES 0.24, ES after 0.06).
- **Refutation:** Nxf3+.
- **Score inputs:** facepalm score 0.996, played prob 0.061, reply spread 1.43, line loss 3 10, mate ply n/a.

#### Window 4: allowed (length 5, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=2961172&ply=12
- **User rating:** 966 (pinned Maia Elo 1158)
- **FEN before the lead-in:** `r1bq1rk1/ppp1bppp/2n2n2/3p4/4P3/2NP2Q1/PPP2PPP/R1B1KBNR w KQ - 0 7`
- **Lead-in:** 7. Bh6
- **Judged user moves:**
  - 7... Nh5 (Good, pre-move ES 0.72), reply 8. Qf3
- **FEN before the answer move:** `r1bq1rk1/ppp1bppp/2n4B/3p3n/4P3/2NP1Q2/PPP2PPP/R3KBNR b KQ - 3 8`
- **Answer:** blunder 8... Ne5 (pre-move ES 0.68, ES after 0.27).
- **Refutation:** Qxh5.
- **Score inputs:** facepalm score 0.971, played prob 0.036, reply spread 1.73, line loss 3 3, mate ply n/a.

#### Window 5: allowed (length 4, blunder at 4)

- **Game:** https://flawchess.com/analysis?game_id=1081253&ply=58
- **User rating:** 770 (pinned Maia Elo 1184)
- **FEN before the lead-in:** `6k1/p2n1ppp/brN5/2p5/4P3/7P/B4PP1/2R3K1 w - - 6 30`
- **Lead-in:** 30. Nxa7
- **Judged user moves:**
  - 30... c4 (Good, pre-move ES 0.50), reply 31. Bxc4
  - 31... Bxc4 (Good, pre-move ES 0.46), reply 32. Rxc4
  - 32... Rb1+ (Good, pre-move ES 0.46), reply 33. Kh2
- **FEN before the answer move:** `6k1/N2n1ppp/8/8/2R1P3/7P/5PPK/1r6 b - - 2 33`
- **Answer:** blunder 33... Ne5 (pre-move ES 0.45, ES after 0.02).
- **Refutation:** Rc8#.
- **Score inputs:** facepalm score 0.993, played prob 0.196, reply spread 1.58, line loss 3 0, mate ply 1.

#### Window 6: allowed (length 3, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=2154732&ply=28
- **User rating:** 712 (pinned Maia Elo 1193)
- **FEN before the lead-in:** `2r2rk1/p2n2pp/1p1qpnp1/3p4/3P4/1QN1P3/PP2BPPP/2R2RK1 w - - 0 15`
- **Lead-in:** 15. f4
- **Judged user moves:**
  - 15... Ne4 (Good, pre-move ES 0.39), reply 16. Nxe4
  - 16... dxe4 (Good, pre-move ES 0.36), reply 17. Bg4
- **FEN before the answer move:** `2r2rk1/p2n2pp/1p1qp1p1/8/3PpPB1/1Q2P3/PP4PP/2R2RK1 b - - 1 17`
- **Answer:** blunder 17... Rf6 (pre-move ES 0.42, ES after 0.09).
- **Refutation:** Rxc8+.
- **Score inputs:** facepalm score 0.996, played prob 0.066, reply spread 1.60, line loss 3 5, mate ply n/a.

#### Window 7: herring (length 4, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=3233892&ply=1
- **User rating:** 1500 (pinned Maia Elo 1149)
- **FEN before the lead-in:** `rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1`
- **Lead-in:** 1... c6
- **Judged user moves:**
  - 2. Nf3 (Good, pre-move ES 0.53), reply 2... d5
  - 3. e5 (Good, pre-move ES 0.52), reply 3... Bg4
  - 4. h3 (Good, pre-move ES 0.52), reply 4... Bxf3
  - 5. Qxf3 (Good, pre-move ES 0.49), reply 5... e6
- **Answer:** all safe (every judged move is Good).

#### Window 8: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2832550&ply=10
- **User rating:** 756 (pinned Maia Elo 1176)
- **FEN before the lead-in:** `r1bqk2r/ppp2ppp/2nb1n2/3pp3/8/3P1NP1/PPP1PPBP/RNBQ1RK1 w kq - 2 6`
- **Lead-in:** 6. Bg5
- **Judged user moves:**
  - 6... h6 (Good, pre-move ES 0.51), reply 7. Bxf6
  - 7... Qxf6 (Good, pre-move ES 0.50), reply 8. Nc3
  - 8... d4 (Good, pre-move ES 0.51), reply 9. Ne4
  - 9... Qe6 (Good, pre-move ES 0.48), reply 10. Nxd6+
  - 10... Qxd6 (Good, pre-move ES 0.49), reply 11. a3
- **Answer:** all safe (every judged move is Good).

#### Window 9: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2863784&ply=20
- **User rating:** 903 (pinned Maia Elo 1118)
- **FEN before the lead-in:** `r3k2r/p2b1ppp/Pp1bpq2/1Bpp4/1n6/1PP1PN2/3P1PPP/RN1QK2R w KQkq - 4 11`
- **Lead-in:** 11. Bxd7+
- **Judged user moves:**
  - 11... Kxd7 (Good, pre-move ES 0.46), reply 12. cxb4
  - 12... Qxa1 (Good, pre-move ES 0.71), reply 13. bxc5
  - 13... Bxc5 (Good, pre-move ES 0.71), reply 14. Ne5+
  - 14... Qxe5 (Good, pre-move ES 0.82), reply 15. d4
  - 15... Bb4+ (Good, pre-move ES 0.85), reply 16. Kf1
- **Answer:** all safe (every judged move is Good).

#### Window 10: herring (length 4, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2864920&ply=23
- **User rating:** 1183 (pinned Maia Elo 1183)
- **FEN before the lead-in:** `rn2k2r/p4ppp/b1p1p3/qpPp4/3P4/2P1PPP1/P1Q1N1P1/R3KB1R b KQkq - 2 12`
- **Lead-in:** 12... b4
- **Judged user moves:**
  - 13. cxb4 (Good, pre-move ES 0.62), reply 13... Qxb4+
  - 14. Kf2 (Good, pre-move ES 0.61), reply 14... h6
  - 15. g4 (Good, pre-move ES 0.62), reply 15... Nd7
  - 16. a3 (Good, pre-move ES 0.59), reply 16... Qb8
- **Answer:** all safe (every judged move is Good).

#### Window 11: allowed (length 3, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=1980609&ply=21
- **User rating:** 644 (pinned Maia Elo 1158)
- **FEN before the lead-in:** `rnbq1rk1/pp3ppp/3b1n2/1B2p3/7N/2PP1Q2/P4PPP/RNB2RK1 b - - 0 11`
- **Lead-in:** 11... a6
- **Judged user moves:**
- **FEN before the answer move:** `rnbq1rk1/1p3ppp/p2b1n2/1B2p3/7N/2PP1Q2/P4PPP/RNB2RK1 w - - 0 12`
- **Answer:** blunder 12. Na3 (pre-move ES 0.39, ES after 0.18).
- **Refutation:** axb5.
- **Score inputs:** facepalm score 0.965, played prob 0.000, reply spread 1.86, line loss 3 2, mate ply n/a.

#### Window 12: herring (length 3, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2960718&ply=80
- **User rating:** 959 (pinned Maia Elo 1154)
- **FEN before the lead-in:** `r1n4k/P3q2p/Q1p5/3p4/3PpP2/6P1/7P/R3B2K w - - 2 41`
- **Lead-in:** 41. Qxc8+
- **Judged user moves:**
  - 41... Rxc8 (Good, pre-move ES 0.80), reply 42. a8=Q
  - 42... Rxa8 (Good, pre-move ES 0.80), reply 43. Rxa8+
  - 43... Kg7 (Good, pre-move ES 0.78), reply 44. Ra4
- **Answer:** all safe (every judged move is Good).

#### Window 13: allowed (length 4, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=1983817&ply=18
- **User rating:** 727 (pinned Maia Elo 1160)
- **FEN before the lead-in:** `rn1qkb1r/1ppn1pp1/p3p2p/1B1PNb2/Q2P4/2N1P3/PP3PPP/R1B1K2R w KQkq - 0 10`
- **Lead-in:** 10. dxe6
- **Judged user moves:**
  - 10... Bxe6 (Good, pre-move ES 0.31), reply 11. d5
  - 11... Bf5 (Good, pre-move ES 0.33), reply 12. e4
- **FEN before the answer move:** `rn1qkb1r/1ppn1pp1/p6p/1B1PNb2/Q3P3/2N5/PP3PPP/R1B1K2R b KQkq - 0 12`
- **Answer:** blunder 12... Bg4 (pre-move ES 0.35, ES after 0.14).
- **Refutation:** Nxg4.
- **Score inputs:** facepalm score 0.991, played prob 0.032, reply spread 5.41, line loss 3 5, mate ply n/a.

#### Window 14: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=3059395&ply=52
- **User rating:** 1133 (pinned Maia Elo 1133)
- **FEN before the lead-in:** `8/ppk4r/2np3b/2p1p3/P3P1P1/2PP1R1P/1P1q2P1/R2Q3K w - - 3 27`
- **Lead-in:** 27. Qxd2
- **Judged user moves:**
  - 27... Bxd2 (Good, pre-move ES 0.21), reply 28. Rf8
  - 28... Bf4 (Good, pre-move ES 0.30), reply 29. Kg1
  - 29... Kb6 (Good, pre-move ES 0.27), reply 30. Kf2
  - 30... a5 (Good, pre-move ES 0.22), reply 31. h4
  - 31... Rxh4 (Good, pre-move ES 0.25), reply 32. Rf6
- **Answer:** all safe (every judged move is Good).

#### Window 15: allowed (length 4, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=3069118&ply=51
- **User rating:** 1022 (pinned Maia Elo 1192)
- **FEN before the lead-in:** `4r1k1/1p2rpp1/p1p1b2p/6PP/8/3B4/PPP2RR1/1K6 b - - 0 26`
- **Lead-in:** 26... Bc4
- **Judged user moves:**
- **FEN before the answer move:** `4r1k1/1p2rpp1/p1p4p/6PP/2b5/3B4/PPP2RR1/1K6 w - - 1 27`
- **Answer:** blunder 27. a3 (pre-move ES 0.23, ES after 0.02).
- **Refutation:** Re1#.
- **Score inputs:** facepalm score 0.991, played prob 0.177, reply spread 2.40, line loss 3 0, mate ply 1.

#### Window 16: mixed (length 5, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=2863850&ply=36
- **User rating:** 678 (pinned Maia Elo 1130)
- **FEN before the lead-in:** `r5k1/pbp2rp1/1p1p4/7p/3PP2b/2N1K2P/PPP5/R1B2R2 w - - 0 19`
- **Lead-in:** 19. Rxf7
- **Judged user moves:**
  - 19... Kxf7 (Good, pre-move ES 0.61), reply 20. Kd3
  - 20... Re8 (Good, pre-move ES 0.62), reply 21. Nb5
- **FEN before the answer move:** `4r3/pbp2kp1/1p1p4/1N5p/3PP2b/3K3P/PPP5/R1B5 b - - 3 21`
- **Answer:** blunder 21... c6 (pre-move ES 0.83, ES after 0.15).
- **Refutation:** Nxd6+.
- **Missed best move:** Bxe4+.
- **Score inputs:** facepalm score 0.823, played prob 0.015, reply spread 1.95, line loss 3 1, mate ply n/a.

#### Window 17: herring (length 3, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2854220&ply=18
- **User rating:** 877 (pinned Maia Elo 1102)
- **FEN before the lead-in:** `r1bq1rk1/ppp2pbp/2n1pnp1/3p4/8/NP1BP3/PBPP1PP1/1R1QK1NR w K - 4 10`
- **Lead-in:** 10. Qf3
- **Judged user moves:**
  - 10... e5 (Good, pre-move ES 0.73), reply 11. Qe2
  - 11... e4 (Good, pre-move ES 0.78), reply 12. Bb5
  - 12... Ne7 (Good, pre-move ES 0.78), reply 13. f3
- **Answer:** all safe (every judged move is Good).

#### Window 18: allowed (length 3, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=2503525&ply=23
- **User rating:** 825 (pinned Maia Elo 1070)
- **FEN before the lead-in:** `r2qkb1r/1p1b1pp1/pNpp3p/8/3BP3/3P4/PPP2PPP/R2Q1RK1 b kq - 1 12`
- **Lead-in:** 12... Rb8
- **Judged user moves:**
  - 13. Qe2 (Good, pre-move ES 0.73), reply 13... Be6
- **FEN before the answer move:** `1r1qkb1r/1p3pp1/pNppb2p/8/3BP3/3P4/PPP1QPPP/R4RK1 w k - 4 14`
- **Answer:** blunder 14. e5 (pre-move ES 0.72, ES after 0.25).
- **Refutation:** c5.
- **Score inputs:** facepalm score 0.865, played prob 0.162, reply spread 4.13, line loss 3 3, mate ply n/a.

#### Window 19: herring (length 4, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2544195&ply=21
- **User rating:** 1018 (pinned Maia Elo 1190)
- **FEN before the lead-in:** `rn3rk1/ppp1qppp/3p4/3P1b2/4n3/2N2N2/PPP1QPPP/2KR1B1R b - - 5 11`
- **Lead-in:** 11... Qd7
- **Judged user moves:**
  - 12. Nxe4 (Good, pre-move ES 0.70), reply 12... Bxe4
  - 13. Qxe4 (Good, pre-move ES 0.86), reply 13... Re8
  - 14. Qh4 (Good, pre-move ES 0.85), reply 14... c6
  - 15. Bd3 (Good, pre-move ES 0.87), reply 15... h6
- **Answer:** all safe (every judged move is Good).

#### Window 20: mixed (length 3, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=3237100&ply=1
- **User rating:** 761 (pinned Maia Elo 1042)
- **FEN before the lead-in:** `rnbqkbnr/pppppppp/8/8/8/4P3/PPPP1PPP/RNBQKBNR b KQkq - 0 1`
- **Lead-in:** 1... h5
- **Judged user moves:**
  - 2. d3 (Good, pre-move ES 0.56), reply 2... g5
  - 3. e4 (Good, pre-move ES 0.58), reply 3... f6
- **FEN before the answer move:** `rnbqkbnr/ppppp3/5p2/6pp/4P3/3P4/PPP2PPP/RNBQKBNR w KQkq - 0 4`
- **Answer:** blunder 4. Qxh5+ (pre-move ES 0.71, ES after 0.11).
- **Refutation:** Rxh5.
- **Missed best move:** Be2.
- **Score inputs:** facepalm score 0.999, played prob 0.001, reply spread 1.00, line loss 3 8, mate ply n/a.

### 1200-1599

#### Window 1: allowed (length 5, blunder at 5)

- **Game:** https://flawchess.com/analysis?game_id=702700&ply=16
- **User rating:** 1338 (pinned Maia Elo 1446)
- **FEN before the lead-in:** `r2qkbnr/pp1n1pp1/4p2p/2ppP3/3P4/2PQ1N2/PP3PPP/RNB2RK1 w kq - 0 9`
- **Lead-in:** 9. Be3
- **Judged user moves:**
  - 9... c4 (Good, pre-move ES 0.47), reply 10. Qc2
  - 10... Nb6 (Good, pre-move ES 0.45), reply 11. b3
  - 11... Be7 (Good, pre-move ES 0.44), reply 12. bxc4
  - 12... Nxc4 (Good, pre-move ES 0.46), reply 13. Nbd2
- **FEN before the answer move:** `r2qk1nr/pp2bpp1/4p2p/3pP3/2nP4/2P1BN2/P1QN1PPP/R4RK1 b kq - 1 13`
- **Answer:** blunder 13... a6 (pre-move ES 0.47, ES after 0.29).
- **Refutation:** Nxc4.
- **Score inputs:** facepalm score 0.721, played prob 0.002, reply spread 1.64, line loss 3 0, mate ply n/a.

#### Window 2: allowed (length 5, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=868580&ply=67
- **User rating:** 1429 (pinned Maia Elo 1587)
- **FEN before the lead-in:** `r7/1b3pk1/4p1pp/2p5/1pB3P1/1P3PKR/P2r4/7R b - - 4 34`
- **Lead-in:** 34... Raxa2
- **Judged user moves:**
  - 35. Rxh6 (Good, pre-move ES 0.17), reply 35... Rg2+
  - 36. Kf4 (Good, pre-move ES 0.16), reply 36... Raf2
- **FEN before the answer move:** `8/1b3pk1/4p1pR/2p5/1pB2KP1/1P3P2/5rr1/7R w - - 3 37`
- **Answer:** blunder 37. Kg5 (pre-move ES 0.26, ES after 0.02).
- **Refutation:** f6+.
- **Score inputs:** facepalm score 0.994, played prob 0.030, reply spread 4.37, line loss 3 5, mate ply n/a.

#### Window 3: herring (length 3, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2832538&ply=59
- **User rating:** 1051 (pinned Maia Elo 1506)
- **FEN before the lead-in:** `1b3rk1/4qpp1/2p1p2p/Q1n5/3P4/4PN1P/5PP1/2R3K1 b - - 2 30`
- **Lead-in:** 30... Qd6
- **Judged user moves:**
  - 31. Qxc5 (Good, pre-move ES 0.54), reply 31... Qxc5
  - 32. Rxc5 (Good, pre-move ES 0.55), reply 32... Bh2+
  - 33. Kxh2 (Good, pre-move ES 0.87), reply 33... g5
- **Answer:** all safe (every judged move is Good).

#### Window 4: allowed (length 3, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=1335341&ply=98
- **User rating:** 1051 (pinned Maia Elo 1448)
- **FEN before the lead-in:** `8/4r3/2p5/2bp2k1/P7/1PPKPR2/8/8 w - - 1 50`
- **Lead-in:** 50. b4
- **Judged user moves:**
- **FEN before the answer move:** `8/4r3/2p5/2bp2k1/PP6/2PKPR2/8/8 b - - 0 50`
- **Answer:** blunder 50... Kg4 (pre-move ES 0.50, ES after 0.16).
- **Refutation:** unknown.
- **Score inputs:** facepalm score 0.950, played prob 0.063, reply spread 2.59, line loss 3 3, mate ply n/a.

#### Window 5: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=1081158&ply=11
- **User rating:** 850 (pinned Maia Elo 1268)
- **FEN before the lead-in:** `r2qkb1r/ppp1pppp/2n2n2/3p4/3P4/2N1PB2/PPP2PPP/R1BQK2R b KQkq - 0 6`
- **Lead-in:** 6... e6
- **Judged user moves:**
  - 7. O-O (Good, pre-move ES 0.53), reply 7... Bb4
  - 8. Bd2 (Good, pre-move ES 0.57), reply 8... O-O
  - 9. a3 (Good, pre-move ES 0.53), reply 9... Bxc3
  - 10. Bxc3 (Good, pre-move ES 0.55), reply 10... Re8
  - 11. b4 (Good, pre-move ES 0.54), reply 11... e5
- **Answer:** all safe (every judged move is Good).

#### Window 6: herring (length 4, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=1602107&ply=17
- **User rating:** 1047 (pinned Maia Elo 1218)
- **FEN before the lead-in:** `rn2kbnr/pp3ppp/2pqp3/8/3P4/2NB1N1P/PPP2P2/R1BQ1RK1 b kq - 0 9`
- **Lead-in:** 9... Be7
- **Judged user moves:**
  - 10. Ne4 (Good, pre-move ES 0.82), reply 10... Qc7
  - 11. Re1 (Good, pre-move ES 0.83), reply 11... Nd7
  - 12. a4 (Good, pre-move ES 0.82), reply 12... Ngf6
  - 13. Nxf6+ (Good, pre-move ES 0.79), reply 13... Nxf6
- **Answer:** all safe (every judged move is Good).

#### Window 7: allowed (length 3, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=2754717&ply=10
- **User rating:** 1497 (pinned Maia Elo 1497)
- **FEN before the lead-in:** `r1bqkb1r/pp3ppp/2n2n2/2Ppp3/8/2NQ1N2/PPP1PPPP/R1B1KB1R w KQkq - 0 6`
- **Lead-in:** 6. Bg5
- **Judged user moves:**
- **FEN before the answer move:** `r1bqkb1r/pp3ppp/2n2n2/2Ppp1B1/8/2NQ1N2/PPP1PPPP/R3KB1R b KQkq - 1 6`
- **Answer:** blunder 6... h6 (pre-move ES 0.58, ES after 0.32).
- **Refutation:** Bxf6.
- **Score inputs:** facepalm score 0.846, played prob 0.011, reply spread 1.76, line loss 3 1, mate ply n/a.

#### Window 8: pure_miss (length 4, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=2613673&ply=89
- **User rating:** 1500 (pinned Maia Elo 1317)
- **FEN before the lead-in:** `8/pp6/6pk/5rB1/5R2/1P6/P1n2K1P/8 b - - 10 45`
- **Lead-in:** 45... Kh5
- **Judged user moves:**
- **FEN before the answer move:** `8/pp6/6p1/5rBk/5R2/1P6/P1n2K1P/8 w - - 11 46`
- **Answer:** blunder 46. h3 (pre-move ES 0.51, ES after 0.13).
- **Missed best move:** Rxf5.
- **Score inputs:** facepalm score 0.983, played prob 0.001, reply spread 2.89, line loss 3 3, mate ply n/a.

#### Window 9: allowed (length 4, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=2618725&ply=58
- **User rating:** 1555 (pinned Maia Elo 1369)
- **FEN before the lead-in:** `2kr3r/2p5/3b1pq1/1Q1P2p1/8/P4N1p/1P4PP/2RR3K w - - 0 30`
- **Lead-in:** 30. g3
- **Judged user moves:**
  - 30... Qe4 (Good, pre-move ES 0.43), reply 31. Qd3
- **FEN before the answer move:** `2kr3r/2p5/3b1p2/3P2p1/4q3/P2Q1NPp/1P5P/2RR3K b - - 2 31`
- **Answer:** blunder 31... Qe6 (pre-move ES 0.50, ES after 0.03).
- **Refutation:** dxe6.
- **Score inputs:** facepalm score 0.999, played prob 0.001, reply spread 1.85, line loss 3 9, mate ply n/a.

#### Window 10: allowed (length 3, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=871319&ply=27
- **User rating:** 1208 (pinned Maia Elo 1571)
- **FEN before the lead-in:** `r2q1rk1/pp2bppp/4nn2/3p1N2/4p3/8/PPPPNPPP/R1BQR1K1 b - - 6 14`
- **Lead-in:** 14... Bc5
- **Judged user moves:**
  - 15. d4 (Good, pre-move ES 0.41), reply 15... exd3
  - 16. Qxd3 (Good, pre-move ES 0.47), reply 16... Re8
- **FEN before the answer move:** `r2qr1k1/pp3ppp/4nn2/2bp1N2/8/3Q4/PPP1NPPP/R1B1R1K1 w - - 1 17`
- **Answer:** blunder 17. Nh6+ (pre-move ES 0.49, ES after 0.20).
- **Refutation:** gxh6.
- **Score inputs:** facepalm score 0.725, played prob 0.004, reply spread 1.40, line loss 3 0, mate ply n/a.

#### Window 11: allowed (length 5, blunder at 4)

- **Game:** https://flawchess.com/analysis?game_id=2493592&ply=13
- **User rating:** 1136 (pinned Maia Elo 1511)
- **FEN before the lead-in:** `r2qk1nr/pp3ppp/2nbp3/5b2/8/2P2N2/PP1PBPPP/RNBQ1RK1 b kq - 3 7`
- **Lead-in:** 7... Qc7
- **Judged user moves:**
  - 8. Re1 (Good, pre-move ES 0.65), reply 8... Nf6
  - 9. d4 (Good, pre-move ES 0.62), reply 9... Ne4
  - 10. Bd3 (Good, pre-move ES 0.77), reply 10... Nxf2
- **FEN before the answer move:** `r3k2r/ppq2ppp/2nbp3/5b2/3P4/2PB1N2/PP3nPP/RNBQR1K1 w kq - 0 11`
- **Answer:** blunder 11. Bxf5 (pre-move ES 0.76, ES after 0.21).
- **Refutation:** Nxd1.
- **Score inputs:** facepalm score 0.999, played prob 0.006, reply spread 1.14, line loss 3 6, mate ply n/a.

#### Window 12: herring (length 4, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=1311762&ply=7
- **User rating:** 1412 (pinned Maia Elo 1571)
- **FEN before the lead-in:** `rnbqkb1r/pp2pppp/2pp1n2/8/B2PP3/8/PPP2PPP/RNBQK1NR b KQkq - 1 4`
- **Lead-in:** 4... Qa5+
- **Judged user moves:**
  - 5. Nc3 (Good, pre-move ES 0.41), reply 5... Nxe4
  - 6. Bb3 (Good, pre-move ES 0.40), reply 6... Nxc3
  - 7. bxc3 (Good, pre-move ES 0.35), reply 7... Qxc3+
  - 8. Bd2 (Good, pre-move ES 0.29), reply 8... Qxd4
- **Answer:** all safe (every judged move is Good).

#### Window 13: allowed (length 5, blunder at 5)

- **Game:** https://flawchess.com/analysis?game_id=2206184&ply=22
- **User rating:** 1264 (pinned Maia Elo 1264)
- **FEN before the lead-in:** `r2q1rk1/pppnbp2/5n1p/3Np1p1/7B/4PN2/PPP2PPP/R2Q1RK1 w - - 0 12`
- **Lead-in:** 12. Nxf6+
- **Judged user moves:**
  - 12... Bxf6 (Good, pre-move ES 0.49), reply 13. Bxg5
  - 13... Bxg5 (Good, pre-move ES 0.50), reply 14. Nxg5
  - 14... hxg5 (Good, pre-move ES 0.73), reply 15. Qh5
  - 15... Qf6 (Good, pre-move ES 0.75), reply 16. Rad1
- **FEN before the answer move:** `r4rk1/pppn1p2/5q2/4p1pQ/8/4P3/PPP2PPP/3R1RK1 b - - 3 16`
- **Answer:** blunder 16... Kg7 (pre-move ES 0.75, ES after 0.28).
- **Refutation:** Rxd7.
- **Score inputs:** facepalm score 0.964, played prob 0.046, reply spread 2.05, line loss 3 3, mate ply n/a.

#### Window 14: allowed (length 3, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=2968420&ply=17
- **User rating:** 1308 (pinned Maia Elo 1428)
- **FEN before the lead-in:** `r2qk2r/ppp2ppp/2nbp1b1/3pN3/3PnB2/2PBP3/PPQN1PPP/R3K2R b KQkq - 6 9`
- **Lead-in:** 9... Nxe5
- **Judged user moves:**
  - 10. dxe5 (Good, pre-move ES 0.56), reply 10... Bc5
- **FEN before the answer move:** `r2qk2r/ppp2ppp/4p1b1/2bpP3/4nB2/2PBP3/PPQN1PPP/R3K2R w KQkq - 1 11`
- **Answer:** blunder 11. O-O-O (pre-move ES 0.60, ES after 0.32).
- **Refutation:** Nxf2.
- **Score inputs:** facepalm score 0.707, played prob 0.024, reply spread 3.31, line loss 3 1, mate ply n/a.

#### Window 15: allowed (length 5, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=1985795&ply=36
- **User rating:** 855 (pinned Maia Elo 1274)
- **FEN before the lead-in:** `2r1r1k1/pq1b1ppp/1p2pn2/nP1p4/P2P4/5N1P/N1PQBPP1/2R2RK1 w - - 3 19`
- **Lead-in:** 19. Nc3
- **Judged user moves:**
  - 19... Qc7 (Good, pre-move ES 0.57), reply 20. Qe3
  - 20... Qxc3 (Good, pre-move ES 0.82), reply 21. Bd3
- **FEN before the answer move:** `2r1r1k1/p2b1ppp/1p2pn2/nP1p4/P2P4/2qBQN1P/2P2PP1/2R2RK1 b - - 1 21`
- **Answer:** blunder 21... Nc4 (pre-move ES 0.81, ES after 0.23).
- **Refutation:** Bxh7+.
- **Score inputs:** facepalm score 0.925, played prob 0.601, reply spread 6.59, line loss 3 7, mate ply n/a.

#### Window 16: mixed (length 3, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=2129573&ply=57
- **User rating:** 1060 (pinned Maia Elo 1235)
- **FEN before the lead-in:** `q6k/6p1/3b1p1p/1p3Q2/2p2P1R/7P/1P1B2PK/4r3 b - - 1 29`
- **Lead-in:** 29... Re2
- **Judged user moves:**
- **FEN before the answer move:** `q6k/6p1/3b1p1p/1p3Q2/2p2P1R/7P/1P1Br1PK/8 w - - 2 30`
- **Answer:** blunder 30. Bc3 (pre-move ES 0.50, ES after 0.02).
- **Refutation:** Qxg2#.
- **Missed best move:** Rxh6+.
- **Score inputs:** facepalm score 0.987, played prob 0.456, reply spread 1.72, line loss 3 1, mate ply 1.

#### Window 17: allowed (length 3, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=3135813&ply=23
- **User rating:** 810 (pinned Maia Elo 1214)
- **FEN before the lead-in:** `r2qk2r/pppb1ppp/2np4/8/2B1P3/1Q1P1N1P/PP3KP1/RNB5 b kq - 2 12`
- **Lead-in:** 12... O-O
- **Judged user moves:**
- **FEN before the answer move:** `r2q1rk1/pppb1ppp/2np4/8/2B1P3/1Q1P1N1P/PP3KP1/RNB5 w - - 3 13`
- **Answer:** blunder 13. Bxf7+ (pre-move ES 0.68, ES after 0.26).
- **Refutation:** Rxf7.
- **Score inputs:** facepalm score 0.959, played prob 0.010, reply spread 1.06, line loss 3 2, mate ply n/a.

#### Window 18: allowed (length 5, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=1559719&ply=18
- **User rating:** 1277 (pinned Maia Elo 1277)
- **FEN before the lead-in:** `r2q1rk1/pppb1pbp/2n2np1/4p1B1/2B1P3/2N2N2/PPP2PPP/R2Q1RK1 w - - 4 10`
- **Lead-in:** 10. Nd5
- **Judged user moves:**
- **FEN before the answer move:** `r2q1rk1/pppb1pbp/2n2np1/3Np1B1/2B1P3/5N2/PPP2PPP/R2Q1RK1 b - - 5 10`
- **Answer:** blunder 10... Qc8 (pre-move ES 0.39, ES after 0.11).
- **Refutation:** Nxf6+.
- **Score inputs:** facepalm score 0.925, played prob 0.023, reply spread 5.45, line loss 3 3, mate ply n/a.

#### Window 19: allowed (length 5, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=1654767&ply=35
- **User rating:** 1391 (pinned Maia Elo 1481)
- **FEN before the lead-in:** `Q3k2r/p1p1npbp/4p1p1/1q6/8/P3B1N1/1PP2PPP/2K4R b k - 0 18`
- **Lead-in:** 18... Kd7
- **Judged user moves:**
- **FEN before the answer move:** `Q6r/p1pknpbp/4p1p1/1q6/8/P3B1N1/1PP2PPP/2K4R w - - 1 19`
- **Answer:** blunder 19. Qxh8 (pre-move ES 0.26, ES after 0.09).
- **Refutation:** Qxb2+.
- **Score inputs:** facepalm score 0.999, played prob 0.003, reply spread 1.92, line loss 3 5, mate ply n/a.

#### Window 20: herring (length 3, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2787444&ply=7
- **User rating:** 1072 (pinned Maia Elo 1460)
- **FEN before the lead-in:** `r1bqkb1r/pppp1ppp/2n2n2/4p1N1/2B1P3/8/PPPP1PPP/RNBQK2R b KQkq - 5 4`
- **Lead-in:** 4... d5
- **Judged user moves:**
  - 5. exd5 (Good, pre-move ES 0.52), reply 5... Nxd5
  - 6. Nxf7 (Good, pre-move ES 0.58), reply 6... Kxf7
  - 7. Qf3+ (Good, pre-move ES 0.58), reply 7... Ke8
- **Answer:** all safe (every judged move is Good).

### 1600-1999

#### Window 1: allowed (length 5, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=2041624&ply=25
- **User rating:** 1336 (pinned Maia Elo 1660)
- **FEN before the lead-in:** `r3k2r/pp3ppp/2p2n2/2n2b2/1PP5/2NP2P1/1P2PPBP/R3K2R b KQkq - 0 13`
- **Lead-in:** 13... Nb3
- **Judged user moves:**
  - 14. Ra3 (Good, pre-move ES 0.45), reply 14... Nd4
  - 15. Kd2 (Good, pre-move ES 0.44), reply 15... O-O
- **FEN before the answer move:** `r4rk1/pp3ppp/2p2n2/5b2/1PPn4/R1NP2P1/1P1KPPBP/7R w - - 5 16`
- **Answer:** blunder 16. Ra5 (pre-move ES 0.44, ES after 0.23).
- **Refutation:** Nb3+.
- **Score inputs:** facepalm score 0.951, played prob 0.002, reply spread 2.58, line loss 3 2, mate ply n/a.

#### Window 2: allowed (length 5, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=1804791&ply=26
- **User rating:** 1682 (pinned Maia Elo 1682)
- **FEN before the lead-in:** `r4rk1/1p3ppp/p1nqpnb1/3p4/6P1/P1NP1N1P/1PP1QPB1/R4RK1 w - - 0 14`
- **Lead-in:** 14. Nd1
- **Judged user moves:**
  - 14... h5 (Good, pre-move ES 0.60), reply 15. Nh2
  - 15... hxg4 (Good, pre-move ES 0.61), reply 16. hxg4
- **FEN before the answer move:** `r4rk1/1p3pp1/p1nqpnb1/3p4/6P1/P2P4/1PP1QPBN/R2N1RK1 b - - 0 16`
- **Answer:** blunder 16... Nxg4 (pre-move ES 0.61, ES after 0.27).
- **Refutation:** Qxg4.
- **Score inputs:** facepalm score 0.962, played prob 0.001, reply spread 1.95, line loss 3 2, mate ply n/a.

#### Window 3: allowed (length 4, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=551957&ply=18
- **User rating:** 1337 (pinned Maia Elo 1661)
- **FEN before the lead-in:** `rnbq1rk1/pp3ppp/4p3/2b1P3/2P1Q3/5N2/PP3PPP/R1B1KB1R w KQ - 3 10`
- **Lead-in:** 10. Bd3
- **Judged user moves:**
- **FEN before the answer move:** `rnbq1rk1/pp3ppp/4p3/2b1P3/2P1Q3/3B1N2/PP3PPP/R1B1K2R b KQ - 4 10`
- **Answer:** blunder 10... Nc6 (pre-move ES 0.28, ES after 0.02).
- **Refutation:** Qxh7#.
- **Score inputs:** facepalm score 0.994, played prob 0.187, reply spread 1.14, line loss 3 1, mate ply 1.

#### Window 4: herring (length 4, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2699112&ply=18
- **User rating:** 1728 (pinned Maia Elo 1728)
- **FEN before the lead-in:** `r2qkb1r/pp2nppp/2n1p3/3pPP2/3p4/5B2/PPP3PP/RNBQ1RK1 w kq - 1 10`
- **Lead-in:** 10. fxe6
- **Judged user moves:**
  - 10... fxe6 (Good, pre-move ES 0.58), reply 11. Bh5+
  - 11... g6 (Good, pre-move ES 0.62), reply 12. Bg4
  - 12... Nf5 (Good, pre-move ES 0.62), reply 13. Bxf5
  - 13... gxf5 (Good, pre-move ES 0.62), reply 14. Qh5+
- **Answer:** all safe (every judged move is Good).

#### Window 5: herring (length 4, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2591279&ply=28
- **User rating:** 1788 (pinned Maia Elo 1965)
- **FEN before the lead-in:** `5rk1/ppN1ppbp/2n3p1/4n1B1/8/5b1P/PP1R2P1/4KBNR w K - 0 15`
- **Lead-in:** 15. Nxf3
- **Judged user moves:**
  - 15... Nxf3+ (Good, pre-move ES 0.11), reply 16. gxf3
  - 16... Nd4 (Good, pre-move ES 0.11), reply 17. Be2
  - 17... Rc8 (Good, pre-move ES 0.12), reply 18. Kf2
  - 18... Rxc7 (Good, pre-move ES 0.14), reply 19. Rhd1
- **Answer:** all safe (every judged move is Good).

#### Window 6: allowed (length 4, blunder at 4)

- **Game:** https://flawchess.com/analysis?game_id=1992387&ply=1
- **User rating:** 1743 (pinned Maia Elo 1862)
- **FEN before the lead-in:** `rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1`
- **Lead-in:** 1... e5
- **Judged user moves:**
  - 2. Nc3 (Good, pre-move ES 0.53), reply 2... Nc6
  - 3. Bc4 (Good, pre-move ES 0.52), reply 3... Bc5
  - 4. Qg4 (Good, pre-move ES 0.53), reply 4... g6
- **FEN before the answer move:** `r1bqk1nr/pppp1p1p/2n3p1/2b1p3/2B1P1Q1/2N5/PPPP1PPP/R1B1K1NR w KQkq - 0 5`
- **Answer:** blunder 5. d3 (pre-move ES 0.55, ES after 0.21).
- **Refutation:** d5.
- **Score inputs:** facepalm score 0.942, played prob 0.102, reply spread 2.19, line loss 3 3, mate ply n/a.

#### Window 7: allowed (length 3, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=2751288&ply=22
- **User rating:** 1622 (pinned Maia Elo 1622)
- **FEN before the lead-in:** `rn1q1rk1/pbp3pp/4pn2/2p2p2/8/B1PBPN2/P4PPP/R2Q1RK1 w - - 0 12`
- **Lead-in:** 12. Bxc5
- **Judged user moves:**
  - 12... Rf7 (Good, pre-move ES 0.47), reply 13. Bc4
- **FEN before the answer move:** `rn1q2k1/pbp2rpp/4pn2/2B2p2/2B5/2P1PN2/P4PPP/R2Q1RK1 b - - 2 13`
- **Answer:** blunder 13... Bd5 (pre-move ES 0.44, ES after 0.26).
- **Refutation:** Ne5.
- **Score inputs:** facepalm score 0.705, played prob 0.090, reply spread 4.70, line loss 3 2, mate ply n/a.

#### Window 8: mixed (length 5, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=1326563&ply=16
- **User rating:** 1616 (pinned Maia Elo 1616)
- **FEN before the lead-in:** `r1bq1rk1/pppp1ppp/1bn5/4P3/2BP2n1/5N2/PP3PPP/RNBQ1RK1 w - - 3 9`
- **Lead-in:** 9. h3
- **Judged user moves:**
- **FEN before the answer move:** `r1bq1rk1/pppp1ppp/1bn5/4P3/2BP2n1/5N1P/PP3PP1/RNBQ1RK1 b - - 0 9`
- **Answer:** blunder 9... Ngxe5 (pre-move ES 0.32, ES after 0.07).
- **Refutation:** dxe5.
- **Missed best move:** d5.
- **Score inputs:** facepalm score 0.890, played prob 0.053, reply spread 1.92, line loss 3 2, mate ply n/a.

#### Window 9: allowed (length 4, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=1223001&ply=14
- **User rating:** 1293 (pinned Maia Elo 1631)
- **FEN before the lead-in:** `rnbqk2r/pp3ppp/3b1p2/2p5/2PP4/5N2/PP3PPP/R1BQKB1R w KQkq - 0 8`
- **Lead-in:** 8. d5
- **Judged user moves:**
  - 8... O-O (Good, pre-move ES 0.48), reply 9. Be3
  - 9... Re8 (Good, pre-move ES 0.50), reply 10. Be2
- **FEN before the answer move:** `rnbqr1k1/pp3ppp/3b1p2/2pP4/2P5/4BN2/PP2BPPP/R2QK2R b KQ - 4 10`
- **Answer:** blunder 10... Bf4 (pre-move ES 0.52, ES after 0.14).
- **Refutation:** Bxf4.
- **Score inputs:** facepalm score 0.988, played prob 0.002, reply spread 1.60, line loss 3 3, mate ply n/a.

#### Window 10: allowed (length 5, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=2797241&ply=22
- **User rating:** 1847 (pinned Maia Elo 1847)
- **FEN before the lead-in:** `r3kb1r/1b1p1ppp/p1n1pn2/q7/Np2P1PP/4QP2/PPPB4/2KR1BNR w kq - 2 12`
- **Lead-in:** 12. b3
- **Judged user moves:**
  - 12... Rc8 (Good, pre-move ES 0.47), reply 13. Kb1
- **FEN before the answer move:** `2r1kb1r/1b1p1ppp/p1n1pn2/q7/Np2P1PP/1P2QP2/P1PB4/1K1R1BNR b k - 2 13`
- **Answer:** blunder 13... Na7 (pre-move ES 0.44, ES after 0.17).
- **Refutation:** Qxa7.
- **Score inputs:** facepalm score 0.979, played prob 0.018, reply spread 5.23, line loss 3 4, mate ply n/a.

#### Window 11: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2597097&ply=0
- **User rating:** 2046 (pinned Maia Elo 1932)
- **FEN before the lead-in:** `rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1`
- **Lead-in:** 1. e4
- **Judged user moves:**
  - 1... c5 (Good, pre-move ES 0.47), reply 2. Nf3
  - 2... d6 (Good, pre-move ES 0.50), reply 3. Bb5+
  - 3... Bd7 (Good, pre-move ES 0.50), reply 4. Bxd7+
  - 4... Qxd7 (Good, pre-move ES 0.48), reply 5. d4
  - 5... cxd4 (Good, pre-move ES 0.50), reply 6. Nxd4
- **Answer:** all safe (every judged move is Good).

#### Window 12: allowed (length 3, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=507931&ply=35
- **User rating:** 1323 (pinned Maia Elo 1719)
- **FEN before the lead-in:** `2r2rk1/2pq1ppp/pp1Bpn2/8/1P1P4/4P3/P1Q1NPPP/2R2RK1 b - - 0 18`
- **Lead-in:** 18... cxd6
- **Judged user moves:**
- **FEN before the answer move:** `2r2rk1/3q1ppp/pp1ppn2/8/1P1P4/4P3/P1Q1NPPP/2R2RK1 w - - 0 19`
- **Answer:** blunder 19. Nf4 (pre-move ES 0.47, ES after 0.16).
- **Refutation:** Rxc2.
- **Score inputs:** facepalm score 0.997, played prob 0.000, reply spread 1.17, line loss 3 4, mate ply n/a.

#### Window 13: herring (length 3, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=485050&ply=13
- **User rating:** 1792 (pinned Maia Elo 1901)
- **FEN before the lead-in:** `rnbq1rk1/ppp2pbp/3p1np1/4P3/2P1P3/2N1BN2/PP3PPP/R2QKB1R b KQ - 0 7`
- **Lead-in:** 7... dxe5
- **Judged user moves:**
  - 8. Qxd8 (Good, pre-move ES 0.52), reply 8... Rxd8
  - 9. Nd5 (Good, pre-move ES 0.49), reply 9... Nxd5
  - 10. cxd5 (Good, pre-move ES 0.55), reply 10... c6
- **Answer:** all safe (every judged move is Good).

#### Window 14: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2759103&ply=25
- **User rating:** 1829 (pinned Maia Elo 1829)
- **FEN before the lead-in:** `r1bqr1k1/ppp2ppp/8/2b1p3/P7/2PP4/B3QPPP/R1B1R1K1 b - - 2 13`
- **Lead-in:** 13... Bd6
- **Judged user moves:**
  - 14. d4 (Good, pre-move ES 0.42), reply 14... Be6
  - 15. d5 (Good, pre-move ES 0.40), reply 15... Bd7
  - 16. Bb3 (Good, pre-move ES 0.37), reply 16... Qh4
  - 17. Qe4 (Good, pre-move ES 0.37), reply 17... Qxe4
  - 18. Rxe4 (Good, pre-move ES 0.36), reply 18... c6
- **Answer:** all safe (every judged move is Good).

#### Window 15: allowed (length 5, blunder at 5)

- **Game:** https://flawchess.com/analysis?game_id=1431068&ply=11
- **User rating:** 1248 (pinned Maia Elo 1662)
- **FEN before the lead-in:** `rnbqkb1r/ppp2ppp/4p3/8/3P4/2P1P3/P4PPP/R1BQKBNR b KQkq - 0 6`
- **Lead-in:** 6... Nc6
- **Judged user moves:**
  - 7. Be2 (Good, pre-move ES 0.57), reply 7... Bd6
  - 8. Bf3 (Good, pre-move ES 0.54), reply 8... O-O
  - 9. Ne2 (Good, pre-move ES 0.52), reply 9... e5
  - 10. O-O (Good, pre-move ES 0.53), reply 10... e4
- **FEN before the answer move:** `r1bq1rk1/ppp2ppp/2nb4/8/3Pp3/2P1PB2/P3NPPP/R1BQ1RK1 w - - 0 11`
- **Answer:** blunder 11. d5 (pre-move ES 0.59, ES after 0.15).
- **Refutation:** exf3.
- **Score inputs:** facepalm score 0.971, played prob 0.000, reply spread 1.26, line loss 3 2, mate ply n/a.

#### Window 16: herring (length 3, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2077828&ply=90
- **User rating:** 1269 (pinned Maia Elo 1616)
- **FEN before the lead-in:** `8/8/P3R3/2k5/1p6/5p2/1r6/6K1 w - - 1 46`
- **Lead-in:** 46. a7
- **Judged user moves:**
  - 46... Ra2 (Good, pre-move ES 0.82), reply 47. Rf6
  - 47... Rxa7 (Good, pre-move ES 0.85), reply 48. Rxf3
  - 48... Rb7 (Good, pre-move ES 0.84), reply 49. Rf5+
- **Answer:** all safe (every judged move is Good).

#### Window 17: allowed (length 4, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=2152420&ply=30
- **User rating:** 1294 (pinned Maia Elo 1697)
- **FEN before the lead-in:** `rn3rk1/ppq2ppp/2pbp3/8/3PB3/3QB1PP/P1P1PP1K/RR6 w - - 4 16`
- **Lead-in:** 16. a4
- **Judged user moves:**
- **FEN before the answer move:** `rn3rk1/ppq2ppp/2pbp3/8/P2PB3/3QB1PP/2P1PP1K/RR6 b - - 0 16`
- **Answer:** blunder 16... a6 (pre-move ES 0.40, ES after 0.24).
- **Refutation:** Qb3.
- **Score inputs:** facepalm score 0.794, played prob 0.002, reply spread 3.94, line loss 3 1, mate ply n/a.

#### Window 18: allowed (length 4, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=505846&ply=7
- **User rating:** 1225 (pinned Maia Elo 1648)
- **FEN before the lead-in:** `rnbqkbnr/pp3ppp/4p3/2pp4/2PP4/4PN2/PP3PPP/RNBQKB1R b KQkq - 0 4`
- **Lead-in:** 4... cxd4
- **Judged user moves:**
  - 5. cxd5 (Good, pre-move ES 0.52), reply 5... Bb4+
- **FEN before the answer move:** `rnbqk1nr/pp3ppp/4p3/3P4/1b1p4/4PN2/PP3PPP/RNBQKB1R w KQkq - 1 6`
- **Answer:** blunder 6. Nc3 (pre-move ES 0.53, ES after 0.19).
- **Refutation:** dxc3.
- **Score inputs:** facepalm score 0.985, played prob 0.008, reply spread 1.55, line loss 3 3, mate ply n/a.

#### Window 19: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2219505&ply=71
- **User rating:** 1877 (pinned Maia Elo 1964)
- **FEN before the lead-in:** `r5k1/5p1p/3p2P1/2p1n1R1/r7/8/4RPP1/6K1 b - - 0 36`
- **Lead-in:** 36... Nxg6
- **Judged user moves:**
  - 37. g3 (Good, pre-move ES 0.14), reply 37... c4
  - 38. f4 (Good, pre-move ES 0.13), reply 38... Kf8
  - 39. Rd5 (Good, pre-move ES 0.13), reply 39... R8a6
  - 40. f5 (Good, pre-move ES 0.12), reply 40... Ne5
  - 41. f6 (Good, pre-move ES 0.10), reply 41... c3
- **Answer:** all safe (every judged move is Good).

#### Window 20: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=3264242&ply=23
- **User rating:** 1909 (pinned Maia Elo 1983)
- **FEN before the lead-in:** `r1bqr1k1/pp3ppp/3b1n2/3pn3/3N4/1PN3P1/PB2PPBP/R2Q1RK1 b - - 1 12`
- **Lead-in:** 12... a6
- **Judged user moves:**
  - 13. Nxd5 (Good, pre-move ES 0.60), reply 13... Nxd5
  - 14. Bxd5 (Good, pre-move ES 0.60), reply 14... Ng4
  - 15. Bg2 (Good, pre-move ES 0.68), reply 15... Be5
  - 16. e3 (Good, pre-move ES 0.66), reply 16... Qb6
  - 17. Qe2 (Good, pre-move ES 0.66), reply 17... Bxd4
- **Answer:** all safe (every judged move is Good).

### 2000-2399

#### Window 1: mixed (length 5, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=510186&ply=38
- **User rating:** 1854 (pinned Maia Elo 2063)
- **FEN before the lead-in:** `r3r1k1/pp3pb1/2p2np1/7p/3Pp3/6Pb/qPQ1PPNP/3RRBK1 w - - 0 20`
- **Lead-in:** 20. e3
- **Judged user moves:**
- **FEN before the answer move:** `r3r1k1/pp3pb1/2p2np1/7p/3Pp3/4P1Pb/qPQ2PNP/3RRBK1 b - - 0 20`
- **Answer:** blunder 20... Qd5 (pre-move ES 0.86, ES after 0.64).
- **Refutation:** Nf4.
- **Missed best move:** Qa5.
- **Score inputs:** facepalm score 0.938, played prob 0.090, reply spread 2.62, line loss 3 3, mate ply n/a.

#### Window 2: allowed (length 5, blunder at 4)

- **Game:** https://flawchess.com/analysis?game_id=609039&ply=24
- **User rating:** 2017 (pinned Maia Elo 2112)
- **FEN before the lead-in:** `rnbk3r/ppp2qpp/3b4/8/8/3P1NR1/PPP1Q3/RNB1K3 w Q - 3 13`
- **Lead-in:** 13. Bg5+
- **Judged user moves:**
  - 13... Kd7 (Good, pre-move ES 0.61), reply 14. Ne5+
  - 14... Bxe5 (Good, pre-move ES 0.72), reply 15. Re3
  - 15... Bd6 (Good, pre-move ES 0.72), reply 16. Nc3
- **FEN before the answer move:** `rnb4r/pppk1qpp/3b4/6B1/8/2NPR3/PPP1Q3/R3K3 b Q - 3 16`
- **Answer:** blunder 16... Nc6 (pre-move ES 0.69, ES after 0.02).
- **Refutation:** Qg4+.
- **Score inputs:** facepalm score 0.982, played prob 0.339, reply spread 3.21, line loss 3 0, mate ply 3.

#### Window 3: allowed (length 5, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=3021708&ply=26
- **User rating:** 2333 (pinned Maia Elo 2237)
- **FEN before the lead-in:** `r4rk1/1p2ppbp/p2p1np1/q1pP4/2P1PP2/2N1BQ2/PP4PP/R4RK1 w - - 2 14`
- **Lead-in:** 14. h3
- **Judged user moves:**
  - 14... b5 (Good, pre-move ES 0.54), reply 15. e5
- **FEN before the answer move:** `r4rk1/4ppbp/p2p1np1/qppPP3/2P2P2/2N1BQ1P/PP4P1/R4RK1 b - - 0 15`
- **Answer:** blunder 15... bxc4 (pre-move ES 0.50, ES after 0.23).
- **Refutation:** exf6.
- **Score inputs:** facepalm score 0.916, played prob 0.001, reply spread 1.09, line loss 3 1, mate ply n/a.

#### Window 4: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=626413&ply=29
- **User rating:** 2019 (pinned Maia Elo 2084)
- **FEN before the lead-in:** `r6r/pp1qkppp/4p3/4Pb2/7Q/2N5/PP3PPP/R3K2R b KQ - 1 15`
- **Lead-in:** 15... Kf8
- **Judged user moves:**
  - 16. O-O (Good, pre-move ES 0.59), reply 16... Qe7
  - 17. Qa4 (Good, pre-move ES 0.58), reply 17... g6
  - 18. Rad1 (Good, pre-move ES 0.65), reply 18... Kg7
  - 19. Rd7 (Good, pre-move ES 0.67), reply 19... Qe8
  - 20. Rfd1 (Good, pre-move ES 0.81), reply 20... Rd8
- **Answer:** all safe (every judged move is Good).

#### Window 5: allowed (length 4, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=574335&ply=79
- **User rating:** 1912 (pinned Maia Elo 2091)
- **FEN before the lead-in:** `8/1p3p1k/2b3p1/4b3/P7/1P1B2pP/4N1P1/3R3K b - - 3 40`
- **Lead-in:** 40... f6
- **Judged user moves:**
  - 41. Nxg3 (Good, pre-move ES 0.88), reply 41... Bxg3
- **FEN before the answer move:** `8/1p5k/2b2pp1/8/P7/1P1B2bP/6P1/3R3K w - - 0 42`
- **Answer:** blunder 42. Bxg6+ (pre-move ES 0.87, ES after 0.53).
- **Refutation:** Kxg6.
- **Score inputs:** facepalm score 0.973, played prob 0.000, reply spread 1.04, line loss 3 2, mate ply n/a.

#### Window 6: mixed (length 3, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=2496230&ply=40
- **User rating:** 1852 (pinned Maia Elo 2007)
- **FEN before the lead-in:** `2r3k1/3nb2N/1q3np1/1p1p4/8/1P1pP2Q/1BPP2PP/R5K1 w - - 0 21`
- **Lead-in:** 21. Nxf6+
- **Judged user moves:**
- **FEN before the answer move:** `2r3k1/3nb3/1q3Np1/1p1p4/8/1P1pP2Q/1BPP2PP/R5K1 b - - 0 21`
- **Answer:** blunder 21... Nxf6 (pre-move ES 0.51, ES after 0.10).
- **Refutation:** Qxc8+.
- **Missed best move:** Bxf6.
- **Score inputs:** facepalm score 0.799, played prob 0.212, reply spread 1.55, line loss 3 2, mate ply n/a.

#### Window 7: herring (length 4, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=3020580&ply=1
- **User rating:** 2226 (pinned Maia Elo 2226)
- **FEN before the lead-in:** `rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1`
- **Lead-in:** 1... c5
- **Judged user moves:**
  - 2. Nf3 (Good, pre-move ES 0.53), reply 2... Nc6
  - 3. d4 (Good, pre-move ES 0.53), reply 3... cxd4
  - 4. Nxd4 (Good, pre-move ES 0.54), reply 4... e5
  - 5. Nb3 (Good, pre-move ES 0.55), reply 5... f5
- **Answer:** all safe (every judged move is Good).

#### Window 8: allowed (length 4, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=496997&ply=47
- **User rating:** 1965 (pinned Maia Elo 2123)
- **FEN before the lead-in:** `r2qk2r/4bp2/1pn1b3/p2PP3/3P2p1/1P4B1/2NN1P2/R2QR1K1 b kq - 0 24`
- **Lead-in:** 24... Bxd5
- **Judged user moves:**
- **FEN before the answer move:** `r2qk2r/4bp2/1pn5/p2bP3/3P2p1/1P4B1/2NN1P2/R2QR1K1 w kq - 0 25`
- **Answer:** blunder 25. Nc4 (pre-move ES 0.31, ES after 0.02).
- **Refutation:** Rh1#.
- **Score inputs:** facepalm score 0.998, played prob 0.015, reply spread 2.24, line loss 3 0, mate ply 1.

#### Window 9: allowed (length 4, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=1898054&ply=107
- **User rating:** 2070 (pinned Maia Elo 2024)
- **FEN before the lead-in:** `5K2/8/6R1/2kn4/8/2p5/7P/8 b - - 0 54`
- **Lead-in:** 54... c2
- **Judged user moves:**
- **FEN before the answer move:** `5K2/8/6R1/2kn4/8/8/2p4P/8 w - - 0 55`
- **Answer:** blunder 55. Rg5 (pre-move ES 0.54, ES after 0.03).
- **Refutation:** c1=Q.
- **Score inputs:** facepalm score 0.720, played prob 0.001, reply spread 1.95, line loss 3 0, mate ply n/a.

#### Window 10: allowed (length 3, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=3028334&ply=35
- **User rating:** 2074 (pinned Maia Elo 2027)
- **FEN before the lead-in:** `r6k/ppp3pp/3pbrq1/4p3/4P3/2P2N1P/PP3PPK/R2Q1R2 b - - 1 18`
- **Lead-in:** 18... Raf8
- **Judged user moves:**
- **FEN before the answer move:** `5r1k/ppp3pp/3pbrq1/4p3/4P3/2P2N1P/PP3PPK/R2Q1R2 w - - 2 19`
- **Answer:** blunder 19. Nd2 (pre-move ES 0.21, ES after 0.06).
- **Refutation:** Bxh3.
- **Score inputs:** facepalm score 0.998, played prob 0.016, reply spread 2.15, line loss 3 6, mate ply n/a.

#### Window 11: allowed (length 4, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=1509017&ply=2
- **User rating:** 2011 (pinned Maia Elo 2154)
- **FEN before the lead-in:** `rnbqkb1r/pppppppp/5n2/8/3P4/8/PPP1PPPP/RNBQKBNR w KQkq - 1 2`
- **Lead-in:** 2. c4
- **Judged user moves:**
  - 2... g6 (Good, pre-move ES 0.48), reply 3. Nc3
- **FEN before the answer move:** `rnbqkb1r/pppppp1p/5np1/8/2PP4/2N5/PP2PPPP/R1BQKBNR b KQkq - 1 3`
- **Answer:** blunder 3... Bh6 (pre-move ES 0.47, ES after 0.11).
- **Refutation:** Bxh6.
- **Score inputs:** facepalm score 0.991, played prob 0.000, reply spread 1.33, line loss 3 3, mate ply n/a.

#### Window 12: allowed (length 3, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=1227979&ply=43
- **User rating:** 2158 (pinned Maia Elo 2082)
- **FEN before the lead-in:** `1r1r4/p1p1qp1k/6pp/2p1Pb2/5P2/1PPp4/P2Q2PP/2NR1RK1 b - - 1 22`
- **Lead-in:** 22... h5
- **Judged user moves:**
- **FEN before the answer move:** `1r1r4/p1p1qp1k/6p1/2p1Pb1p/5P2/1PPp4/P2Q2PP/2NR1RK1 w - - 0 23`
- **Answer:** blunder 23. Nxd3 (pre-move ES 0.41, ES after 0.18).
- **Refutation:** Rxd3.
- **Score inputs:** facepalm score 0.982, played prob 0.009, reply spread 2.05, line loss 3 3, mate ply n/a.

#### Window 13: herring (length 3, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=611652&ply=68
- **User rating:** 2109 (pinned Maia Elo 2210)
- **FEN before the lead-in:** `7r/5qbr/1p1k1p2/p1pPpPp1/P1P1B1p1/1P1Q1K1P/7R/7R w - - 0 35`
- **Lead-in:** 35. Kxg4
- **Judged user moves:**
  - 35... Rh4+ (Good, pre-move ES 0.69), reply 36. Kg3
  - 36... Rf4 (Good, pre-move ES 0.68), reply 37. Qe3
  - 37... Qh5 (Good, pre-move ES 0.72), reply 38. Bf3
- **Answer:** all safe (every judged move is Good).

#### Window 14: herring (length 4, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=1231555&ply=29
- **User rating:** 1946 (pinned Maia Elo 2073)
- **FEN before the lead-in:** `r3k2r/2p2pp1/pbnp1q2/1P2p2p/R3P3/2P2Q1P/3P1PP1/1NB2RK1 b kq - 0 15`
- **Lead-in:** 15... Qxf3
- **Judged user moves:**
  - 16. gxf3 (Good, pre-move ES 0.47), reply 16... Nb8
  - 17. Na3 (Good, pre-move ES 0.50), reply 17... O-O
  - 18. bxa6 (Good, pre-move ES 0.53), reply 18... Rxa6
  - 19. Rxa6 (Good, pre-move ES 0.50), reply 19... Nxa6
- **Answer:** all safe (every judged move is Good).

#### Window 15: allowed (length 5, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=509604&ply=15
- **User rating:** 1983 (pinned Maia Elo 2092)
- **FEN before the lead-in:** `r3kbnr/pp1b1ppp/1qn1p3/3pP3/3P4/2N2N2/PP2BPPP/R1BQK2R b KQkq - 4 8`
- **Lead-in:** 8... Nge7
- **Judged user moves:**
  - 9. O-O (Good, pre-move ES 0.56), reply 9... Nf5
- **FEN before the answer move:** `r3kb1r/pp1b1ppp/1qn1p3/3pPn2/3P4/2N2N2/PP2BPPP/R1BQ1RK1 w kq - 7 10`
- **Answer:** blunder 10. a3 (pre-move ES 0.56, ES after 0.36).
- **Refutation:** Nfxd4.
- **Score inputs:** facepalm score 0.811, played prob 0.010, reply spread 2.68, line loss 3 1, mate ply n/a.

#### Window 16: allowed (length 5, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=2627915&ply=97
- **User rating:** 2120 (pinned Maia Elo 2120)
- **FEN before the lead-in:** `8/8/8/1R4P1/Pk1p4/2pKb3/8/8 b - - 2 49`
- **Lead-in:** 49... Kxa4
- **Judged user moves:**
- **FEN before the answer move:** `8/8/8/1R4P1/k2p4/2pKb3/8/8 w - - 0 50`
- **Answer:** blunder 50. Rb7 (pre-move ES 0.88, ES after 0.51).
- **Refutation:** Bxg5.
- **Score inputs:** facepalm score 0.720, played prob 0.075, reply spread 1.30, line loss 3 1, mate ply n/a.

#### Window 17: herring (length 3, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=764033&ply=23
- **User rating:** 2403 (pinned Maia Elo 2297)
- **FEN before the lead-in:** `r4rk1/ppqn1pbp/2pp1np1/3Pp3/2P1P3/2N1BQP1/PP3PBP/R3R1K1 b - - 0 12`
- **Lead-in:** 12... c5
- **Judged user moves:**
  - 13. Qe2 (Good, pre-move ES 0.63), reply 13... a6
  - 14. Rf1 (Good, pre-move ES 0.63), reply 14... h6
  - 15. a4 (Good, pre-move ES 0.64), reply 15... Rab8
- **Answer:** all safe (every judged move is Good).

#### Window 18: allowed (length 3, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=2073164&ply=9
- **User rating:** 2500 (pinned Maia Elo 2380)
- **FEN before the lead-in:** `rnbqkb1r/ppp1pppp/5n2/3p4/3P1B2/3B4/PPP1NPPP/RN1QK2R b KQkq - 1 5`
- **Lead-in:** 5... c5
- **Judged user moves:**
- **FEN before the answer move:** `rnbqkb1r/pp2pppp/5n2/2pp4/3P1B2/3B4/PPP1NPPP/RN1QK2R w KQkq - 0 6`
- **Answer:** blunder 6. O-O (pre-move ES 0.45, ES after 0.18).
- **Refutation:** c4.
- **Score inputs:** facepalm score 0.908, played prob 0.012, reply spread 3.39, line loss 3 2, mate ply n/a.

#### Window 19: allowed (length 4, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=2836716&ply=52
- **User rating:** 2237 (pinned Maia Elo 2237)
- **FEN before the lead-in:** `8/1p3kpp/2p5/p4p2/2P2P2/1P2K3/Pr3P1P/R7 w - - 2 27`
- **Lead-in:** 27. Kd4
- **Judged user moves:**
  - 27... Rxf2 (Good, pre-move ES 0.69), reply 28. Kc5
  - 28... Rxf4 (Good, pre-move ES 0.69), reply 29. Kb6
- **FEN before the answer move:** `8/1p3kpp/1Kp5/p4p2/2P2r2/1P6/P6P/R7 b - - 1 29`
- **Answer:** blunder 29... a4 (pre-move ES 0.70, ES after 0.49).
- **Refutation:** Kxb7.
- **Score inputs:** facepalm score 0.712, played prob 0.514, reply spread 1.27, line loss 3 2, mate ply n/a.

#### Window 20: allowed (length 5, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=611865&ply=74
- **User rating:** 2117 (pinned Maia Elo 2181)
- **FEN before the lead-in:** `3r2k1/5pp1/4p2p/1q1p4/3n4/4QP1P/5PK1/3R4 w - - 0 38`
- **Lead-in:** 38. Rxd4
- **Judged user moves:**
  - 38... Qd7 (Good, pre-move ES 0.81), reply 39. Rg4
- **FEN before the answer move:** `3r2k1/3q1pp1/4p2p/3p4/6R1/4QP1P/5PK1/8 b - - 2 39`
- **Answer:** blunder 39... Qd6 (pre-move ES 0.80, ES after 0.64).
- **Refutation:** Qxh6.
- **Score inputs:** facepalm score 0.874, played prob 0.007, reply spread 1.50, line loss 3 1, mate ply n/a.

### 2400+

#### Window 1: allowed (length 5, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=1522904&ply=92
- **User rating:** 2505 (pinned Maia Elo 2505)
- **FEN before the lead-in:** `7k/8/6R1/p2p3N/Pp5p/1Pb5/4r3/1K6 w - - 5 47`
- **Lead-in:** 47. Nf4
- **Judged user moves:**
  - 47... Kh7 (Good, pre-move ES 0.75), reply 48. Rd6
- **FEN before the answer move:** `8/7k/3R4/p2p4/Pp3N1p/1Pb5/4r3/1K6 b - - 8 48`
- **Answer:** blunder 48... d4 (pre-move ES 0.82, ES after 0.12).
- **Refutation:** Nxe2.
- **Score inputs:** facepalm score 0.997, played prob 0.030, reply spread 1.61, line loss 3 5, mate ply n/a.

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

#### Window 4: allowed (length 3, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=658043&ply=72
- **User rating:** 2617 (pinned Maia Elo 2571)
- **FEN before the lead-in:** `8/7p/2p1bkp1/1p3p2/4q3/1P5P/P3N1P1/3Q3K w - - 0 37`
- **Lead-in:** 37. Nd4
- **Judged user moves:**
  - 37... Bd5 (Good, pre-move ES 0.70), reply 38. Nf3
- **FEN before the answer move:** `8/7p/2p2kp1/1p1b1p2/4q3/1P3N1P/P5P1/3Q3K b - - 3 38`
- **Answer:** blunder 38... Kf7 (pre-move ES 0.67, ES after 0.09).
- **Refutation:** Ng5+.
- **Score inputs:** facepalm score 0.998, played prob 0.005, reply spread 2.10, line loss 3 6, mate ply n/a.

#### Window 5: allowed (length 4, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=1530400&ply=73
- **User rating:** 3081 (pinned Maia Elo 2600)
- **FEN before the lead-in:** `8/p1pR2pk/4P2p/8/4r3/1P5P/PB3bP1/5n1K b - - 6 37`
- **Lead-in:** 37... Ng3+
- **Judged user moves:**
  - 38. Kh2 (Good, pre-move ES 0.18), reply 38... Nf5
- **FEN before the answer move:** `8/p1pR2pk/4P2p/5n2/4r3/1P5P/PB3bPK/8 w - - 9 39`
- **Answer:** blunder 39. Rf7 (pre-move ES 0.14, ES after 0.02).
- **Refutation:** Bg3+.
- **Score inputs:** facepalm score 0.994, played prob 0.135, reply spread 1.48, line loss 3 0, mate ply 3.

#### Window 6: allowed (length 4, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=658045&ply=83
- **User rating:** 2607 (pinned Maia Elo 2565)
- **FEN before the lead-in:** `8/6k1/2RP4/p3p1PP/n1p1P3/P1r5/3K4/8 b - - 0 42`
- **Lead-in:** 42... Rd3+
- **Judged user moves:**
  - 43. Kc2 (Good, pre-move ES 0.79), reply 43... Rc3+
  - 44. Kb1 (Good, pre-move ES 0.77), reply 44... Rb3+
- **FEN before the answer move:** `8/6k1/2RP4/p3p1PP/n1p1P3/Pr6/8/1K6 w - - 5 45`
- **Answer:** blunder 45. Ka2 (pre-move ES 0.70, ES after 0.02).
- **Refutation:** Nc3+.
- **Score inputs:** facepalm score 0.997, played prob 0.019, reply spread 2.66, line loss 3 0, mate ply 3.

#### Window 7: allowed (length 3, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=1508683&ply=82
- **User rating:** 2886 (pinned Maia Elo 2600)
- **FEN before the lead-in:** `8/5k2/p4p2/1rp5/2K5/1P4P1/2R2P2/8 w - - 1 42`
- **Lead-in:** 42. Ra2
- **Judged user moves:**
- **FEN before the answer move:** `8/5k2/p4p2/1rp5/2K5/1P4P1/R4P2/8 b - - 2 42`
- **Answer:** blunder 42... Ke6 (pre-move ES 0.49, ES after 0.05).
- **Refutation:** Rxa6+.
- **Score inputs:** facepalm score 0.999, played prob 0.002, reply spread 1.06, line loss 3 6, mate ply n/a.

#### Window 8: allowed (length 5, blunder at 4)

- **Game:** https://flawchess.com/analysis?game_id=1526033&ply=49
- **User rating:** 2449 (pinned Maia Elo 2449)
- **FEN before the lead-in:** `1r2qr2/p3kp1Q/2p1p3/2pp4/5N2/2PP1R2/Pb4PP/5R1K b - - 2 25`
- **Lead-in:** 25... Kd6
- **Judged user moves:**
  - 26. Nxe6 (Good, pre-move ES 0.53), reply 26... Qxe6
  - 27. Rf6 (Good, pre-move ES 0.49), reply 27... Bxc3
  - 28. Rxe6+ (Good, pre-move ES 0.50), reply 28... fxe6
- **FEN before the answer move:** `1r3r2/p6Q/2pkp3/2pp4/8/2bP4/P5PP/5R1K w - - 0 29`
- **Answer:** blunder 29. Rxf8 (pre-move ES 0.49, ES after 0.02).
- **Refutation:** Rb1+.
- **Score inputs:** facepalm score 0.991, played prob 0.215, reply spread 1.99, line loss 3 -5, mate ply 3.

#### Window 9: allowed (length 4, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=2876090&ply=28
- **User rating:** 2276 (pinned Maia Elo 2426)
- **FEN before the lead-in:** `r4rk1/pp1n1pp1/3q3p/2pPn3/P1B5/5PB1/1P3P1P/R2Q1RK1 w - - 2 15`
- **Lead-in:** 15. Bb5
- **Judged user moves:**
- **FEN before the answer move:** `r4rk1/pp1n1pp1/3q3p/1BpPn3/P7/5PB1/1P3P1P/R2Q1RK1 b - - 3 15`
- **Answer:** blunder 15... Qg6 (pre-move ES 0.39, ES after 0.19).
- **Refutation:** f4.
- **Score inputs:** facepalm score 0.719, played prob 0.252, reply spread 2.55, line loss 3 2, mate ply n/a.

#### Window 10: mixed (length 5, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=1529725&ply=137
- **User rating:** 2999 (pinned Maia Elo 2600)
- **FEN before the lead-in:** `8/1p2K3/8/8/8/R7/8/kq6 b - - 1 69`
- **Lead-in:** 69... Qa2
- **Judged user moves:**
- **FEN before the answer move:** `8/1p2K3/8/8/8/R7/q7/k7 w - - 2 70`
- **Answer:** blunder 70. Rf3 (pre-move ES 0.50, ES after 0.02).
- **Refutation:** Qe2+.
- **Missed best move:** Rxa2+.
- **Score inputs:** facepalm score 0.996, played prob 0.032, reply spread 2.63, line loss 3 5, mate ply n/a.

#### Window 11: herring (length 3, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=642784&ply=13
- **User rating:** 2644 (pinned Maia Elo 2589)
- **FEN before the lead-in:** `rn1qkb1r/pp3ppp/2p1pn2/3p3b/2PP2P1/2N1PN1P/PP3P2/R1BQKB1R b KQkq - 0 7`
- **Lead-in:** 7... Bg6
- **Judged user moves:**
  - 8. Ne5 (Good, pre-move ES 0.54), reply 8... Nbd7
  - 9. Nxg6 (Good, pre-move ES 0.53), reply 9... hxg6
  - 10. g5 (Good, pre-move ES 0.53), reply 10... Ne4
- **Answer:** all safe (every judged move is Good).

#### Window 12: allowed (length 5, blunder at 5)

- **Game:** https://flawchess.com/analysis?game_id=640296&ply=91
- **User rating:** 2588 (pinned Maia Elo 2588)
- **FEN before the lead-in:** `8/p4p2/4rP2/Ppp1Pk1p/3p2r1/1P3K2/2P2R2/4R3 b - - 1 46`
- **Lead-in:** 46... c4
- **Judged user moves:**
  - 47. Ke2+ (Good, pre-move ES 0.17), reply 47... Kg5
  - 48. Kd2 (Good, pre-move ES 0.21), reply 48... d3
  - 49. bxc4 (Good, pre-move ES 0.50), reply 49... b4
  - 50. cxd3 (Good, pre-move ES 0.69), reply 50... b3
- **FEN before the answer move:** `8/p4p2/4rP2/P3P1kp/2P3r1/1p1P4/3K1R2/4R3 w - - 0 51`
- **Answer:** blunder 51. d4 (pre-move ES 0.79, ES after 0.50).
- **Refutation:** Rxd4+.
- **Score inputs:** facepalm score 0.898, played prob 0.002, reply spread 1.47, line loss 3 1, mate ply n/a.

#### Window 13: herring (length 3, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=658202&ply=58
- **User rating:** 2636 (pinned Maia Elo 2583)
- **FEN before the lead-in:** `r5k1/1p4p1/1bp1p2p/p2n4/P7/1P1R1NBP/2P3PK/8 w - - 0 30`
- **Lead-in:** 30. c4
- **Judged user moves:**
  - 30... Nf6 (Good, pre-move ES 0.56), reply 31. Ne5
  - 31... Rd8 (Good, pre-move ES 0.61), reply 32. Rxd8+
  - 32... Bxd8 (Good, pre-move ES 0.60), reply 33. Kg1
- **Answer:** all safe (every judged move is Good).

#### Window 14: allowed (length 3, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=615317&ply=29
- **User rating:** 2420 (pinned Maia Elo 2414)
- **FEN before the lead-in:** `r4rk1/pQ2ppbp/2pp1np1/8/2P2B2/2N2PPq/PP3P1P/R4RK1 b - - 3 15`
- **Lead-in:** 15... Rfe8
- **Judged user moves:**
  - 16. Qxc6 (Good, pre-move ES 0.51), reply 16... Nh5
- **FEN before the answer move:** `r3r1k1/p3ppbp/2Qp2p1/7n/2P2B2/2N2PPq/PP3P1P/R4RK1 w - - 1 17`
- **Answer:** blunder 17. Qa4 (pre-move ES 0.54, ES after 0.26).
- **Refutation:** Nxf4.
- **Score inputs:** facepalm score 0.769, played prob 0.000, reply spread 1.28, line loss 3 0, mate ply n/a.

#### Window 15: mixed (length 3, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=656186&ply=73
- **User rating:** 2624 (pinned Maia Elo 2576)
- **FEN before the lead-in:** `5n1r/1R1b2k1/P2p1q2/1NpPp3/2P1P3/5p2/2Q2BP1/6K1 b - - 1 37`
- **Lead-in:** 37... fxg2
- **Judged user moves:**
- **FEN before the answer move:** `5n1r/1R1b2k1/P2p1q2/1NpPp3/2P1P3/8/2Q2Bp1/6K1 w - - 0 38`
- **Answer:** blunder 38. Bg3 (pre-move ES 0.58, ES after 0.02).
- **Refutation:** Qf1#.
- **Missed best move:** Qd3.
- **Score inputs:** facepalm score 0.997, played prob 0.055, reply spread 1.49, line loss 3 0, mate ply 1.

#### Window 16: allowed (length 5, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=642185&ply=25
- **User rating:** 2614 (pinned Maia Elo 2569)
- **FEN before the lead-in:** `r2qk2r/pp3ppp/2p1pn2/P4b2/2NP4/2n3P1/4PPBP/R1B1QRK1 b kq - 1 13`
- **Lead-in:** 13... Qxd4
- **Judged user moves:**
- **FEN before the answer move:** `r3k2r/pp3ppp/2p1pn2/P4b2/2Nq4/2n3P1/4PPBP/R1B1QRK1 w kq - 0 14`
- **Answer:** blunder 14. Bb2 (pre-move ES 0.66, ES after 0.46).
- **Refutation:** Qxc4.
- **Score inputs:** facepalm score 0.909, played prob 0.367, reply spread 1.20, line loss 3 3, mate ply n/a.

#### Window 17: allowed (length 4, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=1517409&ply=81
- **User rating:** 2882 (pinned Maia Elo 2600)
- **FEN before the lead-in:** `4r1k1/1b3p2/5Rp1/3Pn2p/1p2PN2/5B1P/3r2P1/1R5K b - - 9 41`
- **Lead-in:** 41... Bc8
- **Judged user moves:**
  - 42. Rxb4 (Good, pre-move ES 0.50), reply 42... Kg7
  - 43. Rfb6 (Good, pre-move ES 0.49), reply 43... h4
- **FEN before the answer move:** `2b1r3/5pk1/1R4p1/3Pn3/1R2PN1p/5B1P/3r2P1/7K w - - 0 44`
- **Answer:** blunder 44. Ne2 (pre-move ES 0.51, ES after 0.21).
- **Refutation:** Nxf3.
- **Score inputs:** facepalm score 0.977, played prob 0.015, reply spread 2.30, line loss 3 3, mate ply n/a.

#### Window 18: allowed (length 5, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=616593&ply=30
- **User rating:** 2509 (pinned Maia Elo 2600)
- **FEN before the lead-in:** `1nr2rk1/2p2ppp/pp1qpn2/8/Q2Pp3/2P3P1/PP1N1PBP/R4RK1 w - - 0 16`
- **Lead-in:** 16. Nxe4
- **Judged user moves:**
  - 16... Nxe4 (Good, pre-move ES 0.47), reply 17. Bxe4
  - 17... c5 (Good, pre-move ES 0.46), reply 18. Rad1
- **FEN before the answer move:** `1nr2rk1/5ppp/pp1qp3/2p5/Q2PB3/2P3P1/PP3P1P/3R1RK1 b - - 1 18`
- **Answer:** blunder 18... Rfd8 (pre-move ES 0.46, ES after 0.28).
- **Refutation:** Bb7.
- **Score inputs:** facepalm score 0.849, played prob 0.057, reply spread 2.91, line loss 3 2, mate ply n/a.

#### Window 19: allowed (length 3, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=1512249&ply=26
- **User rating:** 2780 (pinned Maia Elo 2600)
- **FEN before the lead-in:** `r1b2rk1/p4ppp/2p1p3/2q5/8/8/PPPB1PPP/R2QK2R w KQ - 0 14`
- **Lead-in:** 14. Bc3
- **Judged user moves:**
  - 14... Ba6 (Good, pre-move ES 0.50), reply 15. Qg4
  - 15... e5 (Good, pre-move ES 0.50), reply 16. O-O-O
- **FEN before the answer move:** `r4rk1/p4ppp/b1p5/2q1p3/6Q1/2B5/PPP2PPP/2KR3R b - - 1 16`
- **Answer:** blunder 16... f6 (pre-move ES 0.49, ES after 0.19).
- **Refutation:** Bb4.
- **Score inputs:** facepalm score 0.958, played prob 0.201, reply spread 3.33, line loss 3 4, mate ply n/a.

#### Window 20: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=641901&ply=1
- **User rating:** 2687 (pinned Maia Elo 2600)
- **FEN before the lead-in:** `rnbqkbnr/pppppppp/8/8/8/1P6/P1PPPPPP/RNBQKBNR b KQkq - 0 1`
- **Lead-in:** 1... Nf6
- **Judged user moves:**
  - 2. Bb2 (Good, pre-move ES 0.51), reply 2... e6
  - 3. Nf3 (Good, pre-move ES 0.52), reply 3... Be7
  - 4. g3 (Good, pre-move ES 0.52), reply 4... O-O
  - 5. Bg2 (Good, pre-move ES 0.51), reply 5... b6
  - 6. O-O (Good, pre-move ES 0.52), reply 6... Bb7
- **Answer:** all safe (every judged move is Good).
