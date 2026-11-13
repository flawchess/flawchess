/**
 * BlunderCheckSolution: the solution screen every blunder-check window ends on (Phase 249, D-14).
 *
 * Laid out like the personalized-puzzle reveal on phones and desktop (Phase 249 UAT): the
 * shared stage (progress row, board, eval bar), the reveal actions (rewind, back, forward,
 * Analyze, Next: split across the side column on desktop, with flip in its controls row; under
 * the board on tablets; in the fixed bottom bar on phones) and a
 * panel with the host's verdict card, the Your / Best / Game line chips (`TrainLineChips`), the
 * one move list (`TrainMoveTreeList`) and the game footer. The board follows the reveal move
 * tree (`useTrainRevealTree`), wired the way TrainReveal wires it. Every chip's line is a
 * browser-engine search, run one after another on the session's shared engine. Analyze
 * deep-links to /analysis at the blunder position (internal link, so no Umami attribute,
 * D-19). Copy never says whose move it was (D-09: a stranger's window is never "your move").
 * A cleared herring has no lines: its board steps through the sequence with a plain move list and move sounds.
 * A false alarm gets the same lines and Analyze at the flagged move (Phase 249 UAT), without
 * the window's case or the blunder the user did not reach (D-10).
 *
 * No Umami event is added for blunder check (D-19).
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { ReactElement, ReactNode, RefObject } from 'react';
import { EvalBar } from '@/components/analysis/EvalBar';
import { ChessBoard } from '@/components/board/ChessBoard';
import { HorizontalMoveList } from '@/components/board/HorizontalMoveList';
import type { HorizontalMoveItem } from '@/components/board/HorizontalMoveList';
import type { BoardArrow, SquareMarker } from '@/components/board/ChessBoard';
import { BlunderCheckGameFooter } from '@/components/train/blunder-check/BlunderCheckGameFooter';
import {
  BLUNDER_CHECK_SIDE_CLASS,
  BLUNDER_CHECK_SIDE_FOOTER_CLASS,
  BlunderCheckStage,
} from '@/components/train/blunder-check/BlunderCheckStage';
import { TrainLineChips } from '@/components/train/TrainLineChips';
import { TRAIN_MOVE_TREE_HEIGHT_CLASS, TrainMoveTreeList } from '@/components/train/TrainMoveTreeList';
import {
  TrainRevealActionBar,
  TrainRevealControlsRow,
  TrainRevealFooter,
} from '@/components/train/TrainRevealActionBar';
import { TrainScoreChip } from '@/components/train/TrainVerdictDetails';
import { TrainVerdictCard } from '@/components/train/TrainVerdictStrip';
import { useBoardNavigationInput } from '@/hooks/useBoardNavigationInput';
import { useIsDesktop, useIsSmUp } from '@/hooks/useIsDesktop';
import type { TrainEngineLine, TrainGradingEngine } from '@/hooks/useTrainGradingEngine';
import { useTrainRevealTree } from '@/hooks/useTrainRevealTree';
import type { TrainRevealTree } from '@/hooks/useTrainRevealTree';
import { buildTrainPuzzleAnalysisUrl } from '@/lib/analysisUrl';
import type { DrillProgress } from '@/lib/blunderCheckDrill';
import {
  buildSequenceSteps,
  buildSolutionChips,
  buildSolutionOverlay,
  solutionCopy,
  solutionLineUcis,
} from '@/lib/blunderCheckSolution';
import type { SolutionCopy } from '@/lib/blunderCheckSolution';
import { useEngineDisplaySettings } from '@/lib/engineSettings';
import { terminalPositionEval } from '@/lib/liveFlaw';
import { usePublishMobileBoardControls } from '@/lib/mobileBoardControls';
import type { Persona } from '@/lib/personas/personaRegistry';
import { playSound } from '@/lib/sounds';
import { STOCKFISH_ACCENT } from '@/lib/theme';
import { buildChipFocusOverlay, buildTrainFreePlayOverlay } from '@/lib/trainArrows';
import type { TrainEngineOverlay } from '@/lib/trainArrows';
import { resolveOffRootOverlay } from '@/lib/trainRevealBoardOverlay';
import { DEFAULT_ROOT_FOCUS } from '@/lib/trainRevealLines';
import type {
  ChipGroup,
  GameMoveLineState,
  RevealTreeSnapshot,
  RoleKey,
} from '@/lib/trainRevealLines';
import type { HerringSolution, LinesSolution, WindowSolution } from '@/types/blunderCheck';

type StartGameMoveSearch = (fen: string, uci: string) => Promise<TrainEngineLine>;
type LineStates = Readonly<Record<string, GameMoveLineState>>;

/** Search depth handed to the eval bar for a finished game, so a mate fills the bar (TrainSolveScreen's device). */
const TERMINAL_EVAL_DEPTH = 99;

