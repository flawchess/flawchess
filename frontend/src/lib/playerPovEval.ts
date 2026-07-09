/**
 * playerPovEval — the single shared formatter that re-signs a white-POV
 * Stockfish eval (cp/mate) to the addressed player's ("mover's") frame, for
 * the Maia and FlawChess `/analysis` card prose (quick 260709-o72). A
 * black-mover mate-for-white position must read "-M4" (being mated), not the
 * raw white-POV "M4" — the bug the two prose surfaces both had before this
 * task.
 *
 * White keeps the sign; black flips it (cp and mate both). Delegates the
 * actual string formatting to positionVerdict's formatVerdictEval (DRY —
 * do not re-implement the M-notation/cp branches here).
 */

import type { MoverColor } from '@/lib/liveFlaw';
import { formatVerdictEval } from '@/lib/positionVerdict';

/**
 * Re-signs a white-POV eval to `mover`'s frame, then formats it exactly like
 * formatVerdictEval: "M{n}" / "-M{n}" for mate, "+X.X" / "-X.X" for
 * centipawns, "—" when both are null.
 */
export function formatPlayerPovEval(
  evalCp: number | null,
  evalMate: number | null,
  mover: MoverColor,
): string {
  const flip = mover === 'black';
  const signedCp = flip && evalCp !== null ? -evalCp : evalCp;
  const signedMate = flip && evalMate !== null ? -evalMate : evalMate;
  return formatVerdictEval(signedCp, signedMate);
}
