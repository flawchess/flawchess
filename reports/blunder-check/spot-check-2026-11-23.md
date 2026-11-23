# Blunder-check spot-check

Windows drawn the way the feature draws them (250 D-12): each slot is independently a herring (about 33%, all judged moves safe) or a blunder window, with length L uniform over 3 to 5 user moves. About 20 windows per Elo bucket, at most one per game, drawn with a fixed seed. A blunder window shows its facepalm score inputs after the answer.

Thresholds: facepalm score at least 0.7, eval band [0.10, 0.90] on the pre-move ES. A recommendation only; nothing here is wired into app code.

How to read: for each window, play through the lead-in and the judged moves on the board (the game link opens the game on FlawChess at the first judged move), decide whether the position is a fair question, then compare with the answer. A blunder window is fair when the refutation or the missed move is something a player of that rating could find. Moves are in SAN; a stored move that is not legal on the replayed board prints as its UCI with the word illegal.

### <800

#### Window 1: allowed (length 5, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=1829358&ply=14
- **User rating:** 308 (pinned Maia Elo 600)
- **FEN before the lead-in:** `r1bqkb1r/pp1p1ppp/5n2/1B6/3pP3/3P4/PP3PPP/RNBQK2R w KQkq - 0 8`
- **Lead-in:** 8. O-O
- **Judged user moves:**
  - 8... Bc5 (Good, pre-move ES 0.38), reply 9. e5
- **FEN before the answer move:** `r1bqk2r/pp1p1ppp/5n2/1Bb1P3/3p4/3P4/PP3PPP/RNBQ1RK1 b kq - 0 9`
- **Answer:** blunder 9... Ng4 (pre-move ES 0.32, ES after 0.13).
- **Refutation:** Qxg4.
- **Score inputs:** facepalm score 0.782, played prob 0.230, material loss 3.000, material missed 0.000, reply prob 0.540, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.553, pre-blunder spread 4.18.

#### Window 2: allowed (length 5, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=1669799&ply=17
- **User rating:** 479 (pinned Maia Elo 600)
- **FEN before the lead-in:** `rnb1kbr1/p4Npp/2B2q1B/8/3Pp3/8/PPP2PPP/RN1QK2R b KQq - 0 9`
- **Lead-in:** 9... Nxc6
- **Judged user moves:**
- **FEN before the answer move:** `r1b1kbr1/p4Npp/2n2q1B/8/3Pp3/8/PPP2PPP/RN1QK2R w KQq - 0 10`
- **Answer:** blunder 10. d5 (pre-move ES 0.43, ES after 0.23).
- **Refutation:** gxh6.
- **Score inputs:** facepalm score 0.796, played prob 0.084, material loss 3.452, material missed 0.000, reply prob 0.170, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.013, pre-blunder spread 11.55.

#### Window 3: herring (length 3, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2746846&ply=30
- **User rating:** 711 (pinned Maia Elo 711)
- **FEN before the lead-in:** `2rq1rk1/pp3pbp/2n1b1p1/2ppp3/P5P1/1P2P2P/1BPPNPB1/RN1QK2R w KQ - 5 16`
- **Lead-in:** 16. Bc3
- **Judged user moves:**
  - 16... f5 (Good, pre-move ES 0.39), reply 17. gxf5
  - 17... Bxf5 (Good, pre-move ES 0.37), reply 18. Ng3
  - 18... d4 (Good, pre-move ES 0.40), reply 19. exd4
- **Answer:** all safe (every judged move is Good).

#### Window 4: allowed (length 5, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=1940105&ply=51
- **User rating:** 391 (pinned Maia Elo 600)
- **FEN before the lead-in:** `6k1/pb2N1pp/1p3p2/2p5/2P5/1PKP4/P5rP/5R1R b - - 3 26`
- **Lead-in:** 26... Kf7
- **Judged user moves:**
  - 27. Nd5 (Good, pre-move ES 0.87), reply 27... Rg4
- **FEN before the answer move:** `8/pb3kpp/1p3p2/2pN4/2P3r1/1PKP4/P6P/5R1R w - - 6 28`
- **Answer:** blunder 28. Nf4 (pre-move ES 0.86, ES after 0.30).
- **Refutation:** Bxh1.
- **Score inputs:** facepalm score 0.985, played prob 0.021, material loss 4.516, material missed 0.677, reply prob 0.572, mate ply n/a.
- **Missed inputs:** missed gain 0.677, best move prob 0.155, pre-blunder spread 12.97.

#### Window 5: mixed (length 3, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=3277254&ply=14
- **User rating:** 369 (pinned Maia Elo 600)
- **FEN before the lead-in:** `r1bqk2r/pppp1ppp/5n2/2bPN3/2PnP3/8/PP3PPP/RNBQKB1R w KQkq - 1 8`
- **Lead-in:** 8. Nf3
- **Judged user moves:**
- **FEN before the answer move:** `r1bqk2r/pppp1ppp/5n2/2bP4/2PnP3/5N2/PP3PPP/RNBQKB1R b KQkq - 2 8`
- **Answer:** blunder 8... d6 (pre-move ES 0.41, ES after 0.21).
- **Refutation:** Nxd4.
- **Missed best move:** Nxf3+.
- **Score inputs:** facepalm score 0.891, played prob 0.116, material loss 3.000, material missed 0.000, reply prob 0.925, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.286, pre-blunder spread 5.82.

#### Window 6: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2762517&ply=1
- **User rating:** 759 (pinned Maia Elo 759)
- **FEN before the lead-in:** `rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1`
- **Lead-in:** 1... e5
- **Judged user moves:**
  - 2. Nf3 (Good, pre-move ES 0.52), reply 2... Nc6
  - 3. Bb5 (Good, pre-move ES 0.52), reply 3... Nf6
  - 4. c3 (Good, pre-move ES 0.52), reply 4... a6
  - 5. Ba4 (Good, pre-move ES 0.50), reply 5... b5
  - 6. Bb3 (Good, pre-move ES 0.49), reply 6... d6
- **Answer:** all safe (every judged move is Good).

#### Window 7: allowed (length 3, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=2607591&ply=33
- **User rating:** 581 (pinned Maia Elo 600)
- **FEN before the lead-in:** `r1q2r1k/2p2p1p/p1np2p1/1p4N1/2PNPp2/1B1P3P/PP3PKP/R2Q1R2 b - - 0 17`
- **Lead-in:** 17... Nxd4
- **Judged user moves:**
  - 18. cxb5 (Good, pre-move ES 0.82), reply 18... f3+
  - 19. Kg1 (Good, pre-move ES 0.83), reply 19... f6
- **FEN before the answer move:** `r1q2r1k/2p4p/p2p1pp1/1P4N1/3nP3/1B1P1p1P/PP3P1P/R2Q1RK1 w - - 0 20`
- **Answer:** blunder 20. Nf7+ (pre-move ES 0.83, ES after 0.32).
- **Refutation:** Rxf7.
- **Score inputs:** facepalm score 0.853, played prob 0.171, material loss 3.226, material missed 0.000, reply prob 0.614, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.324, pre-blunder spread 8.70.

#### Window 8: allowed (length 4, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=3161263&ply=23
- **User rating:** 349 (pinned Maia Elo 600)
- **FEN before the lead-in:** `r1bqkb1r/2p1p3/p6p/np1p2pn/3P1P2/1BP2NB1/PP1N1PPP/R2Q1RK1 b kq - 0 12`
- **Lead-in:** 12... gxf4
- **Judged user moves:**
- **FEN before the answer move:** `r1bqkb1r/2p1p3/p6p/np1p3n/3P1p2/1BP2NB1/PP1N1PPP/R2Q1RK1 w kq - 0 13`
- **Answer:** blunder 13. Bxf4 (pre-move ES 0.86, ES after 0.36).
- **Refutation:** Nxf4.
- **Score inputs:** facepalm score 0.728, played prob 0.194, material loss 2.000, material missed 0.484, reply prob 0.787, mate ply n/a.
- **Missed inputs:** missed gain 0.484, best move prob 0.033, pre-blunder spread 3.66.

#### Window 9: mixed (length 3, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=1783017&ply=18
- **User rating:** 795 (pinned Maia Elo 795)
- **FEN before the lead-in:** `r1bq1rk1/ppp2ppp/2n5/b2n4/3P4/2P2N2/PP1Q1PPP/RNB1KB1R w KQ - 1 10`
- **Lead-in:** 10. Bb5
- **Judged user moves:**
  - 10... Re8+ (Good, pre-move ES 0.51), reply 11. Ne5
- **FEN before the answer move:** `r1bqr1k1/ppp2ppp/2n5/bB1nN3/3P4/2P5/PP1Q1PPP/RNB1K2R b KQ - 4 11`
- **Answer:** blunder 11... Nxd4 (pre-move ES 0.77, ES after 0.25).
- **Refutation:** Bxe8.
- **Missed best move:** f6.
- **Score inputs:** facepalm score 0.863, played prob 0.046, material loss 2.516, material missed 1.935, reply prob 0.226, mate ply n/a.
- **Missed inputs:** missed gain 1.935, best move prob 0.209, pre-blunder spread 8.94.

#### Window 10: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2349772&ply=88
- **User rating:** 625 (pinned Maia Elo 625)
- **FEN before the lead-in:** `8/7p/8/8/P1P3rk/1P6/5R2/6K1 w - - 7 45`
- **Lead-in:** 45. Rg2
- **Judged user moves:**
  - 45... Rd4 (Good, pre-move ES 0.15), reply 46. a5
  - 46... Rd3 (Good, pre-move ES 0.17), reply 47. a6
  - 47... Rxb3 (Good, pre-move ES 0.16), reply 48. Kh2
  - 48... Rh3+ (Good, pre-move ES 0.50), reply 49. Kg1
  - 49... Ra3 (Good, pre-move ES 0.50), reply 50. Rh2+
- **Answer:** all safe (every judged move is Good).

#### Window 11: herring (length 4, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2949992&ply=113
- **User rating:** 629 (pinned Maia Elo 629)
- **FEN before the lead-in:** `8/8/7p/1k4p1/1PR5/3K2P1/3B4/3r4 b - - 0 57`
- **Lead-in:** 57... Rxd2+
- **Judged user moves:**
  - 58. Kxd2 (Good, pre-move ES 0.50), reply 58... Kxc4
  - 59. Ke3 (Good, pre-move ES 0.50), reply 59... Kxb4
  - 60. Kf3 (Good, pre-move ES 0.50), reply 60... Kc4
  - 61. Kg4 (Good, pre-move ES 0.50), reply 61... Kd4
- **Answer:** all safe (every judged move is Good).

#### Window 12: allowed (length 4, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=2880547&ply=39
- **User rating:** 295 (pinned Maia Elo 600)
- **FEN before the lead-in:** `r2qr1k1/1b3pb1/3p1npp/p2Pp3/1PN5/1P4P1/2Q1NPBP/R4RK1 b - - 2 20`
- **Lead-in:** 20... Bxd5
- **Judged user moves:**
  - 21. Bxd5 (Good, pre-move ES 0.49), reply 21... Nxd5
- **FEN before the answer move:** `r2qr1k1/5pb1/3p2pp/p2np3/1PN5/1P4P1/2Q1NP1P/R4RK1 w - - 0 22`
- **Answer:** blunder 22. Nxd6 (pre-move ES 0.49, ES after 0.17).
- **Refutation:** Qxd6.
- **Score inputs:** facepalm score 0.839, played prob 0.015, material loss 1.000, material missed 1.000, reply prob 0.843, mate ply n/a.
- **Missed inputs:** missed gain 1.000, best move prob 0.618, pre-blunder spread 5.12.

#### Window 13: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=1870209&ply=8
- **User rating:** 630 (pinned Maia Elo 630)
- **FEN before the lead-in:** `r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/1P6/PBPP1PPP/RN1QK1NR w KQkq - 3 5`
- **Lead-in:** 5. Qe2
- **Judged user moves:**
  - 5... d6 (Good, pre-move ES 0.62), reply 6. b4
  - 6... Bxb4 (Good, pre-move ES 0.69), reply 7. a3
  - 7... Bc5 (Good, pre-move ES 0.68), reply 8. Nf3
  - 8... O-O (Good, pre-move ES 0.67), reply 9. O-O
  - 9... h6 (Good, pre-move ES 0.67), reply 10. Re1
- **Answer:** all safe (every judged move is Good).

#### Window 14: herring (length 3, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=3174377&ply=31
- **User rating:** 730 (pinned Maia Elo 730)
- **FEN before the lead-in:** `r1bk2nr/pp2q2p/1bp2p2/3p3Q/1P5B/1BP5/P2N1PPP/R4RK1 b - - 1 16`
- **Lead-in:** 16... Qg7
- **Judged user moves:**
  - 17. Bxd5 (Good, pre-move ES 0.72), reply 17... cxd5
  - 18. Qxd5+ (Good, pre-move ES 0.71), reply 18... Bd7
  - 19. Qxb7 (Good, pre-move ES 0.76), reply 19... Rc8
- **Answer:** all safe (every judged move is Good).

#### Window 15: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2447139&ply=75
- **User rating:** 621 (pinned Maia Elo 621)
- **FEN before the lead-in:** `k5B1/4b3/8/5p2/1p2b3/8/PK1B4/8 b - - 0 38`
- **Lead-in:** 38... Bd6
- **Judged user moves:**
  - 39. Kb3 (Good, pre-move ES 0.50), reply 39... Kb7
  - 40. Bh7 (Good, pre-move ES 0.50), reply 40... Kb6
  - 41. Be3+ (Good, pre-move ES 0.50), reply 41... Kb5
  - 42. Bg8 (Good, pre-move ES 0.50), reply 42... f4
  - 43. Bf2 (Good, pre-move ES 0.50), reply 43... f3
