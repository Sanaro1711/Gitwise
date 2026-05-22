# Remotes, GitHub, and “access”

Gitwise does **not** connect to GitHub (or GitLab, etc.) through a separate API or OAuth app. It uses the same access **git already has** on your machine.

## What Gitwise can see today (automatic, read-only)

When you run `gw whereami` or (later) `gw do`, Gitwise reads **local** git metadata only:

| Source | What it learns |
|--------|----------------|
| `git remote` | Remote names (`origin`, …) |
| `git remote get-url origin` | Host (e.g. `github.com`) and repo path — **no password** |
| `git branch -vv` / branch config | Current branch, upstream (`origin/main`) |
| `git status`, `git rev-list` | Dirty tree, ahead/behind |

So it already knows **which remote you are using** (usually `origin`) and whether your branch **tracks** an upstream. That is enough to choose `git push` vs `git push -u` automatically.

## What Gitwise does *not* do (MVP)

- No GitHub REST API
- No reading your GitHub username from the website
- No storing tokens inside Gitwise
- No `gh` commands unless you run a deferred PR recipe manually later

## How git gets “access” to GitHub (you set this up once)

When Gitwise (or you) runs `git push` / `git pull`, **git** talks to the host in the remote URL. Authentication is whatever git is already configured to use:

### HTTPS (`https://github.com/user/repo.git`)

- **Git Credential Manager** (common on Windows), or
- Credential helper storing a **Personal Access Token (PAT)**, or
- Prompt for username/token on first use

Create a PAT: GitHub → Settings → Developer settings → Personal access tokens (repo scope for private repos).

### SSH (`git@github.com:user/repo.git`)

- SSH key in `~/.ssh/` added to your GitHub account  
- Test: `ssh -T git@github.com`

### GitHub CLI (`gh`) — optional, later

For pull requests only (future). One-time:

```bash
gh auth login
```

Gitwise will not call `gh` until that feature ships; your normal `git push` does not require `gh`.

## Giving Gitwise “access” in practice

You do **not** grant Gitwise a special permission. If this works in your repo:

```bash
git push
```

then Gitwise can run the same push after you confirm.

If push fails for you manually, Gitwise will fail too — and the **failure handler** (planned) will explain (auth, non-fast-forward, etc.).

## Check your setup

```bash
gw whereami          # remote name, URL, upstream, ahead/behind
git remote -v
git push --dry-run   # sees if auth works without pushing
```

## Privacy

Gitwise only inspects the repo directory you are in (or `-C path`). It does not scan other folders or upload data to a cloud service.
