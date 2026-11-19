# Line repair report: prod / all / full-dryrun

- target: prod
- mode: full-dryrun
- engines: 4
- started: 2026-11-18T22:13:18+00:00
- ended: 2026-11-18T22:15:20+00:00
- work list size: 5012
- cursor before: 0, after: 5012

## Counters

- selected_a: 5946
- selected_b: 1
- sentinel_beyond_dedup_ply: 1291
- legit_short: 5880
- unreplayable: 0
- searched: 67
- written: 0
- would_write: 5
- unchanged: 37
- still_short: 0
- mate_short: 38
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

- rows searched per second: 0.55
- games per second: 41.29
- projected days for the remaining work list: 0.00

## DB health

- connections and commit latency: not monitored in this run

## Gates

| gate | value | threshold | verdict |
|---|---|---|---|
| still_short_share | 0 | 0.03 | PASS |
| projected_days | 0 | 10 | PASS |
| row_count_mismatch | 0 | 0 | PASS |
| failed_batches | 0 | 0 | PASS |

## Verdict: PASS
