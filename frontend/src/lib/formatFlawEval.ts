/**
 * formatFlawEval — user-POV eval swing formatter for FlawCard (Phase 112, SC-6).
 *
 * Stored eval_cp / eval_mate values are white-POV (positive = white ahead).
 * A flaw always harms the user — so for a black user, the eval *improves* for
 * white: the before eval is more negative (for black), and the after eval is
 * even more negative. To show the swing from the user's perspective we negate
 * both cp and mate when user_color === 'black'.
 * (Pitfall 3 fix: without this negation, a black user's blunder would show a
 * positive swing, suggesting the position improved — the opposite of the truth.)
 *
 * Mate priority: when eval_mate is non-null it takes precedence over eval_cp
 * (same convention as EvalChart.formatEval). Formatted as "#N" where N is the
 * signed mate count (positive = good for user, negative = bad for user).
 */

import { formatSignedEvalPawns } from '@/lib/clockFormat';

/** Apply user-POV negation: negate both cp and mate for black players. */
function applyUserPov(
  evalCp: number | null,
  evalMate: number | null,
  userColor: string,
): { evalCp: number | null; evalMate: number | null } {
  if (userColor !== 'black') return { evalCp, evalMate };
  return {
    evalCp: evalCp !== null ? -evalCp : null,
    evalMate: evalMate !== null ? -evalMate : null,
  };
}

/** Format a single eval part (before or after). Mate takes priority over cp. */
function formatFlawEvalPart(evalCp: number | null, evalMate: number | null): string {
  if (evalMate !== null) return `#${evalMate}`;
  if (evalCp !== null) return formatSignedEvalPawns(evalCp / 100);
  return '—';
}

/**
 * Format the eval swing from before the flaw to after as a user-POV string.
 *
 * Examples:
 *   - white user, before +4.7, after #-3    → "+4.7 → #-3"
 *   - black user, before eval_cp=-300        → "+3.0 → ..." (negated for user)
 *   - null before                            → "— → ..."
 *
 * @param evalCpBefore  - White-POV centipawns before the flaw (null if unavailable)
 * @param evalMateBefore - White-POV mate count before the flaw (null if unavailable)
 * @param evalCpAfter   - White-POV centipawns after the flaw (null if unavailable)
 * @param evalMateAfter - White-POV mate count after the flaw (null if unavailable)
 * @param userColor     - "white" or "black" — controls POV negation
 * @returns Swing string, e.g. "+4.7 → #-3", "— → -1.2"
 */
export function formatFlawEval(
  evalCpBefore: number | null,
  evalMateBefore: number | null,
  evalCpAfter: number | null,
  evalMateAfter: number | null,
  userColor: string,
): string {
  const { before, after } = formatFlawEvalParts(
    evalCpBefore,
    evalMateBefore,
    evalCpAfter,
    evalMateAfter,
    userColor,
  );
  return `${before} → ${after}`;
}

/**
 * Like {@link formatFlawEval} but returns the before/after parts separately, so
 * callers can interleave their own separators or icons (e.g. FlawCard renders a
 * Cpu icon before `before` and the word "to" between the parts).
 */
export function formatFlawEvalParts(
  evalCpBefore: number | null,
  evalMateBefore: number | null,
  evalCpAfter: number | null,
  evalMateAfter: number | null,
  userColor: string,
): { before: string; after: string } {
  const before = applyUserPov(evalCpBefore, evalMateBefore, userColor);
  const after = applyUserPov(evalCpAfter, evalMateAfter, userColor);
  return {
    before: formatFlawEvalPart(before.evalCp, before.evalMate),
    after: formatFlawEvalPart(after.evalCp, after.evalMate),
  };
}
