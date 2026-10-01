# Data & Model Artifact Directory

This directory stores local data artifacts and pre-trained model weights.

## Subdirectories

- `models/`: Local model weights and model metadata (e.g. YOLOv8 weights `.pt`, XGBoost `.json`).
- `media/`: Temporary local media storage for testing/development uploads before syncing to Supabase Storage.

## Security & Versioning

- Do **not** commit large training datasets or production customer media to Git.
- Model weights should be versioned with their associated `model_id`, `version`, and class mappings according to `08_AI_ML_SPECIFICATION.md`.
