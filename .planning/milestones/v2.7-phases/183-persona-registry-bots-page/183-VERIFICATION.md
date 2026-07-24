---
phase: 183-persona-registry-bots-page
verified: 2026-07-22T10:26:33Z
status: passed
human_review_resolved: 2026-07-24  # operator confirmed all 3 human_verification items passed on the shipped-to-prod roster at v2.7 close (see 183-UAT.md Resolution); WR-01/IN-02/AVAT-01 accepted as tracked non-blocking follow-ups
score: 5/5 must-haves verified
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "Review the full 24-persona roster (names, species, bios) in the Bots page grid + detail surface"
    expected: "Names/species/bios read well, are distinct, tonally consistent, and each bio's per-tier arc actually lands (e.g. Trickster reads as trap-lines-early/swindle-mode-late) — content quality is a subjective call the plan itself deferred to human review (D-13, mirrors Phase 182's curated-opening-lines process)"
    why_human: "D-13 explicitly requires human review/swap-on-request of authored content; 183-01-SUMMARY.md itself flags this coverage item as human_judgment: true and status unknown"
  - test: "Visually browse /bots on both desktop and mobile: 4 style sections in order, 24 cards with emoji-on-tint avatars, tilde ELO labels, Custom entry; tap a persona, confirm the detail dialog's bio/chips/Play look correct and the mobile anchor doesn't clip"
    expected: "Grid and detail surface are legible and usable at mobile width; per-style tints are visually distinct enough (note the Wall wall-1200/wall-1800 shared turtle-emoji gap flagged by code review, IN-02)"
    why_human: "Visual layout/responsiveness/legibility cannot be verified by grep or unit tests"
  - test: "Play a full game against a persona (ideally a Wall/negative-contempt persona to trigger an outgoing offer sooner) through to checkmate/timeout/resignation while a bot draw offer is live, and separately through Accept/Decline"
    expected: "Persona avatar+name show in the clock strip; the draw-offer banner appears with working Accept/Decline and disappears on your next move; result dialog/strip name the persona and offer Rematch/New opponent — BUT note the confirmed WR-01 gap below: if the game ends via resignation or a clock flag (not via your own next move) while an offer is live, the banner currently keeps rendering, stacked with the result dialog"
    why_human: "End-to-end async engine/timing behavior (draw-offer trigger timing, clock races) is not fully exercised by the unit-test suite per 183-03-SUMMARY.md's own coverage note (D5, human_judgment: true)"
---

# Phase 183: Persona Registry & Bots Page Verification Report

