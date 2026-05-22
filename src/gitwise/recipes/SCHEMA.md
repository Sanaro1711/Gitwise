# Gitwise recipe schema

Each entry in `recipes.yaml` defines one workflow the CLI can match and optionally run.

## Required fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique `snake_case` identifier |
| `category` | string | `sync`, `branch`, `stash`, `commit`, `undo`, `remote`, `history`, `github` |
| `phrases` | list[string] | English intent variants for fuzzy matching (hand-written, 15–40 per recipe) |
| `requires` | list[string] | **All** predicates must pass (see below) |
| `danger` | bool | Show destructive warning in UI |
| `command` | string **or** list[string] | Git command(s) with `{placeholders}` |
| `explanation` | string | Why this command fits; shown before confirmation |
| `confirmation_level` | string | `standard`, `elevated`, `readonly`, `deferred` |

## Placeholders (rendered from repo state + parsed intent)

`{repo_name}`, `{branch}`, `{remote}`, `{upstream}`, `{default_branch}`, `{url}`, `{path}`, `{name}`, `{message}`

## Requires predicates (evaluated against `RepoState` + intent)

| Predicate | Meaning |
|-----------|---------|
| `in_repo` | Current directory is inside a git work tree |
| `not_in_repo` | Not inside a git work tree |
| `has_remote` | At least one remote configured |
| `no_remote_origin` | No remote named `origin` |
| `has_upstream` | Current branch tracks a remote branch |
| `no_upstream` | Current branch has no upstream |
| `clean_tree` | No uncommitted changes |
| `dirty_tree` | Any uncommitted changes |
| `has_staged` | Index has staged changes |
| `has_uncommitted` | Unstaged or untracked changes exist |
| `ahead_of_remote` | Local branch is ahead of upstream |
| `behind_remote` | Local branch is behind upstream |
| `has_stash` | At least one stash entry |
| `on_default_branch` | On `main` / `master` / `origin/HEAD` default |
| `not_on_default_branch` | On a feature branch |
| `merge_in_progress` | `.git/MERGE_HEAD` exists |
| `rebase_in_progress` | Rebase in progress |
| `merge_or_rebase_in_progress` | Either merge or rebase is active |
| `intent_has_branch` | User intent names a branch (`{name}`) |
| `intent_has_name` | User intent names a branch, tag, or other identifier (`{name}`) |
| `intent_has_url` | User intent contains a repo URL |
| `intent_has_path` | User intent names a file path |
| `intent_has_message` | User intent contains a commit/stash message |

## Confirmation levels

- **standard** — `Proceed? [y/N]`
- **elevated** — Extra typed `yes` when `danger: true`
- **readonly** — Inspection only; low risk
- **deferred** — Never executed by CLI (suggestion text only)

## Command notes

- Prefer modern Git: `git switch`, `git restore`, `git stash push` ([git-stash](https://git-scm.com/docs/git-stash), [git-push](https://git-scm.com/docs/git-push)).
- Force push uses `--force-with-lease`, never bare `--force`.
- `git stash pop` applies and removes; `git stash apply` keeps a copy (documented in stash recipe).

## Runtime overrides (render layer, not in YAML)

Some recipes need the command chosen from repo state after matching:

| Recipe id | When | Command used |
|-----------|------|----------------|
| `set_remote_origin` | `origin` missing | `git remote add origin {url}` |
| `set_remote_origin` | `origin` exists | `git remote set-url origin {url}` |
| `abort_merge_or_rebase` | merge active | `git merge --abort` |
| `abort_merge_or_rebase` | rebase active | `git rebase --abort` |
| `show_diff` | intent mentions staged | `git diff --staged` |

## Execution pipeline (later)

When `gw do` runs a recipe: **pre-checks → command → post-checks → failure handler**.

Optional future YAML fields: `post_check`, `on_failure`. See [`docs/EXECUTION_PIPELINE.md`](../../../docs/EXECUTION_PIPELINE.md).
