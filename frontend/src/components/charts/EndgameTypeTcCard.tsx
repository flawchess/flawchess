/**
 * Phase 98 — Per-TC accordion item for the Endgame Type Breakdown section.
 *
 * Renders one `AccordionItem` with a full-bleed charcoal header (TC icon, TC
 * label, Games: X% count) and a responsive 4-tile grid body (rook / minor_piece
 * / pawn / queen in that fixed order). Mixed and pawnless are excluded. The
 * both-axes divider grammar (D-06/D-08) is implemented with per-cell conditional
 * border classes (not divide-x/divide-y, which bleed across wrapped rows).
 *
 * Layout staircase (D-07):
 *   Desktop (xl+): 4×1 — 3 vertical dividers between 4 columns.
 *   Tablet (sm–xl): 2×2 — 1 vertical divider between col-0/col-1 + 1 horizontal
 *                         divider between row-0/row-1.
 *   Mobile (< sm): 1×4 — 3 horizontal dividers between 4 stacked tiles.
 *
 * Games-floor suppression is the section orchestrator's responsibility
 * (EndgameTypeBreakdownSection). This component renders whatever `categories`
 * it receives.
 */

import { cn } from '@/lib/utils';

import { AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { TimeControlIcon } from '@/components/icons/TimeControlIcon';
import { EndgameTypeCard } from '@/components/charts/EndgameTypeCard';
import { HIDDEN_ENDGAME_CLASSES } from '@/lib/endgameMetrics';
import type { EndgameCategoryStats, EndgameClass } from '@/types/endgames';

// Human-readable time-control labels for accordion headers.
const TC_LABELS: Record<'bullet' | 'blitz' | 'rapid' | 'classical', string> = {
  bullet: 'Bullet',
  blitz: 'Blitz',
  rapid: 'Rapid',
  classical: 'Classical',
};

// Fixed tile render order (D-07/SC-3). Mixed is excluded (dropped per D-05 context);
// pawnless is excluded via HIDDEN_ENDGAME_CLASSES upstream.
const TILE_ORDER: EndgameClass[] = ['rook', 'minor_piece', 'pawn', 'queen'];

// Per-cell conditional border classes for the 4-tile both-axes divider grammar
// (D-08, Pitfall 4). Resolves breakpoint-specific classes for each tile index
// i in {0,1,2,3} across 3 layouts:
//
//   Mobile 1×4 (base): horizontal rule above tiles 1-3.
//   Tablet 2×2 (sm:): left-column tiles get border-r; bottom-row tiles get border-t.
//     Reset the mobile top rule on all cells via sm:border-t-0.
//   Desktop 4×1 (xl:): non-last columns get border-r; reset bottom-row top rule.
//     Reset the tablet top rule on all cells via xl:border-t-0.
//
// Divider color matches EndgameMetricsByTcCard: border-border/40 (D-06).
function tileDividerClasses(i: number): string {
  return cn(
    // Mobile: horizontal rule above every tile except the first.
    i > 0 && 'border-t border-border/40',

    // Tablet 2×2: reset mobile top rule, then add sm: rules.
    'sm:border-t-0',
    // Left column (i%2===0): right border between columns.
    i % 2 === 0 && 'sm:border-r sm:border-border/40',
    // Bottom row (i>=2): top border between rows.
    i >= 2 && 'sm:border-t sm:border-border/40',

    // Desktop 4×1: reset tablet top/right rules, add xl: right rule on non-last.
    'xl:border-t-0',
    i < 3 ? 'xl:border-r xl:border-border/40' : 'xl:border-r-0',
  );
}

export interface EndgameTypeTcCardProps {
  tc: 'bullet' | 'blitz' | 'rapid' | 'classical';
  categories: EndgameCategoryStats[];
  onCategorySelect: (cls: EndgameClass) => void;
}

export function EndgameTypeTcCard({
  tc,
  categories,
  onCategorySelect,
}: EndgameTypeTcCardProps) {
  // Build tile list in fixed order; exclude Mixed + pawnless.
  const tileMap = new Map(categories.map((c) => [c.endgame_class, c]));
  const tiles = TILE_ORDER.filter(
    (cls) => !HIDDEN_ENDGAME_CLASSES.has(cls) && cls !== 'mixed',
  )
    .map((cls) => tileMap.get(cls))
    .filter((c): c is EndgameCategoryStats => c !== undefined);

  const ENDGAME_CLASS_SLUGS: Record<EndgameClass, string> = {
    rook: 'rook',
    minor_piece: 'minor-piece',
    pawn: 'pawn',
    queen: 'queen',
    mixed: 'mixed',
    pawnless: 'pawnless',
  };

  return (
    <AccordionItem
      value={tc}
      data-testid={`endgame-type-tc-card-${tc}`}
      // Square off the bottom corners while expanded so the rounded shell doesn't
      // clip the tile-grid dividers (UAT 98: "don't round the bottom corners when
      // unfolded"); collapsed it stays fully rounded.
      className="charcoal-texture rounded-md overflow-hidden border-none data-[state=open]:rounded-b-none"
    >
      {/* Full-bleed charcoal header: TC icon + label + Games count (D-05).
          The AccordionTrigger IS the header — no extra px-4 on AccordionItem.
          AccordionTrigger renders a <button> with keyboard nav from Radix. */}
      <AccordionTrigger
        data-testid={`type-breakdown-tc-${tc}-trigger`}
        aria-label={`${TC_LABELS[tc]} endgame type breakdown`}
        // rounded-none + border-0 override the Radix primitive's rounded-lg and
        // all-side border so the header background fills the shell flush to its
        // edges (UAT 98: no charcoal corner/edge bleed when collapsed). The
        // bottom separator only appears while expanded, dividing header from tiles.
        className="w-full flex items-center gap-2 px-4 py-3 bg-black/20 border-0 rounded-none data-[state=open]:border-b data-[state=open]:border-b-border/40 text-left hover:no-underline [&>svg:last-child]:ml-0"
      >
        <div
          className="flex items-center gap-2 flex-1"
          data-testid={`type-breakdown-tc-${tc}-header`}
        >
          <TimeControlIcon timeControl={tc} className="h-4 w-4 shrink-0" />
          <h3 className="text-base font-semibold">{TC_LABELS[tc]}</h3>
        </div>
      </AccordionTrigger>

      {/* Tile grid body: no px-4 on AccordionContent (full-bleed header constraint,
          RESEARCH §7). The grid div carries its own p-4 padding.
          h-auto overrides the shared primitive's h-(--radix-accordion-content-height),
          which pins the body to the height measured at open time. Without this, a
          viewport resize that reflows the tile grid to more rows (e.g. 4×1 → 2×2)
          leaves the charcoal shell at its old height and clips the bottom row
          (UAT 98). h-auto lets the shell grow/shrink with the reflowed content. */}
      <AccordionContent className="h-auto p-0">
        {tiles.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4">
            {tiles.map((cat, i) => (
              <div
                key={cat.endgame_class}
                className={tileDividerClasses(i)}
              >
                <EndgameTypeCard
                  category={cat}
                  tc={tc}
                  onCategorySelect={onCategorySelect}
                  tileTestId={`type-card-${tc}-${ENDGAME_CLASS_SLUGS[cat.endgame_class]}`}
                />
              </div>
            ))}
          </div>
        ) : (
          <div className="p-4 text-sm text-muted-foreground">
            No endgame type data for this time control.
          </div>
        )}
      </AccordionContent>
    </AccordionItem>
  );
}
