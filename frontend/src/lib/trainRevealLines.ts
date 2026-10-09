/**
 * trainRevealLines — the pure chip/line model behind the Train reveal's single
 * move tree (Phase 237, SEED-194). React-free so it unit-tests without a DOM.
 *
 * The reveal shows up to three "role" lines: Your move, Best move and the move
 * Played in game. Roles whose first move coincides merge into ONE chip (D-02:
 * "Move = Best"); each chip's line is pre-loaded as a root branch of one
 * `useAnalysisBoard` tree, capped at MAX_LINE_PLIES (D-03). Which tree nodes
 * belong to which chip is never stored on a node: it is derived by walking each
 * chip's UCI list through the tree (`walkLinePath`), so late-arriving lines,
 * child reuse and a hand-played move that happens to match a line all fall out
 * of the same code (RESEARCH Pattern 1).
 */

import { Chess } from 'chess.js';
import { findChildBySquares } from '@/hooks/useAnalysisBoard';
import type { MoveNode, NodeId } from '@/hooks/useAnalysisBoard';
import type { GradeResult, TrainEngineLine } from '@/hooks/useTrainGradingEngine';
import type { InstantGradeState } from '@/hooks/trainGradingSupport';
import type { TrainMoveQuality } from '@/lib/trainArrows';

/** 190.1-03 D-03: role keys for the three reveal lines, in their canonical
 * display AND key-precedence order (your > best > game). */
export type RoleKey = 'your' | 'best' | 'game';

export const CANONICAL_ROLE_ORDER: readonly RoleKey[] = ['your', 'best', 'game'];

/** Short chip labels; a merged chip joins them with " = " ("Move = Best"). */
export const ROLE_SHORT_LABELS: Record<RoleKey, string> = {
  your: 'Move',
  best: 'Best',
  game: 'Game',
};

/** The chip whose arrow is lit when the reveal opens, and what rewinding to the
 * puzzle position restores when no chip is focused (RESEARCH A1). */
export const DEFAULT_ROOT_FOCUS: RoleKey = 'your';

/**
 * Phase 200 UAT: a pre-loaded line steps at most this many plies (six full
 * moves — about two wrapped token rows; UAT round 3 raised it from ten). The
 * deep tail of a long PV is noise on the reveal. Moves past the end are
 * ordinary user forks (D-03).
 */
export const MAX_LINE_PLIES = 12;

/**
 * Local discriminated state for the reveal-time "played in game" search
 * (190.1-01/03). Only ever populated for a STANDALONE 'game' chip — the
 * dispatching effect skips the search entirely when the game move coincides
 * with `playedMoveUci` or `gradeResult.bestLine.moves[0]`.
 */
export type GameMoveLineState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'ready'; line: TrainEngineLine }
  | { status: 'error' };

/**
 * One chip: the roles that share a first move, resolved to display data.
 * `key` is the primary role (`roles[0]`), so it stays stable as roles merge in
 * late (a game move arriving later only appends a role).
 */
export interface ChipGroup {
  key: RoleKey;
  roles: RoleKey[];
  /** The chip's (shared) first-move UCI. Always defined: a chip only exists
   * when at least one role resolved a UCI. */
  uci: string;
  san: string | null;
  /** Roles joined with " = ", e.g. "Move = Best". */
  label: string;
  /** The line to display, or null while it is not known yet (see `pending`). */
  line: TrainEngineLine | null;
  /** The UCI moves to pre-load as a root branch: capped at MAX_LINE_PLIES and
   * always starting with `uci` (just `[uci]` while the line is unknown). */
  lineUcis: string[];
  /** 'loading' while the line is still being searched, 'failed' once the search
   * gave up. Null for a ready chip (Phase 236 D-14/D-15). */
  pending: 'loading' | 'failed' | null;
  /** Quality of the chip's first move: 'best' whenever the best move is in the
   * chip, else the played move's own quality, else the game move's. */
  quality: TrainMoveQuality | null;
}

