---
id: SEED-191
status: closed. Resolved by Phase 234 (release #398). Closed at the v2.23 milestone close 2026-10-09.
promoted_to: Phase 234
promoted: 2026-10-05
planted: 2026-10-05
planted_during: /gsd-explore on getting feedback from invested users (milestone v2.21, phase 233 in flight)
trigger_when: next milestone planning, or a free quick-task slot; ship early, since every week without it is a week of near-zero feedback
scope: small-medium
---

# SEED-191: Milestone feedback ask (Hilda the Hippo)

## Why This Matters

Feedback from invested users is one of the most valuable inputs for improving FlawChess, and almost none arrives:

- 11 real feedback submissions since June 2026 (plus 3 owner tests); 7 of the 11 come from a single user who knows the owner personally.
- The floating feedback button is desktop-only (`FeedbackButton.tsx`, mobile had zero submissions).
- Of 58 users with 3+ Train days, only 4 ever sent feedback.

The lesson from the one prolific user: people give feedback when it feels like talking to a person, not a form. A timed, character-voiced, specific ask at a moment of engagement should beat a generic always-on button.

Rejected alternative: emailing active users directly. Users never gave explicit consent to be contacted, so it could read as intrusive.

## Locked Decisions (from /gsd-explore 2026-10-05)

1. **Eligibility:** non-guest users with >= 5 distinct `activity_date` rows in `user_activity`. On 2026-10-05: 98 users eligible, 73 of them active in the last 14 days. Feature-agnostic on purpose, so regulars who never train are covered; no separate Train-session condition needed (training counts as activity).
2. **Surfaces (all three, one shared state; whichever the user hits first):**
   - Import page bot bubble: replaces the usual explore copy ("Analyze your games, try a training session, challenge me to a game, or explore your openings and endgames.", `components/import/importBotBubbleCopy.ts` `EXPLORE_PARTS`).
   - Train landing page host bubble (`TrainStartScreen.tsx` `TrainHeader`): Hilda replaces the daily rotating host while the ask is active.
   - Bots roster page welcome bubble (`components/bots/PersonaGrid.tsx` `BotWelcomeCard`, the `rosterHost` daily rotation): Hilda replaces the standard host greeting while the ask is active. The greeting's inline info popover (how the bots work) is hidden for that stretch, which is acceptable since eligible users have 5+ active days. The welcome bubble renders for guests too, but guests are never eligible.
   - NOT the session score screen.
3. **Mobile exception:** on phones the Train landing bubble is normally hidden for returning users (quick 261004-dta, `max-sm:hidden` in `TrainHeader`). Show it anyway while the ask is active, accepting that it pushes the streak card / Start button down.
4. **Persona + copy:** Hilda the Hippo (`personaRegistry.ts`). "You've been with FlawChess for 5 days now, thanks! Got an idea that would make it better for you?" CTAs: **Maybe later** | **Sure!**
5. **"Sure!"** opens `FeedbackModal` with a concrete placeholder (e.g. "What's one thing you'd change or add?") and marks the ask done forever, even if the modal is closed without submitting.
6. **"Maybe later"** immediately dismisses avatar + bubble and snoozes. Re-ask once after +10 more active days, then never again.
7. **Ignored:** a bubble isn't a modal, so ignoring is normal. After 3 views without a click it counts as "Maybe later". (Refined 2026-10-05 after phase promotion.)
   - **A view = at most one per active day (UTC), across all three surfaces.** On a day the ask is active, Hilda shows on every visit to any surface; only the first render that day increments `views` (server compares a stored `last_view_date` inside the same atomic UPDATE). Per-render counting was rejected: Import -> Train -> Bots would burn all 3 views in one minute.
   - A view is reported only when the bubble actually renders, never on profile fetch.
   - Fully ignored: shows on 3 active days, auto-snoozes, re-asks after +10 active days for 3 more days, then never. Max 6 active days of exposure, spread over >= 13.
8. **State: server-side, one generic JSONB column** (decided over localStorage: no cross-device double-ask, and the funnel is queryable in Postgres). `users.prompt_state JSONB NOT NULL DEFAULT '{}'`, keyed by ask id so future asks (e.g. the deferred NPS ask) add a key, not a migration: `{"feedback_v1": {"status": "snoozed", "views": 2, "last_view_date": "2026-10-05", "snoozed_at_days": 6}}`. Lives on `users`, NOT `train_settings`, since non-trainers must be covered.
   - NOT NULL + default avoids the asyncpg trap where Python `None` writes JSON `null` instead of SQL NULL.
   - Deliberate exception to the CLAUDE.md TEXT + CHECK rule: shape is validated by a Pydantic model per ask (`status: Literal["snoozed", "done"]`) on every read/write instead of a DB CHECK.
   - Updates (view increment, snooze, done) are a single atomic SQL `jsonb_set` / `||` UPDATE, never read-modify-write in Python (two open tabs would lose updates).
   - Profile exposes `active_days` (count from `user_activity`) and the ask state; the server decides eligibility. Also never ask a user who has already submitted feedback from any source.
9. **Measure yield:** tag feedback submissions with a source (e.g. `milestone_ask` vs `floating_button`) so the effect is visible in the `feedback` table.
10. **Priority on Train landing:** above the reminder-install ask (that ask shows indefinitely to anyone without a phone push subscription and would otherwise block this one forever). Guest sign-up and zero-game import asks don't conflict (guests and zero-game users aren't eligible anyway).

## Deferred (out of scope)

- "Recommend FlawChess to a friend" via an NPS-style split: 9-10 get a share CTA, everyone else gets a "what would make it better?" box. Revisit when retention past 14 days improves (on 2026-10-05 only 5 users had 14+ Train days); referrals before retention mostly import churn.
- Re-enabling the floating feedback button on mobile (e.g. as a menu entry instead of a floating button).

## Scope Estimate

**Small-medium:** one Alembic migration (`users.prompt_state` JSONB + `feedback.source` column), profile fields (`active_days`, ask state, has-submitted-feedback), one small POST endpoint for view/snooze/done, three bubble integrations, view/dismiss/snooze mutations, FeedbackModal placeholder + source prop. Likely a single phase or a larger quick task.

## Breadcrumbs

- `frontend/src/components/feedback/FeedbackButton.tsx`, `FeedbackModal.tsx`, `hooks/useFeedback.ts`
- `app/models/feedback.py`, `app/schemas/feedback.py`, `app/services/feedback_service.py`
- `frontend/src/components/import/ImportBotBubble.tsx`, `importBotBubbleCopy.ts`
- `frontend/src/components/train/TrainStartScreen.tsx` (`TrainHeader`, `landingHost`, ask chain), `TrainBotBubble.tsx`
- `frontend/src/components/bots/PersonaGrid.tsx` (`BotWelcomeCard`), `botGameCopy.ts` (`rosterHost`)
- `frontend/src/lib/personas/personaRegistry.ts` (Hilda the Hippo)
- `user_activity` table (`user_id`, `activity_date`, `activity_count`)
