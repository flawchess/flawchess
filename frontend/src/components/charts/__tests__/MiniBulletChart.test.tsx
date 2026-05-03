// @vitest-environment jsdom
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { MiniBulletChart } from '../MiniBulletChart';

describe('MiniBulletChart — backward compatibility', () => {
  it('renders unchanged when ciLow and ciHigh are omitted', () => {
    render(<MiniBulletChart value={0.5} domain={1.0} />);
    expect(screen.queryByTestId('mini-bullet-whisker')).toBeNull();
  });
});

describe('MiniBulletChart — CI whisker', () => {
  it('renders whisker line when both ciLow and ciHigh provided', () => {
    render(<MiniBulletChart value={0.3} ciLow={0.1} ciHigh={0.5} domain={1.0} />);
    expect(screen.queryByTestId('mini-bullet-whisker')).not.toBeNull();
  });

  it('whisker has both end caps when CI fits within domain', () => {
    render(<MiniBulletChart value={0} ciLow={-0.2} ciHigh={0.2} domain={1.0} />);
    expect(screen.queryByTestId('mini-bullet-whisker-cap-low')).not.toBeNull();
    expect(screen.queryByTestId('mini-bullet-whisker-cap-high')).not.toBeNull();
  });

  it('left cap suppressed when ciLow < -domain', () => {
    render(<MiniBulletChart value={0} ciLow={-1.5} ciHigh={0.2} domain={1.0} />);
    expect(screen.queryByTestId('mini-bullet-whisker-cap-low')).toBeNull();
    expect(screen.queryByTestId('mini-bullet-whisker-cap-high')).not.toBeNull();
  });

  it('right cap suppressed when ciHigh > +domain', () => {
    render(<MiniBulletChart value={0} ciLow={-0.2} ciHigh={1.5} domain={1.0} />);
    expect(screen.queryByTestId('mini-bullet-whisker-cap-high')).toBeNull();
    expect(screen.queryByTestId('mini-bullet-whisker-cap-low')).not.toBeNull();
  });

  it('whisker positions clamp to domain edges when CI exceeds domain', () => {
    const { getByTestId } = render(
      <MiniBulletChart value={0} ciLow={-2.0} ciHigh={2.0} domain={1.0} />,
    );
    const whisker = getByTestId('mini-bullet-whisker');
    // toPct(-domain) = ((-1 + 1) / 2) = 0%, toPct(+domain) = 100%
    // width = 100 - 0 = 100%
    expect(whisker.style.left).toBe('0%');
    expect(whisker.style.width).toBe('100%');
  });

  it('whisker only renders if BOTH props provided — only ciLow', () => {
    // @ts-expect-error — intentional partial prop test
    render(<MiniBulletChart value={0} ciLow={0.1} domain={1.0} />);
    expect(screen.queryByTestId('mini-bullet-whisker')).toBeNull();
  });

  it('whisker only renders if BOTH props provided — only ciHigh', () => {
    // @ts-expect-error — intentional partial prop test
    render(<MiniBulletChart value={0} ciHigh={0.1} domain={1.0} />);
    expect(screen.queryByTestId('mini-bullet-whisker')).toBeNull();
  });

  it('does not affect existing aria-label or value bar', () => {
    render(
      <MiniBulletChart
        value={0.3}
        ciLow={0.1}
        ciHigh={0.5}
        domain={1.0}
        ariaLabel="Test label"
      />,
    );
    // aria-label must survive the whisker addition
    expect(screen.queryByRole('img', { name: 'Test label' })).not.toBeNull();
    // value bar (the chart container) still present
    expect(screen.queryByTestId('mini-bullet-chart')).not.toBeNull();
  });
});
