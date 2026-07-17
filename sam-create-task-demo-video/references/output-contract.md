# Output Contract

Draft and validate JSON before reporting completion.

Required fields:

- `manifest_fingerprint`
- `target`: `base_sha`, `head_sha`
- `intent`: `summary`, `invariants`, `no_go`
- `environment`: `kind`, `identity`, `real_data`, `evidence`
- `authorization`: `publish_requested`
- `command_definitions`: `changed`, `inspected`, `evidence`
- `criteria`, `risks`, `scenarios`, `checks`, `commands`, `artifacts`, `cleanup`
- `plan_audit`: `status`, `evidence`
- `recording`: `real_ui`, `linked_backend`, `requires_linked_backend`, `fallback_reason`
- `publication`: `status`, and verified receipt fields when published
- `decision`: `READY_LOCAL`, `PUBLISHED`, or `BLOCKED`

Use stable IDs `AC-###`, `R-###`, `S-###`, `T-###`, `CMD-###`, `ART-###`,
and `CL-###`. Every reference must be a string and every scenario/check,
check/command, and scenario/artifact link must be reciprocal. Criteria require
nonempty text; risks require evidence or description.

Each final artifact requires MP4 MIME/type, path, SHA-256, positive duration and
dimensions, video stream, conversion pass, playback verification, contact-sheet
review, privacy pass, and linked scenarios.

`READY_LOCAL` and `PUBLISHED` are invalid with unsafe environment, failed plan
audit, uninspected changed commands, failed proof commands, invalid media, missing
privacy/playback proof, dishonest real-UI claims, or blocked cleanup. `PUBLISHED`
also requires explicit authorization, host upload (not a git commit), player-or-
image embed markup (never a hyperlink-only body), and successful remote readback
showing a rendered video player or image. When publication is requested, the
result cannot remain `READY_LOCAL` or `NOT_REQUESTED`; a blocked publication
requires a concrete reason or error.

`recording.real_ui` must be `true` when the demo used the product UI and linked
backend. If `real_ui` is `false`, `fallback_reason` is required and the demo must
not be described as a real linked UI walkthrough. Do not claim success for a
demo-only component built while the real product surface was available.
