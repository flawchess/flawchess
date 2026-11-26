// @vitest-environment jsdom
import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { InfoPopover } from '@/components/ui/info-popover';

describe('InfoPopover close on scroll', () => {
  afterEach(cleanup);

  function renderInScroller(closeOnScroll = true): HTMLElement {
    render(
      <div data-testid="scroller" style={{ overflowY: 'auto' }}>
        <InfoPopover ariaLabel="Info" testId="scroll-popover" closeOnScroll={closeOnScroll}>
          <div data-testid="popover-body" style={{ overflowY: 'auto' }}>
            body
          </div>
        </InfoPopover>
      </div>,
    );
    fireEvent.click(screen.getByTestId('scroll-popover'));
    expect(screen.getByTestId('popover-body')).toBeTruthy();
    return screen.getByTestId('scroller');
  }

  it('closes when a container holding the trigger scrolls (mobile move list drag)', () => {
    const scroller = renderInScroller();
    fireEvent.scroll(scroller);
    expect(screen.queryByTestId('popover-body')).toBeNull();
  });

  it('closes when the page scrolls', () => {
    renderInScroller();
    fireEvent.scroll(document);
    expect(screen.queryByTestId('popover-body')).toBeNull();
  });

  it('stays open on page scroll by default, so long text can be scrolled into view', () => {
    renderInScroller(false);
    fireEvent.scroll(document);
    fireEvent.scroll(screen.getByTestId('scroller'));
    expect(screen.getByTestId('popover-body')).toBeTruthy();
  });

  it('stays open when the popover content itself scrolls', () => {
    renderInScroller();
    fireEvent.scroll(screen.getByTestId('popover-body'));
    expect(screen.getByTestId('popover-body')).toBeTruthy();
  });
});
