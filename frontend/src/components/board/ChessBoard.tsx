import { useRef, useEffect, useState, useCallback, useMemo, type RefObject } from 'react';
import { Chessboard } from 'react-chessboard';
import { arrowSortKey, NEUTRAL_ARROW_COLOR } from '../../lib/arrowColor';
import {
  darkSquareStyle,
  lightSquareStyle,
  BOARD_DARK_SQUARE,
  BOARD_LIGHT_SQUARE,
  MOVE_HIGHLIGHT_SQUARE,
  ARROW_OPACITY,
} from '../../lib/theme';
import { HIGHLIGHT_PULSE_DURATION_MS, HIGHLIGHT_PULSE_ITERATIONS } from '../../lib/highlightPulse';
import { DepthLabel, SquareMarkerGroup } from './boardMarkers';
import type { SquareMarker } from './boardMarkers';
import { squareToCoords, buildArrowPath, arrowMoveKey, dedupeArrowsByMove } from './arrowGeometry';
import { computeBoardSize } from './boardSize';

export interface BoardArrow {
  startSquare: string;
  endSquare: string;
  color: string;
  /** Normalized width 0–1 (0 = thinnest, 1 = thickest) */
  width: number;
  /** Whether this arrow's move is currently hovered in the move list */
  isHovered?: boolean;
  /**
   * When true, the arrow's <path> gets the .animate-arrow-pulse class so it
   * pulses (opacity 0.45 → 1.0 → 0.75) for HIGHLIGHT_PULSE_ITERATIONS
   * iterations and then settles at the static ARROW_OPACITY. Used by the
   * deep-link from a Stats finding card → MoveExplorer to draw attention to the
   * candidate move on arrival.
   */
  isHighlightPulse?: boolean;
  /**
   * Optional depth-badge label rendered as an SVG <text> on the arrow's target
   * square (e.g. the tactic depth number), drawn by the shared DepthLabel
   * (boardMarkers.tsx). Omitted = no badge.
   */
  label?: string;
  /**
   * Fill color for the depth-label badge. Caller should pass a theme.ts constant
   * (e.g. TAC_MISSED_LABEL, TAC_ALLOWED_LABEL). Defaults to white.
   */
  labelColor?: string;
  /**
   * When true, this arrow is drawn last of all — above every other arrow,
   * including hovered ones. Used by the analysis board's translucent white
   * next-move arrow so it always stays visible on top of the engine overlay.
   */
  onTop?: boolean;
  /**
   * Optional layer id folded into the arrow's React/dedupe key so two engine
   * arrows on the same from→to (FC + SF agreeing) both survive
   * dedupeArrowsByMove instead of collapsing — mirrors the `-top` suffix
   * escape.
   */
  layerKey?: string;
  /**
   * An explicit resting opacity. The Train reveal dims arrows
   * outside the focused move instead of hiding them. Omitted = the color-based
   * default (neutral grey low-emphasis vs the standard opacity); a hovered arrow
   * always wins over this.
   */
  opacity?: number;
}

// Re-exported so existing importers (useGameOverlay) keep their ChessBoard path.
export type { SquareMarker } from './boardMarkers';

