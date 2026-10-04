---
id: SEED-188
status: dormant
planted: 2026-10-04
planted_during: Phase 232 (SEED-187) Plan 02, override re-check
trigger_when: next dependency maintenance phase, or any of these advisories becoming reachable from the shipped bundle
scope: small
---

# SEED-188: shadcn CLI dev-only npm audit advisories (6 high)

## Why This Matters

A full `npm audit` from `frontend/` (dev dependencies included) reports 6 high
severity findings after Phase 232 cleared the fast-uri advisory. Every one of
them is reached through the `shadcn` devDependency, the component-scaffolding
CLI. None of them is in the shipped bundle, and the production gate
(`npx audit-ci --config frontend/audit-ci.jsonc`, `skip-dev: true`) passes with
an empty allowlist. This seed records them so a later maintenance phase can
decide, instead of the next person rediscovering them in `npm audit` output.

`npm audit` metadata: `{"info":0,"low":0,"moderate":0,"high":6,"critical":0,"total":6}`.

## What

The high advisories exactly as `npm audit --json` reported them on 2026-10-04
(shadcn 4.21.0 installed):

| Package | Advisory | Severity | Affected range | Role |
|---|---|---|---|---|
| braces | GHSA-vfj7-8cjw-p6xm (braces vulnerable to stack-exhaustion denial of service through deeply nested patterns) | high | `<=3.0.3` (installed 3.0.3) | the only package carrying a direct advisory |
| micromatch | via braces | high | `>=0.2.0` (installed 4.0.8) | transitive |
| fast-glob | via micromatch | high | `*` (installed 3.3.3) | transitive |
| @ts-morph/common | via fast-glob | high | `0.2.0 - 0.24.0 \|\| 0.26.0 - 0.27.0` (installed 0.27.0) | transitive |
| ts-morph | via @ts-morph/common | high | `6.0.1 - 23.0.0 \|\| 25.0.0 - 26.0.0` (installed 26.0.0) | transitive |
| shadcn | via fast-glob, ts-morph | high | `<=0.0.0-beta-20261001093212 \|\| >=2.0.0` | direct devDependency |

Dependency paths back to shadcn:

- `shadcn@4.21.0 > fast-glob@3.3.3 > micromatch@4.0.8 > braces@3.0.3`
- `shadcn@4.21.0 > ts-morph@26.0.0 > @ts-morph/common@0.27.0 > fast-glob@3.3.3`

Only `braces` has a root advisory (a stack-exhaustion DoS on deeply nested glob
patterns); the other five are flagged purely because they depend on it. The
audit's suggested fix is a semver-major "downgrade" of shadcn to 1.0.0, which is
not a real option.

Why dev-only: `shadcn` is a devDependency used only to add components
(`npx shadcn add ...`). It is never imported by `frontend/src`, never bundled,
and glob patterns it expands come from the developer's own machine, not from
untrusted input.

Options and trade-offs:

1. **Override `braces` (and friends) within each package's current major.**
   Cheapest, same mechanism as the existing `overrides` block. Risk: the same
   one D-04 guarded against, forcing a version outside a consumer's declared
   range. Needs a patched `braces` 3.x to exist first (the audit range is
   `<=3.0.3`, so check the registry for a fixed 3.x before choosing this).
2. **Wait for a shadcn release** that bumps `fast-glob` / `ts-morph`. No work,
   but no control over timing. Re-run `npm audit` at each maintenance phase.
3. **Drop the shadcn devDependency** and invoke the CLI through `npx` when a
   component is added. Removes all 6 findings from the tree permanently. The
   `shadcn` entry in `frontend/knip.json` `ignoreDependencies` would go too.
   Trade-off: component adds fetch the CLI on demand and the CLI version is no
   longer pinned by the lockfile.

Recommended starting point when this fires: option 3 if the dev-only noise keeps
returning, otherwise option 1 once a patched braces is published.

## Breadcrumbs

- `frontend/package.json` (shadcn devDependency, `overrides` block)
- `frontend/audit-ci.jsonc` (`skip-dev: true`, allowlist `[]`)
- `frontend/knip.json` (`ignoreDependencies` entry for shadcn)
- Phase 232 `232-CONTEXT.md` Deferred Ideas, and `232-02-PLAN.md` Task 1 step 6
