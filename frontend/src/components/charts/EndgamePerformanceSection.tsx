/**
 * Endgame Performance section (D-03 through D-07):
 * - Two side-by-side WDL comparison bars (endgame vs non-endgame)
 * - Three semicircle gauge charts (Conversion, Recovery, Endgame Skill) in a single row
 */

import { EndgameGauge, type GaugeZone } from '@/components/charts/EndgameGauge';
import { InfoPopover } from '@/components/ui/info-popover';
import { WDL_WIN, WDL_DRAW, WDL_LOSS } from '@/components/results/WDLBar';
import type { EndgamePerformanceResponse, EndgameWDLSummary } from '@/types/endgames';

// Glass-effect overlay copied locally to avoid coupling to EndgameWDLChart
const GLASS_OVERLAY =
  'linear-gradient(to bottom, rgba(255,255,255,0.35) 0%, rgba(255,255,255,0.05) 60%, rgba(0,0,0,0.05) 100%)';

// Material advantage/deficit threshold in pawn points (backend uses 300 centipawns)
export const MATERIAL_ADVANTAGE_POINTS = 3;

// Per-gauge zone definitions
const CONVERSION_ZONES: GaugeZone[] = [
  { from: 0,    to: 0.5,  color: 'oklch(0.55 0.20 25)' },   // red
  { from: 0.5,  to: 0.7,  color: 'oklch(0.65 0.18 80)' },   // amber
  { from: 0.7,  to: 1.0,  color: 'oklch(0.55 0.17 145)' },  // green
];

const RECOVERY_ZONES: GaugeZone[] = [
  { from: 0,    to: 0.2,  color: 'oklch(0.55 0.20 25)' },   // red
  { from: 0.2,  to: 0.4,  color: 'oklch(0.65 0.18 80)' },   // amber
  { from: 0.4,  to: 1.0,  color: 'oklch(0.55 0.17 145)' },  // green
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
      <div className="grid grid-cols-3 gap-2 sm:gap-4 mt-4" data-testid="perf-gauges">

        {/* Conversion gauge */}
        <div className="flex flex-col items-center gap-0">
          <div className="flex items-center gap-1 text-xs text-muted-foreground text-center mb-0.5">
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
          <div className="flex items-center gap-1 text-xs text-muted-foreground text-center mb-0.5">
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
          <div className="flex items-center gap-1 text-xs text-muted-foreground text-center mb-0.5">
            <span>Endgame Skill</span>
            <InfoPopover ariaLabel="Endgame Skill info" testId="gauge-endgame-skill-info" side="top">
              A weighted average of your conversion rate (60%) and recovery rate (40%). Measures overall endgame proficiency.
            </InfoPopover>
          </div>
          <EndgameGauge
            value={data.endgame_skill}
            label="Endgame Skill"
          />
        </div>

      </div>
    </div>
  );
}