interface ChessBoardProps {
  position: string;
  onPieceDrop: (sourceSquare: string, targetSquare: string) => boolean;
  flipped?: boolean;
  /** Highlight: { from: "e2", to: "e4" } for the last move */
  lastMove?: { from: string; to: string } | null;
  /**
   * Background color for the last-move from/to square overlay. Defaults to the
   * shared translucent yellow (MOVE_HIGHLIGHT_SQUARE). The analysis board passes
   * a severity-coded color.
   */
  lastMoveColor?: string;
  /** Arrows to render on the board */
  arrows?: BoardArrow[];
  /** Severity glyph badges drawn in the top-right corner of a square. */
  squareMarkers?: SquareMarker[];
  /**
   * Board id for square testid generation. Defaults to 'chessboard'.
   * Pass a distinct id (e.g. 'analysis-board') when two boards coexist
   * in the DOM so their square testids do not collide.
   */
  id?: string;
  /**
   * Maximum board width in px on desktop. Defaults to 400 (matches the Openings
   * miniboard). The dedicated /analysis page passes a larger value so its
   * primary board is not cramped. Mobile still uses the full container width.
   */
  maxWidth?: number;
  /**
   * When supplied, the board also shrinks to this element's flex-resolved
   * clientHeight so it fits the available viewport height. Omitted (default) =
   * width-only sizing: the height budget resolves to Infinity.
   */
  heightRef?: RefObject<HTMLElement | null>;
  /**
   * Piece-slide duration in ms, forwarded verbatim to react-chessboard's option
   * of the same name so the passthrough is obvious at both ends.
   *
   * Omitted (the default) keeps the library's own 300ms fallback: it applies
   * that as a destructuring default in ChessboardProvider, which fires on
   * `undefined`, and these props reach it via a plain `...options` spread — so
   * passing `undefined` is the intended "unchanged" path, not a bug.
   *
   * It exists so the analysis board can SHORTEN the slide for the duration of a
   * fast-forward run, where a 300ms animation would outlast
   * the replay's per-ply cadence (FAST_FORWARD_STEP_MS) and be aborted partway
   * through the slide.
   *
   * Pairs with `showAnimations` below: animations are on everywhere except
   * under vitest, where this duration is inert.
   */
  animationDurationInMs?: number;
}

// Coordinate labels use the opposite square's color for contrast
const DARK_SQUARE_NOTATION: React.CSSProperties = { color: BOARD_LIGHT_SQUARE, fontWeight: 600 };
const LIGHT_SQUARE_NOTATION: React.CSSProperties = { color: BOARD_DARK_SQUARE, fontWeight: 600 };

const PIECE_NAMES: Record<string, string> = {
  wP: 'white pawn', wR: 'white rook', wN: 'white knight', wB: 'white bishop', wQ: 'white queen', wK: 'white king',
  bP: 'black pawn', bR: 'black rook', bN: 'black knight', bB: 'black bishop', bQ: 'black queen', bK: 'black king',
};

// Shaft width range as fraction of square size
const MIN_SHAFT_WIDTH = 0.06;
const MAX_SHAFT_WIDTH = 0.26;
// Arrowhead dimensions as fraction of square size
const MIN_HEAD_WIDTH = 0.25;
const MAX_HEAD_WIDTH = 0.65;
const HEAD_LENGTH_RATIO = 0.7; // head length = head width * this
// Neutral grey arrows (in-between zone OR low-data OR low-confidence) render much
// fainter at rest so reliable red/green arrows visually dominate. Hover bumps
// any arrow back to ARROW_HOVER_OPACITY regardless of color.
const ARROW_LOW_EMPHASIS_OPACITY = 0.30;
const ARROW_HOVER_OPACITY = 0.9;
const ARROW_OUTLINE_COLOR = 'rgba(0, 0, 0, 0.5)';
const ARROW_OUTLINE_WIDTH = 1;
// Hovered arrows are slightly larger so they pop out (multiplicative scale)
const ARROW_HOVER_SCALE = 1.3;
// How far past target square center the arrow tip extends (fraction of square size)
const ARROW_TIP_OVERSHOOT = 0.15;
// Arrow highlight-pulse animation. The .animate-arrow-pulse helper in
// src/index.css encodes a CSS keyframe driven by these constants — keep the
// CSS rule in sync if the values change. Total pulse window =
// HIGHLIGHT_PULSE_ITERATIONS × HIGHLIGHT_PULSE_DURATION_MS (~5 s).
// Constants live in lib/highlightPulse.ts so the MoveExplorer row-pulse
// stays driven by the same timing.
const ARROW_PULSE_CLASS = 'animate-arrow-pulse';
// Window in which react-chessboard's own touchend onSquareClick is treated as a
// repeat of the tap our onPointerUp workaround already handled (see
// isDuplicateTouchTap). A real second tap on the same square comes much later.
const TOUCH_TAP_DEDUPE_MS = 500;

