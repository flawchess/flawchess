---
phase: 77-troll-opening-watermark-on-insights-findings
plan: 02
subsystem: frontend-curation
tags: [troll-openings, curation-script, frontend, partial]
status: checkpoint-pending
requires:
  - chess.js (already installed @1.4.0)
provides:
  - frontend/scripts/curate-troll-openings.ts (curation pipeline)
affects:
  - frontend/src/data/trollOpenings.ts (Task 3 — pending user approval)
tech-stack:
  added: []
  patterns:
    - "Node/TS curation script run via npx tsx — no permanent devDependency added per D-09 anti-pattern"
key-files:
  created:
    - frontend/scripts/curate-troll-openings.ts
    - frontend/scripts/.cache/.gitignore
  modified: []
decisions:
  - "Per-ply emission (both colors) rather than final-position-only — pushes ambiguity into the human review step per Pitfall 2"
  - "Cache directory .gitignore uses -f stage because root .gitignore already excludes .cache (line 59)"
metrics:
  duration: pending-checkpoint
  completed: null
---

# Phase 77 Plan 02: Curate troll openings (PARTIAL — checkpoint pending)

**Status:** Awaiting user approval at Task 2 checkpoint before proceeding to Task 3.

One-liner: Reproducible Node/TS curation script committed; awaiting human pruning of 542 candidates before writing the static data module.

## Tasks Completed

| Task | Name                                                                        | Commit  | Files                                                                                |
| ---- | --------------------------------------------------------------------------- | ------- | ------------------------------------------------------------------------------------ |
| 1    | Create curation script that emits candidates to stdout                      | 7c7dd3b | frontend/scripts/curate-troll-openings.ts, frontend/scripts/.cache/.gitignore        |
| 2    | Surface candidate list to user for hand-pruning approval (D-01 checkpoint) | —       | /tmp/troll-candidates.txt (transient, surfaced inline)                               |

## Tasks Pending

- Task 2: awaiting user approval of pruned set.
- Task 3: not started — depends on Task 2 outcome.

## Curation Run Output

- Cache: `frontend/scripts/.cache/cEDAMVBB.pgn` (19,693 bytes, fetched from `https://lichess.org/study/cEDAMVBB.pgn`, gitignored).
- Chapters parsed: 46 (one chapter has empty mainline and was skipped — chapter 36).
- Total candidates emitted: 542 (per-ply × both colors across 46 chapters).
- Bongcloud canonical defining-position key `8/8/8/8/4P3/8/PPPPKPPP/RNBQ1BNR` is present in the candidate list (sanity check passed).

## Gap Flagged for User Review

The user's stated minimum target set per D-01 / Task 2 prompt is:
- Bongcloud Attack (white) — `1.e4 e5 2.Ke2`
- Grob (white) — `1.g4`
- Borg / Reversed Grob (black) — `1.e4 g5`
- Halloween Gambit (white) — `1.e4 e5 2.Nf3 Nc6 3.Nc3 Nf6 4.Nxe5`
- Barnes Opening (white) — `1.f3`
- Fred Defense (black) — `1.e4 f5`

Of those, only **Bongcloud (chapter 19)** and **Halloween Gambit (chapter 7)** appear in the Lichess study `cEDAMVBB`. **Grob, Borg, Barnes, Fred are MISSING** from the source PGN entirely (verified via case-insensitive grep across the full output — zero matches).

The user has two options when responding to the checkpoint:
1. Accept the subset that's actually in the study (Bongcloud + Halloween, plus any other strict-tier picks the user wants from the 46 chapters).
2. Instruct Task 3 to also include the 4 missing openings using their canonical defining positions derived manually (the executor can compute the keys directly using `deriveUserSideKey` semantics — they're trivial 1-3 ply positions).

## Self-Check

- File `frontend/scripts/curate-troll-openings.ts` exists: FOUND
- File `frontend/scripts/.cache/.gitignore` exists: FOUND
- Commit 7c7dd3b exists: FOUND
- `Total candidates:` line present in /tmp/troll-candidates.txt: FOUND
- Bongcloud key present in /tmp/troll-candidates.txt: FOUND

## Self-Check: PASSED (partial scope — Task 1 + Task 2 run, Task 3 pending checkpoint)
