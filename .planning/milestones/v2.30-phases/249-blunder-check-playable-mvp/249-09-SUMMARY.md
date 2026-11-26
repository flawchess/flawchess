---
phase: 249-blunder-check-playable-mvp
plan: 09
status: in-progress (Task 1 done; awaiting owner go-ahead, Task 2)
---

# 249-09 SUMMARY: browser UAT, go-ahead, ship

## Task 1: agent-run browser UAT on dev (2026-11-10)

Setup: phase branch `gsd/phase-249-blunder-check-playable-mvp` at a7becfea6, `bin/run_local.sh` (applied
`d5b8e2f1a249` to the dev DB), Chrome on http://localhost:5173. No UAT fix commits were needed.

Dev user: id 28 (aimfeld80@gmail.com). Original `beta_enabled` = false → set true for the UAT → restored to
false after the non-beta check (verified by `UPDATE ... RETURNING`).

Session 1 (6 own windows: 4 blunder, 2 herring; no foreign window, since own supply is ample, so the foreign
path rests on the plan 03/05/08 tests).

| Item | Result | Evidence |
|------|--------|----------|
| (a) tab visible, Start composes | pass | Blunder check tab shown for beta user; Start → "Window 1 of 6". Fresh `POST /api/blunder-check/sessions` measured at **255 ms** round trip from the browser (session 2) |
| (b) lead-in, arrow, prompt, 15 s countdown | pass | Arrow drawn with the piece still on its source square, "Safe or blunder?", countdown 15s → 0s |
| (c) correct Safe | pass | +1 flash, Points 0→1, move + reply played, next arrow. Sound not audible to the agent (not verifiable) |
| (d) timeout on a safe move | pass | Window 1 prompt 1 left to expire: no point awarded, window continued to the next prompt. The forfeit animation fell between screenshots (not visually captured) |
| (e) missed blunder | pass | Answered Safe on the blunder: −1 forfeit flash, then "Missed blunder" solution with Best (Bf8) and Game (Nh5) chips + lines, footer "Game: Rapid 10+5 · vs mqnr2 (1417) · Dec 18, 2025" |
| (f) caught blunder + better move | pass | Window 1: +3 (Points 1→4), "Find a better move"; Qf6 graded by the browser engine → +0, server tier 0, solution chips Move/Best/Game with line exploration. Window 5: key move Qb8 → "Good move" +2 (Points 12→14), solution shows the merged "Move = Best" chip. Analyze opened `/analysis?game_id=820108&ply=66` (pre-blunder position); Back lands on the tab start screen with "Session in progress: window 2 of 6" + Resume (known limit listed in 249-08) |
| (g) false alarm | pass | Blunder on a safe move: "False alarm / That move was safe." with only the flagged arrow, no Analyze, no footer, no chips |
| (h) herring cleared | pass | "All safe / Every move in this stretch was safe." with game footer, Analyze, Next |
| (i) reload mid-prompt | pass | Reload with 12 s left → Resume returned to the same prompt with the server clock still running (0 s, timed out because the reload+resume took >12 s of agent tool latency), then continued with the next prompt |
| (j) end screen Score % = DB | pass | UI "52% · 19 of 36 points" with per-window list; DB `sum(points_scored)=19`, `sum(points_possible)=36`, `floor(100*19/36)=52`, status `completed` |
| (k) phone width ~390 px | pass | `/train/blunder-check` in a 390×844 iframe (window resize is ignored by the extension): board, timer, Safe/Blunder and bottom nav fit, `scrollWidth` 386 (no horizontal scroll) |
| (l) console errors | pass | `read_console_messages onlyErrors` empty; all 42 `/api/blunder-check` requests returned 200 |

Observations for the owner (not defects, no change made):
- A blunder solution's Best chip shows "No moves yet" until its engine line search finishes (a few seconds),
  then the line appears. Pending-state copy could read "Searching…".
- Resume after a reload issues `POST /sessions/{id}/windows/{p}/start` twice (dev StrictMode double effect;
  the endpoint is idempotent, both 200).
- Prompt arrow colour is still the light-green played-move colour (249-07 flag, owner decision pending).

