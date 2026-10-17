/**
 * treeCommon — pure, strategy-agnostic tree primitives shared by BOTH
 * `SearchRunner` implementations (`mctsSearch.ts` and
 * `fallbackExpectimax.ts`).
 *
 * Extracted from the two orchestrators: these helpers were
 * previously copy-pasted near-verbatim in both files, including the
 * correctness-critical root-relative mate/draw frame (`terminalValue`) —
 * exactly the class of subtle sign logic a future one-sided fix would have
 * silently diverged. The guardrail's independence story is the two
 * SEARCH STRATEGIES being distinct (PUCT budget allocation vs. full-width
 * depth-limited walk), not each file owning its own copy of the shared
 * value-frame math. `practicalScore` semantics therefore cannot drift
 * between the runners: both consume this single implementation.
 *
 * Everything here is pure with respect to the search: no provider calls, no
 * budget or concurrency bookkeeping, no timers.
 */

import { Chess } from 'chess.js';
import type { MoverColor } from '@/lib/liveFlaw';
import { uciToSquares } from '@/lib/sanToSquares';
import type { EngineSnapshot, ModalPlyStat, RankedLine, Side } from './types';
import { type BackupChild, backupExpectation, backupRootMax } from './backup';
import { pRefForElo, rankFallbackValue, rankScore } from './findability';
import { ROOT_CANDIDATE_HARD_CAP } from './policyTemperature';

/**
 * Neutral expected score (0-1 midpoint): the initial value of an ungraded
 * node and the fallback for a candidate the batched grade() call omitted
 * (should not occur with a well-formed provider).
 */
export const NEUTRAL_EXPECTED_SCORE = 0.5;

/** Root-relative expected score of a drawn terminal (stalemate/insufficient material/threefold/50-move). */
const DRAW_EXPECTED_SCORE = 0.5;

/**
 * The minimal node shape the shared helpers operate over. Each runner's
 * concrete node type extends this with its own strategy-specific fields
 * (e.g. `mctsSearch`'s pending/closure bookkeeping) — the recursive type
 * parameter keeps `children` values typed as the CONCRETE node type.
 */
export interface SearchTreeNode<N extends SearchTreeNode<N>> {
  readonly fen: string;
  readonly side: Side;
  readonly depth: number;
  readonly isRoot: boolean;
  /** The UCI move that produced this node from its parent; null for the root. */
  readonly uci: string | null;
  /**
   * Renormalized Maia prior for this child at its parent. At the
   * root, this is exactly the `P_you` the findability ranking
   * reads (`buildRankedLines`'s `rankScore`).
   */
  prior: number;
  /** Root-relative expected score (0-1): leaf estimate until expanded, then the backed-up value. */
  value: number;
  visits: number;
  /** True once fixed as a checkmate/stalemate/draw leaf — never expanded. */
  isTerminal: boolean;
  /** True once this node's children are populated OR it has been permanently closed (terminal/depth-capped). */
  isExpanded: boolean;
  /** White-POV Stockfish eval (cp) at grading time, if available — surfaced on RankedLine. */
  objectiveEvalCp: number | null;
  /** White-POV Stockfish mate distance at grading time (e.g. -4), set instead of
   *  `objectiveEvalCp` for a forced-mate grade — surfaced on RankedLine so a mate
   *  leaf renders `#-4` instead of `…`. */
  objectiveEvalMate: number | null;
  /**
   * Raw Maia policy probability (0-1) of this node's move at its parent — the
   * value straight from `policy()` before temperature/truncation/renorm, so
   * the move-chip hover matches the raw Maia % shown elsewhere (not `prior`,
   * which is renormalized). Null at the root and for any move `policy()` did
   * not score (e.g. a Stockfish-injected `extraRootMoves` candidate).
   */
  rawMaiaProb: number | null;
  readonly children: Map<string, N>;
}

/** Side-to-move literal from a FEN's own second field — never depth/ply parity. */
export function fenSide(fen: string): Side {
  return fen.split(' ')[1] === 'b' ? 'b' : 'w';
}

