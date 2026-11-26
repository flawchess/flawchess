import { describe, expect, it } from 'vitest';
import { resolveMoveInfo, type MoveInfoInputs } from '@/lib/moveInfo';
import type { FlawMarker } from '@/types/library';

function marker(overrides: Partial<FlawMarker>): FlawMarker {
  return {
    ply: 10,
    severity: 'blunder',
    tags: [],
    is_user: true,
    move_san: 'Qh5',
    allowed_tactic_motif: null,
    allowed_tactic_confidence: null,
    allowed_tactic_depth: null,
    missed_tactic_motif: null,
    missed_tactic_confidence: null,
    missed_tactic_depth: null,
    ...overrides,
  };
}

function inputs(overrides: Partial<MoveInfoInputs> = {}): MoveInfoInputs {
  return {
    isGameMode: true,
    fastForwardRunning: false,
    san: 'Nf3',
    landingPly: 10,
    flawMarkers: [],
    lastMoveMarker: undefined,
    ...overrides,
  };
}

describe('resolveMoveInfo', () => {
  it('is null outside game mode, during a Jump run and at the root', () => {
    expect(resolveMoveInfo(inputs({ isGameMode: false }))).toBeNull();
    expect(resolveMoveInfo(inputs({ fastForwardRunning: true }))).toBeNull();
    expect(resolveMoveInfo(inputs({ san: null }))).toBeNull();
  });

  it('names the board badge on the move target square', () => {
    const cases = [
      [{ square: 'f3', best: true }, 'best'],
      [{ square: 'f3', good: true }, 'good'],
      [{ square: 'f3', gem: true }, 'gem'],
      [{ square: 'f3', great: true }, 'great'],
      [{ square: 'f3', book: true }, 'book'],
      [{ square: 'f3', severity: 'inaccuracy' as const }, 'inaccuracy'],
    ] as const;
    for (const [lastMoveMarker, quality] of cases) {
      expect(resolveMoveInfo(inputs({ lastMoveMarker }))).toEqual({
        kind: 'quality',
        san: 'Nf3',
        quality,
        facepalm: false,
      });
    }
  });

  it('has no quality when the board shows no badge', () => {
    expect(resolveMoveInfo(inputs())).toEqual({ kind: 'quality', san: 'Nf3', quality: null, facepalm: false });
  });

  it('uses the flaw headline for a main-line mistake or blunder with tactics', () => {
    const info = resolveMoveInfo(
      inputs({
        san: 'Qh5',
        flawMarkers: [marker({ ply: 10, allowed_tactic_motif: 'fork', allowed_tactic_depth: null })],
        lastMoveMarker: { square: 'h5', severity: 'blunder' },
      }),
    );
    expect(info).toMatchObject({
      kind: 'flaw',
      headline: { san: 'Qh5', severity: 'blunder', tactics: [{ orientation: 'allowed', text: 'allowed fork' }] },
    });
  });

  it('uses the worded badge for a bare flaw headline (no tactics, no facepalm score)', () => {
    const info = resolveMoveInfo(
      inputs({
        san: 'Qh5',
        flawMarkers: [marker({ ply: 10, severity: 'mistake' })],
        lastMoveMarker: { square: 'h5', severity: 'mistake' },
      }),
    );
    expect(info).toEqual({ kind: 'quality', san: 'Qh5', quality: 'mistake', facepalm: false });
  });

  it('reads a sideline move from its board badge (no main-line ply)', () => {
    const info = resolveMoveInfo(
      inputs({
        landingPly: -1,
        flawMarkers: [marker({ ply: 10, allowed_tactic_motif: 'fork' })],
        lastMoveMarker: { square: 'f3', severity: 'blunder', facepalm: true },
      }),
    );
    expect(info).toEqual({ kind: 'quality', san: 'Nf3', quality: 'blunder', facepalm: true });
  });
});
