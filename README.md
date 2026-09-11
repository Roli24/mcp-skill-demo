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
    three tools over Streamable HTTP, gated by its own bearer token
    (`CONNECTOR_TOKEN`) that's separate from the GitHub token — claude.ai
    only ever sees the former, never `GH_PAT`.

See [`CLAUDE_AI_SETUP.md`](./CLAUDE_AI_SETUP.md) for the exact steps:
push the repo, deploy the connector, add it and the skill to claude.ai,
and run the review.
