# Blunder-check spot-check

Windows drawn the way the feature draws them (250 D-12): each slot is independently a herring (about 33%, all judged moves safe) or a blunder window, with length L uniform over 3 to 5 user moves. About 20 windows per Elo bucket, at most one per game, drawn with a fixed seed. A blunder window shows its facepalm score inputs after the answer.

Thresholds: facepalm score at least 0.5, eval band [0.10, 0.90] on the pre-move ES. A recommendation only; nothing here is wired into app code.

How to read: for each window, play through the lead-in and the judged moves on the board (the game link opens the game on FlawChess at the first judged move), decide whether the position is a fair question, then compare with the answer. A blunder window is fair when the refutation or the missed move is something a player of that rating could find. Moves are in SAN; a stored move that is not legal on the replayed board prints as its UCI with the word illegal.

### <800

#### Window 1: mixed (length 5, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=1597477&ply=32
- **User rating:** 599 (pinned Maia Elo 600)
- **FEN before the lead-in:** `r3r1k1/p1p2ppp/1p1q1nb1/4p3/4P1P1/P1NPBN1P/5P2/RQ2R1K1 w - - 0 17`
- **Lead-in:** 17. Nb5
- **Judged user moves:**
  - 17... Qd7 (Good, pre-move ES 0.25), reply 18. Rd1
- **FEN before the answer move:** `r3r1k1/p1pq1ppp/1p3nb1/1N2p3/4P1P1/P2PBN1P/5P2/RQ1R2K1 b - - 3 18`
- **Answer:** blunder 18... Red8 (pre-move ES 0.37, ES after 0.18).
- **Refutation:** Nxe5.
- **Missed best move:** c6.
- **Score inputs:** facepalm score 0.715, played prob 0.022, material loss 1.000, material missed 1.000, reply prob 0.300, mate ply n/a.
- **Missed inputs:** missed gain 1.000, best move prob 0.217, pre-blunder spread 12.18.

#### Window 2: mixed (length 5, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=1503253&ply=34
- **User rating:** 312 (pinned Maia Elo 600)
- **FEN before the lead-in:** `2r1qrk1/pppbp1bn/4p2p/3P4/PPB5/2N5/2P3PP/R1BQK2R w KQ - 0 18`
- **Lead-in:** 18. dxe6
- **Judged user moves:**
- **FEN before the answer move:** `2r1qrk1/pppbp1bn/4P2p/8/PPB5/2N5/2P3PP/R1BQK2R b KQ - 0 18`
- **Answer:** blunder 18... Bxe6 (pre-move ES 0.73, ES after 0.23).
- **Refutation:** Bxe6+.
- **Missed best move:** Bxc3+.
- **Score inputs:** facepalm score 0.957, played prob 0.600, material loss 3.065, material missed 4.000, reply prob 0.697, mate ply n/a.
- **Missed inputs:** missed gain 4.000, best move prob 0.044, pre-blunder spread 5.52.

#### Window 3: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=1918989&ply=18
- **User rating:** 205 (pinned Maia Elo 600)
- **FEN before the lead-in:** `r1bqk2r/ppp2ppp/2n5/4P2n/3N4/2N5/PP2PPPP/R2QKB1R w KQkq - 1 10`
- **Lead-in:** 10. Nf3
- **Judged user moves:**
  - 10... Qxd1+ (Good, pre-move ES 0.34), reply 11. Rxd1
  - 11... O-O (Good, pre-move ES 0.35), reply 12. e4
  - 12... Bg4 (Good, pre-move ES 0.48), reply 13. Be2
  - 13... Nf4 (Good, pre-move ES 0.48), reply 14. O-O
  - 14... Nxe2+ (Good, pre-move ES 0.52), reply 15. Nxe2
- **Answer:** all safe (every judged move is Good).

#### Window 4: allowed (length 5, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=1502983&ply=5
- **User rating:** 326 (pinned Maia Elo 600)
- **FEN before the lead-in:** `rnbqkbnr/ppp1p1pp/8/3p1p2/3P1P2/4P3/PPP3PP/RNBQKBNR b KQkq - 0 3`
- **Lead-in:** 3... Nc6
- **Judged user moves:**
  - 4. Be2 (Good, pre-move ES 0.54), reply 4... e6
- **FEN before the answer move:** `r1bqkbnr/ppp3pp/2n1p3/3p1p2/3P1P2/4P3/PPP1B1PP/RNBQK1NR w KQkq - 0 5`
- **Answer:** blunder 5. e4 (pre-move ES 0.55, ES after 0.30).
- **Refutation:** fxe4.
- **Score inputs:** facepalm score 0.748, played prob 0.006, material loss 1.000, material missed 0.484, reply prob 0.301, mate ply n/a.
- **Missed inputs:** missed gain 0.484, best move prob 0.374, pre-blunder spread 9.87.

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

- **Game:** https://flawchess.com/analysis?game_id=1828297&ply=20
- **User rating:** 647 (pinned Maia Elo 647)
- **FEN before the lead-in:** `2rqkb1r/1p2pppp/p4n2/3p4/3n1B2/2N2Q1P/PPP2PP1/R3KB1R w KQk - 0 11`
- **Lead-in:** 11. Qd1
- **Judged user moves:**
- **FEN before the answer move:** `2rqkb1r/1p2pppp/p4n2/3p4/3n1B2/2N4P/PPP2PP1/R2QKB1R b KQk - 1 11`
- **Answer:** blunder 11... Nb5 (pre-move ES 0.69, ES after 0.27).
- **Refutation:** Nxb5.
- **Score inputs:** facepalm score 0.884, played prob 0.054, material loss 3.000, material missed 0.000, reply prob 0.446, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.116, pre-blunder spread 12.73.

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

- **Game:** https://flawchess.com/analysis?game_id=2475091&ply=26
- **User rating:** 379 (pinned Maia Elo 600)
- **FEN before the lead-in:** `r3kb1r/pnpq1ppp/2p1p3/4P3/1PPp1P2/3P1R1P/P3Q1P1/RNB1K3 w Qkq - 1 14`
- **Lead-in:** 14. a3
- **Judged user moves:**
  - 14... c5 (Good, pre-move ES 0.46), reply 15. Nd2
  - 15... cxb4 (Good, pre-move ES 0.52), reply 16. Rb1
- **FEN before the answer move:** `r3kb1r/pnpq1ppp/4p3/4P3/1pPp1P2/P2P1R1P/3NQ1P1/1RB1K3 b kq - 1 16`
- **Answer:** blunder 16... O-O-O (pre-move ES 0.61, ES after 0.39).
- **Refutation:** axb4.
- **Score inputs:** facepalm score 0.700, played prob 0.054, material loss 1.000, material missed 0.290, reply prob 0.655, mate ply n/a.
- **Missed inputs:** missed gain 0.290, best move prob 0.107, pre-blunder spread 11.14.

#### Window 9: allowed (length 3, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=2226619&ply=13
- **User rating:** 336 (pinned Maia Elo 600)
- **FEN before the lead-in:** `r1bqkb1r/pppp2pp/2n5/4p3/2B1R1p1/5N2/PPPP1P1P/RNBQ2K1 b kq - 0 7`
- **Lead-in:** 7... gxf3
- **Judged user moves:**
  - 8. Qxf3 (Good, pre-move ES 0.18), reply 8... Qg5+
  - 9. Kh1 (Good, pre-move ES 0.33), reply 9... d6
- **FEN before the answer move:** `r1b1kb1r/ppp3pp/2np4/4p1q1/2B1R3/5Q2/PPPP1P1P/RNB4K w kq - 0 10`
- **Answer:** blunder 10. d4 (pre-move ES 0.31, ES after 0.16).
- **Refutation:** Qxc1+.
- **Score inputs:** facepalm score 0.866, played prob 0.064, material loss 3.226, material missed 0.000, reply prob 0.329, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob n/a, pre-blunder spread 5.69.

#### Window 10: mixed (length 5, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=2183557&ply=20
- **User rating:** 181 (pinned Maia Elo 600)
- **FEN before the lead-in:** `r1q2rk1/1pp2ppp/2npbn2/1pb1p3/PP2P3/2PP1P2/6PP/R1BQKBNR w KQ - 0 11`
- **Lead-in:** 11. bxc5
- **Judged user moves:**
  - 11... dxc5 (Good, pre-move ES 0.71), reply 12. axb5
- **FEN before the answer move:** `r1q2rk1/1pp2ppp/2n1bn2/1Pp1p3/4P3/2PP1P2/6PP/R1BQKBNR b KQ - 0 12`
- **Answer:** blunder 12... Na5 (pre-move ES 0.84, ES after 0.61).
- **Refutation:** c4.
- **Missed best move:** Rxa1.
- **Score inputs:** facepalm score 0.581, played prob 0.095, material loss 0.000, material missed 2.194, reply prob 0.265, mate ply n/a.
- **Missed inputs:** missed gain 2.194, best move prob 0.706, pre-blunder spread 3.25.

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

- **Game:** https://flawchess.com/analysis?game_id=1669428&ply=35
- **User rating:** 296 (pinned Maia Elo 600)
- **FEN before the lead-in:** `3rk2r/5ppp/p3pn2/2b1N1Bb/2p5/N1P1P2P/P4PP1/R4K1R b k - 1 18`
- **Lead-in:** 18... Nd5
- **Judged user moves:**
- **FEN before the answer move:** `3rk2r/5ppp/p3p3/2bnN1Bb/2p5/N1P1P2P/P4PP1/R4K1R w k - 2 19`
- **Answer:** blunder 19. Rd1 (pre-move ES 0.75, ES after 0.07).
- **Refutation:** Nxe3+.
- **Missed best move:** Bxd8.
- **Score inputs:** facepalm score 0.802, played prob 0.044, material loss 2.935, material missed 2.677, reply prob 0.040, mate ply n/a.
- **Missed inputs:** missed gain 2.677, best move prob 0.178, pre-blunder spread 9.23.

#### Window 13: pure_miss (length 5, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=1429193&ply=67
- **User rating:** 212 (pinned Maia Elo 600)
- **FEN before the lead-in:** `4r3/ppp5/3k4/3N1r2/3P1B2/2K5/PPP5/8 b - - 1 34`
- **Lead-in:** 34... Rxf4
- **Judged user moves:**
- **FEN before the answer move:** `4r3/ppp5/3k4/3N4/3P1r2/2K5/PPP5/8 w - - 0 35`
- **Answer:** blunder 35. Kc4 (pre-move ES 0.42, ES after 0.06).
- **Missed best move:** Nxf4.
- **Score inputs:** facepalm score 0.782, played prob 0.072, material loss 1.774, material missed 5.000, reply prob 0.038, mate ply n/a.
- **Missed inputs:** missed gain 5.000, best move prob 0.698, pre-blunder spread 3.48.

#### Window 14: allowed (length 5, blunder at 5)

- **Game:** https://flawchess.com/analysis?game_id=2444875&ply=12
- **User rating:** 543 (pinned Maia Elo 600)
- **FEN before the lead-in:** `r3kbnr/pppbpppp/2n5/1B6/8/8/PPPP1PPP/RNB1K1NR w KQkq - 2 7`
- **Lead-in:** 7. Bxc6
- **Judged user moves:**
  - 7... Bxc6 (Good, pre-move ES 0.58), reply 8. Nc3
  - 8... e6 (Good, pre-move ES 0.60), reply 9. Nf3
  - 9... h6 (Good, pre-move ES 0.59), reply 10. Ne5
  - 10... Bxg2 (Good, pre-move ES 0.64), reply 11. Rg1
- **FEN before the answer move:** `r3kbnr/ppp2pp1/4p2p/4N3/8/2N5/PPPP1PbP/R1B1K1R1 b Qkq - 1 11`
- **Answer:** blunder 11... Be4 (pre-move ES 0.63, ES after 0.20).
- **Refutation:** Nxe4.
- **Score inputs:** facepalm score 0.932, played prob 0.053, material loss 3.000, material missed 0.000, reply prob 0.848, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.192, pre-blunder spread 5.68.

#### Window 15: allowed (length 4, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=2465471&ply=58
- **User rating:** 398 (pinned Maia Elo 600)
- **FEN before the lead-in:** `4rk2/pQ5p/8/5r2/8/P3K2P/2P5/8 w - - 2 30`
- **Lead-in:** 30. Kd2
- **Judged user moves:**
- **FEN before the answer move:** `4rk2/pQ5p/8/5r2/8/P6P/2PK4/8 b - - 3 30`
- **Answer:** blunder 30... Re7 (pre-move ES 0.47, ES after 0.09).
- **Refutation:** Qc8+.
- **Score inputs:** facepalm score 0.724, played prob 0.055, material loss 2.419, material missed 0.000, reply prob 0.233, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.174, pre-blunder spread 8.55.

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