// Depth-label and severity corner-marker rendering live in ./boardMarkers, shared
// with MiniBoard so both boards draw identical marks.

/**
 * Resting opacity of one arrow: hover wins, then an explicit `arrow.opacity`
 * (the Train reveal's focus dimming), then the color-based default (neutral grey arrows
 * render much fainter at rest so reliable red/green arrows dominate).
 */
// eslint-disable-next-line react-refresh/only-export-components -- pure helper shared with tests, not a component
export function resolveArrowOpacity(arrow: BoardArrow): number {
  if (arrow.isHovered) return ARROW_HOVER_OPACITY;
  if (arrow.opacity !== undefined) return arrow.opacity;
  return arrow.color === NEUTRAL_ARROW_COLOR ? ARROW_LOW_EMPHASIS_OPACITY : ARROW_OPACITY;
}

interface TouchTap {
  square: string;
  at: number;
}

/**
 * True when a library onSquareClick is the echo of a touch tap the squareRenderer's
 * onPointerUp already handled: same square, within TOUCH_TAP_DEDUPE_MS.
 */
// eslint-disable-next-line react-refresh/only-export-components -- pure helper shared with tests, not a component
export function isDuplicateTouchTap(lastTap: TouchTap | null, square: string, now: number): boolean {
  return lastTap !== null && lastTap.square === square && now - lastTap.at < TOUCH_TAP_DEDUPE_MS;
}

// Render priority: hovered arrow always on top; otherwise green > red >
// neutral grey > any other color. Within each tier, thicker arrows are drawn
// first so thin arrows stay visible.

