# Evidence Publishing

Read this file only after explicit publication authorization.

## Freeze the remote target

Resolve host, repository, proposal ID, expected head SHA, and requested artifact.
Re-read the current head immediately before publication. Stop on drift.

## Publish

Use the available host capability or CLI. Upload the exact validated MP4; do not
commit generated media unless separately requested. Keep host-specific mechanics
out of the core skill.

Record command or API, remote artifact identifier, comment/note identifier, URL,
status, and error when applicable. Never construct an unverified link manually.

## Verify

Read the remote comment or note back. Confirm the validated video appears in the
host-supported uploaded format and the proof description names the exact scenario.

Return `BLOCKED` when upload, comment creation, permission, target drift, or
readback fails. A local path is not a remote receipt.
