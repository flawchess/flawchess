# Blunder-check spot-check

Windows drawn the way the feature would draw them: length L uniform over 3 to 5 user moves, per-move blunder hazard 0.265, so roughly 30% are herrings (all judged moves safe). About 20 windows per Elo bucket, at most one per game, drawn with a fixed seed.

Thresholds: refutation R = 0.3, best-move X' = 0.2, eval band [0.10, 0.90] on the pre-move ES. A recommendation only; nothing here is wired into app code.

How to read: for each window, play through the lead-in and the judged moves on the board (the game link opens the full game), decide whether the position is a fair question, then compare with the answer. A blunder window is fair when the refutation or the missed move is something a player of that rating could find. Moves are in SAN; a stored move that is not legal on the replayed board prints as its UCI with the word illegal.

### <800

#### Window 1: allowed (length 5, blunder at 4)

- **Game:** https://www.chess.com/game/live/185809311430
- **User rating:** 287 (pinned Maia Elo 600)
- **FEN before the lead-in:** `r1bqkb1r/ppp2ppp/2np1n2/4p3/4P3/5NP1/PPPPQP1P/RNB1KB1R w KQkq - 0 5`
- **Lead-in:** 5. d3 Be6 6. Bg5
- **Judged user moves:**
  - 6... Be7 (Good, pre-move ES 0.56), reply 7. Nh4
  - 7... h6 (Good, pre-move ES 0.62), reply 8. Be3
  - 8... g5 (Good, pre-move ES 0.64), reply 9. Nf5
- **FEN before the answer move:** `r2qk2r/ppp1bp2/2npbn1p/4pNp1/4P3/3PB1P1/PPP1QP1P/RN2KB1R b KQkq - 1 9`
- **Answer:** blunder 9... d5 (pre-move ES 0.61, ES after 0.45).
- **Refutation:** Ng7+ (Maia probability 0.260, rank 1).

#### Window 2: allowed (length 5, blunder at 3)

- **Game:** https://www.chess.com/game/daily/104734235
- **User rating:** 683 (pinned Maia Elo 683)
- **FEN before the lead-in:** `r2qk2r/ppp2ppp/2np1n2/2b5/2B3bP/4PQ2/PPP2PP1/RNB1K1NR w KQkq - 4 8`
- **Lead-in:** 8. Qf4 Qe7 9. Bd2
- **Judged user moves:**
  - 9... O-O-O (Good, pre-move ES 0.60), reply 10. Nc3
  - 10... d5 (Good, pre-move ES 0.67), reply 11. Nxd5
- **FEN before the answer move:** `2kr3r/ppp1qppp/2n2n2/2bN4/2B2QbP/4P3/PPPB1PP1/R3K1NR b KQ - 0 11`
- **Answer:** blunder 11... Nxd5 (pre-move ES 0.68, ES after 0.42).
- **Refutation:** Qxg4+ (Maia probability 0.604, rank 1).

#### Window 3: mixed (length 5, blunder at 1)

- **Game:** https://www.chess.com/game/live/73652575441
- **User rating:** 721 (pinned Maia Elo 721)
- **FEN before the lead-in:** `r1b1k2r/pppp1ppp/1bn2q2/4p3/1P4n1/P4PPN/1BPPP1BP/RN1QK2R b KQkq - 0 8`
- **Lead-in:** 8... Nh6 9. Nc3 e4
- **Judged user moves:**
- **FEN before the answer move:** `r1b1k2r/pppp1ppp/1bn2q1n/8/1P2p3/P1N2PPN/1BPPP1BP/R2QK2R w KQkq - 0 10`
- **Answer:** blunder 10. Nxe4 (pre-move ES 0.69, ES after 0.29).
- **Refutation:** Qxb2 (Maia probability 0.476, rank 1).
- **Missed best move:** fxe4 (Maia probability 0.378, rank 1).

#### Window 4: allowed (length 5, blunder at 2)

- **Game:** https://www.chess.com/game/live/165455386860
- **User rating:** 568 (pinned Maia Elo 600)
- **FEN before the lead-in:** `rn1qkbnr/ppp2ppp/4b3/3pQ3/4P3/5N2/PPPP1PPP/RNB1KB1R b KQkq - 2 4`
- **Lead-in:** 4... f6 5. Qd4 c5
- **Judged user moves:**
  - 6. Qa4+ (Good, pre-move ES 0.61), reply 6... Bd7
- **FEN before the answer move:** `rn1qkbnr/pp1b2pp/5p2/2pp4/Q3P3/5N2/PPPP1PPP/RNB1KB1R w KQkq - 2 7`
- **Answer:** blunder 7. Qb3 (pre-move ES 0.63, ES after 0.41).
- **Refutation:** dxe4 (Maia probability 0.290, rank 1).

#### Window 5: mixed (length 5, blunder at 2)

- **Game:** https://www.chess.com/game/live/82136047456
- **User rating:** 334 (pinned Maia Elo 600)
- **FEN before the lead-in:** `rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1`
- **Lead-in:** 1... e5 2. Qh5 Nf6
- **Judged user moves:**
  - 3. Qxe5+ (Good, pre-move ES 0.47), reply 3... Qe7
- **FEN before the answer move:** `rnb1kb1r/ppppqppp/5n2/4Q3/4P3/8/PPPP1PPP/RNB1KBNR w KQkq - 1 4`
- **Answer:** blunder 4. Qd5 (pre-move ES 0.63, ES after 0.09).
- **Refutation:** Nxd5 (Maia probability 0.816, rank 1).
- **Missed best move:** Qxe7+ (Maia probability 0.266, rank 2).

#### Window 6: allowed (length 3, blunder at 1)

- **Game:** https://www.chess.com/game/live/141441374434
- **User rating:** 374 (pinned Maia Elo 600)
- **FEN before the lead-in:** `r1b3k1/ppp1np2/7p/4P1pn/2B5/2N2N1P/PPP3P1/3R2K1 w - - 0 17`
- **Lead-in:** 17. g4 Nf4 18. Kh2
- **Judged user moves:**
- **FEN before the answer move:** `r1b3k1/ppp1np2/7p/4P1p1/2B2nP1/2N2N1P/PPP4K/3R4 b - - 2 18`
- **Answer:** blunder 18... Neg6 (pre-move ES 0.48, ES after 0.31).
- **Refutation:** Rd8+ (Maia probability 0.604, rank 1).

#### Window 7: allowed (length 4, blunder at 2)

- **Game:** https://www.chess.com/game/live/164449671336
- **User rating:** 514 (pinned Maia Elo 600)
- **FEN before the lead-in:** `1r3rk1/pp2bppp/4p3/3nq3/1P6/P2BPQ2/3N1PPP/R4RK1 w - - 0 16`
- **Lead-in:** 16. Nc4 Qc3 17. Rfd1
- **Judged user moves:**
  - 17... Rfd8 (Good, pre-move ES 0.52), reply 18. g3
- **FEN before the answer move:** `1r1r2k1/pp2bppp/4p3/3n4/1PN5/P1qBPQP1/5P1P/R2R2K1 b - - 0 18`
- **Answer:** blunder 18... Nf6 (pre-move ES 0.54, ES after 0.38).
- **Refutation:** Rac1 (Maia probability 0.317, rank 1).

#### Window 8: herring (length 5, no blunder)

- **Game:** https://www.chess.com/game/live/136120532522
- **User rating:** 639 (pinned Maia Elo 639)
- **FEN before the lead-in:** `1r3rk1/1Np2ppp/p1B5/1p4P1/4PbPq/5Q2/PP3P2/R4RK1 w - - 0 22`
- **Lead-in:** 22. Qxf4 f6 23. Qh2
- **Judged user moves:**
  - 23... Qxg5 (Good, pre-move ES 0.13), reply 24. Rae1
  - 24... Qxg4+ (Good, pre-move ES 0.11), reply 25. Kh1
  - 25... Qf3+ (Good, pre-move ES 0.13), reply 26. Kg1
  - 26... Qg4+ (Good, pre-move ES 0.12), reply 27. Qg3
  - 27... Qxg3+ (Good, pre-move ES 0.12), reply 28. fxg3
- **Answer:** all safe (every judged move is Good).

#### Window 9: allowed (length 5, blunder at 4)

- **Game:** https://www.chess.com/game/live/184923975262
- **User rating:** 593 (pinned Maia Elo 600)
- **FEN before the lead-in:** `8/R6p/B4k2/8/b3p3/r7/3K3P/8 b - - 0 32`
- **Lead-in:** 32... e3+ 33. Ke2 Bb5+
- **Judged user moves:**
  - 34. Bxb5 (Good, pre-move ES 0.18), reply 34... Rxa7
  - 35. Kxe3 (Good, pre-move ES 0.20), reply 35... Re7+
  - 36. Kf4 (Good, pre-move ES 0.25), reply 36... Re5
- **FEN before the answer move:** `8/7p/5k2/1B2r3/5K2/8/7P/8 w - - 3 37`
- **Answer:** blunder 37. h4 (pre-move ES 0.23, ES after 0.01).
- **Refutation:** Rxb5 (Maia probability 0.644, rank 1).

#### Window 10: allowed (length 5, blunder at 4)

- **Game:** https://www.chess.com/game/live/185451253812
- **User rating:** 202 (pinned Maia Elo 600)
- **FEN before the lead-in:** `rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1`
- **Lead-in:** 1. Nf3 d5 2. d4
- **Judged user moves:**
  - 2... Nc6 (Good, pre-move ES 0.47), reply 3. e3
  - 3... Bg4 (Good, pre-move ES 0.45), reply 4. Nc3
  - 4... e5 (Good, pre-move ES 0.50), reply 5. dxe5
- **FEN before the answer move:** `r2qkbnr/ppp2ppp/2n5/3pP3/6b1/2N1PN2/PPP2PPP/R1BQKB1R b KQkq - 0 5`
- **Answer:** blunder 5... d4 (pre-move ES 0.50, ES after 0.27).
- **Refutation:** exd4 (Maia probability 0.852, rank 1).

#### Window 11: allowed (length 5, blunder at 4)

- **Game:** https://www.chess.com/game/live/167670799472
- **User rating:** 603 (pinned Maia Elo 603)
- **FEN before the lead-in:** `2k2b1r/ppp1pppp/4b3/8/5B2/P1P3P1/2P2PBP/5K1R b - - 0 16`
- **Lead-in:** 16... Bc4+ 17. Ke1 g5
- **Judged user moves:**
  - 18. Bxg5 (Good, pre-move ES 0.42), reply 18... h6
  - 19. Bh3+ (Good, pre-move ES 0.45), reply 19... Kb8
  - 20. Bd2 (Good, pre-move ES 0.45), reply 20... e6
- **FEN before the answer move:** `1k3b1r/ppp2p2/4p2p/8/2b5/P1P3PB/2PB1P1P/4K2R w - - 0 21`
- **Answer:** blunder 21. Kd1 (pre-move ES 0.44, ES after 0.29).
- **Refutation:** Bxa3 (Maia probability 0.582, rank 1).

#### Window 12: allowed (length 5, blunder at 4)

- **Game:** https://www.chess.com/game/live/54514165547
- **User rating:** 442 (pinned Maia Elo 600)
- **FEN before the lead-in:** `rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1`
- **Lead-in:** 1. d4
- **Judged user moves:**
  - 1... d5 (Good, pre-move ES 0.47), reply 2. Nc3
  - 2... Nc6 (Good, pre-move ES 0.51), reply 3. e3
  - 3... Bf5 (Good, pre-move ES 0.50), reply 4. Bd3
- **FEN before the answer move:** `r2qkbnr/ppp1pppp/2n5/3p1b2/3P4/2NBP3/PPP2PPP/R1BQK1NR b KQkq - 2 4`
- **Answer:** blunder 4... e5 (pre-move ES 0.50, ES after 0.18).
- **Refutation:** Bxf5 (Maia probability 0.495, rank 1).

#### Window 13: herring (length 3, no blunder)

- **Game:** https://www.chess.com/game/live/122789436108
- **User rating:** 376 (pinned Maia Elo 600)
- **FEN before the lead-in:** `r4b1r/ppp1pppp/4k3/4N3/4n3/8/PPP3PP/R1B1K2R w KQ - 2 12`
- **Lead-in:** 12. Bf4 f6 13. Nc4
- **Judged user moves:**
  - 13... Kf5 (Good, pre-move ES 0.79), reply 14. Rd1
  - 14... Kxf4 (Good, pre-move ES 0.81), reply 15. Rd7
  - 15... Nd6 (Good, pre-move ES 0.83), reply 16. Rxc7
- **Answer:** all safe (every judged move is Good).

#### Window 14: pure_miss (length 4, blunder at 2)