- **Game:** https://flawchess.com/analysis?game_id=3174092&ply=0
- **User rating:** 733 (pinned Maia Elo 733)
- **FEN before the lead-in:** `rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1`
- **Lead-in:** 1. e4
- **Judged user moves:**
  - 1... e5 (Good, pre-move ES 0.47), reply 2. Qf3
  - 2... Nf6 (Good, pre-move ES 0.53), reply 3. d3
  - 3... Bc5 (Good, pre-move ES 0.59), reply 4. Be3
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

#### Window 19: allowed (length 4, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=2349772&ply=36
- **User rating:** 625 (pinned Maia Elo 625)
- **FEN before the lead-in:** `r2q2k1/ppp2r1p/3n1p1B/2b1p3/P1Pp2b1/1P1P1N1P/2n2PP1/R2Q1RK1 w - - 0 19`
- **Lead-in:** 19. hxg4
- **Judged user moves:**
  - 19... Nb4 (Good, pre-move ES 0.83), reply 20. g5
  - 20... fxg5 (Good, pre-move ES 0.81), reply 21. Nxg5
- **FEN before the answer move:** `r2q2k1/ppp2r1p/3n3B/2b1p1N1/PnPp4/1P1P4/5PP1/R2Q1RK1 b - - 0 21`
- **Answer:** blunder 21... Nf5 (pre-move ES 0.85, ES after 0.68).
- **Refutation:** Nxf7.
- **Score inputs:** facepalm score 0.921, played prob 0.046, material loss 2.000, material missed 1.548, reply prob 0.709, mate ply n/a.
- **Missed inputs:** missed gain 1.548, best move prob 0.361, pre-blunder spread 7.95.

#### Window 20: allowed (length 3, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=2895242&ply=8
- **User rating:** 460 (pinned Maia Elo 600)
- **FEN before the lead-in:** `r2qkb1r/pppbpppp/2n2n2/1B1p4/3P4/2N1P3/PPP2PPP/R1BQK1NR w KQkq - 5 5`
- **Lead-in:** 5. Nf3
- **Judged user moves:**
  - 5... Nb4 (Good, pre-move ES 0.48), reply 6. a3
  - 6... Bxb5 (Good, pre-move ES 0.48), reply 7. axb4
- **FEN before the answer move:** `r2qkb1r/ppp1pppp/5n2/1b1p4/1P1P4/2N1PN2/1PP2PPP/R1BQK2R b KQkq - 0 7`
- **Answer:** blunder 7... Ne4 (pre-move ES 0.51, ES after 0.19).
- **Refutation:** Nxb5.
- **Score inputs:** facepalm score 0.908, played prob 0.067, material loss 3.000, material missed 0.000, reply prob 0.675, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.117, pre-blunder spread 12.15.

### 800-1199

#### Window 1: allowed (length 3, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=3068977&ply=40
- **User rating:** 793 (pinned Maia Elo 1196)
- **FEN before the lead-in:** `r3k2r/p3n1p1/2p1bp2/1pnp4/6Pp/P2BN3/1PPB1P1P/2KR3R w kq - 0 21`
- **Lead-in:** 21. Bf5
- **Judged user moves:**
  - 21... Bxf5 (Good, pre-move ES 0.72), reply 22. Nxf5
- **FEN before the answer move:** `r3k2r/p3n1p1/2p2p2/1pnp1N2/6Pp/P7/1PPB1P1P/2KR3R b kq - 0 22`
- **Answer:** blunder 22... g6 (pre-move ES 0.72, ES after 0.50).
- **Refutation:** Nd4.
- **Score inputs:** facepalm score 0.536, played prob 0.030, material loss 0.000, material missed 0.000, reply prob 0.042, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.824, pre-blunder spread 2.32.

#### Window 2: herring (length 3, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2900820&ply=12
- **User rating:** 1195 (pinned Maia Elo 1195)
- **FEN before the lead-in:** `rn1qkb1r/ppp2ppp/5nb1/3p4/3P4/4P1N1/PP3PPP/RNBQKB1R w KQkq - 5 7`
- **Lead-in:** 7. Bd3
- **Judged user moves:**
  - 7... Bd6 (Good, pre-move ES 0.54), reply 8. Bxg6
  - 8... hxg6 (Good, pre-move ES 0.57), reply 9. Ne2
  - 9... Nc6 (Good, pre-move ES 0.58), reply 10. g3
- **Answer:** all safe (every judged move is Good).

#### Window 3: allowed (length 4, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=3162516&ply=56
- **User rating:** 1500 (pinned Maia Elo 1149)
- **FEN before the lead-in:** `r3r1k1/3b1ppp/2q5/3R4/1p2p3/P2PB3/1Q3PPP/5RK1 w - - 1 29`
- **Lead-in:** 29. Qd4
- **Judged user moves:**
  - 29... Rxa3 (Good, pre-move ES 0.50), reply 30. dxe4
  - 30... Be6 (Good, pre-move ES 0.46), reply 31. Rc5
- **FEN before the answer move:** `4r1k1/5ppp/2q1b3/2R5/1p1QP3/r3B3/5PPP/5RK1 b - - 2 31`
- **Answer:** blunder 31... Qb6 (pre-move ES 0.49, ES after 0.20).
- **Refutation:** Rc8.
- **Score inputs:** facepalm score 0.792, played prob 0.158, material loss 4.000, material missed 0.387, reply prob 0.121, mate ply n/a.
- **Missed inputs:** missed gain 0.387, best move prob 0.099, pre-blunder spread 6.89.

#### Window 4: allowed (length 5, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=3327135&ply=63
- **User rating:** 707 (pinned Maia Elo 1149)
- **FEN before the lead-in:** `3r4/3PR1p1/5p1p/P3pk2/8/r6P/5P2/3R2K1 b - - 0 32`
- **Lead-in:** 32... Rxa5
- **Judged user moves:**
  - 33. Re8 (Good, pre-move ES 0.50), reply 33... Raa8
- **FEN before the answer move:** `r2rR3/3P2p1/5p1p/4pk2/8/7P/5P2/3R2K1 w - - 2 34`
- **Answer:** blunder 34. Rd6 (pre-move ES 0.50, ES after 0.18).
- **Refutation:** Rxe8.
- **Score inputs:** facepalm score 0.988, played prob 0.008, material loss 5.000, material missed 0.000, reply prob 0.423, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.284, pre-blunder spread 4.70.

#### Window 5: allowed (length 4, blunder at 4)

- **Game:** https://flawchess.com/analysis?game_id=1081708&ply=10
- **User rating:** 789 (pinned Maia Elo 1194)
- **FEN before the lead-in:** `r1bqkb1r/pppp1ppp/2n2n2/8/3PP3/2N5/PPP3PP/R1BQKBNR w KQkq - 1 6`
- **Lead-in:** 6. e5
- **Judged user moves:**
  - 6... Ng8 (Good, pre-move ES 0.34), reply 7. Nf3
  - 7... d6 (Good, pre-move ES 0.35), reply 8. Bf4
  - 8... dxe5 (Good, pre-move ES 0.39), reply 9. Nxe5
- **FEN before the answer move:** `r1bqkbnr/ppp2ppp/2n5/4N3/3P1B2/2N5/PPP3PP/R2QKB1R b KQkq - 0 9`
- **Answer:** blunder 9... f6 (pre-move ES 0.40, ES after 0.19).
- **Refutation:** Qh5+.
- **Score inputs:** facepalm score 0.866, played prob 0.013, material loss 1.065, material missed 2.323, reply prob 0.313, mate ply n/a.
- **Missed inputs:** missed gain 2.323, best move prob 0.019, pre-blunder spread 4.74.

#### Window 6: allowed (length 3, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=2395456&ply=49
- **User rating:** 1121 (pinned Maia Elo 1121)
- **FEN before the lead-in:** `3r1b1r/pk6/8/3ppN1p/6pP/6B1/PP3PP1/2KR3R b - - 3 25`
- **Lead-in:** 25... Rc8+
- **Judged user moves:**
  - 26. Kb1 (Good, pre-move ES 0.85), reply 26... Bb4
  - 27. Bxe5 (Good, pre-move ES 0.88), reply 27... Rhd8
- **FEN before the answer move:** `2rr4/pk6/8/3pBN1p/1b4pP/8/PP3PP1/1K1R3R w - - 1 28`
- **Answer:** blunder 28. Ne7 (pre-move ES 0.85, ES after 0.61).
- **Refutation:** Bxe7.
- **Score inputs:** facepalm score 0.806, played prob 0.081, material loss 3.000, material missed 0.000, reply prob 0.287, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.175, pre-blunder spread 14.61.

#### Window 7: herring (length 4, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=3233892&ply=49
- **User rating:** 1500 (pinned Maia Elo 1149)
- **FEN before the lead-in:** `6k1/p4ppp/P3p1n1/2bpP3/2pN4/2P3PP/1r3P1B/R5K1 b - - 2 25`
- **Lead-in:** 25... Bxd4
- **Judged user moves:**
  - 26. cxd4 (Good, pre-move ES 0.16), reply 26... Ne7
  - 27. Ra5 (Good, pre-move ES 0.17), reply 27... Nc6
  - 28. Rc5 (Good, pre-move ES 0.16), reply 28... Rb6
  - 29. f4 (Good, pre-move ES 0.16), reply 29... Rxa6
- **Answer:** all safe (every judged move is Good).

#### Window 8: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2832550&ply=30
- **User rating:** 756 (pinned Maia Elo 1176)
- **FEN before the lead-in:** `r2r2k1/pppqnpp1/4b2p/Q3p3/3pP3/P2P1NP1/1PP2PBP/R4RK1 w - - 3 16`
- **Lead-in:** 16. Nxe5
- **Judged user moves:**
  - 16... Qc8 (Good, pre-move ES 0.35), reply 17. Qd2
  - 17... Bh3 (Good, pre-move ES 0.36), reply 18. Rae1
  - 18... Bxg2 (Good, pre-move ES 0.35), reply 19. Kxg2
  - 19... Re8 (Good, pre-move ES 0.35), reply 20. f4
  - 20... Qe6 (Good, pre-move ES 0.31), reply 21. Nf3
- **Answer:** all safe (every judged move is Good).

#### Window 9: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2863785&ply=1
- **User rating:** 911 (pinned Maia Elo 1123)
- **FEN before the lead-in:** `rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1`
- **Lead-in:** 1... e5
- **Judged user moves:**
  - 2. Nf3 (Good, pre-move ES 0.53), reply 2... Nc6
  - 3. Bc4 (Good, pre-move ES 0.53), reply 3... g6
  - 4. d3 (Good, pre-move ES 0.57), reply 4... Bg7
  - 5. O-O (Good, pre-move ES 0.57), reply 5... h6
  - 6. c3 (Good, pre-move ES 0.54), reply 6... Nf6
- **Answer:** all safe (every judged move is Good).

#### Window 10: herring (length 4, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2864920&ply=15
- **User rating:** 1183 (pinned Maia Elo 1183)
- **FEN before the lead-in:** `rnbqk2r/pp3ppp/2p1p3/2Pp4/3Pn3/4P1P1/PP2NPP1/RN1QKB1R b KQkq - 0 8`
- **Lead-in:** 8... b5
- **Judged user moves:**
  - 9. f3 (Good, pre-move ES 0.62), reply 9... Qa5+
  - 10. Nbc3 (Good, pre-move ES 0.62), reply 10... Nxc3
  - 11. bxc3 (Good, pre-move ES 0.60), reply 11... Ba6
  - 12. Qc2 (Good, pre-move ES 0.63), reply 12... b4
- **Answer:** all safe (every judged move is Good).

#### Window 11: mixed (length 3, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=2130192&ply=40
- **User rating:** 783 (pinned Maia Elo 1052)
- **FEN before the lead-in:** `1rb2rk1/5p1p/p4p2/q3p3/2BpP3/2P4P/P2Q1PP1/R2R2K1 w - - 0 21`
- **Lead-in:** 21. cxd4
- **Judged user moves:**
- **FEN before the answer move:** `1rb2rk1/5p1p/p4p2/q3p3/2BPP3/7P/P2Q1PP1/R2R2K1 b - - 0 21`
- **Answer:** blunder 21... Rd8 (pre-move ES 0.35, ES after 0.05).
- **Refutation:** Qxa5.
- **Missed best move:** Qxd2.
- **Score inputs:** facepalm score 0.984, played prob 0.070, material loss 5.000, material missed 0.000, reply prob 0.826, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.407, pre-blunder spread 7.25.

#### Window 12: herring (length 3, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2960718&ply=62
- **User rating:** 959 (pinned Maia Elo 1154)
- **FEN before the lead-in:** `1r5k/2q4p/2p4b/3p1p2/P2PpPpN/4n1P1/2Q4P/R3B2K w - - 0 32`
- **Lead-in:** 32. Qe2
- **Judged user moves:**
  - 32... Nc4 (Good, pre-move ES 0.44), reply 33. Nxf5
  - 33... Bf8 (Good, pre-move ES 0.44), reply 34. Qxg4
  - 34... Qf7 (Good, pre-move ES 0.43), reply 35. a5
