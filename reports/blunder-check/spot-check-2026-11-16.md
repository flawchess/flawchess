# Blunder-check spot-check

Windows drawn the way the feature draws them (250 D-12): each slot is independently a herring (about 33%, all judged moves safe) or a blunder window, with length L uniform over 3 to 5 user moves. About 20 windows per Elo bucket, at most one per game, drawn with a fixed seed. A blunder window shows its facepalm score inputs after the answer.

Thresholds: facepalm score at least 0.5, eval band [0.10, 0.90] on the pre-move ES. A recommendation only; nothing here is wired into app code.

How to read: for each window, play through the lead-in and the judged moves on the board (the game link opens the game on FlawChess at the first judged move), decide whether the position is a fair question, then compare with the answer. A blunder window is fair when the refutation or the missed move is something a player of that rating could find. Moves are in SAN; a stored move that is not legal on the replayed board prints as its UCI with the word illegal.

### <800

#### Window 1: allowed (length 5, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=1669365&ply=7
- **User rating:** 260 (pinned Maia Elo 600)
- **FEN before the lead-in:** `rnbqkbnr/pp1p1ppp/8/2p5/3P1B2/4P3/PPP3PP/RN1QKBNR b KQkq - 0 4`
- **Lead-in:** 4... cxd4
- **Judged user moves:**
  - 5. exd4 (Good, pre-move ES 0.53), reply 5... Qf6
- **FEN before the answer move:** `rnb1kbnr/pp1p1ppp/5q2/8/3P1B2/8/PPP3PP/RN1QKBNR w KQkq - 1 6`
- **Answer:** blunder 6. c3 (pre-move ES 0.63, ES after 0.19).
- **Refutation:** Qxf4.
- **Score inputs:** facepalm score 0.963, played prob 0.025, reply spread 2.58, played material 3 -3, mate ply n/a.
- **Missed inputs:** best material 3 n/a, missed gain n/a, best move prob 0.033, pre-blunder spread 15.81.

#### Window 2: mixed (length 5, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=1641771&ply=23
- **User rating:** 153 (pinned Maia Elo 600)
- **FEN before the lead-in:** `rn2k1nr/pp3pp1/2pp4/2b1p1N1/2B1P1q1/3P4/PPPQ1PPP/R4RK1 b kq - 0 12`
- **Lead-in:** 12... Rh5
- **Judged user moves:**
- **FEN before the answer move:** `rn2k1n1/pp3pp1/2pp4/2b1p1Nr/2B1P1q1/3P4/PPPQ1PPP/R4RK1 w q - 1 13`
- **Answer:** blunder 13. h3 (pre-move ES 0.55, ES after 0.13).
- **Refutation:** Qxg5.
- **Missed best move:** Bxf7+.
- **Score inputs:** facepalm score 0.921, played prob 0.083, reply spread 7.44, played material 3 -3, mate ply n/a.
- **Missed inputs:** best material 3 3, missed gain 3, best move prob 0.291, pre-blunder spread 9.67.

#### Window 3: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=1918989&ply=0
- **User rating:** 205 (pinned Maia Elo 600)
- **FEN before the lead-in:** `rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1`
- **Lead-in:** 1. d4
- **Judged user moves:**
  - 1... d5 (Good, pre-move ES 0.47), reply 2. c4
  - 2... e6 (Good, pre-move ES 0.47), reply 3. Nc3
  - 3... Nf6 (Good, pre-move ES 0.47), reply 4. cxd5
  - 4... exd5 (Good, pre-move ES 0.48), reply 5. Bf4
  - 5... Nh5 (Good, pre-move ES 0.49), reply 6. Be5
- **Answer:** all safe (every judged move is Good).

#### Window 4: allowed (length 5, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=1597152&ply=43
- **User rating:** 324 (pinned Maia Elo 600)
- **FEN before the lead-in:** `r1bqk3/pp2b1r1/2p5/8/n5p1/2P5/PP2QPPP/3RR1K1 b q - 2 22`
- **Lead-in:** 22... Nxb2
- **Judged user moves:**
  - 23. Rxd8+ (Good, pre-move ES 0.32), reply 23... Kxd8
- **FEN before the answer move:** `r1bk4/pp2b1r1/2p5/8/6p1/2P5/Pn2QPPP/4R1K1 w - - 0 24`
- **Answer:** blunder 24. Rd1+ (pre-move ES 0.32, ES after 0.08).
- **Refutation:** Nxd1.
- **Score inputs:** facepalm score 0.910, played prob 0.063, reply spread 4.03, played material 3 -2, mate ply n/a.
- **Missed inputs:** best material 3 3, missed gain 3, best move prob 0.512, pre-blunder spread 6.75.

#### Window 5: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=1920484&ply=28
- **User rating:** 175 (pinned Maia Elo 600)
- **FEN before the lead-in:** `r4rk1/ppp3pp/2n5/2p1p3/8/3PB2q/PPP1KP1P/R5QR w - - 4 15`
- **Lead-in:** 15. Bxc5
- **Judged user moves:**
  - 15... Rf7 (Good, pre-move ES 0.75), reply 16. Qg3
  - 16... Qh5+ (Good, pre-move ES 0.77), reply 17. Kd2
  - 17... e4 (Good, pre-move ES 0.78), reply 18. dxe4
  - 18... Rd8+ (Good, pre-move ES 0.88), reply 19. Kc1
  - 19... Qxc5 (Good, pre-move ES 0.89), reply 20. Rg1
- **Answer:** all safe (every judged move is Good).

#### Window 6: allowed (length 3, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=1918885&ply=52
- **User rating:** 273 (pinned Maia Elo 600)
- **FEN before the lead-in:** `r1bkr3/2p5/1p3PQp/p2pP3/3P4/P1P3Pq/7P/R3R1K1 w - - 1 27`
- **Lead-in:** 27. f7
- **Judged user moves:**
- **FEN before the answer move:** `r1bkr3/2p2P2/1p4Qp/p2pP3/3P4/P1P3Pq/7P/R3R1K1 b - - 0 27`
- **Answer:** blunder 27... Bf5 (pre-move ES 0.13, ES after 0.02).
- **Refutation:** fxe8=Q#.
- **Score inputs:** facepalm score 0.996, played prob 0.053, reply spread 6.15, played material 3 -5, mate ply 1.
- **Missed inputs:** best material 3 4, missed gain 4, best move prob 0.013, pre-blunder spread 4.52.

#### Window 7: herring (length 3, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2274977&ply=43
- **User rating:** 222 (pinned Maia Elo 600)
- **FEN before the lead-in:** `4rrk1/B4ppp/8/3P4/p2P4/6Pb/PP6/R3R1K1 b - - 0 22`
- **Lead-in:** 22... Rxe1+
- **Judged user moves:**
  - 23. Rxe1 (Good, pre-move ES 0.56), reply 23... Ra8
  - 24. Bc5 (Good, pre-move ES 0.62), reply 24... h6
  - 25. d6 (Good, pre-move ES 0.64), reply 25... Kh7
- **Answer:** all safe (every judged move is Good).

#### Window 8: allowed (length 5, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=2666223&ply=63
- **User rating:** 427 (pinned Maia Elo 600)
- **FEN before the lead-in:** `4R3/p1k5/1pp2q2/3p1B2/5P2/6P1/PPP4P/1K6 b - - 0 32`
- **Lead-in:** 32... Qxf5
- **Judged user moves:**
  - 33. Re7+ (Good, pre-move ES 0.18), reply 33... Kd6
  - 34. Rxa7 (Good, pre-move ES 0.19), reply 34... Qh5
- **FEN before the answer move:** `8/R7/1ppk4/3p3q/5P2/6P1/PPP4P/1K6 w - - 1 35`
- **Answer:** blunder 35. Ra3 (pre-move ES 0.18, ES after 0.02).
- **Refutation:** Qd1#.
- **Score inputs:** facepalm score 0.991, played prob 0.040, reply spread 4.83, played material 3 0, mate ply 1.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.053, pre-blunder spread 10.63.

#### Window 9: allowed (length 3, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=2446860&ply=22
- **User rating:** 630 (pinned Maia Elo 630)
- **FEN before the lead-in:** `r2qk2r/ppp3pp/4nn2/2p1NpB1/4P3/3P4/PPP2PPP/R2Q1RK1 w kq - 0 12`
- **Lead-in:** 12. exf5
- **Judged user moves:**
  - 12... Nxg5 (Good, pre-move ES 0.35), reply 13. Re1
  - 13... O-O (Good, pre-move ES 0.72), reply 14. Nf3
- **FEN before the answer move:** `r2q1rk1/ppp3pp/5n2/2p2Pn1/8/3P1N2/PPP2PPP/R2QR1K1 b - - 3 14`
- **Answer:** blunder 14... Nh3+ (pre-move ES 0.76, ES after 0.44).
- **Refutation:** gxh3.
- **Score inputs:** facepalm score 0.979, played prob 0.005, reply spread 1.48, played material 3 -3, mate ply n/a.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.050, pre-blunder spread 4.53.

#### Window 10: allowed (length 5, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=2444253&ply=59
- **User rating:** 667 (pinned Maia Elo 667)
- **FEN before the lead-in:** `2k5/p5pp/8/Pp6/1P1N2n1/6P1/r5BP/5RK1 b - - 3 30`
- **Lead-in:** 30... Ne3
- **Judged user moves:**
  - 31. Rf8+ (Good, pre-move ES 0.87), reply 31... Kd7
- **FEN before the answer move:** `5R2/p2k2pp/8/Pp6/1P1N4/4n1P1/r5BP/6K1 w - - 6 32`
- **Answer:** blunder 32. Nxb5 (pre-move ES 0.86, ES after 0.50).
- **Refutation:** Rxg2+.
- **Score inputs:** facepalm score 0.662, played prob 0.209, reply spread 4.08, played material 3 -2, mate ply n/a.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.057, pre-blunder spread 8.46.

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

- **Game:** https://flawchess.com/analysis?game_id=1871648&ply=27
- **User rating:** 300 (pinned Maia Elo 600)
- **FEN before the lead-in:** `2kr3r/ppp2p2/2nq1n2/3p1p1p/3P2P1/P1N1P2P/1PPQN1P1/R4RK1 b - - 0 14`
- **Lead-in:** 14... fxg4
- **Judged user moves:**
- **FEN before the answer move:** `2kr3r/ppp2p2/2nq1n2/3p3p/3P2p1/P1N1P2P/1PPQN1P1/R4RK1 w - - 0 15`
- **Answer:** blunder 15. Rxf6 (pre-move ES 0.55, ES after 0.28).
- **Refutation:** Qxf6.
- **Missed best move:** h4.
- **Score inputs:** facepalm score 0.940, played prob 0.023, reply spread 1.54, played material 3 -2, mate ply n/a.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.242, pre-blunder spread 8.61.

#### Window 13: mixed (length 5, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=1589702&ply=6
- **User rating:** 300 (pinned Maia Elo 600)
- **FEN before the lead-in:** `rnbqk2r/pppp1ppp/5n2/2b1p3/8/2NP2P1/PPP1PP1P/R1BQKBNR w KQkq - 1 4`
- **Lead-in:** 4. Bg5
- **Judged user moves:**
- **FEN before the answer move:** `rnbqk2r/pppp1ppp/5n2/2b1p1B1/8/2NP2P1/PPP1PP1P/R2QKBNR b KQkq - 2 4`
- **Answer:** blunder 4... Ne4 (pre-move ES 0.65, ES after 0.16).
- **Refutation:** Nxe4.
- **Missed best move:** Bxf2+.
- **Score inputs:** facepalm score 0.974, played prob 0.011, reply spread 3.75, played material 3 -3, mate ply n/a.
- **Missed inputs:** best material 3 1, missed gain 1, best move prob 0.008, pre-blunder spread 7.32.

#### Window 14: pure_miss (length 5, blunder at 5)

- **Game:** https://flawchess.com/analysis?game_id=2615745&ply=20
- **User rating:** 594 (pinned Maia Elo 600)
- **FEN before the lead-in:** `r1q1kb1r/p4ppp/n1p1pn2/1p1b4/4p3/1BQ5/PPPPNPPP/RNBK3R w kq - 0 11`
- **Lead-in:** 11. Bxd5
- **Judged user moves:**
  - 11... cxd5 (Good, pre-move ES 0.73), reply 12. Qxc8+
  - 12... Rxc8 (Good, pre-move ES 0.69), reply 13. h3
  - 13... Bc5 (Good, pre-move ES 0.71), reply 14. Nbc3
  - 14... b4 (Good, pre-move ES 0.69), reply 15. f3
- **FEN before the answer move:** `2r1k2r/p4ppp/n3pn2/2bp4/1p2p3/2N2P1P/PPPPN1P1/R1BK3R b k - 0 15`
- **Answer:** blunder 15... O-O (pre-move ES 0.86, ES after 0.70).
- **Missed best move:** bxc3.
- **Score inputs:** facepalm score 0.535, played prob 0.096, reply spread 7.62, played material 3 0, mate ply n/a.
- **Missed inputs:** best material 3 2, missed gain 2, best move prob 0.669, pre-blunder spread 3.87.