**Phase Goal:** Users can browse and start a game against any of 24 named bot personas — each a complete pinned opponent (preset, provisional ELO label, style params, opening book, resign/draw policy, avatar, bio) — while Custom mode keeps exposing the raw (ELO, preset) knobs unchanged.
**Verified:** 2026-07-22T10:26:33Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User can browse a grid of 24 personas on the Bots page (4 styles × 6 rungs), each showing name, avatar portrait, bio, style, and ELO label | ✓ VERIFIED | `PersonaGrid.tsx` iterates `STYLE_SECTION_ORDER` × `personasForSection`; `PersonaCard.tsx` renders avatar+name+`~rung`; `PersonaDetailSurface.tsx` shows full bio + style. 24 unique ids confirmed via grep. `PersonaGrid.test.tsx`/`PersonaCard.test.tsx` (11 tests) + `Bots.test.tsx` grid-by-default tests all pass. |
| 2 | User can start a game against any persona in one action; game launches with the persona's full pinned config, no separate persona/strength step | ✓ VERIFIED | `PersonaDetailSurface.handlePlay` builds `BotGameSettings` with `botElo`, `blend`, `style: BOT_STYLE_BUNDLES[persona.style]` (by reference, confirmed via source read), resolved color, TC-derived `baseSeconds`/`incrementSeconds`, `personaId` — calls `onStart` (= `Bots.tsx`'s single `handleStart`) exactly once. Grep confirms neither `EloSelector` nor `PlayStyleControl` is imported. `PersonaDetailSurface.test.tsx` (8 tests) pins settings shape + reference identity. |
| 3 | Persona roster is one typed registry mapping each of 24 slots to its complete config, rung's preset per measured ranges (800-1400 Human, 1600 Light/Deep, 1800 Deep) | ✓ VERIFIED | `personaRegistry.ts`'s `PERSONA_REGISTRY: Record<PersonaId, Persona>` is compile-time exhaustive over the 24-id template-literal union; `RUNG_BLEND` maps 800/1000/1200/1400→`HUMAN_BLEND`, 1800→`DEEP_BLEND`; each of the 4 rung-1600 personas explicitly picks `LIGHT_BLEND` or `DEEP_BLEND` with an inline per-style rationale (2 Light: Attacker/Wall, 2 Deep: Trickster/Grinder). `personaRegistry.test.ts` (22 tests) passes; `npx tsc -b` zero errors. |
| 4 | User can still choose Custom mode and configure a bot via the existing raw (ELO, preset) controls, unaffected by the new persona roster | ✓ VERIFIED | `git log` confirms no Phase-183 commit touches `SetupScreen.tsx` (last commit `ba1b6092`, pre-dates this phase). `Bots.tsx`'s `showCustomSetup` branch renders the unmodified `<SetupScreen onStart={handleStart} .../>` behind a sibling back-button, never a wrapper. `SetupScreen.tsx` builds settings with no `personaId` reference (grep confirms), so Custom-mode settings carry `personaId === undefined` by construction. |
| 5 | Each persona's bio conveys a per-tier identity story; avatar is a curated AI-generated portrait consistent with a single style prompt | ⚠️ PARTIAL (accepted per D-16) | Bio half VERIFIED: all 24 bios read the per-tier arc (e.g. `trickster-800` "shiny trap... simple traps" vs `trickster-1600` "swindle mode... high-variance" vs `trickster-1800` "chaos... backed by real calculation"); `personaRegistry.test.ts` asserts non-empty/distinct/trimmed. Avatar half is INTENTIONALLY incomplete per locked decision D-16 ("Phase ships with placeholders; real art lands later" — AVAT-01 explicitly left open). Placeholder emoji-on-tint avatars ship instead (D-18), plus a committed `personaAvatarPrompts.md` (master style prompt + all 24 per-persona descriptors) for the deferred real-art PR. REQUIREMENTS.md correctly reflects this: AVAT-01 `[ ] Pending`, AVAT-02 `[x] Complete`. |

