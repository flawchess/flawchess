/**
 * Phase 86 — Orchestrator for the 4-card "Endgame Metrics" layout, replacing
 * the legacy `EndgameScoreGapSection` (4-gauge strip + eval-stratified WDL
 * table) per SEC2-10.
 *
 * Layout: 3-column card grid on lg+, single-column stacked on mobile.
 *   Row 1: Conversion (col 1) | Parity (col 2) | Recovery (col 3)
 *   Row 2: Endgame Skill at `lg:col-start-2` (under Parity), cols 1+3 empty.
 *
 * Cards live in sibling files (`EndgameMetricCard`, `EndgameSkillCard`,
 * `EndgameOverallConnectorArrows`). This file is the orchestrator: it derives
 * per-card props from `ScoreGapMaterialResponse` and mounts the four cards
 * plus the connector-arrows SVG overlay.
 *
 * Phase 87.2 refactor: MIRROR_BUCKET wiring removed; buildZeroRow updated to
 * drop the deleted MaterialRow fields; new scoreGap* props threaded from
 * response.section2_score_gap_{conv,parity,recov,skill}_* to each card.
 * The section-level "vs opponents" framing is gone per D-08.
 */

import { useRef, type ReactNode } from 'react';

import type {
  MaterialBucket,
  MaterialRow,
  ScoreGapMaterialResponse,
} from '@/types/endgames';

import { ConnectorArrows } from './EndgameOverallConnectorArrows';
import { EndgameMetricCard } from './EndgameMetricCard';
import { EndgameSkillCard } from './EndgameSkillCard';

const TILE_TESTIDS: Record<MaterialBucket, string> = {
  conversion: 'tile-conversion',
  parity: 'tile-parity',
  recovery: 'tile-recovery',
};

// Title-tooltip content per bucket. Lives next to the card title and explains
// the bucket's eval window, scoring rule, and gauge band semantics.
const GAUGE_BAND_BLURB = (
  <p>
    The <strong>gauge</strong> plots your rate against a fixed
    target band (blue = typical, red = below, green = above). Bands are
    calibrated from FlawChess Benchmark data and don't shift with filters,
    giving you a stable target you can chase as you improve.
  </p>
);

const TITLE_TOOLTIPS: Record<MaterialBucket, ReactNode> = {
  conversion: (
    <div className="space-y-2">
      <p>
        <strong>Conversion:</strong> your win rate (only wins count) when you
        entered the endgame with a Stockfish eval {'>='} +1.0 (you ahead).
      </p>
      {GAUGE_BAND_BLURB}
    </div>
  ),
  parity: (
    <div className="space-y-2">
      <p>
        <strong>Parity:</strong> your chess score (wins + half draws) when you
        entered the endgame with an eval between -1.0 and +1.0 (roughly
        balanced).
      </p>
      {GAUGE_BAND_BLURB}
    </div>
  ),
  recovery: (
    <div className="space-y-2">
      <p>
        <strong>Recovery:</strong> your save rate (wins + draws count) when you
        entered the endgame with an eval {'<='} -1.0 (you behind).
      </p>
      {GAUGE_BAND_BLURB}
    </div>
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

export function EndgameMetricsSection({ data }: { data: ScoreGapMaterialResponse }) {
  const gridRef = useRef<HTMLDivElement>(null);

  const totalMaterialGames = data.material_rows.reduce((sum, r) => sum + r.games, 0);

  const rowByBucket: Partial<Record<MaterialBucket, MaterialRow>> = {};
  for (const r of data.material_rows) rowByBucket[r.bucket] = r;

  return (
    <section data-testid="endgame-metrics-section">
      <p className="text-sm text-muted-foreground">
        Do you outperform the Stockfish baseline at converting, holding, and recovering?
      </p>

      {/* 3-column card grid on lg+, single-column stacked on mobile.
          DOM order: Conv -> Parity -> Recov -> Skill. On desktop the row-1 cards
          auto-place across the 3 columns; Skill is lifted to col 2 via
          lg:col-start-2 so it lands under Parity. `relative` anchors the
          ConnectorArrows SVG overlay (desktop only). */}
      <div
        ref={gridRef}
        className="relative grid grid-cols-1 lg:grid-cols-3 gap-4 mt-2"
      >
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
          tileTestId={TILE_TESTIDS['recovery']}
          titleTooltip={TITLE_TOOLTIPS['recovery']}
        />

        {/* Endgame Skill: lg:col-start-2 places it under Parity on desktop.
            On mobile (single column) it falls naturally after Recovery.
            lg:mt-8 matches the spacing above "Endgame Score Differences". */}
        <div className="lg:col-start-2 lg:mt-8">
          <EndgameSkillCard
            skill={data.section2_score_gap_skill_mean}
            totalGames={totalMaterialGames}
            scoreGapMean={data.section2_score_gap_skill_mean}
            scoreGapN={data.section2_score_gap_skill_n}
            scoreGapPValue={data.section2_score_gap_skill_p_value}
            scoreGapCiLow={data.section2_score_gap_skill_ci_low}
            scoreGapCiHigh={data.section2_score_gap_skill_ci_high}
            tileTestId="tile-endgame-skill"
          />
        </div>

        <ConnectorArrows
          containerRef={gridRef}
          leftCardTestId="tile-conversion"
          middleCardTestId="tile-parity"
          rightCardTestId="tile-recovery"
          targetTileTestId="tile-endgame-skill"
        />
      </div>
    </section>
  );
}