- **Answer:** all safe (every judged move is Good).

#### Window 13: allowed (length 4, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=2129629&ply=84
- **User rating:** 797 (pinned Maia Elo 1058)
- **FEN before the lead-in:** `8/P1p3q1/5p2/2PB4/3p1k2/P7/5NKP/8 w - - 1 43`
- **Lead-in:** 43. Kf1
- **Judged user moves:**
  - 43... c6 (Good, pre-move ES 0.10), reply 44. Bxc6
  - 44... Qxa7 (Good, pre-move ES 0.84), reply 45. a4
- **FEN before the answer move:** `8/q7/2B2p2/2P5/P2p1k2/8/5N1P/5K2 b - - 0 45`
- **Answer:** blunder 45... Qxc5 (pre-move ES 0.86, ES after 0.04).
- **Refutation:** Nd3+.
- **Score inputs:** facepalm score 0.503, played prob 0.693, material loss 2.419, material missed 0.226, reply prob 0.360, mate ply n/a.
- **Missed inputs:** missed gain 0.226, best move prob 0.103, pre-blunder spread 3.26.

#### Window 14: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=3060990&ply=0
- **User rating:** 877 (pinned Maia Elo 877)
- **FEN before the lead-in:** `rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1`
- **Lead-in:** 1. d4
- **Judged user moves:**
  - 1... d5 (Good, pre-move ES 0.47), reply 2. c4
  - 2... e6 (Good, pre-move ES 0.47), reply 3. e3
  - 3... Nf6 (Good, pre-move ES 0.49), reply 4. Nf3
  - 4... Be7 (Good, pre-move ES 0.49), reply 5. Bd3
  - 5... O-O (Good, pre-move ES 0.49), reply 6. Nc3
- **Answer:** all safe (every judged move is Good).

#### Window 15: allowed (length 4, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=2863141&ply=28
- **User rating:** 661 (pinned Maia Elo 1118)
- **FEN before the lead-in:** `rn3rk1/ppp2ppp/1q2b3/8/1P6/P2B1Nb1/2PPR1P1/RNBQ1K2 w - - 3 15`
- **Lead-in:** 15. c4
- **Judged user moves:**
- **FEN before the answer move:** `rn3rk1/ppp2ppp/1q2b3/8/1PP5/P2B1Nb1/3PR1P1/RNBQ1K2 b - - 0 15`
- **Answer:** blunder 15... Nc6 (pre-move ES 0.37, ES after 0.18).
- **Refutation:** c5.
- **Score inputs:** facepalm score 0.794, played prob 0.170, material loss 2.419, material missed 0.000, reply prob 0.723, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.408, pre-blunder spread 7.80.

#### Window 16: herring (length 4, no blunder)

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

#### Window 17: herring (length 3, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2854247&ply=11
- **User rating:** 856 (pinned Maia Elo 1088)
- **FEN before the lead-in:** `rnbqk2r/p2pppbp/1pp3pB/3BP3/3P4/8/PPP2PPP/RN1QK1NR b KQkq - 0 6`
- **Lead-in:** 6... Bxh6
- **Judged user moves:**
  - 7. Bc4 (Good, pre-move ES 0.46), reply 7... e6
  - 8. Nf3 (Good, pre-move ES 0.49), reply 8... d5
  - 9. exd6 (Good, pre-move ES 0.51), reply 9... Qxd6
- **Answer:** all safe (every judged move is Good).

#### Window 18: allowed (length 3, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=2667737&ply=8
- **User rating:** 1354 (pinned Maia Elo 1158)
- **FEN before the lead-in:** `rnbqkbnr/pp3p1p/3pp1p1/2p5/2B1P3/5N2/PPPP1PPP/RNBQ1RK1 w kq - 0 5`
- **Lead-in:** 5. Re1
- **Judged user moves:**
  - 5... Bg7 (Good, pre-move ES 0.41), reply 6. d4
- **FEN before the answer move:** `rnbqk1nr/pp3pbp/3pp1p1/2p5/2BPP3/5N2/PPP2PPP/RNBQR1K1 b kq - 0 6`
- **Answer:** blunder 6... d5 (pre-move ES 0.44, ES after 0.11).
- **Refutation:** exd5.
- **Score inputs:** facepalm score 0.793, played prob 0.030, material loss 1.097, material missed 0.000, reply prob 0.882, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.570, pre-blunder spread 4.89.

#### Window 19: herring (length 4, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2544195&ply=29
- **User rating:** 1018 (pinned Maia Elo 1190)
- **FEN before the lead-in:** `rn2r1k1/pp1q1ppp/2pp4/3P4/7Q/3B1N2/PPP2PPP/2KR3R b - - 1 15`
- **Lead-in:** 15... h6
- **Judged user moves:**
  - 16. dxc6 (Good, pre-move ES 0.87), reply 16... Nxc6
  - 17. Qg3 (Good, pre-move ES 0.86), reply 17... Qc7
  - 18. Nh4 (Good, pre-move ES 0.84), reply 18... Nb4
  - 19. Kb1 (Good, pre-move ES 0.84), reply 19... a5
- **Answer:** all safe (every judged move is Good).

#### Window 20: allowed (length 3, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=3328081&ply=27
- **User rating:** 635 (pinned Maia Elo 1100)
- **FEN before the lead-in:** `r2qr3/ppp3kp/3pb1p1/8/1n1QP3/8/PPP2PPP/RNB1R1K1 b - - 0 14`
- **Lead-in:** 14... Kg8
- **Judged user moves:**
  - 15. Qxb4 (Good, pre-move ES 0.87), reply 15... c5
  - 16. Qxb7 (Good, pre-move ES 0.87), reply 16... d5
- **FEN before the answer move:** `r2qr1k1/pQ5p/4b1p1/2pp4/4P3/8/PPP2PPP/RNB1R1K1 w - - 0 17`
- **Answer:** blunder 17. exd5 (pre-move ES 0.88, ES after 0.30).
- **Refutation:** Bc8.
- **Score inputs:** facepalm score 0.559, played prob 0.513, material loss 5.000, material missed 0.000, reply prob 0.031, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.246, pre-blunder spread 4.99.

### 1200-1599

#### Window 1: allowed (length 5, blunder at 5)

- **Game:** https://flawchess.com/analysis?game_id=755548&ply=36
- **User rating:** 1771 (pinned Maia Elo 1573)
- **FEN before the lead-in:** `r3r1k1/pp3ppp/1q2bn2/8/5N2/3n3P/PPP2PP1/R2QR1K1 w - - 0 19`
- **Lead-in:** 19. Qxd3
- **Judged user moves:**
  - 19... Rad8 (Good, pre-move ES 0.83), reply 20. Qg3
  - 20... Bc8 (Good, pre-move ES 0.84), reply 21. Rf1
  - 21... Bf5 (Good, pre-move ES 0.85), reply 22. c3
  - 22... Ne4 (Good, pre-move ES 0.86), reply 23. Qf3
- **FEN before the answer move:** `3rr1k1/pp3ppp/1q6/5b2/4nN2/2P2Q1P/PP3PP1/R4RK1 b - - 2 23`
- **Answer:** blunder 23... Rd4 (pre-move ES 0.88, ES after 0.39).
- **Refutation:** cxd4.
- **Score inputs:** facepalm score 0.996, played prob 0.000, material loss 4.032, material missed 1.548, reply prob 0.991, mate ply n/a.
- **Missed inputs:** missed gain 1.548, best move prob 0.839, pre-blunder spread 2.19.

#### Window 2: allowed (length 5, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=1066832&ply=77
- **User rating:** 1500 (pinned Maia Elo 1583)
- **FEN before the lead-in:** `2r4r/pp2knp1/2p1pbQ1/3n2BP/2R5/8/4RPP1/6K1 b - - 6 39`
- **Lead-in:** 39... Rc7
- **Judged user moves:**
  - 40. Bxf6+ (Good, pre-move ES 0.77), reply 40... gxf6
  - 41. Rce4 (Good, pre-move ES 0.80), reply 41... e5
- **FEN before the answer move:** `7r/ppr1kn2/2p2pQ1/3np2P/4R3/8/4RPP1/6K1 w - - 0 42`
- **Answer:** blunder 42. h6 (pre-move ES 0.79, ES after 0.62).
- **Refutation:** Rxh6.
- **Score inputs:** facepalm score 0.716, played prob 0.054, material loss 1.000, material missed 0.129, reply prob 0.779, mate ply n/a.
- **Missed inputs:** missed gain 0.129, best move prob 0.368, pre-blunder spread 8.29.

#### Window 3: herring (length 3, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=1550958&ply=12
- **User rating:** 1586 (pinned Maia Elo 1586)
- **FEN before the lead-in:** `r1bqk2r/pp1pnpbp/2n1p1p1/2p5/2B1P3/P1PP1N2/1P3PPP/RNBQK2R w KQkq - 1 7`
- **Lead-in:** 7. Nbd2
- **Judged user moves:**
  - 7... O-O (Good, pre-move ES 0.55), reply 8. Nf1
  - 8... d5 (Good, pre-move ES 0.59), reply 9. exd5
  - 9... exd5 (Good, pre-move ES 0.65), reply 10. Ba2
- **Answer:** all safe (every judged move is Good).

#### Window 4: herring (length 4, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=3254358&ply=1
- **User rating:** 1231 (pinned Maia Elo 1421)
- **FEN before the lead-in:** `rnbqkbnr/pppppppp/8/8/3P4/8/PPP1PPPP/RNBQKBNR b KQkq - 0 1`
- **Lead-in:** 1... Nf6
- **Judged user moves:**
  - 2. Bg5 (Good, pre-move ES 0.54), reply 2... d5
  - 3. Bxf6 (Good, pre-move ES 0.50), reply 3... gxf6
  - 4. e3 (Good, pre-move ES 0.50), reply 4... Bg7
  - 5. c4 (Good, pre-move ES 0.54), reply 5... e5
- **Answer:** all safe (every judged move is Good).

#### Window 5: herring (length 3, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2821420&ply=12
- **User rating:** 1787 (pinned Maia Elo 1595)
- **FEN before the lead-in:** `r1bqk1nr/pp2bppp/3p4/2p1p3/2BnP3/2NP1N1P/PPP2PP1/R1BQK2R w KQkq - 3 7`
- **Lead-in:** 7. Nxd4
- **Judged user moves:**
  - 7... cxd4 (Good, pre-move ES 0.45), reply 8. Nd5
  - 8... Nf6 (Good, pre-move ES 0.45), reply 9. O-O
  - 9... O-O (Good, pre-move ES 0.45), reply 10. Nxe7+
- **Answer:** all safe (every judged move is Good).

#### Window 6: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2378633&ply=0
- **User rating:** 1067 (pinned Maia Elo 1457)
- **FEN before the lead-in:** `rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1`
- **Lead-in:** 1. Nf3
- **Judged user moves:**
  - 1... d5 (Good, pre-move ES 0.47), reply 2. Nc3
  - 2... Nf6 (Good, pre-move ES 0.52), reply 3. d4
  - 3... Bf5 (Good, pre-move ES 0.53), reply 4. Bg5
  - 4... Nc6 (Good, pre-move ES 0.52), reply 5. e3
  - 5... e6 (Good, pre-move ES 0.48), reply 6. Bd3
- **Answer:** all safe (every judged move is Good).

#### Window 7: allowed (length 4, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=1880110&ply=49
- **User rating:** 1187 (pinned Maia Elo 1555)
- **FEN before the lead-in:** `3r3r/1k3p2/1p2p1pn/n2pP1Np/1P1P1P2/2P5/3B2PP/R4RK1 b - - 0 25`
- **Lead-in:** 25... Nc4
- **Judged user moves:**
  - 26. Ra2 (Good, pre-move ES 0.50), reply 26... Ra8
- **FEN before the answer move:** `r6r/1k3p2/1p2p1pn/3pP1Np/1PnP1P2/2P5/R2B2PP/5RK1 w - - 3 27`
- **Answer:** blunder 27. Rfa1 (pre-move ES 0.50, ES after 0.20).
- **Refutation:** Nxd2.
- **Score inputs:** facepalm score 0.787, played prob 0.265, material loss 3.000, material missed 0.000, reply prob 0.531, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.615, pre-blunder spread 2.96.

#### Window 8: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2680842&ply=27
- **User rating:** 1218 (pinned Maia Elo 1410)
- **FEN before the lead-in:** `2kr1b1r/1b2pppp/p1p5/qpn2QN1/3P1B2/8/PPPN1PPP/R3R1K1 b - - 10 14`
- **Lead-in:** 14... e6
- **Judged user moves:**
  - 15. Qxf7 (Good, pre-move ES 0.84), reply 15... Rd7
  - 16. Qe8+ (Good, pre-move ES 0.84), reply 16... Rd8
  - 17. Qh5 (Good, pre-move ES 0.84), reply 17... g6
  - 18. Qh3 (Good, pre-move ES 0.88), reply 18... Bd6
  - 19. Bxd6 (Good, pre-move ES 0.89), reply 19... Rxd6
