# Remotes and authentication

Gitwise does not add its own GitHub login. It runs the same `git` commands you would, using credentials **git already has** on your machine.

## What Gitwise reads (local only)

| Git command | Used for |
|-------------|----------|
| `git remote`, `git remote get-url` | Remote name and host |
| `git branch -vv` | Current branch, upstream |
| `git status`, `git rev-list` | Dirty tree, ahead/behind |

No GitHub REST API. No tokens stored inside Gitwise.

## How push and pull authenticate

When Gitwise runs `git push` or `git pull`, **git** talks to your remote:

**HTTPS** — Credential Manager (Windows), macOS Keychain, or a stored PAT.

**SSH** — Your `~/.ssh` keys (`git@github.com:user/repo.git`).

If `git push` works in your terminal, it works in Gitwise after you confirm.

## Verify your setup

```bash
gw whereami
git remote -v
git push --dry-run
```

## GitHub CLI (`gh`)

Optional, for future PR workflows. Not required for push/pull. The `create_github_pr` recipe is deferred and never auto-runs.

## Privacy

Gitwise only inspects the repo directory you pass (`-C path` or current directory). It does not scan other folders.

For LLM-specific privacy (`gw ask`), see [SECURITY.md](SECURITY.md).
