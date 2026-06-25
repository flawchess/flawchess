# Phase 135: Tactic Line Explorer — Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-24
**Phase:** 135-tactic-line-explorer-walkable-pv-stepper-for-tagged-flaws-se
**Areas discussed:** Entry-point UX details

---

## Area selection

| Area | Selected |
|------|----------|
| Explore gating & single-line flaws | |
| Payoff length & short PVs | |
| Backend contract (endpoint + SAN) | |
| Entry-point UX details | ✓ |

The user chose to discuss only **Entry-point UX details**; the other three areas were left to
Claude's discretion using SEED-065's documented leans.

---

## Entry-point UX details

### Modal stacking (game-card Explore)

| Option | Description | Selected |
|--------|-------------|----------|
| Stack on top, close returns | Explore opens as a second Dialog over the Game modal; closing returns to the Game view. | ✓ |
| Replace Game modal | Opening Explore closes the Game modal first; close returns to the page. | |

**User's choice:** Stack on top, close returns to Game modal.
**Notes:** Matches SEED-065's "modal-on-modal acceptable" note. Verify mobile focus/scroll-trap.

### Game-card disabled state

| Option | Description | Selected |
|--------|-------------|----------|
| Visible but disabled + tooltip | Always shown, greyed when parked position isn't a tagged flaw, tooltip explains why. | ✓ |
| Hidden until tagged | Button only appears on a tagged flaw; layout shifts as flaws cycle. | |

**User's choice:** Visible but disabled + tooltip.

### Flaw-card button row (untagged flaws)

| Option | Description | Selected |
|--------|-------------|----------|
| Row with just Game | All flaw cards use the button row; untagged shows a single "Game" button. | ✓ |
| Keep header for untagged | Only tagged flaws get the row; untagged keeps "Game" in the header. | |

**User's choice:** Row with just Game (one consistent layout for all flaw cards).

### Game-card Explore placement

| Option | Description | Selected |
|--------|-------------|----------|
| Below chart, near flaw nav | Beneath the eval chart, adjacent to flaw-marker navigation. | ✓ |
| Card header area | In the game card header alongside existing controls. | |
| You decide | Planner/executor chooses cleanest spot. | |

**User's choice:** Below chart, near the flaw navigation.

---

## Claude's Discretion

- **Explore gating & single-line flaws** — any tagged flaw with ≥1 line gets Explore; "tagged"
  already implies confidence ≥70; single-orientation flaws open with that one line, toggle hidden.
- **Payoff length & short PVs** — tactic move + ~2–4 payoff plies, truncate tail, graceful
  short-PV handling.
- **Backend contract** — dedicated lazy-fetch `tactic-lines` endpoint returning both PVs +
  depths + motif + tactic-move index; UCI→SAN conversion location left to research/planning.

## Deferred Ideas

None — discussion stayed within phase scope.
