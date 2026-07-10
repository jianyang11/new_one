"""LLM client + prompts for BREEZE closed-loop signal generation."""
import json
import os
import re
import time
import requests
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import threading
from config import FS, WIN, LLM_BASE_URL, LLM_MODEL, LLM_MIN_INTERVAL

_rate_lock = threading.Lock()
_last_call = [0.0]

API_KEY = os.environ.get("DASHSCOPE_API_KEY", "")

RECIPE_SCHEMA = """{
 "fr_hz": <shaft rotation frequency in Hz>,
 "target_rms": <overall rms of the vibration channel>,
 "impacts": {"rate_hz": <impact repetition frequency Hz; 0 for healthy>,
   "amp": <impact amplitude, typically 3-6x target_rms so the impacts
   clearly dominate (vibration kurtosis must exceed ~3.6)>,
   "decay_ms": <exponential decay 0.5-10>,
   "resonance_hz": <excited structural resonance Hz, < %NYQ%>,
   "jitter_pct": <1-3 slip jitter>, "amp_var_pct": <5-40>,
   "modulation": {"type": "none"|"shaft", "depth": 0-1}},
 "background": {"noise_rms": <broadband noise rms>,
   "band_weights": [<8 relative energy weights of the background noise over
     the fixed bands 0-250, 250-500, 500-1000, 1000-1500, 1500-2000,
     2000-2500, 2500-3000, 3000-4000 Hz>],
   "components": [{"freq_hz": <Hz>, "amp": <amplitude>} , ...],
   "random_impulses": {"rate_hz": <mean rate of NON-periodic machine
     transients>, "amp": <amplitude>, "decay_ms": <0.5-3>,
     "resonance_hz": <Hz>}},
 "currents": {"fe_hz": <supply fundamental Hz>, "rms": <overall rms of each
   current channel>, "kurtosis": <target kurtosis of each current channel,
   1.50-1.51 for the near-pure sinusoid of this rig>, "crest": <target
   peak-to-RMS ratio, 1.46-1.53>, "thd": <0-0.1>, "sideband_depth": <0-0.2>,
   "fault_freq_hz": <bearing fault frequency Hz or 0>}
}"""

SYSTEM = (
    "You are an expert in rolling-element bearing vibration analysis and "
    "motor current signature analysis. You design physically plausible "
    "parameter recipes for synthetic condition-monitoring signals of a "
    "Paderborn-type test rig (bearing 6203, PMSM drive). Signals are "
    f"sampled at {FS} Hz, window length {WIN} samples. Respond ONLY with a "
    "single JSON object, no markdown fences, no commentary.")


def user_prompt(cls: str, freqs: dict, exemplar_desc: str,
                feedback: list[str] | None = None,
                prev_recipe: dict | None = None, basic: bool = False) -> str:
    fault_desc = {
        "healthy": "a HEALTHY bearing: NO periodic impacts (impacts.amp=0), "
                   "but the real rig still shows frequent NON-periodic random "
                   "machine transients, so the waveform is impulsive (high "
                   "kurtosis) -- realize this with background.random_impulses "
                   "on top of broadband noise.",
        "OR": f"an OUTER-RACE fault: impacts repeat at BPFO = "
              f"{freqs['BPFO']:.1f} Hz with nearly constant amplitude "
              f"(stationary defect in the load zone). The fault impacts sit "
              f"ON TOP of the normal machine background (keep the background "
              f"components and random transients of a running rig).",
        "IR": f"an INNER-RACE fault: impacts repeat at BPFI = "
              f"{freqs['BPFI']:.1f} Hz, amplitude-modulated at the shaft "
              f"frequency fr = {freqs['fr']:.1f} Hz (defect rotates through "
              f"the load zone). The fault impacts sit ON TOP of the normal "
              f"machine background (keep the background components and "
              f"random transients of a running rig).",
    }[cls]
    if basic:
        # open-loop baseline: no kinematics, no train-data character
        simple = {"healthy": "a healthy bearing",
                  "OR": "a bearing with an outer-race fault",
                  "IR": "a bearing with an inner-race fault"}[cls]
        p = (f"Design ONE new signal recipe for {simple} on a motor test rig "
             f"running at {freqs['fr']*60:.0f} rpm.\n"
             f"Output JSON exactly following this schema:\n"
             + RECIPE_SCHEMA.replace("%NYQ%", str(FS // 2)))
    else:
        p = (f"Design ONE new signal recipe for {fault_desc}\n"
             f"Shaft frequency fr = {freqs['fr']:.1f} Hz. Kinematic frequencies: "
             f"BPFO={freqs['BPFO']:.1f}, BPFI={freqs['BPFI']:.1f}, "
             f"BSF={freqs['BSF']:.1f}, FTF={freqs['FTF']:.1f} Hz.\n"
             f"Reference character of real measurements (do not copy, vary "
             f"realistically): {exemplar_desc}\n"
             f"Output JSON exactly following this schema:\n"
             + RECIPE_SCHEMA.replace("%NYQ%", str(FS // 2)))
    if feedback:
        p += "\n\nYour PREVIOUS recipe was rejected by a physics verifier."
        if prev_recipe is not None:
            p += "\nPrevious recipe:\n" + json.dumps(prev_recipe)
        p += ("\nAdjust it minimally to fix ALL of the following violations "
              "while keeping it physically consistent. Make GRADUAL, "
              "proportionate changes - do not overshoot in the opposite "
              "direction:\n- " + "\n- ".join(feedback))
    return p


def chat(messages: list, temperature: float = 1.0, max_retries: int = 3,
         max_tokens: int = 900) -> str:
    for attempt in range(max_retries):
        with _rate_lock:
            dt = LLM_MIN_INTERVAL - (time.time() - _last_call[0])
            if dt > 0:
                time.sleep(dt)
            _last_call[0] = time.time()
        try:
            r = requests.post(
                f"{LLM_BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {API_KEY}"},
                json={"model": LLM_MODEL, "messages": messages,
                      "temperature": temperature, "max_tokens": max_tokens,
                      "enable_thinking": False,
                      "chat_template_kwargs": {"enable_thinking": False}},
                timeout=300)
            d = r.json()
            if "choices" not in d:
                raise RuntimeError(str(d)[:300])
            return d["choices"][0]["message"]["content"]
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)


def parse_recipe(text: str) -> dict | None:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
