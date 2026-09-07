// @vitest-environment jsdom
/**
 * EngineUnsupportedNotice (SEED-158, 2026-09-07): the Maia and FlawChess cards
 * must explain the iOS gate instead of pulsing forever, and must render their
 * normal body in every other store status.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, render, screen } from '@testing-library/react';
import { MaiaHumanPanel } from '../MaiaHumanPanel';
import { FlawChessCard } from '../AnalysisTabs';
import {
  markEngineAssetsUnsupported,
  resetEngineAssetsForTests,
} from '@/lib/engine/engineAssetProgress';

vi.mock('@sentry/react', () => ({ captureException: vi.fn() }));

const START_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';

function renderMaiaCard(): void {
  render(
    <MaiaHumanPanel
      selectedElo={1500}
      perElo={[]}
      isLadderComplete={false}
      playedSan={null}
      bestSan={null}
      shownSans={[]}
      qualityBySan={new Map()}
      mover="white"
      engineTopLines={[]}
    />,
  );
}

function renderFlawChessCard(): void {
  render(
    <FlawChessCard
      flawChessEnabled
      setFlawChessEnabled={vi.fn()}
      selectedElo={1500}
      flawChessLoading
      reconciledRankedLines={[]}
      flawChessIsSearching={false}
      flawChessNodesEvaluated={0}
      position={START_FEN}
      currentPly={0}
      boardFlipped={false}
      flawChessTerminalOutcome={null}
      onMoveClick={vi.fn()}
      reconciledStockfishLine={null}
      enginePvLines={[]}
      flawChessRankedLinesForVerdict={[]}
      engineEnabled
      rawProbBySan={new Map()}
      shownSans={[]}
      onHoverMovesChange={vi.fn()}
      onPlayMove={vi.fn()}
      temperature={0}
      setTemperature={vi.fn()}
    />,
  );
}

describe('EngineUnsupportedNotice in the analysis cards', () => {
  beforeEach(() => {
    resetEngineAssetsForTests();
  });
  afterEach(() => {
    cleanup();
    resetEngineAssetsForTests();
  });

  it('Maia card: shows the notice instead of the chart skeleton once the store reports unsupported', () => {
    renderMaiaCard();
    expect(screen.getByTestId('moves-by-rating-chart-skeleton')).toBeTruthy();
    expect(screen.queryByTestId('analysis-maia-unsupported')).toBeNull();

    act(() => {
      markEngineAssetsUnsupported('no-wasm-simd');
    });

    const notice = screen.getByTestId('analysis-maia-unsupported');
    expect(notice.textContent).toContain("This device can't run Maia");
    expect(screen.queryByTestId('moves-by-rating-chart-skeleton')).toBeNull();
  });

  it('Maia card: a store already unsupported at mount renders the notice straight away', () => {
    act(() => {
      markEngineAssetsUnsupported('no-wasm-simd');
    });
    renderMaiaCard();
    expect(screen.getByTestId('analysis-maia-unsupported').textContent).toContain("This device can't run Maia");
  });

  it('FlawChess card: shows the notice instead of the loading skeleton', () => {
    renderFlawChessCard();
    expect(screen.getByTestId('analysis-flawchess-loading')).toBeTruthy();

    act(() => {
      markEngineAssetsUnsupported('no-wasm-simd');
    });

    expect(screen.getByTestId('analysis-flawchess-unsupported').textContent).toContain("This device can't run Maia");
    expect(screen.queryByTestId('analysis-flawchess-loading')).toBeNull();
  });
});
