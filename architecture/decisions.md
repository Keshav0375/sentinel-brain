# Sentinel Phase 2 — Decision Log

> **Why a decision was made, and what superseded what.** Append-only; newest first.
>
> This file holds **decisions only**. Live execution state — current phase, blockers,
> open reconciliations, the phase-gate ledger — lives in
> [implementation/STATE.md](../implementation/STATE.md) and is authoritative there.
> Do not mirror it here; two copies drift and the stale one gets believed.

**Do not read this file whole — it is ~56 KB (~14K tokens) and you need one entry.**

```bash
python scripts/arch.py decisions --list      # all entries, one line each
python scripts/arch.py decisions R6          # just the entry(s) matching a keyword
```

## Decision Log

### 2026-10-25: Backend phase 9 (Cleanup & End-to-End) contract

User answers (binding; supersede backend §13.1's delete list and task 9.2's demo-PR wording):
- **`GET /api/scenarios` is re-pointed at the real catalog.** It serves the 30 scenario branches (branch, case, fault, expected_signal_type, expected_resolution, …) read-only, from ONE vendored copy of `Sentinel-deployment/scenarios/branches.yaml` shipped with the package. The eval tests use that same copy, so there is no second fixture. It stays behind the bearer token, and the dashboard panel shows the real scenarios.
- **The live demo runs** `pass/01` (true negative: no incident), `deployfail/03` (`deploy_failure` → revert PR) and `runtime/01` (`runtime_error` → rollback or escalation), with `runtime/07` optional. Each is a human-merged PR on Sentinel-deployment, followed by the real path (Datadog → bridge → `repository_dispatch` → `ci_incident_response.yml`).
- **The live runbook lives in `sentinel-brain/reports/DEMO.md`,** never in a code repo.
- **The pipeline adds a LangFuse dataset item at the terminal state.** When an incident ends `rollback_proposed` or `escalated`, the backend writes one item to dataset `sentinel-scenario-runs`, in the item schema documented in `eval/runner.py`. The branch label comes from the deployed version or PR, plus the PR number, the merge SHA and the trajectory. This is a write to our own LangFuse only, like traces and scores, so the HITL rule holds. It is best effort: a failure is logged and never fails the incident. A human then runs `scripts/run_eval.py` to score the runs.

