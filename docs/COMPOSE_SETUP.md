# Run the API and Redis locally

Install Docker with Compose and start its engine. From a clean clone, run:

```bash
docker compose up --build
```

Open <http://localhost:8000/docs> or check the public health endpoint:

```bash
curl --fail http://localhost:8000/health
```

The API waits for Redis to become healthy. Redis is reachable inside the Compose
network at `redis:6379`; it does not expose a host port. Its cached predictions
are temporary and can be discarded when containers are removed.

No `.env` file or cloud account is needed for API-key predictions. The API runs
in development mode and binds only to the local machine. The Compose API-key
placeholder is `local-compose-api-key`; the JWT placeholder is also for local
development only. Use the API docs' **Authorize** button to supply the API key.
The image uses the existing model under `app/models/`.

To enable signup, login, and prediction audit logging, supply your own
`SUPABASE_URL` and `SUPABASE_KEY` through environment variables or a local,
Git-ignored `.env`. You can override `API_KEY` and `JWT_SECRET_KEY` the same way.
Without Supabase, login/signup return 503; API-key predictions still work.

Streamlit is not included in this Compose stack. The existing dashboard is
configured to call the hosted API; this task provides the API and Redis services.

For a detached run that waits for both services to be healthy:

```bash
docker compose up --build --wait --wait-timeout 180
docker compose ps
docker compose logs api
docker compose down
```

The defaults in this file are for local development. Production uses private
environment variables and the Render deployment gate documented separately.
