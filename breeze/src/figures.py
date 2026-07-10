"""Publication figures for BREEZE.

Usage: python figures.py [--only fig_name ...]
Figures are written to paper/figs/ as PDF, SVG, PNG, and TIFF.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from config import (CLASSES, CONDITIONS, FIG_DIR, FS, MAIN_COND, RESULTS_DIR,
                    RUNS_DIR, fault_freqs)
from data import load_file_split
from figure_style import METHOD_COLORS, PALETTE, apply_style, panel_label, save_figure
from pools import build_pool
from verifier.features import envelope_spectrum, time_stats
from verifier.verifier import BreezeVerifier


FIGS = FIG_DIR
FIGS.mkdir(parents=True, exist_ok=True)
RESULTS = RESULTS_DIR
PHYS_RUN = RUNS_DIR / "pool_physics_file_k3"
DOWNSTREAM_CSV = RESULTS / "downstream_file.csv"
CUSTOM_EVAL_CSV = RESULTS / "custom_pool_eval.csv"
V2_POOL = RUNS_DIR / "rescreen_v2_full" / "pool_v2.npz"

CLS_NAME = {"healthy": "Healthy", "OR": "Outer race", "IR": "Inner race"}
POOL_LABELS = {
    "open_loop_basic": "Open-loop basic",
    "open_loop_phys": "Physics-guided",
    "stats_only": "Stats filter",
    "envelope_only": "Envelope filter",
    "breeze_k0": "BREEZE K=0",
    "breeze_k1": "BREEZE K=1",
    "breeze_k2": "BREEZE K=2",
    "breeze_k3": "BREEZE K=3",
    "breeze_v2_full": "BREEZE v2",
}


def _v2_pool() -> tuple[np.ndarray, np.ndarray] | None:
    if not V2_POOL.exists():
        return None
    d = np.load(V2_POOL)
    return d["X"].astype(np.float32), d["y"].astype(np.int64)


def _fft_spectrum(x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    y = np.asarray(x, dtype=float)
    y = y - y.mean()
    win = np.hanning(len(y))
    mag = np.abs(np.fft.rfft(y * win))
    f = np.fft.rfftfreq(len(y), d=1.0 / FS)
    return f, mag


def _norm(y: np.ndarray) -> np.ndarray:
    return y / (np.max(np.abs(y)) + 1e-12)


def _draw_fault_refs(ax, cls: str, freqs: dict, ymax: float = 1.0) -> None:
    refs = [("BPFO", "--"), ("BPFI", ":")]
    for key, ls in refs:
        is_target = (cls == "OR" and key == "BPFO") or (cls == "IR" and key == "BPFI")
        ax.axvline(
            freqs[key],
            color=PALETTE["rose"] if is_target else PALETTE["neutral_mid"],
            lw=0.85 if is_target else 0.65,
            ls=ls,
            alpha=0.9 if is_target else 0.65,
        )
    if cls in ("OR", "IR"):
        key = "BPFO" if cls == "OR" else "BPFI"
        ax.text(freqs[key], ymax * 0.92, key, rotation=90, ha="right", va="top",
                fontsize=5.8, color=PALETTE["rose"])


def fig_waveforms() -> None:
    """Real vs BREEZE-admitted synthetic examples in time/FFT/envelope domains."""
    apply_style(7.0)
    verifier = BreezeVerifier.load(RUNS_DIR / f"verifier_{MAIN_COND}_file_c90.json")
    freqs = fault_freqs(CONDITIONS[MAIN_COND][0] / 60.0)
    pool = _v2_pool()
    if pool is None:
        Xs, ys = build_pool(PHYS_RUN, "breeze", k=3)
        syn_label = "BREEZE K=3"
    else:
        Xs, ys = pool
        syn_label = "BREEZE v2"
    Xr, yr, _ = load_file_split("train", MAIN_COND)

    fig, axes = plt.subplots(3, 3, figsize=(7.2, 5.0), sharex=False)
    sample_n = 1024
    t_left = np.arange(sample_n) / FS * 1000
    t_right = (np.arange(sample_n) + sample_n) / FS * 1000
    split_ms = sample_n / FS * 1000

    for col, cls in enumerate(CLASSES):
        ci = CLASSES.index(cls)
        real_windows = Xr[yr == ci]
        syn_windows = Xs[ys == ci]
        if len(real_windows) == 0 or len(syn_windows) == 0:
            raise RuntimeError(f"Missing real or synthetic windows for {cls}")
        wr = real_windows[min(3, len(real_windows) - 1)]
        ws = syn_windows[0]
        band = tuple(verifier.calib[cls]["band"])

        ax = axes[0, col]
        scale = max(np.max(np.abs(wr[0, :sample_n])), np.max(np.abs(ws[0, :sample_n])), 1e-12)
        ax.plot(t_left, wr[0, :sample_n] / scale, color=PALETTE["blue"], lw=0.55)
        ax.plot(t_right, ws[0, :sample_n] / scale, color=PALETTE["orange"], lw=0.55)
        ax.axvline(split_ms, color=PALETTE["neutral_mid"], lw=0.65, ls="--")
        ax.set_xlim(0, 2 * split_ms)
        ax.set_ylim(-1.1, 1.1)
        ax.set_title(CLS_NAME[cls], fontsize=7.8)
        if col == 0:
            ax.set_ylabel("Time\nnorm. amp.")
        if col == 2:
            ax.plot([], [], color=PALETTE["blue"], lw=1.0, label="Real")
            ax.plot([], [], color=PALETTE["orange"], lw=1.0, label=syn_label)
            ax.legend(loc="upper right", fontsize=5.8)
        ax.text(split_ms * 0.5, -1.0, "Real", ha="center", va="bottom",
                fontsize=5.8, color=PALETTE["blue"])
        ax.text(split_ms * 1.5, -1.0, "Admitted", ha="center", va="bottom",
                fontsize=5.8, color=PALETTE["orange"])

        ax = axes[1, col]
        fr, mr = _fft_spectrum(wr[0])
        fsyn, msyn = _fft_spectrum(ws[0])
        m = fr <= 1000
        ax.plot(fr[m], _norm(mr[m]), color=PALETTE["blue"], lw=0.7)
        ax.plot(fsyn[m], _norm(msyn[m]), color=PALETTE["orange"], lw=0.7, alpha=0.9)
        ax.set_xlim(0, 1000)
        ax.set_ylim(0, 1.05)
        if col == 0:
            ax.set_ylabel("FFT\nnorm. mag.")

        ax = axes[2, col]
        fer, ser = envelope_spectrum(wr[0], FS, band)
        fes, ses = envelope_spectrum(ws[0], FS, band)
        m = fer <= 200
        ax.plot(fer[m], _norm(ser[m]), color=PALETTE["blue"], lw=0.75)
        ax.plot(fes[m], _norm(ses[m]), color=PALETTE["orange"], lw=0.75, alpha=0.9)
        _draw_fault_refs(ax, cls, freqs, ymax=1.0)
        ax.set_xlim(0, 200)
        ax.set_ylim(0, 1.05)
        ax.set_xlabel("Frequency [Hz]")
        if col == 0:
            ax.set_ylabel("Envelope\nnorm. mag.")

    panel_label(axes[0, 0], "a", x=-0.28)
    panel_label(axes[1, 0], "b", x=-0.28)
    panel_label(axes[2, 0], "c", x=-0.28)
    fig.tight_layout(h_pad=0.65, w_pad=0.8)
    save_figure(fig, FIGS / "waveforms.pdf")
    plt.close(fig)


def fig_boxplots() -> None:
    """RMS and kurtosis distributions for real and synthetic pools."""
    import pandas as pd  # noqa: F401

    apply_style(7.0)
    Xr, yr, _ = load_file_split("train", MAIN_COND)
    pools = [("Real", None)]
    for nm, mode, k in [("Physics", "open_loop_phys", 3),
                        ("Envelope", "envelope_only", 3),
                        ("K=3", "breeze", 3)]:
        X, y = build_pool(PHYS_RUN, mode, k=k)
        pools.append((nm, (X, y)))
    v2 = _v2_pool()
    if v2 is not None:
        pools.append(("v2", v2))

    colors = [PALETTE["neutral_soft"], PALETTE["green_soft"], "#CFE4E4",
              PALETTE["blue_soft"], PALETTE["rose_soft"]]
    fig, axes = plt.subplots(2, 3, figsize=(7.2, 3.55), sharex=True)
    rng = np.random.default_rng(0)
    for col, cls in enumerate(CLASSES):
        ci = CLASSES.index(cls)
        for row, stat in enumerate(["rms", "kurtosis"]):
            data, labels = [], []
            for nm, p in pools:
                if p is None:
                    W = Xr[yr == ci]
                    W = W[rng.choice(len(W), min(180, len(W)), replace=False)]
                else:
                    W = p[0][p[1] == ci]
                if len(W) == 0:
                    continue
                data.append([time_stats(w[0])[stat] for w in W])
                labels.append(nm)
            ax = axes[row, col]
            bp = ax.boxplot(data, tick_labels=labels, showfliers=False,
                            widths=0.55, patch_artist=True,
                            medianprops={"color": PALETTE["neutral_dark"], "lw": 0.9},
                            whiskerprops={"lw": 0.7}, capprops={"lw": 0.7})
            for pa, color in zip(bp["boxes"], colors):
                pa.set_facecolor(color)
                pa.set_edgecolor(PALETTE["neutral_dark"])
                pa.set_alpha(0.95)
            if row == 0:
                ax.set_title(CLS_NAME[cls], fontsize=7.8)
            if col == 0:
                ax.set_ylabel("RMS" if stat == "rms" else "Kurtosis")
            ax.tick_params(axis="x", rotation=25, labelsize=5.8)
    panel_label(axes[0, 0], "a", x=-0.28)
    panel_label(axes[1, 0], "b", x=-0.28)
    fig.tight_layout(h_pad=0.7, w_pad=0.8)
    save_figure(fig, FIGS / "boxplots.pdf")
    plt.close(fig)


def fig_metric_distances() -> None:
    """MMD2 and nearest-neighbour diversity ratio by pool and class."""
    import pandas as pd

    apply_style(7.0)
    parts = []
    for rel in ["pool_metrics.csv", "pool_metrics_v2.csv"]:
        p = RESULTS / rel
        if p.exists():
            parts.append(pd.read_csv(p))
    if not parts:
        raise RuntimeError("No pool metric CSV files found")
    d = pd.concat(parts, ignore_index=True)
    order = ["open_loop_basic", "open_loop_phys", "envelope_only", "breeze_k3", "breeze_v2_full"]
    d = d[d["pool"].isin(order)].copy()
    if d.empty:
        raise RuntimeError("Selected pools not found in metric CSV files")
    d["nn_ratio"] = d["nn_div"] / d["nn_div_real"]

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.65), sharex=False)
    x = np.arange(len(CLASSES))
    width = 0.78 / len(order)
    for i, pool in enumerate(order):
        sub = d[d.pool == pool].set_index("class")
        if sub.empty:
            continue
        offset = (i - (len(order) - 1) / 2) * width
        vals = [sub.loc[c, "mmd2"] if c in sub.index else np.nan for c in CLASSES]
        ratios = [sub.loc[c, "nn_ratio"] if c in sub.index else np.nan for c in CLASSES]
        color = METHOD_COLORS.get(pool, PALETTE["neutral_soft"])
        axes[0].bar(x + offset, vals, width=width, color=color, edgecolor="black",
                    linewidth=0.45, label=POOL_LABELS.get(pool, pool))
        axes[1].bar(x + offset, ratios, width=width, color=color, edgecolor="black",
                    linewidth=0.45)

    for ax in axes:
        ax.set_xticks(x)
        ax.set_xticklabels([CLS_NAME[c] for c in CLASSES])
        ax.tick_params(axis="x", labelsize=6.3)
    axes[0].set_ylabel("MMD2\n(lower is closer)")
    axes[1].set_ylabel("NN diversity / real NN")
    axes[1].axhline(1.0, color=PALETTE["neutral_mid"], lw=0.75, ls="--")
    axes[0].legend(loc="upper center", bbox_to_anchor=(1.04, 1.28),
                   ncol=3, fontsize=5.9, handlelength=1.1)
    panel_label(axes[0], "a")
    panel_label(axes[1], "b")
    fig.tight_layout(w_pad=1.0)
    save_figure(fig, FIGS / "metric_distances.pdf")
    plt.close(fig)


def fig_acceptance() -> None:
    """Acceptance, cost, and downstream accuracy vs feedback rounds."""
    import pandas as pd

    apply_style(7.0)
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.35))
    if (RESULTS / "acceptance.csv").exists():
        d = pd.read_csv(RESULTS / "acceptance.csv")
        axes[0].plot(d.K, d.acceptance * 100, "o-", color=PALETTE["blue"],
                     ms=3.2, lw=1.1)
        axes[0].set_xlabel("Feedback rounds K")
        axes[0].set_ylabel("Acceptance [%]")
        axes[0].set_xticks(d.K)
        axes[1].plot(d.K, d.mean_llm_calls, "s-", color=PALETTE["orange"],
                     ms=3.2, lw=1.1)
        axes[1].set_xlabel("Feedback rounds K")
        axes[1].set_ylabel("Mean LLM calls / slot")
        axes[1].set_xticks(d.K)
    if DOWNSTREAM_CSV.exists():
        d = pd.read_csv(DOWNSTREAM_CSV)
        d = d[d.baseline.str.startswith("breeze_k")]
        colors = [PALETTE["green"], PALETTE["blue_mid"], PALETTE["rose"]]
        for nr, color in zip(sorted(d.n_real.unique()), colors):
            grouped = d[d.n_real == nr].groupby("baseline")["acc"].agg(["mean", "std"])
            ks = np.array([int(b.split("breeze_k")[-1]) for b in grouped.index])
            order = np.argsort(ks)
            axes[2].errorbar(
                ks[order],
                grouped["mean"].values[order] * 100,
                yerr=grouped["std"].values[order] * 100,
                marker="o", ms=3.0, capsize=2.2, lw=1.0,
                color=color, label=f"{nr}/class",
            )
        axes[2].set_xlabel("Feedback rounds K")
        axes[2].set_ylabel("Test accuracy [%]")
        axes[2].legend(fontsize=5.8, loc="lower right")
    for label, ax in zip("abc", axes):
        panel_label(ax, label)
    fig.tight_layout(w_pad=0.9)
    save_figure(fig, FIGS / "acceptance_k.pdf")
    plt.close(fig)


def fig_failure_reasons() -> None:
    """Rejected-slot failure reason breakdown and slot/window mapping."""
    import pandas as pd

    apply_style(7.0)
    fail_path = RESULTS / "revision_v2_rejected_slot_fail_reasons.csv"
    map_path = RESULTS / "revision_v2_slot_window_mapping.csv"
    if not fail_path.exists() or not map_path.exists():
        raise RuntimeError("v2 failure-reason or slot-window mapping CSV is missing")
    fail = pd.read_csv(fail_path)
    mapping = pd.read_csv(map_path)
    gates = sorted(fail["gate"].unique())
    classes = CLASSES
    gate_colors = {
        "stats_union": PALETTE["rose"],
        "soft_spectrum": PALETTE["orange"],
        "envelope_multi": PALETTE["blue_mid"],
        "psd_w1": PALETTE["teal"],
        "vector_mcsa": PALETTE["violet"],
        "sanity": PALETTE["neutral_mid"],
    }

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.75), gridspec_kw={"width_ratios": [1.35, 1.0]})
    ax = axes[0]
    y = np.arange(len(classes))
    left = np.zeros(len(classes))
    for gate in gates:
        vals = []
        for cls in classes:
            sub = fail[(fail["class"] == cls) & (fail["gate"] == gate)]
            vals.append(float(sub["count"].sum()) if not sub.empty else 0.0)
        ax.barh(y, vals, left=left, color=gate_colors.get(gate, PALETTE["neutral_soft"]),
                edgecolor="black", linewidth=0.45, label=gate.replace("_", " "))
        left += np.asarray(vals)
    ax.set_yticks(y)
    ax.set_yticklabels([CLS_NAME[c] for c in classes])
    ax.invert_yaxis()
    ax.set_xlabel("Terminal rejected-slot gate failures")
    ax.legend(fontsize=5.8, loc="lower right")
    panel_label(ax, "a")

    ax = axes[1]
    m = mapping[mapping["block"].isin(classes)].set_index("block")
    metrics = ["accepted_slots_before_diversity", "kept_after_diversity", "few_shot_cap_windows"]
    labels = ["Accepted slots", "Kept windows", "Few-shot cap"]
    x = np.arange(len(classes))
    width = 0.25
    colors = [PALETTE["blue_soft"], PALETTE["blue"], PALETTE["rose"]]
    for i, (metric, label, color) in enumerate(zip(metrics, labels, colors)):
        vals = [m.loc[c, metric] for c in classes]
        ax.bar(x + (i - 1) * width, vals, width=width, color=color,
               edgecolor="black", linewidth=0.45, label=label)
    ax.set_xticks(x)
    ax.set_xticklabels([CLS_NAME[c] for c in classes], rotation=20, ha="right")
    ax.set_ylabel("Count")
    ax.legend(fontsize=5.8, loc="upper left")
    panel_label(ax, "b")
    fig.tight_layout(w_pad=1.1)
    save_figure(fig, FIGS / "failure_reasons.pdf")
    plt.close(fig)


def fig_failure_case() -> None:
    """A concrete rejected healthy candidate with forbidden fault-frequency evidence."""

    apply_style(7.0)
    record_path = RUNS_DIR / "rescreen_v2_full" / "records" / "healthy_0013.json"
    if not record_path.exists():
        raise RuntimeError(f"Missing failure-case record: {record_path}")
    record = json.loads(record_path.read_text())
    candidates = [
        c for c in record.get("candidates", [])
        if c.get("gates", {}).get("envelope_multi") is False
    ]
    if not candidates:
        raise RuntimeError("Selected failure-case record has no envelope_multi failure")
    candidate = candidates[0]
    signal_path = Path(candidate["path"])
    if not signal_path.exists():
        raise RuntimeError(f"Missing failure-case waveform: {signal_path}")
    x = np.load(signal_path).astype(float)
    vib = x[0] if x.ndim == 2 else x
    freqs = fault_freqs(CONDITIONS[MAIN_COND][0] / 60.0)

    ir_scores = [s for s in candidate["scores"]["envelope_multi"] if s.get("fault") == "IR"]
    if not ir_scores:
        raise RuntimeError("Failure-case record does not contain IR envelope scores")
    dominant = max(ir_scores, key=lambda s: s["fund_prominence"] / max(s["prom_max"], 1e-12))
    band = tuple(dominant["band"])
    f_env, s_env = envelope_spectrum(vib, FS, band)

    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.45),
                             gridspec_kw={"width_ratios": [1.1, 1.15, 1.0]})

    ax = axes[0]
    t = np.arange(len(vib)) / FS * 1000
    ax.plot(t, _norm(vib), color=PALETTE["rose"], lw=0.65)
    ax.set_xlabel("Time [ms]")
    ax.set_ylabel("Normalized amplitude")
    ax.set_title("Rejected healthy candidate", fontsize=7.6)
    ax.text(0.02, 0.92, "healthy slot 13, round 0", transform=ax.transAxes,
            ha="left", va="top", fontsize=5.9, color=PALETTE["neutral_dark"])
    panel_label(ax, "a")

    ax = axes[1]
    m = f_env <= 200
    ax.plot(f_env[m], _norm(s_env[m]), color=PALETTE["rose"], lw=0.85)
    ax.axvline(freqs["BPFI"], color=PALETTE["rose"], lw=0.9, ls="--")
    ax.text(freqs["BPFI"], 0.96, "BPFI", rotation=90, ha="right", va="top",
            fontsize=5.8, color=PALETTE["rose"])
    ax.set_xlim(0, 200)
    ax.set_ylim(0, 1.05)
    ax.set_xlabel("Frequency [Hz]")
    ax.set_ylabel("Envelope norm. mag.")
    ax.set_title(f"Forbidden IR evidence, band {int(band[0])}-{int(band[1])} Hz",
                 fontsize=7.4)
    panel_label(ax, "b")

    ax = axes[2]
    labels = [f"{int(s['band'][0])}-{int(s['band'][1])}" for s in ir_scores]
    observed = np.array([s["fund_prominence"] for s in ir_scores], dtype=float)
    limits = np.array([s["prom_max"] for s in ir_scores], dtype=float)
    y = np.arange(len(labels))
    ax.barh(y - 0.16, observed, height=0.28, color=PALETTE["rose"],
            edgecolor="black", linewidth=0.45, label="Observed")
    ax.barh(y + 0.16, limits, height=0.28, color=PALETTE["neutral_soft"],
            edgecolor="black", linewidth=0.45, label="Healthy max")
    for yi, obs, lim in zip(y, observed, limits):
        if obs > lim:
            ax.text(max(obs, lim) + 0.08, yi - 0.16, "reject", va="center",
                    ha="left", fontsize=5.7, color=PALETTE["rose"])
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xlabel("Envelope peak prominence")
    ax.set_title("Gate report values", fontsize=7.6)
    ax.legend(fontsize=5.8, loc="lower right")
    panel_label(ax, "c")

    fig.tight_layout(w_pad=0.85)
    save_figure(fig, FIGS / "failure_case.pdf")
    plt.close(fig)


def fig_downstream() -> None:
    """Horizontal bar chart of selected downstream baselines."""
    import pandas as pd

    apply_style(7.0)
    d = pd.read_csv(DOWNSTREAM_CSV)
    order = ["real_only", "noise_aug", "vae", "gan", "open_loop_basic",
             "open_loop_phys", "stats_only", "envelope_only",
             "breeze_k0", "breeze_k3"]
    names = ["Real only", "Noise aug.", "VAE", "GAN", "Open-loop LLM",
             "Physics-guided", "Stats filter", "Envelope filter",
             "BREEZE K=0", "BREEZE K=3"]
    if CUSTOM_EVAL_CSV.exists():
        v2 = pd.read_csv(CUSTOM_EVAL_CSV)
        v2 = v2[v2.baseline == "breeze_v2_full"][["baseline", "n_real", "seed", "n_syn", "acc"]]
        d = pd.concat([d[["baseline", "n_real", "seed", "n_syn", "acc"]], v2], ignore_index=True)
        order.append("breeze_v2_full")
        names.append("BREEZE v2")

    fig, axes = plt.subplots(1, 3, figsize=(7.2, 3.35), sharey=True)
    y_pos = np.arange(len(order))
    colors = [METHOD_COLORS.get(b, PALETTE["neutral_soft"]) for b in order]
    for ax, nr in zip(axes, sorted(d.n_real.unique())):
        dd = d[d.n_real == nr]
        mus, sds = [], []
        for b in order:
            vals = dd[dd.baseline == b]["acc"]
            mus.append(vals.mean() * 100 if len(vals) else np.nan)
            sds.append(vals.std() * 100 if len(vals) else np.nan)
        ax.barh(y_pos, mus, xerr=sds, capsize=2.2,
                color=colors, edgecolor="black", linewidth=0.45, height=0.68)
        ax.set_yticks(y_pos)
        ax.set_xlim(35, 90)
        ax.set_xlabel("Accuracy [%]")
        ax.set_title(f"{nr} real windows/class", fontsize=7.6)
        ax.axvline(np.nanmean(mus), color=PALETTE["neutral_mid"], lw=0.55, ls=":")
    axes[0].set_yticklabels(names, fontsize=6.1)
    for ax in axes[1:]:
        ax.tick_params(axis="y", labelleft=False)
    axes[0].invert_yaxis()
    for label, ax in zip("abc", axes):
        panel_label(ax, label)
    fig.tight_layout(w_pad=0.85)
    save_figure(fig, FIGS / "downstream_bars.pdf")
    plt.close(fig)


def fig_cross_condition() -> None:
    """PU cross-condition verifier pass-rate heatmap."""
    import pandas as pd

    apply_style(7.0)
    p = RESULTS / "cross_condition_verifier_full.csv"
    if not p.exists():
        raise RuntimeError("cross_condition_verifier_full.csv is missing")
    d = pd.read_csv(p)
    conds = sorted(d["cond"].unique())
    classes = CLASSES
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.85), sharey=True,
                             constrained_layout=True)
    for ax, split, label in zip(axes, ["train", "test"], ["a", "b"]):
        mat = np.full((len(conds), len(classes)), np.nan)
        for i, cond in enumerate(conds):
            for j, cls in enumerate(classes):
                sub = d[(d.cond == cond) & (d.split == split) & (d["class"] == cls)]
                if not sub.empty:
                    mat[i, j] = sub["pass_rate"].iloc[0]
        im = ax.imshow(mat, vmin=0.6, vmax=1.0, cmap="Blues", aspect="auto")
        ax.set_xticks(np.arange(len(classes)))
        ax.set_xticklabels([CLS_NAME[c] for c in classes], rotation=20, ha="right")
        ax.set_yticks(np.arange(len(conds)))
        ax.set_yticklabels([c.replace("_", " ") for c in conds])
        ax.set_title(f"{split.capitalize()} pass rate", fontsize=7.7)
        for i in range(mat.shape[0]):
            for j in range(mat.shape[1]):
                val = mat[i, j]
                if np.isfinite(val):
                    ax.text(j, i, f"{val:.2f}", ha="center", va="center",
                            fontsize=6.1, color="white" if val > 0.82 else PALETTE["neutral_dark"])
        panel_label(ax, label)
    cbar = fig.colorbar(im, ax=axes.ravel().tolist(), shrink=0.86, pad=0.025)
    cbar.set_label("Pass rate", fontsize=6.5)
    cbar.ax.tick_params(labelsize=6.0)
    save_figure(fig, FIGS / "cross_condition_heatmap.pdf")
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="+", default=None)
    args = ap.parse_args()
    figs = {
        "waveforms": fig_waveforms,
        "boxplots": fig_boxplots,
        "metrics": fig_metric_distances,
        "acceptance": fig_acceptance,
        "failure": fig_failure_reasons,
        "failure_case": fig_failure_case,
        "downstream": fig_downstream,
        "cross_condition": fig_cross_condition,
    }
    for name, fn in figs.items():
        if args.only and name not in args.only:
            continue
        fn()
        print(name, "ok", flush=True)


if __name__ == "__main__":
    main()
