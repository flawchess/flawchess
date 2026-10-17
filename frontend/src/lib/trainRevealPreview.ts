/**
 * trainRevealPreview — the pure model behind the Train reveal's dimmed live
 * engine preview. React-free so it unit-tests without a DOM.
 *
 * Each chip owns only its first move; everything after it is an ordinary tree
 * node. The preview is the engine continuation shown (dimmed) at the end of the
 * current branch. It is NEVER stored in the move tree: the forward button / a
 * token tap commits its moves as real nodes (`useTrainRevealTree.commitPreview`),
 * and committed nodes never change afterwards.
 *
 * Which line a leaf previews, in precedence order:
 *   1. live      the engine's top line for the CURRENT node, once it reaches
 *                TRAIN_LIVE_ALT_MIN_DEPTH and its first move is legal there
 *                (subject to the minimum-length rule below);
 *   2. stored    the last live line seen at that leaf (so stepping away and back
 *                shows the refined line at once);
 *   3. seed      the chip's graded line minus its first move (only at the chip's
 *                first-move node);
 *   4. inherited the remaining tail of the nearest ancestor's line (stored, else
 *                seed) whose moves match the committed path down to the leaf.
 * Steps are the legal prefix of that line, clipped to TRAIN_PREVIEW_MAX_PLIES.
 *
 * Minimum length: Stockfish PVs are often cut short by hash
 * cutoffs, worst on the warm hash of a stepped line, so a deep live line can be
 * only 1-2 plies long. A live line shorter than TRAIN_PREVIEW_MIN_PLIES yields to
 * the best fallback (stored, seed, inherited) when that fallback is longer and
 * starts with the same move. A live line that disagrees on the first move always
 * wins: correctness beats length, and nothing is ever padded with invented moves.
 */

import { replayPvLine } from '@/components/analysis/EngineLines';
import type { MoveNode, NodeId } from '@/hooks/useAnalysisBoard';
import type { PvLine } from '@/hooks/uciParser';
import { terminalPositionEval } from '@/lib/liveFlaw';
import { TRAIN_LIVE_ALT_MIN_DEPTH } from '@/lib/trainArrows';
import type { ChipGroup, RoleKey } from '@/lib/trainRevealLines';

/**
 * Most plies the displayed preview shows (about two wrapped token rows on a
 * phone). It caps only the DISPLAYED preview, never committed nodes: the user
 * can keep committing past it.
 */
export const TRAIN_PREVIEW_MAX_PLIES = 6;

/**
 * Preview length below which a live line yields to a longer fallback that agrees
 * on its first move (a chip shows its move plus at least five preview plies).
 */
export const TRAIN_PREVIEW_MIN_PLIES = 5;

/** Number of leading UCI characters that identify a move by its squares. */
const UCI_SQUARES_LEN = 4;

/** An engine continuation to preview, white-POV eval. */
export interface PreviewLine {
  ucis: readonly string[];
  evalCp: number | null;
  evalMate: number | null;
}

export interface RevealPreviewStep {
  uci: string;
  san: string;
}

export type PreviewSource = 'live' | 'stored' | 'seed' | 'inherited';

export interface ResolvedPreview {
  /** The leaf the preview hangs off. */
  anchorId: NodeId;
  /** The legal, clipped moves to show. */
  steps: RevealPreviewStep[];
  /** The line the steps came from (for 'inherited': the remaining tail). */
  line: PreviewLine;
  source: PreviewSource;
}

/** A chip's graded line minus its first move, or null when it has no usable
 * tail. The line must start with the chip's own move (same guard the old
 * pre-load cap used), else it belongs to a different move. */
export function chipPreviewSeed(chip: Pick<ChipGroup, 'uci' | 'line'>): PreviewLine | null {
  const { line } = chip;
  if (line === null || line.moves[0] !== chip.uci) return null;
  const tail = line.moves.slice(1);
  if (tail.length === 0) return null;
  return { ucis: tail, evalCp: line.evalCp, evalMate: line.evalMate };
}

