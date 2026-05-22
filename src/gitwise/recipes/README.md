# Gitwise recipes

Hand-authored workflow catalog for `gw do`. **Do not auto-generate phrases** — expand `phrases` lists manually as you discover real user wording.

## Files

| File | Purpose |
|------|---------|
| [`recipes.yaml`](recipes.yaml) | Workflow catalog (~30+, source of truth) |
| [`SCHEMA.md`](SCHEMA.md) | Field definitions, requires predicates, render overrides |
| [`validate_recipes.py`](validate_recipes.py) | Structural validation |

## Validate

```bash
pip install pyyaml
python src/gitwise/recipes/validate_recipes.py
```

## Recipe index (current: 30, may grow)

| Category | IDs |
|----------|-----|
| **sync** | `push_current_branch`, `push_new_branch_upstream`, `pull_latest`, `fetch_remote`, `force_push_safe` |
| **branch** | `create_branch`, `switch_branch`, `rename_branch`, `list_branches`, `delete_local_branch`, `delete_remote_branch`, `merge_into_default`, `abort_merge_or_rebase`, `rebase_onto_default` |
| **stash** | `stash_changes`, `stash_including_untracked`, `apply_latest_stash` |
| **commit** | `stage_all_changes`, `commit_changes` |
| **undo** | `undo_last_commit_keep`, `undo_staged`, `discard_one_file`, `discard_all_local` |
| **remote** | `clone_repo`, `set_remote_origin` |
| **history** | `show_status`, `show_diff`, `check_history`, `create_tag` |
| **github** | `create_github_pr` (deferred — never auto-run) |

## Accuracy notes

- **push_current_branch** vs **push_new_branch_upstream** — separated by `has_upstream` / `no_upstream` so `gw do "push"` never picks the wrong one.
- **force_push_safe** — uses `--force-with-lease` only ([git-push docs](https://git-scm.com/docs/git-push)).
- **stash** — uses `git stash push` / `-u` ([git-stash docs](https://git-scm.com/docs/git-stash)).
- **discard** — `git restore` + `git clean -fd`; irreversible.
- **set_remote_origin** / **abort_merge_or_rebase** / **show_diff** — final command resolved at render time (see SCHEMA.md).
