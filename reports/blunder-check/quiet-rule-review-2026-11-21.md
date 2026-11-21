# Quiet-point rule review (Phase 259 D-09)

## Totals

- rows: 291
- rows with any changed value: 194
- changed values, played line: 143
- changed values, best line: 179
- stored loss / missed cells that drift from the recomputed quiet value: 0 (expected 0)

## Changed values by cause, line and depth

| line | depth | exchange_settled_at_end | longer_exchange_settled | later_capture_pulled_earlier | other | total |
|---|---|---|---|---|---|---|
| played | 1 | 0 | 41 | 0 | 0 | 41 |
| played | 3 | 0 | 28 | 0 | 0 | 28 |
| played | 5 | 0 | 27 | 0 | 0 | 27 |
| played | 7 | 0 | 18 | 0 | 0 | 18 |
| played | 9 | 8 | 21 | 0 | 0 | 29 |
| best | 1 | 0 | 38 | 0 | 0 | 38 |
| best | 3 | 0 | 55 | 0 | 0 | 55 |
| best | 5 | 0 | 37 | 0 | 0 | 37 |
| best | 7 | 6 | 14 | 0 | 0 | 20 |
| best | 9 | 29 | 0 | 0 | 0 | 29 |
| all | all | 43 | 279 | 0 | 0 | 322 |

## Rows whose loss or missed moved by more than 1e-06

162 of 291 rows.