- **Answer:** all safe (every judged move is Good).

#### Window 16: mixed (length 4, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=2048011&ply=27
- **User rating:** 461 (pinned Maia Elo 600)
- **FEN before the lead-in:** `r2qk2r/pp2n2p/4bp2/2b3p1/3pB3/3P4/PPP2PPP/R1B1QRK1 b kq - 1 14`
- **Lead-in:** 14... Bd5
- **Judged user moves:**
  - 15. Bd2 (Good, pre-move ES 0.25), reply 15... Bxe4
  - 16. Qxe4 (Good, pre-move ES 0.21), reply 16... f5
- **FEN before the answer move:** `r2qk2r/pp2n2p/8/2b2pp1/3pQ3/3P4/PPPB1PPP/R4RK1 w kq - 0 17`
- **Answer:** blunder 17. Bxg5 (pre-move ES 0.68, ES after 0.08).
- **Refutation:** fxe4.
- **Missed best move:** Qe5.
- **Score inputs:** facepalm score 0.988, played prob 0.045, material loss 4.032, material missed 3.452, reply prob 0.487, mate ply n/a.
- **Missed inputs:** missed gain 3.452, best move prob 0.287, pre-blunder spread 8.17.

#### Window 17: mixed (length 3, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=1073524&ply=49
- **User rating:** 720 (pinned Maia Elo 720)
- **FEN before the lead-in:** `6k1/5rbp/1Q4p1/2p1p3/3qP3/rP1P4/P1P2PPP/R4RK1 b - - 0 25`
- **Lead-in:** 25... Qc3
- **Judged user moves:**
  - 26. Qe6 (Good, pre-move ES 0.34), reply 26... Qxc2
  - 27. f4 (Good, pre-move ES 0.29), reply 27... exf4
- **FEN before the answer move:** `6k1/5rbp/4Q1p1/2p5/4Pp2/rP1P4/P1q3PP/R4RK1 w - - 0 28`
- **Answer:** blunder 28. g3 (pre-move ES 0.50, ES after 0.09).
- **Refutation:** Bxa1.
- **Missed best move:** Rxf4.
- **Score inputs:** facepalm score 0.797, played prob 0.064, material loss 2.226, material missed 1.000, reply prob 0.346, mate ply n/a.
- **Missed inputs:** missed gain 1.000, best move prob 0.397, pre-blunder spread 6.87.

#### Window 18: herring (length 4, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=1870081&ply=17
- **User rating:** 704 (pinned Maia Elo 704)
- **FEN before the lead-in:** `r1bqkb1r/p4p1p/2N2np1/8/2Bn4/2N5/PPPP1PPP/R1BQ1RK1 b kq - 0 9`
- **Lead-in:** 9... Qb6
- **Judged user moves:**
  - 10. Nxd4 (Good, pre-move ES 0.87), reply 10... Qxd4
  - 11. Qe2+ (Good, pre-move ES 0.86), reply 11... Be7
  - 12. d3 (Good, pre-move ES 0.85), reply 12... Be6
  - 13. Be3 (Good, pre-move ES 0.87), reply 13... Qg4
- **Answer:** all safe (every judged move is Good).

#### Window 19: allowed (length 5, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=1589702&ply=26
- **User rating:** 300 (pinned Maia Elo 600)
- **FEN before the lead-in:** `rnb5/pppp2kp/8/1N3r2/1b6/6PP/PPP1P2R/R2QKBN1 w Q - 3 14`
- **Lead-in:** 14. Qd2
- **Judged user moves:**
  - 14... Bxd2+ (Good, pre-move ES 0.34), reply 15. Kxd2
  - 15... Rd5+ (Good, pre-move ES 0.34), reply 16. Ke1
- **FEN before the answer move:** `rnb5/pppp2kp/8/1N1r4/8/6PP/PPP1P2R/R3KBN1 b - - 2 16`
- **Answer:** blunder 16... Nc6 (pre-move ES 0.36, ES after 0.08).
- **Refutation:** Nxc7.
- **Score inputs:** facepalm score 0.972, played prob 0.030, material loss 2.935, material missed 3.000, reply prob 0.726, mate ply n/a.
- **Missed inputs:** missed gain 3.000, best move prob 0.660, pre-blunder spread 4.81.

#### Window 20: allowed (length 5, blunder at 5)

- **Game:** https://flawchess.com/analysis?game_id=2096061&ply=20
- **User rating:** 254 (pinned Maia Elo 600)
- **FEN before the lead-in:** `r2q1rk1/p1p1bppp/2p5/2npp3/6b1/2NPBN2/PPP2PPP/R2Q1RK1 w - - 0 11`
- **Lead-in:** 11. d4
- **Judged user moves:**
  - 11... exd4 (Good, pre-move ES 0.73), reply 12. Qxd4
  - 12... Bf5 (Good, pre-move ES 0.77), reply 13. Na4
  - 13... Nxa4 (Good, pre-move ES 0.66), reply 14. Bd2
  - 14... Nc5 (Good, pre-move ES 0.86), reply 15. Bc3
- **FEN before the answer move:** `r2q1rk1/p1p1bppp/2p5/2np1b2/3Q4/2B2N2/PPP2PPP/R4RK1 b - - 3 15`
- **Answer:** blunder 15... Bxc2 (pre-move ES 0.86, ES after 0.02).
- **Refutation:** Qxg7#.
- **Score inputs:** facepalm score 0.981, played prob 0.258, material loss 5.000, material missed 1.484, reply prob 0.887, mate ply 1.
- **Missed inputs:** missed gain 1.484, best move prob 0.150, pre-blunder spread 12.41.

### 800-1199

#### Window 1: mixed (length 3, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=671804&ply=42
- **User rating:** 654 (pinned Maia Elo 1113)
- **FEN before the lead-in:** `3k1b2/N1rn2r1/4Rp2/2p1p3/4b1p1/4B3/PPP1N1PP/5RK1 w - - 1 22`
- **Lead-in:** 22. Nb5
- **Judged user moves:**
  - 22... Rb7 (Good, pre-move ES 0.42), reply 23. c4
- **FEN before the answer move:** `3k1b2/1r1n2r1/4Rp2/1Np1p3/2P1b1p1/4B3/PP2N1PP/5RK1 b - - 0 23`
- **Answer:** blunder 23... Bf5 (pre-move ES 0.56, ES after 0.12).
- **Refutation:** Rxf5.
- **Missed best move:** Bd3.
- **Score inputs:** facepalm score 0.802, played prob 0.096, material loss 2.774, material missed 1.000, reply prob 0.257, mate ply n/a.
- **Missed inputs:** missed gain 1.000, best move prob 0.256, pre-blunder spread 10.83.

#### Window 2: allowed (length 3, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=1076508&ply=37
- **User rating:** 594 (pinned Maia Elo 1072)
- **FEN before the lead-in:** `1n1q1rk1/3b1p2/3p1p1p/2P1p3/4P2B/1B1P4/2PN1PPP/Q3K2R b K - 0 19`
- **Lead-in:** 19... dxc5
- **Judged user moves:**
- **FEN before the answer move:** `1n1q1rk1/3b1p2/5p1p/2p1p3/4P2B/1B1P4/2PN1PPP/Q3K2R w K - 0 20`
- **Answer:** blunder 20. Qa5 (pre-move ES 0.86, ES after 0.15).
- **Refutation:** Qxa5.
- **Score inputs:** facepalm score 0.994, played prob 0.005, material loss 5.000, material missed 0.000, reply prob 0.885, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.489, pre-blunder spread 7.35.

#### Window 3: mixed (length 3, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=474805&ply=56
- **User rating:** 991 (pinned Maia Elo 1173)
- **FEN before the lead-in:** `r3r1k1/3q1pp1/7p/p2p1n2/1p2p1Q1/2P5/PP3PPP/2RN1RK1 w - - 0 29`
- **Lead-in:** 29. Ne3
- **Judged user moves:**
  - 29... Re5 (Good, pre-move ES 0.61), reply 30. cxb4
  - 30... axb4 (Good, pre-move ES 0.65), reply 31. f4
- **FEN before the answer move:** `r5k1/3q1pp1/7p/3prn2/1p2pPQ1/4N3/PP4PP/2R2RK1 b - f3 0 31`
- **Answer:** blunder 31... Nxe3 (pre-move ES 0.77, ES after 0.15).
- **Refutation:** Qxd7.
- **Missed best move:** Qa7.
- **Score inputs:** facepalm score 0.964, played prob 0.298, material loss 5.000, material missed 0.000, reply prob 0.882, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.036, pre-blunder spread 7.38.

#### Window 4: mixed (length 4, blunder at 4)

- **Game:** https://flawchess.com/analysis?game_id=1077344&ply=22
- **User rating:** 728 (pinned Maia Elo 1160)
- **FEN before the lead-in:** `rnb2b1r/ppp2kpp/8/4P3/8/8/PPP2PPP/RN1Q2K1 w - - 0 12`
- **Lead-in:** 12. Qd8
- **Judged user moves:**
  - 12... Nc6 (Good, pre-move ES 0.31), reply 13. Qxc7+
  - 13... Be7 (Good, pre-move ES 0.39), reply 14. Nc3
  - 14... Re8 (Good, pre-move ES 0.37), reply 15. Nd5
- **FEN before the answer move:** `r1b1r3/ppQ1bkpp/2n5/3NP3/8/8/PPP2PPP/R5K1 b - - 4 15`
- **Answer:** blunder 15... Bf5 (pre-move ES 0.50, ES after 0.20).
- **Refutation:** Qxb7.
- **Missed best move:** Kg8.
- **Score inputs:** facepalm score 0.782, played prob 0.034, material loss 1.968, material missed 0.000, reply prob 0.457, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.105, pre-blunder spread 6.91.

#### Window 5: allowed (length 3, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=2035205&ply=25
- **User rating:** 1025 (pinned Maia Elo 1025)
- **FEN before the lead-in:** `r4rk1/ppp1qppp/5n2/1P1pb3/P5b1/NQP2NP1/3BPPBP/R4RK1 b - - 0 13`
- **Lead-in:** 13... Qe6
- **Judged user moves:**
  - 14. Nc2 (Good, pre-move ES 0.85), reply 14... Bxf3
  - 15. exf3 (Good, pre-move ES 0.87), reply 15... d4
- **FEN before the answer move:** `r4rk1/ppp2ppp/4qn2/1P2b3/P2p4/1QP2PP1/2NB1PBP/R4RK1 w - - 0 16`
- **Answer:** blunder 16. cxd4 (pre-move ES 0.88, ES after 0.22).
- **Refutation:** Qxb3.
- **Score inputs:** facepalm score 0.978, played prob 0.226, material loss 5.000, material missed 1.000, reply prob 0.843, mate ply n/a.
- **Missed inputs:** missed gain 1.000, best move prob 0.558, pre-blunder spread 4.28.

#### Window 6: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2833187&ply=15
- **User rating:** 533 (pinned Maia Elo 1045)
- **FEN before the lead-in:** `r1bqk2r/pp1p1ppp/2N2n2/2b5/2P5/2N5/PP3PPP/R1BQKB1R b KQkq - 0 8`
- **Lead-in:** 8... bxc6
- **Judged user moves:**
  - 9. Qe2+ (Good, pre-move ES 0.51), reply 9... Qe7
  - 10. Qxe7+ (Good, pre-move ES 0.53), reply 10... Bxe7
  - 11. Be3 (Good, pre-move ES 0.52), reply 11... O-O
  - 12. Bd3 (Good, pre-move ES 0.51), reply 12... Ba6
  - 13. b3 (Good, pre-move ES 0.52), reply 13... Rfe8
- **Answer:** all safe (every judged move is Good).

#### Window 7: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2832682&ply=11
- **User rating:** 984 (pinned Maia Elo 1169)
- **FEN before the lead-in:** `rn1qk1nr/ppp2ppp/3p4/2b1p3/2P5/2N1PB2/PP1P1PPP/R1BQK2R b KQkq - 0 6`
- **Lead-in:** 6... c6
- **Judged user moves:**
  - 7. d4 (Good, pre-move ES 0.62), reply 7... exd4
  - 8. exd4 (Good, pre-move ES 0.66), reply 8... Bb4
  - 9. Bd2 (Good, pre-move ES 0.68), reply 9... Ne7
  - 10. a3 (Good, pre-move ES 0.64), reply 10... Bxc3
  - 11. Bxc3 (Good, pre-move ES 0.62), reply 11... O-O
- **Answer:** all safe (every judged move is Good).

#### Window 8: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2863850&ply=42
- **User rating:** 678 (pinned Maia Elo 1130)
- **FEN before the lead-in:** `4r3/pb3kp1/1ppp4/1N5p/3PP2b/3K3P/PPP5/R1B5 w - - 0 22`
- **Lead-in:** 22. Nxd6+
- **Judged user moves:**
  - 22... Kf8 (Good, pre-move ES 0.15), reply 23. Nxe8
  - 23... Kxe8 (Good, pre-move ES 0.17), reply 24. Bf4
  - 24... Ba6+ (Good, pre-move ES 0.18), reply 25. Kc3
  - 25... Bf2 (Good, pre-move ES 0.19), reply 26. b3
  - 26... c5 (Good, pre-move ES 0.18), reply 27. dxc5
- **Answer:** all safe (every judged move is Good).

