# Phase 41: Code Quality & Dead Code - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-02
**Phase:** 41-code-quality-dead-code
**Areas discussed:** API naming & breaking changes, Dead code strategy, Deduplication threshold, Naming scope

---

## API Naming & Breaking Changes

| Option | Description | Selected |
|--------|-------------|----------|
| Rename freely | No external consumers, so rename endpoints and update frontend in lockstep. Clean slate. | ✓ |
| Add redirects | Rename endpoints but keep old paths as redirects for a transition period. | |
| Rename only egregious ones | Only rename endpoints that are genuinely confusing. Leave acceptable names alone. | |

**User's choice:** Rename freely
**Notes:** No external API consumers — only the React frontend calls the backend.

| Option | Description | Selected |
|--------|-------------|----------|
| Fix inconsistencies only | Standardize naming patterns where inconsistent (plural vs singular, verb vs noun) but don't restructure working paths. | ✓ |
| Full REST restructure | Reorganize all endpoints to strict RESTful nested resources. More churn, but cleaner long-term. | |
| You decide | Claude reviews the current paths and fixes only what's clearly wrong. | |

**User's choice:** Fix inconsistencies only
**Notes:** No full REST restructure — just fix what's inconsistent.

---

## Dead Code Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| One-time audit | Run knip once, review report, remove dead exports. Don't add to CI. | |
| Permanent CI step | Add knip to CI pipeline so dead exports are caught on every PR. | |
| Evaluate first, decide later | Run knip, see how noisy the output is, then decide. | |

**User's choice:** Other — provided detailed tooling recommendation
**Notes:** User provided comprehensive research recommending: (1) Add Knip as CI step, (2) Enable noUncheckedIndexedAccess in tsconfig, (3) Add npm test + npm run build to CI. Explicitly skip Oxlint, Biome, Madge, ts-prune. All three items folded into phase scope.

| Option | Description | Selected |
|--------|-------------|----------|
| Fold both in | Small, high-value changes that fit naturally alongside code quality work. | ✓ |
| Fold CI gaps only | Defer noUncheckedIndexedAccess to future phase. | |
| Defer both | Keep Phase 41 strictly about naming, deduplication, dead code. | |

**User's choice:** Fold both in
**Notes:** noUncheckedIndexedAccess and CI frontend steps folded into Phase 41 scope.

| Option | Description | Selected |
|--------|-------------|----------|
| Manual + ruff | Ruff catches unused imports. Manual review for unused functions/classes — backend is small enough. | ✓ |
| Add vulture | Automated dead code detection for Python. More thorough but false positives with dynamic dispatch. | |
| You decide | Claude picks the approach. | |

**User's choice:** Manual + ruff
**Notes:** Backend is small enough (~12 service/repo files) for manual review.

---

## Deduplication Threshold

| Option | Description | Selected |
|--------|-------------|----------|
| Only obvious duplication | Extract only when logic is clearly duplicated (same function body in 2+ places). | |
| Aggressive DRY | Extract any repeated pattern into shared utilities. | |
| You decide per case | Claude uses judgment — extract when 3+ copies or maintenance risk, skip when abstraction hurts readability. | ✓ |

**User's choice:** You decide per case
**Notes:** Claude's discretion on deduplication threshold.

| Option | Description | Selected |
|--------|-------------|----------|
| Existing files preferred | Add to existing utils/helpers unless shared logic warrants its own module. | ✓ |
| New modules when logical | Create new shared modules when extracted logic has a clear domain. | |
| You decide | Claude places extracted code where it fits best. | |

**User's choice:** Existing files preferred
**Notes:** None.

---

## Naming Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, but conservative | Review internal names but only rename when genuinely confusing or inconsistent. | ✓ |
| API paths only | Limit renaming to API endpoint paths and route names. | |
| Full sweep | Review all public function names, class names, and key variables. | |

**User's choice:** Yes, but conservative
**Notes:** Don't rename for style preference alone.

| Option | Description | Selected |
|--------|-------------|----------|
| Fix only if inconsistent | If most follow PascalCase/camelCase convention, fix outliers. | |
| You decide | Claude reviews current naming patterns and aligns outliers. | ✓ |
| Leave file names alone | Only rename exports and variables, not file names. | |

**User's choice:** You decide
**Notes:** Claude's discretion on frontend file naming alignment.

---

## Claude's Discretion

- Deduplication threshold per case (extract when 3+ copies or maintenance risk)
- Frontend file naming convention alignment (review and fix outliers)

## Deferred Ideas

None — discussion stayed within phase scope.
