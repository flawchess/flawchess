/**
 * Endgame Performance section (D-03 through D-07):
 * - Two side-by-side WDL comparison bars (endgame vs non-endgame)
 * - Three semicircle gauge charts (Conversion, Recovery, Endgame Skill) in a single row
 */

import { EndgameGauge, type GaugeZone } from '@/components/charts/EndgameGauge';
import { InfoPopover } from '@/components/ui/info-popover';
import { WDL_WIN, WDL_DRAW, WDL_LOSS, GLASS_OVERLAY, GAUGE_DANGER, GAUGE_WARNING, GAUGE_SUCCESS } from '@/lib/theme';
import type { EndgamePerformanceResponse, EndgameWDLSummary } from '@/types/endgames';

// Material advantage/deficit threshold in pawn points (backend uses 300 centipawns)
export const MATERIAL_ADVANTAGE_POINTS = 3;

// Per-gauge zone definitions — thresholds differ per metric, colors from theme constants
const CONVERSION_ZONES: GaugeZone[] = [
  { from: 0,    to: 0.6,  color: GAUGE_DANGER },
  { from: 0.6,  to: 0.8,  color: GAUGE_WARNING },
  { from: 0.8,  to: 1.0,  color: GAUGE_SUCCESS },
];

const RECOVERY_ZONES: GaugeZone[] = [
  { from: 0,    to: 0.1,  color: GAUGE_DANGER },
  { from: 0.1,  to: 0.3,  color: GAUGE_WARNING },
  { from: 0.3,  to: 1.0,  color: GAUGE_SUCCESS },
];

const ENDGAME_SKILL_ZONES: GaugeZone[] = [
  { from: 0,    to: 0.4,  color: GAUGE_DANGER },
  { from: 0.4,  to: 0.6,  color: GAUGE_WARNING },
  { from: 0.6,  to: 1.0,  color: GAUGE_SUCCESS },
];

interface WDLRowProps {
  label: string;
  wdl: EndgameWDLSummary;
  testId: string;
}

function WDLRow({ label, wdl, testId }: WDLRowProps) {
  return (
    <div className="space-y-1" data-testid={testId}>
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium">{label}</span>
        <span className="text-xs text-muted-foreground">{wdl.total} games</span>
      </div>
      <div className="flex h-5 w-full overflow-hidden rounded">
        {wdl.win_pct > 0 && (
          <div
            className="transition-all"
            style={{ width: `${wdl.win_pct}%`, backgroundColor: WDL_WIN, backgroundImage: GLASS_OVERLAY }}
          />
        )}
        {wdl.draw_pct > 0 && (
          <div
            className="transition-all"
            style={{ width: `${wdl.draw_pct}%`, backgroundColor: WDL_DRAW, backgroundImage: GLASS_OVERLAY }}
          />
        )}
        {wdl.loss_pct > 0 && (
          <div
            className="transition-all"
            style={{ width: `${wdl.loss_pct}%`, backgroundColor: WDL_LOSS, backgroundImage: GLASS_OVERLAY }}
          />
        )}
      </div>
      <div className="flex justify-center gap-3 text-sm">
        <span style={{ color: WDL_WIN }}>W: {wdl.wins} ({Math.round(wdl.win_pct)}%)</span>
        <span style={{ color: WDL_DRAW }}>D: {wdl.draws} ({Math.round(wdl.draw_pct)}%)</span>
        <span style={{ color: WDL_LOSS }}>L: {wdl.losses} ({Math.round(wdl.loss_pct)}%)</span>
      </div>
    </div>
  );
}

interface EndgamePerformanceSectionProps {
  data: EndgamePerformanceResponse;
}

export function EndgamePerformanceSection({ data }: EndgamePerformanceSectionProps) {
  return (
    <div className="space-y-4">
      <h3 className="text-base font-semibold">
        <span className="inline-flex items-center gap-1">
          Endgame Performance
          <InfoPopover ariaLabel="Endgame Performance info" testId="perf-section-info" side="top">
            Compares your win/draw/loss rates in games that reached an endgame phase versus those that did not.
            Conversion, Recovery, and Endgame Skill are computed from your material advantage/deficit rates.
          </InfoPopover>
        </span>
      </h3>

      {/* WDL comparison bars (D-03) */}
      <div className="space-y-3">
        <WDLRow
          label="Endgame games"
          wdl={data.endgame_wdl}
          testId="perf-wdl-endgame"
        />
        <WDLRow
          label="Non-endgame games"
          wdl={data.non_endgame_wdl}
          testId="perf-wdl-non-endgame"
        />
      </div>

      {/* Gauge charts: Conversion, Recovery, Endgame Skill (D-04, D-05, D-06) */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 sm:gap-4 mt-8 mb-6" data-testid="perf-gauges">

        {/* Conversion gauge */}
        <div className="flex flex-col items-center gap-0">
          <div className="relative z-10 flex items-center gap-1 text-sm text-foreground text-center">
            <span>Conversion</span>
            <InfoPopover ariaLabel="Conversion info" testId="gauge-conversion-info" side="top">
              Your win rate when entering an endgame with a material advantage of at least {MATERIAL_ADVANTAGE_POINTS} points.
            </InfoPopover>
          </div>
          <EndgameGauge
            value={data.aggregate_conversion_pct}
            label="Conversion"
            zones={CONVERSION_ZONES}
          />
        </div>

        {/* Recovery gauge */}
        <div className="flex flex-col items-center gap-0">
          <div className="relative z-10 flex items-center gap-1 text-sm text-foreground text-center">
            <span>Recovery</span>
            <InfoPopover ariaLabel="Recovery info" testId="gauge-recovery-info" side="top">
              Your draw or win rate when entering an endgame with a material deficit of at least {MATERIAL_ADVANTAGE_POINTS} points.
            </InfoPopover>
          </div>
          <EndgameGauge
            value={data.aggregate_recovery_pct}
            label="Recovery"
            zones={RECOVERY_ZONES}
          />
        </div>

        {/* Endgame Skill gauge */}
        <div className="flex flex-col items-center gap-0">
          <div className="relative z-10 flex items-center gap-1 text-sm text-foreground text-center">
            <span>Endgame Skill</span>
            <InfoPopover ariaLabel="Endgame Skill info" testId="gauge-endgame-skill-info" side="top">
              A weighted average of your conversion rate (60%) and recovery rate (40%). Measures overall endgame proficiency.
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
