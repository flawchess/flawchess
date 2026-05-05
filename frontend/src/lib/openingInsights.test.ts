import { describe, it, expect } from 'vitest';
import { formatCandidateMove } from './openingInsights';
import * as openingInsights from './openingInsights';

describe('formatCandidateMove', () => {
  it('renders a white candidate after a long entry sequence with the move-number prefix only', () => {
    expect(
      formatCandidateMove(['e4', 'c5', 'Nf3', 'd6', 'd4', 'cxd4'], 'Nxd4'),
    ).toBe('4.Nxd4');
  });

  it('renders a white candidate after exactly 2 entry plys', () => {
    expect(formatCandidateMove(['e4', 'c5'], 'Nf3')).toBe('2.Nf3');
  });

  it('renders a black candidate with continuation notation', () => {
    expect(formatCandidateMove(['e4'], 'c5')).toBe('1...c5');
  });

  it('renders the first move when the entry sequence is empty', () => {
    expect(formatCandidateMove([], 'e4')).toBe('1.e4');
  });

  it('renders a black candidate after a 3-ply entry sequence', () => {
    expect(formatCandidateMove(['e4', 'c5', 'Nf3'], 'd6')).toBe('2...d6');
  });

  it('renders a white candidate after a 4-ply entry sequence', () => {
    expect(formatCandidateMove(['e4', 'c5', 'Nf3', 'd6'], 'd4')).toBe('3.d4');
  });
});

describe('shared constants — stale-constant removal (Phase 76 D-20)', () => {
  it('does not export getSeverityBorderColor', () => {
    expect((openingInsights as Record<string, unknown>).getSeverityBorderColor).toBeUndefined();
  });


  it('does not export MIN_GAMES_FOR_INSIGHT', () => {
    expect((openingInsights as Record<string, unknown>).MIN_GAMES_FOR_INSIGHT).toBeUndefined();
  });

  it('does not export INSIGHT_RATE_THRESHOLD', () => {
    expect((openingInsights as Record<string, unknown>).INSIGHT_RATE_THRESHOLD).toBeUndefined();
  });

  it('does not export INSIGHT_THRESHOLD_COPY', () => {
    expect((openingInsights as Record<string, unknown>).INSIGHT_THRESHOLD_COPY).toBeUndefined();
  });
});
