# Card template

## Contents

- Title
- Description layout
- Writing rules
- Lists and labels
- Example

## Title

`<Client> - <Task word> <N>: <Area> - <what to do>`

- Example in English: `Acme - Task 22: App - generate the visit PDF`.
- Example in Portuguese: `Acme - Tarefa 22: App - gerar o PDF da visita`.
- `N` runs from 1 without gaps. Do not use phrases like "Slice 3" or "Step 3".
- The area names the part of the product (App, Panel, Portal, Security, Decision).
- The text says the action, not the topic.

## Description layout

Use these headings, in this order, as Markdown `##` headings. Translate them to the requested language unless the user fixed exact names.

1. **Context.** Why this card exists, what already exists, where the code is. Include the source (document, page, MR) and the revision or date.
2. **Dependencies.** Two lists with links. See `dependencies.md`.
3. **Goal.** One sentence that states the result.
4. **Scope.** What to do, as numbered steps when order matters. Give the exact command or file when you know it.
5. **Definition of done.** Checks anyone can run. Each line is true or false. Include the expected values.
6. **Exclusions.** What not to do. Always include: do not merge, do not publish, do not paste secrets, unless the user said otherwise.

Put a short "Where the code is" list inside Context or Scope when files matter: path, function, line.

## Writing rules

- One idea per line. Short sentences. Active voice.
- Define terms once ("merge request (a proposal to join code)").
- Use code formatting for commands, paths, names and values.
- Never invent a number, norm, date or owner. Write "not verified" and say what is missing.
- A card that asks for a decision says who decides and which answers are possible.
- A card that depends on missing material names the material and links the card that asks for it.

## Lists and labels

- Lists that work well: Read first, Backlog, Blocked or waiting for a decision, To do, Doing, Review, Done.
- Put a card in Review only when its code exists and needs checking. Put it in Done only when it is merged.
- Name labels by area plus one label per client (`Client: <Client>`, translated). Do not leave color-only labels.

## Example

```
## Context

The technician starts a visit from the app.
The code is on branch `feat/field` (merge request !40).

## Dependencies

Finish these first:
- [Acme - Task 7: App - find equipment by tag](https://trello.com/c/AAAA)

Unlocks:
- [Acme - Task 9: Panel - filter visit history](https://trello.com/c/BBBB)

## Goal

The visit starts only inside the customer area.

## Scope

1. Open the visit in the app.
2. Set the GPS to the customer point and tap "Register location".
3. Run `cd e2e/playwright && bunx playwright test tests/visit.spec.ts`.

## Definition of done

- Inside the area, the server answers 200 and the start time is saved.
- Outside the area, the server answers 400 and the start time stays empty.

## Exclusions

- Do not change the radius.
- Do not merge or publish.
```