/**
 * Compares a `Side` ('w'|'b') against a `MoverColor` ('white'|'black') — two
 * distinct literal-type domains used side-by-side in this codebase with no
 * existing converter between them. Dedicated,
 * explicitly-tested helper so the root-mover-side comparison never gets
 * hand-rolled (and possibly flipped) independently at the two
 * temperature call sites (`mctsSearch.ts`, `fallbackExpectimax.ts`).
 */
export function sideMatchesMover(side: Side, mover: MoverColor): boolean {
  return (side === 'w' ? 'white' : 'black') === mover;
}

function compareCandidateEntries(a: readonly [string, number], b: readonly [string, number]): number {
  return b[1] - a[1] || (a[0] < b[0] ? -1 : 1);
}

/**
 * Union + prior-seeding: merges `budget.extraRootMoves`
 * into the root's post-truncation candidate map, seeding each newly-added
 * UCI's prior from its share of the ALREADY-KEPT candidates' total mass
 * (never 0: a 0 prior sorts the injected candidate dead last and makes it the
 * hard cap's first casualty, silently defeating the injection mechanism).
 * Under the current formula a 0
 * prior no longer scores exactly 0 — it scores `min(value, V_fallback)`,
 * the SAME clamped floor a low-prior organic candidate below V_fallback
 * gets — but that floor is still below every findable move whose value
 * exceeds V_fallback, so seeding a real (non-zero) prior still matters:
 * without it, an injected move can never saturate rankScore's findability
 * factor and rank above the findable candidates it should beat.
 *
 * Shared by `mctsSearch.ts`'s `dispatchExpansion` and
 * `fallbackExpectimax.ts`'s `expandNode` so the two `SearchRunner`
 * implementations cannot diverge: a future one-sided fix to the merge order,
 * the prior formula, or the exemption-set construction would silently
 * reintroduce the zero-prior bug above.
 *
 * Only meaningful for the root: callers must guard on `isRoot` themselves
 * (this function performs no such check) since a non-root node has no
 * `extraRootMoves` concept.
 */
export function mergeExtraRootMoves(
  candidateMap: Map<string, number>,
  effectivePolicy: Record<string, number>,
  extraRootMoves: readonly string[] | undefined,
): { candidateMap: Map<string, number>; injectedUcis: Set<string> } {
  const injectedUcis = new Set<string>();
  if (!extraRootMoves || extraRootMoves.length === 0) {
    return { candidateMap, injectedUcis };
  }
  const merged = new Map(candidateMap);
  const keptTotal = Array.from(candidateMap.keys()).reduce(
    (sum, uci) => sum + (effectivePolicy[uci] ?? 0),
    0,
  );
  for (const uci of extraRootMoves) {
    if (!merged.has(uci)) {
      merged.set(uci, keptTotal > 0 ? (effectivePolicy[uci] ?? 0) / keptTotal : 0);
      injectedUcis.add(uci);
    }
  }
  return { candidateMap: merged, injectedUcis };
}

/**
 * Root-only hard cap on candidate count, applied AFTER temperature +
 * `truncateAndRenormalize` + the `extraRootMoves` union (never inside
 * `truncateAndRenormalize` itself,
 * which stays general-purpose and untouched). Keeps at most
 * `ROOT_CANDIDATE_HARD_CAP` entries by probability descending, canonical
 * ascending-UCI tie-break for equal probabilities. Shared by
 * both `SearchRunner` implementations so the cap can never diverge between
 * them.
 *
 * `injectedUcis` is the optional exemption set — the UCIs the
 * `extraRootMoves` union actually ADDED, never all of `budget.extraRootMoves`
 * (a UCI the union found already present competes as an organic candidate,
 * not an exemption). When present and non-empty, injected candidates are
 * exempt from competing with organic ones for the cap: organic candidates are
 * capped to `ROOT_CANDIDATE_HARD_CAP - injectedUcis.size` (never negative)
 * instead of every candidate competing for the same `ROOT_CANDIDATE_HARD_CAP`
 * slots. Without the exemption, an injected
 * candidate (seeded with prior `0` at the union site) sorted dead
 * last by this cap's own comparator and was the FIRST entry dropped
 * whenever the root exceeded the cap, silently defeating the injection
 * mechanism exactly on the wide, high-temperature roots that needed it.
 */
