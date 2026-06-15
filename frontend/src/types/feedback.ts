/** Top of the 1-5 star rating scale — mirrors _MAX_RATING in app/schemas/feedback.py. */
export const MAX_RATING = 5;

/** Request body sent to POST /api/feedback. */
export interface FeedbackRequest {
  text: string;
  /** Optional 1-5 star rating. */
  rating?: number;
  page_url: string;
}

/** Response from POST /api/feedback (201). */
export interface FeedbackResponse {
  id: number;
  created_at: string;
}
