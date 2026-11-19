# Line repair report: prod / all / full

- target: prod
- mode: full
- engines: 4
- started: 2026-11-18T22:15:45+00:00
- ended: 2026-11-18T22:18:59+00:00
- work list size: 5012
- cursor before: 0, after: 5012

## Counters

- selected_a: 5946
- selected_b: 1
- sentinel_beyond_dedup_ply: 1291
- legit_short: 5880
- unreplayable: 0
- searched: 67
- written: 4
- would_write: 0
- unchanged: 38
- still_short: 0
- mate_short: 40
- pin_mismatch: 0
- failed: 25
- best_move_written_null: 0
- best_move_written_illegal: 0
- concurrently_changed: 0
- game_deleted: 0
- row_count_mismatch: 0
- failed_batches: 0
- games_done: 5012

## Throughput

- rows searched per second: 0.35
- games per second: 25.88
- projected days for the remaining work list: 0.00

## DB health

- connections baseline 14, peak 22
- commit latency: 3 commits, too few to compare

## Gates

| gate | value | threshold | verdict |
|---|---|---|---|
| still_short_share | 0 | 0.03 | PASS |
| projected_days | 0 | 10 | PASS |
| row_count_mismatch | 0 | 0 | PASS |
| failed_batches | 0 | 0 | PASS |
| connections | 22 | 45 | PASS |

## Verdict: PASS
