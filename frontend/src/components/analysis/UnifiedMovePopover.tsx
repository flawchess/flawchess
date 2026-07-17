/**
 * UnifiedMovePopover — the shared three-line popover body shown when hovering a
 * dotted move span (`ProseSpan`) in EITHER analysis card (quick 260708-qrr):
 * the FlawChess Engine card (`FlawChessAgreementVerdict`) and the Maia card
 * (`MaiaMoveQualityBar`) now render the identical breakdown so a hovered move
 * reads the same everywhere.
 *
 * A 2-column table (source label | value) with up to three color-coded, icon-led
 * rows, each keyed to its source's on-page accent (theme.ts) and rendered ONLY
 * when its value is available for that move; the values align in the right column:
 *  - ♞ FlawChess (practical) | <eval>   — gold/amber (FLAWCHESS_ENGINE_ACCENT)
 *  - 🖥 Stockfish (objective) | <eval>  — blue (STOCKFISH_ACCENT)
 *  - 👤 Maia (human) | <probability>    — violet (MAIA_ACCENT)
 *
 * The line color is applied to the WHOLE row (icon + text) via `style.color`;
 * the lucide icons are `currentColor` so they inherit it. Values are passed
 * pre-formatted by each caller (they own the SAN→eval/probability conversion) —
 * a `null`/omitted prop drops that line entirely (the D-locked "omit when
 * unavailable" rule).
 *
 * Rendered inside `ProseSpan`'s PopoverContent, which is a hover/tap-activated
 * info tooltip — so `text-xs` here is within the CLAUDE.md font-size exception.
 */

import { ChessKnight, Cpu, Gem, User } from 'lucide-react';

import { GreatMoveIcon } from '@/components/icons/GreatMoveIcon';
import { FLAWCHESS_ENGINE_ARROW, STOCKFISH_ACCENT, MAIA_ACCENT, GREAT_ACCENT } from '@/lib/theme';

const ICON_CLASS = 'inline h-3.5 w-3.5 shrink-0';

// Value column: right-aligned tabular figures, padded off the label column, so the
// evals/probability line up down the second column.
const VALUE_CELL_CLASS = 'py-0.5 pl-4 text-right align-middle tabular-nums';

// FlawChess line color: the same deep gold the FlawChess move itself is printed
// with in the prose (its dotted-span textColor / board-arrow color).
const FLAWCHESS_LINE_COLOR = FLAWCHESS_ENGINE_ARROW;

export interface UnifiedMovePopoverProps {
  /** FlawChess practical eval, pre-formatted (e.g. "-2.7"); null/undefined omits the line. */
  practicalEval?: string | null;
  /** Stockfish objective eval, pre-formatted (e.g. "-2.5"); null/undefined omits the line. */
  objectiveEval?: string | null;
  /** Maia human move probability, pre-formatted (e.g. "82%"); null/undefined omits the line. */
  maiaProbability?: string | null;
  /**
   * When true, prepends a gem copy line above the source rows. Set by
   * MaiaMoveQualityBar when the hovered move's quality is 'gem'.
   */
  isGem?: boolean;
  /**
   * When true, prepends a great-move copy line above the source rows (Phase
   * 175, SEED-108). Mutually exclusive with `isGem` by construction — a move
   * classifies as at most one of gem/great. Set by MaiaMoveQualityBar when
   * the hovered move's quality is 'great'.
   */
  isGreat?: boolean;
}

export function UnifiedMovePopover({
  practicalEval,
  objectiveEval,
  maiaProbability,
  isGem,
  isGreat,
}: UnifiedMovePopoverProps): React.ReactElement {
  return (
    // 2-column table: source label (icon + name) | eval/probability, so the values
    // align in one right-hand column across the (up to) three source rows.
    <table className="border-collapse">
      <tbody>
        {isGem && (
          <tr style={{ color: MAIA_ACCENT }}>
            <td className="py-0.5" colSpan={2}>
              <span className="flex items-center gap-1.5">
                <Gem className={ICON_CLASS} aria-hidden="true" />
                {/* "this rating", not "your rating" (163-REVIEW IN-01): the C1
                    probability is evaluated at the draggable ELO slider's value,
                    which may sit far from the user's own rating. */}
                Gem — players at this rating almost never find this.
              </span>
            </td>
          </tr>
        )}
        {isGreat && (
          <tr style={{ color: GREAT_ACCENT }}>
            <td className="py-0.5" colSpan={2}>
              <span className="flex items-center gap-1.5">
                <GreatMoveIcon className={ICON_CLASS} aria-hidden="true" />
                {/* Same "this rating" phrasing as the gem line (163-REVIEW IN-01). */}
                Great — players at this rating rarely find this.
              </span>
            </td>
          </tr>
        )}
        {practicalEval != null && (
          <tr style={{ color: FLAWCHESS_LINE_COLOR }}>
            <td className="py-0.5">
              <span className="flex items-center gap-1.5">
                <ChessKnight className={ICON_CLASS} aria-hidden="true" />
                FlawChess (practical)
              </span>
            </td>
            <td className={VALUE_CELL_CLASS}>{practicalEval}</td>
          </tr>
        )}
        {objectiveEval != null && (
          <tr style={{ color: STOCKFISH_ACCENT }}>
            <td className="py-0.5">
              <span className="flex items-center gap-1.5">
                <Cpu className={ICON_CLASS} aria-hidden="true" />
                Stockfish (objective)
              </span>
            </td>
            <td className={VALUE_CELL_CLASS}>{objectiveEval}</td>
          </tr>
        )}
        {maiaProbability != null && (
          <tr style={{ color: MAIA_ACCENT }}>
            <td className="py-0.5">
              <span className="flex items-center gap-1.5">
                <User className={ICON_CLASS} aria-hidden="true" />
                Maia (human)
              </span>
            </td>
            <td className={VALUE_CELL_CLASS}>{maiaProbability}</td>
          </tr>
        )}
      </tbody>
    </table>
  );
}
