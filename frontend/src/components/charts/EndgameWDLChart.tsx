import { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { InfoPopover } from '@/components/ui/info-popover';
import { Collapsible, CollapsibleTrigger, CollapsibleContent } from '@/components/ui/collapsible';
import { WDL_WIN, WDL_DRAW, WDL_LOSS } from '@/components/results/WDLBar';
import { cn } from '@/lib/utils';
import type { EndgameCategoryStats, EndgameClass } from '@/types/endgames';

interface EndgameWDLChartProps {
  categories: EndgameCategoryStats[];
  selectedCategory: EndgameClass | null;
  onCategoryClick: (category: EndgameClass) => void;
  onSelectedCategoryClick: () => void;
}

// Glass-effect overlay matching WDLBar.tsx
const GLASS_OVERLAY =
  'linear-gradient(to bottom, rgba(255,255,255,0.35) 0%, rgba(255,255,255,0.05) 60%, rgba(0,0,0,0.05) 100%)';

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

const MIN_GAMES_FOR_RELIABLE_STATS = 10;

function formatConversionMetric(pct: number, saves: number, games: number): string {
  if (games === 0) return '—';
  return `${pct.toFixed(0)}% (${saves}/${games})`;
}

interface CategoryData {
  endgame_class: EndgameClass;
  label: string;
  slug: string;
  win_pct: number;
  draw_pct: number;
  loss_pct: number;
  total: number;
  conversion_pct: number;
  conversion_games: number;
  conversion_wins: number;
  conversion_draws: number;
  conversion_losses: number;
  recovery_pct: number;
  recovery_games: number;
  recovery_saves: number;
  recovery_wins: number;
  recovery_draws: number;
}

interface CategoryRowProps {
  cat: CategoryData;
  isSelected: boolean;
  maxTotal: number;
  conversionText: string;
  recoveryText: string;
  hasConvRecov: boolean;
  onCategoryClick: (category: EndgameClass) => void;
  onSelectedCategoryClick: () => void;
}

function EndgameCategoryRow({
  cat,
  isSelected,
  maxTotal,
  conversionText,
  recoveryText,
  hasConvRecov,
  onCategoryClick,
  onSelectedCategoryClick,
}: CategoryRowProps) {
  const [moreOpen, setMoreOpen] = useState(false);

  // Conversion: 3-segment bar (win / draw / loss)
  const convWinPct = cat.conversion_games > 0 ? (cat.conversion_wins / cat.conversion_games) * 100 : 0;
  const convDrawPct = cat.conversion_games > 0 ? (cat.conversion_draws / cat.conversion_games) * 100 : 0;
  const convLossPct = cat.conversion_games > 0 ? (cat.conversion_losses / cat.conversion_games) * 100 : 0;

  // Recovery: 3-segment bar (win / draw / loss)
  const recvWinPct = cat.recovery_games > 0 ? (cat.recovery_wins / cat.recovery_games) * 100 : 0;
  const recvDrawPct = cat.recovery_games > 0 ? (cat.recovery_draws / cat.recovery_games) * 100 : 0;
  const recvLosses = cat.recovery_games - cat.recovery_wins - cat.recovery_draws;
  const recvLossPct = cat.recovery_games > 0 ? (recvLosses / cat.recovery_games) * 100 : 0;

  return (
    <div
      className={cn(
        'rounded px-2 py-1.5 transition-colors',
        isSelected
          ? 'bg-muted/50 ring-1 ring-primary/40'
          : 'hover:bg-muted/30',
      )}
    >
      <button
        data-testid={`endgame-category-${cat.slug}`}
        aria-pressed={isSelected}
        aria-label={`${cat.label} endgame category`}
        onClick={() => {
          if (isSelected) {
            onSelectedCategoryClick();
          } else {
            onCategoryClick(cat.endgame_class);
          }
        }}
        className="w-full text-left cursor-pointer"
      >
        {/* Category label with per-type info popover and game count */}
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
          <span className="text-xs text-muted-foreground">
            {cat.total} games
            {cat.total < MIN_GAMES_FOR_RELIABLE_STATS && (
              <span className="text-xs text-amber-500 ml-1" title="Small sample size — percentages may be unreliable">
                (low sample)
              </span>
            )}
          </span>
        </div>

        {/* Stacked WDL bar with glass overlay — dimmed for low sample size categories */}
        <div className={cn('flex h-5 w-full overflow-hidden rounded mb-0', cat.total < MIN_GAMES_FOR_RELIABLE_STATS && 'opacity-50')}>
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

        {/* WDL percentages */}
        <div className="flex gap-3 text-xs text-muted-foreground">
          <span style={{ color: WDL_WIN }}>W: {cat.win_pct.toFixed(0)}%</span>
          <span style={{ color: WDL_DRAW }}>D: {cat.draw_pct.toFixed(0)}%</span>
          <span style={{ color: WDL_LOSS }}>L: {cat.loss_pct.toFixed(0)}%</span>
        </div>
      </button>

      {/* Collapsible conversion/recovery section */}
      {hasConvRecov && (
        <Collapsible open={moreOpen} onOpenChange={setMoreOpen}>
          <CollapsibleTrigger asChild>
            <button
              data-testid={`endgame-more-${cat.slug}`}
              className="flex items-center gap-0.5 text-[11px] text-muted-foreground mt-1 cursor-pointer hover:text-foreground transition-colors"
            >
              More
              {moreOpen ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
            </button>
          </CollapsibleTrigger>
          <CollapsibleContent>
            <div className="mt-1.5 space-y-1.5">
              {/* Conversion W/D/L bar */}
              {cat.conversion_games > 0 && (
                <div>
                  <p className="text-[11px] text-muted-foreground mb-0.5">
                    Conversion: {conversionText}
                  </p>
                  <div className="flex h-3 w-full overflow-hidden rounded">
                    {convWinPct > 0 && <div style={{ width: `${convWinPct}%`, backgroundColor: WDL_WIN }} />}
                    {convDrawPct > 0 && <div style={{ width: `${convDrawPct}%`, backgroundColor: WDL_DRAW }} />}
                    {convLossPct > 0 && <div style={{ width: `${convLossPct}%`, backgroundColor: WDL_LOSS }} />}
                  </div>
                </div>
              )}

              {/* Recovery W/D/L bar */}
              {cat.recovery_games > 0 && (
                <div>
                  <p className="text-[11px] text-muted-foreground mb-0.5">
                    Recovery: {recoveryText}
                  </p>
                  <div className="flex h-3 w-full overflow-hidden rounded">
                    {recvWinPct > 0 && <div style={{ width: `${recvWinPct}%`, backgroundColor: WDL_WIN }} />}
                    {recvDrawPct > 0 && <div style={{ width: `${recvDrawPct}%`, backgroundColor: WDL_DRAW }} />}
                    {recvLossPct > 0 && <div style={{ width: `${recvLossPct}%`, backgroundColor: WDL_LOSS }} />}
                  </div>
                </div>
              )}
            </div>
          </CollapsibleContent>
        </Collapsible>
      )}
    </div>
  );
}

export function EndgameWDLChart({
  categories,
  selectedCategory,
  onCategoryClick,
  onSelectedCategoryClick,
}: EndgameWDLChartProps) {
  // Backend already sorts by total desc — transform for display
  const data = categories.map((cat) => ({
    endgame_class: cat.endgame_class,
    label: cat.label,
    slug: CLASS_TO_SLUG[cat.endgame_class],
    win_pct: cat.win_pct,
    draw_pct: cat.draw_pct,
    loss_pct: cat.loss_pct,
    wins: cat.wins,
    draws: cat.draws,
    losses: cat.losses,
    total: cat.total,
    conversion_pct: cat.conversion.conversion_pct,
    conversion_games: cat.conversion.conversion_games,
    conversion_wins: cat.conversion.conversion_wins,
    conversion_draws: cat.conversion.conversion_draws,
    conversion_losses: cat.conversion.conversion_losses,
    recovery_pct: cat.conversion.recovery_pct,
    recovery_games: cat.conversion.recovery_games,
    recovery_saves: cat.conversion.recovery_saves,
    recovery_wins: cat.conversion.recovery_wins,
    recovery_draws: cat.conversion.recovery_draws,
  }));

  const maxTotal = Math.max(...categories.map((c) => c.total));

  return (
    <div data-testid="endgame-wdl-chart">
      <h2 className="text-lg font-medium mb-3">
        <span className="inline-flex items-center gap-1">
          Results by Endgame Type
          <InfoPopover ariaLabel="Results by endgame type info" testId="endgame-chart-info" side="top">
            <p className="mb-2">
              Shows your win, draw, and loss percentages for each endgame type, based on games that reached that endgame.
            </p>

            <p className="mb-2">
              Endgame phase is defined as positions where the total count of major and minor pieces
              (queens, rooks, bishops, knights) across both sides is at most 6. Kings and pawns are not counted.
              This follows the Lichess definition.
            </p>

            <p className="mb-2">
              <strong>Conversion</strong> is your win rate when you entered the endgame with a material advantage. <br/>
              <strong>Recovery</strong> is your draw+win rate when you entered with a material deficit.
            </p>

            <p>
              Click a row to select it and view details. Click the same row again to jump to matching games.
            </p>
          </InfoPopover>
        </span>
      </h2>

      {/* Per-category clickable rows with collapsible conversion/recovery */}
      <div className="space-y-2">
        {data.map((cat) => {
          const isSelected = selectedCategory === cat.endgame_class;
          const conversionText = formatConversionMetric(cat.conversion_pct, cat.conversion_wins, cat.conversion_games);
          const recoveryText = formatConversionMetric(cat.recovery_pct, cat.recovery_saves, cat.recovery_games);
          const hasConvRecov = cat.conversion_games > 0 || cat.recovery_games > 0;

          return (
            <EndgameCategoryRow
              key={cat.endgame_class}
              cat={cat}
              isSelected={isSelected}
              maxTotal={maxTotal}
              conversionText={conversionText}
              recoveryText={recoveryText}
              hasConvRecov={hasConvRecov}
              onCategoryClick={onCategoryClick}
              onSelectedCategoryClick={onSelectedCategoryClick}
            />
          );
        })}
      </div>
    </div>
  );
}
