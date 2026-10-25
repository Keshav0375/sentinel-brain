# Sentinel Ops Dashboard — Architecture (binding)

> Lives in the `Keshav0375/Sentinel` repo (the future single Sentinel monorepo). It is public on
> GitHub Pages, so a visitor (team or recruiter) sees every build, incident, agent run and revert PR
> in one place. Decision: `decisions.md` 2026-10-25 "Ops dashboard". Built as backend phase 10.

## 1. Goals

1. **One place** for app builds and deploys, incidents and agent runs, revert PRs and their reviews,
   backend CI/CD, and eval scores, all correlated into end-to-end chains.
2. **Never lose anything.** Every occurrence is counted forever, survives estate teardown and
   backend scale-to-zero, and self-heals missed events.
3. **Progressive detail.** The overview leads into chains, then stages, then traces, using toggles
   and expanders. Nothing is hidden behind a dead end.
4. **Always up and free.** A static site with no server, so it is up whether or not Azure is.

Non-goals: no write actions from the UI (HITL: the dashboard only observes; merging stays in
GitHub). No auth (the site is public by design), so nothing secret or raw goes in (§5).

## 2. Shape

```
 producers (GHA only)                      durable store                      presentation
 ─────────────────────                     ─────────────                      ────────────
 Sentinel workflows ──append event──────▶  ops-ledger branch  ──reconciler──▶ snapshot/*.json ─▶ React SPA
   (incident, deploy, PR gate, scale,       (append-only, one                  (derived, rebuilt)     on GitHub Pages
    eval)  via .github/actions/ops-event     JSON file per event)
 Sentinel-deployment runs/PRs/reviews ──pulled (read-only API) by reconciler──▲
 LangFuse traces (names/timings only) ──pulled by reconciler──────────────────┘
```

- **Store:** orphan branch `ops-ledger` in `Keshav0375/Sentinel`. It is append-only: one file per
  event at `events/YYYY/MM/DD/<iso-ts>-<kind>-<event_id>.json`. Files are never edited or deleted,
  and git history is the audit log. Writing one file per event makes concurrent writers
  conflict-free; a push that races does `git pull --rebase` and retries (bounded).
- **Why not Postgres:** Azure Postgres is destroyed with the estate. An external DB adds a vendor,
  a secret, and an API that a static site would need. A git ledger is durable, free, versioned and
  public-readable. A database can be added later as a *derived* index; the ledger stays the source
  of truth.
- **Snapshot:** the reconciler compacts the ledger into `snapshot/` (`chains.json`, `entities/*.json`,
  `metrics.json`, `meta.json` with `generated_at` + ledger head sha). The site reads only snapshots.

## 3. Event model (schema v1)

Every event has the same envelope:

| field | type | notes |
|---|---|---|
| `schema` | `"ops.v1"` | bumped on breaking change; the reconciler reads all versions |
| `event_id` | hex sha256 | **deterministic**: `sha256(kind + source + source_id + state)`, so a replay is a no-op |
| `kind` | enum | see below |
| `ts` | RFC 3339 UTC | when it happened (source time, not write time) |
| `recorded_at` | RFC 3339 UTC | write time |
| `source` | enum | `gha:<repo>/<workflow>`, `reconciler`, `langfuse` |
| `chain` | object | correlation keys: `correlation_id?`, `sha?` (7–40 hex), `pr?`, `run_id?`, `incident_id?`, `scenario?` |
| `data` | object | kind-specific, **allow-listed fields only** (§5) |

Kinds:
- `build.started|succeeded|failed`, `deploy.started|succeeded|failed` (with `failed_stage`, `version`,
  `duration_s`, `run_url`), covering the Sentinel-deployment app and the Sentinel backend
- `ci.pr_gate.completed`, `scale.changed`
- `alert.received` (signal_type, severity, service)
- `agent.started`, `agent.decided` (resolution_type, confidence, root_cause_summary ≤500 chars,
  tool_calls, reflexion_loops, mttr_s, models_used, langfuse_trace_url), `agent.failed`
- `revert_pr.opened|review_submitted|merged|closed` (state, reviewer, review_state, waited_s, url)
- `escalation.raised`
- `eval.scored` (per scenario run: the four checks + judge dims, 0–1, judge_conflict/failed flags)
- `trace.summarized` (span tree: name, kind, start, duration, status, token counts; no I/O)

Chains are correlated by `correlation_id`, then `sha`, then `pr`. A chain is
`deploy → alert → agent → (revert_pr → review → merge | escalation)`.

## 4. Keeping it complete ("never lose things")

1. **Event-time writes.** Every Sentinel workflow step that changes state calls the composite action
   `.github/actions/ops-event`. It validates the envelope, enforces the allow-list, and appends with
   retry. It is non-blocking: a ledger failure warns, never fails the business job.
