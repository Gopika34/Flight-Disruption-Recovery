"""Local read-only GitHub MCP server. Started as a child process by the API."""
import os
import re
import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("flightguard-github-readonly")


def _valid_repo_part(value: str) -> bool:
    return value not in {".", ".."} and bool(re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", value or ""))

def _github(path: str, params: dict | None = None):
    token = os.getenv("GITHUB_ACCESS_TOKEN", "")
    if not token:
        raise RuntimeError("GitHub credential is unavailable")
    response = httpx.get(
        f"https://api.github.com{path}",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28"},
        params=params, timeout=15.0,
    )
    response.raise_for_status()
    return response.json()

@mcp.tool()
def list_repositories(per_page: int = 20) -> list:
    """List repositories visible to the connected GitHub user (read-only)."""
    per_page = max(1, min(int(per_page), 50))
    data = _github("/user/repos", {"per_page": per_page, "sort": "updated"})
    return [{"name": r.get("full_name"), "private": r.get("private"),
             "description": r.get("description"), "html_url": r.get("html_url")}
            for r in data]

@mcp.tool()
def read_repository_file(owner: str, repo: str, path: str, ref: str | None = None) -> dict:
    """Read a text file from a repository. Does not modify repository contents."""
    if not _valid_repo_part(owner) or not _valid_repo_part(repo) or not path or path.startswith("/") or ".." in path.split("/"):
        raise ValueError("Invalid repository owner, name or file path")
    data = _github(f"/repos/{owner}/{repo}/contents/{path}", {"ref": ref} if ref else None)
    import base64
    if data.get("encoding") != "base64":
        return {"name": data.get("name"), "download_url": data.get("download_url"), "content": "Unsupported file encoding"}
    raw = base64.b64decode(data.get("content", "").replace("\n", ""))
    return {"name": data.get("name"), "content": raw[:200_000].decode("utf-8", errors="replace")}

@mcp.tool()
def search_code(query: str, per_page: int = 10) -> dict:
    """Search code in repositories accessible to the connected user."""
    if not query.strip():
        raise ValueError("Search query is required")
    return _github("/search/code", {"q": query[:200], "per_page": max(1, min(per_page, 20))})

@mcp.tool()
def list_issues(owner: str, repo: str, state: str = "open", per_page: int = 20) -> list:
    """List repository issues. Pull requests are excluded."""
    if not _valid_repo_part(owner) or not _valid_repo_part(repo):
        raise ValueError("Invalid repository owner or name")
    if state not in {"open", "closed", "all"}:
        raise ValueError("state must be open, closed, or all")
    data = _github(f"/repos/{owner}/{repo}/issues", {"state": state, "per_page": max(1, min(per_page, 50))})
    return [{"number": x.get("number"), "title": x.get("title"), "state": x.get("state"),
             "html_url": x.get("html_url"), "created_at": x.get("created_at")}
            for x in data if "pull_request" not in x]

if __name__ == "__main__":
    mcp.run(transport="stdio")
