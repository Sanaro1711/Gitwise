# Gitwise

Git workflow assistant CLI. Inspects your local repository and maps plain English to the right git commands — with an explanation and confirmation before anything runs.

## Install (development)

```bash
cd Gitwise
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -e ".[dev]"
```

## Commands (current)

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

## Intent matching (`gw do`, next)

`rapidfuzz` matches your wording against **hand-written phrase lists**, not a generated cheatsheet. Similar phrases work without being listed verbatim:

- `"push this to main"` → fuzzy **push** + parsed target branch `main`
- `-u` is chosen from **repo state** (`has_upstream`), not from memorizing one exact phrase

See [`src/gitwise/matching/intent_parser.py`](src/gitwise/matching/intent_parser.py).

## Execution pipeline (planned for `gw do`)

Every run will follow:

**pre-checks → command → post-checks → failure handler**

If e.g. `push` fails because the remote is ahead or there are merge conflicts, Gitwise classifies the error, explains it, and suggests next moves (`pull`, `gw fix`, abort merge) — without auto-running them.

Details: [`docs/EXECUTION_PIPELINE.md`](docs/EXECUTION_PIPELINE.md). Stub: [`src/gitwise/execution/`](src/gitwise/execution/).

## Roadmap

- [x] `gw whereami`
- [ ] `gw do "<intent>"` (matcher + confirm)
- [ ] Execution pipeline (pre / post / failure handler)
- [ ] `gw explain "<command>"`
- [ ] `gw fix "<error>"` (reuse failure classifier)

## License

MIT
