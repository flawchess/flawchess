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

// ─── Analysis move-tree export ───────────────────────────────────────────────

/** Standard starting position: a root equal to this needs no `[SetUp]`/`[FEN]` pair. */
const STANDARD_START_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
/** PGN Seven Tag Roster placeholder for an unknown value. */
const UNKNOWN_TAG = '?';
/** PGN movetext / Result-tag token for an unfinished or unknown result. */
const UNKNOWN_RESULT = '*';
const FEN_SIDE_FIELD = 1;
const FEN_FULLMOVE_FIELD = 5;
const ISO_DATE_RE = /^(\d{4})-(\d{2})-(\d{2})/;

/** The node fields the serializer reads (structural subset of useAnalysisBoard's MoveNode). */
export interface PgnTreeNode {
  id: number;
  san: string;
  fen: string;
  parentId: number | null;
}

/** Header values for the exported PGN; null = unknown (written as the `?` placeholder). */
export interface PgnHeaderValues {
  white: string | null;
  black: string | null;
  whiteElo: number | null;
  blackElo: number | null;
  /** `1-0` / `0-1` / `1/2-1/2`; null = `*`. */
  result: string | null;
  /** PGN `YYYY.MM.DD` or an ISO timestamp (converted). */
  date: string | null;
}

export interface AnalysisPgnInput {
  nodes: ReadonlyMap<number, PgnTreeNode>;
  mainLine: readonly number[];
  rootFen: string;
  headers: PgnHeaderValues | null;
}

function escapeTagValue(value: string): string {
  return value.replace(/\\/g, '\\\\').replace(/"/g, '\\"');
}

function pgnDate(date: string | null): string {
  if (date === null) return '????.??.??';
  const iso = ISO_DATE_RE.exec(date);
  return iso ? `${iso[1]}.${iso[2]}.${iso[3]}` : date;
}

function buildHeaderBlock(headers: PgnHeaderValues | null, rootFen: string, result: string): string[] {
  const tags: [string, string][] = [
    ['Event', UNKNOWN_TAG],
    ['Site', UNKNOWN_TAG],
    ['Date', pgnDate(headers?.date ?? null)],
    ['Round', UNKNOWN_TAG],
    ['White', headers?.white ?? UNKNOWN_TAG],
    ['Black', headers?.black ?? UNKNOWN_TAG],
    ['Result', result],
  ];
  if (headers?.whiteElo != null) tags.push(['WhiteElo', String(headers.whiteElo)]);
  if (headers?.blackElo != null) tags.push(['BlackElo', String(headers.blackElo)]);
  if (rootFen !== STANDARD_START_FEN) {
    tags.push(['SetUp', '1'], ['FEN', rootFen]);
  }
  return tags.map(([name, value]) => `[${name} "${escapeTagValue(value)}"]`);
}

/** The SAN token for a move played FROM `fenBefore`, with its move number when needed. */
function moveToken(fenBefore: string, san: string, forceNumber: boolean): string {
  const fields = fenBefore.split(' ');
  const fullmove = fields[FEN_FULLMOVE_FIELD] ?? '1';
  if (fields[FEN_SIDE_FIELD] !== 'b') return `${fullmove}. ${san}`;
  return forceNumber ? `${fullmove}... ${san}` : san;
}

/**
 * Serialize the analysis board's branching move tree as PGN: every node in the
 * tree is exported, sidelines as RAV variations `( ... )`. The primary
 * continuation of a node is its mainLine successor when it has one, else its
 * lowest-id child (the same rule VariationTree uses to pick a sub-fork's line).
 * Free play keeps every move OFF mainLine, so this rule is what gives a
 * free-play tree a main line at all.
 */
export function buildAnalysisPgn({ nodes, mainLine, rootFen, headers }: AnalysisPgnInput): string {
  const children = new Map<number | null, PgnTreeNode[]>();
  for (const node of nodes.values()) {
    const siblings = children.get(node.parentId) ?? [];
    siblings.push(node);
    children.set(node.parentId, siblings);
  }
  for (const siblings of children.values()) siblings.sort((a, b) => a.id - b.id);

  const mainNext = new Map<number | null, number>();
  mainLine.forEach((id, idx) => mainNext.set(idx === 0 ? null : (mainLine[idx - 1] as number), id));

  const tokens: string[] = [];
  // Iterative over the primary line, recursive only into variations.
  const writeLine = (parentId: number | null, parentFen: string, forceFirstNumber: boolean): void => {
    let pId = parentId;
    let pFen = parentFen;
    let forceNumber = forceFirstNumber;
    for (;;) {
      const kids = children.get(pId);
      if (kids === undefined || kids.length === 0) return;
      const mainId = mainNext.get(pId);
      const primary = kids.find((k) => k.id === mainId) ?? (kids[0] as PgnTreeNode);
      tokens.push(moveToken(pFen, primary.san, forceNumber));
      const alternatives = kids.filter((k) => k !== primary);
      for (const alt of alternatives) {
        tokens.push('(' + moveToken(pFen, alt.san, true));
        writeLine(alt.id, alt.fen, false);
        tokens.push(')');
      }
      forceNumber = alternatives.length > 0;
      pId = primary.id;
      pFen = primary.fen;
    }
  };
  writeLine(null, rootFen, true);

  const result = headers?.result ?? UNKNOWN_RESULT;
  // Join tokens, gluing a closing paren onto the move before it: "(2... Nc6 3. Bb5)".
  const movetext = [...tokens, result].join(' ').replace(/ \)/g, ')');
  return [...buildHeaderBlock(headers, rootFen, result), '', movetext, ''].join('\n');
}

/** Game-mode header values from the fetched library game. The API carries no Result tag, so it is derived from user_result + user_color. */
export function gamePgnHeaders(game: {
  white_username: string | null;
  black_username: string | null;
  white_rating: number | null;
  black_rating: number | null;
  played_at: string | null;
  user_result: 'win' | 'draw' | 'loss';
  user_color: string;
}): PgnHeaderValues {
  const whiteWon = (game.user_result === 'win') === (game.user_color === 'white');
  return {
    white: game.white_username,
    black: game.black_username,
    whiteElo: game.white_rating,
    blackElo: game.black_rating,
    date: game.played_at,
    result: game.user_result === 'draw' ? '1/2-1/2' : whiteWon ? '1-0' : '0-1',
  };
}
