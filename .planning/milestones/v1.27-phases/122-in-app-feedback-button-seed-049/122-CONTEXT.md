# Phase 122: In-app feedback button (SEED-049) - Context

**Gathered:** 2026-06-15
**Status:** Ready for planning
**Source:** Synthesized from [SEED-049](../../seeds/closed/SEED-049-in-app-feedback-button.md) (decisions locked 2026-06-15 explore session)

<domain>
## Phase Boundary

Deliver a low-friction in-app feedback channel so any user (guests included) can submit
likes / dislikes / suggestions tied to the exact page they were on.

In scope:
- A global floating feedback button (bottom-right, auto-hides on scroll-down, yields to open
  overlays, iOS safe-area aware) present on every page.
- A submit modal: required freeform text + optional coarse sentiment rating.
- Backend persistence to a new `feedback` table via the router → service → repository layering.
- A Sentry push signal per submission, tagged with username / ELO bucket / platform.
- A light per-user abuse guard (rate-limit + max text length).

Out of scope:
- Any admin UI / dashboard for reading feedback (read via prod MCP / Sentry for now).
- Email or other notification sinks beyond Sentry.
- Threaded replies, status tracking, or feedback voting.
- Denormalizing username/platform/ELO onto the feedback row (derive from the user record).
</domain>

<decisions>
## Implementation Decisions

### D-01 — Trigger surface: global auto-hiding floating button
Bottom-right floating button on every page (not buried in nav/footer — discoverability drives
volume). The captured URL genuinely varies by what the user was looking at. The idiomatic
nav/user-menu entry was **considered and rejected for v1**: it gets far less volume; early on we
want volume over tidiness. Revisit if the button proves noisy.

### D-02 — Mobile button behavior (locked)
- **Hide-on-scroll-down, show-on-scroll-up** so it never permanently covers a chart or list on
  dense pages.
- **Yields to open overlays** — when a filter/bookmark drawer, modal, or bottom sheet is open, the
  button hides (or sits behind it), never floats on top. The button and those drawers share the
  bottom-right corner; this resolves the collision.
- **Respect iOS safe area** via `env(safe-area-inset-bottom)` so it clears the home indicator in
  installed PWA mode.
- **Tap target ≥ 44×44pt** even if the visible icon is smaller.
- **Mini / secondary styling**, NOT a full high-contrast primary FAB (feedback is a low-frequency
  action). Note: this is the floating trigger; the modal's submit button is primary (see D-06).
- Add **bottom scroll padding** to long containers so the last row never hides under the button.

