# Line repair report: prod / all / full

- target: prod
- mode: full
- engines: 8
- started: 2026-11-13T11:25:48+00:00
- ended: 2026-11-13T22:38:03+00:00
- work list size: 1056391
- cursor before: 86564, after: 145164

## Counters

- selected_a: 169977
- selected_b: 6039
- sentinel_beyond_dedup_ply: 50584
- legit_short: 287
- unreplayable: 0
- searched: 175729
- written: 175729
- would_write: 0
- unchanged: 0
- still_short: 0
- mate_short: 4
- pin_mismatch: 0
- failed: 0
- best_move_written_null: 1332
- best_move_written_illegal: 0
- concurrently_changed: 0
- game_deleted: 0
- row_count_mismatch: 0
- failed_batches: 0
- games_done: 58600

## Throughput

- rows searched per second: 4.36
- games per second: 1.45
- projected days for the remaining work list: 7.26

## DB health

- connections baseline 20, peak 29
- commit latency median baseline 0.0150s, rolling 0.0175s

## Gates

| gate | value | threshold | verdict |
|---|---|---|---|
| still_short_share | 0 | 0.03 | PASS |
| projected_days | 7.25935 | 10 | PASS |
| row_count_mismatch | 0 | 0 | PASS |
| failed_batches | 0 | 0 | PASS |
| connections | 29 | 30 | PASS |
| commit_latency | 1.16746 | 3 | PASS |

## Verdict: PASS
