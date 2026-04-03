# Phase 43: Frontend Cleanup - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-03
**Phase:** 43-frontend-cleanup
**Areas discussed:** Button class strategy, Test coverage (TOOL-04)

---

## Gray Area Selection

| Option | Description | Selected |
|--------|-------------|----------|
| Button class strategy | Keep PRIMARY_BUTTON_CLASS JS constant vs. replace with CSS @apply utility class vs. inline Tailwind classes | |
| Test coverage (TOOL-04) | Include in phase or drop. No coverage tooling exists yet. | |
| Remaining cleanup audit | Audit for stray hard-coded semantic colors beyond brand-brown | |

**User's choice:** Selected "Other" — delegated all technical decisions to Claude. Noted index.css looks messy but was informed the oklch values are shadcn/ui standard tokens.
**Notes:** User said: "I'm no frontend specialist. If I'm correct, our theme is centralized in index.css and theme.ts. index.css looks messy with dozens of very similar or identical whites and greys. It may be good or bad, I'll leave the restructuring and cleanup to you and trust your judgement."

---

## Test Coverage (TOOL-04)

| Option | Description | Selected |
|--------|-------------|----------|
| Drop it | Skip test coverage for this milestone. Can revisit in future. | ✓ |
| Include it | Add pytest-cov and/or vitest coverage to CI. Establishes baseline. | |

**User's choice:** Drop it
**Notes:** No additional rationale given.

---

## Claude's Discretion

- Button class strategy (keep/replace PRIMARY_BUTTON_CLASS)
- Hard-coded color audit approach
- index.css cleanup scope (explicitly limited — don't restructure shadcn tokens)
- Overall implementation approach

## Deferred Ideas

- TOOL-04 (test coverage analysis) — dropped from v1.7 milestone
