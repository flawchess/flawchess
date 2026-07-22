/**
 * styleOpeningLines — curated per-style, per-color opening-book SAN-prefix
 * lines (Phase 182, STYLE-01, D-05).
 *
 * Purpose: the bot's opening book (`openingBook.ts`, Phase 169.5) tests
 * candidate legal moves for book membership via a joined move-history
 * prefix key (`[...history, candidateSan].join(' ')`). This module supplies
 * the per-style "menu" of prefixes that Plan 04's `styleBookWeighting`
 * boosts within that existing seam (D-04: a persona re-weights what is on
 * the menu, it never changes the menu or the exit rules).
 *
 * Every curated string uses the SAME normalized shape `openings.ts` builds
 * its `prefixSet` keys in: space-joined SAN tokens with move numbers
 * stripped (e.g. the Bongcloud prefix is `e4 e5 Ke2`), sourced from the real
 * ECO corpus at `frontend/public/openings.tsv`. A curated string that is not
 * a genuine prefix of some line in that corpus can never be booked (D-05) —
 * `__tests__/styleOpeningLines.test.ts` proves every entry below is a member
 * of the real `loadOpeningPrefixSet()` output.
 *
 * Split by color mirrors `frontend/src/data/trollOpenings.ts`'s
 * `WHITE_TROLL_KEYS`/`BLACK_TROLL_KEYS` convention (RESEARCH.md Open
 * Question #3): a style line curated as "White plays the London" only
 * applies when the bot is White. `styleLinesFor(style, side)` picks the
 * correct set from `chess.turn()` at the caller's call site (Plan 04/07).
 *
 * This is pure exported data — no chess.js, no I/O, no React. Lists are kept
 * modest (first ~8 plies) but recognizable: the goal is a perceptible
 * early-game identity (SEED-098's cheapest lever), not exhaustive coverage.
 * User reviews these lists during UAT per D-05.
 */

import type { Side } from './types';

/** The 4 named bot playstyles this phase ships (D-02). No style names leak
 * into the engine transforms themselves (D-01) — this union exists only to
 * key curated data and bundle lookups (Plan 03/05). */
export type Style = 'Attacker' | 'Trickster' | 'Grinder' | 'Wall';

// ─── Attacker — gambits / attacking systems ────────────────────────────────
// White plays the gambit; Black plays an aggressive/complicating reply as
// second player. Sourced by grepping openings.tsv for the classic gambit
// families (King's/Danish/Evans/Smith-Morra on the White side; Latvian/
// Englund/Budapest/Albin on the Black side).

/** White-side Attacker lines: King's Gambit, King's Gambit Accepted, Danish
 * Gambit, Smith-Morra Gambit, Evans Gambit. */
export const ATTACKER_WHITE_LINES: ReadonlySet<string> = new Set([
  'e4 e5 f4', // King's Gambit
  'e4 e5 f4 exf4', // King's Gambit Accepted
  'e4 e5 d4 exd4 c3', // Danish Gambit
  'e4 c5 d4 cxd4 c3', // Sicilian Defense: Smith-Morra Gambit
  'e4 e5 Nf3 Nc6 Bc4 Bc5 b4', // Italian Game: Evans Gambit
]);

/** Black-side Attacker lines: Englund Gambit, Latvian Gambit, Budapest
 * Defense, Albin Countergambit. */
export const ATTACKER_BLACK_LINES: ReadonlySet<string> = new Set([
  'd4 e5', // Englund Gambit
  'e4 e5 Nf3 f5', // Latvian Gambit
  'd4 Nf6 c4 e5', // Indian Defense: Budapest Defense
  'd4 d5 c4 e5', // Queen's Gambit Declined: Albin Countergambit
]);

// ─── Trickster — troll / swindle / trap lines ──────────────────────────────
// Sourced from the troll openings named in `trollOpenings.ts`'s provenance
// comments (Bongcloud, Hammerschlag, Halloween, Sodium, Napoleon, Grob,
// Barnes, Borg) plus a couple of additional swindle/trap defenses, split by
// which color plays the characteristic move. `trollOpenings.ts` stores
// user-side FEN keys, not SAN lines — these are freshly curated (D-05).

/** White-side Trickster lines: Bongcloud Attack, Barnes Opening:
 * Hammerschlag, Four Knights: Halloween Gambit, Sodium Attack, King's Pawn
 * Game: Napoleon Attack, Grob Opening, Barnes Opening. */
export const TRICKSTER_WHITE_LINES: ReadonlySet<string> = new Set([
  'e4 e5 Ke2', // Bongcloud Attack
  'f3 e5 Kf2', // Barnes Opening: Hammerschlag
  'e4 e5 Nf3 Nc6 Nc3 Nf6 Nxe5', // Four Knights Game: Halloween Gambit
  'Na3', // Sodium Attack
  'e4 e5 Qf3', // King's Pawn Game: Napoleon Attack
  'g4', // Grob Opening
  'f3', // Barnes Opening
]);

