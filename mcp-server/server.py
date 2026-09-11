"""Local MCP server for the pr-review skill, for use with Claude Code.

Runs entirely on your machine and talks to api.github.com directly via
github_tools.py. The GitHub token lives only in *this process's*
environment — it is never sent to a third-party hosted MCP endpoint.

Local smoke test:     GH_PAT=... python3 server.py
Registration:         declarative via ../.mcp.json, committed in this repo.
"""

import os
import sys

from mcp.server.fastmcp import FastMCP

import github_tools as gh

GH_TOKEN = os.environ.get("GH_PAT")
if not GH_TOKEN:
    print(
        "GH_PAT is not set — export a fine-grained GitHub PAT "
        "(Contents: read, Pull requests: read & write) before starting "
        "this server.",
        file=sys.stderr,
    )
    sys.exit(1)

mcp = FastMCP("pr-github")


@mcp.tool()
def get_pr_diff(owner: str, repo: str, pr_number: int) -> str:
    """Fetch the unified diff for an open pull request."""
    return gh.get_pr_diff(GH_TOKEN, owner, repo, pr_number)


@mcp.tool()
def get_pr_checks(owner: str, repo: str, pr_number: int) -> str:
    """Fetch CI check-run results for a pull request's latest commit."""
    return gh.get_pr_checks(GH_TOKEN, owner, repo, pr_number)


@mcp.tool()
def post_review_comment(
    owner: str, repo: str, pr_number: int, path: str, line: int, body: str
) -> str:
    """Post one inline review comment on a pull request's diff."""
    return gh.post_review_comment(GH_TOKEN, owner, repo, pr_number, path, line, body)


if __name__ == "__main__":
    mcp.run(transport="stdio")