#### Window 15: allowed (length 4, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=2725025&ply=13
- **User rating:** 433 (pinned Maia Elo 600)
- **FEN before the lead-in:** `r1bqk1nr/ppp3pp/2n2p2/3NP3/8/5N2/PPPQPPPP/R3KB1R b KQkq - 0 7`
- **Lead-in:** 7... fxe5
- **Judged user moves:**
- **FEN before the answer move:** `r1bqk1nr/ppp3pp/2n5/3Np3/8/5N2/PPPQPPPP/R3KB1R w KQkq - 0 8`
- **Answer:** blunder 8. Nxe5 (pre-move ES 0.74, ES after 0.39).
- **Refutation:** Nxe5.
- **Score inputs:** facepalm score 0.687, played prob 0.131, reply spread 2.53, played material 3 -1, mate ply n/a.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.146, pre-blunder spread 11.95.

#### Window 16: herring (length 5, no blunder)

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

#### Window 17: herring (length 3, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=3174305&ply=7
- **User rating:** 700 (pinned Maia Elo 700)
- **FEN before the lead-in:** `rnb1kbnr/ppp1pppp/4q3/8/8/2N5/PPPPNPPP/R1BQKB1R b KQkq - 3 4`
- **Lead-in:** 4... c6
- **Judged user moves:**
  - 5. d4 (Good, pre-move ES 0.57), reply 5... a6
  - 6. g3 (Good, pre-move ES 0.61), reply 6... f5
  - 7. Bg2 (Good, pre-move ES 0.74), reply 7... Nf6
- **Answer:** all safe (every judged move is Good).

#### Window 18: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2447737&ply=36
- **User rating:** 691 (pinned Maia Elo 691)
- **FEN before the lead-in:** `r6r/pp1nk1bp/2p3b1/3p4/1P4N1/2P3N1/P4PPP/2KR1B1R w - - 1 19`
- **Lead-in:** 19. Kb2
- **Judged user moves:**
  - 19... a5 (Good, pre-move ES 0.70), reply 20. Bd3
  - 20... axb4 (Good, pre-move ES 0.80), reply 21. Bxg6
  - 21... Bxc3+ (Good, pre-move ES 0.82), reply 22. Kc2
  - 22... hxg6 (Good, pre-move ES 0.89), reply 23. Ne2
  - 23... Rxa2+ (Good, pre-move ES 0.88), reply 24. Kd3
- **Answer:** all safe (every judged move is Good).

#### Window 19: mixed (length 4, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=2515323&ply=10
- **User rating:** 212 (pinned Maia Elo 600)
- **FEN before the lead-in:** `r1bqk1nr/ppp1bppp/2n5/3p4/P7/2P1Q3/1P2PPPP/RNB1KBNR w KQkq - 3 6`
- **Lead-in:** 6. b4
- **Judged user moves:**
  - 6... Nf6 (Good, pre-move ES 0.68), reply 7. b5
  - 7... Ng4 (Good, pre-move ES 0.65), reply 8. Qg3
- **FEN before the answer move:** `r1bqk2r/ppp1bppp/2n5/1P1p4/P5n1/2P3Q1/4PPPP/RNB1KBNR b KQkq - 2 8`
- **Answer:** blunder 8... f5 (pre-move ES 0.80, ES after 0.54).
- **Refutation:** bxc6.
- **Missed best move:** Bh4.
- **Score inputs:** facepalm score 0.955, played prob 0.005, reply spread 4.92, played material 3 -2, mate ply n/a.
- **Missed inputs:** best material 3 6, missed gain 5, best move prob 0.043, pre-blunder spread 8.47.

#### Window 20: allowed (length 3, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=992964&ply=51
- **User rating:** 680 (pinned Maia Elo 680)
- **FEN before the lead-in:** `2q2rk1/5pp1/2N1b2p/8/3QP3/2R4P/1P3PP1/6K1 b - - 4 26`
- **Lead-in:** 26... Qa8
- **Judged user moves:**
  - 27. Kh2 (Good, pre-move ES 0.77), reply 27... Qa1
  - 28. Ne7+ (Good, pre-move ES 0.85), reply 28... Kh7
- **FEN before the answer move:** `5r2/4Nppk/4b2p/8/3QP3/2R4P/1P3PPK/q7 w - - 9 29`
- **Answer:** blunder 29. e5 (pre-move ES 0.81, ES after 0.54).
- **Refutation:** Qxb2.
- **Score inputs:** facepalm score 0.595, played prob 0.160, reply spread 3.19, played material 3 -1, mate ply n/a.
- **Missed inputs:** best material 3 3, missed gain 3, best move prob 0.229, pre-blunder spread 14.42.

### 800-1199

#### Window 1: allowed (length 3, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=2589144&ply=42
- **User rating:** 1023 (pinned Maia Elo 1023)
- **FEN before the lead-in:** `rn3rk1/1p1b4/p4pp1/3p2Np/1P1P3Q/P7/3b1PPP/R4RK1 w - - 0 22`
- **Lead-in:** 22. f4
- **Judged user moves:**
  - 22... fxg5 (Good, pre-move ES 0.27), reply 23. Qxg5
- **FEN before the answer move:** `rn3rk1/1p1b4/p5p1/3p2Qp/1P1P1P2/P7/3b2PP/R4RK1 b - - 0 23`
- **Answer:** blunder 23... Bb5 (pre-move ES 0.31, ES after 0.03).
- **Refutation:** Qxg6+.
- **Score inputs:** facepalm score 0.642, played prob 0.052, reply spread 4.78, played material 3 -2, mate ply n/a.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.196, pre-blunder spread 10.26.

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

- **Game:** https://flawchess.com/analysis?game_id=1075803&ply=12
- **User rating:** 527 (pinned Maia Elo 1042)
- **FEN before the lead-in:** `rn1qkb1r/pp3ppp/2p2n2/3p4/3Pp1b1/2P1P3/PP3PPP/RNBQKBNR w KQkq - 1 7`
- **Lead-in:** 7. f3
- **Judged user moves:**
  - 7... Bf5 (Good, pre-move ES 0.60), reply 8. f4
  - 8... Bd6 (Good, pre-move ES 0.64), reply 9. h3
- **FEN before the answer move:** `rn1qk2r/pp3ppp/2pb1n2/3p1b2/3PpP2/2P1P2P/PP4P1/RNBQKBNR b KQkq - 0 9`
- **Answer:** blunder 9... Nh5 (pre-move ES 0.66, ES after 0.27).
- **Refutation:** Qxh5.
- **Score inputs:** facepalm score 0.886, played prob 0.017, reply spread 3.92, played material 3 6, mate ply n/a.
- **Missed inputs:** best material 3 1, missed gain 0, best move prob 0.053, pre-blunder spread 5.56.

#### Window 4: allowed (length 5, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=2668684&ply=19
- **User rating:** 1278 (pinned Maia Elo 1083)
- **FEN before the lead-in:** `r3k2r/1ppb1ppp/p1nbpq1n/3p4/BP1P4/P1B1PN2/2P2PPP/RN1QK2R b KQkq - 1 10`
- **Lead-in:** 10... b5
- **Judged user moves:**
  - 11. Bb3 (Good, pre-move ES 0.46), reply 11... a5
- **FEN before the answer move:** `r3k2r/2pb1ppp/2nbpq1n/pp1p4/1P1P4/PBB1PN2/2P2PPP/RN1QK2R w KQkq - 0 12`
- **Answer:** blunder 12. a4 (pre-move ES 0.43, ES after 0.25).
- **Refutation:** axb4.
- **Score inputs:** facepalm score 0.619, played prob 0.043, reply spread 3.15, played material 3 -1, mate ply n/a.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.164, pre-blunder spread 5.87.

#### Window 5: pure_miss (length 4, blunder at 4)

- **Game:** https://flawchess.com/analysis?game_id=3256256&ply=11
- **User rating:** 925 (pinned Maia Elo 1132)
- **FEN before the lead-in:** `r1bqkb1r/ppp2ppp/2n1p3/3N4/3P4/5N2/PPP2PPP/R1BQKB1R b KQkq - 0 6`
- **Lead-in:** 6... Qxd5
- **Judged user moves:**
  - 7. Be3 (Good, pre-move ES 0.58), reply 7... Bd6
  - 8. Bd3 (Good, pre-move ES 0.57), reply 8... O-O
  - 9. O-O (Good, pre-move ES 0.56), reply 9... e5
- **FEN before the answer move:** `r1b2rk1/ppp2ppp/2nb4/3qp3/3P4/3BBN2/PPP2PPP/R2Q1RK1 w - - 0 10`
- **Answer:** blunder 10. c4 (pre-move ES 0.85, ES after 0.67).
- **Missed best move:** dxe5.
- **Score inputs:** facepalm score 0.504, played prob 0.189, reply spread 1.57, played material 3 0, mate ply n/a.
- **Missed inputs:** best material 3 3, missed gain 3, best move prob 0.611, pre-blunder spread 4.03.

#### Window 6: mixed (length 5, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=2607323&ply=14
- **User rating:** 992 (pinned Maia Elo 992)
- **FEN before the lead-in:** `r1b1kb1r/p1p2ppp/5n2/1p1qp1N1/3n4/2PB4/PP1P1PPP/RNBQK2R w KQkq - 0 8`
- **Lead-in:** 8. O-O
- **Judged user moves:**
- **FEN before the answer move:** `r1b1kb1r/p1p2ppp/5n2/1p1qp1N1/3n4/2PB4/PP1P1PPP/RNBQ1RK1 b kq - 1 8`
- **Answer:** blunder 8... Qd7 (pre-move ES 0.61, ES after 0.23).
- **Refutation:** cxd4.
- **Missed best move:** Bb7.
- **Score inputs:** facepalm score 0.972, played prob 0.000, reply spread 2.79, played material 3 -2, mate ply n/a.
- **Missed inputs:** best material 3 n/a, missed gain n/a, best move prob 0.557, pre-blunder spread 5.19.

#### Window 7: allowed (length 3, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=2634463&ply=47
- **User rating:** 1037 (pinned Maia Elo 1037)
- **FEN before the lead-in:** `r5kr/pR2Rpp1/1n1B3p/8/8/3P1P2/PP3P1P/6K1 b - - 6 24`
- **Lead-in:** 24... Nc8
- **Judged user moves:**
- **FEN before the answer move:** `r1n3kr/pR2Rpp1/3B3p/8/8/3P1P2/PP3P1P/6K1 w - - 7 25`
- **Answer:** blunder 25. Ba3 (pre-move ES 0.84, ES after 0.50).
- **Refutation:** Nxe7.
- **Score inputs:** facepalm score 0.983, played prob 0.004, reply spread 1.76, played material 3 -2, mate ply n/a.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.303, pre-blunder spread 3.95.

#### Window 8: allowed (length 5, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=2582436&ply=36
- **User rating:** 809 (pinned Maia Elo 1063)
- **FEN before the lead-in:** `r3k2r/pp2bppp/2n1p3/3p3P/2p2P1q/P3P1Q1/2PPN1P1/1N3RK1 w kq - 1 19`
- **Lead-in:** 19. Qxg7
- **Judged user moves:**
- **FEN before the answer move:** `r3k2r/pp2bpQp/2n1p3/3p3P/2p2P1q/P3P3/2PPN1P1/1N3RK1 b kq - 0 19`
- **Answer:** blunder 19... Qxh5 (pre-move ES 0.88, ES after 0.63).
- **Refutation:** Qxh8+.
- **Score inputs:** facepalm score 0.998, played prob 0.019, reply spread 1.35, played material 3 -4, mate ply n/a.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.028, pre-blunder spread 3.51.

#### Window 9: allowed (length 5, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=1164791&ply=28
- **User rating:** 679 (pinned Maia Elo 1130)
- **FEN before the lead-in:** `r1bq1rk1/1pp3bp/p2p1np1/3Pp3/1P2Pp2/2P3P1/P6Q/RNB1KB1R w KQ - 0 15`
- **Lead-in:** 15. gxf4
- **Judged user moves:**
- **FEN before the answer move:** `r1bq1rk1/1pp3bp/p2p1np1/3Pp3/1P2PP2/2P5/P6Q/RNB1KB1R b KQ - 0 15`
- **Answer:** blunder 15... Rf7 (pre-move ES 0.84, ES after 0.69).
- **Refutation:** fxe5.
- **Score inputs:** facepalm score 0.509, played prob 0.005, reply spread 4.02, played material 3 0, mate ply n/a.
- **Missed inputs:** best material 3 1, missed gain 1, best move prob 0.416, pre-blunder spread 7.76.

#### Window 10: herring (length 3, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2747390&ply=0
- **User rating:** 1029 (pinned Maia Elo 1029)
- **FEN before the lead-in:** `rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1`
- **Lead-in:** 1. e4
- **Judged user moves:**
  - 1... d6 (Good, pre-move ES 0.47), reply 2. d4
  - 2... Nf6 (Good, pre-move ES 0.45), reply 3. Bb5+
  - 3... c6 (Good, pre-move ES 0.48), reply 4. Nc3
- **Answer:** all safe (every judged move is Good).

