// @vitest-environment jsdom
import { describe, expect, it } from 'vitest';

import { workerErrorContext } from '@/lib/engine/workerErrorContext';

describe('workerErrorContext', () => {
  it('captures message, location and error name from an uncaught in-worker error', () => {
    const event = new ErrorEvent('error', {
      message: 'RangeError: Out of memory',
      filename: 'https://flawchess.com/engine/stockfish.js',
      lineno: 12,
      colno: 34,
      error: new RangeError('Out of memory'),
    });

    expect(workerErrorContext(event)).toEqual(
      expect.objectContaining({
        eventType: 'error',
        isErrorEvent: true,
        message: 'RangeError: Out of memory',
        filename: 'https://flawchess.com/engine/stockfish.js',
        lineno: 12,
        colno: 34,
        errorName: 'RangeError',
      }),
    );
  });

  it('omits empty fields for a bare load-failure event', () => {
    const context = workerErrorContext(new Event('error'));

    expect(context.isErrorEvent).toBe(false);
    expect(context).not.toHaveProperty('message');
    expect(context).not.toHaveProperty('filename');
    expect(context).toHaveProperty('visibilityState');
    expect(context).toHaveProperty('online');
  });
});
