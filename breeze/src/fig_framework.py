"""Framework and responsibility-boundary diagrams for BREEZE."""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle

sys.path.insert(0, str(Path(__file__).parent))
from figure_style import PALETTE, apply_style, panel_label, save_figure


FIGS = Path(__file__).parent.parent / "paper" / "figs"


def _box(ax, x, y, w, h, title, lines=(), fc="#F6F8FB", ec="#3A3A3A",
         title_color="#272727", lw=0.9):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.035,rounding_size=0.055",
        fc=fc, ec=ec, lw=lw,
    ))
    ax.text(x + 0.12, y + h - 0.22, title, ha="left", va="top",
            fontsize=7.1, fontweight="bold", color=title_color)
    for i, line in enumerate(lines):
        ax.text(x + 0.12, y + h - 0.48 - i * 0.23, line, ha="left", va="top",
                fontsize=6.3, color=PALETTE["neutral_dark"])


def _arrow(ax, x1, y1, x2, y2, color="#333333", lw=1.0, ls="-",
           connectionstyle="arc3"):
    ax.add_patch(FancyArrowPatch(
        (x1, y1), (x2, y2),
        arrowstyle="-|>", mutation_scale=10,
        lw=lw, ls=ls, color=color,
        connectionstyle=connectionstyle,
    ))


def _mini_signal(ax, x, y, w, h, color):
    t = np.linspace(0, 1, 220)
    sig = 0.22 * np.sin(2 * np.pi * (6 * t + 0.4 * t**2))
    sig += 0.08 * np.sin(2 * np.pi * 31 * t)
    for loc in (0.18, 0.41, 0.66, 0.86):
        sig += 0.34 * np.exp(-((t - loc) / 0.014) ** 2)
    sig = sig / (np.max(np.abs(sig)) + 1e-12)
    ax.plot(x + t * w, y + h * (0.5 + 0.42 * sig), color=color, lw=0.8)
    ax.add_patch(Rectangle((x, y), w, h, fill=False, ec="#B0B0B0", lw=0.45))


def draw_framework():
    apply_style(7.2)
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.axis("off")

    panel_label(ax, "a", x=0.01, y=0.97)
    ax.text(0.32, 5.76, "Closed-loop physical-gate admission", ha="left",
            va="top", fontsize=9.0, fontweight="bold")

    phases = [
        ("1  LLM recipe",
         ["JSON recipe", "fault class + condition", "feedback-aware resampling"],
         0.25, 3.55, 2.05, 1.55, "#FBEAD8", PALETTE["orange"]),
        ("2  Renderer",
         ["fixed equations", "vibration + currents", "seeded waveform"],
         2.75, 3.55, 2.05, 1.55, "#F7F0DF", "#A56B25"),
        ("3  Verifier",
         ["format and legality", "statistics + PSD shape", "envelope and MCSA gates"],
         5.25, 3.55, 2.35, 1.55, "#EAF2FB", PALETTE["blue"]),
        ("4  Admitted pool",
         ["recipe + seed", "pass/fail report", "diversity check"],
         8.05, 3.55, 1.7, 1.55, "#EAF6EA", PALETTE["green"]),
    ]
    for title, lines, x, y, w, h, fc, ec in phases:
        _box(ax, x, y, w, h, title, lines, fc=fc, ec=ec, title_color=ec)
    for x1, x2 in [(2.3, 2.75), (4.8, 5.25), (7.6, 8.05)]:
        _arrow(ax, x1, 4.32, x2, 4.32)

    _mini_signal(ax, 3.08, 3.78, 1.35, 0.42, PALETTE["orange"])
    _mini_signal(ax, 8.24, 3.78, 1.12, 0.42, PALETTE["green"])

    _box(ax, 0.25, 1.55, 2.25, 1.15, "Real train split",
         ["file-level split", "quantiles from train only", "no test leakage"],
         fc="#F0F6EC", ec=PALETTE["green"], title_color=PALETTE["green"])
    _arrow(ax, 2.5, 2.12, 5.25, 3.77, color=PALETTE["green"], ls="--",
           connectionstyle="arc3,rad=-0.15")
    ax.text(3.68, 2.67, "thresholds", fontsize=6.2, color=PALETTE["green"],
            ha="center", va="center", rotation=18)

    _box(ax, 5.25, 1.25, 2.35, 1.25, "Structured rejection",
         ["failed gate", "measured value vs bound", "next prompt constraint"],
         fc="#FCE9E6", ec=PALETTE["rose"], title_color=PALETTE["rose"])
    _arrow(ax, 6.4, 3.55, 6.4, 2.5, color=PALETTE["rose"])
    _arrow(ax, 5.25, 1.86, 1.28, 3.55, color=PALETTE["rose"],
           connectionstyle="arc3,rad=0.24")
    ax.text(3.12, 2.62, "feedback <= K rounds", fontsize=6.2,
            color=PALETTE["rose"], rotation=18, ha="center")

    _box(ax, 8.05, 1.35, 1.7, 1.05, "Few-shot diagnosis",
         ["real + admitted windows", "compact 1-D CNN", "paired tests"],
         fc="#F1ECF7", ec=PALETTE["violet"], title_color=PALETTE["violet"])
    _arrow(ax, 8.9, 3.55, 8.9, 2.4)

    ax.text(0.3, 0.42,
            "BREEZE does not train the generator; it admits candidates that pass train-calibrated gates and records why rejected candidates fail.",
            fontsize=6.6, color=PALETTE["neutral_dark"], ha="left")
    save_figure(fig, FIGS / "framework.pdf")
    plt.close(fig)


