# FlightGuard — Agent Instructions

## Project purpose
FlightGuard is a passenger-facing flight-disruption decision-support application focused on Indian DGCA guidance. It combines React, FastAPI, MongoDB Atlas Vector Search, RAG, deterministic Python rules, LangChain tool calling, flight/recovery integrations, guest JWT authentication, and Clerk-issued user JWT verification.

## Non-negotiable domain rules
1. **The deterministic Python rule engine is the only authority for entitlement outcomes and statutory amounts.** Never calculate or infer compensation in an LLM prompt, agent, frontend, or tool wrapper.
2. The LLM may explain results and retrieve supporting DGCA evidence; it must not override rule-engine output.
3. Never invent flight status, fares, seats, hotel availability, bookings, vouchers, airline responses, or policy quotations.
4. AirLabs schedule data is not a confirmed bookable fare or seat inventory. Hotel directory entries and transport estimates are not confirmed availability or quotes.
5. Ask for missing facts. Never convert unknown values into `false`, `0`, or a convenient default for legal evaluation.
6. Do not expose PNRs, passenger personal data, credentials, tool arguments, raw provider payloads, stack traces, or internal errors in browser-facing events or logs.
7. Never ask passengers to provide bank/UPI details to prepare a claim. Direct them to verified airline channels where required.

## Repository map
- `backend/app/main.py`: FastAPI app, route registration, API endpoints and SSE formatting.
- `backend/app/core/`: environment configuration and guest/Clerk principal verification.
- `backend/app/llm/`: provider selection, LangChain agent, tool definitions, intent classifier and prompts.
- `backend/app/rag/`: embeddings, retrieval, validation and generation.
- `backend/app/rules/`: deterministic rule engine.
- `backend/app/services/`: domain services and MongoDB session persistence.
- `backend/app/schemas/`: Pydantic request/domain schemas.
- `backend/tests/`: pytest suite.
- `frontend/src/services/`: API, token handling and agent SSE client.
- `frontend/src/context/`: client-side session state.
- `frontend/src/pages/ChatPage.jsx`: agent chat experience.

## Development rules
- Read the relevant implementation and tests before editing. Prefer small, targeted changes over broad rewrites.
- Preserve existing API contracts unless the task explicitly changes them. Update tests and docs when a contract changes.
- Keep domain logic in backend services/rules, not React components or LLM prompts.
- Keep provider selection in `backend/app/llm/router.py`; do not add a second model-provider registry.
- Keep intent classification separate from provider fallback. `classify_intent()` is workflow metadata, not a legal decision or authentication signal.
- LangChain tools must validate input, call existing domain services, return bounded structured results, and fail with safe user-facing messages. Do not duplicate service logic inside tools.
- Any tool that can cause an external side effect must require explicit user confirmation and server-side authorization. Current search/evaluation tools should remain read-only.
- Preserve owner scoping: derive `owner_id` only from `get_current_principal`; never accept it from request JSON or query parameters.
- Do not weaken JWT verification, CORS restrictions, rate limits, or production configuration checks.
- SSE events may contain only safe UI metadata and generated text. Never stream tool arguments or raw tool output.
- Keep guest and Clerk user sessions isolated. Guest-to-user migration is not implemented; do not imply it is.
- Avoid committing `.env`, secrets, tokens, database dumps, private passenger data, or generated runtime files.

## Commands
Backend (from `backend/`):
```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q
uvicorn app.main:app --reload
```
Frontend (from `frontend/`):
```bash
npm install
npm run build
npm run lint
npm run dev
```

## Before declaring work complete
- Run focused tests, then the full backend test suite when dependencies/configuration permit.
- Run `npm run build` for frontend changes.
- Report commands actually run and distinguish passed, failed, and not-run checks.
- Check both guest and Clerk-authenticated request paths for protected API changes.
- Check ownership isolation for any session/data access change.
- Update `README.md` or the relevant document when setup, endpoints, environment variables, or architecture changes.

## Agent workflow invariants
- `tools_for_intent()` in `backend/app/llm/agent.py` is the enforced per-intent tool allowlist. When adding an intent or tool, update the mapping and its tests; do not silently expose the full catalogue to every route.
- `AskIn.known_facts` is untrusted client input validated against `Scenario`. Merge it only with facts loaded from the same owner-scoped MongoDB session, validate the merged facts, and persist them with that same verified owner. Never accept `owner_id` from the client.
- MongoDB messages are the conversation history source of truth; MongoDB session facts are the structured facts source of truth. Browser local storage is a convenience cache, not an authorization or persistence authority.
- The Express proxy must forward `Authorization` and stream both `/ask/stream` and `/agent/ask/stream` incrementally. Do not buffer SSE responses or log bearer tokens.