- **Game:** https://www.chess.com/game/live/99278060621
- **User rating:** 712 (pinned Maia Elo 712)
- **FEN before the lead-in:** `r1bqk1nr/p5pp/2p2p2/4p1P1/1b1pP3/6Q1/PPP2P1P/RNB1K1NR w KQkq - 2 10`
- **Lead-in:** 10. c3 dxc3 11. bxc3
- **Judged user moves:**
  - 11... Ba5 (Good, pre-move ES 0.62), reply 12. gxf6
- **FEN before the answer move:** `r1bqk1nr/p5pp/2p2P2/b3p3/4P3/2P3Q1/P4P1P/RNB1K1NR b KQkq - 0 12`
- **Answer:** blunder 12... Qxf6 (pre-move ES 0.73, ES after 0.54).
- **Missed best move:** Nxf6 (Maia probability 0.331, rank 2).

#### Window 15: allowed (length 3, blunder at 2)

- **Game:** https://www.chess.com/game/live/108369792294
- **User rating:** 540 (pinned Maia Elo 600)
- **FEN before the lead-in:** `r1bqk2r/ppp2ppp/2n5/2bnp3/8/2PP1NP1/PP3PBP/RNBQK2R w KQkq - 1 8`
- **Lead-in:** 8. O-O O-O 9. h3
- **Judged user moves:**
  - 9... Bf5 (Good, pre-move ES 0.50), reply 10. Nh4
- **FEN before the answer move:** `r2q1rk1/ppp2ppp/2n5/2bnpb2/7N/2PP2PP/PP3PB1/RNBQ1RK1 b - - 2 10`
- **Answer:** blunder 10... Qd7 (pre-move ES 0.54, ES after 0.22).
- **Refutation:** Nxf5 (Maia probability 0.682, rank 1).

#### Window 16: allowed (length 4, blunder at 3)

- **Game:** https://www.chess.com/game/live/139820044504
- **User rating:** 258 (pinned Maia Elo 600)
- **FEN before the lead-in:** `rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1`
- **Lead-in:** 1. b3
- **Judged user moves:**
  - 1... e5 (Good, pre-move ES 0.52), reply 2. Bb2
  - 2... Nc6 (Good, pre-move ES 0.51), reply 3. d4
- **FEN before the answer move:** `r1bqkbnr/pppp1ppp/2n5/4p3/3P4/1P6/PBP1PPPP/RN1QKBNR b KQkq - 0 3`
- **Answer:** blunder 3... Qe7 (pre-move ES 0.58, ES after 0.42).
- **Refutation:** dxe5 (Maia probability 0.295, rank 1).

#### Window 17: pure_miss (length 4, blunder at 2)

- **Game:** https://www.chess.com/game/live/174436063170
- **User rating:** 347 (pinned Maia Elo 600)
- **FEN before the lead-in:** `rnb1k2r/pp3p1p/2p5/2bB4/6P1/5N2/PPP4P/RNB1K2R w KQkq - 0 13`
- **Lead-in:** 13. Bc4 Be6 14. Ng5
- **Judged user moves:**
  - 14... Bxc4 (Good, pre-move ES 0.50), reply 15. b3
- **FEN before the answer move:** `rn2k2r/pp3p1p/2p5/2b3N1/2b3P1/1P6/P1P4P/RNB1K2R b KQkq - 0 15`
- **Answer:** blunder 15... Bb4+ (pre-move ES 0.65, ES after 0.47).
- **Missed best move:** Bd5 (Maia probability 0.400, rank 1).

#### Window 18: herring (length 4, no blunder)

- **Game:** https://www.chess.com/game/live/160370849523
- **User rating:** 496 (pinned Maia Elo 600)
- **FEN before the lead-in:** `rnbqk1nr/pppp1ppp/8/2b1N3/4P3/8/PPPP1PPP/RNBQKB1R b KQkq - 0 3`
- **Lead-in:** 3... Qh4 4. Qf3 f6
- **Judged user moves:**
  - 5. g3 (Good, pre-move ES 0.68), reply 5... Qg5
  - 6. Nd3 (Good, pre-move ES 0.69), reply 6... b6
  - 7. Bg2 (Good, pre-move ES 0.74), reply 7... Qg6
  - 8. O-O (Good, pre-move ES 0.75), reply 8... Ne7
- **Answer:** all safe (every judged move is Good).

#### Window 19: pure_miss (length 5, blunder at 2)

- **Game:** https://www.chess.com/game/live/108720205698
- **User rating:** 592 (pinned Maia Elo 600)
- **FEN before the lead-in:** `6k1/ppp4p/4b1p1/4B3/2P5/6P1/P6P/5K2 b - - 0 28`
- **Lead-in:** 28... Bxc4+ 29. Kg2 Bxa2
- **Judged user moves:**
  - 30. Bxc7 (Good, pre-move ES 0.21), reply 30... Bd5+
- **FEN before the answer move:** `6k1/ppB4p/6p1/3b4/8/6P1/6KP/8 w - - 1 31`
- **Answer:** blunder 31. Kh3 (pre-move ES 0.45, ES after 0.20).
- **Missed best move:** Kf2 (Maia probability 0.319, rank 2).

#### Window 20: allowed (length 5, blunder at 4)

- **Game:** https://www.chess.com/game/live/6079149399
- **User rating:** 549 (pinned Maia Elo 600)
- **FEN before the lead-in:** `r5k1/pp3ppn/2nNq3/3p3b/3P4/2P1rP1N/PP4PP/R2QR1K1 w - - 1 16`
- **Lead-in:** 16. Nf5 Rxe1+ 17. Qxe1
- **Judged user moves:**
  - 17... Qxf5 (Good, pre-move ES 0.87), reply 18. Qe2
  - 18... Qc8 (Good, pre-move ES 0.87), reply 19. Re1
  - 19... Qd8 (Good, pre-move ES 0.86), reply 20. b4
- **FEN before the answer move:** `r2q2k1/pp3ppn/2n5/3p3b/1P1P4/2P2P1N/P3Q1PP/4R1K1 b - - 0 20`
- **Answer:** blunder 20... Ne7 (pre-move ES 0.86, ES after 0.65).
- **Refutation:** Qxe7 (Maia probability 0.368, rank 1).

### 800-1199

#### Window 1: allowed (length 4, blunder at 1)

- **Game:** https://www.chess.com/game/live/42847783851
- **User rating:** 638 (pinned Maia Elo 1102)
- **FEN before the lead-in:** `4rrk1/7p/p2b2pQ/3P4/2p5/4P3/P3K1R1/1q4R1 w - - 0 33`
- **Lead-in:** 33. Rxg6+ hxg6 34. Qxg6+
- **Judged user moves:**
- **FEN before the answer move:** `4rrk1/8/p2b2Q1/3P4/2p5/4P3/P3K3/1q4R1 b - - 0 34`
- **Answer:** blunder 34... Kh8 (pre-move ES 0.14, ES after 0.02).
- **Refutation:** Qg7# (Maia probability 0.537, rank 1).

#### Window 2: allowed (length 5, blunder at 1)

- **Game:** https://lichess.org/s87xe3Zq
- **User rating:** 1005 (pinned Maia Elo 1005)
- **FEN before the lead-in:** `rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1`
- **Lead-in:** 1. e4 e5 2. Bc4
- **Judged user moves:**
- **FEN before the answer move:** `rnbqkbnr/pppp1ppp/8/4p3/2B1P3/8/PPPP1PPP/RNBQK1NR b KQkq - 1 2`
- **Answer:** blunder 2... Qg5 (pre-move ES 0.50, ES after 0.34).
- **Refutation:** Nf3 (Maia probability 0.243, rank 1).

#### Window 3: allowed (length 3, blunder at 2)

- **Game:** https://lichess.org/OBOBYgIF
- **User rating:** 1389 (pinned Maia Elo 1190)
- **FEN before the lead-in:** `3r2k1/pp3pp1/2n5/q1p1n2B/2P1P3/P2r4/1P2QPPP/R2R2K1 w - - 4 20`
- **Lead-in:** 20. Rab1 Nd4 21. Qe1
- **Judged user moves:**
  - 21... Rxd1 (Good, pre-move ES 0.86), reply 22. Rxd1
- **FEN before the answer move:** `3r2k1/pp3pp1/8/q1p1n2B/2PnP3/P7/1P3PPP/3RQ1K1 b - - 0 22`
- **Answer:** blunder 22... Ndf3+ (pre-move ES 0.87, ES after 0.46).
- **Refutation:** Bxf3 (Maia probability 0.384, rank 2).

#### Window 4: allowed (length 3, blunder at 2)

- **Game:** https://www.chess.com/game/live/166715507104
- **User rating:** 740 (pinned Maia Elo 1167)
- **FEN before the lead-in:** `r2q1rk1/2pp1ppp/3b2n1/1p2p3/1P1Pb3/N1P5/1B2BPPP/R2Q1RK1 w - - 0 17`
- **Lead-in:** 17. f3 Bf5 18. Nxb5
- **Judged user moves:**
  - 18... Rxa1 (Good, pre-move ES 0.57), reply 19. Bxa1
- **FEN before the answer move:** `3q1rk1/2pp1ppp/3b2n1/1N2pb2/1P1P4/2P2P2/4B1PP/B2Q1RK1 b - - 0 19`
- **Answer:** blunder 19... exd4 (pre-move ES 0.57, ES after 0.37).
- **Refutation:** Nxd6 (Maia probability 0.411, rank 1).

#### Window 5: herring (length 5, no blunder)

- **Game:** https://www.chess.com/game/live/119762359336
- **User rating:** 599 (pinned Maia Elo 1075)
- **FEN before the lead-in:** `r5k1/1R4p1/Pb5p/4p3/8/7K/8/R7 b - - 3 35`
- **Lead-in:** 35... Bd4 36. Re7 Bxa1
- **Judged user moves:**
  - 37. a7 (Good, pre-move ES 0.13), reply 37... e4
  - 38. Rxe4 (Good, pre-move ES 0.13), reply 38... Rxa7
  - 39. Re8+ (Good, pre-move ES 0.13), reply 39... Kh7
  - 40. Kh4 (Good, pre-move ES 0.10), reply 40... g5+
  - 41. Kh5 (Good, pre-move ES 0.13), reply 41... Ra5
- **Answer:** all safe (every judged move is Good).

#### Window 6: allowed (length 5, blunder at 1)

- **Game:** https://lichess.org/YbkW4Phe
- **User rating:** 1056 (pinned Maia Elo 1056)
- **FEN before the lead-in:** `5r1k/6pp/1p6/p3n3/P3Q3/4P1K1/1P4PP/R1B1q3 w - - 5 31`
- **Lead-in:** 31. Kh3 Ng6 32. b4
- **Judged user moves:**
- **FEN before the answer move:** `5r1k/6pp/1p4n1/p7/PP2Q3/4P2K/6PP/R1B1q3 b - - 0 32`
- **Answer:** blunder 32... axb4 (pre-move ES 0.88, ES after 0.51).
- **Refutation:** Bb2 (Maia probability 0.600, rank 1).

#### Window 7: allowed (length 4, blunder at 1)

- **Game:** https://www.chess.com/game/live/138070935196
- **User rating:** 762 (pinned Maia Elo 1042)
- **FEN before the lead-in:** `1k1r1b1r/1p4p1/7p/1n3p2/1P5Q/B2q1P2/P5PP/2R1R1K1 w - - 0 26`
- **Lead-in:** 26. Qf4+ Rd6 27. Bb2
- **Judged user moves:**
- **FEN before the answer move:** `1k3b1r/1p4p1/3r3p/1n3p2/1P3Q2/3q1P2/PB4PP/2R1R1K1 b - - 3 27`
- **Answer:** blunder 27... g5 (pre-move ES 0.53, ES after 0.32).
- **Refutation:** Qe5 (Maia probability 0.296, rank 1).

#### Window 8: herring (length 3, no blunder)

- **Game:** https://www.chess.com/game/live/20176799295
- **User rating:** 698 (pinned Maia Elo 1144)
- **FEN before the lead-in:** `2r1kb1r/pppb1ppp/2np2q1/3BP3/3P4/5N2/PPP2PPP/R1BQ1RK1 w k - 1 12`
- **Lead-in:** 12. Ng5 Be6 13. Bxc6+
- **Judged user moves:**
  - 13... bxc6 (Good, pre-move ES 0.27), reply 14. Re1
  - 14... h6 (Good, pre-move ES 0.31), reply 15. Nxe6
  - 15... fxe6 (Good, pre-move ES 0.28), reply 16. exd6
- **Answer:** all safe (every judged move is Good).

#### Window 9: herring (length 4, no blunder)

- **Game:** https://www.chess.com/game/live/171540696088
- **User rating:** 447 (pinned Maia Elo 1031)
- **FEN before the lead-in:** `rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1`
- **Lead-in:** 1. e4 e5
- **Judged user moves:**
  - 2. Nf3 (Good, pre-move ES 0.53), reply 2... d6
  - 3. Bc4 (Good, pre-move ES 0.56), reply 3... Na6
  - 4. c3 (Good, pre-move ES 0.61), reply 4... Nc5
  - 5. d4 (Good, pre-move ES 0.60), reply 5... exd4