- **Answer:** all safe (every judged move is Good).

#### Window 9: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2850677&ply=63
- **User rating:** 1553 (pinned Maia Elo 1553)
- **FEN before the lead-in:** `6k1/p4pp1/5n1p/2BP4/4b3/7P/P4PP1/6K1 b - - 1 32`
- **Lead-in:** 32... Bxd5
- **Judged user moves:**
  - 33. Bxa7 (Good, pre-move ES 0.26), reply 33... Bxa2
  - 34. f3 (Good, pre-move ES 0.27), reply 34... Kf8
  - 35. Bd4 (Good, pre-move ES 0.26), reply 35... Nd5
  - 36. Bc5+ (Good, pre-move ES 0.24), reply 36... Ke8
  - 37. Bd4 (Good, pre-move ES 0.23), reply 37... g6
- **Answer:** all safe (every judged move is Good).

#### Window 10: allowed (length 4, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=478153&ply=56
- **User rating:** 1246 (pinned Maia Elo 1430)
- **FEN before the lead-in:** `5rk1/p2r1p1p/q3p1p1/4P3/3P3Q/1P1KP3/P1P5/7R w - - 2 29`
- **Lead-in:** 29. c4
- **Judged user moves:**
  - 29... f5 (Good, pre-move ES 0.82), reply 30. exf6
- **FEN before the answer move:** `5rk1/p2r3p/q3pPp1/8/2PP3Q/1P1KP3/P7/7R b - - 0 30`
- **Answer:** blunder 30... Rxf6 (pre-move ES 0.86, ES after 0.33).
- **Refutation:** Qxf6.
- **Score inputs:** facepalm score 0.992, played prob 0.026, material loss 4.000, material missed 2.000, reply prob 0.920, mate ply n/a.
- **Missed inputs:** missed gain 2.000, best move prob 0.427, pre-blunder spread 5.04.

#### Window 11: pure_miss (length 3, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=2337769&ply=59
- **User rating:** 1487 (pinned Maia Elo 1303)
- **FEN before the lead-in:** `4k2r/p4ppp/1pNR1b2/8/1P3p2/P6P/5PP1/6K1 b - - 0 30`
- **Lead-in:** 30... Be7
- **Judged user moves:**
  - 31. Rd4 (Good, pre-move ES 0.55), reply 31... Bf6
  - 32. Rxf4 (Good, pre-move ES 0.52), reply 32... g5
- **FEN before the answer move:** `4k2r/p4p1p/1pN2b2/6p1/1P3R2/P6P/5PP1/6K1 w - - 0 33`
- **Answer:** blunder 33. Re4+ (pre-move ES 0.89, ES after 0.50).
- **Missed best move:** Rxf6.
- **Score inputs:** facepalm score 0.841, played prob 0.072, material loss 0.000, material missed 3.548, reply prob 0.756, mate ply n/a.
- **Missed inputs:** missed gain 3.548, best move prob 0.907, pre-blunder spread 1.48.

#### Window 12: mixed (length 3, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=2685201&ply=59
- **User rating:** 855 (pinned Maia Elo 1274)
- **FEN before the lead-in:** `2q2r2/4nk2/1p3pP1/p3pP2/P1PpQ2N/1P6/7P/2K3R1 b - - 0 30`
- **Lead-in:** 30... Kg7
- **Judged user moves:**
  - 31. Nf3 (Good, pre-move ES 0.47), reply 31... Rd8
- **FEN before the answer move:** `2qr4/4n1k1/1p3pP1/p3pP2/P1PpQ3/1P3N2/7P/2K3R1 w - - 3 32`
- **Answer:** blunder 32. Ne1 (pre-move ES 0.71, ES after 0.28).
- **Refutation:** Qxf5.
- **Missed best move:** Ng5.
- **Score inputs:** facepalm score 0.640, played prob 0.004, material loss 1.000, material missed 0.097, reply prob 0.187, mate ply n/a.
- **Missed inputs:** missed gain 0.097, best move prob 0.015, pre-blunder spread 7.04.

#### Window 13: allowed (length 3, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=2679898&ply=42
- **User rating:** 855 (pinned Maia Elo 1274)
- **FEN before the lead-in:** `2bq1rk1/3n1ppp/8/1Q2p3/3p4/6P1/3NPP1P/4KB1R w K - 0 22`
- **Lead-in:** 22. Bg2
- **Judged user moves:**
  - 22... Qf6 (Good, pre-move ES 0.57), reply 23. O-O
- **FEN before the answer move:** `2b2rk1/3n1ppp/5q2/1Q2p3/3p4/6P1/3NPPBP/5RK1 b - - 3 23`
- **Answer:** blunder 23... Ba6 (pre-move ES 0.53, ES after 0.22).
- **Refutation:** Qxd7.
- **Score inputs:** facepalm score 0.844, played prob 0.172, material loss 2.613, material missed 0.000, reply prob 0.881, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.027, pre-blunder spread 12.65.

#### Window 14: pure_miss (length 4, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=1215524&ply=16
- **User rating:** 1583 (pinned Maia Elo 1393)
- **FEN before the lead-in:** `r1b2rk1/pp2ppbp/nqp2np1/3p4/2PP1B2/1P1BPN2/P4PPP/RN1Q1RK1 w - - 1 9`
- **Lead-in:** 9. h3
- **Judged user moves:**
  - 9... Nb4 (Good, pre-move ES 0.41), reply 10. Be2
  - 10... Ne4 (Good, pre-move ES 0.39), reply 11. Nbd2
- **FEN before the answer move:** `r1b2rk1/pp2ppbp/1qp3p1/3p4/1nPPnB2/1P2PN1P/P2NBPP1/R2Q1RK1 b - - 4 11`
- **Answer:** blunder 11... c5 (pre-move ES 0.85, ES after 0.48).
- **Missed best move:** Nc3.
- **Score inputs:** facepalm score 0.654, played prob 0.028, material loss 0.000, material missed 3.355, reply prob 0.118, mate ply n/a.
- **Missed inputs:** missed gain 3.355, best move prob 0.457, pre-blunder spread 6.57.

#### Window 15: allowed (length 4, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=2081480&ply=17
- **User rating:** 1044 (pinned Maia Elo 1444)
- **FEN before the lead-in:** `r1b1kb1r/ppqp2pp/4pn2/8/2BQP3/8/PPP2PPP/RNB2RK1 b kq - 1 9`
- **Lead-in:** 9... Bc5
- **Judged user moves:**
  - 10. Qc3 (Good, pre-move ES 0.52), reply 10... Nxe4
  - 11. Qxg7 (Good, pre-move ES 0.73), reply 11... Rf8
- **FEN before the answer move:** `r1b1kr2/ppqp2Qp/4p3/2b5/2B1n3/8/PPP2PPP/RNB2RK1 w q - 1 12`
- **Answer:** blunder 12. Bxe6 (pre-move ES 0.71, ES after 0.18).
- **Refutation:** Nxf2.
- **Score inputs:** facepalm score 0.920, played prob 0.044, material loss 4.000, material missed 0.000, reply prob 0.246, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.024, pre-blunder spread 6.98.

#### Window 16: allowed (length 3, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=2494478&ply=6
- **User rating:** 1262 (pinned Maia Elo 1440)
- **FEN before the lead-in:** `rnbqkbnr/p1p1pp1p/1p1p2p1/8/3PP3/5N2/PPP2PPP/RNBQKB1R w KQkq - 0 4`
- **Lead-in:** 4. Nc3
- **Judged user moves:**
- **FEN before the answer move:** `rnbqkbnr/p1p1pp1p/1p1p2p1/8/3PP3/2N2N2/PPP2PPP/R1BQKB1R b KQkq - 1 4`
- **Answer:** blunder 4... c5 (pre-move ES 0.39, ES after 0.24).
- **Refutation:** dxc5.
- **Score inputs:** facepalm score 0.581, played prob 0.024, material loss 1.000, material missed 0.000, reply prob 0.279, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.435, pre-blunder spread 4.18.

#### Window 17: mixed (length 3, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=2278310&ply=47
- **User rating:** 1570 (pinned Maia Elo 1570)
- **FEN before the lead-in:** `1r5r/3nkpbp/2p1p1p1/3pP3/3PqPPR/2Q3N1/1PP3P1/1NK1R3 b - - 2 24`
- **Lead-in:** 24... Qxg2
- **Judged user moves:**
- **FEN before the answer move:** `1r5r/3nkpbp/2p1p1p1/3pP3/3P1PPR/2Q3N1/1PP3q1/1NK1R3 w - - 0 25`
- **Answer:** blunder 25. Qxc6 (pre-move ES 0.77, ES after 0.15).
- **Refutation:** Qxg3.
- **Missed best move:** Rhh1.
- **Score inputs:** facepalm score 0.940, played prob 0.022, material loss 2.677, material missed 0.129, reply prob 0.781, mate ply n/a.
- **Missed inputs:** missed gain 0.129, best move prob 0.044, pre-blunder spread 8.60.

#### Window 18: pure_miss (length 5, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=1941740&ply=30
- **User rating:** 1066 (pinned Maia Elo 1521)
- **FEN before the lead-in:** `r1b1kb1r/pp4p1/2pnpq1p/4N3/2BP1B2/2P5/PP4PP/R2Q1RK1 w - - 3 16`
- **Lead-in:** 16. Bxh6
- **Judged user moves:**
- **FEN before the answer move:** `r1b1kb1r/pp4p1/2pnpq1B/4N3/2BP4/2P5/PP4PP/R2Q1RK1 b - - 0 16`
- **Answer:** blunder 16... gxh6 (pre-move ES 0.65, ES after 0.06).
- **Missed best move:** Qxh6.
- **Score inputs:** facepalm score 0.999, played prob 0.005, material loss 5.000, material missed 3.000, reply prob 0.961, mate ply n/a.
- **Missed inputs:** missed gain 3.000, best move prob 0.927, pre-blunder spread 1.50.

#### Window 19: allowed (length 5, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=1997165&ply=8
- **User rating:** 1169 (pinned Maia Elo 1368)
- **FEN before the lead-in:** `r1b1k1nr/ppppqppp/2n5/2b1p3/8/1P2PN2/PBPP1PPP/RN1QKB1R w KQkq - 3 5`
- **Lead-in:** 5. Be2
- **Judged user moves:**
- **FEN before the answer move:** `r1b1k1nr/ppppqppp/2n5/2b1p3/8/1P2PN2/PBPPBPPP/RN1QK2R b KQkq - 4 5`
- **Answer:** blunder 5... Ba3 (pre-move ES 0.49, ES after 0.15).
- **Refutation:** Nxa3.
- **Score inputs:** facepalm score 0.887, played prob 0.015, material loss 3.000, material missed 0.000, reply prob 0.242, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.116, pre-blunder spread 5.34.

#### Window 20: herring (length 3, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2053428&ply=57
- **User rating:** 1437 (pinned Maia Elo 1437)
- **FEN before the lead-in:** `3r4/5B2/5n2/P1Rp1k1p/6p1/1P1P4/5PPP/6K1 b - - 0 29`
- **Lead-in:** 29... Ke5
- **Judged user moves:**
  - 30. a6 (Good, pre-move ES 0.82), reply 30... Rd7
  - 31. Bg6 (Good, pre-move ES 0.84), reply 31... Ra7
  - 32. Ra5 (Good, pre-move ES 0.82), reply 32... h4
- **Answer:** all safe (every judged move is Good).

### 1600-1999

#### Window 1: allowed (length 5, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=2215709&ply=88
- **User rating:** 1655 (pinned Maia Elo 1896)
- **FEN before the lead-in:** `3r1k2/R5R1/2p3P1/3b1r2/7P/P6K/8/8 w - - 0 45`
- **Lead-in:** 45. Rh7
- **Judged user moves:**
  - 45... Kg8 (Good, pre-move ES 0.50), reply 46. Rag7+
  - 46... Kf8 (Good, pre-move ES 0.50), reply 47. Ra7
- **FEN before the answer move:** `3r1k2/R6R/2p3P1/3b1r2/7P/P6K/8/8 b - - 5 47`
- **Answer:** blunder 47... Re8 (pre-move ES 0.50, ES after 0.02).
- **Refutation:** g7+.
- **Score inputs:** facepalm score 0.952, played prob 0.051, material loss 5.000, material missed 0.000, reply prob 0.191, mate ply 3.
- **Missed inputs:** missed gain 0.000, best move prob 0.281, pre-blunder spread 6.57.

#### Window 2: allowed (length 5, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=1975962&ply=32
- **User rating:** 1991 (pinned Maia Elo 1966)
- **FEN before the lead-in:** `r3k2r/ppp1n1p1/4P2p/2b2p2/4p2P/1BP5/PP3PP1/R1BqK2R w KQkq - 0 17`
- **Lead-in:** 17. Bxd1
- **Judged user moves:**
  - 17... Rd8 (Good, pre-move ES 0.57), reply 18. Bb3
  - 18... Ng6 (Good, pre-move ES 0.55), reply 19. h5
