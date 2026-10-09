// @vitest-environment jsdom
/**
 * Phase 137 Plan 02 — EngineLines render tests.
 * Updated Quick 260627-mt8: depth badge moved to the engine info line (Analysis.tsx),
 * so EngineLines no longer takes a `depth` prop or renders a `d{depth}` badge.
 *
 * Verifies:
 *  (a) two fixture PV lines render two rows with correct score (badge) format
 *  (c) fireEvent.click on engine-line-0-move-0 calls onMoveClick("e2","e4")
 *  (d) isAnalyzing && empty pvLines → shows "engine-lines-analyzing"
 *      isAnalyzing && non-empty pvLines → does NOT show "engine-lines-analyzing"
 */

import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';

import { EngineLines, EngineLinesSkeleton } from '../EngineLines';
import { TooltipProvider } from '@/components/ui/tooltip';
import type { PvLine } from '@/hooks/uciParser';
import { DEFAULT_LINES } from '@/lib/engineSettings';
import { BEST_MOVE_ARROW, STOCKFISH_BADGE_SECONDARY } from '@/lib/theme';

const START_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';

beforeAll(() => {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  });
  class ResizeObserverStub {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  (globalThis as unknown as { ResizeObserver: typeof ResizeObserverStub }).ResizeObserver =
    ResizeObserverStub;
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const LINE_CP: PvLine = {
  multipv: 1,
  depth: 20,
  moves: ['e2e4', 'd7d5', 'e4d5'],
  evalCp: 142,
  evalMate: null,
};

const LINE_MATE: PvLine = {
  multipv: 2,
  depth: 20,
  moves: ['d1h5', 'f7f6', 'h5e5'],
  evalCp: null,
  evalMate: 3,
};

const TWO_LINES: PvLine[] = [LINE_CP, LINE_MATE];

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('EngineLines', () => {
  it('(a) renders two PV lines with correct score format', () => {
    render(
      <EngineLines
        maxLines={DEFAULT_LINES}
        pvLines={TWO_LINES}
        isAnalyzing={false}
        onMoveClick={vi.fn()}
      />,
    );

    // Line 0 — evalCp 142 → "+1.4" (1-digit)
    expect(screen.getByText('+1.4')).toBeTruthy();
    // Line 1 — evalMate 3 → "#+3"
    expect(screen.getByText('#+3')).toBeTruthy();
  });

  it('(c) clicking engine-line-0-move-0 calls onMoveClick(["e2e4"])', () => {
    const onMoveClick = vi.fn();
    render(
      <EngineLines
        maxLines={DEFAULT_LINES}
        pvLines={TWO_LINES}
        isAnalyzing={false}
        onMoveClick={onMoveClick}
      />,
    );

    const chip = screen.getByTestId('engine-line-0-move-0');
    fireEvent.click(chip);
    expect(onMoveClick).toHaveBeenCalledTimes(1);
    expect(onMoveClick).toHaveBeenCalledWith(['e2e4']);
  });

  it('clicking a later move passes the full UCI prefix up to that move', () => {
    // LINE_CP = ['e2e4', 'd7d5', 'e4d5']; clicking move index 2 must graft the
    // whole line up to it (not just the single clicked move) — the UAT bug fix.
    const onMoveClick = vi.fn();
    render(
      <EngineLines
        maxLines={DEFAULT_LINES}
        pvLines={[LINE_CP]}
        isAnalyzing={false}
        onMoveClick={onMoveClick}
      />,
    );

    fireEvent.click(screen.getByTestId('engine-line-0-move-2'));
    expect(onMoveClick).toHaveBeenCalledWith(['e2e4', 'd7d5', 'e4d5']);
  });

  it('(d) isAnalyzing && empty pvLines → shows analyzing indicator', () => {
    render(
      <EngineLines
        maxLines={DEFAULT_LINES}
        pvLines={[]}
        isAnalyzing={true}
        onMoveClick={vi.fn()}
      />,
    );
    // Quick 260627-r9g item 3: the "Analyzing…" text is now a skeleton placeholder.
    expect(screen.getByTestId('engine-lines-analyzing')).toBeTruthy();
    expect(screen.queryByText('Analyzing…')).toBeNull();
  });

  it('(d) isAnalyzing && non-empty pvLines → does NOT show analyzing indicator', () => {
    render(
      <EngineLines
        maxLines={DEFAULT_LINES}
        pvLines={TWO_LINES}
        isAnalyzing={true}
        onMoveClick={vi.fn()}
      />,
    );
    expect(screen.queryByTestId('engine-lines-analyzing')).toBeNull();
  });

  it('move chips are <button> elements (semantic HTML)', () => {
    render(
      <EngineLines
        maxLines={DEFAULT_LINES}
        pvLines={[LINE_CP]}
        isAnalyzing={false}
        onMoveClick={vi.fn()}
      />,
    );
    const chip = screen.getByTestId('engine-line-0-move-0');
    expect(chip.tagName.toLowerCase()).toBe('button');
  });

  it('negative evalCp displays without leading +', () => {
    const negativeLine: PvLine = {
      multipv: 1,
      depth: 15,
      moves: ['e7e5'],
      evalCp: -33,
      evalMate: null,
    };
    render(
      <EngineLines
        maxLines={DEFAULT_LINES}
        pvLines={[negativeLine]}
        isAnalyzing={false}
        onMoveClick={vi.fn()}
      />,
    );
    expect(screen.getByText('-0.3')).toBeTruthy();
  });

  it('negative evalMate displays as #-N', () => {
    const losingMate: PvLine = {
      multipv: 1,
      depth: 15,
      moves: ['e7e5'],
      evalCp: null,
      evalMate: -2,
    };
    render(
      <EngineLines
        maxLines={DEFAULT_LINES}
        pvLines={[losingMate]}
        isAnalyzing={false}
        onMoveClick={vi.fn()}
      />,
    );
    expect(screen.getByText('#-2')).toBeTruthy();
  });

  it('!isAnalyzing && empty pvLines → renders empty (no spinner, no error)', () => {
    render(
      <EngineLines
        maxLines={DEFAULT_LINES}
        pvLines={[]}
        isAnalyzing={false}
        onMoveClick={vi.fn()}
      />,
    );
    expect(screen.queryByTestId('engine-lines-analyzing')).toBeNull();
    expect(screen.queryByText('Analyzing…')).toBeNull();
  });

  it('with baseFen, move chips are tooltip-wrapped and still clickable (thl item 5)', () => {
    const onMoveClick = vi.fn();
    render(
      <TooltipProvider>
        <EngineLines
          maxLines={DEFAULT_LINES}
          pvLines={[LINE_CP]}
          isAnalyzing={false}
          baseFen={START_FEN}
          onMoveClick={onMoveClick}
        />
      </TooltipProvider>,
    );
    const chip = screen.getByTestId('engine-line-0-move-0');
    expect(chip.tagName.toLowerCase()).toBe('button');
    fireEvent.click(chip);
    expect(onMoveClick).toHaveBeenCalledWith(['e2e4']);
  });

  it('reads per-line evalCp/evalMate not a non-existent score field', () => {
    // This test verifies the contract at compile time via the PvLine fixture.
    // If PvLine had a `score` field and EngineLines used it, this fixture
    // without a `score` field would fail TypeScript.
    const lineWithOnlyCp: PvLine = {
      multipv: 1,
      depth: 10,
      moves: ['g1f3'],
      evalCp: 50,
      evalMate: null,
    };
    render(
      <EngineLines
        maxLines={DEFAULT_LINES}
        pvLines={[lineWithOnlyCp]}
        isAnalyzing={false}
        onMoveClick={vi.fn()}
      />,
    );
    expect(screen.getByText('+0.5')).toBeTruthy();
  });

  it('chevron expands a >5-ply line to reveal the rest of the PV', () => {
    // 7 plies — collapsed shows the first 5; the expand chevron reveals 6 & 7.
    const longLine: PvLine = {
      multipv: 1,
      depth: 22,
      moves: ['e2e4', 'e7e5', 'g1f3', 'b8c6', 'f1b5', 'a7a6', 'b5a4'],
      evalCp: 20,
      evalMate: null,
    };
    render(
      <EngineLines
        maxLines={DEFAULT_LINES}
        pvLines={[longLine]}
        isAnalyzing={false}
        onMoveClick={vi.fn()}
      />,
    );

    // Collapsed: moves 5 and 6 are not rendered.
    expect(screen.queryByTestId('engine-line-0-move-5')).toBeNull();
    expect(screen.getByTestId('engine-line-0-move-4')).toBeTruthy();

    fireEvent.click(screen.getByTestId('engine-line-0-expand'));

    // Expanded: the remaining plies are now rendered.
    expect(screen.getByTestId('engine-line-0-move-5')).toBeTruthy();
    expect(screen.getByTestId('engine-line-0-move-6')).toBeTruthy();
  });

  it('move chips never wrap inside, so O-O-O stays on one row (Phase 237 UAT)', () => {
    render(
      <EngineLines maxLines={1} pvLines={[LINE_CP]} isAnalyzing={false} onMoveClick={vi.fn()} compact />,
    );
    expect(screen.getByTestId('engine-line-0-move-0').className).toContain('whitespace-nowrap');
  });

  it('renders at most maxLines rows (Phase 228, D-16)', () => {
    const five: PvLine[] = [1, 2, 3, 4, 5].map((n) => ({ ...LINE_CP, multipv: n }));
    const three = render(
      <EngineLines pvLines={five} isAnalyzing={false} maxLines={3} onMoveClick={vi.fn()} />,
    );
    expect(screen.getAllByLabelText(/^Line \d+:/)).toHaveLength(3);
    three.unmount();
    render(
      <EngineLines
        pvLines={five}
        isAnalyzing={false}
        maxLines={DEFAULT_LINES}
        onMoveClick={vi.fn()}
      />,
    );
    expect(screen.getAllByLabelText(/^Line \d+:/)).toHaveLength(2);
  });

  it('badge styling lock: line 1 solid BEST_MOVE_ARROW, every later line STOCKFISH_BADGE_SECONDARY, no dark-ink text override', () => {
    const four: PvLine[] = [1, 2, 3, 4].map((n) => ({ ...LINE_CP, multipv: n }));
    render(<EngineLines pvLines={four} isAnalyzing={false} maxLines={4} onMoveClick={vi.fn()} />);
    const badges = screen.getAllByLabelText(/^Line \d+:/);
    expect(badges).toHaveLength(4);
    expect(badges[0]!.style.backgroundColor).toBe(BEST_MOVE_ARROW);
    for (const badge of badges.slice(1)) {
      expect(badge.style.backgroundColor).toBe(STOCKFISH_BADGE_SECONDARY);
    }
    for (const badge of badges) {
      // White text comes from BADGE_CLASS; no inline color override on any row.
      expect(badge.style.color).toBe('');
      expect(badge.className).toContain('text-white');
    }
  });

  it('the analyzing skeleton shows maxLines placeholder rows', () => {
    render(<EngineLines pvLines={[]} isAnalyzing={true} maxLines={4} onMoveClick={vi.fn()} />);
    expect(screen.getByTestId('engine-lines-analyzing').children).toHaveLength(4);
  });

  it('no chevron when the line is <= 5 plies', () => {
    render(
      <EngineLines
        maxLines={DEFAULT_LINES}
        pvLines={[LINE_CP]} // 3 plies
        isAnalyzing={false}
        onMoveClick={vi.fn()}
      />,
    );
    expect(screen.queryByTestId('engine-line-0-expand')).toBeNull();
  });
});

// ─── G-213-34 (supersedes D-12): EngineLinesSkeleton reads no download state ──

describe('EngineLinesSkeleton', () => {
  it('renders the pulsing placeholder rows (the ONLY thing this skeleton ever renders now)', () => {
    render(<EngineLinesSkeleton testId="skel" rows={DEFAULT_LINES} />);
    const el = screen.getByTestId('skel');
    expect(el).toBeTruthy();
    expect(el.getAttribute('aria-busy')).toBe('true');
    expect(el.getAttribute('aria-label')).toBe('Loading engine lines');
    expect(screen.queryByTestId('skel-progress')).toBeNull();
  });

  it('container min-height follows the row count; defaults keep today\'s heights (60px / 50px)', () => {
    render(<EngineLinesSkeleton testId="default-variant" rows={2} />);
    render(<EngineLinesSkeleton testId="compact-variant" rows={2} compact />);
    render(<EngineLinesSkeleton testId="five-variant" rows={5} />);
    render(<EngineLinesSkeleton testId="five-compact-variant" rows={5} compact />);

    expect(screen.getByTestId('default-variant').style.minHeight).toBe('60px');
    expect(screen.getByTestId('compact-variant').style.minHeight).toBe('50px');
    expect(screen.getByTestId('five-variant').style.minHeight).toBe('150px');
    expect(screen.getByTestId('five-compact-variant').style.minHeight).toBe('125px');
  });

  it('renders exactly `rows` placeholder rows', () => {
    render(<EngineLinesSkeleton testId="skel-rows" rows={5} />);
    expect(screen.getByTestId('skel-rows').children).toHaveLength(5);
  });

  it('aria-busy and aria-label are always set', () => {
    render(<EngineLinesSkeleton testId="skel-aria" rows={DEFAULT_LINES} />);
    const el = screen.getByTestId('skel-aria');
    expect(el.getAttribute('aria-busy')).toBe('true');
    expect(el.getAttribute('aria-label')).toBe('Loading engine lines');
  });
});