export function applyRootCandidateHardCap(
  candidateMap: Map<string, number>,
  injectedUcis?: ReadonlySet<string>,
): Map<string, number> {
  if (candidateMap.size <= ROOT_CANDIDATE_HARD_CAP) return candidateMap;
  if (!injectedUcis || injectedUcis.size === 0) {
    const sorted = Array.from(candidateMap.entries()).sort(compareCandidateEntries);
    return new Map(sorted.slice(0, ROOT_CANDIDATE_HARD_CAP));
  }
  const injected: [string, number][] = [];
  const organic: [string, number][] = [];
  for (const entry of candidateMap.entries()) {
    (injectedUcis.has(entry[0]) ? injected : organic).push(entry);
  }
  const organicSlots = Math.max(0, ROOT_CANDIDATE_HARD_CAP - injected.length);
  injected.sort(compareCandidateEntries);
  organic.sort(compareCandidateEntries);
  const kept = injected.slice(0, ROOT_CANDIDATE_HARD_CAP).concat(organic.slice(0, organicSlots));
  kept.sort(compareCandidateEntries);
  return new Map(kept);
}

/**
 * Converts a UCI move string into the chess.js move argument shape. Single
 * private normalization point shared by `applyUciMoveFen` and
 * `expandChildPositions` so the two can never diverge on how a UCI is parsed
 * into a `{from, to, promotion}` move object.
 */
function uciToMoveArgs(uci: string): { from: string; to: string; promotion: string | undefined } {
  const squares = uciToSquares(uci);
  return {
    from: squares?.from ?? uci.slice(0, 2),
    to: squares?.to ?? uci.slice(2, 4),
    promotion: uci.length > 4 ? uci[4] : undefined,
  };
}

/**
 * Root-relative terminal value computed from an ALREADY-POSITIONED
 * chess.js instance: checkmate is 1.0 when the checkmated side is NOT
 * `rootMover` (the root player delivered mate), 0.0 when it IS;
 * stalemate/insufficient-material/threefold/draw is DRAW_EXPECTED_SCORE.
 * Returns null when `chess`'s current position is not game-over. Single copy
 * of this sign logic — `terminalValue` and `expandChildPositions`
 * both route through it.
 */
function terminalValueFromChess(chess: Chess, rootMover: MoverColor): number | null {
  if (!chess.isGameOver()) return null;
  if (chess.isCheckmate()) {
    // The side to move in a mated position IS the checkmated side —
    // chess.turn() already knows it; no second FEN parse needed.
    const checkmatedSide: MoverColor = chess.turn() === 'w' ? 'white' : 'black';
    return checkmatedSide === rootMover ? 0 : 1;
  }
  return DRAW_EXPECTED_SCORE;
}

/**
 * Fixed root-relative terminal value for a `fen` string. Thin
 * wrapper over `terminalValueFromChess` — kept exported and by-FEN because
 * both `SearchRunner` implementations' `createRoot`/`createChildNode` call it
 * with only a FEN in hand, not a live `Chess` instance (keep ONE copy
 * of the sign logic, not one per call shape).
 */
export function terminalValue(fen: string, rootMover: MoverColor): number | null {
  return terminalValueFromChess(new Chess(fen), rootMover);
}

/**
 * Applies a UCI move to `fen` and returns the resulting FEN, or null when
 * chess.js rejects the move (illegal in this position, or malformed UCI).
 *
 * Candidate UCIs come from `policy()` output and
 * `budget.extraRootMoves` — these are real Maia/Stockfish
 * results crossing a worker boundary, exactly where a stale-FEN race or
 * protocol hiccup can produce a move that is legal in a DIFFERENT position.
 * chess.js's `.move()` THROWS on such input; without this containment one
 * bad candidate rejected the entire SearchRunner promise after budget was
 * partially consumed. Callers skip null (a deterministic drop, not a crash).
 */
