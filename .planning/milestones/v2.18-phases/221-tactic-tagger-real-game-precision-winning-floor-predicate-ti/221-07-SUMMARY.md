---
phase: 221-tactic-tagger-real-game-precision-winning-floor-predicate-ti
plan: 07
subsystem: tactic-tagger
tags: [prod-retag, release, acceptance-queries, tagfix-09, operator-run]

requires:
  - phase: 221-06
    provides: "the merged detector/gate code, the clearance SUPPRESS decision, the dev retag smoke this prod run is compared against"
  - phase: 221-08
    provides: "D-05 retired (sacrifice back to cook's unguarded predicate under D-01's winning floor); the prod retag runs the post-retirement code"
provides:
  - "Phase 221 released to production as ONE squash-merge (d139075e8 on main) -> PR #358 -> production cb5f2d622, deployed via bin/deploy.sh, server HEAD verified"
  - "Full unscoped prod retag at the default margin: 4,764,060 flaws examined, 246,112 rows changed, 3h17m over the SSH tunnel"
  - "reports/retag/retag-2026-09-13.md — the prod writing run's four-bucket report (committed de89898c0)"
  - "TAGFIX-09 acceptance answered on prod with before/after numbers and verbatim SQL (this file)"
affects: []

actuals:
  tokens: 9000
  tasks: 3
  commits: 2
  plan_head_before: 5ebe1d4c7

tech-stack:
  added: []
  patterns:
    - "Prod baseline BEFORE any write: every acceptance figure's 'before' column is captured with SELECT-only queries in the same session, because the retag destroys it"
    - "Python 3.14 raised io.DEFAULT_BUFFER_SIZE to 128 KiB: a retag log redirected to a file flushes only every ~1,300 page lines, so progress must be read from pg_stat_user_tables.n_tup_upd / pg_stat_activity, not from the logfile"

key-files:
  created:
    - reports/retag/retag-2026-09-13.md
  modified: []

key-decisions:
  - "Ran the prod retag from the local box over bin/prod_db_tunnel.sh (the plan's stated path, proven at multi-million-row scale in Phase 220) rather than on the server; 3h17m for 4.76M rows was acceptable off-peak"
  - "Allowed-sacrifice reduction landed at 6.9x, short of the 10x target. Recorded as a shortfall, not patched: the 10x prediction was made with D-05 in force, and D-05 was retired by the operator in plan 08 after the spot-check showed it dropping real sacrifices. SACRIFICE_CLEARANCE_MAX_DEPTH (=4) is the remaining lever; not touched in this plan"
  - "The script prints no host:port banner (the plan's T-221-34 assumed one). Target verified instead by resolving db_url_for_target('prod') read-only to localhost:15432/flawchess and by inet_server_addr()/current_database() on the tunnel connection"

patterns-established: []

requirements-completed: [TAGFIX-09]

coverage:
  - id: D1
    description: "One release: single squash-merge, one main->production PR, one bin/deploy.sh, server SHA verified before any prod write"
    requirement: TAGFIX-09
    verification:
      - kind: other
        ref: "git log --oneline main | grep -c 'feat(221)' == 1; gh pr 358 merged -> production cb5f2d622; ssh flawchess 'git rev-parse HEAD' == cb5f2d622 == git rev-parse origin/production; git rev-list --left-right --count main...origin/main == 0 0"
        status: pass
    human_judgment: false
  - id: D2
    description: "Full unscoped prod retag at the default margin completed, report committed, bounded re-run idempotent"
    requirement: TAGFIX-09
    verification:
      - kind: other
        ref: "scripts/retag_flaws.py --db prod --workers 6 --throttle-ms 50 (4,764,060 examined / 246,112 changed); reports/retag/retag-2026-09-13.md committed de89898c0; re-run --db prod --limit 4000: 0 changed"
        status: pass
    human_judgment: false
  - id: D3
    description: "TAGFIX-09 acceptance queries: losing share <5% per motif and <2% overall in both orientations; zero motif-14, zero motif-15, zero odd-depth motif-6; missed intermezzo within 3x of allowed"
    requirement: TAGFIX-09
    verification:
      - kind: other
        ref: "§2.1 SQL both orientations on TABLESAMPLE SYSTEM (3): allowed max 0.4% (sacrifice, 1/225), overall 0.01%; missed 0.0% every motif; m14 0/0, m15 0/0, m6 odd 0/0; intermezzo 4,611 allowed vs 2,957 missed (1.56x)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Allowed sacrifice count down at least 10x"
    requirement: TAGFIX-09
    verification:
      - kind: other
        ref: "58,863 -> 8,568 = 6.9x; target not met, shortfall recorded with the lever named (see Acceptance claim 5)"
        status: fail
    human_judgment: true
    rationale: "Whether 6.9x is acceptable given the operator's own D-05 retirement (plan 08), or whether SACRIFICE_CLEARANCE_MAX_DEPTH should be lowered in a follow-up, is the operator's call"
  - id: D5
    description: "Product reads correctly on flawchess.com after the retag (remaining tactic chips are real tactics; Library tactic grid renders without the clearance family)"
    requirement: TAGFIX-09
    verification: []
    human_judgment: true
    rationale: "The plan's <human-check>; the operator announced an independent cross-check of the before/after distribution, sacrifice's losing-line share and rows 0064/0133 against prod"

