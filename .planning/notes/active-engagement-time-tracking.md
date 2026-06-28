---
title: Active engagement-time tracking (minutes/day per user)
date: 2026-06-27
context: /gsd-explore — measuring how long users engage per day, building on the new user_activity table
---

# Active engagement-time tracking

## Goal

Get a rough per-user measure of **active engagement time per day** ("how long do users
actually use FlawChess"). Builds on the `user_activity` table introduced 2026-06-26
(DAU/WAU/MAU + retention). Does not need to be perfect.

## Existing state (starting point)

- `user_activity` (one row per `user_id` + UTC `activity_date`) currently stores
  `activity_count` = **distinct active hours that day (1–24)**, because the
  `LastActivityMiddleware` write is hour-throttled. This is already a free, coarse
  engagement proxy, but too crude for "minutes" (a 2-min visit and a 50-min session
  both count as "1 active hour").

## Decision: first-party focus-timer, NOT Umami

Measure active seconds **client-side via a focus/visibility timer**, flush to a new
per-user-per-day total in our own DB.

**Mechanic:**
- Timer accumulates only while `document.visibilityState === 'visible'` (Page Visibility
  API). Pause on `visibilitychange → hidden`, resume on visible — covers tab switches,
  minimize, and mobile backgrounding without threshold guessing.
- Flush accumulated seconds on client route change and on `pagehide`/hidden via
  `navigator.sendBeacon`, which also recovers most of the "last page" time. Losing the
  final page entirely is acceptable per the original ask.
- Store as `active_seconds` (**INTEGER**, not SmallInteger — SmallInteger caps at ~9.1h/day
  and a binge day could exceed it; a UTC day maxes at 86400s) on `user_activity`, assigned
  to the UTC day of the event (consistent with existing bucketing).
- Backend: a thin authenticated endpoint receives the delta and increments the daily total.
  **Clamp each delta server-side** (e.g. `[0, 30min]`) as cheap anti-abuse — the client
  reports the number, so it's spoofable.

**The 30-min navigation cap was dropped.** It was originally proposed to exclude
activity breaks, but a focus/visibility timer does that job directly and more truthfully.

## Key FlawChess-specific nuance

The **analysis board** is a page where a user legitimately sits for 30–40+ min studying one
position without navigating. Two consequences:

- A pure navigation-delta + 30-min-exclude/cap approach would silently discard or truncate
  these (your *most* engaged sessions). The focus timer counts them correctly — thinking
  while focused IS engagement.
- Therefore do **NOT** add an aggressive input-idle timeout (pause after N min of no
  mouse/keyboard): it would wrongly clip genuine deep-think sessions, the worst error for an
  analysis tool.
- The only residual inaccuracy is "tab left focused/visible but user physically walked away"
  (AFK on a second monitor). Optional **generous backstop**: pause after ~30 min of zero input
  events purely to bound the forgotten-tab-overnight tail — a sanity ceiling, not the primary
  signal. Can be skipped initially and added only if data looks inflated.

## Rejected alternatives

- **Umami `umami.identify()`** (per-feature attribution for logged-in users): rejected.
  Research findings:
  - Stable cross-session Distinct ID exists (Umami v2.18.0+), but persistence is
    **localStorage-based** → stitches per-browser only, must re-call on each login.
  - **Cannot reliably measure minutes**: duration = delta between first/last *pageview*
    event only. Single-page visits = 0 duration; last page uncounted; custom events and
    background-tab state don't factor in. **No native heartbeat** (feature request open, no
    maintainer movement; community ping hacks didn't move the number).
  - Good only for per-feature *usage counts*, which we don't need ("we don't need to go
    that far").
  - Privacy cost: a real account ID in localStorage is a stable personal identifier —
    meaningfully beyond our current anonymous Umami setup, would require a Privacy-page
    rewrite, and Umami's own docs say hash the ID.
- **Periodic heartbeat beacons (~every 15–30s)**: more accurate but more build than wanted;
  the focus timer gets us "rough minutes" far more cheaply.

## Privacy

- Far cleaner than the Umami-identify route: no localStorage identifier, no third party, no
  cross-system linkage; the Umami "cookie-free, no personal data shared" promise stays intact
  (Umami untouched).
- **Not zero implications**: `active_seconds` is behavioral data tied to an identifiable
  account → personal data under GDPR, but stays **first-party**. Same category as the existing
  `user_activity` table — opens no new privacy front; rides on whatever basis covers
  `user_activity`.
- **Loose end** (pre-existing, not blocking): the Privacy page copy only mentions Umami
  ("which pages are visited… no personal data"). First-party logged-in usage analytics
  (both `user_activity` and `active_seconds`) should get a one-line disclosure there.
