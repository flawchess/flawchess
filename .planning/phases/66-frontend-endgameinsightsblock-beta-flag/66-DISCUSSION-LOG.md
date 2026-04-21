# Phase 66: Frontend EndgameInsightsBlock & Beta Flag - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-21
**Phase:** 66-frontend-endgameinsightsblock-beta-flag
**Areas discussed:** Block placement & entry UX, Regenerate & filter invalidation, Failure/rate-limit/stale UI, Beta flag plumbing

---

## Block Placement & Entry UX

### Q1: Where does the EndgameInsightsBlock sit in the Endgame stats tab?

| Option | Description | Selected |
|--------|-------------|----------|
| Top, above all 4 H2 sections | Block renders first; overview + up to 4 SectionInsights, then the existing H2s. Matches success criterion #2 literal reading. | |
| Interleaved per section | Overview at top; each SectionInsight rendered inside its matching existing H2. Tighter contextual link. | ✓ |
| Below the charts, at the bottom | Block renders last; 'summary after the data'. | |

**User's choice:** Interleaved per section
**Notes:** Became the architectural backbone of the phase — single API call, multiple render sites, overview replaces top hero card after generation.

### Q2: How does the 'Generate insights' CTA appear before first click?

| Option | Description | Selected |
|--------|-------------|----------|
| Hero card with CTA + blurb | Charcoal-texture card with "Insights" H2, 1-line blurb, primary Generate button. | ✓ |
| Inline button, no hero card | Just a Button below the first H2. | |
| Collapsible accordion trigger | "Insights" accordion; click to expand then Generate. | |

**User's choice:** Hero card with CTA + blurb
**Notes:** Matches the existing H2 + charcoal-card visual pattern used throughout Endgames.tsx.

### Q3: What label heads the insights block?

| Option | Description | Selected |
|--------|-------------|----------|
| Insights | Short, clean; tab context implies Endgame. | ✓ |
| AI Insights | Explicit AI branding. | |
| Endgame Insights | Explicit subject. | |
| Performance Summary | Avoids 'insights'/'AI'. | |

**User's choice:** Insights

### Q4: After a successful generation, always-expanded or collapsible?

| Option | Description | Selected |
|--------|-------------|----------|
| Always expanded, no collapse | Overview and all section blocks stay visible after click. | ✓ |
| Collapsible block with Regenerate | Whole block collapses via X/toggle. | |
| Each section individually collapsible | Sections are accordion items. | |

**User's choice:** Always expanded, no collapse

### Q5: Where inside each existing H2 block does the SectionInsight render?

| Option | Description | Selected |
|--------|-------------|----------|
| Above existing charts | SectionInsight frames the data: headline + bullets, then charts. | ✓ |
| Below existing charts | Takeaway/summary after the charts. | |
| In its own charcoal card inside the H2 | Stacked card alongside chart cards. | |

**User's choice:** Above existing charts

### Q6: After generation, where does the overview render and what happens to the hero card?

| Option | Description | Selected |
|--------|-------------|----------|
| Overview replaces hero card at top | Same top card now contains overview + Regenerate. | ✓ |
| Overview below a compact Regenerate strip | Top strip shrinks to "Insights • Regenerate"; overview in separate card below. | |
| Overview only, no top card | Hero card disappears; overview becomes top content. | |

**User's choice:** Overview replaces hero card at top

### Q7: If the LLM returns fewer than 4 sections, what does the unmatched H2 show?

| Option | Description | Selected |
|--------|-------------|----------|
| Nothing — H2 renders its charts as today | No placeholder, no note. | ✓ |
| Subtle 'no headline signal' note | Small muted text in the section slot. | |
| Empty shell placeholder | Empty card matching SectionInsight shape. | |

**User's choice:** Nothing — H2 renders its charts as today

### Q8: If an H2 is suppressed today (no-data) but LLM returned a matching section_id, what happens?

| Option | Description | Selected |
|--------|-------------|----------|
| Skip the SectionInsight along with the H2 | Existing suppression wins; FE drops the insight. | ✓ |
| Render a standalone insight card | FE renders a lone card where the H2 would've been. | |
| Always show all H2s when insights are present | Force-show every H2. | |

