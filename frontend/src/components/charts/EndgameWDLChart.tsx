import { Link } from 'react-router-dom';
import { FolderOpen } from 'lucide-react';
import { InfoPopover } from '@/components/ui/info-popover';
import { WDLChartRow } from '@/components/charts/WDLChartRow';
import { MiniWDLBar } from '@/components/stats/MiniWDLBar';
import { Tooltip } from '@/components/ui/tooltip';
import {
  MIN_GAMES_FOR_RELIABLE_STATS,
  UNRELIABLE_OPACITY,
} from '@/lib/theme';
import type { EndgameCategoryStats, EndgameClass } from '@/types/endgames';

interface EndgameWDLChartProps {
  categories: EndgameCategoryStats[];
  onCategorySelect: (category: EndgameClass) => void;
}

// Map EndgameClass to slug used in data-testid
const CLASS_TO_SLUG: Record<EndgameClass, string> = {
  rook: 'rook',
  minor_piece: 'minor-piece',
  pawn: 'pawn',
  queen: 'queen',
  mixed: 'mixed',
  pawnless: 'pawnless',
};

const ENDGAME_TYPE_DESCRIPTIONS: Record<EndgameClass, string> = {
  rook: 'Endgames with rooks as the only non-king, non-pawn pieces. The most common endgame type besides Mixed.',
  minor_piece: 'Endgames with bishops and/or knights as the only non-king, non-pawn pieces.',
  pawn: 'King and pawn endgames only — no other pieces remain on the board.',
  queen: 'Endgames where queens are the only non-king, non-pawn pieces.',
  mixed: 'Endgames with pieces from two or more piece types — rooks, minor pieces (bishops/knights), and queens (e.g. queen + rook, rook + knight).',
  pawnless: 'Endgames with no pawns on the board — only kings and pieces.',
};

// Mobile (<lg): stacked full-width WDL bar via WDLChartRow.
function EndgameCategoryRow({ cat, maxTotal, onCategorySelect }: {
  cat: EndgameCategoryStats & { slug: string };
  maxTotal: number;
  onCategorySelect: (category: EndgameClass) => void;
}) {
  return (
    <div className="rounded px-2 py-1.5" data-testid={`endgame-category-${cat.slug}`}>
      <WDLChartRow
        data={cat}
        label={cat.label}
        infoPopover={
          <InfoPopover
            ariaLabel={`${cat.label} endgame type info`}
            testId={`endgame-type-info-${cat.slug}`}
            side="top"
          >
            {ENDGAME_TYPE_DESCRIPTIONS[cat.endgame_class]}
          </InfoPopover>
        }
        gamesLink="/endgames/games"
        onGamesLinkClick={() => onCategorySelect(cat.endgame_class)}
        gamesLinkTestId={`endgame-games-link-${cat.slug}`}
        gamesLinkAriaLabel={`View ${cat.label} endgame games`}
        maxTotal={maxTotal}
        testId={`endgame-category-${cat.slug}-row`}
      />
    </div>
  );
}

