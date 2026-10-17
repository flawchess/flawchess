---
phase: 239-library-stats-you-vs-opponents
verified: 2026-10-13T05:00:00Z
status: passed
score: 13/13 must-haves verified
covered_files:
  - .planning/phases/239-library-stats-you-vs-opponents/239-01-PLAN.md
  - .planning/phases/239-library-stats-you-vs-opponents/239-01-SUMMARY.md
  - .planning/phases/239-library-stats-you-vs-opponents/239-02-PLAN.md
  - .planning/phases/239-library-stats-you-vs-opponents/239-02-SUMMARY.md
  - .planning/phases/239-library-stats-you-vs-opponents/239-03-PLAN.md
  - .planning/phases/239-library-stats-you-vs-opponents/239-03-SUMMARY.md
  - .planning/phases/239-library-stats-you-vs-opponents/239-04-PLAN.md
  - .planning/phases/239-library-stats-you-vs-opponents/239-04-SUMMARY.md
  - .planning/phases/239-library-stats-you-vs-opponents/239-05-PLAN.md
  - .planning/phases/239-library-stats-you-vs-opponents/239-05-SUMMARY.md
  - .planning/phases/239-library-stats-you-vs-opponents/239-06-PLAN.md
  - .planning/phases/239-library-stats-you-vs-opponents/239-06-SUMMARY.md
  - .planning/phases/239-library-stats-you-vs-opponents/239-07-PLAN.md
  - .planning/phases/239-library-stats-you-vs-opponents/239-07-SUMMARY.md
  - .planning/phases/239-library-stats-you-vs-opponents/239-08-PLAN.md
  - .planning/phases/239-library-stats-you-vs-opponents/239-08-SUMMARY.md
  - .planning/phases/239-library-stats-you-vs-opponents/239-09-PLAN.md
  - .planning/phases/239-library-stats-you-vs-opponents/239-09-SUMMARY.md
  - .planning/phases/239-library-stats-you-vs-opponents/239-10-PLAN.md
  - .planning/phases/239-library-stats-you-vs-opponents/239-10-SUMMARY.md
  - app/repositories/library_repository.py
  - app/routers/library.py
  - app/schemas/library.py
  - app/services/flaw_delta_zones.py
  - app/services/library_service.py
  - app/services/tactic_delta_zones.py
  - frontend/src/components/library/stats/ContextTagCards.tsx
  - frontend/src/components/library/stats/FlawTiles.tsx
  - frontend/src/components/library/stats/GapBar.tsx
  - frontend/src/components/library/stats/GapPopover.tsx
  - frontend/src/components/library/stats/GapRow.tsx
  - frontend/src/components/library/stats/LibraryStatsSections.tsx
  - frontend/src/components/library/stats/LibraryTcSwitch.tsx
  - frontend/src/components/library/stats/TacticTables.tsx
  - frontend/src/components/library/stats/WhatStandsOut.tsx
  - frontend/src/hooks/tcSelectionStore.ts
  - frontend/src/hooks/useLibraryStatsTc.ts
  - frontend/src/lib/flawComparisonMeta.ts
  - frontend/src/lib/gapBar.ts
  - frontend/src/lib/tacticComparisonMeta.ts
  - frontend/src/pages/GlobalStats.tsx
  - scripts/benchmarks/chapter5.py
covered_digest: "v3:sha256:14723000b12a6dc349d128b370b205e6c45ef9da59b241a145c55ad783d2f949"
behavior_unverified: 0
overrides_applied: 1
overrides:
  - must_have: "D-07: one basis for all zones; the 12 flaw bands are recomputed on the fully analyzed benchmark sample"
    reason: "Owner accept-with-edits at the 239-06 checkpoint: the 12 flaw bands keep their live values (older whole-cohort basis) because the full-analysis lane's 100-games-per-TC cap makes the proposed 1.5x to 3.5x widening mostly sampling noise (noise-only IQR 70% to 142% of observed). The 9 viable tactic bands use the section 5 full-analysis basis. Recorded under ## Accepted in 239-ZONE-PROPOSAL.md, as a dated note under D-07 in 239-CONTEXT.md, and in reports/benchmark/benchmarks-latest.md section 5 (flaw rows read 'not adopted, the app keeps the live band')."
    accepted_by: "owner (Adrian Imfeld)"
    accepted_at: "2026-10-13"
---

# Phase 239: Library Stats You-vs-Opponents Redesign Verification Report