/** Black-side Trickster lines: Borg Defense, Zukertort Opening: Drunken
 * Knight Variation, Fried Fox Defense. */
export const TRICKSTER_BLACK_LINES: ReadonlySet<string> = new Set([
  'e4 g5', // Borg Defense
  'Nf3 f6 e4 Nh6', // Zukertort Opening: Arctic Defense, Drunken Knight Variation
  'e4 f6 d4 Kf7', // Fried Fox Defense
]);

// ─── Grinder — exchange / simplifying variations ───────────────────────────
// White initiates the trade in the classic Exchange lines; Black steers
// toward well-known solid/drawish structures (Petrov, Berlin, Slav) that
// trade down early rather than fight for the initiative.

/** White-side Grinder lines: Ruy Lopez Exchange, Slav Exchange, QGD
 * Exchange, French Exchange. */
export const GRINDER_WHITE_LINES: ReadonlySet<string> = new Set([
  'e4 e5 Nf3 Nc6 Bb5 a6 Bxc6', // Ruy Lopez: Exchange Variation
  'd4 d5 c4 c6 cxd5', // Slav Defense: Exchange Variation
  'd4 Nf6 c4 e6 Nc3 d5 cxd5', // Queen's Gambit Declined: Exchange Variation
  'e4 e6 d4 d5 exd5', // French Defense: Exchange Variation
]);

/** Black-side Grinder lines: Petrov's Defense, Ruy Lopez Berlin Defense,
 * Slav Defense. */
export const GRINDER_BLACK_LINES: ReadonlySet<string> = new Set([
  'e4 e5 Nf3 Nf6', // Petrov's Defense
  'e4 e5 Nf3 Nc6 Bb5 Nf6', // Ruy Lopez: Berlin Defense
  'd4 d5 c4 c6', // Slav Defense
]);

// ─── Wall — system openings ─────────────────────────────────────────────────
// White plays a fixed setup (London/Colle) largely independent of Black's
// reply; Black mirrors the defensive-system identity with Caro-Kann-type
// solidity and the Stonewall Dutch structure (D-05 explicitly names both).

/** White-side Wall lines: London System (vs ...Nf6/...e6 and vs ...d5),
 * Colle System (vs ...d5/...Nf6). */
export const WALL_WHITE_LINES: ReadonlySet<string> = new Set([
  'd4 Nf6 Nf3 e6 Bf4', // Indian Defense: London System
  'd4 d5 Nf3 Nf6 Bf4', // Queen's Pawn Game: London System
  'd4 d5 Nf3 Nf6 e3', // Queen's Pawn Game: Colle System
]);

/** Black-side Wall lines: Caro-Kann Defense (bare + main line), Dutch
 * Defense: Stonewall Variation (Modern Variation). */
export const WALL_BLACK_LINES: ReadonlySet<string> = new Set([
  'e4 c6', // Caro-Kann Defense
  'e4 c6 d4 d5', // Caro-Kann Defense (main line)
  'd4 f5 c4 e6 Nf3 Nf6 g3 c6', // Dutch Defense: Stonewall Variation, Modern Variation
]);

/** Shared empty sentinel — `styleLinesFor` returns THIS, never `undefined`,
 * for a style/color pairing with no curated lines. */
const EMPTY_LINES: ReadonlySet<string> = new Set();

/** Per-style, per-color lookup table. `Record<Style, ...>` makes TypeScript
 * enforce all 4 styles are present; both colors are always defined here
 * (even a style with a currently-empty color would list `EMPTY_LINES`
 * explicitly, not omit the key). */
const STYLE_LINES: Record<Style, { white: ReadonlySet<string>; black: ReadonlySet<string> }> = {
  Attacker: { white: ATTACKER_WHITE_LINES, black: ATTACKER_BLACK_LINES },
  Trickster: { white: TRICKSTER_WHITE_LINES, black: TRICKSTER_BLACK_LINES },
  Grinder: { white: GRINDER_WHITE_LINES, black: GRINDER_BLACK_LINES },
  Wall: { white: WALL_WHITE_LINES, black: WALL_BLACK_LINES },
};

/**
 * Returns the curated SAN-prefix set for `style` on the given `side`.
 *
 * Mirrors `trollOpenings.ts`'s WHITE/BLACK split (RESEARCH.md Open Question
 * #3): callers pick the color that matches whose turn it is to move.
 * Defensively never returns `undefined` — a style/color pairing with no
 * curated lines (or, at runtime, an unrecognized style value slipping past
 * TypeScript via an external cast) resolves to an empty `ReadonlySet`
 * (STYLE-01 empty edge), so callers can always safely iterate/`.has()` the
 * result without an extra null check.
 */
export function styleLinesFor(style: Style, side: Side): ReadonlySet<string> {
  const entry = STYLE_LINES[style];
  if (!entry) return EMPTY_LINES;
  const lines = side === 'w' ? entry.white : entry.black;
  return lines ?? EMPTY_LINES;
}