#### Window 11: allowed (length 5, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=2222842&ply=24
- **User rating:** 580 (pinned Maia Elo 1066)
- **FEN before the lead-in:** `2kr3r/1ppbqppp/p3p3/n2pPn2/B2P4/P1N2N1P/1PPQ1PP1/2KR3R w - - 3 13`
- **Lead-in:** 13. Bxd7+
- **Judged user moves:**
  - 13... Qxd7 (Good, pre-move ES 0.48), reply 14. Kb1
  - 14... Nc4 (Good, pre-move ES 0.48), reply 15. Qd3
- **FEN before the answer move:** `2kr3r/1ppq1ppp/p3p3/3pPn2/2nP4/P1NQ1N1P/1PP2PP1/1K1R3R b - - 3 15`
- **Answer:** blunder 15... Qb5 (pre-move ES 0.48, ES after 0.13).
- **Refutation:** Nxb5.
- **Score inputs:** facepalm score 0.993, played prob 0.050, reply spread 3.88, played material 3 -6, mate ply n/a.
- **Missed inputs:** best material 3 n/a, missed gain n/a, best move prob 0.033, pre-blunder spread 10.42.

#### Window 12: allowed (length 3, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=550020&ply=12
- **User rating:** 792 (pinned Maia Elo 1196)
- **FEN before the lead-in:** `r1bk1bnr/ppNp1p1p/2n3p1/4p3/8/4Pq2/PPPP1PPP/R1B1KBNR w KQ - 1 7`
- **Lead-in:** 7. Nxf3
- **Judged user moves:**
- **FEN before the answer move:** `r1bk1bnr/ppNp1p1p/2n3p1/4p3/8/4PN2/PPPP1PPP/R1B1KB1R b KQ - 0 7`
- **Answer:** blunder 7... Rb8 (pre-move ES 0.79, ES after 0.35).
- **Refutation:** Nd5.
- **Score inputs:** facepalm score 0.940, played prob 0.003, reply spread 2.13, played material 3 0, mate ply n/a.
- **Missed inputs:** best material 3 4, missed gain 4, best move prob 0.994, pre-blunder spread 1.05.

#### Window 13: allowed (length 3, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=2336806&ply=21
- **User rating:** 1384 (pinned Maia Elo 1185)
- **FEN before the lead-in:** `r3k2r/pp2nppp/2n5/2b1Pb2/N7/5N2/PP2KPPP/R1B2B1R b kq - 6 11`
- **Lead-in:** 11... Nd4+
- **Judged user moves:**
  - 12. Nxd4 (Good, pre-move ES 0.44), reply 12... Bxd4
  - 13. f4 (Good, pre-move ES 0.44), reply 13... Nd5
- **FEN before the answer move:** `r3k2r/pp3ppp/8/3nPb2/N2b1P2/8/PP2K1PP/R1B2B1R w kq - 1 14`
- **Answer:** blunder 14. h3 (pre-move ES 0.47, ES after 0.31).
- **Refutation:** b5.
- **Score inputs:** facepalm score 0.503, played prob 0.115, reply spread 5.47, played material 3 -3, mate ply n/a.
- **Missed inputs:** best material 3 3, missed gain 3, best move prob 0.225, pre-blunder spread 8.49.

#### Window 14: allowed (length 5, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=1600093&ply=60
- **User rating:** 636 (pinned Maia Elo 1153)
- **FEN before the lead-in:** `r4rk1/pp4p1/3N1p2/8/3pK1R1/5P2/PPP5/R6q w - - 6 31`
- **Lead-in:** 31. Rxh1
- **Judged user moves:**
  - 31... Rfd8 (Good, pre-move ES 0.16), reply 32. Kd5
- **FEN before the answer move:** `r2r2k1/pp4p1/3N1p2/3K4/3p2R1/5P2/PPP5/7R b - - 2 32`
- **Answer:** blunder 32... Kf8 (pre-move ES 0.16, ES after 0.02).
- **Refutation:** Rh8+.
- **Score inputs:** facepalm score 0.990, played prob 0.106, reply spread 5.20, played material 3 -1, mate ply 3.
- **Missed inputs:** best material 3 -2, missed gain 0, best move prob 0.242, pre-blunder spread 7.10.

#### Window 15: allowed (length 4, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=3135409&ply=48
- **User rating:** 724 (pinned Maia Elo 1158)
- **FEN before the lead-in:** `6k1/p5pp/1p6/2p1Np2/2P5/1P6/r4PKP/B7 w - - 0 25`
- **Lead-in:** 25. Bc3
- **Judged user moves:**
  - 25... Ra3 (Good, pre-move ES 0.82), reply 26. Nc6
  - 26... Rxb3 (Good, pre-move ES 0.84), reply 27. Be5
- **FEN before the answer move:** `6k1/p5pp/1pN5/2p1Bp2/2P5/1r6/5PKP/8 b - - 1 27`
- **Answer:** blunder 27... Rb1 (pre-move ES 0.86, ES after 0.60).
- **Refutation:** Nxa7.
- **Score inputs:** facepalm score 0.788, played prob 0.011, reply spread 1.93, played material 3 0, mate ply n/a.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.566, pre-blunder spread 5.22.

#### Window 16: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2525022&ply=1
- **User rating:** 856 (pinned Maia Elo 1088)
- **FEN before the lead-in:** `rnbqkbnr/pppppppp/8/8/3P4/8/PPP1PPPP/RNBQKBNR b KQkq - 0 1`
- **Lead-in:** 1... d5
- **Judged user moves:**
  - 2. Bf4 (Good, pre-move ES 0.53), reply 2... e6
  - 3. e3 (Good, pre-move ES 0.51), reply 3... c6
  - 4. Bd3 (Good, pre-move ES 0.53), reply 4... Nd7
  - 5. Nc3 (Good, pre-move ES 0.56), reply 5... b5
  - 6. Nf3 (Good, pre-move ES 0.55), reply 6... b4
- **Answer:** all safe (every judged move is Good).

#### Window 17: herring (length 4, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=1666087&ply=37
- **User rating:** 1335 (pinned Maia Elo 1140)
- **FEN before the lead-in:** `5r1k/2r2pnp/p3b1pn/1p6/1N2P3/1P5P/P1PNBPP1/R4RK1 b - - 3 19`
- **Lead-in:** 19... Rd8
- **Judged user moves:**
  - 20. Bd3 (Good, pre-move ES 0.77), reply 20... f5
  - 21. Nxa6 (Good, pre-move ES 0.85), reply 21... Rcd7
  - 22. Nc5 (Good, pre-move ES 0.87), reply 22... Rc7
  - 23. Na6 (Good, pre-move ES 0.88), reply 23... Rcd7
- **Answer:** all safe (every judged move is Good).

#### Window 18: herring (length 3, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2855249&ply=48
- **User rating:** 964 (pinned Maia Elo 1157)
- **FEN before the lead-in:** `3r2k1/3N1pp1/p2np1bp/3p4/3P4/6P1/PP3PBP/2R3K1 w - - 1 25`
- **Lead-in:** 25. Ne5
- **Judged user moves:**
  - 25... Bf5 (Good, pre-move ES 0.47), reply 26. g4
  - 26... Bh7 (Good, pre-move ES 0.42), reply 27. h4
  - 27... f6 (Good, pre-move ES 0.44), reply 28. Nc6
- **Answer:** all safe (every judged move is Good).

#### Window 19: allowed (length 3, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=2866888&ply=13
- **User rating:** 829 (pinned Maia Elo 829)
- **FEN before the lead-in:** `r1b1k1nr/ppp2ppp/2np1q2/2b5/3NP3/N1P1B3/PP3PPP/R2QKB1R b KQkq - 1 7`
- **Lead-in:** 7... Nh6
- **Judged user moves:**
  - 8. h3 (Good, pre-move ES 0.56), reply 8... Be6
- **FEN before the answer move:** `r3k2r/ppp2ppp/2npbq1n/2b5/3NP3/N1P1B2P/PP3PP1/R2QKB1R w KQkq - 1 9`
- **Answer:** blunder 9. b3 (pre-move ES 0.60, ES after 0.24).
- **Refutation:** Bxa3.
- **Score inputs:** facepalm score 0.678, played prob 0.003, reply spread 9.13, played material 3 0, mate ply n/a.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.040, pre-blunder spread 14.84.

#### Window 20: mixed (length 3, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=2425060&ply=39
- **User rating:** 971 (pinned Maia Elo 971)
- **FEN before the lead-in:** `r4rk1/p3q1pp/npp1p3/4P2Q/1P1pNP2/P2P4/6PP/R4RK1 b - - 1 20`
- **Lead-in:** 20... g6
- **Judged user moves:**
- **FEN before the answer move:** `r4rk1/p3q2p/npp1p1p1/4P2Q/1P1pNP2/P2P4/6PP/R4RK1 w - - 0 21`
- **Answer:** blunder 21. Nf6+ (pre-move ES 0.66, ES after 0.19).
- **Refutation:** Qxf6.
- **Missed best move:** Qg4.
- **Score inputs:** facepalm score 0.894, played prob 0.137, reply spread 3.89, played material 3 -3, mate ply n/a.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.093, pre-blunder spread 4.43.

### 1200-1599

#### Window 1: allowed (length 5, blunder at 5)

- **Game:** https://flawchess.com/analysis?game_id=762736&ply=42
- **User rating:** 1529 (pinned Maia Elo 1529)
- **FEN before the lead-in:** `r4rk1/pp3pb1/2q2np1/6p1/6b1/1P1B4/P1PQ1PPP/1R2R1K1 w - - 0 22`
- **Lead-in:** 22. Qxg5
- **Judged user moves:**
  - 22... Bh5 (Good, pre-move ES 0.88), reply 23. h3
  - 23... Rad8 (Good, pre-move ES 0.86), reply 24. g4
  - 24... Rd5 (Good, pre-move ES 0.86), reply 25. Qf4
  - 25... Nxg4 (Good, pre-move ES 0.85), reply 26. hxg4
- **FEN before the answer move:** `5rk1/pp3pb1/2q3p1/3r3b/5QP1/1P1B4/P1P2P2/1R2R1K1 b - - 0 26`
- **Answer:** blunder 26... Rg5 (pre-move ES 0.83, ES after 0.16).
- **Refutation:** Qxg5.
- **Score inputs:** facepalm score 0.997, played prob 0.017, reply spread 2.03, played material 3 -5, mate ply n/a.
- **Missed inputs:** best material 3 9, missed gain 5, best move prob 0.070, pre-blunder spread 6.54.

#### Window 2: allowed (length 5, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=1083629&ply=23
- **User rating:** 975 (pinned Maia Elo 1399)
- **FEN before the lead-in:** `r2q1rk1/ppp1ppbp/2np2p1/3B4/P3P3/2P2Q2/1P3PPP/1RB2RK1 b - - 0 12`
- **Lead-in:** 12... e6
- **Judged user moves:**
  - 13. Bxc6 (Good, pre-move ES 0.43), reply 13... bxc6
  - 14. b4 (Good, pre-move ES 0.39), reply 14... d5
- **FEN before the answer move:** `r2q1rk1/p1p2pbp/2p1p1p1/3p4/PP2P3/2P2Q2/5PPP/1RB2RK1 w - - 0 15`
- **Answer:** blunder 15. e5 (pre-move ES 0.44, ES after 0.28).
- **Refutation:** Bxe5.
- **Score inputs:** facepalm score 0.775, played prob 0.016, reply spread 3.09, played material 3 -1, mate ply n/a.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.091, pre-blunder spread 6.02.

#### Window 3: herring (length 3, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=1550805&ply=19
- **User rating:** 1576 (pinned Maia Elo 1576)
- **FEN before the lead-in:** `r1bqk2r/pp2n1pp/2n1pp2/1B1p4/3P1B2/2P1PN2/P4PPP/R2QK2R b KQkq - 2 10`
- **Lead-in:** 10... O-O
- **Judged user moves:**
  - 11. O-O (Good, pre-move ES 0.56), reply 11... a6
  - 12. Bd3 (Good, pre-move ES 0.59), reply 12... b5
  - 13. a4 (Good, pre-move ES 0.64), reply 13... Bb7
- **Answer:** all safe (every judged move is Good).

#### Window 4: herring (length 4, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=3254274&ply=49
- **User rating:** 858 (pinned Maia Elo 1278)
- **FEN before the lead-in:** `r6q/1kpQ2pp/pp3b2/4p3/4P3/3PB3/PP1K2PP/n4R2 b - - 3 25`
- **Lead-in:** 25... Rd8
- **Judged user moves:**
  - 26. Qf7 (Good, pre-move ES 0.36), reply 26... Nb3+
  - 27. axb3 (Good, pre-move ES 0.46), reply 27... Rf8
  - 28. Qd7 (Good, pre-move ES 0.43), reply 28... Rd8
  - 29. Qf7 (Good, pre-move ES 0.45), reply 29... h6
- **Answer:** all safe (every judged move is Good).

