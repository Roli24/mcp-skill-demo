# mcp-skill-demo

A tiny storefront API used to record a YouTube demo of a **claude.ai
Connector + Skill** working together end to end.

- **`main`** — a small Flask + SQLite API with a `/login` endpoint. Safe:
  the login query is parameterized.
- **`feature/admin-user-search`** — a PR branch that adds an admin
  "search users" endpoint. It contains a deliberate SQL-injection bug,
  used to show the **`pr-review` skill** (see
  [`skill/pr-review/SKILL.md`](./skill/pr-review/SKILL.md)) catching it.
- **`mcp-server/`** — the connector's server code:
  - [`github_tools.py`](./mcp-server/github_tools.py) — the GitHub REST
    logic (`get_pr_diff`, `get_pr_checks`, `post_review_comment`).
  - [`remote_server.py`](./mcp-server/remote_server.py) — exposes those
    three tools over Streamable HTTP, behind its own single-tenant
    OAuth 2.1 (authorization code + PKCE) authorization server —
    claude.ai's custom-connector form expects Authorization/Token URLs
    and a Client ID/Secret, not a plain bearer token, so that's what's
    implemented. Three separate secrets keep the trust boundaries
    apart: `GH_PAT` (never leaves the host), `OAUTH_CLIENT_SECRET`
    (proves it's really claude.ai calling `/oauth/token`), and
    `CONSENT_PASSWORD` (proves it's really you approving the connector
    in your browser).

See [`CLAUDE_AI_SETUP.md`](./CLAUDE_AI_SETUP.md) for the exact steps:
push the repo, deploy the connector, add it and the skill to claude.ai,
and run the review.
