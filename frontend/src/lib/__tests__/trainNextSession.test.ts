import { describe, expect, it } from 'vitest';
import { localTodayIso, nextSessionWhen } from '@/lib/trainNextSession';

// 2026-11-07 is a Saturday.
const TODAY = '2026-11-07';

describe('nextSessionWhen', () => {
  it('says tomorrow for the next calendar day', () => {
    expect(nextSessionWhen('2026-11-08', TODAY)).toEqual({ line: 'tomorrow', seeYou: 'tomorrow' });
  });

  it('names the weekday from 2 to 6 days out', () => {
    expect(nextSessionWhen('2026-11-09', TODAY)).toEqual({ line: 'Monday', seeYou: 'Monday' });
    expect(nextSessionWhen('2026-11-13', TODAY)).toEqual({ line: 'Friday', seeYou: 'Friday' });
  });

  it('uses the date a week out, never "next <weekday>"', () => {
    expect(nextSessionWhen('2026-11-14', TODAY)).toEqual({ line: 'Nov 14', seeYou: 'on Nov 14' });
  });

  it('uses the date when the clocks disagree, never a wrong relative word', () => {
    expect(nextSessionWhen('2026-11-07', TODAY)).toEqual({ line: 'Nov 7', seeYou: 'on Nov 7' });
    expect(nextSessionWhen('2026-11-01', TODAY)).toEqual({ line: 'Nov 1', seeYou: 'on Nov 1' });
  });

  it('counts calendar days across a DST change', () => {
    // Europe and the US leave DST around these dates; it must still be one day.
    expect(nextSessionWhen('2026-10-26', '2026-10-25').line).toBe('tomorrow');
    expect(nextSessionWhen('2026-11-02', '2026-11-01').line).toBe('tomorrow');
  });
});

describe('localTodayIso', () => {
  const LATE_UTC = Date.UTC(2026, 10, 7, 23, 30);

  it('uses the given timezone, not the browser calendar', () => {
    expect(localTodayIso('Asia/Tokyo', LATE_UTC)).toBe('2026-11-08');
    expect(localTodayIso('America/New_York', LATE_UTC)).toBe('2026-11-07');
  });

  it('falls back to the browser timezone for an unknown name', () => {
    expect(localTodayIso('Not/AZone', LATE_UTC)).toBe(localTodayIso(undefined, LATE_UTC));
  });
});
