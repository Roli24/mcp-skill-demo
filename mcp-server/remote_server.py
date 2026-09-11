"""MCP server for a claude.ai custom connector, using OAuth 2.1
(Authorization Code + PKCE) -- claude.ai's "Add custom connector" UI
currently only exposes OAuth fields (Authorization URL, Token URL,
Client ID, Client Secret), not a plain bearer-token box, so that's
what this implements: a small, single-tenant authorization server
sitting in front of the same three tools.

Three secrets, three purposes -- keep them separate:
  GH_PAT              your GitHub token. Only this host's env sees it;
                      claude.ai never does.
  OAUTH_CLIENT_SECRET the "Client Secret" you paste into claude.ai's
                      connector form, alongside OAUTH_CLIENT_ID. Proves
                      it's really claude.ai's server calling
                      /oauth/token, not a random script.
  CONSENT_PASSWORD    what *you* type into the one-time consent page in
                      your browser when claude.ai redirects you there
                      to approve the connector. Proves it's really you
                      clicking "allow", not anyone who finds the URL.

claude.ai only ever receives OAUTH_CLIENT_SECRET (once, at setup) and
the short-lived access/refresh tokens this server issues afterward --
never GH_PAT, never CONSENT_PASSWORD.

Run:
  export GH_PAT=...
  export OAUTH_CLIENT_SECRET=$(openssl rand -hex 32)
  export CONSENT_PASSWORD=$(openssl rand -hex 16)
  export PUBLIC_URL=https://your-deployed-host
  export OAUTH_REDIRECT_URIS=<redirect URI claude.ai shows you>
  python3 remote_server.py
"""

import base64
import hashlib
import html
import os
import secrets
import sys
import time
from urllib.parse import urlencode

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse

import github_tools as gh

GH_TOKEN = os.environ.get("GH_PAT")
CLIENT_ID = os.environ.get("OAUTH_CLIENT_ID", "pr-github-connector")
CLIENT_SECRET = os.environ.get("OAUTH_CLIENT_SECRET")
CONSENT_PASSWORD = os.environ.get("CONSENT_PASSWORD")
PUBLIC_URL = os.environ.get("PUBLIC_URL", "http://127.0.0.1:8000").rstrip("/")
REDIRECT_ALLOWLIST = {
    u.strip() for u in os.environ.get("OAUTH_REDIRECT_URIS", "").split(",") if u.strip()
}

if not GH_TOKEN or not CLIENT_SECRET or not CONSENT_PASSWORD:
    print(
        "Set GH_PAT, OAUTH_CLIENT_SECRET, and CONSENT_PASSWORD before "
        "starting. Generate the latter two yourself, e.g.:\n"
        "  export OAUTH_CLIENT_SECRET=$(openssl rand -hex 32)\n"
        "  export CONSENT_PASSWORD=$(openssl rand -hex 16)",
        file=sys.stderr,
    )
    sys.exit(1)

PORT = int(os.environ.get("PORT", 8000))

# --- in-memory OAuth state ---------------------------------------------
# Single-process demo store: fine for one deployment, one user. A
# restart clears every issued code/token, which just means re-approving
# the connector in claude.ai -- an acceptable tradeoff for a demo.
AUTH_CODES: dict[str, dict] = {}
ACCESS_TOKENS: dict[str, float] = {}
REFRESH_TOKENS: dict[str, float] = {}

CODE_TTL = 120
ACCESS_TOKEN_TTL = 3600
REFRESH_TOKEN_TTL = 60 * 60 * 24 * 30


def _new_token(store: dict, ttl: int) -> str:
    token = secrets.token_urlsafe(32)
    store[token] = time.time() + ttl
    return token


def _valid(store: dict, token: str) -> bool:
    exp = store.get(token)
    if exp is None:
        return False
    if exp < time.time():
        store.pop(token, None)
        return False
    return True


# --- the three MCP tools -------------------------------------------------
mcp = FastMCP("pr-github-remote", host="0.0.0.0", port=PORT, stateless_http=True)
mcp.settings.transport_security = TransportSecuritySettings(enable_dns_rebinding_protection=False)


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


# --- OAuth 2.1 authorization code + PKCE, single tenant ------------------

async def metadata_authorization_server(request: Request) -> JSONResponse:
    return JSONResponse(
        {
            "issuer": PUBLIC_URL,
            "authorization_endpoint": f"{PUBLIC_URL}/oauth/authorize",
            "token_endpoint": f"{PUBLIC_URL}/oauth/token",
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code", "refresh_token"],
            "code_challenge_methods_supported": ["S256"],
            "token_endpoint_auth_methods_supported": ["client_secret_post", "client_secret_basic"],
        }
    )


async def metadata_protected_resource(request: Request) -> JSONResponse:
    return JSONResponse({"resource": f"{PUBLIC_URL}/mcp", "authorization_servers": [PUBLIC_URL]})


CONSENT_FORM = """<!doctype html><title>Approve connector</title>
<body style="font-family:system-ui;max-width:420px;margin:64px auto">
<h2>Approve pr-github connector?</h2>
<p>claude.ai is requesting access to the pr-github tools
(get_pr_diff, get_pr_checks, post_review_comment).</p>
<form method="post">
<input type="hidden" name="client_id" value="{client_id}">
<input type="hidden" name="redirect_uri" value="{redirect_uri}">
<input type="hidden" name="state" value="{state}">
<input type="hidden" name="code_challenge" value="{code_challenge}">
<input type="hidden" name="code_challenge_method" value="{code_challenge_method}">
<label>Consent password<br><input type="password" name="password" autofocus></label><br><br>
<button type="submit">Approve</button>
</form>{error}
</body>"""