- n=189 set=6 label=1 https://flawchess.com/analysis?game_id=2632426&ply=25: loss 2.452 -> 4.000, missed 1.935 -> 0.000
- n=106 set=5 label=0 https://flawchess.com/analysis?game_id=3230634&ply=39: loss 0.226 -> 1.000, missed 2.677 -> 0.000
- n=163 set=6 label=1 https://flawchess.com/analysis?game_id=1074062&ply=19: loss 2.419 -> 5.000, missed 0.774 -> 0.000
- n=111 set=5 label=0 https://flawchess.com/analysis?game_id=1581100&ply=43: loss 0.065 -> 0.194, missed 2.581 -> 0.000
- n=102 set=5 label=0 https://flawchess.com/analysis?game_id=2312975&ply=27: loss 0.000 -> 0.000, missed 2.645 -> 0.000
- n=261 set=8 label=0 https://flawchess.com/analysis?game_id=1535857&ply=152: loss 0.484 -> 1.129, missed 2.935 -> 1.000
- n=155 set=6 label=1 https://flawchess.com/analysis?game_id=496096&ply=29: loss 5.000 -> 5.000, missed 2.581 -> 0.000
- n=215 set=7 label=1 https://flawchess.com/analysis?game_id=3193193&ply=37: loss 2.419 -> 5.000, missed 0.581 -> 0.581
- n=297 set=8 label=0 https://flawchess.com/analysis?game_id=2207313&ply=28: loss 1.129 -> 1.129, missed 2.581 -> 0.000
- n=extra set=extra label=- https://flawchess.com/analysis?game_id=2883555&ply=47: loss 2.935 -> 2.935, missed 2.581 -> 0.000
- n=69 set=3 label=1 https://flawchess.com/analysis?game_id=606033&ply=45: loss 1.677 -> 3.226, missed 0.774 -> 0.000
- n=238 set=7 label=0 https://flawchess.com/analysis?game_id=2042680&ply=14: loss 0.000 -> 0.000, missed 3.032 -> 0.710
- n=277 set=8 label=1 https://flawchess.com/analysis?game_id=1429319&ply=20: loss 1.194 -> 2.806, missed 3.516 -> 3.000
- n=115 set=5 label=1 https://flawchess.com/analysis?game_id=492808&ply=73: loss 2.419 -> 2.419, missed 2.065 -> 0.000
- n=251 set=8 label=0 https://flawchess.com/analysis?game_id=1871758&ply=50: loss 0.000 -> 0.000, missed 2.935 -> 0.968
- n=76 set=4 label=0.5 https://flawchess.com/analysis?game_id=625770&ply=21: loss 0.097 -> 0.484, missed 1.548 -> 0.000
- n=169 set=6 label=1 https://flawchess.com/analysis?game_id=1220300&ply=33: loss 1.419 -> 3.000, missed 0.194 -> 0.000
- n=145 set=6 label=1 https://flawchess.com/analysis?game_id=3189857&ply=39: loss 2.774 -> 3.000, missed 1.516 -> 0.000
- n=64 set=3 label=1 https://flawchess.com/analysis?game_id=2602392&ply=46: loss 1.452 -> 3.000, missed 0.129 -> 0.000
- n=66 set=3 label=0 https://flawchess.com/analysis?game_id=2499164&ply=35: loss 2.000 -> 2.000, missed 2.323 -> 0.774
- n=81 set=4 label=1 https://flawchess.com/analysis?game_id=2792123&ply=47: loss 5.000 -> 5.000, missed 1.645 -> 0.097
- n=75 set=4 label=1 https://flawchess.com/analysis?game_id=2446731&ply=46: loss 0.000 -> 0.000, missed 3.645 -> 2.097
- n=164 set=6 label=1 https://flawchess.com/analysis?game_id=476993&ply=14: loss 0.387 -> 0.387, missed 2.581 -> 1.032
- n=240 set=7 label=1 https://flawchess.com/analysis?game_id=2561505&ply=41: loss 0.968 -> 0.968, missed 3.097 -> 1.548
- n=244 set=8 label=1 https://flawchess.com/analysis?game_id=2068559&ply=31: loss 1.935 -> 3.484, missed 0.000 -> 0.000
- n=253 set=8 label=0.5 https://flawchess.com/analysis?game_id=505289&ply=21: loss 0.000 -> 0.000, missed 2.645 -> 1.097
- n=255 set=8 label=0 https://flawchess.com/analysis?game_id=2805263&ply=39: loss 0.000 -> 0.000, missed 1.548 -> 0.000
- n=267 set=8 label=0 https://flawchess.com/analysis?game_id=2754513&ply=28: loss 0.000 -> 0.000, missed 1.548 -> 0.000
- n=273 set=8 label=0 https://flawchess.com/analysis?game_id=2022738&ply=78: loss 1.387 -> 2.935, missed 0.000 -> 0.000
- n=292 set=8 label=1 https://flawchess.com/analysis?game_id=1551685&ply=33: loss 2.194 -> 2.968, missed 0.742 -> 1.484
- n=131 set=5 label=0 https://flawchess.com/analysis?game_id=2782206&ply=41: loss 0.000 -> 0.000, missed 1.871 -> 0.387
- n=132 set=5 label=1 https://flawchess.com/analysis?game_id=1588738&ply=51: loss 4.839 -> 4.903, missed 1.290 -> 0.000
- n=221 set=7 label=0.5 https://flawchess.com/analysis?game_id=2652587&ply=34: loss 0.290 -> 0.290, missed 3.355 -> 2.065
- n=222 set=7 label=0 https://flawchess.com/analysis?game_id=2413774&ply=13: loss 0.000 -> 0.000, missed 2.258 -> 0.968
- n=278 set=8 label=0 https://flawchess.com/analysis?game_id=2241067&ply=19: loss 0.000 -> 0.000, missed 2.290 -> 1.000
- n=142 set=6 label=0 https://flawchess.com/analysis?game_id=1995151&ply=29: loss 0.000 -> 0.000, missed 1.323 -> 0.032
- n=146 set=6 label=1 https://flawchess.com/analysis?game_id=2742995&ply=51: loss 1.032 -> 1.032, missed 1.290 -> 0.000
- n=265 set=8 label=0 https://flawchess.com/analysis?game_id=2494184&ply=26: loss 2.871 -> 2.871, missed 1.452 -> 0.161
- n=276 set=8 label=0 https://flawchess.com/analysis?game_id=3125059&ply=25: loss 1.710 -> 3.000, missed 0.000 -> 0.000
- n=167 set=6 label=0 https://flawchess.com/analysis?game_id=2613053&ply=11: loss 0.000 -> 0.000, missed 4.387 -> 3.097
- n=14 set=1 label=0 https://flawchess.com/analysis?game_id=2669428&ply=59: loss 0.871 -> 1.903, missed 0.968 -> 0.774
- n=148 set=6 label=1 https://flawchess.com/analysis?game_id=1460085&ply=12: loss 2.806 -> 3.000, missed 1.032 -> 0.000
- n=263 set=8 label=1 https://flawchess.com/analysis?game_id=2674500&ply=33: loss 0.000 -> 0.000, missed 2.742 -> 3.903
- n=256 set=8 label=0 https://flawchess.com/analysis?game_id=2937604&ply=19: loss 0.000 -> 0.000, missed 4.161 -> 3.000
- n=60 set=3 label=1 https://flawchess.com/analysis?game_id=2709092&ply=81: loss 1.226 -> 2.258, missed 0.000 -> 0.000
- n=15 set=1 label=1 https://flawchess.com/analysis?game_id=2625135&ply=12: loss 0.323 -> 1.097, missed 0.548 -> 0.290
- n=112 set=5 label=1 https://flawchess.com/analysis?game_id=2439721&ply=64: loss 1.806 -> 1.806, missed 1.032 -> 0.000
- n=165 set=6 label=0 https://flawchess.com/analysis?game_id=3197784&ply=11: loss 0.968 -> 0.968, missed 1.484 -> 0.452
- n=195 set=7 label=1 https://flawchess.com/analysis?game_id=1995536&ply=24: loss 0.000 -> 0.000, missed 1.032 -> 0.000
- n=272 set=8 label=1 https://flawchess.com/analysis?game_id=2557076&ply=9: loss 0.516 -> 1.548, missed 1.742 -> 1.742
- n=283 set=8 label=1 https://flawchess.com/analysis?game_id=3118071&ply=19: loss 0.516 -> 1.548, missed 0.000 -> 0.000
- n=284 set=8 label=1 https://flawchess.com/analysis?game_id=2241758&ply=34: loss 0.000 -> 0.000, missed 4.129 -> 3.097
- n=285 set=8 label=1 https://flawchess.com/analysis?game_id=2637772&ply=11: loss 0.968 -> 2.000, missed 0.226 -> 0.226
- n=296 set=8 label=0 https://flawchess.com/analysis?game_id=2739857&ply=23: loss 2.258 -> 3.032, missed 0.258 -> 0.000
- n=199 set=7 label=1 https://flawchess.com/analysis?game_id=2864428&ply=37: loss 3.000 -> 3.000, missed 3.774 -> 3.000
- n=220 set=7 label=0 https://flawchess.com/analysis?game_id=1161949&ply=26: loss 0.000 -> 0.000, missed 4.226 -> 5.000
- n=95 set=5 label=1 https://flawchess.com/analysis?game_id=1237218&ply=52: loss 0.097 -> 0.484, missed 0.903 -> 0.516
- n=99 set=5 label=1 https://flawchess.com/analysis?game_id=2972865&ply=27: loss 0.516 -> 1.290, missed 0.000 -> 0.000
- n=171 set=6 label=1 https://flawchess.com/analysis?game_id=2274686&ply=32: loss 3.000 -> 3.000, missed 0.774 -> 0.000
- n=226 set=7 label=0 https://flawchess.com/analysis?game_id=473003&ply=13: loss 0.000 -> 0.000, missed 0.774 -> 0.000
- n=230 set=7 label=0 https://flawchess.com/analysis?game_id=2660513&ply=35: loss 0.710 -> 1.000, missed 1.484 -> 1.000
- n=254 set=8 label=0 https://flawchess.com/analysis?game_id=2081002&ply=40: loss 0.000 -> 0.000, missed 1.129 -> 1.903
- n=264 set=8 label=0 https://flawchess.com/analysis?game_id=2459567&ply=66: loss 1.129 -> 1.129, missed 0.774 -> 0.000
- n=295 set=8 label=0 https://flawchess.com/analysis?game_id=1431266&ply=17: loss 0.000 -> 0.000, missed 1.774 -> 1.000
- n=77 set=4 label=1 https://flawchess.com/analysis?game_id=2811460&ply=27: loss 0.710 -> 0.968, missed 0.774 -> 1.194
- n=11 set=1 label=1 https://flawchess.com/analysis?game_id=2752284&ply=53: loss 0.548 -> 0.548, missed 0.645 -> 0.000
- n=37 set=2 label=0 https://flawchess.com/analysis?game_id=627424&ply=18: loss 0.355 -> 1.000, missed 0.000 -> 0.000
- n=96 set=5 label=0 https://flawchess.com/analysis?game_id=2993134&ply=23: loss 0.355 -> 0.871, missed 0.613 -> 0.484
- n=156 set=6 label=0 https://flawchess.com/analysis?game_id=2471877&ply=30: loss 0.000 -> 0.000, missed 0.645 -> 0.000
- n=159 set=6 label=1 https://flawchess.com/analysis?game_id=2241539&ply=19: loss 5.000 -> 5.000, missed 0.645 -> 0.000
- n=194 set=7 label=0 https://flawchess.com/analysis?game_id=3249052&ply=37: loss 0.000 -> 0.000, missed 0.871 -> 0.226
- n=214 set=7 label=0 https://flawchess.com/analysis?game_id=2285808&ply=12: loss 0.000 -> 0.000, missed 0.355 -> 1.000
- n=235 set=7 label=0 https://flawchess.com/analysis?game_id=3281026&ply=41: loss 0.000 -> 0.000, missed 2.065 -> 1.484
- n=114 set=5 label=1 https://flawchess.com/analysis?game_id=496082&ply=14: loss 0.968 -> 1.000, missed 0.516 -> 0.000
- n=166 set=6 label=1 https://flawchess.com/analysis?game_id=2655292&ply=50: loss 2.452 -> 2.774, missed 3.226 -> 3.000
- n=88 set=4 label=1 https://flawchess.com/analysis?game_id=1869584&ply=62: loss 4.484 -> 5.000, missed 5.000 -> 5.000
- n=228 set=7 label=1 https://flawchess.com/analysis?game_id=2952292&ply=85: loss 0.000 -> 0.000, missed 4.484 -> 5.000
- n=150 set=6 label=1 https://flawchess.com/analysis?game_id=1983784&ply=9: loss 1.806 -> 2.323, missed 0.000 -> 0.000
- n=275 set=8 label=0 https://flawchess.com/analysis?game_id=2351067&ply=44: loss 0.258 -> 0.258, missed 2.355 -> 1.839
- n=56 set=3 label=1 https://flawchess.com/analysis?game_id=2718033&ply=15: loss 2.129 -> 2.516, missed 0.097 -> 0.226
- n=43 set=2 label=0 https://flawchess.com/analysis?game_id=3191007&ply=23: loss 0.129 -> 0.129, missed 1.000 -> 0.484
- n=48 set=2 label=1 https://flawchess.com/analysis?game_id=867617&ply=65: loss 0.484 -> 1.000, missed 1.000 -> 1.000
- n=49 set=2 label=1 https://flawchess.com/analysis?game_id=1941795&ply=33: loss 0.484 -> 1.000, missed 0.000 -> 0.000
- n=91 set=5 label=1 https://flawchess.com/analysis?game_id=762702&ply=45: loss 0.000 -> 0.000, missed 1.323 -> 0.806
- n=97 set=5 label=0 https://flawchess.com/analysis?game_id=508685&ply=42: loss 0.000 -> 0.000, missed 0.516 -> 0.000
- n=100 set=5 label=1 https://flawchess.com/analysis?game_id=2109556&ply=43: loss 1.387 -> 1.387, missed 0.516 -> 0.000
- n=125 set=5 label=0 https://flawchess.com/analysis?game_id=755718&ply=26: loss 0.000 -> 0.000, missed 2.484 -> 3.000
- n=193 set=7 label=1 https://flawchess.com/analysis?game_id=699627&ply=34: loss 0.000 -> 0.000, missed 1.484 -> 0.968
- n=204 set=7 label=1 https://flawchess.com/analysis?game_id=1871792&ply=30: loss 5.000 -> 5.000, missed 0.516 -> 0.000
- n=234 set=7 label=1 https://flawchess.com/analysis?game_id=3264420&ply=25: loss 0.226 -> 0.226, missed 0.548 -> 0.032
- n=271 set=8 label=0 https://flawchess.com/analysis?game_id=2543217&ply=40: loss 0.000 -> 0.000, missed 1.290 -> 0.774
- n=282 set=8 label=1 https://flawchess.com/analysis?game_id=2727402&ply=30: loss 0.000 -> 0.000, missed 2.161 -> 1.645
- n=298 set=8 label=0 https://flawchess.com/analysis?game_id=2278776&ply=42: loss 0.000 -> 0.000, missed 1.194 -> 0.710
- n=200 set=7 label=0 https://flawchess.com/analysis?game_id=2848141&ply=30: loss 0.000 -> 0.000, missed 3.419 -> 3.000
- n=6 set=1 label=1 https://flawchess.com/analysis?game_id=549443&ply=25: loss 1.065 -> 1.452, missed 0.000 -> 0.000
- n=117 set=5 label=1 https://flawchess.com/analysis?game_id=1327193&ply=16: loss 0.000 -> 0.000, missed 2.387 -> 2.000
- n=206 set=7 label=1 https://flawchess.com/analysis?game_id=2548721&ply=41: loss 0.000 -> 0.000, missed 2.613 -> 3.000
- n=257 set=8 label=0 https://flawchess.com/analysis?game_id=2650568&ply=42: loss 0.000 -> 0.000, missed 1.677 -> 1.290
- n=241 set=8 label=0 https://flawchess.com/analysis?game_id=2022738&ply=88: loss 0.452 -> 0.710, missed 0.871 -> 1.000
- n=78 set=4 label=0.5 https://flawchess.com/analysis?game_id=1902788&ply=9: loss 1.000 -> 1.000, missed 0.387 -> 0.000
- n=123 set=5 label=0 https://flawchess.com/analysis?game_id=1606423&ply=62: loss 0.000 -> 0.000, missed 0.387 -> 0.000
- n=249 set=8 label=0 https://flawchess.com/analysis?game_id=2344527&ply=47: loss 1.129 -> 1.129, missed 0.774 -> 0.387
- n=154 set=6 label=1 https://flawchess.com/analysis?game_id=1239475&ply=43: loss 1.387 -> 1.452, missed 1.323 -> 1.000
- n=172 set=6 label=1 https://flawchess.com/analysis?game_id=1342152&ply=51: loss 0.548 -> 0.548, missed 0.677 -> 1.032
- n=190 set=6 label=1 https://flawchess.com/analysis?game_id=497688&ply=46: loss 3.000 -> 3.000, missed 0.355 -> 0.000
- n=236 set=7 label=1 https://flawchess.com/analysis?game_id=974403&ply=38: loss 2.323 -> 2.323, missed 3.129 -> 3.452
- n=89 set=4 label=0 https://flawchess.com/analysis?game_id=3194358&ply=60: loss 0.000 -> 0.000, missed 2.097 -> 1.806
- n=269 set=8 label=1 https://flawchess.com/analysis?game_id=2048229&ply=20: loss 0.000 -> 0.000, missed 1.710 -> 2.000
- n=191 set=7 label=0 https://flawchess.com/analysis?game_id=499686&ply=62: loss 0.000 -> 0.000, missed 2.258 -> 2.000
- n=202 set=7 label=0 https://flawchess.com/analysis?game_id=2850554&ply=31: loss 0.000 -> 0.000, missed 2.290 -> 2.032
- n=19 set=1 label=0 https://flawchess.com/analysis?game_id=2780723&ply=78: loss 0.000 -> 0.000, missed 0.290 -> 0.032
- n=94 set=5 label=0 https://flawchess.com/analysis?game_id=1668542&ply=51: loss 0.032 -> 0.032, missed 1.258 -> 1.000
- n=130 set=5 label=0.5 https://flawchess.com/analysis?game_id=3066120&ply=50: loss 1.129 -> 1.129, missed 0.258 -> 0.000
- n=133 set=5 label=0 https://flawchess.com/analysis?game_id=2664869&ply=26: loss 0.871 -> 1.000, missed 0.871 -> 1.000
- n=139 set=5 label=0 https://flawchess.com/analysis?game_id=2657540&ply=58: loss 0.903 -> 0.903, missed 0.742 -> 0.484
- n=197 set=7 label=0 https://flawchess.com/analysis?game_id=1077995&ply=48: loss 0.000 -> 0.000, missed 0.968 -> 1.226
- n=210 set=7 label=1 https://flawchess.com/analysis?game_id=2047830&ply=15: loss 5.000 -> 5.000, missed 0.258 -> 0.000
- n=266 set=8 label=0 https://flawchess.com/analysis?game_id=485318&ply=72: loss 0.000 -> 0.000, missed 0.258 -> 0.000
- n=8 set=1 label=1 https://flawchess.com/analysis?game_id=3069554&ply=8: loss 0.000 -> 0.000, missed 2.935 -> 3.194
- n=63 set=3 label=1 https://flawchess.com/analysis?game_id=3237211&ply=48: loss 5.000 -> 5.000, missed 2.194 -> 1.935
- n=262 set=8 label=0 https://flawchess.com/analysis?game_id=1636663&ply=57: loss 0.000 -> 0.000, missed 3.452 -> 3.710
- n=137 set=5 label=0 https://flawchess.com/analysis?game_id=2633412&ply=18: loss 0.000 -> 0.000, missed 1.484 -> 1.290
- n=231 set=7 label=1 https://flawchess.com/analysis?game_id=1066966&ply=44: loss 0.774 -> 0.774, missed 0.968 -> 0.774
- n=16 set=1 label=0 https://flawchess.com/analysis?game_id=1585786&ply=30: loss 0.000 -> 0.000, missed 0.194 -> 0.000
- n=61 set=3 label=0 https://flawchess.com/analysis?game_id=2423001&ply=37: loss 0.000 -> 0.000, missed 0.194 -> 0.000
- n=105 set=5 label=0 https://flawchess.com/analysis?game_id=2679152&ply=36: loss 0.484 -> 0.484, missed 0.194 -> 0.000
- n=136 set=5 label=0 https://flawchess.com/analysis?game_id=504615&ply=25: loss 0.065 -> 0.194, missed 0.032 -> 0.097
- n=3 set=1 label=0 https://flawchess.com/analysis?game_id=1990843&ply=13: loss 0.355 -> 0.548, missed 0.000 -> 0.000
- n=58 set=3 label=1 https://flawchess.com/analysis?game_id=606360&ply=48: loss 0.774 -> 0.774, missed 0.903 -> 1.097
- n=229 set=7 label=1 https://flawchess.com/analysis?game_id=3239949&ply=15: loss 3.000 -> 3.000, missed 0.677 -> 0.484
- n=203 set=7 label=0 https://flawchess.com/analysis?game_id=1941695&ply=39: loss 0.000 -> 0.000, missed 1.710 -> 1.548
- n=40 set=2 label=0 https://flawchess.com/analysis?game_id=2900182&ply=58: loss 0.194 -> 0.226, missed 0.161 -> 0.032
- n=224 set=7 label=0 https://flawchess.com/analysis?game_id=2474796&ply=25: loss 0.097 -> 0.097, missed 1.000 -> 1.129
- n=293 set=8 label=0 https://flawchess.com/analysis?game_id=2757167&ply=66: loss 0.000 -> 0.000, missed 1.000 -> 1.129
- n=299 set=8 label=0 https://flawchess.com/analysis?game_id=2727637&ply=51: loss 1.581 -> 1.710, missed 0.000 -> 0.000
- n=1 set=1 label=0 https://flawchess.com/analysis?game_id=1940139&ply=21: loss 0.000 -> 0.000, missed 0.097 -> 0.226
- n=107 set=5 label=0 https://flawchess.com/analysis?game_id=2404626&ply=30: loss 0.000 -> 0.000, missed 0.129 -> 0.000
- n=122 set=5 label=0 https://flawchess.com/analysis?game_id=2862249&ply=47: loss 0.000 -> 0.000, missed 0.613 -> 0.484
- n=147 set=6 label=1 https://flawchess.com/analysis?game_id=1216301&ply=41: loss 2.000 -> 2.000, missed 0.129 -> 0.000
- n=160 set=6 label=1 https://flawchess.com/analysis?game_id=1547772&ply=83: loss 1.452 -> 1.452, missed 0.129 -> 0.000
- n=173 set=6 label=1 https://flawchess.com/analysis?game_id=2960017&ply=51: loss 2.419 -> 2.419, missed 0.129 -> 0.000
- n=176 set=6 label=0 https://flawchess.com/analysis?game_id=483089&ply=67: loss 0.000 -> 0.000, missed 0.129 -> 0.000
- n=153 set=6 label=0 https://flawchess.com/analysis?game_id=1164073&ply=28: loss 1.323 -> 1.355, missed 1.097 -> 1.000
- n=192 set=7 label=0 https://flawchess.com/analysis?game_id=1224022&ply=47: loss 0.000 -> 0.000, missed 4.194 -> 4.323
- n=207 set=7 label=0 https://flawchess.com/analysis?game_id=1581079&ply=66: loss 0.032 -> 0.032, missed 4.258 -> 4.387
- n=92 set=5 label=1 https://flawchess.com/analysis?game_id=2240105&ply=50: loss 2.903 -> 2.903, missed 1.000 -> 0.903
- n=188 set=6 label=1 https://flawchess.com/analysis?game_id=563171&ply=14: loss 3.000 -> 3.000, missed 0.290 -> 0.194
- n=67 set=3 label=0 https://flawchess.com/analysis?game_id=2350172&ply=33: loss 0.032 -> 0.097, missed 0.065 -> 0.032
- n=219 set=7 label=1 https://flawchess.com/analysis?game_id=1161949&ply=24: loss 0.000 -> 0.065, missed 2.968 -> 3.000
- n=32 set=2 label=0 https://flawchess.com/analysis?game_id=2847507&ply=19: loss 0.677 -> 0.677, missed 2.097 -> 2.000
- n=233 set=7 label=1 https://flawchess.com/analysis?game_id=1554612&ply=24: loss 0.000 -> 0.000, missed 4.387 -> 4.290
- n=79 set=4 label=1 https://flawchess.com/analysis?game_id=2116428&ply=58: loss 0.903 -> 0.968, missed 0.000 -> 0.000
- n=93 set=5 label=1 https://flawchess.com/analysis?game_id=1907494&ply=23: loss 0.387 -> 0.387, missed 0.968 -> 0.903
- n=5 set=1 label=1 https://flawchess.com/analysis?game_id=1689678&ply=16: loss 0.161 -> 0.161, missed 0.065 -> 0.000
- n=7 set=1 label=0 https://flawchess.com/analysis?game_id=1987162&ply=24: loss 0.194 -> 0.226, missed 0.194 -> 0.226
- n=20 set=1 label=1 https://flawchess.com/analysis?game_id=3064720&ply=28: loss 0.000 -> 0.000, missed 0.097 -> 0.161
- n=268 set=8 label=0 https://flawchess.com/analysis?game_id=2543179&ply=30: loss 0.000 -> 0.000, missed 4.935 -> 5.000
- n=90 set=4 label=0.5 https://flawchess.com/analysis?game_id=1078853&ply=77: loss 1.000 -> 1.000, missed 0.032 -> 0.000
- n=120 set=5 label=1 https://flawchess.com/analysis?game_id=1675212&ply=32: loss 2.387 -> 2.419, missed 0.000 -> 0.000
- n=175 set=6 label=1 https://flawchess.com/analysis?game_id=1218742&ply=59: loss 2.000 -> 2.000, missed 1.000 -> 0.968
- n=212 set=7 label=0 https://flawchess.com/analysis?game_id=2721044&ply=15: loss 0.000 -> 0.000, missed 0.968 -> 1.000
- n=259 set=8 label=0 https://flawchess.com/analysis?game_id=1560985&ply=24: loss 0.000 -> 0.000, missed 0.968 -> 1.000

