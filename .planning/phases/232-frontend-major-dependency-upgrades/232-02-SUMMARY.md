---
phase: 232-frontend-major-dependency-upgrades
plan: 02
subsystem: infra
tags: [frontend, deps, overrides, security, renovate, fast-uri, js-yaml]

requires:
  - phase: 232-01
    provides: vite-plugin-pwa 2.0.0 with workbox-build unchanged at 7.4.1, so the override consumer graph could be re-checked on its final shape
provides:
  - fast-uri override floor ^3.1.8 (every installed fast-uri is 3.1.8, GHSA-hrr3-gc8f-f4qj cleared from npm audit)
  - Renovate packageRules entry disabling majors for the override-only js-yaml and fast-uri
  - SEED-188 capturing the 6 high dev-only advisories reached through the shadcn CLI
affects: [232-03, 232-04]

plan_head_before: e4a216b696e0689949672aad2ded93be9c720558
plan_head_after: 5d66c4d752810d7f6415e4955f7e5ef0026ac871

actuals:
  tokens: 4500
  tasks: 2
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Security-only overrides stay inside the major their consumers declare; Renovate majors for override-only deps are disabled with a matchDepTypes overrides rule"

key-files:
  created:
    - .planning/seeds/SEED-188-shadcn-cli-dev-advisories.md
  modified:
    - frontend/package.json
    - frontend/package-lock.json
    - renovate.json

key-decisions:
  - "D-04: fast-uri override floor raised ^3.1.5 -> ^3.1.8 inside its current major; js-yaml override left at ^4.3.1 (resolves to 4.3.2, newest 4.x)"
  - "D-04: Renovate rule (matchDepTypes overrides, js-yaml + fast-uri, major, enabled false) added as the fifth packageRules entry"
  - "No blocking-human package-legitimacy checkpoint for fast-uri 3.1.8: pre-existing override, automated publisher-continuity gate and npm audit signatures passed (Phase 217 precedent, deviation recorded in the plan)"

requirements-completed: [DEP-OVR]

coverage:
  - id: D1
    description: "fast-uri override floor ^3.1.8; all installed fast-uri 3.1.8, no js-yaml 5.x, npm audit no longer lists fast-uri"
    requirement: "DEP-OVR"
    verification:
      - kind: other
        ref: "cd frontend && npm ls fast-uri / npm ls js-yaml check (OVERRIDES-OK) and npm audit --json (FAST-URI-CLEAR)"
        status: pass
      - kind: other
        ref: "cd frontend && npx audit-ci --config audit-ci.jsonc && npm audit signatures && npm run build"
        status: pass
    human_judgment: false
  - id: D2
    description: "renovate.json rule disabling majors for js-yaml and fast-uri overrides, accepted by renovate-config-validator --strict and rejected when deliberately broken"
    requirement: "DEP-OVR"
    verification:
      - kind: other
        ref: "npx -y --package renovate@44.132.5 renovate-config-validator --strict (success, then exit 1 on enabled:\"nope\", then success again)"
        status: pass
    human_judgment: false
  - id: D3
    description: "6 high dev-only shadcn CLI advisories captured as dormant SEED-188, not fixed"
    requirement: "DEP-OVR"
    verification:
      - kind: other
        ref: "ls .planning/seeds/SEED-188-*.md and grep status: dormant"
        status: pass
    human_judgment: false
  - id: D4
    description: "Post-merge: Renovate dashboard #338 stops listing renovate/fast-uri-4.x and renovate/js-yaml-5.x"
    requirement: "DEP-OVR"
    verification: []
    human_judgment: true
    rationale: "Observable only after merge on the Renovate dashboard; cannot be asserted locally."

duration: 9min
completed: 2026-10-04
status: complete
---

# Phase 232 Plan 02: Override floors and Renovate major rule Summary

**fast-uri override floor raised to ^3.1.8 (all installed copies 3.1.8, GHSA-hrr3-gc8f-f4qj cleared), js-yaml kept on 4.x, a validated Renovate rule that stops offering their majors, and the shadcn CLI dev-only advisories captured as SEED-188.**

## Performance

- **Duration:** ~9 min
- **Tasks:** 2 (1 tracer, 1 auto)
- **Files modified:** 4 (3 modified, 1 created)

## Accomplishments

- Re-checked the consumer graph after vite-plugin-pwa 2: the premise for staying within major still holds. Every ajv 8 is the single deduped 8.20.0, declaring `fast-uri ^3.0.1`; cosmiconfig 9.0.2 declares `js-yaml ^4.1.0`.
- fast-uri override `^3.1.5` -> `^3.1.8`; lock moved 3.1.7 -> 3.1.8 (3-line lock diff: version, resolved, integrity). No other override touched.
- `npm audit` no longer lists fast-uri; the full audit is down to the 6 shadcn-reached dev-only highs (captured as SEED-188).
- renovate.json gained a fifth packageRules entry; validator success, negative control and restore all recorded below.
- Full frontend gate green: lint, build (tsc -b + vite), vitest 4983/4983, knip, audit-ci (allowlist `[]`), `npm audit signatures`.

