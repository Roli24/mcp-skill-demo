"""MCP server for a claude.ai custom connector.

claude.ai runs in a browser and can't spawn a local process, so it
needs a server reachable over HTTPS — this is that server, exposing
three tools over Streamable HTTP. Deploy this yourself; it is still
your code, on infrastructure you choose, not a third party's.

Two separate secrets, two separate trust boundaries:
  - GH_PAT           your GitHub token. Lives only in this host's env,
                      used only for this server's own calls to
                      api.github.com. claude.ai never sees it.
  - CONNECTOR_TOKEN   a bearer secret YOU generate (e.g. `openssl rand
                      -hex 32`), unrelated to GitHub. claude.ai must
                      send it on every request or this server refuses
                      to do anything. This is the one secret you paste
                      into claude.ai's connector settings — rotate it
                      any time by changing the env var and restarting.

This is a single-tenant demo: one GH_PAT, one CONNECTOR_TOKEN, meant
for your own use. Don't hand the connector URL + token to anyone else
without rethinking that.

Run:  GH_PAT=... CONNECTOR_TOKEN=... python3 remote_server.py
      (then put it behind HTTPS — a platform's built-in TLS, or a
      reverse proxy — before pointing claude.ai at it)
"""

import os
import secrets
import sys

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

import github_tools as gh

GH_TOKEN = os.environ.get("GH_PAT")
CONNECTOR_TOKEN = os.environ.get("CONNECTOR_TOKEN")

if not GH_TOKEN or not CONNECTOR_TOKEN:
    print(
        "Set both GH_PAT and CONNECTOR_TOKEN before starting the remote "
        "server. Generate CONNECTOR_TOKEN yourself, e.g.:\n"
        "  export CONNECTOR_TOKEN=$(openssl rand -hex 32)",
        file=sys.stderr,
    )
    sys.exit(1)

PORT = int(os.environ.get("PORT", 8000))

mcp = FastMCP("pr-github-remote", host="0.0.0.0", port=PORT, stateless_http=True)

# The SDK's DNS-rebinding guard checks the Host/Origin headers against
# an allowlist meant for a server bound to localhost with one trusted
# client. This server is deliberately public, and BearerAuthMiddleware
# below -- which runs before this check -- is the real gate, so turn
# the host allowlist off rather than fight it with an unmatchable "*".
mcp.settings.transport_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=False,
)


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


class BearerAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        expected = f"Bearer {CONNECTOR_TOKEN}"
        actual = request.headers.get("authorization", "")
        if not secrets.compare_digest(actual, expected):
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        return await call_next(request)


app = mcp.streamable_http_app()
app.add_middleware(BearerAuthMiddleware)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=PORT)
