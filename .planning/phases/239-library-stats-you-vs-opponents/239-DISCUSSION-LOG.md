# Phase 239: Library Stats You-vs-Opponents Redesign - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-12
**Phase:** 239-library-stats-you-vs-opponents
**Areas discussed:** Filters vs TC switch, Tactic IQR sequencing, Low-sample + What stands out

---

## Filters vs TC switch

| Option | Description | Selected |
|--------|-------------|----------|
| Keep filters, switch narrows | Switch offers only TCs allowed by the TC filter; ELO Ratings + Results Breakdown keep reading filters | ✓ |
| Keep filters minus TC | Hide only the TC filter group on this tab | |
| Hide filters like 238 | Stats tab ignores filters entirely | |

**User's choice:** Keep filters, switch narrows.

| Option | Description | Selected |
|--------|-------------|----------|
| List it, gate slot per section | Below-20 TC stays in the switch with "Not enough analyzed games yet (12 of 20)" | ✓ |
| Hide it from the switch | Only TCs with ≥20 analyzed games appear | |

**User's choice:** List it, gate slot per section.

| Option | Description | Selected |
|--------|-------------|----------|
| Separate per page | Own localStorage key; default = most analyzed games, ties to faster, prefer above-gate | ✓ |
| Shared across both pages | One preferred TC for Endgames and Library | |

**User's choice:** Separate per page.

---

## Tactic IQR sequencing

| Option | Description | Selected |
|--------|-------------|----------|
| Build band-less first, zones plan last | Phase closes only after zones land | |
| Ship band-less, zones in a later phase | Tables launch verdict-free | |
| Wait: benchmark first | Block phase on blitz finishing | |

**User's choice (free text):** "Use the Rapid typical ranges for Blitz and Bullet for now. We can update them later."

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, one basis for all | Recompute the 15 flaw-delta zones on the fully analyzed sample too | ✓ |
| No, tactics only | Keep old Lichess-eval basis for the 15 zones | |

| Option | Description | Selected |
|--------|-------------|----------|
| Let collapse verdict decide | Cohen's-d per axis, ≥30 cell floor, fallback to marginal/global | ✓ |
| Force pooled | One zone per family × orientation | |

Follow-ups:

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, same stopgap for all | Flaw-delta zones also map blitz/bullet → rapid | ✓ |
| Keep old pooled zones for blitz/bullet | Mixed bases by TC | |

| Option | Description | Selected |
|--------|-------------|----------|
| No, silent stopgap | Mapping documented in registry + report only | ✓ |
| Yes, one short line | "Typical range from rapid players for now." | |

---

## Low-sample + What stands out

| Option | Description | Selected |
|--------|-------------|----------|
| Fixed 40 flaws, check on dev data | Named constant for tactic cells and context-tag rows | ✓ |
| CI-width rule | No verdict when CI wider than the band | |
| Fixed 40, tactics only | Context tags always get a verdict | |

| Option | Description | Selected |
|--------|-------------|----------|
| Context tags only | Tactics stay in their own tables | ✓ |
| Tags + tactics, faded excluded | One ranked list across both | |

---

## Claude's Discretion

- Plan split; payload shape (one TC per request vs all TCs); removing combo / flaw_rate / top-6 backend paths; Elo used for zone lookup if the Elo axis doesn't collapse; gate-slot and empty-case copy; TC-switch state location.

## Deferred Ideas

- Refresh all zones with blitz/bullet full-analysis samples (replaces the rapid stopgap).
- Tactics in "What stands out".
