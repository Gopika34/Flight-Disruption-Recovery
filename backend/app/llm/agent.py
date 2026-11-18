import json
import logging
from functools import lru_cache
from typing import Any, Iterator

from langchain.agents import create_agent
from langchain.agents.middleware import (
    ToolRetryMiddleware,
    ToolCallLimitMiddleware,
)

from app.core import config as C
from app.llm.router import get_agent_chat_models
from app.llm.tools import flight_tools
from app.loaders.prompt_loader import load_prompt
from app.services.sessions import append_message, load_messages, save_messages

logger = logging.getLogger(__name__)


# ==================================================
# UTILITY HELPERS
# ==================================================

def extract_text_content(content: Any) -> str:
    """Extract clean plain text from LangChain message content.
    Handles str, list of content blocks (dicts or objects), and Gemini multi-part blocks.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict):
                if part.get("type") == "text" and "text" in part:
                    parts.append(str(part["text"]))
                elif "text" in part:
                    parts.append(str(part["text"]))
            elif hasattr(part, "text"):
                parts.append(str(part.text))
        return "".join(parts)
    if isinstance(content, dict):
        if "text" in content:
            return str(content["text"])
    return str(content or "")


# ==================================================
# SYSTEM INSTRUCTIONS
# ==================================================

def get_system_prompt() -> str:
    try:
        return load_prompt("agent_system.txt")
    except Exception as exc:
        logger.warning("Could not load agent_system.txt: %s. Using fallback prompt.", exc)
        return (
            "You are the Flight Disruption Recovery Assistant for Indian DGCA regulations. "
            "Help passengers with claims, flight rebooking, and emergency accommodation using your tools. "
            "Never invent compensation amounts or seat confirmations."
        )


# ==================================================
# CREATE AGENT
# ==================================================

@lru_cache(maxsize=1)
def create_flight_agent():
    model = get_agent_chat_models()
    system_prompt = get_system_prompt()

    agent = create_agent(
        model=model,
        tools=flight_tools,
        system_prompt=system_prompt,
        middleware=[
            ToolRetryMiddleware(
                max_retries=2,
                backoff_factor=2.0,
                initial_delay=1.0,
            ),
            ToolCallLimitMiddleware(
                run_limit=5,
            ),
        ],
        name="flight_disruption_agent",
    )

    return agent


# ==================================================
# AGENT EXECUTION (WITH CONVERSATION MEMORY)
# ==================================================

def run_agent(message: str, session_id: str | None = None) -> str:
    """
    Execute the tool-calling agent with multi-turn conversation memory.
    If session_id is provided, existing message history is loaded and updated.
    """
    agent = create_flight_agent()

    history: list[dict[str, Any]] = []
    if session_id:
        try:
            history = load_messages(session_id)
        except Exception as exc:
            logger.warning("Could not load session messages for %s: %s", session_id, exc)

    messages = list(history)
    messages.append({
        "role": "user",
        "content": message,
    })

    result = agent.invoke({"messages": messages})
    output_messages = result.get("messages", [])

    final_content = (
        extract_text_content(output_messages[-1].content)
        if output_messages and hasattr(output_messages[-1], "content")
        else str(output_messages[-1]) if output_messages else ""
    )

    # Persist updated conversation
    if session_id:
        try:
            serialized_messages = []
            for msg in output_messages:
                if hasattr(msg, "type"):
                    content_str = extract_text_content(getattr(msg, "content", ""))
                    serialized_messages.append({"role": msg.type, "content": content_str})
                elif isinstance(msg, dict):
                    serialized_messages.append(msg)
                else:
                    serialized_messages.append({"role": "assistant", "content": str(msg)})
            save_messages(session_id, serialized_messages)
        except Exception as exc:
            logger.warning("Could not persist session messages for %s: %s", session_id, exc)

    return final_content


# ==================================================
# AGENT EVENT STREAMING (LIFECYCLE SSE)
# ==================================================

def stream_agent_events(message: str, session_id: str | None = None) -> Iterator[tuple[str, dict[str, Any]]]:
    """
    Yields (event_name, data_payload) pairs representing the agent's
    thought, tool call execution lifecycle, and response stream.
    """
    agent = create_flight_agent()

    history: list[dict[str, Any]] = []
    if session_id:
        try:
            history = load_messages(session_id)
        except Exception:
            pass

    messages = list(history)
    messages.append({"role": "user", "content": message})

    yield "session", {"session_id": session_id}
    yield "status", {"message": "Analyzing passenger request..."}

    try:
        final_answer = ""
        for chunk in agent.stream({"messages": messages}):
            if not isinstance(chunk, dict):
                continue

            for node_name, node_val in chunk.items():
                if not isinstance(node_val, dict):
                    continue

                node_messages = node_val.get("messages", [])
                if not node_messages:
                    continue

                for msg in node_messages:
                    tool_calls = getattr(msg, "tool_calls", None)

                    # Model tool calling phase
                    if tool_calls:
                        for tc in tool_calls:
                            if not tc:
                                continue
                            if isinstance(tc, dict):
                                tc_tool = tc.get("name")
                                tc_args = tc.get("args")
                                tc_id = tc.get("id")
                            else:
                                tc_tool = getattr(tc, "name", None)
                                tc_args = getattr(tc, "args", {})
                                tc_id = getattr(tc, "id", None)
                            yield "tool_start", {
                                "tool": tc_tool,
                                "args": tc_args,
                                "id": tc_id,
                            }

                    # Tool execution output phase
                    elif getattr(msg, "type", "") == "tool":
                        raw_out = extract_text_content(getattr(msg, "content", ""))
                        yield "tool_end", {
                            "tool": getattr(msg, "name", "tool"),
                            "output": raw_out[:250] + ("..." if len(raw_out) > 250 else ""),
                        }

                    # Final assistant message content (only when not making tool calls)
                    elif hasattr(msg, "content") and msg.content and not tool_calls:
                        clean_text = extract_text_content(msg.content)
                        if clean_text:
                            final_answer = clean_text
                            # Progressive word streaming for smooth UI display
                            words = clean_text.split(" ")
                            chunk_words = []
                            for w in words:
                                chunk_words.append(w)
                                if len(chunk_words) >= 4:
                                    yield "token", {"text": " ".join(chunk_words) + " "}
                                    chunk_words = []
                            if chunk_words:
                                yield "token", {"text": " ".join(chunk_words)}

        if session_id and final_answer:
            try:
                append_message(session_id, {"role": "user", "content": message})
                append_message(session_id, {"role": "assistant", "content": final_answer})
            except Exception as exc:
                logger.warning("Could not persist session messages for %s: %s", session_id, exc)

        yield "done", {"status": "complete", "session_id": session_id}

    except Exception as exc:
        logger.exception("Agent streaming error")
        yield "error", {"message": f"Agent error: {str(exc)}"}
        yield "done", {"status": "failed", "session_id": session_id}
