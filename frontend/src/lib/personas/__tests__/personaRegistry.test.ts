/**
 * personaRegistry.ts unit tests (Phase 183, PERS-03, AVAT-01/02).
 *
 * Structural + identity invariants over the 24-slot persona registry —
 * mirrors `botStyleBundles.test.ts`'s cross-entry data-shape assertion
 * style. Also encodes the assumption_delta_decision invariant test from
 * 183-01-PLAN.md: every persona slot is a total function to a playable
 * opponent (botElo in ladder, blend in {HUMAN,LIGHT,DEEP}, style === a
 * BOT_STYLE_BUNDLES singleton by reference).
 */

import { describe, it, expect } from 'vitest';
import {
  PERSONA_REGISTRY,
  RUNG_BLEND,
  STYLE_SECTION_ORDER,
  personasForSection,
  personaForId,
  type Persona,
  type PersonaId,
  type Rung,
} from '../personaRegistry';
import { BOT_STYLE_BUNDLES, ATTACKER_STYLE, TRICKSTER_STYLE, GRINDER_STYLE, WALL_STYLE } from '@/lib/engine/botStyleBundles';
import type { Style } from '@/lib/engine/styleOpeningLines';
import { HUMAN_BLEND, LIGHT_BLEND, DEEP_BLEND } from '@/lib/playStyle';
import { MAIA_ELO_LADDER } from '@/lib/maiaEncoding';

const ALL_STYLES: Style[] = ['Attacker', 'Trickster', 'Grinder', 'Wall'];
const ALL_RUNGS: Rung[] = [800, 1000, 1200, 1400, 1600, 1800];
const STYLE_SINGLETONS: Record<Style, unknown> = {
  Attacker: ATTACKER_STYLE,
  Trickster: TRICKSTER_STYLE,
  Grinder: GRINDER_STYLE,
  Wall: WALL_STYLE,
};

describe('PERSONA_REGISTRY', () => {
  it('has exactly 24 keys', () => {
    expect(Object.keys(PERSONA_REGISTRY)).toHaveLength(24);
  });

  it('grouping by style yields exactly 6 personas per style for all 4 styles', () => {
    for (const style of ALL_STYLES) {
      const forStyle = Object.values(PERSONA_REGISTRY).filter((p) => p.style === style);
      expect(forStyle, style).toHaveLength(6);
    }
  });

  it('every PersonaId key matches its persona\'s derived id, and all 24 ids are distinct', () => {
    const ids = new Set<string>();
    for (const [key, persona] of Object.entries(PERSONA_REGISTRY)) {
      expect(persona.id).toBe(key);
      expect(persona.id).toBe(`${persona.style.toLowerCase()}-${persona.rung}`);
      ids.add(persona.id);
    }
    expect(ids.size).toBe(24);
  });

  describe('RUNG_BLEND', () => {
    it('800/1000/1200/1400 map to HUMAN_BLEND', () => {
      expect(RUNG_BLEND[800]).toBe(HUMAN_BLEND);
      expect(RUNG_BLEND[1000]).toBe(HUMAN_BLEND);
      expect(RUNG_BLEND[1200]).toBe(HUMAN_BLEND);
      expect(RUNG_BLEND[1400]).toBe(HUMAN_BLEND);
    });

    it('1800 maps to DEEP_BLEND', () => {
      expect(RUNG_BLEND[1800]).toBe(DEEP_BLEND);
    });

    it('1600 is defined and equals LIGHT_BLEND or DEEP_BLEND', () => {
      expect(RUNG_BLEND[1600]).toBeDefined();
      expect([LIGHT_BLEND, DEEP_BLEND]).toContain(RUNG_BLEND[1600]);
    });

    it('every Rung resolves to a defined blend', () => {
      for (const rung of ALL_RUNGS) {
        expect(RUNG_BLEND[rung]).toBeDefined();
      }
    });
  });

  it('every persona.botElo is a member of MAIA_ELO_LADDER (Phase 184 D-01: retargeted, no longer === rung)', () => {
    for (const persona of Object.values(PERSONA_REGISTRY)) {
      expect(MAIA_ELO_LADDER, persona.id).toContain(persona.botElo);
    }
  });

  it('every persona resolves BOT_STYLE_BUNDLES[persona.style] by reference identity, never a clone', () => {
    for (const persona of Object.values(PERSONA_REGISTRY)) {
      const resolved = BOT_STYLE_BUNDLES[persona.style];
      expect(resolved, persona.id).toBe(STYLE_SINGLETONS[persona.style]);
    }
  });

  it('every persona.blend is one of HUMAN_BLEND/LIGHT_BLEND/DEEP_BLEND (assumption_delta_decision invariant)', () => {
    for (const persona of Object.values(PERSONA_REGISTRY)) {
      expect([HUMAN_BLEND, LIGHT_BLEND, DEEP_BLEND], persona.id).toContain(persona.blend);
    }
  });

  it('every persona.name and persona.bio is a non-empty trimmed string', () => {
    for (const persona of Object.values(PERSONA_REGISTRY)) {
      expect(persona.name.trim().length, `${persona.id} name`).toBeGreaterThan(0);
      expect(persona.name).toBe(persona.name.trim());
      expect(persona.bio.trim().length, `${persona.id} bio`).toBeGreaterThan(0);
      expect(persona.bio).toBe(persona.bio.trim());
    }
  });

  it('the 24 species values are distinct', () => {
    const species = Object.values(PERSONA_REGISTRY).map((p) => p.species);
    expect(new Set(species).size).toBe(24);
  });

  it('every persona.avatarEmoji is a non-empty string', () => {
    for (const persona of Object.values(PERSONA_REGISTRY)) {
      expect(persona.avatarEmoji.length, persona.id).toBeGreaterThan(0);
    }
  });

  it('no persona ships an avatarSrc yet (D-16 — placeholders only this phase)', () => {
    for (const persona of Object.values(PERSONA_REGISTRY)) {
      expect(persona.avatarSrc, persona.id).toBeUndefined();
    }
  });
});

