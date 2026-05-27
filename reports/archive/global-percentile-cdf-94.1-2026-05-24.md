# FlawChess Global Percentile CDF — 2026-05-22

- **DB**: benchmark (Docker on localhost:5433, flawchess_benchmark)
- **Snapshot taken**: 2026-05-22T16:49:53Z
- **Benchmark DB snapshot month**: 2026-03
- **Methodology**: see `.claude/skills/benchmarks/SKILL.md` Chapter 4.
- **Canonical CTE inherited verbatim** from SKILL.md §1 (selected_users + checkpoint-status filter + game-time ELO bucketing + sparse-cell `(2400, classical)` exclusion + universal equal-footing opponent filter `|opp - user| ≤ 100`).
- **Breakpoint set**: every integer percentile p1..p99 (99 entries, no sub-percent steps). Values rendered in pp (×100, one decimal).
- **Cohort sizes (post per-metric inclusion floor)**:
  - **Endgame Score Gap** (`score_gap`): n_users = 2003
  - **Achievable Score Gap** (`achievable_score_gap`): n_users = 2299
  - **Section 2 Conversion ΔES** (`section2_score_gap_conv`): n_users = 2060
  - **Section 2 Parity ΔES** (`section2_score_gap_parity`): n_users = 1804

## Endgame Score Gap (`score_gap`)

- **Cohort size**: n_users = 2003
- **Inclusion floor**: score_gap — inclusion floor ≥30 endgame AND ≥30 non-endgame games per user.
- **Sparse cell** `(2400, classical)` excluded from the pooled distribution.

### Breakpoint table (p1..p99)

| percentile | value (pp) |
|---:|---:|
| p1 | -31.5pp |
| p2 | -28.3pp |
| p3 | -26.2pp |
| p4 | -23.6pp |
| p5 | -22.1pp |
| p6 | -20.7pp |
| p7 | -19.8pp |
| p8 | -19.0pp |
| p9 | -18.0pp |
| p10 | -17.4pp |
| p11 | -16.9pp |
| p12 | -16.1pp |
| p13 | -15.5pp |
| p14 | -14.8pp |
| p15 | -14.2pp |
| p16 | -13.8pp |
| p17 | -13.4pp |
| p18 | -13.0pp |
| p19 | -12.5pp |
| p20 | -12.1pp |
| p21 | -11.6pp |
| p22 | -11.3pp |
| p23 | -10.8pp |
| p24 | -10.4pp |
| p25 | -10.1pp |
| p26 | -9.6pp |
| p27 | -9.2pp |
| p28 | -8.9pp |
| p29 | -8.5pp |
| p30 | -8.2pp |
| p31 | -7.8pp |
| p32 | -7.4pp |
| p33 | -7.1pp |
| p34 | -6.7pp |
| p35 | -6.4pp |
| p36 | -6.2pp |
| p37 | -5.7pp |
| p38 | -5.4pp |
| p39 | -5.0pp |
| p40 | -4.7pp |
| p41 | -4.4pp |
| p42 | -4.0pp |
| p43 | -3.5pp |
| p44 | -3.3pp |
| p45 | -3.0pp |
| p46 | -2.6pp |
| p47 | -2.1pp |
| p48 | -1.8pp |
| p49 | -1.4pp |
| p50 | -1.2pp |
| p51 | -1.0pp |
| p52 | -0.6pp |
| p53 | -0.2pp |
| p54 | +0.1pp |
| p55 | +0.5pp |
| p56 | +0.7pp |
| p57 | +1.1pp |
| p58 | +1.4pp |
| p59 | +1.7pp |
| p60 | +2.0pp |
| p61 | +2.3pp |
| p62 | +2.6pp |
| p63 | +2.8pp |
| p64 | +3.2pp |
| p65 | +3.7pp |
| p66 | +4.1pp |
| p67 | +4.5pp |
| p68 | +4.9pp |
| p69 | +5.4pp |
| p70 | +5.9pp |
| p71 | +6.1pp |
| p72 | +6.5pp |
| p73 | +6.9pp |
| p74 | +7.4pp |
| p75 | +7.8pp |
| p76 | +8.2pp |
| p77 | +8.7pp |
| p78 | +9.1pp |
| p79 | +9.5pp |
| p80 | +9.8pp |
| p81 | +10.5pp |
| p82 | +10.9pp |
| p83 | +11.5pp |
| p84 | +12.1pp |
| p85 | +12.7pp |
| p86 | +13.3pp |
| p87 | +14.0pp |
| p88 | +14.6pp |
| p89 | +15.2pp |
| p90 | +15.9pp |
| p91 | +16.7pp |
| p92 | +17.4pp |
| p93 | +18.2pp |
| p94 | +19.6pp |
| p95 | +20.9pp |
| p96 | +22.3pp |
| p97 | +24.3pp |
| p98 | +25.7pp |
| p99 | +29.2pp |

