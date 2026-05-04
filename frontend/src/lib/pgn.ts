/** Parse PGN string like "1. e4 e5 2. Nf3" into SAN array ["e4", "e5", "Nf3"] */
export function pgnToSanArray(pgn: string): string[] {
  return pgn
    .replace(/\d+\./g, '')
    .split(/\s+/)
    .filter(Boolean);
}

/** Format SAN array ["e4", "e5", "Nf3"] as PGN string "1. e4 e5 2. Nf3". */
export function sanArrayToPgn(moves: string[]): string {
  const parts: string[] = [];
  for (let i = 0; i < moves.length; i++) {
    if (i % 2 === 0) parts.push(`${i / 2 + 1}.`);
    parts.push(moves[i] as string);
  }
  return parts.join(' ');
}
