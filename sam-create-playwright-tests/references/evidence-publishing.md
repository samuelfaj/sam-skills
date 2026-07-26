# Evidence Publishing

Read this file when Playwright videos, screenshots, or traces must leave the
local machine for a PR/MR.

## Contents

1. Non-negotiable rules
2. What to publish
3. Embed markup
4. Upload procedure
5. Body composition checklist
6. Verification
7. Failure modes

## Non-negotiable rules

1. **Never commit** generated videos, screenshots, traces, reports, or
   recordings into the git branch, working tree commit, LFS, or release assets
   that land on the product branch. Host them only as platform uploads.
2. **Never publish media as a hyperlink.** Forbidden patterns include
   `[Download](url)`, `[video](url)`, `[![thumb](img)](video)`, raw
   “click here” anchors, and repository blob/raw URLs.
3. **Videos must render as an inline/native player.** Screenshots and other
   images must render as **inline images**. A downloadable file link alone is a
   failed publication.
4. Prefer **PR/MR description** when the media is primary proof for the change.
   Use a **PR/MR comment/note** when appending evidence after the description is
   already settled, or when the host makes description edits unsafe.
5. Reconfirm host, repository, proposal ID, and expected head SHA immediately
   before upload. Stop on drift.
6. Privacy-scan every frame or surface first. Do not upload secrets, tokens,
   cookies, private customer data, or production identifiers.

## What to publish

Keep traces and HTML reports local unless the user explicitly asks for them.
When publication is authorized (or required by the parent workflow):

- Upload every Playwright **video** that proves a required scenario.
- Upload selected **screenshots** that prove a required scenario when video is
  unavailable or insufficient.
- Convert browser recordings to a compatible MP4 when the host or reviewer
  requires it; keep the validated file local until upload.

Inventory every candidate file with path + SHA-256 before upload. After upload,
every inventoried video must have a receipt and player readback.

## Embed markup (required)

### GitLab (GLFM)

Upload returns markdown of the form `![alt](/uploads/<hash>/<file>)`.

Use that image syntax for **both** videos and images. GitLab converts video
extensions (`.mp4`, `.m4v`, `.mov`, `.webm`, `.ogv`) into a video player and
image extensions into an image.

```markdown
### Browser e2e — void refreshes family ledger

![void refreshes family ledger](/uploads/<hash>/void.webm)

### Screenshot — network proof

![network proof](/uploads/<hash>/network.png)
```

**Do not** use HTML `<video>` tags, HTML `<a>` download links, or
`[label](url)` link syntax for evidence.

Optional width control (still player/image, not a link):

```markdown
![void](/uploads/<hash>/void.webm){width=100%}
```

### GitHub

Host-uploaded attachment URLs under `https://github.com/user-attachments/assets/`
(or the host-issued equivalent) are required.

| Media | Required body form | Renders as |
| --- | --- | --- |
| Video (`.mp4`, `.mov`, `.webm`) | Bare attachment URL alone on its own line (no markdown link wrapper) | Inline video player |
| Image (`.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`, `.svg`) | `![descriptive alt](https://github.com/user-attachments/assets/<id>)` | Inline image |

```markdown
### Browser e2e — void refreshes family ledger

https://github.com/user-attachments/assets/<uuid>

### Screenshot — network proof

![network proof](https://github.com/user-attachments/assets/<uuid>)
```

**Do not** wrap video URLs in `[text](url)`. Repository
`raw.githubusercontent.com` / blob URLs are not valid evidence embeds.

## Upload procedure

### GitLab — `glab`

```bash
glab api --method POST \
  "projects/<urlencoded-namespace%2Fproject>/uploads" \
  --form "file=@/absolute/path/to/test-video.webm"
```

Use the response `markdown` field verbatim in the description or note.

```bash
glab mr update <iid> -R <namespace/project> --description "$(cat body.md)"
# or
glab mr note <iid> -R <namespace/project> --message "$(cat body.md)"
```

Keep the real media extension on the uploaded filename so GLFM selects player
vs image correctly.

### GitHub — `gh`

```bash
gh image --repo <owner/repo> /absolute/path/to/test-video.webm
gh image --repo <owner/repo> /absolute/path/to/shot.png
```

For video bodies, place the bare `user-attachments` URL on its own line. For
images, keep `![alt](url)`.

```bash
gh pr edit <number> --repo <owner/repo> --body-file body.md
# or
gh pr comment <number> --repo <owner/repo> --body-file body.md
```

If `gh image` is unavailable, use another path that still yields a proven
user-attachment player URL—not a branch commit and not a raw blob URL.

## Body composition checklist

- [ ] No media path is staged or committed on the task branch.
- [ ] Every video uses host player markup (GL: `![alt](…video)`; GH: bare
      user-attachments URL).
- [ ] Every image uses `![alt](url)`.
- [ ] Zero `[label](media-url)` download links for evidence.
- [ ] Zero raw/blob/repository file URLs for evidence.
- [ ] Scenario / test IDs sit above each embed.

## Verify (mandatory)

1. Read the remote description or note back via API/CLI.
2. Confirm the body contains the required player/image markup (not a link).
3. Confirm a native player (video) or image appears on the proposal surface.
4. Record under `ART-###`: local path, SHA-256, host, proposal ID, upload
   receipt, embedded markup, comment/description ID, and `player_verified` /
   `image_verified` with readback evidence.

## Failure modes

Report `BLOCKED` or `PARTIAL` (never claim successful remote publication) when:

- Upload, description update, or comment creation fails.
- Head or proposal identity drifted.
- Readback shows only a hyperlink, blob URL, or missing attachment.
- Media was committed to the branch.
- Privacy review failed.

A local filesystem path is never a remote receipt.
