"""LangChain tool-calling agent with owner-scoped memory and real event streaming."""
import logging
from functools import lru_cache
from typing import Any

from langchain.agents import create_agent
from langchain_core.messages import SystemMessage
from langchain.agents.middleware import ToolCallLimitMiddleware, ToolRetryMiddleware

from app.llm.router import get_agent_chat_models
from app.llm.tools import flight_tools
from app.loaders.prompt_loader import load_prompt
from app.services.sessions import load_messages, save_messages
from app.llm.intent_router import classify_intent

logger = logging.getLogger(__name__)


def extract_text_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict) and part.get("type") == "text":
                parts.append(str(part.get("text", "")))
            elif isinstance(part, dict) and "text" in part:
                parts.append(str(part["text"]))
            elif hasattr(part, "text"):
                parts.append(str(part.text))
        return "".join(parts)
    if isinstance(content, dict) and "text" in content:
        return str(content["text"])
    return str(content or "")


def _serialize_message(msg: Any) -> dict[str, Any]:
    """Preserve tool-call metadata so restored histories remain valid."""
    if isinstance(msg, dict):
        role = msg.get("role", "assistant")
        out = {"role": role, "content": extract_text_content(msg.get("content", ""))}
        for key in ("name", "tool_call_id", "tool_calls"):
            if msg.get(key) is not None:
                out[key] = msg[key]
        return out

    msg_type = getattr(msg, "type", "ai")
    role = {"human": "user", "ai": "assistant", "system": "system", "tool": "tool"}.get(msg_type, "assistant")
    out = {"role": role, "content": extract_text_content(getattr(msg, "content", ""))}
    name = getattr(msg, "name", None)
    tool_call_id = getattr(msg, "tool_call_id", None)
    tool_calls = getattr(msg, "tool_calls", None)
    if name:
        out["name"] = name
    if tool_call_id:
        out["tool_call_id"] = tool_call_id
    if tool_calls:
        out["tool_calls"] = [
            {"name": tc.get("name"), "args": tc.get("args", {}),
             "id": tc.get("id"), "type": "tool_call"}
            for tc in tool_calls if isinstance(tc, dict)
        ]
    return out


def get_system_prompt() -> str:
    try:
        return load_prompt("agent_system.txt")
    except Exception as exc:
        logger.warning("Could not load agent prompt (%s); using safe fallback", type(exc).__name__)
        return (
            "You are the Flight Disruption Recovery Assistant. Use tools for verified data. "
            "Never invent compensation, prices, seats, hotel availability, bookings or vouchers. "
            "Clearly label schedule-only and estimated information."
        )


@lru_cache(maxsize=1)
def create_flight_agent():
    return create_agent(
        model=get_agent_chat_models(),
        tools=flight_tools,
        system_prompt=get_system_prompt(),
        middleware=[
            ToolRetryMiddleware(max_retries=2, backoff_factor=2.0, initial_delay=1.0),
            ToolCallLimitMiddleware(run_limit=5),
        ],
        name="flight_disruption_agent",
    )


def run_agent(message: str, session_id: str | None = None, owner_id: str = "legacy_unowned") -> str:
    if not isinstance(message, str) or not 3 <= len(message.strip()) <= 2000:
        raise ValueError("Message must contain between 3 and 2000 characters.")
    agent = create_flight_agent()
    history = load_messages(session_id, owner_id) if session_id else []
    route = classify_intent(message)
    messages = [SystemMessage(content=("Request routing metadata (server-generated): " + route.intent + ". " + route.reason + " Follow the required workflow. For entitlement questions, call evaluate_disruption with only known facts; ask for missing facts instead of guessing.")), *list(history)]
    messages.append({"role": "user", "content": message})
    result = agent.invoke({"messages": messages})
    output_messages = result.get("messages", [])
    final_content = extract_text_content(output_messages[-1].content) if output_messages and hasattr(output_messages[-1], "content") else ""
    if session_id:
        save_messages(session_id, [_serialize_message(msg) for msg in output_messages if getattr(msg, "type", None) != "system"], owner_id)
    return final_content


async def stream_agent_events(message: str, session_id: str | None = None, owner_id: str = "legacy_unowned"):
    """Stream genuine model chunks and tool lifecycle events through LangChain v2."""
    if not isinstance(message, str) or not 3 <= len(message.strip()) <= 2000:
        yield "error", {"message": "Message must contain between 3 and 2000 characters."}
        return
    agent = create_flight_agent()
    history = await __import__("asyncio").to_thread(load_messages, session_id, owner_id) if session_id else []
    route = classify_intent(message)
    messages = [SystemMessage(content=("Request routing metadata (server-generated): " + route.intent + ". " + route.reason + " Follow the required workflow. For entitlement questions, call evaluate_disruption with only known facts; ask for missing facts instead of guessing.")), *list(history)]
    messages.append({"role": "user", "content": message})

    yield "session", {"session_id": session_id}
    yield "route", {"intent": route.intent, "destination": route.destination}
    yield "status", {"message": "Analyzing your request..."}
    final_messages: list[Any] | None = None
    streamed_text = False

    try:
        async for event in agent.astream_events({"messages": messages}, version="v2"):
            event_name = event.get("event", "")
            event_data = event.get("data") or {}

            if event_name == "on_chat_model_stream":
                chunk = event_data.get("chunk")
                if chunk is not None and not getattr(chunk, "tool_call_chunks", None):
                    text = extract_text_content(getattr(chunk, "content", ""))
                    if text:
                        streamed_text = True
                        yield "token", {"text": text}

            elif event_name == "on_tool_start":
                # Tool arguments may contain PNRs, names, route or booking details.
                # Never expose them in browser event payloads.
                yield "tool_start", {"tool": event.get("name", "tool"), "id": event.get("run_id")}

            elif event_name == "on_tool_end":
                yield "tool_end", {"tool": event.get("name", "tool"), "status": "complete"}

            elif event_name == "on_chain_end":
                output = event_data.get("output")
                if isinstance(output, dict) and isinstance(output.get("messages"), list):
                    final_messages = output["messages"]

        if session_id and final_messages:
            await __import__("asyncio").to_thread(
                save_messages, session_id, [_serialize_message(m) for m in final_messages if getattr(m, "type", None) != "system"], owner_id
            )
        if not streamed_text:
            yield "status", {"message": "The agent completed without a text response."}
        yield "done", {"status": "complete", "session_id": session_id}

    except Exception as exc:
        logger.exception("Agent streaming failed (%s)", type(exc).__name__)
        yield "error", {"message": "The AI assistant is temporarily unavailable. Please retry."}
        yield "done", {"status": "failed", "session_id": session_id}
