/**
 * Curate troll-opening positions from Lichess study cEDAMVBB.
 *
 * Reads the multi-chapter PGN, walks each chapter via chess.js, derives the
 * user-side-only FEN key for every mainline ply (both colors), and prints a
 * candidate list to stdout for human review per Phase 77 D-01.
 *
 * Run:
 *   npx tsx frontend/scripts/curate-troll-openings.ts > /tmp/troll-candidates.txt
 *
 * After review, hand-paste the pruned keys into frontend/src/data/trollOpenings.ts.
 * The script does NOT auto-write the data file (per D-09 — human review is mandatory).
 *
 * The output is intentionally noisy: every ply of every chapter for both colors is
 * emitted so the human reviewer can pick the canonical "defining position" without
 * the script guessing wrong (Pitfall 2 from RESEARCH.md).
 */

import { Chess } from 'chess.js';
import { readFileSync, existsSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const STUDY_URL = 'https://lichess.org/study/cEDAMVBB.pgn';
const SCRIPT_DIR = dirname(fileURLToPath(import.meta.url));
const CACHE_PATH = resolve(SCRIPT_DIR, '.cache', 'cEDAMVBB.pgn');

/**
 * Derive a deterministic user-side-only key from a board FEN.
 *
 * Accepts either a full FEN ("rnbq.../w KQkq -") or a piece-placement-only FEN
 * ("rnbq..."). Strips opponent pieces, re-canonicalizes empty-square runs, and
 * returns the rejoined 8-rank string. Stable across opponent variations.
 *
 * NOTE: This duplicates the canonical implementation in frontend/src/lib/trollOpenings.ts
 * (Plan 01). Duplication is intentional — this script runs under `npx tsx` and the
 * `@/...` path alias may not resolve. The Plan 01 unit tests cover the canonical
 * implementation; keep the two in sync if either changes.
 */
function deriveUserSideKey(fen: string, side: 'white' | 'black'): string {
  // safe: split() always returns at least one element for any string input.
  const placement = fen.split(' ', 1)[0]!;
  const ranks = placement.split('/');
  if (ranks.length !== 8) {
    throw new Error(`Invalid FEN piece-placement: expected 8 ranks, got ${ranks.length}`);
  }
  const opponentRegex = side === 'white' ? /[a-z]/ : /[A-Z]/;
  return ranks.map(rank => canonicalizeRank(rank, opponentRegex)).join('/');
}

function canonicalizeRank(rank: string, stripPattern: RegExp): string {
  let out = '';
  let emptyRun = 0;
  for (const ch of rank) {
    if (/\d/.test(ch)) {
      emptyRun += parseInt(ch, 10);
    } else if (stripPattern.test(ch)) {
      emptyRun += 1;
    } else {
      if (emptyRun > 0) {
        out += String(emptyRun);
        emptyRun = 0;
      }
      out += ch;
    }
  }
  if (emptyRun > 0) out += String(emptyRun);
  return out;
}

interface Candidate {
  chapterIndex: number;
  chapterTitle: string;
  trollSide: 'white' | 'black';
  plyNumber: number;
  sanSequence: string;
  key: string;
}

async function loadPgn(): Promise<string> {
  if (existsSync(CACHE_PATH)) {
    return readFileSync(CACHE_PATH, 'utf-8');
  }
  // Cache miss — fetch from Lichess. Cache for re-runnability per D-09.
  console.error(`Cache miss; fetching ${STUDY_URL} ...`);
  const res = await fetch(STUDY_URL);
  if (!res.ok) {
    throw new Error(`Lichess fetch failed: ${res.status} ${res.statusText}`);
  }
  const text = await res.text();
  mkdirSync(dirname(CACHE_PATH), { recursive: true });
  writeFileSync(CACHE_PATH, text);
  console.error(`Cached PGN to ${CACHE_PATH} (${text.length} bytes)`);
  return text;
}

function extractCandidates(chapters: string[]): Candidate[] {
  const candidates: Candidate[] = [];
  for (let chapterIdx = 0; chapterIdx < chapters.length; chapterIdx++) {
    // safe: chapterIdx is a valid index into chapters by loop bounds.
    const chapterText = chapters[chapterIdx]!;
    const chess = new Chess();
    try {
      // chess.js@1.x throws on unparseable PGN (Pitfall 6).
      chess.loadPgn(chapterText);
    } catch (err) {
      console.error(
        `[chapter ${chapterIdx}] Skipping unparseable chapter: ${(err as Error).message}`,
      );
      continue;
    }

    const headers = chess.header();
    const title = headers.Event ?? headers.White ?? `<chapter ${chapterIdx}>`;
    const verboseHistory = chess.history({ verbose: true });

    if (verboseHistory.length === 0) {
      // Skip chapters with no mainline moves (header-only chapters).
      continue;
    }

    // Replay onto a fresh board, emitting BOTH side keys after every ply.
    // This gives the human reviewer full visibility per Pitfall 2.
    const replay = new Chess();
    const sanSeq: string[] = [];
    for (let plyIdx = 0; plyIdx < verboseHistory.length; plyIdx++) {
      // safe: plyIdx is a valid index into verboseHistory by loop bounds.
      const move = verboseHistory[plyIdx]!;
      replay.move(move.san);
      sanSeq.push(move.san);
      const fen = replay.fen();
      const plyNumber = plyIdx + 1;
      const sanSequenceStr = formatSanSequence(sanSeq);
      for (const side of ['white', 'black'] as const) {
        candidates.push({
          chapterIndex: chapterIdx,
          chapterTitle: title,
          trollSide: side,
          plyNumber,
          sanSequence: sanSequenceStr,
          key: deriveUserSideKey(fen, side),
        });
      }
    }
  }
  return candidates;
}

function formatSanSequence(sans: string[]): string {
  // Render as "1.e4 e5 2.Ke2" style for the human reviewer.
  const parts: string[] = [];
  for (let i = 0; i < sans.length; i++) {
    // safe: i is a valid index into sans by loop bounds.
    const san = sans[i]!;
    if (i % 2 === 0) {
      const moveNo = Math.floor(i / 2) + 1;
      parts.push(`${moveNo}.${san}`);
    } else {
      parts.push(san);
    }
  }
  return parts.join(' ');
}

async function main(): Promise<void> {
  const pgnText = await loadPgn();
  // Split on the chapter boundary marker — empty line followed by [Event header.
  const chapters = pgnText.split(/\n\n(?=\[Event )/g).filter(c => c.trim().length > 0);
  console.error(`Parsed ${chapters.length} chapter(s) from PGN.`);

  const candidates = extractCandidates(chapters);

  console.log('=== TROLL OPENING CANDIDATES (review and prune per D-01) ===');
  console.log('');
  let lastChapterIdx = -1;
  for (const c of candidates) {
    if (c.chapterIndex !== lastChapterIdx) {
      console.log(`--- Chapter ${c.chapterIndex}: ${c.chapterTitle} ---`);
      lastChapterIdx = c.chapterIndex;
    }
    console.log(`[${c.trollSide}] after ply ${c.plyNumber}: ${c.sanSequence}`);
    console.log(`  key: ${c.key}`);
  }
  console.log('');
  console.log(
    `Total candidates: ${candidates.length}. Hand-prune to strict Bongcloud-tier set per D-01 before committing.`,
  );
}

main().catch((err: unknown) => {
  console.error(err);
  process.exit(1);
});
