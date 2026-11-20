// @vitest-environment jsdom
/**
 * FacepalmExplanation: the one shared explanation copy (D-23). Pins the floored
 * heading percent and the "your" / "their" switch for an opponent's blunder.
 */
import { describe, it, expect, afterEach } from 'vitest';
import { cleanup, render } from '@testing-library/react';
import { FacepalmExplanation } from '../FacepalmExplanation';

afterEach(cleanup);

describe('FacepalmExplanation', () => {
  it('heads with the floored percent and speaks of your level by default', () => {
    const { container } = render(<FacepalmExplanation score={0.957} type="allowed_loss" />);
    expect(container.textContent).toContain('Facepalm 95%');
    expect(container.textContent).toContain('a player at your level');
    expect(container.textContent).not.toContain('their level');
  });

  it('speaks of their level for an opponent blunder', () => {
    const { container } = render(<FacepalmExplanation score={0.4} type="missed_win" byOpponent />);
    expect(container.textContent).toContain('Facepalm 40%');
    expect(container.textContent).toContain('a player at their level');
    expect(container.textContent).not.toContain('your level');
  });

  it('names a missed win in one line', () => {
    const { getByTestId } = render(<FacepalmExplanation score={0.8} type="missed_win" />);
    expect(getByTestId('facepalm-explanation-type').textContent).toBe(
      'Missed win: the best move won material or led to checkmate, and was not played.',
    );
  });

  it('names an allowed loss in one line', () => {
    const { getByTestId } = render(<FacepalmExplanation score={0.8} type="allowed_loss" />);
    expect(getByTestId('facepalm-explanation-type').textContent).toBe(
      'Allowed loss: the move gave away material or allowed checkmate.',
    );
  });

  it('keeps the type line for an opponent blunder', () => {
    const { getByTestId } = render(<FacepalmExplanation score={0.8} type="missed_win" byOpponent />);
    expect(getByTestId('facepalm-explanation-type').textContent).toContain('Missed win:');
  });

  it('uses no probability wording in the type line (D-05)', () => {
    for (const type of ['missed_win', 'allowed_loss'] as const) {
      const { getByTestId, unmount } = render(<FacepalmExplanation score={0.8} type={type} />);
      expect(getByTestId('facepalm-explanation-type').textContent).not.toMatch(/chance|probab|likel/i);
      unmount();
    }
  });
});
