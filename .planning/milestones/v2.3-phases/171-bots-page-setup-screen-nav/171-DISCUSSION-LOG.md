# Phase 171: Bots Page + Setup Screen + Nav - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-14
**Phase:** 171-bots-page-setup-screen-nav
**Areas discussed:** Play-style knob + SEED-100, ELO range + honest labeling, Setup screen shape + lifecycle, Nav / guest access / Library surfacing

---

## Play-style knob + SEED-100

### How should "play-style" be exposed?

| Option | Description | Selected |
|--------|-------------|----------|
| 3 discrete modes | Human / Balanced / Sharp → blend 0 / 0.5 / 1; matches the real regime dispatch | ✓ (later REVERSED) |
| Continuous 0–1 slider | Literal reading of the SC, but implies a mix that doesn't exist | |
| 2 modes (Human / Engine) | blend 0 and 1 only | |
| Don't expose it this phase | Needs a REQUIREMENTS + SC amendment | |

**User's choice:** initially "3 discrete modes"; **REVERSED at the end of the session** in favour of
a continuous slider with 0.05 steps plus preset buttons, styled like the opponent-strength filter
(single-thumb, not a range slider).

### Follow-up after the reversal — does blend = 0 sit ON the slider?

| Option | Description | Selected |
|--------|-------------|----------|
| Slider spans 0–1, cliff disclosed in the popover | One control; honesty lives in the copy | |
| Slider spans 0.05–1; "Human" is a preset button that sets 0 | Slider covers only the smooth search regime; the discontinuous no-search mode is a button | ✓ |

**Notes:** Claude flagged that `0 → 0.05` is a ~+950 ELO cliff at rung 1500 (no-search → full MCTS),
while the whole remaining 95% of the axis buys only ~+150–375. The user's chosen shape resolves it:
the slider is genuinely smooth, and the regime change is a button press.

### Which 2 presets?

| Option | Description | Selected |
|--------|-------------|----------|
| Human (0) / Engine (1) | The two endpoints — the two regimes that exist as distinct things in code | ✓ |
| Human (0) / Balanced (0.5) | The two you'd realistically one-tap | |
| Balanced (0.5) / Engine (1) | Both presets inside the search regime; never crosses the cliff | |

### How do we resolve SEED-100?

| Option | Description | Selected |
|--------|-------------|----------|
| Document + pin with a test | SEED-100 fix (b); measurement (~0.09s/move) makes the deadline moot | ✓ |
| Enforce deadline outside selectBotMove | SEED-100 fix (a); a deadline abort at blend 0 degrades to a random fallbackMove | |
| Both: pin + hard safety net | Fix (b) plus a last-resort guard | |

### Default play-style / Human-mode pacing

| Option | Description | Selected |
|--------|-------------|----------|
| Balanced (blend 0.5) | Today's hardcoded stub value; shipped behavior unchanged | ✓ |
| Human (blend 0) | Thematically strongest, but the ELO label is most misleading there | |
| Sharp (blend 1) | Least human opponent on a site about human play | |

| Option | Description | Selected |
|--------|-------------|----------|
| Reuse the existing synthetic reveal delay | `chessClock.ts` already has one, built for the blend-0 ~0.09s case | ✓ |
| Add a randomized human-ish delay | New mechanism, new tuning surface | |
| You decide | | |

---

## ELO range + honest labeling

| Option | Description | Selected |
|--------|-------------|----------|
| Full ladder 600–2600 | Reuse `MAIA_ELO_LADDER` exactly as the analysis board does | ✓ |
| Validated band 1100–2000 | Most defensible, but locks out beginners and strong users | |
| A handful of presets | Named chips; new picker convention | |

| Option | Description | Selected |
|--------|-------------|----------|
| "ELO" + honest info popover | Keep the number, carry the caveat in a HelpCircle popover | ✓ |
| Apply a per-mode correction | Rejected: every harness cell is a clamped bound; manufactures precision | |
| Drop the number, use descriptors | Most honest, but throws away info users want | |

| Option | Description | Selected |
|--------|-------------|----------|
| User's rating, else 1500 | Mirrors `useMaiaEloDefault`'s shipped free-play rule | ✓ |
| Fixed 1500 for everyone | BOT-03 unarguable, but bad first experience for a 900-rated user | |
| User's rating minus a handicap | Invented constant, no evidence | |

**Notes:** The user added a load-bearing correction — the default rating **must be lichess-blitz
converted**, "like we do for the analysis board's ELO slider". Verification showed
`profile.current_rating` is the **raw platform rating** (inflated for chess.com users) and that the
analysis board only normalizes in *game* mode, not free-play. That produced two further questions:

