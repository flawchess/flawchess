---
phase: quick
plan: 260327-oxo
type: execute
wave: 1
depends_on: []
files_modified:
  - .planning/ROADMAP.md
  - .planning/STATE.md
autonomous: true
must_haves:
  truths:
    - "Phase 32 is marked complete in all locations"
    - "Phase 30 is renumbered to Phase 33 throughout ROADMAP.md"
    - "v1.5 milestone scope reflects actual completed/remaining phases"
    - "STATE.md reflects current reality (phase progress, position, counters)"
    - "Stale sub-phase details (27.1, 28.1) are cleaned up if completed"
    - "Progress table is accurate for all phases"
  artifacts:
    - path: ".planning/ROADMAP.md"
      provides: "Updated roadmap with accurate phase numbering and status"
    - path: ".planning/STATE.md"
      provides: "Updated project state reflecting current position"
  key_links: []
---

<objective>
Finalize Phase 32 as complete and clean up the ROADMAP.md and STATE.md to reflect current project reality.

Purpose: The roadmap and state files have accumulated drift from rapid phase execution. Phase 32 is done but state still says "Executing Phase 32". Phase 30 (Homepage/SEO) was skipped during v1.5 and should be renumbered to 33 since it is next. Sub-phases 27.1 and 28.1 need cleanup. Milestone v1.5 scope needs accuracy.
Output: Updated ROADMAP.md and STATE.md
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/ROADMAP.md
@.planning/STATE.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Update ROADMAP.md — renumber Phase 30 to 33, fix milestone scope, clean up progress table</name>
  <files>.planning/ROADMAP.md</files>
  <action>
Make the following changes to ROADMAP.md:

1. **Renumber Phase 30 to Phase 33**: Everywhere "Phase 30" appears (milestone scope line, phase list under v1.4, phase details section, progress table), change to "Phase 33". Update the phase directory reference if needed. The phase directory on disk stays as-is (30-homepage-readme-seo-update) — only the roadmap numbering changes.

2. **Update v1.5 milestone scope line** (line 10): Change from "Phases 26-30" to "Phases 26-33". This now includes 26, 27, 27.1, 28, 28.1, 29, 31, 32, and 33 (renumbered from 30).

3. **Mark completed sub-phases in the phase list under v1.4 section**:
   - Phase 27.1 (Optimize game_positions column types) — this was completed via quick tasks (260326-jo8 and 260326-k94 added piece_count, backrank_sparse, mixedness columns). Mark it as complete with date 2026-03-26. In the phase details section, update its status to reflect completion.
   - Phase 28.1 (Import lichess analysis metrics) — already marked complete in progress table. Ensure phase details are consistent.
   - Phase 31 — already marked complete. Ensure consistency.

4. **Fix Phase 28 progress table entry**: Shows "2/3" plans but the phase is marked "Complete". Plan 28-03 (admin re-import script) was never executed. Either mark it as 2/3 with a note that 28-03 was deprioritized, or mark it honestly. Since the phase is listed as "Complete" with date 2026-03-25, keep "Complete" but change plans to "3/3" only if 28-03 was actually done. Looking at the plan list, 28-03 has "[ ]" (unchecked). Change the progress table to "2/3" and status to "Complete (28-03 deferred)" to be accurate.

5. **Move Phase 31 and 32 details out of the Backlog section**: Phase 31 details currently appear under "## Backlog" heading. Move Phase 31 details to be under "## Phase Details" alongside other v1.5 phases (before the backlog). Phase 32 details are already after 31, move them too.

6. **Clean up Phase 27.1 details**: Update from placeholder "Goal: [Urgent work - to be planned]" to reflect what was actually done: "Goal: Optimize game_positions with piece_count, backrank_sparse, and mixedness columns for endgame classification". Mark plans as complete. Remove TBD placeholders.

7. **Update progress table**:
   - Phase 27.1: Add row — "27.1. Optimize game_positions columns | v1.5 | N/A | Complete | 2026-03-26" (done via quick tasks, no formal plans)
   - Phase 28: Change from "2/3" to "2/3" with status "Complete (03 deferred)"
   - Phase 30 row: Renumber to 33
   - Phase 31: Add row if missing — "31. Endgame classification redesign | v1.5 | 2/2 | Complete | 2026-03-26"
   - Ensure Phase 32 row shows correct completion date (2026-03-27 based on recent commits)

8. **Renumber Phase 33 in phase details**: Update the "### Phase 30:" heading to "### Phase 33:" and update depends_on from "Phase 29" to "Phase 32" (since it follows after all the endgame work).
  </action>
  <verify>
    <automated>grep -c "Phase 33" .planning/ROADMAP.md | grep -q "[1-9]" && grep -c "Phase 30" .planning/ROADMAP.md | grep -q "^0$" && echo "PASS: Phase 30 fully renumbered to 33" || echo "FAIL: Phase 30 references remain or Phase 33 missing"</automated>
  </verify>
  <done>Phase 30 is renumbered to 33 everywhere. Progress table is accurate. Sub-phase details are cleaned up. Phase 31/32 details are in the right section. v1.5 scope line is correct.</done>
