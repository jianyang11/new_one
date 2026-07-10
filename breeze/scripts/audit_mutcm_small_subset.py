"""0-API audit for the MU-TCM face-milling small subset.

The audit is intentionally limited to dataset suitability checks:

- file tree and metadata discovery;
- condition x wear support;
- experiment-level label support for two binary schemes;
- metadata-only and signal-only baselines with leave-one-experiment-out splits.

No LLM calls, no synthetic generation, and no random-window split are used.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.io import loadmat, whosmat
from scipy.signal import welch
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_recall_fscore_support
from sklearn.model_selection import LeaveOneOut
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


FORCE_CHANNELS = ["Fx", "Fy", "Fz"]
VIBRATION_CHANNELS = ["Ax", "Ay", "Az"]
AE_CHANNELS = ["AE_F", "AE_RMS"]
CNC_CHANNELS = [
    "SREAL",
    "CV3_S",
    "CV3_X",
    "CV3_Y",
    "CV3_Z",
    "TV2_S",
    "TV2_X",
    "TV2_Y",
    "TV2_Z",
    "TV50",
    "TV51",
    "FREAL",
]
SIGNAL_CHANNELS = FORCE_CHANNELS + VIBRATION_CHANNELS + AE_CHANNELS + CNC_CHANNELS
METADATA_KEYS = [
    "WorkpieceMaterial",
    "ID",
    "Vc",
    "fz",
    "ap",
    "ae",
    "VB",
    "Insert",
    "Edge",
    "Machine",
    "Repetition",
    "Lubrication",
    "ToolDiameter",
    "ToolManufacturer",
    "ToolID",
    "ToolMaterial",
    "ToolReference",
    "Date",
]


def matlab_scalar(value: Any) -> Any:
    arr = np.asarray(value)
    if arr.shape == ():
        value = arr.item()
    elif arr.size == 1:
        value = arr.reshape(-1)[0].item()
    else:
        value = value
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def parse_filename(path: Path) -> dict[str, Any]:
    pattern = re.compile(
        r"Insert(?P<insert>\d+)Edge(?P<edge>\d+)_Vc(?P<Vc>[-+0-9.]+)_fz(?P<fz>[-+0-9.]+)_"
        r"ap(?P<ap>[-+0-9.]+)_VB(?P<VB>[-+0-9.]+)_Rep(?P<rep>\d+)\.mat$"
    )
    m = pattern.match(path.name)
    if not m:
        return {"filename_parse_ok": False}
    out: dict[str, Any] = {"filename_parse_ok": True}
    for key, value in m.groupdict().items():
        out[key] = int(value) if key in {"insert", "edge", "rep"} else float(value)
    return out


def vb_level(vb: float) -> float:
    return round(float(vb), 1)


def label_scheme_a(vb: float) -> str:
    level = vb_level(vb)
    if level in {0.0, 0.1}:
        return "healthy"
    if level in {0.2, 0.3}:
        return "worn"
    return "unlabeled"


def label_scheme_b(vb: float) -> str:
    if math.isclose(float(vb), 0.0, abs_tol=1e-12):
        return "healthy"
    if float(vb) >= 0.2:
        return "worn"
    return "unlabeled"


def signal_group(channel: str) -> str:
    if channel in FORCE_CHANNELS:
        return "force"
    if channel in VIBRATION_CHANNELS:
        return "vibration"
    if channel in AE_CHANNELS:
        return "ae"
    return "cnc"


def channel_sampling_rates(mat: dict[str, Any]) -> dict[str, float]:
    rates: dict[str, float] = {}
    time1 = np.asarray(mat.get("time1", []), dtype=float).reshape(-1)
    time2 = np.asarray(mat.get("time2", []), dtype=float).reshape(-1)
    ae_rate = float(1.0 / np.median(np.diff(time1[: min(len(time1), 10000)]))) if len(time1) > 2 else float("nan")
    fast_rate = float(1.0 / np.median(np.diff(time2[: min(len(time2), 10000)]))) if len(time2) > 2 else float("nan")
    for ch in AE_CHANNELS:
        rates[ch] = ae_rate
    for ch in FORCE_CHANNELS + VIBRATION_CHANNELS:
        rates[ch] = fast_rate
    for ch in CNC_CHANNELS:
        arr = np.asarray(mat.get(ch, []))
        rates[ch] = float(arr.size / 10.0) if arr.size else float("nan")
    return rates


def robust_stats(x: np.ndarray) -> dict[str, float]:
    x = np.asarray(x, dtype=np.float64).reshape(-1)
    x = x[np.isfinite(x)]
    if x.size == 0:
        return {
            "mean": np.nan,
            "std": np.nan,
            "rms": np.nan,
            "min": np.nan,
            "max": np.nan,
            "ptp": np.nan,
            "median": np.nan,
            "q25": np.nan,
            "q75": np.nan,
            "crest": np.nan,
            "skew": np.nan,
            "kurtosis": np.nan,
        }
    mean = float(np.mean(x))
    std = float(np.std(x) + 1e-12)
    rms = float(np.sqrt(np.mean(x * x)))
    centered = x - mean
    return {
        "mean": mean,
        "std": std,
        "rms": rms,
        "min": float(np.min(x)),
        "max": float(np.max(x)),
        "ptp": float(np.ptp(x)),
        "median": float(np.median(x)),
        "q25": float(np.quantile(x, 0.25)),
        "q75": float(np.quantile(x, 0.75)),
        "crest": float(np.max(np.abs(x)) / (rms + 1e-12)),
        "skew": float(np.mean(centered**3) / (std**3)),
        "kurtosis": float(np.mean(centered**4) / (std**4)),
    }


def spectral_stats(x: np.ndarray, fs_hz: float) -> dict[str, float]:
    x = np.asarray(x, dtype=np.float64).reshape(-1)
    x = x[np.isfinite(x)]
    if x.size < 16 or not np.isfinite(fs_hz) or fs_hz <= 0:
        return {
            "spec_total_power": np.nan,
            "spec_centroid_hz": np.nan,
            "spec_low_frac": np.nan,
            "spec_mid_frac": np.nan,
            "spec_high_frac": np.nan,
        }
    nperseg = int(min(8192, max(256, 2 ** int(np.floor(np.log2(min(x.size, 8192)))))))
    freqs, psd = welch(x, fs=fs_hz, nperseg=nperseg, noverlap=nperseg // 2)
    total = float(np.sum(psd) + 1e-18)
    nyq = fs_hz / 2.0
    bands = {
        "low": (0.0, 0.1 * nyq),
        "mid": (0.1 * nyq, 0.4 * nyq),
        "high": (0.4 * nyq, nyq + 1e-9),
    }
    out = {
        "spec_total_power": total,
        "spec_centroid_hz": float(np.sum(freqs * psd) / total),
    }
    for name, (lo, hi) in bands.items():
        mask = (freqs >= lo) & (freqs < hi)
        out[f"spec_{name}_frac"] = float(np.sum(psd[mask]) / total)
    return out


def extract_signal_features(mat_path: Path, metadata: dict[str, Any]) -> dict[str, float]:
    mat = loadmat(mat_path, squeeze_me=True, struct_as_record=False, variable_names=SIGNAL_CHANNELS + ["time1", "time2"])
    rates = channel_sampling_rates(mat)
    features: dict[str, float] = {}
    for ch in SIGNAL_CHANNELS:
        if ch not in mat:
            continue
        x = np.asarray(mat[ch]).reshape(-1)
        prefix = f"{signal_group(ch)}__{ch}"
        for key, value in robust_stats(x).items():
            features[f"{prefix}__{key}"] = value
        for key, value in spectral_stats(x, rates.get(ch, float("nan"))).items():
            features[f"{prefix}__{key}"] = value
    return features


def tree_summary(root: Path, archive_path: Path) -> tuple[list[str], dict[str, int]]:
    lines = [f"# MU-TCM Small Subset File Tree", ""]
    lines.append(f"- Extracted directory: `{root}`")
    lines.append(f"- Archive path: `{archive_path}`")
    lines.append(f"- Archive present: `{archive_path.exists()}`")
    lines.append("- Archive listing: not read; local `7z/7zz` and `py7zr` are unavailable, extracted directory is present and used.")
    lines.append("")
    lines.append("## Tree")
    lines.append("")
    counts: Counter[str] = Counter()
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if path.is_dir():
            lines.append(f"- `{rel}/`")
        else:
            suffix = path.suffix.lower() or "<no_suffix>"
            counts[suffix] += 1
            size = path.stat().st_size
            lines.append(f"- `{rel}` ({size} bytes)")
    return lines, dict(counts)


def load_metadata(mat_path: Path) -> dict[str, Any]:
    mat = loadmat(
        mat_path,
        squeeze_me=True,
        struct_as_record=False,
        variable_names=METADATA_KEYS + ["time1", "time2"] + CNC_CHANNELS,
    )
    parsed = parse_filename(mat_path)
    out = {
        "experiment_id": mat_path.stem,
        "signal_synced_path": str(mat_path),
        "signal_unsynced_path": "",
        "filename_parse_ok": parsed.get("filename_parse_ok", False),
    }
    for key in METADATA_KEYS:
        if key in mat:
            out[key] = matlab_scalar(mat[key])
    out["material"] = str(out.get("WorkpieceMaterial", ""))
    out["cutting_speed"] = float(out.get("Vc", parsed.get("Vc", np.nan)))
    out["feed_rate"] = float(out.get("fz", parsed.get("fz", np.nan)))
    out["depth_of_cut"] = float(out.get("ap", parsed.get("ap", np.nan)))
    out["radial_depth_ae"] = float(out.get("ae", np.nan))
    out["VB"] = float(out.get("VB", parsed.get("VB", np.nan)))
    out["VB_level"] = vb_level(out["VB"])
    out["label_scheme_A"] = label_scheme_a(out["VB"])
    out["label_scheme_B"] = label_scheme_b(out["VB"])
    out["insert"] = int(out.get("Insert", parsed.get("insert", -1)))
    out["edge"] = int(out.get("Edge", parsed.get("edge", -1)))
    out["repetition"] = str(out.get("Repetition", parsed.get("rep", "")))
    rates = channel_sampling_rates(mat)
    cnc_rates = [rates.get(ch, np.nan) for ch in CNC_CHANNELS]
    cnc_median = float(np.nanmedian(cnc_rates)) if np.any(np.isfinite(cnc_rates)) else float("nan")
    out["sampling_rate_json"] = json.dumps(
        {
            "ae_hz": rates.get("AE_F"),
            "force_vibration_hz": rates.get("Fx"),
            "cnc_estimated_hz_median": cnc_median,
        },
        sort_keys=True,
    )
    out["sampling_rate_note"] = "AE from time1; force/vibration from time2; CNC estimated as channel length over 10 s"
    return out


def find_vb_images(root: Path, vb: float, insert: int, edge: int) -> list[str]:
    folder = root / "VB_images" / f"Insert{insert}_Edge{edge}"
    if not folder.exists():
        return []
    token = f"VB{vb:.3f}"
    loose = f"VB{vb:g}"
    matches = [p for p in sorted(folder.glob("*.jpg")) if token in p.name or loose in p.name]
    return [str(p) for p in matches]


def build_metadata(root: Path) -> pd.DataFrame:
    synced = root / "signals_synced"
    unsynced = root / "signals_unsynced"
    rows = []
    for mat_path in sorted(synced.glob("*.mat")):
        row = load_metadata(mat_path)
        unsynced_path = unsynced / mat_path.name
        row["signal_unsynced_path"] = str(unsynced_path) if unsynced_path.exists() else ""
        row["VB_image_paths"] = json.dumps(find_vb_images(root, row["VB"], row["insert"], row["edge"]))
        row["sensor_file_paths"] = json.dumps(
            {
                "synced_mat": row["signal_synced_path"],
                "unsynced_mat": row["signal_unsynced_path"],
                "VB_images": json.loads(row["VB_image_paths"]),
            },
            sort_keys=True,
        )
        rows.append(row)
    return pd.DataFrame(rows)


def support_tables(meta: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    condition_cols = ["material", "cutting_speed", "feed_rate", "depth_of_cut"]
    rows = []
    for key, g in meta.groupby(condition_cols + ["VB_level"], dropna=False):
        key_dict = dict(zip(condition_cols + ["VB_level"], key, strict=False))
        rows.append(
            {
                **key_dict,
                "n_experiments": int(len(g)),
                "exact_VB_values": ";".join(f"{v:g}" for v in sorted(g["VB"].unique())),
                "experiment_ids": ";".join(sorted(g["experiment_id"])),
            }
        )
    support = pd.DataFrame(rows).sort_values(condition_cols + ["VB_level"])
    condition_rows = []
    for key, g in meta.groupby(condition_cols, dropna=False):
        levels = sorted(float(v) for v in g["VB_level"].unique())
        condition_rows.append(
            {
                **dict(zip(condition_cols, key, strict=False)),
                "n_experiments": int(len(g)),
                "n_VB_levels": len(levels),
                "VB_levels": ";".join(f"{v:.1f}" for v in levels),
                "exact_VB_values": ";".join(f"{v:g}" for v in sorted(g["VB"].unique())),
                "has_multiple_wear_levels": len(levels) >= 2,
                "scheme_A_labels": ";".join(sorted(set(g["label_scheme_A"]))),
                "scheme_B_labels": ";".join(sorted(set(g["label_scheme_B"]))),
            }
        )
    condition_summary = pd.DataFrame(condition_rows).sort_values(condition_cols)
    return support, condition_summary


def label_distribution(meta: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for scheme_col, scheme_name in [("label_scheme_A", "A"), ("label_scheme_B", "B")]:
        for label, g in meta.groupby(scheme_col, dropna=False):
            rows.append(
                {
                    "scheme": scheme_name,
                    "label": label,
                    "n_experiments": int(len(g)),
                    "experiment_ids": ";".join(sorted(g["experiment_id"])),
                    "VB_values": ";".join(f"{v:g}" for v in sorted(g["VB"].unique())),
                }
            )
    return pd.DataFrame(rows).sort_values(["scheme", "label"])


def make_feature_table(meta: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for row in meta.to_dict(orient="records"):
        feats = extract_signal_features(Path(row["signal_synced_path"]), row)
        rows.append({"experiment_id": row["experiment_id"], **feats})
    return pd.DataFrame(rows)


def metadata_feature_matrix(meta: pd.DataFrame) -> np.ndarray:
    enc = OneHotEncoder(sparse_output=False, handle_unknown="ignore")
    material = enc.fit_transform(meta[["material"]])
    numeric = meta[["cutting_speed", "feed_rate", "depth_of_cut"]].astype(float).to_numpy()
    return np.concatenate([material, numeric], axis=1).astype(np.float64)


def signal_feature_matrix(features: pd.DataFrame) -> np.ndarray:
    X = features.drop(columns=["experiment_id"]).replace([np.inf, -np.inf], np.nan)
    X = X.fillna(X.median(numeric_only=True)).fillna(0.0)
    return X.to_numpy(dtype=np.float64)


def evaluate_loeo(X: np.ndarray, labels: np.ndarray, experiment_ids: list[str]) -> dict[str, Any]:
    valid = labels != "unlabeled"
    X = X[valid]
    y_str = labels[valid]
    ids = [experiment_ids[i] for i, ok in enumerate(valid) if ok]
    classes = ["healthy", "worn"]
    counts = Counter(y_str)
    if len(X) < 4 or any(counts.get(c, 0) < 2 for c in classes):
        return {
            "status": "insufficient_label_support_for_leave_one_experiment_out",
            "n_labeled": int(len(X)),
            "label_counts_json": json.dumps(dict(counts), sort_keys=True),
            "acc": np.nan,
            "macro_f1": np.nan,
            "majority_acc": float(max(counts.values()) / len(X)) if len(X) else np.nan,
            "confusion_json": "",
            "per_class_f1_json": "",
            "predictions_json": "",
        }
    y = np.asarray([classes.index(v) for v in y_str], dtype=int)
    preds = np.full_like(y, -1)
    loo = LeaveOneOut()
    for train_idx, test_idx in loo.split(X):
        train_classes = set(int(v) for v in y[train_idx])
        if train_classes != {0, 1}:
            pred = Counter(y[train_idx]).most_common(1)[0][0]
        else:
            clf = make_pipeline(
                StandardScaler(),
                LogisticRegression(max_iter=2000, class_weight="balanced", random_state=0),
            )
            clf.fit(X[train_idx], y[train_idx])
            pred = int(clf.predict(X[test_idx])[0])
        preds[test_idx[0]] = pred
    acc = float(accuracy_score(y, preds))
    macro = float(f1_score(y, preds, average="macro", zero_division=0))
    _, _, f1, support = precision_recall_fscore_support(y, preds, labels=[0, 1], zero_division=0)
    cm = confusion_matrix(y, preds, labels=[0, 1]).tolist()
    predictions = [
        {"experiment_id": ids[i], "actual": classes[int(y[i])], "predicted": classes[int(preds[i])]} for i in range(len(y))
    ]
    return {
        "status": "ok",
        "n_labeled": int(len(X)),
        "label_counts_json": json.dumps(dict(counts), sort_keys=True),
        "acc": acc,
        "macro_f1": macro,
        "majority_acc": float(max(counts.values()) / len(X)),
        "confusion_json": json.dumps(cm),
        "per_class_f1_json": json.dumps({classes[i]: float(f1[i]) for i in range(2)}, sort_keys=True),
        "support_json": json.dumps({classes[i]: int(support[i]) for i in range(2)}, sort_keys=True),
        "predictions_json": json.dumps(predictions, sort_keys=True),
    }


def run_baselines(meta: pd.DataFrame, signal_features: pd.DataFrame) -> pd.DataFrame:
    rows = []
    X_meta = metadata_feature_matrix(meta)
    X_signal = signal_feature_matrix(signal_features)
    ids = list(meta["experiment_id"])
    for scheme_col, scheme_name in [("label_scheme_A", "A"), ("label_scheme_B", "B")]:
        labels = meta[scheme_col].astype(str).to_numpy()
        for baseline, X in [("metadata_only", X_meta), ("signal_only", X_signal)]:
            result = evaluate_loeo(X, labels, ids)
            rows.append(
                {
                    "scheme": scheme_name,
                    "baseline": baseline,
                    "split_protocol": "leave_one_experiment_out",
                    **result,
                }
            )
    return pd.DataFrame(rows)


def write_file_tree_report(
    out_path: Path,
    tree_lines: list[str],
    suffix_counts: dict[str, int],
    meta: pd.DataFrame,
    condition_summary: pd.DataFrame,
) -> None:
    lines = tree_lines + [
        "",
        "## File Type Counts",
        "",
        json.dumps(suffix_counts, indent=2, sort_keys=True),
        "",
        "## Auto-Identified Artifacts",
        "",
        "- Metadata / experiment info: MAT metadata fields plus `signals_stats.csv`.",
        "- Wear labels / VB: `VB` MAT field, filename `VB...`, and `VB_images/`.",
        "- Signal files: `signals_synced/*.mat` and `signals_unsynced/*.mat`.",
        "- Preferred audit signals: synced MAT files, one experiment per file.",
        "",
        "## Experiment Count",
        "",
        f"- Synced MAT experiments: `{len(meta)}`",
        f"- Unique materials: `{sorted(meta['material'].unique())}`",
        f"- Unique cutting speeds: `{[float(v) for v in sorted(meta['cutting_speed'].unique())]}`",
        f"- Unique feed rates: `{[float(v) for v in sorted(meta['feed_rate'].unique())]}`",
        f"- Unique depths of cut: `{[float(v) for v in sorted(meta['depth_of_cut'].unique())]}`",
        f"- Unique rounded VB levels: `{[float(v) for v in sorted(meta['VB_level'].unique())]}`",
        "",
        "## Condition Wear Summary",
        "",
        f"- Conditions with multiple rounded VB levels: `{int(condition_summary['has_multiple_wear_levels'].sum())}/{len(condition_summary)}`",
    ]
    out_path.write_text("\n".join(lines) + "\n")


def write_confound_report(
    out_path: Path,
    meta: pd.DataFrame,
    support: pd.DataFrame,
    condition_summary: pd.DataFrame,
    label_dist: pd.DataFrame,
    baseline: pd.DataFrame,
) -> None:
    cond_multiple = int(condition_summary["has_multiple_wear_levels"].sum()) if not condition_summary.empty else 0
    scheme_a = baseline[(baseline["scheme"] == "A") & (baseline["baseline"] == "metadata_only")]
    scheme_a_sig = baseline[(baseline["scheme"] == "A") & (baseline["baseline"] == "signal_only")]
    metadata_ok = bool(not scheme_a.empty and float(scheme_a.iloc[0]["acc"]) < 0.95)
    signal_ok = bool(
        not scheme_a_sig.empty
        and scheme_a_sig.iloc[0]["status"] == "ok"
        and float(scheme_a_sig.iloc[0]["acc"]) > float(scheme_a_sig.iloc[0]["majority_acc"])
    )
    support_a = label_dist[label_dist["scheme"] == "A"].set_index("label")["n_experiments"].to_dict()
    support_b = label_dist[label_dist["scheme"] == "B"].set_index("label")["n_experiments"].to_dict()
    enough_a = support_a.get("healthy", 0) >= 2 and support_a.get("worn", 0) >= 2
    enough_b = support_b.get("healthy", 0) >= 2 and support_b.get("worn", 0) >= 2
    pass_conditions = {
        "same_condition_multiple_wear_levels": cond_multiple > 0,
        "metadata_only_not_near_100_percent_scheme_A": metadata_ok,
        "signal_only_above_majority_scheme_A": signal_ok,
        "scheme_A_support_enough": enough_a,
        "scheme_B_support_enough": enough_b,
        "experiment_level_split_constructible_scheme_A": enough_a,
        "experiment_level_split_constructible_scheme_B": enough_b,
    }
    lines = [
        "# MU-TCM Small Subset Confound Audit",
        "",
        "Status: 0-API data audit only; not a formal conclusion.",
        "",
        "## Dataset Support",
        "",
        f"- Experiments: `{len(meta)}`",
        f"- Rounded VB levels: `{[float(v) for v in sorted(meta['VB_level'].unique())]}`",
        f"- Conditions with multiple rounded VB levels: `{cond_multiple}/{len(condition_summary)}`",
        "",
        "## Label Schemes",
        "",
        "| scheme | label | n experiments | VB values |",
        "|---|---|---:|---|",
    ]
    for _, row in label_dist.iterrows():
        lines.append(f"| {row['scheme']} | {row['label']} | {int(row['n_experiments'])} | {row['VB_values']} |")
    lines.extend(
        [
            "",
            "Scheme A maps rounded VB levels: healthy=`{0.0,0.1}`, worn=`{0.2,0.3}`.",
            "Scheme B uses strict labels: healthy=`VB==0.0`, worn=`VB>=0.2`, discarding `0<VB<0.2`.",
            "",
            "## Baselines",
            "",
            "| scheme | baseline | status | n | Acc | Macro-F1 | majority Acc | per-class F1 |",
            "|---|---|---|---:|---:|---:|---:|---|",
        ]
    )
    for _, row in baseline.iterrows():
        acc = "" if pd.isna(row["acc"]) else f"{float(row['acc']):.4f}"
        macro = "" if pd.isna(row["macro_f1"]) else f"{float(row['macro_f1']):.4f}"
        majority = "" if pd.isna(row["majority_acc"]) else f"{float(row['majority_acc']):.4f}"
        lines.append(
            f"| {row['scheme']} | {row['baseline']} | {row['status']} | {int(row['n_labeled'])} | "
            f"{acc} | {macro} | {majority} | `{row.get('per_class_f1_json', '')}` |"
        )
    lines.extend(
        [
            "",
            "## Pass/Fail Against Screening Conditions",
            "",
            "| condition | pass |",
            "|---|---:|",
        ]
    )
    for key, value in pass_conditions.items():
        lines.append(f"| {key} | {value} |")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- The small subset has repeated wear levels under the same machining condition when material is included in the condition key.",
            "- Scheme A has enough healthy/worn support for leave-one-experiment-out diagnostics; Scheme B does not because it has only one strict `VB==0.0` healthy experiment.",
            "- This audit is useful for deciding whether to expand to the full MU-TCM dataset, but the small subset is too small to serve as a formal milling result by itself.",
        ]
    )
    out_path.write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="data/MU-TCM face-milling dataset/small_subset")
    parser.add_argument("--archive", default="data/MU-TCM face-milling dataset/small_subset.7z")
    parser.add_argument("--out-dir", default="breeze/results/mutcm_small_audit_2026-07-09")
    args = parser.parse_args()

    root = Path(args.data_dir)
    archive = Path(args.archive)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if not root.exists():
        raise SystemExit(f"extracted data directory not found: {root}")

    tree_lines, suffix_counts = tree_summary(root, archive)
    meta = build_metadata(root)
    support, condition_summary = support_tables(meta)
    label_dist = label_distribution(meta)
    signal_features = make_feature_table(meta)
    baseline = run_baselines(meta, signal_features)

    meta_cols = [
        "experiment_id",
        "material",
        "cutting_speed",
        "feed_rate",
        "depth_of_cut",
        "radial_depth_ae",
        "VB",
        "VB_level",
        "label_scheme_A",
        "label_scheme_B",
        "insert",
        "edge",
        "repetition",
        "sampling_rate_json",
        "sampling_rate_note",
        "sensor_file_paths",
        "signal_synced_path",
        "signal_unsynced_path",
        "VB_image_paths",
    ]
    meta[meta_cols].to_csv(out_dir / "mutcm_small_metadata_summary.csv", index=False)
    support.to_csv(out_dir / "mutcm_small_condition_wear_support.csv", index=False)
    label_dist.to_csv(out_dir / "mutcm_small_label_distribution.csv", index=False)
    baseline.to_csv(out_dir / "mutcm_small_baseline_summary.csv", index=False)
    signal_features.to_csv(out_dir / "mutcm_small_signal_feature_table.csv", index=False)
    condition_summary.to_csv(out_dir / "mutcm_small_condition_summary.csv", index=False)
    write_file_tree_report(out_dir / "mutcm_small_file_tree_report.md", tree_lines, suffix_counts, meta, condition_summary)
    write_confound_report(out_dir / "mutcm_small_confound_audit.md", meta, support, condition_summary, label_dist, baseline)
    print(f"wrote {out_dir / 'mutcm_small_file_tree_report.md'}")
    print(f"wrote {out_dir / 'mutcm_small_metadata_summary.csv'}")
    print(f"wrote {out_dir / 'mutcm_small_condition_wear_support.csv'}")
    print(f"wrote {out_dir / 'mutcm_small_label_distribution.csv'}")
    print(f"wrote {out_dir / 'mutcm_small_confound_audit.md'}")
    print(f"wrote {out_dir / 'mutcm_small_baseline_summary.csv'}")


if __name__ == "__main__":
    main()
