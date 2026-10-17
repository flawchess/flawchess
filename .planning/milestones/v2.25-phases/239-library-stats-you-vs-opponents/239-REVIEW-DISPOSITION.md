---
phase: 239-library-stats-you-vs-opponents
review: 239-REVIEW.md
recorded: 2026-10-13
critical: 0
warning: 4
info: 6
---

# Phase 239 — Code Review Disposition

| Finding | Severity | Disposition | Evidence |
|---------|----------|-------------|----------|
| WR-01 | warning | fixed | b16affa67: tactic population requires `blobs_completed_at`; test `test_blob_pending_games_excluded_from_tactic_population` (mutation-proven at both anchor and count) |
| WR-02 | warning | fixed | 954ba3c72: Blunders/Mistakes tiles ignore `low_sample` (D-12 scope); FlawTiles test (mutation-proven) |
| WR-03 | warning | fixed | a28a9b491: `count_analyzed_by_tc` shares the ply_count gate; `test_null_or_zero_ply_count_not_counted` (mutation-proven) |
| WR-04 | warning | fixed | d43595efc: benchmarks-latest.md and CONTEXT D-07 record the owner keeping the live flaw bands |
| IN-01 | info | open | Empty section can reset the shared pinned default TC; not in owner-approved fix scope |
| IN-02 | info | open | "N of your flaws" double-counts a flaw tagged in both orientations; not in fix scope |
| IN-03 | info | fixed | 4947ce770: GapBar aria-label "same flaws as your opponents" |
| IN-04 | info | open | user_moves floor/ceil parity predates the phase and matches app + benchmark; verify separately |
| IN-05 | info | open | Viability query skips the sparse-cell exclusion; not in fix scope |
| IN-06 | info | open | Type-only import cycle types/library.ts ↔ tacticComparisonMeta.ts; not in fix scope |
