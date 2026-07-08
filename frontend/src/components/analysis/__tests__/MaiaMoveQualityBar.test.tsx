// @vitest-environment jsdom
/**
 * MaiaMoveQualityBar tests (quick 260705-kfg) — the move-quality bar below the
 * Human Move Probability chart. Verifies segment rendering by bucket, the
 * hover-to-reveal move list, and the onHoverMovesChange lift used for board
 * arrows. Bucketing math itself is covered in moveQuality.test.ts.
 */

import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';

import { MaiaMoveQualityBar } from '../MaiaMoveQualityBar';
import type { MoveQualityEval } from '../MovesByRatingChart';
import type { MoveCurvePoint } from '@/hooks/useMaiaEngine';
import { MOVE_QUALITY_GOOD } from '@/lib/theme';

const PER_ELO: MoveCurvePoint[] = [
  { elo: 1500, moveProbabilities: { Ra8: 0.52, g4: 0.11, Rb1: 0.1, Ra5: 0.09 } },
];

function grade(map: Record<string, MoveQualityEval['quality']>): Map<string, MoveQualityEval> {
  return new Map(
    Object.entries(map).map(([san, quality]) => [san, { quality, evalCp: 0, evalMate: null }]),
  );
}

const QUALITY = grade({ Ra8: 'best', g4: 'blunder', Rb1: 'blunder', Ra5: 'mistake' });

afterEach(cleanup);