/** Seeds keyed by each chip's first-move node id. A chip with no node yet, or no
 * seed, is skipped. */
export function buildPreviewSeeds(
  chips: readonly Pick<ChipGroup, 'key' | 'uci' | 'line'>[],
  linePaths: Partial<Record<RoleKey, NodeId[]>>,
): Map<NodeId, PreviewLine> {
  const seeds = new Map<NodeId, PreviewLine>();
  for (const chip of chips) {
    const firstId = linePaths[chip.key]?.[0];
    const seed = chipPreviewSeed(chip);
    if (firstId !== undefined && seed !== null) seeds.set(firstId, seed);
  }
  return seeds;
}

/** The engine's top line as a live candidate: deep enough and non-empty. */
export function liveCandidate(pvLines: readonly PvLine[]): PreviewLine | null {
  const top = pvLines[0];
  if (top === undefined || top.depth < TRAIN_LIVE_ALT_MIN_DEPTH || top.moves.length === 0) {
    return null;
  }
  return { ucis: top.moves, evalCp: top.evalCp, evalMate: top.evalMate };
}

function hasChildren(nodes: Map<NodeId, MoveNode>, id: NodeId): boolean {
  for (const node of nodes.values()) {
    if (node.parentId === id) return true;
  }
  return false;
}

export interface PreviewAnchorInput {
  nodes: Map<NodeId, MoveNode>;
  currentNodeId: NodeId | null;
  /** The active chip's first-move node id, or null (no chip / not seeded yet). */
  activeChipFirstId: NodeId | null;
}

/**
 * The node the preview hangs off, or null for no preview. A leaf is its own
 * anchor; at the puzzle position the anchor is the active chip's first-move node
 * while that node is a leaf (so the list looks as full as before at open). A node
 * with children has no preview, and neither does a finished
 * game (checkmate / stalemate / draw).
 */
export function resolvePreviewAnchor({
  nodes,
  currentNodeId,
  activeChipFirstId,
}: PreviewAnchorInput): NodeId | null {
  const anchorId = currentNodeId ?? activeChipFirstId;
  if (anchorId === null) return null;
  const anchor = nodes.get(anchorId);
  if (anchor === undefined || hasChildren(nodes, anchorId)) return null;
  return terminalPositionEval(anchor.fen) === null ? anchorId : null;
}

function squaresOf(uci: string): string {
  return uci.slice(0, UCI_SQUARES_LEN);
}

/** The legal prefix of `ucis` replayed from `fen`, clipped for display. */
function buildSteps(fen: string, ucis: readonly string[]): RevealPreviewStep[] {
  const clipped = ucis.slice(0, TRAIN_PREVIEW_MAX_PLIES);
  const steps: RevealPreviewStep[] = [];
  const replay = replayPvLine(fen, [...clipped]);
  for (const [i, uci] of clipped.entries()) {
    const san = replay[i]?.san;
    if (san === null || san === undefined) break;
    steps.push({ uci, san });
  }
  return steps;
}

/** Whether `ucis` begins with the moves of `path` (compared by squares). */
function startsWithPath(ucis: readonly string[], path: readonly string[]): boolean {
  if (ucis.length <= path.length) return false;
  return path.every((squares, i) => squaresOf(ucis[i] ?? '') === squares);
}

interface PreviewCandidate {
  line: PreviewLine;
  source: PreviewSource;
}

/**
 * The nearest ancestor's line (stored, else seed) that matches the committed
 * path down to `anchorId`, as its remaining tail. A nearer ancestor whose line
 * diverges is skipped, not fatal. Null when no ancestor matches.
 */
