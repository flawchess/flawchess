// @vitest-environment jsdom
/**
 * Privacy.test.tsx — the Privacy page must disclose the Train
 * per-puzzle telemetry (timing, solution engagement, device class).
 */
import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';

import { PrivacyPage } from '@/pages/Privacy';

afterEach(cleanup);

describe('PrivacyPage Train telemetry disclosure', () => {
  it('names the device class and that hidden time is not counted', () => {
    render(
      <MemoryRouter>
        <PrivacyPage />
      </MemoryRouter>,
    );
    const text = screen.getByTestId('privacy-page').textContent ?? '';
    expect(text).toContain('whether you trained on a phone or a computer');
    expect(text).toContain('only while the page is visible');
  });
});