async def oauth_authorize(request: Request):
    params = request.query_params if request.method == "GET" else await request.form()

    client_id = params.get("client_id", "")
    redirect_uri = params.get("redirect_uri", "")
    state = params.get("state", "")
    code_challenge = params.get("code_challenge", "")
    code_challenge_method = params.get("code_challenge_method", "S256")

    if client_id != CLIENT_ID:
        return JSONResponse({"error": "invalid_client"}, status_code=400)
    if REDIRECT_ALLOWLIST and redirect_uri not in REDIRECT_ALLOWLIST:
        return JSONResponse({"error": "invalid_redirect_uri", "got": redirect_uri}, status_code=400)

    form_fields = dict(
        client_id=html.escape(client_id),
        redirect_uri=html.escape(redirect_uri),
        state=html.escape(state),
        code_challenge=html.escape(code_challenge),
        code_challenge_method=html.escape(code_challenge_method),
    )

    if request.method == "GET":
        return HTMLResponse(CONSENT_FORM.format(**form_fields, error=""))

    password = params.get("password", "")
    if not secrets.compare_digest(password, CONSENT_PASSWORD):
        return HTMLResponse(
            CONSENT_FORM.format(**form_fields, error="<p style='color:red'>Wrong password.</p>"),
            status_code=401,
        )

    code = secrets.token_urlsafe(24)
    AUTH_CODES[code] = {
        "redirect_uri": redirect_uri,
        "code_challenge": code_challenge,
        "exp": time.time() + CODE_TTL,
    }
    return RedirectResponse(f"{redirect_uri}?{urlencode({'code': code, 'state': state})}", status_code=302)


def _client_credentials(form: dict, request: Request) -> tuple[str, str]:
    cid, secret = form.get("client_id", ""), form.get("client_secret", "")
    if not cid and not secret:
        auth = request.headers.get("authorization", "")
        if auth.startswith("Basic "):
            try:
                decoded = base64.b64decode(auth[6:]).decode()
                cid, _, secret = decoded.partition(":")
            except Exception:
                pass
    return cid, secret


async def oauth_token(request: Request):
    form = dict(await request.form())
    cid, secret = _client_credentials(form, request)
    if cid != CLIENT_ID or not secrets.compare_digest(secret, CLIENT_SECRET):
        return JSONResponse({"error": "invalid_client"}, status_code=401)

    grant_type = form.get("grant_type")

    if grant_type == "authorization_code":
        entry = AUTH_CODES.pop(form.get("code", ""), None)
        if not entry or entry["exp"] < time.time():
            return JSONResponse({"error": "invalid_grant"}, status_code=400)
        if entry["redirect_uri"] != form.get("redirect_uri", ""):
            return JSONResponse({"error": "invalid_grant", "detail": "redirect_uri mismatch"}, status_code=400)

        if entry["code_challenge"]:
            digest = hashlib.sha256(form.get("code_verifier", "").encode()).digest()
            computed = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
            if computed != entry["code_challenge"]:
                return JSONResponse({"error": "invalid_grant", "detail": "PKCE mismatch"}, status_code=400)

        return JSONResponse(
            {
                "access_token": _new_token(ACCESS_TOKENS, ACCESS_TOKEN_TTL),
                "token_type": "Bearer",
                "expires_in": ACCESS_TOKEN_TTL,
                "refresh_token": _new_token(REFRESH_TOKENS, REFRESH_TOKEN_TTL),
            }
        )

    if grant_type == "refresh_token":
        if not _valid(REFRESH_TOKENS, form.get("refresh_token", "")):
            return JSONResponse({"error": "invalid_grant"}, status_code=400)
        return JSONResponse(
            {
                "access_token": _new_token(ACCESS_TOKENS, ACCESS_TOKEN_TTL),
                "token_type": "Bearer",
                "expires_in": ACCESS_TOKEN_TTL,
            }
        )

    return JSONResponse({"error": "unsupported_grant_type"}, status_code=400)


class BearerAuthMiddleware(BaseHTTPMiddleware):
    """Gates only /mcp -- the oauth/* and well-known routes must stay open
    for the flow that issues the token in the first place."""

    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/mcp"):
            auth = request.headers.get("authorization", "")
            token = auth[7:] if auth.startswith("Bearer ") else ""
            if not _valid(ACCESS_TOKENS, token):
                return JSONResponse({"error": "unauthorized"}, status_code=401)
        return await call_next(request)


app = mcp.streamable_http_app()
app.add_middleware(BearerAuthMiddleware)
app.add_route("/.well-known/oauth-authorization-server", metadata_authorization_server, methods=["GET"])
app.add_route("/.well-known/oauth-protected-resource", metadata_protected_resource, methods=["GET"])
app.add_route("/oauth/authorize", oauth_authorize, methods=["GET", "POST"])
app.add_route("/oauth/token", oauth_token, methods=["POST"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=PORT)
