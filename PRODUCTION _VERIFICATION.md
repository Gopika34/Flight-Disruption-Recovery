# Production configuration and end-to-end verification

This checklist separates what can be verified in source code from what must be verified in the live Clerk, Vercel and Render environments.

## Clerk + Google OAuth

1. In the Clerk Dashboard, open the application used by the deployed frontend.
2. Enable Google as a social connection and complete Google's OAuth consent-screen / OAuth client setup using the redirect URI displayed by Clerk. Do not invent a callback URL; copy the exact URI Clerk provides.
3. Add the production Vercel hostname as an allowed application domain in Clerk. Add preview domains only if previews are intentionally supported.
4. Set these Vercel frontend environment variables: `VITE_CLERK_PUBLISHABLE_KEY` from that same Clerk instance (production key for production deployment) and `VITE_API_BASE_URL=/api` so requests use the configured Vercel rewrite to Render.
5. Set Render backend variables from the same Clerk instance:
   - `CLERK_ISSUER_URL`: exact issuer URL shown by Clerk for the token template/session token issuer in use.
   - `CLERK_JWKS_URL`: matching JWKS endpoint for that issuer.
   - `AUTHORIZED_PARTIES`: comma-separated exact frontend origins expected in the JWT `azp` claim, e.g. `https://your-app.vercel.app` (include a preview origin only if deliberately allowed).
6. Verify the `iss` and `azp` claims of a freshly issued Clerk session token using a local JWT inspection tool. Do not paste a live token into tickets, logs, source code or chat. `iss` must match `CLERK_ISSUER_URL`; `azp` must be one of `AUTHORIZED_PARTIES` when that claim is present.
7. Sign in with Google on the production site. Confirm the browser gets a Clerk session and that an authenticated `/agent/ask/stream` request returns HTTP 200. A successful Google redirect alone does not prove backend JWT verification works.

## Render backend variables

Confirm all required production values are set in Render, not merely in a local `.env` file:

- `ENVIRONMENT=production`
- `MONGO_URI`, `MONGO_DB`
- `GUEST_TOKEN_SECRET` (at least 32 characters, stable across restarts)
- `CLERK_ISSUER_URL`, `CLERK_JWKS_URL`, `AUTHORIZED_PARTIES`
- `GEMINI_API_KEY` for policy embeddings and whichever agent provider keys are enabled
- `LLM_ORDER` and the corresponding `GEMINI_MODELS`, `GROQ_MODEL`, `MISTRAL_MODEL`
- `CORS_ORIGINS` containing the exact Vercel origin(s), without `*`
- `AIRLABS_API_KEY` if live flight status is expected

For the local Express proxy only, set `BACKEND_URL=http://127.0.0.1:8000` (or your local FastAPI URL); Vercel does not use this Express proxy.

Never expose secret keys through `VITE_` variables. The Clerk publishable key is public; Clerk secret keys, guest signing secret, MongoDB credentials and LLM/provider keys are server-only.

## Live agent smoke test

After deployment, obtain a short-lived guest token from `POST /auth/guest` or use a current Clerk session token. Run:

```powershell
$env:FLIGHTGUARD_API_URL="https://your-api.onrender.com"
$env:FLIGHTGUARD_API_TOKEN="<bearer-token>"
python backend/scripts/smoke_agent.py
```

The script checks HTTP bearer authentication, SSE content type, route event, incremental token events, tool lifecycle event, completion, and a follow-up request using the same Mongo-backed session. To exercise fallback in a staging deployment, temporarily configure a provider order that starts with a deliberately unavailable test provider and a valid secondary provider, restart the backend, run the smoke test, and confirm the fallback provider served the request in server logs. Do not deliberately break production credentials. It deliberately does not print the bearer token or PNRs.

Run backend tests and frontend checks separately:

```bash
cd backend
pytest -q
cd ../frontend
npm install
npm run lint
npm run build
```

The live smoke test must be run against the actual Render deployment with real configured providers and MongoDB. Passing mocked unit tests does not establish production provider availability.
