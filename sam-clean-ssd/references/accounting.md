# Reconciling Used Space

Compare the space the filesystem reports as used with the sum of what you can see. A gap of more than a few percent needs an explanation before you promise a result.

## Checks, in order

1. **Units.** `df -h` counts in GiB and TiB (1024-based). Drives are sold in GB and TB, so 3.6 TiB is about 4.0 TB.
2. **Container versus volume.** On APFS several volumes share one container. `diskutil info /System/Volumes/Data` shows the container free space, which is what you can actually gain.
3. **Local snapshots.** `tmutil listlocalsnapshots /` shows snapshots that hold deleted data until they expire.
4. **Unreadable areas.** A terminal without Full Disk Access cannot read the Trash, Mail, Messages, Safari, or other users' folders. `du` then prints "Operation not permitted" or reports tiny sizes (a container folder of a few MB on a busy machine is a hint). Ask the user to read the size in the system Storage settings, or to grant access; do not work around it. A script can ask the file manager for the Trash item count, but not the size of folders inside it.
5. **Deleted but open.** `lsof +L1` lists files removed while a process still holds them. Their space returns when the process exits. Usually small.
6. **Shared blocks.** On copy-on-write filesystems a cloned directory costs little extra, and deleting one copy frees only what it alone owned. `du` counts every copy in full, so expect to free less than the total you remove.
7. **Mounts.** `du -x` does not cross filesystems. Other volumes and disk images are separate numbers.
8. **System-managed space.** Purgeable data and operating system caches are the system's to reclaim. Report them, do not delete them.

## Background scans

`du` over terabytes takes minutes. Run it in the background and write to a file in the scratch directory, then wait for the completion signal. macOS has no `timeout` command. Prefer `du -x -d 1 -k <folders> | sort -rn` per top-level folder, then drill into the largest. Do not pipe a long scan into a command that buffers its output until the end.

## Expected versus actual

After deleting, compare the free space gained with the sum of the sizes removed. Record the shortfall. Attribute it to shared blocks or open files only when a check from the list supports it.