export function applyUciMoveFen(fen: string, uci: string): string | null {
  const chess = new Chess(fen);
  try {
    chess.move(uciToMoveArgs(uci));
  } catch {
    return null;
  }
  return chess.fen();
}

/**
 * Batched sibling of `applyUciMoveFen` + `terminalValue`: builds ONE
 * `new Chess(parentFen)` and reuses it for every candidate UCI (move -> fen +
 * terminal -> undo), instead of `applyExpansion`'s previous per-candidate
 * `new Chess(parentFen)` construction. Values are bit-identical to calling
 * `applyUciMoveFen` + `terminalValue` per UCI:
 *
 *   - chess.js 1.4.0's `undo`/`_undoMove` (`dist/esm/chess.js` ~2675-2700)
 *     restores every FEN field (turn, castling, ep square, halfmove,
 *     fullmove) and decrements the position-repetition count
 *     (`_decPositionCount`, ~3272), so the instance is byte-identical to its
 *     pre-move state for the next iteration.
 *   - A position built via one `move()` off a loaded FEN has position count 1
 *     for that position, same as `new Chess(childFen)` would report — `_moves`
 *     (~2354) never reads `_halfMoves`/`_moveNumber` and `isThreefoldRepetition`
 *     (~2330) only ever sees count 1 either way, so threefold cannot fire from
 *     the shared instance when it would not fire from a fresh one.
 *   - The halfmove clock and legal-move generation chess.js computes from the
 *     moved instance match a fresh `new Chess(childFen)` exactly, because both
 *     start from the same parent FEN fields and apply the same move.
 *
 * A planning-time script verified this empirically: 146 moves across en
 * passant, promotion, castling, mate and fifty-move FENs, shared-instance
 * move/fen/undo matched fresh `new Chess(childFen)` on fen(), isGameOver(),
 * isCheckmate() and turn() with 0 mismatches.
 *
 * An illegal UCI (a move for the side not to move) or a malformed UCI is
 * simply absent from the returned map (a deterministic drop, mirrors
 * `applyUciMoveFen`'s null return) — callers must check `.has()`/`.get()`.
 */
export function expandChildPositions(
  parentFen: string,
  ucis: Iterable<string>,
  rootMover: MoverColor,
): Map<string, { fen: string; terminal: number | null }> {
  const chess = new Chess(parentFen);
  const positions = new Map<string, { fen: string; terminal: number | null }>();
  for (const uci of ucis) {
    try {
      chess.move(uciToMoveArgs(uci));
    } catch {
      continue; // illegal/malformed provider candidate — deterministic drop
    }
    const fen = chess.fen();
    const terminal = terminalValueFromChess(chess, rootMover);
    chess.undo();
    positions.set(uci, { fen, terminal });
  }
  return positions;
}

/** Recomputes `node.value` from its CURRENT children set: max at root, prior-weighted expectation otherwise. */
export function recomputeValue<N extends SearchTreeNode<N>>(node: N): void {
  if (node.children.size === 0) return;
  const backupChildren: BackupChild[] = Array.from(node.children.values()).map((c) => ({
    prior: c.prior,
    value: c.value,
  }));
  node.value = node.isRoot ? backupRootMax(backupChildren) : backupExpectation(backupChildren);
}

/**
 * Most-visited continuation from a root candidate's own subtree (canonical UCI
 * tie-break), returning both the UCI path and the index-aligned per-ply stats
 * (Stockfish eval + raw Maia prob, read off each node on the walk) that the
 * move-chip hover preview surfaces. Single walk so `modalPath` and
 * `modalStats` can never drift out of alignment.
 */
