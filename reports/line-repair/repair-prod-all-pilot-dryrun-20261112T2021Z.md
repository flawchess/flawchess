# Line repair report: prod / all / pilot-dryrun

- target: prod
- mode: pilot-dryrun
- engines: 8
- started: 2026-11-12T20:01:04+00:00
- ended: 2026-11-12T20:21:01+00:00
- work list size: 1056391
- cursor before: 0, after: 2000

## Counters

- selected_a: 5396
- selected_b: 133
- sentinel_beyond_dedup_ply: 1143
- legit_short: 19
- unreplayable: 0
- searched: 5510
- written: 0
- would_write: 5510
- unchanged: 0
- still_short: 0
- mate_short: 0
- pin_mismatch: 0
- failed: 0
- best_move_written_null: 0
- best_move_written_illegal: 0
- concurrently_changed: 0
- game_deleted: 0
- row_count_mismatch: 0
- failed_batches: 0
- games_done: 2000

## Throughput

- rows searched per second: 4.60
- games per second: 1.67
- projected days for the remaining work list: 7.31

## DB health

- connections and commit latency: not monitored in this run

## Gates

| gate | value | threshold | verdict |
|---|---|---|---|
| still_short_share | 0 | 0.03 | PASS |
| projected_days | 7.30583 | 10 | PASS |
| row_count_mismatch | 0 | 0 | PASS |
| failed_batches | 0 | 0 | PASS |

## Verdict: PASS
