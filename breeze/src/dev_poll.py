"""Poll the LLM API; when it works, run the small dev batch and exit."""
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import llm

while True:
    try:
        llm.chat([{"role": "user", "content": "OK"}], temperature=0,
                 max_retries=1)
        print("API OK, running dev batch", flush=True)
        break
    except Exception as e:
        print("api not ready:", str(e)[:120], flush=True)
        time.sleep(300)

subprocess.run([sys.executable, str(Path(__file__).parent / "pipeline.py"),
                "--k", "3", "--n", "10", "--out", "runs/pool_dev_v2",
                "--workers", "2"], cwd=str(Path(__file__).parents[1]))
print("dev batch finished", flush=True)
