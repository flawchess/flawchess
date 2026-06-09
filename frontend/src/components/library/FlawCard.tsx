import { useState } from 'react';
import {
  Swords,
  Calendar,
  Clock,
  Cpu,
  Equal,
  ExternalLink,
  Hash,
  Loader2,
  Minus,
  Plus,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';
import { SEV_BLUNDER, SEV_MISTAKE, SEV_INACCURACY } from '@/lib/theme';
import { Card, CardHeader } from '@/components/ui/card';
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog';
import { LoadError } from '@/components/ui/load-error';
import { Tooltip } from '@/components/ui/tooltip';
import { PlatformIcon } from '@/components/icons/PlatformIcon';
import { LazyMiniBoard } from '@/components/board/LazyMiniBoard';
import { LibraryGameCard } from '@/components/results/LibraryGameCard';
import { SeverityBadge } from '@/components/library/SeverityBadge';
import { TagChip, TagLegend } from '@/components/library/TagChip';
import { flawPlyUrl } from '@/lib/platformLinks';
import { sanToSquares } from '@/lib/sanToSquares';
import { formatMoveNotation } from '@/lib/openingInsights';
import { formatFlawEvalParts } from '@/lib/formatFlawEval';
import { useLibraryGame } from '@/hooks/useLibrary';
import type { FlawListItem, FlawSeverity } from '@/types/library';
import type { UserResult } from '@/types/api';

// Standalone component per D-05 (sibling to LibraryGameCard — do NOT import from it).
// formatDate / formatTimeControl copied verbatim from LibraryGameCard (same display requirements).

// Board size — matches LibraryGameCard's DESKTOP_BOARD_SIZE.
const DESKTOP_BOARD_SIZE = 132;

// Severity → accent color mapping (left-spine and board arrow color)
const SEVERITY_COLOR: Record<FlawSeverity, string> = {
  blunder: SEV_BLUNDER,
  mistake: SEV_MISTAKE,
  inaccuracy: SEV_INACCURACY,
};

// Result indicator: colored chip with +/=/− icon
const RESULT_CLASSES: Record<UserResult, string> = {
  win: 'bg-green-600/20 text-green-400 border-green-600/30',
  draw: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
  loss: 'bg-red-600/20 text-red-400 border-red-600/30',
};
const RESULT_ICONS: Record<UserResult, LucideIcon> = { win: Plus, draw: Equal, loss: Minus };

// Copied verbatim from LibraryGameCard.tsx — same display requirements (D-05 forbids shared import).
function formatDate(dateStr: string | null): string {
  if (!dateStr) return '—';
  try {
    return new Date(dateStr).toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  } catch {
    return dateStr;
  }
}

const SECONDS_PER_DAY = 86400;

// Copied verbatim from LibraryGameCard.tsx — same display requirements (D-05 forbids shared import).
function formatTimeControl(tcStr: string): string {
  // PGN daily/correspondence format: "1/{seconds_per_move}" (e.g. "1/259200" = 3 days/move).
  if (tcStr.startsWith('1/')) {
    const secondsPerMove = Number(tcStr.slice(2));
    const days = Math.round(secondsPerMove / SECONDS_PER_DAY);
    return `${days}d`;
  }
  if (tcStr.includes('+')) {
    const [baseSec, inc] = tcStr.split('+');
    const baseMin = Math.floor(Number(baseSec) / 60);
    return `${baseMin}+${inc}`;
  }
  // No increment — just convert seconds to minutes
  const baseMin = Math.floor(Number(tcStr) / 60);
  return String(baseMin);
}

/**
 * FlawCard — one flawed-move card for the Flaws subtab grid.
 *
 * Replicates the LibraryGameCard visual language: banded header with player
 * names + ratings + exact-ply platform deep-link, 132px miniboard with the
 * flaw-move arrow, standard-notation move + user-POV eval swing, severity
 * badge, family-colored tag chips, TagLegend, and metadata.
 *
 * "View game" button/modal added in 112-04 — a right-aligned secondary "Game"
 * button lives in the card header and opens the modal.
 *
 * Security: user-provided strings (usernames, platform_url) are React children
 * or href (auto-escaped). platform link uses target=_blank + rel=noopener
 * noreferrer (T-112-06 reverse-tabnabbing guard).
 */
export function FlawCard({ flaw }: { flaw: FlawListItem }) {
  const [open, setOpen] = useState(false);
  const { data, isLoading, isError } = useLibraryGame(open ? flaw.game_id : null);

  const flipped = flaw.user_color === 'black';
  const severityColor = SEVERITY_COLOR[flaw.severity];

  // Flaw-move arrow: augment board_fen() to a full FEN (side-to-move + unknown
  // castling/en-passant) so chess.js can resolve the move's from/to squares.
  const sideToMove = flaw.user_color === 'black' ? 'b' : 'w';
  const moveSquares = flaw.move_san
    ? sanToSquares(`${flaw.fen} ${sideToMove} - - 0 1`, flaw.move_san)
    : null;

  // Move notation — shared primitive (D-04, no local helper).
  const moveNotation = flaw.move_san
    ? formatMoveNotation(flaw.ply, flaw.move_san)
    : `Ply ${flaw.ply}`;

  // Eval swing — user-POV negated for black (Pitfall 3). Rendered as
  // "<move> <padding> <Cpu icon><before> to <after>".
  const { before: evalBefore, after: evalAfter } = formatFlawEvalParts(
    flaw.eval_cp_before,
    flaw.eval_mate_before,
    flaw.eval_cp_after,
    flaw.eval_mate_after,
    flaw.user_color,
  );

  const whiteName = flaw.white_username ?? '?';
  const blackName = flaw.black_username ?? '?';
  const whiteRating = flaw.white_rating !== null ? `(${flaw.white_rating})` : '';
  const blackRating = flaw.black_rating !== null ? `(${flaw.black_rating})` : '';

  // Result indicator
  const ResultIcon = RESULT_ICONS[flaw.user_result];
  const resultIndicator = (
    <span
      className={cn(
        'inline-flex items-center justify-center rounded border h-3.5 w-3.5 shrink-0',
        RESULT_CLASSES[flaw.user_result],
      )}
      aria-label={flaw.user_result}
    >
      <ResultIcon className="h-2.5 w-2.5" strokeWidth={3} />
    </span>
  );

  // "View game" trigger — opens the Dialog modal with the full LibraryGameCard.
  // Lives in the header (right-aligned) as a text link (semantically a button
  // since it opens a modal rather than navigating).
  const viewGameButton = (
    <button
      type="button"
      className="ml-auto shrink-0 inline-flex items-center gap-1 text-sm text-brand-brown-light hover:text-brand-brown-highlight transition-colors"
      data-testid={`flaw-card-view-game-${flaw.game_id}-${flaw.ply}`}
      aria-label={`View full game for ${whiteName} vs ${blackName}`}
      onClick={() => setOpen(true)}
    >
      <Swords className="h-3.5 w-3.5" />
      Game
    </button>
  );

  // Platform icon + exact-ply deep link (D-12, T-112-06)
  const flawUrl = flawPlyUrl(flaw.platform, flaw.platform_url, flaw.ply, flaw.user_color);
  const platformIconAndLink = (
    <span className="shrink-0 flex items-center gap-1.5 text-muted-foreground">
      <PlatformIcon platform={flaw.platform} className="h-4 w-4" />
      {flawUrl ? (
        <Tooltip content="Open at this move on platform">
          <a
            href={flawUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-brand-brown-light hover:text-brand-brown-highlight transition-colors"
            aria-label="Open at this move on platform"
            data-testid={`flaw-card-platform-link-${flaw.game_id}-${flaw.ply}`}
          >
            <ExternalLink className="h-4 w-4" />
          </a>
        </Tooltip>
      ) : null}
    </span>
  );

  // HEADER — banded title bar via CardHeader (compact size).
  // rounded-t-md because the card uses overflowVisible (needed for any future
  // tooltip children that escape the card border).
  // Desktop: single line "■ White (rating) vs □ Black (rating)"; mobile: two stacked lines.
  const header = (
    <CardHeader as="h4" size="compact" className="rounded-t-md">
      <span className="hidden sm:block truncate text-foreground min-w-0">
        ■ {whiteName} {whiteRating}
        <span className="mx-1.5 text-muted-foreground font-normal">vs</span>□ {blackName}{' '}
        {blackRating}
      </span>
      <div className="flex sm:hidden min-w-0 flex-1 flex-col text-foreground">
        <span className="truncate">■ {whiteName} {whiteRating}</span>
        <span className="truncate">□ {blackName} {blackRating}</span>
      </div>
      {viewGameButton}
      {platformIconAndLink}
    </CardHeader>
  );

  // Metadata items
  const dateItem = flaw.played_at && (
    <span className="inline-flex items-center gap-1">
      <Calendar className="h-3.5 w-3.5" />
      {formatDate(flaw.played_at)}
    </span>
  );

  const timeControlItem = flaw.time_control_bucket && (
    <span className="inline-flex items-center gap-1">
      <Clock className="h-3.5 w-3.5" />
      <span className="capitalize">{flaw.time_control_bucket}</span>
      {flaw.time_control_str ? ` ${formatTimeControl(flaw.time_control_str)}` : ''}
    </span>
  );

  const moveCountItem = flaw.move_count !== null && (
    <span className="inline-flex items-center gap-1">
      <Hash className="h-3.5 w-3.5" />
      {flaw.move_count}
      {/* "Moves" label is desktop-only; mobile shows just "# <n>" to save width. */}
      <span className="hidden sm:inline">&nbsp;Moves</span>
    </span>
  );

  const terminationItem = flaw.termination && flaw.termination !== 'unknown' && (
    <span className="inline-flex items-center gap-1 capitalize">
      {resultIndicator}
      {flaw.termination}
    </span>
  );

  // Shared game-info block (same order on every game card):
  //   line 1: "<TC name> <base>[+inc]" • "# n Moves" — the two parts wrap at the
  //           bullet when the column is too narrow for one line.
  //   line 2: date
  //   line 3: termination (result chip + reason)
  const metadata = (
    <div className="flex flex-col gap-1 text-sm text-muted-foreground">
      {/* TC + move count share a line, separated by a gap; they wrap onto
          separate lines (no dangling separator) when the column is too narrow. */}
      <div className="flex flex-wrap items-center gap-x-3 gap-y-0.5">
        {timeControlItem}
        {moveCountItem}
      </div>
      {dateItem}
      {terminationItem}
    </div>
  );

  return (
    <Card
      as="article"
      accentColor={severityColor}
      overflowVisible
      data-testid={`flaw-card-${flaw.game_id}-${flaw.ply}`}
    >
      {header}
      {/* Board + content sit in a row; the tags row carries basis-full so it always
          wraps onto its own full-width row below board+content (at every width). */}
      <div className="flex flex-wrap gap-3 items-start p-3">
        {/* Column 1 — 132px miniboard showing the position BEFORE the flaw with the flaw-move arrow */}
        <LazyMiniBoard
          fen={flaw.fen}
          flipped={flipped}
          size={DESKTOP_BOARD_SIZE}
          arrows={
            moveSquares
              ? [{ from: moveSquares.from, to: moveSquares.to, color: SEV_BLUNDER }]
              : undefined
          }
        />

        {/* Column 2 — move/eval, metadata, action */}
        <div className="flex flex-col gap-1.5 min-w-0 flex-1">
          {/* Move notation on its own line, eval swing on the line below:
              "<move>" / "<Cpu icon><before> to <after>" */}
          <div className="flex flex-col gap-0.5 text-sm">
            <span className="text-foreground font-medium">{moveNotation}</span>
            <span className="inline-flex items-center gap-1 text-muted-foreground">
              <Cpu className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
              {evalBefore} to {evalAfter}
            </span>
          </div>

          {/* Metadata block */}
          {metadata}
        </div>

        {/* Tags row — severity badge, family-colored tag chips, and a single "Tags"
            legend. Always rendered (every flaw has a severity). basis-full makes it a
            full-width wrapping row below board+content with the severity badge, chips,
            and "Tags" legend all inline. */}
        <div className="flex flex-wrap items-center gap-1.5 basis-full">
          {/* Severity badge — singular, count-less (one flaw per card). */}
          <SeverityBadge
            severity={flaw.severity}
            count={1}
            gameId={flaw.game_id}
            showCount={false}
          />

          {flaw.tags.length > 0 && (
            // display:contents so the chips + legend flow inline with the severity
            // badge on the single wrapping row.
            <div className="contents">
              {flaw.tags.map((tag) => (
                <TagChip key={tag} tag={tag} gameId={flaw.game_id} definition={false} />
              ))}
              <TagLegend tags={flaw.tags} gameId={flaw.game_id} label="Tags" />
            </div>
          )}
        </div>
      </div>

      {/* View-game Dialog modal — fetches lazily on open via useLibraryGame */}
      <Dialog open={open} onOpenChange={(v) => !v && setOpen(false)}>
        <DialogContent
          // no-scrollbar: the EvalChart tooltip (allowEscapeViewBox y=true) renders
          // downward and overhangs the chart. When the modal is content-height (the
          // common single-card case) that overhang spills past the scroll container,
          // making overflow-y-auto flash a scrollbar (and reflow). Hiding the bar keeps
          // wheel/touch scroll for genuinely tall cards while killing the flicker.
          // sm:p-6: more breathing room around the card on desktop.
          // max-w-[calc(100%-1rem)]: near-full-width on mobile (0.5rem side gutters,
          // overriding DialogContent's default 1rem) so the wide game card has room.
          className="no-scrollbar max-w-[calc(100%-1rem)] sm:max-w-4xl overflow-y-auto max-h-[90vh] sm:p-6"
          data-testid="flaw-game-modal"
          aria-label="View full game"
        >
          <DialogTitle className="sr-only">Full game view</DialogTitle>
          {isLoading && (
            <div className="flex justify-center p-8">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          )}
          {isError && <LoadError resource="game" variant="centered" />}
          {/* min-w-0: DialogContent is a CSS grid, whose items default to
              min-width:auto and won't shrink below the card's intrinsic width. The
              embedded recharts EvalChart then overflows the modal (horizontal scroll
              on mobile). Constraining the grid item lets the w-full chart track the
              modal width instead. */}
          {data && (
            <div className="min-w-0">
              {/* focusPly: pulse the clicked flaw's marker on the modal's eval chart
                  so the eye lands on it on open (yields to hover — see LibraryGameCard). */}
              <LibraryGameCard game={data} focusPly={flaw.ply} />
            </div>
          )}
        </DialogContent>
      </Dialog>
    </Card>
  );
}