export interface BuildChipGroupsInput {
  puzzleFen: string;
  playedMoveUci: string | null;
  gradeResult: GradeResult | null;
  instantGrade: InstantGradeState | null;
  gameMoveUci: string | null;
  gameMoveLine: GameMoveLineState;
  playedMoveQuality: TrainMoveQuality | null;
  gameMoveQuality: TrainMoveQuality | null;
}

/** UCI ("e2e4"/"e7e8q") -> SAN via chess.js from `fen`, or null on a null/
 * malformed/illegal input — a chip falls back to its bare mark rather than
 * rendering a broken token (190.1-03 Task 1). */
export function sanFromUci(fen: string, uci: string | null): string | null {
  if (uci === null || uci.length < 4) return null;
  try {
    const chess = new Chess(fen);
    const move = chess.move({
      from: uci.slice(0, 2),
      to: uci.slice(2, 4),
      promotion: uci.length > 4 ? uci.slice(4, 5) : undefined,
    });
    return move ? move.san : null;
  } catch {
    return null;
  }
}

/**
 * Phase 236: the best-move UCI the reveal shows. The graded result's key line
 * once the phone grade has landed, else the key the instant path carries while
 * it is pending; null when neither exists. Primitive, so effect deps built on
 * it do not re-fire when the grade object replaces the pending state.
 */
export function revealBestUciOf(
  gradeResult: GradeResult | null,
  instantGrade: InstantGradeState | null,
): string | null {
  // WR-01: read `bestMoveUci`, not `bestLine.moves[0]`. The Analyze stand-in grade
  // (gradeFromServerPair) can carry an EMPTY bestLine when the anchor had not
  // settled, so moves[0] was undefined and the Best chip vanished while the board
  // arrow (which already used bestMoveUci) still drew it. One predicate now.
  return gradeResult?.bestMoveUci ?? instantGrade?.keyUci ?? null;
}

/** The pre-load list for a chip: the line capped at MAX_LINE_PLIES when it
 * starts with the chip's own first move, else just that first move. */
function capLineUcis(uci: string, line: TrainEngineLine | null): string[] {
  if (line === null || line.moves[0] !== uci) return [uci];
  return line.moves.slice(0, MAX_LINE_PLIES);
}

/**
 * The line a chip displays. Merge-precedence rule (distinct from key
 * precedence, which is always your > best > game): 'best' present -> best line
 * (played==best fast path, or best alone, or best==game); else 'your' present
 * -> played line (your alone, or your==game); else a standalone 'game' chip
 * takes the game-move search's line once it is ready.
 */
function resolveChipLine(
  roles: readonly RoleKey[],
  input: BuildChipGroupsInput,
): TrainEngineLine | null {
  const { gradeResult, instantGrade, gameMoveLine } = input;
  if (roles.includes('best')) return gradeResult?.bestLine ?? instantGrade?.keyLine ?? null;
  if (roles.includes('your')) return gradeResult?.playedLine ?? null;
  return gameMoveLine.status === 'ready' ? gameMoveLine.line : null;
}

/**
 * Phase 236: a your/best chip with no line yet is waiting on the background
 * search (or gave up), never the game-move search. A STANDALONE game chip is
 * 'loading' until its own search is ready and 'failed' when that search errored.
 */
function resolveChipPending(
  roles: readonly RoleKey[],
  line: TrainEngineLine | null,
  input: BuildChipGroupsInput,
): ChipGroup['pending'] {
  const { instantGrade, gameMoveLine } = input;
  if (roles.includes('your') || roles.includes('best')) {
    if (line !== null || instantGrade === null) return null;
    return instantGrade.status === 'failed' ? 'failed' : 'loading';
  }
  if (gameMoveLine.status === 'ready') return null;
  return gameMoveLine.status === 'error' ? 'failed' : 'loading';
}

/**
 * Groups the up-to-three role lines by coincident first-move UCI (190.1-03
 * D-03 / Phase 237 D-02). Chips come out in canonical your > best > game order.
 */
