// @vitest-environment jsdom
/**
 * MoveStats vitest suite — covers the accuracy
 * strip (canonical-or-muted), all 8 rows always rendering, counts
 * derived from flaw_markers/eval_series, opponent tiers surfaced, and
 * the player-first column reorder.
 */

import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, fireEvent } from '@testing-library/react';
import { MoveStats } from '../MoveStats';
import type { EvalPoint, FlawMarker, GameFlawCard } from '@/types/library';
import { FACEPALM_HIGH_CUTOFF } from '@/lib/facepalm';

afterEach(() => {
  cleanup();
});

const GAME_ID = 123;

function makeGame(overrides: Partial<GameFlawCard> = {}): GameFlawCard {
  return {
    game_id: GAME_ID,
    user_result: 'win',
    played_at: '2026-01-15T10:00:00Z',
    time_control_bucket: 'rapid',
    platform: 'lichess',
    platform_url: 'https://lichess.org/abc',
    white_username: 'Alice',
    black_username: 'Bob',
    white_rating: 1850,
    black_rating: 1720,
    opening_name: 'Sicilian Defense',
    opening_eco: 'B20',
    user_color: 'white',
    ply_count: 80,
    termination: 'checkmate',
    time_control_str: '10+5',
    result_fen: null,
    severity_counts: { inaccuracy: 0, mistake: 0, blunder: 0 },
    white_accuracy: null,
    black_accuracy: null,
    chips: [],
    analysis_state: 'analyzed',
    eval_series: [],
    flaw_markers: [],
    phase_transitions: { middlegame_ply: null, endgame_ply: null },
    moves: [],
    active_eval_status: null,
    opening_ply_count: 0,
    ...overrides,
  };
}

function marker(overrides: Partial<FlawMarker> & Pick<FlawMarker, 'ply' | 'severity'>): FlawMarker {
  return {
    tags: [],
    is_user: false,
    move_san: null,
    allowed_tactic_motif: null,
    allowed_tactic_confidence: null,
    allowed_tactic_depth: null,
    missed_tactic_motif: null,
    missed_tactic_confidence: null,
    missed_tactic_depth: null,
    ...overrides,
  };
}

function point(overrides: Partial<EvalPoint> & Pick<EvalPoint, 'ply'>): EvalPoint {
  return {
    es: null,
    eval_cp: null,
    eval_mate: null,
    clock_seconds: null,
    move_seconds: null,
    best_move: null,
    best_move_tier: null,
    maia_prob: null,
    ...overrides,
  };
}

const ALL_CATEGORIES = [
  'gem',
  'great',
  'best',
  'good',
  'inaccuracy',
  'mistake',
  'blunder',
  'facepalm',
] as const;

describe('MoveStats — all 8 rows always render', () => {
  it('renders exactly 8 category rows with muted 0s for an all-zero analyzed game', () => {
    render(<MoveStats game={makeGame()} />);
    for (const category of ALL_CATEGORIES) {
      expect(screen.getByTestId(`move-stats-row-${category}`)).toBeTruthy();
      const white = screen.getByTestId(`move-stats-cell-${category}-white`);
      const black = screen.getByTestId(`move-stats-cell-${category}-black`);
      expect(white.textContent).toBe('0');
      expect(black.textContent).toBe('0');
      // Zero cells are inert — no button role, no interactive tag.
      expect(white.tagName).not.toBe('BUTTON');
      expect(black.tagName).not.toBe('BUTTON');
    }
  });
});

describe('MoveStats — accuracy strip', () => {
  it('renders a numeric white cell and a muted em-dash black cell when black_accuracy is null', () => {
    render(<MoveStats game={makeGame({ white_accuracy: 87.4, black_accuracy: null })} />);
    const white = screen.getByTestId('move-stats-accuracy-white');
    const black = screen.getByTestId('move-stats-accuracy-black');
    // Pills carry a leading color swatch span (aria-hidden, no text content).
    expect(white.textContent).toBe('87%');
    expect(black.textContent).toBe('—');
  });

  it('never renders an ACPL value or literal "_imported" text', () => {
    const { container } = render(
      <MoveStats game={makeGame({ white_accuracy: 92, black_accuracy: 88 })} />,
    );
    expect(container.textContent).not.toContain('ACPL');
    expect(container.textContent).not.toContain('imported');
  });
});

