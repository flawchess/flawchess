/**
 * Phase 86 — Orchestrator for the "Endgame Metrics" card grid (Conv / Parity /
 * Recov), replacing the legacy `EndgameScoreGapSection` (4-gauge strip +
 * eval-stratified WDL table) per SEC2-10.
 *
 * Layout (Phase 87.4): 3-column card grid on lg+, single-column stacked on
 * mobile. Reading order Conversion → Parity → Recovery. The Endgame Skill
 * card + ConnectorArrows overlay were hard-deleted in Phase 87.4 (D-05).
 *
 * Cards live in sibling files (`EndgameMetricCard`). This file is the
 * orchestrator: it derives per-card props from `ScoreGapMaterialResponse`
 * and mounts the three cards.
 *
 * Phase 87.2 refactor: MIRROR_BUCKET wiring removed; buildZeroRow updated to
 * drop the deleted MaterialRow fields; scoreGap* props threaded from
 * response.section2_score_gap_{conv,parity,recov}_* to each card.
 * Phase 87.4 refactor: EndgameSkillCard + tile-endgame-skill + ConnectorArrows
 * deleted; endgameWdl prop removed (the deleted Skill card was its sole
 * consumer); `relative` class dropped from the grid (no positioned children
 * remain).
 */

import type { ReactNode } from 'react';

import type {
  MaterialBucket,
  MaterialRow,
  ScoreGapMaterialResponse,
} from '@/types/endgames';

import { EndgameMetricCard } from './EndgameMetricCard';

const TILE_TESTIDS: Record<MaterialBucket, string> = {
  conversion: 'tile-conversion',
  parity: 'tile-parity',
  recovery: 'tile-recovery',
};

// Title-tooltip content per bucket. Lives next to the card title and explains
// the bucket in plain language. Technical details (eval thresholds, gauge band
// calibration) live in the "Endgame statistics concepts" section above.
const TITLE_TOOLTIPS: Record<MaterialBucket, ReactNode> = {
  conversion: (
    <p>
      <strong>Conversion:</strong> how often you closed out winning endgames,
      the ones you entered with a clear advantage of at least +1.0.
    </p>
  ),
  parity: (
    <p>
      <strong>Parity:</strong> how well you scored from roughly balanced endgame
      positions.
    </p>
  ),
  recovery: (
    <p>
      <strong>Recovery:</strong> how often you held or saved losing endgames,
      the ones you entered with a clear disadvantage of at least -1.0.
    </p>
  ),
};

/** Synthesize a zero-row for buckets missing from the response. Lets
 * `EndgameMetricCard` render its empty-state branch (gauge at 0% with
 * opacity-50, no WDL bar, no ScoreGapRow) cleanly without conditional
 * skipping at the orchestrator level.
 * Phase 87.2: opponent_score, opponent_games, diff_p_value, diff_ci_low,
 * diff_ci_high removed (deleted from MaterialRow per D-05). */
function buildZeroRow(bucket: MaterialBucket): MaterialRow {
  return {
    bucket,
    label: '',
    games: 0,
    win_pct: 0,
    draw_pct: 0,
    loss_pct: 0,
    score: 0,
  };
}

interface EndgameMetricsSectionProps {
  data: ScoreGapMaterialResponse;
}

export function EndgameMetricsSection({ data }: EndgameMetricsSectionProps) {
  const totalMaterialGames = data.material_rows.reduce((sum, r) => sum + r.games, 0);

  const rowByBucket: Partial<Record<MaterialBucket, MaterialRow>> = {};
  for (const r of data.material_rows) rowByBucket[r.bucket] = r;

  return (
    <section data-testid="endgame-metrics-section">
      <p className="text-sm text-muted-foreground">
        How do you score from winning, balanced, and losing endgames?
      </p>

      {/* Phase 87.4: 3-column card grid on xl+, single-column stacked below.
          DOM order: Conv -> Parity -> Recov. The Skill card slot + ConnectorArrows
          SVG overlay were deleted in Phase 87.4 D-05; the row sits cleanly in a
          3-col grid with no `relative` positioning needed. */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4 mt-2">
        {/* Conversion card */}
        <EndgameMetricCard
          key="conversion"
          bucket="conversion"
          row={rowByBucket['conversion'] ?? buildZeroRow('conversion')}
          sharePct={totalMaterialGames > 0 ? ((rowByBucket['conversion']?.games ?? 0) / totalMaterialGames) * 100 : 0}
          scoreGapMean={data.section2_score_gap_conv_mean}
          scoreGapN={data.section2_score_gap_conv_n}
          scoreGapPValue={data.section2_score_gap_conv_p_value}
          scoreGapCiLow={data.section2_score_gap_conv_ci_low}
          scoreGapCiHigh={data.section2_score_gap_conv_ci_high}
          scoreGapPercentile={data.section2_score_gap_conv_percentile}
          tileTestId={TILE_TESTIDS['conversion']}
          titleTooltip={TITLE_TOOLTIPS['conversion']}
        />

        {/* Parity card */}
        <EndgameMetricCard
          key="parity"
          bucket="parity"
          row={rowByBucket['parity'] ?? buildZeroRow('parity')}
          sharePct={totalMaterialGames > 0 ? ((rowByBucket['parity']?.games ?? 0) / totalMaterialGames) * 100 : 0}
          scoreGapMean={data.section2_score_gap_parity_mean}
          scoreGapN={data.section2_score_gap_parity_n}
          scoreGapPValue={data.section2_score_gap_parity_p_value}
          scoreGapCiLow={data.section2_score_gap_parity_ci_low}
          scoreGapCiHigh={data.section2_score_gap_parity_ci_high}
          scoreGapPercentile={data.section2_score_gap_parity_percentile}
          tileTestId={TILE_TESTIDS['parity']}
          titleTooltip={TITLE_TOOLTIPS['parity']}
        />

        {/* Recovery card */}
        <EndgameMetricCard
          key="recovery"
          bucket="recovery"
          row={rowByBucket['recovery'] ?? buildZeroRow('recovery')}
          sharePct={totalMaterialGames > 0 ? ((rowByBucket['recovery']?.games ?? 0) / totalMaterialGames) * 100 : 0}
          scoreGapMean={data.section2_score_gap_recov_mean}
          scoreGapN={data.section2_score_gap_recov_n}
          scoreGapPValue={data.section2_score_gap_recov_p_value}
          scoreGapCiLow={data.section2_score_gap_recov_ci_low}
          scoreGapCiHigh={data.section2_score_gap_recov_ci_high}
          // Phase 94 D-12: recovery percentile is intentionally `null` — the
          // recovery CDF is not shipped. EndgameMetricCard ALSO guards on
          // `bucket !== 'recovery'` defensively (Pitfall 5).
          scoreGapPercentile={null}
          tileTestId={TILE_TESTIDS['recovery']}
          titleTooltip={TITLE_TOOLTIPS['recovery']}
        />
      </div>
    </section>
  );
}