export function buildChipGroups(input: BuildChipGroupsInput): ChipGroup[] {
  const {
    puzzleFen,
    playedMoveUci,
    gradeResult,
    instantGrade,
    gameMoveUci,
    playedMoveQuality,
    gameMoveQuality,
  } = input;
  const uciByRole: Partial<Record<RoleKey, string>> = {};
  // Phase 236: on the instant path the verdict lands before the phone grade, so
  // the your/best roles exist from the server verdict and the key alone.
  if ((gradeResult !== null || instantGrade !== null) && playedMoveUci !== null) {
    uciByRole.your = playedMoveUci;
  }
  const bestUci = revealBestUciOf(gradeResult, instantGrade);
  if (bestUci !== null) uciByRole.best = bestUci;
  if (gameMoveUci !== null) uciByRole.game = gameMoveUci;

  // 190.1 UAT round 5: the display order is ALWAYS canonical — Your move first —
  // so the user's own move is the first thing read regardless of the verdict.
  const chips: ChipGroup[] = [];
  const consumed = new Set<RoleKey>();

  for (const role of CANONICAL_ROLE_ORDER) {
    if (consumed.has(role)) continue;
    const uci = uciByRole[role];
    if (uci === undefined) continue;
    const roles = CANONICAL_ROLE_ORDER.filter((r) => uciByRole[r] === uci);
    roles.forEach((r) => consumed.add(r));
    const line = resolveChipLine(roles, input);
    const quality: TrainMoveQuality | null = roles.includes('best')
      ? 'best'
      : roles.includes('your')
        ? playedMoveQuality
        : gameMoveQuality;
    chips.push({
      // key precedence your > best > game — roles is already filtered from
      // CANONICAL_ROLE_ORDER, so roles[0] is the highest-precedence role here.
      key: roles[0] ?? role,
      roles,
      uci,
      san: sanFromUci(puzzleFen, uci),
      label: roles.map((r) => ROLE_SHORT_LABELS[r]).join(' = '),
      line,
      lineUcis: capLineUcis(uci, line),
      pending: resolveChipPending(roles, line, input),
      quality,
    });
  }
  return chips;
}

// ─── Tree walking ────────────────────────────────────────────────────────────

/**
 * Node ids along `uciMoves`, starting under `fromId` (null = the root
 * position), stopping at the first missing child. Shorter than `uciMoves` when
 * the tree does not (yet) hold the whole line.
 */
export function walkLinePath(
  nodes: Map<NodeId, MoveNode>,
  uciMoves: readonly string[],
  fromId: NodeId | null = null,
): NodeId[] {
  const path: NodeId[] = [];
  let parent: NodeId | null = fromId;
  for (const uci of uciMoves) {
    const child = findChildBySquares(nodes, parent, uci.slice(0, 2), uci.slice(2, 4));
    if (!child) break;
    path.push(child.id);
    parent = child.id;
  }
  return path;
}

/** Matches the promotion suffix of a SAN ("e8=Q+" -> "Q"). */
const SAN_PROMOTION_SUFFIX = /=([QRBN])/;

/** The UCI of the move that led to `node`: from + to, plus the promotion letter
 * (lowercase, parsed from the SAN) so a round trip through chess.js keeps it. */
export function nodeUci(node: Pick<MoveNode, 'from' | 'to' | 'san'>): string {
  const promotion = SAN_PROMOTION_SUFFIX.exec(node.san)?.[1];
  return node.from + node.to + (promotion !== undefined ? promotion.toLowerCase() : '');
}

/** Node ids from the first move down to `id` (root excluded). Stops at a missing
 * parent rather than looping, so a broken chain yields its reachable suffix. */
export function pathToNode(nodes: Map<NodeId, MoveNode>, id: NodeId | null): NodeId[] {
  const path: NodeId[] = [];
  let cursor = id;
  while (cursor !== null && path.length <= nodes.size) {
    const node = nodes.get(cursor);
    if (!node) break;
    path.push(node.id);
    cursor = node.parentId;
  }
  return path.reverse();
}

