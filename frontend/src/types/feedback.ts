/** Top of the 1-5 star rating scale — mirrors _MAX_RATING in app/schemas/feedback.py. */
export const MAX_RATING = 5;

/** Where a feedback submission came from. Mirrors FeedbackSource in app/schemas/feedback.py and ck_feedback_source. */
export type FeedbackSource = 'floating_button' | 'milestone_ask';

/** Request body sent to POST /api/feedback. */
export interface FeedbackRequest {
  text: string;
  /** Optional 1-5 star rating. */
  rating?: number;
  page_url: string;
  /** Optional on the wire; the server defaults to 'floating_button'. */
  source?: FeedbackSource;
}

/** Response from POST /api/feedback (201). */
export interface FeedbackResponse {
  id: number;
  created_at: string;
}