- **FEN before the answer move:** `3rk2r/ppp3p1/4P1np/2b2p1P/4p3/1BP5/PP3PP1/R1B1K2R b KQk - 0 19`
- **Answer:** blunder 19... Nf4 (pre-move ES 0.54, ES after 0.15).
- **Refutation:** Bxf4.
- **Score inputs:** facepalm score 0.843, played prob 0.040, material loss 1.581, material missed 0.000, reply prob 0.961, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.877, pre-blunder spread 1.68.

#### Window 3: allowed (length 4, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=569482&ply=22
- **User rating:** 1371 (pinned Maia Elo 1685)
- **FEN before the lead-in:** `r2q1rk1/ppp1bppp/4pn2/8/2pP4/P3PB1P/1P3PP1/R1BQ1RK1 w - - 0 12`
- **Lead-in:** 12. Bd2
- **Judged user moves:**
- **FEN before the answer move:** `r2q1rk1/ppp1bppp/4pn2/8/2pP4/P3PB1P/1P1B1PP1/R2Q1RK1 b - - 1 12`
- **Answer:** blunder 12... a6 (pre-move ES 0.47, ES after 0.32).
- **Refutation:** Bxb7.
- **Score inputs:** facepalm score 0.855, played prob 0.006, material loss 1.484, material missed 0.000, reply prob 0.543, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.317, pre-blunder spread 3.65.

#### Window 4: herring (length 4, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2699116&ply=16
- **User rating:** 1730 (pinned Maia Elo 1730)
- **FEN before the lead-in:** `rn1qk2r/pp3ppp/2pbpn2/8/2pP1B2/2NQPN2/PP3PPP/R3K2R w KQkq - 0 9`
- **Lead-in:** 9. Qxc4
- **Judged user moves:**
  - 9... Bxf4 (Good, pre-move ES 0.53), reply 10. exf4
  - 10... Nd5 (Good, pre-move ES 0.53), reply 11. g3
  - 11... O-O (Good, pre-move ES 0.52), reply 12. O-O
  - 12... Nd7 (Good, pre-move ES 0.52), reply 13. Nxd5
- **Answer:** all safe (every judged move is Good).

#### Window 5: herring (length 4, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2591279&ply=64
- **User rating:** 1788 (pinned Maia Elo 1965)
- **FEN before the lead-in:** `8/R2Rp1k1/4Bbp1/3K2pp/8/5P1P/PP6/3r4 w - - 3 33`
- **Lead-in:** 33. Kc6
- **Judged user moves:**
  - 33... Rc1+ (Good, pre-move ES 0.13), reply 34. Kb7
  - 34... Re1 (Good, pre-move ES 0.14), reply 35. Bd5
  - 35... Re2 (Good, pre-move ES 0.14), reply 36. b3
  - 36... Rh2 (Good, pre-move ES 0.10), reply 37. Kc8
- **Answer:** all safe (every judged move is Good).

#### Window 6: allowed (length 4, blunder at 4)

- **Game:** https://flawchess.com/analysis?game_id=2145322&ply=33
- **User rating:** 1885 (pinned Maia Elo 1885)
- **FEN before the lead-in:** `r3k2r/pp2npb1/2pRp1np/6p1/Q3P2q/N1P1BP1P/PP2BP1K/6R1 b kq - 0 17`
- **Lead-in:** 17... Be5+
- **Judged user moves:**
  - 18. Rg3 (Good, pre-move ES 0.16), reply 18... Bxd6
  - 19. Bd1 (Good, pre-move ES 0.17), reply 19... Bxg3+
  - 20. fxg3 (Good, pre-move ES 0.50), reply 20... Qh5
- **FEN before the answer move:** `r3k2r/pp2np2/2p1p1np/6pq/Q3P3/N1P1BPPP/PP5K/3B4 w kq - 1 21`
- **Answer:** blunder 21. Bf2 (pre-move ES 0.50, ES after 0.16).
- **Refutation:** g4.
- **Score inputs:** facepalm score 0.778, played prob 0.004, material loss 0.000, material missed 2.419, reply prob 0.105, mate ply n/a.
- **Missed inputs:** missed gain 2.419, best move prob 0.580, pre-blunder spread 4.68.

#### Window 7: allowed (length 3, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=2073870&ply=70
- **User rating:** 1728 (pinned Maia Elo 1932)
- **FEN before the lead-in:** `8/5rk1/4p2p/p4p2/P4R2/1Q4P1/2P1q1PK/8 w - - 10 36`
- **Lead-in:** 36. Rf3
- **Judged user moves:**
  - 36... Kg6 (Good, pre-move ES 0.50), reply 37. Re3
- **FEN before the answer move:** `8/5r2/4p1kp/p4p2/P7/1Q2R1P1/2P1q1PK/8 b - - 13 37`
- **Answer:** blunder 37... Qf2 (pre-move ES 0.49, ES after 0.18).
- **Refutation:** Qxe6+.
- **Score inputs:** facepalm score 0.741, played prob 0.006, material loss 1.032, material missed 0.000, reply prob 0.370, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.912, pre-blunder spread 1.59.

#### Window 8: allowed (length 5, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=1581179&ply=52
- **User rating:** 1396 (pinned Maia Elo 1702)
- **FEN before the lead-in:** `3bbr2/3n3k/3p1ppB/2p1pN1P/4P1P1/1PqP4/2P2P2/2Q2RK1 w - - 0 27`
- **Lead-in:** 27. Bxf8
- **Judged user moves:**
- **FEN before the answer move:** `3bbB2/3n3k/3p1pp1/2p1pN1P/4P1P1/1PqP4/2P2P2/2Q2RK1 b - - 0 27`
- **Answer:** blunder 27... Nxf8 (pre-move ES 0.15, ES after 0.02).
- **Refutation:** Qh6+.
- **Score inputs:** facepalm score 0.934, played prob 0.591, material loss 5.000, material missed 0.000, reply prob 0.626, mate ply 3.
- **Missed inputs:** missed gain 0.000, best move prob 0.152, pre-blunder spread 2.84.

#### Window 9: pure_miss (length 4, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=1432700&ply=9
- **User rating:** 1344 (pinned Maia Elo 1736)
- **FEN before the lead-in:** `r1bqkbnr/ppp2ppp/2np4/8/2P5/2N5/PP2PPPP/R1BQKBNR b KQkq - 1 5`
- **Lead-in:** 5... Bf5
- **Judged user moves:**
  - 6. e3 (Good, pre-move ES 0.57), reply 6... Nf6
  - 7. Bd3 (Good, pre-move ES 0.53), reply 7... Be7
- **FEN before the answer move:** `r2qk2r/ppp1bppp/2np1n2/5b2/2P5/2NBP3/PP3PPP/R1BQK1NR w KQkq - 3 8`
- **Answer:** blunder 8. Nf3 (pre-move ES 0.86, ES after 0.52).
- **Missed best move:** Bxf5.
- **Score inputs:** facepalm score 0.797, played prob 0.063, material loss 0.000, material missed 3.032, reply prob 0.453, mate ply n/a.
- **Missed inputs:** missed gain 3.032, best move prob 0.857, pre-blunder spread 1.88.

#### Window 10: allowed (length 5, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=3264358&ply=45
- **User rating:** 1777 (pinned Maia Elo 1892)
- **FEN before the lead-in:** `r3r1k1/pp1b1ppp/3Qpn2/3p4/1B1P4/P1RqP1P1/5PBP/5RK1 b - - 8 23`
- **Lead-in:** 23... Qg6
- **Judged user moves:**
  - 24. Rfc1 (Good, pre-move ES 0.43), reply 24... Bc6
- **FEN before the answer move:** `r3r1k1/pp3ppp/2bQpnq1/3p4/1B1P4/P1R1P1P1/5PBP/2R3K1 w - - 11 25`
- **Answer:** blunder 25. Bf1 (pre-move ES 0.43, ES after 0.24).
- **Refutation:** Ne4.
- **Score inputs:** facepalm score 0.609, played prob 0.054, material loss 0.452, material missed 0.000, reply prob 0.819, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.172, pre-blunder spread 13.59.

#### Window 11: allowed (length 3, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=1539709&ply=47
- **User rating:** 1849 (pinned Maia Elo 1849)
- **FEN before the lead-in:** `2R2rk1/4bppp/pQ1p4/1p6/4p3/8/PP2qPPP/4NRK1 b - - 0 24`
- **Lead-in:** 24... Rxc8
- **Judged user moves:**
  - 25. Qb7 (Good, pre-move ES 0.26), reply 25... Rc1
- **FEN before the answer move:** `6k1/1Q2bppp/p2p4/1p6/4p3/8/PP2qPPP/2r1NRK1 w - - 2 26`
- **Answer:** blunder 26. Qb8+ (pre-move ES 0.25, ES after 0.08).
- **Refutation:** Bf8.
- **Score inputs:** facepalm score 0.851, played prob 0.069, material loss 0.968, material missed 1.645, reply prob 1.000, mate ply n/a.
- **Missed inputs:** missed gain 1.645, best move prob 0.829, pre-blunder spread 2.14.

#### Window 12: allowed (length 3, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=550881&ply=68
- **User rating:** 1435 (pinned Maia Elo 1733)
- **FEN before the lead-in:** `r6k/1pp4p/3p2p1/r2P4/4Q1P1/p2P1PK1/R5P1/2q5 w - - 0 35`
- **Lead-in:** 35. Qe7
- **Judged user moves:**
- **FEN before the answer move:** `r6k/1pp1Q2p/3p2p1/r2P4/6P1/p2P1PK1/R5P1/2q5 b - - 1 35`
- **Answer:** blunder 35... Qc2 (pre-move ES 0.90, ES after 0.14).
- **Refutation:** Rxc2.
- **Score inputs:** facepalm score 0.996, played prob 0.001, material loss 5.000, material missed 0.226, reply prob 0.823, mate ply n/a.
- **Missed inputs:** missed gain 0.226, best move prob 0.364, pre-blunder spread 9.04.

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

- **Game:** https://flawchess.com/analysis?game_id=2759425&ply=5
- **User rating:** 1941 (pinned Maia Elo 1941)
- **FEN before the lead-in:** `rnbqk1nr/ppppbppp/8/4p3/2B1P3/2N5/PPPP1PPP/R1BQK1NR b KQkq - 3 3`
- **Lead-in:** 3... Nf6
- **Judged user moves:**
  - 4. d3 (Good, pre-move ES 0.54), reply 4... c6
  - 5. a4 (Good, pre-move ES 0.51), reply 5... d5
  - 6. exd5 (Good, pre-move ES 0.48), reply 6... cxd5
  - 7. Ba2 (Good, pre-move ES 0.43), reply 7... O-O
  - 8. Nge2 (Good, pre-move ES 0.46), reply 8... Be6
- **Answer:** all safe (every judged move is Good).

#### Window 15: allowed (length 5, blunder at 5)

- **Game:** https://flawchess.com/analysis?game_id=1580507&ply=56
- **User rating:** 1559 (pinned Maia Elo 1821)
- **FEN before the lead-in:** `r3r1k1/1p3pp1/2p1b2p/2q5/p3BQP1/3RKP2/2P4P/7R w - - 2 29`
- **Lead-in:** 29. Ke2
- **Judged user moves:**
  - 29... Qxc2+ (Good, pre-move ES 0.89), reply 30. Rd2
  - 30... Bc4+ (Good, pre-move ES 0.87), reply 31. Kf2
  - 31... Qc3 (Good, pre-move ES 0.85), reply 32. Rc2
  - 32... Qd4+ (Good, pre-move ES 0.85), reply 33. Kg3
- **FEN before the answer move:** `r3r1k1/1p3pp1/2p4p/8/p1bqBQP1/5PK1/2R4P/7R b - - 7 33`
- **Answer:** blunder 33... b5 (pre-move ES 0.85, ES after 0.25).
- **Refutation:** Bh7+.
- **Score inputs:** facepalm score 0.965, played prob 0.060, material loss 5.000, material missed 0.000, reply prob 0.308, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.017, pre-blunder spread 9.62.

#### Window 16: herring (length 3, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2077990&ply=22
- **User rating:** 1870 (pinned Maia Elo 1693)
- **FEN before the lead-in:** `rn1qr1k1/pp3ppp/3bpn2/3p4/3P4/2P1B2P/PP1NbPPN/R2Q1RK1 w - - 0 12`
- **Lead-in:** 12. Qxe2
- **Judged user moves:**
  - 12... Nbd7 (Good, pre-move ES 0.52), reply 13. Ng4
  - 13... h5 (Good, pre-move ES 0.52), reply 14. Nxf6+
  - 14... Nxf6 (Good, pre-move ES 0.48), reply 15. Bg5
- **Answer:** all safe (every judged move is Good).

