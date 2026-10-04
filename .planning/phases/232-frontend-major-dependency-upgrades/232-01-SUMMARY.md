---
phase: 232-frontend-major-dependency-upgrades
plan: 01
subsystem: infra
tags: [frontend, deps, pwa, service-worker, workbox, vite-plugin-pwa]

requires:
  - phase: 231
    provides: clean frontend gate baseline (lint, build, vitest, knip, audit-ci allowlist [])
provides:
  - vite-plugin-pwa 2.0.0 (^2.0.0 in package.json, lock pinned 2.0.0) with a proven-inert service worker
  - before/after artifact evidence that installed PWAs receive no service-worker change
affects: [232-02 overrides re-check, 232-03, 232-04]

plan_head_before: 81710d583831103bd912eca89a3a038c0cc5cc23
plan_head_after: 57c802729347029d8684af562e0a27d4bf3cd979

actuals:
  tokens: 500
  tasks: 2
  commits: 1

tech-stack:
  added: []
  patterns:
    - "Prove a service-worker-affecting dependency bump inert by cmp of generated sw.js/manifest/registerSW.js plus a precache list diff, then a real-browser lifecycle smoke"

key-files:
  created: []
  modified:
    - frontend/package.json
    - frontend/package-lock.json

key-decisions:
  - "No blocking-human package-legitimacy checkpoint for vite-plugin-pwa 2.0.0: pre-existing dependency, automated identity gate passed (Phase 217 precedent)"

requirements-completed: [DEP-PWA2]

coverage:
  - id: D1
    description: "vite-plugin-pwa 2.0.0 installed; generated sw.js, manifest.webmanifest and registerSW.js byte-identical to the 1.3.0 build; precache list identical (19 entries) with maia/ and engine/ excluded"
    requirement: "DEP-PWA2"
    verification:
      - kind: other
        ref: "cmp v1/v2 sw.js, manifest.webmanifest, registerSW.js; diff v1/v2 precache.txt (temp/phase-232/pwa/)"
        status: pass
      - kind: other
        ref: "cd frontend && npm run lint && npm run build && npm test -- --run && npm run knip && npx audit-ci --config audit-ci.jsonc"
        status: pass
    human_judgment: false
  - id: D2
    description: "Real-browser lifecycle on the 2.0.0 preview build: SW activated with correct scope, precache count equals precache.txt, zero maia/engine cache URLs, app shell renders offline"
    requirement: "DEP-PWA2"
    verification:
      - kind: manual_procedural
        ref: "Task 2 orchestrator-run Chrome smoke on vite preview --port 4173"
        status: pass
    human_judgment: false

duration: 8min
completed: 2026-10-04
status: complete
---

# Phase 232 Plan 01: vite-plugin-pwa 1 -> 2 Summary

**vite-plugin-pwa bumped 1.3.0 -> 2.0.0 with a byte-identical generated service worker, manifest and register script, an unchanged 19-entry precache list excluding maia/ and engine/, a green frontend gate, and a real-browser activation and offline-shell smoke.**

## Performance

- **Duration:** ~8 min (including the browser checkpoint)
- **Started:** 2026-10-04T11:23:15Z
- **Completed:** 2026-10-04T11:32Z
- **Tasks:** 2 (1 tracer commit, 1 verification-only checkpoint)
- **Files modified:** 2

## Accomplishments

- vite-plugin-pwa is on 2.0.0 (`^2.0.0` in package.json, lock pins 2.0.0). The upstream 2.0.0 change is only `engines.node >=20.19.0` plus allowing `@vite-pwa/assets-generator ^2`; `.nvmrc` is 24 (node v24.19.0), so it is satisfied.
- Proved the upgrade inert for installed clients: `sw.js`, `manifest.webmanifest` and `registerSW.js` are byte-identical (`cmp`) between the 1.3.0 and 2.0.0 builds, so no service-worker update is triggered.
- Precache lists identical: 19 entries / 2721.03 KiB, no `maia/`, `engine/`, `.html`, `.wasm` or `.onnx` entry.
- workbox-build stays 7.4.1, so the fast-uri / ajv consumer graph Plan 02 re-checks is unchanged.
- Full frontend gate green; real-browser smoke approved (Task 2).

## Task Commits

1. **Task 1 (tracer): vite-plugin-pwa 1.3.0 -> 2.0.0** - `57c802729` (chore(deps))
2. **Task 2: Browser smoke of the 2.x service worker** - verification-only checkpoint, no commit (orchestrator-run, approved)

**Plan metadata:** docs(232-01) commit following this SUMMARY (hash recorded in git log).

## Task 1 Evidence