- **Answer:** all safe (every judged move is Good).

#### Window 10: herring (length 3, no blunder)

- **Game:** https://www.chess.com/game/live/169053762538
- **User rating:** 767 (pinned Maia Elo 1044)
- **FEN before the lead-in:** `4k3/1pr1n1b1/pN3p2/B1P2bp1/2P1p3/6R1/P4PPP/R5K1 w - - 2 28`
- **Lead-in:** 28. Nd5 Rxc5 29. Nxe7
- **Judged user moves:**
  - 29... Rxa5 (Good, pre-move ES 0.19), reply 30. Nxf5
  - 30... Rxf5 (Good, pre-move ES 0.17), reply 31. h4
  - 31... Bh6 (Good, pre-move ES 0.23), reply 32. hxg5
- **Answer:** all safe (every judged move is Good).

#### Window 11: pure_miss (length 4, blunder at 1)

- **Game:** https://www.chess.com/game/live/120019919396
- **User rating:** 918 (pinned Maia Elo 1128)
- **FEN before the lead-in:** `rnbqk2r/ppp2ppp/8/2bnN3/2B5/7P/PPPP1PP1/RNBQK2R b KQkq - 0 6`
- **Lead-in:** 6... Qe7 7. Qe2 Bxf2+
- **Judged user moves:**
- **FEN before the answer move:** `rnb1k2r/ppp1qppp/8/3nN3/2B5/7P/PPPPQbP1/RNB1K2R w KQkq - 0 8`
- **Answer:** blunder 8. Qxf2 (pre-move ES 0.83, ES after 0.53).
- **Missed best move:** Kxf2 (Maia probability 0.803, rank 1).

#### Window 12: herring (length 3, no blunder)

- **Game:** https://www.chess.com/game/live/162382627121
- **User rating:** 657 (pinned Maia Elo 1115)
- **FEN before the lead-in:** `r1bq1rk1/5pp1/p3pB1p/3p4/6Q1/PPNBP3/2P2PPP/R4RK1 b - - 0 21`
- **Lead-in:** 21... Qxf6 22. e4 Qxc3
- **Judged user moves:**
  - 23. exd5 (Good, pre-move ES 0.70), reply 23... exd5
  - 24. Qg3 (Good, pre-move ES 0.70), reply 24... a5
  - 25. Bh7+ (Good, pre-move ES 0.89), reply 25... Kh8
- **Answer:** all safe (every judged move is Good).

#### Window 13: herring (length 4, no blunder)

- **Game:** https://www.chess.com/game/live/166273566174
- **User rating:** 939 (pinned Maia Elo 1142)
- **FEN before the lead-in:** `rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1`
- **Lead-in:** 1. e4
- **Judged user moves:**
  - 1... e5 (Good, pre-move ES 0.47), reply 2. Nc3
  - 2... Bc5 (Good, pre-move ES 0.49), reply 3. f4
  - 3... d6 (Good, pre-move ES 0.50), reply 4. Nf3
  - 4... Nc6 (Good, pre-move ES 0.52), reply 5. Bb5
- **Answer:** all safe (every judged move is Good).

#### Window 14: allowed (length 5, blunder at 3)

- **Game:** https://www.chess.com/game/live/184515966174
- **User rating:** 598 (pinned Maia Elo 1074)
- **FEN before the lead-in:** `4r1qk/1bp1Q1pp/2p5/p2p4/3p4/4P1N1/PPPB2PP/5RK1 w - - 1 20`
- **Lead-in:** 20. Qxc7 dxe3 21. Bxe3
- **Judged user moves:**
  - 21... Rxe3 (Good, pre-move ES 0.15), reply 22. Qxb7
  - 22... Re6 (Good, pre-move ES 0.15), reply 23. Nf5
- **FEN before the answer move:** `6qk/1Q4pp/2p1r3/p2p1N2/8/8/PPP3PP/5RK1 b - - 2 23`
- **Answer:** blunder 23... Qf7 (pre-move ES 0.16, ES after 0.02).
- **Refutation:** Qxf7 (Maia probability 0.782, rank 1).

#### Window 15: allowed (length 4, blunder at 1)

- **Game:** https://www.chess.com/game/live/94340035215
- **User rating:** 706 (pinned Maia Elo 1148)
- **FEN before the lead-in:** `r2q1k1r/1b1p1npp/p4b2/1pB5/8/P1NB4/1P3PPP/R2QR1K1 b - - 3 18`
- **Lead-in:** 18... d6 19. Bb4 a5
- **Judged user moves:**
- **FEN before the answer move:** `r2q1k1r/1b3npp/3p1b2/pp6/1B6/P1NB4/1P3PPP/R2QR1K1 w - - 0 20`
- **Answer:** blunder 20. Nxb5 (pre-move ES 0.50, ES after 0.35).
- **Refutation:** axb4 (Maia probability 0.794, rank 1).

#### Window 16: allowed (length 5, blunder at 2)

- **Game:** https://www.chess.com/game/live/100654999161
- **User rating:** 554 (pinned Maia Elo 1054)
- **FEN before the lead-in:** `r2qk1nr/pppb2pp/2n1p3/1B1pPp2/3P4/5N2/PPPQ1PPP/RN3RK1 b kq - 2 8`
- **Lead-in:** 8... Nge7 9. Nc3 Nb4
- **Judged user moves:**
  - 10. a3 (Good, pre-move ES 0.64), reply 10... Bxb5
- **FEN before the answer move:** `r2qk2r/ppp1n1pp/4p3/1b1pPp2/1n1P4/P1N2N2/1PPQ1PPP/R4RK1 w kq - 0 11`
- **Answer:** blunder 11. axb4 (pre-move ES 0.60, ES after 0.36).
- **Refutation:** Bxf1 (Maia probability 0.802, rank 1).

#### Window 17: allowed (length 5, blunder at 3)

- **Game:** https://www.chess.com/game/live/120964816794
- **User rating:** 696 (pinned Maia Elo 1142)
- **FEN before the lead-in:** `4rrk1/ppp3pp/3q2b1/n2p1p2/3P1P2/2PBP3/PP2Q2P/2KR2NR w - - 5 16`
- **Lead-in:** 16. b4 Nc4 17. Bxc4
- **Judged user moves:**
  - 17... dxc4 (Good, pre-move ES 0.61), reply 18. Qxc4+
  - 18... Bf7 (Good, pre-move ES 0.74), reply 19. Qd3
- **FEN before the answer move:** `4rrk1/ppp2bpp/3q4/5p2/1P1P1P2/2PQP3/P6P/2KR2NR b - - 2 19`
- **Answer:** blunder 19... g6 (pre-move ES 0.76, ES after 0.59).
- **Refutation:** Nf3 (Maia probability 0.463, rank 1).

#### Window 18: pure_miss (length 5, blunder at 1)

- **Game:** https://www.chess.com/game/live/148018678326
- **User rating:** 854 (pinned Maia Elo 1087)
- **FEN before the lead-in:** `rn1qk1nr/pbpp1pbp/1p2p1p1/8/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1 b kq - 2 6`
- **Lead-in:** 6... Nf6 7. Bg5 O-O
- **Judged user moves:**
- **FEN before the answer move:** `rn1q1rk1/pbpp1pbp/1p2pnp1/6B1/2B1P3/2NP1N2/PPP2PPP/R2Q1RK1 w - - 5 8`
- **Answer:** blunder 8. Qd2 (pre-move ES 0.77, ES after 0.50).
- **Missed best move:** e5 (Maia probability 0.388, rank 1).

#### Window 19: allowed (length 3, blunder at 1)

- **Game:** https://www.chess.com/game/live/13354437639
- **User rating:** 616 (pinned Maia Elo 1086)
- **FEN before the lead-in:** `2k5/r4p1p/5Kp1/1p6/p1pR2P1/2P5/PP5P/8 w - - 0 32`
- **Lead-in:** 32. b4 cxb3 33. axb3
- **Judged user moves:**
- **FEN before the answer move:** `2k5/r4p1p/5Kp1/1p6/p2R2P1/1PP5/7P/8 b - - 0 33`
- **Answer:** blunder 33... axb3 (pre-move ES 0.81, ES after 0.54).
- **Refutation:** Rb4 (Maia probability 0.865, rank 1).

#### Window 20: allowed (length 4, blunder at 3)

- **Game:** https://www.chess.com/game/live/2148779715
- **User rating:** 916 (pinned Maia Elo 1127)
- **FEN before the lead-in:** `r5k1/2p2pp1/p1n1rq1p/1p2p2Q/3pR2N/1P1P3P/P1P2PP1/R5K1 w - - 0 20`
- **Lead-in:** 20. f4 exf4 21. Rxe6
- **Judged user moves:**
  - 21... Qxe6 (Good, pre-move ES 0.71), reply 22. Rf1
  - 22... g5 (Good, pre-move ES 0.69), reply 23. Nf3
- **FEN before the answer move:** `r5k1/2p2p2/p1n1q2p/1p4pQ/3p1p2/1P1P1N1P/P1P3P1/5RK1 b - - 1 23`
- **Answer:** blunder 23... Re8 (pre-move ES 0.72, ES after 0.48).
- **Refutation:** Re1 (Maia probability 0.472, rank 1).

### 1200-1599

#### Window 1: herring (length 4, no blunder)

- **Game:** https://lichess.org/Kjb1NiHA
- **User rating:** 1566 (pinned Maia Elo 1566)
- **FEN before the lead-in:** `7k/1q3pp1/pb2pn1p/1p2N3/1P1P1Q2/P5PP/5P2/2B3K1 b - - 0 35`
- **Lead-in:** 35... Bxd4 36. Qxd4 Qd5
- **Judged user moves:**
  - 37. Qxd5 (Good, pre-move ES 0.86), reply 37... Nxd5
  - 38. Nd7 (Good, pre-move ES 0.87), reply 38... Kg8
  - 39. Be3 (Good, pre-move ES 0.84), reply 39... f6
  - 40. Nc5 (Good, pre-move ES 0.83), reply 40... Nc7
- **Answer:** all safe (every judged move is Good).

#### Window 2: allowed (length 5, blunder at 1)

- **Game:** https://www.chess.com/game/live/147341735780
- **User rating:** 1101 (pinned Maia Elo 1293)
- **FEN before the lead-in:** `2kr1bnr/pp1npppp/2p5/8/4PBb1/5N2/PPP1BPPP/RN1K3R w - - 5 8`
- **Lead-in:** 8. Nbd2 Ngf6 9. c3
- **Judged user moves:**
- **FEN before the answer move:** `2kr1b1r/pp1npppp/2p2n2/8/4PBb1/2P2N2/PP1NBPPP/R2K3R b - - 0 9`
- **Answer:** blunder 9... Nxe4 (pre-move ES 0.51, ES after 0.26).
- **Refutation:** Nxe4 (Maia probability 0.793, rank 1).

#### Window 3: allowed (length 3, blunder at 2)

- **Game:** https://www.chess.com/game/daily/653089841
- **User rating:** 1304 (pinned Maia Elo 1304)
- **FEN before the lead-in:** `r2q1rk1/pp2b2p/2n1p2p/2ppNp2/3P4/2P5/PP3PPP/RN1QR1K1 w - - 0 13`
- **Lead-in:** 13. Qh5 cxd4 14. Qxh6
- **Judged user moves:**
  - 14... Rf6 (Good, pre-move ES 0.64), reply 15. Qf4
- **FEN before the answer move:** `r2q2k1/pp2b2p/2n1pr2/3pNp2/3p1Q2/2P5/PP3PPP/RN2R1K1 b - - 2 15`
- **Answer:** blunder 15... Bf8 (pre-move ES 0.68, ES after 0.53).
- **Refutation:** cxd4 (Maia probability 0.696, rank 1).

#### Window 4: allowed (length 3, blunder at 1)

- **Game:** https://www.chess.com/game/live/171053976266
- **User rating:** 1228 (pinned Maia Elo 1418)
- **FEN before the lead-in:** `1r4k1/8/2q3p1/Qppb1pNp/8/PP6/5PPP/4R1K1 b - - 0 38`
- **Lead-in:** 38... Bxg2 39. Qa7 Qb7
- **Judged user moves:**
- **FEN before the answer move:** `1r4k1/Qq6/6p1/1pp2pNp/8/PP6/5PbP/4R1K1 w - - 2 40`
- **Answer:** blunder 40. Re8+ (pre-move ES 0.73, ES after 0.06).
- **Refutation:** Rxe8 (Maia probability 0.813, rank 1).

#### Window 5: pure_miss (length 4, blunder at 2)

- **Game:** https://lichess.org/0NZ2RwKI
- **User rating:** 1484 (pinned Maia Elo 1484)
- **FEN before the lead-in:** `r4rk1/4qppp/p1np4/1p1p1p2/1P1Pn3/P3PN1P/2PN1PP1/2RQR1K1 b - - 0 14`
- **Lead-in:** 14... a5 15. bxa5 Rxa5
- **Judged user moves:**
  - 16. Ra1 (Good, pre-move ES 0.44), reply 16... b4
