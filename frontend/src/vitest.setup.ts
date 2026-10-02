/**
 * Project-wide Vitest setup (registered via `test.setupFiles` in vite.config.ts).
 *
 * testing-library's async utilities (`waitFor`, `findBy*`) carry their own
 * ceiling, independent of Vitest's `testTimeout`: `asyncUtilTimeout` defaults
 * to 1000ms. Under the full parallel `vitest run` on a loaded machine a single
 * `waitFor` around a whole-page mount can blow that while the test still has
 * seconds of Vitest headroom, surfacing as a bare `waitFor` stack with no
 * assertion message. Like `testTimeout`, this is a ceiling, not a budget: a
 * `waitFor` resolves the moment its callback stops throwing, so a passing test
 * never waits for it. Files with heavier mounts may still raise it further
 * with their own `configure()` call.
 */
import { configure } from '@testing-library/react';

const ASYNC_UTIL_TIMEOUT_MS = 5000;

configure({ asyncUtilTimeout: ASYNC_UTIL_TIMEOUT_MS });

// jsdom has no ResizeObserver, and the Radix Slider measures its thumb with one
// on mount. Quick 261002-8xb put a Slider on the Train schedule card, which
// broke every test that mounts that card (TrainStartScreen, Train page) with
// "ResizeObserver is not defined". A guarded no-op stub here covers them all;
// files that install their own stub still win, since they assign afterwards.
if (typeof globalThis.ResizeObserver !== 'function') {
  globalThis.ResizeObserver = class {
    observe(): void {}
    unobserve(): void {}
    disconnect(): void {}
  };
}
