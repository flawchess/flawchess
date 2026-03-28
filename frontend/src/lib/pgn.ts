/** Parse PGN string like "1. e4 e5 2. Nf3" into SAN array ["e4", "e5", "Nf3"] */
export function pgnToSanArray(pgn: string): string[] {
  return pgn
    .replace(/\d+\./g, '')
    .split(/\s+/)
    .filter(Boolean);
}