#### Window 9: herring (length 4, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2865027&ply=21
- **User rating:** 945 (pinned Maia Elo 1145)
- **FEN before the lead-in:** `rnb1k1nr/1p2qppp/pbp5/3pP3/B7/2P2P2/PP1NQ1PP/R1B1K2R b KQkq - 2 11`
- **Lead-in:** 11... f6
- **Judged user moves:**
  - 12. f4 (Good, pre-move ES 0.18), reply 12... fxe5
  - 13. fxe5 (Good, pre-move ES 0.15), reply 13... Nh6
  - 14. Qh5+ (Good, pre-move ES 0.20), reply 14... Nf7
  - 15. Nf3 (Good, pre-move ES 0.17), reply 15... g6
- **Answer:** all safe (every judged move is Good).

#### Window 10: mixed (length 3, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=563198&ply=31
- **User rating:** 467 (pinned Maia Elo 1042)
- **FEN before the lead-in:** `2kr3r/ppp2ppp/5n2/4pP2/1b2P3/1PPPqP2/PB5P/RK1Q1B1R b - - 0 16`
- **Lead-in:** 16... Rxd3
- **Judged user moves:**
- **FEN before the answer move:** `2k4r/ppp2ppp/5n2/4pP2/1b2P3/1PPrqP2/PB5P/RK1Q1B1R w - - 0 17`
- **Answer:** blunder 17. cxb4 (pre-move ES 0.89, ES after 0.02).
- **Refutation:** Rxd1+.
- **Missed best move:** Qxd3.
- **Score inputs:** facepalm score 0.999, played prob 0.018, material loss 5.000, material missed 5.000, reply prob 0.977, mate ply 3.
- **Missed inputs:** missed gain 5.000, best move prob 0.110, pre-blunder spread 2.08.

#### Window 11: allowed (length 3, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=2688485&ply=28
- **User rating:** 500 (pinned Maia Elo 1030)
- **FEN before the lead-in:** `r4rk1/pbpp1ppp/1p6/3Pp1q1/8/P1PP3P/1P2nPP1/R2Q1RK1 w - - 0 15`
- **Lead-in:** 15. Qxe2
- **Judged user moves:**
  - 15... Bxd5 (Good, pre-move ES 0.87), reply 16. g3
  - 16... Rae8 (Good, pre-move ES 0.89), reply 17. h4
- **FEN before the answer move:** `4rrk1/p1pp1ppp/1p6/3bp1q1/7P/P1PP2P1/1P2QP2/R4RK1 b - - 0 17`
- **Answer:** blunder 17... Qg4 (pre-move ES 0.89, ES after 0.19).
- **Refutation:** Qxg4.
- **Score inputs:** facepalm score 0.995, played prob 0.015, material loss 5.000, material missed 1.129, reply prob 0.930, mate ply n/a.
- **Missed inputs:** missed gain 1.129, best move prob 0.234, pre-blunder spread 4.65.

#### Window 12: mixed (length 4, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=3172805&ply=37
- **User rating:** 1007 (pinned Maia Elo 1071)
- **FEN before the lead-in:** `N4rk1/2q1pp1p/n5p1/2p1b3/p1P5/3B1Q1P/PP3PP1/R4RK1 b - - 0 19`
- **Lead-in:** 19... Rxa8
- **Judged user moves:**
- **FEN before the answer move:** `r5k1/2q1pp1p/n5p1/2p1b3/p1P5/3B1Q1P/PP3PP1/R4RK1 w - - 0 20`
- **Answer:** blunder 20. a3 (pre-move ES 0.88, ES after 0.61).
- **Refutation:** Ra7.
- **Missed best move:** Qxa8+.
- **Score inputs:** facepalm score 0.812, played prob 0.027, material loss 0.000, material missed 4.968, reply prob 0.007, mate ply n/a.
- **Missed inputs:** missed gain 4.968, best move prob 0.501, pre-blunder spread 6.09.

#### Window 13: allowed (length 3, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=2955916&ply=90
- **User rating:** 786 (pinned Maia Elo 1192)
- **FEN before the lead-in:** `8/1p5k/p7/6p1/P2n1p2/1K5P/1P1r2P1/6R1 w - - 1 46`
- **Lead-in:** 46. Kc3
- **Judged user moves:**
- **FEN before the answer move:** `8/1p5k/p7/6p1/P2n1p2/2K4P/1P1r2P1/6R1 b - - 2 46`
- **Answer:** blunder 46... Re2 (pre-move ES 0.87, ES after 0.69).
- **Refutation:** Kxd4.
- **Score inputs:** facepalm score 0.820, played prob 0.064, material loss 1.968, material missed 0.000, reply prob 0.925, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.674, pre-blunder spread 3.69.

#### Window 14: allowed (length 5, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=973316&ply=84
- **User rating:** 757 (pinned Maia Elo 1040)
- **FEN before the lead-in:** `8/pkp5/2p5/1p1n2P1/5r2/P4K2/1B6/4R3 w - - 0 43`
- **Lead-in:** 43. Kg3
- **Judged user moves:**
  - 43... Rf5 (Good, pre-move ES 0.52), reply 44. Kg4
  - 44... Rf7 (Good, pre-move ES 0.51), reply 45. g6
- **FEN before the answer move:** `8/pkp2r2/2p3P1/1p1n4/6K1/P7/1B6/4R3 b - - 0 45`
- **Answer:** blunder 45... Rg7 (pre-move ES 0.50, ES after 0.06).
- **Refutation:** Bxg7.
- **Score inputs:** facepalm score 0.968, played prob 0.191, material loss 5.000, material missed 0.290, reply prob 0.647, mate ply n/a.
- **Missed inputs:** missed gain 0.290, best move prob 0.055, pre-blunder spread 6.72.

#### Window 15: herring (length 4, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2997085&ply=11
- **User rating:** 771 (pinned Maia Elo 1046)
- **FEN before the lead-in:** `r1bqkb1r/pp3ppp/2np3n/2p1P1N1/4P3/2N5/PPP2PPP/R1BQKB1R b KQkq - 3 6`
- **Lead-in:** 6... Qe7
- **Judged user moves:**
  - 7. Nd5 (Good, pre-move ES 0.73), reply 7... Qxe5
  - 8. Bb5 (Good, pre-move ES 0.78), reply 8... a6
  - 9. Be2 (Good, pre-move ES 0.83), reply 9... f6
  - 10. Nc7+ (Good, pre-move ES 0.82), reply 10... Kd7
- **Answer:** all safe (every judged move is Good).

#### Window 16: herring (length 3, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2795940&ply=76
- **User rating:** 899 (pinned Maia Elo 1116)
- **FEN before the lead-in:** `8/8/2k2p2/4p2R/1Bp5/8/5KPP/3r4 w - - 1 39`
- **Lead-in:** 39. Rh6
- **Judged user moves:**
  - 39... Kd5 (Good, pre-move ES 0.20), reply 40. Rxf6
  - 40... Ke4 (Good, pre-move ES 0.18), reply 41. Rc6
  - 41... Rd4 (Good, pre-move ES 0.19), reply 42. h4
- **Answer:** all safe (every judged move is Good).

#### Window 17: herring (length 4, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2546653&ply=1
- **User rating:** 1159 (pinned Maia Elo 1159)
- **FEN before the lead-in:** `rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1`
- **Lead-in:** 1... e5
- **Judged user moves:**
  - 2. d4 (Good, pre-move ES 0.53), reply 2... exd4
  - 3. c3 (Good, pre-move ES 0.49), reply 3... c5
  - 4. cxd4 (Good, pre-move ES 0.51), reply 4... cxd4
  - 5. Qxd4 (Good, pre-move ES 0.50), reply 5... Nc6
- **Answer:** all safe (every judged move is Good).

#### Window 18: allowed (length 3, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=1309688&ply=9
- **User rating:** 661 (pinned Maia Elo 1118)
- **FEN before the lead-in:** `r1bqkb1r/ppp2ppp/2np1n2/4p3/3P4/1P2P1P1/P1P2PBP/RNBQK1NR b KQkq - 0 5`
- **Lead-in:** 5... exd4
- **Judged user moves:**
  - 6. exd4 (Good, pre-move ES 0.50), reply 6... d5
  - 7. Nc3 (Good, pre-move ES 0.49), reply 7... Bb4
- **FEN before the answer move:** `r1bqk2r/ppp2ppp/2n2n2/3p4/1b1P4/1PN3P1/P1P2PBP/R1BQK1NR w KQkq - 2 8`
- **Answer:** blunder 8. a3 (pre-move ES 0.47, ES after 0.12).
- **Refutation:** Bxc3+.
- **Score inputs:** facepalm score 0.970, played prob 0.015, material loss 3.452, material missed 0.000, reply prob 0.902, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.067, pre-blunder spread 3.19.

#### Window 19: allowed (length 4, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=2696072&ply=48
- **User rating:** 1354 (pinned Maia Elo 1158)
- **FEN before the lead-in:** `5r1k/pr1nn1pp/2q5/5pP1/2BP1P1P/P3B3/8/R2QR1K1 w - - 3 25`
- **Lead-in:** 25. Rc1
- **Judged user moves:**
- **FEN before the answer move:** `5r1k/pr1nn1pp/2q5/5pP1/2BP1P1P/P3B3/8/2RQR1K1 b - - 4 25`
- **Answer:** blunder 25... Qh6 (pre-move ES 0.34, ES after 0.06).
- **Refutation:** unknown.
- **Score inputs:** facepalm score 0.995, played prob 0.002, material loss 5.000, material missed 0.032, reply prob 0.754, mate ply n/a.
- **Missed inputs:** missed gain 0.032, best move prob 0.080, pre-blunder spread 14.86.

#### Window 20: allowed (length 3, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=2044464&ply=6
- **User rating:** 1283 (pinned Maia Elo 1088)
- **FEN before the lead-in:** `r1bqk1nr/pppp1ppp/2n5/2b1p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4`
- **Lead-in:** 4. c3
- **Judged user moves:**
  - 4... d6 (Good, pre-move ES 0.49), reply 5. d4
  - 5... exd4 (Good, pre-move ES 0.46), reply 6. cxd4
- **FEN before the answer move:** `r1bqk1nr/ppp2ppp/2np4/2b5/2BPP3/5N2/PP3PPP/RNBQK2R b KQkq - 0 6`
- **Answer:** blunder 6... Nxd4 (pre-move ES 0.46, ES after 0.22).
- **Refutation:** Nxd4.
- **Score inputs:** facepalm score 0.856, played prob 0.044, material loss 2.000, material missed 0.000, reply prob 0.972, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.457, pre-blunder spread 3.21.

### 1200-1599

#### Window 1: allowed (length 5, blunder at 5)

- **Game:** https://flawchess.com/analysis?game_id=3251407&ply=1
- **User rating:** 1399 (pinned Maia Elo 1399)
- **FEN before the lead-in:** `rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1`
- **Lead-in:** 1... d5
- **Judged user moves:**
  - 2. exd5 (Good, pre-move ES 0.57), reply 2... c6
  - 3. dxc6 (Good, pre-move ES 0.58), reply 3... Nxc6
  - 4. Nc3 (Good, pre-move ES 0.59), reply 4... e5
  - 5. Nf3 (Good, pre-move ES 0.59), reply 5... Bf5
- **FEN before the answer move:** `r2qkbnr/pp3ppp/2n5/4pb2/8/2N2N2/PPPP1PPP/R1BQKB1R w KQkq - 2 6`
- **Answer:** blunder 6. d4 (pre-move ES 0.68, ES after 0.49).
- **Refutation:** exd4.
- **Score inputs:** facepalm score 0.762, played prob 0.011, material loss 0.968, material missed 0.000, reply prob 0.678, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.583, pre-blunder spread 4.00.

#### Window 2: allowed (length 3, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=2213755&ply=14
- **User rating:** 1109 (pinned Maia Elo 1484)
- **FEN before the lead-in:** `rn2kb1r/pp3ppp/1qp1pn2/3p4/3P1Bb1/2P1PN2/PP2BPPP/RNQ1K2R w KQkq - 0 8`
- **Lead-in:** 8. Ne5
- **Judged user moves:**
- **FEN before the answer move:** `rn2kb1r/pp3ppp/1qp1pn2/3pN3/3P1Bb1/2P1P3/PP2BPPP/RNQ1K2R b KQkq - 1 8`
- **Answer:** blunder 8... Nbd7 (pre-move ES 0.54, ES after 0.23).
- **Refutation:** Nxg4.
- **Score inputs:** facepalm score 0.933, played prob 0.014, material loss 3.000, material missed 0.000, reply prob 0.499, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.830, pre-blunder spread 1.85.

#### Window 3: herring (length 3, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=1327435&ply=7
- **User rating:** 1507 (pinned Maia Elo 1507)
- **FEN before the lead-in:** `rnbqk1nr/ppp1ppbp/6p1/3p4/3P4/5NP1/PPP1PPBP/RNBQK2R b KQkq - 3 4`
- **Lead-in:** 4... Nf6
- **Judged user moves:**
  - 5. O-O (Good, pre-move ES 0.53), reply 5... Nc6
  - 6. Bf4 (Good, pre-move ES 0.54), reply 6... Bg4
  - 7. h3 (Good, pre-move ES 0.54), reply 7... Bf5
- **Answer:** all safe (every judged move is Good).

#### Window 4: pure_miss (length 4, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=2675776&ply=23
- **User rating:** 1149 (pinned Maia Elo 1351)
- **FEN before the lead-in:** `2k4r/ppp2ppp/2nr4/4p2q/3P2b1/5N1P/PPP2PP1/R1BQR1K1 b - - 0 12`
- **Lead-in:** 12... Rxd4
- **Judged user moves:**
- **FEN before the answer move:** `2k4r/ppp2ppp/2n5/4p2q/3r2b1/5N1P/PPP2PP1/R1BQR1K1 w - - 0 13`
- **Answer:** blunder 13. Bd2 (pre-move ES 0.75, ES after 0.10).
- **Missed best move:** hxg4.
- **Score inputs:** facepalm score 0.952, played prob 0.096, material loss 3.097, material missed 2.000, reply prob 0.811, mate ply n/a.
- **Missed inputs:** missed gain 2.000, best move prob 0.380, pre-blunder spread 3.17.

