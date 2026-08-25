# sentinel-infra — Architecture Document

> # ⚠️ Phase 5 replaced the model this document describes
>
> **Read [decisions.md](decisions.md) → "2026-08-24: Phases 5-6" before trusting any section
> below.** Phase 5 (built 2026-08-25) replaced the single static estate with a two-layer dynamic
> platform. Sections are marked individually, but the shape of the change is:
>
> | Was | Is |
> |---|---|
> | one estate, `sentinel-*-0375` names | **`modules/naming`** — CAF prefixes + a derived `uid`; deployment names cap at 8 chars |
> | one `sentinel-gha` identity scoped to one RG | **three identities** — `gha-plan` / `gha-deploy` / `gha-ops`, subscription-scoped, separated by *reachability* not scope |
> | resource groups bootstrap-created, read-only (C1) | **managed**, except `rg-sentinel-bootstrap` which holds what Terraform can never own |
> | one cluster per estate (§3.7) | **one cluster, a namespace per deployment** — forced by a 6-vCPU regional quota |
> | one state file | **workspaces** — `platform` plus one per deployment; a deployment's state contains no platform resource, so destroying it *cannot* touch the cluster |
> | teardown is Owner-run and local (R6) | **CI destroys**, behind `environment: destroy` |
> | ~20 root variables | **10**, plus `azure/config/deployment-config.yaml` — `workflow_dispatch` caps at 10 inputs |
> | push to main applies | **apply is dispatch-only** — a push cannot know which deployment it means |
>
> **What still binds** — these are properties of Azure, not of the old model, and phase 5
> carries every one of them forward: the ARM64 AKS SKU and why the alternatives fail (§3.7),
> Entra-only Postgres with no password anywhere (§3.2), Key Vault RBAC mode and soft-delete
> (§3.3), ACR **Standard** because the free grant covers Standard and Basic is a different
> billable meter (§3.1), and the Y1/F1 Linux webspace conflict that forces a separate functions
> resource group (§10).
>
> The operational runbook is **`Sentinel-infra/docs/BOOTSTRAP.md`**, rewritten for the new model
> and the only teardown procedure that is current.


> **↑ Deep dive of the [Architecture Index](README.md).** Start there for the whole
> picture; this file is the authoritative detail for **infra + identity** concerns (index §4 map).

> **Purpose:** Terraform IaC that provisions all Azure resources Sentinel depends on.
> Single `terraform apply` brings up the entire stack. Also manages CI runner
> images in ACR and cross-repo secret distribution.
>
> **Note:** Includes AKS — the sentinel backend runs as a single-replica Deployment
> on a 1-node AKS cluster (free control plane + 1× B2pls_v2 ARM64 node, stopped when idle).
> Terraform provisions the cluster; the sentinel repo's `ci_backend_deployment.yml`
> deploys the app onto it.

---

## 1. System Overview

```
sentinel-infra repo
       │
       │  terraform apply (OIDC — no stored secrets)
       ▼
┌──────────────────────────────────────────────────────────────────┐
│                        Azure (sentinel-rg)                       │
│                                                                   │
│  ┌─────────────────────────┐    ┌──────────────────────────────┐ │
│  │  Azure Container        │    │  Key Vault                    │ │
│  │  Registry (ACR)         │    │  (always free)                │ │
│  │  (free 12 months)       │    │                               │ │
│  │                         │    │  Secrets:                     │ │
│  │  Images:                │    │  ├── anthropic-api-key  ↻     │ │
│  │  ├── sentinel-backend   │    │  ├── openai-api-key     ↻     │ │
│  │  └── ci-runner          │    │  ├── dd-app-key   (no db-pwd) │ │
│  └─────────────────────────┘    │  ├── dd-api-key               │ │
│                                  │  ├── teams-webhook-url        │ │
│  ┌─────────────────────────┐    │  ├── langfuse-secret-key      │ │
│  │  PostgreSQL B1MS        │    │  ├── langfuse-public-key      │ │
│  │  (free 12 months)       │    │  ├── acr-password              │ │
│  │                         │    │  ├── github-pat                │ │
│  │  DB: sentinel (Entra)   │    │  (↻ = rotated; no api-token)  │ │
│  │  Extension: pgvector    │    └──────────────────────────────┘ │
│  │  32 GB storage          │    ┌──────────────────────────────┐ │
│  │  Firewall: allow all    │    │  OIDC Federation              │ │
│  │  (dev — see §3.2)       │    │  (Azure AD App Registration) │ │
│  └─────────────────────────┘    │                               │ │
│                                  │  Trusts:                      │ │
│  ┌─────────────────────────┐    │  ├── sentinel-infra (plan/    │ │
│  │  Event Grid Topic       │    │  │   apply workflows)         │ │
│  │  (always free)          │    │  ├── sentinel (ci/cd/         │ │
│  │  100K ops/month         │    │  │   incident workflows)      │ │
│  └─────────┬───────────────┘    │  └── sentinel-deployment      │ │
│            │                     │      (deploy workflows)       │ │
│            ▼                     └──────────────────────────────┘ │
│  ┌─────────────────────────┐                                      │
│  │  Azure Function         │                                      │
│  │  (always free)          │                                      │
│  │  1M reqs/month          │                                      │
│  │                         │                                      │
│  │  Event Grid →           │                                      │
│  │  repository_dispatch    │                                      │
│  └─────────────────────────┘                                      │
│                                                                   │
│  ┌─────────────────────────┐                                      │
│  │  App Service (F1)       │                                      │
│  │  (always free)          │                                      │
│  │  dummy-api-0375              │    ← sentinel-deployment target      │
│  └─────────────────────────┘                                      │
│                                                                   │
│  ┌─────────────────────────┐                                      │
│  │  AKS (sentinel-aks)     │                                      │
│  │  control plane: free    │    ← sentinel-backend runs here      │
│  │  1× B2pls_v2 node (stop/start)│      (single replica, public LB IP,  │
│  │  (free 12 months)       │       deployed by sentinel repo CI)  │
│  └─────────────────────────┘                                      │
└──────────────────────────────────────────────────────────────────┘

Backend hosting: AKS (modules/aks/). The sentinel repo's
ci_backend_deployment.yml deploys the sentinel-backend image from ACR
to the cluster on every merge to main. Terraform provisions the cluster
only — app manifests live in the sentinel repo (k8s/).
```

---

## 2. Terraform Module Structure

> ⚠️ **Superseded (phase 5).** The root is now layer-split — `main.tf` (providers, config, naming), `platform.tf`, `deployment.tf`, `outputs.tf` — with `var.layer` gating modules by `count`. `oidc.tf` and `identity.tf` are gone; `modules/naming` is new. Two root directories were considered and rejected: two provider blocks and two lock files to keep in step, for one boolean's worth of separation.

One module per Azure resource group concern. Flat structure — no nested modules.
7 modules total. Beyond the modules, the root also declares the **identity plane**
(§4): the `sentinel-gha` UAMI + federated creds, the backend API app registration (§4.4), the
backend workload-identity UAMI + federated credential (§3.7), and the Key Vault
rotation Function + system topic (§3.8) — the last two live in the `functions/`
module.

```
sentinel-infra/
├── main.tf                    # Provider config, RG data source, module calls
├── versions.tf                # required_version + pinned required_providers (C9)
├── variables.tf               # Input variables (subscription_id, location, etc.)
├── outputs.tf                 # Outputs (ACR URL, DB host, etc.) — populated in task 4.4
├── oidc.tf                    # sentinel-gha UAMI + role assignments + fed creds (§4.2)
├── identity.tf                # backend API app regs, IDENTITY tenant (§4.4, task 3.5)
├── terraform.tfvars           # Dev environment values (gitignored)
├── terraform.tfvars.example   # Committed template
├── backend.tf                 # Remote state config (Azure Storage)
├── .terraform.lock.hcl        # Provider hash lock — commit it, or the C9 pins are
│                              #   aspirational rather than reproducible
│
├── scripts/
│   ├── bootstrap-state.sh     # One-time: state RG + storage + container (§8.1)
│   └── bootstrap-oidc.sh      # One-time: UAMI + roles + first 2 fed creds (§4.3)
│
├── docs/
│   └── BOOTSTRAP.md           # The ordered manual runbook (§10)
│
├── modules/
│   ├── acr/                   # Container Registry
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   │
│   ├── postgresql/            # PostgreSQL Flexible Server + DB + pgvector
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   │
│   ├── keyvault/              # Key Vault + secrets + access policies
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   │
│   ├── event-grid/            # Event Grid topic + subscription
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   │
│   ├── functions/             # Azure Function Apps: Event Grid → GHA bridge (§3.5)
│   │   ├── main.tf            #   + Key Vault rotation Function (§3.8)
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   └── src/               # Function source code (Python)
│   │       ├── bridge/        #   Event Grid → repository_dispatch (stamps signal_type)
│   │       │   ├── __init__.py
│   │       │   └── function.json
│   │       └── rotate/        #   SecretNearExpiry → rotate LLM key version
│   │           ├── __init__.py
│   │           └── function.json
│   │
│   ├── app-service/           # App Service F1 for sentinel-deployment
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   │
│   └── aks/                   # AKS cluster — hosts sentinel-backend (1 node)
│       ├── main.tf
│       ├── variables.tf
│       └── outputs.tf
│
├── ci-images/                 # Dockerfiles for CI runner images
│   ├── ci-runner.Dockerfile   # Python 3.12 + ruff + pyright + pytest + az cli
│   └── build-push.sh          # Build and push runner images to ACR
│
├── .github/
│   └── workflows/
│       ├── ci_infra_dry.yml   # terraform validate + plan on push/PR (dry run)
│       ├── ci_infra.yml       # terraform apply on merge to main
│       └── ci_runners.yml     # Build + push CI runner images when Dockerfile changes
│
├── .gitignore
└── README.md
```

### Why per-resource modules (not monorepo flat)?

Each module is independently testable and has clear inputs/outputs. The root
`main.tf` wires them together. If we later split a module into its own Terraform
workspace (e.g., for different lifecycle), the module boundary is already there.

---

## 3. Module Details

> **Globally-unique names carry a `0375` suffix.** ACR, Key Vault, PostgreSQL, Function App,
> App Service and Storage names are unique across **all of Azure**, not per-tenant. Checked
> 2026-08-15: `sentinelacr`, `sentinel-pg`, `sentinel-kv`, `sentineltfstate` and `dummy-api`
> were **all already taken** by other tenants. The suffix is therefore applied to every
> globally-scoped name — **including ones currently free**, because availability today is not
> a reservation and a collision found mid-phase costs a multi-file rename (C12 cost 20
> occurrences across 7 files). Each module takes its name as a **validated variable**, so the
> next collision is a `tfvars` change rather than a code change.
>
> Resource-group-scoped names (`sentinel-rg`, `sentinel-aks`, `sentinel-backend-wi`,
> `sentinel-gha`) need no suffix — they are only unique within the subscription.

### 3.1 ACR Module

```hcl
resource "azurerm_container_registry" "sentinel" {
  name                = "sentinelacr0375"
  resource_group_name = var.resource_group_name
  location            = var.location

  # Standard — and it is FREE, verified 2026-08-16. The subscription is
  # AzureForStudents_2018-01-01, whose 12-month grant covers "1 Standard tier
  # registry with 100 GB storage and 10 webhooks". Basic is a different meter and
  # is NOT covered: the cheaper SKU would have cost ~$5/mo where this costs $0.
  # On a subsidised subscription, "cheaper SKU" and "free SKU" are different
  # questions — check the entitlement before optimising the price.
  sku           = "Standard"
  admin_enabled = true
}
```

