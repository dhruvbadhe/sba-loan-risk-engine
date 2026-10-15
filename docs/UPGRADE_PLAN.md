# SBA Loan Risk Engine: Upgrade Plan

Goal: make this project read as **engineering + ML**, so it works for SDE roles (Apollo-style: tested, CI/CD, containerised, clean code) and ML/AI roles (evaluation, honest metrics, reliability).

Repo reviewed (code read, not run): `github.com/dhruvbadhe/sba-loan-risk-engine` (last commit 27 Jul 2026)

---

## How to use this file

1. Do **Part 0** first. These are bugs that make current resume claims untrue.
2. Then Part 1 in the order given. Each task has a done-check.
3. Work through **pull requests**, not direct pushes to `main`. Turn on branch protection once CI exists.
4. Only put a bullet on the resume once its done-check passes and it's pushed.
5. Before any interview, go through the interview section in Part 1 and be able to explain every file you changed.

---

## Part 0: Fix before anything else

| # | Problem | Where | Why it matters |
|---|---|---|---|
| 0.1 | **Auth bypass.** A request with no API key and no token passes. `verify_api_access` only raises inside `if token:`, so it returns `None` and FastAPI lets the request through. A wrong API key with no token also passes. | `app/core/dependencies.py` | "JWT-secured API" is false today |
| 0.2 | **Login backdoor.** If Supabase isn't configured, `admin`/`admin` logs in. | `app/api/routes_auth.py` | Hardcoded credentials in a public repo |
| 0.3 | **Default secrets are public.** `API_KEY="dev-key-change-in-production"` and the default JWT secret are in the repo. If Render env vars aren't set, anyone can call the API. | `app/core/config.py` | Check Render's env vars today |

Each of these is also an interview story: **wrote a test → it failed → found the bug → fixed it → the test stays in the suite.** Keep the failing test commit and the fix commit separate so the history shows it.

---

## Part 1: Tasks

### Current state
- **Good:** layered app (`api/`, `core/`, `cache/`, `middleware/`), multi-stage Dockerfile, Redis with graceful no-cache fallback, Prometheus instrumentation, Pydantic request/response models, JWT + API key auth, prediction audit log to Supabase, `src/` ML pipeline split into clean/features/pipeline/evaluate/expected_loss/risk_tiers.
- **Missing:** tests, CI, docker-compose, linting, migrations, secret hygiene.
- **Smaller issues:**
  - Model `.pkl` committed twice (`models/` and `app/models/`)
  - CORS `allow_origins=["*"]` with `allow_credentials=True`
  - Redis warning log: typo `yo`, and missing `f` so `{e}` never prints
  - `shap.TreeExplainer` is rebuilt on every request (slow); build it once at startup
  - Model is loaded at import time; a missing file crashes startup with an unclear error

### Tasks (in order)

| # | Task | Done when | Time |
|---|---|---|---|
| S1 ✅ | Fix 0.1: raise 401 at the end of `verify_api_access` | Request with no credentials → 401 | 15 min |
| S2 ✅ | Fix 0.2: delete the `admin`/`admin` branch; return 503 instead | No hardcoded credentials in repo | 10 min |
| S3 | Fix 0.3: fail startup when `ENV=production` and secrets are default | App refuses to boot with default secrets in prod; Render env vars confirmed — local checks pass; awaiting [Render confirmation](RENDER_ENV_SETUP.md) | 20 min |
| S4 | **API tests** (pytest + FastAPI `TestClient`): no creds → 401, bad JWT → 401, valid JWT → 200, valid API key → 200, invalid payload → 422, `/health` → 200. Mock Supabase and Redis. | All pass locally | 1 h |
| S5 | **Unit tests** for `src/expected_loss.py` (LGD clipping, zero gross approval, EL = PD×LGD×EAD) and `src/risk_tiers.py` (each tier boundary) | All pass | 45 min |
| S6 | **Coverage** with `pytest-cov`; record the % | Coverage number in README | 10 min |
| S7 | **GitHub Actions CI:** ruff lint → pytest with coverage → Docker build, on every PR and push to `main` | Green badge in README | 45 min |
| S8 | **Branch protection** on `main` (CI must pass) + PR template | Settings on | 10 min |
| S9 | **CD:** Render deploys only after CI passes on `main` (Render "auto-deploy on CI checks pass", or a deploy hook step in the workflow) | Broken PR can't reach prod | 20 min |
| S10 | **docker-compose:** API + Redis (+ Streamlit) with one command | `docker compose up` works on a clean clone | 45 min |
| S11 | **pre-commit:** ruff, ruff-format, end-of-file fixers | Hooks run on commit | 20 min |
| S12 | Cleanups: one model copy, fix Redis log line, restrict CORS origins, build SHAP explainer once at startup | Each in its own small PR | 45 min |
| S13 | README: architecture diagram (client → FastAPI → auth → cache → model → SHAP → audit log), setup, env vars table, API examples, test/CI badges, design decisions | README reads as an engineering doc | 1 h |

