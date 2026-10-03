---
phase: 227-browser-engine-continuous-dispatch-against-a-relaxed-determi
plan: 11
subsystem: engine
tags: [gate, move-quality, throughput, calibration, continuous-dispatch]

requires:
  - phase: 227-10
    provides: "continuous dispatch behind SearchBudget.dispatchMode; post-extraction clear-hash parity TRIPWIRE PASS"
provides:
  - "Judged MQ (R=5) and report-only MQ (Clear-Hash, analysis-400) data for both arms under gate/"
  - "Interleaved throughput session (3 rounds x 4 configs x 2 arms) under gate/throughput/"
  - "A0/A1 calibration ledgers (10 cells) and the A1-vs-A0 parity verdict under gate/calibration/"
affects: [227-12, 227-13]

plan_head_before: f3d9ea2fe6d2da928243b61eed049ac4f29f49f5
plan_head_after: 591a528be

actuals:
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Orchestrator-run sequential driver under setsid nohup with a logged load gate before each step"
    - "Same-cell A0/A1 calibration pairs launched by a detached slot scheduler (max 6 supervisors)"

requirements-completed: []

coverage:
  - id: D1
    description: "Judged and report-only MQ data for both arms, measured after the accept rule, valid per the twin"
    verification:
      - kind: other
        ref: "uv run python scripts/engine_dispatch_227_verdict.py mq --data-dir reports/data/continuous-dispatch-227 (exit 0)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Interleaved throughput: 24 judged steps, all rc 0, twin throughput subcommand exits 0"
    verification:
      - kind: other
        ref: "uv run python scripts/engine_dispatch_227_verdict.py throughput --data-dir reports/data/continuous-dispatch-227 (exit 0)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Ten calibration cells complete, every ledger row's dispatch_mode matches its arm, parity verdict committed"
    verification:
      - kind: other
        ref: "Task 3 automated verify (2000 ledger rows, MODES_OK, 10 cells files, verdict-a1-vs-a0.json tracked)"
        status: pass
    human_judgment: false
---

# 227-11 SUMMARY: the pre-registered gate run

All three gate legs ran inline from the orchestrator (never an executor), measured at the implementation commit
**I = `f3d9ea2fe6d2da928243b61eed049ac4f29f49f5`**, after the accept rule **R = `7fb704a65`** (`git merge-base
--is-ancestor R HEAD` holds; the first commit under `gate/` is `7090c3ce8`, a descendant of R).
`FLAWCHESS_DISPATCH_MODE` stayed `'round'` throughout; arms were selected only by `--dispatch-mode` /
`PRESET_SUPERVISOR_DISPATCH_MODE`.

## Commits

| Commit | What |
|---|---|
| `7090c3ce8` | `chore(227-11): MQ gate data, round and continuous, R=5 (+ report-only cells)` |
| `5448f94bc` | `chore(227-11): interleaved throughput session, 3 rounds x 4 configs x 2 arms (D-17)` |
| `591a528be` | `chore(227-11): A0/A1 calibration sweeps and parity verdict (D-15)` |

## Preflight

- Content assertion 2 (owner override 2026-10-02 pathspec):
  `git diff --name-only R I -- . ':!.planning' ':!reports/continuous-dispatch-227/*.md' ':!reports/continuous-dispatch-227/reviews/*.md'`
  listed exactly Plan 227-10's six frontend files plus the four `scripts/` files of the comment-only commit `dcba1ba14`
  (`calibration-harness.mjs`, `engine-dispatch-stop-rule.mjs`, `lib/node-engine-providers.mjs`, `lib/stockfish-pool.mjs`).
- `pgrep` for gate processes and `remote_eval_worker`: nothing running. Load average 0.64 at start.
- 227-10-SUMMARY.md records the post-extraction `--hash clear` parity TRIPWIRE PASS.
- Working tree clean except the owner's untracked `frontend/public/sound/alternatives/` (left alone per STATE).

## Task 1: move quality (2026-10-02, 15:16 to 17:42 local, 2h26m)