**Outputs:** `acr_login_server`, `acr_admin_username`, `acr_admin_password`

**Images stored in ACR:**

| Image | Purpose | Built By |
|-------|---------|----------|
| `sentinel-backend:sha-X` | Backend API container (deployed to AKS — immutable tag pinned by the Deployment) | ci_backend_deployment.yml (sentinel repo) |
| `sentinel-backend:stable` | Bookmark tag for the last fully validated image (humans/debugging only — nothing pulls it at runtime) | ci_backend_deployment.yml |
| `ci-runner:latest` | CI runner with Python 3.12 + dev tools | ci_runners.yml (this repo) |

### 3.2 PostgreSQL Module

```hcl
resource "azurerm_postgresql_flexible_server" "sentinel" {
  name                   = "sentinel-pg-0375"
  resource_group_name    = var.resource_group_name
  location               = var.location
  version                = "16"
  sku_name               = "B_Standard_B1ms"  # Free 750 hrs/mo for 12 months
  storage_mb             = 32768               # 32 GB (free tier limit)
  zone                   = "1"

  # Microsoft Entra–ONLY authentication — no admin password stored anywhere.
  # Every client (GHA runners, the backend pod) presents a short-lived Entra
  # access token (audience https://ossrdbms-aad.database.windows.net) as the
  # psql password. User/SP tokens live ~1 h; managed-identity tokens ~24 h.
  # Password auth is disabled for the server entirely.
  authentication {
    active_directory_auth_enabled = true
    password_auth_enabled         = false
    # REQUIRED in practice: Azure populates this server-side once an Entra admin
    # attaches, so omitting it gives a perpetual diff proposing to null it.
    # Passed from a pinned root variable, not data.azurerm_client_config — an
    # `az login` to the identity tenant elsewhere would otherwise repoint it, and
    # tenant_id is ForceNew here.
    tenant_id = var.tenant_id
  }
}

# rev-9 (2026-08-15): the `sentinel-db-admins` security group is GONE. Creating a group
# is a DIRECTORY write, which the uwindsor.ca tenant denies (§4.2). Entra admins are now
# attached directly — one resource per principal, no group indirection:
#   (1) the human owner, for break-glass psql access
#   (2) the backend pod's workload-identity UAMI (§3.7)
# GHA runners are NOT admins; they connect as an Entra DB role created in §10 step 8.
#
# TRADE-OFF, accepted knowingly: with a group, adding an admin was an Entra membership
# change with no infra deploy. Now it is a Terraform change + apply. Worse day-2
# operability, in exchange for needing zero directory rights. Revisit if R4 closes and
# directory writes become available.
resource "azurerm_postgresql_flexible_server_active_directory_administrator" "human" {
  server_name         = azurerm_postgresql_flexible_server.sentinel.name
  resource_group_name = var.resource_group_name
  tenant_id           = data.azurerm_client_config.current.tenant_id
  object_id           = var.postgres_entra_admin_object_id
  principal_name      = var.postgres_entra_admin_principal_name
  principal_type      = "User"

  # Entra auth must be ON before any Entra DB role is created (Terraform ordering).
  depends_on = [azurerm_postgresql_flexible_server.sentinel]
}

resource "azurerm_postgresql_flexible_server_active_directory_administrator" "backend_uami" {
  server_name         = azurerm_postgresql_flexible_server.sentinel.name
  resource_group_name = var.resource_group_name
  tenant_id           = data.azurerm_client_config.current.tenant_id
  object_id           = var.backend_uami_principal_id
  principal_name      = "sentinel-backend-wi"
  principal_type      = "ServicePrincipal"

  depends_on = [azurerm_postgresql_flexible_server.sentinel]
}

resource "azurerm_postgresql_flexible_server_database" "sentinel" {
  name      = "sentinel"
  server_id = azurerm_postgresql_flexible_server.sentinel.id
  charset   = "UTF8"
  collation = "en_US.utf8"
}

# Enable pgvector extension
resource "azurerm_postgresql_flexible_server_configuration" "pgvector" {
  name      = "azure.extensions"
  server_id = azurerm_postgresql_flexible_server.sentinel.id
  value     = "VECTOR"
}

# Firewall: allow all (dev). Network reach ≠ auth — every connection still needs
# a valid Entra token (password auth is disabled), so an open firewall only
# controls who can *reach* the port, not who can *log in*.
# Two client classes connect: (1) the backend on AKS (workload-identity token),
# (2) GHA workflows on GitHub-hosted runners — ci_app_deployment.yml inserts
# deploy rows, ci_incident_response.yml fetches context + records PR refs
# (each acquires an Entra DB token from the sentinel-gha SP).
# GitHub runner IPs rotate across a wide range. During dev we allow all.
# Production would use Private Endpoint + VNet integration.
resource "azurerm_postgresql_flexible_server_firewall_rule" "allow_all_dev" {
  name             = "allow-all-dev"
  server_id        = azurerm_postgresql_flexible_server.sentinel.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "255.255.255.255"
}
```

**Why allow-all?** GHA workflows talk to PostgreSQL directly (deploy recording,
context fetches, PR-reference updates) from GitHub-hosted runners, whose IPs rotate
across a wide CIDR range that changes weekly. There's no stable IP to whitelist.
The `0.0.0.0/0.0.0.0` rule (Azure services only) doesn't cover GitHub runners —
they're not Azure services. The AKS backend's egress IP alone isn't enough. Options:

| Approach | Dev? | Production? |
|----------|------|-------------|
| Allow all (`0.0.0.0`–`255.255.255.255`) | **Yes — simple, works** | No |
| GitHub meta API IP ranges (dynamic) | Fragile — IPs change | No |
| Azure-hosted self-hosted runner | Works but costs money | Maybe |
| Private Endpoint + VNet | Overkill for dev | **Yes** |

We use allow-all for dev. The DB is still protected by **Entra token auth** —
password auth is off, so reaching the port is useless without a valid token
from a Postgres Entra admin (§3.2) or an Entra DB role one of them created.
Lock down the network later with Private Endpoint if needed.

**Entra DB roles (created once by the Entra admin, not by Terraform):** after the
server exists, the admin connects and runs `SELECT * FROM pgaadauth_create_principal(...)`
(or `CREATE ROLE ... ; SECURITY LABEL ...`) to map the `sentinel-gha` SP and the
backend UAMI to PostgreSQL roles with the right grants. Azure matches the token to
the role by the principal's Entra object ID, not its name.

**Connecting (token as password):**
```bash
# GHA runner (after azure/login OIDC) or any Entra principal
PGPASSWORD=$(az account get-access-token \
  --resource https://ossrdbms-aad.database.windows.net \
  --query accessToken -o tsv)
psql "host=sentinel-pg-0375.postgres.database.azure.com dbname=sentinel \
      user=sentinel-gha sslmode=require"   # token supplied via PGPASSWORD
```

**Outputs:** `db_host`, `db_name`, `db_port` (no password output — there is none)

### 3.3 Key Vault Module

```hcl
resource "azurerm_key_vault" "sentinel" {
  name                       = "sentinel-kv-0375"
  location                   = var.location
  resource_group_name        = var.resource_group_name
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "standard"  # Always free (10K txns)
  # Renamed in azurerm v4 — `enable_rbac_authorization` is deprecated and removed in
  # v5. Verified against the pinned 4.81.0 binary, 2026-08-15.
  rbac_authorization_enabled = true

  # Soft-delete is NOT optional on Key Vault (owner decision 2026-08-15). Azure's
  # default of 90 days + purge protection would leave this vault's globally unique
  # name reserved after any teardown, so the "everything, always" rebuild could
  # never recreate it under the same name. The purge that reclaims it needs
  # SUBSCRIPTION scope, which is why teardown is Owner-run and local (R6, §7.3). 7 days + purge allowed
  # makes the designed loop work. Accepted cost: a mistaken destroy can be purged
  # for real — tolerable because all 9 secrets are re-seedable from their external
  # sources (§10 step 7); the vault holds no generated state.
  soft_delete_retention_days = 7
  purge_protection_enabled   = false
}

# Terraform SP — full secret management (set secrets during apply)
resource "azurerm_role_assignment" "terraform_kv_admin" {
  scope                = azurerm_key_vault.sentinel.id
  role_definition_name = "Key Vault Secrets Officer"
  principal_id         = data.azurerm_client_config.current.object_id
}

# GHA SP — read-only (ci_incident_response.yml fetches secrets at runtime)
resource "azurerm_role_assignment" "gha_kv_reader" {
  scope                = azurerm_key_vault.sentinel.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.sentinel_gha.principal_id
}

# Backend pod (workload-identity UAMI, §3.7) — read-only. The pod reads LLM keys
# directly from Key Vault via workload identity, so no secret needs to be baked
# into the K8s Secret for those. No stored credential in the pod.
resource "azurerm_role_assignment" "backend_kv_reader" {
  scope                = azurerm_key_vault.sentinel.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.backend.principal_id
}

# Rotation Function (system-assigned MI, §3.8) — Officer, writes new secret
# versions when a SecretNearExpiry event fires.
resource "azurerm_role_assignment" "rotator_kv_officer" {
  scope                = azurerm_key_vault.sentinel.id
  role_definition_name = "Key Vault Secrets Officer"
  principal_id         = azurerm_linux_function_app.rotator.identity[0].principal_id
}
```

**Access levels:**

| Identity | Role | Purpose |
|----------|------|---------|
| Terraform SP | `Key Vault Secrets Officer` | Create/update secrets + set rotation policies during `terraform apply` |
| GHA SP (OIDC) | `Key Vault Secrets User` | Read-only — `az keyvault secret show` in ci_incident_response.yml |
| Backend UAMI (workload identity) | `Key Vault Secrets User` | Read-only — pod reads LLM keys at runtime, no baked-in secret |
| Rotation Function (system MI) | `Key Vault Secrets Officer` | Writes rotated secret versions (§3.8) |

The GHA SP is the same OIDC-federated identity used by all three repos'
workflows. It can read secrets but never modify them — only Terraform (setup)
and the rotation Function (rotation) write secrets.

**Secrets stored:**

| Secret Name | Description | Consumed By | Rotation |
|-------------|-------------|-------------|----------|
| `anthropic-api-key` | Anthropic LLM provider (default) | Backend (reads via workload identity) | **Rotation policy** (§3.8) |
| `openai-api-key` | OpenAI LLM provider (fallback) | Backend (reads via workload identity) | **Rotation policy** (§3.8) |
| `dd-api-key` | Datadog API key | GHA jobs (Datadog event reporting) | Manual |
| `dd-app-key` | Datadog app key | GHA jobs (Datadog log queries) | Manual |
| `teams-webhook-url` | Teams incoming webhook | GHA jobs (notifications) | Manual |
| `langfuse-secret-key` | LangFuse tracing (secret) | Backend (workload identity) | Manual |
| `langfuse-public-key` | LangFuse tracing (public) | Backend (workload identity) | Manual |
| `acr-password` | ACR admin password | GHA jobs (`container:` image pull) | Manual |
| `github-pat` | GitHub PAT with `repo` scope | Azure Function bridge (repository_dispatch) | Manual |

**Removed vs the previous design:**
- ❌ `db-password` — **gone.** PostgreSQL is Entra-only (§3.2); clients present a
  short-lived Entra token as the password. Nothing stores a DB password.
- ❌ `sentinel-api-token` — **gone.** The backend API is protected by Entra bearer
  tokens (§4.5), validated against Entra JWKS. No shared static token exists.

