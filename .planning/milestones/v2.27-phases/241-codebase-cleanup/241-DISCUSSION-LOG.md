# Phase 241: Codebase Cleanup (naming + comments) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-16
**Phase:** 241-codebase-cleanup
**Areas discussed:** Glossary reach, Rename pruning, Tag-strip reach + style calls
(Execution shape offered, not selected → Claude's discretion)

---

## Glossary reach

| Option | Description | Selected |
|--------|-------------|----------|
| Prose + new code | Canonical governs comments/docstrings/future code; identifiers change only via inventory | ✓ |
| Also drive renames | Every "retire" term becomes a rename (~30+ extra) | |
| Renames for small blast only | Local/module ≤3 files only | |

| Option | Description | Selected |
|--------|-------------|----------|
| Accept suggestions | Adopt INVENTORY §2 "Suggested canonical" wholesale, minus overrides | ✓ |
| Review row by row | ~20 rounds | |
| Only contentious rows | Drop "document only" rows from §3.3 | |

Row #2: `player` ✓ / `you` / `user`. Row #16: `puzzle` ✓ / `drill`.

| Option | Description | Selected |
|--------|-------------|----------|
| Seed candidates only (#43/#59/#60/#79 merges) | Consolidation is code change | ✓ |
| Merge in this phase | Breaks pure-refactor check | |

| Option | Description | Selected |
|--------|-------------|----------|
| tour in prose, walkthrough near its identifiers | rename becomes seed | |
| Add the rename | walkthrough → tour as an extra cross-layer rename | ✓ |

**Notes:** Claude checked blast radius after the choice: ~22 frontend files; `review_walkthrough` wire field and `train-bot-walkthrough` testids stay.

---

## Rename pruning

| Question | Options | Selected |
|----------|---------|----------|
| Which renames ship | All 86 / All minus high-churn / Strike specific rows | All 86 |
| M-verdict names | Verifier's name / Review the 19 | Verifier's name |
| Follow-ons | "should follow" yes, "optional" no / Include all / None | "should follow" yes, "optional" no |
| 772 comment fixes | Apply all, re-verify each / Apply verbatim | Apply all, re-verify each |

---

## Tag-strip reach + style calls

| Question | Options | Selected |
|----------|---------|----------|
| Tree reach | app+frontend/src+tests / +scripts / +scripts,docs,bin | app + frontend/src + tests |
| Tags in test titles/names | Titles and names / Titles only / Comments only | Titles and names |
| Open-seed `(see SEED-NNN)` pointers | Approve / Strip all | Approve |
| Wire-mirroring internal names | Never rename this phase / Rename with explicit alias | Never rename this phase |
| Tags in runtime strings | Leave / Strip with justification | Leave |
| Tagged identifiers missed by inventory | Rename if local/module / List only | Rename if local/module |

---

## Claude's Discretion

- Plan granularity and wave layout (within ROADMAP plan shape, keep plans small)
- Mechanical diff-check method
- Commit message shapes per STYLE-GUIDE §4.5

## Deferred Ideas

- Helper/constant consolidation (#43, #59, #60, #79) → seed candidates
- Glossary-driven renames beyond the inventory → possible later cleanup phase
- scripts/, docs/, bin/ comment pass → later
- INVENTORY §7 seeds and suspected bugs → owner decides separately
