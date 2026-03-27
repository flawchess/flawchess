import { ExternalLink } from 'lucide-react';
import { Link } from 'react-router-dom';
import { InfoPopover } from '@/components/ui/info-popover';
import { WDL_WIN, WDL_DRAW, WDL_LOSS, GLASS_OVERLAY, MIN_GAMES_FOR_RELIABLE_STATS, UNRELIABLE_OPACITY } from '@/lib/theme';
import { cn } from '@/lib/utils';
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
  mixed: 'Endgames with pieces from two or more families (e.g. queen + rook, rook + knight).',
  pawnless: 'Endgames with no pawns on the board — only kings and pieces.',
};

interface CategoryData {
  endgame_class: EndgameClass;
  label: string;
  slug: string;
  wins: number;
  draws: number;
  losses: number;
  win_pct: number;
  draw_pct: number;
  loss_pct: number;
  total: number;
}

interface CategoryRowProps {
  cat: CategoryData;
  maxTotal: number;
  onCategorySelect: (category: EndgameClass) => void;
}

function EndgameCategoryRow({
  cat,
  maxTotal,
  onCategorySelect,
}: CategoryRowProps) {
  return (
    <div
      className="rounded px-2 py-1.5"
      data-testid={`endgame-category-${cat.slug}`}
    >
      {/* Category label with per-type info popover and game count + link */}
      <div className="flex items-center justify-between mb-1">
        <span className="inline-flex items-center gap-1">
          <span className="text-sm font-medium">{cat.label}</span>
          <InfoPopover
            ariaLabel={`${cat.label} endgame type info`}
            testId={`endgame-type-info-${cat.slug}`}
            side="top"
          >
            {ENDGAME_TYPE_DESCRIPTIONS[cat.endgame_class]}
          </InfoPopover>
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="text-xs text-muted-foreground">
            {cat.total} games
            {cat.total < MIN_GAMES_FOR_RELIABLE_STATS && (
              <span className="text-amber-500 ml-1" title="Small sample size — percentages may be unreliable">
                (low)
              </span>
            )}
          </span>
          <Link
            to="/endgames/games"
            onClick={() => onCategorySelect(cat.endgame_class)}
            className="text-muted-foreground hover:text-foreground transition-colors"
            aria-label={`View ${cat.label} endgame games`}
            data-testid={`endgame-games-link-${cat.slug}`}
          >
            <ExternalLink className="h-3.5 w-3.5" />
          </Link>
        </span>
      </div>

      {/* Stacked WDL bar with glass overlay — dimmed for low sample size categories */}
      <div
        className={cn('flex h-5 w-full overflow-hidden rounded mb-0')}
        style={cat.total < MIN_GAMES_FOR_RELIABLE_STATS ? { opacity: UNRELIABLE_OPACITY } : undefined}
      >
        {cat.win_pct > 0 && (
          <div
            className="transition-all"
            style={{ width: `${cat.win_pct}%`, backgroundColor: WDL_WIN, backgroundImage: GLASS_OVERLAY }}
          />
        )}
        {cat.draw_pct > 0 && (
          <div
            className="transition-all"
            style={{ width: `${cat.draw_pct}%`, backgroundColor: WDL_DRAW, backgroundImage: GLASS_OVERLAY }}
          />
        )}
        {cat.loss_pct > 0 && (
          <div
            className="transition-all"
            style={{ width: `${cat.loss_pct}%`, backgroundColor: WDL_LOSS, backgroundImage: GLASS_OVERLAY }}
          />
        )}
      </div>

      {/* Grey-outlined game count bar — proportional to max category total */}
      <div className="h-2 mt-0.5 mb-1">
        <div
          className="h-full rounded-sm"
          style={{
            width: `${(cat.total / maxTotal) * 100}%`,
            border: '1px solid oklch(0.6 0 0)',
            backgroundColor: 'transparent',
          }}
        />
      </div>

      {/* WDL stats with game counts — dimmed for low sample size categories */}
      <div
        className="flex justify-center gap-3 text-sm"
        style={cat.total < MIN_GAMES_FOR_RELIABLE_STATS ? { opacity: UNRELIABLE_OPACITY } : undefined}
      >
        <span style={{ color: WDL_WIN }}>W: {cat.wins} ({Math.round(cat.win_pct)}%)</span>
        <span style={{ color: WDL_DRAW }}>D: {cat.draws} ({Math.round(cat.draw_pct)}%)</span>
        <span style={{ color: WDL_LOSS }}>L: {cat.losses} ({Math.round(cat.loss_pct)}%)</span>
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
    endgame_class: cat.endgame_class,
    label: cat.label,
    slug: CLASS_TO_SLUG[cat.endgame_class],
    wins: cat.wins,
    draws: cat.draws,
    losses: cat.losses,
    win_pct: cat.win_pct,
    draw_pct: cat.draw_pct,
    loss_pct: cat.loss_pct,
    total: cat.total,
  }));

  const maxTotal = Math.max(...categories.map((c) => c.total));

  return (
    <div data-testid="endgame-wdl-chart">
      <h2 className="text-lg font-medium mb-3">
        <span className="inline-flex items-center gap-1">
          Results by Endgame Type
          <InfoPopover ariaLabel="Results by endgame type info" testId="endgame-chart-info" side="top">
            Shows your win, draw, and loss percentages for each endgame type, based on games
            that reached an endgame phase (at most 6 major/minor pieces on the board). Click the link icon to view matching games.
          </InfoPopover>
        </span>
      </h2>

      {/* Per-category rows with game links */}
      <div className="space-y-2">
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
