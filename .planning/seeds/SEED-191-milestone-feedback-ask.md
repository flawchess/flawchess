---
id: SEED-191
status: dormant
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
2. **Surfaces (both, one shared state; whichever the user hits first):**
   - Import page bot bubble: replaces the usual explore copy ("Analyze your games, try a training session, challenge me to a game, or explore your openings and endgames.", `components/import/importBotBubbleCopy.ts` `EXPLORE_PARTS`).
   - Train landing page host bubble (`TrainStartScreen.tsx` `TrainHeader`): Hilda replaces the daily rotating host while the ask is active.
   - NOT the session score screen.
3. **Mobile exception:** on phones the Train landing bubble is normally hidden for returning users (quick 261004-dta, `max-sm:hidden` in `TrainHeader`). Show it anyway while the ask is active, accepting that it pushes the streak card / Start button down.
4. **Persona + copy:** Hilda the Hippo (`personaRegistry.ts`). "You've been with FlawChess for 5 days now, thanks! Got an idea that would make it better for you?" CTAs: **Maybe later** | **Sure!**
5. **"Sure!"** opens `FeedbackModal` with a concrete placeholder (e.g. "What's one thing you'd change or add?") and marks the ask done forever, even if the modal is closed without submitting.
6. **"Maybe later"** immediately dismisses avatar + bubble and snoozes. Re-ask once after +10 more active days, then never again.
7. **Ignored:** a bubble isn't a modal, so ignoring is normal. After 3 views without a click it counts as "Maybe later".
8. **State:** user-level (view counter + status `snoozed`/`done` + the active-day count at snooze), NOT `train_settings`, since non-trainers must be covered. Per CLAUDE.md DB rules: TEXT + CHECK for the status column.
9. **Measure yield:** tag feedback submissions with a source (e.g. `milestone_ask` vs `floating_button`) so the effect is visible in the `feedback` table.
10. **Priority on Train landing:** above the reminder-install ask (that ask shows indefinitely to anyone without a phone push subscription and would otherwise block this one forever). Guest sign-up and zero-game import asks don't conflict (guests and zero-game users aren't eligible anyway).

## Deferred (out of scope)

- "Recommend FlawChess to a friend" via an NPS-style split: 9-10 get a share CTA, everyone else gets a "what would make it better?" box. Revisit when retention past 14 days improves (on 2026-10-05 only 5 users had 14+ Train days); referrals before retention mostly import churn.
- Re-enabling the floating feedback button on mobile (e.g. as a menu entry instead of a floating button).

## Scope Estimate

**Small-medium:** one Alembic migration (user-level ask state + feedback source column), an eligibility/state endpoint (or a field on the user profile), two bubble integrations, view/dismiss/snooze mutations, FeedbackModal placeholder + source prop. Likely a single phase or a larger quick task.

## Breadcrumbs

- `frontend/src/components/feedback/FeedbackButton.tsx`, `FeedbackModal.tsx`, `hooks/useFeedback.ts`
- `app/models/feedback.py`, `app/schemas/feedback.py`, `app/services/feedback_service.py`
- `frontend/src/components/import/ImportBotBubble.tsx`, `importBotBubbleCopy.ts`
- `frontend/src/components/train/TrainStartScreen.tsx` (`TrainHeader`, `landingHost`, ask chain), `TrainBotBubble.tsx`
- `frontend/src/lib/personas/personaRegistry.ts` (Hilda the Hippo)
- `user_activity` table (`user_id`, `activity_date`, `activity_count`)
