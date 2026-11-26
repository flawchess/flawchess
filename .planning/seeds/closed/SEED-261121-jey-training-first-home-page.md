---
id: SEED-261121-jey
status: closed
closed: 2026-11-26
closed_reason: shipped as a direct home page change (no phase). Personalized Training is the hero feature; the owner settled the open question by deciding to post about facepalm blunders and Blunder Check
planted: 2026-11-21
planted_during: /gsd-explore session after the 2026-11-20 release (no active phase)
trigger_when: when the owner decides to push training in outbound content (Reddit, lichess blog, data stories); or when Blunder Check has about 4 weeks of usage and retention data (from about 2026-12-17); or at the next milestone planning that touches the home page or marketing
scope: small to medium, one phase (hero and feature-order rework in Home.tsx, new copy, new screenshots). Home page and messaging only.
updated: 2026-11-26 (closed: hero reorder shipped)
---

# SEED-261121-jey: Training-first home page

Reposition the home page around the training loop (import your games, find your flaws, train on
exactly those) instead of leading with the FlawChess Engine. Add Blunder Check, which is missing
from the home page entirely.

## Closed (2026-11-26)

The owner decided to push training in outbound content (planned Reddit or lichess blog posts about
facepalm blunders and Blunder Check), which settled the open question. Shipped the same day:

- Section order in `Home.tsx`: Personalized Training (hero), Game and Tactic Analysis, FlawChess
  Engine, Bots, Openings, Endgames, Time Management. Analysis is second, not the engine as
  recommended below: readers of a facepalm post find the facepalm bullet right under the hero, and
  the engine now sits directly above the bots it drives.
- The engine section lost its gold accent and looks like every other section.
- Hero bullets trimmed from four to three (streak bullet dropped, repetition intervals removed).
- FAQ: the engine question moved from second to fourth.
- `README.md` intro, top screenshot and feature order follow the same order.
- A schema.org `WebApplication` block on the home page; GitHub repo description, homepage and
  topics updated.

Not done, left to the owner:

- No separate Blunder Check section and no Blunder Check screenshot. It is the third hero bullet.
- `frontend/public/og-image.jpg` still says "Free Chess Analytics" over endgame gauges. It is the
  link preview for any post that links flawchess.com.
- The hero heading is still "Personalized Training".
- The cohort numbers below were not re-run. The decision was made on the positioning argument,
  not on new data.

## Progress (2026-11-26, before the reorder)

Done in `57d3fe2db`, `493edeefd` and `8a6f265bf` (copy only, no layout change):

- The hero tagline and the meta/og descriptions now name training: "Find and fix your chess flaws.
  Analyze your chess.com and lichess games for free, train on puzzles built from your own
  blunders, and play human-like bots." The Sign In page uses the same opening sentence.
- Blunder Check is on the home page: the "Personalized Puzzle Training" section became
  "Personalized Training" with a Blunder Check bullet, and the "How can I improve" FAQ answer
  mentions it. New screenshot `personalized-puzzle.png`.
- The analysis section gained a facepalm-blunder bullet.

Still open, the core of this seed: the hero feature (`FEATURES[0]`) is still the FlawChess Engine
("Your Best Practical Move"), and training is still the third section after Game and Tactic
Analysis. There is no separate Blunder Check section. The open question below (outbound content)
still decides whether to reorder.

## Why This Matters

The owner's thesis: training (Personalized Puzzles, Blunder Check) provides the most value and is
what brings users back regularly, more than analytics or bot play. The home page does not reflect
that. Today the hero is the FlawChess Engine ("Your Best Practical Move"), Personalized Puzzle
Training is the third feature section, and Blunder Check is not mentioned at all.

The owner's own framing of the tension, unresolved at capture time:

- Chess training is a saturated category, but FlawChess training is distinctive and has a better
  UX than the alternatives the owner has tried.
- The FlawChess Engine is more novel and faces less competition, but it has to be explained
  before it can sell (the current hero copy needs three paragraphs).

## Recommended Shape (from the explore session, not yet decided)

- The hero leads with the loop, with training as the payoff: puzzles built from your own
  blunders. This is a one-sentence pitch in a much smaller field than generic puzzle training.
- The FlawChess Engine becomes the second section, directly below the hero, as the "why it's
  better" proof. Arrivals from engine posts still find what they came for within one scroll.