/**
 * Walks up from a free node to its nearest owned ancestor. Returns that owner
 * (null when the chain reaches the root first: a root-fork subtree) and every
 * node visited on the way, which all share it.
 */
function resolveFreeNodeOwner(
  nodes: Map<NodeId, MoveNode>,
  owners: Map<NodeId, RoleKey | null>,
  start: MoveNode,
): { owner: RoleKey | null; chain: NodeId[] } {
  const chain: NodeId[] = [];
  let cursor: MoveNode | undefined = start;
  while (cursor !== undefined && !owners.has(cursor.id)) {
    chain.push(cursor.id);
    cursor = cursor.parentId === null ? undefined : nodes.get(cursor.parentId);
  }
  return { owner: cursor !== undefined ? (owners.get(cursor.id) ?? null) : null, chain };
}

/**
 * Each node's owning chip: a node on a chip's line belongs to that chip, a free
 * node to the owner of its nearest known ancestor, and a node in a root-fork
 * subtree (no known ancestor) to null. Chips never share nodes (distinct first
 * moves), so the canonical order only breaks a tie for a transiently divergent
 * line.
 */
export function classifyTreeNodes(
  nodes: Map<NodeId, MoveNode>,
  linePaths: Partial<Record<RoleKey, NodeId[]>>,
): Map<NodeId, RoleKey | null> {
  const owners = new Map<NodeId, RoleKey | null>();
  for (const key of CANONICAL_ROLE_ORDER) {
    for (const id of linePaths[key] ?? []) {
      if (!owners.has(id)) owners.set(id, key);
    }
  }
  for (const node of nodes.values()) {
    if (owners.has(node.id)) continue;
    const { owner, chain } = resolveFreeNodeOwner(nodes, owners, node);
    for (const id of chain) owners.set(id, owner);
  }
  return owners;
}

// ─── List view and forward navigation ────────────────────────────────────────

/** The slice of the tree the move list renders. Fed to `VariationTree` as its
 * `nodes` / `mainLine`, so the active line is numbered and everything else
 * hanging off it renders as an ordinary sideline. */
export interface TreeListView {
  nodes: Map<NodeId, MoveNode>;
  mainLine: NodeId[];
}

/**
 * The list the user sees for the active chip (sketch `selectedListHtml`): the
 * chip's line as the main line, the free sidelines hanging off it, and the free
 * root forks (rendered before move 1). The other chips' lines, and the free
 * subtrees under them, are excluded. With no active chip (D-04) the list is
 * only the user's own root-fork subtrees.
 */
export function buildTreeListView(
  nodes: Map<NodeId, MoveNode>,
  linePaths: Partial<Record<RoleKey, NodeId[]>>,
  owners: Map<NodeId, RoleKey | null>,
  activeChip: RoleKey | null,
): TreeListView {
  const view = new Map<NodeId, MoveNode>();
  for (const node of nodes.values()) {
    const owner = owners.get(node.id) ?? null;
    if (owner === null || owner === activeChip) view.set(node.id, node);
  }
  const mainLine = activeChip !== null ? [...(linePaths[activeChip] ?? [])] : [];
  return { nodes: view, mainLine };
}

export interface ForwardTargetInput {
  nodes: Map<NodeId, MoveNode>;
  currentNodeId: NodeId | null;
  activeChip: RoleKey | null;
  linePaths: Partial<Record<RoleKey, NodeId[]>>;
  /** The child most recently visited under each parent (null = the root). */
  lastChildByParent: ReadonlyMap<NodeId | null, NodeId>;
}

/**
 * Where › (and ArrowRight) goes. NOT useAnalysisBoard.goForward, whose
 * lowest-id / pv-first rule would step into the wrong chip at the root
 * (RESEARCH Pitfall 3):
 * - at the puzzle position: the ACTIVE chip's first move (with no active chip,
 *   D-04: the last-visited root fork, else the first one);
 * - below the root: the last-visited child, then the next node of the known
 *   line the current node is on, then the lowest-id child (a free sideline).
 * Null when the node has no children.
 */
