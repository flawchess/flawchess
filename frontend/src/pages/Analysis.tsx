/**
 * Analysis — standalone /analysis page.
 *
 * Default export (required by React.lazy — every other page uses a named export;
 * this is the intentional divergence, see RESEARCH.md Pitfall 1).
 *
 * Composes:
 *   useAnalysisBoard  — branching move-tree board state
 *   useStockfishEngine — UCI WASM engine state
 *   EvalBar / EngineLines / VariationTree — analysis display components
 *   ChessBoard / BoardControls — board interaction
 *   EvalChart — below-board eval chart with slider (Phase 140 game mode)
 *
 * Security:
 *   T-138-01: FEN-guard on ?fen= param — malformed FEN degrades to STARTING_FEN.
 *   T-140-02a: NaN-guard on ?game_id= / ?ply= params — malformed → null → isGameMode false.
 *   T-140-02b: L-8 guard on mainLine[ply] accesses — out-of-bounds → undefined → no-op.
 *
 * Engine: on by default (D-06); "Loading engine…" shown in eval area while WASM inits;
 *   board stays interactive throughout (SC#3).
 *
 * Modes: ?fen= seeds free play; ?game_id=X&ply=Y loads the full game at ply Y (game mode).
 *   The legacy tactic mode (?flaw_ply=) was removed in Quick 260627-l2z; clicking a
 *   move-list tactic chip grafts the PV as an in-tree sideline with a depth overlay.
 */

import { useEffect, useMemo, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Chess } from 'chess.js';
import {
  ArrowLeftRight,
  ChessKnight,
  Cpu,
  type LucideIcon,
  Tag,
  TrendingUp,
  User,
} from 'lucide-react';
import { useAnalysisBoard } from '@/hooks/useAnalysisBoard';
import { useStockfishEngine } from '@/hooks/useStockfishEngine';
import { useStockfishGradingEngine } from '@/hooks/useStockfishGradingEngine';
import { useMaiaEngine } from '@/hooks/useMaiaEngine';
import { useMaiaEloDefault } from '@/hooks/useMaiaEloDefault';
import { useFlawChessEngine } from '@/hooks/useFlawChessEngine';
import { useUserProfile } from '@/hooks/useUserProfile';
import { useGameOverlay } from '@/hooks/useGameOverlay';
import { useLiveMoveFlaw } from '@/hooks/useLiveMoveFlaw';
import { useTacticLines, useLibraryGame } from '@/hooks/useLibrary';
import { toDisplayDepthForOrientation } from '@/lib/tacticDepth';
import { buildPvArrow } from '@/lib/tacticArrows';
import { EvalBar } from '@/components/analysis/EvalBar';
import { EngineLines, EngineLinesSkeleton, LINES_MIN_HEIGHT } from '@/components/analysis/EngineLines';
import { FlawChessEngineLines, MAX_LINES as FC_MAX_LINES } from '@/components/analysis/FlawChessEngineLines';
import { FlawChessAgreementVerdict } from '@/components/analysis/FlawChessAgreementVerdict';
import { Card, CardHeader, CardBody } from '@/components/ui/card';
import { Switch } from '@/components/ui/switch';
import { VariationTree } from '@/components/analysis/VariationTree';
import type { FlawMarkerEntry } from '@/components/analysis/VariationTree';
import type { FlawSeverity } from '@/types/library';
import { tacticOrientationAtPly } from '@/lib/tacticOrientation';
import { EvalChart } from '@/components/library/EvalChart';
import { AnalysisTagsPanel } from '@/components/analysis/AnalysisTagsPanel';
import { MaiaHumanPanel } from '@/components/analysis/MaiaHumanPanel';
import { EloSelector } from '@/components/analysis/EloSelector';
import { TemperatureSelector, TEMPERATURE_DEFAULT } from '@/components/analysis/TemperatureSelector';
import type { HoveredQualityMove } from '@/components/analysis/MaiaMoveQualityBar';
import { ChessBoard } from '@/components/board/ChessBoard';
import type { BoardArrow } from '@/components/board/ChessBoard';
import { BoardControls } from '@/components/board/BoardControls';
import { PlayerBar } from '@/components/board/PlayerBar';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { uciToSquares } from '@/lib/sanToSquares';
import {
  TAC_MISSED,
  TAC_ALLOWED,
  MOVE_HIGHLIGHT_GOOD,
  STOCKFISH_ACCENT,
  MAIA_ACCENT,
  FLAWCHESS_ENGINE_ACCENT,
  FLAWCHESS_ENGINE_ARROW,
  BEST_MOVE_ARROW,
  NEXT_MOVE_ARROW,
} from '@/lib/theme';
import { selectCandidatesByMass, nearestByElo, classifyMoveQuality, type MoveGrade } from '@/lib/moveQuality';
import type { MoveQualityEval, EngineLine } from '@/components/analysis/MovesByRatingChart';
import { sideToMoveFromFen } from '@/lib/liveFlaw';
import type { NodeId, MoveNode } from '@/hooks/useAnalysisBoard';
import { buildEvalLookup, getByUci, getBySan } from '@/lib/engineEvalLookup';
import type { RankedLine } from '@/lib/engine/types';

// ─── Constants ────────────────────────────────────────────────────────────────

const STARTING_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';

/** Engine label shown in the engine info line — the bundled Stockfish 18 WASM. */
const ENGINE_NAME = 'Stockfish 18';

/** Cap on the per-session live engine-eval cache (FEN → completed eval), item 4. */
const LIVE_EVAL_CACHE_MAX = 256;

/** Below this width the page renders its mobile takeover layout (matches the shell's
 *  `sm` breakpoint where the app swaps to mobile chrome). */
const MOBILE_BREAKPOINT_PX = 640;

/** Normalized width of the move-quality-bar hover arrows (quick 260705-kfg). */
const QUALITY_HOVER_ARROW_WIDTH = 0.6;

/** Normalized width of the on-main-line next-move arrow — thin so it reads as a
 *  subtle hint layered over the wider 0.5 engine arrows. */
const NEXT_MOVE_ARROW_WIDTH = 0.18;

/**
 * Phase 156 (ARROW-01/02/03, D-02): top-1-per-engine arrow count for the
 * free-analysis board's FC + SF arrow layer. A future engine-settings panel
 * may make this configurable (e.g. top-2) — bumping this constant is the only
 * change needed then, no prop threading now (D-03).
 */
const ARROW_COUNT = 1;

/** Normalized width of the FlawChess Engine board arrow — widest of the three
 *  concentric arrows so it draws at the bottom (D-05). Maxed at 1.0 (156 UAT: the
 *  FC practical move is the headline signal, so its arrow is the boldest on the board). */
const FLAWCHESS_ENGINE_ARROW_WIDTH = 1.0;

/** Normalized width of the Stockfish board arrow — nests inside the FC arrow
 *  and outside the thin white next-move arrow (D-05). */
const STOCKFISH_ENGINE_ARROW_WIDTH = 0.5;

/**
 * True while the viewport is below the mobile breakpoint. Drives a single-tree render
 * (mobile OR desktop, never both) so the board / eval-chart / variation-tree mount once —
 * a CSS `hidden` split would duplicate their stable `id`/`data-testid`s and the engine board.
 */
function useIsMobile(): boolean {
  const [isMobile, setIsMobile] = useState(
    () =>
      typeof window !== 'undefined' &&
      window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT_PX - 1}px)`).matches,
  );
  useEffect(() => {
    const mq = window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT_PX - 1}px)`);
    const update = () => setIsMobile(mq.matches);
    mq.addEventListener('change', update);
    return () => mq.removeEventListener('change', update);
  }, []);
  return isMobile;
}

// ─── Shared engine-card header toggle (D-03) ──────────────────────────────────

/**
 * Switch + accent-tinted caption, shared by all three engine card headers
 * (Stockfish/Maia/FlawChess) so none of the three headers triples this
 * near-identical markup inline (155-RESEARCH.md Pitfall 5). Visual weight:
 * switch first (left), caption text after (UI-SPEC Component Inventory §3).
 * The checked-state track color is set via an inline `style` override (wins
 * over the Switch primitive's default `data-[state=checked]:bg-primary`
 * class) rather than a CSS custom property, keeping this a plain, typed
 * `style={{...}}` object like every other accent usage in this file.
 */
function EngineToggleHeader({
  checked,
  onCheckedChange,
  accent,
  testId,
  ariaLabel,
  icon: Icon,
  children,
}: {
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
  accent: string;
  testId: string;
  ariaLabel: string;
  icon: LucideIcon;
  children: ReactNode;
}) {
  return (
    <>
      <Switch
        checked={checked}
        onCheckedChange={onCheckedChange}
        aria-label={ariaLabel}
        data-testid={testId}
        style={checked ? { backgroundColor: accent } : undefined}
      />
      <span
        className="flex items-center gap-1.5 text-sm font-medium"
        style={{ color: accent }}
      >
        <Icon className="size-4 shrink-0" aria-hidden="true" />
        {children}
      </span>
    </>
  );
}

// ─── Root-ply helper ──────────────────────────────────────────────────────────

/**
 * Derive the ply offset of a position from its FEN.
 * rootPly = (fullmoveNumber - 1) * 2 + (sideToMove === 'b' ? 1 : 0)
 * Used by EngineLines (startPly) and VariationTree (rootPly) to produce
 * correct move-number labels for opening-position entries.
 */
function fenToRootPly(fen: string | undefined): number {
  if (!fen) return 0;
  const parts = fen.split(' ');
  const side = parts[1];
  const fullmove = parts[5];
  if (side === undefined || fullmove === undefined) return 0;
  const ply = (Number(fullmove) - 1) * 2 + (side === 'b' ? 1 : 0);
  return Number.isNaN(ply) ? 0 : ply;
}

/**
 * Main-line ply the tactic PV sideline forks from, by orientation (Quick 260628-pu2 UAT).
 *
 * Missed lines fork at the pre-flaw DECISION board (flawPly-1) and replay the
 * should-have-played PV. Allowed lines fork at the FLAW position itself (flawPly): the
 * sideline begins with the opponent's punishing response, not a replay of the flaw move.
 * The backend's allowed_moves prepends the flaw move at index 0, so allowed PVs grafted
 * here drop that lead-in move (allowed_moves.slice(1)).
 */
function forkPlyForOrientation(flawPly: number, orientation: 'missed' | 'allowed'): number {
  return orientation === 'allowed' ? flawPly : flawPly - 1;
}

/**
 * Stable key for a tactic line (Quick 260703-kyb multi-line state): identifies which
 * flaw a chip / open line belongs to. Used as the openLines Map key and as an
 * activePvKeys entry so VariationTree can read chip "on" state by membership.
 */
function flawKey(flaw: { ply: number; orientation: 'missed' | 'allowed' }): string {
  return `${flaw.ply}:${flaw.orientation}`;
}

/**
 * The engine's top-line first move (UCI) converted to SAN at `baseFen` — feeds
 * MovesByRatingChart's `bestSan` emphasis (Plan 06, SURF-01). Returns null for no
 * PV yet or an illegal/malformed replay (never throws).
 */
function bestSanFromPv(baseFen: string, uci: string | null): string | null {
  const squares = uciToSquares(uci);
  if (!squares || !uci) return null;
  try {
    const chess = new Chess(baseFen);
    const move = chess.move({
      from: squares.from,
      to: squares.to,
      promotion: uci.length > 4 ? uci[4] : undefined,
    });
    return move.san;
  } catch {
    return null;
  }
}

type OpenLine = { rootNodeId: NodeId; ply: number; orientation: 'missed' | 'allowed' };
type FlawRef = { ply: number; orientation: 'missed' | 'allowed' };

