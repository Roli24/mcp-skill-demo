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

## Step 3 — Connect the GitHub MCP server (ON CAMERA)

Generate a fine-grained GitHub PAT first (Settings → Developer settings →
Personal access tokens → Fine-grained), scoped to just this repo, with
`Contents: Read`, `Pull requests: Read and write`, `Issues: Read`.
**Redact this token in the recording** — either blur it or type it into an
env var off-screen and reference `$GH_PAT` on screen instead.

```bash
export GH_PAT="ghp_xxx"   # do this off camera / blur it

claude mcp add --transport http github \
  https://api.githubcopilot.com/mcp \
  -H "Authorization: Bearer $GH_PAT"
```

Verify it's connected:

```bash
claude mcp list
```

Talking point: *"This one command gave Claude a live connection to GitHub's
API — it can now read issues, PRs, CI status, file contents, directly,
without me copy-pasting anything into the chat."*

## Step 4 — Ask Claude to pull PR context via MCP (ON CAMERA)

Inside `claude` (run it from `~/mcp-skill-demo`):

```
what's the status of PR #1 in Roli24/mcp-skill-demo — show me the diff and any CI checks
```

Claude uses the GitHub MCP server's tools to fetch the PR diff and CI status
live — no local checkout needed. Narrate: *this is the "server" half of MCP —
it's giving Claude eyes on GitHub's live data.*

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

Per the skill's step 4, this posts the findings as inline PR review
comments using the *same* GitHub MCP connection from Step 3. This is the
"end-to-end" beat: MCP supplied the live context in, the skill decided
what to say, and the same server pushes the result back out — all inside
one Claude Code session, no manual copy-paste either direction.

---

## Cleanup after recording

```bash
claude mcp remove github     # revoke the local MCP registration
```

Then go to GitHub → Settings → Developer settings → revoke the fine-grained
PAT you created for the demo.
