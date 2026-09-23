# Evidence Publishing

## Rules

1. Host media only as platform uploads. Upload each validated file once; skip a hash already uploaded to that proposal.
2. Never publish media as a hyperlink: no `[Download](url)`, `[video](url)`, `[![thumb](img)](video)`, "click here" or "Download MP4" anchors, HTML `<a>` download links, or repository blob/raw URLs. A downloadable link alone is a failed publication.
3. Video renders as an inline/native player; screenshots and other images render inline.
4. Primary proof goes in the PR/MR description; use a comment/note to append after the description is settled or when description edits are unsafe. Put scenario/test IDs above each embed.
5. Immediately before upload, reconfirm host, repository, proposal ID, and expected head SHA; stop on drift.
6. Privacy-scan every frame or surface first: no secrets, tokens, cookies, private customer data, or production identifiers.

## What to Publish

- Every video that proves a required scenario; selected screenshots when video is unavailable or insufficient. Traces and HTML reports stay local unless explicitly requested.
- Convert recordings to a compatible MP4 when the host or reviewer requires it; keep the validated file local until upload and keep its real media extension.
- Inventory every candidate (path + SHA-256) before upload. After upload, every inventoried video has a receipt and player readback.

## Per Host

| Step | GitLab (`glab`) | GitHub (`gh`) |
| --- | --- | --- |
| Upload | `glab api --method POST "projects/<urlencoded-namespace%2Fproject>/uploads" --form "file=@/abs/video.webm"`; use the response `markdown` verbatim | `gh image --repo <owner/repo> /abs/video.webm` (images the same); if unavailable, any path yielding a proven `user-attachments` URL, never a branch commit or raw blob URL |
| Video embed | `![alt](/uploads/<hash>/<file>)`; `.mp4`, `.m4v`, `.mov`, `.webm`, `.ogv` render as a player; optional `{width=100%}`; no HTML `<video>` | bare `https://github.com/user-attachments/assets/<id>` alone on its own line, never wrapped in `[text](url)` |
| Image embed | `![alt](/uploads/<hash>/<file>)` | `![descriptive alt](https://github.com/user-attachments/assets/<id>)` |
| Write | `glab mr update <iid> -R <namespace/project> --description "$(cat /abs/body.md)"` or `glab mr note <iid> -R <namespace/project> --message "$(cat /abs/body.md)"` | `gh pr edit <n> --repo <owner/repo> --body-file /abs/body.md` or `gh pr comment <n> --repo <owner/repo> --body-file /abs/body.md` |
| Readback | `glab api "projects/<urlencoded>/merge_requests/<iid>" \| python3 -c 'import json,sys;print(json.load(sys.stdin)["description"])' > /abs/readback.md`; a note: `.../merge_requests/<iid>/notes/<note_id>`, key `body` | `gh pr view <n> --repo <owner/repo> --json body --jq .body > /abs/readback.md`; a comment: `gh api repos/<owner/repo>/issues/comments/<id> --jq .body > /abs/readback.md` |

## Verify (mandatory)

Read the description or note back (last row) and count occurrences, without screenshots, rendered HTML, or reading the whole file:

```bash
grep -oE '^https://github.com/user-attachments/assets/[^ ]+$' /abs/readback.md | wc -l  # GitHub videos
grep -oE '!\[[^]]*\]\(https://github.com/user-attachments/assets/' /abs/readback.md | wc -l  # GitHub images
grep -oE '!\[[^]]*\]\(/uploads/' /abs/readback.md | wc -l  # GitLab videos + images
grep -oE '(^|[^!])\[[^]]*\]\([^)]*(user-attachments|/uploads/|\.(mp4|m4v|mov|webm|ogv|png|jpe?g|gif|webp))|\]\([^)]*\)\]\([^)]*(user-attachments|/uploads/|\.(mp4|m4v|mov|webm|ogv))|<(a|video)[^>]*(user-attachments|/uploads/|\.(mp4|m4v|mov|webm|ogv))|(/blob/|/raw/|raw\.githubusercontent)[^ )]*\.(mp4|m4v|mov|webm|ogv|png|jpe?g|gif|webp)' /abs/readback.md | wc -l  # forbidden forms
```

Embed counts must equal the expected videos and images, forbidden forms must be 0, and no media path is staged or committed. Record per `ART-###`: local path, SHA-256, host, proposal ID, upload receipt, embedded markup, description/comment ID, and `player_verified` or `image_verified` with the readback evidence.

## Failure

Stop and report `BLOCKED` or `PARTIAL`, never successful publication, when an upload, description update, or comment fails; head or proposal identity drifted; readback shows only a hyperlink, blob URL, or missing attachment; media was committed to the branch; or privacy review failed. A local filesystem path is never a remote receipt.
