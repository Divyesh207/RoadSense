"""
Download a small pool of road photographs for the faculty demo dataset.

Source: RDD2022 India, official TEST images (Arya et al. 2022, DOI 10.6084/m9.figshare.21431547,
licensed CC BY 4.0 on figshare; the authors' README states CC BY-SA 4.0). The official test
images have no released labels and were not used to train or evaluate the deployed model.

These are third-party photographs of roads in India. They were NOT taken at the demo
coordinates used by the seed script; the demo guide and every seeded record say so.

Only the requested images are transferred (HTTP range requests into the nested country zip),
not the 13 GB archive.

    python scripts/demo/fetch_demo_photos.py                 # the photos the demo seed uses
    python scripts/demo/fetch_demo_photos.py --count 160      # a wider pool, for choosing other photos
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import struct
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "fetch_rdd2022_subset", REPO / "services" / "ai-worker" / "training" / "fetch_rdd2022_subset.py"
)
_fetch = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_fetch)


class Window:
    """Read-only seekable view of [start, start + size) of another seekable file."""

    def __init__(self, base, start: int, size: int):
        self.base, self.start, self.size, self.pos = base, start, size, 0

    def read(self, n: int = -1) -> bytes:
        if n is None or n < 0:
            n = self.size - self.pos
        n = max(0, min(n, self.size - self.pos))
        self.base.seek(self.start + self.pos)
        data = self.base.read(n)
        self.pos += len(data)
        return data

    def seek(self, offset: int, whence: int = 0) -> int:
        self.pos = {0: offset, 1: self.pos + offset, 2: self.size + offset}[whence]
        return self.pos

    def tell(self) -> int:
        return self.pos

    def seekable(self) -> bool:
        return True

    def readable(self) -> bool:
        return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--country", default="India")
    parser.add_argument("--count", type=int, default=0,
                        help="download a pool of this many test images instead of the demo plan's photos")
    parser.add_argument("--step", type=int, default=9, help="take every Nth test image (spreads the sample)")
    parser.add_argument("--out", type=Path, default=REPO / "scripts" / "demo" / "photos" / "pool")
    args = parser.parse_args()

    remote = _fetch.HTTPRangeFile(_fetch.ARCHIVE_URL, _fetch.ARCHIVE_SIZE)
    print("Reading the archive's central directory...", flush=True)
    with zipfile.ZipFile(remote) as outer:
        info = outer.getinfo(f"RDD2022/{args.country}.zip")
        if info.compress_type != zipfile.ZIP_STORED:
            sys.exit("The country zip is compressed inside the archive; use fetch_rdd2022_subset.py instead.")
        # Local file header: 30 fixed bytes + file name + extra field, then the stored data.
        remote.seek(info.header_offset)
        header = remote.read(30)
        name_len, extra_len = struct.unpack("<HH", header[26:30])
        data_start = info.header_offset + 30 + name_len + extra_len

    inner_file = Window(remote, data_start, info.file_size)
    args.out.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(inner_file) as inner:
        tests = sorted(
            m.filename for m in inner.infolist()
            if "/test/images/" in m.filename and m.filename.lower().endswith(".jpg")
        )
        if args.count:
            chosen = tests[:: args.step][: args.count]
        else:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            from demo_plan import all_photos

            by_name = {Path(t).name: t for t in tests}
            missing = [n for n in all_photos() if n not in by_name]
            if missing:
                sys.exit(f"Not found among the test images: {missing}")
            chosen = [by_name[n] for n in all_photos() if not (args.out / n).exists()]
        print(f"{len(tests)} test images in {args.country}; downloading {len(chosen)}", flush=True)
        for i, name in enumerate(chosen, 1):
            target = args.out / Path(name).name
            if not target.exists():
                target.write_bytes(inner.read(name))      # CRC-32 verified by zipfile
            if i % 20 == 0:
                print(f"  {i}/{len(chosen)}", flush=True)

    (args.out / "SOURCE.json").write_text(json.dumps({
        "dataset": "RDD2022 - The multi-national Road Damage Dataset released through CRDDC'2022",
        "subset": f"{args.country}, official test images (unlabelled; not used to train or evaluate the model)",
        "doi": "10.6084/m9.figshare.21431547",
        "license": "CC BY 4.0 (figshare record); the authors' README states CC BY-SA 4.0",
        "citation": "Arya, D., Maeda, H., Ghosh, S. K., Toshniwal, D., & Sekimoto, Y. (2022). RDD2022: A "
                    "multi-national image dataset for automatic Road Damage Detection. arXiv:2209.08538.",
        "images": sorted(p.name for p in args.out.glob("*.jpg")),
        "note": "Third-party photographs. They were not captured at the RoadSense demo coordinates.",
        "bytes_fetched": remote.bytes_fetched,
    }, indent=2), encoding="utf-8")
    print(f"done: {len(chosen)} images in {args.out} ({remote.bytes_fetched / 1e6:.1f} MB transferred)")


if __name__ == "__main__":
    main()
