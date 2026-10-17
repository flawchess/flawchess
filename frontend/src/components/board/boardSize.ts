/**
 * Board size computation shared by ChessBoard's ResizeObserver-driven effect.
 *
 * The board shrinks with available width/height, floors at BOARD_MIN_WIDTH under
 * height pressure, and never grows past the caller's maxWidth. Extracted into a
 * pure function so the clamp/zero-guard logic is unit-testable without mounting
 * react-chessboard or mocking ResizeObserver.
 */

/** Floor — the board never shrinks below this even on a very short viewport. */
export const BOARD_MIN_WIDTH = 420;
/** Ceiling for the /analysis board — Analysis.tsx passes this as its
 * `maxWidth` prop (and derives layout widths from it). The ceiling inside
 * `computeBoardSize` is the caller's own `maxWidth`, not this constant. */
export const BOARD_MAX_WIDTH = 540;

/** Horizontal space the two flanking eval bars + their `gap-2` gutters consume in the
 *  desktop analysis board row: 2×(w-5 bar = 20px) + 2×(gap-2 = 8px). Shared so
 *  `useBoardStageSize.ts` (subtracts it from the stage width to compute `boardWidth`) and
 *  `Analysis.tsx`/`AnalysisBoardStage.tsx` (add it back to that `boardWidth` for the board
 *  group's `maxWidth`) use one bound: independent copies could silently disagree and clip
 *  the eval bars. */
export const BOARD_EVAL_BARS_ALLOWANCE_PX = 56;

/** Per-side horizontal slack (px) left between the analysis board group and its center
 *  track, so the EvalChart slider's thumb overhang doesn't get clipped.
 *  Lives next to `BOARD_EVAL_BARS_ALLOWANCE_PX` (see its doc comment) instead of as a
 *  private per-file copy. */
export const EVAL_SLIDER_SLACK_PX = 12;

/** Desktop-only analysis board-size reduction: draws the board 20px smaller than its
 *  natural fit. Lives next to `BOARD_EVAL_BARS_ALLOWANCE_PX` (see its doc comment)
 *  instead of as a private per-file copy. */
export const DESKTOP_BOARD_SIZE_REDUCTION_PX = 20;

/**
 * Compute the board's pixel size given a width budget, a height budget, and
 * the caller's own maxWidth prop.
 *
 * Zero-guard: if EITHER budget is <= 0, return 0 unconditionally (before any
 * clamping) so ChessBoard's `boardWidth > 0` render gate still suppresses the
 * react-chessboard mount-at-zero-size crash (see ChessBoard.tsx comment at the
 * `boardWidth` state declaration). Do NOT let the BOARD_MIN_WIDTH floor turn a
 * genuine 0 budget into a non-zero board size.
 */
export function computeBoardSize(widthBudget: number, heightBudget: number, maxWidth: number): number {
  if (widthBudget <= 0 || heightBudget <= 0) return 0;
  // The BOARD_MIN_WIDTH floor guards against HEIGHT pressure ONLY (the board never
  // shrinks below it even on a very short viewport). It must NOT clamp the width
  // budget: a container narrower than the floor (the 400px Openings board, a <420px
  // phone) must still size to its container. Applying Math.max across the whole
  // min() would pin every width-driven, heightBudget=Infinity caller to a fixed
  // 420px and overflow those containers.
  // The ceiling is the caller's maxWidth (default 400). Don't also clamp to
  // BOARD_MAX_WIDTH: that capped the larger Train board.
  const heightFloored = Math.max(BOARD_MIN_WIDTH, heightBudget);
  return Math.min(widthBudget, maxWidth, heightFloored);
}
