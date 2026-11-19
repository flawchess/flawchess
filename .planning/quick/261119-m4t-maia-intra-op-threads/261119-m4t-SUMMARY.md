---
quick_id: 261119-m4t
status: complete
date: 2026-11-19
---

# Summary: backend Maia session runs one intra-op thread

The backend lifespan now starts Maia with `settings.MAIA_INTRA_OP_THREADS` (default 1;
0 restores the ORT default). No compose or `.env` change is needed: the code default
applies in prod at the next deploy.

## Local benchmark (16 cores, idle machine, 3 interleaved rounds, 120 positions per arm)

| intra-op threads | callers | positions/s | CPU per position |
|---|---|---|---|
| default (16) | 1 | 12.6 to 13.2 | 607 to 633 ms |
| default (16) | 3 | 23.5 to 30.1 | 332 to 424 ms |
| default (16) | 6 | 44.1 to 46.9 | 275 to 284 ms |
| 1 | 1 | 12.4 to 12.9 | 77 to 81 ms |
| 1 | 3 | 35.2 to 36.0 | 83 to 85 ms |
| 1 | 6 | 57.6 to 60.5 | 98 to 102 ms |
| 2 | 1 | 13.8 to 13.9 | 144 to 145 ms |
| 2 | 3 | 37.8 to 38.6 | 104 to 106 ms |
| 2 | 6 | 63.8 to 64.8 | 108 to 109 ms |

One thread: same wall time per call, about an eighth of the CPU, about 50% more
throughput at three callers even with idle cores to spare. Two threads buy about 5%
more throughput for 10 to 85% more CPU; 1 was chosen because prod is CPU-starved.

## Verification

- `test_backend_lifespan_maia_thread_count` fails under both mutations (default 0;
  helper returning None).
- Full pre-merge gate green: 7,068 backend tests passed, frontend lint/build/test/knip.

## Not verified

- The effect on prod. The prod gain is an expectation from the local benchmark, to be
  measured after deploy (backend CPU, `flaw-blob-submit` median and p95, games/h).
- Interactive Maia callers (analysis board, blunder check) share this session; single
  calls measured the same wall time, but that was not checked on prod hardware.