**Phase Goal:** Make the Library Stats tab (below the Flaw Stats tiles and the Flaws Timeline) readable for non-statisticians: one zero-centred gap bar per you-vs-opponent metric with the gap in words, a Search popover carrying the rates and statistics, a synced TC switch per section, and real benchmark typical ranges for tactic motifs (sketch 010 round 5, SEED-198 decisions 1-12).
**Verified:** 2026-10-13
**Status:** passed
**Re-verification:** No, initial verification

## Goal Achievement

Verified against the code, not the SUMMARYs. Backend and frontend source files were read directly; targeted suites were re-run on this tree (backend 198 passed across the flaw/tactic comparison services, both zone registries, chapter5 SQL shape test, library router tests; frontend 167 passed across `components/library/stats`, `gapBar`, `useLibraryStatsTc`). One mutation check was run by hand (removing the `lowSample: false` override in `FlawTiles.tsx` makes the WR-02 test fail; file restored, working tree clean).

### CONTEXT Decision Coverage (D-00a .. D-13)

| #   | Decision | Status | Evidence |
| --- | -------- | ------ | -------- |
| D-00a | One gap bar: centre 0 tick, off-centre grey IQR band, better to the right, linear in band then `1-e^-x` saturation, no halves/whiskers | VERIFIED | `frontend/src/lib/gapBar.ts` `gapPosition` (linear to `GAP_BAND_HALF_POS`, then `1 - Math.exp(-(a - s)/width)`, sign flip so negative gap is right), `bandRange` draws band at its true (asymmetric) offsets; `GapBar.tsx` renders track, band, zero tick, dot only. `gapBar.test.ts` + `GapBar.test.tsx` green. |
| D-00b | Gap in words ("1.7 fewer", "0.42 more", "same"); typical white, only better/worse coloured; blue dot for typical | VERIFIED | `gapWords`, `formatGapNumber`, `gapVerdictColor` (green/red/`GAUGE_NEUTRAL`); `GapBar` colours the words only when `verdict` is better/worse. |
| D-00c | Only the gap on the page; lucide Search popover on the shared shell: definition + "Fewer is better", You/Opponents, typical range + verdict, basis, greyed counts/CI/p below a separator | VERIFIED | `components/ui/metric-info-popover.tsx` (Search icon, hover+tap); `GapPopover.tsx` body in that order with `<hr>` and italic muted footer (`footerText`: counts, gap 95% CI, p-value). Tiles keep their "Opponents x.xx" line (`FlawTiles.tsx`). |
| D-00d | "flaws/blunders/mistakes", never "events" | VERIFIED | grep of `components/library/stats`, `gapBar.ts`, both meta files: "events" appears only in code comments and identifiers (`youEvents`, `you_events`); `noun` copy per metric; tests assert `/\bevents?\b/i` absent. |
| D-00e | Tiles: Blunders and Mistakes only; Inaccuracies tile, Severity card, "Flaw rate" retire | VERIFIED | `FlawTiles.tsx` `TILE_METRICS = ['blunder','mistake']`; `FlawStatsPanel/FlawStatsBand` deleted; grep shows no `flaw_rate` anywhere in app/schemas/frontend. |
| D-00f | Combos removed; four cards Clock / Game phase / Opponent errors / Lost advantages; tag names unchanged; one-line hints | VERIFIED | `CONTEXT_TAG_CARDS` (4 cards, 10 tags, hints in `FLAW_GAP_META`); no combo code left in `library_repository.py`, `library_service.py`, `schemas/library.py`, `chapter5.py` (only a docstring note that they were dropped). `FLAW_DELTA_METRICS` is exactly 12. |
| D-00g | "What stands out": top 3 strengths / weaknesses by band-width distance outside the band, hint, coloured gap, popover, one "Typical: ..." line | VERIFIED | `WhatStandsOut.tsx` + `pickStandouts` (`TOP_STANDOUTS = 3`, `standoutDistance` in band widths, sorted descending), `Typical:` line, empty copy "Nothing outside the typical range."; test file green. |
| D-00h | Three tactic tables in `TACTIC_GROUPS` order; Motif (+N of your flaws) / Missed / Allowed; per-100-games gap bars; fixed column widths; phones stack; zero-count motifs under table; "More tactics" and top-6 retire | VERIFIED | `TacticTables.tsx` (`TACTIC_GROUPS.map`, `md:grid-cols-[24fr_38fr_38fr]`, header hidden below md and per-cell side label shown, "No flaws yet: ..." paragraph); backend `PER_100_GAMES`, all 19 families x 2 sides interleaved in fixed order, no ranking/top-N (grep clean). Old `TacticComparisonGrid` deleted. |
| D-00i | Advanced collapsed by default with chevron and `EXPAND_HINT`, hidden once open | VERIFIED | `CollapsibleTacticGroup` (controlled accordion, starts closed, `AccordionTrigger band`, `ExpandHint` exported from `ShellyQuote.tsx` hiding via `group-aria-expanded`). |
| D-00j | Card header bands throughout; Fredoka only for h2 titles | VERIFIED | `CardHeader` bands on all cards; h2 uses `font-brand` (also applied to ELO Ratings / Results Breakdown titles). The tile rate number uses `font-brand`, which matches the owner-approved sketch (`.tile .big` is Fredoka in `index.html`); not a defect. |
| D-00k | Flaws Timeline visuals, ELO Ratings, Results Breakdown, coverage badge unchanged | VERIFIED | `GlobalStats.tsx` diff touches only the Flaw Stats block (+ two h2 font classes); `FlawTrendChart` and `EvalCoverageBadge` reused; timeline follows the selected TC via `trend_by_tc`. |
| D-01 | Sidebar filters stay; all gap metrics over filtered analyzed games of the selected TC | VERIFIED | `LibraryStatsSections` receives the page `filters`; repository `count_analyzed_by_tc` / fetches go through `_filtered_games_base` (apply_game_filters). Service tests cover filter + NULL-bucket + tactic_families narrowing. |
| D-02 | Synced TC switch offers only TCs allowed by the filter with >=1 analyzed game; ELO/Results keep reading sidebar filters | VERIFIED | Payload `tcs[]` built from `count_analyzed_by_tc` (positive counts only, `LIBRARY_TC_ORDER`); `LibraryTcSwitch` x3 bound to one store; no `/api` refetch on switch (UAT step 2 + `LibraryStatsSections.test.tsx`). |
| D-03 | Below-gate TC stays in switch; tiles show rates; sections show "Not enough analyzed games yet (N of 20)" | VERIFIED | `below_gate` flag, bullets always computed; `GapGateSlot`; `FlawTiles` shows rates + slot; vs-opponents and tactics sections replace content with the slot. Live step 6 unreachable (recorded); covered by component tests, which pass. |
| D-04 | Default TC = most analyzed games, ties to faster TC, prefers above-gate | VERIFIED | `pickDefaultLibraryTc` -> `pickMostPopulatedTc(tcs, !below_gate, analyzed_n)`; `useLibraryStatsTc.test.ts` green. |
| D-05 | Selected TC in localStorage under a key separate from Endgame; try/catch; fallback to D-04 when not offered | VERIFIED | `LIBRARY_STATS_TC_STORAGE_KEY = 'library_stats_tc'`; `tcSelectionStore.ts` validates stored value against `TIME_CONTROL_ORDER`, try/catch on read/write, ignored when not offered. UAT step 2 confirmed reload restore. |
| D-06 | `/benchmarks` section 5 extended with per-family Missed/Allowed paired-delta zones + viability table, same methodology | VERIFIED | `scripts/benchmarks/chapter5.py` rebuilt on the full-analysis lane (12 flaw + 38 tactic keys, 30-contributor cell floor, collapse verdict per axis, `zone_viable`, noise-only IQR); `tests/scripts/test_chapter5_sql.py` pins it (green); SKILL.md section 5 and `reports/benchmark/benchmarks-latest.md` section 5 updated. 239-06 recorded the diff gate green (4 passed); not re-run here (needs the benchmark DB). |
| D-07 | One basis for all zones; combos and `flaw_rate` dropped from registry | VERIFIED (override) | Combos/`flaw_rate` dropped. The "one basis" part was overridden by the owner at the 239-06 checkpoint for the 12 flaw bands (see frontmatter override). Registry values equal `## Accepted` table exactly (checked line by line: 12 flaw bands unchanged, 9 tactic bands); the override is recorded in all three places (ZONE-PROPOSAL, CONTEXT D-07 dated note, benchmark report rows 'not adopted'). Review finding WR-04 fixed in d43595efc. |
| D-08 | Don't wait for blitz; blitz and bullet use rapid zones | VERIFIED | `ZONE_TC_FOR = {bullet: rapid, blitz: rapid, rapid: rapid, classical: classical}` shared by both registries. |
| D-09 | Stopgap silent in UI; mapping documented in registry module and benchmark report | VERIFIED | No stopgap wording in `GapPopover`/components; documented in both registry docstrings and report lines 699-700, 721. |
| D-10 | Collapse verdict decides granularity per axis; thin cells fall back | VERIFIED | No metric reached keep-separate on TC or ELO, so one pooled band per metric shared by rapid and classical, no Elo keying; owner accepted this as proposed (ZONE-PROPOSAL `## Accepted`). Registry stays keyed metric -> zone TC so per-TC values remain possible. |
| D-11 | Tactic zone registry next to flaw registry wired into `get_tactic_comparison` (`zone_lo/zone_hi/has_zone`); `has_zone=false` renders band-less | VERIFIED | `app/services/tactic_delta_zones.py` (38 entries, 9 non-None); `_build_tactic_bullet` embeds band or `0.0/0.0/has_zone=False`; `bandRange` returns null and `effectiveVerdict` null for zoneless cells; `GapPopover.rangeLine` omits the range line. |
| D-12 | `LOW_SAMPLE_MIN_FLAWS = 40` you+opponent flaws, applied to tactic cells and context-tag rows: faded, no verdict, "Too few flaws to call it" | VERIFIED | Constant in `library_service.py`; `GapRow` fades via `UNRELIABLE_OPACITY`, tactic cells fade when they have flaws; `effectiveVerdict` null under low sample; popover copy `COPY_TOO_FEW`. Tiles deliberately exempt (WR-02 fix 954ba3c72, mutation re-confirmed here). Sanity check vs CI width recorded in ZONE-PROPOSAL (combined median ratio 1.00, constant kept). |
| D-13 | "What stands out" ranks context tags only, faded rows never qualify | VERIFIED | `contextRows` iterates `CONTEXT_TAG_METRICS` (excludes blunder/mistake, no tactics); `pickStandouts` drops low-sample, zoneless, gap-less rows. |

