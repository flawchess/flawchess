import * as React from "react"
import { useNavigate } from "react-router-dom"
import { FolderOpen } from "lucide-react"
import type { OpeningWDL } from "@/types/stats"
import { MinimapPopover } from "./MinimapPopover"
import { WDL_WIN, WDL_DRAW, WDL_LOSS, GLASS_OVERLAY } from "@/lib/theme"

// Minimum percentage to show label text inside a WDL bar segment
const MIN_PCT_FOR_LABEL = 15;

interface MostPlayedOpeningsTableProps {
  openings: OpeningWDL[];
  testIdPrefix: string;
}

/** Format opening name: split on ": " and insert line break if colon found. */
function formatName(name: string): React.ReactNode {
  const parts = name.split(": ");
  if (parts.length > 1) {
    return (
      <>
        <span className="font-medium">{parts[0]}:</span>
        <br />
        <span>{parts.slice(1).join(": ")}</span>
      </>
    );
  }
  return <span className="font-medium">{name}</span>;
}

function MiniWDLBar({ win_pct, draw_pct, loss_pct }: { win_pct: number; draw_pct: number; loss_pct: number }) {
  return (
    <div className="flex h-4 w-full min-w-[80px] overflow-hidden rounded-sm" data-testid="mini-wdl-bar">
      {win_pct > 0 && (
        <div
          className="relative flex items-center justify-center text-[10px] font-medium"
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
          className="relative flex items-center justify-center text-[10px] font-medium"
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
          className="relative flex items-center justify-center text-[10px] font-medium"
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

export function MostPlayedOpeningsTable({ openings, testIdPrefix }: MostPlayedOpeningsTableProps) {
  const navigate = useNavigate();

  if (openings.length === 0) return null;

  return (
    <div className="space-y-1" data-testid={`${testIdPrefix}-table`}>
      {openings.map((o) => (
        <div
          key={`${o.opening_eco}-${o.opening_name}`}
          className="grid grid-cols-[1fr_auto_minmax(80px,120px)] gap-2 items-center rounded px-2 py-1.5 hover:bg-white/5 transition-colors"
          data-testid={`${testIdPrefix}-row-${o.opening_eco}`}
        >
          {/* Column 1: ECO + Name + PGN */}
          <MinimapPopover fen={o.fen} testId={`${testIdPrefix}-minimap-${o.opening_eco}`}>
            <div className="min-w-0">
              <div className="text-sm leading-tight">
                <span className="text-muted-foreground mr-1.5">{o.opening_eco}</span>
                {formatName(o.opening_name)}
              </div>
              <div className="text-xs text-muted-foreground mt-0.5 truncate">{o.pgn}</div>
            </div>
          </MinimapPopover>

          {/* Column 2: Game count with link to games tab */}
          <button
            className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
            aria-label={`View ${o.total} games for ${o.opening_name}`}
            data-testid={`${testIdPrefix}-games-${o.opening_eco}`}
            onClick={() => navigate('/openings/games')}
          >
            <span className="tabular-nums">{o.total}</span>
            <FolderOpen className="h-3.5 w-3.5" />
          </button>

          {/* Column 3: Mini WDL bar */}
          <MiniWDLBar win_pct={o.win_pct} draw_pct={o.draw_pct} loss_pct={o.loss_pct} />
        </div>
      ))}
    </div>
  );
}
