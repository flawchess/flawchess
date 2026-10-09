---
phase: 232-frontend-major-dependency-upgrades
plan: 04
subsystem: infra
tags: [frontend, deps, typescript, typescript-7, toolchain, changelog]

requires:
  - phase: 232-03
    provides: Sentry 11 settled before the compiler swap, so the TS7 type check ran against the final dependency set
provides:
  - "npm run build type-checks with the native TypeScript 7.0.2 tsc (@typescript/native alias)"
  - "typescript resolves to @typescript/typescript6 (TS 6.0.3 JS API) for typescript-eslint and eslint-plugin-sonarjs"
  - "tsconfigs free of baseUrl, ignoreDeprecations and the TODO(TS7) comment; @/* paths mapping unchanged"
  - "Phase close docs: CHANGELOG [Unreleased] bullet, STATE.md alias note, SEED-162 cluster 3 resolved, Phase 217 D-11 superseded"
affects: [phase 232 squash-merge, future TypeScript 7.1 unwind]

plan_head_before: a4708a3a2ec84876467c9c34a925be654b8170c2
plan_head_after: a51b7959d7e7e68e1dd28f462fbabccc4c49c08e

actuals:
  tokens: 20000
  tasks: 3
  commits: 3

tech-stack:
  added: ["@typescript/native (alias of typescript@7.0.2)", "@typescript/typescript6 6.0.2 (alias target of typescript; pulls @typescript/old = typescript 6.0.3)"]
  patterns:
    - "Official side-by-side TypeScript install: the name `typescript` keeps the JS compiler API tools need, the native compiler lives under @typescript/native and owns the `tsc` bin"

key-files:
  created: []
  modified:
    - frontend/tsconfig.json
    - frontend/tsconfig.app.json
    - frontend/package.json
    - frontend/package-lock.json
    - CHANGELOG.md
    - .planning/STATE.md
    - .planning/seeds/SEED-162-major-dependency-backlog.md
    - .planning/milestones/v2.16-phases/217-frontend-major-bumps-vitest-5-jsdom-30-onnxruntime-web-1-29/217-CONTEXT.md

key-decisions:
  - "D-01: TypeScript 7 adopted through Microsoft's side-by-side alias; Renovate's typescript-7.x branch stays unmerged (it installs 7 under the typescript name and breaks lint)"
  - "D-05: last wave, so Plans 01-03 stay shipped independent of this swap (no TS7 type errors surfaced, so it was not needed)"
  - "Unwind trigger recorded: TS 7.1 ships its JS API and a typescript-eslint release accepts it (typescript-eslint#10940)"

requirements-completed: [DEP-TS7]

coverage:
  - id: D1
    description: "tsconfigs TS7-valid (baseUrl, ignoreDeprecations, TODO(TS7) removed, paths mapping kept) and npm run build passes on both TS6 (before the alias) and TS7"
    requirement: "DEP-TS7"
    verification:
      - kind: other
        ref: "grep -nE 'baseUrl|ignoreDeprecations|TODO\\(TS7\\)' frontend/tsconfig*.json (no hits); npm run build exit 0 on TS 6.0.3 and on 7.0.2"
        status: pass
    human_judgment: false
  - id: D2
    description: "Alias pair installed correctly: node_modules/.bin/tsc is Version 7.0.2, tsc6 bin present, require('typescript') is 6.0.3 with createProgram a function, lock entries correctly named, npm audit signatures clean"
    requirement: "DEP-TS7"
    verification:
      - kind: other
        ref: "LOCK-ALIASES-OK node check; tsc --version; require('typescript') probe; npm audit signatures (1010 verified signatures, 310 attestations)"
        status: pass
    human_judgment: false
  - id: D3
    description: "TS7 type gate is real: deliberate TS2322 makes tsc -b exit 1, removing it makes tsc -b pass"
    requirement: "DEP-TS7"
    verification:
      - kind: other
        ref: "temp/phase-232/ts7/negative-control.txt (error TS2322, exit=1), then npx tsc -b exit 0, git status src clean"
        status: pass
    human_judgment: false
  - id: D4
    description: "Full frontend gate and Alpine Docker builder: lint, lint:cognitive finding count unchanged (41 before and after), vitest 4984/4984, knip, audit-ci, npm audit signatures; builder tsc Version 7.0.2 on node:24-alpine; full image builds"
    requirement: "DEP-TS7"
    verification:
      - kind: other
        ref: "cd frontend && npm run lint && npm test -- --run && npm run knip && npx audit-ci --config audit-ci.jsonc && npm audit signatures; docker build --target builder + docker run tsc --version + full docker build"
        status: pass
    human_judgment: false
  - id: D5
    description: "CHANGELOG [Unreleased] bullet, STATE.md alias note, SEED-162 cluster 3 resolved, Phase 217 D-11 superseded line (no em-dash in the new prose)"
    requirement: "DEP-TS7"
    verification:
      - kind: other
        ref: "plan Task 3 grep acceptance criteria; git show --stat of a51b7959d lists exactly the four files"
        status: pass
    human_judgment: false
  - id: D6
    description: "Editor experience: editors using the workspace TypeScript load TS6 while the build checks with TS7; TS7 editor support is the TypeScript (Native Preview) VS Code extension"
    requirement: "DEP-TS7"
    verification: []
    human_judgment: true
    rationale: "Editor behaviour is not asserted by any test; npm run build is the gate. The Native Preview extension is an unverified assumption (RESEARCH A2)."

