# Connecting this demo to claude.ai (Connector + Skill)

claude.ai's **Add custom connector** form asks for an Authorization
URL, Token URL, Client ID, and Client Secret — it does not offer a
plain bearer-token field. `mcp-server/remote_server.py` implements a
small, single-tenant OAuth 2.1 (authorization code + PKCE) server to
match that, sitting in front of the same three tools
(`get_pr_diff`, `get_pr_checks`, `post_review_comment`).

Three secrets, three separate jobs — don't conflate them:

| Secret | Proves | Who ever sees it |
|---|---|---|
| `GH_PAT` | — (just used to call GitHub) | Only your deployed server's environment |
| `OAUTH_CLIENT_SECRET` | It's really claude.ai calling `/oauth/token` | You (paste once into claude.ai's form) + your server |
| `CONSENT_PASSWORD` | It's really you clicking "approve" in the browser | Only you, typed once during setup |

claude.ai never receives `GH_PAT` or `CONSENT_PASSWORD` — only
`OAUTH_CLIENT_SECRET` (once, at setup) and the short-lived access/
refresh tokens your server issues afterward.

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

Note the PR number `gh pr create` prints (e.g. `#1`).

## 1. Deploy `remote_server.py`

Render's free tier works for a demo:

1. On [render.com](https://render.com): **New → Web Service** → connect
   `Roli24/mcp-skill-demo`.
2. Settings:
   - **Root Directory**: `mcp-server`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python3 remote_server.py`
3. Environment variables:
   - `GH_PAT` — your fine-grained GitHub PAT (`Contents: Read`,
     `Pull requests: Read and write`, scoped to this repo)
   - `OAUTH_CLIENT_SECRET` — generate: `openssl rand -hex 32`
   - `CONSENT_PASSWORD` — generate: `openssl rand -hex 16`
   - `PUBLIC_URL` — the URL Render assigns you, e.g.
     `https://mcp-skill-demo.onrender.com` (you'll know this only
     *after* the first deploy creates the service — update and
     redeploy once you have it)
   - `OAUTH_REDIRECT_URIS` — leave unset for the very first deploy;
     you'll fill this in during Step 2 below and redeploy once more.
4. Deploy. Confirm it's up:
   ```bash
   curl -i https://mcp-skill-demo.onrender.com/.well-known/oauth-authorization-server
   # expect 200 + JSON, not a timeout/500
   ```

(Any host that runs a long-lived Python process behind HTTPS works —
Railway, Fly.io, your own VPS. Same env vars either way.)

## 2. Add it as a custom connector on claude.ai

1. claude.ai → **Settings → Connectors → Add custom connector**.
2. Fill in:
   - **Authorization URL**: `https://mcp-skill-demo.onrender.com/oauth/authorize`
   - **Token URL**: `https://mcp-skill-demo.onrender.com/oauth/token`
   - **Client ID**: `pr-github-connector`
   - **Client Secret**: your `OAUTH_CLIENT_SECRET` value
   - **MCP server URL**: `https://mcp-skill-demo.onrender.com/mcp`
3. claude.ai will show you the **redirect URI** it's going to use for
   this connector. Copy it, set it as `OAUTH_REDIRECT_URIS` in your
   host's env vars, and redeploy/restart the server — the
   authorization step will reject the request until this matches.
4. Click connect. You'll be sent to your server's consent page —
   type in `CONSENT_PASSWORD` and approve.
5. claude.ai should now show the connector as connected, listing 3
   tools.

## 3. Upload the skill

1. claude.ai → **Settings → Capabilities → Skills → Create/Upload**.
2. Zip [`.claude/skills/pr-review/`](./.claude/skills/pr-review/) (its
   `SKILL.md`) and upload it, or paste the file's contents into the
   skill editor if claude.ai offers one.
3. It should now show up as an available skill in a chat.

## 4. Run it

In a claude.ai chat, with the connector and `pr-review` skill both
enabled:

```
Review PR #1 in Roli24/mcp-skill-demo
```

Claude should call `get_pr_diff` / `get_pr_checks` on the connector,
work through the skill's checklist, and report the SQL-injection and
missing-auth-check findings in `app.py`'s `search_users()` endpoint.
Follow up with:

```
Post those findings as review comments on the PR
```

to see it call `post_review_comment` and close the loop.

## Cleanup after recording

- Revoke/rotate `OAUTH_CLIENT_SECRET` and `CONSENT_PASSWORD` on the
  host (or tear the service down entirely if it was only for this
  recording).
- Revoke the `GH_PAT` used here the same as you would after any demo.
- Remove the connector from claude.ai settings if you don't intend to
  keep it running.