## Reply probability coverage (information)

- known: 280 of 291
- quartiles: 0.179 / 0.529 / 0.741

## Examples (shipped -> quiet)

### n=189 set=6 label=1

- link: https://flawchess.com/analysis?game_id=2632426&ply=25
- played line: d5e7 c6e7 d1a1 e7g6 f3d4 g4d7 a1c3 a8c8 f1e1 f8e8 f2f4 h7h6
- best line: f6d5 e4d5 g4f3 g2f3 c6e5 a1c1 e5f3 d1f3 f8e8 f3d3 d4f6 f1e1
- played loss, shipped -> quiet: d1 1 -> 4 [longer_exchange_settled]; d3 4 -> 4; d5 4 -> 4; d7 4 -> 4; d9 4 -> 4
- best material, shipped -> quiet: d1 3 -> 0 [longer_exchange_settled]; d3 0 -> 0; d5 3 -> 0 [longer_exchange_settled]; d7 0 -> 0; d9 0 -> 0
- loss 2.452 -> 4.000; missed 1.935 -> 0.000

### n=106 set=5 label=0

- link: https://flawchess.com/analysis?game_id=3230634&ply=39
- played line: d1d8 e7d8 e1e8 f6e8 h3g4 h5h4 g3f4 e8g7 f3e4 g7e6 f4c1 b6d5
- best line: h5h4 g3e5 d8d1 e1d1 b6d7 e5h2 e7d8 a5c4 d8c7 c4d6 c7d6 h2d6
- played loss, shipped -> quiet: d1 0 -> 1 [longer_exchange_settled]; d3 0 -> 1 [longer_exchange_settled]; d5 1 -> 1; d7 1 -> 1; d9 1 -> 1
- best material, shipped -> quiet: d1 5 -> 0 [longer_exchange_settled]; d3 0 -> 0; d5 0 -> 0; d7 0 -> 0; d9 3 -> 0 [exchange_settled_at_end]
- loss 0.226 -> 1.000; missed 2.677 -> 0.000

