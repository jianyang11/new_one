"""Audit the NASA/IMS bearing archive without bulk extraction.

The IMS bearing data are run-to-failure experiments. The readme gives failure
descriptions at the end of each experiment, but it does not assign per-file
fault-onset labels. This script therefore creates a reproducible archive/file
manifest and a dataset-readiness report; it intentionally does not invent
classification labels from arbitrary early/late thresholds.
"""

from __future__ import annotations

import argparse
import csv
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "ims" / "raw"
ANALYSIS = ROOT / "analysis"
REPORTS = ROOT / "reports"


@dataclass(frozen=True)
class SetSpec:
    set_no: int
    archive: str
    directory: str
    recording_duration: str
    expected_files: int
    channels: int
    channel_arrangement: str
    interval: str
    terminal_failure_description: str
    directly_usable_for_multiclass_fault_classification: str


SPECS = {
    1: SetSpec(
        set_no=1,
        archive="1st_test.rar",
        directory="1st_test",
        recording_duration="2003-10-22 12:06:24 to 2003-11-25 23:39:56",
        expected_files=2156,
        channels=8,
        channel_arrangement="Bearing 1 Ch1-2; Bearing 2 Ch3-4; Bearing 3 Ch5-6; Bearing 4 Ch7-8",
        interval="every 10 min except first 43 files every 5 min",
        terminal_failure_description="inner-race defect in bearing 3 and roller-element defect in bearing 4 at experiment end",
        directly_usable_for_multiclass_fault_classification="no_per_file_fault_onset_labels",
    ),
    2: SetSpec(
        set_no=2,
        archive="2nd_test.rar",
        directory="2nd_test",
        recording_duration="2004-02-12 10:32:39 to 2004-02-19 06:22:39",
        expected_files=984,
        channels=4,
        channel_arrangement="Bearing 1 Ch1; Bearing 2 Ch2; Bearing 3 Ch3; Bearing 4 Ch4",
        interval="every 10 min",
        terminal_failure_description="outer-race failure in bearing 1 at experiment end",
        directly_usable_for_multiclass_fault_classification="no_per_file_fault_onset_labels",
    ),
    3: SetSpec(
        set_no=3,
        archive="3rd_test.rar",
        directory="3rd_test",
        recording_duration="2004-03-04 09:27:46 to 2004-04-04 19:01:57",
        expected_files=4448,
        channels=4,
        channel_arrangement="Bearing 1 Ch1; Bearing 2 Ch2; Bearing 3 Ch3; Bearing 4 Ch4",
        interval="every 10 min",
        terminal_failure_description="outer-race failure in bearing 3 at experiment end",
        directly_usable_for_multiclass_fault_classification="no_per_file_fault_onset_labels",
    ),
}

TIMESTAMP_RE = re.compile(r"^\d{4}\.\d{2}\.\d{2}\.\d{2}\.\d{2}\.\d{2}$")