interface SolutionViewProps {
  solution: WindowSolution;
  orientation: 'white' | 'black';
  progress: DrillProgress;
  /** The window's host, who gives the verdict. */
  persona: Persona;
  /** Advances to the next window (or the results). Must be referentially stable. */
  onNext: () => void;
  /** The session's grading engine: only its line search is used here. */
  engine: Pick<TrainGradingEngine, 'startGameMoveSearch'>;
  /**
   * Fired by the Analyze click with the move tree on screen (none for a solution without
   * lines), so the drill can cache the solution for the browser's Back.
   */
  onAnalyze: (revealTree?: RevealTreeSnapshot) => void;
  /** The move tree of a solution restored after Analyze -> Back, else null. */
  restoredTree: RevealTreeSnapshot | null;
}

/**
 * Searches each line one after another (the engine is one shared Worker: a second search
 * would stop the first), reporting every result as it lands. A failed search marks only its
 * own chip, and the next one still runs.
 */
async function searchLinesInOrder(
  fen: string,
  ucis: readonly string[],
  search: StartGameMoveSearch,
  onLine: (uci: string, state: GameMoveLineState) => void,
  isCancelled: () => boolean,
): Promise<void> {
  for (const uci of ucis) {
    if (isCancelled()) return;
    let state: GameMoveLineState;
    try {
      state = { status: 'ready', line: await search(fen, uci) };
    } catch {
      state = { status: 'error' };
    }
    if (isCancelled()) return;
    onLine(uci, state);
  }
}

/** The line state per searched first move; a move with no entry yet is still waiting or searching. */
function useSolutionLines(fen: string, ucis: readonly string[], search: StartGameMoveSearch): LineStates {
  const [lines, setLines] = useState<LineStates>({});
  useEffect(() => {
    let cancelled = false;
    void searchLinesInOrder(
      fen,
      ucis,
      search,
      (uci, state) => setLines((previous) => ({ ...previous, [uci]: state })),
      () => cancelled,
    );
    return () => {
      cancelled = true;
    };
  }, [fen, ucis, search]);
  return lines;
}

/**
 * The chip a missed blunder and a false alarm open on: the move that was played in the game,
 * the one the user misjudged.
 */
const MISJUDGED_MOVE_FOCUS: RoleKey = 'game';

/** What the solution board draws. */
interface SolutionBoardState {
  fen: string;
  lastMove?: { from: string; to: string } | null;
  lastMoveColor?: string;
  squareMarkers?: SquareMarker[];
  arrows?: BoardArrow[];
  /** A move played on the board; absent for a static position, which refuses every move. */
  onPieceDrop?: (from: string, to: string) => boolean;
}

/**
 * What the lines solution board draws on top of the position (the personalized-puzzle
 * reveal's rules). At the solution position: every solution arrow with its move-quality badge,
 * the lit chip's opaque and the others (the other chips, the moves that were also good)
 * translucent. Below it: the reveal's own stepped-line board (`resolveOffRootOverlay`), i.e.
 * the engine arrows with their quality badges, the chip's badge on its first move and the
 * tree's grade of a move the user played.
 */
