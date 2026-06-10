import { useMemo, useState } from 'react';
import { Chess } from 'chess.js';
import { BookOpen, Calendar, Clock, Equal, ExternalLink, Hash, Minus, Plus } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  SEV_BLUNDER,
  SEV_MISTAKE,
  WDL_BORDER_DRAW,
  WDL_BORDER_LOSS,
  WDL_BORDER_WIN,
} from '@/lib/theme';
import { Card, CardHeader } from '@/components/ui/card';
import { Tooltip } from '@/components/ui/tooltip';
import { PlatformIcon } from '@/components/icons/PlatformIcon';
import { LazyMiniBoard } from '@/components/board/LazyMiniBoard';
import { EvalChart } from '@/components/library/EvalChart';
import { SeverityBadge } from '@/components/library/SeverityBadge';
import { TagChip, TagLegend } from '@/components/library/TagChip';
import { NoAnalysisState } from '@/components/library/NoAnalysisState';
import { gamePlatformUrl } from '@/lib/platformLinks';
import { plysToFullMoves } from '@/lib/chess';
import { useFlawFilterStore } from '@/hooks/useFlawFilterStore';
import type { GameFlawCard, FlawSeverity, FlawTag } from '@/types/library';
import type { UserResult } from '@/types/api';

// Standalone component per D-05 — do NOT import from or modify GameCard.tsx.
// formatDate / formatTimeControl copied verbatim from GameCard.tsx (same display requirements).

interface LibraryGameCardProps {
  game: GameFlawCard;
  /**
   * When the card is opened from the Flaws subtab, the ply of the clicked flaw. Its
   * eval-chart marker gets a "ping" ring so the eye lands on it on open. The pulse
   * yields to the hover-driven highlight systems the first time the user hovers a
   * tag/severity or scrubs the chart (see `yieldFocus`). Omitted on the Games subtab.
   */
  focusPly?: number | null;
}

const MOBILE_BOARD_SIZE = 130;
const DESKTOP_BOARD_SIZE = 132;

// Mistake/blunder corner-dot colors (orange/red) for the live hover miniboard.
const DOT_COLOR: Record<'mistake' | 'blunder', string> = {
  mistake: SEV_MISTAKE,
  blunder: SEV_BLUNDER,
};

/** One reconstructed ply: the FEN after the move plus the move's from/to squares. */
interface PerPly {
  fen: string;
  from: string;
  to: string;
}

/**
 * Replay the SAN mainline once into per-ply {fen, to} entries (memoized per card).
 * moves[i] is the move at ply i, so perPly[i] is the position after that move —
 * matching eval_series[i].es (eval_cp is the post-move eval; see zobrist.py). The
 * moved piece sits at perPly[i].to, which the corner dot marks for M/B plies.
 * Stops early on a malformed SAN — earlier plies still scrub.
 */
function buildPerPly(moves: string[] | null): PerPly[] | null {
  if (!moves || moves.length === 0) return null;
  const chess = new Chess();
  const out: PerPly[] = [];
  for (const san of moves) {
    let mv;
    try {
      mv = chess.move(san);
    } catch {
      break;
    }
    if (!mv) break;
    out.push({ fen: chess.fen(), from: mv.from, to: mv.to });
  }
  return out.length > 0 ? out : null;
}

const RESULT_CLASSES: Record<UserResult, string> = {
  win: 'bg-green-600/20 text-green-400 border-green-600/30',
  draw: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
  loss: 'bg-red-600/20 text-red-400 border-red-600/30',
};
const RESULT_ICONS: Record<UserResult, LucideIcon> = { win: Plus, draw: Equal, loss: Minus };
const BORDER_COLORS: Record<UserResult, string> = {
  win: WDL_BORDER_WIN,
  draw: WDL_BORDER_DRAW,
  loss: WDL_BORDER_LOSS,
};

// Severity order for the badge row (must not wrap — sized to full-label nowrap row).
const SEVERITY_ORDER: FlawSeverity[] = ['blunder', 'mistake', 'inaccuracy'];

// Flaw-tag families, mirroring the backend game-selection filter
// (build_flaw_filter_clauses in library_repository.py): OR within family, AND
// across families. Phase tags are not filter predicates and are excluded.
const TAG_FAMILIES: readonly (readonly FlawTag[])[] = [
  ['low-clock', 'hasty', 'unrushed'],
  ['miss', 'lucky'],
  ['reversed', 'squandered'],
];