#### Window 5: herring (length 3, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2669453&ply=12
- **User rating:** 1422 (pinned Maia Elo 1422)
- **FEN before the lead-in:** `r1bqkb1r/p2p1ppp/2p1pn2/8/2B1P3/8/PPP2PPP/RNBQK2R w KQkq - 0 7`
- **Lead-in:** 7. e5
- **Judged user moves:**
  - 7... Qa5+ (Good, pre-move ES 0.67), reply 8. Nc3
  - 8... Qxe5+ (Good, pre-move ES 0.68), reply 9. Qe2
  - 9... Qxe2+ (Good, pre-move ES 0.69), reply 10. Bxe2
- **Answer:** all safe (every judged move is Good).

#### Window 6: herring (length 3, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2681185&ply=25
- **User rating:** 1261 (pinned Maia Elo 1261)
- **FEN before the lead-in:** `r2k3r/pB1b1ppp/4p3/2b1n3/8/4P3/PPP1NKPP/RN1R4 b - - 0 13`
- **Lead-in:** 13... Rb8
- **Judged user moves:**
  - 14. Bf3 (Good, pre-move ES 0.23), reply 14... Rxb2
  - 15. Nbc3 (Good, pre-move ES 0.20), reply 15... Rxc2
  - 16. Be4 (Good, pre-move ES 0.42), reply 16... Rb2
- **Answer:** all safe (every judged move is Good).

#### Window 7: mixed (length 4, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=2494682&ply=12
- **User rating:** 1192 (pinned Maia Elo 1388)
- **FEN before the lead-in:** `rnbqk2r/1pp2ppp/p3pn2/8/1b1PP3/2N2N2/PPP3PP/R1BQKB1R w KQkq - 2 7`
- **Lead-in:** 7. Bd2
- **Judged user moves:**
- **FEN before the answer move:** `rnbqk2r/1pp2ppp/p3pn2/8/1b1PP3/2N2N2/PPPB2PP/R2QKB1R b KQkq - 3 7`
- **Answer:** blunder 7... Nxe4 (pre-move ES 0.51, ES after 0.18).
- **Refutation:** Nxe4.
- **Missed best move:** Bxc3.
- **Score inputs:** facepalm score 0.936, played prob 0.015, material loss 2.032, material missed 1.000, reply prob 0.960, mate ply n/a.
- **Missed inputs:** missed gain 1.000, best move prob 0.638, pre-blunder spread 3.61.

#### Window 8: mixed (length 4, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=2494680&ply=14
- **User rating:** 1209 (pinned Maia Elo 1402)
- **FEN before the lead-in:** `rnbqk2r/2p2ppp/p3pn2/1P6/1bpPP3/2N2N2/1P3PPP/R1BQKB1R w KQkq - 1 8`
- **Lead-in:** 8. Bxc4
- **Judged user moves:**
  - 8... Nxe4 (Good, pre-move ES 0.33), reply 9. Bd2
- **FEN before the answer move:** `rnbqk2r/2p2ppp/p3p3/1P6/1bBPn3/2N2N2/1P1B1PPP/R2QK2R b KQkq - 1 9`
- **Answer:** blunder 9... c6 (pre-move ES 0.50, ES after 0.15).
- **Refutation:** Nxe4.
- **Missed best move:** Nxd2.
- **Score inputs:** facepalm score 0.915, played prob 0.005, material loss 2.000, material missed 0.000, reply prob 0.752, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.400, pre-blunder spread 6.26.

#### Window 9: allowed (length 3, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=2990616&ply=54
- **User rating:** 1255 (pinned Maia Elo 1435)
- **FEN before the lead-in:** `2kr4/p1p4Q/1p1p2p1/8/4PR2/8/q5PP/4R2K w - - 0 28`
- **Lead-in:** 28. Qxg6
- **Judged user moves:**
  - 28... Kb7 (Good, pre-move ES 0.15), reply 29. Qf6
  - 29... Qd2 (Good, pre-move ES 0.15), reply 30. Ra1
- **FEN before the answer move:** `3r4/pkp5/1p1p1Q2/8/4PR2/8/3q2PP/R6K b - - 4 30`
- **Answer:** blunder 30... Qc3 (pre-move ES 0.16, ES after 0.02).
- **Refutation:** Qxc3.
- **Score inputs:** facepalm score 0.991, played prob 0.019, material loss 5.000, material missed 0.000, reply prob 0.798, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.103, pre-blunder spread 6.41.

#### Window 10: pure_miss (length 4, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=2965817&ply=38
- **User rating:** 833 (pinned Maia Elo 1245)
- **FEN before the lead-in:** `r1bk3r/pp3p1B/2p3p1/3pN3/3P1P2/8/1P4PP/4R1K1 w - - 1 20`
- **Lead-in:** 20. Bxg6
- **Judged user moves:**
- **FEN before the answer move:** `r1bk3r/pp3p2/2p3B1/3pN3/3P1P2/8/1P4PP/4R1K1 b - - 0 20`
- **Answer:** blunder 20... Rg8 (pre-move ES 0.47, ES after 0.30).
- **Missed best move:** fxg6.
- **Score inputs:** facepalm score 0.804, played prob 0.021, material loss 0.903, material missed 1.548, reply prob 0.371, mate ply n/a.
- **Missed inputs:** missed gain 1.548, best move prob 0.722, pre-blunder spread 3.21.

#### Window 11: allowed (length 4, blunder at 4)

- **Game:** https://flawchess.com/analysis?game_id=2741971&ply=119
- **User rating:** 1341 (pinned Maia Elo 1498)
- **FEN before the lead-in:** `6r1/8/2B5/3Pk1PK/8/8/8/8 b - - 4 60`
- **Lead-in:** 60... Rg7
- **Judged user moves:**
  - 61. g6 (Good, pre-move ES 0.50), reply 61... Kf6
  - 62. d6 (Good, pre-move ES 0.50), reply 62... Rxg6
  - 63. d7 (Good, pre-move ES 0.48), reply 63... Rg8
- **FEN before the answer move:** `6r1/3P4/2B2k2/7K/8/8/8/8 w - - 1 64`
- **Answer:** blunder 64. Kh6 (pre-move ES 0.50, ES after 0.02).
- **Refutation:** Rh8#.
- **Score inputs:** facepalm score 0.957, played prob 0.337, material loss 5.000, material missed 0.000, reply prob 0.772, mate ply 1.
- **Missed inputs:** missed gain 0.000, best move prob 0.061, pre-blunder spread 5.33.

#### Window 12: mixed (length 3, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=1994983&ply=8
- **User rating:** 1134 (pinned Maia Elo 1338)
- **FEN before the lead-in:** `rn1qkb1r/ppp1pppp/8/3n1b2/3P4/5N2/PP2PPPP/RNBQKB1R w KQkq - 2 5`
- **Lead-in:** 5. Nc3
- **Judged user moves:**
  - 5... c6 (Good, pre-move ES 0.45), reply 6. e4
- **FEN before the answer move:** `rn1qkb1r/pp2pppp/2p5/3n1b2/3PP3/2N2N2/PP3PPP/R1BQKB1R b KQkq - 0 6`
- **Answer:** blunder 6... Nb4 (pre-move ES 0.54, ES after 0.11).
- **Refutation:** exf5.
- **Missed best move:** Nxc3.
- **Score inputs:** facepalm score 0.987, played prob 0.000, material loss 3.000, material missed 1.677, reply prob 0.971, mate ply n/a.
- **Missed inputs:** missed gain 1.677, best move prob 0.935, pre-blunder spread 1.40.

#### Window 13: allowed (length 5, blunder at 5)

- **Game:** https://flawchess.com/analysis?game_id=1312273&ply=32
- **User rating:** 992 (pinned Maia Elo 1413)
- **FEN before the lead-in:** `2kr3r/ppp3bp/4p1pn/5p2/6n1/1BN3P1/PP2qP1P/R1B1R1K1 w - - 0 17`
- **Lead-in:** 17. Rxe2
- **Judged user moves:**
  - 17... e5 (Good, pre-move ES 0.50), reply 18. h3
  - 18... Nf6 (Good, pre-move ES 0.50), reply 19. Rxe5
  - 19... Nd7 (Good, pre-move ES 0.50), reply 20. Re7
  - 20... Bxc3 (Good, pre-move ES 0.47), reply 21. bxc3
- **FEN before the answer move:** `2kr3r/pppnR2p/6pn/5p2/8/1BP3PP/P4P2/R1B3K1 b - - 0 21`
- **Answer:** blunder 21... Nc5 (pre-move ES 0.47, ES after 0.16).
- **Refutation:** Bxh6.
- **Score inputs:** facepalm score 0.817, played prob 0.249, material loss 3.000, material missed 0.000, reply prob 0.757, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.487, pre-blunder spread 4.74.

#### Window 14: herring (length 3, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2553079&ply=20
- **User rating:** 1024 (pinned Maia Elo 1433)
- **FEN before the lead-in:** `r1bqk1nr/4ppbp/p1n3p1/2p5/4P3/P1PQ1N2/5PPP/RNB2RK1 w kq - 0 11`
- **Lead-in:** 11. Qxd8+
- **Judged user moves:**
  - 11... Nxd8 (Good, pre-move ES 0.83), reply 12. Be3
  - 12... Nb7 (Good, pre-move ES 0.84), reply 13. e5
  - 13... f6 (Good, pre-move ES 0.82), reply 14. Nbd2
- **Answer:** all safe (every judged move is Good).

#### Window 15: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=822440&ply=0
- **User rating:** 1392 (pinned Maia Elo 1552)
- **FEN before the lead-in:** `rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1`
- **Lead-in:** 1. e4
- **Judged user moves:**
  - 1... c6 (Good, pre-move ES 0.47), reply 2. Nf3
  - 2... d5 (Good, pre-move ES 0.48), reply 3. exd5
  - 3... cxd5 (Good, pre-move ES 0.48), reply 4. d4
  - 4... Nc6 (Good, pre-move ES 0.48), reply 5. Bb5
  - 5... a6 (Good, pre-move ES 0.48), reply 6. Bxc6+
- **Answer:** all safe (every judged move is Good).

#### Window 16: allowed (length 4, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=1564089&ply=39
- **User rating:** 1191 (pinned Maia Elo 1387)
- **FEN before the lead-in:** `3r1rk1/p5pp/1p1b1p2/4P3/2P5/1P3P1P/P2B1P2/R4RK1 b - - 0 20`
- **Lead-in:** 20... Bxe5
- **Judged user moves:**
- **FEN before the answer move:** `3r1rk1/p5pp/1p3p2/4b3/2P5/1P3P1P/P2B1P2/R4RK1 w - - 0 21`
- **Answer:** blunder 21. Rae1 (pre-move ES 0.60, ES after 0.15).
- **Refutation:** Rxd2.
- **Score inputs:** facepalm score 0.958, played prob 0.014, material loss 3.000, material missed 0.000, reply prob 0.949, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.615, pre-blunder spread 3.39.

#### Window 17: herring (length 3, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2053296&ply=1
- **User rating:** 1044 (pinned Maia Elo 1444)
- **FEN before the lead-in:** `rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1`
- **Lead-in:** 1... c6
- **Judged user moves:**
  - 2. d4 (Good, pre-move ES 0.53), reply 2... d5
  - 3. Nc3 (Good, pre-move ES 0.52), reply 3... e6
  - 4. Nf3 (Good, pre-move ES 0.57), reply 4... Nf6
- **Answer:** all safe (every judged move is Good).

#### Window 18: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=1668576&ply=52
- **User rating:** 1038 (pinned Maia Elo 1204)
- **FEN before the lead-in:** `6k1/p4pp1/4p2p/2p5/1rP1B3/7P/P2R1PP1/6K1 w - - 3 27`
- **Lead-in:** 27. Rc2
- **Judged user moves:**
  - 27... Kf8 (Good, pre-move ES 0.23), reply 28. Rc1
  - 28... Rb2 (Good, pre-move ES 0.24), reply 29. Bb1
  - 29... Ke7 (Good, pre-move ES 0.30), reply 30. a4
  - 30... Rb4 (Good, pre-move ES 0.30), reply 31. Bc2
  - 31... Kd6 (Good, pre-move ES 0.31), reply 32. Bd1
- **Answer:** all safe (every judged move is Good).

#### Window 19: allowed (length 4, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=1216822&ply=74
- **User rating:** 1213 (pinned Maia Elo 1575)
- **FEN before the lead-in:** `8/1p3p2/3P1N2/p1pK2kP/b7/P7/8/8 w - - 2 38`
- **Lead-in:** 38. Ne4+
- **Judged user moves:**
  - 38... Kxh5 (Good, pre-move ES 0.32), reply 39. Nxc5
- **FEN before the answer move:** `8/1p3p2/3P4/p1NK3k/b7/P7/8/8 b - - 0 39`
- **Answer:** blunder 39... Kg6 (pre-move ES 0.35, ES after 0.06).
- **Refutation:** Nxa4.
- **Score inputs:** facepalm score 0.955, played prob 0.011, material loss 3.000, material missed 0.000, reply prob 0.750, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.730, pre-blunder spread 3.08.

