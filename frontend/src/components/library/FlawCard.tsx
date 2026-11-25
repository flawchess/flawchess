import type { ReactNode } from 'react';
import { Link } from 'react-router';
import { Search, Clock } from 'lucide-react';
import {
  SEV_BLUNDER,
  SEV_MISTAKE,
  SEV_INACCURACY,
  BEST_MOVE_ARROW,
  TAC_MISSED,
  TAC_ALLOWED,
  TAC_MISSED_LABEL,
  TAC_ALLOWED_LABEL,
} from '@/lib/theme';
import { Card, CardHeader } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Tooltip } from '@/components/ui/tooltip';
import { PlatformIcon } from '@/components/icons/PlatformIcon';
import { LazyMiniBoard } from '@/components/board/LazyMiniBoard';
import { SeverityBadge } from '@/components/library/SeverityBadge';
import { isFacepalmBlunder } from '@/lib/facepalm';
import { FacepalmBadgePopover } from '@/components/library/FacepalmBadgePopover';
import { ChipPopover } from '@/components/library/ChipPopover';
import { TagChip } from '@/components/library/TagChip';
import { platformPlyUrl } from '@/lib/platformLinks';
import { sanToSquares, uciToSquares } from '@/lib/sanToSquares';
import {
  TACTIC_FAMILY_FOR_MOTIF,
  tacticDepthBadge,
  tacticMotifDefinition,
  tacticMotifLabel,
} from '@/lib/tacticComparisonMeta';
import { TAG_DEFINITIONS } from '@/lib/tagDefinitions';
import { getTagFamily } from '@/lib/tagVisuals';
import { cn } from '@/lib/utils';
import { formatMoveNotation } from '@/lib/openingInsights';
import { useFlawBoardSize } from '@/hooks/useFlawBoardSize';
import { TacticMotifChip } from '@/components/library/TacticMotifChip';
import { buildGameAnalysisUrl } from '@/lib/analysisUrl';
import { trackFeature } from '@/lib/analytics';
import type { FlawListItem, FlawSeverity, FlawTag, TacticOrientation } from '@/types/library';

// Standalone component (sibling to LibraryGameCard — does not import from it).

/** Move times below this show one decimal ("8.4s"), longer ones whole seconds ("62s"). */
const MOVE_TIME_DECIMAL_MAX_SECONDS = 10;

// Severity → accent color mapping (left-spine and board arrow color)
const SEVERITY_COLOR: Record<FlawSeverity, string> = {
  blunder: SEV_BLUNDER,
  mistake: SEV_MISTAKE,
  inaccuracy: SEV_INACCURACY,
};

// Copied verbatim from LibraryGameCard.tsx — same display requirements; the two
// cards are standalone siblings and share no import.
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
 * Mirrors the EvalChart formatClock local helper (kept local, no shared import).
 * Only called when clockSec is non-null.
 */
function formatClock(clockSec: number): string {
  const totalSec = Math.floor(clockSec);
  const minutes = Math.floor(totalSec / 60);
  const seconds = totalSec % 60;
  return `${minutes}:${seconds.toString().padStart(2, '0')}`;
}

// Hover affordance for a chip that is a popover trigger, so it reads as tappable.
const FLAW_CHIP_TRIGGER_CLASS = 'transition-all hover:-translate-y-px hover:brightness-125';

/** Seconds spent on the flawed move. */
function formatMoveTime(seconds: number): string {
  return `${seconds.toFixed(seconds < MOVE_TIME_DECIMAL_MAX_SECONDS ? 1 : 0)}s`;
}

/**
 * The one severity chip of a Flaws card (260-G2): "??? Facepalm" for a facepalm blunder, "?? Blunder" for
 * any other blunder, "? Mistake" for a mistake. For a scored blunder (score and type present, 257 D-09)
 * it is the trigger of the facepalm popover; the testid stays numeric-only so the Umami target is unchanged.
 */
