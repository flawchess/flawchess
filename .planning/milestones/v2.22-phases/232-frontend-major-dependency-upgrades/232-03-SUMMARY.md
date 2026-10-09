---
phase: 232-frontend-major-dependency-upgrades
plan: 03
subsystem: infra
tags: [frontend, deps, sentry, privacy, telemetry, tdd]

requires:
  - phase: 232-02
    provides: override floors settled before the Sentry major, so the lock diff for the bump is attributable to Sentry alone
provides:
  - "@sentry/react 11.4.0 (react, browser, core all 11.4.0, no 10.x copy)"
  - v10-equivalent privacy baseline pinned in Sentry.init (dataCollection + attachStacktrace false), mutation-proven
  - SEED-189 capturing the missing source-map generation and upload
  - STATE.md deploy watch for v11 span volume
affects: [232-04]

plan_head_before: e5d6675b696ccb4b0726d8947c5a03cb3660e399
plan_head_after: 464f86ecae2edd1faefa8f328372f3aa5fc3eba0

actuals:
  tokens: 2300
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "A major bump whose defaults flip silently pins the old behaviour explicitly in the same commit and pins it again with a test that is mutation-proven"

key-files:
  created:
    - .planning/seeds/SEED-189-sentry-source-map-upload.md
  modified:
    - frontend/package.json
    - frontend/package-lock.json
    - frontend/src/instrument.ts
    - frontend/src/__tests__/instrument.beforeSend.test.ts
    - .planning/STATE.md

key-decisions:
  - "D-02: Sentry.init pins a v10-equivalent dataCollection (userInfo false, cookies false, httpHeaders request/response deny lists, httpBodies [], urlQueryParams deny list) plus attachStacktrace false, so collection does not widen and Privacy.tsx / frontend/CLAUDE.md stay untouched"
  - "D-03: live dev smoke approved; v11 event shape accepted by the flawchess Sentry project (FLAWCHESS-CH, resolved afterwards). Source-map resolution deliberately not checked, captured as SEED-189"
  - "Sentry span-volume change after release is a watched item in STATE.md, not a code change in this plan"

requirements-completed: [DEP-SENTRY11]

coverage:
  - id: D1
    description: "@sentry/react ^11.4.0; react, browser and core resolve to 11.4.0 with no leftover 10.x; publisher continuity (sentry-bot) and npm audit signatures pass"
    requirement: "DEP-SENTRY11"
    verification:
      - kind: other
        ref: "npm ls @sentry/react @sentry/browser @sentry/core (only 11.4.0), npm view _npmUser, npm audit signatures"
        status: pass
    human_judgment: false
  - id: D2
    description: "Test 'keeps the v10 privacy baseline under Sentry v11 (dataCollection + attachStacktrace, D-02)' RED before the bump, GREEN after, and mutation-proven twice"
    requirement: "DEP-SENTRY11"
    verification:
      - kind: test
        ref: "frontend/src/__tests__/instrument.beforeSend.test.ts"
        status: pass
    human_judgment: false
  - id: D3
    description: "Full frontend gate: lint, build (tsc -b + vite), vitest 4984/4984, knip, audit-ci, npm audit signatures; no removed v11 API (beforeSendTransaction, ignoreTransactions) in source"
    requirement: "DEP-SENTRY11"
    verification:
      - kind: other
        ref: "cd frontend && npm run lint && npm run build && npm test -- --run && npm run knip && npx audit-ci --config audit-ci.jsonc && npm audit signatures"
        status: pass
    human_judgment: false
  - id: D4
    description: "Live dev event reaches Sentry with tag, context, no IP, no cookies, headers User-Agent only (D-03)"
    requirement: "DEP-SENTRY11"
    verification:
      - kind: other
        ref: "orchestrator-run browser smoke, issue FLAWCHESS-CH, event f7dcfa2a1ce741778148b01b78f69ba5"
        status: pass
    human_judgment: true
    rationale: "The SDK's own transport could not be exercised in the owner's browser (Sentry hosts blocked by the profile); the byte-exact envelope was relayed with curl. See Deviations."
  - id: D5
    description: "SEED-189 dormant seed and STATE.md deploy watch recorded"
    requirement: "DEP-SENTRY11"
    verification:
      - kind: other
        ref: "ls .planning/seeds/SEED-189-*.md; grep 'Sentry 11 deploy watch' .planning/STATE.md"
        status: pass
    human_judgment: false
  - id: D6
    description: "Post-release: span volume after v11 span streaming stays within Sentry quota at tracesSampleRate 0.1"
    requirement: "DEP-SENTRY11"
    verification: []
    human_judgment: true
    rationale: "Observable only after the release ships; tracked as a STATE.md deploy watch."