#### Window 5: herring (length 3, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2821317&ply=7
- **User rating:** 1742 (pinned Maia Elo 1539)
- **FEN before the lead-in:** `rnbqkbnr/pp3ppp/4p3/2pp4/3PP3/2N1B3/PPP2PPP/R2QKBNR b KQkq - 1 4`
- **Lead-in:** 4... cxd4
- **Judged user moves:**
  - 5. Bxd4 (Good, pre-move ES 0.54), reply 5... Nc6
  - 6. exd5 (Good, pre-move ES 0.54), reply 6... exd5
  - 7. Nf3 (Good, pre-move ES 0.57), reply 7... Nf6
- **Answer:** all safe (every judged move is Good).

#### Window 6: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2378523&ply=0
- **User rating:** 984 (pinned Maia Elo 1406)
- **FEN before the lead-in:** `rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1`
- **Lead-in:** 1. e4
- **Judged user moves:**
  - 1... e5 (Good, pre-move ES 0.47), reply 2. d3
  - 2... Nc6 (Good, pre-move ES 0.52), reply 3. Be2
  - 3... Nf6 (Good, pre-move ES 0.51), reply 4. Nf3
  - 4... Bc5 (Good, pre-move ES 0.51), reply 5. O-O
  - 5... d6 (Good, pre-move ES 0.50), reply 6. Be3
- **Answer:** all safe (every judged move is Good).

#### Window 7: allowed (length 4, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=2052322&ply=19
- **User rating:** 859 (pinned Maia Elo 1280)
- **FEN before the lead-in:** `rnb1k2r/pp1pqppp/1bp5/4P1B1/2BP2n1/2N2N2/PPP3PP/R2Q1K1R b kq - 2 10`
- **Lead-in:** 10... f6
- **Judged user moves:**
  - 11. exf6 (Good, pre-move ES 0.66), reply 11... gxf6
- **FEN before the answer move:** `rnb1k2r/pp1pq2p/1bp2p2/6B1/2BP2n1/2N2N2/PPP3PP/R2Q1K1R w kq - 0 12`
- **Answer:** blunder 12. Bh4 (pre-move ES 0.75, ES after 0.23).
- **Refutation:** Ne3+.
- **Score inputs:** facepalm score 0.733, played prob 0.510, reply spread 3.17, played material 3 -6, mate ply n/a.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.050, pre-blunder spread 6.48.

#### Window 8: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2680536&ply=17
- **User rating:** 1346 (pinned Maia Elo 1346)
- **FEN before the lead-in:** `r1b1kb1r/pppq1ppp/2B5/4P3/4Q3/5N2/PPP2PPP/RNB1K2R b KQkq - 0 9`
- **Lead-in:** 9... bxc6
- **Judged user moves:**
  - 10. O-O (Good, pre-move ES 0.88), reply 10... Bc5
  - 11. Nc3 (Good, pre-move ES 0.89), reply 11... O-O
  - 12. Be3 (Good, pre-move ES 0.89), reply 12... Bxe3
  - 13. Qxe3 (Good, pre-move ES 0.89), reply 13... Re8
  - 14. Rad1 (Good, pre-move ES 0.89), reply 14... Qe6
- **Answer:** all safe (every judged move is Good).

#### Window 9: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2850126&ply=11
- **User rating:** 1065 (pinned Maia Elo 1243)
- **FEN before the lead-in:** `r1bqkbnr/3p1ppp/p1n1p3/1pp5/4PP2/1BNP4/PPP3PP/R1BQK1NR b KQkq - 1 6`
- **Lead-in:** 6... Nd4
- **Judged user moves:**
  - 7. Nf3 (Good, pre-move ES 0.50), reply 7... Nxb3
  - 8. axb3 (Good, pre-move ES 0.52), reply 8... Bb7
  - 9. Be3 (Good, pre-move ES 0.52), reply 9... Be7
  - 10. O-O (Good, pre-move ES 0.48), reply 10... Nf6
  - 11. e5 (Good, pre-move ES 0.48), reply 11... Ng4
- **Answer:** all safe (every judged move is Good).

#### Window 10: allowed (length 4, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=478946&ply=21
- **User rating:** 1217 (pinned Maia Elo 1409)
- **FEN before the lead-in:** `r3kb1r/p3pp2/2pq1n1p/2p1Nbp1/3p1P2/1P1PP1P1/PBPN3P/R2QK2R b KQkq - 1 11`
- **Lead-in:** 11... dxe3
- **Judged user moves:**
  - 12. Ndc4 (Good, pre-move ES 0.66), reply 12... Qd5
- **FEN before the answer move:** `r3kb1r/p3pp2/2p2n1p/2pqNbp1/2N2P2/1P1Pp1P1/PBP4P/R2QK2R w KQkq - 2 13`
- **Answer:** blunder 13. Nxe3 (pre-move ES 0.71, ES after 0.16).
- **Refutation:** Qxh1+.
- **Score inputs:** facepalm score 0.984, played prob 0.225, reply spread 1.64, played material 3 -4, mate ply n/a.
- **Missed inputs:** best material 3 1, missed gain 1, best move prob 0.130, pre-blunder spread 7.87.

#### Window 11: pure_miss (length 3, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=2613673&ply=69
- **User rating:** 1500 (pinned Maia Elo 1317)
- **FEN before the lead-in:** `3r4/pp1P2k1/5Rp1/5bB1/8/nP6/P1r2RPP/6K1 b - - 4 35`
- **Lead-in:** 35... Rxf2
- **Judged user moves:**
  - 36. Kxf2 (Good, pre-move ES 0.18), reply 36... Rxd7
  - 37. g3 (Good, pre-move ES 0.17), reply 37... Rd8
- **FEN before the answer move:** `3r4/pp4k1/5Rp1/5bB1/8/nP4P1/P4K1P/8 w - - 1 38`
- **Answer:** blunder 38. g4 (pre-move ES 0.76, ES after 0.23).
- **Missed best move:** Rxf5.
- **Score inputs:** facepalm score 0.600, played prob 0.023, reply spread 5.03, played material 3 0, mate ply n/a.
- **Missed inputs:** best material 3 3, missed gain 3, best move prob 0.452, pre-blunder spread 6.58.

#### Window 12: allowed (length 3, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=2964477&ply=49
- **User rating:** 1372 (pinned Maia Elo 1372)
- **FEN before the lead-in:** `1r2r1k1/2q3p1/2p1p2p/pp1p4/8/2PB2P1/PPQ1R3/4R2K b - - 0 25`
- **Lead-in:** 25... Qxg3
- **Judged user moves:**
  - 26. Bh7+ (Good, pre-move ES 0.52), reply 26... Kh8
- **FEN before the answer move:** `1r2r2k/6pB/2p1p2p/pp1p4/8/2P3q1/PPQ1R3/4R2K w - - 2 27`
- **Answer:** blunder 27. Rg2 (pre-move ES 0.50, ES after 0.08).
- **Refutation:** Qxe1+.
- **Score inputs:** facepalm score 0.990, played prob 0.139, reply spread 3.10, played material 3 -5, mate ply n/a.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.181, pre-blunder spread 7.33.

#### Window 13: allowed (length 3, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=2954073&ply=42
- **User rating:** 1454 (pinned Maia Elo 1263)
- **FEN before the lead-in:** `r1q2rk1/pR4pp/Q3pp2/2bpPn2/5P2/2N5/P3N1PP/2B2R1K w - - 4 22`
- **Lead-in:** 22. Bd2
- **Judged user moves:**
  - 22... Rb8 (Good, pre-move ES 0.49), reply 23. Rfb1
- **FEN before the answer move:** `1rq2rk1/pR4pp/Q3pp2/2bpPn2/5P2/2N5/P2BN1PP/1R5K b - - 7 23`
- **Answer:** blunder 23... Rf7 (pre-move ES 0.48, ES after 0.04).
- **Refutation:** Rxb8.
- **Score inputs:** facepalm score 0.998, played prob 0.032, reply spread 1.88, played material 3 -5, mate ply n/a.
- **Missed inputs:** best material 3 1, missed gain 1, best move prob 0.180, pre-blunder spread 4.05.

#### Window 14: allowed (length 4, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=1311329&ply=38
- **User rating:** 1199 (pinned Maia Elo 1394)
- **FEN before the lead-in:** `r1b2r1k/1p5p/p3p1p1/1Nq1bp2/1nB5/5NP1/P3QP1P/R4RK1 w - - 0 20`
- **Lead-in:** 20. Na3
- **Judged user moves:**
  - 20... Bxa1 (Good, pre-move ES 0.78), reply 21. Rxa1
  - 21... b5 (Good, pre-move ES 0.77), reply 22. Bxe6
- **FEN before the answer move:** `r1b2r1k/7p/p3B1p1/1pq2p2/1n6/N4NP1/P3QP1P/R5K1 b - - 0 22`
- **Answer:** blunder 22... Qc6 (pre-move ES 0.84, ES after 0.02).
- **Refutation:** Qe5+.
- **Score inputs:** facepalm score 0.998, played prob 0.001, reply spread 4.84, played material 3 0, mate ply 3.
- **Missed inputs:** best material 3 3, missed gain 3, best move prob 0.685, pre-blunder spread 2.55.

#### Window 15: allowed (length 4, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=2278844&ply=25
- **User rating:** 1580 (pinned Maia Elo 1580)
- **FEN before the lead-in:** `rnb1qrk1/pp4pp/2p1p3/3pNp1n/3P1B2/P1PBPQ2/2P2PPP/R4RK1 b - - 5 13`
- **Lead-in:** 13... Nxf4
- **Judged user moves:**
  - 14. exf4 (Good, pre-move ES 0.59), reply 14... Nd7
  - 15. Kh1 (Good, pre-move ES 0.56), reply 15... Nf6
- **FEN before the answer move:** `r1b1qrk1/pp4pp/2p1pn2/3pNp2/3P1P2/P1PB1Q2/2P2PPP/R4R1K w - - 3 16`
- **Answer:** blunder 16. g4 (pre-move ES 0.59, ES after 0.43).
- **Refutation:** Nxg4.
- **Score inputs:** facepalm score 0.510, played prob 0.119, reply spread 3.18, played material 3 -1, mate ply n/a.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.007, pre-blunder spread 10.04.

#### Window 16: pure_miss (length 3, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=2695267&ply=54
- **User rating:** 1463 (pinned Maia Elo 1274)
- **FEN before the lead-in:** `r5k1/5ppp/2n1p3/3p4/3P4/2K2NB1/rR4PP/1R6 w - - 2 28`
- **Lead-in:** 28. Ne5
- **Judged user moves:**
- **FEN before the answer move:** `r5k1/5ppp/2n1p3/3pN3/3P4/2K3B1/rR4PP/1R6 b - - 3 28`
- **Answer:** blunder 28... Nxe5 (pre-move ES 0.42, ES after 0.02).
- **Missed best move:** R8a3+.
- **Score inputs:** facepalm score 0.992, played prob 0.093, reply spread 3.30, played material 3 3, mate ply 3.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.300, pre-blunder spread 4.30.

#### Window 17: allowed (length 3, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=2550971&ply=10
- **User rating:** 1142 (pinned Maia Elo 1345)
- **FEN before the lead-in:** `rn1qkb1r/ppp2ppp/5n2/4p3/3pP1b1/3P1N2/PPP1BP1P/RNBQK2R w KQkq - 0 6`
- **Lead-in:** 6. Nxe5
- **Judged user moves:**
- **FEN before the answer move:** `rn1qkb1r/ppp2ppp/5n2/4N3/3pP1b1/3P4/PPP1BP1P/RNBQK2R b KQkq - 0 6`
- **Answer:** blunder 6... c6 (pre-move ES 0.51, ES after 0.19).
- **Refutation:** Nxg4.
- **Score inputs:** facepalm score 0.986, played prob 0.000, reply spread 2.32, played material 3 -3, mate ply n/a.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.860, pre-blunder spread 1.95.

#### Window 18: allowed (length 5, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=2075443&ply=23
- **User rating:** 1305 (pinned Maia Elo 1466)
- **FEN before the lead-in:** `rnbq1rk1/5pbp/p3p1p1/1ppp1n2/5P2/1PN1PN1Q/PBPPB1PP/1R3RK1 b - - 3 12`
- **Lead-in:** 12... e5
- **Judged user moves:**
- **FEN before the answer move:** `rnbq1rk1/5pbp/p5p1/1ppppn2/5P2/1PN1PN1Q/PBPPB1PP/1R3RK1 w - - 0 13`
- **Answer:** blunder 13. fxe5 (pre-move ES 0.48, ES after 0.27).
- **Refutation:** Nxe3.
- **Score inputs:** facepalm score 0.500, played prob 0.243, reply spread 2.06, played material 3 -2, mate ply n/a.
- **Missed inputs:** best material 3 n/a, missed gain n/a, best move prob 0.217, pre-blunder spread 5.32.

#### Window 19: mixed (length 5, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=2138305&ply=51
- **User rating:** 1383 (pinned Maia Elo 1543)
- **FEN before the lead-in:** `r5k1/1p3ppp/p1q5/3P4/8/PP2P1B1/5RPP/3R2K1 b - - 0 26`
- **Lead-in:** 26... Qc3
- **Judged user moves:**
- **FEN before the answer move:** `r5k1/1p3ppp/p7/3P4/8/PPq1P1B1/5RPP/3R2K1 w - - 1 27`
- **Answer:** blunder 27. b4 (pre-move ES 0.70, ES after 0.49).
- **Refutation:** Rd8.
- **Missed best move:** d6.
- **Score inputs:** facepalm score 0.573, played prob 0.013, reply spread 2.87, played material 3 0, mate ply n/a.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.709, pre-blunder spread 3.37.

