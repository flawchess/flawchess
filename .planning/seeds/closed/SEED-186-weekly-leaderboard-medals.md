---
id: SEED-186
status: closed. Resolved by Phase 231 (release #386). Closed at the v2.22 milestone close 2026-10-09.
promoted_to: Phase 231
promoted: 2026-10-04
planted: 2026-10-04
planted_during: no open milestone; right after Phase 230 (SEED-185 weekly Train leaderboards) merged to main
trigger_when: next Train / retention phase, once the weekly leaderboards have run a few weeks in prod
scope: medium (snapshot table + migration, lazy finalization, tally on board rows, last-week podium, claim-and-celebrate dialog, admin demo page)
---

# SEED-186: Weekly leaderboard medals (gold, silver, bronze)

At each Sunday 24:00 UTC deadline, the top 3 of each weekly Train board (Points,
Accuracy) earn gold, silver and bronze medals. Medals are shown as a lifetime tally next to
names on the live board, as a last-week podium in each tab, and are celebrated (animation,
confetti, win sound) the first time a winner opens Train after the week closes.

Follow-up to SEED-185 (Phase 230), whose "Medals" section set the prerequisites: the
global UTC deadline, Accuracy medals for qualified users only (20+ non-filler puzzles), and
a persisted weekly snapshot so that opt-outs and deletions never change past winners.

## Why This Matters

- A weekly board without a lasting reward resets to nothing every Monday. Medals give
  repeat winners visible status ("bragging rights") and make the deadline feel real.
- Final standings are stored for everyone, so non-medallists get "You finished #12 last
  week", a target for the roughly 95% who never reach the podium.

## Locked decisions (owner, 2026-10-04)

### Eligibility and ranking
- **Medals are separate per board.** Points medals and Accuracy medals are awarded,
  counted and displayed independently.
- **Accuracy medals: qualified users only** (20+ non-filler puzzles in the week). Final
  standings skip tentative users.
- **Medals follow the public board exactly.** Users hidden via the leaderboard opt-out at
  finalization time and guests are not eligible. The privacy toggle copy gets one line
  saying hidden users don't earn medals.
- **Ties: Olympic rule.** Tied users share the medal and the next medal is skipped (two
  golds, then bronze). This matches the existing shared-rank display (1, 1, 1, 4).
- **No participation floor on the Points board.** Revisit only if a quiet week gives a
  medal for a trivial total.
- **First medal week: 2026-10-05** (the first full week the board is live; the board
  launched on 2026-10-04). Constant, e.g. `MEDALS_START_WEEK`.

### Score integrity
- **WR-01 accepted for medals too.** Off-key moves keep the client-asserted `move_quality`
  (Phase 230 review WR-01). The owner accepts this on 2026-10-04: no prizes, a small user
  base, and clamping would lower honest users' scores. This reverses SEED-185's "MUST close
  before medals ship". Do not fix it unprompted. If abuse shows up, check in prod how often
  off-key moves score 2 before choosing between clamping and server verification.

### Snapshot
- **Store full final standings, not only the top 3.** One row per (week, board, user) with
  `final_rank`, `value`, `puzzles`, `display_name` (as of finalization) and an explicit
  `medal` column (SMALLINT IntEnum + CHECK, NULL for non-medallists). Don't derive medals
  from `final_rank <= 3`: Olympic ties and the qualified-only Accuracy rule make that wrong.
  About 100 rows per week.
- **Lazy, idempotent finalization.** No cron. The first request after a deadline
  finalizes every unfinalized week from `MEDALS_START_WEEK` on, with `ON CONFLICT DO
  NOTHING` (unique on week + board + user). Solves are keyed on `drill_solves.solved_at`
  (UTC), so late finalization gives the same result. Accepted: a late finalization uses the
  opt-out flags as they are at that moment.
- **Account deletion:** set `user_id` to NULL and replace `display_name` with "Deleted
  user". The podium slot stays and the personal data goes (GDPR erasure).
- **Opt-out after winning:** keep the medal, but show past podiums with the name masked as
  "Anonymous". Opting back in shows the name again. Tally is keyed on user id, so medals
  survive an opt-out and opt-in round trip.

### Display: lifetime tally on the live board (bragging rights)
- Every row shows the user's **lifetime medals for that tab's board only**, non-zero medal
  types only, at most three items:
  ```
  #1  alice  🥇3 🥈1        412 pts  87 puzzles
  #2  bob    🥉2            388 pts  91 puzzles
  #3  carol                 301 pts  54 puzzles
  ```
  Nothing is shown for zero medals, so no "0 medals" shaming.
- **Rendering:** lucide `Medal` icon tinted with gold/silver/bronze constants in
  `theme.ts`, plus a `text-sm` count. No emoji (rendering differs by platform and can't be
  themed).
- **Narrow screens:** the tally lives in the name block, which wraps since the Phase 230
  IN-02 fix (like "(tentative)"). At 375 px it drops below the name. Only the name
  truncates, and the value columns stay aligned.
- `aria-label` on the tally ("3 gold, 1 silver Points medals"). No tap popover with medal
  dates in this phase.
- **Lifetime, not seasonal.** Revisit seasons only if one player dominates.
- **Medals never affect rank.**
- Rows without a username ("Anonymous") still show their tally. The viewer's own row
  shows it like any other row.
- **Wire format:** `medals: {gold, silver, bronze}` per row, from one grouped `COUNT` over
  the snapshot for the visible user ids. Still no user id in the response.

### Display: last-week podium
- At the top of each tab: "Last week: [gold] alice [silver] bob [bronze] carol", names
  only, no tallies. Shared medals list every tied name.
- The viewer's own final rank from last week ("You finished #12 last week") appears in the
  board's hint area when they took part but didn't medal.

### Celebration (first Train visit after the week closes)
- When a user has unclaimed medals, opening Train shows a **medal dialog**: the medal (s)
  animate in (scale/bounce), a **"Claim" button** fires confetti (`fireWinConfetti`, from
  `../../../frontend/src/lib/confetti.ts`) and the win sound (`playSound`, either the existing
  `game-win` event or a new `medal` event in `frontend/src/lib/sounds.ts`).
- **Why a Claim button:** browsers block audio before a user gesture on page load, and on
  iOS audio also depends on `unlockAudio()`/`initWebAudio()` running inside a gesture (see
  the iOS Web Audio memory). The tap unlocks audio and makes the moment feel like
  collecting a reward.
- Respect the mute preference (`useMuted`) and `prefersReducedMotion()` (skip the
  confetti and bounce, keep the dialog).
- **One dialog for all unclaimed medals:** gold on Points plus bronze on Accuracy shows
  both. A user who was away for several weeks sees all unclaimed medals, newest first.
- **Claim state is server-side:** a `celebrated_at` column on the snapshot row, set by a
  POST on Claim (or on dismiss). It shows once across devices, which localStorage can't
  guarantee. That row is the record, so per the Umami rules the Claim needs no
  feature event.
- Non-medallists get no dialog, only the "finished #N" line.

### Demo page (UAT in dev without live data)
- An **admin-only "Leaderboard medals demo"** page or card (Admin area, next to
  `TrainReminderTestCard`), driven entirely by **client-side dummy data**: no backend,
  works in dev and in prod.
- It must render the **real production components** (board card with tally rows, podium,
  medal dialog) through their props, not copies. Otherwise the demo proves nothing about
  production. Shape the components so they take data via props, with a thin hook doing the
  fetching.
- **Play buttons:**
  - Celebrate: gold / silver / bronze on Points; gold on Accuracy; gold + bronze (both
    boards); three unclaimed weeks; shared gold (tie).
  - Board states: tallies at different sizes (none, one type, all three with two-digit
    counts), long names at 375 px, tentative + tally on one row, Anonymous with a tally,
    podium with a tie, podium with a "Deleted user", viewer finished #12 with no medal.
  - Toggles: muted / unmuted, reduced motion on / off (simulated), so the fallbacks can be
    checked without changing OS settings.
- `/admin` is already excluded from Umami tracking, so demo clicks send nothing.

## Out of scope
- Per-medal popovers with dates, medal history pages, profile medal case.
- Notifications (push or email) about medals.
- Seasons, league tiers, prizes.
- Score-integrity hardening (WR-01, accepted above).

## Breadcrumbs
- `SEED-185-weekly-train-leaderboards.md`: board rules, UTC deadline,
  qualifier, tie display, accepted risks
- `../../../app/services/train_leaderboard.py`, `app/repositories/train_leaderboard_repository.py`:
  weekly aggregation to reuse for finalization
- `../../../app/schemas/train.py`: `LeaderboardRow` wire format (add `medals`)
- `../../../frontend/src/components/train/TrainLeaderboardCard.tsx`: row layout (`LeaderboardRowItem`,
  name block wrap from IN-02), tab toggle
- `../../../frontend/src/lib/confetti.ts`: `fireWinConfetti`, `CONFETTI_DURATION_MS`,
  `prefersReducedMotion`
- `../../../frontend/src/lib/sounds.ts`: `SoundEvent`, `playSound`, `unlockAudio`, `useMuted`
- `../../../frontend/src/components/admin/TrainReminderTestCard.tsx`, `frontend/src/pages/Admin.tsx`:
  admin dev-tool card pattern
- `../../../frontend/src/components/settings/LeaderboardPrivacyCard.tsx`: opt-out copy to extend
- `../../phases/230-weekly-train-leaderboards/230-REVIEW-DISPOSITION.md`: WR-01
