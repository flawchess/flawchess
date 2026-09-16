/**
 * botGameCopy.test.ts — Phase 223 Plan 02 Task 2 (BOTVOICE-01/06).
 *
 * Pure-module invariant test mirroring `trainBotCopy.test.ts`'s
 * exhaustiveness + regex-over-every-entry loop template (see that file's
 * `describe('LANDING_GREETINGS / landingHost', ...)` block). Iterates
 * `Object.keys(BOT_LINE_TABLES)` rather than a hand-written key list, so a
 * table added by a later plan is covered automatically, and every per-entry
 * assertion passes the persona id AND the trigger key as the assertion's
 * message argument, so a failure names the exact line.
 */
import { describe, expect, it } from 'vitest';
import {
  BOT_LINE_TABLES,
  BOT_LINE_MAX_CHARS,
  ROSTER_GREETINGS,
  botLineCopy,
  rosterHost,
} from '@/lib/botGameCopy';
import type { BotLineKey } from '@/lib/botGameCopy';
import { PERSONA_REGISTRY } from '@/lib/personas/personaRegistry';
import type { PersonaId } from '@/lib/personas/personaRegistry';
import { LANDING_GREETINGS, landingHost } from '@/lib/trainBotCopy';

const ALL_IDS = Object.keys(PERSONA_REGISTRY) as PersonaId[];
const ALL_KEYS = Object.keys(BOT_LINE_TABLES) as BotLineKey[];

/**
 * The full set of per-persona surfaces the shared invariant loops below
 * check — every `BOT_LINE_TABLES` key PLUS `ROSTER_GREETINGS`, which is a
 * deliberately separate table (a roster greeting welcomes the visitor; an
 * in-game hello opens a game already in progress) but is bound by the same
 * budget/em-dash/forbidden-claim/insult/numeric-disclosure rules. Keying by
 * `string` (not `BotLineKey`) here is intentional: `'roster-greetings'` is
 * not an in-game trigger, so it never belongs in `BotLineKey` itself.
 */
const ALL_SURFACES: Record<string, Record<PersonaId, string>> = {
  ...BOT_LINE_TABLES,
  'roster-greetings': ROSTER_GREETINGS,
};
const ALL_SURFACE_KEYS = Object.keys(ALL_SURFACES);

/**
 * Forbidden-claim rule (223-02-PLAN.md task action for `'earned-tease'`,
 * carried into every table by this module's own header): no line may claim
 * the bot calculated, thought ahead, foresaw, predicted or knew what was
 * coming — 16 of the 24 personas make exactly one Maia policy call and
 * never search (`PersonaGrid.tsx`'s `BotWelcomeCard` doc comment).
 */