#### Window 17: pure_miss (length 4, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=2420307&ply=44
- **User rating:** 1699 (pinned Maia Elo 1819)
- **FEN before the lead-in:** `4k2r/pp3pp1/2p1p2q/8/4n1p1/2P3P1/P3BQ1P/1R3RK1 w k - 1 23`
- **Lead-in:** 23. Qg2
- **Judged user moves:**
- **FEN before the answer move:** `4k2r/pp3pp1/2p1p2q/8/4n1p1/2P3P1/P3B1QP/1R3RK1 b k - 2 23`
- **Answer:** blunder 23... Nd2 (pre-move ES 0.55, ES after 0.16).
- **Missed best move:** Qe3+.
- **Score inputs:** facepalm score 0.813, played prob 0.241, material loss 1.000, material missed 2.968, reply prob 0.747, mate ply n/a.
- **Missed inputs:** missed gain 2.968, best move prob 0.436, pre-blunder spread 4.98.

#### Window 18: allowed (length 4, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=492456&ply=51
- **User rating:** 1712 (pinned Maia Elo 1969)
- **FEN before the lead-in:** `3r4/ppp3p1/5k2/5p1P/8/3P4/PP1NK2R/8 b - - 2 26`
- **Lead-in:** 26... Rd4
- **Judged user moves:**
  - 27. Rh3 (Good, pre-move ES 0.80), reply 27... Rg4
- **FEN before the answer move:** `8/ppp3p1/5k2/5p1P/6r1/3P3R/PP1NK3/8 w - - 5 28`
- **Answer:** blunder 28. Rf3 (pre-move ES 0.79, ES after 0.64).
- **Refutation:** Rh4.
- **Score inputs:** facepalm score 0.629, played prob 0.006, material loss 0.032, material missed 0.000, reply prob 0.517, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.052, pre-blunder spread 6.08.

#### Window 19: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2219845&ply=48
- **User rating:** 1411 (pinned Maia Elo 1714)
- **FEN before the lead-in:** `r5k1/2p2pp1/2pbp2p/8/1PQ2P2/P3B3/2P2Pq1/2KR4 w - - 1 25`
- **Lead-in:** 25. a4
- **Judged user moves:**
  - 25... Rxa4 (Good, pre-move ES 0.84), reply 26. Qb3
  - 26... Rxb4 (Good, pre-move ES 0.86), reply 27. Qa2
  - 27... Qe4 (Good, pre-move ES 0.87), reply 28. Qa8+
  - 28... Kh7 (Good, pre-move ES 0.88), reply 29. Qa2
  - 29... Bxf4 (Good, pre-move ES 0.89), reply 30. Qa3
- **Answer:** all safe (every judged move is Good).

#### Window 20: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=3264357&ply=29
- **User rating:** 1785 (pinned Maia Elo 1897)
- **FEN before the lead-in:** `r2qk2r/1p1bnpp1/p3p2p/nP1pP3/P1P5/N2B1N2/5PPP/R1Q1R1K1 b kq - 0 15`
- **Lead-in:** 15... Nb3
- **Judged user moves:**
  - 16. Qe3 (Good, pre-move ES 0.29), reply 16... Nxa1
  - 17. Rxa1 (Good, pre-move ES 0.29), reply 17... axb5
  - 18. Nxb5 (Good, pre-move ES 0.28), reply 18... dxc4
  - 19. Nd6+ (Good, pre-move ES 0.43), reply 19... Kf8
  - 20. Bxc4 (Good, pre-move ES 0.43), reply 20... Bc6
- **Answer:** all safe (every judged move is Good).

### 2000-2399

#### Window 1: allowed (length 5, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=574376&ply=18
- **User rating:** 1832 (pinned Maia Elo 2053)
- **FEN before the lead-in:** `rnbq1b1r/pp3kp1/4p2p/2pn4/2B5/5N2/PPP2PPP/R1BQK2R w KQ - 0 10`
- **Lead-in:** 10. O-O
- **Judged user moves:**
- **FEN before the answer move:** `rnbq1b1r/pp3kp1/4p2p/2pn4/2B5/5N2/PPP2PPP/R1BQ1RK1 b - - 1 10`
- **Answer:** blunder 10... Nf6 (pre-move ES 0.71, ES after 0.09).
- **Refutation:** Qxd8.
- **Score inputs:** facepalm score 0.995, played prob 0.003, material loss 5.000, material missed 0.000, reply prob 0.912, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.565, pre-blunder spread 3.47.

#### Window 2: pure_miss (length 5, blunder at 4)

- **Game:** https://flawchess.com/analysis?game_id=613048&ply=23
- **User rating:** 2168 (pinned Maia Elo 2243)
- **FEN before the lead-in:** `r3k2r/pp3ppp/2nppn2/1B1P3q/8/2N2Q1P/PPP2PP1/R3K2R b KQkq - 0 12`
- **Lead-in:** 12... Qxf3
- **Judged user moves:**
  - 13. gxf3 (Good, pre-move ES 0.49), reply 13... exd5
  - 14. O-O-O (Good, pre-move ES 0.50), reply 14... O-O-O
  - 15. Nxd5 (Good, pre-move ES 0.50), reply 15... Nd4
- **FEN before the answer move:** `2kr3r/pp3ppp/3p1n2/1B1N4/3n4/5P1P/PPP2P2/2KR3R w - - 1 16`
- **Answer:** blunder 16. Nxf6 (pre-move ES 0.87, ES after 0.53).
- **Missed best move:** Rxd4.
- **Score inputs:** facepalm score 0.932, played prob 0.007, material loss 0.000, material missed 3.226, reply prob 0.996, mate ply n/a.
- **Missed inputs:** missed gain 3.226, best move prob 0.984, pre-blunder spread 1.10.

#### Window 3: mixed (length 5, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=1508916&ply=12
- **User rating:** 1935 (pinned Maia Elo 2104)
- **FEN before the lead-in:** `r1b1kbnr/ppp3pp/2n1p3/3pP3/3P3q/3B4/PPP3PP/RNBQK1NR w KQkq - 2 7`
- **Lead-in:** 7. g3
- **Judged user moves:**
  - 7... Qxd4 (Good, pre-move ES 0.59), reply 8. Qh5+
- **FEN before the answer move:** `r1b1kbnr/ppp3pp/2n1p3/3pP2Q/3q4/3B2P1/PPP4P/RNB1K1NR b KQkq - 1 8`
- **Answer:** blunder 8... Ke7 (pre-move ES 0.75, ES after 0.37).
- **Refutation:** Nf3.
- **Missed best move:** g6.
- **Score inputs:** facepalm score 0.740, played prob 0.011, material loss 0.032, material missed 1.000, reply prob 0.643, mate ply n/a.
- **Missed inputs:** missed gain 1.000, best move prob 0.482, pre-blunder spread 2.76.

#### Window 4: mixed (length 5, blunder at 5)

- **Game:** https://flawchess.com/analysis?game_id=2660013&ply=83
- **User rating:** 1938 (pinned Maia Elo 2069)
- **FEN before the lead-in:** `5nk1/6b1/p3Np2/3P1Pp1/2p3qP/1P2RR2/Pn6/5K2 b - - 1 42`
- **Lead-in:** 42... cxb3
- **Judged user moves:**
  - 43. axb3 (Good, pre-move ES 0.13), reply 43... Qxh4
  - 44. d6 (Good, pre-move ES 0.13), reply 44... Qb4
  - 45. Nxf8 (Good, pre-move ES 0.13), reply 45... Kxf8
  - 46. d7 (Good, pre-move ES 0.15), reply 46... Qb5+
- **FEN before the answer move:** `5k2/3P2b1/p4p2/1q3Pp1/8/1P2RR2/1n6/5K2 w - - 1 47`
- **Answer:** blunder 47. Kf2 (pre-move ES 0.74, ES after 0.09).
- **Refutation:** Qxd7.
- **Missed best move:** Rd3.
- **Score inputs:** facepalm score 0.687, played prob 0.123, material loss 1.032, material missed 0.484, reply prob 0.878, mate ply n/a.
- **Missed inputs:** missed gain 0.484, best move prob 0.140, pre-blunder spread 4.11.

#### Window 5: herring (length 3, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2621085&ply=45
- **User rating:** 1974 (pinned Maia Elo 2087)
- **FEN before the lead-in:** `r3q1rk/1p5p/p1nb1n2/2Np4/1P1P1Nb1/PR4P1/1B4QP/5R1K b - - 2 23`
- **Lead-in:** 23... b6
- **Judged user moves:**
  - 24. Nxd5 (Good, pre-move ES 0.26), reply 24... Nxd5
  - 25. Qxd5 (Good, pre-move ES 0.22), reply 25... bxc5
  - 26. dxc5+ (Good, pre-move ES 0.32), reply 26... Be5
- **Answer:** all safe (every judged move is Good).

#### Window 6: allowed (length 3, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=2874053&ply=84
- **User rating:** 2114 (pinned Maia Elo 2114)
- **FEN before the lead-in:** `5R2/5bk1/p2rp3/1p1n3p/3N4/6P1/1r3PB1/4R1K1 w - - 2 43`
- **Lead-in:** 43. Ra8
- **Judged user moves:**
- **FEN before the answer move:** `R7/5bk1/p2rp3/1p1n3p/3N4/6P1/1r3PB1/4R1K1 b - - 3 43`
- **Answer:** blunder 43... Ra2 (pre-move ES 0.69, ES after 0.51).
- **Refutation:** Nxb5.
- **Score inputs:** facepalm score 0.552, played prob 0.031, material loss 1.000, material missed 0.000, reply prob 0.278, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.068, pre-blunder spread 10.85.

#### Window 7: herring (length 4, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=3020610&ply=41
- **User rating:** 2294 (pinned Maia Elo 2204)
- **FEN before the lead-in:** `2r2rk1/5pp1/p6p/1pbp1b2/4n2B/2PBN3/PP3PPP/R3R1K1 b - - 5 21`
- **Lead-in:** 21... Bh7
- **Judged user moves:**
  - 22. Nxd5 (Good, pre-move ES 0.58), reply 22... g5
  - 23. Bxe4 (Good, pre-move ES 0.72), reply 23... Bxe4
  - 24. Rxe4 (Good, pre-move ES 0.79), reply 24... gxh4
  - 25. Rxh4 (Good, pre-move ES 0.80), reply 25... Rcd8
- **Answer:** all safe (every judged move is Good).

#### Window 8: allowed (length 4, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=498038&ply=73
- **User rating:** 1954 (pinned Maia Elo 2077)
- **FEN before the lead-in:** `6k1/5p2/3p2p1/p1rP1n2/5P2/2pBb1P1/P1R4P/3R3K b - - 4 37`
- **Lead-in:** 37... Nd4
- **Judged user moves:**
- **FEN before the answer move:** `6k1/5p2/3p2p1/p1rP4/3n1P2/2pBb1P1/P1R4P/3R3K w - - 5 38`
- **Answer:** blunder 38. Rg2 (pre-move ES 0.43, ES after 0.27).
- **Refutation:** c2.
- **Score inputs:** facepalm score 0.655, played prob 0.329, material loss 2.032, material missed 0.000, reply prob 0.720, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.294, pre-blunder spread 6.12.

#### Window 9: allowed (length 4, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=2148155&ply=60
- **User rating:** 2022 (pinned Maia Elo 2087)
- **FEN before the lead-in:** `1nk5/1p1r1pp1/4p3/8/2P5/1P4q1/P3QRB1/6K1 w - - 2 31`
- **Lead-in:** 31. b4
- **Judged user moves:**
- **FEN before the answer move:** `1nk5/1p1r1pp1/4p3/8/1PP5/6q1/P3QRB1/6K1 b - - 0 31`
- **Answer:** blunder 31... Qa3 (pre-move ES 0.76, ES after 0.60).
- **Refutation:** Qh5.
- **Score inputs:** facepalm score 0.779, played prob 0.004, material loss 0.000, material missed 1.000, reply prob 0.049, mate ply n/a.
- **Missed inputs:** missed gain 1.000, best move prob 0.818, pre-blunder spread 2.59.

#### Window 10: allowed (length 3, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=2205576&ply=26
- **User rating:** 2162 (pinned Maia Elo 2162)
- **FEN before the lead-in:** `2bq1rk1/p4ppp/2p2n2/n1b1p3/4P3/PrN2N2/1PQ1BPPP/R1B2RK1 w - - 1 14`
- **Lead-in:** 14. Nxe5
- **Judged user moves:**
- **FEN before the answer move:** `2bq1rk1/p4ppp/2p2n2/n1b1N3/4P3/PrN5/1PQ1BPPP/R1B2RK1 b - - 0 14`
- **Answer:** blunder 14... Qb6 (pre-move ES 0.34, ES after 0.16).
- **Refutation:** Na4.
- **Score inputs:** facepalm score 0.918, played prob 0.014, material loss 2.226, material missed 0.065, reply prob 0.703, mate ply n/a.
- **Missed inputs:** missed gain 0.065, best move prob 0.140, pre-blunder spread 7.78.