- **FEN before the answer move:** `5rk1/4qppp/2np4/r2p1p2/1p1Pn3/P3PN1P/2PN1PP1/R2QR1K1 w - - 0 17`
- **Answer:** blunder 17. Nxe4 (pre-move ES 0.61, ES after 0.42).
- **Missed best move:** axb4 (Maia probability 0.839, rank 1).

#### Window 6: pure_miss (length 3, blunder at 1)

- **Game:** https://www.chess.com/game/live/168153185584
- **User rating:** 876 (pinned Maia Elo 1303)
- **FEN before the lead-in:** `8/kp6/p5PR/6Kp/8/8/P4r2/8 b - - 2 42`
- **Lead-in:** 42... Rg2+ 43. Kxh5 Rxa2
- **Judged user moves:**
- **FEN before the answer move:** `8/kp6/p5PR/7K/8/8/r7/8 w - - 0 44`
- **Answer:** blunder 44. Kg5 (pre-move ES 0.85, ES after 0.52).
- **Missed best move:** g7 (Maia probability 0.917, rank 1).

#### Window 7: mixed (length 3, blunder at 2)

- **Game:** https://lichess.org/M3ju8fq2
- **User rating:** 1757 (pinned Maia Elo 1556)
- **FEN before the lead-in:** `r3r1k1/p1qn1pbp/5np1/1p1p2B1/2pp2BN/1PP1P2P/P4PP1/2RQ1RK1 w - - 0 17`
- **Lead-in:** 17. cxd4 Qb6 18. Bxf6
- **Judged user moves:**
  - 18... Nxf6 (Good, pre-move ES 0.59), reply 19. Nf3
- **FEN before the answer move:** `r3r1k1/p4pbp/1q3np1/1p1p4/2pP2B1/1P2PN1P/P4PP1/2RQ1RK1 b - - 1 19`
- **Answer:** blunder 19... Bh6 (pre-move ES 0.82, ES after 0.55).
- **Refutation:** Ne5 (Maia probability 0.565, rank 1).
- **Missed best move:** h5 (Maia probability 0.155, rank 3).

#### Window 8: herring (length 3, no blunder)

- **Game:** https://lichess.org/TyOreRrT
- **User rating:** 1693 (pinned Maia Elo 1479)
- **FEN before the lead-in:** `1kr5/1pp5/p7/8/2Pq3N/1Q6/PP4PP/5RK1 w - - 1 31`
- **Lead-in:** 31. Kh1 Qxh4 32. h3
- **Judged user moves:**
  - 32... Rh8 (Good, pre-move ES 0.27), reply 33. Rf3
  - 33... Qe1+ (Good, pre-move ES 0.32), reply 34. Kh2
  - 34... Rg8 (Good, pre-move ES 0.31), reply 35. c5
- **Answer:** all safe (every judged move is Good).

#### Window 9: allowed (length 5, blunder at 2)

- **Game:** https://www.chess.com/game/live/148255729216
- **User rating:** 851 (pinned Maia Elo 1269)
- **FEN before the lead-in:** `r3kbnr/pp3ppp/1q2p3/3p4/3n1B2/1P3B1P/P1P2PP1/RN1QK2R w KQkq - 0 10`
- **Lead-in:** 10. O-O Nxf3+ 11. Qxf3
- **Judged user moves:**
  - 11... Qd4 (Good, pre-move ES 0.61), reply 12. Nc3
- **FEN before the answer move:** `r3kbnr/pp3ppp/4p3/3p4/3q1B2/1PN2Q1P/P1P2PP1/R4RK1 b kq - 2 12`
- **Answer:** blunder 12... Bb4 (pre-move ES 0.53, ES after 0.19).
- **Refutation:** Nb5 (Maia probability 0.713, rank 1).

#### Window 10: herring (length 4, no blunder)

- **Game:** https://www.chess.com/game/live/145780476996
- **User rating:** 1292 (pinned Maia Elo 1458)
- **FEN before the lead-in:** `rnbqkbnr/pp2pppp/2p5/3p4/4PP2/8/PPPP2PP/RNBQKBNR w KQkq - 0 3`
- **Lead-in:** 3. Nc3 e6 4. Nf3
- **Judged user moves:**
  - 4... Nd7 (Good, pre-move ES 0.46), reply 5. d3
  - 5... Nb6 (Good, pre-move ES 0.45), reply 6. g3
  - 6... Bb4 (Good, pre-move ES 0.43), reply 7. Bd2
  - 7... Ne7 (Good, pre-move ES 0.43), reply 8. Bg2
- **Answer:** all safe (every judged move is Good).

#### Window 11: pure_miss (length 4, blunder at 1)

- **Game:** https://lichess.org/8w6XShFr
- **User rating:** 1468 (pinned Maia Elo 1280)
- **FEN before the lead-in:** `4r1k1/2p2pbp/pnqpr1p1/8/2P5/BPN5/P1Q2PPP/2RR2K1 w - - 2 20`
- **Lead-in:** 20. Qb1 Re5 21. Nd5
- **Judged user moves:**
- **FEN before the answer move:** `4r1k1/2p2pbp/pnqp2p1/3Nr3/2P5/BP6/P4PPP/1QRR2K1 b - - 5 21`
- **Answer:** blunder 21... Qb7 (pre-move ES 0.68, ES after 0.49).
- **Missed best move:** Nxd5 (Maia probability 0.633, rank 1).

#### Window 12: allowed (length 4, blunder at 1)

- **Game:** https://lichess.org/UGQ0FFNC
- **User rating:** 1238 (pinned Maia Elo 1369)
- **FEN before the lead-in:** `r2q1rk1/pp3ppp/2pp1b2/4p3/4P3/1P1P1Q1P/1PP2PP1/R1B2RK1 b - - 0 13`
- **Lead-in:** 13... a5 14. Bd2 b5
- **Judged user moves:**
- **FEN before the answer move:** `r2q1rk1/5ppp/2pp1b2/pp2p3/4P3/1P1P1Q1P/1PPB1PP1/R4RK1 w - - 0 15`
- **Answer:** blunder 15. Bxa5 (pre-move ES 0.53, ES after 0.20).
- **Refutation:** Rxa5 (Maia probability 0.907, rank 1).

#### Window 13: mixed (length 5, blunder at 2)

- **Game:** https://www.chess.com/game/live/43341588839
- **User rating:** 1317 (pinned Maia Elo 1473)
- **FEN before the lead-in:** `rn1q1rk1/ppp1b1pp/5pb1/3p4/8/1PN2N2/P1PPQPPP/R3KB1R b KQ - 7 9`
- **Lead-in:** 9... Nc6 10. O-O-O Ba3+
- **Judged user moves:**
  - 11. Kb1 (Good, pre-move ES 0.23), reply 11... f5
- **FEN before the answer move:** `r2q1rk1/ppp3pp/2n3b1/3p1p2/8/bPN2N2/P1PPQPPP/1K1R1B1R w - - 0 12`
- **Answer:** blunder 12. Ng5 (pre-move ES 0.50, ES after 0.15).
- **Refutation:** Qxg5 (Maia probability 0.717, rank 1).
- **Missed best move:** Qb5 (Maia probability 0.227, rank 1).

#### Window 14: allowed (length 5, blunder at 5)

- **Game:** https://www.chess.com/game/live/170038975290
- **User rating:** 988 (pinned Maia Elo 1410)
- **FEN before the lead-in:** `8/5p1R/4p1p1/5k2/6pP/r7/6PK/8 b - - 1 46`
- **Lead-in:** 46... f6 47. Rg7 e5
- **Judged user moves:**
  - 48. g3 (Good, pre-move ES 0.21), reply 48... e4
  - 49. Re7 (Good, pre-move ES 0.18), reply 49... e3
  - 50. Kg2 (Good, pre-move ES 0.44), reply 50... Ra2+
  - 51. Kf1 (Good, pre-move ES 0.46), reply 51... e2+
- **FEN before the answer move:** `8/4R3/5pp1/5k2/6pP/6P1/r3p3/5K2 w - - 0 52`
- **Answer:** blunder 52. Rxe2 (pre-move ES 0.46, ES after 0.06).
- **Refutation:** Rxe2 (Maia probability 0.672, rank 1).

#### Window 15: allowed (length 5, blunder at 1)

- **Game:** https://www.chess.com/game/live/139635861700
- **User rating:** 839 (pinned Maia Elo 1348)
- **FEN before the lead-in:** `4r3/1nk5/1pp3pp/5p2/1P4n1/2N1B2P/P1P1KPP1/3R4 b - - 0 24`
- **Lead-in:** 24... Nxe3 25. fxe3 f4
- **Judged user moves:**
- **FEN before the answer move:** `4r3/1nk5/1pp3pp/8/1P3p2/2N1P2P/P1P1K1P1/3R4 w - - 0 26`
- **Answer:** blunder 26. Kf3 (pre-move ES 0.56, ES after 0.19).
- **Refutation:** Rxe3+ (Maia probability 0.309, rank 2).

#### Window 16: allowed (length 3, blunder at 3)

- **Game:** https://www.chess.com/game/live/81449421443
- **User rating:** 1100 (pinned Maia Elo 1292)
- **FEN before the lead-in:** `4rrk1/p1p2ppp/8/3P1Q2/1b6/qP2B2P/P5P1/R6K w - - 1 20`
- **Lead-in:** 20. Bd4 Re1+ 21. Rxe1
- **Judged user moves:**
  - 21... Bxe1 (Good, pre-move ES 0.79), reply 22. Qg4
  - 22... g6 (Good, pre-move ES 0.86), reply 23. Qf4
- **FEN before the answer move:** `5rk1/p1p2p1p/6p1/3P4/3B1Q2/qP5P/P5P1/4b2K b - - 1 23`
- **Answer:** blunder 23... Qxa2 (pre-move ES 0.85, ES after 0.02).
- **Refutation:** Qf6 (Maia probability 0.579, rank 1).

#### Window 17: herring (length 4, no blunder)

- **Game:** https://www.chess.com/game/live/94064476751
- **User rating:** 1106 (pinned Maia Elo 1481)
- **FEN before the lead-in:** `rnbqkbnr/ppp1pppp/8/3P4/8/8/PPPP1PPP/RNBQKBNR b KQkq - 0 2`
- **Lead-in:** 2... c6 3. d4 cxd5
- **Judged user moves:**
  - 4. Nf3 (Good, pre-move ES 0.53), reply 4... Nc6
  - 5. c3 (Good, pre-move ES 0.53), reply 5... a6
  - 6. h3 (Good, pre-move ES 0.53), reply 6... Nf6
  - 7. Bf4 (Good, pre-move ES 0.54), reply 7... g6
- **Answer:** all safe (every judged move is Good).

#### Window 18: allowed (length 3, blunder at 3)

- **Game:** https://www.chess.com/game/live/94250553895
- **User rating:** 1171 (pinned Maia Elo 1542)
- **FEN before the lead-in:** `r2qk1nr/p1p2ppp/2p1b3/3pP3/1b6/2N1P3/PPPB1PPP/R2QK1NR b KQkq - 1 7`
- **Lead-in:** 7... Qg5 8. Qf3 Qxe5
- **Judged user moves:**
  - 9. O-O-O (Good, pre-move ES 0.49), reply 9... Nf6
  - 10. Nge2 (Good, pre-move ES 0.49), reply 10... Bg4
- **FEN before the answer move:** `r3k2r/p1p2ppp/2p2n2/3pq3/1b4b1/2N1PQ2/PPPBNPPP/2KR3R w kq - 4 11`
- **Answer:** blunder 11. Qg3 (pre-move ES 0.47, ES after 0.31).
- **Refutation:** Qxg3 (Maia probability 0.410, rank 1).

#### Window 19: allowed (length 5, blunder at 1)

- **Game:** https://lichess.org/11Mmynzr
- **User rating:** 1457 (pinned Maia Elo 1457)
- **FEN before the lead-in:** `r1bq1rk1/ppp2ppp/3p4/2b1p1N1/2BnP1n1/3P2N1/PPP2PPP/R1BQ1RK1 b - - 6 9`
- **Lead-in:** 9... h6 10. Nf3 Re8
- **Judged user moves:**
- **FEN before the answer move:** `r1bqr1k1/ppp2pp1/3p3p/2b1p3/2BnP1n1/3P1NN1/PPP2PPP/R1BQ1RK1 w - - 2 11`
- **Answer:** blunder 11. Nf5 (pre-move ES 0.55, ES after 0.31).
- **Refutation:** Nxf5 (Maia probability 0.606, rank 1).

#### Window 20: herring (length 4, no blunder)

