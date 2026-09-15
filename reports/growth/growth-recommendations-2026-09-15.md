# FlawChess growth audit and recommendations (2026-09-15)

Sources: prod DB (users, import_jobs, drill_*, games), Umami DB (both sites, via SSH read-only), the in-app Activity Pulse dashboard, a Chrome walkthrough of the logged-in app, landing page source, and a web research pass on competitors and channels. Reddit could not be fetched (JS challenge), so post engagement is inferred from referrer traffic.

## 1. Where you are

| Metric | Value | Note |
|---|---|---|
| Registered users (non-admin) | 316 | first signup 2026-03-22 |
| Guest sessions ever | 459 | 78 promoted to accounts (15.6%) |
| Signups, last 30 / 90 days | 93 / 246 | ~3/day |
| MAU / WAU / DAU (incl. guests) | 279 / 94 / 22 | stickiness 8% |
| Registered → import completed | 85% | activation is not the problem |
| Registered → 100+ games | 75% | median library ~1,000 games |
| Returned 7 days after signup | ~20% | July cohort: 26/122 |
| Returned 30 days after signup | ~10% | July cohort: 14/122 |
| Google OAuth share of signups | 78% | 247 oauth rows |
| Weekly visitors (app) | 150–200 | was 25–50 before the July Reddit post |
| Mobile share of sessions | 39% | |
| Push subscriptions | 6 | |
| Feedback rows | 10 (1 real user) | |
| GitHub stars | 18 | |

Traffic sources, all time (sessions): direct 1,735, google 234, reddit 280, chatgpt.com 149 (55 referrer + 94 utm), lichess.org 48 (all in the last 30 days), github 29, stories 22, bing/ddg/brave 45.

Visitor spikes map 1:1 to Reddit posts: "100% free chess analytics platform" (r/chess, ~April), "An engine to find the most practical move, not the best" (r/chess + r/lichess, July 20-27: 332 and 252 visitors/week, 122 signups that month), "I analyzed 112,583 lichess games entering the endgame two pawns up" (r/chess, mid August, 70 story visitors, 22 app sessions).

## 2. Diagnosis

1. **Acquisition is entirely event-driven.** Between Reddit posts the site settles at ~150 visitors/week. There is no compounding channel: 2 URLs in the sitemap, 2 pages indexed, no feature landing pages, no blog on the main domain, stories site gets ~10 visitors/week now.
2. **Activation is excellent for registered users, poor for guests.** 85% of registered accounts import. Guests: 380 → 153 link an account (40%) → 58 start an import (15%). 95 guests link and then never import. Guests also cannot use Train at all, and their analysis is manual one-game-at-a-time. The `/welcome` interstitial (a feature comparison table) sits between the CTA and the product; 390 of 1,051 home visitors who clicked anything landed there.
3. **Retention is the biggest leak.** ~80% of new accounts never come back after week one. There is no re-engagement loop: email is password-reset only, push has 6 subscribers, no weekly digest, no "new games analyzed" nudge. Importing games once gives the user a static report; nothing changes unless they re-import.
4. **Train, the habit feature, punishes newcomers.** Of 131 first Train sessions, 83 (63%) end with zero correct moves (avg 6.8 attempts, 1.3 correct). v2.19 just shipped a narrated onboarding, which fixes explanation, not difficulty. 47% of users who complete a first session complete a second, which is decent once they get over the hump.
5. **Mobile loses people at the engine gate.** Engine gate abandonment last 90 days: mobile 19/52 (37%) vs laptop 4/71 (6%). Mobile is 39% of sessions.
6. **Nothing is shareable.** No share buttons, public profiles, embeddable cards, or referral mechanic anywhere. Every acquisition is you posting.
7. **AI search is already a channel you did not build.** ChatGPT sent 149 sessions (more than Google organic in some months), yet robots.txt (Cloudflare managed block) disallows GPTBot, ClaudeBot, Google-Extended and CCBot. ChatGPT-User/OAI-SearchBot are not blocked, which is why it still works, but you are actively suppressing the training-side citations.

## 3. Recommendations, ranked