#### Window 20: herring (length 3, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2787315&ply=48
- **User rating:** 1187 (pinned Maia Elo 1383)
- **FEN before the lead-in:** `7k/ppp2r1p/8/3P4/1b1r4/2N4P/PPP3P1/5R1K w - - 0 25`
- **Lead-in:** 25. Rxf7
- **Judged user moves:**
  - 25... Bxc3 (Good, pre-move ES 0.50), reply 26. bxc3
  - 26... Rxd5 (Good, pre-move ES 0.49), reply 27. Rxc7
  - 27... Rd1+ (Good, pre-move ES 0.50), reply 28. Kh2
- **Answer:** all safe (every judged move is Good).

### 1600-1999

#### Window 1: allowed (length 5, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=2389677&ply=22
- **User rating:** 1807 (pinned Maia Elo 1807)
- **FEN before the lead-in:** `r1bqk2r/4ppbp/p2p1np1/1p1P4/4PPn1/1Q4P1/PP2N1BP/RNB2RK1 w kq - 1 12`
- **Lead-in:** 12. h3
- **Judged user moves:**
  - 12... Qb6+ (Good, pre-move ES 0.77), reply 13. Kh1
  - 13... Nf2+ (Good, pre-move ES 0.79), reply 14. Kh2
- **FEN before the answer move:** `r1b1k2r/4ppbp/pq1p1np1/1p1P4/4PP2/1Q4PP/PP2NnBK/RNB2R2 b kq - 4 14`
- **Answer:** blunder 14... N6g4+ (pre-move ES 0.81, ES after 0.57).
- **Refutation:** hxg4.
- **Score inputs:** facepalm score 0.972, played prob 0.007, reply spread 1.13, played material 3 -2, mate ply n/a.
- **Missed inputs:** best material 3 1, missed gain 1, best move prob 0.025, pre-blunder spread 2.36.

#### Window 2: allowed (length 5, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=2115977&ply=9
- **User rating:** 1811 (pinned Maia Elo 1978)
- **FEN before the lead-in:** `r1bqkbnr/ppp2ppp/2n5/4p3/2B1P3/5N2/PPPP2PP/RNBQK2R b KQkq - 3 5`
- **Lead-in:** 5... Bc5
- **Judged user moves:**
  - 6. d3 (Good, pre-move ES 0.51), reply 6... Nf6
  - 7. Qe2 (Good, pre-move ES 0.50), reply 7... Bg4
- **FEN before the answer move:** `r2qk2r/ppp2ppp/2n2n2/2b1p3/2B1P1b1/3P1N2/PPP1Q1PP/RNB1K2R w KQkq - 3 8`
- **Answer:** blunder 8. Nc3 (pre-move ES 0.51, ES after 0.29).
- **Refutation:** Nd4.
- **Score inputs:** facepalm score 0.657, played prob 0.011, reply spread 1.54, played material 3 0, mate ply n/a.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.745, pre-blunder spread 2.32.

#### Window 3: pure_miss (length 4, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=571297&ply=39
- **User rating:** 1531 (pinned Maia Elo 1802)
- **FEN before the lead-in:** `2k4r/ppp1q3/7p/5ppn/1PP1r1b1/6P1/P2NBPP1/2RQR1K1 b - - 1 20`
- **Lead-in:** 20... Bxe2
- **Judged user moves:**
- **FEN before the answer move:** `2k4r/ppp1q3/7p/5ppn/1PP1r3/6P1/P2NbPP1/2RQR1K1 w - - 0 21`
- **Answer:** blunder 21. Rxe2 (pre-move ES 0.30, ES after 0.13).
- **Missed best move:** Qa4.
- **Score inputs:** facepalm score 0.846, played prob 0.145, reply spread 1.08, played material 3 -2, mate ply n/a.
- **Missed inputs:** best material 3 n/a, missed gain n/a, best move prob 0.407, pre-blunder spread 4.21.

#### Window 4: herring (length 4, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2699116&ply=8
- **User rating:** 1730 (pinned Maia Elo 1730)
- **FEN before the lead-in:** `rn1qkb1r/pp2pppp/2p2n2/3p1b2/2PP4/2N2N2/PP2PPPP/R1BQKB1R w KQkq - 4 5`
- **Lead-in:** 5. Bf4
- **Judged user moves:**
  - 5... e6 (Good, pre-move ES 0.48), reply 6. e3
  - 6... Bd6 (Good, pre-move ES 0.46), reply 7. Bd3
  - 7... Bxd3 (Good, pre-move ES 0.53), reply 8. Qxd3
  - 8... dxc4 (Good, pre-move ES 0.53), reply 9. Qxc4
- **Answer:** all safe (every judged move is Good).

#### Window 5: herring (length 4, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2591279&ply=48
- **User rating:** 1788 (pinned Maia Elo 1965)
- **FEN before the lead-in:** `8/pR1Rpk2/5bp1/6pp/8/5P1P/PPr1BK2/8 w - - 2 25`
- **Lead-in:** 25. Ke1
- **Judged user moves:**
  - 25... Rc1+ (Good, pre-move ES 0.16), reply 26. Kd2
  - 26... Rh1 (Good, pre-move ES 0.18), reply 27. Bc4+
  - 27... Kg7 (Good, pre-move ES 0.18), reply 28. Be6
  - 28... Rh2+ (Good, pre-move ES 0.17), reply 29. Kd3
- **Answer:** all safe (every judged move is Good).

#### Window 6: allowed (length 4, blunder at 4)

- **Game:** https://flawchess.com/analysis?game_id=1539607&ply=68
- **User rating:** 1856 (pinned Maia Elo 1856)
- **FEN before the lead-in:** `8/ppp1Q2p/4p1pk/5p2/7P/2P2q2/PP6/6K1 w - - 0 35`
- **Lead-in:** 35. Qg5+
- **Judged user moves:**
  - 35... Kg7 (Good, pre-move ES 0.50), reply 36. Qe7+
  - 36... Kh6 (Good, pre-move ES 0.50), reply 37. Qg5+
  - 37... Kg7 (Good, pre-move ES 0.50), reply 38. Qe7+
- **FEN before the answer move:** `8/ppp1Q1kp/4p1p1/5p2/7P/2P2q2/PP6/6K1 b - - 7 38`
- **Answer:** blunder 38... Kh8 (pre-move ES 0.50, ES after 0.02).
- **Refutation:** Qf8#.
- **Score inputs:** facepalm score 0.998, played prob 0.005, reply spread 2.11, played material 3 0, mate ply 1.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.905, pre-blunder spread 1.39.

#### Window 7: allowed (length 3, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=2219505&ply=19
- **User rating:** 1877 (pinned Maia Elo 1964)
- **FEN before the lead-in:** `rn1q1rk1/4ppbp/p2p1np1/1PpP4/4P1b1/2NB1N2/PP1B1PPP/R2Q1RK1 b - - 7 10`
- **Lead-in:** 10... axb5
- **Judged user moves:**
  - 11. Bxb5 (Good, pre-move ES 0.64), reply 11... Nbd7
- **FEN before the answer move:** `r2q1rk1/3nppbp/3p1np1/1BpP4/4P1b1/2N2N2/PP1B1PPP/R2Q1RK1 w - - 1 12`
- **Answer:** blunder 12. h4 (pre-move ES 0.65, ES after 0.49).
- **Refutation:** Rb8.
- **Score inputs:** facepalm score 0.547, played prob 0.000, reply spread 3.01, played material 3 0, mate ply n/a.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.487, pre-blunder spread 4.93.

#### Window 8: allowed (length 5, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=1675426&ply=87
- **User rating:** 1716 (pinned Maia Elo 1716)
- **FEN before the lead-in:** `8/6p1/2kr4/K2p2p1/2PR4/1P6/8/8 b - - 0 44`
- **Lead-in:** 44... dxc4
- **Judged user moves:**
- **FEN before the answer move:** `8/6p1/2kr4/K5p1/2pR4/1P6/8/8 w - - 0 45`
- **Answer:** blunder 45. Rxd6+ (pre-move ES 0.50, ES after 0.04).
- **Refutation:** Kxd6.
- **Score inputs:** facepalm score 0.779, played prob 0.018, reply spread 1.01, played material 3 0, mate ply n/a.
- **Missed inputs:** best material 3 1, missed gain 1, best move prob 0.958, pre-blunder spread 1.25.

#### Window 9: allowed (length 4, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=1553075&ply=7
- **User rating:** 1609 (pinned Maia Elo 1609)
- **FEN before the lead-in:** `rnbqkb1r/pp2pppp/2p2n2/3p4/2PP4/2N2N2/PP2PPPP/R1BQKB1R b KQkq - 1 4`
- **Lead-in:** 4... e6
- **Judged user moves:**
  - 5. Bg5 (Good, pre-move ES 0.53), reply 5... Bb4
  - 6. e3 (Good, pre-move ES 0.55), reply 6... Qa5
- **FEN before the answer move:** `rnb1k2r/pp3ppp/2p1pn2/q2p2B1/1bPP4/2N1PN2/PP3PPP/R2QKB1R w KQkq - 1 7`
- **Answer:** blunder 7. Qb3 (pre-move ES 0.55, ES after 0.34).
- **Refutation:** Ne4.
- **Score inputs:** facepalm score 0.559, played prob 0.144, reply spread 1.87, played material 3 0, mate ply n/a.
- **Missed inputs:** best material 3 2, missed gain 2, best move prob 0.203, pre-blunder spread 4.23.

#### Window 10: allowed (length 5, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=2242121&ply=55
- **User rating:** 1566 (pinned Maia Elo 1889)
- **FEN before the lead-in:** `8/1p4pk/2r4p/p1P5/P3R3/4P3/1P1r1PPP/5RK1 b - - 0 28`
- **Lead-in:** 28... b5
- **Judged user moves:**
  - 29. axb5 (Good, pre-move ES 0.82), reply 29... Rxc5
- **FEN before the answer move:** `8/6pk/7p/pPr5/4R3/4P3/1P1r1PPP/5RK1 w - - 0 30`
- **Answer:** blunder 30. Ra1 (pre-move ES 0.79, ES after 0.63).
- **Refutation:** Rxb2.
- **Score inputs:** facepalm score 0.874, played prob 0.016, reply spread 2.20, played material 3 -2, mate ply n/a.
- **Missed inputs:** best material 3 -1, missed gain 0, best move prob 0.485, pre-blunder spread 4.84.

#### Window 11: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2597324&ply=60
- **User rating:** 1266 (pinned Maia Elo 1615)
- **FEN before the lead-in:** `4r3/pp6/5kp1/6b1/6Kn/1BP1P3/PP3P1B/8 w - - 12 31`
- **Lead-in:** 31. Bg3
- **Judged user moves:**
  - 31... Re4+ (Good, pre-move ES 0.81), reply 32. Kh3
  - 32... Nf5 (Good, pre-move ES 0.80), reply 33. Bc2
  - 33... Re8 (Good, pre-move ES 0.85), reply 34. e4
  - 34... Rh8+ (Good, pre-move ES 0.86), reply 35. Kg4
  - 35... Nh6+ (Good, pre-move ES 0.86), reply 36. Kf3
- **Answer:** all safe (every judged move is Good).

#### Window 12: pure_miss (length 3, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=552289&ply=19
- **User rating:** 1340 (pinned Maia Elo 1663)
- **FEN before the lead-in:** `r1bqk1nr/ppp3pp/3p1p2/6B1/4P2P/2Q5/PPP2PP1/RN2K2R b KQkq - 1 10`
- **Lead-in:** 10... Bd7
- **Judged user moves:**
- **FEN before the answer move:** `r2qk1nr/pppb2pp/3p1p2/6B1/4P2P/2Q5/PPP2PP1/RN2K2R w KQkq - 2 11`
- **Answer:** blunder 11. O-O (pre-move ES 0.53, ES after 0.26).
- **Missed best move:** Bf4.
- **Score inputs:** facepalm score 0.678, played prob 0.008, reply spread 5.75, played material 3 -1, mate ply n/a.
- **Missed inputs:** best material 3 n/a, missed gain n/a, best move prob 0.360, pre-blunder spread 3.11.

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

- **Game:** https://flawchess.com/analysis?game_id=2759301&ply=11
- **User rating:** 1906 (pinned Maia Elo 1906)
- **FEN before the lead-in:** `r1bqkbnr/1p1p1ppp/p1n5/2p1pP2/P1B1P3/2N5/1PPP2PP/R1BQK1NR b KQkq - 0 6`
- **Lead-in:** 6... Qh4+
- **Judged user moves:**
  - 7. g3 (Good, pre-move ES 0.64), reply 7... Qd8
  - 8. Nf3 (Good, pre-move ES 0.63), reply 8... d6
  - 9. d3 (Good, pre-move ES 0.64), reply 9... h6
  - 10. O-O (Good, pre-move ES 0.64), reply 10... Nf6
  - 11. Nd5 (Good, pre-move ES 0.64), reply 11... Be7
