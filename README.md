# mcp-skill-demo

A tiny storefront API used to record a YouTube demo of **MCP servers + Skills**
working together in Claude Code.

- **`main`** — a small Flask + SQLite API with a `/login` endpoint. Safe:
  the login query is parameterized.
- **`feature/admin-user-search`** — a PR branch that adds an admin
  "search users" endpoint. It contains a deliberate SQL-injection bug,
  used to show the **`pr-review` skill** (see
  [`.claude/skills/pr-review/SKILL.md`](./.claude/skills/pr-review/SKILL.md))
  catching it.
- **`mcp-server/`** — a small custom MCP server ([`server.py`](./mcp-server/server.py))
  that runs locally and talks to `api.github.com` directly, exposing just
  three tools (`get_pr_diff`, `get_pr_checks`, `post_review_comment`).
  Your GitHub token stays in this process — it's never sent to a
  third-party hosted MCP endpoint.

See [`RUNBOOK.md`](./RUNBOOK.md) for the exact steps to record.