#### Window 20: herring (length 4, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2955440&ply=1
- **User rating:** 842 (pinned Maia Elo 1257)
- **FEN before the lead-in:** `rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1`
- **Lead-in:** 1... c6
- **Judged user moves:**
  - 2. d4 (Good, pre-move ES 0.53), reply 2... d5
  - 3. exd5 (Good, pre-move ES 0.52), reply 3... cxd5
  - 4. Nf3 (Good, pre-move ES 0.53), reply 4... Nc6
  - 5. Be2 (Good, pre-move ES 0.53), reply 5... Bf5
- **Answer:** all safe (every judged move is Good).

### 1600-1999

#### Window 1: allowed (length 5, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=2317131&ply=38
- **User rating:** 1461 (pinned Maia Elo 1821)
- **FEN before the lead-in:** `r4rk1/bb1p1pp1/p6p/3P4/2p3Q1/2q5/P1B2PPP/R4RK1 w - - 0 20`
- **Lead-in:** 20. Qxd7
- **Judged user moves:**
  - 20... Rab8 (Good, pre-move ES 0.85), reply 21. Rac1
  - 21... Qf6 (Good, pre-move ES 0.85), reply 22. d6
- **FEN before the answer move:** `1r3rk1/bb1Q1pp1/p2P1q1p/8/2p5/8/P1B2PPP/2R2RK1 b - - 0 22`
- **Answer:** blunder 22... Qg6 (pre-move ES 0.86, ES after 0.15).
- **Refutation:** Bxg6.
- **Score inputs:** facepalm score 0.995, played prob 0.005, material loss 5.000, material missed 0.000, reply prob 0.953, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.486, pre-blunder spread 3.90.

#### Window 2: allowed (length 5, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=1426155&ply=33
- **User rating:** 1330 (pinned Maia Elo 1656)
- **FEN before the lead-in:** `3rk2r/2p3p1/p1pbN3/4pp1p/6n1/4B3/PPP2PPP/R3R1K1 b k - 3 17`
- **Lead-in:** 17... Rd7
- **Judged user moves:**
- **FEN before the answer move:** `4k2r/2pr2p1/p1pbN3/4pp1p/6n1/4B3/PPP2PPP/R3R1K1 w k - 4 18`
- **Answer:** blunder 18. Bg5 (pre-move ES 0.43, ES after 0.16).
- **Refutation:** Kf7.
- **Score inputs:** facepalm score 0.720, played prob 0.215, material loss 2.000, material missed 1.000, reply prob 0.624, mate ply n/a.
- **Missed inputs:** missed gain 1.000, best move prob 0.058, pre-blunder spread 9.38.

#### Window 3: herring (length 3, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2116131&ply=16
- **User rating:** 1823 (pinned Maia Elo 1986)
- **FEN before the lead-in:** `r1bqk2r/p3bppp/1pn1pn2/2Pp4/1P1P4/2N2N2/P4PPP/R1BQKB1R w KQkq - 1 9`
- **Lead-in:** 9. b5
- **Judged user moves:**
  - 9... Na5 (Good, pre-move ES 0.38), reply 10. c6
  - 10... Bb4 (Good, pre-move ES 0.38), reply 11. Bb2
  - 11... Ne4 (Good, pre-move ES 0.37), reply 12. Qc2
- **Answer:** all safe (every judged move is Good).

#### Window 4: mixed (length 4, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=2309700&ply=29
- **User rating:** 1636 (pinned Maia Elo 1927)
- **FEN before the lead-in:** `nr1q1rk1/1p2ppbp/3p1np1/1PpP4/P3P3/2N1BQ1P/4BPP1/R3K2R b KQ - 0 15`
- **Lead-in:** 15... Nd7
- **Judged user moves:**
- **FEN before the answer move:** `nr1q1rk1/1p1nppbp/3p2p1/1PpP4/P3P3/2N1BQ1P/4BPP1/R3K2R w KQ - 1 16`
- **Answer:** blunder 16. a5 (pre-move ES 0.54, ES after 0.12).
- **Refutation:** Bxc3+.
- **Missed best move:** Bd2.
- **Score inputs:** facepalm score 0.962, played prob 0.022, material loss 3.452, material missed 0.000, reply prob 0.791, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.263, pre-blunder spread 4.88.

#### Window 5: allowed (length 4, blunder at 4)

- **Game:** https://flawchess.com/analysis?game_id=2594367&ply=40
- **User rating:** 1648 (pinned Maia Elo 1774)
- **FEN before the lead-in:** `r4rk1/2q2pb1/1p1p2pp/pPpPp2n/1nP1P3/1P3NBP/5PP1/R2QRBK1 w - - 7 21`
- **Lead-in:** 21. Bh2
- **Judged user moves:**
  - 21... f5 (Good, pre-move ES 0.52), reply 22. Ra4
  - 22... Qf7 (Good, pre-move ES 0.60), reply 23. exf5
  - 23... gxf5 (Good, pre-move ES 0.60), reply 24. Be2
- **FEN before the answer move:** `r4rk1/5qb1/1p1p3p/pPpPpp1n/RnP5/1P3N1P/4BPPB/3QR1K1 b - - 1 24`
- **Answer:** blunder 24... Rae8 (pre-move ES 0.55, ES after 0.35).
- **Refutation:** Nxe5.
- **Score inputs:** facepalm score 0.846, played prob 0.065, material loss 3.000, material missed 0.194, reply prob 0.338, mate ply n/a.
- **Missed inputs:** missed gain 0.194, best move prob 0.295, pre-blunder spread 7.22.

#### Window 6: herring (length 4, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=3231472&ply=24
- **User rating:** 1654 (pinned Maia Elo 1654)
- **FEN before the lead-in:** `r2q1rk1/1pp2ppp/3p1nb1/p1nPp3/2P1P3/5N1P/PPBN1PP1/R3QRK1 w - - 5 13`
- **Lead-in:** 13. Nh2
- **Judged user moves:**
  - 13... Nh5 (Good, pre-move ES 0.56), reply 14. f3
  - 14... Nf4 (Good, pre-move ES 0.60), reply 15. Rf2
  - 15... Ncd3 (Good, pre-move ES 0.75), reply 16. Bxd3
  - 16... Nxd3 (Good, pre-move ES 0.75), reply 17. Qe2
- **Answer:** all safe (every judged move is Good).

#### Window 7: allowed (length 4, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=2700884&ply=42
- **User rating:** 1768 (pinned Maia Elo 1768)
- **FEN before the lead-in:** `r5k1/1p2b1pp/pqn1p3/3nr3/2p3B1/2PP3R/PP5P/1RB3QK w - - 0 22`
- **Lead-in:** 22. d4
- **Judged user moves:**
- **FEN before the answer move:** `r5k1/1p2b1pp/pqn1p3/3nr3/2pP2B1/2P4R/PP5P/1RB3QK b - - 0 22`
- **Answer:** blunder 22... Re2 (pre-move ES 0.70, ES after 0.23).
- **Refutation:** Bxe2.
- **Score inputs:** facepalm score 0.993, played prob 0.013, material loss 5.000, material missed 0.000, reply prob 0.957, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.038, pre-blunder spread 4.78.

#### Window 8: allowed (length 4, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=2237495&ply=0
- **User rating:** 1716 (pinned Maia Elo 1971)
- **FEN before the lead-in:** `rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1`
- **Lead-in:** 1. e4
- **Judged user moves:**
  - 1... g6 (Good, pre-move ES 0.47), reply 2. d4
  - 2... Bg7 (Good, pre-move ES 0.44), reply 3. e5
- **FEN before the answer move:** `rnbqk1nr/ppppppbp/6p1/4P3/3P4/8/PPP2PPP/RNBQKBNR b KQkq - 0 3`
- **Answer:** blunder 3... Nf6 (pre-move ES 0.53, ES after 0.20).
- **Refutation:** exf6.
- **Score inputs:** facepalm score 0.950, played prob 0.000, material loss 2.000, material missed 0.323, reply prob 0.982, mate ply n/a.
- **Missed inputs:** missed gain 0.323, best move prob 0.655, pre-blunder spread 3.16.

#### Window 9: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2597097&ply=30
- **User rating:** 2046 (pinned Maia Elo 1932)
- **FEN before the lead-in:** `2r2rk1/pp1qpp1p/3p1npQ/8/3NP3/2N2P2/PnP3PP/1R3RK1 w - - 2 16`
- **Lead-in:** 16. Rxb2
- **Judged user moves:**
  - 16... Rxc3 (Good, pre-move ES 0.72), reply 17. Rfb1
  - 17... b6 (Good, pre-move ES 0.73), reply 18. a4
  - 18... Rfc8 (Good, pre-move ES 0.77), reply 19. a5
  - 19... bxa5 (Good, pre-move ES 0.77), reply 20. Rb7
  - 20... R3c7 (Good, pre-move ES 0.74), reply 21. R7b5
- **Answer:** all safe (every judged move is Good).

#### Window 10: allowed (length 3, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=604003&ply=63
- **User rating:** 1716 (pinned Maia Elo 1971)
- **FEN before the lead-in:** `2r2r2/4b2p/pkP1b1p1/1p2Bp2/1P3P2/1N4P1/P1R4P/2R3K1 b - - 2 32`
- **Lead-in:** 32... Bxb4
- **Judged user moves:**
- **FEN before the answer move:** `2r2r2/7p/pkP1b1p1/1p2Bp2/1b3P2/1N4P1/P1R4P/2R3K1 w - - 0 33`
- **Answer:** blunder 33. a3 (pre-move ES 0.50, ES after 0.26).
- **Refutation:** Bxb3.
- **Score inputs:** facepalm score 0.945, played prob 0.001, material loss 2.516, material missed 1.355, reply prob 0.301, mate ply n/a.
- **Missed inputs:** missed gain 1.355, best move prob 0.307, pre-blunder spread 3.87.

#### Window 11: allowed (length 3, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=1655637&ply=42
- **User rating:** 1610 (pinned Maia Elo 1610)
- **FEN before the lead-in:** `1r4k1/2Qp2qp/b1p1p3/p4p2/8/8/Pr1R1PPP/3R2K1 w - - 2 22`
- **Lead-in:** 22. Rxd7
- **Judged user moves:**
- **FEN before the answer move:** `1r4k1/2QR2qp/b1p1p3/p4p2/8/8/Pr3PPP/3R2K1 b - - 0 22`
- **Answer:** blunder 22... Qc3 (pre-move ES 0.34, ES after 0.02).
- **Refutation:** Rd8+.
- **Score inputs:** facepalm score 0.992, played prob 0.008, material loss 5.000, material missed 0.000, reply prob 0.631, mate ply 3.
- **Missed inputs:** missed gain 0.000, best move prob 0.129, pre-blunder spread 8.88.

#### Window 12: pure_miss (length 5, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=1881540&ply=41
- **User rating:** 1550 (pinned Maia Elo 1815)
- **FEN before the lead-in:** `r2R1bk1/1q3ppp/p1b1pn1B/8/Pp6/1B4Q1/NP3PPP/2R3K1 b - - 0 21`
- **Lead-in:** 21... Rxd8
- **Judged user moves:**
  - 22. h3 (Good, pre-move ES 0.24), reply 22... Rd2
- **FEN before the answer move:** `5bk1/1q3ppp/p1b1pn1B/8/Pp6/1B4QP/NP1r1PP1/2R3K1 w - - 1 23`
- **Answer:** blunder 23. Re1 (pre-move ES 0.79, ES after 0.19).
- **Missed best move:** Bxd2.
- **Score inputs:** facepalm score 0.969, played prob 0.002, material loss 0.839, material missed 4.710, reply prob 0.633, mate ply n/a.
- **Missed inputs:** missed gain 4.710, best move prob 0.873, pre-blunder spread 1.99.

#### Window 13: herring (length 3, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2077665&ply=13
- **User rating:** 1269 (pinned Maia Elo 1616)
- **FEN before the lead-in:** `r1bqk1nr/pp3pbp/2n1p1p1/2pP4/2B5/2PP1N2/PP3PPP/RNBQ1RK1 b kq - 0 7`
- **Lead-in:** 7... exd5
- **Judged user moves:**
  - 8. Re1+ (Good, pre-move ES 0.49), reply 8... Nge7
  - 9. Bb5 (Good, pre-move ES 0.48), reply 9... O-O
  - 10. Bg5 (Good, pre-move ES 0.47), reply 10... Re8
- **Answer:** all safe (every judged move is Good).

#### Window 14: allowed (length 4, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=2605010&ply=36
- **User rating:** 1605 (pinned Maia Elo 1605)
- **FEN before the lead-in:** `1rq1rnk1/p4pnp/3p2p1/3p2P1/Q1P4P/1PN2N2/4PP2/R3K2R w KQ - 0 19`
- **Lead-in:** 19. Nxd5
- **Judged user moves:**
- **FEN before the answer move:** `1rq1rnk1/p4pnp/3p2p1/3N2P1/Q1P4P/1P3N2/4PP2/R3K2R b KQ - 0 19`
- **Answer:** blunder 19... Rb7 (pre-move ES 0.42, ES after 0.22).
- **Refutation:** Nf6+.
- **Score inputs:** facepalm score 0.712, played prob 0.032, material loss 0.968, material missed 0.000, reply prob 0.835, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.074, pre-blunder spread 11.94.

#### Window 15: allowed (length 5, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=1322156&ply=55
- **User rating:** 1879 (pinned Maia Elo 1879)
- **FEN before the lead-in:** `4r1k1/1p2rp2/p1p3pp/8/3PB3/PP4bP/1BR1R1P1/6K1 b - - 0 28`
- **Lead-in:** 28... Rxe4
- **Judged user moves:**
- **FEN before the answer move:** `4r1k1/1p3p2/p1p3pp/8/3Pr3/PP4bP/1BR1R1P1/6K1 w - - 0 29`
- **Answer:** blunder 29. Bc3 (pre-move ES 0.23, ES after 0.06).
- **Refutation:** Rxe2.
- **Score inputs:** facepalm score 0.996, played prob 0.001, material loss 5.000, material missed 0.000, reply prob 0.993, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.666, pre-blunder spread 2.10.