### n=163 set=6 label=1

- link: https://flawchess.com/analysis?game_id=1074062&ply=19
- played line: e4a8 e7e2 c3e2 f8e7 a8f3 e7f6 e2c3 g8e7 c1d2 c8e6 e1c1 f6e5
- best line: g8f6 c1g5 e7e6 e1c1 f6e4 c3e4 e8f7 e2f3 e6f5 g5f4 h7h6 h1e1
- played loss, shipped -> quiet: d1 -4 -> 5 [longer_exchange_settled]; d3 5 -> 5; d5 5 -> 5; d7 5 -> 5; d9 5 -> 5
- best material, shipped -> quiet: d1 0 -> 0; d3 3 -> 0 [longer_exchange_settled]; d5 0 -> 0; d7 0 -> 0; d9 0 -> 0
- loss 2.419 -> 5.000; missed 0.774 -> 0.000

### n=111 set=5 label=0

- link: https://flawchess.com/analysis?game_id=1581100&ply=43
- played line: d4g7 b4g4 g7b2 f8e8 h1h6 f7f6 e3f3 g4f3 g2f3 g8g7 h6h4 a8c8
- best line: a8e8 e3c3 b4c3 d4c3 e8c8 c3d4 c8c2 h1a1 f8e8 f2e1 g7g5 f3g1
- played loss, shipped -> quiet: d1 -2 -> -2; d3 -2 -> -2; d5 -1 -> -1; d7 -7 -> 2 [longer_exchange_settled]; d9 2 -> 2
- best material, shipped -> quiet: d1 9 -> 0 [longer_exchange_settled]; d3 0 -> 0; d5 0 -> 0; d7 0 -> 0; d9 0 -> 0
- loss 0.065 -> 0.194; missed 2.581 -> 0.000