function solutionBoardOverlay(
  solution: LinesSolution,
  tree: TrainRevealTree,
  chips: readonly ChipGroup[],
  focusChip: ChipGroup | undefined,
  offLineOverlay: TrainEngineOverlay,
  engineArrowCount: number,
): Pick<SolutionBoardState, 'arrows' | 'squareMarkers' | 'lastMoveColor'> {
  if (tree.isAtRoot) {
    const overlay = buildChipFocusOverlay(
      buildSolutionOverlay(solution),
      focusChip === undefined ? null : [focusChip.uci],
    );
    return { arrows: overlay.arrows, squareMarkers: overlay.markers };
  }
  const overlay = resolveOffRootOverlay(offLineOverlay, tree.pvLines, engineArrowCount, tree, chips);
  return {
    arrows: overlay.arrows,
    squareMarkers: overlay.markers,
    lastMoveColor: overlay.lastMoveColor,
  };
}

/** The action bar's stepping controls. */
interface SolutionNav {
  onRewind: () => void;
  onBack: () => void;
  onForward: () => void;
  canRewind: boolean;
  canGoBack: boolean;
  canGoForward: boolean;
}

interface SolutionShellProps {
  progress: DrillProgress;
  persona: Persona;
  orientation: 'white' | 'black';
  /** The verdict card's heading and sentence, with its point badges. */
  copy: SolutionCopy;
  board: SolutionBoardState;
  nav: SolutionNav;
  /** The Analyze target, or null for no Analyze button. */
  analyzeTo: string | null;
  onAnalyzeClick: () => void;
  onNext: () => void;
  renderEvalBar?: (flipped: boolean) => ReactNode;
  /** The chips and move list, given the board's orientation and the desktop controls row
   * that goes between them (falsy below `lg`). */
  renderLines: (flipped: boolean, controlsRow: ReactNode) => ReactNode;
  footer: ReactNode;
  boardRef: RefObject<HTMLDivElement | null>;
}

/**
 * The reveal layout shared by the three solution kinds: stage, action bar (split across the
 * side column on desktop: controls row above the move list, Next as the footer; under the board on tablets, published to the fixed phone bottom bar
 * below `sm`, so exactly one is mounted) and the verdict panel.
 */