def draw_boundary():
    apply_style(7.2)
    fig, ax = plt.subplots(figsize=(7.2, 3.1))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4.2)
    ax.axis("off")

    panel_label(ax, "a", x=0.01, y=0.96)
    ax.text(0.32, 4.02, "Recipe-renderer-verifier responsibility boundary",
            fontsize=9.0, fontweight="bold", ha="left", va="top")

    cols = [
        ("LLM", "Candidate recipe", ["impact rate", "amplitude envelope", "jitter", "band weights"],
         "#FBEAD8", PALETTE["orange"], 0.35),
        ("Renderer", "Waveform construction", ["impulse train", "colored noise", "current sidebands", "fixed equations"],
         "#F7F0DF", "#A56B25", 3.55),
        ("Verifier", "Admission report", ["format", "statistics + PSD", "envelope evidence", "diversity"],
         "#EAF2FB", PALETTE["blue"], 6.75),
    ]
    for title, subtitle, items, fc, ec, x in cols:
        _box(ax, x, 1.35, 2.55, 1.75, title, [subtitle] + items,
             fc=fc, ec=ec, title_color=ec)
    _arrow(ax, 2.9, 2.22, 3.55, 2.22)
    _arrow(ax, 6.1, 2.22, 6.75, 2.22)

    ax.text(1.62, 0.85, "stochastic proposal", ha="center", fontsize=6.3,
            color=PALETTE["neutral_dark"])
    ax.text(4.82, 0.85, "deterministic signal physics", ha="center", fontsize=6.3,
            color=PALETTE["neutral_dark"])
    ax.text(8.02, 0.85, "train-calibrated decision", ha="center", fontsize=6.3,
            color=PALETTE["neutral_dark"])

    ax.plot([3.18, 3.18], [0.55, 3.45], color=PALETTE["neutral_mid"], lw=0.8, ls="--")
    ax.plot([6.38, 6.38], [0.55, 3.45], color=PALETTE["neutral_mid"], lw=0.8, ls="--")
    ax.text(3.18, 0.34, "boundary 1", ha="center", fontsize=6.2, color=PALETTE["neutral_mid"])
    ax.text(6.38, 0.34, "boundary 2", ha="center", fontsize=6.2, color=PALETTE["neutral_mid"])
    ax.text(0.35, 0.12,
            "A verifier pass is an admissibility decision under training-set gates, not a formal proof of physical correctness.",
            ha="left", fontsize=6.4, color=PALETTE["rose"])
    save_figure(fig, FIGS / "responsibility_boundary.pdf")
    plt.close(fig)


def main():
    draw_framework()
    draw_boundary()
    print("framework.pdf saved")
    print("responsibility_boundary.pdf saved")


if __name__ == "__main__":
    main()