// Desktop (lg+): single-row layout with label | games link | constrained MiniWDLBar.
// Mirrors the Openings Stats (MostPlayedOpeningsTable) column pattern so WDL bars
// don't stretch the full viewport width.
function EndgameCategoryRowDesktop({ cat, maxTotal, onCategorySelect, isEvenRow }: {
  cat: EndgameCategoryStats & { slug: string };
  maxTotal: number;
  onCategorySelect: (category: EndgameClass) => void;
  isEvenRow: boolean;
}) {
  const isUnreliable = cat.total < MIN_GAMES_FOR_RELIABLE_STATS;

  return (
    <div
      className={`grid grid-cols-[minmax(0,1fr)_auto_minmax(120px,200px)] gap-3 items-center rounded px-2 py-1.5 ${isEvenRow ? 'bg-white/[0.02]' : ''}`}
      data-testid={`endgame-category-${cat.slug}-row`}
    >
      {/* Column 1: label + info popover */}
      <span className="inline-flex items-center gap-1 min-w-0">
        <span className="text-sm font-medium truncate">{cat.label}</span>
        <InfoPopover
          ariaLabel={`${cat.label} endgame type info`}
          testId={`endgame-type-info-${cat.slug}`}
          side="top"
        >
          {ENDGAME_TYPE_DESCRIPTIONS[cat.endgame_class]}
        </InfoPopover>
      </span>

      {/* Column 2: games link */}
      <Tooltip content={`View ${cat.label} endgame games`}>
        <Link
          to="/endgames/games"
          onClick={() => onCategorySelect(cat.endgame_class)}
          className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors whitespace-nowrap"
          aria-label={`View ${cat.label} endgame games`}
          data-testid={`endgame-games-link-${cat.slug}`}
        >
          <span className="tabular-nums">{cat.total} games{isUnreliable && ' (low)'}</span>
          <FolderOpen className="h-3.5 w-3.5" />
        </Link>
      </Tooltip>

      {/* Column 3: MiniWDL bar + proportional frequency bar below */}
      <div style={isUnreliable ? { opacity: UNRELIABLE_OPACITY } : undefined}>
        {cat.total === 0 ? (
          <div className="h-5 rounded bg-muted" />
        ) : (
          <MiniWDLBar win_pct={cat.win_pct} draw_pct={cat.draw_pct} loss_pct={cat.loss_pct} />
        )}
        {maxTotal > 0 && (
          <div className="h-2 mt-0.5">
            <div
              className="h-full rounded-sm"
              style={{
                width: `${(cat.total / maxTotal) * 100}%`,
                border: '1px solid oklch(0.6 0 0)',
                backgroundColor: 'transparent',
              }}
            />
          </div>
        )}
      </div>
    </div>
  );
}

export function EndgameWDLChart({
  categories,
  onCategorySelect,
}: EndgameWDLChartProps) {
  // Backend already sorts by total desc — transform for display
  const data = categories.map((cat) => ({
    ...cat,
    slug: CLASS_TO_SLUG[cat.endgame_class],
  }));

  const maxTotal = Math.max(...categories.map((c) => c.total));

  return (
    <div data-testid="endgame-wdl-chart">
      <div className="mb-3">
        <h2 className="text-lg font-medium">
          <span className="inline-flex items-center gap-1">
            Results by Endgame Type
            <InfoPopover ariaLabel="Results by endgame type info" testId="endgame-chart-info" side="top">
              <div className="space-y-2">
                <p>
                  Shows your win, draw, and loss percentages for each endgame type, based on games
              that included the endgame type. Note that a game can include more than one type of endgame.
                </p>
                <p>
                  Click the link icon to view matching games.
                </p>
              </div>
            </InfoPopover>
          </span>
        </h2>
        <p className="text-sm text-muted-foreground mt-1">
          Win/draw/loss rate for each endgame type — a game can count toward multiple types.
        </p>
      </div>

      {/* Desktop (lg+): single-row grid layout matching Openings Stats pattern */}
      <div className="hidden lg:block">
        {data.map((cat, i) => (
          <div key={cat.endgame_class} data-testid={`endgame-category-${cat.slug}`}>
            <EndgameCategoryRowDesktop
              cat={cat}
              maxTotal={maxTotal}
              onCategorySelect={onCategorySelect}
              isEvenRow={i % 2 === 0}
            />
          </div>
        ))}
      </div>
      {/* Mobile (<lg): stacked full-width WDL bars */}
      <div className="lg:hidden space-y-2">
        {data.map((cat) => (
          <EndgameCategoryRow
            key={cat.endgame_class}
            cat={cat}
            maxTotal={maxTotal}
            onCategorySelect={onCategorySelect}
          />
        ))}
      </div>
    </div>
  );
}