**User's choice:** Skip the SectionInsight along with the H2
**Notes:** Defensive safety net; Phase 65 D-19 already instructs the LLM not to emit sections for thin-sample cases.

---

## Regenerate & Filter Invalidation

### Q1: When applied filters change after a report is showing, what happens to the rendered insights?

| Option | Description | Selected |
|--------|-------------|----------|
| Stay visible, flagged as outdated | Keep content on screen; show "outdated" indicator; Regenerate button more prominent. | ✓ |
| Clear immediately, show Generate button | Clear insights; return to pre-click state. | |
| Auto-regenerate on filter commit | New POST automatically fires on every filter change. | |

**User's choice:** Stay visible, flagged as outdated
**Notes:** INS-03 explicitly requires "**regenerating** produces a visibly different insight" — user-initiated.

### Q2: Should the FE distinguish findings-affecting vs non-affecting filters?

| Option | Description | Selected |
|--------|-------------|----------|
| No — backend cache handles it | FE posts with full filter context; backend cache guarantees no LLM call for color/rated_only. | ✓ |
| Yes — FE suppresses 'outdated' indicator for color/rated_only | FE duplicates the findings-affecting filter list. | |
| Yes — FE skips the Regenerate call entirely for color/rated_only | Disable/hide Regenerate when only non-affecting filters changed. | |

**User's choice:** No — backend cache handles it
**Notes:** One code path; INS-03 is a backend property per Phase 65 D-31.

### Q3: How is the insights call modeled in TanStack Query?

| Option | Description | Selected |
|--------|-------------|----------|
| useMutation + local state | Matches useImportTrigger pattern; no cross-page persistence. | ✓ |
| useQuery with enabled:false + manual refetch | Keyed on filters; cache persists across navigation. | |
| useQuery keyed on findings-affecting filters only | Clever but entangles FE with backend cache logic. | |

**User's choice:** useMutation + local state

### Q4: What does the button label say in each state?

| Option | Description | Selected |
|--------|-------------|----------|
| 'Generate insights' → 'Regenerate' after first run | Clear state transition. | ✓ |
| 'Generate insights' always | Same label throughout. | |
| 'Generate insights' → 'Regenerate insights' after first run | Fuller label after first click. | |

**User's choice:** 'Generate insights' → 'Regenerate' after first run

---

## Failure / Rate-Limit / Stale UI

### Q1: What is the locked failure copy (429/502/503/network)?

| Option | Description | Selected |
|--------|-------------|----------|
| "Couldn't generate insights. Please try again in a moment." + [Try again] | Matches project convention (Endgames.tsx:360,433). | ✓ |
| "Insights are temporarily unavailable. Please try again in a moment." + [Try again] | Softer; framed as availability. | |
| "Failed to generate insights. Something went wrong. Please try again in a moment." + [Try again] | Closer clone of existing house style. | |

**User's choice:** "Couldn't generate insights. Please try again in a moment." + [Try again]

### Q2: How is status='stale_rate_limited' surfaced?

| Option | Description | Selected |
|--------|-------------|----------|
| Muted banner above the overview | Banner inside the top card; content renders normally below. | ✓ |
| Pill on the Regenerate button | 'Rate-limited • retry in ~{N} min' badge on button. | |
| No UI distinction | Treat identically to fresh/cache_hit. | |

**User's choice:** Muted banner above the overview

### Q3: Do we show which filters differ (stale_filters) when stale_rate_limited fires?

| Option | Description | Selected |
|--------|-------------|----------|
| No — just 'prior insights' banner | Generic banner; stale_filters unused by FE. | ✓ |
| Yes — list differing filter names | Banner lists filter=value pairs. | |
| Yes — show a diff pill per differing filter | Pills per changed filter. | |

**User's choice:** No — just 'prior insights' banner

### Q4: For HTTP 429 with retry_after_seconds, do we show a countdown?

