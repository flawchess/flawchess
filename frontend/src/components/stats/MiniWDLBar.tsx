import { WDL_WIN, WDL_DRAW, WDL_LOSS, GLASS_OVERLAY } from "@/lib/theme"

// Minimum percentage to show label text inside a WDL bar segment
const MIN_PCT_FOR_LABEL = 15;

interface MiniWDLBarProps {
  win_pct: number;
  draw_pct: number;
  loss_pct: number;
  /** Bar height class, default "h-5" */
  heightClass?: string;
}

export function MiniWDLBar({ win_pct, draw_pct, loss_pct, heightClass = "h-5" }: MiniWDLBarProps) {
  return (
    <div className={`flex ${heightClass} w-full min-w-[80px] overflow-hidden rounded-sm`} data-testid="mini-wdl-bar">
      {win_pct > 0 && (
        <div
          className="relative flex items-center justify-center text-[11px] font-medium"
          style={{ width: `${win_pct}%`, backgroundColor: WDL_WIN }}
        >
          <div className="absolute inset-0" style={{ background: GLASS_OVERLAY }} />
          <span className="relative z-10 text-white drop-shadow-sm">
            {win_pct >= MIN_PCT_FOR_LABEL ? `${Math.round(win_pct)}%` : ""}
          </span>
        </div>
      )}
      {draw_pct > 0 && (
        <div
          className="relative flex items-center justify-center text-[11px] font-medium"
          style={{ width: `${draw_pct}%`, backgroundColor: WDL_DRAW }}
        >
          <div className="absolute inset-0" style={{ background: GLASS_OVERLAY }} />
          <span className="relative z-10 text-white drop-shadow-sm">
            {draw_pct >= MIN_PCT_FOR_LABEL ? `${Math.round(draw_pct)}%` : ""}
          </span>
        </div>
      )}
      {loss_pct > 0 && (
        <div
          className="relative flex items-center justify-center text-[11px] font-medium"
          style={{ width: `${loss_pct}%`, backgroundColor: WDL_LOSS }}
        >
          <div className="absolute inset-0" style={{ background: GLASS_OVERLAY }} />
          <span className="relative z-10 text-white drop-shadow-sm">
            {loss_pct >= MIN_PCT_FOR_LABEL ? `${Math.round(loss_pct)}%` : ""}
          </span>
        </div>
      )}
    </div>
  );
}
