"""Freeze the current BREEZE experiment state.

This script is intentionally read-only for experiment inputs. It inspects the
current local files and writes a dated machine-readable JSON plus a Markdown
snapshot report under the project-level reports directory.
"""

from __future__ import annotations

import csv
import importlib
import json
import os
import platform
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


BREEZE_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BREEZE_DIR.parent
SRC_DIR = BREEZE_DIR / "src"
REPORT_DIR = PROJECT_DIR / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(SRC_DIR))

from config import (  # noqa: E402
    BEARINGS,
    CHANNELS,
    CLASSES,
    CONDITIONS,
    DECIM,
    FS,
    FS_RAW,
    HOP,
    MAIN_COND,
    PROC_DIR,
    RUNS_DIR,
    SPLIT,
    WIN,
    fault_freqs,
)
from data import load_file_split  # noqa: E402
from pools import build_pool  # noqa: E402
from verifier.verifier import BreezeVerifier  # noqa: E402


DATE_TAG = "2026-07-04"
RAW_JSON = REPORT_DIR / f"snapshot_raw_{DATE_TAG}.json"
MD_REPORT = REPORT_DIR / f"experiment_snapshot_{DATE_TAG}.md"


def scalar(v: Any) -> Any:
    if isinstance(v, np.generic):
        return v.item()
    if isinstance(v, np.ndarray):
        return v.tolist()
    return v


def safe_float(v: Any, ndigits: int = 6) -> float:
    return round(float(v), ndigits)