### Roadmap Success Criteria

| # | Criterion | Status | Evidence |
| - | --------- | ------ | -------- |
| 1 | One gap bar for every you-vs-opponent metric | VERIFIED | Tiles, 10 context rows, standouts and all tactic cells render `GapBar`; `MiniBulletChart` no longer used by the Library (still used by Openings, intentionally kept). |
| 2 | Only the gap on the page; Search popover | VERIFIED | See D-00c. |
| 3 | Tiles Blunders/Mistakes with Opponents line and gap bar | VERIFIED | `FlawTiles.tsx`. |
| 4 | Context tags: four cards + What stands out | VERIFIED | `ContextTagCards.tsx`, `WhatStandsOut.tsx`. |
| 5 | Three tactic tables, Advanced collapsed, zero-count motifs listed, top-6 retired, low-sample faded | VERIFIED | `TacticTables.tsx`. |
| 6 | Synced TC switch in every section | VERIFIED | `LibraryTcSwitch` in all three section headers on one store. |
| 7 | Benchmark tactic IQRs: §5 extension + registry wired into `get_tactic_comparison` | VERIFIED | `chapter5.py`, `tactic_delta_zones.py`, `library_service.py`. The "gated on blitz sample" clause was superseded by CONTEXT D-08 (rapid zones as stopgap). |
| G | Guardrails: Timeline/ELO/Results/badge unchanged; "flaws" wording; check Openings before deleting `MiniBulletChart` / `FlawBulletPopover` | VERIFIED | `MiniBulletChart` retained and used by 8 Openings files; `FlawBulletPopover` deleted with no remaining importers; `SeverityGlyphIcon` only had a doc-comment reference (comment updated). UAT desktop + 375px recorded in 239-VALIDATION.md. |

