import { useMemo, useState } from 'react';
import { SeverityBadge } from '@/components/library/SeverityBadge';
import { TacticMotifGroup } from '@/components/library/TacticMotifGroup';
import { ChipColumn } from '@/components/library/ChipColumn';
import { TagChip, TagLegend } from '@/components/library/TagChip';
import { tacticMotifLabel, TACTIC_FAMILY_FOR_MOTIF } from '@/lib/tacticComparisonMeta';
import type { GameFlawCard, FlawSeverity, FlawTag } from '@/types/library';

/**
 * Flaw-tags panel for the /analysis page (game mode) — mirrors the Library game
 * card's severity-badge row + 3-column (Missed | Allowed | Context) tactic/context
 * chip block, per quick-260702-nm8. A standalone component (does NOT import from or
 * modify LibraryGameCard, which stays untouched — the card is well-tested).
 *
 * Clicking a severity badge or tactic/context chip cycles the board through that
 * flaw's positions via `onCyclePly`, mirroring the Library card's click-to-cycle
 * behavior but WITHOUT the card's hover-highlight/eval-chart-outline machinery
 * (no filter store on /analysis — resolved decision 3).
 */

// Re-declared locally (trivially safe copies from LibraryGameCard — not shared
// extractions, per the plan's resolved decision 4).
type TacticChipOrientation = 'missed' | 'allowed';
const TACTIC_ORIENTATIONS: readonly TacticChipOrientation[] = ['missed', 'allowed'];
const TACTIC_ORIENTATION_LABELS: Record<TacticChipOrientation, string> = {
  allowed: 'Allowed',
  missed: 'Missed',
};
const SEVERITY_ORDER: FlawSeverity[] = ['blunder', 'mistake', 'inaccuracy'];

type FlawRef =
  | { kind: 'tag'; tag: FlawTag }
  | { kind: 'severity'; severity: FlawSeverity }
  | { kind: 'motif'; motif: string; orientation: TacticChipOrientation };

function sameFlawRef(a: FlawRef, b: FlawRef): boolean {
  if (a.kind === 'tag' && b.kind === 'tag') return a.tag === b.tag;
  if (a.kind === 'severity' && b.kind === 'severity') return a.severity === b.severity;
  if (a.kind === 'motif' && b.kind === 'motif')
    return a.motif === b.motif && a.orientation === b.orientation;
  return false;
}

function motifPliesKey(orientation: TacticChipOrientation, motifLabel: string): string {
  return `${orientation}:${motifLabel}`;
}

interface AnalysisTagsPanelProps {
  game: GameFlawCard;
  /** Cycles the board (+ synced move list + eval-chart crosshair) to a flaw's ply. */
  onCyclePly: (ply: number) => void;
  className?: string;
}