One sequential driver (accept-rule commands verbatim, pinned order), each step preceded by a load gate
(1-minute load < 2.0, at most 10 minutes). No gate timeout; two steps waited (15 s, 45 s).

| Step | Load at start | Wall |
|---|---|---|
| judged round-off | 0.81 | 1547 s |
| judged continuous-off | 1.61 | 1384 s |
| judged continuous-on | 1.67 | 384 s |
| judged round-on | 1.50 | 469 s |
| Clear-Hash round-off | 1.50 | 346 s |
| Clear-Hash continuous-off | 1.80 (waited 15 s) | 317 s |
| Clear-Hash continuous-on | 1.34 | 117 s |
| Clear-Hash round-on | 1.72 | 130 s |
| analysis-400 round | 1.58 | 2071 s |
| analysis-400 continuous | 1.93 (waited 45 s) | 1923 s |

Twin `mq` exit 0 (valid, complete). Lines as printed (interpretation is Plan 227-12's):

```
MQ off D=-0.004516 margin=0.025206 d01=pass net=0.0 allowance=1 d03=pass
MQ on D=-0.001171 margin=0.025206 d01=pass net=0.4 allowance=1 d03=pass
MQ-REPORT off ... round_repeat_disagreement=0/60 (0.0000) (report-only)
MQ-REPORT on ... round_repeat_disagreement=0/60 (0.0000) (report-only)
MQ-CLEAR off D=-0.000722 net=0.000 ; MQ-CLEAR on D=-0.002602 net=1.000 ; MQ-A400 off D=0.000000 net=0.000
VIRTUAL-LOSS-TRIGGER false
```

Round-repeat disagreement (report-only): 0 of 60 positions in both judged cells.

## Task 2: interleaved throughput (2026-10-02, 17:43 to 20:07 local, 2h25m)

Committed driver `scripts/engine_interleave_227.py run` with judged defaults; 24 steps, all rc 0, no load-gate
timeouts (every step started below 2.0). Twin `throughput` exit 0:

| Config | Ratio (geo mean, probe-normalized) | Gain | Raw ratio | Grade ratio (report-only) |
|---|---|---|---|---|
| stop-p4 | 0.8095 | 19.0% | 0.8061 | 0.7852 |
| t400-p4 | 0.8582 | 14.2% | 0.8505 | 0.8228 |
| t50-p2 | 0.8201 | 18.0% | 0.8160 | 0.7923 |
| t400-p2 | 0.8106 | 18.9% | 0.8076 | 0.7835 |

`THROUGHPUT-BAR gain_met=true no_regression=true passed=true`; POOL2 t50-p2 median 0.8192 (noise 0.0051) and t400-p2
median 0.8155 (noise 0.0150), both pass at tolerance 1.03.

Per config and round (wall = summed `wall_ms` of the 16 judged rows; probe = `probe_total_ms`):

| config | round | A0 wall s | A0 probe s | A0 load1 | A1 wall s | A1 probe s | A1 load1 | norm ratio |
|---|---|---|---|---|---|---|---|---|
| stop-p4 | 1 | 61.1 | 12.27 | 1.40 | 48.3 | 12.01 | 1.57 | 0.8071 |
| stop-p4 | 2 | 60.0 | 11.89 | 1.76 | 49.0 | 11.99 | 1.85 | 0.8100 |
| stop-p4 | 3 | 60.2 | 11.88 | 1.85 | 48.9 | 11.89 | 1.59 | 0.8115 |
| t400-p4 | 1 | 611.9 | 11.91 | 1.78 | 522.6 | 11.83 | 1.94 | 0.8601 |
| t400-p4 | 2 | 612.6 | 12.07 | 1.97 | 519.9 | 11.86 | 1.88 | 0.8639 |
| t400-p4 | 3 | 612.1 | 11.90 | 1.75 | 519.4 | 11.87 | 1.90 | 0.8508 |
| t50-p2 | 1 | 101.9 | 11.86 | 1.73 | 83.1 | 11.89 | 1.74 | 0.8141 |
| t50-p2 | 2 | 102.3 | 11.91 | 1.93 | 83.2 | 11.70 | 1.93 | 0.8272 |
| t50-p2 | 3 | 101.4 | 11.87 | 1.79 | 83.1 | 11.86 | 1.72 | 0.8192 |
| t400-p2 | 1 | 699.7 | 11.95 | 1.90 | 564.2 | 11.78 | 1.42 | 0.8180 |
| t400-p2 | 2 | 697.0 | 11.98 | 1.88 | 564.2 | 11.89 | 1.68 | 0.8155 |
| t400-p2 | 3 | 698.3 | 11.75 | 1.69 | 563.5 | 11.88 | 1.49 | 0.7983 |

## Task 3: calibration (2026-10-02 20:08 to 2026-10-03 12:15 local, about 16h)

Five runbook cells x two arms, 50 games per (cell, anchor), seed 1, pinned anchors, each under
`bin/preset-supervisor.sh` with `PRESET_SUPERVISOR_{DIR,ANCHORS,GAMES=50,DISPATCH_MODE}`. Same-cell pairs; at most 6
supervisors at once (a detached scheduler launched the next pair only when at most 4 were live). No crash relaunches
(one launch per cell), no `ABORT`.

| Cell | Launched (UTC) | A0 (round) done | A1 (continuous) done |
|---|---|---|---|
| deep2300 0.5 | 2026-10-02 18:08 | 10-03 04:29 | 10-03 02:56 |
| deep1500 0.5 | 2026-10-02 18:08 | 10-03 06:41 | 10-03 04:40 |
| light1900 0.05 | 2026-10-02 18:08 | 10-03 05:43 | 10-03 03:44 |
| light1300 0.05 | 2026-10-03 01:44 | 10-03 12:14 | 10-03 10:27 |
| human1100 0 | 2026-10-03 02:41 | 10-03 05:47 | 10-03 05:47 |

(Completion times are local file times.) 2000 ledger rows; every row's `dispatch_mode` matches its arm.

`calibration_parity_verdict.py` (A1 vs A0): **verdict holds**.

| Family | Pooled shift +- se | Threshold | Null control (human1100) |
|---|---|---|---|
| Maia | +33.1 +- 28.1 | 85.0 | shift 0.0 +- 59.0, within 165 |
| Stockfish | -3.6 +- 28.7 | 50.0 | shift +24.4 +- 57.3, within 149 |

Per exposed cell (report): Maia deep2300 +188.0 +- 89.3 is outside its CI (the only one); every other cell is inside
(Maia light1300 +46.2 +- 45.6, deep1500 -40.0 +- 51.0, light1900 +41.7 +- 60.5; SF light1300 +29.7, deep1500 -46.9,
light1900 +13.7, deep2300 -28.9). Whether the deep2300 cell trips the twin's shape guard (z 1.96) is Plan 227-12's
gates evaluation; it is flagged here, not interpreted.

## Deviations from Plan

1. **Monitoring mechanics.** Calibration was watched with a one-shot background waiter (exits on any cell completion,
   launch or ABORT, or after about 2 h) instead of 30-minute Monitor re-arms. No effect on data.
2. **Pair scheduler.** The "launch light1300, then human1100 as earlier pairs finish" step ran as a detached scheduler
   script (`temp/227-11/` keeps the driver logs) rather than by hand. It enforced the same at-most-6 rule.
3. **Owner WebGPU leg arrived early.** The owner ran the interleaved WebGPU leg during the calibration sweep (it runs in
   the owner's browser, not on this box); committed as `cd7b17672` under Plan 227-12. Twin `webgpu`: median ratio
   0.676, pass.

Logs (not committed): `temp/227-11/mq-gate.log`, `temp/227-11/interleave.log`.

## Self-Check: PASSED

- Task 1 verify: TRIPWIRE PASS in 227-10-SUMMARY.md, twin `mq` exit 0, 10 committed MQ TSVs.
- Task 2 verify: 24 judged manifest rows all rc 0, twin `throughput` exit 0, manifest tracked.
- Task 3 verify: dispatch_mode check passes on 2000 rows, 10 cells files, `verdict-a1-vs-a0.json` tracked.
- No refit, flag flip or owner decision happened in this plan.
