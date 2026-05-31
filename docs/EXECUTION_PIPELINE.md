# Execution pipeline

Every runnable `gw do` workflow follows the same stages:

```text
pre-checks  ->  confirm  ->  run git  ->  post-checks  ->  failure handler
```

## 1. Pre-checks

Run before confirmation. Block early when the plan cannot succeed.

Examples: not in a repo, branch missing, merge already in progress, nothing staged for commit.

## 2. Confirm

User sees **why** and the exact commands. Destructive recipes require typing `yes`.

Flags: `-n` dry-run (show only), `-y` skip prompt (use with care).

## 3. Run

Commands execute via subprocess (`shell=False`), one step at a time. Stops on first failure.

## 4. Post-checks

After success, verify expected state (e.g. branch switched, push reduced `ahead` count).

## 5. Failure handler

On error: classify stderr, explain in plain language, suggest `gw do` next steps.

Special flows bypass the generic runner where needed:

- `gw pull` — safe pull with stash and conflict guide
- `gw save` — add, commit, push
- `gw ask` — validated plans only, via Gitwise planner

## Module map

| Module | Role |
|--------|------|
| `execution/pre_checks.py` | Block bad plans |
| `execution/runner.py` | Subprocess chain |
| `execution/post_checks.py` | Verify outcome |
| `execution/failures.py` | Classify errors, suggest fixes |
| `execution/pipeline.py` | Orchestration |

Recipe definitions: `src/gitwise/recipes/recipes.yaml`
