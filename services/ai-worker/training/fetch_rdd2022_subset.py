"""
Fetch one country's zip from the official RDD2022 archive on figshare without
downloading the whole 13.26 GB archive, then extract it.

Source (official dataset record): https://doi.org/10.6084/m9.figshare.21431547
File: RDD2022_released_through_CRDDC2022.zip (13,264,172,619 bytes)

The archive nests one zip per country (e.g. RDD2022/India.zip, 526,709,145 bytes).
Only the central directory and that member's byte range are fetched via HTTP range
requests. CRC-32 is verified for the member and for every file inside it, so a
corrupted transfer fails instead of producing bad data.

Usage (standard library only):
    python fetch_rdd2022_subset.py --country India --out E:/rdd-training/data/raw
"""

import argparse
import hashlib
import json
import time
import urllib.request
import zipfile
from collections import OrderedDict
from pathlib import Path

ARCHIVE_URL = "https://ndownloader.figshare.com/files/38030910"
ARCHIVE_SIZE = 13_264_172_619
BLOCK = 8 * 1024 * 1024


class HTTPRangeFile:
    """Minimal read-only, seekable file over HTTP range requests with a small block cache."""

    def __init__(self, url: str, size: int):
        self.url, self.size, self.pos = url, size, 0
        self.cache: OrderedDict[int, bytes] = OrderedDict()
        self.bytes_fetched = 0
        self.requests = 0

    def _fetch(self, start: int, end: int) -> bytes:
        for attempt in range(5):
            try:
                req = urllib.request.Request(self.url, headers={"Range": f"bytes={start}-{end - 1}"})
                with urllib.request.urlopen(req, timeout=60) as resp:
                    if resp.status != 206:
                        raise OSError(f"expected 206 Partial Content, got {resp.status}")
                    data = resp.read()
                if len(data) != end - start:
                    raise OSError(f"short read {len(data)} != {end - start}")
                self.bytes_fetched += len(data)
                self.requests += 1
                return data
            except OSError:
                if attempt == 4:
                    raise
                time.sleep(2 * (attempt + 1))
        raise AssertionError("unreachable")

    def _block(self, index: int) -> bytes:
        if index in self.cache:
            self.cache.move_to_end(index)
            return self.cache[index]
        start = index * BLOCK
        data = self._fetch(start, min(start + BLOCK, self.size))
        self.cache[index] = data
        if len(self.cache) > 8:
            self.cache.popitem(last=False)
        return data

    def read(self, n: int = -1) -> bytes:
        if n is None or n < 0:
            n = self.size - self.pos
        n = min(n, self.size - self.pos)
        if n <= 0:
            return b""
        if n > 2 * BLOCK:  # large reads (e.g. the central directory) in one request
            data = self._fetch(self.pos, self.pos + n)
        else:
            out = bytearray()
            pos = self.pos
            while len(out) < n:
                idx, off = divmod(pos, BLOCK)
                chunk = self._block(idx)[off : off + (n - len(out))]
                out += chunk
                pos += len(chunk)
            data = bytes(out)
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
    parser.add_argument("--country", required=True, help="Folder under RDD2022/, e.g. India")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    remote = HTTPRangeFile(ARCHIVE_URL, ARCHIVE_SIZE)
    print("Reading the archive's central directory...", flush=True)
    member_name = f"RDD2022/{args.country}.zip"  # the archive nests one zip per country
    args.out.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(remote) as zf:
        info = zf.getinfo(member_name)
        print(f"{member_name}: {info.file_size} bytes", flush=True)
        country_zip = args.out / f"{args.country}.zip"
        with zf.open(info) as src, country_zip.open("wb") as dst:  # CRC-32 checked at end of read
            copied = 0
            while chunk := src.read(4 * 1024 * 1024):
                dst.write(chunk)
                copied += len(chunk)
                if copied % (64 * 1024 * 1024) < 4 * 1024 * 1024:
                    print(f"  {copied / 1e6:.0f}/{info.file_size / 1e6:.0f} MB", flush=True)

    with zipfile.ZipFile(country_zip) as inner:
        bad = inner.testzip()
        if bad is not None:
            raise SystemExit(f"CRC mismatch in {bad}")
        inner.extractall(args.out)
        members = [m for m in inner.infolist() if not m.is_dir()]
    total = info.file_size
    country_sha = hashlib.sha256(country_zip.read_bytes()).hexdigest()
    print(f"extracted {len(members)} files; {country_zip.name} sha256 {country_sha}", flush=True)

    summary = {
        "source": ARCHIVE_URL,
        "doi": "10.6084/m9.figshare.21431547",
        "country": args.country,
        "archive_member": member_name,
        "country_zip_bytes": total,
        "country_zip_sha256": country_sha,
        "files": len(members),
        "bytes_fetched": remote.bytes_fetched,
        "http_requests": remote.requests,
        "crc_verified": True,
    }
    (args.out / f"fetch_{args.country}.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
