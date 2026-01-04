import json
import os
import time
import random
import requests
from typing import Dict, Any, List

COMFY_URL = "http://127.0.0.1:8188"

WORKFLOW_PATH = "/workspace/jobs/day_night_workflow_api.json"
PROMPTS_PATH = "/workspace/jobs/prompts.txt"
PROGRESS_PATH = "/workspace/jobs/progress.json"

# Strong defaults for driving-photo realism
DAY_SUFFIX = "daytime, natural sunlight, clear visibility, realistic lighting, street-level photograph, photo-realistic, DSLR"
NIGHT_SUFFIX = "nighttime, street lights, headlights illumination, realistic night lighting, street-level photograph, photo-realistic, DSLR"

NEGATIVE = "cartoon, illustration, CGI, blurry, low resolution, distorted vehicles, warped road markings, unreadable text, gibberish letters, unreal lighting"

def load_json(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Missing file: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path: str, data: Dict[str, Any]) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)

def read_prompts(path: str) -> List[str]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Missing prompts file: {path}")
    with open(path, "r", encoding="utf-8") as f:
        lines = [ln.strip() for ln in f.readlines()]
    return [ln for ln in lines if ln]

def comfy_healthcheck() -> None:
    # Minimal: check port and /queue endpoint
    r = requests.get(f"{COMFY_URL}/queue", timeout=10)
    r.raise_for_status()

def find_nodes_by_title(workflow: Dict[str, Any], title: str) -> List[str]:
    hits = []
    for node_id, node in workflow.items():
        meta = node.get("_meta", {})
        if meta.get("title") == title:
            hits.append(node_id)
    return hits

def set_text(workflow: Dict[str, Any], node_ids: List[str], text: str) -> None:
    for nid in node_ids:
        workflow[nid]["inputs"]["text"] = text

def set_seed(workflow: Dict[str, Any], node_ids: List[str], seed: int) -> None:
    for nid in node_ids:
        workflow[nid]["inputs"]["seed"] = seed

def queue_prompt(workflow: Dict[str, Any]) -> str:
    r = requests.post(f"{COMFY_URL}/prompt", json={"prompt": workflow}, timeout=60)
    r.raise_for_status()
    return r.json()["prompt_id"]

def wait_until_done(prompt_id: str, poll_s: float = 2.0) -> None:
    # Robust approach: poll /queue until prompt leaves running+pending
    while True:
        r = requests.get(f"{COMFY_URL}/queue", timeout=30)
        r.raise_for_status()
        q = r.json()
        running = [x[1] for x in q.get("queue_running", [])]
        pending = [x[1] for x in q.get("queue_pending", [])]
        if prompt_id not in running and prompt_id not in pending:
            return
        time.sleep(poll_s)

def main():
    comfy_healthcheck()

    workflow = load_json(WORKFLOW_PATH)
    prompts = read_prompts(PROMPTS_PATH)
    if not prompts:
        raise SystemExit("prompts.txt is empty")

    day_nodes = find_nodes_by_title(workflow, "PROMPT_DAY")
    night_nodes = find_nodes_by_title(workflow, "PROMPT_NIGHT")
    neg_nodes = find_nodes_by_title(workflow, "NEGATIVE")

    if not day_nodes or not night_nodes:
        raise SystemExit("Workflow missing nodes titled PROMPT_DAY and/or PROMPT_NIGHT.")

    # Find sampler nodes to set seed deterministically per prompt
    sampler_nodes = [nid for nid, node in workflow.items() if node.get("class_type") == "KSampler"]
    if not sampler_nodes:
        raise SystemExit("Workflow missing KSampler nodes.")

    progress = {"last_done_index": -1}
    if os.path.exists(PROGRESS_PATH):
        try:
            progress = load_json(PROGRESS_PATH)
        except Exception:
            pass

    start_i = int(progress.get("last_done_index", -1)) + 1
    total = len(prompts)

    for i in range(start_i, total):
        base = prompts[i]

        prompt_day = f"photo-realistic street-level photograph, {base}, {DAY_SUFFIX}"
        prompt_night = f"photo-realistic street-level photograph, {base}, {NIGHT_SUFFIX}"

        wf = json.loads(json.dumps(workflow))  # deep copy

        set_text(wf, day_nodes, prompt_day)
        set_text(wf, night_nodes, prompt_night)

        if neg_nodes:
            set_text(wf, neg_nodes, NEGATIVE)

        # Seed: deterministic per prompt index (helps reproducibility)
        seed = (i + 1) * 100003 + random.randint(0, 999)  # small random jitter
        set_seed(wf, sampler_nodes, seed)

        print(f"[{i+1}/{total}] QUEUE: {base}")
        pid = queue_prompt(wf)
        wait_until_done(pid)

        progress["last_done_index"] = i
        save_json(PROGRESS_PATH, progress)

    print("DONE")

if __name__ == "__main__":
    main()