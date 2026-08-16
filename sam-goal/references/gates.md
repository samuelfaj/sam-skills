# Gates

The file is the contract. A checkbox is a claim. Evidence is the proof.

```markdown
# Gates: <scope name>

Scope: <one line>

- [ ] G1: <observable outcome>
  CHECK: <shell command>
  EXPECT: <substring or /regex/>
  EVIDENCE: pending

- [ ] G2: <manual outcome>
  EVIDENCE: pending

ABANDON: G2 <reason, only if surrendered>
```

## Parse rules

- A gate starts at `- [ ]` or `- [x]` (`x` case-insensitive).
- Indented `CHECK:`, `EXPECT:`, `EVIDENCE:` lines belong to the gate above.
- `EXPECT` is a substring of combined stdout+stderr, or `/pattern/flags`
  as a regular expression. With `EXPECT`, the match decides even if the
  command exits non-zero. Without `EXPECT`, exit 0 decides.
- `ABANDON: <id> <reason>` anywhere in the file resolves that gate. Reports
  must still list it.

`scripts/check_gates.py` flips a box and fills `EVIDENCE` only when the
check passes. `--status` reports and writes nothing.

## Unmet

A gate is unmet when any of these hold and no `ABANDON` names it:

1. The box is unchecked.
2. The box is checked and `EVIDENCE` is missing or still `pending`.

Checked-without-evidence is worse than unchecked. It is the premature
done-report this format exists to make visible.

## Writing

- State outcomes, not activities. "Three tiers render with real copy" is
  checkable. "Work on pricing" is not.
- Prefer a `CHECK`. If you cannot name one, the outcome may not be
  observable yet. Sharpen it.
- Make `EXPECT` decisive (`3/3 tiers ok`), not a word that appears either
  way (`done`).
- Cap evidence to the deciding tail, or `path:line` for manual gates.
- Five to twelve gates per leaf. Two means under-specified; twenty means
  the leaf should have been two leaves.
- Any number that will appear in the final report gets its own measuring
  `CHECK`. Re-run those checks at report time.

Default files: `$GOAL_DIR/GATES.md` and `$GOAL_DIR/gates/*.md`.
