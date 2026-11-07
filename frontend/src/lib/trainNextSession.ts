/**
 * trainNextSession — how the score screen names the next Train session. Pure,
 * so the date line and the bot bubble can never disagree about the day.
 */
import { differenceInCalendarDays, format, parseISO } from 'date-fns';
import { readDevClockOffsetMinutes } from '@/lib/devClock';

const MS_PER_MINUTE = 60_000;

/** Farthest day still named by its weekday. At 7 days "Tuesday" could mean
 * today's own weekday, and "next Tuesday" is off the table as a sign-off
 * ("see you next Tuesday" is a rude English joke), so a week out uses the date. */
const MAX_DAYS_NAMED_BY_WEEKDAY = 6;

export interface NextSessionWhen {
  /** Follows "Next session: ". */
  line: string;
  /** Follows "See you ". */
  seeYou: string;
}

/**
 * Today as YYYY-MM-DD in the user's Train timezone, which is the calendar
 * `expires_on` is computed in. The dev clock offset keeps time travel honest.
 * Falls back to the browser's timezone when the setting is absent or invalid.
 */
export function localTodayIso(timeZone: string | undefined, nowMs?: number): string {
  const now = new Date(nowMs ?? Date.now() + readDevClockOffsetMinutes() * MS_PER_MINUTE);
  // en-CA formats as YYYY-MM-DD.
  try {
    return now.toLocaleDateString('en-CA', { timeZone });
  } catch {
    // RangeError: unknown timezone name.
    return now.toLocaleDateString('en-CA');
  }
}

/**
 * Names the next session relative to today: "tomorrow", then the weekday, then
 * the date. A date in the past or today (a browser clock or timezone that
 * disagrees with the server) also uses the date, never a wrong relative word.
 */
export function nextSessionWhen(nextSessionDate: string, todayIso: string): NextSessionWhen {
  const next = parseISO(nextSessionDate);
  const days = differenceInCalendarDays(next, parseISO(todayIso));
  if (days === 1) return { line: 'tomorrow', seeYou: 'tomorrow' };
  if (days > 1 && days <= MAX_DAYS_NAMED_BY_WEEKDAY) {
    const weekday = format(next, 'EEEE');
    return { line: weekday, seeYou: weekday };
  }
  const date = format(next, 'MMM d');
  return { line: date, seeYou: `on ${date}` };
}