### Per-rating-bucket sanity check

| rating bucket | n_users | median (pp) | skew | excess kurt |
|---|---:|---:|---:|---:|
| 800 (game-time) | 342 | -3.1pp | +0.3118 | -0.1074 |
| 1200 (game-time) | 484 | -2.1pp | +0.0937 | -0.0139 |
| 1600 (game-time) | 501 | -0.6pp | -0.1838 | -0.0119 |
| 2000 (game-time) | 414 | -0.2pp | +0.0174 | +0.0618 |
| 2400 (game-time) | 262 | +0.9pp | -0.0750 | -0.2272 |

## Achievable Score Gap (`achievable_score_gap`)

- **Cohort size**: n_users = 2299
- **Inclusion floor**: achievable_score_gap — inclusion floor ≥20 endgame-entry games per user.
- **Sparse cell** `(2400, classical)` excluded from the pooled distribution.

### Breakpoint table (p1..p99)

| percentile | value (pp) |
|---:|---:|
| p1 | -21.8pp |
| p2 | -18.8pp |
| p3 | -15.7pp |
| p4 | -14.3pp |
| p5 | -13.2pp |
| p6 | -12.3pp |
| p7 | -11.5pp |
| p8 | -10.9pp |
| p9 | -10.0pp |
| p10 | -9.3pp |
| p11 | -8.8pp |
| p12 | -8.3pp |
| p13 | -7.9pp |
| p14 | -7.5pp |
| p15 | -7.1pp |
| p16 | -6.8pp |
| p17 | -6.4pp |
| p18 | -6.0pp |
| p19 | -5.7pp |
| p20 | -5.3pp |
| p21 | -5.1pp |
| p22 | -4.8pp |
| p23 | -4.5pp |
| p24 | -4.3pp |
| p25 | -4.0pp |
| p26 | -3.8pp |
| p27 | -3.5pp |
| p28 | -3.4pp |
| p29 | -3.2pp |
| p30 | -3.0pp |
| p31 | -2.8pp |
| p32 | -2.6pp |
| p33 | -2.4pp |
| p34 | -2.1pp |
| p35 | -1.9pp |
| p36 | -1.8pp |
| p37 | -1.6pp |
| p38 | -1.4pp |
| p39 | -1.3pp |
| p40 | -1.1pp |
| p41 | -0.9pp |
| p42 | -0.8pp |
| p43 | -0.7pp |
| p44 | -0.5pp |
| p45 | -0.3pp |
| p46 | -0.1pp |
| p47 | +0.1pp |
| p48 | +0.3pp |
| p49 | +0.4pp |
| p50 | +0.6pp |
| p51 | +0.8pp |
| p52 | +0.9pp |
| p53 | +1.1pp |
| p54 | +1.3pp |
| p55 | +1.5pp |
| p56 | +1.7pp |
| p57 | +1.9pp |
| p58 | +2.0pp |
| p59 | +2.3pp |
| p60 | +2.4pp |
| p61 | +2.6pp |
| p62 | +2.7pp |
| p63 | +2.9pp |
| p64 | +3.1pp |
| p65 | +3.2pp |
| p66 | +3.4pp |
| p67 | +3.6pp |
| p68 | +3.8pp |
| p69 | +3.9pp |
| p70 | +4.1pp |
| p71 | +4.3pp |
| p72 | +4.4pp |
| p73 | +4.6pp |
| p74 | +4.8pp |
| p75 | +5.0pp |
| p76 | +5.2pp |
| p77 | +5.5pp |
| p78 | +5.7pp |
| p79 | +6.0pp |
| p80 | +6.2pp |
| p81 | +6.4pp |
| p82 | +6.7pp |
| p83 | +7.0pp |
| p84 | +7.3pp |
| p85 | +7.6pp |
| p86 | +7.8pp |
| p87 | +8.2pp |
| p88 | +8.7pp |
| p89 | +9.1pp |
| p90 | +9.6pp |
| p91 | +10.1pp |
| p92 | +10.8pp |
| p93 | +11.3pp |
| p94 | +12.2pp |
| p95 | +13.0pp |
| p96 | +13.9pp |
| p97 | +15.2pp |
| p98 | +17.5pp |
| p99 | +20.8pp |