**Score:** 13/13 decision groups verified (D-00a..D-00k grouped as 11 items + D-01..D-13 all accounted for; D-07 carried as PASSED (override)). 0 behavior-unverified, 0 gaps.

### Required Artifacts / Key Links

| Artifact | Status | Details |
| -------- | ------ | ------- |
| `app/services/flaw_delta_zones.py` | VERIFIED | 12 metrics, `ZONE_TC_FOR`, values == accepted table |
| `app/services/tactic_delta_zones.py` | VERIFIED | 38 entries, 9 bands, `tactic_delta_zone()` |
| `app/services/library_service.py` | VERIFIED | per-TC `tcs[]`, `LOW_SAMPLE_MIN_FLAWS`, gates, per-100-games |
| `app/repositories/library_repository.py` | VERIFIED | `count_analyzed_by_tc` (ply_count gate WR-03, `require_tactic_blobs` WR-01), combo/top-6 paths removed |
| `scripts/benchmarks/chapter5.py`, `.claude/skills/benchmarks/SKILL.md`, `reports/benchmark/benchmarks-latest.md` | VERIFIED | §5 rebuilt; report/registry agree on owner edit |
| `frontend/src/lib/gapBar.ts`, `components/library/stats/*` | VERIFIED | substantive, wired from `GlobalStats.tsx` through `LibraryStatsSections` |
| `frontend/src/hooks/tcSelectionStore.ts`, `useLibraryStatsTc.ts` | VERIFIED | shared factory, separate key |

