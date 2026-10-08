/**
 * trainBubbleState.test.ts — Phase 222 Plan 01 Task 2 (D-07).
 *
 * Asserts the seven-way precedence chain resolveBubbleState implements:
 * verdict > grading > submitting > move > intro > drop-nudge > prompt. Pure-module test
 * template (mirrors trainScore.test.ts).
 */
import { describe, expect, it } from 'vitest';
import { resolveBubbleState } from '@/components/train/trainBubbleState';
import type { ResolveBubbleStateInput } from '@/components/train/trainBubbleState';

const BASE: ResolveBubbleStateInput = {
  hasVerdict: false,
  isGrading: false,
  isRechecking: false,
  isSubmitting: false,
  guessMade: false,
  introStep: null,
  nudgeActive: false,
};

describe('resolveBubbleState', () => {
  it('defaults to the prompt state when nothing else applies', () => {
    expect(resolveBubbleState(BASE)).toEqual({ kind: 'prompt' });
  });

  it('drop-nudge state when nudgeActive alone is true', () => {
    expect(resolveBubbleState({ ...BASE, nudgeActive: true })).toEqual({ kind: 'drop-nudge' });
  });

  it('intro state (carrying its step) when introStep is set', () => {
    expect(resolveBubbleState({ ...BASE, introStep: 1 })).toEqual({ kind: 'intro', step: 1 });
  });

  it('move state when the guess has been made', () => {
    expect(resolveBubbleState({ ...BASE, guessMade: true })).toEqual({ kind: 'move' });
  });

  it('grading state when isGrading is true', () => {
    expect(resolveBubbleState({ ...BASE, isGrading: true })).toEqual({ kind: 'grading', recheck: false });
  });

  // Phase 235 (D-12): the same grading state carries the re-check flag.
  it('grading state carries recheck: true while the disagreement re-check runs (D-12)', () => {
    expect(resolveBubbleState({ ...BASE, isGrading: true, isRechecking: true })).toEqual({
      kind: 'grading',
      recheck: true,
    });
  });

  it('a verdict still wins over a re-check in flight', () => {
    expect(
      resolveBubbleState({ ...BASE, hasVerdict: true, isGrading: true, isRechecking: true }),
    ).toEqual({ kind: 'verdict' });
  });

  // Phase 236 (D-16): the instant solve POST round trip.
  it('submitting state while the instant solve POST is in flight (D-16)', () => {
    expect(resolveBubbleState({ ...BASE, guessMade: true, isSubmitting: true })).toEqual({
      kind: 'submitting',
    });
  });

  it('a verdict beats submitting, and grading beats submitting', () => {
    expect(resolveBubbleState({ ...BASE, hasVerdict: true, isSubmitting: true })).toEqual({
      kind: 'verdict',
    });
    expect(resolveBubbleState({ ...BASE, isGrading: true, isSubmitting: true })).toEqual({
      kind: 'grading',
      recheck: false,
    });
  });

  it('submitting beats move, intro, drop-nudge', () => {
    expect(
      resolveBubbleState({ ...BASE, isSubmitting: true, guessMade: true, introStep: 2, nudgeActive: true }),
    ).toEqual({ kind: 'submitting' });
  });

  it('verdict state when hasVerdict is true', () => {
    expect(resolveBubbleState({ ...BASE, hasVerdict: true })).toEqual({ kind: 'verdict' });
  });

  describe('precedence — higher-priority states win over every lower one simultaneously true', () => {
    it('verdict beats grading, move, intro, drop-nudge', () => {
      expect(
        resolveBubbleState({
          hasVerdict: true,
          isGrading: true,
          isRechecking: false,
          isSubmitting: false,
          guessMade: true,
          introStep: 2,
          nudgeActive: true,
        }),
      ).toEqual({ kind: 'verdict' });
    });

    it('grading beats move, intro, drop-nudge', () => {
      expect(
        resolveBubbleState({
          hasVerdict: false,
          isGrading: true,
          isRechecking: false,
          isSubmitting: false,
          guessMade: true,
          introStep: 2,
          nudgeActive: true,
        }),
      ).toEqual({ kind: 'grading', recheck: false });
    });

    it('move beats intro, drop-nudge', () => {
      expect(
        resolveBubbleState({
          hasVerdict: false,
          isGrading: false,
          isRechecking: false,
          isSubmitting: false,
          guessMade: true,
          introStep: 2,
          nudgeActive: true,
        }),
      ).toEqual({ kind: 'move' });
    });

    it('intro beats drop-nudge', () => {
      expect(
        resolveBubbleState({
          hasVerdict: false,
          isGrading: false,
          isRechecking: false,
          isSubmitting: false,
          guessMade: false,
          introStep: 0,
          nudgeActive: true,
        }),
      ).toEqual({ kind: 'intro', step: 0 });
    });

    it('drop-nudge beats the prompt default', () => {
      expect(
        resolveBubbleState({
          hasVerdict: false,
          isGrading: false,
          isRechecking: false,
          isSubmitting: false,
          guessMade: false,
          introStep: null,
          nudgeActive: true,
        }),
      ).toEqual({ kind: 'drop-nudge' });
    });
  });
});
