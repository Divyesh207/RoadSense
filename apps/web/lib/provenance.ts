// Honest labels for how a detection/damage record was produced (API: detection_method, score_type).
// The OpenCV fallback is a rule-based heuristic: its score is not a model probability.

export type DetectionMethod = "TRAINED_MODEL" | "HEURISTIC_FALLBACK" | "MANUAL" | "UNKNOWN";
export type ScoreType = "MODEL_CONFIDENCE" | "HEURISTIC_SCORE";

export function isHeuristic(method?: string | null, scoreType?: string | null): boolean {
  return method === "HEURISTIC_FALLBACK" || scoreType === "HEURISTIC_SCORE";
}

/** Column/label text for a score: "Confidence" only for trained-model output. */
export function scoreLabel(scoreType?: string | null): string {
  if (scoreType === "MODEL_CONFIDENCE") return "Model confidence";
  if (scoreType === "HEURISTIC_SCORE") return "Heuristic score";
  return "Score";
}

export function detectionMethodLabel(method?: string | null): string {
  switch (method) {
    case "TRAINED_MODEL":
      return "Trained model";
    case "HEURISTIC_FALLBACK":
      return "Heuristic fallback (OpenCV rules, not a trained model)";
    case "MANUAL":
      return "Manual entry";
    default:
      return "Unknown method";
  }
}