### Per-rating-bucket sanity check

| rating bucket | n_users | median (pp) | skew | excess kurt |
|---|---:|---:|---:|---:|
| 800 (game-time) | 374 | -0.9pp | +0.0205 | +1.6107 |
| 1200 (game-time) | 541 | -0.5pp | -0.1605 | +2.1253 |
| 1600 (game-time) | 575 | +0.2pp | -0.2657 | +1.3070 |
| 2000 (game-time) | 498 | +1.5pp | -0.2223 | +1.2936 |
| 2400 (game-time) | 311 | +2.6pp | -1.1254 | +4.0891 |

## Section 2 Conversion ΔES (`section2_score_gap_conv`)

- **Cohort size**: n_users = 2060
- **Inclusion floor**: section2_score_gap_conv — inclusion floor ≥20 spans per entry-eval bucket.
- **Sparse cell** `(2400, classical)` excluded from the pooled distribution.

### Breakpoint table (p1..p99)

| percentile | value (pp) |
|---:|---:|
| p1 | -34.6pp |
| p2 | -31.1pp |
| p3 | -29.0pp |
| p4 | -26.9pp |
| p5 | -24.8pp |
| p6 | -23.8pp |
| p7 | -22.4pp |
| p8 | -21.5pp |
| p9 | -20.3pp |
| p10 | -19.2pp |
| p11 | -18.4pp |
| p12 | -17.8pp |
| p13 | -17.2pp |
| p14 | -16.4pp |
| p15 | -15.9pp |
| p16 | -15.1pp |
| p17 | -14.5pp |
| p18 | -13.9pp |
| p19 | -13.5pp |
| p20 | -13.1pp |
| p21 | -12.7pp |
| p22 | -12.3pp |
| p23 | -12.1pp |
| p24 | -11.7pp |
| p25 | -11.3pp |
| p26 | -10.9pp |
| p27 | -10.6pp |
| p28 | -10.2pp |
| p29 | -9.9pp |
| p30 | -9.5pp |
| p31 | -9.2pp |
| p32 | -8.9pp |
| p33 | -8.6pp |
| p34 | -8.3pp |
| p35 | -7.9pp |
| p36 | -7.7pp |
| p37 | -7.5pp |
| p38 | -7.3pp |
| p39 | -7.1pp |
| p40 | -6.8pp |
| p41 | -6.6pp |
| p42 | -6.5pp |
| p43 | -6.2pp |
| p44 | -6.1pp |
| p45 | -6.0pp |
| p46 | -5.8pp |
| p47 | -5.6pp |
| p48 | -5.4pp |
| p49 | -5.2pp |
| p50 | -5.0pp |
| p51 | -4.8pp |
| p52 | -4.5pp |
| p53 | -4.3pp |
| p54 | -4.2pp |
| p55 | -4.0pp |
| p56 | -3.8pp |
| p57 | -3.7pp |
| p58 | -3.5pp |
| p59 | -3.3pp |
| p60 | -3.1pp |
| p61 | -2.8pp |
| p62 | -2.6pp |
| p63 | -2.4pp |
| p64 | -2.2pp |
| p65 | -2.0pp |
| p66 | -1.8pp |
| p67 | -1.7pp |
| p68 | -1.4pp |
| p69 | -1.2pp |
| p70 | -0.9pp |
| p71 | -0.7pp |
| p72 | -0.5pp |
| p73 | -0.3pp |
| p74 | -0.1pp |
| p75 | +0.1pp |
| p76 | +0.4pp |
| p77 | +0.7pp |
| p78 | +0.9pp |
| p79 | +1.2pp |
| p80 | +1.5pp |
| p81 | +1.7pp |
| p82 | +1.9pp |
| p83 | +2.2pp |
| p84 | +2.4pp |
| p85 | +2.7pp |
| p86 | +3.0pp |
| p87 | +3.4pp |
| p88 | +3.6pp |
| p89 | +3.9pp |
| p90 | +4.3pp |
| p91 | +4.5pp |
| p92 | +5.0pp |
| p93 | +5.5pp |
| p94 | +6.0pp |
| p95 | +6.8pp |
| p96 | +7.6pp |
| p97 | +8.2pp |
| p98 | +9.2pp |
| p99 | +10.5pp |

### Per-rating-bucket sanity check