| From | To | Via | Status |
| ---- | -- | --- | ------ |
| `GlobalStats.tsx` | `LibraryStatsSections` | import + render with sidebar `filters` | WIRED |
| `useLibraryFlawComparison` / `useTacticComparison` | sections | one query per payload, TC is a client-side pick (not in query key) | WIRED |
| `library_service.get_tactic_comparison` | `tactic_delta_zone` | `_build_tactic_bullet` | WIRED |
| `library_service._build_flaw_bullet` | `flaw_delta_zone` | per-bullet band | WIRED |
| `GapBar`/`GapPopover` | `MetricInfoPopover` shell | Search trigger | WIRED |

### Data-Flow Trace (Level 4)

| Artifact | Data | Source | Real data | Status |
| -------- | ---- | ------ | --------- | ------ |
| FlawTiles / ContextTagCards / WhatStandsOut | `tcStats.bullets` | `fetch_flaw_comparison` SQL aggregation, user-scoped | Yes (live smoke 239-09: blitz 1,000 / rapid 1,841 analyzed, 12 flaw bullets per TC) | FLOWING |
| TacticTables | `tcStats.bullets` | `fetch_tactic_comparison` x2 orientations + registry bands | Yes (38 bullets per TC, 9 `has_zone`) | FLOWING |
| Flaws Timeline | `trend_by_tc` | `get_flaw_stats` | Yes | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Backend comparison/zone/router suites | `uv run pytest` on 7 files | 198 passed | PASS |
| Frontend Library Stats suites | `npx vitest run src/components/library/stats src/lib/__tests__/gapBar.test.ts src/hooks/__tests__/useLibraryStatsTc.test.ts` | 167 passed | PASS |
| WR-02 mutation (remove `lowSample: false`) | vitest `FlawTiles.test.tsx` | 1 failed as expected; file restored | PASS (test is load-bearing) |

### Probe Execution

None declared by the phase; Step 7c not applicable.

### Requirements Coverage

No REQUIREMENTS.md exists for this milestone; the coverage contract is CONTEXT D-00a..D-13, accounted for in full above. Nothing orphaned.

### Anti-Patterns Found

No `TBD`/`FIXME`/`XXX` markers or stub returns in the reviewed phase files; empty-array/null matches are legitimate initial or empty-state values that real payloads overwrite.

### Open Review Items (non-blocking, none are must-have failures)

| Item | Severity | Note |
| ---- | -------- | ---- |
| IN-02 "N of your flaws" can double-count a flaw carrying a tactic in both orientations (`TacticTables.tsx`) | Warning (advisory) | The label may overstate by the number of such flaws; the gap bars and popovers are unaffected. Recommend relabel or a backend per-family flaw count as a follow-up. |
| IN-01 pinned default TC can be reset by a still-empty section | Info | Narrow; can flip the default TC without a click only when the user has no stored choice. |
| IN-04 `user_moves` floor/ceil parity | Info | Pre-existing, identical in app and benchmark so zones stay self-consistent; verify separately. |
| IN-05, IN-06 | Info | Viability query sparse-cell exclusion; type-only import cycle. |

These were dispositioned open by the owner in `239-REVIEW-DISPOSITION.md`; WR-01..WR-04 and IN-03 are fixed with evidence in code and tests (verified above for WR-01, WR-02, WR-03 and WR-04).

### Human Verification Required

None. Browser UAT (desktop and 375px) was recorded as passed in 239-VALIDATION.md; step 6 (below-gate slot) was unreachable live and is covered by passing component tests, per the orchestrator's note.

### Gaps Summary

No gaps. Every CONTEXT decision is honored in the code, or (D-07, flaw bands) deliberately overridden by a recorded owner decision whose registry values, CONTEXT note and benchmark report all agree. Gates reported green on this tree were corroborated by targeted re-runs.

---

_Verified: 2026-10-13_
_Verifier: Claude (gsd-verifier)_
