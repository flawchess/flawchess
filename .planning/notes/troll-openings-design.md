---
title: Troll-opening watermark on Insights findings — design decisions
date: 2026-04-28
context: Pre-discuss-phase design notes for the troll-openings watermark feature
related_phases: [77]
related_files:
  - frontend/src/components/openings/OpeningFindingCard.tsx
  - frontend/src/components/openings/OpeningInsightsBlock.tsx
  - app/services/opening_insights_service.py
  - app/schemas/insights.py
  - temp/Troll-Face.svg
---

# Troll-opening watermark on Insights findings — design decisions

Captured during `/gsd-explore` on 2026-04-28. Feeds the eventual `/gsd-discuss-phase` for
Phase 77 so we don't relitigate the matching strategy or visual spec.

## Goal

When the Opening Insights finding card shows a position the user reached by playing a
known "troll" opening (Bongcloud, Grob, Borg, Englund Gambit, etc. — see Lichess study
[cEDAMVBB](https://lichess.org/study/cEDAMVBB/DYKeAEFt)), render a Troll-Face SVG as a
subtle watermark behind the card content. Pure visual easter egg, no behavioral change.

## Final spec

### Matching

- **Side-only hash, not full Zobrist hash.** Troll openings are characterized by what the
  user plays, regardless of opponent response. Matching by `white_hash` (when user is
  white) or `black_hash` (when user is black) captures every variation transposing into
  the same user-side position. Same architectural pattern as the existing system opening
  filter.
- **User played it, not faced it.** The watermark fires only when the user themselves
  played the troll moves. Finding cards in the Insights block are already user-position
  scoped, so this falls out naturally — no extra data needed about the opponent.
- **Color inferred from finding context.** The finding's candidate move is from a
  specific position with a known side-to-move. Side-to-move = user color in this view.
- **Boolean signal on the finding payload.** Backend computes `is_troll_opening: bool`
  on each `OpeningInsightFinding`. Frontend reads it and conditionally renders the
  watermark. No frontend hash matching.

### Visual

- **30% opacity watermark.** Troll-Face.svg sits behind the card content, no badge, no
  label, no tooltip. Reads as an easter egg for users who notice; invisible to users who
  don't care.
- **Finding card only.** Not on the Move Explorer, not on bookmarks, not on the moves
  list. Just the rule-based Insights finding card on the Openings → Insights subtab.
- **Mobile parity.** Same opacity, same positioning. Re-verify at 375px that the SVG
  doesn't break the card's text contrast or scroll behavior.
- **Asset move.** `temp/Troll-Face.svg` → `frontend/src/assets/troll-face.svg` (kebab-case
  per repo convention).

### Data sourcing

- **Hybrid: scrape then curate.** Pull the full PGN from
  `https://lichess.org/study/cEDAMVBB.pgn`, parse with python-chess, extract the defining
  position of each chapter. Hand-filter to the openings that are actually trolly —
  Englund / Latvian / Borg are played seriously at low ratings and should probably be
  excluded so the watermark doesn't feel like an unfair burn on legitimate experimenters.
- **Defining position only**, not every position along the line. The trolly identity is
  established once the characteristic move(s) are on the board. One side-hash per opening
  per color.
- **Static TSV.** `app/data/troll_openings.tsv` with columns `name`, `color`, `side_hash`
  (and optionally `defining_moves` for human readability). Loaded into an in-memory
  `frozenset[int]` per color at app startup, mirroring how `app/data/openings.tsv` is
  consumed by `seed_openings.py`. No DB table needed — the set is small (likely 20-30
  entries) and read-only.
- **Curation script** in `scripts/`, similar to existing `seed_openings.py` —
  deterministic, regeneratable, committed alongside the TSV so the data path is
  reproducible.

## Out of scope

- Loud "Troll Opening Detected" labels, tooltips, or badges. Watermark only.
- Scoring/severity adjustments based on troll status. The card's classification logic
  stays unchanged — troll openings already tend to skew negative on score, so the
  existing rule-based card will surface them naturally; the watermark is purely
  decorative.
- Move Explorer surface. Not in v1 of this feature.
- Endgame / time management cards. Insights block on Openings only.
- Per-user opt-out. The joke is not so loud that it warrants a setting.

## Open questions for `/gsd-discuss-phase`

- Whether to include the "fun but legitimate" gambits (Englund, Latvian, Borg, Halloween)
  in the curated set, or strictly bongcloud-tier troll moves. Tone calibration call.
- Whether the watermark should be skipped when the finding's `severity` is "major" on the
  positive side (i.e. user is *winning* with the troll opening). Probably no — the joke
  lands harder when you've trolled successfully — but worth a one-line discuss-phase
  decision.
- Exact CSS positioning: centered behind text, anchored bottom-right, or filling the
  card? 30% opacity is locked, but layout isn't.
