# Trello access

## Contents

- Choose the access path
- Session in the user's browser
- Reads
- Writes
- Attachments and covers
- Members and labels
- Slow background tabs
- Cleanup

## Choose the access path

1. A Trello integration or MCP tool, when the host has one connected. Prefer it.
2. The user's signed-in Chrome through a browser tool that opens a background tab (for example the mac-use MCP). Use this when the user says to use their Chrome or when no integration exists. Do not ask for the user's password and do not sign in on their behalf. If the session is signed out, stop and ask the user to sign in.
3. An API key and token the user provides. Keep them out of files and answers.

## Session in the user's browser

1. Check the browser status. Reuse nothing you do not own.
2. Open a light page on the same site so no heavy app loads, for example `https://trello.com/1/members/me?fields=username`.
3. Run requests with JavaScript in that tab using `fetch` with `credentials: 'include'`. Same-origin paths such as `/1/boards/<id>` work.
4. If the user selects your tab, you get a human-activity error. Release the tab, open a new background tab, and continue. Do not fight for the tab.

## Reads

`GET` needs no token. Export a board in one call:

`/1/boards/<boardId>?lists=all&cards=all&card_attachments=true&labels=all&fields=name&card_fields=name,desc,closed,idList,idLabels,idMembers,cover,pos,shortUrl`

Return only compact fields to the agent. Large results are saved by the tool to a local file: parse that file with a script instead of reading it by eye.

## Writes

`PUT`, `POST` and `DELETE` from the page fail with `403 REQUEST_CSRF_ERROR` when you send the session cookie value as `token`. They work when you send the value of the `dsc` cookie as a field named `dsc` in the JSON body (or in the form data for uploads):

```js
const dsc = document.cookie.match(/dsc=([^;]+)/)[1]
await fetch('/1/cards/<id>', {
  method: 'PUT', credentials: 'include',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ dsc, name, desc, idList, pos, idLabels: 'a,b', idMembers: 'x' }),
})
```

Never print the cookie value. Check `response.ok` and keep a log of failures per card.

- Archive a card with `{ closed: true }`.
- Move a card with `idList` and `pos`.
- `idLabels` and `idMembers` replace the whole set: read the current ids and add yours.
- Names are matched exactly. Make each batch idempotent: look up cards by id or name first.

## Attachments and covers

1. Build local files first (render PDF pages to JPEG, compress big images).
2. Create a temporary `<input type="file">` in the tab, set its files with the browser tool's file-upload call, and read them in page JavaScript.
3. Upload with `POST /1/cards/<id>/attachments` using `FormData` with fields `dsc`, `file` and `name`.
4. Set the cover with `PUT /1/cards/<id>` and `{ idAttachmentCover: <attachmentId> }`.
5. Do not upload the same attachment twice: compare names with the card's current attachments.
6. Remove the temporary input when you finish.

## Members and labels

- Look up a member with `GET /1/members/<username>?fields=username,fullName` and use the id. Check that the member is on the board.
- Create a label with `POST /1/labels` (`name`, `color`, `idBoard`). Reuse it if it exists.

## Slow background tabs

A background tab throttles timers, so a loop over many cards takes seconds per card. Start the loop without waiting for it (store progress in `window.__log`), poll the log with short calls, and do not rerun the whole batch.

## Cleanup

1. Remove injected elements and clear the `window` variables you set.
2. Close the tab you opened and check the browser status shows no tab.
3. Delete local export files that hold card text if the user asked for no copies.
