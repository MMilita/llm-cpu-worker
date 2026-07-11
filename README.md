# llm-cpu-worker

Autonomous **€0** CPU worker for the private LLM gateway. It is a *self-relaunching*
failover worker: it drains the gateway's job queue with Ollama on CPU + a small model
(`qwen2.5:3b`), then returns before the job cap and the cron re-invokes it — **zero manual
intervention**.

## Why a public repo

Private repos get only ~2000 free Actions minutes/month (burns in ~1 day). **Public repos
get unlimited free Actions minutes**, so the `every-4h` cron gives a genuinely 24/7,
€0 worker that restarts itself forever.

## How it works

- `.github/workflows/gpu-worker.yml` — cron `0 */4 * * *` + `workflow_dispatch`. Installs
  Ollama (CPU), pulls `qwen2.5:3b`, runs the worker for ~340 min (under the 6h hard cap),
  then exits. The next cron tick relaunches it.
- `gha_cpu_worker.py` — the worker loop: `POST /gpu/next` (also a heartbeat) → infer on
  local Ollama → `POST /gpu/result`, until `RUN_SECONDS` elapses.
- `worker_core.py` — small pure helper reused across the worker fleet.

Mode is **degraded/failover**: CPU + a 3B model is the guaranteed floor for when the GPU
workers are down. It is self-hosted Ollama on the CI runner — your own compute, not a
third-party API that trains on your data.

## Setup (one time)

No secret ever lives in code. Add the gateway token as an Actions secret:

```
Repo → Settings → Secrets and variables → Actions → New secret
  Name:  GATEWAY_TOKEN
  Value: <your gateway token>
```

Then trigger a first run from the **Actions** tab (or `gh workflow run gpu-worker.yml`).
After that it self-runs on the cron with no further action.