#### Window 16: allowed (length 3, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=2735787&ply=3
- **User rating:** 1486 (pinned Maia Elo 1770)
- **FEN before the lead-in:** `rnbqkbnr/pppp1ppp/8/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq - 1 2`
- **Lead-in:** 2... Nc6
- **Judged user moves:**
  - 3. Bc4 (Good, pre-move ES 0.53), reply 3... d6
  - 4. d4 (Good, pre-move ES 0.55), reply 4... exd4
- **FEN before the answer move:** `r1bqkbnr/ppp2ppp/2np4/8/2BpP3/5N2/PPP2PPP/RNBQK2R w KQkq - 0 5`
- **Answer:** blunder 5. Qxd4 (pre-move ES 0.54, ES after 0.13).
- **Refutation:** Nxd4.
- **Score inputs:** facepalm score 0.997, played prob 0.000, material loss 5.000, material missed 1.000, reply prob 0.899, mate ply n/a.
- **Missed inputs:** missed gain 1.000, best move prob 0.690, pre-blunder spread 2.76.

#### Window 17: herring (length 3, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2797807&ply=72
- **User rating:** 1848 (pinned Maia Elo 1848)
- **FEN before the lead-in:** `8/1p1k1p2/p1pP2pp/2P5/1PK5/P3rB2/6PP/8 w - - 10 37`
- **Lead-in:** 37. a4
- **Judged user moves:**
  - 37... f5 (Good, pre-move ES 0.79), reply 38. b5
  - 38... axb5+ (Good, pre-move ES 0.81), reply 39. axb5
  - 39... cxb5+ (Good, pre-move ES 0.80), reply 40. Kxb5
- **Answer:** all safe (every judged move is Good).

#### Window 18: herring (length 3, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=1890783&ply=0
- **User rating:** 1762 (pinned Maia Elo 1995)
- **FEN before the lead-in:** `rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1`
- **Lead-in:** 1. b4
- **Judged user moves:**
  - 1... c6 (Good, pre-move ES 0.54), reply 2. Bb2
  - 2... d5 (Good, pre-move ES 0.53), reply 3. e3
  - 3... Nf6 (Good, pre-move ES 0.52), reply 4. d4
- **Answer:** all safe (every judged move is Good).

#### Window 19: herring (length 3, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2307302&ply=28
- **User rating:** 1681 (pinned Maia Elo 1904)
- **FEN before the lead-in:** `r4rk1/pb3pp1/1p3q1p/P1ppb3/8/2P1P2P/1P1NBPP1/R2Q1K1R w - - 0 15`
- **Lead-in:** 15. Nf3
- **Judged user moves:**
  - 15... Bc7 (Good, pre-move ES 0.63), reply 16. Qc2
  - 16... bxa5 (Good, pre-move ES 0.71), reply 17. Qb3
  - 17... Qb6 (Good, pre-move ES 0.74), reply 18. Qxb6
- **Answer:** all safe (every judged move is Good).

#### Window 20: herring (length 3, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2741013&ply=16
- **User rating:** 1284 (pinned Maia Elo 1625)
- **FEN before the lead-in:** `rnb1k2r/1p1qbppp/p3pn2/2p5/2P5/2N2N2/PP1PBPPP/R1BQ1RK1 w kq - 0 9`
- **Lead-in:** 9. Ne5
- **Judged user moves:**
  - 9... Qc7 (Good, pre-move ES 0.56), reply 10. Ng4
  - 10... O-O (Good, pre-move ES 0.60), reply 11. Bf3
  - 11... Nc6 (Good, pre-move ES 0.62), reply 12. Nxf6+
- **Answer:** all safe (every judged move is Good).

### 2000-2399

#### Window 1: allowed (length 5, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=1231499&ply=59
- **User rating:** 1913 (pinned Maia Elo 2056)
- **FEN before the lead-in:** `b1r2k1r/2q5/p3p1Q1/5p1p/3P4/2PB3P/PP1K1P2/2R3R1 b - - 2 30`
- **Lead-in:** 30... Qf4+
- **Judged user moves:**
- **FEN before the answer move:** `b1r2k1r/8/p3p1Q1/5p1p/3P1q2/2PB3P/PP1K1P2/2R3R1 w - - 3 31`
- **Answer:** blunder 31. Ke2 (pre-move ES 0.82, ES after 0.02).
- **Refutation:** Bf3+.
- **Score inputs:** facepalm score 0.984, played prob 0.116, material loss 5.000, material missed 1.129, reply prob 0.714, mate ply 3.
- **Missed inputs:** missed gain 1.129, best move prob 0.699, pre-blunder spread 2.55.

#### Window 2: allowed (length 3, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=2227841&ply=25
- **User rating:** 2256 (pinned Maia Elo 2269)
- **FEN before the lead-in:** `r4rk1/pppq1ppp/2n3n1/4P1B1/2Pp4/P4BP1/1P1QPP1P/R4RK1 b - - 0 13`
- **Lead-in:** 13... Ncxe5
- **Judged user moves:**
  - 14. Bxb7 (Good, pre-move ES 0.51), reply 14... Rab8
  - 15. Bd5 (Good, pre-move ES 0.53), reply 15... c6
- **FEN before the answer move:** `1r3rk1/p2q1ppp/2p3n1/3Bn1B1/2Pp4/P5P1/1P1QPP1P/R4RK1 w - - 0 16`
- **Answer:** blunder 16. f4 (pre-move ES 0.53, ES after 0.36).
- **Refutation:** cxd5.
- **Score inputs:** facepalm score 0.719, played prob 0.032, material loss 1.000, material missed 0.000, reply prob 0.846, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.052, pre-blunder spread 1.64.

#### Window 3: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=3329774&ply=5
- **User rating:** 2176 (pinned Maia Elo 2176)
- **FEN before the lead-in:** `rnbqkbnr/ppp2ppp/3p4/4p3/4PP2/5N2/PPPP2PP/RNBQKB1R b KQkq - 1 3`
- **Lead-in:** 3... Bg4
- **Judged user moves:**
  - 4. Nc3 (Good, pre-move ES 0.57), reply 4... Nc6
  - 5. Bb5 (Good, pre-move ES 0.56), reply 5... exf4
  - 6. d4 (Good, pre-move ES 0.58), reply 6... a6
  - 7. Bxc6+ (Good, pre-move ES 0.57), reply 7... bxc6
  - 8. Bxf4 (Good, pre-move ES 0.57), reply 8... Be7
- **Answer:** all safe (every judged move is Good).

#### Window 4: allowed (length 3, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=574564&ply=45
- **User rating:** 1941 (pinned Maia Elo 2107)
- **FEN before the lead-in:** `r3r1k1/p6p/1p2p1p1/2p5/3nP3/P2Q1B1P/5PP1/3R2K1 b - - 6 23`
- **Lead-in:** 23... Rad8
- **Judged user moves:**
  - 24. e5 (Good, pre-move ES 0.82), reply 24... Kg7
  - 25. Qe4 (Good, pre-move ES 0.82), reply 25... Rf8
- **FEN before the answer move:** `3r1r2/p5kp/1p2p1p1/2p1P3/3nQ3/P4B1P/5PP1/3R2K1 w - - 3 26`
- **Answer:** blunder 26. Qh4 (pre-move ES 0.82, ES after 0.28).
- **Refutation:** Nxf3+.
- **Score inputs:** facepalm score 0.993, played prob 0.002, material loss 5.000, material missed 0.000, reply prob 0.584, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.016, pre-blunder spread 9.04.

#### Window 5: allowed (length 4, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=500360&ply=42
- **User rating:** 1903 (pinned Maia Elo 2086)
- **FEN before the lead-in:** `r1b5/1p2qkp1/p1nb1n1p/2p4P/P2p4/NP2P3/1BPP1Q2/2KR2NR w - - 5 22`
- **Lead-in:** 22. Ne2
- **Judged user moves:**
  - 22... dxe3 (Good, pre-move ES 0.32), reply 23. dxe3
- **FEN before the answer move:** `r1b5/1p2qkp1/p1nb1n1p/2p4P/P7/NP2P3/1BP1NQ2/2KR3R b - - 0 23`
- **Answer:** blunder 23... c4 (pre-move ES 0.32, ES after 0.16).
- **Refutation:** Nxc4.
- **Score inputs:** facepalm score 0.812, played prob 0.012, material loss 1.000, material missed 0.000, reply prob 0.984, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.299, pre-blunder spread 6.74.

#### Window 6: allowed (length 3, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=574449&ply=11
- **User rating:** 1821 (pinned Maia Elo 2046)
- **FEN before the lead-in:** `rnbqk2r/ppp2ppp/8/2bPP3/4n3/4PN2/PP3PPP/RNBQKB1R b KQkq - 0 6`
- **Lead-in:** 6... c6
- **Judged user moves:**
- **FEN before the answer move:** `rnbqk2r/pp3ppp/2p5/2bPP3/4n3/4PN2/PP3PPP/RNBQKB1R w KQkq - 0 7`
- **Answer:** blunder 7. dxc6 (pre-move ES 0.76, ES after 0.30).
- **Refutation:** Qxd1+.
- **Score inputs:** facepalm score 0.778, played prob 0.027, material loss 1.129, material missed 0.000, reply prob 0.979, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.594, pre-blunder spread 4.30.

#### Window 7: allowed (length 4, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=2496270&ply=30
- **User rating:** 1853 (pinned Maia Elo 2008)
- **FEN before the lead-in:** `3r1rk1/1pq2pbp/p1p1pnp1/2n5/2P5/1P2PNPP/PBQ2PB1/3R1RK1 w - - 4 16`
- **Lead-in:** 16. Rxd8
- **Judged user moves:**
  - 16... Rxd8 (Good, pre-move ES 0.44), reply 17. Rd1
- **FEN before the answer move:** `3r2k1/1pq2pbp/p1p1pnp1/2n5/2P5/1P2PNPP/PBQ2PB1/3R2K1 b - - 1 17`
- **Answer:** blunder 17... b5 (pre-move ES 0.47, ES after 0.18).
- **Refutation:** Rxd8+.
- **Score inputs:** facepalm score 0.722, played prob 0.011, material loss 1.226, material missed 0.000, reply prob 0.393, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.648, pre-blunder spread 4.22.

#### Window 8: herring (length 4, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2616858&ply=9
- **User rating:** 2019 (pinned Maia Elo 2019)
- **FEN before the lead-in:** `rnbqkbnr/pp2pp2/2pp3p/6p1/4P3/2NPBN2/PPP2PPP/R2QKB1R b KQkq - 1 5`
- **Lead-in:** 5... Bg7
- **Judged user moves:**
  - 6. Qd2 (Good, pre-move ES 0.61), reply 6... Nd7
  - 7. O-O-O (Good, pre-move ES 0.60), reply 7... c5
  - 8. d4 (Good, pre-move ES 0.65), reply 8... g4
  - 9. Nh4 (Good, pre-move ES 0.64), reply 9... cxd4
- **Answer:** all safe (every judged move is Good).

#### Window 9: herring (length 3, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=605802&ply=26
- **User rating:** 2013 (pinned Maia Elo 2155)
- **FEN before the lead-in:** `r1b2rk1/p2n1p2/1pp1pq1p/8/PbBP3p/2NQ4/1P2NPPP/R4RK1 w - - 0 14`
- **Lead-in:** 14. Ne4
- **Judged user moves:**
  - 14... Qg7 (Good, pre-move ES 0.57), reply 15. Nf4
  - 15... Bb7 (Good, pre-move ES 0.56), reply 16. Nh5
  - 16... Qg6 (Good, pre-move ES 0.58), reply 17. Nef6+
- **Answer:** all safe (every judged move is Good).

#### Window 10: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=1537579&ply=17
- **User rating:** 2004 (pinned Maia Elo 2004)
- **FEN before the lead-in:** `r1bqk2r/3pppbp/p1p2np1/8/2B1P3/2N1B3/PPPQ1PPP/R3K2R b KQkq - 1 9`
- **Lead-in:** 9... Ng4
- **Judged user moves:**
  - 10. Bd4 (Good, pre-move ES 0.60), reply 10... e5
  - 11. Bc5 (Good, pre-move ES 0.68), reply 11... Qf6
  - 12. h3 (Good, pre-move ES 0.77), reply 12... Nh6
  - 13. O-O-O (Good, pre-move ES 0.81), reply 13... Rb8
  - 14. g4 (Good, pre-move ES 0.84), reply 14... Ng8
- **Answer:** all safe (every judged move is Good).

#### Window 11: pure_miss (length 3, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=1534474&ply=43
- **User rating:** 2110 (pinned Maia Elo 2110)
- **FEN before the lead-in:** `5rk1/1p2ppb1/p5p1/7p/4r3/2P5/PP1R2PP/1KBR4 b - - 1 22`
- **Lead-in:** 22... Re6
- **Judged user moves:**
  - 23. Kc2 (Good, pre-move ES 0.31), reply 23... Rc6
- **FEN before the answer move:** `5rk1/1p2ppb1/p1r3p1/7p/8/2P5/PPKR2PP/2BR4 w - - 4 24`
- **Answer:** blunder 24. Rf1 (pre-move ES 0.49, ES after 0.32).
- **Missed best move:** Rd7.
- **Score inputs:** facepalm score 0.808, played prob 0.000, material loss 0.032, material missed 1.000, reply prob 0.242, mate ply n/a.
- **Missed inputs:** missed gain 1.000, best move prob 0.947, pre-blunder spread 1.33.

