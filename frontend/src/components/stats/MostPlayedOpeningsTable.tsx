import * as React from "react"
import { FolderOpen, ChevronDown, ChevronUp } from "lucide-react"
import type { OpeningWDL } from "@/types/stats"
import { MinimapPopover } from "./MinimapPopover"
import { MiniWDLBar } from "./MiniWDLBar"
import { Tooltip } from "@/components/ui/tooltip"

// Number of openings to show before the "More" fold
const INITIAL_VISIBLE_COUNT = 3;

interface MostPlayedOpeningsTableProps {
  openings: OpeningWDL[];
  color: "white" | "black";
  testIdPrefix: string;
  /** Called when user clicks the games link on a row. Receives the full opening object so callers can route on any field. */
  onOpenGames: (opening: OpeningWDL, color: "white" | "black") => void;
  /** When true, render every opening without the collapsible "X more" fold. */
  showAll?: boolean;
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

function OpeningRow({ o, color, index, testIdPrefix, rowKey, onOpenGames }: {
  o: OpeningWDL;
  color: "white" | "black";
  index: number;
  testIdPrefix: string;
  rowKey: string;
  onOpenGames: (opening: OpeningWDL, color: "white" | "black") => void;
}) {
  const isEvenRow = index % 2 === 0;

  return (
    <div
      className={`grid grid-cols-[1fr_auto_minmax(80px,140px)] sm:grid-cols-[minmax(0,1fr)_auto_minmax(120px,200px)] gap-2 items-center rounded px-2 py-1.5 hover:bg-white/5 transition-colors ${isEvenRow ? 'bg-white/[0.02]' : ''}`}
      data-testid={`${testIdPrefix}-row-${rowKey}`}
    >
      {/* Column 1: Name + PGN */}
      <MinimapPopover
        fen={o.fen}
        boardOrientation={color}
        testId={`${testIdPrefix}-minimap-${rowKey}`}
      >
        <div className="min-w-0">
          <div className="text-sm leading-tight">
            {formatName(o.opening_name)}
          </div>
          {o.pgn && (
            <div className="text-xs text-muted-foreground mt-0.5 break-words sm:truncate">{o.pgn}</div>
          )}
        </div>
      </MinimapPopover>

      {/* Column 2: Game count with link to games tab */}
      <Tooltip content={`View ${o.total} games for ${o.opening_name}`}>
        <button
          className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
          aria-label={`View ${o.total} games for ${o.opening_name}`}
          data-testid={`${testIdPrefix}-games-${rowKey}`}
          onClick={() => onOpenGames(o, color)}
        >
          <span className="tabular-nums">{o.total}</span>
          <FolderOpen className="h-3.5 w-3.5" />
        </button>
      </Tooltip>

      {/* Column 3: Mini WDL bar */}
      <MiniWDLBar win_pct={o.win_pct} draw_pct={o.draw_pct} loss_pct={o.loss_pct} />
    </div>
  );
}

export function MostPlayedOpeningsTable({ openings, color, testIdPrefix, onOpenGames, showAll = false }: MostPlayedOpeningsTableProps) {
  const [expanded, setExpanded] = React.useState(false);

  if (openings.length === 0) return null;

  const visibleOpenings = showAll || expanded ? openings : openings.slice(0, INITIAL_VISIBLE_COUNT);
  const hiddenCount = openings.length - INITIAL_VISIBLE_COUNT;
  const hasMore = !showAll && hiddenCount > 0;

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
        {visibleOpenings.map((o, i) => {
          const rowKey = o.opening_eco || o.full_hash || `${o.opening_name}-${i}`;
          return (
            <OpeningRow
              key={rowKey}
              o={o}
              color={color}
              index={i}
              testIdPrefix={testIdPrefix}
              rowKey={rowKey}
              onOpenGames={onOpenGames}
            />
          );
        })}
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

