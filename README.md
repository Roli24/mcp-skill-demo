# mcp-skill-demo

**Claude reviews a real GitHub pull request for a real security bug —
live, out loud, with nothing pasted in by hand.** This repo is the
whole thing: the buggy code, the MCP server that gives Claude eyes on
GitHub, and the Skill that tells it what to actually check for. Runs
entirely in Claude Code — no hosting, no browser, no third-party server.

▶️ **[See the bug it catches: PR #1](https://github.com/Roli24/mcp-skill-demo/pull/1)**

---

## What's actually going on here

Two pieces, doing two different jobs:

- **An MCP server** — a small program *you* write and run, that gives
  Claude a live connection to something outside the chat (here:
  GitHub). Without it, Claude only knows what you paste in.
- **A Skill** (`SKILL.md`) — the checklist. It tells Claude *what to
  look for* and *when to use the connection*, so "review this PR"
  means the same thing every time, not whatever you happen to type
  that day.

```mermaid
flowchart LR
    GH[("GitHub<br/>PR #1 · CI checks")]
    MCP["pr-github MCP server<br/><i>your code, 3 tools</i>"]
    C["Claude Code<br/><i>the session</i>"]
    SK["pr-review Skill<br/><i>the checklist</i>"]

    GH -- "diff · CI status" --> MCP
    MCP -- "get_pr_diff / get_pr_checks" --> C
    C -- "post_review_comment" --> MCP
    MCP -- "review comments" --> GH
    SK -. "loaded on /pr-review" .-> C
```

The MCP server never decides *what's wrong* with the code — it just
fetches and posts. The Skill never touches GitHub directly — it just
reasons. Neither one does the whole job alone.

## Where the two files actually live

```
.mcp.json                        <- Claude Code reads this on startup;
                                     declares & launches the MCP server
mcp-server/server.py             <- the server: 3 tools, stdio transport
mcp-server/github_tools.py       <- the GitHub REST calls those tools use
.claude/skills/pr-review/SKILL.md <- auto-discovered; registers /pr-review
```

`.mcp.json` says *what's available* (spawns `server.py`, gets back
`get_pr_diff` / `get_pr_checks` / `post_review_comment`). `SKILL.md`
says *what to do with it* (the checklist, run when you type
`/pr-review`). They never talk to each other directly — they meet
inside Claude's own reasoning.

## The bug it finds

[`app.py`](./app.py)'s `search_users()` endpoint (added in PR #1)
builds SQL with string concatenation:

```python
sql = "SELECT id, username, is_admin FROM users WHERE username LIKE '%" + query + "%'"
```

— classic injection — and the PR description quietly defers the
missing admin-role check to "a follow-up ticket." Both are exactly the
kind of thing that's easy to wave through in a fast review and easy
for a checklist to catch every time.

## Install Claude Code

Skip this if `claude --version` already works. Otherwise:

**macOS / Linux / WSL** — native installer, no Node.js required:
```bash
curl -fsSL https://claude.ai/install.sh | bash
```
macOS alternative, if you prefer Homebrew:
```bash
brew install claude-code
```

**Windows** — native installer, in PowerShell (no WSL, Node, or npm needed):
```powershell
irm https://claude.ai/install.ps1 | iex
```

Either way, confirm it worked:
```bash
claude --version
```

You'll also need Python 3 and `git` on your PATH — this demo's MCP
server is a Python script, and you'll be cloning the repo below.

## Run it yourself

Full steps, including the exact `.mcp.json` field-by-field, are in
[`RUNBOOK.md`](./RUNBOOK.md). Short version:

```bash
git clone https://github.com/Roli24/mcp-skill-demo && cd mcp-skill-demo
cd mcp-server && python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt && cd ..

export GH_PAT="your-fine-grained-github-pat"   # Contents:Read, PRs:Read&write
claude   # approve the pr-github MCP server when prompted

# inside the session:
/pr-review PR #1
/pr-review PR #1 --comment   # posts findings back to the PR
```

> Windows note: the venv activation step is
> `mcp-server\venv\Scripts\activate` (PowerShell/cmd) instead of
> `source mcp-server/venv/bin/activate`, and set the token with
> `$env:GH_PAT="your-token"` instead of `export`. `.mcp.json`'s
> `${CLAUDE_PROJECT_DIR:-.}/mcp-server/venv/bin/python3` path assumes a
> Unix-style venv layout — on Windows that's
> `mcp-server/venv/Scripts/python.exe`; adjust `.mcp.json` accordingly
> if you're recording on Windows rather than macOS/Linux.

## Why bother wiring this up

- **Live grounding, not copy-paste** — Claude reads the real diff and
  CI status. Nothing pasted by hand, nothing goes stale mid-review.
- **A repeatable checklist** — the Skill runs the same correctness/
  security pass every time, not a fresh ad hoc prompt.
- **You control the blast radius** — three tools, not GitHub's whole
  API. A bug in the Skill can't reach further than that.
- **The loop closes** — the same server that pulled the PR in posts
  findings back as inline comments. Starts and ends on GitHub.
- **Your token never leaves your machine** — no hosted MCP endpoint,
  no third party ever sees it.

## Where it actually falls short

- **A credential still has to live somewhere** — your shell env, in
  this case. It needs scoping and rotation like any secret.
- **Cost and latency scale per call** — fine for reviewing one PR on
  camera, not a drop-in replacement for a CI bot reviewing hundreds.
- **First pass, not sign-off** — it can miss a real bug or flag a
  fine line as risky. A human still holds the merge button.
- **Only works where Claude Code runs** — it's a local subprocess, so
  it needs a machine with Python and this repo checked out.
- **More moving parts than a plain prompt** — worth it for a
  repeatable workflow, overkill for a one-off question.

## Repo layout

```
app.py, test_app.py             the buggy demo API (main = safe, feature/admin-user-search = bug)
.claude/skills/pr-review/       the Skill
mcp-server/github_tools.py      GitHub REST logic
mcp-server/server.py            the MCP server (stdio transport)
.mcp.json                       declarative registration, committed
RUNBOOK.md                      exact recording steps
```
