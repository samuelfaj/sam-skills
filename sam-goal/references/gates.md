# Gates

The file is the contract. A checkbox is a claim. Evidence is the proof.

## Parse rules

- A gate starts at `- [ ]` or `- [x]` (`x` case-insensitive), e.g. `- [ ] G1: <observable outcome>`.
- Indented `CHECK:`, `EXPECT:`, `EVIDENCE:` lines belong to the gate above.
- `EXPECT` is a substring of combined stdout+stderr, or `/pattern/flags` as a regular expression. With `EXPECT`, the match decides even if the command exits non-zero. Without `EXPECT`, exit 0 decides.
- Unmet: the box is unchecked, or it is checked while `EVIDENCE` is missing or still `pending`, and no `ABANDON` names it. Checked-without-evidence is worse than unchecked: it is the premature done-report this format exists to expose.
- `ABANDON: <id> <reason>` anywhere in the file resolves that gate; the report must still list it. It is the honest exit for an impossible gate; silent scope-narrowing is not.

`check_gates.py` runs the `CHECK` of each unmet gate and, only on a pass, flips the box and fills `EVIDENCE` with the deciding tail. `--status` reports and writes nothing; `--recheck` is SKILL.md step 8.

## Writing

- State outcomes, not activities. "Three tiers render with real copy" is checkable; "Work on pricing" is not.
- Prefer a `CHECK`. If you cannot name one, the outcome may not be observable yet; sharpen it.
- Make `EXPECT` decisive (`3/3 tiers ok`), not a word that appears either way (`done`).
- Cap evidence to the deciding tail, or `path:line` for manual gates.
- Five to twelve gates per leaf. Two means under-specified; twenty means the leaf should have been two leaves.
- Any number that will appear in the final report gets its own measuring `CHECK`.