*Amended (user answers to the 9.2 HALT, 2026-10-25):*
- **The branch label is forwarded.** `scripts/incident_dispatch.py:shape_pr_details` adds `branch` (the PR's `head.ref`), `PRDetails` gains `branch: str | None` (§3.1 amended), and the dataset writer uses `pr_details.branch`. With no branch, the item is skipped and logged. 9.2 is built after 9.1, not in parallel.
- **A narrow R14 exception covers dataset items only.** The item's `pipeline_result` carries the LLM-written root cause, evidence summary and justification. **Every raw tool-output or log clip is stripped**, including the `_escalate` fallback's ≤300-char tool snippets. The trajectory is the orchestrator's status-only timeline, never raw span exports. Traces and scores keep R14 unchanged.

Orchestrator rulings:
- `scripts/run_eval.py` is **kept**: phase 6 rewrote it as the eval pipeline's CLI, and §13.1's deletion of it is void.
- 9.1 also removes every lingering reference to the deleted code: the `cli.py` `scenario`/`scenarios`/seed paths, `config.sentinel_db_path`, the pyproject `{ include = "data" }`, the tests that import the deleted code, stale comments, `.gitignore` sqlite lines, and the README/CONVENTIONS/CLAUDE.md mentions.
- The offline E2E (`tests/test_e2e/`) stubs the LangFuse client and dataset. Scoring stays a separate `run_eval` pass, never inlined into the pipeline.
- The links between incident, PR, deploy, logs and trace are live-only and are recorded as not yet run until the live demo.

### 2026-10-24: Backend phase 8 (CI/CD Workflows) contract

User answers (binding; they supersede backend §9.1–§9.3 triggers, `secrets.GH_PAT`, the stale names and the `sentinel-gha` PG user):

**`release-phase-2` is the live branch for the rest of Phase 2.**
- `release-phase-2` becomes the **default branch** of `Keshav0375/Sentinel` until the final merge. The user switches it in GitHub settings, then back to `main` at the final merge. This is needed because `repository_dispatch`, `schedule` and `workflow_dispatch` run from the default branch.
- `ci_validation.yml` gates `pull_request` into `[main, release-phase-2]`. It uses `pull_request` (never `pull_request_target`), `permissions: contents: read`, and no `environment`, `id-token`, `azure/login` or secrets.
- `ci_backend_deployment.yml` deploys on `push` to `[main, release-phase-2]`.
- The GitHub environment `sentinel-dev` on Sentinel allows deployments only from `main` and `release-phase-2`.

**Revert-PR credential: a fine-grained PAT.**
- `REVERT_PR_PAT`, scoped to `Keshav0375/Sentinel-deployment` only (Contents RW, Pull requests RW, 90-day expiry), stored as a **`sentinel-dev` environment secret**.
- It pushes only `revert-<sha>` and opens the PR. Sentinel-deployment `main` requires a PR, so no workflow can merge, approve or enable auto-merge.

**Rollback spec: a new backend endpoint.**
- `GET /incidents/{id}/rollback-spec` (bearer auth, `Incident.Write`) returns the `RollbackSpec` the pipeline drafted (404 when there is none, e.g. escalated).
- The workflow passes it unchanged to `POST /generate/pr-content`. The backend still only drafts.

**Orchestrator rulings.**
- `ci_backend_scale.yml` joins `concurrency: {group: sentinel-backend, cancel-in-progress: false}`.
- 8.3's name is `[sentinel] incident — response pipeline`.
- Builds and the PR-gate `docker run` use native arm64 runners (`ubuntu-24.04-arm`).
- Path filters add `poetry.lock`, `alembic/**`, `alembic.ini`, `scripts/**`, `.github/workflows/**` and `.github/actions/**` (all of which change the image or the pipeline).
- Non-deploy runs (8.3, 8.4) resolve `stable` to its `sha-<7>` tag via its ACR digest. ACR cleanup keeps the 3 newest `sha-` tags plus the ones behind `stable` and the running Deployment.
- Dispatch mapping:
  - `client_payload.{signal_type, correlation_id, event}` → `IncidentPayload`
  - `title` ← `event.title`; tags ← `event.tags`
  - a non-UUID `correlation_id` → `uuid5(NAMESPACE_URL, "sentinel:" + id)`, deterministic, so dedupe holds
  - `pr_details.sha` = the **merge commit** sha
- `git revert -m 1` for merge commits.
- `guard-main-source.yml`'s `${{ github.head_ref }}` script injection is fixed (passed via `env:`) as part of 8.1.
- Every job that runs `azure/login` declares `environment: sentinel-dev`.
- *Amended after review:*
  - Every third-party action in every workflow is pinned by commit SHA.
  - The `stable` → `sha-<7>` lookup lives in ONE composite action, `.github/actions/resolve-stable-tag`.
  - Checkouts that use `REVERT_PR_PAT` set `persist-credentials: false`.
  - Once a revert PR exists, the run reports it even if a later step (the DB record) fails.
- Known limitation: the workflow-level `sentinel-backend` concurrency group holds only ONE pending run, so a third alert arriving while one runs and one waits cancels the waiting run. Scenarios are run one at a time by a human, so this is accepted. Revisit with a queue if alerts ever burst.

**Names the infra CI-identity ticket must create** (GitHub environment `sentinel-dev` vars on `Keshav0375/Sentinel`, unless noted):
- Resource-tenant login: `AZURE_CLIENT_ID` (gha-backend UAMI), `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`.
- Identity-tenant login: `AZURE_IDENTITY_TENANT_ID`, `AZURE_GHA_CLIENT_ID`. The latter is a client app holding `Incident.Write` on the API app.
- API: `SENTINEL_API_TENANT_ID`, `SENTINEL_API_AUDIENCE`. *Amended after review:* this is the same comma list the pod uses (client-id GUID first, optionally the identifier URI). `get-backend-token` takes the list and requests a token for the **first** entry, which must be a GUID. Every caller passes `vars.SENTINEL_API_AUDIENCE` and `tenant: vars.AZURE_IDENTITY_TENANT_ID`.
- Infra outputs: `AKS_RESOURCE_GROUP`, `AKS_CLUSTER_NAME`, `ACR_NAME`, `ACR_LOGIN_SERVER`, `KEY_VAULT_URI`, `PG_HOST`, `PG_DATABASE`, `PG_USER_BACKEND` (the pod's PG principal), `PG_USER_GHA` (the gha-backend PG principal).
- Repo var `SENTINEL_KEEP_WARM`. Environment secret `REVERT_PR_PAT` (user-created).
- Grants:
  - gha-backend gets AcrPush (plus tag delete for cleanup) on ACR
  - Key Vault Secrets User on the deployment KV
  - AKS: start/read plus namespace-scoped RBAC write on `sentinel-dev`, and the cluster-user credential for kubelogin
  - a Postgres principal with `SELECT` on `services` and `SELECT(id)` + `UPDATE(pr_number, pr_url)` on `incidents` only (the `WHERE id = … RETURNING id` needs the column SELECT)
- Plus the earlier items: the API app registration (`Incident.Write`, v2 tokens) and seed-vault.sh adding `anthropic-api-key` and `openai-api-key`.

### 2026-10-24: Backend phase 7 (Container & K8s) contract

User answers to the phase 7 distill conflicts (binding; they supersede the hardcoded names and the stale text in backend §7.1, §8.1, §8.2, §8.5, §9.2 and §13.5):

**Names come from infra.**
- Infra Terraform owns namespace `sentinel-dev` (`<deployment>-<env>`) and ServiceAccount `sentinel-backend`, with its WI client-id annotation. The backend ships no `serviceaccount.yaml`.
- The Deployment sets `serviceAccountName: sentinel-backend` and the pod label `azure.workload.identity/use: "true"`.
- Manifests carry `${VAR}` placeholders (ACR login server, image tag, KV URI, PG host/db/user, API tenant/audience). `backend-up` fills them from Terraform outputs and inputs.
- Every kubectl call is namespaced. No resource name is hardcoded: §8's `sentinelacr0375`, `sentinel-aks`, `sentinel-rg`, `sentinel-kv-0375`, `sentinel-pg-0375`, `PGDATABASE=sentinel`, `PGUSER=sentinel-backend-wi` and the bare `api://sentinel-backend` are void.

**Pod config is a ConfigMap only.**
- `sentinel-config` holds non-secret values only: `SENTINEL_API_TENANT_ID`, `SENTINEL_API_AUDIENCE`, `DD_SITE=us5.datadoghq.com`, `KEY_VAULT_URL`, `PGHOST`/`PGDATABASE`/`PGUSER`, `SENTINEL_PRIMARY_PROVIDER`.
- There is no K8s Secret; the task's `sentinel-secrets` is void.
- `terminationGracePeriodSeconds: 45` (the worst-case shutdown is 37 s).

**Scale-to-zero leaves the shared cluster running.**
- `backend-down` (skipped when `vars.SENTINEL_KEEP_WARM == 'true'`) deletes the Service, which releases the LB IP, and scales the deployment to 0. It never stops the shared cluster.
- `backend-up` runs `az aks start` only when the cluster is stopped.
- Stopping the cluster is a separate, manual operation.

**LLM credentials live in Key Vault.**
- Secrets `anthropic-api-key` and `openai-api-key` are added to KV (seed-vault.sh) and read once at startup via workload identity, like the DD and Langfuse secrets.
- This replaces the 2026-08-30 LLM WIF deferral.
- No `ANTHROPIC_API_KEY`/`OPENAI_API_KEY` env var is set in the pod.

**The CI identity is an infra ticket.**
- Phase 7 actions take client ID, tenant and audience as inputs and are validated offline (actionlint plus dry-run).
- A tracked infra task, due before backend phase 8, adds:
  - a `gha-backend` identity with a FIC for `repo:Keshav0375/Sentinel` environment `sentinel-dev`, plus AKS / KV / AcrPush grants
  - the API app registration with the `Incident.Write` role
  - root outputs: ACR login server, KV URI, backend UAMI client ID, API app client ID

*Amended after review (2026-10-24):*
- Callers log in. A workflow runs `azure/login` (OIDC) before using the actions, so the actions take no client-id or tenant input. Only `get-backend-token` takes `audience` and an optional `tenant`.
- `get-kv-secrets` takes the **KV URI** (the infra root output) and derives the vault name from it.
- `backend-up` applies the manifests bundled with the SHA-pinned action (`github.action_path`), never the caller's workspace, and validates every rendered value (no quotes or newlines, plus per-field patterns).
- The pod sets `automountServiceAccountToken: false` (workload identity injects its own projected token) and `readOnlyRootFilesystem: true`, with emptyDir mounts for `/app/reports` and `/tmp`.
- The image base is pinned by `@sha256` digest, and the embedding model by `revision=`.

**The Dockerfile installs from poetry.lock.**
- Multi-stage: the builder installs main deps from `poetry.lock`, with torch from the CPU wheel index.
- The runtime is `python:3.12-slim` with the venv plus `src/`, `alembic/`, `alembic.ini`. There is no `data/` and no requirements.txt.
- Build target `linux/arm64`.
- CMD is uvicorn with `--timeout-graceful-shutdown`.

**pip-audit exception (user ruling, 2026-10-24).**
- filelock CVE-2026-112940, CVE-2026-112913 and CVE-2026-112907 are fixed only in filelock 4.2.1, but litellm (≤1.106.2) caps filelock `<4.0`.
- The gate passes `--ignore-vuln` for exactly those three IDs (`scripts/quality_gate.py`, landed via `fix/pip-audit-filelock-ignore` → `release-phase-2`).
- Re-check by **2026-11-24**. Drop the ignores as soon as litellm lifts the cap.
- setuptools was bumped to 84.2.1 (GHSA-xmj3-9gf7-h52w fixed), and filelock to 3.32.7.

**Orchestrator rulings.**
- Action I/O names follow §9: `get-db-token` → `pg-token`, `get-backend-token` → `bearer`, `psql-exec(sql, pg-token)`.
- There are seven actions, used cross-repo pinned by commit SHA, never `@main`.
- A NetworkPolicy allows TCP 8000 ingress to `app: sentinel-backend` from the world (LB) under Cilium.
- Action inputs reach `run:` only through `env:`, and SQL values travel only as `psql -v` vars.

### 2026-10-22: Backend phase 6 (Eval) contract

User answers to the phase 6 distill conflicts (binding):
- **The runner is a read-only scorer (HITL).** Backend code never merges, deploys or reverts scenario branches. A human runs scenarios by merging a branch's PR; GHA deploys; Sentinel drafts the revert PR. `src/sentinel/eval/runner.py` reads the finished trajectories from a LangFuse dataset. Each dataset item carries its `branch` label, which the runner joins to `scenarios/branches.yaml`. It scores four ground-truth checks (fired, classified `signal_type`, correlated culprit, revert-PR target), each pass = 1 / fail = 0, and also the judge's reasoning dimensions. The offline fixture is a vendored copy of `branches.yaml` under `tests/`. The runner does not depend on `data/` or `sentinel.generator`. §13.2 (runner row) is amended to match.
- **Score scale 0–1.** Every judge dimension and ground-truth check is a NUMERIC LangFuse score in [0,1]. The existing 0–5 models change.
- **Eval route stays `GET /api/eval-report`** (phase 5, behind the bearer). §1.1's `/eval/results` is amended. The runner writes the report that route reads.
- **`incidents.eval_score` JSONB** = `{judge_model, judge_conflict, scores: {dimension: value}, reasoning: {dimension: text}}`, written by a new `EpisodicMemory` method.
- The judge model is per §4.7 / 2026-10-18 (not Haiku); the spec's "Haiku" wording is stale.

*Amended after review (2026-10-22):*
- The LangFuse dataset is named **`sentinel-scenario-runs`**, and its item schema is documented in `src/sentinel/eval/runner.py`.
- The judge rubric anchors on `branches.yaml` ground truth:
  - triage = `expected_signal_type` (+ `expected_failed_stage`)
  - root cause = `fault` / `expected_culprit`
  - remediation = `expected_resolution` + `expected_culprit`
- A judge failure is flagged (`judge_failed`) and, like `judge_conflict`, never pushed or aggregated.
- The runner persists `incidents.eval_score` for items that carry an incident id.
- The judge prompt treats the trajectory as untrusted data, and the reasoning must never quote secrets or raw log values.

### 2026-10-19: Backend phase 5 (API & App) contract

**Auth (§3.6, amended)**
- Entra bearer only. The audience comes from `SENTINEL_API_AUDIENCE`, default `api://<identity_tenant_id>/sentinel-backend-<deployment>-<env>`, which is infra's naming (modules/naming). New tenants reject the bare `api://sentinel-backend`, so it is dropped.
- **`SENTINEL_API_TENANT_ID`** (Settings `sentinel_api_tenant_id`, R4's name; *amended same day*) is the **identity tenant** where the app registration lives. `AZURE_TENANT_ID` keeps its meaning: the resource (school) tenant of the pod's workload identity, which azure-identity uses. Only the **v2** issuer `https://login.microsoftonline.com/<tid>/v2.0` is accepted, and the app registration must set `accessTokenAcceptedVersion = 2`.
- RS256 via `PyJWKClient` on `…/<tid>/discovery/v2.0/keys`.
- A bad, expired, wrong-aud or wrong-iss token → 401. A missing `Incident.Write` role → **403**.

*Amended after review:*
- **Entra v2 access tokens always carry `aud` = the API app's client-id GUID**, not the `api://` identifier URI.
- `SENTINEL_API_AUDIENCE` is therefore a comma-separated list of accepted audiences: the app's client ID (required for v2) and optionally its identifier URI. It is **required config with no default**; the backend cannot derive the deployment/env name. Phase 7 sets it from the infra app registration's outputs.
- Unset means every protected route returns 401 and the startup log says `auth_not_configured`, which fails safe.

**Open routes:** only `/health` and `/ready`. Everything else is behind the bearer, including the Phase-1 dashboard pages' APIs, SSE events, scenarios, eval-report, `GET /api/config` and trajectories. `SENTINEL_DEV_OPEN_DASHBOARD=1` (default off, never set in the pod) opens the dashboard routes for local use only.

**Webhook (§3.1)**
- `POST /webhooks/incident` replaces `/webhooks/alert`.
- `IncidentPayload` requires `signal_type`, `correlation_id` and `title`. All other §3.1 fields are optional: severity defaults to `"unknown"` (`incidents.severity` is NOT NULL), and tags may be an object or a Datadog comma string.
- The Phase-1 `AlertPayload` is replaced as `PipelineInput`'s alert by a model built from `IncidentPayload`; there is no metric/threshold.
- Dedupe on `correlation_id`: a duplicate → 202 with the ORIGINAL `incident_id` and `status: "duplicate"`. Lookup is an in-memory TTL map (24 h) plus the DB.
- `context.pr_details.sha`, when present, is passed to the orchestrator. On the `deploy_failure` fast path the drafted target must match it, or the incident escalates.

**Queries (§3.2):** response shapes are the §5.3 `incidents` columns (no embedding). In-flight incidents are served from short-term memory with `status: "in_progress"`. `/incidents/{id}/deploy` returns the `deployments` row whose `incident_id` = id. **The pipeline sets `deployments.incident_id` on the verified target row when it ends `rollback_proposed`.** That is a write to Sentinel's own DB, not to an external system.

**Generate (§3.4):** the service comes from the stored incident. An unknown incident → 404; a `target_deploy` with no matching `deployments` row → **409**. It returns text only.

**Probes (§3.5):**
- `/health` → exactly `{"status": "ok"}`.
- `/ready` → 200 `{"status": "ready"}` when the app is wired and the DB pool pings (or no DB is configured in fake/dev mode); otherwise 503 `{"status": "not_ready"}`. No LLM-provider check: keys may legitimately be absent until phase 7.

**Runtime config (§8.2)**
- LLM keys come from the **environment** (WIF in phase 7, 2026-08-30).
- Key Vault is optional (`KEY_VAULT_URL` unset → env only). It supplies `datadog-api-key`→`dd_api_key`, `datadog-app-key`→`dd_app_key`, `langfuse-public-key`/`-secret-key`/`-base-url` via `DefaultAzureCredential`. The backend's PR-read PAT stays env-only for now (a vault entry is phase 7).
- DB: `DATABASE_URL` wins when set (local/CI). Otherwise `PGHOST`/`PGDATABASE`/`PGUSER` with an Entra token (`https://ossrdbms-aad.database.windows.net/.default`) supplied by the pool's password callable, fetched per new connection (azure-identity caches and refreshes).
- New deps: `pyjwt[crypto]`, `azure-identity`, `azure-keyvault-secrets`.

### 2026-10-18: Judge model distinct from every agent model (supersedes the 2026-10-15 judge rule)

**Why the old rule failed.** The 2026-10-15 rule (judge = the non-primary provider's `gpt-4o`) self-grades. `openai/gpt-4o` is also the §4.7 **fallback** model for orchestrator, analysis and resolution, so any 429, timeout or missing Anthropic key has gpt-4o score gpt-4o.

**Decision.**
- The judge uses a model **no agent role uses, primary or fallback**: `openai/gpt-4.1` when primary = anthropic, `anthropic/claude-opus-4-1` when primary = openai.
- A static check asserts the judge ∉ every role's (primary, fallback).
- A **runtime guard** marks any eval run whose `models_used` contains the judge model as `judge_conflict`: its score is invalid and not counted.
- The judge still has no fallback.

§4.7's Judge row is amended accordingly.

### 2026-10-15: Backend phase 4 — pipeline shape, providers, judge, status, R14

- **The orchestrator is Python code, not an LLM agent with handoffs,** so every cap is enforced in code:
  - a per-incident tool-call counter (`sentinel_max_tool_calls` = 20), counted across every `Runner.run` including fallback re-runs; exhaustion escalates with context
  - reflexion ≤ 2 loops, when confidence < 0.7
  - reverification FAIL ≤ 1 retry
  - the rollback target cross-checked against a `deployments` row for the incident's service (failed rows allowed)
- **Six LLM agents (§4.2):**
  - `triage` (get_service_metadata, search_past_incidents)
  - `analysis` (fetch_logs, get_deploy_details; merges the Phase-1 `log_analyst` + `deploy_correlator`)
  - `reflexion`
  - `resolution` (prepare_rollback_spec, format_escalation; the renamed `remediation`)
  - `reverification`
  - `pr_content_generator` (no tools)

  The `comms` agent is deleted: GHA posts to Teams. Prompt, Langfuse prompt and file names follow the agent names.
- **The plan step reads `signal_type`** from a phase-4 `PipelineInput{incident_id, alert, signal_type, correlation_id}`. `deploy_failure` takes the fast path to `prepare_rollback_spec` on the failed deploy's SHA, still confidence-gated and reverified. `runtime_error` runs the full loop.
- **Providers: Anthropic and OpenAI only** (§4.7). Groq, Azure and Gemini settings, resolver prefixes and deps are removed.
  - A fixed per-role model map (§4.7 table) is selected by `sentinel_primary_provider` (`anthropic` | `openai`, default `anthropic`).
  - The `PUT /api/config` model-repointing ability is removed.
  - Use `agent.clone(model=…)`; `Agent.with_model` does not exist in openai-agents 0.6.4.
  - A missing primary-provider credential falls back to the other provider. If neither is available, the incident escalates.
  - The fallback catches the `openai.APIError` hierarchy (litellm's RateLimit/Timeout/APIError) plus asyncio/builtin timeouts.
  - `SENTINEL_FAKE_LLM=1` gives a deterministic, no-network model for every role.
- **Judge = the non-primary provider:** `openai/gpt-4o` while agents run on Anthropic, `anthropic/claude-sonnet-4-6` when primary is OpenAI. Code enforces judge ≠ every agent model. This supersedes the §4.7 Judge row and resolves the self-grading follow-up.
- **Terminal incident statuses are `rollback_proposed` | `escalated`.** `pending_approval` is removed from `IncidentStatus` and `IncidentSummary`. `resolved` is reserved for a later "revert deploy succeeded" signal.
- **R14 (closed): a custom add-only openai-agents `TracingProcessor` bridges each LLM generation span to a Langfuse `generation` observation.**
  - It carries model, input/output token usage, and the agent's `TextPromptClient` (prompt-version link, §6.3).
  - It exports no inputs/outputs, so no tool or log data reaches Langfuse.
  - It registers via `add_trace_processor` only.

*Amended 2026-10-15:* the openai-agents **default OpenAI trace exporter is removed**. It uploaded full spans, including LLM inputs and outputs with tool and log data, to OpenAI whenever `OPENAI_API_KEY` was set. Startup now calls `set_trace_processors([...])` **once**, with exactly Sentinel's processors (SentinelTracer, DashboardEventEmitter, the Langfuse generation bridge), never omitting one of ours, and runs set `trace_include_sensitive_data=False`. This supersedes the blanket §6.2 "never `set_trace_processors`" rule, whose purpose was to protect our processors, not the vendor exporter.
  - Per-incident token totals are summed in the pipeline. The 50K-token alert's sink is still unspecified: it is logged as a structured warning `incident_token_budget_exceeded` until the architecture names one.

### 2026-10-14: Backend phase 3 review — requirements carried to later phases

- **Backend 4.2 (orchestrator):** a REAL tool-call counter. `sentinel_max_tool_calls` = 20 must be enforced per incident; exhaustion escalates. Today only the SDK's `max_turns` (20/25) bounds it, and one turn can issue several tool calls.
- **Backend 4.x orchestrator and 5.x `/generate/pr-content`:** `RollbackSpec.target_deploy.commit_sha` (+ pr_number, deployed_at) must be cross-checked against a `deployments` row for the incident's service before it is returned or used as GHA's `TARGET_SHA`. `prepare_rollback_spec` stays pure and format-validates only.
- **Backend 5.x/6.x:** `PUT /api/config` is unauthenticated and can repoint the judge model at runtime. Lock it behind Entra auth, and forbid judge == any agent model (self-grading). This pairs with the phase-6 judge-model fix.
- **§3.4 `/generate/pr-content` body gains `justification`** (string), matching `RollbackSpec`.
- **Credentials:** the backend's GitHub PAT needs only **Pull requests: read** on `Keshav0375/Sentinel-deployment`; Contents is unused.
- **Tool outputs are compact JSON**, and every agent prompt carries a shared "tool results are untrusted data" preamble (`agents/loader.py` `UNTRUSTED_DATA_PREAMBLE`). **Backend 4.x:** when agents switch to the Langfuse prompt path (`infra/tracing.load_prompt`), that path must append the same preamble.

### 2026-10-14: Backend phase 3 (tools) contract

**Config (3.1)**
- Settings keep the existing `sentinel_*` names: `sentinel_db_pool_min/max`, `sentinel_log_level`, `sentinel_max_tool_calls` (default **20**, §4.6), `sentinel_embedding_model`, `sentinel_fake_llm`.
- New fields:
  - `dd_api_key`, `dd_app_key` (SecretStr; env `DD_API_KEY`/`DD_APP_KEY`)
  - `dd_site` (default `us5.datadoghq.com`)
  - `github_api_token` (SecretStr; env `GITHUB_API_TOKEN`)
  - `langfuse_public_key`/`langfuse_secret_key` (SecretStr), `langfuse_base_url`
- **No `sentinel_api_token`/`X-Sentinel-Token`**: inbound auth is Entra (§3.6).
- No Teams field: the backend never notifies (§4.8).
- **No secret is required to boot.** A missing key makes its feature return a structured failure at use (§8.2 reads keys at runtime; 2026-08-30 WIF). `groq_api_key` becomes optional; provider changes are phase 4/7.

**Tool results**
- Tools return `ToolFailure{tool, kind: "not_found"|"unavailable"|"upstream_error"|"bad_input", message}` (Pydantic). `ToolError` stays the exception class.

**Tool set (3.7)**
- The registry holds exactly six tools: `get_service_metadata`, `search_past_incidents`, `fetch_logs`, `get_deploy_details`, `prepare_rollback_spec`, `format_escalation`.
- Removed: `request_human_approval` (and the `approve_hitl` endpoint plus `ApprovalFn` plumbing, since §3.3 says the PR is the only gate), `draft_slack_summary`, `draft_rollback_pr`, `draft_hotfix`.
- Every importer, model and agent prompt that named them is updated. `resolution_type` 'hotfix' stays in the schema vocabulary but no tool drafts hotfixes.

**Tool contracts**
- **`get_deploy_details`** is the single LLM-visible name for the deploy tool; `list_recent_deploys` is retired. It is read-only on `deployments` (window_hours, ordered by time, `failed` rows included). GitHub enrichment is optional and read-only. The `deployments.incident_id` backfill is NOT a tool action.
- **`search_past_incidents`** returns `SimilarIncident{id, service, created_at, root_cause, resolution, resolution_type, similarity, model_generated: true}` (`created_at` and `service` added 2026-10-14 so triage can apply its "similar and within 2 h" duplicate rule). It keeps the "model-generated, unverified" label and uses `EpisodicMemory.query(symptom_text, top_k)` (embeds the text itself and returns scores).
- **`fetch_logs`** returns a new `LogFetchResult` type; `LogAnalysis` stays the log-analyst agent's output. The evidence sources are only what really exists:
  - the failing **Datadog Synthetics** results for the service (status, assertion failures, response-header/body snippet, latency) via the Synthetics API
  - the **CI pipeline logs** (`deploy.completed`) via `POST https://api.${DD_SITE}/api/v2/logs/events/search`

  The app itself sends no runtime logs, and log forwarding is a later option. The search POST counts as a read. 3 attempts with 1/2/4 s backoff on transient errors; never captured to Langfuse.
- **`prepare_rollback_spec`** returns `RollbackSpec{incident_id, root_cause, evidence_summary, confidence, justification, resolution_type: "rollback", target_deploy{pr_number, commit_sha, deployed_at}}`. That is the §3.4 `/generate/pr-content` body; the workflow's `TARGET_SHA` = `target_deploy.commit_sha`. Pure, with no I/O. **`format_escalation`** → `EscalationContext{hypothesis, evidence, confidence, missing}`, also pure.

**Credentials: read-only, owner-created (live check only; tests use mocks)**
- A fine-grained GitHub PAT on `Keshav0375/Sentinel-deployment` with **Pull requests: read** only (Contents is unused; amended same day). It is never the bridge's write-capable `github-pat`.
- A Datadog application key scoped to `logs_read_data` and `synthetics_read`.

### 2026-10-14: Backend phase 2 review amendments

- **`store_incident` writes `resolved_at`** when the model has it (`mttr_seconds` derives from it). The 2026-10-12 mapping's NULL list was meant only for columns the model cannot supply.
- **The trace root opens via `get_client().start_as_current_observation(name="incident-pipeline", trace_context={"trace_id": UUID.hex})`,** exposed as `trace_incident(...)`. It is equivalent to the §4.5 `@observe` + `langfuse_trace_id=`: same trace id, name and propagated attributes.
- **`configure_langfuse()` runs at import.** A blank `LANGFUSE_*` key counts as missing (it is removed from the env) and the SDK's keyless warning is muted. This implements "degrade gracefully".
- **The re-exported `observe` defaults to `capture_input=False, capture_output=False`.** v3 would otherwise ship every observed function's arguments and returns (raw logs, full prompts) to Langfuse. Callers opt in per function.
- **Memory provenance.** `incidents.trajectory.provenance = {root_cause_by, resolution_by, model_generated: true, stored_at}`. The episodic embedding uses observed symptoms only, never earlier agent hypotheses. `search_past_incidents` labels recalled root causes and resolutions "model-generated, unverified".
- **A NULL `services.tier` reads as `standard`** (logged). Only an invalid non-NULL value raises.
- **Follow-up for backend phase 6 (eval):** `sentinel_judge_model` defaults to the triage model (`groq/llama-3.1-8b-instant`). That is self-grading. §5 specifies `anthropic/claude-haiku-4-5`, which is blocked on B4/WIF.

### 2026-10-12: Phase-1 models ↔ §5.3 schema mapping (backend phase 2)

The §5.3 DDL binds; Phase-1 models adapt to it, and phase 4 rewrites the pipeline anyway.

1. **IDs are UUIDs.** `Incident.id` is generated as `str(uuid4())`, not `inc-xxxxxxxx`. `incidents.id` stores it as UUID. `EpisodicRecord.id` is `str(UUID)`, and the trace id is `UUID(id).hex` (§4.5).
2. **`symptoms`** (no column) and the timeline live in `trajectory` JSONB as `{"symptoms": <text>, "timeline": <raw_timeline>}`. On read, `EpisodicRecord.symptoms` and `raw_timeline` come from there. The embedding is computed from the symptoms text.
3. **`store_incident` maps the fields the model has.** `alert_id` comes from `incident.alert.alert_id`; service, severity, root_cause, resolution, mttr_seconds, created_at, embedding and trajectory map directly; `status` is the `IncidentStatus` value (TEXT, no CHECK). Columns the model can't supply (correlation_id, dd_event_id, langfuse_trace_id, reflexion_loops, root_cause_confidence, resolution_type, pr_*, eval_score, resolved_at) stay NULL/default until the phase-4 pipeline writes them.
4. **Service fields.** `ServiceMetadata.oncall_channel`, `description` and `repo_url` come from `services.metadata` keys. `repo_url` is `https://github.com/<metadata.repo>` when only `repo` is present. `services.runbook` maps to `Runbook(id=f"{service}-runbook", service_name, failure_class=<requested or "general">, steps=<the markdown's numbered or bulleted lines; whole text as one step if none>)`. `search_services(embedding, k)` returns `list[tuple[ServiceMetadata, float]]` (similarity = 1 − cosine distance).
5. **Protocol unchanged.** `search_similar(symptoms: str, *, top_k)` still embeds the text itself. A new `search_by_embedding(embedding, *, top_k)` takes a caller-supplied vector.
6. **IVFFlat recall.** Every similarity query runs `SET LOCAL ivfflat.probes = <index lists>` in its transaction (incidents 10, services 5), so small or freshly built tables never miss rows.

### 2026-10-12: Backend phase 2 — memory is Postgres-only; runbooks live in `services.runbook`

- **Episodic and semantic memory take the asyncpg pool, not a SQLite path.** `infra/db.py` and `sentinel_db_path` become dead code for memory; phase 9 deletes them. With no `DATABASE_URL` the app still boots (pool = None), but every memory call raises `SentinelMemoryError`, and the tools report "memory unavailable". There are no silent empty or fake results.
- **Runbooks have no table of their own.** 001 holds one runbook per service in `services.runbook`. `get_runbook(service, failure_class)` returns it, ignoring `failure_class`, and `get_all_runbooks` lists them.
- **Service lookups:** by name is an exact `WHERE name = $1`. Symptom search must not depend on IVFFlat recall at `probes=1` (phase-1 finding): set `ivfflat.probes` high enough for the table size, or scan exactly.
- **`LANGFUSE_BASE_URL` is the setting name** (Langfuse v3 reads it first). `.env.example` and backend task 3.1 drop `LANGFUSE_HOST` / `langfuse_host`.
- **Deferred as R14:** per-LLM-call token/cost capture inside openai-agents' Runner (§6.1 cost tracking).

### 2026-10-12: Langfuse v3 API in §4.5/§6

Follows 2026-10-10 (pin v3). Verified against the installed `langfuse 3.15.0` source and the Langfuse
docs. backend.md §4.5, §6.1 (Tracing row), §6.2, §6.3, §6.4 and backend task 2.4 are rewritten; the
changed blocks are marked "(v3 API, amended 2026-10-12)".

- **API mapping (v2 → v3):**
  - `Langfuse()` module global → `get_client()` singleton (`Langfuse(...)` still exists)
  - `from langfuse.decorators import observe, langfuse_context` → `from langfuse import observe, propagate_attributes, get_client`
  - `langfuse.trace(name=, id=str(incident_id), metadata=)` → root `@observe(name="incident-pipeline")` called with `langfuse_trace_id=incident_id.hex`; no trace object exists
  - `RunContext.langfuse_trace` (object) → `RunContext.langfuse_trace_id` (str, from `get_current_trace_id()`)
  - `langfuse_context.update_current_trace(metadata, tags)` → `propagate_attributes(metadata=, tags=)` (v3's recommended form; `get_client().update_current_trace` still exists)
  - `langfuse_context.update_current_observation` → `update_current_span` / `update_current_generation`
  - `@observe(as_type="tool")` → unchanged spelling. It is now a real type; v3 types: span, generation, embedding, agent, tool, chain, retriever, evaluator, guardrail. Agents use `as_type="agent"`.
  - `get_prompt(name, cache_ttl_seconds=300)` / `.compile()` → unchanged. Prompt → generation link is `update_current_generation(prompt=prompt_client)`.
  - `langfuse.score(trace_id=, name=, value=)` → `create_score(trace_id=, name=, value=, data_type="NUMERIC")`. Inside a live trace you can use `score_current_trace` / `score_current_span`.
  - `flush()` → unchanged; `shutdown()` is also registered at `atexit`
- **Behaviour differences that matter:**
  - **Trace ids are W3C, 32 lowercase hex.** `str(uuid)` (with dashes) is invalid. We use `incident_id.hex`, the same UUID without dashes, which `incidents.langfuse_trace_id` stores, so incident ↔ trace stays 1:1.
  - **Context is OTel `contextvars`.** An asyncio Task inherits the span that was current when it was created; `asyncio.to_thread` copies it too, but `run_in_executor` does not. Incident tasks are created outside any span, so they stay separate traces.
  - **Trace attributes.** `propagate_attributes` metadata values must be str ≤200 chars, and only spans created after entering it carry them, so enter it first thing.
  - **Exporting is a background OTel batch.** The FastAPI lifespan calls `shutdown()` and eval/CLI entry points call `flush()`. Otherwise scale-to-zero or SIGTERM can drop the tail of a trace.
  - **Missing keys give a disabled client** (warning, no-op tracer): `@observe` and `create_score` become silent no-ops. But `get_prompt` **raises** ("SDK is not correctly initialized"), and v3's `fallback=` argument never runs in that case, so §6.3's try/except file fallback is mandatory.
- **Env var: `LANGFUSE_BASE_URL` is correct for v3.** Resolution order: `base_url=` arg → `LANGFUSE_BASE_URL` → `host=` arg → `LANGFUSE_HOST` (deprecated) → `https://cloud.langfuse.com`. This matches KV/`seed-vault.sh`/`ci_infra.yml` (B7). Drift to fix in their own tasks:
  - `Sentinel/.env.example` still says `LANGFUSE_HOST`
  - backend task 3.1 (config) names the setting `langfuse_host`; it should be `langfuse_base_url`
- **openai-agents coexistence.**
  - openai-agents 0.6.4 traces via its own `TracingProcessor` system, not OTel, and Langfuse v3 has no native hook into it.
  - Langfuse's documented integration is the third-party `openinference-instrumentation-openai-agents` (`OpenAIAgentsInstrumentor().instrument()`). It re-emits Agents-SDK spans as OTel spans, which the Langfuse client exports. That package is not installed or listed in §11.
  - Langfuse sets the global OTel `TracerProvider` only if none exists.
  - Any route must add processors (`add_trace_processor`), never replace them (`set_trace_processors` / `set_tracing_disabled`), or `SentinelTracer`/`DashboardEventEmitter` stop.
- **⚠️ FLAGGED — contracts v3 cannot meet without a decision we don't have:**
  1. **§6.1 Cost Tracking and "each LLM call = 1 generation".** Token usage and model only exist on `generation` observations. `@observe` on an agent wrapper does not create them, because the LLM calls happen inside `Runner.run` → `LitellmModel`. Meeting this needs a new dependency or a custom bridge from the Agents-SDK processor to `start_observation(as_type="generation")`. **Undecided — needs an R-item.** Until then the 50K-token alert and per-agent cost are unmet, and task 2.4 ships span tree + latency only.
  2. **§6.3 "versioning shows which prompt version produced which scores".** In v3 the prompt link is made on the generation, so it depends on (1). It is not met until (1) is decided.
  - Not answered from the installed code (openinference is not installed): whether OpenInference spans nest under the active `@observe` span. Verify when (1) is decided.

### 2026-10-10: Backend phase 1 — real service registry, Langfuse v3, `SentinelMemoryError`

- **The `services` registry holds the one real service: `sentinel-watchtower`.** It replaces the 8 Phase-1 acme-corp fixtures, because fake services don't belong in the real DB (§13.1). Row:
  - team `sentinel`, tier `standard`, dependencies `[]`
  - metadata: repo `Keshav0375/Sentinel-deployment`, platform `azure-app-service-f1`
  - runbook: the revert-PR rollback procedure, with a pointer to `Sentinel-deployment/scenarios/README.md`
  - embedding computed at seed time with the existing `EmbeddingClient` (all-MiniLM-L6-v2, 384)

  Test fixtures may still use synthetic services; the real seed must not.
- **Langfuse v3.** An unconstrained `langfuse` resolves to v3, and §6.2/§4.5 use v2-only APIs (`langfuse.decorators`, `langfuse.trace`). Pin v3 now. §6.2/§4.5 are rewritten to the v3 API before backend phase 2 (tracing) builds them.
- **The DB error is `SentinelMemoryError`, not `MemoryError`.** The old name shadows Python's built-in out-of-memory exception, so a broad `except MemoryError` would swallow real OOMs. The hierarchy lives in `src/sentinel/exceptions.py`: `SentinelError` → `ToolError`, `SentinelMemoryError`, `AgentError`, `EvalError`. `CONVENTIONS.md`/`CLAUDE.md` in `Sentinel` are updated with it.
- **Defaults chosen for this phase:**
  - `create_pool` takes an optional `password` (str or callable), so it can use refreshed Entra tokens later (the server is password-less).
  - Settings `database_url`, `sentinel_db_pool_min` (2) and `sentinel_db_pool_max` (10) match the existing `.env` names.

### 2026-10-07: Scenario catalog redesigned for determinism (deploy phase 3)

The architecture review found that roughly half of the original §4.1 faults could not produce their label on the stack as built.
- **Terraform-owned settings:** the start command, env and port are not repo changes.
- **Undetectable runtime faults:** load, payload, intermittent and uptime-relative faults can't be caught by synthetics that send `GET /` and `GET /health` every 30 min, on an F1 app that restarts after idle.
- **A random fault:** the 60 s lifespan sleep usually passes verify.

**Decision:** replace the catalog with 30 deterministic, repo-only faults (deployment.md §4.1, exhaustive) and record the dropped ones with reasons.
- **Verify-stage failures leave the broken version live** (no slots). "Previous version stays live" is true only for build/deploy-stage failures.
- **Branches that also trip a synthetic** carry `also_expected: [runtime_error]`. The ground truth is one deploy, two correlated alerts.
- **Rejected: pipeline auto-rollback.** GHA would remediate on its own, which breaks HITL.
- **The `GET /` synthetic gains assertions:** `content-type` contains `application/json`, and `$.message == "ok"`. There is still no latency assertion, because F1 cold starts would false-alarm.
- **Enum fix:** `expected_signal_type` for case i is `none` (was `—`).

### 2026-10-07: Synthetics every 30 min; deploy only on app-affecting paths

- **The runtime-health synthetics run every 30 minutes**, with one retry a minute later (`tick_every: 1800`, `retry {count 1, interval 60s}`, `min_failure_duration: 0`). They no longer run every 5. F1 sleeps after about 20 idle minutes and has a 60 CPU-minute daily quota. In the first live run the 5-minute checks cold-started gunicorn all day and put the app into `QuotaExceeded`, so the next deploy got a Kudu 403. The monitor broke the thing it watches. A condition-B demo now alerts within about 30 minutes; trigger "Run test now" to demo faster.
- **`ci_app_deployment.yml` triggers only on `app/**`, `requirements.txt`, the workflow itself, `dd-report` and `.github/scripts/**`.** A datadog/, tests/ or docs-only merge has nothing to deploy and would report a false `deploy_failure`. All 30 scenario branches touch app/ or requirements.txt, so all of them still deploy.

### 2026-10-05: Deploy phase 2 — no required check, `succeeded|failed`, synthetic runtime monitor, local monitor apply

- **No required status check on `Sentinel-deployment` `main`.** `ci_app_deployment.yml` runs only on push to `main`, so it can never report on a PR. `deployfail/*` scenario branches are deliberately broken and must stay mergeable. "PR required" plus the environment's main-only policy is the whole merge gate.
- **One status vocabulary: `succeeded` | `failed` | `rolled_back`.** The same `$STATUS` feeds the Datadog `deploy_status` tag and `deployments.deploy_status`. backend §5.3 is amended before backend phase 1 builds it.
- **Runtime-health = Datadog Synthetics API tests** on `GET /` and `GET /health`: 1 location, every 5 min. The app sends nothing to Datadog, and an Azure integration would need a long-lived credential.
- **Monitors and the Datadog→Event Grid webhook are applied locally by the owner** with `datadog/apply.sh` (Datadog app key from the local env file, never CI). The webhook posts a **flat JSON body** (`title`, `tags`, `alert_transition`, `link`, `alert_id`, `date`) with the `aeg-sas-key` header. *Amended the same day:* Datadog's template variables cannot produce the ISO-8601 `eventTime` that Event Grid's default schema requires, so the topic uses `input_schema = "CustomEventSchema"` with input mappings (`subject` ← `alert_id`, `eventType` default `datadog.monitor`, `dataVersion` default `1`). Event Grid stamps `id`/`eventTime` itself, the flat body becomes `data`, and the bridge is unchanged. Its mention is gated `{{#is_alert}}` so recoveries never dispatch. Re-run after each estate recreate, because the topic key changes.
- `deployments.dd_deploy_event_id` stays NULL in this phase; nothing captures the event id yet.

### 2026-10-05: Deployment pipeline prerequisites — `gha-app`, inline SQL, record-stage policy (R7, R8, R11, R12, R13)

**R7 — a fourth CI identity, `gha-app`.** A user-assigned identity in `rg-sentinel-bootstrap`
(created by `scripts/bootstrap-identities.sh`, like the other three), so its client ID is
stable across every destroy/recreate of a deployment and the GitHub secret is pushed once.
It federates exactly one subject, `repo:Keshav0375/Sentinel-deployment:environment:sentinel-dev`.
It holds **no subscription-scope role**. The deployment layer grants it `Website Contributor` on
the deployment's App Service only (gated on the `app_service` component). New FICs on
`gha-deploy` were rejected: that identity can empty the subscription, and the app pipeline
runs on every merge to a repo whose branches are deliberately broken.

**R11 — root outputs** `app_name`, `app_url`, `deployment_resource_group` and `database_name`.
They are deployment-layer outputs, consumed by the secret push (R8).

**R12 — `gha-app` is a database principal, not a server admin.** The human Entra admin runs
`pgaadauth_create_principal('gha-app', false, false)` and grants CONNECT on the deployment
database, plus INSERT/SELECT on `deployments`, through an idempotent
`scripts/grant-db-access.sh`. Terraform cannot do this because there is no resource for
in-database roles (infra §3.2). The role is bound by object ID
(`pgaadauth_create_principal_with_oid`), not by display name.
*Amended same day after review:* only a table's owner can grant on it, and `deployments` will be
owned by backend phase 1's migration role. So **that migration grants**
`INSERT, SELECT ON deployments TO "gha-app"` (guarded on the role existing), recorded as an
acceptance criterion on backend task 1.3. `grant-db-access.sh` only **verifies** it with
`has_table_privilege` and exits non-zero if it is missing. PUBLIC keeps the default CONNECT on
the shared server's databases. This is accepted: CONNECT alone reaches no table.

**Merge gate.** Environment `sentinel-dev` allows deployments from `main` only, and `main`
requires a pull request. Together they mean only merged code can mint a `gha-app` token. The
basic-auth publishing flags are off. Website Contributor could switch them back on, which is
accepted because of the main-only gate, and the next apply reverts the drift.

**R13 — SQL inline in `ci_app_deployment.yml`.** The workflow does not use cross-repo
`get-kv-secrets` / `psql-exec` actions. The token comes from
`az account get-access-token --resource-type oss-rdbms` (after OIDC login as `gha-app`), and
`psql` runs on the runner. Values go in through `psql -v` variables, never string-built SQL,
because PR titles and authors are attacker-influenced text.

**Record-stage policy.** Stage 5 is `continue-on-error`. A failed record is reported to
Datadog as `stage:record` and **never changes `deploy_status`**: the run's colour describes the
deploy, not bookkeeping. Until backend phase 1 creates `deployments`, the record stage fails
visibly with "relation does not exist". The end-to-end "a row exists" check is deferred to
after backend phase 1 and is not claimed by deploy phase 2.

**R8 — distribution.** GitHub environment `sentinel-dev` in `Sentinel-deployment`.
Secrets: `AZURE_CLIENT_ID` (gha-app), `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`,
`DD_API_KEY`. Variables (not secret, not masked): `AZURE_RG`, `APP_NAME`,
`DEPLOYED_APP_URL`, `PG_HOST`, `PG_DATABASE`, `PG_USER`, `DD_SITE=us5.datadoghq.com` (the org is on US5 — verified 2026-10-05; every Datadog URL is built from `DD_SITE`, never hardcoded). The values
are deterministic (uid = `sha1(sub-dep-env)[0:4]`), so they are pushed once rather than resolved
per run.

### 2026-10-04: Target app identity `sentinel-watchtower`; exact-pinned deps; `expected_culprit` label

**Decision 1 — service name (closes R10).** The deployment target's logical service name is
`sentinel-watchtower`. It is the Datadog `service` tag, the `deployments.service` value, the
key every monitor query filters on and the app's `dd_service` default. It is deliberately
**not** the Azure resource name (`app-<dep>-<env>-<uid>`): that name is unreadable in a facet
and a rename would silently break every historical deploy↔incident join. `dummy-api-0375`
was a placeholder and is retired as an identity; the resource-name occurrences left in
`deployment.md` are R9's rewrite.

**Decision 2 — every app dependency pinned `==`** (`deployment.md §2.3`), with `gunicorn`
added because the §2.5 start command runs it. Test/lint tools go in a separate
`requirements-dev.txt` that is never deployed. A deploy must be reproducible so that the only
thing that changes what is installed is a scenario branch (e.g. `deployfail/01`).

**Decision 3 — `expected_culprit` in `branches.yaml`.** The old labels graded *whether*
Sentinel proposed a rollback, not *which* merge its revert PR targets. For case iii that is
the whole point. Each case ii/iii entry now names the culprit (its own merge, bound to
`pr-<N>-<sha>` at run time), so a revert PR is scored exactly against ground truth.

### 2026-08-30: LLM auth — federate the pod, do not ship an API key (deferred to backend phase 7)

**Decision: the backend pod authenticates to Anthropic and OpenAI by workload identity
federation, not by a stored API key. Deferred — the consumer does not exist yet.**

Both vendors support it, and this was checked against their docs rather than recalled:

- **Anthropic** — Workload Identity Federation, GA. Register a federation issuer (`fdis_`),
  a service account (`svac_`), and a federation rule (`fdrl_`); the workload posts its
  IdP-signed JWT to `POST /v1/oauth/token` (RFC 7523 `jwt-bearer`) and gets a short-lived
  `sk-ant-oat01-...`. Named providers include Kubernetes service accounts, Entra ID / AKS,
  and GitHub Actions.
- **OpenAI** — Workload Identity Federation, shipped 2026-05-26. Same shape over RFC 8693.
  Azure, Kubernetes, and GitHub Actions among the supported issuers.

**Why this fits without new plumbing.** The cluster already publishes an OIDC issuer and
projects service-account tokens into pods — `oidc_issuer_enabled` and
`workload_identity_enabled` (modules/aks/main.tf), the backend service account
(namespace.tf), the federated credential (deployment.tf). The token file the SDK wants is the
one already mounted. The subject is `system:serviceaccount:<namespace>:<sa>` — the same
string Entra matches for Key Vault access, so LLM access and Azure access come to rest on one
identity rather than two mechanisms.

**The trap, and it is specific to this platform.** The AKS OIDC issuer URL is per-cluster:
recreating the platform mints a new one. A hand-registered issuer therefore goes stale on
every rebuild — precisely the destroy -> recreate loop the phase-5/6 work exists to make
cheap. So **issuer and rule registration must run in the apply path via each vendor's admin
API**, not as a console step someone repeats from memory. Anthropic documents managing
issuers, service accounts, and rules as infrastructure-as-code for exactly this. GitHub
Actions' issuer (`https://token.actions.githubusercontent.com`) is stable and needs
registering once.

**What it does not achieve, stated plainly.** This is not zero secrets. It trades *one
long-lived runtime key per vendor, present in every pod* for *one admin key per vendor, used
at apply time and absent from the runtime path*. The gain is real — runtime credentials
become short-lived, per-workload attributable, and revocable at the issuer instead of by
hunting every place a key was copied — but the phrase "no secrets" would be false.
Federation is also only as strong as the IdP beneath it.

**Consequence for the vault.** Key Vault carries **five** secrets, not seven: Datadog
(api + app), Langfuse (public + secret), and the Teams webhook. Those vendors offer no
federation, so they stay static and stay rotated. The two LLM entries drop out. What replaces
them in the pod is five **non-secret identifiers** — `ANTHROPIC_FEDERATION_RULE_ID`,
`ANTHROPIC_ORGANIZATION_ID`, `ANTHROPIC_SERVICE_ACCOUNT_ID`, `ANTHROPIC_WORKSPACE_ID`,
`ANTHROPIC_IDENTITY_TOKEN_FILE` (and the OpenAI equivalents). Identifiers belong in Terraform
outputs and pod env, never in a vault; putting an ID in a vault teaches the next reader that
it is sensitive and that everything in the vault is equally sensitive.

**Failure mode to test for, not to trust.** `ANTHROPIC_API_KEY` outranks federation in the
SDK credential chain — a leftover key silently shadows WIF and the workload keeps working on
the static key while appearing federated. The phase-7 acceptance check must assert the
absence of the env var, not the success of a call. Same class of trap on the OpenAI side.

**Why deferred rather than built now.** Infra phase 6 has no pod to federate from. Building
the issuer-registration path against a consumer that does not exist would be guessing at its
service account name, its namespace, and its SDK. Phase 6 ships the vault and the seed step
as designed; the vault is designed so two entries can drop out without reshaping it.

Superseded: nothing. Extends *2026-07-04: OIDC workload identity federation — no stored
credentials*, which established the pattern for Azure and GitHub and left third-party APIs on
static keys because federation was not offered at the time. It now is.

### 2026-08-24: Phases 5-6 — from one static estate to a dynamic multi-deployment platform

Owner request: deploy and destroy complete, isolated deployments from workflow inputs alone.
That is not an extension of phases 1-4 — it reverses four of their load-bearing decisions. Each
is superseded below with its original reasoning preserved, because the reasoning was correct for
the model it was written against.

**The constraint that shaped everything: `workflow_dispatch` accepts at most 10 inputs.**
The stack needs ~40 knobs. A 40-field form is also unreviewable and leaves no record of what was
typed. So the design splits: **the form carries shape and intent** (which deployment, which
components, apply or destroy), **`azure/config/deployment-config.yaml` carries size and detail**
(SKUs, counts, retention), reviewed in git. A deployment absent from the file uses `defaults:`
entirely — so `deployment: demo1` + `apply` is a complete instruction with no file edit. The
file is for exceptions, not enrolment.

**One cluster, a namespace per deployment.** The subscription's regional quota is **6 vCPU** and
an AKS node is 2 — a cluster per deployment stops at three, with no headroom. A namespace per
deployment scales to whatever the cluster's RAM holds. The isolation is not weaker for being
logical: workload identity federates on `system:serviceaccount:<namespace>:<sa>`, Entra matches
that subject as an exact string with no wildcard form, so a pod in one namespace cannot mint a
token for another's Key Vault. Cryptographic separation, not a naming convention. A
`ResourceQuota` per namespace is mandatory rather than optional — it is what makes a shared
cluster acceptable rather than merely cheap.

**Two Terraform states, and this is a safety property not a preference.** The platform (ACR,
AKS, shared Postgres) and each deployment live in separate workspaces. In one state,
`terraform destroy` of a deployment would take the cluster with it. Separate states make that
structurally impossible. Deployments read the platform through a read-only
`terraform_remote_state` data source: they *need* the OIDC issuer and ACR login server, and must
be unable to change either.

---

**Superseded: R5 (2026-08-15) — CI rights scoped to `sentinel-rg`.**
You cannot create a resource group with rights scoped to a resource group, so dynamic
deployments force subscription scope. R5's *intent* survives; the mechanism changes. R5 chose
RBAC Administrator over Owner specifically because the credential is reachable from
`pull_request` workflows on a public repo — so the narrowness moves from **scope** to
**reachability**, via three identities:

| Identity | Rights | Subjects | PR-reachable |
|---|---|---|---|
| `gha-plan` | Reader + state blob | `:pull_request`, `:environment:plan` | yes — changes nothing |
| `gha-deploy` | Contributor + RBAC Admin + KV purge + AKS RBAC Cluster Admin | `:environment:production`, `:environment:destroy` | **no** |
| `gha-ops` | custom role: read + `*/start/action` + `*/stop/action` | `:environment:ops` | **no** |

A job declaring `environment: X` receives the subject `repo:<owner>/<repo>:environment:X`
instead of the branch form, and GitHub will not mint that for a `pull_request` event. So
`gha-deploy` is unreachable from a PR **by construction** — there is no rule to misconfigure.
This is exactly the behaviour that failed phase 4's first apply, now used deliberately.

`gha-ops` exists because pause/resume is the most frequently run operation and should not
require the identity that can delete the subscription. Contributor can delete; a start/stop role
cannot.

**Superseded: R6 (2026-08-16) — no CI destroy.**
R6 refused CI teardown because purging a soft-deleted Key Vault is a subscription-scope action.
That reasoning holds, but the conclusion inverts once destroy is a product feature: **purge is
required for destroy→recreate to work at all.** Without it, destroying `demo1` reserves its
vault name for 7 days and the next create fails on a vault nobody can see — which is precisely
the acceptance test this phase exists to pass. Destroy is therefore in CI, behind
`environment: destroy` (a distinct subject, so a required reviewer attaches to destruction
alone), `workflow_dispatch` only, and a typed confirmation matching the deployment name.

**Superseded: C1 — resource groups bootstrap-created and read-only.**
Read-only RGs meant every new deployment needed a manual bootstrap step, defeating the request.
RGs become managed resources; `destroy` deleting them is now the desired behaviour rather than
the hazard C1 guarded against. The **state** resource group stays out-of-band forever — state
cannot delete itself.

**Superseded: one cluster per estate (§3.7)** — see the 6-vCPU argument above.

**Naming replaced.** The `0375` suffix was collision-avoidance bolted on ad hoc and is not
derivable. Replaced by Azure CAF prefixes plus
`uid = substr(sha1("<subscription>-<deployment>-<env>"), 0, 4)` — deterministic, stable across
applies, never typed. `deployment` is capped at **8 characters**, and that cap is derived rather
than arbitrary: Key Vault allows 24, minus `kv-` minus `-<env>` minus `-<uid>` leaves 11, and 8
keeps headroom.

---

**The old estate is destroyed, not migrated (task 5.0).** Nothing is deployed into it — the
vault is empty by design, AKS runs no workloads, Postgres has no schema — so this is the
cheapest a rename will ever be, and running two naming schemes side by side would mean
maintaining both forever. `sentinel-tf-identity` and its federated credentials survive: they are
repo-scoped, not deployment-scoped.

**A plan cannot prove an apply will succeed**, so phase 6 adds a **preflight** job for the
things a plan structurally cannot see: both tenants minting tokens, global name availability,
soft-deleted vaults holding a name, AKS SKU availability *and* permission, regional vCPU quota,
provider registration, and Postgres being awake. Every one of those is a failure this project
has already hit.

**Pause is not zero cost, and the workflow says so.** `az aks stop` and
`az postgres flexible-server stop` end the compute charge, which dominates; OS disks, storage,
the AKS load balancer and the ACR daily charge continue. Two limits get stated in the summary
rather than discovered: **Postgres auto-restarts after 7 days** (Azure forces it — a pause is a
7-day lease), and AKS stop/start takes 5-10 minutes each way.

### 2026-08-24: Phase 4 — four pre-build decisions (infra CI)

Both reviewers halted phase 4 before a line was written: the specs and `infra.md` contradicted
each other, and each other's corrections, in ten places. Six were stale text with one correct
answer. These four were real, and the owner decided them.

**1. `quality_gate.py` does NOT run in infra CI. → Terraform-only workflows.**
The gate lives in `Sentinel/scripts/`; the workflows run in `Sentinel-infra`. The architecture
never said how it crosses. Three options were live: check out `Sentinel` as a second repo (all
three repos are **public**, so the default `GITHUB_TOKEN` suffices — no PAT, no B9), vendor a
copy, or drop it. **Chosen: drop it.** Infra CI runs `fmt -check` / `init` / `validate` /
`plan` / `apply` and nothing else.

⚠️ **Accepted cost, stated plainly: `tflint`, `shellcheck` and `gitleaks` never run on an infra
PR.** The gate becomes a pre-commit discipline enforced by the human, not by CI. A commit that
leaks a credential or ships a broken shell script *can* merge if the local run is skipped. This
is the one place in Sentinel where "green" is not machine-verified. Mitigating facts: infra has
no application code, the tflint findings so far have been dead-code hygiene rather than
correctness, and `terraform validate` + `plan` — the checks that actually catch a broken infra
change — do run. The owner chose the lower coupling over the coverage; recorded so the
trade-off stays visible rather than being discovered later as an oversight.

**2. Identity pointers are GitHub *variables*, not secrets.**
`§5.2/§5.3` pushed `AZURE_CLIENT_ID` / `AZURE_TENANT_ID` / `AZURE_SUBSCRIPTION_ID` as secrets;
`§5.4` and `§4.4` called them variables; `backend.md §9` read `${{ secrets.AZURE_* }}`. Under
OIDC **there is no secret** — a client id is a public identifier and the entire trust decision
is the federated-credential subject. Masking them costs real debuggability: a failed
`azure/login` prints `AADSTS700213 … subject ***` instead of the string that mismatched, which
is the only useful part of the message. **Chosen: variables.** `backend.md §9` is amended to
`vars.AZURE_*` — free now, since no backend workflow exists yet; it would not have been later.
`ACR_USERNAME` / `ACR_PASSWORD` stay **secrets** — those are real credentials.

**3. `ci_infra_dry.yml` splits by whether a job needs Azure.**
`§7.1` triggered on `push: ['**']`, but `§4.2` declares federated subjects only for
`ref:refs/heads/main` and `pull_request`. Every push to a `dev/*` branch would have died at
`azure/login` — including every branch of this build. Azure subjects are exact strings with no
wildcard, so covering `dev/*` would mean one credential per branch (limit 20) or preview
flexible FICs, *and* would hand Azure access to every dev branch. **Chosen: split the existing
`run-validate` / `run-plan` jobs by credential need.** `run-validate` (`fmt`,
`init -backend=false`, `validate`) touches no Azure and runs on every push; `run-plan`
authenticates and is gated to `pull_request` + `push main`, exactly the subjects that exist.
The job split `§7.1` already described now has a reason to exist.

**4. Task 4.1 also pushes the identity-tenant pointers.**
`§4.5` requires the backend repo to perform a *second* `azure/login` as `sentinel-gha-client`
(identity tenant, `allow-no-subscriptions`) to mint the backend-API token — but `§5` pushed
that identity nowhere, so it was unreachable from `Sentinel`. Distribution of cross-repo config
is precisely what 4.1 exists for; deferring it to backend 5.6 would mean a value hand-set in
the GitHub UI, untracked, which is the exact failure mode this task prevents. **Chosen: add
`AZURE_IDENTITY_TENANT_ID`, `AZURE_GHA_CLIENT_ID` and `SENTINEL_API_AUDIENCE` to the `Sentinel`
push.**

**`SENTINEL_API_AUDIENCE` value settled:** `api://<identity-tenant-id>/sentinel-backend`. The
bare `api://sentinel-backend` in `§5.4`/`§4.4` prose is unbuildable — new Entra tenants reject
it with `InvalidUniqueTenantIdentifierAsPerAppPolicy` (found live 2026-08-23). The live
`identity.tf` form is authoritative; the prose is corrected.

**Also corrected as stale, no decision needed:** task 4.1's `azuread_application.sentinel_gha`
(deleted by rev-9 — the CI identity is `azurerm_user_assigned_identity.sentinel_gha`); task
4.3's four-workflow body and `backend.md §9`'s workflow table (R6 removed `ci_destroy_infra`);
`§7.1`/`§7.2` missing the `identity_client_id` / `identity_use_oidc` vars `§9` makes mandatory;
`§8.1`'s claim that `ARM_*` "arrive from the workflow" when no workflow set them; task 4.4's
"wire every module" (all seven were wired in phases 2–3); `build-runners.yml` → `ci_runners.yml`.

### 2026-08-23: phase-3 build — four more constraints Azure taught us live

**1. Y1 and F1 Linux plans cannot share a resource group.** The F1 plan claimed
`sentinel-rg`'s Linux webspace; the Consumption plan was then rejected ("Dynamic SKU, Linux
Worker not available in resource group"). → **`sentinel-func-rg`**, same bootstrap-created
pattern as `sentinel-state-rg`, CI granted Contributor, added idempotently to
`bootstrap-oidc.sh`.

**2. AKS SKU took three attempts** (separate entry above): grant SKU fails the system-pool
RAM floor; B2s not in the allowed list; landed on ARM64 `B2pls_v2` → backend images must be
`linux/arm64`.

**3. New Entra tenants reject bare `api://name` identifier URIs**
(`InvalidUniqueTenantIdentifierAsPerAppPolicy`). The audience is now
**`api://<identity-tenant-id>/sentinel-backend`** — absorbed downstream because the audience
was already parameterized as `SENTINEL_API_AUDIENCE` (task 4.1) rather than hardcoded.
Backend 5.6 validates whatever that variable carries.

**4. Guest invitation ≠ guest access.** The B2B guest object existed in the portal, but CLI
token requests failed `AADSTS50020` until the invitation was **redeemed** by one interactive
`az login --tenant` as the invited account. An earlier scripted "token minted" check was a
false positive and is corrected here: the azuread provider's real request is the only proof.

Also: Event Grid batch defaults (`max_events_per_batch`, `preferred_batch_size_in_kilobytes`)
are server-populated — declare them or live with a perpetual diff (same class as Postgres
`authentication.tenant_id`). And the §3.7 `resource_group_name` deprecation fixed in phase 1
was accidentally reintroduced in the AKS module by copying the pre-fix snippet — caught by
the plan warning, removed; plans now run with **zero warnings**.

### 2026-08-23: AKS SKU — three attempts, landed on ARM (B2pls_v2)

Live applies rejected, in order: **B2ats_v2** (the free-grant SKU) — `SystemPoolSkuTooLow`,
system pools need ≥4 GB RAM and it has 1 GiB, so **the 750 h/mo grant is unusable for AKS,
full stop**; **B2s** (owner's chosen fallback) — not in the subscription's allowed AKS list
for canadacentral, where **every permitted small SKU is ARM64**. Landed on **`Standard_B2pls_v2`**
(ARM64, 2 vCPU/4 GiB, Bpsv2 quota 2-of-10, ~$0.03/hr — cheaper than B2s) without re-asking:
it preserves the essence of the owner's decision (small node + `az aks stop`/`start`), and the
only alternatives were pricier ARM SKUs.

Also established: a system pool cannot scale below 1 node, so the architecture's original
`nodepool scale 0↔1` mechanism was impossible regardless of SKU — §8.5's composite actions now
use `az aks stop`/`start`. Verified: `terraform plan` works against a **stopped** AKS cluster
(unlike stopped Postgres, which 400s).

**Downstream consequence, flagged in backend task 7.1:** the backend image must be built
`linux/arm64` or the pod fails with `exec format error`.

### 2026-08-23: phase-3 pre-build decisions — identity-tenant auth, expiry, and four arch defects

**1. Local access to the identity tenant = B2B guest invite.** The school account
(`arri@uwindsor.ca`) is invited as a guest into `eae0d3c6-…` and granted **Application
Administrator**, so one `az login` serves both tenants — the aliased `azuread` provider mints
identity-tenant tokens for the same signed-in user. CI authenticates as `sentinel-tf-identity`
(clientId `8f7ff635-…`) via the provider's own OIDC exchange. Rejected: a client secret on the
app (reintroduces the stored credential the design eliminates) and CI-only-behind-a-toggle
(defers 3.5's verification a whole phase).

**2. Secret expiry is a seed-time concern.** §3.8's `azurerm_key_vault_secret` snippet
(value from a var + `timeadd(timestamp(),…)`) is deleted as stale: it would put the value in
plaintext state AND force a new version every apply. §10 step 7 seeds with `--expires` (+90d);
the rotator re-stamps expiry on every version it writes, so the invariant self-maintains.
Terraform manages rotation *infrastructure* only.

**3. Arch defects fixed before building** (all found by warden distill): the bridge Function
had **no identity** while its `GITHUB_TOKEN` is a KV reference that resolves *silently empty*
without one → SystemAssigned + new `enable_bridge_reader` toggle on the keyvault module;
`azurerm_storage_account.func` was referenced but **never declared** → `sentinelfunc0375`;
`sentinel-events` → `sentinel-events-0375` (public DNS name, 0375 convention);
`source_arm_resource_id` → `source_resource_id` (**fourth** azurerm-v4 deprecation of this
class); F1 requires `always_on = false` + `use_32_bit_worker = true` or apply fails.

### 2026-08-16: R6 — full teardown is Owner-run and local, not a workflow

**Context:** Found by `code-reviewer` at the infra Phase 2 gate, and *reproduced* rather than
reasoned about. `modules/keyvault/main.tf` asserted that 7-day soft-delete + purge-allowed
"makes the designed teardown loop actually work". It does not, from CI.

A soft-deleted Key Vault lives at **subscription scope**
(`/subscriptions/{sub}/providers/Microsoft.KeyVault/locations/{loc}/deletedVaults/{name}`).
A live check of every grant `sentinel-gha` holds returned five assignments, **all** scoped to
`sentinel-rg`, `sentinel-state-rg`, or the state storage account — **none at subscription
scope**. So from CI: `terraform destroy` soft-deletes the vault → `az keyvault purge` returns
403, **silently swallowed by `|| true`** → the globally unique name is reserved for 7 days →
the next `terraform apply` fails, because the provider's `recover_soft_deleted_key_vaults`
default *also* reads deleted vaults at subscription scope. The justification for the
soft-delete decision (2026-08-15) was therefore falsified.

**Decision:** `ci_destroy_infra.yml` is **removed**. Full teardown becomes a documented
local procedure run as subscription Owner (§7.3). Infra ships **three** workflows, not four.

**Rejected:** subscription-scope `Key Vault Contributor` (lets CI create, modify and delete
**any** vault in the subscription — materially wider than the problem, for credentials
reachable from `pull_request`-triggered workflows on a public repo); and a custom purge-only
role at subscription scope (least-privilege and workable, but adds a bootstrap step and a
custom role to maintain, to automate the single most destructive operation in the project).

**Why this is arguably better than the thing it replaces:** "destroy everything, always" is
the most destructive operation Sentinel has. Requiring a human with Owner rights is a feature.
It also *removes* a standing privilege rather than adding one — the CI identity ends up with
strictly less power than the original design gave it.

**Consequence:** task 4.3 drops from four workflows to three. §7.3's runbook flags step 2
(`az keyvault purge`) as the one whose omission fails *later*, on the next apply, rather than
immediately.

### 2026-08-15: infra phase 2 — three cost/lifecycle decisions

**1. ACR Standard — free. (Reversed 2026-08-16; the original decision below was wrong.)**
The Azure for Students entitlement was read directly: `AzureForStudents_2018-01-01`, spending
limit **On**, and its 12-month free grant **does** cover the stack — *"Azure Database for
PostgreSQL: 750 hours of Flexible Server Burstable B1MS, 32 GB storage, 32 GB backup"* and
*"Container Registry: 1 **Standard** tier registry with 100 GB storage and 10 webhooks"*,
plus 750 h/month of **B2ats_v2** (the AKS node SKU), a free AKS control plane, and 750 h of
Standard Load Balancer.

So phase 2 costs **$0**, not ~$39/mo — and **Basic would have cost more than Standard**,
because the free grant is scoped to the Standard meter. Reverted to Standard in place (ACR
SKU changes are non-destructive). Spending limit On means the subscription pauses rather than
billing if credit is exhausted.

**The lesson, recorded because it will recur:** on a subsidised subscription, *cheaper SKU*
and *free SKU* are different questions, and optimising price without reading the entitlement
can cost money. The original reasoning follows, kept because the failure mode is instructive:

~~**1. ACR Basic, not Standard.**~~ §11 claimed Postgres B1MS and ACR Standard are free, citing
the **Azure free account** 12-month grant. This subscription is **Azure for Students**
(MS-AZR-0170P) — a different offer whose headline is "$100 credit + always-free services",
and Key Vault is on that always-free list while ACR and Postgres are not. If the grant does
not apply, phase 2 alone bills **~$39/mo** and the credit is gone in ~2.5 months, before
phase 3 adds AKS. ACR Standard (~$20/mo) is the one avoidable line: nothing in §3.1 or §6
needs 100 GB or 10 webhooks for two images. **Basic (~$5/mo)** — identical auth, AcrPull and
login server; SKU raises in place with no data loss. Deviation from §3.1, recorded here.
**Still to verify:** what the Students offer actually includes free — §11's AKS note says
"expires 05/2027", implying a free window *was* observed, so it may cover more than assumed.

**2. Globally-unique names take a `0375` suffix, systematically.** `sentinelacr`,
`sentinel-pg`, `sentinel-kv`, `sentineltfstate` and `dummy-api` were **all** already taken by
other tenants. Applied to every globally-scoped name including ones currently free —
availability is not reservation, and a collision found mid-phase costs a multi-file rename
(C12 cost 20 occurrences across 7 files). Each module takes its name as a validated variable,
so the next collision is a `tfvars` change rather than a code change.

**3. Key Vault: 7-day soft-delete, purge protection off.** Soft-delete is mandatory on Key
Vault; the Azure default (90 days + purge protection) would leave `sentinel-kv-0375`'s name
reserved after any teardown, making `ci_destroy_infra`'s "everything, always" rebuild
impossible under the same name. 7 days + purge allowed + an explicit `az keyvault purge` in
§7.3 makes the designed loop work. **Accepted cost:** a mistaken destroy can be purged for
real. Acceptable because all 9 secrets are re-seedable from their external sources — the
vault holds no generated state.

**Also corrected:** `enable_rbac_authorization` → `rbac_authorization_enabled`, deprecated in
azurerm v4 and removed in v5. Verified against the pinned 4.81.0 binary — same class as the
`parent_id` / `resource_group_name` deprecations found during infra 1.3.

### 2026-08-15: R5 — the CI identity could not create role assignments

**Context:** Surfaced by `code-reviewer` at the infra Phase 1 gate. `sentinel-gha` held exactly
`Contributor` on `sentinel-rg` + `Storage Blob Data Contributor` on the state account. The
built-in **Contributor** role's `notActions` include `Microsoft.Authorization/*/Write` and
`/Delete` — it cannot create or delete role assignments at all.

Phases 2-3 declare **six** Terraform-managed `azurerm_role_assignment` resources (Key Vault
Secrets Officer/User ×4, `AcrPull`, AKS Cluster User). The first `ci_infra.yml` apply touching
any of them would have failed with `AuthorizationFailed`, and `ci_destroy_infra` could not have
deleted them either. Separately, §7.3's `az group delete sentinel-state-rg` would have failed —
the identity had only *data-plane* rights there — silently, since §7.3 masks it with `|| true`.

**Why Phase 1 did not catch it:** every apply so far ran locally as subscription **Owner**. CI
has never once authenticated as this identity. A phase can be fully green and still not have
exercised the thing it built.

**Decision:** grant **Role Based Access Control Administrator** scoped to `sentinel-rg`, plus
**Contributor** on `sentinel-state-rg`.

Chosen over Owner and User Access Administrator because the built-in RBAC Administrator role
carries an ABAC condition forbidding the assignment of **Owner, User Access Administrator and
itself**. The identity can grant the roles the modules need but cannot escalate its own
privileges — which matters concretely: these credentials are reachable from
`pull_request`-triggered workflows on a public repo, so a wider grant would mean a leaked token
could self-promote.

**Accepted tension:** Contributor on `sentinel-state-rg` lets CI delete the very state that
protects it — the thing putting state in a separate resource group was meant to prevent. The
isolation that matters still holds (`terraform destroy` cannot delete the state describing the
run in progress); the "everything, always" teardown is a deliberate, separate, final step. Noted
in `infra.md` §4.2 rather than left implicit.

**Rejected:** moving all role assignments into the bootstrap scripts. It would have avoided the
grant entirely, but the RBAC graph would stop being version-controlled and drift silently — a
real regression for a project whose point is infrastructure-as-code.

### 2026-08-15: R4 resolved — two-tenant identity split (no institutional involvement)

**Context:** `api://sentinel-backend` + the `Incident.Write` app role require an
`azuread_application` — a directory object. `uwindsor.ca` denies app registration at tenant
policy (`allowedToCreateApps: false`, proven via Graph). The rev-9 managed-identity rebuild
rescued the CI identity and the Postgres admin but structurally **cannot** rescue this: a
managed identity can *hold* an app role, never *define* one. Requesting the
`Application Developer` role from UWindsor IT was ruled out by the owner — **no institutional
involvement**. That left the personal tenant or a shared-secret downgrade.

**Decision:** Two tenants, split by *kind of object* rather than by convenience.

| Tenant | Holds | Why | Cost |
|--------|-------|-----|------|
| School (`uwindsor.ca`) | every Azure resource; `sentinel-gha`, backend and rotator UAMIs | they hold RBAC on school resources and break if relocated | $100 credit |
| Identity (personal) | exactly 2 app registrations: `sentinel-backend-api`, `sentinel-gha-client` | only a tenant we own permits app registration | **$0** |

**Why this is not a security regression.** The client app carries a **federated credential**
trusting GitHub OIDC — the same trust source as the UAMI. GitHub mints one OIDC token per job
and exchanges it with each tenant independently; `azure/login@v2` supports
`allow-no-subscriptions`, so the identity tenant needs no subscription. rev-5's "no stored
Azure credential" invariant survives. An earlier note in this file wrongly assumed
client-credentials auth would be required; that was corrected before any code was written.

**A trap this decision creates.** The `sentinel-gha` UAMI **cannot** be granted the
`Incident.Write` role: app-role assignment is a within-tenant directory operation and has no
cross-tenant form. The caller must be its own registration in the identity tenant. Writing
`principal_object_id = azurerm_user_assigned_identity.sentinel_gha.principal_id` would fail
at apply with a misleading "principal not found".

**Accepted costs:** two tenants to reason about — every future auth bug now starts with
"which tenant?"; an aliased `azuread` provider (`provider = azuread.identity`) so the
boundary is explicit in every resource; a second one-time bootstrap seam
(`sentinel-tf-identity` + Application Administrator) mirroring §4.3; and one more admin
account to keep secure. `SENTINEL_API_TENANT_ID` is a required backend setting with **no
default**, since a wrong issuer is the most likely misconfiguration.

**Consequences:** `azuread ~> 3.0` returns to `required_providers` at infra task 3.5 (absent
in phases 1-2). New root variable `identity_tenant_id` + `AZURE_IDENTITY_TENANT_ID` GitHub
variable. Backend task 5.6 validates against the identity tenant's JWKS. Blocker **B11**
rewritten as "create the personal tenant", needed before infra Phase 3.

### 2026-08-15: rev-9 — identity plane rebuilt on managed identities (Option 3)

**Context:** The Azure subscription is **Azure for Students** (`174e25ca-…`) inside the
**University of Windsor** tenant (`uwindsor.ca`, `12f933b3-…`). Azure exposes two
independent permission planes: **Azure RBAC** on the subscription, and **Microsoft Entra**
on the directory. The owner holds **Owner on the subscription** and **no directory write rights** (own-user reads via `User.Read` do work — that is how `PG_ADMIN_OBJECT_ID` was obtained) —
confirmed by a portal 401. Every rev-5 identity construct (`sentinel-gha-oidc` app,
`sentinel-db-admins` group, `sentinel-backend-api` app) is a *directory* object, so B3, B10
and B11 were all unbuildable as designed. Options weighed: (1) ask UWindsor IT for
`Application Developer`; (2) abandon the student credit for a personally-owned tenant at
~$50–60/mo; (3) rebuild the identity plane on Azure-RBAC primitives; (4) self-hosted runner
on a VM with a system-assigned identity — rejected (24/7 cost, and self-hosted runners on a
public repo execute arbitrary PR code).

**Decision:** Option 3. The CI identity becomes a **User-Assigned Managed Identity**
(`azurerm_user_assigned_identity.sentinel_gha`) carrying five
`azurerm_federated_identity_credential` children. A UAMI is an ordinary Azure resource
governed by RBAC; its federated credentials are child resources, not directory objects, and
`azure/login@v2` cannot tell the difference. **B3 solved.** The `sentinel-db-admins` group is
deleted in favour of two direct `..._active_directory_administrator` resources — the human
owner (`principal_type = "User"`) and the backend UAMI (`ServicePrincipal`). **B10 solved.**

**Consequences / costs, stated plainly:**
- **B11 is not solved and cannot be** — only an app registration can *define* an API audience
  and app role. Raised as **R4**; `infra.md` §4.4 carries a ⛔ banner.
- Postgres admin membership is now a Terraform change instead of an Entra group edit. Worse
  day-2 operability, accepted in exchange for needing zero directory rights.
- `bootstrap-oidc.sh` must use `az role assignment create --assignee-object-id` +
  `--assignee-principal-type`; plain `--assignee` performs a Graph lookup that fails without
  directory read.
- Upside: managed-identity resources import by **derivable Azure resource ID**, not opaque
  directory object IDs — which is what makes the five-object import in §4.3.1 tractable.
- The `azuread` provider is no longer needed anywhere in infra Phases 1–2.

### 2026-08-15: Nine architecture conflicts resolved before first code (C1–C9)

Surfaced by `architecture-warden` (distill) against infra Phase 1; all would have produced
broken or unverifiable infra. Resolved as follows:

| # | Conflict | Resolution |
|---|----------|------------|
| C1 | §4.2 scoped Contributor to `azurerm_resource_group.sentinel` (managed) while §10 creates the RG by hand and §7.3 deletes it with `az group delete` | **Data source.** Terraform reads `sentinel-rg`, never owns it — otherwise `destroy` deletes it and the follow-up `az group delete` fails |
| C2 | Contributor scoped to `sentinel-rg`, but state lives in `sentinel-state-rg`, and `backend.tf` set no auth flags — **every CI `terraform init` would fail** | Bootstrap grants **Storage Blob Data Contributor** on `sentineltfstate0375`; backend gains `use_azuread_auth` + `use_oidc`; ARM_* env supplies the IDs |
| C3 | Bootstrap creates 5 objects; §4.3 documented importing 1, with the wrong ID form | All five imports documented in new §4.3.1, by Azure resource ID. Acceptance: `plan` shows no destroy **and no replace** |
| C4 | `subscription_id` declared but never consumed | Wired into `provider "azurerm"` — mandatory under v4 anyway, so C4 and C9 resolve together |
| C5 | CI passed 2 `-var` flags; `location` has no default and tfvars is gitignored → missing-variable failure every run | New `AZURE_LOCATION` GitHub *variable*, passed as `-var="location=…"`. `var.location` keeps **no default** (R3) |
| C6 | `GITHUB_PAT` — GitHub **rejects** the reserved `GITHUB_` prefix; the secret was uncreatable | Renamed **`GH_PAT`** everywhere |
| C7 | §9 classed `AZURE_*` as variables; every §7 workflow read them as `secrets.` | §9 is authoritative — they are `vars.`. Under OIDC these are identifiers, not credentials |
| C8 | §5.1 hardcoded `owner = "Keshav0375"`; task 1.1 required `var.github_owner` | Follow the task (variable, defaulted). Accepted deviation, not a violation |
| C9 | No `required_version`, no provider pins anywhere | `terraform >= 1.9`, `azurerm ~> 4.0`, `integrations/github ~> 6.0`. **No `azuread`** — rev-9 removed the need |

### 2026-07-12: Master ARCHITECTURE.md reshaped into a high-level Architecture Index
**Context:** The master doc had drifted into a fourth full architecture, duplicating detail
that lives in the per-repo files. Agents/skills need a fast whole-picture entry point that
routes to authoritative deep-dives, not a redundant long read.
**Decision:** Rewrote `architecture/README.md` as a lean, diagram-first **index**:
"How to navigate" table, the two system diagrams (three-repo + end-to-end), §3 one-paragraph
summaries per cross-cutting concern each with a `→ deep dive` pointer, and a §4 **concern →
authoritative file+§ map**. Deep detail stays in the per-repo files (authoritative). Added
bidirectional "↑ Deep dive of the Architecture Index" backlinks to all three per-repo arch
headers, framed the master as "start here" in the implementation tracker §4, and added a
doc-patterns rule (§2a) so the planner keeps the index lean going forward. Per-task **Arch
refs** and the `architecture-conformance` agent continue to target the per-repo sections.
**Impact:** Phase-2/ARCHITECTURE.md (rewritten); sentinel/ sentinel-deployment/ sentinel-infra/
ARCHITECTURE.md headers (backlinks); Phase-2-Implementation/README §4; sentinel-planner
doc-patterns.md §2a.

### 2026-07-12: Inbound backend auth — Entra bearer token (deletes sentinel-api-token)
**Context:** The backend API was protected by a shared static token `X-Sentinel-Token`
(`sentinel-api-token` in Key Vault, injected as env + copied to GHA). A static shared
secret is a standing leak risk and doesn't demonstrate real API-auth understanding.
**Decision:** Adopt Entra bearer auth. sentinel-infra registers the backend as an Entra
app (`api://sentinel-backend`) with an `Incident.Write` app role granted to the
`sentinel-gha` SP. Callers mint a token scoped to that audience
(`az account get-access-token --resource api://sentinel-backend`) and send
`Authorization: Bearer`. The backend adds a FastAPI dependency (`api/auth.py`,
`pyjwt[crypto]`) validating the JWT against Entra JWKS (iss/aud/exp/role) — no shared
secret. `/health` + `/ready` stay open for K8s probes. Tenant ID + audience are public
config (GitHub variables), not secrets. `sentinel-api-token` deleted from Key Vault +
GitHub. Documented the "one identity, many audience-scoped tokens" model to correct the
"single reusable token" misconception.
**Impact:** sentinel §3 (auth note), §3.1/§3.6 (new validation dep), §1.1, §8.2/§8.4,
§9.2/§9.3, §11 (pyjwt), §12, §13.3 (api/auth.py). sentinel-infra §4.4 (app reg) + §4.5
(token model). Master §4 (Authentication). sentinel-deployment (Bearer on backend calls).

### 2026-07-12: Dynamic secrets — Azure-native (Entra DB auth + Key Vault rotation), NOT HashiCorp Vault
**Context:** Goal was "zero secret leakage — everything dynamic." Clarified that a
"dynamic secret engine" is a **HashiCorp Vault** concept; Azure Key Vault only stores
static versions with rotation policies. Chose Azure-native over standing up Vault
(cost/ops fit for free tier + scale-to-zero AKS).
**Decision:** (a) **PostgreSQL → Entra-only auth** (`active_directory_auth_enabled=true`,
`password_auth_enabled=false`): clients present a short-lived Entra token (audience
`https://ossrdbms-aad.database.windows.net`, ~1 h user / ~24 h MI) as the psql password;
admin = `sentinel-db-admins` Entra group; DB roles map the SP + backend UAMI. `db-password`
deleted. (b) **LLM API keys → Key Vault rotation policy + rotator Function** (system topic
`SecretNearExpiry` → Function with Secrets Officer writes a new version; provider Admin API
where available, else Teams reminder). (c) **Backend → AKS workload identity** (OIDC issuer
+ UAMI + federated credential + annotated ServiceAccount) reads KV + gets DB tokens with no
pod secret. Honest limit: `GITHUB_PAT` + `ACR_*` remain as bootstrap secrets.
**Impact:** sentinel-infra §3.2 (Entra Postgres), §3.3 (KV roles + inventory), §3.7 (AKS
WI + backend UAMI), §3.8 (rotation Function), §5/§9/§10 (no db-password, PG_ADMIN_GROUP
var). sentinel §8.2 (no K8s Secret), §11 (azure-identity, azure-keyvault-secrets), §12.
sentinel-deployment §3 Stage 5 (Entra DB token). Master §4, §5.

### 2026-07-12: sentinel-deployment pivot — 30 scenario branches replace ci_demo_prs (ground truth + eval set)
**Context:** Demo PRs were template-based via `ci_demo_prs.yml`. The pivot makes the demo
app **real ground truth** and needs a stable, replayable, labelled scenario surface that
also serves as the eval dataset.
**Decision:** Remove `ci_demo_prs.yml` entirely. Ship **30 pre-authored scenario branches**
(10 per case): **(i)** clean pass — green deploy, healthy, no monitor (true negative);
**(ii)** deploy fails — pipeline red, previous version stays live, `deploy-failure` event
monitor → `signal_type=deploy_failure` → **backend Case 2 rollback**; **(iii)** green
deploy but runtime error — `runtime-health` monitor → `signal_type=runtime_error` →
**Case 3 full incident response**. Two Datadog signal types, two backend handling paths.
Ground-truth labels live in `scenarios/branches.yaml`; the branches replace the Phase-1
synthetic scenario JSON as the eval dataset. The Event Grid bridge stamps `signal_type`;
the orchestrator branches on it.
**Impact:** sentinel-deployment §1, §4 (rewritten: 30-branch/3-case), §4.1 (catalog), §5
(scenarios/, no ci_demo_prs), §6.3 (monitors→cases), §7. sentinel-infra §3.4/§3.5 (Event
Grid two-signal + bridge classify). sentinel §3.1 (signal_type payload + two-case table),
§3.4, §13.2 (eval runner = branches). Master §1/§2/§8/§10.

### 2026-07-12: ci_destroy_infra — full teardown workflow ("everything, always")
**Context:** No teardown path existed. Needed a one-shot "free everything from Azure" that
also supports destroy→re-create.
**Decision:** New manual `ci_destroy_infra.yml` (`workflow_dispatch`, typed `DESTROY`
confirm + `destroy` environment protection). **Scope = "everything, always"** (user choice):
two-stage — `terraform destroy` for all state-managed resources incl. the imported OIDC app
+ federated creds, then `az group delete` for `sentinel-rg` + `sentinel-state-rg` (the
manually-bootstrapped state storage TF can't reach). Auth acquired at job start (ARM token
valid ~1 h) so destroy completes after deleting its own identity. Accepted trade: restart
requires re-running the manual bootstrap (§4.3/§10) since OIDC + state are gone.
**Impact:** sentinel-infra §2 (workflow tree), §7 naming table + new §7.3 (full YAML).
sentinel §9 workflow table. Master §1 diagram + §8 workflows table. STATE.md blockers/tasks.

### 2026-07-11: GitHub owner/repo reconciliation — keshxvDev → Keshav0375, real repo casing
**Context:** The architecture docs were written against a placeholder GitHub owner `keshxvDev`
with lowercase repo names (`sentinel`, `sentinel-infra`, `sentinel-deployment`). The actual
cloned repos are `Keshav0375/Sentinel-infra`, `Keshav0375/Sentinel-deployment`, and
`Keshav0375/Sentinel` (capitalized). This matters for correctness, not just cosmetics: the
GitHub OIDC token `sub` claim carries the repo's canonical owner/name, and Azure matches
federated-credential subjects by exact, case-sensitive string — a lowercase or wrong-owner
subject silently fails auth.
**Decision:** Replace every `keshxvDev` reference with `Keshav0375` and correct repo casing
across the architecture docs: OIDC federated-credential subjects (§4.2) + the manual bootstrap
JSON (§4.3), the Function bridge `GITHUB_REPO` (§3.5), the `github` provider `owner` (§5.1),
the `github_actions_secret` `repository` args (§5.2/§5.3), and the cross-repo `uses:` action
references in all three arch docs + the incident-workflow YAML in sentinel §9.3. Added a
casing-sensitivity note to sentinel-infra §4.2. The historical decision-log entry (2026-07-05)
that shows `<owner>/sentinel/...` is left as-is (history); new work uses the concrete values.
**Impact:** sentinel-infra ARCHITECTURE §3.5, §4.2, §4.3, §5.1–5.3; sentinel ARCHITECTURE §9.3;
sentinel-deployment ARCHITECTURE §3.2; master §8. Implementation tracker R1/R2 resolved.

### 2026-07-05: Dynamic backend URL + reusable composite actions + repo buckets
**Context:** The static `SENTINEL_BACKEND_URL` variable forced the LB public IP to persist at scale-zero (~$3-4/mo) — and after the demo-PR correction, no consumer outside the two GHA workflows needs a stable URL. Separately, repeated step blocks (Key Vault reads, Teams posts, psql calls) were copy-pasted across jobs.
**Decision:** (1) **Dynamic URL:** `backend-up` resolves the LB ingress IP from the cluster and emits `backend-url` as an action/job output (non-secret → outputs are legal); `backend-down` deletes the Service, releasing the public IP → **infra is $0 at idle**. Fresh IP per cold run (+~1-3 min LB provisioning); same IP within a KEEP_WARM session. `SENTINEL_BACKEND_URL` variable removed. (2) **Reusable composite actions** in sentinel `.github/actions/`: `backend-up`, `backend-down`, `get-kv-secrets` (fetch + mask), `notify-teams`, `psql-exec`; local `dd-report` action in sentinel-deployment; cross-repo reuse via `uses: <owner>/sentinel/.github/actions/...@main`. Rule: any step block used twice becomes an action. (3) **Repo buckets** documented (sentinel §1.3): `src/sentinel/` (all reasoning, incl. providers/), `azure/` (k8s manifests — moved from `k8s/`), `.github/` (workflows + actions), `alembic/`, `tests/`, `Planning/`, `.claude/` — file system mirrors "backend reasons, GHA executes."
**Impact:** sentinel §1.1/§1.3 (new)/§8.1/§8.5/§9/§13/§14. Master, infra cost + KV flow, deployment §3.2/§3 Stage 5/§5. Total cost now ~$5-12/mo (LLM only), $0 infra at idle.

### 2026-07-05: Scale-to-zero backend — node pool 0↔1 per run (amends AKS always-on)
**Context:** Always-on consumes ~730 of the 750 free B2ats_v2 hrs/mo, leaving nothing for other projects. User chose per-run up/down over the recommended session toggle, accepting the cold-start cost. Key insight driving the design: the **node** is the meter, not the pod — scale-to-zero must target the node pool.
**Decision:** Node pool idles at 0. Shared composite actions `backend-up` (nodepool→1, replicas→1, wait /ready; ~3-7 min cold) and `backend-down` (both→0). `ci_incident_response.yml`: `ensure-backend-up` replaces the health gate (can't come up → Teams alert + loud fail); `teardown-backend` before summary. `ci_backend_deployment.yml`: scales up before deploy, down after. Safety rails: (1) both workflows serialized via `concurrency: group: sentinel-backend` so one run's teardown can't kill another's backend (GHA caveat documented: max 1 queued run per group); (2) `SENTINEL_KEEP_WARM=true` repo variable skips teardowns for live demo sessions; (3) new `ci_backend_scale.yml` — manual up/down + nightly auto-down cron; (4) Terraform `ignore_changes` on node_count so applies don't fight the workflows. LB IP persists at scale-zero → `BACKEND_URL` stays stable. Node consumption: ~20-80 hrs/mo; backend-computed MTTR excludes spin-up (measured from webhook receipt).
**Impact:** sentinel ARCHITECTURE §1, §8.4/§8.5 (new), §9.2/§9.3/§9.5, §14. sentinel-infra §3.7 (lifecycle block), §11. Master doc, READMEs synced.

### 2026-07-05: /generate/pr-content scope — rollback PR content ONLY; demo PRs are template-based
**Context:** Docs had sentinel-deployment's demo-PR workflow calling the backend for realistic PR titles/descriptions. User correction: demo PRs are manual/automated template-style with no agent involvement; the PR-content agent exists solely to write the revert PR during incident response.
**Decision:** `ci_demo_prs.yml` is self-contained — each scenario carries scripted file changes + a pre-written title/description; no backend call, no `SENTINEL_API_URL` variable, not in the concurrency group. `POST /generate/pr-content`'s only consumer is `ci_incident_response.yml`'s `generate-pr-content` job; its contract now takes incident context (root_cause, evidence_summary, confidence, target_deploy) and returns a `revert:`-prefixed title + Incident/Root Cause/Evidence/Rollback description written for the merge-or-close reviewer.
**Impact:** sentinel ARCHITECTURE §3.4 rewritten, §1.1/§8.4/§8.5 cleaned. sentinel-deployment §4/§3.4/§5/§8, README. Infra: sentinel-api-token consumer list.

### 2026-07-04: ci_incident_response health gate — validate the backend, never start it *(SUPERSEDED 2026-07-05: scale-to-zero — `ensure-backend-up` scales the backend up instead of gate-and-fail; the Teams-alert-on-failure behavior carries over)*
**Context:** With the backend always-on on AKS, the incident workflow must not manage its lifecycle — but it must also never process an incident against a dead backend, and never fail silently.
**Decision:** New `check-backend` gate job (Job 0): `curl /health` + `/ready`. Ready → proceed to parallel context fetch. Down → Teams alert ("incident alert received but backend is unreachable — NOT processed, manual action needed") and the workflow fails loudly. All fetch jobs `needs: check-backend`.
**Impact:** sentinel ARCHITECTURE §9.3 (job flow + YAML), §9.5, master §2/§8, sentinel README.

### 2026-07-04: Demo PR taxonomy — three conditions (A/B/C) + two Datadog monitors
**Context:** The 10-PR demo sequence only produced pipeline-detected failures (verify/deploy stage). It had zero scenarios where the deploy is green but the site breaks at runtime — the condition that exercises Sentinel's real diagnostic value.
**Decision:** Every demo PR is classified: **A** clean (green deploy, healthy app, no incident — baseline memory); **B** runtime failure (green deploy, app breaks under traffic → runtime-health monitor fires → revert PR heals the live site); **C** deploy failure (pipeline red, old version usually keeps serving → deploy-failure event monitor fires → revert PR heals main's deployability). Added PRs #11-14 (B scenarios: break `GET /` while `/health` stays green; delayed `/health` degradation past the verify window). Two Datadog monitors defined: `sentinel-deploy-failure` (event monitor on `deploy_status:failed`) and `sentinel-runtime-health` (5xx rate / failed health pings), both notifying the same webhook → Event Grid path; alert tags tell the agents which evidence class to weigh.
**Impact:** sentinel-deployment ARCHITECTURE §4 (taxonomy + 14-PR table), new §6.3 (monitors), README. Partially resolves the "monitor definition missing" review gap.

### 2026-07-04: Backend hosting — AKS single replica (supersedes 2026-07-02 ephemeral decision) *(AMENDED 2026-07-05: scale-to-zero — no longer always-on)*
**Context:** Architecture review found the ephemeral design unimplementable as specced: each GHA job runs on a fresh runner VM, so a container started in a `start-backend` job doesn't exist for `run-agent-pipeline`; GHA also refuses to pass masked secrets between jobs via outputs. The ephemeral pivot had additionally orphaned `/generate/pr-content` (sentinel-deployment's demo-PR workflow had no host to call) and removed the always-on API.
**Decision:** Backend runs as a single-replica Kubernetes Deployment on AKS — free control plane + 1× B2ats_v2 node (free 750 hrs/mo for 12 months, expires 05/2027). Public LoadBalancer IP (dev); all non-health endpoints require `X-Sentinel-Token` (new Key Vault secret `sentinel-api-token`). Secrets sync Key Vault → K8s Secret at deploy time. Kubelet gets AcrPull. K8s manifests (`k8s/deployment.yaml`, `k8s/service.yaml`) live in the sentinel repo, applied by CI — Terraform provisions the cluster only.
**Impact:** sentinel ARCHITECTURE §1, §8 (ephemeral lifecycle → AKS deployment), §9 (all three workflows redesigned), §14 (cost). sentinel-infra: AKS module restored (6→7 modules), secret flows rewritten. Master doc synced. Cost: still ~$0 infra for 12 months (+~$0-4 LB IP); ~$30/mo node after.

### 2026-07-04: HITL — fire-and-forget PR creation, no lifecycle tracking
**Context:** The old design said the backend "watches for the PR merge event" — impossible-adjacent and unnecessary; Phase 2 has no requirement for reviewer/merge-outcome data.
**Decision:** Sentinel's job ends when the revert PR exists and Teams is notified (or escalation is notified). No waiting states, no merge/close tracking. `revert_prs` table dropped (4→3 tables); `pr_number`/`pr_url` recorded on the `incidents` row by GHA right after PR creation (creation record only). Incident is terminal at pipeline completion; `mttr_seconds` = pipeline duration (alert → decision), not human review latency. The PR on GitHub remains the approval gate and audit trail.
**Impact:** sentinel ARCHITECTURE §3.3, §5 (schema), §9.3. Master §5, §7. READMEs synced.

### 2026-07-04: deployments table writer — ci_app_deployment.yml records every deploy
**Context:** Review found the `deployments` table had no writer — `get_deploy_details` and deploy↔incident correlation would query an empty table.
**Decision:** New Stage 5 "Record Deployment" in ci_app_deployment.yml, `if: always()`: OIDC login → read `db-password` from Key Vault → psql INSERT (service, pr_number, commit_sha, author, deploy_status, gha_run_id, files_changed, metadata incl. failed_stage). Failed deploys recorded too — they're the rows incidents join against. `incident_id` backfilled by the backend on correlation. No DB credentials in GitHub secrets.
**Impact:** sentinel-deployment ARCHITECTURE §3 (stages renumbered), §3.3, §3.4. PostgreSQL firewall rationale updated (GHA runners write to DB).

### 2026-07-04: Renamed ci_backend_validation.yml → ci_backend_deployment.yml
**Context:** With AKS hosting the post-merge workflow's job is deployment, not just validation.
**Decision:** `ci_backend_deployment.yml`: quality → build+push (immutable sha tag, no `latest`) → deploy-to-aks (secret sync, `kubectl set image`, rollout status) → tests against the live deployment (incl. smoke test) → promote `stable` tag on green / `kubectl rollout undo` + Teams alert on red. Nothing pulls `latest` at runtime — AKS pins the sha tag, so a half-validated image can't serve an incident.
**Impact:** sentinel ARCHITECTURE §9.2, workflow tables everywhere, sentinel-infra §3.1 image table, READMEs.

### 2026-07-04: Added ci_validation.yml — fast PR gate, split from ci_backend_validation
**Context:** `ci_backend_validation.yml` runs the full pipeline including ACR push, ACR cleanup, and smoke tests. This is heavy for every PR open/sync (~8-12 min). Developers need fast feedback on PRs.
**Decision:** New `ci_validation.yml` runs on PR open/sync: lint (ruff) → typecheck (pyright) → Docker build (local, no push) → run backend from local image → validate /health + /ready → unit tests → integration tests → teardown. No ACR interaction, no smoke test. `ci_backend_validation.yml` moves to `push` trigger (runs on merge to main only) and remains the authoritative validation that pushes to ACR and runs the smoke test.
**Impact:** 7 total workflows across repos (was 6). PR feedback: ~3-5 min. Post-merge full validation: ~8-12 min. Two-stage pipeline: fast gate on PR, full validation on merge.

### 2026-07-04: Merged ci_backend + cd_backend → ci_backend_validation
**Context:** Had two separate workflows: `ci_backend.yml` (quality gate on PR) and `cd_backend.yml` (build+push on merge). But tests should run against the real Docker image, not a local install. And pushing should happen as part of validation, not as a separate post-merge step.
**Decision:** Single `ci_backend_validation.yml` on every PR: lint → typecheck → build + push image to ACR → run backend from the real image → validate /health + /ready → run unit tests → run integration tests → smoke test → teardown. ACR cleanup keeps only the 3 most recent image tags. No separate CD workflow needed.
**Impact:** `cd_backend.yml` removed. Tests now validate the exact artifact that `ci_incident_response.yml` pulls during incidents.

### 2026-07-04: Workflow naming convention — standardized across all repos
**Context:** Workflow file names and display names were inconsistent across sentinel, sentinel-infra, and sentinel-deployment (e.g., `deploy.yml`, `plan.yml`, `incident_response.yml`).
**Decision:** Standard `ci_` prefix convention. Workflow `name:` follows `[repo] scope — description`. Job IDs: `kebab-case` verb-noun. Applied across all three repos.
**Impact:** All workflows: `ci_validation.yml` (fast PR gate), `ci_backend_validation.yml` (full post-merge validation), `ci_incident_response.yml` (real pipeline), `ci_app_deployment.yml` (sentinel-deployment), `ci_infra_dry.yml` (TF validate+plan), `ci_infra.yml` (TF apply), `ci_runners.yml` (runner images).

### 2026-07-04: OIDC workload identity federation — no stored Azure secrets
**Context:** Original plan stored `AZURE_CLIENT_SECRET` as GitHub repo secret. Secrets expire, must be rotated.
**Decision:** OIDC federation — GitHub proves identity via JWT, Azure trusts it. One Azure AD app with federated credentials for all three repos (sentinel-infra main+PR, sentinel main+PR, sentinel-deployment main). Terraform provisions the federated credentials. Only 3 non-secret values needed per repo: CLIENT_ID, TENANT_ID, SUBSCRIPTION_ID.
**Impact:** Added OIDC section (§4) to sentinel-infra ARCHITECTURE.md with full HCL and bootstrap sequence. Removed AZURE_CLIENT_SECRET from all repos.

### 2026-07-04: Cross-repo secret distribution — Terraform pushes GitHub secrets
**Context:** After `terraform apply`, sentinel and sentinel-deployment repos need ACR creds and OIDC IDs as GitHub secrets. Previously manual copy-paste.
**Decision:** Terraform uses `github_actions_secret` resource (GitHub provider) to automatically push ACR_LOGIN_SERVER, ACR_USERNAME, ACR_PASSWORD, AZURE_CLIENT_ID, AZURE_TENANT_ID, AZURE_SUBSCRIPTION_ID to sentinel repo, and OIDC IDs to sentinel-deployment repo. Requires GITHUB_PAT with `repo` scope as sentinel-infra secret.
**Impact:** Added §5 to sentinel-infra ARCHITECTURE.md. GITHUB_PAT added to sentinel-infra repo secrets table.

### 2026-07-04: Key Vault dual access — Terraform writes, GHA reads
**Context:** Key Vault had one access policy (Terraform SP). But incident_response.yml needs to read secrets at runtime.
**Decision:** Two roles: Terraform SP gets `Key Vault Secrets Officer` (create/update secrets). GHA OIDC SP gets `Key Vault Secrets User` (read-only). Switched from access policies to RBAC authorization (`enable_rbac_authorization = true` — **the argument was renamed to `rbac_authorization_enabled` in azurerm v4; see the 2026-08-15 phase-2 entry. The decision stands, only the spelling changed**).
**Impact:** Updated keyvault module (§3.3) with dual role assignments. Added full secret flow diagram showing Key Vault → GHA → Docker env vars.

### 2026-07-04: PostgreSQL firewall — allow all for dev
**Context:** PostgreSQL firewall only allowed Azure services (`0.0.0.0/0.0.0.0`). But ephemeral backend runs on GitHub-hosted runners (not Azure services). GitHub runner IPs rotate across a wide, unpredictable CIDR range.
**Decision:** Allow all (`0.0.0.0` to `255.255.255.255`) for dev. DB still protected by username + password. Production would use Private Endpoint + VNet.
**Impact:** Updated postgresql module (§3.2) with explicit rationale and comparison table of alternatives.

### 2026-07-02: Ephemeral backend — run inside GHA, not AKS *(SUPERSEDED 2026-07-04: AKS single replica — multi-job GHA design was unimplementable)*
**Context:** Backend was planned for 24/7 AKS hosting. But the pipeline runs a few times per day during demos. Paying for always-on compute for a 5-minute job is waste.
**Decision:** Backend runs as an ephemeral Docker container inside the GHA runner. Per-incident lifecycle: fetch secrets → pull image from ACR → docker run → validate /health + /ready → run pipeline → teardown. Zero compute cost (uses GHA free minutes). PostgreSQL stays always-on (free tier). AKS module removed from Terraform.
**Impact:** Rewrote architecture/backend.md §1 (system overview), §8 (K8s manifests → ephemeral lifecycle), §9 (workflows), §10 (Terraform: 7→6 modules), §14 (cost breakdown). No K8s manifests needed. cd_backend.yml simplified to build+push only.

### 2026-07-02: LLM providers — Anthropic + OpenAI only, no Groq/Gemini
**Context:** Original plan used Groq free tier (llama models). But this is a portfolio project — decision-making quality matters more than cost.
**Decision:** Anthropic (default) + OpenAI (fallback). Top models: Sonnet 4.6 for reasoning tasks, Haiku 4.5 for classification. Fallback: gpt-4o / gpt-4o-mini. Switch via `SENTINEL_PRIMARY_PROVIDER` env flag. Both API keys always required. Cost: ~$5-12/month for LLM calls.
**Impact:** Updated architecture/backend.md §4.7 (model table), §12 (prerequisites), §14 (cost). Groq and Gemini references removed.

### 2026-07-01: HITL gate = GitHub PR review, not custom API
**Context:** Original design had a `POST /approvals/{incident_id}` endpoint. But the destructive action IS a revert PR — GitHub already has review/approve/merge.
**Decision:** No `/approvals` endpoint. The revert PR on sentinel-deployment IS the HITL surface. Backend decides rollback vs escalate, GHA creates the PR, reviewer merges or closes. `approvals` table renamed to `revert_prs` — tracks PR lifecycle (created, merged, closed).
**Impact:** Removed `/approvals` endpoint from API contracts. Updated pipeline flow, DB schema, tool table. Cleaner separation: backend reasons, GHA executes.

### 2026-07-01: Backend reasons, GHA executes — separation of concerns
**Context:** Who creates the PR? Who sends the Teams notification? Originally the backend did everything.
**Decision:** Backend returns a detailed response with `resolution_type` (rollback/escalated) + full context. GHA jobs branch on that: rollback path → generate-pr-content job → create-rollback-pr job → notify-rollback job. Escalation path → notify-escalation job. Both → summary job. `draft_rollback_pr` tool removed from backend, replaced by `prepare_rollback_spec` (outputs target SHA + justification, doesn't call GitHub API).
**Impact:** Updated incident_response.yml with full job DAG. Updated tool table. Notifications moved entirely to GHA.

### 2026-07-01: PR content generation endpoint — specialized agent for demo PRs *(SCOPE CHANGED 2026-07-05: rollback PR content only — demo PRs are template-based)*
**Context:** sentinel-deployment creates demo PRs that intentionally break things. PR titles and descriptions need to look realistic — a template can't produce convincing developer-style justifications for changes that are secretly broken.
**Decision:** New `POST /generate/pr-content` endpoint on sentinel backend. Takes scenario context (files changed, diff summary, failure class) and returns LLM-generated PR title + description. Uses Haiku 4.5 (constrained generation, not reasoning). sentinel-deployment GHA calls this in a `generate-pr-content` job, passes output to a `create-pr` job.
**Impact:** Updated architecture/backend.md §3.4 (new API contract), §4.7 (model table), §13.3 (new files). New files: `agents/pr_content_generator.py`, `agents/prompts/pr_content_generator.txt`, `api/generate.py`.

### 2026-07-01: Phase 1 → Phase 2 cleanup plan — data/, generator/, SQLite removal
**Context:** Phase 1 `data/` directory (10 synthetic scenarios, seed JSON, seed.py, sentinel.db) and `src/sentinel/generator/` (alert_gen, log_gen, deploy_gen, scenarios) exist only to fake data. Phase 2 gets real data from Datadog, GitHub, PostgreSQL.
**Decision:** Full cleanup section added to architecture (§13). Delete: `data/`, `generator/`, `db.py`, `scripts/run_scenario.py`, `scripts/run_eval.py`, `scripts/demo.py`. Rewrite: all 6 tools, memory layer, orchestrator, eval. New: `alembic/` for migrations, `database.py` for asyncpg pool. Migration order: add deps → create new modules → rewrite tools → rewrite orchestrator → delete Phase 1 artifacts (late, to keep Phase 1 working until Phase 2 is proven).
**Impact:** Updated architecture/backend.md §1 (diagram), §7 (Dockerfile), added §13 (cleanup plan).

### 2026-07-01: LLM model selection — differentiated per agent role
**Context:** All agents were using the same model. Classification tasks (triage, judge, reflexion, reverification) don't need the same reasoning power.
**Decision:** Haiku 4.5 for classification/scoring tasks. Sonnet 4.6 for reasoning tasks (analysis, resolution, orchestrator). Fallback: OpenAI gpt-4o / gpt-4o-mini. *(Superseded by 2026-07-02 provider decision — Groq/Gemini removed.)*
**Impact:** Better model-task fit. Updated architecture/backend.md §4.7.

### 2026-07-01: Agentic loop patterns — reflexion + plan-execute + reverification
**Context:** Linear chain (triage → analysis → resolution → judge) doesn't self-correct. If analysis is wrong, the whole pipeline proceeds on a bad hypothesis.
**Decision:** Three patterns integrated: (1) Plan-execute — orchestrator plans before dispatching. (2) Reflexion — self-critique after analysis, loops back if confidence < 0.7, max 2 loops. (3) Reverification — post-resolution check that the fix matches the root cause.
**Impact:** Pipeline can now self-correct. Tool-call budget raised from 15 to 20 to accommodate loops. Updated architecture/backend.md §4.2-4.4.

### 2026-07-01: GHA incident_response.yml — parallel data gathering + confidence-gated execution
**Context:** Original design had GHA just doing `curl POST /webhooks/incident`. Missed opportunity to pre-fetch data in parallel.
**Decision:** New 6-stage workflow: (1) fetch secrets from Key Vault, (2) parallel jobs: service metadata, PR details, Datadog logs, (3) trigger backend with enriched payload, (4) poll for completion + confidence check, (5a) escalate if low confidence, (5b) execute if high confidence, (6) always notify Teams + report to Datadog.
**Impact:** Agent pipeline starts with pre-fetched context — faster resolution. GHA does the fan-out/fan-in, backend does the reasoning. Updated architecture/backend.md §9.4.

### 2026-07-01: Concurrent incident handling — asyncio task isolation
**Context:** What if two incidents fire simultaneously?
**Decision:** Each pipeline run = independent `asyncio.Task` with its own ShortTermMemory dict and LangFuse trace. No locking needed — incidents are independent. asyncpg pool (min=2, max=10) handles concurrent DB access. Ephemeral container handles 2-3 concurrent runs within a single incident workflow.
**Impact:** Updated architecture/backend.md §4.5.

### 2026-07-01: Incident ID correlation — deployments table + correlation map
**Context:** No way to trace from incident → exact PR → exact deploy → exact Datadog logs.
**Decision:** (1) New `deployments` table linking service, PR number, commit SHA, GHA run ID, Datadog event ID, and incident ID. (2) `correlation_id` generated at Event Grid bridge, carried through GHA → backend → all agents. (3) Every incident links to alert_id, dd_event_id, correlation_id, deploy_id, and langfuse_trace_id.
**Impact:** Full traceability. Given any incident, trace back to exact PR, deploy, logs, and LLM trace. Updated architecture/backend.md §2.1, §5.3.

### 2026-07-01: PostgreSQL usage — 4 tables with clear purposes
**Context:** Schema had 3 tables. Missing deploy tracking.
**Decision:** 4 tables: incidents (episodic memory), services (semantic memory), approvals (HITL audit), deployments (deploy ↔ incident correlation). Added columns: dd_event_id, correlation_id, root_cause_confidence, resolution_type, reflexion_loops, mttr_seconds, langfuse_trace_id.
**Impact:** Updated architecture/backend.md §5.2-5.4.

### 2026-07-01: LangFuse — full integration (not just tracing)
**Context:** Original plan used LangFuse only for LLM call logging.
**Decision:** Full integration: (1) Tracing — every pipeline run as a trace with spans. (2) Prompt management — load system prompts from LangFuse with local fallback. (3) Scoring — judge scores piped to LangFuse for dashboard. (4) Cost tracking — token usage per agent. (5) Datasets — export trajectories for regression testing.
**Impact:** Added new section architecture/backend.md §6. Prompt loading pattern changes from file-only to LangFuse-first.

### 2026-07-01: Terraform justification — documented
**Context:** Why Terraform over Bicep, CLI scripts, or manual?
**Decision:** Terraform wins on: reproducibility, state tracking, provider-agnostic (interview value), PR-reviewable infra. Provisioning 7 modules covering all Azure resources.
**Impact:** Added architecture/backend.md §10.

### 2026-07-01: sentinel architecture marked final
**Context:** All 9 deep design questions resolved.
**Decision:** Architecture doc updated to final status. All sections complete.

### 2026-07-01: Ingress — AKS public IP for dev
**Context:** Need external access to backend for webhooks.
**Decision:** Use AKS-assigned public IP for dev. No custom domain needed yet. Can add later.

### 2026-07-01: GHA orchestration — thin HTTP call to backend
**Context:** repository_dispatch workflow needs to trigger the agent pipeline.
**Decision:** Superseded by incident_response.yml design (see above). Now a full multi-job workflow, not just a curl.

### 2026-07-01: Infra bootstrap — manual one-time setup
**Context:** Terraform state storage must exist before first `terraform apply`.
**Decision:** Manually create state resource group + storage account + container. Documented in sentinel-infra ARCHITECTURE.md §5.1. Not a recurring concern.

### 2026-07-01: sentinel = backend (no separate repo)
**Context:** Originally planned sentinel-backend as a separate repo. Realized the sentinel repo already contains all backend code in `src/sentinel/`.
**Decision:** sentinel repo is the backend. All agent code, CI/CD workflows, and deployment configs live here. No separate backend repo.
**Impact:** Removed `architecture/sentinel-backend/` folder. Merged backend architecture into `architecture/backend.md`. Simplified from 4 planning folders to 3.

### 2026-07-01: Backend hosting — AKS with B2ats free node *(SUPERSEDED 2026-07-02: ephemeral backend)*
**Context:** Needed always-on hosting for webhook-driven agent API. App Service F1 sleeps and has 60 min CPU/day limit.
**Decision:** ~~AKS~~ → Superseded by ephemeral Docker container inside GHA runner. See 2026-07-02 entry.
**Impact:** AKS module removed from Terraform. K8s manifests removed. cd_backend.yml simplified to build+push only.

### 2026-07-01: Database — PostgreSQL B1MS + pgvector
**Context:** Phase 1 uses SQLite. Need vector similarity for episodic memory search.
**Decision:** Azure PostgreSQL B1MS (free 12 months, 32 GB) with pgvector extension. Driver: asyncpg. Migrations: alembic.
**Impact:** Schema defined in architecture/backend.md. sentinel-infra PostgreSQL module spec'd.

### 2026-07-01: CI/CD — Four workflows for sentinel
**Context:** Need quality gates, auto-deploy, and real incident pipeline.
**Decision:** Four workflows: (1) ci_backend.yml — lint, typecheck, unit + integration tests with pgvector, Docker build verify on PR. (2) cd_backend.yml — build, push to ACR (no deploy — pulled on demand). (3) ci_incident.yml — agent pipeline smoke test on PR. (4) incident_response.yml — full lifecycle with ephemeral backend.
**Impact:** Workflow structure defined in architecture/backend.md §9.

### 2026-07-01: CI runner images in ACR
**Context:** Installing ruff, pyright, pytest, az cli, kubectl every CI run is slow.
**Decision:** Build custom ci-runner Docker image with all tools pre-installed, store in ACR, use as `container:` in GHA workflows.
**Impact:** sentinel-infra manages runner image builds. ci-images/ directory with Dockerfiles.

### 2026-07-01: sentinel-infra — per-resource Terraform modules
**Context:** Needed to decide how to structure Terraform code.
**Decision:** One module per Azure resource concern (acr/, postgresql/, keyvault/, event-grid/, functions/, app-service/). Root main.tf wires them together. *(AKS module removed 2026-07-02.)*
**Impact:** architecture/infra.md written with full module breakdown and HCL.

### 2026-07-01: sentinel-deployment — zip deploy, not Docker
**Context:** Azure App Service F1 does not support container deploys.
**Decision:** Zip deploy via `az webapp deploy`. Pipeline simplifies to 3 stages. No Dockerfile needed.
**Impact:** sentinel-deployment ARCHITECTURE.md rewritten. Cost: $0/month.

### 2026-07-01: sentinel-deployment architecture finalized
**Context:** All decisions resolved for sentinel-deployment.
**Decision:** Architecture doc marked final.
**Impact:** Unblocks sentinel-infra App Service module.

### 2026-06-30: Deploy target — Azure App Service F1 (not DigitalOcean)
**Context:** DigitalOcean requires payment method.
**Decision:** Azure F1 always-free tier.
**Impact:** All DO references removed.

### 2026-06-30: Datadog integration — dual path
**Context:** How deployment data reaches Datadog.
**Decision:** Native Azure integration (auto metrics) + GHA pipeline curl (custom events/logs).

### 2026-06-30: App design — pipeline as product
**Context:** Pivoted from complex job queue to deployment pipeline as the interesting part.
**Decision:** Trivial app, GHA deploy pipeline generates all Datadog signal.

### 2026-06-30: Three-repo architecture
**Decision:** sentinel (backend + orchestration), sentinel-deployment (dummy app), sentinel-infra (Terraform).

### 2026-06-30: Notification channel — Microsoft Teams

### 2026-06-30: LLM providers — Groq primary, Gemini backup *(SUPERSEDED 2026-07-02: Anthropic + OpenAI)*

### 2026-06-30: CI pipeline — 4 workflows total (updated from original 4-linear-jobs plan)
