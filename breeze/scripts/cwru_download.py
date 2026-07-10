"""Resume-safe downloader for the CWRU manifest."""

from __future__ import annotations

import argparse
import csv
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.error import URLError


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = ROOT / "analysis" / "cwru_de12k_full_manifest_2026-07-05.csv"
RAW_FULL = ROOT / "data" / "cwru" / "raw" / "de12k_full"
RAW_SMOKE = ROOT / "data" / "cwru" / "raw" / "smoke"
ANALYSIS = ROOT / "analysis"


def read_manifest(path: Path) -> list[dict[str, str]]:
    with path.open() as fh:
        return list(csv.DictReader(fh))


def copy_if_smoke_exists(filename: str, out_path: Path) -> bool:
    smoke_path = RAW_SMOKE / filename
    if not smoke_path.exists() or out_path.exists():
        return False
    out_path.write_bytes(smoke_path.read_bytes())
    return True


def download_one(row: dict[str, str], out_dir: Path, retries: int = 3) -> dict[str, object]:
    out_path = out_dir / row["filename"]
    if out_path.exists() and out_path.stat().st_size > 100_000:
        return {**row, "status": "exists", "bytes": out_path.stat().st_size, "local_path": str(out_path)}
    if copy_if_smoke_exists(row["filename"], out_path):
        return {**row, "status": "copied_from_smoke", "bytes": out_path.stat().st_size, "local_path": str(out_path)}
    tmp = out_path.with_suffix(out_path.suffix + ".tmp")
    last_error = ""
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(row["source_url"], timeout=120) as response:
                data = response.read()
            if len(data) < 100_000:
                raise RuntimeError(f"download too small: {len(data)} bytes")
            tmp.write_bytes(data)
            tmp.replace(out_path)
            return {**row, "status": "downloaded", "bytes": out_path.stat().st_size, "local_path": str(out_path)}
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            time.sleep(2**attempt)
    return {**row, "status": "failed", "bytes": 0, "local_path": str(out_path), "error": last_error}


def write_status(rows: list[dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for row in rows for key in row.keys()})
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--out-dir", default=str(RAW_FULL))
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    manifest = read_manifest(Path(args.manifest))
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(download_one, row, out_dir) for row in manifest]
        for i, fut in enumerate(as_completed(futures), start=1):
            row = fut.result()
            rows.append(row)
            print(f"{i}/{len(futures)} {row['filename']} {row['status']} {row.get('bytes', 0)}", flush=True)
    status_path = ANALYSIS / "cwru_de12k_full_download_status_2026-07-05.csv"
    write_status(rows, status_path)
    failed = [r for r in rows if r["status"] == "failed"]
    print(f"wrote {status_path}")
    print(f"downloaded/available={len(rows) - len(failed)} failed={len(failed)}")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
