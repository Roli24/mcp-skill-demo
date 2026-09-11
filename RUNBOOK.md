# Recording runbook: MCP server + Skill in Claude Code, end to end

Repo: `~/mcp-skill-demo` · GitHub account: `github.com/Roli24`

`main` is always clean and safe — no bug lives there permanently. Each
recording gets a *fresh* buggy PR via `make-demo-pr.sh`, so the demo is
always reviewing something real and unmerged, never a stale fixture.

Do Steps 1–2 once *before* recording (dead air while `gh` prompts for
auth, or while a PR opens, is not fun to watch); record everything
from Step 3 onward live.

---

## Step 1 — Push the repo to GitHub (one-time, do this before recording)

```bash
cd ~/mcp-skill-demo
gh auth login   # once, if you haven't
git push -u origin main   # only needed the very first time
```

## Step 2 — Open a fresh demo PR (do this before each recording)

```bash
./make-demo-pr.sh
```

This checks out a new branch off `main`, adds the vulnerable
`search_users` endpoint, pushes it, and opens a PR — printing its
number at the end (e.g. `#4`). **Note that number — you'll say it on
camera and use it in Steps 4–5.** Running it again later opens another
fresh PR on a new branch; old ones don't need cleaning up before a new
run, though see *Cleanup* at the bottom for tidying up after you're done.

---

## Step 3 — Set up the local MCP server, then connect it (ON CAMERA)

We're not using GitHub's hosted MCP endpoint — that would mean your PAT
rides in an `Authorization` header sent to `api.githubcopilot.com` on
every call. `mcp-server/server.py` + `mcp-server/github_tools.py` are
under 150 lines total, readable end to end: they run on your machine,
call `api.github.com` directly, and expose exactly three tools
(`get_pr_diff`, `get_pr_checks`, `post_review_comment`). The token
never leaves this process.

```bash
cd ~/mcp-skill-demo/mcp-server
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

Generate a fine-grained GitHub PAT (Settings → Developer settings →
Personal access tokens → Fine-grained), scoped to just this repo, with
`Contents: Read`, `Pull requests: Read and write`.
**Redact this token in the recording** — either blur it or type it into
an env var off-screen and reference `$GH_PAT` on screen instead.

This repo already commits [`.mcp.json`](./.mcp.json), so the wiring is
declarative — no `claude mcp add` needed:

```jsonc
{
  "mcpServers": {
    "pr-github": {
      // Claude Code spawns MCP servers with no defined cwd, so relative
      // paths never resolve -- always anchor to ${CLAUDE_PROJECT_DIR}.
      // Command points at the *venv's* python3, since that's where
      // requirements.txt actually got installed just above.
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
MCP servers — pr-github. Approve?"* — approve it on camera.

Verify, and that only your three tools are exposed:

```bash
claude mcp list
```

(Equivalent one-off command, if you'd rather register it outside the
repo instead of via `.mcp.json`: `claude mcp add pr-github -e
GH_PAT="$GH_PAT" -- ~/mcp-skill-demo/mcp-server/venv/bin/python3
~/mcp-skill-demo/mcp-server/server.py`.)

## Step 4 — Ask Claude to pull PR context via MCP (ON CAMERA)

Inside `claude` (run it from `~/mcp-skill-demo`), using the PR number
`make-demo-pr.sh` printed in Step 2:

```
what's the status of PR #<N> in Roli24/mcp-skill-demo — show me the diff and any CI checks
```

Claude calls `get_pr_diff` / `get_pr_checks` on the `pr-github` server —
watch for the tool-call names in the transcript, that's the beat where
you point out *these are the exact three tools we just wrote, nothing
more*.

## Step 5 — Run the pr-review skill against the PR (ON CAMERA)

This repo ships its own skill at `.claude/skills/pr-review/SKILL.md` —
open that file on screen for a few seconds first before invoking it:

```
/pr-review PR #<N>
```

Expected: the skill pulls the diff via the MCP server (Step 3/4's
connection, not a local checkout), then flags the string-concatenated
SQL in `search_users` (SQL injection) and the missing admin/auth check
on that endpoint. Let it finish and read the findings out loud — this
is the payoff shot.

Optional, to show it posting back to GitHub:

```
/pr-review PR #<N> --comment
```

This calls `post_review_comment` — the third tool — using the *same*
local server from Step 3. MCP supplied the live context in, the skill
decided what to say, and the same server pushes the result back out —
all inside one Claude Code session, no manual copy-paste either
direction, and no token handed to anyone but GitHub itself.

---

## Cleanup after recording

```bash
claude mcp remove pr-github     # revoke the local MCP registration

# close out the demo PR make-demo-pr.sh opened and delete its branch:
gh pr close <N> --delete-branch
git checkout main
```

Then go to GitHub → Settings → Developer settings → revoke the
fine-grained PAT you created for the demo.
