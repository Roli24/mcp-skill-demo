# Recording runbook: MCP server + Skill, end to end

Repo: `~/mcp-skill-demo` · GitHub account: `github.com/Roli24`

This walks through the exact commands for the demo segment of the video.
Do the GitHub push once *before* recording (dead air while `gh` prompts for
auth is not fun to watch); record everything from Step 3 onward live.

---

## Step 1 — Push the repo to GitHub (do this before recording)

```bash
cd ~/mcp-skill-demo

# Install gh if you don't have it: brew install gh
gh auth login

# Creates the repo under your account and pushes main
gh repo create Roli24/mcp-skill-demo --public --source=. --remote=origin --push
```

## Step 2 — Open the PR (do this before recording)

```bash
git push -u origin feature/admin-user-search

gh pr create \
  --title "Add admin user search endpoint" \
  --body "Adds GET /admin/users/search so support staff can look up an \
account by partial username. Admin-role check is tracked in a follow-up \
ticket — out of scope here." \
  --base main --head feature/admin-user-search
```

Note the PR number `gh pr create` prints (e.g. `#1`) — you'll say it on camera.

---

## Step 3 — Stand up your own MCP server, then connect it (ON CAMERA)

We're deliberately *not* using GitHub's hosted MCP endpoint here — that
would mean putting your PAT in an `Authorization` header sent to
`api.githubcopilot.com` on every call. Instead `mcp-server/server.py` is
~90 lines you can read end to end: it runs on your machine, calls
`api.github.com` directly, and exposes exactly three tools
(`get_pr_diff`, `get_pr_checks`, `post_review_comment`) — not GitHub's
whole API surface. The token never leaves this process.

```bash
cd ~/mcp-skill-demo/mcp-server
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

Generate a fine-grained GitHub PAT (Settings → Developer settings →
Personal access tokens → Fine-grained), scoped to just this repo, with
`Contents: Read`, `Pull requests: Read and write`.
**Redact this token in the recording** — either blur it or type it into an
env var off-screen and reference `$GH_PAT` on screen instead.

This repo already commits [`.mcp.json`](./.mcp.json), so the wiring is
declarative — no `claude mcp add` needed:

```jsonc
{
  "mcpServers": {
    "pr-github": {
      // Claude Code spawns MCP servers with no defined cwd, so relative
      // paths never resolve -- always anchor to ${CLAUDE_PROJECT_DIR}.
      // Command points at the *venv's* python3, since that's where
      // requirements.txt actually got installed in Step 3.
      "command": "${CLAUDE_PROJECT_DIR:-.}/mcp-server/venv/bin/python3",
      "args": ["${CLAUDE_PROJECT_DIR:-.}/mcp-server/server.py"],
      "env": { "GH_PAT": "${GH_PAT}" }   // expanded from your shell, never written to disk
    }
  }
}
```

```bash
export GH_PAT="ghp_xxx"   # do this off camera / blur it
cd ~/mcp-skill-demo
claude
```

On first launch Claude Code prompts: *"This project wants to run these
MCP servers — pr-github. Approve?"* — approve it on camera. That
prompt is the whole point: nothing runs without you seeing what it is
first.

(Equivalent one-off command, if you'd rather register it outside the
repo instead of via `.mcp.json`: `claude mcp add pr-github -e
GH_PAT="$GH_PAT" -- python3 ~/mcp-skill-demo/mcp-server/server.py`.)

Verify it's connected, and that only your three tools are exposed:

```bash
claude mcp list
```

Talking point: *"I'm not handing my GitHub token to someone else's
server. This one is mine — three tools, ninety lines, running right
here — and I can read exactly what it does before I trust it with a
token."*

> If `-e` doesn't stick on your Claude Code version, `export GH_PAT=...`
> in the same shell before running `claude` and drop the `-e` flag —
> the server reads it from its inherited environment either way.

## Step 4 — Ask Claude to pull PR context via MCP (ON CAMERA)

Inside `claude` (run it from `~/mcp-skill-demo`):

```
what's the status of PR #1 in Roli24/mcp-skill-demo — show me the diff and any CI checks
```

Claude calls `get_pr_diff` and `get_pr_checks` on the `pr-github` server —
watch for the tool-call names in the transcript, that's the beat where you
point out *these are the exact three tools we just wrote, nothing more*.
Narrate: *this is the "server" half of MCP — it's giving Claude eyes on
GitHub's live data, through code I control.*

## Step 5 — Run the pr-review skill against the PR (ON CAMERA)

This repo ships its own skill at `.claude/skills/pr-review/SKILL.md` —
open that file on screen for a few seconds first ("here's the checklist
Claude is about to run") before invoking it:

```
/pr-review PR #1
```

Expected: the skill's own instructions tell Claude to pull the diff via
the GitHub MCP server (Step 3/4's connection, not a local checkout), then
flag the string-concatenated SQL in `search_users` (SQL injection) as a
correctness/security finding, and also flag the missing admin/auth check
on that endpoint. Let it finish and read the findings out loud on
camera — this is the payoff shot.

Optional, if you want to show it posting back to GitHub:

```
/pr-review PR #1 --comment
```

Per the skill's step 4, this calls `post_review_comment` — the third
tool — using the *same* local server from Step 3. This is the
"end-to-end" beat: your MCP server supplied the live context in, the
skill decided what to say, and the same server pushes the result back
out — all inside one Claude Code session, no manual copy-paste either
direction, and no token handed to anyone but GitHub itself.

---

## Cleanup after recording

```bash
claude mcp remove pr-github     # revoke the local MCP registration
```

Then go to GitHub → Settings → Developer settings → revoke the fine-grained
PAT you created for the demo.