**Score:** 5/5 truths verified (criterion 5's avatar half judged against the recorded D-16 deviation, not the raw roadmap text, per the verification brief's instruction)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `frontend/src/lib/personas/personaRegistry.ts` | 24-slot exhaustive registry | ✓ VERIFIED | 461 lines; `PERSONA_REGISTRY`, `RUNG_BLEND`, `STYLE_SECTION_ORDER`, `personasForSection`, `personaForId`, `personaFor` all present and exported; 24 unique persona ids grep-confirmed |
| `frontend/src/lib/personas/personaAvatars.ts` | Placeholder-avatar helpers | ✓ VERIFIED | `PERSONA_STYLE_TINT`, `placeholderAvatarFor`, `resolveAvatarSrc`; no glob/static image imports (grep-confirmed, only doc-comment mentions) |
| `frontend/src/lib/personas/botPersonaSetupSettings.ts` | Last-used color/TC persistence, new key prefix | ✓ VERIFIED | 134 lines, distinct key prefix from `botSetupSettings.ts`; 16 tests pass |
| `frontend/src/data/personaAvatarPrompts.md` | Master prompt + 24 descriptors | ✓ VERIFIED | 128 lines; all 24 "Name the Species" persona names present |
| `frontend/src/components/bots/PersonaGrid.tsx` | Default browse view | ✓ VERIFIED | 70 lines; 4 sections × 6 cards + Custom entry |
| `frontend/src/components/bots/PersonaCard.tsx` | Persona tile | ✓ VERIFIED | 61 lines; avatar/name/tilde-label, `aria-label`, `data-testid` |
| `frontend/src/components/bots/PersonaDetailSurface.tsx` | Bio + chips + Play | ✓ VERIFIED | 272 lines; Dialog with bio, reused `CHIP_*` color/TC chips, single Play button |
| `frontend/src/components/bots/BotDrawOfferBanner.tsx` | Non-blocking draw-offer banner | ✓ VERIFIED (see WARNING below) | 54 lines; renders only when `offerLive`, Accept/Decline wired |
| `frontend/src/lib/botDrawGate.ts` (`wouldBotOfferDraw`) | Outgoing draw-offer predicate | ✓ VERIFIED | Pure, null-sentinel-first, contempt-shifted band+floor+cooldown; 8 new unit tests, 26/26 total pass |
| `frontend/src/hooks/useBotGame.ts` (`personaId`, `botDrawOffer`, `acceptBotDraw`, `declineBotDraw`) | Persona identity + draw-offer state | ✓ VERIFIED (see WARNING below) | Additive `personaId?: PersonaId`; snapshot round-trips without a version bump (`CURRENT_SNAPSHOT_VERSION` still `1`); single `pool.grade(` call site confirmed |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `persona.style` | `BOT_STYLE_BUNDLES[style]` | reference lookup | ✓ WIRED | `PersonaDetailSurface.tsx:190` `style: BOT_STYLE_BUNDLES[persona.style]` — source-read confirms no spread/clone |
| `PersonaDetailSurface` Play | `Bots.tsx handleStart` | `onStart` prop | ✓ WIRED | Single call site; `SetupScreen`'s Start calls the same `handleStart` — no parallel start path (grep + source read) |
| `settings.personaId` | `PERSONA_REGISTRY` | `personaFor(settings)` | ✓ WIRED | One shared helper in `personaRegistry.ts`; grep for inline re-implementation (`personaId ? PERSONA_REGISTRY[...]`) returns zero hits outside the helper itself |
| `BotDrawOfferBanner` Accept/Decline | `useBotGame` `acceptBotDraw`/`declineBotDraw` | props | ✓ WIRED | `Bots.tsx:471-476` passes `game.acceptBotDraw`/`game.declineBotDraw` directly |
| Rematch button | `BotsPage.handleStart` | `onRematch` prop | ✓ WIRED | `Bots.tsx` threads `onRematch={handleStart}` through both the fresh-start and resumed-snapshot `BotsGame` mounts; `handleRematch` calls `onRematch(settings)` with the same settings reference |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Targeted persona/draw-offer/snapshot/result-copy test files | `npm test -- --run <10 files>` | 123/123 tests pass | ✓ PASS |
| `Bots.tsx` page-level integration | `npm test -- --run src/pages/__tests__/Bots.test.tsx` | 31/31 pass | ✓ PASS |
| Full frontend suite (regression check) | `npm test -- --run` | 182 files / 2490 tests pass | ✓ PASS |
| Type safety | `npx tsc -b` | zero errors | ✓ PASS |
| Dead-export check | `npm run knip` | zero issues | ✓ PASS |
| Lint | `npm run lint` | zero errors (3 pre-existing unrelated warnings in `coverage/`) | ✓ PASS |
| `SetupScreen.tsx` untouched | `git log -1 -- frontend/src/components/bots/SetupScreen.tsx` | last commit `ba1b6092`, pre-dates all `183-*` commits | ✓ PASS |
| `finalizeGame` clears `botDrawOffer` on every end path | source read of `useBotGame.ts:766-795` (`finalizeGame`) vs. the 4 actual clear sites (`commitMove` user-move gate, `acceptBotDraw`, `declineBotDraw`, `newGame`) | `finalizeGame` itself never touches `botDrawOfferRef`/`setBotDrawOffer`; `resign()` and `flagIfOutOfTime` call `finalizeGame` directly, bypassing `commitMove`'s clear | ✗ FAIL (see WARNING WR-01) |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| PERS-01 | 183-04 | Browse 24-persona roster | ✓ SATISFIED | `PersonaGrid`/`PersonaCard`; REQUIREMENTS.md `[x] Complete` |
| PERS-02 | 183-02/03/04/05 | One-action start, full pinned config, no strength picker | ✓ SATISFIED | `PersonaDetailSurface.handlePlay`; REQUIREMENTS.md `[x] Complete` |
| PERS-03 | 183-01 | Single typed registry, rung→preset per measured ranges | ✓ SATISFIED | `PERSONA_REGISTRY`/`RUNG_BLEND`; REQUIREMENTS.md `[x] Complete` |
| PERS-04 | 183-03/04 | Custom mode unaffected | ✓ SATISFIED | `SetupScreen.tsx` byte-unchanged; REQUIREMENTS.md `[x] Complete` |
| AVAT-01 | 183-01/04/05 | 24 AI-generated portraits, curated, committed | ✗ INTENTIONALLY OPEN | D-16 locked decision defers real art; placeholders + prompts ship instead; REQUIREMENTS.md correctly shows `[ ] Pending` |
| AVAT-02 | 183-01/04/05 | Name + bio conveying per-tier identity story | ✓ SATISFIED | 24 authored bios with per-tier arcs; REQUIREMENTS.md `[x] Complete` |