def run_capture(cmd: list[str], timeout: int = 1800) -> str:
    proc = subprocess.run(cmd, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    return proc.stdout


def list_members(archive: Path) -> list[str]:
    text = run_capture(["bsdtar", "-tf", str(archive)])
    members: list[str] = []
    for line in text.splitlines():
        member = line.strip()
        if not member or member.endswith("/"):
            continue
        if "/" not in member:
            continue
        if not TIMESTAMP_RE.match(member.rsplit("/", 1)[-1]):
            continue
        members.append(member)
    return members


def list_sizes(archive: Path) -> dict[str, int]:
    text = run_capture(["bsdtar", "-tvf", str(archive)])
    sizes: dict[str, int] = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 9:
            continue
        try:
            size = int(parts[4])
        except ValueError:
            continue
        name = parts[-1]
        sizes[name] = size
    return sizes


def parse_member_timestamp(member: str, directory: str) -> datetime:
    stem = member.rsplit("/", 1)[-1]
    return datetime.strptime(stem, "%Y.%m.%d.%H.%M.%S")


def read_member_array(archive: Path, member: str) -> np.ndarray:
    proc = subprocess.run(
        ["bsdtar", "-xOf", str(archive), member],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=1800,
    )
    from io import BytesIO

    return np.loadtxt(BytesIO(proc.stdout), dtype=np.float32)


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise RuntimeError(f"no rows for {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def build_manifests() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    set_rows: list[dict[str, object]] = []
    file_rows: list[dict[str, object]] = []
    for set_no, spec in SPECS.items():
        archive = RAW / spec.archive
        if not archive.exists():
            raise FileNotFoundError(f"missing {archive}")
        members = sorted(list_members(archive), key=lambda m: parse_member_timestamp(m, spec.directory))
        sizes = list_sizes(archive)
        first = members[0]
        last = members[-1]
        first_arr = read_member_array(archive, first)
        last_arr = read_member_array(archive, last)
        if first_arr.shape != last_arr.shape:
            raise RuntimeError(f"shape mismatch in set {set_no}: {first_arr.shape} vs {last_arr.shape}")
        if first_arr.shape != (20480, spec.channels):
            raise RuntimeError(f"unexpected set {set_no} sample shape: {first_arr.shape}")
        for idx, member in enumerate(members):
            ts = parse_member_timestamp(member, spec.directory)
            file_rows.append(
                {
                    "dataset": "IMS",
                    "set_no": set_no,
                    "archive": spec.archive,
                    "member": member,
                    "timestamp": ts.isoformat(sep=" "),
                    "index_in_set": idx,
                    "size_bytes": sizes.get(member, ""),
                    "sampling_rate_hz": 20000,
                    "points_per_file": 20480,
                    "channels": spec.channels,
                    "terminal_failure_description": spec.terminal_failure_description,
                    "per_file_label_status": "unlabeled_progression_snapshot",
                }
            )
        set_rows.append(
            {
                "dataset": "IMS",
                "source_url": "https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/",
                "download_url": "https://phm-datasets.s3.amazonaws.com/NASA/4.+Bearings.zip",
                "set_no": set_no,
                "archive": spec.archive,
                "recording_duration_readme": spec.recording_duration,
                "files_listed": len(members),
                "expected_files_readme": spec.expected_files,
                "file_count_matches_readme": str(len(members) == spec.expected_files).lower(),
                "first_timestamp": parse_member_timestamp(first, spec.directory).isoformat(sep=" "),
                "last_timestamp": parse_member_timestamp(last, spec.directory).isoformat(sep=" "),
                "sampling_rate_hz": 20000,
                "points_per_file": 20480,
                "channels": spec.channels,
                "sample_shape": "x".join(str(v) for v in first_arr.shape),
                "channel_arrangement": spec.channel_arrangement,
                "recording_interval": spec.interval,
                "terminal_failure_description": spec.terminal_failure_description,
                "directly_usable_for_multiclass_fault_classification": spec.directly_usable_for_multiclass_fault_classification,
                "classification_claim_readiness": "blocked_without_explicit_run_to_failure_protocol",
            }
        )
    return set_rows, file_rows


def write_report(set_rows: list[dict[str, object]], file_rows: list[dict[str, object]], path: Path) -> None:
    rows_md = "\n".join(
        "| {set_no} | {archive} | {files_listed} | {sample_shape} | {terminal_failure_description} | {classification_claim_readiness} |".format(**row)
        for row in set_rows
    )
    total_files = len(file_rows)
    text = f"""# IMS Bearing Dataset Audit

Date: 2026-07-05

## Source

- Official repository page: `https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/`
- Official archive URL: `https://phm-datasets.s3.amazonaws.com/NASA/4.+Bearings.zip`
- Local archive: `data/ims/raw/4_Bearings.zip`
- Inner archives: `data/ims/raw/1st_test.rar`, `data/ims/raw/2nd_test.rar`, `data/ims/raw/3rd_test.rar`
- Readme: `data/ims/raw/Readme Document for IMS Bearing Data.pdf`

## Archive Manifest

| set | archive | files listed | sample shape | terminal failure description | classification readiness |
| --- | --- | ---: | --- | --- | --- |
{rows_md}

File-level manifest rows: {total_files}

## Interpretation

The IMS archive is available locally and the three RAR archives can be read by
`bsdtar` without bulk extraction. Each member file is a 1-second ASCII vibration
snapshot with 20,480 samples at 20 kHz. The readme gives terminal failure
descriptions for each run-to-failure experiment, but it does not provide
per-file fault-onset labels.

Therefore IMS should not be counted as a CWRU-style supervised multi-class fault
classification dataset unless a separate, explicitly justified run-to-failure
protocol is defined. Acceptable uses are dataset registry reporting,
unsupervised/temporal degradation analysis, or a separately labeled
early-vs-terminal protocol that is clearly described as such and not presented
as ground-truth fault onset.
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--set-out", default=str(ANALYSIS / "ims_bearing_set_manifest_2026-07-05.csv"))
    parser.add_argument("--file-out", default=str(ANALYSIS / "ims_bearing_file_manifest_2026-07-05.csv"))
    parser.add_argument("--report", default=str(REPORTS / "ims_bearing_audit_2026-07-05.md"))
    args = parser.parse_args()
    set_rows, file_rows = build_manifests()
    write_csv(Path(args.set_out), set_rows)
    write_csv(Path(args.file_out), file_rows)
    write_report(set_rows, file_rows, Path(args.report))
    print(f"wrote {args.set_out}")
    print(f"wrote {args.file_out}")
    print(f"wrote {args.report}")
    print(f"sets={len(set_rows)} files={len(file_rows)}")


if __name__ == "__main__":
    main()
