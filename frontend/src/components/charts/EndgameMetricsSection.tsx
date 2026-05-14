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
 * v1.17 single-bullet doctrine: each card carries one peer bullet (vs 0) with
 * the mirror-bucket opponent baseline. Section-level h3 / InfoPopover were
 * dropped (D-10); the bucket-taxonomy explainer moves to the page-level h2
 * "Endgame Metrics and ELO" trigger in `Endgames.tsx` (D-11).
 */

import { useRef } from 'react';

import { MIRROR_BUCKET } from '@/lib/endgameMetrics';
import type {
  MaterialBucket,
  MaterialRow,
  ScoreGapMaterialResponse,
} from '@/types/endgames';

import { ConnectorArrows } from './EndgameOverallConnectorArrows';
import { EndgameMetricCard } from './EndgameMetricCard';
import { EndgameSkillCard } from './EndgameSkillCard';

// Buckets rendered as the row-1 cards, in DOM order. Mobile stacks them in
// this same order; on lg+ they auto-place across the 3 grid columns.
const ROW_ONE_BUCKETS: readonly MaterialBucket[] = ['conversion', 'parity', 'recovery'] as const;

// Per-bucket popover content (D-16, lifted verbatim from CONTEXT).
const METRIC_EXPLANATIONS: Record<MaterialBucket, string> = {
  conversion:
    "Your win rate (only wins count) when you entered the endgame with a Stockfish eval ≥ +1.0, compared to your opponents' Conversion against you.",
  parity:
    "Your chess score (wins + ½ draws) when you entered the endgame with an eval between −1.0 and +1.0, compared to your opponents' Parity against you.",
  recovery:
    "Your save rate (wins + draws count) when you entered the endgame with an eval ≤ −1.0, compared to your opponents' Recovery against you.",
};

// Popover names describe the BULLET-CHART metric (signed userRate − oppRate
// gap), distinct from the gauge labels which name the headline rate
// itself (Conversion / Parity / Recovery). The gauge shows your absolute rate;
// the popover and bullet chart show your gap vs the opponent baseline.
const METRIC_NAMES: Record<MaterialBucket, string> = {
  conversion: 'Conversion Gap',
  parity: 'Parity Gap',
  recovery: 'Recovery Gap',
};

const TILE_TESTIDS: Record<MaterialBucket, string> = {
  conversion: 'tile-conversion',
  parity: 'tile-parity',
  recovery: 'tile-recovery',
};

/** Synthesize a zero-row for buckets missing from the response. Lets
 * `EndgameMetricCard` render its empty-state branch (gauge at 0% with
 * opacity-50, no WDL bar, no peer-bullet row) cleanly without conditional
 * skipping at the orchestrator level. */
function buildZeroRow(bucket: MaterialBucket): MaterialRow {
  return {
    bucket,
    label: '',
    games: 0,
    win_pct: 0,
    draw_pct: 0,
    loss_pct: 0,
    score: 0,
    opponent_score: null,
    opponent_games: 0,
    diff_p_value: null,
    diff_ci_low: null,
    diff_ci_high: null,
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
        Do you outperform your opponents at converting, holding, and recovering?
      </p>

      {/* 3-column card grid on lg+, single-column stacked on mobile.
          DOM order: Conv → Parity → Recov → Skill. On desktop the row-1 cards
          auto-place across the 3 columns; Skill is lifted to col 2 via
          lg:col-start-2 so it lands under Parity. `relative` anchors the
          ConnectorArrows SVG overlay (desktop only). */}
      <div
        ref={gridRef}
        className="relative grid grid-cols-1 lg:grid-cols-3 gap-4 mt-2"
      >
        {ROW_ONE_BUCKETS.map((bucket) => {
          const row = rowByBucket[bucket] ?? buildZeroRow(bucket);
          const mirror = rowByBucket[MIRROR_BUCKET[bucket]];
          const sharePct =
            totalMaterialGames > 0 ? (row.games / totalMaterialGames) * 100 : 0;
          return (
            <EndgameMetricCard
              key={bucket}
              bucket={bucket}
              row={row}
              mirror={mirror}
              sharePct={sharePct}
              metricName={METRIC_NAMES[bucket]}
              metricExplanation={METRIC_EXPLANATIONS[bucket]}
              tileTestId={TILE_TESTIDS[bucket]}
            />
          );
        })}

        {/* Endgame Skill: lg:col-start-2 places it under Parity on desktop.
            On mobile (single column) it falls naturally after Recovery.
            lg:mt-8 matches the spacing above "Endgame Score Differences". */}
        <div className="lg:col-start-2 lg:mt-8">
          <EndgameSkillCard
            skill={data.skill ?? null}
            oppSkill={data.opp_skill ?? null}
            totalGames={totalMaterialGames}
            pValue={data.skill_diff_p_value ?? null}
            ciLow={data.skill_diff_ci_low ?? null}
            ciHigh={data.skill_diff_ci_high ?? null}
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