function FlawSeverityChip({ flaw }: { flaw: FlawListItem }) {
  const { facepalm_score: score, facepalm_type: type } = flaw;
  const scored = flaw.severity === 'blunder' && score != null && type != null;
  const badge = (
    <SeverityBadge
      severity={flaw.severity}
      count={1}
      gameId={flaw.game_id}
      showCount={false}
      showIcon
      facepalm={isFacepalmBlunder(score)}
      className={scored ? FLAW_CHIP_TRIGGER_CLASS : undefined}
    />
  );
  if (!scored) return badge;
  return (
    <FacepalmBadgePopover
      testId={`facepalm-badge-${flaw.game_id}-${flaw.ply}`}
      score={score}
      type={type}
    >
      {badge}
    </FacepalmBadgePopover>
  );
}

/** Explanation popover body: "<bold term>: definition". */
function Definition({ term, children }: { term: string; children: ReactNode }) {
  return (
    <>
      <span className="font-bold">{term}</span>: {children}
    </>
  );
}

/** A tactic chip, cut off only where the column is too narrow for its label; hover or tap explains the motif. */
function FlawTacticChip({
  flaw,
  motif,
  orientation,
}: {
  flaw: FlawListItem;
  motif: string | null;
  orientation: 'missed' | 'allowed';
}) {
  // A family-less motif has no chip (TacticMotifChip renders nothing), so no empty trigger either.
  if (motif == null || TACTIC_FAMILY_FOR_MOTIF[motif] == null) return null;
  const term = `${orientation}: ${tacticMotifLabel(motif)}`;
  const definition = tacticMotifDefinition(motif);
  return (
    <ChipPopover
      testId={`flaw-tactic-${orientation}-${flaw.game_id}-${flaw.ply}`}
      ariaLabel={`${term}. ${definition}`}
      content={<Definition term={term}>{definition}</Definition>}
    >
      <span className={cn('inline-flex min-w-0 max-w-full rounded-full', FLAW_CHIP_TRIGGER_CLASS)}>
        <TacticMotifChip
          motif={motif}
          gameId={flaw.game_id}
          orientation={orientation}
          noTruncate
          fitWidth
        />
      </span>
    </ChipPopover>
  );
}

/** Timing and phase tags are context that nearly every flaw has, so they come last. */
function isContextTag(tag: FlawTag): boolean {
  const family = getTagFamily(tag);
  return family === 'tempo' || family === 'phase';
}

/** A tag chip; hover or tap explains it. */
function FlawTagChip({ flaw, tag }: { flaw: FlawListItem; tag: FlawTag }) {
  return (
    <ChipPopover
      testId={`flaw-tag-${tag}-${flaw.game_id}-${flaw.ply}`}
      ariaLabel={`${tag}. ${TAG_DEFINITIONS[tag]}`}
      content={<Definition term={tag}>{TAG_DEFINITIONS[tag]}</Definition>}
    >
      <span className={cn('inline-flex rounded-full', FLAW_CHIP_TRIGGER_CLASS)}>
        <TagChip tag={tag} gameId={flaw.game_id} showDefinitionPopover={false} />
      </span>
    </ChipPopover>
  );
}

/** The chips below the details: tactics, opportunity and impact, then timing and phase. */
function FlawTags({ flaw, showMissed, showAllowed }: {
  flaw: FlawListItem;
  showMissed: boolean;
  showAllowed: boolean;
}) {
  const tags = [...flaw.tags].sort((a, b) => Number(isContextTag(a)) - Number(isContextTag(b)));
  if (tags.length === 0 && !showMissed && !showAllowed) return null;
  return (
    <div className="flex min-w-0 flex-wrap items-center gap-x-1.5 gap-y-1" data-testid="flaw-card-tags">
      {showMissed && (
        <FlawTacticChip flaw={flaw} motif={flaw.missed_tactic_motif} orientation="missed" />
      )}
      {showAllowed && (
        <FlawTacticChip flaw={flaw} motif={flaw.allowed_tactic_motif} orientation="allowed" />
      )}
      {tags.map((tag) => (
        <FlawTagChip key={tag} flaw={flaw} tag={tag} />
      ))}
    </div>
  );
}

