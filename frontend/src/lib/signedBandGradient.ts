/**
 * Shared signed-band gradient-stops algorithm.
 *
 * Lifted verbatim from EndgameScoreOverTimeChart.tsx:99-165 (Phase 68 UAT fix
 * for the "first non-zero diff initialises currentColor" rule + the
 * `colorA !== colorB` zero-endpoint handling). See the inline comments in the
 * function body for the two edge cases.
 *
 * Phase 87.6: extracted into this shared helper so both
 * EndgameScoreOverTimeChart and EndgameEloTimelineSection call the same
 * code path. One bug-fix surface for any future crossover edge case.
 *
 * IMPORTANT — Recharts UAT pitfall (Phase 68, 260424-pc6):
 * The <Area> that references this gradient MUST be a direct child of
 * <ComposedChart>. A plain <g> wrapper hides the <Area> from Recharts'
 * `findAllByType` scan in `generateCategoricalChart`, so the area never
 * registers with the chart axes and no <path> is emitted. Do NOT wrap
 * <Area> in <g> or <React.Fragment>.
 *
 * See .planning/notes/endgame-elo-pr-direct-rebuild.md for derivation context.
 */

export interface GradientStop {
  offset: number;  // percentage 0..100 along the gradient's x-axis
  color: string;
}

export interface SignedBandRow {
  x: number;            // domain x value (reserved for future non-uniform spacing)
  sign: 1 | -1 | 0;    // direction at this row (0 inherits previous-segment color)
}

/**
 * Build the stop sequence for a horizontal `<linearGradient>` that paints a
 * signed band with instant color flips at every sign crossover.
 *
 * Lifted verbatim from `EndgameScoreOverTimeChart.tsx:99-165` (Phase 68 UAT fix
 * for the "first non-zero diff initialises currentColor" rule + the
 * `colorA !== colorB` zero-endpoint handling). See the inline comments in the
 * function body for the two edge cases.
 *
 * @param rows  Row signs in domain order. Length 0 → empty stops.
 * @param _xDomain  [min, max] domain — currently unused (offset = i / (N-1) * 100);
 *                  reserved for future non-uniform x spacing.
 * @param colors  Positive (sign=1) and negative (sign=-1) fill colors. Sign=0
 *                inherits the previous segment's color.
 */
export function signedBandGradient(
  rows: SignedBandRow[],
  _xDomain: [number, number],
  colors: { positive: string; negative: string },
): GradientStop[] {
  const colorFor = (sign: number): string =>
    sign >= 0 ? colors.positive : colors.negative;

  const stops: GradientStop[] = [];
  const N = rows.length;
  if (N > 0) {
    // Bug 260424: initialize the starting color from the first NON-ZERO
    // sign, not `rows[0]`. If the first row has sign=0, `colorFor(0)` returns
    // positive. The prior sign-flip detector then missed subsequent negative
    // segments because `0 * dB = 0` is not strictly `< 0`, so the whole band
    // stayed positive even where sign was -1. Finding the first non-zero sign
    // makes the initial color match the first visible band direction.
    let currentColor = colors.positive;
    for (const row of rows) {
      if (row.sign !== 0) {
        currentColor = colorFor(row.sign);
        break;
      }
    }
    stops.push({ offset: 0, color: currentColor });
    const denom = N > 1 ? N - 1 : 1;
    for (let i = 0; i < N - 1; i++) {
      const rowA = rows[i]!;
      const rowB = rows[i + 1]!;
      const dA = rowA.sign;
      const dB = rowB.sign;
      const colorA = colorFor(dA);
      const colorB = colorFor(dB);
      // Insert an instant color flip whenever the segment endpoints fall
      // on different color sides. Using `colorA !== colorB` instead of the
      // stricter `dA * dB < 0` correctly handles the zero-endpoint case:
      // if dA=0 and dB<0 the linear t lands at 0 (start of segment),
      // producing a coincident flip-stop that switches `currentColor`
      // forward.
      if (colorA !== colorB) {
        const t = dA / (dA - dB); // in [0, 1] when colorA !== colorB
        const offsetPct = ((i + t) / denom) * 100;
        stops.push({ offset: offsetPct, color: currentColor });
        stops.push({ offset: offsetPct, color: colorB });
        currentColor = colorB;
      }
    }
    stops.push({ offset: 100, color: currentColor });
  }

  return stops;
}
