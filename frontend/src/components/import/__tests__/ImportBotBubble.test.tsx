// @vitest-environment jsdom
/**
 * ImportBotBubble.test.tsx — Phase 224 (S-6, D-06; GUESTACT-07) + UAT round 1.
 *
 * Covers both variants: the `welcome` bubble (copy, the /bots link, NO
 * buttons) and the `signup-ask` bubble (copy, the S-4 button pair with D-02's
 * no-third-button rule proven by an exact button count, the umami attribute
 * contract on the sign-up button), plus persona stability across a re-render
 * (the `useMemo(() => pickBot('friendly'), [])` memo).
 */
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';

const mockNavigate = vi.fn();
vi.mock('react-router', async () => {
  const actual = await vi.importActual<typeof import('react-router')>('react-router');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

const mockLogoutForPromotion = vi.fn();
vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({
    logoutForPromotion: mockLogoutForPromotion,
  }),
}));

afterEach(() => {
  cleanup();
  mockNavigate.mockReset();
  mockLogoutForPromotion.mockReset();
});

import { ImportBotBubble } from '@/components/import/ImportBotBubble';
import {
  IMPORT_EXPLORE_COPY,
  IMPORT_GUEST_SIGNUP_COPY,
  IMPORT_WELCOME_COPY,
  type ImportBotBubbleVariant,
} from '@/components/import/importBotBubbleCopy';

function renderBubble(variant: ImportBotBubbleVariant) {
  return render(
    <MemoryRouter>
      <ImportBotBubble variant={variant} />
    </MemoryRouter>,
  );
}

describe('ImportBotBubble (welcome)', () => {
  it('renders the welcome copy with no action buttons', () => {
    renderBubble('welcome');
    const bubble = screen.getByTestId('import-bot-bubble');
    expect(bubble.getAttribute('data-variant')).toBe('welcome');
    expect(bubble.textContent).toContain(IMPORT_WELCOME_COPY);
    expect(bubble.querySelectorAll('button')).toHaveLength(0);
    expect(screen.queryByTestId('btn-signup-free-import-promo')).toBeNull();
  });

  it('links "challenge me to a game" to /bots without a umami attribute', () => {
    renderBubble('welcome');
    const link = screen.getByTestId('import-bot-bubble-link-challenge');
    expect(link.getAttribute('href')).toBe('/bots');
    expect(link.textContent).toBe('challenge me to a game');
    expect(link.getAttribute('data-umami-event')).toBeNull();
  });
});

describe('ImportBotBubble (explore)', () => {
  it('renders the tab tour with five links and no buttons or sign-up text', () => {
    renderBubble('explore');
    const bubble = screen.getByTestId('import-bot-bubble');
    expect(bubble.getAttribute('data-variant')).toBe('explore');
    expect(bubble.textContent).toContain(IMPORT_EXPLORE_COPY);
    expect(bubble.textContent).not.toContain('sign up');
    expect(bubble.querySelectorAll('a')).toHaveLength(5);
    expect(bubble.querySelectorAll('button')).toHaveLength(0);
  });
});

describe('ImportBotBubble (signup-ask)', () => {
  it('renders the import-specific sign-up copy', () => {
    renderBubble('signup-ask');
    const bubble = screen.getByTestId('import-bot-bubble');
    expect(bubble.getAttribute('data-variant')).toBe('signup-ask');
    expect(bubble.textContent).toContain(IMPORT_GUEST_SIGNUP_COPY);
  });

  it('links the five tab fragments to their routes, none with a umami attribute', () => {
    renderBubble('signup-ask');
    const expected: Record<string, [string, string]> = {
      games: ['/library/games', 'Analyze your games'],
      train: ['/train', 'a training session'],
      challenge: ['/bots', 'challenge me to a game'],
      openings: ['/openings', 'openings'],
      endgames: ['/endgames', 'endgames'],
    };
    for (const [slug, [href, text]] of Object.entries(expected)) {
      const link = screen.getByTestId(`import-bot-bubble-link-${slug}`);
      expect(link.getAttribute('href')).toBe(href);
      expect(link.textContent).toBe(text);
      expect(link.getAttribute('data-umami-event')).toBeNull();
    }
    expect(screen.getByTestId('import-bot-bubble').querySelectorAll('a')).toHaveLength(5);
  });

  it('renders exactly two buttons: btn-signup-why-import-promo and btn-signup-free-import-promo (D-02: no third button)', () => {
    renderBubble('signup-ask');
    const bubble = screen.getByTestId('import-bot-bubble');
    expect(bubble.querySelectorAll('button')).toHaveLength(2);
    expect(screen.getByTestId('btn-signup-why-import-promo')).not.toBeNull();
    expect(screen.getByTestId('btn-signup-free-import-promo')).not.toBeNull();
  });

  it('the sign-up button carries the signup-cta umami event with the import-promo source', () => {
    renderBubble('signup-ask');
    const signUp = screen.getByTestId('btn-signup-free-import-promo');
    expect(signUp.getAttribute('data-umami-event')).toBe('signup-cta');
    expect(signUp.getAttribute('data-umami-event-source')).toBe('import-promo');
  });

  it('the rendered persona name is the same after a re-render (useMemo)', () => {
    const { rerender } = renderBubble('signup-ask');
    const firstName = screen.getByTestId('train-bot-name').textContent;
    rerender(
      <MemoryRouter>
        <ImportBotBubble variant="signup-ask" />
      </MemoryRouter>,
    );
    const secondName = screen.getByTestId('train-bot-name').textContent;
    expect(secondName).toBe(firstName);
  });
});
