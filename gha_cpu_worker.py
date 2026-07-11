#!/usr/bin/env python3
"""Worker CPU di FAILOVER per il gateway LLM — invocato dal workflow GitHub Actions.

Modalità DEGRADATA: Ollama-CPU + modello piccolo (qwen2.5:3b). Drena la coda del
gateway (/gpu/next → infer → /gpu/result) finché scade RUN_SECONDS, poi RITORNA
(il job non deve superare il tetto 6h/job di GitHub Actions). Il cron lo re-invoca.
Privacy salva: è self-host TUO sul runner CI, non un'API che si allena sui dati.
"""
import os
import time
import uuid
import requests

GATEWAY = os.environ.get("LLM_GATEWAY", "https://milita-llm.duckdns.org/v1").rstrip("/")
TOKEN = os.environ.get("GATEWAY_TOKEN", "")
MODEL = os.environ.get("GPU_MODEL", "qwen2.5:3b")
OLLAMA = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434/api/chat")
PREFIX = os.environ.get("WORKER_ID_PREFIX", "gha-cpu")
WORKER_ID = os.environ.get("WORKER_ID", PREFIX + "-" + uuid.uuid4().hex[:6])
RUN_SECONDS = int(os.environ.get("RUN_SECONDS", "20400"))   # ~340 min
H = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}


def infer(messages, max_tokens, fmt=None):
    body = {"model": MODEL, "stream": False, "messages": messages,
            "options": {"num_predict": max_tokens}}
    if fmt == "json":
        body["format"] = "json"
    r = requests.post(OLLAMA, timeout=600, json=body)
    r.raise_for_status()
    return r.json().get("message", {}).get("content", "")


def main():
    assert TOKEN, "GATEWAY_TOKEN mancante (GitHub Actions secret o env)"
    print(f"worker CPU failover attivo → {GATEWAY} | modello {MODEL} | id {WORKER_ID}", flush=True)
    deadline = time.time() + RUN_SECONDS
    done = 0
    while time.time() < deadline:
        try:
            # /gpu/next fa anche da heartbeat: il polling continuo tiene il worker 'vivo'
            j = requests.post(f"{GATEWAY}/gpu/next", headers=H, timeout=30,
                               json={"worker_id": WORKER_ID, "model": MODEL}).json()
        except Exception as e:
            print("next err:", e, flush=True); time.sleep(5); continue
        if not j:
            time.sleep(2)                      # coda vuota: attesa breve
            continue
        try:
            ans = infer(j["messages"], j.get("max_tokens", 1200), j.get("fmt"))
            requests.post(f"{GATEWAY}/gpu/result", headers=H, timeout=30,
                          json={"job_id": j["job_id"], "answer": ans, "worker_id": WORKER_ID})
            done += 1
            print(f"job {j['job_id'][:8]} ✓  ({len(ans)} char, totali {done})", flush=True)
        except Exception as e:
            print("infer/result err:", e, flush=True); time.sleep(2)
    print(f"passata conclusa: {done} job. Il cron re-invoca.", flush=True)


if __name__ == "__main__":
    main()
