"""BREEZE closed-loop generation pipeline (checkpoint-resumable).

Usage:
  python pipeline.py --gen recipe --k 3 --n 100 --cond N09_M07_F10 \
      --out runs/pool_recipe_k3 [--coverage 0.90] [--workers 2]

Each candidate slot i (per class) is generated independently:
  round 0: fresh prompt -> recipe -> render -> verify
  round r: constraint-report feedback -> revised recipe -> verify
Accepted (or exhausted) results are written to out/{cls}_{i:04d}.json (+.npy),
so re-running skips finished slots.
"""
import argparse
import hashlib
import json
import sys
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import CLASSES, MAIN_COND, RUNS_DIR, fault_freqs, CONDITIONS
from data import load_file_split
from verifier.verifier import BreezeVerifier
from renderer import render
import llm


def exemplar_description(Xtr, ytr, btr, cls, bearing):
    """Coarse textual character of real train windows of ONE bearing unit:
    medians of a few train-split summary statistics (MechaForge-style
    summary stage, but deterministic). No verifier bounds are revealed."""
    from verifier.features import time_stats, psd
    from config import FS
    from scipy.signal import find_peaks
    ci = CLASSES.index(cls)
    W = Xtr[(ytr == ci) & (btr == bearing)]
    rng = np.random.default_rng(1)
    idx = rng.choice(len(W), min(100, len(W)), replace=False)
    st = [time_stats(W[i][0]) for i in idx]
    cu = [time_stats(W[i][1]) for i in idx]
    rms = np.median([s["rms"] for s in st])
    kur = np.median([s["kurtosis"] for s in st])
    camp = np.median([s["peak"] for s in cu])
    ckur = np.median([s["kurtosis"] for s in cu])
    crms = np.median([s["rms"] for s in cu])
    from renderer import BANDS as bands
    fracs = []
    for i in idx[:30]:
        f, p = psd(W[i][0], FS)
        tot = np.trapezoid(p, f)
        fracs.append([np.trapezoid(p[(f >= a) & (f < b)], f[(f >= a) & (f < b)])
                      / tot for a, b in bands])
    fr = np.median(fracs, axis=0)
    band_txt = ", ".join(f"{a}-{b} Hz: {v:.0%}" for (a, b), v in zip(bands, fr))
    bw_txt = "[" + ", ".join(f"{v:.3f}" for v in fr) + "]"
    # dominant discrete spectral peaks (shaft harmonics, resonances)
    ps = [psd(W[i][0], FS, nperseg=2048)[1] for i in idx[:60]]
    fgrid = psd(W[0][0], FS, nperseg=2048)[0]
    pmean = np.mean(ps, axis=0)
    pk, _ = find_peaks(np.log10(pmean + 1e-15), prominence=0.4)
    pk = sorted(pk, key=lambda i: -pmean[i])[:10]
    df = fgrid[1] - fgrid[0]
    comp_txt = ", ".join(
        f"{{\"freq_hz\": {fgrid[i]:.0f}, \"amp\": {np.sqrt(4*pmean[i]*df):.3g}}}"
        for i in sorted(pk))
    ri_hint = (f" the rig also shows NON-periodic random transients in every "
               f"health state: include background \"random_impulses\" (amp "
               f"~4-6x the implied noise level, rate_hz 30-60, decay_ms 1-2, "
               f"resonance_hz 2000-3500).")
    if cls == "healthy":
        imp_hint = (f" (reach kurtosis ~{kur:.2g} via the random_impulses "
                    f"amplitude; there must be NO periodic impacts)")
    else:
        imp_hint = (f" (to reach kurtosis ~{kur:.2g}, set \"impacts.amp\" "
                    f"about 4-8x the vibration rms with short decay_ms 1-3"
                    + ("; inner-race impact resonance is typically high, "
                       "~3000-3600 Hz" if cls == "IR" else
                       "; outer-race impact resonance is typically "
                       "~600-1100 Hz") + ")")
    return (f"vibration rms ~{rms:.2g}, kurtosis ~{kur:.2g}{imp_hint};"
            f"{ri_hint} "
            f"vibration energy "
            f"split across bands roughly ({band_txt}) -- set background "
            f"\"band_weights\" close to {bw_txt} and vary moderately; "
            f"include background \"components\" close to [{comp_txt}] "
            f"(dominant measured spectral peaks; keep frequencies, vary "
            f"amplitudes moderately); "
            f"phase currents are "
            f"~{camp:.2g}-peak near-pure sinusoids at ~60 Hz supply frequency "
            f"(set current \"rms\" to ~{crms:.3g} and current \"kurtosis\" to "
            f"exactly {ckur:.4g} -- the real spread of current kurtosis is "
            f"tiny, so do NOT vary this value; sample-to-sample variation "
            f"comes from the renderer noise seed).")


