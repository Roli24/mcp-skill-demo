#!/usr/bin/env bash
# Creates a fresh demo PR: a new branch off main, with a deliberate
# SQL-injection + missing-auth-check bug, pushed and opened as a PR.
#
# main stays clean and safe on purpose -- run this whenever you want a
# real, live, unmerged PR for /pr-review to catch. Requires
# `gh auth login` already done (see README.md).
#
# Usage: ./make-demo-pr.sh
# Prints the PR number to use with /pr-review PR #<N>.

set -euo pipefail
cd "$(dirname "$0")"

BRANCH="demo/admin-user-search-$(date +%s)"

git checkout main -q
git pull -q origin main
git checkout -b "$BRANCH" -q

python3 - "$PWD/app.py" <<'PYEOF'
import re
import sys

path = sys.argv[1]
src = open(path).read()

bug = '''

@app.get("/admin/users/search")
def search_users():
    """Admin tool: search users by a substring of their username.

    NOTE: this ships in the PR without an is_admin check yet -- that's
    tracked in a follow-up ticket, out of scope for this PR.
    """
    query = request.args.get("q", "")

    db = get_db()
    sql = "SELECT id, username, is_admin FROM users WHERE username LIKE '%" + query + "%'"
    rows = db.execute(sql).fetchall()

    return jsonify([dict(row) for row in rows])
'''

marker = 'if __name__ == "__main__":'
if marker not in src:
    sys.exit("Couldn't find insertion point in app.py -- has it changed shape?")

src = src.replace(marker, bug.strip("\n") + "\n\n\n" + marker, 1)
open(path, "w").write(src)
PYEOF

git add app.py
git commit -q -m "Add admin user search endpoint"
git push -u origin "$BRANCH" -q

PR_URL=$(gh pr create \
  --title "Add admin user search endpoint" \
  --body "Adds GET /admin/users/search so support staff can look up an account by partial username. Admin-role check is tracked in a follow-up ticket — out of scope here." \
  --base main --head "$BRANCH")

echo
echo "PR opened: $PR_URL"
echo "Run: /pr-review PR #$(basename "$PR_URL")"
echo
echo "Cleanup:"
echo "  gh pr close $(basename "$PR_URL") --delete-branch"
echo "  git checkout main && git branch -D $BRANCH"
