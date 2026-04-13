/**
 * Endgame Performance section (D-03 through D-07):
 * - Two side-by-side WDL comparison bars (endgame vs non-endgame)
 * - Three semicircle gauge charts (Conversion, Recovery, Endgame Skill) in a single row
 */

import { EndgameGauge, type GaugeZone } from '@/components/charts/EndgameGauge';
import { InfoPopover } from '@/components/ui/info-popover';
import { WDLChartRow } from '@/components/charts/WDLChartRow';
import { MiniWDLBar } from '@/components/stats/MiniWDLBar';
import { GAUGE_DANGER, GAUGE_WARNING, GAUGE_SUCCESS } from '@/lib/theme';
import type { EndgamePerformanceResponse, EndgameWDLSummary } from '@/types/endgames';

// Material advantage/deficit threshold in pawn points (backend uses 100 centipawns)
export const MATERIAL_ADVANTAGE_POINTS = 1;

// Persistence requirement in full moves (= 4 plies on the backend)
export const PERSISTENCE_MOVES = 2;

// Per-gauge zone definitions — thresholds differ per metric, colors from theme constants
const CONVERSION_ZONES: GaugeZone[] = [
  { from: 0,    to: 0.5,  color: GAUGE_DANGER },
  { from: 0.5,  to: 0.7,  color: GAUGE_WARNING },
  { from: 0.7,  to: 1.0,  color: GAUGE_SUCCESS },
];

const RECOVERY_ZONES: GaugeZone[] = [
  { from: 0,    to: 0.15,  color: GAUGE_DANGER },
  { from: 0.15,  to: 0.35, color: GAUGE_WARNING },
  { from: 0.35, to: 1.0,  color: GAUGE_SUCCESS },
];

const ENDGAME_SKILL_ZONES: GaugeZone[] = [
  { from: 0,    to: 0.4,  color: GAUGE_DANGER },
  { from: 0.4,  to: 0.6,  color: GAUGE_WARNING },
  { from: 0.6,  to: 1.0,  color: GAUGE_SUCCESS },
];

interface EndgamePerformanceSectionProps {
  data: EndgamePerformanceResponse;
}

// Desktop-only single-row layout: label | games count | constrained MiniWDLBar.
// Matches the Openings Stats (MostPlayedOpeningsTable) column pattern.
function PerfWDLDesktopRow({
  label,
  pct,
  data,
  testId,
}: {
  label: string;
  pct: string;
  data: EndgameWDLSummary;
  testId: string;
}) {
  return (
    <div
      className="grid grid-cols-[minmax(0,1fr)_auto_minmax(120px,200px)] gap-3 items-center py-1.5"
      data-testid={testId}
    >
      <span className="text-sm font-medium truncate">{label}</span>
      <span className="text-xs text-muted-foreground tabular-nums whitespace-nowrap">
        {pct}% ({data.total}) games
      </span>
      {data.total === 0 ? (
        <div className="h-5 rounded bg-muted" />
      ) : (
        <MiniWDLBar win_pct={data.win_pct} draw_pct={data.draw_pct} loss_pct={data.loss_pct} />
      )}
    </div>
  );
}