No orphaned requirements: the union of all 5 plans' frontmatter `requirements` fields (PERS-01/02/03/04, AVAT-01/02) exactly matches the phase's declared requirement IDs and REQUIREMENTS.md's Phase-183 rows.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `frontend/src/hooks/useBotGame.ts` | 766-795 (`finalizeGame`) | Missing state clear | WARNING | **Confirmed, reproducible, unfixed.** The bot's outgoing draw-offer flag (`botDrawOfferRef`/`botDrawOffer`) is cleared only by a user-move commit (`commitMove`, gated on `mover === settings.userColor`), `acceptBotDraw`, `declineBotDraw`, and `newGame` — never by `finalizeGame` itself. `resign()` and `flagIfOutOfTime` (clock flag) call `finalizeGame` directly, bypassing `commitMove`. Reproducible sequence: bot raises a draw offer → user resigns (or flags on time) instead of moving → `BotDrawOfferBanner` keeps rendering with live Accept/Decline, stacked with the just-opened `GameResultDialog`. Already identified and documented with a fix in `183-REVIEW.md` (WR-01) but the fix was never applied — no commit after `be644dc5` (the review commit) touches `finalizeGame`. Clicking Accept/Decline post-game is functionally harmless (both guard/no-op correctly), so this is a UI-polish bug, not a data-integrity or blocking issue. |
| `frontend/src/components/bots/PersonaDetailSurface.tsx` | 175-176 | Magic numbers | INFO | Hardcoded `600`/`0` TC fallbacks instead of reusing `SetupScreen.tsx`'s `DEFAULT_BOT_SETUP_SETTINGS` constant (CLAUDE.md "no magic numbers" rule). Documented as `183-REVIEW.md` WR-02, not fixed. Low practical impact — `findPresetByLabel(DEFAULT_TC_PRESET_LABEL)` should always resolve, making this fallback branch effectively dead in normal operation. |
| `frontend/src/lib/personas/personaRegistry.ts` | 373, 413 | Duplicate placeholder emoji | INFO | `wall-1200` (Turtle 🐢) and `wall-1800` (Armadillo 🐢) share both emoji AND style tint, undocumented (unlike the cross-style Wolverine/Coyote 🐺 collision, which IS documented). `183-REVIEW.md` IN-02, cosmetic only. |
| `frontend/src/pages/Bots.tsx` | 436-437 | Unguarded concurrent interaction | INFO | The user's own "Offer draw" button (`canOfferDraw`) isn't gated on `game.botDrawOffer` — a user can start their own offer while the bot's offer is still live. Both paths are individually safe. `183-REVIEW.md` IN-03, cosmetic only. |

No TBD/FIXME/XXX debt markers found in the phase's modified files.

### Human Verification Required

1. **Roster content review (D-13)** — Names/species/bios are Claude-authored per convention and explicitly deferred to human review/swap in the plan itself (`183-01-SUMMARY.md` D4: `human_judgment: true`, `status: unknown`).
2. **Visual/responsive check of the persona grid + detail surface** on desktop and mobile — layout, avatar tint legibility, the documented Wall turtle/armadillo emoji collision.
3. **End-to-end playtest of the in-game persona presence** (clock strip, draw-offer banner, result copy, rematch) — async engine timing behavior that the unit suite doesn't fully exercise per `183-03-SUMMARY.md`'s own D5 coverage note (`human_judgment: true`); also a natural point to decide whether WR-01 (dangling draw-offer banner after a non-move game end) needs a fix before this phase is considered fully done, or can ship as a tracked follow-up.

### Gaps Summary

No must-have truth, artifact, or key link failed — all 5 roadmap success criteria are met in the codebase (criterion 5's avatar half correctly and transparently deferred per the team's own locked D-16 decision, with REQUIREMENTS.md AVAT-01 marked `Pending` rather than falsely marked complete). All 182 frontend test files (2490 tests) pass, `tsc -b`/`lint`/`knip` are clean, and every prohibition/backstop declared across the 5 plans' frontmatters was independently confirmed true by direct source reading (style-bundle reference discipline, snapshot version safety, single start path, `SetupScreen.tsx` untouched, no eager avatar-import machinery).

Status is `human_needed` rather than `passed` for two reasons: (1) the plan's own D-13 decision explicitly requires human review of the authored roster content before it's truly "done," and (2) a real, reproducible WARNING-tier bug (WR-01, the dangling post-game draw-offer banner) was found during code review and remains unfixed — it doesn't block any of the 5 named success criteria but is worth a human call on whether to fix now or track as a fast-follow.

---

_Verified: 2026-07-22T10:26:33Z_
_Verifier: Claude (gsd-verifier)_