### n=102 set=5 label=0

- link: https://flawchess.com/analysis?game_id=2312975&ply=27
- played line: b1d2 f6e8 f4g3 d8d6 e4e5 d6e6 d2f3 f8g8 h4h5 g7f8 g3h2 e7d8
- best line: f6h5 f4e3 f8f1 g1f1 b8c6 b1d2 d8d7 b2b3 c6d4 c3d4 g7d4 e3h6
- played loss, shipped -> quiet: d1 0 -> 0; d3 0 -> 0; d5 0 -> 0; d7 0 -> 0; d9 0 -> 0
- best material, shipped -> quiet: d1 5 -> 0 [longer_exchange_settled]; d3 0 -> 0; d5 0 -> 0; d7 1 -> -2 [exchange_settled_at_end]; d9 -1 -> -2 [exchange_settled_at_end]
- loss 0.000 -> 0.000; missed 2.645 -> 0.000

### n=extra set=extra label=-

- link: https://flawchess.com/analysis?game_id=2883555&ply=47
- played line: f4e6 f5f4 e6c7 d7c7 f1g1 g8g4 a1f1 c7b8 f2d4 h8e8 f1e1 e8f8
- best line: d6f4 f2f4 c7f4 f1f4 c8d7 h1h2 d7d6 a1e1 g8g5 f4f3 g5g6 d3d4
- played loss, shipped -> quiet: d1 1 -> 1; d3 7 -> 7; d5 7 -> 7; d7 7 -> 7; d9 7 -> 7
- best material, shipped -> quiet: d1 9 -> 0 [longer_exchange_settled]; d3 0 -> 0; d5 0 -> 0; d7 0 -> 0; d9 0 -> 0
- loss 2.935 -> 2.935; missed 2.581 -> 0.000

