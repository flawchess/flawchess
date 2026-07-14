/**
 * botTimeControlPresets — the 9 lichess-style time-control presets offered on
 * the Bots setup screen (Phase 171 D-14, PLAY-02). Bullet is excluded by
 * design (client-side compute headroom, milestone framing) — do not add a
 * bullet row here.
 *
 * `frontend/src/types/bots.ts`'s `StoreBotGameRequest.tc_preset` doc comment
 * carries the load-bearing warning this module exists to prevent: the
 * DISPLAY label (e.g. "10+5") must never reach `BotGameSettings` or the
 * store-time wire format directly. Every preset here resolves to a concrete
 * `{ baseSeconds, incrementSeconds }` pair up front; `toBackendTcStr`
 * (`botGamePgn.ts`) converts that pair to the wire's base-seconds string
 * (`"600+5"`) at store time — this module does not duplicate that
 * conversion, only the label -> seconds lookup.
 */

export interface TimeControlPreset {
  /** The lichess-style display label, e.g. "10+5". Never sent to the wire. */
  label: string;
  baseSeconds: number;
  incrementSeconds: number;
  /**
   * UI grouping label ONLY (Blitz / Rapid / Classical sub-headers on the
   * setup screen's chip grid). This is NOT the backend's `time_control_bucket`
   * — see the `30+0` row below for the one documented mismatch.
   */
  bucket: 'blitz' | 'rapid' | 'classical';
}

export const TIME_CONTROL_PRESETS: readonly TimeControlPreset[] = [
  { label: '3+0', baseSeconds: 180, incrementSeconds: 0, bucket: 'blitz' },
  { label: '3+2', baseSeconds: 180, incrementSeconds: 2, bucket: 'blitz' },
  { label: '5+0', baseSeconds: 300, incrementSeconds: 0, bucket: 'blitz' },
  { label: '5+3', baseSeconds: 300, incrementSeconds: 3, bucket: 'blitz' },
  { label: '10+0', baseSeconds: 600, incrementSeconds: 0, bucket: 'rapid' },
  { label: '10+5', baseSeconds: 600, incrementSeconds: 5, bucket: 'rapid' },
  { label: '15+10', baseSeconds: 900, incrementSeconds: 10, bucket: 'rapid' },
  // NOTE (accepted, documented quirk — RESEARCH.md Pitfall 4, do NOT "fix"
  // this here or in app/services/normalization.py): the backend's frozen
  // `parse_time_control` computes `estimated = base + inc*40 = 1800 + 0 = 1800`,
  // and its boundary rule sends `estimated <= 1800` to the RAPID bucket, not
  // classical. So a stored 30+0 bot game carries `time_control_bucket =
  // 'rapid'` and its player-rating anchor is looked up under `rapid`, even
  // though this UI groups it under the "Classical" sub-header. The `bucket`
  // field below is a UI display-grouping label ONLY.
  { label: '30+0', baseSeconds: 1800, incrementSeconds: 0, bucket: 'classical' },
  { label: '30+20', baseSeconds: 1800, incrementSeconds: 20, bucket: 'classical' },
] as const;

export const DEFAULT_TC_PRESET_LABEL = '10+0';

/** Looks up a preset by its display label. Returns `undefined` for an
 * unrecognized label — callers fall back to `DEFAULT_TC_PRESET_LABEL`. */
export function findPresetByLabel(label: string): TimeControlPreset | undefined {
  return TIME_CONTROL_PRESETS.find((preset) => preset.label === label);
}