def file_size(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    total = 0
    for p in path.rglob("*"):
        if p.is_file():
            total += p.stat().st_size
    return total


def count_files(path: Path) -> dict[str, Any]:
    files = [p for p in path.rglob("*") if p.is_file()]
    return {
        "files": len(files),
        "bytes": sum(p.stat().st_size for p in files),
        "by_suffix": dict(sorted(Counter(p.suffix or "<none>" for p in files).items())),
    }


def environment_snapshot() -> dict[str, Any]:
    module_names = {
        "numpy": "numpy",
        "scipy": "scipy",
        "pandas": "pandas",
        "scikit-learn": "sklearn",
        "torch": "torch",
        "matplotlib": "matplotlib",
    }
    versions = {}
    for label, module_name in module_names.items():
        try:
            mod = importlib.import_module(module_name)
            versions[label] = getattr(mod, "__version__", "unknown")
        except Exception as exc:
            versions[label] = f"unavailable: {exc}"

    torch_info = {}
    try:
        import torch

        torch_info = {
            "cuda_available": bool(torch.cuda.is_available()),
            "mps_available": bool(getattr(torch.backends, "mps", None) and torch.backends.mps.is_available()),
        }
    except Exception as exc:
        torch_info = {"error": str(exc)}

    req_path = BREEZE_DIR / "requirements.txt"
    requirements = req_path.read_text().splitlines() if req_path.exists() else []
    return {
        "python_executable": sys.executable,
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "versions": versions,
        "torch_runtime": torch_info,
        "requirements_txt": requirements,
    }


def directory_snapshot() -> dict[str, Any]:
    immediate = {}
    for p in sorted(PROJECT_DIR.iterdir()):
        if p.name.startswith("."):
            continue
        if p.is_file():
            immediate[p.name] = {"type": "file", "bytes": p.stat().st_size}
        elif p.is_dir():
            immediate[p.name] = {"type": "dir", **count_files(p)}

    runs = {}
    if RUNS_DIR.exists():
        for p in sorted(RUNS_DIR.iterdir()):
            if p.is_file():
                runs[p.name] = {"type": "file", "bytes": p.stat().st_size}
            elif p.is_dir():
                suffix_counts = Counter(q.suffix or "<none>" for q in p.iterdir() if q.is_file())
                runs[p.name] = {
                    "type": "dir",
                    "files": sum(suffix_counts.values()),
                    "bytes": file_size(p),
                    "by_suffix": dict(sorted(suffix_counts.items())),
                }

    src_files = sorted(str(p.relative_to(BREEZE_DIR)) for p in (BREEZE_DIR / "src").rglob("*.py"))
    return {"project_immediate": immediate, "runs_immediate": runs, "src_py_files": src_files}


def class_from_bearing(bearing: str) -> str:
    for cls, bearings in BEARINGS.items():
        if bearing in bearings:
            return cls
    return "unknown"


def npz_keys_shapes(path: Path) -> dict[str, Any]:
    out = {}
    with np.load(path, allow_pickle=True) as d:
        for key in d.files:
            arr = d[key]
            if arr.shape == ():
                try:
                    out[key] = scalar(arr.item())
                except Exception:
                    out[key] = str(arr)
            else:
                out[key] = {"shape": list(arr.shape), "dtype": str(arr.dtype)}
    return out


def proc_snapshot() -> dict[str, Any]:
    pu_files = []
    mt_npz = []
    by_cond_cls = defaultdict(lambda: {"files": 0, "windows": 0, "bearings": []})

    for p in sorted(PROC_DIR.glob("*.npz")):
        if p.stem.startswith("mt_"):
            info = npz_keys_shapes(p)
            n = int(info["windows"]["shape"][0])
            mt_npz.append({"file": str(p.relative_to(PROJECT_DIR)), "windows": n, "shape": info["windows"]["shape"]})
            continue

        cond, bearing = p.stem.rsplit("_", 1)
        cls = class_from_bearing(bearing)
        with np.load(p, allow_pickle=True) as d:
            windows_shape = list(d["windows"].shape)
            file_ids = d["file_ids"] if "file_ids" in d.files else np.array([])
            unique_files = sorted(int(x) for x in np.unique(file_ids)) if len(file_ids) else []
        rec = {
            "file": str(p.relative_to(PROJECT_DIR)),
            "cond": cond,
            "bearing": bearing,
            "class": cls,
            "windows_shape": windows_shape,
            "n_windows": windows_shape[0],
            "n_channels": windows_shape[1] if len(windows_shape) > 1 else None,
            "window_length": windows_shape[2] if len(windows_shape) > 2 else None,
            "n_measurement_files": len(unique_files),
            "file_id_min": min(unique_files) if unique_files else None,
            "file_id_max": max(unique_files) if unique_files else None,
        }
        pu_files.append(rec)
        key = (cond, cls)
        by_cond_cls[key]["files"] += 1
        by_cond_cls[key]["windows"] += rec["n_windows"]
        by_cond_cls[key]["bearings"].append(bearing)

    by_cond_cls_out = {
        f"{cond}/{cls}": {
            "files": v["files"],
            "windows": v["windows"],
            "bearings": sorted(v["bearings"]),
        }
        for (cond, cls), v in sorted(by_cond_cls.items())
    }
    return {"pu_files": pu_files, "pu_by_cond_class": by_cond_cls_out, "mt_npz": mt_npz}


def split_snapshot() -> dict[str, Any]:
    out = {
        "main_cond": MAIN_COND,
        "protocol": "per bearing, file_ids before the 80% cut are train and the remainder are test",
        "by_split_class": {},
        "by_bearing": [],
        "leakage_checks": [],
    }
    split_class_counts = defaultdict(int)
    split_bearing_counts = {}

    for p in sorted(PROC_DIR.glob(f"{MAIN_COND}_*.npz")):
        cond, bearing = p.stem.rsplit("_", 1)
        cls = class_from_bearing(bearing)
        with np.load(p, allow_pickle=True) as d:
            file_ids = d["file_ids"]
            unique_ids = np.array(sorted(int(x) for x in np.unique(file_ids)))
            cut_idx = int(len(unique_ids) * 0.8)
            cut = int(unique_ids[cut_idx])
            train_mask = file_ids < cut
            test_mask = file_ids >= cut
            train_files = sorted(int(x) for x in np.unique(file_ids[train_mask]))
            test_files = sorted(int(x) for x in np.unique(file_ids[test_mask]))
            overlap = sorted(set(train_files) & set(test_files))
            rec = {
                "bearing": bearing,
                "class": cls,
                "n_files": len(unique_ids),
                "cut_file_id": cut,
                "train_windows": int(train_mask.sum()),
                "test_windows": int(test_mask.sum()),
                "train_files": train_files,
                "test_files": test_files,
                "file_overlap": overlap,
            }
        out["by_bearing"].append(rec)
        split_class_counts[("train", cls)] += rec["train_windows"]
        split_class_counts[("test", cls)] += rec["test_windows"]
        split_bearing_counts[(bearing, "train")] = rec["train_windows"]
        split_bearing_counts[(bearing, "test")] = rec["test_windows"]
        out["leakage_checks"].append({"bearing": bearing, "file_overlap_count": len(overlap)})

    for split in ("train", "test"):
        out["by_split_class"][split] = {
            cls: split_class_counts[(split, cls)] for cls in CLASSES
        }
        out["by_split_class"][split]["total"] = sum(out["by_split_class"][split].values())
    return out


def mt_data_snapshot() -> dict[str, Any]:
    mt_dir = BREEZE_DIR / "data_mt"
    csv_rows = []
    split_files = {"train": {"1", "2", "4", "5", "10"}, "test": {"7", "8"}, "unused": set()}
    for p in sorted(mt_dir.glob("*.csv")):
        stem = p.stem.replace("_pre", "")
        cls, fid = stem.split("_")
        split = "unused"
        if fid in split_files["train"]:
            split = "train"
        elif fid in split_files["test"]:
            split = "test"
        with p.open("r", newline="") as fh:
            reader = csv.reader(fh)
            header = next(reader)
            n_rows = sum(1 for _ in reader)
        csv_rows.append({
            "file": str(p.relative_to(PROJECT_DIR)),
            "class": cls,
            "file_id": fid,
            "split": split,
            "columns": header,
            "rows": n_rows,
            "bytes": p.stat().st_size,
        })
    return {"csv_files": csv_rows}


def verifier_snapshot() -> dict[str, Any]:
    out = {}
    for p in sorted(RUNS_DIR.glob("verifier_N09_M07_F10_file_c*.json")):
        data = json.loads(p.read_text())
        cls_info = {}
        for cls, cal in data.get("calib", {}).items():
            cls_info[cls] = {
                "band": cal.get("band"),
                "stat_channels": sorted(cal.get("stats", {}).keys()),
                "stat_keys": sorted(next(iter(cal.get("stats", {}).values())).keys()) if cal.get("stats") else [],
                "spec_bands": len(cal.get("spec", [])),
                "energy_keys": sorted(cal.get("energy", {}).keys()),
                "env_prom_min": cal.get("env_prom_min"),
                "env_prom_max": cal.get("env_prom_max"),
                "mcsa_min": cal.get("mcsa_min"),
                "alpha": cal.get("alpha"),
            }
        out[p.name] = {
            "coverage": data.get("coverage"),
            "gates": data.get("gates"),
            "cond": data.get("cond"),
            "freqs": {k: safe_float(v, 3) for k, v in data.get("freqs", {}).items()},
            "classes": cls_info,
        }

    pass_rates = {}
    for cov_name in ("c85", "c90", "c95"):
        p = RUNS_DIR / f"verifier_N09_M07_F10_file_{cov_name}.json"
        if not p.exists():
            continue
        verifier = BreezeVerifier.load(p)
        split_rates = {}
        for split in ("train", "test"):
            X, y, _ = load_file_split(split, MAIN_COND)
            feasible = 0
            by_class = {}
            fail_gates = Counter()
            for ci, cls in enumerate(CLASSES):
                idx = np.where(y == ci)[0]
                ok = 0
                for i in idx:
                    rep = verifier.verify(X[i], cls)
                    ok += int(rep["feasible"])
                    if not rep["feasible"]:
                        for gate, gr in rep.get("gates", {}).items():
                            if not gr.get("passed", True):
                                fail_gates[gate] += 1
                by_class[cls] = {"n": int(len(idx)), "pass": int(ok), "rate": safe_float(ok / max(len(idx), 1), 4)}
                feasible += ok
            split_rates[split] = {
                "n": int(len(X)),
                "pass": int(feasible),
                "rate": safe_float(feasible / max(len(X), 1), 4),
                "by_class": by_class,
                "fail_gates": dict(sorted(fail_gates.items())),
            }
        pass_rates[cov_name] = split_rates
    out["computed_pass_rates"] = pass_rates
    return out


def run_dir_snapshot(run_dir: Path) -> dict[str, Any]:
    recs = []
    for p in sorted(run_dir.glob("*.json")):
        d = json.loads(p.read_text())
        hist = d.get("history", [])
        feasible_rounds = [h.get("round") for h in hist if h.get("feasible")]
        gate_fails = Counter()
        for h in hist:
            gp = h.get("gate_pass", {})
            for gate, passed in gp.items():
                if not passed:
                    gate_fails[gate] += 1
        recs.append({
            "class": d.get("class"),
            "slot": d.get("slot"),
            "accepted": bool(d.get("accepted", False)),
            "rounds_used": d.get("rounds_used"),
            "history_len": len(hist),
            "first_feasible_round": min(feasible_rounds) if feasible_rounds else None,
            "gate_fails": dict(gate_fails),
        })
    npy_by_class = Counter()
    for p in run_dir.glob("*.npy"):
        npy_by_class[p.name.split("_")[0]] += 1
    by_class = {}
    for cls in CLASSES:
        cls_recs = [r for r in recs if r["class"] == cls]
        by_class[cls] = {
            "slots": len(cls_recs),
            "accepted_slots": sum(r["accepted"] for r in cls_recs),
            "acceptance": safe_float(sum(r["accepted"] for r in cls_recs) / max(len(cls_recs), 1), 4),
            "npy_files": npy_by_class.get(cls, 0),
            "rounds_used": dict(sorted(Counter(str(r["rounds_used"]) for r in cls_recs).items())),
            "first_feasible_round": dict(sorted(Counter(str(r["first_feasible_round"]) for r in cls_recs).items())),
        }
    all_fails = Counter()
    for r in recs:
        all_fails.update(r["gate_fails"])
    return {
        "path": str(run_dir.relative_to(PROJECT_DIR)),
        "json_files": len(recs),
        "npy_files": sum(npy_by_class.values()),
        "accepted_slots": sum(r["accepted"] for r in recs),
        "acceptance": safe_float(sum(r["accepted"] for r in recs) / max(len(recs), 1), 4),
        "by_class": by_class,
        "gate_fail_counts_across_history": dict(sorted(all_fails.items())),
    }


def pool_npz_snapshot(path: Path) -> dict[str, Any]:
    info = {"file": str(path.relative_to(PROJECT_DIR)), "bytes": path.stat().st_size, "keys": {}}
    with np.load(path, allow_pickle=True) as d:
        for key in d.files:
            arr = d[key]
            entry = {"shape": list(arr.shape), "dtype": str(arr.dtype)}
            if key.lower() in ("y", "labels", "label") and arr.ndim == 1:
                entry["counts"] = {str(k): int(v) for k, v in sorted(Counter(arr.tolist()).items())}
                if set(arr.tolist()).issubset(set(range(len(CLASSES)))):
                    entry["class_counts"] = {
                        CLASSES[int(k)]: int(v) for k, v in sorted(Counter(arr.tolist()).items())
                    }
            info["keys"][key] = entry
    return info


def generated_pool_snapshot() -> dict[str, Any]:
    run_dirs = {}
    for name in ("pool_physics_file_k3", "pool_basic_file_k0", "pool_physics_k3_v1", "pool_basic_k0", "pilot_mimo_k2", "pilot_mimo_k2b", "pool_raw_k2"):
        p = RUNS_DIR / name
        if p.exists() and p.is_dir():
            run_dirs[name] = run_dir_snapshot(p)
    npz_files = {}
    for name in ("pool_breeze_k3.npz", "breeze_ref_pool_v8.npz", "vae_fullcorpus_pool.npz", "gan_fullcorpus_pool.npz"):
        p = RUNS_DIR / name
        if p.exists():
            npz_files[name] = pool_npz_snapshot(p)

    assembled = {}
    configs = {
        "open_loop_basic": (RUNS_DIR / "pool_basic_file_k0", "open_loop_basic", 3),
        "open_loop_phys": (RUNS_DIR / "pool_physics_file_k3", "open_loop_phys", 3),
        "stats_only": (RUNS_DIR / "pool_physics_file_k3", "stats_only", 3),
        "envelope_only": (RUNS_DIR / "pool_physics_file_k3", "envelope_only", 3),
        "breeze_k0": (RUNS_DIR / "pool_physics_file_k3", "breeze", 0),
        "breeze_k1": (RUNS_DIR / "pool_physics_file_k3", "breeze", 1),
        "breeze_k2": (RUNS_DIR / "pool_physics_file_k3", "breeze", 2),
        "breeze_k3": (RUNS_DIR / "pool_physics_file_k3", "breeze", 3),
    }
    for name, args in configs.items():
        X, y = build_pool(args[0], args[1], k=args[2])
        assembled[name] = {
            "shape": list(X.shape),
            "class_counts": {CLASSES[int(k)]: int(v) for k, v in sorted(Counter(y.tolist()).items())},
        }
    return {"run_dirs": run_dirs, "npz_files": npz_files, "assembled_pools": assembled}


def results_snapshot() -> dict[str, Any]:
    out = {}
    results_dir = BREEZE_DIR / "results"
    for p in sorted(results_dir.glob("*.csv")):
        df = pd.read_csv(p)
        out[p.name] = {"rows": int(len(df)), "columns": list(df.columns), "bytes": p.stat().st_size}

    ds = results_dir / "downstream_file.csv"
    if ds.exists():
        df = pd.read_csv(ds)
        grouped = []
        for (baseline, n_real), g in df.groupby(["baseline", "n_real"]):
            grouped.append({
                "baseline": baseline,
                "n_real": int(n_real),
                "rows": int(len(g)),
                "seeds": sorted(int(x) for x in g["seed"].unique()),
                "mean_acc": safe_float(g["acc"].mean(), 4),
                "std_acc": safe_float(g["acc"].std(ddof=1), 4),
                "mean_f1": safe_float(g["f1"].mean(), 4),
                "std_f1": safe_float(g["f1"].std(ddof=1), 4),
            })
        baselines = sorted(df["baseline"].unique())
        n_reals = sorted(int(x) for x in df["n_real"].unique())
        seeds = sorted(int(x) for x in df["seed"].unique())
        missing = []
        for baseline in baselines:
            for n_real in n_reals:
                for seed in seeds:
                    m = (df["baseline"] == baseline) & (df["n_real"] == n_real) & (df["seed"] == seed)
                    if not m.any():
                        missing.append({"baseline": baseline, "n_real": n_real, "seed": seed})
        out["downstream_file_summary"] = {
            "baselines": baselines,
            "n_real": n_reals,
            "seeds": seeds,
            "expected_rows_if_full": len(baselines) * len(n_reals) * len(seeds),
            "missing": missing,
            "grouped": grouped,
        }

    for name in ("acceptance.csv", "pool_metrics.csv", "significance.csv"):
        p = results_dir / name
        if p.exists():
            out[name]["preview"] = pd.read_csv(p).head(20).to_dict(orient="records")
    return out


def paper_snapshot() -> dict[str, Any]:
    paper_dir = BREEZE_DIR / "paper"
    figs_dir = paper_dir / "figs"
    figs = []
    for p in sorted(figs_dir.glob("*")):
        if p.is_file():
            figs.append({"file": str(p.relative_to(PROJECT_DIR)), "bytes": p.stat().st_size})
    tex = paper_dir / "main.tex"
    tex_info = {}
    if tex.exists():
        text = tex.read_text(errors="replace")
        tex_info = {
            "file": str(tex.relative_to(PROJECT_DIR)),
            "bytes": tex.stat().st_size,
            "lines": text.count("\n") + 1,
            "section_count": text.count("\\section"),
            "has_todo_marker": "TODO" in text or "todo" in text,
        }
    return {"main_tex": tex_info, "figures": figs, "main_pdf_exists": (paper_dir / "main.pdf").exists()}


def legacy_log_snapshot() -> dict[str, str]:
    logs = {}
    for name in ("recal_file.log", "block4_llm_pool_check.log", "v8_8seeds.log"):
        path = RUNS_DIR / name
        if path.exists():
            logs[name] = path.read_text(errors="replace").strip()
    return logs


def build_snapshot() -> dict[str, Any]:
    rpm = CONDITIONS[MAIN_COND][0]
    return {
        "date": DATE_TAG,
        "project_dir": str(PROJECT_DIR),
        "breeze_dir": str(BREEZE_DIR),
        "environment": environment_snapshot(),
        "config": {
            "FS_RAW": FS_RAW,
            "DECIM": DECIM,
            "FS": FS,
            "WIN": WIN,
            "HOP": HOP,
            "MAIN_COND": MAIN_COND,
            "CONDITIONS": CONDITIONS,
            "CLASSES": CLASSES,
            "BEARINGS": BEARINGS,
            "SPLIT": SPLIT,
            "CHANNELS": CHANNELS,
            "fault_freqs_main": {k: safe_float(v, 3) for k, v in fault_freqs(rpm / 60.0).items()},
        },
        "directories": directory_snapshot(),
        "proc": proc_snapshot(),
        "file_split": split_snapshot(),
        "machine_tool": mt_data_snapshot(),
        "verifier": verifier_snapshot(),
        "generated_pools": generated_pool_snapshot(),
        "results": results_snapshot(),
        "paper": paper_snapshot(),
        "legacy_logs": legacy_log_snapshot(),
    }


def md_table(rows: list[list[Any]], headers: list[str]) -> str:
    def cell(v: Any) -> str:
        return str(v).replace("\n", " ")

    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        out.append("| " + " | ".join(cell(v) for v in row) + " |")
    return "\n".join(out)


def render_markdown(s: dict[str, Any]) -> str:
    lines = [
        "# BREEZE 实验快照冻结报告",
        "",
        f"冻结日期：{s['date']}",
        "",
        f"项目根目录：`{s['project_dir']}`",
        "",
        "## 1. 环境",
        "",
        f"- Python：`{s['environment']['python_executable']}` (`{s['environment']['python_version']}`)",
        f"- Platform：`{s['environment']['platform']}`",
        f"- Torch runtime：CUDA={s['environment']['torch_runtime'].get('cuda_available')}, MPS={s['environment']['torch_runtime'].get('mps_available')}",
        "",
        md_table(
            [[k, v] for k, v in s["environment"]["versions"].items()],
            ["package", "version"],
        ),
        "",
        "## 2. 数据协议与通道",
        "",
        f"- 主工况：`{s['config']['MAIN_COND']}`，转速 `{s['config']['CONDITIONS'][s['config']['MAIN_COND']][0]}` rpm。",
        f"- 采样：原始 `{s['config']['FS_RAW']}` Hz，降采样因子 `{s['config']['DECIM']}`，当前 `{s['config']['FS']}` Hz。",
        f"- 窗口：`{s['config']['WIN']}` 点，hop `{s['config']['HOP']}`。",
        f"- PU 当前保留通道：`{', '.join(s['config']['CHANNELS'])}`。注意：代码内 X/Y/Z 短名分别是振动、相电流1、相电流2，不是三轴振动。",
        f"- 6203 主工况故障频率：{s['config']['fault_freqs_main']}",
        "",
        "### 2.1 PU 预处理文件",
        "",
        md_table(
            [[k, v["files"], v["windows"], ", ".join(v["bearings"])] for k, v in s["proc"]["pu_by_cond_class"].items()],
            ["condition/class", "npz files", "windows", "bearings"],
        ),
        "",
        "### 2.2 主文件划分",
        "",
        md_table(
            [[split, cls, s["file_split"]["by_split_class"][split][cls]] for split in ("train", "test") for cls in CLASSES]
            + [[split, "total", s["file_split"]["by_split_class"][split]["total"]] for split in ("train", "test")],
            ["split", "class", "windows"],
        ),
        "",
        f"- 文件划分泄漏检查：所有轴承 train/test file_id overlap 计数为 `{[x['file_overlap_count'] for x in s['file_split']['leakage_checks']]}`。",
        "",
        "### 2.3 实验室自建机床数据",
        "",
    ]
    mt_counts = defaultdict(int)
    mt_rows = defaultdict(int)
    mt_columns = Counter()
    for r in s["machine_tool"]["csv_files"]:
        mt_counts[(r["split"], r["class"])] += 1
        mt_rows[(r["split"], r["class"])] += r["rows"]
        mt_columns[tuple(r["columns"])] += 1
    lines.extend([
        md_table(
            [[split, cls, mt_counts[(split, cls)], mt_rows[(split, cls)]] for split in ("train", "test", "unused") for cls in ("1", "2", "3") if mt_counts[(split, cls)]],
            ["split", "class", "csv files", "raw rows"],
        ),
        "",
        f"- CSV 表头集合：`{dict((str(k), v) for k, v in mt_columns.items())}`。",
        "",
        md_table(
            [[Path(r["file"]).name, r["windows"], r["shape"]] for r in s["proc"]["mt_npz"]],
            ["npz", "windows", "shape"],
        ),
        "",
        "- 机床数据是三轴振动 + 单路电流，不能直接套用 PU 的 1 振动 + 2 电流 verifier schema。",
        "",
        "## 3. 物理验证器",
        "",
    ])

    verifier_rows = []
    for name, v in s["verifier"].items():
        if name == "computed_pass_rates":
            continue
        verifier_rows.append([name, v["coverage"], v["gates"], v["freqs"]])
    lines.extend([
        md_table(verifier_rows, ["file", "coverage", "gates", "freqs"]),
        "",
    ])
    pass_rows = []
    for cov, by_split in s["verifier"]["computed_pass_rates"].items():
        for split, r in by_split.items():
            pass_rows.append([cov, split, r["pass"], r["n"], r["rate"], r["fail_gates"]])
    lines.extend([
        md_table(pass_rows, ["coverage", "split", "pass", "n", "rate", "fail gates"]),
        "",
        "复算说明：上表由 `breeze/scripts/freeze_snapshot.py` 逐窗口加载当前 verifier 文件和当前 `proc` 数据全量复算，作为本冻结快照的准确信息。",
        "",
    ])
    if s.get("legacy_logs", {}).get("recal_file.log"):
        lines.extend([
            "`runs/recal_file.log` 中保存的旧复核记录如下，和当前复算有轻微差异；论文写作以本报告和 raw JSON 的当前复算值为准，除非后续查明并记录代码版本差异。",
            "",
            "```text",
            s["legacy_logs"]["recal_file.log"],
            "```",
            "",
        ])
    band_rows = []
    c90 = s["verifier"].get("verifier_N09_M07_F10_file_c90.json", {})
    for cls, info in c90.get("classes", {}).items():
        band_rows.append([cls, info.get("band"), info.get("env_prom_min"), info.get("env_prom_max"), info.get("mcsa_min")])
    lines.extend([
        "主协议为 `_file_c90`。对应 class band 与阈值摘要：",
        "",
        md_table(band_rows, ["class", "band Hz", "env_prom_min", "env_prom_max", "mcsa_min"]),
        "",
        "高风险项：固定硬频带 spectrum gate、单一 SK 最大共振带、单相 MCSA hard gate、9 维宏观统计 diversity embedding。",
        "",
        "## 4. 生成池",
        "",
    ])

    run_rows = []
    for name, info in s["generated_pools"]["run_dirs"].items():
        run_rows.append([name, info["json_files"], info["npy_files"], info["accepted_slots"], info["acceptance"]])
    lines.extend([
        md_table(run_rows, ["run dir", "json", "npy", "accepted slots", "acceptance"]),
        "",
        "从正式 run 组装的论文候选池：",
        "",
        md_table(
            [[name, info["shape"], info["class_counts"]] for name, info in s["generated_pools"]["assembled_pools"].items()],
            ["pool", "shape", "class counts"],
        ),
        "",
        "NPZ 池文件：",
        "",
        md_table(
            [[name, info["keys"]] for name, info in s["generated_pools"]["npz_files"].items()],
            ["npz", "keys/shapes"],
        ),
        "",
        "正式可用：`pool_physics_file_k3`、`pool_basic_file_k0` 及由二者组装的 open-loop/stats/envelope/BREEZE pools。`pool_physics_k3_v1` 属旧架构池，当前不应混入主论文结果。",
        "",
        "## 5. 结果表",
        "",
    ])

    result_file_rows = []
    for name, info in s["results"].items():
        if isinstance(info, dict) and "rows" in info:
            result_file_rows.append([name, info["rows"], info["columns"]])
    lines.extend([
        md_table(result_file_rows, ["csv", "rows", "columns"]),
        "",
    ])

    ds = s["results"].get("downstream_file_summary", {})
    if ds:
        lines.extend([
            f"- `downstream_file.csv` baselines: `{ds['baselines']}`",
            f"- n_real: `{ds['n_real']}`; seeds: `{ds['seeds']}`",
            f"- expected rows: `{ds['expected_rows_if_full']}`; missing: `{len(ds['missing'])}`",
            "",
            md_table(
                [[r["baseline"], r["n_real"], r["rows"], r["mean_acc"], r["std_acc"], r["mean_f1"], r["std_f1"]] for r in ds["grouped"]],
                ["baseline", "n_real", "rows", "mean acc", "std acc", "mean macro-F1", "std macro-F1"],
            ),
            "",
            "重要写作约束：当前完整主表里 BREEZE 相对 real-only 有稳定增益，但不是所有 n_real 下的全表最高；不能写成“最高准确率”除非后续实验支持。",
            "",
        ])

    acc = s["results"].get("acceptance.csv", {}).get("preview", [])
    if acc:
        lines.extend([
            "Acceptance/cost 表：",
            "",
            md_table([[r["K"], r["acceptance"], r["mean_llm_calls"], r["n_slots"]] for r in acc], ["K", "acceptance", "mean LLM calls", "slots"]),
            "",
        ])

    sig = s["results"].get("significance.csv", {}).get("preview", [])
    if sig:
        lines.extend([
            "显著性表预览（breeze_k3 对其他 baseline）：",
            "",
            md_table([[r["n_real"], r["baseline"], r["delta"], r["p_wilcoxon"]] for r in sig[:12]], ["n_real", "baseline", "delta acc", "p_wilcoxon"]),
            "",
        ])

    lines.extend([
        "## 6. 图表与论文草稿",
        "",
        f"- `paper/main.tex`：{s['paper']['main_tex']}",
        f"- `paper/main.pdf` exists：{s['paper']['main_pdf_exists']}",
        "",
        md_table([[r["file"], r["bytes"]] for r in s["paper"]["figures"]], ["figure", "bytes"]),
        "",
        "## 7. 已完成、未完成与禁止写法",
        "",
        "已完成可冻结：",
        "- PU 主工况文件划分数据、c85/c90/c95 verifier、正式 LLM 闭环池、basic open-loop 池、Block 4 主表、Block 5 acceptance/pool/significance 表、主要 PDF 图。",
        "- 本次快照过程中已重新运行 `figures.py` 和 `fig_framework.py`，五个 PDF 图均可由 `pdfinfo` 读取。",
        "",
        "未完成或需复核：",
        "- BREEZE-v2 高风险 gate 改进与离线重筛。",
        "- 自建机床数据跨数据集实验。",
        "- `downstream_file.csv` 未包含 per-class F1，若论文需要 IR 类 F1，必须补跑或修改训练输出。",
        "- 四张数据图已由 `figures.py` 基于当前 CSV/NPZ 重跑；`framework.pdf` 是框架示意图，由 `fig_framework.py` 重跑，不依赖结果表。",
        "- `paper/main.tex` 仍需按最终数据完整写作和逐数字溯源。",
        "",
        "禁止写法：",
        "- 禁止写 PU 原始数据只有 3 通道；只能写本项目选取并保留 3 路。",
        "- 禁止把代码内部 X/Y/Z 写成 PU 三轴振动。",
        "- 禁止写 BREEZE 在完整主表中全基线最高；当前数据不支持。",
        "- 禁止把 `pool_physics_k3_v1` 旧池混入正式结论。",
        "- 禁止把 verifier 阈值描述成用 test set 调过；当前协议是 train-only 校准。",
        "",
        f"机器可读原始统计：`{RAW_JSON.relative_to(PROJECT_DIR)}`",
    ])
    return "\n".join(lines) + "\n"


def main() -> None:
    snapshot = build_snapshot()
    RAW_JSON.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False))
    MD_REPORT.write_text(render_markdown(snapshot))
    print(f"Wrote {RAW_JSON}")
    print(f"Wrote {MD_REPORT}")


if __name__ == "__main__":
    main()