**Still standing (honest accounting):** `acr-password` and `github-pat` remain
genuine secrets. `acr-password` is needed because GHA `container:` jobs pull the
CI-runner image *before* any step runs (can't `az acr login` first); `github-pat`
is needed by the Function bridge's `repository_dispatch` and Terraform's github
provider. Both are bootstrap-class, not runtime-request credentials. Eliminating
them fully would need a GitHub App + Azure-hosted runners (out of scope for now).

**Secret flow 1: backend pod → Key Vault + PostgreSQL via workload identity (runtime):**

```
ci_backend_deployment.yml (sentinel repo, merge to main) — deploy-to-aks job:
│
├── kubectl set image deployment/sentinel-backend sentinel-backend=<ACR>:sha-X
├── kubectl rollout status deployment/sentinel-backend
│
└── validate: curl $BACKEND_URL/health + /ready  (checks DB token + LangFuse)

NO secret sync — no K8s Secret is created. The pod runs under a workload-identity
service account (§3.7). At runtime it exchanges its projected SA token for an
Entra token and:
  • reads anthropic-api-key / openai-api-key / langfuse-* straight from Key Vault
  • gets a PostgreSQL token (aud https://ossrdbms-aad.database.windows.net) for DB
Nothing sensitive is baked into the Deployment manifest or a K8s Secret.
```

**Secret flow 2: GHA jobs acquire per-job tokens/secrets (incident runtime):**

```
ci_incident_response.yml — each job acquires ONLY what it needs, in-job.
(GHA drops masked secrets from job outputs — never pass secrets between jobs.)
│
├── fetch-service-info:   az account get-access-token --resource \
│                           https://ossrdbms-aad.database.windows.net   (Entra DB token → psql read)
├── fetch-datadog-logs:   az keyvault secret show --name dd-api-key
├── run-agent-pipeline:   az account get-access-token --resource \
│                           api://sentinel-backend                      (Entra token → Authorization: Bearer)
├── create-rollback-pr:   Entra DB token (psql UPDATE) + github-pat (open PR)
└── notify-* / summary:   az keyvault secret show --name teams-webhook-url

ci_app_deployment.yml (sentinel-deployment repo):
└── record-deployment:    az account get-access-token --resource \
                            https://ossrdbms-aad.database.windows.net   (Entra DB token → psql INSERT)
```

Two token audiences, one identity: the `sentinel-gha` SP asks Entra for a
DB-scoped token *and* an `api://sentinel-backend`-scoped token as needed — see
§4.5 "one identity, many audience-scoped tokens."

### 3.4 Event Grid Module

The topic ingests **two distinct Datadog signal types**, both from the
sentinel-deployment ground-truth app (see sentinel-deployment ARCHITECTURE §4):

| Signal type | Datadog source | Meaning | Backend handling path |
|-------------|----------------|---------|-----------------------|
| `deploy_failure` | `sentinel-deploy-failure` event monitor (`deploy_status:failed`) | The deploy itself failed; the previous good version stays live | **Case 2 — rollback** (simple; heal main's deployability) |
| `runtime_error` | `sentinel-runtime-health` monitor (5xx rate / failed health pings) | Deploy went green but the live app throws errors | **Case 3 — full incident response** (diagnose → rollback/escalate) |

(Case 1 = a clean deploy fires **no** monitor — nothing reaches Event Grid.)

Both monitors POST to the same topic; the bridge Function (§3.5) inspects the
event, stamps `signal_type` onto the `client_payload`, and dispatches to the
sentinel repo. The backend incident workflow branches on `signal_type`.

```hcl
resource "azurerm_eventgrid_topic" "sentinel" {
  name                = "sentinel-events-0375" # endpoint is a public DNS name → 0375 convention
  location            = var.location
  resource_group_name = var.resource_group_name
}

# One subscription → the bridge Function. The Function classifies the payload
# into deploy_failure vs runtime_error (it does not need two subscriptions —
# both Datadog monitors carry tags the Function reads).
resource "azurerm_eventgrid_event_subscription" "to_function" {
  name  = "sentinel-to-function"
  scope = azurerm_eventgrid_topic.sentinel.id

  azure_function_endpoint {
    function_id = "${var.function_app_id}/functions/bridge"
  }
}
```

### 3.5 Azure Function Module (Event Grid → GHA Bridge)

```hcl
resource "azurerm_service_plan" "functions" {
  name                = "sentinel-func-plan"
  location            = var.location
  resource_group_name = var.resource_group_name
  os_type             = "Linux"
  sku_name            = "Y1"  # Consumption plan — always free (1M reqs)
}

# Mandatory backing storage for the Consumption plan. Globally unique name →
# 0375 convention; was referenced but never declared before 2026-08-23.
resource "azurerm_storage_account" "func" {
  name                     = "sentinelfunc0375"
  location                 = var.location
  resource_group_name      = var.resource_group_name
  account_tier             = "Standard"
  account_replication_type = "LRS"
  min_tls_version          = "TLS1_2"
}

resource "azurerm_linux_function_app" "bridge" {
  name                = "sentinel-bridge-0375"
  location            = var.location
  resource_group_name = var.resource_group_name
  service_plan_id     = azurerm_service_plan.functions.id

  storage_account_name       = azurerm_storage_account.func.name
  storage_account_access_key = azurerm_storage_account.func.primary_access_key

  # REQUIRED (gap fixed 2026-08-23): the GITHUB_TOKEN app setting below is a
  # Key Vault *reference*. Without an identity holding Secrets User on the
  # vault it resolves EMPTY — silently — and the bridge 401s at runtime with
  # nothing in the logs pointing at the cause. The keyvault module exposes
  # enable_bridge_reader for exactly this principal.
  identity {
    type = "SystemAssigned"
  }

  site_config {
    application_stack {
      python_version = "3.12"
    }
  }

  app_settings = {
    "GITHUB_TOKEN"      = "@Microsoft.KeyVault(VaultName=sentinel-kv-0375;SecretName=github-pat)"
    "GITHUB_REPO"       = "Keshav0375/Sentinel"
    "GITHUB_EVENT_TYPE" = "incident-alert"

    # Oryx remote build — the function code ships WITH the infrastructure
    # (archive_file + zip_deploy_file): no CI workflow deploys function code,
    # and Event Grid's endpoint validation needs the function to exist.
    "SCM_DO_BUILD_DURING_DEPLOYMENT" = "true"
    "ENABLE_ORYX_BUILD"              = "true"
  }

  zip_deploy_file = data.archive_file.bridge.output_path
}

# As BUILT (2026-08-23, revised same day after review): the handler is stdlib
# `urllib`, and `client_payload` is exactly THREE top-level keys —
#   { "signal_type", "correlation_id", "event": <the full Datadog payload> }
# NOT a flat {**data} passthrough: GitHub hard-caps client_payload at 10
# top-level properties (422 beyond), and a real Datadog event exceeds that.
# correlation_id is the Event Grid event id — STABLE across re-deliveries, so
# duplicate dispatches are dedupable downstream. Datadog's $TAGS renders as a
# comma-joined STRING; the classifier normalizes string/list/null shapes.
# Consumers (backend 5.1) read client_payload.event.*.
# Unit tests: modules/functions/tests/test_handlers.py — 14, stdlib-only.
```

**Bridge function source (Python):**

```python
import httpx
import azure.functions as func


def _classify(data: dict) -> str:
    """deploy_failure vs runtime_error, from Datadog monitor tags."""
    tags = " ".join(data.get("tags", [])) + data.get("title", "")
    return "deploy_failure" if "deploy_status:failed" in tags else "runtime_error"


def main(event: func.EventGridEvent):
    """Event Grid → GitHub repository_dispatch, stamped with signal_type."""
    data = event.get_json()
    signal_type = _classify(data)

    httpx.post(
        f"https://api.github.com/repos/{GITHUB_REPO}/dispatches",
        headers={
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json",
        },
        json={
            "event_type": GITHUB_EVENT_TYPE,
            "client_payload": {**data, "signal_type": signal_type},
        },
    )
```

`signal_type` drives the backend workflow branch: `deploy_failure` → Case 2
(rollback), `runtime_error` → Case 3 (full incident response).

### 3.6 App Service Module (for sentinel-deployment)

```hcl
resource "azurerm_service_plan" "deployment" {
  name                = "sentinel-deploy-plan"
  location            = var.location
  resource_group_name = var.resource_group_name
  os_type             = "Linux"
  sku_name            = "F1"  # Always free
}

resource "azurerm_linux_web_app" "dummy_api" {
  name                = "dummy-api-0375"
  location            = var.location
  resource_group_name = var.resource_group_name
  service_plan_id     = azurerm_service_plan.deployment.id

  site_config {
    # F1 REJECTS Always On (azurerm defaults it true → apply fails) and only
    # offers a 32-bit worker. Both are hard constraints of the free tier, not
    # preferences.
    always_on         = false
    use_32_bit_worker = true

    application_stack {
      python_version = "3.12"
    }
  }

  app_settings = {
    "APP_VERSION" = "initial"
    "DD_SERVICE"  = "dummy-api-0375"
    "DD_ENV"      = "dev"
    "SCM_DO_BUILD_DURING_DEPLOYMENT" = "true"
  }
}
```

### 3.7 AKS Module (Backend Hosting)

```hcl
resource "azurerm_kubernetes_cluster" "sentinel" {
  name                = "sentinel-aks"
  location            = var.location
  resource_group_name = var.resource_group_name
  dns_prefix          = "sentinel"
  sku_tier            = "Free"          # control plane — always free

  # Workload identity: the cluster becomes an OIDC issuer; pods federate their
  # projected service-account token to an Entra identity for passwordless access
  # to Key Vault + PostgreSQL. No stored secret in the pod.
  oidc_issuer_enabled       = true
  workload_identity_enabled = true

  default_node_pool {
    name       = "default"
    node_count = 1
    # B2pls_v2 (ARM64, 2 vCPU / 4 GiB) — third SKU, each prior rejected live
    # (2026-08-23): B2ats_v2 fails SystemPoolSkuTooLow (system pools need >=4 GB;
    # it has 1 GiB — the free grant is unusable for AKS), and B2s is not in this
    # subscription's allowed AKS list for canadacentral, where every permitted
    # small SKU is ARM. A system pool also cannot scale below 1 node, so
    # scale-to-zero is `az aks stop`/`start` on the whole cluster. ~$0.03/hr,
    # bills only while started. CONSEQUENCE: the backend image must be built
    # linux/arm64 (backend §13 / task 7.1, docker buildx).
    vm_size    = "Standard_B2pls_v2"
  }

  identity {
    type = "SystemAssigned"
  }

  # Scale-to-zero: sentinel repo workflows scale the node pool 0↔1 at runtime
  # (backend-up/backend-down actions + nightly auto-down). Don't let
  # terraform apply fight them over node_count.
  lifecycle {
    ignore_changes = [default_node_pool[0].node_count]
  }
}

# Kubelet pulls images from ACR without imagePullSecrets
resource "azurerm_role_assignment" "aks_acr_pull" {
  scope                = azurerm_container_registry.sentinel.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_kubernetes_cluster.sentinel.kubelet_identity[0].object_id
}

# The sentinel-gha UAMI can deploy (az aks get-credentials + kubectl)
resource "azurerm_role_assignment" "gha_aks_user" {
  scope                = azurerm_kubernetes_cluster.sentinel.id
  role_definition_name = "Azure Kubernetes Service Cluster User Role"
  principal_id         = azurerm_user_assigned_identity.sentinel_gha.principal_id
}

# ── Backend workload identity ────────────────────────────────────────────────
# User-assigned identity the backend pod runs as. It gets Key Vault Secrets User
# (§3.3) and is attached directly as a PostgreSQL Entra admin (§3.2, rev-9).
resource "azurerm_user_assigned_identity" "backend" {
  name                = "sentinel-backend-wi"
  location            = var.location
  resource_group_name = var.resource_group_name
}

# Federate the K8s service account to the UAMI. Subject is the SA that the
# Deployment runs under; audience is the workload-identity exchange audience.
resource "azurerm_federated_identity_credential" "backend" {
  name = "sentinel-backend-fic"
  # `resource_group_name` is unused and `parent_id` is renamed in azurerm v4 — both
  # emit deprecation warnings. Corrected 2026-08-15 after infra 1.3 hit them live.
  user_assigned_identity_id = azurerm_user_assigned_identity.backend.id
  audience                  = ["api://AzureADTokenExchange"]
  issuer              = azurerm_kubernetes_cluster.sentinel.oidc_issuer_url
  subject             = "system:serviceaccount:sentinel:sentinel-backend"  # namespace:sa
}
```

The K8s Deployment references this via a ServiceAccount annotated with
`azure.workload.identity/client-id = <backend UAMI client id>` and the pod label
`azure.workload.identity/use: "true"` (manifests live in the sentinel repo,
`azure/k8s/`). Outputs `backend_identity_client_id` for the sentinel repo to
stamp into the ServiceAccount annotation.

**Lifecycle split:** Terraform provisions the cluster only. The `sentinel-backend`
Deployment/Service manifests live in the sentinel repo (`azure/k8s/`) and are applied by
`ci_backend_deployment.yml` — app deployment is CI's job, not Terraform's. Infra
changes rarely; the app deploys on every merge.

**Outputs:** `aks_cluster_name`, `aks_resource_group`, `oidc_issuer_url`,
`backend_identity_client_id`

---

### 3.8 Rotation Function Module (LLM key rotation)

Azure Key Vault has **no dynamic secret engine** (that is a HashiCorp Vault
concept). It stores static secret *versions* with a **rotation policy** plus an
Event Grid `SecretNearExpiry` notification. We use that to rotate the LLM keys
on a schedule — rotation, not on-demand generation (no LLM provider mints
ephemeral keys).

```hcl
# NO azurerm_key_vault_secret HERE (corrected 2026-08-23; the original snippet
# declared one with value = var.anthropic_api_key). Phase 2 ships ZERO secret
# resources — a secret in HCL is plaintext state — and `timeadd(timestamp(),...)`
# would force a new version on every apply. Expiry is a SEED-TIME concern:
# §10 step 7 seeds with `az keyvault secret set --expires` (+90d), and the
# rotator re-stamps a fresh 90-day expiry on every version it writes, so the
# invariant self-maintains after the first seed. Terraform manages only the
# rotation INFRASTRUCTURE below.

# A second Function App (Consumption, always free) with a system-assigned MI.
# As BUILT: app settings KEY_VAULT_URI / KEY_VAULT_NAME / TEAMS_WEBHOOK_URL
# (a Key Vault reference — Officer includes read). ANTHROPIC_ADMIN_KEY is
# deliberately ABSENT: no admin key exists among the nine secrets, so the
# rotator's default is the manual Teams path; configuring it later enables
# auto-mint with no code change. The KV system topic + SecretNearExpiry
# subscription live in modules/keyvault (not here as this section's tree once
# implied): their lifecycle is the VAULT's — destroy the vault, they die too.
resource "azurerm_linux_function_app" "rotator" {
  name                = "sentinel-rotator-0375"
  location            = var.location
  resource_group_name = var.resource_group_name
  service_plan_id     = azurerm_service_plan.functions.id   # shares the bridge's Y1 plan

  storage_account_name       = azurerm_storage_account.func.name
  storage_account_access_key = azurerm_storage_account.func.primary_access_key

  identity { type = "SystemAssigned" }        # → Key Vault Secrets Officer (§3.3)

  site_config { application_stack { python_version = "3.12" } }
}

# Event Grid: Key Vault SecretNearExpiry → rotator Function.
resource "azurerm_eventgrid_system_topic" "kv" {
  name                   = "sentinel-kv-0375-events"
  location               = var.location
  resource_group_name    = var.resource_group_name
  # `source_arm_resource_id` is deprecated in azurerm v4 (fourth deprecation of
  # this class after enable_rbac_authorization / parent_id / resource_group_name).
  source_resource_id = azurerm_key_vault.sentinel.id
  topic_type             = "Microsoft.KeyVault.vaults"
}

resource "azurerm_eventgrid_system_topic_event_subscription" "rotate" {
  name                = "sentinel-rotate-on-near-expiry"
  system_topic        = azurerm_eventgrid_system_topic.kv.name
  resource_group_name = var.resource_group_name
  included_event_types = ["Microsoft.KeyVault.SecretNearExpiry"]

  azure_function_endpoint {
    function_id = "${azurerm_linux_function_app.rotator.id}/functions/rotate"
  }
}
```

**Rotator Function logic (Python):** on `SecretNearExpiry`, read the secret name
from the event → call the provider's key-management API to mint a fresh key
(Anthropic Admin API `/v1/organizations/api_keys` where org-admin is available;
otherwise the function logs a "manual rotation required" alert to Teams) →
`set_secret` a new version with a fresh 90-day expiry. The backend always reads
the *latest* version via workload identity, so it picks up rotated keys with no
redeploy.

> **Honesty note:** true zero-touch rotation needs a provider key API. Anthropic
> exposes an Admin API for API-key management on qualifying plans; if that is not
> available on the student/dev account, the rotator degrades to a scheduled
> reminder rather than silently doing nothing.

**Outputs:** none consumed downstream (self-contained).

---

## 4. Identity Plane — OIDC + Entra (Workload Identity Federation)

> ⚠️ **Superseded (phase 5).** One identity became three. The dangerous rights are no longer made safe by *narrow scope* — they cannot be, once deployments create their own resource groups — but by being **unreachable**: `gha-deploy` federates only on `environment:*` subjects, and GitHub will not mint those for a `pull_request` event. §4.4's single backend app registration becomes one **per deployment**, so a token minted for one fails audience validation at another.

All three repos authenticate to Azure via OIDC — no stored client secrets.
GitHub proves identity via JWT, Azure trusts it via federated credentials.

### 4.1 How OIDC works

```
GHA workflow                Azure AD
    │                           │
    ├── request JWT token ──►   │
    │   (from GitHub OIDC       │
    │    provider)              │
    │                           │
    ├── az login with JWT ──►   │  verifies issuer = GitHub
    │                           │  verifies subject = repo:org/name:ref:refs/heads/main
    │                           │
    │   ◄── access token ──────┤  scoped to sentinel-rg
    │                           │
    ├── use token for:          │
    │   ├── terraform apply     │
    │   ├── az keyvault secret  │
    │   ├── az acr login        │
    │   └── docker push/pull    │
```

### 4.2 Terraform resources for OIDC

> **rev-9 (2026-08-15) — the CI identity is a User-Assigned Managed Identity, not an app
> registration.** See `decisions.md` "Identity plane rebuilt on managed identities". The
> Sentinel subscription lives in the **University of Windsor** Entra tenant
> (`uwindsor.ca`, `12f933b3-3d61-4b19-9a4d-689021de8cc9`), where the owner holds
> **Owner on the subscription but no directory WRITE rights** — `azuread_application` cannot be
> created. A UAMI is an ordinary Azure resource governed by Azure RBAC, and it carries
> federated identity credentials exactly like an app registration does. `azure/login@v2`
> treats the two identically.

> **Casing matters.** The GitHub OIDC token's `sub` claim uses the repository's canonical
> owner/name (`Keshav0375/Sentinel-infra`, `Keshav0375/Sentinel-deployment`,
> `Keshav0375/Sentinel`), and Azure matches federated-credential subjects as an exact,
> case-sensitive string. Use the real casing below verbatim.

```hcl
# The resource group is created out-of-band by the bootstrap (§10 step 1) and deleted
# by the teardown procedure (§7.3). Terraform reads it, never owns it.
data "azurerm_resource_group" "sentinel" {
  name = var.resource_group_name
}

# The CI identity. A UAMI, not an app registration — see the rev-9 note above.
resource "azurerm_user_assigned_identity" "sentinel_gha" {
  name                = "sentinel-gha"
  resource_group_name = data.azurerm_resource_group.sentinel.name
  location            = var.location
}

# Contributor on the resource group — lets CI manage every Sentinel resource.
resource "azurerm_role_assignment" "gha_contributor" {
  scope                = data.azurerm_resource_group.sentinel.id
  role_definition_name = "Contributor"
  principal_id         = azurerm_user_assigned_identity.sentinel_gha.principal_id
}

# Terraform state lives in a DIFFERENT resource group (§8.1), outside Contributor's
# scope. Without this, `terraform init` fails in CI — the backend uses Entra auth
# (use_azuread_auth), so blob-level RBAC is the credential path.
resource "azurerm_role_assignment" "gha_state_blob" {
  scope                = "/subscriptions/${var.subscription_id}/resourceGroups/sentinel-state-rg/providers/Microsoft.Storage/storageAccounts/sentineltfstate0375"
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.sentinel_gha.principal_id
}

# R5 (2026-08-15). Contributor CANNOT create role assignments — its notActions
# include Microsoft.Authorization/*/Write and /Delete. Phases 2-3 declare six
# Terraform-managed assignments (Key Vault Secrets Officer/User, AcrPull, AKS
# Cluster User), so without this the first CI apply touching any of them fails
# with AuthorizationFailed, and the teardown could not remove them either.
#
# "Role Based Access Control Administrator", not Owner or User Access
# Administrator: its built-in definition carries an ABAC condition forbidding the
# assignment of Owner, User Access Administrator and itself. CI can grant what the
# modules need but cannot escalate its own privileges — which matters because
# these credentials are reachable from pull_request-triggered workflows.
resource "azurerm_role_assignment" "gha_rbac_admin" {
  scope                = data.azurerm_resource_group.sentinel.id
  role_definition_name = "Role Based Access Control Administrator"
  principal_id         = azurerm_user_assigned_identity.sentinel_gha.principal_id
}

# §7.3 finishes with `az group delete sentinel-state-rg`. The blob grant above
# covers data inside the account, not the group. TENSION accepted knowingly: this
# lets CI delete the state that protects it. The isolation that matters still
# holds — `terraform destroy` cannot delete the state describing the run in
# progress — but the full teardown is a deliberate, separate, final step.
resource "azurerm_role_assignment" "gha_state_rg_contributor" {
  scope                = "/subscriptions/${var.subscription_id}/resourceGroups/sentinel-state-rg"
  role_definition_name = "Contributor"
  principal_id         = azurerm_user_assigned_identity.sentinel_gha.principal_id
}

# Federated credentials — one per repo + trigger combination. Children of the UAMI,
# so they are plain Azure resources (RBAC), not directory objects.
resource "azurerm_federated_identity_credential" "sentinel_infra_main" {
  name                = "sentinel-infra-main"
  user_assigned_identity_id = azurerm_user_assigned_identity.sentinel_gha.id
  audience            = ["api://AzureADTokenExchange"]
  issuer              = "https://token.actions.githubusercontent.com"
  subject             = "repo:Keshav0375/Sentinel-infra:ref:refs/heads/main"
}

resource "azurerm_federated_identity_credential" "sentinel_infra_pr" {
  name                = "sentinel-infra-pr"
  user_assigned_identity_id = azurerm_user_assigned_identity.sentinel_gha.id
  audience            = ["api://AzureADTokenExchange"]
  issuer              = "https://token.actions.githubusercontent.com"
  subject             = "repo:Keshav0375/Sentinel-infra:pull_request"
}

resource "azurerm_federated_identity_credential" "sentinel_main" {
  name                = "sentinel-main"
  user_assigned_identity_id = azurerm_user_assigned_identity.sentinel_gha.id
  audience            = ["api://AzureADTokenExchange"]
  issuer              = "https://token.actions.githubusercontent.com"
  subject             = "repo:Keshav0375/Sentinel:ref:refs/heads/main"
}

resource "azurerm_federated_identity_credential" "sentinel_pr" {
  name                = "sentinel-pr"
  user_assigned_identity_id = azurerm_user_assigned_identity.sentinel_gha.id
  audience            = ["api://AzureADTokenExchange"]
  issuer              = "https://token.actions.githubusercontent.com"
  subject             = "repo:Keshav0375/Sentinel:pull_request"
}

resource "azurerm_federated_identity_credential" "sentinel_deployment_main" {
  name                = "sentinel-deployment-main"
  user_assigned_identity_id = azurerm_user_assigned_identity.sentinel_gha.id
  audience            = ["api://AzureADTokenExchange"]
  issuer              = "https://token.actions.githubusercontent.com"
  subject             = "repo:Keshav0375/Sentinel-deployment:ref:refs/heads/main"
}
```

**Limits worth knowing:** a managed identity accepts up to **20** federated credentials
(we use 5), and `subject` cannot be wildcarded — every new repo/trigger pair is a new
resource. That is deliberate: the blast radius of a leaked GitHub workflow is one branch
of one repo.

### 4.3 Chicken-and-egg: bootstrapping OIDC

The federated credential is itself a Terraform resource — but Terraform needs Azure
access to create it. That circularity is resolved by one deliberate manual seam:

1. **Manual (one-time):** create the UAMI, both role assignments, and the two
   `Sentinel-infra` federated credentials via `az`.
2. **Import into Terraform:** all five objects (§4.3.1) — not just the identity.
3. **After import:** Terraform manages every remaining federated credential.

> **Run this in PowerShell.** In Git Bash (MSYS2), `--scope /subscriptions/...` is
> rewritten to a Windows path and the command fails confusingly. If you must use Git
> Bash, prefix `MSYS_NO_PATHCONV=1`. `scripts/bootstrap-oidc.sh` sets this itself.

```bash
SUB_ID=<subscription-id>
LOCATION=canadacentral

az group create --name sentinel-rg --location $LOCATION

# The CI identity — a plain Azure resource, no directory rights required.
az identity create --name sentinel-gha --resource-group sentinel-rg --location $LOCATION
CLIENT_ID=$(az identity show -n sentinel-gha -g sentinel-rg --query clientId -o tsv)
PRINCIPAL_ID=$(az identity show -n sentinel-gha -g sentinel-rg --query principalId -o tsv)

# --assignee-object-id + --assignee-principal-type skip the Microsoft Graph lookup that
# plain --assignee performs. Reads of your own user work (default User.Read), but the
# Graph lookup --assignee needs is denied here, so use the explicit form. That
# lookup fails; this form does not.
az role assignment create --assignee-object-id $PRINCIPAL_ID \
  --assignee-principal-type ServicePrincipal --role Contributor \
  --scope /subscriptions/$SUB_ID/resourceGroups/sentinel-rg

az role assignment create --assignee-object-id $PRINCIPAL_ID \
  --assignee-principal-type ServicePrincipal --role "Storage Blob Data Contributor" \
  --scope /subscriptions/$SUB_ID/resourceGroups/sentinel-state-rg/providers/Microsoft.Storage/storageAccounts/sentineltfstate0375

# First two federated credentials, so ci_infra_dry.yml (PR) and ci_infra.yml (main) run.
az identity federated-credential create --name sentinel-infra-main \
  --identity-name sentinel-gha --resource-group sentinel-rg \
  --issuer https://token.actions.githubusercontent.com \
  --subject repo:Keshav0375/Sentinel-infra:ref:refs/heads/main \
  --audiences api://AzureADTokenExchange

az identity federated-credential create --name sentinel-infra-pr \
  --identity-name sentinel-gha --resource-group sentinel-rg \
  --issuer https://token.actions.githubusercontent.com \
  --subject repo:Keshav0375/Sentinel-infra:pull_request \
  --audiences api://AzureADTokenExchange
```

#### 4.3.1 The import set (all seven — partial import breaks the first apply)

The bootstrap creates seven objects Terraform also declares. Importing only the identity
leaves six to collide on the first `apply`. Managed-identity resources import by Azure
resource ID, which is derivable — one practical advantage over app registrations, whose
import ID is an opaque directory object ID.

```bash
RG=/subscriptions/$SUB_ID/resourceGroups/sentinel-rg
UAMI=$RG/providers/Microsoft.ManagedIdentity/userAssignedIdentities/sentinel-gha

terraform import azurerm_user_assigned_identity.sentinel_gha $UAMI
terraform import azurerm_federated_identity_credential.sentinel_infra_main $UAMI/federatedIdentityCredentials/sentinel-infra-main
terraform import azurerm_federated_identity_credential.sentinel_infra_pr   $UAMI/federatedIdentityCredentials/sentinel-infra-pr

# Role assignments import by assignment GUID — list them first:
#   az role assignment list --assignee $PRINCIPAL_ID --all --query "[].id" -o tsv
terraform import azurerm_role_assignment.gha_contributor            <contributor-assignment-id>
terraform import azurerm_role_assignment.gha_state_blob             <blob-assignment-id>
terraform import azurerm_role_assignment.gha_rbac_admin             <rbac-admin-assignment-id>
terraform import azurerm_role_assignment.gha_state_rg_contributor   <state-rg-assignment-id>
```

> **⚠ Two traps, both hit for real on 2026-08-15.**
>
> **1. Resource-ID casing.** `az identity show --query id` returns the id with
> **`resourcegroups`** (lowercase g). The azurerm provider's ID parser is case-sensitive and
> rejects it with *"parsing segment 'subscriptions': the segment at position 0 didn't
> match"* — an error that points nowhere near the real cause. Build the id by hand with
> **`resourceGroups`**. `scripts/bootstrap-oidc.sh` does this rather than echoing what `az`
> returned.
>
> **2. MSYS path mangling applies to `terraform`, not just `az`.** In Git Bash,
> `/subscriptions/...` is rewritten to `C:/Program Files/Git/subscriptions/...` for **any**
> command. Run the imports in PowerShell, or `export MSYS_NO_PATHCONV=1` first.

**Acceptance:** `terraform plan` after the imports shows **no destroy and no replace**.
Anything else means an attribute drifted between the `az` call and the HCL.

> **Do not set `skip_service_principal_aad_check` on these two role assignments.** It guards
> the PrincipalNotFound race when *Terraform* creates an assignment against a still-
> replicating principal — but these are always created by the bootstrap script and only
> imported, so the race cannot occur. It is also **create-only**: on an imported assignment
> it plans as an in-place update that then fails with `doesn't support update`. Phase 2/3
> assignments (AcrPull, Key Vault) *do* create against fresh identities and should set it.

After this, set the GitHub *variables* in §9 (`AZURE_CLIENT_ID` = the UAMI's `clientId`,
not its principal ID). Then `ci_infra.yml` runs and Terraform manages the rest.

### 4.4 Backend API app registration (inbound Entra bearer auth)

> ✅ **R4 RESOLVED 2026-08-15 → two-tenant identity split.** Defining an API audience
> (`api://sentinel-backend`) and an app role (`Incident.Write`) requires an
> `azuread_application` — a **directory** object. A managed identity is a subscription
> resource: it can *hold* an app role but cannot *define* one, so the rev-9 rebuild could
> not rescue this. `uwindsor.ca` denies app registration at tenant policy
> (`allowedToCreateApps: false`) and **UWindsor IT is not an option**. Therefore these two
> app registrations — and **only** these two — live in a **personally-owned Entra tenant**.
>
> **What does NOT move.** The CI identity (`sentinel-gha` UAMI), the Postgres Entra admin,
> and the backend AKS workload identity are Azure *resources*. They hold RBAC on
> school-tenant resources and must stay there. Relocating any of them breaks it.
>
> | Tenant | Holds | Cost |
> |--------|-------|------|
> | **School** (`uwindsor.ca`) | every Azure resource + all three UAMIs | $100 credit |
> | **Identity** (personal) | 2 app registrations, no resources, no subscription | **$0** |
>
> **No stored secret.** The client app carries a *federated credential* trusting GitHub
> OIDC, exactly like the UAMI does. GitHub mints one OIDC token and exchanges it with each
> tenant separately; `azure/login@v2` takes `allow-no-subscriptions: true` for the identity
> tenant. rev-5's "no stored Azure credential" invariant survives intact.
>
> **Cost of the split, stated plainly:** two tenants to reason about (every future auth bug
> starts with "which tenant?"), an aliased `azuread` provider, and a second one-time
> bootstrap seam. Accepted knowingly — the alternative was reverting rev-5's inbound auth to
> a shared secret.

The sentinel backend is registered as its own Entra app so callers can obtain
tokens **scoped to it** and the backend can validate them against Entra JWKS —
no shared static token (this is what deleted `sentinel-api-token`).

```hcl
# Every resource in this section targets the IDENTITY tenant, never the school
# tenant. The alias is what keeps that boundary explicit and reviewable.
provider "azuread" {
  alias     = "identity"
  tenant_id = var.identity_tenant_id
  # Auth is deliberately explicit — the default azuread provider would inherit
  # the ambient school-tenant context and fail here.
  #  · CI:    client_id = "8f7ff635-799b-4bdd-b1fa-2ff9bbe75560" (sentinel-tf-identity)
  #           + use_oidc = true — the provider exchanges the GitHub OIDC token
  #           itself; no second azure/login needed for Terraform.
  #  · Local: az CLI auth works because the school account is invited as a B2B
  #           GUEST with Application Administrator in the identity tenant
  #           (decision 2026-08-23) — az mints identity-tenant tokens for the
  #           same signed-in user.
}

# ── 1. The API definition: the audience, and the role callers must hold ───────
resource "azuread_application" "sentinel_backend" {
  provider        = azuread.identity
  display_name    = "sentinel-backend-api"
  # Tenant-qualified (live policy, 2026-08-23): new Entra tenants reject bare
  # api://name URIs — InvalidUniqueTenantIdentifierAsPerAppPolicy requires a
  # verified domain, the tenant id, or the app id in every identifier URI.
  # Downstream absorbs this by design: the audience travels as the
  # SENTINEL_API_AUDIENCE variable (task 4.1), never as a literal.
  identifier_uris = ["api://${var.identity_tenant_id}/sentinel-backend"]

  app_role {
    allowed_member_types = ["Application"]
    display_name         = "Incident.Write"
    description          = "Call the incident pipeline and write results"
    value                = "Incident.Write"
    id                   = "11111111-1111-1111-1111-111111111111" # stable GUID
    enabled              = true
  }
}

resource "azuread_service_principal" "sentinel_backend" {
  provider  = azuread.identity
  client_id = azuread_application.sentinel_backend.client_id
}

# ── 2. The caller ─────────────────────────────────────────────────────────────
# The `sentinel-gha` UAMI CANNOT be used here. It is a service principal in the
# SCHOOL tenant, and an app-role assignment is a directory operation *within a
# single tenant* — there is no cross-tenant form. So the caller is its own
# registration in the identity tenant, federated to the same GitHub repo.
#
# Still no stored secret: GitHub mints one OIDC token per job and exchanges it
# with each tenant independently. Two identities, one trust source.
resource "azuread_application" "sentinel_gha_client" {
  provider     = azuread.identity
  display_name = "sentinel-gha-client"
}

resource "azuread_service_principal" "sentinel_gha_client" {
  provider  = azuread.identity
  client_id = azuread_application.sentinel_gha_client.client_id
}

resource "azuread_application_federated_identity_credential" "gha_client_main" {
  provider       = azuread.identity
  application_id = azuread_application.sentinel_gha_client.id
  display_name   = "sentinel-main"
  audiences      = ["api://AzureADTokenExchange"]
  issuer         = "https://token.actions.githubusercontent.com"
  subject        = "repo:Keshav0375/Sentinel:ref:refs/heads/main"
}

# ── 3. Grant the caller the role ──────────────────────────────────────────────
resource "azuread_app_role_assignment" "gha_incident_write" {
  provider            = azuread.identity
  app_role_id         = "11111111-1111-1111-1111-111111111111"
  principal_object_id = azuread_service_principal.sentinel_gha_client.object_id
  resource_object_id  = azuread_service_principal.sentinel_backend.object_id
}
```

**Bootstrap seam (same shape as §4.3).** Terraform cannot create its own permission to
manage the identity tenant. One-time, by hand there: register `sentinel-tf-identity`, give
it a federated credential for `repo:Keshav0375/Sentinel-infra`, and assign it the
**Application Administrator** directory role — which you can do because you are Global Admin
of a tenant you own. Terraform then authenticates to the identity tenant as that app.
`identity_tenant_id` becomes a new root variable plus an `AZURE_IDENTITY_TENANT_ID` GitHub
variable, and `azuread ~> 3.0` returns to `required_providers` at this phase (task 3.5) —
it is deliberately absent in phases 1–2.

**What the backend validates** (FastAPI dependency, backend task 5.6): signature against
`https://login.microsoftonline.com/<IDENTITY-tenant>/discovery/v2.0/keys`, `iss` = the
**identity** tenant, `aud` = `api://sentinel-backend`, `exp` not passed, and the `roles`
claim contains `Incident.Write`. `/health` and `/ready` stay open (K8s probes can't carry
tokens).

> **The tenant in that URL is the identity tenant, not the one the pod runs in.** Token
> validation is pure signature + claims checking and is entirely independent of where the
> compute lives. Making the issuer explicit configuration rather than ambient tenancy is
> arguably the cleaner design — but it is also the single most likely thing to be
> misconfigured, so `SENTINEL_API_TENANT_ID` is a required setting with no default.

Tenant ID + audience are **public config, not secrets** — pushed to the sentinel repo as
GitHub *variables*.

### 4.5 One identity, many audience-scoped tokens

The `sentinel-gha` **UAMI** requests a **different token per destination**. A token stamped
for one audience is rejected by another — by design, limiting blast radius. There is no
single reusable token.

> **rev-9 caveat:** "one identity" is no longer strictly true. Everything in the school
> tenant uses the `sentinel-gha` UAMI; the backend API audience lives in the identity tenant
> and is reached as `sentinel-gha-client` (§4.4). Two identities, but still **one trust
> source** — the same GitHub OIDC token is exchanged with each tenant — and still no stored
> credential anywhere.

| GHA is talking to… | `--resource` / audience | How obtained |
|--------------------|-------------------------|--------------|
| Azure control plane (terraform, `az keyvault`, `az aks`) | `https://management.azure.com` | `azure/login` default |
| Terraform state blob | `https://storage.azure.com` | backend `use_azuread_auth` (§8.1) |
| Sentinel backend API | `api://<identity-tenant-id>/sentinel-backend` | **Different tenant, different identity** — a second `azure/login` as `sentinel-gha-client` against the identity tenant (§4.4), then `az account get-access-token --resource "api://<identity-tenant-id>/sentinel-backend"` |
| PostgreSQL | `https://ossrdbms-aad.database.windows.net` | `az account get-access-token --resource <that>` |

The backend pod does the same via **workload identity** (§3.7): one UAMI, two
audience-scoped tokens (Key Vault, PostgreSQL).

---

## 5. Cross-Repo Secret Distribution

> ⚠️ **Superseded (phase 5).** `github-repo-config.tf` was deleted — its shape assumed one estate with hardcoded `repository = "Sentinel"` literals. Distribution returns per-deployment in phase 6. This also removed the last thing B9 was blocking.

After `terraform apply`, the sentinel and sentinel-deployment repos need ACR
credentials and other values as GitHub Actions secrets. Terraform pushes these
automatically using the GitHub provider — no manual copy-paste.

### 5.1 GitHub provider config

```hcl
provider "github" {
  token = var.github_pat
  owner = var.github_owner # C8: variable, defaulted to "Keshav0375". Do NOT re-hardcode
}
```

### 5.2 What the infra apply pushes to the sentinel repo

> ⚠ **Corrected 2026-08-24 (decisions.md, phase-4 decision 2).** This section used to push all
> six values as `github_actions_secret`, contradicting §5.4, §7 and §9, which all treat the
> identity pointers as repo **variables**. Under OIDC there is no secret to protect — a client
> id is a public identifier and the trust decision is entirely the federated-credential
> subject. Masking them costs real debuggability: a failed `azure/login` prints
> `AADSTS700213 ... subject ***` instead of the string that actually mismatched.
>
> Two further corrections: the ACR values come from **`module.acr`**, not a root-level
> `azurerm_container_registry` (phase 2 made ACR a module); and the identity-tenant caller that
> §4.5 requires was pushed nowhere at all, so the backend repo could not reach it.

**Secrets — real credentials only:**

```hcl
resource "github_actions_secret" "sentinel_acr_login_server" {
  repository      = "Sentinel"
  secret_name     = "ACR_LOGIN_SERVER"
  plaintext_value = module.acr.acr_login_server
}

resource "github_actions_secret" "sentinel_acr_username" {
  repository      = "Sentinel"
  secret_name     = "ACR_USERNAME"
  plaintext_value = module.acr.acr_admin_username
}

resource "github_actions_secret" "sentinel_acr_password" {
  repository      = "Sentinel"
  secret_name     = "ACR_PASSWORD"
  plaintext_value = module.acr.acr_admin_password
}
```

**Variables — public identifiers:**

```hcl
resource "github_actions_variable" "sentinel_azure_client_id" {
  repository    = "Sentinel"
  variable_name = "AZURE_CLIENT_ID"
  value         = azurerm_user_assigned_identity.sentinel_gha.client_id
}

resource "github_actions_variable" "sentinel_azure_tenant_id" {
  repository    = "Sentinel"
  variable_name = "AZURE_TENANT_ID"
  value         = data.azurerm_client_config.current.tenant_id
}

resource "github_actions_variable" "sentinel_azure_subscription_id" {
  repository    = "Sentinel"
  variable_name = "AZURE_SUBSCRIPTION_ID"
  value         = data.azurerm_client_config.current.subscription_id
}

# --- the identity tenant (R4) -------------------------------------------------
# The backend workflows perform a SECOND azure/login as sentinel-gha-client, in
# the identity tenant with allow-no-subscriptions, to mint the backend-API token
# (SS4.5). Without these three the caller identity is unreachable from the
# Sentinel repo and that login cannot be written at all.

resource "github_actions_variable" "sentinel_identity_tenant_id" {
  repository    = "Sentinel"
  variable_name = "AZURE_IDENTITY_TENANT_ID"
  value         = var.identity_tenant_id
}

resource "github_actions_variable" "sentinel_gha_client_id" {
  repository    = "Sentinel"
  variable_name = "AZURE_GHA_CLIENT_ID"
  value         = azuread_application.sentinel_gha_client.client_id
}

# api://<identity-tenant-id>/sentinel-backend -- NOT the bare api://sentinel-backend
# that SS5.4 prose used to state. New Entra tenants reject the bare form with
# InvalidUniqueTenantIdentifierAsPerAppPolicy (found live 2026-08-23).
resource "github_actions_variable" "sentinel_api_audience" {
  repository    = "Sentinel"
  variable_name = "SENTINEL_API_AUDIENCE"
  value         = tolist(azuread_application.sentinel_backend.identifier_uris)[0]
}
```

### 5.3 What the infra apply pushes to the sentinel-deployment repo

Identity pointers only — the deployment repo builds no image and needs no ACR credential.

```hcl
resource "github_actions_variable" "deployment_azure_client_id" {
  repository    = "Sentinel-deployment"
  variable_name = "AZURE_CLIENT_ID"
  value         = azurerm_user_assigned_identity.sentinel_gha.client_id
}

resource "github_actions_variable" "deployment_azure_tenant_id" {
  repository    = "Sentinel-deployment"
  variable_name = "AZURE_TENANT_ID"
  value         = data.azurerm_client_config.current.tenant_id
}

resource "github_actions_variable" "deployment_azure_subscription_id" {
  repository    = "Sentinel-deployment"
  variable_name = "AZURE_SUBSCRIPTION_ID"
  value         = data.azurerm_client_config.current.subscription_id
}
```

### 5.4 What flows where

```
terraform apply
    │
    ├── Creates Azure resources (ACR, PostgreSQL, Key Vault, etc.)
    │
    ├── Pushes to sentinel repo GitHub secrets:
    │   ├── ACR_LOGIN_SERVER, ACR_USERNAME, ACR_PASSWORD
    │   ├── AZURE_CLIENT_ID, AZURE_TENANT_ID, AZURE_SUBSCRIPTION_ID
    │   └── (sentinel's GHA uses OIDC + these to access Key Vault at runtime)
    │
    ├── Pushes to sentinel-deployment repo GitHub secrets:
    │   ├── AZURE_CLIENT_ID, AZURE_TENANT_ID, AZURE_SUBSCRIPTION_ID
    │   └── (deployment's GHA uses OIDC + these for az webapp deploy)
    │
    └── Key Vault stores runtime secrets (API keys, DB password, etc.)
        └── fetched at runtime by ci_incident_response.yml via az keyvault secret show
```

**Three layers now:**
- **GitHub repo *variables*** (non-secret) = identity pointers — `AZURE_CLIENT_ID`,
  `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, and `SENTINEL_API_AUDIENCE`
  (`api://sentinel-backend`). These are just IDs; safe to expose.
- **GitHub repo secrets** = the few genuine bootstrap credentials — `ACR_*`,
  `GH_PAT`. No `AZURE_CLIENT_SECRET` (OIDC), no `DB_PASSWORD` (Entra DB auth),
  no `sentinel-api-token` (Entra bearer).
- **Key Vault secrets** = runtime values — LLM API keys (rotated), Datadog keys,
  Teams webhook, LangFuse keys. **No DB password** (Entra token auth).

Terraform also pushes `SENTINEL_API_AUDIENCE` + `AZURE_TENANT_ID` as variables to
the sentinel repo so `ci_incident_response.yml` can request the backend token and
the backend can validate `aud`/`iss`. GitHub identity pointers are set once and
rarely change; Key Vault secrets update independently via `az keyvault secret set`
(or the rotation Function) without re-running Terraform.

---

## 6. CI Runner Images

The sentinel repo's CI workflows need specific tools. Instead of installing them
every run (slow), we build a custom runner image and store it in ACR.

### 6.1 ci-runner.Dockerfile

```dockerfile
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl gcc libpq-dev git docker.io && rm -rf /var/lib/apt/lists/*

# Dev tools
RUN pip install --no-cache-dir \
    ruff pyright pytest pytest-asyncio \
    asyncpg pgvector alembic

# Azure CLI (for Key Vault access + ACR login)
RUN curl -sL https://aka.ms/InstallAzureCLIDeb | bash
```

### 6.2 Bootstrap: first build is manual

The `ci_runners.yml` workflow needs ACR credentials — but those come from
Terraform, which needs ACR to exist first. Sequence:

1. `terraform apply` creates ACR
2. **Manually** build and push the first `ci-runner` image:
   ```bash
   az acr login --name sentinelacr0375
   docker build -f ci-images/ci-runner.Dockerfile -t sentinelacr0375.azurecr.io/ci-runner:latest .
   docker push sentinelacr0375.azurecr.io/ci-runner:latest
   ```
3. After that, `ci_runners.yml` handles all subsequent updates automatically

### 6.3 `ci_runners.yml` — Build runner images on change

**Name:** `[infra] runners — build and push`

Triggers when `ci-images/` changes on main:

```yaml
name: "[infra] runners — build and push"

on:
  push:
    branches: [main]
    paths: ['ci-images/**']

permissions:
  id-token: write
  contents: read

jobs:
  build-and-push:
    name: Build and Push Runner Image
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: azure/login@v2
        with:
          client-id: ${{ vars.AZURE_CLIENT_ID }}
          tenant-id: ${{ vars.AZURE_TENANT_ID }}
          subscription-id: ${{ vars.AZURE_SUBSCRIPTION_ID }}

      - run: az acr login --name sentinelacr0375

      - run: |
          docker build -f ci-images/ci-runner.Dockerfile \
            -t sentinelacr0375.azurecr.io/ci-runner:latest .
          docker push sentinelacr0375.azurecr.io/ci-runner:latest
```

### 6.4 Usage in sentinel repo workflows

```yaml
# In sentinel repo's ci_validation.yml / ci_backend_deployment.yml:
jobs:
  quality:
    runs-on: ubuntu-latest
    container:
      image: ${{ secrets.ACR_LOGIN_SERVER }}/ci-runner:latest
      credentials:
        username: ${{ secrets.ACR_USERNAME }}
        password: ${{ secrets.ACR_PASSWORD }}
```

---

## 7. CI/CD Workflows

### Naming Convention

Follows the cross-repo standard (defined in architecture/backend.md §9):

| File | Name | Purpose |
|------|------|---------|
| `ci_infra_dry.yml` | `[infra] terraform — validate and plan` | Dry run on push/PR |
| `ci_infra.yml` | `[infra] terraform — apply` | Apply on merge to main |
| _(none)_ | — | Full teardown is a **local Owner-run procedure**, not a workflow (R6, §7.3) |
| `ci_runners.yml` | `[infra] runners — build and push` | Build + push CI runner images |

Job IDs: `kebab-case` verb-noun. Job names: Title case.

### 7.1 `ci_infra_dry.yml` — Dry run on push/PR

**Name:** `[infra] terraform — validate and plan`

Validates Terraform config and runs `plan` — never applies. Runs on every push
and PR to catch syntax errors, missing variables, and drift early.

```yaml
name: "[infra] terraform — validate and plan (dry run)"

on:
  push:
    branches: ['**']
  pull_request:
    branches: [main]

permissions:
  id-token: write
  contents: read
  pull-requests: write

jobs:
  run-validate:
    name: Run Validate
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: hashicorp/setup-terraform@v3

      - uses: azure/login@v2
        with:
          client-id: ${{ vars.AZURE_CLIENT_ID }}
          tenant-id: ${{ vars.AZURE_TENANT_ID }}
          subscription-id: ${{ vars.AZURE_SUBSCRIPTION_ID }}

      - name: Terraform Init
        run: terraform init

      - name: Terraform Validate
        run: terraform validate

      - name: Terraform Format Check
        run: terraform fmt -check -recursive

  run-plan:
    name: Run Plan
    needs: run-validate
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: hashicorp/setup-terraform@v3

      - uses: azure/login@v2
        with:
          client-id: ${{ vars.AZURE_CLIENT_ID }}
          tenant-id: ${{ vars.AZURE_TENANT_ID }}
          subscription-id: ${{ vars.AZURE_SUBSCRIPTION_ID }}

      - name: Terraform Init
        run: terraform init

      - name: Terraform Plan
        id: plan
        run: terraform plan -var="github_pat=${{ secrets.GH_PAT }}" -var="location=${{ vars.AZURE_LOCATION }}" -var="subscription_id=${{ vars.AZURE_SUBSCRIPTION_ID }}" -var="postgres_entra_admin_object_id=${{ vars.PG_ADMIN_OBJECT_ID }}" -var="postgres_entra_admin_principal_name=${{ vars.PG_ADMIN_PRINCIPAL_NAME }}" -var="kv_admin_object_id=${{ vars.KV_ADMIN_OBJECT_ID }}" -no-color -out=tfplan

      - name: Post Plan to PR
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v7
        with:
          script: |
            const plan = `${{ steps.plan.outputs.stdout }}`;
            const truncated = plan.length > 60000 ? plan.substring(0, 60000) + '\n... (truncated)' : plan;
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: `## Terraform Plan\n\`\`\`\n${truncated}\n\`\`\``
            });
