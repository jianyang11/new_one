"""Generator-agnosticism demo: BREEZE wrapping a MechaForge-style RAW
numeric-text LLM generator (the LLM emits the waveform itself as CSV rows,
no renderer). Small scale (windows are 2048 rows -> chunked continuation).

Usage: python raw_pipeline.py --k 2 --n 10 --out runs/pool_raw_k2
"""
import argparse
import json
import re
import sys
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import CLASSES, MAIN_COND, RUNS_DIR, WIN, FS, fault_freqs, CONDITIONS
from data import load_file_split
from verifier.verifier import BreezeVerifier
import llm
from pipeline import exemplar_description

ROW_RE = re.compile(r"^([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?),\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?),\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)$")


def parse_rows(text):
    rows = []
    for line in text.split("\n"):
        m = ROW_RE.match(line.strip())
        if m:
            rows.append([float(v) for v in m.groups()])
    return rows


def raw_prompt(cls, freqs, exemplar, feedback):
    fault = {"healthy": "a HEALTHY bearing (no periodic impacts)",
             "OR": f"an OUTER-RACE fault (impacts every {1000/freqs['BPFO']:.2f} ms "
                   f"= {int(round(FS/freqs['BPFO']))} samples, constant amplitude)",
             "IR": f"an INNER-RACE fault (impacts every {1000/freqs['BPFI']:.2f} ms "
                   f"= {int(round(FS/freqs['BPFI']))} samples, amplitude-modulated "
                   f"at fr={freqs['fr']:.1f} Hz)"}[cls]
    p = (f"Generate a synthetic condition-monitoring window for {fault} on a "
         f"Paderborn-type rig, sampled at {FS} Hz, {WIN} samples.\n"
         f"Real-signal character: {exemplar}\n"
         f"Output ONLY numeric rows 'vibration,current1,current2' (6 decimals), "
         f"one per line, no other text. Start now and output as many rows as "
         f"you can.")
    if feedback:
        p += ("\n\nYour previous window was rejected by a physics verifier. "
              "Fix ALL of these violations:\n- " + "\n- ".join(feedback))
    return p


def gen_raw_window(cls, freqs, exemplar, feedback):
    msgs = [{"role": "system",
             "content": "You are an expert bearing vibration signal generator. "
                        "Output only numeric CSV rows, no commentary."},
            {"role": "user", "content": raw_prompt(cls, freqs, exemplar, feedback)}]
    rows = []
    stall = 0
    for _ in range(14):  # continuation loop
        text = llm.chat(msgs, temperature=1.0, max_tokens=6000)
        new = parse_rows(text)
        if not new:
            stall += 1
            if stall >= 3:
                break
        else:
            stall = 0
            rows.extend(new)
        if len(rows) >= WIN:
            break
        msgs.append({"role": "assistant", "content": text})
        msgs.append({"role": "user",
                     "content": f"You have produced {len(rows)} rows so far. "
                                f"Continue the SAME signal seamlessly from row "
                                f"{len(rows)+1} to row {WIN}. Output ONLY "
                                f"numeric CSV rows, no words, no ellipsis."})
    if len(rows) < WIN:
        return None, len(rows)
    w = np.array(rows[:WIN], dtype=np.float32).T  # (3, WIN)
    return w, len(rows)


def run_slot(args):
    cls, i, K, verifier, freqs, exemplar, out_dir = args
    fjson = out_dir / f"{cls}_{i:04d}.json"
    if fjson.exists():
        return None
    history, feedback = [], None
    accepted, w = False, None
    for rnd in range(K + 1):
        try:
            w, nrows = gen_raw_window(cls, freqs, exemplar, feedback)
        except Exception as e:
            history.append({"round": rnd, "error": str(e)[:200]})
            continue
        if w is None:
            feedback = [f"Only {nrows} rows were produced; output the full "
                        f"{WIN} numeric rows."]
            history.append({"round": rnd, "error": f"short:{nrows}"})
            continue
        rep = verifier.verify(w, cls)
        np.save(out_dir / f"{cls}_{i:04d}_r{rnd}.npy", w)
        history.append({"round": rnd, "feasible": rep["feasible"],
                        "gate_pass": {g: gr["passed"]
                                      for g, gr in rep["gates"].items()},
                        "violations": [m for g in rep["gates"].values()
                                       for m in g["messages"]]})
        if rep["feasible"]:
            accepted = True
            break
        feedback = rep["instructions"]
    fjson.write_text(json.dumps({"class": cls, "slot": i, "K": K,
                                 "accepted": accepted,
                                 "rounds_used": len(history),
                                 "history": history}))
    if accepted and w is not None:
        np.save(out_dir / f"{cls}_{i:04d}.npy", w)
    return cls, i, accepted


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=2)
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=2)
    a = ap.parse_args()
    out_dir = Path(a.out); out_dir.mkdir(parents=True, exist_ok=True)
    Xtr, ytr, btr = load_file_split("train", MAIN_COND)
    verifier = BreezeVerifier.load(RUNS_DIR / f"verifier_{MAIN_COND}_file_c90.json")
    freqs = fault_freqs(CONDITIONS[MAIN_COND][0] / 60.0)
    exemplars = {}
    for c in CLASSES:
        ci = CLASSES.index(c)
        bearing = sorted(set(btr[ytr == ci]))[0]
        exemplars[c] = exemplar_description(Xtr, ytr, btr, c, bearing)
    tasks = [(cls, i, a.k, verifier, freqs, exemplars[cls], out_dir)
             for cls in CLASSES for i in range(a.n)
             if not (out_dir / f"{cls}_{i:04d}.json").exists()]
    print(f"{len(tasks)} raw slots (K={a.k})")
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = [ex.submit(run_slot, t) for t in tasks]
        for f in as_completed(futs):
            r = f.result()
            if r:
                print(r, flush=True)


if __name__ == "__main__":
    main()
