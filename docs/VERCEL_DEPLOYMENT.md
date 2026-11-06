# Vercel deployment

Python 3.12 and Streamlit 1.66.1 are required for the ASGI dashboard launcher.
The model, inference routes and authentication implementation are unchanged.

`api/index.py` exports the existing FastAPI app and mounts Streamlit after its
API routes. Streamlit's lifespan hook starts and stops its session runtime.
`vercel.json` forwards all requests to this single application; existing API
paths stay unchanged. `pyproject.toml` selects this deployment entry point.
The bundle exceeds 500 MB. Set `VERCEL_SUPPORT_LARGE_FUNCTIONS=1` for both
Production and Preview before deploying to enable Vercel's large-functions beta.
This is already configured on the current hosted project.

Configure `ENV=production`, separate strong `API_KEY` and `JWT_SECRET_KEY` values,
and the existing `SUPABASE_URL` and server-only `SUPABASE_KEY` in Vercel.
The model is included from `app/models`; do not set the old Docker `MODEL_PATH`.
Redis remains optional. Render's internal Redis address is not reachable from
Vercel; configure an externally reachable TLS Redis URL if caching is required.

The dashboard uses `API_BASE_URL` when explicitly configured. Otherwise, on Vercel
it uses `VERCEL_PROJECT_PRODUCTION_URL`, falling back to `VERCEL_URL`. For a preview
deployment, set `API_BASE_URL` explicitly to its URL to test that preview's backend.
Outside Vercel the existing Render default remains available.

Deploy with `npx vercel`, verify the preview, then deploy with `npx vercel --prod`.
Check the API health, invalid-credential rejection, a real authenticated prediction
with SHAP output, and browser login and widget behavior. Streamlit sessions are
in memory and can reset when an instance restarts. Deployment success alone does
not verify an interactive session.

Never upload `.env`, local virtual environments, or raw datasets. `.vercelignore`
excludes these files. No changes to the Render service are required.