### D-01 non-beta check (dev)
With `beta_enabled=false` for user 28: `/train/blunder-check` lands on `/train`; tabs = Today, Leaderboard,
Archive (no Blunder check); `GET /api/blunder-check/sessions/open` → **403** with the user's token, **401**
anonymous.

### D-19 tuning SQL (flawchess-db MCP, read-only)

```sql
-- sessions started / completed, median duration
select status, count(*) n,
       percentile_cont(0.5) within group (order by extract(epoch from completed_at - started_at)) median_secs
from blunder_check_sessions group by status;
```
| status | n | median_secs |
|---|---|---|
| completed | 1 | 372.9 |
| open | 1 | null |

```sql
-- window outcome mix by case, own share
select outcome, window_case, count(*) n, round(avg(is_own::int)::numeric, 2) own_share
from blunder_check_windows group by outcome, window_case order by outcome nulls last, window_case;
```
| outcome | window_case | n | own_share |
|---|---|---|---|
| 0 (clear) | 0 | 2 | 1.00 |
| 1 (caught) | 1 | 2 | 1.00 |
| 2 (missed) | 1 | 1 | 1.00 |
| 2 (missed) | 2 | 1 | 1.00 |
| 3 (false alarm) | 1 | 1 | 1.00 |
| null (unplayed) | 0 | 2 | 1.00 |
| null (unplayed) | 1 | 3 | 1.00 |

(Session 2 was composed only to time `POST /sessions` and left open; its first window expired.)

```sql
-- open sessions whose latest answered row forfeited points
with last_ans as (
  select distinct on (w.session_id) w.session_id, a.points_forfeited, a.answered_at
  from blunder_check_answers a join blunder_check_windows w on w.id = a.window_id
  where a.answered_at is not null
  order by w.session_id, a.answered_at desc)
select count(*) as abandoned_after_forfeit
from blunder_check_sessions s join last_ans l on l.session_id = s.id
where s.status = 'open' and l.points_forfeited > 0;
```
| abandoned_after_forfeit |
|---|
| 0 |

No Umami event exists for blunder check (D-19 grep in plans 06–08 prints nothing).

Automated check: `uv run pytest tests/routers/test_blunder_check_sessions.py tests/routers/test_blunder_check_drill.py tests/routers/test_blunder_check_solution.py -x` → 63 passed.

## Task 2: owner go-ahead

Merge-only (owner, 2026-11-13, after 16 UAT rounds): "Squash and merge the phase 249 branch". No deploy go-ahead yet.

## Task 3: ship

Steps 1-4 done on 2026-11-13; steps 5-7 (deploy, prod checks, Sentry) are open.

Pre-merge review (two independent reviewers over `git diff main...HEAD`), owner-approved fixes:

- Early-ply floor now also caps the judged moves before a blunder (it was checked on the blunder ply only).
- A reload during the better-move step resumes it: the caught window stays the session's current window and
  `POST .../start` hands the task back (`WindowStartResponse.better_move`). Browser-checked on dev.
- "Back to start" after an error refreshes the open-session progress; neutral start-screen copy; low-time warning at 3 s.
- Migration `e6c9f3a2b249` (lead-in CHECK 0..4) folded into `d5b8e2f1a249`; dev DB re-stamped. Prod had neither.
- Wire fields `judged_ucis` and `refutation_uci` dropped (no reader). The `refutation_uci` column stays.
- UAT residue removed: unread state fields, unreachable props, never-shipped cache shims, stale 15 s / 4-ply / "safe" comments.

Left as is (follow-ups): `served_ply_ranges` is applied to herring runs only, so a blunder window can re-serve good
moves judged in an earlier window of the same game; the drill's error messages are never rendered (generic LoadError);
the Phase 248 calibration report applies neither the undecided-position rule nor the early-ply floor.

Gate on the phase branch with main merged in: ruff format/check, ty (app and analysis), nesting depth, `pytest -n auto`
(6186 passed), serial `pytest -x` (6186 passed, 6:59), frontend lint, build, tests (6246 passed), knip: all green.

Benchmark lane: run `bin/benchmark_db.sh start` (applies `d5b8e2f1a249`) before restarting the :8001 backend.
