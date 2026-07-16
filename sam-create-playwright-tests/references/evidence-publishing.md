# Evidence Publishing

Read this file only after the user explicitly requests external publication.

## Authorization gate

Resolve the exact host, repository, proposal ID, expected head SHA, and requested
artifact set. Reconfirm the current head immediately before publishing. Stop if
the target changed or authorization is ambiguous.

## Artifact safety

- Keep only unique evidence that proves an acceptance criterion or risk.
- Inspect every frame or trace surface for credentials, tokens, cookies, private
  data, internal URLs, and customer identifiers.
- Convert browser recordings to a broadly compatible MP4 only when requested.
- Never commit generated evidence unless the user explicitly asks.

## Publication

Use the platform capability available in the target environment. Keep host-
specific commands out of the core workflow. Record the attempted command or API,
remote receipt, resulting URL, and readback status.

For uploaded evidence, re-read the remote comment or note and confirm the exact
artifact is present. Report `BLOCKED` or `PARTIAL` when upload or readback fails;
never substitute a local path as a remote receipt.
