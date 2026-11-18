# Backend Agent Instructions

Follow the root `AGENTS.md` and the FlightGuard domain skill at `.agents/skills/flightguard/SKILL.md`.

## Backend-specific conventions
- Use FastAPI routers/dependencies and Pydantic schemas for request validation.
- Keep business rules in `app/rules/` and reusable orchestration in `app/services/`.
- `app/llm/tools.py` is an adapter layer: LangChain tool -> validated schema -> existing service/rule function -> bounded serializable result.
- `app/llm/intent_router.py` may choose a workflow hint only. It must not make eligibility decisions.
- `app/llm/router.py` owns LLM provider selection/fallback. Do not conflate it with passenger-intent routing.
- Auth principal types are `guest` and `clerk` (tests may use `test`). Use `Principal.owner_id` returned by `get_current_principal` for persistence.
- MongoDB session functions in `app/services/sessions.py` enforce owner-scoped access. Preserve this behavior and test cross-owner access.
- Keep SSE responses formatted through the existing helper in `app/main.py`; event payloads must be safe for the browser.
- Never swallow `HTTPException` ownership failures as generic database errors.

## Test expectations
- Add tests for invalid/missing tool inputs and service failures.
- Test entitlement tool behavior with missing facts and valid facts; assert the rule engine is called rather than reimplementing expected arithmetic in the tool.
- Test route classification for positive, negative, and ambiguous utterances.
- Test JWT expiry, invalid signature/issuer, wrong token type, and owner isolation where practical.
- Use mocks for external providers; tests must not make real AirLabs, Gemini, Groq, Mistral, or MongoDB calls.

## Agent workflow implementation
- `create_flight_agent(intent)` must be constructed with `tools_for_intent(intent)`, not the entire tool catalogue.
- Keep `AskIn.known_facts` aligned with the `Scenario` schema. The agent validates and owner-scopes the merged session facts using `load_facts` / `save_facts` before building model context.
- Keep provider fallback in `get_agent_chat_models()`; workflow tool filtering must not create a parallel provider router.
- The live deployment smoke test is `python scripts/smoke_agent.py` with `FLIGHTGUARD_API_URL` and `FLIGHTGUARD_API_TOKEN` set in the environment.