describe('MoveStats — non-zero cell interaction', () => {
  it('dispatches { kind: "category", category, side } on click for a non-zero cell', () => {
    const onCellActivate = vi.fn();
    const game = makeGame({
      flaw_markers: [marker({ ply: 0, severity: 'blunder', is_user: true })],
    });
    render(<MoveStats game={game} onCellActivate={onCellActivate} />);
    const cell = screen.getByTestId('move-stats-cell-blunder-white');
    expect(cell.tagName).toBe('BUTTON');
    fireEvent.click(cell);
    expect(onCellActivate).toHaveBeenCalledWith({ kind: 'category', category: 'blunder', side: 'white' });
  });

  it('reads inaccuracy count from flaw_markers, not severity_counts', () => {
    const game = makeGame({
      severity_counts: { inaccuracy: 99, mistake: 0, blunder: 0 },
      flaw_markers: [marker({ ply: 0, severity: 'inaccuracy' })],
    });
    render(<MoveStats game={game} />);
    // flaw_markers has exactly 1 inaccuracy on ply 0 (white) — must read 1, not 99.
    expect(screen.getByTestId('move-stats-cell-inaccuracy-white').textContent).toBe('1');
  });
});

describe('MoveStats — opponent positive tiers surfaced', () => {
  it('shows an opponent-ply gem in the opponent column', () => {
    // user_color=white, so ply 1 (odd=black) is the opponent.
    const game = makeGame({
      user_color: 'white',
      eval_series: [point({ ply: 1, best_move_tier: 'gem' })],
    });
    render(<MoveStats game={game} />);
    expect(screen.getByTestId('move-stats-cell-gem-black').textContent).toBe('1');
    expect(screen.getByTestId('move-stats-cell-gem-white').textContent).toBe('0');
  });
});

describe('MoveStats — player-first column order', () => {
  it('flips column order with game.user_color while cell background stays literal-color', () => {
    const whiteUserGame = makeGame({ user_color: 'white' });
    const { container: c1 } = render(<MoveStats game={whiteUserGame} />);
    // children[0] is the "Accuracies" label; the player pill comes right after.
    const strip1 = c1.querySelector('[data-testid="move-stats-accuracy-strip"]');
    expect(strip1?.children[1]?.getAttribute('data-testid')).toBe('move-stats-accuracy-white');
    cleanup();

    const blackUserGame = makeGame({ user_color: 'black' });
    const { container: c2 } = render(<MoveStats game={blackUserGame} />);
    const strip2 = c2.querySelector('[data-testid="move-stats-accuracy-strip"]');
    expect(strip2?.children[1]?.getAttribute('data-testid')).toBe('move-stats-accuracy-black');

    // Literal color background is unchanged regardless of column order.
    const whiteCell = screen.getByTestId('move-stats-accuracy-white');
    expect((whiteCell as HTMLElement).style.backgroundColor).not.toBe('');
  });
});

describe('MoveStats — Best/Good rows render the new circular icons', () => {
  it('renders BestMoveIcon and GoodMoveIcon svg titles in their respective rows', () => {
    render(<MoveStats game={makeGame()} />);
    const bestRow = screen.getByTestId('move-stats-row-best');
    const goodRow = screen.getByTestId('move-stats-row-good');
    expect(bestRow.querySelector('title')?.textContent).toBe('Best move');
    expect(goodRow.querySelector('title')?.textContent).toBe('Good move');
  });
});

describe('MoveStats — accuracy info popover', () => {
  it('replaces the bullseye with an info trigger that explains accuracy and every move quality', () => {
    render(<MoveStats game={makeGame()} />);
    const strip = screen.getByTestId('move-stats-accuracy-strip');
    expect(strip.textContent).not.toContain('🎯');

    fireEvent.click(screen.getByTestId('move-stats-info'));
    const body = document.body.textContent ?? '';
    for (const label of ['Accuracy', 'Gem', 'Great', 'Best', 'Good', 'Inaccuracy', 'Mistake', 'Blunder', 'Facepalm', 'Lichess']) {
      expect(body).toContain(label);
    }
  });

  it('defines Facepalm from the cut constant, keeps the Blunder wording and states the Lichess sum', () => {
    render(<MoveStats game={makeGame()} />);
    fireEvent.click(screen.getByTestId('move-stats-info'));
    const body = document.body.textContent ?? '';
    expect(body).toContain(`facepalm score of ${FACEPALM_HIGH_CUTOFF}% or more`);
    expect(body).toContain('Costs 15% winning chances or more.');
    expect(body).toContain("Blunders and facepalms together make up Lichess's blunder count.");
  });

  it('suffixes the info trigger testid with the game id', () => {
    render(<MoveStats game={makeGame()} gameId={GAME_ID} />);
    expect(screen.getByTestId(`move-stats-info-${GAME_ID}`)).toBeTruthy();
  });
});