export function resolveForwardTarget({
  nodes,
  currentNodeId,
  activeChip,
  linePaths,
  lastChildByParent,
}: ForwardTargetInput): NodeId | null {
  const children: MoveNode[] = [];
  for (const node of nodes.values()) {
    if (node.parentId === currentNodeId) children.push(node);
  }
  const first = children.reduce<MoveNode | undefined>(
    (lowest, node) => (lowest === undefined || node.id < lowest.id ? node : lowest),
    undefined,
  );
  if (first === undefined) return null;

  // A remembered child only counts while it still hangs off the current node
  // (ids are reset with the tree, so a stale entry must not be trusted).
  const remembered = lastChildByParent.get(currentNodeId);
  const lastChild =
    remembered !== undefined && children.some((child) => child.id === remembered)
      ? remembered
      : null;

  if (currentNodeId === null) {
    if (activeChip !== null) return linePaths[activeChip]?.[0] ?? null;
    return lastChild ?? first.id;
  }
  if (lastChild !== null) return lastChild;
  for (const key of CANONICAL_ROLE_ORDER) {
    const path = linePaths[key] ?? [];
    const index = path.indexOf(currentNodeId);
    if (index < 0) continue;
    return path[index + 1] ?? first.id;
  }
  return first.id;
}

// ─── Snapshot (restored reveal) ──────────────────────────────────────────────

/**
 * Bounds on a persisted tree snapshot. The snapshot is a per-tab navigation aid
 * (it rides on the Analyze -> Back reveal cache), so it is capped when built AND
 * when replayed: a tampered or runaway entry cannot balloon the tree (T-237-05).
 */
export const REVEAL_TREE_SNAPSHOT_MAX_PATHS = 32;
export const REVEAL_TREE_SNAPSHOT_MAX_PLIES = 64;

/**
 * The reveal tree as UCI paths, never node ids: ids differ across a rebuild
 * because lines graft asynchronously (the game line arrives after a restore).
 * Known-line nodes are re-seeded from the chips, so only the user's own
 * sidelines and the shown position need persisting.
 */
export interface RevealTreeSnapshot {
  rootFocus: RoleKey | null;
  /** UCIs from the puzzle position to the shown position. */
  currentPath: string[];
  /** UCIs from the puzzle position to each free leaf (the user's sidelines). */
  sidelinePaths: string[][];
}

function uciPathTo(nodes: Map<NodeId, MoveNode>, id: NodeId | null): string[] {
  return pathToNode(nodes, id)
    .flatMap((nodeId) => {
      const node = nodes.get(nodeId);
      return node !== undefined ? [nodeUci(node)] : [];
    })
    .slice(0, REVEAL_TREE_SNAPSHOT_MAX_PLIES);
}

/** Serializes the tree: the focus, the shown position and every free leaf. */
export function buildRevealTreeSnapshot(
  nodes: Map<NodeId, MoveNode>,
  currentNodeId: NodeId | null,
  linePaths: Partial<Record<RoleKey, NodeId[]>>,
  rootFocus: RoleKey | null,
): RevealTreeSnapshot {
  const known = new Set(Object.values(linePaths).flatMap((path) => path ?? []));
  const parents = new Set<NodeId>();
  for (const node of nodes.values()) {
    if (node.parentId !== null) parents.add(node.parentId);
  }
  const sidelinePaths: string[][] = [];
  for (const node of nodes.values()) {
    if (sidelinePaths.length >= REVEAL_TREE_SNAPSHOT_MAX_PATHS) break;
    // A free LEAF: its root->leaf path also covers every free ancestor of it.
    if (known.has(node.id) || parents.has(node.id)) continue;
    sidelinePaths.push(uciPathTo(nodes, node.id));
  }
  return { rootFocus, currentPath: uciPathTo(nodes, currentNodeId), sidelinePaths };
}