describe('MaiaMoveQualityBar', () => {
  it('renders a segment per non-empty bucket and omits empty ones', () => {
    render(
      <MaiaMoveQualityBar
        perElo={PER_ELO}
        selectedElo={1500}
        shownSans={['Ra8', 'g4', 'Rb1', 'Ra5']}
        qualityBySan={QUALITY}
      />,
    );
    expect(screen.getByTestId('maia-move-quality-bar')).toBeTruthy();
    expect(screen.getByTestId('maia-quality-segment-good')).toBeTruthy();
    expect(screen.getByTestId('maia-quality-segment-blunder')).toBeTruthy();
    expect(screen.getByTestId('maia-quality-segment-mistake')).toBeTruthy();
    // No inaccuracy candidates in this fixture → no segment.
    expect(screen.queryByTestId('maia-quality-segment-inaccuracy')).toBeNull();
  });

  it('renders nothing when there is no shown-move mass', () => {
    const { container } = render(
      <MaiaMoveQualityBar
        perElo={[]}
        selectedElo={1500}
        shownSans={[]}
        qualityBySan={new Map()}
      />,
    );
    expect(container.firstChild).toBeNull();
  });

  it('reveals only the hovered segment\'s moves and lifts them for board arrows', () => {
    const onHover = vi.fn();
    render(
      <MaiaMoveQualityBar
        perElo={PER_ELO}
        selectedElo={1500}
        shownSans={['Ra8', 'g4', 'Rb1', 'Ra5']}
        qualityBySan={QUALITY}
        onHoverMovesChange={onHover}
      />,
    );

    // Idle (resting state): prose position verdict, not the old static hint
    // text (quick 260705-m3z) — all four fixture moves are graded, so
    // computePositionVerdict has something to narrate.
    expect(screen.getByTestId('maia-position-verdict')).toBeTruthy();

    fireEvent.mouseEnter(screen.getByTestId('maia-quality-segment-good'));
    const list = screen.getByTestId('maia-quality-hovered-list').textContent ?? '';
    expect(list).toMatch(/Good Moves:/);
    // Each move now renders as `SAN · eval · pct%` (quick 260708).
    expect(list).toMatch(/Ra8 · .+ · 52%/);
    // Blunder moves are NOT listed while hovering the good segment.
    expect(list).not.toMatch(/g4/);
    expect(onHover).toHaveBeenLastCalledWith([{ san: 'Ra8', color: MOVE_QUALITY_GOOD }]);

    fireEvent.mouseLeave(screen.getByTestId('maia-quality-segment-good'));
    expect(onHover).toHaveBeenLastCalledWith(null);
  });

  it('falls back to the static help text when no shown move is graded yet (quick 260705-m3z)', () => {
    render(
      <MaiaMoveQualityBar
        perElo={PER_ELO}
        selectedElo={1500}
        shownSans={['Ra8', 'g4', 'Rb1', 'Ra5']}
        qualityBySan={new Map()}
      />,
    );
    expect(screen.getByTestId('maia-quality-hovered-list').textContent).toMatch(/Hover a segment/);
    expect(screen.queryByTestId('maia-position-verdict')).toBeNull();
  });

  it('lists blunder moves probability-descending on hover', () => {
    render(
      <MaiaMoveQualityBar
        perElo={PER_ELO}
        selectedElo={1500}
        shownSans={['g4', 'Rb1']}
        qualityBySan={grade({ g4: 'blunder', Rb1: 'blunder' })}
      />,
    );
    fireEvent.mouseEnter(screen.getByTestId('maia-quality-segment-blunder'));
    const list = screen.getByTestId('maia-quality-hovered-list').textContent ?? '';
    // g4 (11%) before Rb1 (10%).
    expect(list.indexOf('g4')).toBeLessThan(list.indexOf('Rb1'));
  });

  it('frames the verdict around "you" by default and "your opponent" on the opponent\'s move (quick 260705-m3z)', () => {
    const { rerender } = render(
      <MaiaMoveQualityBar
        perElo={PER_ELO}
        selectedElo={1500}
        shownSans={['Ra8', 'g4', 'Rb1', 'Ra5']}
        qualityBySan={QUALITY}
      />,
    );
    const you = screen.getByTestId('maia-position-verdict').textContent ?? '';
    expect(you).toMatch(/for you\b/);
    expect(you).not.toMatch(/your opponent/);

    rerender(
      <MaiaMoveQualityBar
        perElo={PER_ELO}
        selectedElo={1500}
        shownSans={['Ra8', 'g4', 'Rb1', 'Ra5']}
        qualityBySan={QUALITY}
        isOpponentToMove
      />,
    );
    expect(screen.getByTestId('maia-position-verdict').textContent ?? '').toMatch(/for your opponent/);
  });

  it('opens a prose move popover on hover/focus, showing Maia % + eval (quick 260705-m3z)', () => {
    render(
      <MaiaMoveQualityBar
        perElo={PER_ELO}
        selectedElo={1500}
        shownSans={['Ra8', 'g4', 'Rb1', 'Ra5']}
        qualityBySan={QUALITY}
      />,
    );
    const move = screen.getByTestId('maia-prose-move-g4');
    // Closed at rest.
    expect(screen.queryByTestId('maia-prose-move-tooltip-g4')).toBeNull();
    // Focus (the non-delayed hover-equivalent path) opens it with the move's Maia %.
    fireEvent.focus(move);
    expect(screen.getByTestId('maia-prose-move-tooltip-g4').textContent).toMatch(/11%/);
    // Blur closes it again.
    fireEvent.blur(move);
    expect(screen.queryByTestId('maia-prose-move-tooltip-g4')).toBeNull();
  });

  it('plays a prose move as a free move when clicked while its popover is open (quick 260705-mth)', () => {
    const onPlayMove = vi.fn();
    render(
      <MaiaMoveQualityBar
        perElo={PER_ELO}
        selectedElo={1500}
        shownSans={['Ra8', 'g4', 'Rb1', 'Ra5']}
        qualityBySan={QUALITY}
        onPlayMove={onPlayMove}
      />,
    );
    const move = screen.getByTestId('maia-prose-move-g4');
    // Open the popover first (hover/focus on desktop, or the first tap on touch).
    fireEvent.focus(move);
    // A click whose press began while the popover was open plays the move.
    fireEvent.pointerDown(move);
    fireEvent.click(move);
    expect(onPlayMove).toHaveBeenCalledWith('g4');
  });

  it('the first interaction reveals a prose move without playing it (quick 260705-mth)', () => {
    const onPlayMove = vi.fn();
    render(
      <MaiaMoveQualityBar
        perElo={PER_ELO}
        selectedElo={1500}
        shownSans={['Ra8', 'g4', 'Rb1', 'Ra5']}
        qualityBySan={QUALITY}
        onPlayMove={onPlayMove}
      />,
    );
    const move = screen.getByTestId('maia-prose-move-g4');
    // Press begins while closed (first tap): the click only reveals, never plays.
    fireEvent.pointerDown(move);
    fireEvent.click(move);
    expect(onPlayMove).not.toHaveBeenCalled();
    expect(screen.getByTestId('maia-prose-move-tooltip-g4')).toBeTruthy();
  });
});