function ArrowOverlay({
  arrows,
  markers,
  boardWidth,
  flipped,
}: {
  arrows: BoardArrow[];
  markers: SquareMarker[];
  boardWidth: number;
  flipped: boolean;
}) {
  if (arrows.length === 0 && markers.length === 0) return null;

  const sqSize = boardWidth / 8;

  const sortedArrows = dedupeArrowsByMove(
    [...arrows].sort((a, b) => {
      const at = a.onTop ? 1 : 0;
      const bt = b.onTop ? 1 : 0;
      if (at !== bt) return at - bt; // onTop drawn last (above everything, even hovered)
      const ah = a.isHovered ? 1 : 0;
      const bh = b.isHovered ? 1 : 0;
      if (ah !== bh) return ah - bh; // hovered drawn last (on top)
      return arrowSortKey(b.color) - arrowSortKey(a.color) || b.width - a.width;
    }),
  );

  return (
    <svg
      width={boardWidth}
      height={boardWidth}
      style={{ position: 'absolute', top: 0, left: 0, pointerEvents: 'none' }}
      data-testid="arrow-overlay"
    >
      {sortedArrows.map((arrow) => {
        // Skip degenerate arrows where start and end are the same square (causes NaN in path)
        if (arrow.startSquare === arrow.endSquare) return null;

        const [x1, y1] = squareToCoords(arrow.startSquare, flipped);
        const [cx2, cy2] = squareToCoords(arrow.endSquare, flipped);

        // Extend tip past target center
        const adx = cx2 - x1;
        const ady = cy2 - y1;
        const alen = Math.sqrt(adx * adx + ady * ady);
        const x2 = cx2 + (adx / alen) * ARROW_TIP_OVERSHOOT;
        const y2 = cy2 + (ady / alen) * ARROW_TIP_OVERSHOOT;

        const w = arrow.width; // 0–1 normalized frequency
        const scale = arrow.isHovered ? ARROW_HOVER_SCALE : 1;
        const shaftHalf = ((MIN_SHAFT_WIDTH + (MAX_SHAFT_WIDTH - MIN_SHAFT_WIDTH) * w) * sqSize * scale) / 2;
        const headWidth = (MIN_HEAD_WIDTH + (MAX_HEAD_WIDTH - MIN_HEAD_WIDTH) * w) * sqSize * scale;
        const headLen = headWidth * HEAD_LENGTH_RATIO;

        const d = buildArrowPath(
          x1 * sqSize, y1 * sqSize, x2 * sqSize, y2 * sqSize,
          shaftHalf, headWidth / 2, headLen,
        );

        // Highlight-pulse: the CSS class drives the animation and overrides
        // opacity for the pulse window, then settles at ARROW_OPACITY (0.75) via
        // animation-fill-mode: forwards (matching the keyframe's 100% value).
        // Inline style passes the JS constants into CSS so the duration/iteration
        // count are not duplicated as magic numbers.
        const pulseStyle: React.CSSProperties | undefined = arrow.isHighlightPulse
          ? {
              animationDuration: `${HIGHLIGHT_PULSE_DURATION_MS}ms`,
              animationIterationCount: HIGHLIGHT_PULSE_ITERATIONS,
            }
          : undefined;

        // Stable key keyed on the move identity (start→end), NOT the sorted
        // index. Hovering a different move changes another arrow's color and
        // therefore the sort order, so an index-based key would shift the
        // highlighted arrow to a new slot — React would unmount/remount its
        // <path>, restarting the CSS pulse animation. Move-keyed elements are
        // stable across hover-driven re-sorts.
        return (
          <path
            key={arrowMoveKey(arrow)}
            d={d}
            fill={arrow.color}
            opacity={resolveArrowOpacity(arrow)}
            stroke={ARROW_OUTLINE_COLOR}
            strokeWidth={ARROW_OUTLINE_WIDTH}
            strokeLinejoin="round"
            className={arrow.isHighlightPulse ? ARROW_PULSE_CLASS : undefined}
            style={pulseStyle}
          />
        );
      })}
      {/* Depth-label badges drawn after the arrows so they sit on top of the
          arrowheads. Anchored top-left. Only rendered when label is set. */}
      {sortedArrows.map((arrow) =>
        arrow.label ? (
          <DepthLabel
            key={`label-${arrowMoveKey(arrow)}`}
            square={arrow.endSquare}
            label={arrow.label}
            color={arrow.labelColor}
            sqSize={sqSize}
            flipped={flipped}
          />
        ) : null,
      )}
      {/* Severity corner markers — glyph top-right, optional depth top-left. */}
      {markers.map((marker) => (
        <SquareMarkerGroup key={`marker-${marker.square}`} marker={marker} sqSize={sqSize} flipped={flipped} />
      ))}
    </svg>
  );
}

