/**
 * Phase 234 (SEED-191, D-01/D-02): copy and eligibility helpers for Hilda's
 * milestone feedback ask. One sentence serves both rounds (D-02), so there is
 * no round parameter anywhere in the frontend.
 */

import { useSyncExternalStore } from 'react';
import type { UserProfile } from '@/types/users';

/** D-01: the ask copy, quoting the user's active-day count. */
export function feedbackAskCopy(activeDays: number): string {
  return `You've been with FlawChess for ${activeDays} days now, thanks! Got an idea that would make it better for you?`;
}

/**
 * The one predicate every surface reads (Import, Train landing, Bots roster):
 * the profile's active-day count when the server says the ask is active, else
 * null. The optional chaining tolerates a profile from a backend that predates
 * the field (deploy window) and partial profile fixtures in pre-existing tests.
 */
export function feedbackAskDays(profile: UserProfile | undefined | null): number | null {
  return profile?.feedback_ask?.active === true ? profile.active_days : null;
}

/** SEED-191 #5 example wording: Hilda's prompt inside the feedback modal. */
export const FEEDBACK_ASK_PLACEHOLDER = "What's one thing you'd change or add?";

// Modal open flag as a module store (playActive.ts pattern), not context: the
// opener (a bubble inside a page) and the host (ProtectedLayout) live in
// unrelated subtrees, since the layout wraps the router Outlet.
let modalOpen = false;
const modalListeners = new Set<() => void>();

function setModalOpen(next: boolean): void {
  if (modalOpen === next) return;
  modalOpen = next;
  modalListeners.forEach((listener) => listener());
}

function subscribeModalOpen(listener: () => void): () => void {
  modalListeners.add(listener);
  return () => modalListeners.delete(listener);
}

/** Opens the app-level feedback modal (rendered by FeedbackAskModalHost). */
export function openFeedbackAskModal(): void {
  setModalOpen(true);
}

export function closeFeedbackAskModal(): void {
  setModalOpen(false);
}

export function useFeedbackAskModalOpen(): boolean {
  return useSyncExternalStore(subscribeModalOpen, () => modalOpen);
}
