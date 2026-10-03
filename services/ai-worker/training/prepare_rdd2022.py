"""
Convert an RDD2022 country subset (Pascal VOC XML) into a YOLO detection dataset.

Only the four road-damage classes are kept, with their original RDD codes as the
class names (the worker maps D00/D10/D20 -> CRACK and D40 -> POTHOLE and keeps the
original name per detection). Other RDD labels (e.g. D43/D44 road-marking blur,
D50 manhole, Repair) are dropped and counted, never remapped.

The official RDD2022 test images have no released annotations, so the annotated
*train* images are split per image into train/val/test with a fixed seed.
Images without any kept damage stay in the dataset as negatives.

Usage (from the training environment):
    python prepare_rdd2022.py --source E:/rdd-training/data/raw/India --out E:/rdd-training/data/rdd2022_india_yolo
"""

import argparse
import json
import random
import shutil
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

# Class index order is part of the model contract (recorded in the model metadata).
CLASSES = ["D00", "D10", "D20", "D40"]
CLASS_DESCRIPTIONS = {
    "D00": "longitudinal crack",
    "D10": "transverse crack",
    "D20": "alligator crack",
    "D40": "pothole",
}
SPLIT_FRACTIONS = {"train": 0.8, "val": 0.1, "test": 0.1}
SEED = 42


def parse_voc(xml_path: Path) -> tuple[int, int, list[tuple[str, float, float, float, float]]]:
    root = ET.parse(xml_path).getroot()
    size = root.find("size")
    width = int(float(size.findtext("width")))
    height = int(float(size.findtext("height")))
    objects = []
    for obj in root.iter("object"):
        name = (obj.findtext("name") or "").strip()
        box = obj.find("bndbox")
        if box is None:
            continue
        coords = [float(box.findtext(k)) for k in ("xmin", "ymin", "xmax", "ymax")]
        objects.append((name, *coords))
    return width, height, objects


def to_yolo_line(cls_idx: int, w: int, h: int, xmin: float, ymin: float, xmax: float, ymax: float) -> str | None:
    xmin, xmax = max(0.0, min(xmin, w)), max(0.0, min(xmax, w))
    ymin, ymax = max(0.0, min(ymin, h)), max(0.0, min(ymax, h))
    if xmax - xmin < 1 or ymax - ymin < 1:
        return None
    cx, cy = (xmin + xmax) / 2 / w, (ymin + ymax) / 2 / h
    bw, bh = (xmax - xmin) / w, (ymax - ymin) / h
    return f"{cls_idx} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", required=True, type=Path, help="Extracted country folder (contains train/)")
    parser.add_argument("--out", required=True, type=Path, help="Output YOLO dataset directory")
    args = parser.parse_args()

    xml_files = sorted(args.source.glob("train/**/*.xml"))
    if not xml_files:
        raise SystemExit(f"No VOC XML annotations found under {args.source}/train")

    image_index = {p.stem: p for p in args.source.glob("train/**/*.jpg")}
    samples = []
    dropped = Counter()
    kept = Counter()
    skipped_boxes = 0
    missing_images = 0
    for xml_path in xml_files:
        image = image_index.get(xml_path.stem)
        if image is None:
            missing_images += 1
            continue
        w, h, objects = parse_voc(xml_path)
        lines = []
        for name, xmin, ymin, xmax, ymax in objects:
            if name not in CLASSES:
                dropped[name] += 1
                continue
            line = to_yolo_line(CLASSES.index(name), w, h, xmin, ymin, xmax, ymax)
            if line is None:
                skipped_boxes += 1
                continue
            kept[name] += 1
            lines.append(line)
        samples.append((image, lines))

    rng = random.Random(SEED)
    rng.shuffle(samples)
    n = len(samples)
    n_train = int(n * SPLIT_FRACTIONS["train"])
    n_val = int(n * SPLIT_FRACTIONS["val"])
    splits = {
        "train": samples[:n_train],
        "val": samples[n_train : n_train + n_val],
        "test": samples[n_train + n_val :],
    }

    if args.out.exists():
        shutil.rmtree(args.out)
    stats: dict[str, dict] = {}
    for split, items in splits.items():
        img_dir, lbl_dir = args.out / "images" / split, args.out / "labels" / split
        img_dir.mkdir(parents=True)
        lbl_dir.mkdir(parents=True)
        per_class = Counter()
        negatives = 0
        for image, lines in items:
            shutil.copy2(image, img_dir / image.name)
            (lbl_dir / f"{image.stem}.txt").write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
            if not lines:
                negatives += 1
            for line in lines:
                per_class[CLASSES[int(line.split()[0])]] += 1
        stats[split] = {"images": len(items), "negative_images": negatives, "instances": dict(sorted(per_class.items()))}

    (args.out / "data.yaml").write_text(
        "\n".join(
            [
                f"path: {args.out.as_posix()}",
                "train: images/train",
                "val: images/val",
                "test: images/test",
                "names:",
                *[f"  {i}: {c}" for i, c in enumerate(CLASSES)],
                "",
            ]
        ),
        encoding="utf-8",
    )
    summary = {
        "source": str(args.source),
        "classes": CLASSES,
        "class_descriptions": CLASS_DESCRIPTIONS,
        "seed": SEED,
        "split_fractions": SPLIT_FRACTIONS,
        "annotated_images": n,
        "xml_without_image": missing_images,
        "kept_instances": dict(sorted(kept.items())),
        "dropped_labels": dict(sorted(dropped.items())),
        "degenerate_boxes_skipped": skipped_boxes,
        "splits": stats,
    }
    (args.out / "dataset_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