Ranking weighs expected activated users per week of effort. "Effort" is your time. Items 1-5 are the ones I would do before anything else.

### Tier 1: fix the leaks before pouring more in

**1. Weekly "your games this week" email (retention, 1-2 days).**
Resend is already wired. Once a week, for users with new games on their platform since last sync: auto-sync, analyze, send "N new games, 3 blunders tagged (2 forks), your Train pool grew by 5, streak at risk". Registered users with ~1,000-game libraries have already given you the username; you can sync without them. This is the single loop that turns a one-time report into a habit. Add an unsubscribe and a "digest frequency" setting. Expected: 7-day return from ~20% to 35%+ on the July-style cohort.

**2. Guest path: kill `/welcome`, import first, explain later (activation, 1 day).**
Guest button should go straight to a username field ("chess.com or lichess username") with the import starting on submit, then land on Library with the analysis already running. Move the guest-vs-account comparison into a dismissible banner on Library. Investigate the 95 linked-but-not-imported guests: this looks like a UX dead end (linked on `/welcome`, then no obvious "import" affordance), check Sentry and the Import page for guests. Target: guest import rate 15% → 40%.

**3. Train difficulty ramp (retention, 2-3 days).**
First two sessions should be built to be winnable: prefer flaws with the largest eval swing and shortest winning line, cap at 5 puzzles, weight herring/quiet positions higher, and give visible partial credit for the verdict. Show "you'd have found this at 1500 rating" style framing rather than 0/9. Measure zero-correct first sessions (currently 63%) and second-session completion (47%).

**4. Mobile engine gate (activation, 1-2 days).**
37% mobile abandonment on the Maia/Stockfish download gate. Options: show estimated download size and time up front, let the user browse the bot roster and pick an opponent while it downloads, and default mobile bot play to a lighter engine profile with the full one as an upgrade. Also give the bot cards avatar images; the empty circles read as broken.

**5. Unblock AI crawlers and add feature landing pages (acquisition, 1 day + ongoing).**
Remove the Cloudflare-managed AI block in robots.txt (keep `ai-train=no` only if you truly care; it costs citations). Prerender is already set up (`prerender.tsx` handles `/` and `/privacy`), so add static, indexable pages: `/engine` (practical best move vs engine best move), `/endgame-stats`, `/time-management`, `/opening-explorer`, `/bots`, `/train`, each with real screenshots, one data-story chart, and a "try it as a guest" CTA. Put them in the sitemap and link them from the landing feature cards. Search research shows "endgame conversion rate from my games", "chess time management analysis" and "practical best move" have no incumbent; "free game review" is crowded, do not fight for it.

### Tier 2: make the product spread itself

**6. Shareable artifacts (product-led, 3-5 days).**
One share button per insight, rendering an OG image: "My opening WDL card", "Endgame ELO 1420 vs blitz 1587", "Gem move of the week" (board + move), "Flaw profile: 40% of my losses are forks". Put the share on the Train end-of-session summary and the bot game result screen too. Every card links to a public page with a "get yours" CTA. This is how Aimchess-style reports and chess.com's Insights spread on Reddit and Discord. Also gives you a data source: track share events in Umami.

**7. Public player pages (product-led + SEO, 3-5 days).**
Opt-in `flawchess.com/u/<username>` with opening WDL, flaw profile, endgame stats. Indexable, linkable from a lichess/chess.com profile bio, and the natural target of the share cards. Scouting opponents already works internally; a public page is the same query on a different route.

**8. One-click "scout this opponent" from lichess/chess.com game URLs (product-led, 2 days).**
Landing page input: paste any lichess or chess.com game/profile URL and get the opponent's opening WDL as a guest, no login. Zero-friction entry that people share in "how do I prep against X" threads.

**9. Move Train and bots from registered-only to guest-with-cap (activation, 1 day).**
Guests currently can't Train. Give them one 5-puzzle session from their imported games, then gate the second session behind signup. Bots are the most-visited feature by non-registered visitors after the library, and you already have the "sign up to keep this game" hook.

### Tier 3: channels