#### Window 12: herring (length 3, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=611654&ply=0
- **User rating:** 2122 (pinned Maia Elo 2217)
- **FEN before the lead-in:** `rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1`
- **Lead-in:** 1. e4
- **Judged user moves:**
  - 1... c5 (Good, pre-move ES 0.46), reply 2. Nc3
  - 2... d6 (Good, pre-move ES 0.47), reply 3. f4
  - 3... Nc6 (Good, pre-move ES 0.49), reply 4. Nf3
- **Answer:** all safe (every judged move is Good).

#### Window 13: herring (length 4, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=1231539&ply=57
- **User rating:** 1937 (pinned Maia Elo 2068)
- **FEN before the lead-in:** `2q2rk1/p2R1pp1/7p/8/4b1P1/1Q5P/P4P2/2rR1BK1 b - - 4 29`
- **Lead-in:** 29... Rxd1
- **Judged user moves:**
  - 30. Qxd1 (Good, pre-move ES 0.51), reply 30... Bc2
  - 31. Qd5 (Good, pre-move ES 0.54), reply 31... Ba4
  - 32. Rxa7 (Good, pre-move ES 0.54), reply 32... Bc6
  - 33. Qd4 (Good, pre-move ES 0.54), reply 33... Rd8
- **Answer:** all safe (every judged move is Good).

#### Window 14: allowed (length 5, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=2670187&ply=11
- **User rating:** 2168 (pinned Maia Elo 2214)
- **FEN before the lead-in:** `rnb1kbnr/pp3ppp/2p5/q3P3/4p3/2N2P2/PPPB2PP/R2QKBNR b KQkq - 3 6`
- **Lead-in:** 6... Qxe5
- **Judged user moves:**
  - 7. Qe2 (Good, pre-move ES 0.55), reply 7... Nf6
- **FEN before the answer move:** `rnb1kb1r/pp3ppp/2p2n2/4q3/4p3/2N2P2/PPPBQ1PP/R3KBNR w KQkq - 2 8`
- **Answer:** blunder 8. Bg5 (pre-move ES 0.56, ES after 0.14).
- **Refutation:** Qxg5.
- **Score inputs:** facepalm score 0.952, played prob 0.000, material loss 2.000, material missed 1.000, reply prob 0.724, mate ply n/a.
- **Missed inputs:** missed gain 1.000, best move prob 0.338, pre-blunder spread 2.31.

#### Window 15: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2126123&ply=24
- **User rating:** 2067 (pinned Maia Elo 2150)
- **FEN before the lead-in:** `rn5r/pp1k2pp/5p2/2bp4/8/4PN2/PP3PPP/R1B1K2R w KQ - 0 13`
- **Lead-in:** 13. O-O
- **Judged user moves:**
  - 13... Nc6 (Good, pre-move ES 0.50), reply 14. Rd1
  - 14... Ke6 (Good, pre-move ES 0.50), reply 15. a3
  - 15... a5 (Good, pre-move ES 0.51), reply 16. b3
  - 16... Rac8 (Good, pre-move ES 0.51), reply 17. Bb2
  - 17... Rhd8 (Good, pre-move ES 0.51), reply 18. Rac1
- **Answer:** all safe (every judged move is Good).

#### Window 16: allowed (length 3, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=1204764&ply=81
- **User rating:** 2063 (pinned Maia Elo 2185)
- **FEN before the lead-in:** `8/8/3pr1k1/2p1n1pp/4P3/2P2PBP/6PK/5R2 b - - 0 41`
- **Lead-in:** 41... h4
- **Judged user moves:**
- **FEN before the answer move:** `8/8/3pr1k1/2p1n1p1/4P2p/2P2PBP/6PK/5R2 w - - 0 42`
- **Answer:** blunder 42. f4 (pre-move ES 0.69, ES after 0.26).
- **Refutation:** hxg3+.
- **Score inputs:** facepalm score 0.942, played prob 0.001, material loss 2.000, material missed 0.000, reply prob 0.980, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.700, pre-blunder spread 2.11.

#### Window 17: allowed (length 4, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=2020979&ply=23
- **User rating:** 1864 (pinned Maia Elo 2018)
- **FEN before the lead-in:** `r3k1nr/pppb1ppp/2n5/1B6/3P4/2P1BN2/P4PPP/R3K2R b KQkq - 0 12`
- **Lead-in:** 12... O-O-O
- **Judged user moves:**
  - 13. O-O (Good, pre-move ES 0.53), reply 13... Nf6
- **FEN before the answer move:** `2kr3r/pppb1ppp/2n2n2/1B6/3P4/2P1BN2/P4PPP/R4RK1 w - - 3 14`
- **Answer:** blunder 14. Ne5 (pre-move ES 0.53, ES after 0.23).
- **Refutation:** Nxe5.
- **Score inputs:** facepalm score 0.958, played prob 0.009, material loss 2.806, material missed 0.000, reply prob 0.970, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.146, pre-blunder spread 11.81.

#### Window 18: allowed (length 5, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=1227655&ply=66
- **User rating:** 2224 (pinned Maia Elo 2134)
- **FEN before the lead-in:** `k1r5/1p2R3/p1p2p2/8/1Q1P2pP/P1P3P1/8/5q1K w - - 6 34`
- **Lead-in:** 34. Kh2
- **Judged user moves:**
  - 34... Qh3+ (Good, pre-move ES 0.84), reply 35. Kg1
  - 35... Qxg3+ (Good, pre-move ES 0.83), reply 36. Kh1
- **FEN before the answer move:** `k1r5/1p2R3/p1p2p2/8/1Q1P2pP/P1P3q1/8/7K b - - 1 36`
- **Answer:** blunder 36... Qe1+ (pre-move ES 0.86, ES after 0.06).
- **Refutation:** Rxe1.
- **Score inputs:** facepalm score 0.997, played prob 0.002, material loss 5.000, material missed 1.000, reply prob 0.904, mate ply n/a.
- **Missed inputs:** missed gain 1.000, best move prob 0.797, pre-blunder spread 2.18.

#### Window 19: allowed (length 5, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=3028334&ply=65
- **User rating:** 2074 (pinned Maia Elo 2027)
- **FEN before the lead-in:** `5Q1k/ppp5/3p4/4p2p/4P3/2P5/PP6/2qb1K2 b - - 3 33`
- **Lead-in:** 33... Kh7
- **Judged user moves:**
  - 34. Qf7+ (Good, pre-move ES 0.50), reply 34... Kh6
  - 35. Qf6+ (Good, pre-move ES 0.50), reply 35... Kh7
- **FEN before the answer move:** `8/ppp4k/3p1Q2/4p2p/4P3/2P5/PP6/2qb1K2 w - - 8 36`
- **Answer:** blunder 36. Qf8 (pre-move ES 0.50, ES after 0.05).
- **Refutation:** unknown.
- **Score inputs:** facepalm score 0.711, played prob 0.001, material loss 0.000, material missed 0.000, reply prob 0.599, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.889, pre-blunder spread 1.55.

#### Window 20: allowed (length 3, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=2734898&ply=82
- **User rating:** 2089 (pinned Maia Elo 2162)
- **FEN before the lead-in:** `1r4k1/2Q4p/p3p1p1/8/1P1R4/7P/P4PP1/1q4K1 w - - 1 42`
- **Lead-in:** 42. Kh2
- **Judged user moves:**
- **FEN before the answer move:** `1r4k1/2Q4p/p3p1p1/8/1P1R4/7P/P4PPK/1q6 b - - 2 42`
- **Answer:** blunder 42... Rxb4 (pre-move ES 0.23, ES after 0.02).
- **Refutation:** Rd8#.
- **Score inputs:** facepalm score 0.981, played prob 0.106, material loss 5.000, material missed 0.000, reply prob 0.951, mate ply 1.
- **Missed inputs:** missed gain 0.000, best move prob 0.810, pre-blunder spread 2.05.

### 2400+

#### Window 1: allowed (length 5, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=1517409&ply=83
- **User rating:** 2882 (pinned Maia Elo 2600)
- **FEN before the lead-in:** `2b1r1k1/5p2/5Rp1/3Pn2p/1R2PN2/5B1P/3r2P1/7K b - - 0 42`
- **Lead-in:** 42... Kg7
- **Judged user moves:**
  - 43. Rfb6 (Good, pre-move ES 0.49), reply 43... h4
- **FEN before the answer move:** `2b1r3/5pk1/1R4p1/3Pn3/1R2PN1p/5B1P/3r2P1/7K w - - 0 44`
- **Answer:** blunder 44. Ne2 (pre-move ES 0.51, ES after 0.21).
- **Refutation:** Nxf3.
- **Score inputs:** facepalm score 0.913, played prob 0.015, material loss 2.323, material missed 0.000, reply prob 0.772, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.034, pre-blunder spread 5.65.

#### Window 2: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=1517326&ply=63
- **User rating:** 2880 (pinned Maia Elo 2600)
- **FEN before the lead-in:** `r1r2k2/5p1p/p2N1p2/4n3/8/6P1/P4PKP/R1R5 b - - 14 32`
- **Lead-in:** 32... Rd8
- **Judged user moves:**
  - 33. Ne4 (Good, pre-move ES 0.54), reply 33... Kg7
  - 34. Nc5 (Good, pre-move ES 0.51), reply 34... Rd2
  - 35. Rd1 (Good, pre-move ES 0.51), reply 35... Rc2
  - 36. Rdc1 (Good, pre-move ES 0.50), reply 36... Rd2
  - 37. Ne4 (Good, pre-move ES 0.51), reply 37... Re2
- **Answer:** all safe (every judged move is Good).

#### Window 3: allowed (length 3, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=1518563&ply=42
- **User rating:** 2848 (pinned Maia Elo 2600)
- **FEN before the lead-in:** `r1q1r1k1/1p3pp1/p1p2bbp/1N6/4n3/1Q1RB1P1/PP2PPBP/2R3K1 w - - 0 22`
- **Lead-in:** 22. Nd6
- **Judged user moves:**
  - 22... Nxd6 (Good, pre-move ES 0.50), reply 23. Rxd6
- **FEN before the answer move:** `r1q1r1k1/1p3pp1/p1pR1bbp/8/8/1Q2B1P1/PP2PPBP/2R3K1 b - - 0 23`
- **Answer:** blunder 23... Be5 (pre-move ES 0.50, ES after 0.29).
- **Refutation:** Rxg6.
- **Score inputs:** facepalm score 0.839, played prob 0.198, material loss 2.516, material missed 0.677, reply prob 0.945, mate ply n/a.
- **Missed inputs:** missed gain 0.677, best move prob 0.051, pre-blunder spread 11.17.

#### Window 4: pure_miss (length 3, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=1525980&ply=68
- **User rating:** 2927 (pinned Maia Elo 2600)
- **FEN before the lead-in:** `7r/3bkp2/1b2p3/pp3p2/1P6/P1R1P1P1/2N1KPB1/8 w - - 1 35`
- **Lead-in:** 35. Bc6
- **Judged user moves:**
- **FEN before the answer move:** `7r/3bkp2/1bB1p3/pp3p2/1P6/P1R1P1P1/2N1KP2/8 b - - 2 35`
- **Answer:** blunder 35... a4 (pre-move ES 0.83, ES after 0.50).
- **Missed best move:** Rc8.
- **Score inputs:** facepalm score 0.808, played prob 0.010, material loss 0.000, material missed 3.000, reply prob 0.667, mate ply n/a.
- **Missed inputs:** missed gain 3.000, best move prob 0.712, pre-blunder spread 2.39.

#### Window 5: allowed (length 3, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=1511274&ply=93
- **User rating:** 2510 (pinned Maia Elo 2456)
- **FEN before the lead-in:** `r7/1R1R3p/5pp1/4p1k1/2N1P1P1/5n1K/r6P/8 b - - 0 47`
- **Lead-in:** 47... Nxh2
- **Judged user moves:**
- **FEN before the answer move:** `r7/1R1R3p/5pp1/4p1k1/2N1P1P1/7K/r6n/8 w - - 0 48`
- **Answer:** blunder 48. Nd6 (pre-move ES 0.13, ES after 0.02).
- **Refutation:** R8a3+.
- **Score inputs:** facepalm score 0.977, played prob 0.150, material loss 5.000, material missed 0.000, reply prob 0.927, mate ply 3.
- **Missed inputs:** missed gain 0.000, best move prob 0.032, pre-blunder spread 5.78.

#### Window 6: pure_miss (length 4, blunder at 4)

- **Game:** https://flawchess.com/analysis?game_id=658417&ply=43
- **User rating:** 2516 (pinned Maia Elo 2463)
- **FEN before the lead-in:** `r4rk1/pp1q2p1/2n1bn1p/3p3P/3PpN2/2P1B1P1/3QB1P1/2R2RK1 b - - 6 22`
- **Lead-in:** 22... Bg4
- **Judged user moves:**
  - 23. Rb1 (Good, pre-move ES 0.39), reply 23... Bxe2
  - 24. Qxe2 (Good, pre-move ES 0.34), reply 24... Na5
  - 25. Ng6 (Good, pre-move ES 0.42), reply 25... Rfc8
