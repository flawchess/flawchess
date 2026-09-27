// @vitest-environment jsdom
import { afterEach, describe, expect, it } from 'vitest';
import {
  FIRST_TOUCH_STORAGE_KEY,
  buildFirstTouch,
  captureFirstTouch,
  markFirstTouchSent,
  readUnsentFirstTouch,
} from '@/lib/firstTouch';

const APP = 'https://flawchess.com';

describe('buildFirstTouch', () => {
  it('keeps only the external referrer host, utm tags and the landing pathname', () => {
    expect(
      buildFirstTouch(
        `${APP}/bots?utm_source=reddit&utm_medium=social&utm_campaign=engine-post&x=1#frag`,
        'https://www.Reddit.com/r/chess/comments/abc?share=1',
      ),
    ).toEqual({
      referrer_host: 'www.reddit.com',
      utm_source: 'reddit',
      utm_medium: 'social',
      utm_campaign: 'engine-post',
      landing_path: '/bots',
    });
  });

  it('treats an empty or same-site referrer as direct', () => {
    expect(buildFirstTouch(`${APP}/`, '')?.referrer_host).toBeNull();
    expect(buildFirstTouch(`${APP}/`, `${APP}/privacy`)?.referrer_host).toBeNull();
    expect(buildFirstTouch(`${APP}/`, 'not a url')?.referrer_host).toBeNull();
  });

  it('skips auth hops such as the OAuth callback', () => {
    expect(buildFirstTouch(`${APP}/auth/callback#token=secret`, 'https://accounts.google.com/')).toBeNull();
  });

  it('blanks empty utm values', () => {
    expect(buildFirstTouch(`${APP}/?utm_source=%20`, '')?.utm_source).toBeNull();
  });
});

describe('first-touch storage', () => {
  afterEach(() => localStorage.clear());

  it('captures once, never overwrites, and stops returning after it is sent', () => {
    captureFirstTouch(`${APP}/?utm_source=youtube`, '');
    captureFirstTouch(`${APP}/?utm_source=reddit`, '');
    expect(readUnsentFirstTouch()?.utm_source).toBe('youtube');

    markFirstTouchSent();
    expect(readUnsentFirstTouch()).toBeNull();
    expect(localStorage.getItem(FIRST_TOUCH_STORAGE_KEY)).not.toBeNull();
  });

  it('stores nothing for an auth hop, so the next real page load counts', () => {
    captureFirstTouch(`${APP}/auth/callback`, '');
    expect(readUnsentFirstTouch()).toBeNull();
    captureFirstTouch(`${APP}/`, 'https://chatgpt.com/');
    expect(readUnsentFirstTouch()?.referrer_host).toBe('chatgpt.com');
  });
});