function buildModalPath<N extends SearchTreeNode<N>>(rootChild: N): {
  path: string[];
  stats: ModalPlyStat[];
} {
  const path: string[] = [];
  const stats: ModalPlyStat[] = [];
  let node: N | null = rootChild;
  while (node !== null) {
    if (node.uci !== null) {
      path.push(node.uci);
      stats.push({
        objectiveEvalCp: node.objectiveEvalCp,
        objectiveEvalMate: node.objectiveEvalMate,
        maiaProb: node.rawMaiaProb,
      });
    }
    if (!node.isExpanded || node.children.size === 0) break;
    let best: N | null = null;
    for (const child of node.children.values()) {
      const isBetter =
        best === null ||
        child.visits > best.visits ||
        (child.visits === best.visits && (child.uci ?? '') < (best.uci ?? ''));
      if (isBetter) best = child;
    }
    node = best;
  }
  return { path, stats };
}

/**
 * Indirection seam: `buildRankedLines` calls
 * `modalPathBuilder.build(...)` — a property lookup on this mutable, exported
 * object — instead of the bare `buildModalPath` reference, so
 * `treeCommon.test.ts` can `vi.spyOn(modalPathBuilder, 'build')` to prove
 * `buildRankedLines` never invokes the modal-path builder eagerly. Verified
 * empirically: a same-module
 * function DECLARATION reference is early-bound at compile/bundle time, so
 * `vi.spyOn` on the module's exported `buildModalPath`-if-it-were-exported
 * cannot intercept a call the module makes to itself internally — only a
 * late-bound property lookup on a mutable object is spy-able. Do NOT inline
 * this back to a bare `buildModalPath(child)` call at the accessor site
 * below; that would make the lazy-accessor non-invocation tests fail to compile
 * against a removed spy target.
 */
export const modalPathBuilder = { build: buildModalPath };

/**
 * Variance/"sharpness" proxy for a root candidate: the
 * max−min spread across `node`'s OWN children's backed-up `.value`s. When
 * `node` is a root child, these are the grandchildren of the search root —
 * exactly the `RankedLine.childScoreSpread` semantic. Returns `null` when
 * `node.children.size` is 0 or 1 (no meaningful spread to report — never
 * 0-as-a-signal for the empty case).
 */
function computeChildScoreSpread<N extends SearchTreeNode<N>>(node: N): number | null {
  if (node.children.size <= 1) return null;
  let min = Infinity;
  let max = -Infinity;
  for (const child of node.children.values()) {
    if (child.value < min) min = child.value;
    if (child.value > max) max = child.value;
  }
  return max - min;
}

/**
 * Ranked root candidates by findability-weighted rankScore descending,
 * canonical-UCI tie-break.
 * `rankScore` is a SORT-ONLY local — never assigned onto the public
 * `RankedLine` the UI consumes; `practicalScore` stays `child.value`,
 * byte-identical to before this phase. `pRef` is computed ONCE per
 * call from `rootElo` (Anti-Pattern: never recompute per child).
 *
 * `rankScore` blends toward a
 * fallback value instead of toward 0, so `fallbackValue` is ALSO computed
 * ONCE per call — `rankFallbackValue` over every root child's own
 * `{ prior, value }` — and passed to every `rankScore` call below, exactly
 * like `pRef`. This never touches which children exist or `practicalScore`.
 *
 * `modalPath`/`modalStats` are attached as lazy accessor
 * properties, not data properties — `modalPathBuilder.build(child)` (the
 * modal-path walk) only runs on first READ of either field, via a single
 * memoized `getModal` closure PER LINE shared by both accessors (so a
 * consumer reading both fields still pays for exactly one computation, never
 * two). Bot play reads neither field on the vast majority of root candidates
 * (up to `ROOT_CANDIDATE_HARD_CAP`), so this eliminates 100% of that cost for
 * the persona bot path — see `botStyle.ts`'s `applyStyleScoreShaping` for the
 * one consumer that would otherwise have silently defeated this (a spread
 * forces every accessor to evaluate). The sort comparator below reads only
 * `sortRankScore`/`line.rootMove` — never either accessor — so sorting itself
 * never forces evaluation.
 */