- **Answer:** all safe (every judged move is Good).

#### Window 15: allowed (length 5, blunder at 5)

- **Game:** https://flawchess.com/analysis?game_id=1688378&ply=15
- **User rating:** 1683 (pinned Maia Elo 1804)
- **FEN before the lead-in:** `rnbq1rk1/pp3pbp/3ppnp1/2pP2B1/2P1P3/2N2N2/PP1Q1PPP/R3KB1R b KQ - 1 8`
- **Lead-in:** 8... exd5
- **Judged user moves:**
  - 9. cxd5 (Good, pre-move ES 0.53), reply 9... a6
  - 10. Bd3 (Good, pre-move ES 0.52), reply 10... b5
  - 11. h4 (Good, pre-move ES 0.54), reply 11... b4
  - 12. Ne2 (Good, pre-move ES 0.52), reply 12... Re8
- **FEN before the answer move:** `rnbqr1k1/5pbp/p2p1np1/2pP2B1/1p2P2P/3B1N2/PP1QNPP1/R3K2R w KQ - 2 13`
- **Answer:** blunder 13. g4 (pre-move ES 0.52, ES after 0.28).
- **Refutation:** Bxg4.
- **Score inputs:** facepalm score 0.789, played prob 0.001, reply spread 4.24, played material 3 -1, mate ply n/a.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.595, pre-blunder spread 4.41.

#### Window 16: herring (length 3, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2077851&ply=35
- **User rating:** 1862 (pinned Maia Elo 1684)
- **FEN before the lead-in:** `rn2r1k1/p4ppp/1p6/2bP2q1/2P1Pp2/1Q3P2/P3B1PP/R3BK1R b - - 0 18`
- **Lead-in:** 18... f5
- **Judged user moves:**
  - 19. h4 (Good, pre-move ES 0.52), reply 19... Qg6
  - 20. Bd3 (Good, pre-move ES 0.56), reply 20... fxe4
  - 21. Bxe4 (Good, pre-move ES 0.60), reply 21... Qf6
- **Answer:** all safe (every judged move is Good).

#### Window 17: allowed (length 4, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=2617614&ply=58
- **User rating:** 1953 (pinned Maia Elo 1953)
- **FEN before the lead-in:** `6k1/p5pp/1p2pb2/2p2pN1/4q3/6QP/PP3PR1/3r2K1 w - - 1 30`
- **Lead-in:** 30. Kh2
- **Judged user moves:**
- **FEN before the answer move:** `6k1/p5pp/1p2pb2/2p2pN1/4q3/6QP/PP3PRK/3r4 b - - 2 30`
- **Answer:** blunder 30... Be5 (pre-move ES 0.87, ES after 0.50).
- **Refutation:** Nxe4.
- **Score inputs:** facepalm score 0.732, played prob 0.262, reply spread 1.98, played material 3 -3, mate ply n/a.
- **Missed inputs:** best material 3 8, missed gain 5, best move prob 0.005, pre-blunder spread 7.85.

#### Window 18: mixed (length 4, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=492831&ply=40
- **User rating:** 1728 (pinned Maia Elo 1977)
- **FEN before the lead-in:** `r2q1r2/p2k1p1Q/b1pNp1p1/2p1P1N1/8/3Pp3/PP4PP/3R1K2 w - - 0 21`
- **Lead-in:** 21. Ngxf7
- **Judged user moves:**
  - 21... Qe7 (Good, pre-move ES 0.58), reply 22. Qxg6
- **FEN before the answer move:** `r4r2/p2kqN2/b1pNp1Q1/2p1P3/8/3Pp3/PP4PP/3R1K2 b - - 0 22`
- **Answer:** blunder 22... Qxf7+ (pre-move ES 0.79, ES after 0.13).
- **Refutation:** Nxf7.
- **Missed best move:** Rxf7+.
- **Score inputs:** facepalm score 1.000, played prob 0.002, reply spread 1.55, played material 3 -6, mate ply n/a.
- **Missed inputs:** best material 3 3, missed gain 3, best move prob 0.150, pre-blunder spread 5.38.

#### Window 19: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2219671&ply=0
- **User rating:** 1678 (pinned Maia Elo 1800)
- **FEN before the lead-in:** `rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1`
- **Lead-in:** 1. e4
- **Judged user moves:**
  - 1... c6 (Good, pre-move ES 0.47), reply 2. d4
  - 2... d5 (Good, pre-move ES 0.47), reply 3. Nf3
  - 3... dxe4 (Good, pre-move ES 0.58), reply 4. Ne5
  - 4... Nd7 (Good, pre-move ES 0.59), reply 5. Bc4
  - 5... Nxe5 (Good, pre-move ES 0.64), reply 6. dxe5
- **Answer:** all safe (every judged move is Good).

#### Window 20: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=3264332&ply=39
- **User rating:** 1681 (pinned Maia Elo 1802)
- **FEN before the lead-in:** `r1q2k1r/p2nb1p1/1pp1pnB1/2Pp2p1/N2P4/4B3/PPQ2PPP/2KR3R b - - 3 20`
- **Lead-in:** 20... b5
- **Judged user moves:**
  - 21. Nc3 (Good, pre-move ES 0.66), reply 21... b4
  - 22. Ne2 (Good, pre-move ES 0.68), reply 22... a5
  - 23. Bxg5 (Good, pre-move ES 0.74), reply 23... a4
  - 24. Qd3 (Good, pre-move ES 0.74), reply 24... Qa6
  - 25. Qxa6 (Good, pre-move ES 0.76), reply 25... Rxa6
- **Answer:** all safe (every judged move is Good).

### 2000-2399

#### Window 1: allowed (length 5, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=574417&ply=24
- **User rating:** 1829 (pinned Maia Elo 2052)
- **FEN before the lead-in:** `r2q1rk1/1p1nbpp1/p1p2n1p/3p4/3P3B/3BP3/PP2NPPP/2RQ1RK1 w - - 0 13`
- **Lead-in:** 13. b3
- **Judged user moves:**
- **FEN before the answer move:** `r2q1rk1/1p1nbpp1/p1p2n1p/3p4/3P3B/1P1BP3/P3NPPP/2RQ1RK1 b - - 0 13`
- **Answer:** blunder 13... b5 (pre-move ES 0.50, ES after 0.27).
- **Refutation:** Rxc6.
- **Score inputs:** facepalm score 0.831, played prob 0.003, reply spread 2.81, played material 3 -1, mate ply n/a.
- **Missed inputs:** best material 3 n/a, missed gain n/a, best move prob 0.273, pre-blunder spread 7.51.

#### Window 2: allowed (length 5, blunder at 4)

- **Game:** https://flawchess.com/analysis?game_id=3013710&ply=95
- **User rating:** 2134 (pinned Maia Elo 2234)
- **FEN before the lead-in:** `8/8/7R/5rn1/2k4P/8/4K3/8 b - - 0 48`
- **Lead-in:** 48... Nf7
- **Judged user moves:**
  - 49. Rh7 (Good, pre-move ES 0.50), reply 49... Kd4
  - 50. h5 (Good, pre-move ES 0.50), reply 50... Ke5
  - 51. Ke3 (Good, pre-move ES 0.50), reply 51... Ke6
- **FEN before the answer move:** `8/5n1R/4k3/5r1P/8/4K3/8/8 w - - 3 52`
- **Answer:** blunder 52. Ke4 (pre-move ES 0.50, ES after 0.14).
- **Refutation:** Ng5+.
- **Score inputs:** facepalm score 0.681, played prob 0.510, reply spread 3.43, played material 3 -5, mate ply n/a.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.031, pre-blunder spread 4.44.

#### Window 3: allowed (length 3, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=2237970&ply=45
- **User rating:** 1783 (pinned Maia Elo 2008)
- **FEN before the lead-in:** `5rk1/r3q1bp/1ppp2p1/p4p2/Pn1P4/4PNP1/1P2QPP1/1NR2RK1 b - - 3 23`
- **Lead-in:** 23... c5
- **Judged user moves:**
  - 24. dxc5 (Good, pre-move ES 0.53), reply 24... dxc5
- **FEN before the answer move:** `5rk1/r3q1bp/1p4p1/p1p2p2/Pn6/4PNP1/1P2QPP1/1NR2RK1 w - - 0 25`
- **Answer:** blunder 25. Rc3 (pre-move ES 0.56, ES after 0.33).
- **Refutation:** Bxc3.
- **Score inputs:** facepalm score 0.976, played prob 0.000, reply spread 1.77, played material 3 -2, mate ply n/a.
- **Missed inputs:** best material 3 5, missed gain 5, best move prob 0.013, pre-blunder spread 4.53.

#### Window 4: pure_miss (length 5, blunder at 5)

- **Game:** https://flawchess.com/analysis?game_id=2483298&ply=87
- **User rating:** 1866 (pinned Maia Elo 2068)
- **FEN before the lead-in:** `8/8/8/P2R2pk/2pP4/2r5/8/4K3 b - - 0 44`
- **Lead-in:** 44... Ra3
- **Judged user moves:**
  - 45. Rc5 (Good, pre-move ES 0.50), reply 45... c3
  - 46. Kd1 (Good, pre-move ES 0.50), reply 46... Kh4
  - 47. Kc2 (Good, pre-move ES 0.50), reply 47... g4
  - 48. d5 (Good, pre-move ES 0.50), reply 48... g3
- **FEN before the answer move:** `8/8/8/P1RP4/7k/r1p3p1/2K5/8 w - - 0 49`
- **Answer:** blunder 49. Rc8 (pre-move ES 0.85, ES after 0.50).
- **Missed best move:** d6.
- **Score inputs:** facepalm score 0.528, played prob 0.229, reply spread 1.95, played material 3 -1, mate ply n/a.
- **Missed inputs:** best material 3 n/a, missed gain n/a, best move prob 0.517, pre-blunder spread 3.74.

#### Window 5: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=626413&ply=1
- **User rating:** 2019 (pinned Maia Elo 2084)
- **FEN before the lead-in:** `rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1`
- **Lead-in:** 1... c6
- **Judged user moves:**
  - 2. c4 (Good, pre-move ES 0.53), reply 2... d5
  - 3. cxd5 (Good, pre-move ES 0.52), reply 3... cxd5
  - 4. exd5 (Good, pre-move ES 0.52), reply 4... Qxd5
  - 5. Nc3 (Good, pre-move ES 0.54), reply 5... Qd8
  - 6. d4 (Good, pre-move ES 0.55), reply 6... Nf6
- **Answer:** all safe (every judged move is Good).

#### Window 6: allowed (length 4, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=499157&ply=9
- **User rating:** 1961 (pinned Maia Elo 2121)
- **FEN before the lead-in:** `rnb1kbnr/ppp1pppp/6q1/8/8/2N2N2/PPPPBPPP/R1BQK2R b KQkq - 5 5`
- **Lead-in:** 5... c6
- **Judged user moves:**
  - 6. d4 (Good, pre-move ES 0.66), reply 6... Bf5
- **FEN before the answer move:** `rn2kbnr/pp2pppp/2p3q1/5b2/3P4/2N2N2/PPP1BPPP/R1BQK2R w KQkq - 1 7`
- **Answer:** blunder 7. Bd3 (pre-move ES 0.70, ES after 0.51).
- **Refutation:** Bxd3.
- **Score inputs:** facepalm score 0.790, played prob 0.009, reply spread 1.27, played material 3 -1, mate ply n/a.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.023, pre-blunder spread 3.05.

#### Window 7: allowed (length 3, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=3247100&ply=29
- **User rating:** 2087 (pinned Maia Elo 2087)
- **FEN before the lead-in:** `r1b2rk1/pp4pp/1nn1pq2/3p4/8/3B1N2/PPP2PPP/R1BQR1K1 b - - 0 15`
- **Lead-in:** 15... e5
- **Judged user moves:**
- **FEN before the answer move:** `r1b2rk1/pp4pp/1nn2q2/3pp3/8/3B1N2/PPP2PPP/R1BQR1K1 w - - 0 16`
- **Answer:** blunder 16. Bb5 (pre-move ES 0.51, ES after 0.23).
- **Refutation:** e4.
- **Score inputs:** facepalm score 0.779, played prob 0.155, reply spread 1.65, played material 3 -3, mate ply n/a.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.693, pre-blunder spread 3.21.

#### Window 8: herring (length 4, no blunder)

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

#### Window 9: allowed (length 4, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=498038&ply=77
- **User rating:** 1954 (pinned Maia Elo 2077)
- **FEN before the lead-in:** `6k1/5p2/3p2p1/p2r4/3n1P2/2p1b1P1/P1B3RP/3R3K b - - 1 39`
- **Lead-in:** 39... Rc5
- **Judged user moves:**
- **FEN before the answer move:** `6k1/5p2/3p2p1/p1r5/3n1P2/2p1b1P1/P1B3RP/3R3K w - - 2 40`
- **Answer:** blunder 40. Bb3 (pre-move ES 0.51, ES after 0.16).
- **Refutation:** Nxb3.
- **Score inputs:** facepalm score 0.671, played prob 0.012, reply spread 3.62, played material 3 1, mate ply n/a.
- **Missed inputs:** best material 3 1, missed gain 0, best move prob 0.382, pre-blunder spread 6.63.

