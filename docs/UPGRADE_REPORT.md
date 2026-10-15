# Upgrade completion report

Verified on **16 October 2026** (Asia/Kolkata). S1–S10 and S13 were already
merged before this continuation. P1–P9 below are now squash-merged into `main`.
Each task used its own branch and PR; the requested large formatting change
used a separate PR. No direct pushes to `main`, force pushes, history rewrites,
retraining, or model-content changes were performed.

## Tasks and pull requests

| Task | PR | Status |
| --- | --- | --- |
| S1–S10, S13: original upgrade | [#11](https://github.com/dhruvbadhe/sba-loan-risk-engine/pull/11) | Previously merged |
| P1: Supabase key configuration, RLS SQL, owner instructions | [#13](https://github.com/dhruvbadhe/sba-loan-risk-engine/pull/13) | Merged; hosted SQL application and key replacement/revocation still require owner action |
| P2 / S12a: Redis warning includes exception text | [#14](https://github.com/dhruvbadhe/sba-loan-risk-engine/pull/14) | Merged |
| P3 / S12b: explicit environment-configured CORS origins | [#15](https://github.com/dhruvbadhe/sba-loan-risk-engine/pull/15) | Merged |
| P4 / S12c: one canonical model artifact | [#16](https://github.com/dhruvbadhe/sba-loan-risk-engine/pull/16) | Merged |
| P5 / S12d: one lazy, lock-protected SHAP explainer per process | [#17](https://github.com/dhruvbadhe/sba-loan-risk-engine/pull/17) | Merged |
| P6: Streamlit `API_BASE_URL` environment setting | [#18](https://github.com/dhruvbadhe/sba-loan-risk-engine/pull/18) | Merged |
| P7: supported Pydantic schema examples | [#19](https://github.com/dhruvbadhe/sba-loan-risk-engine/pull/19) | Merged |
| P8: backend path tests and comparable coverage | [#20](https://github.com/dhruvbadhe/sba-loan-risk-engine/pull/20) | Merged |
| P9 prerequisite: mechanical Ruff formatting | [#21](https://github.com/dhruvbadhe/sba-loan-risk-engine/pull/21) | Merged separately, as requested |
| P9 / S11: pre-commit hooks and developer setup | [#22](https://github.com/dhruvbadhe/sba-loan-risk-engine/pull/22) | Merged |

For P1–P7, regression tests were run against the old behavior and committed
before the fixes in separate commits. The PRs preserve that review evidence;
their final merges were squashed as requested. Every task PR passed the required
`lint-test-build` CI check before merge, including lint, tests, image build, and
API/Redis startup checks.

## Final measured results

Run from the repository root after installing `requirements-dev.txt`:

```bash
python -m pre_commit validate-config
python -m pre_commit run --all-files
python -m ruff check --config ruff.toml app src tests
python -m pytest -q --cov --cov-report=term-missing --cov-report=xml
```

Local validation uses Python **3.9.6**; CI uses Python **3.10**. The local command
prefix was `venv/bin/python`. Results:

```text
ruff check ........................................................ Passed
ruff format ....................................................... Passed
fix end of files .................................................. Passed
trim trailing whitespace .......................................... Passed
check for added large files ....................................... Passed
All checks passed!
91 passed, 15 warnings
TOTAL: 625 statements, 265 missed, 57.60% covered
```

Backend `app/` statement coverage, excluding Streamlit: **324/324 = 100.00%**.
Overall `app/` plus `src/` coverage, with that same exclusion:
**360/625 = 57.60%**. Research modules remain in the denominator; 100% backend
statement coverage does not mean every branch or possible input is tested.
GitHub's Python 3.10 run independently recorded **91 passed, 1 warning** and
**57.60%** coverage. The README badges use measured values.

### P8 before/after comparison

Both rows use exactly the same source scope: `app/` plus `src/`, excluding
`app/streamlit_app.py`, with startup-test subprocesses included.

| Measurement | Before P8 | After P8 |
| --- | --- | --- |
| Passing tests | 59 | 91 |
| Backend app statements | 265/324 = 81.79% | 324/324 = 100.00% |
| Overall statements | 301/625 = 48.16% | 360/625 = 57.60% |

The 32 added tests exercise real bcrypt password hashing, signup/login failures,
cached responses, Redis and audit failures, risk boundaries, Supabase startup
failure, and explainer concurrency/retry. An offline HTTP request uses the real
bundled pipeline and SHAP explainer and checks expected loss and explanation
additivity. Supabase and Redis are mocked; tests forbid network access and read
settings from an empty temporary directory, without the checkout's `.env`.

The comparison was reproduced with the added test files ignored and their new
cases deselected for the baseline, then the complete suite run for the result.
The earlier 32.44% badge included the whole UI and was a different scope; it is
not presented as directly comparable to this result.

## Security and model verification

- `render.yaml` has a `SUPABASE_KEY` entry with `sync: false` and no key
  value. **The old key remains in Git history and must be replaced and revoked.**
- `supabase/rls.sql` enables RLS, removes previous policies and browser table/
  column grants, and defines backend-only policies on `users` and `predictions`.
  It was applied twice in a disposable local PostgreSQL 17 database; backend
  reads/inserts and generated IDs worked, and anonymous/authenticated access
  was denied. The local fixture is [supabase/tests/rls.sql](../supabase/tests/rls.sql);
  never run that fixture in the hosted project.
- Backend means Supabase `service_role`, used by a server-only secret key.
  Supabase gives this role `BYPASSRLS`; RLS does not contain a stolen backend
  key. Database administrators retain maintenance access. The script does not
  audit unrelated custom roles, views, or security-definer functions.
- Disallowed CORS origins receive no `Access-Control-Allow-Origin` header;
  their preflight requests fail. `CORS_ORIGINS` accepts exact comma-separated
  origins; wildcard values are rejected. CORS does not replace authentication.
- The only stored/tracked model is `app/models/best_hgb_pipeline.pkl`.
  Root `models` is a directory symlink to `app/models`, preserving historical
  notebook paths without editing notebooks. Docker/Compose use the canonical
  path explicitly. Legacy paths need a checkout with symlink support.
- The retained model's SHA-256 is unchanged:
  `4ef8dbea6e7b2eed9f280f5bd95192210a22bea747860112e69c8f86ea36baf5`.
  `src/clean.py`, `src/features.py`, `src/pipeline.py`, and notebooks are untouched.
  The formatting PR changed layout and docstring whitespace, not calculations.

## Exclusions and deferred work

No requested P1–P9 repository task was skipped. These limits remain explicit:

- **Hosted security changes are pending owner action.** No Supabase or Render
  dashboard was opened or changed. SQL/key rotation and the currently deployed
  revision are not claimed as verified by this report.
- **Streamlit is excluded from coverage collection and reporting.** Its real
  sign-in form has two focused backend-URL smoke tests. Comprehensive interactive
  session, prediction, and chart testing is outside this backend task's scope.
- **Research/training coverage was not expanded.** Those modules remain counted
  in the overall result; no retraining or feature changes were authorized.
- **Pydantic deprecations are fixed and treated as errors.** Local Python 3.9
  still emits 14 upstream Matplotlib/Pyparsing deprecation warnings and one
  urllib3/LibreSSL warning. They are not suppressed. Dependency upgrades to
  remove unrelated upstream warnings were outside scope.
- **Optional plan items remain deferred:** latency benchmarking, analytics,
  expanded model documentation, and prediction input bounds were not added.
- The unrelated draft project-guide PR and pre-existing local PDF deletion were
  left outside these task PRs.

## Manual steps for the owner

Follow [SUPABASE_SECURITY.md](SUPABASE_SECURITY.md) for exact click-by-click
instructions, in this order:

1. **Create a backend Supabase key.** In Supabase, select the project, then
   **Project Settings → API Keys → Publishable and secret API keys → Secret
   keys → Create new secret key**. Keep the value private.
2. **Set the new key in Render.** Select **sba-loan-risk-api → Environment →
   Edit**, replace `SUPABASE_KEY`, then save and deploy. Wait for **Live** and
   verify health/login before tightening database access. Do not use a
   publishable key for these backend-only tables.
3. **Apply RLS in Supabase.** Open **SQL Editor → New query**, paste only
   [supabase/rls.sql](../supabase/rls.sql), and run as `postgres`. This replaces all
   policies on these two tables; migrate any other direct table clients first.
   Run the verification queries in the security guide, then verify API
   signup/login and prediction audit inserts still work.
4. **Revoke the old committed key.** Return to **Project Settings → API Keys**,
   select the old key, and revoke/delete it after migrating all its consumers.
   For legacy JWT keys, follow the separate migration instructions in the guide.
   Removing a key from a file does not rotate it or remove it from Git history.
5. **Verify the hosted revision.** In Render's **Deploys** page, confirm the
   successful deployment corresponds to the intended merged `main` commit.
   Check `/health`, login, and an authenticated prediction. Repository CI alone
   does not establish which revision is running in production.
6. **Configure browser origins only if needed.** In Render **Environment →
   Edit**, add `CORS_ORIGINS` with exact HTTPS origins, separated by commas,
   without trailing slashes, then save/deploy. Server-side Streamlit requests
   do not require a CORS entry.
7. **Choose the Streamlit backend when running locally.** Use
   `API_BASE_URL=http://127.0.0.1:8000 python -m streamlit run app/streamlit_app.py`.
   Leave the variable unset to keep the current Render default.
8. **Enable hooks in each other checkout.** Activate the project virtualenv,
   run `python -m pip install -r requirements-dev.txt`, then `pre-commit install`.
   Run `pre-commit run --all-files`. Hooks are installed in this working
   checkout, but Git does not distribute hook installation to other clones.

No further branch-protection changes are required by these tasks. Existing
protection and CI/CD gating were retained.