/** Platform icon, linked to the exact ply on the platform when there is a URL. */
function FlawPlatformLink({ flaw }: { flaw: FlawListItem }) {
  const url = platformPlyUrl(flaw.platform, flaw.platform_url, flaw.ply, flaw.user_color);
  const icon = <PlatformIcon platform={flaw.platform} className="h-4 w-4" />;
  if (!url) return <span className="text-muted-foreground">{icon}</span>;
  return (
    <Tooltip content="Open at this move on platform">
      <a
        href={url}
        data-umami-event="outbound-platform-flaw"
        data-umami-event-platform={flaw.platform}
        target="_blank"
        rel="noopener noreferrer"
        // Padding with a matching negative margin: a larger tap target, same layout.
        className="-m-2 p-2 text-brand-brown-light transition-colors hover:text-brand-brown-highlight"
        aria-label="Open at this move on platform"
        data-testid={`flaw-card-platform-link-${flaw.game_id}-${flaw.ply}`}
      >
        {icon}
      </a>
    </Tooltip>
  );
}

/** The one-line rows beside the board: clock, opponent, date. */
function FlawDetails({ flaw }: { flaw: FlawListItem }) {
  // Opponent: the side the user is NOT playing.
  const isWhite = flaw.user_color === 'white';
  const opponentName = (isWhite ? flaw.black_username : flaw.white_username) ?? '?';
  const opponentRating = isWhite ? flaw.black_rating : flaw.white_rating;
  const clockText = [
    flaw.clock_seconds != null ? formatClock(flaw.clock_seconds) : null,
    flaw.move_seconds != null ? formatMoveTime(flaw.move_seconds) : null,
  ]
    .filter((part) => part != null)
    .join(' · ');
  return (
    <div className="flex min-w-0 flex-col gap-0.5 text-sm text-muted-foreground">
      {clockText !== '' && (
        <span className="flex min-w-0 items-center gap-1">
          <Clock className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
          <span className="truncate">{clockText}</span>
        </span>
      )}
      {/* A long name is cut off, the rating stays. */}
      <span className="flex min-w-0 gap-1" title={opponentName}>
        <span className="truncate">vs {opponentName}</span>
        {opponentRating !== null && <span className="shrink-0">({opponentRating})</span>}
      </span>
      {flaw.played_at && <span className="truncate">{formatDate(flaw.played_at)}</span>}
    </div>
  );
}

/**
 * Props for FlawCard.
 *
 * tacticOrientation controls which chip(s) render.
 * Default 'either' = show both when both exist (backward-compatible).
 */
export interface FlawCardProps {
  flaw: FlawListItem;
  /** Orientation filter — controls which tactic chip(s) render. */
  tacticOrientation?: TacticOrientation;
}

/**
 * FlawCard — one flawed-move card for the Flaws subtab grid. One layout at every width:
 *
 *   header:  severity chip (the facepalm popover trigger on a scored blunder), move, platform link
 *   body:    miniboard with the flaw-move and best-move arrows | details and tags; each tag
 *            explains itself on hover or tap
 *   footer:  full-width Analyze button
 *
 * Security: user-provided strings (usernames, platform_url) are React children
 * or href (auto-escaped). platform link uses target=_blank + rel=noopener
 * noreferrer (reverse-tabnabbing guard).
 */
