/**
 * Confidence bucket shared by the score and eval significance gates. The backend computes the
 * score p-value and 99% Wilson CI (`app/services/score_confidence.py`, D-18); the frontend only
 * reads the resulting bucket.
 */

export type ConfidenceLevel = 'low' | 'medium' | 'high';