#### Window 10: allowed (length 4, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=2417021&ply=36
- **User rating:** 2010 (pinned Maia Elo 2153)
- **FEN before the lead-in:** `2kr2r1/ppqbbp2/1np1p1p1/4P3/2P5/1B2BQ2/PP3PP1/2KR3R w - - 2 19`
- **Lead-in:** 19. Qxf7
- **Judged user moves:**
- **FEN before the answer move:** `2kr2r1/ppqbbQ2/1np1p1p1/4P3/2P5/1B2B3/PP3PP1/2KR3R b - - 0 19`
- **Answer:** blunder 19... Rdf8 (pre-move ES 0.72, ES after 0.20).
- **Refutation:** Qxe7.
- **Score inputs:** facepalm score 0.980, played prob 0.020, reply spread 1.27, played material 3 -3, mate ply n/a.
- **Missed inputs:** best material 3 1, missed gain 1, best move prob 0.496, pre-blunder spread 3.19.

#### Window 11: allowed (length 3, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=2486495&ply=34
- **User rating:** 2312 (pinned Maia Elo 2312)
- **FEN before the lead-in:** `r2q1rk1/pp2bppp/2p2n2/2n5/2bN4/2N1B1P1/PP1Q1PBP/R3R1K1 w - - 0 18`
- **Lead-in:** 18. Nf5
- **Judged user moves:**
- **FEN before the answer move:** `r2q1rk1/pp2bppp/2p2n2/2n2N2/2b5/2N1B1P1/PP1Q1PBP/R3R1K1 b - - 1 18`
- **Answer:** blunder 18... Re8 (pre-move ES 0.51, ES after 0.18).
- **Refutation:** Qxd8.
- **Score inputs:** facepalm score 0.693, played prob 0.242, reply spread 1.95, played material 3 -3, mate ply n/a.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.166, pre-blunder spread 4.95.

#### Window 12: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=575006&ply=83
- **User rating:** 1913 (pinned Maia Elo 2092)
- **FEN before the lead-in:** `8/1b1R1kp1/1p3p1p/p4q2/4p3/7P/3R2P1/6K1 b - - 3 42`
- **Lead-in:** 42... Qxd7
- **Judged user moves:**
  - 43. Rxd7+ (Good, pre-move ES 0.80), reply 43... Ke6
  - 44. Rxb7 (Good, pre-move ES 0.81), reply 44... b5
  - 45. Rb6+ (Good, pre-move ES 0.83), reply 45... Kd5
  - 46. Rxb5+ (Good, pre-move ES 0.85), reply 46... Kc4
  - 47. Rxa5 (Good, pre-move ES 0.88), reply 47... Kd3
- **Answer:** all safe (every judged move is Good).

#### Window 13: herring (length 4, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2629918&ply=9
- **User rating:** 2042 (pinned Maia Elo 2042)
- **FEN before the lead-in:** `rnbqk1nr/pp2ppbp/2p3p1/3pP3/3P4/4BP2/PPP3PP/RN1QKBNR b KQkq - 0 5`
- **Lead-in:** 5... f6
- **Judged user moves:**
  - 6. f4 (Good, pre-move ES 0.50), reply 6... Nh6
  - 7. Be2 (Good, pre-move ES 0.51), reply 7... O-O
  - 8. Nf3 (Good, pre-move ES 0.48), reply 8... Qb6
  - 9. Qc1 (Good, pre-move ES 0.49), reply 9... Nf5
- **Answer:** all safe (every judged move is Good).

#### Window 14: allowed (length 3, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=1239558&ply=39
- **User rating:** 1939 (pinned Maia Elo 2106)
- **FEN before the lead-in:** `2k1R2r/Qp4bp/2pq2p1/1B3pB1/3n4/5P2/PP3P1P/2R3K1 b - - 0 20`
- **Lead-in:** 20... Rxe8
- **Judged user moves:**
- **FEN before the answer move:** `2k1r3/Qp4bp/2pq2p1/1B3pB1/3n4/5P2/PP3P1P/2R3K1 w - - 0 21`
- **Answer:** blunder 21. Bf1 (pre-move ES 0.35, ES after 0.06).
- **Refutation:** Nxf3+.
- **Score inputs:** facepalm score 0.859, played prob 0.069, reply spread 1.26, played material 3 1, mate ply n/a.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.017, pre-blunder spread 7.03.

#### Window 15: allowed (length 3, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=2766505&ply=37
- **User rating:** 1909 (pinned Maia Elo 2054)
- **FEN before the lead-in:** `1r2k2r/3bb1pp/p2pp3/3p1P1P/1q1P1B2/1PNQPP2/2P5/2KR3R b k - 0 19`
- **Lead-in:** 19... Bb5
- **Judged user moves:**
  - 20. Nxb5 (Good, pre-move ES 0.74), reply 20... axb5
  - 21. fxe6 (Good, pre-move ES 0.77), reply 21... Ra8
- **FEN before the answer move:** `r3k2r/4b1pp/3pP3/1p1p3P/1q1P1B2/1P1QPP2/2P5/2KR3R w k - 1 22`
- **Answer:** blunder 22. c3 (pre-move ES 0.71, ES after 0.50).
- **Refutation:** Qxb3.
- **Score inputs:** facepalm score 0.512, played prob 0.251, reply spread 2.14, played material 3 -1, mate ply n/a.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.276, pre-blunder spread 7.68.

#### Window 16: allowed (length 3, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=2670222&ply=54
- **User rating:** 2121 (pinned Maia Elo 2184)
- **FEN before the lead-in:** `5rk1/rb3p2/p3p1p1/P3N1P1/1p2nP1Q/3Bq2P/1PP4K/R4R2 w - - 3 28`
- **Lead-in:** 28. Rae1
- **Judged user moves:**
  - 28... Qd4 (Good, pre-move ES 0.17), reply 29. Ng4
  - 29... Bc6 (Good, pre-move ES 0.15), reply 30. Bxe4
- **FEN before the answer move:** `5rk1/r4p2/p1b1p1p1/P5P1/1p1qBPNQ/7P/1PP4K/4RR2 b - - 0 30`
- **Answer:** blunder 30... Bxe4 (pre-move ES 0.11, ES after 0.02).
- **Refutation:** Nf6+.
- **Score inputs:** facepalm score 0.516, played prob 0.485, reply spread 2.31, played material 3 -3, mate ply n/a.
- **Missed inputs:** best material 3 -3, missed gain 0, best move prob 0.240, pre-blunder spread 5.15.

#### Window 17: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2116100&ply=1
- **User rating:** 1844 (pinned Maia Elo 2001)
- **FEN before the lead-in:** `rnbqkbnr/pppppppp/8/8/3P4/8/PPP1PPPP/RNBQKBNR b KQkq - 0 1`
- **Lead-in:** 1... g6
- **Judged user moves:**
  - 2. Nf3 (Good, pre-move ES 0.56), reply 2... Bg7
  - 3. e3 (Good, pre-move ES 0.55), reply 3... d6
  - 4. Bd3 (Good, pre-move ES 0.53), reply 4... Nf6
  - 5. b3 (Good, pre-move ES 0.52), reply 5... O-O
  - 6. Bb2 (Good, pre-move ES 0.49), reply 6... Re8
- **Answer:** all safe (every judged move is Good).

#### Window 18: allowed (length 3, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=615091&ply=24
- **User rating:** 2245 (pinned Maia Elo 2289)
- **FEN before the lead-in:** `r2q1rk1/pb1nbppp/1p2p3/8/3Pn3/2N3P1/PP3PBP/R1BQR1K1 w - - 0 13`
- **Lead-in:** 13. Nxe4
- **Judged user moves:**
- **FEN before the answer move:** `r2q1rk1/pb1nbppp/1p2p3/8/3PN3/6P1/PP3PBP/R1BQR1K1 b - - 0 13`
- **Answer:** blunder 13... Nf6 (pre-move ES 0.51, ES after 0.16).
- **Refutation:** Nxf6+.
- **Score inputs:** facepalm score 0.868, played prob 0.080, reply spread 1.15, played material 3 -3, mate ply n/a.
- **Missed inputs:** best material 3 3, missed gain 3, best move prob 0.437, pre-blunder spread 6.19.

#### Window 19: herring (length 4, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2731483&ply=0
- **User rating:** 2112 (pinned Maia Elo 2112)
- **FEN before the lead-in:** `rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1`
- **Lead-in:** 1. b4
- **Judged user moves:**
  - 1... e5 (Good, pre-move ES 0.54), reply 2. Bb2
  - 2... Bxb4 (Good, pre-move ES 0.53), reply 3. Bxe5
  - 3... Nf6 (Good, pre-move ES 0.53), reply 4. a3
  - 4... Ba5 (Good, pre-move ES 0.54), reply 5. Nf3
- **Answer:** all safe (every judged move is Good).

#### Window 20: allowed (length 5, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=3015568&ply=12
- **User rating:** 2280 (pinned Maia Elo 2228)
- **FEN before the lead-in:** `r1bqk1nr/pppp1ppp/2n5/b7/2BpP3/2P2N2/P4PPP/RNBQK2R w KQkq - 0 7`
- **Lead-in:** 7. Qb3
- **Judged user moves:**
  - 7... Qf6 (Good, pre-move ES 0.50), reply 8. O-O
  - 8... Bb6 (Good, pre-move ES 0.46), reply 9. e5
- **FEN before the answer move:** `r1b1k1nr/pppp1ppp/1bn2q2/4P3/2Bp4/1QP2N2/P4PPP/RNB2RK1 b kq - 0 9`
- **Answer:** blunder 9... Nxe5 (pre-move ES 0.47, ES after 0.22).
- **Refutation:** Re1.
- **Score inputs:** facepalm score 0.632, played prob 0.039, reply spread 1.46, played material 3 1, mate ply n/a.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.877, pre-blunder spread 1.70.

### 2400+

#### Window 1: allowed (length 5, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=1531843&ply=32
- **User rating:** 3026 (pinned Maia Elo 2600)
- **FEN before the lead-in:** `r1b1r1k1/1pq2ppp/pn1b4/2p3P1/2PpnN2/1P2P3/PBNP2BP/R2Q1RK1 w - - 1 17`
- **Lead-in:** 17. a4
- **Judged user moves:**
  - 17... a5 (Good, pre-move ES 0.56), reply 18. Na3
- **FEN before the answer move:** `r1b1r1k1/1pq2ppp/1n1b4/p1p3P1/P1PpnN2/NP2P3/1B1P2BP/R2Q1RK1 b - - 1 18`
- **Answer:** blunder 18... Be5 (pre-move ES 0.64, ES after 0.24).
- **Refutation:** Bxe4.
- **Score inputs:** facepalm score 0.982, played prob 0.003, reply spread 2.35, played material 3 -3, mate ply n/a.
- **Missed inputs:** best material 3 n/a, missed gain n/a, best move prob 0.386, pre-blunder spread 5.57.

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

- **Game:** https://flawchess.com/analysis?game_id=658671&ply=77
- **User rating:** 2670 (pinned Maia Elo 2600)
- **FEN before the lead-in:** `r2nN1k1/8/6p1/1BBR1p1p/1P2p1n1/2P1b1P1/2K5/8 b - - 0 39`
- **Lead-in:** 39... Bxc5
- **Judged user moves:**
  - 40. Rxc5 (Good, pre-move ES 0.35), reply 40... Ne6
- **FEN before the answer move:** `r3N1k1/8/4n1p1/1BR2p1p/1P2p1n1/2P3P1/2K5/8 w - - 1 41`
- **Answer:** blunder 41. Rc6 (pre-move ES 0.35, ES after 0.16).
- **Refutation:** Rxe8.
- **Score inputs:** facepalm score 0.864, played prob 0.328, reply spread 3.02, played material 3 -3, mate ply n/a.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.128, pre-blunder spread 3.63.

#### Window 5: allowed (length 4, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=1526466&ply=43
- **User rating:** 2965 (pinned Maia Elo 2600)
- **FEN before the lead-in:** `r5k1/1p3pp1/2q1pn1p/p7/8/PP2P2P/1Q2NPP1/3R2K1 b - - 0 22`
- **Lead-in:** 22... Rc8
- **Judged user moves:**
  - 23. Nd4 (Good, pre-move ES 0.50), reply 23... Qc5
- **FEN before the answer move:** `2r3k1/1p3pp1/4pn1p/p1q5/3N4/PP2P2P/1Q3PP1/3R2K1 w - - 3 24`
- **Answer:** blunder 24. Qb1 (pre-move ES 0.49, ES after 0.33).
- **Refutation:** Qxa3.
- **Score inputs:** facepalm score 0.856, played prob 0.001, reply spread 2.38, played material 3 -1, mate ply n/a.
- **Missed inputs:** best material 3 n/a, missed gain n/a, best move prob 0.109, pre-blunder spread 4.96.

