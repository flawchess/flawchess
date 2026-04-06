# Requirements: FlawChess v1.8 Guest Access

**Defined:** 2026-04-06
**Core Value:** Users can determine their success rate for any opening position they specify, filtering by their own pieces only, regardless of how platforms categorize the opening

## v1.8 Requirements

Requirements for the Guest Access milestone. Each maps to a roadmap phase.

### Guest Session

- [ ] **GUEST-01**: User can click "Use as Guest" on the homepage to start using FlawChess without creating an account
- [ ] **GUEST-02**: Guest session persists across page refreshes via a 30-day Bearer JWT
- [ ] **GUEST-03**: Guest user has full platform access (import, explore, analyze, bookmark)
- [ ] **GUEST-04**: Guest user sees a persistent, non-dismissible indicator showing they are a guest
- [ ] **GUEST-05**: Guest session JWT is refreshed on each visit, resetting the 30-day expiry from last activity

### Account Promotion

- [ ] **PROMO-01**: Guest user can promote to a full account via email/password, preserving all imported data
- [ ] **PROMO-02**: Guest user can promote to a full account via Google SSO, preserving all imported data
- [ ] **PROMO-03**: Guest user sees a confirmation step before promotion showing what data will be preserved
- [ ] **PROMO-04**: After promotion, guest user is redirected back to the page they were on

### Guest UX

- [ ] **GUX-01**: Guest user sees an info box on the import page explaining benefits of signing up (cross-device access, no expiry risk)
- [ ] **GUX-02**: If a guest promotes with an email already registered, they see a clear error directing them to log in instead

### Security

- [ ] **SEC-01**: Existing OAuth callback patched for CVE-2025-68481 CSRF vulnerability (double-submit cookie)
- [ ] **SEC-02**: Guest creation endpoint has per-IP rate limiting to prevent abuse

## Future Requirements

Deferred to post-launch or future milestones. Tracked but not in current roadmap.

### Conversion Optimization

- **CONV-01**: Guest user sees an expiry countdown in the guest banner during the last 7 days
- **CONV-02**: Guest user sees a context-sensitive promotion prompt after first import completes
- **CONV-03**: Periodic cleanup job deletes guest accounts inactive for 40+ days

### v1.9 Advanced Analytics

- **ELO-01**: User sees Endgame ELO per (platform, time-control) combination
- **ELO-02**: User sees actual ELO, Endgame ELO, and gap in a breakdown table
- **ELO-03**: Combinations below minimum game threshold omitted; "Insufficient data" fallback
- **ELO-04**: Info popover explaining Endgame ELO methodology and caveats
- **ELO-05**: Endgame ELO timeline chart with color-matched paired lines
- **ELO-06**: Sidebar filters apply to breakdown table and timeline chart
- **OPN-01**: Opening risk per position (material imbalance variance at opening→middlegame transition)
- **OPN-02**: Opening drawishness per position (draw rate of games ending in opening phase)

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Read-only guest mode | Defeats the purpose — no imported games means no WDL stats, zero value experienced |
| Mandatory email capture before guest access | Disguised login wall; removes the "no commitment" promise |
| Dismissible guest banner | Users forget guest state, surprised when data disappears — trust violation |
| Silent data merge without confirmation | Shared-device account takeover risk |
| Guest session analytics / conversion metrics | Requires Umami event tracking; defer to post-launch |
| CookieTransport for guest sessions | Dual-transport complexity, OAuth redirect issues in Safari/Firefox ETP |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| GUEST-01 | Phase 48 | Pending |
| GUEST-02 | Phase 47 | Pending |
| GUEST-03 | Phase 47 | Pending |
| GUEST-04 | Phase 48 | Pending |
| GUEST-05 | Phase 47 | Pending |
| PROMO-01 | Phase 49 | Pending |
| PROMO-02 | Phase 50 | Pending |
| PROMO-03 | Phase 49 | Pending |
| PROMO-04 | Phase 49 | Pending |
| GUX-01 | Phase 49 | Pending |
| GUX-02 | Phase 49 | Pending |
| SEC-01 | Phase 47 | Pending |
| SEC-02 | Phase 47 | Pending |

**Coverage:**
- v1.8 requirements: 13 total
- Mapped to phases: 13
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-06*
*Last updated: 2026-04-06 after roadmap creation*