```

### 7.2 `ci_infra.yml` — Apply on merge to main

**Name:** `[infra] terraform — apply`

Only runs on merge to main. Applies the plan. Uses GitHub environment
protection rules for an extra approval gate if desired.

```yaml
name: "[infra] terraform — apply"

on:
  push:
    branches: [main]

permissions:
  id-token: write
  contents: read

jobs:
  run-apply:
    name: Run Apply
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v4
      - uses: hashicorp/setup-terraform@v3

      - uses: azure/login@v2
        with:
          client-id: ${{ vars.AZURE_CLIENT_ID }}
          tenant-id: ${{ vars.AZURE_TENANT_ID }}
          subscription-id: ${{ vars.AZURE_SUBSCRIPTION_ID }}

      - name: Terraform Init
        run: terraform init

      - name: Terraform Apply
        run: terraform apply -auto-approve -var="github_pat=${{ secrets.GH_PAT }}" -var="location=${{ vars.AZURE_LOCATION }}" -var="subscription_id=${{ vars.AZURE_SUBSCRIPTION_ID }}" -var="postgres_entra_admin_object_id=${{ vars.PG_ADMIN_OBJECT_ID }}" -var="postgres_entra_admin_principal_name=${{ vars.PG_ADMIN_PRINCIPAL_NAME }}" -var="kv_admin_object_id=${{ vars.KV_ADMIN_OBJECT_ID }}"
