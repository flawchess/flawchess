# Phase 231: Weekly Leaderboard Medals (SEED-186) - Context

**Gathered:** 2026-10-04
**Status:** Ready for planning

<domain>
## Phase Boundary

At each Sunday 24:00 UTC deadline the top 3 of each weekly Train board (Points, Accuracy) earn gold,
silver and bronze medals. Delivered as: a persisted final-standings snapshot (new table + migration,
lazy idempotent finalization), a lifetime medal tally on live board rows, a "Last week" podium at the
top of each tab, a "You finished #N last week" line for non-medallists, a claim-and-celebrate medal
dialog on the Train landing, one line of privacy copy, and an admin-only demo page that renders the
real production components from dummy data.

Out of scope: per-medal popovers with dates, medal history or a profile medal case, notifications,
seasons/leagues/prizes, WR-01 hardening.

</domain>

<decisions>
## Implementation Decisions

### Locked upstream (SEED-186 + ROADMAP Phase 231, owner 2026-10-04; do not re-open)
Everything in `.planning/seeds/SEED-186-weekly-leaderboard-medals.md` § "Locked decisions" is binding:
per-board medals, Accuracy medals for qualified users only, medals follow the public board (opted-out
at finalization time and guests are ineligible), Olympic ties, no Points participation floor,
`MEDALS_START_WEEK = 2026-10-05`, WR-01 accepted (do not fix), snapshot shape (`final_rank`, `value`,
`puzzles`, `display_name`, explicit `medal` SMALLINT IntEnum + CHECK, `celebrated_at`, unique on
week + board + user), lazy finalization with `ON CONFLICT DO NOTHING` and no cron, deletion sets
`user_id` NULL + "Deleted user", opt-out masks past podium names as "Anonymous" while the tally
survives, tally rendering (lucide `Medal`, `theme.ts` gold/silver/bronze, `text-sm` count, no emoji,
`aria-label`, in the wrapping name block), wire format `medals: {gold, silver, bronze}` with no user
id, podium format, Claim button (audio-unlock gesture), `useMuted` / `prefersReducedMotion()`,
server-side claim via `celebrated_at` on Claim or dismiss, no Umami event, admin demo page scenarios.

### Who gets a final-standings row (Claude's call, owner said "you decide")
- **D-01:** The snapshot freezes the public board exactly. Points: every registered, non-hidden user
  with at least one solve in the week, ranked. Accuracy: qualified users only (20+ non-filler
  solves), ranked. Tentative Accuracy users, users hidden at finalization time, and guests get **no
  row**. This follows the seed's "medals follow the public board exactly" and "final standings skip
  tentative users", and keeps `final_rank` a true public rank (a hidden user's would-be rank would
  sit beside a real user with the same rank number without being a tie).
  — **Reversibility:** costly — rows not written at finalization can only be rebuilt later from
  `drill_solves` with the opt-out flags as they are at rebuild time, not as they were.
- **D-02:** Ranks in the snapshot come from the same service code as the live board
  (`_tiered_order` / `_competition_ranks` in `app/services/train_leaderboard.py`, as amended by
  quick 261004-8rt), never a second ranking implementation. `medal` is assigned from the
  competition rank (1 gold, 2 silver, 3 bronze) and stored explicitly.
- **D-03:** "You finished #N last week" shows on a tab only when the viewer has a snapshot row for
  that board in the immediately previous week and it carries no medal. Medallists get no such line
  (the podium and tally already show it). No row (hidden, tentative, guest, didn't play) means no
  line. It is a **separate line** in the hint area, below this week's hint (pass target, qualify
  count, etc.), not a replacement for it. Copy: plain rank, e.g. "You finished #12 last week".
- **D-04:** A viewer who opted out after the week still sees their own "finished #N" line and
  claims their own medals (it is their own data; masking only applies to what others see).

### Medal floor (Claude's call)
- **D-05:** A medal needs a value above zero: a Points entry with 0 points, or a qualified Accuracy
  entry at 0%, gets its snapshot row and rank but `medal` NULL. This only matters in a quiet week
  (bronze for 0 points would be silly) and is not a participation floor: one point is enough.
  Flagged as a deliberate refinement of the seed's "no participation floor"; revisit if the owner
  disagrees.