2. **Reconciler** `.github/workflows/ops_reconcile.yml`:
   - Triggers: `schedule` every 30 min, `workflow_run` on every Sentinel workflow, and
     `workflow_dispatch`.
   - It pulls Sentinel and Sentinel-deployment workflow runs, PRs, reviews and merges through the
     GitHub API (read-only; public repos), plus LangFuse trace summaries (read-only keys).
   - It derives the events that should exist and appends any that are missing. Deterministic ids
     make this idempotent.
   - Then it rebuilds `snapshot/`, builds the SPA, and deploys to Pages.
   - A cursor (`meta/cursor.json`) bounds API paging, and a weekly full sweep re-checks everything.
3. **Concurrency:** `concurrency: ops-ledger` with cancel-in-progress **false**, separate from
   `sentinel-backend`. Ledger writers are append-only and safe in parallel.
4. **Counts are derived** from the ledger (never stored counters), so "how many times" is always
   exact.

## 5. Data rules (public site)

- Allow-list per kind (§3). The schema forbids everything else; `ops-event` drops unknown fields
  and fails closed on any value that looks like a secret.
- **No raw logs or tool output** (R14). Agent text is the LLM-written summary only, capped at
  500 chars. Traces are span names, timings and status only. No secrets, tokens, PATs, keys, IPs or
  connection strings. gitleaks runs on the ledger branch in the reconciler.
- Links out to GitHub runs and PRs, the LangFuse trace and the Datadog monitor are allowed.
  Viewers may lack access to LangFuse and Datadog; the UI says so.

## 6. Frontend

- **Stack:** React 18 + TypeScript + Vite, Tailwind CSS with CSS-variable design tokens, Radix UI
  primitives (accessible dialogs, toggles, tabs, tooltips), TanStack Table + Virtual, Recharts, and
  date-fns. No backend. It fetches `snapshot/*.json`. pnpm with a lockfile.
- **Location:** `dashboard-web/` in Sentinel (the existing FastAPI `dashboard/` page is untouched).
- **Theme:** light, dark and system, with a toggle persisted per viewer. WCAG AA contrast in both
  themes. Color is never the only status signal (icon + label too).
- **Information architecture (progressive disclosure):**
  1. **Overview:** KPI cards (deploys, failure rate, incidents, MTTR p50/p90, revert PRs awaiting
     review, escalations, eval score) over a time-range picker. Each card filters below.
  2. **Needs action lane:** revert PRs awaiting review (oldest first, with a waited-for timer),
     escalations, and failed builds with no incident.
  3. **Timeline of chains:** one row per chain, with stage pills (deploy → alert → agent → PR →
     review → merge) and status, timestamps and duration. Expand a row for per-stage details.
  4. **Chain drawer:** full event list, agent decision (confidence meter, root-cause summary,
     tool-call and reflexion counts), trace waterfall (from `trace.summarized`), eval scores, and
     links.
  5. **Detail toggles:** "show raw event JSON", "show traces" and "show eval" switches. Choices
     persist in the URL so views are shareable.
  6. **Filters:** repo, kind, status, scenario (catalog of 30 branches), and full-text search on
     summary and SHA.
- **States:** skeleton loading, empty (explains what will appear), error (with snapshot age), and a
  staleness banner when `generated_at` is over 1 h old.
- **Quality:** keyboard navigable, responsive to 360 px, `prefers-reduced-motion` honoured,
  Lighthouse ≥ 90 on performance and accessibility. Vitest + Testing Library for components,
  Playwright smoke on the built site (both themes).

## 7. Files (in `Keshav0375/Sentinel`)

- `dashboard-web/` (SPA), `scripts/ops/` (ledger lib, `reconcile.py`, `snapshot.py`; stdlib +
  `httpx`), `tests/test_ops/`
- `.github/actions/ops-event/action.yml`, `.github/workflows/ops_reconcile.yml`,
  `.github/workflows/ops_pages.yml` (or one workflow), and the `ops-event` calls added to the
  existing workflows
- Pages: GitHub Pages from Actions, URL `https://keshav0375.github.io/Sentinel/`

## 8. Security and permissions

- The ledger writers use the job's `GITHUB_TOKEN` with `contents: write`, and write **only** to
  `ops-ledger`. `main` and `release-phase-2` stay ruleset-protected (PR required), so the token
  cannot push there.
- The reconciler uses `GITHUB_TOKEN` (read) for both public repos, plus LangFuse read keys from Key
  Vault through the existing login. Pages deploy uses `pages: write` and `id-token: write`
  (Pages OIDC).
- Every third-party action is pinned by SHA (dec 2026-10-24). Untrusted text reaches `run:` only
  through `env:` or files.
- No PR-triggered job writes to the ledger (fork safety).