```

### 7.3 Full teardown — **local, Owner-run. Not a workflow.** (R6, 2026-08-16)

> **This was a `ci_destroy_infra.yml` workflow until R6.** It cannot be one, for a reason
> that is not about policy: a soft-deleted Key Vault lives at **subscription scope**
> (`/subscriptions/{sub}/providers/Microsoft.KeyVault/locations/{loc}/deletedVaults/{name}`),
> and the `sentinel-gha` identity holds nothing at subscription scope — every one of its five
> grants is scoped to `sentinel-rg`, `sentinel-state-rg`, or the state storage account.
>
> From CI the sequence fails silently and then fatally: `terraform destroy` soft-deletes the
> vault → `az keyvault purge` returns **403**, swallowed by `|| true` → the globally unique
> name stays reserved for 7 days → the next `terraform apply` fails, because the azurerm
> provider's `recover_soft_deleted_key_vaults` default *also* reads deleted vaults at
> subscription scope.
>
> The alternatives were a subscription-scope `Key Vault Contributor` grant (lets CI manage
> **any** vault in the subscription — too wide for credentials reachable from
> `pull_request`-triggered workflows on a public repo) or a custom purge-only role. **Owner-run
> teardown was chosen instead:** "destroy everything, always" is the most destructive operation
> in the project, and requiring a human with Owner rights is a feature, not a limitation. It
> also removes a standing privilege rather than adding one.

Run locally, signed in as an Owner of the subscription:

```bash
# 0. Confirm you are in the SCHOOL tenant — az keeps one shared context (§4.3).
az account set --subscription 174e25ca-ab82-4671-a913-9c2f66e5924d

