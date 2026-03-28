import { InfoPopover } from '@/components/ui/info-popover';
import { WDLChartRow } from '@/components/charts/WDLChartRow';
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
        showLowWarning={true}
        testId={`endgame-category-${cat.slug}-row`}
      />
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
      <h2 className="text-lg font-medium mb-3">
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