export function ChessBoard({ position, onPieceDrop, flipped = false, lastMove, lastMoveColor, arrows = [], squareMarkers = [], id, maxWidth = 400, heightRef, animationDurationInMs }: ChessBoardProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  // Start at 0 so we don't mount react-chessboard until the container has measured.
  // Mounting with a non-zero width inside a display:none parent (e.g. the hidden
  // breakpoint variant — both desktop and mobile ChessBoards are in the DOM, one
  // hidden via Tailwind `hidden lg:flex` / `lg:hidden`) causes react-chessboard's
  // passive effect to throw "Square width not found" when it measures squares at 0.
  const [boardWidth, setBoardWidth] = useState(0);
  const [selectedSquare, setSelectedSquare] = useState<string | null>(null);
  const [prevPosition, setPrevPosition] = useState<string>(position);
  const lastTouchTapRef = useRef<TouchTap | null>(null);

  useEffect(() => {
    const updateWidth = () => {
      if (containerRef.current) {
        const containerWidth = containerRef.current.clientWidth;
        // heightRef points at a wrapper the caller sizes via flex-1 min-h-0 (the
        // /analysis board row gives the board this treatment); when unset (e.g.
        // the Openings board), heightBudget is Infinity and sizing is width-driven.
        const heightBudget = heightRef?.current?.clientHeight ?? Infinity;
        setBoardWidth(computeBoardSize(containerWidth, heightBudget, maxWidth));
      }
    };

    updateWidth();
    // Single ResizeObserver instance observing both the width container and the
    // optional height-bounding element — one code path, one set of edge cases
    // (do not add a second observer).
    const observer = new ResizeObserver(updateWidth);
    if (containerRef.current) {
      observer.observe(containerRef.current);
    }
    if (heightRef?.current) {
      observer.observe(heightRef.current);
    }
    return () => observer.disconnect();
  }, [maxWidth, heightRef]);

  // Reset selected square when position changes (e.g. navigating move history).
  // State update during render is the React-recommended pattern for derived state resets.
  if (prevPosition !== position) {
    setPrevPosition(position);
    setSelectedSquare(null);
  }

  type SquareClickHandler = NonNullable<
    NonNullable<Parameters<typeof Chessboard>[0]['options']>['onSquareClick']
  >;
  type SquareHandlerArgs = Parameters<SquareClickHandler>[0];

  const handleSquareClick = useCallback(
    ({ square, piece }: SquareHandlerArgs) => {
      if (selectedSquare === null) {
        // First click: select a square that has a piece
        if (piece) setSelectedSquare(square);
      } else if (square === selectedSquare) {
        // Clicked same square: deselect
        setSelectedSquare(null);
      } else {
        // Second click: attempt move from selectedSquare to target
        const success = onPieceDrop(selectedSquare, square);
        setSelectedSquare(null);
        if (!success && piece !== null) {
          // Failed move but clicked another piece — reselect that piece
          setSelectedSquare(square);
        }
      }
    },
    [selectedSquare, onPieceDrop],
  );

  // A clean tap (no finger movement) fires onSquareClick TWICE, once from our
  // onPointerUp workaround below and once from react-chessboard's own
  // onTouchEnd (its tap flag survives when no drag started). The second call
  // sees the just-selected square and deselects it, so a single tap on a piece
  // would never stick; only a drag back onto the source square (which resets
  // the library flag) selected it. Swallow the echo.
  const handleLibrarySquareClick = useCallback(
    (args: SquareHandlerArgs) => {
      if (isDuplicateTouchTap(lastTouchTapRef.current, args.square, performance.now())) {
        lastTouchTapRef.current = null;
        return;
      }
      handleSquareClick(args);
    },
    [handleSquareClick],
  );

  // Memoize squareStyles so its identity is stable across renders that don't
  // change last-move or selection. Without this, react-chessboard 5.x sees a
  // fresh `options` object every parent tick and re-fires its internal
  // animation/dnd effects, which on /openings/games (where ~21 boards mount
  // simultaneously) can amplify a single parent re-render past React's
  // 50-nested-update guard (Sentry FLAWCHESS-3Y).
  const lastMoveFrom = lastMove?.from ?? null;
  const lastMoveTo = lastMove?.to ?? null;
  const squareStyles = useMemo<Record<string, React.CSSProperties>>(() => {
    const styles: Record<string, React.CSSProperties> = {};
    if (lastMoveFrom && lastMoveTo) {
      // Severity-coded on the analysis board; default translucent yellow elsewhere.
      const highlightStyle: React.CSSProperties = { backgroundColor: lastMoveColor ?? MOVE_HIGHLIGHT_SQUARE };
      styles[lastMoveFrom] = highlightStyle;
      styles[lastMoveTo] = highlightStyle;
    }
    if (selectedSquare) {
      styles[selectedSquare] = {
        ...styles[selectedSquare],
        backgroundColor: 'rgba(255, 255, 0, 0.5)',
      };
    }
    return styles;
  }, [lastMoveFrom, lastMoveTo, lastMoveColor, selectedSquare]);

  const boardStyle = useMemo<React.CSSProperties>(
    () => ({ width: boardWidth, height: boardWidth, borderRadius: '0.5rem' }),
    [boardWidth],
  );

  const handlePieceDrop = useCallback(
    ({ sourceSquare, targetSquare }: { sourceSquare: string; targetSquare: string | null }) => {
      if (!targetSquare) return false;
      return onPieceDrop(sourceSquare, targetSquare);
    },
    [onPieceDrop],
  );

  type SquareRenderer = NonNullable<
    NonNullable<Parameters<typeof Chessboard>[0]['options']>['squareRenderer']
  >;
  const squareRenderer = useCallback<SquareRenderer>(
    ({ piece, square, children }) => {
      const pieceName = piece ? PIECE_NAMES[piece.pieceType] : undefined;
      const label = pieceName ? `${square} ${pieceName}` : square;
      return (
        <div
          style={{ width: '100%', height: '100%', ...squareStyles[square] }}
          aria-label={label}
          data-testid={`square-${square}`}
          // react-chessboard v5 mobile tap detection is broken: dnd-kit's
          // TouchSensor starts a drag on minimal finger movement, which resets
          // the library's isClickingOnMobile flag before onTouchEnd fires.
          // This onPointerUp bypasses that flow to make tap-to-move work.
          onPointerUp={(e) => {
            if (e.pointerType === 'touch') {
              lastTouchTapRef.current = { square, at: performance.now() };
              handleSquareClick({ square, piece: piece ?? null });
            }
          }}
        >
          {children}
        </div>
      );
    },
    [squareStyles, handleSquareClick],
  );

  /**
   * Piece animation is on everywhere, mobile included. Don't gate it on
   * `'ontouchstart' in window`: Chrome defines that on any touch-capable desktop
   * (touchscreen laptop, convertible, touch monitor), which silently loses
   * animation on every navigation (and makes FAST_FORWARD_ANIMATION_MS dead
   * code, since the library early-returns `setCurrentPosition(newPosition)` when
   * showAnimations is false).
   *
   * If react-chessboard's mobile black screen (seen on position updates in
   * 5.10.0) ever resurfaces on some device, gate on
   * `!window.matchMedia('(pointer: coarse)').matches` instead (touch-primary
   * devices only). Analysis.test.tsx keeps its coarse-pointer matchMedia shims
   * returning true for that case.
   *
   * The `MODE !== 'test'` term is NOT a device concern — it is jsdom's. jsdom
   * performs no layout, so every square measures 0 and react-chessboard's
   * animation effect throws "Square width not found"
   * (dist/index.esm.js:5317) on any position change. The animation path is
   * therefore unreachable under vitest no matter what we pass, and asserting
   * otherwise would only be asserting against a stub. Real browsers (including
   * every mobile one) take the `true` branch.
   */
  const showAnimations = import.meta.env.MODE !== 'test';

  const options = useMemo(
    () => ({
      position,
      boardOrientation: (flipped ? 'black' : 'white') as 'black' | 'white',
      boardStyle,
      darkSquareStyle,
      lightSquareStyle,
      darkSquareNotationStyle: DARK_SQUARE_NOTATION,
      lightSquareNotationStyle: LIGHT_SQUARE_NOTATION,
      id: id ?? 'chessboard',
      // Off only under vitest (jsdom has no layout; see showAnimations).
      showAnimations,
      // Undefined here = the library's own 300ms default (see the prop doc).
      animationDurationInMs,
      // Disable library's built-in arrow drawing — we use our own ArrowOverlay
      // which avoids NaN path errors from the library's same-square division-by-zero bug
      allowDrawingArrows: false,
      squareStyles,
      squareRenderer,
      onSquareClick: handleLibrarySquareClick,
      onPieceDrop: handlePieceDrop,
    }),
    [position, flipped, boardStyle, showAnimations, animationDurationInMs, squareStyles, squareRenderer, handleLibrarySquareClick, handlePieceDrop, id],
  );

  return (
    <div ref={containerRef} className="w-full" data-testid="chessboard">
      {boardWidth > 0 && (
      <div style={{ position: 'relative', width: boardWidth, height: boardWidth, touchAction: 'none', borderRadius: '0.5rem', overflow: 'hidden' }}>
        <Chessboard options={options} />
        <ArrowOverlay arrows={arrows} markers={squareMarkers} boardWidth={boardWidth} flipped={flipped} />
      </div>
      )}
    </div>
  );
}
