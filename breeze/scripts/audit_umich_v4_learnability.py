"""Audit UMich v4 clean-label learnability and confounding.

This script does not generate synthetic data and does not read the formal
held-out test split.  It audits the outer-training experiments and evaluates
metadata-only, stage-only, and signal-feature-only baselines on the supplied
clean inner split.
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_recall_fscore_support
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


ACTIVE_STAGES = [
    "Layer 1 Up",
    "Layer 1 Down",
    "Layer 2 Up",
    "Layer 2 Down",
    "Layer 3 Up",
    "Layer 3 Down",
]
WIN = 64


def clean(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip().lower()


def quadrant(tool: str, visual: str) -> str:
    tool = clean(tool)
    visual = clean(visual)
    if tool == "unworn" and visual == "yes":
        return "clean_unworn"
    if tool == "worn" and visual == "no":
        return "clean_worn"
    if tool == "worn" and visual == "yes":
        return "ambiguous_worn_pass"
    if tool == "unworn" and visual == "no":
        return "ambiguous_unworn_fail"
    return f"ambiguous_{tool or 'missing_tool'}_{visual or 'missing_visual'}"


def contiguous_segments(labels: np.ndarray) -> list[tuple[str, int]]:
    if len(labels) == 0:
        return []
    out: list[tuple[str, int]] = []
    start = 0
    for i in range(1, len(labels) + 1):
        if i == len(labels) or labels[i] != labels[start]:
            out.append((str(labels[start]), i - start))
            start = i
    return out


def one_hot(values: np.ndarray, categories: list[str]) -> np.ndarray:
    vals = np.asarray([str(v) for v in values])
    X = np.zeros((len(vals), len(categories)), dtype=np.float32)
    pos = {cat: i for i, cat in enumerate(categories)}
    for i, v in enumerate(vals):
        j = pos.get(v)
        if j is not None:
            X[i, j] = 1.0
    return X


def signal_features(X: np.ndarray) -> np.ndarray:
    X = X.astype(np.float32)
    feats = []
    feats.append(X.mean(axis=2))
    feats.append(X.std(axis=2))
    feats.append(np.sqrt(np.mean(X * X, axis=2)))
    feats.append(X.min(axis=2))
    feats.append(X.max(axis=2))
    feats.append(np.ptp(X, axis=2))
    feats.append(np.median(X, axis=2))
    feats.append(np.quantile(X, 0.25, axis=2))
    feats.append(np.quantile(X, 0.75, axis=2))
    feats.append(X[:, :, -1] - X[:, :, 0])
    centered = X - X.mean(axis=2, keepdims=True)
    power = np.abs(np.fft.rfft(centered, axis=2)) ** 2
    if power.shape[2] > 1:
        power = power[:, :, 1:]
    n_bins = power.shape[2]
    bands = np.array_split(np.arange(n_bins), 4)
    total = power.sum(axis=2) + 1e-8
    for band in bands:
        if len(band) == 0:
            feats.append(np.zeros_like(total))
        else:
            feats.append(np.log1p(power[:, :, band].sum(axis=2) / total))
    return np.concatenate([f.reshape(f.shape[0], -1) for f in feats], axis=1).astype(np.float32)


def metadata_features(train: dict[str, np.ndarray], val: dict[str, np.ndarray], include_stage: bool) -> tuple[np.ndarray, np.ndarray]:
    train_num = np.stack(
        [
            train["feedrate"].astype(np.float32),
            train["clamp_pressure"].astype(np.float32),
            np.asarray([1.0 if str(v).strip().lower() == "yes" else 0.0 for v in train["machining_finalized"]], dtype=np.float32),
        ],
        axis=1,
    )
    val_num = np.stack(
        [
            val["feedrate"].astype(np.float32),
            val["clamp_pressure"].astype(np.float32),
            np.asarray([1.0 if str(v).strip().lower() == "yes" else 0.0 for v in val["machining_finalized"]], dtype=np.float32),
        ],
        axis=1,
    )
    if not include_stage:
        return train_num, val_num
    cats = sorted(set(str(v) for v in train["stage"]))
    return np.concatenate([train_num, one_hot(train["stage"], cats)], axis=1), np.concatenate(
        [val_num, one_hot(val["stage"], cats)], axis=1
    )


def evaluate_baseline(
    name: str,
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val: np.ndarray,
    y_val: np.ndarray,
    class_names: list[str],
    val_meta: dict[str, np.ndarray],
) -> tuple[dict[str, object], list[dict[str, object]], list[dict[str, object]]]:
    clf = make_pipeline(
        StandardScaler(),
        LogisticRegression(max_iter=2000, class_weight="balanced", random_state=0),
    )
    clf.fit(X_train, y_train)
    pred = clf.predict(X_val)
    acc = float(accuracy_score(y_val, pred))
    macro = float(f1_score(y_val, pred, average="macro", zero_division=0))
    pr, rc, f1, sup = precision_recall_fscore_support(y_val, pred, labels=list(range(len(class_names))), zero_division=0)
    row: dict[str, object] = {"baseline": name, "acc": acc, "macro_f1": macro}
    for i, cls in enumerate(class_names):
        row[f"precision_{cls}"] = float(pr[i])
        row[f"recall_{cls}"] = float(rc[i])
        row[f"f1_{cls}"] = float(f1[i])
        row[f"support_{cls}"] = int(sup[i])
    cm = confusion_matrix(y_val, pred, labels=list(range(len(class_names))))
    cm_rows = []
    for i, actual in enumerate(class_names):
        for j, predicted in enumerate(class_names):
            cm_rows.append({"baseline": name, "actual": actual, "predicted": predicted, "n": int(cm[i, j])})
    condition_rows = []
    keys = [
        (
            float(val_meta["feedrate"][i]),
            float(val_meta["clamp_pressure"][i]),
            str(val_meta["stage"][i]),
        )
        for i in range(len(y_val))
    ]
    for key in sorted(set(keys)):
        mask = np.asarray([k == key for k in keys])
        if not np.any(mask):
            continue
        condition_rows.append(
            {
                "baseline": name,
                "feedrate": key[0],
                "clamp_pressure": key[1],
                "stage": key[2],
                "n": int(mask.sum()),
                "acc": float(accuracy_score(y_val[mask], pred[mask])),
                "macro_f1": float(f1_score(y_val[mask], pred[mask], average="macro", zero_division=0)),
            }
        )
    return row, cm_rows, condition_rows


def load_npz(path: Path) -> dict[str, np.ndarray]:
    data = np.load(path, allow_pickle=True)
    return {k: data[k] for k in data.files}


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="data/archive")
    parser.add_argument("--source-npz", required=True, help="Outer-train stage-contiguous NPZ for audit counts.")
    parser.add_argument("--train-npz", required=True, help="Clean inner-train NPZ.")
    parser.add_argument("--val-npz", required=True, help="Clean inner-val NPZ.")
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    source = load_npz(Path(args.source_npz))
    train = load_npz(Path(args.train_npz))
    val = load_npz(Path(args.val_npz))
    class_names = [str(c) for c in train["class_names"]]
    source_experiments = sorted(set(int(v) for v in source["experiment"]))

    meta = pd.read_csv(data_dir / "train.csv")
    meta = meta[meta["No"].isin(source_experiments)].copy()
    experiment_rows = []
    raw_window_rows = []
    stage_counter: Counter[tuple[str, str]] = Counter()
    condition_counter: Counter[tuple[float, float, str]] = Counter()
    before_windows = 0
    active_windows = 0
    active_clean_windows = 0
    for _, rec in meta.iterrows():
        exp_no = int(rec["No"])
        q = quadrant(rec["tool_condition"], rec.get("passed_visual_inspection", ""))
        exp_file = data_dir / f"experiment_{exp_no:02d}.csv"
        df = pd.read_csv(exp_file)
        all_windows = 0
        exp_active = 0
        for stage, n_rows in contiguous_segments(df["Machining_Process"].astype(str).to_numpy()):
            n_win = n_rows // WIN
            if n_win <= 0:
                continue
            all_windows += n_win
            raw_window_rows.append(
                {
                    "experiment": exp_no,
                    "stage": stage,
                    "active_stage": stage in ACTIVE_STAGES,
                    "quadrant": q,
                    "tool_condition": clean(rec["tool_condition"]),
                    "passed_visual_inspection": clean(rec.get("passed_visual_inspection", "")),
                    "feedrate": float(rec["feedrate"]),
                    "clamp_pressure": float(rec["clamp_pressure"]),
                    "windows": n_win,
                }
            )
            if stage in ACTIVE_STAGES:
                exp_active += n_win
                stage_counter[(stage, q)] += n_win
                condition_counter[(float(rec["feedrate"]), float(rec["clamp_pressure"]), q)] += n_win
        before_windows += all_windows
        active_windows += exp_active
        if q in {"clean_unworn", "clean_worn"}:
            active_clean_windows += exp_active
        experiment_rows.append(
            {
                "experiment": exp_no,
                "quadrant": q,
                "tool_condition": clean(rec["tool_condition"]),
                "passed_visual_inspection": clean(rec.get("passed_visual_inspection", "")),
                "machining_finalized": clean(rec.get("machining_finalized", "")),
                "feedrate": float(rec["feedrate"]),
                "clamp_pressure": float(rec["clamp_pressure"]),
                "all_stage_windows": all_windows,
                "active_stage_windows": exp_active,
                "active_clean_supervised_windows": exp_active if q in {"clean_unworn", "clean_worn"} else 0,
            }
        )
    write_csv(out_dir / "umich_v4_quadrant_experiment_counts.csv", experiment_rows)
    write_csv(out_dir / "umich_v4_quadrant_window_counts.csv", raw_window_rows)
    write_csv(
        out_dir / "umich_v4_stage_quadrant_counts.csv",
        [{"stage": k[0], "quadrant": k[1], "windows": v} for k, v in sorted(stage_counter.items())],
    )
    write_csv(
        out_dir / "umich_v4_condition_quadrant_counts.csv",
        [
            {"feedrate": k[0], "clamp_pressure": k[1], "quadrant": k[2], "windows": v}
            for k, v in sorted(condition_counter.items())
        ],
    )

    baseline_rows = []
    cm_rows = []
    cond_rows = []
    X_meta_tr, X_meta_val = metadata_features(train, val, include_stage=True)
    X_stage_tr = one_hot(train["stage"], sorted(set(str(v) for v in train["stage"])))
    X_stage_val = one_hot(val["stage"], sorted(set(str(v) for v in train["stage"])))
    X_sig_tr = signal_features(train["X"])
    X_sig_val = signal_features(val["X"])
    for name, X_tr, X_va in [
        ("metadata_only", X_meta_tr, X_meta_val),
        ("stage_only", X_stage_tr, X_stage_val),
        ("signal_feature_only", X_sig_tr, X_sig_val),
    ]:
        row, cm, cond = evaluate_baseline(name, X_tr, train["y"], X_va, val["y"], class_names, val)
        baseline_rows.append(row)
        cm_rows.extend(cm)
        cond_rows.extend(cond)
    write_csv(out_dir / "umich_v4_diagnostic_baselines.csv", baseline_rows)
    write_csv(out_dir / "umich_v4_diagnostic_baseline_confusions.csv", cm_rows)
    write_csv(out_dir / "umich_v4_diagnostic_baseline_per_condition.csv", cond_rows)

    exp_quad = Counter(r["quadrant"] for r in experiment_rows)
    active_quad = Counter()
    for row in raw_window_rows:
        if row["active_stage"]:
            active_quad[str(row["quadrant"])] += int(row["windows"])
    lines = [
        "# UMich v4 Learnability Audit",
        "",
        "## Scope",
        "",
        f"- Source audit NPZ: `{args.source_npz}`",
        f"- Clean inner-train NPZ: `{args.train_npz}`",
        f"- Clean inner-val NPZ: `{args.val_npz}`",
        "- No formal held-out test split is read.",
        "",
        "## Label Quadrants",
        "",
        f"- Experiment-level quadrants: `{dict(exp_quad)}`",
        f"- Active-stage window quadrants: `{dict(active_quad)}`",
        f"- All stage-contiguous windows before active-stage filter: `{before_windows}`",
        f"- Active-stage windows after cutting-only filter: `{active_windows}`",
        f"- Active-stage clean supervised windows: `{active_clean_windows}`",
        f"- Non-active or ambiguous windows removed before clean supervised learning: `{before_windows - active_clean_windows}`",
        "",
        "## Diagnostic Baselines",
        "",
        "| baseline | Acc | Macro-F1 | F1 unworn | F1 worn |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in baseline_rows:
        lines.append(
            f"| {row['baseline']} | {float(row['acc']):.4f} | {float(row['macro_f1']):.4f} | "
            f"{float(row.get('f1_unworn', 0.0)):.4f} | {float(row.get('f1_worn', 0.0)):.4f} |"
        )
    lines.extend(
        [
            "",
            "Interpretation rule: if metadata-only or stage-only is comparable to signal-only, the split is confounded and must not proceed directly to synthetic formal testing.",
        ]
    )
    (out_dir / "umich_v4_learnability_audit.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
