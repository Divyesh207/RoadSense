# Road-damage detector training (RDD2022 → YOLO11s)

Reproducible scripts for the trained detector used by `inference/model_registry.py`.
Training runs in a **separate CUDA environment** outside this repository (the worker
image stays CPU-only and only loads the exported weights).

## Data and model sources

| Item | Source | License |
|---|---|---|
| RDD2022 (India subset) | figshare, DOI [10.6084/m9.figshare.21431547](https://doi.org/10.6084/m9.figshare.21431547) | CC BY 4.0 on figshare; the authors' README states CC BY-SA 4.0 (treated as CC BY-SA 4.0) |
| `yolo11s.pt` (COCO-pretrained start point) | [ultralytics/assets v8.3.0](https://github.com/ultralytics/assets/releases/tag/v8.3.0) | AGPL-3.0 |

Citation: Arya, D., Maeda, H., Ghosh, S. K., Toshniwal, D., & Sekimoto, Y. (2022).
*RDD2022: A multi-national image dataset for automatic Road Damage Detection.* arXiv:2209.08538.

The per-country zips on the authors' S3 host return HTTP 403, so
`fetch_rdd2022_subset.py` reads only one country folder out of the official 13.26 GB
figshare archive using HTTP range requests (each file's CRC-32 is verified).

## Classes

The model is trained on the original RDD codes only:

| Model class | Meaning | Platform class |
|---|---|---|
| D00 | longitudinal crack | CRACK |
| D10 | transverse crack | CRACK |
| D20 | alligator crack | CRACK |
| D40 | pothole | POTHOLE |

The original code is kept per detection (`model_class_name`). Other RDD labels
(road-marking blur etc.) are dropped. The model does **not** detect DEPRESSION,
WATERLOGGING, SURFACE_DAMAGE or OTHER.

## Steps

```bash
# 0. Separate environment (example: E:\rdd-training\venv)
python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
python -m pip install ultralytics

# 1. Fetch one country folder (standard library only)
python fetch_rdd2022_subset.py --country India --out E:/rdd-training/data/raw

# 2. VOC -> YOLO, keep D00/D10/D20/D40, fixed 80/10/10 split (seed 42)
python prepare_rdd2022.py --source E:/rdd-training/data/raw/RDD2022/India --out E:/rdd-training/data/rdd2022_india_yolo

# 3. Sanity run, then full training
python train_yolo.py --data .../data.yaml --weights E:/rdd-training/weights/yolo11s.pt --project E:/rdd-training/runs --name sanity --epochs 2 --fraction 0.1
python train_yolo.py --data .../data.yaml --weights E:/rdd-training/weights/yolo11s.pt --project E:/rdd-training/runs --name india_yolo11s

# 4. Threshold on val, metrics on held-out test, export weights + sidecar
python evaluate_yolo.py --run E:/rdd-training/runs/india_yolo11s --data .../data.yaml --out E:/rdd-training/export/road_damage_yolo11s_rdd2022_india.pt
```

## Deploying

Copy `<name>.pt` and `<name>.pt.json` to `data/models/` (git-ignored), set
`YOLO_MODEL_FILE=<name>.pt` and `AI_REQUIRE_TRAINED_MODEL=true` in `.env`, and
restart the `ai-worker` service. The sidecar's SHA-256, dataset, configuration,
threshold and **measured** test metrics become the model's recorded provenance.

Metrics are measured on a held-out split of RDD2022 India. They are not evidence of
accuracy on other cities, cameras or conditions.