// Copied verbatim from GameCard.tsx — same display requirements (D-05 forbids shared import).
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

// Copied verbatim from GameCard.tsx — same display requirements (D-05 forbids shared import).
function formatTimeControl(tcStr: string): string {
  // PGN daily/correspondence format: "1/{seconds_per_move}" (e.g. "1/259200" = 3 days/move).
  // Used by chess.com daily and lichess correspondence. Render as "Nd".
  // Previously fell through to Number("1/259200") = NaN, producing "Classical · NaN".
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
 * Analyzed game card for the Library Games subtab.
 *
 * Standalone component per D-05 — does NOT extend or modify GameCard. Borrows
 * GameCard's metadata/board/platform patterns but adds a full-width header, a
 * responsive body (1 column mobile, 2 columns tablet, 3 columns desktop), and a
 * flaw block on mobile.
 *
 * Flaw column branches on analysis_state:
 * - "analyzed"         → SeverityBadge × 3 (nowrap row) + TagChip row (flex-wrap)
 * - "no_engine_analysis" → NoAnalysisState pill (never shows "0 Blunders")
 *
 * Security: all user-provided strings (usernames, opening name, platform_url) are
 * rendered as React children or href (auto-escaped). platform_url uses
 * target="_blank" rel="noopener noreferrer" to prevent reverse-tabnabbing (T-107-10).
 */
export function LibraryGameCard({ game, focusPly }: LibraryGameCardProps) {
  // Live miniboard: hovering the eval chart sets the ply; the board scrubs to
  // that position and (on M/B plies) marks the moved piece. At rest the board
  // shows result_fen, as before.
  const [hoverPly, setHoverPly] = useState<number | null>(null);

  // Clicked-flaw focus pulse (Flaws subtab). Seeded from the prop at mount (the
  // card only mounts once the game has loaded). It is an attention cue, not a
  // persistent mode: it yields the first time the user reaches for the hover-driven
  // highlight tools — hovering a tag/severity or scrubbing the chart — so the focus
  // pulse and the enlarge/dim highlight are never on screen at the same time.
  const [focusedPly, setFocusedPly] = useState<number | null>(focusPly ?? null);
  const yieldFocus = () => setFocusedPly(null);
  const perPly = useMemo(() => buildPerPly(game.moves), [game.moves]);
  const mbByPly = useMemo(() => {
    const m = new Map<number, 'mistake' | 'blunder'>();
    for (const fm of game.flaw_markers ?? []) {
      if (fm.severity === 'mistake' || fm.severity === 'blunder') m.set(fm.ply, fm.severity);
    }
    return m;
  }, [game.flaw_markers]);

  // Per-tag occurrence counts shown on the chips. Scoped to the user's M/B markers
  // (is_user) so a chip count matches the user-only `chips`/`severity_counts` the
  // card already shows, and so the count equals the number of dots that highlight
  // on hover. Inaccuracy markers carry no tags, so they never contribute.
  const tagCounts = useMemo(() => {
    const m = new Map<FlawTag, number>();
    for (const fm of game.flaw_markers ?? []) {
      if (!fm.is_user) continue;
      for (const t of fm.tags) m.set(t, (m.get(t) ?? 0) + 1);
    }
    return m;
  }, [game.flaw_markers]);

  // Transient hover highlight: hovering a tag chip or a severity badge in the flaw
  // column emphasizes the matching markers on this card's eval chart. Inaccuracy is
  // included — its markers are off-chart by default and get revealed on its hover.
  const [highlight, setHighlight] = useState<
    { kind: 'tag'; tag: FlawTag } | { kind: 'severity'; severity: FlawSeverity } | null
  >(null);
  // Hovering a tag/severity (non-null highlight) or scrubbing the chart is the user
  // reaching for the category-highlight tools, so the focus pulse steps aside.
  const setHighlightYieldingFocus = (
    next: { kind: 'tag'; tag: FlawTag } | { kind: 'severity'; severity: FlawSeverity } | null,
  ) => {
    if (next) yieldFocus();
    setHighlight(next);
  };
  const handleHoverPlyChange = (ply: number | null) => {
    if (ply != null) yieldFocus();
    setHoverPly(ply);
  };
  const highlightedPlies = useMemo(() => {
    if (!highlight) return null;
    const set = new Set<number>();
    for (const fm of game.flaw_markers ?? []) {
      if (!fm.is_user) continue;
      const matches =
        highlight.kind === 'severity'
          ? fm.severity === highlight.severity
          : fm.tags.includes(highlight.tag); // inaccuracies have no tags → never match a tag hover
      if (matches) set.add(fm.ply);
    }
    return set;
  }, [highlight, game.flaw_markers]);

  // Persistent (not hover) white outline: user markers matching the active flaw-tag
  // filter under the SAME predicate used to select games (OR within family, AND
  // across families — build_flaw_filter_clauses). Mirrors the TagChip ring on the chart.
  const [flawFilter] = useFlawFilterStore();
  const filterTags = flawFilter.tags;
  const outlinedPlies = useMemo(() => {
    const filterSet = new Set<FlawTag>(filterTags);
    // Per family with ≥1 selected tag, keep the selected subset (the OR-within group).
    const requiredGroups = TAG_FAMILIES.map((fam) => fam.filter((t) => filterSet.has(t))).filter(
      (sel) => sel.length > 0,
    );
    if (requiredGroups.length === 0) return null; // no (recognized) tag filter → no outline
    const set = new Set<number>();
    for (const fm of game.flaw_markers ?? []) {
      if (!fm.is_user) continue;
      const markerTags = new Set<FlawTag>(fm.tags);
      // AND across families: every selected family group must be satisfied by ≥1 tag.
      if (requiredGroups.every((sel) => sel.some((t) => markerTags.has(t)))) set.add(fm.ply);
    }
    return set;
  }, [filterTags, game.flaw_markers]);

  const activePly =
    hoverPly != null && perPly ? Math.min(Math.max(hoverPly, 0), perPly.length - 1) : null;
  const hoverEntry = activePly != null ? perPly?.[activePly] : undefined;
  const boardFen = hoverEntry?.fen ?? game.result_fen ?? null;
  const hoverSeverity = activePly != null ? mbByPly.get(activePly) : undefined;
  const cornerDot =
    hoverEntry && hoverSeverity
      ? { square: hoverEntry.to, color: DOT_COLOR[hoverSeverity] }
      : undefined;
  // Highlight the scrubbed move's from/to squares (only while hovering — at rest
  // the board shows the final position with no single "last move" to mark).
  const lastMove = hoverEntry ? { from: hoverEntry.from, to: hoverEntry.to } : undefined;

  const whiteName = game.white_username ?? '?';
  const blackName = game.black_username ?? '?';
  const whiteRating = game.white_rating !== null ? `(${game.white_rating})` : '';
  const blackRating = game.black_rating !== null ? `(${game.black_rating})` : '';

  // Result indicator: small colored chip with +/=/− icon.
  const ResultIcon = RESULT_ICONS[game.user_result];
  const resultIndicator = (
    <span
      className={cn(
        'inline-flex items-center justify-center rounded border h-3.5 w-3.5 shrink-0',
        RESULT_CLASSES[game.user_result],
      )}
      aria-label={game.user_result}
    >
      <ResultIcon className="h-2.5 w-2.5" strokeWidth={3} />
    </span>
  );

  // Platform icon + external link — verbatim from GameCard.tsx (T-107-10 mitigated).
  // lichess link opens from the user's side (board flipped for black); chess.com
  // has no orientation URL param, so it is unchanged (see lib/platformLinks.ts).
  const gameUrl = gamePlatformUrl(game.platform, game.platform_url, game.user_color);
  const platformIconAndLink = (
    <span className="ml-auto shrink-0 flex items-center gap-1.5 text-muted-foreground">
      <PlatformIcon platform={game.platform} className="h-4 w-4" />
      {gameUrl ? (
        <Tooltip content="Open game on platform">
          <a
            href={gameUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-brand-brown-light hover:text-brand-brown-highlight transition-colors"
            aria-label="Open game on platform"
            data-testid={`game-card-link-${game.game_id}`}
          >
            <ExternalLink className="h-4 w-4" />
          </a>
        </Tooltip>
      ) : null}
    </span>
  );

  // HEADER — banded title bar via the shared CardHeader (compact size). rounded-t-md
  // because the card is overflowVisible (the eval tooltip must escape the border), so
  // the band's top corners aren't clipped by the shell and have to round themselves.
  // Desktop: single line "■ White (rating) vs □ Black (rating)"; mobile: two stacked
  // lines, no "vs". The CardHeader is always flex, so the responsive switch lives on
  // the two inner blocks rather than on the header element.
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
      {platformIconAndLink}
    </CardHeader>
  );

  // Opening line
  const openingLine = (
    <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
      <BookOpen className="h-3.5 w-3.5 shrink-0" />
      <span className="truncate">
        {game.opening_name ?? <span className="italic">Unknown Opening</span>}
      </span>
    </div>
  );

  // Metadata items
  const dateItem = game.played_at && (
    <span className="inline-flex items-center gap-1">
      <Calendar className="h-3.5 w-3.5" />
      {formatDate(game.played_at)}
    </span>
  );

  const timeControlItem = game.time_control_bucket && (
    <span className="inline-flex items-center gap-1">
      <Clock className="h-3.5 w-3.5" />
      <span className="capitalize">{game.time_control_bucket}</span>
      {game.time_control_str ? ` ${formatTimeControl(game.time_control_str)}` : ''}
    </span>
  );

  const moveCountItem = game.ply_count !== null && (
    <span className="inline-flex items-center gap-1">
      <Hash className="h-3.5 w-3.5" />
      {plysToFullMoves(game.ply_count)} Moves
    </span>
  );

  const terminationItem = game.termination && game.termination !== 'unknown' && (
    <span className="inline-flex items-center gap-1 capitalize">
      {resultIndicator}
      {game.termination}
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

  // Flaw column / block content — branches on analysis_state.
  // When "no_engine_analysis": severity_counts is null; never read it (T-107-11 mitigated).
  const flawContent =
    game.analysis_state === 'analyzed' ? (
      <>
        {/* Severity count row — flex-wrap so the badges wrap gracefully inside the
            1/3-width desktop column instead of overflowing. */}
        <div
          className="flex items-center gap-1.5 flex-wrap"
          data-testid={`severity-row-${game.game_id}`}
        >
          {SEVERITY_ORDER.map((sev) => {
            const counts = game.severity_counts;
            // noUncheckedIndexedAccess: narrow severity_counts before reading.
            const count = counts !== null ? (counts[sev] ?? 0) : 0;
            // Every badge drives the hover highlight. B/M emphasize their (already
            // visible) dots; the inaccuracy badge reveals the otherwise-hidden
            // yellow inaccuracy dots on the chart.
            return (
              <SeverityBadge
                key={sev}
                severity={sev}
                count={count}
                gameId={game.game_id}
                onHover={(active) =>
                  setHighlightYieldingFocus(active ? { kind: 'severity', severity: sev } : null)
                }
              />
            );
          })}
        </div>
        {/* Tag chip row — flex-wrap allowed. Definitions live in the single
            <TagLegend> "Tags" popover, rendered inline after the last chip (not on a
            separate line), not per-chip overlays, so the eval chart is never covered
            (definition={false}). Hover still highlights the chart markers via onHover. */}
        {game.chips.length > 0 && (
          <div className="flex flex-wrap items-center gap-1.5">
            {game.chips.map((tag) => (
              <TagChip
                key={tag}
                tag={tag}
                gameId={game.game_id}
                count={tagCounts.get(tag)}
                definition={false}
                onHover={(active) => setHighlightYieldingFocus(active ? { kind: 'tag', tag } : null)}
              />
            ))}
            <TagLegend tags={game.chips} gameId={game.game_id} label="Tags" />
          </div>
        )}
      </>
    ) : (
      <NoAnalysisState gameId={game.game_id} />
    );

  return (
    // overflowVisible (overriding .charcoal-texture's overflow:hidden) lets the
    // EvalChart tooltip overlap the card border instead of being clipped at it.
    // z-30 while hovering: `.charcoal-texture > *` puts every column in a
    // z-index:1 stacking context, so a later card's column would otherwise paint
    // over this card's escaping tooltip. Lifting the whole hovered card above its
    // siblings keeps the tooltip on top of the following card and its divider.
    <Card
      as="article"
      data-testid={`library-game-card-${game.game_id}`}
      accentColor={BORDER_COLORS[game.user_result]}
      overflowVisible
      className={cn('border border-border/20', hoverPly != null && 'z-30')}
    >
      {/* Banded header (desktop single-line, mobile two-line) */}
      {header}

      {/* Mobile body: board+info row, eval chart block, flaw block */}
      <div className="flex flex-col gap-2 sm:hidden px-4 py-4">
        <div className="flex gap-3 items-start">
          {boardFen && (
            <LazyMiniBoard
              fen={boardFen}
              flipped={game.user_color === 'black'}
              size={MOBILE_BOARD_SIZE}
              cornerDot={cornerDot}
              lastMove={lastMove}
            />
          )}
          <div className="flex-1 min-w-0 flex flex-col gap-1">
            {openingLine}
            {metadata}
          </div>
        </div>
        {/* Eval chart — full-width, analyzed games only (mobile parity with desktop col 2) */}
        {game.analysis_state === 'analyzed' &&
          game.eval_series &&
          game.flaw_markers &&
          game.phase_transitions && (
            <EvalChart
              gameId={game.game_id}
              evalSeries={game.eval_series}
              flawMarkers={game.flaw_markers}
              phaseTransitions={game.phase_transitions}
              moves={game.moves ?? []}
              flipped={game.user_color === 'black'}
              onHoverPlyChange={handleHoverPlyChange}
              highlightedPlies={highlightedPlies}
              outlinedPlies={outlinedPlies}
              focusedPly={focusedPly}
              // Match the miniboard height (MOBILE_BOARD_SIZE = 130px). Literal
              // arbitrary value so Tailwind's JIT scanner emits the class.
              heightClass="h-[130px]"
            />
          )}
        {/* Full-width flaw block on mobile */}
        <div className="flex flex-col gap-2">
          {flawContent}
        </div>
      </div>

      {/* Tablet/desktop body: 2 columns (sm–lg) → 3 columns (lg+). On tablet the
          flaw column (col-span-2) drops to a full-width second row beneath
          board+info / eval chart; on desktop all three share one row. */}
      <div className="hidden sm:grid sm:grid-cols-2 lg:grid-cols-3 sm:gap-3 sm:items-start px-4 py-4">
        {/* Col 1: mini board + opening + metadata */}
        <div className="flex gap-3 items-start">
          {boardFen && (
            <LazyMiniBoard
              fen={boardFen}
              flipped={game.user_color === 'black'}
              size={DESKTOP_BOARD_SIZE}
              cornerDot={cornerDot}
              lastMove={lastMove}
            />
          )}
          <div className="min-w-0 flex-1 flex flex-col gap-2">
            {openingLine}
            {metadata}
          </div>
        </div>
        {/* Col 2: eval chart (analyzed) or NoAnalysisState pill */}
        <div className="flex items-center justify-center" data-testid={`card-col2-${game.game_id}`}>
          {game.analysis_state === 'analyzed' &&
          game.eval_series &&
          game.flaw_markers &&
          game.phase_transitions ? (
            <EvalChart
              gameId={game.game_id}
              evalSeries={game.eval_series}
              flawMarkers={game.flaw_markers}
              phaseTransitions={game.phase_transitions}
              moves={game.moves ?? []}
              flipped={game.user_color === 'black'}
              onHoverPlyChange={handleHoverPlyChange}
              highlightedPlies={highlightedPlies}
              outlinedPlies={outlinedPlies}
              focusedPly={focusedPly}
              // Match the miniboard height (DESKTOP_BOARD_SIZE = 132px). Literal
              // arbitrary value so Tailwind's JIT scanner emits the class.
              heightClass="h-[132px]"
            />
          ) : (
            <NoAnalysisState gameId={game.game_id} />
          )}
        </div>
        {/* Col 3: flaw column. Spans both columns on tablet (full-width second
            row), single column on desktop (the grid separates columns — no divider). */}
        <div className="flex flex-col gap-2 sm:col-span-2 lg:col-span-1">
          {flawContent}
        </div>
      </div>
    </Card>
  );
}
