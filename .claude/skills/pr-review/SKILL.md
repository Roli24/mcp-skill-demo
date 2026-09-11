---
name: PR Security Review
description: Reviews an open GitHub pull request for correctness and security issues (injection, missing auth checks, unvalidated input) using live PR diff and CI data, and can post findings back as review comments.
---

# PR Security Review

Orchestrates the local `pr-github` MCP server and this checklist to
review a pull request end to end: pull live context in, review it,
optionally push findings back out. Invoked as `/pr-review <PR
reference>`, e.g. `/pr-review PR #1` or `/pr-review PR #1 --comment`.

## 1. Get live context via the pr-github MCP server

Do not ask the user to paste a diff. Use the local `pr-github` MCP
server's tools to fetch, for the referenced PR:

- `get_pr_diff(owner, repo, pr_number)` — the full diff
- `get_pr_checks(owner, repo, pr_number)` — the latest CI / check-run status

If the `pr-github` server isn't connected, say so and stop — this skill
depends on it for live data, it does not work from memory or a stale
local checkout.

## 2. Review the diff against this checklist

For every changed file, check for:

- **Injection** — SQL, shell, template, or log injection from any
  value built with string concatenation/formatting instead of
  parameterization.
- **Missing authorization** — a new or changed endpoint/handler that
  performs a privileged action without checking the caller's role or
  identity, including cases where the check is deferred with a comment
  like "follow-up ticket."
- **Unvalidated input** — missing type, range, length, or
  empty/negative checks on values that flow into business logic,
  storage, or another system call.
- **Secrets in the diff** — API keys, tokens, or credentials committed
  as literals.
- **Test coverage gap** — does the PR's own test file exercise the new
  code path, including its edge cases? Flag it if the happy path is
  tested but the edge case that matters isn't.

## 3. Report findings

Rank findings most severe first. For each one, cite the exact
`file:line`, state the concrete failure scenario ("a request with
`quantity=-5` does X"), and suggest the minimal fix. Never approve or
merge the PR yourself — that decision stays with a human reviewer.

## 4. Post back to GitHub (only if asked, e.g. `--comment`)

Call `post_review_comment(owner, repo, pr_number, path, line, body)`
once per finding to leave an inline comment on its diff line. Confirm
in chat what was posted, including the comment URL each call returns.