- **D-06:** Fewer than 3 eligible entrants means fewer medals. Ties can produce more than three
  medal rows (1, 1, 3 gives two golds and a bronze; 1, 2, 2 gives a gold and two silvers, no bronze).

### Podium edge states (Claude's call)
- **D-07:** The podium shows only the immediately previous ISO week, labelled "Last week". No
  fallback to an older finalized week (the label would lie). In the week of 2026-10-05 (nothing
  finalized yet) there is no podium.
- **D-08:** A tab whose board awarded no medals last week (nobody played, or no qualified Accuracy
  users) shows no podium line at all, rather than an empty-state message.
- **D-09:** Podium names: `display_name` as stored at finalization; "Anonymous" for a user who is
  hidden *now*; "Deleted user" for a row whose `user_id` is NULL. Every tied name listed, the line
  wraps on narrow screens. Placed at the top of the tab, above the Accuracy helper and the rows.

### Medal dialog (Claude's call)
- **D-10:** Shown on the **Train landing only** (both the default and the in-progress branch of
  `TrainStartScreen`), never mid-session or on the score screen. Never for guests. It opens when the
  unclaimed-medals list is non-empty after the landing mounts.
- **D-11:** One dialog lists every unclaimed medal, newest week first, then Points before Accuracy.
  Each entry: a large tinted lucide `Medal` (same `theme.ts` constants as the tally), the medal and
  board ("Gold, Points"), "(shared)" when tied, the week ("Week of Sep 28", the Monday in UTC) and
  the final value ("412 pts" / "87%"). Title scales with count ("You won a medal!" / "You won 3
  medals!"). Medals animate in with a scale/bounce, skipped under reduced motion.
- **D-12:** Sound: reuse the existing `game-win` event (`WinChime`), no new audio asset. It plays
  once per Claim tap regardless of medal count, unless muted.
- **D-13:** Claim tap: call the audio unlock inside the gesture, play the sound, fire
  `fireWinConfetti()` (unless reduced motion), POST the claim for every shown row, close the dialog
  (the confetti canvas keeps playing over the landing). Dismiss (X, Esc, outside click): POST the
  claim with no sound or confetti. A failed POST is not surfaced beyond the global mutation error
  handling; the medals simply reappear on the next visit.

### Claude's Discretion
- **Finalization trigger and concurrency:** which requests run the lazy finalizer (at least
  `GET /train/leaderboard` and the unclaimed-medals read), how a week with zero eligible entrants is
  remembered as finalized (or cheaply recomputed), and whether to add an advisory lock on top of
  `ON CONFLICT DO NOTHING`. `drill_solves.solved_at` is server-set at submit time
  (`app/repositories/train_repository.py:3001`, `solved_at=now_utc`), so a late finalization sees the
  same solves.
- **API shape:** extending `TrainLeaderboardResponse` with a per-board last-week block (podium +
  viewer's final rank) vs a separate endpoint; a separate unclaimed-medals GET plus a claim POST is
  the expected shape. Claim POST must be scoped to the caller's own rows (IDOR guard).
- **Account deletion mechanics:** find every user-deletion path (`app/services/guest_cleanup_service.py`
  deletes guests, who have no rows per D-01; registered-account deletion may be manual). The stored
  `display_name` must actually be erased, not just masked at read time. Read-time "Deleted user" for
  `user_id IS NULL` is the display rule either way.
- **Tally query:** one grouped `COUNT` over the snapshot for the visible rows' user ids, per board.
- **Component seams for the demo page:** split `TrainLeaderboardCard` so the board, podium and dialog
  take data via props with thin fetching hooks, so the demo renders production components.
- **Theme constants:** exact gold/silver/bronze colors in `theme.ts`, readable on the dark surface.
- **Privacy copy:** the one-line addition to `LeaderboardPrivacyCard` ("Hidden users don't earn
  medals" or similar), plus whether `Privacy.tsx` needs a line about the stored weekly results.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase source
- `.planning/seeds/SEED-186-weekly-leaderboard-medals.md` — full locked decisions, demo scenarios, breadcrumbs
- `.planning/ROADMAP.md` § "Phase 231: Weekly Leaderboard Medals (SEED-186)" — phase goal and locked list
- `.planning/seeds/SEED-185-weekly-train-leaderboards.md` — board rules, UTC deadline, qualifier, tie display, accepted risks

### Phase 230 foundation
- `.planning/phases/230-weekly-train-leaderboards/230-CONTEXT.md` — D-01..D-19 (scoring, window, ranking, visibility)
- `.planning/phases/230-weekly-train-leaderboards/230-REVIEW-DISPOSITION.md` — WR-01 (accepted, do not fix)
- `.planning/quick/261004-8rt-accuracy-leaderboard-qualified-first-tie/261004-8rt-PLAN.md` — qualified-first Accuracy ordering, `rank: int | None` for tentative rows; code landed on `main` in c0499df76 / 173435102 (2026-10-04); the snapshot builds on that ordering

### Backend
- `app/services/train_leaderboard.py` — `week_window`, `display_name`, `_tiered_order`, `_competition_ranks`, `build_board`, `get_weekly_leaderboard`
- `app/repositories/train_leaderboard_repository.py` — `fetch_week_aggregates` (reuse for finalization)
- `app/schemas/train.py` — `LeaderboardRow` (add `medals`), `TrainLeaderboardResponse`
- `app/routers/train.py:281` — `GET /train/leaderboard`, `dev_now_utc` injection
- `app/core/dev_clock.py` — time source for the deadline
- `app/services/guest_cleanup_service.py` — guest deletion path

### Frontend
- `frontend/src/components/train/TrainLeaderboardCard.tsx` — row layout, name-block wrap (IN-02), tabs, hint
- `frontend/src/lib/trainLeaderboard.ts` — `viewerHint`, copy constants
- `frontend/src/lib/confetti.ts` — `fireWinConfetti`, `prefersReducedMotion`
- `frontend/src/lib/sounds.ts` — `SoundEvent` (`game-win`), `playSound`, `unlockAudio`, `useMuted`
- `frontend/src/components/admin/TrainReminderTestCard.tsx`, `frontend/src/pages/Admin.tsx` — admin card pattern
- `frontend/src/components/settings/LeaderboardPrivacyCard.tsx` — opt-out copy to extend
- `frontend/CLAUDE.md` — styling, testids, Umami rules (`/admin` is excluded from tracking)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `week_window(now_utc)` in `train_leaderboard.py`: standalone by design so the snapshot can reuse it
- `fetch_week_aggregates` + `_entry_for` + `_tiered_order`: produce exactly the public, ranked list the snapshot needs
- `fireWinConfetti` / `CONFETTI_DURATION_MS` / `prefersReducedMotion` in `lib/confetti.ts`
- `playSound('game-win')` + `useMuted` + `unlockAudio` in `lib/sounds.ts`
- `TrainReminderTestCard` admin card pattern (note: that card is dev-only; the medals demo must work in prod too since it is client-only)

### Established Patterns
- Router `APIRouter(prefix="/train")`, SQL in repositories, ranking in pure service functions unit-tested without a DB
- Wire format never exposes user ids (`_Entry.key` internal); tally must keep that
- Low-volume domain columns: SMALLINT IntEnum + CHECK for `medal`, TEXT + CHECK or literal for `board`
- FKs mandatory with explicit `ondelete` (here `SET NULL` on `user_id`)
- Time only via `dev_now_utc`; sequential awaits on one `AsyncSession`

### Integration Points
- New snapshot table + Alembic migration
- Lazy finalizer called from the leaderboard and medals read paths
- `LeaderboardRow.medals`, last-week block, unclaimed-medals GET + claim POST
- `TrainStartScreen` hosts the medal dialog (both landing branches)
- `TrainLeaderboardCard` gains podium + tally + finished-line; split into prop-driven components for the demo
- `Admin.tsx` gets the "Leaderboard medals demo" next to `TrainReminderTestCard`

</code_context>

<specifics>
## Specific Ideas

- Dialog entry shape: [gold Medal] "Gold, Points (shared)", "Week of Sep 28", "412 pts".
- Podium: "Last week: [gold] alice [silver] bob [silver] dave" (a 1, 2, 2 week has no bronze).
- Hint area with both lines: "12 points to pass bob" then "You finished #12 last week".

</specifics>

<deferred>
## Deferred Ideas

- "You finished #N" (or "N puzzles short of qualifying") for hidden users and tentative Accuracy users: not stored per D-01; revisit only if asked.
- Revisit the D-05 zero-value medal rule if the owner prefers the seed's literal "no floor".

</deferred>

---

*Phase: 231-weekly-leaderboard-medals*
*Context gathered: 2026-10-04*
