# Gitwise documentation

| Doc | Purpose |
|-----|---------|
| [Getting started](../README.md#quick-start) | Install, verify, daily commands |
| [SECURITY.md](SECURITY.md) | Secrets, privacy, what leaves your machine |
| [GEMINI.md](GEMINI.md) | Optional `gw ask` setup (free Gemini API key) |
| [ACCESS.md](ACCESS.md) | Remotes, GitHub auth, how push/pull credentials work |
| [EXECUTION_PIPELINE.md](EXECUTION_PIPELINE.md) | How `gw do` validates and runs commands |
| [ROADMAP.md](ROADMAP.md) | Shipped features and what is left to build |

Project layout for contributors:

| Path | Purpose |
|------|---------|
| `src/gitwise/cli.py` | CLI entry (`gw`) |
| `src/gitwise/recipes/recipes.yaml` | Workflow catalog for `gw do` |
| `src/gitwise/llm/` | Optional Gemini integration for `gw ask` |
| `src/gitwise/workflows/` | Multi-step flows (`pull`, `save`, `undo`, `ask`) |
