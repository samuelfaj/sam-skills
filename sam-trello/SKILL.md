---
name: sam-trello
description: "Build, rewrite, reconcile and maintain a Trello board as a project manager: numbered tasks, simple cards from a fixed template, dependency links, client prefix, label and assignee, images. Use when the user runs /sam-trello, asks to organize or sync a Trello board, or to add dependencies to its cards."
---

# Sam Trello

Turn source material (merge request, client documents, plans, an existing board) into a Trello board that a person or agent with no project context can pick up and finish. The board is the product: every card must say what to do, in what order, and when it is done.

## Non-Negotiable Contract

- **Language.** Write every card in the language the user asks for. Default to en-US when none is given. Translate the template headings, the dependency headings and the task word ("Task") into that language, unless the user names exact headings; then keep those literally. Keep code, paths, commands and identifiers as they are.
- **Plain writing.** Short sentences, one idea per line, no filler, no em or en dashes, no invented abbreviations. Explain every technical term the first time. Run the text through the `humanizer` skill when it is installed, and aim for well under 15 words per sentence on average.
- **Facts only.** Every claim in a card comes from a source you read or a command you ran: the MR at its newest revision, the client documents, the repository, the CI result. Record the revision and date. Mark what you could not verify. Never invent numbers, norms, owners or dates.
- **No secrets.** Never put passwords, tokens or connection strings in a card, a receipt or an answer. Say where the secret lives.
- **Reversible first.** Archive merged or replaced cards instead of deleting them. Delete only cards that match no source (for example a connection test card) and say why. Do not touch cards you were not asked to change, and keep existing attachments and covers.
- **Authority.** The request authorizes the board edits it names. It does not authorize merging, deploying, or changing the repository. Do not log in for the user, bypass a login, or use another account.
- **Clean up.** Close every browser tab you opened and verify it. Remove any helper element you injected into a page.

## Workflow

1. **Read the sources** the user gave (MR, PDFs, plan files, repository, CI). Fetch the newest state first. Read client documents as images when text hides the layout. Write down which source supports each card.
2. **Read the board** before changing it. Export lists, labels, open cards (name, description, list, position, labels, members, attachments, cover) to a local file. This is the "before" state and your undo map.
3. **Reconcile.** Map every existing card to one outcome: keep and rewrite, merge into another, split, archive, or delete. Create the cards that sources need and the board lacks. Merge cards that share one rule, one code path and one test. Split cards that hide two outcomes. List each merge with its reason and confirm no item of the old Definition of done was lost.
4. **Write the cards** with [references/card-template.md](references/card-template.md): numbered titles, the fixed template, the dependency section, evidence and exclusions.
5. **Order and link.** Number tasks so every dependency has a lower number than the task that needs it. Write the links in both directions, as in [references/dependencies.md](references/dependencies.md). Put cards in lists that match their state and sort them by number.
6. **Client prefix, label, assignee.** When the user names a client, prefix every title with `<Client> - `, add the label `Client: <Client>` (translated), and assign the named member to every card. Look up the member id first and use the user's exact handle.
7. **Images.** Attach the best image from the sources to each card that has one, and set it as the cover. Render PDF pages to JPEG and compress large mockups first. Say why a card has no image.
8. **Apply** through [references/trello-access.md](references/trello-access.md). Write in small idempotent batches, find cards by id or exact name, and skip work already done so a rerun is safe.
9. **Verify by reading back.** Export the board again and run `scripts/lint_board.py` on it (see below). Fix every error and rerun. Read at least five random cards in full as a newcomer would.
10. **Report** what changed, what you merged or archived and why, and what you could not verify.

## Lint

`scripts/lint_board.py <export.json> --prefix <Client>` checks the contract on an export of open cards: numbered titles with the client prefix, no gaps or duplicates, the five template sections plus Dependencies in order, no dashes, sentence length, label and assignee on every card (`--label`, `--member` take ids), and dependency links that exist, point to lower numbers, and match in both directions. Pass `--task-word`, `--headings`, `--dependencies-heading`, `--before-label` and `--after-label` for a language other than English. Run `python3 -B scripts/test_lint_harness.py` to prove the linter itself.

## Return

Report the board URL, card counts per list, the merge and archive map, the check results (lint and the cards you read), the image coverage, and every claim you could not verify. Name the cleanup you did (tabs closed, helper elements removed).
