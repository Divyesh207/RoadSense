"""
Evaluate a trained run and write the deployable weights + metadata sidecar.

1. Confidence threshold is chosen on the VALIDATION split (max mean F1 over classes).
2. Metrics are measured once on the held-out TEST split (never used for training or
   model selection). Precision/recall are Ultralytics' values at each class's
   max-F1 confidence; mAP50 and mAP50-95 are threshold-independent.
3. Writes <out>.pt and <out>.pt.json (read by inference/model_registry.py). Every
   number in the sidecar is measured here or copied from the training run.

    python evaluate_yolo.py --run E:/rdd-training/runs/india_yolo11s \
        --data E:/rdd-training/data/rdd2022_india_yolo/data.yaml \
        --out E:/rdd-training/export/road_damage_yolo11s_rdd2022_india.pt
"""

import argparse
import csv
import hashlib
import json
import shutil
from pathlib import Path

# Platform classes the model's RDD codes map to (see inference/detector.py aliases).
CLASS_MAPPING = {"D00": "CRACK", "D10": "CRACK", "D20": "CRACK", "D40": "POTHOLE"}
NOT_DETECTED = ["DEPRESSION", "WATERLOGGING", "SURFACE_DAMAGE", "OTHER"]
DATASET = {
    "name": "RDD2022 - The multi-national Road Damage Dataset released through CRDDC'2022",
    "subset": "India (annotated train images only; official test images have no released labels)",
    "doi": "10.6084/m9.figshare.21431547",
    "url": "https://figshare.com/articles/dataset/RDD2022_-_The_multi-national_Road_Damage_Dataset_released_through_CRDDC_2022/21431547",
    "license": "CC BY 4.0 (figshare record); the authors' README states CC BY-SA 4.0 - treated as CC BY-SA 4.0",
    "citation": "Arya, D., Maeda, H., Ghosh, S. K., Toshniwal, D., & Sekimoto, Y. (2022). RDD2022: A multi-national "
    "image dataset for automatic Road Damage Detection. arXiv:2209.08538.",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def f1_threshold(metrics) -> tuple[float, float]:
    for x, y, _xlabel, ylabel in metrics.box.curves_results:
        if str(ylabel).lower().startswith("f1"):
            mean_f1 = y.mean(0)
            i = int(mean_f1.argmax())
            return round(float(x[i]), 3), round(float(mean_f1[i]), 4)
    raise RuntimeError("F1-confidence curve not found in validation metrics")


def read_results_csv(run: Path) -> dict:
    rows = list(csv.DictReader((run / "results.csv").open(encoding="utf-8")))
    rows = [{k.strip(): v for k, v in r.items()} for r in rows]
    best = max(rows, key=lambda r: float(r["metrics/mAP50-95(B)"]))
    keys = ["train/box_loss", "train/cls_loss", "train/dfl_loss", "val/box_loss", "val/cls_loss", "val/dfl_loss"]

    def pick(row: dict) -> dict:
        return {k: round(float(row[k]), 4) for k in keys}

    return {"epochs_trained": len(rows), "best_epoch": int(float(best["epoch"])), "final_epoch_losses": pick(rows[-1]),
            "best_epoch_losses": pick(best)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--data", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--model-id", default="rdd2022-india-yolo11s")
    parser.add_argument("--version", default="india-v1")
    args = parser.parse_args()

    from ultralytics import YOLO

    best = args.run / "weights" / "best.pt"
    model = YOLO(str(best))
    names = model.names

    # workers=0: Ultralytics' worker processes are unreliable on Windows outside the training loop
    val = model.val(data=str(args.data), split="val", plots=True, workers=0, project=str(args.run), name="eval_val",
                    exist_ok=True)
    threshold, val_f1 = f1_threshold(val)

    test = model.val(data=str(args.data), split="test", plots=True, workers=0, project=str(args.run), name="eval_test",
                     exist_ok=True)
    per_class = {}
    for i, cls_idx in enumerate(test.box.ap_class_index):
        p, r, ap50, ap = test.box.class_result(i)
        code = names[int(cls_idx)]
        per_class[code] = {"precision": round(float(p), 4), "recall": round(float(r), 4),
                           "mAP50": round(float(ap50), 4), "mAP50_95": round(float(ap), 4)}

    # Confusion matrix and per-class counts at the deployment threshold (the default
    # validation confusion matrix uses conf=0.001 and is not representative).
    at_threshold = model.val(data=str(args.data), split="test", conf=threshold, plots=True, workers=0,
                             project=str(args.run), name=f"eval_test_conf{threshold}", exist_ok=True, verbose=False)
    cm = at_threshold.confusion_matrix.matrix.astype(int)  # rows = predicted, cols = true; last = background
    labels = [names[i] for i in range(len(names))] + ["background"]
    threshold_counts = {}
    for i in range(len(names)):
        tp, fp, fn = int(cm[i, i]), int(cm[i, :].sum() - cm[i, i]), int(cm[:, i].sum() - cm[i, i])
        threshold_counts[labels[i]] = {
            "tp": tp, "fp": fp, "fn": fn,
            "precision": round(tp / (tp + fp), 4) if tp + fp else None,
            "recall": round(tp / (tp + fn), 4) if tp + fn else None,
        }

    dataset_summary = json.loads((args.data.parent / "dataset_summary.json").read_text(encoding="utf-8"))
    training_config = json.loads((args.run / "training_config.json").read_text(encoding="utf-8"))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(best, args.out)
    weights_sha = sha256(args.out)

    sidecar = {
        "model_id": args.model_id,
        "version": args.version,
        "name": "YOLO11s fine-tuned on RDD2022 India (cracks D00/D10/D20, potholes D40)",
        "input_size": training_config["imgsz"],
        "metrics": {
            "evaluation_split": "test: held-out 10% of RDD2022 India annotated images (seed 42), not used in training",
            "precision": round(float(test.box.mp), 4),
            "recall": round(float(test.box.mr), 4),
            "mAP50": round(float(test.box.map50), 4),
            "mAP50_95": round(float(test.box.map), 4),
            "per_class": per_class,
            "test_instances": dataset_summary["splits"]["test"]["instances"],
            "at_deployment_threshold": {
                "confidence_threshold": threshold,
                "confusion_matrix": {"labels": labels, "rows_predicted_cols_true": cm.tolist()},
                "per_class": threshold_counts,
            },
            "note": "Measured on RDD2022 India only; not a measure of accuracy on other cities (e.g. Pune) or cameras.",
        },
        "training": {
            "dataset": {**DATASET, "splits": dataset_summary["splits"], "seed": dataset_summary["seed"],
                        "dropped_labels": dataset_summary["dropped_labels"]},
            "model_class_names": {str(k): v for k, v in names.items()},
            "class_descriptions": dataset_summary["class_descriptions"],
            "class_mapping_to_platform": CLASS_MAPPING,
            "platform_classes_not_detected": NOT_DETECTED,
            "base_model": {"weights": training_config["base_weights"], "source":
                           "https://github.com/ultralytics/assets/releases/tag/v8.3.0", "license": "AGPL-3.0"},
            "config": {k: training_config[k] for k in ("epochs_requested", "patience", "imgsz", "batch", "seed", "amp")},
            "environment": training_config["environment"],
            "peak_gpu_memory_gb": training_config["peak_gpu_memory_gb"],
            **read_results_csv(args.run),
            "confidence_threshold": {
                "value": threshold,
                "selected_on": "validation split",
                "method": "argmax of mean per-class F1 over confidence",
                "validation_mean_f1_at_threshold": val_f1,
                "score_semantics": "YOLO class confidence; uncalibrated model score, not a probability of correctness",
            },
            "weights_sha256": weights_sha,
        },
    }
    sidecar_path = args.out.with_suffix(args.out.suffix + ".json")
    sidecar_path.write_text(json.dumps(sidecar, indent=2), encoding="utf-8")
    print(json.dumps({"weights": str(args.out), "sha256": weights_sha, "threshold": threshold,
                      "metrics": sidecar["metrics"]}, indent=2))


if __name__ == "__main__":
    main()