duration: n/a
completed: 2026-10-04
status: complete
---

# Phase 232 Plan 03: Sentry 11 with a pinned v10 privacy baseline Summary

**@sentry/react bumped 10 -> 11.4.0 with an explicit v10-equivalent `dataCollection` and `attachStacktrace: false`, proven by a test that fails when either is removed, and confirmed by a live dev event carrying no IP, no cookies and User-Agent-only headers.**

## Accomplishments

- v11 compiles against our code unchanged, but its defaults flipped: unset `dataCollection` collects user IP, cookies, bodies, headers and query params, and `attachStacktrace` adds synthetic minified stacks. Both are now pinned in `Sentry.init`, each with a why-comment, in the same commit as the bump.
- `SENTRY_PII_KEY_DENYLIST = ["forwarded", "-ip", "remote-", "via", "-user"]` feeds the request/response header and query deny lists.
- Lock resolves `@sentry/react`, `@sentry/browser`, `@sentry/core`, `browser-utils`, `feedback`, `replay`, `replay-canvas` to 11.4.0 only. The sole non-@sentry lock change is `web-vitals` (new v11 browser dependency).
- Privacy.tsx and frontend/CLAUDE.md are untouched, since collection does not widen.
- Dormant SEED-189 records that production ships no source maps (no `.map` in `dist/assets`, no sentry-cli/token/upload anywhere in deploy tooling, no `release` on init). STATE.md carries a single deploy-watch bullet for span volume.

## Task Commits

1. **Task 1a (RED): pin the v10 privacy baseline** - `5eaae44f1` (test(232-03))
2. **Task 1b (GREEN): bump @sentry/react to 11.x with explicit baseline** - `0685006d1` (chore(deps))
3. **Task 2: source-map seed and span-volume deploy watch** - `464f86eca` (docs(232))
4. **Task 3: live dev smoke (checkpoint:human-verify)** - verification only, no commit of its own

**Plan metadata:** docs(232-03) commit following this SUMMARY.

## TDD Gate Compliance

- **RED:** `5eaae44f1` added the test. Run before the bump it failed only on the planned assertion, `AssertionError: expected undefined to be false` at `dataCollection?.userInfo` (test.ts:415); 1 failed / 27 passed. Valid RED (the assertion, not an import or setup error).
- **GREEN:** `0685006d1`. 28/28 pass including `keeps the v10 privacy baseline under Sentry v11 (dataCollection + attachStacktrace, D-02)`. The test commit is an ancestor of the bump commit.
- **REFACTOR:** none needed.

### Mutation proofs

Performed by copying the file aside and restoring byte-identical (checked with `cmp`); `git stash` is prohibited in this environment.

| Mutation | Result |
|----------|--------|
| Remove both `dataCollection` and `attachStacktrace` from `instrument.ts` | New test fails `expected undefined to be false`, 1 failed / 27 passed |
| Remove only `attachStacktrace` | Fails at test.ts:427:40 `expect(initCall?.attachStacktrace).toBe(false)`, 1 failed / 27 passed |
| Restored | 28/28 |

## Legitimacy and Gate Evidence

- `@sentry/react`, `@sentry/browser`, `@sentry/core` 11.4.0: `_npmUser` sentry-bot (same as 10.73.0), repository `git://github.com/getsentry/sentry-javascript.git`, no install scripts. `npm audit signatures`: 1007 verified signatures, 310 attestations, 0 problems.
- v11 shape confirmed in the installed types: `CollectBehavior = boolean | {allow} | {deny}`; the HttpContext integration reads only User-Agent and Referer, filtered by `dataCollection.httpHeaders.request`.
- Gate from `frontend/` (all exit 0): lint, build (`tsc -b` + vite), vitest 4984/4984, knip (pre-existing `.css` hint only), audit-ci, `npm audit signatures`. Removed-API scan for `beforeSendTransaction|ignoreTransactions`: no hits.
- Acceptance greps: `"@sentry/react": "^11.4.0"` 1; `dataCollection:` 1; `attachStacktrace: false` 1; `SENTRY_PII_KEY_DENYLIST` 4.