duration: ~3h40m wall (3h17m of it the retag itself)
completed: 2026-09-13
status: complete
---

# Phase 221 Plan 07: Release Gate, Full Prod Retag, TAGFIX-09 Acceptance Summary

**Phase 221 shipped to production in one release and every persisted tactic tag in prod was re-derived (4.76M flaws, 246,112 rows changed): losing-line share fell from 10.7% to 0.01% (allowed) and 3.1% to 0.0% (missed), motif 14, clearance and odd discovered-attack depths are gone, missed intermezzo is within 1.6x of allowed; allowed sacrifice fell 6.9x against a 10x target, an expected consequence of the D-05 retirement.**

## Performance

- **Duration:** ~3h40m wall (deploy ~25 min, retag 3h17m, acceptance ~5 min)
- **Started:** 2026-09-12T22:45Z (deploy preflight)
- **Completed:** 2026-09-13T02:35Z
- **Tasks:** 3 completed (1 human-action checkpoint, 2 auto)
- **Files modified:** 1 created (the prod report)

## Task 0 — Release gate (checkpoint:human-action)

The operator pre-answered the checkpoint ("answer done once the deploy is verified") and asked for `/deploy` to run first. Deploy skill run:

| Step | Result |
|---|---|
| Preflight | clean tree, on `main`, `main...origin/main` = `0 0`, 9 real commits since last release |
| Pre-PR gates | ruff format (481 unchanged), ruff check, ty (app/tests/scripts), ty (analysis), eslint: all clean |
| PR | #358 `main -> production`, CI run 34723659503 green in 8m56s (pytest, tagger precision gate, frontend, Trivy) |
| Squash-merge | `cb5f2d622` on `production` |
| `bin/deploy.sh` | run 34724082781 on `production@cb5f2d622`, deploy job 1m22s, "Production is at cb5f2d62", forward-port merge pushed to `main` (`5ebe1d4c7`) |
| Post-deploy | `HTTP 200 in 0.07s`; backend + caddy containers Up; backend log serving remote workers, no errors |

**Read-only pre-retag assertions (all held):**

```
ssh flawchess "cd /opt/flawchess && git rev-parse HEAD"   -> cb5f2d622b5390239adc284b9da1a1426f52a50b
git rev-parse origin/production                            -> cb5f2d622b5390239adc284b9da1a1426f52a50b
git rev-list --left-right --count main...origin/main       -> 0	0
git diff --stat origin/production HEAD                     -> (empty: local tree == deployed tree)
git log --oneline main | grep -c "feat(221)"               -> 1   (one squash-merge, D-14)
grep -n "Tactic tags on your games" CHANGELOG.md           -> line 14 under [Unreleased]
```

flawchess.com exposes no version endpoint; the server-side `git rev-parse HEAD` that `bin/deploy.sh` itself performs is the deployed-SHA evidence.

## Task 1 — Full prod retag

### Pre-retag baseline (SELECT-only, 2026-09-12 ~23:10 UTC, before any write)

