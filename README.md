# Gitwise

Git workflow assistant CLI. Inspects your local repository and maps plain English to the right git commands — with an explanation and confirmation before anything runs.

## Install (development)

```bash
cd Gitwise
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -e ".[dev]"
```

## Commands

### `gw pull`

Guided safe pull with conflict help (also runs when you `gw do "pull"`):

```bash
gw pull
gw pull -n          # dry-run: show steps only
gw pull -C path/to/repo
```

Flow: check branch → stash if dirty → fetch → merge (no rebase) → step-by-step conflict guide → restore stash (kept until you confirm drop).

### `gw do "<intent>"`

One quoting rule: wrap the intent in **double quotes** for the shell; put **names and messages in single quotes**:

```bash
gw do "commit 'fix login bug'"
gw do "create branch 'feature/login'"
gw do "delete branch 'old-hotfix'"
gw do "push to main"
gw do "stash my changes" -n
```

On Windows PowerShell this avoids the nested-double-quote problem. Single-quoted segments are mapped automatically:

| You say | Value used for |
|---------|----------------|
| `commit '...'` | commit message |
| `create branch '...'` | branch name |
| `delete branch '...'` | branch name |
| `stash ... '...'` | stash message |
| `discard ... 'path'` | file path |
| `clone 'url'` | repository URL |

`-u` for push is chosen automatically from upstream tracking (see `push_resolver`).

### `gw whereami`

Full breakdown of the repo you are standing in (read-only git calls only):

```text
Repo: Gitwise
Branch: master
Remote: origin
Upstream: (not set)

Working tree:
  Clean — no uncommitted changes

Sync state:
  No upstream branch configured for this branch.
  First push usually needs: git push -u <remote> <branch>
```

```bash
gw whereami
gw whereami -C path/to/repo
```

## Remotes and GitHub access

Gitwise does **not** use a separate GitHub login. It reads your repo’s **configured remote** (`origin`, URL, upstream) and runs the same `git` commands you would — using **your existing** SSH keys or HTTPS credentials.

See [`docs/ACCESS.md`](docs/ACCESS.md) for how auth works and how to verify setup.

`gw whereami` now shows **Remote URL** so you can see which host (e.g. GitHub) git will talk to.

**Automatic `-u`:** when `gw do` ships, push uses [`push_resolver`](src/gitwise/matching/push_resolver.py) — `-u` is added only when your branch has no upstream (or you explicitly ask for it), not because you said a magic phrase.

## Privacy and safety

- Gitwise only runs git in the **directory you are in** (or `-C path`). It does not scan your home folder or read unrelated files.
- No network API calls in the MVP.
- Destructive commands (`gw do`, coming later) always ask before running.
- If you want the agent or a script to inspect a **personal** repository, say so explicitly first.

## Recipes

Workflow definitions live in [`src/gitwise/recipes/recipes.yaml`](src/gitwise/recipes/recipes.yaml). The count (~30) is a rough guide — add more as needed.

Validate:

```bash
python src/gitwise/recipes/validate_recipes.py
```

## Intent matching (`gw do`)

`rapidfuzz` matches your wording against recipe phrase lists. **Single quotes** inside the intent carry the value (message, branch name, path, URL). Similar phrases work without being listed verbatim:

- `"push this to main"` → fuzzy **push** + branch `main`
- `"commit 'fix bug'"` → message from single quotes
- `-u` is chosen from **repo state** (`has_upstream`), not from phrasing

See [`src/gitwise/matching/intent_parser.py`](src/gitwise/matching/intent_parser.py).

## Execution pipeline (`gw do`)

Every run follows:

**pre-checks → confirm → command → post-checks → failure handler**

- **Pre-checks** catch problems early (e.g. switch to a branch that does not exist).
- **Failure handler** reads git stderr, explains what went wrong, and suggests `gw do` next steps.

Details: [`docs/EXECUTION_PIPELINE.md`](docs/EXECUTION_PIPELINE.md).

## Roadmap

### Shipped

- [x] `gw whereami`
- [x] `gw do "<intent>"` (matcher, confirm, run)
- [x] ~30 recipes in YAML + single-quote values
- [x] Auto `-u` on push (`push_resolver`)
- [x] Pre-checks / post-checks / failure handler on `gw do`

### Not built yet

- [ ] `gw explain "<command>"` — no CLI command; only short text in `gw do` plans
- [ ] `gw fix "<error>"` — no CLI command; failures on `gw do` already suggest fixes

### Merge (planned)

- [x] Basic: `merge_into_default` recipe (`switch` + `git merge`)
- [x] `abort_merge_or_rebase` recipe
- [ ] Merge feature → arbitrary branch (not only default)
- [ ] `gw do` after conflict: stage resolved files + complete merge commit
- [ ] Richer merge pre-checks (uncommitted, already up to date)
- [ ] Post-check: verify merge commit / no lingering `MERGE_HEAD`
- [ ] `gw fix` entries for common merge error strings

## License

MIT