export function EndgamePerformanceSection({ data }: EndgamePerformanceSectionProps) {
  const totalGames = data.endgame_wdl.total + data.non_endgame_wdl.total;
  const endgamePct = totalGames > 0 ? (data.endgame_wdl.total / totalGames * 100).toFixed(1) : '0.0';
  const nonEndgamePct = totalGames > 0 ? (data.non_endgame_wdl.total / totalGames * 100).toFixed(1) : '0.0';

  return (
    <div className="space-y-4">
      <h3 className="text-base font-semibold">
        <span className="inline-flex items-center gap-1">
          Endgame vs. Non-Endgame Games
          <InfoPopover ariaLabel="Endgame vs. Non-Endgame Games info" testId="perf-section-info" side="top">
            Compares your win/draw/loss rates in games that reached an endgame phase versus those that did not.
          </InfoPopover>
        </span>
      </h3>

      {/* WDL comparison bars (D-03) */}
      {/* Desktop (lg+): label | games count | constrained WDL bar on a single row */}
      <div className="hidden lg:block">
        <PerfWDLDesktopRow
          label="Endgame games"
          pct={endgamePct}
          data={data.endgame_wdl}
          testId="perf-wdl-endgame"
        />
        <PerfWDLDesktopRow
          label="Non-endgame games"
          pct={nonEndgamePct}
          data={data.non_endgame_wdl}
          testId="perf-wdl-non-endgame"
        />
      </div>
      {/* Mobile (<lg): stacked full-width WDL bars below headers */}
      <div className="lg:hidden space-y-3">
        <WDLChartRow
          data={data.endgame_wdl}
          label="Endgame games"
          gameCountLabel={<>{endgamePct}% ({data.endgame_wdl.total}) games</>}
          testId="perf-wdl-endgame"
        />
        <WDLChartRow
          data={data.non_endgame_wdl}
          label="Non-endgame games"
          gameCountLabel={<>{nonEndgamePct}% ({data.non_endgame_wdl.total}) games</>}
          testId="perf-wdl-non-endgame"
        />
      </div>
    </div>
  );
}

/**
 * Gauge charts for Conversion, Recovery, and Endgame Skill.
 * Split from EndgamePerformanceSection for layout flexibility.
 */
export function EndgameGaugesSection({ data }: EndgamePerformanceSectionProps) {
  return (
    <div className="space-y-4">
      <h3 className="text-base font-semibold">
        Conversion, Recovery, and Endgame Skill
      </h3>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 sm:gap-4 mb-2" data-testid="perf-gauges">

        {/* Conversion gauge */}
        <div className="flex flex-col items-center gap-0">
          <div className="relative z-10 flex items-center gap-1 text-sm text-foreground text-center">
            <span>Conversion</span>
            <InfoPopover ariaLabel="Conversion info" testId="gauge-conversion-info" side="top">
              Percentage of endgame sequences with a material advantage of at least {MATERIAL_ADVANTAGE_POINTS} point (persisted for at least {PERSISTENCE_MOVES} moves) where you went on to win the game. Measures how well you close out winning endgames.
            </InfoPopover>
          </div>
          <EndgameGauge
            value={data.aggregate_conversion_pct}
            label="Conversion"
            zones={CONVERSION_ZONES}
          />
          <span className="-mt-1 text-xs text-muted-foreground">({data.aggregate_conversion_wins} of {data.aggregate_conversion_games} sequences)</span>
        </div>

        {/* Recovery gauge */}
        <div className="flex flex-col items-center gap-0">
          <div className="relative z-10 flex items-center gap-1 text-sm text-foreground text-center">
            <span>Recovery</span>
            <InfoPopover ariaLabel="Recovery info" testId="gauge-recovery-info" side="top">
              Percentage of endgame sequences with a material deficit of at least {MATERIAL_ADVANTAGE_POINTS} point (persisted for at least {PERSISTENCE_MOVES} moves) where you went on to draw or win the game. Measures how well you defend losing endgames.
            </InfoPopover>
          </div>
          <EndgameGauge
            value={data.aggregate_recovery_pct}
            label="Recovery"
            zones={RECOVERY_ZONES}
          />
          <span className="-mt-1 text-xs text-muted-foreground">({data.aggregate_recovery_saves} of {data.aggregate_recovery_games} sequences)</span>
        </div>

        {/* Endgame Skill gauge */}
        <div className="flex flex-col items-center gap-0">
          <div className="relative z-10 flex items-center gap-1 text-sm text-foreground text-center">
            <span>Endgame Skill</span>
            <InfoPopover ariaLabel="Endgame Skill info" testId="gauge-endgame-skill-info" side="top">
              A weighted average of your conversion rate (70%) and recovery rate (30%). Measures overall endgame proficiency.
            </InfoPopover>
          </div>
          <EndgameGauge
            value={data.endgame_skill}
            label="Endgame Skill"
            zones={ENDGAME_SKILL_ZONES}
          />
        </div>

      </div>
    </div>
  );
}