```sql
SELECT count(*) AS total_flaws,
 count(*) FILTER (WHERE allowed_tactic_motif = 14) AS allowed_m14,
 count(*) FILTER (WHERE missed_tactic_motif = 14) AS missed_m14,
 count(*) FILTER (WHERE allowed_tactic_motif = 15) AS allowed_m15,
 count(*) FILTER (WHERE missed_tactic_motif = 15) AS missed_m15,
 count(*) FILTER (WHERE allowed_tactic_motif = 6) AS allowed_m6,
 count(*) FILTER (WHERE allowed_tactic_motif = 6 AND allowed_tactic_depth % 2 = 1) AS allowed_m6_odd,
 count(*) FILTER (WHERE missed_tactic_motif = 6) AS missed_m6,
 count(*) FILTER (WHERE missed_tactic_motif = 6 AND missed_tactic_depth % 2 = 1) AS missed_m6_odd,
 count(*) FILTER (WHERE allowed_tactic_motif IS NOT NULL) AS allowed_tagged,
 count(*) FILTER (WHERE missed_tactic_motif IS NOT NULL) AS missed_tagged
FROM game_flaws;
```

| figure | before |
|---|---:|
| total_flaws | 4,760,857 (the plan's "~3.18M" was stale) |
| allowed_tagged / missed_tagged | 781,191 / 384,537 |
| allowed_m14 / missed_m14 | 74 / 53 |
| allowed_m15 / missed_m15 (clearance) | 23,473 / 11,962 |
| allowed_m6 odd-depth | 28,487 of 28,488 (99.996%) |
| missed_m6 odd-depth | 16,546 of 16,547 |
| allowed sacrifice (17) / missed sacrifice | 58,863 / 17,682 |
| allowed intermezzo (11) / missed intermezzo | 6,873 / 431 (15.9x) |

Per-motif allowed counts before: `2:215244 8:167124 1:126036 17:58863 3:56108 6:28488 15:23473 10:14716 9:13880 25:13467 4:12640 28:10807 26:9410 7:8107 11:6873 16:5167 13:2518 27:2011 5:1800 20:1135 18:916 12:554 21:507 29:414 24:349 19:220 23:184 22:99 14:74`.
Per-motif missed counts before: `8:103140 1:66062 2:64295 3:34421 17:17682 6:16547 15:11962 9:11520 28:11501 10:11012 25:8866 4:8116 26:6135 16:3110 7:2748 13:1708 5:1331 27:1188 20:753 11:431 18:430 21:382 12:367 29:252 24:228 19:141 23:89 22:67 14:53`.

The §2.1 "before" tables are in the acceptance section below, beside the "after" columns. `import_jobs` carried no running or pending job (1,167 completed, 37 failed).

### Target verification (T-221-34)

`scripts/retag_flaws.py` prints no host:port banner (the plan assumed one). Verified instead:

```
$ uv run python -c "from urllib.parse import urlparse; from app.core.config import db_url_for_target; u=urlparse(db_url_for_target('prod')); print(u.hostname, u.port, u.path)"
localhost 15432 /flawchess
-- on the tunnel connection:
SELECT current_database(), inet_server_addr(), inet_server_port(), version();
flawchess | 172.18.0.4 | 5432 | PostgreSQL 18.6 on x86_64-pc-linux-musl
```

### Bounded rehearsal

`uv run python scripts/retag_flaws.py --db prod --dry-run --limit 4000 --workers 6` (23:11:06 to 23:11:16 UTC): 4,000 examined, 255 would change. Allowed: SACRIFICE 68 -> 61 suppressed (89.7%), CLEARANCE 28 -> 26 suppressed + 2 shifted (0 survive), DISCOVERED_ATTACK 29 -> 14 depth-shifted, FORK 1.5%, HANGING_PIECE 7.8%, MATE 1.2%. Directionally identical to the dev smoke (dev: sacrifice 94.4%, clearance 91.8%). The dry-run report landed on the dev smoke's date-keyed path (`retag-2026-09-12.md`); it was copied aside and the committed dev report restored with `git checkout`.

### Full refresh

```
uv run python scripts/retag_flaws.py --db prod --workers 6 --throttle-ms 50
```

No `--only-tagged`, no `--dry-run`, no `--user-id`, no `--margin` (defaulted to `ONLY_MOVE_WIN_PROB_MARGIN` = 0.35). Launched with `setsid nohup … > <scratchpad>/retag/prod-run.log 2>&1 < /dev/null &` from the orchestrator (never a subagent); python PID 2057087, six spawn workers, one DB connection over the tunnel.

| | |
|---|---|
| Start | 2026-09-12 23:12:18 UTC |
| End | 2026-09-13 02:29:48 UTC (3h17m30s) |
| Flaw rows examined | 4,764,060 |
| Flaw rows changed | 246,112 |
| Batch | 2,000 rows per commit, 50 ms throttle after each commit |
| Prod load during run | db container ~34% CPU, host load 0.9, 9.4 GB available RAM; live worker traffic unaffected |
| Logfile | `<scratchpad>/retag/prod-run.log` (session scratchpad; the committed report is the durable record) |

Note for future operators: the log went silent from 01:00 to 02:29 while the run was healthy. Python 3.14 raised `io.DEFAULT_BUFFER_SIZE` to 128 KiB, so a file-redirected log flushes only every ~1,300 page lines. Progress was confirmed from `pg_stat_user_tables.n_tup_upd` growth and the active page query in `pg_stat_activity`.

### Report

`reports/retag/retag-2026-09-13.md`, committed `de89898c0`. `retag-2026-09-12.md` remains the dev smoke. Excerpt (allowed orientation):

| Motif | Previously tagged | Gate suppressed | Survived | Motif shifted | Depth shifted | Suppression % |
|---|---:|---:|---:|---:|---:|---:|
| SACRIFICE | 58861 | 50587 | 7735 | 539 | 0 | 85.9% |
| CLEARANCE | 23471 | 21182 | 0 | 2289 | 0 | 90.2% |
| SELF_INTERFERENCE | 74 | 68 | 0 | 6 | 0 | 91.9% |
| DISCOVERED_ATTACK | 28495 | 10210 | 8 | 999 | 17278 | 35.8% |
| INTERMEZZO | 6873 | 2341 | 4523 | 9 | 0 | 34.1% |
| FORK | 126144 | 4268 | 121692 | 183 | 1 | 3.4% |
| HANGING_PIECE | 215444 | 13098 | 202233 | 113 | 0 | 6.1% |
| MATE | 167260 | 1004 | 166246 | 9 | 1 | 0.6% |
| PIN | 56138 | 4871 | 51126 | 139 | 2 | 8.7% |

Totals: allowed 122,082 / 781,725 suppressed (15.6%); missed 98,090 / 384,790 (25.5%). Missed MATE lost 34.9% (35,986 rows), the D-04 mate-derived already-winning reject on lines where the mover was already being mated; missed PROMOTION 58.6%.

### Idempotency

```
uv run python scripts/retag_flaws.py --db prod --limit 4000 --workers 6     (writing mode, 02:31:07 UTC)
Page 1: 2000 flaws examined, 0 changed
Page 2: 2000 flaws examined, 0 changed
Flaw rows changed: 0
```

Its report overwrote `retag-2026-09-13.md`; the committed prod-run version was restored with `git checkout` (tree clean).

**No DDL, migration, TRUNCATE or DELETE was issued against prod.** Commands run against prod, in full: the SELECT-only baseline and acceptance queries via the query-only `flawchess-prod-db` MCP server, `retag_flaws.py --db prod --dry-run --limit 4000`, `retag_flaws.py --db prod --workers 6 --throttle-ms 50`, `retag_flaws.py --db prod --limit 4000`. The retag's only write is `bulk_update_tactic_tags` on the eight tactic columns.

## Task 2 — TAGFIX-09 acceptance queries

All "after" queries ran 02:31 UTC, after the completion line and the 0-change idempotency pass. Sample queries use `TABLESAMPLE SYSTEM (3)` as the review did; counts are full-table.

### Claim 1 — Losing-line share below 5% per motif and 2% overall, both orientations: **PASS**

```sql
-- ALLOWED (for MISSED: allowed_* -> missed_*, ply % 2 = 1 -> ply % 2 = 0)
WITH t AS (
  SELECT f.allowed_tactic_motif m, f.allowed_tactic_depth d,
         (f.ply % 2 = 1) AS solver_white,
         f.allowed_pv_lines -> (f.allowed_tactic_depth + (f.allowed_tactic_depth % 2)) AS node
  FROM game_flaws f TABLESAMPLE SYSTEM (3)
  WHERE f.allowed_tactic_motif IS NOT NULL AND f.allowed_pv_lines IS NOT NULL AND f.allowed_tactic_depth IS NOT NULL
), e AS (
  SELECT m, d,
    CASE WHEN node->>'bm' IS NOT NULL THEN (CASE WHEN solver_white THEN (node->>'bm')::int ELSE -(node->>'bm')::int END) END AS mate,
    CASE WHEN node->>'bm' IS NULL AND node->>'b' IS NOT NULL THEN (CASE WHEN solver_white THEN (node->>'b')::int ELSE -(node->>'b')::int END) END AS cp
  FROM t WHERE node IS NOT NULL
)
SELECT m, count(*) n, round(avg(d),2) avg_depth,
  count(*) FILTER (WHERE mate > 0) mate_for, count(*) FILTER (WHERE cp >= 200) ge200,
  count(*) FILTER (WHERE cp >= 0 AND cp < 200) zero_199, count(*) FILTER (WHERE cp < 0 OR mate < 0) losing,
  round(100.0*count(*) FILTER (WHERE cp < 0 OR mate < 0)/count(*),1) losing_pct
FROM e GROUP BY m ORDER BY n DESC;
```

**Allowed orientation** (before = same query 23:10 UTC pre-retag; after = 02:31 UTC):

| m | motif | n before | losing before | losing % before | n after | losing after | losing % after |
|---:|---|---:|---:|---:|---:|---:|---:|
| 2 | hanging-piece | 6376 | 260 | 4.1 | 5993 | 0 | 0.0 |
| 8 | mate | 4919 | 0 | 0.0 | 4965 | 0 | 0.0 |
| 1 | fork | 3750 | 82 | 2.2 | 3680 | 0 | 0.0 |
| 17 | sacrifice | 1696 | 1322 | **77.9** | 225 | 1 | **0.4** |
| 3 | pin | 1637 | 98 | 6.0 | 1597 | 0 | 0.0 |
| 6 | discovered-attack | 864 | 37 | 4.3 | 639 | 0 | 0.0 |
| 15 | clearance | 709 | 347 | 48.9 | — | — | absent |
| 25 | discovered-check | 415 | 17 | 4.1 | 359 | 0 | 0.0 |
| 10 | attraction | 411 | 38 | 9.2 | 395 | 0 | 0.0 |
| 9 | deflection | 376 | 51 | 13.6 | 310 | 0 | 0.0 |
| 4 | skewer | 359 | 39 | 10.9 | 350 | 0 | 0.0 |
| 28 | promotion | 328 | 55 | 16.8 | 224 | 0 | 0.0 |
| 26 | trapped-piece | 268 | 16 | 6.0 | 345 | 0 | 0.0 |
| 7 | back-rank-mate | 229 | 0 | 0.0 | 235 | 0 | 0.0 |
| 11 | intermezzo | 217 | 55 | 25.3 | 136 | 0 | 0.0 |
| 16 | capturing-defender | 167 | 16 | 9.6 | 119 | 0 | 0.0 |
| 5 | double-check | 67 | 4 | 6.0 | 60 | 0 | 0.0 |
| 13 | interference | 65 | 8 | 12.3 | 57 | 0 | 0.0 |
| 27 | en-passant | 41 | 3 | 7.3 | 59 | 0 | 0.0 |
| 12 | x-ray | 12 | 3 | 25.0 | 10 | 0 | 0.0 |
| 29 | under-promotion | 5 | 5 | 100.0 | 3 | 0 | 0.0 |
| 14 | self-interference | 2 | 1 | 50.0 | — | — | absent |
| 18,20,21,19,24,23,22 | mate patterns | 111 | 0 | 0.0 | 95 | 0 | 0.0 |
| **all** | | **23024** | **2457** | **10.7** | **19856** | **1** | **0.01** |

**Missed orientation** (before / after):

| m | motif | n before | losing before | losing % before | n after | losing after | losing % after |
|---:|---|---:|---:|---:|---:|---:|---:|
| 8 | mate | 3076 | 0 | 0.0 | 2043 | 0 | 0.0 |
| 2 | hanging-piece | 1999 | 2 | 0.1 | 1825 | 0 | 0.0 |
| 1 | fork | 1962 | 24 | 1.2 | 1833 | 0 | 0.0 |
| 3 | pin | 997 | 20 | 2.0 | 877 | 0 | 0.0 |
| 17 | sacrifice | 519 | 170 | **32.8** | 212 | 0 | **0.0** |
| 6 | discovered-attack | 442 | 7 | 1.6 | 352 | 0 | 0.0 |
| 15 | clearance | 343 | 40 | 11.7 | — | — | absent |
| 10 | attraction | 323 | 8 | 2.5 | 254 | 0 | 0.0 |
| 28 | promotion | 319 | 9 | 2.8 | 134 | 0 | 0.0 |
| 9 | deflection | 310 | 20 | 6.5 | 235 | 0 | 0.0 |
| 25 | discovered-check | 255 | 3 | 1.2 | 172 | 0 | 0.0 |
| 4 | skewer | 231 | 22 | 9.5 | 180 | 0 | 0.0 |
| 26 | trapped-piece | 182 | 15 | 8.2 | 233 | 0 | 0.0 |
| 16 | capturing-defender | 79 | 5 | 6.3 | 53 | 0 | 0.0 |
| 13 | interference | 51 | 4 | 7.8 | 31 | 0 | 0.0 |
| 11 | intermezzo | 10 | 0 | 0.0 | 81 | 0 | 0.0 |
| 12 | x-ray | 8 | 1 | 12.5 | 6 | 0 | 0.0 |
| 29 | under-promotion | 9 | 1 | 11.1 | 1 | 0 | 0.0 |
| 14 | self-interference | 3 | 0 | 0.0 | — | — | absent |
| others | mate patterns, en-passant, double-check | 224 | 3 | 1.3 | 216 | 0 | 0.0 |
| **all** | | **11342** | **354** | **3.1** | **8728** | **0** | **0.0** |

Every motif is below 5% in both orientations; the single residual is one allowed sacrifice row out of 225 sampled (0.4%). Overall 0.01% allowed, 0.0% missed, both far under 2%. No thin-motif misses: x-ray (10 / 6 rows) and under-promotion (3 / 1) are at 0.0%.

### Claim 2 — Motif 14 gone: **PASS** (0 allowed, 0 missed; before 74 / 53)

```sql
SELECT count(*) FILTER (WHERE allowed_tactic_motif = 14), count(*) FILTER (WHERE missed_tactic_motif = 14) FROM game_flaws;
-- 0 | 0
```

This is the ONLY evidence for this leg: the dev database has zero motif-14 rows, so the dev smoke could not test it. The report's SELF_INTERFERENCE rows: 68 suppressed + 6 motif-shifted (allowed), 45 + 8 (missed).

### Claim 3 — Motif 15 (clearance was SUPPRESSED in plan 06): **PASS** (0 / 0; before 23,473 / 11,962)

```sql
SELECT count(*) FILTER (WHERE allowed_tactic_motif = 15), count(*) FILTER (WHERE missed_tactic_motif = 15) FROM game_flaws;
-- 0 | 0
```

### Claim 4 — Odd discovered-attack depths gone (D-11): **PASS** (0 / 0; before 28,487 of 28,488 and 16,546 of 16,547)

```sql
SELECT count(*) FILTER (WHERE allowed_tactic_motif = 6 AND allowed_tactic_depth % 2 = 1),
       count(*) FILTER (WHERE missed_tactic_motif = 6 AND missed_tactic_depth % 2 = 1) FROM game_flaws;
-- 0 | 0
```

Motif 6 now: 20,225 allowed / 12,304 missed; 17,278 allowed and 10,325 missed rows are in the report's depth-shifted bucket.

### Claim 5 — Allowed sacrifice down 10x: **NOT MET (6.9x)**

```sql
SELECT count(*) FILTER (WHERE allowed_tactic_motif = 17), count(*) FILTER (WHERE missed_tactic_motif = 17) FROM game_flaws;
-- 8568 | 7979        (before: 58863 | 17682)
```

Allowed 58,863 -> 8,568 (ratio 6.87); missed 17,682 -> 7,979 (2.22). Of the 58,861 previously-tagged allowed rows, 50,587 were gate-suppressed, 539 shifted to another motif, 7,735 survived; ~830 rows arrived from other motifs or new detections.

Why it fell short, and the lever: the 10x prediction (review simulation, ~-90%) was made with D-05 (the boards[k+3] persistence check) in force. The operator retired D-05 in plan 08 after the D-13 spot-check showed it dropping confirmed real sacrifices (rows 0064, 0133); plan 08's own SUMMARY predicted "higher survival" for sacrifice here. The dev smoke in plan 06 (D-05 still on) measured -94.4%; the prod run without D-05 measured -85.9%. The remaining named lever is `SACRIFICE_CLEARANCE_MAX_DEPTH` (= 4, `app/services/tactic_detector.py:92`); lowering it would cut the surviving deeper sacrifices. No constant was changed in this plan and no sacrifice persistence rule was reintroduced. Note the quality dimension the count does not capture: sacrifice's losing-line share went 77.9% -> 0.4% (allowed) and 32.8% -> 0.0% (missed), so what survives is no longer "the opponent's best defence sheds material while lost".

### Claim 6 — Missed intermezzo within 3x of allowed: **PASS**

```sql
SELECT count(*) FILTER (WHERE allowed_tactic_motif = 11), count(*) FILTER (WHERE missed_tactic_motif = 11) FROM game_flaws;
-- 4611 | 2957        (before: 6873 | 431, 15.9x; ROADMAP baseline 188 vs 6, 31x)
```

Ratio allowed/missed 1.56 (missed/allowed 0.64). Missed intermezzo grew 431 -> 2,957 despite the gate: the D-09 move-stack fix lets it fire at k=2 on missed lines.

### Spot-check rows carried from 221-D13-SPOTCHECK.md

```sql
SELECT game_id, ply, allowed_tactic_motif, allowed_tactic_depth, allowed_tactic_confidence,
       missed_tactic_motif, missed_tactic_depth, missed_tactic_confidence
FROM game_flaws WHERE (game_id, ply) IN ((1060871, 23), (1689373, 26));
-- 1060871 | 23 | 17 | 2 | 100 | null | null | null      (row 0064, allowed sacrifice)
-- 1689373 | 26 | null | null | null | 17 | 2 | 100       (row 0133, missed sacrifice)
```

Both operator-confirmed real sacrifices carry their tag after the retag (they carried it before as well; with D-05 they would have been dropped).

## Phase verdict — ROADMAP success criteria

| # | Criterion | Verdict | Evidence |
|---|---|---|---|
| 1 | Fixture gate green; oracle 0 cook-only for deflection/fork/trapped-piece, 0 ours-only for discovered-attack; sacrifice/clearance divergences documented | **Met** | 221-06-SUMMARY oracle table (all four required-zero cells 0); after plan 08 sacrifice's cookOnly divergence is gone by construction (predicate reverted to cook's), clearance's is the documented suppression; tagger gate green in CI run 34723659503 ("Tagger precision gate" step) |
| 2 | Real-game gate scored before/after: sacrifice and clearance real-share >= 0.8 or clearance suppressed; no other motif drops | **Met with a documented exception** | clearance suppressed (221-06); sacrifice real_share 0.385 vs floor 0.33 (221-08) is below 0.8 but above its pre-fix baseline 0.375; promotion's single-row dip (n=4, un-gated) recorded in 221-06 |
| 3 | Dev retag delta within reason of the simulation; survivors read as real tactics | **Met** | 221-06 dev smoke: sacrifice -94.4%, clearance fully cleared, tier-2 deviations explained (D-04 combined effect); four survivor lines spot-checked as real |
| 4 | Prod retag done, acceptance queries pasted | **Met** (5 of 6 claims pass; claim 5 at 6.9x vs 10x recorded above) | this file |
| 5 | No `bin/reset_db.sh`, migration, MultiPV re-eval, or change to `PV_CAP_PLIES`, `ONLY_MOVE_CP_GAP_THRESHOLD`, D-05 depth-primary dispatch | **Met** | `git diff --stat 3ceab603a d139075e8 -- alembic/ app/models/` empty; `git diff 3ceab603a d139075e8 -- app/` shows no `PV_CAP_PLIES =` / `ONLY_MOVE_CP_GAP_THRESHOLD =` hunk (`engine.py:109` = 12, `forcing_line_gate.py:78` = 100 unchanged); no engine pass in any plan; `bin/reset_db.sh` not run (dev smoke ran on the existing dev DB) |

