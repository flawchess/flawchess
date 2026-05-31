# Phase 101: Frontend Major Dependency Upgrades - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-31
**Phase:** 101-frontend-major-dependency-upgrades
**Areas discussed:** recharts UAT, Blocker policy, Stragglers, Merge cadence

> Note: This phase was unusually pre-specified. ROADMAP.md success criteria + SEED-032 already locked the cluster list, low→high ordering, atomic-commit-per-cluster structure, the full-gate definition, the pin-back escape hatch, and the peer-compat research question. Discussion covered only the genuinely-open decisions below.

---

## recharts UAT

| Option | Description | Selected |
|--------|-------------|----------|
| Human UAT, Claude prepares | Claude renders charts green, hands user a checklist + local URL/routes for desktop + mobile eyeball; user gives verdict | ✓ |
| Claude browser-automation UAT | Claude drives the app, screenshots each chart at desktop + mobile widths, self-reports | |
| Both — automated pass then human sign-off | Automated screenshot pass for obvious breakage, then human checklist sign-off | |

**User's choice:** Human UAT, Claude prepares
**Notes:** recharts is the one user-facing cluster; human eyeball is the gate. Checklist must cover MiniBulletChart, WDLChartRow, ScoreChart, ScoreGapByTimePressureChart, gauges, custom tooltips/gradients. → D-01

---

## Blocker policy (typescript-eslint ↔ TS6 / eslint10)

| Option | Description | Selected |
|--------|-------------|----------|
| Defer immediately, record blocker | If peers don't cleanly support the target, skip the cluster, note blocker + unblocking version, ship the rest green | |
| Try overrides/workarounds briefly first | Bounded effort (peer overrides, known-good intermediate combo, wait-check), defer only if that fails | ✓ |

**User's choice:** Try overrides/workarounds briefly first
**Notes:** Deliberate slightly-more-aggressive reading of the roadmap's "rather than forced" — try safe workarounds, but don't ship a fragile/over-pinned lockfile to force it. → D-02

---

## Stragglers (multi-select)

| Option | Description | Selected |
|--------|-------------|----------|
| Fold in shadcn 4.9.0 | Within-major bump as a trivial extra commit; gets lockfile current | ✓ |
| Revisit the disabled hooks rule | After eslint-10 bump, re-evaluate `react-hooks/set-state-in-effect: off`; act only if behavior changes | ✓ |

**User's choice:** Both
**Notes:** → D-04 (shadcn), D-05 (hooks rule). Leave the blanket `off` if eslint-10 doesn't change the rule's behavior.

---

## Merge cadence

| Option | Description | Selected |
|--------|-------------|----------|
| One squash-merge at phase end | All clusters on a feature branch, full gate once, single squash-merge | |
| Incremental: merge each green cluster | Each cluster: branch → full gate → squash-merge to main; next branches off updated main | ✓ |

**User's choice:** Incremental: merge each green cluster
**Notes:** Extends bisectability to main history; prevents recharts (high-risk, last) from stranding earlier green work. Accepts ~6 full-gate runs. → D-06

---

## Claude's Discretion

- Exact plan/file structure (one ordered-wave plan vs one plan per cluster) — planner's call, but clusters stay sequential, never parallel.
- Re-run `npm outdated` at planning/execution to refresh exact target versions (SEED-032 snapshot will drift).

## Deferred Ideas

None — discussion stayed within phase scope. Backend dep bumps explicitly out of scope (backend already fully current).

## Surfaced during discussion (factual, folded into CONTEXT.md)

- CI runs Node 24 (`.github/workflows/ci.yml`), so `@types/node` is pinned to the 24.x line — NOT bumped to 25 as the seed's snapshot suggested. → D-03
