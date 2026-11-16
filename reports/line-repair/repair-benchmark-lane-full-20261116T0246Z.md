# Line repair report: benchmark / lane / full

- target: benchmark
- mode: full
- engines: 8
- started: 2026-11-14T14:42:01+00:00
- ended: 2026-11-16T02:46:51+00:00
- work list size: 146219
- cursor before: 1463, after: 146219

## Counters

- selected_a: 490670
- selected_b: 2035
- sentinel_beyond_dedup_ply: 9920
- legit_short: 480
- unreplayable: 0
- searched: 492225
- written: 492181
- would_write: 0
- unchanged: 4
- still_short: 0
- mate_short: 19
- pin_mismatch: 0
- failed: 40
- best_move_written_null: 2875
- best_move_written_illegal: 0
- concurrently_changed: 0
- game_deleted: 0
- row_count_mismatch: 0
- failed_batches: 0
- games_done: 144756

## Throughput

- rows searched per second: 3.79
- games per second: 1.11
- projected days for the remaining work list: 0.00

## DB health

- connections baseline 13, peak 15
- commit latency median baseline 0.0053s, rolling 0.0034s

## Gates

| gate | value | threshold | verdict |
|---|---|---|---|
| still_short_share | 0 | 0.03 | PASS |
| projected_days | 0 | 10 | PASS |
| row_count_mismatch | 0 | 0 | PASS |
| failed_batches | 0 | 0 | PASS |
| connections | 15 | 23 | PASS |
| commit_latency | 0.63853 | 3 | PASS |

## Verdict: PASS
