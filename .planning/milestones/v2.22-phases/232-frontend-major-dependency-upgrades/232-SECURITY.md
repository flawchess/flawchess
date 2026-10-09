---
phase: "232"
slug: "frontend-major-dependency-upgrades"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-10-04"
---

# Phase 232 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| npm registry → build / Docker | Newly published majors (vite-plugin-pwa 2, @sentry/react 11, TS7 alias packages) enter `npm ci` | Third-party code executed at build time and shipped in the bundle |
| Browser → Sentry ingest | @sentry/react 11 envelopes leave the user's browser | Error events: page URL, breadcrumbs, headers, user context (PII-sensitive) |
| Server → installed PWA clients | Generated `sw.js` controls cached shells on installed devices | Service worker routing (stale SW is hard to recover) |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-232-01 | Tampering | vite-plugin-pwa@2.0.0 | medium | mitigate | Publisher/provenance check recorded in 232-01-SUMMARY; lock pins `^2.0.0` resolved to 2.0.0; `npm audit signatures` 1010 verified | closed |
| T-232-02 | Denial of service | generated dist/sw.js | high | mitigate | sw.js/manifest/registerSW byte-identical vs 1.3.0 (232-01); 19 precache entries, 0 maia/engine (re-checked 2026-10-04); UAT test 2: register, offline shell, autoUpdate pass | closed |
| T-232-SC | Tampering | npm installs (all plans) | high | mitigate | Legitimacy gates per plan SUMMARYs; `npm audit signatures`: 1010 verified signatures, 310 attestations; lock only changed via npm install | closed |
| T-232-03 | Spoofing | fast-uri via ajv@8 | low | mitigate | Override `fast-uri: ^3.1.8` (package.json:83), resolves to 3.1.8 | closed |
| T-232-04 | Tampering | fast-uri / js-yaml majors | medium | mitigate | Overrides in-major (`^3.1.8`, `^4.3.1`); renovate.json packageRules disables majors for both; validator --strict OK | closed |
| T-232-05 | Tampering | renovate via npx | low | accept | See Accepted Risks AR-01 | closed |
| T-232-06 | Information disclosure | shadcn CLI dev advisories | low | accept | See Accepted Risks AR-02 (SEED-188) | closed |
| T-232-07 | Information disclosure | Sentry v11 dataCollection defaults | high | mitigate | instrument.ts:229-239 userInfo false, cookies false, httpBodies [], deny-listed headers/query params; plus page-URL scrub (WR-01, 2361acf86) and navigation-breadcrumb scrub (G-232-3, 814a3c44c); 32/32 mutation-proven tests; Chrome-extension envelope check (UAT test 3) | closed |
| T-232-08 | Repudiation | issue grouping | low | mitigate | `attachStacktrace: false` (instrument.ts:244), pinned by test | closed |
| T-232-09 | Denial of service | silent loss of error reporting | medium | mitigate | SDK transport delivery proven (event 256ca584…, FLAWCHESS-CH); UAT test 1 accepted by owner | closed |
| T-232-10 | Information disclosure | v11 span streaming URLs | low | mitigate | `urlQueryParams: { deny: SENTRY_PII_KEY_DENYLIST }`; STATE.md deploy watch on span volume | closed |
| T-232-11 | Tampering | @sentry/react 11.4.0 | medium | mitigate | Publisher continuity (sentry-bot) recorded in 232-03-SUMMARY; registry signatures verified | closed |
| T-232-12 | Tampering | TS7 alias packages (typosquat shape) | medium | mitigate | 232-04-SUMMARY:135 repository URLs = microsoft/TypeScript; lock alias names asserted (232-04-SUMMARY:117) | closed |
| T-232-13 | Elevation of privilege | type gate becoming a no-op | medium | mitigate | tsc 7.0.2 on PATH; TS2322 negative control → exit 1 (232-04) | closed |
| T-232-14 | Denial of service | Alpine Docker build | medium | mitigate | Builder + full image built on node:24-alpine, tsc 7.0.2 inside builder (232-04) | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-01 | T-232-05 | Pinned official renovatebot package run once from the npx cache for config validation; never added to package.json or the lockfile | plan 232-02 (owner-approved plan) | 2026-10-04 |
| AR-02 | T-232-06 | 6 high advisories are in shadcn CLI devDependencies only, not in the shipped bundle (audit-ci skip-dev); tracked in SEED-188 | plan 232-02 (owner-approved plan) | 2026-10-04 |

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-10-04 | 16 | 16 | 0 | /gsd-secure-phase 232 (orchestrator, ASVS L1 short-circuit) |

## Security Audit 2026-10-04
| Metric | Count |
|--------|-------|
| Threats found | 16 |
| Closed | 16 |
| Open | 0 |

Note: UAT surfaced one issue beyond the plan-time register: the page query string leaked through Sentry navigation breadcrumbs (pre-existing under v10). It was fixed in 814a3c44c and recorded under T-232-07.

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-10-04
