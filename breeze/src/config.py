"""BREEZE global configuration.

Parameter justifications (see PARAMS.md for full rationale):
- FS_RAW = 64 kHz: Paderborn (PU) acquisition rate.
- FS = 8 kHz (decimation factor 8, zero-phase FIR anti-aliased): keeps the
  0-4 kHz band which contains the dominant impact/resonance energy used by
  envelope analysis on PU, while making LLM text generation tractable.
- WIN = 2048 samples = 0.256 s: at N09 (900 rpm, fr = 15 Hz) this covers
  ~11.8 BPFO periods (BPFO ~ 46.1 Hz) and ~7.6 BPFI periods... enough cycles
  for a squared-envelope-spectrum peak test with ~3.9 Hz resolution, which
  resolves BPFO (46.1 Hz) vs BPFI (73.9 Hz) vs fr harmonics.
- Bearing 6203 geometry (PU documentation): 8 rolling elements,
  d = 6.75 mm, D = 29.05 mm, contact angle 0.
"""
import os
from pathlib import Path


ROOT = Path(os.environ.get(
    "BREEZE_ROOT",
    Path(__file__).resolve().parents[1],
)).resolve()
RAW_DIR = Path(os.environ.get("BREEZE_RAW_DIR", ROOT / "data" / "pu")).resolve()
RUNS_DIR = Path(os.environ.get("BREEZE_RUNS_DIR", ROOT / "runs")).resolve()
RESULTS_DIR = Path(os.environ.get("BREEZE_RESULTS_DIR", ROOT / "results")).resolve()
FIG_DIR = Path(os.environ.get("BREEZE_FIG_DIR", ROOT / "paper" / "figs")).resolve()


def _first_existing(*paths: Path) -> Path:
    for path in paths:
        if path.exists():
            return path
    return paths[0]


PROC_DIR = Path(os.environ.get(
    "BREEZE_PROC_DIR",
    _first_existing(ROOT / "proc", ROOT.parent / "proc", ROOT / "data" / "proc"),
)).resolve()

FS_RAW = 64_000
DECIM = 8
FS = FS_RAW // DECIM  # 8000 Hz
WIN = 2048            # 0.256 s
HOP = 2048            # non-overlapping windows (independence for statistics)

# Bearing 6203 kinematics (per PU dataset documentation)
N_BALLS = 8
BALL_D = 6.75e-3
PITCH_D = 29.05e-3
CONTACT_ANGLE = 0.0

def fault_freqs(fr_hz: float) -> dict:
    """Characteristic fault frequencies for bearing 6203 at shaft rate fr."""
    from kinematics import bearing_fault_freqs

    return bearing_fault_freqs(
        shaft_hz=fr_hz,
        n_balls=N_BALLS,
        ball_diameter=BALL_D,
        pitch_diameter=PITCH_D,
        contact_angle_deg=CONTACT_ANGLE,
    )

# Operating conditions: name -> (rpm, torque Nm, radial force N)
CONDITIONS = {
    "N09_M07_F10": (900, 0.7, 1000),
    "N15_M01_F10": (1500, 0.1, 1000),
    "N15_M07_F04": (1500, 0.7, 400),
    "N15_M07_F10": (1500, 0.7, 1000),
}
MAIN_COND = "N09_M07_F10"

# Classes and bearing-ID group split (real damages subset; no bearing overlap)
CLASSES = ["healthy", "OR", "IR"]
BEARINGS = {
    "healthy": ["K001", "K002", "K003", "K004", "K005"],
    "OR": ["KA04", "KA15", "KA16", "KA22", "KA30"],
    "IR": ["KI04", "KI14", "KI16", "KI17", "KI18", "KI21"],
}
SPLIT = {
    "train": {"healthy": ["K001", "K002", "K003"],
              "OR": ["KA04", "KA15", "KA16"],
              "IR": ["KI04", "KI14", "KI16", "KI17"]},
    "test": {"healthy": ["K004", "K005"],
             "OR": ["KA22", "KA30"],
             "IR": ["KI18", "KI21"]},
}
CHANNELS = ["vibration_1", "phase_current_1", "phase_current_2"]  # X, Y, Z

# LLM API
LLM_BASE_URL = "https://fufu.iqach.top/v1"
LLM_MODEL = "mimo-v2.5"
LLM_MIN_INTERVAL = 2.0  # seconds between requests (current provider limit)
