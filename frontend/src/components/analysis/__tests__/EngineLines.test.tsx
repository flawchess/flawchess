// @vitest-environment jsdom
/**
 * Phase 137 Plan 02 — EngineLines render tests.
 *
 * Verifies:
 *  (a) two fixture PV lines render two chip rows with correct score format
 *  (b) depth badge appears once (on line 0 only)
 *  (c) fireEvent.click on engine-line-0-move-0 calls onMoveClick("e2","e4")
 *  (d) isAnalyzing && empty pvLines → shows "engine-lines-analyzing"
 *      isAnalyzing && non-empty pvLines → does NOT show "engine-lines-analyzing"
 */

import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';

import { EngineLines } from '../EngineLines';
import type { PvLine } from '@/hooks/uciParser';

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
        pvLines={TWO_LINES}
        depth={20}
        isAnalyzing={false}
        onMoveClick={vi.fn()}
      />,
    );

    // Line 0 — evalCp 142 → "+1.4" (1-digit)
    expect(screen.getByText('+1.4')).toBeTruthy();
    // Line 1 — evalMate 3 → "#+3"
    expect(screen.getByText('#+3')).toBeTruthy();
  });

  it('(b) depth badge appears exactly once (on line 0)', () => {
    render(
      <EngineLines
        pvLines={TWO_LINES}
        depth={20}
        isAnalyzing={false}
        onMoveClick={vi.fn()}
      />,
    );
    const badges = screen.getAllByText('d20');
    expect(badges).toHaveLength(1);
  });

  it('(c) clicking engine-line-0-move-0 calls onMoveClick("e2","e4")', () => {
    const onMoveClick = vi.fn();
    render(
      <EngineLines
        pvLines={TWO_LINES}
        depth={20}
        isAnalyzing={false}
        onMoveClick={onMoveClick}
      />,
    );

    const chip = screen.getByTestId('engine-line-0-move-0');
    fireEvent.click(chip);
    expect(onMoveClick).toHaveBeenCalledTimes(1);
    expect(onMoveClick).toHaveBeenCalledWith('e2', 'e4');
  });

  it('(d) isAnalyzing && empty pvLines → shows analyzing indicator', () => {
    render(
      <EngineLines
        pvLines={[]}
        depth={0}
        isAnalyzing={true}
        onMoveClick={vi.fn()}
      />,
    );
    expect(screen.getByTestId('engine-lines-analyzing')).toBeTruthy();
    expect(screen.getByText('Analyzing…')).toBeTruthy();
  });

  it('(d) isAnalyzing && non-empty pvLines → does NOT show analyzing indicator', () => {
    render(
      <EngineLines
        pvLines={TWO_LINES}
        depth={20}
        isAnalyzing={true}
        onMoveClick={vi.fn()}
      />,
    );
    expect(screen.queryByTestId('engine-lines-analyzing')).toBeNull();
  });

  it('move chips are <button> elements (semantic HTML)', () => {
    render(
      <EngineLines
        pvLines={[LINE_CP]}
        depth={15}
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
        pvLines={[negativeLine]}
        depth={15}
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
        pvLines={[losingMate]}
        depth={15}
        isAnalyzing={false}
        onMoveClick={vi.fn()}
      />,
    );
    expect(screen.getByText('#-2')).toBeTruthy();
  });

  it('!isAnalyzing && empty pvLines → renders empty (no spinner, no error)', () => {
    render(
      <EngineLines
        pvLines={[]}
        depth={0}
        isAnalyzing={false}
        onMoveClick={vi.fn()}
      />,
    );
    expect(screen.queryByTestId('engine-lines-analyzing')).toBeNull();
    expect(screen.queryByText('Analyzing…')).toBeNull();
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
        pvLines={[lineWithOnlyCp]}
        depth={10}
        isAnalyzing={false}
        onMoveClick={vi.fn()}
      />,
    );
    expect(screen.getByText('+0.5')).toBeTruthy();
  });
});
