# Roadmap

What is shipped today and what could come next.

## Shipped

| Feature | Command | Notes |
|---------|---------|-------|
| Repo snapshot | `gw whereami` | Branch, remote, sync, dirty files |
| Natural language workflows | `gw do "…"` | ~30 YAML recipes, fuzzy match, confirm |
| Safe pull + conflicts | `gw pull` | Stash, merge, interactive conflict guide |
| Quick save | `gw save "msg"` | add + commit + push current branch |
| Undo guide | `gw undo last` | Interactive reset/revert/unstage menu |
| AI assistant | `gw ask "…"` | Gemini, validated plans only |
| Auto upstream on push | (in `gw do` / `gw save`) | `-u` when branch has no upstream |
| Execution pipeline | (all runners) | pre-check → confirm → run → post-check → failures |

## Next up (planned)

| Feature | Command | Description |
|---------|---------|-------------|
| Explain repo state | `gw explain-state` | LLM walks through your current situation in plain English |
| Explain a command | `gw explain "git …"` | What a git command would do before you run it |
| Error lookup | `gw fix "error text"` | Map git stderr to recovery steps |
| Merge into any branch | `gw do "…"` | Not only default branch |
| Post-merge in `gw do` | `gw do "…"` | Stage resolved files + complete merge commit |
| GitHub PR helper | `gw do "create pr"` | Optional `gh` integration (deferred today) |

## Ideas (not scheduled)

- Guided rebase conflict flow (like `gw pull` for rebase)
- Shell completions (`gw --install-completion`)
- Config file for defaults (remote name, editor)
- Plugin/recipe packs per team
- Offline mode: disable `gw ask` entirely via env flag
- `gw sync` alias: pull then push when safe
- Richer merge pre/post checks
- Interactive “what next?” after command failures
- YAML-driven `post_check` / `on_failure` hooks per recipe

## Contributing

Fork the repo, add recipes to `recipes.yaml`, or extend workflows under `src/gitwise/workflows/`. See [SECURITY.md](SECURITY.md) before submitting changes that touch the LLM layer.
