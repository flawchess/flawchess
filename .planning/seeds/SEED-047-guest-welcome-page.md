---
id: SEED-047
status: planted
planted: 2026-06-14
planted_during: v1.26 Full-Game Eval Pipeline (via /gsd-explore)
trigger_when: next onboarding/UI polish push, or when guest→signup conversion is prioritized
scope: small (1 frontend UI phase; backend reaper deferred — see "Deferred" below)
---

# SEED-047: Guest Welcome page (explain guest-vs-signup value before Import)

## Why This Matters

A first-time guest currently lands directly on the Import page (`frontend/src/pages/Import.tsx`).
The page mixes a small "consider signing up free" banner with the sync inputs, but it never
explains the one thing that actually motivates sign-up: **guest games get zero FlawChess
Stockfish analysis.** Guests don't know what they're missing, so the sign-up CTA has no teeth.

The fix is a **separate Welcome page** that sits before Import and sets expectations honestly,
then hands off to the existing Import flow via a Proceed button.

## Key Factual Corrections (from codebase exploration)

These reshape the messaging — the original framing ("games partially processed") was imprecise:

- **Guests get *zero* FlawChess Stockfish compute, not partial.** The eval queue and full-eval
  drain both filter `NOT users.is_guest` at every tier (`app/services/eval_queue_service.py:31-34,213`;
  `app/services/eval_drain.py:1465`, comment `D-116-10`). No guest game is ever enqueued for
  our analysis. Rationale (ROADMAP): inactive-guest games are cleanup candidates, so analyzing
  them wastes compute.
- **It *looks* partial because lichess games carry their own `%eval`.** A guest importing from
  lichess sees eval-derived data (lichess freebies, source-agnostic `full_evals`); a guest
  importing from chess.com sees none. So the honest split is "position/WDL analytics + lichess's
  own evals" vs "our deep Stockfish flaw analysis (blunder/mistake/flaw detection)".
- **The 30-day deletion is NOT implemented.** No reaper job exists; "30 days" today is only the
  guest JWT lifetime. The current Import banner already promises "Prevent losing your imported
  games after 30 days of inactivity" — an unenforced claim. Do not make this promise louder
  until the reaper exists (see Deferred).
- **Sign-up is in-place promotion, data preserved.** `promote_guest_with_password()` /
  `promote_guest_with_google()` flip `is_guest=False` on the same user row — games, bookmarks,
  and eval history carry over. No "fresh account" / merge problem to message around.

## Design Decisions (locked in this explore session)

- **Separate `/welcome`-style route**, not an in-place Import redesign and not a hybrid
  collapsible intro. Import page stays lean; Welcome owns the explainer + Proceed button.
- **User-controlled dismissal, not an automatic gate.** A "Don't show this again" checkbox
  (localStorage flag — guests are already device-bound via their localStorage token) lets a
  returning guest skip straight to Import. Default: show it. No "seen" user-model field needed
  for v1.
- **Softened compute copy, no hard deadline.** Frame it as "we don't run deep analysis on guest
  games because inactive guest data may eventually be cleared" — NOT "deleted after 30 days".
  This keeps the copy honest while the reaper is unbuilt.
- **Frontend-only scope.** New page + route + the dismissal flag. No backend changes.

## Value Split to Communicate on the Page

| | Guest (no sign-up) | Signed up (free) |
|---|---|---|
| Opening explorer / WDL by position | ✓ | ✓ |
| Endgame analytics, time management | ✓ | ✓ |
| lichess games' built-in evals | ✓ (freebie) | ✓ |
| **FlawChess deep Stockfish analysis** (per-game blunder/mistake/flaw detection, flaw-delta) | ✗ | ✓ |
| Cross-device access | ✗ | ✓ |
| Data durability (no inactivity cleanup) | ✗ | ✓ |

## Relevant Files

- `frontend/src/pages/Import.tsx` — current landing; banner lines ~292-310, First-Sync box ~443-454
- `frontend/src/pages/Home.tsx:610-628` — routing gate (guest w/ 0 games → `/library/import`);
  Welcome route would slot in ahead of this
- `frontend/src/hooks/useAuth.ts:123-175` — guest creation/resume; where a "seen welcome" flag co-locates
- `app/services/eval_queue_service.py`, `app/services/eval_drain.py:1465` — guest eval exclusion (the "why")

## Deferred — 30-day guest-data reaper (intentionally not built now)

A scheduled job that deletes inactive guest accounts/games. **Implement only once prod actually
needs to reclaim disk space** (user's call). Until then the Welcome copy stays soft (no hard
deadline) so we make no unenforced promise. When built, the soft copy can be upgraded to a
concrete "X days" figure and the guest-exclusion compute rationale becomes literally true.

## Recommended Next Step

Well-scoped for `/gsd-ui-phase` (single new page, clear contract). Sketch the layout first with
`/gsd-sketch` if the design direction wants exploring before a build.
