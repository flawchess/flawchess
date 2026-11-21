# Feed report: prod / all / full

- started: 2026-11-19T14:30:58+00:00
- ended: 2026-11-21T02:16:27+00:00
- stopped because: failed step
- window size 800 games, low water 400 games
- work list size: 1056391, feed cursor: 215664
- windows fed (this run): 212, (total): 305
- lines NULLed, missed: 425979, allowed: 345023
- games fed: 181424, completed: 180511, pending: 913
- eval or flaw-set changed (fingerprint mismatch): 0

## Drain rate measured with the fleet as it is

- observed for 51.93 h since the first fed game
- games per hour: 3476.00
- lines per hour: 14770.36
- projected weeks for the remaining work list: 0

## User-visible NULL window per completed game (this run)

Hours from the feed to the poll that saw blobs_completed_at set, so each value is rounded up to the poll interval.

- completed games measured: 142461
- p50: 0.10 h, p95: 0.54 h, max: 7.08 h

## Gates

| gate | value | threshold | verdict |
|---|---|---|---|
| failed_batches | 1 | 0 | STOP |

## Verdict: STOP
