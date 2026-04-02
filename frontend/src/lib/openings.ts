export interface Opening {
  eco: string;
  name: string;
}

/** Strip move numbers from PGN: "1. e4 c6 2. d4 d5" → "e4 c6 d4 d5" */
function pgnToSanSequence(pgn: string): string {
  return pgn
    .replace(/\d+\./g, '')
    .replace(/\s+/g, ' ')
    .trim();
}

let lookupPromise: Promise<Map<string, Opening>> | null = null;

function buildLookup(): Promise<Map<string, Opening>> {
  if (lookupPromise) return lookupPromise;
  lookupPromise = fetch('/openings.tsv')
    .then((r) => r.text())
    .then((text) => {
      const map = new Map<string, Opening>();
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
          map.set(pgnToSanSequence(pgn), { eco, name });
        }
      }
      return map;
    });
  return lookupPromise;
}

/** Pre-load the openings database in the background. */
export function preloadOpenings(): void {
  buildLookup();
}

/**
 * Find the longest-matching opening for the given SAN move history.
 * Returns null at the starting position or if no match is found.
 */
export async function findOpening(moveHistory: string[]): Promise<Opening | null> {
  if (moveHistory.length === 0) return null;
  const map = await buildLookup();
  for (let len = moveHistory.length; len > 0; len--) {
    const key = moveHistory.slice(0, len).join(' ');
    const opening = map.get(key);
    if (opening) return opening;
  }
  return null;
}
