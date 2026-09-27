// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest';
import { identifyAccountType, installUmamiBeforeSend, scrubUmamiPayload } from '@/lib/analytics';

const ORIGIN = window.location.origin;

describe('scrubUmamiPayload', () => {
  it('strips the password-reset token from the url and keeps other params', () => {
    const out = scrubUmamiPayload('event', {
      url: `${ORIGIN}/auth/reset-password?token=abc.def.ghi&utm_source=mail`,
    });
    expect(out.url).toBe(`${ORIGIN}/auth/reset-password?utm_source=mail`);
  });

  it('strips the token from an origin-relative internal referrer and keeps it relative', () => {
    const out = scrubUmamiPayload('event', { referrer: '/auth/reset-password?token=abc' });
    expect(out.referrer).toBe('/auth/reset-password');
  });

  it.each(['https://accounts.google.com/', 'https://accounts.google.fr/', 'https://accounts.google.co.uk/'])(
    'blanks the Google OAuth referrer %s',
    (referrer) => {
      expect(scrubUmamiPayload('event', { referrer }).referrer).toBe('');
    },
  );

  it('keeps real search and external referrers untouched', () => {
    expect(scrubUmamiPayload('event', { referrer: 'https://www.google.com/' }).referrer).toBe(
      'https://www.google.com/',
    );
    expect(scrubUmamiPayload('event', { referrer: 'https://lichess.org/@/someone' }).referrer).toBe(
      'https://lichess.org/@/someone',
    );
  });

  it('leaves tokenless urls byte-identical and passes other fields through', () => {
    const payload = { url: `${ORIGIN}/analysis?game_id=5&ply=12`, name: 'guest-start', website: 'w' };
    expect(scrubUmamiPayload('event', payload)).toEqual(payload);
  });
});

describe('Umami globals', () => {
  afterEach(() => {
    delete window.umami;
    delete window.umamiBeforeSend;
  });

  it('installs the scrubber under the name index.html references', () => {
    installUmamiBeforeSend();
    expect(window.umamiBeforeSend).toBe(scrubUmamiPayload);
  });

  it('identifies only the coarse account type', () => {
    const identify = vi.fn();
    window.umami = { track: vi.fn(), identify };
    identifyAccountType('guest');
    expect(identify).toHaveBeenCalledWith({ account: 'guest' });
  });

  it('is a no-op when the tracker is absent', () => {
    expect(() => identifyAccountType('registered')).not.toThrow();
  });
});
