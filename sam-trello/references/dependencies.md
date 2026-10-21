# Dependencies

## Contents

- Rules
- Section format
- How to decide
- Order of the board
- Check

## Rules

1. Number tasks so a task depends only on lower numbers. A developer takes the lowest open number and checks its dependencies.
2. Every link is written twice: if task 9 needs task 7, task 9 lists 7 under "Finish these first" and task 7 lists 9 under "Unlocks".
3. Link to the Trello card with its short URL, and use the full card title as the link text.
4. Depend on a card only for a real reason: it provides data, code, a decision or an environment that this card uses. Do not chain cards just to keep them in order.
5. A task with no dependency writes "None." A task that unlocks nothing writes "None."
6. A decision card is a dependency of every card its answer can change.
7. Put work that depends on outside material (client files, tokens, answers) behind a card that asks for that material.
8. Cards that can run in parallel get no link between them.

## Section format

The heading and the two labels are translated to the requested language. In English:

```
## Dependencies

Finish these first:
- [Client - Task 3: Area - title](https://trello.com/c/XXXX): reason in one short sentence.

Unlocks:
- [Client - Task 12: Area - title](https://trello.com/c/YYYY)
```

Keep the labels identical on every card so they can be checked by a script.

## How to decide

1. List what each card needs: data, code, test setup, a decision, a review pass.
2. Find the card that provides each need. That card is a dependency.
3. Sort the cards so providers come first (a topological order). Break ties by risk, then by size.
4. Put the setup and reading cards first (what the board is, how to run the project).
5. Put verification that needs everything (device tests, client approval) last.

## Order of the board

Within each list, order cards by number. Do not move a card to a different list only to fix the order. The number carries the order.

## Check

Run `scripts/lint_board.py` on an export of the board. It fails on a missing section, a link to a card that does not exist, a dependency that points to an equal or higher number, and a link that is not repeated on the other card.
