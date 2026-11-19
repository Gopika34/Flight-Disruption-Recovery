"""Standards-based MCP client for the local read-only GitHub MCP server."""
from __future__ import annotations
import os, sys, time
from typing import Any
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from app.core.auth import Principal
from app.core.authz import has_permission
from app.core.audit import record_audit
from app.services.github_connector import get_access_token, get_access_token_async

ALLOWED_TOOLS = {"list_repositories", "read_repository_file", "search_code", "list_issues"}

async def _session_call(principal: Principal, operation: str, arguments: dict | None = None):
    token = await get_access_token_async(principal)
    if not token:
        raise PermissionError("Connect GitHub before using GitHub tools")
    if operation not in ALLOWED_TOOLS or not has_permission(principal, f"mcp:github:{operation}"):
        raise PermissionError("This GitHub MCP tool is not permitted for this account")
    started = time.monotonic()
    outcome = "error"
    try:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        # Preserve platform variables (notably SystemRoot on Windows) while
        # passing the per-user GitHub credential only to this child process.
        env = dict(os.environ)
        env["PYTHONPATH"] = backend_dir
        env["GITHUB_ACCESS_TOKEN"] = token
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "app.mcp.github_server"],
            env=env,
            cwd=backend_dir,
        )
        async with stdio_client(params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                available = await session.list_tools()
                names = {item.name for item in available.tools}
                if operation not in names:
                    raise RuntimeError(f"MCP server did not expose {operation}")
                result = await session.call_tool(operation, arguments or {})
                if getattr(result, "isError", False):
                    raise RuntimeError("GitHub MCP tool returned an error")
                content = []
                for item in getattr(result, "content", []):
                    if getattr(item, "type", None) == "text":
                        content.append(item.text)
                    else:
                        content.append(str(item))
                outcome = "success"
                return "\n".join(content) if content else str(result.structuredContent or {})
    finally:
        record_audit(owner_id=principal.owner_id, action="mcp.tool.execute",
                     resource=f"github:{operation}", outcome=outcome,
                     metadata={"duration_ms": round((time.monotonic()-started)*1000)})

async def run_tool(principal: Principal, name: str, args: dict[str, Any]):
    return await _session_call(principal, name, args)

class GitHubToolInput(BaseModel):
    tool_name: str = Field(description="One of the available read-only GitHub MCP tools")
    arguments_json: str = Field(default="{}", description="JSON object containing tool arguments")

def langchain_tool_for(principal: Principal):
    async def execute(tool_name: str, arguments_json: str = "{}") -> str:
        import json
        try:
            arguments = json.loads(arguments_json)
        except json.JSONDecodeError as exc:
            raise ValueError("arguments_json must be a valid JSON object") from exc
        if not isinstance(arguments, dict):
            raise ValueError("arguments_json must decode to an object")
        return await run_tool(principal, tool_name, arguments)
    return StructuredTool.from_function(
        coroutine=execute,
        name="github_mcp_execute",
        description=(
            "Execute one authorized read-only GitHub MCP tool. tool_name must be one of: "
            "list_repositories (arguments: {per_page?: integer}), "
            "read_repository_file (arguments: {owner: string, repo: string, path: string, ref?: string}), "
            "search_code (arguments: {query: string, per_page?: integer}), "
            "list_issues (arguments: {owner: string, repo: string, state?: open|closed|all, per_page?: integer}). "
            "Pass arguments_json as a JSON object string. No write operations are exposed."
        ),
        args_schema=GitHubToolInput,
    )

async def list_tools(principal: Principal):
    """Return the fixed allow-listed tool catalog exposed by our local MCP server."""
    token = get_access_token(principal)
    if not token:
        return []
    return sorted(name for name in ALLOWED_TOOLS if has_permission(principal, f"mcp:github:{name}"))

# Legacy compatibility for older imports. New code must call run_tool with a real principal.
def allowed_tool_names(tools):
    return [t.get("name") for t in tools if t.get("name") in ALLOWED_TOOLS]
