# Gitwise

Safe git workflow CLI. Inspect your repo, run commands in plain English, and get confirmation before anything changes.

Works in **any git repository**. Fork, install, and use locally — no cloud account required except optionally for `gw ask`.

## Requirements

- Python 3.11+
- [Git](https://git-scm.com/) on your PATH
- Optional: [Gemini API key](https://aistudio.google.com/apikey) for `gw ask` only

## Quick start

### 1. Clone or fork

```bash
git clone https://github.com/YOUR_USER/Gitwise.git
cd Gitwise
```

### 2. Install

**Windows (PowerShell):**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
```

**Linux / macOS:**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 3. Verify

```bash
gw whereami
gw --help
```

Run these inside any git repo. You should see branch, remote, and sync state.

### 4. Optional — enable `gw ask` (AI)

```powershell
copy .env.example .env          # Windows
# cp .env.example .env          # Linux/macOS
```

Edit `.env` and add your free Gemini key:

```
GEMINI_API_KEY=your-key-here
```

`.env` is gitignored — your key stays local. See [docs/GEMINI.md](docs/GEMINI.md).

```bash
gw ask "what branch am I on?"
```

All other commands work **without** an API key.

---

## Commands

| Command | What it does |
|---------|----------------|
| `gw whereami` | Read-only repo snapshot |
| `gw save "msg"` | `git add .` → commit → push current branch |
| `gw pull` | Safe pull with stash + conflict guide |
| `gw do "intent"` | ~30 natural-language workflows |
| `gw undo last` | Interactive undo menu |
| `gw ask "question"` | Repo-aware AI help (optional) |

Global flags: `-C path` (repo directory), `-n` (dry-run), `-y` (skip confirm).

Full reference: `gw --help`

### Examples

```bash
gw save "fixed login bug"
gw pull
gw pull --from main
gw do "commit 'wip refactor'"
gw do "create branch 'feature/login'"
gw undo last
gw ask "should I pull before pushing?" -n
```

**Quoting (PowerShell):** wrap the whole intent in double quotes; put messages and branch names in **single quotes** inside:

```bash
gw do "commit 'fix bug'"
gw do "delete branch 'old-hotfix'"
```

---

## Security and secrets

Gitwise never stores git passwords or SSH keys. Optional Gemini keys go in `.env` (gitignored) or `GEMINI_API_KEY`.

**Before you push to GitHub:** confirm `.env` is not tracked:

```bash
git status    # .env should NOT appear
```

Read [docs/SECURITY.md](docs/SECURITY.md) for the full safety model.

| Safe to commit | Never commit |
|----------------|--------------|
| `.env.example` | `.env` |
| Source code | `gemini_api_key`, `*.pem`, tokens |

---

## How it works

**`gw do`** matches your wording to recipes in [`recipes.yaml`](src/gitwise/recipes/recipes.yaml) using fuzzy matching, then runs:

```text
pre-checks → confirm → git commands → post-checks → failure help
```

**`gw ask`** sends a small redacted repo snapshot to Gemini, validates any suggested commands against the same planner, and only offers to run Gitwise-approved plans.

Details: [docs/EXECUTION_PIPELINE.md](docs/EXECUTION_PIPELINE.md)

---

## Documentation

| Doc | Topic |
|-----|-------|
| [docs/README.md](docs/README.md) | Documentation index |
| [docs/SECURITY.md](docs/SECURITY.md) | Secrets, privacy, command safety |
| [docs/GEMINI.md](docs/GEMINI.md) | API key setup for `gw ask` |
| [docs/ACCESS.md](docs/ACCESS.md) | Remotes, GitHub auth |
| [docs/ROADMAP.md](docs/ROADMAP.md) | Future features |
| `gw --help` | CLI reference |

---

## Development

```bash
pip install -e ".[dev]"
python -m pytest tests/ -q
python src/gitwise/recipes/validate_recipes.py
```

---

## Roadmap (summary)

**Shipped:** `whereami`, `do`, `pull`, `save`, `undo`, `ask`, recipes, validation pipeline.

**Planned:** `gw explain-state`, `gw explain`, `gw fix`, merge-into-any-branch, GitHub PR via `gh`, guided rebase.

Full list: [docs/ROADMAP.md](docs/ROADMAP.md)

---

## License

MIT