- **Game:** https://lichess.org/mngSm9zy
- **User rating:** 1755 (pinned Maia Elo 1554)
- **FEN before the lead-in:** `3b1k2/p4ppp/4p3/4P3/5B2/4P2P/P3KPP1/8 b - - 3 27`
- **Lead-in:** 27... Ke7 28. Kd3 Kd7
- **Judged user moves:**
  - 29. Kc4 (Good, pre-move ES 0.51), reply 29... Kc6
  - 30. e4 (Good, pre-move ES 0.50), reply 30... Bb6
  - 31. Bg3 (Good, pre-move ES 0.50), reply 31... g6
  - 32. f4 (Good, pre-move ES 0.53), reply 32... a5
- **Answer:** all safe (every judged move is Good).

### 1600-1999

#### Window 1: herring (length 5, no blunder)

- **Game:** https://www.chess.com/game/live/173880123542
- **User rating:** 1725 (pinned Maia Elo 1845)
- **FEN before the lead-in:** `3r1rk1/2q2ppp/1p3n2/pPPp4/P7/3Q3P/N1P2PP1/RR4K1 b - - 0 21`
- **Lead-in:** 21... Qxc5 22. Rc1 Ne4
- **Judged user moves:**
  - 23. Qe3 (Good, pre-move ES 0.31), reply 23... Qxe3
  - 24. fxe3 (Good, pre-move ES 0.28), reply 24... Rfe8
  - 25. Rd1 (Good, pre-move ES 0.31), reply 25... g6
  - 26. Rac1 (Good, pre-move ES 0.36), reply 26... Ng3
  - 27. Nc3 (Good, pre-move ES 0.48), reply 27... Rxe3
- **Answer:** all safe (every judged move is Good).

#### Window 2: allowed (length 4, blunder at 3)

- **Game:** https://lichess.org/uB76tv55
- **User rating:** 1776 (pinned Maia Elo 1776)
- **FEN before the lead-in:** `rnbqkbnr/pp2pppp/8/3p4/8/5N2/PPPP1PPP/RNBQKB1R w KQkq - 0 4`
- **Lead-in:** 4. d4 Nc6 5. c4
- **Judged user moves:**
  - 5... Bg4 (Good, pre-move ES 0.48), reply 6. cxd5
  - 6... Qxd5 (Good, pre-move ES 0.47), reply 7. Nc3
- **FEN before the answer move:** `r3kbnr/pp2pppp/2n5/3q4/3P2b1/2N2N2/PP3PPP/R1BQKB1R b KQkq - 1 7`
- **Answer:** blunder 7... Qxd4 (pre-move ES 0.45, ES after 0.15).
- **Refutation:** Nxd4 (Maia probability 0.525, rank 1).

#### Window 3: allowed (length 3, blunder at 3)

- **Game:** https://www.chess.com/game/live/112901958115
- **User rating:** 1805 (pinned Maia Elo 1908)
- **FEN before the lead-in:** `r3kb1r/p3p1pp/2p2p2/5b2/3P4/2P2N2/P4PPP/R1B1K2R w KQkq - 0 13`
- **Lead-in:** 13. Nh4 Be4 14. f3
- **Judged user moves:**
  - 14... Bd5 (Good, pre-move ES 0.55), reply 15. Nf5
  - 15... e6 (Good, pre-move ES 0.52), reply 16. Ne3
- **FEN before the answer move:** `r3kb1r/p5pp/2p1pp2/3b4/3P4/2P1NP2/P5PP/R1B1K2R b KQkq - 1 16`
- **Answer:** blunder 16... Kf7 (pre-move ES 0.49, ES after 0.26).
- **Refutation:** c4 (Maia probability 0.716, rank 1).

#### Window 4: mixed (length 5, blunder at 5)

- **Game:** https://www.chess.com/game/live/172881316698
- **User rating:** 1769 (pinned Maia Elo 1885)
- **FEN before the lead-in:** `r2qk2r/5ppp/p1p2n2/2b1p3/6b1/2N5/PPPPNPPP/R1BQR2K b kq - 5 10`
- **Lead-in:** 10... Bxf2 11. Rf1 Ba7
- **Judged user moves:**
  - 12. d3 (Good, pre-move ES 0.45), reply 12... O-O
  - 13. Bg5 (Good, pre-move ES 0.56), reply 13... h6
  - 14. Bxf6 (Good, pre-move ES 0.58), reply 14... gxf6
  - 15. Qe1 (Good, pre-move ES 0.57), reply 15... Kh7
- **FEN before the answer move:** `r2q1r2/b4p1k/p1p2p1p/4p3/6b1/2NP4/PPP1N1PP/R3QR1K w - - 2 16`
- **Answer:** blunder 16. Qh4 (pre-move ES 0.78, ES after 0.49).
- **Refutation:** f5 (Maia probability 0.566, rank 1).
- **Missed best move:** Ng3 (Maia probability 0.199, rank 3).

#### Window 5: herring (length 3, no blunder)

- **Game:** https://www.chess.com/game/live/175698556165
- **User rating:** 1723 (pinned Maia Elo 1928)
- **FEN before the lead-in:** `rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1`
- **Lead-in:** 1. c4 Nf6
- **Judged user moves:**
  - 2. Nc3 (Good, pre-move ES 0.54), reply 2... g6
  - 3. Nf3 (Good, pre-move ES 0.55), reply 3... Bg7
  - 4. g3 (Good, pre-move ES 0.56), reply 4... O-O
- **Answer:** all safe (every judged move is Good).

#### Window 6: allowed (length 4, blunder at 1)

- **Game:** https://www.chess.com/game/live/98340871937
- **User rating:** 1476 (pinned Maia Elo 1621)
- **FEN before the lead-in:** `r3r1k1/pppq1pbp/2n1pnp1/2Pp2B1/3P3P/2NBPQ2/PP3PP1/R3K2R w KQ - 0 12`
- **Lead-in:** 12. h5 Nxh5 13. g4
- **Judged user moves:**
- **FEN before the answer move:** `r3r1k1/pppq1pbp/2n1p1p1/2Pp2Bn/3P2P1/2NBPQ2/PP3P2/R3K2R b KQ - 0 13`
- **Answer:** blunder 13... Nf6 (pre-move ES 0.38, ES after 0.17).
- **Refutation:** Bxf6 (Maia probability 0.793, rank 1).

#### Window 7: mixed (length 4, blunder at 2)

- **Game:** https://www.chess.com/game/live/184297978120
- **User rating:** 1462 (pinned Maia Elo 1612)
- **FEN before the lead-in:** `4r3/3r4/1p3k2/6p1/pPP4p/P2N1P1P/5KP1/3R4 b - - 2 34`
- **Lead-in:** 34... Kf5 35. Nb2 Rxd1
- **Judged user moves:**
  - 36. Nxd1 (Good, pre-move ES 0.30), reply 36... Kf4
- **FEN before the answer move:** `4r3/8/1p6/6p1/pPP2k1p/P4P1P/5KP1/3N4 w - - 1 37`
- **Answer:** blunder 37. Ne3 (pre-move ES 0.48, ES after 0.04).
- **Refutation:** Rxe3 (Maia probability 0.917, rank 1).
- **Missed best move:** Nc3 (Maia probability 0.727, rank 1).

#### Window 8: herring (length 5, no blunder)

- **Game:** https://lichess.org/smOtXDMT
- **User rating:** 2026 (pinned Maia Elo 1901)
- **FEN before the lead-in:** `8/8/1K6/p3rRk1/6P1/R6P/P2r4/8 b - - 14 56`
- **Lead-in:** 56... Rxf5 57. gxf5 Kxf5
- **Judged user moves:**
  - 58. Rxa5+ (Good, pre-move ES 0.68), reply 58... Kf4
  - 59. h4 (Good, pre-move ES 0.83), reply 59... Kg4
  - 60. h5 (Good, pre-move ES 0.83), reply 60... Rd6+
  - 61. Kc7 (Good, pre-move ES 0.85), reply 61... Rh6
  - 62. a4 (Good, pre-move ES 0.83), reply 62... Kf4
- **Answer:** all safe (every judged move is Good).

#### Window 9: allowed (length 3, blunder at 1)

- **Game:** https://www.chess.com/game/live/121886441529
- **User rating:** 1742 (pinned Maia Elo 1861)
- **FEN before the lead-in:** `3r2k1/4npp1/4p2p/nB6/NP6/P3PP2/5P1P/5RK1 b - - 0 21`
- **Lead-in:** 21... Nb3 22. Bc4 Nd2
- **Judged user moves:**
- **FEN before the answer move:** `3r2k1/4npp1/4p2p/8/NPB5/P3PP2/3n1P1P/5RK1 w - - 3 23`
- **Answer:** blunder 23. Rd1 (pre-move ES 0.68, ES after 0.19).
- **Refutation:** Nxf3+ (Maia probability 0.946, rank 1).

#### Window 10: allowed (length 3, blunder at 2)

- **Game:** https://www.chess.com/game/live/96560829165
- **User rating:** 1745 (pinned Maia Elo 1946)
- **FEN before the lead-in:** `r2qk2r/pp2bppp/2n1bn2/2pp2B1/3P4/2N2NP1/PP2PPBP/R2Q1RK1 b kq - 6 9`
- **Lead-in:** 9... c4 10. b3 Qa5
- **Judged user moves:**
  - 11. Rc1 (Good, pre-move ES 0.54), reply 11... Bb4
- **FEN before the answer move:** `r3k2r/pp3ppp/2n1bn2/q2p2B1/1bpP4/1PN2NP1/P3PPBP/2RQ1RK1 w kq - 3 12`
- **Answer:** blunder 12. Qd2 (pre-move ES 0.57, ES after 0.26).
- **Refutation:** Ne4 (Maia probability 0.942, rank 1).

#### Window 11: herring (length 3, no blunder)

- **Game:** https://www.chess.com/game/live/173477845804
- **User rating:** 1452 (pinned Maia Elo 1606)
- **FEN before the lead-in:** `r1bqk2r/pppnppbp/3p1np1/8/3PPP2/2N2N2/PPP3PP/R1BQKB1R w KQkq - 2 6`
- **Lead-in:** 6. Bd3 e5 7. fxe5
- **Judged user moves:**
  - 7... dxe5 (Good, pre-move ES 0.35), reply 8. d5
  - 8... O-O (Good, pre-move ES 0.47), reply 9. Bg5
  - 9... h6 (Good, pre-move ES 0.50), reply 10. Bh4
- **Answer:** all safe (every judged move is Good).

#### Window 12: allowed (length 5, blunder at 3)

- **Game:** https://www.chess.com/game/live/164348000000
- **User rating:** 1289 (pinned Maia Elo 1628)
- **FEN before the lead-in:** `rn1qk2r/pp2ppbp/2p2np1/6B1/2P3b1/2NB1N2/PP3PPP/R2Q1RK1 w kq - 2 9`
- **Lead-in:** 9. Re1 e6 10. Ne4
- **Judged user moves:**
  - 10... O-O (Good, pre-move ES 0.50), reply 11. h3
  - 11... Bxf3 (Good, pre-move ES 0.49), reply 12. Qxf3
- **FEN before the answer move:** `rn1q1rk1/pp3pbp/2p1pnp1/6B1/2P1N3/3B1Q1P/PP3PP1/R3R1K1 b - - 0 12`
- **Answer:** blunder 12... h6 (pre-move ES 0.45, ES after 0.16).
- **Refutation:** Bxf6 (Maia probability 0.512, rank 1).

#### Window 13: pure_miss (length 5, blunder at 1)

- **Game:** https://lichess.org/ULABWdAX
- **User rating:** 1792 (pinned Maia Elo 1792)
- **FEN before the lead-in:** `r3k1nr/p1p1p1bp/5pp1/2q5/5B2/8/PPP2PPP/RN1Q1RK1 w kq - 0 13`
- **Lead-in:** 13. Be3 Qb5 14. Bd4
- **Judged user moves:**
- **FEN before the answer move:** `r3k1nr/p1p1p1bp/5pp1/1q6/3B4/8/PPP2PPP/RN1Q1RK1 b kq - 3 14`
- **Answer:** blunder 14... e5 (pre-move ES 0.65, ES after 0.40).
- **Missed best move:** Rd8 (Maia probability 0.428, rank 1).

#### Window 14: allowed (length 4, blunder at 1)

- **Game:** https://lichess.org/jRLBeLys
- **User rating:** 1813 (pinned Maia Elo 1813)
- **FEN before the lead-in:** `4rrk1/pb4bp/1p4p1/3q4/8/1PpB3Q/P2B2PP/R4RK1 w - - 0 22`
- **Lead-in:** 22. Bc4 Qxc4 23. Rxf8+
- **Judged user moves:**
- **FEN before the answer move:** `4rRk1/pb4bp/1p4p1/8/2q5/1Pp4Q/P2B2PP/R5K1 b - - 0 23`
- **Answer:** blunder 23... Rxf8 (pre-move ES 0.50, ES after 0.25).
- **Refutation:** bxc4 (Maia probability 0.948, rank 1).

#### Window 15: pure_miss (length 5, blunder at 3)

