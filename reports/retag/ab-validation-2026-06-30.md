# FlawChess A/B Gate Validation Report

**Generated:** 2026-06-30 17:20:19 UTC
**Script:** `scripts/ab_validate_gate.py`
**DB:** dev, user-id 28
**Scope:** player's own flaws only (opponent flaws excluded via player_only_gate)
**Margin tested:** 0.35 (ONLY_MOVE_WIN_PROB_MARGIN default: 0.35)
**Total blob-bearing flaws loaded:** 3359

## Executive Summary

| Metric | Count |
|--------|-------|
| Ungated tags (allowed) | 1298 |
| Gated survived (allowed) | 583 |
| Gate suppressed (allowed) | 715 (55.1%) |
| Ungated tags (missed) | 1096 |
| Gated survived (missed) | 344 |
| Gate suppressed (missed) | 752 (68.6%) |

| Total dropped cases | 1467 |

## Per-Motif: Allowed Orientation

| Motif | Ungated | Suppressed | Survived | Suppression % | Note |
|-------|---------|------------|----------|---------------|------|
| ATTRACTION | 29 | 20 | 9 | 69.0% |  |
| BACK_RANK_MATE | 15 | 0 | 15 | 0.0% |  |
| CAPTURING_DEFENDER | 16 | 11 | 5 | 68.8% |  |
| CLEARANCE | 202 | 196 | 6 | 97.0% |  |
| DEFLECTION | 38 | 16 | 22 | 42.1% |  |
| DISCOVERED_ATTACK | 77 | 45 | 32 | 58.4% |  |
| DISCOVERED_CHECK | 29 | 23 | 6 | 79.3% |  |
| DOUBLE_CHECK | 1 | 0 | 1 | 0.0% | small-N (N<10) |
| DOVETAIL_MATE | 1 | 0 | 1 | 0.0% | small-N (N<10) |
| EN_PASSANT | 5 | 4 | 1 | 80.0% | small-N (N<10) |
| FORK | 156 | 67 | 89 | 42.9% |  |
| HANGING_PIECE | 188 | 50 | 138 | 26.6% |  |
| INTERFERENCE | 6 | 5 | 1 | 83.3% | small-N (N<10) |
| INTERMEZZO | 24 | 17 | 7 | 70.8% |  |
| MATE | 158 | 41 | 117 | 25.9% |  |
| PIN | 146 | 107 | 39 | 73.3% |  |
| PROMOTION | 36 | 25 | 11 | 69.4% |  |
| SACRIFICE | 107 | 52 | 55 | 48.6% |  |
| SKEWER | 40 | 24 | 16 | 60.0% |  |
| SMOTHERED_MATE | 2 | 0 | 2 | 0.0% | small-N (N<10) |
| TRAPPED_PIECE | 22 | 12 | 10 | 54.5% |  |

## Per-Motif: Missed Orientation

| Motif | Ungated | Suppressed | Survived | Suppression % | Note |
|-------|---------|------------|----------|---------------|------|
| ATTRACTION | 26 | 13 | 13 | 50.0% |  |
| BACK_RANK_MATE | 1 | 0 | 1 | 0.0% | small-N (N<10) |
| CAPTURING_DEFENDER | 24 | 21 | 3 | 87.5% |  |
| CLEARANCE | 251 | 239 | 12 | 95.2% |  |
| DEFLECTION | 35 | 22 | 13 | 62.9% |  |
| DISCOVERED_ATTACK | 65 | 45 | 20 | 69.2% |  |
| DISCOVERED_CHECK | 21 | 12 | 9 | 57.1% |  |
| DOUBLE_CHECK | 2 | 2 | 0 | 100.0% | small-N (N<10) |
| EN_PASSANT | 8 | 8 | 0 | 100.0% | small-N (N<10) |
| FORK | 142 | 79 | 63 | 55.6% |  |
| HANGING_PIECE | 59 | 22 | 37 | 37.3% |  |
| HOOK_MATE | 3 | 0 | 3 | 0.0% | small-N (N<10) |
| INTERFERENCE | 8 | 6 | 2 | 75.0% | small-N (N<10) |
| INTERMEZZO | 7 | 7 | 0 | 100.0% | small-N (N<10) |
| MATE | 91 | 0 | 91 | 0.0% |  |
| PIN | 123 | 90 | 33 | 73.2% |  |
| PROMOTION | 16 | 11 | 5 | 68.8% |  |
| SACRIFICE | 155 | 126 | 29 | 81.3% |  |
| SELF_INTERFERENCE | 1 | 1 | 0 | 100.0% | small-N (N<10) |
| SKEWER | 30 | 28 | 2 | 93.3% |  |
| SMOTHERED_MATE | 3 | 0 | 3 | 0.0% | small-N (N<10) |
| TRAPPED_PIECE | 21 | 16 | 5 | 76.2% |  |
| UNDER_PROMOTION | 2 | 2 | 0 | 100.0% | small-N (N<10) |
| X_RAY | 2 | 2 | 0 | 100.0% | small-N (N<10) |

## Depth-Shift Distribution

### Allowed Orientation

| Motif | Arm | Depth 0 | Depth 1 | Depth 2 | Depth 3+ | Mean |
|-------|-----|---------|---------|---------|----------|------|
| ATTRACTION | ungated | 12 | 0 | 6 | 11 | 1.6 |
| ATTRACTION | gated | 6 | 0 | 2 | 1 | 0.8 |
| BACK_RANK_MATE | ungated | 6 | 0 | 8 | 1 | 1.3 |
| BACK_RANK_MATE | gated | 6 | 0 | 8 | 1 | 1.3 |
| CAPTURING_DEFENDER | ungated | 0 | 0 | 6 | 10 | 2.6 |
| CAPTURING_DEFENDER | gated | 0 | 0 | 3 | 2 | 2.4 |
| CLEARANCE | ungated | 0 | 0 | 36 | 166 | 2.8 |
| CLEARANCE | gated | 0 | 0 | 2 | 4 | 2.7 |
| DEFLECTION | ungated | 0 | 0 | 19 | 19 | 2.5 |
| DEFLECTION | gated | 0 | 0 | 16 | 6 | 2.3 |
| DISCOVERED_ATTACK | ungated | 0 | 41 | 0 | 36 | 1.9 |
| DISCOVERED_ATTACK | gated | 0 | 22 | 0 | 10 | 1.6 |
| DISCOVERED_CHECK | ungated | 12 | 0 | 6 | 11 | 1.6 |
| DISCOVERED_CHECK | gated | 5 | 0 | 1 | 0 | 0.3 |
| DOUBLE_CHECK | ungated | 1 | 0 | 0 | 0 | 0.0 |
| DOUBLE_CHECK | gated | 1 | 0 | 0 | 0 | 0.0 |
| DOVETAIL_MATE | ungated | 1 | 0 | 0 | 0 | 0.0 |
| DOVETAIL_MATE | gated | 1 | 0 | 0 | 0 | 0.0 |
| EN_PASSANT | ungated | 1 | 0 | 3 | 1 | 1.8 |
| EN_PASSANT | gated | 0 | 0 | 1 | 0 | 2.0 |
| FORK | ungated | 95 | 0 | 34 | 27 | 1.0 |
| FORK | gated | 68 | 0 | 17 | 4 | 0.5 |
| HANGING_PIECE | ungated | 188 | 0 | 0 | 0 | 0.0 |
| HANGING_PIECE | gated | 138 | 0 | 0 | 0 | 0.0 |
| INTERFERENCE | ungated | 0 | 0 | 2 | 4 | 2.7 |
| INTERFERENCE | gated | 0 | 0 | 1 | 0 | 2.0 |
| INTERMEZZO | ungated | 0 | 0 | 16 | 8 | 2.3 |
| INTERMEZZO | gated | 0 | 0 | 7 | 0 | 2.0 |
| MATE | ungated | 59 | 0 | 33 | 66 | 1.7 |
| MATE | gated | 56 | 0 | 31 | 30 | 1.3 |
| PIN | ungated | 78 | 0 | 24 | 44 | 1.2 |
| PIN | gated | 30 | 0 | 5 | 4 | 0.6 |
| PROMOTION | ungated | 7 | 0 | 7 | 22 | 2.2 |
| PROMOTION | gated | 4 | 0 | 4 | 3 | 1.5 |
| SACRIFICE | ungated | 0 | 0 | 33 | 74 | 2.7 |
| SACRIFICE | gated | 0 | 0 | 20 | 35 | 2.6 |
| SKEWER | ungated | 0 | 0 | 23 | 17 | 2.4 |
| SKEWER | gated | 0 | 0 | 11 | 5 | 2.3 |
| SMOTHERED_MATE | ungated | 0 | 0 | 0 | 2 | 3.0 |
| SMOTHERED_MATE | gated | 0 | 0 | 0 | 2 | 3.0 |
| TRAPPED_PIECE | ungated | 0 | 0 | 13 | 9 | 2.4 |
| TRAPPED_PIECE | gated | 0 | 0 | 8 | 2 | 2.2 |

### Missed Orientation

| Motif | Arm | Depth 0 | Depth 1 | Depth 2 | Depth 3+ | Mean |
|-------|-----|---------|---------|---------|----------|------|
| ATTRACTION | ungated | 16 | 0 | 3 | 7 | 1.0 |
| ATTRACTION | gated | 11 | 0 | 2 | 0 | 0.3 |
| BACK_RANK_MATE | ungated | 1 | 0 | 0 | 0 | 0.0 |
| BACK_RANK_MATE | gated | 1 | 0 | 0 | 0 | 0.0 |
| CAPTURING_DEFENDER | ungated | 0 | 0 | 9 | 15 | 2.6 |
| CAPTURING_DEFENDER | gated | 0 | 0 | 2 | 1 | 2.3 |
| CLEARANCE | ungated | 0 | 0 | 59 | 192 | 2.8 |
| CLEARANCE | gated | 0 | 0 | 9 | 3 | 2.2 |
| DEFLECTION | ungated | 0 | 0 | 15 | 20 | 2.6 |
| DEFLECTION | gated | 0 | 0 | 9 | 4 | 2.3 |
| DISCOVERED_ATTACK | ungated | 0 | 34 | 0 | 31 | 2.0 |
| DISCOVERED_ATTACK | gated | 0 | 18 | 0 | 2 | 1.2 |
| DISCOVERED_CHECK | ungated | 6 | 0 | 4 | 11 | 2.0 |
| DISCOVERED_CHECK | gated | 3 | 0 | 2 | 4 | 1.8 |
| DOUBLE_CHECK | ungated | 0 | 0 | 0 | 2 | 3.0 |
| DOUBLE_CHECK | gated | 0 | 0 | 0 | 0 | 0.0 |
| EN_PASSANT | ungated | 0 | 0 | 0 | 8 | 3.0 |
| EN_PASSANT | gated | 0 | 0 | 0 | 0 | 0.0 |
| FORK | ungated | 61 | 0 | 37 | 44 | 1.5 |
| FORK | gated | 37 | 0 | 19 | 7 | 0.9 |
| HANGING_PIECE | ungated | 59 | 0 | 0 | 0 | 0.0 |
| HANGING_PIECE | gated | 37 | 0 | 0 | 0 | 0.0 |
| HOOK_MATE | ungated | 1 | 0 | 1 | 1 | 1.7 |
| HOOK_MATE | gated | 1 | 0 | 1 | 1 | 1.7 |
| INTERFERENCE | ungated | 0 | 0 | 5 | 3 | 2.4 |
| INTERFERENCE | gated | 0 | 0 | 2 | 0 | 2.0 |
| INTERMEZZO | ungated | 0 | 0 | 0 | 7 | 3.0 |
| INTERMEZZO | gated | 0 | 0 | 0 | 0 | 0.0 |
| MATE | ungated | 15 | 0 | 21 | 55 | 2.3 |
| MATE | gated | 15 | 0 | 21 | 55 | 2.3 |
| PIN | ungated | 53 | 0 | 22 | 48 | 1.5 |
| PIN | gated | 26 | 0 | 5 | 2 | 0.5 |
| PROMOTION | ungated | 1 | 0 | 4 | 11 | 2.6 |
| PROMOTION | gated | 0 | 0 | 0 | 5 | 3.0 |
| SACRIFICE | ungated | 0 | 0 | 66 | 89 | 2.6 |
| SACRIFICE | gated | 0 | 0 | 20 | 9 | 2.3 |
| SELF_INTERFERENCE | ungated | 0 | 0 | 1 | 0 | 2.0 |
| SELF_INTERFERENCE | gated | 0 | 0 | 0 | 0 | 0.0 |
| SKEWER | ungated | 0 | 0 | 10 | 20 | 2.7 |
| SKEWER | gated | 0 | 0 | 1 | 1 | 2.5 |
| SMOTHERED_MATE | ungated | 0 | 0 | 1 | 2 | 2.7 |
| SMOTHERED_MATE | gated | 0 | 0 | 1 | 2 | 2.7 |
| TRAPPED_PIECE | ungated | 0 | 0 | 8 | 13 | 2.6 |
| TRAPPED_PIECE | gated | 0 | 0 | 5 | 0 | 2.0 |
| UNDER_PROMOTION | ungated | 0 | 0 | 0 | 2 | 3.0 |
| UNDER_PROMOTION | gated | 0 | 0 | 0 | 0 | 0.0 |
| X_RAY | ungated | 0 | 0 | 0 | 2 | 3.0 |
| X_RAY | gated | 0 | 0 | 0 | 0 | 0.0 |

## Dropped Cases — Hand-Check Required (HUMAN-UAT)

_Showing the first 1000 of 1467 dropped cases (capped by MAX_REPORTED_DROPPED_CASES)._

| # | Orientation | Motif | Depth | Moves | Game | FEN |
|---|-------------|-------|-------|-------|------|-----|
| 1 | missed | DISCOVERED_CHECK | 2 | `8... Nxe4 9. Be3` | [ply 15](http://localhost:5173/analysis?game_id=681354&ply=15) | [board](http://localhost:5173/analysis?fen=r3kb1r/ppp2ppp/2n2n2/4p1B1/4P1b1/2P2N1P/PP3PP1/RN1K1B1R%20b%20-%20-%200%208) |
| 2 | missed | CLEARANCE | 2 | `26... Rd8 27. h5 R2d6 28. h6 Rh8 29. h7 Rd7 30. Rh6 Rd6 31. Rh5 Rd7 32. Rxf5` | [ply 51](http://localhost:5173/analysis?game_id=681354&ply=51) | [board](http://localhost:5173/analysis?fen=8/1kp5/2nr4/pBp1pp2/P6P/2P2P2/1P1r1P2/1R2K2R%20b%20-%20-%200%2026) |
| 3 | allowed | INTERMEZZO | 2 | `22... c3 23. Qc1 Qxb4+ 24. Ka1 Rab8 25. Re3 Qa5 26. Bf1 Rb2 27. Bc4 Ba4 28. Rxc3` | [ply 42](http://localhost:5173/analysis?game_id=681357&ply=42) | [board](http://localhost:5173/analysis?fen=r3r1k1/5pp1/p1b4p/8/1Pp1P3/q3Q1P1/P1P2PBP/1K1RR3%20b%20-%20-%200%2022) |
| 4 | allowed | ATTRACTION | 0 | `26... Rxb1+ 27. Kxb1 Qb4+ 28. Kc1 c3 29. Bf1 Bd7 30. Bd3 Bg4 31. f3 Be6 32. Kd1` | [ply 50](http://localhost:5173/analysis?game_id=681357&ply=50) | [board](http://localhost:5173/analysis?fen=1r4k1/5pp1/p1b4p/8/q1p1P3/4Q1P1/P1P2PBP/KR6%20b%20-%20-%201%2026) |
| 5 | missed | SACRIFICE | 2 | `35. Kc1 Qxe4 36. exf7 Qe1+ 37. Kb2 c3+ 38. Kb3 Qe6+ 39. Kb4 Qc4+ 40. Ka5 Qxf7` | [ply 68](http://localhost:5173/analysis?game_id=681357&ply=68) | [board](http://localhost:5173/analysis?fen=1Q6/5p1k/p3P1pp/1b6/2pqB3/6P1/2PK1P1P/8%20w%20-%20-%200%2035) |
| 6 | allowed | MATE | 8 | `37... Qe1+ 38. Kg2 Bf1+ 39. Kf3 Qe2+ 40. Kf4 g5+ 41. Kf5 Qxe6#` | [ply 72](http://localhost:5173/analysis?game_id=681357&ply=72) | [board](http://localhost:5173/analysis?fen=1Q6/5p1k/p3P1pp/1b6/4q3/2p3P1/2P2P1P/6K1%20b%20-%20-%201%2037) |
| 7 | missed | SACRIFICE | 2 | `37. Qxb5 axb5 38. exf7 Kg7 39. f8=Q+ Kxf8 40. g4 Qxc2 41. Kg2 Ke7 42. h3 Qe4+` | [ply 72](http://localhost:5173/analysis?game_id=681357&ply=72) | [board](http://localhost:5173/analysis?fen=1Q6/5p1k/p3P1pp/1b6/4q3/2p3P1/2P2P1P/5K2%20w%20-%20-%200%2037) |
| 8 | missed | SACRIFICE | 8 | `41. Qf4 Qxg4+ 42. Qxg4 hxg4+ 43. Kg3 Ba4 44. h3 Bxc2 45. f4 gxf3 46. Kxf3 Bf5` | [ply 80](http://localhost:5173/analysis?game_id=681357&ply=80) | [board](http://localhost:5173/analysis?fen=1Q6/5p1k/p1b1q1p1/7p/6P1/2p4K/2P2P1P/8%20w%20-%20-%200%2041) |
| 9 | missed | PIN | 6 | `6. Ndb5 d5 7. Bf4 Na6 8. exd5 e5 9. Qe2 Qe7 10. d6 Qe6 11. Be3 Nf6` | [ply 10](http://localhost:5173/analysis?game_id=681358&ply=10) | [board](http://localhost:5173/analysis?fen=rnbqk1nr/pp1p1pbp/4p1p1/8/3NP3/2N5/PPP2PPP/R1BQKB1R%20w%20-%20-%200%206) |
| 10 | missed | CLEARANCE | 2 | `11. Nf3 Na5 12. Qd6 f5 13. Re1 fxe4 14. Nxe4 Bxe4 15. Rxe4 Bxb2 16. Be5 Nf5` | [ply 20](http://localhost:5173/analysis?game_id=681358&ply=20) | [board](http://localhost:5173/analysis?fen=r2qk2r/1b1pnpbp/p1n1p1p1/1p6/3NP3/1BN3B1/PPP2PPP/R2Q1K1R%20w%20-%20-%200%2011) |
| 11 | allowed | CLEARANCE | 2 | `e8g8 f1e2 f8e8 e2f3 b7b5 e1g1 a7a5 f1e1 c8a6 e4e5 d7d6 e5e6` | [ply 20](http://localhost:5173/analysis?game_id=681359&ply=20) | [board](http://localhost:5173/analysis?fen=r1b1k2r/pp1p1pbp/5np1/2pP4/4P2q/2PQ2N1/P4PPP/R1B1KB1R%20b%20-%20-%201%2011) |
| 12 | missed | CLEARANCE | 4 | `15. Be3 Bd7 16. a4 b6 17. Ra2 Rae8 18. Bf2 Qf4 19. Rd1 Nh5 20. Nxh5 Rxh5` | [ply 28](http://localhost:5173/analysis?game_id=681359&ply=28) | [board](http://localhost:5173/analysis?fen=r1b3k1/pp3pbp/3p1np1/2pPr3/4P2q/2PQ1PN1/P3B1PP/R1B2RK1%20w%20-%20-%200%2015) |
| 13 | allowed | CLEARANCE | 8 | `20... Re8 21. e5 Rf8 22. e6 fxe6 23. dxe6 Ne5 24. Qd5 Re7 25. Rae1 Bxe6 26. Qd1` | [ply 38](http://localhost:5173/analysis?game_id=681359&ply=38) | [board](http://localhost:5173/analysis?fen=2b3k1/pr1n1pbp/1pQ3p1/1BpPr3/4Pq2/2P2PN1/P5PP/R4RK1%20b%20-%20-%201%2020) |
| 14 | missed | FORK | 4 | `8... Qb4+ 9. Qd2 Qxb2 10. Qc3 Qc1+ 11. Ke2` | [ply 15](http://localhost:5173/analysis?game_id=681360&ply=15) | [board](http://localhost:5173/analysis?fen=r1b1k2r/ppp1qppp/2n1pn2/3P2N1/8/3PQ3/PPP2PPP/RN2KB1R%20b%20-%20-%200%208) |
| 15 | allowed | FORK | 2 | `16. Rxe6 fxe6 17. Nxe6 Rde8 18. Nxf8 Kxf8 19. Be2 Nf5 20. Bd1 g5 21. Kd2 a5` | [ply 29](http://localhost:5173/analysis?game_id=681360&ply=29) | [board](http://localhost:5173/analysis?fen=3r1rk1/1p2npp1/p1p1bn1p/3p4/3N4/P1NP4/1PP2PPP/2K1RB1R%20w%20-%20-%200%2016) |
| 16 | missed | SACRIFICE | 2 | `15... Nf5 16. Nxe6 Rde8 17. g3 Rxe6 18. Bh3 Rxe1+ 19. Rxe1 Nd4 20. Bg2 Re8 21. Rxe8+` | [ply 29](http://localhost:5173/analysis?game_id=681360&ply=29) | [board](http://localhost:5173/analysis?fen=3r1rk1/pp2npp1/2p1bn1p/3p4/3N4/P1NP4/1PP2PPP/2K1RB1R%20b%20-%20-%200%2015) |
| 17 | allowed | HANGING_PIECE | 0 | `17. gxh3` | [ply 31](http://localhost:5173/analysis?game_id=681365&ply=31) | [board](http://localhost:5173/analysis?fen=r2q1rk1/2p2ppp/6n1/p2p4/3Pn3/PQ2PN1b/1P2BPP1/R1B2RK1%20w%20-%20-%200%2017) |
| 18 | missed | PIN | 0 | `7... Bxe2 8. Qxe2` | [ply 13](http://localhost:5173/analysis?game_id=681368&ply=13) | [board](http://localhost:5173/analysis?fen=r2qk2r/ppp2ppp/2n1pn2/3pN3/1b1P1Bb1/2N1P3/PPP1BPPP/R2QK2R%20b%20-%20-%200%207) |
| 19 | missed | SACRIFICE | 4 | `25... Rxc2 26. Bxg7+ Qxg7 27. Kxc2 Rf2+ 28. Kd1 Qg2 29. Qe5+ Kg8 30. Qg3+ Qxg3 31. hxg3` | [ply 49](http://localhost:5173/analysis?game_id=681368&ply=49) | [board](http://localhost:5173/analysis?fen=5r1k/p5pp/4Q3/3pB3/3Pp3/PK2P3/2P2rqP/R3R3%20b%20-%20-%200%2025) |
| 20 | missed | PIN | 6 | `26. Kf2 Rb8 27. b3 a5 28. Rh1 Ke7 29. Rh7 Kf7 30. Rh3 a4 31. Re3 Ra8` | [ply 50](http://localhost:5173/analysis?game_id=681369&ply=50) | [board](http://localhost:5173/analysis?fen=7r/2pk2p1/p2p1p2/2pP1Pp1/2P3P1/8/PP4P1/4R1K1%20w%20-%20-%200%2026) |
| 21 | missed | DISCOVERED_ATTACK | 3 | `11. Nxd5 Bb7 12. Nf6+ Nxf6 13. Rxd8+ Rxd8 14. Bd2 Nd7 15. Qg4 Rg8 16. Bg5 a6` | [ply 20](http://localhost:5173/analysis?game_id=681372&ply=20) | [board](http://localhost:5173/analysis?fen=r1bqk1nr/p3bppp/1pn1p3/3pP3/2B2Q2/2N2N2/PPP2PPP/R1BR2K1%20w%20-%20-%200%2011) |
| 22 | missed | DEFLECTION | 4 | `12. Ne4 Nh6 13. Nf6+ gxf6 14. Qxh6 Bf8 15. Qh5 a6 16. Bxc6+ Bxc6 17. Be3 f5` | [ply 22](http://localhost:5173/analysis?game_id=681372&ply=22) | [board](http://localhost:5173/analysis?fen=r2qk1nr/pb2bppp/1pn1p3/1B1pP3/5Q2/2N2N2/PPP2PPP/R1BR2K1%20w%20-%20-%200%2012) |
| 23 | missed | SACRIFICE | 2 | `17. Rxd4 exd4 18. g5 dxc3 19. gxf6 Bxf6 20. bxc3 g6 21. Qh3 Qe7 22. Be3 Bc8` | [ply 32](http://localhost:5173/analysis?game_id=681372&ply=32) | [board](http://localhost:5173/analysis?fen=r2q3r/pb2bkpp/1p3n2/1B1ppQ2/3n2P1/2N5/PPP2P1P/R1BR2K1%20w%20-%20-%200%2017) |
| 24 | missed | FORK | 0 | `35. Re5+ Kd8 36. Rd5+ Ke8 37. Rxc5 R8g7 38. Rc8+ Kf7 39. Rc7+ Kf8 40. Rcxg7 Rxg7` | [ply 68](http://localhost:5173/analysis?game_id=681372&ply=68) | [board](http://localhost:5173/analysis?fen=4k1r1/p6R/8/1pb2R2/6r1/P5B1/1PP2P1P/5K2%20w%20-%20-%200%2035) |
| 25 | allowed | PIN | 2 | `6. Bb5+ Nfd7 7. Qe2 Nc6 8. Nf3 Bc5 9. fxe5` | [ply 9](http://localhost:5173/analysis?game_id=681377&ply=9) | [board](http://localhost:5173/analysis?fen=rnbqkb1r/pp3ppp/5n2/3pp3/2B2P2/2N5/PPPP2PP/R1BQK1NR%20w%20-%20-%200%206) |
| 26 | missed | CLEARANCE | 8 | `5... e4 6. dxc6 Nxc6 7. d3 Bg4 8. Nge2 Qb6 9. dxe4 Rd8 10. Bd3 Bc5 11. Kf1` | [ply 9](http://localhost:5173/analysis?game_id=681377&ply=9) | [board](http://localhost:5173/analysis?fen=rnbqkb1r/pp3ppp/2p2n2/3Pp3/2B2P2/2N5/PPPP2PP/R1BQK1NR%20b%20-%20-%200%205) |
| 27 | missed | SACRIFICE | 2 | `17... Bxg4 18. hxg4 Qf3 19. Qf1 Re6 20. g5 Qxf4+ 21. Kg2 Qxg5+ 22. Kxf2 Rf6+ 23. Ke1` | [ply 33](http://localhost:5173/analysis?game_id=681377&ply=33) | [board](http://localhost:5173/analysis?fen=4rrk1/pp3ppp/8/3qp2b/5PP1/2P4P/PP1PRb1K/R1BQ4%20b%20-%20-%200%2017) |
| 28 | allowed | CLEARANCE | 8 | `5. dxc6 bxc6 6. Nc3 Be7 7. Bd3` | [ply 7](http://localhost:5173/analysis?game_id=681378&ply=7) | [board](http://localhost:5173/analysis?fen=r1bqkb1r/ppp2ppp/2np1n2/3Pp3/4P3/5N2/PPP2PPP/RNBQKB1R%20w%20-%20-%201%205) |
| 29 | missed | CLEARANCE | 2 | `15... Bh4 16. Qf3 Qg5+ 17. Kb1 Bg4 18. Qd3 dxc3 19. f3 Rfd8 20. Qxc3 Bf5 21. Qxe5` | [ply 29](http://localhost:5173/analysis?game_id=681378&ply=29) | [board](http://localhost:5173/analysis?fen=r1bq1rk1/pp3pp1/5b1p/4p3/3pB3/2N3Q1/PPP2PPP/2KR3R%20b%20-%20-%200%2015) |
| 30 | missed | DISCOVERED_CHECK | 10 | `25... Bd5 26. Qh5 g6 27. Qg4 Be6 28. Qb4 Rd1+ 29. Kb2 Bc1+ 30. Ka1 Ba3+ 31. Qb1` | [ply 49](http://localhost:5173/analysis?game_id=681378&ply=49) | [board](http://localhost:5173/analysis?fen=6k1/p4pp1/B3b2p/4p1b1/8/2P2Q1P/2Pr1PP1/1K6%20b%20-%20-%200%2025) |
| 31 | allowed | PIN | 4 | `6... Nxd5 7. exd5 Qxd5 8. Nc3 Bb4 9. Bd2 Bxc3 10. Bxc3 exd4 11. Bxd4` | [ply 10](http://localhost:5173/analysis?game_id=681380&ply=10) | [board](http://localhost:5173/analysis?fen=r1bqkb1r/1pp1nppp/p1n5/3Bp3/3PP3/5N2/PPP2PPP/RNBQK2R%20b%20-%20-%200%206) |
| 32 | missed | CLEARANCE | 4 | `8. dxc6 Qxc6` | [ply 14](http://localhost:5173/analysis?game_id=681380&ply=14) | [board](http://localhost:5173/analysis?fen=r1b1kb1r/1pp2ppp/p1nq4/3Pp3/3P4/5N2/PPP2PPP/RNBQK2R%20w%20-%20-%200%208) |
| 33 | missed | INTERFERENCE | 2 | `14. Rc5 Qe6 15. Rxc7 Qd6 16. Rc5 Re8 17. Be3 b6 18. Rg5 f6 19. Rg3 Bf5` | [ply 26](http://localhost:5173/analysis?game_id=681380&ply=26) | [board](http://localhost:5173/analysis?fen=r1b2rk1/1pp2ppp/p7/4R3/2qP4/2P5/P1P2PPP/R1BQ2K1%20w%20-%20-%200%2014) |
| 34 | allowed | HANGING_PIECE | 0 | `15... gxh6 16. Qf3` | [ply 28](http://localhost:5173/analysis?game_id=681380&ply=28) | [board](http://localhost:5173/analysis?fen=r1b2rk1/1pp1R1pp/p4p1B/8/2qP4/2P5/P1P2PPP/R2Q2K1%20b%20-%20-%201%2015) |
| 35 | allowed | DISCOVERED_ATTACK | 3 | `20... Re8 21. a3 Bd7 22. Qd2 Rxe1+ 23. Qxe1 Qe6 24. Qxe6+ Kxe6 25. c4 Ba4 26. f3` | [ply 38](http://localhost:5173/analysis?game_id=681380&ply=38) | [board](http://localhost:5173/analysis?fen=1r6/1pp2k1p/p3bppB/8/2qP4/2P1Q3/P1P2PPP/4R1K1%20b%20-%20-%201%2020) |
| 36 | allowed | PIN | 8 | `23... Rxe3 24. Rxe3 Qd1+ 25. Kg2 Qxg4+ 26. Kf1 Qxh4 27. Rd3 Bb5 28. Be3 Bxd3+ 29. cxd3` | [ply 44](http://localhost:5173/analysis?game_id=681380&ply=44) | [board](http://localhost:5173/analysis?fen=4r3/1ppb1k1p/p4ppB/3q4/6PP/2P1Q3/P1P2P2/4R1K1%20b%20-%20-%200%2023) |
| 37 | missed | SACRIFICE | 10 | `27. f3 Qa4 28. Kf2 Qxc2+ 29. Kf1 Qb1+ 30. Kf2 Qb2+ 31. Kg1 Qxc3 32. h5 g5` | [ply 52](http://localhost:5173/analysis?game_id=681380&ply=52) | [board](http://localhost:5173/analysis?fen=8/1pp2k1p/p1b2ppB/8/6qP/2P3R1/P1P2PK1/8%20w%20-%20-%200%2027) |
| 38 | missed | SACRIFICE | 2 | `29. Kf1 Qxh6 30. Re3 Qh1+ 31. Ke2 Qg2 32. Rd3 g5 33. Rd4 h5 34. Kd2 b5` | [ply 56](http://localhost:5173/analysis?game_id=681380&ply=56) | [board](http://localhost:5173/analysis?fen=8/1pp2k1p/p1b2ppB/8/7q/2P3R1/P1P2P2/6K1%20w%20-%20-%200%2029) |
| 39 | allowed | PIN | 0 | `9. Qe2 Nc6` | [ply 15](http://localhost:5173/analysis?game_id=681384&ply=15) | [board](http://localhost:5173/analysis?fen=rnb1kb1r/pppp3p/6p1/1B3p1Q/4q3/8/PPPP1PPP/R1B1K2R%20w%20-%20-%200%209) |
| 40 | allowed | PIN | 0 | `20... Rxe3+ 21. Kf1 Rf8 22. Nf3 Rexf3 23. gxf3 Rxf3 24. Qg2 Rxd3 25. Qg8+ Bf8 26. Rg1` | [ply 38](http://localhost:5173/analysis?game_id=681385&ply=38) | [board](http://localhost:5173/analysis?fen=2k1r2r/pp1n2Qp/2p5/8/1b1N3q/2PPB3/PP3PPP/R3K2R%20b%20-%20-%201%2020) |
| 41 | missed | HANGING_PIECE | 0 | `23. fxe3 Bc5 24. Re1 Nd7 25. Nf3 Qa4 26. d4 Be7 27. e4 Qxa2 28. Re2 a5` | [ply 44](http://localhost:5173/analysis?game_id=681385&ply=44) | [board](http://localhost:5173/analysis?fen=2k2n2/pp5p/2p5/8/1b1N3q/2PPr3/PP3PPP/R4K1R%20w%20-%20-%200%2023) |
| 42 | missed | HANGING_PIECE | 0 | `33. gxf4 Rd1 34. Rxc6+ Kb8 35. Rcc7 a5 36. bxa5 b4 37. Rcf7 Rd8 38. f5 Rh8` | [ply 64](http://localhost:5173/analysis?game_id=681385&ply=64) | [board](http://localhost:5173/analysis?fen=2k5/p5R1/2p1R3/1p6/1P3n2/6P1/PP3PK1/7r%20w%20-%20-%200%2033) |
| 43 | missed | PIN | 0 | `41. Kd4 Kc7 42. f8=Q Ne6+ 43. Kd3 Nxf8 44. Kxe2 Ne6 45. Ra8 Kd6 46. Rxa7 c5` | [ply 80](http://localhost:5173/analysis?game_id=681385&ply=80) | [board](http://localhost:5173/analysis?fen=2kn2R1/p4P2/2p5/1p2K3/8/6P1/4r3/8%20w%20-%20-%200%2041) |
| 44 | missed | DEFLECTION | 10 | `5. d5 gxf3 6. dxc6 dxc6 7. Qxf3 Be6 8. Nc3 Qd4 9. Qh5+ Bf7 10. Qxf5 Bg6` | [ply 8](http://localhost:5173/analysis?game_id=681387&ply=8) | [board](http://localhost:5173/analysis?fen=r1bqkbnr/ppppp2p/2n5/4Pp2/3P2p1/5N2/PPP2PPP/RNBQKB1R%20w%20-%20-%200%205) |
| 45 | missed | DISCOVERED_CHECK | 4 | `8. Qe2 Nd7 9. Nxe5 Qxg2 10. Nf3+ Kd8 11. Rg1 Qh3 12. Ng5 Qxh2 13. Nxf7+ Kc7` | [ply 14](http://localhost:5173/analysis?game_id=681388&ply=14) | [board](http://localhost:5173/analysis?fen=rnb1kb1r/pp3ppp/2q5/2p1p3/2B5/1P3N2/P1PP1PPP/R1BQK2R%20w%20-%20-%200%208) |
| 46 | missed | DISCOVERED_ATTACK | 3 | `11. Bb2 Be6 12. Nxf7 Qxb2 13. Rxe6 Nc6 14. Ne5 Kh8 15. Nxc6 Bh4 16. Rb1 Bxf2+` | [ply 20](http://localhost:5173/analysis?game_id=681388&ply=20) | [board](http://localhost:5173/analysis?fen=rnb2rk1/pp2bppp/5q2/2p1N3/2B5/1P6/P1PP1PPP/R1BQR1K1%20w%20-%20-%200%2011) |
| 47 | allowed | DEFLECTION | 8 | `13... Nc6 14. Ba3 Bf5 15. c3 b5 16. d4 b4 17. cxb4 cxd4 18. Rc1 Rc8 19. Qf3` | [ply 24](http://localhost:5173/analysis?game_id=681388&ply=24) | [board](http://localhost:5173/analysis?fen=rnb5/pp2bkpp/5q2/2p5/8/1P1P4/P1P2PPP/R1BQR1K1%20b%20-%20-%200%2013) |
| 48 | missed | CLEARANCE | 2 | `14. Rxe7+ Kf8 15. Qe1 Nc6 16. Re8+ Kf7 17. c3 h6 18. d4 Rb8 19. d5 Bd7` | [ply 26](http://localhost:5173/analysis?game_id=681388&ply=26) | [board](http://localhost:5173/analysis?fen=rnb5/pp2bkpp/8/2p5/8/1P1P4/P1P2PPP/q1BQR1K1%20w%20-%20-%200%2014) |
| 49 | allowed | SACRIFICE | 6 | `21... Bxg5 22. Qg3 Be7 23. Rxe5 Kf8 24. Qxg4 c4 25. Kf1 cxb3 26. axb3 Rd8 27. Qf3` | [ply 40](http://localhost:5173/analysis?game_id=681388&ply=40) | [board](http://localhost:5173/analysis?fen=r3k3/p3b1qp/1p4p1/2pPn1B1/5Pb1/1P2Q3/P1P3PP/4R1K1%20b%20-%20-%201%2021) |
| 50 | allowed | ATTRACTION | 6 | `10. Bxc6 Bxh2+ 11. Nxh2 Bxc6 12. Re1+ Ne4 13. Qxd8+ Kxd8 14. Rd1+ Kc8 15. Nf1 b6` | [ply 17](http://localhost:5173/analysis?game_id=681389&ply=17) | [board](http://localhost:5173/analysis?fen=r2qk2r/pppb1ppp/2n2n2/1B2b3/8/5N2/PPP2PPP/RNBQ1RK1%20w%20-%20-%201%2010) |
| 51 | missed | SACRIFICE | 4 | `e8c8 b1d2 e7b4 b5c6 e5h2 f3h2 d7c6 d1c1 h7h6 c2c3 b4b5 g5f4` | [ply 21](http://localhost:5173/analysis?game_id=681389&ply=21) | [board](http://localhost:5173/analysis?fen=r3k2r/pppbqppp/2n2n2/1B2b1B1/8/5N2/PPP2PPP/RN1QR1K1%20b%20-%20-%200%2011) |
| 52 | allowed | DEFLECTION | 2 | `31. Re7+ Kc8 32. bxc6 a6 33. Rxf7 Qd5 34. Rxg7 Qxa5 35. h3 Qa1 36. Ra7 Qa4` | [ply 59](http://localhost:5173/analysis?game_id=681390&ply=59) | [board](http://localhost:5173/analysis?fen=8/pk3pp1/2p4p/PP6/8/4R3/6PP/3q2NK%20w%20-%20-%200%2031) |
| 53 | missed | SACRIFICE | 2 | `22. Kh1 Nxe1 23. Qxe1 a6 24. Qe5 Qb8 25. Qd4 Qc7 26. a4 bxa4 27. h4 Rxc6` | [ply 42](http://localhost:5173/analysis?game_id=681392&ply=42) | [board](http://localhost:5173/analysis?fen=3q1r2/p4pk1/1rB2n1p/1p1P1Pp1/1Pp5/2Nn4/P3Q1PP/4RRK1%20w%20-%20-%200%2022) |
| 54 | missed | PIN | 0 | `7... Qe7 8. Bf4 Nh5 9. g3 Nxf4 10. gxf4 Qh4 11. Qe3 g5 12. f5 Qd4 13. Nc3` | [ply 13](http://localhost:5173/analysis?game_id=681394&ply=13) | [board](http://localhost:5173/analysis?fen=r1bqkb1r/pp1p1ppp/5n2/2p1P3/8/3Q4/PPP2PPP/RNB1KB1R%20b%20-%20-%200%207) |
| 55 | allowed | FORK | 8 | `12. exf6 Bxd5 13. cxd5 gxf6 14. Bxf6 Rg8 15. d6 c4 16. dxe7 Qxd3 17. Bxd3 cxd3` | [ply 21](http://localhost:5173/analysis?game_id=681394&ply=21) | [board](http://localhost:5173/analysis?fen=r2qkb1r/pp2n1pp/4bp2/2pNP1B1/2P5/3Q4/PP3PPP/R3KB1R%20w%20-%20-%200%2012) |
| 56 | allowed | ATTRACTION | 2 | `15. Qf5 Qd7 16. Qxd7+ Kxd7 17. Rxd5+ Ke6 18. Bc4 Kf5 19. Re1 g4 20. Rd7 Re8` | [ply 27](http://localhost:5173/analysis?game_id=681394&ply=27) | [board](http://localhost:5173/analysis?fen=r2qkb1r/pp4pp/8/2pbP1p1/8/3Q4/PP2BPPP/2KR3R%20w%20-%20-%200%2015) |
| 57 | missed | CLEARANCE | 8 | `9... Bxc3 10. bxc3 Nc6 11. h3 h6 12. Bg3 b6 13. Bh4 Bb7 14. Bd3 Ne7 15. Qb1` | [ply 17](http://localhost:5173/analysis?game_id=681396&ply=17) | [board](http://localhost:5173/analysis?fen=rnbq1rk1/pp3ppp/4pn2/2p5/1bBP1B2/P1N1P3/1P2NPPP/R2Q1RK1%20b%20-%20-%200%209) |
| 58 | missed | HANGING_PIECE | 0 | `19... Rxd6 20. Nf4 Qe5 21. bxa7 Bb7 22. Rfd1 Nxa7 23. Bf1 Rxd1 24. Rxd1 g5 25. Nh5` | [ply 37](http://localhost:5173/analysis?game_id=681396&ply=37) | [board](http://localhost:5173/analysis?fen=r1br2k1/p4ppp/1PnNp3/7q/1PB5/P3P1P1/2Q1NP2/R4RK1%20b%20-%20-%200%2019) |
| 59 | missed | CLEARANCE | 2 | `20. Be3 Kf7 21. Rac1 Kg8 22. Qf2 Nd8 23. Qc2 Rf7 24. b4 Ne6 25. a4 Kh7` | [ply 38](http://localhost:5173/analysis?game_id=681397&ply=38) | [board](http://localhost:5173/analysis?fen=4kr1r/p1pq2p1/1pn4p/3pPp2/3P1P1Q/8/PP4PP/R1B2RK1%20w%20-%20-%200%2020) |
| 60 | missed | CAPTURING_DEFENDER | 2 | `27. Qxg7 Rxg7 28. Bxh6 Rgg8 29. Bxf8 Rxf8 30. e7 Rf7 31. Rf4 Rxe7 32. Kf2 Kd7` | [ply 52](http://localhost:5173/analysis?game_id=681397&ply=52) | [board](http://localhost:5173/analysis?fen=4krr1/p5q1/1pp1P2p/3p1p2/3Q1B2/1P6/P5PP/4RRK1%20w%20-%20-%200%2027) |
| 61 | missed | CLEARANCE | 2 | `12. g4 Ne7 13. Qg2 c5 14. dxc5 Bxc5 15. g5 Ne8 16. Rad1 Qd7 17. Kh1 Rd8` | [ply 22](http://localhost:5173/analysis?game_id=681399&ply=22) | [board](http://localhost:5173/analysis?fen=r2q1rk1/1pp2ppp/p1nb1n2/3p4/3P4/P1NBPQ2/1P1B1PPP/R4RK1%20w%20-%20-%200%2012) |
| 62 | missed | HANGING_PIECE | 0 | `21. dxe5 Qxd3 22. Bxf8 Rxf8 23. Red1 Qe4 24. Rc7 Rf7 25. Rc8+ Kg7 26. Re8 Rc7` | [ply 40](http://localhost:5173/analysis?game_id=681399&ply=40) | [board](http://localhost:5173/analysis?fen=r4rk1/1p1q3p/p5p1/2B1np2/3P4/P2BP3/1P3PP1/2R1R1K1%20w%20-%20-%200%2021) |
| 63 | missed | SKEWER | 2 | `16. Rab1 Qe2 17. Rxb7 Rfd8 18. Rd7 Qc2 19. g3 Nb4 20. Rxd8+ Rxd8 21. Qb7 Bf8` | [ply 30](http://localhost:5173/analysis?game_id=681400&ply=30) | [board](http://localhost:5173/analysis?fen=r4rk1/pp2bppp/2n5/3Q4/8/4BN2/Pq3PPP/R4RK1%20w%20-%20-%200%2016) |
| 64 | missed | SKEWER | 4 | `18. a4 a6 19. Rab1 Qc2 20. Rxb7 Rd1 21. g3 Rxf1+ 22. Kxf1 Qe4 23. Rd7 Ne5` | [ply 34](http://localhost:5173/analysis?game_id=681400&ply=34) | [board](http://localhost:5173/analysis?fen=3r1rk1/pp3ppp/2n5/6Q1/8/4B3/Pq3PPP/R4RK1%20w%20-%20-%200%2018) |
| 65 | missed | CLEARANCE | 10 | `6... Nxe5 7. dxe5 Bxc5 8. Qc2 Bb6 9. a4 a5 10. b3 c6 11. Bb2 Bc7 12. Be2` | [ply 11](http://localhost:5173/analysis?game_id=681402&ply=11) | [board](http://localhost:5173/analysis?fen=r1bqkbnr/ppp2ppp/2n5/2PpN3/3Pp3/4P3/PP3PPP/RNBQKB1R%20b%20-%20-%200%206) |
| 66 | missed | FORK | 2 | `15... Bh4+ 16. Kd2 Nf2 17. Qe1 Nxh1 18. Qxh1 f4 19. fxe4 fxe3+ 20. Kc2 Qg5 21. Kb3` | [ply 29](http://localhost:5173/analysis?game_id=681402&ply=29) | [board](http://localhost:5173/analysis?fen=r2q1rk1/p1pbb1p1/2p4p/2Pp1p1P/1P1Pp1n1/2N1PP2/P3B1P1/R1BQK2R%20b%20-%20-%200%2015) |
| 67 | allowed | CLEARANCE | 4 | `14. Bxe6 fxe6 15. d4 Qb4 16. Qc3 Nd5 17. Qxb4 Nxb4 18. Re2 Nd5 19. Nc3 Nxc3` | [ply 25](http://localhost:5173/analysis?game_id=681403&ply=25) | [board](http://localhost:5173/analysis?fen=r4rk1/p2nqpp1/2p1bn1p/1p6/2B5/3P2QN/PPP2PPP/RN2R1K1%20w%20-%20-%200%2014) |
| 68 | missed | CLEARANCE | 6 | `16... Qe7 17. Nxf6+ Nxf6 18. Nd2 Nd5 19. Re5 Rf6 20. Rae1 Raf8 21. Ne4 Rf5 22. a3` | [ply 31](http://localhost:5173/analysis?game_id=681403&ply=31) | [board](http://localhost:5173/analysis?fen=r4rk1/p2n2p1/2pqpn1p/1p5N/8/3P2Q1/PPP2PPP/RN2R1K1%20b%20-%20-%200%2016) |
| 69 | missed | DISCOVERED_CHECK | 4 | `10... e4 11. Ng5 Nxd3+ 12. Bxd3 exd3+ 13. Kf1 f6 14. Nh3 Qe4 15. f3 Bxh3+ 16. Rxh3` | [ply 19](http://localhost:5173/analysis?game_id=681406&ply=19) | [board](http://localhost:5173/analysis?fen=r1b2rk1/ppp1qppp/2n5/4p3/2P2n1P/P2P1NP1/1P3P2/RN1QKB1R%20b%20-%20-%200%2010) |
| 70 | allowed | FORK | 0 | `22. Rf4 Bxd2 23. Rxg4 Rxe1 24. Rxe1 Bxe1 25. Rxg7+ Kf8 26. Rxh7 Ke7 27. Rh5 Bb4` | [ply 41](http://localhost:5173/analysis?game_id=681407&ply=41) | [board](http://localhost:5173/analysis?fen=r3r1k1/p1p2ppp/8/8/1b4b1/8/1BPP1RKP/R3N3%20w%20-%20-%200%2022) |
| 71 | missed | CLEARANCE | 4 | `21... Re4 22. Bc3 Bd7 23. d3 Rg4+ 24. Kf1 Rg6 25. Nf3 Bh3+ 26. Ke1 Re8+ 27. Re2` | [ply 41](http://localhost:5173/analysis?game_id=681407&ply=41) | [board](http://localhost:5173/analysis?fen=r3r1k1/p1p2ppp/3b4/8/1P4b1/8/1BPP1RKP/R3N3%20b%20-%20-%200%2021) |
| 72 | missed | PIN | 4 | `36... g4 37. Bh6+ Kg8 38. Rg7+ Kh8 39. Rd7 Re2 40. Be3 Rb5 41. Kf4 Re1 42. d4` | [ply 71](http://localhost:5173/analysis?game_id=681407&ply=71) | [board](http://localhost:5173/analysis?fen=4rk2/3R4/5p2/6pp/7P/1r1PB1K1/3P4/8%20b%20-%20-%200%2036) |
| 73 | allowed | CLEARANCE | 6 | `9. Bxf6 Bxf6 10. Ne2 Ne6 11. g3 Be7 12. Bg2 Bd6` | [ply 15](http://localhost:5173/analysis?game_id=681408&ply=15) | [board](http://localhost:5173/analysis?fen=r1bq1rk1/ppppbpp1/5n1p/3Np3/2PnP2B/3P3P/PP3PP1/R2QKBNR%20w%20-%20-%201%209) |
| 74 | missed | FORK | 6 | `8... g5 9. b4 Nxd5 10. bxc5 Nb4 11. Bg3 Nbc2+ 12. Kd2 Nxa1 13. Nf3 Nac2 14. Bxe5` | [ply 15](http://localhost:5173/analysis?game_id=681408&ply=15) | [board](http://localhost:5173/analysis?fen=r1bq1rk1/pppp1pp1/5n1p/2bNp3/2PnP2B/3P3P/PP3PP1/R2QKBNR%20b%20-%20-%200%208) |
| 75 | allowed | PROMOTION | 10 | `44. h4 Kd6 45. h5 a5 46. a4 f3 47. h6 Ke6 48. h7 Kd6 49. h8=Q Ke6` | [ply 85](http://localhost:5173/analysis?game_id=681408&ply=85) | [board](http://localhost:5173/analysis?fen=8/p7/4k3/5R2/5pP1/1P5P/P4K2/8%20w%20-%20-%201%2044) |
| 76 | missed | FORK | 8 | `17. dxc5` | [ply 32](http://localhost:5173/analysis?game_id=681410&ply=32) | [board](http://localhost:5173/analysis?fen=r1b1k2r/pp3ppp/n3p3/2p1N3/3P4/2B3P1/PPP3QP/2K5%20w%20-%20-%200%2017) |
| 77 | allowed | CLEARANCE | 10 | `6. Nxe5 f6 7. Nd3 Nc6 8. Nd2 Bf5 9. a3` | [ply 9](http://localhost:5173/analysis?game_id=681411&ply=9) | [board](http://localhost:5173/analysis?fen=r1bnkbnr/ppp2ppp/8/4p3/8/4PN2/PPP2PPP/RNB1KB1R%20w%20-%20-%200%206) |
| 78 | allowed | CLEARANCE | 2 | `10... e6 11. Bxc4 Bc5 12. Nc3 Nge7 13. Rc1 Rd7 14. Ke1 Bxf2+ 15. Ke2 Rhd8 16. Bf4` | [ply 18](http://localhost:5173/analysis?game_id=681412&ply=18) | [board](http://localhost:5173/analysis?fen=2kr1bnr/pp2pppp/2n5/8/2p1P3/5P2/PP1B1P1P/RN1K1B1R%20b%20-%20-%201%2010) |
| 79 | allowed | PIN | 0 | `14... Nxb4 15. Rc1 Nbxd5 16. Bxd5+ Kb8 17. Ke2 Nxd5 18. exd5 Rxd5 19. Rhd1 Rxd1 20. Rxd1` | [ply 26](http://localhost:5173/analysis?game_id=681412&ply=26) | [board](http://localhost:5173/analysis?fen=2k4r/pp1r1ppp/2n2n2/3Np3/1BB1P3/5P2/PP3P1P/R2K3R%20b%20-%20-%200%2014) |
| 80 | missed | DISCOVERED_ATTACK | 1 | `22... Bh3 23. Rxh3 Qxf7 24. Kf2 Rg8 25. Qh2 d5 26. Ke2 Rg7 27. Rh4 dxe4 28. fxe4` | [ply 43](http://localhost:5173/analysis?game_id=681414&ply=43) | [board](http://localhost:5173/analysis?fen=r3r2k/ppqb1B1p/2pp2p1/8/4P3/3PPP2/PPP3QR/5RK1%20b%20-%20-%200%2022) |
| 81 | allowed | CAPTURING_DEFENDER | 2 | `11... Nxd4 12. Qd3 Bxe5 13. f4 Ndc6 14. fxe5 h6 15. Bh4` | [ply 20](http://localhost:5173/analysis?game_id=681415&ply=20) | [board](http://localhost:5173/analysis?fen=r2qk2r/ppb1nppp/2n1p3/2PpN1B1/3P4/8/PP2QPPP/RN3RK1%20b%20-%20-%201%2011) |
| 82 | missed | FORK | 0 | `25. Qxf6+ Kg8 26. h4 Nab4 27. hxg5 Qf7 28. Qe6 Qxe6 29. fxe6 hxg5 30. Bxg5 e4` | [ply 48](http://localhost:5173/analysis?game_id=681415&ply=48) | [board](http://localhost:5173/analysis?fen=r3qk1r/ppb5/2n2pQp/2PppPp1/8/4BN2/nP4PP/4RRK1%20w%20-%20-%200%2025) |
| 83 | allowed | PIN | 0 | `16... Bxh4` | [ply 30](http://localhost:5173/analysis?game_id=681416&ply=30) | [board](http://localhost:5173/analysis?fen=rn2k1r1/1pp1bp2/p2p4/3Pp3/2B1P2N/2N4b/PPP3P1/R1B2RK1%20b%20-%20-%200%2016) |
| 84 | missed | CLEARANCE | 2 | `16. Kh2 Bxg2 17. Rg1 h3 18. Bf1 Nd7 19. Bxg2 hxg2 20. Rxg2 Rf8 21. Bg5 Bxg5` | [ply 30](http://localhost:5173/analysis?game_id=681416&ply=30) | [board](http://localhost:5173/analysis?fen=rn2k1r1/1pp1bp2/p2p4/3Pp3/2B1P2p/2N2N1b/PPP3P1/R1B2RK1%20w%20-%20-%200%2016) |
| 85 | allowed | HANGING_PIECE | 0 | `27... fxg5 28. Nf2 g4 29. Nxg4 Rdg8 30. Rg3 Rxh3+ 31. Rxh3 Rxg4 32. Rh8+ Ka7 33. Kh1` | [ply 52](http://localhost:5173/analysis?game_id=681416&ply=52) | [board](http://localhost:5173/analysis?fen=1k1r3r/1pp5/p2p1p2/3Pp1R1/4Pn2/5R1B/PPP4K/3N4%20b%20-%20-%201%2027) |
| 86 | allowed | CLEARANCE | 10 | `16... Rxe1+ 17. Rxe1 Nxd6 18. Bd5 c6 19. Bb3 Kg7 20. Rd1 Qe7 21. g4 Rd8 22. h4` | [ply 30](http://localhost:5173/analysis?game_id=681419&ply=30) | [board](http://localhost:5173/analysis?fen=r2qr1k1/ppp2p1p/3P2p1/5n2/2B5/2P2Q2/P4PPP/3RR1K1%20b%20-%20-%201%2016) |
| 87 | missed | CLEARANCE | 4 | `19. c4 Rd8 20. g3 Qd1 21. Qg2 Qc1 22. f4 Qxc4 23. Qf2 Rc1 24. g4 Qd4` | [ply 36](http://localhost:5173/analysis?game_id=681419&ply=36) | [board](http://localhost:5173/analysis?fen=r5k1/ppp2p1p/3q2p1/8/8/2P2Q2/P4PPP/4rBK1%20w%20-%20-%200%2019) |
| 88 | missed | SACRIFICE | 8 | `21. Qa6 Rd8 22. f3 Rd3 23. Qa8+ Kg7 24. Kf2 Rxf1+ 25. Kg3 Qe1+ 26. Kh3 h5` | [ply 40](http://localhost:5173/analysis?game_id=681419&ply=40) | [board](http://localhost:5173/analysis?fen=5rk1/Q1p2p1p/6p1/8/8/2P5/P4PPP/3qrBK1%20w%20-%20-%200%2021) |
| 89 | allowed | MATE | 8 | `33... Rxc3+ 34. Kf2 Ra1 35. Ke2 Ra2+ 36. Kd1 Rxh3 37. g5 Rh1#` | [ply 64](http://localhost:5173/analysis?game_id=681419&ply=64) | [board](http://localhost:5173/analysis?fen=6k1/7p/6p1/8/2r3P1/2P2K1P/8/4r3%20b%20-%20-%200%2033) |
| 90 | allowed | HANGING_PIECE | 0 | `16... Kxh7 17. Qg4 Ng6 18. f5 Ne5 19. Qh3+ Kg8 20. f6 Ng6 21. fxg7 Qh4 22. Qf5` | [ply 30](http://localhost:5173/analysis?game_id=681420&ply=30) | [board](http://localhost:5173/analysis?fen=r2qr1k1/2p1nppB/p2p4/2bP4/1p3P2/1P6/PBP3PP/R2Q1R1K%20b%20-%20-%200%2016) |
| 91 | missed | CAPTURING_DEFENDER | 6 | `19... Rd8 20. Qf5 Qd6 21. Qc5 Qxc5 22. Bxc5 Rxc2 23. Bxa7 Rxb2 24. a4 Bf6 25. Be3` | [ply 37](http://localhost:5173/analysis?game_id=681421&ply=37) | [board](http://localhost:5173/analysis?fen=r5k1/p1p2ppp/6q1/3Q4/6Pb/3PB2P/PPP1rP2/R4RK1%20b%20-%20-%200%2019) |
| 92 | missed | FORK | 0 | `18. Bxe7+ Nxe7 19. Bc2 Rfd6 20. h3 Bd7 21. Re3 Ng8 22. Rae1 Nf6 23. Re7 Be8` | [ply 34](http://localhost:5173/analysis?game_id=681422&ply=34) | [board](http://localhost:5173/analysis?fen=3r1k2/p1p1n1pB/1pn2r2/2B3N1/2P3b1/P1P5/5PPP/R3R1K1%20w%20-%20-%200%2018) |
| 93 | allowed | TRAPPED_PIECE | 6 | `8... Nxc3 9. Qc1 Ba3 10. Qxb2 Bxb2 11. Rd1 Nxd1 12. Kxd1 Ba3 13. Nb1 Bb4 14. a3` | [ply 14](http://localhost:5173/analysis?game_id=681423&ply=14) | [board](http://localhost:5173/analysis?fen=r1b1kb1r/pppp1ppp/2n5/3nP3/5B2/2P2NP1/Pq1NPPBP/R2QK2R%20b%20-%20-%201%208) |
| 94 | missed | CLEARANCE | 6 | `10. Rb1 Qxa2 11. Ra1 Qb2 12. Nc4 Qb5 13. Qd3 Be7 14. Rfb1 Nxf4 15. gxf4 Qc5` | [ply 18](http://localhost:5173/analysis?game_id=681423&ply=18) | [board](http://localhost:5173/analysis?fen=r1b2rk1/pppp1ppp/2n5/2bnP3/5B2/2P2NP1/Pq1NPPBP/R2Q1RK1%20w%20-%20-%200%2010) |
| 95 | allowed | DISCOVERED_CHECK | 2 | `27... Bxe3 28. fxe3 Ne4+ 29. Kf3 Nxc3 30. Be6 Rxh2 31. e4 Re2 32. Bd5 Re1 33. Kf4` | [ply 52](http://localhost:5173/analysis?game_id=681423&ply=52) | [board](http://localhost:5173/analysis?fen=5k2/p6p/6p1/2bB4/8/2P1R3/Pr1n1PKP/8%20b%20-%20-%201%2027) |
| 96 | missed | CLEARANCE | 6 | `14... Re8 15. h3 Bd7 16. g4 Nc6 17. Rd1 Rad8 18. Be2 Be7 19. Nf5 Bxf5 20. gxf5` | [ply 27](http://localhost:5173/analysis?game_id=681425&ply=27) | [board](http://localhost:5173/analysis?fen=rn3rk1/ppp2ppp/3b4/8/3Rp1bN/2P5/PBP3PP/2K2B1R%20b%20-%20-%200%2014) |
| 97 | missed | FORK | 2 | `19... Bf4+ 20. Kb1 Be2 21. Rb4 Bxf1 22. a3 Bg5 23. g3 Bxh4 24. gxh4 e3 25. c4` | [ply 37](http://localhost:5173/analysis?game_id=681425&ply=37) | [board](http://localhost:5173/analysis?fen=3r1r1k/pBp1n1pp/3b4/5p2/2R1p1bN/2P5/PBP3PP/2K2R2%20b%20-%20-%200%2019) |
| 98 | allowed | FORK | 0 | `20... Qe5 21. Qe1 Nxe3 22. Rc1 f5 23. Nb6 f4 24. Nf1 Nxf1 25. Qxf1 Be6 26. Qf3` | [ply 38](http://localhost:5173/analysis?game_id=681427&ply=38) | [board](http://localhost:5173/analysis?fen=N1b2rk1/1p2pp2/p2p2pp/7q/4P1n1/PP2P1NP/2PQ2P1/R5K1%20b%20-%20-%200%2020) |
| 99 | allowed | FORK | 0 | `12. Qxd5+ Kh8 13. Qxe4 Rxf2 14. Kxf2 Qf8+ 15. Ke1 Re8 16. Qd5 Bxe3 17. Qxd7 Bxg1+` | [ply 21](http://localhost:5173/analysis?game_id=681428&ply=21) | [board](http://localhost:5173/analysis?fen=r2q1rk1/pppb2pp/2n5/1Bbp4/4n3/2P1P3/PP3BPP/RN1QK1NR%20w%20-%20-%200%2012) |
| 100 | missed | ATTRACTION | 4 | `11... Bg4 12. Nf3 Nxe4 13. Nbd2 Nxf2 14. Kxf2 Qh4+ 15. Ke2 Bxe3 16. Qe1 Qh6 17. Kd1` | [ply 21](http://localhost:5173/analysis?game_id=681428&ply=21) | [board](http://localhost:5173/analysis?fen=r2q1rk1/pppb2pp/2n2n2/1Bbp4/4P3/2P1P3/PP3BPP/RN1QK1NR%20b%20-%20-%200%2011) |
| 101 | allowed | CLEARANCE | 8 | `23. cxd5 Re5 24. Rg1 Rxh3+ 25. Kg2 Rg5+ 26. Kf1 Rf5 27. Rg3 Rxg3 28. fxg3 Rxf3+` | [ply 43](http://localhost:5173/analysis?game_id=681430&ply=43) | [board](http://localhost:5173/analysis?fen=4r1k1/pp1b1ppp/2p4r/3p4/PPPp4/1B1P1P1P/5P1K/3R1R2%20w%20-%20-%201%2023) |
| 102 | missed | DISCOVERED_ATTACK | 3 | `d4c3 d3d4 e6h6 a4a5 d7h3 f1e1 h3d7 h2g3 h6h3 g3f4 g7g5 f4g5` | [ply 43](http://localhost:5173/analysis?game_id=681430&ply=43) | [board](http://localhost:5173/analysis?fen=4r1k1/pp1b1ppp/2p1r3/3p4/PPPp4/1B1P1P1P/5P1K/3R1R2%20b%20-%20-%200%2022) |
| 103 | missed | DEFLECTION | 10 | `23... Re5 24. Rfe1 Rg6+ 25. Kh2 Rh5 26. Re8+ Bxe8 27. Rg1 Rxh3+ 28. Kxh3 Rxg1 29. cxd5` | [ply 45](http://localhost:5173/analysis?game_id=681430&ply=45) | [board](http://localhost:5173/analysis?fen=4r1k1/pp1b1ppp/2p4r/3p4/PPPp4/1B1P1P1P/5P2/3R1RK1%20b%20-%20-%200%2023) |
| 104 | allowed | PROMOTION | 2 | `46. bxa7 Kf4 47. a8=Q Ke3 48. Qf3+ Kd2 49. Qxf5 Kd1 50. a6 Kc2 51. Qe4 Kb1` | [ply 89](http://localhost:5173/analysis?game_id=681430&ply=89) | [board](http://localhost:5173/analysis?fen=8/p7/1P6/P4p2/3p2k1/3P2p1/6K1/8%20w%20-%20-%201%2046) |
| 105 | missed | CLEARANCE | 4 | `6... h6 7. d4 g5 8. h4 Bg7 9. Qd3 Bb7 10. e5 Qe7 11. hxg5 hxg5 12. Rxh8` | [ply 11](http://localhost:5173/analysis?game_id=681431&ply=11) | [board](http://localhost:5173/analysis?fen=r1bqkbnr/2pp1ppp/p1n5/1p6/4Pp2/1B3N2/PPPP2PP/RNBQK2R%20b%20-%20-%200%206) |
| 106 | allowed | FORK | 0 | `19. Rxd7 Qf6 20. Qxf6 Nxf6 21. Rxe8+ Rxe8 22. Rxb7 Rd8 23. Rc7 h5 24. b4 cxb3` | [ply 35](http://localhost:5173/analysis?game_id=681431&ply=35) | [board](http://localhost:5173/analysis?fen=2rqr1k1/1b1p1ppp/p7/8/B1p1nQ2/P1N5/1PP3PP/2KRR3%20w%20-%20-%200%2019) |
| 107 | allowed | CLEARANCE | 6 | `7... Qe7 8. Bg5 Bc5 9. Qd3 Bxf2+ 10. Kd1 Qc5 11. Bxf6 gxf6 12. Rf1 c6 13. e5` | [ply 12](http://localhost:5173/analysis?game_id=681432&ply=12) | [board](http://localhost:5173/analysis?fen=r1bqk2r/pppp1ppp/3b1n2/8/2BQP3/2N5/PPP2PPP/R1B1K2R%20b%20-%20-%201%207) |
| 108 | missed | CLEARANCE | 2 | `15. Ng5 Nc6 16. Bf3 Qc4 17. Rc1` | [ply 28](http://localhost:5173/analysis?game_id=681433&ply=28) | [board](http://localhost:5173/analysis?fen=r1b1k2r/ppR2ppp/4p3/n2qP3/3P4/5N2/p2QBPPP/5RK1%20w%20-%20-%200%2015) |
| 109 | allowed | CLEARANCE | 6 | `4... Qxd4 5. Nd2 Qf6 6. a3 e5 7. b4 Bd6 8. Ngf3 Nge7` | [ply 6](http://localhost:5173/analysis?game_id=681434&ply=6) | [board](http://localhost:5173/analysis?fen=r1bqkbnr/ppp1pppp/2n5/8/2BPP3/8/PP3PPP/RNBQK1NR%20b%20-%20-%200%204) |
| 110 | allowed | SACRIFICE | 10 | `10... Nxc3 11. Bxc3 Be7 12. Bxg7 Rg8 13. Bc3 a6 14. Ba4 Qc7 15. Qxe6 Rg6 16. Qd5` | [ply 18](http://localhost:5173/analysis?game_id=681436&ply=18) | [board](http://localhost:5173/analysis?fen=r1b1kb1r/pp1n2pp/1q1pp3/1Bp5/4n3/1PN2N2/P1PBQPPP/R3K2R%20b%20-%20-%201%2010) |
| 111 | allowed | PIN | 2 | `14... axb5 15. Qe6+ Be7 16. b4 Qd8 17. Ng5 Rf8` | [ply 26](http://localhost:5173/analysis?game_id=681436&ply=26) | [board](http://localhost:5173/analysis?fen=r1b1kb1r/1p1n2pp/p2p4/qB2p3/2Q5/PPN1BN2/2P2PPP/R3K2R%20b%20-%20-%200%2014) |
| 112 | missed | PIN | 8 | `18. Qb3 Qc6` | [ply 34](http://localhost:5173/analysis?game_id=681436&ply=34) | [board](http://localhost:5173/analysis?fen=r1b1k2r/1p2b1pp/q2pQn2/1p2p1B1/1P6/P1N2N2/2P2PPP/R3K2R%20w%20-%20-%200%2018) |
| 113 | missed | CLEARANCE | 8 | `11... Bd6 12. Qg5 h6 13. Qh4 Bf5 14. Bb3 Nd7 15. Qh5 Qf6 16. Ne4 Bxe4 17. Rxe4` | [ply 21](http://localhost:5173/analysis?game_id=681439&ply=21) | [board](http://localhost:5173/analysis?fen=r1bq1rk1/pp2bppp/2p2n2/4Q3/2B5/2N5/PPP2PPP/R1B1R1K1%20b%20-%20-%200%2011) |
| 114 | allowed | MATE | 10 | `48. Rh5+ Kg6 49. Rxh8 Kf7 50. a7 g5 51. f5 Ke7 52. a8=Q Kd7 53. Rh7#` | [ply 93](http://localhost:5173/analysis?game_id=681439&ply=93) | [board](http://localhost:5173/analysis?fen=7r/6p1/P6k/6R1/4NPP1/6K1/8/8%20w%20-%20-%201%2048) |
| 115 | missed | DISCOVERED_CHECK | 0 | `49... Kg7+ 50. Kg3 Rb8 51. Rxg6+ Kf8 52. Rc6 Ra8 53. Kf4 Ke7 54. f6+ Kd7 55. Rb6` | [ply 97](http://localhost:5173/analysis?game_id=681439&ply=97) | [board](http://localhost:5173/analysis?fen=7r/8/P5pk/5PR1/4N1PK/8/8/8%20b%20-%20-%200%2049) |
| 116 | allowed | FORK | 4 | `16. b5 Rc8 17. Nc4 cxb5 18. Nb6+ Ke6 19. Rxb5 Rc5 20. Bb2 Qd3 21. Rb3 Qa6` | [ply 29](http://localhost:5173/analysis?game_id=681440&ply=29) | [board](http://localhost:5173/analysis?fen=3r1b1r/1p1k1ppp/2pp1n2/8/QP6/2q5/P2N1PPP/1RB2RK1%20w%20-%20-%201%2016) |
| 117 | missed | CLEARANCE | 2 | `21... d5 22. Nf3 Bd6 23. Bb2 Qc4 24. Ne5+ Bxe5 25. Qxc4 Bxh2+ 26. Kxh2 dxc4 27. Be5` | [ply 41](http://localhost:5173/analysis?game_id=681440&ply=41) | [board](http://localhost:5173/analysis?fen=3r1b1r/1Rnk3p/2pp2p1/5p2/Q7/2q5/P2N1PPP/2B1R1K1%20b%20-%20-%200%2021) |
| 118 | missed | SACRIFICE | 6 | `7... Qg5 8. d4 Qxg2 9. Rf1 Bd6 10. Nxc6 a6 11. Ba4` | [ply 13](http://localhost:5173/analysis?game_id=681443&ply=13) | [board](http://localhost:5173/analysis?fen=r1bqkb1r/ppp2ppp/2n5/1B2N3/4p3/8/PPPP1PPP/R1BQK2R%20b%20-%20-%200%207) |
| 119 | missed | TRAPPED_PIECE | 8 | `e8c8 e1g1 f8d6 d2d4 e4d3 e2d3 a7a6 b5c4 f6h8 d3d5 c6e5 c4e2` | [ply 19](http://localhost:5173/analysis?game_id=681443&ply=19) | [board](http://localhost:5173/analysis?fen=r3kb1N/pppb3p/2n2qp1/1B6/4p3/8/PPPPQPPP/R1B1K2R%20b%20-%20-%200%2010) |
| 120 | missed | PIN | 0 | `15... Nb4` | [ply 29](http://localhost:5173/analysis?game_id=681443&ply=29) | [board](http://localhost:5173/analysis?fen=2kr4/ppp1b2p/2n3p1/1B1Pqb2/Q7/4B3/PPP2PPP/R3K2R%20b%20-%20-%200%2015) |
| 121 | allowed | INTERMEZZO | 8 | `20... Bxa1 21. Be3 b5 22. h3 Rc8 23. cxb5 Qe5 24. Nf4 axb5 25. a4 Rc3 26. Nf3` | [ply 38](http://localhost:5173/analysis?game_id=681444&ply=38) | [board](http://localhost:5173/analysis?fen=r3qrk1/1p6/p2p2p1/3N1bNp/2PB3Q/8/Pb3PPP/R5K1%20b%20-%20-%201%2020) |
| 122 | missed | CLEARANCE | 6 | `20. Rd1 Qe5 21. h3 Rae8 22. c5 dxc5 23. Qc4 Be6 24. Qxc5 Bxd5 25. Rxd5 Qc3` | [ply 38](http://localhost:5173/analysis?game_id=681444&ply=38) | [board](http://localhost:5173/analysis?fen=r3qrk1/1p6/p2p2p1/3N1bNp/2P4Q/4B3/Pb3PPP/R5K1%20w%20-%20-%200%2020) |
| 123 | missed | CLEARANCE | 6 | `21. Be3 Rc8 22. h3 b5 23. cxb5 axb5 24. Qb4 Rc4 25. Qb3 Kh8 26. Bd2 Be5` | [ply 40](http://localhost:5173/analysis?game_id=681444&ply=40) | [board](http://localhost:5173/analysis?fen=r3qrk1/1p6/p2p2p1/3N1bNp/2PB3Q/8/P4PPP/b5K1%20w%20-%20-%200%2021) |
| 124 | allowed | CLEARANCE | 6 | `9... d4 10. Nb1 Nxe4 11. Nd2 Ndf6 12. Bd3 Bf5 13. Ngf3` | [ply 16](http://localhost:5173/analysis?game_id=681445&ply=16) | [board](http://localhost:5173/analysis?fen=r1b1k2r/pp1n1p1p/2p2n2/2bp4/4P3/2N4P/PP3PP1/R1B1KBNR%20b%20-%20-%200%209) |
| 125 | allowed | CLEARANCE | 6 | `7... Nxd5 8. Bd2 Bb4 9. Qc2 b6` | [ply 12](http://localhost:5173/analysis?game_id=681446&ply=12) | [board](http://localhost:5173/analysis?fen=r1bqkb1r/ppp2ppp/4pn2/n2PP3/2p5/2N2N2/PP3PPP/R1BQKB1R%20b%20-%20-%200%207) |
| 126 | allowed | CLEARANCE | 10 | `18... Kd7 19. Bb5+ Nxb5 20. Rxe4 Nd6 21. Ra4 Re8 22. Nf3 Ne4 23. Rxa7 Bc5 24. Bf4` | [ply 34](http://localhost:5173/analysis?game_id=681446&ply=34) | [board](http://localhost:5173/analysis?fen=r3kbr1/p1p4p/1p3p2/3P4/3nb2N/8/P2BBPPP/R3R1K1%20b%20-%20-%201%2018) |
| 127 | missed | DEFLECTION | 6 | `18. Nxd4 Rxg2+ 19. Kf1 Kf7 20. Bh5+ Bg6 21. Kxg2 Bxh5 22. Rac1 Rc8 23. Kg3 Bc5` | [ply 34](http://localhost:5173/analysis?game_id=681446&ply=34) | [board](http://localhost:5173/analysis?fen=r3kbr1/p1p4p/1p3p2/3P4/3nb3/5N2/P2BBPPP/R3R1K1%20w%20-%20-%200%2018) |
| 128 | missed | DISCOVERED_CHECK | 6 | `29. d6+ cxd6 30. Bf4 Ra8 31. Bxd6+ Ke8 32. Bxa2+ Kd7 33. Be6+ Kc6 34. Rc1+ Kb6` | [ply 56](http://localhost:5173/analysis?game_id=681446&ply=56) | [board](http://localhost:5173/analysis?fen=4rb2/p1p1kN1p/4Bp1B/1p1P4/8/7P/r4PP1/4R1K1%20w%20-%20-%200%2029) |
| 129 | allowed | SACRIFICE | 10 | `33... Rxg3 34. Kxg3 b3 35. Bf5 Re1 36. Ng4 b2 37. Nxf6 a5 38. Nxh7+ Kg7 39. Ng5` | [ply 64](http://localhost:5173/analysis?game_id=681446&ply=64) | [board](http://localhost:5173/analysis?fen=4rk2/p1p4p/4Bp1N/3P4/1p6/r5RP/5PPK/8%20b%20-%20-%201%2033) |
| 130 | missed | CLEARANCE | 6 | `9... Qf5` | [ply 17](http://localhost:5173/analysis?game_id=681447&ply=17) | [board](http://localhost:5173/analysis?fen=r1b1k2r/ppp2ppp/2n1qn2/2b3N1/2P1p3/3P3P/PP2BPP1/RNBQK2R%20b%20-%20-%200%209) |
| 131 | missed | CLEARANCE | 6 | `13... Qh4 14. Nd5` | [ply 25](http://localhost:5173/analysis?game_id=681447&ply=25) | [board](http://localhost:5173/analysis?fen=r1b1k2r/ppp2pp1/2n4p/2b5/2P1q3/2N4P/PP2BPP1/R1BQ1RK1%20b%20-%20-%200%2013) |
| 132 | allowed | CLEARANCE | 8 | `16. Bxf5 Qxf5 17. Re1+ Kf8 18. Qb3 b6 19. Be3 Rd8 20. Rad1 Kg8 21. Qa4 Ne5` | [ply 29](http://localhost:5173/analysis?game_id=681447&ply=29) | [board](http://localhost:5173/analysis?fen=r3k2r/ppp2pp1/2nb2qp/3N1b2/2P5/3B3P/PP3PP1/R1BQ1RK1%20w%20-%20-%201%2016) |
| 133 | allowed | PIN | 4 | `18. Re1 Qe6 19. Bf4 Nxd5 20. Bxd6` | [ply 33](http://localhost:5173/analysis?game_id=681447&ply=33) | [board](http://localhost:5173/analysis?fen=r3k2r/ppp1npp1/3b3p/3N1q2/2P5/7P/PP2QPP1/R1B2RK1%20w%20-%20-%201%2018) |
| 134 | allowed | PROMOTION | 10 | `37. Qb5 Rd7 38. cxd7 Kc7 39. Qf5 Kd8 40. Qe6 Kc7 41. Qe7 Kc6 42. d8=Q Kb5` | [ply 71](http://localhost:5173/analysis?game_id=681447&ply=71) | [board](http://localhost:5173/analysis?fen=1k1r4/pp6/2Pp4/5Q2/8/1P5P/P4PPK/8%20w%20-%20-%200%2037) |
| 135 | allowed | HANGING_PIECE | 0 | `11... dxe4 12. Qxd8+ Kxd8` | [ply 20](http://localhost:5173/analysis?game_id=681449&ply=20) | [board](http://localhost:5173/analysis?fen=r1bqk2r/pp3ppp/4p3/3pP3/4N3/4P3/PP1Q1PPP/R3KB1R%20b%20-%20-%200%2011) |
| 136 | allowed | CLEARANCE | 2 | `15... Bb7` | [ply 28](http://localhost:5173/analysis?game_id=681449&ply=28) | [board](http://localhost:5173/analysis?fen=r1b4r/p3kppp/1p2p3/4P3/4p3/4P1P1/PP3PBP/3RK2R%20b%20-%20-%201%2015) |
| 137 | missed | CLEARANCE | 2 | `17. Rxd8 Rxd8 18. Rc1 f5 19. Bf1 Rd2 20. Rc7+ Rd7 21. Rxd7+ Kxd7 22. a3 Bd5` | [ply 32](http://localhost:5173/analysis?game_id=681449&ply=32) | [board](http://localhost:5173/analysis?fen=3r3r/pb2kppp/1p2p3/4P3/4p3/4P1P1/PP3PBP/3R1RK1%20w%20-%20-%200%2017) |
| 138 | allowed | CLEARANCE | 4 | `9. Nxg6 hxg6 10. d3 Nd7 11. Be3 Qb4 12. Rb1` | [ply 15](http://localhost:5173/analysis?game_id=681450&ply=15) | [board](http://localhost:5173/analysis?fen=r3kb1r/ppp2ppp/2p2nb1/4N3/3qP1P1/2N4P/PPPP1P2/R1BQK2R%20w%20-%20-%201%209) |
| 139 | missed | DISCOVERED_ATTACK | 3 | `14... Nxf3+ 15. Bxf3 Nxe4 16. dxe4 Bxg5 17. Qxd8 Bxd8 18. c5 c6 19. Nd6 b5 20. h3` | [ply 27](http://localhost:5173/analysis?game_id=681451&ply=27) | [board](http://localhost:5173/analysis?fen=r2q1rk1/1pp1bppp/4bn2/pN2p1B1/2PnP3/3P1N2/P2QBPPP/R4RK1%20b%20-%20-%200%2014) |
| 140 | allowed | PROMOTION | 4 | `28. Rxe1 Nxe1 29. d7 h6 30. d8=Q+ Kh7 31. Qxa5 Nc2 32. Qd2 Na1 33. Qxd4 Nb3` | [ply 53](http://localhost:5173/analysis?game_id=681451&ply=53) | [board](http://localhost:5173/analysis?fen=6k1/1p3ppp/2pP4/p1Pb4/P2p3N/3n1P2/6PP/R3r1K1%20w%20-%20-%201%2028) |
| 141 | allowed | MATE | 10 | `30. d8=Q+ Kg7 31. Qxg5+ Kf8 32. Nf5 Nxf3+ 33. gxf3 f6 34. Qg7+ Ke8 35. Qe7#` | [ply 57](http://localhost:5173/analysis?game_id=681451&ply=57) | [board](http://localhost:5173/analysis?fen=6k1/1p1P1p1p/2p5/p1Pb2p1/P2p3N/5P2/6PP/4n1K1%20w%20-%20-%200%2030) |
| 142 | allowed | PIN | 4 | `41. Qb1+ d3 42. Kg3 Ne2+ 43. Kxh3 Bc4 44. Kg2 f5 45. gxf5+ Kxf5 46. Kf2 Ke6` | [ply 79](http://localhost:5173/analysis?game_id=681451&ply=79) | [board](http://localhost:5173/analysis?fen=8/1Q5p/2p2pk1/p1Pb4/P2p1nP1/5P1p/5K2/8%20w%20-%20-%200%2041) |
| 143 | allowed | SACRIFICE | 6 | `e1g1 e7d6 a2a4 f8e7 c1a3 d6e5 f1e1 e5f5 a3e7 d7d5 e7f6 c8e6` | [ply 13](http://localhost:5173/analysis?game_id=681470&ply=13) | [board](http://localhost:5173/analysis?fen=r1b1kb1r/p1ppqppp/2p5/4N3/8/2P5/P1PP1PPP/R1BQK2R%20w%20-%20-%201%208) |
| 144 | missed | CLEARANCE | 10 | `8... f6` | [ply 15](http://localhost:5173/analysis?game_id=681470&ply=15) | [board](http://localhost:5173/analysis?fen=r1b1kb1r/p1ppqppp/2p5/4N3/3P4/2P5/P1P2PPP/R1BQK2R%20b%20-%20-%200%208) |
| 145 | allowed | PIN | 0 | `12. Re1 Be6 13. d5 Bg7 14. Bb2 Bxb2 15. Nxb2` | [ply 21](http://localhost:5173/analysis?game_id=681470&ply=21) | [board](http://localhost:5173/analysis?fen=r1b1kb1r/p1p1qp1p/3p2p1/8/3P4/3N4/P1P2PPP/R1BQ1RK1%20w%20-%20-%200%2012) |
| 146 | missed | SACRIFICE | 2 | `17... Qxb2 18. Nxb2 d5 19. Qc3+ Kg8 20. Qxc7 Ba3 21. Nd3 h5 22. Kf1 Rh7 23. Qc6` | [ply 33](http://localhost:5173/analysis?game_id=681470&ply=33) | [board](http://localhost:5173/analysis?fen=r4b1r/p1p3kp/3p2p1/8/8/3N1Q2/PBP2PPP/q3R1K1%20b%20-%20-%200%2017) |
| 147 | missed | HANGING_PIECE | 0 | `62. Kxf5 Kf3 63. Ke5 Nd1 64. Kd4 Nf2 65. Ke5` | [ply 122](http://localhost:5173/analysis?game_id=681504&ply=122) | [board](http://localhost:5173/analysis?fen=8/8/8/5qK1/8/2n1k3/8/8%20w%20-%20-%200%2062) |
| 148 | allowed | CLEARANCE | 2 | `15... Be6` | [ply 28](http://localhost:5173/analysis?game_id=681508&ply=28) | [board](http://localhost:5173/analysis?fen=r1b1r1k1/pp2bppp/1q3p2/8/8/P1N2Q2/1P1RBPPP/4K2R%20b%20-%20-%201%2015) |
| 149 | missed | CLEARANCE | 8 | `13. Qxb5 Rfd8 14. Bc4 Rab8 15. Qa5 Qf4+ 16. Bd2 Qe4 17. Qc3 Nb6 18. Rhe1 cxd4` | [ply 24](http://localhost:5173/analysis?game_id=681525&ply=24) | [board](http://localhost:5173/analysis?fen=r4rk1/p1qnbppp/5p2/1pp2b2/3P4/2B2N2/PPP1QPPP/2KR1B1R%20w%20-%20-%200%2013) |
| 150 | missed | ATTRACTION | 8 | `36. Kd1 Rc1+ 37. Ke2 Rc2+ 38. Ke1 Rc1+ 39. Rd1 f5 40. Rxf8+ Kxf8 41. d8=Q+ Kf7` | [ply 70](http://localhost:5173/analysis?game_id=681564&ply=70) | [board](http://localhost:5173/analysis?fen=3R1nk1/1p1P1pp1/p2R3p/8/8/1n6/P1r1KPPP/8%20w%20-%20-%200%2036) |
| 151 | missed | FORK | 4 | `10. Nb5 Nxf4 11. Qxf4 Be6 12. Nc7+ Kd7 13. Bb5+ Kc8 14. Nxa8 Ng6 15. Qa4 Bc5` | [ply 18](http://localhost:5173/analysis?game_id=681568&ply=18) | [board](http://localhost:5173/analysis?fen=r1bqkb1r/pp2nppp/6n1/3p4/2BN1B2/8/PPPQ1PPP/RN2K2R%20w%20-%20-%200%2010) |
| 152 | allowed | CLEARANCE | 6 | `16... Bc5 17. Kh1 d4 18. Nd2 Kc7 19. Ne4 Rad8 20. Rad1 Kb8 21. Ng5 Rdf8 22. Nxe6` | [ply 30](http://localhost:5173/analysis?game_id=681568&ply=30) | [board](http://localhost:5173/analysis?fen=r2k1b1r/pp4pp/1q2p1n1/3p4/Q1P5/1B6/PP3PPP/RN2R1K1%20b%20-%20-%200%2016) |
| 153 | missed | INTERFERENCE | 2 | `16. Qg4 Bd6 17. Rxe6 Rf8 18. Re2 Nf4 19. Rd2 Rc8 20. Nc3 h5 21. Qxg7 Rc7` | [ply 30](http://localhost:5173/analysis?game_id=681568&ply=30) | [board](http://localhost:5173/analysis?fen=r2k1b1r/pp4pp/1q2p1n1/3p4/Q7/1B6/PPP2PPP/RN2R1K1%20w%20-%20-%200%2016) |
| 154 | allowed | MATE | 0 | `8. Qf7#` | [ply 13](http://localhost:5173/analysis?game_id=681579&ply=13) | [board](http://localhost:5173/analysis?fen=r1bqkb1r/ppp3pp/2n5/3Bp1p1/8/5Q2/PPPP1PPP/RNB1K2R%20w%20-%20-%200%208) |
| 155 | missed | ATTRACTION | 0 | `22... Rxg2+ 23. Kxg2 Qg4+ 24. Kf1 Qh3+ 25. Kg1 Qg4+` | [ply 43](http://localhost:5173/analysis?game_id=681579&ply=43) | [board](http://localhost:5173/analysis?fen=5rk1/p5pp/8/2Q1pq2/6r1/1P6/P1PPRPP1/RN4K1%20b%20-%20-%200%2022) |
| 156 | allowed | FORK | 0 | `30. Ne4 Qf1+ 31. Rxf1 Rxf1+ 32. Qg1 Rxg1+ 33. Kxg1 Kf7 34. Kf2 Ke6 35. Ke3 Ke5` | [ply 57](http://localhost:5173/analysis?game_id=681579&ply=57) | [board](http://localhost:5173/analysis?fen=6k1/p5pp/5r2/8/1P6/2N5/P4qPQ/3R3K%20w%20-%20-%201%2030) |
| 157 | allowed | PROMOTION | 10 | `43. a5 Kf6 44. b6 axb6 45. axb6 Ke5 46. Na6 Ke6 47. b7 Kd6 48. b8=Q+ Kc6` | [ply 83](http://localhost:5173/analysis?game_id=681579&ply=83) | [board](http://localhost:5173/analysis?fen=8/p7/8/1PN3k1/P5p1/6K1/8/8%20w%20-%20-%201%2043) |
| 158 | missed | FORK | 4 | `22. Ba7 Ra8 23. Bc5 Re8 24. Nc7 Re5 25. Nxa8 Rxc5 26. Nc7 Rc6` | [ply 42](http://localhost:5173/analysis?game_id=681585&ply=42) | [board](http://localhost:5173/analysis?fen=1r1r2k1/1b3ppp/p2P4/1p1N4/3BP3/PP1B4/5KPP/R7%20w%20-%20-%200%2022) |
| 159 | allowed | CLEARANCE | 6 | `26... Rxd4 27. Be4 R4d6 28. Rc6 Rxc6 29. Bxc6 Rd1 30. Bb7 Rb1 31. Kd4 Rxb3 32. Bxa6` | [ply 50](http://localhost:5173/analysis?game_id=681585&ply=50) | [board](http://localhost:5173/analysis?fen=3r2k1/5ppp/p7/1p1r4/3B4/PP1BK3/6PP/2R5%20b%20-%20-%201%2026) |
| 160 | missed | SACRIFICE | 4 | `26. Rd1 Re8+ 27. Kf3 Rxd4 28. Bxh7+ Kxh7 29. Rxd4 Rc8 30. Ke2 Rc2+ 31. Rd2 Rc6` | [ply 50](http://localhost:5173/analysis?game_id=681585&ply=50) | [board](http://localhost:5173/analysis?fen=3r2k1/5ppp/p7/1p1r4/3B4/PP1BK3/6PP/R7%20w%20-%20-%200%2026) |
| 161 | allowed | CLEARANCE | 8 | `7... Bxc3+ 8. Qxc3 bxc4` | [ply 12](http://localhost:5173/analysis?game_id=681586&ply=12) | [board](http://localhost:5173/analysis?fen=rnbqk1nr/p4ppp/2p1p3/1p6/1bBPP3/1QN2N2/PP3PPP/R1B1K2R%20b%20-%20-%201%207) |
| 162 | missed | CLEARANCE | 10 | `7. Bd3 Ne7` | [ply 12](http://localhost:5173/analysis?game_id=681586&ply=12) | [board](http://localhost:5173/analysis?fen=rnbqk1nr/p4ppp/2p1p3/1p6/1bBPP3/2N2N2/PP3PPP/R1BQK2R%20w%20-%20-%200%207) |
| 163 | allowed | CLEARANCE | 10 | `13... Nxd7 14. Qxc6 Qd8 15. Qd6 Qh4` | [ply 24](http://localhost:5173/analysis?game_id=681586&ply=24) | [board](http://localhost:5173/analysis?fen=rn2k2r/p2N1pp1/2p1pq1p/8/2QPP3/2P5/P4PPP/R3K2R%20b%20-%20-%200%2013) |
| 164 | missed | FORK | 4 | `13. Qb4 Bc8 14. Nc4 a5 15. Nd6+ Kf8 16. Qb6 Ba6 17. e5 Qe7 18. c4 Kg8` | [ply 24](http://localhost:5173/analysis?game_id=681586&ply=24) | [board](http://localhost:5173/analysis?fen=rn2k2r/p2b1pp1/2p1pq1p/4N3/2QPP3/2P5/P4PPP/R3K2R%20w%20-%20-%200%2013) |
| 165 | allowed | CLEARANCE | 10 | `17... Nc6 18. exd5 exd5 19. Qd3 Ke8 20. Qh7 Rab8 21. Rbe1+ Kd7 22. Qd3 Re8 23. Qxd5+` | [ply 32](http://localhost:5173/analysis?game_id=681586&ply=32) | [board](http://localhost:5173/analysis?fen=rnr5/3k1pp1/4pq1p/pQ1p4/4P3/2P5/P4PPP/1R3RK1%20b%20-%20-%201%2017) |
| 166 | missed | PIN | 8 | `17. Rb7+ Kd8 18. Qb5 Qxc3 19. Rxf7 Qb4 20. Qd3 Rc3 21. Qd1 Ra6 22. Qh5 Rc7` | [ply 32](http://localhost:5173/analysis?game_id=681586&ply=32) | [board](http://localhost:5173/analysis?fen=rnr5/3k1pp1/4pq1p/p2p4/2Q1P3/2P5/P4PPP/1R3RK1%20w%20-%20-%200%2017) |
| 167 | missed | PIN | 2 | `21. Qb5 Qc6 22. Qe5 Qxc3 23. Qd6 Qc5 24. Qf4 Qf8 25. h4 Rcc7 26. Rfe1 Kc8` | [ply 40](http://localhost:5173/analysis?game_id=681586&ply=40) | [board](http://localhost:5173/analysis?fen=2rk4/r2n1pp1/5q1p/p2Q4/8/2P5/P4PPP/3R1RK1%20w%20-%20-%200%2021) |
| 168 | allowed | INTERMEZZO | 2 | `10... d3 11. Ned4 Qxh6 12. Nf5 Qf4 13. Nxg7+ Kd8 14. Qxd3 Kc7 15. a4 bxa4 16. Rxa4` | [ply 18](http://localhost:5173/analysis?game_id=681589&ply=18) | [board](http://localhost:5173/analysis?fen=rnb1k2r/p2p2pp/2p2pqB/1pb5/3pP3/1B3N2/PPP1NPPP/R2Q1RK1%20b%20-%20-%200%2010) |
| 169 | allowed | CLEARANCE | 10 | `12... a4 13. Bc2 Bxd4 14. Qxd4` | [ply 22](http://localhost:5173/analysis?game_id=681589&ply=22) | [board](http://localhost:5173/analysis?fen=rnb1k2r/3p2pp/2p2p1q/ppb5/3NP3/1BP2N2/PP3PPP/R2Q1RK1%20b%20-%20-%200%2012) |
| 170 | allowed | FORK | 0 | `29... Qxf2+ 30. Kh1 Qxc2 31. Rf1 Rxf1+ 32. Nxf1 Qd3 33. Qf7 h5 34. Qf3 Qc4 35. Qf6+` | [ply 56](http://localhost:5173/analysis?game_id=681589&ply=56) | [board](http://localhost:5173/analysis?fen=5r1k/2b4p/4Q1p1/1p6/pP6/2P3N1/P1Bq1PPP/4R1K1%20b%20-%20-%201%2029) |
| 171 | missed | CLEARANCE | 10 | `29. Re2 Qxc3 30. Qxb5 Qa1+ 31. Nf1 Qf6 32. Be4 Bb6 33. Bf3 a3 34. Re8 Kg7` | [ply 56](http://localhost:5173/analysis?game_id=681589&ply=56) | [board](http://localhost:5173/analysis?fen=5r1k/2b4p/Q5p1/1p6/pP6/2P3N1/P1Bq1PPP/4R1K1%20w%20-%20-%200%2029) |
| 172 | missed | SKEWER | 6 | `44. Ke4 Rd6 45. Rxb5 Rd2 46. Rb6+ Ke7 47. Rxh6 Rxg2 48. Kd4 Rxg3 49. a3 Rg4+` | [ply 86](http://localhost:5173/analysis?game_id=681589&ply=86) | [board](http://localhost:5173/analysis?fen=8/8/1r2k2p/1pR3p1/pP6/2P2KP1/P5P1/8%20w%20-%20-%200%2044) |
| 173 | allowed | SACRIFICE | 10 | `46... Kd7 47. Kh5 Rd6 48. g4 Rd2 49. Kxh6 Rxg2 50. Kxg5 a3 51. Rxb5 Kc6 52. Rc5+` | [ply 90](http://localhost:5173/analysis?game_id=681589&ply=90) | [board](http://localhost:5173/analysis?fen=8/4k3/1r5p/1pR3p1/pP4K1/2P3P1/P5P1/8%20b%20-%20-%201%2046) |
| 174 | missed | DEFLECTION | 2 | `54. g4 Rxg4 55. Rxa2 Ke5 56. Rd2 h5 57. b5 Rg1 58. Ka2 g4 59. b6 Rf1` | [ply 106](http://localhost:5173/analysis?game_id=681589&ply=106) | [board](http://localhost:5173/analysis?fen=8/8/5k1p/R5p1/1P6/1KP3P1/p5r1/8%20w%20-%20-%200%2054) |
| 175 | allowed | DEFLECTION | 4 | `57... Rb8 58. Rb4 g4 59. Rxg4 Rxb6+ 60. Ka4 h5 61. Rg1 Kf5 62. Rh1 Kg5 63. Rc1` | [ply 112](http://localhost:5173/analysis?game_id=681589&ply=112) | [board](http://localhost:5173/analysis?fen=4r3/8/1P3k1p/6p1/R7/1KP5/8/8%20b%20-%20-%201%2057) |
| 176 | missed | DISCOVERED_CHECK | 10 | `60. Rb1 g3 61. c4 h4 62. c5 g2 63. c6 Rxb6 64. Rxb6 g1=Q 65. c7+ Qxb6` | [ply 118](http://localhost:5173/analysis?game_id=681589&ply=118) | [board](http://localhost:5173/analysis?fen=1r6/8/1P3k2/7p/KR4p1/2P5/8/8%20w%20-%20-%200%2060) |
| 177 | allowed | PROMOTION | 4 | `67... h2 68. Rb5+ Kf4 69. Rb2 h1=Q 70. Rf2+ Ke5 71. Rxg2 Qxg2 72. Kc7 Qg1 73. Kc6` | [ply 132](http://localhost:5173/analysis?game_id=681589&ply=132) | [board](http://localhost:5173/analysis?fen=1K6/8/8/6k1/2P5/7p/6p1/1R6%20b%20-%20-%200%2067) |
| 178 | allowed | PROMOTION | 0 | `71... hxg1=Q 72. c8=Q Qb6+ 73. Ka8 Qa5+ 74. Kb8` | [ply 140](http://localhost:5173/analysis?game_id=681589&ply=140) | [board](http://localhost:5173/analysis?fen=1K6/2P5/8/8/8/6k1/7p/6R1%20b%20-%20-%200%2071) |
| 179 | missed | DISCOVERED_ATTACK | 9 | `4. a4 c6 5. axb5 cxb5 6. Nc3 Bd7 7. d5 e5 8. dxe6 Bxe6 9. Qxd8+ Kxd8` | [ply 6](http://localhost:5173/analysis?game_id=681593&ply=6) | [board](http://localhost:5173/analysis?fen=rnbqkbnr/p1p1pppp/8/1p6/2pPP3/8/PP3PPP/RNBQKBNR%20w%20-%20-%200%204) |
| 180 | missed | FORK | 2 | `14. Bxb5+ axb5 15. Qxb5+ Nd7 16. Qxb7 Bd6 17. f3 f5 18. Qc6` | [ply 26](http://localhost:5173/analysis?game_id=681593&ply=26) | [board](http://localhost:5173/analysis?fen=r2qkb1r/1bp2p1p/p4np1/1p1Pp3/4P3/PQN1B3/1P2BPPP/1R2K2R%20w%20-%20-%200%2014) |
| 181 | missed | TRAPPED_PIECE | 8 | `27. f3 Bc5+ 28. Kh1 Rdf8 29. h3 a5 30. Nc1 Bd6 31. fxg4 hxg4 32. Nd3 f4` | [ply 52](http://localhost:5173/analysis?game_id=681593&ply=52) | [board](http://localhost:5173/analysis?fen=1k1r3r/2p5/p2b2p1/3Ppp1p/Pp2P1b1/1P4P1/4NPBP/4RRK1%20w%20-%20-%200%2027) |
| 182 | allowed | DISCOVERED_ATTACK | 3 | `8... Nc6 9. dxe5 dxe5 10. a3 Qxd3 11. Bxd3 Bxf3 12. gxf3 Nd4 13. Kg2 Nh5 14. Ne2` | [ply 14](http://localhost:5173/analysis?game_id=681613&ply=14) | [board](http://localhost:5173/analysis?fen=rn1q1rk1/ppp2pbp/3p1np1/4p3/2BPP1b1/2NQ1N2/PPP2PPP/R1B1R1K1%20b%20-%20-%201%208) |
| 183 | allowed | FORK | 6 | `11... Bxf3 12. gxf3 Nd4 13. Re3 c6 14. a4 Nc2 15. Rd1 h6 16. Re2 Nd4 17. Be3` | [ply 20](http://localhost:5173/analysis?game_id=681613&ply=20) | [board](http://localhost:5173/analysis?fen=r4rk1/ppp2pbp/2n2np1/4p1B1/2B1P1b1/2NP1N2/PP3PPP/R3R1K1%20b%20-%20-%200%2011) |
| 184 | missed | SACRIFICE | 4 | `14. f5 Nf3+ 15. Kg2 Nxe1+ 16. Rxe1 c6 17. a4 Rfb8 18. Be3 a6 19. a5 Bf8` | [ply 26](http://localhost:5173/analysis?game_id=681613&ply=26) | [board](http://localhost:5173/analysis?fen=r4rk1/pppn1pbp/6p1/4p1B1/2BnPP2/2NP4/PP3P1P/R3R1K1%20w%20-%20-%200%2014) |
| 185 | missed | FORK | 6 | `33. Ra4 Rg7 34. Rc6 Rd7 35. Nh5 Be7 36. Nxf6+ Bxf6 37. Rxf6 Rd2 38. Re6 Rxb2` | [ply 64](http://localhost:5173/analysis?game_id=681613&ply=64) | [board](http://localhost:5173/analysis?fen=r4bk1/2R4p/5p2/p3pPr1/1p6/6NK/RP3P1P/8%20w%20-%20-%200%2033) |
| 186 | missed | CLEARANCE | 6 | `34. Kg4 Rxh2 35. Kg3 Rh6 36. b3 Kh8 37. Rd2 Rh1 38. Rdd7 Bg7 39. Kf3 Rg8` | [ply 66](http://localhost:5173/analysis?game_id=681613&ply=66) | [board](http://localhost:5173/analysis?fen=r4bk1/2R4p/5p2/p3pP1r/1p2N3/7K/RP3P1P/8%20w%20-%20-%200%2034) |
| 187 | allowed | DISCOVERED_ATTACK | 1 | `9. d4 Bb7 10. Bxf4 exf4 11. Re1+ Be7 12. Qe2 Na5 13. Bc2 Nc4 14. Be4 c6` | [ply 15](http://localhost:5173/analysis?game_id=681616&ply=15) | [board](http://localhost:5173/analysis?fen=r1bqkb1r/2p2ppp/p1n5/1p2p3/5n2/1BP2N2/PP1P1PPP/RNBQ1RK1%20w%20-%20-%201%209) |
| 188 | allowed | DISCOVERED_CHECK | 8 | `10. d4 Be7 11. d5 Na5 12. Nxe5 Ng6 13. Nxf7 Kxf7 14. d6+ Nxb3 15. Qxb3+ Ke8` | [ply 17](http://localhost:5173/analysis?game_id=681616&ply=17) | [board](http://localhost:5173/analysis?fen=r1bqk2r/2p2ppp/p1nb4/1p2p3/5n2/1BP2N2/PP1P1PPP/RNBQR1K1%20w%20-%20-%201%2010) |
| 189 | allowed | FORK | 2 | `12. Bxc6 Bxc6 13. dxe5 Nh3+ 14. Kf1 Bxe5 15. Rxe5+ Kf8 16. Be3 Rd8 17. Qe2 g5` | [ply 21](http://localhost:5173/analysis?game_id=681616&ply=21) | [board](http://localhost:5173/analysis?fen=r3k2r/2pb1ppp/p1nb1q2/1p1Bp3/3P1n2/2P2N2/PP3PPP/RNBQR1K1%20w%20-%20-%201%2012) |
| 190 | missed | HANGING_PIECE | 0 | `11... Nxd5 12. dxe5 Bxe5 13. Qxd5 Qd6 14. Rxe5+ Nxe5 15. Qxe5+ Qxe5 16. Nxe5` | [ply 21](http://localhost:5173/analysis?game_id=681616&ply=21) | [board](http://localhost:5173/analysis?fen=r1b1k2r/2p2ppp/p1nb1q2/1p1Bp3/3P1n2/2P2N2/PP3PPP/RNBQR1K1%20b%20-%20-%200%2011) |
| 191 | allowed | MATE | 0 | `9. Qf7#` | [ply 15](http://localhost:5173/analysis?game_id=681621&ply=15) | [board](http://localhost:5173/analysis?fen=r1bqkb1r/ppp3pp/8/3Bp3/3n4/5Q2/PPPP1PPP/RNB1K2R%20w%20-%20-%201%209) |
| 192 | missed | CLEARANCE | 8 | `4. cxd5 c6 5. dxc6 bxc6 6. Nf3 e6 7. e4 Be7 8. Be2` | [ply 6](http://localhost:5173/analysis?game_id=681624&ply=6) | [board](http://localhost:5173/analysis?fen=r1bqkb1r/pppnpppp/5n2/3p4/2PP4/2N5/PP2PPPP/R1BQKBNR%20w%20-%20-%200%204) |
| 193 | missed | DISCOVERED_ATTACK | 1 | `23. Rxf6+ Kxf6 24. Qxd7 b6 25. cxb6 axb6 26. Ne5 g5 27. f3 c5 28. Ng4+ Kg6` | [ply 44](http://localhost:5173/analysis?game_id=681624&ply=44) | [board](http://localhost:5173/analysis?fen=5r2/pppq1kp1/4Rb1p/2P5/3P2Q1/5N2/PP3PPP/6K1%20w%20-%20-%200%2023) |
| 194 | missed | CLEARANCE | 6 | `8... dxc4 9. e3 b5 10. a4 c6 11. h4 Qb6 12. h5 h6 13. Qf3 bxa4 14. e4` | [ply 15](http://localhost:5173/analysis?game_id=681632&ply=15) | [board](http://localhost:5173/analysis?fen=rn1q1rk1/pppbbppp/4p3/3p4/2PP1B2/2N5/PP2PPPP/R2QKB1R%20b%20-%20-%200%208) |
| 195 | allowed | FORK | 8 | `21. Nd5 Qxd5 22. Rxd5 Bxd5 23. Bxg7 Kxg7 24. h4 h5 25. Qc5 Rd7 26. Re1 Rad8` | [ply 39](http://localhost:5173/analysis?game_id=681641&ply=39) | [board](http://localhost:5173/analysis?fen=r5k1/1pp1rpbp/p3b1pB/2q5/8/2N5/PP3PPP/R1QR2K1%20w%20-%20-%200%2021) |
| 196 | allowed | CLEARANCE | 2 | `10. d4 Bb6 11. Bg5 Qd7 12. Bh4 Rae8 13. Nd2 c6 14. Re1 Nf4 15. Bxe6 Rxe6` | [ply 17](http://localhost:5173/analysis?game_id=681643&ply=17) | [board](http://localhost:5173/analysis?fen=r2q1rk1/ppp2ppp/4b3/2bnR3/2B5/2P5/PP1P1PPP/RNBQ2K1%20w%20-%20-%201%2010) |
| 197 | missed | CLEARANCE | 6 | `11. Nb3 Qxe5+ 12. Qe2 Nc6 13. Qxe5 Nxe5 14. Be2 b6 15. f4 Ng4 16. Bf3 Rb8` | [ply 20](http://localhost:5173/analysis?game_id=681647&ply=20) | [board](http://localhost:5173/analysis?fen=rnb2rk1/ppp1b1pp/4p3/2N1Pp2/3q4/3B4/PPP2PPP/R1BQK2R%20w%20-%20-%200%2011) |
| 198 | missed | PIN | 2 | `8... Nxe4 9. Nxe4 Qh4 10. Nd2 Bxf2+ 11. Kd1 d5 12. Nf3 Qxe4 13. Qc2 Qxc2+ 14. Kxc2` | [ply 15](http://localhost:5173/analysis?game_id=681650&ply=15) | [board](http://localhost:5173/analysis?fen=r1bqr1k1/pppp1ppp/2n2n2/2b5/Q3P3/2P3NP/PP3PP1/RNB1KB1R%20b%20-%20-%200%208) |
| 199 | allowed | CLEARANCE | 8 | `30. Rb3 Ra2 31. Rb8+ Kg7 32. Rb7 Bb6 33. f3 a5 34. Bg3 Rxa4 35. Be5+ Kf8` | [ply 57](http://localhost:5173/analysis?game_id=681650&ply=57) | [board](http://localhost:5173/analysis?fen=6k1/p1p2p1p/6p1/b1p5/P7/R1P4P/2r2PP1/4BK2%20w%20-%20-%201%2030) |
| 200 | allowed | DISCOVERED_ATTACK | 1 | `8. dxe5 dxe5 9. Qxd8 Rxd8 10. Bxf6 gxf6 11. Nd2 Be6 12. Bd3 Rd6 13. Nb5 Rd7` | [ply 13](http://localhost:5173/analysis?game_id=681686&ply=13) | [board](http://localhost:5173/analysis?fen=r1bq1rk1/ppp2pp1/2np1n1p/4p3/1b1PP2B/2N2N2/PPP2PPP/R2QKB1R%20w%20-%20-%200%208) |
| 201 | missed | PIN | 4 | `7... exd4 8. Nxd4 Re8 9. Nxc6 Rxe4+ 10. Be2 bxc6 11. Bxf6 Qxf6` | [ply 13](http://localhost:5173/analysis?game_id=681686&ply=13) | [board](http://localhost:5173/analysis?fen=r1bq1rk1/pppp1pp1/2n2n1p/4p3/1b1PP2B/2N2N2/PPP2PPP/R2QKB1R%20b%20-%20-%200%207) |
| 202 | missed | CAPTURING_DEFENDER | 4 | `10... Qxd1 11. Raxd1 Bxc3 12. bxc3 Nxe4 13. Rfe1 Nd6 14. Bd5 e4 15. h3 Bxf3 16. gxf3` | [ply 19](http://localhost:5173/analysis?game_id=681686&ply=19) | [board](http://localhost:5173/analysis?fen=r2q1rk1/ppp2pp1/2n2n1p/4p3/1bB1P1bB/2N2N2/PPP2PPP/R2Q1RK1%20b%20-%20-%200%2010) |
| 203 | missed | CAPTURING_DEFENDER | 2 | `13... Qxd1 14. Raxd1 Bxf3 15. Rd3 Bxe4 16. Re3 Bxc2 17. f4 exf4 18. Rxf4 b5 19. Ba2` | [ply 25](http://localhost:5173/analysis?game_id=681686&ply=25) | [board](http://localhost:5173/analysis?fen=r2q1rk1/ppp2pp1/5n1p/4p3/2B1P1bB/P1P2P2/2P2P1P/R2Q1RK1%20b%20-%20-%200%2013) |
| 204 | allowed | CLEARANCE | 6 | `16. Qxd6 cxd6 17. Bxf6 gxf6 18. Kh1 Kh7 19. Rg1 Rac8 20. Rad1 Rc6 21. Rd3 Be6` | [ply 29](http://localhost:5173/analysis?game_id=681686&ply=29) | [board](http://localhost:5173/analysis?fen=r4rk1/ppp2pp1/3q1n1p/4p3/4P2B/PBP2P1b/2P2P1P/R2QR1K1%20w%20-%20-%201%2016) |
| 205 | missed | CLEARANCE | 4 | `15... g5 16. Bg3 Qe7 17. Bc4 Rad8 18. Qc1 Nh5 19. Bf1 Bxf1 20. Kxf1 Rd6 21. a4` | [ply 29](http://localhost:5173/analysis?game_id=681686&ply=29) | [board](http://localhost:5173/analysis?fen=r2q1rk1/ppp2pp1/5n1p/4p3/4P2B/PBP2P1b/2P2P1P/R2QR1K1%20b%20-%20-%200%2015) |
| 206 | missed | PIN | 4 | `18... Nf4 19. Qb1 h5 20. Qxb7 h4 21. Qc6 Nxd5 22. Qxg6 fxg6 23. exd5 hxg3 24. Re3` | [ply 35](http://localhost:5173/analysis?game_id=681686&ply=35) | [board](http://localhost:5173/analysis?fen=r4rk1/ppp2pp1/6qp/3Bp2n/4P3/P1P2PBb/2P2P1P/R1Q1R1K1%20b%20-%20-%200%2018) |
| 207 | allowed | FORK | 2 | `28. Rxd8 Rxd8 29. Qh4 Rd2 30. Bh5 Qg5 31. Qxg5 hxg5 32. axb6 axb6 33. Bg6 Rd8` | [ply 53](http://localhost:5173/analysis?game_id=681686&ply=53) | [board](http://localhost:5173/analysis?fen=3r1r1k/p5p1/1p4qp/P1p2p2/4PQ2/2P3Pb/2P1B2P/R2R2K1%20w%20-%20-%200%2028) |
| 208 | missed | TRAPPED_PIECE | 8 | `12... Qe7 13. e4` | [ply 23](http://localhost:5173/analysis?game_id=681700&ply=23) | [board](http://localhost:5173/analysis?fen=r2qk2r/1ppb1ppp/p7/2nQP3/5B2/5P2/PPP1PbPP/R2K1BNR%20b%20-%20-%200%2012) |
| 209 | allowed | CLEARANCE | 8 | `21... Nxf5 22. exf5 e4 23. Rb1 exf3 24. Bb2 Qxb2 25. Rxb2 Bf6 26. Rb3 fxe2 27. Re1` | [ply 40](http://localhost:5173/analysis?game_id=681709&ply=40) | [board](http://localhost:5173/analysis?fen=r2b3r/p3npk1/P2p1q1p/1QpPpNpb/1p2P3/5N1P/P1P1BPP1/R1B2RK1%20b%20-%20-%201%2021) |
| 210 | missed | CLEARANCE | 4 | `4. Nxd4 exd4` | [ply 6](http://localhost:5173/analysis?game_id=681714&ply=6) | [board](http://localhost:5173/analysis?fen=r1bqkbnr/pppp1ppp/8/4p3/2BnP3/5N2/PPPP1PPP/RNBQK2R%20w%20-%20-%200%204) |
| 211 | allowed | PIN | 4 | `13... Qg5 14. Bxd4 Bxd4 15. c3 Bxh3 16. Qf3 Bg4 17. Qg3 Bc5 18. d4 Bd6 19. f4` | [ply 24](http://localhost:5173/analysis?game_id=681714&ply=24) | [board](http://localhost:5173/analysis?fen=r1b2rk1/ppp2ppp/5q2/2bP4/2Bn4/1PBP3P/P1P2PP1/RN1Q1RK1%20b%20-%20-%201%2013) |
| 212 | missed | CLEARANCE | 10 | `16. Nd2 Re8 17. Nf3 Bxh3 18. gxh3 Qf5 19. Bxd4 Qxh3+ 20. Nh2 Bxd4 21. Qf3 Qh6` | [ply 30](http://localhost:5173/analysis?game_id=681714&ply=30) | [board](http://localhost:5173/analysis?fen=r1b2r1k/ppp2ppp/1b4q1/3P4/1PBn4/2BP3P/P1P2PP1/RN1Q1R1K%20w%20-%20-%200%2016) |
| 213 | allowed | HANGING_PIECE | 0 | `29... Bxe1 30. a6 Rxa6 31. Bxa6 bxa6 32. Qe2 Bc3 33. Qe5+ Kg8 34. Qg5+ Kh8 35. Qc5` | [ply 56](http://localhost:5173/analysis?game_id=681714&ply=56) | [board](http://localhost:5173/analysis?fen=r7/1ppb1rkp/8/P7/Pb1P1p2/3B1Q1P/2P2PP1/4R2K%20b%20-%20-%201%2029) |
| 214 | missed | FORK | 0 | `29. Qxb7 Re8 30. Qxb4 f3 31. g4 Kh8 32. Qc5 Rg7 33. Qh5 Reg8 34. Qe5 Bc6` | [ply 56](http://localhost:5173/analysis?game_id=681714&ply=56) | [board](http://localhost:5173/analysis?fen=r7/1ppb1rkp/8/P7/Pb1P1p2/3B1Q1P/2P2PP1/5R1K%20w%20-%20-%200%2029) |
| 215 | allowed | DISCOVERED_CHECK | 10 | `30... Rxa5 31. Kg1 Rxa4 32. Qe4 Ra1 33. Qxh7+ Kf8 34. Qh8+ Ke7 35. Bg6 Bb4+ 36. Kh2` | [ply 58](http://localhost:5173/analysis?game_id=681714&ply=58) | [board](http://localhost:5173/analysis?fen=r7/1Qpb1rkp/8/P7/P2P1p2/3B3P/2P2PP1/4b2K%20b%20-%20-%200%2030) |
| 216 | missed | SACRIFICE | 2 | `41. Qxe1 Rxe1 42. b7 Rb1 43. a6 Kg7 44. a7 Rxb7 45. a8=Q Rb1 46. Qe8 h5` | [ply 80](http://localhost:5173/analysis?game_id=681714&ply=80) | [board](http://localhost:5173/analysis?fen=6k1/7p/1P2r3/P7/3P1p2/2Q2P2/2P3PK/4r3%20w%20-%20-%200%2041) |
| 217 | allowed | CLEARANCE | 6 | `15. Rxf2 Qd6 16. c5 Qe7 17. Qe2 Rd8 18. Re1 h6 19. Nc4 Be6 20. Nxe5 Nxe5` | [ply 27](http://localhost:5173/analysis?game_id=681715&ply=27) | [board](http://localhost:5173/analysis?fen=r1b2rk1/ppp2ppp/2n2n2/4p3/1PPq4/P6P/1BPN1pP1/1R1Q1RK1%20w%20-%20-%200%2015) |
| 218 | missed | SACRIFICE | 8 | `34... Qh5+ 35. Kg1 Re1+ 36. Rf1 Rxf1+ 37. Kxf1 Rxc5 38. Qxc5 Bh3+ 39. Ke1 Qxc5 40. Rh4` | [ply 67](http://localhost:5173/analysis?game_id=681715&ply=67) | [board](http://localhost:5173/analysis?fen=2r1r1k1/Q4pp1/7p/1PB1q3/1R4b1/6P1/2P2R1K/8%20b%20-%20-%200%2034) |
| 219 | allowed | FORK | 0 | `18... Ne4+ 19. Rxe4 Qxe4 20. Bg3 Qxd5 21. Qf6 g4 22. Bxd6 gxf3 23. Be5 Kf8 24. Qh8+` | [ply 34](http://localhost:5173/analysis?game_id=681718&ply=34) | [board](http://localhost:5173/analysis?fen=r3q1k1/pp3p2/3p1n1p/2pP2p1/7B/P1Q2N2/1PP2KPP/4R3%20b%20-%20-%201%2018) |
| 220 | missed | CLEARANCE | 4 | `23. Qd4 Nd5 24. Qxb6 Nxb6 25. Bd4 Nd5 26. Rd1 b6 27. Bc3 Rd8 28. Rd4 b5` | [ply 44](http://localhost:5173/analysis?game_id=681718&ply=44) | [board](http://localhost:5173/analysis?fen=r5k1/pp3p2/1q3n1p/4B1p1/2p5/P2Q1N2/1PP2KPP/4R3%20w%20-%20-%200%2023) |
| 221 | missed | SACRIFICE | 8 | `37. Bxe1 Qxf6 38. h3 Kh7 39. Bb4 c3 40. Bxc3 Qxc3 41. Kf2 Qd2+ 42. Kf1 Kg6` | [ply 72](http://localhost:5173/analysis?game_id=681718&ply=72) | [board](http://localhost:5173/analysis?fen=6k1/p4p2/1p2qR1p/6p1/2p5/P1B5/6PP/4r1K1%20w%20-%20-%200%2037) |
| 222 | allowed | EN_PASSANT | 4 | `8. d5 Nd4 9. Be3 c5 10. dxc6 bxc6 11. Nf3 Bg4 12. Be2 Bxf3 13. Bxf3 Bc5` | [ply 13](http://localhost:5173/analysis?game_id=681719&ply=13) | [board](http://localhost:5173/analysis?fen=r1bqkb1r/ppp2ppp/2n2n2/4p3/3PP3/P1N5/1P3PPP/R1BQKBNR%20w%20-%20-%201%208) |
| 223 | allowed | PIN | 0 | `15. Rg2 Qh4 16. fxe5 Bd4 17. Rg5 g6` | [ply 27](http://localhost:5173/analysis?game_id=681719&ply=27) | [board](http://localhost:5173/analysis?fen=r1b2rk1/ppp2ppp/7B/2bPp2n/4PP2/P1N2Q2/1P3P1q/R3KBR1%20w%20-%20-%200%2015) |
| 224 | missed | CLEARANCE | 4 | `16... Qxh1 17. fxe5 Bg4 18. Be3 Rae8 19. Kd2 Rxe5 20. Re1 Qf3 21. Bxa7 Nf6 22. Bd3` | [ply 31](http://localhost:5173/analysis?game_id=681719&ply=31) | [board](http://localhost:5173/analysis?fen=r1b2rk1/ppp2ppp/7B/3Pp2n/4PP2/P1N5/1P3Q1q/R3KB1R%20b%20-%20-%200%2016) |
| 225 | missed | CLEARANCE | 8 | `9. Bxc7 Bd7 10. d4 Rc8 11. Bg3 g6` | [ply 16](http://localhost:5173/analysis?game_id=681722&ply=16) | [board](http://localhost:5173/analysis?fen=r1b1kb1r/ppp1pppp/2n2n2/5q2/5B2/2NP1B2/PPP1NPPP/R2QK2R%20w%20-%20-%200%209) |
| 226 | allowed | CLEARANCE | 4 | `8... Ne7 9. f4 c6 10. Be3 Qb6 11. Qxb6 axb6 12. Bxb6 Nc8 13. Bf2 b5 14. Bb3` | [ply 14](http://localhost:5173/analysis?game_id=681723&ply=14) | [board](http://localhost:5173/analysis?fen=r2qkbnr/pppb2pp/3p1p2/8/2BQP3/2N5/PPP2PPP/R1B2RK1%20b%20-%20-%201%208) |
| 227 | missed | CLEARANCE | 10 | `8. Qd5 Qe7 9. Qxb7 Rc8 10. Qb3 Nh6 11. Bxh6 gxh6 12. Nc3 c6 13. Rad1 h5` | [ply 14](http://localhost:5173/analysis?game_id=681723&ply=14) | [board](http://localhost:5173/analysis?fen=r2qkbnr/pppb2pp/3p1p2/8/2BQP3/8/PPP2PPP/RNB2RK1%20w%20-%20-%200%208) |
| 228 | missed | CLEARANCE | 6 | `16... Qd7 17. g4 Bg6 18. Re3 f6 19. Nh4 Bf7 20. Kh2 Rf8 21. Qe1 Ne7` | [ply 31](http://localhost:5173/analysis?game_id=681728&ply=31) | [board](http://localhost:5173/analysis?fen=r2qr1k1/1pp2ppp/1pn5/1N2p2b/8/P2P1N1P/1PP2PP1/R2QR1K1%20b%20-%20-%200%2016) |
| 229 | missed | DEFLECTION | 6 | `8... Bg4 9. Qd2 Nd4 10. c3 Nf3+ 11. gxf3 Bxh3 12. Qe2 Bxf1 13. Kxf1 Nxd5 14. Qxe5` | [ply 15](http://localhost:5173/analysis?game_id=681730&ply=15) | [board](http://localhost:5173/analysis?fen=r1bq1rk1/ppp2pp1/2n2n1p/2bPp3/2B5/3P3N/PPP2PPP/RNBQ1RK1%20b%20-%20-%200%208) |
| 230 | missed | EN_PASSANT | 4 | `8. e5 Ne4 9. Qd4 f5 10. exf6 Nxf6 11. Bxc4 Bxc3+ 12. Qxc3 d6` | [ply 14](http://localhost:5173/analysis?game_id=681736&ply=14) | [board](http://localhost:5173/analysis?fen=rnb1k2r/ppqp1ppp/5n2/3P4/1bp1P3/2N2N2/PP3PPP/R1BQKB1R%20w%20-%20-%200%208) |
| 231 | allowed | PIN | 10 | `9. Nxe5 Nxe5 10. Rxe5+ Be7 11. Bg5 Be6 12. Bxd5 Bxg5 13. Bxa8 Nd7 14. Bc6 Bf6` | [ply 15](http://localhost:5173/analysis?game_id=681739&ply=15) | [board](http://localhost:5173/analysis?fen=r1bqkb1r/2p2ppp/p1n5/1pnpp3/8/1B1P1N2/PPP2PPP/RNBQR1K1%20w%20-%20-%201%209) |
| 232 | allowed | FORK | 0 | `13. Bc6+ Nd7 14. Qh5+ g6 15. Qh3` | [ply 23](http://localhost:5173/analysis?game_id=681739&ply=23) | [board](http://localhost:5173/analysis?fen=r2qk2r/2p3pp/p2bp3/1pnB4/8/3P4/PPP2PPP/RNBQ2K1%20w%20-%20-%200%2013) |
| 233 | allowed | INTERMEZZO | 2 | `12. Qxh7+ Kf8 13. Nxe5 Rxe5 14. Nc4 Re8 15. Qh8+ Ke7 16. Qxg7 Rg8 17. Qe5+ Kf8` | [ply 21](http://localhost:5173/analysis?game_id=681774&ply=21) | [board](http://localhost:5173/analysis?fen=r1bqr1k1/ppp2ppp/8/3nn3/8/4PNP1/PPQN1PP1/R3KB1R%20w%20-%20-%200%2012) |
| 234 | missed | CLEARANCE | 6 | `11... h6 12. Bc4 Be6 13. Qe4 Ndb4 14. Rd1 Bd5 15. Qb1 Bxc4 16. Nxc4 Qe7 17. a3` | [ply 21](http://localhost:5173/analysis?game_id=681774&ply=21) | [board](http://localhost:5173/analysis?fen=r1bqr1k1/ppp2ppp/2n5/3nP3/8/4PNP1/PPQN1PP1/R3KB1R%20b%20-%20-%200%2011) |
| 235 | allowed | SACRIFICE | 2 | `20. Rh6 Rxd2 21. Qxf6+ Kd7 22. Nxd2 Qa5 23. Bh3 Bxh3 24. Rxh3 Qxa2 25. Rh7 Rf8` | [ply 37](http://localhost:5173/analysis?game_id=681774&ply=37) | [board](http://localhost:5173/analysis?fen=3rr3/ppp1kp2/4bn2/6Q1/1qN5/4PPP1/PP1R1P2/4KB1R%20w%20-%20-%201%2020) |
| 236 | missed | CLEARANCE | 10 | `19... Kd7 20. a3 Qb3 21. Bh3 Kc8 22. Bxe6+ fxe6 23. Qg4 Kb8` | [ply 37](http://localhost:5173/analysis?game_id=681774&ply=37) | [board](http://localhost:5173/analysis?fen=3rr3/ppp1kp2/4b3/3n2Q1/1qN5/4PPP1/PP1R1P2/4KB1R%20b%20-%20-%200%2019) |
| 237 | allowed | DISCOVERED_CHECK | 10 | `40... Nd1 41. h4 Bd2+ 42. Kg3 Be1+ 43. Kh2 Re2+ 44. Kh3 Nf2+ 45. Kg3 Nd3+ 46. Kh3` | [ply 78](http://localhost:5173/analysis?game_id=681775&ply=78) | [board](http://localhost:5173/analysis?fen=7R/p4p2/3k1p2/b3r3/5K2/1B3P2/PnP4P/8%20b%20-%20-%201%2040) |
| 238 | allowed | CLEARANCE | 4 | `7. Nc3 Qd8 8. d5 Ne5 9. Bd4 Ned7 10. Nf3 g6 11. Bc4 Bh6` | [ply 11](http://localhost:5173/analysis?game_id=681798&ply=11) | [board](http://localhost:5173/analysis?fen=r1b1kb1r/pp2pppp/2n2n2/3q4/3P4/4B3/PP3PPP/RN1QKBNR%20w%20-%20-%201%207) |
| 239 | missed | DISCOVERED_ATTACK | 7 | `6... d6 7. Nc3 a6 8. a4 d5 9. Ba2 dxe4 10. dxe4 Qxd1+ 11. Rxd1 b5 12. Nf3` | [ply 11](http://localhost:5173/analysis?game_id=681803&ply=11) | [board](http://localhost:5173/analysis?fen=r1bqkb1r/pp1p1p1p/2n1pnp1/1Np5/2B1PB2/3P4/PPP2PPP/R2QK1NR%20b%20-%20-%200%206) |
| 240 | allowed | CLEARANCE | 10 | `13. Qe2 b5 14. Bb3 h6 15. Bxf6+ Bxf6 16. c3 Kf8` | [ply 23](http://localhost:5173/analysis?game_id=681803&ply=23) | [board](http://localhost:5173/analysis?fen=2br4/1pq1kpbp/p1n1pnp1/2p1p1B1/2B5/3P1N2/PPP2PPP/R2QK2R%20w%20-%20-%201%2013) |
| 241 | missed | TRAPPED_PIECE | 4 | `13... b5 14. Bb3 c4 15. a4 cxb3 16. axb5 axb5 17. Re1 Kf8 18. c3 h6 19. Bh4` | [ply 25](http://localhost:5173/analysis?game_id=681803&ply=25) | [board](http://localhost:5173/analysis?fen=2br4/1pq1kpbp/p1n1pnp1/2p1p1B1/2B5/3P1N2/PPP2PPP/R2Q1RK1%20b%20-%20-%200%2013) |
| 242 | missed | FORK | 2 | `28... Bb4 29. h4 Bc3 30. Qf4 Bxa1 31. Rxa1 Rd4 32. Qe5 Rxc4 33. Re1 h5 34. Qa1` | [ply 55](http://localhost:5173/analysis?game_id=681803&ply=55) | [board](http://localhost:5173/analysis?fen=2b3k1/3q1p1p/p2b1Qp1/8/2P5/3r4/P4PPP/R3R1K1%20b%20-%20-%200%2028) |
| 243 | missed | CLEARANCE | 8 | `17. Nxe7+ Kf7 18. axb3 Qd6 19. Qxd6 cxd6 20. Nd5 Bxb2 21. Re7+ Kg8 22. Ra2 Bh8` | [ply 32](http://localhost:5173/analysis?game_id=681804&ply=32) | [board](http://localhost:5173/analysis?fen=r2q1rk1/2p1n1bp/p5p1/1p1N1pB1/8/1n3P1P/PPP2P2/R2QR1K1%20w%20-%20-%200%2017) |
| 244 | missed | CLEARANCE | 10 | `14... Be6 15. h3 Bb6 16. Rfe1 Rad8 17. Ba4 g6 18. Qh6+ Ke7 19. Nf1 Rh8 20. Qg5` | [ply 27](http://localhost:5173/analysis?game_id=681818&ply=27) | [board](http://localhost:5173/analysis?fen=r1b1rk2/pp3ppQ/2n2q2/2bp4/8/2P2N2/PPBN1PPP/R4RK1%20b%20-%20-%200%2014) |
| 245 | missed | CLEARANCE | 2 | `15... Be6 16. Ba4 Rac8 17. Nb3 Qh6 18. Qd3 Kg8 19. Re2 Rf8 20. Rfe1 Ne7 21. g3` | [ply 29](http://localhost:5173/analysis?game_id=681818&ply=29) | [board](http://localhost:5173/analysis?fen=r1b1rk2/p4ppQ/1pn2q2/2bp4/8/2P2N2/PPBN1PPP/4RRK1%20b%20-%20-%200%2015) |
| 246 | allowed | CLEARANCE | 8 | `6... Kh8 7. a3 Qe8 8. Bxf6 Rxf6 9. c4 d6 10. Nc3 Be6 11. b4 Bb6 12. Be2` | [ply 10](http://localhost:5173/analysis?game_id=681821&ply=10) | [board](http://localhost:5173/analysis?fen=rnbq1rk1/pppp2pp/5n2/2b3B1/8/4PN2/PPP2PPP/RN1QKB1R%20b%20-%20-%200%206) |
| 247 | missed | CLEARANCE | 6 | `6. Bxf6 Bxf2+ 7. Kxf2 Qxf6 8. e3 d5 9. Be2 g5 10. Ke1 Nc6 11. Qxd5+ Kh8` | [ply 10](http://localhost:5173/analysis?game_id=681821&ply=10) | [board](http://localhost:5173/analysis?fen=rnbq1rk1/pppp2pp/5n2/2b3B1/8/5N2/PPP1PPPP/RN1QKB1R%20w%20-%20-%200%206) |
| 248 | allowed | SKEWER | 10 | `21... Qd7 22. Rfe1 Nf4 23. Qf1 a6 24. Na3 Rxc1 25. Rxc1 Qa4 26. Nc4 Qxa2 27. Kh2` | [ply 40](http://localhost:5173/analysis?game_id=681825&ply=40) | [board](http://localhost:5173/analysis?fen=2rq3r/p4pk1/1p1p2p1/1N1Pp2n/1P2P3/3Q3P/P4PP1/2R2RK1%20b%20-%20-%201%2021) |
| 249 | missed | SACRIFICE | 2 | `26. Qxh3 Rxh3 27. Ne8+ Kf8 28. Nd6 Rh8 29. f4 Qh4 30. f5 Qh2+ 31. Kf2 Qf4+` | [ply 50](http://localhost:5173/analysis?game_id=681825&ply=50) | [board](http://localhost:5173/analysis?fen=7r/p2Q1pk1/1p1N2p1/3Pp1q1/1P2P3/7n/P4PP1/5RK1%20w%20-%20-%200%2026) |
| 250 | allowed | FORK | 8 | `8... Bb4` | [ply 14](http://localhost:5173/analysis?game_id=681844&ply=14) | [board](http://localhost:5173/analysis?fen=rn1qkbnr/pb3ppp/4p3/1p6/2pPP3/5N2/1P1NBPPP/R1BQK2R%20b%20-%20-%201%208) |
| 251 | allowed | SACRIFICE | 10 | `13... Bxf3 14. Qxf3 Qd5 15. Qg3 Nc6 16. Re1 a5 17. Qxg7` | [ply 24](http://localhost:5173/analysis?game_id=681844&ply=24) | [board](http://localhost:5173/analysis?fen=rn1qk2r/p4ppp/4p3/1p6/2pPb3/5B1P/1P3PP1/R1BQ1RK1%20b%20-%20-%201%2013) |
| 252 | missed | CLEARANCE | 6 | `20. Qxd4 e5 21. Qxd8 Rfxd8 22. Bg5 Rd6 23. Re1 Rd5 24. Bf6 Re8 25. f4 e4` | [ply 38](http://localhost:5173/analysis?game_id=681844&ply=38) | [board](http://localhost:5173/analysis?fen=r2q1rk1/p6p/4p1p1/1p3p2/2pnQ2R/7P/1P3PP1/R1B3K1%20w%20-%20-%200%2020) |
| 253 | allowed | FORK | 8 | `17. Be2 Bxe2 18. Rxe2 Qc6 19. Qd3 Nd7 20. Nd5 Nb6 21. Ne7+ Rxe7 22. Bxe7 Bd4+` | [ply 31](http://localhost:5173/analysis?game_id=681848&ply=31) | [board](http://localhost:5173/analysis?fen=2r1r1k1/1pq2pbp/p2p1np1/2p3B1/P1P1PPb1/2NB4/1P4PP/R2QR1K1%20w%20-%20-%201%2017) |
| 254 | allowed | FORK | 4 | `21. cxb5 Qd7 22. e5 Qe6 23. Nf6+ Kg7 24. Nxe8+ Qxe8 25. bxa6 Qd8 26. Rac1 Be6` | [ply 39](http://localhost:5173/analysis?game_id=681848&ply=39) | [board](http://localhost:5173/analysis?fen=2r1r1k1/5p1p/p1qp2p1/1ppN4/P1PbPPb1/3B4/1P1Q2PP/R3R2K%20w%20-%20-%200%2021) |
| 255 | missed | CLEARANCE | 4 | `22... Rfe8 23. Qxb6 Re7 24. Re3 Rae8 25. c3 Qg5 26. a4 Rxe4 27. Rxe4 Rxe4 28. Qxb7` | [ply 43](http://localhost:5173/analysis?game_id=681849&ply=43) | [board](http://localhost:5173/analysis?fen=r4rk1/1p3pp1/1ppp2q1/8/1PPQP3/P4R2/2P3P1/5RK1%20b%20-%20-%200%2022) |
| 256 | allowed | SKEWER | 2 | `9. Rb1 Qxa2 10. Rxb7 Nbd7 11. h3 Bxf3 12. Qxf3 Ne5 13. Qf4 Qd5 14. Nc3 Qd6` | [ply 15](http://localhost:5173/analysis?game_id=681893&ply=15) | [board](http://localhost:5173/analysis?fen=rn2kb1r/pp2pppp/2p2n2/8/4N1b1/3BBN2/PqP2PPP/R2Q1RK1%20w%20-%20-%201%209) |
| 257 | missed | CLEARANCE | 6 | `10... Qe5 11. Bf4 Qd4 12. Qe2 Nxe4 13. Bxe4 Qf6 14. Qd2 e5 15. Bg5 Qd6 16. Qa5` | [ply 19](http://localhost:5173/analysis?game_id=681893&ply=19) | [board](http://localhost:5173/analysis?fen=rn2kb1r/pp2pppp/2p2n2/8/4N3/3BBP2/PqPQ1P1P/R4RK1%20b%20-%20-%200%2010) |
| 258 | allowed | SKEWER | 2 | `12. Rfb1 Qa3 13. Rxb7 Rd8 14. Rxa7 Qb2 15. Qe1 Bb4 16. Rb1 Bxe1 17. Nd6+ Ke7` | [ply 21](http://localhost:5173/analysis?game_id=681893&ply=21) | [board](http://localhost:5173/analysis?fen=r3kb1r/pp1n1ppp/2p2n2/4p3/4NP2/3BB3/PqPQ1P1P/R4RK1%20w%20-%20-%200%2012) |
| 259 | allowed | SACRIFICE | 2 | `14. Qe2 Nxe4 15. Bf4 Nxd3 16. Qxe4+ Be7 17. cxd3 Qe6 18. Rxb7 Qxe4 19. dxe4 a5` | [ply 25](http://localhost:5173/analysis?game_id=681893&ply=25) | [board](http://localhost:5173/analysis?fen=r3kb1r/pp3ppp/2p2n2/4n3/4N3/3BB3/q1PQ1P1P/1R3RK1%20w%20-%20-%200%2014) |
| 260 | missed | FORK | 0 | `13... Nf3+ 14. Kg2 Nxd2 15. Bxd2 Qe5 16. Nxf6+ gxf6 17. Rxb7 Rg8+ 18. Kh1 Qd5+ 19. f3` | [ply 25](http://localhost:5173/analysis?game_id=681893&ply=25) | [board](http://localhost:5173/analysis?fen=r3kb1r/pp3ppp/2p2n2/4n3/4N3/3BB3/PqPQ1P1P/1R3RK1%20b%20-%20-%200%2013) |
| 261 | missed | CAPTURING_DEFENDER | 6 | `8... Bxf3 9. Bxf3 Nc6 10. Ne2 cxd4 11. Nxd4 Nxe5 12. c3 Nf6 13. g5 Ne4 14. Qa4+` | [ply 15](http://localhost:5173/analysis?game_id=681899&ply=15) | [board](http://localhost:5173/analysis?fen=rn1qkbnr/pp3ppp/4p3/2ppP3/3Pb1P1/2N2N1P/PPP2PB1/R1BQK2R%20b%20-%20-%200%208) |
| 262 | missed | HANGING_PIECE | 0 | `24... Rxc3` | [ply 47](http://localhost:5173/analysis?game_id=681899&ply=47) | [board](http://localhost:5173/analysis?fen=1r4k1/1p1R2pp/p1n1p3/5P2/2P2P2/1PN1r2P/P7/5RK1%20b%20-%20-%200%2024) |
| 263 | missed | PIN | 0 | `11. Bxc6 Qxc6 12. e5 Nd7 13. Bd2 h6 14. Nxe6 Qxe6 15. f4` | [ply 20](http://localhost:5173/analysis?game_id=681901&ply=20) | [board](http://localhost:5173/analysis?fen=r3k2r/1p1qppbp/p1n1bnp1/1B1p2N1/3PP3/2N4P/PP3PP1/R1BQ1RK1%20w%20-%20-%200%2011) |
| 264 | missed | DISCOVERED_ATTACK | 7 | `21. Qb3 Qd7 22. dxe5 b6 23. Rcc1 Nd5 24. e6 fxe6 25. Bxg7 Kxg7 26. Rc4 e5` | [ply 40](http://localhost:5173/analysis?game_id=681901&ply=40) | [board](http://localhost:5173/analysis?fen=3rr1k1/1p3pbp/p2q1np1/2R1p1N1/PP1P4/7P/1B3PP1/3QR1K1%20w%20-%20-%200%2021) |
| 265 | allowed | HANGING_PIECE | 0 | `34... Rxf3 35. Kg2 Rdf8 36. h4 Nd7 37. Ra2 R8f7 38. Rc2 Bc3 39. Ra2 h5 40. Ra6` | [ply 66](http://localhost:5173/analysis?game_id=681901&ply=66) | [board](http://localhost:5173/analysis?fen=3r2k1/7p/1n2p1p1/4b3/8/1r3NPP/4RP1K/8%20b%20-%20-%201%2034) |
| 266 | missed | HANGING_PIECE | 0 | `34. Nxe5 Ra8 35. Re2 Nd5 36. h4 Rb5 37. Nc6 Nb4 38. Ne5 Ra2 39. Rxa2 Nxa2` | [ply 66](http://localhost:5173/analysis?game_id=681901&ply=66) | [board](http://localhost:5173/analysis?fen=3r2k1/7p/1n2p1p1/4b3/8/1r3NPP/R4P1K/8%20w%20-%20-%200%2034) |
| 267 | allowed | CLEARANCE | 8 | `26. Rxf8+ Rxf8 27. Bc1 Qd5 28. Be3 Qc4 29. Qd2 Qb3 30. Re1 Rf5 31. Bf4 Qd5` | [ply 49](http://localhost:5173/analysis?game_id=681902&ply=49) | [board](http://localhost:5173/analysis?fen=2k2r1r/1p1qbR2/p1p1p3/P1P1P3/1P1Pp2p/7P/1B4P1/R2Q2K1%20w%20-%20-%201%2026) |
| 268 | missed | INTERFERENCE | 4 | `15... f5 16. g3 bxc5 17. Bd3 cxd4 18. Bxe4 fxe4 19. Rxe4 Bb6 20. Qf3 Re8 21. Rxe8+` | [ply 29](http://localhost:5173/analysis?game_id=681903&ply=29) | [board](http://localhost:5173/analysis?fen=r2q1rk1/p1bn1ppp/Bpp2p2/2P5/1P1Pb2N/8/P4PPP/R1BQR1K1%20b%20-%20-%200%2015) |
| 269 | allowed | PIN | 0 | `21... Rae8 22. c4 Bf5 23. Qc3 Re6 24. d5 Rh6 25. e6 Qh4 26. Re5 Qxh2+ 27. Kf1` | [ply 40](http://localhost:5173/analysis?game_id=681909&ply=40) | [board](http://localhost:5173/analysis?fen=r4rk1/1p4pp/2p5/p3P1q1/3P1p2/P1PQ1B1b/5PPP/R3R1K1%20b%20-%20-%201%2021) |
| 270 | allowed | CLEARANCE | 2 | `15. e4 Nd7 16. Bg5 Qa5 17. Rc1 Nxc5 18. e5 Nd7 19. Qa4 Qxa4 20. Nxa4 Rec8` | [ply 27](http://localhost:5173/analysis?game_id=681912&ply=27) | [board](http://localhost:5173/analysis?fen=rn1qr1k1/p4pbp/2p1p1p1/2Pp4/3P2b1/2N1PN2/P3BP2/R1BQ1RK1%20w%20-%20-%200%2015) |
| 271 | missed | SACRIFICE | 6 | `14... e5 15. Nxe5 Bxe2 16. Nxe2 Rxe5 17. dxe5 Bxe5 18. Rb1 Qg5+ 19. Ng3 Bxg3 20. fxg3` | [ply 27](http://localhost:5173/analysis?game_id=681912&ply=27) | [board](http://localhost:5173/analysis?fen=rn1qr1k1/p3ppbp/2p3p1/2Pp4/3P2b1/2N1PN2/P3BP2/R1BQ1RK1%20b%20-%20-%200%2014) |
| 272 | allowed | DISCOVERED_ATTACK | 3 | `21. Rab1 Rb8 22. Ba3 Ne6 23. Rxb8 Qxb8 24. Ne2 h5 25. Bc1 a6 26. Rd1 Qb5` | [ply 39](http://localhost:5173/analysis?game_id=681912&ply=39) | [board](http://localhost:5173/analysis?fen=r2qr1k1/p4pbp/2p3p1/2np4/8/2N2Q2/PB3P1N/R4RK1%20w%20-%20-%200%2021) |
| 273 | missed | FORK | 4 | `20... Ne5 21. Qg3 Nc4 22. Rab1 Nd2 23. Bc1 Nxf1 24. Nxf1 d4 25. Na4 Qd5 26. Rb7` | [ply 39](http://localhost:5173/analysis?game_id=681912&ply=39) | [board](http://localhost:5173/analysis?fen=r2qr1k1/p2n1pbp/2p3p1/2Pp4/8/2N2Q2/PB3P1N/R4RK1%20b%20-%20-%200%2020) |
| 274 | missed | CLEARANCE | 10 | `23... Rxb1 24. Qxc5 h5 25. Kg2 Qb6 26. Qd6 d4 27. Nf3 c5 28. Qd5 Qe6 29. Qg5` | [ply 45](http://localhost:5173/analysis?game_id=681912&ply=45) | [board](http://localhost:5173/analysis?fen=1r1qr1k1/p4p1p/2p3p1/2np4/8/2Q5/P4P1N/1RB2RK1%20b%20-%20-%200%2023) |
| 275 | allowed | PIN | 4 | `9. Nxd4 Bg6 10. Bb5+ Nd7` | [ply 15](http://localhost:5173/analysis?game_id=681915&ply=15) | [board](http://localhost:5173/analysis?fen=rn2kbnr/pp3ppp/4p3/3pPbB1/1q1p4/2N2N2/PPP2PPP/R2QKB1R%20w%20-%20-%200%209) |
| 276 | allowed | FORK | 0 | `23. Rc3+ Kb7 24. Rxc2 Rxa3 25. Ke2 Ne4 26. Rhc1 Nc5 27. Rb1 Kc6 28. Rcb2 Ra6` | [ply 43](http://localhost:5173/analysis?game_id=681915&ply=43) | [board](http://localhost:5173/analysis?fen=r7/5ppp/1pk1pn2/3p4/5P2/PR6/2b3PP/4K2R%20w%20-%20-%200%2023) |
| 277 | allowed | SKEWER | 2 | `40. Rc5+ Kd6 41. Rxf5 Rb2 42. Rxd4+ Ke6 43. Rfxf4 Rb3+ 44. Ke2 g5 45. Rf3 Rb2+` | [ply 77](http://localhost:5173/analysis?game_id=681915&ply=77) | [board](http://localhost:5173/analysis?fen=8/6p1/7p/4kp2/R2p1p1P/2R2K2/3r2P1/8%20w%20-%20-%200%2040) |
| 278 | allowed | MATE | 10 | `51. Rd7+ Kc8 52. Kxf2 f4 53. Rxd2 f3 54. Kxf3 h5 55. Kf4 Kb8 56. Rd8#` | [ply 99](http://localhost:5173/analysis?game_id=681915&ply=99) | [board](http://localhost:5173/analysis?fen=3k4/4R2R/7p/5p2/7P/4K3/3p1rP1/8%20w%20-%20-%201%2051) |
| 279 | missed | PROMOTION | 6 | `50... Kf8 51. Rd7 Kg8 52. Rh8+ Kxh8 53. Kxf2 d1=Q 54. Rxd1 h5 55. Kf3 Kg7 56. Kf4` | [ply 99](http://localhost:5173/analysis?game_id=681915&ply=99) | [board](http://localhost:5173/analysis?fen=4k3/4R2R/7p/5p2/7P/4K3/3p1rP1/8%20b%20-%20-%200%2050) |
| 280 | missed | SACRIFICE | 10 | `10. h3 e5 11. dxe5 Nc6 12. Bg2 Nxe5` | [ply 18](http://localhost:5173/analysis?game_id=681958&ply=18) | [board](http://localhost:5173/analysis?fen=rnbqr1k1/ppp1pp1p/3p1bpB/8/2PP2P1/2N2N2/PP3P1P/R2QKB1R%20w%20-%20-%200%2010) |
| 281 | allowed | CLEARANCE | 4 | `22. hxg6+ fxg6 23. d5 Rfd8 24. Qc4 b5 25. Qxc5 Qa2 26. Ra1 Rxd5+ 27. Bd4 Rxd4+` | [ply 41](http://localhost:5173/analysis?game_id=681963&ply=41) | [board](http://localhost:5173/analysis?fen=r4r2/pp3pbk/5pp1/2p4P/3P1Q2/2PKBN1P/1q3P2/3R3R%20w%20-%20-%201%2022) |
| 282 | missed | ATTRACTION | 0 | `21... c4+ 22. Kxc4 Rfc8+ 23. Qc7 Rxc7+ 24. Kd3 Rxc3+ 25. Ke4 Bh6 26. Ne5 Bxe3 27. Rd3` | [ply 41](http://localhost:5173/analysis?game_id=681963&ply=41) | [board](http://localhost:5173/analysis?fen=r4rk1/pp3pb1/5pp1/2p4P/3P1Q2/2PKBN1P/1q3P2/3R3R%20b%20-%20-%200%2021) |
| 283 | allowed | MATE | 6 | `20. Rac1+ Qc4 21. Rxc4+ dxc4 22. Bb6 Kb8 23. Qc7#` | [ply 37](http://localhost:5173/analysis?game_id=681977&ply=37) | [board](http://localhost:5173/analysis?fen=r1k4r/1b3Q1p/p3p1p1/3p4/4q3/NP2B3/P4PPP/R4RK1%20w%20-%20-%201%2020) |
| 284 | missed | SACRIFICE | 4 | `19... Kd6 20. Rac1 Rhc8 21. Qxb7 Ke5 22. Rxc8 Rxc8 23. Qxc8 g5 24. Qc3+ Kf5 25. h3` | [ply 37](http://localhost:5173/analysis?game_id=681977&ply=37) | [board](http://localhost:5173/analysis?fen=r6r/1b1k1Q1p/p3p1p1/3p4/4q3/NP2B3/P4PPP/R4RK1%20b%20-%20-%200%2019) |
| 285 | missed | TRAPPED_PIECE | 4 | `15. Ne5 Nf6 16. d6 Nc6 17. dxe7 Qxe7 18. Nxc6 Bxc6 19. Bf1 Qc7 20. Bg5 Rad8` | [ply 28](http://localhost:5173/analysis?game_id=681993&ply=28) | [board](http://localhost:5173/analysis?fen=rn1q1rk1/1p1bbppp/p7/2pP3n/8/P1N2N1P/1P2BPP1/R1BQR1K1%20w%20-%20-%200%2015) |
| 286 | missed | CLEARANCE | 6 | `18. Bd3 Rc8 19. Rc1 Be6 20. Qe2 Re8 21. Rcd1 Qc7 22. Ne4 Nxe4 23. Bxe4 Bc4` | [ply 34](http://localhost:5173/analysis?game_id=681993&ply=34) | [board](http://localhost:5173/analysis?fen=r2q1rk1/3bbppp/p1n2n2/1p6/1P6/P1N2N1P/1B2BPP1/R2QR1K1%20w%20-%20-%200%2018) |
| 287 | allowed | DEFLECTION | 6 | `43. g4+ hxg4 44. hxg4+ Ke5 45. Bc3+ Kd6 46. Kxe4 Kc6 47. Kxd3 Kb6 48. Ke4 Kxa6` | [ply 83](http://localhost:5173/analysis?game_id=682005&ply=83) | [board](http://localhost:5173/analysis?fen=8/5p2/P7/5kpp/1B2b3/3pK1PP/6P1/8%20w%20-%20-%200%2043) |
| 288 | allowed | MATE | 8 | `49. Kxd2 Bd5 50. Qc5 Ka2 51. Qa5+ Kb3 52. Qb4+ Ka2 53. Qb2#` | [ply 95](http://localhost:5173/analysis?game_id=682005&ply=95) | [board](http://localhost:5173/analysis?fen=2Q5/5p2/8/6p1/4b1P1/1kB1K3/3p2P1/8%20w%20-%20-%201%2049) |
| 289 | missed | SACRIFICE | 10 | `48... Kb5 49. Qd7+ Bc6 50. Qxd2 f6 51. Qd3+ Kb6 52. Bd4+ Kc7 53. Bxf6 Kb7 54. Be5` | [ply 95](http://localhost:5173/analysis?game_id=682005&ply=95) | [board](http://localhost:5173/analysis?fen=2Q5/5p2/8/6p1/2k1b1P1/2B1K3/3p2P1/8%20b%20-%20-%200%2048) |
| 290 | allowed | FORK | 0 | `15. dxe5 Nxe5 16. Nxe5 Rxe5 17. Qd2 Rae8 18. Rad1 h6 19. Nxd5 Nxd5 20. Bxd5 Qg6` | [ply 27](http://localhost:5173/analysis?game_id=682008&ply=27) | [board](http://localhost:5173/analysis?fen=r3r1k1/5ppp/p1nq1n2/1p1ppb2/3P4/PBN2N1P/1PP2PP1/R3QRK1%20w%20-%20-%200%2015) |
| 291 | allowed | FORK | 0 | `23. g4 Rxf4 24. gxh5 Re6 25. Re3 Rxh4 26. f3 Bf5 27. Rc3 g6 28. Rc7 Rxh5` | [ply 43](http://localhost:5173/analysis?game_id=682008&ply=43) | [board](http://localhost:5173/analysis?fen=4r1k1/5ppp/p7/1p1p1r1q/4bQ1P/PB4P1/1PP2P2/4RRK1%20w%20-%20-%201%2023) |
| 292 | missed | CLEARANCE | 2 | `11... e6 12. f5 Bb4+ 13. Kf1 exf5 14. g5 f4 15. Ne2 Bd3 16. Bxf4 Nc6 17. Kf2` | [ply 21](http://localhost:5173/analysis?game_id=682050&ply=21) | [board](http://localhost:5173/analysis?fen=rn1qkb1r/pp2pppp/6b1/3pP3/2pP1PP1/8/PP4BP/R1BQK1NR%20b%20-%20-%200%2011) |
| 293 | allowed | CLEARANCE | 8 | `11... Bxf3 12. gxf3 Rg6+ 13. Kh2 Nc6 14. Ne2 e5 15. f4 Qf6 16. dxe5 dxe5 17. Qd5+` | [ply 20](http://localhost:5173/analysis?game_id=682060&ply=20) | [board](http://localhost:5173/analysis?fen=rn1q2k1/ppp1p1bp/3p1r2/7p/2PP2b1/2N2N1P/PP3PP1/R1BQ1RK1%20b%20-%20-%200%2011) |
| 294 | allowed | PIN | 2 | `18... Bxf4+ 19. Ng3 h4 20. Bxf4 Qxf4 21. Qc2 hxg3+ 22. fxg3 Qf7 23. Qe2 Nd7 24. Rf1` | [ply 34](http://localhost:5173/analysis?game_id=682060&ply=34) | [board](http://localhost:5173/analysis?fen=rn4k1/pp2p3/3p2p1/2pPbq1p/2P1NP2/7P/PP3P1K/R1BQ4%20b%20-%20-%200%2018) |
| 295 | allowed | FORK | 8 | `10. Bg5 Bg7 11. Bxf6 Bxf6 12. Nxd5 Bxd4 13. Nb4 Nxb4 14. Qxd4 Qxd4 15. Nxd4 Rd8` | [ply 17](http://localhost:5173/analysis?game_id=682083&ply=17) | [board](http://localhost:5173/analysis?fen=r2qkb1r/4pp1p/p1n2np1/1p1p4/3P2b1/1BN2N2/PPP2PPP/R1BQ1RK1%20w%20-%20-%200%2010) |
| 296 | missed | CLEARANCE | 8 | `9... e6 10. Ne2 Bxf3 11. gxf3 Bd6 12. Kh1 Nh5 13. Rg1 Qf6 14. Qd3 Qh4 15. Rg2` | [ply 17](http://localhost:5173/analysis?game_id=682083&ply=17) | [board](http://localhost:5173/analysis?fen=r2qkb1r/4pppp/p1n2n2/1p1p4/3P2b1/1BN2N2/PPP2PPP/R1BQ1RK1%20b%20-%20-%200%209) |
| 297 | missed | CAPTURING_DEFENDER | 2 | `10... Bxf3 11. Qxf3 Nxd4 12. Qd3 Nxb3 13. axb3 b4 14. Na4 Bg7 15. Nc5` | [ply 19](http://localhost:5173/analysis?game_id=682083&ply=19) | [board](http://localhost:5173/analysis?fen=r2qkb1r/4pp1p/p1n2np1/1p1p4/3P2b1/1BN2N1P/PPP2PP1/R1BQ1RK1%20b%20-%20-%200%2010) |
| 298 | missed | EN_PASSANT | 4 | `15... b4 16. Ne2 Bg7 17. c4 bxc3 18. bxc3 Ne4 19. Be3 Nxc3 20. Nxc3 Bxc3 21. Ra4` | [ply 29](http://localhost:5173/analysis?game_id=682083&ply=29) | [board](http://localhost:5173/analysis?fen=r2qkb1r/4pp2/p4np1/1p1p4/8/1PN3P1/1PP2PQ1/R1B2RK1%20b%20-%20-%200%2015) |
| 299 | allowed | FORK | 4 | `17. Nxd5 Rc8 18. Rfe1 e6 19. Nb6 Qc7 20. Nxc8 Qxc8 21. Rad1 Be7 22. Bxe7 Kxe7` | [ply 31](http://localhost:5173/analysis?game_id=682083&ply=31) | [board](http://localhost:5173/analysis?fen=r3kb1r/3qpp2/p5p1/1p1p2B1/6n1/1PN3P1/1PP2PQ1/R4RK1%20w%20-%20-%201%2017) |
| 300 | allowed | FORK | 0 | `18. Nc7+ Kd7 19. Qb7 Qxf2+ 20. Rxf2 Rh1+ 21. Qxh1 Nxf2 22. Kxf2 Ra7 23. Nxa6 e5` | [ply 33](http://localhost:5173/analysis?game_id=682083&ply=33) | [board](http://localhost:5173/analysis?fen=r3kb1r/4pp2/p5p1/1p1N1qB1/6n1/1P4P1/1PP2PQ1/R4RK1%20w%20-%20-%201%2018) |
| 301 | allowed | MATE | 6 | `19. Nc7+ Kd7 20. Rfd1+ Qd3 21. Rxd3+ Kc8 22. Qxa8#` | [ply 35](http://localhost:5173/analysis?game_id=682083&ply=35) | [board](http://localhost:5173/analysis?fen=r3kb2/4pp2/p5p1/1p1N1q2/5Bn1/1P4P1/1PP2PQr/R4RK1%20w%20-%20-%201%2019) |
| 302 | missed | SACRIFICE | 4 | `18... Rc8 19. Nb6 Bh6 20. Nxc8 Qxc8 21. Bxh6 Rxh6 22. c4 bxc4 23. Rfc1 Ne5 24. Qd5` | [ply 35](http://localhost:5173/analysis?game_id=682083&ply=35) | [board](http://localhost:5173/analysis?fen=r3kb1r/4pp2/p5p1/1p1N1q2/5Bn1/1P4P1/1PP2PQ1/R4RK1%20b%20-%20-%200%2018) |
| 303 | missed | ATTRACTION | 4 | `19... Rc8 20. Rae1 Rxf2 21. Rxf2 Nxf2 22. Kxf2 Rxc2+ 23. Kg1 e6 24. g4 Bc5+ 25. Kh1` | [ply 37](http://localhost:5173/analysis?game_id=682083&ply=37) | [board](http://localhost:5173/analysis?fen=r3kb2/4pp2/p5p1/1p1N1q2/5Bn1/1P3QP1/1PP2P1r/R4RK1%20b%20-%20-%200%2019) |
| 304 | missed | DISCOVERED_ATTACK | 9 | `20... Qc5+ 21. Kh1 Rf2 22. Qe1 Ng4 23. h3 Qe3 24. Nf3 d4 25. hxg4 Bxf3 26. Qxe3` | [ply 39](http://localhost:5173/analysis?game_id=682103&ply=39) | [board](http://localhost:5173/analysis?fen=5rk1/pb2q1pp/4p2n/1P1pP3/2p5/2P5/P1BNQ1PP/R5K1%20b%20-%20-%200%2020) |
| 305 | allowed | CLEARANCE | 4 | `24. Bxf5 exf5 25. Nd4 Bc8 26. Qf3 f4 27. gxf4 h6 28. Re1 Kh8 29. e6 Nf6` | [ply 45](http://localhost:5173/analysis?game_id=682103&ply=45) | [board](http://localhost:5173/analysis?fen=5rk1/pb4pp/4p3/1P1pPq2/2p3nP/2P2NP1/P1B1Q3/R5K1%20w%20-%20-%201%2024) |
| 306 | allowed | SACRIFICE | 6 | `27. Kg1 g5 28. Nxd4 Rxf1+ 29. Qxf1 Nxf1 30. Kxf1 gxh4 31. gxh4 Kf7 32. a4 a6` | [ply 51](http://localhost:5173/analysis?game_id=682103&ply=51) | [board](http://localhost:5173/analysis?fen=6k1/pb4pp/4p3/1P2Pr2/2pp3P/2P1nNP1/P3Q1K1/5R2%20w%20-%20-%201%2027) |
| 307 | allowed | PROMOTION | 8 | `57. Kb5 g3 58. a6 Bc8 59. b7 Bd7+ 60. Kb4 g2 61. c8=Q g1=R 62. Qxd7+ Ke4` | [ply 111](http://localhost:5173/analysis?game_id=682103&ply=111) | [board](http://localhost:5173/analysis?fen=8/1bP5/1P6/P3pk2/2K3p1/8/8/8%20w%20-%20-%200%2057) |
| 308 | missed | TRAPPED_PIECE | 2 | `10. Rd1 Bg4 11. Rxd8+ Rxd8 12. Qb5 Bxf3 13. gxf3 fxe5 14. Qxb7 Nd4 15. Bb5+ Kf7` | [ply 18](http://localhost:5173/analysis?game_id=682106&ply=18) | [board](http://localhost:5173/analysis?fen=r1bqk1nr/ppp1b1pp/2n2p2/4P3/5B2/2N2N2/PPP1Q1PP/R3KB1R%20w%20-%20-%200%2010) |
| 309 | missed | CAPTURING_DEFENDER | 4 | `14. Nb5 Qc6 15. Qxc6 Nxc6 16. Nxc7 Rb8 17. d5 Nce5 18. Nc5 b6 19. N5e6 Rf7` | [ply 26](http://localhost:5173/analysis?game_id=682110&ply=26) | [board](http://localhost:5173/analysis?fen=rnb2r1k/ppp3pp/3q1pn1/8/2QP4/2NN4/PPP3PP/2KR1B1R%20w%20-%20-%200%2014) |
| 310 | missed | CLEARANCE | 4 | `13... cxd4 14. Qxd4 Nc6 15. Qd5 Rad8 16. Bf4 Qc7 17. Qc4 Qb6 18. Qb3 Qa6 19. Red1` | [ply 25](http://localhost:5173/analysis?game_id=682111&ply=25) | [board](http://localhost:5173/analysis?fen=rn3rk1/pp1q1ppp/3b1p2/2p5/3P4/6P1/PPPQ1PNP/R1B1R1K1%20b%20-%20-%200%2013) |
| 311 | missed | FORK | 0 | `15... Nc4 16. Qd3 Nxe3 17. Nxe3 Rad8 18. Bd2 Rfe8 19. Rd1 h5 20. b3 g6 21. a4` | [ply 29](http://localhost:5173/analysis?game_id=682111&ply=29) | [board](http://localhost:5173/analysis?fen=r4rk1/pp1q1ppp/3b1p2/2pPn3/8/4R1P1/PPPQ1PNP/R1B3K1%20b%20-%20-%200%2015) |
| 312 | missed | INTERMEZZO | 6 | `21... Bxe3 22. fxe3 Qh5 23. Bxe5 b5 24. Rf4 Qxe5 25. Nf3 Qd6 26. Rd4 Rfe8 27. Kg2` | [ply 41](http://localhost:5173/analysis?game_id=682111&ply=41) | [board](http://localhost:5173/analysis?fen=2r2rk1/1p3ppp/5p2/2bPn3/R5qN/1P2R1P1/1BPQ1P1P/6K1%20b%20-%20-%200%2021) |
| 313 | missed | PIN | 0 | `25... g5 26. fxg6 hxg6 27. Rae1 Re5 28. Rc1 Re4 29. Rc4 Rf4 30. Qc3 Rxf3 31. Rxf3` | [ply 49](http://localhost:5173/analysis?game_id=682127&ply=49) | [board](http://localhost:5173/analysis?fen=3rr1k1/pp3ppp/1b3p2/5P2/3B4/5NqP/PP1Q2P1/R4RK1%20b%20-%20-%200%2025) |
| 314 | allowed | DISCOVERED_CHECK | 10 | `10... Bg4 11. Qe3` | [ply 18](http://localhost:5173/analysis?game_id=682171&ply=18) | [board](http://localhost:5173/analysis?fen=r1b1k2r/ppp1qppp/3b1n2/3P4/8/2N2Q2/PPPPB1PP/R1B1K2R%20b%20-%20-%201%2010) |
| 315 | allowed | PIN | 0 | `18... Rf5 19. Ne2 Nxd5 20. g4 Rf6 21. Rd1 Ne3+ 22. Ke1 Nxd1 23. Kxd1 c6 24. Kd2` | [ply 34](http://localhost:5173/analysis?game_id=682171&ply=34) | [board](http://localhost:5173/analysis?fen=6k1/ppp2ppp/5n2/2PPr3/5B2/2N5/PPP3PP/R4K2%20b%20-%20-%201%2018) |
| 316 | missed | SACRIFICE | 4 | `20... g5 21. f3 Nxh2 22. Kxh2 Ke7 23. a4 Rac8 24. axb5 axb5 25. f4 gxh4 26. g4` | [ply 39](http://localhost:5173/analysis?game_id=682178&ply=39) | [board](http://localhost:5173/analysis?fen=r3k2r/5pp1/p3pq2/1p1p1p2/1P1P2nN/P2Q2P1/5P1P/4RRK1%20b%20-%20-%200%2020) |
| 317 | allowed | CLEARANCE | 10 | `23. gxh4 Qxh4+ 24. Kg2 f4 25. Rf2 g5 26. Rd1 Kd7 27. Kg1 Rh8 28. Rg2 f6` | [ply 43](http://localhost:5173/analysis?game_id=682178&ply=43) | [board](http://localhost:5173/analysis?fen=2r1k3/5pp1/p3pq2/1p1p1p2/1P1P3r/P2Q1PP1/7K/4RR2%20w%20-%20-%200%2023) |
| 318 | missed | TRAPPED_PIECE | 4 | `22... f4 23. Kg2 fxg3 24. Rh1 Rxh4 25. Rxh4 Qxh4 26. Rh1 Qf4 27. Rh8+ Kd7 28. Rxc8` | [ply 43](http://localhost:5173/analysis?game_id=682178&ply=43) | [board](http://localhost:5173/analysis?fen=2r1k2r/5pp1/p3pq2/1p1p1p2/1P1P3N/P2Q1PP1/7K/4RR2%20b%20-%20-%200%2022) |
| 319 | allowed | PIN | 0 | `25. Qxf5 Qxd4 26. Rf2 Rh8 27. Qg5+ Kd7 28. Rd2 Qc3 29. Rc1 Qxc1 30. Rxd5+ exd5` | [ply 47](http://localhost:5173/analysis?game_id=682178&ply=47) | [board](http://localhost:5173/analysis?fen=2r5/4kpp1/p3p3/1p1p1p2/1P1P3q/P2Q1P2/6K1/4RR2%20w%20-%20-%201%2025) |
| 320 | missed | CLEARANCE | 4 | `24... f4 25. Re2 Kd7 26. Kg1 Rh8 27. Rg2 g5 28. Qd2 Qh1+ 29. Kf2 Qh4+ 30. Ke2` | [ply 47](http://localhost:5173/analysis?game_id=682178&ply=47) | [board](http://localhost:5173/analysis?fen=2r1k3/5pp1/p3p3/1p1p1p2/1P1P3q/P2Q1P2/6K1/4RR2%20b%20-%20-%200%2024) |
| 321 | allowed | CLEARANCE | 8 | `12... Bxe6 13. Bxf4 Nd7 14. a4 h6 15. Bg3` | [ply 22](http://localhost:5173/analysis?game_id=682182&ply=22) | [board](http://localhost:5173/analysis?fen=rn2k2r/pp2bppp/2p1Q3/8/3P1pb1/2PB1N2/PP4PP/R1B2RK1%20b%20-%20-%200%2012) |
| 322 | allowed | CLEARANCE | 8 | `4. Nxe5` | [ply 5](http://localhost:5173/analysis?game_id=682185&ply=5) | [board](http://localhost:5173/analysis?fen=rnbqk2r/pppp1ppp/5n2/4p3/1bP5/2N2N2/PP1PPPPP/R1BQKB1R%20w%20-%20-%201%204) |
| 323 | missed | CLEARANCE | 6 | `5... a5 6. Qc2 a4 7. e3 d6 8. Be2 Be6 9. Nxb4 Nxb4 10. Qb1 e4 11. Nd4` | [ply 9](http://localhost:5173/analysis?game_id=682185&ply=9) | [board](http://localhost:5173/analysis?fen=r1bqk2r/pppp1ppp/2n2n2/3Np3/1bP5/1Q3N2/PP1PPPPP/R1B1KB1R%20b%20-%20-%200%205) |
| 324 | missed | FORK | 8 | `23... Rc8+ 24. Kb4 Qc4+ 25. Ka3 Rc6 26. Qb8+ Rf8 27. Qxa7 Ra6+ 28. Qxa6 Qxa6+ 29. Kb4` | [ply 45](http://localhost:5173/analysis?game_id=682185&ply=45) | [board](http://localhost:5173/analysis?fen=5rk1/pp3rpp/3Q4/8/3P2P1/2K1P1P1/PP5P/R1B2q2%20b%20-%20-%200%2023) |
| 325 | allowed | FORK | 0 | `17. Bxd5 Rb8 18. Rxe4 exd4 19. Qh5 Qd7 20. Rxd4 Qf5 21. Bxf7+ Rxf7 22. Qxf5 Bxf5` | [ply 31](http://localhost:5173/analysis?game_id=682190&ply=31) | [board](http://localhost:5173/analysis?fen=r1b2rk1/2q2ppp/p2b4/1p1pp3/3Nn3/1BP3P1/PP3P1P/R1BQR1K1%20w%20-%20-%200%2017) |
| 326 | allowed | HANGING_PIECE | 0 | `24. Qxf3 Be7 25. Be3 Qd6 26. Rh3 Rad8 27. a4 bxa4 28. g4 f4 29. Bf2 Qe6` | [ply 45](http://localhost:5173/analysis?game_id=682190&ply=45) | [board](http://localhost:5173/analysis?fen=r4rk1/6pp/p2b4/1pq1pp2/7R/2P2bP1/PP5P/R1BQ3K%20w%20-%20-%200%2024) |
| 327 | missed | PIN | 0 | `23... Qc6 24. Kg2 Be7 25. a4 bxa4 26. Rxa4 Bxh4 27. Ra5 Be7 28. h3 Bh5 29. Rd5` | [ply 45](http://localhost:5173/analysis?game_id=682190&ply=45) | [board](http://localhost:5173/analysis?fen=r4rk1/6pp/p2b4/1pq1pp2/6bR/2P2PP1/PP5P/R1BQ3K%20b%20-%20-%200%2023) |
| 328 | missed | CLEARANCE | 4 | `7. Qd1 e6 8. g3 Nf6 9. Bg2 Be7` | [ply 12](http://localhost:5173/analysis?game_id=682196&ply=12) | [board](http://localhost:5173/analysis?fen=r2qkbnr/pp2pppp/3p4/2p5/3nP3/2NP1Q1P/PPP2PP1/R1B1KB1R%20w%20-%20-%200%207) |
| 329 | missed | TRAPPED_PIECE | 4 | `12. Bb2 d5 13. exd5 Nxd5 14. Rxa1 g6 15. Kc2 Nb4+ 16. Kb1 Bg7 17. f5 Nc6` | [ply 22](http://localhost:5173/analysis?game_id=682196&ply=22) | [board](http://localhost:5173/analysis?fen=2kr1b1r/pp2pppp/3p1n2/q1p5/4PP2/1PNP2QP/P2KB1P1/n1B4R%20w%20-%20-%200%2012) |
| 330 | missed | CLEARANCE | 6 | `5. fxe5 d5 6. exd6 cxd6 7. d4 Bb6 8. Bg5 Bg4 9. Qd3 f6 10. Bd2` | [ply 8](http://localhost:5173/analysis?game_id=682217&ply=8) | [board](http://localhost:5173/analysis?fen=r1bqk2r/ppppnppp/2n5/2b1p3/4PP2/2N2N2/PPPP2PP/R1BQKB1R%20w%20-%20-%200%205) |
| 331 | allowed | CLEARANCE | 10 | `11... g5 12. Bg3 Nf5 13. d4 Bxf3 14. dxc5 Bxg2 15. Rg1 d4 16. Nb5 Qd5 17. Qd2` | [ply 20](http://localhost:5173/analysis?game_id=682217&ply=20) | [board](http://localhost:5173/analysis?fen=r2q1rk1/pp2npp1/2n4p/2bpP3/6bB/2NP1N2/PPP1B1PP/R2QK2R%20b%20-%20-%200%2011) |
| 332 | missed | PIN | 6 | `e1g1 d8d7 h2h3 g4h5 f3d4 h5d1 c4b5 d1a4 b5d7 e8d7 d4f5 g7g6` | [ply 14](http://localhost:5173/analysis?game_id=682228&ply=14) | [board](http://localhost:5173/analysis?fen=r2qk1nr/ppp2ppp/8/3Pp3/1bBnP1b1/5N2/PP1N1PPP/R1BQK2R%20w%20-%20-%200%208) |
| 333 | allowed | SACRIFICE | 4 | `9... c6 10. dxc6 b5 11. Bxb5 Qa5 12. Qxa5 Bxa5 13. b4 Bxb4 14. Rb1 a5` | [ply 16](http://localhost:5173/analysis?game_id=682228&ply=16) | [board](http://localhost:5173/analysis?fen=r2qk1nr/ppp2ppp/8/3Pp3/QbBnP3/5b1P/PP1N1PP1/R1B1K2R%20b%20-%20-%201%209) |
| 334 | missed | FORK | 8 | `9. gxf3 c6 10. Kf1 Ne7 11. Nb3 cxd5 12. Nxd4 dxc4 13. Qa4+ Qd7 14. Nb5 Nc6` | [ply 16](http://localhost:5173/analysis?game_id=682228&ply=16) | [board](http://localhost:5173/analysis?fen=r2qk1nr/ppp2ppp/8/3Pp3/1bBnP3/5b1P/PP1N1PP1/R1BQK2R%20w%20-%20-%200%209) |
| 335 | allowed | FORK | 2 | `16... Bxf4 17. Bxf4 Qf2+ 18. Kh1 Qxf4 19. h3 Rad8 20. Re1 Rfe8 21. Rb1 Ng3+ 22. Kg1` | [ply 30](http://localhost:5173/analysis?game_id=682286&ply=30) | [board](http://localhost:5173/analysis?fen=r4rk1/p4ppp/2Qb4/8/4nR1q/4B3/PPP3PP/R5K1%20b%20-%20-%201%2016) |
| 336 | missed | CLEARANCE | 10 | `16. h3 Rae8 17. Rf3 Bb8 18. Qc4 Qe7 19. Raf1 Qd6 20. Bf4 Qg6 21. Re3 Bxf4` | [ply 30](http://localhost:5173/analysis?game_id=682286&ply=30) | [board](http://localhost:5173/analysis?fen=r4rk1/p4ppp/2Qb4/8/4n2q/4B3/PPP3PP/R4RK1%20w%20-%20-%200%2016) |
| 337 | allowed | CLEARANCE | 4 | `20... Qf6 21. Rfe1 Bd5 22. Qd2 Qc6 23. Bxd4 cxd4 24. Rxe8+ Rxe8 25. f3 Rd8 26. Kf2` | [ply 38](http://localhost:5173/analysis?game_id=682291&ply=38) | [board](http://localhost:5173/analysis?fen=1r1qr1k1/p1p2p1p/4b1p1/2p5/3b4/PP2B2P/2B1QPP1/3R1RK1%20b%20-%20-%200%2020) |
| 338 | allowed | MATE | 8 | `31... Rxd3 32. Ra1 g5 33. Kh1 Rd2 34. Rg1 Qg3 35. Rf1 Qxg2#` | [ply 60](http://localhost:5173/analysis?game_id=682291&ply=60) | [board](http://localhost:5173/analysis?fen=8/p4pkp/6p1/8/3p4/1r1B3P/5qPK/6R1%20b%20-%20-%201%2031) |
| 339 | allowed | MATE | 8 | `32... Qf4+ 33. Kh1 Qxe4 34. Kh2 Qe5+ 35. Kh1 Qg3 36. Rd1 Qxg2#` | [ply 62](http://localhost:5173/analysis?game_id=682291&ply=62) | [board](http://localhost:5173/analysis?fen=8/p4pkp/6p1/8/3pB3/7P/1r3qPK/6R1%20b%20-%20-%201%2032) |
| 340 | allowed | INTERFERENCE | 4 | `21... Qxh2+ 22. Kf1 Bxg2+ 23. Ke2 Qxe5+ 24. Kd2 Qf4+ 25. Qe3 Rad8+ 26. Kc1 Qxe3+ 27. Rxe3` | [ply 40](http://localhost:5173/analysis?game_id=682292&ply=40) | [board](http://localhost:5173/analysis?fen=r6r/p1p1kpp1/1p2p3/3bN3/5q2/P1PQ4/2B2PPP/R3R1K1%20b%20-%20-%201%2021) |
| 341 | allowed | ATTRACTION | 6 | `25... Qf6 26. Qe3 Rad8 27. Rad1 Bxf3+ 28. Qxf3 Qxf3+ 29. Kxf3 Rh3+ 30. Rg3 Rxg3+ 31. Kxg3` | [ply 48](http://localhost:5173/analysis?game_id=682292&ply=48) | [board](http://localhost:5173/analysis?fen=r6r/p1p1kpp1/1p2p3/3b2q1/8/P1PQ1N2/2B1KP2/R5R1%20b%20-%20-%201%2025) |
| 342 | missed | PIN | 4 | `30. Rxg7 Rhf8 31. Re1 Rd6 32. Bg6 Qb5+ 33. c4 Qxc4+ 34. Kg1 Kd8 35. Bxf7 Qd4` | [ply 58](http://localhost:5173/analysis?game_id=682292&ply=58) | [board](http://localhost:5173/analysis?fen=3r3r/p1p1kpp1/1p2p3/8/8/P1PB1Q2/1q3P2/3R1KR1%20w%20-%20-%200%2030) |
| 343 | missed | CLEARANCE | 10 | `32. Qh4+ Qf6 33. Qg3 Rd6 34. Rc1 c5 35. Rc4 Rd5 36. Ra4 a5 37. Bb5 g6` | [ply 62](http://localhost:5173/analysis?game_id=682292&ply=62) | [board](http://localhost:5173/analysis?fen=3r4/p1p1kpp1/1p2p3/8/8/P1qB4/5P2/3R1K1Q%20w%20-%20-%200%2032) |
| 344 | allowed | PIN | 2 | `8... dxe4 9. Nxe4 Qe7 10. Bd3 Bg4` | [ply 14](http://localhost:5173/analysis?game_id=682296&ply=14) | [board](http://localhost:5173/analysis?fen=r1bqk1nr/ppp2ppp/1bn5/3p4/1P1PP3/P1N2N2/5PPP/R1BQKB1R%20b%20-%20-%200%208) |
| 345 | missed | CLEARANCE | 6 | `8. Bg5 f6 9. Bc1 Bg4 10. e3 f5 11. Be2 Nf6` | [ply 14](http://localhost:5173/analysis?game_id=682296&ply=14) | [board](http://localhost:5173/analysis?fen=r1bqk1nr/ppp2ppp/1bn5/3p4/1P1P4/P1N2N2/4PPPP/R1BQKB1R%20w%20-%20-%200%208) |
| 346 | allowed | ATTRACTION | 6 | `11... Nf6 12. Bd3 Bf5 13. Nxf6+ Qxf6 14. Bxf5 Bxf2+ 15. Kxf2 Qxf5+ 16. Qf3 Qxb1 17. Re1+` | [ply 20](http://localhost:5173/analysis?game_id=682296&ply=20) | [board](http://localhost:5173/analysis?fen=r1bqk1nr/ppp2ppp/8/8/1P1bN3/P7/5PPP/1RBQKB1R%20b%20-%20-%201%2011) |
| 347 | allowed | DISCOVERED_CHECK | 6 | `13... Qxf2+ 14. Kd2 Bf5 15. Rf1` | [ply 24](http://localhost:5173/analysis?game_id=682296&ply=24) | [board](http://localhost:5173/analysis?fen=r1b1k2r/ppp2ppp/5q2/8/1P1b4/P7/4BPPP/1RBQK2R%20b%20-%20-%201%2013) |
| 348 | missed | CLEARANCE | 10 | `13. Bb5+ c6 14. Qe2+ Be6 15. Bc4 Bxf2+ 16. Qxf2 Qc3+ 17. Bd2 Qxc4 18. Rc1 Qe4+` | [ply 24](http://localhost:5173/analysis?game_id=682296&ply=24) | [board](http://localhost:5173/analysis?fen=r1b1k2r/ppp2ppp/5q2/8/1P1b4/P7/5PPP/1RBQKB1R%20w%20-%20-%200%2013) |
| 349 | allowed | DISCOVERED_ATTACK | 9 | `15... Rad8 16. Rb3 Be6 17. Rb1 Bc4 18. Bg5 Qxg5 19. Bxc4 Bxf2+ 20. Rxf2 Rxd1+ 21. Rxd1` | [ply 28](http://localhost:5173/analysis?game_id=682296&ply=28) | [board](http://localhost:5173/analysis?fen=r4rk1/ppp2ppp/5q2/5b2/1P1b4/P2B4/5PPP/1RBQ1RK1%20b%20-%20-%201%2015) |
| 350 | allowed | CLEARANCE | 2 | `16. Nd4 Ra6 17. Qf3 Be4 18. Qc3 Rfa8 19. Rfe1 Qa7 20. Re3 Qb6 21. h4 Bg6` | [ply 29](http://localhost:5173/analysis?game_id=682302&ply=29) | [board](http://localhost:5173/analysis?fen=r4rk1/4qpp1/2p1p2p/1p1pPb2/1P6/P4N2/2P2PPP/R2Q1RK1%20w%20-%20-%200%2016) |
| 351 | missed | FORK | 8 | `25... d4 26. Qf2 Bg6 27. h4 Bh5 28. Rb1 Qc3 29. Ne4 Qd3 30. Re1 Bg6 31. Nd6` | [ply 49](http://localhost:5173/analysis?game_id=682302&ply=49) | [board](http://localhost:5173/analysis?fen=5rk1/5pp1/3Np2p/2qpP3/5P2/5Q2/2b3PP/5R1K%20b%20-%20-%200%2025) |
| 352 | missed | FORK | 2 | `28... Rg6 29. Qf2 Bxg2+ 30. Qxg2 Rxg2 31. Kxg2 Qc2+ 32. Rf2 Qg6+ 33. Kf1 Qxe8 34. f5` | [ply 55](http://localhost:5173/analysis?game_id=682302&ply=55) | [board](http://localhost:5173/analysis?fen=4N1k1/6p1/4pr1p/2qp4/4bP2/6Q1/6PP/5R1K%20b%20-%20-%200%2028) |
| 353 | missed | CLEARANCE | 10 | `10... h6 11. Bf6 Bxf6 12. exf6 Nc6 13. Qe3+ Kf8 14. Nd5 d6 15. Bb5 Be6 16. Bxc6` | [ply 19](http://localhost:5173/analysis?game_id=682318&ply=19) | [board](http://localhost:5173/analysis?fen=r1bqk2r/ppppnpbp/6p1/4P1B1/3Q4/2N5/PPP2PPP/2KR1B1R%20b%20-%20-%200%2010) |
| 354 | missed | PIN | 0 | `15... Bh6 16. dxc7 Be6 17. Nd5 Bxd2+ 18. Kxd2 Kg7 19. a4 Rac8 20. a5 h5 21. Re1` | [ply 29](http://localhost:5173/analysis?game_id=682318&ply=29) | [board](http://localhost:5173/analysis?fen=r1b2rk1/ppp2pbp/3P2p1/8/2B5/2N5/PPPR1PPP/2K4R%20b%20-%20-%200%2015) |
| 355 | allowed | PIN | 2 | `15. Qa4+ Nc6 16. Rd1 Qa5 17. Qxa5 Nxa5 18. f4 Be7 19. Nd6+ Bxd6 20. exd6 Kd7` | [ply 27](http://localhost:5173/analysis?game_id=682325&ply=27) | [board](http://localhost:5173/analysis?fen=r2qkb1r/pp3pp1/4p1np/4P3/3nN3/7P/PP2BPP1/R1BQR1K1%20w%20-%20-%200%2015) |
| 356 | allowed | PIN | 2 | `18. Qa4+ Nc6 19. Rxd8+ Rxd8 20. Qb3 Rd7 21. Nc5 Rc7 22. Nxe6 fxe6 23. Qxe6 Rf8` | [ply 33](http://localhost:5173/analysis?game_id=682325&ply=33) | [board](http://localhost:5173/analysis?fen=r2qk2r/pp2bpp1/4p2p/4n3/4N3/4B2P/PP1R1PP1/R2Q2K1%20w%20-%20-%201%2018) |
| 357 | missed | CLEARANCE | 10 | `17... Qa5 18. Rc1 Nc6 19. Nc5 Bxc5 20. Bxc5 Rd8 21. b4 Rxd2 22. Qxd2 Qd8 23. Qc3` | [ply 33](http://localhost:5173/analysis?game_id=682325&ply=33) | [board](http://localhost:5173/analysis?fen=r2qkb1r/pp3pp1/4p2p/4n3/4N3/4B2P/PP1R1PP1/R2Q2K1%20b%20-%20-%200%2017) |
| 358 | allowed | DISCOVERED_ATTACK | 1 | `7... Nxe5 8. dxe5 Qxd1+ 9. Nxd1 Ne4 10. f3 Nc5 11. f4 b6 12. Be3 Bb7 13. Nf2` | [ply 12](http://localhost:5173/analysis?game_id=682336&ply=12) | [board](http://localhost:5173/analysis?fen=r1bqk2r/pppnppbp/5np1/4N3/2PP4/2N5/PP3PPP/R1BQKB1R%20b%20-%20-%200%207) |
| 359 | missed | CLEARANCE | 6 | `9. Bf3 Ba6 10. Nc6 Qe8` | [ply 16](http://localhost:5173/analysis?game_id=682336&ply=16) | [board](http://localhost:5173/analysis?fen=r1bq1rk1/p1pnppbp/1p3np1/4N3/2PP4/2N5/PP2BPPP/R1BQK2R%20w%20-%20-%200%209) |
| 360 | missed | DISCOVERED_ATTACK | 1 | `17... Bxc3 18. Qxc3 Rxf4 19. Rxe6 Nd4 20. Qxd4 Rxd4 21. Rxd4 Qc7 22. Rxd5 Qc4 23. Rde5` | [ply 33](http://localhost:5173/analysis?game_id=682339&ply=33) | [board](http://localhost:5173/analysis?fen=2rq1rk1/1p4pp/p1n1pb2/3p4/1P3B2/P1N2Q1P/2P2PP1/3RR1K1%20b%20-%20-%200%2017) |
| 361 | missed | FORK | 6 | `18... Qf6 19. Bxe5 Qxf3 20. gxf3 Nxe5 21. Nd4 Nxf3+ 22. Nxf3 Rxf3 23. Rxe6 Rxc2 24. Re8+` | [ply 35](http://localhost:5173/analysis?game_id=682339&ply=35) | [board](http://localhost:5173/analysis?fen=2rq1rk1/1p4pp/p1n1p3/3pb3/1P3B2/P4Q1P/2P1NPP1/3RR1K1%20b%20-%20-%200%2018) |
| 362 | missed | SACRIFICE | 4 | `14. Nb5+ Kd8 15. Rad1 gxf4 16. Rd3 c4 17. Rdd1 Rf5 18. Nbd4 Rxe5 19. Nxe5 Bxe5` | [ply 26](http://localhost:5173/analysis?game_id=682341&ply=26) | [board](http://localhost:5173/analysis?fen=5rnr/ppknp1b1/4p2p/2p1P1p1/5B2/P1N2NP1/1PP2P1P/R4RK1%20w%20-%20-%200%2014) |
| 363 | missed | TRAPPED_PIECE | 4 | `26... Qa5 27. Kc1 Qc3 28. Nb1 Qxa1 29. Kd2 Qd4+ 30. Qd3 Qxf2+ 31. Qe2 Qxg1 32. Qxa6` | [ply 51](http://localhost:5173/analysis?game_id=682344&ply=51) | [board](http://localhost:5173/analysis?fen=r2q2k1/5ppp/r4p2/3n4/5B2/1P4P1/pKPNQP1P/R5R1%20b%20-%20-%200%2026) |
| 364 | missed | SKEWER | 4 | `30... Rxa2+ 31. Kb1 Ra1+ 32. Kb2 Rxg1 33. Qe4 Rd1 34. Qa4 Kh8 35. Qa7 Nb4 36. Nc4` | [ply 59](http://localhost:5173/analysis?game_id=682344&ply=59) | [board](http://localhost:5173/analysis?fen=r1q3k1/5ppp/2r2p2/8/5B2/1P3QP1/RKnN1P1P/6R1%20b%20-%20-%200%2030) |
| 365 | allowed | CLEARANCE | 6 | `14. Nxe6 fxe6 15. Bc4 Kf7 16. Rd1 Bb4 17. Rhe1 b5 18. Bb3 a5 19. Rxe6 Rxe6` | [ply 25](http://localhost:5173/analysis?game_id=682359&ply=25) | [board](http://localhost:5173/analysis?fen=rn2r1k1/pp3pp1/2pbbp1p/8/5N2/2N3P1/PPP2P1P/2K1RB1R%20w%20-%20-%201%2014) |
| 366 | allowed | SACRIFICE | 6 | `18. Bc8 a5 19. Rd1 Kg8 20. f4 Bxc3 21. Rd8+ Kf7 22. Bxb7 Ra7 23. Rxb8 Bd4` | [ply 33](http://localhost:5173/analysis?game_id=682359&ply=33) | [board](http://localhost:5173/analysis?fen=rn5k/pp4p1/2p1Bp1p/4b3/8/2N3P1/PPP2P1P/2K4R%20w%20-%20-%201%2018) |
| 367 | allowed | CLEARANCE | 4 | `4... exd4 5. Nxd4` | [ply 6](http://localhost:5173/analysis?game_id=682407&ply=6) | [board](http://localhost:5173/analysis?fen=rnbqk2r/pppp1ppp/5n2/2b1p3/3PP3/2N2N2/PPP2PPP/R1BQKB1R%20b%20-%20-%200%204) |
| 368 | allowed | CLEARANCE | 6 | `18... Nxd6 19. Rfe1 f6 20. Bd3 Ke7 21. Re3 Rad8 22. Rde1 Rg8 23. Kf1 c6 24. g3` | [ply 34](http://localhost:5173/analysis?game_id=682407&ply=34) | [board](http://localhost:5173/analysis?fen=r2k1r2/ppp2p2/3N3p/4pnp1/2B5/7P/PPP2PP1/3R1RK1%20b%20-%20-%200%2018) |
| 369 | missed | CLEARANCE | 10 | `19. Bd3 Qh6 20. Qc2 Rad8 21. Rb1 b6 22. Rb5 Kg8 23. Bd2 Rd6 24. Rc1 a6` | [ply 36](http://localhost:5173/analysis?game_id=682409&ply=36) | [board](http://localhost:5173/analysis?fen=r3rk2/ppp1nppB/2n2q2/2Q5/3P4/P3P3/5PPP/R1B2RK1%20w%20-%20-%200%2019) |
| 370 | missed | CLEARANCE | 10 | `14... Qxc2 15. Rc1 Qg6 16. Na4 Bd6 17. Rxc6 Ne7 18. Rc1` | [ply 27](http://localhost:5173/analysis?game_id=682411&ply=27) | [board](http://localhost:5173/analysis?fen=r3k1nr/5ppp/p1p1p1q1/3p4/1b1P2P1/2N4P/PPPBQP2/R3K2R%20b%20-%20-%200%2014) |
| 371 | missed | FORK | 0 | `21... Ng3 22. Qh2 Nxh1 23. Nc5 Rbd8 24. h4 e5 25. dxe5 Qe7 26. Rc3 Nf2 27. Qxf2` | [ply 41](http://localhost:5173/analysis?game_id=682411&ply=41) | [board](http://localhost:5173/analysis?fen=1r3rk1/5ppp/p1p1pq2/3p4/N2Pn1P1/P2R1P1P/1PP1Q3/1K5R%20b%20-%20-%200%2021) |
| 372 | missed | FORK | 2 | `21. Qa5+ Kb8 22. Nxc6+ Bxc6 23. dxc6 Be5 24. Rxe5 Qa7 25. Qb4+ Kc8 26. Nb6+ Kb8` | [ply 40](http://localhost:5173/analysis?game_id=682422&ply=40) | [board](http://localhost:5173/analysis?fen=3r3r/1bk1qpbp/p1p5/2RPNp2/N3P3/2Q5/PP3PPP/5RK1%20w%20-%20-%200%2021) |
| 373 | allowed | CLEARANCE | 2 | `22... Kb8 23. Rcc1 Bc7 24. Qc3 cxd5 25. Nc5 Bb6 26. Nxb7 Qxb7 27. exd5 Rhe8 28. Qf6` | [ply 42](http://localhost:5173/analysis?game_id=682422&ply=42) | [board](http://localhost:5173/analysis?fen=3r3r/1bk1qp1p/p1p5/Q1RPbp2/N3P3/8/PP3PPP/3R2K1%20b%20-%20-%201%2022) |
| 374 | missed | DOUBLE_CHECK | 6 | `23. Rdc1 Bf4 24. dxc6 Bxc1 25. Rxc1 Qd6 26. cxb7+ Kxb7 27. h4 Rc8 28. Nc5+ Ka7` | [ply 44](http://localhost:5173/analysis?game_id=682422&ply=44) | [board](http://localhost:5173/analysis?fen=2kr3r/1b2qp1p/p1p5/Q1RPbp2/N3P3/8/PP3PPP/3R2K1%20w%20-%20-%200%2023) |
| 375 | allowed | CLEARANCE | 10 | `7... dxe4 8. Ne5` | [ply 12](http://localhost:5173/analysis?game_id=682429&ply=12) | [board](http://localhost:5173/analysis?fen=r1bqk2r/ppp1bppp/2n2n2/3p2B1/3PP3/2N2N2/PP3PPP/R2QKB1R%20b%20-%20-%200%207) |
| 376 | missed | CLEARANCE | 2 | `7. e3` | [ply 12](http://localhost:5173/analysis?game_id=682429&ply=12) | [board](http://localhost:5173/analysis?fen=r1bqk2r/ppp1bppp/2n2n2/3p2B1/3P4/2N2N2/PP2PPPP/R2QKB1R%20w%20-%20-%200%207) |
| 377 | allowed | SACRIFICE | 2 | `26. Rb7 fxg3 27. Qxg3 Qxg3+ 28. Kxg3 Rf7 29. Rxf7 Kxf7 30. c4 Nb6 31. Rc5 Rc8` | [ply 49](http://localhost:5173/analysis?game_id=682437&ply=49) | [board](http://localhost:5173/analysis?fen=r4rk1/p5p1/2p4p/3nR3/3P1pq1/3Q2N1/P1P2PK1/1R6%20w%20-%20-%200%2026) |
| 378 | missed | CLEARANCE | 6 | `9... Ne7 10. Bd3 Rc8 11. Qg4 Ng6 12. f4 Bc5+ 13. Kh1` | [ply 17](http://localhost:5173/analysis?game_id=682439&ply=17) | [board](http://localhost:5173/analysis?fen=r2qkbnr/pp1b1ppp/4p3/1B1pP3/3Q4/2N5/PPP2PPP/R1B2RK1%20b%20-%20-%200%209) |
| 379 | allowed | PIN | 0 | `19. Ne4 b6 20. Nf6+ Rxf6 21. exf6 Rxg3+ 22. Kh2 Rf3 23. Re2 Rf4 24. b3 Rxf6` | [ply 35](http://localhost:5173/analysis?game_id=682439&ply=35) | [board](http://localhost:5173/analysis?fen=6r1/1p1k1p1p/p3p2p/2bpPr2/P7/2N3PP/1PP2P2/3RR1K1%20w%20-%20-%201%2019) |
| 380 | allowed | PIN | 0 | `20. Ne4 Kc6` | [ply 37](http://localhost:5173/analysis?game_id=682439&ply=37) | [board](http://localhost:5173/analysis?fen=6r1/1p1k3p/p3pp1p/2bpPr2/P7/2N3PP/1PPR1P2/4R1K1%20w%20-%20-%200%2020) |
| 381 | missed | PIN | 0 | `21... Rxg3+ 22. Kh2` | [ply 41](http://localhost:5173/analysis?game_id=682439&ply=41) | [board](http://localhost:5173/analysis?fen=6r1/1p1k3p/p3pr1p/P1bp4/8/2N3PP/1PPR1P2/4R1K1%20b%20-%20-%200%2021) |
| 382 | allowed | PIN | 0 | `13... Nxd4 14. Qd1 Nf5 15. Bxf6 Qxf6 16. Rb1 dxc4 17. Be2 Qc3+ 18. Qd2 Qxa3 19. Bxc4` | [ply 24](http://localhost:5173/analysis?game_id=682445&ply=24) | [board](http://localhost:5173/analysis?fen=r4rk1/ppp1qpp1/2n2n1p/3p4/2PP3B/P3PQ1P/5PP1/R3KB1R%20b%20-%20-%200%2013) |
| 383 | missed | CAPTURING_DEFENDER | 2 | `13. Bxf6 Qxf6 14. Qxd5 Qg6 15. Be2 Rfd8 16. Qf3 Na5` | [ply 24](http://localhost:5173/analysis?game_id=682445&ply=24) | [board](http://localhost:5173/analysis?fen=r4rk1/ppp1qpp1/2n2n1p/3p4/3P3B/P1P1PQ1P/5PP1/R3KB1R%20w%20-%20-%200%2013) |
| 384 | allowed | PIN | 0 | `14... Nxd4 15. Qd1 Nf5 16. Bxf6 Qxf6` | [ply 26](http://localhost:5173/analysis?game_id=682445&ply=26) | [board](http://localhost:5173/analysis?fen=r4rk1/ppp1qpp1/2n2n1p/8/2BP3B/P3PQ1P/5PP1/R3K2R%20b%20-%20-%200%2014) |
| 385 | allowed | FORK | 0 | `16... Ne5 17. Qe2 g5 18. Bg3 Ne4 19. Bxe5 Qxe5 20. Qc2 b5 21. Bb3 Re7 22. Rad1` | [ply 30](http://localhost:5173/analysis?game_id=682445&ply=30) | [board](http://localhost:5173/analysis?fen=4rrk1/1pp1qpp1/p1n2n1p/3P4/2B4B/P3PQ1P/5PP1/R4RK1%20b%20-%20-%200%2016) |
| 386 | missed | CLEARANCE | 4 | `16. Rfc1 Nd8 17. Bd3 c6 18. Rc5 Ne6 19. Re5 Rd8 20. Qf5 Rfe8 21. Rb1 Rd7` | [ply 30](http://localhost:5173/analysis?game_id=682445&ply=30) | [board](http://localhost:5173/analysis?fen=4rrk1/1pp1qpp1/p1n2n1p/8/2BP3B/P3PQ1P/5PP1/R4RK1%20w%20-%20-%200%2016) |
| 387 | missed | CLEARANCE | 2 | `18. Rf2 Qc5 19. Qf4 a5 20. Bf1 Qb6 21. e5 b4 22. Qf6 b3 23. axb3 Rae8` | [ply 34](http://localhost:5173/analysis?game_id=682458&ply=34) | [board](http://localhost:5173/analysis?fen=r4rk1/p4p1p/3p2p1/1p1P4/4PRQ1/2qB4/P5PP/3R2K1%20w%20-%20-%200%2018) |
| 388 | allowed | DISCOVERED_ATTACK | 5 | `16. dxc5 Nd5 17. Qb2 Be4 18. Nh4 f5 19. Bxe4 fxe4 20. c4 Bxh4 21. Rxd5 Qf6` | [ply 29](http://localhost:5173/analysis?game_id=682460&ply=29) | [board](http://localhost:5173/analysis?fen=2rqr1k1/pp2bppp/1n3p2/2p2b2/3P4/1PP1BNPP/P3QPB1/3R1RK1%20w%20-%20-%201%2016) |
| 389 | missed | PIN | 10 | `27... Rxd4 28. bxc5 Rxd3 29. cxb6 axb6 30. h4 Rxc3 31. Qd7 Ra8 32. e5 Rxg3 33. e6` | [ply 53](http://localhost:5173/analysis?game_id=682460&ply=53) | [board](http://localhost:5173/analysis?fen=4r1k1/pp1r1pp1/1n3pp1/2q5/1P1RP1Q1/2PR2PP/P5B1/6K1%20b%20-%20-%200%2027) |
| 390 | missed | CLEARANCE | 2 | `11. d5 Bd7 12. Qd4 Rg8 13. Bg5 Be7 14. Bxe7 Qxe7 15. c4 g5 16. Ne5 g4` | [ply 20](http://localhost:5173/analysis?game_id=682463&ply=20) | [board](http://localhost:5173/analysis?fen=r2qkb1r/1pp2p1p/p1b1p1p1/8/3PP3/2P2N2/P4PPP/R1BQ1RK1%20w%20-%20-%200%2011) |
| 391 | missed | PIN | 4 | `13. Ne5 Bd6 14. Nxc6 bxc6 15. Qa4 Kd7 16. c4 Rab8 17. Ba3 Bxa3 18. Qxa3 Rb6` | [ply 24](http://localhost:5173/analysis?game_id=682463&ply=24) | [board](http://localhost:5173/analysis?fen=r3kb1r/1pp4p/p1b1pqp1/8/3P4/2P2N2/P4PPP/R1BQ1RK1%20w%20-%20-%200%2013) |
| 392 | missed | PIN | 6 | `23. cxd5 cxd5 24. Qxd5+ Qd6 25. Qe4 Rhf8 26. Red1 Rf6 27. Rxd6+ Rxd6 28. h4 Re8` | [ply 44](http://localhost:5173/analysis?game_id=682463&ply=44) | [board](http://localhost:5173/analysis?fen=3r3r/2pk3p/p1p3p1/3p4/2P2q2/1Q6/P4PPP/1R2R1K1%20w%20-%20-%200%2023) |
| 393 | missed | CLEARANCE | 10 | `23. Qxf6 Be5 24. Qf7 Qd6 25. Bg5 Kd7 26. Rhf1 Rae8 27. Rf3 Kc7 28. Rdf1 Kb8` | [ply 44](http://localhost:5173/analysis?game_id=682465&ply=44) | [board](http://localhost:5173/analysis?fen=r2k3r/ppq1nQ2/3b1ppB/2pB4/2PpP1P1/7P/PP6/2KR3R%20w%20-%20-%200%2023) |
| 394 | allowed | CLEARANCE | 8 | `29... Kc7 30. Qg7+ Kb6 31. Rde1 Qb8 32. Qxg6 Qg3 33. h4 Rf8 34. h5 a5 35. h6` | [ply 56](http://localhost:5173/analysis?game_id=682465&ply=56) | [board](http://localhost:5173/analysis?fen=r2kq3/pp6/2n2Qp1/2p5/2Pp2P1/7P/PP6/K2R3R%20b%20-%20-%200%2029) |
| 395 | missed | SKEWER | 4 | `29. Rhe1 Qd7 30. Qh8+ Kc7 31. Qxa8 Qd6 32. Qg8 Qh2 33. Qg7+ Kb6 34. Qxf6 Ka5` | [ply 56](http://localhost:5173/analysis?game_id=682465&ply=56) | [board](http://localhost:5173/analysis?fen=r2kq3/pp4Q1/2n2pp1/2p5/2Pp2P1/7P/PP6/K2R3R%20w%20-%20-%200%2029) |
| 396 | allowed | CLEARANCE | 4 | `13... Nxe5 14. dxe5 c6 15. Nd2 Qa5 16. cxd5 cxd5 17. Bd3 Rad8 18. Qe2 Rfe8 19. Bxe4` | [ply 24](http://localhost:5173/analysis?game_id=682478&ply=24) | [board](http://localhost:5173/analysis?fen=r2q1rk1/ppp2p2/2n4p/3pBbp1/2PPn3/P3PN2/5PPP/R2QKB1R%20b%20-%20-%200%2013) |
| 397 | missed | DISCOVERED_ATTACK | 5 | `18. Nd4 Bh7 19. f3 Nc5 20. Bxf7+ Rxf7 21. Rxc5 Re7 22. e6 b6 23. Rc6 Bg6` | [ply 34](http://localhost:5173/analysis?game_id=682478&ply=34) | [board](http://localhost:5173/analysis?fen=r4rk1/ppp2p2/7p/4Pbp1/2B1n3/P3PN2/5PPP/2R1K2R%20w%20-%20-%200%2018) |
| 398 | missed | HANGING_PIECE | 0 | `28. Rxc6 Rfc8` | [ply 54](http://localhost:5173/analysis?game_id=682478&ply=54) | [board](http://localhost:5173/analysis?fen=r4rk1/5p2/p1b4p/1p2P1p1/1R6/Pp2P3/5KPP/2R5%20w%20-%20-%200%2028) |
| 399 | missed | PIN | 2 | `7. Bxd5 Qd7 8. Bxc6 Qxc6 9. Qf3 Qxf3 10. Nxf3 e6 11. a3 Bg4 12. Ng5 c5` | [ply 12](http://localhost:5173/analysis?game_id=682481&ply=12) | [board](http://localhost:5173/analysis?fen=r2qkb1r/ppp1pppp/2n5/3nPb2/2BP4/2N5/PP3PPP/R1BQK1NR%20w%20-%20-%200%207) |
| 400 | allowed | CLEARANCE | 10 | `14... N6d4 15. Nxd4 Nxd4 16. Qd1 Nc6 17. Ra1` | [ply 26](http://localhost:5173/analysis?game_id=682481&ply=26) | [board](http://localhost:5173/analysis?fen=r2qk2r/ppp2ppp/2n5/3NPb2/2B5/5Q2/1Pn1NPPP/1RB2RK1%20b%20-%20-%201%2014) |
| 401 | missed | SACRIFICE | 2 | `14. Qxf5 Nxa1 15. Bg5` | [ply 26](http://localhost:5173/analysis?game_id=682481&ply=26) | [board](http://localhost:5173/analysis?fen=r2qk2r/ppp2ppp/2n5/3NPb2/2B5/5Q2/1Pn1NPPP/R1B2RK1%20w%20-%20-%200%2014) |
| 402 | missed | INTERMEZZO | 10 | `11... b5 12. Bd3 b4 13. Na4 Nbd7 14. Kh1 c5 15. dxc5 Qa5 16. b3 Nxc5 17. Nxc5` | [ply 21](http://localhost:5173/analysis?game_id=682527&ply=21) | [board](http://localhost:5173/analysis?fen=rn1q1rk1/pp2bppp/2p1pnb1/8/2BPP3/2N2N2/PPP1Q1PP/R1B2RK1%20b%20-%20-%200%2011) |
| 403 | allowed | DEFLECTION | 8 | `20. Nf3 Qb5+ 21. Rd3 f6 22. Qd4 c5 23. a4 Qxa4 24. bxc5 Qc6 25. c4 e5` | [ply 37](http://localhost:5173/analysis?game_id=682530&ply=37) | [board](http://localhost:5173/analysis?fen=2k1r1r1/pppq1pp1/n3p1p1/3pQ1N1/1P6/2P1P3/P3KPPP/3R3R%20w%20-%20-%201%2020) |
| 404 | missed | CLEARANCE | 8 | `9. Bg5 Be7 10. Bxf6 Bxf6 11. a4 Be7 12. Qd3` | [ply 16](http://localhost:5173/analysis?game_id=682532&ply=16) | [board](http://localhost:5173/analysis?fen=r2qkb1r/pp3ppp/2bp1n2/1B2p3/4P3/2N5/PPP2PPP/R1BQ1RK1%20w%20-%20-%200%209) |
| 405 | missed | CLEARANCE | 2 | `10. Qd3` | [ply 18](http://localhost:5173/analysis?game_id=682532&ply=18) | [board](http://localhost:5173/analysis?fen=r2qk2r/pp2bppp/2bp1n2/4p3/2B1P3/2N5/PPP2PPP/R1BQ1RK1%20w%20-%20-%200%2010) |
| 406 | allowed | CLEARANCE | 2 | `13... exf4 14. c3 Be5 15. Nxf4 Bxe4 16. Bd5 Bxf4 17. Rxf4 Bxd5 18. Qxd5 Qb6+ 19. Rf2` | [ply 24](http://localhost:5173/analysis?game_id=682532&ply=24) | [board](http://localhost:5173/analysis?fen=r2q1rk1/1p3ppp/p1bp1b2/3Np3/2B1PP2/8/PPP3PP/R2Q1RK1%20b%20-%20-%200%2013) |
| 407 | missed | CLEARANCE | 10 | `13. a4 b5 14. Bb3 a5 15. axb5 Bxb5 16. Re1 Bg5 17. Nc3 Bc6 18. Bd5 Qd7` | [ply 24](http://localhost:5173/analysis?game_id=682532&ply=24) | [board](http://localhost:5173/analysis?fen=r2q1rk1/1p3ppp/p1bp1b2/3Np3/2B1P3/8/PPP2PPP/R2Q1RK1%20w%20-%20-%200%2013) |
| 408 | missed | CLEARANCE | 6 | `18. g3 a5 19. a3 Kh8 20. Qd3 Rab8 21. Rbf1 f6 22. Ne7 Bd7 23. Nf5 Rfd8` | [ply 34](http://localhost:5173/analysis?game_id=682532&ply=34) | [board](http://localhost:5173/analysis?fen=r4rk1/5ppp/p1bp4/1p1Nb1q1/4P3/1B6/P1P2RPP/1R1Q2K1%20w%20-%20-%200%2018) |
| 409 | allowed | PIN | 0 | `19... Bd4 20. Kh1 Bxf2 21. Qxf2 Bxd5 22. Bxd5 Rab8 23. h3 Qe7 24. Qd4 f6 25. Qd2` | [ply 36](http://localhost:5173/analysis?game_id=682532&ply=36) | [board](http://localhost:5173/analysis?fen=r4r1k/5ppp/p1bp4/1p1Nb1q1/4P3/1B3Q2/P1P2RPP/5RK1%20b%20-%20-%201%2019) |
| 410 | missed | CLEARANCE | 8 | `19. Rd1 Rac8 20. Qh3 Qd8 21. Qe3 a5 22. a3 a4 23. Ba2 g6 24. Nb6 Rb8` | [ply 36](http://localhost:5173/analysis?game_id=682532&ply=36) | [board](http://localhost:5173/analysis?fen=r4r1k/5ppp/p1bp4/1p1Nb1q1/4P3/1B3Q2/P1P2RPP/1R4K1%20w%20-%20-%200%2019) |
| 411 | allowed | PIN | 2 | `21... Bxf5 22. exf5 Bd4 23. Be6 Qd2 24. c3 Bxf2+ 25. Rxf2 Qe1+ 26. Rf1 Qe5 27. Rd1` | [ply 40](http://localhost:5173/analysis?game_id=682532&ply=40) | [board](http://localhost:5173/analysis?fen=r4r1k/3b2pp/p2p1p2/1p2bNq1/4P3/1B3Q2/P1P2RPP/5RK1%20b%20-%20-%201%2021) |
| 412 | missed | CLEARANCE | 4 | `21. Qd3 a5 22. a3 g6 23. Ba2 Rae8 24. Nd5 Rc8 25. c3 a4 26. Kh1 Qh6` | [ply 40](http://localhost:5173/analysis?game_id=682532&ply=40) | [board](http://localhost:5173/analysis?fen=r4r1k/3bN1pp/p2p1p2/1p2b1q1/4P3/1B3Q2/P1P2RPP/5RK1%20w%20-%20-%200%2021) |
| 413 | missed | SACRIFICE | 10 | `30. Rg1 Qe4 31. h3 Qxf5 32. c4 bxc4 33. Bxc4 d5 34. Bxd5 Qxd5 35. a4 Qd2` | [ply 58](http://localhost:5173/analysis?game_id=682532&ply=58) | [board](http://localhost:5173/analysis?fen=r3r2k/6pp/3p1p2/1p3P2/8/1B6/P1P3PP/4qR1K%20w%20-%20-%200%2030) |
| 414 | missed | EN_PASSANT | 4 | `19. Qh4 Kb8 20. Bc1 e5 21. dxe6 fxe6 22. Bc4 d5 23. exd5 exd5 24. Bd3 c4+` | [ply 36](http://localhost:5173/analysis?game_id=682533&ply=36) | [board](http://localhost:5173/analysis?fen=2kr3r/1p1npp2/1q1p1npb/pNpP3p/P3PP2/1P1BB1QP/2P3P1/4RRK1%20w%20-%20-%200%2019) |
| 415 | missed | DISCOVERED_CHECK | 0 | `24. Nxf7+` | [ply 46](http://localhost:5173/analysis?game_id=682533&ply=46) | [board](http://localhost:5173/analysis?fen=1k1r3r/1p1n1p2/1q1N2p1/p1pn1P1p/P7/1P1B2QP/2Pb2P1/4RR1K%20w%20-%20-%200%2024) |
| 416 | allowed | SACRIFICE | 2 | `26... Rxd5 27. exd5 Nd4 28. Bxd4 exd4 29. Rc5 Rxa3 30. Rxb5+ Kc8 31. d6 Ra2+ 32. Kg1` | [ply 50](http://localhost:5173/analysis?game_id=682535&ply=50) | [board](http://localhost:5173/analysis?fen=3b4/1kp5/r1nr3p/1p1Bp1p1/1P2P3/P3BP2/2R3KP/2R5%20b%20-%20-%201%2026) |
| 417 | missed | PIN | 4 | `26. Rxc6 Raxc6 27. Rxc6 Rxc6 28. Bc5 g4 29. a4 bxa4 30. b5 gxf3 31. Kf2 Bf6` | [ply 50](http://localhost:5173/analysis?game_id=682535&ply=50) | [board](http://localhost:5173/analysis?fen=3b4/1kp5/r1nr3p/1p1Bp1p1/1P2P3/P3BP2/2R4P/2R3K1%20w%20-%20-%200%2026) |
| 418 | missed | PIN | 4 | `30. Bc5 Rd8 31. Bg1 Rd6 32. a4 Rxa4 33. Rxc6 Rxc6 34. Rxc6 Kc8 35. Rxf6 Rxb4` | [ply 58](http://localhost:5173/analysis?game_id=682535&ply=58) | [board](http://localhost:5173/analysis?fen=8/1kp5/r1nr1b2/1p1Bp1p1/1P2P2p/P3BP1P/2R3K1/2R5%20w%20-%20-%200%2030) |
| 419 | allowed | FORK | 4 | `18. Rxc2 Rxa7 19. Rxc8+ Nf8 20. Nc6 Qb7 21. Nbxa7 g5 22. Nb5 Qa6 23. a3 Kg7` | [ply 33](http://localhost:5173/analysis?game_id=682559&ply=33) | [board](http://localhost:5173/analysis?fen=r1r3k1/Q2nqppp/4pn2/1N1pN3/3P4/8/PPb1BPPP/2R2RK1%20w%20-%20-%201%2018) |
| 420 | missed | SACRIFICE | 4 | `25... Kf8 26. Nc6 Qd6 27. Nxb8 Nxb8 28. Bb5 g6 29. a4 d4 30. a5 e5 31. Bd3` | [ply 49](http://localhost:5173/analysis?game_id=682559&ply=49) | [board](http://localhost:5173/analysis?fen=1r4k1/4Nppp/n3p3/3pq3/8/3B4/PPR2PPP/5RK1%20b%20-%20-%200%2025) |
| 421 | allowed | CLEARANCE | 2 | `7... e6 8. Re1 Bd6 9. d4 c6 10. Bb3 Nf6 11. d5 cxd5 12. Nxd5 Nxd5 13. Qxd5` | [ply 12](http://localhost:5173/analysis?game_id=682565&ply=12) | [board](http://localhost:5173/analysis?fen=rn1qkbnr/1pp1ppp1/p6p/5b2/2B5/2NP1N2/PPP2PPP/R1BQ1RK1%20b%20-%20-%200%207) |
| 422 | missed | CLEARANCE | 2 | `7. Ne5 e6 8. Qf3 Ne7 9. Qxb7 Nd7 10. Nxd7 Kxd7 11. Bxa6 Qb8 12. Bb5+ Kd8` | [ply 12](http://localhost:5173/analysis?game_id=682565&ply=12) | [board](http://localhost:5173/analysis?fen=rn1qkbnr/1pp1ppp1/p6p/5b2/2B5/2N2N2/PPPP1PPP/R1BQ1RK1%20w%20-%20-%200%207) |
| 423 | allowed | CLEARANCE | 2 | `7... d5 8. exd5 Bf5 9. Qb5+ Bd7 10. Qe2+ Qe7 11. Qxe7+ Nxe7 12. Na3 Nexd5 13. Nf3` | [ply 12](http://localhost:5173/analysis?game_id=682568&ply=12) | [board](http://localhost:5173/analysis?fen=r1bqkbnr/pp1p1ppp/8/8/1nQ1P3/8/PP3PPP/RNB1KBNR%20b%20-%20-%201%207) |
| 424 | missed | CLEARANCE | 8 | `13. Kd1 Be7 14. Kxc2` | [ply 24](http://localhost:5173/analysis?game_id=682568&ply=24) | [board](http://localhost:5173/analysis?fen=r2qkb1r/pb1n1ppp/1p6/1B1pP3/5Q2/2N2N2/PPn2PPP/R1B1K2R%20w%20-%20-%200%2013) |
| 425 | allowed | SACRIFICE | 2 | `16... Bg7 17. Rxa1 Rc8 18. Kf1 a6 19. Bxb6 Rf8 20. Qe3 Qe7 21. Bxd7+ Qxd7 22. Rd1` | [ply 30](http://localhost:5173/analysis?game_id=682568&ply=30) | [board](http://localhost:5173/analysis?fen=r2qkb1r/pb1n3p/1p2p1p1/1B1p4/5Q2/2N1BN2/PP2KPPP/n6R%20b%20-%20-%201%2016) |
| 426 | missed | FORK | 8 | `16. Ne5 Qe7 17. Bxd7+ Qxd7 18. Nxd7 Kxd7 19. Ke2 Nc2 20. Qa4+ b5 21. Qxc2 Rc8` | [ply 30](http://localhost:5173/analysis?game_id=682568&ply=30) | [board](http://localhost:5173/analysis?fen=r2qkb1r/pb1n3p/1p2p1p1/1B1p4/5Q2/2N1BN2/PP3PPP/n4K1R%20w%20-%20-%200%2016) |
| 427 | allowed | PIN | 0 | `22... Rde8 23. Bxg7+ Kxg7 24. Nd4 Bc8 25. f3 Bxe6 26. Kf2 g5 27. Rc1 Bd7 28. h3` | [ply 42](http://localhost:5173/analysis?game_id=682568&ply=42) | [board](http://localhost:5173/analysis?fen=3r1r1k/pb4bp/1p2B1p1/3p4/3B4/2N2N2/PP2KPPP/R7%20b%20-%20-%201%2022) |
| 428 | allowed | SACRIFICE | 6 | `24... Rf4 25. Rd1 Ba6+ 26. Kg1 Rxd4 27. Rxd4 Re8 28. f3 Rxe6 29. Rxd5 Re7 30. Kf2` | [ply 46](http://localhost:5173/analysis?game_id=682568&ply=46) | [board](http://localhost:5173/analysis?fen=3r1r2/pb4kp/1p2B1p1/3p4/3N4/2N5/PP3PPP/R4K2%20b%20-%20-%201%2024) |
| 429 | allowed | PIN | 0 | `31... Bxf3 32. g5 Rxe2+ 33. Kf1 d3 34. Bd7 d2 35. Ba4 Rxh2 36. Kg1 Rg2+ 37. Kf1` | [ply 60](http://localhost:5173/analysis?game_id=682568&ply=60) | [board](http://localhost:5173/analysis?fen=8/pb4kp/1p4p1/8/3p2P1/4rP1B/PP2N2P/4K3%20b%20-%20-%200%2031) |
| 430 | allowed | HANGING_PIECE | 0 | `26. Qxb4 a5 27. Qd6 Rc6 28. Qxc6 Qxc6 29. Rxc3 Qa6 30. Kd2 a4 31. Bc2 Qa5` | [ply 49](http://localhost:5173/analysis?game_id=682578&ply=49) | [board](http://localhost:5173/analysis?fen=2r2rk1/5ppp/pq2p3/1p1pP3/1b4Q1/1BnKPN1P/P5P1/2R4R%20w%20-%20-%200%2026) |
| 431 | missed | FORK | 2 | `25... Ne4 26. Qf4 Nf2+ 27. Ke2 Nxh1 28. Rxh1 Qc7 29. Nd4 Bxb4 30. Bc2 h6 31. g4` | [ply 49](http://localhost:5173/analysis?game_id=682578&ply=49) | [board](http://localhost:5173/analysis?fen=2r2rk1/4bppp/pq2p3/1p1pP3/1P4Q1/1BnKPN1P/P5P1/2R4R%20b%20-%20-%200%2025) |
| 432 | allowed | HANGING_PIECE | 0 | `18... Nxe5 19. Nc4 Nxc4 20. Rxc4 b5 21. Rc6 Ba3 22. e5 Re8 23. f4 a5 24. Kf1` | [ply 34](http://localhost:5173/analysis?game_id=682595&ply=34) | [board](http://localhost:5173/analysis?fen=2k2b1r/p1p3pp/1pn5/4B3/4P3/N7/P4PPP/2RR2K1%20b%20-%20-%201%2018) |
| 433 | allowed | CLEARANCE | 8 | `50. Kc5 Rxg4 51. Kd6 Kf4 52. e6 Rg5 53. e7 Re5 54. Be6 Rxe4 55. e8=Q Kg5` | [ply 97](http://localhost:5173/analysis?game_id=682602&ply=97) | [board](http://localhost:5173/analysis?fen=8/8/1K4p1/3BP1k1/4P1P1/6r1/8/8%20w%20-%20-%201%2050) |
| 434 | allowed | PROMOTION | 2 | `51. e7 Rg3 52. e8=Q Rd3 53. Qe7+ Kh6 54. Qf8+ Kg5 55. Qc5 Kf4 56. Qd6+ Ke3` | [ply 99](http://localhost:5173/analysis?game_id=682602&ply=99) | [board](http://localhost:5173/analysis?fen=8/8/1K2P1p1/3B2k1/4P1r1/8/8/8%20w%20-%20-%200%2051) |
| 435 | allowed | HANGING_PIECE | 0 | `54. Bxb3 Kg5 55. e5 Kf4 56. e6 g5 57. e7 g4 58. Qh5 Kg3 59. e8=Q Kf3` | [ply 105](http://localhost:5173/analysis?game_id=682602&ply=105) | [board](http://localhost:5173/analysis?fen=4Q3/8/6p1/2KB4/4P2k/1r6/8/8%20w%20-%20-%201%2054) |
| 436 | allowed | SACRIFICE | 6 | `e8c8 c1g5 f8b4 e1f1 b4c5 g5d8 h8d8 d1c2 c5d4 a1e1 d4e5 c2e4` | [ply 20](http://localhost:5173/analysis?game_id=682653&ply=20) | [board](http://localhost:5173/analysis?fen=r3kb1r/pppq1ppp/8/4P3/3Np3/8/PP3PPP/R1BQK2R%20b%20-%20-%200%2011) |
| 437 | allowed | CLEARANCE | 4 | `15... Qxd1+ 16. Ne1 Qa4 17. g3 Rd1 18. Kg2 Rxc1 19. Bxc1 Qc6 20. Nc2 e3+ 21. f3` | [ply 28](http://localhost:5173/analysis?game_id=682653&ply=28) | [board](http://localhost:5173/analysis?fen=2kr3r/pp1q1ppp/8/2p1P3/1b2p3/4B3/PPN2PPP/2RQ1K1R%20b%20-%20-%201%2015) |
| 438 | missed | PIN | 0 | `15. Qe2 Kb8 16. Nb5 Rhe8 17. h4 c4 18. Nd6 Rxe5 19. Nxc4 Rd5 20. g3 b5` | [ply 28](http://localhost:5173/analysis?game_id=682653&ply=28) | [board](http://localhost:5173/analysis?fen=2kr3r/pp1q1ppp/8/2p1P3/1b1Np3/4B3/PP3PPP/2RQ1K1R%20w%20-%20-%200%2015) |
| 439 | missed | PIN | 2 | `16. Qe2 Ba5 17. Nd4 Qxe5 18. Nb3 Bb6 19. Nxc5 Kb8 20. g3 Qf5 21. Kg2 Rd5` | [ply 30](http://localhost:5173/analysis?game_id=682653&ply=30) | [board](http://localhost:5173/analysis?fen=2kr3r/pp3ppp/8/2p1Pq2/1b2p3/4B3/PPN2PPP/2RQ1K1R%20w%20-%20-%200%2016) |
| 440 | missed | SACRIFICE | 10 | `29. Rd6+ Kb5 30. Be5 Qa2 31. Rd5+ Ka6 32. Rd1 b2 33. Bxb2 Qxb2 34. h3 Kb5` | [ply 56](http://localhost:5173/analysis?game_id=682653&ply=56) | [board](http://localhost:5173/analysis?fen=8/p2R1ppp/qpk5/8/4pB2/1p6/5PPP/6K1%20w%20-%20-%200%2029) |
| 441 | missed | CLEARANCE | 10 | `12. Nxg5 hxg5 13. Qe1 Bh5 14. Rf5 Bg6 15. Bxg5 Qe8 16. Qh4 Nd7 17. Re1 Qe6` | [ply 22](http://localhost:5173/analysis?game_id=682677&ply=22) | [board](http://localhost:5173/analysis?fen=rn1q1rk1/pp3pp1/2p4p/3pP1b1/3P2b1/2PB1N2/P1PQ2PP/R1B2RK1%20w%20-%20-%200%2012) |
| 442 | missed | CLEARANCE | 8 | `16. Nxf5 Bxf5 17. Qxg5 hxg5 18. Bxf5 Re8 19. Rf3 Re7 20. Rcf1 Nd7 21. Rg3 Nf8` | [ply 30](http://localhost:5173/analysis?game_id=682677&ply=30) | [board](http://localhost:5173/analysis?fen=rn3rk1/pp4p1/2p4p/3pPpq1/3P2bN/2PB2Q1/P1P3PP/2R2RK1%20w%20-%20-%200%2016) |
| 443 | missed | CLEARANCE | 6 | `17. Ng6 Nd7 18. h4 Qh5 19. Ne7+ Kh8 20. Bg6 Rae8 21. Bxh5 Bxh5 22. Qd2 f3` | [ply 32](http://localhost:5173/analysis?game_id=682677&ply=32) | [board](http://localhost:5173/analysis?fen=rn3rk1/pp4p1/2p4p/3pP1q1/3P1pbN/2PB4/P1P2QPP/2R2RK1%20w%20-%20-%200%2017) |
| 444 | allowed | HANGING_PIECE | 0 | `13... Bxc5 14. Nf2 Bb4+ 15. Bd2 Bxd2+ 16. Qxd2 Qf5 17. Ne4 Kf7` | [ply 24](http://localhost:5173/analysis?game_id=682681&ply=24) | [board](http://localhost:5173/analysis?fen=r3kbnr/pppq4/2n2Pp1/2N1p1Pp/3p4/3P1P1N/PPP1Q2P/R1B1K2R%20b%20-%20-%201%2013) |
| 445 | allowed | DEFLECTION | 6 | `14... Qh4+ 15. Kd1 Bxc5 16. b4 Bxb4 17. Bxb4 Qxg5 18. f7+ Kxf7 19. Bd2 Qf5 20. Rg1` | [ply 26](http://localhost:5173/analysis?game_id=682681&ply=26) | [board](http://localhost:5173/analysis?fen=r3kbnr/ppp5/2n2Pp1/2N1p1Pp/3p4/3P1P1q/PPPBQ2P/R3K2R%20b%20-%20-%201%2014) |
| 446 | allowed | HANGING_PIECE | 0 | `18... Rxd5 19. Rxe2` | [ply 34](http://localhost:5173/analysis?game_id=682688&ply=34) | [board](http://localhost:5173/analysis?fen=r5k1/ppp2ppp/8/2bB3r/2N4N/3P4/PPPBn2P/1K2R3%20b%20-%20-%201%2018) |
| 447 | allowed | FORK | 2 | `19... Rxd5 20. Bxc7 Bf2 21. Re4 f5 22. Rf4 Bxh4 23. Rxh4 b5 24. Nd2 Re8 25. b4` | [ply 36](http://localhost:5173/analysis?game_id=682688&ply=36) | [board](http://localhost:5173/analysis?fen=r5k1/ppp2ppp/8/2bB3r/2N2B1N/3P4/PPP4P/1K2R3%20b%20-%20-%200%2019) |
| 448 | missed | CLEARANCE | 2 | `17. f4 Be7 18. Rf2 a6 19. a4 b4 20. Nc4 Qg6 21. Qe2 gxf4 22. Bxf4 Rc8` | [ply 32](http://localhost:5173/analysis?game_id=682690&ply=32) | [board](http://localhost:5173/analysis?fen=r3kbr1/pb3p2/4pq1p/1p2N1pQ/3pP3/3P4/PPPB1PPP/R4RK1%20w%20-%20-%200%2017) |
| 449 | allowed | TRAPPED_PIECE | 2 | `14. hxg6 fxg6 15. Bxh1 e5 16. a4` | [ply 25](http://localhost:5173/analysis?game_id=682691&ply=25) | [board](http://localhost:5173/analysis?fen=r3kb1r/pp1nppp1/2p3bp/7P/2N5/2P3P1/PP2N1B1/R1B1K2n%20w%20-%20-%200%2014) |
| 450 | allowed | HANGING_PIECE | 0 | `19. Nxd6+ Ke7` | [ply 35](http://localhost:5173/analysis?game_id=682691&ply=35) | [board](http://localhost:5173/analysis?fen=r3k2r/pp1n1pp1/2pbp2p/8/2N2N2/2P2KP1/PP6/R1B5%20w%20-%20-%201%2019) |
| 451 | missed | FORK | 6 | `28... Rd2 29. Ne2 Rxa2 30. Bd6 Rd2 31. Bf4 Nh2+ 32. Kf2 Nxf1 33. Kxf1 Rd3 34. b4` | [ply 55](http://localhost:5173/analysis?game_id=682691&ply=55) | [board](http://localhost:5173/analysis?fen=3r2k1/p5p1/4p2p/5p2/5Nn1/BPP2KP1/P7/5R2%20b%20-%20-%200%2028) |
| 452 | missed | FORK | 0 | `29... Nh2+ 30. Kg2 Nxf1 31. Kxf1 e5 32. Ne2 Kf7 33. c4 g5 34. c5 h5 35. b4` | [ply 57](http://localhost:5173/analysis?game_id=682691&ply=57) | [board](http://localhost:5173/analysis?fen=4r1k1/p5p1/3Bp2p/5p2/5Nn1/1PP2KP1/P7/5R2%20b%20-%20-%200%2029) |
| 453 | missed | TRAPPED_PIECE | 8 | `37... h5 38. c5 Ke6 39. Ng7+ Kf6 40. Nxh5+ Kg6 41. Nxf4+ gxf4 42. Bb4 Kf5 43. Kg2` | [ply 73](http://localhost:5173/analysis?game_id=682691&ply=73) | [board](http://localhost:5173/analysis?fen=3r4/p4k2/7p/5Np1/2P2p2/BP6/P7/5K2%20b%20-%20-%200%2037) |
| 454 | allowed | DISCOVERED_CHECK | 4 | `41. Ne5+ Kf6 42. Nc4 Ke7 43. c6+ Rxa3 44. Nxa3 Kd6 45. Nb5+ Kxc6 46. Nxa7+ Kc5` | [ply 79](http://localhost:5173/analysis?game_id=682691&ply=79) | [board](http://localhost:5173/analysis?fen=8/p7/6k1/2P3p1/5pN1/BP6/r7/5K2%20w%20-%20-%200%2041) |
| 455 | missed | FORK | 2 | `25... Qxg4+ 26. hxg4 d4 27. b4 dxc3 28. Ra3 Rb8 29. Re4 Rfc8 30. Rxe5 Rxb4 31. Rxc3` | [ply 49](http://localhost:5173/analysis?game_id=682700&ply=49) | [board](http://localhost:5173/analysis?fen=4rrk1/5ppp/p7/3ppq2/P4nQ1/1PN1RP1P/R1P2P2/6K1%20b%20-%20-%200%2025) |
| 456 | allowed | ATTRACTION | 0 | `14. Bxf5 Qxf5 15. g4 Qf6 16. f5 e4 17. dxe4 d3 18. Nec3 Be5 19. Qxd3 Rd8` | [ply 25](http://localhost:5173/analysis?game_id=682742&ply=25) | [board](http://localhost:5173/analysis?fen=r3nrk1/pppq2pp/2nb4/4pb2/3pBP2/PP1P2PP/2P1N3/RNBQK2R%20w%20-%20-%201%2014) |
| 457 | missed | SKEWER | 10 | `21... Rxd3 22. Qxd3 Qxd3 23. Rd1 Qe3 24. Rd2 Re8 25. Kd1 Ne4 26. Nxe4 Qxb3+ 27. Ke1` | [ply 41](http://localhost:5173/analysis?game_id=682742&ply=41) | [board](http://localhost:5173/analysis?fen=3r1rk1/ppp3pp/2n2n2/8/5P2/PPNP3q/3QN3/R3KR2%20b%20-%20-%200%2021) |
| 458 | allowed | CLEARANCE | 10 | `7... cxd4 8. Qxd4 c5 9. Qf4 Ne7` | [ply 12](http://localhost:5173/analysis?game_id=682745&ply=12) | [board](http://localhost:5173/analysis?fen=r1bqkbnr/5ppp/p1p1p3/2ppP3/3P4/2N2N2/PPP2PPP/R1BQK2R%20b%20-%20-%200%207) |
| 459 | missed | PIN | 4 | `21. Qg5 f5 22. exf6 g6 23. f4 Ra7 24. f5 exf5 25. Rfe1 Qc6 26. Re7 Rf7` | [ply 40](http://localhost:5173/analysis?game_id=682745&ply=40) | [board](http://localhost:5173/analysis?fen=r1b2rk1/2q2ppp/4p3/p1ppP2N/5Q2/1P6/P1P2PPP/R4RK1%20w%20-%20-%200%2021) |
| 460 | missed | PIN | 0 | `26. Nxh5+ Kg8 27. Re3 Qxe5 28. Qxe5 f6 29. Nxf6+ Rxf6 30. Qxf6 a4 31. Qxg6+ Kf8` | [ply 50](http://localhost:5173/analysis?game_id=682745&ply=50) | [board](http://localhost:5173/analysis?fen=r1b2r2/2q2pk1/4pNp1/p2pP1Qp/2p5/1P6/P1P2PPP/R3R1K1%20w%20-%20-%200%2026) |
| 461 | allowed | CLEARANCE | 2 | `9... e5 10. dxe5 Bb4+ 11. Nc3 Qxd1+ 12. Bxd1 Bxc3+ 13. bxc3 Nxe5` | [ply 16](http://localhost:5173/analysis?game_id=682746&ply=16) | [board](http://localhost:5173/analysis?fen=r2qkbnr/p3pppp/2n5/1p6/2pPP3/4BB2/1P3PPP/RN1QK2R%20b%20-%20-%201%209) |
| 462 | missed | FORK | 8 | `12. Nc3 Qd7 13. Ra5 Nc8 14. Nxb5 Bb4 15. Nc7+ Qxc7 16. Qa4+ Nd7 17. Qxb4 Rb8` | [ply 22](http://localhost:5173/analysis?game_id=682746&ply=22) | [board](http://localhost:5173/analysis?fen=r2qkb1r/p3nppp/5n2/1p1Pp3/2p1P3/4BB2/1P3PPP/RN1Q1RK1%20w%20-%20-%200%2012) |
| 463 | missed | INTERMEZZO | 8 | `8... Ne4 9. Qc1 Ba5 10. b4 Nxc3 11. bxa5 Ne4 12. Nf3 Qxa5+ 13. Nd2 h5 14. f3` | [ply 15](http://localhost:5173/analysis?game_id=682752&ply=15) | [board](http://localhost:5173/analysis?fen=r1bqk2r/pp3ppp/2n2n2/3pp3/1b6/P1N1P1B1/1PPQ1PPP/R3KBNR%20b%20-%20-%200%208) |
| 464 | missed | INTERMEZZO | 4 | `15... Nxg3 16. Nxf5 Qg5+ 17. Kb1 Nxf5 18. h4 Qg4 19. g3 Rad8 20. Bh3 Qh5 21. Qf1` | [ply 29](http://localhost:5173/analysis?game_id=682752&ply=29) | [board](http://localhost:5173/analysis?fen=r2qr1k1/pp3ppp/2n5/5b2/3Nn3/P2Q2B1/1PP2PPP/2KR1B1R%20b%20-%20-%200%2015) |
| 465 | missed | FORK | 4 | `17... Qg5+ 18. Kb1 Bxf1 19. h4 Qf6 20. Rdxf1 Qxc6 21. h5 h6 22. Bd4 f6 23. Rf4` | [ply 33](http://localhost:5173/analysis?game_id=682752&ply=33) | [board](http://localhost:5173/analysis?fen=r2qr1k1/pp3ppp/2N5/8/8/P2b4/1PP2BPP/2KR1B1R%20b%20-%20-%200%2017) |
| 466 | allowed | CLEARANCE | 6 | `23. Bc3 Qe4 24. Kb2 Re3 25. Rxe3 Qxe3 26. Bc4 a4 27. Rf1 Rf8 28. g3 c5` | [ply 43](http://localhost:5173/analysis?game_id=682752&ply=43) | [board](http://localhost:5173/analysis?fen=r5k1/5ppp/2p5/p2q4/3B4/PP1R4/K1P3PP/4rB1R%20w%20-%20-%200%2023) |
| 467 | missed | PIN | 6 | `22... Qf5 23. g4 Qe4 24. Rg1 Qf4 25. Be2 Rxe2 26. Kb1 Qxh2 27. Rgd1 Rd8 28. g5` | [ply 43](http://localhost:5173/analysis?game_id=682752&ply=43) | [board](http://localhost:5173/analysis?fen=r5k1/p4ppp/2p5/3q4/3B4/PP1R4/K1P3PP/4rB1R%20b%20-%20-%200%2022) |
| 468 | allowed | DISCOVERED_CHECK | 0 | `19... Nxe4+ 20. Kh1 Nxd2 21. Bxd2 f5 22. bxa4 Qb2 23. Rfc1 e4 24. c5 Nxc5 25. dxc6` | [ply 36](http://localhost:5173/analysis?game_id=682760&ply=36) | [board](http://localhost:5173/analysis?fen=r4rk1/1p1n1pb1/1qpp2pB/2nPp3/p1P1P3/1PN4P/P1BQ2P1/R4RK1%20b%20-%20-%201%2019) |
| 469 | missed | CLEARANCE | 6 | `32. Rh5 Kg6 33. Rxh3 d4 34. g4 Rd6 35. Rd3 Rb6 36. b3 Ra6 37. a4 dxc3` | [ply 62](http://localhost:5173/analysis?game_id=682774&ply=62) | [board](http://localhost:5173/analysis?fen=3r4/pp3k2/4p2p/3pR3/8/2P3Pp/PP2KP1P/8%20w%20-%20-%200%2032) |
| 470 | missed | SELF_INTERFERENCE | 2 | `6. Ng5 Bd7 7. cxd5 Nd4 8. e3 Ne2 9. Nf3 Nxc1 10. Nxe5 Nxd3+ 11. Qxd3 Nf6` | [ply 10](http://localhost:5173/analysis?game_id=682784&ply=10) | [board](http://localhost:5173/analysis?fen=r2qkbnr/ppp3pp/2n1b3/3ppp2/2P5/3P1NP1/PP2PPBP/RNBQK2R%20w%20-%20-%200%206) |
| 471 | missed | CLEARANCE | 2 | `8... c5 9. Qe2 Qa5+ 10. Nd2 cxd4 11. Bxd4 Nc6 12. Bc3 Qc5 13. Nf3 Nh5 14. Bxg7` | [ply 15](http://localhost:5173/analysis?game_id=682788&ply=15) | [board](http://localhost:5173/analysis?fen=rn1q1rk1/ppp1ppbp/3p1np1/8/2PPP3/3BBQ1P/PP3PP1/RN2K2R%20b%20-%20-%200%208) |
| 472 | missed | DEFLECTION | 4 | `21... Kf8 22. Rd7 e3 23. fxe3 Rxg3+ 24. Kh1 Be5 25. Nd5 Kg8 26. Rf1 Re8 27. c5` | [ply 41](http://localhost:5173/analysis?game_id=682788&ply=41) | [board](http://localhost:5173/analysis?fen=r5k1/ppp1N1bp/6p1/6rn/2P1p3/1P1R2PP/P4P2/3R2K1%20b%20-%20-%200%2021) |
| 473 | missed | PROMOTION | 4 | `30... Nxf4 31. gxf4+ Kxf4 32. Kg2 e1=Q 33. Nd5+ Kg5 34. Re7 Rxe7 35. Nxe7 Qe2+ 36. Kg3` | [ply 59](http://localhost:5173/analysis?game_id=682788&ply=59) | [board](http://localhost:5173/analysis?fen=8/pR2N2p/6p1/4r1kn/2P2P2/1P4PP/P3p3/6K1%20b%20-%20-%200%2030) |
| 474 | allowed | PIN | 10 | `13... Qxf2+ 14. Kh1 Qc5 15. Re2 Nc6 16. d4 Qh5 17. Bxc7` | [ply 24](http://localhost:5173/analysis?game_id=682809&ply=24) | [board](http://localhost:5173/analysis?fen=rnb1k2r/ppp1b2p/5p2/2q5/5Bn1/2NP1NP1/PP3PBP/R2QR1K1%20b%20-%20-%201%2013) |
| 475 | missed | SACRIFICE | 10 | `13. d4 Qb5 14. Nc3 Qxb2 15. Bd2 Nc6 16. Rb1 Qa3 17. Nb5 Qxa2 18. Ra1 Qb2` | [ply 24](http://localhost:5173/analysis?game_id=682809&ply=24) | [board](http://localhost:5173/analysis?fen=rnb1k2r/ppp1b2p/5p2/2q5/5Bn1/3P1NP1/PP3PBP/RN1QR1K1%20w%20-%20-%200%2013) |
| 476 | missed | SACRIFICE | 6 | `15. g3 Qxd4 16. Bxg4 Rxe1+ 17. Qxe1 Qxg4 18. Qe3 b6 19. Kg2 Re8 20. Qf3 Qd7` | [ply 28](http://localhost:5173/analysis?game_id=682811&ply=28) | [board](http://localhost:5173/analysis?fen=4rrk1/ppp2pp1/3b1n1p/4q3/3N2b1/2NP4/PPP1BPPP/R2QR1K1%20w%20-%20-%200%2015) |
| 477 | allowed | HANGING_PIECE | 0 | `18... Nxg4 19. Ng1 Rxe1+ 20. Rxe1 Qh1 21. g3 f5 22. Nd1 Nh2+ 23. Ke2 f4 24. gxf4` | [ply 34](http://localhost:5173/analysis?game_id=682811&ply=34) | [board](http://localhost:5173/analysis?fen=4r1k1/ppp2pp1/3b1n1p/8/6B1/2NP4/PPP1NPPq/R3QK2%20b%20-%20-%201%2018) |
| 478 | missed | SACRIFICE | 2 | `18. Qxe8+ Nxe8 19. Nde2 Qh1+ 20. Ng1 Bh2 21. Ne2 Bxg1 22. Nxg1 Qh4 23. Bf3 Nf6` | [ply 34](http://localhost:5173/analysis?game_id=682811&ply=34) | [board](http://localhost:5173/analysis?fen=4r1k1/ppp2pp1/3b1n1p/8/3N2B1/2NP4/PPP2PPq/R3QK2%20w%20-%20-%200%2018) |
| 479 | allowed | CLEARANCE | 6 | `21. f3 Reb8 22. Qc2 Qc6 23. d4 Nc4 24. Qd3 Qd5 25. Rab1 Rb2 26. Rxb2 Rxb2` | [ply 39](http://localhost:5173/analysis?game_id=682854&ply=39) | [board](http://localhost:5173/analysis?fen=4r1k1/1rpq1p2/pn3p2/2B1p3/8/1QPP2P1/P3PPKP/R3R3%20w%20-%20-%201%2021) |
| 480 | missed | CLEARANCE | 2 | `18... Ne2+ 19. Kf1 Qd4 20. Qh4 Qg1+ 21. Kxe2 Qxg2+ 22. Ke1 Rxd3 23. Qg3 Qxg3+ 24. hxg3` | [ply 35](http://localhost:5173/analysis?game_id=682871&ply=35) | [board](http://localhost:5173/analysis?fen=3r1rk1/pp4pp/2pqp3/5p2/3n2n1/3B1P1Q/PPPB2PP/R2R2K1%20b%20-%20-%200%2018) |
| 481 | missed | DISCOVERED_ATTACK | 1 | `18... Bb4+ 19. c3 Qxf7 20. cxb4 Qxf2+ 21. Kd1 e3 22. Re1 Qxg2 23. a4 Kb8 24. b5` | [ply 35](http://localhost:5173/analysis?game_id=682883&ply=35) | [board](http://localhost:5173/analysis?fen=2kr3r/pp1qbQ1p/8/8/3pp3/7P/PPPK1PP1/R1B4R%20b%20-%20-%200%2018) |
| 482 | missed | CLEARANCE | 2 | `8... e6 9. Nce2 Bd6 10. c3` | [ply 15](http://localhost:5173/analysis?game_id=682885&ply=15) | [board](http://localhost:5173/analysis?fen=r1bqkb1r/4pppp/p1n2n2/1p1p4/3P4/1BN1B3/PPP2PPP/R2QK1NR%20b%20-%20-%200%208) |
| 483 | allowed | MATE | 10 | `15. Qxf7+ Kh8 16. Qxe8+ Kg7 17. Qf7+ Kh6 18. Qf8+ Kh5 19. Bg4+ Kh4 20. g3#` | [ply 27](http://localhost:5173/analysis?game_id=682887&ply=27) | [board](http://localhost:5173/analysis?fen=rn2r1k1/ppp2p1p/4B1p1/4p1b1/4P3/5Q1P/PPP2PP1/3R1RK1%20w%20-%20-%200%2015) |
| 484 | missed | CLEARANCE | 4 | `14... Rxe6 15. Bxf6 Nc6 16. c3 Rae8 17. Bg5 f6 18. Bh6 Rd8 19. Kh2 f5 20. exf5` | [ply 27](http://localhost:5173/analysis?game_id=682887&ply=27) | [board](http://localhost:5173/analysis?fen=rn2r1k1/ppp2p1p/4Bbp1/4p1B1/4P3/5Q1P/PPP2PP1/3R1RK1%20b%20-%20-%200%2014) |
| 485 | missed | CLEARANCE | 2 | `17... Rfe8 18. Rb3 Bf8 19. Bd4 g6 20. Ne3 Qa6 21. g4 Qd6 22. Bb2 Nc5 23. g5` | [ply 33](http://localhost:5173/analysis?game_id=682895&ply=33) | [board](http://localhost:5173/analysis?fen=r4rk1/pp1nbppp/5n2/3P1N2/8/4B2P/q4PP1/1R1Q1RK1%20b%20-%20-%200%2017) |
| 486 | allowed | CLEARANCE | 4 | `14... Bxd3 15. Bg5 Qc7 16. Rf2 Rce8 17. Qd2 c4 18. Bxc6 Qxc6 19. Bh6 a5 20. a3` | [ply 26](http://localhost:5173/analysis?game_id=682917&ply=26) | [board](http://localhost:5173/analysis?fen=2rq1rk1/p4pbp/2np2p1/1ppB1b2/8/2PP1N2/PP1B2PP/R1Q2RK1%20b%20-%20-%201%2014) |
| 487 | missed | DISCOVERED_ATTACK | 1 | `14. Ng5 Ne5 15. Rxf5 gxf5 16. Qh5 h6 17. Rf1 hxg5 18. Rxf5 b4 19. Rxg5 Qf6` | [ply 26](http://localhost:5173/analysis?game_id=682917&ply=26) | [board](http://localhost:5173/analysis?fen=2rq1rk1/p4pbp/2np2p1/1ppB1b2/8/2PP1N2/PP1B2PP/R2Q1RK1%20w%20-%20-%200%2014) |
| 488 | allowed | PIN | 6 | `19... Qxd5 20. Bd2 Qc4 21. Qf4+ Kg8 22. Nc3 Nd4 23. Kd1 Bxb4 24. Rc1 Ba3 25. Rc2` | [ply 36](http://localhost:5173/analysis?game_id=682923&ply=36) | [board](http://localhost:5173/analysis?fen=3q1b1r/p4kpp/1p2p3/3B4/1P2pBQ1/8/P1n1N1PP/R1K4R%20b%20-%20-%200%2019) |
| 489 | missed | DISCOVERED_CHECK | 2 | `19. Rf1 Bxc4 20. Bg5+ Ke8 21. Bxd8 Nxb4 22. Qxe4 Nd3+ 23. Kd2 Bb4+ 24. Kc2 Bb5` | [ply 36](http://localhost:5173/analysis?game_id=682923&ply=36) | [board](http://localhost:5173/analysis?fen=3q1b1r/p4kpp/1p2p3/3b4/1PB1pBQ1/8/P1n1N1PP/R1K4R%20w%20-%20-%200%2019) |
| 490 | allowed | HANGING_PIECE | 0 | `8... gxh4` | [ply 14](http://localhost:5173/analysis?game_id=682928&ply=14) | [board](http://localhost:5173/analysis?fen=rnbqkb1r/ppp1p3/5n1p/4Npp1/3P3B/2N5/PPP3PP/R2QKB1R%20b%20-%20-%201%208) |
| 491 | allowed | SACRIFICE | 10 | `12... Qg5 13. Qxe4 Bg7 14. Ng6 Qf5 15. Qxf5 exf5` | [ply 22](http://localhost:5173/analysis?game_id=682928&ply=22) | [board](http://localhost:5173/analysis?fen=rnbqkb1r/ppp5/4p2p/4N3/2BPp2p/8/PPP1Q1PP/R3K2R%20b%20-%20-%201%2012) |
| 492 | missed | CLEARANCE | 10 | `4... dxc4 5. Nf3 Nd5 6. g3 Nd7 7. Bd2 Nxc3 8. bxc3 b5 9. Bg2 Bb7` | [ply 7](http://localhost:5173/analysis?game_id=682939&ply=7) | [board](http://localhost:5173/analysis?fen=rnbqkb1r/pp2pppp/2p2n2/3p4/2PP1B2/2N5/PP2PPPP/R2QKBNR%20b%20-%20-%200%204) |
| 493 | missed | FORK | 4 | `19... a4 20. Nxa4 Ne4 21. f3 Ng3 22. Qh2 Qf4+ 23. Kb1 Nxh1 24. Qxf4 Rxf4 25. Rxh1` | [ply 37](http://localhost:5173/analysis?game_id=682943&ply=37) | [board](http://localhost:5173/analysis?fen=r4rk1/6pp/3qpnp1/p2p2P1/1n1P4/1BN4P/1PP1QP2/2KR3R%20b%20-%20-%200%2019) |
| 494 | allowed | CLEARANCE | 10 | `22. Qxe6+ Qxe6 23. Bxe6+ Kh8 24. Rd2 a3 25. bxa3 Rxa3 26. Kb2 Ra5 27. Ra1 Rb5` | [ply 41](http://localhost:5173/analysis?game_id=682943&ply=41) | [board](http://localhost:5173/analysis?fen=r4rk1/6pp/3qp1p1/6P1/pn1PQ3/1B5P/1PP2P2/2KR3R%20w%20-%20-%200%2022) |
| 495 | allowed | HANGING_PIECE | 0 | `26. Bxb4 f6 27. g4 Nh4 28. f4 a5 29. Bc5 Nf3+ 30. Kf2 Nd2 31. Ke2 Ne4` | [ply 49](http://localhost:5173/analysis?game_id=682960&ply=49) | [board](http://localhost:5173/analysis?fen=r5k1/4Bppp/p7/1p3n2/1bp5/4P2P/P4PP1/2R3K1%20w%20-%20-%200%2026) |
| 496 | missed | FORK | 0 | `25... Ne2+ 26. Kh2 Nxc1 27. Bxb4 Nxa2 28. Bc5 a5 29. e4 c3 30. e5 Nb4 31. Bxb4` | [ply 49](http://localhost:5173/analysis?game_id=682960&ply=49) | [board](http://localhost:5173/analysis?fen=r5k1/4Bppp/p7/1p3N2/1bpn4/4P2P/P4PP1/2R3K1%20b%20-%20-%200%2025) |
| 497 | allowed | DEFLECTION | 6 | `19... Qh4 20. Bc1 Qxh2+ 21. Kf1 Qh1+ 22. Ke2 Qxg2 23. Rf1` | [ply 36](http://localhost:5173/analysis?game_id=682969&ply=36) | [board](http://localhost:5173/analysis?fen=r2qk2r/p4ppp/2p5/1p6/PPnP2n1/1QN1P3/1B3PPP/R2R2K1%20b%20-%20-%200%2019) |
| 498 | missed | CLEARANCE | 6 | `20. Bc1 Qxh2+ 21. Kf1 Qh1+ 22. Ke2 Qxg2 23. Rf1 Nh2 24. Rd1 a6 25. Qb1 Qf3+` | [ply 38](http://localhost:5173/analysis?game_id=682969&ply=38) | [board](http://localhost:5173/analysis?fen=r3k2r/p4ppp/2p5/1p6/PPnP2nq/1QN1P3/1B3PPP/R2R2K1%20w%20-%20-%200%2020) |
| 499 | missed | SACRIFICE | 2 | `23. Rg1 Nxb3 24. d5 Qxb2 25. Nd1 Nxd1 26. Re1+ Kf8 27. Rxd1 Qe2 28. Rb1 cxd5` | [ply 44](http://localhost:5173/analysis?game_id=682969&ply=44) | [board](http://localhost:5173/analysis?fen=r3k2r/p4ppp/2p5/1p6/PP1P4/1QN1n2P/1B1n1qP1/R6K%20w%20-%20-%200%2023) |
| 500 | allowed | SACRIFICE | 6 | `7. Nc3 Nc6 8. Bf4 exd3 9. Nd5 dxc2 10. Qh5+ g6 11. Qe2+ Kf7 12. Nf3 Bd6` | [ply 11](http://localhost:5173/analysis?game_id=682972&ply=11) | [board](http://localhost:5173/analysis?fen=rnbqkbnr/pp4pp/8/2p2p2/4p3/3P2P1/PPP2PBP/RNBQK1NR%20w%20-%20-%200%207) |
| 501 | missed | CLEARANCE | 10 | `6... Nf6 7. Nf3 Nc6` | [ply 11](http://localhost:5173/analysis?game_id=682972&ply=11) | [board](http://localhost:5173/analysis?fen=rnbqkbnr/pp4pp/8/2p1pp2/8/3P2P1/PPP2PBP/RNBQK1NR%20b%20-%20-%200%206) |
| 502 | missed | FORK | 6 | `17... Ng4 18. Qd2 Bxe4 19. Nxe4 Nxh6 20. Qxh6 Ne2+ 21. Kh1 Nxc1 22. Qxc1 Kg7 23. h4` | [ply 33](http://localhost:5173/analysis?game_id=682972&ply=33) | [board](http://localhost:5173/analysis?fen=r2q2k1/1p2br1p/p4npB/2p2b2/3nN3/2NQ2P1/PPP2PBP/2R2RK1%20b%20-%20-%200%2017) |
| 503 | allowed | DISCOVERED_ATTACK | 5 | `19. c3 Bxe4 20. Qxe4 Bf8 21. cxd4 Bxh6 22. Rxc5 Bg7 23. Rd5 Qe8 24. Qd3 Kh8` | [ply 35](http://localhost:5173/analysis?game_id=682972&ply=35) | [board](http://localhost:5173/analysis?fen=r5k1/1p1qbr1p/p5pB/2p2b2/3nN3/3Q2P1/PPP2PBP/2R2RK1%20w%20-%20-%201%2019) |
| 504 | allowed | CAPTURING_DEFENDER | 2 | `11... Nxc3 12. Qxc3 Nxd5 13. Qb3 c6 14. Rad1 f6 15. c4 Nxe3 16. fxe3 Be7 17. e4` | [ply 20](http://localhost:5173/analysis?game_id=682976&ply=20) | [board](http://localhost:5173/analysis?fen=r3kb1r/pppq1ppp/3p1n2/3Pp3/4n3/P1NQBN2/1PP2PPP/R4RK1%20b%20-%20-%201%2011) |
| 505 | allowed | FORK | 2 | `e8g8 f4e5 f7f6 g5e6 f6e5 e6f8 a8f8 f1f8 g8f8 e1f1 f8g8 g1h1` | [ply 40](http://localhost:5173/analysis?game_id=682976&ply=40) | [board](http://localhost:5173/analysis?fen=r3k2r/p1pq1pbp/1p4p1/3Pp1N1/1PP1QB2/P7/6PP/4RRK1%20b%20-%20-%201%2021) |
| 506 | allowed | SKEWER | 10 | `12. Ne5 Nxe5 13. dxe5 Nd7 14. Bxe7 Qxe7 15. Qg3 h5 16. c3 Bf5 17. Qxg7` | [ply 21](http://localhost:5173/analysis?game_id=682982&ply=21) | [board](http://localhost:5173/analysis?fen=r2qk2r/4bppp/p1n1pn2/1p1p2B1/3P2b1/1B1Q1N2/PPP2PPP/RN2R1K1%20w%20-%20-%201%2012) |
| 507 | missed | CAPTURING_DEFENDER | 2 | `11... Bxf3 12. Qxf3 Nxd4 13. Qd1 Nxb3 14. axb3 Bc5 15. Qf3` | [ply 21](http://localhost:5173/analysis?game_id=682982&ply=21) | [board](http://localhost:5173/analysis?fen=r2qk2r/5ppp/p1nbpn2/1p1p2B1/3P2b1/1B1Q1N2/PPP2PPP/RN2R1K1%20b%20-%20-%200%2011) |
| 508 | missed | SKEWER | 10 | `30... a5 31. a4 bxa4 32. Bxa4 Rc8 33. Ra6 Kf8 34. Bc6 Be8 35. Bxd5 Rxc3 36. Ra8` | [ply 59](http://localhost:5173/analysis?game_id=682982&ply=59) | [board](http://localhost:5173/analysis?fen=5rk1/5bpp/p2R4/1p1p4/6P1/1BP2P2/P1P4P/6K1%20b%20-%20-%200%2030) |
| 509 | allowed | FORK | 0 | `18. Nxe6 Bxb2 19. Nxf8 Bxa1 20. Nxh7 Bb2 21. Rc2 Rc8 22. Ng5 Rxc2 23. Qf7+ Kh8` | [ply 33](http://localhost:5173/analysis?game_id=682988&ply=33) | [board](http://localhost:5173/analysis?fen=r2q1rk1/pp4pp/4pb2/3p4/3N4/5Q2/PP3PPP/R1R3K1%20w%20-%20-%200%2018) |
| 510 | missed | DISCOVERED_ATTACK | 9 | `11. b4` | [ply 20](http://localhost:5173/analysis?game_id=683005&ply=20) | [board](http://localhost:5173/analysis?fen=rn1qk2r/p2b3p/1p1p2pn/3Ppp2/2P5/2NB1N2/PP3PPP/R2Q1RK1%20w%20-%20-%200%2011) |
| 511 | missed | FORK | 2 | `12. Qd2 Na6 13. Ne6 Bxe6 14. dxe6 Kg7 15. Nd5 Re8 16. e7 Qd7 17. Qg5 Ng8` | [ply 22](http://localhost:5173/analysis?game_id=683005&ply=22) | [board](http://localhost:5173/analysis?fen=rn1q1rk1/p2b3p/1p1p2pn/3PppN1/2P5/2NB4/PP3PPP/R2Q1RK1%20w%20-%20-%200%2012) |
| 512 | missed | SACRIFICE | 10 | `12... f6 13. Bc1 c5 14. d5 Kh8 15. dxe6 c4 16. Bxc4 Qxd1+ 17. Nxd1 Bb6 18. Be3` | [ply 23](http://localhost:5173/analysis?game_id=683009&ply=23) | [board](http://localhost:5173/analysis?fen=rn1q1rk1/pp3ppp/2p1p3/5bB1/3P4/1BN2N2/PPP2bPP/R2Q3K%20b%20-%20-%200%2012) |
| 513 | missed | SACRIFICE | 2 | `13... Bxd4 14. Nxd4 Bg6 15. Nf5 Qxd2 16. Ne7+ Kh8 17. Nxg6+ hxg6 18. Bxd2 Nd7 19. a4` | [ply 25](http://localhost:5173/analysis?game_id=683009&ply=25) | [board](http://localhost:5173/analysis?fen=rn3rk1/pp3ppp/2pqp3/5bB1/3P4/1BN2N2/PPPQ1bPP/R6K%20b%20-%20-%200%2013) |
| 514 | allowed | SACRIFICE | 10 | `24. Re2 bxa4 25. Bxa4 Rf5 26. Kg2 Rxe5 27. h4 Rxe3 28. Rxe3 Bxe3 29. Qc3 Bc5` | [ply 45](http://localhost:5173/analysis?game_id=683024&ply=45) | [board](http://localhost:5173/analysis?fen=5rk1/6pp/pq2p3/1pbpP3/P7/1B2P1PP/1P1Q4/4R1K1%20w%20-%20-%201%2024) |
| 515 | missed | FORK | 2 | `23... bxa4 24. Bc2 Bxe3+ 25. Rxe3 Rxc2 26. Qxc2 Qxe3+ 27. Kg2 Qxe5 28. Qc8+ Kf7 29. Qd7+` | [ply 45](http://localhost:5173/analysis?game_id=683024&ply=45) | [board](http://localhost:5173/analysis?fen=2r3k1/6pp/pq2p3/1pbpP3/P7/1B2P1PP/1P1Q4/4R1K1%20b%20-%20-%200%2023) |
| 516 | allowed | DISCOVERED_ATTACK | 1 | `16... fxe5 17. Ne4 Rxf3 18. gxf3 exd4 19. Rfe1 Rf8 20. Bf1 Ne5 21. Bg2 d3 22. Qg5` | [ply 30](http://localhost:5173/analysis?game_id=683025&ply=30) | [board](http://localhost:5173/analysis?fen=r4rk1/p2nq2p/b1pNppp1/1p1nP3/3P4/3B1N2/PP1Q1PPP/R4RK1%20b%20-%20-%201%2016) |
| 517 | missed | CLEARANCE | 8 | `9... b5 10. a4 b4 11. Na2 a5 12. c3 Qe7 13. Nc1 Rfb8 14. Nd3 Bb7 15. Ne5` | [ply 17](http://localhost:5173/analysis?game_id=683030&ply=17) | [board](http://localhost:5173/analysis?fen=r2q1rk1/ppp2ppp/2bbpn2/3p4/3P1P2/2N1P1N1/PPPB2PP/R2QK2R%20b%20-%20-%200%209) |
| 518 | missed | SACRIFICE | 10 | `24... Rfc8 25. Kf2 Qa2+ 26. Rc2 Qxc2+ 27. Nxc2 Rxc3 28. Qe2 e5 29. fxe5 Rbc8 30. Nd4` | [ply 47](http://localhost:5173/analysis?game_id=683030&ply=47) | [board](http://localhost:5173/analysis?fen=1r3rk1/4bppp/4p3/3b2PQ/pPqNpP2/P1B1P3/7P/2R1K2R%20b%20-%20-%200%2024) |
| 519 | missed | ATTRACTION | 4 | `5... e5 6. dxe5 Qa5+ 7. Qd2 Qxd2+ 8. Kxd2 Ne4+ 9. Ke1 g5 10. f3 gxf4 11. fxe4` | [ply 9](http://localhost:5173/analysis?game_id=683033&ply=9) | [board](http://localhost:5173/analysis?fen=r1bqkb1r/pp2pppp/2n2n2/1Npp4/3P1B2/4P3/PPP2PPP/R2QKBNR%20b%20-%20-%200%205) |
| 520 | allowed | PIN | 0 | `21. exf6 Bxf6 22. Bf4 Rb4 23. Qe2 Qb6 24. Nxf6+ gxf6 25. g3 Rg7 26. Bc1 Re4` | [ply 39](http://localhost:5173/analysis?game_id=683056&ply=39) | [board](http://localhost:5173/analysis?fen=1r1q2k1/4brpp/p3pp1B/2ppPn1N/6Q1/1P6/P4PPP/3R1RK1%20w%20-%20-%201%2021) |
| 521 | allowed | CLEARANCE | 10 | `24. Qg5 h6 25. Qxf6 gxf6 26. Bd2 Rb6 27. Rc1 Rc6 28. Rc3 h5 29. Rfc1 Rfc7` | [ply 45](http://localhost:5173/analysis?game_id=683056&ply=45) | [board](http://localhost:5173/analysis?fen=6k1/5rpp/p3pq2/2pp1n2/1r3BQ1/1P6/P4PPP/3R1RK1%20w%20-%20-%200%2024) |
| 522 | allowed | FORK | 2 | `17. Nxe4 dxe4 18. Nxf7 Rxf7 19. Rxf7 Nf5 20. Bxg4 hxg4 21. Qxg4 Nh6 22. Qxg7 Nxf7` | [ply 31](http://localhost:5173/analysis?game_id=683084&ply=31) | [board](http://localhost:5173/analysis?fen=2k2r1r/2p1npp1/p2qp3/P2pN2p/3Pn1b1/2P1P1P1/3NB1PP/R2Q1RK1%20w%20-%20-%201%2017) |
| 523 | allowed | FORK | 6 | `20. Rab1 Nb4 21. Qxb4 Qxb4 22. Rxb4 f6 23. Ng6 Rd8 24. Nxh8 Rxh8 25. Rfb1 Kd7` | [ply 37](http://localhost:5173/analysis?game_id=683084&ply=37) | [board](http://localhost:5173/analysis?fen=2k2r1r/2p2pp1/p2qp3/P2nN3/3Pp1p1/1QP1P1P1/6PP/R4RK1%20w%20-%20-%201%2020) |
| 524 | missed | SACRIFICE | 8 | `19... f6 20. Rab1 Kd8 21. Qb8+ Nc8 22. Ng6 Rh5 23. Nxf8 Qxf8 24. Qa8 Kd7 25. Qxe4` | [ply 37](http://localhost:5173/analysis?game_id=683084&ply=37) | [board](http://localhost:5173/analysis?fen=2k2r1r/2p1npp1/p2qp3/P3N3/3Pp1p1/1QP1P1P1/6PP/R4RK1%20b%20-%20-%200%2019) |
| 525 | missed | SACRIFICE | 6 | `20... Nb4 21. Nxf7 Qe7 22. Qxb4 Qxb4 23. cxb4 Rhg8 24. Ng5 Rh8 25. Rxf8+ Rxf8 26. Nxe6` | [ply 39](http://localhost:5173/analysis?game_id=683084&ply=39) | [board](http://localhost:5173/analysis?fen=2k2r1r/2p2pp1/p2qp3/P2nN3/3Pp1p1/1QP1P1P1/6PP/1R3RK1%20b%20-%20-%200%2020) |
| 526 | allowed | PIN | 10 | `13... Nxf4 14. gxf4 Qxf4 15. Bxc6+ bxc6 16. Re1 Qh2+ 17. Kf1` | [ply 24](http://localhost:5173/analysis?game_id=683123&ply=24) | [board](http://localhost:5173/analysis?fen=rb2k2r/pp3ppp/2nqp3/1B1p3n/3P1B2/2N2PPP/PP3P2/2RQ1RK1%20b%20-%20-%201%2013) |
| 527 | allowed | CAPTURING_DEFENDER | 4 | `21... Qxf2+ 22. Qxf2 Bxf2 23. Kxf2 Nxd4 24. Bd3 g6 25. Rh4 Nc6 26. Rgh1 h5 27. Rg1` | [ply 40](http://localhost:5173/analysis?game_id=683123&ply=40) | [board](http://localhost:5173/analysis?fen=r4rk1/pp3ppp/2n1p3/1B1p4/3P4/2N1QPb1/PP2KPq1/6RR%20b%20-%20-%201%2021) |
| 528 | allowed | CLEARANCE | 8 | `27... Nf5 28. Bxf5 exf5 29. Nxd5 Rc2+ 30. Kg3 f6 31. Rb4 Rf7 32. Ne3 Rc5 33. Rd1` | [ply 52](http://localhost:5173/analysis?game_id=683123&ply=52) | [board](http://localhost:5173/analysis?fen=2r2rk1/pp3pp1/4p3/3p4/3n3R/2NB1P2/PP3K2/6R1%20b%20-%20-%201%2027) |
| 529 | missed | DISCOVERED_CHECK | 6 | `27. Bh7+ Kh8 28. Rg4 Nc6 29. Nxd5 exd5 30. Bf5+ Kg8 31. Rgh4 g5 32. Rh8+ Kg7` | [ply 52](http://localhost:5173/analysis?game_id=683123&ply=52) | [board](http://localhost:5173/analysis?fen=2r2rk1/pp3pp1/4p3/3p4/3n4/2NB1P2/PP3K2/6RR%20w%20-%20-%200%2027) |
| 530 | allowed | SKEWER | 2 | `48... a1=Q+ 49. Kd5 Qxf6 50. f8=Q Qxf8 51. Kd4 Qd6+ 52. Ke3 Qf4+ 53. Kd3 Rd2+ 54. Kc3` | [ply 94](http://localhost:5173/analysis?game_id=683123&ply=94) | [board](http://localhost:5173/analysis?fen=8/1p3P2/5R2/1k2K3/8/8/p4r2/8%20b%20-%20-%201%2048) |
| 531 | missed | CLEARANCE | 2 | `48. Kd5 a1=Q 49. Re5 Qa2+ 50. Kd6+ Kb4 51. Re4+ Ka5 52. Rg4 Qxf7 53. Rg1 Rd2+` | [ply 94](http://localhost:5173/analysis?game_id=683123&ply=94) | [board](http://localhost:5173/analysis?fen=8/1p3P2/4R3/1k2K3/8/8/p4r2/8%20w%20-%20-%200%2048) |
| 532 | missed | PROMOTION | 4 | `55. Kd7 Qf5+ 56. Ke7 Kc5 57. f8=Q Qxf8+ 58. Kxf8 Kd4 59. Ke7 b5 60. Kd6 b4` | [ply 108](http://localhost:5173/analysis?game_id=683123&ply=108) | [board](http://localhost:5173/analysis?fen=8/1p3P2/4K3/1k6/4q3/8/8/8%20w%20-%20-%200%2055) |
| 533 | missed | PROMOTION | 0 | `56. f8=Q+ Kb5 57. Qa8 Qc6+ 58. Kf7 b6 59. Qa1 Qd6 60. Ke8 Qe6+ 61. Kd8 Qc6` | [ply 110](http://localhost:5173/analysis?game_id=683123&ply=110) | [board](http://localhost:5173/analysis?fen=8/1p3P2/5K2/2k5/4q3/8/8/8%20w%20-%20-%200%2056) |
| 534 | missed | PROMOTION | 8 | `57. Kg8 Qg5+ 58. Kh8 Qd8+ 59. Kg7 Qe7 60. Kg8 Kd5 61. f8=Q Qxf8+ 62. Kxf8 Ke6` | [ply 112](http://localhost:5173/analysis?game_id=683123&ply=112) | [board](http://localhost:5173/analysis?fen=8/1p3PK1/8/2k1q3/8/8/8/8%20w%20-%20-%200%2057) |
| 535 | allowed | PIN | 0 | `13. Nxd5 Qc5 14. c4 Ne7 15. b4 Nxf3+ 16. Qxf3 Qc6 17. Rac1 Ng6 18. b5 axb5` | [ply 23](http://localhost:5173/analysis?game_id=683131&ply=23) | [board](http://localhost:5173/analysis?fen=r3k1nr/1p3ppp/pq1bp3/3p2B1/3n4/2N2B1P/PPP2PP1/R2QR1K1%20w%20-%20-%200%2013) |
| 536 | allowed | PIN | 6 | `16. Bxg7 Ne7 17. Bxh8 Rc8 18. Nxd5 exd5 19. Qxd5 Bc5 20. Bd4 Bb4 21. Qxb7 Bxe1` | [ply 29](http://localhost:5173/analysis?game_id=683131&ply=29) | [board](http://localhost:5173/analysis?fen=r3k1nr/1p3ppp/p2bp3/3p4/3B4/2N2Q1P/P1q2PP1/R3R1K1%20w%20-%20-%200%2016) |
| 537 | allowed | FORK | 2 | `34... Bd4 35. Qe6 Bxf2+ 36. Kg2 Qf3+ 37. Kh3 Bxe1 38. Qxe1 Rc7 39. Qb1 Qe2 40. a4` | [ply 66](http://localhost:5173/analysis?game_id=683141&ply=66) | [board](http://localhost:5173/analysis?fen=8/5rbk/Q5pp/1p6/8/Pq4P1/5P1P/4R1K1%20b%20-%20-%201%2034) |
| 538 | allowed | ATTRACTION | 4 | `35... Qd2 36. Qb6 Bd4 37. Rf6 Qxf2+ 38. Rxf2 Bxb6 39. Kf1 Bxf2 40. Ke2 Bc5 41. Kd3` | [ply 68](http://localhost:5173/analysis?game_id=683141&ply=68) | [board](http://localhost:5173/analysis?fen=8/5rbk/Q3R1pp/1p6/8/P1q3P1/5P1P/6K1%20b%20-%20-%201%2035) |
| 539 | missed | CLEARANCE | 4 | `39. Qc6 g5 40. Qe4 Qc5 41. Rc6 Qd4 42. Qf5 Qb2 43. h3 Qb8 44. Qe4` | [ply 76](http://localhost:5173/analysis?game_id=683141&ply=76) | [board](http://localhost:5173/analysis?fen=4Q3/5rk1/4Rbpp/8/8/q5P1/5PKP/8%20w%20-%20-%200%2039) |
| 540 | allowed | HANGING_PIECE | 0 | `40... Rxf6 41. Qe2 Qc3 42. Kg1 Rf7 43. Kg2 Kh7 44. Kg1 Qd4 45. Qc2 Re7 46. Qc1` | [ply 78](http://localhost:5173/analysis?game_id=683141&ply=78) | [board](http://localhost:5173/analysis?fen=4Q3/5rk1/5Rp1/7p/7P/q5P1/5PK1/8%20b%20-%20-%200%2040) |
| 541 | allowed | PIN | 10 | `20. Qxb5 Rc8 21. Qe2 f6 22. Bf4 Qa6 23. Qg4 Rxc2 24. h4 Nc3 25. Bh6 g6` | [ply 37](http://localhost:5173/analysis?game_id=683146&ply=37) | [board](http://localhost:5173/analysis?fen=q3r1k1/1p3ppp/4p3/1p1pB3/3Pn3/1Q6/2P2PPP/5RK1%20w%20-%20-%201%2020) |
| 542 | missed | DISCOVERED_CHECK | 10 | `19... Qc8 20. Re1 Qc4 21. Re3 b4 22. h4 f6 23. Bd6 Ne2+ 24. Kf1 Nxd4+ 25. Qxc4` | [ply 37](http://localhost:5173/analysis?game_id=683146&ply=37) | [board](http://localhost:5173/analysis?fen=q3r1k1/1p3ppp/4p3/1p1pB3/3P4/1Qn5/2P2PPP/5RK1%20b%20-%20-%200%2019) |
| 543 | allowed | HANGING_PIECE | 0 | `32. Qxc7 gxh5 33. gxh5 Kf6 34. Qg3 Ke7 35. Kh2 Kd7 36. c3 Qxc3 37. Kg2 Qd4` | [ply 61](http://localhost:5173/analysis?game_id=683146&ply=61) | [board](http://localhost:5173/analysis?fen=1Q6/2r2pkp/4p1p1/3p3P/6P1/4qP2/2P2RK1/8%20w%20-%20-%201%2032) |
| 544 | missed | PIN | 0 | `9... dxc4` | [ply 17](http://localhost:5173/analysis?game_id=683154&ply=17) | [board](http://localhost:5173/analysis?fen=r2qk2r/pQp2ppp/2n1pn2/b2p4/2PPbB2/P3PN2/1P1N1PPP/R3KB1R%20b%20-%20-%200%209) |
| 545 | missed | PIN | 2 | `10... c6 11. Qb7 dxc4 12. Bxc4 Bxf3 13. gxf3 Bxd2+ 14. Kxd2` | [ply 19](http://localhost:5173/analysis?game_id=683154&ply=19) | [board](http://localhost:5173/analysis?fen=r2qk2r/p1p1nppp/4pn2/bQ1p4/2PPbB2/P3PN2/1P1N1PPP/R3KB1R%20b%20-%20-%200%2010) |
| 546 | missed | SACRIFICE | 4 | `33... Kh7 34. Rd8 Rd4 35. Rxd4 Qg6 36. Rdd1 a5 37. bxa5` | [ply 65](http://localhost:5173/analysis?game_id=683154&ply=65) | [board](http://localhost:5173/analysis?fen=7k/p1P3p1/5n1p/5q2/1P5r/P4P2/4Q1PP/3RR1K1%20b%20-%20-%200%2033) |
| 547 | allowed | PIN | 2 | `12... dxe6 13. Qe2 Bh3 14. Ne1 Bf5 15. Nc2 Kf8 16. Rfd1 Qc8 17. Ne3 Bg6 18. h4` | [ply 22](http://localhost:5173/analysis?game_id=683171&ply=22) | [board](http://localhost:5173/analysis?fen=rn1qk1r1/2ppbp1p/p3Pp2/5b2/2B5/2N2N2/PP3PPP/R2Q1RK1%20b%20-%20-%200%2012) |
| 548 | missed | CLEARANCE | 2 | `12. Re1 Bh3 13. Bf1 Kf8 14. Nd4 Bg4 15. Qd3 c5 16. Nde2 f5 17. Rad1 Bf6` | [ply 22](http://localhost:5173/analysis?game_id=683171&ply=22) | [board](http://localhost:5173/analysis?fen=rn1qk1r1/2ppbp1p/p3pp2/3P1b2/2B5/2N2N2/PP3PPP/R2Q1RK1%20w%20-%20-%200%2012) |
| 549 | allowed | CLEARANCE | 4 | `23... Qd6 24. Qe4 Kg7 25. Nd5 Rd8 26. Qd4 Rxa2 27. Nh4 Kh8 28. Nf5 Qc6 29. Nfe7` | [ply 44](http://localhost:5173/analysis?game_id=683171&ply=44) | [board](http://localhost:5173/analysis?fen=5kr1/2p1q2p/p1Q2p2/8/8/2N2NP1/Pr5P/4R1K1%20b%20-%20-%201%2023) |
| 550 | missed | PIN | 4 | `23. Rd7 Rb6 24. Qa8+ Qe8 25. Rd8 Ke7 26. Rxe8+ Rxe8 27. Qd5 Rd6 28. Qe4+ Kd8` | [ply 44](http://localhost:5173/analysis?game_id=683171&ply=44) | [board](http://localhost:5173/analysis?fen=5kr1/2p1q2p/p1Q2p2/8/8/2N2NP1/Pr5P/3R2K1%20w%20-%20-%200%2023) |
| 551 | missed | FORK | 2 | `26. Nxc7 Kh6 27. Qc1+ Kh5 28. Rd1 Qxd1+ 29. Qxd1 a5 30. Ne1+ Rg4 31. Qf3 Rxa2` | [ply 50](http://localhost:5173/analysis?game_id=683171&ply=50) | [board](http://localhost:5173/analysis?fen=3q4/2p3kp/p4pr1/2QN4/8/5NP1/Pr5P/4R1K1%20w%20-%20-%200%2026) |
| 552 | allowed | MATE | 10 | `24... Ra3+ 25. Kb1 Qa5 26. c3 Bxc3 27. b3 Raxb3+ 28. Kc1 Qa1+ 29. Kc2 Qb2#` | [ply 46](http://localhost:5173/analysis?game_id=683202&ply=46) | [board](http://localhost:5173/analysis?fen=2b3k1/1r5p/p3pBpP/6q1/1b1Pp1P1/4r3/1PP1N3/2KR2QR%20b%20-%20-%201%2024) |
| 553 | missed | SACRIFICE | 2 | `24. Kb1 Rxe2 25. Rh3 e3 26. Rf3 Rf2 27. Rxf2 exf2 28. Qxf2 Rf7 29. Qe2 Qd5` | [ply 46](http://localhost:5173/analysis?game_id=683202&ply=46) | [board](http://localhost:5173/analysis?fen=2b3k1/1r4Bp/p3p1pP/6q1/1b1Pp1P1/4r3/1PP1N3/2KR2QR%20w%20-%20-%200%2024) |
| 554 | missed | PIN | 2 | `14... Bxd2+ 15. Kxd2 Ne5 16. Qf6 Nxf3+ 17. gxf3 Qa5+ 18. Ke3 e5 19. Qxe5 Qc3+ 20. Bd3` | [ply 27](http://localhost:5173/analysis?game_id=683236&ply=27) | [board](http://localhost:5173/analysis?fen=2kr4/pp1n1Q2/1qp1p1p1/5b2/1b1P4/1P3N2/P1PB1PPP/R3KB1R%20b%20-%20-%200%2014) |
| 555 | allowed | CLEARANCE | 8 | `5... h6 6. Bh4 Nxe5 7. e4 Bd6 8. Rb1 Ng6 9. Bd3 Bf4 10. Bg3 Bxg3 11. hxg3` | [ply 8](http://localhost:5173/analysis?game_id=683244&ply=8) | [board](http://localhost:5173/analysis?fen=r1b1kbnr/pppp1ppp/2n5/4P1B1/1q6/5N2/PPPNPPPP/R2QKB1R%20b%20-%20-%201%205) |
| 556 | allowed | CAPTURING_DEFENDER | 6 | `12. Ne5 Qb6 13. Qb3 Bd6 14. Qxb6 axb6 15. Nxc6` | [ply 21](http://localhost:5173/analysis?game_id=683248&ply=21) | [board](http://localhost:5173/analysis?fen=r2qk2r/p3bppp/2p2n2/3p3b/3P4/3Q1N1P/PP3PP1/RNB2RK1%20w%20-%20-%200%2012) |
| 557 | missed | SACRIFICE | 2 | `22... Rxf5 23. gxf5 a5 24. Kb1 a4 25. Rhg1 Re8 26. Rd5 Rb8 27. Rd4 Kf6 28. h3` | [ply 43](http://localhost:5173/analysis?game_id=683256&ply=43) | [board](http://localhost:5173/analysis?fen=2r5/p3kp2/3p3p/1p1r1N2/2n3P1/P1P1P3/1P3P1P/2KR3R%20b%20-%20-%200%2022) |
| 558 | allowed | HANGING_PIECE | 0 | `12... axb5 13. Nb6+ Kc7 14. Rxc2 Ne7 15. a4 bxa4 16. Nxa4 Ra8 17. Nc3 Nd5 18. Nxd5+` | [ply 22](http://localhost:5173/analysis?game_id=683308&ply=22) | [board](http://localhost:5173/analysis?fen=N5nr/1p1k1ppp/p1n1p3/1B6/1b1P4/4B3/PPb1KPPP/2R4R%20b%20-%20-%201%2012) |
| 559 | allowed | PIN | 0 | `45. Nxe6+ Kh8 46. Nxd8 Rxg2+ 47. Kh3 Rg3+ 48. Kh2 Rg2+` | [ply 87](http://localhost:5173/analysis?game_id=683313&ply=87) | [board](http://localhost:5173/analysis?fen=3r4/1R3pk1/4pNpp/3pPn2/4bN1P/8/5rPK/8%20w%20-%20-%201%2045) |
| 560 | allowed | MATE | 6 | `48. Nxf7+ Kg7 49. Nd6+ Ne7 50. Rxe7+ Kf8 51. Rf7#` | [ply 93](http://localhost:5173/analysis?game_id=683313&ply=93) | [board](http://localhost:5173/analysis?fen=3N3k/1R3p2/5Npp/3pPn2/4b2P/7K/8/6r1%20w%20-%20-%201%2048) |
| 561 | allowed | HANGING_PIECE | 0 | `51. Nxe4` | [ply 99](http://localhost:5173/analysis?game_id=683313&ply=99) | [board](http://localhost:5173/analysis?fen=3N3k/5p2/5Npp/4Pn2/3pb2P/8/7K/8%20w%20-%20-%200%2051) |
| 562 | allowed | PIN | 0 | `12. Bxe7` | [ply 21](http://localhost:5173/analysis?game_id=683314&ply=21) | [board](http://localhost:5173/analysis?fen=r3k2r/ppq1npp1/2n1p2p/1B1pPbB1/Q2P4/2P2N2/P4PPP/R3K2R%20w%20-%20-%200%2012) |
| 563 | missed | FORK | 6 | `23... Rac8 24. Re5 Nf5 25. Rxd5 Rxc2 26. Rxc2 Nxe3 27. Rdc5 Rf1+ 28. Kh2 Nxc2 29. Rxc2` | [ply 45](http://localhost:5173/analysis?game_id=683320&ply=45) | [board](http://localhost:5173/analysis?fen=r4rk1/6pp/p3R2n/1p1p4/4p3/4P2P/P1B3P1/2R3K1%20b%20-%20-%200%2023) |
| 564 | missed | DISCOVERED_ATTACK | 5 | `24... Kf7 25. Re5 Ne7 26. Rf1+ Ke8 27. Bb3 Rxf1+ 28. Kxf1 Kf8 29. Re6 a5 30. Rd6` | [ply 47](http://localhost:5173/analysis?game_id=683320&ply=47) | [board](http://localhost:5173/analysis?fen=r4rk1/6pp/p3R3/1p1p1n2/4p3/4P2P/P1B3P1/4R1K1%20b%20-%20-%200%2024) |
| 565 | allowed | INTERMEZZO | 2 | `17... Qxb2+ 18. Kd2 cxd5 19. Qc3 c5 20. dxc5 Rfc8 21. a4 Qb4 22. Qxb4 Rxb4 23. Rc3` | [ply 32](http://localhost:5173/analysis?game_id=683321&ply=32) | [board](http://localhost:5173/analysis?fen=1r3rk1/p1p2pp1/2p1p2p/3N4/1q1P4/6QR/PPP3PP/2KR4%20b%20-%20-%200%2017) |
| 566 | missed | CLEARANCE | 2 | `13. c5 e6 14. Bc4 Kh8 15. c6 Nxc6 16. dxc6 Bxc6 17. Bd3 e5 18. Rc1 Bb7` | [ply 24](http://localhost:5173/analysis?game_id=683333&ply=24) | [board](http://localhost:5173/analysis?fen=rn1q1rk1/pbppp1bp/1p4p1/3P4/2P1N3/5N2/P3BPPP/1R1Q1RK1%20w%20-%20-%200%2013) |
| 567 | allowed | CLEARANCE | 4 | `14... Nxc6 15. Qd3 Qc7 16. Rfd1 Rad8 17. c5 e6 18. cxb6 axb6 19. Qe3 h6 20. Qxb6` | [ply 26](http://localhost:5173/analysis?game_id=683333&ply=26) | [board](http://localhost:5173/analysis?fen=rn1q1rk1/pb1pp1bp/1pP3p1/6N1/2P5/5N2/P3BPPP/1R1Q1RK1%20b%20-%20-%200%2014) |
| 568 | allowed | PIN | 0 | `16... Ba5 17. Rc1 Qe4+ 18. Kd2 Ba4 19. Qxa4 Qxf3 20. Qxa5 Qxh1 21. h4 Qg1 22. Bd3` | [ply 30](http://localhost:5173/analysis?game_id=683339&ply=30) | [board](http://localhost:5173/analysis?fen=r4rk1/pp3pp1/1bb1p1qp/3pP3/3P4/P1N2NP1/5P1P/R2QKB1R%20b%20-%20-%200%2016) |
| 569 | missed | SACRIFICE | 6 | `18. Kd2 Ba4 19. Qxa4 Qxf3 20. Qxa5 Qxh1 21. h4 Qg1 22. Bd3 Qxf2+ 23. Ne2 b5` | [ply 34](http://localhost:5173/analysis?game_id=683339&ply=34) | [board](http://localhost:5173/analysis?fen=r4rk1/pp3pp1/2b1p2p/b2pP3/3Pq3/P1N2NP1/5P1P/2RQKB1R%20w%20-%20-%200%2018) |
| 570 | allowed | CLEARANCE | 8 | `12. Nxf5 Qc7 13. Nxe7 Nxe7 14. Qc2 h5 15. d4 Nd7 16. Bd3 g6 17. a4 h4` | [ply 21](http://localhost:5173/analysis?game_id=683341&ply=21) | [board](http://localhost:5173/analysis?fen=rn2k2r/pp2bppp/1qp1p1n1/3pPb2/3N1P2/1NPPB3/PP2Q1PP/R3KB1R%20w%20-%20-%201%2012) |
| 571 | missed | CLEARANCE | 4 | `11... Qa6 12. g4 Nxf4 13. Bxf4 Bg6 14. Qd2 c5 15. Nf3 Qb6 16. Be2 a5 17. d4` | [ply 21](http://localhost:5173/analysis?game_id=683341&ply=21) | [board](http://localhost:5173/analysis?fen=rn2k2r/pp2bppp/2p1p1n1/1q1pPb2/3N1P2/1NPPB3/PP2Q1PP/R3KB1R%20b%20-%20-%200%2011) |
| 572 | allowed | PIN | 4 | `29. Qxf1 Qd8 30. Bxc6 h5 31. Ra8 Qxa8 32. Bxa8 Kh7 33. Bxd5 h4 34. Qf7 Kh6` | [ply 55](http://localhost:5173/analysis?game_id=683341&ply=55) | [board](http://localhost:5173/analysis?fen=7k/3B2pp/2p5/1p1pP1q1/1P1P4/2P3P1/4Q2P/R3Kr2%20w%20-%20-%200%2029) |
| 573 | allowed | DISCOVERED_ATTACK | 7 | `18... Bd4 19. Rb1 Nxa2 20. Bd2 f5 21. Ng5 Bxe5 22. fxe5 Rxd2 23. Rxf5 h6 24. Nf3` | [ply 34](http://localhost:5173/analysis?game_id=683347&ply=34) | [board](http://localhost:5173/analysis?fen=2krr3/ppp2ppp/1b6/4P3/1nP1NP2/1P6/P5PP/R1B2R1K%20b%20-%20-%200%2018) |
| 574 | allowed | DEFLECTION | 8 | `11... Bxg5 12. Qa4 Rc8 13. c4` | [ply 20](http://localhost:5173/analysis?game_id=683359&ply=20) | [board](http://localhost:5173/analysis?fen=r2qk2r/p3bppp/1pn4n/2ppPpB1/3P4/2P2N1P/PP3PP1/RN1QR1K1%20b%20-%20-%201%2011) |
| 575 | missed | PIN | 6 | `16. Na3 Rxe7 17. Qc8+ Nd8 18. Nb5 Qc6 19. Nxa7 Qxc8 20. Nxc8 Rxe1+ 21. Rxe1+ Kd7` | [ply 30](http://localhost:5173/analysis?game_id=683359&ply=30) | [board](http://localhost:5173/analysis?fen=4k2r/p1r1P1pp/Qpnq1p1n/2pp1pb1/3P4/2P2N1P/PP3PP1/RN2R1K1%20w%20-%20-%200%2016) |
| 576 | allowed | DISCOVERED_ATTACK | 1 | `10... axb4 11. axb4 Rxa1 12. Qxa1 Nb3 13. Qa3 Nxd2 14. Kxd2 g6 15. Bc4 Bg7 16. Qa7` | [ply 18](http://localhost:5173/analysis?game_id=683364&ply=18) | [board](http://localhost:5173/analysis?fen=r2qkbnr/1bpp1ppp/1p6/p1nP4/1P2P3/P1N2N2/3B1PPP/R2QKB1R%20b%20-%20-%200%2010) |
| 577 | missed | PIN | 4 | `28. Qd2 Nxg2 29. f3 Qh8 30. Re7 Qf6 31. Rxd7 Nf4 32. Rxc7 Bd5 33. Rc3 Qh4` | [ply 54](http://localhost:5173/analysis?game_id=683364&ply=54) | [board](http://localhost:5173/analysis?fen=q7/1bpp1p1k/1p4pp/4R3/3N1n2/3Q3P/5PP1/6K1%20w%20-%20-%200%2028) |
| 578 | allowed | DISCOVERED_CHECK | 4 | `30... Nxe3 31. Nf3 Nf1+ 32. Kg1 Nd2+ 33. Ne1 Nf3+ 34. Kf1 Kg7 35. Re3 Nxe1 36. Ke2` | [ply 58](http://localhost:5173/analysis?game_id=683364&ply=58) | [board](http://localhost:5173/analysis?fen=8/1bppRp1k/1p4pp/8/3N4/4Q2P/5PnK/q7%20b%20-%20-%201%2030) |
| 579 | missed | SACRIFICE | 6 | `30. Qb3 d5 31. Qf3 f5 32. Qg3 Qxd4 33. Re7+ Kh8 34. Re8+ Kh7 35. Qxc7+ Qg7` | [ply 58](http://localhost:5173/analysis?game_id=683364&ply=58) | [board](http://localhost:5173/analysis?fen=8/1bpp1p1k/1p4pp/4R3/3N4/4Q2P/5PnK/q7%20w%20-%20-%200%2030) |
| 580 | allowed | CLEARANCE | 4 | `26... Qa2 27. Qg5+ Kh8 28. Rb1 Rg8 29. Qxh5 Rxg2+ 30. Ke3 Qa6 31. Rg1 Rxg1 32. Rxg1` | [ply 50](http://localhost:5173/analysis?game_id=683365&ply=50) | [board](http://localhost:5173/analysis?fen=5rk1/r3pp1p/8/q1pP1Q1p/8/1pP5/1P1K2P1/3RR3%20b%20-%20-%201%2026) |
| 581 | allowed | SKEWER | 6 | `30... Qa6 31. Rg3 Qg6 32. Kd2 Rxd5+ 33. Qxd5 Qxg3 34. Re1 e6 35. Qe5+ Qxe5 36. Rxe5` | [ply 58](http://localhost:5173/analysis?game_id=683365&ply=58) | [board](http://localhost:5173/analysis?fen=5r1k/3rpp1p/8/q1pP2Qp/8/1pP1R3/1P4P1/1RK5%20b%20-%20-%201%2030) |
| 582 | missed | SKEWER | 10 | `35. Qxd2 Rxd2 36. Kxd2 Kg7 37. c4 Kf6 38. Ra5 Ke5 39. Rxc5+ Kd4 40. Rxh5 e5` | [ply 68](http://localhost:5173/analysis?game_id=683365&ply=68) | [board](http://localhost:5173/analysis?fen=3r3k/4pp1p/8/2p4p/8/1pP5/1P1r2P1/R1K1Q3%20w%20-%20-%200%2035) |
| 583 | allowed | PROMOTION | 8 | `38... Qxe5 39. dxe5 a4 40. Kh2 a3 41. Kg3 a2 42. f4 a1=Q 43. Kh4 Qe1+ 44. Kg4` | [ply 74](http://localhost:5173/analysis?game_id=683366&ply=74) | [board](http://localhost:5173/analysis?fen=8/2pkqp2/2p5/p2pQ3/3P4/2P2P1P/6P1/6K1%20b%20-%20-%201%2038) |
| 584 | allowed | PROMOTION | 10 | `40... a2 41. Kf1 Qf8 42. Kf2 Qb8 43. Qf4 Qb2+ 44. Kg3 Kc8 45. c4 a1=Q 46. cxd5` | [ply 78](http://localhost:5173/analysis?game_id=683366&ply=78) | [board](http://localhost:5173/analysis?fen=8/2pkqp2/2p5/3p4/3P4/p1P2P1P/6P1/2Q3K1%20b%20-%20-%201%2040) |
| 585 | allowed | HANGING_PIECE | 0 | `27... Nxh6 28. Rdd7 Qe5 29. h3 Kh8 30. a4 Rd6 31. g4 bxa4 32. Rxd6 Qxd6 33. Ra7` | [ply 52](http://localhost:5173/analysis?game_id=683398&ply=52) | [board](http://localhost:5173/analysis?fen=4r1k1/2R2p1p/p3r1pQ/1p3n2/1P2q3/P3P3/2P2PPP/3R2K1%20b%20-%20-%201%2027) |
| 586 | missed | CLEARANCE | 10 | `19... Bd6 20. f5 Bf4 21. Re1 e5 22. Be3 Bxe3 23. fxe3 Kf7 24. Nc3 Rhd8 25. a4` | [ply 37](http://localhost:5173/analysis?game_id=683399&ply=37) | [board](http://localhost:5173/analysis?fen=2r1kb1r/1p4pp/4pp2/3p4/2nB1P2/P6P/1P3P2/RNR3K1%20b%20-%20-%200%2019) |
| 587 | allowed | HANGING_PIECE | 0 | `22. Rxc5 Nf3+ 23. Kg2 Nh4+ 24. Kh1 Kd7 25. Nd2 g5 26. Rb5 gxf4 27. Rxb7+ Kc6` | [ply 41](http://localhost:5173/analysis?game_id=683399&ply=41) | [board](http://localhost:5173/analysis?fen=4k2r/1p4pp/4pp2/2rp4/5P2/PP5P/3n1P2/RNR3K1%20w%20-%20-%201%2022) |
| 588 | missed | SACRIFICE | 2 | `21... Kd7 22. bxc4 b5 23. Nc3 bxc4 24. Rab1 Kc6 25. Re1 Re8 26. Kf1 e5 27. Rb4` | [ply 41](http://localhost:5173/analysis?game_id=683399&ply=41) | [board](http://localhost:5173/analysis?fen=4k2r/1p4pp/4pp2/2rp4/2n2P2/PP5P/5P2/RNR3K1%20b%20-%20-%200%2021) |
| 589 | allowed | CLEARANCE | 4 | `10... Bxd3 11. cxd3 g6 12. Nge2 Bg7` | [ply 18](http://localhost:5173/analysis?game_id=683400&ply=18) | [board](http://localhost:5173/analysis?fen=rn2kb1r/pp1n1pp1/1qp1p1b1/3p2Pp/3P1B1P/P1NBPP2/1PP5/R2QK1NR%20b%20-%20-%200%2010) |
| 590 | missed | CLEARANCE | 8 | `17... c6 18. a4 Rce8 19. Rc5 Nc8 20. Qc2 Nd6 21. b4 Ra8 22. h3 Qf6 23. Ne5` | [ply 33](http://localhost:5173/analysis?game_id=683411&ply=33) | [board](http://localhost:5173/analysis?fen=2r2rk1/npp1qpp1/p3b2p/3p4/3P4/PQ1BPN2/1PR2PPP/2R3K1%20b%20-%20-%200%2017) |
| 591 | allowed | PROMOTION | 8 | `46. Re6+ Kd3 47. d5 Ra1 48. d6 Rxa6 49. d7 Rxe6 50. d8=Q+ Ke2 51. Qg5 Rxe3+` | [ply 89](http://localhost:5173/analysis?game_id=683411&ply=89) | [board](http://localhost:5173/analysis?fen=8/6p1/P2R4/7p/3PkPp1/4P1K1/r7/8%20w%20-%20-%201%2046) |
| 592 | missed | PIN | 2 | `45... g6 46. Rc6 Ra3 47. Rc5+ Kf6 48. Rc6+` | [ply 89](http://localhost:5173/analysis?game_id=683411&ply=89) | [board](http://localhost:5173/analysis?fen=8/6p1/P2R4/5k1p/3P1Pp1/4P1K1/r7/8%20b%20-%20-%200%2045) |
| 593 | missed | SKEWER | 10 | `51... Rf1+ 52. Ke5 Re1 53. d5 Rxe4+ 54. Kd6 Ra4 55. Kc5 Ra5+ 56. Kb6 Rxd5 57. a7` | [ply 101](http://localhost:5173/analysis?game_id=683411&ply=101) | [board](http://localhost:5173/analysis?fen=8/6p1/P3R3/5P1p/3PPKp1/3k4/8/6r1%20b%20-%20-%200%2051) |
| 594 | allowed | PIN | 8 | `13. Bxd5 Nb4 14. N2c3 c6 15. Bc4 Qd4 16. h5 b5 17. hxg6 Bxg6 18. Be2 a5` | [ply 23](http://localhost:5173/analysis?game_id=683426&ply=23) | [board](http://localhost:5173/analysis?fen=r2q1rk1/1pp2pbp/p1n3p1/3npbP1/2B1N2P/1P3Q2/PBPPNP2/2KR3R%20w%20-%20-%200%2013) |
| 595 | allowed | CLEARANCE | 6 | `29. dxc3 Ne6 30. Qg3 Nf4 31. c4 Kg8 32. Qc3 Re8 33. Rhf1 b4 34. axb4 Ne2` | [ply 55](http://localhost:5173/analysis?game_id=683426&ply=55) | [board](http://localhost:5173/analysis?fen=r2r3k/2p2p1p/q5pP/1p2p1P1/3nP3/PPbQ4/1B1P4/1K1R3R%20w%20-%20-%200%2029) |
| 596 | missed | DISCOVERED_ATTACK | 7 | `29... Kg8 30. b4 Qe6 31. Qh3 Qe7 32. Rc1 Ne6 33. Rc6 Rxd2 34. Rhc1 Rad8 35. Qg3` | [ply 57](http://localhost:5173/analysis?game_id=683426&ply=57) | [board](http://localhost:5173/analysis?fen=r2r3k/2p2p1p/q5pP/1p2p1P1/3nP3/PPQ5/1B1P4/1K1R3R%20b%20-%20-%200%2029) |
| 597 | allowed | SACRIFICE | 2 | `34. Qxe5 Nxc1 35. Rf1 f5 36. Rxc1 f4 37. Qh8+ Kf7 38. Qxh7+ Ke8 39. Qg8+ Ke7` | [ply 65](http://localhost:5173/analysis?game_id=683426&ply=65) | [board](http://localhost:5173/analysis?fen=r1r3k1/q4p1p/2p2RpP/1p2p1P1/4P3/PPQP4/1B2n3/1KR5%20w%20-%20-%201%2034) |
| 598 | allowed | SKEWER | 6 | `36. Rxc6 Kf8 37. Rxc8+ Rxc8 38. Qh8+ Ke7 39. Qxc8 bxa3 40. Ka2 Qf2+ 41. Kxa3 Qd4` | [ply 69](http://localhost:5173/analysis?game_id=683426&ply=69) | [board](http://localhost:5173/analysis?fen=r1r3k1/q4p1p/2p2RpP/4Q1P1/1p2P3/PP1P4/8/1KB5%20w%20-%20-%200%2036) |
| 599 | missed | SACRIFICE | 6 | `36... Kf8 37. Rxc8+ Rxc8 38. Qh8+ Ke7 39. Qxc8 bxa3 40. Qc3 Kd7 41. d4 f5 42. Qc4` | [ply 71](http://localhost:5173/analysis?game_id=683426&ply=71) | [board](http://localhost:5173/analysis?fen=r1r3k1/q4p1p/2R3pP/4Q1P1/1p2P3/PP1P4/8/1KB5%20b%20-%20-%200%2036) |
| 600 | missed | CLEARANCE | 10 | `15... Kd7 16. a4 bxa4 17. N2b3 Ng6 18. Nxf5 exf5 19. f4 Be7 20. Nd4 Rhb8 21. Nxf5` | [ply 29](http://localhost:5173/analysis?game_id=683441&ply=29) | [board](http://localhost:5173/analysis?fen=r3kb1r/4nppp/2p1p3/1p1pPb2/3N4/2P1B3/P2N1PPP/R4RK1%20b%20-%20-%200%2015) |
| 601 | allowed | FORK | 0 | `18. Nd6+ Kd7 19. Nxc8 Kxc8 20. Bg5 Nc6 21. f4 h6 22. Bh4 Rg8 23. Rf3 g5` | [ply 33](http://localhost:5173/analysis?game_id=683441&ply=33) | [board](http://localhost:5173/analysis?fen=2r1kb1r/4nppp/4p3/1Np1Pb2/2Pp4/4B3/P2N1PPP/R4RK1%20w%20-%20-%200%2018) |
| 602 | missed | TRAPPED_PIECE | 2 | `20... f6 21. a4 fxg5 22. a5 Kd7 23. a6 Ra8 24. a7 Ne5 25. Ra6 Bd3 26. Rc1` | [ply 39](http://localhost:5173/analysis?game_id=683441&ply=39) | [board](http://localhost:5173/analysis?fen=2r1k2r/5ppp/3Pp1n1/2p2bB1/2Pp4/8/P2N1PPP/R4RK1%20b%20-%20-%200%2020) |
| 603 | allowed | CLEARANCE | 2 | `14. c4 Qa5 15. Qc2 Bg6 16. Qb3 Nc3 17. Bd1 Nxd1 18. Rfxd1 Qa6 19. Rac1 Na5` | [ply 25](http://localhost:5173/analysis?game_id=683463&ply=25) | [board](http://localhost:5173/analysis?fen=r4rk1/pp3ppp/2n1p3/3q3b/3Pn3/P3BN1P/2P1BPP1/R2Q1RK1%20w%20-%20-%200%2014) |
| 604 | allowed | FORK | 0 | `16. g4 Bxg4 17. hxg4 Qxg4 18. Qd3 Nc5 19. Qc3 Qh5+ 20. Nh2 Qxe2 21. dxc5 f6` | [ply 29](http://localhost:5173/analysis?game_id=683463&ply=29) | [board](http://localhost:5173/analysis?fen=3r1rk1/pp3ppp/2n1p3/5q1b/2PPn3/P3BN1P/4BPP1/R2Q1R1K%20w%20-%20-%201%2016) |
| 605 | allowed | CLEARANCE | 10 | `8... f6 9. exf6 Nxf6 10. Bd3 d6` | [ply 14](http://localhost:5173/analysis?game_id=683473&ply=14) | [board](http://localhost:5173/analysis?fen=r1b1k2r/ppppqppp/2n5/4P1Bn/4P3/P1P2N2/1PP3PP/R2QKB1R%20b%20-%20-%201%208) |
| 606 | missed | ATTRACTION | 2 | `15. Qh5 Qf7 16. Qxf7+ Kxf7 17. Rf1+ Ke7 18. Nf5+ Kf7 19. Nxh6+ Kg6 20. Nf5 b6` | [ply 28](http://localhost:5173/analysis?game_id=683473&ply=28) | [board](http://localhost:5173/analysis?fen=r1b2qk1/pppp2p1/2n4p/8/3NP3/P1PB4/1PP3PP/R2Q2K1%20w%20-%20-%200%2015) |
| 607 | allowed | FORK | 4 | `18... Nxe4 19. Qxb4 Qxb4 20. Bxb4 Nf2 21. Bxf5 Nf6 22. Bd3 Ba6 23. c4 Nxh1 24. Rxh1` | [ply 34](http://localhost:5173/analysis?game_id=683493&ply=34) | [board](http://localhost:5173/analysis?fen=r1b1k2r/3n2pp/1qpBBn2/5p2/pp2P3/4P3/PPPQ2PP/1NKR3R%20b%20-%20-%201%2018) |
| 608 | missed | FORK | 6 | `21... f5 22. Kg2 Na5 23. Rhf1 Nc4 24. Kh1 Nd2 25. gxf5 Qf6 26. Qg3 Nxf1 27. Rxf1` | [ply 41](http://localhost:5173/analysis?game_id=683513&ply=41) | [board](http://localhost:5173/analysis?fen=4rr2/pp3ppk/2n1q2p/3p3P/3P2P1/P1P1PQ2/5K1N/R6R%20b%20-%20-%200%2021) |
| 609 | allowed | CLEARANCE | 2 | `16... f5 17. Re1 Rf7 18. h4 Raf8 19. h5 Rg7 20. hxg6 hxg6 21. Rh3 Nd8 22. Qg5` | [ply 30](http://localhost:5173/analysis?game_id=683526&ply=30) | [board](http://localhost:5173/analysis?fen=r4rk1/pp3p1p/2nqp1pQ/3p4/3P4/2PB1R2/PP4PP/R5K1%20b%20-%20-%201%2016) |
| 610 | allowed | CLEARANCE | 6 | `36... Kh6 37. Kxb6 a4 38. Bb5 Ne4 39. Qd4 Qc1 40. c4 a3 41. bxa3 Qxa3 42. c5` | [ply 70](http://localhost:5173/analysis?game_id=683526&ply=70) | [board](http://localhost:5173/analysis?fen=8/3Q2kp/1p4p1/pK3pq1/8/2PB3P/PP1n4/8%20b%20-%20-%201%2036) |
| 611 | allowed | DISCOVERED_CHECK | 0 | `37... f4+ 38. Bd5 f3 39. Qf7 Qf5 40. Qxf5 gxf5 41. Bxf3 Nxf3 42. Kxb6 f4 43. Kc5` | [ply 72](http://localhost:5173/analysis?game_id=683526&ply=72) | [board](http://localhost:5173/analysis?fen=8/3Q3p/1p4pk/pK3pq1/2B5/2P4P/PP1n4/8%20b%20-%20-%201%2037) |
| 612 | missed | PIN | 8 | `8. d5 exd5 9. Nxd5 Bb4+ 10. c3 Bd6 11. Qe2+ Nge7 12. Bxd6 cxd6` | [ply 14](http://localhost:5173/analysis?game_id=683536&ply=14) | [board](http://localhost:5173/analysis?fen=r2qkbnr/pppb2pp/2n1pp2/1B6/3P1B2/2N2N2/PPP3PP/R2QK2R%20w%20-%20-%200%208) |
| 613 | allowed | HANGING_PIECE | 0 | `22... Rfxf7 23. Rd6 Rxd6 24. Qxd6 Qc5 25. Kb2 g5 26. Rd5 Qxd6 27. Rxd6 Kg7 28. Rxb6` | [ply 42](http://localhost:5173/analysis?game_id=683536&ply=42) | [board](http://localhost:5173/analysis?fen=5r1k/1pqr1Np1/1p2Rp1p/3Q4/8/1P6/P1P3PP/1K1R4%20b%20-%20-%201%2022) |
| 614 | allowed | INTERMEZZO | 2 | `20. Be3 Rfc8 21. Qxd4 Qxd4 22. Bxd4 Rc4 23. Be3 h6 24. Rfd1 a6 25. Kf1 Rb8` | [ply 37](http://localhost:5173/analysis?game_id=683545&ply=37) | [board](http://localhost:5173/analysis?fen=r4rk1/p4ppp/4p3/3pP3/q2n2Q1/8/P2B1PPP/R4RK1%20w%20-%20-%200%2020) |
| 615 | allowed | FORK | 0 | `9. Qxd5 Qxd5 10. Nxd5 e5 11. Bxe5 Nc6 12. Nf3 Bb4+ 13. Nxb4 Nxb4 14. Rc1 Nd3+` | [ply 15](http://localhost:5173/analysis?game_id=683546&ply=15) | [board](http://localhost:5173/analysis?fen=rnb1kb1r/p3pppp/8/q2p4/2p1nB2/2N5/PP3PPP/R2QKBNR%20w%20-%20-%200%209) |
| 616 | allowed | TRAPPED_PIECE | 10 | `14. Bxc4 Be7 15. Nf3` | [ply 25](http://localhost:5173/analysis?game_id=683546&ply=25) | [board](http://localhost:5173/analysis?fen=rn2kb1r/p4ppp/4p3/8/b1ppPB2/P7/1P4PP/R3KBNR%20w%20-%20-%200%2014) |
| 617 | missed | CLEARANCE | 10 | `13... Bc5 14. Ne2` | [ply 25](http://localhost:5173/analysis?game_id=683546&ply=25) | [board](http://localhost:5173/analysis?fen=rn2kb1r/p4ppp/4p3/3p4/b1p1PB2/P7/1P4PP/R3KBNR%20b%20-%20-%200%2013) |
| 618 | missed | CAPTURING_DEFENDER | 8 | `18... Nc6 19. Nc1` | [ply 35](http://localhost:5173/analysis?game_id=683546&ply=35) | [board](http://localhost:5173/analysis?fen=rn2k2r/p4ppp/1b2p3/8/bPRpPB2/8/4N1PP/4KB1R%20b%20-%20-%200%2018) |
| 619 | missed | PIN | 6 | `24. Rc8 Qa5 25. Nxe7+ Kg7 26. Rxf8 Kxf8 27. Qxg6 f6 28. Qh7 Rg5 29. Rc1 Bc5` | [ply 46](http://localhost:5173/analysis?game_id=683549&ply=46) | [board](http://localhost:5173/analysis?fen=3q1rk1/1p2pp2/p2p2p1/1r1N4/3bP1Q1/7P/6P1/2R2R1K%20w%20-%20-%200%2024) |
| 620 | allowed | SACRIFICE | 6 | `25... Bf6 26. Rxe7 Rxd5 27. Rxe8+ Qxe8 28. exd5 Be5 29. Qg4 Kg7 30. h4 b5 31. g3` | [ply 48](http://localhost:5173/analysis?game_id=683549&ply=48) | [board](http://localhost:5173/analysis?fen=3qr1k1/1pR1pp2/p2p2p1/1r1N4/3bPQ2/7P/6P1/5R1K%20b%20-%20-%201%2025) |
| 621 | missed | PIN | 6 | `25. Rd7 Qc8 26. Rxe7 Rxd5 27. exd5 Be5 28. Qxc8 Rxc8 29. Rxb7 a5 30. Rbxf7 Ra8` | [ply 48](http://localhost:5173/analysis?game_id=683549&ply=48) | [board](http://localhost:5173/analysis?fen=3qr1k1/1pR1pp2/p2p2p1/1r1N4/3bP1Q1/7P/6P1/5R1K%20w%20-%20-%200%2025) |
| 622 | missed | CLEARANCE | 2 | `34. Ra7 Ra1 35. Reb7 Kg7 36. e6 Kf6 37. exf7 Kg7 38. Ra6 Rxf7 39. Rbb6 Kg8` | [ply 66](http://localhost:5173/analysis?game_id=683549&ply=66) | [board](http://localhost:5173/analysis?fen=5rk1/2R1Rp2/6p1/p3P3/1p6/7P/6PK/4r3%20w%20-%20-%200%2034) |
| 623 | allowed | CLEARANCE | 2 | `59... Kf1 60. Kf4 g1=Q 61. Ke5 Qc5+ 62. Kf6 Qd6+ 63. Kf5 Qe7 64. Kg4 Kf2 65. Kf4` | [ply 116](http://localhost:5173/analysis?game_id=683549&ply=116) | [board](http://localhost:5173/analysis?fen=8/8/8/8/8/6K1/6p1/6k1%20b%20-%20-%201%2059) |
| 624 | missed | DISCOVERED_ATTACK | 3 | `9. Be5 Bxe5 10. dxe5 Be6 11. Qxd5 Bxd5 12. Rc1 Nd7 13. Bb5 Bxf3 14. gxf3 Nxe5` | [ply 16](http://localhost:5173/analysis?game_id=683556&ply=16) | [board](http://localhost:5173/analysis?fen=rnb2rk1/pp2ppbp/6p1/2pq4/3P1B2/4PN2/PP3PPP/R2QKB1R%20w%20-%20-%200%209) |
| 625 | allowed | CLEARANCE | 10 | `29... Qa1 30. Qd2 Be5+ 31. g3 Bc3 32. Qe2 Rfd8 33. Rd3 Rxd3 34. Bxd3 Rd8 35. h4` | [ply 56](http://localhost:5173/analysis?game_id=683556&ply=56) | [board](http://localhost:5173/analysis?fen=1r3r1k/3R2bp/6p1/3Q4/2B5/1P2P2P/P5PK/5q2%20b%20-%20-%201%2029) |
| 626 | allowed | DISCOVERED_CHECK | 2 | `10. Nxc6 Qc8 11. Ne5+ axb5 12. Qxb5+ Nd7 13. Na4 Rxa4 14. Qxa4 f6 15. Nxd7 Qxd7` | [ply 17](http://localhost:5173/analysis?game_id=683558&ply=17) | [board](http://localhost:5173/analysis?fen=r3kb1r/1pq2ppp/p1n1pn2/1B1pNb2/Q2P4/2N1P3/PP3PPP/R1B1K2R%20w%20-%20-%200%2010) |
| 627 | missed | PROMOTION | 2 | `48... Kg8 49. b5 h1=Q 50. Qxh1 Bxh1 51. b6 Kg7 52. b7 Be4 53. Kd4 Bf5 54. b8=Q` | [ply 95](http://localhost:5173/analysis?game_id=683558&ply=95) | [board](http://localhost:5173/analysis?fen=8/5pk1/6p1/3N4/1PK5/5b2/7p/Q7%20b%20-%20-%200%2048) |
| 628 | missed | PROMOTION | 2 | `49... g5 50. b5 h1=Q 51. Qxh1+ Bxh1 52. b6 Bxd5+ 53. Kxd5 Kh5 54. b7 Kg4 55. b8=Q` | [ply 97](http://localhost:5173/analysis?game_id=683558&ply=97) | [board](http://localhost:5173/analysis?fen=8/5p2/6pk/3N4/1PK5/5b2/7p/2Q5%20b%20-%20-%200%2049) |
| 629 | allowed | PIN | 10 | `6. dxe5 Nxe5` | [ply 9](http://localhost:5173/analysis?game_id=683559&ply=9) | [board](http://localhost:5173/analysis?fen=r2qkbnr/ppp2ppp/2n5/3pp3/3P4/5PP1/PPP2PBP/RNBQK2R%20w%20-%20-%200%206) |
| 630 | allowed | PIN | 2 | `8... dxe4 9. Nxe4 Re8 10. Bd3 Nc6` | [ply 14](http://localhost:5173/analysis?game_id=683562&ply=14) | [board](http://localhost:5173/analysis?fen=rnbq1rk1/ppp2ppp/5b2/3p4/3PP3/2N2N2/PP3PPP/R2QKB1R%20b%20-%20-%200%208) |
| 631 | missed | CLEARANCE | 2 | `8. e3 g6 9. Bd3 a5 10. h3 c6` | [ply 14](http://localhost:5173/analysis?game_id=683562&ply=14) | [board](http://localhost:5173/analysis?fen=rnbq1rk1/ppp2ppp/5b2/3p4/3P4/2N2N2/PP2PPPP/R2QKB1R%20w%20-%20-%200%208) |
| 632 | missed | HANGING_PIECE | 0 | `14. gxf3 Nc6 15. Rad1 Qh4 16. Bc4 Qf4 17. Kg2 Be5 18. Rh1 Na5 19. Qc2 Nxc4` | [ply 26](http://localhost:5173/analysis?game_id=683562&ply=26) | [board](http://localhost:5173/analysis?fen=rn1qr1k1/ppp2ppp/8/8/3bN3/1Q1B1b1P/PP3PP1/R4RK1%20w%20-%20-%200%2014) |
| 633 | missed | SACRIFICE | 10 | `14... Rc8 15. Re3 Rc4 16. Rb1 h6 17. Bxf6 Qxf6 18. Rxb7 Rf4 19. Rxa7 Rb8 20. Re1` | [ply 27](http://localhost:5173/analysis?game_id=683570&ply=27) | [board](http://localhost:5173/analysis?fen=r2q1rk1/pp3ppp/4pn2/3p2B1/8/2P3Q1/P1P2PPP/R3R1K1%20b%20-%20-%200%2014) |
| 634 | allowed | CLEARANCE | 8 | `42... Rf8 43. h4 Rc8 44. Kg1 Qc3 45. h5 Qf6 46. Qa1 Rc3 47. Rf3 Qe5 48. Qa4` | [ply 82](http://localhost:5173/analysis?game_id=683578&ply=82) | [board](http://localhost:5173/analysis?fen=8/6pk/4pr1p/3p1p2/2q5/4P3/6PP/4QR1K%20b%20-%20-%201%2042) |
| 635 | allowed | PIN | 0 | `42. Kc6 e5 43. d5 f4 44. gxf4 Qxb7+ 45. Kxb7 exf4 46. d6 f3 47. d7 f2` | [ply 81](http://localhost:5173/analysis?game_id=683627&ply=81) | [board](http://localhost:5173/analysis?fen=8/pQ1K2qk/4pp2/5p2/1P1P4/2P3P1/8/8%20w%20-%20-%200%2042) |
| 636 | allowed | PIN | 10 | `45. d6 f4 46. gxf4 Kg6 47. d7 a5 48. d8=Q axb4 49. cxb4 Kf5 50. Qd5 Kxf4` | [ply 87](http://localhost:5173/analysis?game_id=683627&ply=87) | [board](http://localhost:5173/analysis?fen=8/pK4k1/5p2/3Ppp2/1P6/2P3P1/8/8%20w%20-%20-%201%2045) |
| 637 | allowed | CLEARANCE | 2 | `23. Ba3 Nf4 24. Rad1 g5 25. fxg6 hxg6 26. Rxd7 Rxd7 27. Kf3 g5 28. Rd1 Rxd1` | [ply 43](http://localhost:5173/analysis?game_id=683636&ply=43) | [board](http://localhost:5173/analysis?fen=3r2k1/p1br1ppp/Pp3n2/1P2pP2/2N1P1P1/2PnK2P/2B5/R1B4R%20w%20-%20-%201%2023) |
| 638 | missed | FORK | 0 | `27... Ne1+ 28. Kf2 Nxc2 29. Ra2 Rd3 30. Rxc2 Ng3 31. Nd2 Bd6 32. Kg2 f6 33. Nc4` | [ply 53](http://localhost:5173/analysis?game_id=683636&ply=53) | [board](http://localhost:5173/analysis?fen=6k1/p1br1ppp/Pp6/1P2pPPn/2N1P2P/2P2K2/2B3n1/R1B5%20b%20-%20-%200%2027) |
| 639 | allowed | DISCOVERED_CHECK | 6 | `34. Nxd6 Re7 35. Bb3 Kf8 36. Rxf7+ Rxf7 37. Nxf7+ Ke8 38. Bd5 Kd7 39. Kh6 Ke8` | [ply 65](http://localhost:5173/analysis?game_id=683636&ply=65) | [board](http://localhost:5173/analysis?fen=8/p2r1pkp/Pp1b4/1P2p1PK/2N1P3/B1P2R2/2B5/8%20w%20-%20-%201%2034) |
| 640 | allowed | INTERMEZZO | 6 | `16. cxd5 Nf4 17. Qc4 Nxd5 18. Na4 Qb4 19. Bxd5 exd5 20. Qxc5 Qxa4 21. Qxd5 Rad8` | [ply 29](http://localhost:5173/analysis?game_id=683637&ply=29) | [board](http://localhost:5173/analysis?fen=r4rk1/pp3ppp/1q2p1n1/2bp4/2P5/2N2B2/PP2QPPP/R4RK1%20w%20-%20-%201%2016) |
| 641 | allowed | CLEARANCE | 4 | `17... Bxb4 18. cxb4 Nb6 19. e4 Qd7 20. Ra5 Rb8 21. Bf4 Rb7 22. Qa2` | [ply 32](http://localhost:5173/analysis?game_id=683642&ply=32) | [board](http://localhost:5173/analysis?fen=r3kb1r/p2n2pp/2p1pp2/3q4/1RpP4/2P1PN1P/3BQPP1/R5K1%20b%20-%20-%201%2017) |
| 642 | allowed | CLEARANCE | 4 | `16. axb5 axb5 17. Qd3 Qb8 18. Rfc1 Qb6 19. Qxb5 Qxd4 20. Na4 Ne5 21. c3 Qc4` | [ply 29](http://localhost:5173/analysis?game_id=683643&ply=29) | [board](http://localhost:5173/analysis?fen=2r2rk1/5ppp/p1nqpn2/1p1p4/P2P4/2N3NP/1PP2PP1/R2Q1RK1%20w%20-%20-%200%2016) |
| 643 | missed | DISCOVERED_ATTACK | 7 | `15... Qb4 16. Nge2 Qxb2 17. Rb1 Qa3 18. Rxb7 Na5 19. Ra7 Rxc3 20. Nxc3 Qxc3 21. Qd3` | [ply 29](http://localhost:5173/analysis?game_id=683643&ply=29) | [board](http://localhost:5173/analysis?fen=2r2rk1/1p3ppp/p1nqpn2/3p4/P2P4/2N3NP/1PP2PP1/R2Q1RK1%20b%20-%20-%200%2015) |
| 644 | allowed | CLEARANCE | 4 | `13. Ke2 Qc7 14. c4 Bd6 15. Qb3 a5 16. Rad1 a4 17. Qd3 b5 18. c5 Be7` | [ply 23](http://localhost:5173/analysis?game_id=683652&ply=23) | [board](http://localhost:5173/analysis?fen=r2qkb1r/pp3pp1/2p1pnp1/8/3P2P1/4BN1P/PPP2P2/R2QK2R%20w%20-%20-%200%2013) |
| 645 | allowed | CLEARANCE | 8 | `15. Qe2 b5 16. a3 Be7 17. Ne5 Qd5 18. Kb1 Ne4 19. Bc1 Nd6 20. f3 Rd8` | [ply 27](http://localhost:5173/analysis?game_id=683652&ply=27) | [board](http://localhost:5173/analysis?fen=r2qk2r/1p3pp1/2p1pnp1/p7/1b1P2P1/4BN1P/PPPQ1P2/2KR3R%20w%20-%20-%201%2015) |
| 646 | missed | FORK | 4 | `20... Qb5 21. Rdg1 Qd5 22. Rxg4 Qxf3 23. Rgh4 Rac8 24. R4h3 Qd5 25. a4 Qf5 26. Qe3` | [ply 39](http://localhost:5173/analysis?game_id=683652&ply=39) | [board](http://localhost:5173/analysis?fen=r4rk1/1p3p2/1qpbp1pB/p7/3P2n1/2P2N2/PP1Q1P2/2KR3R%20b%20-%20-%200%2020) |
| 647 | missed | PIN | 2 | `15... dxe3 16. Bxe3 Neg4 17. fxg4 Rxe3+ 18. Kf1 Qxg4 19. Nc4 Bxg3 20. hxg3 Rxg3 21. Re1` | [ply 29](http://localhost:5173/analysis?game_id=683660&ply=29) | [board](http://localhost:5173/analysis?fen=2r1r1k1/p2q1ppp/1p1b1n2/2p1n3/3p4/PPP1PPN1/2QN1BPP/R3K2R%20b%20-%20-%200%2015) |
| 648 | missed | FORK | 2 | `19... Nce2 20. Nxe2 d3 21. Qd2 Nxe2 22. Qxd3 Nxg1 23. Nc3 Rcd8 24. Nd5 Nxf3+ 25. gxf3` | [ply 37](http://localhost:5173/analysis?game_id=683660&ply=37) | [board](http://localhost:5173/analysis?fen=2r1r1k1/p2q1ppp/1p1b4/2p5/2PpPn2/PPn2PN1/2Q2BPP/RN2K1R1%20b%20-%20-%200%2019) |
| 649 | missed | SACRIFICE | 4 | `46... a6 47. Qxb6 Bg7 48. Qxc5 Kg8 49. Qc8+ Kh7 50. Qd7 Kh8 51. Qe8+ Kh7 52. Qf7` | [ply 91](http://localhost:5173/analysis?game_id=683660&ply=91) | [board](http://localhost:5173/analysis?fen=8/p4k2/1p4p1/2pN4/P1PbKPP1/1Q6/8/8%20b%20-%20-%200%2046) |
| 650 | allowed | MATE | 10 | `48. Qb5 Bg7 49. axb6 Bf6 50. b7 Be7 51. b8=Q+ Ke6 52. Q5e8 g5 53. Qxe7#` | [ply 93](http://localhost:5173/analysis?game_id=683660&ply=93) | [board](http://localhost:5173/analysis?fen=8/p7/1p1k2p1/P1pN4/2PbKPP1/1Q6/8/8%20w%20-%20-%201%2048) |
| 651 | allowed | DISCOVERED_ATTACK | 1 | `4... dxe4 5. Nxe4 Qxd4 6. Nf3 Qd5 7. c4 Qd8 8. Nxf6+ exf6` | [ply 6](http://localhost:5173/analysis?game_id=683679&ply=6) | [board](http://localhost:5173/analysis?fen=rnbqkb1r/pp2pppp/2p2n2/3p4/3PP3/2NB4/PPP2PPP/R1BQK1NR%20b%20-%20-%201%204) |
| 652 | missed | DEFLECTION | 4 | `26. Qh5+ g6 27. Qh7+ Ke8 28. Bxg6+ Kd8 29. Qh5 Rf8 30. Be4 Bd7 31. Qe5 Qf6` | [ply 50](http://localhost:5173/analysis?game_id=683690&ply=50) | [board](http://localhost:5173/analysis?fen=r1b5/4qkpQ/2p1pr2/1p6/3P4/p1P5/P1B2PPP/R3R1K1%20w%20-%20-%200%2026) |
| 653 | allowed | MATE | 10 | `22... Nxd3 23. Rh3+ Rh4 24. Rxh4+ Qxh4+ 25. Kg2 Qg4+ 26. Kh1 Nf4 27. Kh2 Qg2#` | [ply 42](http://localhost:5173/analysis?game_id=683721&ply=42) | [board](http://localhost:5173/analysis?fen=r7/pp4pk/8/3Pn3/5r2/2PQR3/P1P2q2/R6K%20b%20-%20-%200%2022) |
| 654 | missed | CLEARANCE | 2 | `22. Rh3+ Rh4 23. Qe3 Qxe3 24. Rxh4+ Kg8 25. Rf1 Nf3 26. Rh3 dxe4 27. Kg2 Qe2+` | [ply 42](http://localhost:5173/analysis?game_id=683721&ply=42) | [board](http://localhost:5173/analysis?fen=r7/pp4pk/8/3pn3/4Pr2/2PQR3/P1P2q2/R6K%20w%20-%20-%200%2022) |
| 655 | missed | SACRIFICE | 6 | `23. Rf1 Rh4+ 24. Rh3 Nxd3 25. Rxf2 Nxf2+ 26. Kg2 Nxh3 27. d6 Ng5 28. Kg3 Rh6` | [ply 44](http://localhost:5173/analysis?game_id=683721&ply=44) | [board](http://localhost:5173/analysis?fen=r5k1/pp4p1/8/3Pn3/5r2/2PQR3/P1P2q2/R6K%20w%20-%20-%200%2023) |
| 656 | allowed | PIN | 8 | `2... exd4 3. Nf3 Bb4+ 4. c3 dxc3 5. Nxc3 Nf6 6. e5 Ne4 7. Qc2 d5 8. Bd3` | [ply 2](http://localhost:5173/analysis?game_id=683725&ply=2) | [board](http://localhost:5173/analysis?fen=rnbqkbnr/pppp1ppp/8/4p3/3PP3/8/PPP2PPP/RNBQKBNR%20b%20-%20-%200%202) |
| 657 | missed | CLEARANCE | 6 | `2. dxe5 Nc6 3. Nf3 h6 4. e4 d6 5. Bb5 Bd7 6. Bxc6 Bxc6 7. Nc3 dxe5` | [ply 2](http://localhost:5173/analysis?game_id=683725&ply=2) | [board](http://localhost:5173/analysis?fen=rnbqkbnr/pppp1ppp/8/4p3/3P4/8/PPP1PPPP/RNBQKBNR%20w%20-%20-%200%202) |
| 658 | allowed | SACRIFICE | 4 | `8... Nxe4 9. Bxe4 Bxc3+ 10. bxc3 d5` | [ply 14](http://localhost:5173/analysis?game_id=683725&ply=14) | [board](http://localhost:5173/analysis?fen=r1bqr1k1/pppp1ppp/2n2n2/8/1b2P3/2NB2N1/PPP2PPP/R1BQK2R%20b%20-%20-%201%208) |
| 659 | allowed | ATTRACTION | 4 | `16... Nf3+ 17. Kh1 Nh4 18. Qg5 Nxg2 19. Kxg2 Bf3+ 20. Kg1 Re5 21. Qh4 h5 22. Nh1` | [ply 30](http://localhost:5173/analysis?game_id=683725&ply=30) | [board](http://localhost:5173/analysis?fen=3rr1k1/pppq1ppp/5n2/4n3/P3p1b1/BBP1Q1N1/2P2PPP/R4RK1%20b%20-%20-%201%2016) |
| 660 | allowed | SACRIFICE | 6 | `28. f3 Ne5 29. Qc7 Ng6 30. dxe6 Rxd1 31. exf7+ Kh7 32. Rxd1 Qf5 33. f8=N+ Qxf8` | [ply 53](http://localhost:5173/analysis?game_id=683727&ply=53) | [board](http://localhost:5173/analysis?fen=3r2k1/p4pp1/1pQ1pq1p/3P4/2P3n1/1P6/P4PPP/3RR1K1%20w%20-%20-%201%2028) |
| 661 | allowed | HANGING_PIECE | 0 | `34. Kxe2 Qe4+ 35. Kf1 Qc2 36. Re1 exd5 37. Re2 Qb1+ 38. Re1 Qc2` | [ply 65](http://localhost:5173/analysis?game_id=683727&ply=65) | [board](http://localhost:5173/analysis?fen=5rk1/p1Q2pp1/1p2p2p/3P4/2P4q/1P5P/P3nPP1/3R1K2%20w%20-%20-%201%2034) |
| 662 | allowed | CLEARANCE | 10 | `28. R5xe4 dxe4 29. Bxe6+ Kh7 30. d5 h5 31. gxh5 Kh6 32. Kf2 Kxh5 33. Rg1 Kh4` | [ply 53](http://localhost:5173/analysis?game_id=683737&ply=53) | [board](http://localhost:5173/analysis?fen=4rrk1/6p1/p3pp1p/1p1pRP2/3Pb1P1/1BP4P/PP6/4R1K1%20w%20-%20-%200%2028) |
| 663 | allowed | FORK | 2 | `7... d5 8. Bd3 dxe4 9. Nxe4 Nbd7` | [ply 12](http://localhost:5173/analysis?game_id=683743&ply=12) | [board](http://localhost:5173/analysis?fen=rnb1kb1r/pp1p1ppp/1qp1pn2/8/2PPP3/P1N2N2/1P1B1PPP/R2QKB1R%20b%20-%20-%201%207) |
| 664 | missed | SKEWER | 8 | `14. g3 Qe7 15. Rae1 Rae8 16. Qg2 Qd7 17. a4 Ne7 18. Qxb7 Qxa4 19. Bd2 Nd5` | [ply 26](http://localhost:5173/analysis?game_id=683749&ply=26) | [board](http://localhost:5173/analysis?fen=r4rk1/1pp2ppp/p1nbp3/8/3P3q/2PBBQ2/PP4PP/R4RK1%20w%20-%20-%200%2014) |
| 665 | missed | DISCOVERED_ATTACK | 5 | `33... Qh4+ 34. Kf1 Qxh2 35. b4 Rg5 36. Qf2 Qxd6 37. b5 Rh5 38. Kg1 Qh2+ 39. Kf1` | [ply 65](http://localhost:5173/analysis?game_id=683755&ply=65) | [board](http://localhost:5173/analysis?fen=r5k1/5ppp/p2N1n2/R2pr3/2q5/2P2P2/1PQ2KPP/R7%20b%20-%20-%200%2033) |
| 666 | missed | CLEARANCE | 4 | `17... Bg6 18. e4 f6 19. Rd2 Bf7 20. Nf5 a5 21. Rhd1 Kf8 22. f4 Nc4 23. Rd7` | [ply 33](http://localhost:5173/analysis?game_id=683759&ply=33) | [board](http://localhost:5173/analysis?fen=r3r1k1/1pp2ppp/p7/2P1nb2/8/P1B1P1N1/1P3PPP/2KR3R%20b%20-%20-%200%2017) |
| 667 | allowed | DISCOVERED_ATTACK | 7 | `14. Ne4 Qe6 15. Nxd6 Qxd6 16. Bg2 h6 17. Nh4 a5 18. Bxc6 Qxc6 19. Qe4 Ra6` | [ply 25](http://localhost:5173/analysis?game_id=683766&ply=25) | [board](http://localhost:5173/analysis?fen=r1b1r1k1/5ppp/p1nb1q2/1p2p3/3p4/2NP1N1P/PPPB1P2/2KRQB1R%20w%20-%20-%200%2014) |
| 668 | allowed | DISCOVERED_ATTACK | 7 | `16. Qe4 Qxe4 17. Nxe4 Be6 18. Bg2 f5 19. Nf6+ gxf6 20. Bxc6 Kf7 21. Bxa8 Rxa8` | [ply 29](http://localhost:5173/analysis?game_id=683766&ply=29) | [board](http://localhost:5173/analysis?fen=r1br2k1/5ppp/p1nN4/1p2p3/3p4/3P1q1P/PPPB1P2/2KRQB1R%20w%20-%20-%201%2016) |
| 669 | allowed | SACRIFICE | 4 | `14. Ba4+ Ndc6 15. Nxd5 exd5 16. c4 Qa5 17. b3` | [ply 25](http://localhost:5173/analysis?game_id=683767&ply=25) | [board](http://localhost:5173/analysis?fen=r2qkb1r/4nppp/p3p3/3pP3/1p1n4/1BN3Q1/PPP2PPP/R4RK1%20w%20-%20-%200%2014) |
| 670 | missed | CLEARANCE | 2 | `13... Nef5 14. Qh3 Bc5 15. Rad1 Qh4 16. Qxh4 Nxh4 17. Nxd5 exd5 18. Bxd5 Rd8 19. Bb7` | [ply 25](http://localhost:5173/analysis?game_id=683767&ply=25) | [board](http://localhost:5173/analysis?fen=r2qkb1r/4nppp/p3p3/1p1pP3/3n4/1BN3Q1/PPP2PPP/R4RK1%20b%20-%20-%200%2013) |
| 671 | allowed | CLEARANCE | 6 | `30. Rxa5 Rd8 31. d5 Rc8 32. d6 Kf7 33. Re5 Rd8 34. Rxe4 Rxd6 35. a4 Rd1+` | [ply 57](http://localhost:5173/analysis?game_id=683768&ply=57) | [board](http://localhost:5173/analysis?fen=4r1k1/6pp/8/pR6/3Pp3/P5P1/1P5P/6K1%20w%20-%20-%201%2030) |
| 672 | missed | SKEWER | 4 | `30... Rb8 31. Kf2 Rxb2+ 32. Ke3 Rxh2 33. Rf5 g6 34. Rf1 Rg2 35. Kxe4 Rxg3 36. d5` | [ply 59](http://localhost:5173/analysis?game_id=683768&ply=59) | [board](http://localhost:5173/analysis?fen=4r1k1/6pp/8/p3R3/3Pp3/P5P1/1P5P/6K1%20b%20-%20-%200%2030) |
| 673 | allowed | PROMOTION | 6 | `51... Rg3 52. Rg8+ Kf4 53. Rxg3 Kxg3 54. a6 g1=Q 55. Kc3 Kf4 56. Kc2 Ke4 57. Kb2` | [ply 100](http://localhost:5173/analysis?game_id=683776&ply=100) | [board](http://localhost:5173/analysis?fen=3R4/8/8/Pp3pk1/1P6/4r3/3K2p1/8%20b%20-%20-%201%2051) |
| 674 | missed | CLEARANCE | 6 | `20. Nc1 c5 21. Qc3 Qb6 22. Bc4 Kh8 23. Rhd1 Rab8 24. a4` | [ply 38](http://localhost:5173/analysis?game_id=683782&ply=38) | [board](http://localhost:5173/analysis?fen=r4rk1/3R2pp/2p1Pp2/q5b1/3Q4/1P5P/PBP1N1P1/1K3B1R%20w%20-%20-%200%2020) |
| 675 | missed | CLEARANCE | 8 | `22... Qh6 23. R1f2 Nxb3 24. Qxb3 Rd7 25. Nb5 Ne7 26. Re5 Qb6 27. Qd3 Nc6 28. Re3` | [ply 43](http://localhost:5173/analysis?game_id=683783&ply=43) | [board](http://localhost:5173/analysis?fen=5rk1/2N2ppp/2nr4/p2p1Rq1/3P4/PB1Q3P/1PPn2P1/5RK1%20b%20-%20-%200%2022) |
| 676 | missed | CLEARANCE | 10 | `25... Rxd4 26. Qg3+ Kh8 27. Rxf6 Nxf1 28. Rxf1 Rdd8 29. Bxf7 Rd7 30. Bh5 Rfd8 31. Qf4` | [ply 49](http://localhost:5173/analysis?game_id=683783&ply=49) | [board](http://localhost:5173/analysis?fen=5rk1/5p1p/2nrBp2/p4R2/3P4/P2Q3P/1PPn2P1/5RK1%20b%20-%20-%200%2025) |
| 677 | missed | SACRIFICE | 10 | `27... Kg7 28. Qg3+ Kxf6 29. Qxd6 Ne7 30. Qe5+ Kf7 31. Qf4+ Ke8 32. Qxd2 h5 33. Qh6` | [ply 53](http://localhost:5173/analysis?game_id=683783&ply=53) | [board](http://localhost:5173/analysis?fen=6k1/7p/2nrpR2/p7/3P4/P2Q3P/1PPn2P1/6K1%20b%20-%20-%200%2027) |
| 678 | allowed | MATE | 10 | `32... Qxe3 33. Kh2 Rd1 34. Qg5 Qxg5 35. g4 Qe3 36. Kg2 Rd2+ 37. Kf1 Qf2#` | [ply 62](http://localhost:5173/analysis?game_id=683787&ply=62) | [board](http://localhost:5173/analysis?fen=8/pppr2k1/6p1/2q2p2/2P4Q/4R2P/6P1/7K%20b%20-%20-%201%2032) |
| 679 | allowed | CLEARANCE | 4 | `14. a4 Qb8 15. Bc5 Ng6 16. Qe3 h6 17. b4 Nf8 18. Nd4 Qb7 19. Nb3 Nd7` | [ply 25](http://localhost:5173/analysis?game_id=683792&ply=25) | [board](http://localhost:5173/analysis?fen=r3k2r/p3nppp/b1p1p3/1q1pP3/8/1P2BN2/P1PQ1PPP/R3K2R%20w%20-%20-%201%2014) |
| 680 | missed | DEFLECTION | 4 | `23... d4 24. Bxd4 Rxd4 25. Qxd4 Qxg2 26. c4 Qxh1+ 27. Kf2 h5 28. Rb4 Qxh2+ 29. Ke3` | [ply 45](http://localhost:5173/analysis?game_id=683792&ply=45) | [board](http://localhost:5173/analysis?fen=2rr2k1/p4ppp/b1q1p3/3pP3/P4P2/4B3/1RPQ2PP/4K2R%20b%20-%20-%200%2023) |
| 681 | missed | PIN | 6 | `24... d4 25. Kg3 dxe3 26. Qxe3 h6 27. h4 Qc3 28. Qxc3 Rxc3+ 29. Kh2 h5 30. Rhb1` | [ply 47](http://localhost:5173/analysis?game_id=683792&ply=47) | [board](http://localhost:5173/analysis?fen=2rr2k1/p4ppp/b3p3/3pP3/P1q2P2/4B3/1RPQ1KPP/7R%20b%20-%20-%200%2024) |
| 682 | missed | CLEARANCE | 2 | `20... Be7 21. b5 Rh8 22. a4 Rh2+ 23. Kd3 e5 24. Ba3 Bxa3 25. Rxg5 Bf8 26. Ne4` | [ply 39](http://localhost:5173/analysis?game_id=683794&ply=39) | [board](http://localhost:5173/analysis?fen=2kr1b2/pp1n1pp1/2p1p3/6n1/1P1P4/P1N1P3/1BP1K3/6R1%20b%20-%20-%200%2020) |
| 683 | missed | CLEARANCE | 10 | `14... g6 15. Bg5 Be7 16. h4 Rc8 17. Nd4 Re8 18. f4 Ne4 19. Qe3 Bf6 20. h5` | [ply 27](http://localhost:5173/analysis?game_id=683798&ply=27) | [board](http://localhost:5173/analysis?fen=r2q1rk1/pp3ppp/4pn2/1Nbp4/5B2/5P1P/PPPQ1P2/2KR2R1%20b%20-%20-%200%2014) |
| 684 | allowed | PIN | 0 | `21. Qxh5 e5 22. Be3 d4 23. Ne4 Bg7 24. Bh6 Qc7 25. Rd2 Qa5 26. Bxg7 Qxa2` | [ply 39](http://localhost:5173/analysis?game_id=683798&ply=39) | [board](http://localhost:5173/analysis?fen=2rqr1k1/1p3p1p/p3pbpQ/3p3n/3B4/2N2P1P/PPP2P2/2KR2R1%20w%20-%20-%201%2021) |
| 685 | missed | SACRIFICE | 2 | `17... Ngf6 18. Nxh8 Rxh8 19. g5 Nd5 20. Qxe6 N7b6 21. Qd6+ Nc7 22. Rhd1 a5 23. Bf1` | [ply 33](http://localhost:5173/analysis?game_id=683806&ply=33) | [board](http://localhost:5173/analysis?fen=1k1r2nr/pp1n1Np1/2p1p1p1/8/6P1/2P4P/qP1RQPB1/2K4R%20b%20-%20-%200%2017) |
| 686 | missed | CLEARANCE | 2 | `16. Re1 h6 17. Rad1 Qc7 18. Bd2 Bxd3 19. cxd3 Qd6 20. exd5 cxd5 21. Rc1 Qb6` | [ply 30](http://localhost:5173/analysis?game_id=683819&ply=30) | [board](http://localhost:5173/analysis?fen=r2qr1k1/5ppp/b1p2n2/3pp3/pB2P3/P2B1Q1P/1PP2PP1/R2R2K1%20w%20-%20-%200%2016) |
| 687 | missed | PIN | 0 | `14. Nxe5 Ne7 15. Nxc6 Nxc6 16. Rc1 Rb8 17. Rxc6 bxc6 18. Ba5 Qd6 19. Nc7+ Kd7` | [ply 26](http://localhost:5173/analysis?game_id=683857&ply=26) | [board](http://localhost:5173/analysis?fen=r2qkbnr/1p3ppp/p1n3b1/3Np3/Q3P3/5N1P/PP1BBPP1/R3K2R%20w%20-%20-%200%2014) |
| 688 | missed | CLEARANCE | 4 | `12... Ne7 13. Qe2 Nf5 14. Nd2 Be7 15. Rab1 c5 16. c4` | [ply 23](http://localhost:5173/analysis?game_id=683887&ply=23) | [board](http://localhost:5173/analysis?fen=r2qkbnr/5ppp/p1p1p3/3pP3/8/2P1BQ1P/P4PP1/RN3RK1%20b%20-%20-%200%2012) |
| 689 | allowed | INTERFERENCE | 2 | `14. Qc6+ Ke7 15. Qxc5+ Kd7 16. Qxd4+ Ke8 17. Qe4 Bb4 18. c5 Rb8 19. Qc6+ Kf8` | [ply 25](http://localhost:5173/analysis?game_id=683887&ply=25) | [board](http://localhost:5173/analysis?fen=r2qkbnr/5ppp/p3p3/2p1P3/2Pp4/4BQ1P/P4PP1/RN3RK1%20w%20-%20-%200%2014) |
| 690 | missed | CLEARANCE | 6 | `15... Ra7 16. Nd2 Ne7 17. Rab1 Nf5 18. Qa3 Be7 19. Qa4+ Kf8 20. Ne4 h5 21. Rd3` | [ply 29](http://localhost:5173/analysis?game_id=683887&ply=29) | [board](http://localhost:5173/analysis?fen=r3kbnr/2q2ppp/p3p3/2p1P3/2Pp1B2/5Q1P/P4PP1/RN1R2K1%20b%20-%20-%200%2015) |
| 691 | missed | SACRIFICE | 4 | `30... Qe8 31. Bxh6 Qf7 32. Rxf7 Rxf7 33. Rb8+ Kh7 34. Bd2 Rf6 35. Qh4+ Kg6` | [ply 59](http://localhost:5173/analysis?game_id=683887&ply=59) | [board](http://localhost:5173/analysis?fen=2q2rk1/1R4p1/4p2p/6B1/2Pp4/6QP/P4PP1/1R4K1%20b%20-%20-%200%2030) |
| 692 | allowed | CLEARANCE | 4 | `10... Bh7 11. Bc4 e6 12. g3 Be7 13. Ng2 Nd7 14. Bd2` | [ply 18](http://localhost:5173/analysis?game_id=683889&ply=18) | [board](http://localhost:5173/analysis?fen=rn1qkb1r/1p2ppp1/p6p/5b2/3Pp2N/3BP3/PP3PPP/R1BQ1RK1%20b%20-%20-%201%2010) |
| 693 | missed | TRAPPED_PIECE | 4 | `12. Bxe7 Nxd2 13. Bh4 Nf3+ 14. gxf3 Be6 15. Kd2 f6 16. Rhg1 Kf7 17. Rae1 Bd5` | [ply 22](http://localhost:5173/analysis?game_id=683901&ply=22) | [board](http://localhost:5173/analysis?fen=rnb1k2r/pp2qppp/2p5/6B1/3Pn3/3B4/PP1Q1PPP/R3K2R%20w%20-%20-%200%2012) |
| 694 | allowed | CLEARANCE | 6 | `18... Ra7 19. Ng3 Qd7 20. Ne4 Qd8 21. Qf4 Rd7 22. b4 a5 23. bxa5 bxa5 24. Nxc5` | [ply 34](http://localhost:5173/analysis?game_id=683908&ply=34) | [board](http://localhost:5173/analysis?fen=rnb2r2/6kp/pp1p1pp1/2pP1q2/2P5/5N2/PP1QNPPP/R3R1K1%20b%20-%20-%201%2018) |
| 695 | allowed | TRAPPED_PIECE | 2 | `18. a3 a4 19. axb4 axb3 20. f5 h6 21. Bd2 Qb5 22. Qe3 Qb6 23. Kh1 h5` | [ply 33](http://localhost:5173/analysis?game_id=683939&ply=33) | [board](http://localhost:5173/analysis?fen=2r1k2r/4nppp/1qp1p3/p2pP3/1b1P1PP1/1N1QB3/PP5P/R4RK1%20w%20-%20-%201%2018) |
| 696 | missed | SACRIFICE | 10 | `29... Rf8 30. Rf7 Rxf7 31. exf7+ Kh8 32. Qe3 Bf8 33. h5 Qd7 34. hxg6 Qxg4+ 35. Kf2` | [ply 57](http://localhost:5173/analysis?game_id=683939&ply=57) | [board](http://localhost:5173/analysis?fen=4r1k1/1q4pp/4P1n1/3p2N1/pb1B2PP/3Q4/PP6/5RK1%20b%20-%20-%200%2029) |
| 697 | missed | SACRIFICE | 2 | `30... Bxg5 31. Rxb7 Bf6 32. Bxf6 gxf6 33. Qf5 Re7 34. Rxe7 Nxe7 35. Qxf6 Ng6 36. Qf7+` | [ply 59](http://localhost:5173/analysis?game_id=683939&ply=59) | [board](http://localhost:5173/analysis?fen=4r1k1/1q2bRpp/4P1n1/3p2N1/p2B2PP/3Q4/PP6/6K1%20b%20-%20-%200%2030) |
| 698 | allowed | MATE | 6 | `32. Rxg7+ Kh8 33. Rxg6+ Qe5 34. Bxe5+ Bf6 35. Bxf6#` | [ply 61](http://localhost:5173/analysis?game_id=683939&ply=61) | [board](http://localhost:5173/analysis?fen=1q2r1k1/5Rpp/4P1n1/3p2bP/p2B2P1/3Q4/PP6/6K1%20w%20-%20-%200%2032) |
| 699 | missed | SACRIFICE | 2 | `31... Bf6 32. hxg6 h6 33. Rxf6 gxf6 34. Nh7 Rxe6 35. Nxf6+ Rxf6 36. Bxf6 Qd6 37. Qc3` | [ply 61](http://localhost:5173/analysis?game_id=683939&ply=61) | [board](http://localhost:5173/analysis?fen=1q2r1k1/4bRpp/4P1n1/3p2NP/p2B2P1/3Q4/PP6/6K1%20b%20-%20-%200%2031) |
| 700 | missed | SACRIFICE | 4 | `36... Nc6 37. Qc5 d3 38. Qxc6 Rh7 39. Qb6+ Rc7 40. Bd1 Kc8` | [ply 71](http://localhost:5173/analysis?game_id=683941&ply=71) | [board](http://localhost:5173/analysis?fen=3k4/3r4/8/p3QP2/Pn1pP3/1B4N1/1P3P2/1K6%20b%20-%20-%200%2036) |
| 701 | allowed | PIN | 10 | `14... Qg6 15. Rc1 Nd7 16. Rc3 Nxe5 17. Qc2` | [ply 26](http://localhost:5173/analysis?game_id=683945&ply=26) | [board](http://localhost:5173/analysis?fen=1n2k2r/1b3ppp/5q2/1p2P3/1bp5/4P3/1P1N1PPP/R2QKB1R%20b%20-%20-%200%2014) |
| 702 | allowed | CLEARANCE | 8 | `19... cxd3 20. Qxe3+ Bxe3 21. Ra3 Bb6 22. Rxd3 Ke7 23. Ke2 Rd8 24. Rxd8 Bxd8 25. g4` | [ply 36](http://localhost:5173/analysis?game_id=683945&ply=36) | [board](http://localhost:5173/analysis?fen=1n2k2r/R4ppp/8/1p6/2p5/3BqP2/1P1bQ1PP/5K1R%20b%20-%20-%201%2019) |
| 703 | missed | PIN | 0 | `19. Kd1` | [ply 36](http://localhost:5173/analysis?game_id=683945&ply=36) | [board](http://localhost:5173/analysis?fen=1n2k2r/R4ppp/8/1p6/2p5/3BqP2/1P1bQ1PP/4K2R%20w%20-%20-%200%2019) |
| 704 | missed | FORK | 4 | `26. Rxc3 g5 27. Ke2 Bxc3 28. Rxd8+ Kg7 29. Rxb8 Be5 30. Rb7 Bxh2 31. Bc4 Kf6` | [ply 50](http://localhost:5173/analysis?game_id=683945&ply=50) | [board](http://localhost:5173/analysis?fen=1n1r2k1/2R2ppp/8/1B6/8/2p2P2/3b1KPP/3R4%20w%20-%20-%200%2026) |
| 705 | allowed | CLEARANCE | 8 | `12. Nd3 Bd6 13. g3 b5 14. a3 Nd7` | [ply 21](http://localhost:5173/analysis?game_id=683948&ply=21) | [board](http://localhost:5173/analysis?fen=r1b2rk1/1pq2ppp/4pn2/p2p4/1N1P1b2/2P5/PP1NBPPP/R2QK2R%20w%20-%20-%200%2012) |
| 706 | allowed | CAPTURING_DEFENDER | 4 | `7. axb5 cxb5 8. Nxb5 Bb7 9. Bxc4 a5 10. Bd2 Be7 11. Nc3` | [ply 11](http://localhost:5173/analysis?game_id=683949&ply=11) | [board](http://localhost:5173/analysis?fen=rnbqkb1r/p4ppp/2p1pn2/1p6/P1pP4/2N1PN2/1P3PPP/R1BQKB1R%20w%20-%20-%200%207) |
| 707 | missed | DISCOVERED_ATTACK | 1 | `15... Ne5 16. Nxe5 Rxc4 17. Nxc4 Bc6 18. Nd6 Re7 19. Bc5 Qa8 20. e4 h5 21. c4` | [ply 29](http://localhost:5173/analysis?game_id=683949&ply=29) | [board](http://localhost:5173/analysis?fen=2rqr1k1/p2b1ppp/2n1pn2/8/2QP4/B1PBPN2/5PPP/RR4K1%20b%20-%20-%200%2015) |
| 708 | allowed | CAPTURING_DEFENDER | 4 | `19. Qxb8 Qxb8 20. Rxb8 Rxb8 21. Nxe5 Nc8 22. Ra1 g6 23. c4 Bf5 24. Bxf5 gxf5` | [ply 35](http://localhost:5173/analysis?game_id=683949&ply=35) | [board](http://localhost:5173/analysis?fen=1r1qr1k1/R3nppp/4bn2/2B1p3/1Q1P4/2PBPN2/5PPP/1R4K1%20w%20-%20-%201%2019) |
| 709 | missed | FORK | 0 | `20... e4 21. Bb5 Bd5 22. Qa6 exf3 23. Bxe8 Nxe8 24. e4 Bxe4 25. Re1 Nd5 26. Rxe4` | [ply 39](http://localhost:5173/analysis?game_id=683949&ply=39) | [board](http://localhost:5173/analysis?fen=3qr1k1/1Q2nppp/4bn2/2B1p3/3P4/2PBPN2/5PPP/1R4K1%20b%20-%20-%200%2020) |
| 710 | missed | CLEARANCE | 4 | `9... Bxf3 10. Qxf3 e6 11. Ne2 Bd6 12. c3` | [ply 17](http://localhost:5173/analysis?game_id=683960&ply=17) | [board](http://localhost:5173/analysis?fen=rn1qkb1r/4pppp/p4n2/1p1p4/3P2b1/1BN2N1P/PPP2PP1/R1BQK2R%20b%20-%20-%200%209) |
| 711 | missed | FORK | 4 | `23... Qxh3+ 24. Kg1 Bxg3 25. fxg3 Qxg3+ 26. Bg2 Nc6 27. Qd2 Ne5 28. Qf2 Qg4 29. Rd5` | [ply 45](http://localhost:5173/analysis?game_id=683960&ply=45) | [board](http://localhost:5173/analysis?fen=1n2r1k1/5ppp/p2b4/Qp6/2P5/1P3BPP/P4P1q/3R1K2%20b%20-%20-%200%2023) |
| 712 | allowed | CAPTURING_DEFENDER | 4 | `18. Be3 Bg7 19. Bxd4 Qd8 20. Qxf3 Qg8 21. Qf7 Qxf7 22. Nxf7 Nf5 23. Nd6 Nxd4` | [ply 33](http://localhost:5173/analysis?game_id=683963&ply=33) | [board](http://localhost:5173/analysis?fen=r1b2b1N/pp1kn2R/1q2p3/3pP3/1P1n4/P4p2/5P2/R1BQKB2%20w%20-%20-%200%2018) |
| 713 | missed | SACRIFICE | 10 | `17... Kc7 18. Be3 a6 19. Bd3 Kb8 20. Qxf3 Nf5 21. Bxf5 exf5 22. Qxd5 f4 23. Bxf4` | [ply 33](http://localhost:5173/analysis?game_id=683963&ply=33) | [board](http://localhost:5173/analysis?fen=r1b2b1N/pp1kn2R/1qn1p3/3pP3/1P1P4/P4p2/5P2/R1BQKB2%20b%20-%20-%200%2017) |
| 714 | missed | SACRIFICE | 6 | `20... Qc6 21. Qxc6+ bxc6 22. Ng6 Kd8 23. Nxf8 Nd5 24. Kd2 a5 25. b5 cxb5 26. Ng6` | [ply 39](http://localhost:5173/analysis?game_id=683963&ply=39) | [board](http://localhost:5173/analysis?fen=r1b2b1N/pp1kn2R/1q2p3/4P3/1P1B4/P4p2/2Q2P2/R3KB2%20b%20-%20-%200%2020) |
| 715 | allowed | SACRIFICE | 2 | `10. Nxe5 Bxe5 11. Qh5 g6 12. Qxe5 f6 13. Qe3 Kf7 14. Ne2 Qxe3 15. Bxe3 g5` | [ply 17](http://localhost:5173/analysis?game_id=683964&ply=17) | [board](http://localhost:5173/analysis?fen=r3k1nr/pp2qppp/2bb4/3pp3/8/2NP1N2/PPP2PPP/R1BQR1K1%20w%20-%20-%201%2010) |
| 716 | allowed | CLEARANCE | 10 | `16. Nxd5 Nxd5 17. Qxd5 Rad8 18. Qf5 g6 19. Qb5 g5 20. Be3 f5 21. Rad1 Kh7` | [ply 29](http://localhost:5173/analysis?game_id=683964&ply=29) | [board](http://localhost:5173/analysis?fen=r4rk1/pp2qpp1/3b1n1p/3b4/4p3/2N4N/PPP3PP/R1BQR1K1%20w%20-%20-%200%2016) |
| 717 | allowed | DISCOVERED_ATTACK | 1 | `15... Nf5 16. Nxe6 Qxh4 17. Nxf8 Nxd4 18. Kf1 Kxf8 19. Qb4+ Qe7 20. Qd2 Qh4` | [ply 28](http://localhost:5173/analysis?game_id=683970&ply=28) | [board](http://localhost:5173/analysis?fen=rn1q1rk1/pp2np2/2p1p2p/3pP1N1/2PP3B/P1Q5/1P3PPP/R3K2R%20b%20-%20-%200%2015) |
| 718 | missed | UNDER_PROMOTION | 8 | `28... Qc4 29. d5 Qd4+ 30. Kg3 Qxe5+ 31. Qxe5+ Nxe5 32. Rhh1 cxb1=R 33. Rxb1 Rb8 34. dxc6` | [ply 55](http://localhost:5173/analysis?game_id=683971&ply=55) | [board](http://localhost:5173/analysis?fen=6r1/p2nk1pR/q1p5/4PQN1/Pb1P4/8/1pp2K2/1R6%20b%20-%20-%200%2028) |
| 719 | missed | SACRIFICE | 2 | `14. Nxd4 Nxd4 15. Nb4 Nf3+ 16. Qxf3 Qa4 17. Qd3 Be6 18. Nd5 Ng4 19. f4 Bxd5` | [ply 26](http://localhost:5173/analysis?game_id=683974&ply=26) | [board](http://localhost:5173/analysis?fen=r1b2rk1/pp3ppp/2np3n/8/2BpP3/1R1N1N2/q1P2PPP/3Q1RK1%20w%20-%20-%200%2014) |
| 720 | allowed | TRAPPED_PIECE | 4 | `15... Bxd5 16. exd5 Ne7 17. Nxb6+ axb6 18. Rxa1 Nxd5 19. Rd1 Ke6 20. Rc1 Ra8 21. a3` | [ply 28](http://localhost:5173/analysis?game_id=683994&ply=28) | [board](http://localhost:5173/analysis?fen=N5nr/pb1k2pp/1p3p2/3Bp3/4P3/4PN2/PP2K1PP/n6R%20b%20-%20-%201%2015) |
| 721 | missed | FORK | 0 | `15. Rd1+ Ke7 16. Nc7 Nh6 17. Rxa1 Bxe4 18. Nd5+ Bxd5 19. Bxd5 Rc8 20. Rd1 Nf5` | [ply 28](http://localhost:5173/analysis?game_id=683994&ply=28) | [board](http://localhost:5173/analysis?fen=N5nr/pb1k2pp/1p3p2/4p3/2B1P3/4PN2/PP2K1PP/n6R%20w%20-%20-%200%2015) |
| 722 | allowed | INTERFERENCE | 10 | `19... Rc8 20. a3 g5 21. Nf5+ Nxf5 22. exf5 Rd8 23. g4 Nd4+ 24. exd4 Rxd5 25. Ke3` | [ply 36](http://localhost:5173/analysis?game_id=683994&ply=36) | [board](http://localhost:5173/analysis?fen=7r/p3k1pp/1p3p1n/3Bp3/4P2N/4P3/PPn1K1PP/3R4%20b%20-%20-%201%2019) |
| 723 | missed | CLEARANCE | 4 | `9. Bb1 c6 10. a3 Na6 11. Ba2` | [ply 16](http://localhost:5173/analysis?game_id=683995&ply=16) | [board](http://localhost:5173/analysis?fen=r1bqk2r/ppp1ppbp/1n4p1/3P4/1n2P3/2NB1N2/PP3PPP/R1BQK2R%20w%20-%20-%200%209) |
| 724 | missed | CLEARANCE | 8 | `26. Rad1 Qf7 27. Qd3 Rce4 28. Kh1 Qc4 29. Qxc4 Rxc4 30. Rd7+ Kg8 31. Rd2 g5` | [ply 50](http://localhost:5173/analysis?game_id=683995&ply=50) | [board](http://localhost:5173/analysis?fen=4r3/p2q2kp/2p2pp1/1p6/2r5/P3QN1N/1P3PPP/R4RK1%20w%20-%20-%200%2026) |
| 725 | allowed | HANGING_PIECE | 0 | `11... Kxf7` | [ply 20](http://localhost:5173/analysis?game_id=683996&ply=20) | [board](http://localhost:5173/analysis?fen=rn1qk2r/1b3Npp/p2bpn2/2p3B1/8/2NB4/PPP2PPP/R2Q1RK1%20b%20-%20-%200%2011) |
| 726 | allowed | CLEARANCE | 2 | `20... Kg7 21. Qa4 Qf8 22. h4 Ra7 23. Rd2 Rf7 24. Red1 e5 25. h5 e4 26. Rd5` | [ply 38](http://localhost:5173/analysis?game_id=683996&ply=38) | [board](http://localhost:5173/analysis?fen=rn2r3/7p/p3pkp1/2p2q2/7Q/8/PPP2PPP/3RR1K1%20b%20-%20-%201%2020) |
| 727 | allowed | CLEARANCE | 10 | `21... Nc6 22. h4 g4 23. Rd7 Rad8 24. Rc7 Ne5 25. Qxc5 Rd7 26. b4 Red8 27. Rxd7` | [ply 40](http://localhost:5173/analysis?game_id=683996&ply=40) | [board](http://localhost:5173/analysis?fen=rn2r3/7p/p3pk2/2p2qp1/2Q5/8/PPP2PPP/3RR1K1%20b%20-%20-%201%2021) |
| 728 | missed | PIN | 4 | `21. Qa4 Ke7 22. Qb3 Ra7 23. Rd5 Qf6 24. Rxg5 Rd7 25. Rxc5 Kf8 26. Rc3 Rf7` | [ply 40](http://localhost:5173/analysis?game_id=683996&ply=40) | [board](http://localhost:5173/analysis?fen=rn2r3/7p/p3pk2/2p2qp1/7Q/8/PPP2PPP/3RR1K1%20w%20-%20-%200%2021) |
| 729 | allowed | PIN | 0 | `13. Bb5 Rc8 14. Rfc1` | [ply 23](http://localhost:5173/analysis?game_id=683999&ply=23) | [board](http://localhost:5173/analysis?fen=r2qk2r/p3bppp/1pn1p3/3pPn2/3P4/1Q2BN2/PP2BPPP/R4RK1%20w%20-%20-%201%2013) |
| 730 | missed | CLEARANCE | 8 | `12... a6 13. Qc3 Na5 14. Bd2 Ne7 15. b3 Nec6 16. a3 Be7 17. Ra2 b5 18. Qd3` | [ply 23](http://localhost:5173/analysis?game_id=683999&ply=23) | [board](http://localhost:5173/analysis?fen=r2qkb1r/p4ppp/1pn1p3/3pPn2/3P4/1Q2BN2/PP2BPPP/R4RK1%20b%20-%20-%200%2012) |
| 731 | missed | CLEARANCE | 8 | `21... Qb8 22. Qa3 a5 23. Qd3 Nxe3 24. Qxe3 Rc7 25. Rc2 Qc8 26. Qc1 g6 27. h3` | [ply 41](http://localhost:5173/analysis?game_id=683999&ply=41) | [board](http://localhost:5173/analysis?fen=2rb2k1/5ppp/pqB1p3/1pQpPn2/3P4/4BN2/PP3PPP/2R3K1%20b%20-%20-%200%2021) |
| 732 | allowed | PIN | 8 | `12. Bxf6 gxf6 13. Qh5 Rh7 14. d5 Rg7 15. dxc6 e6 16. Bxe6 Nxc6 17. Bd5 Rc8` | [ply 21](http://localhost:5173/analysis?game_id=684003&ply=21) | [board](http://localhost:5173/analysis?fen=rn1qkb1r/p3ppp1/2p2n1p/6B1/NpBP4/5Q2/PP3PPP/R4RK1%20w%20-%20-%200%2012) |
| 733 | allowed | CLEARANCE | 10 | `16. Bxd5 Qc7 17. Bxa8 Bd6 18. g3 Nd7 19. Qc6 Ne5 20. Qxc7 Bxc7 21. Bh1 Ba5` | [ply 29](http://localhost:5173/analysis?game_id=684003&ply=29) | [board](http://localhost:5173/analysis?fen=rn1q1rk1/p3bpp1/5p1p/3p4/NpB5/5Q2/PP3PPP/3RR1K1%20w%20-%20-%200%2016) |
| 734 | missed | FORK | 6 | `6. Nb5 Qa5+ 7. b4 Qxb4+ 8. Bd2 cxd4 9. Nc7+ Kd8 10. Nxa8 dxc4 11. Rb1 Qd6` | [ply 10](http://localhost:5173/analysis?game_id=684007&ply=10) | [board](http://localhost:5173/analysis?fen=r1bqkb1r/pp1n1ppp/4pn2/2pp4/2PP1B2/2N2N2/PP2PPPP/R2QKB1R%20w%20-%20-%200%206) |
| 735 | missed | CLEARANCE | 4 | `7. Bd2 N5f6 8. g3 b6 9. Bg2 Bb7 10. Bf4 Be7` | [ply 12](http://localhost:5173/analysis?game_id=684007&ply=12) | [board](http://localhost:5173/analysis?fen=r1bqkb1r/pp1n1ppp/4p3/2pn4/3P1B2/2N2N2/PP2PPPP/R2QKB1R%20w%20-%20-%200%207) |
| 736 | missed | DISCOVERED_ATTACK | 7 | `12. Qg4 Kf8` | [ply 22](http://localhost:5173/analysis?game_id=684008&ply=22) | [board](http://localhost:5173/analysis?fen=rn2k2r/pb1qbppp/2p1p3/4P3/p2PQ3/2P2N2/1P2BPPP/R1B1K2R%20w%20-%20-%200%2012) |
| 737 | missed | PIN | 0 | `15... Nxh3+ 16. Kf1 Qf6 17. gxh3 Qxh4 18. Qg4 Qf6 19. Re3 Re6 20. h4 Qg6 21. Qxg6` | [ply 29](http://localhost:5173/analysis?game_id=684013&ply=29) | [board](http://localhost:5173/analysis?fen=r3r1k1/p1p2ppp/2pb2q1/3pp3/P4n1N/1P1P3P/1BP2PP1/R2QR1K1%20b%20-%20-%200%2015) |
| 738 | allowed | CLEARANCE | 4 | `25. Kxg4 Rxf2 26. Raf1 Rxc2 27. Ba1 Rg2+ 28. Kf3 Rg3+ 29. Ke2 c5 30. Rf3 Rg2+` | [ply 47](http://localhost:5173/analysis?game_id=684013&ply=47) | [board](http://localhost:5173/analysis?fen=6k1/p1p2ppp/2pb4/3p2P1/P5rP/1P5K/1BP1rP2/R6R%20w%20-%20-%201%2025) |
| 739 | allowed | MATE | 10 | `24. b4 c5 25. Be5+ Kc6 26. Qc7+ Kb5 27. Qa5+ Kc6 28. b5+ Kd7 29. Qc7#` | [ply 45](http://localhost:5173/analysis?game_id=684018&ply=45) | [board](http://localhost:5173/analysis?fen=r3q2r/p5Q1/2pkpB1R/3p4/3p1P2/2P5/PP4P1/nN1K4%20w%20-%20-%201%2024) |
| 740 | missed | SKEWER | 10 | `33... c5 34. Qa6+ Qb5 35. Qxb5+ Kxb5 36. g4 Rg8 37. g5 Rh2+ 38. Kc3 Rxa2 39. Kd3` | [ply 65](http://localhost:5173/analysis?game_id=684018&ply=65) | [board](http://localhost:5173/analysis?fen=r3q3/pQ6/2p1p3/3pB3/2k2P2/8/P2K2P1/n6r%20b%20-%20-%200%2033) |
| 741 | allowed | CLEARANCE | 6 | `7. Nxf3 g6 8. d3 Bg7 9. g3` | [ply 11](http://localhost:5173/analysis?game_id=684031&ply=11) | [board](http://localhost:5173/analysis?fen=r2qkb1r/ppp1pppp/2n2n2/5b2/8/2N2p2/PPPPQ1PP/R1B1KBNR%20w%20-%20-%200%207) |
| 742 | missed | CLEARANCE | 8 | `6... Nd4 7. Qd1 exf3 8. d3 f2+ 9. Kxf2 e5 10. Ke1 Bc5 11. Nge2` | [ply 11](http://localhost:5173/analysis?game_id=684031&ply=11) | [board](http://localhost:5173/analysis?fen=r2qkb1r/ppp1pppp/2n2n2/5b2/4p3/2N2P2/PPPPQ1PP/R1B1KBNR%20b%20-%20-%200%206) |
| 743 | allowed | PIN | 10 | `16. dxe5 Qxd1+ 17. Rxd1 Nxe5 18. Na5 Rd8 19. Bb5+ Bd7 20. Bxd7+ Rxd7 21. Re1 Rd5` | [ply 29](http://localhost:5173/analysis?game_id=684046&ply=29) | [board](http://localhost:5173/analysis?fen=r3k2r/pp1n1ppp/5n2/4pb2/3P4/BN6/P1q1BPPP/R2Q1K1R%20w%20-%20-%200%2016) |
| 744 | missed | SKEWER | 2 | `10... dxc4 11. Bxc4 Qxb2 12. Ra2 Qb6 13. Nbd2 Nd5 14. Bxd5 exd5 15. Nb3 Be7 16. Bg5` | [ply 19](http://localhost:5173/analysis?game_id=684050&ply=19) | [board](http://localhost:5173/analysis?fen=r4rk1/pp3ppp/1qn1pn2/1Bbp1b2/2P2B2/P3PN1P/1P3PP1/RN1Q1RK1%20b%20-%20-%200%2010) |
| 745 | allowed | FORK | 2 | `12. Nc3 Qxb2 13. Na4 Qb5 14. dxc6 Rad8 15. Qc1 Qxa4 16. Qxc5 Ne4 17. Qb4 Qxc6` | [ply 21](http://localhost:5173/analysis?game_id=684050&ply=21) | [board](http://localhost:5173/analysis?fen=r4rk1/1p3ppp/p1n1pn2/1qbP1b2/5B2/P3PN1P/1P3PP1/RN1Q1RK1%20w%20-%20-%200%2012) |
| 746 | missed | SACRIFICE | 4 | `11... Nxd5 12. Bxc6 Nxf4 13. exf4 Rfd8 14. Qc1 Rac8 15. b4 Bd6 16. Qe3 Rxc6 17. Ra2` | [ply 21](http://localhost:5173/analysis?game_id=684050&ply=21) | [board](http://localhost:5173/analysis?fen=r4rk1/1p3ppp/pqn1pn2/1BbP1b2/5B2/P3PN1P/1P3PP1/RN1Q1RK1%20b%20-%20-%200%2011) |
| 747 | allowed | DISCOVERED_ATTACK | 1 | `18... Nxg3 19. hxg3 Rxe3 20. fxe3 Re8 21. Rxf3 g6 22. Rdf1 Qc7 23. b4 h5 24. c3` | [ply 34](http://localhost:5173/analysis?game_id=684058&ply=34) | [board](http://localhost:5173/analysis?fen=r3r1k1/pp3ppp/1qp5/3p4/3Nn3/1P2QpPB/2P2P1P/3R1RK1%20b%20-%20-%201%2018) |
| 748 | missed | PIN | 8 | `22. Qg3 Re4 23. Bf5 Ree8 24. Bd7 Re4 25. Nf5 g6 26. Qg5 Qe2 27. Nh6+ Kg7` | [ply 42](http://localhost:5173/analysis?game_id=684058&ply=42) | [board](http://localhost:5173/analysis?fen=r5k1/pp3ppp/q1p5/3pr3/3N4/1P3Q1B/2P2PKP/3R4%20w%20-%20-%200%2022) |
| 749 | allowed | CLEARANCE | 6 | `24... Rxf1 25. Qc3 Rxg1+ 26. Kxg1 c5 27. Qxc5 Qg6+ 28. Kf1 Qh5 29. f3 Qxh2 30. Qb5` | [ply 46](http://localhost:5173/analysis?game_id=684058&ply=46) | [board](http://localhost:5173/analysis?fen=4r1k1/pp3ppp/q1p5/3p4/3N4/1P3Q2/2P2P1P/4rBRK%20b%20-%20-%201%2024) |
| 750 | missed | SACRIFICE | 8 | `24. Qc3 Rxg1+ 25. Kxg1 g6 26. Bd7 Re4 27. Nf5 gxf5 28. Bxf5 Qe2 29. Qg3+ Kf8` | [ply 46](http://localhost:5173/analysis?game_id=684058&ply=46) | [board](http://localhost:5173/analysis?fen=4r1k1/pp3ppp/q1p5/3p4/3N4/1P3Q1B/2P2P1P/4r1RK%20w%20-%20-%200%2024) |
| 751 | allowed | INTERMEZZO | 2 | `14... Bxf1 15. Kxf1 Nxf6 16. Qxd8 Raxd8 17. Bxf6 gxf6 18. Ke2 c5 19. Nh4 Rd5 20. g4` | [ply 26](http://localhost:5173/analysis?game_id=684061&ply=26) | [board](http://localhost:5173/analysis?fen=r2qr1k1/p1pn1ppp/1p3P2/8/2b5/PPB1PN2/5PPP/R2Q1RK1%20b%20-%20-%200%2014) |
| 752 | missed | HANGING_PIECE | 0 | `14. bxc4 Ng4 15. e6 Rxe6 16. Nd4 Rg6 17. Nf5 Nh6 18. Ng3 Qe8 19. Qf3 Re6` | [ply 26](http://localhost:5173/analysis?game_id=684061&ply=26) | [board](http://localhost:5173/analysis?fen=r2qr1k1/p1pn1ppp/1p3n2/4P3/2b5/PPB1PN2/5PPP/R2Q1RK1%20w%20-%20-%200%2014) |
| 753 | missed | CLEARANCE | 2 | `8. e5 Ne8 9. Be4 dxe5 10. dxe5 Nc7 11. Nb5 Nba6 12. Bxa8 Nxa8 13. Qxd8 Rxd8` | [ply 14](http://localhost:5173/analysis?game_id=684074&ply=14) | [board](http://localhost:5173/analysis?fen=rnbq1rk1/p3ppbp/1p1p1np1/2p5/2PPP3/2NB1N2/PP3PPP/R1BQ1RK1%20w%20-%20-%200%208) |
| 754 | missed | FORK | 0 | `26... Qxc3 27. Rc1 Bf6 28. Rf1 Qe5 29. Qxe5 Bxe5 30. Re1 Bb2 31. Rxe6 d4 32. Bf5` | [ply 51](http://localhost:5173/analysis?game_id=684077&ply=51) | [board](http://localhost:5173/analysis?fen=6rk/p3b1qp/4p1n1/3p3Q/2p3R1/2P3PP/P1B3P1/4R1K1%20b%20-%20-%200%2026) |
| 755 | missed | PIN | 0 | `18. Rad1 Kh8 19. Ne3 Be7 20. Bc2 b5 21. a3 Bc6 22. Ncd5 Nh5 23. Qg4 Qd8` | [ply 34](http://localhost:5173/analysis?game_id=684078&ply=34) | [board](http://localhost:5173/analysis?fen=r2b1rk1/1b1q1p1p/pp1p1np1/2p1pN2/2P1P3/2NB2QP/PP3PP1/R4RK1%20w%20-%20-%200%2018) |
| 756 | missed | SKEWER | 6 | `13. Nxg6 fxg6 14. Qd3` | [ply 24](http://localhost:5173/analysis?game_id=684091&ply=24) | [board](http://localhost:5173/analysis?fen=r2qk2r/ppp2pp1/2n1pbbp/4N3/3P2P1/2N4P/PPPQ4/2KR1B1R%20w%20-%20-%200%2013) |
| 757 | missed | FORK | 0 | `29. Nf4 Rdd2 30. Nxe2 Rxe2 31. bxa5 Kd7 32. a4 Re3 33. Kb4 Rxh3 34. c4 Kc6` | [ply 56](http://localhost:5173/analysis?game_id=684091&ply=56) | [board](http://localhost:5173/analysis?fen=2k5/1pp3p1/6Np/p2r4/1P4P1/1KP4P/P3r3/8%20w%20-%20-%200%2029) |
| 758 | allowed | DISCOVERED_ATTACK | 7 | `8. dxe5 Nxe5 9. Bxd5 Qd7` | [ply 13](http://localhost:5173/analysis?game_id=684095&ply=13) | [board](http://localhost:5173/analysis?fen=r2qkbnr/pp3ppp/2n5/3pp3/3P4/2P2B2/PP3PPP/RNBQK2R%20w%20-%20-%200%208) |
| 759 | allowed | CLEARANCE | 10 | `29. a4 Rb8 30. Bc1 Rd4 31. Kf1 Rdd8 32. a5 Rb3 33. Rd1 Ra8 34. Be3 Ra6` | [ply 55](http://localhost:5173/analysis?game_id=684095&ply=55) | [board](http://localhost:5173/analysis?fen=r5k1/5pp1/7p/3r4/8/3n2P1/PB1R1P1P/R5K1%20w%20-%20-%201%2029) |
| 760 | allowed | PROMOTION | 8 | `59. h5 Ke5 60. h6 Ke6 61. Kg6 Ke5 62. h7 Ke4 63. h8=Q f4 64. Qa8+ Ke3` | [ply 115](http://localhost:5173/analysis?game_id=684095&ply=115) | [board](http://localhost:5173/analysis?fen=8/8/8/5pK1/4k2P/6P1/8/8%20w%20-%20-%201%2059) |
| 761 | allowed | MATE | 8 | `26... Nh4 27. f3 Qe3+ 28. Kh1 Qe2 29. Rg1 Qxf3+ 30. Rg2 Qxg2#` | [ply 50](http://localhost:5173/analysis?game_id=684097&ply=50) | [board](http://localhost:5173/analysis?fen=4r3/Q1R1ppk1/1P4p1/3P4/P3q3/6Pp/5PnP/5RK1%20b%20-%20-%200%2026) |
| 762 | allowed | PIN | 8 | `28... Rxe7 29. Qa6 Qd2 30. Rf2 Qd1+ 31. Rf1 Nxf1 32. Qxf1 Re1 33. Kf2 Qd2+ 34. Qe2` | [ply 54](http://localhost:5173/analysis?game_id=684097&ply=54) | [board](http://localhost:5173/analysis?fen=4r3/Q3Rpk1/1P4p1/3q4/P7/4nPPp/7P/5RK1%20b%20-%20-%200%2028) |
| 763 | allowed | INTERMEZZO | 4 | `13. dxc5 Bxc5 14. Nd2 Rb8 15. Bxc5 Qxc5 16. Qg4 Ne7 17. Qxg7 Ng6 18. b3 Qf8` | [ply 23](http://localhost:5173/analysis?game_id=684101&ply=23) | [board](http://localhost:5173/analysis?fen=r3kbnr/5ppp/pq2p3/2ppP3/3P4/4BQ1P/PP3PP1/RN3RK1%20w%20-%20-%201%2013) |
| 764 | allowed | DISCOVERED_ATTACK | 3 | `22. Kh2 Rc4 23. Ne4 dxe4 24. Rxc4 Nf3+ 25. gxf3 Qxc4 26. Qxe4 Qxa2 27. Kg2 Qb2` | [ply 41](http://localhost:5173/analysis?game_id=684101&ply=41) | [board](http://localhost:5173/analysis?fen=5rk1/5ppp/p3p3/2qpP3/1r1n4/2N1Q2P/P4PP1/2RR2K1%20w%20-%20-%201%2022) |
| 765 | missed | DEFLECTION | 10 | `28. e4 Ng6 29. exd5 Rxe1+ 30. Rxe1 Nxf4 31. Re8+ Kd7 32. Re7+ Kc8 33. dxc6 Bxc6` | [ply 54](http://localhost:5173/analysis?game_id=684102&ply=54) | [board](http://localhost:5173/analysis?fen=2k1rn2/pb6/2p2B2/3p4/2n2P2/4P2P/P5P1/2R1R1K1%20w%20-%20-%200%2028) |
| 766 | missed | CLEARANCE | 10 | `15. Bxc6+ bxc6 16. Qxd4 Qxd4 17. Bxd4 Ke7 18. Bc5+ Ke6 19. Ke2 a5 20. Rhe1 axb4` | [ply 28](http://localhost:5173/analysis?game_id=684109&ply=28) | [board](http://localhost:5173/analysis?fen=r2qk2r/1pp2ppp/p1n5/4P3/1P1b4/P4B2/1B3PPP/R2QK2R%20w%20-%20-%200%2015) |
| 767 | missed | PIN | 8 | `16. Bxb7 Ra7 17. Be4 c5 18. Qa4+ Rd7 19. bxc5 Qh4 20. Bc6 Ke7 21. Rd1 Rhd8` | [ply 30](http://localhost:5173/analysis?game_id=684109&ply=30) | [board](http://localhost:5173/analysis?fen=r2qk2r/1pp2ppp/p7/4P3/1P1n4/P4B2/5PPP/R2QK2R%20w%20-%20-%200%2016) |
| 768 | allowed | DISCOVERED_CHECK | 0 | `36... e3+ 37. Kh2 exf2 38. Qxh5+ Kg8 39. Qe2 Qc1 40. Qxf2 Qxa3 41. b5 Kh8 42. Qe2` | [ply 70](http://localhost:5173/analysis?game_id=684109&ply=70) | [board](http://localhost:5173/analysis?fen=8/6pk/2q5/6Qp/1P2p2P/P5P1/5PK1/8%20b%20-%20-%201%2036) |
| 769 | missed | FORK | 2 | `28... Rge3 29. Na5 Re1+ 30. Qxe1 Rxe1+ 31. Rf1 Rxf1+ 32. Kxf1 cxd5 33. Kg1 Kf8 34. Nxb7` | [ply 55](http://localhost:5173/analysis?game_id=684111&ply=55) | [board](http://localhost:5173/analysis?fen=4r1k1/pp3pp1/2p3qp/2PP4/1P6/PN4r1/5RB1/3Q2K1%20b%20-%20-%200%2028) |
| 770 | missed | PIN | 0 | `31... Rxa3 32. Qe1 Ra2 33. Kh2 Qh5+ 34. Kg1` | [ply 61](http://localhost:5173/analysis?game_id=684111&ply=61) | [board](http://localhost:5173/analysis?fen=6k1/pp3pp1/2pP2qp/2Pr4/1P6/P5r1/3N1RB1/5QK1%20b%20-%20-%200%2031) |
| 771 | allowed | DEFLECTION | 4 | `39. d8=Q+ Kh7 40. Bf5+ g6 41. Rxh6+ Kxh6 42. Qh8+ Kg5 43. Qxb2 Ra6 44. Bd3 b5` | [ply 75](http://localhost:5173/analysis?game_id=684111&ply=75) | [board](http://localhost:5173/analysis?fen=6k1/pp1P1pp1/2p4p/2P5/1P5R/r6B/1r6/6K1%20w%20-%20-%201%2039) |
| 772 | missed | DEFLECTION | 4 | `38... Rd2 39. Re4 Ra1+ 40. Bf1 Rxd7 41. Kf2 Kf8 42. b5 Ra2+ 43. Kf3 Ra3+ 44. Kf4` | [ply 75](http://localhost:5173/analysis?game_id=684111&ply=75) | [board](http://localhost:5173/analysis?fen=6k1/pp1P1pp1/2p4p/2P5/1P5R/r6B/5r2/6K1%20b%20-%20-%200%2038) |
| 773 | missed | DEFLECTION | 2 | `41... Rxh3 42. Rxh3 Rxb4 43. Re3 Rf4+ 44. Kg2 b6 45. Rf3 Rf6 46. Kf2 Rg6 47. Rxf7` | [ply 81](http://localhost:5173/analysis?game_id=684111&ply=81) | [board](http://localhost:5173/analysis?fen=8/pp3ppk/2p4p/2P5/1P5R/6rB/1r6/3Q1K2%20b%20-%20-%200%2041) |
| 774 | missed | DISCOVERED_ATTACK | 5 | `35... Ke8 36. f5 gxf5 37. Rh8+ Kd7 38. h4 Rxh8 39. Qxh8 Nxc4 40. Qb8 e5 41. Qxa7+` | [ply 69](http://localhost:5173/analysis?game_id=684126&ply=69) | [board](http://localhost:5173/analysis?fen=r4k2/p4p2/1pqnpQp1/2p5/2P2P2/7R/PP4PP/6K1%20b%20-%20-%200%2035) |
| 775 | allowed | CLEARANCE | 6 | `12... Nxf6 13. Bf3 Bb7 14. Bb2 Qd7 15. Qe2 Rad8 16. Rad1 Qc8 17. g3 dxc4 18. Bxb7` | [ply 22](http://localhost:5173/analysis?game_id=684145&ply=22) | [board](http://localhost:5173/analysis?fen=r1bq1rk1/p2nb1pp/1p2pP2/2pp4/2P2P2/1PN1P3/P3B1PP/R1BQ1RK1%20b%20-%20-%200%2012) |
| 776 | allowed | SACRIFICE | 6 | `14... a6 15. Bf3 axb5 16. Bxa8 bxc4 17. exd4 Ba6 18. Bf3 c3 19. Bxc3 Bxf1 20. Qxf1` | [ply 26](http://localhost:5173/analysis?game_id=684145&ply=26) | [board](http://localhost:5173/analysis?fen=r1bq1rk1/p2n2pp/1p2pb2/1Np5/2Pp1P2/1P2P3/PB2B1PP/R2Q1RK1%20b%20-%20-%201%2014) |
| 777 | missed | CLEARANCE | 8 | `14. Ne4 Bb7 15. Nxf6+ Qxf6 16. exd4 Rad8 17. Bg4 Be4 18. Qe2 Bf5 19. Bxf5 Qxf5` | [ply 26](http://localhost:5173/analysis?game_id=684145&ply=26) | [board](http://localhost:5173/analysis?fen=r1bq1rk1/p2n2pp/1p2pb2/2p5/2Pp1P2/1PN1P3/PB2B1PP/R2Q1RK1%20w%20-%20-%200%2014) |
| 778 | allowed | CLEARANCE | 10 | `7... d5 8. Nd4 Qe7` | [ply 12](http://localhost:5173/analysis?game_id=684158&ply=12) | [board](http://localhost:5173/analysis?fen=rnb1kb1r/pp1p1ppp/2p1qn2/8/2B1P3/1PN2N2/P1P2PPP/R1BQK2R%20b%20-%20-%201%207) |
| 779 | missed | PIN | 2 | `12. Bxc4 Bb7 13. Bxb5 Qxb5 14. Qxa4 Qxa4 15. Rxa4 Bc6 16. Ra3 Bd5` | [ply 22](http://localhost:5173/analysis?game_id=684171&ply=22) | [board](http://localhost:5173/analysis?fen=rnb1k2r/p1pq1ppp/4p3/1p2P1B1/n1pP4/5N2/2Q2PPP/R3KB1R%20w%20-%20-%200%2012) |
| 780 | allowed | PROMOTION | 10 | `26... Bxf3 27. gxf3 a5 28. f4 a4 29. f5 a3 30. Kg2 a2 31. h4 a1=Q 32. f6` | [ply 50](http://localhost:5173/analysis?game_id=684171&ply=50) | [board](http://localhost:5173/analysis?fen=6k1/p1p2pp1/2b1p2p/4P3/1r6/3B1NBP/5PPK/8%20b%20-%20-%201%2026) |
| 781 | allowed | PIN | 0 | `9... Qe7 10. f4 Ng4` | [ply 16](http://localhost:5173/analysis?game_id=684175&ply=16) | [board](http://localhost:5173/analysis?fen=r1bqk2r/ppp2ppp/3p1n2/4P3/2PQ4/8/PP1N1PPP/R3KB1R%20b%20-%20-%200%209) |
| 782 | missed | CLEARANCE | 4 | `12. Qc3 Re8` | [ply 22](http://localhost:5173/analysis?game_id=684175&ply=22) | [board](http://localhost:5173/analysis?fen=r2q1rk1/ppp2ppp/4bn2/4Q3/2P5/8/PP1NBPPP/R3K2R%20w%20-%20-%200%2012) |
| 783 | allowed | HANGING_PIECE | 0 | `13... Qxd2 14. Rad1 Qb4 15. a3 Qe7 16. Bd3 Rad8 17. h3 c5 18. g4 Rd4 19. Bc2` | [ply 24](http://localhost:5173/analysis?game_id=684175&ply=24) | [board](http://localhost:5173/analysis?fen=r2qr1k1/ppp2ppp/4bn2/4Q3/2P5/8/PP1NBPPP/R3R1K1%20b%20-%20-%201%2013) |
| 784 | allowed | CLEARANCE | 10 | `15... Nxe4 16. Qc2 f5` | [ply 28](http://localhost:5173/analysis?game_id=684180&ply=28) | [board](http://localhost:5173/analysis?fen=r2q1r2/pbp2pbk/1p1p1npp/1P1Pp3/2P1P3/4BN1P/P2QNPP1/R3K2R%20b%20-%20-%201%2015) |
| 785 | allowed | DISCOVERED_ATTACK | 1 | `18... Nxg4 19. hxg4 Bxa1 20. Qd2 Rh8 21. Nc3 Kg8 22. Bd4 Bxc3 23. Qxc3 Rh7 24. Bf6` | [ply 34](http://localhost:5173/analysis?game_id=684180&ply=34) | [board](http://localhost:5173/analysis?fen=r2q1r2/pbp2pbk/1p1p1npp/1P1P4/2P1p1N1/4B2P/P1Q1NPP1/R3K2R%20b%20-%20-%201%2018) |
| 786 | allowed | PIN | 2 | `31. Qd3+ Re4 32. c7 Qc5 33. Re1 Qc4 34. Qb1 Qxc7 35. Rxe4 Nxe4 36. Qxe4+ Kg8` | [ply 59](http://localhost:5173/analysis?game_id=684184&ply=59) | [board](http://localhost:5173/analysis?fen=8/3Q2pk/p1P5/4P1np/5r2/P6P/5qP1/3R3K%20w%20-%20-%201%2031) |
| 787 | missed | CAPTURING_DEFENDER | 2 | `7. Bxf6 Qxf6 8. Nxd5 Qd8 9. e4 Nc6 10. Rc1 Be6 11. Bc4 cxd4` | [ply 12](http://localhost:5173/analysis?game_id=684191&ply=12) | [board](http://localhost:5173/analysis?fen=rnb1kb1r/pp3ppp/1q3n2/2pp2B1/3P4/2N2N2/PP2PPPP/R2QKB1R%20w%20-%20-%200%207) |
| 788 | missed | CLEARANCE | 4 | `9. Bxf6 Qxf6 10. e3 Bb4 11. Bb5+ Nc6 12. Rc1` | [ply 16](http://localhost:5173/analysis?game_id=684191&ply=16) | [board](http://localhost:5173/analysis?fen=rnb1k2r/pp3ppp/1q3n2/2bp2B1/3N4/1PN5/P3PPPP/R2QKB1R%20w%20-%20-%200%209) |
| 789 | allowed | ATTRACTION | 0 | `26... Qxe3 27. Rxe3 Bf4 28. Ke2 Bxe3 29. Kxe3 Kf8 30. Ra2 Re7 31. Nf4 Bf5 32. g4` | [ply 50](http://localhost:5173/analysis?game_id=684191&ply=50) | [board](http://localhost:5173/analysis?fen=3rr1k1/p4ppp/1qp3b1/8/2B1P3/1P1NQP2/3R2Pb/4RK2%20b%20-%20-%201%2026) |
| 790 | missed | CLEARANCE | 4 | `8. Qb3 Qe6 9. e3 g6 10. Bd3 Bg7 11. Rc1 c6` | [ply 14](http://localhost:5173/analysis?game_id=684193&ply=14) | [board](http://localhost:5173/analysis?fen=rn2kb1r/pbp2ppp/1p3q2/3p4/3P4/2N2N2/PP2PPPP/R2QKB1R%20w%20-%20-%200%208) |
| 791 | missed | PIN | 8 | `20... e5 21. Qd1 Nxf2 22. Qd2 Rad8 23. Qe3 Qg6 24. Qxe5 Nxh3+ 25. Kh2 Ng5 26. Ng3` | [ply 39](http://localhost:5173/analysis?game_id=684204&ply=39) | [board](http://localhost:5173/analysis?fen=r4rk1/6pp/p2qp3/3p3N/2pQn3/7P/PPP2PP1/R3R1K1%20b%20-%20-%200%2020) |
| 792 | allowed | PIN | 2 | `8. Nxe5 Nxe5 9. Re1 Be7 10. Rxe5` | [ply 13](http://localhost:5173/analysis?game_id=684213&ply=13) | [board](http://localhost:5173/analysis?fen=r2qkb1r/pp1n1ppp/5n2/3pp3/8/3P1N2/PPP2PPP/RNBQ1RK1%20w%20-%20-%200%208) |
| 793 | missed | CLEARANCE | 6 | `7... Qc7 8. Qe2 Rc8 9. Bd2 e6 10. c4 Be7 11. Nc3 dxc4 12. Nb5 Qb8 13. dxc4` | [ply 13](http://localhost:5173/analysis?game_id=684213&ply=13) | [board](http://localhost:5173/analysis?fen=r2qkb1r/pp1npppp/5n2/3p4/8/3P1N2/PPP2PPP/RNBQ1RK1%20b%20-%20-%200%207) |
| 794 | allowed | DISCOVERED_CHECK | 4 | `30. Nd2 Qd7 31. Kc1 Raf8 32. c4+ Kg8 33. Qb5 R2f5 34. Rhf1 dxc4 35. Rxf5 Rxf5` | [ply 57](http://localhost:5173/analysis?game_id=684227&ply=57) | [board](http://localhost:5173/analysis?fen=r6k/1p5p/2n1q1p1/3p4/2N5/2P5/PQK2r2/4R2R%20w%20-%20-%201%2030) |
| 795 | allowed | CLEARANCE | 2 | `32. Rxh7+ Kg8 33. Reh1 Ne5 34. Rh8+ Kf7 35. Qxb7+ Kf6 36. Qb6+ Kf5 37. Rxa8 Qxd2+` | [ply 61](http://localhost:5173/analysis?game_id=684227&ply=61) | [board](http://localhost:5173/analysis?fen=r6k/1p5p/2n3p1/3p4/5q2/2P5/PQ1N1r2/2K1R2R%20w%20-%20-%201%2032) |
| 796 | allowed | PIN | 0 | `37. Rxb8 h5 38. Rxf8+ Rxf8 39. d6 Nf2 40. Re1 Ng4 41. d7 Nf6 42. Re7 Kh8` | [ply 71](http://localhost:5173/analysis?game_id=684227&ply=71) | [board](http://localhost:5173/analysis?fen=1r2Rqk1/1Q5p/6p1/3P4/8/3n4/P2N1r2/1K5R%20w%20-%20-%201%2037) |
| 797 | missed | PIN | 2 | `8. cxd5 exd5 9. Bb5 Bb7 10. Qa4 Qd7 11. Nxd5 Qxd5 12. Rc1 Kd7 13. Ne5+ Bxe5` | [ply 14](http://localhost:5173/analysis?game_id=684263&ply=14) | [board](http://localhost:5173/analysis?fen=r1bqk2r/p1p2ppp/1pn1pb2/3p4/2PP4/2N1PN2/PP3PPP/R2QKB1R%20w%20-%20-%200%208) |
| 798 | allowed | SACRIFICE | 6 | `25. Qd4 Bxh5 26. Qxb6 cxb6 27. Rb3 Rxa4 28. Nd4 Be8 29. Bf3 h5 30. Bxg4 hxg4` | [ply 47](http://localhost:5173/analysis?game_id=684264&ply=47) | [board](http://localhost:5173/analysis?fen=r2r2k1/1pp2bpp/1q3p2/3P3P/Pp2PPn1/5R2/4N1B1/2RQ2K1%20w%20-%20-%201%2025) |
| 799 | missed | DISCOVERED_ATTACK | 7 | `24. Qh4 Rh8 25. Qe7 Qe6 26. Qg5 f5 27. exf6+ Qxf6 28. Qxd5 Rhf8 29. h3 c5` | [ply 46](http://localhost:5173/analysis?game_id=684268&ply=46) | [board](http://localhost:5173/analysis?fen=2r1r3/2p1Qpk1/p5p1/1p1pPq2/3P4/2P1P1R1/P5PP/R5K1%20w%20-%20-%200%2024) |
| 800 | missed | SACRIFICE | 2 | `35. Kxf2 Qxg4 36. a4 Qh3 37. c5 Qh2+ 38. Ke1 Qxg3+ 39. Kd2 Qg2+ 40. Ke1 bxc5` | [ply 68](http://localhost:5173/analysis?game_id=684292&ply=68) | [board](http://localhost:5173/analysis?fen=8/p5k1/1p3p2/6pq/2PP2Q1/4PKP1/P4r2/2R5%20w%20-%20-%200%2035) |
| 801 | missed | CLEARANCE | 8 | `15... g6 16. a3 h5 17. g3 h4 18. Nb4 Kg7 19. Nd3 Rh8 20. Bg2 Rh6 21. Qd2` | [ply 29](http://localhost:5173/analysis?game_id=684296&ply=29) | [board](http://localhost:5173/analysis?fen=r2q1rk1/1p3pp1/p1n1pb1p/3p4/3P4/2P2B2/PPN2PPP/R2QR1K1%20b%20-%20-%200%2015) |
| 802 | missed | CLEARANCE | 2 | `20... Rxc1 21. Bxc1 Rc8 22. Be3 Nc3 23. f4 h5 24. Nd4 Ne4 25. Ne2 Qb2 26. Rc1` | [ply 39](http://localhost:5173/analysis?game_id=684320&ply=39) | [board](http://localhost:5173/analysis?fen=2r2rk1/5ppp/p2bpq2/1p1p4/1P2n3/PP1Q3P/3BNPP1/2R2RK1%20b%20-%20-%200%2020) |
| 803 | allowed | PIN | 0 | `22. fxe6+ Kg6 23. Rxf6+ gxf6 24. Qg3+ Kh7 25. Qf4 Rg8 26. Qxf6 Rg7 27. Qf4 Kg8` | [ply 41](http://localhost:5173/analysis?game_id=684327&ply=41) | [board](http://localhost:5173/analysis?fen=r4b1r/pR2nkp1/4pq1p/5P2/4p3/1Q6/P5PP/5RK1%20w%20-%20-%201%2022) |
| 804 | missed | CLEARANCE | 8 | `21... Kg8 22. Qxe6+ Kh7 23. f6 Re8 24. Qf7 Nf5 25. g3 Bc5+ 26. Kg2 Rhf8 27. Qxg7+` | [ply 41](http://localhost:5173/analysis?game_id=684327&ply=41) | [board](http://localhost:5173/analysis?fen=r4b1r/pR2nkp1/4p2p/5P2/4p2q/1Q6/P5PP/5RK1%20b%20-%20-%200%2021) |
| 805 | allowed | FORK | 4 | `30. Rf7+ Kg6 31. Qxf5+ Kh6 32. Qxe4 Re8 33. Qxb1 Rxe6 34. Qf5 Rd6 35. Re7 Rf6` | [ply 57](http://localhost:5173/analysis?game_id=684327&ply=57) | [board](http://localhost:5173/analysis?fen=r7/p2R2b1/4Pk2/5np1/4p1Q1/8/P5PK/1r6%20w%20-%20-%201%2030) |
| 806 | missed | SACRIFICE | 4 | `32... Ne7 33. Rd1 Rf2 34. Kxf2 Bf8 35. Rf1 Kg7 36. Ke2 Ng6 37. Rf7+ Kh6 38. Qh1+` | [ply 63](http://localhost:5173/analysis?game_id=684327&ply=63) | [board](http://localhost:5173/analysis?fen=4r3/p2R2b1/4Pk2/5np1/4Q1P1/8/Pr6/6K1%20b%20-%20-%200%2032) |
| 807 | allowed | DISCOVERED_ATTACK | 7 | `8. Be3 Bxf3 9. gxf3 Qe6 10. a5 a6 11. Bxa6 Qxa6 12. Qxd4 e6 13. Qa4+ b5` | [ply 13](http://localhost:5173/analysis?game_id=684334&ply=13) | [board](http://localhost:5173/analysis?fen=r3kbnr/pp2pppp/1q6/3p4/P2n1Bb1/3B1N2/1PP2PPP/RN1QK2R%20w%20-%20-%201%208) |
| 808 | missed | CLEARANCE | 4 | `7... Bxf3 8. gxf3 e6 9. a5 Bd6 10. Be3 Nc6 11. a6 bxa6 12. Rg1 g6 13. Rxa6` | [ply 13](http://localhost:5173/analysis?game_id=684334&ply=13) | [board](http://localhost:5173/analysis?fen=r2qkbnr/pp2pppp/8/3p4/P2n1Bb1/3B1N2/1PP2PPP/RN1QK2R%20b%20-%20-%200%207) |
| 809 | allowed | HANGING_PIECE | 0 | `18... Kxf7` | [ply 34](http://localhost:5173/analysis?game_id=684337&ply=34) | [board](http://localhost:5173/analysis?fen=r4rk1/2pB1Np1/1p2p2p/3p4/P2P4/1qPQP3/5PPP/R5K1%20b%20-%20-%200%2018) |
| 810 | allowed | FORK | 2 | `22... Rxf2 23. Qg6 Rxg2+ 24. Qxg2 Qxb1+ 25. Qf1 Qg6+ 26. Qg2 Qh5 27. Be2 Qf5 28. Bb5` | [ply 42](http://localhost:5173/analysis?game_id=684337&ply=42) | [board](http://localhost:5173/analysis?fen=r4rk1/2p3p1/1p2p2p/1B1pP3/P2P4/2PQ4/q4PPP/1R4K1%20b%20-%20-%200%2022) |
| 811 | allowed | CLEARANCE | 2 | `24... Rxf1+ 25. Qxf1 Rf8 26. Qd1 Qe4 27. Qg1 Rf4 28. h3 Kf7 29. Kh2 Ke7 30. Kh1` | [ply 46](http://localhost:5173/analysis?game_id=684337&ply=46) | [board](http://localhost:5173/analysis?fen=r4rk1/2p3p1/1p2p2p/1B1pP3/P2P3q/2PQ4/6PP/5R1K%20b%20-%20-%201%2024) |
| 812 | allowed | MATE | 4 | `26... Qe1+ 27. Qf1 Rxf1+ 28. Bxf1 Qxf1#` | [ply 50](http://localhost:5173/analysis?game_id=684337&ply=50) | [board](http://localhost:5173/analysis?fen=5rk1/2p3p1/1p2p2p/1B1pP3/P2P3q/2PQ4/6PP/7K%20b%20-%20-%201%2026) |
| 813 | missed | SACRIFICE | 2 | `27. Qd1 cxb5 28. h3 bxa4 29. c4 dxc4 30. d5 Qf4 31. dxe6 Qf1+ 32. Qxf1 Rxf1+` | [ply 52](http://localhost:5173/analysis?game_id=684337&ply=52) | [board](http://localhost:5173/analysis?fen=5rk1/6p1/1pp1p2p/1B1pP3/P2P3q/2PQ4/6PP/7K%20w%20-%20-%200%2027) |
| 814 | missed | CAPTURING_DEFENDER | 10 | `11... e4 12. Nd4 Ne5` | [ply 21](http://localhost:5173/analysis?game_id=684342&ply=21) | [board](http://localhost:5173/analysis?fen=r1bq1rk1/pp3ppp/2n5/1B1np3/8/P1P1PN2/3Q1PPP/R1B1K2R%20b%20-%20-%200%2011) |
| 815 | allowed | MATE | 6 | `47. Rc5 Re8 48. c8=Q Re5 49. Rxe5 g3 50. fxg3#` | [ply 91](http://localhost:5173/analysis?game_id=684342&ply=91) | [board](http://localhost:5173/analysis?fen=1Br5/2P5/8/8/6pk/2R5/5PKP/8%20w%20-%20-%201%2047) |
| 816 | missed | SACRIFICE | 6 | `47... Kh5 48. Rd8 Rxc7 49. Rd5+ Kg6 50. Bxc7 Kf6 51. Re5 Kf7 52. Kg3 Kg7 53. Kxg4` | [ply 93](http://localhost:5173/analysis?game_id=684342&ply=93) | [board](http://localhost:5173/analysis?fen=1Br5/2P5/8/8/6pk/3R4/5PKP/8%20b%20-%20-%200%2047) |
| 817 | allowed | PIN | 0 | `19. Nf5 Qd7 20. b4 g6 21. Rad1 Rd8 22. Ne3 Be7 23. Nxd5 exd5 24. Qf6 Rg8` | [ply 35](http://localhost:5173/analysis?game_id=684344&ply=35) | [board](http://localhost:5173/analysis?fen=r3kb1r/5ppp/p2qp3/2pp4/3N4/1P3Q2/P4PPP/R3R1K1%20w%20-%20-%200%2019) |
| 818 | allowed | PIN | 0 | `20. Qxd5 Rd8 21. Qc4 g6 22. Ne3 Be7 23. Qxa6` | [ply 37](http://localhost:5173/analysis?game_id=684344&ply=37) | [board](http://localhost:5173/analysis?fen=r3kb1r/2q2ppp/p3p3/2pp1N2/8/1P3Q2/P4PPP/R3R1K1%20w%20-%20-%201%2020) |
| 819 | allowed | PIN | 0 | `21. Qxd5` | [ply 39](http://localhost:5173/analysis?game_id=684344&ply=39) | [board](http://localhost:5173/analysis?fen=r3k2r/2q2ppp/p2bp3/2pp4/8/1P3QN1/P4PPP/R3R1K1%20w%20-%20-%201%2021) |
| 820 | allowed | PIN | 0 | `32. Nh5 Rb4 33. Nf6+ Kg7 34. Nxe8+ Qxe8 35. g3 Rg4 36. Qd2 d4 37. Rxe6 Qc6+` | [ply 61](http://localhost:5173/analysis?game_id=684344&ply=61) | [board](http://localhost:5173/analysis?fen=4r1k1/5q1p/p2bp1p1/3p1pQ1/5r2/6N1/P3R1P1/4R2K%20w%20-%20-%201%2032) |
| 821 | missed | DISCOVERED_ATTACK | 1 | `31... Rg4 32. Rxe6 Bxg3 33. Qe3 Rh4+ 34. Kg1 Bxe1 35. Rxa6 Re4 36. Qd3 Rfe8 37. g3` | [ply 61](http://localhost:5173/analysis?game_id=684344&ply=61) | [board](http://localhost:5173/analysis?fen=5rk1/5q1p/p2bp1p1/3p1pQ1/5r2/6N1/P3R1P1/4R2K%20b%20-%20-%200%2031) |
| 822 | allowed | DEFLECTION | 2 | `22... Rxf2 23. Rxf2 Qxa1+ 24. Kh2 Rxf2 25. Qxf2 b6 26. Qh4 Qf6 27. Qg4 Qe7 28. a4` | [ply 42](http://localhost:5173/analysis?game_id=684353&ply=42) | [board](http://localhost:5173/analysis?fen=5r2/ppp2rkp/3p2p1/3P4/2P5/P3Q2P/1q3PP1/R4RK1%20b%20-%20-%201%2022) |
| 823 | missed | SKEWER | 2 | `22. Rab1 Qxa3 23. Rxb7 Qc5 24. Rb5 Qa3 25. Qd4+ Kg8 26. Qd2 Rf4 27. Ra5 Qb3` | [ply 42](http://localhost:5173/analysis?game_id=684353&ply=42) | [board](http://localhost:5173/analysis?fen=5r2/ppp2rkp/3p2p1/3P4/2P1Q3/P6P/1q3PP1/R4RK1%20w%20-%20-%200%2022) |
| 824 | allowed | PIN | 2 | `19. Rxb4 Bxe2 20. Rxb6 Rxb6 21. Bf2 Bh5 22. Rb1 Rxb1+ 23. Nxb1 Kf8 24. Qxc6 Kg8` | [ply 35](http://localhost:5173/analysis?game_id=684356&ply=35) | [board](http://localhost:5173/analysis?fen=1r2k2r/5pp1/pqp1p3/3pPn2/Qb1P2b1/P1N1B3/4N2P/RR4K1%20w%20-%20-%201%2019) |
| 825 | allowed | CLEARANCE | 8 | `20. Nxe2 a5 21. axb4 axb4 22. Qd1` | [ply 37](http://localhost:5173/analysis?game_id=684356&ply=37) | [board](http://localhost:5173/analysis?fen=1r2k2r/5pp1/pqp1p3/3pPn2/Qb1P4/P1N5/4bB1P/RR4K1%20w%20-%20-%200%2020) |
| 826 | missed | SACRIFICE | 2 | `19... a5 20. axb4 axb4 21. Rxb4 Qxb4 22. Qxb4 Rxb4 23. Ra8+ Kd7 24. Rxh8 c5 25. dxc5` | [ply 37](http://localhost:5173/analysis?game_id=684356&ply=37) | [board](http://localhost:5173/analysis?fen=1r2k2r/5pp1/pqp1p3/3pPn2/Qb1P2b1/P1N5/4NB1P/RR4K1%20b%20-%20-%200%2019) |
| 827 | allowed | HANGING_PIECE | 0 | `30. Rxd4` | [ply 57](http://localhost:5173/analysis?game_id=684356&ply=57) | [board](http://localhost:5173/analysis?fen=7r/3k1pp1/q1p1p3/PpQpP3/1R1n4/8/8/2R2KBr%20w%20-%20-%200%2030) |
| 828 | allowed | DEFLECTION | 4 | `32. Qb8+ Kd7 33. Qd6+ Ke8 34. Rxc6 Qb7 35. Rxh4 Rxh4 36. Rc7 Qxc7 37. Qxc7 Rc4` | [ply 61](http://localhost:5173/analysis?game_id=684356&ply=61) | [board](http://localhost:5173/analysis?fen=4k3/5pp1/q1pQp3/Pp1pP3/3R3r/8/8/2R2KBr%20w%20-%20-%201%2032) |
| 829 | missed | DISCOVERED_CHECK | 0 | `31... b4+` | [ply 61](http://localhost:5173/analysis?game_id=684356&ply=61) | [board](http://localhost:5173/analysis?fen=4k2r/5pp1/q1pQp3/Pp1pP3/3R4/8/8/2R2KBr%20b%20-%20-%200%2031) |
| 830 | allowed | MATE | 10 | `34. Rxa6 Rf4+ 35. Bf2 Rxf2+ 36. Kxf2 f6 37. Qxe6+ Kd8 38. Ra8+ Kc7 39. Qc8#` | [ply 65](http://localhost:5173/analysis?game_id=684356&ply=65) | [board](http://localhost:5173/analysis?fen=4k3/5pp1/q1RQp3/P2pP3/1p5r/8/8/5KB1%20w%20-%20-%200%2034) |
| 831 | missed | SACRIFICE | 10 | `33... Rf4+ 34. Ke2 Qa8 35. Rc7 Qd8 36. Qc6+ Kf8 37. Rc8 g5 38. Rxd8+ Kg7 39. Qe8` | [ply 65](http://localhost:5173/analysis?game_id=684356&ply=65) | [board](http://localhost:5173/analysis?fen=4k3/5pp1/q1RQp3/Pp1pP3/7r/8/8/5KB1%20b%20-%20-%200%2033) |
| 832 | allowed | CLEARANCE | 4 | `15... Bxc5 16. Kh1 a5 17. Na4 Ba7 18. Rac1 f6 19. Qc3 fxe5 20. Qxe5 Qe7 21. Nc5` | [ply 28](http://localhost:5173/analysis?game_id=684361&ply=28) | [board](http://localhost:5173/analysis?fen=r2qk3/pp2bpr1/2p1p2p/2PpPp2/5P2/2NQP3/PP4PP/R4RK1%20b%20-%20-%200%2015) |
| 833 | allowed | MATE | 4 | `30... Rb1+ 31. Rc1 Rxc1+ 32. Qf1 Rxf1#` | [ply 58](http://localhost:5173/analysis?game_id=684361&ply=58) | [board](http://localhost:5173/analysis?fen=1r6/2k2pr1/2p1p2p/p2pPp2/5Pq1/b3P3/2R1Q1PP/7K%20b%20-%20-%201%2030) |
| 834 | allowed | INTERFERENCE | 4 | `25... Rac8 26. e4 Nc3 27. Re1 Qxa3 28. Bh4 Rd7 29. Ne5 Rxd4 30. Qf3 Qf8 31. h3` | [ply 48](http://localhost:5173/analysis?game_id=684369&ply=48) | [board](http://localhost:5173/analysis?fen=r2r2k1/4qpp1/p3p2p/1p1n4/3P4/P2QPNB1/5PPP/1R4K1%20b%20-%20-%201%2025) |
| 835 | missed | FORK | 2 | `25. e4 Nb6 26. Nc6 Qd7 27. Nxd8 Rxd8 28. Rd1 Qc8 29. h3 Na4 30. Qf3 Nb2` | [ply 48](http://localhost:5173/analysis?game_id=684369&ply=48) | [board](http://localhost:5173/analysis?fen=r2r2k1/4qpp1/p3p2p/1p1nN3/3P4/P2QP1B1/5PPP/1R4K1%20w%20-%20-%200%2025) |
| 836 | missed | PIN | 0 | `35. Nh6+` | [ply 68](http://localhost:5173/analysis?game_id=684369&ply=68) | [board](http://localhost:5173/analysis?fen=r3rqk1/5Np1/4ppQ1/p7/1n1P3B/4P3/5PPP/1R4K1%20w%20-%20-%200%2035) |
| 837 | allowed | CLEARANCE | 6 | `53... Rb1 54. Ke3 Rxa1 55. Kxd2 Rf1 56. Kd3 a1=Q 57. Ke2 Qe1+ 58. Kd3 Rxf2 59. Kc4` | [ply 104](http://localhost:5173/analysis?game_id=684369&ply=104) | [board](http://localhost:5173/analysis?fen=8/7k/4p1pP/4P1P1/1r2P3/5K2/p2r1P2/R7%20b%20-%20-%200%2053) |
| 838 | missed | SACRIFICE | 8 | `53. Rc1 Rd7 54. Ra1 Ra7 55. Ke2 Rb1 56. Rxa2 Rxa2+ 57. Kd3 Rxf2 58. Kc3 Rg2` | [ply 104](http://localhost:5173/analysis?game_id=684369&ply=104) | [board](http://localhost:5173/analysis?fen=8/7k/4p1pP/4P1P1/1r6/4PK2/p2r1P2/R7%20w%20-%20-%200%2053) |
| 839 | missed | EN_PASSANT | 4 | `9. d5 Na5 10. Nxb5 e5 11. dxe6 Bb4+ 12. Bd2 Bxd2+ 13. Qxd2 fxe6 14. Qxd8+ Kxd8` | [ply 16](http://localhost:5173/analysis?game_id=684376&ply=16) | [board](http://localhost:5173/analysis?fen=r2qkb1r/1bp1pppp/2n2n2/1p6/2pPPB2/2N2N2/1P3PPP/R2QKB1R%20w%20-%20-%200%209) |
| 840 | allowed | DISCOVERED_ATTACK | 3 | `16... Nxd4 17. Bf3 Ne2+ 18. Kh1 Qxd2 19. Bxb7 Nxc3 20. Qa1 Rd8 21. f4 Nd1 22. f5` | [ply 30](http://localhost:5173/analysis?game_id=684376&ply=30) | [board](http://localhost:5173/analysis?fen=5rk1/1bp1bppp/2n1p3/1p1qP3/2pP4/2P3B1/3NBPPP/1Q3RK1%20b%20-%20-%201%2016) |
| 841 | missed | DEFLECTION | 8 | `16. Bd1 Na5 17. Bc2 h6 18. Re1 b4 19. Bh4 Bxh4 20. Qxb4 Bd8 21. Bh7+ Kxh7` | [ply 30](http://localhost:5173/analysis?game_id=684376&ply=30) | [board](http://localhost:5173/analysis?fen=5rk1/1bp1bppp/2n1p3/1p1qP3/2pP4/2P2NB1/4BPPP/1Q3RK1%20w%20-%20-%200%2016) |
| 842 | allowed | CLEARANCE | 6 | `26... cxb4 27. Ne4 c3 28. h4 b3 29. Nxc3 Qb4 30. Ne4 b2 31. h5 Kg7 32. Kh2` | [ply 50](http://localhost:5173/analysis?game_id=684376&ply=50) | [board](http://localhost:5173/analysis?fen=5rk1/1q3p1p/b3p1p1/2p1P1N1/1Pp5/8/5PPP/1Q1R2K1%20b%20-%20-%200%2026) |
| 843 | allowed | CLEARANCE | 10 | `15... Nxe5 16. Bxb7 Nxf3+ 17. Bxf3 Rac8 18. Qa4 Qb6 19. g3 Rfd8 20. Rfd1 Bf8 21. b3` | [ply 28](http://localhost:5173/analysis?game_id=684378&ply=28) | [board](http://localhost:5173/analysis?fen=r4rk1/pb2ppbp/2n2qp1/3BB3/1p1P4/4PN2/PP3PPP/2RQ1RK1%20b%20-%20-%201%2015) |
| 844 | allowed | EN_PASSANT | 0 | `23... bxa3 24. bxa3` | [ply 44](http://localhost:5173/analysis?game_id=684378&ply=44) | [board](http://localhost:5173/analysis?fen=r2r2k1/2R2p1p/4pbp1/p7/Pp1P4/1B2P3/1P3PPP/2R3K1%20b%20-%20a3%200%2023) |
| 845 | allowed | CLEARANCE | 10 | `2... exd4 3. Qxd4 Nc6 4. Qd1 Nf6 5. Nc3 Bb4 6. Bd2` | [ply 2](http://localhost:5173/analysis?game_id=684384&ply=2) | [board](http://localhost:5173/analysis?fen=rnbqkbnr/pppp1ppp/8/4p3/2PP4/8/PP2PPPP/RNBQKBNR%20b%20-%20-%200%202) |
| 846 | allowed | SKEWER | 2 | `22... Rae8 23. Nc3 Rxe3 24. Nb5 Rfe8 25. Nxc7 Re1+ 26. Rxe1 Rxe1+ 27. Kf2 Rc1` | [ply 42](http://localhost:5173/analysis?game_id=684384&ply=42) | [board](http://localhost:5173/analysis?fen=r4r2/ppp2pk1/3p2pp/8/2P1NP2/P3P2P/1P4P1/3R2K1%20b%20-%20-%200%2022) |
| 847 | missed | CLEARANCE | 10 | `28. Ne4 g6 29. g3 h6 30. Bb3 Rf5 31. Rxf5 gxf5 32. Nc5 Bxc5 33. Re8+ Kxd7` | [ply 54](http://localhost:5173/analysis?game_id=684393&ply=54) | [board](http://localhost:5173/analysis?fen=1r1k1r2/p2P2pp/1b6/3R4/2B5/2N5/5PPP/4R1K1%20w%20-%20-%200%2028) |
| 848 | missed | SKEWER | 2 | `11. Rb1 Qa3 12. Rxb7 e6 13. c5 Ne4 14. Rb3 Qa5` | [ply 20](http://localhost:5173/analysis?game_id=684394&ply=20) | [board](http://localhost:5173/analysis?fen=r3kb1r/pp2ppp1/2p2n1p/3p4/2PP4/2NQPN2/Pq3PPP/R3K2R%20w%20-%20-%200%2011) |
| 849 | missed | SACRIFICE | 4 | `13. cxd5 Nxc3 14. Rxb7 cxd5 15. Ne5 g6 16. Rfb1 Rd8 17. R7b3 Qd6 18. Rxc3 Bg7` | [ply 24](http://localhost:5173/analysis?game_id=684394&ply=24) | [board](http://localhost:5173/analysis?fen=r3kb1r/pp2ppp1/2p4p/3p4/2PPn3/q1NQPN2/P4PPP/1R3RK1%20w%20-%20-%200%2013) |
| 850 | missed | SKEWER | 10 | `20. Ne5+ Kc7 21. Qb1 c5 22. e4 Qxd4 23. Nxf7 Kd7 24. Rd8+ Ke6 25. Rxd4 Kxf7` | [ply 38](http://localhost:5173/analysis?game_id=684394&ply=38) | [board](http://localhost:5173/analysis?fen=1R3b1r/p2kppp1/2p4p/3q4/3PQ3/4PN2/5PPP/6K1%20w%20-%20-%200%2020) |
| 851 | allowed | CLEARANCE | 4 | `10... Bb4+ 11. Nd2 Bg4 12. f3 Rad8 13. Bd3 Rxd3 14. cxd3 Bxd2+ 15. Kf2 Bc1+ 16. Kg3` | [ply 18](http://localhost:5173/analysis?game_id=684406&ply=18) | [board](http://localhost:5173/analysis?fen=r1b2rk1/ppN2ppp/2n5/2b5/8/4PN2/PqP2PPP/R2QKB1R%20b%20-%20-%200%2010) |
| 852 | missed | SACRIFICE | 4 | `16. Ke3 Qb6 17. Ke2 Qxc7 18. Kf1 Rad8 19. h4 Bxd3+ 20. cxd3 Rxd3 21. Qe2 h6` | [ply 30](http://localhost:5173/analysis?game_id=684406&ply=30) | [board](http://localhost:5173/analysis?fen=r5k1/ppN2ppp/8/5b2/3r4/3B4/PqPK1PPP/R2Q3R%20w%20-%20-%200%2016) |
| 853 | missed | CLEARANCE | 4 | `15... h5 16. h3 Qf6 17. Qe2 Rfd8 18. Rfd1 Rd7 19. Rd2 b5 20. Rad1 Rad8 21. f4` | [ply 29](http://localhost:5173/analysis?game_id=684409&ply=29) | [board](http://localhost:5173/analysis?fen=r2q1rk1/pp3ppp/4p1n1/3p4/2p5/2P1PPB1/PPQ2P1P/R4RK1%20b%20-%20-%200%2015) |
| 854 | allowed | PIN | 8 | `29. Rxf7+ Kh6 30. Qe5 g5 31. Qxe6+ Rg6 32. fxg5+ Qxg5 33. hxg5+ Kxg5 34. Qe7+ Rf6` | [ply 55](http://localhost:5173/analysis?game_id=684409&ply=55) | [board](http://localhost:5173/analysis?fen=1r1q2r1/1pR2p1k/p3p1p1/P6p/4PP1P/2Q3B1/1P3P2/4R1K1%20w%20-%20-%201%2029) |
| 855 | missed | PIN | 10 | `45... Ra2 46. f5 e5 47. Rd5 e4 48. Rd6+ Kg7 49. fxg6 Ra3 50. Be5+ Kg8 51. Rf6` | [ply 89](http://localhost:5173/analysis?game_id=684409&ply=89) | [board](http://localhost:5173/analysis?fen=5r2/PR1R1p2/4pkp1/7p/5P1P/5PBK/8/r7%20b%20-%20-%200%2045) |
| 856 | missed | PIN | 4 | `5... Qh4+ 6. Ke2 Qxe4+ 7. Be3 Bc5 8. Qd3 Qxe3+ 9. Qxe3 Bxe3 10. Kxe3 cxd5 11. Nf3` | [ply 9](http://localhost:5173/analysis?game_id=684410&ply=9) | [board](http://localhost:5173/analysis?fen=rnbqkbnr/pp3ppp/2p5/3Pp3/4P3/8/PPP3PP/RNBQKBNR%20b%20-%20-%200%205) |
| 857 | allowed | CLEARANCE | 4 | `15. Kd2 Rd8 16. Qe1 Qf6 17. Rd1 cxd5 18. Nxd5 Nxd5 19. exd5 Rxd5+ 20. Bd3 Nc6` | [ply 27](http://localhost:5173/analysis?game_id=684410&ply=27) | [board](http://localhost:5173/analysis?fen=rn3rk1/pp3pp1/2p4p/3Pp3/4Pn1q/2N2P1P/PPP1K3/R2Q1B1R%20w%20-%20-%201%2015) |
| 858 | allowed | SACRIFICE | 2 | `19. h4 Nxd5+ 20. Kf2 Qf6 21. exd5 Nd4 22. Qe4 Qb6 23. b4 a5 24. bxa5 Qxa5` | [ply 35](http://localhost:5173/analysis?game_id=684410&ply=35) | [board](http://localhost:5173/analysis?fen=r2r2k1/pp3pp1/2n4p/3Np1q1/2P1Pn2/4KP1P/PP6/R3QB1R%20w%20-%20-%201%2019) |
| 859 | missed | ATTRACTION | 8 | `40... Ke7 41. Ke2 h4 42. Kf1 h3 43. Rd1 h2 44. Kg2 h1=Q+ 45. Kxh1 Qh8+ 46. Kg2` | [ply 79](http://localhost:5173/analysis?game_id=684410&ply=79) | [board](http://localhost:5173/analysis?fen=3q4/pp1P4/4kp2/3Rp2p/1P2P1P1/P3KP2/8/8%20b%20-%20-%200%2040) |
| 860 | missed | FORK | 0 | `17... Bb3 18. Nc3 Bxd1 19. Nxd1 Nd4 20. Nxd4 Bxd4 21. Ne3 Bxe3 22. Bxe3 Rfd8 23. Re1` | [ply 33](http://localhost:5173/analysis?game_id=684414&ply=33) | [board](http://localhost:5173/analysis?fen=r4rk1/bp3ppp/p1n1b3/4Pp2/N4B2/P4N2/1P3PPP/3R1RK1%20b%20-%20-%200%2017) |
| 861 | missed | PIN | 2 | `16... Qe6+ 17. Qe3 f4 18. Qe2 Bd6` | [ply 31](http://localhost:5173/analysis?game_id=684420&ply=31) | [board](http://localhost:5173/analysis?fen=r3kb1r/1p3ppp/pq6/3p1p2/1P1B1Q2/P1N4P/2P2PP1/R3K2R%20b%20-%20-%200%2016) |
| 862 | missed | CLEARANCE | 8 | `11... Nfd7 12. Rd2 h6 13. Bf4 Nb6 14. c4 Na6 15. Be2 Rd8 16. Be3 Rxd2 17. Kxd2` | [ply 21](http://localhost:5173/analysis?game_id=684421&ply=21) | [board](http://localhost:5173/analysis?fen=rn2k2r/pp3ppp/2p1pnb1/4P1B1/7P/6N1/PPP2PP1/3RKB1R%20b%20-%20-%200%2011) |
| 863 | allowed | PIN | 6 | `12. Qg4 Qe5 13. Rfe1 h5 14. Rxe5 hxg4 15. Nxd5 Rd8 16. Ne3 Nf6 17. Rc5 Rh5` | [ply 21](http://localhost:5173/analysis?game_id=684425&ply=21) | [board](http://localhost:5173/analysis?fen=r3k1nr/1p3ppp/p2qp3/3p4/3n4/2NB4/PPP2PPP/R2Q1RK1%20w%20-%20-%200%2012) |
| 864 | allowed | CLEARANCE | 6 | `18. Rxe4 Qg7 19. Rg4 Qf8 20. Qf2 e5 21. Rh4 f5 22. Rh5 Kb8 23. Rxf5 Qg7` | [ply 33](http://localhost:5173/analysis?game_id=684425&ply=33) | [board](http://localhost:5173/analysis?fen=2kr3r/1p3p1p/p1n1p3/3p2q1/4n2Q/2NB1P2/PPP3PP/R3R1K1%20w%20-%20-%201%2018) |
| 865 | missed | SKEWER | 2 | `26... Rg1+ 27. Kf2 Rxe1 28. Rxe1 Nxe1 29. Kxe1 Rc8 30. Nc3 h4 31. Kf2 f5 32. Bf3` | [ply 51](http://localhost:5173/analysis?game_id=684425&ply=51) | [board](http://localhost:5173/analysis?fen=1k4rr/1p3p2/p3p3/7p/N3B3/5n2/PP5P/2R1RK2%20b%20-%20-%200%2026) |
| 866 | allowed | FORK | 0 | `17... Qxb4+ 18. Ke2 Qxb6 19. Rhb1 Qd6 20. Ra6 Qe7 21. Ne5 Rc8 22. Qd1` | [ply 32](http://localhost:5173/analysis?game_id=684428&ply=32) | [board](http://localhost:5173/analysis?fen=r3k2r/p2bqppp/1B2p3/3p3n/1P1P4/3BPN2/2Q2PPP/R3K2R%20b%20-%20-%200%2017) |
| 867 | missed | CLEARANCE | 4 | `17. Ne5` | [ply 32](http://localhost:5173/analysis?game_id=684428&ply=32) | [board](http://localhost:5173/analysis?fen=r3k2r/p1Bbqppp/1p2p3/3p3n/1P1P4/3BPN2/2Q2PPP/R3K2R%20w%20-%20-%200%2017) |
| 868 | allowed | CLEARANCE | 10 | `13... Nxd3 14. Qxd3 Re8 15. Rfd1 f6 16. Bf4 cxd4 17. exd4 Nb6 18. Bc7 Bd7 19. h3` | [ply 24](http://localhost:5173/analysis?game_id=684434&ply=24) | [board](http://localhost:5173/analysis?fen=r1b2rk1/pp1n1ppp/4p3/q1p3B1/1nPP4/PQ1BPN2/5PPP/R4RK1%20b%20-%20-%200%2013) |
| 869 | allowed | CLEARANCE | 6 | `23... Nb6 24. Qa7+ Kc8 25. Qa6+ Kd7 26. Ra5 Rb8 27. Qb5+ Kd8 28. Qxf5 hxg3 29. fxg3` | [ply 44](http://localhost:5173/analysis?game_id=684442&ply=44) | [board](http://localhost:5173/analysis?fen=1k1r3r/2pnq3/Q7/5pp1/R2Pp2p/P3P1P1/1P3PP1/5RK1%20b%20-%20-%201%2023) |
| 870 | allowed | PIN | 10 | `25... hxg3 26. fxg3 Qd6 27. Rxf5 Rdf8 28. Qa5 Qh6 29. a4 Qh1+ 30. Kf2 Qh7 31. Rxf8+` | [ply 48](http://localhost:5173/analysis?game_id=684442&ply=48) | [board](http://localhost:5173/analysis?fen=2kr3r/Q1p1q3/1n6/5pp1/1R1Pp2p/P3P1P1/1P3PP1/5RK1%20b%20-%20-%201%2025) |
| 871 | missed | PIN | 10 | `25. Qa6+ Kd7 26. Ra5 Rb8 27. Qb5+ Kd8 28. Qxf5 hxg3 29. fxg3 Nc4 30. Ra8 Rxa8` | [ply 48](http://localhost:5173/analysis?game_id=684442&ply=48) | [board](http://localhost:5173/analysis?fen=2kr3r/Q1p1q3/1n6/5pp1/R2Pp2p/P3P1P1/1P3PP1/5RK1%20w%20-%20-%200%2025) |
| 872 | missed | CLEARANCE | 4 | `19. dxc6 Bxc6` | [ply 36](http://localhost:5173/analysis?game_id=684448&ply=36) | [board](http://localhost:5173/analysis?fen=r2q1r2/1b3pk1/1ppp1npp/p2Pp3/2P5/1P2QN1P/P3BPP1/R3K2R%20w%20-%20-%200%2019) |
| 873 | missed | INTERMEZZO | 10 | `21. f4 d4 22. Qd3 Bc8` | [ply 40](http://localhost:5173/analysis?game_id=684448&ply=40) | [board](http://localhost:5173/analysis?fen=r2q1r2/1b3pk1/1p1p1np1/p2pp1Np/2P4P/1P2Q3/P3BPP1/R3K2R%20w%20-%20-%200%2021) |
| 874 | allowed | CLEARANCE | 2 | `23. Be5 h5 24. Re4 Nc6 25. Bf6 Rd6 26. Rc1 Nfxd4 27. Re3 e5 28. Bxe5 Nxe5` | [ply 43](http://localhost:5173/analysis?game_id=684449&ply=43) | [board](http://localhost:5173/analysis?fen=2rr2k1/p4p1p/4p1p1/5n2/1nBP1BR1/1P3P2/1K3P1P/6R1%20w%20-%20-%200%2023) |
| 875 | allowed | SKEWER | 2 | `29. Rh6+ Kg5 30. Rxc6 Re8 31. cxb5 Re2+ 32. Kd1 Rxf2 33. a4 Ra2 34. Ke1 Kg4` | [ply 55](http://localhost:5173/analysis?game_id=684456&ply=55) | [board](http://localhost:5173/analysis?fen=3r4/p7/2p2k2/1p3p1R/2P2p2/2P5/P1K2P2/8%20w%20-%20-%200%2029) |
| 876 | missed | CAPTURING_DEFENDER | 6 | `5... Qa5+ 6. Bd2 Qf5 7. Be2 Bxf3 8. Bxf3 Nxd4 9. Bxb7 Nc2+ 10. Kf1 Qd3+ 11. Qe2` | [ply 9](http://localhost:5173/analysis?game_id=684458&ply=9) | [board](http://localhost:5173/analysis?fen=r3kbnr/ppp1pppp/2n5/3q4/2PP2b1/5N2/PP3PPP/RNBQKB1R%20b%20-%20-%200%205) |
| 877 | allowed | DISCOVERED_ATTACK | 1 | `11... Nxd5 12. cxd5 Bxg5 13. Qc2 h6` | [ply 20](http://localhost:5173/analysis?game_id=684466&ply=20) | [board](http://localhost:5173/analysis?fen=r2qk2r/pp2bppp/5n2/2pPp1B1/2P3b1/2NB4/PP1Q1PPP/R3K2R%20b%20-%20-%201%2011) |
| 878 | allowed | CLEARANCE | 2 | `29. Qc2 Qb6 30. Rb3 Qd4 31. Rc3` | [ply 55](http://localhost:5173/analysis?game_id=684473&ply=55) | [board](http://localhost:5173/analysis?fen=rr6/ppk5/2p1pb1p/3p4/3q1P2/1QRB2P1/PP5P/1KR5%20w%20-%20-%201%2029) |
| 879 | missed | DISCOVERED_ATTACK | 1 | `28... Qb6 29. Qa3 Bxc3 30. Qxc3 Rad8 31. f5 d4 32. Qe1 Kb8 33. Qxe6 Qa5 34. Rf1` | [ply 55](http://localhost:5173/analysis?game_id=684473&ply=55) | [board](http://localhost:5173/analysis?fen=r6r/ppk5/2p1pb1p/3p4/3q1P2/1QRB2P1/PP5P/1KR5%20b%20-%20-%200%2028) |
| 880 | allowed | PIN | 0 | `31. Qxd5 Bxc3 32. Qf7+ Kb6 33. Qb3+ Kc7 34. Qf7+` | [ply 59](http://localhost:5173/analysis?game_id=684473&ply=59) | [board](http://localhost:5173/analysis?fen=rr6/ppk5/2p2b1p/3p1B2/8/1QR3P1/PP3q1P/1KR5%20w%20-%20-%201%2031) |
| 881 | missed | CLEARANCE | 4 | `30... Rd8 31. Qc2 Rd6 32. a3 Re8 33. Rb3 Bg5 34. Rd1 Qe5 35. h4 Bd8 36. Ka2` | [ply 59](http://localhost:5173/analysis?game_id=684473&ply=59) | [board](http://localhost:5173/analysis?fen=rr6/ppk5/2p2b1p/3p1B2/3q4/1QR3P1/PP5P/1KR5%20b%20-%20-%200%2030) |
| 882 | missed | SACRIFICE | 4 | `40... Kc5 41. Qxe6 Rxa5 42. Rxa5+ Kxb6 43. Rxd5 Qh2+ 44. Rd2 Qxh4 45. Qe3+ Kb5 46. Qd3+` | [ply 79](http://localhost:5173/analysis?game_id=684474&ply=79) | [board](http://localhost:5173/analysis?fen=1q6/5Q1p/rPpkp1p1/P2p2P1/7P/2P2P2/2K5/R7%20b%20-%20-%200%2040) |
| 883 | allowed | PROMOTION | 0 | `51. a8=Q Qf2+ 52. Kd1 Qxf3+ 53. Ke1 Qg3+ 54. Ke2 Qg2+ 55. Ke1 Qh1+ 56. Kd2 Qh2+` | [ply 99](http://localhost:5173/analysis?game_id=684474&ply=99) | [board](http://localhost:5173/analysis?fen=3r4/PP2k2p/1q2p1p1/3p2P1/2p4P/2P2P2/2K5/R7%20w%20-%20-%201%2051) |
| 884 | missed | FORK | 6 | `50... Qf2+ 51. Kc1 Qe3+ 52. Kc2 Qd3+ 53. Kc1 Qxc3+ 54. Kd1 Qxa1+ 55. Ke2 Qxa7 56. h5` | [ply 99](http://localhost:5173/analysis?game_id=684474&ply=99) | [board](http://localhost:5173/analysis?fen=1r6/PP2k2p/1q2p1p1/3p2P1/2p4P/2P2P2/2K5/R7%20b%20-%20-%200%2050) |
| 885 | allowed | SKEWER | 2 | `12... Bg4 13. Qg3 Bxd1 14. Rxd1 Qe8 15. Nd5 Nxd5 16. Bxa5 Nb6 17. Bc3 f6 18. b3` | [ply 22](http://localhost:5173/analysis?game_id=684479&ply=22) | [board](http://localhost:5173/analysis?fen=r1bq1rk1/pp3ppp/3p1n2/b1p5/4P3/P1NB1Q2/1PPB1PPP/3R1RK1%20b%20-%20-%201%2012) |
| 886 | allowed | SKEWER | 2 | `13... Bg4 14. Qg3 Bxd1 15. Rxd1 Re8 16. Bc4 Nxe4 17. Bxf7+ Kh8 18. Nxe4 Rxe4 19. Be3` | [ply 24](http://localhost:5173/analysis?game_id=684479&ply=24) | [board](http://localhost:5173/analysis?fen=r2q1rk1/pp3ppp/3pbn2/b1p5/4P3/P1NB1Q2/1PPB1PPP/3RR1K1%20b%20-%20-%201%2013) |
| 887 | allowed | SKEWER | 2 | `23... Rd8 24. Qg3 Rxd2 25. Ne3 Bxe3 26. fxe3 Rxc2 27. e4 Kh8 28. Qe3 h5 29. b3` | [ply 44](http://localhost:5173/analysis?game_id=684479&ply=44) | [board](http://localhost:5173/analysis?fen=r3q1k1/p4ppp/1b6/8/8/P2Q3P/1PPB1PP1/3N2K1%20b%20-%20-%200%2023) |
| 888 | allowed | MATE | 8 | `31... Qf4+ 32. g3 Rd2+ 33. Qg2 Rxg2+ 34. Kxg2 Qf2+ 35. Kh1 Qg1#` | [ply 60](http://localhost:5173/analysis?game_id=684479&ply=60) | [board](http://localhost:5173/analysis?fen=3r1k2/pQ2Nppp/1b6/8/8/P6P/1PP2qPK/8%20b%20-%20-%201%2031) |
| 889 | missed | SACRIFICE | 8 | `31. Qe5 f6 32. Qc3 Qf4+ 33. Qg3 Qxg3+ 34. Kxg3 Kxe7 35. a4 Rd2 36. b4 Rxc2` | [ply 60](http://localhost:5173/analysis?game_id=684479&ply=60) | [board](http://localhost:5173/analysis?fen=3r1k2/p1Q1Nppp/1b6/8/8/P6P/1PP2qPK/8%20w%20-%20-%200%2031) |
| 890 | allowed | ATTRACTION | 0 | `19... Bxf2+ 20. Kxf2 Qc5+ 21. Re3 Qxc4 22. Kg1 Qxc2 23. Rf1 Ne5 24. Qg3 Re6 25. Rc3` | [ply 36](http://localhost:5173/analysis?game_id=684488&ply=36) | [board](http://localhost:5173/analysis?fen=r3r2k/1pp4p/p1np1ppB/2b1q3/2B1P1Q1/P6P/1PP2PP1/R3R1K1%20b%20-%20-%201%2019) |
| 891 | missed | PIN | 4 | `36. Be4+ Ng6 37. Rb8 Re7 38. Rxb7 Kg8 39. Rxe7 Nxe7 40. b4 Kf7 41. Bb7 Kf6` | [ply 70](http://localhost:5173/analysis?game_id=684488&ply=70) | [board](http://localhost:5173/analysis?fen=3R4/1p4rk/p6p/3Bn1pp/8/P6P/1PP3PK/8%20w%20-%20-%200%2036) |
| 892 | allowed | CLEARANCE | 2 | `29... Bg7 30. Rd1 Rd8 31. Bd5 b5 32. Bxf7 b4 33. Be6+ Kc7 34. Nd5+ Kb8 35. Nxb4` | [ply 56](http://localhost:5173/analysis?game_id=684506&ply=56) | [board](http://localhost:5173/analysis?fen=2k2br1/pp3p2/b5p1/7p/2pR1P2/2N1PB2/1P3PKP/8%20b%20-%20-%201%2029) |
| 893 | allowed | CLEARANCE | 10 | `32... b4 33. Ne2 Bg7 34. Rf4 Rc5 35. Be4 Bxb2 36. Rxf7 c3 37. Bc2 Bc4 38. Rf4` | [ply 62](http://localhost:5173/analysis?game_id=684506&ply=62) | [board](http://localhost:5173/analysis?fen=2k2b2/p4p2/b1B5/1p4rp/2pR4/2N1P3/1P3P1P/5K2%20b%20-%20-%201%2032) |
| 894 | missed | SACRIFICE | 2 | `33. Rd7 bxc3 34. bxc3 Rg6 35. Rxf7 Rxc6 36. Rxf8+ Kc7 37. f4 Bb7 38. e4 a5` | [ply 64](http://localhost:5173/analysis?game_id=684506&ply=64) | [board](http://localhost:5173/analysis?fen=2k2b2/p4p2/b1B5/6rp/1ppR4/2N1P3/1P3P1P/5K2%20w%20-%20-%200%2033) |
| 895 | allowed | CLEARANCE | 10 | `20. gxh3 Qg5 21. h4 Qg6 22. c3 Bg4 23. f3 Bh5 24. Kf2 a5 25. Rg1 f6` | [ply 37](http://localhost:5173/analysis?game_id=684513&ply=37) | [board](http://localhost:5173/analysis?fen=2r2rk1/4qpp1/p3p2p/1p1pPb2/8/PB4Nn/1PP2PP1/R2QR1K1%20w%20-%20-%200%2020) |
| 896 | allowed | DISCOVERED_ATTACK | 3 | `16. Bxd4 Qd6 17. cxd5 Nxd5 18. Bxa6 bxa6 19. Rc1 Re6 20. Qf3 h6 21. Rc4 Rg6` | [ply 29](http://localhost:5173/analysis?game_id=684525&ply=29) | [board](http://localhost:5173/analysis?fen=r3r1k1/ppq2ppp/n1p2n2/3p4/2Pp4/P1B1P2P/1P2BPP1/R2Q1RK1%20w%20-%20-%200%2016) |
| 897 | allowed | FORK | 0 | `7. Qa4+ Nc6 8. Nd5 Bc5 9. b4 Bb6 10. Nxb6 cxb6 11. Bb2 Qe7` | [ply 11](http://localhost:5173/analysis?game_id=684526&ply=11) | [board](http://localhost:5173/analysis?fen=rnbqk2r/ppp3pp/3p1n2/5pN1/1bP1p3/2N1P3/PP1PBPPP/R1BQK2R%20w%20-%20-%200%207) |
| 898 | allowed | PIN | 4 | `28. Rf1 Rf8 29. Qh7+ Kf7 30. Rxf6+ Kxf6 31. Rf3+ Ke7 32. Qxg7+ Kd6 33. Rxf8 Rxf8` | [ply 53](http://localhost:5173/analysis?game_id=684533&ply=53) | [board](http://localhost:5173/analysis?fen=2r1r1k1/6p1/1q2pbQ1/p2p4/1p1P4/1Pp1B2R/P5PP/R6K%20w%20-%20-%201%2028) |
| 899 | allowed | SACRIFICE | 10 | `31. Qd3 Qh5 32. Rgf3 c2 33. Bc1 Rc3 34. Qa6 Re8 35. Rxf6 gxf6 36. h3 Qg6` | [ply 59](http://localhost:5173/analysis?game_id=684533&ply=59) | [board](http://localhost:5173/analysis?fen=2r2rk1/5qp1/4pbQ1/p2p4/1p1P1B2/1Pp3R1/P5PP/5R1K%20w%20-%20-%201%2031) |
| 900 | allowed | CLEARANCE | 10 | `14... Nd7 15. Rh3 Qe8 16. g4 g6 17. Rg3 fxg4 18. Nxg4 Rf8 19. Kh1 Bh4 20. Rg2` | [ply 26](http://localhost:5173/analysis?game_id=684535&ply=26) | [board](http://localhost:5173/analysis?fen=rnb3k1/pp2b1pp/2p2r2/3pNp1q/3P1P2/2NBPR2/PPQ3PP/R5K1%20b%20-%20-%201%2014) |
| 901 | allowed | PIN | 0 | `20... Rxf4 21. Na4 Rxa4 22. Qc2 Rg4 23. Qxc5 Rxg3 24. hxg3 Qxe5 25. Rf1 Bd7 26. e4` | [ply 38](http://localhost:5173/analysis?game_id=684535&ply=38) | [board](http://localhost:5173/analysis?fen=r1b1qrk1/pp5p/2p3p1/2bpP3/5P2/2NBP1R1/PP2Q1PP/R5K1%20b%20-%20-%201%2020) |
| 902 | allowed | FORK | 2 | `19... Qxe3+ 20. Kh1 Nd2 21. Qc2 Nxd4 22. Qc5+ Kg8 23. fxg4 Qxd3 24. Rad1 Rad8 25. Qxc7` | [ply 36](http://localhost:5173/analysis?game_id=684537&ply=36) | [board](http://localhost:5173/analysis?fen=r3rk2/ppp2pp1/2n4p/6q1/3Pn1bN/PQ1BPPB1/6PP/R4RK1%20b%20-%20-%200%2019) |
| 903 | allowed | CLEARANCE | 10 | `22... Nxd4 23. Qb1 Rad8 24. f4 Bd5 25. Bb5 Nxb5 26. Qh7 Be4 27. f5 Rd3 28. Rf3` | [ply 42](http://localhost:5173/analysis?game_id=684537&ply=42) | [board](http://localhost:5173/analysis?fen=r3rk2/ppp2pp1/2n1b2p/8/3P3N/P2BqPP1/2Q3PK/R4R2%20b%20-%20-%201%2022) |
| 904 | missed | CLEARANCE | 6 | `24. Qc3 Qe5 25. Rac1 c5 26. Bb1 b6 27. Qd3 g6 28. f4 Qh5 29. Qa6 Rad8` | [ply 46](http://localhost:5173/analysis?game_id=684537&ply=46) | [board](http://localhost:5173/analysis?fen=r3r1k1/ppp2pp1/4b2p/2Q5/3n3N/P2BqPP1/6PK/R4R2%20w%20-%20-%200%2024) |
| 905 | allowed | HANGING_PIECE | 0 | `17... Nxd3 18. Qe3 Bxd4 19. Qxd4 Nf4 20. Qe3 Qg5 21. Qf3 a4 22. Rae1 axb3 23. axb3` | [ply 32](http://localhost:5173/analysis?game_id=684538&ply=32) | [board](http://localhost:5173/analysis?fen=r2q1rk1/1pp2pb1/3p2p1/p2Pn3/2PNPQ1p/1P1B3P/P4PP1/R4RK1%20b%20-%20-%201%2017) |
| 906 | missed | DISCOVERED_ATTACK | 5 | `16. dxe5` | [ply 30](http://localhost:5173/analysis?game_id=684560&ply=30) | [board](http://localhost:5173/analysis?fen=r1n1k2r/pp1bq1pp/5pn1/P2pp3/3P4/2PBPNB1/5PPP/R2Q1RK1%20w%20-%20-%200%2016) |
| 907 | allowed | EN_PASSANT | 2 | `21... Qxh4 22. f4 exf3 23. Rxf3` | [ply 40](http://localhost:5173/analysis?game_id=684560&ply=40) | [board](http://localhost:5173/analysis?fen=r3k2r/1p1bq1pp/p2n4/P2P1p2/3Pp2B/4P2P/2B2PP1/R2Q1RK1%20b%20-%20-%200%2021) |
| 908 | missed | CLEARANCE | 2 | `21. Qh5+ Ng6 22. Rfb1` | [ply 40](http://localhost:5173/analysis?game_id=684560&ply=40) | [board](http://localhost:5173/analysis?fen=r3k2r/1p1bq1pp/p2n4/P2P1p2/3Pp2n/4P1BP/2B2PP1/R2Q1RK1%20w%20-%20-%200%2021) |
| 909 | allowed | CAPTURING_DEFENDER | 8 | `22... Qf6 23. Nce2 Kh8 24. Ra1 Rxa1 25. Rxa1 Nxc4 26. Ra7 Bxd5 27. Rxc7 Nd3 28. Bxd3` | [ply 42](http://localhost:5173/analysis?game_id=684562&ply=42) | [board](http://localhost:5173/analysis?fen=r2q1r2/1bp3kp/1p1p4/1PnPnp2/2PNpQ2/2N4P/2B2PP1/4RRK1%20b%20-%20-%201%2022) |
| 910 | allowed | DISCOVERED_ATTACK | 7 | `26... Bxc6 27. dxc6 f4 28. Qh2 Qf6 29. Rc1 Nf3+ 30. gxf3 Qxc3 31. Qh1 Nd3 32. Kh2` | [ply 50](http://localhost:5173/analysis?game_id=684562&ply=50) | [board](http://localhost:5173/analysis?fen=3q1r1k/2pb3p/1pNp4/1PnPnp2/2P1p3/2N3QP/2B2PP1/R5K1%20b%20-%20-%201%2026) |
| 911 | missed | SACRIFICE | 6 | `29. Ra7 f4 30. Qg4 e3 31. f3 Qxc3 32. Rxc7 Qe1+ 33. Kh2 Qg3+ 34. Qxg3 fxg3+` | [ply 56](http://localhost:5173/analysis?game_id=684562&ply=56) | [board](http://localhost:5173/analysis?fen=5r1k/2p4p/1pPp1q2/2nP1p2/2n1p3/2N3QP/5PP1/R2B2K1%20w%20-%20-%200%2029) |
| 912 | allowed | CLEARANCE | 6 | `13... Qc7 14. Nxd7 Nxd7 15. Qb1 a6 16. Bg3 Qa7 17. Qa2 Bb7 18. f3 e5 19. e4` | [ply 24](http://localhost:5173/analysis?game_id=684581&ply=24) | [board](http://localhost:5173/analysis?fen=r1bq1rk1/p2n1pp1/4pn1p/1p2N3/2pP3B/2P1P3/4BPPP/R2Q1RK1%20b%20-%20-%201%2013) |
| 913 | allowed | SKEWER | 2 | `10. c4 Nb6 11. Bxb7 Qxd4+ 12. Kh1 Qxd1 13. Rxd1 a6 14. Bxa8 Nxa8 15. b3 Nc6` | [ply 17](http://localhost:5173/analysis?game_id=684584&ply=17) | [board](http://localhost:5173/analysis?fen=rn1qkb1r/pp3ppp/4p3/2pnP3/3P4/5B2/PPP3PP/RNBQ1RK1%20w%20-%20-%200%2010) |
| 914 | allowed | PIN | 6 | `12. Qh5 g6 13. Qf3 Qe7 14. Bxa8 cxd4 15. Bc6 Bg7 16. Bxd7+ Qxd7 17. Bf4` | [ply 21](http://localhost:5173/analysis?game_id=684584&ply=21) | [board](http://localhost:5173/analysis?fen=r2qkb1r/pB1n1ppp/1n2p3/2p1P3/2PP4/8/PP4PP/RNBQ1RK1%20w%20-%20-%201%2012) |
| 915 | missed | CAPTURING_DEFENDER | 4 | `21... Qf6 22. Qxf6 gxf6 23. Re4 Nxf3+ 24. Kg2 f5 25. Rb4 Ne5 26. Rdxb7 Rec8 27. Rd4` | [ply 41](http://localhost:5173/analysis?game_id=684589&ply=41) | [board](http://localhost:5173/analysis?fen=r3r1k1/1p1R1ppp/p3p3/8/5Q1n/N4P2/1q3P1P/4R1K1%20b%20-%20-%200%2021) |
| 916 | missed | SKEWER | 2 | `23... Rf8 24. Qxe6 Rxf3 25. Re2 Qc1+ 26. Re1 Qg5+ 27. Kh1 Rxf2 28. Qh3 Qc5 29. Red1` | [ply 45](http://localhost:5173/analysis?game_id=684589&ply=45) | [board](http://localhost:5173/analysis?fen=r3r2k/1p1R1Qpp/p3p1n1/8/4R3/N4P2/1q3P1P/6K1%20b%20-%20-%200%2023) |
| 917 | allowed | PIN | 6 | `16... Qxg2 17. Rf1 Rxb2` | [ply 30](http://localhost:5173/analysis?game_id=684592&ply=30) | [board](http://localhost:5173/analysis?fen=1r3rk1/p1Q2pp1/4b1p1/4P1q1/8/P1N1P3/1P3PPP/R3K2R%20b%20-%20-%200%2016) |
| 918 | missed | SACRIFICE | 6 | `e1g1 f8c8 c3e4 g5g4 c7a7 g4e4 a7d4 e4d4 e3d4 c8d8 f1d1 e6b3` | [ply 32](http://localhost:5173/analysis?game_id=684592&ply=32) | [board](http://localhost:5173/analysis?fen=5rk1/p1Q2pp1/4b1p1/4P1q1/8/P1N1P3/1r3PPP/R3K2R%20w%20-%20-%200%2017) |
| 919 | allowed | DISCOVERED_ATTACK | 7 | `8. dxe5 Nxe5 9. Bxd5 Qd7` | [ply 13](http://localhost:5173/analysis?game_id=684607&ply=13) | [board](http://localhost:5173/analysis?fen=r2qkbnr/pp3ppp/2n5/3pp3/3P4/2P2B2/PP3PPP/RNBQK2R%20w%20-%20-%200%208) |
| 920 | allowed | CLEARANCE | 8 | `19. Bxe7 Qxe7 20. Qxh5 Rfd8 21. Nxd5 Qd6 22. Ne3 g6 23. Qc5 Qxc5 24. dxc5 f5` | [ply 35](http://localhost:5173/analysis?game_id=684607&ply=35) | [board](http://localhost:5173/analysis?fen=r2q1rk1/4bppp/8/n2p2Bn/3Pp3/2P1N2B/5PPP/R2QR1K1%20w%20-%20-%201%2019) |
| 921 | missed | PIN | 8 | `24... Kg7 25. Qxh7+ Kxf6 26. Bxg6 Qg5 27. Rxe4 Nd2 28. h4 Nf3+ 29. Kh1 Qxg6 30. Rf4+` | [ply 47](http://localhost:5173/analysis?game_id=684607&ply=47) | [board](http://localhost:5173/analysis?fen=r4rk1/5p1p/5Np1/q4B1Q/3Pp3/1nP5/5PPP/3RR1K1%20b%20-%20-%200%2024) |
| 922 | allowed | CLEARANCE | 10 | `23. Nxa6+ Qxa6 24. Rxc8+ Rxc8 25. Bxa6 bxa6 26. Bc3 Nc2+ 27. Kd2 Nce3 28. Rc1 Rh8` | [ply 43](http://localhost:5173/analysis?game_id=684620&ply=43) | [board](http://localhost:5173/analysis?fen=1kr4r/1p1b1p1N/p3p1p1/q3Pn2/1N1n1P2/3B3Q/P2B3P/2R1K1R1%20w%20-%20-%201%2023) |
| 923 | missed | INTERFERENCE | 4 | `22... Rxh7 23. Qg2 Qa3 24. Rc3 Qxb4 25. Rc8+ Rxc8 26. Bxb4 Bc6 27. Qf2 Nf3+ 28. Ke2` | [ply 43](http://localhost:5173/analysis?game_id=684620&ply=43) | [board](http://localhost:5173/analysis?fen=1k1r3r/1p1b1p1N/p3p1p1/q3Pn2/1N1n1P2/3B3Q/P2B3P/2R1K1R1%20b%20-%20-%200%2022) |
| 924 | allowed | CLEARANCE | 4 | `26. Rxc1 Rxc1 27. Bxf5 Nxf5 28. Qd3 b6 29. Bd2 Rc7 30. Qxa6 Bc8 31. Qxb6+ Rb7` | [ply 49](http://localhost:5173/analysis?game_id=684620&ply=49) | [board](http://localhost:5173/analysis?fen=1kr5/1p1b1p1N/p3p1p1/B3Pn2/3n1P2/3B3Q/P4K1P/2r3R1%20w%20-%20-%201%2026) |
| 925 | missed | SACRIFICE | 6 | `32... Rb2 33. Kg5 Ng1 34. Qd4+ b6 35. Qxb2 Nf3+ 36. Kh6 bxa5 37. Nd7 Bxd7 38. Qf2+` | [ply 63](http://localhost:5173/analysis?game_id=684620&ply=63) | [board](http://localhost:5173/analysis?fen=3Q4/kp3p2/p1b1pN2/B3Pp2/5P1K/8/P1r1n2P/8%20b%20-%20-%200%2032) |
| 926 | missed | HANGING_PIECE | 0 | `34... Bxd7 35. Qd6+ Ka8 36. Qxd7 Nd5 37. h3 Ka7 38. Qxf7 Rxa2 39. Bd8 Ra3 40. Qd7` | [ply 67](http://localhost:5173/analysis?game_id=684620&ply=67) | [board](http://localhost:5173/analysis?fen=1k6/1p1N1p2/pQb1p3/B3Pp2/5n1K/8/P1r4P/8%20b%20-%20-%200%2034) |
| 927 | allowed | TRAPPED_PIECE | 8 | `19. Bxh5 Rd8 20. Bg4 f5 21. h4 Qf6 22. f3 fxg4 23. fxe4 Qxd4 24. Nxg4 Qxe4` | [ply 35](http://localhost:5173/analysis?game_id=684625&ply=35) | [board](http://localhost:5173/analysis?fen=r5k1/1pp2pp1/p1n1r3/2Pp2qp/3Pb3/P3N1PP/1P2BP1K/R2Q1R2%20w%20-%20-%200%2019) |
| 928 | missed | SACRIFICE | 4 | `18... Qf6 19. f3 Bd3 20. Qxd3 Rae8 21. Nc2 Rxe2+ 22. Kg1 h5 23. Rf2 Rxf2 24. Kxf2` | [ply 35](http://localhost:5173/analysis?game_id=684625&ply=35) | [board](http://localhost:5173/analysis?fen=r5k1/1pp2pp1/p1n1r2p/2Pp2q1/3Pb3/P3N1PP/1P2BP1K/R2Q1R2%20b%20-%20-%200%2018) |
| 929 | missed | DISCOVERED_ATTACK | 3 | `21... g6 22. Bg4 Bf3 23. Bxf3 Rxe3 24. Bg4 Rae8 25. Rc1 c6 26. Rc3 Nf5 27. Bxf5` | [ply 41](http://localhost:5173/analysis?game_id=684625&ply=41) | [board](http://localhost:5173/analysis?fen=r5k1/1pp2pp1/p3rq2/2Pp3B/3nbP1P/P3N1P1/1P5K/R2Q1R2%20b%20-%20-%200%2021) |
| 930 | allowed | HANGING_PIECE | 0 | `23. Qxf3 Qd8 24. Rad1 Be4 25. Qb3 Bxd5 26. Qxd5 Qf6 27. Kh3 Rae8 28. Bf3 c6` | [ply 43](http://localhost:5173/analysis?game_id=684625&ply=43) | [board](http://localhost:5173/analysis?fen=r5k1/1pp2pp1/p3rq2/2PN1b1B/5P1P/P4nP1/1P5K/R2Q1R2%20w%20-%20-%201%2023) |
| 931 | missed | SACRIFICE | 2 | `22... Qd8 23. Qxd4 c6 24. Rae1 cxd5 25. Rxe6 fxe6 26. Bf3 Rc8 27. b4 b6 28. Rc1` | [ply 43](http://localhost:5173/analysis?game_id=684625&ply=43) | [board](http://localhost:5173/analysis?fen=r5k1/1pp2pp1/p3rq2/2PN1b1B/3n1P1P/P5P1/1P5K/R2Q1R2%20b%20-%20-%200%2022) |
| 932 | allowed | CLEARANCE | 2 | `26. Qxe2 Qxe2 27. Rae1 Qc2 28. Rxe4 Rd8 29. c6 bxc6 30. Ne3 Qc3 31. Rb1 Qxa3` | [ply 49](http://localhost:5173/analysis?game_id=684625&ply=49) | [board](http://localhost:5173/analysis?fen=r5k1/1pp2pp1/p7/2PN4/4bP1P/P5P1/1q2r1BK/R2Q2R1%20w%20-%20-%201%2026) |
| 933 | missed | PIN | 2 | `25... Rae8 26. Nb4 Bg4 27. Rb1 Qf6 28. Qd5 Bf5 29. c6 b6 30. Nxa6 Be4 31. Qd7` | [ply 49](http://localhost:5173/analysis?game_id=684625&ply=49) | [board](http://localhost:5173/analysis?fen=r5k1/1pp2pp1/p7/2PN1b2/5P1P/P5P1/1q2r1BK/R2Q2R1%20b%20-%20-%200%2025) |
| 934 | missed | FORK | 2 | `31... Qf1 32. Nd4 Qf2+ 33. Kh3 Qxd4 34. Qxc7 Qd5 35. Qb6 Qh1+ 36. Kg4 Qd1+ 37. Kh3` | [ply 61](http://localhost:5173/analysis?game_id=684625&ply=61) | [board](http://localhost:5173/analysis?fen=4rk2/1Qp2pp1/p7/2P2N2/5P1P/P5P1/7K/q7%20b%20-%20-%200%2031) |
| 935 | missed | PIN | 2 | `32... Qa2+ 33. Kh3 Qe6 34. g4 Qb3+ 35. Ng3 Kg8 36. h5 Qb8 37. Qd7 Re3 38. Qf5` | [ply 63](http://localhost:5173/analysis?game_id=684625&ply=63) | [board](http://localhost:5173/analysis?fen=4rk2/2Q2pp1/p7/2P2N2/5P1P/q5P1/7K/8%20b%20-%20-%200%2032) |
| 936 | allowed | FORK | 0 | `20... Bd5 21. Qa3 Nxd1 22. Nf4 Kh8 23. Bxd1 Bxe6 24. Nxe6 Qe8 25. Bb3 Rf7 26. d5` | [ply 38](http://localhost:5173/analysis?game_id=684645&ply=38) | [board](http://localhost:5173/analysis?fen=r2q1r2/p5kp/4Rpp1/1p6/3Pb3/1Q1Nn2P/PP2BPP1/3R2K1%20b%20-%20-%200%2020) |
| 937 | missed | SACRIFICE | 4 | `20. Nc5 Kh8 21. Rd6 Qxd6 22. Nxe4 Qd5 23. Qxe3 Qxa2 24. b3 a5 25. Bxb5 Rac8` | [ply 38](http://localhost:5173/analysis?game_id=684645&ply=38) | [board](http://localhost:5173/analysis?fen=r2q1r2/p5kp/2R1ppp1/1p6/3Pb3/1Q1Nn2P/PP2BPP1/3R2K1%20w%20-%20-%200%2020) |
| 938 | allowed | CLEARANCE | 4 | `21... Nxd1 22. Qxd1 Qd7 23. Re3 Rae8 24. Rd3 Qd5 25. a3 Rc8 26. g3 Rfd8 27. Qd2` | [ply 40](http://localhost:5173/analysis?game_id=684645&ply=40) | [board](http://localhost:5173/analysis?fen=r2q1r2/p5kp/4Rpp1/1p6/3P4/3Qn2P/PP2BPP1/3R2K1%20b%20-%20-%200%2021) |
| 939 | missed | HANGING_PIECE | 0 | `21. Rxe3 Bxe2 22. Rxe2 a6 23. Re6 Re8 24. d5 Ra7 25. Rc6 Rd7 26. Rxa6 Re5` | [ply 40](http://localhost:5173/analysis?game_id=684645&ply=40) | [board](http://localhost:5173/analysis?fen=r2q1r2/p5kp/4Rpp1/1p6/3P4/1Q1bn2P/PP2BPP1/3R2K1%20w%20-%20-%200%2021) |
| 940 | missed | CLEARANCE | 6 | `12... Bxe2 13. Qxe2 Qd7 14. f3` | [ply 23](http://localhost:5173/analysis?game_id=684647&ply=23) | [board](http://localhost:5173/analysis?fen=r2qk2r/pp3ppp/5n2/3p4/3Pp1b1/4P1P1/PP1NBPP1/R2QK2R%20b%20-%20-%200%2012) |
| 941 | allowed | PROMOTION | 6 | `38. b5 Kf6 39. b6 Ke6 40. b7 Kd7 41. b8=Q Kxc6 42. a4 Kd7 43. a5 Ke7` | [ply 73](http://localhost:5173/analysis?game_id=684647&ply=73) | [board](http://localhost:5173/analysis?fen=8/5p2/2N5/3p2k1/1P1P3p/P3PP2/6K1/8%20w%20-%20-%201%2038) |
| 942 | missed | SACRIFICE | 6 | `37... h3+ 38. Kxh3 Kg5 39. Ne7 f5 40. Nxd5 f4 41. e4 Kg6 42. b5 Kh6 43. b6` | [ply 73](http://localhost:5173/analysis?game_id=684647&ply=73) | [board](http://localhost:5173/analysis?fen=8/5p2/2N5/3p1k2/1P1P3p/P3PP2/6K1/8%20b%20-%20-%200%2037) |
| 943 | missed | FORK | 6 | `30... Nf5 31. Rd3 Bxc5 32. g3 h6 33. h4 Bxd4+ 34. Nxd4 Nxd4 35. Kg2 c5 36. Be3` | [ply 59](http://localhost:5173/analysis?game_id=684652&ply=59) | [board](http://localhost:5173/analysis?fen=4r2k/1p1r2pp/2p5/p1P5/Pb1P1B1n/1P5R/1R2N1PP/6K1%20b%20-%20-%200%2030) |
| 944 | allowed | DISCOVERED_ATTACK | 7 | `13... Qe7 14. Qe3 Re8 15. Be2 Bf5` | [ply 24](http://localhost:5173/analysis?game_id=684657&ply=24) | [board](http://localhost:5173/analysis?fen=r1bq1rk1/1pp2p1p/6p1/p1NPb3/2P5/7P/PP1Q1PP1/R3KB1R%20b%20-%20-%200%2013) |
| 945 | missed | CLEARANCE | 6 | `13. Bd3 a4 14. Rd1 b6` | [ply 24](http://localhost:5173/analysis?game_id=684657&ply=24) | [board](http://localhost:5173/analysis?fen=r1bq1rk1/1pp2p1p/6p1/p1pPb3/2P1N3/7P/PP1Q1PP1/R3KB1R%20w%20-%20-%200%2013) |
| 946 | missed | DISCOVERED_ATTACK | 1 | `18. Bg4 Ba4 19. Rxe8+ Bxe8 20. Kb1 b5 21. Qf4 Qb6 22. Ne5 bxc4 23. Nxc4 Qb4` | [ply 34](http://localhost:5173/analysis?game_id=684657&ply=34) | [board](http://localhost:5173/analysis?fen=r3r1k1/1p1b1p1p/5qp1/p1pP4/2Pb4/3N3P/PP1QBPP1/2KRR3%20w%20-%20-%200%2018) |
| 947 | allowed | PIN | 6 | `22... Rxe2 23. Rxe2 axb3 24. Kb1 g5 25. Qg3 Qg6 26. Bg4 f5 27. axb3 fxg4 28. Ra2` | [ply 42](http://localhost:5173/analysis?game_id=684657&ply=42) | [board](http://localhost:5173/analysis?fen=r3r1k1/1p1b1pqp/6p1/2pP4/p1Pb1Q2/1P1N1B1P/P3RPP1/2K1R3%20b%20-%20-%201%2022) |
| 948 | missed | CLEARANCE | 4 | `19... Bh6 20. Kf2 Kh8 21. Rg1 Rg8 22. g3 f5 23. Ne5 Bd5 24. Qd3 f6 25. Nf3` | [ply 37](http://localhost:5173/analysis?game_id=684663&ply=37) | [board](http://localhost:5173/analysis?fen=r4rk1/ppq2pbp/2p1pp2/8/2QPb3/P1P1PN1P/1P2B1P1/3R1RK1%20b%20-%20-%200%2019) |
| 949 | allowed | CLEARANCE | 10 | `24... Bxh3 25. Qxh3 Rh8 26. Qf3+ Kg8` | [ply 46](http://localhost:5173/analysis?game_id=684666&ply=46) | [board](http://localhost:5173/analysis?fen=r1bq1r2/pp3knQ/3p2p1/1N1Pp3/4P3/7R/PP3PP1/R3K3%20b%20-%20-%201%2024) |
| 950 | missed | DEFLECTION | 2 | `26. Nxd6+ Ke7 27. Qxg7+ Kxd6 28. Qxg6+ Kc5 29. Qg3 Qb5+ 30. Kg1 Qxb2 31. Qe3+ Kb5` | [ply 50](http://localhost:5173/analysis?game_id=684666&ply=50) | [board](http://localhost:5173/analysis?fen=r4r2/pp3knQ/3p2p1/qN1Pp3/4P3/7b/PP3PP1/R4K2%20w%20-%20-%200%2026) |
| 951 | missed | DEFLECTION | 8 | `32. g4 Qd8 33. Rc3 Rhh8 34. g5 Rf8 35. Qxg7+ Rf7 36. Qxh8 Qxh8 37. Rc7+ Kd8` | [ply 62](http://localhost:5173/analysis?game_id=684666&ply=62) | [board](http://localhost:5173/analysis?fen=6r1/pp2k1n1/1q1p2Q1/3Pp2r/4P3/8/PP3PP1/2R3K1%20w%20-%20-%200%2032) |
| 952 | missed | CLEARANCE | 10 | `11. e5 Nd5 12. Ng5 f5 13. exf6 Nxf6 14. Bxe6+ Kh8 15. Bf4 Qe8 16. Rae1 h6` | [ply 20](http://localhost:5173/analysis?game_id=684671&ply=20) | [board](http://localhost:5173/analysis?fen=r1bq1rk1/1pp2ppp/p1n1pn2/8/2BPP3/P1PQ1N2/5PPP/R1B2RK1%20w%20-%20-%200%2011) |
| 953 | allowed | CLEARANCE | 6 | `17... Nxe5 18. Qh3 Nc4 19. Qh4 f6 20. Bh6 Qd7 21. Bxf8 Rxf8 22. a4 Bd5 23. Qg3` | [ply 32](http://localhost:5173/analysis?game_id=684671&ply=32) | [board](http://localhost:5173/analysis?fen=3r1rk1/1bp2pqp/p1n1p1p1/1p2N1B1/3P4/P1PQ4/2B2PPP/R3R1K1%20b%20-%20-%201%2017) |
| 954 | allowed | HANGING_PIECE | 0 | `20... Rxf6 21. Qg3 Qh6 22. h4 Qf4 23. Qxf4 Rxf4 24. Rxe6 Rd6 25. Rxd6 cxd6 26. a4` | [ply 38](http://localhost:5173/analysis?game_id=684671&ply=38) | [board](http://localhost:5173/analysis?fen=3r1rk1/1bp3q1/p3pBp1/1p2R2p/3P4/P1P4Q/2B2PPP/R5K1%20b%20-%20-%200%2020) |
| 955 | allowed | PROMOTION | 2 | `56... g2 57. Kc3 g1=Q 58. Kd4 Qg5 59. Ke4 Ke2 60. Kd4 Kf3 61. Kc3 Qc5+ 62. Kb3` | [ply 110](http://localhost:5173/analysis?game_id=684671&ply=110) | [board](http://localhost:5173/analysis?fen=8/8/8/8/8/6p1/3K1k2/8%20b%20-%20-%201%2056) |
| 956 | missed | CLEARANCE | 8 | `e8g8 f1e1 b8d7 c1d2 d7b6 c4b3 f8e8 a1d1 e7f8 e1e8 d8e8 a2a4` | [ply 19](http://localhost:5173/analysis?game_id=684672&ply=19) | [board](http://localhost:5173/analysis?fen=rn1qk2r/pp2bppp/2p2p2/8/2BP4/5Q1P/PPP2PP1/R1B2RK1%20b%20-%20-%200%2010) |
| 957 | missed | FORK | 0 | `23... Qd3 24. Bd2 Ne4 25. Qa6 Nxd2 26. Rbd1 Qe4 27. a4 Nxb3 28. Rxd7 Nc5 29. axb5` | [ply 45](http://localhost:5173/analysis?game_id=684672&ply=45) | [board](http://localhost:5173/analysis?fen=4r1k1/3r1p1p/2pq1bp1/1pn2p2/5P2/QBP4P/PP4P1/1RB2R1K%20b%20-%20-%200%2023) |
| 958 | allowed | SACRIFICE | 4 | `15. Bxf7+ Kd8 16. Bxe6 Qxa1 17. Bxd5 Kc7 18. Rf7+ Kb6 19. Qd3 a6 20. Bxc6 bxc6` | [ply 27](http://localhost:5173/analysis?game_id=684673&ply=27) | [board](http://localhost:5173/analysis?fen=r3kb1r/pp3ppp/2n1p3/3pP2B/3q4/1P6/P5PP/RN1Q1R1K%20w%20-%20-%200%2015) |
| 959 | missed | INTERFERENCE | 2 | `14... g6 15. Nd2 Nxd4 16. Re1 Qd3 17. Be2 Nxe2 18. Rxe2 Bg7 19. Qf1 Rc8 20. Nf3` | [ply 27](http://localhost:5173/analysis?game_id=684673&ply=27) | [board](http://localhost:5173/analysis?fen=r3kb1r/pp3ppp/2n1p3/3pP2B/3P4/1P2q3/P5PP/RN1Q1R1K%20b%20-%20-%200%2014) |
| 960 | allowed | TRAPPED_PIECE | 2 | `36. Kf3 Kf5 37. Kxg2 Ke4 38. Nf4 Kxe5 39. Kf3 Kd4 40. Nxe6+ Kc3 41. Nc7 b4` | [ply 69](http://localhost:5173/analysis?game_id=684673&ply=69) | [board](http://localhost:5173/analysis?fen=8/7p/4p1k1/pp1pP2p/5K2/1P1N2PP/P5n1/8%20w%20-%20-%201%2036) |
| 961 | allowed | TRAPPED_PIECE | 2 | `37. g4 Kf7 38. Kxg2 Ke7 39. Kf3 Kd7 40. Nc5+ Ke7 41. Ke3 Kf7 42. Kf4 b4` | [ply 71](http://localhost:5173/analysis?game_id=684673&ply=71) | [board](http://localhost:5173/analysis?fen=8/7p/4p1k1/pp1pP3/7p/1P1N1KPP/P5n1/8%20w%20-%20-%200%2037) |
| 962 | missed | SACRIFICE | 2 | `36... Kf5 37. Kxg2 Ke4 38. Nf4 Kxe5 39. Kf3 Kd4 40. Nxe6+ Kc3 41. Nc7 b4 42. Ne6` | [ply 71](http://localhost:5173/analysis?game_id=684673&ply=71) | [board](http://localhost:5173/analysis?fen=8/7p/4p1k1/pp1pP2p/8/1P1N1KPP/P5n1/8%20b%20-%20-%200%2036) |
| 963 | allowed | MATE | 10 | `42. a7 Rd3+ 43. Nxd3 Kb7 44. Rh8 Kc7 45. Rh7+ Kb6 46. a8=Q Kb5 47. Rb7#` | [ply 81](http://localhost:5173/analysis?game_id=684675&ply=81) | [board](http://localhost:5173/analysis?fen=8/2k5/P6R/2NK4/1P5P/2P3r1/8/8%20w%20-%20-%201%2042) |
| 964 | missed | CLEARANCE | 4 | `41... Kd8 42. b5 Ke7 43. b6 Rd8+ 44. Kc4 Kf7 45. b7 Kg7 46. Rc6 Rh8 47. Kb5` | [ply 81](http://localhost:5173/analysis?game_id=684675&ply=81) | [board](http://localhost:5173/analysis?fen=6r1/2k5/P6R/2NK4/1P5P/2P5/8/8%20b%20-%20-%200%2041) |
| 965 | allowed | PIN | 4 | `13... Nf4 14. f3 Qg5 15. g3 d6 16. Nd3 Nxd3 17. Bxd3 Qe3+ 18. Kg2 Qxd4 19. Nb5` | [ply 24](http://localhost:5173/analysis?game_id=684681&ply=24) | [board](http://localhost:5173/analysis?fen=rn1q1r2/pbpp2kp/1p2p1p1/4N2n/2BP4/2N5/PPP2PPP/R2Q1RK1%20b%20-%20-%201%2013) |
| 966 | missed | CLEARANCE | 10 | `6... e6 7. Nc3 exd5 8. exd5 a6 9. Qe2+ Be7 10. Bg5` | [ply 11](http://localhost:5173/analysis?game_id=684695&ply=11) | [board](http://localhost:5173/analysis?fen=rnbqkb1r/pp2pppp/5n2/2pP4/4P3/5N2/PP3PPP/RNBQKB1R%20b%20-%20-%200%206) |
| 967 | missed | HANGING_PIECE | 0 | `16... Bxa1 17. Nc3 Bb2 18. Bxf8 Qxf8 19. Bb3 Rb4 20. Re1 c4 21. Bxc4 Qc5 22. Nd1` | [ply 31](http://localhost:5173/analysis?game_id=684695&ply=31) | [board](http://localhost:5173/analysis?fen=1r1q1rk1/p2n1p1p/2bB2p1/2p5/2B5/3Q1N2/Pb3PPP/RN3RK1%20b%20-%20-%200%2016) |
| 968 | missed | CLEARANCE | 2 | `22... Rc2 23. Rf2 Rac8 24. Rdd2 Rxd2 25. Rxd2 Rc6 26. Nd4 Rc1+ 27. Kf2 Kf7 28. Ne2` | [ply 43](http://localhost:5173/analysis?game_id=684699&ply=43) | [board](http://localhost:5173/analysis?fen=r1r3k1/p5pp/4N1n1/3p4/8/7P/PP4P1/3R1RK1%20b%20-%20-%200%2022) |
| 969 | missed | FORK | 8 | `12. Ng5 Qf6 13. f4 Qxd4 14. Qxd4 Nxd4 15. Bxd7 Rd8 16. Ndxf7 Rxd7 17. Nxh8 Nc2+` | [ply 22](http://localhost:5173/analysis?game_id=684716&ply=22) | [board](http://localhost:5173/analysis?fen=r2q1knr/p2b1ppp/1pnNp3/1B6/3P4/5N2/PP1Q1PPP/R3K2R%20w%20-%20-%200%2012) |
| 970 | missed | CLEARANCE | 8 | `15. Ne5 Be8 16. Qa3 Kg8 17. Rfc1 Nd5 18. Rc2 h6 19. Rac1 Qe7 20. Rc8 Rxc8` | [ply 28](http://localhost:5173/analysis?game_id=684716&ply=28) | [board](http://localhost:5173/analysis?fen=r2q1k1r/4nppp/ppbNp3/8/1Q1P4/5N2/PP3PPP/R4RK1%20w%20-%20-%200%2015) |
| 971 | missed | FORK | 0 | `28. Rxf7+ Qxf7 29. Qxf7+ Kxf7 30. Rg3 Rc2 31. Kg2 Rxb2 32. Rd3 Rf8 33. Kg3 Kg8` | [ply 54](http://localhost:5173/analysis?game_id=684716&ply=54) | [board](http://localhost:5173/analysis?fen=r1r5/2QR1pkp/p3p1p1/1p2P3/8/5q2/PP3PRP/7K%20w%20-%20-%200%2028) |
| 972 | allowed | PROMOTION | 0 | `45... c1=Q+ 46. Ke2 Rc7 47. Rd2 Kf4 48. e5 Kxf5 49. exf6 Qc4+ 50. Ke1 Qe4+ 51. Kf2` | [ply 88](http://localhost:5173/analysis?game_id=684719&ply=88) | [board](http://localhost:5173/analysis?fen=8/5r2/5p2/pp2kB2/4P3/P2R4/2p5/5K2%20b%20-%20-%200%2045) |
| 973 | allowed | SKEWER | 8 | `20. Nb5 Raf8 21. Ree1 Qxe5 22. Qxe5 Nxe5 23. Kg1 Nxd3 24. Rxe6 Rf2 25. Nc3 Rxb2` | [ply 37](http://localhost:5173/analysis?game_id=684729&ply=37) | [board](http://localhost:5173/analysis?fen=r5k1/ppq3pp/2n1p3/3pPr2/8/2NPR1Q1/PP4PP/R6K%20w%20-%20-%201%2020) |
| 974 | missed | FORK | 0 | `19... d4 20. Nd5 Qd7 21. Nf6+ Rxf6 22. exf6 dxe3 23. Qxe3 gxf6 24. Rf1 Qe7 25. d4` | [ply 37](http://localhost:5173/analysis?game_id=684729&ply=37) | [board](http://localhost:5173/analysis?fen=r4rk1/ppq3pp/2n1p3/3pP3/8/2NPR1Q1/PP4PP/R6K%20b%20-%20-%200%2019) |
| 975 | allowed | ATTRACTION | 8 | `18. g4 Ne7 19. Rfc1 Qb4 20. a3 Qxa3 21. R1c5 Qb4 22. Rxe7+ Kxe7 23. Rc7+ Kd8` | [ply 33](http://localhost:5173/analysis?game_id=684731&ply=33) | [board](http://localhost:5173/analysis?fen=r3k2r/ppR2ppp/4p3/1q1pPn2/N7/1P3Q2/P4PPP/5RK1%20w%20-%20-%201%2018) |
| 976 | allowed | DISCOVERED_CHECK | 0 | `12... c4+ 13. Qf2 Qxf2+ 14. Rxf2 Be7 15. d4 cxd3 16. cxd3 Rhc8 17. h3 a6 18. Nd4` | [ply 22](http://localhost:5173/analysis?game_id=684745&ply=22) | [board](http://localhost:5173/analysis?fen=r4b1r/pp3k1p/1q1p1np1/1Np5/4P3/8/PPPPQ1PP/R1B2RK1%20b%20-%20-%201%2012) |
| 977 | allowed | CLEARANCE | 4 | `12. Bxe7 Nxe7 13. Ne5 Bf5 14. Qg3 Ng6 15. Qe3 Rc8 16. Nc3 c5 17. Na4 Qd6` | [ply 21](http://localhost:5173/analysis?game_id=684746&ply=21) | [board](http://localhost:5173/analysis?fen=r3k1nr/4bppp/pqp1p3/3p2B1/3P2b1/1P1Q1N2/P1P2PPP/RN3RK1%20w%20-%20-%201%2012) |
| 978 | missed | CLEARANCE | 6 | `19... Qxg3+ 20. hxg3 a5 21. Rc1 Kd7 22. Rc2 Rhb8 23. Kg2 h5 24. Nf3 Ke7 25. Rh1` | [ply 37](http://localhost:5173/analysis?game_id=684746&ply=37) | [board](http://localhost:5173/analysis?fen=r3k2r/5ppp/p1p1p3/3p4/2PP1qn1/1P4Q1/P2N1P1P/3R1RK1%20b%20-%20-%200%2019) |
| 979 | allowed | HANGING_PIECE | 0 | `10... Qxf4 11. Rg1 e6 12. Qe2 Nd7 13. Nc3 Qf5 14. Rg5 Qh3+ 15. Kg1 Bd6 16. Rg2` | [ply 18](http://localhost:5173/analysis?game_id=684765&ply=18) | [board](http://localhost:5173/analysis?fen=rn2kb1r/ppp1pppp/8/8/2B2Bq1/3P1N2/PPP2P2/RN1Q1R1K%20b%20-%20-%201%2010) |
| 980 | missed | CLEARANCE | 4 | `10. Bg3 Nd7 11. Nh2 Qg6 12. Qf3 h5 13. Kh1` | [ply 18](http://localhost:5173/analysis?game_id=684765&ply=18) | [board](http://localhost:5173/analysis?fen=rn2kb1r/ppp1pppp/8/8/2B2Bq1/3P1N2/PPP2P2/RN1Q1RK1%20w%20-%20-%200%2010) |
| 981 | allowed | CLEARANCE | 4 | `10. Bxf5 exf5` | [ply 17](http://localhost:5173/analysis?game_id=684767&ply=17) | [board](http://localhost:5173/analysis?fen=2r1k1nr/pp3ppp/2n1p3/q2p1b2/1b1P1B2/2NB1N2/PPP2PPP/R2QK2R%20w%20-%20-%201%2010) |
| 982 | missed | DEFLECTION | 4 | `9... Bg4 10. Be3 Ba3 11. bxa3 Qxc3+ 12. Bd2 Qxa3` | [ply 17](http://localhost:5173/analysis?game_id=684767&ply=17) | [board](http://localhost:5173/analysis?fen=2r1kbnr/pp3ppp/2n1p3/q2p1b2/3P1B2/2NB1N2/PPP2PPP/R2QK2R%20b%20-%20-%200%209) |
| 983 | allowed | PIN | 2 | `12. Bd2 Qa3 13. Qe2 Nf6` | [ply 21](http://localhost:5173/analysis?game_id=684767&ply=21) | [board](http://localhost:5173/analysis?fen=2r1k1nr/pp3ppp/2n1p3/3p1B2/3P1B2/2q2N2/P1P2PPP/R2QK2R%20w%20-%20-%200%2012) |
| 984 | missed | PIN | 0 | `11... exf5` | [ply 21](http://localhost:5173/analysis?game_id=684767&ply=21) | [board](http://localhost:5173/analysis?fen=2r1k1nr/pp3ppp/2n1p3/q2p1B2/3P1B2/2P2N2/P1P2PPP/R2QK2R%20b%20-%20-%200%2011) |
| 985 | allowed | CLEARANCE | 8 | `14... Nxd4 15. Kh1 Nxf3 16. Rxf3 Bxc3 17. Bxc3 Rxf3 18. Qxf3 Rf8 19. Qg4 Qb6 20. Bd4` | [ply 26](http://localhost:5173/analysis?game_id=684769&ply=26) | [board](http://localhost:5173/analysis?fen=r4rk1/qpp3pp/p1n1p3/3nP3/1b1P4/P1N2N2/1PPB2PP/R2Q1RK1%20b%20-%20-%200%2014) |
| 986 | missed | PROMOTION | 2 | `35. d7 Kf7 36. d8=Q f3 37. Qd7+ Kg6 38. Qe6+ Kh7 39. Qf5+ g6 40. Qxf3 g5` | [ply 68](http://localhost:5173/analysis?game_id=684769&ply=68) | [board](http://localhost:5173/analysis?fen=6k1/1p4p1/p2P4/4P3/5p2/P6P/6PK/8%20w%20-%20-%200%2035) |
| 987 | missed | CLEARANCE | 8 | `7. Bxb7 Bxb7 8. Qxb7 Nd7 9. Qc6 Be7 10. b3` | [ply 12](http://localhost:5173/analysis?game_id=684778&ply=12) | [board](http://localhost:5173/analysis?fen=rnbqkb1r/ppp2ppp/4p3/3B4/8/5Q2/PPPP1PPP/R1B1K1NR%20w%20-%20-%200%207) |
| 988 | allowed | CLEARANCE | 8 | `24... Bb6 25. Kf1 Bxd4 26. cxd4 Rad8 27. Rd1 Rf5 28. Re7 Rdf8 29. Rd2 R8f7 30. Rxf7` | [ply 46](http://localhost:5173/analysis?game_id=684778&ply=46) | [board](http://localhost:5173/analysis?fen=r4rk1/ppp3p1/4R3/b5p1/3N4/2P5/PP3PPP/R5K1%20b%20-%20-%200%2024) |
| 989 | allowed | DISCOVERED_ATTACK | 1 | `39... cxb3 40. axb3 Rxc3 41. Rb4 Rc1+ 42. Kh2 Rc5 43. Kg3 a5 44. Rb6+ Kf7 45. Kf3` | [ply 76](http://localhost:5173/analysis?game_id=684778&ply=76) | [board](http://localhost:5173/analysis?fen=8/p7/4k1p1/2r3p1/2pR4/1PP4P/P4PP1/6K1%20b%20-%20-%200%2039) |
| 990 | missed | TRAPPED_PIECE | 6 | `17... Qh6 18. Nf4 Bxf4 19. exf4 g6 20. g4 gxh5 21. g5 Qg6 22. Rae1 Rae8 23. Re3` | [ply 33](http://localhost:5173/analysis?game_id=684805&ply=33) | [board](http://localhost:5173/analysis?fen=r4rk1/pp4pp/2nbp1q1/3p1p1B/3P3P/2P1PQP1/PP2N3/R4RK1%20b%20-%20-%200%2017) |
| 991 | allowed | INTERMEZZO | 2 | `8... hxg5 9. a4 gxf6 10. axb5 cxb5 11. Nxb5 Bb4+ 12. Nc3 Kf8 13. g3 Bb7 14. Bg2` | [ply 14](http://localhost:5173/analysis?game_id=684809&ply=14) | [board](http://localhost:5173/analysis?fen=rnbqkb1r/p4pp1/2p1pP1p/1p4B1/2pP4/2N2N2/PP3PPP/R2QKB1R%20b%20-%20-%200%208) |
| 992 | missed | HANGING_PIECE | 0 | `13. dxe5 Qxd2+ 14. Kxd2 Nd7 15. Bxg4 Nxe5 16. Be2 Ke7 17. f4 Ng6 18. g3 e5` | [ply 24](http://localhost:5173/analysis?game_id=684809&ply=24) | [board](http://localhost:5173/analysis?fen=rnbqk2r/p4p2/2p1p3/1p2b3/2pP2p1/2N5/PP1QBPPP/R3K2R%20w%20-%20-%200%2013) |
| 993 | allowed | DISCOVERED_ATTACK | 1 | `12. Nxf6+ gxf6 13. Qxf5 Bxd2+ 14. Kxd2 Qc3+ 15. Kc1 dxe3 16. Kb1 Qb4+ 17. Ka1 Nc6` | [ply 21](http://localhost:5173/analysis?game_id=684813&ply=21) | [board](http://localhost:5173/analysis?fen=rn3rk1/pp3ppp/5p2/5b2/1b1pN3/3QP3/PqPN1PPP/3RKB1R%20w%20-%20-%201%2012) |
| 994 | allowed | ATTRACTION | 2 | `29. Qxe3 Qxb8 30. Bxf7+ Kxf7 31. Qe6+ Kg6 32. Qxd5 h5 33. Qd3+ Kh6 34. Qe3+ g5` | [ply 55](http://localhost:5173/analysis?game_id=684813&ply=55) | [board](http://localhost:5173/analysis?fen=1R2B1k1/p4pp1/5p1p/3r4/8/2P1n1qP/P2Q2P1/4R2K%20w%20-%20-%201%2029) |
| 995 | allowed | INTERFERENCE | 4 | `30. Rxd1 g6 31. Qf3 Qxb8 32. Qxe3 Qb7 33. Re1 Kg7 34. Qd4 h5` | [ply 57](http://localhost:5173/analysis?game_id=684813&ply=57) | [board](http://localhost:5173/analysis?fen=1R2B1k1/p4pp1/5p1p/8/8/2P1n1qP/P3Q1P1/3rR2K%20w%20-%20-%201%2030) |
| 996 | missed | HANGING_PIECE | 0 | `29... Qxb8 30. Bxf7+ Kxf7 31. Qxe3 Re5 32. Qd2 Rxe1+ 33. Qxe1 a5 34. Qd1 Qe5 35. c4` | [ply 57](http://localhost:5173/analysis?game_id=684813&ply=57) | [board](http://localhost:5173/analysis?fen=1R2B1k1/p4pp1/5p1p/3r4/8/2P1n1qP/P3Q1P1/4R2K%20b%20-%20-%200%2029) |
| 997 | allowed | PROMOTION | 4 | `64. Qxe5 fxe5 65. c7 Kg6 66. c8=Q Kf6 67. Bc2 e4 68. Bxe4 g6 69. Qd8+ Kg7` | [ply 125](http://localhost:5173/analysis?game_id=684813&ply=125) | [board](http://localhost:5173/analysis?fen=8/5ppk/2PK1p1p/1Q2q3/B7/7P/6P1/8%20w%20-%20-%201%2064) |
| 998 | missed | PIN | 8 | `69... f5 70. c8=Q Qd6+ 71. Kb7 Qe7+ 72. Qcd7 Qe4+ 73. Qbd5 Kg5 74. Qxe4 fxe4 75. Qxf7` | [ply 137](http://localhost:5173/analysis?game_id=684813&ply=137) | [board](http://localhost:5173/analysis?fen=1K6/2P1qpp1/5pkp/1Q6/B7/7P/6P1/8%20b%20-%20-%200%2069) |
| 999 | allowed | CLEARANCE | 10 | `14. Nxd5 Be7 15. Qb3` | [ply 25](http://localhost:5173/analysis?game_id=684824&ply=25) | [board](http://localhost:5173/analysis?fen=r2qkb1r/pp3ppp/2n5/3pPp2/8/2N1B3/PP3PPP/R2Q1RK1%20w%20-%20-%200%2014) |
| 1000 | allowed | DEFLECTION | 6 | `13... Qh4 14. Re1 Qxh2+ 15. Kf1 Qh1+ 16. Ke2 Qxg2 17. Rg1 Qf3+ 18. Ke1 Qf4 19. Ne2` | [ply 24](http://localhost:5173/analysis?game_id=684851&ply=24) | [board](http://localhost:5173/analysis?fen=rn2k2r/pp1bqpp1/3p4/2pPp3/2P1P1p1/2NB4/PP3PPN/R2Q1RK1%20b%20-%20-%201%2013) |

### Full PV Lines for Dropped Cases

#### Case 1 — DISCOVERED_CHECK (missed, depth 2)

Moves (SAN): `8... Nxe4 9. Be3`

FEN (line start): `r3kb1r/ppp2ppp/2n2n2/4p1B1/4P1b1/2P2N1P/PP3PP1/RN1K1B1R b - - 0 8`

Game (full game at ply): http://localhost:5173/analysis?game_id=681354&ply=15

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3kb1r/ppp2ppp/2n2n2/4p1B1/4P1b1/2P2N1P/PP3PP1/RN1K1B1R%20b%20-%20-%200%208

#### Case 2 — CLEARANCE (missed, depth 2)

Moves (SAN): `26... Rd8 27. h5 R2d6 28. h6 Rh8 29. h7 Rd7 30. Rh6 Rd6 31. Rh5 Rd7 32. Rxf5`

FEN (line start): `8/1kp5/2nr4/pBp1pp2/P6P/2P2P2/1P1r1P2/1R2K2R b - - 0 26`

Game (full game at ply): http://localhost:5173/analysis?game_id=681354&ply=51

FEN (free-play from line start): http://localhost:5173/analysis?fen=8/1kp5/2nr4/pBp1pp2/P6P/2P2P2/1P1r1P2/1R2K2R%20b%20-%20-%200%2026

#### Case 3 — INTERMEZZO (allowed, depth 2)

Moves (SAN): `22... c3 23. Qc1 Qxb4+ 24. Ka1 Rab8 25. Re3 Qa5 26. Bf1 Rb2 27. Bc4 Ba4 28. Rxc3`

FEN (line start): `r3r1k1/5pp1/p1b4p/8/1Pp1P3/q3Q1P1/P1P2PBP/1K1RR3 b - - 0 22`

Game (full game at ply): http://localhost:5173/analysis?game_id=681357&ply=42

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3r1k1/5pp1/p1b4p/8/1Pp1P3/q3Q1P1/P1P2PBP/1K1RR3%20b%20-%20-%200%2022

#### Case 4 — ATTRACTION (allowed, depth 0)

Moves (SAN): `26... Rxb1+ 27. Kxb1 Qb4+ 28. Kc1 c3 29. Bf1 Bd7 30. Bd3 Bg4 31. f3 Be6 32. Kd1`

FEN (line start): `1r4k1/5pp1/p1b4p/8/q1p1P3/4Q1P1/P1P2PBP/KR6 b - - 1 26`

Game (full game at ply): http://localhost:5173/analysis?game_id=681357&ply=50

FEN (free-play from line start): http://localhost:5173/analysis?fen=1r4k1/5pp1/p1b4p/8/q1p1P3/4Q1P1/P1P2PBP/KR6%20b%20-%20-%201%2026

#### Case 5 — SACRIFICE (missed, depth 2)

Moves (SAN): `35. Kc1 Qxe4 36. exf7 Qe1+ 37. Kb2 c3+ 38. Kb3 Qe6+ 39. Kb4 Qc4+ 40. Ka5 Qxf7`

FEN (line start): `1Q6/5p1k/p3P1pp/1b6/2pqB3/6P1/2PK1P1P/8 w - - 0 35`

Game (full game at ply): http://localhost:5173/analysis?game_id=681357&ply=68

FEN (free-play from line start): http://localhost:5173/analysis?fen=1Q6/5p1k/p3P1pp/1b6/2pqB3/6P1/2PK1P1P/8%20w%20-%20-%200%2035

#### Case 6 — MATE (allowed, depth 8)

Moves (SAN): `37... Qe1+ 38. Kg2 Bf1+ 39. Kf3 Qe2+ 40. Kf4 g5+ 41. Kf5 Qxe6#`

FEN (line start): `1Q6/5p1k/p3P1pp/1b6/4q3/2p3P1/2P2P1P/6K1 b - - 1 37`

Game (full game at ply): http://localhost:5173/analysis?game_id=681357&ply=72

FEN (free-play from line start): http://localhost:5173/analysis?fen=1Q6/5p1k/p3P1pp/1b6/4q3/2p3P1/2P2P1P/6K1%20b%20-%20-%201%2037

#### Case 7 — SACRIFICE (missed, depth 2)

Moves (SAN): `37. Qxb5 axb5 38. exf7 Kg7 39. f8=Q+ Kxf8 40. g4 Qxc2 41. Kg2 Ke7 42. h3 Qe4+`

FEN (line start): `1Q6/5p1k/p3P1pp/1b6/4q3/2p3P1/2P2P1P/5K2 w - - 0 37`

Game (full game at ply): http://localhost:5173/analysis?game_id=681357&ply=72

FEN (free-play from line start): http://localhost:5173/analysis?fen=1Q6/5p1k/p3P1pp/1b6/4q3/2p3P1/2P2P1P/5K2%20w%20-%20-%200%2037

#### Case 8 — SACRIFICE (missed, depth 8)

Moves (SAN): `41. Qf4 Qxg4+ 42. Qxg4 hxg4+ 43. Kg3 Ba4 44. h3 Bxc2 45. f4 gxf3 46. Kxf3 Bf5`

FEN (line start): `1Q6/5p1k/p1b1q1p1/7p/6P1/2p4K/2P2P1P/8 w - - 0 41`

Game (full game at ply): http://localhost:5173/analysis?game_id=681357&ply=80

FEN (free-play from line start): http://localhost:5173/analysis?fen=1Q6/5p1k/p1b1q1p1/7p/6P1/2p4K/2P2P1P/8%20w%20-%20-%200%2041

#### Case 9 — PIN (missed, depth 6)

Moves (SAN): `6. Ndb5 d5 7. Bf4 Na6 8. exd5 e5 9. Qe2 Qe7 10. d6 Qe6 11. Be3 Nf6`

FEN (line start): `rnbqk1nr/pp1p1pbp/4p1p1/8/3NP3/2N5/PPP2PPP/R1BQKB1R w - - 0 6`

Game (full game at ply): http://localhost:5173/analysis?game_id=681358&ply=10

FEN (free-play from line start): http://localhost:5173/analysis?fen=rnbqk1nr/pp1p1pbp/4p1p1/8/3NP3/2N5/PPP2PPP/R1BQKB1R%20w%20-%20-%200%206

#### Case 10 — CLEARANCE (missed, depth 2)

Moves (SAN): `11. Nf3 Na5 12. Qd6 f5 13. Re1 fxe4 14. Nxe4 Bxe4 15. Rxe4 Bxb2 16. Be5 Nf5`

FEN (line start): `r2qk2r/1b1pnpbp/p1n1p1p1/1p6/3NP3/1BN3B1/PPP2PPP/R2Q1K1R w - - 0 11`

Game (full game at ply): http://localhost:5173/analysis?game_id=681358&ply=20

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qk2r/1b1pnpbp/p1n1p1p1/1p6/3NP3/1BN3B1/PPP2PPP/R2Q1K1R%20w%20-%20-%200%2011

#### Case 11 — CLEARANCE (allowed, depth 2)

Moves (UCI — SAN unavailable): `e8g8 f1e2 f8e8 e2f3 b7b5 e1g1 a7a5 f1e1 c8a6 e4e5 d7d6 e5e6`

FEN (line start): `r1b1k2r/pp1p1pbp/5np1/2pP4/4P2q/2PQ2N1/P4PPP/R1B1KB1R b - - 1 11`

Game (full game at ply): http://localhost:5173/analysis?game_id=681359&ply=20

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1b1k2r/pp1p1pbp/5np1/2pP4/4P2q/2PQ2N1/P4PPP/R1B1KB1R%20b%20-%20-%201%2011

#### Case 12 — CLEARANCE (missed, depth 4)

Moves (SAN): `15. Be3 Bd7 16. a4 b6 17. Ra2 Rae8 18. Bf2 Qf4 19. Rd1 Nh5 20. Nxh5 Rxh5`

FEN (line start): `r1b3k1/pp3pbp/3p1np1/2pPr3/4P2q/2PQ1PN1/P3B1PP/R1B2RK1 w - - 0 15`

Game (full game at ply): http://localhost:5173/analysis?game_id=681359&ply=28

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1b3k1/pp3pbp/3p1np1/2pPr3/4P2q/2PQ1PN1/P3B1PP/R1B2RK1%20w%20-%20-%200%2015

#### Case 13 — CLEARANCE (allowed, depth 8)

Moves (SAN): `20... Re8 21. e5 Rf8 22. e6 fxe6 23. dxe6 Ne5 24. Qd5 Re7 25. Rae1 Bxe6 26. Qd1`

FEN (line start): `2b3k1/pr1n1pbp/1pQ3p1/1BpPr3/4Pq2/2P2PN1/P5PP/R4RK1 b - - 1 20`

Game (full game at ply): http://localhost:5173/analysis?game_id=681359&ply=38

FEN (free-play from line start): http://localhost:5173/analysis?fen=2b3k1/pr1n1pbp/1pQ3p1/1BpPr3/4Pq2/2P2PN1/P5PP/R4RK1%20b%20-%20-%201%2020

#### Case 14 — FORK (missed, depth 4)

Moves (SAN): `8... Qb4+ 9. Qd2 Qxb2 10. Qc3 Qc1+ 11. Ke2`

FEN (line start): `r1b1k2r/ppp1qppp/2n1pn2/3P2N1/8/3PQ3/PPP2PPP/RN2KB1R b - - 0 8`

Game (full game at ply): http://localhost:5173/analysis?game_id=681360&ply=15

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1b1k2r/ppp1qppp/2n1pn2/3P2N1/8/3PQ3/PPP2PPP/RN2KB1R%20b%20-%20-%200%208

#### Case 15 — FORK (allowed, depth 2)

Moves (SAN): `16. Rxe6 fxe6 17. Nxe6 Rde8 18. Nxf8 Kxf8 19. Be2 Nf5 20. Bd1 g5 21. Kd2 a5`

FEN (line start): `3r1rk1/1p2npp1/p1p1bn1p/3p4/3N4/P1NP4/1PP2PPP/2K1RB1R w - - 0 16`

Game (full game at ply): http://localhost:5173/analysis?game_id=681360&ply=29

FEN (free-play from line start): http://localhost:5173/analysis?fen=3r1rk1/1p2npp1/p1p1bn1p/3p4/3N4/P1NP4/1PP2PPP/2K1RB1R%20w%20-%20-%200%2016

#### Case 16 — SACRIFICE (missed, depth 2)

Moves (SAN): `15... Nf5 16. Nxe6 Rde8 17. g3 Rxe6 18. Bh3 Rxe1+ 19. Rxe1 Nd4 20. Bg2 Re8 21. Rxe8+`

FEN (line start): `3r1rk1/pp2npp1/2p1bn1p/3p4/3N4/P1NP4/1PP2PPP/2K1RB1R b - - 0 15`

Game (full game at ply): http://localhost:5173/analysis?game_id=681360&ply=29

FEN (free-play from line start): http://localhost:5173/analysis?fen=3r1rk1/pp2npp1/2p1bn1p/3p4/3N4/P1NP4/1PP2PPP/2K1RB1R%20b%20-%20-%200%2015

#### Case 17 — HANGING_PIECE (allowed, depth 0)

Moves (SAN): `17. gxh3`

FEN (line start): `r2q1rk1/2p2ppp/6n1/p2p4/3Pn3/PQ2PN1b/1P2BPP1/R1B2RK1 w - - 0 17`

Game (full game at ply): http://localhost:5173/analysis?game_id=681365&ply=31

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2q1rk1/2p2ppp/6n1/p2p4/3Pn3/PQ2PN1b/1P2BPP1/R1B2RK1%20w%20-%20-%200%2017

#### Case 18 — PIN (missed, depth 0)

Moves (SAN): `7... Bxe2 8. Qxe2`

FEN (line start): `r2qk2r/ppp2ppp/2n1pn2/3pN3/1b1P1Bb1/2N1P3/PPP1BPPP/R2QK2R b - - 0 7`

Game (full game at ply): http://localhost:5173/analysis?game_id=681368&ply=13

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qk2r/ppp2ppp/2n1pn2/3pN3/1b1P1Bb1/2N1P3/PPP1BPPP/R2QK2R%20b%20-%20-%200%207

#### Case 19 — SACRIFICE (missed, depth 4)

Moves (SAN): `25... Rxc2 26. Bxg7+ Qxg7 27. Kxc2 Rf2+ 28. Kd1 Qg2 29. Qe5+ Kg8 30. Qg3+ Qxg3 31. hxg3`

FEN (line start): `5r1k/p5pp/4Q3/3pB3/3Pp3/PK2P3/2P2rqP/R3R3 b - - 0 25`

Game (full game at ply): http://localhost:5173/analysis?game_id=681368&ply=49

FEN (free-play from line start): http://localhost:5173/analysis?fen=5r1k/p5pp/4Q3/3pB3/3Pp3/PK2P3/2P2rqP/R3R3%20b%20-%20-%200%2025

#### Case 20 — PIN (missed, depth 6)

Moves (SAN): `26. Kf2 Rb8 27. b3 a5 28. Rh1 Ke7 29. Rh7 Kf7 30. Rh3 a4 31. Re3 Ra8`

FEN (line start): `7r/2pk2p1/p2p1p2/2pP1Pp1/2P3P1/8/PP4P1/4R1K1 w - - 0 26`

Game (full game at ply): http://localhost:5173/analysis?game_id=681369&ply=50

FEN (free-play from line start): http://localhost:5173/analysis?fen=7r/2pk2p1/p2p1p2/2pP1Pp1/2P3P1/8/PP4P1/4R1K1%20w%20-%20-%200%2026

#### Case 21 — DISCOVERED_ATTACK (missed, depth 3)

Moves (SAN): `11. Nxd5 Bb7 12. Nf6+ Nxf6 13. Rxd8+ Rxd8 14. Bd2 Nd7 15. Qg4 Rg8 16. Bg5 a6`

FEN (line start): `r1bqk1nr/p3bppp/1pn1p3/3pP3/2B2Q2/2N2N2/PPP2PPP/R1BR2K1 w - - 0 11`

Game (full game at ply): http://localhost:5173/analysis?game_id=681372&ply=20

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1bqk1nr/p3bppp/1pn1p3/3pP3/2B2Q2/2N2N2/PPP2PPP/R1BR2K1%20w%20-%20-%200%2011

#### Case 22 — DEFLECTION (missed, depth 4)

Moves (SAN): `12. Ne4 Nh6 13. Nf6+ gxf6 14. Qxh6 Bf8 15. Qh5 a6 16. Bxc6+ Bxc6 17. Be3 f5`

FEN (line start): `r2qk1nr/pb2bppp/1pn1p3/1B1pP3/5Q2/2N2N2/PPP2PPP/R1BR2K1 w - - 0 12`

Game (full game at ply): http://localhost:5173/analysis?game_id=681372&ply=22

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qk1nr/pb2bppp/1pn1p3/1B1pP3/5Q2/2N2N2/PPP2PPP/R1BR2K1%20w%20-%20-%200%2012

#### Case 23 — SACRIFICE (missed, depth 2)

Moves (SAN): `17. Rxd4 exd4 18. g5 dxc3 19. gxf6 Bxf6 20. bxc3 g6 21. Qh3 Qe7 22. Be3 Bc8`

FEN (line start): `r2q3r/pb2bkpp/1p3n2/1B1ppQ2/3n2P1/2N5/PPP2P1P/R1BR2K1 w - - 0 17`

Game (full game at ply): http://localhost:5173/analysis?game_id=681372&ply=32

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2q3r/pb2bkpp/1p3n2/1B1ppQ2/3n2P1/2N5/PPP2P1P/R1BR2K1%20w%20-%20-%200%2017

#### Case 24 — FORK (missed, depth 0)

Moves (SAN): `35. Re5+ Kd8 36. Rd5+ Ke8 37. Rxc5 R8g7 38. Rc8+ Kf7 39. Rc7+ Kf8 40. Rcxg7 Rxg7`

FEN (line start): `4k1r1/p6R/8/1pb2R2/6r1/P5B1/1PP2P1P/5K2 w - - 0 35`

Game (full game at ply): http://localhost:5173/analysis?game_id=681372&ply=68

FEN (free-play from line start): http://localhost:5173/analysis?fen=4k1r1/p6R/8/1pb2R2/6r1/P5B1/1PP2P1P/5K2%20w%20-%20-%200%2035

#### Case 25 — PIN (allowed, depth 2)

Moves (SAN): `6. Bb5+ Nfd7 7. Qe2 Nc6 8. Nf3 Bc5 9. fxe5`

FEN (line start): `rnbqkb1r/pp3ppp/5n2/3pp3/2B2P2/2N5/PPPP2PP/R1BQK1NR w - - 0 6`

Game (full game at ply): http://localhost:5173/analysis?game_id=681377&ply=9

FEN (free-play from line start): http://localhost:5173/analysis?fen=rnbqkb1r/pp3ppp/5n2/3pp3/2B2P2/2N5/PPPP2PP/R1BQK1NR%20w%20-%20-%200%206

#### Case 26 — CLEARANCE (missed, depth 8)

Moves (SAN): `5... e4 6. dxc6 Nxc6 7. d3 Bg4 8. Nge2 Qb6 9. dxe4 Rd8 10. Bd3 Bc5 11. Kf1`

FEN (line start): `rnbqkb1r/pp3ppp/2p2n2/3Pp3/2B2P2/2N5/PPPP2PP/R1BQK1NR b - - 0 5`

Game (full game at ply): http://localhost:5173/analysis?game_id=681377&ply=9

FEN (free-play from line start): http://localhost:5173/analysis?fen=rnbqkb1r/pp3ppp/2p2n2/3Pp3/2B2P2/2N5/PPPP2PP/R1BQK1NR%20b%20-%20-%200%205

#### Case 27 — SACRIFICE (missed, depth 2)

Moves (SAN): `17... Bxg4 18. hxg4 Qf3 19. Qf1 Re6 20. g5 Qxf4+ 21. Kg2 Qxg5+ 22. Kxf2 Rf6+ 23. Ke1`

FEN (line start): `4rrk1/pp3ppp/8/3qp2b/5PP1/2P4P/PP1PRb1K/R1BQ4 b - - 0 17`

Game (full game at ply): http://localhost:5173/analysis?game_id=681377&ply=33

FEN (free-play from line start): http://localhost:5173/analysis?fen=4rrk1/pp3ppp/8/3qp2b/5PP1/2P4P/PP1PRb1K/R1BQ4%20b%20-%20-%200%2017

#### Case 28 — CLEARANCE (allowed, depth 8)

Moves (SAN): `5. dxc6 bxc6 6. Nc3 Be7 7. Bd3`

FEN (line start): `r1bqkb1r/ppp2ppp/2np1n2/3Pp3/4P3/5N2/PPP2PPP/RNBQKB1R w - - 1 5`

Game (full game at ply): http://localhost:5173/analysis?game_id=681378&ply=7

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1bqkb1r/ppp2ppp/2np1n2/3Pp3/4P3/5N2/PPP2PPP/RNBQKB1R%20w%20-%20-%201%205

#### Case 29 — CLEARANCE (missed, depth 2)

Moves (SAN): `15... Bh4 16. Qf3 Qg5+ 17. Kb1 Bg4 18. Qd3 dxc3 19. f3 Rfd8 20. Qxc3 Bf5 21. Qxe5`

FEN (line start): `r1bq1rk1/pp3pp1/5b1p/4p3/3pB3/2N3Q1/PPP2PPP/2KR3R b - - 0 15`

Game (full game at ply): http://localhost:5173/analysis?game_id=681378&ply=29

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1bq1rk1/pp3pp1/5b1p/4p3/3pB3/2N3Q1/PPP2PPP/2KR3R%20b%20-%20-%200%2015

#### Case 30 — DISCOVERED_CHECK (missed, depth 10)

Moves (SAN): `25... Bd5 26. Qh5 g6 27. Qg4 Be6 28. Qb4 Rd1+ 29. Kb2 Bc1+ 30. Ka1 Ba3+ 31. Qb1`

FEN (line start): `6k1/p4pp1/B3b2p/4p1b1/8/2P2Q1P/2Pr1PP1/1K6 b - - 0 25`

Game (full game at ply): http://localhost:5173/analysis?game_id=681378&ply=49

FEN (free-play from line start): http://localhost:5173/analysis?fen=6k1/p4pp1/B3b2p/4p1b1/8/2P2Q1P/2Pr1PP1/1K6%20b%20-%20-%200%2025

#### Case 31 — PIN (allowed, depth 4)

Moves (SAN): `6... Nxd5 7. exd5 Qxd5 8. Nc3 Bb4 9. Bd2 Bxc3 10. Bxc3 exd4 11. Bxd4`

FEN (line start): `r1bqkb1r/1pp1nppp/p1n5/3Bp3/3PP3/5N2/PPP2PPP/RNBQK2R b - - 0 6`

Game (full game at ply): http://localhost:5173/analysis?game_id=681380&ply=10

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1bqkb1r/1pp1nppp/p1n5/3Bp3/3PP3/5N2/PPP2PPP/RNBQK2R%20b%20-%20-%200%206

#### Case 32 — CLEARANCE (missed, depth 4)

Moves (SAN): `8. dxc6 Qxc6`

FEN (line start): `r1b1kb1r/1pp2ppp/p1nq4/3Pp3/3P4/5N2/PPP2PPP/RNBQK2R w - - 0 8`

Game (full game at ply): http://localhost:5173/analysis?game_id=681380&ply=14

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1b1kb1r/1pp2ppp/p1nq4/3Pp3/3P4/5N2/PPP2PPP/RNBQK2R%20w%20-%20-%200%208

#### Case 33 — INTERFERENCE (missed, depth 2)

Moves (SAN): `14. Rc5 Qe6 15. Rxc7 Qd6 16. Rc5 Re8 17. Be3 b6 18. Rg5 f6 19. Rg3 Bf5`

FEN (line start): `r1b2rk1/1pp2ppp/p7/4R3/2qP4/2P5/P1P2PPP/R1BQ2K1 w - - 0 14`

Game (full game at ply): http://localhost:5173/analysis?game_id=681380&ply=26

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1b2rk1/1pp2ppp/p7/4R3/2qP4/2P5/P1P2PPP/R1BQ2K1%20w%20-%20-%200%2014

#### Case 34 — HANGING_PIECE (allowed, depth 0)

Moves (SAN): `15... gxh6 16. Qf3`

FEN (line start): `r1b2rk1/1pp1R1pp/p4p1B/8/2qP4/2P5/P1P2PPP/R2Q2K1 b - - 1 15`

Game (full game at ply): http://localhost:5173/analysis?game_id=681380&ply=28

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1b2rk1/1pp1R1pp/p4p1B/8/2qP4/2P5/P1P2PPP/R2Q2K1%20b%20-%20-%201%2015

#### Case 35 — DISCOVERED_ATTACK (allowed, depth 3)

Moves (SAN): `20... Re8 21. a3 Bd7 22. Qd2 Rxe1+ 23. Qxe1 Qe6 24. Qxe6+ Kxe6 25. c4 Ba4 26. f3`

FEN (line start): `1r6/1pp2k1p/p3bppB/8/2qP4/2P1Q3/P1P2PPP/4R1K1 b - - 1 20`

Game (full game at ply): http://localhost:5173/analysis?game_id=681380&ply=38

FEN (free-play from line start): http://localhost:5173/analysis?fen=1r6/1pp2k1p/p3bppB/8/2qP4/2P1Q3/P1P2PPP/4R1K1%20b%20-%20-%201%2020

#### Case 36 — PIN (allowed, depth 8)

Moves (SAN): `23... Rxe3 24. Rxe3 Qd1+ 25. Kg2 Qxg4+ 26. Kf1 Qxh4 27. Rd3 Bb5 28. Be3 Bxd3+ 29. cxd3`

FEN (line start): `4r3/1ppb1k1p/p4ppB/3q4/6PP/2P1Q3/P1P2P2/4R1K1 b - - 0 23`

Game (full game at ply): http://localhost:5173/analysis?game_id=681380&ply=44

FEN (free-play from line start): http://localhost:5173/analysis?fen=4r3/1ppb1k1p/p4ppB/3q4/6PP/2P1Q3/P1P2P2/4R1K1%20b%20-%20-%200%2023

#### Case 37 — SACRIFICE (missed, depth 10)

Moves (SAN): `27. f3 Qa4 28. Kf2 Qxc2+ 29. Kf1 Qb1+ 30. Kf2 Qb2+ 31. Kg1 Qxc3 32. h5 g5`

FEN (line start): `8/1pp2k1p/p1b2ppB/8/6qP/2P3R1/P1P2PK1/8 w - - 0 27`

Game (full game at ply): http://localhost:5173/analysis?game_id=681380&ply=52

FEN (free-play from line start): http://localhost:5173/analysis?fen=8/1pp2k1p/p1b2ppB/8/6qP/2P3R1/P1P2PK1/8%20w%20-%20-%200%2027

#### Case 38 — SACRIFICE (missed, depth 2)

Moves (SAN): `29. Kf1 Qxh6 30. Re3 Qh1+ 31. Ke2 Qg2 32. Rd3 g5 33. Rd4 h5 34. Kd2 b5`

FEN (line start): `8/1pp2k1p/p1b2ppB/8/7q/2P3R1/P1P2P2/6K1 w - - 0 29`

Game (full game at ply): http://localhost:5173/analysis?game_id=681380&ply=56

FEN (free-play from line start): http://localhost:5173/analysis?fen=8/1pp2k1p/p1b2ppB/8/7q/2P3R1/P1P2P2/6K1%20w%20-%20-%200%2029

#### Case 39 — PIN (allowed, depth 0)

Moves (SAN): `9. Qe2 Nc6`

FEN (line start): `rnb1kb1r/pppp3p/6p1/1B3p1Q/4q3/8/PPPP1PPP/R1B1K2R w - - 0 9`

Game (full game at ply): http://localhost:5173/analysis?game_id=681384&ply=15

FEN (free-play from line start): http://localhost:5173/analysis?fen=rnb1kb1r/pppp3p/6p1/1B3p1Q/4q3/8/PPPP1PPP/R1B1K2R%20w%20-%20-%200%209

#### Case 40 — PIN (allowed, depth 0)

Moves (SAN): `20... Rxe3+ 21. Kf1 Rf8 22. Nf3 Rexf3 23. gxf3 Rxf3 24. Qg2 Rxd3 25. Qg8+ Bf8 26. Rg1`

FEN (line start): `2k1r2r/pp1n2Qp/2p5/8/1b1N3q/2PPB3/PP3PPP/R3K2R b - - 1 20`

Game (full game at ply): http://localhost:5173/analysis?game_id=681385&ply=38

FEN (free-play from line start): http://localhost:5173/analysis?fen=2k1r2r/pp1n2Qp/2p5/8/1b1N3q/2PPB3/PP3PPP/R3K2R%20b%20-%20-%201%2020

#### Case 41 — HANGING_PIECE (missed, depth 0)

Moves (SAN): `23. fxe3 Bc5 24. Re1 Nd7 25. Nf3 Qa4 26. d4 Be7 27. e4 Qxa2 28. Re2 a5`

FEN (line start): `2k2n2/pp5p/2p5/8/1b1N3q/2PPr3/PP3PPP/R4K1R w - - 0 23`

Game (full game at ply): http://localhost:5173/analysis?game_id=681385&ply=44

FEN (free-play from line start): http://localhost:5173/analysis?fen=2k2n2/pp5p/2p5/8/1b1N3q/2PPr3/PP3PPP/R4K1R%20w%20-%20-%200%2023

#### Case 42 — HANGING_PIECE (missed, depth 0)

Moves (SAN): `33. gxf4 Rd1 34. Rxc6+ Kb8 35. Rcc7 a5 36. bxa5 b4 37. Rcf7 Rd8 38. f5 Rh8`

FEN (line start): `2k5/p5R1/2p1R3/1p6/1P3n2/6P1/PP3PK1/7r w - - 0 33`

Game (full game at ply): http://localhost:5173/analysis?game_id=681385&ply=64

FEN (free-play from line start): http://localhost:5173/analysis?fen=2k5/p5R1/2p1R3/1p6/1P3n2/6P1/PP3PK1/7r%20w%20-%20-%200%2033

#### Case 43 — PIN (missed, depth 0)

Moves (SAN): `41. Kd4 Kc7 42. f8=Q Ne6+ 43. Kd3 Nxf8 44. Kxe2 Ne6 45. Ra8 Kd6 46. Rxa7 c5`

FEN (line start): `2kn2R1/p4P2/2p5/1p2K3/8/6P1/4r3/8 w - - 0 41`

Game (full game at ply): http://localhost:5173/analysis?game_id=681385&ply=80

FEN (free-play from line start): http://localhost:5173/analysis?fen=2kn2R1/p4P2/2p5/1p2K3/8/6P1/4r3/8%20w%20-%20-%200%2041

#### Case 44 — DEFLECTION (missed, depth 10)

Moves (SAN): `5. d5 gxf3 6. dxc6 dxc6 7. Qxf3 Be6 8. Nc3 Qd4 9. Qh5+ Bf7 10. Qxf5 Bg6`

FEN (line start): `r1bqkbnr/ppppp2p/2n5/4Pp2/3P2p1/5N2/PPP2PPP/RNBQKB1R w - - 0 5`

Game (full game at ply): http://localhost:5173/analysis?game_id=681387&ply=8

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1bqkbnr/ppppp2p/2n5/4Pp2/3P2p1/5N2/PPP2PPP/RNBQKB1R%20w%20-%20-%200%205

#### Case 45 — DISCOVERED_CHECK (missed, depth 4)

Moves (SAN): `8. Qe2 Nd7 9. Nxe5 Qxg2 10. Nf3+ Kd8 11. Rg1 Qh3 12. Ng5 Qxh2 13. Nxf7+ Kc7`

FEN (line start): `rnb1kb1r/pp3ppp/2q5/2p1p3/2B5/1P3N2/P1PP1PPP/R1BQK2R w - - 0 8`

Game (full game at ply): http://localhost:5173/analysis?game_id=681388&ply=14

FEN (free-play from line start): http://localhost:5173/analysis?fen=rnb1kb1r/pp3ppp/2q5/2p1p3/2B5/1P3N2/P1PP1PPP/R1BQK2R%20w%20-%20-%200%208

#### Case 46 — DISCOVERED_ATTACK (missed, depth 3)

Moves (SAN): `11. Bb2 Be6 12. Nxf7 Qxb2 13. Rxe6 Nc6 14. Ne5 Kh8 15. Nxc6 Bh4 16. Rb1 Bxf2+`

FEN (line start): `rnb2rk1/pp2bppp/5q2/2p1N3/2B5/1P6/P1PP1PPP/R1BQR1K1 w - - 0 11`

Game (full game at ply): http://localhost:5173/analysis?game_id=681388&ply=20

FEN (free-play from line start): http://localhost:5173/analysis?fen=rnb2rk1/pp2bppp/5q2/2p1N3/2B5/1P6/P1PP1PPP/R1BQR1K1%20w%20-%20-%200%2011

#### Case 47 — DEFLECTION (allowed, depth 8)

Moves (SAN): `13... Nc6 14. Ba3 Bf5 15. c3 b5 16. d4 b4 17. cxb4 cxd4 18. Rc1 Rc8 19. Qf3`

FEN (line start): `rnb5/pp2bkpp/5q2/2p5/8/1P1P4/P1P2PPP/R1BQR1K1 b - - 0 13`

Game (full game at ply): http://localhost:5173/analysis?game_id=681388&ply=24

FEN (free-play from line start): http://localhost:5173/analysis?fen=rnb5/pp2bkpp/5q2/2p5/8/1P1P4/P1P2PPP/R1BQR1K1%20b%20-%20-%200%2013

#### Case 48 — CLEARANCE (missed, depth 2)

Moves (SAN): `14. Rxe7+ Kf8 15. Qe1 Nc6 16. Re8+ Kf7 17. c3 h6 18. d4 Rb8 19. d5 Bd7`

FEN (line start): `rnb5/pp2bkpp/8/2p5/8/1P1P4/P1P2PPP/q1BQR1K1 w - - 0 14`

Game (full game at ply): http://localhost:5173/analysis?game_id=681388&ply=26

FEN (free-play from line start): http://localhost:5173/analysis?fen=rnb5/pp2bkpp/8/2p5/8/1P1P4/P1P2PPP/q1BQR1K1%20w%20-%20-%200%2014

#### Case 49 — SACRIFICE (allowed, depth 6)

Moves (SAN): `21... Bxg5 22. Qg3 Be7 23. Rxe5 Kf8 24. Qxg4 c4 25. Kf1 cxb3 26. axb3 Rd8 27. Qf3`

FEN (line start): `r3k3/p3b1qp/1p4p1/2pPn1B1/5Pb1/1P2Q3/P1P3PP/4R1K1 b - - 1 21`

Game (full game at ply): http://localhost:5173/analysis?game_id=681388&ply=40

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3k3/p3b1qp/1p4p1/2pPn1B1/5Pb1/1P2Q3/P1P3PP/4R1K1%20b%20-%20-%201%2021

#### Case 50 — ATTRACTION (allowed, depth 6)

Moves (SAN): `10. Bxc6 Bxh2+ 11. Nxh2 Bxc6 12. Re1+ Ne4 13. Qxd8+ Kxd8 14. Rd1+ Kc8 15. Nf1 b6`

FEN (line start): `r2qk2r/pppb1ppp/2n2n2/1B2b3/8/5N2/PPP2PPP/RNBQ1RK1 w - - 1 10`

Game (full game at ply): http://localhost:5173/analysis?game_id=681389&ply=17

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qk2r/pppb1ppp/2n2n2/1B2b3/8/5N2/PPP2PPP/RNBQ1RK1%20w%20-%20-%201%2010

#### Case 51 — SACRIFICE (missed, depth 4)

Moves (UCI — SAN unavailable): `e8c8 b1d2 e7b4 b5c6 e5h2 f3h2 d7c6 d1c1 h7h6 c2c3 b4b5 g5f4`

FEN (line start): `r3k2r/pppbqppp/2n2n2/1B2b1B1/8/5N2/PPP2PPP/RN1QR1K1 b - - 0 11`

Game (full game at ply): http://localhost:5173/analysis?game_id=681389&ply=21

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3k2r/pppbqppp/2n2n2/1B2b1B1/8/5N2/PPP2PPP/RN1QR1K1%20b%20-%20-%200%2011

#### Case 52 — DEFLECTION (allowed, depth 2)

Moves (SAN): `31. Re7+ Kc8 32. bxc6 a6 33. Rxf7 Qd5 34. Rxg7 Qxa5 35. h3 Qa1 36. Ra7 Qa4`

FEN (line start): `8/pk3pp1/2p4p/PP6/8/4R3/6PP/3q2NK w - - 0 31`

Game (full game at ply): http://localhost:5173/analysis?game_id=681390&ply=59

FEN (free-play from line start): http://localhost:5173/analysis?fen=8/pk3pp1/2p4p/PP6/8/4R3/6PP/3q2NK%20w%20-%20-%200%2031

#### Case 53 — SACRIFICE (missed, depth 2)

Moves (SAN): `22. Kh1 Nxe1 23. Qxe1 a6 24. Qe5 Qb8 25. Qd4 Qc7 26. a4 bxa4 27. h4 Rxc6`

FEN (line start): `3q1r2/p4pk1/1rB2n1p/1p1P1Pp1/1Pp5/2Nn4/P3Q1PP/4RRK1 w - - 0 22`

Game (full game at ply): http://localhost:5173/analysis?game_id=681392&ply=42

FEN (free-play from line start): http://localhost:5173/analysis?fen=3q1r2/p4pk1/1rB2n1p/1p1P1Pp1/1Pp5/2Nn4/P3Q1PP/4RRK1%20w%20-%20-%200%2022

#### Case 54 — PIN (missed, depth 0)

Moves (SAN): `7... Qe7 8. Bf4 Nh5 9. g3 Nxf4 10. gxf4 Qh4 11. Qe3 g5 12. f5 Qd4 13. Nc3`

FEN (line start): `r1bqkb1r/pp1p1ppp/5n2/2p1P3/8/3Q4/PPP2PPP/RNB1KB1R b - - 0 7`

Game (full game at ply): http://localhost:5173/analysis?game_id=681394&ply=13

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1bqkb1r/pp1p1ppp/5n2/2p1P3/8/3Q4/PPP2PPP/RNB1KB1R%20b%20-%20-%200%207

#### Case 55 — FORK (allowed, depth 8)

Moves (SAN): `12. exf6 Bxd5 13. cxd5 gxf6 14. Bxf6 Rg8 15. d6 c4 16. dxe7 Qxd3 17. Bxd3 cxd3`

FEN (line start): `r2qkb1r/pp2n1pp/4bp2/2pNP1B1/2P5/3Q4/PP3PPP/R3KB1R w - - 0 12`

Game (full game at ply): http://localhost:5173/analysis?game_id=681394&ply=21

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qkb1r/pp2n1pp/4bp2/2pNP1B1/2P5/3Q4/PP3PPP/R3KB1R%20w%20-%20-%200%2012

#### Case 56 — ATTRACTION (allowed, depth 2)

Moves (SAN): `15. Qf5 Qd7 16. Qxd7+ Kxd7 17. Rxd5+ Ke6 18. Bc4 Kf5 19. Re1 g4 20. Rd7 Re8`

FEN (line start): `r2qkb1r/pp4pp/8/2pbP1p1/8/3Q4/PP2BPPP/2KR3R w - - 0 15`

Game (full game at ply): http://localhost:5173/analysis?game_id=681394&ply=27

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qkb1r/pp4pp/8/2pbP1p1/8/3Q4/PP2BPPP/2KR3R%20w%20-%20-%200%2015

#### Case 57 — CLEARANCE (missed, depth 8)

Moves (SAN): `9... Bxc3 10. bxc3 Nc6 11. h3 h6 12. Bg3 b6 13. Bh4 Bb7 14. Bd3 Ne7 15. Qb1`

FEN (line start): `rnbq1rk1/pp3ppp/4pn2/2p5/1bBP1B2/P1N1P3/1P2NPPP/R2Q1RK1 b - - 0 9`

Game (full game at ply): http://localhost:5173/analysis?game_id=681396&ply=17

FEN (free-play from line start): http://localhost:5173/analysis?fen=rnbq1rk1/pp3ppp/4pn2/2p5/1bBP1B2/P1N1P3/1P2NPPP/R2Q1RK1%20b%20-%20-%200%209

#### Case 58 — HANGING_PIECE (missed, depth 0)

Moves (SAN): `19... Rxd6 20. Nf4 Qe5 21. bxa7 Bb7 22. Rfd1 Nxa7 23. Bf1 Rxd1 24. Rxd1 g5 25. Nh5`

FEN (line start): `r1br2k1/p4ppp/1PnNp3/7q/1PB5/P3P1P1/2Q1NP2/R4RK1 b - - 0 19`

Game (full game at ply): http://localhost:5173/analysis?game_id=681396&ply=37

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1br2k1/p4ppp/1PnNp3/7q/1PB5/P3P1P1/2Q1NP2/R4RK1%20b%20-%20-%200%2019

#### Case 59 — CLEARANCE (missed, depth 2)

Moves (SAN): `20. Be3 Kf7 21. Rac1 Kg8 22. Qf2 Nd8 23. Qc2 Rf7 24. b4 Ne6 25. a4 Kh7`

FEN (line start): `4kr1r/p1pq2p1/1pn4p/3pPp2/3P1P1Q/8/PP4PP/R1B2RK1 w - - 0 20`

Game (full game at ply): http://localhost:5173/analysis?game_id=681397&ply=38

FEN (free-play from line start): http://localhost:5173/analysis?fen=4kr1r/p1pq2p1/1pn4p/3pPp2/3P1P1Q/8/PP4PP/R1B2RK1%20w%20-%20-%200%2020

#### Case 60 — CAPTURING_DEFENDER (missed, depth 2)

Moves (SAN): `27. Qxg7 Rxg7 28. Bxh6 Rgg8 29. Bxf8 Rxf8 30. e7 Rf7 31. Rf4 Rxe7 32. Kf2 Kd7`

FEN (line start): `4krr1/p5q1/1pp1P2p/3p1p2/3Q1B2/1P6/P5PP/4RRK1 w - - 0 27`

Game (full game at ply): http://localhost:5173/analysis?game_id=681397&ply=52

FEN (free-play from line start): http://localhost:5173/analysis?fen=4krr1/p5q1/1pp1P2p/3p1p2/3Q1B2/1P6/P5PP/4RRK1%20w%20-%20-%200%2027

#### Case 61 — CLEARANCE (missed, depth 2)

Moves (SAN): `12. g4 Ne7 13. Qg2 c5 14. dxc5 Bxc5 15. g5 Ne8 16. Rad1 Qd7 17. Kh1 Rd8`

FEN (line start): `r2q1rk1/1pp2ppp/p1nb1n2/3p4/3P4/P1NBPQ2/1P1B1PPP/R4RK1 w - - 0 12`

Game (full game at ply): http://localhost:5173/analysis?game_id=681399&ply=22

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2q1rk1/1pp2ppp/p1nb1n2/3p4/3P4/P1NBPQ2/1P1B1PPP/R4RK1%20w%20-%20-%200%2012

#### Case 62 — HANGING_PIECE (missed, depth 0)

Moves (SAN): `21. dxe5 Qxd3 22. Bxf8 Rxf8 23. Red1 Qe4 24. Rc7 Rf7 25. Rc8+ Kg7 26. Re8 Rc7`

FEN (line start): `r4rk1/1p1q3p/p5p1/2B1np2/3P4/P2BP3/1P3PP1/2R1R1K1 w - - 0 21`

Game (full game at ply): http://localhost:5173/analysis?game_id=681399&ply=40

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4rk1/1p1q3p/p5p1/2B1np2/3P4/P2BP3/1P3PP1/2R1R1K1%20w%20-%20-%200%2021

#### Case 63 — SKEWER (missed, depth 2)

Moves (SAN): `16. Rab1 Qe2 17. Rxb7 Rfd8 18. Rd7 Qc2 19. g3 Nb4 20. Rxd8+ Rxd8 21. Qb7 Bf8`

FEN (line start): `r4rk1/pp2bppp/2n5/3Q4/8/4BN2/Pq3PPP/R4RK1 w - - 0 16`

Game (full game at ply): http://localhost:5173/analysis?game_id=681400&ply=30

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4rk1/pp2bppp/2n5/3Q4/8/4BN2/Pq3PPP/R4RK1%20w%20-%20-%200%2016

#### Case 64 — SKEWER (missed, depth 4)

Moves (SAN): `18. a4 a6 19. Rab1 Qc2 20. Rxb7 Rd1 21. g3 Rxf1+ 22. Kxf1 Qe4 23. Rd7 Ne5`

FEN (line start): `3r1rk1/pp3ppp/2n5/6Q1/8/4B3/Pq3PPP/R4RK1 w - - 0 18`

Game (full game at ply): http://localhost:5173/analysis?game_id=681400&ply=34

FEN (free-play from line start): http://localhost:5173/analysis?fen=3r1rk1/pp3ppp/2n5/6Q1/8/4B3/Pq3PPP/R4RK1%20w%20-%20-%200%2018

#### Case 65 — CLEARANCE (missed, depth 10)

Moves (SAN): `6... Nxe5 7. dxe5 Bxc5 8. Qc2 Bb6 9. a4 a5 10. b3 c6 11. Bb2 Bc7 12. Be2`

FEN (line start): `r1bqkbnr/ppp2ppp/2n5/2PpN3/3Pp3/4P3/PP3PPP/RNBQKB1R b - - 0 6`

Game (full game at ply): http://localhost:5173/analysis?game_id=681402&ply=11

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1bqkbnr/ppp2ppp/2n5/2PpN3/3Pp3/4P3/PP3PPP/RNBQKB1R%20b%20-%20-%200%206

#### Case 66 — FORK (missed, depth 2)

Moves (SAN): `15... Bh4+ 16. Kd2 Nf2 17. Qe1 Nxh1 18. Qxh1 f4 19. fxe4 fxe3+ 20. Kc2 Qg5 21. Kb3`

FEN (line start): `r2q1rk1/p1pbb1p1/2p4p/2Pp1p1P/1P1Pp1n1/2N1PP2/P3B1P1/R1BQK2R b - - 0 15`

Game (full game at ply): http://localhost:5173/analysis?game_id=681402&ply=29

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2q1rk1/p1pbb1p1/2p4p/2Pp1p1P/1P1Pp1n1/2N1PP2/P3B1P1/R1BQK2R%20b%20-%20-%200%2015

#### Case 67 — CLEARANCE (allowed, depth 4)

Moves (SAN): `14. Bxe6 fxe6 15. d4 Qb4 16. Qc3 Nd5 17. Qxb4 Nxb4 18. Re2 Nd5 19. Nc3 Nxc3`

FEN (line start): `r4rk1/p2nqpp1/2p1bn1p/1p6/2B5/3P2QN/PPP2PPP/RN2R1K1 w - - 0 14`

Game (full game at ply): http://localhost:5173/analysis?game_id=681403&ply=25

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4rk1/p2nqpp1/2p1bn1p/1p6/2B5/3P2QN/PPP2PPP/RN2R1K1%20w%20-%20-%200%2014

#### Case 68 — CLEARANCE (missed, depth 6)

Moves (SAN): `16... Qe7 17. Nxf6+ Nxf6 18. Nd2 Nd5 19. Re5 Rf6 20. Rae1 Raf8 21. Ne4 Rf5 22. a3`

FEN (line start): `r4rk1/p2n2p1/2pqpn1p/1p5N/8/3P2Q1/PPP2PPP/RN2R1K1 b - - 0 16`

Game (full game at ply): http://localhost:5173/analysis?game_id=681403&ply=31

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4rk1/p2n2p1/2pqpn1p/1p5N/8/3P2Q1/PPP2PPP/RN2R1K1%20b%20-%20-%200%2016

#### Case 69 — DISCOVERED_CHECK (missed, depth 4)

Moves (SAN): `10... e4 11. Ng5 Nxd3+ 12. Bxd3 exd3+ 13. Kf1 f6 14. Nh3 Qe4 15. f3 Bxh3+ 16. Rxh3`

FEN (line start): `r1b2rk1/ppp1qppp/2n5/4p3/2P2n1P/P2P1NP1/1P3P2/RN1QKB1R b - - 0 10`

Game (full game at ply): http://localhost:5173/analysis?game_id=681406&ply=19

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1b2rk1/ppp1qppp/2n5/4p3/2P2n1P/P2P1NP1/1P3P2/RN1QKB1R%20b%20-%20-%200%2010

#### Case 70 — FORK (allowed, depth 0)

Moves (SAN): `22. Rf4 Bxd2 23. Rxg4 Rxe1 24. Rxe1 Bxe1 25. Rxg7+ Kf8 26. Rxh7 Ke7 27. Rh5 Bb4`

FEN (line start): `r3r1k1/p1p2ppp/8/8/1b4b1/8/1BPP1RKP/R3N3 w - - 0 22`

Game (full game at ply): http://localhost:5173/analysis?game_id=681407&ply=41

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3r1k1/p1p2ppp/8/8/1b4b1/8/1BPP1RKP/R3N3%20w%20-%20-%200%2022

#### Case 71 — CLEARANCE (missed, depth 4)

Moves (SAN): `21... Re4 22. Bc3 Bd7 23. d3 Rg4+ 24. Kf1 Rg6 25. Nf3 Bh3+ 26. Ke1 Re8+ 27. Re2`

FEN (line start): `r3r1k1/p1p2ppp/3b4/8/1P4b1/8/1BPP1RKP/R3N3 b - - 0 21`

Game (full game at ply): http://localhost:5173/analysis?game_id=681407&ply=41

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3r1k1/p1p2ppp/3b4/8/1P4b1/8/1BPP1RKP/R3N3%20b%20-%20-%200%2021

#### Case 72 — PIN (missed, depth 4)

Moves (SAN): `36... g4 37. Bh6+ Kg8 38. Rg7+ Kh8 39. Rd7 Re2 40. Be3 Rb5 41. Kf4 Re1 42. d4`

FEN (line start): `4rk2/3R4/5p2/6pp/7P/1r1PB1K1/3P4/8 b - - 0 36`

Game (full game at ply): http://localhost:5173/analysis?game_id=681407&ply=71

FEN (free-play from line start): http://localhost:5173/analysis?fen=4rk2/3R4/5p2/6pp/7P/1r1PB1K1/3P4/8%20b%20-%20-%200%2036

#### Case 73 — CLEARANCE (allowed, depth 6)

Moves (SAN): `9. Bxf6 Bxf6 10. Ne2 Ne6 11. g3 Be7 12. Bg2 Bd6`

FEN (line start): `r1bq1rk1/ppppbpp1/5n1p/3Np3/2PnP2B/3P3P/PP3PP1/R2QKBNR w - - 1 9`

Game (full game at ply): http://localhost:5173/analysis?game_id=681408&ply=15

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1bq1rk1/ppppbpp1/5n1p/3Np3/2PnP2B/3P3P/PP3PP1/R2QKBNR%20w%20-%20-%201%209

#### Case 74 — FORK (missed, depth 6)

Moves (SAN): `8... g5 9. b4 Nxd5 10. bxc5 Nb4 11. Bg3 Nbc2+ 12. Kd2 Nxa1 13. Nf3 Nac2 14. Bxe5`

FEN (line start): `r1bq1rk1/pppp1pp1/5n1p/2bNp3/2PnP2B/3P3P/PP3PP1/R2QKBNR b - - 0 8`

Game (full game at ply): http://localhost:5173/analysis?game_id=681408&ply=15

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1bq1rk1/pppp1pp1/5n1p/2bNp3/2PnP2B/3P3P/PP3PP1/R2QKBNR%20b%20-%20-%200%208

#### Case 75 — PROMOTION (allowed, depth 10)

Moves (SAN): `44. h4 Kd6 45. h5 a5 46. a4 f3 47. h6 Ke6 48. h7 Kd6 49. h8=Q Ke6`

FEN (line start): `8/p7/4k3/5R2/5pP1/1P5P/P4K2/8 w - - 1 44`

Game (full game at ply): http://localhost:5173/analysis?game_id=681408&ply=85

FEN (free-play from line start): http://localhost:5173/analysis?fen=8/p7/4k3/5R2/5pP1/1P5P/P4K2/8%20w%20-%20-%201%2044

#### Case 76 — FORK (missed, depth 8)

Moves (SAN): `17. dxc5`

FEN (line start): `r1b1k2r/pp3ppp/n3p3/2p1N3/3P4/2B3P1/PPP3QP/2K5 w - - 0 17`

Game (full game at ply): http://localhost:5173/analysis?game_id=681410&ply=32

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1b1k2r/pp3ppp/n3p3/2p1N3/3P4/2B3P1/PPP3QP/2K5%20w%20-%20-%200%2017

#### Case 77 — CLEARANCE (allowed, depth 10)

Moves (SAN): `6. Nxe5 f6 7. Nd3 Nc6 8. Nd2 Bf5 9. a3`

FEN (line start): `r1bnkbnr/ppp2ppp/8/4p3/8/4PN2/PPP2PPP/RNB1KB1R w - - 0 6`

Game (full game at ply): http://localhost:5173/analysis?game_id=681411&ply=9

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1bnkbnr/ppp2ppp/8/4p3/8/4PN2/PPP2PPP/RNB1KB1R%20w%20-%20-%200%206

#### Case 78 — CLEARANCE (allowed, depth 2)

Moves (SAN): `10... e6 11. Bxc4 Bc5 12. Nc3 Nge7 13. Rc1 Rd7 14. Ke1 Bxf2+ 15. Ke2 Rhd8 16. Bf4`

FEN (line start): `2kr1bnr/pp2pppp/2n5/8/2p1P3/5P2/PP1B1P1P/RN1K1B1R b - - 1 10`

Game (full game at ply): http://localhost:5173/analysis?game_id=681412&ply=18

FEN (free-play from line start): http://localhost:5173/analysis?fen=2kr1bnr/pp2pppp/2n5/8/2p1P3/5P2/PP1B1P1P/RN1K1B1R%20b%20-%20-%201%2010

#### Case 79 — PIN (allowed, depth 0)

Moves (SAN): `14... Nxb4 15. Rc1 Nbxd5 16. Bxd5+ Kb8 17. Ke2 Nxd5 18. exd5 Rxd5 19. Rhd1 Rxd1 20. Rxd1`

FEN (line start): `2k4r/pp1r1ppp/2n2n2/3Np3/1BB1P3/5P2/PP3P1P/R2K3R b - - 0 14`

Game (full game at ply): http://localhost:5173/analysis?game_id=681412&ply=26

FEN (free-play from line start): http://localhost:5173/analysis?fen=2k4r/pp1r1ppp/2n2n2/3Np3/1BB1P3/5P2/PP3P1P/R2K3R%20b%20-%20-%200%2014

#### Case 80 — DISCOVERED_ATTACK (missed, depth 1)

Moves (SAN): `22... Bh3 23. Rxh3 Qxf7 24. Kf2 Rg8 25. Qh2 d5 26. Ke2 Rg7 27. Rh4 dxe4 28. fxe4`

FEN (line start): `r3r2k/ppqb1B1p/2pp2p1/8/4P3/3PPP2/PPP3QR/5RK1 b - - 0 22`

Game (full game at ply): http://localhost:5173/analysis?game_id=681414&ply=43

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3r2k/ppqb1B1p/2pp2p1/8/4P3/3PPP2/PPP3QR/5RK1%20b%20-%20-%200%2022

#### Case 81 — CAPTURING_DEFENDER (allowed, depth 2)

Moves (SAN): `11... Nxd4 12. Qd3 Bxe5 13. f4 Ndc6 14. fxe5 h6 15. Bh4`

FEN (line start): `r2qk2r/ppb1nppp/2n1p3/2PpN1B1/3P4/8/PP2QPPP/RN3RK1 b - - 1 11`

Game (full game at ply): http://localhost:5173/analysis?game_id=681415&ply=20

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qk2r/ppb1nppp/2n1p3/2PpN1B1/3P4/8/PP2QPPP/RN3RK1%20b%20-%20-%201%2011

#### Case 82 — FORK (missed, depth 0)

Moves (SAN): `25. Qxf6+ Kg8 26. h4 Nab4 27. hxg5 Qf7 28. Qe6 Qxe6 29. fxe6 hxg5 30. Bxg5 e4`

FEN (line start): `r3qk1r/ppb5/2n2pQp/2PppPp1/8/4BN2/nP4PP/4RRK1 w - - 0 25`

Game (full game at ply): http://localhost:5173/analysis?game_id=681415&ply=48

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3qk1r/ppb5/2n2pQp/2PppPp1/8/4BN2/nP4PP/4RRK1%20w%20-%20-%200%2025

#### Case 83 — PIN (allowed, depth 0)

Moves (SAN): `16... Bxh4`

FEN (line start): `rn2k1r1/1pp1bp2/p2p4/3Pp3/2B1P2N/2N4b/PPP3P1/R1B2RK1 b - - 0 16`

Game (full game at ply): http://localhost:5173/analysis?game_id=681416&ply=30

FEN (free-play from line start): http://localhost:5173/analysis?fen=rn2k1r1/1pp1bp2/p2p4/3Pp3/2B1P2N/2N4b/PPP3P1/R1B2RK1%20b%20-%20-%200%2016

#### Case 84 — CLEARANCE (missed, depth 2)

Moves (SAN): `16. Kh2 Bxg2 17. Rg1 h3 18. Bf1 Nd7 19. Bxg2 hxg2 20. Rxg2 Rf8 21. Bg5 Bxg5`

FEN (line start): `rn2k1r1/1pp1bp2/p2p4/3Pp3/2B1P2p/2N2N1b/PPP3P1/R1B2RK1 w - - 0 16`

Game (full game at ply): http://localhost:5173/analysis?game_id=681416&ply=30

FEN (free-play from line start): http://localhost:5173/analysis?fen=rn2k1r1/1pp1bp2/p2p4/3Pp3/2B1P2p/2N2N1b/PPP3P1/R1B2RK1%20w%20-%20-%200%2016

#### Case 85 — HANGING_PIECE (allowed, depth 0)

Moves (SAN): `27... fxg5 28. Nf2 g4 29. Nxg4 Rdg8 30. Rg3 Rxh3+ 31. Rxh3 Rxg4 32. Rh8+ Ka7 33. Kh1`

FEN (line start): `1k1r3r/1pp5/p2p1p2/3Pp1R1/4Pn2/5R1B/PPP4K/3N4 b - - 1 27`

Game (full game at ply): http://localhost:5173/analysis?game_id=681416&ply=52

FEN (free-play from line start): http://localhost:5173/analysis?fen=1k1r3r/1pp5/p2p1p2/3Pp1R1/4Pn2/5R1B/PPP4K/3N4%20b%20-%20-%201%2027

#### Case 86 — CLEARANCE (allowed, depth 10)

Moves (SAN): `16... Rxe1+ 17. Rxe1 Nxd6 18. Bd5 c6 19. Bb3 Kg7 20. Rd1 Qe7 21. g4 Rd8 22. h4`

FEN (line start): `r2qr1k1/ppp2p1p/3P2p1/5n2/2B5/2P2Q2/P4PPP/3RR1K1 b - - 1 16`

Game (full game at ply): http://localhost:5173/analysis?game_id=681419&ply=30

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qr1k1/ppp2p1p/3P2p1/5n2/2B5/2P2Q2/P4PPP/3RR1K1%20b%20-%20-%201%2016

#### Case 87 — CLEARANCE (missed, depth 4)

Moves (SAN): `19. c4 Rd8 20. g3 Qd1 21. Qg2 Qc1 22. f4 Qxc4 23. Qf2 Rc1 24. g4 Qd4`

FEN (line start): `r5k1/ppp2p1p/3q2p1/8/8/2P2Q2/P4PPP/4rBK1 w - - 0 19`

Game (full game at ply): http://localhost:5173/analysis?game_id=681419&ply=36

FEN (free-play from line start): http://localhost:5173/analysis?fen=r5k1/ppp2p1p/3q2p1/8/8/2P2Q2/P4PPP/4rBK1%20w%20-%20-%200%2019

#### Case 88 — SACRIFICE (missed, depth 8)

Moves (SAN): `21. Qa6 Rd8 22. f3 Rd3 23. Qa8+ Kg7 24. Kf2 Rxf1+ 25. Kg3 Qe1+ 26. Kh3 h5`

FEN (line start): `5rk1/Q1p2p1p/6p1/8/8/2P5/P4PPP/3qrBK1 w - - 0 21`

Game (full game at ply): http://localhost:5173/analysis?game_id=681419&ply=40

FEN (free-play from line start): http://localhost:5173/analysis?fen=5rk1/Q1p2p1p/6p1/8/8/2P5/P4PPP/3qrBK1%20w%20-%20-%200%2021

#### Case 89 — MATE (allowed, depth 8)

Moves (SAN): `33... Rxc3+ 34. Kf2 Ra1 35. Ke2 Ra2+ 36. Kd1 Rxh3 37. g5 Rh1#`

FEN (line start): `6k1/7p/6p1/8/2r3P1/2P2K1P/8/4r3 b - - 0 33`

Game (full game at ply): http://localhost:5173/analysis?game_id=681419&ply=64

FEN (free-play from line start): http://localhost:5173/analysis?fen=6k1/7p/6p1/8/2r3P1/2P2K1P/8/4r3%20b%20-%20-%200%2033

#### Case 90 — HANGING_PIECE (allowed, depth 0)

Moves (SAN): `16... Kxh7 17. Qg4 Ng6 18. f5 Ne5 19. Qh3+ Kg8 20. f6 Ng6 21. fxg7 Qh4 22. Qf5`

FEN (line start): `r2qr1k1/2p1nppB/p2p4/2bP4/1p3P2/1P6/PBP3PP/R2Q1R1K b - - 0 16`

Game (full game at ply): http://localhost:5173/analysis?game_id=681420&ply=30

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qr1k1/2p1nppB/p2p4/2bP4/1p3P2/1P6/PBP3PP/R2Q1R1K%20b%20-%20-%200%2016

#### Case 91 — CAPTURING_DEFENDER (missed, depth 6)

Moves (SAN): `19... Rd8 20. Qf5 Qd6 21. Qc5 Qxc5 22. Bxc5 Rxc2 23. Bxa7 Rxb2 24. a4 Bf6 25. Be3`

FEN (line start): `r5k1/p1p2ppp/6q1/3Q4/6Pb/3PB2P/PPP1rP2/R4RK1 b - - 0 19`

Game (full game at ply): http://localhost:5173/analysis?game_id=681421&ply=37

FEN (free-play from line start): http://localhost:5173/analysis?fen=r5k1/p1p2ppp/6q1/3Q4/6Pb/3PB2P/PPP1rP2/R4RK1%20b%20-%20-%200%2019

#### Case 92 — FORK (missed, depth 0)

Moves (SAN): `18. Bxe7+ Nxe7 19. Bc2 Rfd6 20. h3 Bd7 21. Re3 Ng8 22. Rae1 Nf6 23. Re7 Be8`

FEN (line start): `3r1k2/p1p1n1pB/1pn2r2/2B3N1/2P3b1/P1P5/5PPP/R3R1K1 w - - 0 18`

Game (full game at ply): http://localhost:5173/analysis?game_id=681422&ply=34

FEN (free-play from line start): http://localhost:5173/analysis?fen=3r1k2/p1p1n1pB/1pn2r2/2B3N1/2P3b1/P1P5/5PPP/R3R1K1%20w%20-%20-%200%2018

#### Case 93 — TRAPPED_PIECE (allowed, depth 6)

Moves (SAN): `8... Nxc3 9. Qc1 Ba3 10. Qxb2 Bxb2 11. Rd1 Nxd1 12. Kxd1 Ba3 13. Nb1 Bb4 14. a3`

FEN (line start): `r1b1kb1r/pppp1ppp/2n5/3nP3/5B2/2P2NP1/Pq1NPPBP/R2QK2R b - - 1 8`

Game (full game at ply): http://localhost:5173/analysis?game_id=681423&ply=14

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1b1kb1r/pppp1ppp/2n5/3nP3/5B2/2P2NP1/Pq1NPPBP/R2QK2R%20b%20-%20-%201%208

#### Case 94 — CLEARANCE (missed, depth 6)

Moves (SAN): `10. Rb1 Qxa2 11. Ra1 Qb2 12. Nc4 Qb5 13. Qd3 Be7 14. Rfb1 Nxf4 15. gxf4 Qc5`

FEN (line start): `r1b2rk1/pppp1ppp/2n5/2bnP3/5B2/2P2NP1/Pq1NPPBP/R2Q1RK1 w - - 0 10`

Game (full game at ply): http://localhost:5173/analysis?game_id=681423&ply=18

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1b2rk1/pppp1ppp/2n5/2bnP3/5B2/2P2NP1/Pq1NPPBP/R2Q1RK1%20w%20-%20-%200%2010

#### Case 95 — DISCOVERED_CHECK (allowed, depth 2)

Moves (SAN): `27... Bxe3 28. fxe3 Ne4+ 29. Kf3 Nxc3 30. Be6 Rxh2 31. e4 Re2 32. Bd5 Re1 33. Kf4`

FEN (line start): `5k2/p6p/6p1/2bB4/8/2P1R3/Pr1n1PKP/8 b - - 1 27`

Game (full game at ply): http://localhost:5173/analysis?game_id=681423&ply=52

FEN (free-play from line start): http://localhost:5173/analysis?fen=5k2/p6p/6p1/2bB4/8/2P1R3/Pr1n1PKP/8%20b%20-%20-%201%2027

#### Case 96 — CLEARANCE (missed, depth 6)

Moves (SAN): `14... Re8 15. h3 Bd7 16. g4 Nc6 17. Rd1 Rad8 18. Be2 Be7 19. Nf5 Bxf5 20. gxf5`

FEN (line start): `rn3rk1/ppp2ppp/3b4/8/3Rp1bN/2P5/PBP3PP/2K2B1R b - - 0 14`

Game (full game at ply): http://localhost:5173/analysis?game_id=681425&ply=27

FEN (free-play from line start): http://localhost:5173/analysis?fen=rn3rk1/ppp2ppp/3b4/8/3Rp1bN/2P5/PBP3PP/2K2B1R%20b%20-%20-%200%2014

#### Case 97 — FORK (missed, depth 2)

Moves (SAN): `19... Bf4+ 20. Kb1 Be2 21. Rb4 Bxf1 22. a3 Bg5 23. g3 Bxh4 24. gxh4 e3 25. c4`

FEN (line start): `3r1r1k/pBp1n1pp/3b4/5p2/2R1p1bN/2P5/PBP3PP/2K2R2 b - - 0 19`

Game (full game at ply): http://localhost:5173/analysis?game_id=681425&ply=37

FEN (free-play from line start): http://localhost:5173/analysis?fen=3r1r1k/pBp1n1pp/3b4/5p2/2R1p1bN/2P5/PBP3PP/2K2R2%20b%20-%20-%200%2019

#### Case 98 — FORK (allowed, depth 0)

Moves (SAN): `20... Qe5 21. Qe1 Nxe3 22. Rc1 f5 23. Nb6 f4 24. Nf1 Nxf1 25. Qxf1 Be6 26. Qf3`

FEN (line start): `N1b2rk1/1p2pp2/p2p2pp/7q/4P1n1/PP2P1NP/2PQ2P1/R5K1 b - - 0 20`

Game (full game at ply): http://localhost:5173/analysis?game_id=681427&ply=38

FEN (free-play from line start): http://localhost:5173/analysis?fen=N1b2rk1/1p2pp2/p2p2pp/7q/4P1n1/PP2P1NP/2PQ2P1/R5K1%20b%20-%20-%200%2020

#### Case 99 — FORK (allowed, depth 0)

Moves (SAN): `12. Qxd5+ Kh8 13. Qxe4 Rxf2 14. Kxf2 Qf8+ 15. Ke1 Re8 16. Qd5 Bxe3 17. Qxd7 Bxg1+`

FEN (line start): `r2q1rk1/pppb2pp/2n5/1Bbp4/4n3/2P1P3/PP3BPP/RN1QK1NR w - - 0 12`

Game (full game at ply): http://localhost:5173/analysis?game_id=681428&ply=21

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2q1rk1/pppb2pp/2n5/1Bbp4/4n3/2P1P3/PP3BPP/RN1QK1NR%20w%20-%20-%200%2012

#### Case 100 — ATTRACTION (missed, depth 4)

Moves (SAN): `11... Bg4 12. Nf3 Nxe4 13. Nbd2 Nxf2 14. Kxf2 Qh4+ 15. Ke2 Bxe3 16. Qe1 Qh6 17. Kd1`

FEN (line start): `r2q1rk1/pppb2pp/2n2n2/1Bbp4/4P3/2P1P3/PP3BPP/RN1QK1NR b - - 0 11`

Game (full game at ply): http://localhost:5173/analysis?game_id=681428&ply=21

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2q1rk1/pppb2pp/2n2n2/1Bbp4/4P3/2P1P3/PP3BPP/RN1QK1NR%20b%20-%20-%200%2011

#### Case 101 — CLEARANCE (allowed, depth 8)

Moves (SAN): `23. cxd5 Re5 24. Rg1 Rxh3+ 25. Kg2 Rg5+ 26. Kf1 Rf5 27. Rg3 Rxg3 28. fxg3 Rxf3+`

FEN (line start): `4r1k1/pp1b1ppp/2p4r/3p4/PPPp4/1B1P1P1P/5P1K/3R1R2 w - - 1 23`

Game (full game at ply): http://localhost:5173/analysis?game_id=681430&ply=43

FEN (free-play from line start): http://localhost:5173/analysis?fen=4r1k1/pp1b1ppp/2p4r/3p4/PPPp4/1B1P1P1P/5P1K/3R1R2%20w%20-%20-%201%2023

#### Case 102 — DISCOVERED_ATTACK (missed, depth 3)

Moves (UCI — SAN unavailable): `d4c3 d3d4 e6h6 a4a5 d7h3 f1e1 h3d7 h2g3 h6h3 g3f4 g7g5 f4g5`

FEN (line start): `4r1k1/pp1b1ppp/2p1r3/3p4/PPPp4/1B1P1P1P/5P1K/3R1R2 b - - 0 22`

Game (full game at ply): http://localhost:5173/analysis?game_id=681430&ply=43

FEN (free-play from line start): http://localhost:5173/analysis?fen=4r1k1/pp1b1ppp/2p1r3/3p4/PPPp4/1B1P1P1P/5P1K/3R1R2%20b%20-%20-%200%2022

#### Case 103 — DEFLECTION (missed, depth 10)

Moves (SAN): `23... Re5 24. Rfe1 Rg6+ 25. Kh2 Rh5 26. Re8+ Bxe8 27. Rg1 Rxh3+ 28. Kxh3 Rxg1 29. cxd5`

FEN (line start): `4r1k1/pp1b1ppp/2p4r/3p4/PPPp4/1B1P1P1P/5P2/3R1RK1 b - - 0 23`

Game (full game at ply): http://localhost:5173/analysis?game_id=681430&ply=45

FEN (free-play from line start): http://localhost:5173/analysis?fen=4r1k1/pp1b1ppp/2p4r/3p4/PPPp4/1B1P1P1P/5P2/3R1RK1%20b%20-%20-%200%2023

#### Case 104 — PROMOTION (allowed, depth 2)

Moves (SAN): `46. bxa7 Kf4 47. a8=Q Ke3 48. Qf3+ Kd2 49. Qxf5 Kd1 50. a6 Kc2 51. Qe4 Kb1`

FEN (line start): `8/p7/1P6/P4p2/3p2k1/3P2p1/6K1/8 w - - 1 46`

Game (full game at ply): http://localhost:5173/analysis?game_id=681430&ply=89

FEN (free-play from line start): http://localhost:5173/analysis?fen=8/p7/1P6/P4p2/3p2k1/3P2p1/6K1/8%20w%20-%20-%201%2046

#### Case 105 — CLEARANCE (missed, depth 4)

Moves (SAN): `6... h6 7. d4 g5 8. h4 Bg7 9. Qd3 Bb7 10. e5 Qe7 11. hxg5 hxg5 12. Rxh8`

FEN (line start): `r1bqkbnr/2pp1ppp/p1n5/1p6/4Pp2/1B3N2/PPPP2PP/RNBQK2R b - - 0 6`

Game (full game at ply): http://localhost:5173/analysis?game_id=681431&ply=11

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1bqkbnr/2pp1ppp/p1n5/1p6/4Pp2/1B3N2/PPPP2PP/RNBQK2R%20b%20-%20-%200%206

#### Case 106 — FORK (allowed, depth 0)

Moves (SAN): `19. Rxd7 Qf6 20. Qxf6 Nxf6 21. Rxe8+ Rxe8 22. Rxb7 Rd8 23. Rc7 h5 24. b4 cxb3`

FEN (line start): `2rqr1k1/1b1p1ppp/p7/8/B1p1nQ2/P1N5/1PP3PP/2KRR3 w - - 0 19`

Game (full game at ply): http://localhost:5173/analysis?game_id=681431&ply=35

FEN (free-play from line start): http://localhost:5173/analysis?fen=2rqr1k1/1b1p1ppp/p7/8/B1p1nQ2/P1N5/1PP3PP/2KRR3%20w%20-%20-%200%2019

#### Case 107 — CLEARANCE (allowed, depth 6)

Moves (SAN): `7... Qe7 8. Bg5 Bc5 9. Qd3 Bxf2+ 10. Kd1 Qc5 11. Bxf6 gxf6 12. Rf1 c6 13. e5`

FEN (line start): `r1bqk2r/pppp1ppp/3b1n2/8/2BQP3/2N5/PPP2PPP/R1B1K2R b - - 1 7`

Game (full game at ply): http://localhost:5173/analysis?game_id=681432&ply=12

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1bqk2r/pppp1ppp/3b1n2/8/2BQP3/2N5/PPP2PPP/R1B1K2R%20b%20-%20-%201%207

#### Case 108 — CLEARANCE (missed, depth 2)

Moves (SAN): `15. Ng5 Nc6 16. Bf3 Qc4 17. Rc1`

FEN (line start): `r1b1k2r/ppR2ppp/4p3/n2qP3/3P4/5N2/p2QBPPP/5RK1 w - - 0 15`

Game (full game at ply): http://localhost:5173/analysis?game_id=681433&ply=28

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1b1k2r/ppR2ppp/4p3/n2qP3/3P4/5N2/p2QBPPP/5RK1%20w%20-%20-%200%2015

#### Case 109 — CLEARANCE (allowed, depth 6)

Moves (SAN): `4... Qxd4 5. Nd2 Qf6 6. a3 e5 7. b4 Bd6 8. Ngf3 Nge7`

FEN (line start): `r1bqkbnr/ppp1pppp/2n5/8/2BPP3/8/PP3PPP/RNBQK1NR b - - 0 4`

Game (full game at ply): http://localhost:5173/analysis?game_id=681434&ply=6

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1bqkbnr/ppp1pppp/2n5/8/2BPP3/8/PP3PPP/RNBQK1NR%20b%20-%20-%200%204

#### Case 110 — SACRIFICE (allowed, depth 10)

Moves (SAN): `10... Nxc3 11. Bxc3 Be7 12. Bxg7 Rg8 13. Bc3 a6 14. Ba4 Qc7 15. Qxe6 Rg6 16. Qd5`

FEN (line start): `r1b1kb1r/pp1n2pp/1q1pp3/1Bp5/4n3/1PN2N2/P1PBQPPP/R3K2R b - - 1 10`

Game (full game at ply): http://localhost:5173/analysis?game_id=681436&ply=18

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1b1kb1r/pp1n2pp/1q1pp3/1Bp5/4n3/1PN2N2/P1PBQPPP/R3K2R%20b%20-%20-%201%2010

#### Case 111 — PIN (allowed, depth 2)

Moves (SAN): `14... axb5 15. Qe6+ Be7 16. b4 Qd8 17. Ng5 Rf8`

FEN (line start): `r1b1kb1r/1p1n2pp/p2p4/qB2p3/2Q5/PPN1BN2/2P2PPP/R3K2R b - - 0 14`

Game (full game at ply): http://localhost:5173/analysis?game_id=681436&ply=26

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1b1kb1r/1p1n2pp/p2p4/qB2p3/2Q5/PPN1BN2/2P2PPP/R3K2R%20b%20-%20-%200%2014

#### Case 112 — PIN (missed, depth 8)

Moves (SAN): `18. Qb3 Qc6`

FEN (line start): `r1b1k2r/1p2b1pp/q2pQn2/1p2p1B1/1P6/P1N2N2/2P2PPP/R3K2R w - - 0 18`

Game (full game at ply): http://localhost:5173/analysis?game_id=681436&ply=34

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1b1k2r/1p2b1pp/q2pQn2/1p2p1B1/1P6/P1N2N2/2P2PPP/R3K2R%20w%20-%20-%200%2018

#### Case 113 — CLEARANCE (missed, depth 8)

Moves (SAN): `11... Bd6 12. Qg5 h6 13. Qh4 Bf5 14. Bb3 Nd7 15. Qh5 Qf6 16. Ne4 Bxe4 17. Rxe4`

FEN (line start): `r1bq1rk1/pp2bppp/2p2n2/4Q3/2B5/2N5/PPP2PPP/R1B1R1K1 b - - 0 11`

Game (full game at ply): http://localhost:5173/analysis?game_id=681439&ply=21

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1bq1rk1/pp2bppp/2p2n2/4Q3/2B5/2N5/PPP2PPP/R1B1R1K1%20b%20-%20-%200%2011

#### Case 114 — MATE (allowed, depth 10)

Moves (SAN): `48. Rh5+ Kg6 49. Rxh8 Kf7 50. a7 g5 51. f5 Ke7 52. a8=Q Kd7 53. Rh7#`

FEN (line start): `7r/6p1/P6k/6R1/4NPP1/6K1/8/8 w - - 1 48`

Game (full game at ply): http://localhost:5173/analysis?game_id=681439&ply=93

FEN (free-play from line start): http://localhost:5173/analysis?fen=7r/6p1/P6k/6R1/4NPP1/6K1/8/8%20w%20-%20-%201%2048

#### Case 115 — DISCOVERED_CHECK (missed, depth 0)

Moves (SAN): `49... Kg7+ 50. Kg3 Rb8 51. Rxg6+ Kf8 52. Rc6 Ra8 53. Kf4 Ke7 54. f6+ Kd7 55. Rb6`

FEN (line start): `7r/8/P5pk/5PR1/4N1PK/8/8/8 b - - 0 49`

Game (full game at ply): http://localhost:5173/analysis?game_id=681439&ply=97

FEN (free-play from line start): http://localhost:5173/analysis?fen=7r/8/P5pk/5PR1/4N1PK/8/8/8%20b%20-%20-%200%2049

#### Case 116 — FORK (allowed, depth 4)

Moves (SAN): `16. b5 Rc8 17. Nc4 cxb5 18. Nb6+ Ke6 19. Rxb5 Rc5 20. Bb2 Qd3 21. Rb3 Qa6`

FEN (line start): `3r1b1r/1p1k1ppp/2pp1n2/8/QP6/2q5/P2N1PPP/1RB2RK1 w - - 1 16`

Game (full game at ply): http://localhost:5173/analysis?game_id=681440&ply=29

FEN (free-play from line start): http://localhost:5173/analysis?fen=3r1b1r/1p1k1ppp/2pp1n2/8/QP6/2q5/P2N1PPP/1RB2RK1%20w%20-%20-%201%2016

#### Case 117 — CLEARANCE (missed, depth 2)

Moves (SAN): `21... d5 22. Nf3 Bd6 23. Bb2 Qc4 24. Ne5+ Bxe5 25. Qxc4 Bxh2+ 26. Kxh2 dxc4 27. Be5`

FEN (line start): `3r1b1r/1Rnk3p/2pp2p1/5p2/Q7/2q5/P2N1PPP/2B1R1K1 b - - 0 21`

Game (full game at ply): http://localhost:5173/analysis?game_id=681440&ply=41

FEN (free-play from line start): http://localhost:5173/analysis?fen=3r1b1r/1Rnk3p/2pp2p1/5p2/Q7/2q5/P2N1PPP/2B1R1K1%20b%20-%20-%200%2021

#### Case 118 — SACRIFICE (missed, depth 6)

Moves (SAN): `7... Qg5 8. d4 Qxg2 9. Rf1 Bd6 10. Nxc6 a6 11. Ba4`

FEN (line start): `r1bqkb1r/ppp2ppp/2n5/1B2N3/4p3/8/PPPP1PPP/R1BQK2R b - - 0 7`

Game (full game at ply): http://localhost:5173/analysis?game_id=681443&ply=13

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1bqkb1r/ppp2ppp/2n5/1B2N3/4p3/8/PPPP1PPP/R1BQK2R%20b%20-%20-%200%207

#### Case 119 — TRAPPED_PIECE (missed, depth 8)

Moves (UCI — SAN unavailable): `e8c8 e1g1 f8d6 d2d4 e4d3 e2d3 a7a6 b5c4 f6h8 d3d5 c6e5 c4e2`

FEN (line start): `r3kb1N/pppb3p/2n2qp1/1B6/4p3/8/PPPPQPPP/R1B1K2R b - - 0 10`

Game (full game at ply): http://localhost:5173/analysis?game_id=681443&ply=19

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3kb1N/pppb3p/2n2qp1/1B6/4p3/8/PPPPQPPP/R1B1K2R%20b%20-%20-%200%2010

#### Case 120 — PIN (missed, depth 0)

Moves (SAN): `15... Nb4`

FEN (line start): `2kr4/ppp1b2p/2n3p1/1B1Pqb2/Q7/4B3/PPP2PPP/R3K2R b - - 0 15`

Game (full game at ply): http://localhost:5173/analysis?game_id=681443&ply=29

FEN (free-play from line start): http://localhost:5173/analysis?fen=2kr4/ppp1b2p/2n3p1/1B1Pqb2/Q7/4B3/PPP2PPP/R3K2R%20b%20-%20-%200%2015

#### Case 121 — INTERMEZZO (allowed, depth 8)

Moves (SAN): `20... Bxa1 21. Be3 b5 22. h3 Rc8 23. cxb5 Qe5 24. Nf4 axb5 25. a4 Rc3 26. Nf3`

FEN (line start): `r3qrk1/1p6/p2p2p1/3N1bNp/2PB3Q/8/Pb3PPP/R5K1 b - - 1 20`

Game (full game at ply): http://localhost:5173/analysis?game_id=681444&ply=38

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3qrk1/1p6/p2p2p1/3N1bNp/2PB3Q/8/Pb3PPP/R5K1%20b%20-%20-%201%2020

#### Case 122 — CLEARANCE (missed, depth 6)

Moves (SAN): `20. Rd1 Qe5 21. h3 Rae8 22. c5 dxc5 23. Qc4 Be6 24. Qxc5 Bxd5 25. Rxd5 Qc3`

FEN (line start): `r3qrk1/1p6/p2p2p1/3N1bNp/2P4Q/4B3/Pb3PPP/R5K1 w - - 0 20`

Game (full game at ply): http://localhost:5173/analysis?game_id=681444&ply=38

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3qrk1/1p6/p2p2p1/3N1bNp/2P4Q/4B3/Pb3PPP/R5K1%20w%20-%20-%200%2020

#### Case 123 — CLEARANCE (missed, depth 6)

Moves (SAN): `21. Be3 Rc8 22. h3 b5 23. cxb5 axb5 24. Qb4 Rc4 25. Qb3 Kh8 26. Bd2 Be5`

FEN (line start): `r3qrk1/1p6/p2p2p1/3N1bNp/2PB3Q/8/P4PPP/b5K1 w - - 0 21`

Game (full game at ply): http://localhost:5173/analysis?game_id=681444&ply=40

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3qrk1/1p6/p2p2p1/3N1bNp/2PB3Q/8/P4PPP/b5K1%20w%20-%20-%200%2021

#### Case 124 — CLEARANCE (allowed, depth 6)

Moves (SAN): `9... d4 10. Nb1 Nxe4 11. Nd2 Ndf6 12. Bd3 Bf5 13. Ngf3`

FEN (line start): `r1b1k2r/pp1n1p1p/2p2n2/2bp4/4P3/2N4P/PP3PP1/R1B1KBNR b - - 0 9`

Game (full game at ply): http://localhost:5173/analysis?game_id=681445&ply=16

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1b1k2r/pp1n1p1p/2p2n2/2bp4/4P3/2N4P/PP3PP1/R1B1KBNR%20b%20-%20-%200%209

#### Case 125 — CLEARANCE (allowed, depth 6)

Moves (SAN): `7... Nxd5 8. Bd2 Bb4 9. Qc2 b6`

FEN (line start): `r1bqkb1r/ppp2ppp/4pn2/n2PP3/2p5/2N2N2/PP3PPP/R1BQKB1R b - - 0 7`

Game (full game at ply): http://localhost:5173/analysis?game_id=681446&ply=12

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1bqkb1r/ppp2ppp/4pn2/n2PP3/2p5/2N2N2/PP3PPP/R1BQKB1R%20b%20-%20-%200%207

#### Case 126 — CLEARANCE (allowed, depth 10)

Moves (SAN): `18... Kd7 19. Bb5+ Nxb5 20. Rxe4 Nd6 21. Ra4 Re8 22. Nf3 Ne4 23. Rxa7 Bc5 24. Bf4`

FEN (line start): `r3kbr1/p1p4p/1p3p2/3P4/3nb2N/8/P2BBPPP/R3R1K1 b - - 1 18`

Game (full game at ply): http://localhost:5173/analysis?game_id=681446&ply=34

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3kbr1/p1p4p/1p3p2/3P4/3nb2N/8/P2BBPPP/R3R1K1%20b%20-%20-%201%2018

#### Case 127 — DEFLECTION (missed, depth 6)

Moves (SAN): `18. Nxd4 Rxg2+ 19. Kf1 Kf7 20. Bh5+ Bg6 21. Kxg2 Bxh5 22. Rac1 Rc8 23. Kg3 Bc5`

FEN (line start): `r3kbr1/p1p4p/1p3p2/3P4/3nb3/5N2/P2BBPPP/R3R1K1 w - - 0 18`

Game (full game at ply): http://localhost:5173/analysis?game_id=681446&ply=34

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3kbr1/p1p4p/1p3p2/3P4/3nb3/5N2/P2BBPPP/R3R1K1%20w%20-%20-%200%2018

#### Case 128 — DISCOVERED_CHECK (missed, depth 6)

Moves (SAN): `29. d6+ cxd6 30. Bf4 Ra8 31. Bxd6+ Ke8 32. Bxa2+ Kd7 33. Be6+ Kc6 34. Rc1+ Kb6`

FEN (line start): `4rb2/p1p1kN1p/4Bp1B/1p1P4/8/7P/r4PP1/4R1K1 w - - 0 29`

Game (full game at ply): http://localhost:5173/analysis?game_id=681446&ply=56

FEN (free-play from line start): http://localhost:5173/analysis?fen=4rb2/p1p1kN1p/4Bp1B/1p1P4/8/7P/r4PP1/4R1K1%20w%20-%20-%200%2029

#### Case 129 — SACRIFICE (allowed, depth 10)

Moves (SAN): `33... Rxg3 34. Kxg3 b3 35. Bf5 Re1 36. Ng4 b2 37. Nxf6 a5 38. Nxh7+ Kg7 39. Ng5`

FEN (line start): `4rk2/p1p4p/4Bp1N/3P4/1p6/r5RP/5PPK/8 b - - 1 33`

Game (full game at ply): http://localhost:5173/analysis?game_id=681446&ply=64

FEN (free-play from line start): http://localhost:5173/analysis?fen=4rk2/p1p4p/4Bp1N/3P4/1p6/r5RP/5PPK/8%20b%20-%20-%201%2033

#### Case 130 — CLEARANCE (missed, depth 6)

Moves (SAN): `9... Qf5`

FEN (line start): `r1b1k2r/ppp2ppp/2n1qn2/2b3N1/2P1p3/3P3P/PP2BPP1/RNBQK2R b - - 0 9`

Game (full game at ply): http://localhost:5173/analysis?game_id=681447&ply=17

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1b1k2r/ppp2ppp/2n1qn2/2b3N1/2P1p3/3P3P/PP2BPP1/RNBQK2R%20b%20-%20-%200%209

#### Case 131 — CLEARANCE (missed, depth 6)

Moves (SAN): `13... Qh4 14. Nd5`

FEN (line start): `r1b1k2r/ppp2pp1/2n4p/2b5/2P1q3/2N4P/PP2BPP1/R1BQ1RK1 b - - 0 13`

Game (full game at ply): http://localhost:5173/analysis?game_id=681447&ply=25

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1b1k2r/ppp2pp1/2n4p/2b5/2P1q3/2N4P/PP2BPP1/R1BQ1RK1%20b%20-%20-%200%2013

#### Case 132 — CLEARANCE (allowed, depth 8)

Moves (SAN): `16. Bxf5 Qxf5 17. Re1+ Kf8 18. Qb3 b6 19. Be3 Rd8 20. Rad1 Kg8 21. Qa4 Ne5`

FEN (line start): `r3k2r/ppp2pp1/2nb2qp/3N1b2/2P5/3B3P/PP3PP1/R1BQ1RK1 w - - 1 16`

Game (full game at ply): http://localhost:5173/analysis?game_id=681447&ply=29

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3k2r/ppp2pp1/2nb2qp/3N1b2/2P5/3B3P/PP3PP1/R1BQ1RK1%20w%20-%20-%201%2016

#### Case 133 — PIN (allowed, depth 4)

Moves (SAN): `18. Re1 Qe6 19. Bf4 Nxd5 20. Bxd6`

FEN (line start): `r3k2r/ppp1npp1/3b3p/3N1q2/2P5/7P/PP2QPP1/R1B2RK1 w - - 1 18`

Game (full game at ply): http://localhost:5173/analysis?game_id=681447&ply=33

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3k2r/ppp1npp1/3b3p/3N1q2/2P5/7P/PP2QPP1/R1B2RK1%20w%20-%20-%201%2018

#### Case 134 — PROMOTION (allowed, depth 10)

Moves (SAN): `37. Qb5 Rd7 38. cxd7 Kc7 39. Qf5 Kd8 40. Qe6 Kc7 41. Qe7 Kc6 42. d8=Q Kb5`

FEN (line start): `1k1r4/pp6/2Pp4/5Q2/8/1P5P/P4PPK/8 w - - 0 37`

Game (full game at ply): http://localhost:5173/analysis?game_id=681447&ply=71

FEN (free-play from line start): http://localhost:5173/analysis?fen=1k1r4/pp6/2Pp4/5Q2/8/1P5P/P4PPK/8%20w%20-%20-%200%2037

#### Case 135 — HANGING_PIECE (allowed, depth 0)

Moves (SAN): `11... dxe4 12. Qxd8+ Kxd8`

FEN (line start): `r1bqk2r/pp3ppp/4p3/3pP3/4N3/4P3/PP1Q1PPP/R3KB1R b - - 0 11`

Game (full game at ply): http://localhost:5173/analysis?game_id=681449&ply=20

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1bqk2r/pp3ppp/4p3/3pP3/4N3/4P3/PP1Q1PPP/R3KB1R%20b%20-%20-%200%2011

#### Case 136 — CLEARANCE (allowed, depth 2)

Moves (SAN): `15... Bb7`

FEN (line start): `r1b4r/p3kppp/1p2p3/4P3/4p3/4P1P1/PP3PBP/3RK2R b - - 1 15`

Game (full game at ply): http://localhost:5173/analysis?game_id=681449&ply=28

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1b4r/p3kppp/1p2p3/4P3/4p3/4P1P1/PP3PBP/3RK2R%20b%20-%20-%201%2015

#### Case 137 — CLEARANCE (missed, depth 2)

Moves (SAN): `17. Rxd8 Rxd8 18. Rc1 f5 19. Bf1 Rd2 20. Rc7+ Rd7 21. Rxd7+ Kxd7 22. a3 Bd5`

FEN (line start): `3r3r/pb2kppp/1p2p3/4P3/4p3/4P1P1/PP3PBP/3R1RK1 w - - 0 17`

Game (full game at ply): http://localhost:5173/analysis?game_id=681449&ply=32

FEN (free-play from line start): http://localhost:5173/analysis?fen=3r3r/pb2kppp/1p2p3/4P3/4p3/4P1P1/PP3PBP/3R1RK1%20w%20-%20-%200%2017

#### Case 138 — CLEARANCE (allowed, depth 4)

Moves (SAN): `9. Nxg6 hxg6 10. d3 Nd7 11. Be3 Qb4 12. Rb1`

FEN (line start): `r3kb1r/ppp2ppp/2p2nb1/4N3/3qP1P1/2N4P/PPPP1P2/R1BQK2R w - - 1 9`

Game (full game at ply): http://localhost:5173/analysis?game_id=681450&ply=15

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3kb1r/ppp2ppp/2p2nb1/4N3/3qP1P1/2N4P/PPPP1P2/R1BQK2R%20w%20-%20-%201%209

#### Case 139 — DISCOVERED_ATTACK (missed, depth 3)

Moves (SAN): `14... Nxf3+ 15. Bxf3 Nxe4 16. dxe4 Bxg5 17. Qxd8 Bxd8 18. c5 c6 19. Nd6 b5 20. h3`

FEN (line start): `r2q1rk1/1pp1bppp/4bn2/pN2p1B1/2PnP3/3P1N2/P2QBPPP/R4RK1 b - - 0 14`

Game (full game at ply): http://localhost:5173/analysis?game_id=681451&ply=27

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2q1rk1/1pp1bppp/4bn2/pN2p1B1/2PnP3/3P1N2/P2QBPPP/R4RK1%20b%20-%20-%200%2014

#### Case 140 — PROMOTION (allowed, depth 4)

Moves (SAN): `28. Rxe1 Nxe1 29. d7 h6 30. d8=Q+ Kh7 31. Qxa5 Nc2 32. Qd2 Na1 33. Qxd4 Nb3`

FEN (line start): `6k1/1p3ppp/2pP4/p1Pb4/P2p3N/3n1P2/6PP/R3r1K1 w - - 1 28`

Game (full game at ply): http://localhost:5173/analysis?game_id=681451&ply=53

FEN (free-play from line start): http://localhost:5173/analysis?fen=6k1/1p3ppp/2pP4/p1Pb4/P2p3N/3n1P2/6PP/R3r1K1%20w%20-%20-%201%2028

#### Case 141 — MATE (allowed, depth 10)

Moves (SAN): `30. d8=Q+ Kg7 31. Qxg5+ Kf8 32. Nf5 Nxf3+ 33. gxf3 f6 34. Qg7+ Ke8 35. Qe7#`

FEN (line start): `6k1/1p1P1p1p/2p5/p1Pb2p1/P2p3N/5P2/6PP/4n1K1 w - - 0 30`

Game (full game at ply): http://localhost:5173/analysis?game_id=681451&ply=57

FEN (free-play from line start): http://localhost:5173/analysis?fen=6k1/1p1P1p1p/2p5/p1Pb2p1/P2p3N/5P2/6PP/4n1K1%20w%20-%20-%200%2030

#### Case 142 — PIN (allowed, depth 4)

Moves (SAN): `41. Qb1+ d3 42. Kg3 Ne2+ 43. Kxh3 Bc4 44. Kg2 f5 45. gxf5+ Kxf5 46. Kf2 Ke6`

FEN (line start): `8/1Q5p/2p2pk1/p1Pb4/P2p1nP1/5P1p/5K2/8 w - - 0 41`

Game (full game at ply): http://localhost:5173/analysis?game_id=681451&ply=79

FEN (free-play from line start): http://localhost:5173/analysis?fen=8/1Q5p/2p2pk1/p1Pb4/P2p1nP1/5P1p/5K2/8%20w%20-%20-%200%2041

#### Case 143 — SACRIFICE (allowed, depth 6)

Moves (UCI — SAN unavailable): `e1g1 e7d6 a2a4 f8e7 c1a3 d6e5 f1e1 e5f5 a3e7 d7d5 e7f6 c8e6`

FEN (line start): `r1b1kb1r/p1ppqppp/2p5/4N3/8/2P5/P1PP1PPP/R1BQK2R w - - 1 8`

Game (full game at ply): http://localhost:5173/analysis?game_id=681470&ply=13

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1b1kb1r/p1ppqppp/2p5/4N3/8/2P5/P1PP1PPP/R1BQK2R%20w%20-%20-%201%208

#### Case 144 — CLEARANCE (missed, depth 10)

Moves (SAN): `8... f6`

FEN (line start): `r1b1kb1r/p1ppqppp/2p5/4N3/3P4/2P5/P1P2PPP/R1BQK2R b - - 0 8`

Game (full game at ply): http://localhost:5173/analysis?game_id=681470&ply=15

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1b1kb1r/p1ppqppp/2p5/4N3/3P4/2P5/P1P2PPP/R1BQK2R%20b%20-%20-%200%208

#### Case 145 — PIN (allowed, depth 0)

Moves (SAN): `12. Re1 Be6 13. d5 Bg7 14. Bb2 Bxb2 15. Nxb2`

FEN (line start): `r1b1kb1r/p1p1qp1p/3p2p1/8/3P4/3N4/P1P2PPP/R1BQ1RK1 w - - 0 12`

Game (full game at ply): http://localhost:5173/analysis?game_id=681470&ply=21

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1b1kb1r/p1p1qp1p/3p2p1/8/3P4/3N4/P1P2PPP/R1BQ1RK1%20w%20-%20-%200%2012

#### Case 146 — SACRIFICE (missed, depth 2)

Moves (SAN): `17... Qxb2 18. Nxb2 d5 19. Qc3+ Kg8 20. Qxc7 Ba3 21. Nd3 h5 22. Kf1 Rh7 23. Qc6`

FEN (line start): `r4b1r/p1p3kp/3p2p1/8/8/3N1Q2/PBP2PPP/q3R1K1 b - - 0 17`

Game (full game at ply): http://localhost:5173/analysis?game_id=681470&ply=33

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4b1r/p1p3kp/3p2p1/8/8/3N1Q2/PBP2PPP/q3R1K1%20b%20-%20-%200%2017

#### Case 147 — HANGING_PIECE (missed, depth 0)

Moves (SAN): `62. Kxf5 Kf3 63. Ke5 Nd1 64. Kd4 Nf2 65. Ke5`

FEN (line start): `8/8/8/5qK1/8/2n1k3/8/8 w - - 0 62`

Game (full game at ply): http://localhost:5173/analysis?game_id=681504&ply=122

FEN (free-play from line start): http://localhost:5173/analysis?fen=8/8/8/5qK1/8/2n1k3/8/8%20w%20-%20-%200%2062

#### Case 148 — CLEARANCE (allowed, depth 2)

Moves (SAN): `15... Be6`

FEN (line start): `r1b1r1k1/pp2bppp/1q3p2/8/8/P1N2Q2/1P1RBPPP/4K2R b - - 1 15`

Game (full game at ply): http://localhost:5173/analysis?game_id=681508&ply=28

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1b1r1k1/pp2bppp/1q3p2/8/8/P1N2Q2/1P1RBPPP/4K2R%20b%20-%20-%201%2015

#### Case 149 — CLEARANCE (missed, depth 8)

Moves (SAN): `13. Qxb5 Rfd8 14. Bc4 Rab8 15. Qa5 Qf4+ 16. Bd2 Qe4 17. Qc3 Nb6 18. Rhe1 cxd4`

FEN (line start): `r4rk1/p1qnbppp/5p2/1pp2b2/3P4/2B2N2/PPP1QPPP/2KR1B1R w - - 0 13`

Game (full game at ply): http://localhost:5173/analysis?game_id=681525&ply=24

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4rk1/p1qnbppp/5p2/1pp2b2/3P4/2B2N2/PPP1QPPP/2KR1B1R%20w%20-%20-%200%2013

#### Case 150 — ATTRACTION (missed, depth 8)

Moves (SAN): `36. Kd1 Rc1+ 37. Ke2 Rc2+ 38. Ke1 Rc1+ 39. Rd1 f5 40. Rxf8+ Kxf8 41. d8=Q+ Kf7`

FEN (line start): `3R1nk1/1p1P1pp1/p2R3p/8/8/1n6/P1r1KPPP/8 w - - 0 36`

Game (full game at ply): http://localhost:5173/analysis?game_id=681564&ply=70

FEN (free-play from line start): http://localhost:5173/analysis?fen=3R1nk1/1p1P1pp1/p2R3p/8/8/1n6/P1r1KPPP/8%20w%20-%20-%200%2036

#### Case 151 — FORK (missed, depth 4)

Moves (SAN): `10. Nb5 Nxf4 11. Qxf4 Be6 12. Nc7+ Kd7 13. Bb5+ Kc8 14. Nxa8 Ng6 15. Qa4 Bc5`

FEN (line start): `r1bqkb1r/pp2nppp/6n1/3p4/2BN1B2/8/PPPQ1PPP/RN2K2R w - - 0 10`

Game (full game at ply): http://localhost:5173/analysis?game_id=681568&ply=18

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1bqkb1r/pp2nppp/6n1/3p4/2BN1B2/8/PPPQ1PPP/RN2K2R%20w%20-%20-%200%2010

#### Case 152 — CLEARANCE (allowed, depth 6)

Moves (SAN): `16... Bc5 17. Kh1 d4 18. Nd2 Kc7 19. Ne4 Rad8 20. Rad1 Kb8 21. Ng5 Rdf8 22. Nxe6`

FEN (line start): `r2k1b1r/pp4pp/1q2p1n1/3p4/Q1P5/1B6/PP3PPP/RN2R1K1 b - - 0 16`

Game (full game at ply): http://localhost:5173/analysis?game_id=681568&ply=30

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2k1b1r/pp4pp/1q2p1n1/3p4/Q1P5/1B6/PP3PPP/RN2R1K1%20b%20-%20-%200%2016

#### Case 153 — INTERFERENCE (missed, depth 2)

Moves (SAN): `16. Qg4 Bd6 17. Rxe6 Rf8 18. Re2 Nf4 19. Rd2 Rc8 20. Nc3 h5 21. Qxg7 Rc7`

FEN (line start): `r2k1b1r/pp4pp/1q2p1n1/3p4/Q7/1B6/PPP2PPP/RN2R1K1 w - - 0 16`

Game (full game at ply): http://localhost:5173/analysis?game_id=681568&ply=30

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2k1b1r/pp4pp/1q2p1n1/3p4/Q7/1B6/PPP2PPP/RN2R1K1%20w%20-%20-%200%2016

#### Case 154 — MATE (allowed, depth 0)

Moves (SAN): `8. Qf7#`

FEN (line start): `r1bqkb1r/ppp3pp/2n5/3Bp1p1/8/5Q2/PPPP1PPP/RNB1K2R w - - 0 8`

Game (full game at ply): http://localhost:5173/analysis?game_id=681579&ply=13

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1bqkb1r/ppp3pp/2n5/3Bp1p1/8/5Q2/PPPP1PPP/RNB1K2R%20w%20-%20-%200%208

#### Case 155 — ATTRACTION (missed, depth 0)

Moves (SAN): `22... Rxg2+ 23. Kxg2 Qg4+ 24. Kf1 Qh3+ 25. Kg1 Qg4+`

FEN (line start): `5rk1/p5pp/8/2Q1pq2/6r1/1P6/P1PPRPP1/RN4K1 b - - 0 22`

Game (full game at ply): http://localhost:5173/analysis?game_id=681579&ply=43

FEN (free-play from line start): http://localhost:5173/analysis?fen=5rk1/p5pp/8/2Q1pq2/6r1/1P6/P1PPRPP1/RN4K1%20b%20-%20-%200%2022

#### Case 156 — FORK (allowed, depth 0)

Moves (SAN): `30. Ne4 Qf1+ 31. Rxf1 Rxf1+ 32. Qg1 Rxg1+ 33. Kxg1 Kf7 34. Kf2 Ke6 35. Ke3 Ke5`

FEN (line start): `6k1/p5pp/5r2/8/1P6/2N5/P4qPQ/3R3K w - - 1 30`

Game (full game at ply): http://localhost:5173/analysis?game_id=681579&ply=57

FEN (free-play from line start): http://localhost:5173/analysis?fen=6k1/p5pp/5r2/8/1P6/2N5/P4qPQ/3R3K%20w%20-%20-%201%2030

#### Case 157 — PROMOTION (allowed, depth 10)

Moves (SAN): `43. a5 Kf6 44. b6 axb6 45. axb6 Ke5 46. Na6 Ke6 47. b7 Kd6 48. b8=Q+ Kc6`

FEN (line start): `8/p7/8/1PN3k1/P5p1/6K1/8/8 w - - 1 43`

Game (full game at ply): http://localhost:5173/analysis?game_id=681579&ply=83

FEN (free-play from line start): http://localhost:5173/analysis?fen=8/p7/8/1PN3k1/P5p1/6K1/8/8%20w%20-%20-%201%2043

#### Case 158 — FORK (missed, depth 4)

Moves (SAN): `22. Ba7 Ra8 23. Bc5 Re8 24. Nc7 Re5 25. Nxa8 Rxc5 26. Nc7 Rc6`

FEN (line start): `1r1r2k1/1b3ppp/p2P4/1p1N4/3BP3/PP1B4/5KPP/R7 w - - 0 22`

Game (full game at ply): http://localhost:5173/analysis?game_id=681585&ply=42

FEN (free-play from line start): http://localhost:5173/analysis?fen=1r1r2k1/1b3ppp/p2P4/1p1N4/3BP3/PP1B4/5KPP/R7%20w%20-%20-%200%2022

#### Case 159 — CLEARANCE (allowed, depth 6)

Moves (SAN): `26... Rxd4 27. Be4 R4d6 28. Rc6 Rxc6 29. Bxc6 Rd1 30. Bb7 Rb1 31. Kd4 Rxb3 32. Bxa6`

FEN (line start): `3r2k1/5ppp/p7/1p1r4/3B4/PP1BK3/6PP/2R5 b - - 1 26`

Game (full game at ply): http://localhost:5173/analysis?game_id=681585&ply=50

FEN (free-play from line start): http://localhost:5173/analysis?fen=3r2k1/5ppp/p7/1p1r4/3B4/PP1BK3/6PP/2R5%20b%20-%20-%201%2026

#### Case 160 — SACRIFICE (missed, depth 4)

Moves (SAN): `26. Rd1 Re8+ 27. Kf3 Rxd4 28. Bxh7+ Kxh7 29. Rxd4 Rc8 30. Ke2 Rc2+ 31. Rd2 Rc6`

FEN (line start): `3r2k1/5ppp/p7/1p1r4/3B4/PP1BK3/6PP/R7 w - - 0 26`

Game (full game at ply): http://localhost:5173/analysis?game_id=681585&ply=50

FEN (free-play from line start): http://localhost:5173/analysis?fen=3r2k1/5ppp/p7/1p1r4/3B4/PP1BK3/6PP/R7%20w%20-%20-%200%2026

#### Case 161 — CLEARANCE (allowed, depth 8)

Moves (SAN): `7... Bxc3+ 8. Qxc3 bxc4`

FEN (line start): `rnbqk1nr/p4ppp/2p1p3/1p6/1bBPP3/1QN2N2/PP3PPP/R1B1K2R b - - 1 7`

Game (full game at ply): http://localhost:5173/analysis?game_id=681586&ply=12

FEN (free-play from line start): http://localhost:5173/analysis?fen=rnbqk1nr/p4ppp/2p1p3/1p6/1bBPP3/1QN2N2/PP3PPP/R1B1K2R%20b%20-%20-%201%207

#### Case 162 — CLEARANCE (missed, depth 10)

Moves (SAN): `7. Bd3 Ne7`

FEN (line start): `rnbqk1nr/p4ppp/2p1p3/1p6/1bBPP3/2N2N2/PP3PPP/R1BQK2R w - - 0 7`

Game (full game at ply): http://localhost:5173/analysis?game_id=681586&ply=12

FEN (free-play from line start): http://localhost:5173/analysis?fen=rnbqk1nr/p4ppp/2p1p3/1p6/1bBPP3/2N2N2/PP3PPP/R1BQK2R%20w%20-%20-%200%207

#### Case 163 — CLEARANCE (allowed, depth 10)

Moves (SAN): `13... Nxd7 14. Qxc6 Qd8 15. Qd6 Qh4`

FEN (line start): `rn2k2r/p2N1pp1/2p1pq1p/8/2QPP3/2P5/P4PPP/R3K2R b - - 0 13`

Game (full game at ply): http://localhost:5173/analysis?game_id=681586&ply=24

FEN (free-play from line start): http://localhost:5173/analysis?fen=rn2k2r/p2N1pp1/2p1pq1p/8/2QPP3/2P5/P4PPP/R3K2R%20b%20-%20-%200%2013

#### Case 164 — FORK (missed, depth 4)

Moves (SAN): `13. Qb4 Bc8 14. Nc4 a5 15. Nd6+ Kf8 16. Qb6 Ba6 17. e5 Qe7 18. c4 Kg8`

FEN (line start): `rn2k2r/p2b1pp1/2p1pq1p/4N3/2QPP3/2P5/P4PPP/R3K2R w - - 0 13`

Game (full game at ply): http://localhost:5173/analysis?game_id=681586&ply=24

FEN (free-play from line start): http://localhost:5173/analysis?fen=rn2k2r/p2b1pp1/2p1pq1p/4N3/2QPP3/2P5/P4PPP/R3K2R%20w%20-%20-%200%2013

#### Case 165 — CLEARANCE (allowed, depth 10)

Moves (SAN): `17... Nc6 18. exd5 exd5 19. Qd3 Ke8 20. Qh7 Rab8 21. Rbe1+ Kd7 22. Qd3 Re8 23. Qxd5+`

FEN (line start): `rnr5/3k1pp1/4pq1p/pQ1p4/4P3/2P5/P4PPP/1R3RK1 b - - 1 17`

Game (full game at ply): http://localhost:5173/analysis?game_id=681586&ply=32

FEN (free-play from line start): http://localhost:5173/analysis?fen=rnr5/3k1pp1/4pq1p/pQ1p4/4P3/2P5/P4PPP/1R3RK1%20b%20-%20-%201%2017

#### Case 166 — PIN (missed, depth 8)

Moves (SAN): `17. Rb7+ Kd8 18. Qb5 Qxc3 19. Rxf7 Qb4 20. Qd3 Rc3 21. Qd1 Ra6 22. Qh5 Rc7`

FEN (line start): `rnr5/3k1pp1/4pq1p/p2p4/2Q1P3/2P5/P4PPP/1R3RK1 w - - 0 17`

Game (full game at ply): http://localhost:5173/analysis?game_id=681586&ply=32

FEN (free-play from line start): http://localhost:5173/analysis?fen=rnr5/3k1pp1/4pq1p/p2p4/2Q1P3/2P5/P4PPP/1R3RK1%20w%20-%20-%200%2017

#### Case 167 — PIN (missed, depth 2)

Moves (SAN): `21. Qb5 Qc6 22. Qe5 Qxc3 23. Qd6 Qc5 24. Qf4 Qf8 25. h4 Rcc7 26. Rfe1 Kc8`

FEN (line start): `2rk4/r2n1pp1/5q1p/p2Q4/8/2P5/P4PPP/3R1RK1 w - - 0 21`

Game (full game at ply): http://localhost:5173/analysis?game_id=681586&ply=40

FEN (free-play from line start): http://localhost:5173/analysis?fen=2rk4/r2n1pp1/5q1p/p2Q4/8/2P5/P4PPP/3R1RK1%20w%20-%20-%200%2021

#### Case 168 — INTERMEZZO (allowed, depth 2)

Moves (SAN): `10... d3 11. Ned4 Qxh6 12. Nf5 Qf4 13. Nxg7+ Kd8 14. Qxd3 Kc7 15. a4 bxa4 16. Rxa4`

FEN (line start): `rnb1k2r/p2p2pp/2p2pqB/1pb5/3pP3/1B3N2/PPP1NPPP/R2Q1RK1 b - - 0 10`

Game (full game at ply): http://localhost:5173/analysis?game_id=681589&ply=18

FEN (free-play from line start): http://localhost:5173/analysis?fen=rnb1k2r/p2p2pp/2p2pqB/1pb5/3pP3/1B3N2/PPP1NPPP/R2Q1RK1%20b%20-%20-%200%2010

#### Case 169 — CLEARANCE (allowed, depth 10)

Moves (SAN): `12... a4 13. Bc2 Bxd4 14. Qxd4`

FEN (line start): `rnb1k2r/3p2pp/2p2p1q/ppb5/3NP3/1BP2N2/PP3PPP/R2Q1RK1 b - - 0 12`

Game (full game at ply): http://localhost:5173/analysis?game_id=681589&ply=22

FEN (free-play from line start): http://localhost:5173/analysis?fen=rnb1k2r/3p2pp/2p2p1q/ppb5/3NP3/1BP2N2/PP3PPP/R2Q1RK1%20b%20-%20-%200%2012

#### Case 170 — FORK (allowed, depth 0)

Moves (SAN): `29... Qxf2+ 30. Kh1 Qxc2 31. Rf1 Rxf1+ 32. Nxf1 Qd3 33. Qf7 h5 34. Qf3 Qc4 35. Qf6+`

FEN (line start): `5r1k/2b4p/4Q1p1/1p6/pP6/2P3N1/P1Bq1PPP/4R1K1 b - - 1 29`

Game (full game at ply): http://localhost:5173/analysis?game_id=681589&ply=56

FEN (free-play from line start): http://localhost:5173/analysis?fen=5r1k/2b4p/4Q1p1/1p6/pP6/2P3N1/P1Bq1PPP/4R1K1%20b%20-%20-%201%2029

#### Case 171 — CLEARANCE (missed, depth 10)

Moves (SAN): `29. Re2 Qxc3 30. Qxb5 Qa1+ 31. Nf1 Qf6 32. Be4 Bb6 33. Bf3 a3 34. Re8 Kg7`

FEN (line start): `5r1k/2b4p/Q5p1/1p6/pP6/2P3N1/P1Bq1PPP/4R1K1 w - - 0 29`

Game (full game at ply): http://localhost:5173/analysis?game_id=681589&ply=56

FEN (free-play from line start): http://localhost:5173/analysis?fen=5r1k/2b4p/Q5p1/1p6/pP6/2P3N1/P1Bq1PPP/4R1K1%20w%20-%20-%200%2029

#### Case 172 — SKEWER (missed, depth 6)

Moves (SAN): `44. Ke4 Rd6 45. Rxb5 Rd2 46. Rb6+ Ke7 47. Rxh6 Rxg2 48. Kd4 Rxg3 49. a3 Rg4+`

FEN (line start): `8/8/1r2k2p/1pR3p1/pP6/2P2KP1/P5P1/8 w - - 0 44`

Game (full game at ply): http://localhost:5173/analysis?game_id=681589&ply=86

FEN (free-play from line start): http://localhost:5173/analysis?fen=8/8/1r2k2p/1pR3p1/pP6/2P2KP1/P5P1/8%20w%20-%20-%200%2044

#### Case 173 — SACRIFICE (allowed, depth 10)

Moves (SAN): `46... Kd7 47. Kh5 Rd6 48. g4 Rd2 49. Kxh6 Rxg2 50. Kxg5 a3 51. Rxb5 Kc6 52. Rc5+`

FEN (line start): `8/4k3/1r5p/1pR3p1/pP4K1/2P3P1/P5P1/8 b - - 1 46`

Game (full game at ply): http://localhost:5173/analysis?game_id=681589&ply=90

FEN (free-play from line start): http://localhost:5173/analysis?fen=8/4k3/1r5p/1pR3p1/pP4K1/2P3P1/P5P1/8%20b%20-%20-%201%2046

#### Case 174 — DEFLECTION (missed, depth 2)

Moves (SAN): `54. g4 Rxg4 55. Rxa2 Ke5 56. Rd2 h5 57. b5 Rg1 58. Ka2 g4 59. b6 Rf1`

FEN (line start): `8/8/5k1p/R5p1/1P6/1KP3P1/p5r1/8 w - - 0 54`

Game (full game at ply): http://localhost:5173/analysis?game_id=681589&ply=106

FEN (free-play from line start): http://localhost:5173/analysis?fen=8/8/5k1p/R5p1/1P6/1KP3P1/p5r1/8%20w%20-%20-%200%2054

#### Case 175 — DEFLECTION (allowed, depth 4)

Moves (SAN): `57... Rb8 58. Rb4 g4 59. Rxg4 Rxb6+ 60. Ka4 h5 61. Rg1 Kf5 62. Rh1 Kg5 63. Rc1`

FEN (line start): `4r3/8/1P3k1p/6p1/R7/1KP5/8/8 b - - 1 57`

Game (full game at ply): http://localhost:5173/analysis?game_id=681589&ply=112

FEN (free-play from line start): http://localhost:5173/analysis?fen=4r3/8/1P3k1p/6p1/R7/1KP5/8/8%20b%20-%20-%201%2057

#### Case 176 — DISCOVERED_CHECK (missed, depth 10)

Moves (SAN): `60. Rb1 g3 61. c4 h4 62. c5 g2 63. c6 Rxb6 64. Rxb6 g1=Q 65. c7+ Qxb6`

FEN (line start): `1r6/8/1P3k2/7p/KR4p1/2P5/8/8 w - - 0 60`

Game (full game at ply): http://localhost:5173/analysis?game_id=681589&ply=118

FEN (free-play from line start): http://localhost:5173/analysis?fen=1r6/8/1P3k2/7p/KR4p1/2P5/8/8%20w%20-%20-%200%2060

#### Case 177 — PROMOTION (allowed, depth 4)

Moves (SAN): `67... h2 68. Rb5+ Kf4 69. Rb2 h1=Q 70. Rf2+ Ke5 71. Rxg2 Qxg2 72. Kc7 Qg1 73. Kc6`

FEN (line start): `1K6/8/8/6k1/2P5/7p/6p1/1R6 b - - 0 67`

Game (full game at ply): http://localhost:5173/analysis?game_id=681589&ply=132

FEN (free-play from line start): http://localhost:5173/analysis?fen=1K6/8/8/6k1/2P5/7p/6p1/1R6%20b%20-%20-%200%2067

#### Case 178 — PROMOTION (allowed, depth 0)

Moves (SAN): `71... hxg1=Q 72. c8=Q Qb6+ 73. Ka8 Qa5+ 74. Kb8`

FEN (line start): `1K6/2P5/8/8/8/6k1/7p/6R1 b - - 0 71`

Game (full game at ply): http://localhost:5173/analysis?game_id=681589&ply=140

FEN (free-play from line start): http://localhost:5173/analysis?fen=1K6/2P5/8/8/8/6k1/7p/6R1%20b%20-%20-%200%2071

#### Case 179 — DISCOVERED_ATTACK (missed, depth 9)

Moves (SAN): `4. a4 c6 5. axb5 cxb5 6. Nc3 Bd7 7. d5 e5 8. dxe6 Bxe6 9. Qxd8+ Kxd8`

FEN (line start): `rnbqkbnr/p1p1pppp/8/1p6/2pPP3/8/PP3PPP/RNBQKBNR w - - 0 4`

Game (full game at ply): http://localhost:5173/analysis?game_id=681593&ply=6

FEN (free-play from line start): http://localhost:5173/analysis?fen=rnbqkbnr/p1p1pppp/8/1p6/2pPP3/8/PP3PPP/RNBQKBNR%20w%20-%20-%200%204

#### Case 180 — FORK (missed, depth 2)

Moves (SAN): `14. Bxb5+ axb5 15. Qxb5+ Nd7 16. Qxb7 Bd6 17. f3 f5 18. Qc6`

FEN (line start): `r2qkb1r/1bp2p1p/p4np1/1p1Pp3/4P3/PQN1B3/1P2BPPP/1R2K2R w - - 0 14`

Game (full game at ply): http://localhost:5173/analysis?game_id=681593&ply=26

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qkb1r/1bp2p1p/p4np1/1p1Pp3/4P3/PQN1B3/1P2BPPP/1R2K2R%20w%20-%20-%200%2014

#### Case 181 — TRAPPED_PIECE (missed, depth 8)

Moves (SAN): `27. f3 Bc5+ 28. Kh1 Rdf8 29. h3 a5 30. Nc1 Bd6 31. fxg4 hxg4 32. Nd3 f4`

FEN (line start): `1k1r3r/2p5/p2b2p1/3Ppp1p/Pp2P1b1/1P4P1/4NPBP/4RRK1 w - - 0 27`

Game (full game at ply): http://localhost:5173/analysis?game_id=681593&ply=52

FEN (free-play from line start): http://localhost:5173/analysis?fen=1k1r3r/2p5/p2b2p1/3Ppp1p/Pp2P1b1/1P4P1/4NPBP/4RRK1%20w%20-%20-%200%2027

#### Case 182 — DISCOVERED_ATTACK (allowed, depth 3)

Moves (SAN): `8... Nc6 9. dxe5 dxe5 10. a3 Qxd3 11. Bxd3 Bxf3 12. gxf3 Nd4 13. Kg2 Nh5 14. Ne2`

FEN (line start): `rn1q1rk1/ppp2pbp/3p1np1/4p3/2BPP1b1/2NQ1N2/PPP2PPP/R1B1R1K1 b - - 1 8`

Game (full game at ply): http://localhost:5173/analysis?game_id=681613&ply=14

FEN (free-play from line start): http://localhost:5173/analysis?fen=rn1q1rk1/ppp2pbp/3p1np1/4p3/2BPP1b1/2NQ1N2/PPP2PPP/R1B1R1K1%20b%20-%20-%201%208

#### Case 183 — FORK (allowed, depth 6)

Moves (SAN): `11... Bxf3 12. gxf3 Nd4 13. Re3 c6 14. a4 Nc2 15. Rd1 h6 16. Re2 Nd4 17. Be3`

FEN (line start): `r4rk1/ppp2pbp/2n2np1/4p1B1/2B1P1b1/2NP1N2/PP3PPP/R3R1K1 b - - 0 11`

Game (full game at ply): http://localhost:5173/analysis?game_id=681613&ply=20

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4rk1/ppp2pbp/2n2np1/4p1B1/2B1P1b1/2NP1N2/PP3PPP/R3R1K1%20b%20-%20-%200%2011

#### Case 184 — SACRIFICE (missed, depth 4)

Moves (SAN): `14. f5 Nf3+ 15. Kg2 Nxe1+ 16. Rxe1 c6 17. a4 Rfb8 18. Be3 a6 19. a5 Bf8`

FEN (line start): `r4rk1/pppn1pbp/6p1/4p1B1/2BnPP2/2NP4/PP3P1P/R3R1K1 w - - 0 14`

Game (full game at ply): http://localhost:5173/analysis?game_id=681613&ply=26

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4rk1/pppn1pbp/6p1/4p1B1/2BnPP2/2NP4/PP3P1P/R3R1K1%20w%20-%20-%200%2014

#### Case 185 — FORK (missed, depth 6)

Moves (SAN): `33. Ra4 Rg7 34. Rc6 Rd7 35. Nh5 Be7 36. Nxf6+ Bxf6 37. Rxf6 Rd2 38. Re6 Rxb2`

FEN (line start): `r4bk1/2R4p/5p2/p3pPr1/1p6/6NK/RP3P1P/8 w - - 0 33`

Game (full game at ply): http://localhost:5173/analysis?game_id=681613&ply=64

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4bk1/2R4p/5p2/p3pPr1/1p6/6NK/RP3P1P/8%20w%20-%20-%200%2033

#### Case 186 — CLEARANCE (missed, depth 6)

Moves (SAN): `34. Kg4 Rxh2 35. Kg3 Rh6 36. b3 Kh8 37. Rd2 Rh1 38. Rdd7 Bg7 39. Kf3 Rg8`

FEN (line start): `r4bk1/2R4p/5p2/p3pP1r/1p2N3/7K/RP3P1P/8 w - - 0 34`

Game (full game at ply): http://localhost:5173/analysis?game_id=681613&ply=66

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4bk1/2R4p/5p2/p3pP1r/1p2N3/7K/RP3P1P/8%20w%20-%20-%200%2034

#### Case 187 — DISCOVERED_ATTACK (allowed, depth 1)

Moves (SAN): `9. d4 Bb7 10. Bxf4 exf4 11. Re1+ Be7 12. Qe2 Na5 13. Bc2 Nc4 14. Be4 c6`

FEN (line start): `r1bqkb1r/2p2ppp/p1n5/1p2p3/5n2/1BP2N2/PP1P1PPP/RNBQ1RK1 w - - 1 9`

Game (full game at ply): http://localhost:5173/analysis?game_id=681616&ply=15

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1bqkb1r/2p2ppp/p1n5/1p2p3/5n2/1BP2N2/PP1P1PPP/RNBQ1RK1%20w%20-%20-%201%209

#### Case 188 — DISCOVERED_CHECK (allowed, depth 8)

Moves (SAN): `10. d4 Be7 11. d5 Na5 12. Nxe5 Ng6 13. Nxf7 Kxf7 14. d6+ Nxb3 15. Qxb3+ Ke8`

FEN (line start): `r1bqk2r/2p2ppp/p1nb4/1p2p3/5n2/1BP2N2/PP1P1PPP/RNBQR1K1 w - - 1 10`

Game (full game at ply): http://localhost:5173/analysis?game_id=681616&ply=17

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1bqk2r/2p2ppp/p1nb4/1p2p3/5n2/1BP2N2/PP1P1PPP/RNBQR1K1%20w%20-%20-%201%2010

#### Case 189 — FORK (allowed, depth 2)

Moves (SAN): `12. Bxc6 Bxc6 13. dxe5 Nh3+ 14. Kf1 Bxe5 15. Rxe5+ Kf8 16. Be3 Rd8 17. Qe2 g5`

FEN (line start): `r3k2r/2pb1ppp/p1nb1q2/1p1Bp3/3P1n2/2P2N2/PP3PPP/RNBQR1K1 w - - 1 12`

Game (full game at ply): http://localhost:5173/analysis?game_id=681616&ply=21

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3k2r/2pb1ppp/p1nb1q2/1p1Bp3/3P1n2/2P2N2/PP3PPP/RNBQR1K1%20w%20-%20-%201%2012

#### Case 190 — HANGING_PIECE (missed, depth 0)

Moves (SAN): `11... Nxd5 12. dxe5 Bxe5 13. Qxd5 Qd6 14. Rxe5+ Nxe5 15. Qxe5+ Qxe5 16. Nxe5`

FEN (line start): `r1b1k2r/2p2ppp/p1nb1q2/1p1Bp3/3P1n2/2P2N2/PP3PPP/RNBQR1K1 b - - 0 11`

Game (full game at ply): http://localhost:5173/analysis?game_id=681616&ply=21

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1b1k2r/2p2ppp/p1nb1q2/1p1Bp3/3P1n2/2P2N2/PP3PPP/RNBQR1K1%20b%20-%20-%200%2011

#### Case 191 — MATE (allowed, depth 0)

Moves (SAN): `9. Qf7#`

FEN (line start): `r1bqkb1r/ppp3pp/8/3Bp3/3n4/5Q2/PPPP1PPP/RNB1K2R w - - 1 9`

Game (full game at ply): http://localhost:5173/analysis?game_id=681621&ply=15

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1bqkb1r/ppp3pp/8/3Bp3/3n4/5Q2/PPPP1PPP/RNB1K2R%20w%20-%20-%201%209

#### Case 192 — CLEARANCE (missed, depth 8)

Moves (SAN): `4. cxd5 c6 5. dxc6 bxc6 6. Nf3 e6 7. e4 Be7 8. Be2`

FEN (line start): `r1bqkb1r/pppnpppp/5n2/3p4/2PP4/2N5/PP2PPPP/R1BQKBNR w - - 0 4`

Game (full game at ply): http://localhost:5173/analysis?game_id=681624&ply=6

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1bqkb1r/pppnpppp/5n2/3p4/2PP4/2N5/PP2PPPP/R1BQKBNR%20w%20-%20-%200%204

#### Case 193 — DISCOVERED_ATTACK (missed, depth 1)

Moves (SAN): `23. Rxf6+ Kxf6 24. Qxd7 b6 25. cxb6 axb6 26. Ne5 g5 27. f3 c5 28. Ng4+ Kg6`

FEN (line start): `5r2/pppq1kp1/4Rb1p/2P5/3P2Q1/5N2/PP3PPP/6K1 w - - 0 23`

Game (full game at ply): http://localhost:5173/analysis?game_id=681624&ply=44

FEN (free-play from line start): http://localhost:5173/analysis?fen=5r2/pppq1kp1/4Rb1p/2P5/3P2Q1/5N2/PP3PPP/6K1%20w%20-%20-%200%2023

#### Case 194 — CLEARANCE (missed, depth 6)

Moves (SAN): `8... dxc4 9. e3 b5 10. a4 c6 11. h4 Qb6 12. h5 h6 13. Qf3 bxa4 14. e4`

FEN (line start): `rn1q1rk1/pppbbppp/4p3/3p4/2PP1B2/2N5/PP2PPPP/R2QKB1R b - - 0 8`

Game (full game at ply): http://localhost:5173/analysis?game_id=681632&ply=15

FEN (free-play from line start): http://localhost:5173/analysis?fen=rn1q1rk1/pppbbppp/4p3/3p4/2PP1B2/2N5/PP2PPPP/R2QKB1R%20b%20-%20-%200%208

#### Case 195 — FORK (allowed, depth 8)

Moves (SAN): `21. Nd5 Qxd5 22. Rxd5 Bxd5 23. Bxg7 Kxg7 24. h4 h5 25. Qc5 Rd7 26. Re1 Rad8`

FEN (line start): `r5k1/1pp1rpbp/p3b1pB/2q5/8/2N5/PP3PPP/R1QR2K1 w - - 0 21`

Game (full game at ply): http://localhost:5173/analysis?game_id=681641&ply=39

FEN (free-play from line start): http://localhost:5173/analysis?fen=r5k1/1pp1rpbp/p3b1pB/2q5/8/2N5/PP3PPP/R1QR2K1%20w%20-%20-%200%2021

#### Case 196 — CLEARANCE (allowed, depth 2)

Moves (SAN): `10. d4 Bb6 11. Bg5 Qd7 12. Bh4 Rae8 13. Nd2 c6 14. Re1 Nf4 15. Bxe6 Rxe6`

FEN (line start): `r2q1rk1/ppp2ppp/4b3/2bnR3/2B5/2P5/PP1P1PPP/RNBQ2K1 w - - 1 10`

Game (full game at ply): http://localhost:5173/analysis?game_id=681643&ply=17

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2q1rk1/ppp2ppp/4b3/2bnR3/2B5/2P5/PP1P1PPP/RNBQ2K1%20w%20-%20-%201%2010

#### Case 197 — CLEARANCE (missed, depth 6)

Moves (SAN): `11. Nb3 Qxe5+ 12. Qe2 Nc6 13. Qxe5 Nxe5 14. Be2 b6 15. f4 Ng4 16. Bf3 Rb8`

FEN (line start): `rnb2rk1/ppp1b1pp/4p3/2N1Pp2/3q4/3B4/PPP2PPP/R1BQK2R w - - 0 11`

Game (full game at ply): http://localhost:5173/analysis?game_id=681647&ply=20

FEN (free-play from line start): http://localhost:5173/analysis?fen=rnb2rk1/ppp1b1pp/4p3/2N1Pp2/3q4/3B4/PPP2PPP/R1BQK2R%20w%20-%20-%200%2011

#### Case 198 — PIN (missed, depth 2)

Moves (SAN): `8... Nxe4 9. Nxe4 Qh4 10. Nd2 Bxf2+ 11. Kd1 d5 12. Nf3 Qxe4 13. Qc2 Qxc2+ 14. Kxc2`

FEN (line start): `r1bqr1k1/pppp1ppp/2n2n2/2b5/Q3P3/2P3NP/PP3PP1/RNB1KB1R b - - 0 8`

Game (full game at ply): http://localhost:5173/analysis?game_id=681650&ply=15

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1bqr1k1/pppp1ppp/2n2n2/2b5/Q3P3/2P3NP/PP3PP1/RNB1KB1R%20b%20-%20-%200%208

#### Case 199 — CLEARANCE (allowed, depth 8)

Moves (SAN): `30. Rb3 Ra2 31. Rb8+ Kg7 32. Rb7 Bb6 33. f3 a5 34. Bg3 Rxa4 35. Be5+ Kf8`

FEN (line start): `6k1/p1p2p1p/6p1/b1p5/P7/R1P4P/2r2PP1/4BK2 w - - 1 30`

Game (full game at ply): http://localhost:5173/analysis?game_id=681650&ply=57

FEN (free-play from line start): http://localhost:5173/analysis?fen=6k1/p1p2p1p/6p1/b1p5/P7/R1P4P/2r2PP1/4BK2%20w%20-%20-%201%2030

#### Case 200 — DISCOVERED_ATTACK (allowed, depth 1)

Moves (SAN): `8. dxe5 dxe5 9. Qxd8 Rxd8 10. Bxf6 gxf6 11. Nd2 Be6 12. Bd3 Rd6 13. Nb5 Rd7`

FEN (line start): `r1bq1rk1/ppp2pp1/2np1n1p/4p3/1b1PP2B/2N2N2/PPP2PPP/R2QKB1R w - - 0 8`

Game (full game at ply): http://localhost:5173/analysis?game_id=681686&ply=13

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1bq1rk1/ppp2pp1/2np1n1p/4p3/1b1PP2B/2N2N2/PPP2PPP/R2QKB1R%20w%20-%20-%200%208

#### Case 201 — PIN (missed, depth 4)

Moves (SAN): `7... exd4 8. Nxd4 Re8 9. Nxc6 Rxe4+ 10. Be2 bxc6 11. Bxf6 Qxf6`

FEN (line start): `r1bq1rk1/pppp1pp1/2n2n1p/4p3/1b1PP2B/2N2N2/PPP2PPP/R2QKB1R b - - 0 7`

Game (full game at ply): http://localhost:5173/analysis?game_id=681686&ply=13

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1bq1rk1/pppp1pp1/2n2n1p/4p3/1b1PP2B/2N2N2/PPP2PPP/R2QKB1R%20b%20-%20-%200%207

#### Case 202 — CAPTURING_DEFENDER (missed, depth 4)

Moves (SAN): `10... Qxd1 11. Raxd1 Bxc3 12. bxc3 Nxe4 13. Rfe1 Nd6 14. Bd5 e4 15. h3 Bxf3 16. gxf3`

FEN (line start): `r2q1rk1/ppp2pp1/2n2n1p/4p3/1bB1P1bB/2N2N2/PPP2PPP/R2Q1RK1 b - - 0 10`

Game (full game at ply): http://localhost:5173/analysis?game_id=681686&ply=19

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2q1rk1/ppp2pp1/2n2n1p/4p3/1bB1P1bB/2N2N2/PPP2PPP/R2Q1RK1%20b%20-%20-%200%2010

#### Case 203 — CAPTURING_DEFENDER (missed, depth 2)

Moves (SAN): `13... Qxd1 14. Raxd1 Bxf3 15. Rd3 Bxe4 16. Re3 Bxc2 17. f4 exf4 18. Rxf4 b5 19. Ba2`

FEN (line start): `r2q1rk1/ppp2pp1/5n1p/4p3/2B1P1bB/P1P2P2/2P2P1P/R2Q1RK1 b - - 0 13`

Game (full game at ply): http://localhost:5173/analysis?game_id=681686&ply=25

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2q1rk1/ppp2pp1/5n1p/4p3/2B1P1bB/P1P2P2/2P2P1P/R2Q1RK1%20b%20-%20-%200%2013

#### Case 204 — CLEARANCE (allowed, depth 6)

Moves (SAN): `16. Qxd6 cxd6 17. Bxf6 gxf6 18. Kh1 Kh7 19. Rg1 Rac8 20. Rad1 Rc6 21. Rd3 Be6`

FEN (line start): `r4rk1/ppp2pp1/3q1n1p/4p3/4P2B/PBP2P1b/2P2P1P/R2QR1K1 w - - 1 16`

Game (full game at ply): http://localhost:5173/analysis?game_id=681686&ply=29

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4rk1/ppp2pp1/3q1n1p/4p3/4P2B/PBP2P1b/2P2P1P/R2QR1K1%20w%20-%20-%201%2016

#### Case 205 — CLEARANCE (missed, depth 4)

Moves (SAN): `15... g5 16. Bg3 Qe7 17. Bc4 Rad8 18. Qc1 Nh5 19. Bf1 Bxf1 20. Kxf1 Rd6 21. a4`

FEN (line start): `r2q1rk1/ppp2pp1/5n1p/4p3/4P2B/PBP2P1b/2P2P1P/R2QR1K1 b - - 0 15`

Game (full game at ply): http://localhost:5173/analysis?game_id=681686&ply=29

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2q1rk1/ppp2pp1/5n1p/4p3/4P2B/PBP2P1b/2P2P1P/R2QR1K1%20b%20-%20-%200%2015

#### Case 206 — PIN (missed, depth 4)

Moves (SAN): `18... Nf4 19. Qb1 h5 20. Qxb7 h4 21. Qc6 Nxd5 22. Qxg6 fxg6 23. exd5 hxg3 24. Re3`

FEN (line start): `r4rk1/ppp2pp1/6qp/3Bp2n/4P3/P1P2PBb/2P2P1P/R1Q1R1K1 b - - 0 18`

Game (full game at ply): http://localhost:5173/analysis?game_id=681686&ply=35

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4rk1/ppp2pp1/6qp/3Bp2n/4P3/P1P2PBb/2P2P1P/R1Q1R1K1%20b%20-%20-%200%2018

#### Case 207 — FORK (allowed, depth 2)

Moves (SAN): `28. Rxd8 Rxd8 29. Qh4 Rd2 30. Bh5 Qg5 31. Qxg5 hxg5 32. axb6 axb6 33. Bg6 Rd8`

FEN (line start): `3r1r1k/p5p1/1p4qp/P1p2p2/4PQ2/2P3Pb/2P1B2P/R2R2K1 w - - 0 28`

Game (full game at ply): http://localhost:5173/analysis?game_id=681686&ply=53

FEN (free-play from line start): http://localhost:5173/analysis?fen=3r1r1k/p5p1/1p4qp/P1p2p2/4PQ2/2P3Pb/2P1B2P/R2R2K1%20w%20-%20-%200%2028

#### Case 208 — TRAPPED_PIECE (missed, depth 8)

Moves (SAN): `12... Qe7 13. e4`

FEN (line start): `r2qk2r/1ppb1ppp/p7/2nQP3/5B2/5P2/PPP1PbPP/R2K1BNR b - - 0 12`

Game (full game at ply): http://localhost:5173/analysis?game_id=681700&ply=23

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qk2r/1ppb1ppp/p7/2nQP3/5B2/5P2/PPP1PbPP/R2K1BNR%20b%20-%20-%200%2012

#### Case 209 — CLEARANCE (allowed, depth 8)

Moves (SAN): `21... Nxf5 22. exf5 e4 23. Rb1 exf3 24. Bb2 Qxb2 25. Rxb2 Bf6 26. Rb3 fxe2 27. Re1`

FEN (line start): `r2b3r/p3npk1/P2p1q1p/1QpPpNpb/1p2P3/5N1P/P1P1BPP1/R1B2RK1 b - - 1 21`

Game (full game at ply): http://localhost:5173/analysis?game_id=681709&ply=40

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2b3r/p3npk1/P2p1q1p/1QpPpNpb/1p2P3/5N1P/P1P1BPP1/R1B2RK1%20b%20-%20-%201%2021

#### Case 210 — CLEARANCE (missed, depth 4)

Moves (SAN): `4. Nxd4 exd4`

FEN (line start): `r1bqkbnr/pppp1ppp/8/4p3/2BnP3/5N2/PPPP1PPP/RNBQK2R w - - 0 4`

Game (full game at ply): http://localhost:5173/analysis?game_id=681714&ply=6

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1bqkbnr/pppp1ppp/8/4p3/2BnP3/5N2/PPPP1PPP/RNBQK2R%20w%20-%20-%200%204

#### Case 211 — PIN (allowed, depth 4)

Moves (SAN): `13... Qg5 14. Bxd4 Bxd4 15. c3 Bxh3 16. Qf3 Bg4 17. Qg3 Bc5 18. d4 Bd6 19. f4`

FEN (line start): `r1b2rk1/ppp2ppp/5q2/2bP4/2Bn4/1PBP3P/P1P2PP1/RN1Q1RK1 b - - 1 13`

Game (full game at ply): http://localhost:5173/analysis?game_id=681714&ply=24

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1b2rk1/ppp2ppp/5q2/2bP4/2Bn4/1PBP3P/P1P2PP1/RN1Q1RK1%20b%20-%20-%201%2013

#### Case 212 — CLEARANCE (missed, depth 10)

Moves (SAN): `16. Nd2 Re8 17. Nf3 Bxh3 18. gxh3 Qf5 19. Bxd4 Qxh3+ 20. Nh2 Bxd4 21. Qf3 Qh6`

FEN (line start): `r1b2r1k/ppp2ppp/1b4q1/3P4/1PBn4/2BP3P/P1P2PP1/RN1Q1R1K w - - 0 16`

Game (full game at ply): http://localhost:5173/analysis?game_id=681714&ply=30

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1b2r1k/ppp2ppp/1b4q1/3P4/1PBn4/2BP3P/P1P2PP1/RN1Q1R1K%20w%20-%20-%200%2016

#### Case 213 — HANGING_PIECE (allowed, depth 0)

Moves (SAN): `29... Bxe1 30. a6 Rxa6 31. Bxa6 bxa6 32. Qe2 Bc3 33. Qe5+ Kg8 34. Qg5+ Kh8 35. Qc5`

FEN (line start): `r7/1ppb1rkp/8/P7/Pb1P1p2/3B1Q1P/2P2PP1/4R2K b - - 1 29`

Game (full game at ply): http://localhost:5173/analysis?game_id=681714&ply=56

FEN (free-play from line start): http://localhost:5173/analysis?fen=r7/1ppb1rkp/8/P7/Pb1P1p2/3B1Q1P/2P2PP1/4R2K%20b%20-%20-%201%2029

#### Case 214 — FORK (missed, depth 0)

Moves (SAN): `29. Qxb7 Re8 30. Qxb4 f3 31. g4 Kh8 32. Qc5 Rg7 33. Qh5 Reg8 34. Qe5 Bc6`

FEN (line start): `r7/1ppb1rkp/8/P7/Pb1P1p2/3B1Q1P/2P2PP1/5R1K w - - 0 29`

Game (full game at ply): http://localhost:5173/analysis?game_id=681714&ply=56

FEN (free-play from line start): http://localhost:5173/analysis?fen=r7/1ppb1rkp/8/P7/Pb1P1p2/3B1Q1P/2P2PP1/5R1K%20w%20-%20-%200%2029

#### Case 215 — DISCOVERED_CHECK (allowed, depth 10)

Moves (SAN): `30... Rxa5 31. Kg1 Rxa4 32. Qe4 Ra1 33. Qxh7+ Kf8 34. Qh8+ Ke7 35. Bg6 Bb4+ 36. Kh2`

FEN (line start): `r7/1Qpb1rkp/8/P7/P2P1p2/3B3P/2P2PP1/4b2K b - - 0 30`

Game (full game at ply): http://localhost:5173/analysis?game_id=681714&ply=58

FEN (free-play from line start): http://localhost:5173/analysis?fen=r7/1Qpb1rkp/8/P7/P2P1p2/3B3P/2P2PP1/4b2K%20b%20-%20-%200%2030

#### Case 216 — SACRIFICE (missed, depth 2)

Moves (SAN): `41. Qxe1 Rxe1 42. b7 Rb1 43. a6 Kg7 44. a7 Rxb7 45. a8=Q Rb1 46. Qe8 h5`

FEN (line start): `6k1/7p/1P2r3/P7/3P1p2/2Q2P2/2P3PK/4r3 w - - 0 41`

Game (full game at ply): http://localhost:5173/analysis?game_id=681714&ply=80

FEN (free-play from line start): http://localhost:5173/analysis?fen=6k1/7p/1P2r3/P7/3P1p2/2Q2P2/2P3PK/4r3%20w%20-%20-%200%2041

#### Case 217 — CLEARANCE (allowed, depth 6)

Moves (SAN): `15. Rxf2 Qd6 16. c5 Qe7 17. Qe2 Rd8 18. Re1 h6 19. Nc4 Be6 20. Nxe5 Nxe5`

FEN (line start): `r1b2rk1/ppp2ppp/2n2n2/4p3/1PPq4/P6P/1BPN1pP1/1R1Q1RK1 w - - 0 15`

Game (full game at ply): http://localhost:5173/analysis?game_id=681715&ply=27

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1b2rk1/ppp2ppp/2n2n2/4p3/1PPq4/P6P/1BPN1pP1/1R1Q1RK1%20w%20-%20-%200%2015

#### Case 218 — SACRIFICE (missed, depth 8)

Moves (SAN): `34... Qh5+ 35. Kg1 Re1+ 36. Rf1 Rxf1+ 37. Kxf1 Rxc5 38. Qxc5 Bh3+ 39. Ke1 Qxc5 40. Rh4`

FEN (line start): `2r1r1k1/Q4pp1/7p/1PB1q3/1R4b1/6P1/2P2R1K/8 b - - 0 34`

Game (full game at ply): http://localhost:5173/analysis?game_id=681715&ply=67

FEN (free-play from line start): http://localhost:5173/analysis?fen=2r1r1k1/Q4pp1/7p/1PB1q3/1R4b1/6P1/2P2R1K/8%20b%20-%20-%200%2034

#### Case 219 — FORK (allowed, depth 0)

Moves (SAN): `18... Ne4+ 19. Rxe4 Qxe4 20. Bg3 Qxd5 21. Qf6 g4 22. Bxd6 gxf3 23. Be5 Kf8 24. Qh8+`

FEN (line start): `r3q1k1/pp3p2/3p1n1p/2pP2p1/7B/P1Q2N2/1PP2KPP/4R3 b - - 1 18`

Game (full game at ply): http://localhost:5173/analysis?game_id=681718&ply=34

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3q1k1/pp3p2/3p1n1p/2pP2p1/7B/P1Q2N2/1PP2KPP/4R3%20b%20-%20-%201%2018

#### Case 220 — CLEARANCE (missed, depth 4)

Moves (SAN): `23. Qd4 Nd5 24. Qxb6 Nxb6 25. Bd4 Nd5 26. Rd1 b6 27. Bc3 Rd8 28. Rd4 b5`

FEN (line start): `r5k1/pp3p2/1q3n1p/4B1p1/2p5/P2Q1N2/1PP2KPP/4R3 w - - 0 23`

Game (full game at ply): http://localhost:5173/analysis?game_id=681718&ply=44

FEN (free-play from line start): http://localhost:5173/analysis?fen=r5k1/pp3p2/1q3n1p/4B1p1/2p5/P2Q1N2/1PP2KPP/4R3%20w%20-%20-%200%2023

#### Case 221 — SACRIFICE (missed, depth 8)

Moves (SAN): `37. Bxe1 Qxf6 38. h3 Kh7 39. Bb4 c3 40. Bxc3 Qxc3 41. Kf2 Qd2+ 42. Kf1 Kg6`

FEN (line start): `6k1/p4p2/1p2qR1p/6p1/2p5/P1B5/6PP/4r1K1 w - - 0 37`

Game (full game at ply): http://localhost:5173/analysis?game_id=681718&ply=72

FEN (free-play from line start): http://localhost:5173/analysis?fen=6k1/p4p2/1p2qR1p/6p1/2p5/P1B5/6PP/4r1K1%20w%20-%20-%200%2037

#### Case 222 — EN_PASSANT (allowed, depth 4)

Moves (SAN): `8. d5 Nd4 9. Be3 c5 10. dxc6 bxc6 11. Nf3 Bg4 12. Be2 Bxf3 13. Bxf3 Bc5`

FEN (line start): `r1bqkb1r/ppp2ppp/2n2n2/4p3/3PP3/P1N5/1P3PPP/R1BQKBNR w - - 1 8`

Game (full game at ply): http://localhost:5173/analysis?game_id=681719&ply=13

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1bqkb1r/ppp2ppp/2n2n2/4p3/3PP3/P1N5/1P3PPP/R1BQKBNR%20w%20-%20-%201%208

#### Case 223 — PIN (allowed, depth 0)

Moves (SAN): `15. Rg2 Qh4 16. fxe5 Bd4 17. Rg5 g6`

FEN (line start): `r1b2rk1/ppp2ppp/7B/2bPp2n/4PP2/P1N2Q2/1P3P1q/R3KBR1 w - - 0 15`

Game (full game at ply): http://localhost:5173/analysis?game_id=681719&ply=27

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1b2rk1/ppp2ppp/7B/2bPp2n/4PP2/P1N2Q2/1P3P1q/R3KBR1%20w%20-%20-%200%2015

#### Case 224 — CLEARANCE (missed, depth 4)

Moves (SAN): `16... Qxh1 17. fxe5 Bg4 18. Be3 Rae8 19. Kd2 Rxe5 20. Re1 Qf3 21. Bxa7 Nf6 22. Bd3`

FEN (line start): `r1b2rk1/ppp2ppp/7B/3Pp2n/4PP2/P1N5/1P3Q1q/R3KB1R b - - 0 16`

Game (full game at ply): http://localhost:5173/analysis?game_id=681719&ply=31

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1b2rk1/ppp2ppp/7B/3Pp2n/4PP2/P1N5/1P3Q1q/R3KB1R%20b%20-%20-%200%2016

#### Case 225 — CLEARANCE (missed, depth 8)

Moves (SAN): `9. Bxc7 Bd7 10. d4 Rc8 11. Bg3 g6`

FEN (line start): `r1b1kb1r/ppp1pppp/2n2n2/5q2/5B2/2NP1B2/PPP1NPPP/R2QK2R w - - 0 9`

Game (full game at ply): http://localhost:5173/analysis?game_id=681722&ply=16

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1b1kb1r/ppp1pppp/2n2n2/5q2/5B2/2NP1B2/PPP1NPPP/R2QK2R%20w%20-%20-%200%209

#### Case 226 — CLEARANCE (allowed, depth 4)

Moves (SAN): `8... Ne7 9. f4 c6 10. Be3 Qb6 11. Qxb6 axb6 12. Bxb6 Nc8 13. Bf2 b5 14. Bb3`

FEN (line start): `r2qkbnr/pppb2pp/3p1p2/8/2BQP3/2N5/PPP2PPP/R1B2RK1 b - - 1 8`

Game (full game at ply): http://localhost:5173/analysis?game_id=681723&ply=14

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qkbnr/pppb2pp/3p1p2/8/2BQP3/2N5/PPP2PPP/R1B2RK1%20b%20-%20-%201%208

#### Case 227 — CLEARANCE (missed, depth 10)

Moves (SAN): `8. Qd5 Qe7 9. Qxb7 Rc8 10. Qb3 Nh6 11. Bxh6 gxh6 12. Nc3 c6 13. Rad1 h5`

FEN (line start): `r2qkbnr/pppb2pp/3p1p2/8/2BQP3/8/PPP2PPP/RNB2RK1 w - - 0 8`

Game (full game at ply): http://localhost:5173/analysis?game_id=681723&ply=14

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qkbnr/pppb2pp/3p1p2/8/2BQP3/8/PPP2PPP/RNB2RK1%20w%20-%20-%200%208

#### Case 228 — CLEARANCE (missed, depth 6)

Moves (SAN): `16... Qd7 17. g4 Bg6 18. Re3 f6 19. Nh4 Bf7 20. Kh2 Rf8 21. Qe1 Ne7`

FEN (line start): `r2qr1k1/1pp2ppp/1pn5/1N2p2b/8/P2P1N1P/1PP2PP1/R2QR1K1 b - - 0 16`

Game (full game at ply): http://localhost:5173/analysis?game_id=681728&ply=31

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qr1k1/1pp2ppp/1pn5/1N2p2b/8/P2P1N1P/1PP2PP1/R2QR1K1%20b%20-%20-%200%2016

#### Case 229 — DEFLECTION (missed, depth 6)

Moves (SAN): `8... Bg4 9. Qd2 Nd4 10. c3 Nf3+ 11. gxf3 Bxh3 12. Qe2 Bxf1 13. Kxf1 Nxd5 14. Qxe5`

FEN (line start): `r1bq1rk1/ppp2pp1/2n2n1p/2bPp3/2B5/3P3N/PPP2PPP/RNBQ1RK1 b - - 0 8`

Game (full game at ply): http://localhost:5173/analysis?game_id=681730&ply=15

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1bq1rk1/ppp2pp1/2n2n1p/2bPp3/2B5/3P3N/PPP2PPP/RNBQ1RK1%20b%20-%20-%200%208

#### Case 230 — EN_PASSANT (missed, depth 4)

Moves (SAN): `8. e5 Ne4 9. Qd4 f5 10. exf6 Nxf6 11. Bxc4 Bxc3+ 12. Qxc3 d6`

FEN (line start): `rnb1k2r/ppqp1ppp/5n2/3P4/1bp1P3/2N2N2/PP3PPP/R1BQKB1R w - - 0 8`

Game (full game at ply): http://localhost:5173/analysis?game_id=681736&ply=14

FEN (free-play from line start): http://localhost:5173/analysis?fen=rnb1k2r/ppqp1ppp/5n2/3P4/1bp1P3/2N2N2/PP3PPP/R1BQKB1R%20w%20-%20-%200%208

#### Case 231 — PIN (allowed, depth 10)

Moves (SAN): `9. Nxe5 Nxe5 10. Rxe5+ Be7 11. Bg5 Be6 12. Bxd5 Bxg5 13. Bxa8 Nd7 14. Bc6 Bf6`

FEN (line start): `r1bqkb1r/2p2ppp/p1n5/1pnpp3/8/1B1P1N2/PPP2PPP/RNBQR1K1 w - - 1 9`

Game (full game at ply): http://localhost:5173/analysis?game_id=681739&ply=15

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1bqkb1r/2p2ppp/p1n5/1pnpp3/8/1B1P1N2/PPP2PPP/RNBQR1K1%20w%20-%20-%201%209

#### Case 232 — FORK (allowed, depth 0)

Moves (SAN): `13. Bc6+ Nd7 14. Qh5+ g6 15. Qh3`

FEN (line start): `r2qk2r/2p3pp/p2bp3/1pnB4/8/3P4/PPP2PPP/RNBQ2K1 w - - 0 13`

Game (full game at ply): http://localhost:5173/analysis?game_id=681739&ply=23

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qk2r/2p3pp/p2bp3/1pnB4/8/3P4/PPP2PPP/RNBQ2K1%20w%20-%20-%200%2013

#### Case 233 — INTERMEZZO (allowed, depth 2)

Moves (SAN): `12. Qxh7+ Kf8 13. Nxe5 Rxe5 14. Nc4 Re8 15. Qh8+ Ke7 16. Qxg7 Rg8 17. Qe5+ Kf8`

FEN (line start): `r1bqr1k1/ppp2ppp/8/3nn3/8/4PNP1/PPQN1PP1/R3KB1R w - - 0 12`

Game (full game at ply): http://localhost:5173/analysis?game_id=681774&ply=21

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1bqr1k1/ppp2ppp/8/3nn3/8/4PNP1/PPQN1PP1/R3KB1R%20w%20-%20-%200%2012

#### Case 234 — CLEARANCE (missed, depth 6)

Moves (SAN): `11... h6 12. Bc4 Be6 13. Qe4 Ndb4 14. Rd1 Bd5 15. Qb1 Bxc4 16. Nxc4 Qe7 17. a3`

FEN (line start): `r1bqr1k1/ppp2ppp/2n5/3nP3/8/4PNP1/PPQN1PP1/R3KB1R b - - 0 11`

Game (full game at ply): http://localhost:5173/analysis?game_id=681774&ply=21

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1bqr1k1/ppp2ppp/2n5/3nP3/8/4PNP1/PPQN1PP1/R3KB1R%20b%20-%20-%200%2011

#### Case 235 — SACRIFICE (allowed, depth 2)

Moves (SAN): `20. Rh6 Rxd2 21. Qxf6+ Kd7 22. Nxd2 Qa5 23. Bh3 Bxh3 24. Rxh3 Qxa2 25. Rh7 Rf8`

FEN (line start): `3rr3/ppp1kp2/4bn2/6Q1/1qN5/4PPP1/PP1R1P2/4KB1R w - - 1 20`

Game (full game at ply): http://localhost:5173/analysis?game_id=681774&ply=37

FEN (free-play from line start): http://localhost:5173/analysis?fen=3rr3/ppp1kp2/4bn2/6Q1/1qN5/4PPP1/PP1R1P2/4KB1R%20w%20-%20-%201%2020

#### Case 236 — CLEARANCE (missed, depth 10)

Moves (SAN): `19... Kd7 20. a3 Qb3 21. Bh3 Kc8 22. Bxe6+ fxe6 23. Qg4 Kb8`

FEN (line start): `3rr3/ppp1kp2/4b3/3n2Q1/1qN5/4PPP1/PP1R1P2/4KB1R b - - 0 19`

Game (full game at ply): http://localhost:5173/analysis?game_id=681774&ply=37

FEN (free-play from line start): http://localhost:5173/analysis?fen=3rr3/ppp1kp2/4b3/3n2Q1/1qN5/4PPP1/PP1R1P2/4KB1R%20b%20-%20-%200%2019

#### Case 237 — DISCOVERED_CHECK (allowed, depth 10)

Moves (SAN): `40... Nd1 41. h4 Bd2+ 42. Kg3 Be1+ 43. Kh2 Re2+ 44. Kh3 Nf2+ 45. Kg3 Nd3+ 46. Kh3`

FEN (line start): `7R/p4p2/3k1p2/b3r3/5K2/1B3P2/PnP4P/8 b - - 1 40`

Game (full game at ply): http://localhost:5173/analysis?game_id=681775&ply=78

FEN (free-play from line start): http://localhost:5173/analysis?fen=7R/p4p2/3k1p2/b3r3/5K2/1B3P2/PnP4P/8%20b%20-%20-%201%2040

#### Case 238 — CLEARANCE (allowed, depth 4)

Moves (SAN): `7. Nc3 Qd8 8. d5 Ne5 9. Bd4 Ned7 10. Nf3 g6 11. Bc4 Bh6`

FEN (line start): `r1b1kb1r/pp2pppp/2n2n2/3q4/3P4/4B3/PP3PPP/RN1QKBNR w - - 1 7`

Game (full game at ply): http://localhost:5173/analysis?game_id=681798&ply=11

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1b1kb1r/pp2pppp/2n2n2/3q4/3P4/4B3/PP3PPP/RN1QKBNR%20w%20-%20-%201%207

#### Case 239 — DISCOVERED_ATTACK (missed, depth 7)

Moves (SAN): `6... d6 7. Nc3 a6 8. a4 d5 9. Ba2 dxe4 10. dxe4 Qxd1+ 11. Rxd1 b5 12. Nf3`

FEN (line start): `r1bqkb1r/pp1p1p1p/2n1pnp1/1Np5/2B1PB2/3P4/PPP2PPP/R2QK1NR b - - 0 6`

Game (full game at ply): http://localhost:5173/analysis?game_id=681803&ply=11

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1bqkb1r/pp1p1p1p/2n1pnp1/1Np5/2B1PB2/3P4/PPP2PPP/R2QK1NR%20b%20-%20-%200%206

#### Case 240 — CLEARANCE (allowed, depth 10)

Moves (SAN): `13. Qe2 b5 14. Bb3 h6 15. Bxf6+ Bxf6 16. c3 Kf8`

FEN (line start): `2br4/1pq1kpbp/p1n1pnp1/2p1p1B1/2B5/3P1N2/PPP2PPP/R2QK2R w - - 1 13`

Game (full game at ply): http://localhost:5173/analysis?game_id=681803&ply=23

FEN (free-play from line start): http://localhost:5173/analysis?fen=2br4/1pq1kpbp/p1n1pnp1/2p1p1B1/2B5/3P1N2/PPP2PPP/R2QK2R%20w%20-%20-%201%2013

#### Case 241 — TRAPPED_PIECE (missed, depth 4)

Moves (SAN): `13... b5 14. Bb3 c4 15. a4 cxb3 16. axb5 axb5 17. Re1 Kf8 18. c3 h6 19. Bh4`

FEN (line start): `2br4/1pq1kpbp/p1n1pnp1/2p1p1B1/2B5/3P1N2/PPP2PPP/R2Q1RK1 b - - 0 13`

Game (full game at ply): http://localhost:5173/analysis?game_id=681803&ply=25

FEN (free-play from line start): http://localhost:5173/analysis?fen=2br4/1pq1kpbp/p1n1pnp1/2p1p1B1/2B5/3P1N2/PPP2PPP/R2Q1RK1%20b%20-%20-%200%2013

#### Case 242 — FORK (missed, depth 2)

Moves (SAN): `28... Bb4 29. h4 Bc3 30. Qf4 Bxa1 31. Rxa1 Rd4 32. Qe5 Rxc4 33. Re1 h5 34. Qa1`

FEN (line start): `2b3k1/3q1p1p/p2b1Qp1/8/2P5/3r4/P4PPP/R3R1K1 b - - 0 28`

Game (full game at ply): http://localhost:5173/analysis?game_id=681803&ply=55

FEN (free-play from line start): http://localhost:5173/analysis?fen=2b3k1/3q1p1p/p2b1Qp1/8/2P5/3r4/P4PPP/R3R1K1%20b%20-%20-%200%2028

#### Case 243 — CLEARANCE (missed, depth 8)

Moves (SAN): `17. Nxe7+ Kf7 18. axb3 Qd6 19. Qxd6 cxd6 20. Nd5 Bxb2 21. Re7+ Kg8 22. Ra2 Bh8`

FEN (line start): `r2q1rk1/2p1n1bp/p5p1/1p1N1pB1/8/1n3P1P/PPP2P2/R2QR1K1 w - - 0 17`

Game (full game at ply): http://localhost:5173/analysis?game_id=681804&ply=32

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2q1rk1/2p1n1bp/p5p1/1p1N1pB1/8/1n3P1P/PPP2P2/R2QR1K1%20w%20-%20-%200%2017

#### Case 244 — CLEARANCE (missed, depth 10)

Moves (SAN): `14... Be6 15. h3 Bb6 16. Rfe1 Rad8 17. Ba4 g6 18. Qh6+ Ke7 19. Nf1 Rh8 20. Qg5`

FEN (line start): `r1b1rk2/pp3ppQ/2n2q2/2bp4/8/2P2N2/PPBN1PPP/R4RK1 b - - 0 14`

Game (full game at ply): http://localhost:5173/analysis?game_id=681818&ply=27

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1b1rk2/pp3ppQ/2n2q2/2bp4/8/2P2N2/PPBN1PPP/R4RK1%20b%20-%20-%200%2014

#### Case 245 — CLEARANCE (missed, depth 2)

Moves (SAN): `15... Be6 16. Ba4 Rac8 17. Nb3 Qh6 18. Qd3 Kg8 19. Re2 Rf8 20. Rfe1 Ne7 21. g3`

FEN (line start): `r1b1rk2/p4ppQ/1pn2q2/2bp4/8/2P2N2/PPBN1PPP/4RRK1 b - - 0 15`

Game (full game at ply): http://localhost:5173/analysis?game_id=681818&ply=29

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1b1rk2/p4ppQ/1pn2q2/2bp4/8/2P2N2/PPBN1PPP/4RRK1%20b%20-%20-%200%2015

#### Case 246 — CLEARANCE (allowed, depth 8)

Moves (SAN): `6... Kh8 7. a3 Qe8 8. Bxf6 Rxf6 9. c4 d6 10. Nc3 Be6 11. b4 Bb6 12. Be2`

FEN (line start): `rnbq1rk1/pppp2pp/5n2/2b3B1/8/4PN2/PPP2PPP/RN1QKB1R b - - 0 6`

Game (full game at ply): http://localhost:5173/analysis?game_id=681821&ply=10

FEN (free-play from line start): http://localhost:5173/analysis?fen=rnbq1rk1/pppp2pp/5n2/2b3B1/8/4PN2/PPP2PPP/RN1QKB1R%20b%20-%20-%200%206

#### Case 247 — CLEARANCE (missed, depth 6)

Moves (SAN): `6. Bxf6 Bxf2+ 7. Kxf2 Qxf6 8. e3 d5 9. Be2 g5 10. Ke1 Nc6 11. Qxd5+ Kh8`

FEN (line start): `rnbq1rk1/pppp2pp/5n2/2b3B1/8/5N2/PPP1PPPP/RN1QKB1R w - - 0 6`

Game (full game at ply): http://localhost:5173/analysis?game_id=681821&ply=10

FEN (free-play from line start): http://localhost:5173/analysis?fen=rnbq1rk1/pppp2pp/5n2/2b3B1/8/5N2/PPP1PPPP/RN1QKB1R%20w%20-%20-%200%206

#### Case 248 — SKEWER (allowed, depth 10)

Moves (SAN): `21... Qd7 22. Rfe1 Nf4 23. Qf1 a6 24. Na3 Rxc1 25. Rxc1 Qa4 26. Nc4 Qxa2 27. Kh2`

FEN (line start): `2rq3r/p4pk1/1p1p2p1/1N1Pp2n/1P2P3/3Q3P/P4PP1/2R2RK1 b - - 1 21`

Game (full game at ply): http://localhost:5173/analysis?game_id=681825&ply=40

FEN (free-play from line start): http://localhost:5173/analysis?fen=2rq3r/p4pk1/1p1p2p1/1N1Pp2n/1P2P3/3Q3P/P4PP1/2R2RK1%20b%20-%20-%201%2021

#### Case 249 — SACRIFICE (missed, depth 2)

Moves (SAN): `26. Qxh3 Rxh3 27. Ne8+ Kf8 28. Nd6 Rh8 29. f4 Qh4 30. f5 Qh2+ 31. Kf2 Qf4+`

FEN (line start): `7r/p2Q1pk1/1p1N2p1/3Pp1q1/1P2P3/7n/P4PP1/5RK1 w - - 0 26`

Game (full game at ply): http://localhost:5173/analysis?game_id=681825&ply=50

FEN (free-play from line start): http://localhost:5173/analysis?fen=7r/p2Q1pk1/1p1N2p1/3Pp1q1/1P2P3/7n/P4PP1/5RK1%20w%20-%20-%200%2026

#### Case 250 — FORK (allowed, depth 8)

Moves (SAN): `8... Bb4`

FEN (line start): `rn1qkbnr/pb3ppp/4p3/1p6/2pPP3/5N2/1P1NBPPP/R1BQK2R b - - 1 8`

Game (full game at ply): http://localhost:5173/analysis?game_id=681844&ply=14

FEN (free-play from line start): http://localhost:5173/analysis?fen=rn1qkbnr/pb3ppp/4p3/1p6/2pPP3/5N2/1P1NBPPP/R1BQK2R%20b%20-%20-%201%208

#### Case 251 — SACRIFICE (allowed, depth 10)

Moves (SAN): `13... Bxf3 14. Qxf3 Qd5 15. Qg3 Nc6 16. Re1 a5 17. Qxg7`

FEN (line start): `rn1qk2r/p4ppp/4p3/1p6/2pPb3/5B1P/1P3PP1/R1BQ1RK1 b - - 1 13`

Game (full game at ply): http://localhost:5173/analysis?game_id=681844&ply=24

FEN (free-play from line start): http://localhost:5173/analysis?fen=rn1qk2r/p4ppp/4p3/1p6/2pPb3/5B1P/1P3PP1/R1BQ1RK1%20b%20-%20-%201%2013

#### Case 252 — CLEARANCE (missed, depth 6)

Moves (SAN): `20. Qxd4 e5 21. Qxd8 Rfxd8 22. Bg5 Rd6 23. Re1 Rd5 24. Bf6 Re8 25. f4 e4`

FEN (line start): `r2q1rk1/p6p/4p1p1/1p3p2/2pnQ2R/7P/1P3PP1/R1B3K1 w - - 0 20`

Game (full game at ply): http://localhost:5173/analysis?game_id=681844&ply=38

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2q1rk1/p6p/4p1p1/1p3p2/2pnQ2R/7P/1P3PP1/R1B3K1%20w%20-%20-%200%2020

#### Case 253 — FORK (allowed, depth 8)

Moves (SAN): `17. Be2 Bxe2 18. Rxe2 Qc6 19. Qd3 Nd7 20. Nd5 Nb6 21. Ne7+ Rxe7 22. Bxe7 Bd4+`

FEN (line start): `2r1r1k1/1pq2pbp/p2p1np1/2p3B1/P1P1PPb1/2NB4/1P4PP/R2QR1K1 w - - 1 17`

Game (full game at ply): http://localhost:5173/analysis?game_id=681848&ply=31

FEN (free-play from line start): http://localhost:5173/analysis?fen=2r1r1k1/1pq2pbp/p2p1np1/2p3B1/P1P1PPb1/2NB4/1P4PP/R2QR1K1%20w%20-%20-%201%2017

#### Case 254 — FORK (allowed, depth 4)

Moves (SAN): `21. cxb5 Qd7 22. e5 Qe6 23. Nf6+ Kg7 24. Nxe8+ Qxe8 25. bxa6 Qd8 26. Rac1 Be6`

FEN (line start): `2r1r1k1/5p1p/p1qp2p1/1ppN4/P1PbPPb1/3B4/1P1Q2PP/R3R2K w - - 0 21`

Game (full game at ply): http://localhost:5173/analysis?game_id=681848&ply=39

FEN (free-play from line start): http://localhost:5173/analysis?fen=2r1r1k1/5p1p/p1qp2p1/1ppN4/P1PbPPb1/3B4/1P1Q2PP/R3R2K%20w%20-%20-%200%2021

#### Case 255 — CLEARANCE (missed, depth 4)

Moves (SAN): `22... Rfe8 23. Qxb6 Re7 24. Re3 Rae8 25. c3 Qg5 26. a4 Rxe4 27. Rxe4 Rxe4 28. Qxb7`

FEN (line start): `r4rk1/1p3pp1/1ppp2q1/8/1PPQP3/P4R2/2P3P1/5RK1 b - - 0 22`

Game (full game at ply): http://localhost:5173/analysis?game_id=681849&ply=43

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4rk1/1p3pp1/1ppp2q1/8/1PPQP3/P4R2/2P3P1/5RK1%20b%20-%20-%200%2022

#### Case 256 — SKEWER (allowed, depth 2)

Moves (SAN): `9. Rb1 Qxa2 10. Rxb7 Nbd7 11. h3 Bxf3 12. Qxf3 Ne5 13. Qf4 Qd5 14. Nc3 Qd6`

FEN (line start): `rn2kb1r/pp2pppp/2p2n2/8/4N1b1/3BBN2/PqP2PPP/R2Q1RK1 w - - 1 9`

Game (full game at ply): http://localhost:5173/analysis?game_id=681893&ply=15

FEN (free-play from line start): http://localhost:5173/analysis?fen=rn2kb1r/pp2pppp/2p2n2/8/4N1b1/3BBN2/PqP2PPP/R2Q1RK1%20w%20-%20-%201%209

#### Case 257 — CLEARANCE (missed, depth 6)

Moves (SAN): `10... Qe5 11. Bf4 Qd4 12. Qe2 Nxe4 13. Bxe4 Qf6 14. Qd2 e5 15. Bg5 Qd6 16. Qa5`

FEN (line start): `rn2kb1r/pp2pppp/2p2n2/8/4N3/3BBP2/PqPQ1P1P/R4RK1 b - - 0 10`

Game (full game at ply): http://localhost:5173/analysis?game_id=681893&ply=19

FEN (free-play from line start): http://localhost:5173/analysis?fen=rn2kb1r/pp2pppp/2p2n2/8/4N3/3BBP2/PqPQ1P1P/R4RK1%20b%20-%20-%200%2010

#### Case 258 — SKEWER (allowed, depth 2)

Moves (SAN): `12. Rfb1 Qa3 13. Rxb7 Rd8 14. Rxa7 Qb2 15. Qe1 Bb4 16. Rb1 Bxe1 17. Nd6+ Ke7`

FEN (line start): `r3kb1r/pp1n1ppp/2p2n2/4p3/4NP2/3BB3/PqPQ1P1P/R4RK1 w - - 0 12`

Game (full game at ply): http://localhost:5173/analysis?game_id=681893&ply=21

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3kb1r/pp1n1ppp/2p2n2/4p3/4NP2/3BB3/PqPQ1P1P/R4RK1%20w%20-%20-%200%2012

#### Case 259 — SACRIFICE (allowed, depth 2)

Moves (SAN): `14. Qe2 Nxe4 15. Bf4 Nxd3 16. Qxe4+ Be7 17. cxd3 Qe6 18. Rxb7 Qxe4 19. dxe4 a5`

FEN (line start): `r3kb1r/pp3ppp/2p2n2/4n3/4N3/3BB3/q1PQ1P1P/1R3RK1 w - - 0 14`

Game (full game at ply): http://localhost:5173/analysis?game_id=681893&ply=25

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3kb1r/pp3ppp/2p2n2/4n3/4N3/3BB3/q1PQ1P1P/1R3RK1%20w%20-%20-%200%2014

#### Case 260 — FORK (missed, depth 0)

Moves (SAN): `13... Nf3+ 14. Kg2 Nxd2 15. Bxd2 Qe5 16. Nxf6+ gxf6 17. Rxb7 Rg8+ 18. Kh1 Qd5+ 19. f3`

FEN (line start): `r3kb1r/pp3ppp/2p2n2/4n3/4N3/3BB3/PqPQ1P1P/1R3RK1 b - - 0 13`

Game (full game at ply): http://localhost:5173/analysis?game_id=681893&ply=25

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3kb1r/pp3ppp/2p2n2/4n3/4N3/3BB3/PqPQ1P1P/1R3RK1%20b%20-%20-%200%2013

#### Case 261 — CAPTURING_DEFENDER (missed, depth 6)

Moves (SAN): `8... Bxf3 9. Bxf3 Nc6 10. Ne2 cxd4 11. Nxd4 Nxe5 12. c3 Nf6 13. g5 Ne4 14. Qa4+`

FEN (line start): `rn1qkbnr/pp3ppp/4p3/2ppP3/3Pb1P1/2N2N1P/PPP2PB1/R1BQK2R b - - 0 8`

Game (full game at ply): http://localhost:5173/analysis?game_id=681899&ply=15

FEN (free-play from line start): http://localhost:5173/analysis?fen=rn1qkbnr/pp3ppp/4p3/2ppP3/3Pb1P1/2N2N1P/PPP2PB1/R1BQK2R%20b%20-%20-%200%208

#### Case 262 — HANGING_PIECE (missed, depth 0)

Moves (SAN): `24... Rxc3`

FEN (line start): `1r4k1/1p1R2pp/p1n1p3/5P2/2P2P2/1PN1r2P/P7/5RK1 b - - 0 24`

Game (full game at ply): http://localhost:5173/analysis?game_id=681899&ply=47

FEN (free-play from line start): http://localhost:5173/analysis?fen=1r4k1/1p1R2pp/p1n1p3/5P2/2P2P2/1PN1r2P/P7/5RK1%20b%20-%20-%200%2024

#### Case 263 — PIN (missed, depth 0)

Moves (SAN): `11. Bxc6 Qxc6 12. e5 Nd7 13. Bd2 h6 14. Nxe6 Qxe6 15. f4`

FEN (line start): `r3k2r/1p1qppbp/p1n1bnp1/1B1p2N1/3PP3/2N4P/PP3PP1/R1BQ1RK1 w - - 0 11`

Game (full game at ply): http://localhost:5173/analysis?game_id=681901&ply=20

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3k2r/1p1qppbp/p1n1bnp1/1B1p2N1/3PP3/2N4P/PP3PP1/R1BQ1RK1%20w%20-%20-%200%2011

#### Case 264 — DISCOVERED_ATTACK (missed, depth 7)

Moves (SAN): `21. Qb3 Qd7 22. dxe5 b6 23. Rcc1 Nd5 24. e6 fxe6 25. Bxg7 Kxg7 26. Rc4 e5`

FEN (line start): `3rr1k1/1p3pbp/p2q1np1/2R1p1N1/PP1P4/7P/1B3PP1/3QR1K1 w - - 0 21`

Game (full game at ply): http://localhost:5173/analysis?game_id=681901&ply=40

FEN (free-play from line start): http://localhost:5173/analysis?fen=3rr1k1/1p3pbp/p2q1np1/2R1p1N1/PP1P4/7P/1B3PP1/3QR1K1%20w%20-%20-%200%2021

#### Case 265 — HANGING_PIECE (allowed, depth 0)

Moves (SAN): `34... Rxf3 35. Kg2 Rdf8 36. h4 Nd7 37. Ra2 R8f7 38. Rc2 Bc3 39. Ra2 h5 40. Ra6`

FEN (line start): `3r2k1/7p/1n2p1p1/4b3/8/1r3NPP/4RP1K/8 b - - 1 34`

Game (full game at ply): http://localhost:5173/analysis?game_id=681901&ply=66

FEN (free-play from line start): http://localhost:5173/analysis?fen=3r2k1/7p/1n2p1p1/4b3/8/1r3NPP/4RP1K/8%20b%20-%20-%201%2034

#### Case 266 — HANGING_PIECE (missed, depth 0)

Moves (SAN): `34. Nxe5 Ra8 35. Re2 Nd5 36. h4 Rb5 37. Nc6 Nb4 38. Ne5 Ra2 39. Rxa2 Nxa2`

FEN (line start): `3r2k1/7p/1n2p1p1/4b3/8/1r3NPP/R4P1K/8 w - - 0 34`

Game (full game at ply): http://localhost:5173/analysis?game_id=681901&ply=66

FEN (free-play from line start): http://localhost:5173/analysis?fen=3r2k1/7p/1n2p1p1/4b3/8/1r3NPP/R4P1K/8%20w%20-%20-%200%2034

#### Case 267 — CLEARANCE (allowed, depth 8)

Moves (SAN): `26. Rxf8+ Rxf8 27. Bc1 Qd5 28. Be3 Qc4 29. Qd2 Qb3 30. Re1 Rf5 31. Bf4 Qd5`

FEN (line start): `2k2r1r/1p1qbR2/p1p1p3/P1P1P3/1P1Pp2p/7P/1B4P1/R2Q2K1 w - - 1 26`

Game (full game at ply): http://localhost:5173/analysis?game_id=681902&ply=49

FEN (free-play from line start): http://localhost:5173/analysis?fen=2k2r1r/1p1qbR2/p1p1p3/P1P1P3/1P1Pp2p/7P/1B4P1/R2Q2K1%20w%20-%20-%201%2026

#### Case 268 — INTERFERENCE (missed, depth 4)

Moves (SAN): `15... f5 16. g3 bxc5 17. Bd3 cxd4 18. Bxe4 fxe4 19. Rxe4 Bb6 20. Qf3 Re8 21. Rxe8+`

FEN (line start): `r2q1rk1/p1bn1ppp/Bpp2p2/2P5/1P1Pb2N/8/P4PPP/R1BQR1K1 b - - 0 15`

Game (full game at ply): http://localhost:5173/analysis?game_id=681903&ply=29

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2q1rk1/p1bn1ppp/Bpp2p2/2P5/1P1Pb2N/8/P4PPP/R1BQR1K1%20b%20-%20-%200%2015

#### Case 269 — PIN (allowed, depth 0)

Moves (SAN): `21... Rae8 22. c4 Bf5 23. Qc3 Re6 24. d5 Rh6 25. e6 Qh4 26. Re5 Qxh2+ 27. Kf1`

FEN (line start): `r4rk1/1p4pp/2p5/p3P1q1/3P1p2/P1PQ1B1b/5PPP/R3R1K1 b - - 1 21`

Game (full game at ply): http://localhost:5173/analysis?game_id=681909&ply=40

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4rk1/1p4pp/2p5/p3P1q1/3P1p2/P1PQ1B1b/5PPP/R3R1K1%20b%20-%20-%201%2021

#### Case 270 — CLEARANCE (allowed, depth 2)

Moves (SAN): `15. e4 Nd7 16. Bg5 Qa5 17. Rc1 Nxc5 18. e5 Nd7 19. Qa4 Qxa4 20. Nxa4 Rec8`

FEN (line start): `rn1qr1k1/p4pbp/2p1p1p1/2Pp4/3P2b1/2N1PN2/P3BP2/R1BQ1RK1 w - - 0 15`

Game (full game at ply): http://localhost:5173/analysis?game_id=681912&ply=27

FEN (free-play from line start): http://localhost:5173/analysis?fen=rn1qr1k1/p4pbp/2p1p1p1/2Pp4/3P2b1/2N1PN2/P3BP2/R1BQ1RK1%20w%20-%20-%200%2015

#### Case 271 — SACRIFICE (missed, depth 6)

Moves (SAN): `14... e5 15. Nxe5 Bxe2 16. Nxe2 Rxe5 17. dxe5 Bxe5 18. Rb1 Qg5+ 19. Ng3 Bxg3 20. fxg3`

FEN (line start): `rn1qr1k1/p3ppbp/2p3p1/2Pp4/3P2b1/2N1PN2/P3BP2/R1BQ1RK1 b - - 0 14`

Game (full game at ply): http://localhost:5173/analysis?game_id=681912&ply=27

FEN (free-play from line start): http://localhost:5173/analysis?fen=rn1qr1k1/p3ppbp/2p3p1/2Pp4/3P2b1/2N1PN2/P3BP2/R1BQ1RK1%20b%20-%20-%200%2014

#### Case 272 — DISCOVERED_ATTACK (allowed, depth 3)

Moves (SAN): `21. Rab1 Rb8 22. Ba3 Ne6 23. Rxb8 Qxb8 24. Ne2 h5 25. Bc1 a6 26. Rd1 Qb5`

FEN (line start): `r2qr1k1/p4pbp/2p3p1/2np4/8/2N2Q2/PB3P1N/R4RK1 w - - 0 21`

Game (full game at ply): http://localhost:5173/analysis?game_id=681912&ply=39

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qr1k1/p4pbp/2p3p1/2np4/8/2N2Q2/PB3P1N/R4RK1%20w%20-%20-%200%2021

#### Case 273 — FORK (missed, depth 4)

Moves (SAN): `20... Ne5 21. Qg3 Nc4 22. Rab1 Nd2 23. Bc1 Nxf1 24. Nxf1 d4 25. Na4 Qd5 26. Rb7`

FEN (line start): `r2qr1k1/p2n1pbp/2p3p1/2Pp4/8/2N2Q2/PB3P1N/R4RK1 b - - 0 20`

Game (full game at ply): http://localhost:5173/analysis?game_id=681912&ply=39

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qr1k1/p2n1pbp/2p3p1/2Pp4/8/2N2Q2/PB3P1N/R4RK1%20b%20-%20-%200%2020

#### Case 274 — CLEARANCE (missed, depth 10)

Moves (SAN): `23... Rxb1 24. Qxc5 h5 25. Kg2 Qb6 26. Qd6 d4 27. Nf3 c5 28. Qd5 Qe6 29. Qg5`

FEN (line start): `1r1qr1k1/p4p1p/2p3p1/2np4/8/2Q5/P4P1N/1RB2RK1 b - - 0 23`

Game (full game at ply): http://localhost:5173/analysis?game_id=681912&ply=45

FEN (free-play from line start): http://localhost:5173/analysis?fen=1r1qr1k1/p4p1p/2p3p1/2np4/8/2Q5/P4P1N/1RB2RK1%20b%20-%20-%200%2023

#### Case 275 — PIN (allowed, depth 4)

Moves (SAN): `9. Nxd4 Bg6 10. Bb5+ Nd7`

FEN (line start): `rn2kbnr/pp3ppp/4p3/3pPbB1/1q1p4/2N2N2/PPP2PPP/R2QKB1R w - - 0 9`

Game (full game at ply): http://localhost:5173/analysis?game_id=681915&ply=15

FEN (free-play from line start): http://localhost:5173/analysis?fen=rn2kbnr/pp3ppp/4p3/3pPbB1/1q1p4/2N2N2/PPP2PPP/R2QKB1R%20w%20-%20-%200%209

#### Case 276 — FORK (allowed, depth 0)

Moves (SAN): `23. Rc3+ Kb7 24. Rxc2 Rxa3 25. Ke2 Ne4 26. Rhc1 Nc5 27. Rb1 Kc6 28. Rcb2 Ra6`

FEN (line start): `r7/5ppp/1pk1pn2/3p4/5P2/PR6/2b3PP/4K2R w - - 0 23`

Game (full game at ply): http://localhost:5173/analysis?game_id=681915&ply=43

FEN (free-play from line start): http://localhost:5173/analysis?fen=r7/5ppp/1pk1pn2/3p4/5P2/PR6/2b3PP/4K2R%20w%20-%20-%200%2023

#### Case 277 — SKEWER (allowed, depth 2)

Moves (SAN): `40. Rc5+ Kd6 41. Rxf5 Rb2 42. Rxd4+ Ke6 43. Rfxf4 Rb3+ 44. Ke2 g5 45. Rf3 Rb2+`

FEN (line start): `8/6p1/7p/4kp2/R2p1p1P/2R2K2/3r2P1/8 w - - 0 40`

Game (full game at ply): http://localhost:5173/analysis?game_id=681915&ply=77

FEN (free-play from line start): http://localhost:5173/analysis?fen=8/6p1/7p/4kp2/R2p1p1P/2R2K2/3r2P1/8%20w%20-%20-%200%2040

#### Case 278 — MATE (allowed, depth 10)

Moves (SAN): `51. Rd7+ Kc8 52. Kxf2 f4 53. Rxd2 f3 54. Kxf3 h5 55. Kf4 Kb8 56. Rd8#`

FEN (line start): `3k4/4R2R/7p/5p2/7P/4K3/3p1rP1/8 w - - 1 51`

Game (full game at ply): http://localhost:5173/analysis?game_id=681915&ply=99

FEN (free-play from line start): http://localhost:5173/analysis?fen=3k4/4R2R/7p/5p2/7P/4K3/3p1rP1/8%20w%20-%20-%201%2051

#### Case 279 — PROMOTION (missed, depth 6)

Moves (SAN): `50... Kf8 51. Rd7 Kg8 52. Rh8+ Kxh8 53. Kxf2 d1=Q 54. Rxd1 h5 55. Kf3 Kg7 56. Kf4`

FEN (line start): `4k3/4R2R/7p/5p2/7P/4K3/3p1rP1/8 b - - 0 50`

Game (full game at ply): http://localhost:5173/analysis?game_id=681915&ply=99

FEN (free-play from line start): http://localhost:5173/analysis?fen=4k3/4R2R/7p/5p2/7P/4K3/3p1rP1/8%20b%20-%20-%200%2050

#### Case 280 — SACRIFICE (missed, depth 10)

Moves (SAN): `10. h3 e5 11. dxe5 Nc6 12. Bg2 Nxe5`

FEN (line start): `rnbqr1k1/ppp1pp1p/3p1bpB/8/2PP2P1/2N2N2/PP3P1P/R2QKB1R w - - 0 10`

Game (full game at ply): http://localhost:5173/analysis?game_id=681958&ply=18

FEN (free-play from line start): http://localhost:5173/analysis?fen=rnbqr1k1/ppp1pp1p/3p1bpB/8/2PP2P1/2N2N2/PP3P1P/R2QKB1R%20w%20-%20-%200%2010

#### Case 281 — CLEARANCE (allowed, depth 4)

Moves (SAN): `22. hxg6+ fxg6 23. d5 Rfd8 24. Qc4 b5 25. Qxc5 Qa2 26. Ra1 Rxd5+ 27. Bd4 Rxd4+`

FEN (line start): `r4r2/pp3pbk/5pp1/2p4P/3P1Q2/2PKBN1P/1q3P2/3R3R w - - 1 22`

Game (full game at ply): http://localhost:5173/analysis?game_id=681963&ply=41

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4r2/pp3pbk/5pp1/2p4P/3P1Q2/2PKBN1P/1q3P2/3R3R%20w%20-%20-%201%2022

#### Case 282 — ATTRACTION (missed, depth 0)

Moves (SAN): `21... c4+ 22. Kxc4 Rfc8+ 23. Qc7 Rxc7+ 24. Kd3 Rxc3+ 25. Ke4 Bh6 26. Ne5 Bxe3 27. Rd3`

FEN (line start): `r4rk1/pp3pb1/5pp1/2p4P/3P1Q2/2PKBN1P/1q3P2/3R3R b - - 0 21`

Game (full game at ply): http://localhost:5173/analysis?game_id=681963&ply=41

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4rk1/pp3pb1/5pp1/2p4P/3P1Q2/2PKBN1P/1q3P2/3R3R%20b%20-%20-%200%2021

#### Case 283 — MATE (allowed, depth 6)

Moves (SAN): `20. Rac1+ Qc4 21. Rxc4+ dxc4 22. Bb6 Kb8 23. Qc7#`

FEN (line start): `r1k4r/1b3Q1p/p3p1p1/3p4/4q3/NP2B3/P4PPP/R4RK1 w - - 1 20`

Game (full game at ply): http://localhost:5173/analysis?game_id=681977&ply=37

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1k4r/1b3Q1p/p3p1p1/3p4/4q3/NP2B3/P4PPP/R4RK1%20w%20-%20-%201%2020

#### Case 284 — SACRIFICE (missed, depth 4)

Moves (SAN): `19... Kd6 20. Rac1 Rhc8 21. Qxb7 Ke5 22. Rxc8 Rxc8 23. Qxc8 g5 24. Qc3+ Kf5 25. h3`

FEN (line start): `r6r/1b1k1Q1p/p3p1p1/3p4/4q3/NP2B3/P4PPP/R4RK1 b - - 0 19`

Game (full game at ply): http://localhost:5173/analysis?game_id=681977&ply=37

FEN (free-play from line start): http://localhost:5173/analysis?fen=r6r/1b1k1Q1p/p3p1p1/3p4/4q3/NP2B3/P4PPP/R4RK1%20b%20-%20-%200%2019

#### Case 285 — TRAPPED_PIECE (missed, depth 4)

Moves (SAN): `15. Ne5 Nf6 16. d6 Nc6 17. dxe7 Qxe7 18. Nxc6 Bxc6 19. Bf1 Qc7 20. Bg5 Rad8`

FEN (line start): `rn1q1rk1/1p1bbppp/p7/2pP3n/8/P1N2N1P/1P2BPP1/R1BQR1K1 w - - 0 15`

Game (full game at ply): http://localhost:5173/analysis?game_id=681993&ply=28

FEN (free-play from line start): http://localhost:5173/analysis?fen=rn1q1rk1/1p1bbppp/p7/2pP3n/8/P1N2N1P/1P2BPP1/R1BQR1K1%20w%20-%20-%200%2015

#### Case 286 — CLEARANCE (missed, depth 6)

Moves (SAN): `18. Bd3 Rc8 19. Rc1 Be6 20. Qe2 Re8 21. Rcd1 Qc7 22. Ne4 Nxe4 23. Bxe4 Bc4`

FEN (line start): `r2q1rk1/3bbppp/p1n2n2/1p6/1P6/P1N2N1P/1B2BPP1/R2QR1K1 w - - 0 18`

Game (full game at ply): http://localhost:5173/analysis?game_id=681993&ply=34

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2q1rk1/3bbppp/p1n2n2/1p6/1P6/P1N2N1P/1B2BPP1/R2QR1K1%20w%20-%20-%200%2018

#### Case 287 — DEFLECTION (allowed, depth 6)

Moves (SAN): `43. g4+ hxg4 44. hxg4+ Ke5 45. Bc3+ Kd6 46. Kxe4 Kc6 47. Kxd3 Kb6 48. Ke4 Kxa6`

FEN (line start): `8/5p2/P7/5kpp/1B2b3/3pK1PP/6P1/8 w - - 0 43`

Game (full game at ply): http://localhost:5173/analysis?game_id=682005&ply=83

FEN (free-play from line start): http://localhost:5173/analysis?fen=8/5p2/P7/5kpp/1B2b3/3pK1PP/6P1/8%20w%20-%20-%200%2043

#### Case 288 — MATE (allowed, depth 8)

Moves (SAN): `49. Kxd2 Bd5 50. Qc5 Ka2 51. Qa5+ Kb3 52. Qb4+ Ka2 53. Qb2#`

FEN (line start): `2Q5/5p2/8/6p1/4b1P1/1kB1K3/3p2P1/8 w - - 1 49`

Game (full game at ply): http://localhost:5173/analysis?game_id=682005&ply=95

FEN (free-play from line start): http://localhost:5173/analysis?fen=2Q5/5p2/8/6p1/4b1P1/1kB1K3/3p2P1/8%20w%20-%20-%201%2049

#### Case 289 — SACRIFICE (missed, depth 10)

Moves (SAN): `48... Kb5 49. Qd7+ Bc6 50. Qxd2 f6 51. Qd3+ Kb6 52. Bd4+ Kc7 53. Bxf6 Kb7 54. Be5`

FEN (line start): `2Q5/5p2/8/6p1/2k1b1P1/2B1K3/3p2P1/8 b - - 0 48`

Game (full game at ply): http://localhost:5173/analysis?game_id=682005&ply=95

FEN (free-play from line start): http://localhost:5173/analysis?fen=2Q5/5p2/8/6p1/2k1b1P1/2B1K3/3p2P1/8%20b%20-%20-%200%2048

#### Case 290 — FORK (allowed, depth 0)

Moves (SAN): `15. dxe5 Nxe5 16. Nxe5 Rxe5 17. Qd2 Rae8 18. Rad1 h6 19. Nxd5 Nxd5 20. Bxd5 Qg6`

FEN (line start): `r3r1k1/5ppp/p1nq1n2/1p1ppb2/3P4/PBN2N1P/1PP2PP1/R3QRK1 w - - 0 15`

Game (full game at ply): http://localhost:5173/analysis?game_id=682008&ply=27

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3r1k1/5ppp/p1nq1n2/1p1ppb2/3P4/PBN2N1P/1PP2PP1/R3QRK1%20w%20-%20-%200%2015

#### Case 291 — FORK (allowed, depth 0)

Moves (SAN): `23. g4 Rxf4 24. gxh5 Re6 25. Re3 Rxh4 26. f3 Bf5 27. Rc3 g6 28. Rc7 Rxh5`

FEN (line start): `4r1k1/5ppp/p7/1p1p1r1q/4bQ1P/PB4P1/1PP2P2/4RRK1 w - - 1 23`

Game (full game at ply): http://localhost:5173/analysis?game_id=682008&ply=43

FEN (free-play from line start): http://localhost:5173/analysis?fen=4r1k1/5ppp/p7/1p1p1r1q/4bQ1P/PB4P1/1PP2P2/4RRK1%20w%20-%20-%201%2023

#### Case 292 — CLEARANCE (missed, depth 2)

Moves (SAN): `11... e6 12. f5 Bb4+ 13. Kf1 exf5 14. g5 f4 15. Ne2 Bd3 16. Bxf4 Nc6 17. Kf2`

FEN (line start): `rn1qkb1r/pp2pppp/6b1/3pP3/2pP1PP1/8/PP4BP/R1BQK1NR b - - 0 11`

Game (full game at ply): http://localhost:5173/analysis?game_id=682050&ply=21

FEN (free-play from line start): http://localhost:5173/analysis?fen=rn1qkb1r/pp2pppp/6b1/3pP3/2pP1PP1/8/PP4BP/R1BQK1NR%20b%20-%20-%200%2011

#### Case 293 — CLEARANCE (allowed, depth 8)

Moves (SAN): `11... Bxf3 12. gxf3 Rg6+ 13. Kh2 Nc6 14. Ne2 e5 15. f4 Qf6 16. dxe5 dxe5 17. Qd5+`

FEN (line start): `rn1q2k1/ppp1p1bp/3p1r2/7p/2PP2b1/2N2N1P/PP3PP1/R1BQ1RK1 b - - 0 11`

Game (full game at ply): http://localhost:5173/analysis?game_id=682060&ply=20

FEN (free-play from line start): http://localhost:5173/analysis?fen=rn1q2k1/ppp1p1bp/3p1r2/7p/2PP2b1/2N2N1P/PP3PP1/R1BQ1RK1%20b%20-%20-%200%2011

#### Case 294 — PIN (allowed, depth 2)

Moves (SAN): `18... Bxf4+ 19. Ng3 h4 20. Bxf4 Qxf4 21. Qc2 hxg3+ 22. fxg3 Qf7 23. Qe2 Nd7 24. Rf1`

FEN (line start): `rn4k1/pp2p3/3p2p1/2pPbq1p/2P1NP2/7P/PP3P1K/R1BQ4 b - - 0 18`

Game (full game at ply): http://localhost:5173/analysis?game_id=682060&ply=34

FEN (free-play from line start): http://localhost:5173/analysis?fen=rn4k1/pp2p3/3p2p1/2pPbq1p/2P1NP2/7P/PP3P1K/R1BQ4%20b%20-%20-%200%2018

#### Case 295 — FORK (allowed, depth 8)

Moves (SAN): `10. Bg5 Bg7 11. Bxf6 Bxf6 12. Nxd5 Bxd4 13. Nb4 Nxb4 14. Qxd4 Qxd4 15. Nxd4 Rd8`

FEN (line start): `r2qkb1r/4pp1p/p1n2np1/1p1p4/3P2b1/1BN2N2/PPP2PPP/R1BQ1RK1 w - - 0 10`

Game (full game at ply): http://localhost:5173/analysis?game_id=682083&ply=17

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qkb1r/4pp1p/p1n2np1/1p1p4/3P2b1/1BN2N2/PPP2PPP/R1BQ1RK1%20w%20-%20-%200%2010

#### Case 296 — CLEARANCE (missed, depth 8)

Moves (SAN): `9... e6 10. Ne2 Bxf3 11. gxf3 Bd6 12. Kh1 Nh5 13. Rg1 Qf6 14. Qd3 Qh4 15. Rg2`

FEN (line start): `r2qkb1r/4pppp/p1n2n2/1p1p4/3P2b1/1BN2N2/PPP2PPP/R1BQ1RK1 b - - 0 9`

Game (full game at ply): http://localhost:5173/analysis?game_id=682083&ply=17

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qkb1r/4pppp/p1n2n2/1p1p4/3P2b1/1BN2N2/PPP2PPP/R1BQ1RK1%20b%20-%20-%200%209

#### Case 297 — CAPTURING_DEFENDER (missed, depth 2)

Moves (SAN): `10... Bxf3 11. Qxf3 Nxd4 12. Qd3 Nxb3 13. axb3 b4 14. Na4 Bg7 15. Nc5`

FEN (line start): `r2qkb1r/4pp1p/p1n2np1/1p1p4/3P2b1/1BN2N1P/PPP2PP1/R1BQ1RK1 b - - 0 10`

Game (full game at ply): http://localhost:5173/analysis?game_id=682083&ply=19

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qkb1r/4pp1p/p1n2np1/1p1p4/3P2b1/1BN2N1P/PPP2PP1/R1BQ1RK1%20b%20-%20-%200%2010

#### Case 298 — EN_PASSANT (missed, depth 4)

Moves (SAN): `15... b4 16. Ne2 Bg7 17. c4 bxc3 18. bxc3 Ne4 19. Be3 Nxc3 20. Nxc3 Bxc3 21. Ra4`

FEN (line start): `r2qkb1r/4pp2/p4np1/1p1p4/8/1PN3P1/1PP2PQ1/R1B2RK1 b - - 0 15`

Game (full game at ply): http://localhost:5173/analysis?game_id=682083&ply=29

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qkb1r/4pp2/p4np1/1p1p4/8/1PN3P1/1PP2PQ1/R1B2RK1%20b%20-%20-%200%2015

#### Case 299 — FORK (allowed, depth 4)

Moves (SAN): `17. Nxd5 Rc8 18. Rfe1 e6 19. Nb6 Qc7 20. Nxc8 Qxc8 21. Rad1 Be7 22. Bxe7 Kxe7`

FEN (line start): `r3kb1r/3qpp2/p5p1/1p1p2B1/6n1/1PN3P1/1PP2PQ1/R4RK1 w - - 1 17`

Game (full game at ply): http://localhost:5173/analysis?game_id=682083&ply=31

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3kb1r/3qpp2/p5p1/1p1p2B1/6n1/1PN3P1/1PP2PQ1/R4RK1%20w%20-%20-%201%2017

#### Case 300 — FORK (allowed, depth 0)

Moves (SAN): `18. Nc7+ Kd7 19. Qb7 Qxf2+ 20. Rxf2 Rh1+ 21. Qxh1 Nxf2 22. Kxf2 Ra7 23. Nxa6 e5`

FEN (line start): `r3kb1r/4pp2/p5p1/1p1N1qB1/6n1/1P4P1/1PP2PQ1/R4RK1 w - - 1 18`

Game (full game at ply): http://localhost:5173/analysis?game_id=682083&ply=33

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3kb1r/4pp2/p5p1/1p1N1qB1/6n1/1P4P1/1PP2PQ1/R4RK1%20w%20-%20-%201%2018

#### Case 301 — MATE (allowed, depth 6)

Moves (SAN): `19. Nc7+ Kd7 20. Rfd1+ Qd3 21. Rxd3+ Kc8 22. Qxa8#`

FEN (line start): `r3kb2/4pp2/p5p1/1p1N1q2/5Bn1/1P4P1/1PP2PQr/R4RK1 w - - 1 19`

Game (full game at ply): http://localhost:5173/analysis?game_id=682083&ply=35

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3kb2/4pp2/p5p1/1p1N1q2/5Bn1/1P4P1/1PP2PQr/R4RK1%20w%20-%20-%201%2019

#### Case 302 — SACRIFICE (missed, depth 4)

Moves (SAN): `18... Rc8 19. Nb6 Bh6 20. Nxc8 Qxc8 21. Bxh6 Rxh6 22. c4 bxc4 23. Rfc1 Ne5 24. Qd5`

FEN (line start): `r3kb1r/4pp2/p5p1/1p1N1q2/5Bn1/1P4P1/1PP2PQ1/R4RK1 b - - 0 18`

Game (full game at ply): http://localhost:5173/analysis?game_id=682083&ply=35

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3kb1r/4pp2/p5p1/1p1N1q2/5Bn1/1P4P1/1PP2PQ1/R4RK1%20b%20-%20-%200%2018

#### Case 303 — ATTRACTION (missed, depth 4)

Moves (SAN): `19... Rc8 20. Rae1 Rxf2 21. Rxf2 Nxf2 22. Kxf2 Rxc2+ 23. Kg1 e6 24. g4 Bc5+ 25. Kh1`

FEN (line start): `r3kb2/4pp2/p5p1/1p1N1q2/5Bn1/1P3QP1/1PP2P1r/R4RK1 b - - 0 19`

Game (full game at ply): http://localhost:5173/analysis?game_id=682083&ply=37

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3kb2/4pp2/p5p1/1p1N1q2/5Bn1/1P3QP1/1PP2P1r/R4RK1%20b%20-%20-%200%2019

#### Case 304 — DISCOVERED_ATTACK (missed, depth 9)

Moves (SAN): `20... Qc5+ 21. Kh1 Rf2 22. Qe1 Ng4 23. h3 Qe3 24. Nf3 d4 25. hxg4 Bxf3 26. Qxe3`

FEN (line start): `5rk1/pb2q1pp/4p2n/1P1pP3/2p5/2P5/P1BNQ1PP/R5K1 b - - 0 20`

Game (full game at ply): http://localhost:5173/analysis?game_id=682103&ply=39

FEN (free-play from line start): http://localhost:5173/analysis?fen=5rk1/pb2q1pp/4p2n/1P1pP3/2p5/2P5/P1BNQ1PP/R5K1%20b%20-%20-%200%2020

#### Case 305 — CLEARANCE (allowed, depth 4)

Moves (SAN): `24. Bxf5 exf5 25. Nd4 Bc8 26. Qf3 f4 27. gxf4 h6 28. Re1 Kh8 29. e6 Nf6`

FEN (line start): `5rk1/pb4pp/4p3/1P1pPq2/2p3nP/2P2NP1/P1B1Q3/R5K1 w - - 1 24`

Game (full game at ply): http://localhost:5173/analysis?game_id=682103&ply=45

FEN (free-play from line start): http://localhost:5173/analysis?fen=5rk1/pb4pp/4p3/1P1pPq2/2p3nP/2P2NP1/P1B1Q3/R5K1%20w%20-%20-%201%2024

#### Case 306 — SACRIFICE (allowed, depth 6)

Moves (SAN): `27. Kg1 g5 28. Nxd4 Rxf1+ 29. Qxf1 Nxf1 30. Kxf1 gxh4 31. gxh4 Kf7 32. a4 a6`

FEN (line start): `6k1/pb4pp/4p3/1P2Pr2/2pp3P/2P1nNP1/P3Q1K1/5R2 w - - 1 27`

Game (full game at ply): http://localhost:5173/analysis?game_id=682103&ply=51

FEN (free-play from line start): http://localhost:5173/analysis?fen=6k1/pb4pp/4p3/1P2Pr2/2pp3P/2P1nNP1/P3Q1K1/5R2%20w%20-%20-%201%2027

#### Case 307 — PROMOTION (allowed, depth 8)

Moves (SAN): `57. Kb5 g3 58. a6 Bc8 59. b7 Bd7+ 60. Kb4 g2 61. c8=Q g1=R 62. Qxd7+ Ke4`

FEN (line start): `8/1bP5/1P6/P3pk2/2K3p1/8/8/8 w - - 0 57`

Game (full game at ply): http://localhost:5173/analysis?game_id=682103&ply=111

FEN (free-play from line start): http://localhost:5173/analysis?fen=8/1bP5/1P6/P3pk2/2K3p1/8/8/8%20w%20-%20-%200%2057

#### Case 308 — TRAPPED_PIECE (missed, depth 2)

Moves (SAN): `10. Rd1 Bg4 11. Rxd8+ Rxd8 12. Qb5 Bxf3 13. gxf3 fxe5 14. Qxb7 Nd4 15. Bb5+ Kf7`

FEN (line start): `r1bqk1nr/ppp1b1pp/2n2p2/4P3/5B2/2N2N2/PPP1Q1PP/R3KB1R w - - 0 10`

Game (full game at ply): http://localhost:5173/analysis?game_id=682106&ply=18

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1bqk1nr/ppp1b1pp/2n2p2/4P3/5B2/2N2N2/PPP1Q1PP/R3KB1R%20w%20-%20-%200%2010

#### Case 309 — CAPTURING_DEFENDER (missed, depth 4)

Moves (SAN): `14. Nb5 Qc6 15. Qxc6 Nxc6 16. Nxc7 Rb8 17. d5 Nce5 18. Nc5 b6 19. N5e6 Rf7`

FEN (line start): `rnb2r1k/ppp3pp/3q1pn1/8/2QP4/2NN4/PPP3PP/2KR1B1R w - - 0 14`

Game (full game at ply): http://localhost:5173/analysis?game_id=682110&ply=26

FEN (free-play from line start): http://localhost:5173/analysis?fen=rnb2r1k/ppp3pp/3q1pn1/8/2QP4/2NN4/PPP3PP/2KR1B1R%20w%20-%20-%200%2014

#### Case 310 — CLEARANCE (missed, depth 4)

Moves (SAN): `13... cxd4 14. Qxd4 Nc6 15. Qd5 Rad8 16. Bf4 Qc7 17. Qc4 Qb6 18. Qb3 Qa6 19. Red1`

FEN (line start): `rn3rk1/pp1q1ppp/3b1p2/2p5/3P4/6P1/PPPQ1PNP/R1B1R1K1 b - - 0 13`

Game (full game at ply): http://localhost:5173/analysis?game_id=682111&ply=25

FEN (free-play from line start): http://localhost:5173/analysis?fen=rn3rk1/pp1q1ppp/3b1p2/2p5/3P4/6P1/PPPQ1PNP/R1B1R1K1%20b%20-%20-%200%2013

#### Case 311 — FORK (missed, depth 0)

Moves (SAN): `15... Nc4 16. Qd3 Nxe3 17. Nxe3 Rad8 18. Bd2 Rfe8 19. Rd1 h5 20. b3 g6 21. a4`

FEN (line start): `r4rk1/pp1q1ppp/3b1p2/2pPn3/8/4R1P1/PPPQ1PNP/R1B3K1 b - - 0 15`

Game (full game at ply): http://localhost:5173/analysis?game_id=682111&ply=29

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4rk1/pp1q1ppp/3b1p2/2pPn3/8/4R1P1/PPPQ1PNP/R1B3K1%20b%20-%20-%200%2015

#### Case 312 — INTERMEZZO (missed, depth 6)

Moves (SAN): `21... Bxe3 22. fxe3 Qh5 23. Bxe5 b5 24. Rf4 Qxe5 25. Nf3 Qd6 26. Rd4 Rfe8 27. Kg2`

FEN (line start): `2r2rk1/1p3ppp/5p2/2bPn3/R5qN/1P2R1P1/1BPQ1P1P/6K1 b - - 0 21`

Game (full game at ply): http://localhost:5173/analysis?game_id=682111&ply=41

FEN (free-play from line start): http://localhost:5173/analysis?fen=2r2rk1/1p3ppp/5p2/2bPn3/R5qN/1P2R1P1/1BPQ1P1P/6K1%20b%20-%20-%200%2021

#### Case 313 — PIN (missed, depth 0)

Moves (SAN): `25... g5 26. fxg6 hxg6 27. Rae1 Re5 28. Rc1 Re4 29. Rc4 Rf4 30. Qc3 Rxf3 31. Rxf3`

FEN (line start): `3rr1k1/pp3ppp/1b3p2/5P2/3B4/5NqP/PP1Q2P1/R4RK1 b - - 0 25`

Game (full game at ply): http://localhost:5173/analysis?game_id=682127&ply=49

FEN (free-play from line start): http://localhost:5173/analysis?fen=3rr1k1/pp3ppp/1b3p2/5P2/3B4/5NqP/PP1Q2P1/R4RK1%20b%20-%20-%200%2025

#### Case 314 — DISCOVERED_CHECK (allowed, depth 10)

Moves (SAN): `10... Bg4 11. Qe3`

FEN (line start): `r1b1k2r/ppp1qppp/3b1n2/3P4/8/2N2Q2/PPPPB1PP/R1B1K2R b - - 1 10`

Game (full game at ply): http://localhost:5173/analysis?game_id=682171&ply=18

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1b1k2r/ppp1qppp/3b1n2/3P4/8/2N2Q2/PPPPB1PP/R1B1K2R%20b%20-%20-%201%2010

#### Case 315 — PIN (allowed, depth 0)

Moves (SAN): `18... Rf5 19. Ne2 Nxd5 20. g4 Rf6 21. Rd1 Ne3+ 22. Ke1 Nxd1 23. Kxd1 c6 24. Kd2`

FEN (line start): `6k1/ppp2ppp/5n2/2PPr3/5B2/2N5/PPP3PP/R4K2 b - - 1 18`

Game (full game at ply): http://localhost:5173/analysis?game_id=682171&ply=34

FEN (free-play from line start): http://localhost:5173/analysis?fen=6k1/ppp2ppp/5n2/2PPr3/5B2/2N5/PPP3PP/R4K2%20b%20-%20-%201%2018

#### Case 316 — SACRIFICE (missed, depth 4)

Moves (SAN): `20... g5 21. f3 Nxh2 22. Kxh2 Ke7 23. a4 Rac8 24. axb5 axb5 25. f4 gxh4 26. g4`

FEN (line start): `r3k2r/5pp1/p3pq2/1p1p1p2/1P1P2nN/P2Q2P1/5P1P/4RRK1 b - - 0 20`

Game (full game at ply): http://localhost:5173/analysis?game_id=682178&ply=39

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3k2r/5pp1/p3pq2/1p1p1p2/1P1P2nN/P2Q2P1/5P1P/4RRK1%20b%20-%20-%200%2020

#### Case 317 — CLEARANCE (allowed, depth 10)

Moves (SAN): `23. gxh4 Qxh4+ 24. Kg2 f4 25. Rf2 g5 26. Rd1 Kd7 27. Kg1 Rh8 28. Rg2 f6`

FEN (line start): `2r1k3/5pp1/p3pq2/1p1p1p2/1P1P3r/P2Q1PP1/7K/4RR2 w - - 0 23`

Game (full game at ply): http://localhost:5173/analysis?game_id=682178&ply=43

FEN (free-play from line start): http://localhost:5173/analysis?fen=2r1k3/5pp1/p3pq2/1p1p1p2/1P1P3r/P2Q1PP1/7K/4RR2%20w%20-%20-%200%2023

#### Case 318 — TRAPPED_PIECE (missed, depth 4)

Moves (SAN): `22... f4 23. Kg2 fxg3 24. Rh1 Rxh4 25. Rxh4 Qxh4 26. Rh1 Qf4 27. Rh8+ Kd7 28. Rxc8`

FEN (line start): `2r1k2r/5pp1/p3pq2/1p1p1p2/1P1P3N/P2Q1PP1/7K/4RR2 b - - 0 22`

Game (full game at ply): http://localhost:5173/analysis?game_id=682178&ply=43

FEN (free-play from line start): http://localhost:5173/analysis?fen=2r1k2r/5pp1/p3pq2/1p1p1p2/1P1P3N/P2Q1PP1/7K/4RR2%20b%20-%20-%200%2022

#### Case 319 — PIN (allowed, depth 0)

Moves (SAN): `25. Qxf5 Qxd4 26. Rf2 Rh8 27. Qg5+ Kd7 28. Rd2 Qc3 29. Rc1 Qxc1 30. Rxd5+ exd5`

FEN (line start): `2r5/4kpp1/p3p3/1p1p1p2/1P1P3q/P2Q1P2/6K1/4RR2 w - - 1 25`

Game (full game at ply): http://localhost:5173/analysis?game_id=682178&ply=47

FEN (free-play from line start): http://localhost:5173/analysis?fen=2r5/4kpp1/p3p3/1p1p1p2/1P1P3q/P2Q1P2/6K1/4RR2%20w%20-%20-%201%2025

#### Case 320 — CLEARANCE (missed, depth 4)

Moves (SAN): `24... f4 25. Re2 Kd7 26. Kg1 Rh8 27. Rg2 g5 28. Qd2 Qh1+ 29. Kf2 Qh4+ 30. Ke2`

FEN (line start): `2r1k3/5pp1/p3p3/1p1p1p2/1P1P3q/P2Q1P2/6K1/4RR2 b - - 0 24`

Game (full game at ply): http://localhost:5173/analysis?game_id=682178&ply=47

FEN (free-play from line start): http://localhost:5173/analysis?fen=2r1k3/5pp1/p3p3/1p1p1p2/1P1P3q/P2Q1P2/6K1/4RR2%20b%20-%20-%200%2024

#### Case 321 — CLEARANCE (allowed, depth 8)

Moves (SAN): `12... Bxe6 13. Bxf4 Nd7 14. a4 h6 15. Bg3`

FEN (line start): `rn2k2r/pp2bppp/2p1Q3/8/3P1pb1/2PB1N2/PP4PP/R1B2RK1 b - - 0 12`

Game (full game at ply): http://localhost:5173/analysis?game_id=682182&ply=22

FEN (free-play from line start): http://localhost:5173/analysis?fen=rn2k2r/pp2bppp/2p1Q3/8/3P1pb1/2PB1N2/PP4PP/R1B2RK1%20b%20-%20-%200%2012

#### Case 322 — CLEARANCE (allowed, depth 8)

Moves (SAN): `4. Nxe5`

FEN (line start): `rnbqk2r/pppp1ppp/5n2/4p3/1bP5/2N2N2/PP1PPPPP/R1BQKB1R w - - 1 4`

Game (full game at ply): http://localhost:5173/analysis?game_id=682185&ply=5

FEN (free-play from line start): http://localhost:5173/analysis?fen=rnbqk2r/pppp1ppp/5n2/4p3/1bP5/2N2N2/PP1PPPPP/R1BQKB1R%20w%20-%20-%201%204

#### Case 323 — CLEARANCE (missed, depth 6)

Moves (SAN): `5... a5 6. Qc2 a4 7. e3 d6 8. Be2 Be6 9. Nxb4 Nxb4 10. Qb1 e4 11. Nd4`

FEN (line start): `r1bqk2r/pppp1ppp/2n2n2/3Np3/1bP5/1Q3N2/PP1PPPPP/R1B1KB1R b - - 0 5`

Game (full game at ply): http://localhost:5173/analysis?game_id=682185&ply=9

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1bqk2r/pppp1ppp/2n2n2/3Np3/1bP5/1Q3N2/PP1PPPPP/R1B1KB1R%20b%20-%20-%200%205

#### Case 324 — FORK (missed, depth 8)

Moves (SAN): `23... Rc8+ 24. Kb4 Qc4+ 25. Ka3 Rc6 26. Qb8+ Rf8 27. Qxa7 Ra6+ 28. Qxa6 Qxa6+ 29. Kb4`

FEN (line start): `5rk1/pp3rpp/3Q4/8/3P2P1/2K1P1P1/PP5P/R1B2q2 b - - 0 23`

Game (full game at ply): http://localhost:5173/analysis?game_id=682185&ply=45

FEN (free-play from line start): http://localhost:5173/analysis?fen=5rk1/pp3rpp/3Q4/8/3P2P1/2K1P1P1/PP5P/R1B2q2%20b%20-%20-%200%2023

#### Case 325 — FORK (allowed, depth 0)

Moves (SAN): `17. Bxd5 Rb8 18. Rxe4 exd4 19. Qh5 Qd7 20. Rxd4 Qf5 21. Bxf7+ Rxf7 22. Qxf5 Bxf5`

FEN (line start): `r1b2rk1/2q2ppp/p2b4/1p1pp3/3Nn3/1BP3P1/PP3P1P/R1BQR1K1 w - - 0 17`

Game (full game at ply): http://localhost:5173/analysis?game_id=682190&ply=31

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1b2rk1/2q2ppp/p2b4/1p1pp3/3Nn3/1BP3P1/PP3P1P/R1BQR1K1%20w%20-%20-%200%2017

#### Case 326 — HANGING_PIECE (allowed, depth 0)

Moves (SAN): `24. Qxf3 Be7 25. Be3 Qd6 26. Rh3 Rad8 27. a4 bxa4 28. g4 f4 29. Bf2 Qe6`

FEN (line start): `r4rk1/6pp/p2b4/1pq1pp2/7R/2P2bP1/PP5P/R1BQ3K w - - 0 24`

Game (full game at ply): http://localhost:5173/analysis?game_id=682190&ply=45

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4rk1/6pp/p2b4/1pq1pp2/7R/2P2bP1/PP5P/R1BQ3K%20w%20-%20-%200%2024

#### Case 327 — PIN (missed, depth 0)

Moves (SAN): `23... Qc6 24. Kg2 Be7 25. a4 bxa4 26. Rxa4 Bxh4 27. Ra5 Be7 28. h3 Bh5 29. Rd5`

FEN (line start): `r4rk1/6pp/p2b4/1pq1pp2/6bR/2P2PP1/PP5P/R1BQ3K b - - 0 23`

Game (full game at ply): http://localhost:5173/analysis?game_id=682190&ply=45

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4rk1/6pp/p2b4/1pq1pp2/6bR/2P2PP1/PP5P/R1BQ3K%20b%20-%20-%200%2023

#### Case 328 — CLEARANCE (missed, depth 4)

Moves (SAN): `7. Qd1 e6 8. g3 Nf6 9. Bg2 Be7`

FEN (line start): `r2qkbnr/pp2pppp/3p4/2p5/3nP3/2NP1Q1P/PPP2PP1/R1B1KB1R w - - 0 7`

Game (full game at ply): http://localhost:5173/analysis?game_id=682196&ply=12

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qkbnr/pp2pppp/3p4/2p5/3nP3/2NP1Q1P/PPP2PP1/R1B1KB1R%20w%20-%20-%200%207

#### Case 329 — TRAPPED_PIECE (missed, depth 4)

Moves (SAN): `12. Bb2 d5 13. exd5 Nxd5 14. Rxa1 g6 15. Kc2 Nb4+ 16. Kb1 Bg7 17. f5 Nc6`

FEN (line start): `2kr1b1r/pp2pppp/3p1n2/q1p5/4PP2/1PNP2QP/P2KB1P1/n1B4R w - - 0 12`

Game (full game at ply): http://localhost:5173/analysis?game_id=682196&ply=22

FEN (free-play from line start): http://localhost:5173/analysis?fen=2kr1b1r/pp2pppp/3p1n2/q1p5/4PP2/1PNP2QP/P2KB1P1/n1B4R%20w%20-%20-%200%2012

#### Case 330 — CLEARANCE (missed, depth 6)

Moves (SAN): `5. fxe5 d5 6. exd6 cxd6 7. d4 Bb6 8. Bg5 Bg4 9. Qd3 f6 10. Bd2`

FEN (line start): `r1bqk2r/ppppnppp/2n5/2b1p3/4PP2/2N2N2/PPPP2PP/R1BQKB1R w - - 0 5`

Game (full game at ply): http://localhost:5173/analysis?game_id=682217&ply=8

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1bqk2r/ppppnppp/2n5/2b1p3/4PP2/2N2N2/PPPP2PP/R1BQKB1R%20w%20-%20-%200%205

#### Case 331 — CLEARANCE (allowed, depth 10)

Moves (SAN): `11... g5 12. Bg3 Nf5 13. d4 Bxf3 14. dxc5 Bxg2 15. Rg1 d4 16. Nb5 Qd5 17. Qd2`

FEN (line start): `r2q1rk1/pp2npp1/2n4p/2bpP3/6bB/2NP1N2/PPP1B1PP/R2QK2R b - - 0 11`

Game (full game at ply): http://localhost:5173/analysis?game_id=682217&ply=20

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2q1rk1/pp2npp1/2n4p/2bpP3/6bB/2NP1N2/PPP1B1PP/R2QK2R%20b%20-%20-%200%2011

#### Case 332 — PIN (missed, depth 6)

Moves (UCI — SAN unavailable): `e1g1 d8d7 h2h3 g4h5 f3d4 h5d1 c4b5 d1a4 b5d7 e8d7 d4f5 g7g6`

FEN (line start): `r2qk1nr/ppp2ppp/8/3Pp3/1bBnP1b1/5N2/PP1N1PPP/R1BQK2R w - - 0 8`

Game (full game at ply): http://localhost:5173/analysis?game_id=682228&ply=14

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qk1nr/ppp2ppp/8/3Pp3/1bBnP1b1/5N2/PP1N1PPP/R1BQK2R%20w%20-%20-%200%208

#### Case 333 — SACRIFICE (allowed, depth 4)

Moves (SAN): `9... c6 10. dxc6 b5 11. Bxb5 Qa5 12. Qxa5 Bxa5 13. b4 Bxb4 14. Rb1 a5`

FEN (line start): `r2qk1nr/ppp2ppp/8/3Pp3/QbBnP3/5b1P/PP1N1PP1/R1B1K2R b - - 1 9`

Game (full game at ply): http://localhost:5173/analysis?game_id=682228&ply=16

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qk1nr/ppp2ppp/8/3Pp3/QbBnP3/5b1P/PP1N1PP1/R1B1K2R%20b%20-%20-%201%209

#### Case 334 — FORK (missed, depth 8)

Moves (SAN): `9. gxf3 c6 10. Kf1 Ne7 11. Nb3 cxd5 12. Nxd4 dxc4 13. Qa4+ Qd7 14. Nb5 Nc6`

FEN (line start): `r2qk1nr/ppp2ppp/8/3Pp3/1bBnP3/5b1P/PP1N1PP1/R1BQK2R w - - 0 9`

Game (full game at ply): http://localhost:5173/analysis?game_id=682228&ply=16

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qk1nr/ppp2ppp/8/3Pp3/1bBnP3/5b1P/PP1N1PP1/R1BQK2R%20w%20-%20-%200%209

#### Case 335 — FORK (allowed, depth 2)

Moves (SAN): `16... Bxf4 17. Bxf4 Qf2+ 18. Kh1 Qxf4 19. h3 Rad8 20. Re1 Rfe8 21. Rb1 Ng3+ 22. Kg1`

FEN (line start): `r4rk1/p4ppp/2Qb4/8/4nR1q/4B3/PPP3PP/R5K1 b - - 1 16`

Game (full game at ply): http://localhost:5173/analysis?game_id=682286&ply=30

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4rk1/p4ppp/2Qb4/8/4nR1q/4B3/PPP3PP/R5K1%20b%20-%20-%201%2016

#### Case 336 — CLEARANCE (missed, depth 10)

Moves (SAN): `16. h3 Rae8 17. Rf3 Bb8 18. Qc4 Qe7 19. Raf1 Qd6 20. Bf4 Qg6 21. Re3 Bxf4`

FEN (line start): `r4rk1/p4ppp/2Qb4/8/4n2q/4B3/PPP3PP/R4RK1 w - - 0 16`

Game (full game at ply): http://localhost:5173/analysis?game_id=682286&ply=30

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4rk1/p4ppp/2Qb4/8/4n2q/4B3/PPP3PP/R4RK1%20w%20-%20-%200%2016

#### Case 337 — CLEARANCE (allowed, depth 4)

Moves (SAN): `20... Qf6 21. Rfe1 Bd5 22. Qd2 Qc6 23. Bxd4 cxd4 24. Rxe8+ Rxe8 25. f3 Rd8 26. Kf2`

FEN (line start): `1r1qr1k1/p1p2p1p/4b1p1/2p5/3b4/PP2B2P/2B1QPP1/3R1RK1 b - - 0 20`

Game (full game at ply): http://localhost:5173/analysis?game_id=682291&ply=38

FEN (free-play from line start): http://localhost:5173/analysis?fen=1r1qr1k1/p1p2p1p/4b1p1/2p5/3b4/PP2B2P/2B1QPP1/3R1RK1%20b%20-%20-%200%2020

#### Case 338 — MATE (allowed, depth 8)

Moves (SAN): `31... Rxd3 32. Ra1 g5 33. Kh1 Rd2 34. Rg1 Qg3 35. Rf1 Qxg2#`

FEN (line start): `8/p4pkp/6p1/8/3p4/1r1B3P/5qPK/6R1 b - - 1 31`

Game (full game at ply): http://localhost:5173/analysis?game_id=682291&ply=60

FEN (free-play from line start): http://localhost:5173/analysis?fen=8/p4pkp/6p1/8/3p4/1r1B3P/5qPK/6R1%20b%20-%20-%201%2031

#### Case 339 — MATE (allowed, depth 8)

Moves (SAN): `32... Qf4+ 33. Kh1 Qxe4 34. Kh2 Qe5+ 35. Kh1 Qg3 36. Rd1 Qxg2#`

FEN (line start): `8/p4pkp/6p1/8/3pB3/7P/1r3qPK/6R1 b - - 1 32`

Game (full game at ply): http://localhost:5173/analysis?game_id=682291&ply=62

FEN (free-play from line start): http://localhost:5173/analysis?fen=8/p4pkp/6p1/8/3pB3/7P/1r3qPK/6R1%20b%20-%20-%201%2032

#### Case 340 — INTERFERENCE (allowed, depth 4)

Moves (SAN): `21... Qxh2+ 22. Kf1 Bxg2+ 23. Ke2 Qxe5+ 24. Kd2 Qf4+ 25. Qe3 Rad8+ 26. Kc1 Qxe3+ 27. Rxe3`

FEN (line start): `r6r/p1p1kpp1/1p2p3/3bN3/5q2/P1PQ4/2B2PPP/R3R1K1 b - - 1 21`

Game (full game at ply): http://localhost:5173/analysis?game_id=682292&ply=40

FEN (free-play from line start): http://localhost:5173/analysis?fen=r6r/p1p1kpp1/1p2p3/3bN3/5q2/P1PQ4/2B2PPP/R3R1K1%20b%20-%20-%201%2021

#### Case 341 — ATTRACTION (allowed, depth 6)

Moves (SAN): `25... Qf6 26. Qe3 Rad8 27. Rad1 Bxf3+ 28. Qxf3 Qxf3+ 29. Kxf3 Rh3+ 30. Rg3 Rxg3+ 31. Kxg3`

FEN (line start): `r6r/p1p1kpp1/1p2p3/3b2q1/8/P1PQ1N2/2B1KP2/R5R1 b - - 1 25`

Game (full game at ply): http://localhost:5173/analysis?game_id=682292&ply=48

FEN (free-play from line start): http://localhost:5173/analysis?fen=r6r/p1p1kpp1/1p2p3/3b2q1/8/P1PQ1N2/2B1KP2/R5R1%20b%20-%20-%201%2025

#### Case 342 — PIN (missed, depth 4)

Moves (SAN): `30. Rxg7 Rhf8 31. Re1 Rd6 32. Bg6 Qb5+ 33. c4 Qxc4+ 34. Kg1 Kd8 35. Bxf7 Qd4`

FEN (line start): `3r3r/p1p1kpp1/1p2p3/8/8/P1PB1Q2/1q3P2/3R1KR1 w - - 0 30`

Game (full game at ply): http://localhost:5173/analysis?game_id=682292&ply=58

FEN (free-play from line start): http://localhost:5173/analysis?fen=3r3r/p1p1kpp1/1p2p3/8/8/P1PB1Q2/1q3P2/3R1KR1%20w%20-%20-%200%2030

#### Case 343 — CLEARANCE (missed, depth 10)

Moves (SAN): `32. Qh4+ Qf6 33. Qg3 Rd6 34. Rc1 c5 35. Rc4 Rd5 36. Ra4 a5 37. Bb5 g6`

FEN (line start): `3r4/p1p1kpp1/1p2p3/8/8/P1qB4/5P2/3R1K1Q w - - 0 32`

Game (full game at ply): http://localhost:5173/analysis?game_id=682292&ply=62

FEN (free-play from line start): http://localhost:5173/analysis?fen=3r4/p1p1kpp1/1p2p3/8/8/P1qB4/5P2/3R1K1Q%20w%20-%20-%200%2032

#### Case 344 — PIN (allowed, depth 2)

Moves (SAN): `8... dxe4 9. Nxe4 Qe7 10. Bd3 Bg4`

FEN (line start): `r1bqk1nr/ppp2ppp/1bn5/3p4/1P1PP3/P1N2N2/5PPP/R1BQKB1R b - - 0 8`

Game (full game at ply): http://localhost:5173/analysis?game_id=682296&ply=14

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1bqk1nr/ppp2ppp/1bn5/3p4/1P1PP3/P1N2N2/5PPP/R1BQKB1R%20b%20-%20-%200%208

#### Case 345 — CLEARANCE (missed, depth 6)

Moves (SAN): `8. Bg5 f6 9. Bc1 Bg4 10. e3 f5 11. Be2 Nf6`

FEN (line start): `r1bqk1nr/ppp2ppp/1bn5/3p4/1P1P4/P1N2N2/4PPPP/R1BQKB1R w - - 0 8`

Game (full game at ply): http://localhost:5173/analysis?game_id=682296&ply=14

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1bqk1nr/ppp2ppp/1bn5/3p4/1P1P4/P1N2N2/4PPPP/R1BQKB1R%20w%20-%20-%200%208

#### Case 346 — ATTRACTION (allowed, depth 6)

Moves (SAN): `11... Nf6 12. Bd3 Bf5 13. Nxf6+ Qxf6 14. Bxf5 Bxf2+ 15. Kxf2 Qxf5+ 16. Qf3 Qxb1 17. Re1+`

FEN (line start): `r1bqk1nr/ppp2ppp/8/8/1P1bN3/P7/5PPP/1RBQKB1R b - - 1 11`

Game (full game at ply): http://localhost:5173/analysis?game_id=682296&ply=20

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1bqk1nr/ppp2ppp/8/8/1P1bN3/P7/5PPP/1RBQKB1R%20b%20-%20-%201%2011

#### Case 347 — DISCOVERED_CHECK (allowed, depth 6)

Moves (SAN): `13... Qxf2+ 14. Kd2 Bf5 15. Rf1`

FEN (line start): `r1b1k2r/ppp2ppp/5q2/8/1P1b4/P7/4BPPP/1RBQK2R b - - 1 13`

Game (full game at ply): http://localhost:5173/analysis?game_id=682296&ply=24

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1b1k2r/ppp2ppp/5q2/8/1P1b4/P7/4BPPP/1RBQK2R%20b%20-%20-%201%2013

#### Case 348 — CLEARANCE (missed, depth 10)

Moves (SAN): `13. Bb5+ c6 14. Qe2+ Be6 15. Bc4 Bxf2+ 16. Qxf2 Qc3+ 17. Bd2 Qxc4 18. Rc1 Qe4+`

FEN (line start): `r1b1k2r/ppp2ppp/5q2/8/1P1b4/P7/5PPP/1RBQKB1R w - - 0 13`

Game (full game at ply): http://localhost:5173/analysis?game_id=682296&ply=24

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1b1k2r/ppp2ppp/5q2/8/1P1b4/P7/5PPP/1RBQKB1R%20w%20-%20-%200%2013

#### Case 349 — DISCOVERED_ATTACK (allowed, depth 9)

Moves (SAN): `15... Rad8 16. Rb3 Be6 17. Rb1 Bc4 18. Bg5 Qxg5 19. Bxc4 Bxf2+ 20. Rxf2 Rxd1+ 21. Rxd1`

FEN (line start): `r4rk1/ppp2ppp/5q2/5b2/1P1b4/P2B4/5PPP/1RBQ1RK1 b - - 1 15`

Game (full game at ply): http://localhost:5173/analysis?game_id=682296&ply=28

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4rk1/ppp2ppp/5q2/5b2/1P1b4/P2B4/5PPP/1RBQ1RK1%20b%20-%20-%201%2015

#### Case 350 — CLEARANCE (allowed, depth 2)

Moves (SAN): `16. Nd4 Ra6 17. Qf3 Be4 18. Qc3 Rfa8 19. Rfe1 Qa7 20. Re3 Qb6 21. h4 Bg6`

FEN (line start): `r4rk1/4qpp1/2p1p2p/1p1pPb2/1P6/P4N2/2P2PPP/R2Q1RK1 w - - 0 16`

Game (full game at ply): http://localhost:5173/analysis?game_id=682302&ply=29

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4rk1/4qpp1/2p1p2p/1p1pPb2/1P6/P4N2/2P2PPP/R2Q1RK1%20w%20-%20-%200%2016

#### Case 351 — FORK (missed, depth 8)

Moves (SAN): `25... d4 26. Qf2 Bg6 27. h4 Bh5 28. Rb1 Qc3 29. Ne4 Qd3 30. Re1 Bg6 31. Nd6`

FEN (line start): `5rk1/5pp1/3Np2p/2qpP3/5P2/5Q2/2b3PP/5R1K b - - 0 25`

Game (full game at ply): http://localhost:5173/analysis?game_id=682302&ply=49

FEN (free-play from line start): http://localhost:5173/analysis?fen=5rk1/5pp1/3Np2p/2qpP3/5P2/5Q2/2b3PP/5R1K%20b%20-%20-%200%2025

#### Case 352 — FORK (missed, depth 2)

Moves (SAN): `28... Rg6 29. Qf2 Bxg2+ 30. Qxg2 Rxg2 31. Kxg2 Qc2+ 32. Rf2 Qg6+ 33. Kf1 Qxe8 34. f5`

FEN (line start): `4N1k1/6p1/4pr1p/2qp4/4bP2/6Q1/6PP/5R1K b - - 0 28`

Game (full game at ply): http://localhost:5173/analysis?game_id=682302&ply=55

FEN (free-play from line start): http://localhost:5173/analysis?fen=4N1k1/6p1/4pr1p/2qp4/4bP2/6Q1/6PP/5R1K%20b%20-%20-%200%2028

#### Case 353 — CLEARANCE (missed, depth 10)

Moves (SAN): `10... h6 11. Bf6 Bxf6 12. exf6 Nc6 13. Qe3+ Kf8 14. Nd5 d6 15. Bb5 Be6 16. Bxc6`

FEN (line start): `r1bqk2r/ppppnpbp/6p1/4P1B1/3Q4/2N5/PPP2PPP/2KR1B1R b - - 0 10`

Game (full game at ply): http://localhost:5173/analysis?game_id=682318&ply=19

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1bqk2r/ppppnpbp/6p1/4P1B1/3Q4/2N5/PPP2PPP/2KR1B1R%20b%20-%20-%200%2010

#### Case 354 — PIN (missed, depth 0)

Moves (SAN): `15... Bh6 16. dxc7 Be6 17. Nd5 Bxd2+ 18. Kxd2 Kg7 19. a4 Rac8 20. a5 h5 21. Re1`

FEN (line start): `r1b2rk1/ppp2pbp/3P2p1/8/2B5/2N5/PPPR1PPP/2K4R b - - 0 15`

Game (full game at ply): http://localhost:5173/analysis?game_id=682318&ply=29

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1b2rk1/ppp2pbp/3P2p1/8/2B5/2N5/PPPR1PPP/2K4R%20b%20-%20-%200%2015

#### Case 355 — PIN (allowed, depth 2)

Moves (SAN): `15. Qa4+ Nc6 16. Rd1 Qa5 17. Qxa5 Nxa5 18. f4 Be7 19. Nd6+ Bxd6 20. exd6 Kd7`

FEN (line start): `r2qkb1r/pp3pp1/4p1np/4P3/3nN3/7P/PP2BPP1/R1BQR1K1 w - - 0 15`

Game (full game at ply): http://localhost:5173/analysis?game_id=682325&ply=27

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qkb1r/pp3pp1/4p1np/4P3/3nN3/7P/PP2BPP1/R1BQR1K1%20w%20-%20-%200%2015

#### Case 356 — PIN (allowed, depth 2)

Moves (SAN): `18. Qa4+ Nc6 19. Rxd8+ Rxd8 20. Qb3 Rd7 21. Nc5 Rc7 22. Nxe6 fxe6 23. Qxe6 Rf8`

FEN (line start): `r2qk2r/pp2bpp1/4p2p/4n3/4N3/4B2P/PP1R1PP1/R2Q2K1 w - - 1 18`

Game (full game at ply): http://localhost:5173/analysis?game_id=682325&ply=33

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qk2r/pp2bpp1/4p2p/4n3/4N3/4B2P/PP1R1PP1/R2Q2K1%20w%20-%20-%201%2018

#### Case 357 — CLEARANCE (missed, depth 10)

Moves (SAN): `17... Qa5 18. Rc1 Nc6 19. Nc5 Bxc5 20. Bxc5 Rd8 21. b4 Rxd2 22. Qxd2 Qd8 23. Qc3`

FEN (line start): `r2qkb1r/pp3pp1/4p2p/4n3/4N3/4B2P/PP1R1PP1/R2Q2K1 b - - 0 17`

Game (full game at ply): http://localhost:5173/analysis?game_id=682325&ply=33

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qkb1r/pp3pp1/4p2p/4n3/4N3/4B2P/PP1R1PP1/R2Q2K1%20b%20-%20-%200%2017

#### Case 358 — DISCOVERED_ATTACK (allowed, depth 1)

Moves (SAN): `7... Nxe5 8. dxe5 Qxd1+ 9. Nxd1 Ne4 10. f3 Nc5 11. f4 b6 12. Be3 Bb7 13. Nf2`

FEN (line start): `r1bqk2r/pppnppbp/5np1/4N3/2PP4/2N5/PP3PPP/R1BQKB1R b - - 0 7`

Game (full game at ply): http://localhost:5173/analysis?game_id=682336&ply=12

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1bqk2r/pppnppbp/5np1/4N3/2PP4/2N5/PP3PPP/R1BQKB1R%20b%20-%20-%200%207

#### Case 359 — CLEARANCE (missed, depth 6)

Moves (SAN): `9. Bf3 Ba6 10. Nc6 Qe8`

FEN (line start): `r1bq1rk1/p1pnppbp/1p3np1/4N3/2PP4/2N5/PP2BPPP/R1BQK2R w - - 0 9`

Game (full game at ply): http://localhost:5173/analysis?game_id=682336&ply=16

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1bq1rk1/p1pnppbp/1p3np1/4N3/2PP4/2N5/PP2BPPP/R1BQK2R%20w%20-%20-%200%209

#### Case 360 — DISCOVERED_ATTACK (missed, depth 1)

Moves (SAN): `17... Bxc3 18. Qxc3 Rxf4 19. Rxe6 Nd4 20. Qxd4 Rxd4 21. Rxd4 Qc7 22. Rxd5 Qc4 23. Rde5`

FEN (line start): `2rq1rk1/1p4pp/p1n1pb2/3p4/1P3B2/P1N2Q1P/2P2PP1/3RR1K1 b - - 0 17`

Game (full game at ply): http://localhost:5173/analysis?game_id=682339&ply=33

FEN (free-play from line start): http://localhost:5173/analysis?fen=2rq1rk1/1p4pp/p1n1pb2/3p4/1P3B2/P1N2Q1P/2P2PP1/3RR1K1%20b%20-%20-%200%2017

#### Case 361 — FORK (missed, depth 6)

Moves (SAN): `18... Qf6 19. Bxe5 Qxf3 20. gxf3 Nxe5 21. Nd4 Nxf3+ 22. Nxf3 Rxf3 23. Rxe6 Rxc2 24. Re8+`

FEN (line start): `2rq1rk1/1p4pp/p1n1p3/3pb3/1P3B2/P4Q1P/2P1NPP1/3RR1K1 b - - 0 18`

Game (full game at ply): http://localhost:5173/analysis?game_id=682339&ply=35

FEN (free-play from line start): http://localhost:5173/analysis?fen=2rq1rk1/1p4pp/p1n1p3/3pb3/1P3B2/P4Q1P/2P1NPP1/3RR1K1%20b%20-%20-%200%2018

#### Case 362 — SACRIFICE (missed, depth 4)

Moves (SAN): `14. Nb5+ Kd8 15. Rad1 gxf4 16. Rd3 c4 17. Rdd1 Rf5 18. Nbd4 Rxe5 19. Nxe5 Bxe5`

FEN (line start): `5rnr/ppknp1b1/4p2p/2p1P1p1/5B2/P1N2NP1/1PP2P1P/R4RK1 w - - 0 14`

Game (full game at ply): http://localhost:5173/analysis?game_id=682341&ply=26

FEN (free-play from line start): http://localhost:5173/analysis?fen=5rnr/ppknp1b1/4p2p/2p1P1p1/5B2/P1N2NP1/1PP2P1P/R4RK1%20w%20-%20-%200%2014

#### Case 363 — TRAPPED_PIECE (missed, depth 4)

Moves (SAN): `26... Qa5 27. Kc1 Qc3 28. Nb1 Qxa1 29. Kd2 Qd4+ 30. Qd3 Qxf2+ 31. Qe2 Qxg1 32. Qxa6`

FEN (line start): `r2q2k1/5ppp/r4p2/3n4/5B2/1P4P1/pKPNQP1P/R5R1 b - - 0 26`

Game (full game at ply): http://localhost:5173/analysis?game_id=682344&ply=51

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2q2k1/5ppp/r4p2/3n4/5B2/1P4P1/pKPNQP1P/R5R1%20b%20-%20-%200%2026

#### Case 364 — SKEWER (missed, depth 4)

Moves (SAN): `30... Rxa2+ 31. Kb1 Ra1+ 32. Kb2 Rxg1 33. Qe4 Rd1 34. Qa4 Kh8 35. Qa7 Nb4 36. Nc4`

FEN (line start): `r1q3k1/5ppp/2r2p2/8/5B2/1P3QP1/RKnN1P1P/6R1 b - - 0 30`

Game (full game at ply): http://localhost:5173/analysis?game_id=682344&ply=59

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1q3k1/5ppp/2r2p2/8/5B2/1P3QP1/RKnN1P1P/6R1%20b%20-%20-%200%2030

#### Case 365 — CLEARANCE (allowed, depth 6)

Moves (SAN): `14. Nxe6 fxe6 15. Bc4 Kf7 16. Rd1 Bb4 17. Rhe1 b5 18. Bb3 a5 19. Rxe6 Rxe6`

FEN (line start): `rn2r1k1/pp3pp1/2pbbp1p/8/5N2/2N3P1/PPP2P1P/2K1RB1R w - - 1 14`

Game (full game at ply): http://localhost:5173/analysis?game_id=682359&ply=25

FEN (free-play from line start): http://localhost:5173/analysis?fen=rn2r1k1/pp3pp1/2pbbp1p/8/5N2/2N3P1/PPP2P1P/2K1RB1R%20w%20-%20-%201%2014

#### Case 366 — SACRIFICE (allowed, depth 6)

Moves (SAN): `18. Bc8 a5 19. Rd1 Kg8 20. f4 Bxc3 21. Rd8+ Kf7 22. Bxb7 Ra7 23. Rxb8 Bd4`

FEN (line start): `rn5k/pp4p1/2p1Bp1p/4b3/8/2N3P1/PPP2P1P/2K4R w - - 1 18`

Game (full game at ply): http://localhost:5173/analysis?game_id=682359&ply=33

FEN (free-play from line start): http://localhost:5173/analysis?fen=rn5k/pp4p1/2p1Bp1p/4b3/8/2N3P1/PPP2P1P/2K4R%20w%20-%20-%201%2018

#### Case 367 — CLEARANCE (allowed, depth 4)

Moves (SAN): `4... exd4 5. Nxd4`

FEN (line start): `rnbqk2r/pppp1ppp/5n2/2b1p3/3PP3/2N2N2/PPP2PPP/R1BQKB1R b - - 0 4`

Game (full game at ply): http://localhost:5173/analysis?game_id=682407&ply=6

FEN (free-play from line start): http://localhost:5173/analysis?fen=rnbqk2r/pppp1ppp/5n2/2b1p3/3PP3/2N2N2/PPP2PPP/R1BQKB1R%20b%20-%20-%200%204

#### Case 368 — CLEARANCE (allowed, depth 6)

Moves (SAN): `18... Nxd6 19. Rfe1 f6 20. Bd3 Ke7 21. Re3 Rad8 22. Rde1 Rg8 23. Kf1 c6 24. g3`

FEN (line start): `r2k1r2/ppp2p2/3N3p/4pnp1/2B5/7P/PPP2PP1/3R1RK1 b - - 0 18`

Game (full game at ply): http://localhost:5173/analysis?game_id=682407&ply=34

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2k1r2/ppp2p2/3N3p/4pnp1/2B5/7P/PPP2PP1/3R1RK1%20b%20-%20-%200%2018

#### Case 369 — CLEARANCE (missed, depth 10)

Moves (SAN): `19. Bd3 Qh6 20. Qc2 Rad8 21. Rb1 b6 22. Rb5 Kg8 23. Bd2 Rd6 24. Rc1 a6`

FEN (line start): `r3rk2/ppp1nppB/2n2q2/2Q5/3P4/P3P3/5PPP/R1B2RK1 w - - 0 19`

Game (full game at ply): http://localhost:5173/analysis?game_id=682409&ply=36

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3rk2/ppp1nppB/2n2q2/2Q5/3P4/P3P3/5PPP/R1B2RK1%20w%20-%20-%200%2019

#### Case 370 — CLEARANCE (missed, depth 10)

Moves (SAN): `14... Qxc2 15. Rc1 Qg6 16. Na4 Bd6 17. Rxc6 Ne7 18. Rc1`

FEN (line start): `r3k1nr/5ppp/p1p1p1q1/3p4/1b1P2P1/2N4P/PPPBQP2/R3K2R b - - 0 14`

Game (full game at ply): http://localhost:5173/analysis?game_id=682411&ply=27

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3k1nr/5ppp/p1p1p1q1/3p4/1b1P2P1/2N4P/PPPBQP2/R3K2R%20b%20-%20-%200%2014

#### Case 371 — FORK (missed, depth 0)

Moves (SAN): `21... Ng3 22. Qh2 Nxh1 23. Nc5 Rbd8 24. h4 e5 25. dxe5 Qe7 26. Rc3 Nf2 27. Qxf2`

FEN (line start): `1r3rk1/5ppp/p1p1pq2/3p4/N2Pn1P1/P2R1P1P/1PP1Q3/1K5R b - - 0 21`

Game (full game at ply): http://localhost:5173/analysis?game_id=682411&ply=41

FEN (free-play from line start): http://localhost:5173/analysis?fen=1r3rk1/5ppp/p1p1pq2/3p4/N2Pn1P1/P2R1P1P/1PP1Q3/1K5R%20b%20-%20-%200%2021

#### Case 372 — FORK (missed, depth 2)

Moves (SAN): `21. Qa5+ Kb8 22. Nxc6+ Bxc6 23. dxc6 Be5 24. Rxe5 Qa7 25. Qb4+ Kc8 26. Nb6+ Kb8`

FEN (line start): `3r3r/1bk1qpbp/p1p5/2RPNp2/N3P3/2Q5/PP3PPP/5RK1 w - - 0 21`

Game (full game at ply): http://localhost:5173/analysis?game_id=682422&ply=40

FEN (free-play from line start): http://localhost:5173/analysis?fen=3r3r/1bk1qpbp/p1p5/2RPNp2/N3P3/2Q5/PP3PPP/5RK1%20w%20-%20-%200%2021

#### Case 373 — CLEARANCE (allowed, depth 2)

Moves (SAN): `22... Kb8 23. Rcc1 Bc7 24. Qc3 cxd5 25. Nc5 Bb6 26. Nxb7 Qxb7 27. exd5 Rhe8 28. Qf6`

FEN (line start): `3r3r/1bk1qp1p/p1p5/Q1RPbp2/N3P3/8/PP3PPP/3R2K1 b - - 1 22`

Game (full game at ply): http://localhost:5173/analysis?game_id=682422&ply=42

FEN (free-play from line start): http://localhost:5173/analysis?fen=3r3r/1bk1qp1p/p1p5/Q1RPbp2/N3P3/8/PP3PPP/3R2K1%20b%20-%20-%201%2022

#### Case 374 — DOUBLE_CHECK (missed, depth 6)

Moves (SAN): `23. Rdc1 Bf4 24. dxc6 Bxc1 25. Rxc1 Qd6 26. cxb7+ Kxb7 27. h4 Rc8 28. Nc5+ Ka7`

FEN (line start): `2kr3r/1b2qp1p/p1p5/Q1RPbp2/N3P3/8/PP3PPP/3R2K1 w - - 0 23`

Game (full game at ply): http://localhost:5173/analysis?game_id=682422&ply=44

FEN (free-play from line start): http://localhost:5173/analysis?fen=2kr3r/1b2qp1p/p1p5/Q1RPbp2/N3P3/8/PP3PPP/3R2K1%20w%20-%20-%200%2023

#### Case 375 — CLEARANCE (allowed, depth 10)

Moves (SAN): `7... dxe4 8. Ne5`

FEN (line start): `r1bqk2r/ppp1bppp/2n2n2/3p2B1/3PP3/2N2N2/PP3PPP/R2QKB1R b - - 0 7`

Game (full game at ply): http://localhost:5173/analysis?game_id=682429&ply=12

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1bqk2r/ppp1bppp/2n2n2/3p2B1/3PP3/2N2N2/PP3PPP/R2QKB1R%20b%20-%20-%200%207

#### Case 376 — CLEARANCE (missed, depth 2)

Moves (SAN): `7. e3`

FEN (line start): `r1bqk2r/ppp1bppp/2n2n2/3p2B1/3P4/2N2N2/PP2PPPP/R2QKB1R w - - 0 7`

Game (full game at ply): http://localhost:5173/analysis?game_id=682429&ply=12

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1bqk2r/ppp1bppp/2n2n2/3p2B1/3P4/2N2N2/PP2PPPP/R2QKB1R%20w%20-%20-%200%207

#### Case 377 — SACRIFICE (allowed, depth 2)

Moves (SAN): `26. Rb7 fxg3 27. Qxg3 Qxg3+ 28. Kxg3 Rf7 29. Rxf7 Kxf7 30. c4 Nb6 31. Rc5 Rc8`

FEN (line start): `r4rk1/p5p1/2p4p/3nR3/3P1pq1/3Q2N1/P1P2PK1/1R6 w - - 0 26`

Game (full game at ply): http://localhost:5173/analysis?game_id=682437&ply=49

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4rk1/p5p1/2p4p/3nR3/3P1pq1/3Q2N1/P1P2PK1/1R6%20w%20-%20-%200%2026

#### Case 378 — CLEARANCE (missed, depth 6)

Moves (SAN): `9... Ne7 10. Bd3 Rc8 11. Qg4 Ng6 12. f4 Bc5+ 13. Kh1`

FEN (line start): `r2qkbnr/pp1b1ppp/4p3/1B1pP3/3Q4/2N5/PPP2PPP/R1B2RK1 b - - 0 9`

Game (full game at ply): http://localhost:5173/analysis?game_id=682439&ply=17

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qkbnr/pp1b1ppp/4p3/1B1pP3/3Q4/2N5/PPP2PPP/R1B2RK1%20b%20-%20-%200%209

#### Case 379 — PIN (allowed, depth 0)

Moves (SAN): `19. Ne4 b6 20. Nf6+ Rxf6 21. exf6 Rxg3+ 22. Kh2 Rf3 23. Re2 Rf4 24. b3 Rxf6`

FEN (line start): `6r1/1p1k1p1p/p3p2p/2bpPr2/P7/2N3PP/1PP2P2/3RR1K1 w - - 1 19`

Game (full game at ply): http://localhost:5173/analysis?game_id=682439&ply=35

FEN (free-play from line start): http://localhost:5173/analysis?fen=6r1/1p1k1p1p/p3p2p/2bpPr2/P7/2N3PP/1PP2P2/3RR1K1%20w%20-%20-%201%2019

#### Case 380 — PIN (allowed, depth 0)

Moves (SAN): `20. Ne4 Kc6`

FEN (line start): `6r1/1p1k3p/p3pp1p/2bpPr2/P7/2N3PP/1PPR1P2/4R1K1 w - - 0 20`

Game (full game at ply): http://localhost:5173/analysis?game_id=682439&ply=37

FEN (free-play from line start): http://localhost:5173/analysis?fen=6r1/1p1k3p/p3pp1p/2bpPr2/P7/2N3PP/1PPR1P2/4R1K1%20w%20-%20-%200%2020

#### Case 381 — PIN (missed, depth 0)

Moves (SAN): `21... Rxg3+ 22. Kh2`

FEN (line start): `6r1/1p1k3p/p3pr1p/P1bp4/8/2N3PP/1PPR1P2/4R1K1 b - - 0 21`

Game (full game at ply): http://localhost:5173/analysis?game_id=682439&ply=41

FEN (free-play from line start): http://localhost:5173/analysis?fen=6r1/1p1k3p/p3pr1p/P1bp4/8/2N3PP/1PPR1P2/4R1K1%20b%20-%20-%200%2021

#### Case 382 — PIN (allowed, depth 0)

Moves (SAN): `13... Nxd4 14. Qd1 Nf5 15. Bxf6 Qxf6 16. Rb1 dxc4 17. Be2 Qc3+ 18. Qd2 Qxa3 19. Bxc4`

FEN (line start): `r4rk1/ppp1qpp1/2n2n1p/3p4/2PP3B/P3PQ1P/5PP1/R3KB1R b - - 0 13`

Game (full game at ply): http://localhost:5173/analysis?game_id=682445&ply=24

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4rk1/ppp1qpp1/2n2n1p/3p4/2PP3B/P3PQ1P/5PP1/R3KB1R%20b%20-%20-%200%2013

#### Case 383 — CAPTURING_DEFENDER (missed, depth 2)

Moves (SAN): `13. Bxf6 Qxf6 14. Qxd5 Qg6 15. Be2 Rfd8 16. Qf3 Na5`

FEN (line start): `r4rk1/ppp1qpp1/2n2n1p/3p4/3P3B/P1P1PQ1P/5PP1/R3KB1R w - - 0 13`

Game (full game at ply): http://localhost:5173/analysis?game_id=682445&ply=24

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4rk1/ppp1qpp1/2n2n1p/3p4/3P3B/P1P1PQ1P/5PP1/R3KB1R%20w%20-%20-%200%2013

#### Case 384 — PIN (allowed, depth 0)

Moves (SAN): `14... Nxd4 15. Qd1 Nf5 16. Bxf6 Qxf6`

FEN (line start): `r4rk1/ppp1qpp1/2n2n1p/8/2BP3B/P3PQ1P/5PP1/R3K2R b - - 0 14`

Game (full game at ply): http://localhost:5173/analysis?game_id=682445&ply=26

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4rk1/ppp1qpp1/2n2n1p/8/2BP3B/P3PQ1P/5PP1/R3K2R%20b%20-%20-%200%2014

#### Case 385 — FORK (allowed, depth 0)

Moves (SAN): `16... Ne5 17. Qe2 g5 18. Bg3 Ne4 19. Bxe5 Qxe5 20. Qc2 b5 21. Bb3 Re7 22. Rad1`

FEN (line start): `4rrk1/1pp1qpp1/p1n2n1p/3P4/2B4B/P3PQ1P/5PP1/R4RK1 b - - 0 16`

Game (full game at ply): http://localhost:5173/analysis?game_id=682445&ply=30

FEN (free-play from line start): http://localhost:5173/analysis?fen=4rrk1/1pp1qpp1/p1n2n1p/3P4/2B4B/P3PQ1P/5PP1/R4RK1%20b%20-%20-%200%2016

#### Case 386 — CLEARANCE (missed, depth 4)

Moves (SAN): `16. Rfc1 Nd8 17. Bd3 c6 18. Rc5 Ne6 19. Re5 Rd8 20. Qf5 Rfe8 21. Rb1 Rd7`

FEN (line start): `4rrk1/1pp1qpp1/p1n2n1p/8/2BP3B/P3PQ1P/5PP1/R4RK1 w - - 0 16`

Game (full game at ply): http://localhost:5173/analysis?game_id=682445&ply=30

FEN (free-play from line start): http://localhost:5173/analysis?fen=4rrk1/1pp1qpp1/p1n2n1p/8/2BP3B/P3PQ1P/5PP1/R4RK1%20w%20-%20-%200%2016

#### Case 387 — CLEARANCE (missed, depth 2)

Moves (SAN): `18. Rf2 Qc5 19. Qf4 a5 20. Bf1 Qb6 21. e5 b4 22. Qf6 b3 23. axb3 Rae8`

FEN (line start): `r4rk1/p4p1p/3p2p1/1p1P4/4PRQ1/2qB4/P5PP/3R2K1 w - - 0 18`

Game (full game at ply): http://localhost:5173/analysis?game_id=682458&ply=34

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4rk1/p4p1p/3p2p1/1p1P4/4PRQ1/2qB4/P5PP/3R2K1%20w%20-%20-%200%2018

#### Case 388 — DISCOVERED_ATTACK (allowed, depth 5)

Moves (SAN): `16. dxc5 Nd5 17. Qb2 Be4 18. Nh4 f5 19. Bxe4 fxe4 20. c4 Bxh4 21. Rxd5 Qf6`

FEN (line start): `2rqr1k1/pp2bppp/1n3p2/2p2b2/3P4/1PP1BNPP/P3QPB1/3R1RK1 w - - 1 16`

Game (full game at ply): http://localhost:5173/analysis?game_id=682460&ply=29

FEN (free-play from line start): http://localhost:5173/analysis?fen=2rqr1k1/pp2bppp/1n3p2/2p2b2/3P4/1PP1BNPP/P3QPB1/3R1RK1%20w%20-%20-%201%2016

#### Case 389 — PIN (missed, depth 10)

Moves (SAN): `27... Rxd4 28. bxc5 Rxd3 29. cxb6 axb6 30. h4 Rxc3 31. Qd7 Ra8 32. e5 Rxg3 33. e6`

FEN (line start): `4r1k1/pp1r1pp1/1n3pp1/2q5/1P1RP1Q1/2PR2PP/P5B1/6K1 b - - 0 27`

Game (full game at ply): http://localhost:5173/analysis?game_id=682460&ply=53

FEN (free-play from line start): http://localhost:5173/analysis?fen=4r1k1/pp1r1pp1/1n3pp1/2q5/1P1RP1Q1/2PR2PP/P5B1/6K1%20b%20-%20-%200%2027

#### Case 390 — CLEARANCE (missed, depth 2)

Moves (SAN): `11. d5 Bd7 12. Qd4 Rg8 13. Bg5 Be7 14. Bxe7 Qxe7 15. c4 g5 16. Ne5 g4`

FEN (line start): `r2qkb1r/1pp2p1p/p1b1p1p1/8/3PP3/2P2N2/P4PPP/R1BQ1RK1 w - - 0 11`

Game (full game at ply): http://localhost:5173/analysis?game_id=682463&ply=20

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qkb1r/1pp2p1p/p1b1p1p1/8/3PP3/2P2N2/P4PPP/R1BQ1RK1%20w%20-%20-%200%2011

#### Case 391 — PIN (missed, depth 4)

Moves (SAN): `13. Ne5 Bd6 14. Nxc6 bxc6 15. Qa4 Kd7 16. c4 Rab8 17. Ba3 Bxa3 18. Qxa3 Rb6`

FEN (line start): `r3kb1r/1pp4p/p1b1pqp1/8/3P4/2P2N2/P4PPP/R1BQ1RK1 w - - 0 13`

Game (full game at ply): http://localhost:5173/analysis?game_id=682463&ply=24

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3kb1r/1pp4p/p1b1pqp1/8/3P4/2P2N2/P4PPP/R1BQ1RK1%20w%20-%20-%200%2013

#### Case 392 — PIN (missed, depth 6)

Moves (SAN): `23. cxd5 cxd5 24. Qxd5+ Qd6 25. Qe4 Rhf8 26. Red1 Rf6 27. Rxd6+ Rxd6 28. h4 Re8`

FEN (line start): `3r3r/2pk3p/p1p3p1/3p4/2P2q2/1Q6/P4PPP/1R2R1K1 w - - 0 23`

Game (full game at ply): http://localhost:5173/analysis?game_id=682463&ply=44

FEN (free-play from line start): http://localhost:5173/analysis?fen=3r3r/2pk3p/p1p3p1/3p4/2P2q2/1Q6/P4PPP/1R2R1K1%20w%20-%20-%200%2023

#### Case 393 — CLEARANCE (missed, depth 10)

Moves (SAN): `23. Qxf6 Be5 24. Qf7 Qd6 25. Bg5 Kd7 26. Rhf1 Rae8 27. Rf3 Kc7 28. Rdf1 Kb8`

FEN (line start): `r2k3r/ppq1nQ2/3b1ppB/2pB4/2PpP1P1/7P/PP6/2KR3R w - - 0 23`

Game (full game at ply): http://localhost:5173/analysis?game_id=682465&ply=44

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2k3r/ppq1nQ2/3b1ppB/2pB4/2PpP1P1/7P/PP6/2KR3R%20w%20-%20-%200%2023

#### Case 394 — CLEARANCE (allowed, depth 8)

Moves (SAN): `29... Kc7 30. Qg7+ Kb6 31. Rde1 Qb8 32. Qxg6 Qg3 33. h4 Rf8 34. h5 a5 35. h6`

FEN (line start): `r2kq3/pp6/2n2Qp1/2p5/2Pp2P1/7P/PP6/K2R3R b - - 0 29`

Game (full game at ply): http://localhost:5173/analysis?game_id=682465&ply=56

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2kq3/pp6/2n2Qp1/2p5/2Pp2P1/7P/PP6/K2R3R%20b%20-%20-%200%2029

#### Case 395 — SKEWER (missed, depth 4)

Moves (SAN): `29. Rhe1 Qd7 30. Qh8+ Kc7 31. Qxa8 Qd6 32. Qg8 Qh2 33. Qg7+ Kb6 34. Qxf6 Ka5`

FEN (line start): `r2kq3/pp4Q1/2n2pp1/2p5/2Pp2P1/7P/PP6/K2R3R w - - 0 29`

Game (full game at ply): http://localhost:5173/analysis?game_id=682465&ply=56

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2kq3/pp4Q1/2n2pp1/2p5/2Pp2P1/7P/PP6/K2R3R%20w%20-%20-%200%2029

#### Case 396 — CLEARANCE (allowed, depth 4)

Moves (SAN): `13... Nxe5 14. dxe5 c6 15. Nd2 Qa5 16. cxd5 cxd5 17. Bd3 Rad8 18. Qe2 Rfe8 19. Bxe4`

FEN (line start): `r2q1rk1/ppp2p2/2n4p/3pBbp1/2PPn3/P3PN2/5PPP/R2QKB1R b - - 0 13`

Game (full game at ply): http://localhost:5173/analysis?game_id=682478&ply=24

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2q1rk1/ppp2p2/2n4p/3pBbp1/2PPn3/P3PN2/5PPP/R2QKB1R%20b%20-%20-%200%2013

#### Case 397 — DISCOVERED_ATTACK (missed, depth 5)

Moves (SAN): `18. Nd4 Bh7 19. f3 Nc5 20. Bxf7+ Rxf7 21. Rxc5 Re7 22. e6 b6 23. Rc6 Bg6`

FEN (line start): `r4rk1/ppp2p2/7p/4Pbp1/2B1n3/P3PN2/5PPP/2R1K2R w - - 0 18`

Game (full game at ply): http://localhost:5173/analysis?game_id=682478&ply=34

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4rk1/ppp2p2/7p/4Pbp1/2B1n3/P3PN2/5PPP/2R1K2R%20w%20-%20-%200%2018

#### Case 398 — HANGING_PIECE (missed, depth 0)

Moves (SAN): `28. Rxc6 Rfc8`

FEN (line start): `r4rk1/5p2/p1b4p/1p2P1p1/1R6/Pp2P3/5KPP/2R5 w - - 0 28`

Game (full game at ply): http://localhost:5173/analysis?game_id=682478&ply=54

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4rk1/5p2/p1b4p/1p2P1p1/1R6/Pp2P3/5KPP/2R5%20w%20-%20-%200%2028

#### Case 399 — PIN (missed, depth 2)

Moves (SAN): `7. Bxd5 Qd7 8. Bxc6 Qxc6 9. Qf3 Qxf3 10. Nxf3 e6 11. a3 Bg4 12. Ng5 c5`

FEN (line start): `r2qkb1r/ppp1pppp/2n5/3nPb2/2BP4/2N5/PP3PPP/R1BQK1NR w - - 0 7`

Game (full game at ply): http://localhost:5173/analysis?game_id=682481&ply=12

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qkb1r/ppp1pppp/2n5/3nPb2/2BP4/2N5/PP3PPP/R1BQK1NR%20w%20-%20-%200%207

#### Case 400 — CLEARANCE (allowed, depth 10)

Moves (SAN): `14... N6d4 15. Nxd4 Nxd4 16. Qd1 Nc6 17. Ra1`

FEN (line start): `r2qk2r/ppp2ppp/2n5/3NPb2/2B5/5Q2/1Pn1NPPP/1RB2RK1 b - - 1 14`

Game (full game at ply): http://localhost:5173/analysis?game_id=682481&ply=26

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qk2r/ppp2ppp/2n5/3NPb2/2B5/5Q2/1Pn1NPPP/1RB2RK1%20b%20-%20-%201%2014

#### Case 401 — SACRIFICE (missed, depth 2)

Moves (SAN): `14. Qxf5 Nxa1 15. Bg5`

FEN (line start): `r2qk2r/ppp2ppp/2n5/3NPb2/2B5/5Q2/1Pn1NPPP/R1B2RK1 w - - 0 14`

Game (full game at ply): http://localhost:5173/analysis?game_id=682481&ply=26

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qk2r/ppp2ppp/2n5/3NPb2/2B5/5Q2/1Pn1NPPP/R1B2RK1%20w%20-%20-%200%2014

#### Case 402 — INTERMEZZO (missed, depth 10)

Moves (SAN): `11... b5 12. Bd3 b4 13. Na4 Nbd7 14. Kh1 c5 15. dxc5 Qa5 16. b3 Nxc5 17. Nxc5`

FEN (line start): `rn1q1rk1/pp2bppp/2p1pnb1/8/2BPP3/2N2N2/PPP1Q1PP/R1B2RK1 b - - 0 11`

Game (full game at ply): http://localhost:5173/analysis?game_id=682527&ply=21

FEN (free-play from line start): http://localhost:5173/analysis?fen=rn1q1rk1/pp2bppp/2p1pnb1/8/2BPP3/2N2N2/PPP1Q1PP/R1B2RK1%20b%20-%20-%200%2011

#### Case 403 — DEFLECTION (allowed, depth 8)

Moves (SAN): `20. Nf3 Qb5+ 21. Rd3 f6 22. Qd4 c5 23. a4 Qxa4 24. bxc5 Qc6 25. c4 e5`

FEN (line start): `2k1r1r1/pppq1pp1/n3p1p1/3pQ1N1/1P6/2P1P3/P3KPPP/3R3R w - - 1 20`

Game (full game at ply): http://localhost:5173/analysis?game_id=682530&ply=37

FEN (free-play from line start): http://localhost:5173/analysis?fen=2k1r1r1/pppq1pp1/n3p1p1/3pQ1N1/1P6/2P1P3/P3KPPP/3R3R%20w%20-%20-%201%2020

#### Case 404 — CLEARANCE (missed, depth 8)

Moves (SAN): `9. Bg5 Be7 10. Bxf6 Bxf6 11. a4 Be7 12. Qd3`

FEN (line start): `r2qkb1r/pp3ppp/2bp1n2/1B2p3/4P3/2N5/PPP2PPP/R1BQ1RK1 w - - 0 9`

Game (full game at ply): http://localhost:5173/analysis?game_id=682532&ply=16

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qkb1r/pp3ppp/2bp1n2/1B2p3/4P3/2N5/PPP2PPP/R1BQ1RK1%20w%20-%20-%200%209

#### Case 405 — CLEARANCE (missed, depth 2)

Moves (SAN): `10. Qd3`

FEN (line start): `r2qk2r/pp2bppp/2bp1n2/4p3/2B1P3/2N5/PPP2PPP/R1BQ1RK1 w - - 0 10`

Game (full game at ply): http://localhost:5173/analysis?game_id=682532&ply=18

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qk2r/pp2bppp/2bp1n2/4p3/2B1P3/2N5/PPP2PPP/R1BQ1RK1%20w%20-%20-%200%2010

#### Case 406 — CLEARANCE (allowed, depth 2)

Moves (SAN): `13... exf4 14. c3 Be5 15. Nxf4 Bxe4 16. Bd5 Bxf4 17. Rxf4 Bxd5 18. Qxd5 Qb6+ 19. Rf2`

FEN (line start): `r2q1rk1/1p3ppp/p1bp1b2/3Np3/2B1PP2/8/PPP3PP/R2Q1RK1 b - - 0 13`

Game (full game at ply): http://localhost:5173/analysis?game_id=682532&ply=24

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2q1rk1/1p3ppp/p1bp1b2/3Np3/2B1PP2/8/PPP3PP/R2Q1RK1%20b%20-%20-%200%2013

#### Case 407 — CLEARANCE (missed, depth 10)

Moves (SAN): `13. a4 b5 14. Bb3 a5 15. axb5 Bxb5 16. Re1 Bg5 17. Nc3 Bc6 18. Bd5 Qd7`

FEN (line start): `r2q1rk1/1p3ppp/p1bp1b2/3Np3/2B1P3/8/PPP2PPP/R2Q1RK1 w - - 0 13`

Game (full game at ply): http://localhost:5173/analysis?game_id=682532&ply=24

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2q1rk1/1p3ppp/p1bp1b2/3Np3/2B1P3/8/PPP2PPP/R2Q1RK1%20w%20-%20-%200%2013

#### Case 408 — CLEARANCE (missed, depth 6)

Moves (SAN): `18. g3 a5 19. a3 Kh8 20. Qd3 Rab8 21. Rbf1 f6 22. Ne7 Bd7 23. Nf5 Rfd8`

FEN (line start): `r4rk1/5ppp/p1bp4/1p1Nb1q1/4P3/1B6/P1P2RPP/1R1Q2K1 w - - 0 18`

Game (full game at ply): http://localhost:5173/analysis?game_id=682532&ply=34

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4rk1/5ppp/p1bp4/1p1Nb1q1/4P3/1B6/P1P2RPP/1R1Q2K1%20w%20-%20-%200%2018

#### Case 409 — PIN (allowed, depth 0)

Moves (SAN): `19... Bd4 20. Kh1 Bxf2 21. Qxf2 Bxd5 22. Bxd5 Rab8 23. h3 Qe7 24. Qd4 f6 25. Qd2`

FEN (line start): `r4r1k/5ppp/p1bp4/1p1Nb1q1/4P3/1B3Q2/P1P2RPP/5RK1 b - - 1 19`

Game (full game at ply): http://localhost:5173/analysis?game_id=682532&ply=36

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4r1k/5ppp/p1bp4/1p1Nb1q1/4P3/1B3Q2/P1P2RPP/5RK1%20b%20-%20-%201%2019

#### Case 410 — CLEARANCE (missed, depth 8)

Moves (SAN): `19. Rd1 Rac8 20. Qh3 Qd8 21. Qe3 a5 22. a3 a4 23. Ba2 g6 24. Nb6 Rb8`

FEN (line start): `r4r1k/5ppp/p1bp4/1p1Nb1q1/4P3/1B3Q2/P1P2RPP/1R4K1 w - - 0 19`

Game (full game at ply): http://localhost:5173/analysis?game_id=682532&ply=36

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4r1k/5ppp/p1bp4/1p1Nb1q1/4P3/1B3Q2/P1P2RPP/1R4K1%20w%20-%20-%200%2019

#### Case 411 — PIN (allowed, depth 2)

Moves (SAN): `21... Bxf5 22. exf5 Bd4 23. Be6 Qd2 24. c3 Bxf2+ 25. Rxf2 Qe1+ 26. Rf1 Qe5 27. Rd1`

FEN (line start): `r4r1k/3b2pp/p2p1p2/1p2bNq1/4P3/1B3Q2/P1P2RPP/5RK1 b - - 1 21`

Game (full game at ply): http://localhost:5173/analysis?game_id=682532&ply=40

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4r1k/3b2pp/p2p1p2/1p2bNq1/4P3/1B3Q2/P1P2RPP/5RK1%20b%20-%20-%201%2021

#### Case 412 — CLEARANCE (missed, depth 4)

Moves (SAN): `21. Qd3 a5 22. a3 g6 23. Ba2 Rae8 24. Nd5 Rc8 25. c3 a4 26. Kh1 Qh6`

FEN (line start): `r4r1k/3bN1pp/p2p1p2/1p2b1q1/4P3/1B3Q2/P1P2RPP/5RK1 w - - 0 21`

Game (full game at ply): http://localhost:5173/analysis?game_id=682532&ply=40

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4r1k/3bN1pp/p2p1p2/1p2b1q1/4P3/1B3Q2/P1P2RPP/5RK1%20w%20-%20-%200%2021

#### Case 413 — SACRIFICE (missed, depth 10)

Moves (SAN): `30. Rg1 Qe4 31. h3 Qxf5 32. c4 bxc4 33. Bxc4 d5 34. Bxd5 Qxd5 35. a4 Qd2`

FEN (line start): `r3r2k/6pp/3p1p2/1p3P2/8/1B6/P1P3PP/4qR1K w - - 0 30`

Game (full game at ply): http://localhost:5173/analysis?game_id=682532&ply=58

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3r2k/6pp/3p1p2/1p3P2/8/1B6/P1P3PP/4qR1K%20w%20-%20-%200%2030

#### Case 414 — EN_PASSANT (missed, depth 4)

Moves (SAN): `19. Qh4 Kb8 20. Bc1 e5 21. dxe6 fxe6 22. Bc4 d5 23. exd5 exd5 24. Bd3 c4+`

FEN (line start): `2kr3r/1p1npp2/1q1p1npb/pNpP3p/P3PP2/1P1BB1QP/2P3P1/4RRK1 w - - 0 19`

Game (full game at ply): http://localhost:5173/analysis?game_id=682533&ply=36

FEN (free-play from line start): http://localhost:5173/analysis?fen=2kr3r/1p1npp2/1q1p1npb/pNpP3p/P3PP2/1P1BB1QP/2P3P1/4RRK1%20w%20-%20-%200%2019

#### Case 415 — DISCOVERED_CHECK (missed, depth 0)

Moves (SAN): `24. Nxf7+`

FEN (line start): `1k1r3r/1p1n1p2/1q1N2p1/p1pn1P1p/P7/1P1B2QP/2Pb2P1/4RR1K w - - 0 24`

Game (full game at ply): http://localhost:5173/analysis?game_id=682533&ply=46

FEN (free-play from line start): http://localhost:5173/analysis?fen=1k1r3r/1p1n1p2/1q1N2p1/p1pn1P1p/P7/1P1B2QP/2Pb2P1/4RR1K%20w%20-%20-%200%2024

#### Case 416 — SACRIFICE (allowed, depth 2)

Moves (SAN): `26... Rxd5 27. exd5 Nd4 28. Bxd4 exd4 29. Rc5 Rxa3 30. Rxb5+ Kc8 31. d6 Ra2+ 32. Kg1`

FEN (line start): `3b4/1kp5/r1nr3p/1p1Bp1p1/1P2P3/P3BP2/2R3KP/2R5 b - - 1 26`

Game (full game at ply): http://localhost:5173/analysis?game_id=682535&ply=50

FEN (free-play from line start): http://localhost:5173/analysis?fen=3b4/1kp5/r1nr3p/1p1Bp1p1/1P2P3/P3BP2/2R3KP/2R5%20b%20-%20-%201%2026

#### Case 417 — PIN (missed, depth 4)

Moves (SAN): `26. Rxc6 Raxc6 27. Rxc6 Rxc6 28. Bc5 g4 29. a4 bxa4 30. b5 gxf3 31. Kf2 Bf6`

FEN (line start): `3b4/1kp5/r1nr3p/1p1Bp1p1/1P2P3/P3BP2/2R4P/2R3K1 w - - 0 26`

Game (full game at ply): http://localhost:5173/analysis?game_id=682535&ply=50

FEN (free-play from line start): http://localhost:5173/analysis?fen=3b4/1kp5/r1nr3p/1p1Bp1p1/1P2P3/P3BP2/2R4P/2R3K1%20w%20-%20-%200%2026

#### Case 418 — PIN (missed, depth 4)

Moves (SAN): `30. Bc5 Rd8 31. Bg1 Rd6 32. a4 Rxa4 33. Rxc6 Rxc6 34. Rxc6 Kc8 35. Rxf6 Rxb4`

FEN (line start): `8/1kp5/r1nr1b2/1p1Bp1p1/1P2P2p/P3BP1P/2R3K1/2R5 w - - 0 30`

Game (full game at ply): http://localhost:5173/analysis?game_id=682535&ply=58

FEN (free-play from line start): http://localhost:5173/analysis?fen=8/1kp5/r1nr1b2/1p1Bp1p1/1P2P2p/P3BP1P/2R3K1/2R5%20w%20-%20-%200%2030

#### Case 419 — FORK (allowed, depth 4)

Moves (SAN): `18. Rxc2 Rxa7 19. Rxc8+ Nf8 20. Nc6 Qb7 21. Nbxa7 g5 22. Nb5 Qa6 23. a3 Kg7`

FEN (line start): `r1r3k1/Q2nqppp/4pn2/1N1pN3/3P4/8/PPb1BPPP/2R2RK1 w - - 1 18`

Game (full game at ply): http://localhost:5173/analysis?game_id=682559&ply=33

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1r3k1/Q2nqppp/4pn2/1N1pN3/3P4/8/PPb1BPPP/2R2RK1%20w%20-%20-%201%2018

#### Case 420 — SACRIFICE (missed, depth 4)

Moves (SAN): `25... Kf8 26. Nc6 Qd6 27. Nxb8 Nxb8 28. Bb5 g6 29. a4 d4 30. a5 e5 31. Bd3`

FEN (line start): `1r4k1/4Nppp/n3p3/3pq3/8/3B4/PPR2PPP/5RK1 b - - 0 25`

Game (full game at ply): http://localhost:5173/analysis?game_id=682559&ply=49

FEN (free-play from line start): http://localhost:5173/analysis?fen=1r4k1/4Nppp/n3p3/3pq3/8/3B4/PPR2PPP/5RK1%20b%20-%20-%200%2025

#### Case 421 — CLEARANCE (allowed, depth 2)

Moves (SAN): `7... e6 8. Re1 Bd6 9. d4 c6 10. Bb3 Nf6 11. d5 cxd5 12. Nxd5 Nxd5 13. Qxd5`

FEN (line start): `rn1qkbnr/1pp1ppp1/p6p/5b2/2B5/2NP1N2/PPP2PPP/R1BQ1RK1 b - - 0 7`

Game (full game at ply): http://localhost:5173/analysis?game_id=682565&ply=12

FEN (free-play from line start): http://localhost:5173/analysis?fen=rn1qkbnr/1pp1ppp1/p6p/5b2/2B5/2NP1N2/PPP2PPP/R1BQ1RK1%20b%20-%20-%200%207

#### Case 422 — CLEARANCE (missed, depth 2)

Moves (SAN): `7. Ne5 e6 8. Qf3 Ne7 9. Qxb7 Nd7 10. Nxd7 Kxd7 11. Bxa6 Qb8 12. Bb5+ Kd8`

FEN (line start): `rn1qkbnr/1pp1ppp1/p6p/5b2/2B5/2N2N2/PPPP1PPP/R1BQ1RK1 w - - 0 7`

Game (full game at ply): http://localhost:5173/analysis?game_id=682565&ply=12

FEN (free-play from line start): http://localhost:5173/analysis?fen=rn1qkbnr/1pp1ppp1/p6p/5b2/2B5/2N2N2/PPPP1PPP/R1BQ1RK1%20w%20-%20-%200%207

#### Case 423 — CLEARANCE (allowed, depth 2)

Moves (SAN): `7... d5 8. exd5 Bf5 9. Qb5+ Bd7 10. Qe2+ Qe7 11. Qxe7+ Nxe7 12. Na3 Nexd5 13. Nf3`

FEN (line start): `r1bqkbnr/pp1p1ppp/8/8/1nQ1P3/8/PP3PPP/RNB1KBNR b - - 1 7`

Game (full game at ply): http://localhost:5173/analysis?game_id=682568&ply=12

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1bqkbnr/pp1p1ppp/8/8/1nQ1P3/8/PP3PPP/RNB1KBNR%20b%20-%20-%201%207

#### Case 424 — CLEARANCE (missed, depth 8)

Moves (SAN): `13. Kd1 Be7 14. Kxc2`

FEN (line start): `r2qkb1r/pb1n1ppp/1p6/1B1pP3/5Q2/2N2N2/PPn2PPP/R1B1K2R w - - 0 13`

Game (full game at ply): http://localhost:5173/analysis?game_id=682568&ply=24

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qkb1r/pb1n1ppp/1p6/1B1pP3/5Q2/2N2N2/PPn2PPP/R1B1K2R%20w%20-%20-%200%2013

#### Case 425 — SACRIFICE (allowed, depth 2)

Moves (SAN): `16... Bg7 17. Rxa1 Rc8 18. Kf1 a6 19. Bxb6 Rf8 20. Qe3 Qe7 21. Bxd7+ Qxd7 22. Rd1`

FEN (line start): `r2qkb1r/pb1n3p/1p2p1p1/1B1p4/5Q2/2N1BN2/PP2KPPP/n6R b - - 1 16`

Game (full game at ply): http://localhost:5173/analysis?game_id=682568&ply=30

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qkb1r/pb1n3p/1p2p1p1/1B1p4/5Q2/2N1BN2/PP2KPPP/n6R%20b%20-%20-%201%2016

#### Case 426 — FORK (missed, depth 8)

Moves (SAN): `16. Ne5 Qe7 17. Bxd7+ Qxd7 18. Nxd7 Kxd7 19. Ke2 Nc2 20. Qa4+ b5 21. Qxc2 Rc8`

FEN (line start): `r2qkb1r/pb1n3p/1p2p1p1/1B1p4/5Q2/2N1BN2/PP3PPP/n4K1R w - - 0 16`

Game (full game at ply): http://localhost:5173/analysis?game_id=682568&ply=30

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qkb1r/pb1n3p/1p2p1p1/1B1p4/5Q2/2N1BN2/PP3PPP/n4K1R%20w%20-%20-%200%2016

#### Case 427 — PIN (allowed, depth 0)

Moves (SAN): `22... Rde8 23. Bxg7+ Kxg7 24. Nd4 Bc8 25. f3 Bxe6 26. Kf2 g5 27. Rc1 Bd7 28. h3`

FEN (line start): `3r1r1k/pb4bp/1p2B1p1/3p4/3B4/2N2N2/PP2KPPP/R7 b - - 1 22`

Game (full game at ply): http://localhost:5173/analysis?game_id=682568&ply=42

FEN (free-play from line start): http://localhost:5173/analysis?fen=3r1r1k/pb4bp/1p2B1p1/3p4/3B4/2N2N2/PP2KPPP/R7%20b%20-%20-%201%2022

#### Case 428 — SACRIFICE (allowed, depth 6)

Moves (SAN): `24... Rf4 25. Rd1 Ba6+ 26. Kg1 Rxd4 27. Rxd4 Re8 28. f3 Rxe6 29. Rxd5 Re7 30. Kf2`

FEN (line start): `3r1r2/pb4kp/1p2B1p1/3p4/3N4/2N5/PP3PPP/R4K2 b - - 1 24`

Game (full game at ply): http://localhost:5173/analysis?game_id=682568&ply=46

FEN (free-play from line start): http://localhost:5173/analysis?fen=3r1r2/pb4kp/1p2B1p1/3p4/3N4/2N5/PP3PPP/R4K2%20b%20-%20-%201%2024

#### Case 429 — PIN (allowed, depth 0)

Moves (SAN): `31... Bxf3 32. g5 Rxe2+ 33. Kf1 d3 34. Bd7 d2 35. Ba4 Rxh2 36. Kg1 Rg2+ 37. Kf1`

FEN (line start): `8/pb4kp/1p4p1/8/3p2P1/4rP1B/PP2N2P/4K3 b - - 0 31`

Game (full game at ply): http://localhost:5173/analysis?game_id=682568&ply=60

FEN (free-play from line start): http://localhost:5173/analysis?fen=8/pb4kp/1p4p1/8/3p2P1/4rP1B/PP2N2P/4K3%20b%20-%20-%200%2031

#### Case 430 — HANGING_PIECE (allowed, depth 0)

Moves (SAN): `26. Qxb4 a5 27. Qd6 Rc6 28. Qxc6 Qxc6 29. Rxc3 Qa6 30. Kd2 a4 31. Bc2 Qa5`

FEN (line start): `2r2rk1/5ppp/pq2p3/1p1pP3/1b4Q1/1BnKPN1P/P5P1/2R4R w - - 0 26`

Game (full game at ply): http://localhost:5173/analysis?game_id=682578&ply=49

FEN (free-play from line start): http://localhost:5173/analysis?fen=2r2rk1/5ppp/pq2p3/1p1pP3/1b4Q1/1BnKPN1P/P5P1/2R4R%20w%20-%20-%200%2026

#### Case 431 — FORK (missed, depth 2)

Moves (SAN): `25... Ne4 26. Qf4 Nf2+ 27. Ke2 Nxh1 28. Rxh1 Qc7 29. Nd4 Bxb4 30. Bc2 h6 31. g4`

FEN (line start): `2r2rk1/4bppp/pq2p3/1p1pP3/1P4Q1/1BnKPN1P/P5P1/2R4R b - - 0 25`

Game (full game at ply): http://localhost:5173/analysis?game_id=682578&ply=49

FEN (free-play from line start): http://localhost:5173/analysis?fen=2r2rk1/4bppp/pq2p3/1p1pP3/1P4Q1/1BnKPN1P/P5P1/2R4R%20b%20-%20-%200%2025

#### Case 432 — HANGING_PIECE (allowed, depth 0)

Moves (SAN): `18... Nxe5 19. Nc4 Nxc4 20. Rxc4 b5 21. Rc6 Ba3 22. e5 Re8 23. f4 a5 24. Kf1`

FEN (line start): `2k2b1r/p1p3pp/1pn5/4B3/4P3/N7/P4PPP/2RR2K1 b - - 1 18`

Game (full game at ply): http://localhost:5173/analysis?game_id=682595&ply=34

FEN (free-play from line start): http://localhost:5173/analysis?fen=2k2b1r/p1p3pp/1pn5/4B3/4P3/N7/P4PPP/2RR2K1%20b%20-%20-%201%2018

#### Case 433 — CLEARANCE (allowed, depth 8)

Moves (SAN): `50. Kc5 Rxg4 51. Kd6 Kf4 52. e6 Rg5 53. e7 Re5 54. Be6 Rxe4 55. e8=Q Kg5`

FEN (line start): `8/8/1K4p1/3BP1k1/4P1P1/6r1/8/8 w - - 1 50`

Game (full game at ply): http://localhost:5173/analysis?game_id=682602&ply=97

FEN (free-play from line start): http://localhost:5173/analysis?fen=8/8/1K4p1/3BP1k1/4P1P1/6r1/8/8%20w%20-%20-%201%2050

#### Case 434 — PROMOTION (allowed, depth 2)

Moves (SAN): `51. e7 Rg3 52. e8=Q Rd3 53. Qe7+ Kh6 54. Qf8+ Kg5 55. Qc5 Kf4 56. Qd6+ Ke3`

FEN (line start): `8/8/1K2P1p1/3B2k1/4P1r1/8/8/8 w - - 0 51`

Game (full game at ply): http://localhost:5173/analysis?game_id=682602&ply=99

FEN (free-play from line start): http://localhost:5173/analysis?fen=8/8/1K2P1p1/3B2k1/4P1r1/8/8/8%20w%20-%20-%200%2051

#### Case 435 — HANGING_PIECE (allowed, depth 0)

Moves (SAN): `54. Bxb3 Kg5 55. e5 Kf4 56. e6 g5 57. e7 g4 58. Qh5 Kg3 59. e8=Q Kf3`

FEN (line start): `4Q3/8/6p1/2KB4/4P2k/1r6/8/8 w - - 1 54`

Game (full game at ply): http://localhost:5173/analysis?game_id=682602&ply=105

FEN (free-play from line start): http://localhost:5173/analysis?fen=4Q3/8/6p1/2KB4/4P2k/1r6/8/8%20w%20-%20-%201%2054

#### Case 436 — SACRIFICE (allowed, depth 6)

Moves (UCI — SAN unavailable): `e8c8 c1g5 f8b4 e1f1 b4c5 g5d8 h8d8 d1c2 c5d4 a1e1 d4e5 c2e4`

FEN (line start): `r3kb1r/pppq1ppp/8/4P3/3Np3/8/PP3PPP/R1BQK2R b - - 0 11`

Game (full game at ply): http://localhost:5173/analysis?game_id=682653&ply=20

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3kb1r/pppq1ppp/8/4P3/3Np3/8/PP3PPP/R1BQK2R%20b%20-%20-%200%2011

#### Case 437 — CLEARANCE (allowed, depth 4)

Moves (SAN): `15... Qxd1+ 16. Ne1 Qa4 17. g3 Rd1 18. Kg2 Rxc1 19. Bxc1 Qc6 20. Nc2 e3+ 21. f3`

FEN (line start): `2kr3r/pp1q1ppp/8/2p1P3/1b2p3/4B3/PPN2PPP/2RQ1K1R b - - 1 15`

Game (full game at ply): http://localhost:5173/analysis?game_id=682653&ply=28

FEN (free-play from line start): http://localhost:5173/analysis?fen=2kr3r/pp1q1ppp/8/2p1P3/1b2p3/4B3/PPN2PPP/2RQ1K1R%20b%20-%20-%201%2015

#### Case 438 — PIN (missed, depth 0)

Moves (SAN): `15. Qe2 Kb8 16. Nb5 Rhe8 17. h4 c4 18. Nd6 Rxe5 19. Nxc4 Rd5 20. g3 b5`

FEN (line start): `2kr3r/pp1q1ppp/8/2p1P3/1b1Np3/4B3/PP3PPP/2RQ1K1R w - - 0 15`

Game (full game at ply): http://localhost:5173/analysis?game_id=682653&ply=28

FEN (free-play from line start): http://localhost:5173/analysis?fen=2kr3r/pp1q1ppp/8/2p1P3/1b1Np3/4B3/PP3PPP/2RQ1K1R%20w%20-%20-%200%2015

#### Case 439 — PIN (missed, depth 2)

Moves (SAN): `16. Qe2 Ba5 17. Nd4 Qxe5 18. Nb3 Bb6 19. Nxc5 Kb8 20. g3 Qf5 21. Kg2 Rd5`

FEN (line start): `2kr3r/pp3ppp/8/2p1Pq2/1b2p3/4B3/PPN2PPP/2RQ1K1R w - - 0 16`

Game (full game at ply): http://localhost:5173/analysis?game_id=682653&ply=30

FEN (free-play from line start): http://localhost:5173/analysis?fen=2kr3r/pp3ppp/8/2p1Pq2/1b2p3/4B3/PPN2PPP/2RQ1K1R%20w%20-%20-%200%2016

#### Case 440 — SACRIFICE (missed, depth 10)

Moves (SAN): `29. Rd6+ Kb5 30. Be5 Qa2 31. Rd5+ Ka6 32. Rd1 b2 33. Bxb2 Qxb2 34. h3 Kb5`

FEN (line start): `8/p2R1ppp/qpk5/8/4pB2/1p6/5PPP/6K1 w - - 0 29`

Game (full game at ply): http://localhost:5173/analysis?game_id=682653&ply=56

FEN (free-play from line start): http://localhost:5173/analysis?fen=8/p2R1ppp/qpk5/8/4pB2/1p6/5PPP/6K1%20w%20-%20-%200%2029

#### Case 441 — CLEARANCE (missed, depth 10)

Moves (SAN): `12. Nxg5 hxg5 13. Qe1 Bh5 14. Rf5 Bg6 15. Bxg5 Qe8 16. Qh4 Nd7 17. Re1 Qe6`

FEN (line start): `rn1q1rk1/pp3pp1/2p4p/3pP1b1/3P2b1/2PB1N2/P1PQ2PP/R1B2RK1 w - - 0 12`

Game (full game at ply): http://localhost:5173/analysis?game_id=682677&ply=22

FEN (free-play from line start): http://localhost:5173/analysis?fen=rn1q1rk1/pp3pp1/2p4p/3pP1b1/3P2b1/2PB1N2/P1PQ2PP/R1B2RK1%20w%20-%20-%200%2012

#### Case 442 — CLEARANCE (missed, depth 8)

Moves (SAN): `16. Nxf5 Bxf5 17. Qxg5 hxg5 18. Bxf5 Re8 19. Rf3 Re7 20. Rcf1 Nd7 21. Rg3 Nf8`

FEN (line start): `rn3rk1/pp4p1/2p4p/3pPpq1/3P2bN/2PB2Q1/P1P3PP/2R2RK1 w - - 0 16`

Game (full game at ply): http://localhost:5173/analysis?game_id=682677&ply=30

FEN (free-play from line start): http://localhost:5173/analysis?fen=rn3rk1/pp4p1/2p4p/3pPpq1/3P2bN/2PB2Q1/P1P3PP/2R2RK1%20w%20-%20-%200%2016

#### Case 443 — CLEARANCE (missed, depth 6)

Moves (SAN): `17. Ng6 Nd7 18. h4 Qh5 19. Ne7+ Kh8 20. Bg6 Rae8 21. Bxh5 Bxh5 22. Qd2 f3`

FEN (line start): `rn3rk1/pp4p1/2p4p/3pP1q1/3P1pbN/2PB4/P1P2QPP/2R2RK1 w - - 0 17`

Game (full game at ply): http://localhost:5173/analysis?game_id=682677&ply=32

FEN (free-play from line start): http://localhost:5173/analysis?fen=rn3rk1/pp4p1/2p4p/3pP1q1/3P1pbN/2PB4/P1P2QPP/2R2RK1%20w%20-%20-%200%2017

#### Case 444 — HANGING_PIECE (allowed, depth 0)

Moves (SAN): `13... Bxc5 14. Nf2 Bb4+ 15. Bd2 Bxd2+ 16. Qxd2 Qf5 17. Ne4 Kf7`

FEN (line start): `r3kbnr/pppq4/2n2Pp1/2N1p1Pp/3p4/3P1P1N/PPP1Q2P/R1B1K2R b - - 1 13`

Game (full game at ply): http://localhost:5173/analysis?game_id=682681&ply=24

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3kbnr/pppq4/2n2Pp1/2N1p1Pp/3p4/3P1P1N/PPP1Q2P/R1B1K2R%20b%20-%20-%201%2013

#### Case 445 — DEFLECTION (allowed, depth 6)

Moves (SAN): `14... Qh4+ 15. Kd1 Bxc5 16. b4 Bxb4 17. Bxb4 Qxg5 18. f7+ Kxf7 19. Bd2 Qf5 20. Rg1`

FEN (line start): `r3kbnr/ppp5/2n2Pp1/2N1p1Pp/3p4/3P1P1q/PPPBQ2P/R3K2R b - - 1 14`

Game (full game at ply): http://localhost:5173/analysis?game_id=682681&ply=26

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3kbnr/ppp5/2n2Pp1/2N1p1Pp/3p4/3P1P1q/PPPBQ2P/R3K2R%20b%20-%20-%201%2014

#### Case 446 — HANGING_PIECE (allowed, depth 0)

Moves (SAN): `18... Rxd5 19. Rxe2`

FEN (line start): `r5k1/ppp2ppp/8/2bB3r/2N4N/3P4/PPPBn2P/1K2R3 b - - 1 18`

Game (full game at ply): http://localhost:5173/analysis?game_id=682688&ply=34

FEN (free-play from line start): http://localhost:5173/analysis?fen=r5k1/ppp2ppp/8/2bB3r/2N4N/3P4/PPPBn2P/1K2R3%20b%20-%20-%201%2018

#### Case 447 — FORK (allowed, depth 2)

Moves (SAN): `19... Rxd5 20. Bxc7 Bf2 21. Re4 f5 22. Rf4 Bxh4 23. Rxh4 b5 24. Nd2 Re8 25. b4`

FEN (line start): `r5k1/ppp2ppp/8/2bB3r/2N2B1N/3P4/PPP4P/1K2R3 b - - 0 19`

Game (full game at ply): http://localhost:5173/analysis?game_id=682688&ply=36

FEN (free-play from line start): http://localhost:5173/analysis?fen=r5k1/ppp2ppp/8/2bB3r/2N2B1N/3P4/PPP4P/1K2R3%20b%20-%20-%200%2019

#### Case 448 — CLEARANCE (missed, depth 2)

Moves (SAN): `17. f4 Be7 18. Rf2 a6 19. a4 b4 20. Nc4 Qg6 21. Qe2 gxf4 22. Bxf4 Rc8`

FEN (line start): `r3kbr1/pb3p2/4pq1p/1p2N1pQ/3pP3/3P4/PPPB1PPP/R4RK1 w - - 0 17`

Game (full game at ply): http://localhost:5173/analysis?game_id=682690&ply=32

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3kbr1/pb3p2/4pq1p/1p2N1pQ/3pP3/3P4/PPPB1PPP/R4RK1%20w%20-%20-%200%2017

#### Case 449 — TRAPPED_PIECE (allowed, depth 2)

Moves (SAN): `14. hxg6 fxg6 15. Bxh1 e5 16. a4`

FEN (line start): `r3kb1r/pp1nppp1/2p3bp/7P/2N5/2P3P1/PP2N1B1/R1B1K2n w - - 0 14`

Game (full game at ply): http://localhost:5173/analysis?game_id=682691&ply=25

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3kb1r/pp1nppp1/2p3bp/7P/2N5/2P3P1/PP2N1B1/R1B1K2n%20w%20-%20-%200%2014

#### Case 450 — HANGING_PIECE (allowed, depth 0)

Moves (SAN): `19. Nxd6+ Ke7`

FEN (line start): `r3k2r/pp1n1pp1/2pbp2p/8/2N2N2/2P2KP1/PP6/R1B5 w - - 1 19`

Game (full game at ply): http://localhost:5173/analysis?game_id=682691&ply=35

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3k2r/pp1n1pp1/2pbp2p/8/2N2N2/2P2KP1/PP6/R1B5%20w%20-%20-%201%2019

#### Case 451 — FORK (missed, depth 6)

Moves (SAN): `28... Rd2 29. Ne2 Rxa2 30. Bd6 Rd2 31. Bf4 Nh2+ 32. Kf2 Nxf1 33. Kxf1 Rd3 34. b4`

FEN (line start): `3r2k1/p5p1/4p2p/5p2/5Nn1/BPP2KP1/P7/5R2 b - - 0 28`

Game (full game at ply): http://localhost:5173/analysis?game_id=682691&ply=55

FEN (free-play from line start): http://localhost:5173/analysis?fen=3r2k1/p5p1/4p2p/5p2/5Nn1/BPP2KP1/P7/5R2%20b%20-%20-%200%2028

#### Case 452 — FORK (missed, depth 0)

Moves (SAN): `29... Nh2+ 30. Kg2 Nxf1 31. Kxf1 e5 32. Ne2 Kf7 33. c4 g5 34. c5 h5 35. b4`

FEN (line start): `4r1k1/p5p1/3Bp2p/5p2/5Nn1/1PP2KP1/P7/5R2 b - - 0 29`

Game (full game at ply): http://localhost:5173/analysis?game_id=682691&ply=57

FEN (free-play from line start): http://localhost:5173/analysis?fen=4r1k1/p5p1/3Bp2p/5p2/5Nn1/1PP2KP1/P7/5R2%20b%20-%20-%200%2029

#### Case 453 — TRAPPED_PIECE (missed, depth 8)

Moves (SAN): `37... h5 38. c5 Ke6 39. Ng7+ Kf6 40. Nxh5+ Kg6 41. Nxf4+ gxf4 42. Bb4 Kf5 43. Kg2`

FEN (line start): `3r4/p4k2/7p/5Np1/2P2p2/BP6/P7/5K2 b - - 0 37`

Game (full game at ply): http://localhost:5173/analysis?game_id=682691&ply=73

FEN (free-play from line start): http://localhost:5173/analysis?fen=3r4/p4k2/7p/5Np1/2P2p2/BP6/P7/5K2%20b%20-%20-%200%2037

#### Case 454 — DISCOVERED_CHECK (allowed, depth 4)

Moves (SAN): `41. Ne5+ Kf6 42. Nc4 Ke7 43. c6+ Rxa3 44. Nxa3 Kd6 45. Nb5+ Kxc6 46. Nxa7+ Kc5`

FEN (line start): `8/p7/6k1/2P3p1/5pN1/BP6/r7/5K2 w - - 0 41`

Game (full game at ply): http://localhost:5173/analysis?game_id=682691&ply=79

FEN (free-play from line start): http://localhost:5173/analysis?fen=8/p7/6k1/2P3p1/5pN1/BP6/r7/5K2%20w%20-%20-%200%2041

#### Case 455 — FORK (missed, depth 2)

Moves (SAN): `25... Qxg4+ 26. hxg4 d4 27. b4 dxc3 28. Ra3 Rb8 29. Re4 Rfc8 30. Rxe5 Rxb4 31. Rxc3`

FEN (line start): `4rrk1/5ppp/p7/3ppq2/P4nQ1/1PN1RP1P/R1P2P2/6K1 b - - 0 25`

Game (full game at ply): http://localhost:5173/analysis?game_id=682700&ply=49

FEN (free-play from line start): http://localhost:5173/analysis?fen=4rrk1/5ppp/p7/3ppq2/P4nQ1/1PN1RP1P/R1P2P2/6K1%20b%20-%20-%200%2025

#### Case 456 — ATTRACTION (allowed, depth 0)

Moves (SAN): `14. Bxf5 Qxf5 15. g4 Qf6 16. f5 e4 17. dxe4 d3 18. Nec3 Be5 19. Qxd3 Rd8`

FEN (line start): `r3nrk1/pppq2pp/2nb4/4pb2/3pBP2/PP1P2PP/2P1N3/RNBQK2R w - - 1 14`

Game (full game at ply): http://localhost:5173/analysis?game_id=682742&ply=25

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3nrk1/pppq2pp/2nb4/4pb2/3pBP2/PP1P2PP/2P1N3/RNBQK2R%20w%20-%20-%201%2014

#### Case 457 — SKEWER (missed, depth 10)

Moves (SAN): `21... Rxd3 22. Qxd3 Qxd3 23. Rd1 Qe3 24. Rd2 Re8 25. Kd1 Ne4 26. Nxe4 Qxb3+ 27. Ke1`

FEN (line start): `3r1rk1/ppp3pp/2n2n2/8/5P2/PPNP3q/3QN3/R3KR2 b - - 0 21`

Game (full game at ply): http://localhost:5173/analysis?game_id=682742&ply=41

FEN (free-play from line start): http://localhost:5173/analysis?fen=3r1rk1/ppp3pp/2n2n2/8/5P2/PPNP3q/3QN3/R3KR2%20b%20-%20-%200%2021

#### Case 458 — CLEARANCE (allowed, depth 10)

Moves (SAN): `7... cxd4 8. Qxd4 c5 9. Qf4 Ne7`

FEN (line start): `r1bqkbnr/5ppp/p1p1p3/2ppP3/3P4/2N2N2/PPP2PPP/R1BQK2R b - - 0 7`

Game (full game at ply): http://localhost:5173/analysis?game_id=682745&ply=12

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1bqkbnr/5ppp/p1p1p3/2ppP3/3P4/2N2N2/PPP2PPP/R1BQK2R%20b%20-%20-%200%207

#### Case 459 — PIN (missed, depth 4)

Moves (SAN): `21. Qg5 f5 22. exf6 g6 23. f4 Ra7 24. f5 exf5 25. Rfe1 Qc6 26. Re7 Rf7`

FEN (line start): `r1b2rk1/2q2ppp/4p3/p1ppP2N/5Q2/1P6/P1P2PPP/R4RK1 w - - 0 21`

Game (full game at ply): http://localhost:5173/analysis?game_id=682745&ply=40

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1b2rk1/2q2ppp/4p3/p1ppP2N/5Q2/1P6/P1P2PPP/R4RK1%20w%20-%20-%200%2021

#### Case 460 — PIN (missed, depth 0)

Moves (SAN): `26. Nxh5+ Kg8 27. Re3 Qxe5 28. Qxe5 f6 29. Nxf6+ Rxf6 30. Qxf6 a4 31. Qxg6+ Kf8`

FEN (line start): `r1b2r2/2q2pk1/4pNp1/p2pP1Qp/2p5/1P6/P1P2PPP/R3R1K1 w - - 0 26`

Game (full game at ply): http://localhost:5173/analysis?game_id=682745&ply=50

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1b2r2/2q2pk1/4pNp1/p2pP1Qp/2p5/1P6/P1P2PPP/R3R1K1%20w%20-%20-%200%2026

#### Case 461 — CLEARANCE (allowed, depth 2)

Moves (SAN): `9... e5 10. dxe5 Bb4+ 11. Nc3 Qxd1+ 12. Bxd1 Bxc3+ 13. bxc3 Nxe5`

FEN (line start): `r2qkbnr/p3pppp/2n5/1p6/2pPP3/4BB2/1P3PPP/RN1QK2R b - - 1 9`

Game (full game at ply): http://localhost:5173/analysis?game_id=682746&ply=16

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qkbnr/p3pppp/2n5/1p6/2pPP3/4BB2/1P3PPP/RN1QK2R%20b%20-%20-%201%209

#### Case 462 — FORK (missed, depth 8)

Moves (SAN): `12. Nc3 Qd7 13. Ra5 Nc8 14. Nxb5 Bb4 15. Nc7+ Qxc7 16. Qa4+ Nd7 17. Qxb4 Rb8`

FEN (line start): `r2qkb1r/p3nppp/5n2/1p1Pp3/2p1P3/4BB2/1P3PPP/RN1Q1RK1 w - - 0 12`

Game (full game at ply): http://localhost:5173/analysis?game_id=682746&ply=22

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qkb1r/p3nppp/5n2/1p1Pp3/2p1P3/4BB2/1P3PPP/RN1Q1RK1%20w%20-%20-%200%2012

#### Case 463 — INTERMEZZO (missed, depth 8)

Moves (SAN): `8... Ne4 9. Qc1 Ba5 10. b4 Nxc3 11. bxa5 Ne4 12. Nf3 Qxa5+ 13. Nd2 h5 14. f3`

FEN (line start): `r1bqk2r/pp3ppp/2n2n2/3pp3/1b6/P1N1P1B1/1PPQ1PPP/R3KBNR b - - 0 8`

Game (full game at ply): http://localhost:5173/analysis?game_id=682752&ply=15

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1bqk2r/pp3ppp/2n2n2/3pp3/1b6/P1N1P1B1/1PPQ1PPP/R3KBNR%20b%20-%20-%200%208

#### Case 464 — INTERMEZZO (missed, depth 4)

Moves (SAN): `15... Nxg3 16. Nxf5 Qg5+ 17. Kb1 Nxf5 18. h4 Qg4 19. g3 Rad8 20. Bh3 Qh5 21. Qf1`

FEN (line start): `r2qr1k1/pp3ppp/2n5/5b2/3Nn3/P2Q2B1/1PP2PPP/2KR1B1R b - - 0 15`

Game (full game at ply): http://localhost:5173/analysis?game_id=682752&ply=29

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qr1k1/pp3ppp/2n5/5b2/3Nn3/P2Q2B1/1PP2PPP/2KR1B1R%20b%20-%20-%200%2015

#### Case 465 — FORK (missed, depth 4)

Moves (SAN): `17... Qg5+ 18. Kb1 Bxf1 19. h4 Qf6 20. Rdxf1 Qxc6 21. h5 h6 22. Bd4 f6 23. Rf4`

FEN (line start): `r2qr1k1/pp3ppp/2N5/8/8/P2b4/1PP2BPP/2KR1B1R b - - 0 17`

Game (full game at ply): http://localhost:5173/analysis?game_id=682752&ply=33

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qr1k1/pp3ppp/2N5/8/8/P2b4/1PP2BPP/2KR1B1R%20b%20-%20-%200%2017

#### Case 466 — CLEARANCE (allowed, depth 6)

Moves (SAN): `23. Bc3 Qe4 24. Kb2 Re3 25. Rxe3 Qxe3 26. Bc4 a4 27. Rf1 Rf8 28. g3 c5`

FEN (line start): `r5k1/5ppp/2p5/p2q4/3B4/PP1R4/K1P3PP/4rB1R w - - 0 23`

Game (full game at ply): http://localhost:5173/analysis?game_id=682752&ply=43

FEN (free-play from line start): http://localhost:5173/analysis?fen=r5k1/5ppp/2p5/p2q4/3B4/PP1R4/K1P3PP/4rB1R%20w%20-%20-%200%2023

#### Case 467 — PIN (missed, depth 6)

Moves (SAN): `22... Qf5 23. g4 Qe4 24. Rg1 Qf4 25. Be2 Rxe2 26. Kb1 Qxh2 27. Rgd1 Rd8 28. g5`

FEN (line start): `r5k1/p4ppp/2p5/3q4/3B4/PP1R4/K1P3PP/4rB1R b - - 0 22`

Game (full game at ply): http://localhost:5173/analysis?game_id=682752&ply=43

FEN (free-play from line start): http://localhost:5173/analysis?fen=r5k1/p4ppp/2p5/3q4/3B4/PP1R4/K1P3PP/4rB1R%20b%20-%20-%200%2022

#### Case 468 — DISCOVERED_CHECK (allowed, depth 0)

Moves (SAN): `19... Nxe4+ 20. Kh1 Nxd2 21. Bxd2 f5 22. bxa4 Qb2 23. Rfc1 e4 24. c5 Nxc5 25. dxc6`

FEN (line start): `r4rk1/1p1n1pb1/1qpp2pB/2nPp3/p1P1P3/1PN4P/P1BQ2P1/R4RK1 b - - 1 19`

Game (full game at ply): http://localhost:5173/analysis?game_id=682760&ply=36

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4rk1/1p1n1pb1/1qpp2pB/2nPp3/p1P1P3/1PN4P/P1BQ2P1/R4RK1%20b%20-%20-%201%2019

#### Case 469 — CLEARANCE (missed, depth 6)

Moves (SAN): `32. Rh5 Kg6 33. Rxh3 d4 34. g4 Rd6 35. Rd3 Rb6 36. b3 Ra6 37. a4 dxc3`

FEN (line start): `3r4/pp3k2/4p2p/3pR3/8/2P3Pp/PP2KP1P/8 w - - 0 32`

Game (full game at ply): http://localhost:5173/analysis?game_id=682774&ply=62

FEN (free-play from line start): http://localhost:5173/analysis?fen=3r4/pp3k2/4p2p/3pR3/8/2P3Pp/PP2KP1P/8%20w%20-%20-%200%2032

#### Case 470 — SELF_INTERFERENCE (missed, depth 2)

Moves (SAN): `6. Ng5 Bd7 7. cxd5 Nd4 8. e3 Ne2 9. Nf3 Nxc1 10. Nxe5 Nxd3+ 11. Qxd3 Nf6`

FEN (line start): `r2qkbnr/ppp3pp/2n1b3/3ppp2/2P5/3P1NP1/PP2PPBP/RNBQK2R w - - 0 6`

Game (full game at ply): http://localhost:5173/analysis?game_id=682784&ply=10

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qkbnr/ppp3pp/2n1b3/3ppp2/2P5/3P1NP1/PP2PPBP/RNBQK2R%20w%20-%20-%200%206

#### Case 471 — CLEARANCE (missed, depth 2)

Moves (SAN): `8... c5 9. Qe2 Qa5+ 10. Nd2 cxd4 11. Bxd4 Nc6 12. Bc3 Qc5 13. Nf3 Nh5 14. Bxg7`

FEN (line start): `rn1q1rk1/ppp1ppbp/3p1np1/8/2PPP3/3BBQ1P/PP3PP1/RN2K2R b - - 0 8`

Game (full game at ply): http://localhost:5173/analysis?game_id=682788&ply=15

FEN (free-play from line start): http://localhost:5173/analysis?fen=rn1q1rk1/ppp1ppbp/3p1np1/8/2PPP3/3BBQ1P/PP3PP1/RN2K2R%20b%20-%20-%200%208

#### Case 472 — DEFLECTION (missed, depth 4)

Moves (SAN): `21... Kf8 22. Rd7 e3 23. fxe3 Rxg3+ 24. Kh1 Be5 25. Nd5 Kg8 26. Rf1 Re8 27. c5`

FEN (line start): `r5k1/ppp1N1bp/6p1/6rn/2P1p3/1P1R2PP/P4P2/3R2K1 b - - 0 21`

Game (full game at ply): http://localhost:5173/analysis?game_id=682788&ply=41

FEN (free-play from line start): http://localhost:5173/analysis?fen=r5k1/ppp1N1bp/6p1/6rn/2P1p3/1P1R2PP/P4P2/3R2K1%20b%20-%20-%200%2021

#### Case 473 — PROMOTION (missed, depth 4)

Moves (SAN): `30... Nxf4 31. gxf4+ Kxf4 32. Kg2 e1=Q 33. Nd5+ Kg5 34. Re7 Rxe7 35. Nxe7 Qe2+ 36. Kg3`

FEN (line start): `8/pR2N2p/6p1/4r1kn/2P2P2/1P4PP/P3p3/6K1 b - - 0 30`

Game (full game at ply): http://localhost:5173/analysis?game_id=682788&ply=59

FEN (free-play from line start): http://localhost:5173/analysis?fen=8/pR2N2p/6p1/4r1kn/2P2P2/1P4PP/P3p3/6K1%20b%20-%20-%200%2030

#### Case 474 — PIN (allowed, depth 10)

Moves (SAN): `13... Qxf2+ 14. Kh1 Qc5 15. Re2 Nc6 16. d4 Qh5 17. Bxc7`

FEN (line start): `rnb1k2r/ppp1b2p/5p2/2q5/5Bn1/2NP1NP1/PP3PBP/R2QR1K1 b - - 1 13`

Game (full game at ply): http://localhost:5173/analysis?game_id=682809&ply=24

FEN (free-play from line start): http://localhost:5173/analysis?fen=rnb1k2r/ppp1b2p/5p2/2q5/5Bn1/2NP1NP1/PP3PBP/R2QR1K1%20b%20-%20-%201%2013

#### Case 475 — SACRIFICE (missed, depth 10)

Moves (SAN): `13. d4 Qb5 14. Nc3 Qxb2 15. Bd2 Nc6 16. Rb1 Qa3 17. Nb5 Qxa2 18. Ra1 Qb2`

FEN (line start): `rnb1k2r/ppp1b2p/5p2/2q5/5Bn1/3P1NP1/PP3PBP/RN1QR1K1 w - - 0 13`

Game (full game at ply): http://localhost:5173/analysis?game_id=682809&ply=24

FEN (free-play from line start): http://localhost:5173/analysis?fen=rnb1k2r/ppp1b2p/5p2/2q5/5Bn1/3P1NP1/PP3PBP/RN1QR1K1%20w%20-%20-%200%2013

#### Case 476 — SACRIFICE (missed, depth 6)

Moves (SAN): `15. g3 Qxd4 16. Bxg4 Rxe1+ 17. Qxe1 Qxg4 18. Qe3 b6 19. Kg2 Re8 20. Qf3 Qd7`

FEN (line start): `4rrk1/ppp2pp1/3b1n1p/4q3/3N2b1/2NP4/PPP1BPPP/R2QR1K1 w - - 0 15`

Game (full game at ply): http://localhost:5173/analysis?game_id=682811&ply=28

FEN (free-play from line start): http://localhost:5173/analysis?fen=4rrk1/ppp2pp1/3b1n1p/4q3/3N2b1/2NP4/PPP1BPPP/R2QR1K1%20w%20-%20-%200%2015

#### Case 477 — HANGING_PIECE (allowed, depth 0)

Moves (SAN): `18... Nxg4 19. Ng1 Rxe1+ 20. Rxe1 Qh1 21. g3 f5 22. Nd1 Nh2+ 23. Ke2 f4 24. gxf4`

FEN (line start): `4r1k1/ppp2pp1/3b1n1p/8/6B1/2NP4/PPP1NPPq/R3QK2 b - - 1 18`

Game (full game at ply): http://localhost:5173/analysis?game_id=682811&ply=34

FEN (free-play from line start): http://localhost:5173/analysis?fen=4r1k1/ppp2pp1/3b1n1p/8/6B1/2NP4/PPP1NPPq/R3QK2%20b%20-%20-%201%2018

#### Case 478 — SACRIFICE (missed, depth 2)

Moves (SAN): `18. Qxe8+ Nxe8 19. Nde2 Qh1+ 20. Ng1 Bh2 21. Ne2 Bxg1 22. Nxg1 Qh4 23. Bf3 Nf6`

FEN (line start): `4r1k1/ppp2pp1/3b1n1p/8/3N2B1/2NP4/PPP2PPq/R3QK2 w - - 0 18`

Game (full game at ply): http://localhost:5173/analysis?game_id=682811&ply=34

FEN (free-play from line start): http://localhost:5173/analysis?fen=4r1k1/ppp2pp1/3b1n1p/8/3N2B1/2NP4/PPP2PPq/R3QK2%20w%20-%20-%200%2018

#### Case 479 — CLEARANCE (allowed, depth 6)

Moves (SAN): `21. f3 Reb8 22. Qc2 Qc6 23. d4 Nc4 24. Qd3 Qd5 25. Rab1 Rb2 26. Rxb2 Rxb2`

FEN (line start): `4r1k1/1rpq1p2/pn3p2/2B1p3/8/1QPP2P1/P3PPKP/R3R3 w - - 1 21`

Game (full game at ply): http://localhost:5173/analysis?game_id=682854&ply=39

FEN (free-play from line start): http://localhost:5173/analysis?fen=4r1k1/1rpq1p2/pn3p2/2B1p3/8/1QPP2P1/P3PPKP/R3R3%20w%20-%20-%201%2021

#### Case 480 — CLEARANCE (missed, depth 2)

Moves (SAN): `18... Ne2+ 19. Kf1 Qd4 20. Qh4 Qg1+ 21. Kxe2 Qxg2+ 22. Ke1 Rxd3 23. Qg3 Qxg3+ 24. hxg3`

FEN (line start): `3r1rk1/pp4pp/2pqp3/5p2/3n2n1/3B1P1Q/PPPB2PP/R2R2K1 b - - 0 18`

Game (full game at ply): http://localhost:5173/analysis?game_id=682871&ply=35

FEN (free-play from line start): http://localhost:5173/analysis?fen=3r1rk1/pp4pp/2pqp3/5p2/3n2n1/3B1P1Q/PPPB2PP/R2R2K1%20b%20-%20-%200%2018

#### Case 481 — DISCOVERED_ATTACK (missed, depth 1)

Moves (SAN): `18... Bb4+ 19. c3 Qxf7 20. cxb4 Qxf2+ 21. Kd1 e3 22. Re1 Qxg2 23. a4 Kb8 24. b5`

FEN (line start): `2kr3r/pp1qbQ1p/8/8/3pp3/7P/PPPK1PP1/R1B4R b - - 0 18`

Game (full game at ply): http://localhost:5173/analysis?game_id=682883&ply=35

FEN (free-play from line start): http://localhost:5173/analysis?fen=2kr3r/pp1qbQ1p/8/8/3pp3/7P/PPPK1PP1/R1B4R%20b%20-%20-%200%2018

#### Case 482 — CLEARANCE (missed, depth 2)

Moves (SAN): `8... e6 9. Nce2 Bd6 10. c3`

FEN (line start): `r1bqkb1r/4pppp/p1n2n2/1p1p4/3P4/1BN1B3/PPP2PPP/R2QK1NR b - - 0 8`

Game (full game at ply): http://localhost:5173/analysis?game_id=682885&ply=15

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1bqkb1r/4pppp/p1n2n2/1p1p4/3P4/1BN1B3/PPP2PPP/R2QK1NR%20b%20-%20-%200%208

#### Case 483 — MATE (allowed, depth 10)

Moves (SAN): `15. Qxf7+ Kh8 16. Qxe8+ Kg7 17. Qf7+ Kh6 18. Qf8+ Kh5 19. Bg4+ Kh4 20. g3#`

FEN (line start): `rn2r1k1/ppp2p1p/4B1p1/4p1b1/4P3/5Q1P/PPP2PP1/3R1RK1 w - - 0 15`

Game (full game at ply): http://localhost:5173/analysis?game_id=682887&ply=27

FEN (free-play from line start): http://localhost:5173/analysis?fen=rn2r1k1/ppp2p1p/4B1p1/4p1b1/4P3/5Q1P/PPP2PP1/3R1RK1%20w%20-%20-%200%2015

#### Case 484 — CLEARANCE (missed, depth 4)

Moves (SAN): `14... Rxe6 15. Bxf6 Nc6 16. c3 Rae8 17. Bg5 f6 18. Bh6 Rd8 19. Kh2 f5 20. exf5`

FEN (line start): `rn2r1k1/ppp2p1p/4Bbp1/4p1B1/4P3/5Q1P/PPP2PP1/3R1RK1 b - - 0 14`

Game (full game at ply): http://localhost:5173/analysis?game_id=682887&ply=27

FEN (free-play from line start): http://localhost:5173/analysis?fen=rn2r1k1/ppp2p1p/4Bbp1/4p1B1/4P3/5Q1P/PPP2PP1/3R1RK1%20b%20-%20-%200%2014

#### Case 485 — CLEARANCE (missed, depth 2)

Moves (SAN): `17... Rfe8 18. Rb3 Bf8 19. Bd4 g6 20. Ne3 Qa6 21. g4 Qd6 22. Bb2 Nc5 23. g5`

FEN (line start): `r4rk1/pp1nbppp/5n2/3P1N2/8/4B2P/q4PP1/1R1Q1RK1 b - - 0 17`

Game (full game at ply): http://localhost:5173/analysis?game_id=682895&ply=33

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4rk1/pp1nbppp/5n2/3P1N2/8/4B2P/q4PP1/1R1Q1RK1%20b%20-%20-%200%2017

#### Case 486 — CLEARANCE (allowed, depth 4)

Moves (SAN): `14... Bxd3 15. Bg5 Qc7 16. Rf2 Rce8 17. Qd2 c4 18. Bxc6 Qxc6 19. Bh6 a5 20. a3`

FEN (line start): `2rq1rk1/p4pbp/2np2p1/1ppB1b2/8/2PP1N2/PP1B2PP/R1Q2RK1 b - - 1 14`

Game (full game at ply): http://localhost:5173/analysis?game_id=682917&ply=26

FEN (free-play from line start): http://localhost:5173/analysis?fen=2rq1rk1/p4pbp/2np2p1/1ppB1b2/8/2PP1N2/PP1B2PP/R1Q2RK1%20b%20-%20-%201%2014

#### Case 487 — DISCOVERED_ATTACK (missed, depth 1)

Moves (SAN): `14. Ng5 Ne5 15. Rxf5 gxf5 16. Qh5 h6 17. Rf1 hxg5 18. Rxf5 b4 19. Rxg5 Qf6`

FEN (line start): `2rq1rk1/p4pbp/2np2p1/1ppB1b2/8/2PP1N2/PP1B2PP/R2Q1RK1 w - - 0 14`

Game (full game at ply): http://localhost:5173/analysis?game_id=682917&ply=26

FEN (free-play from line start): http://localhost:5173/analysis?fen=2rq1rk1/p4pbp/2np2p1/1ppB1b2/8/2PP1N2/PP1B2PP/R2Q1RK1%20w%20-%20-%200%2014

#### Case 488 — PIN (allowed, depth 6)

Moves (SAN): `19... Qxd5 20. Bd2 Qc4 21. Qf4+ Kg8 22. Nc3 Nd4 23. Kd1 Bxb4 24. Rc1 Ba3 25. Rc2`

FEN (line start): `3q1b1r/p4kpp/1p2p3/3B4/1P2pBQ1/8/P1n1N1PP/R1K4R b - - 0 19`

Game (full game at ply): http://localhost:5173/analysis?game_id=682923&ply=36

FEN (free-play from line start): http://localhost:5173/analysis?fen=3q1b1r/p4kpp/1p2p3/3B4/1P2pBQ1/8/P1n1N1PP/R1K4R%20b%20-%20-%200%2019

#### Case 489 — DISCOVERED_CHECK (missed, depth 2)

Moves (SAN): `19. Rf1 Bxc4 20. Bg5+ Ke8 21. Bxd8 Nxb4 22. Qxe4 Nd3+ 23. Kd2 Bb4+ 24. Kc2 Bb5`

FEN (line start): `3q1b1r/p4kpp/1p2p3/3b4/1PB1pBQ1/8/P1n1N1PP/R1K4R w - - 0 19`

Game (full game at ply): http://localhost:5173/analysis?game_id=682923&ply=36

FEN (free-play from line start): http://localhost:5173/analysis?fen=3q1b1r/p4kpp/1p2p3/3b4/1PB1pBQ1/8/P1n1N1PP/R1K4R%20w%20-%20-%200%2019

#### Case 490 — HANGING_PIECE (allowed, depth 0)

Moves (SAN): `8... gxh4`

FEN (line start): `rnbqkb1r/ppp1p3/5n1p/4Npp1/3P3B/2N5/PPP3PP/R2QKB1R b - - 1 8`

Game (full game at ply): http://localhost:5173/analysis?game_id=682928&ply=14

FEN (free-play from line start): http://localhost:5173/analysis?fen=rnbqkb1r/ppp1p3/5n1p/4Npp1/3P3B/2N5/PPP3PP/R2QKB1R%20b%20-%20-%201%208

#### Case 491 — SACRIFICE (allowed, depth 10)

Moves (SAN): `12... Qg5 13. Qxe4 Bg7 14. Ng6 Qf5 15. Qxf5 exf5`

FEN (line start): `rnbqkb1r/ppp5/4p2p/4N3/2BPp2p/8/PPP1Q1PP/R3K2R b - - 1 12`

Game (full game at ply): http://localhost:5173/analysis?game_id=682928&ply=22

FEN (free-play from line start): http://localhost:5173/analysis?fen=rnbqkb1r/ppp5/4p2p/4N3/2BPp2p/8/PPP1Q1PP/R3K2R%20b%20-%20-%201%2012

#### Case 492 — CLEARANCE (missed, depth 10)

Moves (SAN): `4... dxc4 5. Nf3 Nd5 6. g3 Nd7 7. Bd2 Nxc3 8. bxc3 b5 9. Bg2 Bb7`

FEN (line start): `rnbqkb1r/pp2pppp/2p2n2/3p4/2PP1B2/2N5/PP2PPPP/R2QKBNR b - - 0 4`

Game (full game at ply): http://localhost:5173/analysis?game_id=682939&ply=7

FEN (free-play from line start): http://localhost:5173/analysis?fen=rnbqkb1r/pp2pppp/2p2n2/3p4/2PP1B2/2N5/PP2PPPP/R2QKBNR%20b%20-%20-%200%204

#### Case 493 — FORK (missed, depth 4)

Moves (SAN): `19... a4 20. Nxa4 Ne4 21. f3 Ng3 22. Qh2 Qf4+ 23. Kb1 Nxh1 24. Qxf4 Rxf4 25. Rxh1`

FEN (line start): `r4rk1/6pp/3qpnp1/p2p2P1/1n1P4/1BN4P/1PP1QP2/2KR3R b - - 0 19`

Game (full game at ply): http://localhost:5173/analysis?game_id=682943&ply=37

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4rk1/6pp/3qpnp1/p2p2P1/1n1P4/1BN4P/1PP1QP2/2KR3R%20b%20-%20-%200%2019

#### Case 494 — CLEARANCE (allowed, depth 10)

Moves (SAN): `22. Qxe6+ Qxe6 23. Bxe6+ Kh8 24. Rd2 a3 25. bxa3 Rxa3 26. Kb2 Ra5 27. Ra1 Rb5`

FEN (line start): `r4rk1/6pp/3qp1p1/6P1/pn1PQ3/1B5P/1PP2P2/2KR3R w - - 0 22`

Game (full game at ply): http://localhost:5173/analysis?game_id=682943&ply=41

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4rk1/6pp/3qp1p1/6P1/pn1PQ3/1B5P/1PP2P2/2KR3R%20w%20-%20-%200%2022

#### Case 495 — HANGING_PIECE (allowed, depth 0)

Moves (SAN): `26. Bxb4 f6 27. g4 Nh4 28. f4 a5 29. Bc5 Nf3+ 30. Kf2 Nd2 31. Ke2 Ne4`

FEN (line start): `r5k1/4Bppp/p7/1p3n2/1bp5/4P2P/P4PP1/2R3K1 w - - 0 26`

Game (full game at ply): http://localhost:5173/analysis?game_id=682960&ply=49

FEN (free-play from line start): http://localhost:5173/analysis?fen=r5k1/4Bppp/p7/1p3n2/1bp5/4P2P/P4PP1/2R3K1%20w%20-%20-%200%2026

#### Case 496 — FORK (missed, depth 0)

Moves (SAN): `25... Ne2+ 26. Kh2 Nxc1 27. Bxb4 Nxa2 28. Bc5 a5 29. e4 c3 30. e5 Nb4 31. Bxb4`

FEN (line start): `r5k1/4Bppp/p7/1p3N2/1bpn4/4P2P/P4PP1/2R3K1 b - - 0 25`

Game (full game at ply): http://localhost:5173/analysis?game_id=682960&ply=49

FEN (free-play from line start): http://localhost:5173/analysis?fen=r5k1/4Bppp/p7/1p3N2/1bpn4/4P2P/P4PP1/2R3K1%20b%20-%20-%200%2025

#### Case 497 — DEFLECTION (allowed, depth 6)

Moves (SAN): `19... Qh4 20. Bc1 Qxh2+ 21. Kf1 Qh1+ 22. Ke2 Qxg2 23. Rf1`

FEN (line start): `r2qk2r/p4ppp/2p5/1p6/PPnP2n1/1QN1P3/1B3PPP/R2R2K1 b - - 0 19`

Game (full game at ply): http://localhost:5173/analysis?game_id=682969&ply=36

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qk2r/p4ppp/2p5/1p6/PPnP2n1/1QN1P3/1B3PPP/R2R2K1%20b%20-%20-%200%2019

#### Case 498 — CLEARANCE (missed, depth 6)

Moves (SAN): `20. Bc1 Qxh2+ 21. Kf1 Qh1+ 22. Ke2 Qxg2 23. Rf1 Nh2 24. Rd1 a6 25. Qb1 Qf3+`

FEN (line start): `r3k2r/p4ppp/2p5/1p6/PPnP2nq/1QN1P3/1B3PPP/R2R2K1 w - - 0 20`

Game (full game at ply): http://localhost:5173/analysis?game_id=682969&ply=38

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3k2r/p4ppp/2p5/1p6/PPnP2nq/1QN1P3/1B3PPP/R2R2K1%20w%20-%20-%200%2020

#### Case 499 — SACRIFICE (missed, depth 2)

Moves (SAN): `23. Rg1 Nxb3 24. d5 Qxb2 25. Nd1 Nxd1 26. Re1+ Kf8 27. Rxd1 Qe2 28. Rb1 cxd5`

FEN (line start): `r3k2r/p4ppp/2p5/1p6/PP1P4/1QN1n2P/1B1n1qP1/R6K w - - 0 23`

Game (full game at ply): http://localhost:5173/analysis?game_id=682969&ply=44

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3k2r/p4ppp/2p5/1p6/PP1P4/1QN1n2P/1B1n1qP1/R6K%20w%20-%20-%200%2023

#### Case 500 — SACRIFICE (allowed, depth 6)

Moves (SAN): `7. Nc3 Nc6 8. Bf4 exd3 9. Nd5 dxc2 10. Qh5+ g6 11. Qe2+ Kf7 12. Nf3 Bd6`

FEN (line start): `rnbqkbnr/pp4pp/8/2p2p2/4p3/3P2P1/PPP2PBP/RNBQK1NR w - - 0 7`

Game (full game at ply): http://localhost:5173/analysis?game_id=682972&ply=11

FEN (free-play from line start): http://localhost:5173/analysis?fen=rnbqkbnr/pp4pp/8/2p2p2/4p3/3P2P1/PPP2PBP/RNBQK1NR%20w%20-%20-%200%207

#### Case 501 — CLEARANCE (missed, depth 10)

Moves (SAN): `6... Nf6 7. Nf3 Nc6`

FEN (line start): `rnbqkbnr/pp4pp/8/2p1pp2/8/3P2P1/PPP2PBP/RNBQK1NR b - - 0 6`

Game (full game at ply): http://localhost:5173/analysis?game_id=682972&ply=11

FEN (free-play from line start): http://localhost:5173/analysis?fen=rnbqkbnr/pp4pp/8/2p1pp2/8/3P2P1/PPP2PBP/RNBQK1NR%20b%20-%20-%200%206

#### Case 502 — FORK (missed, depth 6)

Moves (SAN): `17... Ng4 18. Qd2 Bxe4 19. Nxe4 Nxh6 20. Qxh6 Ne2+ 21. Kh1 Nxc1 22. Qxc1 Kg7 23. h4`

FEN (line start): `r2q2k1/1p2br1p/p4npB/2p2b2/3nN3/2NQ2P1/PPP2PBP/2R2RK1 b - - 0 17`

Game (full game at ply): http://localhost:5173/analysis?game_id=682972&ply=33

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2q2k1/1p2br1p/p4npB/2p2b2/3nN3/2NQ2P1/PPP2PBP/2R2RK1%20b%20-%20-%200%2017

#### Case 503 — DISCOVERED_ATTACK (allowed, depth 5)

Moves (SAN): `19. c3 Bxe4 20. Qxe4 Bf8 21. cxd4 Bxh6 22. Rxc5 Bg7 23. Rd5 Qe8 24. Qd3 Kh8`

FEN (line start): `r5k1/1p1qbr1p/p5pB/2p2b2/3nN3/3Q2P1/PPP2PBP/2R2RK1 w - - 1 19`

Game (full game at ply): http://localhost:5173/analysis?game_id=682972&ply=35

FEN (free-play from line start): http://localhost:5173/analysis?fen=r5k1/1p1qbr1p/p5pB/2p2b2/3nN3/3Q2P1/PPP2PBP/2R2RK1%20w%20-%20-%201%2019

#### Case 504 — CAPTURING_DEFENDER (allowed, depth 2)

Moves (SAN): `11... Nxc3 12. Qxc3 Nxd5 13. Qb3 c6 14. Rad1 f6 15. c4 Nxe3 16. fxe3 Be7 17. e4`

FEN (line start): `r3kb1r/pppq1ppp/3p1n2/3Pp3/4n3/P1NQBN2/1PP2PPP/R4RK1 b - - 1 11`

Game (full game at ply): http://localhost:5173/analysis?game_id=682976&ply=20

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3kb1r/pppq1ppp/3p1n2/3Pp3/4n3/P1NQBN2/1PP2PPP/R4RK1%20b%20-%20-%201%2011

#### Case 505 — FORK (allowed, depth 2)

Moves (UCI — SAN unavailable): `e8g8 f4e5 f7f6 g5e6 f6e5 e6f8 a8f8 f1f8 g8f8 e1f1 f8g8 g1h1`

FEN (line start): `r3k2r/p1pq1pbp/1p4p1/3Pp1N1/1PP1QB2/P7/6PP/4RRK1 b - - 1 21`

Game (full game at ply): http://localhost:5173/analysis?game_id=682976&ply=40

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3k2r/p1pq1pbp/1p4p1/3Pp1N1/1PP1QB2/P7/6PP/4RRK1%20b%20-%20-%201%2021

#### Case 506 — SKEWER (allowed, depth 10)

Moves (SAN): `12. Ne5 Nxe5 13. dxe5 Nd7 14. Bxe7 Qxe7 15. Qg3 h5 16. c3 Bf5 17. Qxg7`

FEN (line start): `r2qk2r/4bppp/p1n1pn2/1p1p2B1/3P2b1/1B1Q1N2/PPP2PPP/RN2R1K1 w - - 1 12`

Game (full game at ply): http://localhost:5173/analysis?game_id=682982&ply=21

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qk2r/4bppp/p1n1pn2/1p1p2B1/3P2b1/1B1Q1N2/PPP2PPP/RN2R1K1%20w%20-%20-%201%2012

#### Case 507 — CAPTURING_DEFENDER (missed, depth 2)

Moves (SAN): `11... Bxf3 12. Qxf3 Nxd4 13. Qd1 Nxb3 14. axb3 Bc5 15. Qf3`

FEN (line start): `r2qk2r/5ppp/p1nbpn2/1p1p2B1/3P2b1/1B1Q1N2/PPP2PPP/RN2R1K1 b - - 0 11`

Game (full game at ply): http://localhost:5173/analysis?game_id=682982&ply=21

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qk2r/5ppp/p1nbpn2/1p1p2B1/3P2b1/1B1Q1N2/PPP2PPP/RN2R1K1%20b%20-%20-%200%2011

#### Case 508 — SKEWER (missed, depth 10)

Moves (SAN): `30... a5 31. a4 bxa4 32. Bxa4 Rc8 33. Ra6 Kf8 34. Bc6 Be8 35. Bxd5 Rxc3 36. Ra8`

FEN (line start): `5rk1/5bpp/p2R4/1p1p4/6P1/1BP2P2/P1P4P/6K1 b - - 0 30`

Game (full game at ply): http://localhost:5173/analysis?game_id=682982&ply=59

FEN (free-play from line start): http://localhost:5173/analysis?fen=5rk1/5bpp/p2R4/1p1p4/6P1/1BP2P2/P1P4P/6K1%20b%20-%20-%200%2030

#### Case 509 — FORK (allowed, depth 0)

Moves (SAN): `18. Nxe6 Bxb2 19. Nxf8 Bxa1 20. Nxh7 Bb2 21. Rc2 Rc8 22. Ng5 Rxc2 23. Qf7+ Kh8`

FEN (line start): `r2q1rk1/pp4pp/4pb2/3p4/3N4/5Q2/PP3PPP/R1R3K1 w - - 0 18`

Game (full game at ply): http://localhost:5173/analysis?game_id=682988&ply=33

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2q1rk1/pp4pp/4pb2/3p4/3N4/5Q2/PP3PPP/R1R3K1%20w%20-%20-%200%2018

#### Case 510 — DISCOVERED_ATTACK (missed, depth 9)

Moves (SAN): `11. b4`

FEN (line start): `rn1qk2r/p2b3p/1p1p2pn/3Ppp2/2P5/2NB1N2/PP3PPP/R2Q1RK1 w - - 0 11`

Game (full game at ply): http://localhost:5173/analysis?game_id=683005&ply=20

FEN (free-play from line start): http://localhost:5173/analysis?fen=rn1qk2r/p2b3p/1p1p2pn/3Ppp2/2P5/2NB1N2/PP3PPP/R2Q1RK1%20w%20-%20-%200%2011

#### Case 511 — FORK (missed, depth 2)

Moves (SAN): `12. Qd2 Na6 13. Ne6 Bxe6 14. dxe6 Kg7 15. Nd5 Re8 16. e7 Qd7 17. Qg5 Ng8`

FEN (line start): `rn1q1rk1/p2b3p/1p1p2pn/3PppN1/2P5/2NB4/PP3PPP/R2Q1RK1 w - - 0 12`

Game (full game at ply): http://localhost:5173/analysis?game_id=683005&ply=22

FEN (free-play from line start): http://localhost:5173/analysis?fen=rn1q1rk1/p2b3p/1p1p2pn/3PppN1/2P5/2NB4/PP3PPP/R2Q1RK1%20w%20-%20-%200%2012

#### Case 512 — SACRIFICE (missed, depth 10)

Moves (SAN): `12... f6 13. Bc1 c5 14. d5 Kh8 15. dxe6 c4 16. Bxc4 Qxd1+ 17. Nxd1 Bb6 18. Be3`

FEN (line start): `rn1q1rk1/pp3ppp/2p1p3/5bB1/3P4/1BN2N2/PPP2bPP/R2Q3K b - - 0 12`

Game (full game at ply): http://localhost:5173/analysis?game_id=683009&ply=23

FEN (free-play from line start): http://localhost:5173/analysis?fen=rn1q1rk1/pp3ppp/2p1p3/5bB1/3P4/1BN2N2/PPP2bPP/R2Q3K%20b%20-%20-%200%2012

#### Case 513 — SACRIFICE (missed, depth 2)

Moves (SAN): `13... Bxd4 14. Nxd4 Bg6 15. Nf5 Qxd2 16. Ne7+ Kh8 17. Nxg6+ hxg6 18. Bxd2 Nd7 19. a4`

FEN (line start): `rn3rk1/pp3ppp/2pqp3/5bB1/3P4/1BN2N2/PPPQ1bPP/R6K b - - 0 13`

Game (full game at ply): http://localhost:5173/analysis?game_id=683009&ply=25

FEN (free-play from line start): http://localhost:5173/analysis?fen=rn3rk1/pp3ppp/2pqp3/5bB1/3P4/1BN2N2/PPPQ1bPP/R6K%20b%20-%20-%200%2013

#### Case 514 — SACRIFICE (allowed, depth 10)

Moves (SAN): `24. Re2 bxa4 25. Bxa4 Rf5 26. Kg2 Rxe5 27. h4 Rxe3 28. Rxe3 Bxe3 29. Qc3 Bc5`

FEN (line start): `5rk1/6pp/pq2p3/1pbpP3/P7/1B2P1PP/1P1Q4/4R1K1 w - - 1 24`

Game (full game at ply): http://localhost:5173/analysis?game_id=683024&ply=45

FEN (free-play from line start): http://localhost:5173/analysis?fen=5rk1/6pp/pq2p3/1pbpP3/P7/1B2P1PP/1P1Q4/4R1K1%20w%20-%20-%201%2024

#### Case 515 — FORK (missed, depth 2)

Moves (SAN): `23... bxa4 24. Bc2 Bxe3+ 25. Rxe3 Rxc2 26. Qxc2 Qxe3+ 27. Kg2 Qxe5 28. Qc8+ Kf7 29. Qd7+`

FEN (line start): `2r3k1/6pp/pq2p3/1pbpP3/P7/1B2P1PP/1P1Q4/4R1K1 b - - 0 23`

Game (full game at ply): http://localhost:5173/analysis?game_id=683024&ply=45

FEN (free-play from line start): http://localhost:5173/analysis?fen=2r3k1/6pp/pq2p3/1pbpP3/P7/1B2P1PP/1P1Q4/4R1K1%20b%20-%20-%200%2023

#### Case 516 — DISCOVERED_ATTACK (allowed, depth 1)

Moves (SAN): `16... fxe5 17. Ne4 Rxf3 18. gxf3 exd4 19. Rfe1 Rf8 20. Bf1 Ne5 21. Bg2 d3 22. Qg5`

FEN (line start): `r4rk1/p2nq2p/b1pNppp1/1p1nP3/3P4/3B1N2/PP1Q1PPP/R4RK1 b - - 1 16`

Game (full game at ply): http://localhost:5173/analysis?game_id=683025&ply=30

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4rk1/p2nq2p/b1pNppp1/1p1nP3/3P4/3B1N2/PP1Q1PPP/R4RK1%20b%20-%20-%201%2016

#### Case 517 — CLEARANCE (missed, depth 8)

Moves (SAN): `9... b5 10. a4 b4 11. Na2 a5 12. c3 Qe7 13. Nc1 Rfb8 14. Nd3 Bb7 15. Ne5`

FEN (line start): `r2q1rk1/ppp2ppp/2bbpn2/3p4/3P1P2/2N1P1N1/PPPB2PP/R2QK2R b - - 0 9`

Game (full game at ply): http://localhost:5173/analysis?game_id=683030&ply=17

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2q1rk1/ppp2ppp/2bbpn2/3p4/3P1P2/2N1P1N1/PPPB2PP/R2QK2R%20b%20-%20-%200%209

#### Case 518 — SACRIFICE (missed, depth 10)

Moves (SAN): `24... Rfc8 25. Kf2 Qa2+ 26. Rc2 Qxc2+ 27. Nxc2 Rxc3 28. Qe2 e5 29. fxe5 Rbc8 30. Nd4`

FEN (line start): `1r3rk1/4bppp/4p3/3b2PQ/pPqNpP2/P1B1P3/7P/2R1K2R b - - 0 24`

Game (full game at ply): http://localhost:5173/analysis?game_id=683030&ply=47

FEN (free-play from line start): http://localhost:5173/analysis?fen=1r3rk1/4bppp/4p3/3b2PQ/pPqNpP2/P1B1P3/7P/2R1K2R%20b%20-%20-%200%2024

#### Case 519 — ATTRACTION (missed, depth 4)

Moves (SAN): `5... e5 6. dxe5 Qa5+ 7. Qd2 Qxd2+ 8. Kxd2 Ne4+ 9. Ke1 g5 10. f3 gxf4 11. fxe4`

FEN (line start): `r1bqkb1r/pp2pppp/2n2n2/1Npp4/3P1B2/4P3/PPP2PPP/R2QKBNR b - - 0 5`

Game (full game at ply): http://localhost:5173/analysis?game_id=683033&ply=9

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1bqkb1r/pp2pppp/2n2n2/1Npp4/3P1B2/4P3/PPP2PPP/R2QKBNR%20b%20-%20-%200%205

#### Case 520 — PIN (allowed, depth 0)

Moves (SAN): `21. exf6 Bxf6 22. Bf4 Rb4 23. Qe2 Qb6 24. Nxf6+ gxf6 25. g3 Rg7 26. Bc1 Re4`

FEN (line start): `1r1q2k1/4brpp/p3pp1B/2ppPn1N/6Q1/1P6/P4PPP/3R1RK1 w - - 1 21`

Game (full game at ply): http://localhost:5173/analysis?game_id=683056&ply=39

FEN (free-play from line start): http://localhost:5173/analysis?fen=1r1q2k1/4brpp/p3pp1B/2ppPn1N/6Q1/1P6/P4PPP/3R1RK1%20w%20-%20-%201%2021

#### Case 521 — CLEARANCE (allowed, depth 10)

Moves (SAN): `24. Qg5 h6 25. Qxf6 gxf6 26. Bd2 Rb6 27. Rc1 Rc6 28. Rc3 h5 29. Rfc1 Rfc7`

FEN (line start): `6k1/5rpp/p3pq2/2pp1n2/1r3BQ1/1P6/P4PPP/3R1RK1 w - - 0 24`

Game (full game at ply): http://localhost:5173/analysis?game_id=683056&ply=45

FEN (free-play from line start): http://localhost:5173/analysis?fen=6k1/5rpp/p3pq2/2pp1n2/1r3BQ1/1P6/P4PPP/3R1RK1%20w%20-%20-%200%2024

#### Case 522 — FORK (allowed, depth 2)

Moves (SAN): `17. Nxe4 dxe4 18. Nxf7 Rxf7 19. Rxf7 Nf5 20. Bxg4 hxg4 21. Qxg4 Nh6 22. Qxg7 Nxf7`

FEN (line start): `2k2r1r/2p1npp1/p2qp3/P2pN2p/3Pn1b1/2P1P1P1/3NB1PP/R2Q1RK1 w - - 1 17`

Game (full game at ply): http://localhost:5173/analysis?game_id=683084&ply=31

FEN (free-play from line start): http://localhost:5173/analysis?fen=2k2r1r/2p1npp1/p2qp3/P2pN2p/3Pn1b1/2P1P1P1/3NB1PP/R2Q1RK1%20w%20-%20-%201%2017

#### Case 523 — FORK (allowed, depth 6)

Moves (SAN): `20. Rab1 Nb4 21. Qxb4 Qxb4 22. Rxb4 f6 23. Ng6 Rd8 24. Nxh8 Rxh8 25. Rfb1 Kd7`

FEN (line start): `2k2r1r/2p2pp1/p2qp3/P2nN3/3Pp1p1/1QP1P1P1/6PP/R4RK1 w - - 1 20`

Game (full game at ply): http://localhost:5173/analysis?game_id=683084&ply=37

FEN (free-play from line start): http://localhost:5173/analysis?fen=2k2r1r/2p2pp1/p2qp3/P2nN3/3Pp1p1/1QP1P1P1/6PP/R4RK1%20w%20-%20-%201%2020

#### Case 524 — SACRIFICE (missed, depth 8)

Moves (SAN): `19... f6 20. Rab1 Kd8 21. Qb8+ Nc8 22. Ng6 Rh5 23. Nxf8 Qxf8 24. Qa8 Kd7 25. Qxe4`

FEN (line start): `2k2r1r/2p1npp1/p2qp3/P3N3/3Pp1p1/1QP1P1P1/6PP/R4RK1 b - - 0 19`

Game (full game at ply): http://localhost:5173/analysis?game_id=683084&ply=37

FEN (free-play from line start): http://localhost:5173/analysis?fen=2k2r1r/2p1npp1/p2qp3/P3N3/3Pp1p1/1QP1P1P1/6PP/R4RK1%20b%20-%20-%200%2019

#### Case 525 — SACRIFICE (missed, depth 6)

Moves (SAN): `20... Nb4 21. Nxf7 Qe7 22. Qxb4 Qxb4 23. cxb4 Rhg8 24. Ng5 Rh8 25. Rxf8+ Rxf8 26. Nxe6`

FEN (line start): `2k2r1r/2p2pp1/p2qp3/P2nN3/3Pp1p1/1QP1P1P1/6PP/1R3RK1 b - - 0 20`

Game (full game at ply): http://localhost:5173/analysis?game_id=683084&ply=39

FEN (free-play from line start): http://localhost:5173/analysis?fen=2k2r1r/2p2pp1/p2qp3/P2nN3/3Pp1p1/1QP1P1P1/6PP/1R3RK1%20b%20-%20-%200%2020

#### Case 526 — PIN (allowed, depth 10)

Moves (SAN): `13... Nxf4 14. gxf4 Qxf4 15. Bxc6+ bxc6 16. Re1 Qh2+ 17. Kf1`

FEN (line start): `rb2k2r/pp3ppp/2nqp3/1B1p3n/3P1B2/2N2PPP/PP3P2/2RQ1RK1 b - - 1 13`

Game (full game at ply): http://localhost:5173/analysis?game_id=683123&ply=24

FEN (free-play from line start): http://localhost:5173/analysis?fen=rb2k2r/pp3ppp/2nqp3/1B1p3n/3P1B2/2N2PPP/PP3P2/2RQ1RK1%20b%20-%20-%201%2013

#### Case 527 — CAPTURING_DEFENDER (allowed, depth 4)

Moves (SAN): `21... Qxf2+ 22. Qxf2 Bxf2 23. Kxf2 Nxd4 24. Bd3 g6 25. Rh4 Nc6 26. Rgh1 h5 27. Rg1`

FEN (line start): `r4rk1/pp3ppp/2n1p3/1B1p4/3P4/2N1QPb1/PP2KPq1/6RR b - - 1 21`

Game (full game at ply): http://localhost:5173/analysis?game_id=683123&ply=40

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4rk1/pp3ppp/2n1p3/1B1p4/3P4/2N1QPb1/PP2KPq1/6RR%20b%20-%20-%201%2021

#### Case 528 — CLEARANCE (allowed, depth 8)

Moves (SAN): `27... Nf5 28. Bxf5 exf5 29. Nxd5 Rc2+ 30. Kg3 f6 31. Rb4 Rf7 32. Ne3 Rc5 33. Rd1`

FEN (line start): `2r2rk1/pp3pp1/4p3/3p4/3n3R/2NB1P2/PP3K2/6R1 b - - 1 27`

Game (full game at ply): http://localhost:5173/analysis?game_id=683123&ply=52

FEN (free-play from line start): http://localhost:5173/analysis?fen=2r2rk1/pp3pp1/4p3/3p4/3n3R/2NB1P2/PP3K2/6R1%20b%20-%20-%201%2027

#### Case 529 — DISCOVERED_CHECK (missed, depth 6)

Moves (SAN): `27. Bh7+ Kh8 28. Rg4 Nc6 29. Nxd5 exd5 30. Bf5+ Kg8 31. Rgh4 g5 32. Rh8+ Kg7`

FEN (line start): `2r2rk1/pp3pp1/4p3/3p4/3n4/2NB1P2/PP3K2/6RR w - - 0 27`

Game (full game at ply): http://localhost:5173/analysis?game_id=683123&ply=52

FEN (free-play from line start): http://localhost:5173/analysis?fen=2r2rk1/pp3pp1/4p3/3p4/3n4/2NB1P2/PP3K2/6RR%20w%20-%20-%200%2027

#### Case 530 — SKEWER (allowed, depth 2)

Moves (SAN): `48... a1=Q+ 49. Kd5 Qxf6 50. f8=Q Qxf8 51. Kd4 Qd6+ 52. Ke3 Qf4+ 53. Kd3 Rd2+ 54. Kc3`

FEN (line start): `8/1p3P2/5R2/1k2K3/8/8/p4r2/8 b - - 1 48`

Game (full game at ply): http://localhost:5173/analysis?game_id=683123&ply=94

FEN (free-play from line start): http://localhost:5173/analysis?fen=8/1p3P2/5R2/1k2K3/8/8/p4r2/8%20b%20-%20-%201%2048

#### Case 531 — CLEARANCE (missed, depth 2)

Moves (SAN): `48. Kd5 a1=Q 49. Re5 Qa2+ 50. Kd6+ Kb4 51. Re4+ Ka5 52. Rg4 Qxf7 53. Rg1 Rd2+`

FEN (line start): `8/1p3P2/4R3/1k2K3/8/8/p4r2/8 w - - 0 48`

Game (full game at ply): http://localhost:5173/analysis?game_id=683123&ply=94

FEN (free-play from line start): http://localhost:5173/analysis?fen=8/1p3P2/4R3/1k2K3/8/8/p4r2/8%20w%20-%20-%200%2048

#### Case 532 — PROMOTION (missed, depth 4)

Moves (SAN): `55. Kd7 Qf5+ 56. Ke7 Kc5 57. f8=Q Qxf8+ 58. Kxf8 Kd4 59. Ke7 b5 60. Kd6 b4`

FEN (line start): `8/1p3P2/4K3/1k6/4q3/8/8/8 w - - 0 55`

Game (full game at ply): http://localhost:5173/analysis?game_id=683123&ply=108

FEN (free-play from line start): http://localhost:5173/analysis?fen=8/1p3P2/4K3/1k6/4q3/8/8/8%20w%20-%20-%200%2055

#### Case 533 — PROMOTION (missed, depth 0)

Moves (SAN): `56. f8=Q+ Kb5 57. Qa8 Qc6+ 58. Kf7 b6 59. Qa1 Qd6 60. Ke8 Qe6+ 61. Kd8 Qc6`

FEN (line start): `8/1p3P2/5K2/2k5/4q3/8/8/8 w - - 0 56`

Game (full game at ply): http://localhost:5173/analysis?game_id=683123&ply=110

FEN (free-play from line start): http://localhost:5173/analysis?fen=8/1p3P2/5K2/2k5/4q3/8/8/8%20w%20-%20-%200%2056

#### Case 534 — PROMOTION (missed, depth 8)

Moves (SAN): `57. Kg8 Qg5+ 58. Kh8 Qd8+ 59. Kg7 Qe7 60. Kg8 Kd5 61. f8=Q Qxf8+ 62. Kxf8 Ke6`

FEN (line start): `8/1p3PK1/8/2k1q3/8/8/8/8 w - - 0 57`

Game (full game at ply): http://localhost:5173/analysis?game_id=683123&ply=112

FEN (free-play from line start): http://localhost:5173/analysis?fen=8/1p3PK1/8/2k1q3/8/8/8/8%20w%20-%20-%200%2057

#### Case 535 — PIN (allowed, depth 0)

Moves (SAN): `13. Nxd5 Qc5 14. c4 Ne7 15. b4 Nxf3+ 16. Qxf3 Qc6 17. Rac1 Ng6 18. b5 axb5`

FEN (line start): `r3k1nr/1p3ppp/pq1bp3/3p2B1/3n4/2N2B1P/PPP2PP1/R2QR1K1 w - - 0 13`

Game (full game at ply): http://localhost:5173/analysis?game_id=683131&ply=23

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3k1nr/1p3ppp/pq1bp3/3p2B1/3n4/2N2B1P/PPP2PP1/R2QR1K1%20w%20-%20-%200%2013

#### Case 536 — PIN (allowed, depth 6)

Moves (SAN): `16. Bxg7 Ne7 17. Bxh8 Rc8 18. Nxd5 exd5 19. Qxd5 Bc5 20. Bd4 Bb4 21. Qxb7 Bxe1`

FEN (line start): `r3k1nr/1p3ppp/p2bp3/3p4/3B4/2N2Q1P/P1q2PP1/R3R1K1 w - - 0 16`

Game (full game at ply): http://localhost:5173/analysis?game_id=683131&ply=29

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3k1nr/1p3ppp/p2bp3/3p4/3B4/2N2Q1P/P1q2PP1/R3R1K1%20w%20-%20-%200%2016

#### Case 537 — FORK (allowed, depth 2)

Moves (SAN): `34... Bd4 35. Qe6 Bxf2+ 36. Kg2 Qf3+ 37. Kh3 Bxe1 38. Qxe1 Rc7 39. Qb1 Qe2 40. a4`

FEN (line start): `8/5rbk/Q5pp/1p6/8/Pq4P1/5P1P/4R1K1 b - - 1 34`

Game (full game at ply): http://localhost:5173/analysis?game_id=683141&ply=66

FEN (free-play from line start): http://localhost:5173/analysis?fen=8/5rbk/Q5pp/1p6/8/Pq4P1/5P1P/4R1K1%20b%20-%20-%201%2034

#### Case 538 — ATTRACTION (allowed, depth 4)

Moves (SAN): `35... Qd2 36. Qb6 Bd4 37. Rf6 Qxf2+ 38. Rxf2 Bxb6 39. Kf1 Bxf2 40. Ke2 Bc5 41. Kd3`

FEN (line start): `8/5rbk/Q3R1pp/1p6/8/P1q3P1/5P1P/6K1 b - - 1 35`

Game (full game at ply): http://localhost:5173/analysis?game_id=683141&ply=68

FEN (free-play from line start): http://localhost:5173/analysis?fen=8/5rbk/Q3R1pp/1p6/8/P1q3P1/5P1P/6K1%20b%20-%20-%201%2035

#### Case 539 — CLEARANCE (missed, depth 4)

Moves (SAN): `39. Qc6 g5 40. Qe4 Qc5 41. Rc6 Qd4 42. Qf5 Qb2 43. h3 Qb8 44. Qe4`

FEN (line start): `4Q3/5rk1/4Rbpp/8/8/q5P1/5PKP/8 w - - 0 39`

Game (full game at ply): http://localhost:5173/analysis?game_id=683141&ply=76

FEN (free-play from line start): http://localhost:5173/analysis?fen=4Q3/5rk1/4Rbpp/8/8/q5P1/5PKP/8%20w%20-%20-%200%2039

#### Case 540 — HANGING_PIECE (allowed, depth 0)

Moves (SAN): `40... Rxf6 41. Qe2 Qc3 42. Kg1 Rf7 43. Kg2 Kh7 44. Kg1 Qd4 45. Qc2 Re7 46. Qc1`

FEN (line start): `4Q3/5rk1/5Rp1/7p/7P/q5P1/5PK1/8 b - - 0 40`

Game (full game at ply): http://localhost:5173/analysis?game_id=683141&ply=78

FEN (free-play from line start): http://localhost:5173/analysis?fen=4Q3/5rk1/5Rp1/7p/7P/q5P1/5PK1/8%20b%20-%20-%200%2040

#### Case 541 — PIN (allowed, depth 10)

Moves (SAN): `20. Qxb5 Rc8 21. Qe2 f6 22. Bf4 Qa6 23. Qg4 Rxc2 24. h4 Nc3 25. Bh6 g6`

FEN (line start): `q3r1k1/1p3ppp/4p3/1p1pB3/3Pn3/1Q6/2P2PPP/5RK1 w - - 1 20`

Game (full game at ply): http://localhost:5173/analysis?game_id=683146&ply=37

FEN (free-play from line start): http://localhost:5173/analysis?fen=q3r1k1/1p3ppp/4p3/1p1pB3/3Pn3/1Q6/2P2PPP/5RK1%20w%20-%20-%201%2020

#### Case 542 — DISCOVERED_CHECK (missed, depth 10)

Moves (SAN): `19... Qc8 20. Re1 Qc4 21. Re3 b4 22. h4 f6 23. Bd6 Ne2+ 24. Kf1 Nxd4+ 25. Qxc4`

FEN (line start): `q3r1k1/1p3ppp/4p3/1p1pB3/3P4/1Qn5/2P2PPP/5RK1 b - - 0 19`

Game (full game at ply): http://localhost:5173/analysis?game_id=683146&ply=37

FEN (free-play from line start): http://localhost:5173/analysis?fen=q3r1k1/1p3ppp/4p3/1p1pB3/3P4/1Qn5/2P2PPP/5RK1%20b%20-%20-%200%2019

#### Case 543 — HANGING_PIECE (allowed, depth 0)

Moves (SAN): `32. Qxc7 gxh5 33. gxh5 Kf6 34. Qg3 Ke7 35. Kh2 Kd7 36. c3 Qxc3 37. Kg2 Qd4`

FEN (line start): `1Q6/2r2pkp/4p1p1/3p3P/6P1/4qP2/2P2RK1/8 w - - 1 32`

Game (full game at ply): http://localhost:5173/analysis?game_id=683146&ply=61

FEN (free-play from line start): http://localhost:5173/analysis?fen=1Q6/2r2pkp/4p1p1/3p3P/6P1/4qP2/2P2RK1/8%20w%20-%20-%201%2032

#### Case 544 — PIN (missed, depth 0)

Moves (SAN): `9... dxc4`

FEN (line start): `r2qk2r/pQp2ppp/2n1pn2/b2p4/2PPbB2/P3PN2/1P1N1PPP/R3KB1R b - - 0 9`

Game (full game at ply): http://localhost:5173/analysis?game_id=683154&ply=17

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qk2r/pQp2ppp/2n1pn2/b2p4/2PPbB2/P3PN2/1P1N1PPP/R3KB1R%20b%20-%20-%200%209

#### Case 545 — PIN (missed, depth 2)

Moves (SAN): `10... c6 11. Qb7 dxc4 12. Bxc4 Bxf3 13. gxf3 Bxd2+ 14. Kxd2`

FEN (line start): `r2qk2r/p1p1nppp/4pn2/bQ1p4/2PPbB2/P3PN2/1P1N1PPP/R3KB1R b - - 0 10`

Game (full game at ply): http://localhost:5173/analysis?game_id=683154&ply=19

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qk2r/p1p1nppp/4pn2/bQ1p4/2PPbB2/P3PN2/1P1N1PPP/R3KB1R%20b%20-%20-%200%2010

#### Case 546 — SACRIFICE (missed, depth 4)

Moves (SAN): `33... Kh7 34. Rd8 Rd4 35. Rxd4 Qg6 36. Rdd1 a5 37. bxa5`

FEN (line start): `7k/p1P3p1/5n1p/5q2/1P5r/P4P2/4Q1PP/3RR1K1 b - - 0 33`

Game (full game at ply): http://localhost:5173/analysis?game_id=683154&ply=65

FEN (free-play from line start): http://localhost:5173/analysis?fen=7k/p1P3p1/5n1p/5q2/1P5r/P4P2/4Q1PP/3RR1K1%20b%20-%20-%200%2033

#### Case 547 — PIN (allowed, depth 2)

Moves (SAN): `12... dxe6 13. Qe2 Bh3 14. Ne1 Bf5 15. Nc2 Kf8 16. Rfd1 Qc8 17. Ne3 Bg6 18. h4`

FEN (line start): `rn1qk1r1/2ppbp1p/p3Pp2/5b2/2B5/2N2N2/PP3PPP/R2Q1RK1 b - - 0 12`

Game (full game at ply): http://localhost:5173/analysis?game_id=683171&ply=22

FEN (free-play from line start): http://localhost:5173/analysis?fen=rn1qk1r1/2ppbp1p/p3Pp2/5b2/2B5/2N2N2/PP3PPP/R2Q1RK1%20b%20-%20-%200%2012

#### Case 548 — CLEARANCE (missed, depth 2)

Moves (SAN): `12. Re1 Bh3 13. Bf1 Kf8 14. Nd4 Bg4 15. Qd3 c5 16. Nde2 f5 17. Rad1 Bf6`

FEN (line start): `rn1qk1r1/2ppbp1p/p3pp2/3P1b2/2B5/2N2N2/PP3PPP/R2Q1RK1 w - - 0 12`

Game (full game at ply): http://localhost:5173/analysis?game_id=683171&ply=22

FEN (free-play from line start): http://localhost:5173/analysis?fen=rn1qk1r1/2ppbp1p/p3pp2/3P1b2/2B5/2N2N2/PP3PPP/R2Q1RK1%20w%20-%20-%200%2012

#### Case 549 — CLEARANCE (allowed, depth 4)

Moves (SAN): `23... Qd6 24. Qe4 Kg7 25. Nd5 Rd8 26. Qd4 Rxa2 27. Nh4 Kh8 28. Nf5 Qc6 29. Nfe7`

FEN (line start): `5kr1/2p1q2p/p1Q2p2/8/8/2N2NP1/Pr5P/4R1K1 b - - 1 23`

Game (full game at ply): http://localhost:5173/analysis?game_id=683171&ply=44

FEN (free-play from line start): http://localhost:5173/analysis?fen=5kr1/2p1q2p/p1Q2p2/8/8/2N2NP1/Pr5P/4R1K1%20b%20-%20-%201%2023

#### Case 550 — PIN (missed, depth 4)

Moves (SAN): `23. Rd7 Rb6 24. Qa8+ Qe8 25. Rd8 Ke7 26. Rxe8+ Rxe8 27. Qd5 Rd6 28. Qe4+ Kd8`

FEN (line start): `5kr1/2p1q2p/p1Q2p2/8/8/2N2NP1/Pr5P/3R2K1 w - - 0 23`

Game (full game at ply): http://localhost:5173/analysis?game_id=683171&ply=44

FEN (free-play from line start): http://localhost:5173/analysis?fen=5kr1/2p1q2p/p1Q2p2/8/8/2N2NP1/Pr5P/3R2K1%20w%20-%20-%200%2023

#### Case 551 — FORK (missed, depth 2)

Moves (SAN): `26. Nxc7 Kh6 27. Qc1+ Kh5 28. Rd1 Qxd1+ 29. Qxd1 a5 30. Ne1+ Rg4 31. Qf3 Rxa2`

FEN (line start): `3q4/2p3kp/p4pr1/2QN4/8/5NP1/Pr5P/4R1K1 w - - 0 26`

Game (full game at ply): http://localhost:5173/analysis?game_id=683171&ply=50

FEN (free-play from line start): http://localhost:5173/analysis?fen=3q4/2p3kp/p4pr1/2QN4/8/5NP1/Pr5P/4R1K1%20w%20-%20-%200%2026

#### Case 552 — MATE (allowed, depth 10)

Moves (SAN): `24... Ra3+ 25. Kb1 Qa5 26. c3 Bxc3 27. b3 Raxb3+ 28. Kc1 Qa1+ 29. Kc2 Qb2#`

FEN (line start): `2b3k1/1r5p/p3pBpP/6q1/1b1Pp1P1/4r3/1PP1N3/2KR2QR b - - 1 24`

Game (full game at ply): http://localhost:5173/analysis?game_id=683202&ply=46

FEN (free-play from line start): http://localhost:5173/analysis?fen=2b3k1/1r5p/p3pBpP/6q1/1b1Pp1P1/4r3/1PP1N3/2KR2QR%20b%20-%20-%201%2024

#### Case 553 — SACRIFICE (missed, depth 2)

Moves (SAN): `24. Kb1 Rxe2 25. Rh3 e3 26. Rf3 Rf2 27. Rxf2 exf2 28. Qxf2 Rf7 29. Qe2 Qd5`

FEN (line start): `2b3k1/1r4Bp/p3p1pP/6q1/1b1Pp1P1/4r3/1PP1N3/2KR2QR w - - 0 24`

Game (full game at ply): http://localhost:5173/analysis?game_id=683202&ply=46

FEN (free-play from line start): http://localhost:5173/analysis?fen=2b3k1/1r4Bp/p3p1pP/6q1/1b1Pp1P1/4r3/1PP1N3/2KR2QR%20w%20-%20-%200%2024

#### Case 554 — PIN (missed, depth 2)

Moves (SAN): `14... Bxd2+ 15. Kxd2 Ne5 16. Qf6 Nxf3+ 17. gxf3 Qa5+ 18. Ke3 e5 19. Qxe5 Qc3+ 20. Bd3`

FEN (line start): `2kr4/pp1n1Q2/1qp1p1p1/5b2/1b1P4/1P3N2/P1PB1PPP/R3KB1R b - - 0 14`

Game (full game at ply): http://localhost:5173/analysis?game_id=683236&ply=27

FEN (free-play from line start): http://localhost:5173/analysis?fen=2kr4/pp1n1Q2/1qp1p1p1/5b2/1b1P4/1P3N2/P1PB1PPP/R3KB1R%20b%20-%20-%200%2014

#### Case 555 — CLEARANCE (allowed, depth 8)

Moves (SAN): `5... h6 6. Bh4 Nxe5 7. e4 Bd6 8. Rb1 Ng6 9. Bd3 Bf4 10. Bg3 Bxg3 11. hxg3`

FEN (line start): `r1b1kbnr/pppp1ppp/2n5/4P1B1/1q6/5N2/PPPNPPPP/R2QKB1R b - - 1 5`

Game (full game at ply): http://localhost:5173/analysis?game_id=683244&ply=8

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1b1kbnr/pppp1ppp/2n5/4P1B1/1q6/5N2/PPPNPPPP/R2QKB1R%20b%20-%20-%201%205

#### Case 556 — CAPTURING_DEFENDER (allowed, depth 6)

Moves (SAN): `12. Ne5 Qb6 13. Qb3 Bd6 14. Qxb6 axb6 15. Nxc6`

FEN (line start): `r2qk2r/p3bppp/2p2n2/3p3b/3P4/3Q1N1P/PP3PP1/RNB2RK1 w - - 0 12`

Game (full game at ply): http://localhost:5173/analysis?game_id=683248&ply=21

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qk2r/p3bppp/2p2n2/3p3b/3P4/3Q1N1P/PP3PP1/RNB2RK1%20w%20-%20-%200%2012

#### Case 557 — SACRIFICE (missed, depth 2)

Moves (SAN): `22... Rxf5 23. gxf5 a5 24. Kb1 a4 25. Rhg1 Re8 26. Rd5 Rb8 27. Rd4 Kf6 28. h3`

FEN (line start): `2r5/p3kp2/3p3p/1p1r1N2/2n3P1/P1P1P3/1P3P1P/2KR3R b - - 0 22`

Game (full game at ply): http://localhost:5173/analysis?game_id=683256&ply=43

FEN (free-play from line start): http://localhost:5173/analysis?fen=2r5/p3kp2/3p3p/1p1r1N2/2n3P1/P1P1P3/1P3P1P/2KR3R%20b%20-%20-%200%2022

#### Case 558 — HANGING_PIECE (allowed, depth 0)

Moves (SAN): `12... axb5 13. Nb6+ Kc7 14. Rxc2 Ne7 15. a4 bxa4 16. Nxa4 Ra8 17. Nc3 Nd5 18. Nxd5+`

FEN (line start): `N5nr/1p1k1ppp/p1n1p3/1B6/1b1P4/4B3/PPb1KPPP/2R4R b - - 1 12`

Game (full game at ply): http://localhost:5173/analysis?game_id=683308&ply=22

FEN (free-play from line start): http://localhost:5173/analysis?fen=N5nr/1p1k1ppp/p1n1p3/1B6/1b1P4/4B3/PPb1KPPP/2R4R%20b%20-%20-%201%2012

#### Case 559 — PIN (allowed, depth 0)

Moves (SAN): `45. Nxe6+ Kh8 46. Nxd8 Rxg2+ 47. Kh3 Rg3+ 48. Kh2 Rg2+`

FEN (line start): `3r4/1R3pk1/4pNpp/3pPn2/4bN1P/8/5rPK/8 w - - 1 45`

Game (full game at ply): http://localhost:5173/analysis?game_id=683313&ply=87

FEN (free-play from line start): http://localhost:5173/analysis?fen=3r4/1R3pk1/4pNpp/3pPn2/4bN1P/8/5rPK/8%20w%20-%20-%201%2045

#### Case 560 — MATE (allowed, depth 6)

Moves (SAN): `48. Nxf7+ Kg7 49. Nd6+ Ne7 50. Rxe7+ Kf8 51. Rf7#`

FEN (line start): `3N3k/1R3p2/5Npp/3pPn2/4b2P/7K/8/6r1 w - - 1 48`

Game (full game at ply): http://localhost:5173/analysis?game_id=683313&ply=93

FEN (free-play from line start): http://localhost:5173/analysis?fen=3N3k/1R3p2/5Npp/3pPn2/4b2P/7K/8/6r1%20w%20-%20-%201%2048

#### Case 561 — HANGING_PIECE (allowed, depth 0)

Moves (SAN): `51. Nxe4`

FEN (line start): `3N3k/5p2/5Npp/4Pn2/3pb2P/8/7K/8 w - - 0 51`

Game (full game at ply): http://localhost:5173/analysis?game_id=683313&ply=99

FEN (free-play from line start): http://localhost:5173/analysis?fen=3N3k/5p2/5Npp/4Pn2/3pb2P/8/7K/8%20w%20-%20-%200%2051

#### Case 562 — PIN (allowed, depth 0)

Moves (SAN): `12. Bxe7`

FEN (line start): `r3k2r/ppq1npp1/2n1p2p/1B1pPbB1/Q2P4/2P2N2/P4PPP/R3K2R w - - 0 12`

Game (full game at ply): http://localhost:5173/analysis?game_id=683314&ply=21

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3k2r/ppq1npp1/2n1p2p/1B1pPbB1/Q2P4/2P2N2/P4PPP/R3K2R%20w%20-%20-%200%2012

#### Case 563 — FORK (missed, depth 6)

Moves (SAN): `23... Rac8 24. Re5 Nf5 25. Rxd5 Rxc2 26. Rxc2 Nxe3 27. Rdc5 Rf1+ 28. Kh2 Nxc2 29. Rxc2`

FEN (line start): `r4rk1/6pp/p3R2n/1p1p4/4p3/4P2P/P1B3P1/2R3K1 b - - 0 23`

Game (full game at ply): http://localhost:5173/analysis?game_id=683320&ply=45

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4rk1/6pp/p3R2n/1p1p4/4p3/4P2P/P1B3P1/2R3K1%20b%20-%20-%200%2023

#### Case 564 — DISCOVERED_ATTACK (missed, depth 5)

Moves (SAN): `24... Kf7 25. Re5 Ne7 26. Rf1+ Ke8 27. Bb3 Rxf1+ 28. Kxf1 Kf8 29. Re6 a5 30. Rd6`

FEN (line start): `r4rk1/6pp/p3R3/1p1p1n2/4p3/4P2P/P1B3P1/4R1K1 b - - 0 24`

Game (full game at ply): http://localhost:5173/analysis?game_id=683320&ply=47

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4rk1/6pp/p3R3/1p1p1n2/4p3/4P2P/P1B3P1/4R1K1%20b%20-%20-%200%2024

#### Case 565 — INTERMEZZO (allowed, depth 2)

Moves (SAN): `17... Qxb2+ 18. Kd2 cxd5 19. Qc3 c5 20. dxc5 Rfc8 21. a4 Qb4 22. Qxb4 Rxb4 23. Rc3`

FEN (line start): `1r3rk1/p1p2pp1/2p1p2p/3N4/1q1P4/6QR/PPP3PP/2KR4 b - - 0 17`

Game (full game at ply): http://localhost:5173/analysis?game_id=683321&ply=32

FEN (free-play from line start): http://localhost:5173/analysis?fen=1r3rk1/p1p2pp1/2p1p2p/3N4/1q1P4/6QR/PPP3PP/2KR4%20b%20-%20-%200%2017

#### Case 566 — CLEARANCE (missed, depth 2)

Moves (SAN): `13. c5 e6 14. Bc4 Kh8 15. c6 Nxc6 16. dxc6 Bxc6 17. Bd3 e5 18. Rc1 Bb7`

FEN (line start): `rn1q1rk1/pbppp1bp/1p4p1/3P4/2P1N3/5N2/P3BPPP/1R1Q1RK1 w - - 0 13`

Game (full game at ply): http://localhost:5173/analysis?game_id=683333&ply=24

FEN (free-play from line start): http://localhost:5173/analysis?fen=rn1q1rk1/pbppp1bp/1p4p1/3P4/2P1N3/5N2/P3BPPP/1R1Q1RK1%20w%20-%20-%200%2013

#### Case 567 — CLEARANCE (allowed, depth 4)

Moves (SAN): `14... Nxc6 15. Qd3 Qc7 16. Rfd1 Rad8 17. c5 e6 18. cxb6 axb6 19. Qe3 h6 20. Qxb6`

FEN (line start): `rn1q1rk1/pb1pp1bp/1pP3p1/6N1/2P5/5N2/P3BPPP/1R1Q1RK1 b - - 0 14`

Game (full game at ply): http://localhost:5173/analysis?game_id=683333&ply=26

FEN (free-play from line start): http://localhost:5173/analysis?fen=rn1q1rk1/pb1pp1bp/1pP3p1/6N1/2P5/5N2/P3BPPP/1R1Q1RK1%20b%20-%20-%200%2014

#### Case 568 — PIN (allowed, depth 0)

Moves (SAN): `16... Ba5 17. Rc1 Qe4+ 18. Kd2 Ba4 19. Qxa4 Qxf3 20. Qxa5 Qxh1 21. h4 Qg1 22. Bd3`

FEN (line start): `r4rk1/pp3pp1/1bb1p1qp/3pP3/3P4/P1N2NP1/5P1P/R2QKB1R b - - 0 16`

Game (full game at ply): http://localhost:5173/analysis?game_id=683339&ply=30

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4rk1/pp3pp1/1bb1p1qp/3pP3/3P4/P1N2NP1/5P1P/R2QKB1R%20b%20-%20-%200%2016

#### Case 569 — SACRIFICE (missed, depth 6)

Moves (SAN): `18. Kd2 Ba4 19. Qxa4 Qxf3 20. Qxa5 Qxh1 21. h4 Qg1 22. Bd3 Qxf2+ 23. Ne2 b5`

FEN (line start): `r4rk1/pp3pp1/2b1p2p/b2pP3/3Pq3/P1N2NP1/5P1P/2RQKB1R w - - 0 18`

Game (full game at ply): http://localhost:5173/analysis?game_id=683339&ply=34

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4rk1/pp3pp1/2b1p2p/b2pP3/3Pq3/P1N2NP1/5P1P/2RQKB1R%20w%20-%20-%200%2018

#### Case 570 — CLEARANCE (allowed, depth 8)

Moves (SAN): `12. Nxf5 Qc7 13. Nxe7 Nxe7 14. Qc2 h5 15. d4 Nd7 16. Bd3 g6 17. a4 h4`

FEN (line start): `rn2k2r/pp2bppp/1qp1p1n1/3pPb2/3N1P2/1NPPB3/PP2Q1PP/R3KB1R w - - 1 12`

Game (full game at ply): http://localhost:5173/analysis?game_id=683341&ply=21

FEN (free-play from line start): http://localhost:5173/analysis?fen=rn2k2r/pp2bppp/1qp1p1n1/3pPb2/3N1P2/1NPPB3/PP2Q1PP/R3KB1R%20w%20-%20-%201%2012

#### Case 571 — CLEARANCE (missed, depth 4)

Moves (SAN): `11... Qa6 12. g4 Nxf4 13. Bxf4 Bg6 14. Qd2 c5 15. Nf3 Qb6 16. Be2 a5 17. d4`

FEN (line start): `rn2k2r/pp2bppp/2p1p1n1/1q1pPb2/3N1P2/1NPPB3/PP2Q1PP/R3KB1R b - - 0 11`

Game (full game at ply): http://localhost:5173/analysis?game_id=683341&ply=21

FEN (free-play from line start): http://localhost:5173/analysis?fen=rn2k2r/pp2bppp/2p1p1n1/1q1pPb2/3N1P2/1NPPB3/PP2Q1PP/R3KB1R%20b%20-%20-%200%2011

#### Case 572 — PIN (allowed, depth 4)

Moves (SAN): `29. Qxf1 Qd8 30. Bxc6 h5 31. Ra8 Qxa8 32. Bxa8 Kh7 33. Bxd5 h4 34. Qf7 Kh6`

FEN (line start): `7k/3B2pp/2p5/1p1pP1q1/1P1P4/2P3P1/4Q2P/R3Kr2 w - - 0 29`

Game (full game at ply): http://localhost:5173/analysis?game_id=683341&ply=55

FEN (free-play from line start): http://localhost:5173/analysis?fen=7k/3B2pp/2p5/1p1pP1q1/1P1P4/2P3P1/4Q2P/R3Kr2%20w%20-%20-%200%2029

#### Case 573 — DISCOVERED_ATTACK (allowed, depth 7)

Moves (SAN): `18... Bd4 19. Rb1 Nxa2 20. Bd2 f5 21. Ng5 Bxe5 22. fxe5 Rxd2 23. Rxf5 h6 24. Nf3`

FEN (line start): `2krr3/ppp2ppp/1b6/4P3/1nP1NP2/1P6/P5PP/R1B2R1K b - - 0 18`

Game (full game at ply): http://localhost:5173/analysis?game_id=683347&ply=34

FEN (free-play from line start): http://localhost:5173/analysis?fen=2krr3/ppp2ppp/1b6/4P3/1nP1NP2/1P6/P5PP/R1B2R1K%20b%20-%20-%200%2018

#### Case 574 — DEFLECTION (allowed, depth 8)

Moves (SAN): `11... Bxg5 12. Qa4 Rc8 13. c4`

FEN (line start): `r2qk2r/p3bppp/1pn4n/2ppPpB1/3P4/2P2N1P/PP3PP1/RN1QR1K1 b - - 1 11`

Game (full game at ply): http://localhost:5173/analysis?game_id=683359&ply=20

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qk2r/p3bppp/1pn4n/2ppPpB1/3P4/2P2N1P/PP3PP1/RN1QR1K1%20b%20-%20-%201%2011

#### Case 575 — PIN (missed, depth 6)

Moves (SAN): `16. Na3 Rxe7 17. Qc8+ Nd8 18. Nb5 Qc6 19. Nxa7 Qxc8 20. Nxc8 Rxe1+ 21. Rxe1+ Kd7`

FEN (line start): `4k2r/p1r1P1pp/Qpnq1p1n/2pp1pb1/3P4/2P2N1P/PP3PP1/RN2R1K1 w - - 0 16`

Game (full game at ply): http://localhost:5173/analysis?game_id=683359&ply=30

FEN (free-play from line start): http://localhost:5173/analysis?fen=4k2r/p1r1P1pp/Qpnq1p1n/2pp1pb1/3P4/2P2N1P/PP3PP1/RN2R1K1%20w%20-%20-%200%2016

#### Case 576 — DISCOVERED_ATTACK (allowed, depth 1)

Moves (SAN): `10... axb4 11. axb4 Rxa1 12. Qxa1 Nb3 13. Qa3 Nxd2 14. Kxd2 g6 15. Bc4 Bg7 16. Qa7`

FEN (line start): `r2qkbnr/1bpp1ppp/1p6/p1nP4/1P2P3/P1N2N2/3B1PPP/R2QKB1R b - - 0 10`

Game (full game at ply): http://localhost:5173/analysis?game_id=683364&ply=18

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qkbnr/1bpp1ppp/1p6/p1nP4/1P2P3/P1N2N2/3B1PPP/R2QKB1R%20b%20-%20-%200%2010

#### Case 577 — PIN (missed, depth 4)

Moves (SAN): `28. Qd2 Nxg2 29. f3 Qh8 30. Re7 Qf6 31. Rxd7 Nf4 32. Rxc7 Bd5 33. Rc3 Qh4`

FEN (line start): `q7/1bpp1p1k/1p4pp/4R3/3N1n2/3Q3P/5PP1/6K1 w - - 0 28`

Game (full game at ply): http://localhost:5173/analysis?game_id=683364&ply=54

FEN (free-play from line start): http://localhost:5173/analysis?fen=q7/1bpp1p1k/1p4pp/4R3/3N1n2/3Q3P/5PP1/6K1%20w%20-%20-%200%2028

#### Case 578 — DISCOVERED_CHECK (allowed, depth 4)

Moves (SAN): `30... Nxe3 31. Nf3 Nf1+ 32. Kg1 Nd2+ 33. Ne1 Nf3+ 34. Kf1 Kg7 35. Re3 Nxe1 36. Ke2`

FEN (line start): `8/1bppRp1k/1p4pp/8/3N4/4Q2P/5PnK/q7 b - - 1 30`

Game (full game at ply): http://localhost:5173/analysis?game_id=683364&ply=58

FEN (free-play from line start): http://localhost:5173/analysis?fen=8/1bppRp1k/1p4pp/8/3N4/4Q2P/5PnK/q7%20b%20-%20-%201%2030

#### Case 579 — SACRIFICE (missed, depth 6)

Moves (SAN): `30. Qb3 d5 31. Qf3 f5 32. Qg3 Qxd4 33. Re7+ Kh8 34. Re8+ Kh7 35. Qxc7+ Qg7`

FEN (line start): `8/1bpp1p1k/1p4pp/4R3/3N4/4Q2P/5PnK/q7 w - - 0 30`

Game (full game at ply): http://localhost:5173/analysis?game_id=683364&ply=58

FEN (free-play from line start): http://localhost:5173/analysis?fen=8/1bpp1p1k/1p4pp/4R3/3N4/4Q2P/5PnK/q7%20w%20-%20-%200%2030

#### Case 580 — CLEARANCE (allowed, depth 4)

Moves (SAN): `26... Qa2 27. Qg5+ Kh8 28. Rb1 Rg8 29. Qxh5 Rxg2+ 30. Ke3 Qa6 31. Rg1 Rxg1 32. Rxg1`

FEN (line start): `5rk1/r3pp1p/8/q1pP1Q1p/8/1pP5/1P1K2P1/3RR3 b - - 1 26`

Game (full game at ply): http://localhost:5173/analysis?game_id=683365&ply=50

FEN (free-play from line start): http://localhost:5173/analysis?fen=5rk1/r3pp1p/8/q1pP1Q1p/8/1pP5/1P1K2P1/3RR3%20b%20-%20-%201%2026

#### Case 581 — SKEWER (allowed, depth 6)

Moves (SAN): `30... Qa6 31. Rg3 Qg6 32. Kd2 Rxd5+ 33. Qxd5 Qxg3 34. Re1 e6 35. Qe5+ Qxe5 36. Rxe5`

FEN (line start): `5r1k/3rpp1p/8/q1pP2Qp/8/1pP1R3/1P4P1/1RK5 b - - 1 30`

Game (full game at ply): http://localhost:5173/analysis?game_id=683365&ply=58

FEN (free-play from line start): http://localhost:5173/analysis?fen=5r1k/3rpp1p/8/q1pP2Qp/8/1pP1R3/1P4P1/1RK5%20b%20-%20-%201%2030

#### Case 582 — SKEWER (missed, depth 10)

Moves (SAN): `35. Qxd2 Rxd2 36. Kxd2 Kg7 37. c4 Kf6 38. Ra5 Ke5 39. Rxc5+ Kd4 40. Rxh5 e5`

FEN (line start): `3r3k/4pp1p/8/2p4p/8/1pP5/1P1r2P1/R1K1Q3 w - - 0 35`

Game (full game at ply): http://localhost:5173/analysis?game_id=683365&ply=68

FEN (free-play from line start): http://localhost:5173/analysis?fen=3r3k/4pp1p/8/2p4p/8/1pP5/1P1r2P1/R1K1Q3%20w%20-%20-%200%2035

#### Case 583 — PROMOTION (allowed, depth 8)

Moves (SAN): `38... Qxe5 39. dxe5 a4 40. Kh2 a3 41. Kg3 a2 42. f4 a1=Q 43. Kh4 Qe1+ 44. Kg4`

FEN (line start): `8/2pkqp2/2p5/p2pQ3/3P4/2P2P1P/6P1/6K1 b - - 1 38`

Game (full game at ply): http://localhost:5173/analysis?game_id=683366&ply=74

FEN (free-play from line start): http://localhost:5173/analysis?fen=8/2pkqp2/2p5/p2pQ3/3P4/2P2P1P/6P1/6K1%20b%20-%20-%201%2038

#### Case 584 — PROMOTION (allowed, depth 10)

Moves (SAN): `40... a2 41. Kf1 Qf8 42. Kf2 Qb8 43. Qf4 Qb2+ 44. Kg3 Kc8 45. c4 a1=Q 46. cxd5`

FEN (line start): `8/2pkqp2/2p5/3p4/3P4/p1P2P1P/6P1/2Q3K1 b - - 1 40`

Game (full game at ply): http://localhost:5173/analysis?game_id=683366&ply=78

FEN (free-play from line start): http://localhost:5173/analysis?fen=8/2pkqp2/2p5/3p4/3P4/p1P2P1P/6P1/2Q3K1%20b%20-%20-%201%2040

#### Case 585 — HANGING_PIECE (allowed, depth 0)

Moves (SAN): `27... Nxh6 28. Rdd7 Qe5 29. h3 Kh8 30. a4 Rd6 31. g4 bxa4 32. Rxd6 Qxd6 33. Ra7`

FEN (line start): `4r1k1/2R2p1p/p3r1pQ/1p3n2/1P2q3/P3P3/2P2PPP/3R2K1 b - - 1 27`

Game (full game at ply): http://localhost:5173/analysis?game_id=683398&ply=52

FEN (free-play from line start): http://localhost:5173/analysis?fen=4r1k1/2R2p1p/p3r1pQ/1p3n2/1P2q3/P3P3/2P2PPP/3R2K1%20b%20-%20-%201%2027

#### Case 586 — CLEARANCE (missed, depth 10)

Moves (SAN): `19... Bd6 20. f5 Bf4 21. Re1 e5 22. Be3 Bxe3 23. fxe3 Kf7 24. Nc3 Rhd8 25. a4`

FEN (line start): `2r1kb1r/1p4pp/4pp2/3p4/2nB1P2/P6P/1P3P2/RNR3K1 b - - 0 19`

Game (full game at ply): http://localhost:5173/analysis?game_id=683399&ply=37

FEN (free-play from line start): http://localhost:5173/analysis?fen=2r1kb1r/1p4pp/4pp2/3p4/2nB1P2/P6P/1P3P2/RNR3K1%20b%20-%20-%200%2019

#### Case 587 — HANGING_PIECE (allowed, depth 0)

Moves (SAN): `22. Rxc5 Nf3+ 23. Kg2 Nh4+ 24. Kh1 Kd7 25. Nd2 g5 26. Rb5 gxf4 27. Rxb7+ Kc6`

FEN (line start): `4k2r/1p4pp/4pp2/2rp4/5P2/PP5P/3n1P2/RNR3K1 w - - 1 22`

Game (full game at ply): http://localhost:5173/analysis?game_id=683399&ply=41

FEN (free-play from line start): http://localhost:5173/analysis?fen=4k2r/1p4pp/4pp2/2rp4/5P2/PP5P/3n1P2/RNR3K1%20w%20-%20-%201%2022

#### Case 588 — SACRIFICE (missed, depth 2)

Moves (SAN): `21... Kd7 22. bxc4 b5 23. Nc3 bxc4 24. Rab1 Kc6 25. Re1 Re8 26. Kf1 e5 27. Rb4`

FEN (line start): `4k2r/1p4pp/4pp2/2rp4/2n2P2/PP5P/5P2/RNR3K1 b - - 0 21`

Game (full game at ply): http://localhost:5173/analysis?game_id=683399&ply=41

FEN (free-play from line start): http://localhost:5173/analysis?fen=4k2r/1p4pp/4pp2/2rp4/2n2P2/PP5P/5P2/RNR3K1%20b%20-%20-%200%2021

#### Case 589 — CLEARANCE (allowed, depth 4)

Moves (SAN): `10... Bxd3 11. cxd3 g6 12. Nge2 Bg7`

FEN (line start): `rn2kb1r/pp1n1pp1/1qp1p1b1/3p2Pp/3P1B1P/P1NBPP2/1PP5/R2QK1NR b - - 0 10`

Game (full game at ply): http://localhost:5173/analysis?game_id=683400&ply=18

FEN (free-play from line start): http://localhost:5173/analysis?fen=rn2kb1r/pp1n1pp1/1qp1p1b1/3p2Pp/3P1B1P/P1NBPP2/1PP5/R2QK1NR%20b%20-%20-%200%2010

#### Case 590 — CLEARANCE (missed, depth 8)

Moves (SAN): `17... c6 18. a4 Rce8 19. Rc5 Nc8 20. Qc2 Nd6 21. b4 Ra8 22. h3 Qf6 23. Ne5`

FEN (line start): `2r2rk1/npp1qpp1/p3b2p/3p4/3P4/PQ1BPN2/1PR2PPP/2R3K1 b - - 0 17`

Game (full game at ply): http://localhost:5173/analysis?game_id=683411&ply=33

FEN (free-play from line start): http://localhost:5173/analysis?fen=2r2rk1/npp1qpp1/p3b2p/3p4/3P4/PQ1BPN2/1PR2PPP/2R3K1%20b%20-%20-%200%2017

#### Case 591 — PROMOTION (allowed, depth 8)

Moves (SAN): `46. Re6+ Kd3 47. d5 Ra1 48. d6 Rxa6 49. d7 Rxe6 50. d8=Q+ Ke2 51. Qg5 Rxe3+`

FEN (line start): `8/6p1/P2R4/7p/3PkPp1/4P1K1/r7/8 w - - 1 46`

Game (full game at ply): http://localhost:5173/analysis?game_id=683411&ply=89

FEN (free-play from line start): http://localhost:5173/analysis?fen=8/6p1/P2R4/7p/3PkPp1/4P1K1/r7/8%20w%20-%20-%201%2046

#### Case 592 — PIN (missed, depth 2)

Moves (SAN): `45... g6 46. Rc6 Ra3 47. Rc5+ Kf6 48. Rc6+`

FEN (line start): `8/6p1/P2R4/5k1p/3P1Pp1/4P1K1/r7/8 b - - 0 45`

Game (full game at ply): http://localhost:5173/analysis?game_id=683411&ply=89

FEN (free-play from line start): http://localhost:5173/analysis?fen=8/6p1/P2R4/5k1p/3P1Pp1/4P1K1/r7/8%20b%20-%20-%200%2045

#### Case 593 — SKEWER (missed, depth 10)

Moves (SAN): `51... Rf1+ 52. Ke5 Re1 53. d5 Rxe4+ 54. Kd6 Ra4 55. Kc5 Ra5+ 56. Kb6 Rxd5 57. a7`

FEN (line start): `8/6p1/P3R3/5P1p/3PPKp1/3k4/8/6r1 b - - 0 51`

Game (full game at ply): http://localhost:5173/analysis?game_id=683411&ply=101

FEN (free-play from line start): http://localhost:5173/analysis?fen=8/6p1/P3R3/5P1p/3PPKp1/3k4/8/6r1%20b%20-%20-%200%2051

#### Case 594 — PIN (allowed, depth 8)

Moves (SAN): `13. Bxd5 Nb4 14. N2c3 c6 15. Bc4 Qd4 16. h5 b5 17. hxg6 Bxg6 18. Be2 a5`

FEN (line start): `r2q1rk1/1pp2pbp/p1n3p1/3npbP1/2B1N2P/1P3Q2/PBPPNP2/2KR3R w - - 0 13`

Game (full game at ply): http://localhost:5173/analysis?game_id=683426&ply=23

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2q1rk1/1pp2pbp/p1n3p1/3npbP1/2B1N2P/1P3Q2/PBPPNP2/2KR3R%20w%20-%20-%200%2013

#### Case 595 — CLEARANCE (allowed, depth 6)

Moves (SAN): `29. dxc3 Ne6 30. Qg3 Nf4 31. c4 Kg8 32. Qc3 Re8 33. Rhf1 b4 34. axb4 Ne2`

FEN (line start): `r2r3k/2p2p1p/q5pP/1p2p1P1/3nP3/PPbQ4/1B1P4/1K1R3R w - - 0 29`

Game (full game at ply): http://localhost:5173/analysis?game_id=683426&ply=55

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2r3k/2p2p1p/q5pP/1p2p1P1/3nP3/PPbQ4/1B1P4/1K1R3R%20w%20-%20-%200%2029

#### Case 596 — DISCOVERED_ATTACK (missed, depth 7)

Moves (SAN): `29... Kg8 30. b4 Qe6 31. Qh3 Qe7 32. Rc1 Ne6 33. Rc6 Rxd2 34. Rhc1 Rad8 35. Qg3`

FEN (line start): `r2r3k/2p2p1p/q5pP/1p2p1P1/3nP3/PPQ5/1B1P4/1K1R3R b - - 0 29`

Game (full game at ply): http://localhost:5173/analysis?game_id=683426&ply=57

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2r3k/2p2p1p/q5pP/1p2p1P1/3nP3/PPQ5/1B1P4/1K1R3R%20b%20-%20-%200%2029

#### Case 597 — SACRIFICE (allowed, depth 2)

Moves (SAN): `34. Qxe5 Nxc1 35. Rf1 f5 36. Rxc1 f4 37. Qh8+ Kf7 38. Qxh7+ Ke8 39. Qg8+ Ke7`

FEN (line start): `r1r3k1/q4p1p/2p2RpP/1p2p1P1/4P3/PPQP4/1B2n3/1KR5 w - - 1 34`

Game (full game at ply): http://localhost:5173/analysis?game_id=683426&ply=65

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1r3k1/q4p1p/2p2RpP/1p2p1P1/4P3/PPQP4/1B2n3/1KR5%20w%20-%20-%201%2034

#### Case 598 — SKEWER (allowed, depth 6)

Moves (SAN): `36. Rxc6 Kf8 37. Rxc8+ Rxc8 38. Qh8+ Ke7 39. Qxc8 bxa3 40. Ka2 Qf2+ 41. Kxa3 Qd4`

FEN (line start): `r1r3k1/q4p1p/2p2RpP/4Q1P1/1p2P3/PP1P4/8/1KB5 w - - 0 36`

Game (full game at ply): http://localhost:5173/analysis?game_id=683426&ply=69

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1r3k1/q4p1p/2p2RpP/4Q1P1/1p2P3/PP1P4/8/1KB5%20w%20-%20-%200%2036

#### Case 599 — SACRIFICE (missed, depth 6)

Moves (SAN): `36... Kf8 37. Rxc8+ Rxc8 38. Qh8+ Ke7 39. Qxc8 bxa3 40. Qc3 Kd7 41. d4 f5 42. Qc4`

FEN (line start): `r1r3k1/q4p1p/2R3pP/4Q1P1/1p2P3/PP1P4/8/1KB5 b - - 0 36`

Game (full game at ply): http://localhost:5173/analysis?game_id=683426&ply=71

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1r3k1/q4p1p/2R3pP/4Q1P1/1p2P3/PP1P4/8/1KB5%20b%20-%20-%200%2036

#### Case 600 — CLEARANCE (missed, depth 10)

Moves (SAN): `15... Kd7 16. a4 bxa4 17. N2b3 Ng6 18. Nxf5 exf5 19. f4 Be7 20. Nd4 Rhb8 21. Nxf5`

FEN (line start): `r3kb1r/4nppp/2p1p3/1p1pPb2/3N4/2P1B3/P2N1PPP/R4RK1 b - - 0 15`

Game (full game at ply): http://localhost:5173/analysis?game_id=683441&ply=29

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3kb1r/4nppp/2p1p3/1p1pPb2/3N4/2P1B3/P2N1PPP/R4RK1%20b%20-%20-%200%2015

#### Case 601 — FORK (allowed, depth 0)

Moves (SAN): `18. Nd6+ Kd7 19. Nxc8 Kxc8 20. Bg5 Nc6 21. f4 h6 22. Bh4 Rg8 23. Rf3 g5`

FEN (line start): `2r1kb1r/4nppp/4p3/1Np1Pb2/2Pp4/4B3/P2N1PPP/R4RK1 w - - 0 18`

Game (full game at ply): http://localhost:5173/analysis?game_id=683441&ply=33

FEN (free-play from line start): http://localhost:5173/analysis?fen=2r1kb1r/4nppp/4p3/1Np1Pb2/2Pp4/4B3/P2N1PPP/R4RK1%20w%20-%20-%200%2018

#### Case 602 — TRAPPED_PIECE (missed, depth 2)

Moves (SAN): `20... f6 21. a4 fxg5 22. a5 Kd7 23. a6 Ra8 24. a7 Ne5 25. Ra6 Bd3 26. Rc1`

FEN (line start): `2r1k2r/5ppp/3Pp1n1/2p2bB1/2Pp4/8/P2N1PPP/R4RK1 b - - 0 20`

Game (full game at ply): http://localhost:5173/analysis?game_id=683441&ply=39

FEN (free-play from line start): http://localhost:5173/analysis?fen=2r1k2r/5ppp/3Pp1n1/2p2bB1/2Pp4/8/P2N1PPP/R4RK1%20b%20-%20-%200%2020

#### Case 603 — CLEARANCE (allowed, depth 2)

Moves (SAN): `14. c4 Qa5 15. Qc2 Bg6 16. Qb3 Nc3 17. Bd1 Nxd1 18. Rfxd1 Qa6 19. Rac1 Na5`

FEN (line start): `r4rk1/pp3ppp/2n1p3/3q3b/3Pn3/P3BN1P/2P1BPP1/R2Q1RK1 w - - 0 14`

Game (full game at ply): http://localhost:5173/analysis?game_id=683463&ply=25

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4rk1/pp3ppp/2n1p3/3q3b/3Pn3/P3BN1P/2P1BPP1/R2Q1RK1%20w%20-%20-%200%2014

#### Case 604 — FORK (allowed, depth 0)

Moves (SAN): `16. g4 Bxg4 17. hxg4 Qxg4 18. Qd3 Nc5 19. Qc3 Qh5+ 20. Nh2 Qxe2 21. dxc5 f6`

FEN (line start): `3r1rk1/pp3ppp/2n1p3/5q1b/2PPn3/P3BN1P/4BPP1/R2Q1R1K w - - 1 16`

Game (full game at ply): http://localhost:5173/analysis?game_id=683463&ply=29

FEN (free-play from line start): http://localhost:5173/analysis?fen=3r1rk1/pp3ppp/2n1p3/5q1b/2PPn3/P3BN1P/4BPP1/R2Q1R1K%20w%20-%20-%201%2016

#### Case 605 — CLEARANCE (allowed, depth 10)

Moves (SAN): `8... f6 9. exf6 Nxf6 10. Bd3 d6`

FEN (line start): `r1b1k2r/ppppqppp/2n5/4P1Bn/4P3/P1P2N2/1PP3PP/R2QKB1R b - - 1 8`

Game (full game at ply): http://localhost:5173/analysis?game_id=683473&ply=14

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1b1k2r/ppppqppp/2n5/4P1Bn/4P3/P1P2N2/1PP3PP/R2QKB1R%20b%20-%20-%201%208

#### Case 606 — ATTRACTION (missed, depth 2)

Moves (SAN): `15. Qh5 Qf7 16. Qxf7+ Kxf7 17. Rf1+ Ke7 18. Nf5+ Kf7 19. Nxh6+ Kg6 20. Nf5 b6`

FEN (line start): `r1b2qk1/pppp2p1/2n4p/8/3NP3/P1PB4/1PP3PP/R2Q2K1 w - - 0 15`

Game (full game at ply): http://localhost:5173/analysis?game_id=683473&ply=28

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1b2qk1/pppp2p1/2n4p/8/3NP3/P1PB4/1PP3PP/R2Q2K1%20w%20-%20-%200%2015

#### Case 607 — FORK (allowed, depth 4)

Moves (SAN): `18... Nxe4 19. Qxb4 Qxb4 20. Bxb4 Nf2 21. Bxf5 Nf6 22. Bd3 Ba6 23. c4 Nxh1 24. Rxh1`

FEN (line start): `r1b1k2r/3n2pp/1qpBBn2/5p2/pp2P3/4P3/PPPQ2PP/1NKR3R b - - 1 18`

Game (full game at ply): http://localhost:5173/analysis?game_id=683493&ply=34

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1b1k2r/3n2pp/1qpBBn2/5p2/pp2P3/4P3/PPPQ2PP/1NKR3R%20b%20-%20-%201%2018

#### Case 608 — FORK (missed, depth 6)

Moves (SAN): `21... f5 22. Kg2 Na5 23. Rhf1 Nc4 24. Kh1 Nd2 25. gxf5 Qf6 26. Qg3 Nxf1 27. Rxf1`

FEN (line start): `4rr2/pp3ppk/2n1q2p/3p3P/3P2P1/P1P1PQ2/5K1N/R6R b - - 0 21`

Game (full game at ply): http://localhost:5173/analysis?game_id=683513&ply=41

FEN (free-play from line start): http://localhost:5173/analysis?fen=4rr2/pp3ppk/2n1q2p/3p3P/3P2P1/P1P1PQ2/5K1N/R6R%20b%20-%20-%200%2021

#### Case 609 — CLEARANCE (allowed, depth 2)

Moves (SAN): `16... f5 17. Re1 Rf7 18. h4 Raf8 19. h5 Rg7 20. hxg6 hxg6 21. Rh3 Nd8 22. Qg5`

FEN (line start): `r4rk1/pp3p1p/2nqp1pQ/3p4/3P4/2PB1R2/PP4PP/R5K1 b - - 1 16`

Game (full game at ply): http://localhost:5173/analysis?game_id=683526&ply=30

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4rk1/pp3p1p/2nqp1pQ/3p4/3P4/2PB1R2/PP4PP/R5K1%20b%20-%20-%201%2016

#### Case 610 — CLEARANCE (allowed, depth 6)

Moves (SAN): `36... Kh6 37. Kxb6 a4 38. Bb5 Ne4 39. Qd4 Qc1 40. c4 a3 41. bxa3 Qxa3 42. c5`

FEN (line start): `8/3Q2kp/1p4p1/pK3pq1/8/2PB3P/PP1n4/8 b - - 1 36`

Game (full game at ply): http://localhost:5173/analysis?game_id=683526&ply=70

FEN (free-play from line start): http://localhost:5173/analysis?fen=8/3Q2kp/1p4p1/pK3pq1/8/2PB3P/PP1n4/8%20b%20-%20-%201%2036

#### Case 611 — DISCOVERED_CHECK (allowed, depth 0)

Moves (SAN): `37... f4+ 38. Bd5 f3 39. Qf7 Qf5 40. Qxf5 gxf5 41. Bxf3 Nxf3 42. Kxb6 f4 43. Kc5`

FEN (line start): `8/3Q3p/1p4pk/pK3pq1/2B5/2P4P/PP1n4/8 b - - 1 37`

Game (full game at ply): http://localhost:5173/analysis?game_id=683526&ply=72

FEN (free-play from line start): http://localhost:5173/analysis?fen=8/3Q3p/1p4pk/pK3pq1/2B5/2P4P/PP1n4/8%20b%20-%20-%201%2037

#### Case 612 — PIN (missed, depth 8)

Moves (SAN): `8. d5 exd5 9. Nxd5 Bb4+ 10. c3 Bd6 11. Qe2+ Nge7 12. Bxd6 cxd6`

FEN (line start): `r2qkbnr/pppb2pp/2n1pp2/1B6/3P1B2/2N2N2/PPP3PP/R2QK2R w - - 0 8`

Game (full game at ply): http://localhost:5173/analysis?game_id=683536&ply=14

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qkbnr/pppb2pp/2n1pp2/1B6/3P1B2/2N2N2/PPP3PP/R2QK2R%20w%20-%20-%200%208

#### Case 613 — HANGING_PIECE (allowed, depth 0)

Moves (SAN): `22... Rfxf7 23. Rd6 Rxd6 24. Qxd6 Qc5 25. Kb2 g5 26. Rd5 Qxd6 27. Rxd6 Kg7 28. Rxb6`

FEN (line start): `5r1k/1pqr1Np1/1p2Rp1p/3Q4/8/1P6/P1P3PP/1K1R4 b - - 1 22`

Game (full game at ply): http://localhost:5173/analysis?game_id=683536&ply=42

FEN (free-play from line start): http://localhost:5173/analysis?fen=5r1k/1pqr1Np1/1p2Rp1p/3Q4/8/1P6/P1P3PP/1K1R4%20b%20-%20-%201%2022

#### Case 614 — INTERMEZZO (allowed, depth 2)

Moves (SAN): `20. Be3 Rfc8 21. Qxd4 Qxd4 22. Bxd4 Rc4 23. Be3 h6 24. Rfd1 a6 25. Kf1 Rb8`

FEN (line start): `r4rk1/p4ppp/4p3/3pP3/q2n2Q1/8/P2B1PPP/R4RK1 w - - 0 20`

Game (full game at ply): http://localhost:5173/analysis?game_id=683545&ply=37

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4rk1/p4ppp/4p3/3pP3/q2n2Q1/8/P2B1PPP/R4RK1%20w%20-%20-%200%2020

#### Case 615 — FORK (allowed, depth 0)

Moves (SAN): `9. Qxd5 Qxd5 10. Nxd5 e5 11. Bxe5 Nc6 12. Nf3 Bb4+ 13. Nxb4 Nxb4 14. Rc1 Nd3+`

FEN (line start): `rnb1kb1r/p3pppp/8/q2p4/2p1nB2/2N5/PP3PPP/R2QKBNR w - - 0 9`

Game (full game at ply): http://localhost:5173/analysis?game_id=683546&ply=15

FEN (free-play from line start): http://localhost:5173/analysis?fen=rnb1kb1r/p3pppp/8/q2p4/2p1nB2/2N5/PP3PPP/R2QKBNR%20w%20-%20-%200%209

#### Case 616 — TRAPPED_PIECE (allowed, depth 10)

Moves (SAN): `14. Bxc4 Be7 15. Nf3`

FEN (line start): `rn2kb1r/p4ppp/4p3/8/b1ppPB2/P7/1P4PP/R3KBNR w - - 0 14`

Game (full game at ply): http://localhost:5173/analysis?game_id=683546&ply=25

FEN (free-play from line start): http://localhost:5173/analysis?fen=rn2kb1r/p4ppp/4p3/8/b1ppPB2/P7/1P4PP/R3KBNR%20w%20-%20-%200%2014

#### Case 617 — CLEARANCE (missed, depth 10)

Moves (SAN): `13... Bc5 14. Ne2`

FEN (line start): `rn2kb1r/p4ppp/4p3/3p4/b1p1PB2/P7/1P4PP/R3KBNR b - - 0 13`

Game (full game at ply): http://localhost:5173/analysis?game_id=683546&ply=25

FEN (free-play from line start): http://localhost:5173/analysis?fen=rn2kb1r/p4ppp/4p3/3p4/b1p1PB2/P7/1P4PP/R3KBNR%20b%20-%20-%200%2013

#### Case 618 — CAPTURING_DEFENDER (missed, depth 8)

Moves (SAN): `18... Nc6 19. Nc1`

FEN (line start): `rn2k2r/p4ppp/1b2p3/8/bPRpPB2/8/4N1PP/4KB1R b - - 0 18`

Game (full game at ply): http://localhost:5173/analysis?game_id=683546&ply=35

FEN (free-play from line start): http://localhost:5173/analysis?fen=rn2k2r/p4ppp/1b2p3/8/bPRpPB2/8/4N1PP/4KB1R%20b%20-%20-%200%2018

#### Case 619 — PIN (missed, depth 6)

Moves (SAN): `24. Rc8 Qa5 25. Nxe7+ Kg7 26. Rxf8 Kxf8 27. Qxg6 f6 28. Qh7 Rg5 29. Rc1 Bc5`

FEN (line start): `3q1rk1/1p2pp2/p2p2p1/1r1N4/3bP1Q1/7P/6P1/2R2R1K w - - 0 24`

Game (full game at ply): http://localhost:5173/analysis?game_id=683549&ply=46

FEN (free-play from line start): http://localhost:5173/analysis?fen=3q1rk1/1p2pp2/p2p2p1/1r1N4/3bP1Q1/7P/6P1/2R2R1K%20w%20-%20-%200%2024

#### Case 620 — SACRIFICE (allowed, depth 6)

Moves (SAN): `25... Bf6 26. Rxe7 Rxd5 27. Rxe8+ Qxe8 28. exd5 Be5 29. Qg4 Kg7 30. h4 b5 31. g3`

FEN (line start): `3qr1k1/1pR1pp2/p2p2p1/1r1N4/3bPQ2/7P/6P1/5R1K b - - 1 25`

Game (full game at ply): http://localhost:5173/analysis?game_id=683549&ply=48

FEN (free-play from line start): http://localhost:5173/analysis?fen=3qr1k1/1pR1pp2/p2p2p1/1r1N4/3bPQ2/7P/6P1/5R1K%20b%20-%20-%201%2025

#### Case 621 — PIN (missed, depth 6)

Moves (SAN): `25. Rd7 Qc8 26. Rxe7 Rxd5 27. exd5 Be5 28. Qxc8 Rxc8 29. Rxb7 a5 30. Rbxf7 Ra8`

FEN (line start): `3qr1k1/1pR1pp2/p2p2p1/1r1N4/3bP1Q1/7P/6P1/5R1K w - - 0 25`

Game (full game at ply): http://localhost:5173/analysis?game_id=683549&ply=48

FEN (free-play from line start): http://localhost:5173/analysis?fen=3qr1k1/1pR1pp2/p2p2p1/1r1N4/3bP1Q1/7P/6P1/5R1K%20w%20-%20-%200%2025

#### Case 622 — CLEARANCE (missed, depth 2)

Moves (SAN): `34. Ra7 Ra1 35. Reb7 Kg7 36. e6 Kf6 37. exf7 Kg7 38. Ra6 Rxf7 39. Rbb6 Kg8`

FEN (line start): `5rk1/2R1Rp2/6p1/p3P3/1p6/7P/6PK/4r3 w - - 0 34`

Game (full game at ply): http://localhost:5173/analysis?game_id=683549&ply=66

FEN (free-play from line start): http://localhost:5173/analysis?fen=5rk1/2R1Rp2/6p1/p3P3/1p6/7P/6PK/4r3%20w%20-%20-%200%2034

#### Case 623 — CLEARANCE (allowed, depth 2)

Moves (SAN): `59... Kf1 60. Kf4 g1=Q 61. Ke5 Qc5+ 62. Kf6 Qd6+ 63. Kf5 Qe7 64. Kg4 Kf2 65. Kf4`

FEN (line start): `8/8/8/8/8/6K1/6p1/6k1 b - - 1 59`

Game (full game at ply): http://localhost:5173/analysis?game_id=683549&ply=116

FEN (free-play from line start): http://localhost:5173/analysis?fen=8/8/8/8/8/6K1/6p1/6k1%20b%20-%20-%201%2059

#### Case 624 — DISCOVERED_ATTACK (missed, depth 3)

Moves (SAN): `9. Be5 Bxe5 10. dxe5 Be6 11. Qxd5 Bxd5 12. Rc1 Nd7 13. Bb5 Bxf3 14. gxf3 Nxe5`

FEN (line start): `rnb2rk1/pp2ppbp/6p1/2pq4/3P1B2/4PN2/PP3PPP/R2QKB1R w - - 0 9`

Game (full game at ply): http://localhost:5173/analysis?game_id=683556&ply=16

FEN (free-play from line start): http://localhost:5173/analysis?fen=rnb2rk1/pp2ppbp/6p1/2pq4/3P1B2/4PN2/PP3PPP/R2QKB1R%20w%20-%20-%200%209

#### Case 625 — CLEARANCE (allowed, depth 10)

Moves (SAN): `29... Qa1 30. Qd2 Be5+ 31. g3 Bc3 32. Qe2 Rfd8 33. Rd3 Rxd3 34. Bxd3 Rd8 35. h4`

FEN (line start): `1r3r1k/3R2bp/6p1/3Q4/2B5/1P2P2P/P5PK/5q2 b - - 1 29`

Game (full game at ply): http://localhost:5173/analysis?game_id=683556&ply=56

FEN (free-play from line start): http://localhost:5173/analysis?fen=1r3r1k/3R2bp/6p1/3Q4/2B5/1P2P2P/P5PK/5q2%20b%20-%20-%201%2029

#### Case 626 — DISCOVERED_CHECK (allowed, depth 2)

Moves (SAN): `10. Nxc6 Qc8 11. Ne5+ axb5 12. Qxb5+ Nd7 13. Na4 Rxa4 14. Qxa4 f6 15. Nxd7 Qxd7`

FEN (line start): `r3kb1r/1pq2ppp/p1n1pn2/1B1pNb2/Q2P4/2N1P3/PP3PPP/R1B1K2R w - - 0 10`

Game (full game at ply): http://localhost:5173/analysis?game_id=683558&ply=17

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3kb1r/1pq2ppp/p1n1pn2/1B1pNb2/Q2P4/2N1P3/PP3PPP/R1B1K2R%20w%20-%20-%200%2010

#### Case 627 — PROMOTION (missed, depth 2)

Moves (SAN): `48... Kg8 49. b5 h1=Q 50. Qxh1 Bxh1 51. b6 Kg7 52. b7 Be4 53. Kd4 Bf5 54. b8=Q`

FEN (line start): `8/5pk1/6p1/3N4/1PK5/5b2/7p/Q7 b - - 0 48`

Game (full game at ply): http://localhost:5173/analysis?game_id=683558&ply=95

FEN (free-play from line start): http://localhost:5173/analysis?fen=8/5pk1/6p1/3N4/1PK5/5b2/7p/Q7%20b%20-%20-%200%2048

#### Case 628 — PROMOTION (missed, depth 2)

Moves (SAN): `49... g5 50. b5 h1=Q 51. Qxh1+ Bxh1 52. b6 Bxd5+ 53. Kxd5 Kh5 54. b7 Kg4 55. b8=Q`

FEN (line start): `8/5p2/6pk/3N4/1PK5/5b2/7p/2Q5 b - - 0 49`

Game (full game at ply): http://localhost:5173/analysis?game_id=683558&ply=97

FEN (free-play from line start): http://localhost:5173/analysis?fen=8/5p2/6pk/3N4/1PK5/5b2/7p/2Q5%20b%20-%20-%200%2049

#### Case 629 — PIN (allowed, depth 10)

Moves (SAN): `6. dxe5 Nxe5`

FEN (line start): `r2qkbnr/ppp2ppp/2n5/3pp3/3P4/5PP1/PPP2PBP/RNBQK2R w - - 0 6`

Game (full game at ply): http://localhost:5173/analysis?game_id=683559&ply=9

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qkbnr/ppp2ppp/2n5/3pp3/3P4/5PP1/PPP2PBP/RNBQK2R%20w%20-%20-%200%206

#### Case 630 — PIN (allowed, depth 2)

Moves (SAN): `8... dxe4 9. Nxe4 Re8 10. Bd3 Nc6`

FEN (line start): `rnbq1rk1/ppp2ppp/5b2/3p4/3PP3/2N2N2/PP3PPP/R2QKB1R b - - 0 8`

Game (full game at ply): http://localhost:5173/analysis?game_id=683562&ply=14

FEN (free-play from line start): http://localhost:5173/analysis?fen=rnbq1rk1/ppp2ppp/5b2/3p4/3PP3/2N2N2/PP3PPP/R2QKB1R%20b%20-%20-%200%208

#### Case 631 — CLEARANCE (missed, depth 2)

Moves (SAN): `8. e3 g6 9. Bd3 a5 10. h3 c6`

FEN (line start): `rnbq1rk1/ppp2ppp/5b2/3p4/3P4/2N2N2/PP2PPPP/R2QKB1R w - - 0 8`

Game (full game at ply): http://localhost:5173/analysis?game_id=683562&ply=14

FEN (free-play from line start): http://localhost:5173/analysis?fen=rnbq1rk1/ppp2ppp/5b2/3p4/3P4/2N2N2/PP2PPPP/R2QKB1R%20w%20-%20-%200%208

#### Case 632 — HANGING_PIECE (missed, depth 0)

Moves (SAN): `14. gxf3 Nc6 15. Rad1 Qh4 16. Bc4 Qf4 17. Kg2 Be5 18. Rh1 Na5 19. Qc2 Nxc4`

FEN (line start): `rn1qr1k1/ppp2ppp/8/8/3bN3/1Q1B1b1P/PP3PP1/R4RK1 w - - 0 14`

Game (full game at ply): http://localhost:5173/analysis?game_id=683562&ply=26

FEN (free-play from line start): http://localhost:5173/analysis?fen=rn1qr1k1/ppp2ppp/8/8/3bN3/1Q1B1b1P/PP3PP1/R4RK1%20w%20-%20-%200%2014

#### Case 633 — SACRIFICE (missed, depth 10)

Moves (SAN): `14... Rc8 15. Re3 Rc4 16. Rb1 h6 17. Bxf6 Qxf6 18. Rxb7 Rf4 19. Rxa7 Rb8 20. Re1`

FEN (line start): `r2q1rk1/pp3ppp/4pn2/3p2B1/8/2P3Q1/P1P2PPP/R3R1K1 b - - 0 14`

Game (full game at ply): http://localhost:5173/analysis?game_id=683570&ply=27

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2q1rk1/pp3ppp/4pn2/3p2B1/8/2P3Q1/P1P2PPP/R3R1K1%20b%20-%20-%200%2014

#### Case 634 — CLEARANCE (allowed, depth 8)

Moves (SAN): `42... Rf8 43. h4 Rc8 44. Kg1 Qc3 45. h5 Qf6 46. Qa1 Rc3 47. Rf3 Qe5 48. Qa4`

FEN (line start): `8/6pk/4pr1p/3p1p2/2q5/4P3/6PP/4QR1K b - - 1 42`

Game (full game at ply): http://localhost:5173/analysis?game_id=683578&ply=82

FEN (free-play from line start): http://localhost:5173/analysis?fen=8/6pk/4pr1p/3p1p2/2q5/4P3/6PP/4QR1K%20b%20-%20-%201%2042

#### Case 635 — PIN (allowed, depth 0)

Moves (SAN): `42. Kc6 e5 43. d5 f4 44. gxf4 Qxb7+ 45. Kxb7 exf4 46. d6 f3 47. d7 f2`

FEN (line start): `8/pQ1K2qk/4pp2/5p2/1P1P4/2P3P1/8/8 w - - 0 42`

Game (full game at ply): http://localhost:5173/analysis?game_id=683627&ply=81

FEN (free-play from line start): http://localhost:5173/analysis?fen=8/pQ1K2qk/4pp2/5p2/1P1P4/2P3P1/8/8%20w%20-%20-%200%2042

#### Case 636 — PIN (allowed, depth 10)

Moves (SAN): `45. d6 f4 46. gxf4 Kg6 47. d7 a5 48. d8=Q axb4 49. cxb4 Kf5 50. Qd5 Kxf4`

FEN (line start): `8/pK4k1/5p2/3Ppp2/1P6/2P3P1/8/8 w - - 1 45`

Game (full game at ply): http://localhost:5173/analysis?game_id=683627&ply=87

FEN (free-play from line start): http://localhost:5173/analysis?fen=8/pK4k1/5p2/3Ppp2/1P6/2P3P1/8/8%20w%20-%20-%201%2045

#### Case 637 — CLEARANCE (allowed, depth 2)

Moves (SAN): `23. Ba3 Nf4 24. Rad1 g5 25. fxg6 hxg6 26. Rxd7 Rxd7 27. Kf3 g5 28. Rd1 Rxd1`

FEN (line start): `3r2k1/p1br1ppp/Pp3n2/1P2pP2/2N1P1P1/2PnK2P/2B5/R1B4R w - - 1 23`

Game (full game at ply): http://localhost:5173/analysis?game_id=683636&ply=43

FEN (free-play from line start): http://localhost:5173/analysis?fen=3r2k1/p1br1ppp/Pp3n2/1P2pP2/2N1P1P1/2PnK2P/2B5/R1B4R%20w%20-%20-%201%2023

#### Case 638 — FORK (missed, depth 0)

Moves (SAN): `27... Ne1+ 28. Kf2 Nxc2 29. Ra2 Rd3 30. Rxc2 Ng3 31. Nd2 Bd6 32. Kg2 f6 33. Nc4`

FEN (line start): `6k1/p1br1ppp/Pp6/1P2pPPn/2N1P2P/2P2K2/2B3n1/R1B5 b - - 0 27`

Game (full game at ply): http://localhost:5173/analysis?game_id=683636&ply=53

FEN (free-play from line start): http://localhost:5173/analysis?fen=6k1/p1br1ppp/Pp6/1P2pPPn/2N1P2P/2P2K2/2B3n1/R1B5%20b%20-%20-%200%2027

#### Case 639 — DISCOVERED_CHECK (allowed, depth 6)

Moves (SAN): `34. Nxd6 Re7 35. Bb3 Kf8 36. Rxf7+ Rxf7 37. Nxf7+ Ke8 38. Bd5 Kd7 39. Kh6 Ke8`

FEN (line start): `8/p2r1pkp/Pp1b4/1P2p1PK/2N1P3/B1P2R2/2B5/8 w - - 1 34`

Game (full game at ply): http://localhost:5173/analysis?game_id=683636&ply=65

FEN (free-play from line start): http://localhost:5173/analysis?fen=8/p2r1pkp/Pp1b4/1P2p1PK/2N1P3/B1P2R2/2B5/8%20w%20-%20-%201%2034

#### Case 640 — INTERMEZZO (allowed, depth 6)

Moves (SAN): `16. cxd5 Nf4 17. Qc4 Nxd5 18. Na4 Qb4 19. Bxd5 exd5 20. Qxc5 Qxa4 21. Qxd5 Rad8`

FEN (line start): `r4rk1/pp3ppp/1q2p1n1/2bp4/2P5/2N2B2/PP2QPPP/R4RK1 w - - 1 16`

Game (full game at ply): http://localhost:5173/analysis?game_id=683637&ply=29

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4rk1/pp3ppp/1q2p1n1/2bp4/2P5/2N2B2/PP2QPPP/R4RK1%20w%20-%20-%201%2016

#### Case 641 — CLEARANCE (allowed, depth 4)

Moves (SAN): `17... Bxb4 18. cxb4 Nb6 19. e4 Qd7 20. Ra5 Rb8 21. Bf4 Rb7 22. Qa2`

FEN (line start): `r3kb1r/p2n2pp/2p1pp2/3q4/1RpP4/2P1PN1P/3BQPP1/R5K1 b - - 1 17`

Game (full game at ply): http://localhost:5173/analysis?game_id=683642&ply=32

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3kb1r/p2n2pp/2p1pp2/3q4/1RpP4/2P1PN1P/3BQPP1/R5K1%20b%20-%20-%201%2017

#### Case 642 — CLEARANCE (allowed, depth 4)

Moves (SAN): `16. axb5 axb5 17. Qd3 Qb8 18. Rfc1 Qb6 19. Qxb5 Qxd4 20. Na4 Ne5 21. c3 Qc4`

FEN (line start): `2r2rk1/5ppp/p1nqpn2/1p1p4/P2P4/2N3NP/1PP2PP1/R2Q1RK1 w - - 0 16`

Game (full game at ply): http://localhost:5173/analysis?game_id=683643&ply=29

FEN (free-play from line start): http://localhost:5173/analysis?fen=2r2rk1/5ppp/p1nqpn2/1p1p4/P2P4/2N3NP/1PP2PP1/R2Q1RK1%20w%20-%20-%200%2016

#### Case 643 — DISCOVERED_ATTACK (missed, depth 7)

Moves (SAN): `15... Qb4 16. Nge2 Qxb2 17. Rb1 Qa3 18. Rxb7 Na5 19. Ra7 Rxc3 20. Nxc3 Qxc3 21. Qd3`

FEN (line start): `2r2rk1/1p3ppp/p1nqpn2/3p4/P2P4/2N3NP/1PP2PP1/R2Q1RK1 b - - 0 15`

Game (full game at ply): http://localhost:5173/analysis?game_id=683643&ply=29

FEN (free-play from line start): http://localhost:5173/analysis?fen=2r2rk1/1p3ppp/p1nqpn2/3p4/P2P4/2N3NP/1PP2PP1/R2Q1RK1%20b%20-%20-%200%2015

#### Case 644 — CLEARANCE (allowed, depth 4)

Moves (SAN): `13. Ke2 Qc7 14. c4 Bd6 15. Qb3 a5 16. Rad1 a4 17. Qd3 b5 18. c5 Be7`

FEN (line start): `r2qkb1r/pp3pp1/2p1pnp1/8/3P2P1/4BN1P/PPP2P2/R2QK2R w - - 0 13`

Game (full game at ply): http://localhost:5173/analysis?game_id=683652&ply=23

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qkb1r/pp3pp1/2p1pnp1/8/3P2P1/4BN1P/PPP2P2/R2QK2R%20w%20-%20-%200%2013

#### Case 645 — CLEARANCE (allowed, depth 8)

Moves (SAN): `15. Qe2 b5 16. a3 Be7 17. Ne5 Qd5 18. Kb1 Ne4 19. Bc1 Nd6 20. f3 Rd8`

FEN (line start): `r2qk2r/1p3pp1/2p1pnp1/p7/1b1P2P1/4BN1P/PPPQ1P2/2KR3R w - - 1 15`

Game (full game at ply): http://localhost:5173/analysis?game_id=683652&ply=27

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qk2r/1p3pp1/2p1pnp1/p7/1b1P2P1/4BN1P/PPPQ1P2/2KR3R%20w%20-%20-%201%2015

#### Case 646 — FORK (missed, depth 4)

Moves (SAN): `20... Qb5 21. Rdg1 Qd5 22. Rxg4 Qxf3 23. Rgh4 Rac8 24. R4h3 Qd5 25. a4 Qf5 26. Qe3`

FEN (line start): `r4rk1/1p3p2/1qpbp1pB/p7/3P2n1/2P2N2/PP1Q1P2/2KR3R b - - 0 20`

Game (full game at ply): http://localhost:5173/analysis?game_id=683652&ply=39

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4rk1/1p3p2/1qpbp1pB/p7/3P2n1/2P2N2/PP1Q1P2/2KR3R%20b%20-%20-%200%2020

#### Case 647 — PIN (missed, depth 2)

Moves (SAN): `15... dxe3 16. Bxe3 Neg4 17. fxg4 Rxe3+ 18. Kf1 Qxg4 19. Nc4 Bxg3 20. hxg3 Rxg3 21. Re1`

FEN (line start): `2r1r1k1/p2q1ppp/1p1b1n2/2p1n3/3p4/PPP1PPN1/2QN1BPP/R3K2R b - - 0 15`

Game (full game at ply): http://localhost:5173/analysis?game_id=683660&ply=29

FEN (free-play from line start): http://localhost:5173/analysis?fen=2r1r1k1/p2q1ppp/1p1b1n2/2p1n3/3p4/PPP1PPN1/2QN1BPP/R3K2R%20b%20-%20-%200%2015

#### Case 648 — FORK (missed, depth 2)

Moves (SAN): `19... Nce2 20. Nxe2 d3 21. Qd2 Nxe2 22. Qxd3 Nxg1 23. Nc3 Rcd8 24. Nd5 Nxf3+ 25. gxf3`

FEN (line start): `2r1r1k1/p2q1ppp/1p1b4/2p5/2PpPn2/PPn2PN1/2Q2BPP/RN2K1R1 b - - 0 19`

Game (full game at ply): http://localhost:5173/analysis?game_id=683660&ply=37

FEN (free-play from line start): http://localhost:5173/analysis?fen=2r1r1k1/p2q1ppp/1p1b4/2p5/2PpPn2/PPn2PN1/2Q2BPP/RN2K1R1%20b%20-%20-%200%2019

#### Case 649 — SACRIFICE (missed, depth 4)

Moves (SAN): `46... a6 47. Qxb6 Bg7 48. Qxc5 Kg8 49. Qc8+ Kh7 50. Qd7 Kh8 51. Qe8+ Kh7 52. Qf7`

FEN (line start): `8/p4k2/1p4p1/2pN4/P1PbKPP1/1Q6/8/8 b - - 0 46`

Game (full game at ply): http://localhost:5173/analysis?game_id=683660&ply=91

FEN (free-play from line start): http://localhost:5173/analysis?fen=8/p4k2/1p4p1/2pN4/P1PbKPP1/1Q6/8/8%20b%20-%20-%200%2046

#### Case 650 — MATE (allowed, depth 10)

Moves (SAN): `48. Qb5 Bg7 49. axb6 Bf6 50. b7 Be7 51. b8=Q+ Ke6 52. Q5e8 g5 53. Qxe7#`

FEN (line start): `8/p7/1p1k2p1/P1pN4/2PbKPP1/1Q6/8/8 w - - 1 48`

Game (full game at ply): http://localhost:5173/analysis?game_id=683660&ply=93

FEN (free-play from line start): http://localhost:5173/analysis?fen=8/p7/1p1k2p1/P1pN4/2PbKPP1/1Q6/8/8%20w%20-%20-%201%2048

#### Case 651 — DISCOVERED_ATTACK (allowed, depth 1)

Moves (SAN): `4... dxe4 5. Nxe4 Qxd4 6. Nf3 Qd5 7. c4 Qd8 8. Nxf6+ exf6`

FEN (line start): `rnbqkb1r/pp2pppp/2p2n2/3p4/3PP3/2NB4/PPP2PPP/R1BQK1NR b - - 1 4`

Game (full game at ply): http://localhost:5173/analysis?game_id=683679&ply=6

FEN (free-play from line start): http://localhost:5173/analysis?fen=rnbqkb1r/pp2pppp/2p2n2/3p4/3PP3/2NB4/PPP2PPP/R1BQK1NR%20b%20-%20-%201%204

#### Case 652 — DEFLECTION (missed, depth 4)

Moves (SAN): `26. Qh5+ g6 27. Qh7+ Ke8 28. Bxg6+ Kd8 29. Qh5 Rf8 30. Be4 Bd7 31. Qe5 Qf6`

FEN (line start): `r1b5/4qkpQ/2p1pr2/1p6/3P4/p1P5/P1B2PPP/R3R1K1 w - - 0 26`

Game (full game at ply): http://localhost:5173/analysis?game_id=683690&ply=50

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1b5/4qkpQ/2p1pr2/1p6/3P4/p1P5/P1B2PPP/R3R1K1%20w%20-%20-%200%2026

#### Case 653 — MATE (allowed, depth 10)

Moves (SAN): `22... Nxd3 23. Rh3+ Rh4 24. Rxh4+ Qxh4+ 25. Kg2 Qg4+ 26. Kh1 Nf4 27. Kh2 Qg2#`

FEN (line start): `r7/pp4pk/8/3Pn3/5r2/2PQR3/P1P2q2/R6K b - - 0 22`

Game (full game at ply): http://localhost:5173/analysis?game_id=683721&ply=42

FEN (free-play from line start): http://localhost:5173/analysis?fen=r7/pp4pk/8/3Pn3/5r2/2PQR3/P1P2q2/R6K%20b%20-%20-%200%2022

#### Case 654 — CLEARANCE (missed, depth 2)

Moves (SAN): `22. Rh3+ Rh4 23. Qe3 Qxe3 24. Rxh4+ Kg8 25. Rf1 Nf3 26. Rh3 dxe4 27. Kg2 Qe2+`

FEN (line start): `r7/pp4pk/8/3pn3/4Pr2/2PQR3/P1P2q2/R6K w - - 0 22`

Game (full game at ply): http://localhost:5173/analysis?game_id=683721&ply=42

FEN (free-play from line start): http://localhost:5173/analysis?fen=r7/pp4pk/8/3pn3/4Pr2/2PQR3/P1P2q2/R6K%20w%20-%20-%200%2022

#### Case 655 — SACRIFICE (missed, depth 6)

Moves (SAN): `23. Rf1 Rh4+ 24. Rh3 Nxd3 25. Rxf2 Nxf2+ 26. Kg2 Nxh3 27. d6 Ng5 28. Kg3 Rh6`

FEN (line start): `r5k1/pp4p1/8/3Pn3/5r2/2PQR3/P1P2q2/R6K w - - 0 23`

Game (full game at ply): http://localhost:5173/analysis?game_id=683721&ply=44

FEN (free-play from line start): http://localhost:5173/analysis?fen=r5k1/pp4p1/8/3Pn3/5r2/2PQR3/P1P2q2/R6K%20w%20-%20-%200%2023

#### Case 656 — PIN (allowed, depth 8)

Moves (SAN): `2... exd4 3. Nf3 Bb4+ 4. c3 dxc3 5. Nxc3 Nf6 6. e5 Ne4 7. Qc2 d5 8. Bd3`

FEN (line start): `rnbqkbnr/pppp1ppp/8/4p3/3PP3/8/PPP2PPP/RNBQKBNR b - - 0 2`

Game (full game at ply): http://localhost:5173/analysis?game_id=683725&ply=2

FEN (free-play from line start): http://localhost:5173/analysis?fen=rnbqkbnr/pppp1ppp/8/4p3/3PP3/8/PPP2PPP/RNBQKBNR%20b%20-%20-%200%202

#### Case 657 — CLEARANCE (missed, depth 6)

Moves (SAN): `2. dxe5 Nc6 3. Nf3 h6 4. e4 d6 5. Bb5 Bd7 6. Bxc6 Bxc6 7. Nc3 dxe5`

FEN (line start): `rnbqkbnr/pppp1ppp/8/4p3/3P4/8/PPP1PPPP/RNBQKBNR w - - 0 2`

Game (full game at ply): http://localhost:5173/analysis?game_id=683725&ply=2

FEN (free-play from line start): http://localhost:5173/analysis?fen=rnbqkbnr/pppp1ppp/8/4p3/3P4/8/PPP1PPPP/RNBQKBNR%20w%20-%20-%200%202

#### Case 658 — SACRIFICE (allowed, depth 4)

Moves (SAN): `8... Nxe4 9. Bxe4 Bxc3+ 10. bxc3 d5`

FEN (line start): `r1bqr1k1/pppp1ppp/2n2n2/8/1b2P3/2NB2N1/PPP2PPP/R1BQK2R b - - 1 8`

Game (full game at ply): http://localhost:5173/analysis?game_id=683725&ply=14

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1bqr1k1/pppp1ppp/2n2n2/8/1b2P3/2NB2N1/PPP2PPP/R1BQK2R%20b%20-%20-%201%208

#### Case 659 — ATTRACTION (allowed, depth 4)

Moves (SAN): `16... Nf3+ 17. Kh1 Nh4 18. Qg5 Nxg2 19. Kxg2 Bf3+ 20. Kg1 Re5 21. Qh4 h5 22. Nh1`

FEN (line start): `3rr1k1/pppq1ppp/5n2/4n3/P3p1b1/BBP1Q1N1/2P2PPP/R4RK1 b - - 1 16`

Game (full game at ply): http://localhost:5173/analysis?game_id=683725&ply=30

FEN (free-play from line start): http://localhost:5173/analysis?fen=3rr1k1/pppq1ppp/5n2/4n3/P3p1b1/BBP1Q1N1/2P2PPP/R4RK1%20b%20-%20-%201%2016

#### Case 660 — SACRIFICE (allowed, depth 6)

Moves (SAN): `28. f3 Ne5 29. Qc7 Ng6 30. dxe6 Rxd1 31. exf7+ Kh7 32. Rxd1 Qf5 33. f8=N+ Qxf8`

FEN (line start): `3r2k1/p4pp1/1pQ1pq1p/3P4/2P3n1/1P6/P4PPP/3RR1K1 w - - 1 28`

Game (full game at ply): http://localhost:5173/analysis?game_id=683727&ply=53

FEN (free-play from line start): http://localhost:5173/analysis?fen=3r2k1/p4pp1/1pQ1pq1p/3P4/2P3n1/1P6/P4PPP/3RR1K1%20w%20-%20-%201%2028

#### Case 661 — HANGING_PIECE (allowed, depth 0)

Moves (SAN): `34. Kxe2 Qe4+ 35. Kf1 Qc2 36. Re1 exd5 37. Re2 Qb1+ 38. Re1 Qc2`

FEN (line start): `5rk1/p1Q2pp1/1p2p2p/3P4/2P4q/1P5P/P3nPP1/3R1K2 w - - 1 34`

Game (full game at ply): http://localhost:5173/analysis?game_id=683727&ply=65

FEN (free-play from line start): http://localhost:5173/analysis?fen=5rk1/p1Q2pp1/1p2p2p/3P4/2P4q/1P5P/P3nPP1/3R1K2%20w%20-%20-%201%2034

#### Case 662 — CLEARANCE (allowed, depth 10)

Moves (SAN): `28. R5xe4 dxe4 29. Bxe6+ Kh7 30. d5 h5 31. gxh5 Kh6 32. Kf2 Kxh5 33. Rg1 Kh4`

FEN (line start): `4rrk1/6p1/p3pp1p/1p1pRP2/3Pb1P1/1BP4P/PP6/4R1K1 w - - 0 28`

Game (full game at ply): http://localhost:5173/analysis?game_id=683737&ply=53

FEN (free-play from line start): http://localhost:5173/analysis?fen=4rrk1/6p1/p3pp1p/1p1pRP2/3Pb1P1/1BP4P/PP6/4R1K1%20w%20-%20-%200%2028

#### Case 663 — FORK (allowed, depth 2)

Moves (SAN): `7... d5 8. Bd3 dxe4 9. Nxe4 Nbd7`

FEN (line start): `rnb1kb1r/pp1p1ppp/1qp1pn2/8/2PPP3/P1N2N2/1P1B1PPP/R2QKB1R b - - 1 7`

Game (full game at ply): http://localhost:5173/analysis?game_id=683743&ply=12

FEN (free-play from line start): http://localhost:5173/analysis?fen=rnb1kb1r/pp1p1ppp/1qp1pn2/8/2PPP3/P1N2N2/1P1B1PPP/R2QKB1R%20b%20-%20-%201%207

#### Case 664 — SKEWER (missed, depth 8)

Moves (SAN): `14. g3 Qe7 15. Rae1 Rae8 16. Qg2 Qd7 17. a4 Ne7 18. Qxb7 Qxa4 19. Bd2 Nd5`

FEN (line start): `r4rk1/1pp2ppp/p1nbp3/8/3P3q/2PBBQ2/PP4PP/R4RK1 w - - 0 14`

Game (full game at ply): http://localhost:5173/analysis?game_id=683749&ply=26

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4rk1/1pp2ppp/p1nbp3/8/3P3q/2PBBQ2/PP4PP/R4RK1%20w%20-%20-%200%2014

#### Case 665 — DISCOVERED_ATTACK (missed, depth 5)

Moves (SAN): `33... Qh4+ 34. Kf1 Qxh2 35. b4 Rg5 36. Qf2 Qxd6 37. b5 Rh5 38. Kg1 Qh2+ 39. Kf1`

FEN (line start): `r5k1/5ppp/p2N1n2/R2pr3/2q5/2P2P2/1PQ2KPP/R7 b - - 0 33`

Game (full game at ply): http://localhost:5173/analysis?game_id=683755&ply=65

FEN (free-play from line start): http://localhost:5173/analysis?fen=r5k1/5ppp/p2N1n2/R2pr3/2q5/2P2P2/1PQ2KPP/R7%20b%20-%20-%200%2033

#### Case 666 — CLEARANCE (missed, depth 4)

Moves (SAN): `17... Bg6 18. e4 f6 19. Rd2 Bf7 20. Nf5 a5 21. Rhd1 Kf8 22. f4 Nc4 23. Rd7`

FEN (line start): `r3r1k1/1pp2ppp/p7/2P1nb2/8/P1B1P1N1/1P3PPP/2KR3R b - - 0 17`

Game (full game at ply): http://localhost:5173/analysis?game_id=683759&ply=33

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3r1k1/1pp2ppp/p7/2P1nb2/8/P1B1P1N1/1P3PPP/2KR3R%20b%20-%20-%200%2017

#### Case 667 — DISCOVERED_ATTACK (allowed, depth 7)

Moves (SAN): `14. Ne4 Qe6 15. Nxd6 Qxd6 16. Bg2 h6 17. Nh4 a5 18. Bxc6 Qxc6 19. Qe4 Ra6`

FEN (line start): `r1b1r1k1/5ppp/p1nb1q2/1p2p3/3p4/2NP1N1P/PPPB1P2/2KRQB1R w - - 0 14`

Game (full game at ply): http://localhost:5173/analysis?game_id=683766&ply=25

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1b1r1k1/5ppp/p1nb1q2/1p2p3/3p4/2NP1N1P/PPPB1P2/2KRQB1R%20w%20-%20-%200%2014

#### Case 668 — DISCOVERED_ATTACK (allowed, depth 7)

Moves (SAN): `16. Qe4 Qxe4 17. Nxe4 Be6 18. Bg2 f5 19. Nf6+ gxf6 20. Bxc6 Kf7 21. Bxa8 Rxa8`

FEN (line start): `r1br2k1/5ppp/p1nN4/1p2p3/3p4/3P1q1P/PPPB1P2/2KRQB1R w - - 1 16`

Game (full game at ply): http://localhost:5173/analysis?game_id=683766&ply=29

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1br2k1/5ppp/p1nN4/1p2p3/3p4/3P1q1P/PPPB1P2/2KRQB1R%20w%20-%20-%201%2016

#### Case 669 — SACRIFICE (allowed, depth 4)

Moves (SAN): `14. Ba4+ Ndc6 15. Nxd5 exd5 16. c4 Qa5 17. b3`

FEN (line start): `r2qkb1r/4nppp/p3p3/3pP3/1p1n4/1BN3Q1/PPP2PPP/R4RK1 w - - 0 14`

Game (full game at ply): http://localhost:5173/analysis?game_id=683767&ply=25

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qkb1r/4nppp/p3p3/3pP3/1p1n4/1BN3Q1/PPP2PPP/R4RK1%20w%20-%20-%200%2014

#### Case 670 — CLEARANCE (missed, depth 2)

Moves (SAN): `13... Nef5 14. Qh3 Bc5 15. Rad1 Qh4 16. Qxh4 Nxh4 17. Nxd5 exd5 18. Bxd5 Rd8 19. Bb7`

FEN (line start): `r2qkb1r/4nppp/p3p3/1p1pP3/3n4/1BN3Q1/PPP2PPP/R4RK1 b - - 0 13`

Game (full game at ply): http://localhost:5173/analysis?game_id=683767&ply=25

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qkb1r/4nppp/p3p3/1p1pP3/3n4/1BN3Q1/PPP2PPP/R4RK1%20b%20-%20-%200%2013

#### Case 671 — CLEARANCE (allowed, depth 6)

Moves (SAN): `30. Rxa5 Rd8 31. d5 Rc8 32. d6 Kf7 33. Re5 Rd8 34. Rxe4 Rxd6 35. a4 Rd1+`

FEN (line start): `4r1k1/6pp/8/pR6/3Pp3/P5P1/1P5P/6K1 w - - 1 30`

Game (full game at ply): http://localhost:5173/analysis?game_id=683768&ply=57

FEN (free-play from line start): http://localhost:5173/analysis?fen=4r1k1/6pp/8/pR6/3Pp3/P5P1/1P5P/6K1%20w%20-%20-%201%2030

#### Case 672 — SKEWER (missed, depth 4)

Moves (SAN): `30... Rb8 31. Kf2 Rxb2+ 32. Ke3 Rxh2 33. Rf5 g6 34. Rf1 Rg2 35. Kxe4 Rxg3 36. d5`

FEN (line start): `4r1k1/6pp/8/p3R3/3Pp3/P5P1/1P5P/6K1 b - - 0 30`

Game (full game at ply): http://localhost:5173/analysis?game_id=683768&ply=59

FEN (free-play from line start): http://localhost:5173/analysis?fen=4r1k1/6pp/8/p3R3/3Pp3/P5P1/1P5P/6K1%20b%20-%20-%200%2030

#### Case 673 — PROMOTION (allowed, depth 6)

Moves (SAN): `51... Rg3 52. Rg8+ Kf4 53. Rxg3 Kxg3 54. a6 g1=Q 55. Kc3 Kf4 56. Kc2 Ke4 57. Kb2`

FEN (line start): `3R4/8/8/Pp3pk1/1P6/4r3/3K2p1/8 b - - 1 51`

Game (full game at ply): http://localhost:5173/analysis?game_id=683776&ply=100

FEN (free-play from line start): http://localhost:5173/analysis?fen=3R4/8/8/Pp3pk1/1P6/4r3/3K2p1/8%20b%20-%20-%201%2051

#### Case 674 — CLEARANCE (missed, depth 6)

Moves (SAN): `20. Nc1 c5 21. Qc3 Qb6 22. Bc4 Kh8 23. Rhd1 Rab8 24. a4`

FEN (line start): `r4rk1/3R2pp/2p1Pp2/q5b1/3Q4/1P5P/PBP1N1P1/1K3B1R w - - 0 20`

Game (full game at ply): http://localhost:5173/analysis?game_id=683782&ply=38

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4rk1/3R2pp/2p1Pp2/q5b1/3Q4/1P5P/PBP1N1P1/1K3B1R%20w%20-%20-%200%2020

#### Case 675 — CLEARANCE (missed, depth 8)

Moves (SAN): `22... Qh6 23. R1f2 Nxb3 24. Qxb3 Rd7 25. Nb5 Ne7 26. Re5 Qb6 27. Qd3 Nc6 28. Re3`

FEN (line start): `5rk1/2N2ppp/2nr4/p2p1Rq1/3P4/PB1Q3P/1PPn2P1/5RK1 b - - 0 22`

Game (full game at ply): http://localhost:5173/analysis?game_id=683783&ply=43

FEN (free-play from line start): http://localhost:5173/analysis?fen=5rk1/2N2ppp/2nr4/p2p1Rq1/3P4/PB1Q3P/1PPn2P1/5RK1%20b%20-%20-%200%2022

#### Case 676 — CLEARANCE (missed, depth 10)

Moves (SAN): `25... Rxd4 26. Qg3+ Kh8 27. Rxf6 Nxf1 28. Rxf1 Rdd8 29. Bxf7 Rd7 30. Bh5 Rfd8 31. Qf4`

FEN (line start): `5rk1/5p1p/2nrBp2/p4R2/3P4/P2Q3P/1PPn2P1/5RK1 b - - 0 25`

Game (full game at ply): http://localhost:5173/analysis?game_id=683783&ply=49

FEN (free-play from line start): http://localhost:5173/analysis?fen=5rk1/5p1p/2nrBp2/p4R2/3P4/P2Q3P/1PPn2P1/5RK1%20b%20-%20-%200%2025

#### Case 677 — SACRIFICE (missed, depth 10)

Moves (SAN): `27... Kg7 28. Qg3+ Kxf6 29. Qxd6 Ne7 30. Qe5+ Kf7 31. Qf4+ Ke8 32. Qxd2 h5 33. Qh6`

FEN (line start): `6k1/7p/2nrpR2/p7/3P4/P2Q3P/1PPn2P1/6K1 b - - 0 27`

Game (full game at ply): http://localhost:5173/analysis?game_id=683783&ply=53

FEN (free-play from line start): http://localhost:5173/analysis?fen=6k1/7p/2nrpR2/p7/3P4/P2Q3P/1PPn2P1/6K1%20b%20-%20-%200%2027

#### Case 678 — MATE (allowed, depth 10)

Moves (SAN): `32... Qxe3 33. Kh2 Rd1 34. Qg5 Qxg5 35. g4 Qe3 36. Kg2 Rd2+ 37. Kf1 Qf2#`

FEN (line start): `8/pppr2k1/6p1/2q2p2/2P4Q/4R2P/6P1/7K b - - 1 32`

Game (full game at ply): http://localhost:5173/analysis?game_id=683787&ply=62

FEN (free-play from line start): http://localhost:5173/analysis?fen=8/pppr2k1/6p1/2q2p2/2P4Q/4R2P/6P1/7K%20b%20-%20-%201%2032

#### Case 679 — CLEARANCE (allowed, depth 4)

Moves (SAN): `14. a4 Qb8 15. Bc5 Ng6 16. Qe3 h6 17. b4 Nf8 18. Nd4 Qb7 19. Nb3 Nd7`

FEN (line start): `r3k2r/p3nppp/b1p1p3/1q1pP3/8/1P2BN2/P1PQ1PPP/R3K2R w - - 1 14`

Game (full game at ply): http://localhost:5173/analysis?game_id=683792&ply=25

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3k2r/p3nppp/b1p1p3/1q1pP3/8/1P2BN2/P1PQ1PPP/R3K2R%20w%20-%20-%201%2014

#### Case 680 — DEFLECTION (missed, depth 4)

Moves (SAN): `23... d4 24. Bxd4 Rxd4 25. Qxd4 Qxg2 26. c4 Qxh1+ 27. Kf2 h5 28. Rb4 Qxh2+ 29. Ke3`

FEN (line start): `2rr2k1/p4ppp/b1q1p3/3pP3/P4P2/4B3/1RPQ2PP/4K2R b - - 0 23`

Game (full game at ply): http://localhost:5173/analysis?game_id=683792&ply=45

FEN (free-play from line start): http://localhost:5173/analysis?fen=2rr2k1/p4ppp/b1q1p3/3pP3/P4P2/4B3/1RPQ2PP/4K2R%20b%20-%20-%200%2023

#### Case 681 — PIN (missed, depth 6)

Moves (SAN): `24... d4 25. Kg3 dxe3 26. Qxe3 h6 27. h4 Qc3 28. Qxc3 Rxc3+ 29. Kh2 h5 30. Rhb1`

FEN (line start): `2rr2k1/p4ppp/b3p3/3pP3/P1q2P2/4B3/1RPQ1KPP/7R b - - 0 24`

Game (full game at ply): http://localhost:5173/analysis?game_id=683792&ply=47

FEN (free-play from line start): http://localhost:5173/analysis?fen=2rr2k1/p4ppp/b3p3/3pP3/P1q2P2/4B3/1RPQ1KPP/7R%20b%20-%20-%200%2024

#### Case 682 — CLEARANCE (missed, depth 2)

Moves (SAN): `20... Be7 21. b5 Rh8 22. a4 Rh2+ 23. Kd3 e5 24. Ba3 Bxa3 25. Rxg5 Bf8 26. Ne4`

FEN (line start): `2kr1b2/pp1n1pp1/2p1p3/6n1/1P1P4/P1N1P3/1BP1K3/6R1 b - - 0 20`

Game (full game at ply): http://localhost:5173/analysis?game_id=683794&ply=39

FEN (free-play from line start): http://localhost:5173/analysis?fen=2kr1b2/pp1n1pp1/2p1p3/6n1/1P1P4/P1N1P3/1BP1K3/6R1%20b%20-%20-%200%2020

#### Case 683 — CLEARANCE (missed, depth 10)

Moves (SAN): `14... g6 15. Bg5 Be7 16. h4 Rc8 17. Nd4 Re8 18. f4 Ne4 19. Qe3 Bf6 20. h5`

FEN (line start): `r2q1rk1/pp3ppp/4pn2/1Nbp4/5B2/5P1P/PPPQ1P2/2KR2R1 b - - 0 14`

Game (full game at ply): http://localhost:5173/analysis?game_id=683798&ply=27

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2q1rk1/pp3ppp/4pn2/1Nbp4/5B2/5P1P/PPPQ1P2/2KR2R1%20b%20-%20-%200%2014

#### Case 684 — PIN (allowed, depth 0)

Moves (SAN): `21. Qxh5 e5 22. Be3 d4 23. Ne4 Bg7 24. Bh6 Qc7 25. Rd2 Qa5 26. Bxg7 Qxa2`

FEN (line start): `2rqr1k1/1p3p1p/p3pbpQ/3p3n/3B4/2N2P1P/PPP2P2/2KR2R1 w - - 1 21`

Game (full game at ply): http://localhost:5173/analysis?game_id=683798&ply=39

FEN (free-play from line start): http://localhost:5173/analysis?fen=2rqr1k1/1p3p1p/p3pbpQ/3p3n/3B4/2N2P1P/PPP2P2/2KR2R1%20w%20-%20-%201%2021

#### Case 685 — SACRIFICE (missed, depth 2)

Moves (SAN): `17... Ngf6 18. Nxh8 Rxh8 19. g5 Nd5 20. Qxe6 N7b6 21. Qd6+ Nc7 22. Rhd1 a5 23. Bf1`

FEN (line start): `1k1r2nr/pp1n1Np1/2p1p1p1/8/6P1/2P4P/qP1RQPB1/2K4R b - - 0 17`

Game (full game at ply): http://localhost:5173/analysis?game_id=683806&ply=33

FEN (free-play from line start): http://localhost:5173/analysis?fen=1k1r2nr/pp1n1Np1/2p1p1p1/8/6P1/2P4P/qP1RQPB1/2K4R%20b%20-%20-%200%2017

#### Case 686 — CLEARANCE (missed, depth 2)

Moves (SAN): `16. Re1 h6 17. Rad1 Qc7 18. Bd2 Bxd3 19. cxd3 Qd6 20. exd5 cxd5 21. Rc1 Qb6`

FEN (line start): `r2qr1k1/5ppp/b1p2n2/3pp3/pB2P3/P2B1Q1P/1PP2PP1/R2R2K1 w - - 0 16`

Game (full game at ply): http://localhost:5173/analysis?game_id=683819&ply=30

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qr1k1/5ppp/b1p2n2/3pp3/pB2P3/P2B1Q1P/1PP2PP1/R2R2K1%20w%20-%20-%200%2016

#### Case 687 — PIN (missed, depth 0)

Moves (SAN): `14. Nxe5 Ne7 15. Nxc6 Nxc6 16. Rc1 Rb8 17. Rxc6 bxc6 18. Ba5 Qd6 19. Nc7+ Kd7`

FEN (line start): `r2qkbnr/1p3ppp/p1n3b1/3Np3/Q3P3/5N1P/PP1BBPP1/R3K2R w - - 0 14`

Game (full game at ply): http://localhost:5173/analysis?game_id=683857&ply=26

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qkbnr/1p3ppp/p1n3b1/3Np3/Q3P3/5N1P/PP1BBPP1/R3K2R%20w%20-%20-%200%2014

#### Case 688 — CLEARANCE (missed, depth 4)

Moves (SAN): `12... Ne7 13. Qe2 Nf5 14. Nd2 Be7 15. Rab1 c5 16. c4`

FEN (line start): `r2qkbnr/5ppp/p1p1p3/3pP3/8/2P1BQ1P/P4PP1/RN3RK1 b - - 0 12`

Game (full game at ply): http://localhost:5173/analysis?game_id=683887&ply=23

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qkbnr/5ppp/p1p1p3/3pP3/8/2P1BQ1P/P4PP1/RN3RK1%20b%20-%20-%200%2012

#### Case 689 — INTERFERENCE (allowed, depth 2)

Moves (SAN): `14. Qc6+ Ke7 15. Qxc5+ Kd7 16. Qxd4+ Ke8 17. Qe4 Bb4 18. c5 Rb8 19. Qc6+ Kf8`

FEN (line start): `r2qkbnr/5ppp/p3p3/2p1P3/2Pp4/4BQ1P/P4PP1/RN3RK1 w - - 0 14`

Game (full game at ply): http://localhost:5173/analysis?game_id=683887&ply=25

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qkbnr/5ppp/p3p3/2p1P3/2Pp4/4BQ1P/P4PP1/RN3RK1%20w%20-%20-%200%2014

#### Case 690 — CLEARANCE (missed, depth 6)

Moves (SAN): `15... Ra7 16. Nd2 Ne7 17. Rab1 Nf5 18. Qa3 Be7 19. Qa4+ Kf8 20. Ne4 h5 21. Rd3`

FEN (line start): `r3kbnr/2q2ppp/p3p3/2p1P3/2Pp1B2/5Q1P/P4PP1/RN1R2K1 b - - 0 15`

Game (full game at ply): http://localhost:5173/analysis?game_id=683887&ply=29

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3kbnr/2q2ppp/p3p3/2p1P3/2Pp1B2/5Q1P/P4PP1/RN1R2K1%20b%20-%20-%200%2015

#### Case 691 — SACRIFICE (missed, depth 4)

Moves (SAN): `30... Qe8 31. Bxh6 Qf7 32. Rxf7 Rxf7 33. Rb8+ Kh7 34. Bd2 Rf6 35. Qh4+ Kg6`

FEN (line start): `2q2rk1/1R4p1/4p2p/6B1/2Pp4/6QP/P4PP1/1R4K1 b - - 0 30`

Game (full game at ply): http://localhost:5173/analysis?game_id=683887&ply=59

FEN (free-play from line start): http://localhost:5173/analysis?fen=2q2rk1/1R4p1/4p2p/6B1/2Pp4/6QP/P4PP1/1R4K1%20b%20-%20-%200%2030

#### Case 692 — CLEARANCE (allowed, depth 4)

Moves (SAN): `10... Bh7 11. Bc4 e6 12. g3 Be7 13. Ng2 Nd7 14. Bd2`

FEN (line start): `rn1qkb1r/1p2ppp1/p6p/5b2/3Pp2N/3BP3/PP3PPP/R1BQ1RK1 b - - 1 10`

Game (full game at ply): http://localhost:5173/analysis?game_id=683889&ply=18

FEN (free-play from line start): http://localhost:5173/analysis?fen=rn1qkb1r/1p2ppp1/p6p/5b2/3Pp2N/3BP3/PP3PPP/R1BQ1RK1%20b%20-%20-%201%2010

#### Case 693 — TRAPPED_PIECE (missed, depth 4)

Moves (SAN): `12. Bxe7 Nxd2 13. Bh4 Nf3+ 14. gxf3 Be6 15. Kd2 f6 16. Rhg1 Kf7 17. Rae1 Bd5`

FEN (line start): `rnb1k2r/pp2qppp/2p5/6B1/3Pn3/3B4/PP1Q1PPP/R3K2R w - - 0 12`

Game (full game at ply): http://localhost:5173/analysis?game_id=683901&ply=22

FEN (free-play from line start): http://localhost:5173/analysis?fen=rnb1k2r/pp2qppp/2p5/6B1/3Pn3/3B4/PP1Q1PPP/R3K2R%20w%20-%20-%200%2012

#### Case 694 — CLEARANCE (allowed, depth 6)

Moves (SAN): `18... Ra7 19. Ng3 Qd7 20. Ne4 Qd8 21. Qf4 Rd7 22. b4 a5 23. bxa5 bxa5 24. Nxc5`

FEN (line start): `rnb2r2/6kp/pp1p1pp1/2pP1q2/2P5/5N2/PP1QNPPP/R3R1K1 b - - 1 18`

Game (full game at ply): http://localhost:5173/analysis?game_id=683908&ply=34

FEN (free-play from line start): http://localhost:5173/analysis?fen=rnb2r2/6kp/pp1p1pp1/2pP1q2/2P5/5N2/PP1QNPPP/R3R1K1%20b%20-%20-%201%2018

#### Case 695 — TRAPPED_PIECE (allowed, depth 2)

Moves (SAN): `18. a3 a4 19. axb4 axb3 20. f5 h6 21. Bd2 Qb5 22. Qe3 Qb6 23. Kh1 h5`

FEN (line start): `2r1k2r/4nppp/1qp1p3/p2pP3/1b1P1PP1/1N1QB3/PP5P/R4RK1 w - - 1 18`

Game (full game at ply): http://localhost:5173/analysis?game_id=683939&ply=33

FEN (free-play from line start): http://localhost:5173/analysis?fen=2r1k2r/4nppp/1qp1p3/p2pP3/1b1P1PP1/1N1QB3/PP5P/R4RK1%20w%20-%20-%201%2018

#### Case 696 — SACRIFICE (missed, depth 10)

Moves (SAN): `29... Rf8 30. Rf7 Rxf7 31. exf7+ Kh8 32. Qe3 Bf8 33. h5 Qd7 34. hxg6 Qxg4+ 35. Kf2`

FEN (line start): `4r1k1/1q4pp/4P1n1/3p2N1/pb1B2PP/3Q4/PP6/5RK1 b - - 0 29`

Game (full game at ply): http://localhost:5173/analysis?game_id=683939&ply=57

FEN (free-play from line start): http://localhost:5173/analysis?fen=4r1k1/1q4pp/4P1n1/3p2N1/pb1B2PP/3Q4/PP6/5RK1%20b%20-%20-%200%2029

#### Case 697 — SACRIFICE (missed, depth 2)

Moves (SAN): `30... Bxg5 31. Rxb7 Bf6 32. Bxf6 gxf6 33. Qf5 Re7 34. Rxe7 Nxe7 35. Qxf6 Ng6 36. Qf7+`

FEN (line start): `4r1k1/1q2bRpp/4P1n1/3p2N1/p2B2PP/3Q4/PP6/6K1 b - - 0 30`

Game (full game at ply): http://localhost:5173/analysis?game_id=683939&ply=59

FEN (free-play from line start): http://localhost:5173/analysis?fen=4r1k1/1q2bRpp/4P1n1/3p2N1/p2B2PP/3Q4/PP6/6K1%20b%20-%20-%200%2030

#### Case 698 — MATE (allowed, depth 6)

Moves (SAN): `32. Rxg7+ Kh8 33. Rxg6+ Qe5 34. Bxe5+ Bf6 35. Bxf6#`

FEN (line start): `1q2r1k1/5Rpp/4P1n1/3p2bP/p2B2P1/3Q4/PP6/6K1 w - - 0 32`

Game (full game at ply): http://localhost:5173/analysis?game_id=683939&ply=61

FEN (free-play from line start): http://localhost:5173/analysis?fen=1q2r1k1/5Rpp/4P1n1/3p2bP/p2B2P1/3Q4/PP6/6K1%20w%20-%20-%200%2032

#### Case 699 — SACRIFICE (missed, depth 2)

Moves (SAN): `31... Bf6 32. hxg6 h6 33. Rxf6 gxf6 34. Nh7 Rxe6 35. Nxf6+ Rxf6 36. Bxf6 Qd6 37. Qc3`

FEN (line start): `1q2r1k1/4bRpp/4P1n1/3p2NP/p2B2P1/3Q4/PP6/6K1 b - - 0 31`

Game (full game at ply): http://localhost:5173/analysis?game_id=683939&ply=61

FEN (free-play from line start): http://localhost:5173/analysis?fen=1q2r1k1/4bRpp/4P1n1/3p2NP/p2B2P1/3Q4/PP6/6K1%20b%20-%20-%200%2031

#### Case 700 — SACRIFICE (missed, depth 4)

Moves (SAN): `36... Nc6 37. Qc5 d3 38. Qxc6 Rh7 39. Qb6+ Rc7 40. Bd1 Kc8`

FEN (line start): `3k4/3r4/8/p3QP2/Pn1pP3/1B4N1/1P3P2/1K6 b - - 0 36`

Game (full game at ply): http://localhost:5173/analysis?game_id=683941&ply=71

FEN (free-play from line start): http://localhost:5173/analysis?fen=3k4/3r4/8/p3QP2/Pn1pP3/1B4N1/1P3P2/1K6%20b%20-%20-%200%2036

#### Case 701 — PIN (allowed, depth 10)

Moves (SAN): `14... Qg6 15. Rc1 Nd7 16. Rc3 Nxe5 17. Qc2`

FEN (line start): `1n2k2r/1b3ppp/5q2/1p2P3/1bp5/4P3/1P1N1PPP/R2QKB1R b - - 0 14`

Game (full game at ply): http://localhost:5173/analysis?game_id=683945&ply=26

FEN (free-play from line start): http://localhost:5173/analysis?fen=1n2k2r/1b3ppp/5q2/1p2P3/1bp5/4P3/1P1N1PPP/R2QKB1R%20b%20-%20-%200%2014

#### Case 702 — CLEARANCE (allowed, depth 8)

Moves (SAN): `19... cxd3 20. Qxe3+ Bxe3 21. Ra3 Bb6 22. Rxd3 Ke7 23. Ke2 Rd8 24. Rxd8 Bxd8 25. g4`

FEN (line start): `1n2k2r/R4ppp/8/1p6/2p5/3BqP2/1P1bQ1PP/5K1R b - - 1 19`

Game (full game at ply): http://localhost:5173/analysis?game_id=683945&ply=36

FEN (free-play from line start): http://localhost:5173/analysis?fen=1n2k2r/R4ppp/8/1p6/2p5/3BqP2/1P1bQ1PP/5K1R%20b%20-%20-%201%2019

#### Case 703 — PIN (missed, depth 0)

Moves (SAN): `19. Kd1`

FEN (line start): `1n2k2r/R4ppp/8/1p6/2p5/3BqP2/1P1bQ1PP/4K2R w - - 0 19`

Game (full game at ply): http://localhost:5173/analysis?game_id=683945&ply=36

FEN (free-play from line start): http://localhost:5173/analysis?fen=1n2k2r/R4ppp/8/1p6/2p5/3BqP2/1P1bQ1PP/4K2R%20w%20-%20-%200%2019

#### Case 704 — FORK (missed, depth 4)

Moves (SAN): `26. Rxc3 g5 27. Ke2 Bxc3 28. Rxd8+ Kg7 29. Rxb8 Be5 30. Rb7 Bxh2 31. Bc4 Kf6`

FEN (line start): `1n1r2k1/2R2ppp/8/1B6/8/2p2P2/3b1KPP/3R4 w - - 0 26`

Game (full game at ply): http://localhost:5173/analysis?game_id=683945&ply=50

FEN (free-play from line start): http://localhost:5173/analysis?fen=1n1r2k1/2R2ppp/8/1B6/8/2p2P2/3b1KPP/3R4%20w%20-%20-%200%2026

#### Case 705 — CLEARANCE (allowed, depth 8)

Moves (SAN): `12. Nd3 Bd6 13. g3 b5 14. a3 Nd7`

FEN (line start): `r1b2rk1/1pq2ppp/4pn2/p2p4/1N1P1b2/2P5/PP1NBPPP/R2QK2R w - - 0 12`

Game (full game at ply): http://localhost:5173/analysis?game_id=683948&ply=21

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1b2rk1/1pq2ppp/4pn2/p2p4/1N1P1b2/2P5/PP1NBPPP/R2QK2R%20w%20-%20-%200%2012

#### Case 706 — CAPTURING_DEFENDER (allowed, depth 4)

Moves (SAN): `7. axb5 cxb5 8. Nxb5 Bb7 9. Bxc4 a5 10. Bd2 Be7 11. Nc3`

FEN (line start): `rnbqkb1r/p4ppp/2p1pn2/1p6/P1pP4/2N1PN2/1P3PPP/R1BQKB1R w - - 0 7`

Game (full game at ply): http://localhost:5173/analysis?game_id=683949&ply=11

FEN (free-play from line start): http://localhost:5173/analysis?fen=rnbqkb1r/p4ppp/2p1pn2/1p6/P1pP4/2N1PN2/1P3PPP/R1BQKB1R%20w%20-%20-%200%207

#### Case 707 — DISCOVERED_ATTACK (missed, depth 1)

Moves (SAN): `15... Ne5 16. Nxe5 Rxc4 17. Nxc4 Bc6 18. Nd6 Re7 19. Bc5 Qa8 20. e4 h5 21. c4`

FEN (line start): `2rqr1k1/p2b1ppp/2n1pn2/8/2QP4/B1PBPN2/5PPP/RR4K1 b - - 0 15`

Game (full game at ply): http://localhost:5173/analysis?game_id=683949&ply=29

FEN (free-play from line start): http://localhost:5173/analysis?fen=2rqr1k1/p2b1ppp/2n1pn2/8/2QP4/B1PBPN2/5PPP/RR4K1%20b%20-%20-%200%2015

#### Case 708 — CAPTURING_DEFENDER (allowed, depth 4)

Moves (SAN): `19. Qxb8 Qxb8 20. Rxb8 Rxb8 21. Nxe5 Nc8 22. Ra1 g6 23. c4 Bf5 24. Bxf5 gxf5`

FEN (line start): `1r1qr1k1/R3nppp/4bn2/2B1p3/1Q1P4/2PBPN2/5PPP/1R4K1 w - - 1 19`

Game (full game at ply): http://localhost:5173/analysis?game_id=683949&ply=35

FEN (free-play from line start): http://localhost:5173/analysis?fen=1r1qr1k1/R3nppp/4bn2/2B1p3/1Q1P4/2PBPN2/5PPP/1R4K1%20w%20-%20-%201%2019

#### Case 709 — FORK (missed, depth 0)

Moves (SAN): `20... e4 21. Bb5 Bd5 22. Qa6 exf3 23. Bxe8 Nxe8 24. e4 Bxe4 25. Re1 Nd5 26. Rxe4`

FEN (line start): `3qr1k1/1Q2nppp/4bn2/2B1p3/3P4/2PBPN2/5PPP/1R4K1 b - - 0 20`

Game (full game at ply): http://localhost:5173/analysis?game_id=683949&ply=39

FEN (free-play from line start): http://localhost:5173/analysis?fen=3qr1k1/1Q2nppp/4bn2/2B1p3/3P4/2PBPN2/5PPP/1R4K1%20b%20-%20-%200%2020

#### Case 710 — CLEARANCE (missed, depth 4)

Moves (SAN): `9... Bxf3 10. Qxf3 e6 11. Ne2 Bd6 12. c3`

FEN (line start): `rn1qkb1r/4pppp/p4n2/1p1p4/3P2b1/1BN2N1P/PPP2PP1/R1BQK2R b - - 0 9`

Game (full game at ply): http://localhost:5173/analysis?game_id=683960&ply=17

FEN (free-play from line start): http://localhost:5173/analysis?fen=rn1qkb1r/4pppp/p4n2/1p1p4/3P2b1/1BN2N1P/PPP2PP1/R1BQK2R%20b%20-%20-%200%209

#### Case 711 — FORK (missed, depth 4)

Moves (SAN): `23... Qxh3+ 24. Kg1 Bxg3 25. fxg3 Qxg3+ 26. Bg2 Nc6 27. Qd2 Ne5 28. Qf2 Qg4 29. Rd5`

FEN (line start): `1n2r1k1/5ppp/p2b4/Qp6/2P5/1P3BPP/P4P1q/3R1K2 b - - 0 23`

Game (full game at ply): http://localhost:5173/analysis?game_id=683960&ply=45

FEN (free-play from line start): http://localhost:5173/analysis?fen=1n2r1k1/5ppp/p2b4/Qp6/2P5/1P3BPP/P4P1q/3R1K2%20b%20-%20-%200%2023

#### Case 712 — CAPTURING_DEFENDER (allowed, depth 4)

Moves (SAN): `18. Be3 Bg7 19. Bxd4 Qd8 20. Qxf3 Qg8 21. Qf7 Qxf7 22. Nxf7 Nf5 23. Nd6 Nxd4`

FEN (line start): `r1b2b1N/pp1kn2R/1q2p3/3pP3/1P1n4/P4p2/5P2/R1BQKB2 w - - 0 18`

Game (full game at ply): http://localhost:5173/analysis?game_id=683963&ply=33

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1b2b1N/pp1kn2R/1q2p3/3pP3/1P1n4/P4p2/5P2/R1BQKB2%20w%20-%20-%200%2018

#### Case 713 — SACRIFICE (missed, depth 10)

Moves (SAN): `17... Kc7 18. Be3 a6 19. Bd3 Kb8 20. Qxf3 Nf5 21. Bxf5 exf5 22. Qxd5 f4 23. Bxf4`

FEN (line start): `r1b2b1N/pp1kn2R/1qn1p3/3pP3/1P1P4/P4p2/5P2/R1BQKB2 b - - 0 17`

Game (full game at ply): http://localhost:5173/analysis?game_id=683963&ply=33

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1b2b1N/pp1kn2R/1qn1p3/3pP3/1P1P4/P4p2/5P2/R1BQKB2%20b%20-%20-%200%2017

#### Case 714 — SACRIFICE (missed, depth 6)

Moves (SAN): `20... Qc6 21. Qxc6+ bxc6 22. Ng6 Kd8 23. Nxf8 Nd5 24. Kd2 a5 25. b5 cxb5 26. Ng6`

FEN (line start): `r1b2b1N/pp1kn2R/1q2p3/4P3/1P1B4/P4p2/2Q2P2/R3KB2 b - - 0 20`

Game (full game at ply): http://localhost:5173/analysis?game_id=683963&ply=39

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1b2b1N/pp1kn2R/1q2p3/4P3/1P1B4/P4p2/2Q2P2/R3KB2%20b%20-%20-%200%2020

#### Case 715 — SACRIFICE (allowed, depth 2)

Moves (SAN): `10. Nxe5 Bxe5 11. Qh5 g6 12. Qxe5 f6 13. Qe3 Kf7 14. Ne2 Qxe3 15. Bxe3 g5`

FEN (line start): `r3k1nr/pp2qppp/2bb4/3pp3/8/2NP1N2/PPP2PPP/R1BQR1K1 w - - 1 10`

Game (full game at ply): http://localhost:5173/analysis?game_id=683964&ply=17

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3k1nr/pp2qppp/2bb4/3pp3/8/2NP1N2/PPP2PPP/R1BQR1K1%20w%20-%20-%201%2010

#### Case 716 — CLEARANCE (allowed, depth 10)

Moves (SAN): `16. Nxd5 Nxd5 17. Qxd5 Rad8 18. Qf5 g6 19. Qb5 g5 20. Be3 f5 21. Rad1 Kh7`

FEN (line start): `r4rk1/pp2qpp1/3b1n1p/3b4/4p3/2N4N/PPP3PP/R1BQR1K1 w - - 0 16`

Game (full game at ply): http://localhost:5173/analysis?game_id=683964&ply=29

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4rk1/pp2qpp1/3b1n1p/3b4/4p3/2N4N/PPP3PP/R1BQR1K1%20w%20-%20-%200%2016

#### Case 717 — DISCOVERED_ATTACK (allowed, depth 1)

Moves (SAN): `15... Nf5 16. Nxe6 Qxh4 17. Nxf8 Nxd4 18. Kf1 Kxf8 19. Qb4+ Qe7 20. Qd2 Qh4`

FEN (line start): `rn1q1rk1/pp2np2/2p1p2p/3pP1N1/2PP3B/P1Q5/1P3PPP/R3K2R b - - 0 15`

Game (full game at ply): http://localhost:5173/analysis?game_id=683970&ply=28

FEN (free-play from line start): http://localhost:5173/analysis?fen=rn1q1rk1/pp2np2/2p1p2p/3pP1N1/2PP3B/P1Q5/1P3PPP/R3K2R%20b%20-%20-%200%2015

#### Case 718 — UNDER_PROMOTION (missed, depth 8)

Moves (SAN): `28... Qc4 29. d5 Qd4+ 30. Kg3 Qxe5+ 31. Qxe5+ Nxe5 32. Rhh1 cxb1=R 33. Rxb1 Rb8 34. dxc6`

FEN (line start): `6r1/p2nk1pR/q1p5/4PQN1/Pb1P4/8/1pp2K2/1R6 b - - 0 28`

Game (full game at ply): http://localhost:5173/analysis?game_id=683971&ply=55

FEN (free-play from line start): http://localhost:5173/analysis?fen=6r1/p2nk1pR/q1p5/4PQN1/Pb1P4/8/1pp2K2/1R6%20b%20-%20-%200%2028

#### Case 719 — SACRIFICE (missed, depth 2)

Moves (SAN): `14. Nxd4 Nxd4 15. Nb4 Nf3+ 16. Qxf3 Qa4 17. Qd3 Be6 18. Nd5 Ng4 19. f4 Bxd5`

FEN (line start): `r1b2rk1/pp3ppp/2np3n/8/2BpP3/1R1N1N2/q1P2PPP/3Q1RK1 w - - 0 14`

Game (full game at ply): http://localhost:5173/analysis?game_id=683974&ply=26

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1b2rk1/pp3ppp/2np3n/8/2BpP3/1R1N1N2/q1P2PPP/3Q1RK1%20w%20-%20-%200%2014

#### Case 720 — TRAPPED_PIECE (allowed, depth 4)

Moves (SAN): `15... Bxd5 16. exd5 Ne7 17. Nxb6+ axb6 18. Rxa1 Nxd5 19. Rd1 Ke6 20. Rc1 Ra8 21. a3`

FEN (line start): `N5nr/pb1k2pp/1p3p2/3Bp3/4P3/4PN2/PP2K1PP/n6R b - - 1 15`

Game (full game at ply): http://localhost:5173/analysis?game_id=683994&ply=28

FEN (free-play from line start): http://localhost:5173/analysis?fen=N5nr/pb1k2pp/1p3p2/3Bp3/4P3/4PN2/PP2K1PP/n6R%20b%20-%20-%201%2015

#### Case 721 — FORK (missed, depth 0)

Moves (SAN): `15. Rd1+ Ke7 16. Nc7 Nh6 17. Rxa1 Bxe4 18. Nd5+ Bxd5 19. Bxd5 Rc8 20. Rd1 Nf5`

FEN (line start): `N5nr/pb1k2pp/1p3p2/4p3/2B1P3/4PN2/PP2K1PP/n6R w - - 0 15`

Game (full game at ply): http://localhost:5173/analysis?game_id=683994&ply=28

FEN (free-play from line start): http://localhost:5173/analysis?fen=N5nr/pb1k2pp/1p3p2/4p3/2B1P3/4PN2/PP2K1PP/n6R%20w%20-%20-%200%2015

#### Case 722 — INTERFERENCE (allowed, depth 10)

Moves (SAN): `19... Rc8 20. a3 g5 21. Nf5+ Nxf5 22. exf5 Rd8 23. g4 Nd4+ 24. exd4 Rxd5 25. Ke3`

FEN (line start): `7r/p3k1pp/1p3p1n/3Bp3/4P2N/4P3/PPn1K1PP/3R4 b - - 1 19`

Game (full game at ply): http://localhost:5173/analysis?game_id=683994&ply=36

FEN (free-play from line start): http://localhost:5173/analysis?fen=7r/p3k1pp/1p3p1n/3Bp3/4P2N/4P3/PPn1K1PP/3R4%20b%20-%20-%201%2019

#### Case 723 — CLEARANCE (missed, depth 4)

Moves (SAN): `9. Bb1 c6 10. a3 Na6 11. Ba2`

FEN (line start): `r1bqk2r/ppp1ppbp/1n4p1/3P4/1n2P3/2NB1N2/PP3PPP/R1BQK2R w - - 0 9`

Game (full game at ply): http://localhost:5173/analysis?game_id=683995&ply=16

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1bqk2r/ppp1ppbp/1n4p1/3P4/1n2P3/2NB1N2/PP3PPP/R1BQK2R%20w%20-%20-%200%209

#### Case 724 — CLEARANCE (missed, depth 8)

Moves (SAN): `26. Rad1 Qf7 27. Qd3 Rce4 28. Kh1 Qc4 29. Qxc4 Rxc4 30. Rd7+ Kg8 31. Rd2 g5`

FEN (line start): `4r3/p2q2kp/2p2pp1/1p6/2r5/P3QN1N/1P3PPP/R4RK1 w - - 0 26`

Game (full game at ply): http://localhost:5173/analysis?game_id=683995&ply=50

FEN (free-play from line start): http://localhost:5173/analysis?fen=4r3/p2q2kp/2p2pp1/1p6/2r5/P3QN1N/1P3PPP/R4RK1%20w%20-%20-%200%2026

#### Case 725 — HANGING_PIECE (allowed, depth 0)

Moves (SAN): `11... Kxf7`

FEN (line start): `rn1qk2r/1b3Npp/p2bpn2/2p3B1/8/2NB4/PPP2PPP/R2Q1RK1 b - - 0 11`

Game (full game at ply): http://localhost:5173/analysis?game_id=683996&ply=20

FEN (free-play from line start): http://localhost:5173/analysis?fen=rn1qk2r/1b3Npp/p2bpn2/2p3B1/8/2NB4/PPP2PPP/R2Q1RK1%20b%20-%20-%200%2011

#### Case 726 — CLEARANCE (allowed, depth 2)

Moves (SAN): `20... Kg7 21. Qa4 Qf8 22. h4 Ra7 23. Rd2 Rf7 24. Red1 e5 25. h5 e4 26. Rd5`

FEN (line start): `rn2r3/7p/p3pkp1/2p2q2/7Q/8/PPP2PPP/3RR1K1 b - - 1 20`

Game (full game at ply): http://localhost:5173/analysis?game_id=683996&ply=38

FEN (free-play from line start): http://localhost:5173/analysis?fen=rn2r3/7p/p3pkp1/2p2q2/7Q/8/PPP2PPP/3RR1K1%20b%20-%20-%201%2020

#### Case 727 — CLEARANCE (allowed, depth 10)

Moves (SAN): `21... Nc6 22. h4 g4 23. Rd7 Rad8 24. Rc7 Ne5 25. Qxc5 Rd7 26. b4 Red8 27. Rxd7`

FEN (line start): `rn2r3/7p/p3pk2/2p2qp1/2Q5/8/PPP2PPP/3RR1K1 b - - 1 21`

Game (full game at ply): http://localhost:5173/analysis?game_id=683996&ply=40

FEN (free-play from line start): http://localhost:5173/analysis?fen=rn2r3/7p/p3pk2/2p2qp1/2Q5/8/PPP2PPP/3RR1K1%20b%20-%20-%201%2021

#### Case 728 — PIN (missed, depth 4)

Moves (SAN): `21. Qa4 Ke7 22. Qb3 Ra7 23. Rd5 Qf6 24. Rxg5 Rd7 25. Rxc5 Kf8 26. Rc3 Rf7`

FEN (line start): `rn2r3/7p/p3pk2/2p2qp1/7Q/8/PPP2PPP/3RR1K1 w - - 0 21`

Game (full game at ply): http://localhost:5173/analysis?game_id=683996&ply=40

FEN (free-play from line start): http://localhost:5173/analysis?fen=rn2r3/7p/p3pk2/2p2qp1/7Q/8/PPP2PPP/3RR1K1%20w%20-%20-%200%2021

#### Case 729 — PIN (allowed, depth 0)

Moves (SAN): `13. Bb5 Rc8 14. Rfc1`

FEN (line start): `r2qk2r/p3bppp/1pn1p3/3pPn2/3P4/1Q2BN2/PP2BPPP/R4RK1 w - - 1 13`

Game (full game at ply): http://localhost:5173/analysis?game_id=683999&ply=23

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qk2r/p3bppp/1pn1p3/3pPn2/3P4/1Q2BN2/PP2BPPP/R4RK1%20w%20-%20-%201%2013

#### Case 730 — CLEARANCE (missed, depth 8)

Moves (SAN): `12... a6 13. Qc3 Na5 14. Bd2 Ne7 15. b3 Nec6 16. a3 Be7 17. Ra2 b5 18. Qd3`

FEN (line start): `r2qkb1r/p4ppp/1pn1p3/3pPn2/3P4/1Q2BN2/PP2BPPP/R4RK1 b - - 0 12`

Game (full game at ply): http://localhost:5173/analysis?game_id=683999&ply=23

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qkb1r/p4ppp/1pn1p3/3pPn2/3P4/1Q2BN2/PP2BPPP/R4RK1%20b%20-%20-%200%2012

#### Case 731 — CLEARANCE (missed, depth 8)

Moves (SAN): `21... Qb8 22. Qa3 a5 23. Qd3 Nxe3 24. Qxe3 Rc7 25. Rc2 Qc8 26. Qc1 g6 27. h3`

FEN (line start): `2rb2k1/5ppp/pqB1p3/1pQpPn2/3P4/4BN2/PP3PPP/2R3K1 b - - 0 21`

Game (full game at ply): http://localhost:5173/analysis?game_id=683999&ply=41

FEN (free-play from line start): http://localhost:5173/analysis?fen=2rb2k1/5ppp/pqB1p3/1pQpPn2/3P4/4BN2/PP3PPP/2R3K1%20b%20-%20-%200%2021

#### Case 732 — PIN (allowed, depth 8)

Moves (SAN): `12. Bxf6 gxf6 13. Qh5 Rh7 14. d5 Rg7 15. dxc6 e6 16. Bxe6 Nxc6 17. Bd5 Rc8`

FEN (line start): `rn1qkb1r/p3ppp1/2p2n1p/6B1/NpBP4/5Q2/PP3PPP/R4RK1 w - - 0 12`

Game (full game at ply): http://localhost:5173/analysis?game_id=684003&ply=21

FEN (free-play from line start): http://localhost:5173/analysis?fen=rn1qkb1r/p3ppp1/2p2n1p/6B1/NpBP4/5Q2/PP3PPP/R4RK1%20w%20-%20-%200%2012

#### Case 733 — CLEARANCE (allowed, depth 10)

Moves (SAN): `16. Bxd5 Qc7 17. Bxa8 Bd6 18. g3 Nd7 19. Qc6 Ne5 20. Qxc7 Bxc7 21. Bh1 Ba5`

FEN (line start): `rn1q1rk1/p3bpp1/5p1p/3p4/NpB5/5Q2/PP3PPP/3RR1K1 w - - 0 16`

Game (full game at ply): http://localhost:5173/analysis?game_id=684003&ply=29

FEN (free-play from line start): http://localhost:5173/analysis?fen=rn1q1rk1/p3bpp1/5p1p/3p4/NpB5/5Q2/PP3PPP/3RR1K1%20w%20-%20-%200%2016

#### Case 734 — FORK (missed, depth 6)

Moves (SAN): `6. Nb5 Qa5+ 7. b4 Qxb4+ 8. Bd2 cxd4 9. Nc7+ Kd8 10. Nxa8 dxc4 11. Rb1 Qd6`

FEN (line start): `r1bqkb1r/pp1n1ppp/4pn2/2pp4/2PP1B2/2N2N2/PP2PPPP/R2QKB1R w - - 0 6`

Game (full game at ply): http://localhost:5173/analysis?game_id=684007&ply=10

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1bqkb1r/pp1n1ppp/4pn2/2pp4/2PP1B2/2N2N2/PP2PPPP/R2QKB1R%20w%20-%20-%200%206

#### Case 735 — CLEARANCE (missed, depth 4)

Moves (SAN): `7. Bd2 N5f6 8. g3 b6 9. Bg2 Bb7 10. Bf4 Be7`

FEN (line start): `r1bqkb1r/pp1n1ppp/4p3/2pn4/3P1B2/2N2N2/PP2PPPP/R2QKB1R w - - 0 7`

Game (full game at ply): http://localhost:5173/analysis?game_id=684007&ply=12

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1bqkb1r/pp1n1ppp/4p3/2pn4/3P1B2/2N2N2/PP2PPPP/R2QKB1R%20w%20-%20-%200%207

#### Case 736 — DISCOVERED_ATTACK (missed, depth 7)

Moves (SAN): `12. Qg4 Kf8`

FEN (line start): `rn2k2r/pb1qbppp/2p1p3/4P3/p2PQ3/2P2N2/1P2BPPP/R1B1K2R w - - 0 12`

Game (full game at ply): http://localhost:5173/analysis?game_id=684008&ply=22

FEN (free-play from line start): http://localhost:5173/analysis?fen=rn2k2r/pb1qbppp/2p1p3/4P3/p2PQ3/2P2N2/1P2BPPP/R1B1K2R%20w%20-%20-%200%2012

#### Case 737 — PIN (missed, depth 0)

Moves (SAN): `15... Nxh3+ 16. Kf1 Qf6 17. gxh3 Qxh4 18. Qg4 Qf6 19. Re3 Re6 20. h4 Qg6 21. Qxg6`

FEN (line start): `r3r1k1/p1p2ppp/2pb2q1/3pp3/P4n1N/1P1P3P/1BP2PP1/R2QR1K1 b - - 0 15`

Game (full game at ply): http://localhost:5173/analysis?game_id=684013&ply=29

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3r1k1/p1p2ppp/2pb2q1/3pp3/P4n1N/1P1P3P/1BP2PP1/R2QR1K1%20b%20-%20-%200%2015

#### Case 738 — CLEARANCE (allowed, depth 4)

Moves (SAN): `25. Kxg4 Rxf2 26. Raf1 Rxc2 27. Ba1 Rg2+ 28. Kf3 Rg3+ 29. Ke2 c5 30. Rf3 Rg2+`

FEN (line start): `6k1/p1p2ppp/2pb4/3p2P1/P5rP/1P5K/1BP1rP2/R6R w - - 1 25`

Game (full game at ply): http://localhost:5173/analysis?game_id=684013&ply=47

FEN (free-play from line start): http://localhost:5173/analysis?fen=6k1/p1p2ppp/2pb4/3p2P1/P5rP/1P5K/1BP1rP2/R6R%20w%20-%20-%201%2025

#### Case 739 — MATE (allowed, depth 10)

Moves (SAN): `24. b4 c5 25. Be5+ Kc6 26. Qc7+ Kb5 27. Qa5+ Kc6 28. b5+ Kd7 29. Qc7#`

FEN (line start): `r3q2r/p5Q1/2pkpB1R/3p4/3p1P2/2P5/PP4P1/nN1K4 w - - 1 24`

Game (full game at ply): http://localhost:5173/analysis?game_id=684018&ply=45

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3q2r/p5Q1/2pkpB1R/3p4/3p1P2/2P5/PP4P1/nN1K4%20w%20-%20-%201%2024

#### Case 740 — SKEWER (missed, depth 10)

Moves (SAN): `33... c5 34. Qa6+ Qb5 35. Qxb5+ Kxb5 36. g4 Rg8 37. g5 Rh2+ 38. Kc3 Rxa2 39. Kd3`

FEN (line start): `r3q3/pQ6/2p1p3/3pB3/2k2P2/8/P2K2P1/n6r b - - 0 33`

Game (full game at ply): http://localhost:5173/analysis?game_id=684018&ply=65

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3q3/pQ6/2p1p3/3pB3/2k2P2/8/P2K2P1/n6r%20b%20-%20-%200%2033

#### Case 741 — CLEARANCE (allowed, depth 6)

Moves (SAN): `7. Nxf3 g6 8. d3 Bg7 9. g3`

FEN (line start): `r2qkb1r/ppp1pppp/2n2n2/5b2/8/2N2p2/PPPPQ1PP/R1B1KBNR w - - 0 7`

Game (full game at ply): http://localhost:5173/analysis?game_id=684031&ply=11

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qkb1r/ppp1pppp/2n2n2/5b2/8/2N2p2/PPPPQ1PP/R1B1KBNR%20w%20-%20-%200%207

#### Case 742 — CLEARANCE (missed, depth 8)

Moves (SAN): `6... Nd4 7. Qd1 exf3 8. d3 f2+ 9. Kxf2 e5 10. Ke1 Bc5 11. Nge2`

FEN (line start): `r2qkb1r/ppp1pppp/2n2n2/5b2/4p3/2N2P2/PPPPQ1PP/R1B1KBNR b - - 0 6`

Game (full game at ply): http://localhost:5173/analysis?game_id=684031&ply=11

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qkb1r/ppp1pppp/2n2n2/5b2/4p3/2N2P2/PPPPQ1PP/R1B1KBNR%20b%20-%20-%200%206

#### Case 743 — PIN (allowed, depth 10)

Moves (SAN): `16. dxe5 Qxd1+ 17. Rxd1 Nxe5 18. Na5 Rd8 19. Bb5+ Bd7 20. Bxd7+ Rxd7 21. Re1 Rd5`

FEN (line start): `r3k2r/pp1n1ppp/5n2/4pb2/3P4/BN6/P1q1BPPP/R2Q1K1R w - - 0 16`

Game (full game at ply): http://localhost:5173/analysis?game_id=684046&ply=29

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3k2r/pp1n1ppp/5n2/4pb2/3P4/BN6/P1q1BPPP/R2Q1K1R%20w%20-%20-%200%2016

#### Case 744 — SKEWER (missed, depth 2)

Moves (SAN): `10... dxc4 11. Bxc4 Qxb2 12. Ra2 Qb6 13. Nbd2 Nd5 14. Bxd5 exd5 15. Nb3 Be7 16. Bg5`

FEN (line start): `r4rk1/pp3ppp/1qn1pn2/1Bbp1b2/2P2B2/P3PN1P/1P3PP1/RN1Q1RK1 b - - 0 10`

Game (full game at ply): http://localhost:5173/analysis?game_id=684050&ply=19

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4rk1/pp3ppp/1qn1pn2/1Bbp1b2/2P2B2/P3PN1P/1P3PP1/RN1Q1RK1%20b%20-%20-%200%2010

#### Case 745 — FORK (allowed, depth 2)

Moves (SAN): `12. Nc3 Qxb2 13. Na4 Qb5 14. dxc6 Rad8 15. Qc1 Qxa4 16. Qxc5 Ne4 17. Qb4 Qxc6`

FEN (line start): `r4rk1/1p3ppp/p1n1pn2/1qbP1b2/5B2/P3PN1P/1P3PP1/RN1Q1RK1 w - - 0 12`

Game (full game at ply): http://localhost:5173/analysis?game_id=684050&ply=21

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4rk1/1p3ppp/p1n1pn2/1qbP1b2/5B2/P3PN1P/1P3PP1/RN1Q1RK1%20w%20-%20-%200%2012

#### Case 746 — SACRIFICE (missed, depth 4)

Moves (SAN): `11... Nxd5 12. Bxc6 Nxf4 13. exf4 Rfd8 14. Qc1 Rac8 15. b4 Bd6 16. Qe3 Rxc6 17. Ra2`

FEN (line start): `r4rk1/1p3ppp/pqn1pn2/1BbP1b2/5B2/P3PN1P/1P3PP1/RN1Q1RK1 b - - 0 11`

Game (full game at ply): http://localhost:5173/analysis?game_id=684050&ply=21

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4rk1/1p3ppp/pqn1pn2/1BbP1b2/5B2/P3PN1P/1P3PP1/RN1Q1RK1%20b%20-%20-%200%2011

#### Case 747 — DISCOVERED_ATTACK (allowed, depth 1)

Moves (SAN): `18... Nxg3 19. hxg3 Rxe3 20. fxe3 Re8 21. Rxf3 g6 22. Rdf1 Qc7 23. b4 h5 24. c3`

FEN (line start): `r3r1k1/pp3ppp/1qp5/3p4/3Nn3/1P2QpPB/2P2P1P/3R1RK1 b - - 1 18`

Game (full game at ply): http://localhost:5173/analysis?game_id=684058&ply=34

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3r1k1/pp3ppp/1qp5/3p4/3Nn3/1P2QpPB/2P2P1P/3R1RK1%20b%20-%20-%201%2018

#### Case 748 — PIN (missed, depth 8)

Moves (SAN): `22. Qg3 Re4 23. Bf5 Ree8 24. Bd7 Re4 25. Nf5 g6 26. Qg5 Qe2 27. Nh6+ Kg7`

FEN (line start): `r5k1/pp3ppp/q1p5/3pr3/3N4/1P3Q1B/2P2PKP/3R4 w - - 0 22`

Game (full game at ply): http://localhost:5173/analysis?game_id=684058&ply=42

FEN (free-play from line start): http://localhost:5173/analysis?fen=r5k1/pp3ppp/q1p5/3pr3/3N4/1P3Q1B/2P2PKP/3R4%20w%20-%20-%200%2022

#### Case 749 — CLEARANCE (allowed, depth 6)

Moves (SAN): `24... Rxf1 25. Qc3 Rxg1+ 26. Kxg1 c5 27. Qxc5 Qg6+ 28. Kf1 Qh5 29. f3 Qxh2 30. Qb5`

FEN (line start): `4r1k1/pp3ppp/q1p5/3p4/3N4/1P3Q2/2P2P1P/4rBRK b - - 1 24`

Game (full game at ply): http://localhost:5173/analysis?game_id=684058&ply=46

FEN (free-play from line start): http://localhost:5173/analysis?fen=4r1k1/pp3ppp/q1p5/3p4/3N4/1P3Q2/2P2P1P/4rBRK%20b%20-%20-%201%2024

#### Case 750 — SACRIFICE (missed, depth 8)

Moves (SAN): `24. Qc3 Rxg1+ 25. Kxg1 g6 26. Bd7 Re4 27. Nf5 gxf5 28. Bxf5 Qe2 29. Qg3+ Kf8`

FEN (line start): `4r1k1/pp3ppp/q1p5/3p4/3N4/1P3Q1B/2P2P1P/4r1RK w - - 0 24`

Game (full game at ply): http://localhost:5173/analysis?game_id=684058&ply=46

FEN (free-play from line start): http://localhost:5173/analysis?fen=4r1k1/pp3ppp/q1p5/3p4/3N4/1P3Q1B/2P2P1P/4r1RK%20w%20-%20-%200%2024

#### Case 751 — INTERMEZZO (allowed, depth 2)

Moves (SAN): `14... Bxf1 15. Kxf1 Nxf6 16. Qxd8 Raxd8 17. Bxf6 gxf6 18. Ke2 c5 19. Nh4 Rd5 20. g4`

FEN (line start): `r2qr1k1/p1pn1ppp/1p3P2/8/2b5/PPB1PN2/5PPP/R2Q1RK1 b - - 0 14`

Game (full game at ply): http://localhost:5173/analysis?game_id=684061&ply=26

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qr1k1/p1pn1ppp/1p3P2/8/2b5/PPB1PN2/5PPP/R2Q1RK1%20b%20-%20-%200%2014

#### Case 752 — HANGING_PIECE (missed, depth 0)

Moves (SAN): `14. bxc4 Ng4 15. e6 Rxe6 16. Nd4 Rg6 17. Nf5 Nh6 18. Ng3 Qe8 19. Qf3 Re6`

FEN (line start): `r2qr1k1/p1pn1ppp/1p3n2/4P3/2b5/PPB1PN2/5PPP/R2Q1RK1 w - - 0 14`

Game (full game at ply): http://localhost:5173/analysis?game_id=684061&ply=26

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qr1k1/p1pn1ppp/1p3n2/4P3/2b5/PPB1PN2/5PPP/R2Q1RK1%20w%20-%20-%200%2014

#### Case 753 — CLEARANCE (missed, depth 2)

Moves (SAN): `8. e5 Ne8 9. Be4 dxe5 10. dxe5 Nc7 11. Nb5 Nba6 12. Bxa8 Nxa8 13. Qxd8 Rxd8`

FEN (line start): `rnbq1rk1/p3ppbp/1p1p1np1/2p5/2PPP3/2NB1N2/PP3PPP/R1BQ1RK1 w - - 0 8`

Game (full game at ply): http://localhost:5173/analysis?game_id=684074&ply=14

FEN (free-play from line start): http://localhost:5173/analysis?fen=rnbq1rk1/p3ppbp/1p1p1np1/2p5/2PPP3/2NB1N2/PP3PPP/R1BQ1RK1%20w%20-%20-%200%208

#### Case 754 — FORK (missed, depth 0)

Moves (SAN): `26... Qxc3 27. Rc1 Bf6 28. Rf1 Qe5 29. Qxe5 Bxe5 30. Re1 Bb2 31. Rxe6 d4 32. Bf5`

FEN (line start): `6rk/p3b1qp/4p1n1/3p3Q/2p3R1/2P3PP/P1B3P1/4R1K1 b - - 0 26`

Game (full game at ply): http://localhost:5173/analysis?game_id=684077&ply=51

FEN (free-play from line start): http://localhost:5173/analysis?fen=6rk/p3b1qp/4p1n1/3p3Q/2p3R1/2P3PP/P1B3P1/4R1K1%20b%20-%20-%200%2026

#### Case 755 — PIN (missed, depth 0)

Moves (SAN): `18. Rad1 Kh8 19. Ne3 Be7 20. Bc2 b5 21. a3 Bc6 22. Ncd5 Nh5 23. Qg4 Qd8`

FEN (line start): `r2b1rk1/1b1q1p1p/pp1p1np1/2p1pN2/2P1P3/2NB2QP/PP3PP1/R4RK1 w - - 0 18`

Game (full game at ply): http://localhost:5173/analysis?game_id=684078&ply=34

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2b1rk1/1b1q1p1p/pp1p1np1/2p1pN2/2P1P3/2NB2QP/PP3PP1/R4RK1%20w%20-%20-%200%2018

#### Case 756 — SKEWER (missed, depth 6)

Moves (SAN): `13. Nxg6 fxg6 14. Qd3`

FEN (line start): `r2qk2r/ppp2pp1/2n1pbbp/4N3/3P2P1/2N4P/PPPQ4/2KR1B1R w - - 0 13`

Game (full game at ply): http://localhost:5173/analysis?game_id=684091&ply=24

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qk2r/ppp2pp1/2n1pbbp/4N3/3P2P1/2N4P/PPPQ4/2KR1B1R%20w%20-%20-%200%2013

#### Case 757 — FORK (missed, depth 0)

Moves (SAN): `29. Nf4 Rdd2 30. Nxe2 Rxe2 31. bxa5 Kd7 32. a4 Re3 33. Kb4 Rxh3 34. c4 Kc6`

FEN (line start): `2k5/1pp3p1/6Np/p2r4/1P4P1/1KP4P/P3r3/8 w - - 0 29`

Game (full game at ply): http://localhost:5173/analysis?game_id=684091&ply=56

FEN (free-play from line start): http://localhost:5173/analysis?fen=2k5/1pp3p1/6Np/p2r4/1P4P1/1KP4P/P3r3/8%20w%20-%20-%200%2029

#### Case 758 — DISCOVERED_ATTACK (allowed, depth 7)

Moves (SAN): `8. dxe5 Nxe5 9. Bxd5 Qd7`

FEN (line start): `r2qkbnr/pp3ppp/2n5/3pp3/3P4/2P2B2/PP3PPP/RNBQK2R w - - 0 8`

Game (full game at ply): http://localhost:5173/analysis?game_id=684095&ply=13

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qkbnr/pp3ppp/2n5/3pp3/3P4/2P2B2/PP3PPP/RNBQK2R%20w%20-%20-%200%208

#### Case 759 — CLEARANCE (allowed, depth 10)

Moves (SAN): `29. a4 Rb8 30. Bc1 Rd4 31. Kf1 Rdd8 32. a5 Rb3 33. Rd1 Ra8 34. Be3 Ra6`

FEN (line start): `r5k1/5pp1/7p/3r4/8/3n2P1/PB1R1P1P/R5K1 w - - 1 29`

Game (full game at ply): http://localhost:5173/analysis?game_id=684095&ply=55

FEN (free-play from line start): http://localhost:5173/analysis?fen=r5k1/5pp1/7p/3r4/8/3n2P1/PB1R1P1P/R5K1%20w%20-%20-%201%2029

#### Case 760 — PROMOTION (allowed, depth 8)

Moves (SAN): `59. h5 Ke5 60. h6 Ke6 61. Kg6 Ke5 62. h7 Ke4 63. h8=Q f4 64. Qa8+ Ke3`

FEN (line start): `8/8/8/5pK1/4k2P/6P1/8/8 w - - 1 59`

Game (full game at ply): http://localhost:5173/analysis?game_id=684095&ply=115

FEN (free-play from line start): http://localhost:5173/analysis?fen=8/8/8/5pK1/4k2P/6P1/8/8%20w%20-%20-%201%2059

#### Case 761 — MATE (allowed, depth 8)

Moves (SAN): `26... Nh4 27. f3 Qe3+ 28. Kh1 Qe2 29. Rg1 Qxf3+ 30. Rg2 Qxg2#`

FEN (line start): `4r3/Q1R1ppk1/1P4p1/3P4/P3q3/6Pp/5PnP/5RK1 b - - 0 26`

Game (full game at ply): http://localhost:5173/analysis?game_id=684097&ply=50

FEN (free-play from line start): http://localhost:5173/analysis?fen=4r3/Q1R1ppk1/1P4p1/3P4/P3q3/6Pp/5PnP/5RK1%20b%20-%20-%200%2026

#### Case 762 — PIN (allowed, depth 8)

Moves (SAN): `28... Rxe7 29. Qa6 Qd2 30. Rf2 Qd1+ 31. Rf1 Nxf1 32. Qxf1 Re1 33. Kf2 Qd2+ 34. Qe2`

FEN (line start): `4r3/Q3Rpk1/1P4p1/3q4/P7/4nPPp/7P/5RK1 b - - 0 28`

Game (full game at ply): http://localhost:5173/analysis?game_id=684097&ply=54

FEN (free-play from line start): http://localhost:5173/analysis?fen=4r3/Q3Rpk1/1P4p1/3q4/P7/4nPPp/7P/5RK1%20b%20-%20-%200%2028

#### Case 763 — INTERMEZZO (allowed, depth 4)

Moves (SAN): `13. dxc5 Bxc5 14. Nd2 Rb8 15. Bxc5 Qxc5 16. Qg4 Ne7 17. Qxg7 Ng6 18. b3 Qf8`

FEN (line start): `r3kbnr/5ppp/pq2p3/2ppP3/3P4/4BQ1P/PP3PP1/RN3RK1 w - - 1 13`

Game (full game at ply): http://localhost:5173/analysis?game_id=684101&ply=23

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3kbnr/5ppp/pq2p3/2ppP3/3P4/4BQ1P/PP3PP1/RN3RK1%20w%20-%20-%201%2013

#### Case 764 — DISCOVERED_ATTACK (allowed, depth 3)

Moves (SAN): `22. Kh2 Rc4 23. Ne4 dxe4 24. Rxc4 Nf3+ 25. gxf3 Qxc4 26. Qxe4 Qxa2 27. Kg2 Qb2`

FEN (line start): `5rk1/5ppp/p3p3/2qpP3/1r1n4/2N1Q2P/P4PP1/2RR2K1 w - - 1 22`

Game (full game at ply): http://localhost:5173/analysis?game_id=684101&ply=41

FEN (free-play from line start): http://localhost:5173/analysis?fen=5rk1/5ppp/p3p3/2qpP3/1r1n4/2N1Q2P/P4PP1/2RR2K1%20w%20-%20-%201%2022

#### Case 765 — DEFLECTION (missed, depth 10)

Moves (SAN): `28. e4 Ng6 29. exd5 Rxe1+ 30. Rxe1 Nxf4 31. Re8+ Kd7 32. Re7+ Kc8 33. dxc6 Bxc6`

FEN (line start): `2k1rn2/pb6/2p2B2/3p4/2n2P2/4P2P/P5P1/2R1R1K1 w - - 0 28`

Game (full game at ply): http://localhost:5173/analysis?game_id=684102&ply=54

FEN (free-play from line start): http://localhost:5173/analysis?fen=2k1rn2/pb6/2p2B2/3p4/2n2P2/4P2P/P5P1/2R1R1K1%20w%20-%20-%200%2028

#### Case 766 — CLEARANCE (missed, depth 10)

Moves (SAN): `15. Bxc6+ bxc6 16. Qxd4 Qxd4 17. Bxd4 Ke7 18. Bc5+ Ke6 19. Ke2 a5 20. Rhe1 axb4`

FEN (line start): `r2qk2r/1pp2ppp/p1n5/4P3/1P1b4/P4B2/1B3PPP/R2QK2R w - - 0 15`

Game (full game at ply): http://localhost:5173/analysis?game_id=684109&ply=28

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qk2r/1pp2ppp/p1n5/4P3/1P1b4/P4B2/1B3PPP/R2QK2R%20w%20-%20-%200%2015

#### Case 767 — PIN (missed, depth 8)

Moves (SAN): `16. Bxb7 Ra7 17. Be4 c5 18. Qa4+ Rd7 19. bxc5 Qh4 20. Bc6 Ke7 21. Rd1 Rhd8`

FEN (line start): `r2qk2r/1pp2ppp/p7/4P3/1P1n4/P4B2/5PPP/R2QK2R w - - 0 16`

Game (full game at ply): http://localhost:5173/analysis?game_id=684109&ply=30

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qk2r/1pp2ppp/p7/4P3/1P1n4/P4B2/5PPP/R2QK2R%20w%20-%20-%200%2016

#### Case 768 — DISCOVERED_CHECK (allowed, depth 0)

Moves (SAN): `36... e3+ 37. Kh2 exf2 38. Qxh5+ Kg8 39. Qe2 Qc1 40. Qxf2 Qxa3 41. b5 Kh8 42. Qe2`

FEN (line start): `8/6pk/2q5/6Qp/1P2p2P/P5P1/5PK1/8 b - - 1 36`

Game (full game at ply): http://localhost:5173/analysis?game_id=684109&ply=70

FEN (free-play from line start): http://localhost:5173/analysis?fen=8/6pk/2q5/6Qp/1P2p2P/P5P1/5PK1/8%20b%20-%20-%201%2036

#### Case 769 — FORK (missed, depth 2)

Moves (SAN): `28... Rge3 29. Na5 Re1+ 30. Qxe1 Rxe1+ 31. Rf1 Rxf1+ 32. Kxf1 cxd5 33. Kg1 Kf8 34. Nxb7`

FEN (line start): `4r1k1/pp3pp1/2p3qp/2PP4/1P6/PN4r1/5RB1/3Q2K1 b - - 0 28`

Game (full game at ply): http://localhost:5173/analysis?game_id=684111&ply=55

FEN (free-play from line start): http://localhost:5173/analysis?fen=4r1k1/pp3pp1/2p3qp/2PP4/1P6/PN4r1/5RB1/3Q2K1%20b%20-%20-%200%2028

#### Case 770 — PIN (missed, depth 0)

Moves (SAN): `31... Rxa3 32. Qe1 Ra2 33. Kh2 Qh5+ 34. Kg1`

FEN (line start): `6k1/pp3pp1/2pP2qp/2Pr4/1P6/P5r1/3N1RB1/5QK1 b - - 0 31`

Game (full game at ply): http://localhost:5173/analysis?game_id=684111&ply=61

FEN (free-play from line start): http://localhost:5173/analysis?fen=6k1/pp3pp1/2pP2qp/2Pr4/1P6/P5r1/3N1RB1/5QK1%20b%20-%20-%200%2031

#### Case 771 — DEFLECTION (allowed, depth 4)

Moves (SAN): `39. d8=Q+ Kh7 40. Bf5+ g6 41. Rxh6+ Kxh6 42. Qh8+ Kg5 43. Qxb2 Ra6 44. Bd3 b5`

FEN (line start): `6k1/pp1P1pp1/2p4p/2P5/1P5R/r6B/1r6/6K1 w - - 1 39`

Game (full game at ply): http://localhost:5173/analysis?game_id=684111&ply=75

FEN (free-play from line start): http://localhost:5173/analysis?fen=6k1/pp1P1pp1/2p4p/2P5/1P5R/r6B/1r6/6K1%20w%20-%20-%201%2039

#### Case 772 — DEFLECTION (missed, depth 4)

Moves (SAN): `38... Rd2 39. Re4 Ra1+ 40. Bf1 Rxd7 41. Kf2 Kf8 42. b5 Ra2+ 43. Kf3 Ra3+ 44. Kf4`

FEN (line start): `6k1/pp1P1pp1/2p4p/2P5/1P5R/r6B/5r2/6K1 b - - 0 38`

Game (full game at ply): http://localhost:5173/analysis?game_id=684111&ply=75

FEN (free-play from line start): http://localhost:5173/analysis?fen=6k1/pp1P1pp1/2p4p/2P5/1P5R/r6B/5r2/6K1%20b%20-%20-%200%2038

#### Case 773 — DEFLECTION (missed, depth 2)

Moves (SAN): `41... Rxh3 42. Rxh3 Rxb4 43. Re3 Rf4+ 44. Kg2 b6 45. Rf3 Rf6 46. Kf2 Rg6 47. Rxf7`

FEN (line start): `8/pp3ppk/2p4p/2P5/1P5R/6rB/1r6/3Q1K2 b - - 0 41`

Game (full game at ply): http://localhost:5173/analysis?game_id=684111&ply=81

FEN (free-play from line start): http://localhost:5173/analysis?fen=8/pp3ppk/2p4p/2P5/1P5R/6rB/1r6/3Q1K2%20b%20-%20-%200%2041

#### Case 774 — DISCOVERED_ATTACK (missed, depth 5)

Moves (SAN): `35... Ke8 36. f5 gxf5 37. Rh8+ Kd7 38. h4 Rxh8 39. Qxh8 Nxc4 40. Qb8 e5 41. Qxa7+`

FEN (line start): `r4k2/p4p2/1pqnpQp1/2p5/2P2P2/7R/PP4PP/6K1 b - - 0 35`

Game (full game at ply): http://localhost:5173/analysis?game_id=684126&ply=69

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4k2/p4p2/1pqnpQp1/2p5/2P2P2/7R/PP4PP/6K1%20b%20-%20-%200%2035

#### Case 775 — CLEARANCE (allowed, depth 6)

Moves (SAN): `12... Nxf6 13. Bf3 Bb7 14. Bb2 Qd7 15. Qe2 Rad8 16. Rad1 Qc8 17. g3 dxc4 18. Bxb7`

FEN (line start): `r1bq1rk1/p2nb1pp/1p2pP2/2pp4/2P2P2/1PN1P3/P3B1PP/R1BQ1RK1 b - - 0 12`

Game (full game at ply): http://localhost:5173/analysis?game_id=684145&ply=22

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1bq1rk1/p2nb1pp/1p2pP2/2pp4/2P2P2/1PN1P3/P3B1PP/R1BQ1RK1%20b%20-%20-%200%2012

#### Case 776 — SACRIFICE (allowed, depth 6)

Moves (SAN): `14... a6 15. Bf3 axb5 16. Bxa8 bxc4 17. exd4 Ba6 18. Bf3 c3 19. Bxc3 Bxf1 20. Qxf1`

FEN (line start): `r1bq1rk1/p2n2pp/1p2pb2/1Np5/2Pp1P2/1P2P3/PB2B1PP/R2Q1RK1 b - - 1 14`

Game (full game at ply): http://localhost:5173/analysis?game_id=684145&ply=26

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1bq1rk1/p2n2pp/1p2pb2/1Np5/2Pp1P2/1P2P3/PB2B1PP/R2Q1RK1%20b%20-%20-%201%2014

#### Case 777 — CLEARANCE (missed, depth 8)

Moves (SAN): `14. Ne4 Bb7 15. Nxf6+ Qxf6 16. exd4 Rad8 17. Bg4 Be4 18. Qe2 Bf5 19. Bxf5 Qxf5`

FEN (line start): `r1bq1rk1/p2n2pp/1p2pb2/2p5/2Pp1P2/1PN1P3/PB2B1PP/R2Q1RK1 w - - 0 14`

Game (full game at ply): http://localhost:5173/analysis?game_id=684145&ply=26

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1bq1rk1/p2n2pp/1p2pb2/2p5/2Pp1P2/1PN1P3/PB2B1PP/R2Q1RK1%20w%20-%20-%200%2014

#### Case 778 — CLEARANCE (allowed, depth 10)

Moves (SAN): `7... d5 8. Nd4 Qe7`

FEN (line start): `rnb1kb1r/pp1p1ppp/2p1qn2/8/2B1P3/1PN2N2/P1P2PPP/R1BQK2R b - - 1 7`

Game (full game at ply): http://localhost:5173/analysis?game_id=684158&ply=12

FEN (free-play from line start): http://localhost:5173/analysis?fen=rnb1kb1r/pp1p1ppp/2p1qn2/8/2B1P3/1PN2N2/P1P2PPP/R1BQK2R%20b%20-%20-%201%207

#### Case 779 — PIN (missed, depth 2)

Moves (SAN): `12. Bxc4 Bb7 13. Bxb5 Qxb5 14. Qxa4 Qxa4 15. Rxa4 Bc6 16. Ra3 Bd5`

FEN (line start): `rnb1k2r/p1pq1ppp/4p3/1p2P1B1/n1pP4/5N2/2Q2PPP/R3KB1R w - - 0 12`

Game (full game at ply): http://localhost:5173/analysis?game_id=684171&ply=22

FEN (free-play from line start): http://localhost:5173/analysis?fen=rnb1k2r/p1pq1ppp/4p3/1p2P1B1/n1pP4/5N2/2Q2PPP/R3KB1R%20w%20-%20-%200%2012

#### Case 780 — PROMOTION (allowed, depth 10)

Moves (SAN): `26... Bxf3 27. gxf3 a5 28. f4 a4 29. f5 a3 30. Kg2 a2 31. h4 a1=Q 32. f6`

FEN (line start): `6k1/p1p2pp1/2b1p2p/4P3/1r6/3B1NBP/5PPK/8 b - - 1 26`

Game (full game at ply): http://localhost:5173/analysis?game_id=684171&ply=50

FEN (free-play from line start): http://localhost:5173/analysis?fen=6k1/p1p2pp1/2b1p2p/4P3/1r6/3B1NBP/5PPK/8%20b%20-%20-%201%2026

#### Case 781 — PIN (allowed, depth 0)

Moves (SAN): `9... Qe7 10. f4 Ng4`

FEN (line start): `r1bqk2r/ppp2ppp/3p1n2/4P3/2PQ4/8/PP1N1PPP/R3KB1R b - - 0 9`

Game (full game at ply): http://localhost:5173/analysis?game_id=684175&ply=16

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1bqk2r/ppp2ppp/3p1n2/4P3/2PQ4/8/PP1N1PPP/R3KB1R%20b%20-%20-%200%209

#### Case 782 — CLEARANCE (missed, depth 4)

Moves (SAN): `12. Qc3 Re8`

FEN (line start): `r2q1rk1/ppp2ppp/4bn2/4Q3/2P5/8/PP1NBPPP/R3K2R w - - 0 12`

Game (full game at ply): http://localhost:5173/analysis?game_id=684175&ply=22

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2q1rk1/ppp2ppp/4bn2/4Q3/2P5/8/PP1NBPPP/R3K2R%20w%20-%20-%200%2012

#### Case 783 — HANGING_PIECE (allowed, depth 0)

Moves (SAN): `13... Qxd2 14. Rad1 Qb4 15. a3 Qe7 16. Bd3 Rad8 17. h3 c5 18. g4 Rd4 19. Bc2`

FEN (line start): `r2qr1k1/ppp2ppp/4bn2/4Q3/2P5/8/PP1NBPPP/R3R1K1 b - - 1 13`

Game (full game at ply): http://localhost:5173/analysis?game_id=684175&ply=24

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qr1k1/ppp2ppp/4bn2/4Q3/2P5/8/PP1NBPPP/R3R1K1%20b%20-%20-%201%2013

#### Case 784 — CLEARANCE (allowed, depth 10)

Moves (SAN): `15... Nxe4 16. Qc2 f5`

FEN (line start): `r2q1r2/pbp2pbk/1p1p1npp/1P1Pp3/2P1P3/4BN1P/P2QNPP1/R3K2R b - - 1 15`

Game (full game at ply): http://localhost:5173/analysis?game_id=684180&ply=28

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2q1r2/pbp2pbk/1p1p1npp/1P1Pp3/2P1P3/4BN1P/P2QNPP1/R3K2R%20b%20-%20-%201%2015

#### Case 785 — DISCOVERED_ATTACK (allowed, depth 1)

Moves (SAN): `18... Nxg4 19. hxg4 Bxa1 20. Qd2 Rh8 21. Nc3 Kg8 22. Bd4 Bxc3 23. Qxc3 Rh7 24. Bf6`

FEN (line start): `r2q1r2/pbp2pbk/1p1p1npp/1P1P4/2P1p1N1/4B2P/P1Q1NPP1/R3K2R b - - 1 18`

Game (full game at ply): http://localhost:5173/analysis?game_id=684180&ply=34

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2q1r2/pbp2pbk/1p1p1npp/1P1P4/2P1p1N1/4B2P/P1Q1NPP1/R3K2R%20b%20-%20-%201%2018

#### Case 786 — PIN (allowed, depth 2)

Moves (SAN): `31. Qd3+ Re4 32. c7 Qc5 33. Re1 Qc4 34. Qb1 Qxc7 35. Rxe4 Nxe4 36. Qxe4+ Kg8`

FEN (line start): `8/3Q2pk/p1P5/4P1np/5r2/P6P/5qP1/3R3K w - - 1 31`

Game (full game at ply): http://localhost:5173/analysis?game_id=684184&ply=59

FEN (free-play from line start): http://localhost:5173/analysis?fen=8/3Q2pk/p1P5/4P1np/5r2/P6P/5qP1/3R3K%20w%20-%20-%201%2031

#### Case 787 — CAPTURING_DEFENDER (missed, depth 2)

Moves (SAN): `7. Bxf6 Qxf6 8. Nxd5 Qd8 9. e4 Nc6 10. Rc1 Be6 11. Bc4 cxd4`

FEN (line start): `rnb1kb1r/pp3ppp/1q3n2/2pp2B1/3P4/2N2N2/PP2PPPP/R2QKB1R w - - 0 7`

Game (full game at ply): http://localhost:5173/analysis?game_id=684191&ply=12

FEN (free-play from line start): http://localhost:5173/analysis?fen=rnb1kb1r/pp3ppp/1q3n2/2pp2B1/3P4/2N2N2/PP2PPPP/R2QKB1R%20w%20-%20-%200%207

#### Case 788 — CLEARANCE (missed, depth 4)

Moves (SAN): `9. Bxf6 Qxf6 10. e3 Bb4 11. Bb5+ Nc6 12. Rc1`

FEN (line start): `rnb1k2r/pp3ppp/1q3n2/2bp2B1/3N4/1PN5/P3PPPP/R2QKB1R w - - 0 9`

Game (full game at ply): http://localhost:5173/analysis?game_id=684191&ply=16

FEN (free-play from line start): http://localhost:5173/analysis?fen=rnb1k2r/pp3ppp/1q3n2/2bp2B1/3N4/1PN5/P3PPPP/R2QKB1R%20w%20-%20-%200%209

#### Case 789 — ATTRACTION (allowed, depth 0)

Moves (SAN): `26... Qxe3 27. Rxe3 Bf4 28. Ke2 Bxe3 29. Kxe3 Kf8 30. Ra2 Re7 31. Nf4 Bf5 32. g4`

FEN (line start): `3rr1k1/p4ppp/1qp3b1/8/2B1P3/1P1NQP2/3R2Pb/4RK2 b - - 1 26`

Game (full game at ply): http://localhost:5173/analysis?game_id=684191&ply=50

FEN (free-play from line start): http://localhost:5173/analysis?fen=3rr1k1/p4ppp/1qp3b1/8/2B1P3/1P1NQP2/3R2Pb/4RK2%20b%20-%20-%201%2026

#### Case 790 — CLEARANCE (missed, depth 4)

Moves (SAN): `8. Qb3 Qe6 9. e3 g6 10. Bd3 Bg7 11. Rc1 c6`

FEN (line start): `rn2kb1r/pbp2ppp/1p3q2/3p4/3P4/2N2N2/PP2PPPP/R2QKB1R w - - 0 8`

Game (full game at ply): http://localhost:5173/analysis?game_id=684193&ply=14

FEN (free-play from line start): http://localhost:5173/analysis?fen=rn2kb1r/pbp2ppp/1p3q2/3p4/3P4/2N2N2/PP2PPPP/R2QKB1R%20w%20-%20-%200%208

#### Case 791 — PIN (missed, depth 8)

Moves (SAN): `20... e5 21. Qd1 Nxf2 22. Qd2 Rad8 23. Qe3 Qg6 24. Qxe5 Nxh3+ 25. Kh2 Ng5 26. Ng3`

FEN (line start): `r4rk1/6pp/p2qp3/3p3N/2pQn3/7P/PPP2PP1/R3R1K1 b - - 0 20`

Game (full game at ply): http://localhost:5173/analysis?game_id=684204&ply=39

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4rk1/6pp/p2qp3/3p3N/2pQn3/7P/PPP2PP1/R3R1K1%20b%20-%20-%200%2020

#### Case 792 — PIN (allowed, depth 2)

Moves (SAN): `8. Nxe5 Nxe5 9. Re1 Be7 10. Rxe5`

FEN (line start): `r2qkb1r/pp1n1ppp/5n2/3pp3/8/3P1N2/PPP2PPP/RNBQ1RK1 w - - 0 8`

Game (full game at ply): http://localhost:5173/analysis?game_id=684213&ply=13

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qkb1r/pp1n1ppp/5n2/3pp3/8/3P1N2/PPP2PPP/RNBQ1RK1%20w%20-%20-%200%208

#### Case 793 — CLEARANCE (missed, depth 6)

Moves (SAN): `7... Qc7 8. Qe2 Rc8 9. Bd2 e6 10. c4 Be7 11. Nc3 dxc4 12. Nb5 Qb8 13. dxc4`

FEN (line start): `r2qkb1r/pp1npppp/5n2/3p4/8/3P1N2/PPP2PPP/RNBQ1RK1 b - - 0 7`

Game (full game at ply): http://localhost:5173/analysis?game_id=684213&ply=13

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qkb1r/pp1npppp/5n2/3p4/8/3P1N2/PPP2PPP/RNBQ1RK1%20b%20-%20-%200%207

#### Case 794 — DISCOVERED_CHECK (allowed, depth 4)

Moves (SAN): `30. Nd2 Qd7 31. Kc1 Raf8 32. c4+ Kg8 33. Qb5 R2f5 34. Rhf1 dxc4 35. Rxf5 Rxf5`

FEN (line start): `r6k/1p5p/2n1q1p1/3p4/2N5/2P5/PQK2r2/4R2R w - - 1 30`

Game (full game at ply): http://localhost:5173/analysis?game_id=684227&ply=57

FEN (free-play from line start): http://localhost:5173/analysis?fen=r6k/1p5p/2n1q1p1/3p4/2N5/2P5/PQK2r2/4R2R%20w%20-%20-%201%2030

#### Case 795 — CLEARANCE (allowed, depth 2)

Moves (SAN): `32. Rxh7+ Kg8 33. Reh1 Ne5 34. Rh8+ Kf7 35. Qxb7+ Kf6 36. Qb6+ Kf5 37. Rxa8 Qxd2+`

FEN (line start): `r6k/1p5p/2n3p1/3p4/5q2/2P5/PQ1N1r2/2K1R2R w - - 1 32`

Game (full game at ply): http://localhost:5173/analysis?game_id=684227&ply=61

FEN (free-play from line start): http://localhost:5173/analysis?fen=r6k/1p5p/2n3p1/3p4/5q2/2P5/PQ1N1r2/2K1R2R%20w%20-%20-%201%2032

#### Case 796 — PIN (allowed, depth 0)

Moves (SAN): `37. Rxb8 h5 38. Rxf8+ Rxf8 39. d6 Nf2 40. Re1 Ng4 41. d7 Nf6 42. Re7 Kh8`

FEN (line start): `1r2Rqk1/1Q5p/6p1/3P4/8/3n4/P2N1r2/1K5R w - - 1 37`

Game (full game at ply): http://localhost:5173/analysis?game_id=684227&ply=71

FEN (free-play from line start): http://localhost:5173/analysis?fen=1r2Rqk1/1Q5p/6p1/3P4/8/3n4/P2N1r2/1K5R%20w%20-%20-%201%2037

#### Case 797 — PIN (missed, depth 2)

Moves (SAN): `8. cxd5 exd5 9. Bb5 Bb7 10. Qa4 Qd7 11. Nxd5 Qxd5 12. Rc1 Kd7 13. Ne5+ Bxe5`

FEN (line start): `r1bqk2r/p1p2ppp/1pn1pb2/3p4/2PP4/2N1PN2/PP3PPP/R2QKB1R w - - 0 8`

Game (full game at ply): http://localhost:5173/analysis?game_id=684263&ply=14

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1bqk2r/p1p2ppp/1pn1pb2/3p4/2PP4/2N1PN2/PP3PPP/R2QKB1R%20w%20-%20-%200%208

#### Case 798 — SACRIFICE (allowed, depth 6)

Moves (SAN): `25. Qd4 Bxh5 26. Qxb6 cxb6 27. Rb3 Rxa4 28. Nd4 Be8 29. Bf3 h5 30. Bxg4 hxg4`

FEN (line start): `r2r2k1/1pp2bpp/1q3p2/3P3P/Pp2PPn1/5R2/4N1B1/2RQ2K1 w - - 1 25`

Game (full game at ply): http://localhost:5173/analysis?game_id=684264&ply=47

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2r2k1/1pp2bpp/1q3p2/3P3P/Pp2PPn1/5R2/4N1B1/2RQ2K1%20w%20-%20-%201%2025

#### Case 799 — DISCOVERED_ATTACK (missed, depth 7)

Moves (SAN): `24. Qh4 Rh8 25. Qe7 Qe6 26. Qg5 f5 27. exf6+ Qxf6 28. Qxd5 Rhf8 29. h3 c5`

FEN (line start): `2r1r3/2p1Qpk1/p5p1/1p1pPq2/3P4/2P1P1R1/P5PP/R5K1 w - - 0 24`

Game (full game at ply): http://localhost:5173/analysis?game_id=684268&ply=46

FEN (free-play from line start): http://localhost:5173/analysis?fen=2r1r3/2p1Qpk1/p5p1/1p1pPq2/3P4/2P1P1R1/P5PP/R5K1%20w%20-%20-%200%2024

#### Case 800 — SACRIFICE (missed, depth 2)

Moves (SAN): `35. Kxf2 Qxg4 36. a4 Qh3 37. c5 Qh2+ 38. Ke1 Qxg3+ 39. Kd2 Qg2+ 40. Ke1 bxc5`

FEN (line start): `8/p5k1/1p3p2/6pq/2PP2Q1/4PKP1/P4r2/2R5 w - - 0 35`

Game (full game at ply): http://localhost:5173/analysis?game_id=684292&ply=68

FEN (free-play from line start): http://localhost:5173/analysis?fen=8/p5k1/1p3p2/6pq/2PP2Q1/4PKP1/P4r2/2R5%20w%20-%20-%200%2035

#### Case 801 — CLEARANCE (missed, depth 8)

Moves (SAN): `15... g6 16. a3 h5 17. g3 h4 18. Nb4 Kg7 19. Nd3 Rh8 20. Bg2 Rh6 21. Qd2`

FEN (line start): `r2q1rk1/1p3pp1/p1n1pb1p/3p4/3P4/2P2B2/PPN2PPP/R2QR1K1 b - - 0 15`

Game (full game at ply): http://localhost:5173/analysis?game_id=684296&ply=29

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2q1rk1/1p3pp1/p1n1pb1p/3p4/3P4/2P2B2/PPN2PPP/R2QR1K1%20b%20-%20-%200%2015

#### Case 802 — CLEARANCE (missed, depth 2)

Moves (SAN): `20... Rxc1 21. Bxc1 Rc8 22. Be3 Nc3 23. f4 h5 24. Nd4 Ne4 25. Ne2 Qb2 26. Rc1`

FEN (line start): `2r2rk1/5ppp/p2bpq2/1p1p4/1P2n3/PP1Q3P/3BNPP1/2R2RK1 b - - 0 20`

Game (full game at ply): http://localhost:5173/analysis?game_id=684320&ply=39

FEN (free-play from line start): http://localhost:5173/analysis?fen=2r2rk1/5ppp/p2bpq2/1p1p4/1P2n3/PP1Q3P/3BNPP1/2R2RK1%20b%20-%20-%200%2020

#### Case 803 — PIN (allowed, depth 0)

Moves (SAN): `22. fxe6+ Kg6 23. Rxf6+ gxf6 24. Qg3+ Kh7 25. Qf4 Rg8 26. Qxf6 Rg7 27. Qf4 Kg8`

FEN (line start): `r4b1r/pR2nkp1/4pq1p/5P2/4p3/1Q6/P5PP/5RK1 w - - 1 22`

Game (full game at ply): http://localhost:5173/analysis?game_id=684327&ply=41

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4b1r/pR2nkp1/4pq1p/5P2/4p3/1Q6/P5PP/5RK1%20w%20-%20-%201%2022

#### Case 804 — CLEARANCE (missed, depth 8)

Moves (SAN): `21... Kg8 22. Qxe6+ Kh7 23. f6 Re8 24. Qf7 Nf5 25. g3 Bc5+ 26. Kg2 Rhf8 27. Qxg7+`

FEN (line start): `r4b1r/pR2nkp1/4p2p/5P2/4p2q/1Q6/P5PP/5RK1 b - - 0 21`

Game (full game at ply): http://localhost:5173/analysis?game_id=684327&ply=41

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4b1r/pR2nkp1/4p2p/5P2/4p2q/1Q6/P5PP/5RK1%20b%20-%20-%200%2021

#### Case 805 — FORK (allowed, depth 4)

Moves (SAN): `30. Rf7+ Kg6 31. Qxf5+ Kh6 32. Qxe4 Re8 33. Qxb1 Rxe6 34. Qf5 Rd6 35. Re7 Rf6`

FEN (line start): `r7/p2R2b1/4Pk2/5np1/4p1Q1/8/P5PK/1r6 w - - 1 30`

Game (full game at ply): http://localhost:5173/analysis?game_id=684327&ply=57

FEN (free-play from line start): http://localhost:5173/analysis?fen=r7/p2R2b1/4Pk2/5np1/4p1Q1/8/P5PK/1r6%20w%20-%20-%201%2030

#### Case 806 — SACRIFICE (missed, depth 4)

Moves (SAN): `32... Ne7 33. Rd1 Rf2 34. Kxf2 Bf8 35. Rf1 Kg7 36. Ke2 Ng6 37. Rf7+ Kh6 38. Qh1+`

FEN (line start): `4r3/p2R2b1/4Pk2/5np1/4Q1P1/8/Pr6/6K1 b - - 0 32`

Game (full game at ply): http://localhost:5173/analysis?game_id=684327&ply=63

FEN (free-play from line start): http://localhost:5173/analysis?fen=4r3/p2R2b1/4Pk2/5np1/4Q1P1/8/Pr6/6K1%20b%20-%20-%200%2032

#### Case 807 — DISCOVERED_ATTACK (allowed, depth 7)

Moves (SAN): `8. Be3 Bxf3 9. gxf3 Qe6 10. a5 a6 11. Bxa6 Qxa6 12. Qxd4 e6 13. Qa4+ b5`

FEN (line start): `r3kbnr/pp2pppp/1q6/3p4/P2n1Bb1/3B1N2/1PP2PPP/RN1QK2R w - - 1 8`

Game (full game at ply): http://localhost:5173/analysis?game_id=684334&ply=13

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3kbnr/pp2pppp/1q6/3p4/P2n1Bb1/3B1N2/1PP2PPP/RN1QK2R%20w%20-%20-%201%208

#### Case 808 — CLEARANCE (missed, depth 4)

Moves (SAN): `7... Bxf3 8. gxf3 e6 9. a5 Bd6 10. Be3 Nc6 11. a6 bxa6 12. Rg1 g6 13. Rxa6`

FEN (line start): `r2qkbnr/pp2pppp/8/3p4/P2n1Bb1/3B1N2/1PP2PPP/RN1QK2R b - - 0 7`

Game (full game at ply): http://localhost:5173/analysis?game_id=684334&ply=13

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qkbnr/pp2pppp/8/3p4/P2n1Bb1/3B1N2/1PP2PPP/RN1QK2R%20b%20-%20-%200%207

#### Case 809 — HANGING_PIECE (allowed, depth 0)

Moves (SAN): `18... Kxf7`

FEN (line start): `r4rk1/2pB1Np1/1p2p2p/3p4/P2P4/1qPQP3/5PPP/R5K1 b - - 0 18`

Game (full game at ply): http://localhost:5173/analysis?game_id=684337&ply=34

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4rk1/2pB1Np1/1p2p2p/3p4/P2P4/1qPQP3/5PPP/R5K1%20b%20-%20-%200%2018

#### Case 810 — FORK (allowed, depth 2)

Moves (SAN): `22... Rxf2 23. Qg6 Rxg2+ 24. Qxg2 Qxb1+ 25. Qf1 Qg6+ 26. Qg2 Qh5 27. Be2 Qf5 28. Bb5`

FEN (line start): `r4rk1/2p3p1/1p2p2p/1B1pP3/P2P4/2PQ4/q4PPP/1R4K1 b - - 0 22`

Game (full game at ply): http://localhost:5173/analysis?game_id=684337&ply=42

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4rk1/2p3p1/1p2p2p/1B1pP3/P2P4/2PQ4/q4PPP/1R4K1%20b%20-%20-%200%2022

#### Case 811 — CLEARANCE (allowed, depth 2)

Moves (SAN): `24... Rxf1+ 25. Qxf1 Rf8 26. Qd1 Qe4 27. Qg1 Rf4 28. h3 Kf7 29. Kh2 Ke7 30. Kh1`

FEN (line start): `r4rk1/2p3p1/1p2p2p/1B1pP3/P2P3q/2PQ4/6PP/5R1K b - - 1 24`

Game (full game at ply): http://localhost:5173/analysis?game_id=684337&ply=46

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4rk1/2p3p1/1p2p2p/1B1pP3/P2P3q/2PQ4/6PP/5R1K%20b%20-%20-%201%2024

#### Case 812 — MATE (allowed, depth 4)

Moves (SAN): `26... Qe1+ 27. Qf1 Rxf1+ 28. Bxf1 Qxf1#`

FEN (line start): `5rk1/2p3p1/1p2p2p/1B1pP3/P2P3q/2PQ4/6PP/7K b - - 1 26`

Game (full game at ply): http://localhost:5173/analysis?game_id=684337&ply=50

FEN (free-play from line start): http://localhost:5173/analysis?fen=5rk1/2p3p1/1p2p2p/1B1pP3/P2P3q/2PQ4/6PP/7K%20b%20-%20-%201%2026

#### Case 813 — SACRIFICE (missed, depth 2)

Moves (SAN): `27. Qd1 cxb5 28. h3 bxa4 29. c4 dxc4 30. d5 Qf4 31. dxe6 Qf1+ 32. Qxf1 Rxf1+`

FEN (line start): `5rk1/6p1/1pp1p2p/1B1pP3/P2P3q/2PQ4/6PP/7K w - - 0 27`

Game (full game at ply): http://localhost:5173/analysis?game_id=684337&ply=52

FEN (free-play from line start): http://localhost:5173/analysis?fen=5rk1/6p1/1pp1p2p/1B1pP3/P2P3q/2PQ4/6PP/7K%20w%20-%20-%200%2027

#### Case 814 — CAPTURING_DEFENDER (missed, depth 10)

Moves (SAN): `11... e4 12. Nd4 Ne5`

FEN (line start): `r1bq1rk1/pp3ppp/2n5/1B1np3/8/P1P1PN2/3Q1PPP/R1B1K2R b - - 0 11`

Game (full game at ply): http://localhost:5173/analysis?game_id=684342&ply=21

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1bq1rk1/pp3ppp/2n5/1B1np3/8/P1P1PN2/3Q1PPP/R1B1K2R%20b%20-%20-%200%2011

#### Case 815 — MATE (allowed, depth 6)

Moves (SAN): `47. Rc5 Re8 48. c8=Q Re5 49. Rxe5 g3 50. fxg3#`

FEN (line start): `1Br5/2P5/8/8/6pk/2R5/5PKP/8 w - - 1 47`

Game (full game at ply): http://localhost:5173/analysis?game_id=684342&ply=91

FEN (free-play from line start): http://localhost:5173/analysis?fen=1Br5/2P5/8/8/6pk/2R5/5PKP/8%20w%20-%20-%201%2047

#### Case 816 — SACRIFICE (missed, depth 6)

Moves (SAN): `47... Kh5 48. Rd8 Rxc7 49. Rd5+ Kg6 50. Bxc7 Kf6 51. Re5 Kf7 52. Kg3 Kg7 53. Kxg4`

FEN (line start): `1Br5/2P5/8/8/6pk/3R4/5PKP/8 b - - 0 47`

Game (full game at ply): http://localhost:5173/analysis?game_id=684342&ply=93

FEN (free-play from line start): http://localhost:5173/analysis?fen=1Br5/2P5/8/8/6pk/3R4/5PKP/8%20b%20-%20-%200%2047

#### Case 817 — PIN (allowed, depth 0)

Moves (SAN): `19. Nf5 Qd7 20. b4 g6 21. Rad1 Rd8 22. Ne3 Be7 23. Nxd5 exd5 24. Qf6 Rg8`

FEN (line start): `r3kb1r/5ppp/p2qp3/2pp4/3N4/1P3Q2/P4PPP/R3R1K1 w - - 0 19`

Game (full game at ply): http://localhost:5173/analysis?game_id=684344&ply=35

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3kb1r/5ppp/p2qp3/2pp4/3N4/1P3Q2/P4PPP/R3R1K1%20w%20-%20-%200%2019

#### Case 818 — PIN (allowed, depth 0)

Moves (SAN): `20. Qxd5 Rd8 21. Qc4 g6 22. Ne3 Be7 23. Qxa6`

FEN (line start): `r3kb1r/2q2ppp/p3p3/2pp1N2/8/1P3Q2/P4PPP/R3R1K1 w - - 1 20`

Game (full game at ply): http://localhost:5173/analysis?game_id=684344&ply=37

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3kb1r/2q2ppp/p3p3/2pp1N2/8/1P3Q2/P4PPP/R3R1K1%20w%20-%20-%201%2020

#### Case 819 — PIN (allowed, depth 0)

Moves (SAN): `21. Qxd5`

FEN (line start): `r3k2r/2q2ppp/p2bp3/2pp4/8/1P3QN1/P4PPP/R3R1K1 w - - 1 21`

Game (full game at ply): http://localhost:5173/analysis?game_id=684344&ply=39

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3k2r/2q2ppp/p2bp3/2pp4/8/1P3QN1/P4PPP/R3R1K1%20w%20-%20-%201%2021

#### Case 820 — PIN (allowed, depth 0)

Moves (SAN): `32. Nh5 Rb4 33. Nf6+ Kg7 34. Nxe8+ Qxe8 35. g3 Rg4 36. Qd2 d4 37. Rxe6 Qc6+`

FEN (line start): `4r1k1/5q1p/p2bp1p1/3p1pQ1/5r2/6N1/P3R1P1/4R2K w - - 1 32`

Game (full game at ply): http://localhost:5173/analysis?game_id=684344&ply=61

FEN (free-play from line start): http://localhost:5173/analysis?fen=4r1k1/5q1p/p2bp1p1/3p1pQ1/5r2/6N1/P3R1P1/4R2K%20w%20-%20-%201%2032

#### Case 821 — DISCOVERED_ATTACK (missed, depth 1)

Moves (SAN): `31... Rg4 32. Rxe6 Bxg3 33. Qe3 Rh4+ 34. Kg1 Bxe1 35. Rxa6 Re4 36. Qd3 Rfe8 37. g3`

FEN (line start): `5rk1/5q1p/p2bp1p1/3p1pQ1/5r2/6N1/P3R1P1/4R2K b - - 0 31`

Game (full game at ply): http://localhost:5173/analysis?game_id=684344&ply=61

FEN (free-play from line start): http://localhost:5173/analysis?fen=5rk1/5q1p/p2bp1p1/3p1pQ1/5r2/6N1/P3R1P1/4R2K%20b%20-%20-%200%2031

#### Case 822 — DEFLECTION (allowed, depth 2)

Moves (SAN): `22... Rxf2 23. Rxf2 Qxa1+ 24. Kh2 Rxf2 25. Qxf2 b6 26. Qh4 Qf6 27. Qg4 Qe7 28. a4`

FEN (line start): `5r2/ppp2rkp/3p2p1/3P4/2P5/P3Q2P/1q3PP1/R4RK1 b - - 1 22`

Game (full game at ply): http://localhost:5173/analysis?game_id=684353&ply=42

FEN (free-play from line start): http://localhost:5173/analysis?fen=5r2/ppp2rkp/3p2p1/3P4/2P5/P3Q2P/1q3PP1/R4RK1%20b%20-%20-%201%2022

#### Case 823 — SKEWER (missed, depth 2)

Moves (SAN): `22. Rab1 Qxa3 23. Rxb7 Qc5 24. Rb5 Qa3 25. Qd4+ Kg8 26. Qd2 Rf4 27. Ra5 Qb3`

FEN (line start): `5r2/ppp2rkp/3p2p1/3P4/2P1Q3/P6P/1q3PP1/R4RK1 w - - 0 22`

Game (full game at ply): http://localhost:5173/analysis?game_id=684353&ply=42

FEN (free-play from line start): http://localhost:5173/analysis?fen=5r2/ppp2rkp/3p2p1/3P4/2P1Q3/P6P/1q3PP1/R4RK1%20w%20-%20-%200%2022

#### Case 824 — PIN (allowed, depth 2)

Moves (SAN): `19. Rxb4 Bxe2 20. Rxb6 Rxb6 21. Bf2 Bh5 22. Rb1 Rxb1+ 23. Nxb1 Kf8 24. Qxc6 Kg8`

FEN (line start): `1r2k2r/5pp1/pqp1p3/3pPn2/Qb1P2b1/P1N1B3/4N2P/RR4K1 w - - 1 19`

Game (full game at ply): http://localhost:5173/analysis?game_id=684356&ply=35

FEN (free-play from line start): http://localhost:5173/analysis?fen=1r2k2r/5pp1/pqp1p3/3pPn2/Qb1P2b1/P1N1B3/4N2P/RR4K1%20w%20-%20-%201%2019

#### Case 825 — CLEARANCE (allowed, depth 8)

Moves (SAN): `20. Nxe2 a5 21. axb4 axb4 22. Qd1`

FEN (line start): `1r2k2r/5pp1/pqp1p3/3pPn2/Qb1P4/P1N5/4bB1P/RR4K1 w - - 0 20`

Game (full game at ply): http://localhost:5173/analysis?game_id=684356&ply=37

FEN (free-play from line start): http://localhost:5173/analysis?fen=1r2k2r/5pp1/pqp1p3/3pPn2/Qb1P4/P1N5/4bB1P/RR4K1%20w%20-%20-%200%2020

#### Case 826 — SACRIFICE (missed, depth 2)

Moves (SAN): `19... a5 20. axb4 axb4 21. Rxb4 Qxb4 22. Qxb4 Rxb4 23. Ra8+ Kd7 24. Rxh8 c5 25. dxc5`

FEN (line start): `1r2k2r/5pp1/pqp1p3/3pPn2/Qb1P2b1/P1N5/4NB1P/RR4K1 b - - 0 19`

Game (full game at ply): http://localhost:5173/analysis?game_id=684356&ply=37

FEN (free-play from line start): http://localhost:5173/analysis?fen=1r2k2r/5pp1/pqp1p3/3pPn2/Qb1P2b1/P1N5/4NB1P/RR4K1%20b%20-%20-%200%2019

#### Case 827 — HANGING_PIECE (allowed, depth 0)

Moves (SAN): `30. Rxd4`

FEN (line start): `7r/3k1pp1/q1p1p3/PpQpP3/1R1n4/8/8/2R2KBr w - - 0 30`

Game (full game at ply): http://localhost:5173/analysis?game_id=684356&ply=57

FEN (free-play from line start): http://localhost:5173/analysis?fen=7r/3k1pp1/q1p1p3/PpQpP3/1R1n4/8/8/2R2KBr%20w%20-%20-%200%2030

#### Case 828 — DEFLECTION (allowed, depth 4)

Moves (SAN): `32. Qb8+ Kd7 33. Qd6+ Ke8 34. Rxc6 Qb7 35. Rxh4 Rxh4 36. Rc7 Qxc7 37. Qxc7 Rc4`

FEN (line start): `4k3/5pp1/q1pQp3/Pp1pP3/3R3r/8/8/2R2KBr w - - 1 32`

Game (full game at ply): http://localhost:5173/analysis?game_id=684356&ply=61

FEN (free-play from line start): http://localhost:5173/analysis?fen=4k3/5pp1/q1pQp3/Pp1pP3/3R3r/8/8/2R2KBr%20w%20-%20-%201%2032

#### Case 829 — DISCOVERED_CHECK (missed, depth 0)

Moves (SAN): `31... b4+`

FEN (line start): `4k2r/5pp1/q1pQp3/Pp1pP3/3R4/8/8/2R2KBr b - - 0 31`

Game (full game at ply): http://localhost:5173/analysis?game_id=684356&ply=61

FEN (free-play from line start): http://localhost:5173/analysis?fen=4k2r/5pp1/q1pQp3/Pp1pP3/3R4/8/8/2R2KBr%20b%20-%20-%200%2031

#### Case 830 — MATE (allowed, depth 10)

Moves (SAN): `34. Rxa6 Rf4+ 35. Bf2 Rxf2+ 36. Kxf2 f6 37. Qxe6+ Kd8 38. Ra8+ Kc7 39. Qc8#`

FEN (line start): `4k3/5pp1/q1RQp3/P2pP3/1p5r/8/8/5KB1 w - - 0 34`

Game (full game at ply): http://localhost:5173/analysis?game_id=684356&ply=65

FEN (free-play from line start): http://localhost:5173/analysis?fen=4k3/5pp1/q1RQp3/P2pP3/1p5r/8/8/5KB1%20w%20-%20-%200%2034

#### Case 831 — SACRIFICE (missed, depth 10)

Moves (SAN): `33... Rf4+ 34. Ke2 Qa8 35. Rc7 Qd8 36. Qc6+ Kf8 37. Rc8 g5 38. Rxd8+ Kg7 39. Qe8`

FEN (line start): `4k3/5pp1/q1RQp3/Pp1pP3/7r/8/8/5KB1 b - - 0 33`

Game (full game at ply): http://localhost:5173/analysis?game_id=684356&ply=65

FEN (free-play from line start): http://localhost:5173/analysis?fen=4k3/5pp1/q1RQp3/Pp1pP3/7r/8/8/5KB1%20b%20-%20-%200%2033

#### Case 832 — CLEARANCE (allowed, depth 4)

Moves (SAN): `15... Bxc5 16. Kh1 a5 17. Na4 Ba7 18. Rac1 f6 19. Qc3 fxe5 20. Qxe5 Qe7 21. Nc5`

FEN (line start): `r2qk3/pp2bpr1/2p1p2p/2PpPp2/5P2/2NQP3/PP4PP/R4RK1 b - - 0 15`

Game (full game at ply): http://localhost:5173/analysis?game_id=684361&ply=28

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qk3/pp2bpr1/2p1p2p/2PpPp2/5P2/2NQP3/PP4PP/R4RK1%20b%20-%20-%200%2015

#### Case 833 — MATE (allowed, depth 4)

Moves (SAN): `30... Rb1+ 31. Rc1 Rxc1+ 32. Qf1 Rxf1#`

FEN (line start): `1r6/2k2pr1/2p1p2p/p2pPp2/5Pq1/b3P3/2R1Q1PP/7K b - - 1 30`

Game (full game at ply): http://localhost:5173/analysis?game_id=684361&ply=58

FEN (free-play from line start): http://localhost:5173/analysis?fen=1r6/2k2pr1/2p1p2p/p2pPp2/5Pq1/b3P3/2R1Q1PP/7K%20b%20-%20-%201%2030

#### Case 834 — INTERFERENCE (allowed, depth 4)

Moves (SAN): `25... Rac8 26. e4 Nc3 27. Re1 Qxa3 28. Bh4 Rd7 29. Ne5 Rxd4 30. Qf3 Qf8 31. h3`

FEN (line start): `r2r2k1/4qpp1/p3p2p/1p1n4/3P4/P2QPNB1/5PPP/1R4K1 b - - 1 25`

Game (full game at ply): http://localhost:5173/analysis?game_id=684369&ply=48

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2r2k1/4qpp1/p3p2p/1p1n4/3P4/P2QPNB1/5PPP/1R4K1%20b%20-%20-%201%2025

#### Case 835 — FORK (missed, depth 2)

Moves (SAN): `25. e4 Nb6 26. Nc6 Qd7 27. Nxd8 Rxd8 28. Rd1 Qc8 29. h3 Na4 30. Qf3 Nb2`

FEN (line start): `r2r2k1/4qpp1/p3p2p/1p1nN3/3P4/P2QP1B1/5PPP/1R4K1 w - - 0 25`

Game (full game at ply): http://localhost:5173/analysis?game_id=684369&ply=48

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2r2k1/4qpp1/p3p2p/1p1nN3/3P4/P2QP1B1/5PPP/1R4K1%20w%20-%20-%200%2025

#### Case 836 — PIN (missed, depth 0)

Moves (SAN): `35. Nh6+`

FEN (line start): `r3rqk1/5Np1/4ppQ1/p7/1n1P3B/4P3/5PPP/1R4K1 w - - 0 35`

Game (full game at ply): http://localhost:5173/analysis?game_id=684369&ply=68

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3rqk1/5Np1/4ppQ1/p7/1n1P3B/4P3/5PPP/1R4K1%20w%20-%20-%200%2035

#### Case 837 — CLEARANCE (allowed, depth 6)

Moves (SAN): `53... Rb1 54. Ke3 Rxa1 55. Kxd2 Rf1 56. Kd3 a1=Q 57. Ke2 Qe1+ 58. Kd3 Rxf2 59. Kc4`

FEN (line start): `8/7k/4p1pP/4P1P1/1r2P3/5K2/p2r1P2/R7 b - - 0 53`

Game (full game at ply): http://localhost:5173/analysis?game_id=684369&ply=104

FEN (free-play from line start): http://localhost:5173/analysis?fen=8/7k/4p1pP/4P1P1/1r2P3/5K2/p2r1P2/R7%20b%20-%20-%200%2053

#### Case 838 — SACRIFICE (missed, depth 8)

Moves (SAN): `53. Rc1 Rd7 54. Ra1 Ra7 55. Ke2 Rb1 56. Rxa2 Rxa2+ 57. Kd3 Rxf2 58. Kc3 Rg2`

FEN (line start): `8/7k/4p1pP/4P1P1/1r6/4PK2/p2r1P2/R7 w - - 0 53`

Game (full game at ply): http://localhost:5173/analysis?game_id=684369&ply=104

FEN (free-play from line start): http://localhost:5173/analysis?fen=8/7k/4p1pP/4P1P1/1r6/4PK2/p2r1P2/R7%20w%20-%20-%200%2053

#### Case 839 — EN_PASSANT (missed, depth 4)

Moves (SAN): `9. d5 Na5 10. Nxb5 e5 11. dxe6 Bb4+ 12. Bd2 Bxd2+ 13. Qxd2 fxe6 14. Qxd8+ Kxd8`

FEN (line start): `r2qkb1r/1bp1pppp/2n2n2/1p6/2pPPB2/2N2N2/1P3PPP/R2QKB1R w - - 0 9`

Game (full game at ply): http://localhost:5173/analysis?game_id=684376&ply=16

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qkb1r/1bp1pppp/2n2n2/1p6/2pPPB2/2N2N2/1P3PPP/R2QKB1R%20w%20-%20-%200%209

#### Case 840 — DISCOVERED_ATTACK (allowed, depth 3)

Moves (SAN): `16... Nxd4 17. Bf3 Ne2+ 18. Kh1 Qxd2 19. Bxb7 Nxc3 20. Qa1 Rd8 21. f4 Nd1 22. f5`

FEN (line start): `5rk1/1bp1bppp/2n1p3/1p1qP3/2pP4/2P3B1/3NBPPP/1Q3RK1 b - - 1 16`

Game (full game at ply): http://localhost:5173/analysis?game_id=684376&ply=30

FEN (free-play from line start): http://localhost:5173/analysis?fen=5rk1/1bp1bppp/2n1p3/1p1qP3/2pP4/2P3B1/3NBPPP/1Q3RK1%20b%20-%20-%201%2016

#### Case 841 — DEFLECTION (missed, depth 8)

Moves (SAN): `16. Bd1 Na5 17. Bc2 h6 18. Re1 b4 19. Bh4 Bxh4 20. Qxb4 Bd8 21. Bh7+ Kxh7`

FEN (line start): `5rk1/1bp1bppp/2n1p3/1p1qP3/2pP4/2P2NB1/4BPPP/1Q3RK1 w - - 0 16`

Game (full game at ply): http://localhost:5173/analysis?game_id=684376&ply=30

FEN (free-play from line start): http://localhost:5173/analysis?fen=5rk1/1bp1bppp/2n1p3/1p1qP3/2pP4/2P2NB1/4BPPP/1Q3RK1%20w%20-%20-%200%2016

#### Case 842 — CLEARANCE (allowed, depth 6)

Moves (SAN): `26... cxb4 27. Ne4 c3 28. h4 b3 29. Nxc3 Qb4 30. Ne4 b2 31. h5 Kg7 32. Kh2`

FEN (line start): `5rk1/1q3p1p/b3p1p1/2p1P1N1/1Pp5/8/5PPP/1Q1R2K1 b - - 0 26`

Game (full game at ply): http://localhost:5173/analysis?game_id=684376&ply=50

FEN (free-play from line start): http://localhost:5173/analysis?fen=5rk1/1q3p1p/b3p1p1/2p1P1N1/1Pp5/8/5PPP/1Q1R2K1%20b%20-%20-%200%2026

#### Case 843 — CLEARANCE (allowed, depth 10)

Moves (SAN): `15... Nxe5 16. Bxb7 Nxf3+ 17. Bxf3 Rac8 18. Qa4 Qb6 19. g3 Rfd8 20. Rfd1 Bf8 21. b3`

FEN (line start): `r4rk1/pb2ppbp/2n2qp1/3BB3/1p1P4/4PN2/PP3PPP/2RQ1RK1 b - - 1 15`

Game (full game at ply): http://localhost:5173/analysis?game_id=684378&ply=28

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4rk1/pb2ppbp/2n2qp1/3BB3/1p1P4/4PN2/PP3PPP/2RQ1RK1%20b%20-%20-%201%2015

#### Case 844 — EN_PASSANT (allowed, depth 0)

Moves (SAN): `23... bxa3 24. bxa3`

FEN (line start): `r2r2k1/2R2p1p/4pbp1/p7/Pp1P4/1B2P3/1P3PPP/2R3K1 b - a3 0 23`

Game (full game at ply): http://localhost:5173/analysis?game_id=684378&ply=44

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2r2k1/2R2p1p/4pbp1/p7/Pp1P4/1B2P3/1P3PPP/2R3K1%20b%20-%20a3%200%2023

#### Case 845 — CLEARANCE (allowed, depth 10)

Moves (SAN): `2... exd4 3. Qxd4 Nc6 4. Qd1 Nf6 5. Nc3 Bb4 6. Bd2`

FEN (line start): `rnbqkbnr/pppp1ppp/8/4p3/2PP4/8/PP2PPPP/RNBQKBNR b - - 0 2`

Game (full game at ply): http://localhost:5173/analysis?game_id=684384&ply=2

FEN (free-play from line start): http://localhost:5173/analysis?fen=rnbqkbnr/pppp1ppp/8/4p3/2PP4/8/PP2PPPP/RNBQKBNR%20b%20-%20-%200%202

#### Case 846 — SKEWER (allowed, depth 2)

Moves (SAN): `22... Rae8 23. Nc3 Rxe3 24. Nb5 Rfe8 25. Nxc7 Re1+ 26. Rxe1 Rxe1+ 27. Kf2 Rc1`

FEN (line start): `r4r2/ppp2pk1/3p2pp/8/2P1NP2/P3P2P/1P4P1/3R2K1 b - - 0 22`

Game (full game at ply): http://localhost:5173/analysis?game_id=684384&ply=42

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4r2/ppp2pk1/3p2pp/8/2P1NP2/P3P2P/1P4P1/3R2K1%20b%20-%20-%200%2022

#### Case 847 — CLEARANCE (missed, depth 10)

Moves (SAN): `28. Ne4 g6 29. g3 h6 30. Bb3 Rf5 31. Rxf5 gxf5 32. Nc5 Bxc5 33. Re8+ Kxd7`

FEN (line start): `1r1k1r2/p2P2pp/1b6/3R4/2B5/2N5/5PPP/4R1K1 w - - 0 28`

Game (full game at ply): http://localhost:5173/analysis?game_id=684393&ply=54

FEN (free-play from line start): http://localhost:5173/analysis?fen=1r1k1r2/p2P2pp/1b6/3R4/2B5/2N5/5PPP/4R1K1%20w%20-%20-%200%2028

#### Case 848 — SKEWER (missed, depth 2)

Moves (SAN): `11. Rb1 Qa3 12. Rxb7 e6 13. c5 Ne4 14. Rb3 Qa5`

FEN (line start): `r3kb1r/pp2ppp1/2p2n1p/3p4/2PP4/2NQPN2/Pq3PPP/R3K2R w - - 0 11`

Game (full game at ply): http://localhost:5173/analysis?game_id=684394&ply=20

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3kb1r/pp2ppp1/2p2n1p/3p4/2PP4/2NQPN2/Pq3PPP/R3K2R%20w%20-%20-%200%2011

#### Case 849 — SACRIFICE (missed, depth 4)

Moves (SAN): `13. cxd5 Nxc3 14. Rxb7 cxd5 15. Ne5 g6 16. Rfb1 Rd8 17. R7b3 Qd6 18. Rxc3 Bg7`

FEN (line start): `r3kb1r/pp2ppp1/2p4p/3p4/2PPn3/q1NQPN2/P4PPP/1R3RK1 w - - 0 13`

Game (full game at ply): http://localhost:5173/analysis?game_id=684394&ply=24

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3kb1r/pp2ppp1/2p4p/3p4/2PPn3/q1NQPN2/P4PPP/1R3RK1%20w%20-%20-%200%2013

#### Case 850 — SKEWER (missed, depth 10)

Moves (SAN): `20. Ne5+ Kc7 21. Qb1 c5 22. e4 Qxd4 23. Nxf7 Kd7 24. Rd8+ Ke6 25. Rxd4 Kxf7`

FEN (line start): `1R3b1r/p2kppp1/2p4p/3q4/3PQ3/4PN2/5PPP/6K1 w - - 0 20`

Game (full game at ply): http://localhost:5173/analysis?game_id=684394&ply=38

FEN (free-play from line start): http://localhost:5173/analysis?fen=1R3b1r/p2kppp1/2p4p/3q4/3PQ3/4PN2/5PPP/6K1%20w%20-%20-%200%2020

#### Case 851 — CLEARANCE (allowed, depth 4)

Moves (SAN): `10... Bb4+ 11. Nd2 Bg4 12. f3 Rad8 13. Bd3 Rxd3 14. cxd3 Bxd2+ 15. Kf2 Bc1+ 16. Kg3`

FEN (line start): `r1b2rk1/ppN2ppp/2n5/2b5/8/4PN2/PqP2PPP/R2QKB1R b - - 0 10`

Game (full game at ply): http://localhost:5173/analysis?game_id=684406&ply=18

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1b2rk1/ppN2ppp/2n5/2b5/8/4PN2/PqP2PPP/R2QKB1R%20b%20-%20-%200%2010

#### Case 852 — SACRIFICE (missed, depth 4)

Moves (SAN): `16. Ke3 Qb6 17. Ke2 Qxc7 18. Kf1 Rad8 19. h4 Bxd3+ 20. cxd3 Rxd3 21. Qe2 h6`

FEN (line start): `r5k1/ppN2ppp/8/5b2/3r4/3B4/PqPK1PPP/R2Q3R w - - 0 16`

Game (full game at ply): http://localhost:5173/analysis?game_id=684406&ply=30

FEN (free-play from line start): http://localhost:5173/analysis?fen=r5k1/ppN2ppp/8/5b2/3r4/3B4/PqPK1PPP/R2Q3R%20w%20-%20-%200%2016

#### Case 853 — CLEARANCE (missed, depth 4)

Moves (SAN): `15... h5 16. h3 Qf6 17. Qe2 Rfd8 18. Rfd1 Rd7 19. Rd2 b5 20. Rad1 Rad8 21. f4`

FEN (line start): `r2q1rk1/pp3ppp/4p1n1/3p4/2p5/2P1PPB1/PPQ2P1P/R4RK1 b - - 0 15`

Game (full game at ply): http://localhost:5173/analysis?game_id=684409&ply=29

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2q1rk1/pp3ppp/4p1n1/3p4/2p5/2P1PPB1/PPQ2P1P/R4RK1%20b%20-%20-%200%2015

#### Case 854 — PIN (allowed, depth 8)

Moves (SAN): `29. Rxf7+ Kh6 30. Qe5 g5 31. Qxe6+ Rg6 32. fxg5+ Qxg5 33. hxg5+ Kxg5 34. Qe7+ Rf6`

FEN (line start): `1r1q2r1/1pR2p1k/p3p1p1/P6p/4PP1P/2Q3B1/1P3P2/4R1K1 w - - 1 29`

Game (full game at ply): http://localhost:5173/analysis?game_id=684409&ply=55

FEN (free-play from line start): http://localhost:5173/analysis?fen=1r1q2r1/1pR2p1k/p3p1p1/P6p/4PP1P/2Q3B1/1P3P2/4R1K1%20w%20-%20-%201%2029

#### Case 855 — PIN (missed, depth 10)

Moves (SAN): `45... Ra2 46. f5 e5 47. Rd5 e4 48. Rd6+ Kg7 49. fxg6 Ra3 50. Be5+ Kg8 51. Rf6`

FEN (line start): `5r2/PR1R1p2/4pkp1/7p/5P1P/5PBK/8/r7 b - - 0 45`

Game (full game at ply): http://localhost:5173/analysis?game_id=684409&ply=89

FEN (free-play from line start): http://localhost:5173/analysis?fen=5r2/PR1R1p2/4pkp1/7p/5P1P/5PBK/8/r7%20b%20-%20-%200%2045

#### Case 856 — PIN (missed, depth 4)

Moves (SAN): `5... Qh4+ 6. Ke2 Qxe4+ 7. Be3 Bc5 8. Qd3 Qxe3+ 9. Qxe3 Bxe3 10. Kxe3 cxd5 11. Nf3`

FEN (line start): `rnbqkbnr/pp3ppp/2p5/3Pp3/4P3/8/PPP3PP/RNBQKBNR b - - 0 5`

Game (full game at ply): http://localhost:5173/analysis?game_id=684410&ply=9

FEN (free-play from line start): http://localhost:5173/analysis?fen=rnbqkbnr/pp3ppp/2p5/3Pp3/4P3/8/PPP3PP/RNBQKBNR%20b%20-%20-%200%205

#### Case 857 — CLEARANCE (allowed, depth 4)

Moves (SAN): `15. Kd2 Rd8 16. Qe1 Qf6 17. Rd1 cxd5 18. Nxd5 Nxd5 19. exd5 Rxd5+ 20. Bd3 Nc6`

FEN (line start): `rn3rk1/pp3pp1/2p4p/3Pp3/4Pn1q/2N2P1P/PPP1K3/R2Q1B1R w - - 1 15`

Game (full game at ply): http://localhost:5173/analysis?game_id=684410&ply=27

FEN (free-play from line start): http://localhost:5173/analysis?fen=rn3rk1/pp3pp1/2p4p/3Pp3/4Pn1q/2N2P1P/PPP1K3/R2Q1B1R%20w%20-%20-%201%2015

#### Case 858 — SACRIFICE (allowed, depth 2)

Moves (SAN): `19. h4 Nxd5+ 20. Kf2 Qf6 21. exd5 Nd4 22. Qe4 Qb6 23. b4 a5 24. bxa5 Qxa5`

FEN (line start): `r2r2k1/pp3pp1/2n4p/3Np1q1/2P1Pn2/4KP1P/PP6/R3QB1R w - - 1 19`

Game (full game at ply): http://localhost:5173/analysis?game_id=684410&ply=35

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2r2k1/pp3pp1/2n4p/3Np1q1/2P1Pn2/4KP1P/PP6/R3QB1R%20w%20-%20-%201%2019

#### Case 859 — ATTRACTION (missed, depth 8)

Moves (SAN): `40... Ke7 41. Ke2 h4 42. Kf1 h3 43. Rd1 h2 44. Kg2 h1=Q+ 45. Kxh1 Qh8+ 46. Kg2`

FEN (line start): `3q4/pp1P4/4kp2/3Rp2p/1P2P1P1/P3KP2/8/8 b - - 0 40`

Game (full game at ply): http://localhost:5173/analysis?game_id=684410&ply=79

FEN (free-play from line start): http://localhost:5173/analysis?fen=3q4/pp1P4/4kp2/3Rp2p/1P2P1P1/P3KP2/8/8%20b%20-%20-%200%2040

#### Case 860 — FORK (missed, depth 0)

Moves (SAN): `17... Bb3 18. Nc3 Bxd1 19. Nxd1 Nd4 20. Nxd4 Bxd4 21. Ne3 Bxe3 22. Bxe3 Rfd8 23. Re1`

FEN (line start): `r4rk1/bp3ppp/p1n1b3/4Pp2/N4B2/P4N2/1P3PPP/3R1RK1 b - - 0 17`

Game (full game at ply): http://localhost:5173/analysis?game_id=684414&ply=33

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4rk1/bp3ppp/p1n1b3/4Pp2/N4B2/P4N2/1P3PPP/3R1RK1%20b%20-%20-%200%2017

#### Case 861 — PIN (missed, depth 2)

Moves (SAN): `16... Qe6+ 17. Qe3 f4 18. Qe2 Bd6`

FEN (line start): `r3kb1r/1p3ppp/pq6/3p1p2/1P1B1Q2/P1N4P/2P2PP1/R3K2R b - - 0 16`

Game (full game at ply): http://localhost:5173/analysis?game_id=684420&ply=31

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3kb1r/1p3ppp/pq6/3p1p2/1P1B1Q2/P1N4P/2P2PP1/R3K2R%20b%20-%20-%200%2016

#### Case 862 — CLEARANCE (missed, depth 8)

Moves (SAN): `11... Nfd7 12. Rd2 h6 13. Bf4 Nb6 14. c4 Na6 15. Be2 Rd8 16. Be3 Rxd2 17. Kxd2`

FEN (line start): `rn2k2r/pp3ppp/2p1pnb1/4P1B1/7P/6N1/PPP2PP1/3RKB1R b - - 0 11`

Game (full game at ply): http://localhost:5173/analysis?game_id=684421&ply=21

FEN (free-play from line start): http://localhost:5173/analysis?fen=rn2k2r/pp3ppp/2p1pnb1/4P1B1/7P/6N1/PPP2PP1/3RKB1R%20b%20-%20-%200%2011

#### Case 863 — PIN (allowed, depth 6)

Moves (SAN): `12. Qg4 Qe5 13. Rfe1 h5 14. Rxe5 hxg4 15. Nxd5 Rd8 16. Ne3 Nf6 17. Rc5 Rh5`

FEN (line start): `r3k1nr/1p3ppp/p2qp3/3p4/3n4/2NB4/PPP2PPP/R2Q1RK1 w - - 0 12`

Game (full game at ply): http://localhost:5173/analysis?game_id=684425&ply=21

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3k1nr/1p3ppp/p2qp3/3p4/3n4/2NB4/PPP2PPP/R2Q1RK1%20w%20-%20-%200%2012

#### Case 864 — CLEARANCE (allowed, depth 6)

Moves (SAN): `18. Rxe4 Qg7 19. Rg4 Qf8 20. Qf2 e5 21. Rh4 f5 22. Rh5 Kb8 23. Rxf5 Qg7`

FEN (line start): `2kr3r/1p3p1p/p1n1p3/3p2q1/4n2Q/2NB1P2/PPP3PP/R3R1K1 w - - 1 18`

Game (full game at ply): http://localhost:5173/analysis?game_id=684425&ply=33

FEN (free-play from line start): http://localhost:5173/analysis?fen=2kr3r/1p3p1p/p1n1p3/3p2q1/4n2Q/2NB1P2/PPP3PP/R3R1K1%20w%20-%20-%201%2018

#### Case 865 — SKEWER (missed, depth 2)

Moves (SAN): `26... Rg1+ 27. Kf2 Rxe1 28. Rxe1 Nxe1 29. Kxe1 Rc8 30. Nc3 h4 31. Kf2 f5 32. Bf3`

FEN (line start): `1k4rr/1p3p2/p3p3/7p/N3B3/5n2/PP5P/2R1RK2 b - - 0 26`

Game (full game at ply): http://localhost:5173/analysis?game_id=684425&ply=51

FEN (free-play from line start): http://localhost:5173/analysis?fen=1k4rr/1p3p2/p3p3/7p/N3B3/5n2/PP5P/2R1RK2%20b%20-%20-%200%2026

#### Case 866 — FORK (allowed, depth 0)

Moves (SAN): `17... Qxb4+ 18. Ke2 Qxb6 19. Rhb1 Qd6 20. Ra6 Qe7 21. Ne5 Rc8 22. Qd1`

FEN (line start): `r3k2r/p2bqppp/1B2p3/3p3n/1P1P4/3BPN2/2Q2PPP/R3K2R b - - 0 17`

Game (full game at ply): http://localhost:5173/analysis?game_id=684428&ply=32

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3k2r/p2bqppp/1B2p3/3p3n/1P1P4/3BPN2/2Q2PPP/R3K2R%20b%20-%20-%200%2017

#### Case 867 — CLEARANCE (missed, depth 4)

Moves (SAN): `17. Ne5`

FEN (line start): `r3k2r/p1Bbqppp/1p2p3/3p3n/1P1P4/3BPN2/2Q2PPP/R3K2R w - - 0 17`

Game (full game at ply): http://localhost:5173/analysis?game_id=684428&ply=32

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3k2r/p1Bbqppp/1p2p3/3p3n/1P1P4/3BPN2/2Q2PPP/R3K2R%20w%20-%20-%200%2017

#### Case 868 — CLEARANCE (allowed, depth 10)

Moves (SAN): `13... Nxd3 14. Qxd3 Re8 15. Rfd1 f6 16. Bf4 cxd4 17. exd4 Nb6 18. Bc7 Bd7 19. h3`

FEN (line start): `r1b2rk1/pp1n1ppp/4p3/q1p3B1/1nPP4/PQ1BPN2/5PPP/R4RK1 b - - 0 13`

Game (full game at ply): http://localhost:5173/analysis?game_id=684434&ply=24

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1b2rk1/pp1n1ppp/4p3/q1p3B1/1nPP4/PQ1BPN2/5PPP/R4RK1%20b%20-%20-%200%2013

#### Case 869 — CLEARANCE (allowed, depth 6)

Moves (SAN): `23... Nb6 24. Qa7+ Kc8 25. Qa6+ Kd7 26. Ra5 Rb8 27. Qb5+ Kd8 28. Qxf5 hxg3 29. fxg3`

FEN (line start): `1k1r3r/2pnq3/Q7/5pp1/R2Pp2p/P3P1P1/1P3PP1/5RK1 b - - 1 23`

Game (full game at ply): http://localhost:5173/analysis?game_id=684442&ply=44

FEN (free-play from line start): http://localhost:5173/analysis?fen=1k1r3r/2pnq3/Q7/5pp1/R2Pp2p/P3P1P1/1P3PP1/5RK1%20b%20-%20-%201%2023

#### Case 870 — PIN (allowed, depth 10)

Moves (SAN): `25... hxg3 26. fxg3 Qd6 27. Rxf5 Rdf8 28. Qa5 Qh6 29. a4 Qh1+ 30. Kf2 Qh7 31. Rxf8+`

FEN (line start): `2kr3r/Q1p1q3/1n6/5pp1/1R1Pp2p/P3P1P1/1P3PP1/5RK1 b - - 1 25`

Game (full game at ply): http://localhost:5173/analysis?game_id=684442&ply=48

FEN (free-play from line start): http://localhost:5173/analysis?fen=2kr3r/Q1p1q3/1n6/5pp1/1R1Pp2p/P3P1P1/1P3PP1/5RK1%20b%20-%20-%201%2025

#### Case 871 — PIN (missed, depth 10)

Moves (SAN): `25. Qa6+ Kd7 26. Ra5 Rb8 27. Qb5+ Kd8 28. Qxf5 hxg3 29. fxg3 Nc4 30. Ra8 Rxa8`

FEN (line start): `2kr3r/Q1p1q3/1n6/5pp1/R2Pp2p/P3P1P1/1P3PP1/5RK1 w - - 0 25`

Game (full game at ply): http://localhost:5173/analysis?game_id=684442&ply=48

FEN (free-play from line start): http://localhost:5173/analysis?fen=2kr3r/Q1p1q3/1n6/5pp1/R2Pp2p/P3P1P1/1P3PP1/5RK1%20w%20-%20-%200%2025

#### Case 872 — CLEARANCE (missed, depth 4)

Moves (SAN): `19. dxc6 Bxc6`

FEN (line start): `r2q1r2/1b3pk1/1ppp1npp/p2Pp3/2P5/1P2QN1P/P3BPP1/R3K2R w - - 0 19`

Game (full game at ply): http://localhost:5173/analysis?game_id=684448&ply=36

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2q1r2/1b3pk1/1ppp1npp/p2Pp3/2P5/1P2QN1P/P3BPP1/R3K2R%20w%20-%20-%200%2019

#### Case 873 — INTERMEZZO (missed, depth 10)

Moves (SAN): `21. f4 d4 22. Qd3 Bc8`

FEN (line start): `r2q1r2/1b3pk1/1p1p1np1/p2pp1Np/2P4P/1P2Q3/P3BPP1/R3K2R w - - 0 21`

Game (full game at ply): http://localhost:5173/analysis?game_id=684448&ply=40

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2q1r2/1b3pk1/1p1p1np1/p2pp1Np/2P4P/1P2Q3/P3BPP1/R3K2R%20w%20-%20-%200%2021

#### Case 874 — CLEARANCE (allowed, depth 2)

Moves (SAN): `23. Be5 h5 24. Re4 Nc6 25. Bf6 Rd6 26. Rc1 Nfxd4 27. Re3 e5 28. Bxe5 Nxe5`

FEN (line start): `2rr2k1/p4p1p/4p1p1/5n2/1nBP1BR1/1P3P2/1K3P1P/6R1 w - - 0 23`

Game (full game at ply): http://localhost:5173/analysis?game_id=684449&ply=43

FEN (free-play from line start): http://localhost:5173/analysis?fen=2rr2k1/p4p1p/4p1p1/5n2/1nBP1BR1/1P3P2/1K3P1P/6R1%20w%20-%20-%200%2023

#### Case 875 — SKEWER (allowed, depth 2)

Moves (SAN): `29. Rh6+ Kg5 30. Rxc6 Re8 31. cxb5 Re2+ 32. Kd1 Rxf2 33. a4 Ra2 34. Ke1 Kg4`

FEN (line start): `3r4/p7/2p2k2/1p3p1R/2P2p2/2P5/P1K2P2/8 w - - 0 29`

Game (full game at ply): http://localhost:5173/analysis?game_id=684456&ply=55

FEN (free-play from line start): http://localhost:5173/analysis?fen=3r4/p7/2p2k2/1p3p1R/2P2p2/2P5/P1K2P2/8%20w%20-%20-%200%2029

#### Case 876 — CAPTURING_DEFENDER (missed, depth 6)

Moves (SAN): `5... Qa5+ 6. Bd2 Qf5 7. Be2 Bxf3 8. Bxf3 Nxd4 9. Bxb7 Nc2+ 10. Kf1 Qd3+ 11. Qe2`

FEN (line start): `r3kbnr/ppp1pppp/2n5/3q4/2PP2b1/5N2/PP3PPP/RNBQKB1R b - - 0 5`

Game (full game at ply): http://localhost:5173/analysis?game_id=684458&ply=9

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3kbnr/ppp1pppp/2n5/3q4/2PP2b1/5N2/PP3PPP/RNBQKB1R%20b%20-%20-%200%205

#### Case 877 — DISCOVERED_ATTACK (allowed, depth 1)

Moves (SAN): `11... Nxd5 12. cxd5 Bxg5 13. Qc2 h6`

FEN (line start): `r2qk2r/pp2bppp/5n2/2pPp1B1/2P3b1/2NB4/PP1Q1PPP/R3K2R b - - 1 11`

Game (full game at ply): http://localhost:5173/analysis?game_id=684466&ply=20

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qk2r/pp2bppp/5n2/2pPp1B1/2P3b1/2NB4/PP1Q1PPP/R3K2R%20b%20-%20-%201%2011

#### Case 878 — CLEARANCE (allowed, depth 2)

Moves (SAN): `29. Qc2 Qb6 30. Rb3 Qd4 31. Rc3`

FEN (line start): `rr6/ppk5/2p1pb1p/3p4/3q1P2/1QRB2P1/PP5P/1KR5 w - - 1 29`

Game (full game at ply): http://localhost:5173/analysis?game_id=684473&ply=55

FEN (free-play from line start): http://localhost:5173/analysis?fen=rr6/ppk5/2p1pb1p/3p4/3q1P2/1QRB2P1/PP5P/1KR5%20w%20-%20-%201%2029

#### Case 879 — DISCOVERED_ATTACK (missed, depth 1)

Moves (SAN): `28... Qb6 29. Qa3 Bxc3 30. Qxc3 Rad8 31. f5 d4 32. Qe1 Kb8 33. Qxe6 Qa5 34. Rf1`

FEN (line start): `r6r/ppk5/2p1pb1p/3p4/3q1P2/1QRB2P1/PP5P/1KR5 b - - 0 28`

Game (full game at ply): http://localhost:5173/analysis?game_id=684473&ply=55

FEN (free-play from line start): http://localhost:5173/analysis?fen=r6r/ppk5/2p1pb1p/3p4/3q1P2/1QRB2P1/PP5P/1KR5%20b%20-%20-%200%2028

#### Case 880 — PIN (allowed, depth 0)

Moves (SAN): `31. Qxd5 Bxc3 32. Qf7+ Kb6 33. Qb3+ Kc7 34. Qf7+`

FEN (line start): `rr6/ppk5/2p2b1p/3p1B2/8/1QR3P1/PP3q1P/1KR5 w - - 1 31`

Game (full game at ply): http://localhost:5173/analysis?game_id=684473&ply=59

FEN (free-play from line start): http://localhost:5173/analysis?fen=rr6/ppk5/2p2b1p/3p1B2/8/1QR3P1/PP3q1P/1KR5%20w%20-%20-%201%2031

#### Case 881 — CLEARANCE (missed, depth 4)

Moves (SAN): `30... Rd8 31. Qc2 Rd6 32. a3 Re8 33. Rb3 Bg5 34. Rd1 Qe5 35. h4 Bd8 36. Ka2`

FEN (line start): `rr6/ppk5/2p2b1p/3p1B2/3q4/1QR3P1/PP5P/1KR5 b - - 0 30`

Game (full game at ply): http://localhost:5173/analysis?game_id=684473&ply=59

FEN (free-play from line start): http://localhost:5173/analysis?fen=rr6/ppk5/2p2b1p/3p1B2/3q4/1QR3P1/PP5P/1KR5%20b%20-%20-%200%2030

#### Case 882 — SACRIFICE (missed, depth 4)

Moves (SAN): `40... Kc5 41. Qxe6 Rxa5 42. Rxa5+ Kxb6 43. Rxd5 Qh2+ 44. Rd2 Qxh4 45. Qe3+ Kb5 46. Qd3+`

FEN (line start): `1q6/5Q1p/rPpkp1p1/P2p2P1/7P/2P2P2/2K5/R7 b - - 0 40`

Game (full game at ply): http://localhost:5173/analysis?game_id=684474&ply=79

FEN (free-play from line start): http://localhost:5173/analysis?fen=1q6/5Q1p/rPpkp1p1/P2p2P1/7P/2P2P2/2K5/R7%20b%20-%20-%200%2040

#### Case 883 — PROMOTION (allowed, depth 0)

Moves (SAN): `51. a8=Q Qf2+ 52. Kd1 Qxf3+ 53. Ke1 Qg3+ 54. Ke2 Qg2+ 55. Ke1 Qh1+ 56. Kd2 Qh2+`

FEN (line start): `3r4/PP2k2p/1q2p1p1/3p2P1/2p4P/2P2P2/2K5/R7 w - - 1 51`

Game (full game at ply): http://localhost:5173/analysis?game_id=684474&ply=99

FEN (free-play from line start): http://localhost:5173/analysis?fen=3r4/PP2k2p/1q2p1p1/3p2P1/2p4P/2P2P2/2K5/R7%20w%20-%20-%201%2051

#### Case 884 — FORK (missed, depth 6)

Moves (SAN): `50... Qf2+ 51. Kc1 Qe3+ 52. Kc2 Qd3+ 53. Kc1 Qxc3+ 54. Kd1 Qxa1+ 55. Ke2 Qxa7 56. h5`

FEN (line start): `1r6/PP2k2p/1q2p1p1/3p2P1/2p4P/2P2P2/2K5/R7 b - - 0 50`

Game (full game at ply): http://localhost:5173/analysis?game_id=684474&ply=99

FEN (free-play from line start): http://localhost:5173/analysis?fen=1r6/PP2k2p/1q2p1p1/3p2P1/2p4P/2P2P2/2K5/R7%20b%20-%20-%200%2050

#### Case 885 — SKEWER (allowed, depth 2)

Moves (SAN): `12... Bg4 13. Qg3 Bxd1 14. Rxd1 Qe8 15. Nd5 Nxd5 16. Bxa5 Nb6 17. Bc3 f6 18. b3`

FEN (line start): `r1bq1rk1/pp3ppp/3p1n2/b1p5/4P3/P1NB1Q2/1PPB1PPP/3R1RK1 b - - 1 12`

Game (full game at ply): http://localhost:5173/analysis?game_id=684479&ply=22

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1bq1rk1/pp3ppp/3p1n2/b1p5/4P3/P1NB1Q2/1PPB1PPP/3R1RK1%20b%20-%20-%201%2012

#### Case 886 — SKEWER (allowed, depth 2)

Moves (SAN): `13... Bg4 14. Qg3 Bxd1 15. Rxd1 Re8 16. Bc4 Nxe4 17. Bxf7+ Kh8 18. Nxe4 Rxe4 19. Be3`

FEN (line start): `r2q1rk1/pp3ppp/3pbn2/b1p5/4P3/P1NB1Q2/1PPB1PPP/3RR1K1 b - - 1 13`

Game (full game at ply): http://localhost:5173/analysis?game_id=684479&ply=24

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2q1rk1/pp3ppp/3pbn2/b1p5/4P3/P1NB1Q2/1PPB1PPP/3RR1K1%20b%20-%20-%201%2013

#### Case 887 — SKEWER (allowed, depth 2)

Moves (SAN): `23... Rd8 24. Qg3 Rxd2 25. Ne3 Bxe3 26. fxe3 Rxc2 27. e4 Kh8 28. Qe3 h5 29. b3`

FEN (line start): `r3q1k1/p4ppp/1b6/8/8/P2Q3P/1PPB1PP1/3N2K1 b - - 0 23`

Game (full game at ply): http://localhost:5173/analysis?game_id=684479&ply=44

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3q1k1/p4ppp/1b6/8/8/P2Q3P/1PPB1PP1/3N2K1%20b%20-%20-%200%2023

#### Case 888 — MATE (allowed, depth 8)

Moves (SAN): `31... Qf4+ 32. g3 Rd2+ 33. Qg2 Rxg2+ 34. Kxg2 Qf2+ 35. Kh1 Qg1#`

FEN (line start): `3r1k2/pQ2Nppp/1b6/8/8/P6P/1PP2qPK/8 b - - 1 31`

Game (full game at ply): http://localhost:5173/analysis?game_id=684479&ply=60

FEN (free-play from line start): http://localhost:5173/analysis?fen=3r1k2/pQ2Nppp/1b6/8/8/P6P/1PP2qPK/8%20b%20-%20-%201%2031

#### Case 889 — SACRIFICE (missed, depth 8)

Moves (SAN): `31. Qe5 f6 32. Qc3 Qf4+ 33. Qg3 Qxg3+ 34. Kxg3 Kxe7 35. a4 Rd2 36. b4 Rxc2`

FEN (line start): `3r1k2/p1Q1Nppp/1b6/8/8/P6P/1PP2qPK/8 w - - 0 31`

Game (full game at ply): http://localhost:5173/analysis?game_id=684479&ply=60

FEN (free-play from line start): http://localhost:5173/analysis?fen=3r1k2/p1Q1Nppp/1b6/8/8/P6P/1PP2qPK/8%20w%20-%20-%200%2031

#### Case 890 — ATTRACTION (allowed, depth 0)

Moves (SAN): `19... Bxf2+ 20. Kxf2 Qc5+ 21. Re3 Qxc4 22. Kg1 Qxc2 23. Rf1 Ne5 24. Qg3 Re6 25. Rc3`

FEN (line start): `r3r2k/1pp4p/p1np1ppB/2b1q3/2B1P1Q1/P6P/1PP2PP1/R3R1K1 b - - 1 19`

Game (full game at ply): http://localhost:5173/analysis?game_id=684488&ply=36

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3r2k/1pp4p/p1np1ppB/2b1q3/2B1P1Q1/P6P/1PP2PP1/R3R1K1%20b%20-%20-%201%2019

#### Case 891 — PIN (missed, depth 4)

Moves (SAN): `36. Be4+ Ng6 37. Rb8 Re7 38. Rxb7 Kg8 39. Rxe7 Nxe7 40. b4 Kf7 41. Bb7 Kf6`

FEN (line start): `3R4/1p4rk/p6p/3Bn1pp/8/P6P/1PP3PK/8 w - - 0 36`

Game (full game at ply): http://localhost:5173/analysis?game_id=684488&ply=70

FEN (free-play from line start): http://localhost:5173/analysis?fen=3R4/1p4rk/p6p/3Bn1pp/8/P6P/1PP3PK/8%20w%20-%20-%200%2036

#### Case 892 — CLEARANCE (allowed, depth 2)

Moves (SAN): `29... Bg7 30. Rd1 Rd8 31. Bd5 b5 32. Bxf7 b4 33. Be6+ Kc7 34. Nd5+ Kb8 35. Nxb4`

FEN (line start): `2k2br1/pp3p2/b5p1/7p/2pR1P2/2N1PB2/1P3PKP/8 b - - 1 29`

Game (full game at ply): http://localhost:5173/analysis?game_id=684506&ply=56

FEN (free-play from line start): http://localhost:5173/analysis?fen=2k2br1/pp3p2/b5p1/7p/2pR1P2/2N1PB2/1P3PKP/8%20b%20-%20-%201%2029

#### Case 893 — CLEARANCE (allowed, depth 10)

Moves (SAN): `32... b4 33. Ne2 Bg7 34. Rf4 Rc5 35. Be4 Bxb2 36. Rxf7 c3 37. Bc2 Bc4 38. Rf4`

FEN (line start): `2k2b2/p4p2/b1B5/1p4rp/2pR4/2N1P3/1P3P1P/5K2 b - - 1 32`

Game (full game at ply): http://localhost:5173/analysis?game_id=684506&ply=62

FEN (free-play from line start): http://localhost:5173/analysis?fen=2k2b2/p4p2/b1B5/1p4rp/2pR4/2N1P3/1P3P1P/5K2%20b%20-%20-%201%2032

#### Case 894 — SACRIFICE (missed, depth 2)

Moves (SAN): `33. Rd7 bxc3 34. bxc3 Rg6 35. Rxf7 Rxc6 36. Rxf8+ Kc7 37. f4 Bb7 38. e4 a5`

FEN (line start): `2k2b2/p4p2/b1B5/6rp/1ppR4/2N1P3/1P3P1P/5K2 w - - 0 33`

Game (full game at ply): http://localhost:5173/analysis?game_id=684506&ply=64

FEN (free-play from line start): http://localhost:5173/analysis?fen=2k2b2/p4p2/b1B5/6rp/1ppR4/2N1P3/1P3P1P/5K2%20w%20-%20-%200%2033

#### Case 895 — CLEARANCE (allowed, depth 10)

Moves (SAN): `20. gxh3 Qg5 21. h4 Qg6 22. c3 Bg4 23. f3 Bh5 24. Kf2 a5 25. Rg1 f6`

FEN (line start): `2r2rk1/4qpp1/p3p2p/1p1pPb2/8/PB4Nn/1PP2PP1/R2QR1K1 w - - 0 20`

Game (full game at ply): http://localhost:5173/analysis?game_id=684513&ply=37

FEN (free-play from line start): http://localhost:5173/analysis?fen=2r2rk1/4qpp1/p3p2p/1p1pPb2/8/PB4Nn/1PP2PP1/R2QR1K1%20w%20-%20-%200%2020

#### Case 896 — DISCOVERED_ATTACK (allowed, depth 3)

Moves (SAN): `16. Bxd4 Qd6 17. cxd5 Nxd5 18. Bxa6 bxa6 19. Rc1 Re6 20. Qf3 h6 21. Rc4 Rg6`

FEN (line start): `r3r1k1/ppq2ppp/n1p2n2/3p4/2Pp4/P1B1P2P/1P2BPP1/R2Q1RK1 w - - 0 16`

Game (full game at ply): http://localhost:5173/analysis?game_id=684525&ply=29

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3r1k1/ppq2ppp/n1p2n2/3p4/2Pp4/P1B1P2P/1P2BPP1/R2Q1RK1%20w%20-%20-%200%2016

#### Case 897 — FORK (allowed, depth 0)

Moves (SAN): `7. Qa4+ Nc6 8. Nd5 Bc5 9. b4 Bb6 10. Nxb6 cxb6 11. Bb2 Qe7`

FEN (line start): `rnbqk2r/ppp3pp/3p1n2/5pN1/1bP1p3/2N1P3/PP1PBPPP/R1BQK2R w - - 0 7`

Game (full game at ply): http://localhost:5173/analysis?game_id=684526&ply=11

FEN (free-play from line start): http://localhost:5173/analysis?fen=rnbqk2r/ppp3pp/3p1n2/5pN1/1bP1p3/2N1P3/PP1PBPPP/R1BQK2R%20w%20-%20-%200%207

#### Case 898 — PIN (allowed, depth 4)

Moves (SAN): `28. Rf1 Rf8 29. Qh7+ Kf7 30. Rxf6+ Kxf6 31. Rf3+ Ke7 32. Qxg7+ Kd6 33. Rxf8 Rxf8`

FEN (line start): `2r1r1k1/6p1/1q2pbQ1/p2p4/1p1P4/1Pp1B2R/P5PP/R6K w - - 1 28`

Game (full game at ply): http://localhost:5173/analysis?game_id=684533&ply=53

FEN (free-play from line start): http://localhost:5173/analysis?fen=2r1r1k1/6p1/1q2pbQ1/p2p4/1p1P4/1Pp1B2R/P5PP/R6K%20w%20-%20-%201%2028

#### Case 899 — SACRIFICE (allowed, depth 10)

Moves (SAN): `31. Qd3 Qh5 32. Rgf3 c2 33. Bc1 Rc3 34. Qa6 Re8 35. Rxf6 gxf6 36. h3 Qg6`

FEN (line start): `2r2rk1/5qp1/4pbQ1/p2p4/1p1P1B2/1Pp3R1/P5PP/5R1K w - - 1 31`

Game (full game at ply): http://localhost:5173/analysis?game_id=684533&ply=59

FEN (free-play from line start): http://localhost:5173/analysis?fen=2r2rk1/5qp1/4pbQ1/p2p4/1p1P1B2/1Pp3R1/P5PP/5R1K%20w%20-%20-%201%2031

#### Case 900 — CLEARANCE (allowed, depth 10)

Moves (SAN): `14... Nd7 15. Rh3 Qe8 16. g4 g6 17. Rg3 fxg4 18. Nxg4 Rf8 19. Kh1 Bh4 20. Rg2`

FEN (line start): `rnb3k1/pp2b1pp/2p2r2/3pNp1q/3P1P2/2NBPR2/PPQ3PP/R5K1 b - - 1 14`

Game (full game at ply): http://localhost:5173/analysis?game_id=684535&ply=26

FEN (free-play from line start): http://localhost:5173/analysis?fen=rnb3k1/pp2b1pp/2p2r2/3pNp1q/3P1P2/2NBPR2/PPQ3PP/R5K1%20b%20-%20-%201%2014

#### Case 901 — PIN (allowed, depth 0)

Moves (SAN): `20... Rxf4 21. Na4 Rxa4 22. Qc2 Rg4 23. Qxc5 Rxg3 24. hxg3 Qxe5 25. Rf1 Bd7 26. e4`

FEN (line start): `r1b1qrk1/pp5p/2p3p1/2bpP3/5P2/2NBP1R1/PP2Q1PP/R5K1 b - - 1 20`

Game (full game at ply): http://localhost:5173/analysis?game_id=684535&ply=38

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1b1qrk1/pp5p/2p3p1/2bpP3/5P2/2NBP1R1/PP2Q1PP/R5K1%20b%20-%20-%201%2020

#### Case 902 — FORK (allowed, depth 2)

Moves (SAN): `19... Qxe3+ 20. Kh1 Nd2 21. Qc2 Nxd4 22. Qc5+ Kg8 23. fxg4 Qxd3 24. Rad1 Rad8 25. Qxc7`

FEN (line start): `r3rk2/ppp2pp1/2n4p/6q1/3Pn1bN/PQ1BPPB1/6PP/R4RK1 b - - 0 19`

Game (full game at ply): http://localhost:5173/analysis?game_id=684537&ply=36

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3rk2/ppp2pp1/2n4p/6q1/3Pn1bN/PQ1BPPB1/6PP/R4RK1%20b%20-%20-%200%2019

#### Case 903 — CLEARANCE (allowed, depth 10)

Moves (SAN): `22... Nxd4 23. Qb1 Rad8 24. f4 Bd5 25. Bb5 Nxb5 26. Qh7 Be4 27. f5 Rd3 28. Rf3`

FEN (line start): `r3rk2/ppp2pp1/2n1b2p/8/3P3N/P2BqPP1/2Q3PK/R4R2 b - - 1 22`

Game (full game at ply): http://localhost:5173/analysis?game_id=684537&ply=42

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3rk2/ppp2pp1/2n1b2p/8/3P3N/P2BqPP1/2Q3PK/R4R2%20b%20-%20-%201%2022

#### Case 904 — CLEARANCE (missed, depth 6)

Moves (SAN): `24. Qc3 Qe5 25. Rac1 c5 26. Bb1 b6 27. Qd3 g6 28. f4 Qh5 29. Qa6 Rad8`

FEN (line start): `r3r1k1/ppp2pp1/4b2p/2Q5/3n3N/P2BqPP1/6PK/R4R2 w - - 0 24`

Game (full game at ply): http://localhost:5173/analysis?game_id=684537&ply=46

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3r1k1/ppp2pp1/4b2p/2Q5/3n3N/P2BqPP1/6PK/R4R2%20w%20-%20-%200%2024

#### Case 905 — HANGING_PIECE (allowed, depth 0)

Moves (SAN): `17... Nxd3 18. Qe3 Bxd4 19. Qxd4 Nf4 20. Qe3 Qg5 21. Qf3 a4 22. Rae1 axb3 23. axb3`

FEN (line start): `r2q1rk1/1pp2pb1/3p2p1/p2Pn3/2PNPQ1p/1P1B3P/P4PP1/R4RK1 b - - 1 17`

Game (full game at ply): http://localhost:5173/analysis?game_id=684538&ply=32

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2q1rk1/1pp2pb1/3p2p1/p2Pn3/2PNPQ1p/1P1B3P/P4PP1/R4RK1%20b%20-%20-%201%2017

#### Case 906 — DISCOVERED_ATTACK (missed, depth 5)

Moves (SAN): `16. dxe5`

FEN (line start): `r1n1k2r/pp1bq1pp/5pn1/P2pp3/3P4/2PBPNB1/5PPP/R2Q1RK1 w - - 0 16`

Game (full game at ply): http://localhost:5173/analysis?game_id=684560&ply=30

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1n1k2r/pp1bq1pp/5pn1/P2pp3/3P4/2PBPNB1/5PPP/R2Q1RK1%20w%20-%20-%200%2016

#### Case 907 — EN_PASSANT (allowed, depth 2)

Moves (SAN): `21... Qxh4 22. f4 exf3 23. Rxf3`

FEN (line start): `r3k2r/1p1bq1pp/p2n4/P2P1p2/3Pp2B/4P2P/2B2PP1/R2Q1RK1 b - - 0 21`

Game (full game at ply): http://localhost:5173/analysis?game_id=684560&ply=40

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3k2r/1p1bq1pp/p2n4/P2P1p2/3Pp2B/4P2P/2B2PP1/R2Q1RK1%20b%20-%20-%200%2021

#### Case 908 — CLEARANCE (missed, depth 2)

Moves (SAN): `21. Qh5+ Ng6 22. Rfb1`

FEN (line start): `r3k2r/1p1bq1pp/p2n4/P2P1p2/3Pp2n/4P1BP/2B2PP1/R2Q1RK1 w - - 0 21`

Game (full game at ply): http://localhost:5173/analysis?game_id=684560&ply=40

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3k2r/1p1bq1pp/p2n4/P2P1p2/3Pp2n/4P1BP/2B2PP1/R2Q1RK1%20w%20-%20-%200%2021

#### Case 909 — CAPTURING_DEFENDER (allowed, depth 8)

Moves (SAN): `22... Qf6 23. Nce2 Kh8 24. Ra1 Rxa1 25. Rxa1 Nxc4 26. Ra7 Bxd5 27. Rxc7 Nd3 28. Bxd3`

FEN (line start): `r2q1r2/1bp3kp/1p1p4/1PnPnp2/2PNpQ2/2N4P/2B2PP1/4RRK1 b - - 1 22`

Game (full game at ply): http://localhost:5173/analysis?game_id=684562&ply=42

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2q1r2/1bp3kp/1p1p4/1PnPnp2/2PNpQ2/2N4P/2B2PP1/4RRK1%20b%20-%20-%201%2022

#### Case 910 — DISCOVERED_ATTACK (allowed, depth 7)

Moves (SAN): `26... Bxc6 27. dxc6 f4 28. Qh2 Qf6 29. Rc1 Nf3+ 30. gxf3 Qxc3 31. Qh1 Nd3 32. Kh2`

FEN (line start): `3q1r1k/2pb3p/1pNp4/1PnPnp2/2P1p3/2N3QP/2B2PP1/R5K1 b - - 1 26`

Game (full game at ply): http://localhost:5173/analysis?game_id=684562&ply=50

FEN (free-play from line start): http://localhost:5173/analysis?fen=3q1r1k/2pb3p/1pNp4/1PnPnp2/2P1p3/2N3QP/2B2PP1/R5K1%20b%20-%20-%201%2026

#### Case 911 — SACRIFICE (missed, depth 6)

Moves (SAN): `29. Ra7 f4 30. Qg4 e3 31. f3 Qxc3 32. Rxc7 Qe1+ 33. Kh2 Qg3+ 34. Qxg3 fxg3+`

FEN (line start): `5r1k/2p4p/1pPp1q2/2nP1p2/2n1p3/2N3QP/5PP1/R2B2K1 w - - 0 29`

Game (full game at ply): http://localhost:5173/analysis?game_id=684562&ply=56

FEN (free-play from line start): http://localhost:5173/analysis?fen=5r1k/2p4p/1pPp1q2/2nP1p2/2n1p3/2N3QP/5PP1/R2B2K1%20w%20-%20-%200%2029

#### Case 912 — CLEARANCE (allowed, depth 6)

Moves (SAN): `13... Qc7 14. Nxd7 Nxd7 15. Qb1 a6 16. Bg3 Qa7 17. Qa2 Bb7 18. f3 e5 19. e4`

FEN (line start): `r1bq1rk1/p2n1pp1/4pn1p/1p2N3/2pP3B/2P1P3/4BPPP/R2Q1RK1 b - - 1 13`

Game (full game at ply): http://localhost:5173/analysis?game_id=684581&ply=24

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1bq1rk1/p2n1pp1/4pn1p/1p2N3/2pP3B/2P1P3/4BPPP/R2Q1RK1%20b%20-%20-%201%2013

#### Case 913 — SKEWER (allowed, depth 2)

Moves (SAN): `10. c4 Nb6 11. Bxb7 Qxd4+ 12. Kh1 Qxd1 13. Rxd1 a6 14. Bxa8 Nxa8 15. b3 Nc6`

FEN (line start): `rn1qkb1r/pp3ppp/4p3/2pnP3/3P4/5B2/PPP3PP/RNBQ1RK1 w - - 0 10`

Game (full game at ply): http://localhost:5173/analysis?game_id=684584&ply=17

FEN (free-play from line start): http://localhost:5173/analysis?fen=rn1qkb1r/pp3ppp/4p3/2pnP3/3P4/5B2/PPP3PP/RNBQ1RK1%20w%20-%20-%200%2010

#### Case 914 — PIN (allowed, depth 6)

Moves (SAN): `12. Qh5 g6 13. Qf3 Qe7 14. Bxa8 cxd4 15. Bc6 Bg7 16. Bxd7+ Qxd7 17. Bf4`

FEN (line start): `r2qkb1r/pB1n1ppp/1n2p3/2p1P3/2PP4/8/PP4PP/RNBQ1RK1 w - - 1 12`

Game (full game at ply): http://localhost:5173/analysis?game_id=684584&ply=21

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qkb1r/pB1n1ppp/1n2p3/2p1P3/2PP4/8/PP4PP/RNBQ1RK1%20w%20-%20-%201%2012

#### Case 915 — CAPTURING_DEFENDER (missed, depth 4)

Moves (SAN): `21... Qf6 22. Qxf6 gxf6 23. Re4 Nxf3+ 24. Kg2 f5 25. Rb4 Ne5 26. Rdxb7 Rec8 27. Rd4`

FEN (line start): `r3r1k1/1p1R1ppp/p3p3/8/5Q1n/N4P2/1q3P1P/4R1K1 b - - 0 21`

Game (full game at ply): http://localhost:5173/analysis?game_id=684589&ply=41

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3r1k1/1p1R1ppp/p3p3/8/5Q1n/N4P2/1q3P1P/4R1K1%20b%20-%20-%200%2021

#### Case 916 — SKEWER (missed, depth 2)

Moves (SAN): `23... Rf8 24. Qxe6 Rxf3 25. Re2 Qc1+ 26. Re1 Qg5+ 27. Kh1 Rxf2 28. Qh3 Qc5 29. Red1`

FEN (line start): `r3r2k/1p1R1Qpp/p3p1n1/8/4R3/N4P2/1q3P1P/6K1 b - - 0 23`

Game (full game at ply): http://localhost:5173/analysis?game_id=684589&ply=45

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3r2k/1p1R1Qpp/p3p1n1/8/4R3/N4P2/1q3P1P/6K1%20b%20-%20-%200%2023

#### Case 917 — PIN (allowed, depth 6)

Moves (SAN): `16... Qxg2 17. Rf1 Rxb2`

FEN (line start): `1r3rk1/p1Q2pp1/4b1p1/4P1q1/8/P1N1P3/1P3PPP/R3K2R b - - 0 16`

Game (full game at ply): http://localhost:5173/analysis?game_id=684592&ply=30

FEN (free-play from line start): http://localhost:5173/analysis?fen=1r3rk1/p1Q2pp1/4b1p1/4P1q1/8/P1N1P3/1P3PPP/R3K2R%20b%20-%20-%200%2016

#### Case 918 — SACRIFICE (missed, depth 6)

Moves (UCI — SAN unavailable): `e1g1 f8c8 c3e4 g5g4 c7a7 g4e4 a7d4 e4d4 e3d4 c8d8 f1d1 e6b3`

FEN (line start): `5rk1/p1Q2pp1/4b1p1/4P1q1/8/P1N1P3/1r3PPP/R3K2R w - - 0 17`

Game (full game at ply): http://localhost:5173/analysis?game_id=684592&ply=32

FEN (free-play from line start): http://localhost:5173/analysis?fen=5rk1/p1Q2pp1/4b1p1/4P1q1/8/P1N1P3/1r3PPP/R3K2R%20w%20-%20-%200%2017

#### Case 919 — DISCOVERED_ATTACK (allowed, depth 7)

Moves (SAN): `8. dxe5 Nxe5 9. Bxd5 Qd7`

FEN (line start): `r2qkbnr/pp3ppp/2n5/3pp3/3P4/2P2B2/PP3PPP/RNBQK2R w - - 0 8`

Game (full game at ply): http://localhost:5173/analysis?game_id=684607&ply=13

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qkbnr/pp3ppp/2n5/3pp3/3P4/2P2B2/PP3PPP/RNBQK2R%20w%20-%20-%200%208

#### Case 920 — CLEARANCE (allowed, depth 8)

Moves (SAN): `19. Bxe7 Qxe7 20. Qxh5 Rfd8 21. Nxd5 Qd6 22. Ne3 g6 23. Qc5 Qxc5 24. dxc5 f5`

FEN (line start): `r2q1rk1/4bppp/8/n2p2Bn/3Pp3/2P1N2B/5PPP/R2QR1K1 w - - 1 19`

Game (full game at ply): http://localhost:5173/analysis?game_id=684607&ply=35

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2q1rk1/4bppp/8/n2p2Bn/3Pp3/2P1N2B/5PPP/R2QR1K1%20w%20-%20-%201%2019

#### Case 921 — PIN (missed, depth 8)

Moves (SAN): `24... Kg7 25. Qxh7+ Kxf6 26. Bxg6 Qg5 27. Rxe4 Nd2 28. h4 Nf3+ 29. Kh1 Qxg6 30. Rf4+`

FEN (line start): `r4rk1/5p1p/5Np1/q4B1Q/3Pp3/1nP5/5PPP/3RR1K1 b - - 0 24`

Game (full game at ply): http://localhost:5173/analysis?game_id=684607&ply=47

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4rk1/5p1p/5Np1/q4B1Q/3Pp3/1nP5/5PPP/3RR1K1%20b%20-%20-%200%2024

#### Case 922 — CLEARANCE (allowed, depth 10)

Moves (SAN): `23. Nxa6+ Qxa6 24. Rxc8+ Rxc8 25. Bxa6 bxa6 26. Bc3 Nc2+ 27. Kd2 Nce3 28. Rc1 Rh8`

FEN (line start): `1kr4r/1p1b1p1N/p3p1p1/q3Pn2/1N1n1P2/3B3Q/P2B3P/2R1K1R1 w - - 1 23`

Game (full game at ply): http://localhost:5173/analysis?game_id=684620&ply=43

FEN (free-play from line start): http://localhost:5173/analysis?fen=1kr4r/1p1b1p1N/p3p1p1/q3Pn2/1N1n1P2/3B3Q/P2B3P/2R1K1R1%20w%20-%20-%201%2023

#### Case 923 — INTERFERENCE (missed, depth 4)

Moves (SAN): `22... Rxh7 23. Qg2 Qa3 24. Rc3 Qxb4 25. Rc8+ Rxc8 26. Bxb4 Bc6 27. Qf2 Nf3+ 28. Ke2`

FEN (line start): `1k1r3r/1p1b1p1N/p3p1p1/q3Pn2/1N1n1P2/3B3Q/P2B3P/2R1K1R1 b - - 0 22`

Game (full game at ply): http://localhost:5173/analysis?game_id=684620&ply=43

FEN (free-play from line start): http://localhost:5173/analysis?fen=1k1r3r/1p1b1p1N/p3p1p1/q3Pn2/1N1n1P2/3B3Q/P2B3P/2R1K1R1%20b%20-%20-%200%2022

#### Case 924 — CLEARANCE (allowed, depth 4)

Moves (SAN): `26. Rxc1 Rxc1 27. Bxf5 Nxf5 28. Qd3 b6 29. Bd2 Rc7 30. Qxa6 Bc8 31. Qxb6+ Rb7`

FEN (line start): `1kr5/1p1b1p1N/p3p1p1/B3Pn2/3n1P2/3B3Q/P4K1P/2r3R1 w - - 1 26`

Game (full game at ply): http://localhost:5173/analysis?game_id=684620&ply=49

FEN (free-play from line start): http://localhost:5173/analysis?fen=1kr5/1p1b1p1N/p3p1p1/B3Pn2/3n1P2/3B3Q/P4K1P/2r3R1%20w%20-%20-%201%2026

#### Case 925 — SACRIFICE (missed, depth 6)

Moves (SAN): `32... Rb2 33. Kg5 Ng1 34. Qd4+ b6 35. Qxb2 Nf3+ 36. Kh6 bxa5 37. Nd7 Bxd7 38. Qf2+`

FEN (line start): `3Q4/kp3p2/p1b1pN2/B3Pp2/5P1K/8/P1r1n2P/8 b - - 0 32`

Game (full game at ply): http://localhost:5173/analysis?game_id=684620&ply=63

FEN (free-play from line start): http://localhost:5173/analysis?fen=3Q4/kp3p2/p1b1pN2/B3Pp2/5P1K/8/P1r1n2P/8%20b%20-%20-%200%2032

#### Case 926 — HANGING_PIECE (missed, depth 0)

Moves (SAN): `34... Bxd7 35. Qd6+ Ka8 36. Qxd7 Nd5 37. h3 Ka7 38. Qxf7 Rxa2 39. Bd8 Ra3 40. Qd7`

FEN (line start): `1k6/1p1N1p2/pQb1p3/B3Pp2/5n1K/8/P1r4P/8 b - - 0 34`

Game (full game at ply): http://localhost:5173/analysis?game_id=684620&ply=67

FEN (free-play from line start): http://localhost:5173/analysis?fen=1k6/1p1N1p2/pQb1p3/B3Pp2/5n1K/8/P1r4P/8%20b%20-%20-%200%2034

#### Case 927 — TRAPPED_PIECE (allowed, depth 8)

Moves (SAN): `19. Bxh5 Rd8 20. Bg4 f5 21. h4 Qf6 22. f3 fxg4 23. fxe4 Qxd4 24. Nxg4 Qxe4`

FEN (line start): `r5k1/1pp2pp1/p1n1r3/2Pp2qp/3Pb3/P3N1PP/1P2BP1K/R2Q1R2 w - - 0 19`

Game (full game at ply): http://localhost:5173/analysis?game_id=684625&ply=35

FEN (free-play from line start): http://localhost:5173/analysis?fen=r5k1/1pp2pp1/p1n1r3/2Pp2qp/3Pb3/P3N1PP/1P2BP1K/R2Q1R2%20w%20-%20-%200%2019

#### Case 928 — SACRIFICE (missed, depth 4)

Moves (SAN): `18... Qf6 19. f3 Bd3 20. Qxd3 Rae8 21. Nc2 Rxe2+ 22. Kg1 h5 23. Rf2 Rxf2 24. Kxf2`

FEN (line start): `r5k1/1pp2pp1/p1n1r2p/2Pp2q1/3Pb3/P3N1PP/1P2BP1K/R2Q1R2 b - - 0 18`

Game (full game at ply): http://localhost:5173/analysis?game_id=684625&ply=35

FEN (free-play from line start): http://localhost:5173/analysis?fen=r5k1/1pp2pp1/p1n1r2p/2Pp2q1/3Pb3/P3N1PP/1P2BP1K/R2Q1R2%20b%20-%20-%200%2018

#### Case 929 — DISCOVERED_ATTACK (missed, depth 3)

Moves (SAN): `21... g6 22. Bg4 Bf3 23. Bxf3 Rxe3 24. Bg4 Rae8 25. Rc1 c6 26. Rc3 Nf5 27. Bxf5`

FEN (line start): `r5k1/1pp2pp1/p3rq2/2Pp3B/3nbP1P/P3N1P1/1P5K/R2Q1R2 b - - 0 21`

Game (full game at ply): http://localhost:5173/analysis?game_id=684625&ply=41

FEN (free-play from line start): http://localhost:5173/analysis?fen=r5k1/1pp2pp1/p3rq2/2Pp3B/3nbP1P/P3N1P1/1P5K/R2Q1R2%20b%20-%20-%200%2021

#### Case 930 — HANGING_PIECE (allowed, depth 0)

Moves (SAN): `23. Qxf3 Qd8 24. Rad1 Be4 25. Qb3 Bxd5 26. Qxd5 Qf6 27. Kh3 Rae8 28. Bf3 c6`

FEN (line start): `r5k1/1pp2pp1/p3rq2/2PN1b1B/5P1P/P4nP1/1P5K/R2Q1R2 w - - 1 23`

Game (full game at ply): http://localhost:5173/analysis?game_id=684625&ply=43

FEN (free-play from line start): http://localhost:5173/analysis?fen=r5k1/1pp2pp1/p3rq2/2PN1b1B/5P1P/P4nP1/1P5K/R2Q1R2%20w%20-%20-%201%2023

#### Case 931 — SACRIFICE (missed, depth 2)

Moves (SAN): `22... Qd8 23. Qxd4 c6 24. Rae1 cxd5 25. Rxe6 fxe6 26. Bf3 Rc8 27. b4 b6 28. Rc1`

FEN (line start): `r5k1/1pp2pp1/p3rq2/2PN1b1B/3n1P1P/P5P1/1P5K/R2Q1R2 b - - 0 22`

Game (full game at ply): http://localhost:5173/analysis?game_id=684625&ply=43

FEN (free-play from line start): http://localhost:5173/analysis?fen=r5k1/1pp2pp1/p3rq2/2PN1b1B/3n1P1P/P5P1/1P5K/R2Q1R2%20b%20-%20-%200%2022

#### Case 932 — CLEARANCE (allowed, depth 2)

Moves (SAN): `26. Qxe2 Qxe2 27. Rae1 Qc2 28. Rxe4 Rd8 29. c6 bxc6 30. Ne3 Qc3 31. Rb1 Qxa3`

FEN (line start): `r5k1/1pp2pp1/p7/2PN4/4bP1P/P5P1/1q2r1BK/R2Q2R1 w - - 1 26`

Game (full game at ply): http://localhost:5173/analysis?game_id=684625&ply=49

FEN (free-play from line start): http://localhost:5173/analysis?fen=r5k1/1pp2pp1/p7/2PN4/4bP1P/P5P1/1q2r1BK/R2Q2R1%20w%20-%20-%201%2026

#### Case 933 — PIN (missed, depth 2)

Moves (SAN): `25... Rae8 26. Nb4 Bg4 27. Rb1 Qf6 28. Qd5 Bf5 29. c6 b6 30. Nxa6 Be4 31. Qd7`

FEN (line start): `r5k1/1pp2pp1/p7/2PN1b2/5P1P/P5P1/1q2r1BK/R2Q2R1 b - - 0 25`

Game (full game at ply): http://localhost:5173/analysis?game_id=684625&ply=49

FEN (free-play from line start): http://localhost:5173/analysis?fen=r5k1/1pp2pp1/p7/2PN1b2/5P1P/P5P1/1q2r1BK/R2Q2R1%20b%20-%20-%200%2025

#### Case 934 — FORK (missed, depth 2)

Moves (SAN): `31... Qf1 32. Nd4 Qf2+ 33. Kh3 Qxd4 34. Qxc7 Qd5 35. Qb6 Qh1+ 36. Kg4 Qd1+ 37. Kh3`

FEN (line start): `4rk2/1Qp2pp1/p7/2P2N2/5P1P/P5P1/7K/q7 b - - 0 31`

Game (full game at ply): http://localhost:5173/analysis?game_id=684625&ply=61

FEN (free-play from line start): http://localhost:5173/analysis?fen=4rk2/1Qp2pp1/p7/2P2N2/5P1P/P5P1/7K/q7%20b%20-%20-%200%2031

#### Case 935 — PIN (missed, depth 2)

Moves (SAN): `32... Qa2+ 33. Kh3 Qe6 34. g4 Qb3+ 35. Ng3 Kg8 36. h5 Qb8 37. Qd7 Re3 38. Qf5`

FEN (line start): `4rk2/2Q2pp1/p7/2P2N2/5P1P/q5P1/7K/8 b - - 0 32`

Game (full game at ply): http://localhost:5173/analysis?game_id=684625&ply=63

FEN (free-play from line start): http://localhost:5173/analysis?fen=4rk2/2Q2pp1/p7/2P2N2/5P1P/q5P1/7K/8%20b%20-%20-%200%2032

#### Case 936 — FORK (allowed, depth 0)

Moves (SAN): `20... Bd5 21. Qa3 Nxd1 22. Nf4 Kh8 23. Bxd1 Bxe6 24. Nxe6 Qe8 25. Bb3 Rf7 26. d5`

FEN (line start): `r2q1r2/p5kp/4Rpp1/1p6/3Pb3/1Q1Nn2P/PP2BPP1/3R2K1 b - - 0 20`

Game (full game at ply): http://localhost:5173/analysis?game_id=684645&ply=38

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2q1r2/p5kp/4Rpp1/1p6/3Pb3/1Q1Nn2P/PP2BPP1/3R2K1%20b%20-%20-%200%2020

#### Case 937 — SACRIFICE (missed, depth 4)

Moves (SAN): `20. Nc5 Kh8 21. Rd6 Qxd6 22. Nxe4 Qd5 23. Qxe3 Qxa2 24. b3 a5 25. Bxb5 Rac8`

FEN (line start): `r2q1r2/p5kp/2R1ppp1/1p6/3Pb3/1Q1Nn2P/PP2BPP1/3R2K1 w - - 0 20`

Game (full game at ply): http://localhost:5173/analysis?game_id=684645&ply=38

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2q1r2/p5kp/2R1ppp1/1p6/3Pb3/1Q1Nn2P/PP2BPP1/3R2K1%20w%20-%20-%200%2020

#### Case 938 — CLEARANCE (allowed, depth 4)

Moves (SAN): `21... Nxd1 22. Qxd1 Qd7 23. Re3 Rae8 24. Rd3 Qd5 25. a3 Rc8 26. g3 Rfd8 27. Qd2`

FEN (line start): `r2q1r2/p5kp/4Rpp1/1p6/3P4/3Qn2P/PP2BPP1/3R2K1 b - - 0 21`

Game (full game at ply): http://localhost:5173/analysis?game_id=684645&ply=40

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2q1r2/p5kp/4Rpp1/1p6/3P4/3Qn2P/PP2BPP1/3R2K1%20b%20-%20-%200%2021

#### Case 939 — HANGING_PIECE (missed, depth 0)

Moves (SAN): `21. Rxe3 Bxe2 22. Rxe2 a6 23. Re6 Re8 24. d5 Ra7 25. Rc6 Rd7 26. Rxa6 Re5`

FEN (line start): `r2q1r2/p5kp/4Rpp1/1p6/3P4/1Q1bn2P/PP2BPP1/3R2K1 w - - 0 21`

Game (full game at ply): http://localhost:5173/analysis?game_id=684645&ply=40

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2q1r2/p5kp/4Rpp1/1p6/3P4/1Q1bn2P/PP2BPP1/3R2K1%20w%20-%20-%200%2021

#### Case 940 — CLEARANCE (missed, depth 6)

Moves (SAN): `12... Bxe2 13. Qxe2 Qd7 14. f3`

FEN (line start): `r2qk2r/pp3ppp/5n2/3p4/3Pp1b1/4P1P1/PP1NBPP1/R2QK2R b - - 0 12`

Game (full game at ply): http://localhost:5173/analysis?game_id=684647&ply=23

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qk2r/pp3ppp/5n2/3p4/3Pp1b1/4P1P1/PP1NBPP1/R2QK2R%20b%20-%20-%200%2012

#### Case 941 — PROMOTION (allowed, depth 6)

Moves (SAN): `38. b5 Kf6 39. b6 Ke6 40. b7 Kd7 41. b8=Q Kxc6 42. a4 Kd7 43. a5 Ke7`

FEN (line start): `8/5p2/2N5/3p2k1/1P1P3p/P3PP2/6K1/8 w - - 1 38`

Game (full game at ply): http://localhost:5173/analysis?game_id=684647&ply=73

FEN (free-play from line start): http://localhost:5173/analysis?fen=8/5p2/2N5/3p2k1/1P1P3p/P3PP2/6K1/8%20w%20-%20-%201%2038

#### Case 942 — SACRIFICE (missed, depth 6)

Moves (SAN): `37... h3+ 38. Kxh3 Kg5 39. Ne7 f5 40. Nxd5 f4 41. e4 Kg6 42. b5 Kh6 43. b6`

FEN (line start): `8/5p2/2N5/3p1k2/1P1P3p/P3PP2/6K1/8 b - - 0 37`

Game (full game at ply): http://localhost:5173/analysis?game_id=684647&ply=73

FEN (free-play from line start): http://localhost:5173/analysis?fen=8/5p2/2N5/3p1k2/1P1P3p/P3PP2/6K1/8%20b%20-%20-%200%2037

#### Case 943 — FORK (missed, depth 6)

Moves (SAN): `30... Nf5 31. Rd3 Bxc5 32. g3 h6 33. h4 Bxd4+ 34. Nxd4 Nxd4 35. Kg2 c5 36. Be3`

FEN (line start): `4r2k/1p1r2pp/2p5/p1P5/Pb1P1B1n/1P5R/1R2N1PP/6K1 b - - 0 30`

Game (full game at ply): http://localhost:5173/analysis?game_id=684652&ply=59

FEN (free-play from line start): http://localhost:5173/analysis?fen=4r2k/1p1r2pp/2p5/p1P5/Pb1P1B1n/1P5R/1R2N1PP/6K1%20b%20-%20-%200%2030

#### Case 944 — DISCOVERED_ATTACK (allowed, depth 7)

Moves (SAN): `13... Qe7 14. Qe3 Re8 15. Be2 Bf5`

FEN (line start): `r1bq1rk1/1pp2p1p/6p1/p1NPb3/2P5/7P/PP1Q1PP1/R3KB1R b - - 0 13`

Game (full game at ply): http://localhost:5173/analysis?game_id=684657&ply=24

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1bq1rk1/1pp2p1p/6p1/p1NPb3/2P5/7P/PP1Q1PP1/R3KB1R%20b%20-%20-%200%2013

#### Case 945 — CLEARANCE (missed, depth 6)

Moves (SAN): `13. Bd3 a4 14. Rd1 b6`

FEN (line start): `r1bq1rk1/1pp2p1p/6p1/p1pPb3/2P1N3/7P/PP1Q1PP1/R3KB1R w - - 0 13`

Game (full game at ply): http://localhost:5173/analysis?game_id=684657&ply=24

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1bq1rk1/1pp2p1p/6p1/p1pPb3/2P1N3/7P/PP1Q1PP1/R3KB1R%20w%20-%20-%200%2013

#### Case 946 — DISCOVERED_ATTACK (missed, depth 1)

Moves (SAN): `18. Bg4 Ba4 19. Rxe8+ Bxe8 20. Kb1 b5 21. Qf4 Qb6 22. Ne5 bxc4 23. Nxc4 Qb4`

FEN (line start): `r3r1k1/1p1b1p1p/5qp1/p1pP4/2Pb4/3N3P/PP1QBPP1/2KRR3 w - - 0 18`

Game (full game at ply): http://localhost:5173/analysis?game_id=684657&ply=34

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3r1k1/1p1b1p1p/5qp1/p1pP4/2Pb4/3N3P/PP1QBPP1/2KRR3%20w%20-%20-%200%2018

#### Case 947 — PIN (allowed, depth 6)

Moves (SAN): `22... Rxe2 23. Rxe2 axb3 24. Kb1 g5 25. Qg3 Qg6 26. Bg4 f5 27. axb3 fxg4 28. Ra2`

FEN (line start): `r3r1k1/1p1b1pqp/6p1/2pP4/p1Pb1Q2/1P1N1B1P/P3RPP1/2K1R3 b - - 1 22`

Game (full game at ply): http://localhost:5173/analysis?game_id=684657&ply=42

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3r1k1/1p1b1pqp/6p1/2pP4/p1Pb1Q2/1P1N1B1P/P3RPP1/2K1R3%20b%20-%20-%201%2022

#### Case 948 — CLEARANCE (missed, depth 4)

Moves (SAN): `19... Bh6 20. Kf2 Kh8 21. Rg1 Rg8 22. g3 f5 23. Ne5 Bd5 24. Qd3 f6 25. Nf3`

FEN (line start): `r4rk1/ppq2pbp/2p1pp2/8/2QPb3/P1P1PN1P/1P2B1P1/3R1RK1 b - - 0 19`

Game (full game at ply): http://localhost:5173/analysis?game_id=684663&ply=37

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4rk1/ppq2pbp/2p1pp2/8/2QPb3/P1P1PN1P/1P2B1P1/3R1RK1%20b%20-%20-%200%2019

#### Case 949 — CLEARANCE (allowed, depth 10)

Moves (SAN): `24... Bxh3 25. Qxh3 Rh8 26. Qf3+ Kg8`

FEN (line start): `r1bq1r2/pp3knQ/3p2p1/1N1Pp3/4P3/7R/PP3PP1/R3K3 b - - 1 24`

Game (full game at ply): http://localhost:5173/analysis?game_id=684666&ply=46

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1bq1r2/pp3knQ/3p2p1/1N1Pp3/4P3/7R/PP3PP1/R3K3%20b%20-%20-%201%2024

#### Case 950 — DEFLECTION (missed, depth 2)

Moves (SAN): `26. Nxd6+ Ke7 27. Qxg7+ Kxd6 28. Qxg6+ Kc5 29. Qg3 Qb5+ 30. Kg1 Qxb2 31. Qe3+ Kb5`

FEN (line start): `r4r2/pp3knQ/3p2p1/qN1Pp3/4P3/7b/PP3PP1/R4K2 w - - 0 26`

Game (full game at ply): http://localhost:5173/analysis?game_id=684666&ply=50

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4r2/pp3knQ/3p2p1/qN1Pp3/4P3/7b/PP3PP1/R4K2%20w%20-%20-%200%2026

#### Case 951 — DEFLECTION (missed, depth 8)

Moves (SAN): `32. g4 Qd8 33. Rc3 Rhh8 34. g5 Rf8 35. Qxg7+ Rf7 36. Qxh8 Qxh8 37. Rc7+ Kd8`

FEN (line start): `6r1/pp2k1n1/1q1p2Q1/3Pp2r/4P3/8/PP3PP1/2R3K1 w - - 0 32`

Game (full game at ply): http://localhost:5173/analysis?game_id=684666&ply=62

FEN (free-play from line start): http://localhost:5173/analysis?fen=6r1/pp2k1n1/1q1p2Q1/3Pp2r/4P3/8/PP3PP1/2R3K1%20w%20-%20-%200%2032

#### Case 952 — CLEARANCE (missed, depth 10)

Moves (SAN): `11. e5 Nd5 12. Ng5 f5 13. exf6 Nxf6 14. Bxe6+ Kh8 15. Bf4 Qe8 16. Rae1 h6`

FEN (line start): `r1bq1rk1/1pp2ppp/p1n1pn2/8/2BPP3/P1PQ1N2/5PPP/R1B2RK1 w - - 0 11`

Game (full game at ply): http://localhost:5173/analysis?game_id=684671&ply=20

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1bq1rk1/1pp2ppp/p1n1pn2/8/2BPP3/P1PQ1N2/5PPP/R1B2RK1%20w%20-%20-%200%2011

#### Case 953 — CLEARANCE (allowed, depth 6)

Moves (SAN): `17... Nxe5 18. Qh3 Nc4 19. Qh4 f6 20. Bh6 Qd7 21. Bxf8 Rxf8 22. a4 Bd5 23. Qg3`

FEN (line start): `3r1rk1/1bp2pqp/p1n1p1p1/1p2N1B1/3P4/P1PQ4/2B2PPP/R3R1K1 b - - 1 17`

Game (full game at ply): http://localhost:5173/analysis?game_id=684671&ply=32

FEN (free-play from line start): http://localhost:5173/analysis?fen=3r1rk1/1bp2pqp/p1n1p1p1/1p2N1B1/3P4/P1PQ4/2B2PPP/R3R1K1%20b%20-%20-%201%2017

#### Case 954 — HANGING_PIECE (allowed, depth 0)

Moves (SAN): `20... Rxf6 21. Qg3 Qh6 22. h4 Qf4 23. Qxf4 Rxf4 24. Rxe6 Rd6 25. Rxd6 cxd6 26. a4`

FEN (line start): `3r1rk1/1bp3q1/p3pBp1/1p2R2p/3P4/P1P4Q/2B2PPP/R5K1 b - - 0 20`

Game (full game at ply): http://localhost:5173/analysis?game_id=684671&ply=38

FEN (free-play from line start): http://localhost:5173/analysis?fen=3r1rk1/1bp3q1/p3pBp1/1p2R2p/3P4/P1P4Q/2B2PPP/R5K1%20b%20-%20-%200%2020

#### Case 955 — PROMOTION (allowed, depth 2)

Moves (SAN): `56... g2 57. Kc3 g1=Q 58. Kd4 Qg5 59. Ke4 Ke2 60. Kd4 Kf3 61. Kc3 Qc5+ 62. Kb3`

FEN (line start): `8/8/8/8/8/6p1/3K1k2/8 b - - 1 56`

Game (full game at ply): http://localhost:5173/analysis?game_id=684671&ply=110

FEN (free-play from line start): http://localhost:5173/analysis?fen=8/8/8/8/8/6p1/3K1k2/8%20b%20-%20-%201%2056

#### Case 956 — CLEARANCE (missed, depth 8)

Moves (UCI — SAN unavailable): `e8g8 f1e1 b8d7 c1d2 d7b6 c4b3 f8e8 a1d1 e7f8 e1e8 d8e8 a2a4`

FEN (line start): `rn1qk2r/pp2bppp/2p2p2/8/2BP4/5Q1P/PPP2PP1/R1B2RK1 b - - 0 10`

Game (full game at ply): http://localhost:5173/analysis?game_id=684672&ply=19

FEN (free-play from line start): http://localhost:5173/analysis?fen=rn1qk2r/pp2bppp/2p2p2/8/2BP4/5Q1P/PPP2PP1/R1B2RK1%20b%20-%20-%200%2010

#### Case 957 — FORK (missed, depth 0)

Moves (SAN): `23... Qd3 24. Bd2 Ne4 25. Qa6 Nxd2 26. Rbd1 Qe4 27. a4 Nxb3 28. Rxd7 Nc5 29. axb5`

FEN (line start): `4r1k1/3r1p1p/2pq1bp1/1pn2p2/5P2/QBP4P/PP4P1/1RB2R1K b - - 0 23`

Game (full game at ply): http://localhost:5173/analysis?game_id=684672&ply=45

FEN (free-play from line start): http://localhost:5173/analysis?fen=4r1k1/3r1p1p/2pq1bp1/1pn2p2/5P2/QBP4P/PP4P1/1RB2R1K%20b%20-%20-%200%2023

#### Case 958 — SACRIFICE (allowed, depth 4)

Moves (SAN): `15. Bxf7+ Kd8 16. Bxe6 Qxa1 17. Bxd5 Kc7 18. Rf7+ Kb6 19. Qd3 a6 20. Bxc6 bxc6`

FEN (line start): `r3kb1r/pp3ppp/2n1p3/3pP2B/3q4/1P6/P5PP/RN1Q1R1K w - - 0 15`

Game (full game at ply): http://localhost:5173/analysis?game_id=684673&ply=27

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3kb1r/pp3ppp/2n1p3/3pP2B/3q4/1P6/P5PP/RN1Q1R1K%20w%20-%20-%200%2015

#### Case 959 — INTERFERENCE (missed, depth 2)

Moves (SAN): `14... g6 15. Nd2 Nxd4 16. Re1 Qd3 17. Be2 Nxe2 18. Rxe2 Bg7 19. Qf1 Rc8 20. Nf3`

FEN (line start): `r3kb1r/pp3ppp/2n1p3/3pP2B/3P4/1P2q3/P5PP/RN1Q1R1K b - - 0 14`

Game (full game at ply): http://localhost:5173/analysis?game_id=684673&ply=27

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3kb1r/pp3ppp/2n1p3/3pP2B/3P4/1P2q3/P5PP/RN1Q1R1K%20b%20-%20-%200%2014

#### Case 960 — TRAPPED_PIECE (allowed, depth 2)

Moves (SAN): `36. Kf3 Kf5 37. Kxg2 Ke4 38. Nf4 Kxe5 39. Kf3 Kd4 40. Nxe6+ Kc3 41. Nc7 b4`

FEN (line start): `8/7p/4p1k1/pp1pP2p/5K2/1P1N2PP/P5n1/8 w - - 1 36`

Game (full game at ply): http://localhost:5173/analysis?game_id=684673&ply=69

FEN (free-play from line start): http://localhost:5173/analysis?fen=8/7p/4p1k1/pp1pP2p/5K2/1P1N2PP/P5n1/8%20w%20-%20-%201%2036

#### Case 961 — TRAPPED_PIECE (allowed, depth 2)

Moves (SAN): `37. g4 Kf7 38. Kxg2 Ke7 39. Kf3 Kd7 40. Nc5+ Ke7 41. Ke3 Kf7 42. Kf4 b4`

FEN (line start): `8/7p/4p1k1/pp1pP3/7p/1P1N1KPP/P5n1/8 w - - 0 37`

Game (full game at ply): http://localhost:5173/analysis?game_id=684673&ply=71

FEN (free-play from line start): http://localhost:5173/analysis?fen=8/7p/4p1k1/pp1pP3/7p/1P1N1KPP/P5n1/8%20w%20-%20-%200%2037

#### Case 962 — SACRIFICE (missed, depth 2)

Moves (SAN): `36... Kf5 37. Kxg2 Ke4 38. Nf4 Kxe5 39. Kf3 Kd4 40. Nxe6+ Kc3 41. Nc7 b4 42. Ne6`

FEN (line start): `8/7p/4p1k1/pp1pP2p/8/1P1N1KPP/P5n1/8 b - - 0 36`

Game (full game at ply): http://localhost:5173/analysis?game_id=684673&ply=71

FEN (free-play from line start): http://localhost:5173/analysis?fen=8/7p/4p1k1/pp1pP2p/8/1P1N1KPP/P5n1/8%20b%20-%20-%200%2036

#### Case 963 — MATE (allowed, depth 10)

Moves (SAN): `42. a7 Rd3+ 43. Nxd3 Kb7 44. Rh8 Kc7 45. Rh7+ Kb6 46. a8=Q Kb5 47. Rb7#`

FEN (line start): `8/2k5/P6R/2NK4/1P5P/2P3r1/8/8 w - - 1 42`

Game (full game at ply): http://localhost:5173/analysis?game_id=684675&ply=81

FEN (free-play from line start): http://localhost:5173/analysis?fen=8/2k5/P6R/2NK4/1P5P/2P3r1/8/8%20w%20-%20-%201%2042

#### Case 964 — CLEARANCE (missed, depth 4)

Moves (SAN): `41... Kd8 42. b5 Ke7 43. b6 Rd8+ 44. Kc4 Kf7 45. b7 Kg7 46. Rc6 Rh8 47. Kb5`

FEN (line start): `6r1/2k5/P6R/2NK4/1P5P/2P5/8/8 b - - 0 41`

Game (full game at ply): http://localhost:5173/analysis?game_id=684675&ply=81

FEN (free-play from line start): http://localhost:5173/analysis?fen=6r1/2k5/P6R/2NK4/1P5P/2P5/8/8%20b%20-%20-%200%2041

#### Case 965 — PIN (allowed, depth 4)

Moves (SAN): `13... Nf4 14. f3 Qg5 15. g3 d6 16. Nd3 Nxd3 17. Bxd3 Qe3+ 18. Kg2 Qxd4 19. Nb5`

FEN (line start): `rn1q1r2/pbpp2kp/1p2p1p1/4N2n/2BP4/2N5/PPP2PPP/R2Q1RK1 b - - 1 13`

Game (full game at ply): http://localhost:5173/analysis?game_id=684681&ply=24

FEN (free-play from line start): http://localhost:5173/analysis?fen=rn1q1r2/pbpp2kp/1p2p1p1/4N2n/2BP4/2N5/PPP2PPP/R2Q1RK1%20b%20-%20-%201%2013

#### Case 966 — CLEARANCE (missed, depth 10)

Moves (SAN): `6... e6 7. Nc3 exd5 8. exd5 a6 9. Qe2+ Be7 10. Bg5`

FEN (line start): `rnbqkb1r/pp2pppp/5n2/2pP4/4P3/5N2/PP3PPP/RNBQKB1R b - - 0 6`

Game (full game at ply): http://localhost:5173/analysis?game_id=684695&ply=11

FEN (free-play from line start): http://localhost:5173/analysis?fen=rnbqkb1r/pp2pppp/5n2/2pP4/4P3/5N2/PP3PPP/RNBQKB1R%20b%20-%20-%200%206

#### Case 967 — HANGING_PIECE (missed, depth 0)

Moves (SAN): `16... Bxa1 17. Nc3 Bb2 18. Bxf8 Qxf8 19. Bb3 Rb4 20. Re1 c4 21. Bxc4 Qc5 22. Nd1`

FEN (line start): `1r1q1rk1/p2n1p1p/2bB2p1/2p5/2B5/3Q1N2/Pb3PPP/RN3RK1 b - - 0 16`

Game (full game at ply): http://localhost:5173/analysis?game_id=684695&ply=31

FEN (free-play from line start): http://localhost:5173/analysis?fen=1r1q1rk1/p2n1p1p/2bB2p1/2p5/2B5/3Q1N2/Pb3PPP/RN3RK1%20b%20-%20-%200%2016

#### Case 968 — CLEARANCE (missed, depth 2)

Moves (SAN): `22... Rc2 23. Rf2 Rac8 24. Rdd2 Rxd2 25. Rxd2 Rc6 26. Nd4 Rc1+ 27. Kf2 Kf7 28. Ne2`

FEN (line start): `r1r3k1/p5pp/4N1n1/3p4/8/7P/PP4P1/3R1RK1 b - - 0 22`

Game (full game at ply): http://localhost:5173/analysis?game_id=684699&ply=43

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1r3k1/p5pp/4N1n1/3p4/8/7P/PP4P1/3R1RK1%20b%20-%20-%200%2022

#### Case 969 — FORK (missed, depth 8)

Moves (SAN): `12. Ng5 Qf6 13. f4 Qxd4 14. Qxd4 Nxd4 15. Bxd7 Rd8 16. Ndxf7 Rxd7 17. Nxh8 Nc2+`

FEN (line start): `r2q1knr/p2b1ppp/1pnNp3/1B6/3P4/5N2/PP1Q1PPP/R3K2R w - - 0 12`

Game (full game at ply): http://localhost:5173/analysis?game_id=684716&ply=22

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2q1knr/p2b1ppp/1pnNp3/1B6/3P4/5N2/PP1Q1PPP/R3K2R%20w%20-%20-%200%2012

#### Case 970 — CLEARANCE (missed, depth 8)

Moves (SAN): `15. Ne5 Be8 16. Qa3 Kg8 17. Rfc1 Nd5 18. Rc2 h6 19. Rac1 Qe7 20. Rc8 Rxc8`

FEN (line start): `r2q1k1r/4nppp/ppbNp3/8/1Q1P4/5N2/PP3PPP/R4RK1 w - - 0 15`

Game (full game at ply): http://localhost:5173/analysis?game_id=684716&ply=28

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2q1k1r/4nppp/ppbNp3/8/1Q1P4/5N2/PP3PPP/R4RK1%20w%20-%20-%200%2015

#### Case 971 — FORK (missed, depth 0)

Moves (SAN): `28. Rxf7+ Qxf7 29. Qxf7+ Kxf7 30. Rg3 Rc2 31. Kg2 Rxb2 32. Rd3 Rf8 33. Kg3 Kg8`

FEN (line start): `r1r5/2QR1pkp/p3p1p1/1p2P3/8/5q2/PP3PRP/7K w - - 0 28`

Game (full game at ply): http://localhost:5173/analysis?game_id=684716&ply=54

FEN (free-play from line start): http://localhost:5173/analysis?fen=r1r5/2QR1pkp/p3p1p1/1p2P3/8/5q2/PP3PRP/7K%20w%20-%20-%200%2028

#### Case 972 — PROMOTION (allowed, depth 0)

Moves (SAN): `45... c1=Q+ 46. Ke2 Rc7 47. Rd2 Kf4 48. e5 Kxf5 49. exf6 Qc4+ 50. Ke1 Qe4+ 51. Kf2`

FEN (line start): `8/5r2/5p2/pp2kB2/4P3/P2R4/2p5/5K2 b - - 0 45`

Game (full game at ply): http://localhost:5173/analysis?game_id=684719&ply=88

FEN (free-play from line start): http://localhost:5173/analysis?fen=8/5r2/5p2/pp2kB2/4P3/P2R4/2p5/5K2%20b%20-%20-%200%2045

#### Case 973 — SKEWER (allowed, depth 8)

Moves (SAN): `20. Nb5 Raf8 21. Ree1 Qxe5 22. Qxe5 Nxe5 23. Kg1 Nxd3 24. Rxe6 Rf2 25. Nc3 Rxb2`

FEN (line start): `r5k1/ppq3pp/2n1p3/3pPr2/8/2NPR1Q1/PP4PP/R6K w - - 1 20`

Game (full game at ply): http://localhost:5173/analysis?game_id=684729&ply=37

FEN (free-play from line start): http://localhost:5173/analysis?fen=r5k1/ppq3pp/2n1p3/3pPr2/8/2NPR1Q1/PP4PP/R6K%20w%20-%20-%201%2020

#### Case 974 — FORK (missed, depth 0)

Moves (SAN): `19... d4 20. Nd5 Qd7 21. Nf6+ Rxf6 22. exf6 dxe3 23. Qxe3 gxf6 24. Rf1 Qe7 25. d4`

FEN (line start): `r4rk1/ppq3pp/2n1p3/3pP3/8/2NPR1Q1/PP4PP/R6K b - - 0 19`

Game (full game at ply): http://localhost:5173/analysis?game_id=684729&ply=37

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4rk1/ppq3pp/2n1p3/3pP3/8/2NPR1Q1/PP4PP/R6K%20b%20-%20-%200%2019

#### Case 975 — ATTRACTION (allowed, depth 8)

Moves (SAN): `18. g4 Ne7 19. Rfc1 Qb4 20. a3 Qxa3 21. R1c5 Qb4 22. Rxe7+ Kxe7 23. Rc7+ Kd8`

FEN (line start): `r3k2r/ppR2ppp/4p3/1q1pPn2/N7/1P3Q2/P4PPP/5RK1 w - - 1 18`

Game (full game at ply): http://localhost:5173/analysis?game_id=684731&ply=33

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3k2r/ppR2ppp/4p3/1q1pPn2/N7/1P3Q2/P4PPP/5RK1%20w%20-%20-%201%2018

#### Case 976 — DISCOVERED_CHECK (allowed, depth 0)

Moves (SAN): `12... c4+ 13. Qf2 Qxf2+ 14. Rxf2 Be7 15. d4 cxd3 16. cxd3 Rhc8 17. h3 a6 18. Nd4`

FEN (line start): `r4b1r/pp3k1p/1q1p1np1/1Np5/4P3/8/PPPPQ1PP/R1B2RK1 b - - 1 12`

Game (full game at ply): http://localhost:5173/analysis?game_id=684745&ply=22

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4b1r/pp3k1p/1q1p1np1/1Np5/4P3/8/PPPPQ1PP/R1B2RK1%20b%20-%20-%201%2012

#### Case 977 — CLEARANCE (allowed, depth 4)

Moves (SAN): `12. Bxe7 Nxe7 13. Ne5 Bf5 14. Qg3 Ng6 15. Qe3 Rc8 16. Nc3 c5 17. Na4 Qd6`

FEN (line start): `r3k1nr/4bppp/pqp1p3/3p2B1/3P2b1/1P1Q1N2/P1P2PPP/RN3RK1 w - - 1 12`

Game (full game at ply): http://localhost:5173/analysis?game_id=684746&ply=21

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3k1nr/4bppp/pqp1p3/3p2B1/3P2b1/1P1Q1N2/P1P2PPP/RN3RK1%20w%20-%20-%201%2012

#### Case 978 — CLEARANCE (missed, depth 6)

Moves (SAN): `19... Qxg3+ 20. hxg3 a5 21. Rc1 Kd7 22. Rc2 Rhb8 23. Kg2 h5 24. Nf3 Ke7 25. Rh1`

FEN (line start): `r3k2r/5ppp/p1p1p3/3p4/2PP1qn1/1P4Q1/P2N1P1P/3R1RK1 b - - 0 19`

Game (full game at ply): http://localhost:5173/analysis?game_id=684746&ply=37

FEN (free-play from line start): http://localhost:5173/analysis?fen=r3k2r/5ppp/p1p1p3/3p4/2PP1qn1/1P4Q1/P2N1P1P/3R1RK1%20b%20-%20-%200%2019

#### Case 979 — HANGING_PIECE (allowed, depth 0)

Moves (SAN): `10... Qxf4 11. Rg1 e6 12. Qe2 Nd7 13. Nc3 Qf5 14. Rg5 Qh3+ 15. Kg1 Bd6 16. Rg2`

FEN (line start): `rn2kb1r/ppp1pppp/8/8/2B2Bq1/3P1N2/PPP2P2/RN1Q1R1K b - - 1 10`

Game (full game at ply): http://localhost:5173/analysis?game_id=684765&ply=18

FEN (free-play from line start): http://localhost:5173/analysis?fen=rn2kb1r/ppp1pppp/8/8/2B2Bq1/3P1N2/PPP2P2/RN1Q1R1K%20b%20-%20-%201%2010

#### Case 980 — CLEARANCE (missed, depth 4)

Moves (SAN): `10. Bg3 Nd7 11. Nh2 Qg6 12. Qf3 h5 13. Kh1`

FEN (line start): `rn2kb1r/ppp1pppp/8/8/2B2Bq1/3P1N2/PPP2P2/RN1Q1RK1 w - - 0 10`

Game (full game at ply): http://localhost:5173/analysis?game_id=684765&ply=18

FEN (free-play from line start): http://localhost:5173/analysis?fen=rn2kb1r/ppp1pppp/8/8/2B2Bq1/3P1N2/PPP2P2/RN1Q1RK1%20w%20-%20-%200%2010

#### Case 981 — CLEARANCE (allowed, depth 4)

Moves (SAN): `10. Bxf5 exf5`

FEN (line start): `2r1k1nr/pp3ppp/2n1p3/q2p1b2/1b1P1B2/2NB1N2/PPP2PPP/R2QK2R w - - 1 10`

Game (full game at ply): http://localhost:5173/analysis?game_id=684767&ply=17

FEN (free-play from line start): http://localhost:5173/analysis?fen=2r1k1nr/pp3ppp/2n1p3/q2p1b2/1b1P1B2/2NB1N2/PPP2PPP/R2QK2R%20w%20-%20-%201%2010

#### Case 982 — DEFLECTION (missed, depth 4)

Moves (SAN): `9... Bg4 10. Be3 Ba3 11. bxa3 Qxc3+ 12. Bd2 Qxa3`

FEN (line start): `2r1kbnr/pp3ppp/2n1p3/q2p1b2/3P1B2/2NB1N2/PPP2PPP/R2QK2R b - - 0 9`

Game (full game at ply): http://localhost:5173/analysis?game_id=684767&ply=17

FEN (free-play from line start): http://localhost:5173/analysis?fen=2r1kbnr/pp3ppp/2n1p3/q2p1b2/3P1B2/2NB1N2/PPP2PPP/R2QK2R%20b%20-%20-%200%209

#### Case 983 — PIN (allowed, depth 2)

Moves (SAN): `12. Bd2 Qa3 13. Qe2 Nf6`

FEN (line start): `2r1k1nr/pp3ppp/2n1p3/3p1B2/3P1B2/2q2N2/P1P2PPP/R2QK2R w - - 0 12`

Game (full game at ply): http://localhost:5173/analysis?game_id=684767&ply=21

FEN (free-play from line start): http://localhost:5173/analysis?fen=2r1k1nr/pp3ppp/2n1p3/3p1B2/3P1B2/2q2N2/P1P2PPP/R2QK2R%20w%20-%20-%200%2012

#### Case 984 — PIN (missed, depth 0)

Moves (SAN): `11... exf5`

FEN (line start): `2r1k1nr/pp3ppp/2n1p3/q2p1B2/3P1B2/2P2N2/P1P2PPP/R2QK2R b - - 0 11`

Game (full game at ply): http://localhost:5173/analysis?game_id=684767&ply=21

FEN (free-play from line start): http://localhost:5173/analysis?fen=2r1k1nr/pp3ppp/2n1p3/q2p1B2/3P1B2/2P2N2/P1P2PPP/R2QK2R%20b%20-%20-%200%2011

#### Case 985 — CLEARANCE (allowed, depth 8)

Moves (SAN): `14... Nxd4 15. Kh1 Nxf3 16. Rxf3 Bxc3 17. Bxc3 Rxf3 18. Qxf3 Rf8 19. Qg4 Qb6 20. Bd4`

FEN (line start): `r4rk1/qpp3pp/p1n1p3/3nP3/1b1P4/P1N2N2/1PPB2PP/R2Q1RK1 b - - 0 14`

Game (full game at ply): http://localhost:5173/analysis?game_id=684769&ply=26

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4rk1/qpp3pp/p1n1p3/3nP3/1b1P4/P1N2N2/1PPB2PP/R2Q1RK1%20b%20-%20-%200%2014

#### Case 986 — PROMOTION (missed, depth 2)

Moves (SAN): `35. d7 Kf7 36. d8=Q f3 37. Qd7+ Kg6 38. Qe6+ Kh7 39. Qf5+ g6 40. Qxf3 g5`

FEN (line start): `6k1/1p4p1/p2P4/4P3/5p2/P6P/6PK/8 w - - 0 35`

Game (full game at ply): http://localhost:5173/analysis?game_id=684769&ply=68

FEN (free-play from line start): http://localhost:5173/analysis?fen=6k1/1p4p1/p2P4/4P3/5p2/P6P/6PK/8%20w%20-%20-%200%2035

#### Case 987 — CLEARANCE (missed, depth 8)

Moves (SAN): `7. Bxb7 Bxb7 8. Qxb7 Nd7 9. Qc6 Be7 10. b3`

FEN (line start): `rnbqkb1r/ppp2ppp/4p3/3B4/8/5Q2/PPPP1PPP/R1B1K1NR w - - 0 7`

Game (full game at ply): http://localhost:5173/analysis?game_id=684778&ply=12

FEN (free-play from line start): http://localhost:5173/analysis?fen=rnbqkb1r/ppp2ppp/4p3/3B4/8/5Q2/PPPP1PPP/R1B1K1NR%20w%20-%20-%200%207

#### Case 988 — CLEARANCE (allowed, depth 8)

Moves (SAN): `24... Bb6 25. Kf1 Bxd4 26. cxd4 Rad8 27. Rd1 Rf5 28. Re7 Rdf8 29. Rd2 R8f7 30. Rxf7`

FEN (line start): `r4rk1/ppp3p1/4R3/b5p1/3N4/2P5/PP3PPP/R5K1 b - - 0 24`

Game (full game at ply): http://localhost:5173/analysis?game_id=684778&ply=46

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4rk1/ppp3p1/4R3/b5p1/3N4/2P5/PP3PPP/R5K1%20b%20-%20-%200%2024

#### Case 989 — DISCOVERED_ATTACK (allowed, depth 1)

Moves (SAN): `39... cxb3 40. axb3 Rxc3 41. Rb4 Rc1+ 42. Kh2 Rc5 43. Kg3 a5 44. Rb6+ Kf7 45. Kf3`

FEN (line start): `8/p7/4k1p1/2r3p1/2pR4/1PP4P/P4PP1/6K1 b - - 0 39`

Game (full game at ply): http://localhost:5173/analysis?game_id=684778&ply=76

FEN (free-play from line start): http://localhost:5173/analysis?fen=8/p7/4k1p1/2r3p1/2pR4/1PP4P/P4PP1/6K1%20b%20-%20-%200%2039

#### Case 990 — TRAPPED_PIECE (missed, depth 6)

Moves (SAN): `17... Qh6 18. Nf4 Bxf4 19. exf4 g6 20. g4 gxh5 21. g5 Qg6 22. Rae1 Rae8 23. Re3`

FEN (line start): `r4rk1/pp4pp/2nbp1q1/3p1p1B/3P3P/2P1PQP1/PP2N3/R4RK1 b - - 0 17`

Game (full game at ply): http://localhost:5173/analysis?game_id=684805&ply=33

FEN (free-play from line start): http://localhost:5173/analysis?fen=r4rk1/pp4pp/2nbp1q1/3p1p1B/3P3P/2P1PQP1/PP2N3/R4RK1%20b%20-%20-%200%2017

#### Case 991 — INTERMEZZO (allowed, depth 2)

Moves (SAN): `8... hxg5 9. a4 gxf6 10. axb5 cxb5 11. Nxb5 Bb4+ 12. Nc3 Kf8 13. g3 Bb7 14. Bg2`

FEN (line start): `rnbqkb1r/p4pp1/2p1pP1p/1p4B1/2pP4/2N2N2/PP3PPP/R2QKB1R b - - 0 8`

Game (full game at ply): http://localhost:5173/analysis?game_id=684809&ply=14

FEN (free-play from line start): http://localhost:5173/analysis?fen=rnbqkb1r/p4pp1/2p1pP1p/1p4B1/2pP4/2N2N2/PP3PPP/R2QKB1R%20b%20-%20-%200%208

#### Case 992 — HANGING_PIECE (missed, depth 0)

Moves (SAN): `13. dxe5 Qxd2+ 14. Kxd2 Nd7 15. Bxg4 Nxe5 16. Be2 Ke7 17. f4 Ng6 18. g3 e5`

FEN (line start): `rnbqk2r/p4p2/2p1p3/1p2b3/2pP2p1/2N5/PP1QBPPP/R3K2R w - - 0 13`

Game (full game at ply): http://localhost:5173/analysis?game_id=684809&ply=24

FEN (free-play from line start): http://localhost:5173/analysis?fen=rnbqk2r/p4p2/2p1p3/1p2b3/2pP2p1/2N5/PP1QBPPP/R3K2R%20w%20-%20-%200%2013

#### Case 993 — DISCOVERED_ATTACK (allowed, depth 1)

Moves (SAN): `12. Nxf6+ gxf6 13. Qxf5 Bxd2+ 14. Kxd2 Qc3+ 15. Kc1 dxe3 16. Kb1 Qb4+ 17. Ka1 Nc6`

FEN (line start): `rn3rk1/pp3ppp/5p2/5b2/1b1pN3/3QP3/PqPN1PPP/3RKB1R w - - 1 12`

Game (full game at ply): http://localhost:5173/analysis?game_id=684813&ply=21

FEN (free-play from line start): http://localhost:5173/analysis?fen=rn3rk1/pp3ppp/5p2/5b2/1b1pN3/3QP3/PqPN1PPP/3RKB1R%20w%20-%20-%201%2012

#### Case 994 — ATTRACTION (allowed, depth 2)

Moves (SAN): `29. Qxe3 Qxb8 30. Bxf7+ Kxf7 31. Qe6+ Kg6 32. Qxd5 h5 33. Qd3+ Kh6 34. Qe3+ g5`

FEN (line start): `1R2B1k1/p4pp1/5p1p/3r4/8/2P1n1qP/P2Q2P1/4R2K w - - 1 29`

Game (full game at ply): http://localhost:5173/analysis?game_id=684813&ply=55

FEN (free-play from line start): http://localhost:5173/analysis?fen=1R2B1k1/p4pp1/5p1p/3r4/8/2P1n1qP/P2Q2P1/4R2K%20w%20-%20-%201%2029

#### Case 995 — INTERFERENCE (allowed, depth 4)

Moves (SAN): `30. Rxd1 g6 31. Qf3 Qxb8 32. Qxe3 Qb7 33. Re1 Kg7 34. Qd4 h5`

FEN (line start): `1R2B1k1/p4pp1/5p1p/8/8/2P1n1qP/P3Q1P1/3rR2K w - - 1 30`

Game (full game at ply): http://localhost:5173/analysis?game_id=684813&ply=57

FEN (free-play from line start): http://localhost:5173/analysis?fen=1R2B1k1/p4pp1/5p1p/8/8/2P1n1qP/P3Q1P1/3rR2K%20w%20-%20-%201%2030

#### Case 996 — HANGING_PIECE (missed, depth 0)

Moves (SAN): `29... Qxb8 30. Bxf7+ Kxf7 31. Qxe3 Re5 32. Qd2 Rxe1+ 33. Qxe1 a5 34. Qd1 Qe5 35. c4`

FEN (line start): `1R2B1k1/p4pp1/5p1p/3r4/8/2P1n1qP/P3Q1P1/4R2K b - - 0 29`

Game (full game at ply): http://localhost:5173/analysis?game_id=684813&ply=57

FEN (free-play from line start): http://localhost:5173/analysis?fen=1R2B1k1/p4pp1/5p1p/3r4/8/2P1n1qP/P3Q1P1/4R2K%20b%20-%20-%200%2029

#### Case 997 — PROMOTION (allowed, depth 4)

Moves (SAN): `64. Qxe5 fxe5 65. c7 Kg6 66. c8=Q Kf6 67. Bc2 e4 68. Bxe4 g6 69. Qd8+ Kg7`

FEN (line start): `8/5ppk/2PK1p1p/1Q2q3/B7/7P/6P1/8 w - - 1 64`

Game (full game at ply): http://localhost:5173/analysis?game_id=684813&ply=125

FEN (free-play from line start): http://localhost:5173/analysis?fen=8/5ppk/2PK1p1p/1Q2q3/B7/7P/6P1/8%20w%20-%20-%201%2064

#### Case 998 — PIN (missed, depth 8)

Moves (SAN): `69... f5 70. c8=Q Qd6+ 71. Kb7 Qe7+ 72. Qcd7 Qe4+ 73. Qbd5 Kg5 74. Qxe4 fxe4 75. Qxf7`

FEN (line start): `1K6/2P1qpp1/5pkp/1Q6/B7/7P/6P1/8 b - - 0 69`

Game (full game at ply): http://localhost:5173/analysis?game_id=684813&ply=137

FEN (free-play from line start): http://localhost:5173/analysis?fen=1K6/2P1qpp1/5pkp/1Q6/B7/7P/6P1/8%20b%20-%20-%200%2069

#### Case 999 — CLEARANCE (allowed, depth 10)

Moves (SAN): `14. Nxd5 Be7 15. Qb3`

FEN (line start): `r2qkb1r/pp3ppp/2n5/3pPp2/8/2N1B3/PP3PPP/R2Q1RK1 w - - 0 14`

Game (full game at ply): http://localhost:5173/analysis?game_id=684824&ply=25

FEN (free-play from line start): http://localhost:5173/analysis?fen=r2qkb1r/pp3ppp/2n5/3pPp2/8/2N1B3/PP3PPP/R2Q1RK1%20w%20-%20-%200%2014

#### Case 1000 — DEFLECTION (allowed, depth 6)

Moves (SAN): `13... Qh4 14. Re1 Qxh2+ 15. Kf1 Qh1+ 16. Ke2 Qxg2 17. Rg1 Qf3+ 18. Ke1 Qf4 19. Ne2`

FEN (line start): `rn2k2r/pp1bqpp1/3p4/2pPp3/2P1P1p1/2NB4/PP3PPN/R2Q1RK1 b - - 1 13`

Game (full game at ply): http://localhost:5173/analysis?game_id=684851&ply=24

FEN (free-play from line start): http://localhost:5173/analysis?fen=rn2k2r/pp1bqpp1/3p4/2pPp3/2P1P1p1/2NB4/PP3PPN/R2Q1RK1%20b%20-%20-%201%2013

## False Negative Count (HUMAN-UAT — fill in after hand-check)

- **Total dropped:** 1467
- **False negatives (good tags killed):** _[fill in after reviewing each case above]_
- **Correct drops (noise):** _[fill in]_

## A/B Summary & Margin Justification

Margin 0.35 — confirm or change based on hand-check results.
`ONLY_MOVE_WIN_PROB_MARGIN` in `forcing_line_gate.py` line 52 will be updated with a
pointer comment to this report after the hand-check is complete (Plan 02).

*Generated by `scripts/ab_validate_gate.py --db dev --user-id 28 --margin 0.35`.*
