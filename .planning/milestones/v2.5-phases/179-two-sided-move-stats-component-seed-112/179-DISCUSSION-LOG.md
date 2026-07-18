# Phase 179: Two-sided Move Stats component (SEED-112) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-18
**Phase:** 179-two-sided-move-stats-component-seed-112
**Areas discussed:** Accuracy fallback, ACPL visibility, Row/icon rendering, Mobile/empty state

---

## Accuracy fallback (canonical NULL behavior)

| Option | Description | Selected |
|--------|-------------|----------|
| Fall back to `*_imported` | Show platform-reported value when canonical is NULL | |
| Canonical only, else "—" | Show a number only when we computed it uniformly; else a dash | ✓ |
| Canonical only + analyze affordance | "—" + surface the on-demand analyze pill to fill it | |

**User's choice:** Canonical only, else "—"
**Notes:** Preserves Phase 178's "one uniform metric" guarantee; no methodology mixing on the surface. Accepted that many cards show "—" until the prod backfill runs. (Unanalyzed games still show the analyze pill per the separate empty-state decision.)

---

## ACPL visibility

| Option | Description | Selected |
|--------|-------------|----------|
| Accuracy % only | ACPL stays a backend/validation signal, not surfaced | ✓ |
| Accuracy % + ACPL subtext | Small ACPL under/behind each accuracy cell | |

**User's choice:** Accuracy % only
**Notes:** Keeps the tight ~225px desktop card uncluttered; matches chess.com's headline.

---

## Row / icon rendering

| Option | Description | Selected |
|--------|-------------|----------|
| All 7 rows always, 0 muted | Every category row always present; zero shown muted | ✓ |
| Hide fully-empty rows | Drop a row only when both players have 0 | |

**User's choice:** All 7 rows always, 0 shown muted
**Notes:** Stable, scannable layout across cards. Best/Good get new circular badge icons (design in plan).

---

## Mobile / empty state

| Option | Description | Selected |
|--------|-------------|----------|
| User severities + analyze pill | Collapsed = strip + user's 3 severity counts; unanalyzed = analyze pill | ✓ |
| Both-side severities collapsed | Collapsed = strip + both players' severity counts | |

**User's choice:** User severities + analyze pill
**Notes:** Collapsed mobile default stays scannable; unanalyzed game behaves as today's badge rows (analyze pill).

---

## Claude's Discretion

- Exact `FlawRef` union shape for the side dimension and how far to push the shared
  `MoveStats` extraction (SEED-112's natural extraction point vs the two files'
  deliberate "trivially safe copies" convention) — left to the planner.
- Confirming the analysis payload exposes `flaw_markers` + `eval_series` identically
  to the library card before planning client-side count derivation.

## Deferred Ideas

- Surfacing ACPL anywhere in the UI (computed in 178, intentionally not shown).
- `*_imported` accuracy fallback for coverage (explicitly rejected this phase).
- Running the Phase 178 prod accuracy/ACPL backfill (operator step, not gated here).