- **Game:** https://www.chess.com/game/live/164972189972
- **User rating:** 1663 (pinned Maia Elo 1899)
- **FEN before the lead-in:** `3N2k1/5ppp/4p3/p4b2/q7/B2p4/P4PPP/2R2RK1 w - - 0 25`
- **Lead-in:** 25. Rc8 h6 26. Nxe6+
- **Judged user moves:**
  - 26... Kh7 (Good, pre-move ES 0.50), reply 27. Nf8+
  - 27... Kh8 (Good, pre-move ES 0.50), reply 28. Bd6
- **FEN before the answer move:** `2R2N1k/5pp1/3B3p/p4b2/q7/3p4/P4PPP/5RK1 b - - 4 28`
- **Answer:** blunder 28... d2 (pre-move ES 0.90, ES after 0.50).
- **Missed best move:** Bxc8 (Maia probability 0.791, rank 1).

#### Window 16: allowed (length 5, blunder at 1)

- **Game:** https://www.chess.com/game/live/165848895572
- **User rating:** 1804 (pinned Maia Elo 1973)
- **FEN before the lead-in:** `r1b1kb1r/pp3qpp/2p2n2/8/3Np3/8/PPP1B1PP/R1BQ1RK1 w kq - 0 14`
- **Lead-in:** 14. b3 Bc5 15. Bb2
- **Judged user moves:**
- **FEN before the answer move:** `r1b1k2r/pp3qpp/2p2n2/2b5/3Np3/1P6/PBP1B1PP/R2Q1RK1 b kq - 2 15`
- **Answer:** blunder 15... Bxd4+ (pre-move ES 0.65, ES after 0.44).
- **Refutation:** Qxd4 (Maia probability 0.403, rank 2).

#### Window 17: herring (length 3, no blunder)

- **Game:** https://www.chess.com/game/live/126785388339
- **User rating:** 1782 (pinned Maia Elo 1896)
- **FEN before the lead-in:** `2R5/6p1/6kp/6p1/8/2P4P/2r3P1/6K1 b - - 3 37`
- **Lead-in:** 37... Kh5 38. c4 g6
- **Judged user moves:**
  - 39. Rc5 (Good, pre-move ES 0.50), reply 39... Kh4
  - 40. Rc6 (Good, pre-move ES 0.50), reply 40... Kh5
  - 41. c5 (Good, pre-move ES 0.50), reply 41... Rc4
- **Answer:** all safe (every judged move is Good).

#### Window 18: pure_miss (length 5, blunder at 1)

- **Game:** https://www.chess.com/game/live/183982396124
- **User rating:** 1167 (pinned Maia Elo 1606)
- **FEN before the lead-in:** `r2qkbnr/pp1nppp1/2p4p/3pP3/3P4/3Q1N2/PPP2PPP/RNB1K2R w KQkq - 1 7`
- **Lead-in:** 7. O-O Qc7 8. Nc3
- **Judged user moves:**
- **FEN before the answer move:** `r3kbnr/ppqnppp1/2p4p/3pP3/3P4/2NQ1N2/PPP2PPP/R1B2RK1 b kq - 4 8`
- **Answer:** blunder 8... O-O-O (pre-move ES 0.44, ES after 0.25).
- **Missed best move:** e6 (Maia probability 0.657, rank 1).

#### Window 19: allowed (length 3, blunder at 2)

- **Game:** https://www.chess.com/game/live/35294867745
- **User rating:** 1414 (pinned Maia Elo 1716)
- **FEN before the lead-in:** `2r5/pp3pkp/8/2pN1bp1/8/1P3PB1/PKPnr1PP/6R1 b - - 3 25`
- **Lead-in:** 25... Be6 26. Ne7 Rc7
- **Judged user moves:**
  - 27. Bxc7 (Good, pre-move ES 0.50), reply 27... c4
- **FEN before the answer move:** `8/ppB1Npkp/4b3/6p1/2p5/1P3P2/PKPnr1PP/6R1 w - - 0 28`
- **Answer:** blunder 28. g4 (pre-move ES 0.52, ES after 0.20).
- **Refutation:** Nxf3 (Maia probability 0.345, rank 2).

#### Window 20: allowed (length 3, blunder at 1)

- **Game:** https://www.chess.com/game/live/12343607653
- **User rating:** 1518 (pinned Maia Elo 1650)
- **FEN before the lead-in:** `r3k1r1/1pp2p2/pbnp3p/5b2/2BPn2N/N7/PP3PPP/R1B1R1K1 b q - 4 16`
- **Lead-in:** 16... Bh7 17. f3 Bxd4+
- **Judged user moves:**
- **FEN before the answer move:** `r3k1r1/1pp2p1b/p1np3p/8/2Bbn2N/N4P2/PP4PP/R1B1R1K1 w q - 0 18`
- **Answer:** blunder 18. Kh1 (pre-move ES 0.51, ES after 0.28).
- **Refutation:** Bf2 (Maia probability 0.376, rank 2).

### 2000-2399

#### Window 1: allowed (length 5, blunder at 1)

- **Game:** https://www.chess.com/game/live/45457231241
- **User rating:** 2052 (pinned Maia Elo 2179)
- **FEN before the lead-in:** `8/p5kp/4p1p1/8/4N3/1R2K1P1/PPr2P1P/3r4 b - - 23 39`
- **Lead-in:** 39... Rf1 40. Rb7+ Kh6
- **Judged user moves:**
- **FEN before the answer move:** `8/pR5p/4p1pk/8/4N3/4K1P1/PPr2P1P/5r2 w - - 26 41`
- **Answer:** blunder 41. Rb8 (pre-move ES 0.51, ES after 0.35).
- **Refutation:** Re1+ (Maia probability 0.453, rank 1).

#### Window 2: allowed (length 5, blunder at 1)

- **Game:** https://lichess.org/QDq1Jq1Z
- **User rating:** 2123 (pinned Maia Elo 2060)
- **FEN before the lead-in:** `8/8/1b6/pN4kp/P3B3/5KP1/1P6/8 w - - 2 42`
- **Lead-in:** 42. Nd6 h4 43. Nf7+
- **Judged user moves:**
- **FEN before the answer move:** `8/5N2/1b6/p5k1/P3B2p/5KP1/1P6/8 b - - 1 43`
- **Answer:** blunder 43... Kh5 (pre-move ES 0.18, ES after 0.02).
- **Refutation:** g4# (Maia probability 0.823, rank 1).

#### Window 3: herring (length 5, no blunder)

- **Game:** https://lichess.org/PMP7WJcu
- **User rating:** 2418 (pinned Maia Elo 2310)
- **FEN before the lead-in:** `6k1/p4p1p/4p1p1/1N2b3/2P5/1P3P2/P6P/7K b - - 0 28`
- **Lead-in:** 28... a6 29. Kg2 axb5
- **Judged user moves:**
  - 30. cxb5 (Good, pre-move ES 0.18), reply 30... Bd4
  - 31. a4 (Good, pre-move ES 0.21), reply 31... Kf8
  - 32. b4 (Good, pre-move ES 0.20), reply 32... Ke7
  - 33. a5 (Good, pre-move ES 0.16), reply 33... Kd6
  - 34. b6 (Good, pre-move ES 0.16), reply 34... Kc6
- **Answer:** all safe (every judged move is Good).

#### Window 4: allowed (length 5, blunder at 3)

- **Game:** https://www.chess.com/game/live/166250216734
- **User rating:** 1947 (pinned Maia Elo 2111)
- **FEN before the lead-in:** `8/2k5/2rpR3/6r1/1p6/1P6/2PR4/2K5 b - - 3 40`
- **Lead-in:** 40... Rg1+ 41. Rd1 Rg2
- **Judged user moves:**
  - 42. Rd2 (Good, pre-move ES 0.50), reply 42... Rg1+
  - 43. Kb2 (Good, pre-move ES 0.50), reply 43... Rg3
- **FEN before the answer move:** `8/2k5/2rpR3/8/1p6/1P4r1/1KPR4/8 w - - 10 44`
- **Answer:** blunder 44. Rexd6 (pre-move ES 0.53, ES after 0.18).
- **Refutation:** Rxd6 (Maia probability 0.852, rank 1).

#### Window 5: herring (length 5, no blunder)

- **Game:** https://www.chess.com/game/live/63586738445
- **User rating:** 2110 (pinned Maia Elo 2210)
- **FEN before the lead-in:** `r2qr1k1/1p3ppp/p1pb4/2Np4/1P1P4/P3P1P1/5PKP/2RQ1R2 b - - 0 19`
- **Lead-in:** 19... Bxc5 20. bxc5 Re7
- **Judged user moves:**
  - 21. Rb1 (Good, pre-move ES 0.52), reply 21... Qd7
  - 22. Rb6 (Good, pre-move ES 0.53), reply 22... Qe6
  - 23. Qd3 (Good, pre-move ES 0.55), reply 23... Rd8
  - 24. Rfb1 (Good, pre-move ES 0.51), reply 24... Rdd7
  - 25. a4 (Good, pre-move ES 0.51), reply 25... h5
- **Answer:** all safe (every judged move is Good).

#### Window 6: allowed (length 5, blunder at 2)

- **Game:** https://lichess.org/scKFgksk
- **User rating:** 2201 (pinned Maia Elo 2201)
- **FEN before the lead-in:** `r1bqr1k1/pp1n1ppp/2p1pn2/2Pp4/P2P4/B1P2N2/4PPPP/R2QKB1R w KQ - 2 10`
- **Lead-in:** 10. Ne5 Nxe5 11. dxe5
- **Judged user moves:**
  - 11... Nd7 (Good, pre-move ES 0.62), reply 12. f4
- **FEN before the answer move:** `r1bqr1k1/pp1n1ppp/2p1p3/2PpP3/P4P2/B1P5/4P1PP/R2QKB1R b KQ - 0 12`
- **Answer:** blunder 12... g5 (pre-move ES 0.63, ES after 0.42).
- **Refutation:** e3 (Maia probability 0.735, rank 1).

#### Window 7: allowed (length 5, blunder at 1)

- **Game:** https://www.chess.com/game/live/3655293329
- **User rating:** 2089 (pinned Maia Elo 2162)
- **FEN before the lead-in:** `r3kbr1/1p5p/p2qp1p1/3n4/4Q3/4B3/PP3PPP/2R2RK1 w q - 6 26`
- **Lead-in:** 26. Rfe1 Kf7 27. Bd4
- **Judged user moves:**
- **FEN before the answer move:** `r4br1/1p3k1p/p2qp1p1/3n4/3BQ3/8/PP3PPP/2R1R1K1 b - - 9 27`
- **Answer:** blunder 27... Bg7 (pre-move ES 0.75, ES after 0.53).
- **Refutation:** Qf3+ (Maia probability 0.321, rank 2).

#### Window 8: herring (length 3, no blunder)

- **Game:** https://lichess.org/i55vY0qu
- **User rating:** 2359 (pinned Maia Elo 2359)
- **FEN before the lead-in:** `rr4k1/5ppp/1q1p4/3Pp1bP/1B4P1/P2Q1P2/1P6/1K1R3R w - - 5 26`
- **Lead-in:** 26. Rh2 Bf4 27. Rc2
- **Judged user moves:**
  - 27... Rd8 (Good, pre-move ES 0.30), reply 28. Rc6
  - 28... Qb8 (Good, pre-move ES 0.27), reply 29. Qc4
  - 29... g6 (Good, pre-move ES 0.27), reply 30. hxg6
- **Answer:** all safe (every judged move is Good).

#### Window 9: mixed (length 3, blunder at 2)

- **Game:** https://www.chess.com/game/live/141840195678
- **User rating:** 2276 (pinned Maia Elo 2281)
- **FEN before the lead-in:** `1rb2k1r/2qn1pp1/p3p3/b1ppP2p/N4PQ1/2P1BR2/PP2B1PP/R5K1 w - - 0 17`
- **Lead-in:** 17. Qg5 g6 18. Rg3
- **Judged user moves:**
  - 18... Qc6 (Good, pre-move ES 0.51), reply 19. Nxc5
- **FEN before the answer move:** `1rb2k1r/3n1p2/p1q1p1p1/b1NpP1Qp/5P2/2P1B1R1/PP2B1PP/R5K1 b - - 0 19`
- **Answer:** blunder 19... Bd8 (pre-move ES 0.70, ES after 0.03).
- **Refutation:** Qxd8+ (Maia probability 0.610, rank 1).
- **Missed best move:** Nxc5 (Maia probability 0.861, rank 1).

#### Window 10: mixed (length 4, blunder at 1)