| Option | Description | Selected |
|--------|-------------|----------|
| Show 'Try again in ~{N} min' below the locked copy | Static, rounded to minute. | ✓ |
| Live ticking countdown | MM:SS decrementing; re-enable Retry at 0. | |
| Generic locked copy, no countdown | Ignore retry_after_seconds. | |

**User's choice:** Show 'Try again in ~{N} min' below the locked copy

---

## Beta Flag Plumbing

### Q1: Where do we surface insights_beta_enabled to the FE?

| Option | Description | Selected |
|--------|-------------|----------|
| Add to /users/me/profile response | Extend UserProfileResponse + UserProfile TS type with insights_beta_enabled: bool. | ✓ (with rename) |
| New /users/me/features endpoint | Dedicated feature-flags endpoint. | |
| Inline in the auth /users/me response | Mix auth and feature concerns. | |

**User's choice:** Use /users/me/profile, BUT rename the flag to be feature-agnostic: `beta_enabled` (not `insights_beta_enabled`)
**Notes:** User explicitly overrode the column name in "Other" text. Generalization trade-off acknowledged: all beta features share one flag. REQUIREMENTS.md BETA-01 and ROADMAP.md Phase 66/67 references need rewriting as part of implementation.

### Q2: Where does the FE conditional render live?

| Option | Description | Selected |
|--------|-------------|----------|
| Inside EndgameInsightsBlock (returns null if flag false) | Component self-gates via useUserProfile(). | ✓ |
| Conditional in Endgames.tsx | Parent component handles the check. | |
| Generic <FeatureGate> wrapper | Reusable gate component. | |

**User's choice:** Inside EndgameInsightsBlock (returns null if flag false)

### Q3: What does the Alembic migration look like?

| Option | Description | Selected |
|--------|-------------|----------|
| Single column, nullable=False, server_default='false' | Clean default for prod backfill; no index. | ✓ |
| Same + partial index WHERE beta_enabled = true | Index for future admin queries. | |
| nullable=True, no server_default | NULL allowed; FE treats as false. | |

**User's choice:** Single column, nullable=False, server_default='false'

### Q4: Does admin impersonation (Phase 62) respect the impersonated user's beta flag?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — flag follows the impersonated user | ClaimAwareJWTStrategy flips current_active_user; /users/me/profile returns the impersonated user's flag naturally. | ✓ |
| No — always show insights to admins during impersonation | Superusers see insights regardless of target flag. | |
| Explicit admin-override toggle | Admin has a separate 'show beta features' toggle. | |

**User's choice:** Yes — flag follows the impersonated user
**Notes:** This is the mechanism Phase 67 will use for its 5+ real-user eyeball validation.

---

## Claude's Discretion

- Exact visual treatment of the "outdated" indicator (pill / icon / caption) — UI phase or planner
- Exact hero card blurb copy (1-line explanation) — planner
- Exact stale banner copy (muted style) — planner
- SectionInsight typography, margins, rule-above-charts — UI phase or planner
- Loading skeleton shape during in-flight mutation — planner
- `data-testid` values per CLAUDE.md §Frontend naming — planner
- Whether mutation state lives in `EndgameInsightsBlock` or is lifted to `Endgames.tsx` with a context — planner
- Minute-rounding rule for retry_after_seconds (`ceil` vs `round`, min 1) — planner
- Mobile variant specifics beyond "matches existing Endgame tab mobile layout" — planner

## Deferred Ideas

- LocalStorage persistence of the last rendered report across reloads
- Admin UI for flipping `beta_enabled` (locked to direct DB ops by BETA-01)
- Per-feature beta columns / `user_beta_features` table (deliberate generalization trade-off)
- Live ticking countdown on 429
- Filter-diff visualization on `stale_rate_limited`
- Displaying `model_used` / `prompt_version` to regular users (Phase 65 D-17 debug-only)
- Per-section streaming responses (Phase 65 D-40 deferred)
- Info-popover on the insights block explaining the feature
- Scroll-into-view anchor after Generate click
- Integration-test scope (Phase 66 ships tests? Phase 67 handles it?) — planner decides
