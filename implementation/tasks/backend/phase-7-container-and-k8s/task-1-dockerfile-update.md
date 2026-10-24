# task-1 — Dockerfile update (drop `data/`, torch-cpu)   ·   [backend / phase-7-container-and-k8s]

| Field | Value |
|-------|-------|
| **Status** | `done-pending-review` |
| **Repo** | `Sentinel` (backend) |
| **Phase branch** | `dev/backend-phase-7-container-and-k8s` |
| **Commit prefix** | `refactor:` |
| **Arch refs** | architecture/backend.md §7, §13.2 (Dockerfile), §13.5 step 9 |
| **Depends on** | Phase-5 app boots |
| **Referenced by** | [[task-2-k8s-manifests]], [[task-2-ci-backend-deployment]] |

> ⚠ **ARM64 (2026-08-23):** the AKS node is `Standard_B2pls_v2` — **arm64**. The image MUST
> be built `linux/arm64` (`docker buildx build --platform linux/arm64`) or the pod dies in
> CrashLoopBackOff with `exec format error`. Python base images and torch-cpu both publish
> aarch64 wheels. The x86 grant SKU could not host an AKS system pool (SystemPoolSkuTooLow).

## Spec
Update the image: copy `src/` + `alembic/` (no `data/`), install with torch-cpu index to
keep the image small.

**Files modified:** `Dockerfile`
- `python:3.12-slim`; apt `libpq-dev gcc`; `pip install -r requirements.txt` with `PIP_EXTRA_INDEX_URL=https://download.pytorch.org/whl/cpu`; `COPY src/ alembic/ alembic.ini`; **no `COPY data/`**; `CMD uvicorn sentinel.main:app --host 0.0.0.0 --port 8000`.

## Prerequisites
- [ ] Docker installed. [ ] Phase-5 app importable.

## Acceptance Criteria
- [ ] `docker build` succeeds; image runs and serves `/health`; no `data/` in the image; torch is cpu build (~80 MB not ~2 GB).

## Tests
- **Build/run:** `docker build -t sentinel-backend:test .`; `docker run` + `curl /health` (with local DB env / FAKE_LLM).
- **Lint:** hadolint (optional).
- **Quality gate:** `--repo backend`.
- **Result:** gate VERDICT GREEN (full run, 7 ran, 0 skipped); `sentinel serve` boot OK. 4 new tests in tests/test_scripts/test_install_locked.py (run directly; test_scripts glob joins the gate list when phase merges); 3 edited + 2 new in test_workload_identity.py.

## How to Verify (phase gate)
1. `docker buildx build --platform linux/arm64 -t sentinel-backend:test .` succeeds; container serves `/health`.
2. `docker run … sh -c 'ls'` shows no `data/`.
3. `docker run --network none …` then `curl /health` returns 200 (model baked, offline).

## Report   ·   _filled on completion_
Built 2026-10-24. Commits 3f4980c "refactor: lock-based arm64 image; LLM keys read from Key Vault" + 0730682 "refactor: bake the embedding model into the image; run offline" on dev/backend-phase-7-container-and-k8s (rebased onto release-phase-2 d0e58f4).
- Multi-stage arm64 image (2.47 GB), installs from poetry.lock (scripts/install_locked.py --main-only), torch 2.14.1+cpu, no CUDA/nvidia/triton. Non-root uid 10001, PYTHONPATH=/app/src; has alembic/, alembic.ini, src/; no data/.
- all-MiniLM-L6-v2 baked into /opt/hf, HF_HUB_OFFLINE=1, TRANSFORMERS_OFFLINE=1. uvicorn --timeout-graceful-shutdown 5 (5+37=42 s < 45 s grace).
- KV loader reads anthropic-api-key and openai-api-key into Settings (no env mirroring).
- Tooling: PR #25 (d0e58f4) bumped setuptools/filelock + dated filelock CVE ignore (expires 2026-11-24). Decisions: dd95eef.

## BLOCKED
_none locally (Docker). Note: full boot needs DB env or FAKE_LLM._