function SolutionShell({
  progress,
  persona,
  orientation,
  copy,
  board,
  nav,
  analyzeTo,
  onAnalyzeClick,
  onNext,
  renderEvalBar,
  renderLines,
  footer,
  boardRef,
}: SolutionShellProps): ReactElement {
  // The board opens facing the user's side; the desktop controls row can flip it.
  const [flipped, setFlipped] = useState(orientation === 'black');
  const handleFlip = useCallback(() => setFlipped((previous) => !previous), []);
  const isSmUp = useIsSmUp();
  const isDesktop = useIsDesktop();
  const { onRewind, onBack, onForward, canRewind, canGoBack, canGoForward } = nav;
  const mobileControls = useMemo<Parameters<typeof usePublishMobileBoardControls>[0]>(
    () =>
      isSmUp
        ? null
        : {
            onBack,
            onForward,
            onReset: onRewind,
            canGoBack,
            canGoForward,
            canReset: canRewind,
            onNext,
            analyzeTo,
            onAnalyzeClick,
          },
    [
      isSmUp,
      onBack,
      onForward,
      onRewind,
      canGoBack,
      canGoForward,
      canRewind,
      onNext,
      analyzeTo,
      onAnalyzeClick,
    ],
  );
  usePublishMobileBoardControls(mobileControls);

  // `isSmUp` keeps the one-bar invariant explicit: the phone payload publishes when it is false.
  const onDesktop = isDesktop && isSmUp;
  // Desktop: the controls sit between the chips and the move list.
  const controlsRow = onDesktop && (
    <TrainRevealControlsRow
      onRewind={onRewind}
      onBack={onBack}
      onForward={onForward}
      canRewind={canRewind}
      canGoBack={canGoBack}
      canGoForward={canGoForward}
      onFlip={handleFlip}
    />
  );

  return (
    <BlunderCheckStage
      progress={progress}
      testId="blunder-check-solution"
      boardRef={boardRef}
      evalBar={renderEvalBar?.(flipped)}
      renderBoard={(boardMaxWidthPx) => (
        <ChessBoard
          position={board.fen}
          flipped={flipped}
          lastMove={board.lastMove ?? null}
          lastMoveColor={board.lastMoveColor}
          squareMarkers={board.squareMarkers}
          arrows={board.arrows ?? []}
          onPieceDrop={board.onPieceDrop ?? (() => false)}
          maxWidth={boardMaxWidthPx}
          id="chessboard"
        />
      )}
      actionBar={
        isSmUp && !isDesktop && (
          <TrainRevealActionBar
            onRewind={onRewind}
            onBack={onBack}
            onForward={onForward}
            canRewind={canRewind}
            canGoBack={canGoBack}
            canGoForward={canGoForward}
            analyzeTo={analyzeTo}
            onAnalyzeClick={onAnalyzeClick}
            onNext={onNext}
            framed
            className="w-full"
          />
        )
      }
      underBoard={footer}
      side={
        <div
          className={BLUNDER_CHECK_SIDE_CLASS}
          data-testid="blunder-check-solution-panel"
        >
          <TrainVerdictCard
            persona={persona}
            renderDetails={(avatar) => (
              <div className="flow-root">
                {avatar}
                <h2 className="font-semibold" data-testid="blunder-check-solution-heading">
                  {copy.heading}
                </h2>
                {/* The same "+N" pills as the personalized-puzzle verdict, so the user can
                    read what each part of the sequence earned after the flash is gone. */}
                <p data-testid="blunder-check-solution-summary">
                  {copy.parts.map((part) =>
                    typeof part === 'string' ? (
                      part
                    ) : (
                      <TrainScoreChip
                        key={part.name}
                        points={part.points}
                        testid={`blunder-check-pill-${part.name}`}
                      />
                    ),
                  )}
                </p>
              </div>
            )}
          />
          {renderLines(flipped, controlsRow)}
          {/* Desktop shows the game info under the board instead (underBoard). */}
          {!isDesktop && footer}
          {/* Desktop: Analyze and Next are the side column's footer, on the board's bottom edge. */}
          {onDesktop && (
            <TrainRevealFooter
              onNext={onNext}
              analyzeTo={analyzeTo}
              onAnalyzeClick={onAnalyzeClick}
              className={BLUNDER_CHECK_SIDE_FOOTER_CLASS}
            />
          )}
        </div>
      }
    />
  );
}

/** The Your / Best / Game chips and the one move list under them (TrainReveal's wiring). */
function SolutionLines({
  tree,
  chips,
  focusKey,
  flipped,
  controlsRow,
}: {
  tree: TrainRevealTree;
  chips: readonly ChipGroup[];
  focusKey: ChipGroup['key'] | null;
  flipped: boolean;
  controlsRow: ReactNode;
}): ReactElement {
  return (
    <div className="flex flex-col gap-4" data-testid="blunder-check-solution-lines">
      <TrainLineChips
        chips={chips}
        activeChip={focusKey}
        onSelect={tree.selectChip}
        sanOnlyGameMove={null}
      />
      {controlsRow}
      <TrainMoveTreeList tree={tree} flipped={flipped} />
    </div>
  );
}

/** The Analyze target of a window whose game the user may open, else null. */
function analyzeTarget(gameId: number | null, analysisPly: number): string | null {
  return gameId === null ? null : buildTrainPuzzleAnalysisUrl(gameId, analysisPly);
}

/** A caught blunder opens on the user's better move, the misjudged ones on the game move. */
function linesSolutionFocus(solution: LinesSolution): RoleKey {
  return solution.kind === 'blunder' && solution.outcome === 'caught'
    ? DEFAULT_ROOT_FOCUS
    : MISJUDGED_MOVE_FOCUS;
}