function buildRankedLines<N extends SearchTreeNode<N>>(root: N, rootElo: number): RankedLine[] {
  const pRef = pRefForElo(rootElo);
  // V_fallback is computed ONCE per call, from every
  // root child's own { prior, value } — the SAME filter (`uci !== null`) as
  // the scoring loop below, so the fallback average and the scored set are
  // over the identical child population.
  const fallbackChildren: { prior: number; value: number }[] = [];
  for (const child of root.children.values()) {
    if (child.uci === null) continue; // defensive; every root child has a uci
    fallbackChildren.push({ prior: child.prior, value: child.value });
  }
  const fallbackValue = rankFallbackValue(fallbackChildren);
  // Sort-only pairing of each public RankedLine with its ephemeral rankScore
  // (never assigned onto RankedLine itself) — kept as parallel local
  // state rather than a spread-and-omit so no unused-binding placeholder is
  // needed to strip the sort key afterwards.
  const scored: { line: RankedLine; sortRankScore: number }[] = [];
  for (const child of root.children.values()) {
    if (child.uci === null) continue; // defensive; every root child has a uci

    let modalCache: { path: string[]; stats: ModalPlyStat[] } | undefined;
    const getModal = (): { path: string[]; stats: ModalPlyStat[] } =>
      (modalCache ??= modalPathBuilder.build(child));

    const line = {
      rootMove: child.uci,
      practicalScore: child.value,
      objectiveEvalCp: child.objectiveEvalCp,
      objectiveEvalMate: child.objectiveEvalMate,
      visits: child.visits,
      childScoreSpread: computeChildScoreSpread(child),
    } as RankedLine;
    Object.defineProperty(line, 'modalPath', { get: () => getModal().path, enumerable: true });
    Object.defineProperty(line, 'modalStats', { get: () => getModal().stats, enumerable: true });

    scored.push({ line, sortRankScore: rankScore(child.prior, pRef, child.value, fallbackValue) });
  }
  scored.sort((a, b) => {
    if (b.sortRankScore !== a.sortRankScore) return b.sortRankScore - a.sortRankScore;
    return a.line.rootMove < b.line.rootMove ? -1 : a.line.rootMove > b.line.rootMove ? 1 : 0;
  });
  return scored.map((s) => s.line);
}

/**
 * Returns a copy of `line` with `overrides` applied, PRESERVING the laziness of
 * `modalPath`/`modalStats`.
 *
 * Never spread a `RankedLine`. `{ ...line }`, `Object.assign({}, line)`,
 * `structuredClone`, and JSON round-trips all READ every enumerable property,
 * which force-evaluates the two accessors `buildRankedLines` installs above and
 * silently undoes the lazy-accessor optimization — with no test failure, because the resulting VALUES
 * are identical. Only the cost changes.
 *
 * Single implementation of the descriptor copy: it was once hand-rolled at
 * two separate call sites, one of which was missed. A third caller cannot get
 * it subtly wrong, and a regression is caught by this module's own tests.
 */
export function cloneRankedLineWith(line: RankedLine, overrides: Partial<RankedLine>): RankedLine {
  const next = Object.create(Object.getPrototypeOf(line) as object | null) as RankedLine;
  Object.defineProperties(next, Object.getOwnPropertyDescriptors(line));
  for (const [key, value] of Object.entries(overrides)) {
    Object.defineProperty(next, key, {
      value,
      enumerable: true,
      writable: true,
      configurable: true,
    });
  }
  return next;
}

/**
 * `stopReason` defaults to `null` so the pre-existing
 * callers in `fallbackExpectimax.ts` (which has no stop-rule concept) keep
 * compiling and behaving unchanged — only `mctsSearch.ts`'s own stop-rule-
 * aware loop passes an explicit value.
 */
export function buildSnapshot<N extends SearchTreeNode<N>>(
  root: N,
  nodesEvaluated: number,
  budgetExhausted: boolean,
  rootElo: number,
  stopReason: EngineSnapshot['stopReason'] = null,
): EngineSnapshot {
  return { rankedLines: buildRankedLines(root, rootElo), nodesEvaluated, budgetExhausted, stopReason };
}
