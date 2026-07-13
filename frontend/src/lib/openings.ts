/**
 * This module has two DIFFERENT consumers querying the SAME parsed ECO data
 * (frontend/public/openings.tsv) in opposite directions:
 *
 * - `findOpening()` NAMES an already-played sequence: it walks `len` DOWN
 *   from the history length against `fullLineMap` (keyed by a line's FULL
 *   SAN sequence), returning the longest match. Used by useChessGame.ts.
 * - the bot's opening book (Phase 169.5) tests candidate LEGAL MOVES for
 *   book membership: for each candidate, it checks whether
 *   `[...history, candidateSan].join(' ')` is a member of `prefixSet` (every
 *   PREFIX of every line, not just full lines) — a fixed-length forward
 *   membership test, not a longest-match walk.
 *
 * Do not conflate the two lookup shapes — same source data, different query.
 */

export interface Opening {
  eco: string;
  name: string;
}

export interface OpeningLookup {
  fullLineMap: Map<string, Opening>;
  prefixSet: Set<string>;
}

/** Strip move numbers from PGN: "1. e4 c6 2. d4 d5" → "e4 c6 d4 d5" */
function pgnToSanSequence(pgn: string): string {
  return pgn
    .replace(/\d+\./g, '')
    .replace(/\s+/g, ' ')
    .trim();
}

let lookupPromise: Promise<OpeningLookup> | null = null;

function buildLookup(): Promise<OpeningLookup> {
  if (lookupPromise) return lookupPromise;
  lookupPromise = fetch('/openings.tsv')
    .then((r) => r.text())
    .then((text) => {
      const fullLineMap = new Map<string, Opening>();
      const prefixSet = new Set<string>();
      const lines = text.split('\n');
      // Skip header row
      for (let i = 1; i < lines.length; i++) {
        // safe: loop bound guarantees i < lines.length
        const line = lines[i]!.trim();
        if (!line) continue;
        const parts = line.split('\t');
        const eco = parts[0];
        const name = parts[1];
        const pgn = parts[2];
        if (eco && name && pgn) {
          const tokens = pgnToSanSequence(pgn).split(' ').filter(Boolean);
          fullLineMap.set(tokens.join(' '), { eco, name });
          // Insert every prefix of the line, not just the full line — the
          // opening book's candidate-membership test needs to know "is
          // history + one more move still a prefix of some ECO line".
          for (let len = 1; len <= tokens.length; len++) {
            prefixSet.add(tokens.slice(0, len).join(' '));
          }
        }
      }
      return { fullLineMap, prefixSet };
    })
    .catch((err) => {
      // Clear the cache so a later call can retry — otherwise a transient
      // fetch failure permanently breaks opening name lookup for the session.
      lookupPromise = null;
      throw err;
    });
  return lookupPromise;
}

/** Pre-load the openings database in the background. */
export function preloadOpenings(): void {
  // Swallow errors — the opening name is a cosmetic feature and a transient
  // fetch failure (dev server restart, offline, etc.) shouldn't surface as an
  // unhandled promise rejection. findOpening() will retry on next call.
  buildLookup().catch(() => {});
}

/**
 * Find the longest-matching opening for the given SAN move history.
 * Returns null at the starting position or if no match is found.
 */
export async function findOpening(moveHistory: string[]): Promise<Opening | null> {
  if (moveHistory.length === 0) return null;
  const { fullLineMap } = await buildLookup();
  for (let len = moveHistory.length; len > 0; len--) {
    const key = moveHistory.slice(0, len).join(' ');
    const opening = fullLineMap.get(key);
    if (opening) return opening;
  }
  return null;
}

/**
 * The set of every prefix (of every length) of every ECO line, keyed by
 * space-joined canonical SAN tokens — exactly what chess.js's `Move.san`
 * emits (verified by the corpus-parity test in openings.test.ts). Used by
 * the bot's opening book (Phase 169.5) to test "does history + candidateSan
 * stay inside book theory". Does NOT swallow fetch errors — the book's
 * caller decides how to react to a rejected promise (Phase 169.5 D-03:
 * latch permanently out of book on failure rather than silently degrade).
 */
export async function loadOpeningPrefixSet(): Promise<ReadonlySet<string>> {
  const { prefixSet } = await buildLookup();
  return prefixSet;
}