export function FlawCard({ flaw, tacticOrientation = 'either' }: FlawCardProps) {
  const { ref: contentRef, boardSize } = useFlawBoardSize();

  const flipped = flaw.user_color === 'black';
  const severityColor = SEVERITY_COLOR[flaw.severity];

  // Flaw-move arrow: augment board_fen() to a full FEN (side-to-move + unknown
  // castling/en-passant) so chess.js can resolve the move's from/to squares.
  const sideToMove = flaw.user_color === 'black' ? 'b' : 'w';
  const moveSquares = flaw.move_san
    ? sanToSquares(`${flaw.fen} ${sideToMove} - - 0 1`, flaw.move_san)
    : null;

  // Engine best move FROM the pre-flaw position (UCI) — blue arrow next to the
  // red flaw-move arrow. Skip if it coincides with the played move (avoids a
  // duplicate arrow / React key collision; a genuine flaw rarely matches).
  const bestMoveSquares = uciToSquares(flaw.best_move);
  const showBestMove =
    bestMoveSquares != null &&
    !(moveSquares && moveSquares.from === bestMoveSquares.from && moveSquares.to === bestMoveSquares.to);
  // Tactic-depth badges (1-based display): the allowed tactic sits at the end of
  // the flaw-move arrow; the missed tactic at the end of the blue best-move arrow.
  // Allowed is decision-anchored (+1 vs missed) because the opponent's refutation
  // line starts one ply after the shared pre-flaw decision board.
  // Shared resolver: the family guard ensures a family-less motif
  // (self-interference, clearance) — whose chip self-nullifies — never paints a bare
  // depth number with no chip to explain it.
  const allowedDepthLabel =
    tacticDepthBadge(flaw.allowed_tactic_motif, flaw.allowed_tactic_depth, 'allowed') ?? undefined;
  const missedDepthLabel =
    tacticDepthBadge(flaw.missed_tactic_motif, flaw.missed_tactic_depth, 'missed') ?? undefined;
  // Arrow recolor: a move that belongs to a tactic carries the
  // tactic's color instead of the generic severity/best-move color. The played-move arrow
  // turns crimson (allowed) and the best-move arrow turns teal (missed). Gate on the same
  // orientation + motif condition that decides whether each tactic chip renders, so the
  // arrow color and the chip never disagree.
  const showAllowedTactic = tacticOrientation !== 'missed' && flaw.allowed_tactic_motif != null;
  const showMissedTactic = tacticOrientation !== 'allowed' && flaw.missed_tactic_motif != null;
  const boardArrows = [
    ...(moveSquares
      ? [
          {
            from: moveSquares.from,
            to: moveSquares.to,
            color: showAllowedTactic ? TAC_ALLOWED : severityColor,
            label: allowedDepthLabel,
            labelColor: TAC_ALLOWED_LABEL,
          },
        ]
      : []),
    ...(showBestMove
      ? [
          {
            from: bestMoveSquares.from,
            to: bestMoveSquares.to,
            color: showMissedTactic ? TAC_MISSED : BEST_MOVE_ARROW,
            label: missedDepthLabel,
            labelColor: TAC_MISSED_LABEL,
          },
        ]
      : []),
  ];

  // Move notation — shared primitive, no local helper.
  const moveNotation = flaw.move_san
    ? formatMoveNotation(flaw.ply, flaw.move_san)
    : `Ply ${flaw.ply}`;

  return (
    <Card
      as="article"
      accentColor={severityColor}
      overflowVisible
      data-testid={`flaw-card-${flaw.game_id}-${flaw.ply}`}
    >
      {/* rounded-t-md because overflowVisible turns the card's own corner clip off. */}
      <CardHeader as="h4" size="compact" className="rounded-t-md px-3 py-1.5">
        <FlawSeverityChip flaw={flaw} />
        <span className="min-w-0 truncate text-foreground">{moveNotation}</span>
        <span className="ml-auto flex shrink-0 items-center">
          <FlawPlatformLink flaw={flaw} />
        </span>
      </CardHeader>

      <div className="p-3">
        <div ref={contentRef} className="flex flex-col gap-2.5">
          <div className="flex gap-3">
            <LazyMiniBoard
              fen={flaw.fen}
              flipped={flipped}
              size={boardSize}
              arrows={boardArrows.length > 0 ? boardArrows : undefined}
            />
            <div className="flex min-w-0 flex-1 flex-col gap-2">
              <FlawDetails flaw={flaw} />
              <FlawTags flaw={flaw} showMissed={showMissedTactic} showAllowed={showAllowedTactic} />
            </div>
          </div>
          <Button asChild variant="brand-outline" className="w-full">
            {/* Real <a> via Link for middle-click / cmd-click new-tab support. */}
            <Link
              to={buildGameAnalysisUrl(flaw.game_id, flaw.ply)}
              data-testid="btn-flaw-analyze"
              aria-label="Analyze game"
              // Internal Link: track in onClick, never data-umami-event (frontend/CLAUDE.md).
              onClick={() => trackFeature('action', { target: 'analyze' })}
            >
              <Search className="h-4 w-4 mr-1" />
              Analyze
            </Link>
          </Button>
        </div>
      </div>
    </Card>
  );
}