## Task Commits

1. **Task 1 (tracer): fast-uri floor to ^3.1.8** - `611d02cbe` (chore(deps))
   - Seed (Task 1 step 6): `d665adf83` (docs(232))
2. **Task 2: Renovate stops offering js-yaml and fast-uri majors** - `5d66c4d75` (chore(renovate))

**Plan metadata:** docs(232-02) commit following this SUMMARY.

## Task 1 Evidence

**Consumer graph re-check (`npm ls fast-uri ajv js-yaml cosmiconfig workbox-build`, before the change):**

```
eslint@10.10.0 > ajv@6.15.0
shadcn@4.21.0 > @dotenvx/dotenvx@1.75.1 > conf@10.2.0 > ajv@8.20.0 > fast-uri@3.1.7
shadcn@4.21.0 > @modelcontextprotocol/sdk@1.30.0 > ajv@8.20.0 > fast-uri@3.1.7
shadcn@4.21.0 > cosmiconfig@9.0.2 > js-yaml@4.3.2
vite-plugin-pwa@2.0.0 > workbox-build@7.4.1 > ajv@8.20.0 > fast-uri@3.1.7
```

`npm view ajv@8.20.0 dependencies.fast-uri` -> `^3.0.1`; `npm view cosmiconfig@9.0.2 dependencies.js-yaml` -> `^4.1.0`. Both ranges as expected, so D-04's premise is intact and no checkpoint was needed. (ajv@6.15.0 under eslint does not use fast-uri.)

**Pre-install identity check (T-232-SC):** `fast-uri@3.1.8` `_npmUser.name` `matteo.collina`, same as 3.1.7; repository `git+https://github.com/fastify/fast-uri.git`; scripts contain only lint/test entries, no preinstall, install or postinstall. All conditions met, no blocking-human escalation.

**After `npm install`:** `npm ls fast-uri` shows only 3.1.8 (4 instances, all deduped to one); `npm ls js-yaml` shows only 4.3.2; script `OVERRIDES-OK`. `npm audit --json` -> `FAST-URI-CLEAR`. `npx audit-ci --config audit-ci.jsonc` "Passed npm security audit", `npm audit signatures` 1006 verified registry signatures and 310 verified attestations, `npm run build` exit 0.

**Tracer gate (auto mode):** verify re-run end to end after the commit passed, so expansion to Task 2 proceeded.

## Task 2 Evidence

Validator (`npx -y --package renovate@44.132.5 renovate-config-validator --strict`, from repo root):

```
 INFO: Validating renovate.json
 INFO: Config validated successfully against 1 file(s)
```

Negative control (rule's `enabled` temporarily set to the string `"nope"`):

```
ERROR: Found errors in configuration
  "message": "Configuration option `packageRules[4].enabled` should be boolean. Found: \"nope\" (string)"
exit 1
```

Restored to `false`, validator again `Config validated successfully against 1 file(s)`. `packageRules.length` = 5; the diff is purely additive (8 inserted lines, none removed).

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. `npm install` printed the pre-existing allow-scripts warning for `protobufjs@7.6.6` and `stockfish@18.0.8` (unrelated). The planning-time notes about `grep` carat handling are moot: in this shell `grep` is a wrapper that treats an unescaped `^` literally differently, so the `"fast-uri": "^3.1.8"` acceptance count was verified with the caret escaped (prints 1; js-yaml likewise 1).

## Known Stubs

None.

## Threat Flags

None. No new endpoints, auth paths or schema changes. T-232-03 and T-232-04 mitigated as planned; T-232-05 accepted (renovate fetched once into the npx cache, not added to package.json or lock); T-232-06 accepted and recorded in SEED-188.

## User Setup Required

None.

## Next Phase Readiness

- Ready for 232-03. Post-merge observation (not gated): Renovate dashboard #338 should stop listing fast-uri 4.x and js-yaml 5.x.
- Requirement `DEP-OVR` is a descriptive ID with no `.planning/REQUIREMENTS.md` entry, so `requirements.mark-complete` is skipped.

## Self-Check: PASSED

- FOUND: commits 611d02cbe, d665adf83, 5d66c4d75 on gsd/phase-232-frontend-major-dependency-upgrades
- FOUND: `"fast-uri": "^3.1.8"` and `"js-yaml": "^4.3.1"` in frontend/package.json; fast-uri-3.1.8.tgz in lock
- FOUND: .planning/seeds/SEED-188-shadcn-cli-dev-advisories.md (status: dormant)
- FOUND: renovate.json fifth packageRules entry
- commits measured: `git rev-list --count e4a216b69..HEAD` = 3

---
*Phase: 232-frontend-major-dependency-upgrades*
*Completed: 2026-10-04*
