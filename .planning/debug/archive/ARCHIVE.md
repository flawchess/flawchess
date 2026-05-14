---
archived_on: 2026-05-14
reason: Recurring-baggage cleanup before v1.17 milestone close
---

# Debug session archive

These 9 sessions never reached `status: resolved` but stopped being relevant
because the affected feature was rebuilt, the bug stopped reproducing in
subsequent quick tasks / phases, or follow-up work (re-import, schema
change) closed the gap implicitly.

They were archived in bulk on 2026-05-14 so milestone audits stop flagging
them as "open". If any symptom recurs, create a new debug session rather
than reopening one of these — the original context is now several
milestones stale.

| File | Last status | Created |
|------|-------------|---------|
| all-data-missing-wrong-dev-user.md | diagnosed | 2026-03-14 |
| dashboard-no-data.md | awaiting_human_verify | 2026-03-14 |
| import-modal-second-platform.md | diagnosed | 2026-03-14 |
| lichess-import-truncated-191-of-1201.md | awaiting_human_verify | 2026-04-05 |
| match-side-always-mine.md | diagnosed | 2026-03-15 |
| phase-80-stats-incomplete.md | root_cause_found | 2026-05-03 |
| sort-order-always-zero.md | diagnosed | 2026-03-15 |
| stats-pages-empty-state.md | diagnosed | 2026-03-14 |
| suggestions-dedup-and-duplicates.md | diagnosed | 2026-03-15 |
