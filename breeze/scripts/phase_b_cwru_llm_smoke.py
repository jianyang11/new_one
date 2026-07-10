"""CWRU LLM recipe smoke under the Phase-B verifier.

Small-batch validation only: by default this script requests 5 recipes per
class (20 API requests if every call succeeds), renders each recipe with
multiple seeds, and admits only verifier-passing signals. It is checkpointed at
the slot JSON level, so reruns skip completed slots without additional API use.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import requests
from scipy.signal import find_peaks


ROOT = Path(__file__).resolve().parents[2]
BREEZE = ROOT / "breeze"
RUNS = BREEZE / "runs"
RESULTS = BREEZE / "results"
SCRIPTS = BREEZE / "scripts"
sys.path.insert(0, str(SCRIPTS))

from phase_b_cwru_recipe_smoke import (  # noqa: E402
    BANDS,
    CWRU_CLASSES,
    FS,
    WIN,
    CwruVerifier,
    build_profiles,
    psd,
    render,
    stable_seed,
    target_freq,
)


DEFAULT_ENDPOINT = "https://fufu.iqach.top/v1/chat/completions"
DEFAULT_MODEL = "mimo-v2.5"
API_LOG = RESULTS / "phaseB_api_usage_log.csv"


def _round_list(values: list[float], ndigits: int = 6) -> list[float]:
    return [round(float(v), ndigits) for v in values]


def schema_text() -> str:
    bands = ", ".join([f"{int(lo)}-{int(hi)} Hz" for lo, hi in BANDS])
    return (
        "{\n"
        '  "fr_hz": <shaft frequency Hz, use the provided value>,\n'
        '  "target_rms": <overall RMS, within the train-supported q05-q95 range>,\n'
        '  "impacts": {\n'
        '    "rate_hz": <0 for healthy, otherwise the target fault frequency>,\n'
        '    "amp": <impact amplitude in signal units; 0 for healthy>,\n'
        '    "decay_ms": <exponential decay time, 0.4-5.0>,\n'
        '    "resonance_hz": <excited resonance, 500-5500>,\n'
        '    "jitter_pct": <cycle jitter percent, 0-6>,\n'
        '    "amp_var_pct": <impact-to-impact amplitude variation percent, 0-45>,\n'
        '    "modulation": {"type": "none"|"shaft"|"cage", "depth": <0-0.9>}\n'
        "  },\n"
        '  "background": {\n'
        '    "noise_rms": <broadband background RMS>,\n'
        f'    "band_weights": <exactly {len(BANDS)} nonnegative weights for bands [{bands}]>,\n'
        '    "components": [{"freq_hz": <running component Hz>, "amp": <amplitude>}],\n'
        '    "random_impulses": {"rate_hz": <nonperiodic transient rate>, "amp": <amplitude>, "decay_ms": <0.4-3.0>, "resonance_hz": <500-5500>}\n'
        "  }\n"
        "}"
    )


def system_prompt() -> str:
    return (
        "You are an expert in rolling-element bearing vibration analysis. "
        "Design physically plausible parameter recipes for a deterministic "
        "CWRU drive-end bearing signal renderer. Signals are sampled at "
        f"{FS} Hz with window length {WIN}. Respond only with one valid JSON "
        "object matching the requested schema; no markdown, no comments."
    )


def component_anchors(X: np.ndarray, y: np.ndarray, max_components: int = 30) -> dict[str, list[dict[str, float]]]:
    anchors: dict[str, list[dict[str, float]]] = {}
    for ci, cls in enumerate(CWRU_CLASSES):
        W = X[y == ci]
        f, _ = psd(W[0, 0])
        psds = np.asarray([psd(w[0])[1] for w in W[: min(len(W), 600)]])
        mean_psd = np.mean(psds, axis=0)
        peaks, _ = find_peaks(np.log10(mean_psd + 1e-18), prominence=0.05)
        idx = [int(i) for i in peaks if 5.0 <= f[i] <= FS / 2 - 50]
        idx = sorted(idx, key=lambda i: -mean_psd[i])
        selected: list[int] = []
        for i in idx:
            if all(abs(float(f[i] - f[j])) >= 30.0 for j in selected):
                selected.append(i)
            if len(selected) >= max_components:
                break
        if len(selected) < max_components:
            for i in np.argsort(mean_psd)[::-1]:
                i = int(i)
                if 5.0 <= f[i] <= FS / 2 - 50 and all(abs(float(f[i] - f[j])) >= 30.0 for j in selected):
                    selected.append(i)
                if len(selected) >= max_components:
                    break
        df = float(f[1] - f[0])
        anchors[cls] = [
            {
                "freq_hz": round(float(f[i]), 4),
                "amp": round(float(np.sqrt(4 * mean_psd[i] * df)), 8),
            }
            for i in selected
        ]
    return anchors


def user_prompt(
    cls: str,
    profile: Any,
    meta: dict[str, Any],
    slot: int,
    anchors: list[dict[str, float]],
    healthy_anchor_count: int,
    fault_quality_targets: bool,
) -> str:
    fr_hz = float(meta["fr_hz"])
    if cls == "healthy":
        class_goal = (
            "HEALTHY bearing: no periodic bearing-fault impacts. Set "
            "impacts.rate_hz=0 and impacts.amp=0. Use broadband vibration, "
            "running-speed components, and at most weak nonperiodic transients."
        )
        target_hz = 0.0
        modulation = "none"
    else:
        target_hz = target_freq(cls, fr_hz)
        long_name = {"IR": "INNER-RACE", "B": "BALL", "OR": "OUTER-RACE"}[cls]
        modulation = {"IR": "shaft", "B": "cage", "OR": "none"}[cls]
        class_goal = (
            f"{long_name} fault: periodic impacts at {target_hz:.3f} Hz. "
            f"Use modulation.type={modulation}; for OR use depth 0 or very "
            "small, for IR/B use physically moderate modulation."
        )
    profile_summary = {
        "rms_q05": round(profile.rms_q05, 8),
        "rms_q50": round(profile.rms_q50, 8),
        "rms_q95": round(profile.rms_q95, 8),
        "peak_q50": round(profile.peak_q50, 8),
        "kurtosis_q50": round(profile.kurtosis_q50, 6),
        "band_median": _round_list(profile.band_median),
        "running_components": [
            {"freq_hz": round(float(c["freq_hz"]), 4), "amp": round(float(c["amp"]), 8)}
            for c in profile.components
        ],
        "resonance_bands": [
            [round(float(lo), 2), round(float(hi), 2)] for lo, hi in profile.resonance_bands
        ],
        "component_anchors_full_band": anchors[:healthy_anchor_count if cls == "healthy" else 12],
    }
    constraints = [
        f"Use fr_hz={fr_hz:.6f} and do not invent another shaft speed.",
        f"target_rms must stay between {profile.rms_q05:.8g} and {profile.rms_q95:.8g}.",
        f"band_weights must contain exactly {len(BANDS)} values and should remain close to the train-supported band_median without copying it exactly.",
        "Do not output arrays other than band_weights and components.",
        "Do not include psd_template_amp or any waveform/template field.",
    ]
    if cls != "healthy":
        constraints.append(f"impacts.rate_hz should be {target_hz:.6f} Hz.")
        if profile.resonance_bands:
            constraints.append(
                "Choose impacts.resonance_hz inside one of the train-supported "
                f"resonance bands: {profile_summary['resonance_bands']}."
            )
        if fault_quality_targets:
            constraints.extend(
                [
                    f"Use target_rms close to the class median {profile.rms_q50:.8g}; do not choose a high-RMS edge case.",
                    "Use lower broadband background noise, about 0.05-0.18 times target_rms, so periodic impacts remain visible.",
                    "Make fault impacts sharper and more diagnostic than generic broadband vibration: use impact amplitude about 2.5-5.0 times target_rms and decay_ms about 0.6-2.2.",
                    "Aim for clear envelope prominence at the fault rate while keeping time statistics train-supported.",
                    "Avoid smooth low-kurtosis fault recipes and avoid inflating target_rms to compensate for weak impacts.",
                ]
            )
    else:
        if healthy_anchor_count <= 10:
            constraints.extend(
                [
                    f"Use exactly {healthy_anchor_count} background.components, one for each component_anchors_full_band item.",
                    "Keep component amplitudes close to the listed amp values, varying each by at most about 25%.",
                    "Return compact JSON; do not pretty-print or add extra whitespace.",
                ]
            )
        else:
            constraints.append(
                "Use 20 to 30 background.components chosen from component_anchors_full_band, with amplitudes varied moderately around the listed amp values."
            )
        constraints.extend(
            [
                "Include the dominant anchors near 1031.25, 164.0625, 93.75, 2109.375, and 351.5625 Hz when they are present.",
                "Set background.random_impulses.rate_hz=0 and background.random_impulses.amp=0 for healthy.",
                "Set background.noise_rms to roughly 0.2-0.6 times target_rms; the narrowband components should carry the healthy spectral lines.",
                "Avoid a purely broadband healthy recipe; broad band weights alone are not enough to match the train-supported CWRU healthy PSD.",
            ]
        )
    return (
        f"Dataset: CWRU 12 kHz drive-end bearing split within_load0.\n"
        "Bearing: 6205-2RS JEM SKF drive-end; frequency multipliers are "
        "BPFI=5.4152*fr, BSF=4.7135*fr, BPFO=3.5848*fr, FTF=0.39828*fr.\n"
        f"Class request: {class_goal}\n"
        f"Slot index: {slot}; make this recipe distinct from nearby slots while "
        "staying inside the stated physical and train-supported ranges.\n\n"
        "Train-supported profile for this class:\n"
        + json.dumps(profile_summary, indent=2)
        + "\n\nHard constraints:\n- "
        + "\n- ".join(constraints)
        + "\n\nReturn exactly this JSON schema:\n"
        + schema_text()
    )


def extract_json(text: str) -> dict[str, Any] | None:
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        return None
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def validate_recipe(recipe: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    try:
        bg = recipe["background"]
        imp = recipe["impacts"]
    except KeyError as exc:
        return [f"missing key {exc}"]
    for key in ("fr_hz", "target_rms"):
        if key not in recipe:
            problems.append(f"missing {key}")
    for key in ("rate_hz", "amp", "decay_ms", "resonance_hz", "jitter_pct", "amp_var_pct"):
        if key not in imp:
            problems.append(f"missing impacts.{key}")
    if "modulation" not in imp:
        problems.append("missing impacts.modulation")
    elif imp["modulation"].get("type") not in {"none", "shaft", "cage"}:
        problems.append("invalid impacts.modulation.type")
    for key in ("noise_rms", "band_weights", "components", "random_impulses"):
        if key not in bg:
            problems.append(f"missing background.{key}")
    weights = bg.get("band_weights", [])
    if not isinstance(weights, list) or len(weights) != len(BANDS):
        problems.append(f"background.band_weights length must be {len(BANDS)}")
    else:
        try:
            arr = np.asarray(weights, dtype=float)
            if not np.all(np.isfinite(arr)) or np.any(arr < 0) or float(arr.sum()) <= 0:
                problems.append("background.band_weights must be finite nonnegative with positive sum")
        except (TypeError, ValueError):
            problems.append("background.band_weights must be numeric")
    if "psd_template_amp" in bg:
        problems.append("psd_template_amp is not allowed in LLM smoke recipes")
    return problems


class ApiBudgetExceeded(RuntimeError):
    pass


class LlmClient:
    def __init__(
        self,
        endpoint: str,
        model: str,
        api_key: str,
        min_interval: float,
        timeout: float,
        max_retries: int,
        max_api_requests: int,
        temperature: float,
        top_p: float,
        max_tokens: int,
    ) -> None:
        self.endpoint = endpoint
        self.model = model
        self.api_key = api_key
        self.min_interval = min_interval
        self.timeout = timeout
        self.max_retries = max_retries
        self.max_api_requests = max_api_requests
        self.temperature = temperature
        self.top_p = top_p
        self.max_tokens = max_tokens
        self.api_requests = 0
        self._last_call = 0.0

    def chat(self, messages: list[dict[str, str]]) -> tuple[str, dict[str, Any], list[str]]:
        errors: list[str] = []
        for attempt in range(self.max_retries):
            if self.api_requests >= self.max_api_requests:
                raise ApiBudgetExceeded(
                    f"API request cap reached ({self.max_api_requests}); stopping smoke."
                )
            elapsed = time.monotonic() - self._last_call
            delay = self.min_interval - elapsed
            if delay > 0:
                time.sleep(delay)
            self._last_call = time.monotonic()
            self.api_requests += 1
            try:
                response = requests.post(
                    self.endpoint,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": self.model,
                        "messages": messages,
                        "temperature": self.temperature,
                        "top_p": self.top_p,
                        "max_tokens": self.max_tokens,
                        "enable_thinking": False,
                        "chat_template_kwargs": {"enable_thinking": False},
                    },
                    timeout=self.timeout,
                )
                payload = response.json()
                if response.status_code >= 400:
                    errors.append(f"HTTP {response.status_code}: {str(payload)[:300]}")
                    continue
                if "choices" not in payload:
                    errors.append(f"missing choices: {str(payload)[:300]}")
                    continue
                text = payload["choices"][0]["message"]["content"]
                return str(text), payload, errors
            except Exception as exc:  # requests errors, JSON errors, provider truncation
                errors.append(f"attempt {attempt + 1}: {type(exc).__name__}: {exc}")
                if attempt + 1 < self.max_retries:
                    time.sleep(2**attempt)
        raise RuntimeError("; ".join(errors[-3:]))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def append_api_log(stage: str, dataset: str, planned: int, actual: int, notes: str) -> int:
    API_LOG.parent.mkdir(parents=True, exist_ok=True)
    cumulative = actual
    if API_LOG.exists():
        with API_LOG.open(newline="") as fh:
            rows = list(csv.DictReader(fh))
        if rows:
            cumulative = int(rows[-1]["cumulative_api_requests"]) + actual
    exists = API_LOG.exists()
    with API_LOG.open("a", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "timestamp_local",
                "stage",
                "dataset",
                "planned_calls",
                "actual_api_requests",
                "cumulative_api_requests",
                "notes",
            ],
        )
        if not exists:
            writer.writeheader()
        writer.writerow(
            {
                "timestamp_local": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "stage": stage,
                "dataset": dataset,
                "planned_calls": planned,
                "actual_api_requests": actual,
                "cumulative_api_requests": cumulative,
                "notes": notes,
            }
        )
    return cumulative


def summarize_failures(slot_records: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for rec in slot_records:
        if not rec.get("parse_ok"):
            counts["parse_failed"] += 1
        if not rec.get("schema_ok"):
            counts["schema_failed"] += 1
        reports = rec.get("reports", [])
        for report in reports:
            if report.get("feasible"):
                continue
            for violation in report.get("violations", []):
                counts[str(violation)] += 1
    return dict(counts)


def make_report(out_dir: Path, summary: dict[str, Any], failure_counts: dict[str, int]) -> None:
    rows = []
    for cls, item in summary["by_class"].items():
        rows.append(
            f"| {cls} | {item['slots']} | {item['api_requests']} | "
            f"{item['accepted_slots']} | {item['accepted_items']} | "
            f"{item['slot_acceptance']:.3f} |"
        )
    failures = "\n".join(
        f"- {name}: {count}" for name, count in sorted(failure_counts.items(), key=lambda x: (-x[1], x[0]))
    )
    if not failures:
        failures = "- none"
    report = (
        "# Phase-B CWRU LLM Smoke Gate Report\n\n"
        "## Scope\n"
        "- Dataset/order: CWRU first, before XJTU and IMS.\n"
        "- Protocol: within_load0 train-only calibration, CWRU 12 kHz drive-end channel.\n"
        "- API discipline: serial calls, interval >=2.0 s, max_tokens<=900, retries<=3, "
        "global cap <=30 API requests for this smoke.\n"
        "- Renderer/verifier: same CWRU Phase-B renderer and train-calibrated verifier used by the local rule/random smoke; no recipe post-processing or template injection is applied after LLM output.\n\n"
        "## API Usage\n"
        f"- Planned recipe slots: {summary['planned_slots']}.\n"
        f"- New API requests in this run: {summary['actual_new_api_requests']}.\n"
        f"- Cumulative API requests since the 2026-07-06 counter reset: {summary['cumulative_api_requests']}.\n\n"
        "## Acceptance By Class\n"
        "| class | slots | API requests | accepted slots | accepted items | slot acceptance |\n"
        "|---|---:|---:|---:|---:|---:|\n"
        + "\n".join(rows)
        + "\n\n## Failure Counts\n"
        + failures
        + "\n\n## Gate Decision\n"
        f"- Decision: {summary['gate_decision']}.\n"
        f"- Rationale: {summary['gate_rationale']}\n"
    )
    (out_dir / "gate_report.md").write_text(report)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train-npz", default="proc/cwru_de12k_within_load0_train.npz")
    parser.add_argument("--split", default="within_load0")
    parser.add_argument("--classes", nargs="+", choices=list(CWRU_CLASSES), default=list(CWRU_CLASSES))
    parser.add_argument("--n-per-class", type=int, default=5)
    parser.add_argument("--expansions", type=int, default=5)
    parser.add_argument("--healthy-anchor-count", type=int, default=8)
    parser.add_argument("--fault-quality-targets", action="store_true")
    parser.add_argument("--coverage", type=float, default=0.90)
    parser.add_argument("--tag", default="smoke_api_v1")
    parser.add_argument("--endpoint", default=os.environ.get("BREEZE_LLM_ENDPOINT", DEFAULT_ENDPOINT))
    parser.add_argument("--model", default=os.environ.get("BREEZE_LLM_MODEL", DEFAULT_MODEL))
    parser.add_argument("--min-interval", type=float, default=2.0)
    parser.add_argument("--timeout", type=float, default=300.0)
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument("--max-api-requests", type=int, default=30)
    parser.add_argument("--temperature", type=float, default=0.8)
    parser.add_argument("--top-p", type=float, default=0.9)
    parser.add_argument("--max-tokens", type=int, default=900)
    args = parser.parse_args()

    if args.max_tokens > 900:
        raise ValueError("max_tokens must be <=900 by task constraint")
    if args.max_retries > 3:
        raise ValueError("max_retries must be <=3 by task constraint")
    if args.min_interval < 2.0:
        raise ValueError("min_interval must be >=2.0 seconds by current task constraint")

    api_key = os.environ.get("MIMO_API_KEY") or os.environ.get("DASHSCOPE_API_KEY")
    if not api_key:
        raise RuntimeError("Set MIMO_API_KEY or DASHSCOPE_API_KEY in the environment; the key is not read from files.")

    data = np.load(ROOT / args.train_npz, allow_pickle=True)
    X = data["X"].astype(np.float32)
    y = data["y"].astype(np.int64)
    meta_rows = [json.loads(str(item)) for item in data["metadata"]]
    profiles, meta = build_profiles(X, y, meta_rows)
    anchors = component_anchors(X, y)
    verifier = CwruVerifier(args.coverage)
    verifier.calibrate(X, y, meta_rows)

    out_dir = RUNS / f"phaseB_cwru_{args.split}_llm_{args.tag}"
    out_dir.mkdir(parents=True, exist_ok=True)

    planned_slots = args.n_per_class * len(args.classes)
    client = LlmClient(
        endpoint=args.endpoint,
        model=args.model,
        api_key=api_key,
        min_interval=args.min_interval,
        timeout=args.timeout,
        max_retries=args.max_retries,
        max_api_requests=args.max_api_requests,
        temperature=args.temperature,
        top_p=args.top_p,
        max_tokens=args.max_tokens,
    )

    slot_rows: list[dict[str, Any]] = []
    manifest: list[dict[str, Any]] = []
    full_records: list[dict[str, Any]] = []
    budget_exhausted = False

    for cls in args.classes:
        for slot in range(args.n_per_class):
            rec_path = out_dir / f"{cls}_{slot:04d}.json"
            if rec_path.exists():
                rec = json.loads(rec_path.read_text())
            else:
                prompt = user_prompt(
                    cls,
                    profiles[cls],
                    meta,
                    slot,
                    anchors[cls],
                    args.healthy_anchor_count,
                    args.fault_quality_targets,
                )
                messages = [
                    {"role": "system", "content": system_prompt()},
                    {"role": "user", "content": prompt},
                ]
                before = client.api_requests
                rec: dict[str, Any] = {
                    "source": "llm",
                    "dataset": "CWRU",
                    "split": args.split,
                    "class": cls,
                    "slot": slot,
                    "prompt": prompt,
                    "model": args.model,
                    "temperature": args.temperature,
                    "top_p": args.top_p,
                    "max_tokens": args.max_tokens,
                }
                try:
                    text, payload, api_errors = client.chat(messages)
                    recipe = extract_json(text)
                    schema_problems = validate_recipe(recipe) if recipe is not None else ["parse_failed"]
                    accepted_paths = []
                    reports = []
                    if recipe is not None and not schema_problems:
                        for exp in range(args.expansions):
                            seed = stable_seed(f"llm-cwru:{cls}:{slot}:{exp}")
                            w = render(recipe, seed)
                            report = verifier.verify(w, cls)
                            reports.append(report)
                            if report["feasible"]:
                                path = out_dir / f"{cls}_{slot:04d}_r{exp}.npy"
                                np.save(path, w)
                                accepted_paths.append(str(path.relative_to(ROOT)))
                    rec.update(
                        {
                            "api_requests": client.api_requests - before,
                            "api_errors": api_errors,
                            "raw_response": text,
                            "provider_usage": payload.get("usage", {}),
                            "recipe": recipe,
                            "parse_ok": recipe is not None,
                            "schema_ok": not schema_problems,
                            "schema_problems": schema_problems,
                            "accepted": bool(accepted_paths),
                            "n_candidates": args.expansions,
                            "n_feasible_expansions": len(accepted_paths),
                            "accepted_paths": accepted_paths,
                            "reports": reports,
                        }
                    )
                except ApiBudgetExceeded as exc:
                    budget_exhausted = True
                    rec.update(
                        {
                            "api_requests": client.api_requests - before,
                            "api_errors": [str(exc)],
                            "raw_response": "",
                            "provider_usage": {},
                            "recipe": None,
                            "parse_ok": False,
                            "schema_ok": False,
                            "schema_problems": ["api_budget_exhausted"],
                            "accepted": False,
                            "n_candidates": args.expansions,
                            "n_feasible_expansions": 0,
                            "accepted_paths": [],
                            "reports": [],
                        }
                    )
                except Exception as exc:
                    rec.update(
                        {
                            "api_requests": client.api_requests - before,
                            "api_errors": [f"{type(exc).__name__}: {exc}"],
                            "raw_response": "",
                            "provider_usage": {},
                            "recipe": None,
                            "parse_ok": False,
                            "schema_ok": False,
                            "schema_problems": ["api_or_parse_failed"],
                            "accepted": False,
                            "n_candidates": args.expansions,
                            "n_feasible_expansions": 0,
                            "accepted_paths": [],
                            "reports": [],
                        }
                    )
                rec_path.write_text(json.dumps(rec, indent=2) + "\n")
            slot_rows.append(
                {
                    "source": "llm",
                    "dataset": "CWRU",
                    "split": args.split,
                    "class": cls,
                    "slot": slot,
                    "api_requests": int(rec.get("api_requests", 0)),
                    "parse_ok": bool(rec.get("parse_ok", False)),
                    "schema_ok": bool(rec.get("schema_ok", False)),
                    "accepted_slot": bool(rec.get("accepted", False)),
                    "n_candidates": int(rec.get("n_candidates", args.expansions)),
                    "n_feasible_expansions": int(rec.get("n_feasible_expansions", 0)),
                    "schema_problems": ";".join(rec.get("schema_problems", [])),
                }
            )
            for path in rec.get("accepted_paths", []):
                manifest.append({"source": "llm", "class": cls, "slot": slot, "path": path})
            full_records.append(rec)
            if budget_exhausted:
                break
        if budget_exhausted:
            break

    if manifest:
        xs, ys = [], []
        for item in manifest:
            xs.append(np.load(ROOT / item["path"]).astype(np.float32))
            ys.append(CWRU_CLASSES.index(item["class"]))
        np.savez_compressed(
            out_dir / "pool.npz",
            X=np.stack(xs),
            y=np.asarray(ys, dtype=np.int64),
            class_names=np.asarray(CWRU_CLASSES),
        )
        write_csv(out_dir / "manifest.csv", manifest)
    write_csv(out_dir / "slot_summary.csv", slot_rows)

    by_class: dict[str, dict[str, Any]] = {}
    for cls in args.classes:
        rows = [r for r in slot_rows if r["class"] == cls]
        slots = len(rows)
        accepted_slots = int(sum(bool(r["accepted_slot"]) for r in rows))
        by_class[cls] = {
            "slots": slots,
            "api_requests": int(sum(int(r["api_requests"]) for r in rows)),
            "accepted_slots": accepted_slots,
            "accepted_items": int(sum(int(r["n_feasible_expansions"]) for r in rows)),
            "slot_acceptance": float(accepted_slots / slots) if slots else 0.0,
        }

    completed_classes = [cls for cls, item in by_class.items() if item["slots"] > 0]
    all_completed = len(slot_rows) == planned_slots
    no_empty_completed_class = all(
        by_class[cls]["accepted_slots"] > 0 for cls in completed_classes
    )
    if not all_completed:
        gate_decision = "INCOMPLETE"
        gate_rationale = "API budget exhausted or run interrupted before all planned slots completed."
    elif no_empty_completed_class:
        gate_decision = "PASS_FOR_DOWNSTREAM_SMOKE"
        gate_rationale = "Every completed class has at least one accepted LLM slot under the train-only verifier."
    else:
        gate_decision = "FAIL_NEEDS_ITERATION"
        gate_rationale = "At least one class has zero accepted LLM slots; inspect failures before scaling."

    actual = client.api_requests
    cumulative = append_api_log(
        stage="phaseB_cwru_llm_smoke",
        dataset="CWRU",
        planned=planned_slots,
        actual=actual,
        notes=f"{args.split}; tag={args.tag}; decision={gate_decision}; model={args.model}; key_not_stored",
    )
    failure_counts = summarize_failures(full_records)
    summary = {
        "dataset": "CWRU",
        "split": args.split,
        "source": "llm",
        "tag": args.tag,
        "planned_slots": planned_slots,
        "completed_slots": len(slot_rows),
        "actual_new_api_requests": actual,
        "cumulative_api_requests": cumulative,
        "coverage": args.coverage,
        "expansions": args.expansions,
        "by_class": by_class,
        "failure_counts": failure_counts,
        "pool": str((out_dir / "pool.npz").relative_to(ROOT)) if manifest else "",
        "gate_decision": gate_decision,
        "gate_rationale": gate_rationale,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    make_report(out_dir, summary, failure_counts)
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
