# Evidence Publishing

## Rules

- Forbidden media forms: `[Download](url)`, `[video](url)`, reference-style `[x][1]` links, `[![thumb](img)](video)`, "click here" or HTML `<a>` download anchors, HTML `<video>` tags, repository blob/raw/LFS URLs (`raw.`/`media.githubusercontent.com`). A downloadable link alone is a failed publication.
- Prefer the PR/MR **description** when the media is primary proof; use a **comment/note** to append after the description is settled or when description edits are unsafe.
- Immediately before upload, reconfirm host, repository, proposal ID, and expected head SHA; stop on drift.
- Put a scenario title above each embed. Keep a video or image extension on every uploaded filename.

## Per Host

| Host | Upload | Video embed | Image embed |
| --- | --- | --- | --- |
| GitLab | `glab api --method POST "projects/<urlencoded-ns%2Fproject>/uploads" --form "file=@/abs/demo.mp4"`; paste the response `markdown` verbatim; `url`/`full_path` is the receipt | returned `![alt](/uploads/<hash>/demo.mp4)` — GLFM plays `.mp4 .m4v .mov .webm .ogv`; `{width=100%}` optional | `![alt](/uploads/<hash>/shot.png)` |
| GitHub | `gh image --repo <owner/repo> /abs/file`, or another host path yielding a rendering `https://github.com/user-attachments/assets/<id>` URL | bare attachment URL alone on its own line (`.mp4 .mov .webm`); never wrapped in `[..](..)` or `![..](..)` | `![alt](https://github.com/user-attachments/assets/<id>)` (`.png .jpg .jpeg .gif .webp .svg`) |

Publish the composed body:

```bash
glab mr update <iid> -R <ns/project> --description "$(cat <tmp>/body.md)"   # or: glab mr note <iid> -R <ns/project> --message "$(cat <tmp>/body.md)"
gh pr edit <number> --repo <owner/repo> --body-file <tmp>/body.md          # or: gh pr comment <number> --repo <owner/repo> --body-file <tmp>/body.md
```

## Verify (mandatory)

Read the body back through the API into a file and count embeds. Never print the whole body, fetch the rendered page, or take screenshots.

```bash
gh pr view <number> --repo <owner/repo> --json body -q .body > <tmp>/readback.md          # comment: gh api repos/<owner/repo>/issues/comments/<id> -q .body
glab api "projects/<urlencoded-ns%2Fproject>/merge_requests/<iid>" \
  | python3 -c 'import json,sys;print(json.load(sys.stdin)["description"])' > <tmp>/readback.md   # note: .../notes/<id>, key "body"
python3 <skill>/scripts/count_embeds.py <tmp>/readback.md --video-url <url> --image-url <url>
```

Pass every uploaded URL from its upload receipt (GitLab: the response `url`), repeating the flag per file. `PASS` (each URL in its host's player/image form outside code and comments, zero media links) sets `readback_verified: true`. Record per artifact: local path, SHA-256, host, proposal ID, upload receipt (a local path is never one), embed markup, description/comment ID, and the `count_embeds.py` line.

## BLOCKED, never `PUBLISHED`, when

- upload, description update, or comment creation fails;
- head or proposal identity drifted;
- `count_embeds.py` prints `FAIL` for the readback;
- media was committed to the branch;
- privacy review failed.
