# Frontend Agent Instructions

Follow the root `AGENTS.md` and the FlightGuard domain skill at `.agents/skills/flightguard/SKILL.md`.

## Frontend-specific conventions
- Keep API calls in `src/services/`; avoid embedding fetch logic in page components.
- Use `src/services/authToken.js` as the token boundary. Do not read Clerk secrets or backend signing secrets in the browser.
- The backend issues guest tokens at `POST /auth/guest`; Clerk supplies registered-user session tokens. The backend verifies either token type.
- Use `src/services/agentApi.js` for the LangChain agent SSE stream. Parse events incrementally and handle aborts/errors.
- Render only safe tool lifecycle labels and assistant text. Do not render raw tool arguments or internal tool output.
- Session IDs are opaque identifiers, not proof of ownership. The backend must authorize every session operation.
- Identity switching must not silently merge guest data into a Clerk account. Clear or isolate client-side state when principal type changes.
- Do not claim a flight is booked or a seat/hotel is confirmed based on search results.
- Preserve accessible labels, keyboard behavior, loading states, and responsive layouts.

## Validation
- Run `npm run build` after UI/service changes.
- Run `npm run lint` where TypeScript checking is applicable; this repo includes JSX and may have existing lint/type limitations.
- Manually test guest initialization, Clerk login, switching identities, a normal agent answer, a tool-start/tool-end event, stream cancellation, and a failed API response.

## Express API proxy
- `server.ts` must forward the incoming bearer `Authorization` header to FastAPI for every protected `/api/*` request.
- Treat both `/ask/stream` and `/agent/ask/stream` as SSE: forward chunks as they arrive, set no-buffer headers, and abort the upstream request when the browser disconnects.
- Vercel's `/api/:path*` rewrite bypasses this local Express proxy; verify Vercel and local proxy behavior separately.
