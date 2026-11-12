# Line repair report: prod / all / pilot

- target: prod
- mode: pilot
- engines: 8
- started: 2026-11-12T20:28:00+00:00
- ended: 2026-11-12T22:07:59+00:00
- work list size: 1056391
- cursor before: 0, after: 10564

## Counters

- selected_a: 29867
- selected_b: 838
- sentinel_beyond_dedup_ply: 6992
- legit_short: 53
- unreplayable: 0
- searched: 30652
- written: 30652
- would_write: 0
- unchanged: 0
- still_short: 0
- mate_short: 0
- pin_mismatch: 0
- failed: 0
- best_move_written_null: 192
- best_move_written_illegal: 0
- concurrently_changed: 0
- game_deleted: 0
- row_count_mismatch: 0
- failed_batches: 0
- games_done: 10564

## Throughput

- rows searched per second: 5.11
- games per second: 1.76
- projected days for the remaining work list: 6.87

## DB health

- connections baseline 19, peak 21
- commit latency median baseline 0.0157s, rolling 0.0159s

## Gates

| gate | value | threshold | verdict |
|---|---|---|---|
| still_short_share | 0 | 0.03 | PASS |
| projected_days | 6.87451 | 10 | PASS |
| row_count_mismatch | 0 | 0 | PASS |
| failed_batches | 0 | 0 | PASS |
| connections | 21 | 29 | PASS |
| commit_latency | 1.00986 | 3 | PASS |

## Verdict: PASS