| Option | Description | Selected |
|--------|-------------|----------|
| Expose the blitz anchor on `/users/me` | Derived from `user_rating_anchors` (already lichess-equivalent, already trusted by Phase 167) | ✓ |
| Convert `current_rating` client-side | Duplicates a Python conversion; noisier input | |
| Use whatever the analysis board uses | The inflated number the user just flagged | |

| Option | Description | Selected |
|--------|-------------|----------|
| Defer the analysis free-play fix | Real inconsistency, but not this phase's | |
| Fix both in this phase | One-line change once the profile field exists; the two ELO surfaces then agree | ✓ |

---

## Setup screen shape + lifecycle

| Option | Description | Selected |
|--------|-------------|----------|
| Pre-game screen on `/bots` | Replaces the D-14 stub branch; composes with the ResumeGate | ✓ |
| Modal over the board | Would mount with placeholder settings and remount on Start | |
| Separate `/bots/new` route | Deep-linkable, but adds routing surface and a redirect dance | |

| Option | Description | Selected |
|--------|-------------|----------|
| "New game" → back to setup, prefilled | Setup becomes the single entry point for every new game | ✓ |
| Instant rematch, same settings | Two start paths, settings state in two places | |
| You decide | | |

| Option | Description | Selected |
|--------|-------------|----------|
| Remember last-used settings (owner-scoped localStorage) | Reuses 170's key convention | ✓ |
| Always start from defaults | One less key, but a repeat player re-picks every game | |

| Option | Description | Selected |
|--------|-------------|----------|
| Color: White / Black / Random (resolved at Start) | Snapshot + PGN carry the real color | ✓ |
| White / Black only | Everyone picks white forever | |

| Option | Description | Selected |
|--------|-------------|----------|
| Default TC 5+3 blitz | Today's stub; the exercised path | |
| Default TC 10+0 rapid | More headroom on a phone; most slack for bot pacing | ✓ |
| Default TC 10+5 rapid | Most forgiving; slowest to demo | |

| Option | Description | Selected |
|--------|-------------|----------|
| No prewarm — rely on the opening book | 169.5 already warms during the book window | ✓ |
| Warm during setup | Requires hoisting provider construction out of `useBotGame` | |
| You decide | | |

---

## Nav, guest access + Library surfacing

| Option | Description | Selected |
|--------|-------------|----------|
| Library · Bots · Openings · Endgames | Keeps the two always-enabled items together, the import-gated ones at the end | ✓ |
| Library · Openings · Endgames · Bots | Splits the clickable items with two greyed ones | |
| Bots first | Demotes Library, which is the import CTA | |

| Option | Description | Selected |
|--------|-------------|----------|
| Mobile bottom bar — 4 items + More | 5 slots, the standard ceiling | ✓ |
| More drawer only | Bots would be the only page with no thumb-reachable entry | |

| Option | Description | Selected |
|--------|-------------|----------|
| Logged-out `/bots` → `/login` (today's behavior) | Guests enter via the existing Try-as-guest flow; SC3 still met | ✓ |
| Auto-mint a guest session on `/bots` | Best funnel, but mints accounts on route visit | |
| Public "Play as guest / Log in" screen at `/bots` | New public route surface | |

| Option | Description | Selected |
|--------|-------------|----------|
| Keep Analyze-the-line; add a confirmed "Saved to Library" link + guest caveat | Primary CTA never depends on the POST landing | ✓ |
| Repoint "Analyze this game" at the stored Library game | Fragile — the store is queued and may be pending | |
| Show the guest caveat on the setup screen | A downer pre-game; SC4 asks for it at game end | |

---

## Claude's Discretion

- Whether to reuse `EloSelector` or build a setup-specific picker (the `MAIA_ELO_LADDER` + clamp rule
  are locked; the widget is not).
- The visual convention for "Human preset active" while the slider has no valid thumb position.
- Exact copy for the ELO info popover, the play-style summary line, and the "Saved to your Library" /
  guest-caveat strings.

## Deferred Ideas

- Auto-minting a guest session on a tokenless `/bots` visit (shareable funnel).
- A public "Play as guest / Log in" chooser at `/bots`.
- Randomized, position-aware bot reveal delays so Human mode's tempo reads as human.
- Named bot personas / the 2D style layer (already SEED-098, future milestone).
- A calibrated, honest ELO label (SEED-101 → 102 → 103 → 104).
