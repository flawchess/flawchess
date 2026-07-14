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
 *   ?line= guard: parseAnalysisLineParam degrades a malformed UCI line to its legal
 *     prefix (or empty) — a hand-typed bad URL can't crash the board.
 *   ?fen= guard (T-165-03): parseAnalysisFenParam chess.js-validates the decoded FEN,
 *     degrading a malformed/garbage value to null (free-play start) instead of crashing.
 *   T-140-02a: NaN-guard on ?game_id= / ?ply= params — malformed → null → isGameMode false.
 *   T-140-02b: L-8 guard on mainLine[ply] accesses — out-of-bounds → undefined → no-op.
 *
 * Engine: on by default (D-06); "Loading engine…" shown in eval area while WASM inits;
 *   board stays interactive throughout (SC#3).
 *
 * Modes: ?line=<uci,uci,…> seeds free play with an opening main line (cursor at the end,
 *   navigable back to move 1); no line → bare start. ?fen=<encoded fen> additively seeds
 *   free play with an arbitrary mid-game FEN snapshot as the root (SEED-094 / D-06;
 *   restored alongside ?line=, not a replacement — no navigable history back to move 1).
 *   ?game_id=X&ply=Y loads the full game at ply Y (game mode). Precedence when multiple
 *   params are present: game_id > fen > line. ?orientation=white|black additively orients
 *   the board in ANY free-play sub-mode (171 UAT gap 1); game mode ignores it and always
 *   orients from gameData.user_color. A manual flip still wins over either (hasAutoFlipped).
 *   The legacy tactic mode (?flaw_ply=, removed Quick 260627-l2z) is gone; clicking a
 *   move-list tactic chip grafts the PV as an in-tree sideline with a depth overlay.
 */

import { useEffect, useMemo, useRef, useState } from 'react';
import type { CSSProperties, ReactNode, RefObject } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Chess } from 'chess.js';
import {
  ArrowLeftRight,
  ChessKnight,
  Cpu,
  type LucideIcon,
  Tag,
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
import {
  parseAnalysisLineParam,
  parseAnalysisFenParam,
  parseAnalysisOrientationParam,
} from '@/lib/analysisUrl';
import { toDisplayDepthForOrientation } from '@/lib/tacticDepth';
import { buildPvArrow } from '@/lib/tacticArrows';
import { EvalBar } from '@/components/analysis/EvalBar';
import { EngineLines, EngineLinesSkeleton, LINES_MIN_HEIGHT, MAX_LINES as SF_MAX_LINES } from '@/components/analysis/EngineLines';
import { FlawChessEngineLines, MAX_LINES as FC_MAX_LINES } from '@/components/analysis/FlawChessEngineLines';
import { FlawChessAgreementVerdict } from '@/components/analysis/FlawChessAgreementVerdict';
import { Card, CardHeader, CardBody } from '@/components/ui/card';
import { Switch } from '@/components/ui/switch';
import { InfoPopover } from '@/components/ui/info-popover';
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
import { BOARD_MAX_WIDTH, computeBoardSize } from '@/components/board/boardSize';
import { BoardControls } from '@/components/board/BoardControls';
import { PlayerBar } from '@/components/board/PlayerBar';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { uciToSquares, sanToUci } from '@/lib/sanToSquares';
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
import { sideToMoveFromFen, terminalPositionEval, evalToExpectedScore } from '@/lib/liveFlaw';
import type { NodeId, MoveNode } from '@/hooks/useAnalysisBoard';
import type { MoveCurvePoint } from '@/hooks/useMaiaEngine';
import { buildEvalLookup, getByUci, getBySan, resolveReconciledBest, rankReconciledCandidates } from '@/lib/engineEvalLookup';
import type { RankedLine } from '@/lib/engine/types';
import type { PvLine } from '@/hooks/uciParser';
import { classifyGem, summarizeForGem, GEM_MAIA_MAX_PROB } from '@/lib/gemMove';

// ─── Constants ────────────────────────────────────────────────────────────────

const STARTING_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';

/** Engine label shown in the engine info line — the bundled Stockfish 18 WASM. */
const ENGINE_NAME = 'Stockfish 18';

/** Cap on the per-session live engine-eval cache (FEN → completed eval), item 4. */
const LIVE_EVAL_CACHE_MAX = 256;

/** Synthetic eval-bar depth for a terminal (checkmate/draw) position — clears EvalBar's
 *  mate-display gate (depth >= 8) so a decisive terminal eval fills the bar (Quick 260709-j3k). */
const TERMINAL_EVAL_DEPTH = 99;

/** Below this width the page renders its mobile takeover layout (matches the shell's
 *  `sm` breakpoint where the app swaps to mobile chrome). */
const MOBILE_BREAKPOINT_PX = 640;

/** Horizontal space the two flanking eval bars + their `gap-2` gutters consume in the
 *  desktop board row: 2×(w-5 bar = 20px) + 2×(gap-2 = 8px). Subtracted from the stage's
 *  measured width so the board is sized to the space that actually remains beside the
 *  bars (Phase 161 UAT: bars hug the board, board never clips). */
const BOARD_EVAL_BARS_ALLOWANCE_PX = 56;

/** The board's height budget only binds in the locked desktop layout, i.e. at/above the
 *  desk3col width breakpoint AND at/above the `short` height-unlock threshold. Both mirror
 *  the CSS tokens in index.css (`--breakpoint-desk3col: 1200px`, `short` = max-height
 *  559.98px). Outside that band the page scrolls, so the board is width-driven. */
const BOARD_WIDTH_LOCK_MIN_PX = 1200;
const BOARD_HEIGHT_LOCK_MIN_PX = 560;

/** Fixed width (px) of each side-panel grid track. Mirrors the `360px` literals in the
 *  `desk3col:grid-cols-[360px_1fr_360px]` template and `desk3col:w-[360px]` columns below. */
const SIDE_COLUMN_WIDTH_PX = 360;
/** Gutter (px) between the three desktop columns — mirrors the grid's `gap-4`. */
const DESKTOP_GRID_GAP_PX = 16;
/** Per-side horizontal slack (px) left between the board group and its center track. The
 *  board group is sized this much narrower than the track so it centers with breathing room
 *  on each side, into which the EvalChart slider's ±8px thumb overhang (EvalChart.tsx: the
 *  `calc(100% + 16px)` / `-8px` marginLeft slider) lands — otherwise the stage's
 *  overflow-x-hidden clips the thumb at the min/max position (Phase 161 UAT). Also widens the
 *  visible column gap a touch, which was the paired request. */
const EVAL_SLIDER_SLACK_PX = 12;
/** Max width of the desktop 3-column grid: two side panels + two gutters + the board group
 *  at its ceiling (board max + flanking eval bars + the two slider-slack margins). Past this
 *  the grid stops stretching and centers itself, so extra viewport width falls to the window
 *  margins instead of inflating the fluid center track and pulling the side panels away from
 *  the board (Phase 161 UAT). */
const DESKTOP_GRID_MAX_WIDTH_PX =
  SIDE_COLUMN_WIDTH_PX * 2 +
  DESKTOP_GRID_GAP_PX * 2 +
  BOARD_MAX_WIDTH +
  BOARD_EVAL_BARS_ALLOWANCE_PX +
  EVAL_SLIDER_SLACK_PX * 2;

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

/**
 * Header info tooltip for the FlawChess Engine card — a plain-language, three-paragraph
 * explanation of what the engine does and why it differs from a normal engine. Sourced
 * from docs/flawchess-engine-explained-2026-07-06.md (§1, §9), kept non-technical
 * (no "expectimax"/"MCTS" jargon in user-facing copy).
 */
function FlawChessInfoTooltip() {
  return (
    <InfoPopover ariaLabel="About the FlawChess Engine" testId="flawchess-info-popover">
      <div className="max-w-xs space-y-2">
        <p>
          Stockfish shows the objectively best move, assuming perfect play. The FlawChess
          Engine instead favors moves you can realistically pull off: ones that are easier
          for a player at your level to find (along with their follow-ups), and that pay off
          against an opponent who defends imperfectly, the way real players do.
        </p>
        <p>
          It blends Stockfish's objective quality with Maia's model of how humans at a given
          rating really play, treating both sides as fallible. So it can rank a trap above
          the textbook best move, showing both numbers: "objectively +3.0, but practically
          +0.9 for you."
        </p>
      </div>
    </InfoPopover>
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
 * ROUTE-02: ?line= seeds a free-play opening main line; empty/malformed → standard start.
 * ROUTE-04 (Phase 140): ?game_id=&ply= enters game mode (full game at initial ply).
 * ?fen= (SEED-094 / D-06): additively seeds a free-play mid-game FEN snapshot root;
 *   precedence game_id > fen > line when multiple params are present.
 */
export default function Analysis() {
  const [searchParams] = useSearchParams();

  // Free-play entry point: the opening line to seed as the board's main line,
  // carried as a `?line=` param of comma-separated UCI moves from the standard
  // start (replaces the old `?fen=` snapshot — a move list lets the user step
  // all the way back to move 1). parseAnalysisLineParam degrades a malformed or
  // hand-typed value to its legal prefix, so bad input can't crash the board —
  // the same defensive posture the old FEN guard (T-138-01) had.
  const lineParam = searchParams.get('line');
  const lineSans = useMemo(() => parseAnalysisLineParam(lineParam), [lineParam]);

  // Additive `?fen=` snapshot entry point (SEED-094 / D-06): seeds an arbitrary
  // mid-game FEN (e.g. a gem-ELO calibration harness row) as a free-play root
  // with no navigable history. parseAnalysisFenParam degrades a malformed or
  // hand-typed value to null (T-165-03), so a bad URL can't crash the board.
  // Precedence when both ?fen= and ?line= are present: fen wins (see the
  // ?line= seeding effect's `rootFenSeed === null` guard below).
  const fenParam = searchParams.get('fen');
  const rootFenSeed = useMemo(() => parseAnalysisFenParam(fenParam), [fenParam]);

  // Free-play orientation entry point (171 UAT gap 1): `?orientation=white|black`
  // orients the board when opened from e.g. a finished bot game. Before this,
  // free play had no orientation input at all — a bot game played as Black
  // opened white-side-up. parseAnalysisOrientationParam degrades a malformed or
  // hand-typed value to null (T-171-08-01/02), matching the fen/line guards above.
  const orientationParam = searchParams.get('orientation');
  const urlOrientation = useMemo(
    () => parseAnalysisOrientationParam(orientationParam),
    [orientationParam]
  );

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
  } = useAnalysisBoard(STARTING_FEN);

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
  const { selectedElo, setSelectedElo, defaultElo, resetToDefault } = useMaiaEloDefault({
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

  // Orient the board to the player's color once (item 5; 171 UAT gap 1). ONE
  // orientation source for BOTH modes: game mode learns the player's colour
  // from the backend (gameData.user_color), free play learns it from the URL
  // (?orientation=). Before 171-08 free play had NO orientation input at all,
  // so a bot game played as Black opened white-side-up. Black games/lines open
  // flipped; manual flips afterward win permanently (hasAutoFlipped guard).
  const autoOrientation = isGameMode ? (gameData?.user_color ?? null) : urlOrientation;

  useEffect(() => {
    if (autoOrientation === null || hasAutoFlipped.current) return;
    hasAutoFlipped.current = true;
    setBoardFlipped(autoOrientation === 'black');
  }, [autoOrientation]);

  // Game mode: seed the board once when game data arrives (L-1: never call from chip click).
  useEffect(() => {
    if (!isGameMode || gameData?.moves == null || hasLoadedMainLine.current) return;
    hasLoadedMainLine.current = true;
    loadMainLine(gameData.moves, STARTING_FEN);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [gameData?.moves, isGameMode]);

  // Free play: seed the opening main line from the ?line= param once. The cursor
  // lands at the end of the line (loadMainLine's default), and the user can step
  // back to move 1 through the variation tree. hasLoadedMainLine is shared with
  // game mode and the ?fen= effect below — a page is exactly one of the three,
  // never more. `rootFenSeed === null` makes precedence explicit (game_id > fen >
  // line): when both ?fen= and ?line= are present, fen wins (RESEARCH Landmine 8 —
  // without this guard, effect ordering alone would decide the winner).
  useEffect(() => {
    if (isGameMode || rootFenSeed !== null || lineSans.length === 0 || hasLoadedMainLine.current)
      return;
    hasLoadedMainLine.current = true;
    loadMainLine(lineSans, STARTING_FEN);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lineSans, isGameMode, rootFenSeed]);

  // Free play: seed an arbitrary mid-game FEN snapshot from the ?fen= param once
  // (SEED-094 / D-06, additive alongside ?line=). Empty sans + the parsed FEN as
  // root seeds a free-play root at that exact position — no new hook method
  // needed. hasLoadedMainLine is shared with the other seeding effects above.
  useEffect(() => {
    if (isGameMode || rootFenSeed === null || hasLoadedMainLine.current) return;
    hasLoadedMainLine.current = true;
    loadMainLine([], rootFenSeed);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rootFenSeed, isGameMode]);

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

  // Phase 162 (SEED-090 D-02/D-09): the free run has "committed" a bestmove for
  // the current position once it has at least one PV line and is no longer
  // mid-search. `pvLines` is cleared to `[]` on every FEN change and
  // `isAnalyzing` flips false only on a non-stale bestmove (useStockfishEngine.ts),
  // so this pairing never reads a stale prior-position PV as committed.
  const freeRunCommitted = engine.pvLines.length > 0 && !engine.isAnalyzing;

  // Phase 158 (SEED-087 SC2, RESEARCH Pitfall 4) / Phase 162 (SEED-090 D-02/D-09):
  // the deduplicated, sorted union of the Maia chart's shownSans, the FC card's
  // displayed SANs, and — once the free run has committed a bestmove for this
  // position — the free run's own top-2 root SANs. This closes the "no
  // uncovered displayed move" gap: the grading union now contains everything
  // the Stockfish card shows, not just what Maia/FlawChess independently
  // surface. Sorted + deduped via the SAME single `Array.from(new
  // Set(...)).sort()` (mirroring the grading hook's own candidatesKey pattern)
  // so a re-throttle of the SAME top moves produces the same array and does
  // not re-trigger the search.
  const unionSans = useMemo(() => {
    const maiaSans = maiaEnabled ? shownSans : [];
    const fcSans = flawChessEnabled ? flawChessDisplayedSans : [];
    const freeRunSans: string[] = [];
    if (freeRunCommitted) {
      const san0 = bestSanFromPv(position, engine.pvLines[0]?.moves[0] ?? null);
      const san1 = bestSanFromPv(position, engine.pvLines[1]?.moves[0] ?? null);
      if (san0 !== null) freeRunSans.push(san0);
      if (san1 !== null) freeRunSans.push(san1);
    }
    return Array.from(new Set([...maiaSans, ...fcSans, ...freeRunSans])).sort();
  }, [maiaEnabled, shownSans, flawChessEnabled, flawChessDisplayedSans, freeRunCommitted, engine.pvLines, position]);

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

  // Phase 158 (SEED-087 SC1) / Phase 162 (SEED-090 D-01): the single
  // UCI-keyed eval source every displayed Stockfish eval on this page
  // resolves through — the grading run wins by construction (module
  // precedence in buildEvalLookup), so a move graded by both sources shows
  // the deeper, depth-parity grading value; a move graded ONLY by the free
  // run still resolves to the free-run value until grading catches up.
  const evalLookup = useMemo(
    () => buildEvalLookup(engine.pvLines, grading.gradeMap, position),
    [engine.pvLines, grading.gradeMap, position],
  );

  // The grading run's own SAN keyspace converted to UCI (Pitfall 3 — the SAME
  // keyspace `qualityBySan` iterates below, NOT the broader `unionSans`, which
  // only seeds the grading run's search). Hoisted (162 UAT) because BOTH the
  // argmax below and the card's reconciled ranking (`reconciledPvLines`) rank
  // over this exact set — sharing it guarantees card line 1 === argmax.
  const gradedCandidateUcis = useMemo(() => {
    const candidateUcis: string[] = [];
    for (const san of grading.gradeMap.keys()) {
      const uci = sanToUci(position, san);
      if (uci !== null) candidateUcis.push(uci);
    }
    return candidateUcis;
  }, [grading.gradeMap, position]);

  // Tie-break toward the free run's own bestSan (converted to UCI) so a
  // genuine expected-score tie prefers the standalone Stockfish pick — shared
  // by the argmax and the card ranking (162 UAT).
  const reconciledTieBreakUci = useMemo(
    () => (bestSan !== null ? sanToUci(position, bestSan) : null),
    [bestSan, position],
  );

  // Phase 162 (SEED-090 D-03/D-11/D-10): the SINGLE canonical reconciled-best
  // UCI every downstream display consumer threads through instead of
  // re-deriving its own argmax (the Phase 158 anti-pattern this phase exists
  // to kill) — qualityBySan, the arrow, verdict, eval bar, and card all read
  // it. Re-derives fresh every render from `evalLookup` — no pinned-label
  // state (D-10: live argmax per snapshot, never a pin).
  const reconciledBestUci = useMemo(() => {
    // 162-REVIEW WR-01: with Maia off + FlawChess on, the grading union is
    // FC's top-3 only until the free run commits AND the widened union
    // re-grades — in that window the argmax ran over a candidate set that
    // cannot contain Stockfish's actual best, so the verdict/arrow/eval bar
    // could present a non-SF-best FC candidate as "Stockfish's pick" (and the
    // verdict could falsely claim alignment). Treat the argmax as unresolved
    // until the committed free-run best is itself a graded candidate — every
    // consumer already falls back to raw engine.pvLines[0] on null (the
    // existing first-paint path), which gets the move identity right.
    const freeRunBestUci = freeRunCommitted ? (engine.pvLines[0]?.moves[0] ?? null) : null;
    if (freeRunBestUci !== null && !gradedCandidateUcis.includes(freeRunBestUci)) {
      return null;
    }
    return resolveReconciledBest(evalLookup, gradedCandidateUcis, sideToMoveFromFen(position), reconciledTieBreakUci);
  }, [evalLookup, gradedCandidateUcis, position, reconciledTieBreakUci, freeRunCommitted, engine.pvLines]);

  // 162-REVIEW WR-02: the SAN form of the reconciled argmax, hoisted out of
  // qualityBySan so BOTH the chart's Best quality/label designation AND its
  // emphasized (thick) stroke key off the SAME move. Pre-fix the emphasis
  // prop stayed on the raw free-run bestSan, so the chart could thick-stroke
  // one move while coloring/naming a DIFFERENT move Best (the exact
  // mirror-image scenario this phase fixed for the label). Null (no grades
  // yet) — the chart call sites fall back to the raw bestSan.
  const reconciledBestSan = useMemo(
    () => (reconciledBestUci !== null ? bestSanFromPv(position, reconciledBestUci) : null),
    [reconciledBestUci, position],
  );

  // Phase 162 (SEED-090 D-13): a PvLine-shaped object for the reconciled-argmax
  // move, fed to FlawChessAgreementVerdict's `stockfishLine` prop so the
  // verdict's Stockfish side always names the TRUE global reconciled argmax
  // with ITS reconciled eval, never raw `engine.pvLines[0]` (RESEARCH Pitfall
  // 1: this call site bypassed evalLookup entirely pre-162). `moves` carries
  // the resolved grade's own PV when retained (162 UAT), falling back to the
  // bare root move; `depth` is the resolved grade's depth, free-run depth as
  // fallback (cosmetic only — the verdict never renders a PV's depth). null
  // when reconciledBestUci is null (grading not yet landed) — the call site
  // below falls back to `engine.pvLines[0]` so first paint still shows a value.
  const reconciledStockfishLine = useMemo<PvLine | null>(() => {
    if (reconciledBestUci === null) return null;
    const resolved = getByUci(evalLookup, reconciledBestUci);
    return {
      multipv: 1,
      depth: resolved?.depth ?? engine.depth,
      moves: resolved?.pv ?? [reconciledBestUci],
      evalCp: resolved?.evalCp ?? null,
      evalMate: resolved?.evalMate ?? null,
    };
  }, [reconciledBestUci, evalLookup, engine.depth]);

  // Phase 162 (SEED-090 D-08): the off-main-line eval bar's engine-passthrough
  // source (useGameOverlay's enginePassthrough branch) — the reconciled best's
  // eval once grading has landed for this position, else the raw free-run eval
  // (a natural lookup fallback: reconciledBestUci is null pre-grading or when
  // gradingEnabled is false, so no special-casing is needed here). Closes
  // RESEARCH Pitfall 1's second bypass — useGameOverlay's engineEvalCp/Mate/
  // Depth params previously read `engine.evalCp`/`evalMate`/`depth` raw.
  const reconciledBestEval = useMemo(() => {
    const resolved = reconciledBestUci !== null ? getByUci(evalLookup, reconciledBestUci) : null;
    return resolved ?? { evalCp: engine.evalCp, evalMate: engine.evalMate, depth: engine.depth };
  }, [reconciledBestUci, evalLookup, engine.evalCp, engine.evalMate, engine.depth]);

  // Phase 158 (SEED-087 SC1/SC3/SC4, SC5 scope fence): parallel RankedLine-
  // shaped display objects — NEVER the live MCTS-core snapshots themselves —
  // with `objectiveEvalCp`/`objectiveEvalMate` swapped for the reconciled
  // lookup value. Both are pulled from the SAME resolved grade so a forced-mate
  // root candidate surfaces `#-4` on the card + agreement verdict instead of the
  // `…` a null cp alone would print (quick 260709 — the earlier cp-only swap
  // dropped mate).
  const reconciledRankedLines = useMemo<RankedLine[]>(
    () =>
      flawChessEngine.rankedLines.slice(0, FC_MAX_LINES).map((line) => {
        const resolved = getByUci(evalLookup, line.rootMove);
        return {
          ...line,
          objectiveEvalCp: resolved?.evalCp ?? null,
          objectiveEvalMate: resolved?.evalMate ?? null,
        };
      }),
    [flawChessEngine.rankedLines, evalLookup],
  );

  // Phase 162 UAT (supersedes D-04/D-12's card scope): the Stockfish card's
  // lines are the top-2 of the reconciled ranking over the FULL grading union
  // — not the free run's own 2 PVs with swapped evals. This closes the D-12
  // residual edge case UAT flagged: the arrow/verdict/FC card named a
  // reconciled best (a Maia/FC-sourced candidate) that the Stockfish card
  // didn't list. PV move text comes from each grade's retained `pv` (bare
  // root move as fallback for a pre-`pv` cache entry); per-line depth is the
  // grade's own depth. Gated on `reconciledBestUci` (the WR-01 guard) so the
  // card, arrow, and verdict re-source at the same instant; until then the
  // free run's own lines render with reconciled evals, re-sorted by expected
  // score (the pre-UAT D-04 behavior, now purely the placeholder path).
  const reconciledPvLines = useMemo<PvLine[]>(() => {
    const mover = sideToMoveFromFen(position);
    if (reconciledBestUci !== null) {
      const ranked = rankReconciledCandidates(evalLookup, gradedCandidateUcis, mover, reconciledTieBreakUci);
      return ranked.slice(0, SF_MAX_LINES).map(({ uci, grade }, index) => ({
        multipv: index + 1,
        depth: grade.depth,
        moves: grade.pv ?? [uci],
        evalCp: grade.evalCp,
        evalMate: grade.evalMate,
      }));
    }
    const withReconciledEval = engine.pvLines.map((line) => {
      const uci = line.moves[0];
      const resolved = uci !== undefined ? getByUci(evalLookup, uci) : null;
      return resolved !== null ? { ...line, evalCp: resolved.evalCp, evalMate: resolved.evalMate } : line;
    });
    return [...withReconciledEval].sort(
      (a, b) =>
        evalToExpectedScore(b.evalCp, b.evalMate, mover) - evalToExpectedScore(a.evalCp, a.evalMate, mover),
    );
  }, [engine.pvLines, evalLookup, position, reconciledBestUci, gradedCandidateUcis, reconciledTieBreakUci]);

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
    // Phase 162 (SEED-090 D-03): pass the SAN form of the single reconciled
    // argmax — NOT the free run's raw bestSan — so the chart's "Best" label
    // always agrees with the reconciled eval, closing the mirror-image bug
    // where a free-run pin could label a lower-eval move Best. Null (no
    // grades yet) falls back to classifyMoveQuality's own top-scorer.
    // (162-REVIEW WR-02: the SAN is hoisted into reconciledBestSan above so
    // the chart's emphasis stroke shares it.)
    const infoBySan = classifyMoveQuality(reconciledGradeMap, sideToMoveFromFen(position), reconciledBestSan);
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
  }, [evalLookup, grading.gradeMap, position, reconciledBestSan]);

  // Phase 163 (SEED-092): recolors the CURRENT position's reconciled-best candidate
  // as 'gem' when it satisfies classifyGem — feeds ONLY the chart/bar display sites
  // (MaiaHumanPanel below), never positionVerdict/the FlawChess card (those stay on
  // the base qualityBySan; the gem override is a display concern only). Distinct
  // from the gem block below (~liveFlawByNode section): this memo is
  // forward-looking over the CURRENT position's own candidates, while that block
  // classifies the ARRIVAL move that reached the current node against the PARENT
  // position (graded on demand). Stable ref (returns qualityBySan unchanged) when
  // no gem qualifies, so consumers memoized on it don't re-render needlessly.
  const qualityBySanWithGem = useMemo<Map<string, MoveQualityEval>>(() => {
    if (reconciledBestSan === null) return qualityBySan;
    const rung = nearestByElo(maia.perElo, selectedElo);
    const maiaProb = rung?.moveProbabilities[reconciledBestSan] ?? null;
    // Bug fix (163-REVIEW WR-01): verify the summarized argmax IS the move we are
    // about to recolor instead of hard-coding playedIsBest: true. When the
    // summarize argmax diverges from reconciledBestSan (tie-break drift, or a
    // partially graded map), classifyGem would otherwise evaluate the argmax
    // pair's gap while a DIFFERENT move gets painted violet — a false gem.
    // Mirrors the arrival-move path's own `bestSan === playedSan` check (gem
    // block below).
    const { bestSan, bestEs, secondBestEs } = summarizeForGem(
      qualityBySan,
      sideToMoveFromFen(position),
    );
    const isGem = classifyGem({
      maiaProbability: maiaProb,
      playedIsBest: bestSan === reconciledBestSan,
      bestEs,
      secondBestEs,
    });
    if (!isGem) return qualityBySan;
    const bestInfo = qualityBySan.get(reconciledBestSan);
    if (!bestInfo) return qualityBySan;
    const next = new Map(qualityBySan);
    next.set(reconciledBestSan, { ...bestInfo, quality: 'gem' });
    return next;
  }, [qualityBySan, reconciledBestSan, maia.perElo, selectedElo, position]);

  // The FlawChess Engine's top practical pick — its root move's SAN + reconciled
  // white-POV objective eval — shown as the pinned "FlawChess" reference row atop
  // the Maia chart tooltip (quick 260710-e2p). Sourced ONLY from the FlawChess
  // Engine (reconciledRankedLines[0]), NEVER standalone Stockfish: the row is
  // labeled "FlawChess", so pinning Stockfish's objective best there mislabeled it
  // as FlawChess (the two diverge exactly when FlawChess trades objective eval for
  // human findability, e.g. exd6 over Rad1). Empty — which drops the pinned row —
  // when the FlawChess Engine is off or has no ranked line yet, rather than falling
  // back to a mislabeled Stockfish pick. Reconciled objective eval matches the FC
  // card's blue objective aside; the FlawChess source carries mate via the same
  // reconciled lookup (objectiveEvalMate), so a forced-mate root prints "#-N".
  const engineTopLines = useMemo<EngineLine[]>(() => {
    if (!flawChessEnabled) return [];
    const top = reconciledRankedLines[0];
    if (!top) return [];
    const san = bestSanFromPv(position, top.rootMove);
    if (san === null) return [];
    return [{ san, evalCp: top.objectiveEvalCp, evalMate: top.objectiveEvalMate }];
  }, [position, flawChessEnabled, reconciledRankedLines]);

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
  // Phase 162 (SEED-090 D-08): the eval-bar passthrough params (engineEvalCp/
  // Mate/Depth) are now `reconciledBestEval`'s fields, not the raw free-run
  // eval — closes RESEARCH Pitfall 1's second evalLookup bypass. Off the main
  // line, useGameOverlay's own enginePassthrough branch surfaces these
  // unchanged (the hook's internals are untouched — only the caller's source
  // changed); on the main line the precomputed game eval still wins as before.
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
    engineEvalCp: reconciledBestEval.evalCp,
    engineEvalMate: reconciledBestEval.evalMate,
    engineDepth: reconciledBestEval.depth,
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

  // Phase 163 (SEED-092, RESEARCH Pitfall 1): a per-FEN retention cache for the
  // Maia curve, mirroring engineEvalByFen exactly — useMaiaEngine only exposes
  // CURRENT-position data, but gem detection (C1: hard-to-find) needs the PARENT
  // position's Maia curve once the user has navigated to the child. Retained
  // while each position is current; read back below (parentFen-keyed) once it's
  // the parent. Maia is fast and reliably wins the navigation race, so caching it
  // is safe; the Stockfish grade (C2) is instead fetched on demand per node (see
  // the gem block below) rather than cached per FEN, which is what used to race.
  const [maiaCurveByFen, setMaiaCurveByFen] = useState<Map<string, MoveCurvePoint[]>>(
    () => new Map(),
  );
  useEffect(() => {
    if (!maiaEnabled || maia.perElo.length === 0) return;
    // Bug fix (163-REVIEW WR-03): useMaiaEngine clears its result one commit
    // AFTER `position` changes, so on the navigation commit `maia.perElo`
    // still holds the PARENT's curve — writing it under the child's FEN would
    // poison the cache (a rapid two-step navigation then classifies the
    // grandchild's arrival move against the wrong position's policy map).
    // Only cache when the hook says the curve belongs to the shown position.
    if (maia.resultFen !== position) return;
    setMaiaCurveByFen((prev) => {
      const existing = prev.get(position);
      if (existing === maia.perElo) return prev; // unchanged (stable ref) — skip re-render
      const next = new Map(prev);
      next.set(position, maia.perElo);
      if (next.size > LIVE_EVAL_CACHE_MAX) {
        const oldest = next.keys().next().value;
        if (oldest !== undefined) next.delete(oldest);
      }
      return next;
    });
  }, [position, maia.perElo, maia.resultFen, maiaEnabled]);

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

  // Deterministic eval for a terminal (checkmate/draw) displayed position — the live
  // engine reports an ambiguous `mate 0` there, which read as the 0.5 midpoint and
  // graded a mating move as a blunder (Quick 260709-j3k). Drives both the live
  // classification below and the right eval bar.
  const terminalEval = useMemo(() => terminalPositionEval(position), [position]);

  // Game-over state of the shown position, for the FlawChess card's terminal row
  // (quick 260709). terminalPositionEval reports checkmate as a mate score and a
  // draw as cp 0; a terminal root has no legal moves so the engine ranks nothing.
  const flawChessTerminalOutcome: 'checkmate' | 'draw' | null =
    terminalEval == null ? null : terminalEval.mate != null ? 'checkmate' : 'draw';

  const liveFlaw = useLiveMoveFlaw({
    active: liveFlawActive,
    parentFen,
    parentEval,
    // On a checkmate the child position is decisive for the mover, so the mating move
    // reads clean (green) instead of a blunder; a genuine stalemate-when-winning still
    // flags because its cp-0 child correctly drops the mover's expected score.
    childEvalCp: terminalEval ? terminalEval.cp : engine.evalCp,
    childEvalMate: terminalEval ? terminalEval.mate : engine.evalMate,
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

  // Phase 163 (SEED-092 D-03/D-04/D-05/D-06): gem-move detection. Broader gate than
  // liveFlawActive — D-05 requires coverage on EVERY visited node, mainline AND free
  // variations, both colors — so this deliberately has NO isGameMode/isOnMainLine/
  // isOnPvLine exclusion.
  const gemActive = currentNodeId !== null && parentFen !== null;

  // The numbers behind a detected gem, surfaced in the move-list gem popover — the
  // ELO rung it was found at, the Maia probability of the move at that rung, and
  // whether the OPPONENT (not the user) played it (game mode only; switches the
  // popover heading).
  type GemDetail = { maiaProbability: number; elo: number; byOpponent: boolean };

  // Sticky per-node gem RESOLUTION. `has(nodeId)` means the node's arrival move has
  // been graded and resolved — the gate that stops us re-grading it. A non-null
  // value is a confirmed gem (shows the badge, carries its popover detail); an
  // explicit `null` is a graded-and-rejected node. Populated ONLY by the on-demand
  // parent-grade effect below — NOT a per-FEN grade cache.
  //
  // This replaces the old gradeSummaryByFen race: the C2 grade was cached per FEN
  // only when the parent's grading pass COMPLETED while the parent was the current
  // position. Play the move before that finished and the parent — no longer current
  // — was never graded again, so the gem never showed (the reported bug). Now the
  // grade is fetched on demand for the node, so it appears regardless of timing.
  const [gemByNode, setGemByNode] = useState<Map<NodeId, GemDetail | null>>(() => new Map());

  // C1 (hard to find): the arrival move into the current node and its Maia
  // probability at the PARENT rung, read from the reliably-cached parent Maia curve
  // (Maia is fast and wins the navigation race). Cheap, so it gates whether we
  // bother spinning up a Stockfish pass on the parent at all — gems are rare by
  // construction, so this passes infrequently. Re-reads at the current selectedElo
  // so an ELO-slider change can newly qualify a move (additive; never un-resolves).
  const gemC1 = useMemo<{ playedSan: string; maiaProbability: number } | null>(() => {
    if (!gemActive || currentNodeId === null || parentFen === null) return null;
    const playedSan = nodes.get(currentNodeId)?.san ?? null;
    if (playedSan === null) return null;
    const parentCurve = maiaCurveByFen.get(parentFen);
    if (parentCurve === undefined) return null; // parent Maia not cached yet — wait
    const maiaProbability = nearestByElo(parentCurve, selectedElo)?.moveProbabilities[playedSan] ?? null;
    if (maiaProbability === null || maiaProbability > GEM_MAIA_MAX_PROB) return null;
    return { playedSan, maiaProbability };
  }, [gemActive, currentNodeId, parentFen, nodes, maiaCurveByFen, selectedElo]);

  // Grade the PARENT to confirm C2 (only good move) only when the arrival move is a
  // rare gem candidate (C1 passed) AND this node is not already resolved.
  const needParentGemGrade =
    gemC1 !== null && currentNodeId !== null && !gemByNode.has(currentNodeId);

  // The parent's candidate SANs to grade — the same Maia-mass selection the chart
  // uses, plus the played move (always included). No free-run contribution (the
  // free engine is on the child), so C2 is judged over Maia's candidate set.
  const parentGemCandidateSans = useMemo<string[]>(() => {
    if (!needParentGemGrade || parentFen === null || gemC1 === null) return [];
    const parentCurve = maiaCurveByFen.get(parentFen);
    if (parentCurve === undefined) return [];
    return selectCandidatesByMass(parentCurve, selectedElo, gemC1.playedSan, null);
  }, [needParentGemGrade, parentFen, maiaCurveByFen, selectedElo, gemC1]);

  // On-demand SECOND grading worker, pinned to the parent FEN only while a gem
  // candidate needs confirming (absent/idle otherwise — `enabled` gates worker
  // creation). Fully isolated from the shared `grading` worker so the current
  // position's chart / FC card / Stockfish reconciliation are never disturbed
  // while we grade the parent.
  const gemGrading = useStockfishGradingEngine({
    fen: needParentGemGrade ? parentFen : null,
    candidateSans: parentGemCandidateSans,
    enabled: gradingEnabled && needParentGemGrade,
  });

  // When the parent grade completes, run C2 and RESOLVE the node: stamp the gem
  // detail on a pass, or an explicit null on a miss (so it is never re-graded).
  useEffect(() => {
    if (!needParentGemGrade || currentNodeId === null || parentFen === null) return;
    // Wait for a COMPLETE parent pass keyed to the parent FEN (gradeMapFen guards
    // against the one-commit-late clear, mirroring the Maia cache's WR-03 guard).
    if (gemGrading.gradeMapFen !== parentFen || gemGrading.isGrading) return;
    if (gemGrading.gradeMap.size === 0) return;

    const gradeBySan = new Map<string, { evalCp: number | null; evalMate: number | null }>();
    for (const [san, g] of gemGrading.gradeMap) {
      gradeBySan.set(san, { evalCp: g.evalCp, evalMate: g.evalMate });
    }
    const mover = sideToMoveFromFen(parentFen);
    const { bestSan, bestEs, secondBestEs } = summarizeForGem(gradeBySan, mover);
    const playedSan = nodes.get(currentNodeId)?.san ?? null;
    const parentCurve = maiaCurveByFen.get(parentFen);
    const maiaProbability =
      playedSan !== null
        ? nearestByElo(parentCurve ?? [], selectedElo)?.moveProbabilities[playedSan] ?? null
        : null;
    const isGem = classifyGem({
      maiaProbability,
      playedIsBest: bestSan === playedSan,
      bestEs,
      secondBestEs,
    });
    // The mover made the move; in game mode it's the opponent when it isn't the
    // user's color. Free play has no opponent, so this stays false there.
    const byOpponent =
      isGameMode && gameData?.user_color != null && mover !== gameData.user_color;
    // classifyGem === true guarantees maiaProbability is non-null (it rejects a
    // null probability), so the detail's number is safe.
    const detail: GemDetail | null =
      isGem && maiaProbability !== null ? { maiaProbability, elo: selectedElo, byOpponent } : null;
    setGemByNode((prev) => {
      if (prev.has(currentNodeId)) return prev; // already resolved — first wins
      const next = new Map(prev);
      next.set(currentNodeId, detail);
      if (next.size > LIVE_EVAL_CACHE_MAX) {
        const oldest = next.keys().next().value;
        if (oldest !== undefined) next.delete(oldest);
      }
      return next;
    });
  }, [
    needParentGemGrade,
    currentNodeId,
    parentFen,
    gemGrading.gradeMap,
    gemGrading.gradeMapFen,
    gemGrading.isGrading,
    nodes,
    maiaCurveByFen,
    selectedElo,
    isGameMode,
    gameData?.user_color,
  ]);

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
    const hasGemWork = gemByNode.size > 0;
    if (liveFlawByNode.size === 0 && !showCurrentLive && !hasGemWork) return flawMarkerByNodeId;

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

    // Phase 163 (SEED-092 D-05/D-06): fold gemByNode's sticky entries into the SAME
    // map — unlike addLive above, this has NO mainLineSet exclusion. gemActive covers
    // mainline AND free-variation nodes (D-05), and moveListMarkers is the ONLY map
    // VariationTree reads, so excluding mainline ids here would silently drop mainline
    // gem badges from the move list. Merging onto a severity-free entry (e.g. a
    // tactic-chips-only game entry) keeps its chips and adds the gem.
    const addGem = (nodeId: NodeId, detail: GemDetail): void => {
      if (!nodes.has(nodeId)) return; // node deleted (e.g. a collapsed PV fork)
      const existing = merged.get(nodeId);
      if (existing?.gem) return; // already flagged
      // Bug fix (163-REVIEW WR-05, move-list side): a backend/live severity entry on
      // the same node wins — one move never renders two badges. "Mutually exclusive
      // by construction" only holds within the live pipeline; a BACKEND severity
      // (server Stockfish) and the live WASM gem can legitimately disagree.
      if (existing?.severity != null) return;
      merged.set(nodeId, {
        ...(existing ?? {
          missedMotif: null,
          allowedMotif: null,
          missedDepth: null,
          allowedDepth: null,
          ply: -1,
        }),
        gem: true,
        // The detection-time rung + probability + who played it, for the
        // move-list gem popover.
        gemMaiaProbability: detail.maiaProbability,
        gemElo: detail.elo,
        gemByOpponent: detail.byOpponent,
      });
    };
    // Sticky resolutions carry their own detection detail (D-06). Skip null
    // entries — those are graded-and-rejected nodes (kept only to prevent
    // re-grading), not gems.
    for (const [nodeId, detail] of gemByNode) {
      if (detail !== null) addGem(nodeId, detail);
    }

    return merged;
  }, [flawMarkerByNodeId, liveFlaw, currentNodeId, liveFlawByNode, mainLine, nodes, gemByNode]);

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
        // Phase 162 (SEED-090 D-07/D-12): the green SF arrow follows the TRUE
        // global reconciled argmax, not the free run's own pvLines[i] — this
        // may point at a move outside the Stockfish card's 2 displayed lines
        // (accepted edge case, D-12). Falls back to the free run's own top
        // line until grading has produced a reconciled best (first paint, no
        // regression) — reuses the single reconciledBestUci memo, never a
        // fresh argmax loop (RESEARCH Anti-Pattern).
        const sfUci = reconciledBestUci ?? engine.pvLines[i]?.moves[0] ?? null;
        const sfSquares = uciToSquares(sfUci);
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
  }, [flawChessEnabled, flawChessEngine.rankedLines, engineEnabled, engine.pvLines, reconciledBestUci]);

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
        setGemByNode(new Map()); // Phase 163: re-derives instantly from the FEN caches on revisit
        // T-140-02b: L-8 guard on initialPly — out-of-bounds is a no-op.
        const nodeId = mainLine[initialPly ?? 0];
        if (nodeId !== undefined) goToNode(nodeId);
      }
    : () => {
        setLiveFlawByNode(new Map());
        setGemByNode(new Map());
        if (mainLine.length > 0) {
          // Opening-line free play (?line=): keep the seeded opening as the main
          // line, drop any exploration sidelines, and return to the end of the
          // line (the entry point) — mirrors game mode's clear-and-return reset.
          clearAllSidelines();
          const endId = mainLine[mainLine.length - 1];
          if (endId !== undefined) goToNode(endId);
        } else {
          // Bare free play (no line): wipe back to the empty start position.
          loadMainLine([], rootFen);
        }
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
  // A terminal position pins the left bar to the deterministic result too: neither the
  // FlawChess nor the Maia engine emits a ranked line for a checkmate (no legal move),
  // so their fraction fell back to 0.5 while the Stockfish bar already read decisive
  // (Quick 260709-j3k follow-up). mate > 0 = White wins (full white), < 0 = Black wins
  // (full black), draw = midpoint.
  const terminalWhiteFraction =
    terminalEval == null
      ? null
      : terminalEval.mate != null
        ? terminalEval.mate > 0
          ? 1
          : 0
        : 0.5;
  const leftEvalBarWhiteFraction =
    terminalWhiteFraction ?? (flawChessEnabled ? fcWhiteFraction : maiaWhiteFraction);
  const leftEvalBarAccent = flawChessEnabled ? FLAWCHESS_ENGINE_ACCENT : MAIA_ACCENT;
  const leftEvalBarTestId = flawChessEnabled ? 'analysis-flawchess-eval-bar' : 'analysis-maia-eval-bar';
  // The right bar is labeled "SF" (Stockfish): the real standalone Stockfish eval
  // whenever its switch is on, going neutral when the user turns Stockfish off
  // (`!engineEnabled`). `null`/`0` reads as the sigmoid midpoint in EvalBar's
  // computeWhiteFraction (no data → 0.5).
  // A terminal position (checkmate/draw) overrides the engine passthrough with the
  // deterministic eval so the bar fills to the winner (or sits at the midpoint on a
  // draw) instead of snapping to `mate 0` at ~50% (Quick 260709-j3k). Synthetic depth
  // clears EvalBar's mate-display gate.
  const rightEvalBarEvalCp = engineEnabled
    ? terminalEval
      ? terminalEval.cp
      : gameOverlay.evalCp
    : null;
  const rightEvalBarEvalMate = engineEnabled
    ? terminalEval
      ? terminalEval.mate
      : gameOverlay.evalMate
    : null;
  const rightEvalBarDepth = engineEnabled
    ? terminalEval
      ? TERMINAL_EVAL_DEPTH
      : gameOverlay.evalDepth
    : 0;

  // Desktop board sizing (Phase 161 UAT): the board + eval bars are measured and sized
  // in JS rather than via flexbox, so the bars are exactly as tall as the board and hug
  // its edges, and the board shrinks (never clips) when width/height is tight. We measure
  // the STAGE (a full-width, flex-height box that is NOT sized by the board itself, so no
  // circular/zero-height bootstrap), subtract the eval-bar allowance, and clamp with the
  // same computeBoardSize helper ChessBoard uses. The height budget only binds inside the
  // locked band; outside it the page scrolls and the board is width-driven.
  const boardStageRef = useRef<HTMLDivElement>(null);
  const [boardWidth, setBoardWidth] = useState(0);
  useEffect(() => {
    const stage = boardStageRef.current;
    if (!stage) return; // mobile tree: the desktop stage is not mounted; boardWidth is unused there.
    const measure = (): void => {
      const el = boardStageRef.current;
      if (!el) return;
      const locked =
        window.matchMedia(`(min-width:${BOARD_WIDTH_LOCK_MIN_PX}px)`).matches &&
        window.matchMedia(`(min-height:${BOARD_HEIGHT_LOCK_MIN_PX}px)`).matches;
      // Non-board "chrome" (source caps + player rows + eval chart + gaps) shares the board's
      // vertical budget, so subtract it. Derived from the DOM as (group height − board box
      // height) rather than the boardWidth STATE, so it carries no stale closure and settles
      // in one pass: group height = chrome + board box height, so the difference is exactly
      // the chrome regardless of the current board size.
      const group = el.firstElementChild;
      const boardBoxHeight = containerRef.current?.clientHeight ?? 0;
      const chrome = group ? Math.max(0, group.clientHeight - boardBoxHeight) : 0;
      // Reserve the bars allowance AND both slider-slack margins so the board group ends up
      // narrower than its track and centers with EVAL_SLIDER_SLACK_PX of breathing room on
      // each side — room the eval-chart slider's thumb overhang needs to avoid being clipped.
      const widthBudget = el.clientWidth - BOARD_EVAL_BARS_ALLOWANCE_PX - EVAL_SLIDER_SLACK_PX * 2;
      const heightBudget = locked ? el.clientHeight - chrome : Infinity;
      setBoardWidth(computeBoardSize(widthBudget, heightBudget, BOARD_MAX_WIDTH));
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(stage);
    // A viewport resize that crosses the width/height lock thresholds also flips the
    // `locked` branch above; observe window resize too so those crossings recompute even
    // if the stage's own box happens not to change on the same frame.
    window.addEventListener('resize', measure);
    return () => {
      observer.disconnect();
      window.removeEventListener('resize', measure);
    };
    // containerRef is a stable ref object; listed to satisfy exhaustive-deps without churn.
    // isGameMode/gameData: the board-group chrome (player bars + eval chart) mounts
    // ASYNChronously once the game loads, but the ResizeObserver watches the fixed-size
    // stage box and never fires on that inner growth — so without a re-measure here the
    // board stays sized for the pre-load (chrome-less) group and the now-taller group
    // overflows the stage, producing a spurious vertical scrollbar (Phase 161 UAT). Re-run
    // on those transitions so the height budget re-subtracts the real chrome and refits.
  }, [isMobile, containerRef, isGameMode, gameData]);

  // Left eval bar — FlawChess Engine (brown) when enabled (D-04 precedence), else Maia
  // (violet, D-01/D-05, SURF-04). Single expected-score fill: both sources bypass the cp
  // sigmoid entirely via whiteFraction. 0.5 fallback while neither source has a result yet.
  // Bug fix (151.1 UAT): Maia's WDL is from the side-to-MOVE's perspective (the board is
  // mirrored to the mover's POV when Black is to move — see maiaEncoding.encodeBoard), so
  // expectedScore is the mover's expected score. The bar's whiteFraction must be
  // WHITE-relative to match the Stockfish bar and the board orientation, so invert it
  // whenever Black is to move (see fcWhiteFraction above).
  const leftEvalBarNode = (className?: string) => (
    <EvalBar
      evalCp={null}
      evalMate={null}
      depth={0}
      whiteFraction={leftEvalBarWhiteFraction}
      flipped={boardFlipped}
      accentColor={leftEvalBarAccent}
      testId={leftEvalBarTestId}
      className={className}
    />
  );

  // Right eval bar: precomputed eval in game mode (immediate), live engine otherwise —
  // useGameOverlay passes the engine through when disabled. D-04 handoff: while the
  // FlawChess Engine runs, this bar is fed its top line's own objective root eval (never a
  // mate — ±MATE_CP_EQUIVALENT reads as near-mate on the sigmoid) rather than a second live
  // Stockfish search on the same position (POOL-04).
  const rightEvalBarNode = (className?: string) => (
    <EvalBar
      evalCp={rightEvalBarEvalCp}
      evalMate={rightEvalBarEvalMate}
      depth={rightEvalBarDepth}
      flipped={boardFlipped}
      accentColor={STOCKFISH_ACCENT}
      className={className}
    />
  );

  // Phase 163 (SEED-092 D-06): the board's own gem badge — appended to whichever
  // base squareMarkers source (precomputed game overlay or live free-move
  // classification) is currently active. Reads the sticky per-node resolution
  // (gemByNode) for the CURRENT node, the SAME source the move list uses — so the
  // two can never disagree, and the badge shows the moment the on-demand parent
  // grade resolves rather than depending on grade-timing at navigation. A `null`
  // value is a graded-and-rejected node (no badge). Note (behavior change from the
  // old live D-03 read): the badge is now sticky at its detection ELO rather than
  // re-evaluating C1 on every ELO-slider tick — it matches the move list, and the
  // popover already discloses the detection ELO. An ELO change can still newly
  // qualify an as-yet-unresolved node (gemC1 above re-reads at selectedElo).
  const boardSquareMarkers = useMemo(() => {
    const base =
      gameOverlay.squareMarkers.length > 0 ? gameOverlay.squareMarkers : liveFlaw.squareMarkers;
    const gemHere = currentNodeId !== null ? gemByNode.get(currentNodeId) : undefined;
    // Bug fix (163-REVIEW WR-05): in game mode the base can carry a BACKEND-
    // precomputed severity marker on lastMove.to (server-side Stockfish), while
    // the gem's C2 comes from the frontend WASM pass — the two evals diverge by
    // design (documented eval non-determinism), so "mutually exclusive by
    // construction" doesn't hold across pipelines. One square never renders two
    // badges: an existing severity marker wins, the gem yields.
    if (
      gemHere != null && // non-null resolution = confirmed gem (null = graded, not a gem)
      lastMove != null &&
      !base.some((m) => m.square === lastMove.to && m.severity != null)
    ) {
      return [...base, { square: lastMove.to, gem: true }];
    }
    return base;
  }, [gameOverlay.squareMarkers, liveFlaw.squareMarkers, gemByNode, currentNodeId, lastMove]);

  // The single react-chessboard instance / `analysis-board` focus target. Shared by the
  // desktop stage and the mobile row (only one renders at a time via isMobile), so the
  // board mounts exactly once either way. `heightRef` is supplied on mobile (the row's own
  // wrapper drives height-aware sizing); the desktop stage sizes the wrapping box directly.
  const chessBoardNode = (heightRef?: RefObject<HTMLElement | null>) => (
    <ChessBoard
      id="analysis-board"
      position={position}
      onPieceDrop={makeMove}
      lastMove={lastMove}
      // Precomputed overlay (main line) wins; else the live free-move classification (item
      // 4), which also covers free-play mode. Default green (MOVE_HIGHLIGHT_GOOD): a played
      // move is assumed OK until the engine proves otherwise, so engine-line (PV) moves and
      // not-yet-graded moves read green instead of the shared yellow fallback. The engine
      // still overrides to red/orange on a blunder/mistake (and yellow on an inaccuracy).
      lastMoveColor={
        gameOverlay.lastMoveHighlightColor ??
        liveFlaw.lastMoveHighlightColor ??
        MOVE_HIGHLIGHT_GOOD
      }
      flipped={boardFlipped}
      arrows={boardArrows}
      squareMarkers={boardSquareMarkers}
      maxWidth={BOARD_MAX_WIDTH}
      heightRef={heightRef}
    />
  );

  // Mobile board row — purely width-driven square that fills the takeover width. No
  // heightRef: the mobile page scrolls (no viewport height lock), so the board sizes to its
  // flex-1 container width alone. The bars (items-stretch) match the board's height and the
  // board fills its container, so the bars hug it. Desktop uses the JS-sized stage below.
  const boardRow = (
    <div className="flex flex-row items-stretch gap-2">
      {leftEvalBarNode()}
      <div ref={containerRef} data-testid="analysis-board" tabIndex={0} className="min-w-0 flex-1">
        {chessBoardNode()}
      </div>
      {rightEvalBarNode()}
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
      // deleteSubtree wired unconditionally: the free-move sideline × delete must
      // work in free-play mode too. Previously gated on isGameMode, so in free play
      // the × rendered (free-move blocks always show it) but its handler was
      // undefined and clicking did nothing. deleteSubtree is always safe — it
      // recovers currentNodeId to the fork parent when the current node is deleted.
      onDeleteLine={deleteSubtree}
    />
  );

  // Board controls — shared. The desktop panel now sits in the move-list card's darker
  // footer band (flat, compact sm icons evenly spread); the mobile footer passes flat with
  // no size so the buttons fill the width like the main nav (Quick 260628-dgv).
  const boardControls = (flat = false, size?: 'sm' | 'md' | 'lg') => (
    <BoardControls
      onBack={goBack}
      onForward={goForward}
      onReset={handleReset}
      onFlip={() => setBoardFlipped((f) => !f)}
      canGoBack={currentNodeId !== null}
      canReset={canReset}
      canGoForward={canGoForward}
      flat={flat}
      size={size}
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

  // Desktop board column (Phase 161 UAT). The outer div is the measured "stage" (see the
  // boardStageRef effect): a full-width, viewport-height-locked box. Inside sits ONE tight,
  // centered group — source caps + top player, the board flanked by its two eval bars, the
  // bottom player, and the eval chart. The board is JS-sized (computeBoardSize) so:
  //   • the eval bars are exactly as tall as the board and sit flush to its edges (gap-2),
  //   • the player rows and chart stay directly adjacent to the board (no flex-1 gap), and
  //   • the board shrinks to fit as width/height tighten until it hits the board's floor
  //     (D-08), past which the overflowing bottom (eval chart, then board) is CLIPPED, not
  //     scrolled — a middle-column scrollbar is never acceptable (Phase 161 UAT).
  // The group's width follows the board+bars row (maxWidth = boardWidth + bars allowance),
  // so the caps, player rows and chart all align to the board edges. `w-5` fixes each bar's
  // width; `h-full` makes it fill the boardWidth-tall wrapper.
  const desktopBoardStage = (
    <div
      ref={boardStageRef}
      // overflow-hidden on BOTH axes: x clips the EvalChart slider's intentional ±8px
      // alignment slack (its -ml-8px track overhang); y clips a too-tall group on a short
      // window instead of showing a vertical scrollbar (Phase 161 UAT — the user prefers
      // the eval chart cut off at the bottom over a middle-column scrollbar).
      className="flex w-full min-w-0 shrink-0 flex-col items-center desk3col:min-h-0 desk3col:h-full desk3col:justify-start desk3col:overflow-hidden"
    >
      <div
        className="flex w-full flex-col items-center gap-2"
        style={{ maxWidth: boardWidth ? boardWidth + BOARD_EVAL_BARS_ALLOWANCE_PX : undefined }}
      >
        {/* Source caps (Maia/SF) over the bars + top player (game mode). */}
        <div className="w-full">
          {boardHeaderRow(
            isGameMode && gameData ? playerBar(boardFlipped ? 'white' : 'black') : null,
          )}
        </div>

        {/* Board flanked by its two eval bars — all three exactly boardWidth tall. */}
        <div className="flex flex-row items-center gap-2">
          <div className="w-5 shrink-0" style={{ height: boardWidth }}>
            {leftEvalBarNode('h-full w-full')}
          </div>
          <div
            ref={containerRef}
            data-testid="analysis-board"
            tabIndex={0}
            style={{ width: boardWidth, height: boardWidth }}
          >
            {chessBoardNode()}
          </div>
          <div className="w-5 shrink-0" style={{ height: boardWidth }}>
            {rightEvalBarNode('h-full w-full')}
          </div>
        </div>

        {/* Bottom player (game mode only). */}
        {isGameMode && gameData && (
          <div className="w-full">{boardFooterRow(playerBar(boardFlipped ? 'black' : 'white'))}</div>
        )}

        {/* EvalChart with slider — game mode only, aligned to the board width.
            highlightedPlies (Task 3): dims non-matching markers on tags-panel hover. */}
        {evalChartReady && (
          <div data-testid="analysis-eval-chart" className="w-full">
            {evalChart('h-[120px]', tagsHighlightedPlies)}
          </div>
        )}
      </div>
    </div>
  );

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

  // Shared ELO slider: drives BOTH the FlawChess and Maia engines, so on desktop it
  // sits BETWEEN the two cards (164 UAT); each mobile tab (FlawChess / Maia) renders
  // its own copy since they're separate screens. The FlawChess card header still
  // reflects the value ("FlawChess Engine (N ELO)"). The reset control snaps back to
  // the players' rating once the user has dragged off it (164 UAT).
  const eloSelector = (
    <div className="px-2 flex flex-col gap-2" data-testid="analysis-elo-selector-row">
      <EloSelector
        value={selectedElo}
        onChange={setSelectedElo}
        defaultElo={defaultElo}
        onReset={resetToDefault}
      />
    </div>
  );

  // FlawChess Engine card (D-01, DISPLAY-04) — a fixed-height charcoal Card
  // stacked directly above MaiaHumanPanel, reused verbatim in BOTH the desktop
  // human column and the mobile "FlawChess" tab (mobile-parity: D-01's "apply to
  // both" + CLAUDE.md's mobile-parity rule). Mirrors the Stockfish card's own
  // loading → off → lines CardBody pattern (line ~1585 below): flawChessLoading
  // gates the pre-`isReady` skeleton (worker pool spin-up); once ready,
  // FlawChessEngineLines renders its OWN pre-first-snapshot skeleton internally.
  // `footer` (164 UAT): mobile passes the ELO slider so it sits inside the card;
  // desktop omits it (the slider is a standalone row between the two cards there).
  const renderFlawChessCard = (footer?: React.ReactNode): React.ReactElement => (
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
        <FlawChessInfoTooltip />
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
              terminalOutcome={flawChessTerminalOutcome}
              onMoveClick={playUciLine}
            />
            {/* Agreement verdict (Phase 157-02, REVIEW-02; Phase 158 SEED-087
                SC4; Phase 162 SEED-090 D-13): the Stockfish side is now
                `reconciledStockfishLine` — the TRUE global reconciled argmax
                (`reconciledBestUci`) named at ITS reconciled eval, which may
                be a different move than raw `engine.pvLines[0]` (D-12 accepted
                edge case) — never engineTopLines, which silently degrades to a
                FlawChess row when standalone Stockfish is off. Falls back to
                `engine.pvLines[0]` pre-grading so first paint still resolves.
                The FlawChess side is reconciledRankedLines (evalLookup-
                sourced), so both picks resolve through the SAME lookup —
                making "FC pick grades higher than the objective best"
                impossible by construction.
                Hidden in a terminal position (quick 260709): the game is over, so
                the "Turn on Stockfish to compare picks." prompt is misleading —
                the terminal `#0`/`½–½` badge above says it all. */}
            {flawChessTerminalOutcome == null && (
              <FlawChessAgreementVerdict
                flawChessLine={reconciledRankedLines[0] ?? null}
                stockfishLine={reconciledStockfishLine ?? (engine.pvLines[0] ?? null)}
                flawChessRankedLines={reconciledRankedLines}
                engineEnabled={engineEnabled}
                elo={selectedElo}
                baseFen={position}
                rawProbBySan={rawProbBySan}
                shownSans={shownSans}
                onHoverMovesChange={setHoveredQualityMoves}
                onPlayMove={playProseMove}
              />
            )}
            {/* Phase 159 D-08: the Human <-> Stockfish play-style slider lives at
                the bottom of the FlawChess Engine card (it only reshapes this
                engine's policy). */}
            <div className="mt-2 px-2">
              <TemperatureSelector value={temperature} onChange={setTemperature} />
            </div>
          </>
        )}
        {/* Mobile-only ELO slider inside the card (164 UAT); always shown, even when
            the engine is off, since it also drives the Maia surfaces. */}
        {footer !== undefined && <div className="mt-2">{footer}</div>}
      </CardBody>
    </Card>
  );

  // The mobile "Maia" tab content (D-03, LIC-02) — shared across every mobile tab
  // layout below, so this JSX isn't duplicated. The FlawChess card lives in its own
  // adjacent tab (flawChessTab) rather than here; the ELO slider sits inside the Maia
  // card (as its footer) on mobile since it drives both engines (164 UAT).
  const humanTab = (
    <TabsContent value="human" className="min-h-0 overflow-y-auto thin-scrollbar">
      <div className="flex flex-col gap-3 px-3">
        <MaiaHumanPanel
          selectedElo={selectedElo}
          perElo={maia.perElo}
          playedSan={playedSan}
          // 162-REVIEW WR-02: the chart's emphasized stroke follows the SAME
          // reconciled Best the quality color/label/verdict designate, not the
          // raw free-run pick (raw bestSan still feeds selectCandidatesByMass
          // above so the free-run pick stays plotted).
          bestSan={reconciledBestSan ?? bestSan}
          shownSans={shownSans}
          qualityBySan={qualityBySanWithGem}
          mover={sideToMoveFromFen(position)}
          engineTopLines={engineTopLines}
          onHoverMovesChange={setHoveredQualityMoves}
          isOpponentToMove={isOpponentToMove}
          onPlayMove={playProseMove}
          enabled={maiaEnabled}
          onToggleEnabled={setMaiaEnabled}
          compact
          footer={eloSelector}
        />
      </div>
    </TabsContent>
  );

  // The mobile "FlawChess" tab content — the FlawChess Engine card, moved out of the
  // Maia tab into its own tab to the right of it. Shared across the mobile tab layouts.
  // The ELO slider sits inside the card (as its footer) on mobile (164 UAT), since this
  // is a separate screen from the Maia tab (which carries its own copy).
  const flawChessTab = (
    <TabsContent value="flawchess" className="min-h-0 overflow-y-auto thin-scrollbar">
      <div className="flex flex-col gap-3 px-3">{renderFlawChessCard(eloSelector)}</div>
    </TabsContent>
  );

  // Mobile Stockfish PV lines, without the info-card header. Mirrors the desktop
  // `analysis-engine-card` body's loading → off → lines branches. Relocated from
  // above the board to the top of the Eval tab; shown there in every mobile layout.
  const mobileEngineLines = (
    <div className="shrink-0 px-2" data-testid="analysis-engine-lines-mobile">
      {engineLoading ? (
        <EngineLinesSkeleton testId="analysis-engine-loading" compact />
      ) : !engineEnabled ? (
        <div className="flex h-full items-center px-2 text-sm text-muted-foreground">
          Engine off
        </div>
      ) : (
        // 162 UAT: reconciled top-2 over the full grading union, mobile parity
        // with the desktop card below (CLAUDE.md mobile-parity rule).
        <EngineLines
          pvLines={reconciledPvLines}
          isAnalyzing={engine.isAnalyzing}
          startPly={currentPly}
          baseFen={position}
          flipped={boardFlipped}
          onMoveClick={playUciLine}
          compact
        />
      )}
    </div>
  );

  // The mobile "Eval" tab content — Stockfish PV lines on top, the eval chart below
  // (game mode only; evalChart() returns null in free play / before the game loads,
  // leaving just the engine lines).
  const evalTab = (
    <TabsContent
      value="eval"
      className="min-h-0 overflow-x-hidden overflow-y-auto thin-scrollbar"
    >
      <div className="flex flex-col gap-2 pt-1">
        {mobileEngineLines}
        {evalChartReady && <div className="px-3">{evalChart('h-[120px]')}</div>}
      </div>
    </TabsContent>
  );

  // The mobile "Moves" tab content — the vertical variation tree. Shared across the
  // mobile tab layouts.
  const movesTab = (
    <TabsContent value="moves" className="flex min-h-0 flex-1 flex-col">
      {variationTree('vertical')}
    </TabsContent>
  );

  // The mobile "Tags" tab content — the flaw-tags panel (game mode only, so it only
  // appears in the full tab strip below).
  const tagsTab = (
    <TabsContent value="tags" className="min-h-0 overflow-y-auto thin-scrollbar">
      <div className="px-2">{tagsPanel()}</div>
    </TabsContent>
  );

  // ── Mobile takeover layout (< 640px) ──────────────────────────────────────────
  // Board + eval bar, then a tab view (Moves | Eval | Maia | FlawChess [| Tags]) that
  // fills the space down to the in-flow board-controls footer. The Stockfish PV lines
  // live at the top of the Eval tab (not above the board). The shell's back-button
  // header + suppressed bottom nav (ProtectedLayout) complete the takeover.
  if (isMobile) {
    return (
      <div
        data-testid="analysis-page"
        className="flex min-h-0 flex-1 flex-col bg-background"
      >
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

        {/* Tab view — fills all vertical space between the board and the footer.
            Bounded chart height inside the Eval tab (not h-full): the board already
            dominates the viewport, so a greedy chart pushed the board-controls footer
            off-screen when the mobile browser's URL bar shrank the height. h-[120px]
            (the established mobile chart height) keeps the footer visible. The full
            5-tab strip (with Tags) shows only for a loaded, analyzed game; free play
            and still-loading games drop the Tags tab. */}
        {isGameMode && evalChartReady ? (
          <Tabs
            defaultValue="moves"
            className="flex min-h-0 flex-1 flex-col gap-2 px-2 pt-2"
          >
            <TabsList variant="underline" className="w-full shrink-0">
              <TabsTrigger value="moves" data-testid="analysis-tab-moves" className="gap-1 px-1">
                <ArrowLeftRight aria-hidden="true" />
                Moves
              </TabsTrigger>
              {/* Engine-colored tab nav: Eval = Stockfish blue, Maia = violet,
                  FlawChess = gold — matching each surface's accent (theme.ts). */}
              <TabsTrigger
                value="eval"
                data-testid="analysis-tab-eval"
                className="gap-1 px-1"
                style={{ color: STOCKFISH_ACCENT }}
              >
                <Cpu aria-hidden="true" />
                Eval
              </TabsTrigger>
              <TabsTrigger
                value="human"
                data-testid="analysis-tab-human"
                className="gap-1 px-1"
                style={{ color: MAIA_ACCENT }}
              >
                <User aria-hidden="true" />
                Maia
              </TabsTrigger>
              <TabsTrigger
                value="flawchess"
                data-testid="analysis-tab-flawchess"
                className="gap-1 px-1"
                style={{ color: FLAWCHESS_ENGINE_ACCENT }}
              >
                <ChessKnight aria-hidden="true" />
                FlawChess
              </TabsTrigger>
              <TabsTrigger value="tags" data-testid="analysis-tab-tags" className="gap-1 px-1">
                <Tag aria-hidden="true" />
                Tags
              </TabsTrigger>
            </TabsList>
            {movesTab}
            {evalTab}
            {humanTab}
            {flawChessTab}
            {tagsTab}
          </Tabs>
        ) : (
          // Free play or a still-loading / unanalyzed game: no eval chart or tags, but
          // Moves, engine lines (Eval tab), Maia, and FlawChess must all stay reachable.
          <Tabs defaultValue="moves" className="flex min-h-0 flex-1 flex-col gap-2 px-2 pt-2">
            <TabsList variant="underline" className="w-full shrink-0">
              <TabsTrigger value="moves" data-testid="analysis-tab-moves" className="gap-1 px-1">
                <ArrowLeftRight aria-hidden="true" />
                Moves
              </TabsTrigger>
              {/* Engine-colored tab nav: Eval = Stockfish blue, Maia = violet,
                  FlawChess = gold — matching each surface's accent (theme.ts). */}
              <TabsTrigger
                value="eval"
                data-testid="analysis-tab-eval"
                className="gap-1 px-1"
                style={{ color: STOCKFISH_ACCENT }}
              >
                <Cpu aria-hidden="true" />
                Eval
              </TabsTrigger>
              <TabsTrigger
                value="human"
                data-testid="analysis-tab-human"
                className="gap-1 px-1"
                style={{ color: MAIA_ACCENT }}
              >
                <User aria-hidden="true" />
                Maia
              </TabsTrigger>
              <TabsTrigger
                value="flawchess"
                data-testid="analysis-tab-flawchess"
                className="gap-1 px-1"
                style={{ color: FLAWCHESS_ENGINE_ACCENT }}
              >
                <ChessKnight aria-hidden="true" />
                FlawChess
              </TabsTrigger>
            </TabsList>
            {movesTab}
            {evalTab}
            {humanTab}
            {flawChessTab}
          </Tabs>
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
      {/* Phase 161 D-03: max-w-7xl removed at desk3col+ to reclaim horizontal space
          for the fluid grid; min-h-0/flex/h-full complete the min-h-0 chain from the
          App shell (D-01) down into the grid row below. */}
      <main className="mx-auto w-full flex-1 px-4 py-2 pb-20 md:py-6 md:pb-6 md:px-6 desk3col:flex desk3col:h-full desk3col:min-h-0 desk3col:flex-col">
        {/* Phase 161 UAT: cap the grid at its natural full-board width and center it
            (desk3col:mx-auto). Below the cap the fluid `1fr` center track still shrinks the
            board; above it the grid stops growing, so surplus width lands in the window
            margins and the side panels stay hugged to the board+bars instead of drifting
            apart. maxWidth is harmless below desk3col (stacked column, always narrower).
            desk3col:w-full gives the grid a definite width so the `1fr` track keeps a real
            basis; without it a bare mx-auto collapses the flex item to content width and
            starves the board's width measurement. */}
        <div
          className="flex flex-col gap-4 desk3col:mx-auto desk3col:grid desk3col:h-full desk3col:min-h-0 desk3col:w-full desk3col:grid-cols-[360px_1fr_360px]"
          style={{ maxWidth: DESKTOP_GRID_MAX_WIDTH_PX }}
        >

          {/* Human column ──────────────────────────────────────────────────── */}
          {/* D-01 3-column layout: left = Maia ("human") surfaces, matching the
              existing right panel's ~360px width (D-02 trade-off: narrower chart,
              fewer x-axis ticks, accepted for the thematic left-grouping). */}
          <div
            data-testid="analysis-human-column"
            className="flex w-full shrink-0 flex-col gap-4 min-w-0 desk3col:w-[360px] desk3col:min-h-0 desk3col:h-full desk3col:overflow-y-auto"
          >
            {/* Invisible spacer mirroring the board column's top player bar so the
                Human card top aligns with the board top (not the player-bar top) —
                same trick as the engine column. Desktop only; -mb-2 trims this
                column's gap-4 to the board column's gap-2. (Quick 260705-bm3) */}
            {isGameMode && gameData && (
              <div aria-hidden="true" className="hidden desk3col:block desk3col:invisible desk3col:-mb-2">
                {playerBar(boardFlipped ? 'white' : 'black')}
              </div>
            )}
            {renderFlawChessCard()}
            {/* Shared ELO slider between the two cards (164 UAT): it drives both the
                FlawChess and Maia engines, so it sits in the gap rather than inside
                either card. */}
            {eloSelector}
            <MaiaHumanPanel
              selectedElo={selectedElo}
              perElo={maia.perElo}
              playedSan={playedSan}
              // 162-REVIEW WR-02: same reconciled-emphasis threading as the
              // mobile Maia tab above (CLAUDE.md mobile/desktop parity).
              bestSan={reconciledBestSan ?? bestSan}
              shownSans={shownSans}
              qualityBySan={qualityBySanWithGem}
              mover={sideToMoveFromFen(position)}
              engineTopLines={engineTopLines}
              onHoverMovesChange={setHoveredQualityMoves}
              isOpponentToMove={isOpponentToMove}
              onPlayMove={playProseMove}
              enabled={maiaEnabled}
              onToggleEnabled={setMaiaEnabled}
            />
          </div>

          {/* Board column ──────────────────────────────────────────────────── */}
          {/* Fluid `1fr` grid track holding the JS-sized board stage (caps + players +
              board/eval-bars + eval chart). All sizing/scroll behavior lives inside
              desktopBoardStage (defined above) so this middle track is just its slot. */}
          {desktopBoardStage}

          {/* Side panel: engine + variation tree + controls. Narrower than the board
              column (UAT 260627-mt8 item 1) and stretched to the board column's
              height. overflow-hidden (not -y-auto): the column NEVER shows its own
              scrollbar — a too-tall stack is clipped at the viewport bottom, matching the
              board column's Phase 161 clip-don't-scroll rule (user UAT). The move list
              keeps its own internal scroller, so no moves are lost. */}
          <div className="flex w-full shrink-0 flex-col gap-4 min-w-0 desk3col:w-[360px] desk3col:min-h-0 desk3col:h-full desk3col:overflow-hidden">

            {/* Spacer mirroring the board column's top player bar so the engine card
                top aligns with the board top (not the player-bar top). Desktop only
                (desk3col) where the columns sit side by side; invisible keeps its
                height. -mb-2 trims this column's gap-4 down to the board column's
                gap-2 so the spacer→card gap equals the bar→board gap. (Quick 260628-pcb) */}
            {isGameMode && gameData && (
              <div aria-hidden="true" className="hidden desk3col:block desk3col:invisible desk3col:-mb-2">
                {playerBar(boardFlipped ? 'white' : 'black')}
              </div>
            )}

            {/* Game load error (CLAUDE.md isError branch). */}
            {isGameMode && gameError && (
              <p className="text-sm text-muted-foreground p-2">
                Failed to load game. Something went wrong. Please try again in a moment.
              </p>
            )}

            {/* Board-height region: the engine + moves cards together span exactly the
                board's height at desk3col, so the moves card's bottom border (its controls
                footer) lands on the board's bottom edge (user UAT). `--analysis-board-h` is
                the JS-measured board size; the desk3col:h-[var(...)] only binds it on the
                3-column desktop layout, leaving the stacked mobile layout at natural height.
                The tags panel below then sits beside the bottom player bar + eval chart. */}
            <div
              className="flex min-h-0 flex-col gap-4 desk3col:h-[var(--analysis-board-h)] desk3col:shrink-0"
              style={{ '--analysis-board-h': boardWidth ? `${boardWidth}px` : undefined } as CSSProperties}
            >
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
                  {/* 162 UAT (supersedes D-05): once the card re-sources to the
                      reconciled lines, the headline depth describes line 1's own
                      grade — reconciledBestEval falls back to the free run's
                      depth pre-grading, so first paint is unchanged. */}
                  {engineEnabled && reconciledBestEval.depth > 0 ? `, Depth ${reconciledBestEval.depth}` : ''}
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
                  // 162 UAT (supersedes D-04/D-12 card scope): reconciledPvLines
                  // is the reconciled top-2 over the full grading union, so the
                  // card always lists the same best move the arrow, chart crown,
                  // and verdict name.
                  <EngineLines
                    pvLines={reconciledPvLines}
                    isAnalyzing={engine.isAnalyzing}
                    startPly={currentPly}
                    baseFen={position}
                    flipped={boardFlipped}
                    onMoveClick={playUciLine}
                  />
                )}
              </CardBody>
            </Card>

            {/* Move list in a charcoal card. Unlike the engine card above (darker HEADER),
                the board controls sit in a darker FOOTER band (bg-black/20 border-t —
                mirror of CardHeader) so the card reads header-less at the top. The card is
                the column's flex-1 element: the move list fills and scrolls internally, the
                controls stay pinned at the card bottom (chess.com pattern — UI-SPEC). */}
            <Card
              data-testid="analysis-movelist-card"
              className="relative flex min-h-0 flex-1 flex-col"
            >
              <CardHeader size="compact" data-testid="analysis-movelist-header">
                <ArrowLeftRight className="h-4 w-4" aria-hidden />
                Moves
              </CardHeader>
              {variationTree('responsive')}
              <div className="border-t border-border/40 bg-black/20 px-1">
                {boardControls(true, 'sm')}
              </div>
            </Card>
            </div>

            {/* Phase 161 D-04: Tags/badges panel relocated here from the board column
                (was directly under the eval chart) so that column is board + chart
                only. withHighlight=true preserved — its hover state still wires back
                onto the eval chart in the middle column. */}
            {tagsPanel(true)}
          </div>

        </div>
      </main>
    </div>
  );
}