# 1. Destroy everything Terraform manages, including the imported UAMI and its
#    federated credentials. Acquire the token first so the destroy survives
#    deleting the identity it authenticated with.
terraform destroy -auto-approve   -var="github_pat=$GH_PAT" -var="location=canadacentral"   -var="subscription_id=$SUB_ID"   -var="postgres_entra_admin_object_id=$PG_ADMIN_OBJECT_ID"   -var="postgres_entra_admin_principal_name=$PG_ADMIN_UPN"   -var="kv_admin_object_id=$KV_ADMIN_OBJECT_ID"

# 2. Purge the soft-deleted vault. REQUIRES OWNER — this is the step CI cannot do.
#    Without it the name is held for 7 days (§3.3) and the rebuild fails.
az keyvault purge --name sentinel-kv-0375 --location canadacentral

# 3. Delete the resource groups Terraform does not own (C1).
az group delete --name sentinel-rg        --yes --no-wait
az group delete --name sentinel-func-rg   --yes --no-wait
az group delete --name sentinel-state-rg  --yes --no-wait

# 4. Verify nothing is stranded before re-bootstrapping.
az keyvault list-deleted --query "[?name=='sentinel-kv-0375']" -o tsv   # → empty
```

Then re-bootstrap from §10 step 1. **Do not skip step 2** — it is the only step whose
omission fails *later*, during the next apply, rather than immediately.

> **Unverified:** whether PostgreSQL Flexible Server reserves `sentinel-pg-0375` during its
> dropped-server restore window. ACR has no soft-delete and re-applies cleanly. If the
> Postgres name turns out to be held, the same suffix-bump remedy applies (§3 naming).

---

## 8. Terraform State

> ⚠️ **Superseded (phase 5).** State lives in `rg-sentinel-bootstrap` / `stsentineltf<uid6>`, and workspaces separate the layers. Note the azurerm backend stores a workspace at `<key>env:<workspace>` — appending, not nesting. `env:/platform/...` is the **S3** backend's layout and reads a blob that does not exist.

### 8.1 Remote State (Azure Storage)

```hcl
terraform {
  backend "azurerm" {
    resource_group_name  = "sentinel-state-rg"
    storage_account_name = "sentineltfstate0375"
    container_name       = "tfstate"
    key                  = "sentinel.terraform.tfstate"

    # Entra auth, not a storage access key. Combined with the Storage Blob Data
    # Contributor assignment in §4.2, this is what lets CI reach state at all —
    # the state account sits outside the Contributor scope on sentinel-rg.
    use_azuread_auth = true
    use_oidc         = true
  }
}
```

`subscription_id`, `tenant_id` and `client_id` are **not** written in the backend block —
they arrive as `ARM_SUBSCRIPTION_ID` / `ARM_TENANT_ID` / `ARM_CLIENT_ID` / `ARM_USE_OIDC`
env vars from the workflow, so the same `backend.tf` works locally (`az login`) and in CI
(federated token). A backend block cannot interpolate variables — this is the standard
way around that.

The state storage account is created manually (one-time bootstrap), in its **own**
resource group so that `terraform destroy` / `az group delete` on `sentinel-rg` (§7.3)
cannot destroy the state that describes it:
```bash
az group create --name sentinel-state-rg --location canadacentral
az storage account create --name sentineltfstate0375 --resource-group sentinel-state-rg \
  --sku Standard_LRS --encryption-services blob