**10. Lichess ecosystem (partnerships, days of outreach, high fit).**
Being free and AGPL is exactly what got Listudy featured by thibault and listed on lichess.org/page/extend. Ask for a listing on /page/extend (via lichess Discord or feedback), publish a lichess community blog post (ublog) about the practical-move engine with the two-pawns-up data, and post the Train feature in the lichess forum once the difficulty ramp is in. The lichess.org referrer already appeared this month (48 sessions) without you doing anything.

**11. YouTube, not Twitch, not HN, not Product Hunt (paid, small budget).**
Two independent founders (Chessbook, Chessigma) report YouTube sponsorships or creator Shorts as the only paid channel that worked; Chessbook says Meta/X/Reddit/Google ads burned money. HN gave near-competitor tools (trueelo.app, dontblunder) 2-7 points. Budget: 3-5 mid-size improvement channels (10-100k subs) at a few hundred dollars each, with a per-creator landing page and utm. Pitch the engine ("the move you'll actually pull off") and the Train-from-your-own-blunders angle, not "free analytics". Provide the creator a ready-made data story chart to show.

**12. Newsletter and reviewer pickup (organic, hours).**
Perpetual Chess Linkfest (Ben Johnson) regularly features listener-built free tools; "Adventures of a Chess Noob" (vitualis) reviews tools unpaid; chessnewsletter.substack.com lists free improvement tools as a beat. Email each with one data story and one screenshot. Submit to chessdir.app and open a PR to awesome-chess.

**13. Data stories: publish on the main domain and time them with Reddit (organic).**
The stories site got 114 visitors total and 22 app sessions. The two-pawns-up story is good content but lives on a subdomain with no nav to the app and a Reddit post that linked the story, not the app. Move stories under `flawchess.com/stories/` (share domain authority), end each with an interactive "check your own conversion rate" guest CTA, and post one story per month to r/chess with the app link in the first comment. Candidate next stories from data you already have: "what a 1200 actually blunders" (tactic-motif distribution by rating from game_flaws), "the practical move vs the engine move" (engine-disagreement study), "bots at 1500: how often do humans beat a human-like bot".

**14. Reddit cadence (organic, already proven).**
Your three posts produced roughly 250 signups. Keep a 4-6 week cadence, one feature or story per post, and answer every comment for 48 hours. Rotate subreddits: r/chess, r/chessbeginners (416k, underused), r/lichess, r/chessprogramming for the engine. Add an "As seen on r/chess" landing variant with utm so you can attribute.

**15. chess.com side (organic, low priority).**
No app directory exists. A member blog post in the Chess.com Developer Community club and a review-style blog post on chess.com are the only venues. Worth one afternoon.

### Tier 4: instrumentation you need before spending money

**16. Fix attribution before paying anyone.** "direct" is 48% of sessions and includes all app-open PWA traffic. Add utm to every link you post, tag PWA launches (`?source=pwa` in the manifest start_url), and record `first_referrer` on the users row at signup so cohorts can be split by source in the Activity dashboard.
**17. Feedback volume is ~1 user.** Add a post-import "what did you come here for?" one-question survey (5 options) and a post-Train "too hard / about right / too easy" toggle. You cannot fix retention on 10 feedback rows.
**18. Add a retention-by-source and a Train-difficulty card to Activity Pulse** so items 1, 3 and 16 are measurable without ad-hoc SQL.

## 4. What I would not do

- Paid Meta/X/Reddit/Google ads: two independent founder retros say they lost money in this niche.
- Product Hunt / Hacker News launches: the category does not perform there.
- Twitch streamer sponsorships: ~3.4k concurrent viewers category-wide, and Chessbook reports it failed.
- Chasing "free chess.com game review alternative" SEO: eight AI-coach sites already own it with programmatic blogs.

## 5. Suggested order

Week 1: items 2, 4, 5 (robots + first two landing pages). Week 2-3: items 1, 3, 16. Week 4: item 6 with a Reddit post about the share cards (item 14). Then 10, 12, 13 in parallel with 7 and 9. Paid YouTube (11) only after 1 and 6 exist, otherwise you are buying visitors into a leaky bucket.