/** A caught or missed blunder, or a false alarm: the chips, their lines and the move tree. */
function LinesSolutionView({
  solution,
  orientation,
  progress,
  persona,
  onNext,
  engine,
  onAnalyze,
  restoredTree,
}: SolutionViewProps & { solution: LinesSolution }): ReactElement {
  const { startGameMoveSearch } = engine;
  const ucis = useMemo(() => solutionLineUcis(solution), [solution]);
  const lines = useSolutionLines(solution.fen, ucis, startGameMoveSearch);
  const chips = useMemo(() => buildSolutionChips(solution, lines), [solution, lines]);
  // The reveal engine stays off until the line searches are done, so it never competes with them.
  const linesSettled = ucis.every((uci) => {
    const status = lines[uci]?.status;
    return status === 'ready' || status === 'error';
  });
  const boardRef = useRef<HTMLDivElement>(null);
  const tree = useTrainRevealTree({
    startFen: solution.fen,
    active: true,
    chips,
    engineEnabled: linesSettled,
    navContainerRef: boardRef,
    restored: restoredTree,
    // A misjudged move opens on the move played in the game, so the user first works out
    // why it is a blunder (or good) before looking at the best move (Phase 249 UAT).
    defaultFocus: linesSolutionFocus(solution),
  });
  const treeSnapshot = tree.snapshot;
  const handleAnalyzeClick = useCallback(
    () => onAnalyze(treeSnapshot()),
    [onAnalyze, treeSnapshot],
  );
  // The lit chip: the tree's focus, else the first chip.
  const focusChip = chips.find((chip) => chip.key === tree.activeChip) ?? chips[0];
  // Below the solution position the board draws the reveal engine's top moves, as many as
  // the Stockfish arrows setting asks for (the personalized-puzzle reveal's stepped board).
  const { sfArrows } = useEngineDisplaySettings();
  const treePvLines = tree.pvLines;
  const treeFen = tree.fen;
  const offLineOverlay = useMemo(
    () => buildTrainFreePlayOverlay(treePvLines, sfArrows, treeFen),
    [treePvLines, sfArrows, treeFen],
  );
  const overlay = solutionBoardOverlay(solution, tree, chips, focusChip, offLineOverlay, sfArrows);

  const copy = useMemo(() => solutionCopy(solution), [solution]);
  // A finished game's result first (the rules know it), else the reveal engine's reading.
  const terminal = terminalPositionEval(tree.fen);
  const evalReading =
    terminal === null
      ? tree.evalReading
      : { evalCp: terminal.cp, evalMate: terminal.mate, depth: TERMINAL_EVAL_DEPTH };
  return (
    <SolutionShell
      progress={progress}
      persona={persona}
      orientation={orientation}
      copy={copy}
      board={{
        fen: tree.fen,
        lastMove: tree.lastMove,
        ...overlay,
        // A drop forks a sideline in place.
        onPieceDrop: tree.playMove,
      }}
      nav={{
        onRewind: tree.goToRoot,
        onBack: tree.goBack,
        onForward: tree.goForward,
        canRewind: !tree.isAtRoot,
        canGoBack: tree.canGoBack,
        canGoForward: tree.canGoForward,
      }}
      boardRef={boardRef}
      analyzeTo={analyzeTarget(solution.game_id, solution.analysis_ply)}
      onAnalyzeClick={handleAnalyzeClick}
      onNext={onNext}
      // The bar waits for the line searches, like the reveal engine that feeds it.
      renderEvalBar={
        linesSettled
          ? (flipped) => (
              <EvalBar
                evalCp={evalReading.evalCp}
                evalMate={evalReading.evalMate}
                depth={evalReading.depth}
                flipped={flipped}
                accentColor={STOCKFISH_ACCENT}
                testId="blunder-check-eval-bar"
                className="h-full w-full"
              />
            )
          : undefined
      }
      renderLines={(flipped, controlsRow) => (
        <SolutionLines
          tree={tree}
          chips={chips}
          focusKey={focusChip?.key ?? null}
          flipped={flipped}
          controlsRow={controlsRow}
        />
      )}
      footer={
        <BlunderCheckGameFooter
          gameId={solution.game_id}
          isOwn={solution.is_own}
          gameInfo={solution.game_info}
        />
      }
    />
  );
}