- **FEN before the answer move:** `r1r3k1/pp1q2p1/5nNp/n2p3P/3Pp3/2P1B1P1/4Q1P1/1R3RK1 w - - 3 26`
- **Answer:** blunder 26. Ne5 (pre-move ES 0.66, ES after 0.50).
- **Missed best move:** Bxh6.
- **Score inputs:** facepalm score 0.957, played prob 0.159, material loss 4.000, material missed 1.000, reply prob 0.817, mate ply n/a.
- **Missed inputs:** missed gain 1.000, best move prob 0.724, pre-blunder spread 2.57.

#### Window 7: allowed (length 3, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=1515849&ply=134
- **User rating:** 2852 (pinned Maia Elo 2600)
- **FEN before the lead-in:** `8/2k5/3r4/P7/1R6/1K6/8/8 w - - 3 68`
- **Lead-in:** 68. Ka4
- **Judged user moves:**
  - 68... Kd7 (Good, pre-move ES 0.50), reply 69. Rb5
  - 69... Ke7 (Good, pre-move ES 0.50), reply 70. Kb4
- **FEN before the answer move:** `8/4k3/3r4/PR6/1K6/8/8/8 b - - 8 70`
- **Answer:** blunder 70... Rd2 (pre-move ES 0.50, ES after 0.19).
- **Refutation:** a6.
- **Score inputs:** facepalm score 0.793, played prob 0.003, material loss 0.000, material missed 2.419, reply prob 0.626, mate ply n/a.
- **Missed inputs:** missed gain 2.419, best move prob 0.640, pre-blunder spread 3.46.

#### Window 8: allowed (length 5, blunder at 5)

- **Game:** https://flawchess.com/analysis?game_id=1518286&ply=46
- **User rating:** 2564 (pinned Maia Elo 2564)
- **FEN before the lead-in:** `r4rk1/5ppp/5bq1/3Qp3/3N4/2P1B3/1P1R1PPP/5RK1 w - - 4 24`
- **Lead-in:** 24. Nc6
- **Judged user moves:**
  - 24... Rfe8 (Good, pre-move ES 0.14), reply 25. b4
  - 25... Ra3 (Good, pre-move ES 0.14), reply 26. Qd7
  - 26... Rf8 (Good, pre-move ES 0.12), reply 27. Ne7+
  - 27... Bxe7 (Good, pre-move ES 0.14), reply 28. Qxe7
- **FEN before the answer move:** `5rk1/4Qppp/6q1/4p3/1P6/r1P1B3/3R1PPP/5RK1 b - - 0 28`
- **Answer:** blunder 28... Qe4 (pre-move ES 0.14, ES after 0.02).
- **Refutation:** Rd8.
- **Score inputs:** facepalm score 0.906, played prob 0.023, material loss 2.419, material missed 0.516, reply prob 0.594, mate ply n/a.
- **Missed inputs:** missed gain 0.516, best move prob 0.064, pre-blunder spread 4.70.

#### Window 9: allowed (length 3, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=641901&ply=51
- **User rating:** 2687 (pinned Maia Elo 2600)
- **FEN before the lead-in:** `q1rr1bk1/5p1p/pp1Ppnp1/6P1/PPP2P2/2N4P/1B4Q1/3RR1K1 b - - 0 26`
- **Lead-in:** 26... Qxg2+
- **Judged user moves:**
  - 27. Kxg2 (Good, pre-move ES 0.60), reply 27... Nh5
- **FEN before the answer move:** `2rr1bk1/5p1p/pp1Pp1p1/6Pn/PPP2P2/2N4P/1B4K1/3RR3 w - - 1 28`
- **Answer:** blunder 28. Rd4 (pre-move ES 0.65, ES after 0.42).
- **Refutation:** Rxd6.
- **Score inputs:** facepalm score 0.800, played prob 0.012, material loss 1.226, material missed 0.000, reply prob 0.691, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.673, pre-blunder spread 3.11.

#### Window 10: herring (length 3, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=658045&ply=65
- **User rating:** 2607 (pinned Maia Elo 2565)
- **FEN before the lead-in:** `1r5k/1pR3p1/3p4/p1nPp2B/2P1P2P/P1P1K1P1/8/8 b - - 0 33`
- **Lead-in:** 33... Kh7
- **Judged user moves:**
  - 34. g4 (Good, pre-move ES 0.77), reply 34... b5
  - 35. Rc6 (Good, pre-move ES 0.75), reply 35... g6
  - 36. Bxg6+ (Good, pre-move ES 0.79), reply 36... Kxg6
- **Answer:** all safe (every judged move is Good).

#### Window 11: allowed (length 3, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=615317&ply=29
- **User rating:** 2420 (pinned Maia Elo 2414)
- **FEN before the lead-in:** `r4rk1/pQ2ppbp/2pp1np1/8/2P2B2/2N2PPq/PP3P1P/R4RK1 b - - 3 15`
- **Lead-in:** 15... Rfe8
- **Judged user moves:**
  - 16. Qxc6 (Good, pre-move ES 0.51), reply 16... Nh5
- **FEN before the answer move:** `r3r1k1/p3ppbp/2Qp2p1/7n/2P2B2/2N2PPq/PP3P1P/R4RK1 w - - 1 17`
- **Answer:** blunder 17. Qa4 (pre-move ES 0.54, ES after 0.26).
- **Refutation:** Nxf4.
- **Score inputs:** facepalm score 0.875, played prob 0.000, material loss 1.032, material missed 0.000, reply prob 0.952, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.506, pre-blunder spread 4.34.

#### Window 12: mixed (length 3, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=1516950&ply=79
- **User rating:** 2875 (pinned Maia Elo 2600)
- **FEN before the lead-in:** `1Q6/pb1R4/kqp4r/1p5B/2p3P1/8/PP3PPK/8 b - - 0 40`
- **Lead-in:** 40... b4
- **Judged user moves:**
- **FEN before the answer move:** `1Q6/pb1R4/kqp4r/7B/1pp3P1/8/PP3PPK/8 w - - 0 41`
- **Answer:** blunder 41. Qe5 (pre-move ES 0.78, ES after 0.50).
- **Refutation:** Qxf2.
- **Missed best move:** Qf4.
- **Score inputs:** facepalm score 0.810, played prob 0.013, material loss 1.000, material missed 1.000, reply prob 0.614, mate ply n/a.
- **Missed inputs:** missed gain 1.000, best move prob 0.693, pre-blunder spread 3.71.

#### Window 13: allowed (length 5, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=644277&ply=140
- **User rating:** 2658 (pinned Maia Elo 2600)
- **FEN before the lead-in:** `8/8/4R3/1pr5/1k2p2K/4Pp2/5P2/8 w - - 0 71`
- **Lead-in:** 71. Kg4
- **Judged user moves:**
  - 71... Rc4 (Good, pre-move ES 0.86), reply 72. Re5
- **FEN before the answer move:** `8/8/8/1p2R3/1kr1p1K1/4Pp2/5P2/8 b - - 3 72`
- **Answer:** blunder 72... Rc3 (pre-move ES 0.87, ES after 0.50).
- **Refutation:** Rxe4+.
- **Score inputs:** facepalm score 0.877, played prob 0.000, material loss 1.097, material missed 0.000, reply prob 0.909, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.878, pre-blunder spread 1.72.

#### Window 14: allowed (length 5, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=1532315&ply=101
- **User rating:** 3116 (pinned Maia Elo 2600)
- **FEN before the lead-in:** `8/3R4/6k1/3n1p2/1p2p2P/bP2P3/2K2P2/8 b - - 4 51`
- **Lead-in:** 51... Nf6
- **Judged user moves:**
  - 52. Rd6 (Good, pre-move ES 0.50), reply 52... Kf7
  - 53. Ra6 (Good, pre-move ES 0.50), reply 53... Ng4
- **FEN before the answer move:** `8/5k2/R7/5p2/1p2p1nP/bP2P3/2K2P2/8 w - - 9 54`
- **Answer:** blunder 54. Kd1 (pre-move ES 0.50, ES after 0.34).
- **Refutation:** Nxf2+.
- **Score inputs:** facepalm score 0.808, played prob 0.009, material loss 1.000, material missed 0.000, reply prob 0.865, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.070, pre-blunder spread 2.31.

#### Window 15: allowed (length 4, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=1532885&ply=25
- **User rating:** 3072 (pinned Maia Elo 2600)
- **FEN before the lead-in:** `r1q2rk1/pp2ppbp/2n2np1/8/Q7/2N1B3/PPP1BPPP/3R1RK1 b - - 7 13`
- **Lead-in:** 13... a6
- **Judged user moves:**
- **FEN before the answer move:** `r1q2rk1/1p2ppbp/p1n2np1/8/Q7/2N1B3/PPP1BPPP/3R1RK1 w - - 0 14`
- **Answer:** blunder 14. Qg4 (pre-move ES 0.54, ES after 0.09).
- **Refutation:** Nxg4.
- **Score inputs:** facepalm score 0.995, played prob 0.000, material loss 5.000, material missed 0.000, reply prob 0.849, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.038, pre-blunder spread 6.70.

#### Window 16: allowed (length 3, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=643203&ply=51
- **User rating:** 2663 (pinned Maia Elo 2600)
- **FEN before the lead-in:** `5rk1/rp2b1p1/q1n4p/4pb2/2PpN3/PR4P1/3BPPBP/1RQ3K1 b - - 4 26`
- **Lead-in:** 26... Be6
- **Judged user moves:**
  - 27. Bxh6 (Good, pre-move ES 0.68), reply 27... Qxc4
- **FEN before the answer move:** `5rk1/rp2b1p1/2n1b2B/4p3/2qpN3/PR4P1/4PPBP/1RQ3K1 w - - 0 28`
- **Answer:** blunder 28. R3b2 (pre-move ES 0.68, ES after 0.50).
- **Refutation:** gxh6.
- **Score inputs:** facepalm score 0.990, played prob 0.003, material loss 3.933, material missed 2.000, reply prob 0.490, mate ply n/a.
- **Missed inputs:** missed gain 2.000, best move prob 0.508, pre-blunder spread 4.78.

#### Window 17: herring (length 3, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=1537427&ply=41
- **User rating:** 3203 (pinned Maia Elo 2600)
- **FEN before the lead-in:** `2r2r2/1b2ppkp/pq6/3p1B2/8/1P4P1/P3QP1P/2R2RK1 b - - 0 21`
- **Lead-in:** 21... Rxc1
- **Judged user moves:**
  - 22. Rxc1 (Good, pre-move ES 0.67), reply 22... Qf6
  - 23. Qg4+ (Good, pre-move ES 0.67), reply 23... Kh8
  - 24. Rc7 (Good, pre-move ES 0.67), reply 24... Ba8
- **Answer:** all safe (every judged move is Good).

#### Window 18: allowed (length 4, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=1513345&ply=44
- **User rating:** 2714 (pinned Maia Elo 2600)
- **FEN before the lead-in:** `r4rk1/p1q3pp/1p1n4/2p1nP2/2PpN1P1/1P1P4/PB2Q1Nb/R4R1K w - - 4 23`
- **Lead-in:** 23. Ng5
- **Judged user moves:**
- **FEN before the answer move:** `r4rk1/p1q3pp/1p1n4/2p1nPN1/2Pp2P1/1P1P4/PB2Q1Nb/R4R1K b - - 5 23`
- **Answer:** blunder 23... Rae8 (pre-move ES 0.50, ES after 0.28).
- **Refutation:** Ne6.
- **Score inputs:** facepalm score 0.823, played prob 0.122, material loss 2.419, material missed 0.000, reply prob 0.903, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.531, pre-blunder spread 5.40.

#### Window 19: allowed (length 4, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=2701539&ply=30
- **User rating:** 2456 (pinned Maia Elo 2600)
- **FEN before the lead-in:** `r3k2r/pbq1npb1/1pn1B1p1/2p3p1/P3NP2/2P5/1P1P2PP/R1BQ1RK1 w kq - 0 16`
- **Lead-in:** 16. Nxg5
- **Judged user moves:**
  - 16... fxe6 (Good, pre-move ES 0.80), reply 17. Nxe6
  - 17... Qd6 (Good, pre-move ES 0.80), reply 18. Qb3
- **FEN before the answer move:** `r3k2r/pb2n1b1/1pnqN1p1/2p5/P4P2/1QP5/1P1P2PP/R1B2RK1 b kq - 2 18`
- **Answer:** blunder 18... Qd5 (pre-move ES 0.84, ES after 0.50).
- **Refutation:** Nc7+.
- **Score inputs:** facepalm score 0.956, played prob 0.000, material loss 2.419, material missed 0.000, reply prob 0.868, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.000, pre-blunder spread 1.48.

#### Window 20: pure_miss (length 4, blunder at 4)

- **Game:** https://flawchess.com/analysis?game_id=657450&ply=63
- **User rating:** 2593 (pinned Maia Elo 2552)
- **FEN before the lead-in:** `2r3k1/1N2bppp/4p3/1B1n4/P7/4p1PP/6P1/3R1K2 b - - 2 32`
- **Lead-in:** 32... Bb4
- **Judged user moves:**
  - 33. Rb1 (Good, pre-move ES 0.20), reply 33... g5
  - 34. a5 (Good, pre-move ES 0.19), reply 34... Ra8
  - 35. a6 (Good, pre-move ES 0.48), reply 35... Bc5
- **FEN before the answer move:** `r5k1/1N3p1p/P3p3/1Bbn2p1/8/4p1PP/6P1/1R3K2 w - - 1 36`
- **Answer:** blunder 36. Be2 (pre-move ES 0.85, ES after 0.45).
- **Missed best move:** Nxc5.
- **Score inputs:** facepalm score 0.890, played prob 0.000, material loss 0.000, material missed 2.774, reply prob 0.443, mate ply n/a.
- **Missed inputs:** missed gain 2.774, best move prob 0.948, pre-blunder spread 1.32.
