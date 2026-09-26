// @vitest-environment jsdom
import { afterEach, describe, expect, it } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useReturnToTracking } from '@/hooks/useReturnToTracking';
import { peekReturnTo, stashReturnTo } from '@/lib/returnTo';

afterEach(() => {
  sessionStorage.clear();
});

describe('useReturnToTracking (quick 260926-9bg)', () => {
  it('stashes the path when the visitor arrives signed out', () => {
    renderHook(() => useReturnToTracking(null, '/train'));
    expect(peekReturnTo()).toBe('/train');
  });

  it('clears a stashed path once authenticated', () => {
    stashReturnTo('/train');
    renderHook(() => useReturnToTracking('token', '/train'));
    expect(peekReturnTo()).toBeNull();
  });

  it('does not stash when the token goes away while mounted (logout)', () => {
    const { rerender } = renderHook(
      ({ token }: { token: string | null }) => useReturnToTracking(token, '/train'),
      { initialProps: { token: 'token' as string | null } },
    );
    rerender({ token: null });
    expect(peekReturnTo()).toBeNull();
  });
});