### D-03 — Form: required freeform text + optional sentiment
- Freeform text is **required** (guarantees real signal).
- Sentiment rating is **optional** (keeps completion high, gives a coarse trend).
- Use thumbs-up/down or a **3-point sentiment**, NOT 1–5 stars (star scales invite "what does 3
  mean?" paralysis). Settle the exact control at UI-design time (UI-SPEC).

### D-04 — Captured context
Persist: `user_id` (always present, including guests), page URL, freeform text, optional
sentiment rating, `created_at`. Username + platform + ELO bucket are **derivable from the user
record** — do NOT denormalize onto the feedback row unless query convenience clearly warrants it.

### D-05 — Destinations: DB table AND Sentry
- New `feedback` table — durable, queryable via prod MCP (`mcp__flawchess-prod-db__query`). Follow
  the project DB rules: `user_id` FK with explicit `ondelete` policy, appropriate column types,
  `created_at`. This is the system of record.
- Sentry — the **push** signal so a submission pings the team instead of rotting in a table.
  Capture via `sentry_sdk` with `source="feedback"` plus **username + ELO bucket + platform as
  Sentry tags** (enables cohort filtering, e.g. "2000+ rapid" vs "sub-1200 bullet"). Sentry is a
  secondary sink, not the system of record. Note: a successful user submission is not an exception
  — use the appropriate non-exception Sentry signal (e.g. `capture_message` / message event), and
  do NOT embed variable data in the message string (use tags/context per the Sentry grouping rules).

### D-06 — Frontend conventions
- Browser-automation rules: `data-testid` on the button, modal, text input, sentiment control, and
  submit; `aria-label` on the icon-only floating button; semantic `<button>` / `<form>`.
- Theme colors from `theme.ts`; the modal's primary submit uses `variant="default"` (brand brown).
- Wire the page URL from the router (current location), captured at submit time.
- Apply the same behavior to mobile and desktop surfaces.

### D-07 — Abuse guard (keep it simple)
Public-ish endpoint → add a basic **per-user rate limit** and/or a **max text length** so it can't
be spammed. Keep it simple; do not over-engineer (no CAPTCHA, no IP throttling for v1).

### D-08 — Guests are in scope
Guests have device-bound `user_id`s and are arguably the most valuable feedback cohort. Feedback is
accepted from guests and authenticated users alike — no nullable-user / anonymous code path needed.

### Claude's Discretion
- Exact `feedback` table column types/lengths and index choices (follow DB rules).
- Exact sentiment control (thumbs vs 3-point) and its enum/storage encoding — settle in UI-SPEC.
- Rate-limit window/threshold values and max text length (pick sensible named constants).
- Component file structure, hook names, and where the floating button mounts in the app shell.
- Endpoint path/shape and Pydantic schema names (follow the router prefix convention).
- How "open overlay" state is detected for the yield-to-overlay behavior.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Seed (source of locked decisions)
- `.planning/seeds/SEED-049-in-app-feedback-button.md` — full rationale + locked decisions.

### Project rules (CLAUDE.md sections)
- `CLAUDE.md` → **Architecture / Backend Layout / Router Convention** — routers thin (HTTP only),
  business logic in services, DB access in repositories; `APIRouter(prefix=...)` with relative paths.
- `CLAUDE.md` → **Database Design Rules** — mandatory FK with explicit `ondelete`, appropriate
  column types, natural-key uniqueness where relevant.
- `CLAUDE.md` → **Error Handling & Sentry (Backend Rules)** — `sentry_sdk` usage, tags vs context,
  never embed variables in message strings (preserves grouping), skip trivial/expected exceptions.
- `CLAUDE.md` → **Frontend / Browser Automation Rules** — `data-testid`, `aria-label`, semantic
  HTML, `theme.ts` color constants, primary = `variant="default"`, min font `text-sm`, mobile-first.
- `CLAUDE.md` → **Coding Guidelines** — no magic numbers, type safety (`Literal` for fixed sets /
  Pydantic v2), function size limits.

### Tech stack anchors
- Backend: FastAPI + SQLAlchemy 2.x async + Alembic + asyncpg + Pydantic v2 + FastAPI-Users.
- Frontend: React 19 + TS + Vite, TanStack Query, Tailwind, shadcn `Button`/dialog components.
</canonical_refs>

<specifics>
## Specific Ideas

- ELO bucket derivation should reuse the project's existing rating-bucket logic (400-wide buckets
  anchored at 800/1200/1600/2000/2400) if one exists; verify at plan time rather than inventing a
  new bucketing scheme.
- The floating button competes for the bottom-right corner with existing filter/bookmark drawers —
  the yield-to-overlay behavior must be verified against those actual components.
- Sentiment storage should use a typed `Literal` / enum, not a bare string.
</specifics>

<deferred>
## Deferred Ideas

- Admin/read UI for feedback (use prod MCP + Sentry for now).
- Denormalizing cohort fields onto the feedback row (only if query convenience later warrants it).
- Revisiting the nav/user-menu entry pattern if the floating button proves noisy in practice.
</deferred>

---

*Phase: 122-in-app-feedback-button-seed-049*
*Context synthesized: 2026-06-15 from SEED-049 (decisions locked in explore session)*
