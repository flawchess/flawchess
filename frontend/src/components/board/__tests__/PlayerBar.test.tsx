// @vitest-environment jsdom
import { describe, it, expect, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import { PlayerBar } from '../PlayerBar';

describe('PlayerBar', () => {
  afterEach(() => {
    cleanup();
  });

  it('renders name + ELO in parentheses with the white glyph', () => {
    render(<PlayerBar isWhite name="Magnus" rating={2839} clockSeconds={179.4} testId="pb" />);
    const row = screen.getByTestId('pb');
    expect(row.textContent).toContain('■');
    expect(row.textContent).toContain('Magnus');
    expect(row.textContent).toContain('(2839)');
  });

  it('uses the hollow glyph for black', () => {
    render(<PlayerBar isWhite={false} name="Hikaru" rating={2802} clockSeconds={60} testId="pb" />);
    expect(screen.getByTestId('pb').textContent).toContain('□');
  });

  it('formats the clock as m:ss (floored)', () => {
    render(<PlayerBar isWhite name="A" rating={1500} clockSeconds={179.4} testId="pb" />);
    expect(screen.getByTestId('pb').textContent).toContain('2:59');
  });

  it('zero-pads the seconds', () => {
    render(<PlayerBar isWhite name="A" rating={1500} clockSeconds={65} testId="pb" />);
    expect(screen.getByTestId('pb').textContent).toContain('1:05');
  });

  it('clamps negative clocks to 0:00', () => {
    render(<PlayerBar isWhite name="A" rating={1500} clockSeconds={-3} testId="pb" />);
    expect(screen.getByTestId('pb').textContent).toContain('0:00');
  });

  it('omits the rating when null', () => {
    render(<PlayerBar isWhite name="A" rating={null} clockSeconds={30} testId="pb" />);
    expect(screen.getByTestId('pb').textContent).not.toContain('(');
  });

  it('falls back to ? when the name is null', () => {
    render(<PlayerBar isWhite name={null} rating={1500} clockSeconds={30} testId="pb" />);
    expect(screen.getByTestId('pb').textContent).toContain('?');
  });

  it('hides the clock when clockSeconds is null (no %clk import)', () => {
    render(<PlayerBar isWhite name="A" rating={1500} clockSeconds={null} testId="pb" />);
    // m:ss has a colon; with no clock there should be no time string rendered
    expect(screen.getByTestId('pb').textContent).not.toMatch(/\d:\d\d/);
  });
});
