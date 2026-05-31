"""Comprehensive help text for `gw --help`."""

APP_HELP = """\
Gitwise (gw) - safe git workflow CLI

Run git in plain English with explanation and confirmation before anything
mutates your repo. Works in any git repository on your machine.

QUICK START
  gw whereami                    Branch, remote, sync state, dirty files
  gw save "your message"         Stage all, commit, push current branch
  gw pull                        Safe pull with conflict help
  gw do "push to main"           Natural-language workflows (~30 recipes)
  gw undo last                   Pick the safest undo option
  gw ask "your question"         Optional AI help (needs GEMINI_API_KEY)

INSTALL (after fork/clone)
  python -m venv .venv
  .venv\\Scripts\\activate          Windows
  source .venv/bin/activate       Linux/macOS
  pip install -e .
  copy .env.example .env            optional, for gw ask only

SECRETS
  Never commit .env or API keys. See docs/SECURITY.md.
  Gemini key: .env, GEMINI_API_KEY env var, or ~/.gitwise/gemini_api_key

COMMANDS

  whereami [-C PATH]
      Read-only snapshot of the current repository.

  save MESSAGE [-n] [-y] [-C PATH]
      git add .  ->  commit  ->  push (current branch, auto -u if needed).

  pull [--from BRANCH] [-n] [-y] [-C PATH]
      Stash if dirty, fetch, merge (no rebase), conflict guide, restore stash.

  do INTENT [-n] [-y] [-C PATH]
      Match intent to a recipe. Double quotes outside; single quotes for values:

        gw do "commit 'fix login bug'"
        gw do "create branch 'feature/x'"
        gw do "pull from branch 'main'"

  undo [last] [-n] [-y] [-C PATH]
      Interactive menu: reset, revert, unstage, discard, abort merge/rebase.

  ask QUESTION [-n] [-y] [-C PATH]
      Ask Gemini about your repo (redacted context). Action plans are validated
      against Gitwise before you can run them. Setup: docs/GEMINI.md

GLOBAL OPTIONS
  -C, --path PATH     Repository directory (default: current directory)
  -n, --dry-run       Show plan only; do not run git
  -y, --yes           Skip confirmation (destructive ops still need 'yes')
  -V, --version       Print version

DOCUMENTATION
  docs/README.md        Index of all docs
  docs/SECURITY.md      Secrets, privacy, safety model
  docs/GEMINI.md        Optional API key for gw ask
  docs/ROADMAP.md       Future features
"""
