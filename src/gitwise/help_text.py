"""Comprehensive help text for `gw --help`."""

APP_HELP = """\
Gitwise (gw) - Git workflow assistant

Inspect your repo, run safe git workflows from plain English, or use shortcut
commands for common tasks. Gitwise only runs git in the directory you choose;
it uses your existing SSH keys or HTTPS credentials (no separate GitHub login).

QUICK START
  gw whereami              See branch, remote, sync state, working tree
  gw save "your message"   Stage all, commit, and push current branch
  gw pull                  Guided pull with conflict help
  gw do "push to main"     Match intent to a recipe and run with confirmation
  gw undo last             Explain undo options and pick the safest one

COMMANDS

  whereami [-C PATH]
      Read-only repo snapshot: branch, upstream, ahead/behind, dirty files.

  save MESSAGE [-n] [-y] [-C PATH]
      Stage everything (git add .), commit with MESSAGE, push current branch.
      Adds -u automatically when your branch has no upstream yet.

  pull [--from BRANCH] [-n] [-y] [-C PATH]
      Safe pull: stash if dirty -> fetch -> merge (no rebase) -> conflict guide
      -> restore stash. Use --from main to merge origin/main explicitly.

  do INTENT [-n] [-y] [-C PATH]
      Natural-language git workflows (~30 recipes). Always shows why and asks
      before running (unless -y). Wrap intent in double quotes; put names and
      messages in single quotes inside:

        gw do "commit 'fix login bug'"
        gw do "create branch 'feature/login'"
        gw do "pull from branch 'main'"
        gw do "stash my changes with message 'wip'"

  undo [last] [-n] [-y] [-C PATH]
      Interactive menu explaining undo options (reset, revert, unstage, discard,
      abort merge/rebase) and helps you pick the best choice for your situation.

GLOBAL OPTIONS
  -C, --path PATH   Run in a different repository directory
  -n, --dry-run     Show the plan without executing git
  -y, --yes         Skip confirmation prompts (use with care)
  -V, --version     Show version

TIPS
  - Use gw whereami first when unsure about branch or sync state.
  - gw save is the fast path when you just want add + commit + push.
  - gw pull handles merge conflicts step-by-step; gw do "pull latest" routes there too.
  - Destructive actions require typing 'yes' or explicit confirmation.
  - See docs/ACCESS.md for remotes, auth, and GitHub setup.
"""