az storage container create --name tfstate --account-name sentineltfstate0375 --auth-mode login
```

> **`sentineltfstate0375` is a globally unique name across all of Azure.** If it is taken,
> change it in `backend.tf`, `scripts/bootstrap-state.sh`, `docs/BOOTSTRAP.md`, the
> §4.2 `gha_state_blob` scope, and this section — together, in one commit.

### 8.2 State Locking

Azure Storage provides native state locking via blob leases. No DynamoDB needed.

---

## 9. Required GitHub Variables & Secrets (sentinel-infra repo)

> ⚠️ **Superseded (phase 5).** Most of these variables moved into `azure/config/deployment-config.yaml`. `AZURE_CLIENT_ID` became `AZURE_CLIENT_ID_PLAN` / `_DEPLOY` / `_OPS`.

> **Read these as `${{ vars.X }}` or `${{ secrets.X }}` exactly as classified below.**
> The split is real, not cosmetic: a value in the *variables* table is readable in logs
> and forks by design. Every workflow in §7 must match this table — mixing them up is
> how `vars.AZURE_CLIENT_ID` silently evaluates to empty string and `azure/login` fails
> with an unhelpful error.

**GitHub *variables* (`vars.` — non-secret identifiers):**

| Variable | Description | How Set |
|----------|-------------|---------|
| `AZURE_CLIENT_ID` | The `sentinel-gha` **UAMI's `clientId`** (not its principal/object ID) | Manual (from bootstrap §4.3) |
| `AZURE_TENANT_ID` | Entra tenant ID — `12f933b3-3d61-4b19-9a4d-689021de8cc9` (uwindsor.ca) | Manual |
| `AZURE_SUBSCRIPTION_ID` | Azure subscription ID | Manual |
| `AZURE_LOCATION` | Azure region — `canadacentral` (R3, resolved 2026-08-15) | Manual |
| `PG_ADMIN_OBJECT_ID` | Object ID of the PostgreSQL Entra admin **principal** (§3.2) | Manual (`az ad signed-in-user show --query id`) |
| `PG_ADMIN_PRINCIPAL_NAME` | That principal's UPN, e.g. `you@uwindsor.ca` | Manual |
| `AZURE_IDENTITY_TENANT_ID` | The personal **identity** tenant (R4) — `eae0d3c6-af22-4b70-ad3b-12d625a06139`. Consumed by the aliased `azuread` provider from task 3.5 on | Manual |
| `AZURE_IDENTITY_CLIENT_ID` | `sentinel-tf-identity`'s clientId — `8f7ff635-799b-4bdd-b1fa-2ff9bbe75560`. CI passes it as `-var identity_client_id` together with `-var identity_use_oidc=true`; locally both stay at defaults and the guest CLI login is used | Manual |
| `KV_ADMIN_OBJECT_ID` | Object ID of the human who seeds Key Vault secrets (§10 step 7). **Required, no default** — deliberately NOT `data.azurerm_client_config.current.object_id`, which resolves to the CI identity when CI applies and would destroy the human's Officer rights | Manual |

**GitHub *secrets* (`secrets.` — genuine credentials):**

| Secret | Description | How Set |
|--------|-------------|---------|
| `GH_PAT` | GitHub PAT with `repo` scope | Manual (for `github_actions_secret` provider + Function bridge) |

> **Why `GH_PAT` and not `GITHUB_PAT`.** GitHub **rejects** any Actions secret or variable
> whose name begins with `GITHUB_` — the prefix is reserved. The earlier name was
> unusable; this is a correction, not a preference (conflict C6, 2026-08-15).

**Why `AZURE_LOCATION` exists at all.** `var.location` deliberately has **no default**
(R3 — a silently defaulted region is a resource-graph-wide mistake), and
`terraform.tfvars` is gitignored, so CI has no other way to supply it. Every §7 workflow
therefore passes `-var="location=${{ vars.AZURE_LOCATION }}"` on plan / apply / destroy,
alongside the other required inputs. One mechanism for all five variables — no mix of
`-var` flags and `TF_VAR_*` env (conflict C5, 2026-08-15).

**No `AZURE_CLIENT_SECRET`** — OIDC eliminates it.
**No `DB_PASSWORD`** — PostgreSQL is Entra-only (§3.2); clients present a token.
**No `sentinel-api-token`** — the backend API uses Entra bearer tokens (§4.4, ⛔ R4).
**No `PG_ADMIN_GROUP_OBJECT_ID`** — the `sentinel-db-admins` group was removed in rev-9;
the Postgres Entra admin is now a principal set directly (§3.2).

---

## 10. Prerequisites & Setup Checklist

> ⚠️ **Superseded (phase 5).** The current runbook is `Sentinel-infra/docs/BOOTSTRAP.md`. Order is now: state → identities → GitHub config → identity-tenant credentials → platform → runner image → deployment → secrets.

### One-time Bootstrap (manual — run once, in order)

> **Run every `az` command in PowerShell.** Git Bash rewrites `/subscriptions/...` scope
> arguments into Windows paths (§4.3). Region is `canadacentral` throughout (R3).

> **⚠ Both bootstrap scripts assert the expected subscription ID before doing anything**
> (`EXPECTED_SUB`, overridable). Since R4, Sentinel spans **two tenants**, and `az` keeps a
> single shared context in `~/.azure` — an `az login` to the identity tenant in *any* other
> terminal silently repoints every other session. This happened during infra 1.3, and the
> assertion is what stopped `sentinel-gha` being created in the wrong tenant. The subscription
> ID is a non-secret identifier (§9 classifies it as a GitHub *variable*), so hardcoding the
> default is deliberate, not a leak.

1. [ ] Create the resource group **and register the resource providers**. A fresh
   subscription has nearly every provider `NotRegistered`; the first `apply` then fails
   with a "subscription is not registered to use namespace" error that reads like a
   Terraform bug. Registration is idempotent and takes a minute or two.
   ```bash
   az group create --name sentinel-rg --location canadacentral
   # Y1 (Consumption) and F1 (Dedicated) Linux plans cannot share a resource
   # group — the Functions webspace gets its own (2026-08-23):
   az group create --name sentinel-func-rg --location canadacentral

   for ns in Microsoft.Compute Microsoft.ContainerService Microsoft.ContainerRegistry \
             Microsoft.DBforPostgreSQL Microsoft.KeyVault Microsoft.EventGrid \
             Microsoft.Web Microsoft.Storage Microsoft.ManagedIdentity \
             Microsoft.OperationalInsights; do
     az provider register --namespace "$ns"
   done
   az provider show --namespace Microsoft.Compute --query registrationState -o tsv  # → Registered
   ```

2. [ ] Create state storage (§8.1) — note its **own** resource group:
   ```bash
   az group create --name sentinel-state-rg --location canadacentral
   az storage account create --name sentineltfstate0375 --resource-group sentinel-state-rg \
     --sku Standard_LRS --encryption-services blob
   az storage container create --name tfstate --account-name sentineltfstate0375 --auth-mode login

   # Control plane ≠ data plane: Owner does NOT grant blob access. Without this,
   # `terraform init` fails with a 403 that reads like a bug.
   SA_ID=$(az storage account show -n sentineltfstate0375 -g sentinel-state-rg --query id -o tsv)
   az role assignment create \
     --assignee-object-id $(az ad signed-in-user show --query id -o tsv) \
     --assignee-principal-type User \
     --role "Storage Blob Data Contributor" --scope $SA_ID
   ```

3. [ ] Create the `sentinel-gha` UAMI, both role assignments, and the two
   `Sentinel-infra` federated credentials (§4.3), then **import all five** (§4.3.1).

4. [ ] Record the PostgreSQL Entra admin principal (§3.2). rev-9 removed the
   `sentinel-db-admins` group — you are the admin directly, and the backend UAMI is
   added as a second admin once Terraform creates it:
   ```bash
   az ad signed-in-user show --query "{id:id, upn:userPrincipalName}" -o json
   ```
   `az ad signed-in-user show` needs only the delegated `User.Read` scope that every
   account holds, so it works even where directory writes are denied.

5. [ ] Add GitHub *variables* + the `GH_PAT` secret to sentinel-infra (§9) — incl.
   `AZURE_LOCATION`, `PG_ADMIN_OBJECT_ID`, `PG_ADMIN_PRINCIPAL_NAME`. **No**
   `DB_PASSWORD`, **no** `GITHUB_PAT` (reserved prefix — see §9).

6. [ ] First `terraform apply` (local or via GHA):
   ```bash
   terraform init
   terraform apply -var="github_pat=<your-pat>" \
     -var="location=canadacentral" \
     -var="subscription_id=<sub-id>" \
     -var="postgres_entra_admin_object_id=<your object id>" \
     -var="postgres_entra_admin_principal_name=<your UPN>"
   ```
   Then add the backend UAMI as a second Postgres Entra admin (§3.2).

7. [ ] Populate Key Vault with runtime secrets (no `db-password`, no
   `sentinel-api-token` — both eliminated):
   ```bash
   az keyvault secret set --vault-name sentinel-kv-0375 --name anthropic-api-key --value "sk-ant-..." --expires "$(date -u -d '+90 days' +%Y-%m-%dT%H:%M:%SZ)"
   az keyvault secret set --vault-name sentinel-kv-0375 --name openai-api-key --value "sk-..." --expires "$(date -u -d '+90 days' +%Y-%m-%dT%H:%M:%SZ)"
   az keyvault secret set --vault-name sentinel-kv-0375 --name dd-api-key --value "..."
   az keyvault secret set --vault-name sentinel-kv-0375 --name dd-app-key --value "..."
   az keyvault secret set --vault-name sentinel-kv-0375 --name teams-webhook-url --value "https://..."
   az keyvault secret set --vault-name sentinel-kv-0375 --name langfuse-secret-key --value "sk-lf-..."
   az keyvault secret set --vault-name sentinel-kv-0375 --name langfuse-public-key --value "pk-lf-..."
   ```

8. [ ] Create Entra DB roles: connect to PostgreSQL as an Entra admin (§3.2) (token as
   password) and map the SP + backend UAMI to DB roles with grants:
   ```sql
   SELECT * FROM pgaadauth_create_principal('sentinel-gha', false, false);
   SELECT * FROM pgaadauth_create_principal('sentinel-backend-wi', false, false);
   -- then GRANT the needed privileges on the sentinel DB to each role
   ```

9. [ ] Build and push first CI runner image manually (§6.2)

10. [ ] Verify AKS + workload identity: `az aks get-credentials --resource-group sentinel-rg --name sentinel-aks && kubectl get nodes`
    (Terraform already enabled `oidc_issuer_enabled` + `workload_identity_enabled`.)

11. [ ] Run `alembic upgrade head` against PostgreSQL (Entra token auth) to create tables

### After bootstrap — ongoing

- Push to main on sentinel-infra → `ci_infra.yml` runs `terraform apply`
- Change `ci-images/` → `ci_runners.yml` rebuilds runner image
- Terraform auto-distributes secrets to sentinel + sentinel-deployment repos
- Runtime secrets updated via `az keyvault secret set` (no Terraform needed)

---

## 11. Cost Breakdown

| Resource | Monthly Cost | Covered By |
|----------|-------------|------------|
| AKS control plane | Free | Always free (Free tier) |
| AKS node (1× B2pls_v2, ARM64) | ~$1–3/mo | `az aks stop`/`start` — bills only while started, ~20–80 h/mo. The free B2ats_v2 grant is unusable for AKS (SystemPoolSkuTooLow, 2026-08-23) |
| LoadBalancer public IP | ~$0 | Released at teardown (Service deleted per run, URL resolved fresh by backend-up); bills only while scaled up |
| PostgreSQL B1MS | Free | 12-month free |
| ACR Standard | Free | 12-month free (100 GB) |
| Key Vault | Free | Always free |
| Event Grid | Free | Always free (100K ops) — custom topic + KV system topic |
| Azure Functions | Free | Always free (1M reqs) — bridge + rotator share the Y1 plan |
| App Service F1 | Free | Always free |
| Storage (TF state) | ~$0.01 | Negligible |
| **Total** | **~$0/month at idle** | **12 months** |

Backend compute = the free AKS node, scaled to zero between runs (sentinel repo
workflows manage node_count — Terraform ignores drift on it). After 05/2027 the node
bills only for scaled-up hours — `terraform destroy` when the project wraps.