/**
 * Find the open (or pending) tactic line the board is currently "in" — extracted to a
 * pure module-scope function (not inlined in a component useMemo) because the React
 * Compiler's memoization-preservation lint cannot analyze this control flow (nested
 * for/while loop with early returns) inline; a plain function called FROM useMemo
 * satisfies it (Quick 260703-kyb).
 *
 * Checks pendingFlaw first (its fork node always matches BEFORE any previously-focused
 * line would, since handlePvChipClick / the auto-open effect navigate there immediately),
 * then every open line: match by fork-node equality OR subtree containment (walk parentId
 * up from currentNodeId until it reaches the line's rootNodeId).
 */
function findFocusedFlaw(
  isGameMode: boolean,
  currentNodeId: NodeId | null,
  pendingFlaw: FlawRef | null,
  openLines: Map<string, OpenLine>,
  mainLine: NodeId[],
  nodes: Map<NodeId, MoveNode>,
): FlawRef | null {
  if (!isGameMode || currentNodeId === null) return null;
  if (pendingFlaw != null) {
    const forkNodeId = mainLine[forkPlyForOrientation(pendingFlaw.ply, pendingFlaw.orientation)];
    if (forkNodeId !== undefined && currentNodeId === forkNodeId) return pendingFlaw;
  }
  for (const line of openLines.values()) {
    const forkNodeId = mainLine[forkPlyForOrientation(line.ply, line.orientation)];
    if (forkNodeId !== undefined && currentNodeId === forkNodeId) {
      return { ply: line.ply, orientation: line.orientation };
    }
    if (isNodeInsideSubtree(nodes, currentNodeId, line.rootNodeId)) {
      return { ply: line.ply, orientation: line.orientation };
    }
  }
  return null;
}

/** True iff walking parentId up from `nodeId` reaches `rootId`. */
function isNodeInsideSubtree(
  nodes: Map<NodeId, MoveNode>,
  nodeId: NodeId,
  rootId: NodeId,
): boolean {
  let id: NodeId | null = nodeId;
  while (id !== null) {
    if (id === rootId) return true;
    id = nodes.get(id)?.parentId ?? null;
  }
  return false;
}

/**
 * Walk children from `rootNodeId` following the lowest-id child chain until it leaves
 * `pvNodeIds` — the ordered node array of an open tactic line. Module-scope pure
 * function for the same React Compiler reason as findFocusedFlaw above.
 */
function buildFocusedPvLine(
  nodes: Map<NodeId, MoveNode>,
  pvNodeIds: Set<NodeId>,
  rootNodeId: NodeId,
): NodeId[] {
  const chain: NodeId[] = [];
  let id: NodeId | undefined = rootNodeId;
  while (id !== undefined && pvNodeIds.has(id)) {
    chain.push(id);
    let lowest: NodeId | undefined;
    for (const node of nodes.values()) {
      if (node.parentId === id && (lowest === undefined || node.id < lowest)) lowest = node.id;
    }
    id = lowest;
  }
  return chain;
}

// ─── Page ────────────────────────────────────────────────────────────────────

/**
 * Default-exported Analysis page (required by React.lazy in App.tsx).
 * ROUTE-01: reachable by authenticated users inside ProtectedLayout.
 * ROUTE-02: ?fen= seeds the board; empty/malformed → standard start.
 * ROUTE-04 (Phase 140): ?game_id=&ply= enters game mode (full game at initial ply).
 */