describe('MoveStats — mobile compact row (D-05)', () => {
  it('renders gem, great, best, mistake, blunder, facepalm and the chevron, no inaccuracy or good cell', () => {
    render(<MoveStats game={makeGame()} showCompactRow />);
    for (const category of ['gem', 'great', 'best', 'mistake', 'blunder', 'facepalm']) {
      expect(screen.getByTestId(`move-stats-compact-cell-${category}`)).toBeTruthy();
    }
    expect(screen.queryByTestId('move-stats-compact-cell-inaccuracy')).toBeNull();
    expect(screen.queryByTestId('move-stats-compact-cell-good')).toBeNull();
    expect(screen.getByTestId('move-stats-expand-toggle')).toBeTruthy();
    expect(screen.getByTestId('move-stats-compact').className).toContain('grid-cols-7');
  });

  it('counts user-side with the Blunder / Facepalm split and dispatches the facepalm ref on tap', () => {
    const onCellActivate = vi.fn();
    const aboveCut = (FACEPALM_HIGH_CUTOFF + 1) / 100;
    const game = makeGame({
      user_color: 'white',
      flaw_markers: [
        marker({ ply: 0, severity: 'blunder', is_user: true, facepalm_score: aboveCut }),
        marker({ ply: 2, severity: 'blunder', is_user: true }),
        // Opponent facepalm must not count in the user-side compact row.
        marker({ ply: 1, severity: 'blunder', is_user: false, facepalm_score: aboveCut }),
      ],
    });
    render(<MoveStats game={game} showCompactRow onCellActivate={onCellActivate} />);
    // The count is the first span; the icon's glyph text sits after it in textContent.
    const countOf = (category: string): string | undefined =>
      screen.getByTestId(`move-stats-compact-cell-${category}`).querySelector('span')?.textContent;
    expect(countOf('blunder')).toBe('1');
    const facepalmCell = screen.getByTestId('move-stats-compact-cell-facepalm');
    expect(countOf('facepalm')).toBe('1');
    fireEvent.click(facepalmCell);
    expect(onCellActivate).toHaveBeenCalledWith({ kind: 'category', category: 'facepalm', side: 'white' });
  });
});

describe('MoveStats - outlinedRefs filter ring (D-20, D-28)', () => {
  const RING_CLASS_FRAGMENT = 'ring-2';
  const aboveCut = (FACEPALM_HIGH_CUTOFF + 1) / 100;
  // user_color 'white': a facepalm blunder and a mistake on each side.
  function ringedGame(): GameFlawCard {
    return makeGame({
      user_color: 'white',
      flaw_markers: [
        marker({ ply: 0, severity: 'blunder', is_user: true, facepalm_score: aboveCut }),
        marker({ ply: 2, severity: 'mistake', is_user: true }),
        marker({ ply: 1, severity: 'blunder', is_user: false, facepalm_score: aboveCut }),
        marker({ ply: 3, severity: 'mistake', is_user: false }),
      ],
    });
  }

  it('rings every matching table cell and the matching compact cells, and only those', () => {
    render(
      <MoveStats
        game={ringedGame()}
        showCompactRow
        outlinedRefs={[
          { kind: 'category', category: 'facepalm', side: 'white' },
          { kind: 'category', category: 'mistake', side: 'white' },
        ]}
      />,
    );
    const cls = (id: string): string => screen.getByTestId(id).className;
    expect(cls('move-stats-cell-facepalm-white')).toContain(RING_CLASS_FRAGMENT);
    expect(cls('move-stats-cell-mistake-white')).toContain(RING_CLASS_FRAGMENT);
    expect(cls('move-stats-cell-facepalm-black')).not.toContain(RING_CLASS_FRAGMENT);
    expect(cls('move-stats-cell-mistake-black')).not.toContain(RING_CLASS_FRAGMENT);
    expect(cls('move-stats-compact-cell-facepalm')).toContain(RING_CLASS_FRAGMENT);
    expect(cls('move-stats-compact-cell-mistake')).toContain(RING_CLASS_FRAGMENT);
  });

  it('rings nothing without outlinedRefs (the AnalysisTagsPanel case)', () => {
    render(<MoveStats game={ringedGame()} showCompactRow />);
    for (const id of [
      'move-stats-cell-facepalm-white',
      'move-stats-cell-mistake-white',
      'move-stats-compact-cell-facepalm',
      'move-stats-compact-cell-mistake',
    ]) {
      expect(screen.getByTestId(id).className).not.toContain(RING_CLASS_FRAGMENT);
    }
  });
});