| rating bucket | n_users | median (pp) | skew | excess kurt |
|---|---:|---:|---:|---:|
| 800 (game-time) | 336 | -10.9pp | -1.0777 | +1.2445 |
| 1200 (game-time) | 494 | -6.5pp | -1.0485 | +1.6716 |
| 1600 (game-time) | 514 | -4.1pp | -0.8603 | +0.7136 |
| 2000 (game-time) | 435 | -1.5pp | -0.9337 | +0.9416 |
| 2400 (game-time) | 281 | -1.3pp | -0.3811 | +0.3628 |

## Section 2 Parity ΔES (`section2_score_gap_parity`)

- **Cohort size**: n_users = 1804
- **Inclusion floor**: section2_score_gap_parity — inclusion floor ≥20 spans per entry-eval bucket.
- **Sparse cell** `(2400, classical)` excluded from the pooled distribution.

### Breakpoint table (p1..p99)

| percentile | value (pp) |
|---:|---:|
| p1 | -17.0pp |
| p2 | -14.7pp |
| p3 | -13.0pp |
| p4 | -11.6pp |
| p5 | -10.6pp |
| p6 | -9.9pp |
| p7 | -9.4pp |
| p8 | -8.9pp |
| p9 | -8.5pp |
| p10 | -8.1pp |
| p11 | -7.7pp |
| p12 | -7.3pp |
| p13 | -6.8pp |
| p14 | -6.5pp |
| p15 | -6.2pp |
| p16 | -5.9pp |
| p17 | -5.6pp |
| p18 | -5.3pp |
| p19 | -5.0pp |
| p20 | -4.6pp |
| p21 | -4.4pp |
| p22 | -4.2pp |
| p23 | -4.0pp |
| p24 | -3.8pp |
| p25 | -3.6pp |
| p26 | -3.5pp |
| p27 | -3.3pp |
| p28 | -3.1pp |
| p29 | -2.9pp |
| p30 | -2.7pp |
| p31 | -2.5pp |
| p32 | -2.2pp |
| p33 | -2.1pp |
| p34 | -1.9pp |
| p35 | -1.7pp |
| p36 | -1.6pp |
| p37 | -1.4pp |
| p38 | -1.3pp |
| p39 | -1.2pp |
| p40 | -1.0pp |
| p41 | -0.9pp |
| p42 | -0.7pp |
| p43 | -0.6pp |
| p44 | -0.4pp |
| p45 | -0.4pp |
| p46 | -0.2pp |
| p47 | -0.1pp |
| p48 | +0.1pp |
| p49 | +0.2pp |
| p50 | +0.3pp |
| p51 | +0.5pp |
| p52 | +0.7pp |
| p53 | +0.8pp |
| p54 | +0.9pp |
| p55 | +1.0pp |
| p56 | +1.1pp |
| p57 | +1.3pp |
| p58 | +1.4pp |
| p59 | +1.6pp |
| p60 | +1.7pp |
| p61 | +1.8pp |
| p62 | +2.0pp |
| p63 | +2.1pp |
| p64 | +2.3pp |
| p65 | +2.4pp |
| p66 | +2.5pp |
| p67 | +2.7pp |
| p68 | +2.9pp |
| p69 | +3.0pp |
| p70 | +3.1pp |
| p71 | +3.3pp |
| p72 | +3.5pp |
| p73 | +3.7pp |
| p74 | +3.8pp |
| p75 | +4.0pp |
| p76 | +4.3pp |
| p77 | +4.5pp |
| p78 | +4.7pp |
| p79 | +4.9pp |
| p80 | +5.1pp |
| p81 | +5.3pp |
| p82 | +5.5pp |
| p83 | +5.8pp |
| p84 | +6.0pp |
| p85 | +6.2pp |
| p86 | +6.4pp |
| p87 | +6.7pp |
| p88 | +7.0pp |
| p89 | +7.3pp |
| p90 | +7.5pp |
| p91 | +8.0pp |
| p92 | +8.3pp |
| p93 | +8.7pp |
| p94 | +9.2pp |
| p95 | +10.1pp |
| p96 | +11.0pp |
| p97 | +12.2pp |
| p98 | +14.0pp |
| p99 | +16.6pp |

### Per-rating-bucket sanity check

| rating bucket | n_users | median (pp) | skew | excess kurt |
|---|---:|---:|---:|---:|
| 800 (game-time) | 211 | +0.1pp | -0.5162 | +0.5974 |
| 1200 (game-time) | 399 | -0.6pp | +0.1963 | +0.8430 |
| 1600 (game-time) | 469 | -0.2pp | -0.0168 | +1.6441 |
| 2000 (game-time) | 434 | +0.8pp | -0.0711 | +1.6119 |
| 2400 (game-time) | 291 | +1.4pp | -0.1698 | +1.1852 |
