# mcp-skill-demo

A tiny storefront API used to record a YouTube demo of **MCP servers + Skills**
working together in Claude Code.

- **`main`** — a small Flask + SQLite API with a `/login` endpoint. Safe:
  the login query is parameterized.
- **`feature/admin-user-search`** — a PR branch that adds an admin
  "search users" endpoint. It contains a deliberate SQL-injection bug,
  used to show the **`pr-review` skill** (see
  [`.claude/skills/pr-review/SKILL.md`](./.claude/skills/pr-review/SKILL.md))
  catching it, with the **GitHub MCP server** supplying Claude live PR/CI
  context and posting findings back.

See [`RUNBOOK.md`](./RUNBOOK.md) for the exact steps to record.
