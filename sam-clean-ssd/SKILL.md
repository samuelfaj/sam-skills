---
name: sam-clean-ssd
description: "Free disk space on a full SSD or drive: measure first, explain where the space went, then remove only what the user approves from regenerable caches, build output and stale git worktrees. Use when the user asks to clean, free up or shrink disk space, or a disk is full; never to erase or format a drive."
---

# Sam Clean SSD

Reclaim space without losing work. Measure, show the user where the space went, remove only what they approve, and prove the result with free-space numbers from the filesystem.

## Non-Negotiable Contract

- **Free space, never erase.** "Clean" means reclaim space. Never wipe, format, reset or reinstall a drive from here. If the user wants that, say it needs recovery tooling outside this skill and stop.
- **Measure before you touch.** Read-only first. Nothing is deleted until the user approved an explicit list with sizes and risk tiers. Approval of a summary does not cover items you flagged as conditional; ask again for those.
- **Delete by exact path only.** Use `scripts/remove_listed.py` on an approved list, dry run first. No globs, no pattern deletes, no `sudo`, nothing in another user's folders, system volumes, or off the list. Permission denied is a finding to report, not an obstacle to bypass.
- **Unique work is not junk.** Before removing a project, clone or worktree, check what exists nowhere else: uncommitted or untracked files, commits on no remote, a repository with no remote at all, commits on a detached HEAD. Say it once, plainly, with numbers. If the user repeats the instruction after seeing it, do it. Save what is cheap to save (patches) first.
- **Do not trust your own side effects.** Your deletions change folder modification times and free-space timing. Judge "in use" by the working directory of running processes and "recent" by commit date.
- **Long scans run in the background.** A multi-terabyte `du` takes minutes. Write results to a file in the scratch directory, wait for the completion signal, and do not start a second copy of a scan that is running.
- **Report faithfully.** Free space before and after, read from the filesystem. Name everything refused, failed, skipped or unreadable. If used space does not add up, say how much is unexplained.
- **Privacy.** Paths, project names and user names stay on the machine. Do not paste them into outside services or into files that will be published.

## Workflow

1. **Intent and baseline.** Confirm the goal (free space, how much). Record free space with `df -h` on the data volume (on macOS `/System/Volumes/Data`). `df -h` counts in GiB and TiB; drive sizes are sold in GB and TB.
2. **Quick wins.** Measure tier 1 (regenerable caches, logs, old temp files) from [references/targets.md](references/targets.md). Often tens to hundreds of GiB on a developer machine.
3. **Find the real weight.** In the background, measure top-level folders with `du -x -d 1 -k`, then run `scripts/scan_regenerable.py <root> --out <file>` on the places that hold projects. It is read-only and applies markers: a `target` directory counts only next to `Cargo.toml`, `.build` only next to `Package.swift`. Do not cap the search depth; nested copies are common.
4. **Reconcile.** If visible usage is far below what the filesystem reports, follow [references/accounting.md](references/accounting.md) before promising a result. Usual causes: areas the terminal cannot read (Trash, mail, other users), local snapshots, deleted-but-open files, shared blocks.
5. **Classify worktrees and clones.** Run `scripts/classify_worktrees.py` and apply [references/worktrees.md](references/worktrees.md). Nested repositories need a look at each entry.
6. **Propose.** Show tiers with sizes, largest first, and what each costs to regenerate. Tier 1 can be approved as a group, tier 2 per project, tier 3 item by item. Ask which to run.
7. **Execute in tiers.** Tier 1 with the documented commands. Tier 2 and worktrees with `scripts/remove_listed.py`: dry run, read its refusals, then `--execute`. For worktrees add `--save-patches <dir>`, and `--allow-uncommitted-loss` only for worktrees whose lost changes the user accepted. Run long deletions in the background.
8. **Verify.** Re-read free space. Check that nothing on the list still exists and read every failure. Expect less than the sum of the sizes (shared blocks, open files) and explain the gap instead of hiding it.
9. **Repeat or stop.** If the target is not met, show what remains and who decides it (models, app data, whole projects) with sizes. Do not widen scope on your own.

## Scripts

- `scripts/scan_regenerable.py ROOT [--out FILE] [--min-mib N]`: read-only TSV of regenerable directories, `verified` by marker or `review:<git state>` for generic names.
- `scripts/classify_worktrees.py PATH... [--from-file FILE]`: read-only decision per worktree or clone (`REMOVE`, `REMOVE_LOSES_CHANGES`, `REVIEW_NESTED`, `SKIP_*`).
- `scripts/remove_listed.py LIST --root ROOT --kind artifacts|worktrees [--execute]`: re-validates every path, refuses the unsafe ones, deletes only with `--execute`, prunes worktree metadata. Flags: `--include-review`, `--allow-uncommitted-loss`, `--save-patches DIR`, `--jobs N`.
- `python3 -B scripts/test_harness.py` proves these rules on fixtures.

## Return

Report free space before and after against the target. For each tier: what was removed (count, GiB) and what it costs to regenerate. List what was refused, failed, skipped or left for the user, with sizes. State any loss of uncommitted or untracked work and where patches were saved. Name unexplained space and the areas that could not be read. End with the remaining options ordered by size.
