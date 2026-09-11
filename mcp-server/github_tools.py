"""GitHub REST calls used by server.py's three MCP tools. Kept in its
own module so server.py stays focused on the stdio/MCP wiring, not
GitHub's API shape.
"""

import requests

API = "https://api.github.com"


def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _pr(token: str, owner: str, repo: str, pr_number: int) -> dict:
    resp = requests.get(
        f"{API}/repos/{owner}/{repo}/pulls/{pr_number}", headers=_headers(token), timeout=15
    )
    resp.raise_for_status()
    return resp.json()


def get_pr_diff(token: str, owner: str, repo: str, pr_number: int) -> str:
    resp = requests.get(
        f"{API}/repos/{owner}/{repo}/pulls/{pr_number}",
        headers={**_headers(token), "Accept": "application/vnd.github.v3.diff"},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.text


def get_pr_checks(token: str, owner: str, repo: str, pr_number: int) -> str:
    sha = _pr(token, owner, repo, pr_number)["head"]["sha"]
    resp = requests.get(
        f"{API}/repos/{owner}/{repo}/commits/{sha}/check-runs",
        headers=_headers(token),
        timeout=15,
    )
    resp.raise_for_status()
    runs = resp.json().get("check_runs", [])
    if not runs:
        return f"No check runs found for {sha[:7]}."
    return "\n".join(
        f"{r['name']}: {r['status']} ({r.get('conclusion') or 'pending'})" for r in runs
    )


def post_review_comment(
    token: str, owner: str, repo: str, pr_number: int, path: str, line: int, body: str
) -> str:
    sha = _pr(token, owner, repo, pr_number)["head"]["sha"]
    resp = requests.post(
        f"{API}/repos/{owner}/{repo}/pulls/{pr_number}/comments",
        headers=_headers(token),
        json={"body": body, "commit_id": sha, "path": path, "line": line, "side": "RIGHT"},
        timeout=15,
    )
    resp.raise_for_status()
    return f"Posted comment on {path}:{line} — {resp.json()['html_url']}"