def gen_recipe_candidate(cls, freqs, exemplar, feedback, prev_recipe=None,
                         temperature=1.0, basic=False):
    msg = [{"role": "system", "content": llm.SYSTEM},
           {"role": "user",
            "content": llm.user_prompt(cls, freqs, exemplar, feedback,
                                        prev_recipe, basic=basic)}]
    text = llm.chat(msg, temperature=temperature)
    return llm.parse_recipe(text)


def run_slot(args):
    cls, i, K, verifier, freqs, exemplar, out_dir, prompt_mode = args
    fjson = out_dir / f"{cls}_{i:04d}.json"
    if fjson.exists():
        return None
    history, feedback, prev = [], None, None
    accepted, w = False, None
    for rnd in range(K + 1):
        try:
            recipe = gen_recipe_candidate(
                cls, freqs, "" if prompt_mode == "basic" else exemplar,
                feedback, prev, basic=(prompt_mode == "basic"))
        except Exception as e:
            history.append({"round": rnd, "error": str(e)[:200]})
            continue
        if recipe is None:
            feedback = ["Previous output was not valid JSON. Output a single "
                        "valid JSON object only."]
            history.append({"round": rnd, "error": "parse_fail"})
            continue
        # cheap stochastic resampling: several renderer seeds per recipe
        rep, w = None, None
        try:
            for sub in range(3):
                seed = int(hashlib.md5(f"{cls}_{i}_{rnd}_{sub}".encode())
                           .hexdigest()[:8], 16)
                w = render(recipe, seed)
                rep = verifier.verify(w, cls)
                if rep["feasible"]:
                    break
        except Exception as e:
            feedback = [f"Recipe could not be rendered: {e}. Follow the schema "
                        "exactly with numeric values."]
            history.append({"round": rnd, "error": f"render: {e}"[:200]})
            continue
        np.save(out_dir / f"{cls}_{i:04d}_r{rnd}.npy", w)
        history.append({"round": rnd, "recipe": recipe,
                        "feasible": rep["feasible"],
                        "gate_pass": {g: gr["passed"]
                                      for g, gr in rep["gates"].items()},
                        "violations": [m for g in rep["gates"].values()
                                       for m in g["messages"]]})
        if rep["feasible"]:
            accepted = True
            break
        feedback, prev = rep["instructions"], recipe
    result = {"class": cls, "slot": i, "K": K, "accepted": accepted,
              "rounds_used": len(history), "history": history}
    if accepted and w is not None:
        np.save(out_dir / f"{cls}_{i:04d}.npy", w)
        # free multi-seed expansion of the accepted recipe (no LLM calls):
        # extra renderer seeds, each rechecked by the verifier
        rec = history[-1]["recipe"]
        nx = 0
        for sub in range(3, 12):
            if nx >= 4:
                break
            seed = int(hashlib.md5(f"{cls}_{i}_x_{sub}".encode())
                       .hexdigest()[:8], 16)
            try:
                wx = render(rec, seed)
            except Exception:
                continue
            if verifier.verify(wx, cls)["feasible"]:
                np.save(out_dir / f"{cls}_{i:04d}_x{nx}.npy", wx)
                nx += 1
    fjson.write_text(json.dumps(result))
    return cls, i, accepted, len(history)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--cond", default=MAIN_COND)
    ap.add_argument("--out", required=True)
    ap.add_argument("--coverage", type=float, default=0.90)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--prompt", default="physics", choices=["physics", "basic"])
    ap.add_argument("--classes", nargs="+", default=None)
    a = ap.parse_args()

    out_dir = Path(a.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    Xtr, ytr, btr = load_file_split("train", a.cond)
    vpath = RUNS_DIR / f"verifier_{a.cond}_file_c{int(a.coverage*100)}.json"
    if vpath.exists():
        verifier = BreezeVerifier.load(vpath)
    else:
        verifier = BreezeVerifier(coverage=a.coverage)
        verifier.calibrate(Xtr, ytr, a.cond, bearings=btr)
        verifier.save(vpath)
    freqs = fault_freqs(CONDITIONS[a.cond][0] / 60.0)
    exemplars = {c: {b: exemplar_description(Xtr, ytr, btr, c, b)
                     for b in np.unique(btr[ytr == CLASSES.index(c)])}
                 for c in CLASSES}

    run_classes = a.classes or CLASSES
    tasks = []
    for cls in run_classes:
        bearings = sorted(exemplars[cls])
        for i in range(a.n):
            if (out_dir / f"{cls}_{i:04d}.json").exists():
                continue
            ex = exemplars[cls][bearings[i % len(bearings)]]
            tasks.append((cls, i, a.k, verifier, freqs, ex, out_dir, a.prompt))
    print(f"{len(tasks)} slots to run (K={a.k})")
    done = acc = 0
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = [ex.submit(run_slot, t) for t in tasks]
        for f in as_completed(futs):
            r = f.result()
            if r:
                done += 1
                acc += r[2]
                if done % 10 == 0:
                    print(f"{done}/{len(tasks)} done, acceptance {acc/done:.2f}",
                          flush=True)
    print(f"finished: {done} slots, acceptance {acc/max(done,1):.3f}")


if __name__ == "__main__":
    main()