export default function Analysis() {
  const [searchParams] = useSearchParams();
  const fenParam = searchParams.get('fen') ?? undefined;

  // Security FEN-guard (T-138-01): attempt chess.js parse; fall back to
  // undefined (STARTING_FEN) so a hand-typed bad URL renders the start
  // position instead of crashing react-chessboard at render.
  let guardedFen: string | undefined;
  if (fenParam !== undefined) {
    try {
      new Chess(fenParam);
      guardedFen = fenParam;
    } catch {
      // Malformed FEN: degrade to STARTING_FEN (guardedFen stays undefined).
    }
  }

  // ── URL params — game mode (T-140-02a) ──────────────────────────────────────
  // Security: NaN-guard on numeric params — malformed → null → mode disabled.
  const gameIdRaw = searchParams.get('game_id');
  const plyRaw = searchParams.get('ply');

  const gameId: number | null =
    gameIdRaw != null && !Number.isNaN(Number(gameIdRaw)) ? Number(gameIdRaw) : null;
  // Game mode initial ply (T-140-02a: NaN-guard). null when the ply param is absent
  // or malformed; game mode still loads (gameId drives it) and opens at ply 0
  // (Quick 260628-qta UAT: game_id without ply loads the game at ply 0).
  const initialPly: number | null =
    plyRaw != null && !Number.isNaN(Number(plyRaw)) ? Number(plyRaw) : null;

  // Game mode is keyed on game_id alone — the ply param is optional (defaults to 0
  // via the `?? 0` guards on every mainLine[initialPly] access below).
  const isGameMode = gameId != null;

  const isMobile = useIsMobile();

  // D-06: engine on by default; toggle available via infoSlot button.
  const [engineEnabled, setEngineEnabled] = useState(true);
  // Phase 155 D-02/D-03: the Maia and FlawChess Engine header switches — all
  // three engine cards default ON (all-by-default UI, gated on the SC4
  // real-device mobile-memory UAT per 155-RESEARCH.md D-02).
  const [maiaEnabled, setMaiaEnabled] = useState(true);
  const [flawChessEnabled, setFlawChessEnabled] = useState(true);
  const [boardFlipped, setBoardFlipped] = useState(false);
  // Once we have auto-oriented the board to the player's color, manual flips win.
  const hasAutoFlipped = useRef(false);

  // Quick 260703-kyb: multi-line tactic state (move-list tactic-chip expansion →
  // flat in-tree sideline; replaces the Phase 140 activePvFlaw singleton).
  // Ephemeral in-memory — D-01: not URL-encoded.
  //
  // openLines — every currently GRAFTED tactic line, keyed by flawKey(ply, orientation).
  // pendingFlaw — the line currently being opened, awaiting its PV fetch. Only one
  // open action is in flight at a time (clicks/auto-opens are sequential); once its
  // fetch arrives, the graft effect below records it into openLines and clears this.
  const [openLines, setOpenLines] = useState<
    Map<string, { rootNodeId: NodeId; ply: number; orientation: 'missed' | 'allowed' }>
  >(() => new Map());
  const [pendingFlaw, setPendingFlaw] = useState<{
    ply: number;
    orientation: 'missed' | 'allowed';
  } | null>(null);

  // Quick 260702-nm8 (Task 3): desktop-only hover-highlight from the tags panel onto
  // the eval chart's markers — mirrors LibraryGameCard's highlightedPlies. Not passed
  // on mobile (the chart lives on a different tab there).
  const [tagsHighlightedPlies, setTagsHighlightedPlies] = useState<Set<number> | null>(null);

  // Quick 260705-kfg: the moves of the move-quality bar's currently-hovered segment
  // (SAN + severity color), drawn as board arrows. Null when nothing is hovered.
  const [hoveredQualityMoves, setHoveredQualityMoves] = useState<HoveredQualityMove[] | null>(null);

  // ── All hooks (unconditional, React rules) ────────────────────────────────────

  const {
    position,
    currentNodeId,
    nodes,
    mainLine,
    pvNodeIds,
    nextId,
    rootFen,
    lastMove,
    makeMove,
    goBack,
    goForward,
    goToNode,
    loadMainLine,
    isOnMainLine,
    insertPvLine,
    playUciLine,
    deleteSubtree,
    clearAllSidelines,
    isOnPvLine,
    containerRef,
  } = useAnalysisBoard(guardedFen);

  // Engine hook must run unconditionally (React rules).
  // 155 UAT un-merge: the standalone Stockfish search runs whenever its own
  // switch (`engineEnabled`) is on, independently of the FlawChess Engine. The
  // two engines pick very different moves (objective vs practical-for-you), so
  // the user must see both — the Stockfish card shows Stockfish's own top-2 with
  // depth deepening live, alongside the separate FlawChess Engine card. This
  // reverses the earlier D-04 handoff (which fed the SF surfaces the FlawChess
  // engine's objective root eval and blanked the Stockfish card). Cost: two
  // concurrent Stockfish searches (this standalone WASM + the engine's 2-4
  // worker pool); mobile memory stays the deferred SC4 follow-up, not a blocker.
  const engine = useStockfishEngine({
    fen: engineEnabled ? position : null,
    enabled: engineEnabled,
  });

  // focusedFlaw: the open (or pending) line the board is currently "in" — its subtree
  // contains currentNodeId, OR its fork node equals currentNodeId (so the depth arrow
  // shows while parked at a just-opened line's fork). pendingFlaw is checked first: as
  // soon as it's set, handlePvChipClick/the auto-open effect also navigate to its fork
  // node, so this always matches BEFORE any previously-focused line would.
  const focusedFlaw = useMemo(
    () => findFocusedFlaw(isGameMode, currentNodeId, pendingFlaw, openLines, mainLine, nodes),
    [isGameMode, currentNodeId, pendingFlaw, openLines, mainLine, nodes],
  );

  // focusedPvLine: the ordered node array of the focused line — replaces the old
  // singleton pvLine as the input to the overlay memos below. Empty while the line is
  // still pending (not yet grafted) or when nothing is focused.
  const focusedPvLine = useMemo<NodeId[]>(() => {
    if (focusedFlaw == null) return [];
    const line = openLines.get(flawKey(focusedFlaw));
    if (line == null) return [];
    return buildFocusedPvLine(nodes, pvNodeIds, line.rootNodeId);
  }, [focusedFlaw, openLines, nodes, pvNodeIds]);

  // Contextual PV fetch: lazy-fetch for inline chip expansion (L-3: unconditional).
  // Keyed on pendingFlaw when a line is being opened, else the focused (already-open)
  // line — react-query caches per (gameId, ply), so re-focusing an already-opened line
  // is a cache hit, not a re-fetch.
  const fetchFlaw = pendingFlaw ?? focusedFlaw;
  const {
    data: contextualTacticData,
    isFetching: contextualPending,
    isError: contextualError,
  } = useTacticLines(gameId, fetchFlaw?.ply ?? null, fetchFlaw != null && isGameMode);

  // Game-by-id fetch for full-game mode (D-4: existing endpoint, no new backend).
  // Unconditional hook call; enabled only when isGameMode (gameId is null otherwise).
  const { data: gameData, isError: gameError } = useLibraryGame(
    isGameMode ? gameId : null,
  );

  // Free-play ELO default source (D-07) — read from useUserProfile(), never useAuth().user
  // (no rating field there, cf. beta-gating memory).
  const { data: userProfile } = useUserProfile();

  // D-06/D-07: "you are here" ELO for the Maia surfaces, derived from game-mode
  // rating-at-game-time or free-play current_rating, with user-override precedence.
  const { selectedElo, setSelectedElo } = useMaiaEloDefault({
    isGameMode,
    gameData,
    profile: userProfile,
    // Default the ELO to whoever is to move — the opponent's rating on their
    // moves — so the Maia surfaces reflect the actual decision-maker (quick 260705-m3z).
    sideToMove: sideToMoveFromFen(position),
  });

  // Whose move the analysed position is — drives the Maia verdict's you/opponent
  // framing. False in free play (no opponent).
  const isOpponentToMove =
    isGameMode && gameData?.user_color != null && sideToMoveFromFen(position) !== gameData.user_color;

  // Play a named move from the Maia verdict prose as a free move (quick 260705-mth).
  // The prose SANs are legal at the current position; resolve to from/to and hand
  // to makeMove, which advances into the existing line or forks a sideline.
  const playProseMove = (san: string): void => {
    try {
      const move = new Chess(position).move(san);
      if (move) makeMove(move.from, move.to);
    } catch {
      // SAN no longer legal (position changed under the prose) — ignore.
    }
  };

  // Maia-3 human-move model (MAIA-04/05, SURF-05): full per-ELO curve + WDL for the
  // current position, no server round-trip. Phase 155 D-03: gated on the Maia
  // card's own header switch (`maiaEnabled`) — MAIA-02's laziness is otherwise
  // already satisfied by the route-level React.lazy covering this whole page.
  // Note: this is a SEPARATE Worker instance from the FlawChess Engine's own
  // internal maiaQueue (Phase 154) — turning this switch off must not starve
  // the FlawChess Engine's policy source (UI-SPEC Component Inventory §3).
  const maia = useMaiaEngine({ fen: position, enabled: maiaEnabled, selectedElo });

  // Phase 159 D-08 (Thread A): session-only policy-temperature state, plain
  // useState mirroring the ELO slider's no-persistence behavior (no
  // localStorage/URL param) — resets to TEMPERATURE_DEFAULT on every page load.
  const [temperature, setTemperature] = useState(TEMPERATURE_DEFAULT);

  // FlawChess Engine (Phase 153-155 client-side MCTS search core, DISPLAY-01):
  // gated on its own header switch (`flawChessEnabled`), independent of the
  // Stockfish and Maia switches. `selectedElo` is shared for both colors
  // (D-07/Open Question 2, 155-02). `temperature` (Phase 159 D-06/D-07) reshapes
  // the root-mover's-own-side Maia policy before search and composes with the
  // findability ranking automatically (buildRankedLines reads child.prior).
  const flawChessEngine = useFlawChessEngine({
    fen: flawChessEnabled ? position : null,
    enabled: flawChessEnabled,
    elo: selectedElo,
    policyTemperature: temperature,
  });

  // Seeding guard refs: prevent re-running effects after the first game load.
  const hasLoadedMainLine = useRef(false);
  const hasNavigatedToInitialPly = useRef(false);

  // Quick 260702-fog: the tactic (if any) the board auto-opens to when the entry ply carries
  // a user tactic chip. Drives BOTH the initial navigation effect and the move-list top-align
  // target, so the two stay in sync. Missed wins over allowed (see tacticOrientationAtPly).
  const initialTactic = useMemo<{ ply: number; orientation: 'missed' | 'allowed' } | null>(() => {
    if (!isGameMode) return null;
    const ply = initialPly ?? 0;
    const orientation = tacticOrientationAtPly(gameData?.flaw_markers, ply);
    return orientation === null ? null : { ply, orientation };
  }, [isGameMode, gameData?.flaw_markers, initialPly]);

  // Ply the move list top-aligns on first open: the tactic fork ply when a tactic auto-opens
  // (missed → decision board ply-1, allowed → flaw ply), else the plain entry ply. Keeps the
  // scroller's initial top-align on the node the board actually navigates to (Quick 260702-fog).
  const initialAlignPly =
    initialTactic !== null
      ? forkPlyForOrientation(initialTactic.ply, initialTactic.orientation)
      : (initialPly ?? 0);

  // ── Effects (game seeding, board flip, contextual PV insert) ──────────────────

  // Game mode: orient the board to the player's color once (item 5). Black games open
  // flipped; manual flips afterward win (hasAutoFlipped guard). Free play stays white.
  useEffect(() => {
    if (!isGameMode || gameData?.user_color == null || hasAutoFlipped.current) return;
    hasAutoFlipped.current = true;
    setBoardFlipped(gameData.user_color === 'black');
  }, [isGameMode, gameData?.user_color]);

  // Game mode: seed the board once when game data arrives (L-1: never call from chip click).
  useEffect(() => {
    if (!isGameMode || gameData?.moves == null || hasLoadedMainLine.current) return;
    hasLoadedMainLine.current = true;
    loadMainLine(gameData.moves, STARTING_FEN);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [gameData?.moves, isGameMode]);

  // Navigate to initialPly AFTER loadMainLine state lands (separate effect — RESEARCH.md Hardest Part 3).
  // Watches mainLine.length so it fires after the batch-reset from loadMainLine.
  useEffect(() => {
    if (!isGameMode || mainLine.length === 0 || hasNavigatedToInitialPly.current) return;
    hasNavigatedToInitialPly.current = true;
    const ply = initialPly ?? 0;
    // Quick 260702-fog: if the opening ply carries a user tactic chip, open its line
    // automatically — same effect as clicking the chip (setPendingFlaw + navigate to the
    // fork node; the useTacticLines → insertPvLine graft effect below records the sideline
    // once the PV arrives). Missed forks at the decision board (ply-1), allowed at the flaw
    // position. initialAlignPly mirrors this fork so the move list top-aligns the same node.
    if (initialTactic !== null) {
      const forkNodeId = mainLine[forkPlyForOrientation(initialTactic.ply, initialTactic.orientation)];
      if (forkNodeId !== undefined) {
        setPendingFlaw(initialTactic);
        goToNode(forkNodeId);
        return;
      }
    }
    // No tactic chip here (or fork out of bounds): navigate to initialPly as before.
    // T-140-02b: L-8 guard — out-of-bounds ply is a no-op, not a crash.
    const nodeId = mainLine[ply];
    if (nodeId !== undefined) goToNode(nodeId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mainLine.length, isGameMode]);

  // Insert contextual PV sideline when the fetch arrives (L-1: insertPvLine, not loadMainLine).
  // Quick 260703-kyb: records the new line into openLines WITHOUT touching any previously
  // open line — insertPvLine unions ids into pvNodeIds, never clobbers.
  useEffect(() => {
    if (!isGameMode || pendingFlaw == null || contextualTacticData == null) return;
    const key = flawKey(pendingFlaw);
    if (openLines.has(key)) return; // already recorded — guard against a stale re-run
    // Allowed lines start AT the flaw position and drop the prepended flaw move (index 0),
    // so the sideline begins with the opponent's response (Quick 260628-pu2 UAT). Missed
    // lines start at the decision board and use the full PV.
    const pvMoves =
      pendingFlaw.orientation === 'missed'
        ? (contextualTacticData.missed_moves ?? [])
        : (contextualTacticData.allowed_moves ?? []).slice(1);
    // T-140-02b: L-8 guard on the fork node lookup.
    const forkNodeId = mainLine[forkPlyForOrientation(pendingFlaw.ply, pendingFlaw.orientation)];
    if (forkNodeId === undefined || pvMoves.length === 0) return;
    // Snapshot the line's root id BEFORE grafting — the hook assigns nextId to the first
    // grafted node (insertPvLine's batch-build loop starts at prev.nextId).
    const rootNodeId = nextId;
    insertPvLine(pvMoves, forkNodeId);
    setOpenLines((prev) => new Map(prev).set(key, { rootNodeId, ply: pendingFlaw.ply, orientation: pendingFlaw.orientation }));
    setPendingFlaw(null);
    // mainLine/openLines/nextId intentionally omitted — mainLine is stable after game load;
    // openLines/nextId are read fresh from the latest render at the moment this effect
    // fires (triggered by pendingFlaw/contextualTacticData, already guarded above), so
    // reacting to them too would cause spurious re-runs when the user navigates the tree.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [contextualTacticData, pendingFlaw?.ply, pendingFlaw?.orientation, isGameMode]);

  // ── Derived values ────────────────────────────────────────────────────────────

  // Stockfish card loading skeleton — spins only while the standalone Stockfish
  // WASM is still initializing (155 UAT un-merge: the search runs independently
  // of the FlawChess Engine, so this no longer depends on flawChessEnabled).
  const engineLoading = engineEnabled && !engine.isReady;
  // Mirrors engineLoading: true only while the FlawChess Engine's WorkerPool/
  // MaiaQueue are still spinning up (pre-`isReady`); once ready,
  // FlawChessEngineLines handles its own pre-first-snapshot skeleton.
  const flawChessLoading = flawChessEnabled && !flawChessEngine.isReady;

  const rootPly = fenToRootPly(rootFen);
  const currentPly = fenToRootPly(position);

  const canGoForward = useMemo(() => {
    for (const node of nodes.values()) {
      if (node.parentId === currentNodeId) return true;
    }
    return false;
  }, [nodes, currentNodeId]);

  // MovesByRatingChart emphasis (Plan 06, SURF-01): the SAN of the move that reached
  // the current node — true for both game mode (the played main-line/PV move) and
  // free play (the last move the user played), since both read the same node field.
  const playedSan = currentNodeId !== null ? (nodes.get(currentNodeId)?.san ?? null) : null;

  // MovesByRatingChart emphasis: the engine's current top-line first move, converted
  // to SAN at the current position. Prefer the standalone Stockfish top move (its
  // objective best); when Stockfish is off but the FlawChess Engine is on, fall back
  // to the top practical candidate so the 151.1 best-move highlight still shows
  // (WR-04, 155-REVIEW.md).
  const bestSan = useMemo(() => {
    const uci = engineEnabled
      ? (engine.pvLines[0]?.moves[0] ?? null)
      : flawChessEnabled
        ? (flawChessEngine.rankedLines[0]?.rootMove ?? null)
        : null;
    return bestSanFromPv(position, uci);
  }, [position, engineEnabled, engine.pvLines, flawChessEnabled, flawChessEngine.rankedLines]);

  // Phase 151.1 SC2/D-02/D-06/D-07: the 0.95-cumulative-mass candidate set at the
  // selected ELO, unioned with {bestSan, playedSan} — computed ONCE here and
  // consumed as one contributor to the grading union below (unionSans), plus
  // passed to the chart (as shownSans), replacing MovesByRatingChart's own
  // top-6-by-peak cap.
  const shownSans = useMemo(
    () => selectCandidatesByMass(maia.perElo, selectedElo, playedSan, bestSan),
    [maia.perElo, selectedElo, playedSan, bestSan],
  );

  // Phase 159 D-10/D-12 (SEED-085 ride-along, 159-Pitfall 5): raw Maia move-probability-by-SAN
  // map at the selected ELO, computed ONCE here (the SAME rung the chart displays via
  // nearestByElo) and passed down to FlawChessAgreementVerdict as `rawProbBySan` — the verdict
  // gate must never call nearestByElo independently, so the prose can never contradict the chart.
  const rawProbBySan = useMemo(
    () => nearestByElo(maia.perElo, selectedElo)?.moveProbabilities ?? {},
    [maia.perElo, selectedElo],
  );

  // Phase 158 (SEED-087 SC2): the FC card's own top-MAX_LINES displayed SANs,
  // converted from their root UCI moves — the FlawChess Engine's contribution
  // to the shared grading union below. Empty (a no-op contributor) whenever
  // the FC card is off, so the union reflects only active consumers.
  const flawChessDisplayedSans = useMemo(() => {
    if (!flawChessEnabled) return [];
    const sans: string[] = [];
    for (const line of flawChessEngine.rankedLines.slice(0, FC_MAX_LINES)) {
      const san = bestSanFromPv(position, line.rootMove);
      if (san !== null) sans.push(san);
    }
    return sans;
  }, [flawChessEnabled, flawChessEngine.rankedLines, position]);

  // Phase 158 (SEED-087 SC2, RESEARCH Pitfall 4): the deduplicated, sorted
  // union of the Maia chart's shownSans and the FC card's displayed SANs —
  // the shared grading run's candidate set. Sorted + deduped (mirroring the
  // grading hook's own candidatesKey pattern) so a re-throttle of the SAME
  // top moves produces the same array and does not re-trigger the search.
  const unionSans = useMemo(() => {
    const maiaSans = maiaEnabled ? shownSans : [];
    const fcSans = flawChessEnabled ? flawChessDisplayedSans : [];
    return Array.from(new Set([...maiaSans, ...fcSans])).sort();
  }, [maiaEnabled, shownSans, flawChessEnabled, flawChessDisplayedSans]);

  // Phase 158 (SEED-087 SC2, RESEARCH Pitfall 5): the shared grading run is
  // gated on EITHER display consumer being active — fen/enabled are always
  // paired on this same condition below so the worker is never alive-but-
  // positionless.
  const gradingEnabled = maiaEnabled || flawChessEnabled;

  // Phase 151.1 SC3 / Phase 158 (SEED-087 SC2): a SECOND, independent
  // Stockfish worker that grades the FC∪Maia candidate union via one
  // searchmoves-restricted MultiPV search. This shared run now powers BOTH
  // the Moves-by-Rating chart (via qualityBySan) and the FC card's reconciled
  // evals (via evalLookup below), so it is gated on `maiaEnabled ||
  // flawChessEnabled` (gradingEnabled) — replacing the prior Maia-switch-only
  // gating. It never touches the `engine` (useStockfishEngine) instance or
  // its consumers.
  const grading = useStockfishGradingEngine({
    fen: gradingEnabled ? position : null,
    candidateSans: unionSans,
    enabled: gradingEnabled,
  });

  // Phase 158 (SEED-087 SC1): the single UCI-keyed eval source every
  // displayed Stockfish eval on this page resolves through — the free run's
  // pvLines win by construction (module precedence in buildEvalLookup), so a
  // move graded by both sources always shows the free-run value, and
  // progressive refinement is emergent (a resolved UCI's value can never
  // regress to the grading value).
  const evalLookup = useMemo(
    () => buildEvalLookup(engine.pvLines, grading.gradeMap, position),
    [engine.pvLines, grading.gradeMap, position],
  );

  // Phase 158 (SEED-087 SC1/SC3/SC4, SC5 scope fence): parallel RankedLine-
  // shaped display objects — NEVER the live MCTS-core snapshots themselves —
  // with only `objectiveEvalCp` swapped for the reconciled lookup value. A
  // resolved mate grade (evalCp null) yields null here, same as the
  // pre-existing FC-source cp-only limitation (RankedLine has no mate field);
  // the card renders its existing '…' placeholder, not a bug.
  const reconciledRankedLines = useMemo<RankedLine[]>(
    () =>
      flawChessEngine.rankedLines.slice(0, FC_MAX_LINES).map((line) => ({
        ...line,
        objectiveEvalCp: getByUci(evalLookup, line.rootMove)?.evalCp ?? null,
      })),
    [flawChessEngine.rankedLines, evalLookup],
  );

  // Phase 151.1 D-08 / Phase 158 (SEED-087 SC3): 5-bucket quality
  // classification of the RECONCILED grades (not the raw grading pass's
  // gradeMap directly) — so a move's displayed number and its severity color
  // can never disagree at a bucket boundary (covers the Maia chart line/
  // SAN-label colors, the quality-bar segments, and positionVerdict). The
  // reconciled map is built over the SAME SAN keyspace the grading pass
  // produced; an unresolved SAN (a sanToUci conversion failure) maps to a
  // null/null grade, never the raw pool grade.
  const qualityBySan = useMemo<Map<string, MoveQualityEval>>(() => {
    const reconciledGradeMap = new Map<string, MoveGrade>();
    for (const san of grading.gradeMap.keys()) {
      reconciledGradeMap.set(
        san,
        getBySan(evalLookup, position, san) ?? { evalCp: null, evalMate: null, depth: 0 },
      );
    }
    // Pass the primary engine's bestSan so the chart's "best" agrees with the
    // eval bar + engine card (151.1 UAT: reconcile the two Stockfish sources).
    const infoBySan = classifyMoveQuality(reconciledGradeMap, sideToMoveFromFen(position), bestSan);
    const merged = new Map<string, MoveQualityEval>();
    for (const [san, info] of infoBySan) {
      const grade = reconciledGradeMap.get(san);
      merged.set(san, {
        quality: info.quality,
        evalCp: grade?.evalCp ?? null,
        evalMate: grade?.evalMate ?? null,
      });
    }
    return merged;
  }, [evalLookup, grading.gradeMap, position, bestSan]);

  // The primary engine's top PV lines (best + 2nd-best), each as its first move's
  // SAN + white-POV eval — shown as a reference header in the Maia chart tooltip
  // (151.1 UAT). Prefer standalone Stockfish (the objective reference); fall back to
  // the FlawChess Engine's RECONCILED practical top-2 only when Stockfish is off
  // (WR-04, Phase 158 SEED-087 SC1) — relocated after evalLookup/
  // reconciledRankedLines so its FC branch can read reconciled values. The
  // FlawChess source has no mate field, so evalMate is null there.
  const engineTopLines = useMemo<EngineLine[]>(() => {
    const lines: EngineLine[] = [];
    if (engineEnabled) {
      for (const line of engine.pvLines.slice(0, 2)) {
        const san = bestSanFromPv(position, line.moves[0] ?? null);
        if (san === null) continue;
        lines.push({ san, evalCp: line.evalCp, evalMate: line.evalMate });
      }
      return lines;
    }
    if (flawChessEnabled) {
      for (const line of reconciledRankedLines) {
        const san = bestSanFromPv(position, line.rootMove);
        if (san === null) continue;
        lines.push({ san, evalCp: line.objectiveEvalCp, evalMate: null });
      }
    }
    return lines;
  }, [position, engineEnabled, engine.pvLines, flawChessEnabled, reconciledRankedLines]);

  // ── Derived values (game mode — new) ─────────────────────────────────────────

  // Slider parked when not on the main line (D-05): disabled + opacity-40 + tooltip.
  const isOnMainLineForSlider = currentNodeId === null || isOnMainLine(currentNodeId);

  // Eval-chart sync ply (Quick 260627-mt8): the board's current main-line ply, or the
  // fork point (nearest main-line ancestor) when off the main line. Drives the eval-
  // chart slider so navigating the move list / board keeps the chart in sync; on a
  // sideline it parks the (disabled) slider at the position the sideline branches from.
  const evalChartPly = useMemo<number | null>(() => {
    if (!isGameMode || currentNodeId === null) return null;
    if (isOnMainLine(currentNodeId)) {
      const idx = mainLine.indexOf(currentNodeId);
      return idx >= 0 ? idx : null;
    }
    let id: NodeId | null = nodes.get(currentNodeId)?.parentId ?? null;
    while (id !== null) {
      if (isOnMainLine(id)) {
        const idx = mainLine.indexOf(id);
        return idx >= 0 ? idx : null;
      }
      id = nodes.get(id)?.parentId ?? null;
    }
    return null;
  }, [isGameMode, currentNodeId, mainLine, nodes, isOnMainLine]);

  // Per-side remaining clock at the current position (Quick 260628-pcb). eval_series
  // carries the mover's remaining clock per ply (even ply = White, odd = Black,
  // 0-based on moves — same convention as game_positions.ply and mainLine indexing).
  // Walk up to the current ply, keeping the latest clock seen for each side.
  // clock_seconds is null for imports without %clk (e.g. some chess.com games), so
  // that side simply shows no clock.
  const playerClocks = useMemo<{ white: number | null; black: number | null }>(() => {
    const series = gameData?.eval_series;
    if (!isGameMode || series == null) return { white: null, black: null };
    const ply = evalChartPly ?? -1;
    let white: number | null = null;
    let black: number | null = null;
    for (const point of series) {
      if (point.ply > ply) break; // eval_series is ply-ascending
      if (point.clock_seconds == null) continue;
      if (point.ply % 2 === 0) white = point.clock_seconds;
      else black = point.clock_seconds;
    }
    return { white, black };
  }, [isGameMode, gameData?.eval_series, evalChartPly]);

  // Flaw marker map for VariationTree: keyed by mainLine nodeId.
  // Only entries with a tactic chip or blunder/mistake severity are included (D-02, D-03).
  const flawMarkerByNodeId = useMemo<Map<NodeId, FlawMarkerEntry>>(() => {
    const map = new Map<NodeId, FlawMarkerEntry>();
    if (!isGameMode || gameData?.flaw_markers == null) return map;
    // Quick 260628-1t5 (reverting e116912c item 5): the missed chip goes back onto the
    // flaw node mainLine[ply], together with the allowed chip + severity glyph — a single
    // entry per flaw node, no decision-node (ply-1) split.
    for (const fm of gameData.flaw_markers) {
      // noUncheckedIndexedAccess guard (T-140-02b): skip out-of-range plies.
      const nodeId = mainLine[fm.ply];
      if (nodeId === undefined) continue;
      // Quick 260628-u7d follow-up: opponent tactic tags are surfaced in the eval-chart
      // tooltip (built separately in EvalChart) but NOT in the move list — suppress the
      // opponent's motifs here. Severity glyphs stay both-color (pre-existing behavior).
      const missedMotif = fm.is_user ? fm.missed_tactic_motif : null;
      const allowedMotif = fm.is_user ? fm.allowed_tactic_motif : null;
      const sev = fm.severity;
      if (missedMotif !== null || allowedMotif !== null || sev === 'blunder' || sev === 'mistake') {
        map.set(nodeId, {
          missedMotif,
          allowedMotif,
          missedDepth: fm.is_user ? fm.missed_tactic_depth : null,
          allowedDepth: fm.is_user ? fm.allowed_tactic_depth : null,
          severity: sev,
          ply: fm.ply,
        });
      }
    }
    return map;
  }, [isGameMode, gameData, mainLine]);

  // Multi-active chip highlight (Quick 260703-kyb): every currently OPEN or
  // pending-open chip's key, so multiple tactic chips can read "on" simultaneously
  // (flat siblings) instead of a single activePvNodeId/activePvOrientation match.
  const activePvKeys = useMemo<Set<string>>(() => {
    const keys = new Set<string>();
    for (const key of openLines.keys()) keys.add(key);
    if (pendingFlaw != null) keys.add(flawKey(pendingFlaw));
    return keys;
  }, [openLines, pendingFlaw]);

  // Contextual overlay PV ply (0 = fork position, 1+ = steps into the focused PV).
  const contextualCurrentPly =
    currentNodeId !== null ? focusedPvLine.indexOf(currentNodeId) + 1 : 0;

  // onStoredLine for contextual overlay: true only when on the PV sideline itself.
  const contextualOnStoredLine = currentNodeId !== null && isOnPvLine(currentNodeId);

  // Game-mode overlay (Quick 260627): precomputed blue best-move arrow + tactic depth
  // overlay + eval bar, with the live engine supplying only the grey 2nd-best line.
  const gameOverlay = useGameOverlay({
    enabled: isGameMode,
    engineEnabled,
    evalSeries: gameData?.eval_series,
    flawMarkers: gameData?.flaw_markers,
    mainLine,
    currentNodeId,
    isOnMainLine,
    lastMove,
    enginePvLines: engine.pvLines,
    engineEvalCp: engine.evalCp,
    engineEvalMate: engine.evalMate,
    engineDepth: engine.depth,
  });

  // ── Live free-move classification (item 4) ────────────────────────────────────
  // Cache each position's COMPLETED engine eval (white POV) keyed by FEN. The engine
  // only sets evalCp/evalMate once a search finishes (null while analyzing), so a
  // non-null value here is a depth-complete eval for the current position. Held in
  // state (not a ref) so reading it during render is legitimate; updates are
  // low-frequency (one per completed ~1.5s search) and no-op when unchanged.
  const [engineEvalByFen, setEngineEvalByFen] = useState<
    Map<string, { cp: number | null; mate: number | null }>
  >(() => new Map());
  useEffect(() => {
    if (!engineEnabled) return;
    if (engine.evalCp == null && engine.evalMate == null) return;
    setEngineEvalByFen((prev) => {
      const existing = prev.get(position);
      if (existing && existing.cp === engine.evalCp && existing.mate === engine.evalMate) {
        return prev; // unchanged — skip the re-render
      }
      const next = new Map(prev);
      next.set(position, { cp: engine.evalCp, mate: engine.evalMate });
      // Rough FIFO cap (Map preserves insertion order) so a long session can't grow it
      // without bound.
      if (next.size > LIVE_EVAL_CACHE_MAX) {
        const oldest = next.keys().next().value;
        if (oldest !== undefined) next.delete(oldest);
      }
      return next;
    });
  }, [position, engine.evalCp, engine.evalMate, engineEnabled]);

  // FEN of the position BEFORE the current move — the live classifier's "best before".
  const parentFen = useMemo<string | null>(() => {
    if (currentNodeId === null) return null;
    const node = nodes.get(currentNodeId);
    if (!node) return null;
    if (node.parentId === null) return rootFen;
    return nodes.get(node.parentId)?.fen ?? rootFen;
  }, [currentNodeId, nodes, rootFen]);

  // Live classification applies only to freely-played moves off the precomputed line:
  // any node that is NOT a game main-line node (game mode) and NOT a grafted PV node
  // (those are best-play lines). In free-play mode every played node qualifies.
  const liveFlawActive =
    currentNodeId !== null &&
    !(isGameMode && isOnMainLine(currentNodeId)) &&
    !isOnPvLine(currentNodeId);

  const parentEval = parentFen != null ? engineEvalByFen.get(parentFen) ?? null : null;

  const liveFlaw = useLiveMoveFlaw({
    active: liveFlawActive,
    parentFen,
    parentEval,
    childEvalCp: engine.evalCp,
    childEvalMate: engine.evalMate,
    lastMove,
  });

  // Persist each freely-played node's live blunder/mistake classification, keyed by node id
  // (Quick 260628-r5v UAT). Two purposes: (1) the move-list glyph stays on EVERY sideline move
  // the user has stepped through, not just the current one; (2) it caches the per-node
  // classification so returning to an earlier sideline move re-shows its icon without waiting
  // on the live engine to re-grade it. (The eval VALUE is already cached by FEN in
  // engineEvalByFen above; this caches the derived classification per node.)
  const [liveFlawByNode, setLiveFlawByNode] = useState<Map<NodeId, FlawSeverity>>(
    () => new Map(),
  );
  useEffect(() => {
    if (!liveFlawActive || currentNodeId === null) return;
    const severity = liveFlaw.squareMarkers[0]?.severity;
    // Only blunder/mistake paint a glyph; skip while still pending (squareMarkers is empty
    // until both parent and child evals complete) or when the move grades clean/inaccuracy.
    if (severity !== 'blunder' && severity !== 'mistake') return;
    setLiveFlawByNode((prev) => {
      if (prev.get(currentNodeId) === severity) return prev; // unchanged — skip re-render
      const next = new Map(prev);
      next.set(currentNodeId, severity);
      // FIFO cap (Map preserves insertion order) mirrors the eval-cache bound.
      if (next.size > LIVE_EVAL_CACHE_MAX) {
        const oldest = next.keys().next().value;
        if (oldest !== undefined) next.delete(oldest);
      }
      return next;
    });
  }, [liveFlawActive, currentNodeId, liveFlaw]);

  // Move-list marker map (item 1, Quick 260628-1t5): merge the game-mode flaw markers with
  // the live free-move severity for the CURRENT node, so a freely-played blunder/mistake
  // paints the same glyph in the move list as on the board (single source — liveFlaw's own
  // squareMarker severity — so list and board can never disagree). Only blunder/mistake get
  // a glyph (inaccuracy/clean show none, matching the main-line behavior). The live entry is
  // NOT gated by game mode — it must also surface in free-play mode (where flawMarkerByNodeId
  // is empty). When there is no live flaw the original map is returned unchanged (stable ref).
  const moveListMarkers = useMemo<Map<NodeId, FlawMarkerEntry>>(() => {
    const liveSeverity = liveFlaw.squareMarkers[0]?.severity;
    const showCurrentLive =
      currentNodeId !== null && (liveSeverity === 'blunder' || liveSeverity === 'mistake');
    if (liveFlawByNode.size === 0 && !showCurrentLive) return flawMarkerByNodeId;

    const mainLineSet = new Set(mainLine);
    const merged = new Map(flawMarkerByNodeId);
    const addLive = (nodeId: NodeId, severity: FlawSeverity): void => {
      if (merged.has(nodeId)) return; // game/PV flaw entry wins (keeps its tactic chips)
      if (mainLineSet.has(nodeId)) return; // stale id reused as a main-line node after reload
      if (!nodes.has(nodeId)) return; // node deleted (e.g. a collapsed PV fork)
      merged.set(nodeId, {
        missedMotif: null,
        allowedMotif: null,
        missedDepth: null,
        allowedDepth: null,
        severity,
        ply: -1, // placeholder — free-move entries carry no game ply
      });
    };
    // Persisted sideline classifications first, then the current node's in-flight one.
    for (const [nodeId, severity] of liveFlawByNode) addLive(nodeId, severity);
    if (currentNodeId !== null && (liveSeverity === 'blunder' || liveSeverity === 'mistake')) {
      addLive(currentNodeId, liveSeverity);
    }
    return merged;
  }, [flawMarkerByNodeId, liveFlaw, currentNodeId, liveFlawByNode, mainLine, nodes]);

  // Move-list coloring inside the PV sideline (Quick 260628-ojq UAT, extends item 4):
  // teal (TAC_MISSED) for a missed tactic, crimson (TAC_ALLOWED) for an allowed one. Every
  // sideline move from the fork up to and including the depth-0 resolving move is colored,
  // so the whole tactic line reads in its orientation color (not just the punchline move).
  // The *_tactic_ply_index indexes the PV moves, which line up 1:1 with focusedPvLine.
  const sidelineNodeColors = useMemo(() => {
    const colors = new Map<NodeId, string>();
    if (!isGameMode || focusedFlaw == null || contextualTacticData == null) return colors;
    const isMissed = focusedFlaw.orientation === 'missed';
    // allowed_tactic_ply_index indexes the API allowed_moves (flaw move at index 0); the
    // grafted focusedPvLine drops that lead-in, so shift -1 to align (Quick 260628-pu2).
    const resolveIdx = isMissed
      ? (contextualTacticData.missed_tactic_ply_index ?? 0)
      : (contextualTacticData.allowed_tactic_ply_index ?? 1) - 1;
    const color = isMissed ? TAC_MISSED : TAC_ALLOWED;
    for (let i = 0; i <= resolveIdx; i++) {
      const node = focusedPvLine[i];
      if (node !== undefined) colors.set(node, color);
    }
    return colors;
  }, [isGameMode, focusedFlaw, contextualTacticData, focusedPvLine]);

  // Board "tactic overlay" while navigating a PV sideline (item 3): the depth-countdown
  // arrow on the next stored PV move, mirroring the old tactic-mode overlay. Anchored to
  // the FOCUSED line's depth/orientation (the line the board is currently in); the live
  // engine still supplies the grey 2nd.
  const pvSidelineArrows = useMemo<BoardArrow[] | null>(() => {
    if (!isGameMode || focusedFlaw == null || contextualTacticData == null) return null;
    const orientation = focusedFlaw.orientation;
    const forkNodeId = mainLine[forkPlyForOrientation(focusedFlaw.ply, orientation)];
    const onPvPath = contextualOnStoredLine || (forkNodeId !== undefined && currentNodeId === forkNodeId);
    if (!onPvPath) return null;

    const depthRaw =
      orientation === 'missed'
        ? (contextualTacticData.missed_depth ?? 0)
        : (contextualTacticData.allowed_depth ?? 0);
    // anchored=false (Quick 260628-1t5 DECISION 2): the analysis board is a navigable
    // surface, so the allowed +1 decision-anchor offset is dropped (allowed reads like missed).
    const rootDisplayDepth = toDisplayDepthForOrientation(depthRaw, orientation, false);

    // Steps into the focused PV from the current node (0 at the fork position).
    const stepIntoPv = contextualCurrentPly;
    const nextPvNodeId = focusedPvLine[stepIntoPv];
    const nextPvNode = nextPvNodeId !== undefined ? nodes.get(nextPvNodeId) : undefined;
    const nextMove = nextPvNode ? { from: nextPvNode.from, to: nextPvNode.to } : null;
    if (!nextMove) return null;

    const displayDepth = Math.max(0, rootDisplayDepth - stepIntoPv);
    // Depth 0 is the move after the tactic resolves: treat it as payoff so it shows no
    // number and drops the orientation color — the tactic is over by then (Quick 260628-pu2
    // UAT). The countdown therefore runs ...2, 1 (punchline), then payoff.
    const isPayoff = stepIntoPv >= rootDisplayDepth;
    // 156 UAT (top-1 per engine): only the single PV-continuation arrow — the
    // light-blue 2nd-best Stockfish arrow was dropped here for parity with the
    // free-analysis board (one FC arrow + one SF arrow, no second-best anywhere).
    const arrows = buildPvArrow(nextMove, displayDepth, isPayoff, orientation);
    return arrows.length > 0 ? arrows : null;
  }, [
    isGameMode,
    focusedFlaw,
    contextualTacticData,
    contextualOnStoredLine,
    contextualCurrentPly,
    currentNodeId,
    mainLine,
    focusedPvLine,
    nodes,
  ]);

  // Quick 260705-kfg: arrows for the move-quality bar's hovered segment — one per
  // move, tinted its severity color. Each SAN is replayed at the CURRENT position
  // to resolve from/to squares (skipped if illegal/malformed; never throws). Works
  // in both game mode and free play, so it's derived independently of isGameMode.
  const qualityHoverArrows = useMemo<BoardArrow[] | null>(() => {
    if (hoveredQualityMoves === null || hoveredQualityMoves.length === 0) return null;
    const arrows: BoardArrow[] = [];
    for (const { san, color } of hoveredQualityMoves) {
      try {
        const chess = new Chess(position);
        const move = chess.move(san);
        arrows.push({
          startSquare: move.from,
          endSquare: move.to,
          color,
          width: QUALITY_HOVER_ARROW_WIDTH,
        });
      } catch {
        // Illegal SAN for this position (stale hover across a board move) — skip it.
      }
    }
    return arrows.length > 0 ? arrows : null;
  }, [hoveredQualityMoves, position]);

  // Translucent white "next move played" arrow, shown whenever the board sits on
  // the main line (root or a main-line node). It points to the move that follows
  // in the game's main line — mainLine[0] at the root, else the node after the
  // current one. Rendered on top of the engine overlay (onTop) and a bit thinner.
  const nextMoveArrow = useMemo<BoardArrow | null>(() => {
    const onMain = currentNodeId === null || isOnMainLine(currentNodeId);
    if (!onMain) return null;
    const idx = currentNodeId === null ? -1 : mainLine.indexOf(currentNodeId);
    const nextNodeId = mainLine[idx + 1];
    if (nextNodeId === undefined) return null; // at the end of the main line
    const nextNode = nodes.get(nextNodeId);
    if (!nextNode) return null;
    return {
      startSquare: nextNode.from,
      endSquare: nextNode.to,
      color: NEXT_MOVE_ARROW,
      width: NEXT_MOVE_ARROW_WIDTH,
      onTop: true,
    };
  }, [currentNodeId, isOnMainLine, mainLine, nodes]);

  // Phase 156 (ARROW-01/02/03): the board's two live engine arrows — amber
  // FlawChess Engine (practical move) and blue Stockfish (objective move).
  // Independently toggled via the existing Phase 155 card switches; each simply
  // doesn't render until its engine's first snapshot yields a root move (no
  // placeholder arrow, mirrors the card skeleton timing). 156 UAT: this layer is
  // the default board overlay in BOTH game mode and free analysis — the engine
  // arrows must be identical regardless of whether a game is loaded.
  const engineArrows = useMemo<BoardArrow[]>(() => {
    const arrows: BoardArrow[] = [];
    if (flawChessEnabled) {
      for (let i = 0; i < ARROW_COUNT; i++) {
        const fcSquares = uciToSquares(flawChessEngine.rankedLines[i]?.rootMove ?? null);
        if (fcSquares) {
          arrows.push({
            startSquare: fcSquares.from,
            endSquare: fcSquares.to,
            color: FLAWCHESS_ENGINE_ARROW,
            width: FLAWCHESS_ENGINE_ARROW_WIDTH,
            layerKey: `fc-${i}`,
          });
        }
      }
    }
    if (engineEnabled) {
      for (let i = 0; i < ARROW_COUNT; i++) {
        const sfSquares = uciToSquares(engine.pvLines[i]?.moves[0] ?? null);
        if (sfSquares) {
          arrows.push({
            startSquare: sfSquares.from,
            endSquare: sfSquares.to,
            color: BEST_MOVE_ARROW,
            width: STOCKFISH_ENGINE_ARROW_WIDTH,
            layerKey: `sf-${i}`,
          });
        }
      }
    }
    return arrows;
  }, [flawChessEnabled, flawChessEngine.rankedLines, engineEnabled, engine.pvLines]);

  // Board arrows (156 UAT — game/free parity): the FC + SF engine-arrow layer is
  // the default overlay in BOTH modes, so the board looks identical whether or not
  // a game is loaded. The move-quality hover overlay still wins (both modes) so
  // hovering the bar previews its moves; the game-only flaw-line drill-down overlay
  // (pvSidelineArrows, self-gated to null outside game mode) still takes precedence
  // when you navigate into a specific flaw's PV. The old game-review default overlay
  // (gameOverlay.boardArrows: Stockfish best + light-blue 2nd-best) is no longer
  // drawn — top-1 per engine everywhere. Draw order is ChessBoard's width sort
  // (D-05), not array order; the white next-move arrow layers on top (onTop).
  const baseArrows: BoardArrow[] | undefined =
    qualityHoverArrows ??
    pvSidelineArrows ??
    (engineArrows.length > 0 ? engineArrows : undefined);
  // D-09 arrow isolation (157 UAT): while a move is being previewed via hover (or
  // first-tap on mobile), show ONLY that move's arrow(s). The translucent white
  // next-move arrow was previously appended unconditionally, so it survived the
  // preview and cluttered the board — suppress it too whenever a hover is active.
  const isHoverIsolated = qualityHoverArrows !== null;
  const boardArrows: BoardArrow[] | undefined =
    nextMoveArrow && !isHoverIsolated ? [...(baseArrows ?? []), nextMoveArrow] : baseArrows;

  // ── Handlers ──────────────────────────────────────────────────────────────────

  // L-5: game mode Reset → clear every sideline, reset multi-line state, navigate to entry ply.
  const handleReset = isGameMode
    ? () => {
        clearAllSidelines();
        setOpenLines(new Map());
        setPendingFlaw(null);
        setLiveFlawByNode(new Map()); // drop persisted sideline glyphs on reset
        // T-140-02b: L-8 guard on initialPly — out-of-bounds is a no-op.
        const nodeId = mainLine[initialPly ?? 0];
        if (nodeId !== undefined) goToNode(nodeId);
      }
    : () => {
        setLiveFlawByNode(new Map());
        loadMainLine([], rootFen);
      };

  const canReset = currentNodeId !== null;

  // Inline chip click: toggle off (SAME chip only — deleteSubtree removes just that
  // line, others stay open) or open a new line WITHOUT touching any other open line
  // (Quick 260703-kyb — flat siblings, removes the old singleton "clear previous PV
  // on chip switch" behavior).
  const handlePvChipClick = (
    nodeId: NodeId,
    flaw: { ply: number; orientation: 'missed' | 'allowed' },
  ): void => {
    const key = flawKey(flaw);
    const existing = openLines.get(key);
    if (existing != null) {
      // Same chip clicked again: collapse ONLY this line — no fetch needed.
      deleteSubtree(existing.rootNodeId);
      setOpenLines((prev) => {
        const next = new Map(prev);
        next.delete(key);
        return next;
      });
      return;
    }
    // Different/new chip: open it. insertPvLine is called by the graft effect once
    // contextualTacticData arrives; other open lines are left untouched.
    setPendingFlaw(flaw);
    // Navigate to the fork node — decision board (ply-1) for missed, flaw position (ply) for
    // allowed (Quick 260628-pu2 UAT). T-140-02b guard.
    const forkNodeId = mainLine[forkPlyForOrientation(flaw.ply, flaw.orientation)];
    if (forkNodeId !== undefined) goToNode(forkNodeId);
    void nodeId; // nodeId passed for API symmetry with VariationTree; ply identifies the flaw
  };

  // EvalChart scrub callback: navigate board on main line only (slider disabled off-line).
  const handleEvalChartPlyChange = (ply: number | null): void => {
    if (ply === null || !isOnMainLineForSlider) return;
    // T-140-02b: L-8 guard — ply from eval chart may not align exactly with mainLine.
    const nodeId = mainLine[ply];
    if (nodeId !== undefined) goToNode(nodeId);
  };

  // Cycling a flaw tag/severity/motif chip surfaces the eval-chart tooltip on the
  // targeted ply, mirroring the Library game card's click-to-cycle. commandedPly is
  // the target ply; commandSeq is a nonce so re-clicking the same ply re-fires the
  // reveal (and re-shows the tooltip after the chart's outside-click dismissal).
  const [tagCommandedPly, setTagCommandedPly] = useState<number | null>(null);
  const [tagCommandSeq, setTagCommandSeq] = useState(0);

  // ── Render ────────────────────────────────────────────────────────────────────

  // Maia expected score is the side-to-MOVE's expected score (WDL is emitted from the
  // mover's POV). Convert to a WHITE-relative fraction for the eval bar so it agrees
  // with the Stockfish (white-POV) bar and the board orientation. 0.5 while unresolved.
  const maiaWhiteFraction =
    maia.expectedScoreAtSelectedElo === null
      ? 0.5
      : sideToMoveFromFen(position) === 'white'
        ? maia.expectedScoreAtSelectedElo
        : 1 - maia.expectedScoreAtSelectedElo;

  // Eval-bar wiring. Left slot shows FC (brown) over Maia (violet) whenever the
  // FlawChess Engine is enabled — its practical-for-you expected score. Right slot
  // is always the standalone Stockfish objective eval (155 UAT un-merge: no handoff
  // — Stockfish runs independently again, so the SF bar shows Stockfish's own eval
  // with depth deepening live). Kept as a small derived block (not inlined in the
  // JSX below) per Pitfall 5.
  // noUncheckedIndexedAccess: topLine is RankedLine | undefined, narrowed via
  // the `topLine ? ... : ...` ternaries below rather than a non-null assertion.
  const topLine = flawChessEngine.rankedLines[0];
  const fcWhiteFraction = topLine
    ? sideToMoveFromFen(position) === 'white'
      ? topLine.practicalScore
      : 1 - topLine.practicalScore
    : 0.5;
  const leftEvalBarWhiteFraction = flawChessEnabled ? fcWhiteFraction : maiaWhiteFraction;
  const leftEvalBarAccent = flawChessEnabled ? FLAWCHESS_ENGINE_ACCENT : MAIA_ACCENT;
  const leftEvalBarTestId = flawChessEnabled ? 'analysis-flawchess-eval-bar' : 'analysis-maia-eval-bar';
  // The right bar is labeled "SF" (Stockfish): the real standalone Stockfish eval
  // whenever its switch is on, going neutral when the user turns Stockfish off
  // (`!engineEnabled`). `null`/`0` reads as the sigmoid midpoint in EvalBar's
  // computeWhiteFraction (no data → 0.5).
  const rightEvalBarEvalCp = engineEnabled ? gameOverlay.evalCp : null;
  const rightEvalBarEvalMate = engineEnabled ? gameOverlay.evalMate : null;
  const rightEvalBarDepth = engineEnabled ? gameOverlay.evalDepth : 0;

  // Board + EvalBar row — the single source of the `analysis-board` ref/testid and the
  // react-chessboard instance. Shared by the desktop and mobile trees (only one renders
  // at a time via isMobile), so the board mounts exactly once either way.
  const boardRow = (
    <div className="flex flex-row items-stretch gap-2">
      {/* Left eval bar — FlawChess Engine (brown) when enabled (D-04 precedence),
          else Maia (violet, D-01/D-05, SURF-04). Single expected-score fill: both
          sources bypass the cp sigmoid entirely via whiteFraction. 0.5 fallback
          while neither source has produced a result yet.
          Bug fix (151.1 UAT): Maia's WDL is from the side-to-MOVE's perspective (the
          board is mirrored to the mover's POV when Black is to move — see
          maiaEncoding.encodeBoard), so expectedScore is the mover's expected score.
          The bar's whiteFraction must be WHITE-relative to match the Stockfish bar and
          the board orientation, so invert it whenever Black is to move. Without this
          the bar read inverted on every Black-to-move position. RankedLine.practicalScore
          (D-06) is likewise root-side-to-move-relative, same inversion applies (see
          fcWhiteFraction above). */}
      <EvalBar
        evalCp={null}
        evalMate={null}
        depth={0}
        whiteFraction={leftEvalBarWhiteFraction}
        flipped={boardFlipped}
        accentColor={leftEvalBarAccent}
        testId={leftEvalBarTestId}
      />

      <div ref={containerRef} data-testid="analysis-board" tabIndex={0} className="flex-1">
        <ChessBoard
          id="analysis-board"
          position={position}
          onPieceDrop={makeMove}
          lastMove={lastMove}
          // Precomputed overlay (main line) wins; else the live free-move
          // classification (item 4), which also covers free-play mode. Default green
          // (MOVE_HIGHLIGHT_GOOD): a played move is assumed OK until the engine proves
          // otherwise, so engine-line (PV) moves and not-yet-graded moves read green
          // instead of the shared yellow fallback. The engine still overrides to
          // red/orange on a blunder/mistake (and yellow on an inaccuracy).
          lastMoveColor={
            gameOverlay.lastMoveHighlightColor ??
            liveFlaw.lastMoveHighlightColor ??
            MOVE_HIGHLIGHT_GOOD
          }
          flipped={boardFlipped}
          arrows={boardArrows}
          squareMarkers={
            gameOverlay.squareMarkers.length > 0
              ? gameOverlay.squareMarkers
              : liveFlaw.squareMarkers
          }
          maxWidth={600}
        />
      </div>

      {/* Right eval bar: precomputed eval in game mode (immediate), live engine
          otherwise — useGameOverlay passes the engine through when disabled. D-04
          handoff: while the FlawChess Engine runs, this bar is instead fed its top
          line's own objective root eval (never a mate — ±MATE_CP_EQUIVALENT reads
          as near-mate on the sigmoid scale) rather than a second live Stockfish
          search on the same position (POOL-04). */}
      <EvalBar
        evalCp={rightEvalBarEvalCp}
        evalMate={rightEvalBarEvalMate}
        depth={rightEvalBarDepth}
        flipped={boardFlipped}
        accentColor={STOCKFISH_ACCENT}
      />
    </div>
  );

  // Player info row (desktop, game mode): name + ELO left, remaining clock right.
  // Rendered above and below the board, ordered by orientation (Quick 260628-pcb).
  const playerBar = (color: 'white' | 'black') => (
    <PlayerBar
      isWhite={color === 'white'}
      name={(color === 'white' ? gameData?.white_username : gameData?.black_username) ?? null}
      rating={(color === 'white' ? gameData?.white_rating : gameData?.black_rating) ?? null}
      clockSeconds={color === 'white' ? playerClocks.white : playerClocks.black}
      testId={`analysis-player-${color}`}
    />
  );

  // Small source cap centered over an eval bar (151.1 UAT): "FC"/"Maia" (brown/
  // violet) over the left bar per D-04 precedence, "SF" (blue) over the right.
  // "Maia" is wider than the w-5 slot and overflows symmetrically — the ~7px
  // right overflow stays inside the gap-2 to the player name, and the left
  // overflow lands in the inter-column gutter. Common Pitfall 4: keep the new
  // "FC" cap at the existing text-xs size — do not introduce text-sm here.
  const evalBarCap = (text: 'Maia' | 'SF' | 'FC', color: string) => (
    // text-xs (below the usual text-sm floor) — a tiny bar cap acting as a visual
    // aside, per UAT "make the labels smaller". leading-none keeps the row compact.
    <span className="whitespace-nowrap text-xs font-medium leading-none" style={{ color }}>
      {text}
    </span>
  );

  // Eval-bar-width flanking slot — matches boardRow's `w-5` bars + `gap-2` so the
  // center content lines up exactly with the board's left/right edges.
  const evalBarSlot = (content: ReactNode) => (
    <div className="flex w-5 shrink-0 justify-center">{content}</div>
  );

  // Row flanking the board with the source caps, its center aligned to the board
  // edges. `player` renders the name/clock line (game mode); free play passes null
  // to show the caps alone over the bars.
  const boardHeaderRow = (player: ReactNode) => (
    <div className="flex flex-row items-center gap-2">
      {evalBarSlot(
        flawChessEnabled
          ? evalBarCap('FC', FLAWCHESS_ENGINE_ACCENT)
          : evalBarCap('Maia', MAIA_ACCENT),
      )}
      <div className="min-w-0 flex-1">{player}</div>
      {evalBarSlot(evalBarCap('SF', STOCKFISH_ACCENT))}
    </div>
  );

  // Bottom player row: same board-edge alignment as the header, no caps.
  const boardFooterRow = (player: ReactNode) => (
    <div className="flex flex-row items-center gap-2">
      {evalBarSlot(null)}
      <div className="min-w-0 flex-1">{player}</div>
      {evalBarSlot(null)}
    </div>
  );

  // VariationTree props — shared between the desktop side panel and the mobile Moves tab.
  // The mobile tab passes variant="vertical" to fill the space; props are otherwise identical.
  const variationTree = (variant: 'responsive' | 'vertical') => (
    <VariationTree
      variant={variant}
      nodes={nodes}
      mainLine={mainLine}
      currentNodeId={currentNodeId}
      rootPly={rootPly}
      initialPly={isGameMode ? initialAlignPly : undefined}
      onNodeClick={goToNode}
      decorations={sidelineNodeColors}
      pvNodeIds={isGameMode ? pvNodeIds : undefined}
      flawMarkerByNodeId={moveListMarkers}
      onPvChipClick={isGameMode ? handlePvChipClick : undefined}
      activePvKeys={isGameMode ? activePvKeys : undefined}
      pvFetchPending={isGameMode ? contextualPending : undefined}
      pvFetchError={isGameMode ? contextualError : undefined}
      onDeleteLine={isGameMode ? deleteSubtree : undefined}
    />
  );

  // Board controls — shared; the desktop panel keeps the charcoal pill, the mobile
  // footer passes flat so the buttons read like the main nav (Quick 260628-dgv).
  const boardControls = (flat = false) => (
    <BoardControls
      onBack={goBack}
      onForward={goForward}
      onReset={handleReset}
      onFlip={() => setBoardFlipped((f) => !f)}
      canGoBack={currentNodeId !== null}
      canReset={canReset}
      canGoForward={canGoForward}
      flat={flat}
    />
  );

  // The eval-chart element (game mode only) — placed below the board on desktop, inside the
  // Eval tab on mobile. Single instance; rendered in whichever tree is active.
  const evalChartReady =
    isGameMode &&
    gameId != null &&
    gameData?.eval_series != null &&
    gameData.flaw_markers != null &&
    gameData.phase_transitions != null &&
    gameData.moves != null;
  // `highlightedPlies` is desktop-only (the tags panel's hover-highlight, Task 3);
  // the mobile evalChart() call site omits it, leaving chart markers un-dimmed there.
  const evalChart = (heightClass: string, highlightedPlies?: Set<number> | null) =>
    evalChartReady && gameId != null && gameData?.eval_series != null && gameData.flaw_markers != null && gameData.phase_transitions != null && gameData.moves != null ? (
      <EvalChart
        gameId={gameId}
        evalSeries={gameData.eval_series}
        flawMarkers={gameData.flaw_markers}
        phaseTransitions={gameData.phase_transitions}
        moves={gameData.moves}
        heightClass={heightClass}
        initialPly={initialPly}
        flipped={gameData.user_color === 'black'}
        sliderTestId="analysis-eval-chart-slider"
        sliderDisabled={!isOnMainLineForSlider}
        disableHoverScrub
        onHoverPlyChange={handleEvalChartPlyChange}
        syncPly={evalChartPly}
        commandedPly={tagCommandedPly}
        commandSeq={tagCommandSeq}
        highlightedPlies={highlightedPlies}
      />
    ) : null;

  // The flaw-tags panel (game mode only, quick-260702-nm8) — severity row + Missed |
  // Allowed | Context chip block. Same readiness gate as the eval chart (implies
  // flaw_markers present); mounts exactly once regardless of desktop/mobile, mirroring
  // the evalChart helper above. Cycling a badge/chip reuses the exact goToNode pattern
  // from handleEvalChartPlyChange — a single call auto-syncs board + move list +
  // eval-chart crosshair (evalChartPly derives from currentNodeId). `withHighlight`
  // (Task 3, desktop only) wires the hover-highlight back onto the eval chart.
  const tagsPanel = (withHighlight = false) =>
    evalChartReady && gameData ? (
      <AnalysisTagsPanel
        game={gameData}
        onCyclePly={(ply) => {
          // T-140-02b: L-8 guard for noUncheckedIndexedAccess.
          const nodeId = mainLine[ply];
          if (nodeId !== undefined) goToNode(nodeId);
          // Surface the eval-chart tooltip on the cycled ply (like the game card).
          setTagCommandedPly(ply);
          setTagCommandSeq((s) => s + 1);
        }}
        onHighlightChange={withHighlight ? setTagsHighlightedPlies : undefined}
      />
    ) : null;

  // FlawChess Engine card (D-01, DISPLAY-04) — a fixed-height charcoal Card
  // stacked directly above MaiaHumanPanel, reused verbatim in BOTH the desktop
  // human column and the mobile "Human" tab (mobile-parity: D-01's "apply to
  // both" + CLAUDE.md's mobile-parity rule). Mirrors the Stockfish card's own
  // loading → off → lines CardBody pattern (line ~1585 below): flawChessLoading
  // gates the pre-`isReady` skeleton (worker pool spin-up); once ready,
  // FlawChessEngineLines renders its OWN pre-first-snapshot skeleton internally.
  const flawChessCard = (
    <Card data-testid="analysis-flawchess-panel">
      <CardHeader
        size="compact"
        data-testid="analysis-flawchess-info"
        className="font-normal text-muted-foreground"
      >
        <EngineToggleHeader
          checked={flawChessEnabled}
          onCheckedChange={setFlawChessEnabled}
          accent={FLAWCHESS_ENGINE_ACCENT}
          testId="btn-analysis-flawchess-toggle"
          ariaLabel="Toggle FlawChess Engine"
          icon={ChessKnight}
        >
          {/* ELO in parens = the mover's rating (or the slider override), the
              strength the engine is playing at (155 UAT). */}
          FlawChess Engine ({selectedElo} ELO)
        </EngineToggleHeader>
      </CardHeader>
      <CardBody className={`${LINES_MIN_HEIGHT} p-2`}>
        {flawChessLoading ? (
          <EngineLinesSkeleton testId="analysis-flawchess-loading" rows={2} />
        ) : !flawChessEnabled ? (
          <div className="flex h-full items-center px-2 text-sm text-muted-foreground">
            FlawChess Engine off
          </div>
        ) : (
          <>
            <FlawChessEngineLines
              rankedLines={reconciledRankedLines}
              isSearching={flawChessEngine.isSearching}
              baseFen={position}
              startPly={currentPly}
              flipped={boardFlipped}
              onMoveClick={playUciLine}
            />
            {/* Agreement verdict (Phase 157-02, REVIEW-02; Phase 158 SEED-087
                SC4): reads Stockfish's TRUE objective #1 from engine.pvLines[0]
                (D-01) — never engineTopLines, which silently degrades to a
                FlawChess row when standalone Stockfish is off. The FlawChess
                side is reconciledRankedLines (evalLookup-sourced), so both
                picks resolve through the SAME lookup — making "FC pick grades
                higher than the objective best" impossible by construction. */}
            <FlawChessAgreementVerdict
              flawChessLine={reconciledRankedLines[0] ?? null}
              stockfishLine={engine.pvLines[0] ?? null}
              flawChessRankedLines={reconciledRankedLines}
              engineEnabled={engineEnabled}
              elo={selectedElo}
              baseFen={position}
              rawProbBySan={rawProbBySan}
              shownSans={shownSans}
              onHoverMovesChange={setHoveredQualityMoves}
              onPlayMove={playProseMove}
            />
          </>
        )}
      </CardBody>
    </Card>
  );

  // Shared ELO slider (155 UAT): moved OUT of the Maia card because it drives BOTH
  // the FlawChess and Maia engines, not just Maia. Rendered directly below the Maia
  // panel in both the desktop human column and the mobile "Human" tab. Phase 159
  // D-08: the temperature slider renders directly below it, in this SAME shared
  // JSX const, so both mobile (humanTab) and desktop (human column) render sites
  // get it for free (mobile/desktop parity via one render site, not two).
  const eloSelector = (
    <div className="px-1 flex flex-col gap-2" data-testid="analysis-elo-selector-row">
      <EloSelector value={selectedElo} onChange={setSelectedElo} />
      <TemperatureSelector value={temperature} onChange={setTemperature} />
    </div>
  );

  // The mobile "Human" tab content (D-03, LIC-02) — shared between the game-mode
  // 4-tab strip and the free-play Moves|Human pair below, so this JSX isn't
  // duplicated across both mobile tab layouts.
  const humanTab = (
    <TabsContent value="human" className="min-h-0 overflow-y-auto thin-scrollbar">
      <div className="flex flex-col gap-3 px-3">
        {flawChessCard}
        <MaiaHumanPanel
          selectedElo={selectedElo}
          perElo={maia.perElo}
          playedSan={playedSan}
          bestSan={bestSan}
          shownSans={shownSans}
          qualityBySan={qualityBySan}
          engineTopLines={engineTopLines}
          onHoverMovesChange={setHoveredQualityMoves}
          isOpponentToMove={isOpponentToMove}
          onPlayMove={playProseMove}
          enabled={maiaEnabled}
          onToggleEnabled={setMaiaEnabled}
          compact
        />
        {eloSelector}
      </div>
    </TabsContent>
  );

  // ── Mobile takeover layout (< 640px) ──────────────────────────────────────────
  // Engine PV lines above the board (no info card), board + eval bar, then a 2-tab view
  // (Moves | Eval) that fills the space down to the in-flow board-controls footer. Free
  // play has no eval chart, so it shows only the move list (no tab bar). The shell's
  // back-button header + suppressed bottom nav (ProtectedLayout) complete the takeover.
  if (isMobile) {
    return (
      <div
        data-testid="analysis-page"
        className="flex min-h-0 flex-1 flex-col bg-background"
      >
        {/* Stockfish PV lines on top, without the info-card header. Mirrors the
            desktop `analysis-engine-card` body's loading → off → lines branches.
            155 UAT un-merge: the standalone Stockfish top-2 shows independently of
            the FlawChess Engine (no "merged" state). */}
        <div className="shrink-0 px-2 pt-2" data-testid="analysis-engine-lines-mobile">
          {engineLoading ? (
            <EngineLinesSkeleton testId="analysis-engine-loading" compact />
          ) : !engineEnabled ? (
            <div className="flex h-full items-center px-2 text-sm text-muted-foreground">
              Engine off
            </div>
          ) : (
            <EngineLines
              pvLines={engine.pvLines}
              isAnalyzing={engine.isAnalyzing}
              startPly={currentPly}
              baseFen={position}
              flipped={boardFlipped}
              onMoveClick={playUciLine}
              compact
            />
          )}
        </div>

        {/* Board + eval bar. */}
        {/* Board block: source caps + top player, board, bottom player. max-w-[92vw]
            shrinks the board a touch so the name/clock strips top and bottom stay on
            screen (151.1 UAT). Free play has no players — the caps show alone. */}
        <div className="mx-auto flex w-full max-w-[92vw] shrink-0 flex-col gap-1 px-2 pt-2">
          {boardHeaderRow(
            isGameMode && gameData ? playerBar(boardFlipped ? 'white' : 'black') : null,
          )}
          {boardRow}
          {isGameMode && gameData && boardFooterRow(playerBar(boardFlipped ? 'black' : 'white'))}
        </div>

        {/* Game load error (CLAUDE.md isError branch). */}
        {isGameMode && gameError && (
          <p className="shrink-0 px-3 py-2 text-sm text-muted-foreground">
            Failed to load game. Something went wrong. Please try again in a moment.
          </p>
        )}

        {/* Tab view — fills all vertical space between the board and the footer. */}
        {isGameMode && evalChartReady ? (
          <Tabs
            defaultValue="moves"
            className="flex min-h-0 flex-1 flex-col gap-2 px-2 pt-2"
          >
            <TabsList variant="underline" className="w-full shrink-0">
              <TabsTrigger value="moves" data-testid="analysis-tab-moves">
                <ArrowLeftRight aria-hidden="true" />
                Moves
              </TabsTrigger>
              <TabsTrigger value="eval" data-testid="analysis-tab-eval">
                <TrendingUp aria-hidden="true" />
                Chart
              </TabsTrigger>
              <TabsTrigger value="human" data-testid="analysis-tab-human">
                <User aria-hidden="true" />
                Maia
              </TabsTrigger>
              <TabsTrigger value="tags" data-testid="analysis-tab-tags">
                <Tag aria-hidden="true" />
                Tags
              </TabsTrigger>
            </TabsList>
            <TabsContent value="moves" className="flex min-h-0 flex-1 flex-col">
              {variationTree('vertical')}
            </TabsContent>
            {/* Bounded chart height (not h-full): the board already dominates the
                viewport, so a greedy chart pushed the board-controls footer off-screen
                when the mobile browser's URL bar shrank the height. h-[120px] (the
                established mobile chart height) keeps the footer visible.
                px-3 wrapper: the scrub slider is rendered 16px wider than the chart
                (±8px thumb overhang) and normally lands in the desktop card's padding;
                here it needs that horizontal room or it triggers a horizontal scrollbar
                (overflow-y-auto coerces overflow-x to auto). overflow-x-hidden is the
                belt-and-suspenders. */}
            <TabsContent value="eval" className="min-h-0 overflow-x-hidden overflow-y-auto thin-scrollbar">
              <div className="px-3">{evalChart('h-[120px]')}</div>
            </TabsContent>
            {humanTab}
            <TabsContent value="tags" className="min-h-0 overflow-y-auto thin-scrollbar">
              <div className="px-2">{tagsPanel()}</div>
            </TabsContent>
          </Tabs>
        ) : !isGameMode ? (
          // Free play (D-03 open detail): a minimal Moves | Human tab pair — no eval
          // chart / tags in free play, but the Human chart must still be reachable.
          <Tabs defaultValue="moves" className="flex min-h-0 flex-1 flex-col gap-2 px-2 pt-2">
            <TabsList variant="underline" className="w-full shrink-0">
              <TabsTrigger value="moves" data-testid="analysis-tab-moves">
                <ArrowLeftRight aria-hidden="true" />
                Moves
              </TabsTrigger>
              <TabsTrigger value="human" data-testid="analysis-tab-human">
                <User aria-hidden="true" />
                Maia
              </TabsTrigger>
            </TabsList>
            <TabsContent value="moves" className="flex min-h-0 flex-1 flex-col">
              {variationTree('vertical')}
            </TabsContent>
            {humanTab}
          </Tabs>
        ) : (
          // Game mode but not yet ready for the full tab strip (game data still
          // loading, or an unanalyzed game with no eval_series) — unchanged prior
          // behavior: move list only.
          <div className="flex min-h-0 flex-1 flex-col px-2 pt-2">
            {variationTree('vertical')}
          </div>
        )}

        {/* In-flow board-controls footer — replaces the suppressed mobile nav bar. */}
        <div
          data-testid="analysis-mobile-footer"
          className="shrink-0 border-t border-border bg-background px-2 py-2 pb-safe"
        >
          {boardControls(true)}
        </div>
      </div>
    );
  }

  return (
    <div data-testid="analysis-page" className="flex min-h-0 flex-1 flex-col bg-background">
      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-2 pb-20 md:py-6 md:pb-6 md:px-6">
        <div className="flex flex-col lg:flex-row lg:items-stretch gap-4">

          {/* Human column ──────────────────────────────────────────────────── */}
          {/* D-01 3-column layout: left = Maia ("human") surfaces, matching the
              existing right panel's ~360px width (D-02 trade-off: narrower chart,
              fewer x-axis ticks, accepted for the thematic left-grouping). */}
          <div
            data-testid="analysis-human-column"
            className="flex w-full lg:w-[360px] shrink-0 flex-col gap-4 min-w-0"
          >
            {/* Invisible spacer mirroring the board column's top player bar so the
                Human card top aligns with the board top (not the player-bar top) —
                same trick as the engine column. Desktop only; -mb-2 trims this
                column's gap-4 to the board column's gap-2. (Quick 260705-bm3) */}
            {isGameMode && gameData && (
              <div aria-hidden="true" className="hidden lg:block lg:invisible lg:-mb-2">
                {playerBar(boardFlipped ? 'white' : 'black')}
              </div>
            )}
            {flawChessCard}
            <MaiaHumanPanel
              selectedElo={selectedElo}
              perElo={maia.perElo}
              playedSan={playedSan}
              bestSan={bestSan}
              shownSans={shownSans}
              qualityBySan={qualityBySan}
              engineTopLines={engineTopLines}
              onHoverMovesChange={setHoveredQualityMoves}
              isOpponentToMove={isOpponentToMove}
              onPlayMove={playProseMove}
              enabled={maiaEnabled}
              onToggleEnabled={setMaiaEnabled}
            />
            {eloSelector}
          </div>

          {/* Board column ──────────────────────────────────────────────────── */}
          <div className="flex flex-col gap-2 w-full lg:w-[628px] shrink-0">
            {/* Top row: source caps (Maia/SF) over the bars, name/clock aligned to
                the board edges. Free play has no player line — caps show alone. */}
            {boardHeaderRow(
              isGameMode && gameData ? playerBar(boardFlipped ? 'white' : 'black') : null,
            )}

            {/* Board + EvalBar row */}
            {boardRow}

            {/* Bottom player (game mode only), aligned to the board edges. */}
            {isGameMode && gameData && boardFooterRow(playerBar(boardFlipped ? 'black' : 'white'))}

            {/* EvalChart with slider — game mode only, below board (UI-SPEC Layout Contract).
                highlightedPlies (Task 3, desktop only): dims non-matching markers while
                hovering a tags-panel badge/chip. */}
            {evalChartReady && (
              <div data-testid="analysis-eval-chart">
                {evalChart('h-[120px]', tagsHighlightedPlies)}
              </div>
            )}

            {/* Flaw-tags panel — game mode only, directly below the eval chart
                (quick-260702-nm8). withHighlight=true wires its hover state back onto
                the eval chart above (desktop only — mobile's tagsPanel() call omits it). */}
            {tagsPanel(true)}
          </div>

          {/* Side panel: engine + variation tree + controls. Narrower than the board
              column (UAT 260627-mt8 item 1) and stretched to the board column's
              height so the controls bottom-align with the eval-chart slider. */}
          <div className="flex w-full lg:w-[360px] shrink-0 flex-col gap-4 min-w-0">

            {/* Spacer mirroring the board column's top player bar so the engine card
                top aligns with the board top (not the player-bar top). Desktop only
                (lg) where the columns sit side by side; invisible keeps its height.
                -mb-2 trims this column's gap-4 down to the board column's gap-2 so the
                spacer→card gap equals the bar→board gap. (Quick 260628-pcb) */}
            {isGameMode && gameData && (
              <div aria-hidden="true" className="hidden lg:block lg:invisible lg:-mb-2">
                {playerBar(boardFlipped ? 'white' : 'black')}
              </div>
            )}

            {/* Game load error (CLAUDE.md isError branch). */}
            {isGameMode && gameError && (
              <p className="text-sm text-muted-foreground p-2">
                Failed to load game. Something went wrong. Please try again in a moment.
              </p>
            )}

            {/* Engine info + lines in a fixed-height charcoal Card (Quick 260627-r9g
                item 3). The info line is the card header; the body never jumps as the
                engine transitions loading → analyzing → 2 lines. */}
            <Card data-testid="analysis-engine-card">
              {/* Info line in the header: engine toggle + "Stockfish 18, Depth d". */}
              <CardHeader
                size="compact"
                data-testid="analysis-engine-info"
                className="font-normal text-muted-foreground"
              >
                <EngineToggleHeader
                  checked={engineEnabled}
                  onCheckedChange={setEngineEnabled}
                  accent={STOCKFISH_ACCENT}
                  testId="btn-analysis-engine-toggle"
                  ariaLabel="Toggle Stockfish engine"
                  icon={Cpu}
                >
                  {ENGINE_NAME}
                  {engineEnabled && engine.depth > 0 ? `, Depth ${engine.depth}` : ''}
                </EngineToggleHeader>
              </CardHeader>

              {/* min-height (not fixed) — holds a stable floor through the
                  loading → analyzing → 2-lines transition, but grows to fit a line
                  the user expands via its chevron (Quick 260628-shc UAT). */}
              <CardBody className="min-h-[78px] p-2">
                {engineLoading ? (
                  <EngineLinesSkeleton testId="analysis-engine-loading" />
                ) : !engineEnabled ? (
                  <div className="flex h-full items-center px-2 text-sm text-muted-foreground">
                    Engine off
                  </div>
                ) : (
                  // 155 UAT un-merge: the standalone Stockfish top-2 (depth
                  // deepening live) shows independently of the FlawChess Engine.
                  <EngineLines
                    pvLines={engine.pvLines}
                    isAnalyzing={engine.isAnalyzing}
                    startPly={currentPly}
                    baseFen={position}
                    flipped={boardFlipped}
                    onMoveClick={playUciLine}
                  />
                )}
              </CardBody>
            </Card>

            {variationTree('responsive')}

            {/* BoardControls relocated to bottom of right column (chess.com pattern — UI-SPEC). */}
            {boardControls()}
          </div>

        </div>
      </main>
    </div>
  );
}
