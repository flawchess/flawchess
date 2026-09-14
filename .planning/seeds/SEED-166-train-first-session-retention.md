---
id: SEED-166
status: complete (promoted → Phase 222; shipped in v2.19, release #359, 2026-09-14)
planted: 2026-09-12
planted_during: /gsd-explore "Train retention" (prod funnel cut + research pass); amended 2026-09-13 by /gsd-explore "Train bot introductions" (bot-narrated delivery, tone rules, corrections)
trigger_when: next Train window; both fixes share one metric pair and should ship together so the second one has a population to act on
scope: one phase — (A) first-session premise explanation delivered by bot avatars in speech bubbles, then a persistent bot bubble carrying the guess buttons on every puzzle, (B) per-puzzle bot feedback that always states when the position returns, plus a bot-delivered session close that frames the reminder as being for the user; plus two funnel metrics recorded before/after
---

# SEED-166: Train loses 57% of first-timers before their first move, and half of the rest after one session

## Symptom

5–7 completed Train sessions per day, almost all from the same ~5 users. Personalized
training is the only feature built to bring the same person back on a schedule, and it
isn't doing that.

## Prod funnel (2026-09-12, `drill_sessions` / `drill_solves` / `train_settings`)

Every user who ever opened a Train session, bucketed by completed sessions:

| Completed | Users | Reminder on | Pressed "Remind me" | First session: solved 0 puzzles |
|---:|---:|---:|---:|---:|
| 0 | **70** | 2 | – | **52** |
| 1 | 27 | 2 | 0 | 4 |
| 2–4 | 18 | 1 | 1 | 12 |
| 5+ | 8 | 2 | (incl. above) | – |

Of 123 openers: 57% never finished a session, 22% finished exactly one, 21% came back.
Five users hold 126 of 220 completed sessions.

Facts that shaped the diagnosis:

- **52 of the 70 never-finishers left the first puzzle without playing a move**
  (`solved_at IS NULL` on every row of their first session). 14 quit after 1–2 puzzles,
  4 after 3+. The leak is at the first screen, not mid-session.
- **Warm-up is not the cause.** Only 5 of the 70 (and 4 of the 27 one-timers) got a
  warm-up first session; the typical bouncer had real own-blunder puzzles waiting.
- **One-timers did fine**: solved ~5 of ~7, 61% guesses right, 64% moves right, missed
  2.7 puzzles on average (only 3 of 27 missed nothing). So there is always something
  concrete to promise at the end ("these 3 come back").
- **The reminder ask is not being declined at the permission prompt; it isn't pressed.**
  `reminder_intent_at` is null for all 27 one-timers. 7 of 123 openers ever enabled it.
- 25 of 27 one-timers are on the untouched `weekday_mask = 127` (daily) default.
  Decision: **daily stays**; it is the right SR cadence and the leak is elsewhere.

## Diagnosis

Two separate leaks, different populations, different fixes, one root: the product never
states its premise.

**Leak 1 (first puzzle, ~42% of first-timers).** The first thing a new user sees is a
locked board and *"Before you move with white, decide: [One critical move] [Several fine
moves]"*. Nothing says why. The guess step is the actual skill Train exists to build:
in a real game nobody tells you a tactic is on the board, and deciding whether this is
a moment that demands precision or a normal position where several moves are fine is the
decision you face every move. Ordinary puzzle sites skip that decision by construction.
A newcomer who has only seen ordinary puzzles reads the two buttons as an unexplained
quiz and leaves.

Compounding it, and probably the dominant mechanism for the 52: **the locked board
gives no feedback.** Pieces are draggable before the guess, and `handlePieceDrop`
returns `false` silently while `guess === null`
(`frontend/src/components/train/TrainSolveScreen.tsx:535`), so a dragged piece snaps
back with no explanation. The natural first action on a chessboard is to move a piece;
here that action fails silently. The prompt and the two buttons DO fit below the board
on a phone (correction 2026-09-13: the original "below the fold" claim was wrong), but
nothing draws the eye to them, so a plain text prompt under a chessboard is easy to
skip past.

**Leak 2 (after one completed session, ~half of finishers).** The score screen says
"Session complete" plus stats and a "Remind me" button. It closes a loop instead of
opening one. Nothing tells the user that the positions they missed will come back, when,
or why repeating *their own* blunders at growing intervals is worth more than a fresh
puzzle rush. The reminder is therefore an unmotivated ask for commitment before any value
has been felt. The next-session cue that does exist lives on the landing page, which only
a returning user sees.

Onboarding *before* the session (a spaced-repetition explainer up front) would touch
neither leak: leak 1 is at the puzzle, leak 2 is at the close.

## Research (admitted claims only, with sources)

