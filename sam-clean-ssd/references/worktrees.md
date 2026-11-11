# Git Worktrees and Clones

A worktree is a full checkout, so a few dozen of them can hold hundreds of GiB even after their build output is gone.

## What removal loses

- A **linked worktree** keeps its history in the main repository. Commits on any branch survive and the branch stays. Stashes are repository-wide and survive too.
- Lost with the folder: uncommitted changes to tracked files, untracked and ignored files, and commits reachable only from a detached HEAD (orphan commits, whose log is deleted with the worktree metadata).
- A **standalone clone** holds its own history. Unpushed commits, or a repository with no remote, exist nowhere else.

## Decisions from `scripts/classify_worktrees.py`

| Decision | Meaning | Action |
| --- | --- | --- |
| `REMOVE` | Linked worktree, or clean clone fully on a remote | Safe to list |
| `REMOVE_LOSES_CHANGES` | Tracked or untracked changes exist | Needs the user's approval naming the loss. `remove_listed.py` then needs `--allow-uncommitted-loss`; use `--save-patches`. Untracked files are not saved |
| `SKIP_ORPHAN_COMMITS` | Commits on no branch, remote or tag | `remove_listed.py` always refuses. Offer a branch for those commits (the user's choice), then classify again |
| `SKIP_CLONE_HAS_WORK` | Clone with changes or unpushed commits | Leave it and show the user |
| `SKIP_IN_USE` | A running process has its working directory inside | Leave it; ask the user to close the process |
| `REVIEW_NESTED` | Another `.git` inside | Inspect each nested entry (below) |
| `SKIP_NOT_GIT`, `SKIP_UNSUPPORTED_GITFILE` | Not a worktree or clone | Leave it |

## Nested repositories

List the nested entries and classify each one. Dependency checkouts that a package manager clones inside a build folder, and cache clones, are regenerable. A nested repository with changes or unpushed commits is not. Remove the parent only when every nested entry is clean or regenerable.

## Judgment

- "Unpushed" means not reachable from any remote-tracking ref known locally. A fetch could change the answer; fetch only if the user allows network use.
- Do not read the folder's modification time as "recent". Your own deletions inside it update that time. Use the last commit date and running processes.
- An application that created the worktrees may keep a record of them; tell the user it may need to forget them.
- After removal `remove_listed.py` runs `git worktree prune` on the main repositories. That also drops metadata of worktrees whose folders were already missing.
- Report how many worktrees lost uncommitted work and where the patches are.
