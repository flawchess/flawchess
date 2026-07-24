---
phase: 185
slug: bots-roster-transpose-win-stars
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: 2026-07-22
---

# Phase 185 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| client → API (POST /bots/games) | client-supplied `persona_id` crosses here and is persisted | persona identifier string, low sensitivity |
| client → API (GET /bots/persona-wins) | authenticated read of per-user win aggregation | per-user win counts keyed by persona_id |
| API → DB | SQLAlchemy bound-parameter writes/reads | persona_id, user_id, game results |
| API → client (persona-wins response) | per-persona win dict rendered in PersonaCard | persona_id keys + integer counts |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-185-01 | Tampering/DoS | StoreBotGameRequest.persona_id | medium | mitigate | `Field(min_length=1, max_length=30)` at the Pydantic boundary (app/schemas/bots.py:57) — overlong or empty values 422 before SQL (WR-03 tightened min_length) | closed |
| T-185-02 | Elevation/Info Disclosure | GET /bots/persona-wins | high | mitigate | user_id derived only from `current_active_user` JWT (app/routers/bots.py:44-47); no user_id query/path param; repository scoped by `Game.user_id == user_id` | closed |
| T-185-03 | Injection | count_wins_by_persona / persona_id write | low | mitigate | SQLAlchemy `select()` with bound parameters + typed `String(30)` column (app/models/game.py:187); no string interpolation into SQL | closed |
| T-185-04 | Info Disclosure | persona_id echoed as JSON dict key in aggregation response | low | accept | value is length-bounded and rendered downstream only as React JSX text/dict key (auto-escaped); no server-side sink | closed |
| T-185-05 | Info Disclosure | PersonaGrid presentational transpose | low | accept | no new trust boundary — re-layout of the compile-time-static `PERSONA_REGISTRY`; no user-supplied input reaches this code path | closed |
| T-185-06 | Info Disclosure/XSS | persona_id as dict key rendered in PersonaCard/aria-label | low | accept | rendered only as React JSX text/aria-label (auto-escaped); no `dangerouslySetInnerHTML` in bots components (grep-verified); never used to build DOM ids/selectors from server data | closed |
| T-185-07 | Tampering | toStoreRequest persona_id mapping | low | mitigate | client value not trusted beyond its own display; server re-validates at the Pydantic boundary (T-185-01) before persistence | closed |
| T-185-SC | Tampering | npm/pip/cargo installs | low | accept | no new packages introduced this phase (RESEARCH Package Legitimacy Audit skip-condition met) | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| R-185-01 | T-185-04 | persona_id in response is length-bounded, client renders via auto-escaping JSX only | plan-time threat model (185-01-PLAN.md) | 2026-07-22 |
| R-185-02 | T-185-05 | pure client-side re-layout of static registry, no input surface | plan-time threat model (185-02-PLAN.md) | 2026-07-22 |
| R-185-03 | T-185-06 | React JSX auto-escaping covers all persona_id render sites; no innerHTML sinks | plan-time threat model (185-03-PLAN.md) | 2026-07-22 |
| R-185-04 | T-185-SC | no new dependencies introduced in any plan of this phase | plan-time threat model (all plans) | 2026-07-22 |

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-07-22 | 8 | 8 | 0 | /gsd-secure-phase (L1 grep-depth verification, short-circuit: plan-time register, threats_open 0) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-07-22