- Anki labels every answer button with the interval that answer produces ("Each answer
  button shows the next time a card will be reviewed"), so the SR payoff is visible from
  the first card. https://docs.ankiweb.net/studying.html
- Duolingo moved signup behind the first lesson (+20% DAU) and tuned reminder cadence to
  23.5h: commitment asks belong after the first value moment.
  https://review.firstround.com/the-tenets-of-a-b-testing-from-duolingos-master-growth-hacker/
- Lichess Storm has no tutorial; its one non-obvious mechanic is explained inline at the
  moment it applies ("Skip this move to preserve your combo! Only works once per race").
  https://raw.githubusercontent.com/lichess-org/lila/master/translation/source/storm.xml

Unresolved (do not cite as fact): Chessable surfacing next-due in-product (interval list
is primary, display claim unsourced); "ask for push at session 4–6" opt-in figures (all
trace to a dead vendor post); any day-1→day-2 return benchmark.

## Delivery vehicle: the bot personas narrate Train (decided 2026-09-13)

The 24 Bots personas (`frontend/src/lib/personas/personaRegistry.ts`, avatars via
`personaAvatars.ts`, 128px WebP) become the voice of Train. Every explanation, prompt
and verdict below is spoken by a bot avatar with a speech bubble. Rationale: the bubble
makes the guess prompt look like a question someone is asking rather than a widget to
scroll past, it reuses characters and art that already exist (no new register for the
product), and the bots plus Train are the two features that bring users back, so tying
them together is cheap. The bot layer is permanent, not a first-session-only device;
only the *explanation* content is first-session-only.

Roles and tone:

- **Tank the Ox introduces the drill** (first session only). Friendlier bots (e.g. Hilda
  the Hippo) do the actual explaining.
- **Bot identity carries tone, not puzzle type.** Two curated sets, chosen per outcome:
  stern set (Tank, Diesel, Nell, Talon, Gus) fronts 0–1 point verdicts, friendly set
  (Shelly, Pip, Bruno, Rocco, Hilda) fronts 2–3 point verdicts. The registry has styles
  (Attacker/Grinder/Trickster/Wall) but no temperament field; add one or keep two
  explicit id lists.
- **Stern face, encouraging voice.** Copy never comments on the user and always looks
  forward. Reference lines: 0–1 points: "Not quite right. We'll try this again in the
  next session." 2–3 points: "Good job! Let's see if you remember this in 4 days."
- **Copy is written per outcome bucket with a few variants, never per bot.** 24 bots ×
  per-bot voice does not scale and is not needed.

## Scope

**A. First-ever puzzle: explain the premise, inline, once, in bot bubbles.** Before the
first guess is committed: this is a real position from a real game (yours, once enough
are analyzed); unlike a puzzle, nobody has told you whether a tactic exists; decide
first, then play. Define the two buttons: *one critical move* = a single move matters
and everything else loses something; *several fine moves* = a normal position, several
moves are fine, just play sensibly. Say that the guess is the point, not a formality,
and (briefly) that missed positions come back at growing intervals. Storm-style: at the
buttons, not a pre-session page. Shown once per user (server-side flag, not
device-local).

After the first session the explanation goes away but the bubble stays: **on every
puzzle a bot avatar with a speech bubble carries the guess prompt and the two decision
buttons inside it.** The buttons are ones the user needs anyway, so this adds no
friction. The board stays fully visible: the position must be readable to make the
decision, so the bubble sits below/next to the board, never over it (the earlier
"overlay on the board" option is withdrawn). A drop while `guess === null` must still
react (pull the bubble into view, pulse it); no drag may ever snap back with nothing
said. Design for the phone viewport first.

**B. Per-puzzle verdict and session close, spoken by bots, always with the return
date.** The reveal shows the outcome-matched bot (stern for 0–1, friendly for 2–3) with
one line that ends with when the position returns, Anki-style, from the actual SR
schedule. The score screen then has a bot sum it up: the N positions you missed come
back (and when), the ones you got are parked until later, why repeating your own
blunders at growing intervals beats one-off puzzles, and that "Remind me" exists so
this works for you, not for us. The reminder ask comes *after* that, in the same view.
Lighter copy on later sessions. Bots may also appear in the point animation over the
board; nice-to-have, decide in the UI phase.

**C. Metrics, recorded before and after** (SQL in this seed's history, or add to
`db-report`):
- First-session 0-solve rate: users whose first session has no `solved_at` / users who
  ever opened a session. Baseline **52/123 = 42%**.
- Second-session return: users with ≥2 completed / users with ≥1 completed. Baseline
  **26/53 = 49%**.

## Planning notes (verified 2026-09-13)

- `SolveResponse.due_date` (`app/schemas/train.py`) already carries the next due date
  for SR items, so "in x days" needs no schema change. It is `None` for red herrings and
  sharp filler, which carry no SR bookkeeping: the verdict copy for those must not
  promise a return ("this one was a warm-up" style variant).
- No server-side "first session" / "explanation seen" flag exists yet
  (`session_streak_count` is the only progress counter surfaced). Add one; do not use
  device-local storage, the phone-handoff flow moves users between devices.
- Avatar art resolves per persona id via `resolveAvatarSrc`; personas without curated
  art fall back to an emoji placeholder, so the stern/friendly sets should be drawn from
  personas that have real art.

## Out of scope / decided against

- Changing the daily default cadence (decided: keep).
- Push channel changes (email, etc.). The button isn't pressed; the channel isn't the
  problem yet.
- A pre-session spaced-repetition onboarding page.
- Renaming the feature to "FlawChess Boot Camp" (dropped 2026-09-13: cost across nav,
  route, Umami events, push and handoff copy, and "boot camp" signals the harsh register
  decided against). Tank may still *call* it a boot camp in his intro line.
- Bot images on the Train landing page (decoration; only returning users see it and they
  are not the leak). Revisit after the metrics have a post-change reading.
- Harsh or judgmental verdict copy, and mapping bots to puzzle type instead of outcome.
