"""Freeze Phase-A v2 artifacts into a checksumed read-only snapshot.

This script does not modify the original Phase-A v2 files. It copies the
registered artifacts into a dated freeze directory, writes a SHA256 manifest,
and makes the copied files read-only. If rerun, it verifies the existing
snapshot instead of overwriting it.
"""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BREEZE = ROOT / "breeze"
FREEZE_DIR = BREEZE / "results" / "phaseA_v2_frozen_2026-07-06"

ARTIFACTS = [
    "breeze/results/phaseA_v2_downstream_cnn.csv",
    "breeze/results/phaseA_v2_wilcoxon.csv",
    "breeze/results/phaseA_v2_gate_report.md",
    "breeze/results/phaseA_v2_gate_criteria.csv",
    "breeze/results/phaseA_v2_downstream_summary.csv",
    "breeze/results/phaseA_v2_per_class_summary.csv",
    "breeze/results/phaseA_v2_failure_gate_summary.csv",
    "breeze/results/phaseA_v2_budget_summary.csv",
    "breeze/results/phaseA_v2_balanced_pool_summary.csv",
    "breeze/runs/phaseA_v2_balanced/phaseA_v2_rule_B150.npz",
    "breeze/runs/phaseA_v2_balanced/phaseA_v2_rule_B150_manifest.csv",
    "breeze/runs/phaseA_v2_balanced/phaseA_v2_llm_k3_B150.npz",
    "breeze/runs/phaseA_v2_balanced/phaseA_v2_llm_k3_B150_manifest.csv",
    "breeze/runs/phaseA_v2_balanced/phaseA_v2_random_open_loop_B150.npz",
    "breeze/runs/phaseA_v2_balanced/phaseA_v2_random_open_loop_B150_manifest.csv",
    "breeze/runs/recipe_ablation_rule_v2_full/summary.json",
    "breeze/runs/recipe_ablation_rule_v2_full/slot_summary.csv",
    "breeze/runs/recipe_ablation_random_v2_full/summary.json",
    "breeze/runs/recipe_ablation_random_v2_full/slot_summary.csv",
    "breeze/runs/rescreen_v2_full/summary.json",
    "breeze/runs/rescreen_v2_full/slot_summary.csv",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    FREEZE_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    missing = []
    for rel in ARTIFACTS:
        src = ROOT / rel
        if not src.exists():
            missing.append(rel)
            continue
        dst = FREEZE_DIR / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        src_hash = sha256(src)
        if dst.exists():
            dst_hash = sha256(dst)
            if dst_hash != src_hash:
                raise RuntimeError(
                    f"frozen copy differs from source for {rel}: "
                    f"frozen={dst_hash} source={src_hash}"
                )
        else:
            shutil.copy2(src, dst)
            dst.chmod(0o444)
        stat = src.stat()
        rows.append(
            {
                "relative_path": rel,
                "sha256": src_hash,
                "size_bytes": stat.st_size,
                "source_mtime_utc": datetime.fromtimestamp(
                    stat.st_mtime, timezone.utc
                ).isoformat(),
                "frozen_copy": str(dst.relative_to(ROOT)),
            }
        )
    if missing:
        raise FileNotFoundError("missing Phase-A v2 artifacts: " + ", ".join(missing))

    manifest = FREEZE_DIR / "manifest_sha256.csv"
    if not manifest.exists():
        with manifest.open("w", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        manifest.chmod(0o444)

    readme = FREEZE_DIR / "FREEZE_README.md"
    if not readme.exists():
        readme.write_text(
            "# Phase-A v2 Frozen Snapshot\n\n"
            "Created on 2026-07-06 after Phase-A v2 passed. These copied "
            "artifacts are read-only evidence snapshots. Do not overwrite "
            "the original Phase-A v2 pools, CSVs, reports, or manifests; any "
            "future rerun must use a new directory and a new filename prefix.\n\n"
            "Rule IR slot consumption to report in the manuscript: 400 IR "
            "slots were required to obtain 150 balanced kept items for rule, "
            "with 59 accepted slots in the IR supplementation pass "
            "(acceptance 14.75%). Source-specific slot consumption must be "
            "reported transparently.\n"
        )
        readme.chmod(0o444)

    summary = {
        "freeze_dir": str(FREEZE_DIR.relative_to(ROOT)),
        "artifact_count": len(rows),
        "manifest": str(manifest.relative_to(ROOT)),
    }
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
