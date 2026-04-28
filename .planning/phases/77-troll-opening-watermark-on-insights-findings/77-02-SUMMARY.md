---
phase: 77-troll-opening-watermark-on-insights-findings
plan: 02
subsystem: frontend-curation
tags: [troll-openings, curation-script, frontend, complete]
status: complete
requires:
  - chess.js (already installed @1.4.0)
provides:
  - frontend/scripts/curate-troll-openings.ts (curation pipeline)
  - frontend/src/data/trollOpenings.ts (curated data module)
affects:
  - frontend/src/lib/trollOpenings.ts (Plan 01 — consumes WHITE_TROLL_KEYS, BLACK_TROLL_KEYS)
tech-stack:
  added: []
  patterns:
    - "Node/TS curation script run via npx tsx — no permanent devDependency added per D-09 anti-pattern"
key-files:
  created:
    - frontend/scripts/curate-troll-openings.ts
    - frontend/scripts/.cache/.gitignore
    - frontend/src/data/trollOpenings.ts
  modified: []
decisions:
  - "Per-ply emission (both colors) rather than final-position-only — pushes ambiguity into the human review step per Pitfall 2"
  - "Cache directory .gitignore uses -f stage because root .gitignore already excludes .cache (line 59)"
  - "Curated set scope: full study extraction (10 white + 1 black) plus 4 manually-derived keys (Grob, Barnes, Borg, Fred) for openings absent from cEDAMVBB"
metrics:
  duration: ~4 min (resumed from checkpoint)
  completed: 2026-04-29
---

# Phase 77 Plan 02: Curate troll openings (COMPLETE)

One-liner: Reproducible Node/TS curation script + hand-pruned static `ReadonlySet<string>` data module covering 12 white-side and 3 black-side strict-Bongcloud-tier troll openings.

## Tasks Completed

| Task | Name                                                                        | Commit  | Files                                                                                |
| ---- | --------------------------------------------------------------------------- | ------- | ------------------------------------------------------------------------------------ |
| 1    | Create curation script that emits candidates to stdout                      | 7c7dd3b | frontend/scripts/curate-troll-openings.ts, frontend/scripts/.cache/.gitignore        |
| 2    | Surface candidate list to user for hand-pruning approval (D-01 checkpoint) | —       | /tmp/troll-candidates.txt (transient, surfaced inline)                               |
| 3    | Commit the hand-pruned data module                                          | 13a88db | frontend/src/data/trollOpenings.ts                                                   |

## Curation Run Output

- Cache: `frontend/scripts/.cache/cEDAMVBB.pgn` (19,693 bytes, fetched from `https://lichess.org/study/cEDAMVBB.pgn`, gitignored).
- Chapters parsed: 46 (one chapter has empty mainline and was skipped — chapter 36).
- Total candidates emitted: **542** → final pruned set: **15 keys** (12 white + 3 black).

## Curated Set

### WHITE_TROLL_KEYS (12 entries)

| Opening                       | SAN sequence                                          | Key                                                          | Source                |
| ----------------------------- | ----------------------------------------------------- | ------------------------------------------------------------ | --------------------- |
| Bongcloud Attack              | `1.e4 e5 2.Ke2`                                       | `8/8/8/8/4P3/8/PPPPKPPP/RNBQ1BNR`                            | study chapter 19 (canary) |
| Hammerschlag (Pork Chop)      | `1.f3 e5 2.Kf2`                                       | `8/8/8/8/8/5P2/PPPPPKPP/RNBQ1BNR`                            | study chapter 1       |
| Halloween Gambit              | `1.e4 e5 2.Nf3 Nc6 3.Nc3 Nf6 4.Nxe5`                  | `8/8/8/4N3/4P3/2N5/PPPP1PPP/R1BQKB1R`                        | study chapter 7       |
| Sodium Attack                 | `1.Na3`                                               | `8/8/8/8/8/N7/PPPPPPPP/R1BQKBNR`                             | study chapter 8       |
| Drunken Knight Opening        | `1.Nh3`                                               | `8/8/8/8/8/7N/PPPPPPPP/RNBQKB1R`                             | study chapter 9       |
| Crab Opening                  | `1.a4 e5 2.h4`                                        | `8/8/8/8/P6P/8/1PPPPPP1/RNBQKBNR`                            | study chapter 15      |
| Double Duck Formation         | `1.f4 f5 2.d4 d5`                                     | `8/8/8/8/3P1P2/8/PPP1P1PP/RNBQKBNR`                          | study chapter 16      |
| Creepy Crawly Formation       | `1.a3 e5 2.h3`                                        | `8/8/8/8/8/P6P/1PPPPPP1/RNBQKBNR`                            | study chapter 18      |
| Reagan's Attack               | `1.h4`                                                | `8/8/8/8/7P/8/PPPPPPP1/RNBQKBNR`                             | study chapter 22      |
| Napoleon Attack               | `1.e4 e5 2.Qf3`                                       | `8/8/8/8/4P3/5Q2/PPPP1PPP/RNB1KBNR`                          | study chapter 24      |
| Grob Attack                   | `1.g4`                                                | `8/8/8/8/6P1/8/PPPPPP1P/RNBQKBNR`                            | manual (not in study) |
| Barnes Opening                | `1.f3`                                                | `8/8/8/8/8/5P2/PPPPP1PP/RNBQKBNR`                            | manual (not in study) |

### BLACK_TROLL_KEYS (3 entries)

| Opening                       | SAN sequence                                          | Key                                                          | Source                |
| ----------------------------- | ----------------------------------------------------- | ------------------------------------------------------------ | --------------------- |
| Drunken Knight Variation      | `1.Nf3 f6 2.e4 Nh6`                                   | `rnbqkb1r/ppppp1pp/5p1n/8/8/8/8/8`                           | study chapter 31      |
| Borg Defence (Reversed Grob)  | `1.e4 g5`                                             | `rnbqkbnr/pppppp1p/8/6p1/8/8/8/8`                            | manual (not in study) |
| Fred Defence                  | `1.e4 f5`                                             | `rnbqkbnr/ppppp1pp/8/5p2/8/8/8/8`                            | manual (not in study) |

## Gap Vs Stated Minimum Target Set

User's stated minimum (Bongcloud, Grob, Borg, Halloween, Barnes, Fred) — only Bongcloud and Halloween are present in cEDAMVBB. Grob, Borg, Barnes, Fred were added manually with canonical defining-position keys derived directly from `deriveUserSideKey` semantics (1-3 ply positions, trivial). User approved option "Full study set + manual Grob/Borg/Barnes/Fred" at the checkpoint.

## Verification

- `cd frontend && npm test -- --run src/lib/trollOpenings.test.ts` → 10/10 pass
- `cd frontend && npm run knip` → exit 0 (data module flagged "unused" until Plan 03 imports `isTrollPosition`)
- `cd frontend && npx tsc --noEmit -p tsconfig.app.json` → exit 0
- Bongcloud canary key `8/8/8/8/4P3/8/PPPPKPPP/RNBQ1BNR` present in WHITE_TROLL_KEYS

## Self-Check

- File `frontend/scripts/curate-troll-openings.ts` exists: FOUND
- File `frontend/scripts/.cache/.gitignore` exists: FOUND
- File `frontend/src/data/trollOpenings.ts` exists: FOUND
- Commits 7c7dd3b, 02032c5, 13a88db exist: FOUND
- Inline `// <Opening Name> — after <SAN sequence>` comment per entry: FOUND

## Self-Check: PASSED
