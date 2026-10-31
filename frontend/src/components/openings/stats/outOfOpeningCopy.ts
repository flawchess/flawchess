/**
 * Copy for the Openings Stats "Out of the opening" card and its popover (Phase 243).
 * A non-component module so fast refresh stays happy in the components. The unit word is
 * always "eval" (D-03); statistics vocabulary appears only in the greyed footer.
 */

import {
  COPY_CHANCE,
  PERCENTILE_TYPICAL_HIGH,
  PERCENTILE_TYPICAL_LOW,
  displayPercentile,
  formatOrdinal,
  formatPValue,
} from '@/components/endgames/stats/rankedMetrics';
import { formatSignedGap } from '@/lib/gapBar';
import { evalBaselinePawns } from '@/lib/openingVerdict';
import { TC_LABELS } from '@/lib/timeControlLabels';
import type { Color } from '@/types/api';
import type { OpeningOutRateOut, OpeningOutSide, OpeningOutTcOut } from '@/types/openingOut';

/** Mirrors OPENING_OUT_THRESHOLD in app/services/opening_insights_constants.py (the eval cut for worse/better). */
const OUT_OF_OPENING_EVAL_CUT = 1.0;
/** Mirrors RECENT_GAMES_PER_TC_CAP / RECENCY_WINDOW_MONTHS in app/services/canonical_slice_sql.py. */
const RECENT_GAMES_PER_TC_CAP = 1000;
const RECENCY_WINDOW_MONTHS = 36;
const PERCENT_SCALE = 100;
const CI_DECIMALS = 1;
const FOOTER_SEPARATOR = ' · ';
const NUMBER_LOCALE = 'en-US';

export const OUT_OF_OPENING_LABELS: Record<OpeningOutSide, string> = {
  worse: 'Came out worse',
  better: 'Came out better',
};

/** Label of the pooled rate inside each card; the card title says which games. */
export const OUT_OF_OPENING_RATE_LABEL = 'Share of your games';

/**
 * One plain sentence: WHAT the rate measures, in eval units only (D-03), with the
 * colour-specific threshold spelled out: baseline -/+ cut, from the user's side (UAT).
 */
export function whatCopy(side: OpeningOutSide, color: Color): string {
  const worse = side === 'worse';
  const colorName = color === 'white' ? 'White' : 'Black';
  const baseline = evalBaselinePawns(color);
  const threshold = worse ? baseline - OUT_OF_OPENING_EVAL_CUT : baseline + OUT_OF_OPENING_EVAL_CUT;
  const bound = worse ? 'or lower' : 'or higher';
  const direction = worse ? 'below' : 'above';
  return `how often you leave the opening with an eval of ${formatSignedGap(threshold)} ${bound} as ${colorName}, ${OUT_OF_OPENING_EVAL_CUT.toFixed(1)} ${direction} a typical ${colorName} opening position (${formatSignedGap(baseline)}).`;
}

/** The row hint; the percentile is already oriented (higher = better for the user). */
export function hintCopy(side: OpeningOutSide, percentile: number): string {
  const shown = displayPercentile(percentile);
  return side === 'worse'
    ? `Fewer bad openings than ${shown}% of peers`
    : `More good openings than ${shown}% of peers`;
}

/** The bold percentile statement of the popover. */
export function statementCopy(side: OpeningOutSide, percentile: number): string {
  const shown = displayPercentile(percentile);
  return side === 'worse'
    ? `Fewer bad openings than ${shown}% of similarly rated peers.`
    : `More good openings than ${shown}% of similarly rated peers.`;
}

/** Appended to the statement when the percentile is out of range and not significant. */
export function chanceCopy(percentile: number, significant: boolean): string | null {
  const shown = displayPercentile(percentile);
  const outOfRange = shown < PERCENTILE_TYPICAL_LOW || shown > PERCENTILE_TYPICAL_HIGH;
  return outOfRange && !significant ? COPY_CHANCE : null;
}

/** Cohort, basis and filter-independence (D-12). Trimmed to three lines in UAT. */
export const OUT_OF_OPENING_DISCLOSURES: readonly string[] = [
  'Compared against benchmarked Lichess players at your rating, not FlawChess users.',
  `Ranked games only: rated, opponents within ±100 Elo, your most recent ${RECENT_GAMES_PER_TC_CAP.toLocaleString(NUMBER_LOCALE)} per time control from the last ${RECENCY_WINDOW_MONTHS} months.`,
  'Not affected by the page filters.',
];

function formatCount(value: number): string {
  return value.toLocaleString(NUMBER_LOCALE);
}

function percentOf(fraction: number, decimals: number): string {
  return `${(fraction * PERCENT_SCALE).toFixed(decimals)}%`;
}

/** The popover line of one time control: numbers when ranked, a short status word otherwise. */
export function tcLineCopy(tcOut: OpeningOutTcOut): string {
  const label = TC_LABELS[tcOut.tc];
  switch (tcOut.status) {
    case 'ranked': {
      if (tcOut.percentile_favorable === null || tcOut.rate === null) {
        return `${label}: not ranked yet`;
      }
      const percentile = formatOrdinal(displayPercentile(tcOut.percentile_favorable));
      const games = `${formatCount(tcOut.n)} ${tcOut.n === 1 ? 'game' : 'games'}`;
      return `${label}: ${percentOf(tcOut.rate, 0)}, ${percentile} percentile, ${games}`;
    }
    case 'below_floor':
      return `${label}: not enough games yet (${tcOut.floor_n} of ${tcOut.floor_required})`;
    case 'pending':
      return `${label}: analyzing`;
    case 'unranked':
      return `${label}: not ranked yet`;
  }
}

/**
 * Greyed statistics line: pooled k of n, then (ranked cards only) the 95% CI, the p-value
 * against the peer median it is tested on, and the peer band.
 */
export function footerCopy(rate: OpeningOutRateOut): string {
  const parts = [`${formatCount(rate.k)} of ${formatCount(rate.n)} games`];
  if (rate.ci_low !== null && rate.ci_high !== null) {
    parts.push(`95% CI ${percentOf(rate.ci_low, CI_DECIMALS)} to ${percentOf(rate.ci_high, CI_DECIMALS)}`);
  }
  if (rate.p_value !== null && rate.peer_p50 !== null) {
    parts.push(`${formatPValue(rate.p_value)} vs peer median ${percentOf(rate.peer_p50, CI_DECIMALS)}`);
  }
  if (rate.peer_p25 !== null && rate.peer_p75 !== null) {
    parts.push(`peers typically ${percentOf(rate.peer_p25, 0)} to ${percentOf(rate.peer_p75, 0)}`);
  }
  return parts.join(FOOTER_SEPARATOR);
}