- **Game:** https://lichess.org/ZZ1JjkrL
- **User rating:** 2168 (pinned Maia Elo 2086)
- **FEN before the lead-in:** `r3r1k1/ppR5/3p2qp/8/3bPP2/7Q/1P6/1K3R2 b - - 0 33`
- **Lead-in:** 33... Rxe4 34. f5 Qg5
- **Judged user moves:**
- **FEN before the answer move:** `r5k1/ppR5/3p3p/5Pq1/3br3/7Q/1P6/1K3R2 w - - 1 35`
- **Answer:** blunder 35. Qf3 (pre-move ES 0.65, ES after 0.21).
- **Refutation:** Rae8 (Maia probability 0.620, rank 1).
- **Missed best move:** Qb3+ (Maia probability 0.411, rank 2).

#### Window 11: allowed (length 5, blunder at 1)

- **Game:** https://www.chess.com/game/live/48302965083
- **User rating:** 1993 (pinned Maia Elo 2142)
- **FEN before the lead-in:** `6k1/pp1R2pp/2p1p3/r7/2P5/1P5P/P5P1/6K1 w - - 2 32`
- **Lead-in:** 32. a4 b6 33. Rc7
- **Judged user moves:**
- **FEN before the answer move:** `6k1/p1R3pp/1pp1p3/r7/P1P5/1P5P/6P1/6K1 b - - 1 33`
- **Answer:** blunder 33... c5 (pre-move ES 0.50, ES after 0.19).
- **Refutation:** Kf2 (Maia probability 0.567, rank 1).

#### Window 12: allowed (length 5, blunder at 1)

- **Game:** https://lichess.org/T0AHJ8hQ
- **User rating:** 2180 (pinned Maia Elo 2092)
- **FEN before the lead-in:** `8/pp2k1n1/6P1/2p1KP2/8/8/PP6/8 b - - 2 36`
- **Lead-in:** 36... Nxf5 37. Kxf5 b5
- **Judged user moves:**
- **FEN before the answer move:** `8/p3k3/6P1/1pp2K2/8/8/PP6/8 w - - 0 38`
- **Answer:** blunder 38. Kg5 (pre-move ES 0.86, ES after 0.50).
- **Refutation:** Kf8 (Maia probability 0.699, rank 1).

#### Window 13: pure_miss (length 3, blunder at 2)

- **Game:** https://lichess.org/A70m2nbj
- **User rating:** 2332 (pinned Maia Elo 2332)
- **FEN before the lead-in:** `2r5/8/1np2kp1/1p2p3/4Pb2/1PP3N1/6K1/3R1R2 w - - 0 34`
- **Lead-in:** 34. Ne2 g5 35. Rd6+
- **Judged user moves:**
  - 35... Ke7 (Good, pre-move ES 0.30), reply 36. Rfd1
- **FEN before the answer move:** `2r5/4k3/1npR4/1p2p1p1/4Pb2/1PP5/4N1K1/3R4 b - - 3 36`
- **Answer:** blunder 36... Rc7 (pre-move ES 0.50, ES after 0.25).
- **Missed best move:** Nd5 (Maia probability 0.212, rank 2).

#### Window 14: allowed (length 4, blunder at 3)

- **Game:** https://lichess.org/MtNiMeUW
- **User rating:** 2126 (pinned Maia Elo 2126)
- **FEN before the lead-in:** `rn1qk2r/pp2bppp/4pn2/3p1bB1/3P4/2N1PN2/PP3PPP/R2QKB1R w KQkq - 1 8`
- **Lead-in:** 8. Bb5+ Nc6 9. Ne5
- **Judged user moves:**
  - 9... Rc8 (Good, pre-move ES 0.48), reply 10. Qa4
  - 10... Qb6 (Good, pre-move ES 0.48), reply 11. O-O
- **FEN before the answer move:** `2r1k2r/pp2bppp/1qn1pn2/1B1pNbB1/Q2P4/2N1P3/PP3PPP/R4RK1 b k - 8 11`
- **Answer:** blunder 11... O-O (pre-move ES 0.49, ES after 0.29).
- **Refutation:** Bxf6 (Maia probability 0.802, rank 1).

#### Window 15: allowed (length 5, blunder at 3)

- **Game:** https://lichess.org/yeZbVhfs
- **User rating:** 2288 (pinned Maia Elo 2288)
- **FEN before the lead-in:** `rnbqkbnr/ppp1pppp/8/3p4/8/5N2/PPPPPPPP/RNBQKB1R w KQkq - 0 2`
- **Lead-in:** 2. g3 g6 3. Bg2
- **Judged user moves:**
  - 3... Bg7 (Good, pre-move ES 0.47), reply 4. O-O
  - 4... e5 (Good, pre-move ES 0.49), reply 5. d3
- **FEN before the answer move:** `rnbqk1nr/ppp2pbp/6p1/3pp3/8/3P1NP1/PPP1PPBP/RNBQ1RK1 b kq - 0 5`
- **Answer:** blunder 5... e4 (pre-move ES 0.48, ES after 0.31).
- **Refutation:** dxe4 (Maia probability 0.866, rank 1).

#### Window 16: herring (length 5, no blunder)

- **Game:** https://www.chess.com/game/live/146285982628
- **User rating:** 2057 (pinned Maia Elo 2140)
- **FEN before the lead-in:** `r1b2rk1/pp2qppp/1nn1p3/2pP4/2P5/2N2N2/PP2BPPP/R2Q1RK1 b - - 0 12`
- **Lead-in:** 12... exd5 13. cxd5 Ne5
- **Judged user moves:**
  - 14. Nxe5 (Good, pre-move ES 0.60), reply 14... Qxe5
  - 15. Bf3 (Good, pre-move ES 0.56), reply 15... Bf5
  - 16. Re1 (Good, pre-move ES 0.54), reply 16... Qd6
  - 17. Nb5 (Good, pre-move ES 0.54), reply 17... Qd7
  - 18. a4 (Good, pre-move ES 0.52), reply 18... a6
- **Answer:** all safe (every judged move is Good).

#### Window 17: mixed (length 5, blunder at 2)

- **Game:** https://www.chess.com/game/live/116996417071
- **User rating:** 2009 (pinned Maia Elo 2106)
- **FEN before the lead-in:** `rn1qr1k1/pp2p3/2p2ppB/4Nb1p/3P1Q1P/2P5/PP3PP1/R3K2R b KQ - 1 16`
- **Lead-in:** 16... Qd5 17. c4 Qxg2
- **Judged user moves:**
  - 18. O-O-O (Good, pre-move ES 0.32), reply 18... Nd7
- **FEN before the answer move:** `r3r1k1/pp1np3/2p2ppB/4Nb1p/2PP1Q1P/8/PP3Pq1/2KR3R w - - 2 19`
- **Answer:** blunder 19. Rde1 (pre-move ES 0.66, ES after 0.16).
- **Refutation:** fxe5 (Maia probability 0.824, rank 1).
- **Missed best move:** Nxd7 (Maia probability 0.355, rank 1).

#### Window 18: herring (length 3, no blunder)

- **Game:** https://www.chess.com/game/live/168375313176
- **User rating:** 1986 (pinned Maia Elo 2137)
- **FEN before the lead-in:** `r2q1rk1/pb3ppp/1p1p1n2/4p3/4n2N/2P3P1/PP3PBP/R1BQR1K1 w - - 0 14`
- **Lead-in:** 14. Nf5 Nc5 15. Bxb7
- **Judged user moves:**
  - 15... Nxb7 (Good, pre-move ES 0.46), reply 16. Bg5
  - 16... h6 (Good, pre-move ES 0.45), reply 17. Bxh6
  - 17... gxh6 (Good, pre-move ES 0.59), reply 18. Nxh6+
- **Answer:** all safe (every judged move is Good).

#### Window 19: herring (length 4, no blunder)

- **Game:** https://lichess.org/MQw2b2pr
- **User rating:** 2018 (pinned Maia Elo 2018)
- **FEN before the lead-in:** `rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1`
- **Lead-in:** 1. d4 Nf6
- **Judged user moves:**
  - 2. c4 (Good, pre-move ES 0.53), reply 2... e5
  - 3. dxe5 (Good, pre-move ES 0.57), reply 3... Ng4
  - 4. Nf3 (Good, pre-move ES 0.56), reply 4... Bc5
  - 5. e3 (Good, pre-move ES 0.56), reply 5... Nc6
- **Answer:** all safe (every judged move is Good).

#### Window 20: allowed (length 3, blunder at 3)

- **Game:** https://www.chess.com/game/live/170456664670
- **User rating:** 2119 (pinned Maia Elo 2216)
- **FEN before the lead-in:** `5rk1/2r2ppp/p2qp3/np1p4/3P2P1/P1PQ1B1P/1P3P2/R3R1K1 w - - 1 22`
- **Lead-in:** 22. a4 bxa4 23. Rxa4
- **Judged user moves:**
  - 23... Nc4 (Good, pre-move ES 0.52), reply 24. b3
  - 24... Nb2 (Good, pre-move ES 0.81), reply 25. Qxa6
- **FEN before the answer move:** `5rk1/2r2ppp/Q2qp3/3p4/R2P2P1/1PP2B1P/1n3P2/4R1K1 b - - 0 25`
- **Answer:** blunder 25... Qxa6 (pre-move ES 0.79, ES after 0.53).
- **Refutation:** Rxa6 (Maia probability 0.998, rank 1).

### 2400+

#### Window 1: pure_miss (length 5, blunder at 4)

- **Game:** https://www.chess.com/game/live/3069776409
- **User rating:** 2578 (pinned Maia Elo 2535)
- **FEN before the lead-in:** `r3q3/1QRnrppk/3R3p/p2p4/3P1B2/1P4P1/P4P1P/6K1 w - - 4 25`
- **Lead-in:** 25. Qxd5 Re1+ 26. Kg2
- **Judged user moves:**
  - 26... Nf6 (Good, pre-move ES 0.24), reply 27. Qf5+
  - 27... Kg8 (Good, pre-move ES 0.23), reply 28. Bxh6
  - 28... Qe4+ (Good, pre-move ES 0.37), reply 29. Qf3
- **FEN before the answer move:** `r5k1/2R2pp1/3R1n1B/p7/3Pq3/1P3QP1/P4PKP/4r3 b - - 2 29`
- **Answer:** blunder 29... Qxf3+ (pre-move ES 0.84, ES after 0.52).
- **Missed best move:** Rg1+ (Maia probability 0.969, rank 1).

#### Window 2: herring (length 3, no blunder)

- **Game:** https://www.chess.com/game/live/139254646919
- **User rating:** 2651 (pinned Maia Elo 2593)
- **FEN before the lead-in:** `r1bqkb1r/pppn1ppp/3p1n2/4p3/3PP3/2N2N2/PPP2PPP/R1BQKB1R w KQkq - 4 5`
- **Lead-in:** 5. g4 exd4 6. Nxd4
- **Judged user moves:**
  - 6... Nc5 (Good, pre-move ES 0.38), reply 7. Bg2
  - 7... Bxg4 (Good, pre-move ES 0.53), reply 8. f3
  - 8... Bd7 (Good, pre-move ES 0.54), reply 9. Be3
- **Answer:** all safe (every judged move is Good).

#### Window 3: herring (length 3, no blunder)

- **Game:** https://www.chess.com/game/live/2278175040
- **User rating:** 2482 (pinned Maia Elo 2432)
- **FEN before the lead-in:** `r1bqk2r/1p1nbppp/p1n1p3/2ppP3/3P1P2/2N1BN2/PPPQ2PP/R3KB1R w KQkq - 0 9`
- **Lead-in:** 9. Qf2 b6 10. O-O-O
- **Judged user moves:**
  - 10... O-O (Good, pre-move ES 0.42), reply 11. g4
  - 11... f6 (Good, pre-move ES 0.45), reply 12. exf6
  - 12... Nxf6 (Good, pre-move ES 0.44), reply 13. Rg1
- **Answer:** all safe (every judged move is Good).

#### Window 4: herring (length 4, no blunder)

- **Game:** https://lichess.org/tHaa3Un7
- **User rating:** 2904 (pinned Maia Elo 2600)
- **FEN before the lead-in:** `rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1`
- **Lead-in:** 1. d4 Nf6
- **Judged user moves:**
  - 2. c3 (Good, pre-move ES 0.52), reply 2... d5
  - 3. Nf3 (Good, pre-move ES 0.50), reply 3... Bf5
  - 4. Qb3 (Good, pre-move ES 0.51), reply 4... Qc8
  - 5. Bf4 (Good, pre-move ES 0.51), reply 5... e6
- **Answer:** all safe (every judged move is Good).

#### Window 5: allowed (length 5, blunder at 2)

- **Game:** https://lichess.org/48FWFxdN
- **User rating:** 2725 (pinned Maia Elo 2585)
- **FEN before the lead-in:** `R7/5pkp/3P2p1/1p6/8/6PB/p5KP/3r4 b - - 3 41`
- **Lead-in:** 41... Ra1 42. d7 Rd1
- **Judged user moves:**
  - 43. Rxa2 (Good, pre-move ES 0.75), reply 43... f5
