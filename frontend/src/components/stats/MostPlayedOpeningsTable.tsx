import * as React from "react"
import { FolderOpen, ChevronDown, ChevronUp } from "lucide-react"
import type { OpeningWDL } from "@/types/stats"
import { MinimapPopover } from "./MinimapPopover"
import { MiniWDLBar } from "./MiniWDLBar"

// Number of openings to show before the "More" fold
const INITIAL_VISIBLE_COUNT = 3;

interface MostPlayedOpeningsTableProps {
  openings: OpeningWDL[];
  color: "white" | "black";
  testIdPrefix: string;
  /** Load PGN moves onto the board and navigate to games tab */
  onOpenGames: (pgn: string, color: "white" | "black") => void;
}

/** Format opening name: split on ": " — line break only on mobile. */
function formatName(name: string): React.ReactNode {
  const parts = name.split(": ");
  if (parts.length > 1) {
    return (
      <>
        <span className="font-medium">{parts[0]}:</span>
        {/* Line break on mobile only, space on desktop */}
        <br className="sm:hidden" />
        <span className="hidden sm:inline"> </span>
        <span>{parts.slice(1).join(": ")}</span>
      </>
    );
  }
  return <span className="font-medium">{name}</span>;
}

function OpeningRow({ o, color, index, testIdPrefix, onOpenGames }: {
  o: OpeningWDL;
  color: "white" | "black";
  index: number;
  testIdPrefix: string;
  onOpenGames: (pgn: string, color: "white" | "black") => void;
}) {
  const isEvenRow = index % 2 === 0;

  return (
    <div
      className={`grid grid-cols-[1fr_auto_minmax(80px,140px)] sm:grid-cols-[minmax(0,1fr)_auto_minmax(120px,200px)] gap-2 items-center rounded px-2 py-1.5 hover:bg-white/5 transition-colors ${isEvenRow ? 'bg-white/[0.02]' : ''}`}
      data-testid={`${testIdPrefix}-row-${o.opening_eco}`}
    >
      {/* Column 1: ECO + Name + PGN */}
      <MinimapPopover
        fen={o.fen}
        boardOrientation={color}
        testId={`${testIdPrefix}-minimap-${o.opening_eco}`}
      >
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
        onClick={() => onOpenGames(o.pgn, color)}
      >
        <span className="tabular-nums">{o.total}</span>
        <FolderOpen className="h-3.5 w-3.5" />
      </button>

      {/* Column 3: Mini WDL bar */}
      <MiniWDLBar win_pct={o.win_pct} draw_pct={o.draw_pct} loss_pct={o.loss_pct} />
    </div>
  );
}

export function MostPlayedOpeningsTable({ openings, color, testIdPrefix, onOpenGames }: MostPlayedOpeningsTableProps) {
  const [expanded, setExpanded] = React.useState(false);

  if (openings.length === 0) return null;

  const visibleOpenings = expanded ? openings : openings.slice(0, INITIAL_VISIBLE_COUNT);
  const hiddenCount = openings.length - INITIAL_VISIBLE_COUNT;
  const hasMore = hiddenCount > 0;

  return (
    <div data-testid={`${testIdPrefix}-table`}>
      {/* Table header */}
      <div className="grid grid-cols-[1fr_auto_minmax(80px,140px)] sm:grid-cols-[minmax(0,1fr)_auto_minmax(120px,200px)] gap-2 px-2 pb-1 text-xs text-muted-foreground border-b border-white/10 mb-1">
        <span>Name</span>
        <span>Games</span>
        <span>Win / Draw / Loss</span>
      </div>

      {/* Rows */}
      <div>
        {visibleOpenings.map((o, i) => (
          <OpeningRow
            key={`${o.opening_eco}-${o.opening_name}`}
            o={o}
            color={color}
            index={i}
            testIdPrefix={testIdPrefix}
            onOpenGames={onOpenGames}
          />
        ))}
      </div>

      {/* More/Less toggle */}
      {hasMore && (
        <button
          className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors mt-2 px-2"
          onClick={() => setExpanded(!expanded)}
          data-testid={`${testIdPrefix}-btn-more`}
          aria-label={expanded ? "Show fewer openings" : `Show ${hiddenCount} more openings`}
        >
          {expanded ? (
            <>
              <ChevronUp className="h-4 w-4" />
              Less
            </>
          ) : (
            <>
              <ChevronDown className="h-4 w-4" />
              {hiddenCount} more
            </>
          )}
        </button>
      )}
    </div>
  );
}