### n=156 set=6 label=0

- link: https://flawchess.com/analysis?game_id=2471877&ply=30
- played line: d8d7 a1e1 h4e1 h1e1 e8d8 a4b4 b7b6 b4c4 h8e8 f4c7 d7c7 e1e8
- best line: a1e1 h4e1 h1e1 e8f8 f4c7 d8d5 c4d5 f6d5 c7d6 f8g8 c2c4 d5f6
- played loss, shipped -> quiet: d1 0 -> 0; d3 -3 -> -3; d5 -3 -> -3; d7 -3 -> -3; d9 -4 -> -1 [exchange_settled_at_end]
- best material, shipped -> quiet: d1 -2 -> -2; d3 -1 -> -1; d5 8 -> -1 [longer_exchange_settled]; d7 -1 -> -1; d9 -1 -> -1
- loss 0.000 -> 0.000; missed 0.645 -> 0.000

### n=154 set=6 label=1

- link: https://flawchess.com/analysis?game_id=1239475&ply=43
- played line: e3c5 d7c6 d5c6 d8d6 c6b7 c8d8 b5d6 e7d6 c5f5 b8b7 f5f4 b7c7
- best line: d7b5 c4b5 f4d5 b5b6 a7b6 a5b6 c7c6 e3a3 c6b6 c1c5 c8b8 h1g1
- played loss, shipped -> quiet: d1 1 -> 1; d3 1 -> 1; d5 2 -> 2; d7 4 -> 4; d9 3 -> 6 [longer_exchange_settled]
- best material, shipped -> quiet: d1 1 -> 1; d3 2 -> 1 [longer_exchange_settled]; d5 1 -> 1; d7 2 -> 1 [longer_exchange_settled]; d9 1 -> 1
- loss 1.387 -> 1.452; missed 1.323 -> 1.000

