---
id: SEED-169
status: promoted → Phase 224 (2026-09-17)
planted: 2026-09-17
planted_during: /gsd-explore "guest drop-off" — follow-up to reports/growth/growth-recommendations-2026-09-15.md finding 2 (corrected 2026-09-17)
trigger_when: next growth or Train window. Decision 1 (drop the forced /welcome redirect) is independent and could ship alone as a quick task if the import-start lever is wanted before the rest.
scope: one phase — (1) remove the forced /welcome interstitial for new guests, (2) open Train to guests as the full daily loop (reverses Phase 189 D-05), (3) guest-branch sign-up nudges delivered by bot bubbles on the Train score screen and the Import page, each with a "Why?" + "Sign up free" button pair, (4) rewrite /welcome as a short "What changes when you sign up" page, (5) before/after metrics on two separate funnel steps
---

# SEED-169: New guests hit an upsell-shaped interstitial before the product, and the one feature that brings people back daily is closed to them

## Symptom (prod, 90-day window, growth report 2026-09-15 finding 2, corrected 2026-09-17)

| Step | Registered | Guest |
|---|---:|---:|
| Accounts created | 322 | 468 |
| Start an import | 274 (85%) | 226 (48%) |
| Of those with surviving history, end up with games | – | 124 of 125 (99%) |

- The whole guest gap is at the FIRST step: ~242 of 468 guests never start an import.
  There is no post-link dead end (the earlier "95 link and never import" reading was an
  artifact of `import_jobs` rows purged for inactivity).
- Umami: 390 of 1,051 home visitors who clicked anything landed on `/welcome`.
  `Home.tsx:781` force-redirects every 0-game guest there unless a localStorage flag
  (`welcome_dismissed`) is set.
- `/welcome` is a 10-row "Guest vs Signed up" comparison table with two buttons. Six of
  the ten rows are "both have it". It is long, and reads as an upsell even though signing
  up is free. Its original purpose was to explain why e.g. Train does not work for guests.
- Since then Phase 210/211 (v2.13) shipped the warm-up path: a session with none of the
  user's own blunders is labeled a warm-up and topped up from the sharp CC0 filler pool
  (`app/services/sharp_filler.py`, `app/data/sharp_filler_puzzles.csv`) plus red herrings.
  A guest with zero games could therefore run a real Train session today; only the
  gate stops them.

## Diagnosis

Two separate levers, two separate funnel steps. Do not conflate them when measuring.

- **Lever A, guest → start an import.** The interstitial sits between the CTA and the
  product. Removing it is the direct fix for the 48% vs 85% gap. Nothing else in this
  seed moves this number.
- **Lever B, guest → register.** Guests cannot use Train, the only feature built to bring
  the same person back on a schedule (SEED-166). Letting them run the warm-up loop and
  asking for sign-up at the moment the product has just delivered value is the
  conversion moment; the comparison table on entry is not.

## Decisions (locked 2026-09-17 in /gsd-explore)

1. **Drop the forced `/welcome` redirect.** `Home.tsx` sends 0-game guests to
   `/library/import` like everyone else. `welcomeDismissal.ts` and its flag go away.
   `/welcome` stays routable (decision 5) but is never forced.
2. **Open Train to guests as the FULL daily loop**, not a one-shot demo. Sessions,
   streaks, `drill_sessions`/`train_settings` rows, the same weekday cadence. Every guest
   session is a warm-up until they import and analyze games. This **reverses Phase 189
   D-05 (LOCKED)**: `_reject_guest` in `app/routers/train.py` (all seven handlers) and
   `frontend/src/components/train/TrainGuestGate.tsx` are removed.