## Residual old-value inventory

- `game_flaws.allowed_pv_lines` / `missed_pv_lines` JSONB blobs: read-only inputs, NOT rewritten. The old tags can be recomputed by reverting the code and re-running the same retag (another ~3h prod write).
- No materialised aggregate of motif counts exists; the Library tactic comparison grid and the Train pool recompute from the eight columns at read time, so they reflect the retag immediately.
- Frontend bundle: changed (clearance family removed from `TacticFamily`, colours, icon, Advanced group) and deployed in the same release.
- `TacticMotifInt` 14 and 15 remain encodable/decodable for old rows; prod now has zero such rows.

## Task Commits

1. **T-221-07-00: Release gate** — no commit in this plan; release commits are `cb5f2d622` (production, PR #358) and `5ebe1d4c7` (forward-port on main)
2. **T-221-07-01: Full prod retag** — `de89898c0` (docs: prod retag report)
3. **T-221-07-02: Acceptance queries** — this SUMMARY (docs commit below)

## Deviations from Plan

**1. [Rule 3 - Blocking] No host:port banner to paste.** The plan's T-221-34 mitigation expected `retag_flaws.py` to print the resolved target. It prints scope/mode/margin only. Substituted an equivalent read-only check (`db_url_for_target('prod')` parsed to host/port/db, plus `current_database()`/`inet_server_addr()` on the tunnel connection). No code changed.

**2. Date-keyed report collision.** The dry-run rehearsal (23:11 UTC on 09-12) overwrote the committed dev smoke report `retag-2026-09-12.md`, and the idempotency pass overwrote the prod report `retag-2026-09-13.md`. Both were restored with `git checkout` after copying the transient reports to the scratchpad; the committed files are the dev smoke and the prod writing run respectively, as the plan requires.

**3. Plan text still references D-05** ("do not relax D-05"). D-05 was retired in gap-closure plan 08 before this plan ran; no sacrifice persistence rule was reintroduced, and the sacrifice shortfall is attributed to that retirement rather than patched.

## Issues Encountered

- Log silence 01:00-02:29 UTC caused by Python 3.14's 128 KiB stdout buffer (see Task 1). Diagnosed via `pg_stat_user_tables.n_tup_upd` deltas; no action needed.

## User Setup Required

None.

## Operator human-check (open)

The plan's `<human-check>` (open a game with a former sacrifice/clearance tag on flawchess.com, confirm remaining chips are real tactics, confirm the Library tactic grid renders without the clearance family) is left to the operator, who announced an independent cross-check of the before/after distribution, sacrifice's losing-line share and rows 0064/0133 against prod. All figures needed for that cross-check are in this file.

## Next Phase Readiness

- Phase 221 is fully executed (8 of 8 plans). Remaining: verifier, phase completion, milestone bookkeeping.
- Open follow-up (not scheduled, flag only): allowed sacrifice at 6.9x rather than 10x; the lever is `SACRIFICE_CLEARANCE_MAX_DEPTH` if the operator wants the count lower. The losing-line signal the phase targeted is already at 0.4%.

## Self-Check: PASSED

`reports/retag/retag-2026-09-13.md` on disk with "Motif shifted" and "Depth shifted" columns; commit `de89898c0` in `git log`; working tree clean after the report restores.

---
*Phase: 221-tactic-tagger-real-game-precision-winning-floor-predicate-ti*
*Completed: 2026-09-13*