**Block 1 local verification (15 October 2026):** 17 tests passed with two existing
Pydantic deprecation warnings. Statement coverage is 10.20% across all Python code
in `app/` and `src/` (including the untested UI and training modules); settings
coverage is 100%. Measurement includes the startup-test child processes. S1 and S2
have passed their checks on the task branches; the PRs remain unmerged. S3's local
checks pass, but its done-check still requires Render environment confirmation.

**Optional (after the deadline)**
- **Latency numbers:** a small Locust or `httpx` load test; report p50/p95 with and without Redis. Strong for both SDE and ML-serving roles.
- **SQL analytics endpoint:** approval/EL by risk tier and sector from the `predictions` table (Supabase RPC or direct Postgres). Shows real SQL.
- **Model card** section in README: data window, out-of-time split, AUC 0.75, known limits (LGD assumes zero recovery on the unguaranteed part; trained on historical SBA data only).
- **Input validation:** bounds on rates, terms and amounts in the Pydantic model (e.g. `gt=0`).

### What to know cold for interviews (SBA)
- **Auth flow:** login → bcrypt verify → JWT with `exp` → `Authorization: Bearer` → `decode_access_token`. Why the bypass happened and how the test caught it.
- **Cache:** key = hash of the input, TTL 1 h. Why a deterministic model makes this safe. What happens when Redis is down (falls back to no cache). When the cache must be cleared (new model version → include model version in the key).
- **EL:** PD from the model; LGD = (GrAppv − SBA_Appv) / GrAppv (unguaranteed share, assumes zero recovery → conservative upper bound); EAD = GrAppv.
- **Validation:** why out-of-time, what "leak-safe out-of-fold" bank/sector default-rate features mean.
- **Docker:** why multi-stage (smaller image, no compilers in runtime).
- **CI:** each step in the workflow and why mocks are needed.

---

## Part 2: Resume bullets (SDE + ML)

Use these once the matching tasks are done. Replace `N` and `X` with real numbers.

**SBA Loan Risk Engine & REST API** (Python, FastAPI, scikit-learn, Redis, Docker, GitHub Actions) — GitHub | Live Demo
- Built a credit-risk API that scores SBA 7(a) loan applications and returns 4-tier underwriting decisions, with JWT/API-key auth, Redis caching, Prometheus metrics and an audit log of every decision.
- Trained a HistGradientBoosting PD model on 1.9M+ loans with leak-safe out-of-fold bank and sector features, validated on an out-of-time split (ROC-AUC 0.75); converted PD to Expected Loss (EL = PD × LGD × EAD, LGD from the unguaranteed share) with per-loan SHAP explanations.
- Added a pytest suite (N tests, X% coverage) and GitHub Actions CI/CD (lint → test → Docker build → deploy); the suite caught and fixed an auth bypass that let unauthenticated requests reach the prediction endpoint.

### Which bullet to lead with
| Target | Lead with |
|---|---|
| SDE (Apollo, SAP) | Bullet 1 (API) then 3 (tests/CI) |
| ML / AI engineer | Bullet 2 (model + EL) then 1 |

### Claims to remove or reword everywhere
- "JWT-secured" → only after S1–S3 are merged.
- Supabase "PostgreSQL audit logs" → fine, Supabase is Postgres; be ready to say you used its client, not raw SQL.

---

## Part 3: Order of work and time (with Claude Code)

| Block | Tasks | Time |
|---|---|---|
| 1 | S1–S3 (security fixes) | 45 min |
| 2 | S4–S6 (tests + coverage) | 2 h |
| 3 | S7–S9 (CI/CD + branch protection) | 1.25 h |
| 4 | S10, S13 (compose + README) | 1.75 h |
| **Total** | | **~5.75 h** |
| Later | S11–S12, optional items | +2–3 h |

If time is short, blocks 1–3 alone make every SBA resume claim true.

### Prompting Claude Code
- One task per session. Paste the task row and its done-check.
- Ask it to write the **failing test first**, run it, then fix.
- Ask for a short explanation of every changed file, and read the diff before committing.
- Never let it touch the model pipeline (`src/pipeline.py`, `.pkl` files) during these tasks.

### Before submitting
- [ ] CI green
- [ ] Live demo opens and `/health` responds
- [ ] Render env vars set (no default secrets)
- [ ] Every resume number matches the repo
- [ ] You can explain every file you changed
