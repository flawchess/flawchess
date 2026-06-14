const WELCOME_DISMISSED_KEY = 'welcome_dismissed';

/**
 * Returns true if the current guest has previously dismissed the Welcome page.
 * Guards against SSR/prerender environments where localStorage is unavailable.
 */
export function isWelcomeDismissed(): boolean {
  if (typeof localStorage === 'undefined') return false;
  return localStorage.getItem(WELCOME_DISMISSED_KEY) === '1';
}

/**
 * Sets or clears the welcome-dismissed flag in localStorage.
 * Passing true persists the flag; false removes it.
 */
export function setWelcomeDismissed(dismissed: boolean): void {
  if (dismissed) {
    localStorage.setItem(WELCOME_DISMISSED_KEY, '1');
  } else {
    localStorage.removeItem(WELCOME_DISMISSED_KEY);
  }
}
