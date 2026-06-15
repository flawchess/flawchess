---
id: SEED-049
status: planted
planted: 2026-06-15
planted_during: v1.26 Full-Game Eval Pipeline (via /gsd-explore)
trigger_when: next UI polish / engagement push, or whenever you want a direct user-feedback channel before broadening the user base
scope: small (1 phase: ~1 backend table+endpoint, 1 frontend floating button + modal)
---

# SEED-049: In-app feedback button (likes / dislikes / suggestions, with page context)

## Why This Matters

FlawChess is free and still finding its shape. A low-friction in-app feedback channel is one
of the highest-leverage, cheapest things to add: it surfaces what users like, dislike, and want,
tied to the exact page they were on. Feedback without page context ("the chart is confusing") is
nearly useless; the captured URL tells you *which* surface. And because every user (including
guests) already has a `user_id` with a derivable platform username and game-based ELO, every
submission arrives with rich cohort context for free.

## Design Decisions (locked in this explore session)

- **Trigger surface: global floating button that auto-hides on scroll**, bottom-right on every
  page (not buried in nav/footer — discoverability drives volume). The captured URL genuinely
  varies by what the user was looking at. Mobile behavior, locked:
  - **Hide-on-scroll-down, show-on-scroll-up** so it never permanently covers a chart or list on
    dense pages. This is the key concession that makes a persistent button acceptable on mobile.
  - **Yields to open overlays** — when a filter/bookmark drawer, modal, or bottom sheet is open,
    the button hides (or sits behind it), never floats on top. Those drawers and the button want
    the same bottom-right corner; this resolves the collision.
  - **Respect iOS safe area** via `env(safe-area-inset-bottom)` so it clears the home indicator in
    installed PWA mode (no browser chrome to absorb it).
  - **Tap target ≥ 44×44pt** even if the visible icon is smaller; **mini/secondary styling**, not
    a full high-contrast primary FAB (feedback is a low-frequency action, not the page's main one).
  - Add **bottom scroll padding** to long containers so the last row never hides under the button.
  - **Considered alternative (rejected for v1):** a feedback entry buried in the nav/user menu is
    the more idiomatic mobile pattern for a low-frequency action and sidesteps the drawer collision
    entirely, but gets far less volume. Early on we want volume over tidiness, so the auto-hiding
    floating button wins. Revisit if the button proves noisy in practice.
- **Form: required freeform text + optional sentiment rating.** Required text guarantees real
  signal; optional rating keeps completion high while giving a coarse trend over time. Lean
  thumbs-up/down or a 3-point sentiment over 1–5 stars (star scales invite "what does 3 mean?"
  paralysis) — settle the exact control at design time.
- **Captured context:** `user_id` (always present, including guests), page URL, the freeform
  text, optional rating, timestamp. Username + platform + ELO bucket are derivable from the user
  record (do not denormalize unless query convenience warrants it).
- **Destinations: DB table *and* Sentry.**
  - New `feedback` table — durable, queryable via the prod MCP (`mcp__flawchess-prod-db__query`).
    Follow the project DB rules: `user_id` FK with `ondelete` policy, appropriate column types,
    `created_at`.
  - Sentry — the *push* signal so a submission pings you instead of sitting in a table nobody
    reads (the classic feedback failure mode). Attach **username + ELO bucket + platform as Sentry
    tags** so you can filter cohorts ("feedback from 2000+ rapid" vs "sub-1200 bullet") — they
    complain about completely different things. Sentry is a secondary sink here, not the system
    of record; the DB table is.
- **Light abuse guard.** Public-ish endpoint → add basic rate-limiting per user (and/or a max
  length on the text) so it can't be spammed. Keep it simple.

## Why guests are in scope (corrects the original framing)

The initial idea said "capture `user_id`", which seemed to exclude guests. It doesn't: guests
**have** `user_id`s (device-bound). They're arguably the most valuable feedback cohort — the
people who haven't committed and might bounce for a knowable reason. So feedback is accepted from
guests and authenticated users alike; no nullable-user / anonymous path needed.

## Relevant Files (starting points, verify at plan time)

- Backend: new `app/models/feedback.py` + Alembic migration; thin router under
  `routers/` (HTTP only) → service → repository, per the layering rules. Sentry capture via
  `sentry_sdk` with tags (`source="feedback"`, plus username/ELO/platform).
- Frontend: new floating-button component + submit modal; wire page URL from the router. Honor
  the browser-automation rules (`data-testid`, `aria-label` on the icon button, semantic
  `<button>`/`<form>`). Theme colors from `theme.ts`; primary submit = `variant="default"`.

## Recommended Next Step

Small and well-scoped. `/gsd-phase` to promote it to a ROADMAP phase when prioritized, then
`/gsd-plan-phase`. If the floating-button placement/feel wants exploring first (mobile drawer
overlap is the real design risk), a quick `/gsd-sketch` would de-risk it.
