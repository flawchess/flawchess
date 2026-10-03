// @vitest-environment jsdom
/**
 * SettingsDialogButton.test.tsx: the desktop settings modal opens the full panel,
 * closes on Escape, and hands keyboard focus back to the cogwheel (228 code review
 * WR-01, second pass: a plain onClick button left focus on <body>).
 */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';

import { SettingsDialogButton } from '@/components/settings/SettingsDialogButton';

afterEach(() => {
  cleanup();
  localStorage.clear();
});

describe('SettingsDialogButton', () => {
  it('opens the full panel in a modal dialog', async () => {
    render(<SettingsDialogButton testId="btn-test-settings" />);
    fireEvent.click(screen.getByTestId('btn-test-settings'));

    const dialog = await screen.findByTestId('settings-dialog');
    expect(dialog.getAttribute('aria-modal')).toBe('true');
    expect(dialog.querySelector('[data-testid="settings-panel"]')).not.toBeNull();
  });

  it('closes on Escape and returns keyboard focus to the cogwheel', async () => {
    render(<SettingsDialogButton testId="btn-test-settings" />);
    const trigger = screen.getByTestId('btn-test-settings');
    trigger.focus();
    fireEvent.click(trigger);
    const dialog = await screen.findByTestId('settings-dialog');

    fireEvent.keyDown(dialog, { key: 'Escape' });
    await waitFor(() => expect(screen.queryByTestId('settings-dialog')).toBeNull());
    expect(document.activeElement).toBe(trigger);
  });
});