#### Window 11: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=575006&ply=9
- **User rating:** 1913 (pinned Maia Elo 2092)
- **FEN before the lead-in:** `rn1qkbnr/pbp2ppp/1p2p3/3p4/2PP1B2/2N2N2/PP2PPPP/R2QKB1R b KQkq - 3 5`
- **Lead-in:** 5... Nf6
- **Judged user moves:**
  - 6. cxd5 (Good, pre-move ES 0.53), reply 6... exd5
  - 7. Bg5 (Good, pre-move ES 0.54), reply 7... Be7
  - 8. e3 (Good, pre-move ES 0.52), reply 8... h6
  - 9. Bh4 (Good, pre-move ES 0.54), reply 9... Nbd7
  - 10. Bg3 (Good, pre-move ES 0.52), reply 10... O-O
- **Answer:** all safe (every judged move is Good).

#### Window 12: herring (length 4, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2629912&ply=0
- **User rating:** 2031 (pinned Maia Elo 2031)
- **FEN before the lead-in:** `rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1`
- **Lead-in:** 1. f4
- **Judged user moves:**
  - 1... Nf6 (Good, pre-move ES 0.53), reply 2. Nf3
  - 2... g6 (Good, pre-move ES 0.53), reply 3. c4
  - 3... c5 (Good, pre-move ES 0.53), reply 4. Nc3
  - 4... Nc6 (Good, pre-move ES 0.52), reply 5. d3
- **Answer:** all safe (every judged move is Good).

#### Window 13: pure_miss (length 3, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=1233044&ply=59
- **User rating:** 2249 (pinned Maia Elo 2163)
- **FEN before the lead-in:** `8/q4ppk/7p/2bnpN2/1p6/4PP1P/1Q1B2P1/6K1 b - - 1 30`
- **Lead-in:** 30... g6
- **Judged user moves:**
- **FEN before the answer move:** `8/q4p1k/6pp/2bnpN2/1p6/4PP1P/1Q1B2P1/6K1 w - - 0 31`
- **Answer:** blunder 31. Ng3 (pre-move ES 0.41, ES after 0.15).
- **Missed best move:** Qxe5.
- **Score inputs:** facepalm score 0.636, played prob 0.111, material loss 1.000, material missed 0.419, reply prob 0.680, mate ply n/a.
- **Missed inputs:** missed gain 0.419, best move prob 0.810, pre-blunder spread 2.09.

#### Window 14: allowed (length 3, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=2837416&ply=48
- **User rating:** 2105 (pinned Maia Elo 2105)
- **FEN before the lead-in:** `r4r2/q3b1kp/b1n1p1p1/p2p1pP1/B2P1P2/4P2P/P2B1R2/2RQ2K1 w - - 0 25`
- **Lead-in:** 25. Bxc6
- **Judged user moves:**
  - 25... Rab8 (Good, pre-move ES 0.54), reply 26. Bxa5
  - 26... Bc4 (Good, pre-move ES 0.55), reply 27. Qa4
- **FEN before the answer move:** `1r3r2/q3b1kp/2B1p1p1/B2p1pP1/Q1bP1P2/4P2P/P4R2/2R3K1 b - - 2 27`
- **Answer:** blunder 27... Rb4 (pre-move ES 0.57, ES after 0.16).
- **Refutation:** Bxb4.
- **Score inputs:** facepalm score 0.915, played prob 0.017, material loss 2.000, material missed 0.484, reply prob 0.705, mate ply n/a.
- **Missed inputs:** missed gain 0.484, best move prob 0.494, pre-blunder spread 6.53.

#### Window 15: allowed (length 3, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=2445858&ply=43
- **User rating:** 1875 (pinned Maia Elo 2028)
- **FEN before the lead-in:** `r4qk1/pp4b1/4N1pp/3Pp3/5r2/4QN2/PP4K1/R2R4 b - - 1 22`
- **Lead-in:** 22... Rg4+
- **Judged user moves:**
  - 23. Kf2 (Good, pre-move ES 0.75), reply 23... Qf6
  - 24. Nxg7 (Good, pre-move ES 0.70), reply 24... Rf8
- **FEN before the answer move:** `5rk1/pp4N1/5qpp/3Pp3/6r1/4QN2/PP3K2/R2R4 w - - 1 25`
- **Answer:** blunder 25. Rf1 (pre-move ES 0.67, ES after 0.18).
- **Refutation:** e4.
- **Score inputs:** facepalm score 0.578, played prob 0.020, material loss 0.000, material missed 0.000, reply prob 0.395, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.819, pre-blunder spread 2.35.

#### Window 16: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2116100&ply=11
- **User rating:** 1844 (pinned Maia Elo 2001)
- **FEN before the lead-in:** `rnbq1rk1/ppp1ppbp/3p1np1/8/3P4/1P1BPN2/PBP2PPP/RN1QK2R b KQ - 2 6`
- **Lead-in:** 6... Re8
- **Judged user moves:**
  - 7. Nbd2 (Good, pre-move ES 0.51), reply 7... Nc6
  - 8. O-O (Good, pre-move ES 0.49), reply 8... Nh5
  - 9. c4 (Good, pre-move ES 0.52), reply 9... e5
  - 10. dxe5 (Good, pre-move ES 0.53), reply 10... Nxe5
  - 11. Nxe5 (Good, pre-move ES 0.52), reply 11... Bxe5
- **Answer:** all safe (every judged move is Good).

#### Window 17: allowed (length 3, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=613231&ply=53
- **User rating:** 2175 (pinned Maia Elo 2219)
- **FEN before the lead-in:** `b2r3r/P1pkB1p1/R1n1p3/5q2/2PPN2p/8/5PBP/3Q1RK1 b - - 0 27`
- **Lead-in:** 27... Kxe7
- **Judged user moves:**
- **FEN before the answer move:** `b2r3r/P1p1k1p1/R1n1p3/5q2/2PPN2p/8/5PBP/3Q1RK1 w - - 0 28`
- **Answer:** blunder 28. Nc5 (pre-move ES 0.75, ES after 0.47).
- **Refutation:** Rxd4.
- **Score inputs:** facepalm score 0.709, played prob 0.073, material loss 2.226, material missed 0.000, reply prob 0.305, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.668, pre-blunder spread 3.68.

#### Window 18: herring (length 4, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=2731502&ply=0
- **User rating:** 2148 (pinned Maia Elo 2148)
- **FEN before the lead-in:** `rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1`
- **Lead-in:** 1. d4
- **Judged user moves:**
  - 1... d5 (Good, pre-move ES 0.47), reply 2. Bg5
  - 2... f6 (Good, pre-move ES 0.52), reply 3. Bh4
  - 3... Nh6 (Good, pre-move ES 0.54), reply 4. e3
  - 4... c5 (Good, pre-move ES 0.57), reply 5. c3
- **Answer:** all safe (every judged move is Good).

#### Window 19: allowed (length 5, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=2653207&ply=69
- **User rating:** 2365 (pinned Maia Elo 2365)
- **FEN before the lead-in:** `6k1/q2n2p1/4Rp2/1p2pN2/1P1bP1P1/3P2B1/r4PBK/4Q3 b - - 2 35`
- **Lead-in:** 35... Bxf2
- **Judged user moves:**
  - 36. Bxf2 (Good, pre-move ES 0.83), reply 36... Rxf2
  - 37. Re8+ (Good, pre-move ES 0.82), reply 37... Nf8
- **FEN before the answer move:** `4Rnk1/q5p1/5p2/1p2pN2/1P2P1P1/3P4/5rBK/4Q3 w - - 2 38`
- **Answer:** blunder 38. d4 (pre-move ES 0.89, ES after 0.67).
- **Refutation:** Qa2.
- **Score inputs:** facepalm score 0.538, played prob 0.133, material loss 0.226, material missed 0.968, reply prob 0.736, mate ply n/a.
- **Missed inputs:** missed gain 0.968, best move prob 0.021, pre-blunder spread 7.07.

#### Window 20: allowed (length 5, blunder at 4)

- **Game:** https://flawchess.com/analysis?game_id=616643&ply=85
- **User rating:** 2275 (pinned Maia Elo 2280)
- **FEN before the lead-in:** `8/7R/r7/Pkp5/8/4P3/4K3/8 b - - 0 43`
- **Lead-in:** 43... Rxa5
- **Judged user moves:**
  - 44. Rc7 (Good, pre-move ES 0.50), reply 44... c4
  - 45. e4 (Good, pre-move ES 0.50), reply 45... Kb4
  - 46. Ke3 (Good, pre-move ES 0.50), reply 46... Kc3
- **FEN before the answer move:** `8/2R5/8/r7/2p1P3/2k1K3/8/8 w - - 3 47`
- **Answer:** blunder 47. e5 (pre-move ES 0.50, ES after 0.16).
- **Refutation:** Rxe5+.
- **Score inputs:** facepalm score 0.833, played prob 0.016, material loss 1.000, material missed 0.000, reply prob 0.976, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.007, pre-blunder spread 3.67.

### 2400+

#### Window 1: allowed (length 5, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=1523311&ply=73
- **User rating:** 2888 (pinned Maia Elo 2600)
- **FEN before the lead-in:** `8/p4Qkp/6p1/2pB1n2/2P5/1P4qP/P7/7K b - - 6 37`
- **Lead-in:** 37... Kh6
- **Judged user moves:**
  - 38. Qf8+ (Good, pre-move ES 0.48), reply 38... Kh5
- **FEN before the answer move:** `5Q2/p6p/6p1/2pB1n1k/2P5/1P4qP/P7/7K w - - 9 39`
- **Answer:** blunder 39. Qd8 (pre-move ES 0.50, ES after 0.14).
- **Refutation:** Qxh3+.
- **Score inputs:** facepalm score 0.901, played prob 0.001, material loss 1.032, material missed 0.484, reply prob 0.801, mate ply n/a.
- **Missed inputs:** missed gain 0.484, best move prob 0.416, pre-blunder spread 3.40.

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

- **Game:** https://flawchess.com/analysis?game_id=657367&ply=46
- **User rating:** 2619 (pinned Maia Elo 2572)
- **FEN before the lead-in:** `1r1q1r1k/5ppp/b2p3b/2nNpN2/4PPQ1/Pp4P1/1P4BP/R3R2K w - - 9 24`
- **Lead-in:** 24. Rad1
- **Judged user moves:**
  - 24... Bc8 (Good, pre-move ES 0.40), reply 25. Nde7
- **FEN before the answer move:** `1rbq1r1k/4Nppp/3p3b/2n1pN2/4PPQ1/Pp4P1/1P4BP/3RR2K b - - 12 25`
- **Answer:** blunder 25... g6 (pre-move ES 0.80, ES after 0.45).
- **Missed best move:** Qxe7.
- **Score inputs:** facepalm score 0.588, played prob 0.098, material loss 0.000, material missed 3.000, reply prob 0.345, mate ply n/a.
- **Missed inputs:** missed gain 3.000, best move prob 0.593, pre-blunder spread 4.46.

#### Window 5: allowed (length 4, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=1531955&ply=48
- **User rating:** 3016 (pinned Maia Elo 2600)
- **FEN before the lead-in:** `2r4r/pN2kpp1/2n1p1bp/8/1P2P3/6P1/P5BP/R1R3K1 w - - 1 25`
- **Lead-in:** 25. a3
- **Judged user moves:**
  - 25... Nd4 (Good, pre-move ES 0.53), reply 26. Kf2
- **FEN before the answer move:** `2r4r/pN2kpp1/4p1bp/8/1P1nP3/P5P1/5KBP/R1R5 b - - 2 26`
- **Answer:** blunder 26... Kf6 (pre-move ES 0.62, ES after 0.44).
- **Refutation:** Nd6.
- **Score inputs:** facepalm score 0.546, played prob 0.013, material loss 0.000, material missed 0.000, reply prob 0.258, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.713, pre-blunder spread 2.83.

#### Window 6: allowed (length 4, blunder at 3)

- **Game:** https://flawchess.com/analysis?game_id=657317&ply=87
- **User rating:** 2588 (pinned Maia Elo 2546)
- **FEN before the lead-in:** `7k/p3q2p/8/4bPr1/4B3/P4Q2/7P/3R3K b - - 20 44`
- **Lead-in:** 44... Bc7
- **Judged user moves:**
  - 45. f6 (Good, pre-move ES 0.51), reply 45... Qe5
  - 46. Rd2 (Good, pre-move ES 0.50), reply 46... Qc5
- **FEN before the answer move:** `7k/p1b4p/5P2/2q3r1/4B3/P4Q2/3R3P/7K w - - 3 47`
- **Answer:** blunder 47. Rg2 (pre-move ES 0.52, ES after 0.02).
- **Refutation:** Qc1+.
- **Score inputs:** facepalm score 0.619, played prob 0.136, material loss 1.129, material missed 0.000, reply prob 0.796, mate ply 5.
- **Missed inputs:** missed gain 0.000, best move prob 0.048, pre-blunder spread 3.80.