describe('CAL-05 calibrated label honesty (Phase 184)', () => {
  /** Parses a `~NNNN` calibrated label back to its numeric value. */
  function parseLabel(label: string): number {
    return Number(label.replace('~', ''));
  }

  it('every persona has a defined, non-empty calibratedLabel and botElo (24-slot completeness)', () => {
    for (const persona of Object.values(PERSONA_REGISTRY)) {
      expect(persona.calibratedLabel, persona.id).toBeDefined();
      expect(persona.calibratedLabel.trim().length, persona.id).toBeGreaterThan(0);
      expect(persona.botElo, persona.id).toBeDefined();
    }
  });

  it('every calibratedLabel is a tilde-prefixed integer, rounded to the nearest 50 (D-03)', () => {
    for (const persona of Object.values(PERSONA_REGISTRY)) {
      expect(persona.calibratedLabel, persona.id).toMatch(/^~\d+$/);
      const value = parseLabel(persona.calibratedLabel);
      expect(value % 50, persona.id).toBe(0);
    }
  });

  it('no calibratedLabel exceeds the ~1800 global ceiling (D-07)', () => {
    for (const persona of Object.values(PERSONA_REGISTRY)) {
      expect(parseLabel(persona.calibratedLabel), persona.id).toBeLessThanOrEqual(1800);
    }
  });

  it('every bottom-rung (800) persona carries a defined, non-blank label — the floor is acknowledged, never dropped (D-06)', () => {
    const floorPersonas = Object.values(PERSONA_REGISTRY).filter((p) => p.rung === 800);
    expect(floorPersonas).toHaveLength(4);
    for (const persona of floorPersonas) {
      expect(persona.calibratedLabel, persona.id).toBeDefined();
      expect(persona.calibratedLabel.trim().length, persona.id).toBeGreaterThan(0);
    }
  });

  it('calibratedLabel is non-decreasing by rung within each style column (D-04 monotonicity spot-check)', () => {
    for (const style of ALL_STYLES) {
      const personas = personasForSection(style);
      const values = personas.map((p) => parseLabel(p.calibratedLabel));
      for (let i = 1; i < values.length; i++) {
        const prev = values[i - 1];
        const curr = values[i];
        expect(prev, `${style} rung ${personas[i - 1]?.rung}->${personas[i]?.rung}`).toBeDefined();
        expect(curr).toBeGreaterThanOrEqual(prev as number);
      }
    }
  });
});

describe('STYLE_SECTION_ORDER', () => {
  it('deep-equals [Attacker, Trickster, Grinder, Wall]', () => {
    expect(STYLE_SECTION_ORDER).toEqual(['Attacker', 'Trickster', 'Grinder', 'Wall']);
  });
});

describe('personasForSection', () => {
  it.each(ALL_STYLES)('returns 6 personas for %s with rung strictly ascending', (style) => {
    const personas = personasForSection(style);
    expect(personas).toHaveLength(6);
    expect(personas.every((p) => p.style === style)).toBe(true);
    const rungs = personas.map((p) => p.rung);
    expect(rungs).toEqual([...rungs].sort((a, b) => a - b));
    expect(new Set(rungs).size).toBe(6);
  });
});

describe('personaForId', () => {
  it('returns the matching persona for a known id', () => {
    const persona = personaForId('attacker-800' as PersonaId);
    expect(persona?.name).toBe('Ziggy the Wasp');
  });

  it('returns undefined for an unrecognized id without throwing', () => {
    expect(() => personaForId('nonexistent-id' as PersonaId)).not.toThrow();
    expect(personaForId('nonexistent-id' as PersonaId)).toBeUndefined();
  });

  it('returns undefined for an undefined id without throwing', () => {
    expect(personaForId(undefined)).toBeUndefined();
  });
});

// Type-level exhaustiveness smoke check: this compiles only if every Persona
// below satisfies the full interface shape — a missing field is a TS error,
// not a runtime one, so this block has no runtime assertions.
function assertPersonaShape(p: Persona): void {
  void p.id;
  void p.style;
  void p.rung;
  void p.botElo;
  void p.calibratedLabel;
  void p.blend;
  void p.name;
  void p.species;
  void p.bio;
  void p.avatarEmoji;
}
for (const persona of Object.values(PERSONA_REGISTRY)) {
  assertPersonaShape(persona);
}