**Pre-install identity gate (T-232-01), all clean, no blocking-human escalation:**
- `vite-plugin-pwa@2.0.0` `_npmUser.name` "GitHub Actions" (same as 1.3.0)
- repository `git+https://github.com/vite-pwa/vite-plugin-pwa.git`
- provenance predicate `https://slsa.dev/provenance/v1`
- `engines.node >=20.19.0`; no `preinstall` / `install` / `postinstall` scripts

**Install:** `npm install -D vite-plugin-pwa@2.0.0`. Lock diff is 12 lines: version/resolved/integrity, `engines.node` `>=16.0.0` -> `>=20.19.0`, and the `@vite-pwa/assets-generator` peer range gaining `|| ^2.0.0`. `npm ls --depth=0` before/after differs only in the vite-plugin-pwa line.

**Artifact comparison (1.3.0 vs 2.0.0 builds):**

| Artifact | Result |
|----------|--------|
| dist/sw.js | byte-identical (cmp) |
| dist/manifest.webmanifest | byte-identical (cmp) |
| dist/registerSW.js | byte-identical (cmp) |
| precache list (`url:"..."`, sorted) | identical, 19 entries, 2721.03 KiB |
| maia/, engine/, .html, .wasm, .onnx entries | none |

**Other checks:** `npm audit signatures` exit 0 (1006 verified registry signatures, 310 verified attestations). Gate: lint 0, build (`tsc -b` + vite) 0, vitest 4983/4983, knip 0 (pre-existing `.css` config hint only), audit-ci 0 with allowlist `[]`.

Evidence files (gitignored): `temp/phase-232/pwa/{v1,v2}/`, `ls-before.txt`, `ls-after.txt`.

## Task 2 Browser Smoke (orchestrator-run, Chrome automation, `vite preview --port 4173`, 2.0.0 build)

- Started clean: unregistered 1 stale registration and deleted 3 stale caches from an earlier session on localhost:4173 before the first load.
- Service worker: state `activated`, scriptURL `http://localhost:4173/sw.js`, scope `http://localhost:4173/`, page controlled.
- `caches.keys()`: `workbox-precache-v2-http://localhost:4173/` (19 entries, equals the precache.txt line count) and `html-shell` (1 entry after reload).
- maia/engine scan across all caches: 0 URLs.
- Offline shell (server stopped, curl confirmed connection refused): navigating to `http://localhost:4173/library/import` rendered the full FlawChess app shell from `html-shell` (title, nav and Import page text present, SW-controlled).
- After restarting the server and reloading: no console messages, registration active=activated, waiting=false, installing=false (no SW registration or update errors).
- Preview server stopped afterwards.
- All four acceptance criteria met.

**Observation (pre-existing, not a regression):** an offline navigation to `/` showed Chrome's error page. The NetworkFirst `html-shell` cache is keyed per URL, and the only cached shell was `/library/import` (the app client-redirects `/` to `/library/import`, so the reload cached that URL). `sw.js` is byte-identical to 1.3.0, so this behavior predates the upgrade.

## Files Created/Modified

- `frontend/package.json` - `vite-plugin-pwa` `^1.3.0` -> `^2.0.0`
- `frontend/package-lock.json` - lock entry resolves to 2.0.0 (12-line diff)

## Decisions Made

- No blocking-human legitimacy checkpoint for 2.0.0 (pre-existing dependency, `too-new` was the only `[SUS]` signal, automated identity gate and `npm audit signatures` both passed), following the Phase 217 precedent and the deviation recorded in the plan.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. The pre-existing npm allow-scripts warning for `protobufjs@7.6.6` and `stockfish@18.0.8` postinstall scripts is unrelated to this plan.

## Known Stubs

None.

## Threat Flags

None. No new network endpoints, auth paths or schema changes; the generated service worker is byte-identical.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 02 (fast-uri override floor, js-yaml stays 4.x, Renovate rule) can proceed; workbox-build is unchanged at 7.4.1 so the consumer graph is the same as at planning time.
- Note for the phase deploy: installed PWAs get no service-worker update from this plan.

## Self-Check: PASSED

- FOUND: commit 57c802729 on gsd/phase-232-frontend-major-dependency-upgrades
- FOUND: frontend/package.json contains `"vite-plugin-pwa": "^2.0.0"`; frontend/package-lock.json contains `vite-plugin-pwa-2.0.0.tgz`
- FOUND: temp/phase-232/pwa/v1 and v2 evidence, precache.txt 19 lines
- commits measured: `git rev-list --count 81710d583..HEAD` = 1

---
*Phase: 232-frontend-major-dependency-upgrades*
*Completed: 2026-10-04*
