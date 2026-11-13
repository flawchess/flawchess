# Line repair report: prod / all / full

- target: prod
- mode: full
- engines: 8
- started: 2026-11-12T22:08:05+00:00
- ended: 2026-11-13T09:55:53+00:00
- work list size: 1056391
- cursor before: 10564, after: 86564

## Counters

- selected_a: 219321
- selected_b: 6897
- sentinel_beyond_dedup_ply: 60010
- legit_short: 399
- unreplayable: 0
- searched: 225819
- written: 225818
- would_write: 0
- unchanged: 1
- still_short: 0
- mate_short: 3
- pin_mismatch: 0
- failed: 0
- best_move_written_null: 1503
- best_move_written_illegal: 0
- concurrently_changed: 0
- game_deleted: 0
- row_count_mismatch: 0
- failed_batches: 0
- games_done: 76000

## Throughput

- rows searched per second: 5.32
- games per second: 1.79
- projected days for the remaining work list: 6.27

## DB health

- connections baseline 19, peak 23
- commit latency median baseline 0.0156s, rolling 0.0153s

## Gates

| gate | value | threshold | verdict |
|---|---|---|---|
| still_short_share | 0 | 0.03 | PASS |
| projected_days | 6.27243 | 10 | PASS |
| row_count_mismatch | 0 | 0 | PASS |
| failed_batches | 0 | 0 | PASS |
| connections | 23 | 29 | PASS |
| commit_latency | 0.979721 | 3 | PASS |

## Verdict: PASS
