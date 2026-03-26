/**
 * Endgame Performance section (D-03 through D-07):
 * - Two side-by-side WDL comparison bars (endgame vs non-endgame)
 * - Two semicircle gauge charts (Relative Endgame Strength, Endgame Skill)
 */

import { EndgameGauge } from '@/components/charts/EndgameGauge';
import { InfoPopover } from '@/components/ui/info-popover';
import { WDL_WIN, WDL_DRAW, WDL_LOSS } from '@/components/results/WDLBar';
import type { EndgamePerformanceResponse, EndgameWDLSummary } from '@/types/endgames';

// Glass-effect overlay copied locally to avoid coupling to EndgameWDLChart
const GLASS_OVERLAY =
  'linear-gradient(to bottom, rgba(255,255,255,0.35) 0%, rgba(255,255,255,0.05) 60%, rgba(0,0,0,0.05) 100%)';

// maxValue for Relative Endgame Strength gauge — above 100 is valid (can exceed overall win rate)
const RELATIVE_STRENGTH_MAX = 150;

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
      <div className="flex gap-3 text-xs text-muted-foreground">
        <span style={{ color: WDL_WIN }}>W: {wdl.win_pct.toFixed(1)}%</span>
        <span style={{ color: WDL_DRAW }}>D: {wdl.draw_pct.toFixed(1)}%</span>
        <span style={{ color: WDL_LOSS }}>L: {wdl.loss_pct.toFixed(1)}%</span>
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
            Relative Endgame Strength and Endgame Skill are computed from those rates.
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

      {/* Gauge charts (D-04, D-05, D-06) */}
      <div className="grid grid-cols-2 gap-4 sm:gap-8 mt-4" data-testid="perf-gauges">
        <div className="flex flex-col items-center gap-0">
          <div className="flex items-center gap-1 text-xs text-muted-foreground">
            <span>Relative Endgame Strength</span>
            <InfoPopover ariaLabel="Relative Endgame Strength info" testId="gauge-relative-strength-info" side="top">
              Your win rate in endgame games as a percentage of your overall win rate. 100% means identical
              performance; above 100% means you outperform your baseline in endgames.
            </InfoPopover>
          </div>
          <EndgameGauge
            value={data.relative_strength}
            maxValue={RELATIVE_STRENGTH_MAX}
            label="Relative Endgame Strength"
          />
        </div>
        <div className="flex flex-col items-center gap-0">
          <div className="flex items-center gap-1 text-xs text-muted-foreground">
            <span>Endgame Skill</span>
            <InfoPopover ariaLabel="Endgame Skill info" testId="gauge-endgame-skill-info" side="top">
              How often you win or draw when entering an endgame with a material advantage (conversion), or
              escape with a draw or win when at a deficit (recovery). Averaged across both metrics.
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
