# Phase 229: Umami User Identification & Feature Events - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-03
**Phase:** 229-umami-identify-feature-events
**Areas discussed:** Event taxonomy, Identity edge cases, Inventory scope

---

## Event taxonomy

| Option | Description | Selected |
|--------|-------------|----------|
| No event for URL-routed tabs | Pageviews cover them; `tab-switch` only for non-URL tabs | ✓ |
| Event everything uniformly | `tab-switch` for every tab, duplicates pageviews | |

| Option | Description | Selected |
|--------|-------------|----------|
| Verb-level names + page/target props | ~6-10 generic names | ✓ |
| Per-feature names | 30-50 rows in Umami | |
| You decide | | |

| Option | Description | Selected |
|--------|-------------|----------|
| On user-initiated change only | No mount/restore/programmatic events | ✓ |
| Also on popover/menu open | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Enumerated values only | Typed unions, no FEN/usernames/free text | ✓ |
| Allow some identifiers | ECO, game id | |

| Option | Description | Selected |
|--------|-------------|----------|
| Leave existing events as-is | Keep history continuity | ✓ |
| Rename to fit the scheme | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Skip high-frequency actions | Move stepping, drag, scrubbing | ✓ |
| Track once per session | | |

---

## Identity edge cases

| Option | Description | Selected |
|--------|-------------|----------|
| Clean break, whatever it takes | Reload / storage clear if needed | ✓ |
| Best effort | Accept mis-attribution until next load | |

| Option | Description | Selected |
|--------|-------------|----------|
| Identify superusers normally, filter by id | | ✓ |
| Tag as account: admin | | |
| Don't identify superusers | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Keep skipping identify during impersonation | | ✓ |
| Identify as the admin | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Prefer no storage, re-identify each load | | ✓ |
| Accept storage, disclose it | | |

| Option | Description | Selected |
|--------|-------------|----------|
| First pageview without id acceptable if Umami stitches by session | | ✓ |
| Must be on every pageview | | |

---

## Inventory scope

| Option | Description | Selected |
|--------|-------------|----------|
| Analysis board | | ✓ |
| Openings / Endgames / Library | | ✓ |
| Train + Bots | | ✓ |
| Info popovers + nav | | ✓ |

| Option | Description | Selected |
|--------|-------------|----------|
| Inventory plan with review gate | | |
| Planner decides and wires directly | | ✓ |

| Option | Description | Selected |
|--------|-------------|----------|
| Exclude /admin, /activity, auth flows | | ✓ |
| Include auth flow steps | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Explanation popovers only, filters on change | | |
| Track filter-panel opens too | | ✓ |

**Notes:** Filter-panel opens are tracked as an explicit exception to the change-only rule.

---

## Claude's Discretion

Exact event-name list and prop keys, `page` derivation, plan split, test strategy, post-ship
verification query.

## Deferred Ideas

None.