const FORBIDDEN_CLAIM_PATTERN =
  /calculat\w*|foresaw|foresee\w*|foresight|predict\w*|planned|thought ahead|knew (it|that|this|what|you'?d)|saw (it|that|this) coming/i;

/**
 * Insult rule (223-CONTEXT.md prohibition: "the tease must never read as
 * mean; a line describes the board, never the player"). A short deny-list
 * of words that would make a line read as an attack on the player rather
 * than a remark about the board.
 */
const INSULT_PATTERN =
  /\b(stupid|idiot(?:ic)?|dumb|moron(?:ic)?|pathetic|loser|trash|garbage|foolish|fool|clueless|lame)\b/i;

/**
 * Numeric-disclosure rule (223-02-PLAN.md T-223-02-02 behavior): a line
 * never reports a number, unit or engine term the board does not show —
 * this is the copy-level control the STRIDE threat register (T-223-02-02)
 * names as the mitigation for the in-game line tables' Information
 * Disclosure risk.
 */
const NUMERIC_DISCLOSURE_PATTERN = /\d+\s*(cp|centipawns?|pawns?)\b|\d+\s*%|\bengine\b|\bevaluation\b/i;

/** No em-dash anywhere in an authored bot line (223-CONTEXT D-08). */
const EM_DASH_PATTERN = /—/;

describe('BOT_LINE_TABLES — exhaustiveness', () => {
  it('has an entry for every registry persona in every table, non-empty after trimming', () => {
    for (const key of ALL_KEYS) {
      for (const id of ALL_IDS) {
        const line = BOT_LINE_TABLES[key][id];
        expect(line, `${key}/${id}`).toBeDefined();
        expect(line.trim().length, `${key}/${id}`).toBeGreaterThan(0);
      }
    }
  });

  it('no entry in any table is byte-identical to that same persona\'s entry in a different table', () => {
    for (const id of ALL_IDS) {
      const seen = new Map<string, BotLineKey>();
      for (const key of ALL_KEYS) {
        const line = BOT_LINE_TABLES[key][id];
        const priorKey = seen.get(line);
        expect(priorKey, `${id}: "${line}" duplicated between ${String(priorKey)} and ${key}`).toBeUndefined();
        seen.set(line, key);
      }
    }
  });

  it('botLineCopy returns the exact table entry for every key/persona pair', () => {
    for (const key of ALL_KEYS) {
      for (const id of ALL_IDS) {
        expect(botLineCopy(key, id), `${key}/${id}`).toBe(BOT_LINE_TABLES[key][id]);
      }
    }
  });
});

describe('ALL_SURFACES (BOT_LINE_TABLES + ROSTER_GREETINGS) — shared invariants', () => {
  it('has an entry for every registry persona on every surface, non-empty after trimming', () => {
    for (const key of ALL_SURFACE_KEYS) {
      for (const id of ALL_IDS) {
        const line = ALL_SURFACES[key][id];
        expect(line, `${key}/${id}`).toBeDefined();
        expect(line.trim().length, `${key}/${id}`).toBeGreaterThan(0);
      }
    }
  });

  it('never exceeds BOT_LINE_MAX_CHARS on any surface/persona pair', () => {
    for (const key of ALL_SURFACE_KEYS) {
      for (const id of ALL_IDS) {
        const line = ALL_SURFACES[key][id];
        expect(line.length, `${key}/${id}`).toBeLessThanOrEqual(BOT_LINE_MAX_CHARS);
      }
    }
  });

  it('never contains an em-dash on any surface/persona pair', () => {
    for (const key of ALL_SURFACE_KEYS) {
      for (const id of ALL_IDS) {
        const line = ALL_SURFACES[key][id];
        expect(line, `${key}/${id}`).not.toMatch(EM_DASH_PATTERN);
      }
    }
  });

  it('never claims the bot calculated, thought ahead, foresaw or predicted anything', () => {
    for (const key of ALL_SURFACE_KEYS) {
      for (const id of ALL_IDS) {
        const line = ALL_SURFACES[key][id];
        expect(line, `${key}/${id}`).not.toMatch(FORBIDDEN_CLAIM_PATTERN);
      }
    }
  });

  it('never insults the player', () => {
    for (const key of ALL_SURFACE_KEYS) {
      for (const id of ALL_IDS) {
        const line = ALL_SURFACES[key][id];
        expect(line, `${key}/${id}`).not.toMatch(INSULT_PATTERN);
      }
    }
  });

  it('never discloses a number, unit or engine term the board does not show', () => {
    for (const key of ALL_SURFACE_KEYS) {
      for (const id of ALL_IDS) {
        const line = ALL_SURFACES[key][id];
        expect(line, `${key}/${id}`).not.toMatch(NUMERIC_DISCLOSURE_PATTERN);
      }
    }
  });

  it('no entry on any surface is byte-identical to that same persona\'s LANDING_GREETINGS entry', () => {
    for (const key of ALL_SURFACE_KEYS) {
      for (const id of ALL_IDS) {
        const line = ALL_SURFACES[key][id];
        expect(line, `${key}/${id}`).not.toBe(LANDING_GREETINGS[id]);
      }
    }
  });

  it('no entry on any surface is byte-identical to that same persona\'s entry on a different surface', () => {
    for (const id of ALL_IDS) {
      const seen = new Map<string, string>();
      for (const key of ALL_SURFACE_KEYS) {
        const line = ALL_SURFACES[key][id];
        const priorKey = seen.get(line);
        expect(priorKey, `${id}: "${line}" duplicated between ${String(priorKey)} and ${key}`).toBeUndefined();
        seen.set(line, key);
      }
    }
  });
});

describe('rosterHost / landingHost — shared daily rotation (223-02)', () => {
  // 24 consecutive days is a full cycle over all 24 personas — enough to
  // prove the two rotations agree on every offset, not just one lucky date.
  const DAYS_IN_CYCLE = ALL_IDS.length;

  it('rosterHost and landingHost resolve to the SAME persona for the same date, for a full rotation cycle', () => {
    for (let offset = 0; offset < DAYS_IN_CYCLE; offset += 1) {
      const date = new Date(Date.UTC(2026, 6, 1 + offset)).toISOString().slice(0, 10);
      const roster = rosterHost({ today: date });
      const landing = landingHost({ sessionDate: date, introSeenAt: '2026-07-01T00:00:00Z' });
      expect(roster.persona.id, date).toBe(landing.persona.id);
    }
  });

  it('rosterHost always pairs a persona with that persona\'s own ROSTER_GREETINGS entry', () => {
    for (let offset = 0; offset < DAYS_IN_CYCLE; offset += 1) {
      const date = new Date(Date.UTC(2026, 6, 1 + offset)).toISOString().slice(0, 10);
      const host = rosterHost({ today: date });
      expect(host.copy, date).toBe(ROSTER_GREETINGS[host.persona.id]);
    }
  });

  it('falls back to Tank on a null date or an unparseable one, with no intro gate involved', () => {
    expect(rosterHost({ today: null }).persona.id).toBe('grinder-1600');
    expect(rosterHost({ today: 'not-a-date' }).persona.id).toBe('grinder-1600');
  });
});

describe("'draw-offer' reads as an offer, not an announcement of a result", () => {
  const OFFER_PATTERN = /draw|truce/i;
  const RESULT_ANNOUNCEMENT_PATTERN = /\b(you won|you lost|game over|i won|i lost)\b/i;

  it('every persona\'s draw-offer line mentions the offer and never announces a result', () => {
    for (const id of ALL_IDS) {
      const line = BOT_LINE_TABLES['draw-offer'][id];
      expect(line, id).toMatch(OFFER_PATTERN);
      expect(line, id).not.toMatch(RESULT_ANNOUNCEMENT_PATTERN);
    }
  });
});

describe('the three terminal tables are distinct per outcome and tonally consistent', () => {
  // A bot-won line must not congratulate the PLAYER on winning (the bot won,
  // not the player) and must not commiserate as if the bot's own win were a
  // sad event.
  const WRONG_TONE_FOR_BOT_WON = /\bcongrat|you won|nice win|great win|sorry|unlucky|hard luck|shame on\b/i;
  // A bot-lost line must not gloat over the player, since the player won.
  const WRONG_TONE_FOR_BOT_LOST = /gloat|too easy|no contest/i;

  it("'bot-won' never congratulates the player on winning and never commiserates", () => {
    for (const id of ALL_IDS) {
      expect(BOT_LINE_TABLES['bot-won'][id], id).not.toMatch(WRONG_TONE_FOR_BOT_WON);
    }
  });

  it("'bot-lost' never gloats over the player", () => {
    for (const id of ALL_IDS) {
      expect(BOT_LINE_TABLES['bot-lost'][id], id).not.toMatch(WRONG_TONE_FOR_BOT_LOST);
    }
  });

  it('bot-won, bot-lost and game-drawn are pairwise distinct for every persona', () => {
    for (const id of ALL_IDS) {
      const won = BOT_LINE_TABLES['bot-won'][id];
      const lost = BOT_LINE_TABLES['bot-lost'][id];
      const drawn = BOT_LINE_TABLES['game-drawn'][id];
      expect(won, id).not.toBe(lost);
      expect(won, id).not.toBe(drawn);
      expect(lost, id).not.toBe(drawn);
    }
  });
});
