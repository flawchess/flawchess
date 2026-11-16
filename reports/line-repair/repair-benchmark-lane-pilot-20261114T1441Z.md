# Line repair report: benchmark / lane / pilot

- target: benchmark
- mode: pilot
- engines: 8
- started: 2026-11-14T14:16:57+00:00
- ended: 2026-11-14T14:41:44+00:00
- work list size: 146219
- cursor before: 0, after: 1463

## Counters

- selected_a: 5058
- selected_b: 26
- sentinel_beyond_dedup_ply: 121
- legit_short: 6
- unreplayable: 0
- searched: 5078
- written: 5078
- would_write: 0
- unchanged: 0
- still_short: 0
- mate_short: 0
- pin_mismatch: 0
- failed: 0
- best_move_written_null: 38
- best_move_written_illegal: 0
- concurrently_changed: 0
- game_deleted: 0
- row_count_mismatch: 0
- failed_batches: 0
- games_done: 1463

## Throughput

- rows searched per second: 3.41
- games per second: 0.98
- projected days for the remaining work list: 1.70

## DB health

- connections baseline 13, peak 13
- commit latency median baseline 0.0045s, rolling 0.0062s

## Gates

| gate | value | threshold | verdict |
|---|---|---|---|
| still_short_share | 0 | 0.03 | PASS |
| projected_days | 1.70339 | 10 | PASS |
| row_count_mismatch | 0 | 0 | PASS |
| failed_batches | 0 | 0 | PASS |
| connections | 13 | 23 | PASS |
| commit_latency | 1.39074 | 3 | PASS |

## Verdict: PASS