#### Window 6: allowed (length 3, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=2701539&ply=34
- **User rating:** 2456 (pinned Maia Elo 2600)
- **FEN before the lead-in:** `r3k2r/pb2n1b1/1pnqN1p1/2p5/P4P2/2P5/1P1P2PP/R1BQ1RK1 w kq - 1 18`
- **Lead-in:** 18. Qb3
- **Judged user moves:**
- **FEN before the answer move:** `r3k2r/pb2n1b1/1pnqN1p1/2p5/P4P2/1QP5/1P1P2PP/R1B2RK1 b kq - 2 18`
- **Answer:** blunder 18... Qd5 (pre-move ES 0.84, ES after 0.50).
- **Refutation:** Nc7+.
- **Score inputs:** facepalm score 0.978, played prob 0.000, reply spread 1.63, played material 3 -9, mate ply n/a.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.000, pre-blunder spread 1.48.

#### Window 7: pure_miss (length 3, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=1512247&ply=64
- **User rating:** 2780 (pinned Maia Elo 2600)
- **FEN before the lead-in:** `8/pp2kppp/3qp3/5b2/3P4/1PQ5/PK5P/2R5 w - - 9 33`
- **Lead-in:** 33. Qe3
- **Judged user moves:**
- **FEN before the answer move:** `8/pp2kppp/3qp3/5b2/3P4/1P2Q3/PK5P/2R5 b - - 10 33`
- **Answer:** blunder 33... Qd5 (pre-move ES 0.74, ES after 0.25).
- **Missed best move:** Qxh2+.
- **Score inputs:** facepalm score 0.583, played prob 0.001, reply spread 5.89, played material 3 -1, mate ply n/a.
- **Missed inputs:** best material 3 1, missed gain 1, best move prob 0.820, pre-blunder spread 2.14.

#### Window 8: allowed (length 5, blunder at 4)

- **Game:** https://flawchess.com/analysis?game_id=1531955&ply=44
- **User rating:** 3016 (pinned Maia Elo 2600)
- **FEN before the lead-in:** `2r4r/pN2kpp1/2n1p2p/3p1b2/1P6/3P2P1/P3P1BP/R1R3K1 w - - 1 23`
- **Lead-in:** 23. e4
- **Judged user moves:**
  - 23... dxe4 (Good, pre-move ES 0.52), reply 24. dxe4
  - 24... Bg6 (Good, pre-move ES 0.54), reply 25. a3
  - 25... Nd4 (Good, pre-move ES 0.53), reply 26. Kf2
- **FEN before the answer move:** `2r4r/pN2kpp1/4p1bp/8/1P1nP3/P5P1/5KBP/R1R5 b - - 2 26`
- **Answer:** blunder 26... Kf6 (pre-move ES 0.62, ES after 0.44).
- **Refutation:** Nd6.
- **Score inputs:** facepalm score 0.609, played prob 0.013, reply spread 3.73, played material 3 0, mate ply n/a.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.713, pre-blunder spread 2.83.

#### Window 9: allowed (length 4, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=1532378&ply=35
- **User rating:** 3095 (pinned Maia Elo 2600)
- **FEN before the lead-in:** `1r1q1rk1/pB3pb1/3N2np/2P1n1p1/3p4/6B1/PP3PPP/R2QR1K1 b - - 3 18`
- **Lead-in:** 18... Qa5
- **Judged user moves:**
- **FEN before the answer move:** `1r3rk1/pB3pb1/3N2np/q1P1n1p1/3p4/6B1/PP3PPP/R2QR1K1 w - - 4 19`
- **Answer:** blunder 19. a3 (pre-move ES 0.63, ES after 0.23).
- **Refutation:** Qxc5.
- **Score inputs:** facepalm score 0.966, played prob 0.010, reply spread 1.24, played material 3 -4, mate ply n/a.
- **Missed inputs:** best material 3 n/a, missed gain n/a, best move prob 0.555, pre-blunder spread 3.36.

#### Window 10: herring (length 4, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=1520095&ply=1
- **User rating:** 2916 (pinned Maia Elo 2600)
- **FEN before the lead-in:** `rnbqkbnr/pppppppp/8/8/8/5N2/PPPPPPPP/RNBQKB1R b KQkq - 1 1`
- **Lead-in:** 1... d5
- **Judged user moves:**
  - 2. e3 (Good, pre-move ES 0.53), reply 2... c5
  - 3. d4 (Good, pre-move ES 0.51), reply 3... e6
  - 4. Bd3 (Good, pre-move ES 0.52), reply 4... Nf6
  - 5. dxc5 (Good, pre-move ES 0.51), reply 5... Bxc5
- **Answer:** all safe (every judged move is Good).

#### Window 11: allowed (length 3, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=655816&ply=81
- **User rating:** 2558 (pinned Maia Elo 2512)
- **FEN before the lead-in:** `8/4k1pp/8/3Bpp2/3n4/1P1K2P1/7P/8 b - - 7 41`
- **Lead-in:** 41... Kd6
- **Judged user moves:**
- **FEN before the answer move:** `8/6pp/3k4/3Bpp2/3n4/1P1K2P1/7P/8 w - - 8 42`
- **Answer:** blunder 42. Kc4 (pre-move ES 0.37, ES after 0.18).
- **Refutation:** Nxb3.
- **Score inputs:** facepalm score 0.561, played prob 0.030, reply spread 4.60, played material 3 -1, mate ply n/a.
- **Missed inputs:** best material 3 n/a, missed gain n/a, best move prob 0.804, pre-blunder spread 2.22.

#### Window 12: pure_miss (length 3, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=1521262&ply=94
- **User rating:** 2828 (pinned Maia Elo 2600)
- **FEN before the lead-in:** `8/8/2b1pp2/7k/pR6/P4P2/2r3P1/R5K1 w - - 0 48`
- **Lead-in:** 48. Kh2
- **Judged user moves:**
- **FEN before the answer move:** `8/8/2b1pp2/7k/pR6/P4P2/2r3PK/R7 b - - 1 48`
- **Answer:** blunder 48... Kg6 (pre-move ES 0.48, ES after 0.30).
- **Missed best move:** Bxf3.
- **Score inputs:** facepalm score 0.749, played prob 0.013, reply spread 2.32, played material 3 0, mate ply n/a.
- **Missed inputs:** best material 3 n/a, missed gain n/a, best move prob 0.829, pre-blunder spread 2.04.

#### Window 13: herring (length 4, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=1505841&ply=0
- **User rating:** 2915 (pinned Maia Elo 2600)
- **FEN before the lead-in:** `rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1`
- **Lead-in:** 1. e4
- **Judged user moves:**
  - 1... e5 (Good, pre-move ES 0.48), reply 2. Nf3
  - 2... Nc6 (Good, pre-move ES 0.49), reply 3. Bb5
  - 3... a6 (Good, pre-move ES 0.48), reply 4. Ba4
  - 4... Nf6 (Good, pre-move ES 0.48), reply 5. d3
- **Answer:** all safe (every judged move is Good).

#### Window 14: allowed (length 3, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=658426&ply=45
- **User rating:** 2516 (pinned Maia Elo 2463)
- **FEN before the lead-in:** `1r2k2r/p2p1pp1/4p2p/q3P3/2b2B1P/bNP3R1/Q1B2PP1/1K1R4 b k - 2 23`
- **Lead-in:** 23... Qa4
- **Judged user moves:**
- **FEN before the answer move:** `1r2k2r/p2p1pp1/4p2p/4P3/q1b2B1P/bNP3R1/Q1B2PP1/1K1R4 w k - 3 24`
- **Answer:** blunder 24. Ka1 (pre-move ES 0.73, ES after 0.35).
- **Refutation:** Rxb3.
- **Score inputs:** facepalm score 0.605, played prob 0.079, reply spread 2.75, played material 3 -1, mate ply n/a.
- **Missed inputs:** best material 3 n/a, missed gain n/a, best move prob 0.783, pre-blunder spread 2.19.

#### Window 15: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=1516884&ply=1
- **User rating:** 2648 (pinned Maia Elo 2600)
- **FEN before the lead-in:** `rnbqkbnr/pppppppp/8/8/8/5N2/PPPPPPPP/RNBQKB1R b KQkq - 1 1`
- **Lead-in:** 1... c5
- **Judged user moves:**
  - 2. e3 (Good, pre-move ES 0.51), reply 2... Nc6
  - 3. d4 (Good, pre-move ES 0.53), reply 3... cxd4
  - 4. exd4 (Good, pre-move ES 0.52), reply 4... d5
  - 5. c3 (Good, pre-move ES 0.52), reply 5... Bg4
  - 6. Bd3 (Good, pre-move ES 0.50), reply 6... e6
- **Answer:** all safe (every judged move is Good).

#### Window 16: allowed (length 5, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=1513307&ply=86
- **User rating:** 2705 (pinned Maia Elo 2600)
- **FEN before the lead-in:** `8/8/1R6/4p2p/pb2p3/1k2B1P1/2r1PP1P/5K2 w - - 2 44`
- **Lead-in:** 44. Bg5
- **Judged user moves:**
  - 44... a3 (Good, pre-move ES 0.68), reply 45. Bf6
- **FEN before the answer move:** `8/8/1R3B2/4p2p/1b2p3/pk4P1/2r1PP1P/5K2 b - - 1 45`
- **Answer:** blunder 45... Rc4 (pre-move ES 0.74, ES after 0.57).
- **Refutation:** Bxe5.
- **Score inputs:** facepalm score 0.799, played prob 0.027, reply spread 1.58, played material 3 -1, mate ply n/a.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.015, pre-blunder spread 4.00.

#### Window 17: allowed (length 4, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=1515849&ply=142
- **User rating:** 2852 (pinned Maia Elo 2600)
- **FEN before the lead-in:** `8/4k3/8/P1R5/1K6/8/8/3r4 w - - 11 72`
- **Lead-in:** 72. Kb5
- **Judged user moves:**
  - 72... Rb1+ (Good, pre-move ES 0.50), reply 73. Kc6
- **FEN before the answer move:** `8/4k3/2K5/P1R5/8/8/8/1r6 b - - 14 73`
- **Answer:** blunder 73... Rc1 (pre-move ES 0.50, ES after 0.02).
- **Refutation:** Rxc1.
- **Score inputs:** facepalm score 0.999, played prob 0.001, reply spread 1.32, played material 3 -5, mate ply n/a.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.767, pre-blunder spread 2.17.

#### Window 18: pure_miss (length 3, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=658069&ply=91
- **User rating:** 2583 (pinned Maia Elo 2540)
- **FEN before the lead-in:** `1R6/2r1p1k1/3pP3/3P1pKp/3n1P2/4N3/4n3/8 b - - 7 46`
- **Lead-in:** 46... Rc3
- **Judged user moves:**
- **FEN before the answer move:** `1R6/4p1k1/3pP3/3P1pKp/3n1P2/2r1N3/4n3/8 w - - 8 47`
- **Answer:** blunder 47. Re8 (pre-move ES 0.15, ES after 0.02).
- **Missed best move:** Nxf5+.
- **Score inputs:** facepalm score 0.991, played prob 0.271, reply spread 2.35, played material 3 1, mate ply 3.
- **Missed inputs:** best material 3 1, missed gain 0, best move prob 0.521, pre-blunder spread 3.69.

#### Window 19: mixed (length 4, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=642685&ply=83
- **User rating:** 2610 (pinned Maia Elo 2566)
- **FEN before the lead-in:** `R7/6p1/5p1p/p6k/4B2P/1nr3P1/5PK1/8 b - - 4 42`
- **Lead-in:** 42... Rc5
- **Judged user moves:**
- **FEN before the answer move:** `R7/6p1/5p1p/p1r4k/4B2P/1n4P1/5PK1/8 w - - 5 43`
- **Answer:** blunder 43. Bc2 (pre-move ES 0.89, ES after 0.15).
- **Refutation:** Rxc2.
- **Missed best move:** Kh3.
- **Score inputs:** facepalm score 0.994, played prob 0.000, reply spread 2.22, played material 3 -3, mate ply n/a.
- **Missed inputs:** best material 3 5, missed gain 5, best move prob 0.574, pre-blunder spread 4.38.

#### Window 20: allowed (length 3, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=644877&ply=37
- **User rating:** 2582 (pinned Maia Elo 2568)
- **FEN before the lead-in:** `r3r1k1/p4ppp/5n2/2qp4/5P2/1PNQ4/P5PP/4RR1K b - - 1 19`
- **Lead-in:** 19... Rxe1
- **Judged user moves:**
  - 20. Rxe1 (Good, pre-move ES 0.39), reply 20... Ng4
- **FEN before the answer move:** `r5k1/p4ppp/8/2qp4/5Pn1/1PNQ4/P5PP/4R2K w - - 1 21`
- **Answer:** blunder 21. Qf3 (pre-move ES 0.46, ES after 0.13).
- **Refutation:** Nf2+.
- **Score inputs:** facepalm score 0.667, played prob 0.055, reply spread 1.50, played material 3 0, mate ply n/a.
- **Missed inputs:** best material 3 0, missed gain 0, best move prob 0.457, pre-blunder spread 4.02.