</task>

<task type="auto">
  <name>Task 2: Update STATE.md — current position, progress counters, phase table, milestone</name>
  <files>.planning/STATE.md</files>
  <action>
Make the following changes to STATE.md:

1. **Frontmatter updates**:
   - `milestone`: Change from "v1.4" to "v1.5" (that is the active milestone)
   - `milestone_name`: Change from "Improvements" to "Game Statistics and Endgame Analysis"
   - `status`: Change from "Executing Phase 32" to "Phase 32 Complete — Planning Phase 33"
   - `last_updated`: Set to current date/time
   - `last_activity`: Set to "2026-03-27"
   - `progress.completed_phases`: Update count to reflect all completed phases (add 31, 32, 27.1 = +3 from current 6, so 9)
   - `progress.total_phases`: Update to reflect actual total (was 11, now includes 31, 32 = 13)
   - `progress.completed_plans`: Recount — phases 26(2) + 27(2) + 27.1(0 formal) + 28(2) + 28.1(1) + 29(3) + 31(2) + 32(3) = 15 plans in v1.5 completed. Plus earlier milestones already in the count. Current says 14 completed of 16 total. Add 31(2) + 32(3) + 27.1(0) = 5 more completed. So 14+5=19 completed. Total plans: 16+5=21. But also 28-03 is deferred, so total should subtract 0 (it still exists). Set completed_plans to 19, total_plans to 21.
   - Actually, let me recalculate from scratch for v1.4+v1.5 only (earlier milestones were not tracked in these counters). The frontmatter says total_phases: 11, completed_phases: 6. This seems to only track post-v1.3 phases. Phases 24-32 + 27.1 + 28.1 = 11 phases total. Completed: 24, 26, 27, 27.1, 28, 28.1, 29, 31, 32 = 9. Not started: 25, 33. So total_phases: 11, completed_phases: 9. For plans: 24(2)+26(2)+27(2)+28(2)+28.1(1)+29(3)+31(2)+32(3)=17 completed. 28 has 1 deferred (28-03). Total plans created: 17+1(deferred)=18. So completed_plans: 17, total_plans: 18.

2. **Current Position**: Change to "Phase: 33 (homepage-readme-seo-update) — NOT STARTED" or "Between phases — Phase 32 complete, Phase 33 next"

3. **Current focus**: Keep "Game Statistics & Endgame Analysis (v1.5)" — still accurate since Phase 33 is the last v1.5 phase.

4. **Phase Progress table**: Replace the stale placeholder phases (26-29 showing "Not started") with accurate status:
   - Remove the old entries for phases 26, 27, 28, 29 that say "Not started" (lines 32-35)
   - The real progress is tracked in the Progress table in ROADMAP.md, so this section in STATE.md should either mirror reality or just reference ROADMAP.md
   - Replace with: Phase 33 (Homepage, README & SEO) — Not started. Only show upcoming/active phases, not completed ones.

5. **Roadmap Evolution section**: Add entry for Phase 33 renumbering:
   - "Phase 30 renumbered to Phase 33: Homepage, README & SEO Update (was skipped during v1.5 execution)"

6. **Last activity line**: Update to "2026-03-27 - Completed Phase 32: Endgame Performance Charts. Roadmap cleanup."
  </action>
  <verify>
    <automated>grep "milestone: v1.5" .planning/STATE.md && grep "completed_phases: 9" .planning/STATE.md && grep "Phase 33" .planning/STATE.md && echo "PASS" || echo "FAIL"</automated>
  </verify>
  <done>STATE.md reflects: v1.5 milestone active, Phase 32 complete, Phase 33 is next, progress counters are accurate, phase table shows only upcoming work.</done>
</task>

</tasks>

<verification>
- `grep "Phase 30" .planning/ROADMAP.md` returns zero matches (fully renumbered)
- `grep "Phase 33" .planning/ROADMAP.md` returns multiple matches
- `grep "milestone: v1.5" .planning/STATE.md` confirms milestone updated
- `grep "completed_phases: 9" .planning/STATE.md` confirms count
- Phase 31 and 32 details appear before the Backlog section in ROADMAP.md
- No "Not started" entries in STATE.md phase table for phases that are actually complete
</verification>

<success_criteria>
1. ROADMAP.md has Phase 33 (renumbered from 30) with no remaining "Phase 30" references
2. Progress table in ROADMAP.md is fully accurate for all phases
3. STATE.md frontmatter reflects v1.5 milestone with correct counters
4. STATE.md current position shows Phase 33 as next
5. Sub-phase 27.1 details are updated from placeholder to actual completed work
6. Phase 31/32 details are in the Phase Details section, not under Backlog
</success_criteria>

<output>
No summary file needed for quick tasks.
</output>
