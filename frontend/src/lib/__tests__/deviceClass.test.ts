// @vitest-environment jsdom
import { afterEach, describe, expect, it } from 'vitest';
import { isMobileUserAgent, telemetryClient } from '@/lib/deviceClass';

const ORIGINAL_UA = navigator.userAgent;
const ORIGINAL_TOUCH_POINTS = navigator.maxTouchPoints;

function stubUserAgent(userAgent: string): void {
  Object.defineProperty(navigator, 'userAgent', { value: userAgent, configurable: true });
}

function stubTouchPoints(points: number): void {
  Object.defineProperty(navigator, 'maxTouchPoints', { value: points, configurable: true });
}

const MAC_SAFARI_UA =
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15';
const IPAD_TOUCH_POINTS = 5;

const MOBILE_UAS: Record<string, string> = {
  iPhone: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 Safari/604.1',
  iPad: 'Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 Safari/604.1',
  Android: 'Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 Chrome/120.0 Mobile Safari/537.36',
  iPod: 'Mozilla/5.0 (iPod touch; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148',
};

const DESKTOP_CHROME_UA =
  'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36';

describe('deviceClass', () => {
  afterEach(() => {
    stubUserAgent(ORIGINAL_UA);
    stubTouchPoints(ORIGINAL_TOUCH_POINTS);
  });

  it.each(Object.entries(MOBILE_UAS))('classifies %s as mobile', (_name, ua) => {
    stubUserAgent(ua);
    expect(isMobileUserAgent()).toBe(true);
    expect(telemetryClient()).toBe('mobile');
  });

  it('classifies a desktop Chrome UA as desktop', () => {
    stubUserAgent(DESKTOP_CHROME_UA);
    expect(isMobileUserAgent()).toBe(false);
    expect(telemetryClient()).toBe('desktop');
  });

  it('classifies an iPadOS desktop-class UA (Macintosh + touch) as mobile for telemetry only', () => {
    stubUserAgent(MAC_SAFARI_UA);
    stubTouchPoints(IPAD_TOUCH_POINTS);
    expect(telemetryClient()).toBe('mobile');
    // The install-prompt gate is unchanged (D-06).
    expect(isMobileUserAgent()).toBe(false);
  });

  it('classifies a Mac without touch as desktop', () => {
    stubUserAgent(MAC_SAFARI_UA);
    stubTouchPoints(0);
    expect(telemetryClient()).toBe('desktop');
  });

  it("classifies jsdom's default UA as desktop", () => {
    expect(telemetryClient()).toBe('desktop');
  });
});
