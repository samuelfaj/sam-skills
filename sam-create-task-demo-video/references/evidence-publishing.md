# Evidence Publishing

Read this file when media must leave the local machine for a PR/MR.

## Non-negotiable rules

1. **Never commit** generated videos, screenshots, contact sheets, traces, or
   recordings into the git branch, working tree commit, LFS, or release assets
   that land on the product branch. Host them only as platform uploads.
2. **Never publish media as a hyperlink.** Forbidden patterns include
   `[Download](url)`, `[video](url)`, `[![thumb](img)](video)`, raw
   “click here” anchors, and repository blob/raw URLs.
3. **Videos must render as an inline/native player.** Images must render as
   **inline images**. A downloadable file link alone is a failed publication.
4. Prefer **PR/MR description** when the media is primary proof for the change.
   Use a **PR/MR comment/note** when appending evidence after the description is
   already settled, or when the host makes description edits unsafe.
5. Reconfirm host, repository, proposal ID, and expected head SHA immediately
   before upload. Stop on drift.
6. Privacy-scan every frame first. Do not upload secrets, tokens, cookies,
   private customer data, or production identifiers.

## Embed markup (required)

### GitLab (GLFM)

Upload returns markdown of the form `![alt](/uploads/<hash>/<file>)`.

Use that image syntax for **both** videos and images. GitLab converts video
extensions (`.mp4`, `.m4v`, `.mov`, `.webm`, `.ogv`) into a video player and
image extensions into an image.

```markdown
### Demo — void refreshes family ledger

![void refreshes family ledger](/uploads/<hash>/demo.mp4)

### Screenshot — ledger after restore

![ledger after restore](/uploads/<hash>/after.png)
```

**Do not** use HTML `<video>` tags, HTML `<a>` download links, or
`[label](url)` link syntax for evidence.

Optional width control (still player/image, not a link):

```markdown
![demo](/uploads/<hash>/demo.mp4){width=100%}
```

### GitHub

Host-uploaded attachment URLs under `https://github.com/user-attachments/assets/`
(or the host-issued equivalent) are required.

| Media | Required body form | Renders as |
| --- | --- | --- |
| Video (`.mp4`, `.mov`, `.webm`) | Bare attachment URL alone on its own line (no markdown link wrapper) | Inline video player |
| Image (`.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`, `.svg`) | `![descriptive alt](https://github.com/user-attachments/assets/<id>)` | Inline image |

```markdown
### Demo — void refreshes family ledger

https://github.com/user-attachments/assets/<uuid>

### Screenshot — ledger after restore

![ledger after restore](https://github.com/user-attachments/assets/<uuid>)
```

**Do not** wrap video URLs in `[text](url)` or `![alt](url)` unless the host
readback proves a player still renders. Prefer the bare attachment URL for
video. Repository `raw.githubusercontent.com` / blob URLs are not valid evidence
embeds.

## Upload procedure

### GitLab — `glab`

```bash
# Upload one file; response includes markdown + url
glab api --method POST \
  "projects/<urlencoded-namespace%2Fproject>/uploads" \
  --form "file=@/absolute/path/to/demo.mp4"
```

Response fields:

- `markdown` — use this string verbatim in the description or note (already
  `![alt](/uploads/...)`).
- `url` / `full_path` — record as the upload receipt identifier.

Publish into the proposal:

```bash
# Description (preferred for primary demo)
glab mr update <iid> -R <namespace/project> --description "$(cat body.md)"

# Or comment/note
glab mr note <iid> -R <namespace/project> --message "$(cat body.md)"
```

Ensure the uploaded filename keeps a video or image extension so GLFM chooses
player vs image correctly.

### GitHub — `gh`

Prefer session-backed user-attachment upload so URLs render as native players:

```bash
# Images and videos via user-attachments (prints ![alt](url) for images;
# for video, place the bare user-attachments URL alone on its own line)
gh image --repo <owner/repo> /absolute/path/to/file.mp4
# or
gh image --repo <owner/repo> /absolute/path/to/shot.png
```

If `gh image` is unavailable, use another host path that still yields a
`user-attachments` (or equivalent) URL proven to render a player—not a branch
commit and not a raw blob URL.

Publish:

```bash
# Description
gh pr edit <number> --repo <owner/repo> --body-file body.md

# Or comment
gh pr comment <number> --repo <owner/repo> --body-file body.md
```

When composing `body.md` for GitHub videos, insert the attachment URL as a
standalone line so the UI shows a player. For images, keep `![alt](url)`.

## Body composition checklist

Before writing the remote body:

- [ ] No media path is staged or committed on the task branch.
- [ ] Every video uses host player markup (GL: `![alt](…mp4)`; GH: bare
      user-attachments URL).
- [ ] Every image uses `![alt](url)`.
- [ ] Zero `[label](media-url)` download links for evidence.
- [ ] Zero raw/blob/repository file URLs for evidence.
- [ ] Scenario titles sit above each embed so reviewers know what they prove.

## Verify (mandatory)

1. Read the remote description or note back via API/CLI.
2. Confirm the body contains the required player/image markup (not a link).
3. Open or render-check the proposal surface when possible and confirm a native
   player (video) or image (screenshot) appears.
4. Record under `ART-###`: local path, SHA-256, host, proposal ID, upload
   receipt, embedded markup, comment/description ID, and `player_verified` /
   `image_verified` with readback evidence.

## Failure modes

Return `BLOCKED` (do not claim `PUBLISHED`) when:

- Upload, description update, or comment creation fails.
- Head or proposal identity drifted.
- Readback shows only a hyperlink, blob URL, or missing attachment.
- Media was committed to the branch.
- Privacy review failed.

A local filesystem path is never a remote receipt.