## Task 3: Live dev smoke (D-03), approved

Run by the orchestrator against the dev server on port 5174 (5173 was occupied by the owner). The repo-root env sets no `VITE_SENTRY_DSN` for dev, so the server was restarted with the public DSN taken from the live flawchess.com bundle (project 4511084868272208, ingest host `o4511084502450176.ingest.de.sentry.io`); environment stayed `development`.

- **SDK state in the app module:** `SDK_VERSION` 11.4.0, client defined, `getOptions()` shows `attachStacktrace` false and `dataCollection` exactly the committed baseline.
- **Envelope** captured via `beforeEnvelope` after `captureException(new Error('phase232-sentry-v11-smoke'))` with tag `source=phase232-smoke` and context `phase232.plan=sentry-v11`: single event item; sdk 11.4.0; `sdk.settings.infer_ip` "never"; `user` null (no `ip_address`); no `request.cookies`; `request.headers` keys `[User-Agent]` only; tag and context intact; environment development; 1 stack frame.
- **Sentry UI:** issue FLAWCHESS-CH (event `f7dcfa2a1ce741778148b01b78f69ba5`), environment development, tag and context present, stack trace present, Chrome 154 and Linux contexts present, no IP address shown. Only a coarse `user.geo` (CH, Zurich) appears, matching production v10 events (e.g. FLAWCHESS-24 shows `user.geo` GB with no IP), so there is no privacy widening. FLAWCHESS-CH was resolved afterwards with a comment.
- Dev server and receiver stopped.

## Deviations from Plan

### Environmental (not a code deviation)

**Task 3: the SDK's own POST could not reach Sentry from the owner's browser.**
- **Cause:** the owner's Chrome profile blocks every Sentry host from the page (ingest, de.sentry.io and browser.sentry-cdn.com all "Failed to fetch"; a GitHub control fetch succeeded). The SDK's transport reported status 503.
- **Not caused by v11:** curl probes from the same machine got 200 for every Origin (localhost:5174, localhost:5173, flawchess.com) and the CORS preflight is correct.
- **Workaround:** the byte-exact v11 envelope captured in the page (4848 bytes) was relayed to a local receiver and forwarded unchanged to the ingest endpoint with curl (Origin localhost:5174), HTTP 200.
- **What this proves and does not prove:** it proves the v11 event shape is accepted and processed with tag, context and privacy settings intact. It does not exercise the SDK transport inside this browser. Transport code is unchanged in kind between v10 and v11, and production v10 events arrive normally.

Tasks 1 and 2: none. Plan executed as written (file copy instead of `git stash` for the mutation proofs, as stash is prohibited).

## Issues Encountered

None beyond the above. `npm install` printed the pre-existing allow-scripts warning for `protobufjs` and `stockfish` (unrelated).

## Known Stubs

None.

## Threat Flags

None. No new endpoints, auth paths or schema changes; the change narrows to the previous collection surface rather than widening it.

## User Setup Required

None.

## Next Phase Readiness

- Ready for 232-04 (TypeScript 7).
- After the release that ships Phase 232, check span usage in Sentry Stats and lower `VITE_SENTRY_TRACES_SAMPLE_RATE` in `.prod.env` if quota climbs (STATE.md deploy watch).
- `DEP-SENTRY11` is a descriptive ID with no `.planning/REQUIREMENTS.md` entry, so `requirements.mark-complete` is skipped.

## Self-Check: PASSED

- FOUND: commits 5eaae44f1, 0685006d1, 464f86eca on gsd/phase-232-frontend-major-dependency-upgrades
- FOUND: `"@sentry/react": "^11.4.0"` in frontend/package.json; `dataCollection` and `attachStacktrace: false` in frontend/src/instrument.ts
- FOUND: .planning/seeds/SEED-189-sentry-source-map-upload.md
- FOUND: "Sentry 11 deploy watch" bullet in .planning/STATE.md
- commits measured: `git rev-list --count e5d6675b6..HEAD` = 3

---
*Phase: 232-frontend-major-dependency-upgrades*
*Completed: 2026-10-04*