3. **Score screen, guest branch.** The reminder ask in the score bubble
   (`scoreBubbleCopy`, `WARMUP_REMINDER_ASK_COPY`) is REPLACED for guests by a sign-up
   ask. No reminder slot, no QR/install block, no push subscription for guests: push
   reminders for an account whose games are purged after 30 days idle is a promise the
   product cannot keep. The ask names the concrete payoff: your own blunders come back
   instead of warm-ups, and your streak and history carry over (see "Promotion is
   in-place" below). The nudge repeats every session.
4. **Buttons live in the speech bubble**, using `TrainBotBubble`'s existing `actions`
   slot (right-aligned, wraps, `mt-2`; already hosts the guess buttons on phones, so
   height and mobile behaviour are settled). Two buttons: **"Why?"** (`brand-outline`
   secondary, links to the info page) and **"Sign up free"** (primary CTA, runs the
   existing `logoutForPromotion()` + `/login?tab=register` promotion flow). Done stays
   alone in the row below, unchanged.
5. **`/welcome` becomes a short "What changes when you sign up" page.** Drop the
   table. Four deltas only: automatic Stockfish analysis of imported games, Train from
   your own mistakes, use on any device, no 30-day inactivity purge. One "Sign up free"
   button. Reachable only via the "Why?" buttons (and a plain URL).
6. **Import page.** The guest `Alert` ("Sign up free to use FlawChess on any device and
   unlock automatic Stockfish analysis of your games.", `import-guest-promo-info`) is
   replaced by a `TrainBotBubble` hosted by a **random friendly bot**
   (`pickBot('friendly')`, the score screen uses `pickBot('smart')`), shown on **every**
   guest visit to Import, with the same "Why?" + "Sign up free" pair. This is the first
   time the personas speak outside a game or puzzle context; accepted deliberately.
7. **Two metrics, recorded before and after, separately.** Lever A: guest import-start
   rate (baseline 48%, 226/468 over 90 days) and Umami `/welcome` landings (baseline
   390 of 1,051 clicking home visitors; should fall to ~0). Lever B: guest promotion
   rate (`users.promoted_at IS NOT NULL` among guests created in the window) and guest
   Train sessions completed. Do not report a combined "guest conversion" number.

## Facts the plan must respect

- **Promotion is in-place.** `promote_guest_with_password` /
  `promote_guest_with_google` (`app/services/guest_service.py`) UPDATE the same user
  row (`is_guest=False`, `promoted_at=now()`). A guest's `drill_sessions`,
  `train_settings`, streak and solves survive registration with no migration. The
  sign-up copy may promise this.
- **Guest cleanup assumes guests hold no Train rows.**
  `app/services/guest_cleanup_service.py` (~line 108) and
  `tests/test_guest_cleanup_service.py::test_purge_guest_cascades_drill_rows` document
  that `_reject_guest` keeps guest Train state empty. After decision 2 the purge must
  be re-reasoned: `drill_items`/`drill_solves` ride the `games` cascade (fine, but a
  guest's warm-up solves reference filler/herring items, not the guest's own games —
  check what the cascade actually reaches), and `drill_sessions`/`train_settings` are
  preserved by design (D-04, "session history is user progress"). Decide explicitly
  whether that preservation holds for a purged guest, and update the comments and test.
- **Herring pool is cross-user** (~91% of served herrings come from another user's
  game). Guests are cheap to create; the pool is now reachable by throwaway accounts.
  The existing guest-creation limiter (Cf-Connecting-Ip aware since Phase 216) is the
  backstop; check it covers this before opening the gate.
- **Warm-up copy assumes the user has games coming.** `WARMUP_TAIL` ("Your own
  positions will [come back]") and `INTRO_WARMUP` are written for a registered user
  whose analysis is pending. For a games-less guest, "your own positions" do not exist
  yet; the guest branch needs its own line (import + sign up, in that order).
- **`is_guest` must come from `useUserProfile().data`**, never `useAuth().user`
  (FLAWCHESS-64, `Train.tsx:66`).
- **Frontend tests to rewrite or delete:** `Train.guestGate.test.tsx` (also has a known
  cross-test contamination failure, `215/deferred-items.md`), `Welcome.test.tsx`, the
  `Home.tsx` redirect coverage, the Import guest-alert testids
  (`import-guest-promo-info`, `import-guest-promo-link`). Umami events `signup-cta` with
  `data-umami-event-source` should gain `train-score` and keep `import-promo` so lever
  B can be attributed per surface.

## Out of scope

- Push reminders for guests (decision 3).
- Any change to the registered-user score bubble, reminder slot or QR block.
- A one-shot "demo session" variant (rejected: full loop or nothing).
- Roadmap or milestone entry: this seed is a recommendation, promote via the normal
  cycle.
