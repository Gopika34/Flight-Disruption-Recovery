# FlightGuard Architecture

## System boundaries

```text
React application
  ├─ Clerk sign-in UI / guest token bootstrap
  ├─ SessionContext (browser-side session selection and cached UI state)
  └─ agentApi.js (POST + fetch reader for SSE)
          |
          v
FastAPI application
  ├─ Authentication: guest HS256 or Clerk RS256/JWKS
  ├─ Rate limiting and CORS
  ├─ Passenger APIs and LangChain agent APIs
  └─ SSE event formatting
          |
          +--> Intent classifier (workflow hint only)
          |
          +--> LangChain create_agent()
          |      ├─ DGCA RAG tool --> embeddings/retriever --> MongoDB Atlas Vector Search
          |      ├─ Flight status tool --> AirLabs-backed flight service
          |      ├─ Claim package tool --> claims service
          |      ├─ Alternative flight tool --> rebooking service
          |      ├─ Stay/transport tool --> recovery services
          |      └─ evaluate_disruption --> Pydantic Scenario --> deterministic rule engine
          |
          +--> LLM provider router --> Gemini / Groq / Mistral
          |
          +--> MongoDB passenger session persistence (owner_id scoped)
```

## Three different kinds of routing

- **Intent routing** (`app/llm/intent_router.py`): classifies the passenger's wording into a workflow hint. It does not calculate entitlements. The current classifier adds route metadata to the agent context and exposes `/assistant/route` for observability.
- **Tool routing** (LangChain agent): the model chooses from the registered `@tool` functions based on the request and tool descriptions.
- **Provider routing** (`app/llm/router.py`): chooses/configures model providers and fallback order. It is independent of passenger intent.

## Decision authority

The rule engine is authoritative for supported legal/entitlement outcomes. RAG returns relevant DGCA passages, and the agent explains information. Neither retrieved text nor model-generated reasoning may override the rule-engine result. Missing facts must remain missing and trigger clarification or an indeterminate result.

## Session ownership

The backend verifies a bearer token and creates a `Principal(owner_id, kind)`. The owner ID is passed internally to MongoDB session operations. Session queries are scoped by both session ID and owner ID. The browser's `SessionContext` also caches session metadata/messages in localStorage, but that browser cache is not an authorization boundary.

Guest and Clerk users have different owner IDs. The current project does not implement guest-history migration. Existing legacy MongoDB documents without an owner are not automatically assigned to a new identity.

## Streaming

`POST /agent/ask/stream` is a POST-based SSE stream consumed with `fetch()` and a `ReadableStream`, not native `EventSource`. The backend emits named events such as `session`, `route`, `status`, `token`, `tool_start`, `tool_end`, `error`, and `done`. Verify event payloads in `app/llm/agent.py` when changing the frontend parser. Tool arguments and raw tool results must not be forwarded to the browser.
