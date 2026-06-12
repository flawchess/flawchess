import { useState } from 'react';
import {
  Swords,
  Calendar,
  Clock,
  Cpu,
  ExternalLink,
  Loader2,
} from 'lucide-react';
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

// Standalone component per D-05 (sibling to LibraryGameCard — do NOT import from it).
// formatDate copied verbatim from LibraryGameCard (same display requirements; D-05 forbids shared import).

// Board size — matches LibraryGameCard's DESKTOP_BOARD_SIZE.
const DESKTOP_BOARD_SIZE = 132;

// Severity → accent color mapping (left-spine and board arrow color)
const SEVERITY_COLOR: Record<FlawSeverity, string> = {
  blunder: SEV_BLUNDER,
  mistake: SEV_MISTAKE,
  inaccuracy: SEV_INACCURACY,
};

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

/**
 * Format a clock value (seconds) as mm:ss using floor division.
 * Mirrors the EvalChart formatClock local helper (D-05 forbids shared import).
 * Only called when clockSec is non-null.
 */
function formatClock(clockSec: number): string {
  const totalSec = Math.floor(clockSec);
  const minutes = Math.floor(totalSec / 60);
  const seconds = totalSec % 60;
  return `${minutes}:${seconds.toString().padStart(2, '0')}`;
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

  // Opponent: the side the user is NOT playing.
  const whiteName = flaw.white_username ?? '?';
  const blackName = flaw.black_username ?? '?';
  const opponentName = flaw.user_color === 'white' ? blackName : whiteName;
  const opponentRating =
    flaw.user_color === 'white'
      ? flaw.black_rating !== null
        ? `(${flaw.black_rating})`
        : ''
      : flaw.white_rating !== null
        ? `(${flaw.white_rating})`
        : '';
  // Square glyph: white square = white-piece side, black square = black-piece side.
  const opponentGlyph = flaw.user_color === 'white' ? '□' : '■';

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
  // Shows only the opponent: "vs <glyph><name> <rating>" on both desktop and mobile.
  const header = (
    <CardHeader as="h4" size="compact" className="rounded-t-md">
      <span className="truncate text-foreground min-w-0">
        <span className="text-muted-foreground font-normal">vs </span>
        {opponentGlyph} {opponentName} {opponentRating}
      </span>
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

  // Clock/move-time line: "<Clock icon> mm:ss · Move Ns" (matches the eval-chart tooltip).
  // Renders the clock part only when clock_seconds is non-null; the "· Move Ns" part
  // only when move_seconds is non-null. When both are null the item is falsy and
  // omitted from the metadata block.
  const clockMoveItem = (flaw.clock_seconds != null || flaw.move_seconds != null) && (
    <span className="inline-flex items-center gap-1">
      <Clock className="h-3.5 w-3.5" />
      {flaw.clock_seconds != null && formatClock(flaw.clock_seconds)}
      {flaw.clock_seconds != null && flaw.move_seconds != null && <span>&middot;</span>}
      {flaw.move_seconds != null && <span>Move {flaw.move_seconds.toFixed(1)}s</span>}
    </span>
  );

  // Shared game-info block:
  //   line 1: clock/move-time (when available)
  //   line 2: date
  // No TC or move count (replaced by clock context); no termination text.
  const metadata = (
    <div className="flex flex-col gap-1 text-sm text-muted-foreground">
      {clockMoveItem}
      {dateItem}
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
