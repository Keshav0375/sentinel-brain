# task-1 — `dd-report` composite action   ·   [deployment / phase-2-deploy-pipeline]

| Field | Value |
|-------|-------|
| **Status** | `verified` |
| **Repo** | `Sentinel-deployment` |
| **Phase branch** | `dev/deploy-phase-2-deploy-pipeline` |
| **Commit prefix** | `feat:` |
| **Arch refs** | architecture/deployment.md §3.2 |
| **Depends on** | — |
| **Referenced by** | [[task-2-ci-app-deployment]] (every reporting stage) |

## Spec
Local composite action so every pipeline stage calls one Datadog reporter instead of
copy-pasted curl blocks.

**Files created:** `.github/actions/dd-report/action.yml`
- Inputs: `title`, `text`, `tags` (comma list), `alert-type` (`info|error`), optional `log-payload`, `dd-api-key`, `dd-site` (**required**, no default: the org is on US5 `us5.datadoghq.com`, and a wrong default fails as a silent 403).
- Steps: `send_dd_event` → POST `https://api.${DD_SITE}/api/v1/events`; if `log-payload` set, `send_dd_log` → POST `https://http-intake.logs.${DD_SITE}/api/v2/logs` (§3.2 helper bodies).
- Mask the API key; fail soft (report failures shouldn't break the deploy record).

## Prerequisites
- [ ] actionlint. [ ] ⛔ B6 (Datadog key) only for live verify.

## Acceptance Criteria
- [ ] `action.yml` validates under actionlint; inputs match §3.2; key masked.
- [ ] Event + log paths both implemented; `dd-site` configurable.

## Tests
- **Lint:** actionlint, yamllint.
- **Integration (⛔ B6):** call the action with a real key → event appears in Datadog Events Explorer.
- **Quality gate:** `--repo deployment`.

## How to Verify (phase gate)
_Gate: VERDICT GREEN, 4 ran (ruff-lint, yamllint, gitleaks, pytest); actionlint n/a until task 2.2 adds .github/workflows. 12 tests against a stub curl. Action hand-checked from a scratch workflow._
1. actionlint clean.
2. (with DD key) a workflow step using the action posts a visible test event/log to Datadog.

## Report
Built `dd-report` composite action. Commit `05d35ce` (Sentinel-deployment, feat: add dd-report composite action for Datadog events and logs).
Files: `.github/actions/dd-report/action.yml`, `.github/actions/dd-report/dd-report.sh`, `.yamllint.yaml`, `tests/test_dd_report.py`.
Key goes to curl via a 0600 header file (never in argv/output); JSON built with jq; `dd-site` required (US5), URLs built from it; `event-id` prefers id_str; fails soft with warnings. First commit d144d9b failed gitleaks on a fake key literal; amended to 05d35ce.

## BLOCKED
_Live verify ⛔ B6. YAML + lint now._