/**
 * A cleared herring: every judged move was fine. The board rests at the window's start and
 * steps through the sequence (the action bar, the arrow keys, a tap on a move). No chips and
 * no engine: there is nothing to refute, and Analyze opens the game for anyone who wants more.
 */
function HerringSolutionView({
  solution,
  orientation,
  progress,
  persona,
  onNext,
  onAnalyze,
}: SolutionViewProps & { solution: HerringSolution }): ReactElement {
  const handleAnalyzeClick = useCallback(() => onAnalyze(), [onAnalyze]);
  const copy = useMemo(() => solutionCopy(solution), [solution]);
  const steps = useMemo(
    () => buildSequenceSteps(solution.fen, solution.sequence_ucis),
    [solution.fen, solution.sequence_ucis],
  );
  // Plies played on the board: 0 is the window's start.
  const [ply, setPly] = useState(0);
  const lastPly = steps.length;
  // Every step sounds like the move the board lands on (a plain move at the window's start).
  const goTo = useCallback(
    (target: number): void => {
      const next = Math.min(lastPly, Math.max(0, target));
      if (next === ply) return;
      playSound(steps[next - 1]?.sound ?? 'move');
      setPly(next);
    },
    [lastPly, ply, steps],
  );
  const goToStart = useCallback(() => goTo(0), [goTo]);
  const goBack = useCallback(() => goTo(ply - 1), [goTo, ply]);
  const goForward = useCallback(() => goTo(ply + 1), [goTo, ply]);
  const boardRef = useRef<HTMLDivElement>(null);
  useBoardNavigationInput({ containerRefs: [boardRef], goBack, goForward, goHome: goToStart });

  const step = ply === 0 ? undefined : steps[ply - 1];
  const items = useMemo<HorizontalMoveItem[]>(
    () =>
      steps.map((entry, index) => ({
        key: index + 1,
        ply: index + 1,
        numberLabel: entry.numberLabel,
        san: entry.san,
        isCurrent: ply === index + 1,
        testId: `blunder-check-sequence-move-${index + 1}`,
      })),
    [steps, ply],
  );
  return (
    <SolutionShell
      progress={progress}
      persona={persona}
      orientation={orientation}
      copy={copy}
      board={{
        fen: step?.fen ?? solution.fen,
        lastMove: step === undefined ? null : { from: step.from, to: step.to },
      }}
      nav={{
        onRewind: goToStart,
        onBack: goBack,
        onForward: goForward,
        canRewind: ply > 0,
        canGoBack: ply > 0,
        canGoForward: ply < lastPly,
      }}
      boardRef={boardRef}
      analyzeTo={analyzeTarget(solution.game_id, solution.analysis_ply)}
      onAnalyzeClick={handleAnalyzeClick}
      onNext={onNext}
      renderLines={(_flipped, controlsRow) => (
        <div className="flex flex-col gap-4" data-testid="blunder-check-solution-sequence">
          {controlsRow}
          <HorizontalMoveList
            items={items}
            onMoveClick={goTo}
            heightClass={TRAIN_MOVE_TREE_HEIGHT_CLASS}
            testId="blunder-check-sequence-list"
          />
        </div>
      )}
      footer={
        <BlunderCheckGameFooter
          gameId={solution.game_id}
          isOwn={solution.is_own}
          gameInfo={solution.game_info}
        />
      }
    />
  );
}

export function BlunderCheckSolution(props: SolutionViewProps): ReactElement {
  const { solution } = props;
  switch (solution.kind) {
    case 'blunder':
    case 'false_alarm':
      return <LinesSolutionView {...props} solution={solution} />;
    case 'herring':
      return <HerringSolutionView {...props} solution={solution} />;
  }
}
