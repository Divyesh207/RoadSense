"""
Fine-tune an Ultralytics YOLO detector on a dataset produced by prepare_rdd2022.py.

Run from the separate CUDA training environment (not the worker image):
    python train_yolo.py --data E:/rdd-training/data/rdd2022_india_yolo/data.yaml \
        --weights E:/rdd-training/weights/yolo11s.pt --project E:/rdd-training/runs --name india_yolo11s

A short sanity run (pipeline + CUDA + memory check) uses --fraction / --epochs:
    python train_yolo.py ... --name sanity --epochs 2 --fraction 0.1
"""

import argparse
import json
import platform
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data", required=True, type=Path)
    parser.add_argument("--weights", required=True, type=Path, help="Pretrained starting weights, e.g. yolo11s.pt")
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--name", required=True)
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--patience", type=int, default=20)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--fraction", type=float, default=1.0, help="Fraction of the train split (sanity runs)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--skip-amp-check",
        action="store_true",
        help="Skip Ultralytics' AMP self-check, which downloads an extra model (yolo11n.pt). "
        "AMP stays enabled; watch the loss for NaNs in the sanity run.",
    )
    args = parser.parse_args()

    import torch
    from ultralytics import YOLO
    from ultralytics import __version__ as ultralytics_version

    if not torch.cuda.is_available():
        raise SystemExit("CUDA is not available in this environment; refusing to train on CPU.")

    environment = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "torch": torch.__version__,
        "torch_cuda": torch.version.cuda,
        "gpu": torch.cuda.get_device_name(0),
        "ultralytics": ultralytics_version,
    }
    print(json.dumps(environment, indent=2), flush=True)

    if args.skip_amp_check:
        import ultralytics.engine.trainer as trainer_module

        trainer_module.check_amp = lambda *_args, **_kwargs: True

    model = YOLO(str(args.weights))
    model.train(
        data=str(args.data),
        epochs=args.epochs,
        patience=args.patience,
        imgsz=args.imgsz,
        batch=args.batch,
        workers=args.workers,
        fraction=args.fraction,
        seed=args.seed,
        deterministic=True,
        device=0,
        amp=True,
        project=str(args.project),
        name=args.name,
        exist_ok=False,
        plots=True,
    )

    run_dir = Path(model.trainer.save_dir)
    config = {
        "base_weights": args.weights.name,
        "data": str(args.data),
        "epochs_requested": args.epochs,
        "patience": args.patience,
        "imgsz": args.imgsz,
        "batch": args.batch,
        "workers": args.workers,
        "fraction": args.fraction,
        "seed": args.seed,
        "amp": True,
        "amp_self_check_skipped": args.skip_amp_check,
        "peak_gpu_memory_gb": round(torch.cuda.max_memory_reserved(0) / 1024**3, 2),
        "environment": environment,
    }
    (run_dir / "training_config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    print(f"Run directory: {run_dir}", flush=True)


if __name__ == "__main__":
    main()
