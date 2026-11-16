# Feed report: benchmark / lane / pilot

- started: 2026-11-16T05:49:36+00:00
- ended: 2026-11-16T05:57:24+00:00
- stopped because: stop requested
- window size 500 games, low water 150 games
- work list size: 146219, feed cursor: 500
- windows fed (this run): 1, (total): 1
- lines NULLed, missed: 1119, allowed: 870
- games fed: 442, completed: 0, pending: 442
- eval or flaw-set changed (fingerprint mismatch): 0

## Drain rate measured with the fleet as it is

- observed for 0.13 h since the first fed game
- games per hour: 0.00
- lines per hour: 0.00
- projected weeks for the remaining work list: 0

## User-visible NULL window per completed game (this run)

Hours from the feed to the poll that saw blobs_completed_at set, so each value is rounded up to the poll interval.

- completed games measured: 0
- p50: 0.00 h, p95: 0.00 h, max: 0.00 h

## Gates

| gate | value | threshold | verdict |
|---|---|---|---|
| projected_weeks | 0 | 8 | PASS |
| eval_change_share | 0 | 0.005 | PASS |

## Verdict: PASS
