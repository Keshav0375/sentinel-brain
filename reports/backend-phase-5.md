# backend phase 5 — API & App

| | |
|---|---|
| **Repo** | `Sentinel` |
| **Branch → PR** | `dev/backend-phase-5-api` → `release-phase-2` · PR #23 — https://github.com/Keshav0375/Sentinel/pull/23 |
| **Tasks** | 6/6 green |
| **Gate** | ⬜ awaiting sign-off (gate GREEN on d27a8f3: 7 ran, 0 skipped) |

Reviews: architecture CONFORMS (audience amendment: brain 59684aa) · safety SAFE (body cap, concurrency cap, timeout fixed) · code LGTM after 2 fix rounds.

## What shipped

- **5.1 Webhook receiver** — POST /webhooks/incident: dedupe on correlation_id, per-incident task, 413 body cap, 429 concurrency cap, pipeline timeout, 503 on shutdown.
- **5.2 Incident queries** — list (limit ≤200), single, trajectory, linked deploy.
- **5.3 PR content** — POST /generate/pr-content, text only; 502 on agents SDK errors.
- **5.4 Probes** — /health `{"status":"ok"}`; /ready pings the DB pool.
- **5.5 Lifespan** — Entra PG token pool, optional Key Vault secrets, bounded shutdown drain and Langfuse flush.
- **5.6 Entra bearer auth** — v2 JWKS validation; audience is a comma-separated list (client-id GUID).

## What this unblocks

- Phase 6 (eval/judge) and phase 7 (deployment of the API) can call a real authenticated service.

## See it working

1. `docker start sentinel-pg-test`
2. Boot from ../Sentinel with SENTINEL_FAKE_LLM=1 and SENTINEL_API_TENANT_ID / SENTINEL_API_AUDIENCE set: `poetry run sentinel serve`
3. `curl -i localhost:8000/health` → 200; `curl -i localhost:8000/ready` → 200
4. `curl -i localhost:8000/incidents` → 401

## Not done / blocked

- Real-LLM run needs real API keys in Sentinel/.env.
- Live Entra token check not run here.
- **Skipped checks:** none.

## Carried follow-ups

- (a) Worst-case shutdown is 37s (drain 20 + 2 + trace flush 5 + close_pool 10), above k8s's 30s default grace; phase 7 needs terminationGracePeriodSeconds ≥45 or a shorter drain.
- (b) OTel TracerProvider atexit shutdown can add up to 30s; bounded, untested.
- (c) Key Vault is read once at startup; restart to rotate secrets.
- (d) Real-LLM run needs real API keys in Sentinel/.env.
- (e) User's Sentinel/.env fixes: DATABASE_URL, LANGFUSE_BASE_URL, DD_SITE us5.

## Decisions made during the build

- Audience accepts the API client-id GUID (v2 tokens); required config (brain 59684aa).