### n=153 set=6 label=0

- link: https://flawchess.com/analysis?game_id=1164073&ply=28
- played line: c8d7 a4b3 g8g6 g1h1 d7e6 f2f4 d8d6 b3b7 a8d8 f4e5 f6e5 c2c4
- best line: g4h5 f5g7 h5h6 c8e6 a1d1 c7c6 d2e4 g7f5 h6h5 e6f7 h5f5 g8g6
- played loss, shipped -> quiet: d1 0 -> 0; d3 3 -> 3; d5 3 -> 3; d7 2 -> 2; d9 1 -> 2 [longer_exchange_settled]
- best material, shipped -> quiet: d1 1 -> 1; d3 1 -> 1; d5 1 -> 1; d7 1 -> 1; d9 4 -> 1 [exchange_settled_at_end]
- loss 1.323 -> 1.355; missed 1.097 -> 1.000

### n=170 set=6 label=0

- link: https://flawchess.com/analysis?game_id=2869941&ply=67
- played line: g1g6 b2c2 c3c2 c5b4 f4f5 g8d8 g7g8q d8g8 g6g8 h6h5 c2d3 h5h4
- best line: b7g7 g1h1 g7g6 h1h5 c5b6 h5b5 b6c6 b5a5 g6g1 a5a6 c6c7 a6a7
- played loss, shipped -> quiet: d1 0 -> 0; d3 0 -> 0; d5 0 -> 0; d7 -9 -> -4 [longer_exchange_settled]; d9 -4 -> -4
- best material, shipped -> quiet: d1 1 -> 1; d3 1 -> 1; d5 1 -> 1; d7 1 -> 1; d9 1 -> 1
- loss 0.000 -> 0.000; missed 0.903 -> 0.903