- **FEN before the answer move:** `8/3P2kp/6p1/1p3p2/8/6PB/R5KP/3r4 w - - 0 44`
- **Answer:** blunder 44. Re2 (pre-move ES 0.73, ES after 0.51).
- **Refutation:** Rxd7 (Maia probability 0.977, rank 1).

#### Window 6: allowed (length 3, blunder at 2)

- **Game:** https://www.chess.com/game/live/165760503496
- **User rating:** 3189 (pinned Maia Elo 2600)
- **FEN before the lead-in:** `3r4/4bk1p/p3p3/5p2/P1q2P2/1pPP2rP/1P1R1B2/2K1R3 w - - 0 35`
- **Lead-in:** 35. dxc4 Rxd2 36. Kxd2
- **Judged user moves:**
  - 36... Rxh3 (Good, pre-move ES 0.56), reply 37. c5
- **FEN before the answer move:** `8/4bk1p/p3p3/2P2p2/P4P2/1pP4r/1P1K1B2/4R3 b - - 0 37`
- **Answer:** blunder 37... Rf3 (pre-move ES 0.62, ES after 0.39).
- **Refutation:** Be3 (Maia probability 0.568, rank 1).

#### Window 7: herring (length 3, no blunder)

- **Game:** https://www.chess.com/game/live/84462890627
- **User rating:** 2837 (pinned Maia Elo 2600)
- **FEN before the lead-in:** `rn1qkbnr/pp3ppp/2p1p3/3p4/4P3/2NP1Q1P/PPP2PP1/R1B1KB1R b KQkq - 0 6`
- **Lead-in:** 6... Bb4 7. Bd2 d4
- **Judged user moves:**
  - 8. Nb1 (Good, pre-move ES 0.52), reply 8... Qb6
  - 9. Be2 (Good, pre-move ES 0.52), reply 9... Nd7
  - 10. O-O (Good, pre-move ES 0.54), reply 10... Ne7
- **Answer:** all safe (every judged move is Good).

#### Window 8: allowed (length 5, blunder at 3)

- **Game:** https://lichess.org/SO8cUh1w
- **User rating:** 2449 (pinned Maia Elo 2449)
- **FEN before the lead-in:** `1r2qr2/p3kp1Q/2p1p3/2pp4/5N2/2PP1R2/Pb4PP/5R1K b - - 2 25`
- **Lead-in:** 25... Kd6 26. Nxe6 Qxe6
- **Judged user moves:**
  - 27. Rf6 (Good, pre-move ES 0.49), reply 27... Bxc3
  - 28. Rxe6+ (Good, pre-move ES 0.50), reply 28... fxe6
- **FEN before the answer move:** `1r3r2/p6Q/2pkp3/2pp4/8/2bP4/P5PP/5R1K w - - 0 29`
- **Answer:** blunder 29. Rxf8 (pre-move ES 0.49, ES after 0.02).
- **Refutation:** Rb1+ (Maia probability 0.403, rank 2).

#### Window 9: allowed (length 5, blunder at 1)

- **Game:** https://www.chess.com/game/live/105110488005
- **User rating:** 2878 (pinned Maia Elo 2600)
- **FEN before the lead-in:** `8/8/8/1R6/7r/3KB2k/8/8 w - - 18 65`
- **Lead-in:** 65. Ke2 Rg4 66. Bf2
- **Judged user moves:**
- **FEN before the answer move:** `8/8/8/1R6/6r1/7k/4KB2/8 b - - 21 66`
- **Answer:** blunder 66... Rg3 (pre-move ES 0.49, ES after 0.02).
- **Refutation:** Bxg3 (Maia probability 0.579, rank 1).

#### Window 10: herring (length 3, no blunder)

- **Game:** https://www.chess.com/game/live/166712769260
- **User rating:** 3177 (pinned Maia Elo 2600)
- **FEN before the lead-in:** `r3k2r/pp3p1p/2p1p3/q3P1p1/2P3n1/3B1bB1/PP2K2P/R2Q3R w kq - 0 17`
- **Lead-in:** 17. Kxf3 Nxe5+ 18. Bxe5
- **Judged user moves:**
  - 18... Qxe5 (Good, pre-move ES 0.48), reply 19. Qe2
  - 19... Qd4 (Good, pre-move ES 0.48), reply 20. Rad1
  - 20... O-O-O (Good, pre-move ES 0.43), reply 21. Kg2
- **Answer:** all safe (every judged move is Good).

#### Window 11: allowed (length 3, blunder at 2)

- **Game:** https://www.chess.com/game/live/86895006623
- **User rating:** 2842 (pinned Maia Elo 2600)
- **FEN before the lead-in:** `1nr3k1/4bpp1/p1q1p2p/5b1P/1p2p3/1Q2B1N1/P3BPP1/3R2K1 w - - 1 28`
- **Lead-in:** 28. Nxf5 exf5 29. Rc1
- **Judged user moves:**
  - 29... Qd7 (Good, pre-move ES 0.63), reply 30. Bc4
- **FEN before the answer move:** `1nr3k1/3qbpp1/p6p/5p1P/1pB1p3/1Q2B3/P4PP1/2R3K1 b - - 3 30`
- **Answer:** blunder 30... Bf6 (pre-move ES 0.64, ES after 0.41).
- **Refutation:** Bxf7+ (Maia probability 0.802, rank 1).

#### Window 12: allowed (length 3, blunder at 3)

- **Game:** https://www.chess.com/game/live/143722145680
- **User rating:** 2370 (pinned Maia Elo 2574)
- **FEN before the lead-in:** `1r1q1rk1/2p2pp1/p2bb2p/2pNR3/8/1P1B1Q1P/P1P2PP1/R5K1 w - - 1 19`
- **Lead-in:** 19. Rh5 g6 20. Nf6+
- **Judged user moves:**
  - 20... Kg7 (Good, pre-move ES 0.77), reply 21. Ne4
  - 21... gxh5 (Good, pre-move ES 0.75), reply 22. Qxh5
- **FEN before the answer move:** `1r1q1r2/2p2pk1/p2bb2p/2p4Q/4N3/1P1B3P/P1P2PP1/R5K1 b - - 0 22`
- **Answer:** blunder 22... Bd5 (pre-move ES 0.82, ES after 0.50).
- **Refutation:** Qg4+ (Maia probability 0.484, rank 1).

#### Window 13: mixed (length 3, blunder at 1)

- **Game:** https://www.chess.com/game/live/137413440298
- **User rating:** 2621 (pinned Maia Elo 2574)
- **FEN before the lead-in:** `5rk1/pb3pp1/1p3q2/2n2NQ1/8/6P1/5P1P/3RR1K1 w - - 5 31`
- **Lead-in:** 31. Qh5 g6 32. Qg4
- **Judged user moves:**
- **FEN before the answer move:** `5rk1/pb3p2/1p3qp1/2n2N2/6Q1/6P1/5P1P/3RR1K1 b - - 1 32`
- **Answer:** blunder 32... Ne6 (pre-move ES 0.77, ES after 0.39).
- **Refutation:** Nd6 (Maia probability 0.448, rank 1).
- **Missed best move:** Qxf5 (Maia probability 0.756, rank 1).

#### Window 14: allowed (length 5, blunder at 2)

- **Game:** https://lichess.org/2joxkwbc
- **User rating:** 2449 (pinned Maia Elo 2449)
- **FEN before the lead-in:** `2r5/2P2p2/6p1/7p/6kP/2R3P1/8/2K5 w - - 1 50`
- **Lead-in:** 50. Kb2 f5 51. Kb3
- **Judged user moves:**
  - 51... f4 (Good, pre-move ES 0.50), reply 52. gxf4
- **FEN before the answer move:** `2r5/2P5/6p1/7p/5PkP/1KR5/8/8 b - - 0 52`
- **Answer:** blunder 52... Kxf4 (pre-move ES 0.50, ES after 0.32).
- **Refutation:** Kb4 (Maia probability 0.571, rank 1).

#### Window 15: herring (length 4, no blunder)

- **Game:** https://www.chess.com/game/live/142673664126
- **User rating:** 2503 (pinned Maia Elo 2600)
- **FEN before the lead-in:** `rn2k2r/pppb1pb1/5qpp/3Np3/2B1P3/8/PPP1QPPP/3RK1NR b Kkq - 1 10`
- **Lead-in:** 10... Qd8 11. Qf3 O-O
- **Judged user moves:**
  - 12. Ne2 (Good, pre-move ES 0.50), reply 12... c6
  - 13. Ne3 (Good, pre-move ES 0.46), reply 13... Qe7
  - 14. O-O (Good, pre-move ES 0.49), reply 14... Be6
  - 15. Bxe6 (Good, pre-move ES 0.52), reply 15... Qxe6
- **Answer:** all safe (every judged move is Good).

#### Window 16: herring (length 4, no blunder)

- **Game:** https://www.chess.com/game/live/112348824103
- **User rating:** 2996 (pinned Maia Elo 2600)
- **FEN before the lead-in:** `2rqr1k1/pp1n1pbp/2nP2p1/3Np3/4p3/2P4P/PP3PP1/R1BQRBK1 b - - 2 18`
- **Lead-in:** 18... Nc5 19. Nc7 Rxc7
- **Judged user moves:**
  - 20. dxc7 (Good, pre-move ES 0.73), reply 20... Qxc7
  - 21. Be3 (Good, pre-move ES 0.71), reply 21... Rd8
  - 22. Qc2 (Good, pre-move ES 0.73), reply 22... Nd3
  - 23. Red1 (Good, pre-move ES 0.74), reply 23... Nd4
- **Answer:** all safe (every judged move is Good).

#### Window 17: mixed (length 3, blunder at 2)

- **Game:** https://www.chess.com/game/live/3610968136
- **User rating:** 2600 (pinned Maia Elo 2560)
- **FEN before the lead-in:** `r2qr1k1/2p2pp1/bp1p1n1p/p1bpn3/2P1P3/PPN4P/2B1NPP1/1RBQ1R1K w - - 0 15`
- **Lead-in:** 15. exd5 Nfg4 16. Ne4
- **Judged user moves:**
  - 16... Qh4 (Good, pre-move ES 0.38), reply 17. Kg1
- **FEN before the answer move:** `r3r1k1/2p2pp1/bp1p3p/p1bPn3/2P1N1nq/PP5P/2B1NPP1/1RBQ1RK1 b - - 4 17`
- **Answer:** blunder 17... a4 (pre-move ES 0.50, ES after 0.33).
- **Refutation:** Nxc5 (Maia probability 0.352, rank 1).
- **Missed best move:** Nf3+ (Maia probability 0.580, rank 1).

#### Window 18: herring (length 4, no blunder)

- **Game:** https://www.chess.com/game/live/85965622551
- **User rating:** 2803 (pinned Maia Elo 2600)
- **FEN before the lead-in:** `4r1k1/1pq1r2p/2p1bppb/p2n4/P1NPBp2/2PQ3P/1P2RPPB/4R1K1 b - - 9 24`
- **Lead-in:** 24... Kg7 25. Bf3 Bg5
- **Judged user moves:**
  - 26. Qd2 (Good, pre-move ES 0.50), reply 26... h5
  - 27. Na3 (Good, pre-move ES 0.49), reply 27... Bh6
  - 28. Nc2 (Good, pre-move ES 0.50), reply 28... Nb6
  - 29. d5 (Good, pre-move ES 0.46), reply 29... Bxd5
- **Answer:** all safe (every judged move is Good).

#### Window 19: allowed (length 4, blunder at 1)

- **Game:** https://lichess.org/sOkW0kDD
- **User rating:** 2636 (pinned Maia Elo 2600)
- **FEN before the lead-in:** `5rk1/1q5p/2p2rp1/1pQ4n/2p1P3/2N4P/1PR2PB1/3R2K1 b - - 1 25`
- **Lead-in:** 25... Nf4 26. e5 Re6
- **Judged user moves:**
- **FEN before the answer move:** `5rk1/1q5p/2p1r1p1/1pQ1P3/2p2n2/2N4P/1PR2PB1/3R2K1 w - - 1 27`
- **Answer:** blunder 27. Rd6 (pre-move ES 0.78, ES after 0.61).
- **Refutation:** Qe7 (Maia probability 0.475, rank 1).

#### Window 20: herring (length 4, no blunder)

- **Game:** https://www.chess.com/game/live/98895336663
- **User rating:** 2864 (pinned Maia Elo 2600)
- **FEN before the lead-in:** `r2R2k1/pp2rpbp/1np3p1/N7/2P5/P5B1/1PK2PPP/3R4 b - - 6 24`
- **Lead-in:** 24... Re8 25. Rxa8 Rxa8
- **Judged user moves:**
  - 26. b3 (Good, pre-move ES 0.77), reply 26... Bf8
  - 27. a4 (Good, pre-move ES 0.77), reply 27... Re8
  - 28. Nxb7 (Good, pre-move ES 0.77), reply 28... Bb4
  - 29. Rd8 (Good, pre-move ES 0.79), reply 29... Kf8
- **Answer:** all safe (every judged move is Good).
