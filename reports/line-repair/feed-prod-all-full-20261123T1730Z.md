# Feed report: prod / all / full

- started: 2026-11-21T19:06:53+00:00
- ended: 2026-11-23T17:30:07+00:00
- stopped because: stop requested
- window size 800 games, low water 400 games
- work list size: 1056391, feed cursor: 415664
- windows fed (this run): 208, (total): 555
- lines NULLed, missed: 847178, allowed: 685571
- games fed: 351981, completed: 351143, pending: 838
- eval or flaw-set changed (fingerprint mismatch): 0

## Drain rate measured with the fleet as it is

- observed for 115.16 h since the first fed game
- games per hour: 3049.22
- lines per hour: 13278.26
- projected weeks for the remaining work list: 1.05886

## User-visible NULL window per completed game (this run)

Hours from the feed to the poll that saw blobs_completed_at set, so each value is rounded up to the poll interval.

- completed games measured: 141837
- p50: 0.10 h, p95: 0.68 h, max: 17.40 h

## Gates

| gate | value | threshold | verdict |
|---|---|---|---|
| projected_weeks | 1.05886 | 8 | PASS |
| eval_change_share | 0 | 0.005 | PASS |

## Verdict: PASS