function inheritedCandidate(
  nodes: Map<NodeId, MoveNode>,
  anchorId: NodeId,
  stored: ReadonlyMap<NodeId, PreviewLine>,
  seeds: ReadonlyMap<NodeId, PreviewLine>,
): PreviewCandidate | null {
  // Squares of the moves from the current ancestor down to the anchor.
  const downPath: string[] = [];
  let cursor: NodeId | null = anchorId;
  // Bounded by the tree size so a malformed parent cycle cannot loop.
  for (let hops = 0; cursor !== null && hops <= nodes.size; hops++) {
    const node: MoveNode | undefined = nodes.get(cursor);
    if (node === undefined) return null;
    downPath.unshift(node.from + node.to);
    cursor = node.parentId;
    if (cursor === null) return null;
    const entry = stored.get(cursor) ?? seeds.get(cursor);
    if (entry !== undefined && startsWithPath(entry.ucis, downPath)) {
      const tail = entry.ucis.slice(downPath.length);
      return { line: { ...entry, ucis: tail }, source: 'inherited' };
    }
  }
  return null;
}

export interface ResolvePreviewInput {
  nodes: Map<NodeId, MoveNode>;
  anchorId: NodeId;
  /** The live candidate; the caller passes it only when the anchor is the current node. */
  live: PreviewLine | null;
  stored: ReadonlyMap<NodeId, PreviewLine>;
  seeds: ReadonlyMap<NodeId, PreviewLine>;
}

/** The first candidate (in order) with at least one legal step, else the
 * inherited tail, as a resolved preview; null when none has a legal move. */
function firstResolvable(
  nodes: Map<NodeId, MoveNode>,
  anchor: MoveNode,
  anchorId: NodeId,
  candidates: readonly PreviewCandidate[],
  stored: ReadonlyMap<NodeId, PreviewLine>,
  seeds: ReadonlyMap<NodeId, PreviewLine>,
): ResolvedPreview | null {
  for (const candidate of candidates) {
    const steps = buildSteps(anchor.fen, candidate.line.ucis);
    if (steps.length > 0) return { anchorId, steps, ...candidate };
  }
  const inherited = inheritedCandidate(nodes, anchorId, stored, seeds);
  if (inherited === null) return null;
  const steps = buildSteps(anchor.fen, inherited.line.ucis);
  return steps.length > 0 ? { anchorId, steps, ...inherited } : null;
}

/** Whether a short live preview yields to `fallback` (the minimum-length rule). */
function fallbackOutranksLive(live: ResolvedPreview, fallback: ResolvedPreview | null): boolean {
  if (fallback === null || live.steps.length >= TRAIN_PREVIEW_MIN_PLIES) return false;
  const sameFirstMove =
    squaresOf(fallback.steps[0]?.uci ?? '') === squaresOf(live.steps[0]?.uci ?? '');
  return sameFirstMove && fallback.steps.length > live.steps.length;
}

/** The preview to show at `anchorId`, or null when no candidate has a legal move. */
export function resolvePreview({
  nodes,
  anchorId,
  live,
  stored,
  seeds,
}: ResolvePreviewInput): ResolvedPreview | null {
  const anchor = nodes.get(anchorId);
  if (anchor === undefined) return null;

  const fallbacks: PreviewCandidate[] = [];
  const storedLine = stored.get(anchorId);
  if (storedLine !== undefined) fallbacks.push({ line: storedLine, source: 'stored' });
  const seedLine = seeds.get(anchorId);
  if (seedLine !== undefined) fallbacks.push({ line: seedLine, source: 'seed' });
  const fallback = firstResolvable(nodes, anchor, anchorId, fallbacks, stored, seeds);

  if (live === null) return fallback;
  const liveSteps = buildSteps(anchor.fen, live.ucis);
  if (liveSteps.length === 0) return fallback;
  const livePreview: ResolvedPreview = { anchorId, steps: liveSteps, line: live, source: 'live' };
  return fallbackOutranksLive(livePreview, fallback) ? fallback : livePreview;
}
