---
name: flightguard-domain
description: Domain and engineering rules for developing FlightGuard, a DGCA-grounded flight-disruption recovery assistant.
---

# FlightGuard Domain Skill

Use this skill whenever changing FlightGuard backend, frontend, RAG, rules, LangChain tools, authentication, streaming, or documentation.

## Product model
FlightGuard helps passengers understand flight-disruption options for supported Indian aviation scenarios. It combines:
- DGCA policy retrieval through RAG and MongoDB Atlas Vector Search.
- Deterministic Python evaluation for supported disruption facts.
- LangChain `create_agent()` with tools for policy retrieval, flight information, claim preparation, alternative flight schedules, emergency stay/transport, and deterministic disruption evaluation.
- Provider fallback (Gemini, Groq, Mistral) managed by the existing LLM router.
- FastAPI SSE endpoints and a React chat interface.
- Guest identities issued by the backend and registered identities verified from Clerk JWTs.

## Authority hierarchy
1. Validated passenger facts and trusted provider data are inputs, not conclusions.
2. `app/rules/rule_engine.py` is authoritative for supported entitlement outcomes.
3. `app/services/` implements domain operations and data access.
4. RAG supplies supporting regulatory passages; retrieval is evidence, not a legal ruling.
5. The LangChain agent chooses tools and explains results. It cannot overrule the rule engine.
6. Frontend text is presentation only and must not calculate legal outcomes.

## Tool authoring checklist
For every `@tool`:
- Write a clear docstring describing when to call it, required fields, accepted formats, and limitations.
- Validate all arguments with existing Pydantic schemas or explicit bounded checks.
- Call the existing service/rule implementation; do not duplicate business logic.
- Treat absent/unknown facts as unknown. Return a `needs_more_info`/`cannot_determine` state when applicable.
- Bound result sizes and remove unnecessary personal data, PNRs, contact data, and provider internals.
- Return a predictable structured JSON string where useful (`status`, safe result fields, limitations, next action).
- Catch expected domain/provider errors separately; log safe diagnostic context server-side and return a non-sensitive message.
- Do not add side-effecting booking/payment/claim-submission tools without explicit confirmation and authorization design.

## Agent behavior
- Ask concise follow-up questions when required information is missing.
- Use `evaluate_disruption` for compensation/refund entitlement questions, passing only known facts.
- Use `search_dgca_policy` for relevant supporting policy evidence.
- Use flight tools for flight-specific requests; never invent a flight identifier.
- Distinguish provider facts, user-provided facts, estimates, retrieved text, and rule-engine outcomes.
- Do not expose tool arguments, PNR, passenger name, tokens, payment details, or internal errors.
- Never claim a booking, seat, voucher, hotel reservation, refund, or claim submission occurred unless an authorized integration confirms it.

## Routing
`classify_intent()` is a lightweight deterministic workflow hint. It is not an LLM provider router and not a legal evaluator. Ambiguous input should be handled conversationally by the agent. Keep the rule engine as the only entitlement authority.

## Authentication and persistence
- Guest token: backend-signed HS256 token with `typ=guest`, issuer, expiry, and `guest_` subject.
- Registered user: Clerk session JWT verified by backend using RS256/JWKS, issuer and authorized-party checks.
- `owner_id` must come from the verified `Principal`, never from user input.
- MongoDB session reads/writes must filter by both session ID and owner ID.
- Guest and Clerk histories are separate. No guest-history migration exists unless a separately reviewed, explicit transfer feature is implemented.

## Streaming
Current agent stream uses POST `/agent/ask/stream` and named SSE events including `session`, `route`, `status`, `tool_start`, `tool_end`, `token`, `error`, and `done` (verify implementation before relying on exact event payloads). Browser events must not contain tool args or raw tool results. Handle cancellation and failed streams without displaying secrets.

## Common commands
```bash
# backend
cd backend
pip install -r requirements-dev.txt
pytest -q
uvicorn app.main:app --reload

# frontend
cd frontend
npm install
npm run build
npm run dev
```

## Definition of done
- Tests cover the new behavior and relevant failure paths.
- No secrets or private passenger information are added to source control.
- Backend and frontend checks are reported truthfully.
- API, environment, architecture, or setup changes are reflected in docs.