#### Window 7: allowed (length 3, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=1509297&ply=38
- **User rating:** 2900 (pinned Maia Elo 2600)
- **FEN before the lead-in:** `r3k1nr/p3b1p1/1pp2pq1/3p3p/3N1B1P/Q1Nn4/PP3PP1/R3R1K1 w kq - 6 20`
- **Lead-in:** 20. Nxc6
- **Judged user moves:**
- **FEN before the answer move:** `r3k1nr/p3b1p1/1pN2pq1/3p3p/5B1P/Q1Nn4/PP3PP1/R3R1K1 b kq - 0 20`
- **Answer:** blunder 20... Nxf4 (pre-move ES 0.17, ES after 0.02).
- **Refutation:** Rxe7+.
- **Score inputs:** facepalm score 0.884, played prob 0.032, material loss 1.387, material missed 1.032, reply prob 0.856, mate ply n/a.
- **Missed inputs:** missed gain 1.032, best move prob 0.878, pre-blunder spread 1.78.

#### Window 8: allowed (length 5, blunder at 4)

- **Game:** https://flawchess.com/analysis?game_id=1523305&ply=99
- **User rating:** 2926 (pinned Maia Elo 2600)
- **FEN before the lead-in:** `8/5pk1/6pp/8/3Rp1P1/7P/1r4P1/5K2 b - - 0 50`
- **Lead-in:** 50... f5
- **Judged user moves:**
  - 51. gxf5 (Good, pre-move ES 0.50), reply 51... gxf5
  - 52. Rd7+ (Good, pre-move ES 0.50), reply 52... Kf6
  - 53. Rd6+ (Good, pre-move ES 0.46), reply 53... Ke5
- **FEN before the answer move:** `8/8/3R3p/4kp2/4p3/7P/1r4P1/5K2 w - - 4 54`
- **Answer:** blunder 54. Rd8 (pre-move ES 0.50, ES after 0.23).
- **Refutation:** Kf4.
- **Score inputs:** facepalm score 0.751, played prob 0.021, material loss 0.000, material missed 1.000, reply prob 0.691, mate ply n/a.
- **Missed inputs:** missed gain 1.000, best move prob 0.958, pre-blunder spread 1.27.

#### Window 9: pure_miss (length 4, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=1523636&ply=86
- **User rating:** 2449 (pinned Maia Elo 2449)
- **FEN before the lead-in:** `8/1p3p2/6p1/7p/2P3kP/1P2R1P1/5r2/2K5 w - - 7 44`
- **Lead-in:** 44. b4
- **Judged user moves:**
- **FEN before the answer move:** `8/1p3p2/6p1/7p/1PP3kP/4R1P1/5r2/2K5 b - - 0 44`
- **Answer:** blunder 44... b6 (pre-move ES 0.66, ES after 0.51).
- **Missed best move:** Rf3.
- **Score inputs:** facepalm score 0.578, played prob 0.016, material loss 0.000, material missed 1.000, reply prob 0.239, mate ply n/a.
- **Missed inputs:** missed gain 1.000, best move prob 0.616, pre-blunder spread 3.44.

#### Window 10: herring (length 4, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=1520203&ply=9
- **User rating:** 2509 (pinned Maia Elo 2509)
- **FEN before the lead-in:** `r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/2PP1N2/PP3PPP/RNBQK2R b KQkq - 0 5`
- **Lead-in:** 5... O-O
- **Judged user moves:**
  - 6. O-O (Good, pre-move ES 0.53), reply 6... h6
  - 7. a4 (Good, pre-move ES 0.53), reply 7... a5
  - 8. Re1 (Good, pre-move ES 0.52), reply 8... d6
  - 9. Nbd2 (Good, pre-move ES 0.52), reply 9... Bb6
- **Answer:** all safe (every judged move is Good).

#### Window 11: allowed (length 3, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=654533&ply=48
- **User rating:** 2495 (pinned Maia Elo 2441)
- **FEN before the lead-in:** `2r1k3/5ppp/2b1pn2/1B2n3/8/BP2P3/P4PPP/3R2K1 w - - 7 25`
- **Lead-in:** 25. Rc1
- **Judged user moves:**
- **FEN before the answer move:** `2r1k3/5ppp/2b1pn2/1B2n3/8/BP2P3/P4PPP/2R3K1 b - - 8 25`
- **Answer:** blunder 25... Ra8 (pre-move ES 0.61, ES after 0.20).
- **Refutation:** Rxc6.
- **Score inputs:** facepalm score 0.940, played prob 0.036, material loss 3.000, material missed 0.000, reply prob 0.805, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.657, pre-blunder spread 3.45.

#### Window 12: allowed (length 3, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=1515918&ply=59
- **User rating:** 2630 (pinned Maia Elo 2502)
- **FEN before the lead-in:** `r2r2k1/pp3pp1/2p3b1/5P1p/2P3P1/1P2Q2P/Pq4B1/3R1RK1 b - - 0 30`
- **Lead-in:** 30... Bh7
- **Judged user moves:**
- **FEN before the answer move:** `r2r2k1/pp3ppb/2p5/5P1p/2P3P1/1P2Q2P/Pq4B1/3R1RK1 w - - 1 31`
- **Answer:** blunder 31. g5 (pre-move ES 0.67, ES after 0.34).
- **Refutation:** Rxd1.
- **Score inputs:** facepalm score 0.792, played prob 0.018, material loss 1.000, material missed 0.097, reply prob 0.727, mate ply n/a.
- **Missed inputs:** missed gain 0.097, best move prob 0.243, pre-blunder spread 5.43.

#### Window 13: herring (length 4, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=1506169&ply=24
- **User rating:** 3046 (pinned Maia Elo 2600)
- **FEN before the lead-in:** `r1bq1rk1/1p3pp1/1bpp1nnp/p3p3/P1B1P3/2PP1NNP/1P3PP1/R1BQR1K1 w - - 0 13`
- **Lead-in:** 13. d4
- **Judged user moves:**
  - 13... Bc7 (Good, pre-move ES 0.50), reply 14. Bb3
  - 14... Re8 (Good, pre-move ES 0.46), reply 15. dxe5
  - 15... dxe5 (Good, pre-move ES 0.48), reply 16. Be3
  - 16... Qe7 (Good, pre-move ES 0.49), reply 17. Nf5
- **Answer:** all safe (every judged move is Good).

#### Window 14: allowed (length 3, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=657313&ply=49
- **User rating:** 2620 (pinned Maia Elo 2573)
- **FEN before the lead-in:** `3r1k2/p2q2bQ/1p3r2/n2Pp1N1/2p1Pp2/2P5/P2B1PP1/3R1RK1 b - - 7 25`
- **Lead-in:** 25... Rh6
- **Judged user moves:**
- **FEN before the answer move:** `3r1k2/p2q2bQ/1p5r/n2Pp1N1/2p1Pp2/2P5/P2B1PP1/3R1RK1 w - - 8 26`
- **Answer:** blunder 26. Ne6+ (pre-move ES 0.57, ES after 0.35).
- **Refutation:** Qxe6.
- **Score inputs:** facepalm score 0.618, played prob 0.112, material loss 1.000, material missed 0.000, reply prob 0.795, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.870, pre-blunder spread 1.59.

#### Window 15: herring (length 5, no blunder)

- **Game:** https://flawchess.com/analysis?game_id=1516915&ply=32
- **User rating:** 2845 (pinned Maia Elo 2600)
- **FEN before the lead-in:** `r3rnk1/2pq2p1/1pp2p2/p3p2p/P3P1PN/3PB2b/1PP2P1P/R2Q2RK w - - 0 17`
- **Lead-in:** 17. gxh5
- **Judged user moves:**
  - 17... Kh7 (Good, pre-move ES 0.18), reply 18. Qf3
  - 18... Be6 (Good, pre-move ES 0.12), reply 19. h6
  - 19... g6 (Good, pre-move ES 0.13), reply 20. Qxf6
  - 20... Qf7 (Good, pre-move ES 0.12), reply 21. Qxf7+
  - 21... Bxf7 (Good, pre-move ES 0.16), reply 22. Nf3
- **Answer:** all safe (every judged move is Good).

#### Window 16: allowed (length 5, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=1520695&ply=71
- **User rating:** 2856 (pinned Maia Elo 2600)
- **FEN before the lead-in:** `1r4k1/1q3p1p/1r1p2p1/p3b3/4P3/1PP4P/2QN2P1/1R2R2K b - - 3 36`
- **Lead-in:** 36... Rc6
- **Judged user moves:**
  - 37. Nc4 (Good, pre-move ES 0.43), reply 37... Qb5
- **FEN before the answer move:** `1r4k1/5p1p/2rp2p1/pq2b3/2N1P3/1PP4P/2Q3P1/1R2R2K w - - 6 38`
- **Answer:** blunder 38. Na3 (pre-move ES 0.49, ES after 0.34).
- **Refutation:** Rxc3.
- **Score inputs:** facepalm score 0.607, played prob 0.007, material loss 1.000, material missed 0.000, reply prob 0.192, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.274, pre-blunder spread 5.70.

#### Window 17: allowed (length 4, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=1530000&ply=77
- **User rating:** 2958 (pinned Maia Elo 2600)
- **FEN before the lead-in:** `1k4Q1/1pb5/2p5/p5q1/P1Np4/3P2rp/1P3RPB/5R1K b - - 0 39`
- **Lead-in:** 39... Qxg8
- **Judged user moves:**
  - 40. Rf8+ (Good, pre-move ES 0.51), reply 40... Ka7
- **FEN before the answer move:** `5Rq1/kpb5/2p5/p7/P1Np4/3P2rp/1P4PB/5R1K w - - 2 41`
- **Answer:** blunder 41. gxh3 (pre-move ES 0.52, ES after 0.03).
- **Refutation:** Qd5+.
- **Score inputs:** facepalm score 0.971, played prob 0.023, material loss 0.677, material missed 5.000, reply prob 0.804, mate ply n/a.
- **Missed inputs:** missed gain 5.000, best move prob 0.930, pre-blunder spread 1.41.

#### Window 18: allowed (length 3, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=657170&ply=89
- **User rating:** 2540 (pinned Maia Elo 2491)
- **FEN before the lead-in:** `8/6p1/p4p2/1p1k1P2/6K1/1P6/P6P/8 b - - 0 45`
- **Lead-in:** 45... Ke4
- **Judged user moves:**
- **FEN before the answer move:** `8/6p1/p4p2/1p3P2/4k1K1/1P6/P6P/8 w - - 1 46`
- **Answer:** blunder 46. Kh5 (pre-move ES 0.49, ES after 0.11).
- **Refutation:** Kxf5.
- **Score inputs:** facepalm score 0.869, played prob 0.007, material loss 1.000, material missed 0.000, reply prob 0.998, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.079, pre-blunder spread 3.22.

#### Window 19: mixed (length 4, blunder at 1)

- **Game:** https://flawchess.com/analysis?game_id=642630&ply=46
- **User rating:** 2562 (pinned Maia Elo 2516)
- **FEN before the lead-in:** `3k4/pp6/2b1p3/8/5Q1P/P1q1Pp2/2P5/4KBN1 w - - 0 24`
- **Lead-in:** 24. Kd1
- **Judged user moves:**
- **FEN before the answer move:** `3k4/pp6/2b1p3/8/5Q1P/P1q1Pp2/2P5/3K1BN1 b - - 1 24`
- **Answer:** blunder 24... e5 (pre-move ES 0.52, ES after 0.15).
- **Refutation:** Qf8+.
- **Missed best move:** Qa1+.
- **Score inputs:** facepalm score 0.800, played prob 0.052, material loss 0.000, material missed 2.742, reply prob 0.452, mate ply n/a.
- **Missed inputs:** missed gain 2.742, best move prob 0.885, pre-blunder spread 1.68.

#### Window 20: allowed (length 3, blunder at 2)

- **Game:** https://flawchess.com/analysis?game_id=658671&ply=89
- **User rating:** 2670 (pinned Maia Elo 2600)
- **FEN before the lead-in:** `5n2/6k1/2R3p1/3N1p1p/1PB1p1n1/1KP3P1/6r1/8 b - - 10 45`
- **Lead-in:** 45... Rxg3
- **Judged user moves:**
  - 46. Rc7+ (Good, pre-move ES 0.40), reply 46... Kh6
- **FEN before the answer move:** `5n2/2R5/6pk/3N1p1p/1PB1p1n1/1KP3r1/8/8 w - - 2 47`
- **Answer:** blunder 47. Ne7 (pre-move ES 0.37, ES after 0.18).
- **Refutation:** h4.
- **Score inputs:** facepalm score 0.601, played prob 0.019, material loss 0.000, material missed 0.000, reply prob 0.521, mate ply n/a.
- **Missed inputs:** missed gain 0.000, best move prob 0.852, pre-blunder spread 1.99.
