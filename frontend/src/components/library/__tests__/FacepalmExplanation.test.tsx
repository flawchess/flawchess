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
    const { container } = render(<FacepalmExplanation score={0.957} />);
    expect(container.textContent).toContain('Facepalm 95%');
    expect(container.textContent).toContain('a player at your level');
    expect(container.textContent).not.toContain('their level');
  });

  it('speaks of their level for an opponent blunder', () => {
    const { container } = render(<FacepalmExplanation score={0.4} byOpponent />);
    expect(container.textContent).toContain('Facepalm 40%');
    expect(container.textContent).toContain('a player at their level');
    expect(container.textContent).not.toContain('your level');
  });
});
