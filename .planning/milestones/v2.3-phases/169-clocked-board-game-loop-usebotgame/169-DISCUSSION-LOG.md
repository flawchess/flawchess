# Phase 169: Clocked Board + Game Loop (`useBotGame`) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-12
**Phase:** 169-clocked-board-game-loop-usebotgame
**Areas discussed:** Bot draw/resign etiquette, Pacing & clock display, Sounds, Result screen & phase surface

---

## Bot draw/resign etiquette

| Option | Description | Selected |
|--------|-------------|----------|
| Eval-based accept | Accept when eval near-equal (expected score ~0.5 within threshold), reusing existing grading provider | |
| Eval + endgame gate | Accept only when eval near-equal AND past a material/move threshold (e.g. queens off or move 30+) | ✓ |
| Always decline | Bot never accepts; draws only via automatic rules | |

**User's choice:** Eval + endgame gate

| Option | Description | Selected |
|--------|-------------|----------|
| No, bot never offers | Bot only responds to user offers | ✓ |
| Yes, in dead-drawn endings | Proactive one-time offer under the same gate | |

**User's choice:** No, bot never offers (recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| No, plays to the end | Bot never resigns — mate practice for beginners, zero extra logic | ✓ |
| Resigns when clearly lost | Resign at hopeless eval for several consecutive moves | |

**User's choice:** No, plays to the end (recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Confirm resign + throttle draws | Resign confirmation; after a decline, wait ~5 of your moves before re-offering | ✓ |
| Confirm resign only | Unlimited draw offers | |
| No guards | One-tap resign, unlimited offers | |

**User's choice:** Confirm resign + throttle draws (recommended)

---

## Pacing & clock display

| Option | Description | Selected |
|--------|-------------|----------|
| Tick real-time, debit = max(real, synthetic) | Clock ticks naturally during think; final debit is the larger of real elapsed and scripted synthetic; clamped never-flag | ✓ |
| Animate toward synthetic target | Scaled tick rate landing exactly on the synthetic value at reveal | |
| Freeze, then deduct on reveal | Clock stands still, one jump at reveal | |

**User's choice:** Tick real-time, debit = max(real, synthetic) (recommended)
**Notes:** Claude flagged the interaction with the locked "bot never flags" rule → final debit clamped so the bot's clock never reaches zero (named-constant floor).

| Option | Description | Selected |
|--------|-------------|----------|
| Subtle indicator | Pulsing dot / ellipsis next to bot's name/clock during think | ✓ |
| No indicator | Ticking clock is the only signal | |

**User's choice:** Subtle indicator (recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Lichess-style | Tenths under ~10s + active clock red/urgent | ✓ |
| Color warning only | Red under threshold, whole seconds | |
| No special treatment | Plain mm:ss | |

**User's choice:** Lichess-style (recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Claude's discretion | Debit params (divisor N, increment share, jitter) + reveal-delay range tuned by feel as named constants | ✓ |
| Set ballpark now | Lock concrete values in CONTEXT.md | |

**User's choice:** Claude's discretion (recommended)

---

## Sounds

| Option | Description | Selected |
|--------|-------------|----------|
| Lichess sound set | Vendor standard lichess sounds; AGPL-compatible with attribution | ✓ |
| CC0 / freesound assets | Permissively-licensed curated sounds | |
| Synthesized (Web Audio) | Generated tones, no assets | |

**User's choice:** Lichess sound set (recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Low-time warning | One alert when user's clock first crosses ~10s | ✓ |
| Castling/promotion distinct | Distinct sounds for castling/promotion | |
| Draw-offer/decline blip | Notification blip when bot declines a draw offer | ✓ |
| None — just the four | Only move/capture/check/game-end | |

**User's choice (multi-select):** Low-time warning + Draw-offer/decline blip

| Option | Description | Selected |
|--------|-------------|----------|
| Default ON, persist mute | Mute toggle on game screen, localStorage-persisted boolean | ✓ |
| Default ON + volume slider | Persisted volume level plus mute | |
| Default OFF, opt-in | Silent until unmuted | |

**User's choice:** Default ON, persist mute (recommended)

---

## Result screen & phase surface

| Option | Description | Selected |
|--------|-------------|----------|
| Dismissible dialog | Compact modal + persistent inline result strip after dismiss | ✓ |
| Inline panel only | No modal; result panel beside/below board | |
| Full modal only | Modal only; actions homeless after dismiss | |

**User's choice:** Dismissible dialog (recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Deep-link with moves now | /analysis via existing `line` param; 171 upgrades to stored game_id | ✓ |
| Stub until 171 | Button disabled/hidden in 169 | |

**User's choice:** Deep-link with moves now (recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Move list + view-back | Linear SAN list; view-only step-back, snaps to live on new move | ✓ |
| Move list, no navigation | List only, board always live | |
| No move list during play | Board + clocks only | |

**User's choice:** Move list + view-back (recommended)

| Option | Description | Selected |
|--------|-------------|----------|
| Final route, unlinked | Real lazy-loaded /bots route with hardcoded-settings start stub; 171 replaces stub + adds nav | ✓ |
| Dev-only route | Throwaway /dev/bot-game deleted in 171 | |
| Components + tests only | No route until 171 | |

**User's choice:** Final route, unlinked (recommended)

---

## Claude's Discretion

- Synthetic-debit parameters (divisor N, increment share, jitter), exact reveal-delay range, never-flag clamp floor
- D-01 eval band + endgame gate definition; draw-throttle count
- Audio implementation approach (HTMLAudioElement vs Web Audio), preloading, asset format
- Interim /bots start-stub shape; component/file layout; promotion-picker UX; board orientation defaults

## Deferred Ideas

- Premove (new capability, own phase/seed if wanted)
- Bot proactively offering draws / resigning lost positions (rejected D-02/D-03)
- Volume slider / per-event sound settings
- TC-scaled cosmetic pacing envelope (stays deferred per SEED-096 / 168.5)
