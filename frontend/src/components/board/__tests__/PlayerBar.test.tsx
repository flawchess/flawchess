// @vitest-environment jsdom
import { describe, it, expect, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import { PlayerBar } from '../PlayerBar';

// Black's queen removed — White up a queen (9 points). Quick 260809-jzz (D-05).
const WHITE_UP_QUEEN_FEN = 'rnb1kbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';

describe('PlayerBar', () => {
  afterEach(() => {
    cleanup();
  });

  it('renders name + ELO in parentheses', () => {
    render(<PlayerBar isWhite name="Magnus" rating={2839} clockSeconds={179.4} testId="pb" />);
    const row = screen.getByTestId('pb');
    expect(row.textContent).toContain('Magnus');
    expect(row.textContent).toContain('(2839)');
  });

  // Phase 223 UAT: the clock badge carries the side identity in its own board
  // colour, so the ■/□ glyph is NOT rendered alongside it — it only appears in
  // the no-clock fallback (see the two glyph-fallback tests below).
  it('omits the side glyph while a clock badge is rendered', () => {
    render(<PlayerBar isWhite name="Magnus" rating={2839} clockSeconds={179.4} testId="pb" />);
    expect(screen.getByTestId('pb').textContent).not.toContain('■');
  });

  it('falls back to the solid glyph for white when there is no clock', () => {
    render(<PlayerBar isWhite name="Magnus" rating={2839} clockSeconds={null} testId="pb" />);
    expect(screen.getByTestId('pb').textContent).toContain('■');
  });

  it('falls back to the hollow glyph for black when there is no clock', () => {
    render(
      <PlayerBar isWhite={false} name="Hikaru" rating={2802} clockSeconds={null} testId="pb" />,
    );
    expect(screen.getByTestId('pb').textContent).toContain('□');
  });

  it('paints the clock badge in each side\'s own board colour', () => {
    const { unmount } = render(
      <PlayerBar isWhite name="A" rating={null} clockSeconds={30} testId="pb" />,
    );
    const white = screen.getByTestId('pb-clock-badge');
    expect(white.getAttribute('style')).toContain('background-color');
    expect(white.getAttribute('class')).toContain('text-black');
    unmount();

    render(<PlayerBar isWhite={false} name="A" rating={null} clockSeconds={30} testId="pb" />);
    const black = screen.getByTestId('pb-clock-badge');
    expect(black.getAttribute('style')).not.toBe(white.getAttribute('style'));
    expect(black.getAttribute('class')).toContain('text-white');
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

  it('shows the material surplus when a fen is provided (Quick 260809-jzz, D-05)', () => {
    render(
      <PlayerBar
        isWhite
        name="A"
        rating={1500}
        clockSeconds={30}
        fen={WHITE_UP_QUEEN_FEN}
        testId="pb"
      />,
    );
    expect(screen.getByTestId('pb').textContent).toContain('+9');
  });

  it('renders no material text when fen is omitted', () => {
    render(<PlayerBar isWhite name="A" rating={1500} clockSeconds={30} testId="pb" />);
    expect(screen.getByTestId('pb').textContent).not.toMatch(/\+\d/);
  });

  // Phase 223 (BOTVOICE-05, D-11): ratingLabel is additive and wins over the
  // numeric rating prop when both are present, so a calibrated estimate is
  // never misrepresented as a parenthesised exact integer.
  it('renders the tilde-prefixed label and NOT the parenthesised number when both are supplied', () => {
    render(
      <PlayerBar isWhite name="Ziggy" rating={800} ratingLabel="~850" clockSeconds={30} testId="pb" />,
    );
    const text = screen.getByTestId('pb').textContent ?? '';
    expect(text).toContain('~850');
    expect(text).not.toContain('(800)');
  });

  it('renders the label alone when only ratingLabel is supplied (no numeric rating)', () => {
    render(<PlayerBar isWhite name="Ziggy" rating={null} ratingLabel="~850" clockSeconds={30} testId="pb" />);
    const text = screen.getByTestId('pb').textContent ?? '';
    expect(text).toContain('~850');
    expect(text).not.toContain('(');
  });

  it('renders neither a label nor a numeric rating when both are absent (no empty parens/stray separator)', () => {
    render(<PlayerBar isWhite name="Ziggy" rating={null} clockSeconds={30} testId="pb" />);
    const text = screen.getByTestId('pb').textContent ?? '';
    expect(text).toContain('Ziggy');
    expect(text).not.toContain('(');
    expect(text).not.toContain(')');
  });

  // Phase 223 UAT: the clock icon marks the side to move; the slot stays
  // laid out (invisible, not unmounted) so the digits never shift.
  it('keeps the clock icon visible when clockActive is omitted (analysis rendering unchanged)', () => {
    render(<PlayerBar isWhite name="A" rating={1500} clockSeconds={30} testId="pb" />);
    expect(screen.getByTestId('pb-clock-icon').getAttribute('class')).not.toContain('invisible');
  });

  it('hides the clock icon (but keeps the digits) when clockActive is false', () => {
    render(<PlayerBar isWhite name="A" rating={1500} clockSeconds={30} clockActive={false} testId="pb" />);
    expect(screen.getByTestId('pb-clock-icon').getAttribute('class')).toContain('invisible');
    expect(screen.getByTestId('pb').textContent).toContain('0:30');
  });

  // Phase 223 UAT: low time repaints the whole badge (background + text),
  // outranking the side-identity colour it normally carries.
  it('repaints the clock badge in the low-time color only when clockUrgent is set', () => {
    const { unmount } = render(
      <PlayerBar isWhite name="A" rating={1500} clockSeconds={5} clockUrgent testId="pb" />,
    );
    const urgent = screen.getByTestId('pb-clock-badge');
    const urgentStyle = urgent.getAttribute('style');
    expect(urgent.getAttribute('class')).toContain('text-white');
    unmount();

    render(<PlayerBar isWhite name="A" rating={1500} clockSeconds={5} testId="pb" />);
    const calm = screen.getByTestId('pb-clock-badge');
    expect(calm.getAttribute('style')).not.toBe(urgentStyle);
    expect(calm.getAttribute('class')).toContain('text-black');
  });
});
