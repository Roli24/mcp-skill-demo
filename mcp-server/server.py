"""Local MCP server for the pr-review skill.

Runs entirely on your machine and talks to api.github.com directly. The
GitHub token lives only in *this process's* environment — it is never
sent to a third-party hosted MCP endpoint (e.g. api.githubcopilot.com).
Only the three actions the pr-review skill actually needs are exposed
here, not GitHub's full API surface.

Local smoke test:     GH_PAT=... python3 server.py
Register with Claude: see ../RUNBOOK.md (Step 3)
"""

import os
import sys

import requests
from mcp.server.fastmcp import FastMCP

GH_TOKEN = os.environ.get("GH_PAT")
if not GH_TOKEN:
    print(
        "GH_PAT is not set — export a fine-grained GitHub PAT "
        "(Contents: read, Pull requests: read & write) before starting "
        "this server.",
        file=sys.stderr,
    )
    sys.exit(1)

API = "https://api.github.com"
HEADERS = {
    "Authorization": f"Bearer {GH_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

mcp = FastMCP("pr-github")


def _pr(owner: str, repo: str, pr_number: int) -> dict:
    resp = requests.get(
        f"{API}/repos/{owner}/{repo}/pulls/{pr_number}", headers=HEADERS, timeout=15
    )
    resp.raise_for_status()
    return resp.json()


@mcp.tool()
def get_pr_diff(owner: str, repo: str, pr_number: int) -> str:
    """Fetch the unified diff for an open pull request."""
    resp = requests.get(
        f"{API}/repos/{owner}/{repo}/pulls/{pr_number}",
        headers={**HEADERS, "Accept": "application/vnd.github.v3.diff"},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.text


@mcp.tool()
def get_pr_checks(owner: str, repo: str, pr_number: int) -> str:
    """Fetch CI check-run results for a pull request's latest commit."""
    sha = _pr(owner, repo, pr_number)["head"]["sha"]

    resp = requests.get(
        f"{API}/repos/{owner}/{repo}/commits/{sha}/check-runs",
        headers=HEADERS,
        timeout=15,
    )
    resp.raise_for_status()
    runs = resp.json().get("check_runs", [])
    if not runs:
        return f"No check runs found for {sha[:7]}."
    return "\n".join(
        f"{r['name']}: {r['status']} ({r.get('conclusion') or 'pending'})" for r in runs
    )


@mcp.tool()
def post_review_comment(
    owner: str, repo: str, pr_number: int, path: str, line: int, body: str
) -> str:
    """Post one inline review comment on a pull request's diff."""
    sha = _pr(owner, repo, pr_number)["head"]["sha"]

    resp = requests.post(
        f"{API}/repos/{owner}/{repo}/pulls/{pr_number}/comments",
        headers=HEADERS,
        json={
            "body": body,
            "commit_id": sha,
            "path": path,
            "line": line,
            "side": "RIGHT",
        },
        timeout=15,
    )
    resp.raise_for_status()
    return f"Posted comment on {path}:{line} — {resp.json()['html_url']}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