export function AnalysisTagsPanel({ game, onCyclePly, className }: AnalysisTagsPanelProps) {
  const markers = game.flaw_markers ?? [];

  // Per-severity ascending list of the user's marker plies (B/M/I).
  const severityPlies = useMemo(() => {
    const m = new Map<FlawSeverity, number[]>();
    for (const fm of markers) {
      if (!fm.is_user) continue;
      const arr = m.get(fm.severity);
      if (arr) arr.push(fm.ply);
      else m.set(fm.severity, [fm.ply]);
    }
    for (const arr of m.values()) arr.sort((a, b) => a - b);
    return m;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [game.flaw_markers]);

  // Per-tag ascending list of the user's marker plies (context chips).
  const tagPlies = useMemo(() => {
    const m = new Map<FlawTag, number[]>();
    for (const fm of markers) {
      if (!fm.is_user) continue;
      for (const t of fm.tags) {
        const arr = m.get(t);
        if (arr) arr.push(fm.ply);
        else m.set(t, [fm.ply]);
      }
    }
    for (const arr of m.values()) arr.sort((a, b) => a - b);
    return m;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [game.flaw_markers]);

  // Per-tag occurrence counts.
  const tagCounts = useMemo(() => {
    const m = new Map<FlawTag, number>();
    for (const fm of markers) {
      if (!fm.is_user) continue;
      for (const t of fm.tags) m.set(t, (m.get(t) ?? 0) + 1);
    }
    return m;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [game.flaw_markers]);

  // Per-tactic-motif ascending list of the user's marker plies, keyed by orientation +
  // display label (motifPliesKey collapses named-mate subtypes to "checkmate").
  const motifPlies = useMemo(() => {
    const m = new Map<string, number[]>();
    const push = (key: string, ply: number): void => {
      const arr = m.get(key);
      if (arr) arr.push(ply);
      else m.set(key, [ply]);
    };
    for (const fm of markers) {
      if (!fm.is_user) continue;
      if (fm.allowed_tactic_motif != null)
        push(motifPliesKey('allowed', tacticMotifLabel(fm.allowed_tactic_motif)), fm.ply);
      if (fm.missed_tactic_motif != null)
        push(motifPliesKey('missed', tacticMotifLabel(fm.missed_tactic_motif)), fm.ply);
    }
    for (const arr of m.values()) arr.sort((a, b) => a - b);
    return m;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [game.flaw_markers]);

  // Distinct (orientation, display-label) tactic motifs; family-less motifs are
  // skipped; named-mate subtypes collapse to a single "checkmate" chip per orientation.
  // Allowed motifs collected before missed (stable grouping, mirrors LibraryGameCard).
  const tacticMotifs = useMemo<{ motif: string; orientation: TacticChipOrientation }[]>(() => {
    const seen = new Set<string>();
    const out: { motif: string; orientation: TacticChipOrientation }[] = [];
    const collect = (raw: string | null, orientation: TacticChipOrientation): void => {
      if (raw == null) return;
      const label = tacticMotifLabel(raw);
      if (TACTIC_FAMILY_FOR_MOTIF[label] == null) return;
      const key = motifPliesKey(orientation, label);
      if (seen.has(key)) return;
      seen.add(key);
      out.push({ motif: label, orientation });
    };
    for (const fm of markers) if (fm.is_user) collect(fm.allowed_tactic_motif, 'allowed');
    for (const fm of markers) if (fm.is_user) collect(fm.missed_tactic_motif, 'missed');
    return out;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [game.flaw_markers]);

  // Click-to-cycle state: clicking a ref advances through its ply list, wrapping;
  // clicking a different ref restarts at position 0.
  const [cycle, setCycle] = useState<{ ref: FlawRef; pos: number } | null>(null);

  const pliesForRef = (ref: FlawRef): number[] => {
    if (ref.kind === 'tag') return tagPlies.get(ref.tag) ?? [];
    if (ref.kind === 'severity') return severityPlies.get(ref.severity) ?? [];
    return motifPlies.get(motifPliesKey(ref.orientation, ref.motif)) ?? [];
  };

  const handleActivate = (ref: FlawRef): void => {
    const plies = pliesForRef(ref);
    if (plies.length === 0) return;
    const pos = cycle && sameFlawRef(cycle.ref, ref) ? (cycle.pos + 1) % plies.length : 0;
    setCycle({ ref, pos });
    const ply = plies[pos];
    if (ply !== undefined) onCyclePly(ply);
  };

  // Belt-and-suspenders: the Analysis page already gates rendering on evalChartReady
  // (which implies flaw_markers present), but guard here too — no NoAnalysisState.
  if (game.analysis_state !== 'analyzed' || markers.length === 0) return null;

  const contextChips =
    game.chips.length > 0 ? (
      <>
        {game.chips.map((tag) => (
          <TagChip
            key={tag}
            tag={tag}
            gameId={game.game_id}
            count={tagCounts.get(tag)}
            definition={false}
            onActivate={() => handleActivate({ kind: 'tag', tag })}
          />
        ))}
      </>
    ) : null;
  const contextLegend =
    game.chips.length > 0 ? (
      <TagLegend variant="icon" tags={game.chips} tacticMotifs={[]} gameId={game.game_id} />
    ) : null;

  return (
    <div data-testid="analysis-tags-panel" className={className}>
      <div className="flex items-center gap-1.5 flex-wrap">
        {SEVERITY_ORDER.map((sev) => {
          const counts = game.severity_counts;
          const count = counts !== null ? (counts[sev] ?? 0) : 0;
          return (
            <SeverityBadge
              key={sev}
              severity={sev}
              count={count}
              gameId={game.game_id}
              onActivate={() => handleActivate({ kind: 'severity', severity: sev })}
            />
          );
        })}
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-x-3 gap-y-2 mt-2">
        {TACTIC_ORIENTATIONS.map((orientation) => {
          const groupMotifs = tacticMotifs.filter((t) => t.orientation === orientation);
          return (
            <TacticMotifGroup
              key={orientation}
              orientation={orientation}
              label={TACTIC_ORIENTATION_LABELS[orientation]}
              gameId={game.game_id}
              motifs={groupMotifs.map(({ motif }) => ({
                motif,
                count: motifPlies.get(motifPliesKey(orientation, motif))?.length ?? 0,
                // No filter store on /analysis (resolved decision 3) — never ring.
                filterRingActive: false,
              }))}
              onChipHover={() => {}}
              onChipActivate={(motif) => handleActivate({ kind: 'motif', motif, orientation })}
              legend={
                <TagLegend
                  variant="icon"
                  tags={[]}
                  tacticMotifs={groupMotifs.map((t) => t.motif)}
                  gameId={game.game_id}
                  testId={`tag-legend-tactic-${orientation}-${game.game_id}`}
                />
              }
            />
          );
        })}
        <ChipColumn
          label="Context"
          testId={`context-column-${game.game_id}`}
          isEmpty={contextChips == null}
          labelTrailing={contextLegend}
        >
          {contextChips}
        </ChipColumn>
      </div>
    </div>
  );
}
