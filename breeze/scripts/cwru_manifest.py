"""Parse official CWRU HTML pages into a download manifest."""

from __future__ import annotations

import argparse
import csv
import html
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
META = ROOT / "data" / "cwru" / "meta"
ANALYSIS = ROOT / "analysis"

LINK_RE = re.compile(r'<a\s+href="(?P<href>https://engineering\.case\.edu/sites/default/files/(?P<file>\d+\.mat))"[^>]*>(?P<label>[^<]+)</a>')


def parse_normal_page(path: Path) -> list[dict[str, object]]:
    text = path.read_text(errors="ignore")
    rows = []
    for match in LINK_RE.finditer(text):
        label = html.unescape(match.group("label")).strip()
        if not label.startswith("Normal_"):
            continue
        load = int(label.split("_")[-1])
        rpm_match = re.search(rf"(\d{{4}})</td>\s*<td[^>]*>\s*{re.escape(match.group(0))}", text)
        rpm_by_load = {0: 1797, 1: 1772, 2: 1750, 3: 1730}
        rows.append(
            {
                "protocol": "cwru_de12k_full",
                "file_id": int(match.group("file").split(".")[0]),
                "filename": match.group("file"),
                "label_text": label,
                "class": "healthy",
                "fault_diameter_in": "none",
                "load_hp": load,
                "rpm": rpm_by_load[load],
                "fault_location": "none",
                "source_url": match.group("href"),
            }
        )
    return rows


def parse_fault_label(label: str) -> tuple[str, str, int, str]:
    clean = html.unescape(label).strip()
    load = int(clean.split("_")[-1])
    head = clean.rsplit("_", 1)[0]
    if head.startswith("IR"):
        return "IR", "0." + head[2:5], load, "inner_race"
    if head.startswith("B"):
        return "B", "0." + head[1:4], load, "ball"
    if head.startswith("OR"):
        diameter = "0." + head[2:5]
        loc = "outer_race_" + head.split("@", 1)[1]
        return "OR", diameter, load, loc
    raise ValueError(label)


def parse_fault_page(path: Path) -> list[dict[str, object]]:
    text = path.read_text(errors="ignore")
    rpm_by_load = {0: 1797, 1: 1772, 2: 1750, 3: 1730}
    rows = []
    for match in LINK_RE.finditer(text):
        label = html.unescape(match.group("label")).strip()
        if not (label.startswith("IR") or label.startswith("B") or label.startswith("OR")):
            continue
        cls, diameter, load, location = parse_fault_label(label)
        rows.append(
            {
                "protocol": "cwru_de12k_full",
                "file_id": int(match.group("file").split(".")[0]),
                "filename": match.group("file"),
                "label_text": label,
                "class": cls,
                "fault_diameter_in": diameter,
                "load_hp": load,
                "rpm": rpm_by_load[load],
                "fault_location": location,
                "source_url": match.group("href"),
            }
        )
    return rows


def write_manifest(rows: list[dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = sorted(rows, key=lambda r: (int(r["load_hp"]), str(r["class"]), str(r["fault_diameter_in"]), str(r["fault_location"]), int(r["file_id"])))
    with path.open("w", newline="") as fh:
        fieldnames = list(rows[0].keys())
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(ANALYSIS / "cwru_de12k_full_manifest_2026-07-05.csv"))
    args = parser.parse_args()
    normal = parse_normal_page(META / "normal_baseline_data.html")
    faults = parse_fault_page(META / "12k_drive_end_fault_data.html")
    rows = normal + faults
    if len(rows) < 20:
        raise RuntimeError(f"parsed too few CWRU links: {len(rows)}")
    out = Path(args.out)
    write_manifest(rows, out)
    by_class = {}
    for row in rows:
        by_class[row["class"]] = by_class.get(row["class"], 0) + 1
    print(f"wrote {out}")
    print(f"rows={len(rows)} by_class={by_class}")


if __name__ == "__main__":
    main()
