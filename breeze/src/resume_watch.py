"""Poll the LLM API; when quota is restored, resume the full generation
queue (physics K=3 pool, basic K=0 pool, raw-generator demo) from checkpoints.
"""
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import llm

ROOT = Path(__file__).parent.parent
PY = sys.executable


def api_ok():
    try:
        r = llm.chat([{"role": "user", "content": "reply with OK"}],
                     temperature=0.0)
        return bool(r)
    except Exception as e:
        print("api not ready:", str(e)[:120], flush=True)
        return False


def run(cmd, log):
    with open(ROOT / "runs" / log, "a") as f:
        subprocess.run(cmd, stdout=f, stderr=f, cwd=ROOT)


while not api_ok():
    time.sleep(600)
print("API restored, resuming generation", flush=True)
run([PY, "src/pipeline.py", "--k", "3", "--n", "150",
     "--out", "runs/pool_physics_file_k3", "--workers", "2"],
    "pool_physics_file_k3.log")
run([PY, "src/pipeline.py", "--k", "0", "--n", "150", "--prompt", "basic",
     "--out", "runs/pool_basic_file_k0", "--workers", "2"],
    "pool_basic_file_k0.log")
run([PY, "src/raw_pipeline.py", "--k", "2", "--n", "12",
     "--out", "runs/pool_raw_k2", "--workers", "2"], "pool_raw_k2.log")
print("generation queue complete", flush=True)
