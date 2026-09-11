# mcp-skill-demo

A tiny storefront API used to record a YouTube demo of an **MCP server +
Skill** working together end to end — shown two ways: locally in Claude
Code, and remotely as a claude.ai connector.

- **`main`** — a small Flask + SQLite API with a `/login` endpoint. Safe:
  the login query is parameterized.
- **`feature/admin-user-search`** — a PR branch that adds an admin
  "search users" endpoint. It contains a deliberate SQL-injection bug,
  used to show the **`pr-review` skill** (see
  [`.claude/skills/pr-review/SKILL.md`](./.claude/skills/pr-review/SKILL.md))
  catching it.
- **`mcp-server/github_tools.py`** — the shared GitHub REST logic
  (`get_pr_diff`, `get_pr_checks`, `post_review_comment`) used by both
  servers below, so they can't drift into different behavior.
  - **[`server.py`](./mcp-server/server.py)** — stdio transport, for
    Claude Code. Runs on your machine via [`.mcp.json`](./.mcp.json);
    your GitHub token never leaves this process. → [`RUNBOOK.md`](./RUNBOOK.md)
  - **[`remote_server.py`](./mcp-server/remote_server.py)** — Streamable
    HTTP transport with its own OAuth 2.1 authorization server, for a
    claude.ai custom connector. → [`CLAUDE_AI_SETUP.md`](./CLAUDE_AI_SETUP.md)

Pick whichever path matches what you're recording — both use the same
`SKILL.md` and the same GitHub logic underneath.