- Add a Blunder Check section.
- Scope is the home page and messaging only. Changing post-import routing was considered and
  dropped: the red pending-puzzles badge on the main nav already steers users to Train.

## The Open Question That Decides the Direction

Will outbound content shift toward training too? All organic acquisition so far was fed by engine
and analytics content (the Reddit post and lichess blog posts about the FlawChess Engine, the
chess data stories blog). If that stays the case, a training hero works against the existing
funnel and risks a bait-and-switch for people arriving from engine posts. If the owner intends to
push training outward, the hero should lead that change.

The owner posted about training once, on r/lichess, and it got no traction
(https://www.reddit.com/r/lichess/comments/1vhawzs/). One post in one subreddit is weak evidence
about the pitch either way.

## Evidence (prod DB + Umami, pulled 2026-11-20)

Method: GM Noel Studer's newsletter linked directly to `/train` and would bias any all-users
number, so home-page arrivals were isolated with `users.first_touch->>'landing_path' = '/'`.
`first_touch` only exists from about 2026-09-24. Retention figures use users who signed up at
least 21 days before the pull. Superusers excluded. Umami `session.distinct_id` is the user id,
which is how page views were joined to these users.

Return rate by first-week behaviour (home-page arrivals, n=227):

| First-week behaviour | Users | Active again after day 7 | After day 14 |
|---|---|---|---|
| Never imported | 59 | 5% | 5% |
| Imported, did not train | 117 | 15% | 11% |
| Imported and trained | 49 | 29% | 24% |

Correlational only: motivated users self-select into training, and the groups are small.

Adoption gap: only 30% of importers (49 of 166) solve a puzzle in week one, even though 45% of
home-page arrivals open Train on day one (Umami, n=288). Day-one section visits: import 93%,
analysis board 55%, Train 45%, flaws list 37%, openings 35%, bots 29%, endgames 24%.

What returning users do (day 7 onward, Umami, 254 user-days from 44 users):

| Section | Share of return days | Returning users who used it |
|---|---|---|
| Train | 52% | 16 |
| Analysis board | 42% | 32 |
| Bots | 19% | 9 |
| Openings | 13% | 16 |
| Endgames | 7% | 7 |

Training drives frequency, analysis drives reach. Train usage is concentrated: in the prod DB,
three users account for 81 of the 130 return days with a solved puzzle.

By acquisition source (signed up at least 21 days before the pull):

| Source | Users | Imported | Solved a puzzle in week 1 | Active after day 7 |
|---|---|---|---|---|
| Search | 107 | 79 | 23 | 18 |
| Direct | 60 | 46 | 17 | 11 |
| Reddit | 26 | 21 | 6 | 4 |
| ChatGPT | 22 | 10 | 2 | 0 |
| Newsletter (landed on `/train`) | 80 | 43 | 37 | 21 |

Training adoption is flat at about 30% of importers across search, direct and Reddit. The
newsletter cohort is the only one that was promised training: it trained at 46% of arrivals
versus 22% for home-page arrivals, and returned at 26% versus 16%. That gap is confounded by
audience quality (improvement-minded subscribers) and a GM's endorsement, but it is the only
evidence on what a training-first promise does.

Blunder Check had no usable data: first answers on 2026-11-19, from 11 users.

## When to Surface

**Trigger:** any of

- the owner decides to push training in outbound content
- Blunder Check has about 4 weeks of usage and retention data (from about 2026-12-17)
- the next milestone planning that touches the home page or marketing

## Before Acting

- Re-run the `first_touch` cohort numbers; the sample will be larger and the figures above will
  be stale.
- Include Blunder Check in the return-day and retention cuts.
- Settle the open question about outbound content first. It decides between the loop framing and
  leaving the engine as hero.

## Breadcrumbs

- `frontend/src/pages/Home.tsx`: `FEATURES` array (index 0 is the hero feature, the rest render
  as `featureSections`), hero section at `data-testid="hero-section"`, hero subhead copy
- `frontend/public/screenshots/`: per-feature screenshots referenced from `FEATURES`
- `frontend/src/lib/firstTouch.ts` and `users.first_touch` (`app/models/user.py`): acquisition
  attribution used for the cohort split
- `user_activity`, `drill_solves`, `blunder_check_answers`, `games.platform = 'flawchess'` (bot
  games): the prod tables behind the retention and return-day numbers