duration: 8min
completed: 2026-10-04
status: complete
---

# Phase 232 Plan 04: TypeScript 7 via the side-by-side alias Summary

**`npm run build` now type-checks with the native TypeScript 7.0.2 compiler while typescript-eslint and eslint-plugin-sonarjs keep loading the TypeScript 6.0.3 JS API, using Microsoft's `typescript@npm:@typescript/typescript6` plus `@typescript/native@npm:typescript@7` pair, with the removed tsconfig options dropped and the gate proven real by a TS2322 negative control.**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-10-04T11:50Z
- **Completed:** 2026-10-04T11:59Z
- **Tasks:** 3 (1 tracer, 2 auto)
- **Files modified:** 8

## Accomplishments

- tsconfig cleanup first, on TS6 (valid there too): `baseUrl`, `ignoreDeprecations` and the 3-line `TODO(TS7)` comment removed from `frontend/tsconfig.json` and `frontend/tsconfig.app.json`; `"@/*": ["./src/*"]` untouched; `npm run build` exit 0 on TS 6.0.3. No `"*"` fallback mapping added.
- Alias install per D-01 with uninstall first (`npm uninstall typescript`, then `npm install -D "typescript@npm:@typescript/typescript6@^6.0.2" "@typescript/native@npm:typescript@^7.0.2"`), lock never hand-edited, build script unchanged. Lock names are right: `node_modules/typescript` is `@typescript/typescript6` 6.0.2, `@typescript/native` is `typescript` 7.0.2, `@typescript/old` is `typescript` 6.0.3.
- `node_modules/.bin/tsc --version` prints `Version 7.0.2`; `tsc6` exists; `require('typescript')` reports 6.0.3 with `createProgram` a function.
- Build timing: `tsc -b --force` on TS 6.0.3 took 13.0 s wall; the whole `npm run build` (TS7 `tsc -b` plus vite build) takes 4.6 s wall.
- Phase-close docs: CHANGELOG `[Unreleased]` / `### Changed` bullet (covers TypeScript 7, Sentry 11, vite-plugin-pwa 2 and the patched fast-uri; user-facing wording, no em-dash), STATE.md TS7-blocked bullet replaced by the alias note (Plan 03's "Sentry 11 deploy watch" bullet kept), SEED-162 status and Cluster 3 heading updated, Phase 217 D-11 annotated as superseded.

## Task Commits

1. **Task 1a: drop baseUrl and ignoreDeprecations from tsconfigs** - `b5a021ea4` (chore(ts))
2. **Task 1b: type-check with TypeScript 7 via the official side-by-side alias** - `7130cc9bf` (chore(deps))
3. **Task 2: gate proof (negative control, lint, cognitive, test, knip, audit, Docker)** - no commit, no tracked file changed
4. **Task 3: record TypeScript 7 adoption and the phase changelog entry** - `a51b7959d` (docs(232))

**Plan metadata:** docs(232-04) commit following this SUMMARY.

The tsconfig commit is an ancestor of the alias commit (checked with `git merge-base --is-ancestor`).

## Gate Evidence

- **Legitimacy (T-232-12):** `npm view typescript@7.0.2 repository.url` and `npm view @typescript/typescript6@6.0.2 repository.url` both `git+https://github.com/microsoft/TypeScript.git`; the latter's bin is `tsc6`, dependency `@typescript/old@npm:typescript@^6`. After install `npm audit signatures`: 1010 verified signatures, 310 verified attestations, no problems.
- **Negative control (T-232-13):** `src/__ts7_negative_control.ts` with `export const ts7NegativeControl: number = "not a number";` made `npx tsc -b` print `error TS2322: Type 'string' is not assignable to type 'number'.` and exit 1 (`temp/phase-232/ts7/negative-control.txt`). After deleting the file `npx tsc -b` exit 0, the file is gone and `git status --porcelain src` is empty.
- **Lint stack on the TS6 API:** `npm run lint` exit 0. `npm run lint:cognitive` reports `41 problems (41 errors, 0 warnings)` both before (baseline captured before any change) and after (`cognitive-before.txt` / `cognitive-after.txt`), so sonarjs still parses with the TS6 API. That script is report-only and exits 1 by design while findings exist.
- **Frontend gate:** vitest 4984 passed (4984); knip exit 0 (pre-existing `.css` configuration hint only); `audit-ci --config audit-ci.jsonc` "Passed npm security audit"; `npm audit signatures` clean.
- **Alpine Docker builder (T-232-14):** `docker build -f frontend/Dockerfile --target builder` succeeded (npm ci and npm run build on node:24-alpine); `docker run --rm ... node_modules/.bin/tsc --version` printed `Version 7.0.2`; the full image built too. Both tags removed afterwards.
- **Acceptance greps:** `"typescript": "npm:@typescript/typescript6@^6.0.2"` 1, `"@typescript/native": "npm:typescript@^7.0.2"` 1 (fixed-string match, the caret needs literal matching in this shell), `"build": "tsc -b && vite build"` 1.

## Editor note (Pitfall 7)

Editors that use the workspace TypeScript now load TS6 from `node_modules/typescript`, while the build checks with TS7, so an error message can read slightly differently between the two. `npm run build` is the gate. TS7 editor support is the "TypeScript (Native Preview)" VS Code extension (unverified assumption A2).

## Decisions Made

- Followed D-01 exactly; no deviation from the owner-approved alias arrangement.
- No application source needed changes: TS7 compiled the app with zero type errors, so the Task 1 step 6 stop-and-checkpoint path was not triggered and D-05's insurance (separate last wave) went unused.
- Unwind path (recorded in the commit body, STATE.md and SEED-162): when TS 7.1 ships a JS API and a typescript-eslint release supports it (typescript-eslint#10940), collapse back to a single `typescript` dependency.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. `npm install` printed the pre-existing allow-scripts warning for `protobufjs` and `stockfish` (unrelated), and an `npm audit` summary of the known dev-only shadcn advisories (SEED-188).

## Known Stubs

None.

## Threat Flags

None. No endpoints, auth paths or schema changes; the new packages are build-time devDependencies verified under T-232-12.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 232 has executed all four plans on branch `gsd/phase-232-frontend-major-dependency-upgrades`; not yet squash-merged to `main` and not deployed.
- Before the squash-merge the orchestrator runs the full root CLAUDE.md pre-merge gate (backend included; no backend code changed in this phase).
- After merge, expect Renovate dashboard #338 to drop typescript-7.x, vite-plugin-pwa-2.x, the Sentry major, fast-uri-4.x and js-yaml-5.x; watch the first CI run on `main` with `gh run watch <id> --exit-status`.
- `DEP-TS7` is a descriptive ID with no `.planning/REQUIREMENTS.md` entry (the file does not exist), so `requirements.mark-complete` is skipped.

## Self-Check: PASSED

- FOUND: commits b5a021ea4, 7130cc9bf, a51b7959d on gsd/phase-232-frontend-major-dependency-upgrades
- FOUND: alias entries in frontend/package.json and correctly named lock entries (LOCK-ALIASES-OK)
- FOUND: temp/phase-232/ts7/negative-control.txt with TS2322 and exit=1; src/__ts7_negative_control.ts absent
- FOUND: "TypeScript 7 adopted in Phase 232" and "Sentry 11 deploy watch" in .planning/STATE.md; "RESOLVED by Phase 232" in SEED-162; "Superseded 2026-10-04 by Phase 232 D-01" in 217-CONTEXT.md
- commits measured: `git rev-list --count a4708a3a2..HEAD` = 3 (before this SUMMARY commit)

---
*Phase: 232-frontend-major-dependency-upgrades*
*Completed: 2026-10-04*
