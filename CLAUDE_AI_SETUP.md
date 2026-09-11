# Connecting this demo to claude.ai (Connector + Skill)

claude.ai runs in a browser, so it needs a server reachable over
HTTPS — `mcp-server/remote_server.py` exposes three tools
(`get_pr_diff`, `get_pr_checks`, `post_review_comment`) over Streamable
HTTP for exactly that.

Two independent secrets are involved. Keep them mentally separate:

| Secret | What it's for | Who ever sees it |
|---|---|---|
| `GH_PAT` | Talks to `api.github.com` | Only your deployed server's environment |
| `CONNECTOR_TOKEN` | Gates every request to *your* server | You, and claude.ai's connector config |

claude.ai never receives `GH_PAT`. It only receives `CONNECTOR_TOKEN` —
a secret that authenticates to your server, not to GitHub. If someone
got hold of `CONNECTOR_TOKEN`, the worst they can do is call your three
tools; they still can't do anything GitHub-side you haven't already
scoped `GH_PAT` to allow.

## 0. Push the repo and open the demo PR

```bash
cd ~/mcp-skill-demo
gh repo create Roli24/mcp-skill-demo --public --source=. --remote=origin --push

git push -u origin feature/admin-user-search
gh pr create \
  --title "Add admin user search endpoint" \
  --body "Adds GET /admin/users/search so support staff can look up an \
account by partial username. Admin-role check is tracked in a follow-up \
ticket — out of scope here." \
  --base main --head feature/admin-user-search
```

Note the PR number `gh pr create` prints (e.g. `#1`) — that's what
you'll reference later.

## 1. Deploy `remote_server.py` somewhere with a public URL

Any host that runs a long-lived Python process works. Render's free
tier is the least fuss for a demo:

1. On [render.com](https://render.com): **New → Web Service** → connect
   `Roli24/mcp-skill-demo`.
2. Settings:
   - **Root Directory**: `mcp-server`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python3 remote_server.py`
3. Environment variables (Render's dashboard, not committed anywhere):
   - `GH_PAT` — your fine-grained GitHub PAT (`Contents: Read`,
     `Pull requests: Read and write`, scoped to this repo)
   - `CONNECTOR_TOKEN` — generate one yourself: `openssl rand -hex 32`
4. Deploy. Render gives you a URL like
   `https://mcp-skill-demo.onrender.com`. Your MCP endpoint is that URL
   plus `/mcp` — e.g. `https://mcp-skill-demo.onrender.com/mcp`.

(Railway, Fly.io, or your own VPS work the same way — the only
requirements are: run `remote_server.py`, set both env vars, terminate
TLS in front of it.)

Smoke-test it's alive before touching claude.ai:

```bash
curl -i https://mcp-skill-demo.onrender.com/mcp   # expect 401, not a timeout/500
```

## 2. Add it as a custom connector on claude.ai

1. claude.ai → **Settings → Connectors → Add custom connector**.
2. **URL**: `https://mcp-skill-demo.onrender.com/mcp`
3. Auth: bearer token — paste your `CONNECTOR_TOKEN` value.
4. Save, then confirm it shows connected and lists 3 tools
   (`get_pr_diff`, `get_pr_checks`, `post_review_comment`).

## 3. Upload the skill

1. claude.ai → **Settings → Capabilities → Skills → Create/Upload**.
2. Zip [`skill/pr-review/`](./skill/pr-review/) (its `SKILL.md`) and
   upload it, or paste the file's contents into the skill editor if
   claude.ai offers one.
3. It should now show up as an available skill in a chat.

## 4. Run it

In a claude.ai chat, with the `pr-github` connector and `pr-review`
skill both enabled:

```
Review PR #1 in Roli24/mcp-skill-demo
```

Claude should call `get_pr_diff` / `get_pr_checks` on the connector,
work through the skill's checklist, and report the SQL-injection and
missing-auth-check findings in `app.py`'s `search_users()` endpoint. To
see it close the loop, follow up with:

```
Post those findings as review comments on the PR
```

## Cleanup after recording

- Rotate/delete `CONNECTOR_TOKEN` on the host (or tear the service down
  entirely if it was only for this recording).
- Revoke the `GH_PAT` used here the same as you would after any demo.
- Remove the connector from claude.ai settings if you don't intend to
  keep it running.
