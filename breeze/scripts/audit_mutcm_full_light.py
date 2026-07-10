"""Light audit for MU-TCM full_dataset from CSV-only features.

This script intentionally does not extract or read any MAT signal files.  It
uses only:

- the archive file listing;
- `signals_stats.csv`;
- `signals_sync.csv`.

All evaluations are audit-only and use experiment/file/group-level splits.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_recall_fscore_support
from sklearn.model_selection import GroupKFold, LeaveOneGroupOut, LeaveOneOut
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

try:
    from xgboost import XGBClassifier  # type: ignore
except Exception:  # pragma: no cover - optional local dependency
    XGBClassifier = None


FILENAME_RE = re.compile(
    r"Insert(?P<insert>\d+)Edge(?P<edge>\d+)_Vc(?P<Vc>[-+0-9.]+)_fz(?P<fz>[-+0-9.]+)_"
    r"ap(?P<ap>[-+0-9.]+)_VB(?P<VB>[-+0-9.]+)_Rep(?P<rep>\d+)\.mat$"
)
META_COLS = {
    "_file_name",
    "RPM_avg",
    "material",
    "Vc",
    "fz",
    "ap",
    "ae",
    "VB",
    "Insert",
    "Edge",
    "Repetition",
    "experiment_id",
    "insert_edge",
    "rounded_VB_level",
    "Lubrication",
    "label_scheme_A",
    "label_scheme_B",
    "label_scheme_C",
    "signal_synced_path",
    "signal_unsynced_path",
}
DIRECT_LEAK_PATTERNS = ("vb", "file", "filename", "_name")
SIGNAL_SUFFIXES = (
    "_rms",
    "_var",
    "_max",
    "_kurt",
    "_skew",
    "_ptp",
    "_speckurt",
    "_specskew",
    "_wavenergy",
)


def parse_filename(name: str) -> dict[str, Any]:
    m = FILENAME_RE.match(name)
    if not m:
        return {"filename_parse_ok": False}
    out: dict[str, Any] = {"filename_parse_ok": True}
    for key, value in m.groupdict().items():
        out[key] = int(value) if key in {"insert", "edge", "rep"} else float(value)
    return out


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, sep=";")


def rounded_vb(vb: float) -> float:
    return round(float(vb), 1)


def label_a(vb: float) -> str:
    level = rounded_vb(vb)
    if level in {0.0, 0.1}:
        return "healthy"
    if level in {0.2, 0.3}:
        return "worn"
    return "unlabeled"


def label_b(vb: float) -> str:
    level = rounded_vb(vb)
    if level == 0.0:
        return "healthy"
    if level >= 0.2:
        return "worn"
    return "unlabeled"


def label_c(vb: float) -> str:
    return "healthy" if float(vb) < 0.15 else "worn"


def lubrication_from_material(material: str) -> str:
    if "CastIron" in material:
        return "Dry"
    if "StainlessSteel" in material:
        return "MQL"
    return "unknown"


def archive_listing(archive: Path) -> list[str]:
    if not archive.exists():
        return []
    proc = subprocess.run(
        ["bsdtar", "-tf", str(archive)],
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        return []
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def summarize_archive(paths: list[str]) -> dict[str, int]:
    return {
        "synced_mat": sum(p.startswith("full_dataset/signals_synced/") and p.endswith(".mat") for p in paths),
        "unsynced_mat": sum(p.startswith("full_dataset/signals_unsynced/") and p.endswith(".mat") for p in paths),
        "vb_images": sum(p.startswith("full_dataset/VB_images/") and p.lower().endswith(".jpg") for p in paths),
        "csv": sum(p.startswith("full_dataset/") and p.lower().endswith(".csv") for p in paths),
        "signals_stats_csv": int("full_dataset/signals_stats.csv" in paths),
        "signals_sync_csv": int("full_dataset/signals_sync.csv" in paths),
    }


def build_metadata(stats: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in stats.iterrows():
        fname = str(row["_file_name"])
        parsed = parse_filename(fname)
        insert = int(parsed.get("insert", -1))
        edge = int(parsed.get("edge", -1))
        rep = int(parsed.get("rep", -1))
        material = str(row["material"])
        vb = float(row["VB"])
        rows.append(
            {
                "file_name": fname,
                "experiment_id": Path(fname).stem,
                "Insert": insert,
                "Edge": edge,
                "Repetition": rep,
                "insert_edge": f"Insert{insert}_Edge{edge}",
                "WorkpieceMaterial": material,
                "material": material,
                "Lubrication": lubrication_from_material(material),
                "Vc": float(row["Vc"]),
                "fz": float(row["fz"]),
                "ap": float(row["ap"]),
                "ae": float(row["ae"]),
                "VB": vb,
                "rounded_VB_level": rounded_vb(vb),
                "label_scheme_A": label_a(vb),
                "label_scheme_B": label_b(vb),
                "label_scheme_C": label_c(vb),
                "signal_synced_path": f"full_dataset/signals_synced/{fname}",
                "signal_unsynced_path": f"full_dataset/signals_unsynced/{fname}",
                "filename_parse_ok": bool(parsed.get("filename_parse_ok", False)),
            }
        )
    return pd.DataFrame(rows)


def condition_cols(include_repetition: bool = False) -> list[str]:
    cols = ["material", "Vc", "fz", "ap", "ae"]
    if include_repetition:
        cols.append("Repetition")
    return cols


def condition_id(meta: pd.DataFrame) -> pd.Series:
    return meta[condition_cols(False)].astype(str).agg("|".join, axis=1)


def support_table(meta: pd.DataFrame) -> pd.DataFrame:
    cols = condition_cols(False) + ["rounded_VB_level", "Repetition"]
    rows = []
    for key, g in meta.groupby(cols, dropna=False):
        rows.append(
            {
                **dict(zip(cols, key, strict=False)),
                "n_experiments": int(len(g)),
                "VB_values": ";".join(f"{float(v):g}" for v in sorted(g["VB"].unique())),
                "experiment_ids": ";".join(sorted(g["experiment_id"])),
            }
        )
    return pd.DataFrame(rows).sort_values(cols)


def condition_summary(meta: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for key, g in meta.groupby(condition_cols(False), dropna=False):
        levels = sorted(float(v) for v in g["rounded_VB_level"].unique())
        labels_a = sorted(set(g["label_scheme_A"]) - {"unlabeled"})
        labels_b = sorted(set(g["label_scheme_B"]) - {"unlabeled"})
        labels_c = sorted(set(g["label_scheme_C"]) - {"unlabeled"})
        reps_by_level = {
            f"{float(level):.1f}": sorted(int(v) for v in g[g["rounded_VB_level"] == level]["Repetition"].unique())
            for level in levels
        }
        rows.append(
            {
                **dict(zip(condition_cols(False), key, strict=False)),
                "condition_id": "|".join(str(x) for x in key),
                "n_experiments": int(len(g)),
                "VB_levels": ";".join(f"{v:.1f}" for v in levels),
                "has_all_0p0_0p1_0p2_0p3": set(levels) >= {0.0, 0.1, 0.2, 0.3},
                "scheme_A_has_both_labels": set(labels_a) >= {"healthy", "worn"},
                "scheme_B_has_both_labels": set(labels_b) >= {"healthy", "worn"},
                "scheme_C_has_both_labels": set(labels_c) >= {"healthy", "worn"},
                "repetitions_by_level_json": json.dumps(reps_by_level, sort_keys=True),
                "min_repetitions_per_level": min((len(v) for v in reps_by_level.values()), default=0),
            }
        )
    return pd.DataFrame(rows).sort_values(condition_cols(False))


def label_scheme_audit(meta: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    rows = []
    cond = condition_id(meta)
    insert_edge = meta["insert_edge"].astype(str)
    for scheme_name, col in [("A", "label_scheme_A"), ("B", "label_scheme_B"), ("C", "label_scheme_C")]:
        labels = meta[col].astype(str)
        valid = labels != "unlabeled"
        counts = Counter(labels[valid])
        n_valid = int(valid.sum())
        groups_condition = cond[valid]
        condition_has_both = 0
        condition_total = 0
        for _, g in meta[valid].groupby(cond[valid]):
            lab = set(g[col])
            condition_total += 1
            condition_has_both += int(lab >= {"healthy", "worn"})
        insert_edge_groups = int(insert_edge[valid].nunique())
        condition_groups = int(groups_condition.nunique())
        rows.append(
            {
                "scheme": scheme_name,
                "definition": {
                    "A": "healthy rounded_VB in {0.0,0.1}; worn rounded_VB in {0.2,0.3}",
                    "B": "healthy rounded_VB == 0.0; worn rounded_VB >= 0.2; drop rounded_VB == 0.1",
                    "C": "healthy VB < 0.15; worn VB >= 0.15",
                }[scheme_name],
                "n_valid": n_valid,
                "healthy": int(counts.get("healthy", 0)),
                "worn": int(counts.get("worn", 0)),
                "unlabeled": int((~valid).sum()),
                "balance_ratio_min_over_max": float(min(counts.values()) / max(counts.values())) if counts else 0.0,
                "supports_experiment_level_split": bool(counts.get("healthy", 0) >= 2 and counts.get("worn", 0) >= 2),
                "supports_leave_one_condition_out": bool(condition_groups >= 2 and condition_has_both == condition_total),
                "condition_groups": condition_groups,
                "condition_groups_with_both_labels": condition_has_both,
                "condition_groups_total": condition_total,
                "insert_edge_groups": insert_edge_groups,
                "supports_groupkfold_by_insert_edge": bool(insert_edge_groups >= 2 and counts.get("healthy", 0) >= 2 and counts.get("worn", 0) >= 2),
                "supports_n_real_2": bool(counts.get("healthy", 0) >= 2 and counts.get("worn", 0) >= 2),
                "supports_n_real_5": bool(counts.get("healthy", 0) >= 5 and counts.get("worn", 0) >= 5),
                "supports_n_real_10": bool(counts.get("healthy", 0) >= 10 and counts.get("worn", 0) >= 10),
            }
        )
        for group_name, group_values in [
            ("material", meta["material"].astype(str)),
            ("condition", cond),
            ("repetition", meta["Repetition"].astype(str)),
            ("insert_edge", insert_edge),
        ]:
            for value, idx in group_values[valid].groupby(group_values[valid]).groups.items():
                sub = meta.loc[idx, col]
                c = Counter(sub)
                rows.append(
                    {
                        "scheme": scheme_name,
                        "definition": f"per-{group_name}",
                        "group_type": group_name,
                        "group_value": value,
                        "n_valid": int(len(sub)),
                        "healthy": int(c.get("healthy", 0)),
                        "worn": int(c.get("worn", 0)),
                        "unlabeled": 0,
                        "balance_ratio_min_over_max": "",
                        "supports_experiment_level_split": "",
                        "supports_leave_one_condition_out": "",
                        "condition_groups": "",
                        "condition_groups_with_both_labels": "",
                        "condition_groups_total": "",
                        "insert_edge_groups": "",
                        "supports_groupkfold_by_insert_edge": "",
                        "supports_n_real_2": "",
                        "supports_n_real_5": "",
                        "supports_n_real_10": "",
                    }
                )
    return pd.DataFrame(rows), "summary rows have empty group_type; detail rows are per material/condition/repetition/insert_edge."


def safe_feature_cols(stats: pd.DataFrame) -> list[str]:
    cols = []
    for col in stats.columns:
        low = col.lower()
        if col in META_COLS:
            continue
        if any(p in low for p in DIRECT_LEAK_PATTERNS):
            continue
        if col.endswith("_start") or col.endswith("_end"):
            continue
        if col.endswith(SIGNAL_SUFFIXES):
            cols.append(col)
    return cols


def make_meta_matrix(meta: pd.DataFrame, leaky: bool) -> tuple[np.ndarray, list[str]]:
    categorical = ["material", "Lubrication"]
    numeric = ["Vc", "fz", "ap", "ae"]
    if leaky:
        categorical += ["insert_edge"]
        numeric += ["Insert", "Edge", "Repetition"]
    enc = OneHotEncoder(sparse_output=False, handle_unknown="ignore")
    X_cat = enc.fit_transform(meta[categorical].astype(str))
    X_num = meta[numeric].astype(float).to_numpy()
    names = list(enc.get_feature_names_out(categorical)) + numeric
    return np.concatenate([X_cat, X_num], axis=1).astype(float), names


def make_signal_matrix(stats: pd.DataFrame, cols: list[str]) -> np.ndarray:
    X = stats[cols].replace([np.inf, -np.inf], np.nan)
    X = X.fillna(X.median(numeric_only=True)).fillna(0.0)
    return X.to_numpy(dtype=float)


def make_model(name: str):
    if name == "logreg":
        return make_pipeline(StandardScaler(), LogisticRegression(max_iter=3000, class_weight="balanced", random_state=0))
    if name == "rf":
        return RandomForestClassifier(n_estimators=300, class_weight="balanced", random_state=0, min_samples_leaf=1)
    if name == "extratrees":
        return ExtraTreesClassifier(n_estimators=400, class_weight="balanced", random_state=0, min_samples_leaf=1)
    if name == "xgboost" and XGBClassifier is not None:
        return XGBClassifier(
            n_estimators=100,
            max_depth=3,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.9,
            random_state=0,
            eval_metric="logloss",
        )
    raise ValueError(name)


def split_indices(protocol: str, groups: np.ndarray, y: np.ndarray) -> list[tuple[np.ndarray, np.ndarray]]:
    n = len(y)
    if protocol == "loeo":
        return [(tr, te) for tr, te in LeaveOneOut().split(np.arange(n))]
    unique_groups = np.unique(groups)
    if len(unique_groups) < 2:
        return []
    if protocol in {"logo_condition", "logo_insert_edge"}:
        return [(tr, te) for tr, te in LeaveOneGroupOut().split(np.arange(n), y, groups)]
    n_splits = min(5, len(unique_groups))
    if n_splits < 2:
        return []
    return [(tr, te) for tr, te in GroupKFold(n_splits=n_splits).split(np.arange(n), y, groups)]


def majority_baseline(y: np.ndarray) -> float:
    if len(y) == 0:
        return float("nan")
    return float(max(Counter(y).values()) / len(y))


def evaluate(
    X: np.ndarray,
    labels: np.ndarray,
    ids: list[str],
    condition: np.ndarray,
    insert_edge: np.ndarray,
    scheme: str,
    baseline: str,
    model_name: str,
    protocol: str,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    valid = labels != "unlabeled"
    Xv = X[valid]
    y_str = labels[valid]
    ids_v = [ids[i] for i, ok in enumerate(valid) if ok]
    cond_v = condition[valid]
    edge_v = insert_edge[valid]
    classes = ["healthy", "worn"]
    counts = Counter(y_str)
    row_base: dict[str, Any] = {
        "scheme": scheme,
        "baseline": baseline,
        "model": model_name,
        "split_protocol": protocol,
        "n_labeled": int(len(y_str)),
        "label_counts_json": json.dumps(dict(counts), sort_keys=True),
        "majority_acc": majority_baseline(y_str),
    }
    if len(y_str) < 4 or counts.get("healthy", 0) < 2 or counts.get("worn", 0) < 2:
        row = {
            **row_base,
            "status": "insufficient_label_support",
            "n_folds": 0,
            "acc": np.nan,
            "macro_f1": np.nan,
            "per_class_f1_json": "",
            "confusion_json": "",
        }
        return row, [], []
    y = np.asarray([classes.index(v) for v in y_str], dtype=int)
    groups = cond_v if protocol in {"logo_condition", "groupkfold_condition"} else edge_v
    splits = split_indices(protocol, groups, y)
    if not splits:
        row = {**row_base, "status": "split_not_constructible", "n_folds": 0, "acc": np.nan, "macro_f1": np.nan}
        return row, [], []
    preds = np.full_like(y, -1)
    for train_idx, test_idx in splits:
        if set(int(v) for v in y[train_idx]) != {0, 1}:
            pred = Counter(y[train_idx]).most_common(1)[0][0]
            preds[test_idx] = pred
            continue
        model = make_model(model_name)
        model.fit(Xv[train_idx], y[train_idx])
        preds[test_idx] = model.predict(Xv[test_idx])
    acc = float(accuracy_score(y, preds))
    macro = float(f1_score(y, preds, average="macro", zero_division=0))
    _, _, f1, support = precision_recall_fscore_support(y, preds, labels=[0, 1], zero_division=0)
    cm = confusion_matrix(y, preds, labels=[0, 1])
    row = {
        **row_base,
        "status": "ok",
        "n_folds": len(splits),
        "acc": acc,
        "macro_f1": macro,
        "per_class_f1_json": json.dumps({classes[i]: float(f1[i]) for i in range(2)}, sort_keys=True),
        "support_json": json.dumps({classes[i]: int(support[i]) for i in range(2)}, sort_keys=True),
        "confusion_json": json.dumps(cm.tolist()),
    }
    confusion_rows = []
    for i, actual in enumerate(classes):
        for j, predicted in enumerate(classes):
            confusion_rows.append(
                {
                    "scheme": scheme,
                    "baseline": baseline,
                    "model": model_name,
                    "split_protocol": protocol,
                    "actual": actual,
                    "predicted": predicted,
                    "n": int(cm[i, j]),
                }
            )
    perf_rows = []
    pred_labels = np.asarray([classes[int(v)] for v in preds])
    actual_labels = np.asarray([classes[int(v)] for v in y])
    for cond_value in sorted(set(cond_v)):
        mask = cond_v == cond_value
        if not np.any(mask):
            continue
        perf_rows.append(
            {
                "scheme": scheme,
                "baseline": baseline,
                "model": model_name,
                "split_protocol": protocol,
                "condition_id": cond_value,
                "n": int(mask.sum()),
                "majority_acc": majority_baseline(actual_labels[mask]),
                "acc": float(accuracy_score(actual_labels[mask], pred_labels[mask])),
                "macro_f1": float(f1_score(actual_labels[mask], pred_labels[mask], average="macro", zero_division=0)),
            }
        )
    return row, confusion_rows, perf_rows


def run_metadata_baselines(meta: pd.DataFrame) -> pd.DataFrame:
    rows = []
    ids = list(meta["experiment_id"])
    cond = condition_id(meta).to_numpy()
    edge = meta["insert_edge"].astype(str).to_numpy()
    for scheme, col in [("A", "label_scheme_A"), ("B", "label_scheme_B"), ("C", "label_scheme_C")]:
        labels = meta[col].astype(str).to_numpy()
        for baseline, leaky in [("metadata_safe", False), ("metadata_leaky", True)]:
            X, _ = make_meta_matrix(meta, leaky)
            for protocol in ["loeo", "logo_condition", "groupkfold_condition", "groupkfold_insert_edge"]:
                row, _, _ = evaluate(X, labels, ids, cond, edge, scheme, baseline, "logreg", protocol)
                rows.append(row)
    return pd.DataFrame(rows)


def run_signal_baselines(meta: pd.DataFrame, stats: pd.DataFrame, feature_cols: list[str]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rows = []
    confusions = []
    per_condition = []
    X = make_signal_matrix(stats, feature_cols)
    ids = list(meta["experiment_id"])
    cond = condition_id(meta).to_numpy()
    edge = meta["insert_edge"].astype(str).to_numpy()
    model_names = ["logreg", "rf", "extratrees"]
    if XGBClassifier is not None:
        model_names.append("xgboost")
    for scheme, col in [("A", "label_scheme_A"), ("B", "label_scheme_B"), ("C", "label_scheme_C")]:
        labels = meta[col].astype(str).to_numpy()
        for model_name in model_names:
            for protocol in ["loeo", "logo_condition", "groupkfold_condition", "groupkfold_insert_edge"]:
                row, cm, perf = evaluate(X, labels, ids, cond, edge, scheme, "signal_only", model_name, protocol)
                rows.append(row)
                confusions.extend(cm)
                per_condition.extend(perf)
    return pd.DataFrame(rows), pd.DataFrame(confusions), pd.DataFrame(per_condition)


def write_file_tree_report(path: Path, archive: Path, summary: dict[str, int], listing: list[str], csv_dir: Path) -> None:
    sample = "\n".join(f"- `{p}`" for p in listing[:120])
    lines = [
        "# MU-TCM Full Dataset Light File Tree Report",
        "",
        "- Audit mode: light; only CSV files were extracted.",
        f"- Archive: `{archive}`",
        f"- Extracted CSV dir: `{csv_dir}`",
        "",
        "## Counts",
        "",
        f"- synced MAT: `{summary['synced_mat']}`",
        f"- unsynced MAT: `{summary['unsynced_mat']}`",
        f"- VB image jpg: `{summary['vb_images']}`",
        f"- CSV: `{summary['csv']}`",
        f"- signals_stats.csv present: `{bool(summary['signals_stats_csv'])}`",
        f"- signals_sync.csv present: `{bool(summary['signals_sync_csv'])}`",
        "",
        "## Listing Sample",
        "",
        sample,
    ]
    path.write_text("\n".join(lines) + "\n")


def markdown_table(df: pd.DataFrame, cols: list[str], max_rows: int = 30) -> list[str]:
    if df.empty:
        return ["No rows."]
    out = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in df.head(max_rows).iterrows():
        out.append("| " + " | ".join(str(row.get(c, "")) for c in cols) + " |")
    if len(df) > max_rows:
        out.append(f"| ... | {len(df) - max_rows} more rows |" + " |" * max(0, len(cols) - 2))
    return out


def write_metadata_report(path: Path, meta: pd.DataFrame) -> None:
    lines = [
        "# MU-TCM Full Metadata Report",
        "",
        f"- Experiments in `signals_stats.csv`: `{len(meta)}`",
        f"- Unique materials: `{sorted(meta['material'].unique())}`",
        f"- Unique Vc: `{[float(v) for v in sorted(meta['Vc'].unique())]}`",
        f"- Unique fz: `{[float(v) for v in sorted(meta['fz'].unique())]}`",
        f"- Unique ap: `{[float(v) for v in sorted(meta['ap'].unique())]}`",
        f"- Unique ae: `{[float(v) for v in sorted(meta['ae'].unique())]}`",
        f"- Rounded VB levels: `{[float(v) for v in sorted(meta['rounded_VB_level'].unique())]}`",
        f"- Filename parse failures: `{int((~meta['filename_parse_ok']).sum())}`",
    ]
    path.write_text("\n".join(lines) + "\n")


def write_support_report(path: Path, cond_summary: pd.DataFrame) -> None:
    lines = [
        "# MU-TCM Full Condition Wear Support Report",
        "",
        f"- Cutting conditions: `{len(cond_summary)}`",
        f"- Conditions with VB 0.0/0.1/0.2/0.3: `{int(cond_summary['has_all_0p0_0p1_0p2_0p3'].sum())}/{len(cond_summary)}`",
        f"- Scheme A conditions with both labels: `{int(cond_summary['scheme_A_has_both_labels'].sum())}/{len(cond_summary)}`",
        f"- Scheme B conditions with both labels: `{int(cond_summary['scheme_B_has_both_labels'].sum())}/{len(cond_summary)}`",
        f"- Scheme C conditions with both labels: `{int(cond_summary['scheme_C_has_both_labels'].sum())}/{len(cond_summary)}`",
        f"- Minimum repetitions per condition/VB level: `{int(cond_summary['min_repetitions_per_level'].min())}`",
        "",
        "## Condition Summary",
        "",
    ]
    lines.extend(
        markdown_table(
            cond_summary,
            [
                "condition_id",
                "n_experiments",
                "VB_levels",
                "has_all_0p0_0p1_0p2_0p3",
                "scheme_A_has_both_labels",
                "scheme_C_has_both_labels",
                "min_repetitions_per_level",
            ],
            max_rows=20,
        )
    )
    path.write_text("\n".join(lines) + "\n")


def write_label_report(path: Path, label_audit: pd.DataFrame, note: str) -> None:
    summary = label_audit[label_audit.get("group_type", "").fillna("") == ""]
    lines = [
        "# MU-TCM Full Label Scheme Audit",
        "",
        note,
        "",
    ]
    lines.extend(
        markdown_table(
            summary,
            [
                "scheme",
                "n_valid",
                "healthy",
                "worn",
                "unlabeled",
                "balance_ratio_min_over_max",
                "supports_experiment_level_split",
                "supports_leave_one_condition_out",
                "supports_n_real_2",
                "supports_n_real_5",
                "supports_n_real_10",
            ],
        )
    )
    path.write_text("\n".join(lines) + "\n")


def write_metadata_confound_report(path: Path, meta_base: pd.DataFrame) -> None:
    lines = [
        "# MU-TCM Full Metadata Confound Report",
        "",
        "| scheme | baseline | split | status | Acc | Macro-F1 | majority |",
        "|---|---|---|---|---:|---:|---:|",
    ]
    for _, row in meta_base.iterrows():
        acc = "" if pd.isna(row["acc"]) else f"{float(row['acc']):.4f}"
        macro = "" if pd.isna(row["macro_f1"]) else f"{float(row['macro_f1']):.4f}"
        majority = "" if pd.isna(row["majority_acc"]) else f"{float(row['majority_acc']):.4f}"
        lines.append(
            f"| {row['scheme']} | {row['baseline']} | {row['split_protocol']} | {row['status']} | {acc} | {macro} | {majority} |"
        )
    lines.extend(
        [
            "",
            "Interpretation: `metadata_safe` excludes insert, edge, and repetition. `metadata_leaky` includes them to test tool identity leakage.",
        ]
    )
    path.write_text("\n".join(lines) + "\n")


def best_signal_rows(signal_base: pd.DataFrame) -> pd.DataFrame:
    ok = signal_base[signal_base["status"] == "ok"].copy()
    if ok.empty:
        return ok
    return ok.sort_values(["scheme", "split_protocol", "macro_f1", "acc"], ascending=[True, True, False, False]).groupby(
        ["scheme", "split_protocol"], as_index=False
    ).head(1)


def decide(
    label_audit: pd.DataFrame,
    cond_summary: pd.DataFrame,
    meta_base: pd.DataFrame,
    signal_base: pd.DataFrame,
) -> tuple[bool, list[str], str | None]:
    reasons: list[str] = []
    summary = label_audit[label_audit.get("group_type", "").fillna("") == ""]
    candidate_schemes = []
    for scheme in ["A", "C"]:
        row = summary[summary["scheme"] == scheme].iloc[0]
        if bool(row["supports_n_real_10"]) and float(row["balance_ratio_min_over_max"]) >= 0.5:
            candidate_schemes.append(scheme)
    if not candidate_schemes:
        reasons.append("No candidate among Scheme A/C is both balanced and supports n_real=10.")
    all_conditions_both = {
        "A": bool(cond_summary["scheme_A_has_both_labels"].all()),
        "C": bool(cond_summary["scheme_C_has_both_labels"].all()),
    }
    chosen = None
    best_metric = -np.inf
    best = best_signal_rows(signal_base)
    for scheme in candidate_schemes:
        safe = meta_base[
            (meta_base["scheme"] == scheme)
            & (meta_base["baseline"] == "metadata_safe")
            & (meta_base["split_protocol"] == "logo_condition")
        ]
        signal_logo = best[(best["scheme"] == scheme) & (best["split_protocol"] == "logo_condition")]
        signal_edge = best[(best["scheme"] == scheme) & (best["split_protocol"] == "groupkfold_insert_edge")]
        if not all_conditions_both.get(scheme, False):
            reasons.append(f"Scheme {scheme}: not every cutting condition contains both healthy and worn.")
            continue
        if safe.empty or safe.iloc[0]["status"] != "ok" or float(safe.iloc[0]["acc"]) >= 0.95:
            reasons.append(f"Scheme {scheme}: metadata_safe is near-perfect or unavailable under LOGO condition.")
            continue
        if signal_logo.empty or float(signal_logo.iloc[0]["acc"]) <= float(signal_logo.iloc[0]["majority_acc"]):
            reasons.append(f"Scheme {scheme}: signal-only does not beat majority under LOGO condition.")
            continue
        if signal_edge.empty or float(signal_edge.iloc[0]["acc"]) <= float(signal_edge.iloc[0]["majority_acc"]):
            reasons.append(f"Scheme {scheme}: signal-only does not beat majority under insert-edge GroupKFold.")
            continue
        leaky = meta_base[
            (meta_base["scheme"] == scheme)
            & (meta_base["baseline"] == "metadata_leaky")
            & (meta_base["split_protocol"] == "groupkfold_insert_edge")
        ]
        if not leaky.empty and float(leaky.iloc[0]["acc"]) >= 0.95:
            reasons.append(f"Scheme {scheme}: metadata_leaky is near-perfect, indicating insert/edge identity leakage.")
            continue
        metric = float(signal_logo.iloc[0]["macro_f1"]) + float(signal_edge.iloc[0]["macro_f1"])
        if metric > best_metric:
            best_metric = metric
            chosen = scheme
    return chosen is not None, reasons, chosen


def write_final_report(
    pass_path: Path,
    fail_path: Path,
    passed: bool,
    reasons: list[str],
    chosen: str | None,
    label_audit: pd.DataFrame,
    meta_base: pd.DataFrame,
    signal_base: pd.DataFrame,
) -> None:
    target = pass_path if passed else fail_path
    other = fail_path if passed else pass_path
    if other.exists():
        other.unlink()
    best = best_signal_rows(signal_base)
    lines = [
        f"# MU-TCM Full Audit {'Pass' if passed else 'Fail'}",
        "",
        "Status: light audit only; no MAT extraction beyond CSVs, no LLM/API, no preregistration, no formal test.",
        "",
    ]
    if passed:
        lines.extend(
            [
                f"- Recommended label scheme: `{chosen}`",
                "- Recommended split protocol: condition-aware outer split plus inner validation, with mandatory insert-edge grouped isolation/diagnostics.",
                "- Recommended feature set for first formal protocol: `signals_stats.csv` signal statistics only; no filename/VB/metadata fields.",
                "- Baselines: real_only, noise_aug on signal windows only after MAT extraction, rule/random/LLM only after inner-val verifier calibration.",
                "- Next step: extract `signals_synced/*.mat` only, build experiment-level NPZ, and create a new preregistration before any formal held-out test.",
                "- Critical caveat: metadata_leaky is near-perfect under non-insert-edge-isolated splits, so Insert/Edge/Repetition must never be treated as safe model features.",
            ]
        )
    else:
        lines.extend(["## Failure Reasons", ""])
        lines.extend(f"- {reason}" for reason in reasons)
    lines.extend(
        [
            "",
            "## Label Scheme Summary",
            "",
        ]
    )
    summary = label_audit[label_audit.get("group_type", "").fillna("") == ""]
    lines.extend(markdown_table(summary, ["scheme", "healthy", "worn", "unlabeled", "supports_n_real_10"]))
    lines.extend(["", "## Metadata Baseline Snapshot", ""])
    lines.extend(markdown_table(meta_base, ["scheme", "baseline", "split_protocol", "status", "acc", "macro_f1"], max_rows=24))
    lines.extend(["", "## Best Signal Baseline Snapshot", ""])
    lines.extend(markdown_table(best, ["scheme", "split_protocol", "model", "acc", "macro_f1", "majority_acc"], max_rows=24))
    target.write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", default="data/MU-TCM face-milling dataset/full_dataset.7z")
    parser.add_argument("--csv-dir", default="breeze/results/mutcm_full_light_audit_2026-07-09/extracted_csv/full_dataset")
    parser.add_argument("--out-dir", default="breeze/results/mutcm_full_light_audit_2026-07-09")
    args = parser.parse_args()

    archive = Path(args.archive)
    csv_dir = Path(args.csv_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stats_path = csv_dir / "signals_stats.csv"
    sync_path = csv_dir / "signals_sync.csv"
    if not stats_path.exists() or not sync_path.exists():
        raise SystemExit(f"missing extracted CSVs: {stats_path}, {sync_path}")

    listing = archive_listing(archive)
    summary = summarize_archive(listing)
    stats = read_csv(stats_path)
    _sync = read_csv(sync_path)
    meta = build_metadata(stats)
    support = support_table(meta)
    cond_summary = condition_summary(meta)
    label_audit, label_note = label_scheme_audit(meta)
    feature_cols = safe_feature_cols(stats)
    meta_base = run_metadata_baselines(meta)
    signal_base, confusions, per_condition = run_signal_baselines(meta, stats, feature_cols)
    passed, reasons, chosen = decide(label_audit, cond_summary, meta_base, signal_base)

    meta.to_csv(out_dir / "mutcm_full_metadata_summary.csv", index=False)
    support.to_csv(out_dir / "mutcm_full_condition_wear_support.csv", index=False)
    cond_summary.to_csv(out_dir / "mutcm_full_condition_summary.csv", index=False)
    label_audit.to_csv(out_dir / "mutcm_full_label_scheme_audit.csv", index=False)
    meta_base.to_csv(out_dir / "mutcm_full_metadata_only_baseline.csv", index=False)
    signal_base.to_csv(out_dir / "mutcm_full_signal_only_baseline.csv", index=False)
    confusions.to_csv(out_dir / "mutcm_full_signal_only_confusions.csv", index=False)
    per_condition.to_csv(out_dir / "mutcm_full_per_condition_performance.csv", index=False)
    pd.DataFrame({"feature": feature_cols}).to_csv(out_dir / "mutcm_full_signal_feature_columns.csv", index=False)

    write_file_tree_report(out_dir / "full_dataset_file_tree_report.md", archive, summary, listing, csv_dir)
    write_metadata_report(out_dir / "mutcm_full_metadata_report.md", meta)
    write_support_report(out_dir / "mutcm_full_condition_wear_support_report.md", cond_summary)
    write_label_report(out_dir / "mutcm_full_label_scheme_audit.md", label_audit, label_note)
    write_metadata_confound_report(out_dir / "mutcm_full_metadata_confound_report.md", meta_base)
    write_final_report(
        out_dir / "mutcm_full_audit_pass.md",
        out_dir / "mutcm_full_audit_fail.md",
        passed,
        reasons,
        chosen,
        label_audit,
        meta_base,
        signal_base,
    )
    print(f"wrote {out_dir}")
    print(f"feature_cols={len(feature_cols)} passed={passed} chosen={chosen}")


if __name__ == "__main__":
    main()
